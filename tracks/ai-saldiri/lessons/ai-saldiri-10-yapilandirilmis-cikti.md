---
id: ai-saldiri-10
title: Yapılandırılmış Çıktı ve Ayrıştırıcı Atlatma
summary: Model çıktısındaki JSON'u katı biçimde ayrıştır, yinelenen anahtarları ve özel sayıları reddet, şema doğrulamasından sonra yalnız izinli iç komut üret.
timeout: 45
---

::: anlat Gerçek biçimi bil, sentetik temsili ayırt et: JSON'a benzemesi JSON sözleşmesini sağlamaz

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Gerçek bir uygulamada model yanıtı, Ollama `/api/chat` ya da bir bulut API'sinden `message.content` string'i olarak gelir. JSON modu veya şema kısıtlı çözümleme (`format`) açık olsa bile kod çiti, açıklama ya da yarım üretim (`done_reason: "length"`) görülebilir. Yanıt sonra bir ayrıştırıcıdan, şema doğrulayıcıdan (jsonschema, Pydantic) ve iş kuyruğuna yazan bir adaptörden geçer. | Görev 1–3: `veri/ham_yanitlar.json`, `veri/kararlar.json` ve `veri/komut_vakalari.json` içindeki **sentetik** ham metin ve kararlar. Son adım: görünür sentetik JSON dosyası, kurulu yerel Ollama modelinden iki canlı yanıt ve geçici bir SQLite kuyruğu. | Bir ayrıştırıcının doğru davranması, uygulamadaki öbür ayrıştırıcıların (JavaScript `JSON.parse`, Go, bir log işleyici) aynı belgeyi aynı okuduğunu göstermez. Modelin bozuk JSON üretip üretmeyeceği bu derste ölçülmez. İç komutlar yalnız veri etiketidir; gerçek özet ya da çeviri yapılmaz. |

> [!NOT]
> Görev 1–3 sentetik veriyle çalışır. Bu görevlerde model ve ağ yoktur. Son adımdaki **Gerçek deney** görevi yalnız kurulu yerel Ollama modelini ve deneyin kendi SQLite dosyasını kullanır. `veri/` dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalanır; kopyada yaptığın değişiklik bir sonraki çalıştırmada sıfırlanır, **kalıcılık yoktur**. Son adımın düzenlenebilir örnek dosyası ise ayrıca kalıcı tutulur. Kontrol bu dosyalardan ayrı, gizli verilerle sınar.

Modelden yapılandırılmış çıktı istemek, çıktının her zaman tek bir geçerli JSON belgesi olacağını garanti etmez. Kod çiti, açıklama, ek metin, yinelenen anahtar, yanlış tür veya `NaN` gibi standart dışı değerler görülebilir. Uygulama ile başka bir ayrıştırıcı bunları farklı yorumlarsa **parser differential** oluşur.

Bu derste dar bir sözleşme kullanıyoruz:

1. Girdi tek JSON belgesidir; başında ve sonunda yalnız whitespace olabilir.
2. Yinelenen object anahtarı kabul edilmez; son değeri sessizce kullanmayız.
3. `NaN`, `Infinity`, `-Infinity` kabul edilmez.
4. Ayrıştırmadan sonra alan adları ve türler ayrıca doğrulanır.
5. Doğrulanan eylem adı doğrudan fonksiyon veya araç adı olarak çalıştırılmaz; iç komut allowlist'inden geçer.

```python
import json
metin = '{"eylem":"ozetle","guvence":0.9}'
veri, bitis = json.JSONDecoder().raw_decode(metin)
print(veri["eylem"], bitis == len(metin))
print(json.loads('{"a":1,"a":2}'))
```

Son örnekte standart `json.loads` yinelenen anahtarda son değeri tutar. Bizim katı çözümümüz bunu hata yapacak. Görev 1–3 gerçek model çağırmaz; saldırı örnekleri zararsız metin fixture'larıdır. Son adım ise iki gerçek yerel model yanıtını aynı hattan geçirir.

**Görev 1'de sık tuzaklar:** Kod çitini ya da "İşte JSON:" önekini soyup devam etmek kolaylık gibi görünür. Ama aynı metni başka bir bileşen farklı okuyabilir; parser differential tam olarak budur (`veri/ham_yanitlar.json`, `h-02`, `h-03`). Ayrıştırma hatasında `None` döndürmek, çağıranın "boş karar" ile "geçersiz yanıt" arasındaki farkı görmesini engeller. `1e400` bir sabit değil, sayı belirtecidir; `parse_constant` onu yakalamaz ve sonuç `inf` olur (`h-12`). Bu yüzden sonluluk kontrolü şema katmanında da gerekir.
:::

::: tahmin
Katı ayrıştırıcı yinelenen anahtarı ve sondaki ek metni reddediyor. Üç çıktı satırını yaz:

```python
import json
ornekler = [
    '{"a":1}',
    '{"a":1,"a":2}',
    '{"a":1} ek',
]
for metin in ornekler:
    try:
        veri, bitis = json.JSONDecoder().raw_decode(metin)
        print(bitis == len(metin), veri)
    except json.JSONDecodeError:
        print("HATA")
print(json.loads('{"a":1,"a":2}'))
```

???

```cikti
True {'a': 1}
True {'a': 2}
False {'a': 1}
{'a': 2}
```

