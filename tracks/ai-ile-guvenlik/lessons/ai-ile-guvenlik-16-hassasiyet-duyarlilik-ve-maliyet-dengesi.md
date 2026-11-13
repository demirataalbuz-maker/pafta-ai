---
id: ai-ile-guvenlik-16
title: "Güvenlik Ajanlarında Hassasiyet, Duyarlılık ve Maliyet Dengesi"
summary: Farklı istem ve model ayarlarında güvenlik ajanının precision, recall, F1, gecikme (ms) ve token maliyetini birlikte ölç; bütçe kısıtları altında Pareto optimal yapılandırmayı seç.
esleme: ai-guvence-04, ai-savunma-31
timeout: 300
---

::: anlat Gerçek biçimi bil, sentetik temsili ayırt et: Çok amaçlı ajan optimizasyonu
Üretim ortamındaki bir Güvenlik Operasyon Merkezi (SOC) triyajında veya otomatik zafiyet analizinde güvenlik ajanlarını değerlendirirken yalnız doğruluk (`F1`) puanına odaklanmak felaketle sonuçlanabilir:
- Çok turlu düşünce zinciri (Chain of Thought - CoT) veya ReAct döngüsü kullanan aşırı detaylı bir ajan yapılandırması saldırıların tamamına yakınını yakalayabilir (`recall = 1.0`),
- Ancak olay başına `950` token tüketip `2400 ms` çıkarım gecikmesi (latency) üreterek gerçek zamanlı olay kuyruğunun tıkanmasına (kendi kendini DoS etme durumu) ve bulut bütçesinin saatler içinde tükenmesine yol açar (`ai-guvence-04` ve `ai-savunma-31` derslerindeki bütçe ve değerlendirme ilkelerini hatırla).

| Gerçek araç / model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Çoklu istem/model değerlendirme hatlarını (`promptfoo`, yerel eval harnesses), GPU çıkarım profillerini, token sayaçlarını ve gecikme dağılımlarını | İlk üç görevde `ajan_kosu_sonuclari.json` içindeki **sentetik** koşu ölçümlerini; son görevde canlı `ai_lab.SohbetOturumu` ile dar bütçeli Pareto seçim deneyini | Yalnızca ortalama gecikme (`ortalama_ms`) ölçümünün, anlık trafik patlamalarındaki kuyruk şişmesini (`p99 tail latency`) veya model context window aşım riskini tek başına temsil edebileceğini söyleyemez |

> [!NOT]
> İlk üç görevde çalışma dizinine hazırlanan `ajan_kosu_sonuclari.json` dosyası **sentetik** bir kıyaslama (benchmark) eğitim verisidir; canlı üretim sunucusu veya ticari değerlendirici kaydı değildir. Kurulum (`setup`) bloğunda `hazirla("ai-ile-guvenlik-16")` çağrısıyla çalışma alanına geçici olarak yüklenir; çalıştırmalar arasında **kalıcılık yoktur**. Son adımdaki **Gerçek deney** adımı kurulu yerel modeli (`qwen3`) çağırarak dar token bütçesinde canlı sınıflandırma yaptırır ve Pareto seçim kapısını doğrular. Promptfoo veya harici eval sunucuları çalıştırılmaz. Amaç tek boyutlu başarı peşinde koşmak değil, bütçe kısıtları altında çok amaçlı optimizasyon (Pareto optimizasyonu) yaparak en dengeli güvenlik ajanını seçmektir.
:::

::: anlat Bir güvenlik ajanında ne olur, saldırgan neyi dener ve savunma neden kırılır?
Güvenlik ajanları binlerce gelen şüpheli isteği ve güvenlik alarmını otonom olarak sınıflandırırken karmaşık bir kalite-maliyet dengesi işletir:

- **Aracın Altında Ne Olur?** Güvenlik değerlendiricisi, ajanın her istem/model varyasyonu için elde ettiği Doğru Pozitif (`tp`), Yanlış Pozitif (`fp`), Doğru Negatif (`tn`) ve Yanlış Negatif (`fn`) sayılarını toplar. `precision` (alarm verilenlerin ne kadarı gerçek saldırı?), `recall` (gerçek saldırıların ne kadarı yakalandı?) ve bunların harmonik ortalaması olan `F1` skorunu hesaplar. Eşzamanlı olarak, her çıkarım için harcanan ortalama token miktarı ve milisaniye (`ms`) cinsinden gecikme kaydedilir.
- **Saldırganın Taktikleri:** Saldırganlar güvenlik ajanlarının operasyonel kısıtlarını doğrudan hedefler:
  1. *Karmaşıklık ve Kaynak Tüketimi Saldırısı (Algorithmic Complexity / Exhaustion):* Saldırgan, ajanın CoT veya derin düşünme motorunu tetikleyecek karmaşık, iç içe geçmiş veya çelişkili girdi yükleri gönderir. Bu, ajanın token tüketimini tavan yaptırarak SOC kuyruğunun şişmesine ve diğer meşru alarmların işlenememesine yol açar.
  2. *Eşik Altı Kalma Taktikleri (Low-and-Slow):* Saldırgan, kurumun yüksek gecikmeden kaçınmak için düşük duyarlılıklı (`ayar-hizli-kaba`) bir ajan profili çalıştırdığını fark ettiğinde, saldırı izlerini zayıf sinyallere bölerek hızlı ajanın düşük recall zafiyetinden içeri sızar.
