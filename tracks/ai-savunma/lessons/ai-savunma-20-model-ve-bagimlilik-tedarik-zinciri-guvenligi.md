---
id: ai-savunma-20
title: Model ve Bağımlılık Tedarik Zinciri Güvenliği
summary: Model, imaj ve paket bileşenlerinde kaynak, imza, boyut, SHA-256 bütünlüğü ve risk bulgularını fail-closed kararlarla denetle; önce görünür sentetik SBOM ile, sonra kurulu Ollama modelinin katmanlarını gerçek SHA-256 ile doğrula.
timeout: 45
esleme: ai-saldiri-41, ai-saldiri-01
---

::: anlat Gerçek biçimi bil, sentetik temsili ayırt et: İndirilebilir olması güvenilir olduğu anlamına gelmez

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Cosign/Sigstore bir imajın veya dosyanın kimin tarafından imzalandığını doğrular. Trivy veya Grype bileşenlerdeki bilinen zafiyetleri (CVE) önem derecesiyle listeler. SBOM (CycloneDX, SPDX) hangi bileşenin hangi sürüm ve özetle kullanıldığını kaydeder. `sha256sum` dosyanın bayt bayt aynı olup olmadığını gösterir. | Görev 1–3: `veri/tedarik_politikasi.json` ve `veri/bilesenler.json` içindeki **sentetik** SBOM/tarama özeti. Son adım: kurulu Ollama modelinin manifest'i ve blob dosyaları salt okunur açılır, her katmanın SHA-256 özeti **gerçekten hesaplanır**. Tahrifat senaryosu için küçük bir katmanın geçici kopyası bir bayt değiştirilerek yeniden özetlenir. | Özet eşleşmesi yalnız dosyanın manifest'te yazanla aynı olduğunu gösterir. Manifest'i yazanın güvenilir olduğunu, modelin arka kapısız olduğunu ya da zafiyet bulunmadığını göstermez. Bu derste Cosign ve Trivy çalıştırılmaz; imza ve risk alanları gerçek deneyde de tarama sonucu değildir. |

> [!NOT]
> Görev 1–3 sentetik veriyle çalışır. Bu görevlerde dosya özeti hesaplanmaz, model çağrılmaz. Son adımdaki **Gerçek deney** görevi yerel Ollama sunucusundan kurulu modelin adını alır ve o modelin dosyalarını **yalnız okuyarak** gerçek SHA-256 hesaplar. Hiçbir model indirilmez, yüklenmez ya da değiştirilmez. Trivy ve Cosign çalıştırılmaz. `veri/` dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalanır; kopyada yaptığın değişiklik bir sonraki çalıştırmada sıfırlanır, **kalıcılık yoktur**. Kontrol bu dosyalardan ayrı, gizli verilerle sınar.

Model dosyası, konteyner imajı veya Python paketi bir üretim zincirine girmeden önce kaynağı, türü, imzası ve bütünlüğü doğrulanır. Trivy benzeri bir tarayıcının risk bulguları da politika dışında kalan bileşeni durdurmak için kullanılır. Yapay zekâ bileşenleri burada özel bir risk taşır. Bir model dosyası "veri" gibi görünür, ama `pickle` tabanlı biçimler yüklenirken kod çalıştırabilir. Ağırlıklara gömülmüş bir arka kapı ise hiçbir tarayıcının imzasıyla eşleşmez. Hugging Face gibi açık depolarda isim benzerliğiyle (typosquatting) ya da ele geçirilmiş hesaplarla zararlı model yayımlanması belgelenmiş bir saldırı yoludur.

**Üç ayrı soru vardır ve birbirinin yerine geçmez.** Bütünlük, dosyanın beklenen dosya olup olmadığını sorar. İmza, beklenen dosyayı kimin onayladığını sorar. Risk taraması, onaylı dosyada bilinen bir zafiyet bulunup bulunmadığını sorar. Fail-closed politika üçünden biri cevapsız kalırsa bileşeni karantinaya alır.
:::

::: anlat Bütünlük ve risk ayrı kontrollerdir
SHA-256 özeti 64 küçük onaltılık karakterdir. Beklenen ve gerçek özetin aynı olması bütünlük koşuludur; özetteki tek karakter farkı bile kabul edilmez. Ancak eşleşen özet, bileşende politika dışı risk bulunmadığını kanıtlamaz.

Riskler `dusuk`, `orta`, `yuksek`, `kritik` değerleridir. Politikanın izinli risk listesi boş olabilir; bu durumda yalnız hiç risk bulgusu olmayan bileşen kabul edilebilir.

**Özet nasıl çalışır?** SHA-256 girdinin her bitine bağlı 256 bitlik bir çıktı üretir. Tek bir bayt değiştiğinde çıktının yaklaşık yarısı değişir. Bilinen bir özetle aynı özeti üreten farklı bir dosya bulmak bugünkü hesap gücüyle pratikte mümkün değildir. Bu yüzden "özet eşleşti" demek, dosya bayt bayt aynı demektir. `veri/bilesenler.json` içindeki `ozet-modeli-ayna` kaydında beklenen ve gerçek özet **yalnız son karakterde** ayrılır. Gerçek bir dosyada tek bayt değişince özetin tamamı değişir. Bu kayıt, kısaltmayla karşılaştırmanın neyi kaçırdığını göstermek için abartılmış bir öğretim örneğidir. Asıl tehlike şudur: arayüzlerde sık görülen 12 karakterlik kısa özet yalnız 48 bittir. Bu kadar kısa bir öneki tutturan farklı bir dosya üretmek, büyük hesap gücüne sahip bir saldırgan için ulaşılabilir bir hedeftir. Karşılaştırma bu yüzden her zaman tam 64 karakterle yapılır, önek ya da kısaltmayla yapılmaz.

**Beklenen özet nereden gelir?** Burada asıl tuzak budur. Beklenen özeti indirdiğin dosyanın yanındaki `.sha256` dosyasından alıyorsan, sunucuyu ele geçiren saldırgan ikisini birlikte değiştirebilir. Beklenen değer ayrı bir güven kaynağından gelmelidir: sürüm kilidi (lockfile), imzalı manifest ya da kurum içinde pinlenmiş SBOM. Python'da `pip install --require-hashes` bunu paketler için yapar. Ollama ve Docker/OCI ise dosyaları zaten özetleriyle adresler (`blobs/sha256-<hex>`). Bu yapı manifest'in kendisinin güvenilir olmasına dayanır.

**Saldırgan bakışı:** Saldırgan özeti kırmaya uğraşmaz; özetin kontrol edilmediği yeri arar. Örnekler: önbellekten gelen eski bir dosya, "geçici olarak" imza kontrolü kapatılmış bir CI adımı, `latest` etiketiyle çekilen ve her gün değişebilen bir imaj, beklenen özet alanı boş bırakıldığında "kabul" diyen bir kod.

**Savunucu tarafı ve sık tuzaklar:**

- **Biçim denetimi:** Büyük harfli ya da 63 karakterlik özet biçim hatasıdır, reddedilir. Normalleştirip kabul etmek, bozuk bir manifest'i sessizce geçirir.
- **Boyut eşitliği:** Boyut sınırına eşit bileşen kabul edilir (`ozet-modeli`, tam 1000 MB).
- **Tek risk nedeni:** Birden çok politika dışı risk olsa da `risk` nedeni bir kez yazılır. Ayrıntı tarayıcı raporunda kalır.
- **Boş risk listesi:** "Risk yok" demek değildir. Tarama yapılmadıysa bu, raporda ayrıca belirtilmelidir.
:::

::: tahmin SHA-256 desenini ve eşitliğini tahmin et
Üç çıktı satırını yaz:

```python
import re
ozet = "a" * 64
print(len(ozet))
print(bool(re.fullmatch(r"[0-9a-f]{64}", ozet)))
print(ozet == "a" * 63 + "b")
```

???

```cikti
64
True
False
```

Desen doğrulaması yalnız özetin biçimini denetler. Beklenen değerle karşılaştırma ayrıca yapılır.
:::

::: gorev 1 · Tedarik güvenliği politikasını doğrula
`tedarik_politikasi_dogrula(politika)` işlevini yaz. Politika tam olarak `izinli_kaynaklar`, `izinli_turler`, `izinli_riskler`, `max_boyut_mb`, `imza_zorunlu` alanlarını taşısın. Kaynak listesi `resmi`, `kurumsal`, `yerel`; tür listesi `model`, `imaj`, `paket` değerlerinden oluşan boş olmayan ve yinelenmeyen listedir.

Risk listesi `dusuk`, `orta`, `yuksek`, `kritik` değerlerinden oluşan yinelenmeyen listedir ve boş olabilir. Boyut sınırı bool olmayan 1–10000 arası int olmalıdır. İmza zorunluluğu gerçek `True` olmalıdır. Geçersiz veride `ValueError` yükselt.

Politikayı yeni listelerle döndür; girdiyi değiştirme.

Görünür veri: `veri/tedarik_politikasi.json`. Başlangıç kodu asıl politikayı ve dört bozuk politikayı doğrulamayı dener. Bozukların dördü de reddedilmelidir.