Standart ayrıştırıcı ikinci örnekte yinelenen anahtarın son değerini tutar; `raw_decode` ise sondaki `ek` metnini kendiliğinden tüketmez. Katı çözüm bu iki durumu ayrıca reddeder.
:::

::: gorev 1 · Tek ve katı JSON belgesi ayrıştır
`kati_json(metin)` işlevini yaz. Girdi string değilse veya boşsa `ValueError` yükselt. Baş ve sondaki whitespace'i kabul et; kod çiti veya başka ek metin kabul etme. `json.JSONDecoder.raw_decode` kullanarak tam belgeyi ayrıştır.

Bütün object düzeylerinde yinelenen anahtarı `ValueError` yap. `NaN`, `Infinity` ve `-Infinity` değerlerini de `ValueError` ile reddet. Geçerli JSON değerini dön; string, liste veya sayı gibi nesne olmayan kök değerler bu görevde kabul edilir. Ayrıştırma hatasını sahte boş değerle gizleme; `ValueError` olarak yükselt.

Görünür veri: `veri/ham_yanitlar.json`. Her örneğin `beklenen` alanı vardır; README tablosu nedenlerini açıklar.

```starter
import json
from ai_saldiri_veri import json_yukle

def kati_json(metin):
    # KUSURLU BAŞLANGIÇ KODU: kod çitini ve öndeki açıklamayı "akıllıca" soyuyor (başka bir ayrıştırıcı aynı metni farklı okur), json.loads kullanıyor (yinelenen anahtarda son değer kazanır, NaN/Infinity kabul edilir) ve ayrıştırma hatasını None ile gizliyor!
    kaynak = str(metin).strip()
    cit = "`" * 3
    if cit in kaynak:
        kaynak = kaynak.split(cit)[1].removeprefix("json").strip()
    elif "{" in kaynak:
        kaynak = kaynak[kaynak.index("{"):]
    try:
        return json.loads(kaynak)
    except json.JSONDecodeError:
        return None

veri = json_yukle("veri/ham_yanitlar.json")
for o in veri["ornekler"]:
    try:
        deger = kati_json(o["ham"])
        durum = {"kabul": True, "deger_repr": repr(deger)}
    except ValueError:
        durum = {"kabul": False}
    print(o["id"], "doğru" if durum == o["beklenen"] else "YANLIŞ", durum)
for b in veri["bozuk_girdiler"]:
    try:
        print(repr(b), "KABUL edildi (yanlış):", repr(kati_json(b)))
    except ValueError as hata:
        print(repr(b), "reddedildi:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-10")
```

```test
def sozlesme(fn):
    try:
        if fn(' {"a":1,"b":[true,null]} \n') != {"a": 1, "b": [True, None]}:
            return False
        if fn('"Pafta"') != "Pafta" or fn('[1,2]') != [1, 2] or fn('0') != 0:
            return False
        for metin in [
            '', '   ', '```json\n{"a":1}\n```', '{"a":1} ek', '{"a":1}{"b":2}',
            '{"a":1,"a":2}', '{"a":{"b":1,"b":2}}', '{"a":NaN}', '{"a":Infinity}', '{"a":-Infinity}',
            '{"a":}', '[1,2', None, 3,
        ]:
            try:
                fn(metin)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(kati_json), "tam tüketim, yinelenen anahtar, özel sayı ve tür denetimi korunmalı")
def m_loads(metin):
    import json
    return json.loads(metin)
def m_ilk(metin):
    import json
    return json.JSONDecoder().raw_decode(metin.strip())[0]
def m_sondan(metin):
    import json
    return json.loads(metin.split('```')[1])