- **Savunmanın Kırılma Noktaları:** Savunma genellikle iki uçta kırılır: Ya maliyet ve gecikme tamamen unutulup "en yüksek F1 her zaman en iyisidir" yanılgısına düşülür ve üretim kuyruğu kilitlenir; ya da aşırı bütçe kısıtlaması nedeniyle kabul edilemez oranda saldırı (`false negative`) kaçıran ucuz modeller sahaya sürülür. Doğru mühendislik yaklaşımı, asgari kabul edilebilir güvenlik barajını (`asgari_recall`) ve azami bütçe tavanını (`azami_token`, `azami_ms`) katı birer kısıt kapısı olarak uygulamak, ardından Pareto cephesinde elenmemiş en verimli ayarı seçmektir.
- **Sık Yapılan Geliştirici Tuzakları:**
  1. Sıfıra bölme hatası: `tp + fp == 0` veya `tp + fn == 0` durumlarında istisna fırlatmamak veya varsayılan `0.0` ile sistemi sessizce bozmak.
  2. Tip denetimi tuzağı: Python'da `bool` sınıfı `int` sınıfının alt sınıfı olduğundan (`isinstance(True, int) == True`), sayısal alanlarda `isinstance(deger, bool)` kontrolünün unutulması.
  3. Pareto baskınlık yönü hatası: `F1` metriğinde yüksek olan (`f1_a >= f1_b`) iyiyken, maliyet ve gecikme metriklerinde düşük olan (`token_a <= token_b`, `ms_a <= ms_b`) iyidir. Yönlerin ters çevrilmesi en kötü ayarın en iyi sanılmasına yol açar.
  4. Kesin üstünlük koşulunu atlamak: Tüm hedeflerde eşit olan iki aday (`f1`, `token`, `ms` aynı) birbirine Pareto baskın değildir; baskınlık için en az bir hedefte kesin üstünlük (`any(d > 0)`) şarttır.
  5. Sıralama anahtarında kararsızlık: Pareto cephesindeki adaylar sıralanırken eşit F1 durumunda daha az token harcayanı öne almak için `(-x["f1"], x["ortalama_token"], x["ayar_id"])` bileşik anahtarı kullanılmalıdır.
:::

::: anlat Doğruluk ve maliyet dengesinde Pareto seçimi üç adımda yapılır
Güvenlik ajanı yapılandırmaları şu üç aşamalı eleme ve seçim algoritmasıyla değerlendirilir:

1. **Kalite ve Maliyet Metrikleri (`ajan_metrik_hesapla`):** Her koşu için `precision = round(tp / (tp + fp), 4)`, `recall = round(tp / (tp + fn), 4)` ve `f1 = round((2 * tp) / (2 * tp + fp + fn), 4)` hesaplanır.
2. **Pareto Baskınlık Kontrolü (`pareto_baskin_mi`):** `A` yapılandırması `B` yapılandırmasından en az onun kadar yüksek `f1` değerine (`f1_A >= f1_B`), en az onun kadar düşük token (`token_A <= token_B`) ve gecikme (`ms_A <= ms_B`) maliyetine sahipse **ve** bu üç ölçütün en az birinde kesin olarak daha iyiyse `A`, `B`'ye **Pareto baskındır** (`True`).
3. **Kısıt Kapısı ve Optimal Seçim (`optimal_ajan_sec`):**
   - Önce `recall < asgari_recall` olanlar `"dusuk_recall"` gerekçesiyle elenir.
   - Ardından `ortalama_token > azami_token` veya `ortalama_ms > azami_ms` olanlar `"butce_asimi"` nedeniyle elenir.
   - Kalan adaylar arasında, başka bir uygun aday tarafından Pareto baskınlığına uğrayanlar `"pareto_baskin"` olarak işaretlenip elenir.
   - Pareto cephesinde kalan adaylar `(-f1, ortalama_token, ayar_id)` kuralıyla sıralanır ve ilk sıradaki ayar seçilir.
:::

::: anlat Bulguyu sınırlı ve doğrulanabilir yaz: aynı F1 puanında daha hantal olan elenir
İki ajan yapılandırması aynı `F1 = 0.9` başarısını gösteriyorsa, olay başına `410` token ve `820 ms` harcayan ayar, `540` token ve `1100 ms` harcayan ayara Pareto baskındır. Mühendislik kararı öznel tercihle değil, kısıt kapısı ve Pareto cephesiyle matematiksel olarak verilir.
:::

::: tahmin İki ajan ayarı arasında Pareto baskınlığını tahmin et
Aşağıdaki Python kodunun çıktısını tahmin et:

```python
a = {"f1": 0.9, "token": 410, "ms": 820}
b = {"f1": 0.9, "token": 540, "ms": 1100}
en_az_esit = a["f1"] >= b["f1"] and a["token"] <= b["token"] and a["ms"] <= b["ms"]
kesin_iyi = a["f1"] > b["f1"] or a["token"] < b["token"] or a["ms"] < b["ms"]
print(en_az_esit and kesin_iyi)
```

???

```cikti
True
```

`a` ayarı `b` ile aynı `f1` değerine sahipken hem daha az token hem de daha düşük gecikme kullandığı için `b` üzerinde Pareto baskındır (`True`).
:::

::: gorev 1 · Güvenlik ajanı koşusundan precision, recall ve F1 metriklerini hesapla
`ajan_metrik_hesapla(kosu)` işlevini yaz.