```starter
from ai_savunma_veri import json_yukle

def tedarik_politikasi_dogrula(politika):
    # KUSURLU BAŞLANGIÇ KODU: imza_zorunlu False'u, boş tür listesini, yinelenen riski ve sınır dışı boyutu kabul ediyor; girdinin kendisini döndürüyor!
    for alan in ("izinli_kaynaklar", "izinli_turler", "izinli_riskler", "max_boyut_mb", "imza_zorunlu"):
        if alan not in politika:
            raise ValueError("eksik alan: " + alan)
    if not isinstance(politika["max_boyut_mb"], int):
        raise ValueError("boyut sınırı int olmalı")
    return politika

veri = json_yukle("veri/tedarik_politikasi.json")
for ad, p in [("asil", veri["politika"])] + [(b["ad"], b["politika"]) for b in veri["bozuk_politikalar"]]:
    try:
        tedarik_politikasi_dogrula(p)
        print(ad, "kabul")
    except ValueError as hata:
        print(ad, "reddedildi:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-20")
```

```test
import copy
P = {"izinli_kaynaklar": ["resmi", "kurumsal"], "izinli_turler": ["model", "paket"], "izinli_riskler": ["dusuk"], "max_boyut_mb": 1000, "imza_zorunlu": True}
def sozlesme(fn):
    try:
        once = copy.deepcopy(P)
        sonuc = fn(P)
        if sonuc != P or P != once or sonuc is P:
            return False
        if any(sonuc[x] is P[x] for x in ("izinli_kaynaklar", "izinli_turler", "izinli_riskler")):
            return False
        if fn(dict(P, izinli_riskler=[]))["izinli_riskler"] != []:
            return False
        for sinir in (1, 10000):
            if fn(dict(P, max_boyut_mb=sinir))["max_boyut_mb"] != sinir:
                return False
        for politika in [
            None, [], dict(P, ek=1), dict(P, izinli_kaynaklar=[]), dict(P, izinli_kaynaklar=None),
            dict(P, izinli_kaynaklar=["resmi", "resmi"]), dict(P, izinli_kaynaklar=["bilinmeyen"]),
            dict(P, izinli_turler=[]), dict(P, izinli_turler=["model", "model"]), dict(P, izinli_turler=["dosya"]),
            dict(P, izinli_riskler=None), dict(P, izinli_riskler=["dusuk", "dusuk"]), dict(P, izinli_riskler=["bilinmeyen"]),
            dict(P, max_boyut_mb=0), dict(P, max_boyut_mb=10001), dict(P, max_boyut_mb=True),
            dict(P, imza_zorunlu=False), dict(P, imza_zorunlu=1),
        ]:
            try:
                fn(politika)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(tedarik_politikasi_dogrula), "kaynak, tür, risk, boyut ve imza politikaları korunmalı")
def m_kaynak(politika):
    sonuc = tedarik_politikasi_dogrula(politika)
    sonuc["izinli_kaynaklar"].append("yerel")
    return sonuc
def m_risk(politika):
    sonuc = tedarik_politikasi_dogrula(politika)
    sonuc["izinli_riskler"].append("kritik")
    return sonuc
def m_imza(politika):
    sonuc = tedarik_politikasi_dogrula(politika)
    sonuc["imza_zorunlu"] = False
    return sonuc
for ad, mutant in [("kaynağı açan", m_kaynak), ("riski açan", m_risk), ("imzayı kaldıran", m_imza)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def tedarik_politikasi_dogrula(politika):
    if not isinstance(politika, dict):
        raise ValueError("politika sözlük olmalı")
    if set(politika) != {"izinli_kaynaklar", "izinli_turler", "izinli_riskler", "max_boyut_mb", "imza_zorunlu"}:
        raise ValueError("politika şeması geçersiz")
    for alan, izinler, bos_olabilir in [
        ("izinli_kaynaklar", ("resmi", "kurumsal", "yerel"), False),
        ("izinli_turler", ("model", "imaj", "paket"), False),
        ("izinli_riskler", ("dusuk", "orta", "yuksek", "kritik"), True),
    ]:
        degerler = politika[alan]
        if not isinstance(degerler, list):
            raise ValueError(alan + " liste olmalı")
        if not degerler and not bos_olabilir:
            raise ValueError(alan + " boş olamaz")
        if len(set(degerler)) != len(degerler):
            raise ValueError(alan + " yinelenemez")
        if any(deger not in izinler for deger in degerler):
            raise ValueError(alan + " geçersiz değer içeriyor")
    if type(politika["max_boyut_mb"]) is not int:
        raise ValueError("boyut sınırı int olmalı")
    if politika["max_boyut_mb"] < 1:
        raise ValueError("boyut sınırı pozitif olmalı")
    if politika["max_boyut_mb"] > 10000:
        raise ValueError("boyut sınırı çok büyük")
    if politika["imza_zorunlu"] is not True:
        raise ValueError("imza zorunlu olmalı")
    return {"izinli_kaynaklar": list(politika["izinli_kaynaklar"]), "izinli_turler": list(politika["izinli_turler"]), "izinli_riskler": list(politika["izinli_riskler"]), "max_boyut_mb": politika["max_boyut_mb"], "imza_zorunlu": True}
```

```hint
Üç liste için tür, boşluk, yineleme ve izinli değer kontrollerini birlikte uygula. Risk listesinin boş olabileceğini diğerlerinden ayrı belirt.
```
:::

::: anlat Kabul raporu her ihlali ayrı gösterir
Bileşen türü veya kaynağı politika dışında ise sırasıyla `tur` ve `kaynak`, boyut sınırı aşılıyorsa `boyut`, imza yoksa `imza` nedeni üretilir. Nedenler bu sıradadır; herhangi biri bileşeni karantinaya alır.

Boyut sınırına eşitlik kabul edilir. SHA-256 alanı bu görevde yalnız biçim açısından doğrulanır; beklenen değerle karşılaştırma üçüncü görevdedir.
:::

::: gorev 2 · Bileşen kabul kararlarını raporla
`bilesen_kabul_raporu(bilesenler, politika)` işlevini yaz. Politika ilk görevdeki bütün kuralları sağlasın. Bileşenler liste; her kayıt tam olarak `id`, `tur`, `kaynak`, `boyut_mb`, `imzali`, `sha256` alanlarını taşısın. Kimlik 1–64 karakterlik, ASCII harf/rakamla başlayan ve yalnız ASCII harf, rakam, alt çizgi veya tire içeren benzersiz stringdir.

Tür `model`, `imaj`, `paket`; kaynak `resmi`, `kurumsal`, `yerel` olmalıdır. Boyut bool olmayan pozitif int, imza gerçek bool olmalıdır. Özet 64 küçük onaltılık karakterdir. Geçersiz veride `ValueError` yükselt.

Dört kabul nedenini sırayla uygula. Her kayıt için `{"id":ID,"karar":"karantina" if nedenler else "kabul","nedenler":[...]}` döndür. Kimliğe göre sırala, boş bileşende boş liste döndür ve girdileri değiştirme.

Görünür veri: `veri/bilesenler.json` içindeki `kabul_kayitlari` ve `veri/tedarik_politikasi.json`. `ozet-modeli` sınıra tam eşit olduğu için kabul edilmelidir. `topluluk-ince-ayar` üç nedenin hepsini göstermelidir.

```starter
from ai_savunma_veri import json_yukle

def bilesen_kabul_raporu(bilesenler, politika):
    # KUSURLU BAŞLANGIÇ KODU: ilk nedende duruyor (elif) ve boyut sınırına eşitliği ihlal sayıyor!
    sonuc = []
    for b in bilesenler:
        nedenler = []
        if b["tur"] not in politika["izinli_turler"]:
            nedenler.append("tur")
        elif b["kaynak"] not in politika["izinli_kaynaklar"]:
            nedenler.append("kaynak")
        elif b["boyut_mb"] >= politika["max_boyut_mb"]:
            nedenler.append("boyut")
        elif not b["imzali"]:
            nedenler.append("imza")
        sonuc.append({"id": b["id"], "karar": "karantina" if nedenler else "kabul", "nedenler": nedenler})
    return sorted(sonuc, key=lambda x: x["id"])

politika = json_yukle("veri/tedarik_politikasi.json")["politika"]
veri = json_yukle("veri/bilesenler.json")
for s in bilesen_kabul_raporu(veri["kabul_kayitlari"], politika):
    print(s["id"], s["karar"], s["nedenler"])
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-20")
```

