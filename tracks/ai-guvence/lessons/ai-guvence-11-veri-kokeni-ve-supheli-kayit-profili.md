---
id: ai-guvence-11
title: Veri Kökeni ve Şüpheli Kayıt Profili
summary: Kaynak ve dönüşüm geçmişini doğrula; dağılım sapmasını ölçerek izlenebilir şüpheli kayıt profili üret.
esleme: ai-guvence-12, ai-guvence-15, ai-guvence-21
timeout: 45
---

::: anlat Gerçek veri soykütüğünü (lineage) bil, sentetik temsili ayırt et
Bir veri kaydını değerlendirirken yalnız içeriğine bakmak yetmez. Kaynağı, sürümü ve uygulanan dönüşümlerin sırası korunmalıdır. Ham kayıtta dönüşüm listesi boş olabilir; sonraki her işlem açık ve sıralı bir iz bırakmalıdır. Veri soykütüğü (`data lineage`), model eğitimine giren her girdinin hangi kaynaktan geldiğini ve hangi aşamalardan geçtiğini kanıtlanabilir kılar.

| Gerçek araç / model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| DVC/OpenLineage köken kayıtlarını, total variation distance değerini ($TVD = \frac{1}{2}\sum |p_i - q_i|$) ve scikit-learn model olasılık sapmalarını | İlk üç görevde `veri/koken_kayitlari.json` ve `veri/dagilim_ve_profil.json` içindeki **sentetik** köken/dağılım kayıtlarını; son görevde `scikit-learn` (`LogisticRegression`) ile canlı telemetri köken ve şüpheli profil analizini | Geçerli köken üstverisinin, kaynak deponun ele geçirilmediğini kriptografik imza olmadan tek başına kanıtlayabileceğini; yüksek sapmanın doğal alt-popülasyonlar yerine kesin zehirleme olduğunu söyleyemez |

> [!NOT]
> İlk üç görevde çalışma dizinine kopyalanan `veri/koken_kayitlari.json` ve `veri/dagilim_ve_profil.json` dosyaları **sentetik** eğitim örnekleridir. Her çalıştırmada yeniden kopyalanır; çalıştırmalar arasında **kalıcılık yoktur**. Son adımdaki **Gerçek deney** görevinde yazdığın üç işlev `scikit-learn` sınıflandırıcısının canlı olasılık sapmaları ve telemetri kökeniyle sınanır; harici DVC veya OpenLineage sunucusu çalıştırılmaz.
:::

::: anlat Veri kökeni ve şüpheli profil hattında ne olur, saldırgan ne dener ve savunma neden kırılır?
Yapay zeka sistemlerine beslenen verilerin güvenilirliği, verinin üretim kaynağından model girdisine kadar olan zincirin bütünlüğüne bağlıdır:

- **Aracın Altında Ne Olur?**
  1. *Veri Kökeni ve Soykütüğü Doğrulama (`kayit_kokeni_dogrula`):* Gelen veri paketinin `id`, `kaynak`, `surum` ve sıralı `donusumler` alanları doğrulanır. Kimlik biçimi (ASCII regex), kaynak metin uzunluğu ve sürümün pozitif tamsayı olması denetlenir. Ham veriden eğitime kadar olan adımların (`donusumler`) sırası ve yinelenmezliği garanti edilir.
  2. *total variation distance ile Dağılım Sapması (`dagilim_sapmasi`):* Beklenen referans dağılım ile gözlenen dağılımın kategorik frekansları kendi toplamlarına bölünerek olasılık dağılımlarına normalize edilir. total variation distance (\(TVD = \frac{1}{2} \sum |p_i - q_i|\)) hesaplanır ve en çok sapan kategori alfabetik eşitlik kuralıyla saptanır.
  3. *Şüpheli Kayıt Profillemesi (`supheli_kayit_profili`):* Modelin atanan sınıfa verdiği tahmin olasılığından hesaplanan sapma (\(1 - P(y_{\text{atanan}} \mid x)\)) eşik değerini (\(\ge \text{esik}\)) aşıyorsa veya kaydın etiketinde bir değişiklik (`etiket_degisti = True`) tespit edilmişse kayıt şüpheli kabul edilir. Şüpheli kayıtların kaynaklara göre dağılımı (`kaynaklar`) çıkarılarak dış kaynaklardan sızan zehir profillenir.
- **Çıktı Nasıl Okunur?**
  - TVD skoru \(0\) ile \(1\) arasında değişir; \(0\) tam örtüşmeyi, \(1\) ise tamamen ayrık dağılımları gösterir.
  - Şüpheli kayıt oranı (\(\text{supheli\_orani}\)) toplam girdi evrenine göre hesaplanır; ancak `kaynaklar` sözlüğü yalnız şüpheli kayıtların hangi kaynaktan geldiğini sayar.
- **Saldırganın Taktikleri:**
  1. *Soykütüğü Sahteciliği (Lineage Tampering):* Saldırgan, denetim izini örtbas etmek için sahte dönüşüm adımları enjekte eder veya sürüm numaralarını manipüle ederek eski zehirli paketleri meşru gibi sunar.
  2. *Sessiz Dağılım Kayması (Silent Covariate Shift):* Saldırgan, genel sınıf oranlarını bozmadan altküme özniteliklerini kaydırarak modelin karar sınırlarını bozar.
- **Savunmanın Kırılma Noktaları:**
  - Kriptografik imza olmadan yalnızca üstveri metnine güvenmek: Üstveriyi değiştiren bir saldırgan kolayca meşru köken süsü verebilir.
  - Normalizasyon yapmadan ham frekansları karşılaştırmak: Farklı büyüklükteki veri kümelerinde ham farklar yanıltıcı sapmalar üretir.