Kurallar:
- `kosu`: tam olarak `{"ayar_id", "tp", "fp", "tn", "fn", "ortalama_token", "ortalama_ms"}` anahtarlarına sahip `dict`; `ayar_id` boş olmayan `str`, sayısal alanlar negatif olmayan `int` (`bool` hariç) olmalıdır.
- `tp + fp > 0`, `tp + fn > 0`, `ortalama_token > 0` ve `ortalama_ms > 0` olmalıdır; aksi halde `ValueError` yükselt.
- Oranları 4 ondalığa yuvarlayarak hesapla:
  - `precision = round(tp / (tp + fp), 4)`
  - `recall = round(tp / (tp + fn), 4)`
  - `f1 = round((2 * tp) / (2 * tp + fp + fn), 4)`
- `{"ayar_id": ..., "precision": ..., "recall": ..., "f1": ..., "ortalama_token": ..., "ortalama_ms": ...}` sözlüğünü döndür.

```starter
from ai_ile_guvenlik_veri import json_yukle

kosular = json_yukle("ajan_kosu_sonuclari.json")["kosular"]

def ajan_metrik_hesapla(kosu):
    # KUSURLU BAŞLANGIÇ KODU: Sıfıra bölme kontrolünü yapmadan ve oranları 4 basamağa yuvarlamadan ham bölme uyguluyor!
    tp = kosu.get("tp", 0)
    fp = kosu.get("fp", 0)
    fn = kosu.get("fn", 0)
    p = tp / max(tp + fp, 1)
    r = tp / max(tp + fn, 1)
    f = (2 * p * r) / max(p + r, 0.0001)
    return {
        "ayar_id": kosu.get("ayar_id", ""),
        "precision": p,
        "recall": r,
        "f1": f,
        "ortalama_token": kosu.get("ortalama_token", 0),
        "ortalama_ms": kosu.get("ortalama_ms", 0),
    }

for k in kosular:
    print(ajan_metrik_hesapla(k))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-16")
```

```test
need("ajan_metrik_hesapla")

def sozlesme(fn):
    try:
        r1 = fn({
            "ayar_id": "a1",
            "tp": 9,
            "fp": 1,
            "tn": 9,
            "fn": 1,
            "ortalama_token": 410,
            "ortalama_ms": 820,
        })
        if r1 != {
            "ayar_id": "a1",
            "precision": 0.9,
            "recall": 0.9,
            "f1": 0.9,
            "ortalama_token": 410,
            "ortalama_ms": 820,
        }:
            return False

        r2 = fn({
            "ayar_id": "a2",
            "tp": 2,
            "fp": 1,
            "tn": 5,
            "fn": 1,
            "ortalama_token": 300,
            "ortalama_ms": 500,
        })
        if r2 != {
            "ayar_id": "a2",
            "precision": 0.6667,
            "recall": 0.6667,
            "f1": 0.6667,
            "ortalama_token": 300,
            "ortalama_ms": 500,
        }:
            return False

        for h in [
            None,
            {},
            {"ayar_id": "", "tp": 1, "fp": 1, "tn": 1, "fn": 1, "ortalama_token": 10, "ortalama_ms": 10},
            {"ayar_id": "a", "tp": 0, "fp": 0, "tn": 5, "fn": 2, "ortalama_token": 10, "ortalama_ms": 10},
            {"ayar_id": "a", "tp": 0, "fp": 2, "tn": 5, "fn": 0, "ortalama_token": 10, "ortalama_ms": 10},
            {"ayar_id": "a", "tp": 1, "fp": 1, "tn": 1, "fn": 1, "ortalama_token": 0, "ortalama_ms": 10},
            {"ayar_id": "a", "tp": True, "fp": 1, "tn": 1, "fn": 1, "ortalama_token": 10, "ortalama_ms": 10},
        ]:
            try:
                fn(h)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(ajan_metrik_hesapla), "ajan_metrik_hesapla: precision, recall ve F1 hesaplaması doğru")
ok(not sozlesme(lambda k: {"ayar_id": k["ayar_id"], "precision": 0.9, "recall": 0.9, "f1": 0.9, "ortalama_token": 410, "ortalama_ms": 820}), "mutasyon: sabit metrik döndüren işlev reddedilmeli")
```

```solution
from ai_gercek_ai_ile_guvenlik_16 import _kosu_kontrol

def ajan_metrik_hesapla(kosu):
    _kosu_kontrol(kosu)
    tp = kosu["tp"]
    fp = kosu["fp"]
    fn = kosu["fn"]

    Payda_p = tp + fp
    Payda_r = tp + fn
    iki_tp = tp + tp

    return {
        "ayar_id": kosu["ayar_id"],
        "precision": round(tp / Payda_p, 4),
        "recall": round(tp / Payda_r, 4),
        "f1": round(iki_tp / (iki_tp + fp + fn), 4),
        "ortalama_token": kosu["ortalama_token"],
        "ortalama_ms": kosu["ortalama_ms"],
    }
```

```hint
`_kosu_kontrol(kosu)` doğrulamasından sonra `precision`, `recall` ve `f1` oranlarını `round(..., 4)` ile hesapla.
```
:::

::: gorev 2 · İki yapılandırma arasında Pareto baskınlığını kontrol et
`pareto_baskin_mi(aday_a, aday_b)` işlevini yaz.