```test
import copy
P = {"izinli_kaynaklar": ["resmi", "kurumsal"], "izinli_turler": ["model", "paket"], "izinli_riskler": ["dusuk"], "max_boyut_mb": 1000, "imza_zorunlu": True}
B = [
    {"id": "kabul-1", "tur": "model", "kaynak": "resmi", "boyut_mb": 1000, "imzali": True, "sha256": "a" * 64},
    {"id": "ret-1", "tur": "imaj", "kaynak": "yerel", "boyut_mb": 1001, "imzali": False, "sha256": "b" * 64},
    {"id": "imza-1", "tur": "paket", "kaynak": "kurumsal", "boyut_mb": 1, "imzali": False, "sha256": "c" * 64},
]
BEKLENEN = [
    {"id": "imza-1", "karar": "karantina", "nedenler": ["imza"]},
    {"id": "kabul-1", "karar": "kabul", "nedenler": []},
    {"id": "ret-1", "karar": "karantina", "nedenler": ["tur", "kaynak", "boyut", "imza"]},
]
def sozlesme(fn):
    try:
        bonce = copy.deepcopy(B)
        ponce = copy.deepcopy(P)
        if fn(B, P) != BEKLENEN or B != bonce or P != ponce or fn(list(reversed(B)), P) != BEKLENEN or fn([], P) != []:
            return False
        if fn([dict(B[0], id="a" * 64)], P)[0]["id"] != "a" * 64:
            return False
        if fn([dict(B[0], sha256="0123456789abcdef" * 4)], P)[0]["karar"] != "kabul":
            return False
        for alan, deger in [("izinli_riskler", []), ("max_boyut_mb", 1), ("max_boyut_mb", 10000)]:
            if fn([], dict(P, **{alan: deger})) != []:
                return False
        for bilesenler, politika in [
            (None, P), ({}, P), ([None], P), (B, None), (B, dict(P, imza_zorunlu=False)),
            (B, dict(P, izinli_kaynaklar=[])), (B, dict(P, izinli_turler=[])),
            (B, dict(P, izinli_riskler=["bilinmeyen"])), (B, dict(P, max_boyut_mb=0)), (B, dict(P, max_boyut_mb=10001)),
            ([dict(B[0], ek=1)], P), ([dict(B[0], id="")], P), ([dict(B[0], id="a b")], P),
            ([dict(B[0], id="a" * 65)], P), ([B[0], B[0]], P), ([dict(B[0], tur="dosya")], P),
            ([dict(B[0], kaynak="bilinmeyen")], P), ([dict(B[0], boyut_mb=0)], P),
            ([dict(B[0], boyut_mb=True)], P), ([dict(B[0], imzali=1)], P),
            ([dict(B[0], sha256="a" * 63)], P), ([dict(B[0], sha256="A" * 64)], P),
            ([dict(B[0], sha256="g" * 64)], P), ([dict(B[0], sha256=None)], P),
        ]:
            try:
                fn(bilesenler, politika)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(bilesen_kabul_raporu), "tür, kaynak, boyut, imza ve özet kuralları korunmalı")
def m_tur(bilesenler, politika):
    return bilesen_kabul_raporu(bilesenler, dict(politika, izinli_turler=["model", "paket", "imaj"]))
def m_kaynak(bilesenler, politika):
    return bilesen_kabul_raporu(bilesenler, dict(politika, izinli_kaynaklar=["resmi", "kurumsal", "yerel"]))
def m_imza(bilesenler, politika):
    return bilesen_kabul_raporu([dict(x, imzali=True) for x in bilesenler], politika)
for ad, mutant in [("türü açan", m_tur), ("kaynağı açan", m_kaynak), ("imzayı silen", m_imza)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
raises(ValueError,bilesen_kabul_raporu,[{'id': 'kabul-1', 'tur': 'model', 'kaynak': 'resmi', 'boyut_mb': 1000, 'imzali': True, 'sha256': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'}, {'id': 'ret-1', 'tur': 'imaj', 'kaynak': 'yerel', 'boyut_mb': 1001, 'imzali': False, 'sha256': 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'}, {'id': 'imza-1', 'tur': 'paket', 'kaynak': 'kurumsal', 'boyut_mb': 1, 'imzali': False, 'sha256': 'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc'}],{'izinli_kaynaklar': None, 'izinli_turler': ['model', 'paket'], 'izinli_riskler': ['dusuk'], 'max_boyut_mb': 1000, 'imza_zorunlu': True},msg="hatalı alan ValueError sözleşmesi: mutant:328:29:Add->Sub")
raises(ValueError,bilesen_kabul_raporu,[{'id': 'kabul-1', 'tur': 'model', 'kaynak': 'resmi', 'boyut_mb': 1000, 'imzali': True, 'sha256': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'}, {'id': 'ret-1', 'tur': 'imaj', 'kaynak': 'yerel', 'boyut_mb': 1001, 'imzali': False, 'sha256': 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'}, {'id': 'imza-1', 'tur': 'paket', 'kaynak': 'kurumsal', 'boyut_mb': 1, 'imzali': False, 'sha256': 'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc'}],{'izinli_kaynaklar': ['x', 'x'], 'izinli_turler': ['model', 'paket'], 'izinli_riskler': ['dusuk'], 'max_boyut_mb': 1000, 'imza_zorunlu': True},msg="hatalı alan ValueError sözleşmesi: mutant:340:29:Add->Sub")
# --- carbon-c8-ek-bas ---
raises(ValueError, bilesen_kabul_raporu, B, dict(P, izinli_kaynaklar=[123]), msg="izinli kaynak str olmalı")
raises(ValueError, bilesen_kabul_raporu, B, dict(P, izinli_turler=[123]), msg="izinli tür str olmalı")
raises(ValueError, bilesen_kabul_raporu, B, dict(P, izinli_riskler=[123]), msg="izinli risk str olmalı")
raises(ValueError, bilesen_kabul_raporu, B, dict(P, max_boyut_mb=True), msg="max_boyut_mb bool ret")
raises(ValueError, bilesen_kabul_raporu, [dict(B[0], id=123)], P, msg="id str olmalı")
raises(ValueError, bilesen_kabul_raporu, [dict(B[0], tur=123)], P, msg="tür str olmalı")
raises(ValueError, bilesen_kabul_raporu, [dict(B[0], kaynak=123)], P, msg="kaynak str olmalı")
raises(ValueError, bilesen_kabul_raporu, [dict(B[0], boyut_mb=True)], P, msg="boyut_mb bool ret")
raises(ValueError, bilesen_kabul_raporu, [dict(B[0], sha256=123)], P, msg="sha256 str olmalı")
raises(ValueError, bilesen_kabul_raporu, B, dict(P, ek=1), msg="politika fazla alan ret")
raises(ValueError, bilesen_kabul_raporu, B, dict(P, izinli_kaynaklar=tuple(P["izinli_kaynaklar"])), msg="izinli_kaynaklar tuple olamaz")
raises(ValueError, bilesen_kabul_raporu, B, dict(P, izinli_kaynaklar=P["izinli_kaynaklar"] + [P["izinli_kaynaklar"][0]]), msg="yinelenen izinli kaynak ret")
# --- carbon-c8-ek-son ---
```

```solution
def bilesen_kabul_raporu(bilesenler, politika):
    import re
    if not isinstance(politika, dict):
        raise ValueError("politika sözlük olmalı")
    if set(politika) != {"izinli_kaynaklar", "izinli_turler", "izinli_riskler", "max_boyut_mb", "imza_zorunlu"}:
        raise ValueError("politika şeması geçersiz")
    for alan, izinler, bos_olabilir in [
        ("izinli_kaynaklar", ("resmi", "kurumsal", "yerel"), False),
        ("izinli_turler", ("model", "imaj", "paket"), False),
        ("izinli_riskler", ("dusuk", "orta", "yuksek", "kritik"), True),
    ]:
        degerler = politika[alan]
        if not isinstance(degerler, list):
            raise ValueError(alan + " liste olmalı")
        if not degerler and not bos_olabilir:
            raise ValueError(alan + " boş olamaz")
        if len(set(degerler)) != len(degerler):
            raise ValueError(alan + " yinelenemez")
        if any(deger not in izinler for deger in degerler):
            raise ValueError(alan + " geçersiz değer içeriyor")
    if type(politika["max_boyut_mb"]) is not int:
        raise ValueError("boyut sınırı int olmalı")
    if politika["max_boyut_mb"] < 1:
        raise ValueError("boyut sınırı pozitif olmalı")
    if politika["max_boyut_mb"] > 10000:
        raise ValueError("boyut sınırı çok büyük")
    if politika["imza_zorunlu"] is not True:
        raise ValueError("imza zorunlu olmalı")
    if not isinstance(bilesenler, list):
        raise ValueError("bileşenler liste olmalı")
    kimlikler = set()
    sonuc = []
    for bilesen in bilesenler:
        if not isinstance(bilesen, dict):
            raise ValueError("bileşen sözlük olmalı")
        if set(bilesen) != {"id", "tur", "kaynak", "boyut_mb", "imzali", "sha256"}:
            raise ValueError("bileşen şeması geçersiz")
        kimlik = bilesen["id"]
        if not isinstance(kimlik, str):
            raise ValueError("kimlik string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kimlik):
            raise ValueError("kimlik geçersiz")
        if kimlik in kimlikler:
            raise ValueError("kimlik yinelenemez")
        kimlikler.add(kimlik)
        if bilesen["tur"] not in ("model", "imaj", "paket"):
            raise ValueError("tür geçersiz")
        if bilesen["kaynak"] not in ("resmi", "kurumsal", "yerel"):
            raise ValueError("kaynak geçersiz")
        if type(bilesen["boyut_mb"]) is not int:
            raise ValueError("boyut int olmalı")
        if bilesen["boyut_mb"] < 1:
            raise ValueError("boyut pozitif olmalı")
        if type(bilesen["imzali"]) is not bool:
            raise ValueError("imza bool olmalı")
        if not isinstance(bilesen["sha256"], str):
            raise ValueError("özet string olmalı")
        if not re.fullmatch(r"[0-9a-f]{64}", bilesen["sha256"]):
            raise ValueError("özet geçersiz")
        nedenler = []
        if bilesen["tur"] not in politika["izinli_turler"]:
            nedenler.append("tur")
        if bilesen["kaynak"] not in politika["izinli_kaynaklar"]:
            nedenler.append("kaynak")
        if bilesen["boyut_mb"] > politika["max_boyut_mb"]:
            nedenler.append("boyut")
        if not bilesen["imzali"]:
            nedenler.append("imza")
        sonuc.append({"id": kimlik, "karar": "karantina" if nedenler else "kabul", "nedenler": nedenler})
    return sorted(sonuc, key=lambda x: x["id"])
```

