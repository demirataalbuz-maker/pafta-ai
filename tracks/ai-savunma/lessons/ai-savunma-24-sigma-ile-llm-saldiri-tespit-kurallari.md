---
id: ai-savunma-24
title: Sigma ile LLM Saldırı Tespit Kuralları
summary: Injection, yetki ve şüpheli egress kurallarını doğrula; alan ve anahtar kelime eşleşmelerinden test edilebilir alarmlar üret; önce görünür Sigma YAML ve sentetik olaylarla, sonra pySigma ile ayrıştırılan kuralları yerel Ollama modelinin gerçek telemetrisinde sına.
esleme: ai-savunma-21, ai-savunma-25, ai-ile-guvenlik-11
timeout: 45
---

::: anlat Gerçek biçimi bil, sentetik temsili ayırt et: Sigma kuralı taşınabilir ve sınanabilir olmalıdır

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Sigma kuralı YAML'dır: `title`, UUID `id`, `level`, `logsource` (ürün/kategori), `detection` (seçim + `condition`) alanlarını taşır. pySigma kuralı ayrıştırıp doğrular, `sigma-cli` ise Elastic, Splunk veya başka bir arka uç için sorguya çevirir. | Görev 1–3: `veri/sigma/*.yml` içindeki **gerçek biçimli** Sigma kuralları, bunların ders şemasına çevrilmiş hâli `veri/kurallar.json` ve **sentetik** olaylar `veri/olaylar.json`. Son adım: kurulu **pySigma 2.0.1** gerçek Sigma YAML'ını ayrıştırır, kurulu yerel Ollama modeliyle yapılan gerçek etkileşimlerden olaylar üretilir. | Ders yalnız tek seçimli, `contains` tabanlı kuralları kendi eşleştiricisiyle değerlendirir. Sigma'nın tam koşul dilini (`1 of`, `not`, alan eşlemesi) ve Elastic'e dönüştürmeyi kapsamaz. Anahtar kelime kuralları gerçek saldırıların tamamını yakalamaz. |

> [!NOT]
> Görev 1–3 sentetik veriyle çalışır. Bu görevlerde model ve pySigma çağrılmaz, ancak `veri/sigma/` içindeki YAML dosyalarını açıp ders şemasıyla karşılaştırabilirsin. Son adımdaki **Gerçek deney** görevi kurulu pySigma'yı ve yerel Ollama modelini gerçekten çalıştırır; yeni paket veya model indirmez. Elastic ve `sigma-cli` bu derste çalıştırılmaz. `veri/` dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalanır; kopyada yaptığın değişiklik bir sonraki çalıştırmada sıfırlanır, **kalıcılık yoktur**. Kontrol bu dosyalardan ayrı, gizli verilerle sınar.

Sigma benzeri kurallar injection, yetki ihlali ve şüpheli egress olaylarını ortak bir biçimde tanımlar. Kuralın alanı, seviyesi, anahtar kelimeleri ve eşleşme koşulu açık olur. Elastic benzeri bir sisteme aktarılmadan önce pozitif ve negatif olaylarla sınanır.

**Sigma neden var?** Her SIEM'in kendi sorgu dili vardır (Elastic KQL/EQL, Splunk SPL, Sentinel KQL). Bir tespit kuralı bunlardan birine doğrudan yazılırsa başka sisteme taşınamaz ve gözden geçirilmesi zorlaşır. Sigma, kuralı araçtan bağımsız bir YAML olarak yazmayı ve sonra derleyiciyle hedef dile çevirmeyi sağlar. Böylece kural kod gibi sürüm kontrolüne girer, pozitif/negatif örneklerle test edilir ve gözden geçirilir. Dersteki çeviri tablosu şudur: `level: high` → `seviye: yuksek`, `logsource.category` → `alan`, `metin|contains` değerleri → `eslesmeler`, `|all` belirleyicisi varsa `kosul: tumu`, yoksa `herhangi`.
:::

::: anlat Alan eşleşmesi zorunlu, metin eşleşmesi büyük/küçük harfsizdir
Kural yalnız kendi alanındaki olaya uygulanır. `herhangi` koşulunda anahtar kelimelerden en az biri, `tumu` koşulunda tamamı metinde bulunur. Metin `casefold` ile normalize edilir; kurallardaki anahtar kelimeler küçük harfli olmak zorundadır.

Alarm seviyesi önceliği `kritik`, `yuksek`, `orta`, `dusuk` sırasıdır. Birden çok kural eşleşirse olay raporunda en yüksek seviye ve eşleşen bütün kural kimlikleri korunur.

**Çıktı nasıl okunur?** Bir alarm, kuralın metinde aradığı dizeyi bulduğunu söyler; saldırının gerçekleştiğini söylemez. `veri/olaylar.json` bu farkı bilerek gösterir:

- **Yanlış pozitif:** `e-08` bir destek kaydıdır. Kullanıcı uygulamanın verdiği "ignore previous" uyarısını alıntılar ve `yuksek` alarm üretir.
- **Yanlış negatif:** `e-03`, `e-04` ve `e-05` gerçek saldırılardır ama temiz geçer.
  - `e-03` Türkçe talimat ezmedir.
  - `e-04` metadata servisine `https://` ile gider. Egress kuralı `|all` ile hem `http://` hem `metadata` ister ve `https://` içinde `http://` dizesi yoktur.
  - `e-05` bulut metadata servisinin IP adresini (`169.254.169.254`) ve `meta-data` yazımını kullanır.

**Saldırgan bakışı:** Kuralın tam metnini bilmeyen saldırgan bile en bilinen kalıbın yakalandığını varsayar. Bu yüzden eş anlamlı ifade, başka dil, kodlama, farklı protokol ya da IP adresi dener. `|all` koşulu kuralı daraltır ve yanlış pozitifi azaltır, ama atlatmayı kolaylaştırır. `herhangi` koşulu ise genişletir, karşılığında gürültü artar. İyi bir kural seti bu dengeyi örnek olaylarla ölçer: her kuralın en az bir yakalaması gereken ve en az bir yakalamaması gereken olayı vardır.

**Savunucu tarafı ve sık tuzaklar:**

- **Alan kontrolü:** Alan uyuşmazsa metne hiç bakılmaz. `e-09` injection kalıbı taşır ama `yetki` alanındadır ve injection kuralı onu görmez. Bu bilinçli bir sınırdır: kural, beklediği log kaynağına uygulanır.
- **Büyük harf:** Büyük harfli anahtar kelime casefold edilmiş metinde asla bulunmaz ve kuralı sessizce öldürür. Doğrulama bu yüzden reddeder.
- **Kural kimliği:** Kimlik, alarmı kurala geri bağlar. Sigma kimliğin UUID olmasını zorunlu tutar; pySigma başka biçimi reddeder.
- **Alarm sonrası:** Alarm bir karar değil, inceleme başlangıcıdır. Yüksek seviyeli bir kuralın yanlış pozitifi sık ise analistler onu görmezden gelmeye başlar.
:::

