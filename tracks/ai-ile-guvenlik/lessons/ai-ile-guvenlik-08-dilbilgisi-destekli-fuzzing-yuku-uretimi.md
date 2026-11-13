---
id: ai-ile-guvenlik-08
title: "Dilbilgisi Destekli (Grammar-Guided) Fuzzing Yükü Üretimi"
summary: Rastgele bayt mutasyonu yerine hedef şemadan (grammar) geçen sınır değer yükleri üret, yıkıcı komutları ele ve iş mantığı katmanındaki taşma anomalilerini sınıflandır.
timeout: 300
esleme: ai-saldiri-40, ai-savunma-05, ai-savunma-13
---

::: anlat Gerçek biçimi bil, sentetik temsili ayırt et: Dilbilgisi destekli fuzzing ve sınır değer analizi
Bir API uç noktasına veya girdi işleyicisine tamamen rastgele baytlar (`{bozuk json%x99\xff`) göndermek geleneksel karadelik fuzzing (`dumb fuzzing`) yöntemidir. Ancak modern yazılımlarda bu rastgele baytlar, uygulamanın en dış kabuğundaki sözdizimi ayrıştırıcısında (`JSON parser`, `deserializer`) anında `400 Bad Request` veya `JSONDecodeError` ile reddedilir. Sonuç olarak, arkada çalışan asıl kritik iş mantığı (`business logic`), yetkilendirme katmanı ve bellek yönetimi kod dallarına hiçbir zaman ulaşılamaz.

Buna karşılık **dilbilgisi destekli fuzzing (`grammar-guided fuzzing`)**, hedefin beklediği veri yapısının biçimsel tanımını (JSON Schema, ANTLR dilbilgisi, Protobuf spesifikasyonu) kılavuz olarak kullanır. Üretilen yükler sözdizimi açısından tamamen geçerlidir; ancak veri alanlarının içindeki değerler sınır (`boundary/corner case`) şartlarını (`-1`, `0`, `50000`, aşırı uzun dizgeler) hedef alacak şekilde mutasyona uğratılır. Böylece ön filtreleri tereyağından kıl çeker gibi geçen yükler, iç servis katmanında beklenmeyen `IndexError` (negatif indeks erişimi) veya `MemoryError` (aşırı bellek tahsisi) anomalilerini tetikler (`ai-saldiri-40` dersindeki kaynak tüketimi sınırlarını ve `ai-savunma-05` dersindeki şema doğrulamasını hatırla).

| Gerçek araç / model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| JSON dilbilgisi doğrulayıcısını, sınır değer mutasyon üretecini ve yerel Ollama modelinin (`qwen3`) önerdiği test yüklerini | İlk üç görevde `aday_yukler.json` ve `dilbilgisi_kurallari.json` içindeki **sentetik** yük verilerini; son görevde canlı `ai_lab.SohbetOturumu` ile dilbilgisi destekli fuzzing deneyini | Kapsam kılavuzlu dinamik enstrümantasyon (`coverage-guided instrumentation` / AFL++, libFuzzer) olmadan yalnız sabit sınır değer listesiyle tüm gizli dalların keşfedilebileceğini söyleyemez |

> [!NOT]
> İlk üç görevde kullanılan `aday_yukler.json` ve `hedef_isleyici_simule` işlevi **sentetik** eğitim verisidir; canlı bir mikroservis ya da API ağ geçidi değildir. Kurulum (`setup`) bloğundaki `hazirla("ai-ile-guvenlik-08")` çağrısıyla çalışma ortamına geçici olarak yüklenir; oturumlar arasında **kalıcılık yoktur**. Son adımdaki **Gerçek deney** adımı kurulu yerel modeli (`qwen3`) sorgulayarak hedef şema için sınır değer analizi yaptırır ve dilbilgisi süzgecini çalıştırır. Harici bir fuzzer süreci (AFL, Radamsa, Boofuzz) kurulmaz veya koşturulmaz.
:::

::: anlat Bir fuzzing hattında ne olur, saldırgan neyi dener ve savunma neden kırılır?
Dilbilgisi destekli fuzzing mekanizması sözdizimsel geçerlilik ile anlamsal güvenlik arasındaki boşluğu test eder:

- **Aracın Altında Ne Olur?**
  1. *Dilbilgisi ve Güvenlik Filtresi (`dilbilgisi_yuku_dogrula`):* Gelen ham metin önce `json.loads` ile ayrıştırılır. Ardından şemanın tamlığı (`{"komut", "limit"}` anahtar kümesi), komutun izinli eylemler (`"listele"`, `"detay"`, `"durum"`) içinde bulunması ve `limit` alanının `bool` olmayan saf bir tamsayı (`int`) olması denetlenir. Yıkıcı ya da geçersiz yükler işleyiciye iletilmeden elenir.
  2. *Sınır Değer Mutasyonu Üretimi (`sinir_mutasyonlari_uret`):* İzinli komutlar için kritik sayısal eşikler (`-1, 0, 1, 1000, 10001`) belirlenir ve `json.dumps(..., sort_keys=True)` ile deterministik test yükleri oluşturulur.
  3. *Fuzz Kampanyası ve Anomali Sınıflandırma (`fuzz_kampanyasi_kostur`):* Doğrulamadan geçen yükler hedef iç servise (`hedef_isleyici_simule`) gönderilir. Normal yanıt verenler `normal_yukler` listesine, istisna fırlatanlar ise hata türlerine (`IndexError`, `MemoryError`) göre `anomali_yukleri` haritasına kaydedilir.
- **Saldırganın Taktikleri:**
  1. *Ayrıştırıcı Atlama ve Yıkıcı Enjeksiyon:* Saldırgan, şema doğrulamasını aşabilmek için biçimsel olarak doğru görünen fakat izin verilmeyen yönetimsel/yıkıcı komutlar (`"sil"`, `"format"`, `"admin_reset"`) enjekte etmeye çalışır.
  2. *Sınır Değer Taşmaları (Boundary Overflow):* Tamsayı sınırlarını aşan değerler (`-1` ile dizi indeksleme açıkları, `50000` ile bellek tahsisi krizleri) göndererek hedef sistemde hizmet dışı bırakma (`DoS`) veya bellek sızıntısı tetiklemeyi hedefler.
  3. *Tip Karışıklığı (Type Confusion):* JSON biçiminde `true` veya `"10"` gibi değerler göndererek zayıf tipli kontrolleri atlatmayı dener.
- **Savunmanın Kırılma Noktaları:**
  - Yalnızca JSON ayrıştırmasını (`json.loads`) yeterli görüp anahtar kümesini ve tipleri doğrulamamak: Ekstra alanlar (`"admin": true`) kütle atama (`mass assignment`) açıklarına zemin hazırlar.
  - İzinli liste (`allowlist`) yerine kara liste (`blocklist`) kullanmak: Saldırgan bilinmeyen bir komut adıyla korumayı atlayabilir.
  - Sayısal aralık sınırlaması (`clamp` / min-max denetimi) koymamak: Pozitif/negatif ekstremumlar iş mantığında beklenmeyen dalları tetikler.
- **Sık Yapılan Geliştirici Tuzakları:**
  1. Python'da `bool` sınıfının `int` alt sınıfı olması (`issubclass(bool, int) is True`): `isinstance(True, int)` ifadesi `True` döndürdüğünden, `not isinstance(limit, bool)` kontrolü eklenmezse bayraklar tamsayı gibi işlenir.
  2. Girdi dizgelerindeki boşlukların kontrol edilmemesi: Yalnızca `isinstance(x, str)` yetmez; boş veya salt boşluk (`"   "`) içeren dizgeler için `x.strip()` denetimi yapılmalıdır.
  3. JSON serileştirmesinde anahtar sırasının korunmaması: `json.dumps` çağrısında `sort_keys=True` kullanılmadığında karmaşık karşılaştırmalarda test kırılmaları yaşanır.
  4. Hata sınıflandırmasında genel `Exception` mesajlarına güvenmek: Güvenlik denetim izinde hata sınıfı doğrudan `type(e).__name__` üzerinden deterministik olarak kaydedilmelidir.
:::

::: anlat Dilbilgisi kapısı ayrıştırıcıda takılan gürültüyü eler
Dilbilgisi destekli fuzzing hattı üç aşamada çalışır:

1. **Dilbilgisi ve Güvenli Komut Doğrulaması (`dilbilgisi_yuku_dogrula`):**
   - Metin `json.loads` ile ayrıştırılamazsa `"json_hatasi"` döner.
   - Ayrıştırılan nesne tam olarak `{"komut", "limit"}` anahtarlarına sahip bir `dict` değilse `"sema_hatasi"` döner.
   - `komut` değeri `("listele", "detay", "durum")` kümesinde değilse `"yasak_komut"` döner (yıkıcı eylemleri engeller).
   - `limit` değeri `bool` olmayan bir `int` değilse `"tip_hatasi"` döner.