for ad, mutant in [("yinelenen anahtarı ve NaN kabul eden", m_loads), ("sondaki metni yok sayan", m_ilk), ("kod çitini tahmin eden", m_sondan)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
import json

def kati_json(metin):
    if not isinstance(metin, str) or not metin.strip():
        raise ValueError("tek JSON belgesi gerekli")
    def nesne(parcalar):
        sonuc = {}
        for anahtar, deger in parcalar:
            if anahtar in sonuc:
                raise ValueError("yinelenen anahtar")
            sonuc[anahtar] = deger
        return sonuc
    def sabit(deger):
        raise ValueError("standart dışı sayı")
    decoder = json.JSONDecoder(object_pairs_hook=nesne, parse_constant=sabit)
    kaynak = metin.strip()
    try:
        veri, bitis = decoder.raw_decode(kaynak)
    except json.JSONDecodeError as e:
        raise ValueError("geçersiz JSON") from e
    if bitis != len(kaynak):
        raise ValueError("JSON sonrası ek içerik")
    return veri
```

```hint
`object_pairs_hook` her object için anahtar-değer çiftlerini verir; burada tekrar denetlenebilir. `raw_decode` dönüşündeki bitiş konumu temizlenmiş stringin uzunluğuna eşit olmalıdır.
```
:::

::: anlat Ayrıştırma ile yetkilendirme farklı katmanlardır
Geçerli JSON, güvenli komut demek değildir. `{"eylem":"dosya_sil"}` sözdizimsel olarak kusursuz olabilir; uygulama şemasında ve yetki politikasında yoksa reddedilir. Şema doğrulamasında ek alanları sessizce bırakmak da iki katmanın aynı belgeyi farklı görmesine yol açabilir. Bu derste tam anahtar kümesi zorunludur.

Python'da `bool`, `int` alt sınıfıdır. Bu yüzden güvence değeri `True` olduğunda `isinstance(deger, int)` kontrolü onu sayı sanabilir. Açık bool reddi ve sonlu sayı denetimi gerekir. Metin için otomatik `str(...)` dönüşümü, güvence için `float(...)` dönüşümü yapmayız; türü değiştirmek hatayı görünmez kılar.

**Sık tuzaklar:** `float(True)` sonucu `1.0`, `float("0.9")` sonucu `0.9` olur. İki bozuk değer de böylece geçerli bir güvenceye dönüşür (`veri/kararlar.json`, `k-02`, `k-03`). `Ozetle` gibi bir eylemi `lower()` ile kabul etmek, şemanın söylemediği bir normalleştirmedir (`k-08`). Ek `arac` alanını taşıyan nesneyi aynen döndürmek, bir sonraki katmanın o alanı okumasına kapı açar (`k-06`).
:::

::: gorev 2 · Karar şemasını türleri bozmadan doğrula
`karar_dogrula(veri)` işlevini yaz. Kök dict olmalı ve tam olarak `eylem`, `metin`, `guvence` anahtarlarını taşımalıdır.

- `eylem`: `ozetle`, `cevir` veya `yoksay`.
- `metin`: 1–120 karakterli string.
- `guvence`: bool olmayan `int` veya `float`; sonlu ve `0 <= guvence <= 1`.

Bütün kurallar sağlanırsa alanları aynı değerlerle taşıyan yeni dict dön; girdiyi değiştirme. Aksi durumda `ValueError` yükselt. Ek alan kabul etme, tür dönüşümü yapma.

Görünür veri: `veri/kararlar.json`. Her örneğin `beklenen_kabul` alanı vardır. Kabul edilen kararlarda girdi değişmemelidir.

```starter
import copy
from ai_saldiri_veri import json_yukle

def karar_dogrula(veri):
    # KUSURLU BAŞLANGIÇ KODU: ek alanları sessizce bırakıyor, eylemi lower() ile "düzeltiyor", float() ile True ve "0.9" değerlerini sayıya çeviriyor, metin türünü ve uzunluğunu denetlemiyor ve girdiyi yerinde değiştirip aynı nesneyi döndürüyor!
    eylem = str(veri["eylem"]).lower()
    if eylem not in ("ozetle", "cevir", "yoksay"):
        raise ValueError("eylem izinli değil")
    guvence = float(veri["guvence"])
    if not 0 <= guvence <= 1:
        raise ValueError("güvence 0..1 olmalı")
    veri["eylem"] = eylem
    veri["guvence"] = guvence
    return veri

veri = json_yukle("veri/kararlar.json")
for o in veri["ornekler"]:
    karar = copy.deepcopy(o["karar"])
    try:
        sonuc = karar_dogrula(karar)
        kabul = True
    except ValueError:
        sonuc, kabul = None, False
    notlar = []
    if kabul != o["beklenen_kabul"]:
        notlar.append("YANLIŞ")
    if karar != o["karar"]:
        notlar.append("girdi değişti")
    if kabul and sonuc is karar:
        notlar.append("aynı nesne döndü")
    print(o["id"], o["aciklama"], "kabul" if kabul else "red", " · ".join(notlar))
for b in veri["bozuk_girdiler"]:
    try:
        karar_dogrula(b)
        print(repr(b), "KABUL edildi (yanlış)")
    except ValueError as hata:
        print(repr(b), "reddedildi:", hata)
    except Exception as hata:
        print(repr(b), "ValueError yerine", type(hata).__name__, "(yanlış)")
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-10")
```

```test
import copy
KARAR = {"eylem": "ozetle", "metin": "Pafta", "guvence": 0.8}
def sozlesme(fn):
    try:
        once = copy.deepcopy(KARAR)
        sonuc = fn(KARAR)
        if sonuc != KARAR or sonuc is KARAR or KARAR != once:
            return False
        for deger in [
            {"eylem": "cevir", "metin": "a", "guvence": 0},
            {"eylem": "yoksay", "metin": "b" * 120, "guvence": 1},
        ]:
            if fn(deger) != deger:
                return False
        for deger in [
            None, [], dict(KARAR, ek=1), {"eylem": "ozetle", "metin": "x"},
            dict(KARAR, eylem="dosya_sil"), dict(KARAR, eylem=1),
            dict(KARAR, metin=""), dict(KARAR, metin="x" * 121), dict(KARAR, metin=3),
            dict(KARAR, guvence=True), dict(KARAR, guvence="0.8"),
            dict(KARAR, guvence=-0.1), dict(KARAR, guvence=1.1),
            dict(KARAR, guvence=float("nan")), dict(KARAR, guvence=float("inf")),
        ]:
            try:
                fn(deger)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(karar_dogrula), "tam şema, bool reddi, uzunluk ve sonlu aralık birlikte korunmalı")
def m_ek_alan(veri):
    return {k: veri[k] for k in ("eylem", "metin", "guvence") if k in veri}
def m_donustur(veri):
    return {"eylem": str(veri["eylem"]), "metin": str(veri["metin"]), "guvence": float(veri["guvence"])}