- **Sık Yapılan Geliştirici Tuzakları:**
  1. Python'da `bool` tipinin `int` alt sınıfı olması (`issubclass(bool, int) is True`): `surum` ve sayısal girdilerde `not isinstance(x, bool)` kontrolünün unutulması.
  2. Girdi sözlüklerini ve dönüşüm listelerini yerinde kopyalamamak (`list(donusumler)`): Yan etkiler güvenlik izini bozar.
  3. Eşitlik durumunda alfabetik sıralama kuralını ihmal etmek: `max(farklar, key=...)` aramasında determinizm için kategorilerin önceden sıralanması zorunludur.
  4. Şüpheli oranının paydası ile kaynaklar sözlüğünün evrenini karıştırmak: Oranın paydası tüm kayıtlarken, kaynak sayımları yalnız şüpheli kayıtları kapsar.
:::

::: anlat Sapma ve etiket değişikliği ayrı kanıtlardır
İki dağılımı karşılaştırırken önce sayıları kendi toplamlarına bölerek olasılığa çeviririz. Toplam varyasyon, kategori olasılık farklarının mutlak değerler toplamının yarısıdır. Böylece farklı büyüklükteki örneklem sayıları doğrudan karşılaştırılabilir.

Kayıt profilinde dağılım sapması eşiği ve etiket değişikliği ayrı korunur. Eşiğe eşit sapma şüphelidir; etiketi değişen kayıt ise sapma değeri düşük olsa da listeye girer. Şüpheli kayıt oranı tüm kayıtlar üzerinden, kaynak dağılımı ise yalnız şüpheli kayıtlar üzerinden hesaplanır.