2. **Sınır Değer Mutasyonu Üretimi (`sinir_mutasyonlari_uret`):** İzinli bir komut için `(-1, 0, 1, 1000, 10001)` sınır değerlerini içeren geçerli JSON dizgeleri üretilir.
3. **Fuzz Kampanyası ve Anomali Sınıflandırma (`fuzz_kampanyasi_kostur`):** Dilbilgisi kapısından geçen yükler hedef işleyiciye verilir; fırlatılan istisna türleri (`IndexError`, `MemoryError`) `anomali_yukleri` sözlüğüne kaydedilir.
:::

::: anlat Bulguyu sınırlı ve doğrulanabilir yaz: ayrıştırıcı reddi ile iç anomaliyi karıştırma
Bozuk bir JSON metninin reddedilmesi hedef serviste bir zafiyet değil, ön ayrıştırıcının beklenen davranışıdır (`elenen_yukler`). Gerçek bulgu, dilbilgisi ve şema kapısından **geçtiği hâlde** (`gecerli == True`) hedef işleyicide beklenmeyen istisna (`anomali_yukleri`) üreten sınır değer yükleridir.
:::

::: tahmin Python'da bool tipinin int alt sınıfı olması ve JSON şema kontrolünü tahmin et
Aşağıdaki Python kodunun çıktısını tahmin et:

```python
import json

yukler = ['{"komut": "listele", "limit": true}', '{"komut": "listele", "limit": -1}']
sonuc = []
for y in yukler:
    v = json.loads(y)
    gecerli_int = isinstance(v["limit"], int) and not isinstance(v["limit"], bool)
    sonuc.append((v["limit"], gecerli_int))
print(sonuc)
```

???

```cikti
[(True, False), (-1, True)]
```

Python'da `bool` sınıfı `int` sınıfından türediği için `isinstance(True, int)` `True` döner; bu yüzden dilbilgisi doğrulamasında `not isinstance(limit, bool)` kontrolü zorunludur.
:::

::: gorev 1 · Aday fuzzing yükünü dilbilgisi ve izinli komut kurallarına göre doğrula
`dilbilgisi_yuku_dogrula(json_metni)` işlevini yaz.

Girdi kuralları:
- `json_metni`: boş olmayan (`strip()` sonrası dolu) `str`. Boş metin veya `str` dışı tipte `ValueError` yükselt.

Doğrulama kuralları (sırasıyla):
1. `json.loads(json_metni)` başarısız olursa `{"gecerli": False, "neden": "json_hatasi", "veri": None}` döndür.
2. Sonuç bir `dict` değilse veya anahtar kümesi tam olarak `{"komut", "limit"}` değilse `{"gecerli": False, "neden": "sema_hatasi", "veri": None}` döndür.
3. `veri["komut"]` değeri `("listele", "detay", "durum")` içinde değilse `{"gecerli": False, "neden": "yasak_komut", "veri": None}` döndür.
4. `veri["limit"]` bir `bool` ise veya `int` değilse `{"gecerli": False, "neden": "tip_hatasi", "veri": None}` döndür.
5. Tüm kontroller geçerse `{"gecerli": True, "neden": "tamam", "veri": veri}` döndür.

```starter
import json
from ai_ile_guvenlik_veri import json_yukle

adaylar = json_yukle("aday_yukler.json")

def dilbilgisi_yuku_dogrula(json_metni):
    # KUSURLU BAŞLANGIÇ KODU: Yasaklı yıkıcı komutları filtrelemeden ve limit tipinin tamsayı olduğunu denetlemeden JSON'ı doğrudan geçerli sayıyor!
    try:
        veri = json.loads(json_metni)
    except Exception:
        return {"gecerli": False, "neden": "json_hatasi", "veri": None}
    return {"gecerli": True, "neden": "tamam", "veri": veri}

print(dilbilgisi_yuku_dogrula(adaylar[0]["json_metni"]))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-08")
```