def m_bool(veri):
    sonuc = karar_dogrula(veri)
    return sonuc
for ad, mutant in [("ek alanı ve eksik şemayı kabul eden", m_ek_alan), ("türleri zorla dönüştüren", m_donustur)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
import math

def karar_dogrula(veri):
    if not isinstance(veri, dict) or set(veri) != {"eylem", "metin", "guvence"}:
        raise ValueError("karar şeması geçersiz")
    if veri["eylem"] not in ("ozetle", "cevir", "yoksay"):
        raise ValueError("eylem izinli değil")
    if not isinstance(veri["metin"], str) or not 1 <= len(veri["metin"]) <= 120:
        raise ValueError("metin 1..120 karakter olmalı")
    guvence = veri["guvence"]
    if isinstance(guvence, bool) or not isinstance(guvence, (int, float)):
        raise ValueError("güvence sayı olmalı")
    if not math.isfinite(guvence) or not 0 <= guvence <= 1:
        raise ValueError("güvence 0..1 olmalı")
    return {"eylem": veri["eylem"], "metin": veri["metin"], "guvence": guvence}
```

```hint
Önce dict ve tam anahtar kümesini denetle. `math.isfinite` ile `NaN`/sonsuzluğu ayır; güvence için `isinstance(guvence, bool)` kontrolünü sayı kontrolünden önce yap.
```
:::

::: anlat Modelin verdiği ad çalıştırılabilir adres değildir
`getattr(modul, veri["eylem"])` veya `eval` ile model çıktısını doğrudan çağırmak, şema doğrulamasını yetki sistemi sanmaktır. Uygulamanın desteklediği az sayıdaki iç komut açık eşleştirmeyle seçilir. Güvence eşiğinin altındaki karar da otomatik işlem yerine inceleme yoluna gider.

Bu derste iç komutlar `OZET`, `CEVIR`, `YOKSAY`, `INCELE`; bunlar yalnız veri etiketleridir, araç çağrısı değildir. Eşik `0.75`'tir. Eşik altında `INCELE` döner ve model metni komut kaydına taşınmaz. Bu eşik güvenlik garantisi değildir; yalnız fixture politikasının açık ve test edilebilir kuralıdır.

**Çıktı nasıl okunur?** `veri/komut_vakalari.json` içinde `c-01` tam `0.75` güvencededir ve `OZET` üretmelidir; `>` ile yazılan eşik onu incelemeye düşürür. `c-05` düşük güvencelidir. Metni (`GİZLİ NOT`) inceleme kaydına taşınmamalıdır. `c-06` ve `c-07` ise bilinmeyen eylem adlarının hiçbir koşulda komuta dönüşmediğini gösterir.
:::

::: gorev 3 · Doğrulanmış kararı izinli iç komuta çevir
`komut_uret(veri)` işlevini yaz. İkinci görevdeki şemayı bağımsız olarak doğrula. `eylem` eşleşmesi `ozetle → OZET`, `cevir → CEVIR`, `yoksay → YOKSAY` olsun.

`guvence >= 0.75` ise `{"komut": eslesen-komut, "icerik": metin}` dön. Daha düşük güvencede `{"komut": "INCELE", "icerik": ""}` dön. Başka eylem, ek alan, yanlış tür veya geçersiz güvence `ValueError` olmalı. `eval`, `exec`, `getattr` veya dinamik modül çağrısı kullanma; girdiyi değiştirme.

Görünür veri: `veri/komut_vakalari.json`. `beklenen: null`, `ValueError` demektir.

```starter
from ai_saldiri_veri import json_yukle

def komut_uret(veri):
    # KUSURLU BAŞLANGIÇ KODU: bilinmeyen eylem adını büyük harfe çevirip komut yapıyor (dosya_sil → DOSYA_SIL), eşiği > ile uyguluyor (tam 0.75 incelemeye düşer), düşük güvencede model metnini inceleme kaydına taşıyor ve şemayı hiç denetlemiyor!
    esleme = {"ozetle": "OZET", "cevir": "CEVIR", "yoksay": "YOKSAY"}
    if veri["guvence"] > 0.75:
        return {"komut": esleme.get(veri["eylem"], str(veri["eylem"]).upper()), "icerik": veri["metin"]}
    return {"komut": "INCELE", "icerik": veri["metin"]}

veri = json_yukle("veri/komut_vakalari.json")
for o in veri["ornekler"]:
    try:
        sonuc = komut_uret(dict(o["karar"]))
    except ValueError:
        sonuc = None
    print(o["id"], "doğru" if sonuc == o["beklenen"] else "YANLIŞ", sonuc, "" if sonuc == o["beklenen"] else "≠ " + str(o["beklenen"]))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-10")
```

```test
import copy
def sozlesme(fn):
    try:
        for veri, beklenen in [
            ({"eylem": "ozetle", "metin": "Pafta", "guvence": 0.75}, {"komut": "OZET", "icerik": "Pafta"}),
            ({"eylem": "cevir", "metin": "Merhaba", "guvence": 1}, {"komut": "CEVIR", "icerik": "Merhaba"}),
            ({"eylem": "cevir", "metin": "x", "guvence": 0}, {"komut": "INCELE", "icerik": ""}),
            ({"eylem": "cevir", "metin": "b" * 120, "guvence": 1}, {"komut": "CEVIR", "icerik": "b" * 120}),
            ({"eylem": "yoksay", "metin": "not", "guvence": 0.9}, {"komut": "YOKSAY", "icerik": "not"}),
            ({"eylem": "ozetle", "metin": "gizli", "guvence": 0.74}, {"komut": "INCELE", "icerik": ""}),
        ]:
            once = copy.deepcopy(veri)
            if fn(veri) != beklenen or veri != once:
                return False
        for veri in [
            None, [],
            {"eylem": "eval", "metin": "x", "guvence": 1},
            {"eylem": "ozetle", "metin": "x", "guvence": 1, "arac": "dosya_sil"},
            {"eylem": "ozetle", "metin": "x", "guvence": True},
            {"eylem": "ozetle", "metin": "x", "guvence": -0.1},
            {"eylem": "ozetle", "metin": "x", "guvence": 1.1},
            {"eylem": "ozetle", "metin": "x", "guvence": "0.8"},
            {"eylem": "ozetle", "metin": "x", "guvence": float("nan")},
            {"eylem": "ozetle", "metin": "x", "guvence": float("inf")},
            {"eylem": "ozetle", "metin": "", "guvence": 1},
            {"eylem": "ozetle", "metin": "x" * 121, "guvence": 1},
            {"eylem": "ozetle", "metin": 3, "guvence": 1},
        ]:
            try:
                fn(veri)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(komut_uret), "sabit eşleme, eşik sınırı, inceleme yolu ve şema korunmalı")