Kurallar:
- `aday_a` ve `aday_b`: 1. görevin çıktısı olan metrik sözlüğü şemasına (`{"ayar_id", "precision", "recall", "f1", "ortalama_token", "ortalama_ms"}`) sahip olmalıdır; aksi halde `ValueError` yükselt.
- `aday_a` şu iki koşulu birlikte sağlıyorsa `True`, aksi halde `False` döndür:
  1. Tüm hedeflerde en az `aday_b` kadar iyi olma: `f1_a >= f1_b`, `token_a <= token_b` ve `ms_a <= ms_b`.
  2. En az bir hedefte kesin daha iyi olma: `f1_a > f1_b` veya `token_a < token_b` veya `ms_a < ms_b`.

```starter
def pareto_baskin_mi(aday_a, aday_b):
    # KUSURLU BAŞLANGIÇ KODU: Maliyet ve gecikme metriklerini ters yönde karşılaştırarak kaynak tüketimi daha yüksek olan ayarı baskın sayıyor!
    f1_a = aday_a.get("f1", 0)
    f1_b = aday_b.get("f1", 0)
    token_a = aday_a.get("ortalama_token", 0)
    token_b = aday_b.get("ortalama_token", 0)
    ms_a = aday_a.get("ortalama_ms", 0)
    ms_b = aday_b.get("ortalama_ms", 0)
    en_az_esit = (f1_a >= f1_b) and (token_a >= token_b) and (ms_a >= ms_b)
    kesin_iyi = (f1_a > f1_b) or (token_a > token_b) or (ms_a > ms_b)
    return en_az_esit and kesin_iyi

print(pareto_baskin_mi(
    {"ayar_id": "a", "precision": 0.9, "recall": 0.9, "f1": 0.9, "ortalama_token": 400, "ortalama_ms": 800},
    {"ayar_id": "b", "precision": 0.9, "recall": 0.9, "f1": 0.9, "ortalama_token": 500, "ortalama_ms": 900},
))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-16")
```

```test
need("pareto_baskin_mi")

BAZ = {"ayar_id": "a", "precision": 0.9, "recall": 0.9, "f1": 0.9, "ortalama_token": 410, "ortalama_ms": 820}
HANTAL_TOKEN = {"ayar_id": "b", "precision": 0.9, "recall": 0.9, "f1": 0.9, "ortalama_token": 540, "ortalama_ms": 820}
HANTAL_MS = {"ayar_id": "c", "precision": 0.9, "recall": 0.9, "f1": 0.9, "ortalama_token": 410, "ortalama_ms": 1100}
DUSUK_F1 = {"ayar_id": "d", "precision": 0.8, "recall": 0.8, "f1": 0.8, "ortalama_token": 410, "ortalama_ms": 820}
TAKASLI = {"ayar_id": "e", "precision": 0.95, "recall": 0.95, "f1": 0.95, "ortalama_token": 600, "ortalama_ms": 820}

def sozlesme(fn):
    try:
        if fn(BAZ, HANTAL_TOKEN) is not True:
            return False
        if fn(BAZ, HANTAL_MS) is not True:
            return False
        if fn(BAZ, DUSUK_F1) is not True:
            return False
        if fn(BAZ, BAZ) is not False:
            return False
        if fn(HANTAL_TOKEN, BAZ) is not False:
            return False
        if fn(BAZ, TAKASLI) is not False or fn(TAKASLI, BAZ) is not False:
            return False

        for a_in, b_in in [
            (None, BAZ),
            (BAZ, {}),
            (dict(BAZ, f1=1.5), BAZ),
            (dict(BAZ, ortalama_token=0), BAZ),
        ]:
            try:
                fn(a_in, b_in)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(pareto_baskin_mi), "pareto_baskin_mi: F1, token ve gecikme eksenlerinde Pareto baskınlığını doğru saptamalı")
ok(not sozlesme(lambda a, b: True), "mutasyon: her çifti baskın sayan işlev reddedilmeli")
```

```solution
from ai_gercek_ai_ile_guvenlik_16 import _metrik_sozlugu_kontrol

def pareto_baskin_mi(aday_a, aday_b):
    _metrik_sozlugu_kontrol(aday_a)
    _metrik_sozlugu_kontrol(aday_b)

    farklar = (
        aday_a["f1"] - aday_b["f1"],
        aday_b["ortalama_token"] - aday_a["ortalama_token"],
        aday_b["ortalama_ms"] - aday_a["ortalama_ms"],
    )
    return all(d >= 0 for d in farklar) and any(d > 0 for d in farklar)
```

```hint
İyileşme farklarını `(a["f1"] - b["f1"], b["ortalama_token"] - a["ortalama_token"], b["ortalama_ms"] - a["ortalama_ms"])` olarak kur; tümünün `>= 0` ve en az birinin `> 0` olup olmadığını kontrol et.
```
:::

::: gorev 3 · Kısıt kapısı ve Pareto cephesiyle optimal güvenlik ajanını seç
`optimal_ajan_sec(kosular, kisitlar)` işlevini yaz.

Kurallar:
- `kosular`: boş olmayan `list`; her öğesi 1. görevdeki şemaya uymalı ve `ayar_id` değerleri benzersiz olmalıdır.
- `kisitlar`: tam olarak `{"asgari_recall", "azami_token", "azami_ms"}` anahtarlarına sahip `dict` olmalıdır (aksi halde `ValueError` yükselt).
- Her koşuyu önce `ajan_metrik_hesapla` ile değerlendir ve kısıt kapısından geçir:
  - `recall < kisitlar["asgari_recall"]` ise `elenen_ayarlar[ayar_id] = "dusuk_recall"` olarak ayır.
  - `ortalama_token > kisitlar["azami_token"]` veya `ortalama_ms > kisitlar["azami_ms"]` ise `elenen_ayarlar[ayar_id] = "butce_asimi"` olarak ayır.