::: tahmin Herhangi ve tümü koşullarını tahmin et
Üç çıktı satırını yaz:

```python
metin = "IGNORE previous instructions".casefold()
print("ignore" in metin)
print(all(x in metin for x in ["ignore", "previous"]))
print(any(x in metin for x in ["secret", "token"]))
```

???

```cikti
True
True
False
```

Metin eşleşmesinden önce alan eşleşmesi de sağlanmalıdır.
:::

::: gorev 1 · Sigma kuralını doğrula
`sigma_kural_dogrula(kural)` işlevini yaz. Kural tam olarak `id`, `baslik`, `seviye`, `alan`, `eslesmeler`, `kosul`, `aktif` alanlarını taşısın. Kimlik 1–64 karakterlik, ASCII harf/rakamla başlayan ve yalnız ASCII harf, rakam, alt çizgi veya tire içeren stringdir.

Başlık başı/sonu boşluğu olmayan boş olmayan stringdir. Seviye `dusuk`, `orta`, `yuksek`, `kritik`; alan `injection`, `yetki`, `egress` olmalıdır. Eşleşmeler boş olmayan, yinelenmeyen listedir; her öğe küçük harfli, başı/sonu boşluğu olmayan boş olmayan stringdir ve kontrol karakteri içeremez. Koşul `herhangi` veya `tumu`, aktif gerçek `True` olmalıdır. Geçersiz veride `ValueError` yükselt.

Kuralı yeni listeyle döndür; girdiyi değiştirme.

Görünür veri: `veri/kurallar.json` ve kaynağı `veri/sigma/llm_injection.yml`. Başlangıç kodu önce YAML'ın ilk satırlarını gösterir, sonra beş geçerli ve dört bozuk kuralı doğrulamayı dener.

```starter
from pathlib import Path
from ai_savunma_veri import json_yukle

def sigma_kural_dogrula(kural):
    # KUSURLU BAŞLANGIÇ KODU: yalnız seviye ve alanı denetliyor; pasif kuralı, büyük harfli ve yinelenen eşleşmeyi kabul ediyor, girdinin kendisini döndürüyor!
    if kural.get("seviye") not in ("dusuk", "orta", "yuksek", "kritik"):
        raise ValueError("seviye geçersiz")
    return kural

print("".join(Path("veri/sigma/llm_injection.yml").read_text(encoding="utf-8").splitlines(True)[:14]))
veri = json_yukle("veri/kurallar.json")
for k in veri["kurallar"] + veri["bozuk_kurallar"]:
    try:
        sigma_kural_dogrula(k)
        print(k["id"], "kabul")
    except ValueError as hata:
        print(k["id"], "reddedildi:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-24")
```

```test
import copy
K = {"id": "r-injection", "baslik": "Injection işareti", "seviye": "yuksek", "alan": "injection", "eslesmeler": ["ignore previous", "system message"], "kosul": "herhangi", "aktif": True}
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        sonuc = fn(K)
        if sonuc != K or K != once or sonuc is K or sonuc["eslesmeler"] is K["eslesmeler"]:
            return False
        if fn(dict(K, id="a" * 64))["id"] != "a" * 64:
            return False
        if fn(dict(K, eslesmeler=["token"], kosul="tumu"))["kosul"] != "tumu":
            return False
        for kural in [
            None, [], dict(K, ek=1), dict(K, id=123), dict(K, id=""), dict(K, id="a b"), dict(K, id="a" * 65),
            dict(K, baslik=123), dict(K, baslik=""), dict(K, baslik=" x"), dict(K, seviye="bilinmeyen"), dict(K, alan="diger"),
            dict(K, eslesmeler=[]), dict(K, eslesmeler=None), dict(K, eslesmeler="ignore"), dict(K, eslesmeler=["token", "token"]),
            dict(K, eslesmeler=[123]), dict(K, eslesmeler=[""]), dict(K, eslesmeler=["TOKEN"]), dict(K, eslesmeler=[" token"]), dict(K, eslesmeler=["a\x1fb"]),
            dict(K, kosul="hicbiri"), dict(K, aktif=False), dict(K, aktif=1),
        ]:
            try:
                fn(kural)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(sigma_kural_dogrula), "kural kimliği, alan, seviye ve eşleşmeler korunmalı")
def m_alan(kural):
    sonuc = sigma_kural_dogrula(kural)
    sonuc["alan"] = "egress"
    return sonuc
def m_kosul(kural):
    return sigma_kural_dogrula(dict(kural, kosul="tumu"))
def m_aktif(kural):
    sonuc = sigma_kural_dogrula(kural)
    sonuc["aktif"] = False
    return sonuc
for ad, mutant in [("alanı değiştiren", m_alan), ("koşulu değiştiren", m_kosul), ("kuralı kapatan", m_aktif)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def sigma_kural_dogrula(kural):
    import re
    if not isinstance(kural, dict):
        raise ValueError("kural sözlük olmalı")
    if set(kural) != {"id", "baslik", "seviye", "alan", "eslesmeler", "kosul", "aktif"}:
        raise ValueError("kural şeması geçersiz")
    if not isinstance(kural["id"], str):
        raise ValueError("kimlik string olmalı")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kural["id"]):
        raise ValueError("kimlik geçersiz")
    if not isinstance(kural["baslik"], str):
        raise ValueError("başlık string olmalı")
    if not kural["baslik"] or kural["baslik"] != kural["baslik"].strip():
        raise ValueError("başlık geçersiz")
    if kural["seviye"] not in ("dusuk", "orta", "yuksek", "kritik"):
        raise ValueError("seviye geçersiz")
    if kural["alan"] not in ("injection", "yetki", "egress"):
        raise ValueError("alan geçersiz")
    eslesmeler = kural["eslesmeler"]
    if not isinstance(eslesmeler, list):
        raise ValueError("eşleşmeler liste olmalı")
    if not eslesmeler:
        raise ValueError("eşleşmeler boş olamaz")
    if len(set(eslesmeler)) != len(eslesmeler):
        raise ValueError("eşleşmeler yinelenemez")
    for eslesme in eslesmeler:
        if not isinstance(eslesme, str):
            raise ValueError("eşleşme string olmalı")
        if not eslesme or eslesme != eslesme.strip():
            raise ValueError("eşleşme boşluk biçimi geçersiz")
        if eslesme.casefold() != eslesme:
            raise ValueError("eşleşme küçük harfli olmalı")
        if any(ord(karakter) < 32 for karakter in eslesme):
            raise ValueError("eşleşme kontrol karakteri içeremez")
    if kural["kosul"] not in ("herhangi", "tumu"):
        raise ValueError("koşul geçersiz")
    if kural["aktif"] is not True:
        raise ValueError("kural aktif olmalı")
    return {"id": kural["id"], "baslik": kural["baslik"], "seviye": kural["seviye"], "alan": kural["alan"], "eslesmeler": list(eslesmeler), "kosul": kural["kosul"], "aktif": True}
```