def m_dinamik(veri):
    return {"komut": veri["eylem"].upper(), "icerik": veri["metin"]}
def m_esik(veri):
    sonuc = komut_uret(veri)
    if sonuc["komut"] == "INCELE":
        sonuc = {"komut": "OZET", "icerik": veri["metin"]}
    return sonuc
def m_ek(veri):
    return {"komut": "OZET", "icerik": veri["metin"]}
for ad, mutant in [("model adını komut yapan", m_dinamik), ("düşük güvenceyi çalıştıran", m_esik), ("şemayı atlayan", m_ek)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
import math

def komut_uret(veri):
    if not isinstance(veri, dict) or set(veri) != {"eylem", "metin", "guvence"}:
        raise ValueError("karar şeması geçersiz")
    esleme = {"ozetle": "OZET", "cevir": "CEVIR", "yoksay": "YOKSAY"}
    if veri["eylem"] not in esleme:
        raise ValueError("eylem izinli değil")
    if not isinstance(veri["metin"], str) or not 1 <= len(veri["metin"]) <= 120:
        raise ValueError("metin geçersiz")
    guvence = veri["guvence"]
    if isinstance(guvence, bool) or not isinstance(guvence, (int, float)) or not math.isfinite(guvence) or not 0 <= guvence <= 1:
        raise ValueError("güvence geçersiz")
    if guvence < 0.75:
        return {"komut": "INCELE", "icerik": ""}
    return {"komut": esleme[veri["eylem"]], "icerik": veri["metin"]}
```

```hint
İç komutları literal dict ile eşle. Eşik altını erken `INCELE` dönüşüyle ayır; modelden gelen eylem adını çıktı komutuna doğrudan büyük harfle çevirme.
```
:::


::: anlat Gerçek JSON'un diskteki iş etkisini incele
[Sentetik ham JSON karar örneklerini aç](/data/ai-saldiri-10-json.txt). Dış dosya bir JSON listesidir; her `ham` alanının içindeki metin ayrı ayrıştırılacak model yanıtını temsil eder. Yinelenen anahtar ve `NaN` örnekleri eğitim için yazılmıştır, canlı model çıktısı değildir. Çalıştır ayrı kalıcı `calisma/ai-saldiri-10/kararlar.json` öğrenci kopyasını ve tam yolunu gösterir. Dış editör veya Python ile değiştirip tekrar çalıştır; sıfırlanmaz. 1–10 benzersiz `id` ve en çok 2000 karakterli `ham` kaydı kullan; en az bir izinli ve bir düşük güvenceli inceleme örneğini koru.

Yeni bölüm iki gerçek yerel model yanıtını da aynı ayrıştırma/şema/komut hattından geçirir. Model bozuk örneği düzeltirse veya kod çiti eklerse gözlenen gerçek çıktı kaydedilir; beklenen sabit cümle dayatılmaz. Doğru reddedilen canlı çıktı kabulü bozmaz, taşıma/yarım üretim hatası bozar.

İç komut bu kez yalnız sözlükte kalmaz: izinli iş gerçek SQLite `isler` kuyruğuna, düşük güvence `inceleme` kuyruğuna boş içerikle yazılır. Reddedilen girdinin hiçbir kuyruğa yazmaması ölçülür. Bağlantı kapanıp yeni bağlantıyla disk tekrar okunur. Bu, kuyruk adaptörü deneyidir; gerçek çeviri/özet üretildiği veya keyfi model komutlarının çalıştırıldığı iddiası yoktur. `dosya_sil` örneği hiçbir gerçek silme işlemi yapmaz. SQLite dosyası öğrenci alanında korunur; mevcut veriler silinmez. Test örnek dosyanı değiştirmekten bağımsız yeni veriler kullanır.
:::

::: gorev Gerçek deney · Katı JSON'dan gerçek iş kuyruğuna
Önceki üç işlevi birleştir: `kati_json`, `karar_dogrula`, `komut_uret`. Çalıştır, sentetik ve canlı ham kayıtları ayrı gösterir; her vaka için reddi/komutu ve SQLite değişim sayısını raporlar. Kontrol Et meşru akışın çalışmasını, düşük güvencenin incelemeye gitmesini ve geçersiz JSON'un sıfır kuyruk etkisi üretmesini doğrular. Modelin saldırı denemesine uyması şart değildir.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import json
import ai_lab

def kati_json(metin):
    # KUSURLU BAŞLANGIÇ KODU: kod çitini ve öndeki açıklamayı "akıllıca" soyuyor (başka bir ayrıştırıcı aynı metni farklı okur), json.loads kullanıyor (yinelenen anahtarda son değer kazanır, NaN/Infinity kabul edilir) ve ayrıştırma hatasını None ile gizliyor!
    kaynak = str(metin).strip()
    cit = "`" * 3
    if cit in kaynak:
        kaynak = kaynak.split(cit)[1].removeprefix("json").strip()
    elif "{" in kaynak:
        kaynak = kaynak[kaynak.index("{"):]
    try:
        return json.loads(kaynak)
    except json.JSONDecodeError:
        return None

def karar_dogrula(veri):
    # KUSURLU BAŞLANGIÇ KODU: ek alanları sessizce bırakıyor, eylemi lower() ile "düzeltiyor", float() ile True ve "0.9" değerlerini sayıya çeviriyor, metin türünü ve uzunluğunu denetlemiyor ve girdiyi yerinde değiştirip aynı nesneyi döndürüyor!
    eylem = str(veri["eylem"]).lower()
    if eylem not in ("ozetle", "cevir", "yoksay"):
        raise ValueError("eylem izinli değil")
    guvence = float(veri["guvence"])
    if not 0 <= guvence <= 1:
        raise ValueError("güvence 0..1 olmalı")
    veri["eylem"] = eylem
    veri["guvence"] = guvence
    return veri

def komut_uret(veri):
    # KUSURLU BAŞLANGIÇ KODU: bilinmeyen eylem adını büyük harfe çevirip komut yapıyor (dosya_sil → DOSYA_SIL), eşiği > ile uyguluyor (tam 0.75 incelemeye düşer), düşük güvencede model metnini inceleme kaydına taşıyor ve şemayı hiç denetlemiyor!
    esleme = {"ozetle": "OZET", "cevir": "CEVIR", "yoksay": "YOKSAY"}
    if veri["guvence"] > 0.75:
        return {"komut": esleme.get(veri["eylem"], str(veri["eylem"]).upper()), "icerik": veri["metin"]}
    return {"komut": "INCELE", "icerik": veri["metin"]}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_10 as deney
    deney.goster(kati_json,karar_dogrula,komut_uret)

```

```test
def sozlesme(fn):
    try:
        if fn(' {"a":1,"b":[true,null]} \n') != {"a": 1, "b": [True, None]}:
            return False
        if fn('"Pafta"') != "Pafta" or fn('[1,2]') != [1, 2] or fn('0') != 0:
            return False
        for metin in [
            '', '   ', '```json\n{"a":1}\n```', '{"a":1} ek', '{"a":1}{"b":2}',
            '{"a":1,"a":2}', '{"a":{"b":1,"b":2}}', '{"a":NaN}', '{"a":Infinity}', '{"a":-Infinity}',
            '{"a":}', '[1,2', None, 3,
        ]:
            try:
                fn(metin)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(kati_json), "tam tüketim, yinelenen anahtar, özel sayı ve tür denetimi korunmalı")