- Kısıtları geçen adaylar arasında başka bir uygun aday tarafından Pareto baskınlığına uğrayanları `elenen_ayarlar[ayar_id] = "pareto_baskin"` olarak ayır.
- Kalan Pareto cephesi adaylarını `(-f1, ortalama_token, ayar_id)` sırasına diz; ilkini `secilen_ayar_id` olarak seç (hiç aday kalmazsa `None`).
- `{"secilen_ayar_id": ..., "pareto_adaylari": [...], "elenen_ayarlar": ...}` sözlüğünü döndür.

```starter
from ai_ile_guvenlik_veri import json_yukle

veri = json_yukle("ajan_kosu_sonuclari.json")

def optimal_ajan_sec(kosular, kisitlar):
    # KUSURLU BAŞLANGIÇ KODU: Bütçe kısıtlarını ve Pareto baskınlığını denetlemeden yalnız asgari recall kontrolüyle ilk ayarı seçiyor!
    asgari_recall = kisitlar.get("asgari_recall", 0.0)
    elenen = {}
    uygun = []
    for k in kosular:
        aid = k.get("ayar_id", "")
        r = k.get("tp", 0) / max(k.get("tp", 0) + k.get("fn", 0), 1)
        if r < asgari_recall:
            elenen[aid] = "dusuk_recall"
        else:
            uygun.append(aid)
    secilen = uygun[0] if uygun else None
    return {
        "secilen_ayar_id": secilen,
        "pareto_adaylari": uygun,
        "elenen_ayarlar": elenen,
    }

print(optimal_ajan_sec(veri["kosular"], veri["kisitlar"]))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-16")
```

```test
need("optimal_ajan_sec")
from ai_ile_guvenlik_veri import json_yukle

VERI = json_yukle("ajan_kosu_sonuclari.json")
KOSULAR = VERI["kosular"]
KISITLAR = VERI["kisitlar"]

def sozlesme(fn):
    try:
        r = fn(KOSULAR, KISITLAR)
        if r != {
            "secilen_ayar_id": "ayar-dengeli-v1",
            "pareto_adaylari": ["ayar-dengeli-v1"],
            "elenen_ayarlar": {
                "ayar-hizli-kaba": "dusuk_recall",
                "ayar-dengeli-hantal": "pareto_baskin",
                "ayar-asiri-dusunen": "butce_asimi",
            },
        }:
            return False

        r_bos = fn([KOSULAR[0]], KISITLAR)
        if r_bos["secilen_ayar_id"] is not None or r_bos["pareto_adaylari"] != []:
            return False

        r_sinir = fn([KOSULAR[1]], {"asgari_recall": 0.9, "azami_token": 410, "azami_ms": 820})
        if r_sinir["secilen_ayar_id"] != "ayar-dengeli-v1":
            return False

        for k_in, s_in in [
            (None, KISITLAR),
            (tuple(KOSULAR), KISITLAR),
            (123, KISITLAR),
            ([], KISITLAR),
            ([KOSULAR[0], KOSULAR[0]], KISITLAR),
            (KOSULAR, None),
            (KOSULAR, {}),
        ]:
            try:
                fn(k_in, s_in)
                return False
            except ValueError:
                pass
        import copy
        a = copy.deepcopy(KOSULAR[1]); b = copy.deepcopy(a)
        a["ayar_id"] = "a"; b["ayar_id"] = "b"
        b["ortalama_token"] = a["ortalama_token"] - 1
        b["ortalama_ms"] = a["ortalama_ms"] + 1
        trade = fn([a, b], {"asgari_recall": 0, "azami_token": 999999, "azami_ms": 999999})
        if sorted(trade["pareto_adaylari"]) != ["a", "b"]:
            return False
        c = copy.deepcopy(KOSULAR[1]); d = copy.deepcopy(c); eq_dup = copy.deepcopy(c)
        c["ayar_id"] = "z-yuksek"; c["tp"] = 19; c["fp"] = 1; c["fn"] = 1; c["ortalama_token"] = 500
        d["ayar_id"] = "a-dusuk"; d["tp"] = 8; d["fp"] = 2; d["fn"] = 3; d["ortalama_token"] = 200
        eq_dup["ayar_id"] = "z-esit"; eq_dup["tp"] = 19; eq_dup["fp"] = 1; eq_dup["fn"] = 1; eq_dup["ortalama_token"] = 500
        f1_sira = fn([d, eq_dup, c], {"asgari_recall": 0, "azami_token": 999999, "azami_ms": 999999})
        if f1_sira["pareto_adaylari"] != ["z-esit", "z-yuksek", "a-dusuk"] or f1_sira["secilen_ayar_id"] != "z-esit":
            return False
        dom_a = dict(KOSULAR[1], ayar_id="dom-a", tp=9, fp=0, fn=1, ortalama_token=300, ortalama_ms=500)
        dom_b = dict(KOSULAR[1], ayar_id="dom-b", tp=8, fp=2, fn=0, ortalama_token=300, ortalama_ms=500)
        dom_r = fn([dom_a, dom_b], {"asgari_recall": 0, "azami_token": 999999, "azami_ms": 999999})
        if dom_r != {"secilen_ayar_id": "dom-a", "pareto_adaylari": ["dom-a"], "elenen_ayarlar": {"dom-b": "pareto_baskin"}}:
            return False
        return True
    except Exception:
        return False

ok(sozlesme(optimal_ajan_sec), "optimal_ajan_sec: düşük recall, bütçe aşımı ve Pareto baskın adayları eleyip optimal ayarı seçmeli")
ok(not sozlesme(lambda k, s: {"secilen_ayar_id": "ayar-dengeli-hantal", "pareto_adaylari": [], "elenen_ayarlar": {}}), "mutasyon: Pareto baskın adayı seçen işlev reddedilmeli")
```