```hint
Özet için `[0-9a-f]{64}` desenini kullan. Dört karar nedenini bağımsız üret; boyutta yalnız politika üstünü ihlal say.
```
:::

::: anlat Sürüm kararı bütünlük ve zafiyeti birlikte değerlendirir
İkinci görevdeki dört kurala ek olarak beklenen ve gerçek SHA-256 farklıysa `butunluk`, risklerden en az biri izinli listede yoksa `risk` nedeni eklenir. Neden sırası `tur`, `kaynak`, `boyut`, `imza`, `butunluk`, `risk` şeklindedir.

Birden çok risk olsa da `risk` nedeni yalnız bir kez yazılır. Karar raporu bileşenin içeriğini çalıştırmaz; yalnız kabul veya karantina sonucunu üretir.
:::

::: gorev 3 · Bütünlük ve zafiyet denetimli sürüm kararı üret
`surum_guvenlik_raporu(bilesenler, politika)` işlevini yaz. Politika ilk görevdeki bütün kuralları sağlasın. Bileşenler liste; her kayıt tam olarak `id`, `tur`, `kaynak`, `boyut_mb`, `imzali`, `beklenen_sha256`, `gercek_sha256`, `riskler` alanlarını taşısın. Kimlik, tür, kaynak, boyut ve imza ikinci görevdeki kurallara uysun. İki özet de 64 küçük onaltılık karakterdir.

Riskler liste olmalı; her değer `dusuk`, `orta`, `yuksek`, `kritik` olmalı ve listede yinelenmemelidir. Geçersiz veride `ValueError` yükselt. Altı karar nedenini belirtilen sırayla uygula.

Her kayıt için `{"id":ID,"karar":"karantina" if nedenler else "kabul","nedenler":[...]}` döndür. Kimliğe göre sırala, boş bileşende boş liste döndür ve girdileri değiştirme.

Görünür veri: `veri/bilesenler.json` içindeki `surum_kayitlari`. `ozet-modeli-ayna` yalnız son karakterde ayrılır ve `butunluk` nedeni almalıdır. `yardimci-paket` için `risk` nedeni bir kez yazılmalıdır. `bozuk_kayitlar` reddedilmelidir.

```starter
from ai_savunma_veri import json_yukle

def surum_guvenlik_raporu(bilesenler, politika):
    # KUSURLU BAŞLANGIÇ KODU: özetleri yalnız ilk 12 karakterle karşılaştırıyor, büyük harfli özeti normalleştirip kabul ediyor ve her politika dışı risk için ayrı neden yazıyor!
    sonuc = []
    for b in bilesenler:
        nedenler = []
        if b["tur"] not in politika["izinli_turler"]:
            nedenler.append("tur")
        if b["kaynak"] not in politika["izinli_kaynaklar"]:
            nedenler.append("kaynak")
        if b["boyut_mb"] > politika["max_boyut_mb"]:
            nedenler.append("boyut")
        if not b["imzali"]:
            nedenler.append("imza")
        if b["beklenen_sha256"].lower()[:12] != b["gercek_sha256"].lower()[:12]:
            nedenler.append("butunluk")
        nedenler += ["risk" for r in b["riskler"] if r not in politika["izinli_riskler"]]
        sonuc.append({"id": b["id"], "karar": "karantina" if nedenler else "kabul", "nedenler": nedenler})
    return sorted(sonuc, key=lambda x: x["id"])

politika = json_yukle("veri/tedarik_politikasi.json")["politika"]
veri = json_yukle("veri/bilesenler.json")
for s in surum_guvenlik_raporu(veri["surum_kayitlari"], politika):
    print(s["id"], s["karar"], s["nedenler"])
for b in veri["bozuk_kayitlar"]:
    try:
        surum_guvenlik_raporu([b], politika)
        print(b["id"], "KABUL edildi (yanlış)")
    except ValueError as hata:
        print(b["id"], "reddedildi:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-20")
```