```hint
Liste ve metin kurallarını ayrı doğrula. Küçük harf koşulunu `casefold() != eslesme` ile denetle; aktif alanı `is not True` ile sınırla.
```
:::

::: anlat Eşleşmeler olay ve kural çifti olarak raporlanır
Her olay her kuralla karşılaştırılır. Alan uyuşmazsa metne bakılmaz. Alan uyuştuğunda koşula göre `any` veya `all` uygulanır. Eşleşen her çift için olay kimliği, kural kimliği ve kuralın seviyesi döndürülür.

Olay kimliği ve kural kimliği kendi listelerinde benzersizdir. Boş olay veya boş kural listesi boş sonuç üretir; bu durum alarm değildir.
:::

::: gorev 2 · Sigma olay ve kurallarını eşleştir
`sigma_eslesmeleri(olaylar, kurallar)` işlevini yaz. Kurallar liste olmalı; her kural ilk görevdeki bütün kuralları sağlamalı ve kural kimlikleri benzersiz olmalıdır. Olaylar liste; her kayıt tam olarak `id`, `alan`, `metin` alanlarını taşısın. Olay kimliği ilk görevdeki desene uyan benzersiz string, alan `injection`, `yetki`, `egress` olmalıdır.

Metin başı/sonu boşluğu olmayan boş olmayan stringdir ve kontrol karakteri içeremez. Geçersiz veride `ValueError` yükselt. Eşleşen her çift için `{"olay_id":OLAY,"kural_id":KURAL,"seviye":SEVIYE}` döndür. Önce olay, sonra kural kimliğine göre sırala ve girdileri değiştirme.

Görünür veri: `veri/kurallar.json` ve `veri/olaylar.json`. `e-02` iki kuralla eşleşir. `e-09`'un metni injection kalıbı taşır ama alanı `yetki` olduğu için eşleşmemelidir.

```starter
from ai_savunma_veri import json_yukle

def sigma_eslesmeleri(olaylar, kurallar):
    # KUSURLU BAŞLANGIÇ KODU: alanı denetlemiyor, metni casefold etmiyor ve "tumu" koşulunu da "herhangi" gibi uyguluyor!
    sonuc = []
    for o in olaylar:
        for k in kurallar:
            if any(x in o["metin"] for x in k["eslesmeler"]):
                sonuc.append({"olay_id": o["id"], "kural_id": k["id"], "seviye": k["seviye"]})
    return sorted(sonuc, key=lambda x: (x["olay_id"], x["kural_id"]))

kurallar = json_yukle("veri/kurallar.json")["kurallar"]
veri = json_yukle("veri/olaylar.json")
for e in sigma_eslesmeleri(veri["olaylar"], kurallar):
    print(e["olay_id"], "→", e["kural_id"][-2:], e["seviye"])
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-24")
```

```test
import copy
R = [
    {"id": "r-injection", "baslik": "Injection", "seviye": "yuksek", "alan": "injection", "eslesmeler": ["ignore previous", "system message"], "kosul": "herhangi", "aktif": True},
    {"id": "r-egress", "baslik": "Egress", "seviye": "kritik", "alan": "egress", "eslesmeler": ["https://", "gizli"], "kosul": "tumu", "aktif": True},
]
O = [
    {"id": "o-1", "alan": "injection", "metin": "IGNORE PREVIOUS instructions"},
    {"id": "o-2", "alan": "egress", "metin": "https://ornek.test gizli"},
    {"id": "o-3", "alan": "injection", "metin": "System message"},
    {"id": "o-4", "alan": "yetki", "metin": "ignore previous"},
]
BEKLENEN = [
    {"olay_id": "o-1", "kural_id": "r-injection", "seviye": "yuksek"},
    {"olay_id": "o-2", "kural_id": "r-egress", "seviye": "kritik"},
    {"olay_id": "o-3", "kural_id": "r-injection", "seviye": "yuksek"},
]
def sozlesme(fn):
    try:
        oonce = copy.deepcopy(O)
        ronce = copy.deepcopy(R)
        if fn(O, R) != BEKLENEN or O != oonce or R != ronce or fn(list(reversed(O)), R) != BEKLENEN:
            return False
        if fn([], R) != [] or fn(O, []) != []:
            return False
        if fn([dict(O[1], metin="https://ornek.test")], R) != [] or fn([{"id": "o-5", "alan": "injection", "metin": "temiz metin"}], R) != []:
            return False
        for olaylar, kurallar in [
            (None, R), ({}, R), ([None], R), (O, None), (O, {}), (O, [None]),
            ([dict(O[0], ek=1)], R), ([dict(O[0], id=123)], R), ([dict(O[0], id="a b")], R), ([dict(O[0], id="a" * 65)], R),
            ([O[0], O[0]], R), ([dict(O[0], alan="diger")], R), ([dict(O[0], metin=123)], R), ([dict(O[0], metin="")], R),
            ([dict(O[0], metin=" x")], R), ([dict(O[0], metin="a\x1fb")], R),
            (O, [dict(R[0], ek=1)]), (O, [dict(R[0], id=123)]), (O, [dict(R[0], id="a" * 65)]),
            (O, [dict(R[0], baslik=123)]), (O, [dict(R[0], baslik="")]), (O, [dict(R[0], baslik=" x")]),
            (O, [dict(R[0], seviye="x")]), ([], [dict(R[0], seviye="x")]), (O, [dict(R[0], alan="x")]), (O, [dict(R[0], aktif=False)]),
            (O, [dict(R[0], eslesmeler=[])]), (O, [dict(R[0], eslesmeler="ignore")]), (O, [dict(R[0], eslesmeler=["x", "x"])]),
            (O, [dict(R[0], eslesmeler=[123])]), (O, [dict(R[0], eslesmeler=[""])]), (O, [dict(R[0], eslesmeler=[" x"])]),
            (O, [dict(R[0], eslesmeler=["X"])]), (O, [dict(R[0], eslesmeler=["a\x1fb"])]),
            (O, [dict(R[0], kosul="hicbiri")]), (O, [R[0], R[0]]),
        ]:
            try:
                fn(olaylar, kurallar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(sigma_eslesmeleri), "alan, koşul, metin ve çift sıralaması korunmalı")
def m_alan(olaylar, kurallar):
    return sigma_eslesmeleri([dict(x, alan="injection") for x in olaylar], kurallar)
def m_kosul(olaylar, kurallar):
    return sigma_eslesmeleri(olaylar, [dict(x, kosul="herhangi") for x in kurallar])
def m_metin(olaylar, kurallar):
    return sigma_eslesmeleri([dict(x, metin="temiz") for x in olaylar], kurallar)
for ad, mutant in [("alanı değiştiren", m_alan), ("koşulu açan", m_kosul), ("metni silen", m_metin)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def sigma_eslesmeleri(olaylar, kurallar):
    import re
    if not isinstance(kurallar, list):
        raise ValueError("kurallar liste olmalı")
    kural_ids = set()
    for kural in kurallar:
        if not isinstance(kural, dict):
            raise ValueError("kural sözlük olmalı")
        if set(kural) != {"id", "baslik", "seviye", "alan", "eslesmeler", "kosul", "aktif"}:
            raise ValueError("kural şeması geçersiz")
        if not isinstance(kural["id"], str):
            raise ValueError("kural kimliği string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kural["id"]):
            raise ValueError("kural kimliği geçersiz")
        if kural["id"] in kural_ids:
            raise ValueError("kural kimliği yinelenemez")
        kural_ids.add(kural["id"])
        if not isinstance(kural["baslik"], str):
            raise ValueError("başlık string olmalı")
        if not kural["baslik"]:
            raise ValueError("başlık boş olamaz")
        if kural["baslik"] != kural["baslik"].strip():
            raise ValueError("başlık boşluk biçimi geçersiz")
        if kural["seviye"] not in ("dusuk", "orta", "yuksek", "kritik"):
            raise ValueError("seviye geçersiz")
        if kural["alan"] not in ("injection", "yetki", "egress"):
            raise ValueError("alan geçersiz")
        eslesmeler = kural["eslesmeler"]
        if not isinstance(eslesmeler, list):
            raise ValueError("eşleşmeler liste olmalı")
        if not eslesmeler:
            raise ValueError("eşleşmeler boş olamaz")
        if len(set(eslesmeler)) != len(eslesmeler):
            raise ValueError("eşleşmeler yinelenemez")
        for eslesme in eslesmeler:
            if not isinstance(eslesme, str):
                raise ValueError("eşleşme string olmalı")
            if not eslesme:
                raise ValueError("eşleşme boş olamaz")
            if eslesme != eslesme.strip():
                raise ValueError("eşleşme boşluk biçimi geçersiz")
            if eslesme.casefold() != eslesme:
                raise ValueError("eşleşme küçük harfli olmalı")
            if any(ord(k) < 32 for k in eslesme):
                raise ValueError("eşleşme kontrol karakteri içeremez")
        if kural["kosul"] not in ("herhangi", "tumu"):
            raise ValueError("koşul geçersiz")
        if kural["aktif"] is not True:
            raise ValueError("kural aktif olmalı")
    if not isinstance(olaylar, list):
        raise ValueError("olaylar liste olmalı")
    olay_ids = set()
    for olay in olaylar:
        if not isinstance(olay, dict):
            raise ValueError("olay sözlük olmalı")
        if set(olay) != {"id", "alan", "metin"}:
            raise ValueError("olay şeması geçersiz")
        if not isinstance(olay["id"], str):
            raise ValueError("olay kimliği string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", olay["id"]):
            raise ValueError("olay kimliği geçersiz")
        if olay["id"] in olay_ids:
            raise ValueError("olay kimliği yinelenemez")
        olay_ids.add(olay["id"])
        if olay["alan"] not in ("injection", "yetki", "egress"):
            raise ValueError("olay alanı geçersiz")
        metin = olay["metin"]
        if not isinstance(metin, str):
            raise ValueError("metin string olmalı")
        if not metin:
            raise ValueError("metin boş olamaz")
        if metin != metin.strip():
            raise ValueError("metin boşluk biçimi geçersiz")
        if any(ord(k) < 32 for k in metin):
            raise ValueError("metin kontrol karakteri içeremez")
    sonuc = []
    for olay in olaylar:
        metin = olay["metin"].casefold()
        for kural in kurallar:
            if olay["alan"] != kural["alan"]:
                continue
            if kural["kosul"] == "herhangi":
                eslesti = any(x in metin for x in kural["eslesmeler"])
            else:
                eslesti = all(x in metin for x in kural["eslesmeler"])
            if eslesti:
                sonuc.append({"olay_id": olay["id"], "kural_id": kural["id"], "seviye": kural["seviye"]})
    return sorted(sonuc, key=lambda x: (x["olay_id"], x["kural_id"]))
```