Kaynaklar: [OpenLineage — An Open Framework for Data Lineage Collection and Analysis](https://openlineage.io/), [Steinhardt vd. 2017 — Certified Defenses for Data Poisoning Attacks (arXiv:1706.03691)](https://arxiv.org/abs/1706.03691).
:::

::: tahmin Sapma ve şüpheli oranını tahmin et
Üç çıktı satırını yaz:

```python
print(round(0.5 * (abs(0.7 - 0.5) + abs(0.3 - 0.5)), 6))
print(max(["b", "a"], key=lambda k: {"a": 0.2, "b": 0.1}[k]))
print(round(2 / 3, 6))
```

???

```cikti
0.2
a
0.666667
```

İlk satır toplam varyasyonu, ikinci satır en büyük farklı kategoriyi, üçüncü satır altı ondalıklı şüpheli kayıt oranını gösterir.
:::

::: gorev 1 · Kayıt kökenini doğrula
`kayit_kokeni_dogrula(kayit)` işlevini yaz. Kayıt tam olarak `id`, `kaynak`, `surum`, `donusumler` alanlarını taşısın. Kimlik 1–64 karakterlik, ASCII harf/rakamla başlayan ve yalnız ASCII harf, rakam, alt çizgi veya tire içeren stringdir. Kaynak başı ve sonu boşluk olmayan, 1–120 karakterlik stringdir. Sürüm bool olmayan pozitif tamsayıdır.

Dönüşümler stringlerden oluşan listedir; boş liste ham kayıt için geçerlidir. Her dönüşüm başı ve sonu boşluk olmayan 1–80 karakterlik stringdir ve listede yinelenemez. Geçersiz veride `ValueError` yükselt. Alanları ve dönüşüm sırasını koruyan bağımsız yeni sözlük döndür; girdiyi değiştirme.

```starter
from ai_guvence_veri import json_yukle

def kayit_kokeni_dogrula(kayit):
    # KUSURLU BAŞLANGIÇ KODU: dönüşümleri kopyalamadan ve yinelenmeyi denetlemeden döndürüyor!
    return kayit

print("Örnek köken:", kayit_kokeni_dogrula(json_yukle("veri/koken_kayitlari.json")))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-11")
```

```test
import copy
K = {"id": "ornek-1", "kaynak": "yerel-arşiv", "surum": 2, "donusumler": ["temizle", "normalize"]}
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        sonuc = fn(K)
        if sonuc != K or K != once or sonuc is K or sonuc["donusumler"] is K["donusumler"]:
            return False
        ham = {"id": "a" * 64, "kaynak": "k", "surum": 1, "donusumler": []}
        if fn(ham) != ham:
            return False
        sinir = {"id": "sinir", "kaynak": "k" * 120, "surum": 1, "donusumler": ["x", "y" * 80]}
        if fn(sinir) != sinir:
            return False
        for kayit in [
            None, [], dict(K, ek=1), dict(K, id=""), dict(K, id="a b"), dict(K, id="a" * 65), dict(K, id=None),
            dict(K, kaynak=""), dict(K, kaynak=" kaynak"), dict(K, kaynak="kaynak "), dict(K, kaynak="a" * 121), dict(K, kaynak=None),
            dict(K, surum=0), dict(K, surum=-1), dict(K, surum=True), dict(K, surum=1.0), dict(K, surum=None),
            dict(K, donusumler=None), dict(K, donusumler={}), dict(K, donusumler=[""]), dict(K, donusumler=[" temizle"]),
            dict(K, donusumler=["temizle "]), dict(K, donusumler=["a" * 81]), dict(K, donusumler=[1]),
            dict(K, donusumler=["temizle", "temizle"]),
        ]:
            try:
                fn(kayit)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(kayit_kokeni_dogrula), "köken şeması, dönüşüm sırası ve kopya korunmalı")
def m_surum(kayit):
    return kayit_kokeni_dogrula(dict(kayit, surum=0))
def m_donusum(kayit):
    return kayit_kokeni_dogrula(dict(kayit, donusumler=[]))
def m_kaynak(kayit):
    return kayit_kokeni_dogrula(dict(kayit, kaynak=""))
for ad, mutant in [("sürümü silen", m_surum), ("dönüşümleri silen", m_donusum), ("kaynağı silen", m_kaynak)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def kayit_kokeni_dogrula(kayit):
    import re
    if not isinstance(kayit, dict):
        raise ValueError("kayıt sözlük olmalı")
    if set(kayit) != {"id", "kaynak", "surum", "donusumler"}:
        raise ValueError("kayıt şeması geçersiz")
    if not isinstance(kayit["id"], str):
        raise ValueError("kimlik string olmalı")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
        raise ValueError("kimlik geçersiz")
    kaynak = kayit["kaynak"]
    if not isinstance(kaynak, str):
        raise ValueError("kaynak string olmalı")
    if not 1 <= len(kaynak) <= 120 or kaynak != kaynak.strip():
        raise ValueError("kaynak geçersiz")
    surum = kayit["surum"]
    if isinstance(surum, bool):
        raise ValueError("sürüm tamsayı olmalı")
    if not isinstance(surum, int):
        raise ValueError("sürüm tamsayı olmalı")
    if surum <= 0:
        raise ValueError("sürüm pozitif olmalı")
    donusumler = kayit["donusumler"]
    if not isinstance(donusumler, list):
        raise ValueError("dönüşümler liste olmalı")
    for donusum in donusumler:
        if not isinstance(donusum, str):
            raise ValueError("dönüşüm string olmalı")
        if not 1 <= len(donusum) <= 80 or donusum != donusum.strip():
            raise ValueError("dönüşüm geçersiz")
    if len(set(donusumler)) != len(donusumler):
        raise ValueError("dönüşüm yinelenemez")
    return {"id": kayit["id"], "kaynak": kaynak, "surum": surum, "donusumler": list(donusumler)}
```

```hint
Dönüşüm listesini ayrıca doğrula ve `list(...)` ile kopyala. Kaynak ve dönüşüm metinlerinde `strip()` sonrası değişiklik olmamalı.
```
:::

::: gorev 2 · Dağılım sapmasını ölç
`dagilim_sapmasi(beklenen, gozlenen)` işlevini yaz. İki girdi de aynı anahtar kümesine sahip, boş olmayan sözlüktür. Anahtarlar boş olmayan string, değerler bool olmayan sonlu ve negatif olmayan sayılardır. Her dağılımın değer toplamı pozitif olmalıdır. Geçersiz veride `ValueError` yükselt ve girdileri değiştirme.

Her dağılımı kendi toplamına bölerek normalize et. `{"toplam_varyasyon":X,"en_sapkan_kategori":K,"maksimum_fark":X}` döndür. Toplam varyasyon mutlak olasılık farklarının toplamının yarısı; maksimum fark en büyük mutlak kategori farkıdır. En yüksek farkta eşitlik varsa alfabetik olarak küçük kategori seçilir. İki sayısal çıktıyı da altı ondalık basamağa yuvarla.

```starter
from ai_guvence_veri import json_yukle

def dagilim_sapmasi(beklenen, gozlenen):
    # KUSURLU BAŞLANGIÇ KODU: sayıları kendi toplamlarına bölmeden doğrudan ham farkları hesaplıyor!
    return {"toplam_varyasyon": 0.0, "en_sapkan_kategori": "", "maksimum_fark": 0.0}

ornek = json_yukle("veri/dagilim_ve_profil.json")
print("Örnek dağılım sapması:", dagilim_sapmasi(ornek["beklenen_dagilim"], ornek["gozlenen_dagilim"]))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-11")
```

```test
import copy
B = {"a": 50, "b": 50}
G = {"a": 75, "b": 25}
def sozlesme(fn):
    try:
        bonce = copy.deepcopy(B)
        gonce = copy.deepcopy(G)
        if fn(B, G) != {"toplam_varyasyon": 0.25, "en_sapkan_kategori": "a", "maksimum_fark": 0.25} or B != bonce or G != gonce:
            return False
        if fn({"a": 1, "b": 1}, {"a": 3, "b": 1}) != {"toplam_varyasyon": 0.25, "en_sapkan_kategori": "a", "maksimum_fark": 0.25}:
            return False
        if fn({"a": 1, "b": 1}, {"a": 1, "b": 1})["toplam_varyasyon"] != 0:
            return False
        if fn({"a": 1, "b": 0}, {"a": 0, "b": 1}) != {"toplam_varyasyon": 1.0, "en_sapkan_kategori": "a", "maksimum_fark": 1.0}:
            return False
        esit = fn({"a": 1, "b": 1, "c": 0}, {"a": 0, "b": 1, "c": 1})
        if esit["en_sapkan_kategori"] != "a" or esit["maksimum_fark"] != 0.5:
            return False
        yuvarla = fn({"a": 1, "b": 2}, {"a": 2, "b": 1})
        if yuvarla != {"toplam_varyasyon": 0.333333, "en_sapkan_kategori": "a", "maksimum_fark": 0.333333}:
            return False
        for beklenen, gozlenen in [
            (None, G), (B, None), (123, G), (B, 123), ({}, {}), ([], G), (B, []), ({}, G), (B, {}),
            ({"a": 1}, {"b": 1}), ({"": 1}, {"": 1}), ({1: 1}, {1: 1}),
            ({"a": True}, {"a": 1}), ({"a": "1"}, {"a": 1}), ({"a": float("nan")}, {"a": 1}),
            ({"a": float("inf")}, {"a": 1}), ({"a": -1}, {"a": 1}), ({"a": 0}, {"a": 1}),
            (B, {"a": True, "b": 1}), (B, {"a": "1", "b": 1}), (B, {"a": float("nan"), "b": 1}),
            (B, {"a": float("inf"), "b": 1}), (B, {"a": -1, "b": 1}), (B, {"a": 0, "b": 0}),
        ]:
            try:
                fn(beklenen, gozlenen)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(dagilim_sapmasi), "normalizasyon, toplam varyasyon ve kategori seçimi korunmalı")
def m_beklenen(beklenen, gozlenen):
    return dagilim_sapmasi({k: 1 for k in beklenen}, gozlenen)
def m_gozlenen(beklenen, gozlenen):
    return dagilim_sapmasi(beklenen, {k: 1 for k in gozlenen})
def m_anahtar(beklenen, gozlenen):
    return dagilim_sapmasi(beklenen, {"x": 1})
for ad, mutant in [("bekleneni silen", m_beklenen), ("gözleneni silen", m_gozlenen), ("kategorileri bozan", m_anahtar)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def dagilim_sapmasi(beklenen, gozlenen):
    import math
    if not isinstance(beklenen, dict):
        raise ValueError("dağılımlar sözlük olmalı")
    if not isinstance(gozlenen, dict):
        raise ValueError("dağılımlar sözlük olmalı")
    if not beklenen:
        raise ValueError("dağılımlar boş olamaz")
    if not gozlenen:
        raise ValueError("dağılımlar boş olamaz")
    if set(beklenen) != set(gozlenen):
        raise ValueError("kategori kümeleri uyuşmuyor")
    for dagilim in (beklenen, gozlenen):
        for kategori, deger in dagilim.items():
            if not isinstance(kategori, str) or not kategori:
                raise ValueError("kategori geçersiz")
            if isinstance(deger, bool):
                raise ValueError("değer sayı olmalı")
            if not isinstance(deger, (int, float)):
                raise ValueError("değer sayı olmalı")
            if not math.isfinite(deger):
                raise ValueError("değer sonlu olmalı")
            if deger < 0:
                raise ValueError("değer negatif olamaz")
        if sum(dagilim.values()) == 0:
            raise ValueError("dağılım toplamı pozitif olmalı")
    toplam_b = sum(beklenen.values())
    toplam_g = sum(gozlenen.values())
    farklar = {k: abs(beklenen[k] / toplam_b - gozlenen[k] / toplam_g) for k in sorted(beklenen)}
    en_kategori = max(farklar, key=lambda k: farklar[k])
    return {"toplam_varyasyon": round(0.5 * sum(farklar.values()), 6), "en_sapkan_kategori": en_kategori, "maksimum_fark": round(farklar[en_kategori], 6)}
```

```hint
Kategorileri sıralı gez ki eşitlikte `max` ilk küçük kategoriyi korusun. Farkları normalize edilmiş oranlardan üret.
```
:::

::: gorev 3 · Şüpheli kayıt profili üret
`supheli_kayit_profili(kayitlar, esik)` işlevini yaz. Kayıtlar boş olmayan listedir; her kayıt tam olarak `id`, `kaynak`, `sapma`, `etiket_degisti` alanlarını taşır. Kimlik ilk görevdeki biçimdedir ve yinelenemez. Kaynak başı ve sonu boşluk olmayan, 1–120 karakterlik stringdir. Sapma ve eşik bool olmayan sonlu sayı ve `[0,1]` aralığındadır. Etiket değişikliği bool olmalıdır. Geçersiz veride `ValueError` yükselt.

Bir kayıt `sapma >= esik` veya `etiket_degisti=True` ise şüphelidir. `{"supheli_sayisi":N,"supheli_idler":[ID,...],"supheli_orani":X,"kaynaklar":{KAYNAK:N,...}}` döndür. Kimlikleri sırala, oranı bütün kayıtlar üzerinden hesaplayıp altı ondalık basamağa yuvarla ve kaynak sayı sözlüğünü kaynak adına göre sıralı oluştur. Hiç şüpheli yoksa kimlik listesi ve kaynak sözlüğü boş, oran sıfır olur. Girdiyi değiştirme.

```starter
from ai_guvence_veri import json_yukle

def supheli_kayit_profili(kayitlar, esik):
    # KUSURLU BAŞLANGIÇ KODU: etiket_degisti bayrağını yok sayıp yalnız sapma >= esik koşuluna bakıyor!
    supheli = [x["id"] for x in (kayitlar or []) if isinstance(x, dict) and x.get("sapma", 0) >= esik]
    return {"supheli_sayisi": len(supheli), "supheli_idler": supheli, "supheli_orani": 0.0, "kaynaklar": {}}

ornek = json_yukle("veri/dagilim_ve_profil.json")
print("Örnek şüpheli profili:", supheli_kayit_profili(ornek["aday_kayitlar"], 0.5))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-11")
```

```test
import copy
K = [
    {"id": "r-1", "kaynak": "a", "sapma": 0.2, "etiket_degisti": False},
    {"id": "r-2", "kaynak": "b", "sapma": 0.8, "etiket_degisti": False},
    {"id": "r-3", "kaynak": "a", "sapma": 0.1, "etiket_degisti": True},
]
BEKLENEN = {"supheli_sayisi": 2, "supheli_idler": ["r-2", "r-3"], "supheli_orani": 0.666667, "kaynaklar": {"a": 1, "b": 1}}
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        if fn(K, 0.5) != BEKLENEN or K != once:
            return False
        esit = fn([K[0]], 0.2)
        if esit["supheli_idler"] != ["r-1"] or esit["supheli_orani"] != 1:
            return False
        temiz = fn([dict(K[0], sapma=0)], 1)
        if temiz != {"supheli_sayisi": 0, "supheli_idler": [], "supheli_orani": 0.0, "kaynaklar": {}}:
            return False
        sinir = fn([dict(K[0], sapma=0, etiket_degisti=True), dict(K[1], sapma=1)], 0)
        if sinir["supheli_sayisi"] != 2:
            return False
        dagilim = fn(K + [dict(K[1], id="r-4", kaynak="a", sapma=0.9)], 0.5)
        if dagilim["supheli_sayisi"] != 3 or dagilim["kaynaklar"] != {"a": 2, "b": 1}:
            return False
        uzun = fn([dict(K[0], kaynak="k" * 120, sapma=1)], 0.5)
        if uzun["kaynaklar"] != {"k" * 120: 1}:
            return False
        for kayitlar, esik in [
            (None, 0.5), (tuple(K), 0.5), (K, False), (K, None), ({}, 0.5), ([], 0.5), ([None], 0.5), ([dict(K[0], ek=1)], 0.5), ([dict(K[0], id=123)], 0.5), ([dict(K[0], kaynak=123)], 0.5),
            ([K[0], K[0]], 0.5), ([dict(K[0], id="a b")], 0.5), ([dict(K[0], id="a" * 65)], 0.5),
            ([dict(K[0], kaynak="")], 0.5), ([dict(K[0], kaynak=" a")], 0.5), ([dict(K[0], kaynak="a" * 121)], 0.5),
            ([dict(K[0], sapma=True)], 0.5), ([dict(K[0], sapma="0.2")], 0.5), ([dict(K[0], sapma=float("nan"))], 0.5),
            ([dict(K[0], sapma=float("inf"))], 0.5), ([dict(K[0], sapma=-0.1)], 0.5), ([dict(K[0], sapma=1.1)], 0.5),
            ([dict(K[0], etiket_degisti=1)], 0.5), ([dict(K[0], etiket_degisti="true")], 0.5),
            (K, True), (K, "0.5"), (K, float("nan")), (K, float("inf")), (K, -0.1), (K, 1.1),
        ]:
            try:
                fn(kayitlar, esik)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(supheli_kayit_profili), "eşik, etiket kanıtı, oran ve kaynak profili korunmalı")
def m_sapma(kayitlar, esik):
    return supheli_kayit_profili([dict(x, sapma=0) for x in kayitlar], esik)
def m_etiket(kayitlar, esik):
    return supheli_kayit_profili([dict(x, etiket_degisti=False) for x in kayitlar], esik)
def m_kaynak(kayitlar, esik):
    return supheli_kayit_profili([dict(x, kaynak="a") for x in kayitlar], esik)
for ad, mutant in [("sapmayı silen", m_sapma), ("etiketi silen", m_etiket), ("kaynakları birleştiren", m_kaynak)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def supheli_kayit_profili(kayitlar, esik):
    import math
    import re
    if not isinstance(kayitlar, list):
        raise ValueError("kayıtlar liste olmalı")
    if not kayitlar:
        raise ValueError("kayıtlar boş olamaz")
    if isinstance(esik, bool):
        raise ValueError("eşik sayı olmalı")
    if not isinstance(esik, (int, float)):
        raise ValueError("eşik sayı olmalı")
    if not math.isfinite(esik):
        raise ValueError("eşik sonlu olmalı")
    if esik < 0 or esik > 1:
        raise ValueError("eşik aralık dışında")
    idler = set()
    for kayit in kayitlar:
        if not isinstance(kayit, dict):
            raise ValueError("kayıt sözlük olmalı")
        if set(kayit) != {"id", "kaynak", "sapma", "etiket_degisti"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(kayit["id"], str):
            raise ValueError("kimlik string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
            raise ValueError("kimlik geçersiz")
        if kayit["id"] in idler:
            raise ValueError("kimlik yinelenemez")
        kaynak = kayit["kaynak"]
        if not isinstance(kaynak, str):
            raise ValueError("kaynak string olmalı")
        if not 1 <= len(kaynak) <= 120 or kaynak != kaynak.strip():
            raise ValueError("kaynak geçersiz")
        sapma = kayit["sapma"]
        if isinstance(sapma, bool):
            raise ValueError("sapma sayı olmalı")
        if not isinstance(sapma, (int, float)):
            raise ValueError("sapma sayı olmalı")
        if not math.isfinite(sapma):
            raise ValueError("sapma sonlu olmalı")
        if sapma < 0 or sapma > 1:
            raise ValueError("sapma aralık dışında")
        if not isinstance(kayit["etiket_degisti"], bool):
            raise ValueError("etiket değişikliği bool olmalı")
        idler.add(kayit["id"])
    supheli = [x for x in kayitlar if x["sapma"] >= esik or x["etiket_degisti"]]
    kaynaklar = {}
    for kaynak in sorted({x["kaynak"] for x in supheli}):
        kaynaklar[kaynak] = sum(1 for x in supheli if x["kaynak"] == kaynak)
    return {"supheli_sayisi": len(supheli), "supheli_idler": sorted(x["id"] for x in supheli), "supheli_orani": round(len(supheli) / len(kayitlar), 6), "kaynaklar": kaynaklar}
```

```hint
Şüpheli listeyi iki bağımsız kanıtla üret. Oranın paydası bütün kayıtlar, kaynak sayılarının evreni ise yalnız şüpheli listedir.
```
:::

::: anlat `scikit-learn` `LogisticRegression` olasılık sapmaları ile canlı veri kökeni ve şüpheli kayıt profili
Önceki görevlerde sentetik sözlükler üzerinde köken doğrulama, TVD dağılım sapması ve şüpheli kayıt profillemesini kurdun. Şimdi bu üç sözleşmeyi **`scikit-learn` (`LogisticRegression`) ile iki farklı veri kaynağından (`ic-telemetri` ve `dis-ortam-toplayici`) gelen örnekler üzerinde eğitilen canlı sınıflandırıcı** üzerinde çalıştıracaksın:

1. `telemetri-paket-11` köken kaydı `kayit_kokeni_dogrula` ile doğrulanır,
2. Eğitim kümesi ile dış kaynaktan gelen kaydırılmış denetim kümesi arasındaki sınıf dağılımı farkı `dagilim_sapmasi` ile ölçülür,
3. Modelin tahmin olasılıklarından hesaplanan sapmalar ($1 - P(y_{\text{atanan}} \mid x)$) ve etiket değişim izleri `supheli_kayit_profili` ile özetlenip kanıt dosyasına kaydedilir.
:::

::: gorev Gerçek deney · scikit-learn olasılık sapmaları ve kaynak profili denetimi
Önceki üç görevde yazdığın `kayit_kokeni_dogrula(kayit)`, `dagilim_sapmasi(beklenen, gozlenen)` ve `supheli_kayit_profili(kayitlar, esik)` işlevlerini burada birleştir.

```meta
motor: ai-gercek
gereksinim: torch
timeout: 180
```

```starter
import math
import re
import ai_lab
from sandbox import ai_gercek_ai_guvence_11 as L

def kayit_kokeni_dogrula(kayit):
    # KUSURLU BAŞLANGIÇ KODU: doğrulama yapmadan girdi sözlüğünü döndürüyor!
    return kayit

def dagilim_sapmasi(beklenen, gozlenen):
    # KUSURLU BAŞLANGIÇ KODU: normalizasyon yapmadan boş fark döndürüyor!
    return {"toplam_varyasyon": 0.0, "en_sapkan_kategori": "", "maksimum_fark": 0.0}

def supheli_kayit_profili(kayitlar, esik):
    # KUSURLU BAŞLANGIÇ KODU: etiket_degisti bayrağını incelemeden boş liste dönüyor!
    return {"supheli_sayisi": 0, "supheli_idler": [], "supheli_orani": 0.0, "kaynaklar": {}}

if ai_lab.CALISTIR:
    L.goster(kayit_kokeni_dogrula, dagilim_sapmasi, supheli_kayit_profili)
```

```test
import ast
import ai_lab
from sandbox import ai_gercek_ai_guvence_11 as L

checks = []
_base_ok = ok
def ok(kosul, mesaj):
    checks.append(bool(kosul))
    return _base_ok(kosul, mesaj)

for ad in ("kayit_kokeni_dogrula", "dagilim_sapmasi", "supheli_kayit_profili"):
    need(ad)

yasak = (
    "referans",
    "kayit_kokeni_dogrula_referans",
    "dagilim_sapmasi_referans",
    "supheli_kayit_profili_referans",
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

def _sozlesme_kontrol():
    try:
        K = {"id": "k-1", "kaynak": "ic", "surum": 1, "donusumler": ["temizle"]}
        if kayit_kokeni_dogrula(K) != K or kayit_kokeni_dogrula(K) is K:
            return False
        for bk in [None, dict(K, surum=0), dict(K, donusumler=["a", "a"])]:
            try:
                kayit_kokeni_dogrula(bk)
                return False
            except ValueError:
                pass
        if dagilim_sapmasi({"a": 5, "b": 5}, {"a": 8, "b": 2}) != {"toplam_varyasyon": 0.3, "en_sapkan_kategori": "a", "maksimum_fark": 0.3}:
            return False
        P = [{"id": "r-1", "kaynak": "a", "sapma": 0.8, "etiket_degisti": False}]
        if supheli_kayit_profili(P, 0.5) != {"supheli_sayisi": 1, "supheli_idler": ["r-1"], "supheli_orani": 1.0, "kaynaklar": {"a": 1}}:
            return False
        return True
    except Exception:
        return False

def _birim1(fn):
    import copy
    K = {"id": "ornek-1", "kaynak": "yerel-arşiv", "surum": 2, "donusumler": ["temizle", "normalize"]}
    def sozlesme(fn):
        try:
            once = copy.deepcopy(K)
            sonuc = fn(K)
            if sonuc != K or K != once or sonuc is K or sonuc["donusumler"] is K["donusumler"]:
                return False
            ham = {"id": "a" * 64, "kaynak": "k", "surum": 1, "donusumler": []}
            if fn(ham) != ham:
                return False
            sinir = {"id": "sinir", "kaynak": "k" * 120, "surum": 1, "donusumler": ["x", "y" * 80]}
            if fn(sinir) != sinir:
                return False
            for kayit in [
                None, [], dict(K, ek=1), dict(K, id=""), dict(K, id="a b"), dict(K, id="a" * 65), dict(K, id=None),
                dict(K, kaynak=""), dict(K, kaynak=" kaynak"), dict(K, kaynak="kaynak "), dict(K, kaynak="a" * 121), dict(K, kaynak=None),
                dict(K, surum=0), dict(K, surum=-1), dict(K, surum=True), dict(K, surum=1.0), dict(K, surum=None),
                dict(K, donusumler=None), dict(K, donusumler={}), dict(K, donusumler=[""]), dict(K, donusumler=[" temizle"]),
                dict(K, donusumler=["temizle "]), dict(K, donusumler=["a" * 81]), dict(K, donusumler=[1]),
                dict(K, donusumler=["temizle", "temizle"]),
            ]:
                try:
                    fn(kayit)
                    return False
                except ValueError:
                    pass
            return True
        except Exception:
            return False
    return sozlesme(fn)

def _birim2(fn):
    import copy
    B = {"a": 50, "b": 50}
    G = {"a": 75, "b": 25}
    def sozlesme(fn):
        try:
            bonce = copy.deepcopy(B)
            gonce = copy.deepcopy(G)
            if fn(B, G) != {"toplam_varyasyon": 0.25, "en_sapkan_kategori": "a", "maksimum_fark": 0.25} or B != bonce or G != gonce:
                return False
            if fn({"a": 1, "b": 1}, {"a": 3, "b": 1}) != {"toplam_varyasyon": 0.25, "en_sapkan_kategori": "a", "maksimum_fark": 0.25}:
                return False
            if fn({"a": 1, "b": 1}, {"a": 1, "b": 1})["toplam_varyasyon"] != 0:
                return False
            if fn({"a": 1, "b": 0}, {"a": 0, "b": 1}) != {"toplam_varyasyon": 1.0, "en_sapkan_kategori": "a", "maksimum_fark": 1.0}:
                return False
            esit = fn({"a": 1, "b": 1, "c": 0}, {"a": 0, "b": 1, "c": 1})
            if esit["en_sapkan_kategori"] != "a" or esit["maksimum_fark"] != 0.5:
                return False
            yuvarla = fn({"a": 1, "b": 2}, {"a": 2, "b": 1})
            if yuvarla != {"toplam_varyasyon": 0.333333, "en_sapkan_kategori": "a", "maksimum_fark": 0.333333}:
                return False
            for beklenen, gozlenen in [
                (None, G), (B, None), (123, G), (B, 123), ({}, {}), ([], G), (B, []), ({}, G), (B, {}),
                ({"a": 1}, {"b": 1}), ({"": 1}, {"": 1}), ({1: 1}, {1: 1}),
                ({"a": True}, {"a": 1}), ({"a": "1"}, {"a": 1}), ({"a": float("nan")}, {"a": 1}),
                ({"a": float("inf")}, {"a": 1}), ({"a": -1}, {"a": 1}), ({"a": 0}, {"a": 1}),
                (B, {"a": True, "b": 1}), (B, {"a": "1", "b": 1}), (B, {"a": float("nan"), "b": 1}),
                (B, {"a": float("inf"), "b": 1}), (B, {"a": -1, "b": 1}), (B, {"a": 0, "b": 0}),
            ]:
                try:
                    fn(beklenen, gozlenen)
                    return False
                except ValueError:
                    pass
            return True
        except Exception:
            return False
    return sozlesme(fn)

def _birim3(fn):
    import copy
    K = [
        {"id": "r-1", "kaynak": "a", "sapma": 0.2, "etiket_degisti": False},
        {"id": "r-2", "kaynak": "b", "sapma": 0.8, "etiket_degisti": False},
        {"id": "r-3", "kaynak": "a", "sapma": 0.1, "etiket_degisti": True},
    ]
    BEKLENEN = {"supheli_sayisi": 2, "supheli_idler": ["r-2", "r-3"], "supheli_orani": 0.666667, "kaynaklar": {"a": 1, "b": 1}}
    def sozlesme(fn):
        try:
            once = copy.deepcopy(K)
            if fn(K, 0.5) != BEKLENEN or K != once:
                return False
            esit = fn([K[0]], 0.2)
            if esit["supheli_idler"] != ["r-1"] or esit["supheli_orani"] != 1:
                return False
            temiz = fn([dict(K[0], sapma=0)], 1)
            if temiz != {"supheli_sayisi": 0, "supheli_idler": [], "supheli_orani": 0.0, "kaynaklar": {}}:
                return False
            sinir = fn([dict(K[0], sapma=0, etiket_degisti=True), dict(K[1], sapma=1)], 0)
            if sinir["supheli_sayisi"] != 2:
                return False
            dagilim = fn(K + [dict(K[1], id="r-4", kaynak="a", sapma=0.9)], 0.5)
            if dagilim["supheli_sayisi"] != 3 or dagilim["kaynaklar"] != {"a": 2, "b": 1}:
                return False
            uzun = fn([dict(K[0], kaynak="k" * 120, sapma=1)], 0.5)
            if uzun["kaynaklar"] != {"k" * 120: 1}:
                return False
            for kayitlar, esik in [
                (None, 0.5), (tuple(K), 0.5), (K, False), (K, None), ({}, 0.5), ([], 0.5), ([None], 0.5), ([dict(K[0], ek=1)], 0.5), ([dict(K[0], id=123)], 0.5), ([dict(K[0], kaynak=123)], 0.5),
                ([K[0], K[0]], 0.5), ([dict(K[0], id="a b")], 0.5), ([dict(K[0], id="a" * 65)], 0.5),
                ([dict(K[0], kaynak="")], 0.5), ([dict(K[0], kaynak=" a")], 0.5), ([dict(K[0], kaynak="a" * 121)], 0.5),
                ([dict(K[0], sapma=True)], 0.5), ([dict(K[0], sapma="0.2")], 0.5), ([dict(K[0], sapma=float("nan"))], 0.5),
                ([dict(K[0], sapma=float("inf"))], 0.5), ([dict(K[0], sapma=-0.1)], 0.5), ([dict(K[0], sapma=1.1)], 0.5),
                ([dict(K[0], etiket_degisti=1)], 0.5), ([dict(K[0], etiket_degisti="true")], 0.5),
                (K, True), (K, "0.5"), (K, float("nan")), (K, float("inf")), (K, -0.1), (K, 1.1),
            ]:
                try:
                    fn(kayitlar, esik)
                    return False
                except ValueError:
                    pass
            return True
        except Exception:
            return False
    return sozlesme(fn)

ok(_birim1(kayit_kokeni_dogrula), "kayit_kokeni_dogrula tam birim sözleşmesini geçmeli")
ok(_birim2(dagilim_sapmasi), "dagilim_sapmasi tam birim sözleşmesini geçmeli")
ok(_birim3(supheli_kayit_profili), "supheli_kayit_profili tam birim sözleşmesini geçmeli")
ok(_sozlesme_kontrol(), "kayit_kokeni_dogrula, dagilim_sapmasi ve supheli_kayit_profili sözleşme kontrollerini geçmeli")
if not all(checks):
    stop()

try:
    rapor = L.deney(kayit_kokeni_dogrula, dagilim_sapmasi, supheli_kayit_profili)
except ai_lab.GercekLabYok as e:
    ok(False, str(e))
    stop()
except Exception as e:
    ok(False, f"GERÇEK VERİ KÖKENİ DENEYİ YAPILAMADI: {type(e).__name__}: {e}")
    stop()

k = rapor["kontroller"]
ok(k["koken_uyumu"], f"kayit_kokeni_dogrula canlı köken kaydında referansla uyuşmalı: {rapor['koken']}")
ok(k["dagilim_sapmasi_uyumu"], f"dagilim_sapmasi canlı dağılım farkında referansla uyuşmalı: {rapor['dagilim_sapmasi']}")
ok(k["supheli_profil_uyumu"] and k["dis_kaynak_yakalandi"], f"supheli_kayit_profili canlı olasılık sapmalarında referansla uyuşmalı: {rapor['supheli_profili']}")

kabul = all(checks)
kanit_yolu = ai_lab.kanit_yaz("guvence-11-veri-kokeni", dict(rapor, kaynak="gercek", kabul=kabul))
o = rapor["ozet"]
print(f"GERÇEK VERİ KÖKENİ DENEYİ: sklearn={o['sklearn_surum']} tvd={o['toplam_varyasyon']} şüpheli={o['supheli_sayisi']} kanıt={kanit_yolu}")
```

```solution
import math
import re
import ai_lab
from sandbox import ai_gercek_ai_guvence_11 as L

def kayit_kokeni_dogrula(kayit):
    if not isinstance(kayit, dict) or set(kayit) != {"id", "kaynak", "surum", "donusumler"}:
        raise ValueError("kayıt şeması geçersiz")
    if not isinstance(kayit["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
        raise ValueError("kimlik geçersiz")
    kaynak = kayit["kaynak"]
    if not isinstance(kaynak, str) or not 1 <= len(kaynak) <= 120 or kaynak != kaynak.strip():
        raise ValueError("kaynak geçersiz")
    surum = kayit["surum"]
    if isinstance(surum, bool) or not isinstance(surum, int) or surum <= 0:
        raise ValueError("sürüm geçersiz")
    donusumler = kayit["donusumler"]
    if not isinstance(donusumler, list) or len(set(donusumler)) != len(donusumler):
        raise ValueError("dönüşümler geçersiz")
    for d in donusumler:
        if not isinstance(d, str) or not 1 <= len(d) <= 80 or d != d.strip():
            raise ValueError("dönüşüm öğesi geçersiz")
    return {"id": kayit["id"], "kaynak": kaynak, "surum": surum, "donusumler": list(donusumler)}

def dagilim_sapmasi(beklenen, gozlenen):
    if not isinstance(beklenen, dict) or not isinstance(gozlenen, dict) or not beklenen or set(beklenen) != set(gozlenen):
        raise ValueError("dağılımlar geçersiz")
    for dagilim in (beklenen, gozlenen):
        for k, v in dagilim.items():
            if not isinstance(k, str) or not k or isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
                raise ValueError("dağılım öğesi geçersiz")
        if sum(dagilim.values()) == 0:
            raise ValueError("toplam pozitif olmalı")
    tb = sum(beklenen.values())
    tg = sum(gozlenen.values())
    farklar = {k: abs(beklenen[k] / tb - gozlenen[k] / tg) for k in sorted(beklenen)}
    en_k = max(farklar, key=lambda k: farklar[k])
    return {"toplam_varyasyon": round(0.5 * sum(farklar.values()), 6), "en_sapkan_kategori": en_k, "maksimum_fark": round(farklar[en_k], 6)}

def supheli_kayit_profili(kayitlar, esik):
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar geçersiz")
    if isinstance(esik, bool) or not isinstance(esik, (int, float)) or not math.isfinite(esik) or esik < 0 or esik > 1:
        raise ValueError("eşik geçersiz")
    idler = set()
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"id", "kaynak", "sapma", "etiket_degisti"}:
            raise ValueError("şema geçersiz")
        if not isinstance(kayit["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]) or kayit["id"] in idler:
            raise ValueError("id geçersiz")
        kaynak = kayit["kaynak"]
        if not isinstance(kaynak, str) or not 1 <= len(kaynak) <= 120 or kaynak != kaynak.strip():
            raise ValueError("kaynak geçersiz")
        sapma = kayit["sapma"]
        if isinstance(sapma, bool) or not isinstance(sapma, (int, float)) or not math.isfinite(sapma) or sapma < 0 or sapma > 1:
            raise ValueError("sapma geçersiz")
        if not isinstance(kayit["etiket_degisti"], bool):
            raise ValueError("etiket_degisti geçersiz")
        idler.add(kayit["id"])
    supheli = [x for x in kayitlar if x["sapma"] >= esik or x["etiket_degisti"]]
    kaynaklar = {k: sum(1 for x in supheli if x["kaynak"] == k) for k in sorted({x["kaynak"] for x in supheli})}
    return {"supheli_sayisi": len(supheli), "supheli_idler": sorted(x["id"] for x in supheli), "supheli_orani": round(len(supheli) / len(kayitlar), 6), "kaynaklar": kaynaklar}

if ai_lab.CALISTIR:
    L.goster(kayit_kokeni_dogrula, dagilim_sapmasi, supheli_kayit_profili)
```

```hint
Önceki üç görevde yazdığın `kayit_kokeni_dogrula`, `dagilim_sapmasi` ve `supheli_kayit_profili` işlevlerini eksiksiz taşı; canlı deneyde `scikit-learn` `LogisticRegression` olasılık sapmalarıyla dış kaynak kayıtları yakalanır.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Veri soykütüğü (`data lineage`) (30 sn).** "Eğitime giren her kaydın kaynağı, sürümü ve tekrarsız dönüşüm zinciri doğrulanmadan zehirli bir örneğin hangi boru hattından sızdığı geriye doğru izlenemez."
2. **Toplam varyasyon uzaklığı (`TVD`) (35 sn).** "Farklı büyüklükteki veri paketlerini karşılaştırmak için kategori sayıları kendi toplamlarına bölünür ve $TVD = \frac{1}{2}\sum |p_i - q_i|$ ile $[0, 1]$ aralığında normalize sapma ölçülür."
3. **Çift kanıtlı şüpheli profili (30 sn).** "Yüksek model olasılık sapması (`sapma >= esik`) ve açık etiket değişimi (`etiket_degisti`) bağımsız kanıtlardır; şüpheli kayıtların kaynak bazında toplanması hangi dış toplayıcının risk ürettiğini gösterir."
4. **Soru (25 sn).** "Kriptografik imza olmadan yalnız JSON üstverisindeki `kaynak` ve `surum` alanlarına güvenmek tedarik zinciri saldırısında neden kırılır?"
:::