```test
import copy
P = {"izinli_kaynaklar": ["resmi", "kurumsal"], "izinli_turler": ["model", "paket"], "izinli_riskler": ["dusuk"], "max_boyut_mb": 1000, "imza_zorunlu": True}
B = [
    {"id": "kabul-1", "tur": "model", "kaynak": "resmi", "boyut_mb": 1000, "imzali": True, "beklenen_sha256": "a" * 64, "gercek_sha256": "a" * 64, "riskler": ["dusuk"]},
    {"id": "ozet-1", "tur": "paket", "kaynak": "kurumsal", "boyut_mb": 1, "imzali": True, "beklenen_sha256": "b" * 64, "gercek_sha256": "c" * 64, "riskler": []},
    {"id": "risk-1", "tur": "model", "kaynak": "resmi", "boyut_mb": 1, "imzali": True, "beklenen_sha256": "d" * 64, "gercek_sha256": "d" * 64, "riskler": ["orta", "kritik"]},
    {"id": "ret-1", "tur": "imaj", "kaynak": "yerel", "boyut_mb": 1001, "imzali": False, "beklenen_sha256": "e" * 64, "gercek_sha256": "f" * 64, "riskler": ["yuksek"]},
]
BEKLENEN = [
    {"id": "kabul-1", "karar": "kabul", "nedenler": []},
    {"id": "ozet-1", "karar": "karantina", "nedenler": ["butunluk"]},
    {"id": "ret-1", "karar": "karantina", "nedenler": ["tur", "kaynak", "boyut", "imza", "butunluk", "risk"]},
    {"id": "risk-1", "karar": "karantina", "nedenler": ["risk"]},
]
def sozlesme(fn):
    try:
        bonce = copy.deepcopy(B)
        ponce = copy.deepcopy(P)
        if fn(B, P) != BEKLENEN or B != bonce or P != ponce or fn(list(reversed(B)), P) != BEKLENEN or fn([], P) != []:
            return False
        if fn([dict(B[0], id="a" * 64, riskler=[])], dict(P, izinli_riskler=[]))[0]["karar"] != "kabul":
            return False
        if fn([dict(B[0], riskler=["dusuk"])], dict(P, izinli_riskler=[]))[0]["nedenler"] != ["risk"]:
            return False
        for alan, deger in [("izinli_riskler", []), ("max_boyut_mb", 1), ("max_boyut_mb", 10000)]:
            if fn([], dict(P, **{alan: deger})) != []:
                return False
        for bilesenler, politika in [
            (None, P), ({}, P), ([None], P), (B, None), (B, dict(P, imza_zorunlu=False)),
            (B, dict(P, izinli_kaynaklar=[])), (B, dict(P, izinli_turler=[])),
            (B, dict(P, izinli_riskler=["bilinmeyen"])), (B, dict(P, max_boyut_mb=0)), (B, dict(P, max_boyut_mb=10001)),
            ([dict(B[0], ek=1)], P), ([dict(B[0], id="a b")], P), ([dict(B[0], id="a" * 65)], P),
            ([B[0], B[0]], P), ([dict(B[0], tur="dosya")], P), ([dict(B[0], kaynak="bilinmeyen")], P),
            ([dict(B[0], boyut_mb=0)], P), ([dict(B[0], boyut_mb=True)], P), ([dict(B[0], imzali=1)], P),
            ([dict(B[0], beklenen_sha256="a" * 63)], P), ([dict(B[0], gercek_sha256="A" * 64)], P),
            ([dict(B[0], riskler=None)], P), ([dict(B[0], riskler=["bilinmeyen"])], P),
            ([dict(B[0], riskler=["dusuk", "dusuk"])], P),
        ]:
            try:
                fn(bilesenler, politika)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(surum_guvenlik_raporu), "kaynak, imza, bütünlük ve risk kararları korunmalı")
def m_ozet(bilesenler, politika):
    return surum_guvenlik_raporu([dict(x, gercek_sha256=x["beklenen_sha256"]) for x in bilesenler], politika)
def m_risk(bilesenler, politika):
    return surum_guvenlik_raporu([dict(x, riskler=[]) for x in bilesenler], politika)
def m_imza(bilesenler, politika):
    return surum_guvenlik_raporu([dict(x, imzali=True) for x in bilesenler], politika)
for ad, mutant in [("özeti eşitleyen", m_ozet), ("riski silen", m_risk), ("imzayı silen", m_imza)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
raises(ValueError,surum_guvenlik_raporu,[{'id': 'kabul-1', 'tur': 'model', 'kaynak': 'resmi', 'boyut_mb': 1000, 'imzali': True, 'beklenen_sha256': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'gercek_sha256': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'riskler': ['dusuk']}, {'id': 'ozet-1', 'tur': 'paket', 'kaynak': 'kurumsal', 'boyut_mb': 1, 'imzali': True, 'beklenen_sha256': 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', 'gercek_sha256': 'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc', 'riskler': []}, {'id': 'risk-1', 'tur': 'model', 'kaynak': 'resmi', 'boyut_mb': 1, 'imzali': True, 'beklenen_sha256': 'dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd', 'gercek_sha256': 'dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd', 'riskler': ['orta', 'kritik']}, {'id': 'ret-1', 'tur': 'imaj', 'kaynak': 'yerel', 'boyut_mb': 1001, 'imzali': False, 'beklenen_sha256': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee', 'gercek_sha256': 'ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff', 'riskler': ['yuksek']}],{'izinli_kaynaklar': None, 'izinli_turler': ['model', 'paket'], 'izinli_riskler': ['dusuk'], 'max_boyut_mb': 1000, 'imza_zorunlu': True},msg="hatalı alan ValueError sözleşmesi: mutant:368:29:Add->Sub")
raises(ValueError,surum_guvenlik_raporu,[{'id': 'kabul-1', 'tur': 'model', 'kaynak': 'resmi', 'boyut_mb': 1000, 'imzali': True, 'beklenen_sha256': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'gercek_sha256': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'riskler': ['dusuk']}, {'id': 'ozet-1', 'tur': 'paket', 'kaynak': 'kurumsal', 'boyut_mb': 1, 'imzali': True, 'beklenen_sha256': 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', 'gercek_sha256': 'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc', 'riskler': []}, {'id': 'risk-1', 'tur': 'model', 'kaynak': 'resmi', 'boyut_mb': 1, 'imzali': True, 'beklenen_sha256': 'dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd', 'gercek_sha256': 'dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd', 'riskler': ['orta', 'kritik']}, {'id': 'ret-1', 'tur': 'imaj', 'kaynak': 'yerel', 'boyut_mb': 1001, 'imzali': False, 'beklenen_sha256': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee', 'gercek_sha256': 'ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff', 'riskler': ['yuksek']}],{'izinli_kaynaklar': ['x', 'x'], 'izinli_turler': ['model', 'paket'], 'izinli_riskler': ['dusuk'], 'max_boyut_mb': 1000, 'imza_zorunlu': True},msg="hatalı alan ValueError sözleşmesi: mutant:380:29:Add->Sub")
raises(ValueError,surum_guvenlik_raporu,[{'id': 'kabul-1', 'tur': 'model', 'kaynak': 'resmi', 'boyut_mb': 1000, 'imzali': True, 'beklenen_sha256': None, 'gercek_sha256': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'riskler': ['dusuk']}, {'id': 'ozet-1', 'tur': 'paket', 'kaynak': 'kurumsal', 'boyut_mb': 1, 'imzali': True, 'beklenen_sha256': 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', 'gercek_sha256': 'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc', 'riskler': []}, {'id': 'risk-1', 'tur': 'model', 'kaynak': 'resmi', 'boyut_mb': 1, 'imzali': True, 'beklenen_sha256': 'dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd', 'gercek_sha256': 'dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd', 'riskler': ['orta', 'kritik']}, {'id': 'ret-1', 'tur': 'imaj', 'kaynak': 'yerel', 'boyut_mb': 1001, 'imzali': False, 'beklenen_sha256': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee', 'gercek_sha256': 'ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff', 'riskler': ['yuksek']}],{'izinli_kaynaklar': ['resmi', 'kurumsal'], 'izinli_turler': ['model', 'paket'], 'izinli_riskler': ['dusuk'], 'max_boyut_mb': 1000, 'imza_zorunlu': True},msg="hatalı alan ValueError sözleşmesi: mutant:613:33:Add->Sub")
# --- carbon-c8-ek-bas ---
raises(ValueError, surum_guvenlik_raporu, B, dict(P, izinli_kaynaklar=[123]), msg="izinli kaynak str olmalı")
raises(ValueError, surum_guvenlik_raporu, B, dict(P, izinli_turler=[123]), msg="izinli tür str olmalı")
raises(ValueError, surum_guvenlik_raporu, B, dict(P, izinli_riskler=[123]), msg="izinli risk str olmalı")
raises(ValueError, surum_guvenlik_raporu, B, dict(P, max_boyut_mb=True), msg="max_boyut_mb bool ret")
raises(ValueError, surum_guvenlik_raporu, [dict(B[0], id=123)], P, msg="id str olmalı")
raises(ValueError, surum_guvenlik_raporu, [dict(B[0], tur=123)], P, msg="tür str olmalı")
raises(ValueError, surum_guvenlik_raporu, [dict(B[0], kaynak=123)], P, msg="kaynak str olmalı")
raises(ValueError, surum_guvenlik_raporu, [dict(B[0], boyut_mb=True)], P, msg="boyut_mb bool ret")
raises(ValueError, surum_guvenlik_raporu, [dict(B[0], beklenen_sha256=123)], P, msg="beklenen_sha256 str olmalı")
raises(ValueError, surum_guvenlik_raporu, [dict(B[0], gercek_sha256=123)], P, msg="gercek_sha256 str olmalı")
raises(ValueError, surum_guvenlik_raporu, [dict(B[0], riskler=[123])], P, msg="risk elemanı str olmalı")
raises(ValueError, surum_guvenlik_raporu, B, dict(P, ek=1), msg="politika fazla alan ret")
raises(ValueError, surum_guvenlik_raporu, B, dict(P, izinli_kaynaklar=tuple(P["izinli_kaynaklar"])), msg="izinli_kaynaklar tuple olamaz")
raises(ValueError, surum_guvenlik_raporu, B, dict(P, izinli_kaynaklar=P["izinli_kaynaklar"] + [P["izinli_kaynaklar"][0]]), msg="yinelenen izinli kaynak ret")
# --- carbon-c8-ek-son ---
```

```solution
def surum_guvenlik_raporu(bilesenler, politika):
    import re
    if not isinstance(politika, dict):
        raise ValueError("politika sözlük olmalı")
    if set(politika) != {"izinli_kaynaklar", "izinli_turler", "izinli_riskler", "max_boyut_mb", "imza_zorunlu"}:
        raise ValueError("politika şeması geçersiz")
    for alan, izinler, bos_olabilir in [
        ("izinli_kaynaklar", ("resmi", "kurumsal", "yerel"), False),
        ("izinli_turler", ("model", "imaj", "paket"), False),
        ("izinli_riskler", ("dusuk", "orta", "yuksek", "kritik"), True),
    ]:
        degerler = politika[alan]
        if not isinstance(degerler, list):
            raise ValueError(alan + " liste olmalı")
        if not degerler and not bos_olabilir:
            raise ValueError(alan + " boş olamaz")
        if len(set(degerler)) != len(degerler):
            raise ValueError(alan + " yinelenemez")
        if any(deger not in izinler for deger in degerler):
            raise ValueError(alan + " geçersiz değer içeriyor")
    if type(politika["max_boyut_mb"]) is not int:
        raise ValueError("boyut sınırı int olmalı")
    if politika["max_boyut_mb"] < 1:
        raise ValueError("boyut sınırı pozitif olmalı")
    if politika["max_boyut_mb"] > 10000:
        raise ValueError("boyut sınırı çok büyük")
    if politika["imza_zorunlu"] is not True:
        raise ValueError("imza zorunlu olmalı")
    if not isinstance(bilesenler, list):
        raise ValueError("bileşenler liste olmalı")
    kimlikler = set()
    sonuc = []
    for bilesen in bilesenler:
        if not isinstance(bilesen, dict):
            raise ValueError("bileşen sözlük olmalı")
        if set(bilesen) != {"id", "tur", "kaynak", "boyut_mb", "imzali", "beklenen_sha256", "gercek_sha256", "riskler"}:
            raise ValueError("bileşen şeması geçersiz")
        kimlik = bilesen["id"]
        if not isinstance(kimlik, str):
            raise ValueError("kimlik string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kimlik):
            raise ValueError("kimlik geçersiz")
        if kimlik in kimlikler:
            raise ValueError("kimlik yinelenemez")
        kimlikler.add(kimlik)
        if bilesen["tur"] not in ("model", "imaj", "paket"):
            raise ValueError("tür geçersiz")
        if bilesen["kaynak"] not in ("resmi", "kurumsal", "yerel"):
            raise ValueError("kaynak geçersiz")
        if type(bilesen["boyut_mb"]) is not int:
            raise ValueError("boyut int olmalı")
        if bilesen["boyut_mb"] < 1:
            raise ValueError("boyut pozitif olmalı")
        if type(bilesen["imzali"]) is not bool:
            raise ValueError("imza bool olmalı")
        for alan in ("beklenen_sha256", "gercek_sha256"):
            if not isinstance(bilesen[alan], str):
                raise ValueError(alan + " string olmalı")
            if not re.fullmatch(r"[0-9a-f]{64}", bilesen[alan]):
                raise ValueError(alan + " geçersiz")
        riskler = bilesen["riskler"]
        if not isinstance(riskler, list):
            raise ValueError("riskler liste olmalı")
        if len(set(riskler)) != len(riskler):
            raise ValueError("riskler yinelenemez")
        if any(risk not in ("dusuk", "orta", "yuksek", "kritik") for risk in riskler):
            raise ValueError("risk geçersiz")
        nedenler = []
        if bilesen["tur"] not in politika["izinli_turler"]:
            nedenler.append("tur")
        if bilesen["kaynak"] not in politika["izinli_kaynaklar"]:
            nedenler.append("kaynak")
        if bilesen["boyut_mb"] > politika["max_boyut_mb"]:
            nedenler.append("boyut")
        if not bilesen["imzali"]:
            nedenler.append("imza")
        if bilesen["beklenen_sha256"] != bilesen["gercek_sha256"]:
            nedenler.append("butunluk")
        if any(risk not in politika["izinli_riskler"] for risk in riskler):
            nedenler.append("risk")
        sonuc.append({"id": kimlik, "karar": "karantina" if nedenler else "kabul", "nedenler": nedenler})
    return sorted(sonuc, key=lambda x: x["id"])
```