```hint
Alan eşit değilse kuralı atla. Koşul `herhangi` ise `any`, `tumu` ise `all` kullan; sonuçları iki kimlikle sırala.
```
:::

::: anlat Olay raporu en yüksek alarm seviyesini seçer
Eşleşen kurallar aynı olayda birleştirilir. Kural kimlikleri alfabetik sıralanır ve en yüksek seviye seçilir. Hiçbir kural eşleşmezse olay `temiz`, seviye `None` olur. Temiz olayın kural listesi boştur.

Bu rapor yalnız fixture kurallarının sonucudur. Temiz kararı, olayın her olası saldırıdan arındığını kanıtlamaz.
:::

::: gorev 3 · Olay bazında Sigma alarm raporu üret
`sigma_alarm_raporu(olaylar, kurallar)` işlevini yaz. Girdi ikinci görevdeki bütün kuralları sağlasın; geçersiz veride `ValueError` yükselt. Aynı alan, koşul ve metin eşleşme kurallarını uygula.

Her olay için `{"olay_id":ID,"karar":"alarm" if eslesmeler else "temiz","seviye":EN_YUKSEK_veya_None,"kural_ids":[...]}` döndür. Olay kimliğine göre sırala, boş olayda boş liste döndür ve girdileri değiştirme.

Görünür veri: aynı dosyalar. Doğru raporda `e-01`, `e-02`, `e-07` ve `e-08` için `yuksek`, `e-06` ve `e-10` için `kritik` alarm çıkar. `e-10`'da `orta` seviyeli kısaltıcı kuralı da eşleşir; seviye öncelik sırasıyla seçilmelidir, alfabetik sırayla değil. Diğerleri temiz kalır; bunlardan `e-03`, `e-04` ve `e-05` yanlış negatiftir.

```starter
from ai_savunma_veri import json_yukle

def sigma_alarm_raporu(olaylar, kurallar):
    # KUSURLU BAŞLANGIÇ KODU: seviyeyi alfabetik en büyük değerle seçiyor ("yuksek" > "kritik") ve olay bozuksa reddetmiyor!
    rapor = []
    for o in sorted(olaylar, key=lambda x: x["id"]):
        metin = o["metin"].casefold()
        eslesen = [k for k in kurallar if k["alan"] == o["alan"]
                   and (all if k["kosul"] == "tumu" else any)(x in metin for x in k["eslesmeler"])]
        rapor.append({"olay_id": o["id"], "karar": "alarm" if eslesen else "temiz",
                      "seviye": max((k["seviye"] for k in eslesen), default=None), "kural_ids": sorted(k["id"] for k in eslesen)})
    return rapor

kurallar = json_yukle("veri/kurallar.json")["kurallar"]
veri = json_yukle("veri/olaylar.json")
for r in sigma_alarm_raporu(veri["olaylar"], kurallar):
    print(r["olay_id"], r["karar"], r["seviye"], [x[-2:] for x in r["kural_ids"]])
for o in veri["bozuk_olaylar"]:
    try:
        sigma_alarm_raporu([o], kurallar)
        print(o["id"], "KABUL edildi (yanlış)")
    except ValueError as hata:
        print(o["id"], "reddedildi:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-24")
```