```test
need("dilbilgisi_yuku_dogrula")

def sozlesme(fn):
    try:
        if fn('{"komut": "listele", "limit": -1}') != {
            "gecerli": True,
            "neden": "tamam",
            "veri": {"komut": "listele", "limit": -1},
        }:
            return False

        if fn("{bozuk") != {"gecerli": False, "neden": "json_hatasi", "veri": None}:
            return False
        if fn("[1, 2]") != {"gecerli": False, "neden": "sema_hatasi", "veri": None}:
            return False
        if fn('{"komut": "listele"}') != {"gecerli": False, "neden": "sema_hatasi", "veri": None}:
            return False
        if fn('{"komut": "sil", "limit": 10}') != {"gecerli": False, "neden": "yasak_komut", "veri": None}:
            return False
        if fn('{"komut": "detay", "limit": true}') != {"gecerli": False, "neden": "tip_hatasi", "veri": None}:
            return False
        if fn('{"komut": "durum", "limit": "10"}') != {"gecerli": False, "neden": "tip_hatasi", "veri": None}:
            return False

        for h in (None, 123, "", "   \n "):
            try:
                fn(h)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(dilbilgisi_yuku_dogrula), "dilbilgisi doğrulayıcısı JSON, şema, izinli komut ve int tipini doğru kontrol etmeli")
def m_hep_gecerli(m):
    return dict(dilbilgisi_yuku_dogrula(m), gecerli=True)
def m_yasak_atlayan(m):
    r = dilbilgisi_yuku_dogrula(m)
    return {"gecerli": True, "neden": "tamam", "veri": {}} if r["neden"] == "yasak_komut" else r
for ad, mutant in [("hep geçerli sayan", m_hep_gecerli), ("yasak komutu geçiren", m_yasak_atlayan)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
import json

IZINLI_KOMUTLAR = ("listele", "detay", "durum")

def dilbilgisi_yuku_dogrula(json_metni):
    if not isinstance(json_metni, str) or not json_metni.strip():
        raise ValueError("json_metni boş olmayan string olmalı")
    try:
        veri = json.loads(json_metni)
    except Exception:
        return {"gecerli": False, "neden": "json_hatasi", "veri": None}

    if not isinstance(veri, dict) or set(veri.keys()) != {"komut", "limit"}:
        return {"gecerli": False, "neden": "sema_hatasi", "veri": None}

    komut = veri["komut"]
    limit = veri["limit"]
    if komut not in IZINLI_KOMUTLAR:
        return {"gecerli": False, "neden": "yasak_komut", "veri": None}
    if isinstance(limit, bool) or not isinstance(limit, int):
        return {"gecerli": False, "neden": "tip_hatasi", "veri": None}

    return {"gecerli": True, "neden": "tamam", "veri": veri}
```

```hint
`json.loads` sonrası sırasıyla `isinstance(veri, dict)`, `set(veri.keys()) == {"komut", "limit"}`, `komut in IZINLI_KOMUTLAR` ve `not isinstance(limit, bool) and isinstance(limit, int)` kontrollerini uygula.
```
:::

::: gorev 2 · İzinli komut için dilbilgisine uygun sınır değer mutasyonları üret
`sinir_mutasyonlari_uret(temel_komut)` işlevini yaz.

Girdi kuralları:
- `temel_komut`: `("listele", "detay", "durum")` kümesinden bir `str`. Geçersiz komut veya tipte `ValueError` yükselt.

Üretim kuralları:
- Sırasıyla `(-1, 0, 1, 1000, 10001)` sınır değerleri için `json.dumps({"komut": temel_komut, "limit": deger}, sort_keys=True)` formatında 5 adet JSON dizgesi içeren `list` döndür.

```starter
import json

def sinir_mutasyonlari_uret(temel_komut):
    # KUSURLU BAŞLANGIÇ KODU: İzinli komut kümesini denetlemeden yalnızca tek bir sabit limit değeri (10) üretiyor; sınır değerlerini üretmiyor!
    return [json.dumps({"komut": temel_komut, "limit": 10}, sort_keys=True)]

print(sinir_mutasyonlari_uret("listele"))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-08")
```

```test
need("sinir_mutasyonlari_uret")

def sozlesme(fn):
    try:
        beklenen = [
            '{"komut": "detay", "limit": -1}',
            '{"komut": "detay", "limit": 0}',
            '{"komut": "detay", "limit": 1}',
            '{"komut": "detay", "limit": 1000}',
            '{"komut": "detay", "limit": 10001}',
        ]
        if fn("detay") != beklenen:
            return False

        for h in (None, 123, "", "sil", "admin"):
            try:
                fn(h)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(sinir_mutasyonlari_uret), "sınır mutasyonları izinli komutlar için 5 sınır değer JSON yükü üretmeli")
def m_eksik(k):
    return sinir_mutasyonlari_uret(k)[:3]
def m_sirasiz(k):
    return list(reversed(sinir_mutasyonlari_uret(k)))
for ad, mutant in [("eksik sınır üreten", m_eksik), ("sırayı bozan", m_sirasiz)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
import json

IZINLI_KOMUTLAR = ("listele", "detay", "durum")

def sinir_mutasyonlari_uret(temel_komut):
    if not isinstance(temel_komut, str) or temel_komut not in IZINLI_KOMUTLAR:
        raise ValueError("temel_komut izinli komutlardan biri olmalı")
    sinir_degerler = (-1, 0, 1, 1000, 10001)
    return [
        json.dumps({"komut": temel_komut, "limit": deger}, sort_keys=True)
        for deger in sinir_degerler
    ]
```