```hint
İki özeti ayrı ayrı doğrulayıp sonra karşılaştır. Politika dışı en az bir risk varsa tek `risk` nedeni ekle; diğer nedenleri koru.
```
:::

::: anlat Bütünlük kâğıt üstünde değil, kurulu modelin gerçek özetiyle doğrulanır
Görev 1–3'te özetler JSON dosyasında hazır yazılıydı. Bu adımda özetleri **gerçek dosyalardan** hesaplıyoruz. Ollama bir modeli Docker/OCI dağıtım manifest'iyle saklar. Manifest her katmanı (ağırlık dosyası, sohbet şablonu, lisans, parametreler, config) `sha256:<hex>` özetiyle adresler ve dosyalar `models/blobs/sha256-<hex>` adıyla diskte durur. `sandbox/ai_gercek_ai_savunma_20.py` deneyi şunları yapar:

1. Yerel Ollama sunucusundan kurulu sohbet modelinin adını alır. Modeli yüklemez ve sohbet çağrısı yapmaz.
2. O modelin manifest dosyasını salt okunur açar. **Beklenen** özetler buradan gelir.
3. Her katmanın blob dosyasını baştan sona okuyup SHA-256'sını **gerçekten hesaplar**. Ağırlık dosyası da dahildir; birkaç GB'lık dosya akışla okunur ve süre kanıta yazılır.
4. Tahrifat senaryosu için en küçük katmanın geçici bir **kopyasını** oluşturur, son baytını değiştirir ve kopyanın özetini hesaplar. Kullanıcının dosyalarına yazılmaz; kopya hemen silinir.
5. Katmanları ve tahrif kopyasını senin `surum_guvenlik_raporu` işlevine, 3. görevdeki politikanın gerçek deney sürümüyle verir.

Okunan manifest'te imza bilgisi yoktur, bu yüzden `imzali` alanı dürüstçe `False` yazılır. İmza zorunlu politika her katmana `imza` nedeni ekler. Bu, deneyin bir hatası değil, gerçek bir bulgudur: Ollama katmanları özetle adreslenir ama bu yerel kopyada imzayla doğrulanmaz. Zafiyet taraması yapılmadığı için `riskler` boş listedir ve kanıtta "tarama yapılmadı" diye işaretlenir.

Test önce işlevini gizli deterministik kayıtlarla sınar. Ardından gerçek katmanlardan ürettiğin raporu bağımsız bir referans hesapla birebir karşılaştırır. Tahrif kopyası `butunluk` nedeni almak zorundadır. Diskteki bir katman gerçekten bozuksa doğru rapor onu da `butunluk` ile işaretler; bu da kabul edilir, çünkü ölçüm doğrudur. Kanıta her katmanın manifest özeti, hesaplanan özeti, dosya boyutu ve hesaplama süresi yazılır.

Ders yazılırken bu makinede `qwen3:4b-instruct-2507-q4_K_M` modelinin 6 katmanının 6'sı manifest'le eşleşti. 2382 MB'lık ağırlık dosyasının özeti yaklaşık 2,2 saniyede hesaplandı. Tahrif kopyası `["imza", "butunluk"]` nedenleriyle karantinaya alındı. Kendi makinende model ve sayılar farklı olabilir.

:::

::: gorev Gerçek deney · Kurulu modelin gerçek digest'iyle bütünlük
`surum_guvenlik_raporu(bilesenler, politika)` işlevini yaz. Kuralları ve çıktısı 3. görevdekiyle **aynıdır**. Deney kurulu modelin her katmanının SHA-256 özetini gerçekten hesaplar ve tahrif edilmiş bir kopya ekler. Senin işlevin bu gerçek kayıtlardan kararları üretir. `sandbox.ai_gercek_ai_savunma_20` içindeki `surum_guvenlik_raporu_referans` yalnız test içindir; onu import etmek veya kaynağını okuyup çalıştırmak Kontrol'de reddedilir.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab

def surum_guvenlik_raporu(bilesenler, politika):
    # KUSURLU BAŞLANGIÇ KODU: şema doğrulaması yok, imza alanını hiç denetlemiyor ve özetleri yalnız ilk 12 karakterle karşılaştırıyor!
    sonuc = []
    for b in bilesenler:
        nedenler = [n for n, kosul in (("tur", b["tur"] not in politika["izinli_turler"]),
                                        ("kaynak", b["kaynak"] not in politika["izinli_kaynaklar"]),
                                        ("boyut", b["boyut_mb"] > politika["max_boyut_mb"]),
                                        ("butunluk", b["beklenen_sha256"][:12] != b["gercek_sha256"][:12]),
                                        ("risk", any(r not in politika["izinli_riskler"] for r in b["riskler"]))) if kosul]
        sonuc.append({"id": b["id"], "karar": "karantina" if nedenler else "kabul", "nedenler": nedenler})
    return sorted(sonuc, key=lambda x: x["id"])

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_20 as deney
    deney.goster(surum_guvenlik_raporu)
```

```test
import ast
import ai_lab
from sandbox import ai_gercek_ai_savunma_20 as D
sonuclar = []
def kontrol(kosul, mesaj):
    sonuclar.append(bool(kosul))
    return ok(kosul, mesaj)
_yasak = ("surum_guvenlik_raporu_referans", "kanit_yaz")
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
if not kontrol(not sorun, "Kendi surum_guvenlik_raporu işlevini yaz; laboratuvar/referans kullanımı yasak: " + "; ".join(sorted(set(sorun)))):
    stop()
fn = need("surum_guvenlik_raporu")
P = {"izinli_kaynaklar": ["resmi", "kurumsal"], "izinli_turler": ["model", "paket"], "izinli_riskler": ["dusuk"], "max_boyut_mb": 10000, "imza_zorunlu": True}
B = [
    {"id": "kabul-1", "tur": "model", "kaynak": "resmi", "boyut_mb": 1000, "imzali": True, "beklenen_sha256": "a" * 64, "gercek_sha256": "a" * 64, "riskler": ["dusuk"]},
    {"id": "ozet-1", "tur": "paket", "kaynak": "kurumsal", "boyut_mb": 1, "imzali": True, "beklenen_sha256": "b" * 64, "gercek_sha256": "c" * 64, "riskler": []},
]
BEKLENEN = [
    {"id": "kabul-1", "karar": "kabul", "nedenler": []},
    {"id": "ozet-1", "karar": "karantina", "nedenler": ["butunluk"]},
]
def sozlesme(f):
    try:
        if f(B, P) != BEKLENEN or f([], P) != []:
            return False
        son_bayt = dict(B[0], id="son-1", beklenen_sha256="d" * 63 + "e", gercek_sha256="d" * 63 + "f", imzali=False,
                        boyut_mb=10000, riskler=["kritik", "orta", "dusuk"])
        if f([son_bayt], P) != [{"id": "son-1", "karar": "karantina", "nedenler": ["imza", "butunluk", "risk"]}]:
            return False
        if f([dict(B[0], tur="imaj", kaynak="yerel", boyut_mb=10001)], P)[0]["nedenler"] != ["tur", "kaynak", "boyut"]:
            return False
        for bozuk in (None, [None], [dict(B[0], ek=1)], [dict(B[0], gercek_sha256="A" * 64)], [dict(B[0], riskler=["dusuk", "dusuk"])],
                      [dict(B[0], beklenen_sha256="a" * 63)], [dict(B[0], imzali=1)], [dict(B[0], boyut_mb=True)], [B[0], B[0]]):
            try:
                f(bozuk, P)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