```test
import copy
R = [
    {"id": "r-kritik", "baslik": "Kritik", "seviye": "kritik", "alan": "injection", "eslesmeler": ["ignore"], "kosul": "herhangi", "aktif": True},
    {"id": "r-orta", "baslik": "Orta", "seviye": "orta", "alan": "injection", "eslesmeler": ["ignore", "previous"], "kosul": "tumu", "aktif": True},
    {"id": "r-dusuk", "baslik": "Düşük", "seviye": "dusuk", "alan": "egress", "eslesmeler": ["token"], "kosul": "herhangi", "aktif": True},
]
O = [
    {"id": "o-1", "alan": "injection", "metin": "IGNORE previous"},
    {"id": "o-2", "alan": "egress", "metin": "token"},
    {"id": "o-3", "alan": "yetki", "metin": "ignore previous"},
]
BEKLENEN = [
    {"olay_id": "o-1", "karar": "alarm", "seviye": "kritik", "kural_ids": ["r-kritik", "r-orta"]},
    {"olay_id": "o-2", "karar": "alarm", "seviye": "dusuk", "kural_ids": ["r-dusuk"]},
    {"olay_id": "o-3", "karar": "temiz", "seviye": None, "kural_ids": []},
]
def sozlesme(fn):
    try:
        oonce = copy.deepcopy(O)
        ronce = copy.deepcopy(R)
        if fn(O, R) != BEKLENEN or O != oonce or R != ronce or fn(list(reversed(O)), R) != BEKLENEN or fn([], R) != []:
            return False
        if [x["karar"] for x in fn(O, [])] != ["temiz", "temiz", "temiz"]:
            return False
        if fn([dict(O[0], metin="ignore")], R)[0]["kural_ids"] != ["r-kritik"]:
            return False
        if fn([O[0]], [dict(R[0], eslesmeler=["ignore", "yok"], kosul="herhangi")])[0]["kural_ids"] != ["r-kritik"]:
            return False
        if fn([O[0]], [dict(R[0], eslesmeler=["ignore previous"], kosul="tumu")])[0]["kural_ids"] != ["r-kritik"]:
            return False
        for olaylar, kurallar in [
            (None, R), ({}, R), ([None], R), (O, None), (O, {}), (O, [None]),
            ([dict(O[0], ek=1)], R), ([dict(O[0], id=123)], R), ([dict(O[0], id="a b")], R), ([dict(O[0], id="a" * 65)], R), ([O[0], O[0]], R),
            ([dict(O[0], alan="diger")], R), ([dict(O[0], metin=123)], R), ([dict(O[0], metin="")], R), ([dict(O[0], metin=" x")], R), ([dict(O[0], metin="a\x1fb")], R),
            (O, [dict(R[0], ek=1)]), (O, [dict(R[0], id=123)]), (O, [dict(R[0], id="a" * 65)]),
            (O, [dict(R[0], baslik=123)]), (O, [dict(R[0], baslik="")]), (O, [dict(R[0], baslik=" x")]),
            (O, [dict(R[0], seviye="x")]), ([], [dict(R[0], seviye="x")]), (O, [dict(R[0], alan="x")]), (O, [dict(R[0], aktif=False)]),
            (O, [dict(R[0], eslesmeler=[])]), (O, [dict(R[0], eslesmeler="ignore")]), (O, [dict(R[0], eslesmeler=["x", "x"])]),
            (O, [dict(R[0], eslesmeler=[123])]), (O, [dict(R[0], eslesmeler=[""])]), (O, [dict(R[0], eslesmeler=[" x"])]),
            (O, [dict(R[0], eslesmeler=["X"])]), (O, [dict(R[0], eslesmeler=["a\x1fb"])]),
            (O, [dict(R[0], kosul="hicbiri")]), (O, [R[0], R[0]]),
        ]:
            try:
                fn(olaylar, kurallar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(sigma_alarm_raporu), "alarm, en yüksek seviye ve kural listesi korunmalı")
def m_seviye(olaylar, kurallar):
    return sigma_alarm_raporu(olaylar, [dict(x, seviye="dusuk") for x in kurallar])
def m_kural(olaylar, kurallar):
    return sigma_alarm_raporu(olaylar, kurallar[:1])
def m_alan(olaylar, kurallar):
    return sigma_alarm_raporu([dict(x, alan="injection") for x in olaylar], kurallar)
for ad, mutant in [("seviyeyi düşüren", m_seviye), ("kuralları silen", m_kural), ("alanı değiştiren", m_alan)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def sigma_alarm_raporu(olaylar, kurallar):
    import re
    if not isinstance(kurallar, list):
        raise ValueError("kurallar liste olmalı")
    kural_ids = set()
    for kural in kurallar:
        if not isinstance(kural, dict):
            raise ValueError("kural sözlük olmalı")
        if set(kural) != {"id", "baslik", "seviye", "alan", "eslesmeler", "kosul", "aktif"}:
            raise ValueError("kural şeması geçersiz")
        if not isinstance(kural["id"], str):
            raise ValueError("kural kimliği string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kural["id"]):
            raise ValueError("kural kimliği geçersiz")
        if kural["id"] in kural_ids:
            raise ValueError("kural kimliği yinelenemez")
        kural_ids.add(kural["id"])
        if not isinstance(kural["baslik"], str):
            raise ValueError("başlık string olmalı")
        if not kural["baslik"]:
            raise ValueError("başlık boş olamaz")
        if kural["baslik"] != kural["baslik"].strip():
            raise ValueError("başlık boşluk biçimi geçersiz")
        if kural["seviye"] not in ("dusuk", "orta", "yuksek", "kritik"):
            raise ValueError("seviye geçersiz")
        if kural["alan"] not in ("injection", "yetki", "egress"):
            raise ValueError("alan geçersiz")
        eslesmeler = kural["eslesmeler"]
        if not isinstance(eslesmeler, list):
            raise ValueError("eşleşmeler liste olmalı")
        if not eslesmeler:
            raise ValueError("eşleşmeler boş olamaz")
        if len(set(eslesmeler)) != len(eslesmeler):
            raise ValueError("eşleşmeler yinelenemez")
        for eslesme in eslesmeler:
            if not isinstance(eslesme, str):
                raise ValueError("eşleşme string olmalı")
            if not eslesme:
                raise ValueError("eşleşme boş olamaz")
            if eslesme != eslesme.strip():
                raise ValueError("eşleşme boşluk biçimi geçersiz")
            if eslesme.casefold() != eslesme:
                raise ValueError("eşleşme küçük harfli olmalı")
            if any(ord(k) < 32 for k in eslesme):
                raise ValueError("eşleşme kontrol karakteri içeremez")
        if kural["kosul"] not in ("herhangi", "tumu"):
            raise ValueError("koşul geçersiz")
        if kural["aktif"] is not True:
            raise ValueError("kural aktif olmalı")
    if not isinstance(olaylar, list):
        raise ValueError("olaylar liste olmalı")
    olay_ids = set()
    for olay in olaylar:
        if not isinstance(olay, dict):
            raise ValueError("olay sözlük olmalı")
        if set(olay) != {"id", "alan", "metin"}:
            raise ValueError("olay şeması geçersiz")
        if not isinstance(olay["id"], str):
            raise ValueError("olay kimliği string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", olay["id"]):
            raise ValueError("olay kimliği geçersiz")
        if olay["id"] in olay_ids:
            raise ValueError("olay kimliği yinelenemez")
        olay_ids.add(olay["id"])
        if olay["alan"] not in ("injection", "yetki", "egress"):
            raise ValueError("olay alanı geçersiz")
        metin = olay["metin"]
        if not isinstance(metin, str):
            raise ValueError("metin string olmalı")
        if not metin:
            raise ValueError("metin boş olamaz")
        if metin != metin.strip():
            raise ValueError("metin boşluk biçimi geçersiz")
        if any(ord(k) < 32 for k in metin):
            raise ValueError("metin kontrol karakteri içeremez")
    oncelik = ("dusuk", "orta", "yuksek", "kritik")
    sonuc = []
    for olay in olaylar:
        metin = olay["metin"].casefold()
        eslesen = []
        for kural in kurallar:
            if olay["alan"] != kural["alan"]:
                continue
            if kural["kosul"] == "herhangi":
                eslesti = any(x in metin for x in kural["eslesmeler"])
            else:
                eslesti = all(x in metin for x in kural["eslesmeler"])
            if eslesti:
                eslesen.append(kural)
        if eslesen:
            karar = "alarm"
            seviye = max((x["seviye"] for x in eslesen), key=oncelik.index)
        else:
            karar = "temiz"
            seviye = None
        sonuc.append({"olay_id": olay["id"], "karar": karar, "seviye": seviye, "kural_ids": sorted(x["id"] for x in eslesen)})
    return sorted(sonuc, key=lambda x: x["olay_id"])
```