def m_loads(metin):
    import json
    return json.loads(metin)
def m_ilk(metin):
    import json
    return json.JSONDecoder().raw_decode(metin.strip())[0]
def m_sondan(metin):
    import json
    return json.loads(metin.split('```')[1])
for ad, mutant in [("yinelenen anahtarı ve NaN kabul eden", m_loads), ("sondaki metni yok sayan", m_ilk), ("kod çitini tahmin eden", m_sondan)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

import copy
KARAR = {"eylem": "ozetle", "metin": "Pafta", "guvence": 0.8}
def sozlesme(fn):
    try:
        once = copy.deepcopy(KARAR)
        sonuc = fn(KARAR)
        if sonuc != KARAR or sonuc is KARAR or KARAR != once:
            return False
        for deger in [
            {"eylem": "cevir", "metin": "a", "guvence": 0},
            {"eylem": "yoksay", "metin": "b" * 120, "guvence": 1},
        ]:
            if fn(deger) != deger:
                return False
        for deger in [
            None, [], dict(KARAR, ek=1), {"eylem": "ozetle", "metin": "x"},
            dict(KARAR, eylem="dosya_sil"), dict(KARAR, eylem=1),
            dict(KARAR, metin=""), dict(KARAR, metin="x" * 121), dict(KARAR, metin=3),
            dict(KARAR, guvence=True), dict(KARAR, guvence="0.8"),
            dict(KARAR, guvence=-0.1), dict(KARAR, guvence=1.1),
            dict(KARAR, guvence=float("nan")), dict(KARAR, guvence=float("inf")),
        ]:
            try:
                fn(deger)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(karar_dogrula), "tam şema, bool reddi, uzunluk ve sonlu aralık birlikte korunmalı")