kontrol(sozlesme(fn), "kaynak, imza, bütünlük ve risk kararları korunmalı")
r, oz = None, None
# --- carbon-c8-g4-bas ---
def _c8_birim_denetimi():
    _u = []
    def _same(got, exp):
        try:
            if not bool(got == exp):
                return False
        except Exception:
            return False
        if isinstance(exp, bool) or isinstance(got, bool):
            return isinstance(got, bool) and isinstance(exp, bool)
        if isinstance(exp, (int, float)) and isinstance(got, (int, float)):
            return True
        return isinstance(got, type(exp))
    def ok(cond, msg=None, got=None):
        _u.append(bool(cond))
        return bool(cond)
    def eq(got, exp, msg=None):
        r = _same(got, exp)
        _u.append(r)
        return r
    def yakin(got, exp, msg=None, tol=1e-6):
        try:
            r = abs(got - exp) <= tol
        except Exception:
            r = False
        _u.append(bool(r))
        return bool(r)
    def raises(exc, fn_cagri, *a, msg=None, **kw):
        try:
            fn_cagri(*a, **kw)
        except exc:
            _u.append(True)
            return True
        except Exception:
            _u.append(False)
            return False
        _u.append(False)
        return False
    surum_guvenlik_raporu = need('surum_guvenlik_raporu')
    def _birim_adim_3():
        import copy
        P = {"izinli_kaynaklar": ["resmi", "kurumsal"], "izinli_turler": ["model", "paket"], "izinli_riskler": ["dusuk"], "max_boyut_mb": 1000, "imza_zorunlu": True}
        B = [
            {"id": "kabul-1", "tur": "model", "kaynak": "resmi", "boyut_mb": 1000, "imzali": True, "beklenen_sha256": "a" * 64, "gercek_sha256": "a" * 64, "riskler": ["dusuk"]},
            {"id": "ozet-1", "tur": "paket", "kaynak": "kurumsal", "boyut_mb": 1, "imzali": True, "beklenen_sha256": "b" * 64, "gercek_sha256": "c" * 64, "riskler": []},
            {"id": "risk-1", "tur": "model", "kaynak": "resmi", "boyut_mb": 1, "imzali": True, "beklenen_sha256": "d" * 64, "gercek_sha256": "d" * 64, "riskler": ["orta", "kritik"]},
            {"id": "ret-1", "tur": "imaj", "kaynak": "yerel", "boyut_mb": 1001, "imzali": False, "beklenen_sha256": "e" * 64, "gercek_sha256": "f" * 64, "riskler": ["yuksek"]},
        ]
        BEKLENEN = [
            {"id": "kabul-1", "karar": "kabul", "nedenler": []},
            {"id": "ozet-1", "karar": "karantina", "nedenler": ["butunluk"]},
            {"id": "ret-1", "karar": "karantina", "nedenler": ["tur", "kaynak", "boyut", "imza", "butunluk", "risk"]},
            {"id": "risk-1", "karar": "karantina", "nedenler": ["risk"]},
        ]
        def sozlesme(fn):
            try:
                bonce = copy.deepcopy(B)
                ponce = copy.deepcopy(P)
                if fn(B, P) != BEKLENEN or B != bonce or P != ponce or fn(list(reversed(B)), P) != BEKLENEN or fn([], P) != []:
                    return False
                if fn([dict(B[0], id="a" * 64, riskler=[])], dict(P, izinli_riskler=[]))[0]["karar"] != "kabul":
                    return False
                if fn([dict(B[0], riskler=["dusuk"])], dict(P, izinli_riskler=[]))[0]["nedenler"] != ["risk"]:
                    return False
                for alan, deger in [("izinli_riskler", []), ("max_boyut_mb", 1), ("max_boyut_mb", 10000)]:
                    if fn([], dict(P, **{alan: deger})) != []:
                        return False
                for bilesenler, politika in [
                    (None, P), ({}, P), ([None], P), (B, None), (B, dict(P, imza_zorunlu=False)),
                    (B, dict(P, izinli_kaynaklar=[])), (B, dict(P, izinli_turler=[])),
                    (B, dict(P, izinli_riskler=["bilinmeyen"])), (B, dict(P, max_boyut_mb=0)), (B, dict(P, max_boyut_mb=10001)),
                    ([dict(B[0], ek=1)], P), ([dict(B[0], id="a b")], P), ([dict(B[0], id="a" * 65)], P),
                    ([B[0], B[0]], P), ([dict(B[0], tur="dosya")], P), ([dict(B[0], kaynak="bilinmeyen")], P),
                    ([dict(B[0], boyut_mb=0)], P), ([dict(B[0], boyut_mb=True)], P), ([dict(B[0], imzali=1)], P),
                    ([dict(B[0], beklenen_sha256="a" * 63)], P), ([dict(B[0], gercek_sha256="A" * 64)], P),
                    ([dict(B[0], riskler=None)], P), ([dict(B[0], riskler=["bilinmeyen"])], P),
                    ([dict(B[0], riskler=["dusuk", "dusuk"])], P),
                ]:
                    try:
                        fn(bilesenler, politika)
                        return False
                    except ValueError:
                        pass
                return True
            except Exception:
                return False
        ok(sozlesme(surum_guvenlik_raporu), "kaynak, imza, bütünlük ve risk kararları korunmalı")
        def m_ozet(bilesenler, politika):
            return surum_guvenlik_raporu([dict(x, gercek_sha256=x["beklenen_sha256"]) for x in bilesenler], politika)
        def m_risk(bilesenler, politika):
            return surum_guvenlik_raporu([dict(x, riskler=[]) for x in bilesenler], politika)
        def m_imza(bilesenler, politika):
            return surum_guvenlik_raporu([dict(x, imzali=True) for x in bilesenler], politika)
        for ad, mutant in [("özeti eşitleyen", m_ozet), ("riski silen", m_risk), ("imzayı silen", m_imza)]:
            ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
        raises(ValueError,surum_guvenlik_raporu,[{'id': 'kabul-1', 'tur': 'model', 'kaynak': 'resmi', 'boyut_mb': 1000, 'imzali': True, 'beklenen_sha256': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'gercek_sha256': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'riskler': ['dusuk']}, {'id': 'ozet-1', 'tur': 'paket', 'kaynak': 'kurumsal', 'boyut_mb': 1, 'imzali': True, 'beklenen_sha256': 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', 'gercek_sha256': 'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc', 'riskler': []}, {'id': 'risk-1', 'tur': 'model', 'kaynak': 'resmi', 'boyut_mb': 1, 'imzali': True, 'beklenen_sha256': 'dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd', 'gercek_sha256': 'dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd', 'riskler': ['orta', 'kritik']}, {'id': 'ret-1', 'tur': 'imaj', 'kaynak': 'yerel', 'boyut_mb': 1001, 'imzali': False, 'beklenen_sha256': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee', 'gercek_sha256': 'ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff', 'riskler': ['yuksek']}],{'izinli_kaynaklar': None, 'izinli_turler': ['model', 'paket'], 'izinli_riskler': ['dusuk'], 'max_boyut_mb': 1000, 'imza_zorunlu': True},msg="hatalı alan ValueError sözleşmesi: mutant:368:29:Add->Sub")
        raises(ValueError,surum_guvenlik_raporu,[{'id': 'kabul-1', 'tur': 'model', 'kaynak': 'resmi', 'boyut_mb': 1000, 'imzali': True, 'beklenen_sha256': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'gercek_sha256': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'riskler': ['dusuk']}, {'id': 'ozet-1', 'tur': 'paket', 'kaynak': 'kurumsal', 'boyut_mb': 1, 'imzali': True, 'beklenen_sha256': 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', 'gercek_sha256': 'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc', 'riskler': []}, {'id': 'risk-1', 'tur': 'model', 'kaynak': 'resmi', 'boyut_mb': 1, 'imzali': True, 'beklenen_sha256': 'dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd', 'gercek_sha256': 'dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd', 'riskler': ['orta', 'kritik']}, {'id': 'ret-1', 'tur': 'imaj', 'kaynak': 'yerel', 'boyut_mb': 1001, 'imzali': False, 'beklenen_sha256': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee', 'gercek_sha256': 'ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff', 'riskler': ['yuksek']}],{'izinli_kaynaklar': ['x', 'x'], 'izinli_turler': ['model', 'paket'], 'izinli_riskler': ['dusuk'], 'max_boyut_mb': 1000, 'imza_zorunlu': True},msg="hatalı alan ValueError sözleşmesi: mutant:380:29:Add->Sub")
        raises(ValueError,surum_guvenlik_raporu,[{'id': 'kabul-1', 'tur': 'model', 'kaynak': 'resmi', 'boyut_mb': 1000, 'imzali': True, 'beklenen_sha256': None, 'gercek_sha256': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'riskler': ['dusuk']}, {'id': 'ozet-1', 'tur': 'paket', 'kaynak': 'kurumsal', 'boyut_mb': 1, 'imzali': True, 'beklenen_sha256': 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', 'gercek_sha256': 'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc', 'riskler': []}, {'id': 'risk-1', 'tur': 'model', 'kaynak': 'resmi', 'boyut_mb': 1, 'imzali': True, 'beklenen_sha256': 'dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd', 'gercek_sha256': 'dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd', 'riskler': ['orta', 'kritik']}, {'id': 'ret-1', 'tur': 'imaj', 'kaynak': 'yerel', 'boyut_mb': 1001, 'imzali': False, 'beklenen_sha256': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee', 'gercek_sha256': 'ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff', 'riskler': ['yuksek']}],{'izinli_kaynaklar': ['resmi', 'kurumsal'], 'izinli_turler': ['model', 'paket'], 'izinli_riskler': ['dusuk'], 'max_boyut_mb': 1000, 'imza_zorunlu': True},msg="hatalı alan ValueError sözleşmesi: mutant:613:33:Add->Sub")
        raises(ValueError, surum_guvenlik_raporu, B, dict(P, izinli_kaynaklar=[123]), msg="izinli kaynak str olmalı")
        raises(ValueError, surum_guvenlik_raporu, B, dict(P, izinli_turler=[123]), msg="izinli tür str olmalı")
        raises(ValueError, surum_guvenlik_raporu, B, dict(P, izinli_riskler=[123]), msg="izinli risk str olmalı")
        raises(ValueError, surum_guvenlik_raporu, B, dict(P, max_boyut_mb=True), msg="max_boyut_mb bool ret")
        raises(ValueError, surum_guvenlik_raporu, [dict(B[0], id=123)], P, msg="id str olmalı")
        raises(ValueError, surum_guvenlik_raporu, [dict(B[0], tur=123)], P, msg="tür str olmalı")
        raises(ValueError, surum_guvenlik_raporu, [dict(B[0], kaynak=123)], P, msg="kaynak str olmalı")
        raises(ValueError, surum_guvenlik_raporu, [dict(B[0], boyut_mb=True)], P, msg="boyut_mb bool ret")
        raises(ValueError, surum_guvenlik_raporu, [dict(B[0], beklenen_sha256=123)], P, msg="beklenen_sha256 str olmalı")
        raises(ValueError, surum_guvenlik_raporu, [dict(B[0], gercek_sha256=123)], P, msg="gercek_sha256 str olmalı")
        raises(ValueError, surum_guvenlik_raporu, [dict(B[0], riskler=[123])], P, msg="risk elemanı str olmalı")
        raises(ValueError, surum_guvenlik_raporu, B, dict(P, ek=1), msg="politika fazla alan ret")
        raises(ValueError, surum_guvenlik_raporu, B, dict(P, izinli_kaynaklar=tuple(P["izinli_kaynaklar"])), msg="izinli_kaynaklar tuple olamaz")
        raises(ValueError, surum_guvenlik_raporu, B, dict(P, izinli_kaynaklar=P["izinli_kaynaklar"] + [P["izinli_kaynaklar"][0]]), msg="yinelenen izinli kaynak ret")
    try:
        _birim_adim_3()
    except Exception:
        _u.append(False)
    return bool(_u) and all(_u)