```hint
Her olayda eşleşen kural nesnelerini topla. Seviyeyi öncelik sözlüğüyle `max` üzerinden seç; kural kimliklerini ayrı sırala.
```
:::

::: anlat Sigma kuralları gerçek etkileşim telemetrisinde test edilir
Görev 1–3'te kurallar hazır JSON'dan, olaylar elle yazılmış dosyadan geliyordu. Bu adımda ikisi de gerçek kaynaktan gelir. `sandbox/ai_gercek_ai_savunma_24.py` deneyi şunları yapar:

1. İki kurallık bir **Sigma YAML** metni kurulu **pySigma** ile (`SigmaCollection.from_yaml`) ayrıştırılır. Başlık, UUID, `level`, `logsource.category`, `|contains` değerleri ve `|all` belirleyicisi ders şemasına çevrilir. Karşılaştırma için belirleyici adı bozuk yazılmış (`|contians`) bir kural da pySigma'ya verilir. pySigma onu `SigmaModifierError` ile reddeder ve bu ret kanıta yazılır.
2. Kurulu yerel Ollama modeliyle üç gerçek etkileşim yapılır:
   - Bilinen bir enjeksiyon girdisi canary'li bir sistem istemiyle gönderilir. Girdi `o-girdi`, modelin **gerçek yanıtı** `o-yanit` olayı olur.
   - Modele bir `istek_at` aracı verilir ve metadata URL'sini önermesi istenir. Model aracı çağırırsa **önerdiği URL** `o-egress` olayı olur. Çağırmazsa egress olayı yazılmaz, uydurulmaz. URL'ye hiçbir istek gönderilmez.
   - Zararsız bir girdi `o-temiz` olayı olur.
3. Olaylar senin `sigma_alarm_raporu` işlevine pySigma'dan çevrilen kurallarla verilir.

Test önce işlevini gizli deterministik olay ve kurallarla sınar. Ardından şunları denetler: pySigma iki kuralı ayrıştırmış ve bozuk kuralı reddetmiş olmalı, raporun bağımsız referans hesapla birebir aynı olmalı. Girdi olayı deterministik olduğu için `yuksek` alarm almalı, zararsız girdi temiz kalmalı. Model aracı çağırdıysa egress olayı da kural gereği `kritik` alarm almalıdır. Modelin yanıtının alarm üretip üretmemesi kabul koşulu değildir. Yanıt girdiyi alıntılarsa bu bir yanlış pozitif olur ve doğru rapor onu da alarm sayar. Ham yanıtlar, araç çağrıları ve pySigma'nın ayrıştırdığı kural ayrıntıları kanıta yazılır.

Ders yazılırken bu makinede `qwen3:4b-instruct-2507` ile yapılan koşuda model aracı çağırdı ve URL'yi aynen önerdi; egress olayı `kritik` alarm aldı. Modelin enjeksiyon girdisine yanıtı kalıbı alıntılamadığı için temiz kaldı. Bu koşudaki egress kuralı yalnız `http://` dizesini arar. Model aynı adresi `https://` ile ya da IP adresiyle yazsaydı kural onu kaçırırdı; görünür verideki `e-04` ve `e-05` tam olarak bunu gösterir.

:::

::: gorev Gerçek deney · Sigma kurallarını gerçek telemetride test et
`sigma_alarm_raporu(olaylar, kurallar)` işlevini yaz. Kuralları ve çıktısı 3. görevdekiyle **aynıdır**. Deney Sigma YAML'ını pySigma ile ayrıştırır ve gerçek etkileşimlerden olaylar üretir: enjeksiyon girdisi, modelin gerçek yanıtı, modelin önerdiği URL ve zararsız girdi. Senin raporun bu gerçek içerikte alarm ya da temiz kararı verir. `sandbox.ai_gercek_ai_savunma_24` içindeki `sigma_alarm_raporu_referans` yalnız test içindir; onu import etmek veya kaynağını okuyup çalıştırmak Kontrol'de reddedilir.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab

def sigma_alarm_raporu(olaylar, kurallar):
    # KUSURLU BAŞLANGIÇ KODU: metni casefold etmiyor; büyük harfle başlayan "Ignore previous" girdisini kaçırıyor ve olay şemasını doğrulamıyor!
    rapor = []
    for o in sorted(olaylar, key=lambda x: x["id"]):
        metin = o["metin"]
        eslesen = [k for k in kurallar if k["alan"] == o["alan"]
                   and (all if k["kosul"] == "tumu" else any)(x in metin for x in k["eslesmeler"])]
        sira = {"dusuk": 0, "orta": 1, "yuksek": 2, "kritik": 3}
        rapor.append({"olay_id": o["id"], "karar": "alarm" if eslesen else "temiz",
                      "seviye": max((k["seviye"] for k in eslesen), key=lambda s: sira[s]) if eslesen else None,
                      "kural_ids": sorted(k["id"] for k in eslesen)})
    return rapor

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_24 as deney
    deney.goster(sigma_alarm_raporu)