```hint
`temel_komut not in IZINLI_KOMUTLAR` durumunda `ValueError` yükselt ve `(-1, 0, 1, 1000, 10001)` demetindeki her sayı için `json.dumps(..., sort_keys=True)` üret.
```
:::

::: gorev 3 · Fuzz kampanyasını koştur ve hedef işleyici anomalilerini sınıflandır
`fuzz_kampanyasi_kostur(aday_yukler)` işlevini yaz.

Girdi kuralları:
- `aday_yukler`: boş olmayan `list`; her öğe tam olarak `{"yuk_id", "json_metni"}` anahtarlarına sahip `dict` olmalı, `yuk_id` boş olmayan benzersiz `str` ve `json_metni` boş olmayan `str` olmalıdır.
- Geçersiz girdi veya şemada `ValueError` yükselt.

Kampanya kuralları:
1. Her adayı 1. görevdeki `dilbilgisi_yuku_dogrula` kurallarıyla kontrol et:
   - `gecerli == False` ise hedef işleyiciye **göndermeden** `elenen_yukler` listesine `yuk_id` ekle.
2. `gecerli == True` ise `ai_gercek_ai_ile_guvenlik_08.hedef_isleyici_simule(veri)` işlevini çağır:
   - İstisna fırlatılmazsa `normal_yukler` listesine `yuk_id` ekle.
   - İstisna fırlatılırsa `anomali_yukleri[yuk_id] = type(e).__name__` olarak kaydet.
3. `{"normal_yukler": sorted(...), "elenen_yukler": sorted(...), "anomali_yukleri": ..., "anomali_sayisi": len(anomali_yukleri)}` sözlüğünü döndür.

```starter
from ai_ile_guvenlik_veri import json_yukle
from ai_gercek_ai_ile_guvenlik_08 import hedef_isleyici_simule

adaylar = json_yukle("aday_yukler.json")

def fuzz_kampanyasi_kostur(aday_yukler):
    # KUSURLU BAŞLANGIÇ KODU: Dilbilgisi doğrulamasını uygulamadan tüm yükleri normal kabul ediyor ve hedef işleyici anomalilerini yakalamıyor!
    return {
        "normal_yukler": [a.get("yuk_id") for a in (aday_yukler or []) if isinstance(a, dict)],
        "elenen_yukler": [],
        "anomali_yukleri": {},
        "anomali_sayisi": 0,
    }

print(fuzz_kampanyasi_kostur(adaylar))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-08")
```