```solution
from ai_gercek_ai_ile_guvenlik_16 import _kisit_kontrol, _kosu_kontrol, _metrik_sozlugu_kontrol

def ajan_metrik_hesapla(kosu):
    _kosu_kontrol(kosu)
    tp = kosu["tp"]
    fp = kosu["fp"]
    fn = kosu["fn"]

    payda_p = tp + fp
    payda_r = tp + fn
    iki_tp = tp + tp

    return {
        "ayar_id": kosu["ayar_id"],
        "precision": round(tp / payda_p, 4),
        "recall": round(tp / payda_r, 4),
        "f1": round(iki_tp / (iki_tp + fp + fn), 4),
        "ortalama_token": kosu["ortalama_token"],
        "ortalama_ms": kosu["ortalama_ms"],
    }

def pareto_baskin_mi(aday_a, aday_b):
    _metrik_sozlugu_kontrol(aday_a)
    _metrik_sozlugu_kontrol(aday_b)

    farklar = (
        aday_a["f1"] - aday_b["f1"],
        aday_b["ortalama_token"] - aday_a["ortalama_token"],
        aday_b["ortalama_ms"] - aday_a["ortalama_ms"],
    )
    return all(d >= 0 for d in farklar) and any(d > 0 for d in farklar)

def optimal_ajan_sec(kosular, kisitlar):
    if not (isinstance(kosular, list) and bool(kosular)):
        raise ValueError("kosular boş olmayan liste olmalı")
    _kisit_kontrol(kisitlar)

    uygunlar = []
    elenenler = {}
    gorulen = set()

    for k in kosular:
        m = ajan_metrik_hesapla(k)
        aid = m["ayar_id"]
        if aid in gorulen:
            raise ValueError("tekrarlanan ayar_id")
        gorulen.add(aid)

        if m["recall"] < kisitlar["asgari_recall"]:
            elenenler[aid] = "dusuk_recall"
            continue
        if any([m["ortalama_token"] > kisitlar["azami_token"], m["ortalama_ms"] > kisitlar["azami_ms"]]):
            elenenler[aid] = "butce_asimi"
            continue
        uygunlar.append(m)

    pareto_kumesi = []
    for m in uygunlar:
        if any(pareto_baskin_mi(diger, m) for diger in uygunlar if diger["ayar_id"] != m["ayar_id"]):
            elenenler[m["ayar_id"]] = "pareto_baskin"
        else:
            pareto_kumesi.append(m)

    pareto_kumesi.sort(key=lambda x: (-x["f1"], x["ortalama_token"], x["ayar_id"]))
    secilen = pareto_kumesi[0]["ayar_id"] if pareto_kumesi else None

    return {
        "secilen_ayar_id": secilen,
        "pareto_adaylari": [x["ayar_id"] for x in pareto_kumesi],
        "elenen_ayarlar": elenenler,
    }
```

```hint
Önce `recall < asgari_recall` ve bütçe aşımı kontrollerini uygula; kalanlar içinde başka bir aday tarafından Pareto baskınlığına uğrayanları `"pareto_baskin"` olarak ayır.
```
:::

::: gorev Gerçek deney · Yerel modelle güvenlik ajanında doğruluk ve maliyet dengesi deneyi
Önceki üç görevde yazdığın `ajan_metrik_hesapla`, `pareto_baskin_mi` ve `optimal_ajan_sec` işlevlerini bu adımda birleştir.

Canlı deneyde:
1. Yerel Ollama modeli (`ai_lab.SohbetOturumu`) dar token bütçesiyle (`en_fazla=40`) SOC triyaj sınıflandırması yapar.
2. Farklı istem/model koşularının sonuçları senin yazdığın `optimal_ajan_sec` değerlendiricisinden geçirilir.
3. Düşük duyarlılıklı (`ayar-hizli-kaba`), bütçe aşan (`ayar-asiri-dusunen`) ve Pareto baskınlığına uğrayan (`ayar-dengeli-hantal`) ayarların elenip `ayar-dengeli-v1` yapılandırmasının seçildiği doğrulanır.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab

def ajan_metrik_hesapla(kosu):
    # KUSURLU BAŞLANGIÇ KODU: Metrikleri hesaplamadan boş şablon döndürüyor!
    return {"ayar_id": kosu.get("ayar_id", ""), "precision": 0.0, "recall": 0.0, "f1": 0.0, "ortalama_token": 0, "ortalama_ms": 0}

def pareto_baskin_mi(aday_a, aday_b):
    # KUSURLU BAŞLANGIÇ KODU: Karşılaştırma yapmadan her zaman False dönüyor!
    return False

def optimal_ajan_sec(kosular, kisitlar):
    # KUSURLU BAŞLANGIÇ KODU: Kısıt ve Pareto elemesini yapmadan boş seçim dönüyor!
    return {"secilen_ayar_id": None, "pareto_adaylari": [], "elenen_ayarlar": {}}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_ile_guvenlik_16 as deney
    deney.goster(ajan_metrik_hesapla, pareto_baskin_mi, optimal_ajan_sec)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-16")