def m_ek_alan(veri):
    return {k: veri[k] for k in ("eylem", "metin", "guvence") if k in veri}
def m_donustur(veri):
    return {"eylem": str(veri["eylem"]), "metin": str(veri["metin"]), "guvence": float(veri["guvence"])}
def m_bool(veri):
    sonuc = karar_dogrula(veri)
    return sonuc
for ad, mutant in [("ek alanı ve eksik şemayı kabul eden", m_ek_alan), ("türleri zorla dönüştüren", m_donustur)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

import copy
def sozlesme(fn):
    try:
        for veri, beklenen in [
            ({"eylem": "ozetle", "metin": "Pafta", "guvence": 0.75}, {"komut": "OZET", "icerik": "Pafta"}),
            ({"eylem": "cevir", "metin": "Merhaba", "guvence": 1}, {"komut": "CEVIR", "icerik": "Merhaba"}),
            ({"eylem": "cevir", "metin": "x", "guvence": 0}, {"komut": "INCELE", "icerik": ""}),
            ({"eylem": "cevir", "metin": "b" * 120, "guvence": 1}, {"komut": "CEVIR", "icerik": "b" * 120}),
            ({"eylem": "yoksay", "metin": "not", "guvence": 0.9}, {"komut": "YOKSAY", "icerik": "not"}),
            ({"eylem": "ozetle", "metin": "gizli", "guvence": 0.74}, {"komut": "INCELE", "icerik": ""}),
        ]:
            once = copy.deepcopy(veri)
            if fn(veri) != beklenen or veri != once:
                return False
        for veri in [
            None, [],
            {"eylem": "eval", "metin": "x", "guvence": 1},
            {"eylem": "ozetle", "metin": "x", "guvence": 1, "arac": "dosya_sil"},
            {"eylem": "ozetle", "metin": "x", "guvence": True},
            {"eylem": "ozetle", "metin": "x", "guvence": -0.1},
            {"eylem": "ozetle", "metin": "x", "guvence": 1.1},
            {"eylem": "ozetle", "metin": "x", "guvence": "0.8"},
            {"eylem": "ozetle", "metin": "x", "guvence": float("nan")},
            {"eylem": "ozetle", "metin": "x", "guvence": float("inf")},
            {"eylem": "ozetle", "metin": "", "guvence": 1},
            {"eylem": "ozetle", "metin": "x" * 121, "guvence": 1},
            {"eylem": "ozetle", "metin": 3, "guvence": 1},
        ]:
            try:
                fn(veri)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(komut_uret), "sabit eşleme, eşik sınırı, inceleme yolu ve şema korunmalı")
def m_dinamik(veri):
    return {"komut": veri["eylem"].upper(), "icerik": veri["metin"]}
def m_esik(veri):
    sonuc = komut_uret(veri)
    if sonuc["komut"] == "INCELE":
        sonuc = {"komut": "OZET", "icerik": veri["metin"]}
    return sonuc
def m_ek(veri):
    return {"komut": "OZET", "icerik": veri["metin"]}