```

```test
import ast
import ai_lab
from sandbox import ai_gercek_ai_savunma_24 as D
sonuclar = []
def kontrol(kosul, mesaj):
    sonuclar.append(bool(kosul))
    return ok(kosul, mesaj)
_yasak = ("sigma_alarm_raporu_referans", "kanit_yaz")
sorun = ai_lab.kod_denetimi(src, yasak=_yasak)
for n in ast.walk(ast.parse(src)):
    if isinstance(n, ast.ImportFrom) and any(a.name in _yasak or a.name == "*" for a in n.names):
        sorun.append("referans importu yasak")
    if isinstance(n, (ast.Import, ast.ImportFrom)):
        adlar = [a.name for a in n.names] + ([n.module] if isinstance(n, ast.ImportFrom) and n.module else [])
        if any(a and a.split(".")[0] in ("inspect", "importlib", "runpy") for a in adlar):
            sorun.append("kaynak okuma/dinamik import yasak")
    if isinstance(n, ast.Name) and n.id in ("exec", "eval", "compile", "__builtins__"):
        sorun.append("dinamik kod çalıştırma yasak: " + n.id)
if not kontrol(not sorun, "Kendi sigma_alarm_raporu işlevini yaz; laboratuvar/referans kullanımı yasak: " + "; ".join(sorted(set(sorun)))):
    stop()
fn = need("sigma_alarm_raporu")
R = [
    {"id": "r-injection", "baslik": "Injection", "seviye": "yuksek", "alan": "injection", "eslesmeler": ["ignore previous", "system message"], "kosul": "herhangi", "aktif": True},
    {"id": "r-egress", "baslik": "Egress", "seviye": "kritik", "alan": "egress", "eslesmeler": ["http://", "metadata"], "kosul": "tumu", "aktif": True},
]
O = [
    {"id": "o-1", "alan": "injection", "metin": "IGNORE PREVIOUS instructions"},
    {"id": "o-2", "alan": "egress", "metin": "http://metadata.google.internal/token"},
    {"id": "o-3", "alan": "injection", "metin": "temiz ozet"},
]
BEKLENEN = [
    {"olay_id": "o-1", "karar": "alarm", "seviye": "yuksek", "kural_ids": ["r-injection"]},
    {"olay_id": "o-2", "karar": "alarm", "seviye": "kritik", "kural_ids": ["r-egress"]},
    {"olay_id": "o-3", "karar": "temiz", "seviye": None, "kural_ids": []},
]
def sozlesme(f):
    try:
        if f(O, R) != BEKLENEN or f([], R) != [] or f(list(reversed(O)), R) != BEKLENEN:
            return False
        R2 = R + [dict(R[0], id="r-orta", seviye="orta", eslesmeler=["ignore previous", "secret"], kosul="tumu")]
        O2 = [{"id": "p-1", "alan": "injection", "metin": "ignore previous; SECRET"}, {"id": "p-2", "alan": "egress", "metin": "https://metadata"},
              {"id": "p-3", "alan": "yetki", "metin": "ignore previous"}, {"id": "p-4", "alan": "injection", "metin": "ignore previous"}]
        if f(O2, R2) != [{"olay_id": "p-1", "karar": "alarm", "seviye": "yuksek", "kural_ids": ["r-injection", "r-orta"]},
                         {"olay_id": "p-2", "karar": "temiz", "seviye": None, "kural_ids": []},
                         {"olay_id": "p-3", "karar": "temiz", "seviye": None, "kural_ids": []},
                         {"olay_id": "p-4", "karar": "alarm", "seviye": "yuksek", "kural_ids": ["r-injection"]}]:
            return False
        for bozuk in (None, {}, [None], [dict(O[0], ek=1)], [dict(O[0], id=123)], [dict(O[0], id="a b")], [dict(O[0], id="a" * 65)],
                      [dict(O[0], alan="diger")], [dict(O[0], metin=123)], [dict(O[0], metin="")],
                      [dict(O[0], metin=" x")], [dict(O[0], metin="a\x1fb")], [O[0], O[0]]):
            try:
                f(bozuk, R)
                return False
            except ValueError:
                pass
        for bozuk_k in (None, {}, [None], [dict(R[0], ek=1)], [dict(R[0], id=123)], [dict(R[0], id="a b")], [dict(R[0], id="a" * 65)],
                        [dict(R[0], baslik=123)], [dict(R[0], baslik="")], [dict(R[0], baslik=" x")],
                        [dict(R[0], seviye="x")], [dict(R[0], alan="x")], [dict(R[0], aktif=False)], [dict(R[0], aktif=1)],
                        [dict(R[0], eslesmeler=[])], [dict(R[0], eslesmeler="ignore")], [dict(R[0], eslesmeler=["x", "x"])],
                        [dict(R[0], eslesmeler=[123])], [dict(R[0], eslesmeler=[""])], [dict(R[0], eslesmeler=[" x"])],
                        [dict(R[0], eslesmeler=["X"])], [dict(R[0], eslesmeler=["a\x1fb"])], [dict(R[0], kosul="hicbiri")], [R[0], R[0]]):
            try:
                f(O, bozuk_k)
                return False
            except ValueError:
                pass
        try:
            f([], [dict(R[0], seviye="x")])
            return False
        except ValueError:
            pass
        return True
    except Exception:
        return False
kontrol(sozlesme(fn), "alan, koşul, seviye ve kural kimliği birleştirmesi korunmalı")
r, oz = None, None
if all(sonuclar):
    try:
        r = D.deney(fn)
    except ai_lab.GercekLabYok as e:
        kontrol(False, f"GERÇEK MODEL YOK, deney yapılmadı: {e}")
        stop()
    kontrol(len(r["kurallar"]) == 2 and r["bozuk_red"], f"pySigma iki gerçek Sigma kuralını ayrıştırdı ve bozuk belirleyiciyi reddetti: {r['bozuk_red']}")
    kontrol(r["kararlar"].get("o-girdi") == ("alarm", "yuksek"), "gerçek enjeksiyon girdisi yüksek alarm üretti")
    kontrol(r["kararlar"].get("o-temiz") == ("temiz", None), "zararsız girdi temiz kaldı")
    if r["onerilen_url"] and "http://" in r["onerilen_url"].casefold() and "metadata" in r["onerilen_url"].casefold():
        kontrol(r["kararlar"].get("o-egress") == ("alarm", "kritik"), f"modelin önerdiği URL kritik egress alarmı üretti: {r['onerilen_url']}")
    bagimsiz = D.sigma_alarm_raporu_referans([dict(o) for o in r["olaylar"]], [dict(k, eslesmeler=list(k["eslesmeler"])) for k in r["kurallar"]])
    kontrol(r["rapor"] == bagimsiz, f"gerçek olaylardaki rapor bağımsız hesapla aynı olmalı: senin {r['rapor']} · beklenen {bagimsiz}")
    oz = D.ozet(r)