```

```test
import ast
import ai_lab
from sandbox import ai_gercek_ai_ile_guvenlik_16 as D

checks = []
_base_ok = ok
def ok(kosul, mesaj):
    checks.append(bool(kosul))
    return _base_ok(kosul, mesaj)

for ad in ("ajan_metrik_hesapla", "pareto_baskin_mi", "optimal_ajan_sec"):
    need(ad)

yasak = (
    "referans",
    "ajan_metrik_hesapla_referans",
    "pareto_baskin_mi_referans",
    "optimal_ajan_sec_referans",
    "getattr",
    "kanit_yaz",
)
ihlal = ai_lab.kod_denetimi(src, yasak=yasak)
try:
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.ImportFrom) and any(a.name in yasak or a.name == "*" for a in node.names):
            ihlal.append("referans ithali")
except SyntaxError:
    ihlal.append("sözdizimi")

ok(not ihlal, "Kendi çözümünü yaz; referans işlevler ithal edilemez: " + ", ".join(ihlal))
if not all(checks):
    stop()

def _on_sozlesme():
    try:
        m1 = ajan_metrik_hesapla({"ayar_id": "a2", "tp": 2, "fp": 1, "tn": 5, "fn": 3, "ortalama_token": 300, "ortalama_ms": 500})
        if m1 != {"ayar_id": "a2", "precision": 0.6667, "recall": 0.4, "f1": 0.5, "ortalama_token": 300, "ortalama_ms": 500}:
            return False
        for h in (None, {}, dict(D.ORNEK_KOSULAR[0], tp=0, fp=0), dict(D.ORNEK_KOSULAR[0], tp=0, fn=0)):
            try:
                ajan_metrik_hesapla(h)
                return False
            except ValueError:
                pass
        baz = {"ayar_id": "a", "precision": 0.9, "recall": 0.9, "f1": 0.9, "ortalama_token": 410, "ortalama_ms": 820}
        if pareto_baskin_mi(baz, dict(baz, ortalama_token=540)) is not True:
            return False
        if pareto_baskin_mi(baz, dict(baz, ortalama_ms=1100)) is not True:
            return False
        if pareto_baskin_mi(baz, dict(baz, f1=0.8)) is not True:
            return False
        if pareto_baskin_mi(baz, baz) is not False:
            return False
        if pareto_baskin_mi(baz, dict(baz, f1=0.95, ortalama_token=600)) is not False:
            return False
        if pareto_baskin_mi(dict(baz, ortalama_token=409, ortalama_ms=821), baz) is not False:
            return False
        for a_in, b_in in [(None, baz), (baz, {})]:
            try:
                pareto_baskin_mi(a_in, b_in)
                return False
            except ValueError:
                pass
        if optimal_ajan_sec(D.ORNEK_KOSULAR, D.KISITLAR) != {
            "secilen_ayar_id": "ayar-dengeli-v1",
            "pareto_adaylari": ["ayar-dengeli-v1"],
            "elenen_ayarlar": {
                "ayar-hizli-kaba": "dusuk_recall",
                "ayar-dengeli-hantal": "pareto_baskin",
                "ayar-asiri-dusunen": "butce_asimi",
            },
        }:
            return False
        if optimal_ajan_sec([D.ORNEK_KOSULAR[0]], D.KISITLAR)["secilen_ayar_id"] is not None:
            return False
        if optimal_ajan_sec([D.ORNEK_KOSULAR[1]], {"asgari_recall": 0.9, "azami_token": 410, "azami_ms": 820})["secilen_ayar_id"] != "ayar-dengeli-v1":
            return False
        if optimal_ajan_sec([dict(D.ORNEK_KOSULAR[1], ortalama_ms=9999)], D.KISITLAR)["elenen_ayarlar"]["ayar-dengeli-v1"] != "butce_asimi":
            return False
        k_a = dict(D.ORNEK_KOSULAR[1], ayar_id="b", ortalama_token=409, ortalama_ms=821)
        k_b = dict(D.ORNEK_KOSULAR[1], ayar_id="a", ortalama_token=410, ortalama_ms=820)
        tr = optimal_ajan_sec([k_b, k_a], {"asgari_recall": 0, "azami_token": 999999, "azami_ms": 999999})
        if tr["pareto_adaylari"] != ["b", "a"] or tr["secilen_ayar_id"] != "b":
            return False
        k_hi = dict(D.ORNEK_KOSULAR[1], ayar_id="z-hi", tp=19, fp=1, fn=1, ortalama_token=500)
        k_lo = dict(D.ORNEK_KOSULAR[1], ayar_id="a-lo", tp=8, fp=2, fn=3, ortalama_token=200)
        tr_f1 = optimal_ajan_sec([k_lo, k_hi], {"asgari_recall": 0, "azami_token": 999999, "azami_ms": 999999})
        if tr_f1["pareto_adaylari"] != ["z-hi", "a-lo"] or tr_f1["secilen_ayar_id"] != "z-hi":
            return False
        for k_list in (None, tuple(D.ORNEK_KOSULAR), 123, [], [D.ORNEK_KOSULAR[0], D.ORNEK_KOSULAR[0]]):
            try:
                optimal_ajan_sec(k_list, D.KISITLAR)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(_on_sozlesme(), "sentetik ön kontrol: F1, bütçe kısıtı ve Pareto seçim kuralları tam")

if not all(checks):
    stop()