for ad, mutant in [("model adını komut yapan", m_dinamik), ("düşük güvenceyi çalıştıran", m_esik), ("şemayı atlayan", m_ek)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

from sandbox import ai_gercek_ai_saldiri_10 as deney
import json,secrets,tempfile
from pathlib import Path
import ast
_yasak=('pipeline_referans','_pipeline','_isle','eval','exec','getattr','kanit_yaz')
_sorun=list(ai_lab.kod_denetimi(src,_yasak))
for _n in ast.walk(ast.parse(src)):
    if isinstance(_n,ast.ImportFrom) and any(a.name in _yasak or a.name=='*' for a in _n.names):_sorun.append('referans importu yasak')
    if isinstance(_n,(ast.Import,ast.ImportFrom)) and any(x and x.split('.')[0] in ('inspect','importlib','runpy') for x in [a.name for a in _n.names]+([_n.module] if isinstance(_n,ast.ImportFrom) else [])):_sorun.append('kaynak okuma/dinamik import yasak')
    if isinstance(_n,ast.Name) and _n.id in ('exec','eval','compile','__builtins__'):_sorun.append('dinamik kod çalıştırma yasak: '+_n.id)
if not ok(not _sorun, 'dinamik çağrı ve laboratuvar yaması olmamalı: '+'; '.join(sorted(set(_sorun)))):stop()
for i in range(4):
    marker='NOT-'+secrets.token_hex(4)
    valid=json.dumps(dict(eylem='ozetle',metin=marker,guvence=.75),ensure_ascii=False)
    if not ok(komut_uret(karar_dogrula(kati_json(valid)))==dict(komut='OZET',icerik=marker),'yeni geçerli JSON eşik sınırında iş üretmeli'):stop()
    for raw in [valid+' EK','{"x":1,"x":2}', '{"ic":{"x":1,"x":2}}']:
        rejected=False
        try:kati_json(raw)
        except ValueError:rejected=True
        if not ok(rejected,'yeni bozuk JSON ek metin/yinelenen anahtar reddi'):stop()
with tempfile.TemporaryDirectory(prefix='pafta_json10_') as tmp:
    samples=deney.ornekleri_oku(deney.ORNEK)
    samples[0]['ham']=json.dumps(dict(eylem='ozetle',metin=secrets.token_hex(4),guvence=.9))
    result=deney.deney(kati_json,karar_dogrula,komut_uret,samples,Path(tmp)/'kuyruk.sqlite3')
    for key,value in result['kontroller'].items():ok(value,'gerçek deney: '+key)
    accepted=all(result['kontroller'].values())
    ai_lab.kanit_yaz('saldiri-10-json',dict(result,kabul=accepted))
    ok(accepted,'gerçek SQLite kuyruk etkisi ve iki canlı yanıt; modelin belirli bozuk JSON üretmesi şart değil')

```

```solution
import ai_lab

import json

def kati_json(metin):
    if not isinstance(metin, str) or not metin.strip():
        raise ValueError("tek JSON belgesi gerekli")
    def nesne(parcalar):
        sonuc = {}
        for anahtar, deger in parcalar:
            if anahtar in sonuc:
                raise ValueError("yinelenen anahtar")
            sonuc[anahtar] = deger
        return sonuc
    def sabit(deger):
        raise ValueError("standart dışı sayı")
    decoder = json.JSONDecoder(object_pairs_hook=nesne, parse_constant=sabit)
    kaynak = metin.strip()
    try:
        veri, bitis = decoder.raw_decode(kaynak)
    except json.JSONDecodeError as e:
        raise ValueError("geçersiz JSON") from e
    if bitis != len(kaynak):
        raise ValueError("JSON sonrası ek içerik")
    return veri

import math

def karar_dogrula(veri):
    if not isinstance(veri, dict) or set(veri) != {"eylem", "metin", "guvence"}:
        raise ValueError("karar şeması geçersiz")
    if veri["eylem"] not in ("ozetle", "cevir", "yoksay"):
        raise ValueError("eylem izinli değil")
    if not isinstance(veri["metin"], str) or not 1 <= len(veri["metin"]) <= 120:
        raise ValueError("metin 1..120 karakter olmalı")
    guvence = veri["guvence"]
    if isinstance(guvence, bool) or not isinstance(guvence, (int, float)):
        raise ValueError("güvence sayı olmalı")
    if not math.isfinite(guvence) or not 0 <= guvence <= 1:
        raise ValueError("güvence 0..1 olmalı")
    return {"eylem": veri["eylem"], "metin": veri["metin"], "guvence": guvence}

import math

def komut_uret(veri):
    if not isinstance(veri, dict) or set(veri) != {"eylem", "metin", "guvence"}:
        raise ValueError("karar şeması geçersiz")
    esleme = {"ozetle": "OZET", "cevir": "CEVIR", "yoksay": "YOKSAY"}
    if veri["eylem"] not in esleme:
        raise ValueError("eylem izinli değil")
    if not isinstance(veri["metin"], str) or not 1 <= len(veri["metin"]) <= 120:
        raise ValueError("metin geçersiz")
    guvence = veri["guvence"]
    if isinstance(guvence, bool) or not isinstance(guvence, (int, float)) or not math.isfinite(guvence) or not 0 <= guvence <= 1:
        raise ValueError("güvence geçersiz")
    if guvence < 0.75:
        return {"komut": "INCELE", "icerik": ""}
    return {"komut": esleme[veri["eylem"]], "icerik": veri["metin"]}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_10 as deney
    deney.goster(kati_json,karar_dogrula,komut_uret)

```

```hint
Katı parser bütün belgeyi tüketsin ve nesne kancası her düzeyde yineleneni reddetsin. Şema ile komut yetkisini ayır; bool güvence değildir. Eşik altında içerik boş kalsın. Reddedilen kayıt için SQL eklemesi oluşmamalı.
```
:::


::: anlat Bunu iki dakikada nasıl anlatırsın?
Katı JSON ayrıştırıcısında tek belge şartından başla: sondaki ikinci nesne, duplicate key ve NaN gibi uzantılar farklı ayrıştırıcıların farklı karar vermesine yol açabilir. Ayrıştırma sonrasında alan kümesini ve türleri doğrula; bool Python’da int alt türü olsa da sözleşmede sayı sayılmaz. Ancak doğrulanmış kararı sabit izinli iç komuta çevir ve gerçek kuyruğa öyle yaz. Biçimsel olarak geçerli JSON, yetkili eylem demek değildir.

Önkoşul ve yol köprüsü: ai-savunma-14 şema denetimi.

| Yaygın yanlış | Mekanizma ve sınır |
|---|---|
| JSON parse edildiği için güvenlidir | Şema, alan türü ve eylem yetkisi ayrı kapılardır |

Dinleyiciye sor: Hangi aşamanın çıktısı bir sonrakinin girdisine dönüşüyor; bu geçişte kaynak ve yetki nasıl korunuyor? Gerçek deneyin kayıtlarıyla cevapla.
:::


::: anlat Birincil kaynak ve deney sınırı
[Python json.JSONDecoder](https://docs.python.org/3/library/json.html): `raw_decode`, `object_pairs_hook` ve `parse_constant` davranışları için referans. Duplicate key ve standart dışı sayıların reddi dersin katı parser sözleşmesidir. Çalışan araç/model sürümü canlı kanıtta saklanır; bağlantıdaki belge sürümüyle otomatik eşit kabul edilmez.
:::