yol = ai_lab.kanit_yaz("savunma-sigma", {"kaynak": "gercek", "kabul": all(sonuclar), "ders": "ai-savunma-24",
                                         "ortam": (r or {}).get("ortam"), "ozet": oz, "sigma": (r or {}).get("sigma_ham"),
                                         "olaylar": (r or {}).get("olaylar"), "ham_yanitlar": (r or {}).get("ham_yanitlar")})
if oz:
    ok(True, f"BULGU (pySigma {oz['pysigma']}, {r['ortam']['model']['ad']}): {oz['kural_sayisi']} Sigma kuralı ayrıştırıldı, bozuk kural reddedildi; "
             f"önerilen URL {oz['onerilen_url']!r}; kararlar {oz['kararlar']}. Ham yanıtlar ve kural ayrıntıları kanıtta.")
```

```solution
import ai_lab

def sigma_alarm_raporu(olaylar, kurallar):
    import re
    if not isinstance(kurallar, list):
        raise ValueError("kurallar liste olmalı")
    kural_ids = set()
    for kural in kurallar:
        if not isinstance(kural, dict):
            raise ValueError("kural sözlük olmalı")
        if set(kural) != {"id", "baslik", "seviye", "alan", "eslesmeler", "kosul", "aktif"}:
            raise ValueError("kural şeması geçersiz")
        if not isinstance(kural["id"], str):
            raise ValueError("kural kimliği string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kural["id"]):
            raise ValueError("kural kimliği geçersiz")
        if kural["id"] in kural_ids:
            raise ValueError("kural kimliği yinelenemez")
        kural_ids.add(kural["id"])
        if not isinstance(kural["baslik"], str):
            raise ValueError("başlık string olmalı")
        if not kural["baslik"]:
            raise ValueError("başlık boş olamaz")
        if kural["baslik"] != kural["baslik"].strip():
            raise ValueError("başlık boşluk biçimi geçersiz")
        if kural["seviye"] not in ("dusuk", "orta", "yuksek", "kritik"):
            raise ValueError("seviye geçersiz")
        if kural["alan"] not in ("injection", "yetki", "egress"):
            raise ValueError("alan geçersiz")
        eslesmeler = kural["eslesmeler"]
        if not isinstance(eslesmeler, list):
            raise ValueError("eşleşmeler liste olmalı")
        if not eslesmeler:
            raise ValueError("eşleşmeler boş olamaz")
        if len(set(eslesmeler)) != len(eslesmeler):
            raise ValueError("eşleşmeler yinelenemez")
        for eslesme in eslesmeler:
            if not isinstance(eslesme, str):
                raise ValueError("eşleşme string olmalı")
            if not eslesme:
                raise ValueError("eşleşme boş olamaz")
            if eslesme != eslesme.strip():
                raise ValueError("eşleşme boşluk biçimi geçersiz")
            if eslesme.casefold() != eslesme:
                raise ValueError("eşleşme küçük harfli olmalı")
            if any(ord(k) < 32 for k in eslesme):
                raise ValueError("eşleşme kontrol karakteri içeremez")
        if kural["kosul"] not in ("herhangi", "tumu"):
            raise ValueError("koşul geçersiz")
        if kural["aktif"] is not True:
            raise ValueError("kural aktif olmalı")
    if not isinstance(olaylar, list):
        raise ValueError("olaylar liste olmalı")
    olay_ids = set()
    for olay in olaylar:
        if not isinstance(olay, dict):
            raise ValueError("olay sözlük olmalı")
        if set(olay) != {"id", "alan", "metin"}:
            raise ValueError("olay şeması geçersiz")
        if not isinstance(olay["id"], str):
            raise ValueError("olay kimliği string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", olay["id"]):
            raise ValueError("olay kimliği geçersiz")
        if olay["id"] in olay_ids:
            raise ValueError("olay kimliği yinelenemez")
        olay_ids.add(olay["id"])
        if olay["alan"] not in ("injection", "yetki", "egress"):
            raise ValueError("olay alanı geçersiz")
        metin = olay["metin"]
        if not isinstance(metin, str):
            raise ValueError("metin string olmalı")
        if not metin:
            raise ValueError("metin boş olamaz")
        if metin != metin.strip():
            raise ValueError("metin boşluk biçimi geçersiz")
        if any(ord(k) < 32 for k in metin):
            raise ValueError("metin kontrol karakteri içeremez")
    oncelik = ("dusuk", "orta", "yuksek", "kritik")
    sonuc = []
    for olay in olaylar:
        metin = olay["metin"].casefold()
        eslesen = []
        for kural in kurallar:
            if olay["alan"] != kural["alan"]:
                continue
            if kural["kosul"] == "herhangi":
                eslesti = any(x in metin for x in kural["eslesmeler"])
            else:
                eslesti = all(x in metin for x in kural["eslesmeler"])
            if eslesti:
                eslesen.append(kural)
        if eslesen:
            karar = "alarm"
            seviye = max((x["seviye"] for x in eslesen), key=oncelik.index)
        else:
            karar = "temiz"
            seviye = None
        sonuc.append({"olay_id": olay["id"], "karar": karar, "seviye": seviye, "kural_ids": sorted(x["id"] for x in eslesen)})
    return sorted(sonuc, key=lambda x: x["olay_id"])

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_24 as deney
    deney.goster(sigma_alarm_raporu)
```

```hint
Bu işlev 3. görevdeki `sigma_alarm_raporu` ile birebir aynıdır; tek fark, kuralların pySigma ile gerçek Sigma YAML'ından ayrıştırılması ve olayların gerçek etkileşimlerden gelmesidir. Alan eşitliğini denetle; `herhangi`/`tumu` koşuluna göre eşleştir ve en yüksek seviyeyi seç.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Model telemetrisinde taşınabilir tespit (30 sn).** "LLM uygulamasının giriş (`injection`), araç çağrısı (`yetki`) ve dış ağ (`egress`) kayıtlarını yapılandırılmış olay olarak topladığımızda, taşınabilir Sigma YAML kuralları aynı mantığı farklı SIEM arka uçlarına taşır."
2. **Şema disiplini ve koşul semantiği (35 sn).** "Kural kimliği, seviye, alan ve küçük harfe normalize edilmiş eşleşme dizgeleri sıkı doğrulanmadan güvenilir alarm üretilemez; `herhangi` tek izle geniş yakalama sağlarken `tumu` birlikte görülmesi gereken sinyallerle yanlış alarmı kısar."
3. **Önceliklendirme ve sınır (30 sn).** "Aynı olay birden çok kuralı tetiklediğinde SOC kuyruğu en yüksek ciddiyet seviyesini (`kritik > yuksek > orta > dusuk`) ve sıralı kural kimliklerini görür; ancak düz alt-dizge kuralları kodlama ve yeniden ifadeyle atlatılabileceği için davranışsal kontrollerle desteklenmelidir."
4. **Soru (25 sn).** "Bir `egress` Sigma kuralında yalnız hedef alan adını aramak yerine hangi ek telemetri alanlarını koşula bağlamak veri sızıntısı tespitini güçlendirir?"
:::