try:
    r = D.deney(ajan_metrik_hesapla, pareto_baskin_mi, optimal_ajan_sec)
except Exception as e:
    ok(False, f"GERÇEK PARETO DENGE DENEYİ YAPILAMADI: {type(e).__name__}: {e}")
    stop()

for ad, deger in r["kontroller"].items():
    ok(deger, "gerçek deney: " + ad)

ai_lab.kanit_yaz("ile-guvenlik-16-denge", {
    "kaynak": "gercek",
    "kabul": all(checks),
    "ders": "ai-ile-guvenlik-16",
    "ortam": r["ortam"],
    "ayarlar": r["ayarlar"],
    "deney": r,
    "ozet": r["ozet"],
})
o = r["ozet"]
ok(
    True,
    f"BULGU ({o['model']}): secilen={o['secilen_ayar']}, elenen={o['elenen_ayarlar']}.",
)
```

```solution
import ai_lab
from sandbox.ai_gercek_ai_ile_guvenlik_16 import _kisit_kontrol, _kosu_kontrol, _metrik_sozlugu_kontrol

def ajan_metrik_hesapla(kosu):
    _kosu_kontrol(kosu)
    tp = kosu["tp"]
    fp = kosu["fp"]
    fn = kosu["fn"]

    payda_p = tp + fp
    payda_r = tp + fn
    iki_tp = tp + tp

    return {
        "ayar_id": kosu["ayar_id"],
        "precision": round(tp / payda_p, 4),
        "recall": round(tp / payda_r, 4),
        "f1": round(iki_tp / (iki_tp + fp + fn), 4),
        "ortalama_token": kosu["ortalama_token"],
        "ortalama_ms": kosu["ortalama_ms"],
    }

def pareto_baskin_mi(aday_a, aday_b):
    _metrik_sozlugu_kontrol(aday_a)
    _metrik_sozlugu_kontrol(aday_b)

    farklar = (
        aday_a["f1"] - aday_b["f1"],
        aday_b["ortalama_token"] - aday_a["ortalama_token"],
        aday_b["ortalama_ms"] - aday_a["ortalama_ms"],
    )
    return all(d >= 0 for d in farklar) and any(d > 0 for d in farklar)

def optimal_ajan_sec(kosular, kisitlar):
    if not (isinstance(kosular, list) and bool(kosular)):
        raise ValueError("kosular boş olmayan liste olmalı")
    _kisit_kontrol(kisitlar)

    uygunlar = []
    elenenler = {}
    gorulen = set()

    for k in kosular:
        m = ajan_metrik_hesapla(k)
        aid = m["ayar_id"]
        if aid in gorulen:
            raise ValueError("tekrarlanan ayar_id")
        gorulen.add(aid)

        if m["recall"] < kisitlar["asgari_recall"]:
            elenenler[aid] = "dusuk_recall"
            continue
        if any([m["ortalama_token"] > kisitlar["azami_token"], m["ortalama_ms"] > kisitlar["azami_ms"]]):
            elenenler[aid] = "butce_asimi"
            continue
        uygunlar.append(m)

    pareto_kumesi = []
    for m in uygunlar:
        if any(pareto_baskin_mi(diger, m) for diger in uygunlar if diger["ayar_id"] != m["ayar_id"]):
            elenenler[m["ayar_id"]] = "pareto_baskin"
        else:
            pareto_kumesi.append(m)

    pareto_kumesi.sort(key=lambda x: (-x["f1"], x["ortalama_token"], x["ayar_id"]))
    secilen = pareto_kumesi[0]["ayar_id"] if pareto_kumesi else None

    return {
        "secilen_ayar_id": secilen,
        "pareto_adaylari": [x["ayar_id"] for x in pareto_kumesi],
        "elenen_ayarlar": elenenler,
    }

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_ile_guvenlik_16 as deney
    deney.goster(ajan_metrik_hesapla, pareto_baskin_mi, optimal_ajan_sec)
```

```hint
Önceki üç görevdeki `ajan_metrik_hesapla`, `pareto_baskin_mi` ve `optimal_ajan_sec` işlevlerini birleştir.
```
:::


::: anlat Bunu iki dakikada nasıl anlatırsın?
Precision/recall/F1 aynı risk ve maliyet sorusunu cevaplamaz. Önce kalite ve token/gecikme tavanlarını uygula; sonra Pareto baskınlığı için bütün eksenlerde en az eşit, birinde kesin daha iyi olma koşulunu türet. İki eşit yapılandırma birbirine baskın değildir. Birden çok Pareto adayı kalırsa son sıralama kuralı yine açık bir tercih belirtir; tek evrensel optimal güvenlik ajanı bulunmuş olmaz.

Önkoşul ve yol köprüsü: ai-savunma-31 tüketim tavanı.

| Yaygın yanlış | Mekanizma ve sınır |
|---|---|
| En yüksek F1 her üretim sistemi için en iyidir | Kısıtlar ve maliyet tercihleri optimumu değiştirir |

Dinleyiciye sor: Bir model önerisini gerçek güvenlik kararı hâline getiren hangi uygulama denetimidir? Veri kökenini ve kalan sınırı koruyarak cevapla.
:::


### Birincil kaynak ve deneyin sınırı

[Ollama sohbet API sözleşmesi](https://docs.ollama.com/api/chat). Yanıtın sayaç ve süre alanları ölçüm girdisidir; yerel örneklemdeki Pareto seçimi genel bir model üstünlüğü kanıtlamaz.