kontrol(_c8_birim_denetimi(), "deney öncesi tam birim sözleşmesi korunmalı")
# --- carbon-c8-g4-son ---
if all(sonuclar):
    try:
        r = D.deney(fn)
    except ai_lab.GercekLabYok as e:
        kontrol(False, f"GERÇEK MODEL YOK, deney yapılmadı: {e}")
        stop()
    kontrol(len(r["olcumler"]) >= 3 and any(o["id"] == "agirlik" for o in r["olcumler"]),
            "ağırlık dahil gerçek katman dosyalarının SHA-256 özeti hesaplandı")
    kontrol(r["tahrif_karar"] == "karantina" and "butunluk" in (r["tahrif_nedenler"] or []),
            "son baytı değişen tahrif kopyası bütünlük nedeniyle karantinaya alındı")
    bagimsiz = D.surum_guvenlik_raporu_referans([dict(b, riskler=list(b["riskler"])) for b in r["bilesenler"]], dict(D.POLITIKA))
    kontrol(r["rapor"] == bagimsiz, f"gerçek katmanlardaki rapor bağımsız hesapla aynı olmalı: senin {r['rapor']} · beklenen {bagimsiz}")
    oz = D.ozet(r)
yol = ai_lab.kanit_yaz("savunma-tedarik", {"kaynak": "gercek", "kabul": all(sonuclar), "ders": "ai-savunma-20",
                                           "ortam": (r or {}).get("ortam"), "ozet": oz,
                                           "olcumler": (r or {}).get("olcumler"), "rapor": (r or {}).get("rapor")})
if oz:
    ok(True, f"BULGU (kurulu model {oz['model']}): {oz['katman_sayisi']} katmanın {oz['eslesen_katman']}'i manifest'le eşleşti; "
             f"ağırlık ~{oz['agirlik_mb']} MB, SHA-256 {oz['agirlik_ozet_onek']} ({oz['agirlik_hash_sn']} sn). "
             f"Tahrif kopyası → {oz['tahrif_karar']} {oz['tahrif_nedenler']}. İmza bilgisi olmadığı için katmanlar 'imza' nedeniyle karantinada.")
```

```solution
import ai_lab

def surum_guvenlik_raporu(bilesenler, politika):
    import re
    if not isinstance(politika, dict):
        raise ValueError("politika sözlük olmalı")
    if set(politika) != {"izinli_kaynaklar", "izinli_turler", "izinli_riskler", "max_boyut_mb", "imza_zorunlu"}:
        raise ValueError("politika şeması geçersiz")
    for alan, izinler, bos_olabilir in [
        ("izinli_kaynaklar", ("resmi", "kurumsal", "yerel"), False),
        ("izinli_turler", ("model", "imaj", "paket"), False),
        ("izinli_riskler", ("dusuk", "orta", "yuksek", "kritik"), True),
    ]:
        degerler = politika[alan]
        if not isinstance(degerler, list):
            raise ValueError(alan + " liste olmalı")
        if not degerler and not bos_olabilir:
            raise ValueError(alan + " boş olamaz")
        if len(set(degerler)) != len(degerler):
            raise ValueError(alan + " yinelenemez")
        if any(deger not in izinler for deger in degerler):
            raise ValueError(alan + " geçersiz değer içeriyor")
    if type(politika["max_boyut_mb"]) is not int:
        raise ValueError("boyut sınırı int olmalı")
    if politika["max_boyut_mb"] < 1:
        raise ValueError("boyut sınırı pozitif olmalı")
    if politika["max_boyut_mb"] > 10000:
        raise ValueError("boyut sınırı çok büyük")
    if politika["imza_zorunlu"] is not True:
        raise ValueError("imza zorunlu olmalı")
    if not isinstance(bilesenler, list):
        raise ValueError("bileşenler liste olmalı")
    kimlikler = set()
    sonuc = []
    for bilesen in bilesenler:
        if not isinstance(bilesen, dict):
            raise ValueError("bileşen sözlük olmalı")
        if set(bilesen) != {"id", "tur", "kaynak", "boyut_mb", "imzali", "beklenen_sha256", "gercek_sha256", "riskler"}:
            raise ValueError("bileşen şeması geçersiz")
        kimlik = bilesen["id"]
        if not isinstance(kimlik, str):
            raise ValueError("kimlik string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kimlik):
            raise ValueError("kimlik geçersiz")
        if kimlik in kimlikler:
            raise ValueError("kimlik yinelenemez")
        kimlikler.add(kimlik)
        if bilesen["tur"] not in ("model", "imaj", "paket"):
            raise ValueError("tür geçersiz")
        if bilesen["kaynak"] not in ("resmi", "kurumsal", "yerel"):
            raise ValueError("kaynak geçersiz")
        if type(bilesen["boyut_mb"]) is not int:
            raise ValueError("boyut int olmalı")
        if bilesen["boyut_mb"] < 1:
            raise ValueError("boyut pozitif olmalı")
        if type(bilesen["imzali"]) is not bool:
            raise ValueError("imza bool olmalı")
        for alan in ("beklenen_sha256", "gercek_sha256"):
            if not isinstance(bilesen[alan], str):
                raise ValueError(alan + " string olmalı")
            if not re.fullmatch(r"[0-9a-f]{64}", bilesen[alan]):
                raise ValueError(alan + " geçersiz")
        riskler = bilesen["riskler"]
        if not isinstance(riskler, list):
            raise ValueError("riskler liste olmalı")
        if len(set(riskler)) != len(riskler):
            raise ValueError("riskler yinelenemez")
        if any(risk not in ("dusuk", "orta", "yuksek", "kritik") for risk in riskler):
            raise ValueError("risk geçersiz")
        nedenler = []
        if bilesen["tur"] not in politika["izinli_turler"]:
            nedenler.append("tur")
        if bilesen["kaynak"] not in politika["izinli_kaynaklar"]:
            nedenler.append("kaynak")
        if bilesen["boyut_mb"] > politika["max_boyut_mb"]:
            nedenler.append("boyut")
        if not bilesen["imzali"]:
            nedenler.append("imza")
        if bilesen["beklenen_sha256"] != bilesen["gercek_sha256"]:
            nedenler.append("butunluk")
        if any(risk not in politika["izinli_riskler"] for risk in riskler):
            nedenler.append("risk")
        sonuc.append({"id": kimlik, "karar": "karantina" if nedenler else "kabul", "nedenler": nedenler})
    return sorted(sonuc, key=lambda x: x["id"])

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_20 as deney
    deney.goster(surum_guvenlik_raporu)
```

```hint
Bu işlev 3. görevdeki `surum_guvenlik_raporu` ile birebir aynıdır; tek fark, katmanların gerçek özetinin kurulu modelin dosyalarından hesaplanmasıdır. İki özeti ayrı doğrula, sonra karşılaştır; politika dışı riskte tek `risk` nedeni ekle.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
### Digest eşleşmesi tedarik politikasının bir koşuludur

Gerçek model digestini beklenen sürümle karşılaştırmak bytes kimliğini bağlar. Kaynak onayı, zafiyet politikası ve sürüm kararı bu eşitlikten bağımsızdır. Bilinen kötü bir dosyanın hashini kusursuz eşleştirmek onu güvenli yapmaz. Kurulu modelin değişmediği ile bütün tedarik zincirinin güvenilirliği ayrı iddialardır.

| Yaygın yanlış | Mekanizmanın sınırı |
|---|---|
| Hash doğruysa bütün bileşen güvenlidir | Bütünlük, kaynak ve davranış kabulü ayrı kontrollerdir. |

Saldırı–savunma bağlantısı: ai-saldiri-41.
:::

::: anlat Kaynak ile lab sonucunu ayır
[Python hashlib](https://docs.python.org/3/library/hashlib.html). Özet bütünlük karşılaştırmasını destekler; kaynağın güvenilirliği ve zafiyet kabulü ayrı kararlardır.
:::