```test
need("fuzz_kampanyasi_kostur")

ADAYLAR = [
    {"yuk_id": "f1", "json_metni": '{"komut": "listele", "limit": 10}'},
    {"yuk_id": "f2", "json_metni": '{"komut": "listele", "limit": -1}'},
    {"yuk_id": "f3", "json_metni": '{"komut": "listele", "limit": 50000}'},
    {"yuk_id": "f4", "json_metni": "{bozuk json"},
    {"yuk_id": "f5", "json_metni": '{"komut": "sil", "limit": 10}'},
    {"yuk_id": "f6", "json_metni": '{"komut": "detay"}'},
    {"yuk_id": "f7", "json_metni": '{"komut": "durum", "limit": true}'},
    {"yuk_id": "f8", "json_metni": '{"komut": "durum", "limit": "10"}'},
    {"yuk_id": "f9", "json_metni": '[1, 2]'},
]

def sozlesme(fn):
    try:
        r = fn(ADAYLAR)
        if r != {
            "normal_yukler": ["f1"],
            "elenen_yukler": ["f4", "f5", "f6", "f7", "f8", "f9"],
            "anomali_yukleri": {"f2": "IndexError", "f3": "MemoryError"},
            "anomali_sayisi": 2,
        }:
            return False

        hatalilar = [
            None,
            123,
            [],
            [123],
            "liste",
            ["bozuk"],
            [{"yuk_id": "f1"}],
            [{"yuk_id": "", "json_metni": "{}"}],
            [{"yuk_id": "   ", "json_metni": "{}"}],
            [{"yuk_id": 123, "json_metni": "{}"}],
            [{"yuk_id": "f1", "json_metni": ""}],
            [{"yuk_id": "f1", "json_metni": "   "}],
            [{"yuk_id": "f1", "json_metni": None}],
            [ADAYLAR[0], ADAYLAR[0]],
        ]
        for h in hatalilar:
            try:
                fn(h)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(fuzz_kampanyasi_kostur), "fuzz kampanyası geçersiz yükleri elemeli ve sınır değer anomalilerini sınıflandırmalı")
def m_anomali_gizleyen(a):
    return dict(fuzz_kampanyasi_kostur(a), anomali_yukleri={}, anomali_sayisi=0)
def m_elenen_gizleyen(a):
    return dict(fuzz_kampanyasi_kostur(a), elenen_yukler=[])
for ad, mutant in [("anomalileri gizleyen", m_anomali_gizleyen), ("elenen yükleri gizleyen", m_elenen_gizleyen)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
import json
from ai_gercek_ai_ile_guvenlik_08 import hedef_isleyici_simule

IZINLI_KOMUTLAR = ("listele", "detay", "durum")

def _dogrula(json_metni):
    if not isinstance(json_metni, str) or not json_metni.strip():
        raise ValueError("json_metni boş olmayan string olmalı")
    try:
        veri = json.loads(json_metni)
    except Exception:
        return False, None
    if not isinstance(veri, dict) or set(veri.keys()) != {"komut", "limit"}:
        return False, None
    if veri["komut"] not in IZINLI_KOMUTLAR:
        return False, None
    if isinstance(veri["limit"], bool) or not isinstance(veri["limit"], int):
        return False, None
    return True, veri

def fuzz_kampanyasi_kostur(aday_yukler):
    if not isinstance(aday_yukler, list) or not aday_yukler:
        raise ValueError("aday_yukler boş olamaz")

    gorulen = set()
    elenen_yukler = []
    normal_yukler = []
    anomali_yukleri = {}

    for a in aday_yukler:
        if not isinstance(a, dict) or set(a.keys()) != {"yuk_id", "json_metni"}:
            raise ValueError("aday yük şeması geçersiz")
        yid = a["yuk_id"]
        metin = a["json_metni"]
        if not isinstance(yid, str) or not yid.strip() or yid in gorulen:
            raise ValueError("yuk_id geçersiz veya tekrarlı")
        gorulen.add(yid)

        gecerli, veri = _dogrula(metin)
        if not gecerli:
            elenen_yukler.append(yid)
            continue

        try:
            hedef_isleyici_simule(veri)
            normal_yukler.append(yid)
        except Exception as e:
            anomali_yukleri[yid] = type(e).__name__

    return {
        "normal_yukler": sorted(normal_yukler),
        "elenen_yukler": sorted(elenen_yukler),
        "anomali_yukleri": anomali_yukleri,
        "anomali_sayisi": len(anomali_yukleri),
    }
```

```hint
Dilbilgisi doğrulamasından geçmeyen yükleri `elenen_yukler` listesine ekle; geçenleri `try/except` bloğunda `hedef_isleyici_simule(veri)` ile çalıştırarak istisna adını `type(e).__name__` ile kaydet.
```
:::

::: gorev Gerçek deney · Yerel modelle dilbilgisi destekli sınır değer fuzzing kampanyası
Önceki üç görevde yazdığın `dilbilgisi_yuku_dogrula`, `sinir_mutasyonlari_uret` ve `fuzz_kampanyasi_kostur` işlevlerini bu adımda birleştir.

Canlı deneyde:
1. Yerel Ollama modeli (`ai_lab.SohbetOturumu`) üzerinde hedef şema için sınır değer analizi yapılır.
2. `sinir_mutasyonlari_uret` ile dilbilgisine uygun sınır değer yükleri üretilir.
3. `fuzz_kampanyasi_kostur` ile yıkıcı/bozuk yükler elenir ve hedef işleyicideki `IndexError` ile `MemoryError` anomalileri yakalanır.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab

def dilbilgisi_yuku_dogrula(json_metni):
    # KUSURLU BAŞLANGIÇ KODU: Şema ve izinli komut kontrolü yapmadan her yükü geçerli sayıyor!
    return {"gecerli": True, "neden": "tamam", "veri": {}}

def sinir_mutasyonlari_uret(temel_komut):
    # KUSURLU BAŞLANGIÇ KODU: Sınır değer listesi yerine boş liste döndürüyor!
    return []

def fuzz_kampanyasi_kostur(aday_yukler):
    # KUSURLU BAŞLANGIÇ KODU: Fuzz kampanyasını yürütmeden boş sonuç üretiyor!
    return {
        "normal_yukler": [],
        "elenen_yukler": [],
        "anomali_yukleri": {},
        "anomali_sayisi": 0,
    }

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_ile_guvenlik_08 as deney
    deney.goster(dilbilgisi_yuku_dogrula, sinir_mutasyonlari_uret, fuzz_kampanyasi_kostur)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-08")
```

```test
import ast
import ai_lab
from sandbox import ai_gercek_ai_ile_guvenlik_08 as D

checks = []
_base_ok = ok
def ok(kosul, mesaj):
    checks.append(bool(kosul))
    return _base_ok(kosul, mesaj)

for ad in ("dilbilgisi_yuku_dogrula", "sinir_mutasyonlari_uret", "fuzz_kampanyasi_kostur"):
    need(ad)

yasak = (
    "referans",
    "dilbilgisi_yuku_dogrula_referans",
    "sinir_mutasyonlari_uret_referans",
    "fuzz_kampanyasi_kostur_referans",
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

def _on_sozlesme():
    try:
        if dilbilgisi_yuku_dogrula('{"komut": "listele", "limit": 10}') != {"gecerli": True, "neden": "tamam", "veri": {"komut": "listele", "limit": 10}}:
            return False
        for m, beklenen_neden in [
            ("{bozuk", "json_hatasi"),
            ("[1]", "sema_hatasi"),
            ('{"komut": "listele"}', "sema_hatasi"),
            ('{"komut": "sil", "limit": 1}', "yasak_komut"),
            ('{"komut": "listele", "limit": true}', "tip_hatasi"),
            ('{"komut": "listele", "limit": "1"}', "tip_hatasi"),
        ]:
            if dilbilgisi_yuku_dogrula(m) != {"gecerli": False, "neden": beklenen_neden, "veri": None}:
                return False
        if sinir_mutasyonlari_uret("detay") != [
            '{"komut": "detay", "limit": -1}',
            '{"komut": "detay", "limit": 0}',
            '{"komut": "detay", "limit": 1}',
            '{"komut": "detay", "limit": 1000}',
            '{"komut": "detay", "limit": 10001}',
        ]:
            return False
        kamp = fuzz_kampanyasi_kostur([
            {"yuk_id": "f1", "json_metni": '{"komut": "listele", "limit": 10}'},
            {"yuk_id": "f2", "json_metni": '{"komut": "listele", "limit": -1}'},
            {"yuk_id": "f3", "json_metni": '{"komut": "listele", "limit": 50000}'},
            {"yuk_id": "f4", "json_metni": "{bozuk"},
        ])
        if kamp != {"normal_yukler": ["f1"], "elenen_yukler": ["f4"], "anomali_yukleri": {"f2": "IndexError", "f3": "MemoryError"}, "anomali_sayisi": 2}:
            return False
        for h in (None, 123, "", "   "):
            try:
                dilbilgisi_yuku_dogrula(h)
                return False
            except ValueError:
                pass
        for hk in (None, 123, "", "sil"):
            try:
                sinir_mutasyonlari_uret(hk)
                return False
            except ValueError:
                pass
        for a_in in (
            None,
            123,
            [],
            [123],
            [{}],
            [{"yuk_id": "", "json_metni": "{}"}],
            [{"yuk_id": 123, "json_metni": "{}"}],
            [{"yuk_id": "a", "json_metni": ""}],
            [D.ADAY_YUKLER[0], D.ADAY_YUKLER[0]],
        ):
            try:
                fuzz_kampanyasi_kostur(a_in)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(_on_sozlesme(), "sentetik ön kontrol: dilbilgisi ve kampanya kuralları tam")

if not all(checks):
    stop()

try:
    r = D.deney(dilbilgisi_yuku_dogrula, sinir_mutasyonlari_uret, fuzz_kampanyasi_kostur)
except Exception as e:
    ok(False, f"GERÇEK FUZZING DENEYİ YAPILAMADI: {type(e).__name__}: {e}")
    stop()

for ad, deger in r["kontroller"].items():
    ok(deger, "gerçek deney: " + ad)

ai_lab.kanit_yaz("ile-guvenlik-08-fuzz", {
    "kaynak": "gercek",
    "kabul": all(checks),
    "ders": "ai-ile-guvenlik-08",
    "ortam": r["ortam"],
    "ayarlar": r["ayarlar"],
    "deney": r,
    "ozet": r["ozet"],
})
o = r["ozet"]
ok(
    True,
    f"BULGU ({o['model']}): normal={o['normal_yukler']}, elenen={o['elenen_yukler']}, anomaliler={o['anomali_yukleri']}.",
)
```

```solution
import json
import ai_lab
from ai_gercek_ai_ile_guvenlik_08 import hedef_isleyici_simule

IZINLI_KOMUTLAR = ("listele", "detay", "durum")

def dilbilgisi_yuku_dogrula(json_metni):
    if not isinstance(json_metni, str) or not json_metni.strip():
        raise ValueError("json_metni boş olmayan string olmalı")
    try:
        veri = json.loads(json_metni)
    except Exception:
        return {"gecerli": False, "neden": "json_hatasi", "veri": None}

    if not isinstance(veri, dict) or set(veri.keys()) != {"komut", "limit"}:
        return {"gecerli": False, "neden": "sema_hatasi", "veri": None}

    komut = veri["komut"]
    limit = veri["limit"]
    if komut not in IZINLI_KOMUTLAR:
        return {"gecerli": False, "neden": "yasak_komut", "veri": None}
    if isinstance(limit, bool) or not isinstance(limit, int):
        return {"gecerli": False, "neden": "tip_hatasi", "veri": None}

    return {"gecerli": True, "neden": "tamam", "veri": veri}

def sinir_mutasyonlari_uret(temel_komut):
    if not isinstance(temel_komut, str) or temel_komut not in IZINLI_KOMUTLAR:
        raise ValueError("temel_komut izinli komutlardan biri olmalı")
    sinir_degerler = (-1, 0, 1, 1000, 10001)
    return [
        json.dumps({"komut": temel_komut, "limit": deger}, sort_keys=True)
        for deger in sinir_degerler
    ]

def fuzz_kampanyasi_kostur(aday_yukler):
    if not isinstance(aday_yukler, list) or not aday_yukler:
        raise ValueError("aday_yukler boş olamaz")

    gorulen = set()
    elenen_yukler = []
    normal_yukler = []
    anomali_yukleri = {}

    for a in aday_yukler:
        if not isinstance(a, dict) or set(a.keys()) != {"yuk_id", "json_metni"}:
            raise ValueError("aday yük şeması geçersiz")
        yid = a["yuk_id"]
        metin = a["json_metni"]
        if not isinstance(yid, str) or not yid.strip() or yid in gorulen:
            raise ValueError("yuk_id geçersiz veya tekrarlı")
        gorulen.add(yid)

        dogrulama = dilbilgisi_yuku_dogrula(metin)
        if not dogrulama["gecerli"]:
            elenen_yukler.append(yid)
            continue

        try:
            hedef_isleyici_simule(dogrulama["veri"])
            normal_yukler.append(yid)
        except Exception as e:
            anomali_yukleri[yid] = type(e).__name__

    return {
        "normal_yukler": sorted(normal_yukler),
        "elenen_yukler": sorted(elenen_yukler),
        "anomali_yukleri": anomali_yukleri,
        "anomali_sayisi": len(anomali_yukleri),
    }

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_ile_guvenlik_08 as deney
    deney.goster(dilbilgisi_yuku_dogrula, sinir_mutasyonlari_uret, fuzz_kampanyasi_kostur)
```

```hint
Önceki üç görevdeki `dilbilgisi_yuku_dogrula`, `sinir_mutasyonlari_uret` ve `fuzz_kampanyasi_kostur` işlevlerini birleştir.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
### Fuzz yükü hedef dilbilgisinde kalır

Rastgele bytes üretmek yerine izinli komutun biçim ve sınır değerleri değiştirilir. Kampanya her yükü gerçek yerel işleyiciye götürür ve beklenen ret, hata veya anomaliyi ayırır. Hedefin kibarca reddettiği girdi crash değildir. Küçük dilbilgisindeki kapsama genel parser güvenliği veya bütün fuzz uzayının tüketilmesi anlamına gelmez.

| Yaygın yanlış | Kontrolün gösterdiği |
|---|---|
| Her hata cevabı zafiyettir | Beklenen doğrulama reddi ile anomali sınıfları ayrılır. |

Sonraki bağlantı: ai-savunma-13. [Birincil kaynak](https://docs.python.org/3/library/subprocess.html). Kaynak ilgili araç veya yöntemi açıklar; labın gerçek sonucu ham kanıt kaydındadır.
:::
