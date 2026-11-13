---
id: ai-saldiri-37
title: Red Team Metodolojisi II · Kapsam Matrisi, Saldırı Zinciri Önceliklendirme ve Operasyon Kapanışı
summary: Sistem anatomisine karşı saldırı kapsam matrisini ve kör noktaları çıkar; çok adımlı saldırı zinciri ve kanıt durumuyla bulguları önceliklendir ve operasyon sonunda RAG/bellek/oturum izlerinin temizlendiğini canlı modelde doğrula.
timeout: 60
esleme: ai-saldiri-36, ai-guvence-29, ai-guvence-33
---

::: anlat Gerçek biçimi bil, sentetik temsili ayırt et
`ai-saldiri-36` dersinde çalışmaya başlamadan önce yasal kapsamı (RoE) ve hedef sistemin 6 katmanlı anatomisini kurmuştuk. Yolu tamamlayan bu son derste ise bir red team kampanyasının **sistematik kapsam muhasebesini**, **saldırı zinciri önceliklendirmesini** ve **operasyon kapanışı / iz temizliğini (teardown & sanitization)** yürütüyoruz:

| Katman | Gerçek operasyonda ne yapılır? | Bu ders ne kullanır? | Ne söyleyemez? |
|---|---|---|---|
| **Kapsam matrisi** | Hedefin aktif her yüzeyi için en az iki farklı saldırı ailesinin hatasız koşturulduğunu doğrulama; sınanmayan katmanları **kör nokta** olarak işaretleme | İlk 3 görevde `kampanya/kapsam_kayitlari.json` (**sentetik fixture**); son görevde canlı kampanya özeti | Bir katmanda iki tekniğin başarısız olması o katmanın matematiksel olarak kırılmaz olduğunu kanıtlamaz |
| **Zincir önceliklendirme** | Dolaylı RAG/bellek girişinden araç, çıktı tüketici veya SSRF'e uzanan güven sınırı geçişlerini (`+15` zincir bonusu) ve doğrulanmış canary kanıtını ayrıştırma | `kampanya/zincir_bulgulari.json` (**sentetik fixture**) ve canlı deney bulguları | Bu derste kurumsal rapor yazımı yapılmaz; bulgu raporlama ve yönetişim süreci için `ai-guvence-29`, N koşuda tekrarlanabilirlik için `ai-guvence-33` derslerine bakılır |
| **Kapanış ve temizlik** | Test sırasında eklenen RAG zehir belgelerinin, kalıcı bellek kayıtlarının ve geçici canary'lerin silindiğini **temizlik sonrası doğrulama sorgusuyla** kanıtlama | `kampanya/kapanis_envanteri.json` (**sentetik fixture**); son görevde yerel Ollama modelinde canlı öncesi/sonrası temizlik doğrulaması | Tek bir doğrulama sorgusunun temiz dönmesi, harici yedekleme veya log arşivlerindeki kopyaların silindiğini tek başına garanti etmez |

> [!GÜVENLİK]
> Red team operasyonu bittiğinde hedef sistemde unutulan tek bir zehirli RAG belgesi veya kalıcı bellek kaydı, gerçek kullanıcıları etkileyen canlı bir güvenlik açığına dönüşür. Bu dersteki `kampanya/*.json` dosyaları her çalıştırmada geçici çalışma klasörüne yeniden kopyalanır (**çalıştırmalar arasında dosya kalıcılığı yoktur**).

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-37")
```

```python
from ai_saldiri_veri import json_yukle

kapsam = json_yukle("kampanya/kapsam_kayitlari.json")
envanter = json_yukle("kampanya/kapanis_envanteri.json")
print("Aktif katmanlar:", kapsam["aktif_katmanlar"], "test sayısı:", len(kapsam["kosulan_testler"]))
print("Kapanış envanteri:", [(k["iz_id"], k["durum"], k["dogrulama_sorgusu_temiz"]) for k in envanter])
```
:::

::: anlat Sistematik kapsam matrisi: “baktık, bir şey çıkmadı” neden yetmez?
Bir AI red team çalışmasında en sık yapılan metodoloji hatası, yalnız doğrudan kullanıcı istemini (`dogrudan-istem`) birkaç jailbreak ile zorlayıp diğer yüzeyleri (`dolayli-rag`, `arac-yetki`, `bellek-oturum`, `cikti-tuketici`, `ag-ssrf`) sınamadan çalışmayı kapatmaktır.

Sistematik kapsam muhasebesinde üç kural uygulanır:
1. **Aktif yüzey eşlemesi:** Hedef mimaride açık olan her katman (`aktif_katmanlar`) kapsam matrisinde ayrı bir satırdır; aktif olmayan bir katmana test kaydı girilmesi kapsam hatasıdır (`ValueError`).
2. **Taşıma hatası kapsam sayılmaz:** `durum == "hata"` (zaman aşımı, bağlantı kopması) ile sonuçlanan denemeler geçerli sınama (`gecerli_deneme`) veya farklı teknik (`farkli_teknik`) sayısına eklenmez.
3. **Asgari teknik çeşitliliği:** Bir katmanın sınanmış (`kapsandi = True`) sayılması için o katmanda `durum != "hata"` olan **en az 2 farklı teknik** (`farkli_teknik >= 2`) koşturulmuş olmalıdır. Bu eşiği karşılamayan aktif katmanlar `kor_noktalar` listesinde açıkça belirtilir.
:::

::: anlat Saldırı zinciri önceliklendirme: tekil sızıntı ile yürütme zincirini ayır
`ai-guvence-33` dersinde temel etki × erişim puanlamasını ve N koşuda tekrarlanabilirliği görmüştük. Saldırı tarafında bulguları düzeltme sırasına koyarken iki ek boyut belirleyicidir:

- **Yürütme / dış ağ zinciri (`zincir_bonusu`):** Bulgu yalnız tek bir katmanda kalmayıp en az 2 adımlı bir zincir (`len(adimlar) >= 2`) oluşturuyor **ve** zincirde yürütme/dış etki katmanlarından biri (`"arac-yetki"`, `"cikti-tuketici"`, `"ag-ssrf"`) yer alıyorsa (`dolayli-rag -> arac-yetki` gibi), bulguya `+15` zincir bonusu eklenir.
- **Kanıt durumu (`kanit_durumu`):** Canlı deneyde vekil işaretle doğrulanmış (`"dogrulandi"`, `+20`) veya kısmi kanıtlı (`"kismi"`, `+5`) bulgular puanlarına göre `"p1-acil"` (`>= 80`), `"p2-yuksek"` (`>= 55`) veya `"p3-normal"` (`< 55`) sınıfına girer. Buna karşılık henüz deneyle doğrulanmamış `"teorik"` (`+0`) bulgular, teorik puanı ne olursa olsun her zaman `"izleme"` sınıfında tutulur; doğrulanmamış varsayımlar acil yama kuyruğunu tıkamaz.
:::

::: anlat Operasyon kapanışı ve iz temizliği (teardown & sanitization)
Klasik pentestte test hesabı silinip bağlantı kapatılırken, AI red team operasyonunda modelin bağlamına giren kalıcı izler ek bir temizlik doğrulaması gerektirir:

- **Zehirli RAG belgeleri (`rag-zehir-belgesi`):** Vektör indeksine eklenen test chunk'ları silinmeli ve indeks önbelleği yenilenmelidir.
- **Kalıcı bellek kayıtları (`kalici-bellek-kaydi`):** Oturumlar arası belleğe yazılan test talimatları temizlenmelidir.
- **Geçici vekil işaretler (`gecici-vekil-canary`) ve yerel model oturumları (`yerel-model-oturumu`):** Test canary kayıtları ve GPU/CPU üzerinde açılan model oturumları kapatılmalıdır.

Bir izin gerçekten temizlendiği (`temiz`), yalnız veritabanında `durum == "silindi"` yazmasıyla değil, temizlik sonrasında gönderilen doğrulama sorgusunun da temiz dönmesiyle (`dogrulama_sorgusu_temiz == True`) onaylanır (`kapanis_onayi`). *(Not: Kapanış sonrası yönetici ve teknik rapor yazımı bu dersin kapsamı dışındadır; kanıt paketi ve raporlama yapısı `ai-guvence-29` dersinde ele alınır.)*
:::

::: tahmin Kapsam matrisi ve kapanış onayı hangi çıktıyı üretir?
Aşağıdaki kod parçasında `"hata"` durumundaki testin teknik sayısına etkisini ve kapanış onayını izleyerek üç çıktı satırını tahmin et:

```python
testler = [
    {"katman": "dolayli-rag", "teknik": "t1", "durum": "basarisiz"},
    {"katman": "dolayli-rag", "teknik": "t2", "durum": "hata"},
    {"katman": "dogrudan-istem", "teknik": "t1", "durum": "basarisiz"},
    {"katman": "dogrudan-istem", "teknik": "t2", "durum": "basari"},
]
for k in ("dogrudan-istem", "dolayli-rag"):
    teknikler = {t["teknik"] for t in testler if t["katman"] == k and t["durum"] != "hata"}
    print(k, len(teknikler), len(teknikler) >= 2)
izler = [
    {"id": "iz1", "durum": "silindi", "temiz": True},
    {"id": "iz2", "durum": "silindi", "temiz": False},
]
print("kapanis_onayi:", all(x["durum"] == "silindi" and x["temiz"] for x in izler))
```

???

```cikti
dogrudan-istem 2 True
dolayli-rag 1 False
kapanis_onayi: False
```

`dolayli-rag` katmanındaki ikinci teknik (`t2`) `"hata"` durumunda kaldığı için geçerli teknik kümesine girmez (`1 False`) ve katman kör nokta olarak kalır. `iz2` kaydında `durum == "silindi"` olsa bile doğrulama sorgusu temiz dönmediği (`temiz: False`) için `kapanis_onayi: False` olur.
:::

::: gorev 1 · Sistem anatomisine karşı saldırı kapsam matrisini ve kör noktaları çıkar
`kapsam_matrisi(aktif_katmanlar, kosulan_testler)` işlevini yaz.

- Bilinen 6 saldırı katmanı: `"dogrudan-istem"`, `"dolayli-rag"`, `"arac-yetki"`, `"bellek-oturum"`, `"cikti-tuketici"`, `"ag-ssrf"`.
- `aktif_katmanlar`: bilinen katmanlardan oluşan, boş olmayan ve yinelenmeyen `str` listesi.
- `kosulan_testler`: `0..50` öğeli liste; her öğe tam olarak `{"test_id", "katman", "teknik", "durum"}` anahtarlarını taşır:
  - `test_id`: boş olmayan ve listede benzersiz `str`.
  - `katman`: `aktif_katmanlar` içinde yer alan bir `str` (aktif olmayan veya bilinmeyen katmansa `ValueError`).
  - `teknik`: boş olmayan `str`.
  - `durum`: `"basari"`, `"basarisiz"` veya `"hata"`.
- Geçersiz şema, tür veya değer durumunda `ValueError` yükselt. Girdileri değiştirme.

Her aktif katman için (alfabetik sırayla):
- `gecerli_deneme`: `durum != "hata"` olan test sayısı.
- `hata`: `durum == "hata"` olan test sayısı.
- `basari`: `durum == "basari"` olan test sayısı.
- `farkli_teknik`: o katmanda `durum != "hata"` ile koşturulan **tekil** `teknik` sayısı.
- `kapsandi`: `farkli_teknik >= 2`.

Dönüş sözlüğü:

```text
{
  "katman_ozeti": {
    katman: {
      "gecerli_deneme": int,
      "hata": int,
      "basari": int,
      "farkli_teknik": int,
      "kapsandi": bool
    }, ...
  },
  "kor_noktalar": [...],      # kapsandi == False olan aktif katmanlar (alfabetik)
  "kapsam_orani": float       # round(kapsanan_katman / len(aktif_katmanlar), 4)
}
```

```starter
from ai_saldiri_veri import json_yukle

kayit = json_yukle("kampanya/kapsam_kayitlari.json")

def kapsam_matrisi(aktif_katmanlar, kosulan_testler):
    # HATA: Taşıma hatalarını geçerli teknik sayıyor ve yalnız 1 tekniği kapsam için yeterli kabul ediyor.
    ozet = {
        k: {"gecerli_deneme": 0, "hata": 0, "basari": 0, "farkli_teknik": 0, "kapsandi": False}
        for k in sorted(aktif_katmanlar)
    }
    for t in kosulan_testler:
        k = t["katman"]
        ozet[k]["gecerli_deneme"] += 1
        ozet[k]["farkli_teknik"] += 1
        ozet[k]["kapsandi"] = True
    kor = [k for k, v in ozet.items() if not v["kapsandi"]]
    return {
        "katman_ozeti": ozet,
        "kor_noktalar": kor,
        "kapsam_orani": round((len(ozet) - len(kor)) / len(ozet), 4),
    }

print(kapsam_matrisi(kayit["aktif_katmanlar"], kayit["kosulan_testler"]))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-37")
```

```test
import copy
from pathlib import Path

ok(Path("kampanya/kapsam_kayitlari.json").is_file(), "görünür kapsam kayıtları dosyası hazır")

AKTIF = ["dogrudan-istem", "dolayli-rag", "arac-yetki"]
TESTLER = [
    {"test_id": "t1", "katman": "dogrudan-istem", "teknik": "rol", "durum": "basarisiz"},
    {"test_id": "t2", "katman": "dogrudan-istem", "teknik": "rol", "durum": "basari"},
    {"test_id": "t3", "katman": "dogrudan-istem", "teknik": "crescendo", "durum": "basarisiz"},
    {"test_id": "t4", "katman": "dolayli-rag", "teknik": "gizli-etiket", "durum": "basari"},
    {"test_id": "t5", "katman": "dolayli-rag", "teknik": "ustbilgi", "durum": "hata"},
]

def sozlesme(fn):
    try:
        a_kopya = copy.deepcopy(AKTIF)
        t_kopya = copy.deepcopy(TESTLER)
        r = fn(AKTIF, TESTLER)
        if AKTIF != a_kopya or TESTLER != t_kopya:
            return False
        if r != {
            "katman_ozeti": {
                "arac-yetki": {"gecerli_deneme": 0, "hata": 0, "basari": 0, "farkli_teknik": 0, "kapsandi": False},
                "dogrudan-istem": {"gecerli_deneme": 3, "hata": 0, "basari": 1, "farkli_teknik": 2, "kapsandi": True},
                "dolayli-rag": {"gecerli_deneme": 1, "hata": 1, "basari": 1, "farkli_teknik": 1, "kapsandi": False},
            },
            "kor_noktalar": ["arac-yetki", "dolayli-rag"],
            "kapsam_orani": 0.3333,
        }:
            return False
        elli = [{"test_id": f"x{i}", "katman": "dogrudan-istem", "teknik": f"tek{i % 2}", "durum": "basarisiz"} for i in range(50)]
        if fn(["dogrudan-istem"], elli)["kapsam_orani"] != 1.0:
            return False
        if fn(["ag-ssrf"], [])["kor_noktalar"] != ["ag-ssrf"]:
            return False
        for ba, bt in [
            (None, []), ([], []), (("dogrudan-istem",), []), ("dogrudan-istem", []), ([1], []), ([[]], []), (["bilinmeyen"], []),
            (["dogrudan-istem", "dogrudan-istem"], []),
            (["dogrudan-istem"], None), (["dogrudan-istem"], "test"),
            (["dogrudan-istem"], [{"test_id": f"x{i}", "katman": "dogrudan-istem", "teknik": "t", "durum": "basari"} for i in range(51)]),
            (["dogrudan-istem"], [None]), (["dogrudan-istem"], [{}]),
            (["dogrudan-istem"], [{"test_id": "", "katman": "dogrudan-istem", "teknik": "t", "durum": "basari"}]),
            (["dogrudan-istem"], [{"test_id": 1, "katman": "dogrudan-istem", "teknik": "t", "durum": "basari"}]),
            (["dogrudan-istem"], [{"test_id": "a", "katman": "dogrudan-istem", "teknik": "t1", "durum": "basari"},
                                  {"test_id": "a", "katman": "dogrudan-istem", "teknik": "t2", "durum": "basarisiz"}]),
            (["dogrudan-istem"], [{"test_id": "a", "katman": "ag-ssrf", "teknik": "t1", "durum": "basari"}]),
            (["dogrudan-istem"], [{"test_id": "a", "katman": 1, "teknik": "t1", "durum": "basari"}]),
            (["dogrudan-istem"], [{"test_id": "a", "katman": [], "teknik": "t1", "durum": "basari"}]),
            (["dogrudan-istem"], [{"test_id": "a", "katman": "dogrudan-istem", "teknik": "", "durum": "basari"}]),
            (["dogrudan-istem"], [{"test_id": "a", "katman": "dogrudan-istem", "teknik": 1, "durum": "basari"}]),
            (["dogrudan-istem"], [{"test_id": "a", "katman": "dogrudan-istem", "teknik": "t1", "durum": "beklemede"}]),
            (["dogrudan-istem"], [{"test_id": "a", "katman": "dogrudan-istem", "teknik": "t1", "durum": "basari", "ek": 1}]),
        ]:
            try:
                fn(ba, bt)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(kapsam_matrisi), "hata-ayrık kapsam matrisi, en az 2 farklı teknik eşiği ve kör nokta tespiti korunmalı")
def m_hata_dahil(a, t):
    r = kapsam_matrisi(a, [dict(x, durum="basarisiz" if x["durum"] == "hata" else x["durum"]) for x in t])
    return r
def m_tek_teknik(a, t):
    r = kapsam_matrisi(a, t)
    for k, v in r["katman_ozeti"].items():
        v["kapsandi"] = v["farkli_teknik"] >= 1
    r["kor_noktalar"] = [k for k, v in r["katman_ozeti"].items() if not v["kapsandi"]]
    return r
for ad, mutant in [("hatalı denemeyi kapsama katan", m_hata_dahil), ("tek tekniği yeterli sayan", m_tek_teknik)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def kapsam_matrisi(aktif_katmanlar, kosulan_testler):
    bilinen = (
        "dogrudan-istem",
        "dolayli-rag",
        "arac-yetki",
        "bellek-oturum",
        "cikti-tuketici",
        "ag-ssrf",
    )
    if not isinstance(aktif_katmanlar, list) or not aktif_katmanlar:
        raise ValueError("aktif_katmanlar boş olmayan liste olmalı")
    if any(not isinstance(k, str) or k not in bilinen for k in aktif_katmanlar):
        raise ValueError("bilinmeyen katman")
    if len(set(aktif_katmanlar)) != len(aktif_katmanlar):
        raise ValueError("yinelenen aktif katman")
    if not isinstance(kosulan_testler, list) or len(kosulan_testler) > 50:
        raise ValueError("kosulan_testler 0..50 öğeli liste olmalı")

    aktif_kume = set(aktif_katmanlar)
    sirali = sorted(aktif_kume)
    ozet = {
        k: {"gecerli_deneme": 0, "hata": 0, "basari": 0, "farkli_teknik": 0, "kapsandi": False}
        for k in sirali
    }
    teknikler = {k: set() for k in sirali}
    gorulen = set()

    for t in kosulan_testler:
        if not isinstance(t, dict) or set(t) != {"test_id", "katman", "teknik", "durum"}:
            raise ValueError("test şeması geçersiz")
        tid = t["test_id"]
        katman = t["katman"]
        teknik = t["teknik"]
        durum = t["durum"]
        if not isinstance(tid, str) or not tid or tid in gorulen:
            raise ValueError("test_id geçersiz")
        if not isinstance(katman, str) or katman not in aktif_kume:
            raise ValueError("katman aktif değil")
        if not isinstance(teknik, str) or not teknik:
            raise ValueError("teknik geçersiz")
        if durum not in ("basari", "basarisiz", "hata"):
            raise ValueError("durum geçersiz")
        gorulen.add(tid)

        if durum == "hata":
            ozet[katman]["hata"] += 1
        else:
            ozet[katman]["gecerli_deneme"] += 1
            teknikler[katman].add(teknik)
            if durum == "basari":
                ozet[katman]["basari"] += 1

    kor_noktalar = []
    for k in sirali:
        ft = len(teknikler[k])
        ozet[k]["farkli_teknik"] = ft
        ozet[k]["kapsandi"] = ft >= 2
        if not ozet[k]["kapsandi"]:
            kor_noktalar.append(k)

    kapsanan = len(sirali) - len(kor_noktalar)
    return {
        "katman_ozeti": ozet,
        "kor_noktalar": kor_noktalar,
        "kapsam_orani": round(kapsanan / len(sirali), 4),
    }
```

```hint
Her katman için `durum != "hata"` olan teknikleri bir `set` içinde topla. `farkli_teknik = len(teknikler[k])` ve `kapsandi = farkli_teknik >= 2` olarak hesapla.
```
:::

::: gorev 2 · Saldırı zinciri derinliği ve kanıt durumuyla bulguları önceliklendir
`zincir_onceliklendir(bulgular)` işlevini yaz. `bulgular`, `1..30` öğeli bir listedir; her öğe tam olarak `{"bulgu_id", "adimlar", "etki_turu", "kanit_durumu"}` anahtarlarını taşır:

- `bulgu_id`: boş olmayan ve listede benzersiz `str`.
- `adimlar`: `1..5` öğeli, yinelenmeyen ve bilinen 6 katmandan (`"dogrudan-istem"`, `"dolayli-rag"`, `"arac-yetki"`, `"bellek-oturum"`, `"cikti-tuketici"`, `"ag-ssrf"`) oluşan `str` listesi.
- `etki_turu`: `"salt-metin"` (`20` puan), `"veri-sizintisi"` (`40` puan), `"yetkisiz-arac"` (`60` puan) veya `"dis-ag-exfil"` (`70` puan).
- `kanit_durumu`: `"dogrulandi"` (`+20` puan), `"kismi"` (`+5` puan) veya `"teorik"` (`+0` puan).
- Geçersiz şema, tür veya değer durumunda `ValueError` yükselt. Girdiyi değiştirme.

Puan ve öncelik hesabı:
- `zincir_bonusu`: `len(adimlar) >= 2` **ve** `adimlar` içinde `{"arac-yetki", "cikti-tuketici", "ag-ssrf"}` kümesinden en az bir katman varsa `+15`, aksi hâlde `0`.
- `puan`: `min(100, taban_puan + kanit_puani + zincir_bonusu)`.
- `oncelik`:
  - `kanit_durumu == "teorik"` ise puan ne olursa olsun `"izleme"`.
  - Aksi hâlde `puan >= 80` ise `"p1-acil"`, `puan >= 55` ise `"p2-yuksek"`, değilse `"p3-normal"`.

Sonucu `(-puan, bulgu_id)` sırasıyla şu öğelerden oluşan bir liste olarak döndür:
`{"bulgu_id": str, "zincir_uzunlugu": int, "puan": int, "oncelik": str}`

```starter
from ai_saldiri_veri import json_yukle

bulgular = json_yukle("kampanya/zincir_bulgulari.json")

def zincir_onceliklendir(bulgular):
    # HATA: Zincir bonusunu hesaplamıyor ve teorik bulguları doğrulanmış gibi yüksek önceliğe sokuyor.
    taban = {"salt-metin": 20, "veri-sizintisi": 40, "yetkisiz-arac": 60, "dis-ag-exfil": 70}
    sonuc = []
    for b in bulgular:
        p = taban[b["etki_turu"]]
        oncelik = "p1-acil" if p >= 60 else "p3-normal"
        sonuc.append({"bulgu_id": b["bulgu_id"], "zincir_uzunlugu": len(b["adimlar"]), "puan": p, "oncelik": oncelik})
    return sonuc

print(zincir_onceliklendir(bulgular))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-37")
```

```test
import copy
from pathlib import Path

ok(Path("kampanya/zincir_bulgulari.json").is_file(), "görünür zincir bulguları dosyası hazır")

ORNEK_BULGULAR = [
    {"bulgu_id": "b2", "adimlar": ["dogrudan-istem"], "etki_turu": "veri-sizintisi", "kanit_durumu": "dogrulandi"},
    {"bulgu_id": "b1", "adimlar": ["dolayli-rag", "arac-yetki"], "etki_turu": "yetkisiz-arac", "kanit_durumu": "dogrulandi"},
    {"bulgu_id": "b3", "adimlar": ["dolayli-rag", "ag-ssrf"], "etki_turu": "dis-ag-exfil", "kanit_durumu": "teorik"},
    {"bulgu_id": "b4", "adimlar": ["dogrudan-istem", "bellek-oturum"], "etki_turu": "salt-metin", "kanit_durumu": "kismi"},
    {"bulgu_id": "b5", "adimlar": ["dolayli-rag", "cikti-tuketici"], "etki_turu": "dis-ag-exfil", "kanit_durumu": "dogrulandi"},
]

def sozlesme(fn):
    try:
        once = copy.deepcopy(ORNEK_BULGULAR)
        r = fn(ORNEK_BULGULAR)
        if ORNEK_BULGULAR != once:
            return False
        if r != [
            {"bulgu_id": "b5", "zincir_uzunlugu": 2, "puan": 100, "oncelik": "p1-acil"},
            {"bulgu_id": "b1", "zincir_uzunlugu": 2, "puan": 95, "oncelik": "p1-acil"},
            {"bulgu_id": "b3", "zincir_uzunlugu": 2, "puan": 85, "oncelik": "izleme"},
            {"bulgu_id": "b2", "zincir_uzunlugu": 1, "puan": 60, "oncelik": "p2-yuksek"},
            {"bulgu_id": "b4", "zincir_uzunlugu": 2, "puan": 25, "oncelik": "p3-normal"},
        ]:
            return False
        esit_puan = [
            {"bulgu_id": "z", "adimlar": ["arac-yetki"], "etki_turu": "yetkisiz-arac", "kanit_durumu": "dogrulandi"},
            {"bulgu_id": "a", "adimlar": ["dolayli-rag", "arac-yetki"], "etki_turu": "veri-sizintisi", "kanit_durumu": "kismi"},
        ]
        r_esit = fn(esit_puan)
        if r_esit[0] != {"bulgu_id": "z", "zincir_uzunlugu": 1, "puan": 80, "oncelik": "p1-acil"} or r_esit[1]["oncelik"] != "p2-yuksek" or r_esit[1]["puan"] != 60:
            return False
        elli_bes = [{"bulgu_id": "e55", "adimlar": ["dolayli-rag", "arac-yetki"], "etki_turu": "salt-metin", "kanit_durumu": "dogrulandi"}]
        if fn(elli_bes)[0]["puan"] != 55 or fn(elli_bes)[0]["oncelik"] != "p2-yuksek":
            return False
        bes_adim = [{"bulgu_id": f"k{i}", "adimlar": ["dogrudan-istem", "dolayli-rag", "bellek-oturum", "arac-yetki", "ag-ssrf"], "etki_turu": "salt-metin", "kanit_durumu": "kismi"} for i in range(30)]
        if len(fn(bes_adim)) != 30 or fn(bes_adim)[0]["zincir_uzunlugu"] != 5:
            return False
        for b in [
            None, [], "liste", [None], [{}],
            [{"bulgu_id": f"k{i}", "adimlar": ["dogrudan-istem"], "etki_turu": "salt-metin", "kanit_durumu": "kismi"} for i in range(31)],
            [{"bulgu_id": "", "adimlar": ["dogrudan-istem"], "etki_turu": "salt-metin", "kanit_durumu": "kismi"}],
            [{"bulgu_id": 1, "adimlar": ["dogrudan-istem"], "etki_turu": "salt-metin", "kanit_durumu": "kismi"}],
            [{"bulgu_id": "a", "adimlar": ["dogrudan-istem"], "etki_turu": "salt-metin", "kanit_durumu": "kismi"},
             {"bulgu_id": "a", "adimlar": ["dolayli-rag"], "etki_turu": "salt-metin", "kanit_durumu": "kismi"}],
            [{"bulgu_id": "a", "adimlar": [], "etki_turu": "salt-metin", "kanit_durumu": "kismi"}],
            [{"bulgu_id": "a", "adimlar": ["dogrudan-istem", "dolayli-rag", "bellek-oturum", "arac-yetki", "cikti-tuketici", "ag-ssrf"], "etki_turu": "salt-metin", "kanit_durumu": "kismi"}],
            [{"bulgu_id": "a", "adimlar": "dogrudan-istem", "etki_turu": "salt-metin", "kanit_durumu": "kismi"}],
            [{"bulgu_id": "a", "adimlar": ("dogrudan-istem",), "etki_turu": "salt-metin", "kanit_durumu": "kismi"}],
            [{"bulgu_id": "a", "adimlar": [[]], "etki_turu": "salt-metin", "kanit_durumu": "kismi"}],
            [{"bulgu_id": "a", "adimlar": ["bilinmeyen"], "etki_turu": "salt-metin", "kanit_durumu": "kismi"}],
            [{"bulgu_id": "a", "adimlar": [1], "etki_turu": "salt-metin", "kanit_durumu": "kismi"}],
            [{"bulgu_id": "a", "adimlar": ["dogrudan-istem", "dogrudan-istem"], "etki_turu": "salt-metin", "kanit_durumu": "kismi"}],
            [{"bulgu_id": "a", "adimlar": ["dogrudan-istem"], "etki_turu": "rce", "kanit_durumu": "kismi"}],
            [{"bulgu_id": "a", "adimlar": ["dogrudan-istem"], "etki_turu": "salt-metin", "kanit_durumu": "kesin"}],
            [{"bulgu_id": "a", "adimlar": ["dogrudan-istem"], "etki_turu": "salt-metin", "kanit_durumu": "kismi", "ek": 1}],
        ]:
            try:
                fn(b)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(zincir_onceliklendir), "saldırı zinciri bonusu, 100 tavanı ve teorik bulgu izleme kuralı korunmalı")
def m_teorik_acil(bl):
    r = zincir_onceliklendir(bl)
    for x in r:
        if x["oncelik"] == "izleme":
            x["oncelik"] = "p1-acil"
    return r
def m_bonussuz(bl):
    r = zincir_onceliklendir([dict(x, adimlar=[x["adimlar"][0]]) for x in bl])
    return r
for ad, mutant in [("teorik bulguyu p1-acil yapan", m_teorik_acil), ("çok adımlı zincir bonusunu yok sayan", m_bonussuz)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def zincir_onceliklendir(bulgular):
    bilinen_katmanlar = {
        "dogrudan-istem",
        "dolayli-rag",
        "arac-yetki",
        "bellek-oturum",
        "cikti-tuketici",
        "ag-ssrf",
    }
    yurutme = {"arac-yetki", "cikti-tuketici", "ag-ssrf"}
    etki_taban = {
        "salt-metin": 20,
        "veri-sizintisi": 40,
        "yetkisiz-arac": 60,
        "dis-ag-exfil": 70,
    }
    kanit_puan = {
        "dogrulandi": 20,
        "kismi": 5,
        "teorik": 0,
    }
    if not isinstance(bulgular, list) or not 1 <= len(bulgular) <= 30:
        raise ValueError("bulgular 1..30 öğeli liste olmalı")
    gorulen = set()
    sonuc = []

    for b in bulgular:
        if not isinstance(b, dict) or set(b) != {"bulgu_id", "adimlar", "etki_turu", "kanit_durumu"}:
            raise ValueError("bulgu şeması geçersiz")
        bid = b["bulgu_id"]
        adimlar = b["adimlar"]
        etki = b["etki_turu"]
        kanit = b["kanit_durumu"]
        if not isinstance(bid, str) or not bid or bid in gorulen:
            raise ValueError("bulgu_id geçersiz")
        if not isinstance(adimlar, list) or not 1 <= len(adimlar) <= 5:
            raise ValueError("adimlar 1..5 öğeli liste olmalı")
        if any(not isinstance(a, str) or a not in bilinen_katmanlar for a in adimlar) or len(set(adimlar)) != len(adimlar):
            raise ValueError("adimlar geçersiz")
        if etki not in etki_taban:
            raise ValueError("etki_turu geçersiz")
        if kanit not in kanit_puan:
            raise ValueError("kanit_durumu geçersiz")
        gorulen.add(bid)

        bonus = 15 if len(adimlar) >= 2 and any(a in yurutme for a in adimlar) else 0
        puan = min(100, etki_taban[etki] + kanit_puan[kanit] + bonus)
        if kanit == "teorik":
            oncelik = "izleme"
        elif puan >= 80:
            oncelik = "p1-acil"
        elif puan >= 55:
            oncelik = "p2-yuksek"
        else:
            oncelik = "p3-normal"

        sonuc.append({
            "bulgu_id": bid,
            "zincir_uzunlugu": len(adimlar),
            "puan": puan,
            "oncelik": oncelik,
        })

    return sorted(sonuc, key=lambda r: (-r["puan"], r["bulgu_id"]))
```

```hint
Önce `puan = min(100, ...)` değerini hesapla; `kanit == "teorik"` kontrolünü `puan >= 80` kontrolünden **önce** yap ki yüksek puanlı teorik zincirler `"izleme"` olarak kalsın.
```
:::

::: gorev 3 · Operasyon kapanışı ve iz temizliğini (teardown) doğrula
`kapanis_temizlik_dogrula(envanter)` işlevini yaz. `envanter`, `1..30` öğeli bir listedir; her öğe tam olarak `{"iz_id", "tur", "durum", "dogrulama_sorgusu_temiz"}` anahtarlarını taşır:

- `iz_id`: boş olmayan ve listede benzersiz `str`.
- `tur`: `"rag-zehir-belgesi"`, `"kalici-bellek-kaydi"`, `"gecici-vekil-canary"` veya `"yerel-model-oturumu"`.
- `durum`: `"silindi"` veya `"aktif"`.
- `dogrulama_sorgusu_temiz`: `bool`.
- Geçersiz şema, tür veya değer durumunda `ValueError` yükselt. Girdiyi değiştirme.

Bir kayıt ancak `durum == "silindi"` **ve** `dogrulama_sorgusu_temiz == True` ise temizlenmiş sayılır (`temizlenen_iz`). Aksi hâlde `iz_id` değeri `kalan_izler` listesine, `tur` değeri ise `riskli_turler` kümesine eklenir.

Dönüş sözlüğü:

```text
{
  "toplam_iz": int,
  "temizlenen_iz": int,
  "kalan_izler": [...],     # alfabetik sıralı
  "riskli_turler": [...],   # alfabetik sıralı tekil liste
  "kapanis_onayi": bool     # len(kalan_izler) == 0
}
```

```starter
from ai_saldiri_veri import json_yukle

envanter = json_yukle("kampanya/kapanis_envanteri.json")

def kapanis_temizlik_dogrula(envanter):
    # HATA: Yalnız durum == "silindi" alanına bakıyor; doğrulama sorgusunun temiz dönüp dönmediğini kontrol etmiyor.
    kalan = [k["iz_id"] for k in envanter if k["durum"] != "silindi"]
    turler = sorted({k["tur"] for k in envanter if k["durum"] != "silindi"})
    return {
        "toplam_iz": len(envanter),
        "temizlenen_iz": len(envanter) - len(kalan),
        "kalan_izler": sorted(kalan),
        "riskli_turler": turler,
        "kapanis_onayi": len(kalan) == 0,
    }

print(kapanis_temizlik_dogrula(envanter))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-37")
```

```test
import copy
from pathlib import Path

ok(Path("kampanya/kapanis_envanteri.json").is_file(), "görünür kapanış envanteri dosyası hazır")

ORNEK_ENVANTER = [
    {"iz_id": "iz1", "tur": "rag-zehir-belgesi", "durum": "silindi", "dogrulama_sorgusu_temiz": True},
    {"iz_id": "iz3", "tur": "kalici-bellek-kaydi", "durum": "silindi", "dogrulama_sorgusu_temiz": False},
    {"iz_id": "iz2", "tur": "gecici-vekil-canary", "durum": "aktif", "dogrulama_sorgusu_temiz": True},
]

def sozlesme(fn):
    try:
        once = copy.deepcopy(ORNEK_ENVANTER)
        r = fn(ORNEK_ENVANTER)
        if ORNEK_ENVANTER != once:
            return False
        if r != {
            "toplam_iz": 3,
            "temizlenen_iz": 1,
            "kalan_izler": ["iz2", "iz3"],
            "riskli_turler": ["gecici-vekil-canary", "kalici-bellek-kaydi"],
            "kapanis_onayi": False,
        }:
            return False
        tam_temiz = [
            {"iz_id": f"t{i}", "tur": "yerel-model-oturumu", "durum": "silindi", "dogrulama_sorgusu_temiz": True}
            for i in range(30)
        ]
        if fn(tam_temiz) != {
            "toplam_iz": 30,
            "temizlenen_iz": 30,
            "kalan_izler": [],
            "riskli_turler": [],
            "kapanis_onayi": True,
        } or fn([tam_temiz[0]])["toplam_iz"] != 1:
            return False
        for b in [
            None, [], "liste", [None], [{}],
            [{"iz_id": f"t{i}", "tur": "yerel-model-oturumu", "durum": "silindi", "dogrulama_sorgusu_temiz": True} for i in range(31)],
            [{"iz_id": "", "tur": "rag-zehir-belgesi", "durum": "silindi", "dogrulama_sorgusu_temiz": True}],
            [{"iz_id": 1, "tur": "rag-zehir-belgesi", "durum": "silindi", "dogrulama_sorgusu_temiz": True}],
            [{"iz_id": "a", "tur": "rag-zehir-belgesi", "durum": "silindi", "dogrulama_sorgusu_temiz": True},
             {"iz_id": "a", "tur": "kalici-bellek-kaydi", "durum": "silindi", "dogrulama_sorgusu_temiz": True}],
            [{"iz_id": "a", "tur": "log-kaydi", "durum": "silindi", "dogrulama_sorgusu_temiz": True}],
            [{"iz_id": "a", "tur": "rag-zehir-belgesi", "durum": "beklemede", "dogrulama_sorgusu_temiz": True}],
            [{"iz_id": "a", "tur": "rag-zehir-belgesi", "durum": "silindi", "dogrulama_sorgusu_temiz": 1}],
            [{"iz_id": "a", "tur": "rag-zehir-belgesi", "durum": "silindi", "dogrulama_sorgusu_temiz": True, "ek": 1}],
        ]:
            try:
                fn(b)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(kapanis_temizlik_dogrula), "hem silinme durumu hem doğrulama sorgusu temizliği zorunlu tutulmalı")
def m_sorgusuz(env):
    kalan = [k["iz_id"] for k in env if k["durum"] != "silindi"]
    return {
        "toplam_iz": len(env),
        "temizlenen_iz": len(env) - len(kalan),
        "kalan_izler": sorted(kalan),
        "riskli_turler": sorted({k["tur"] for k in env if k["durum"] != "silindi"}),
        "kapanis_onayi": len(kalan) == 0,
    }
def m_durumsuz(env):
    kalan = [k["iz_id"] for k in env if not k["dogrulama_sorgusu_temiz"]]
    return {
        "toplam_iz": len(env),
        "temizlenen_iz": len(env) - len(kalan),
        "kalan_izler": sorted(kalan),
        "riskli_turler": sorted({k["tur"] for k in env if not k["dogrulama_sorgusu_temiz"]}),
        "kapanis_onayi": len(kalan) == 0,
    }
for ad, mutant in [("doğrulama sorgusunu atlayan", m_sorgusuz), ("silinme durumunu atlayan", m_durumsuz)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def kapanis_temizlik_dogrula(envanter):
    bilinen_turler = (
        "rag-zehir-belgesi",
        "kalici-bellek-kaydi",
        "gecici-vekil-canary",
        "yerel-model-oturumu",
    )
    if not isinstance(envanter, list) or not 1 <= len(envanter) <= 30:
        raise ValueError("envanter 1..30 öğeli liste olmalı")
    gorulen = set()
    temizlenen = 0
    kalan_izler = []
    riskli_turler = set()

    for kayit in envanter:
        if not isinstance(kayit, dict) or set(kayit) != {"iz_id", "tur", "durum", "dogrulama_sorgusu_temiz"}:
            raise ValueError("envanter şeması geçersiz")
        iid = kayit["iz_id"]
        tur = kayit["tur"]
        durum = kayit["durum"]
        sorgu_temiz = kayit["dogrulama_sorgusu_temiz"]
        if not isinstance(iid, str) or not iid or iid in gorulen:
            raise ValueError("iz_id geçersiz")
        if tur not in bilinen_turler:
            raise ValueError("tur geçersiz")
        if durum not in ("silindi", "aktif"):
            raise ValueError("durum geçersiz")
        if not isinstance(sorgu_temiz, bool):
            raise ValueError("dogrulama_sorgusu_temiz bool olmalı")
        gorulen.add(iid)

        if durum == "silindi" and sorgu_temiz:
            temizlenen += 1
        else:
            kalan_izler.append(iid)
            riskli_turler.add(tur)

    return {
        "toplam_iz": len(envanter),
        "temizlenen_iz": temizlenen,
        "kalan_izler": sorted(kalan_izler),
        "riskli_turler": sorted(riskli_turler),
        "kapanis_onayi": len(kalan_izler) == 0,
    }
```

```hint
`durum == "silindi" and sorgu_temiz` koşulunun ikisi birden sağlanmıyorsa kaydı `kalan_izler` ve `riskli_turler` içine ekle.
```
:::

::: gorev Gerçek deney · Yerel modelde saldırı zinciri ve kapanış/temizlik doğrulaması
Önceki üç görevdeki `kapsam_matrisi`, `zincir_onceliklendir` ve `kapanis_temizlik_dogrula` işlevlerini burada birleştir.

Bu gerçek deneyde `ai_lab.SohbetOturumu` ile yerel Ollama modeli üzerinde iki aşamalı bir operasyon yürütülür:
1. **Aktif test aşaması:** Bağlama geçici bir RAG zehir belgesi (`DOC-TEMP-99`) ve oturuma özel vekil işaret (`PAFTA-ZINCIR-...`) yerleştirilerek modelin tepkisi gözlenir; kapsam matrisi ve saldırı zinciri önceliklendirmesi hesaplanır.
2. **Kapanış ve temizlik doğrulaması (teardown):** Geçici RAG zehir belgesi ve vekil işaret bağlamdan kaldırılır; yerel modele **temizlik sonrası doğrulama sorgusu** gönderilerek yanıtın artık vekil işareti taşımadığı (`dogrulama_sorgusu_temiz == True`) ve yerel model oturumunun temizlendiği (`kapanis_temizlik_dogrula`) canlı olarak kanıtlanır.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab
from ai_saldiri_veri import json_yukle

def kapsam_matrisi(aktif_katmanlar, kosulan_testler):
    return {"katman_ozeti": {}, "kor_noktalar": list(aktif_katmanlar), "kapsam_orani": 0.0}

def zincir_onceliklendir(bulgular):
    return [{"bulgu_id": b["bulgu_id"], "zincir_uzunlugu": len(b["adimlar"]), "puan": 0, "oncelik": "izleme"} for b in bulgular]

def kapanis_temizlik_dogrula(envanter):
    return {"toplam_iz": len(envanter), "temizlenen_iz": 0, "kalan_izler": [k["iz_id"] for k in envanter], "riskli_turler": [], "kapanis_onayi": False}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_37 as deney
    deney.goster(kapsam_matrisi, zincir_onceliklendir, kapanis_temizlik_dogrula)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-37")
```

```test
import ai_lab
import copy
from sandbox import ai_gercek_ai_saldiri_37 as D

checks = []
_base_ok = ok
def ok(kosul, mesaj):
    checks.append(bool(kosul))
    return _base_ok(kosul, mesaj)

for ad in ("kapsam_matrisi", "zincir_onceliklendir", "kapanis_temizlik_dogrula"):
    need(ad)

sorun = ai_lab.kod_denetimi(src, ("kapsam_matrisi_referans", "zincir_onceliklendir_referans", "kapanis_temizlik_referans"))
ok(not sorun, "laboratuvar yamalanmamalı, referans işlevler çağrılmamalı")

def _sinir_ve_sema_kontrol():
    try:
        aktif = ["dogrudan-istem", "dolayli-rag", "arac-yetki"]
        testler = [
            {"test_id": "t1", "katman": "dogrudan-istem", "teknik": "rol", "durum": "basarisiz"},
            {"test_id": "t2", "katman": "dogrudan-istem", "teknik": "rol", "durum": "basari"},
            {"test_id": "t3", "katman": "dogrudan-istem", "teknik": "crescendo", "durum": "basarisiz"},
            {"test_id": "t4", "katman": "dolayli-rag", "teknik": "gizli-etiket", "durum": "basari"},
            {"test_id": "t5", "katman": "dolayli-rag", "teknik": "ustbilgi", "durum": "hata"},
        ]
        if kapsam_matrisi(copy.deepcopy(aktif), copy.deepcopy(testler)) != D.kapsam_matrisi_referans(aktif, testler):
            return False
        elli = [{"test_id": f"x{i}", "katman": "dogrudan-istem", "teknik": f"tek{i % 2}", "durum": "basarisiz"} for i in range(50)]
        if kapsam_matrisi(["dogrudan-istem"], elli)["kapsam_orani"] != 1.0 or kapsam_matrisi(["ag-ssrf"], [])["kor_noktalar"] != ["ag-ssrf"]:
            return False
        for ba, bt in [
            (None, []), ([], []), (("dogrudan-istem",), []), ("dogrudan-istem", []), ([1], []), ([[]], []), (["bilinmeyen"], []),
            (["dogrudan-istem", "dogrudan-istem"], []),
            (["dogrudan-istem"], None), (["dogrudan-istem"], "test"),
            (["dogrudan-istem"], [{"test_id": f"x{i}", "katman": "dogrudan-istem", "teknik": "t", "durum": "basari"} for i in range(51)]),
            (["dogrudan-istem"], [None]), (["dogrudan-istem"], [{}]),
            (["dogrudan-istem"], [{"test_id": "", "katman": "dogrudan-istem", "teknik": "t", "durum": "basari"}]),
            (["dogrudan-istem"], [{"test_id": 1, "katman": "dogrudan-istem", "teknik": "t", "durum": "basari"}]),
            (["dogrudan-istem"], [{"test_id": "a", "katman": "dogrudan-istem", "teknik": "t1", "durum": "basari"},
                                  {"test_id": "a", "katman": "dogrudan-istem", "teknik": "t2", "durum": "basarisiz"}]),
            (["dogrudan-istem"], [{"test_id": "a", "katman": "ag-ssrf", "teknik": "t1", "durum": "basari"}]),
            (["dogrudan-istem"], [{"test_id": "a", "katman": 1, "teknik": "t1", "durum": "basari"}]),
            (["dogrudan-istem"], [{"test_id": "a", "katman": [], "teknik": "t1", "durum": "basari"}]),
            (["dogrudan-istem"], [{"test_id": "a", "katman": "dogrudan-istem", "teknik": "", "durum": "basari"}]),
            (["dogrudan-istem"], [{"test_id": "a", "katman": "dogrudan-istem", "teknik": 1, "durum": "basari"}]),
            (["dogrudan-istem"], [{"test_id": "a", "katman": "dogrudan-istem", "teknik": "t1", "durum": "beklemede"}]),
            (["dogrudan-istem"], [{"test_id": "a", "katman": "dogrudan-istem", "teknik": "t1", "durum": "basari", "ek": 1}]),
        ]:
            try:
                kapsam_matrisi(ba, bt)
                return False
            except ValueError:
                pass

        bulgular = [
            {"bulgu_id": "b2", "adimlar": ["dogrudan-istem"], "etki_turu": "veri-sizintisi", "kanit_durumu": "dogrulandi"},
            {"bulgu_id": "b1", "adimlar": ["dolayli-rag", "arac-yetki"], "etki_turu": "yetkisiz-arac", "kanit_durumu": "dogrulandi"},
            {"bulgu_id": "b3", "adimlar": ["dolayli-rag", "ag-ssrf"], "etki_turu": "dis-ag-exfil", "kanit_durumu": "teorik"},
            {"bulgu_id": "b4", "adimlar": ["dogrudan-istem", "bellek-oturum"], "etki_turu": "salt-metin", "kanit_durumu": "kismi"},
            {"bulgu_id": "b5", "adimlar": ["dolayli-rag", "cikti-tuketici"], "etki_turu": "dis-ag-exfil", "kanit_durumu": "dogrulandi"},
        ]
        esit_puan = [
            {"bulgu_id": "z", "adimlar": ["arac-yetki"], "etki_turu": "yetkisiz-arac", "kanit_durumu": "dogrulandi"},
            {"bulgu_id": "a", "adimlar": ["dolayli-rag", "arac-yetki"], "etki_turu": "veri-sizintisi", "kanit_durumu": "kismi"},
        ]
        elli_bes = [{"bulgu_id": "e55", "adimlar": ["dolayli-rag", "arac-yetki"], "etki_turu": "salt-metin", "kanit_durumu": "dogrulandi"}]
        bes_adim = [{"bulgu_id": f"k{i}", "adimlar": ["dogrudan-istem", "dolayli-rag", "bellek-oturum", "arac-yetki", "ag-ssrf"], "etki_turu": "salt-metin", "kanit_durumu": "kismi"} for i in range(30)]
        for bl in (bulgular, esit_puan, elli_bes, bes_adim):
            if zincir_onceliklendir(copy.deepcopy(bl)) != D.zincir_onceliklendir_referans(bl):
                return False
        for bb in [
            None, [], "liste", [None], [{}],
            [{"bulgu_id": f"k{i}", "adimlar": ["dogrudan-istem"], "etki_turu": "salt-metin", "kanit_durumu": "kismi"} for i in range(31)],
            [{"bulgu_id": "", "adimlar": ["dogrudan-istem"], "etki_turu": "salt-metin", "kanit_durumu": "kismi"}],
            [{"bulgu_id": 1, "adimlar": ["dogrudan-istem"], "etki_turu": "salt-metin", "kanit_durumu": "kismi"}],
            [{"bulgu_id": "a", "adimlar": ["dogrudan-istem"], "etki_turu": "salt-metin", "kanit_durumu": "kismi"},
             {"bulgu_id": "a", "adimlar": ["dolayli-rag"], "etki_turu": "salt-metin", "kanit_durumu": "kismi"}],
            [{"bulgu_id": "a", "adimlar": [], "etki_turu": "salt-metin", "kanit_durumu": "kismi"}],
            [{"bulgu_id": "a", "adimlar": ["dogrudan-istem", "dolayli-rag", "bellek-oturum", "arac-yetki", "cikti-tuketici", "ag-ssrf"], "etki_turu": "salt-metin", "kanit_durumu": "kismi"}],
            [{"bulgu_id": "a", "adimlar": "dogrudan-istem", "etki_turu": "salt-metin", "kanit_durumu": "kismi"}],
            [{"bulgu_id": "a", "adimlar": ("dogrudan-istem",), "etki_turu": "salt-metin", "kanit_durumu": "kismi"}],
            [{"bulgu_id": "a", "adimlar": [[]], "etki_turu": "salt-metin", "kanit_durumu": "kismi"}],
            [{"bulgu_id": "a", "adimlar": ["bilinmeyen"], "etki_turu": "salt-metin", "kanit_durumu": "kismi"}],
            [{"bulgu_id": "a", "adimlar": [1], "etki_turu": "salt-metin", "kanit_durumu": "kismi"}],
            [{"bulgu_id": "a", "adimlar": ["dogrudan-istem", "dogrudan-istem"], "etki_turu": "salt-metin", "kanit_durumu": "kismi"}],
            [{"bulgu_id": "a", "adimlar": ["dogrudan-istem"], "etki_turu": "rce", "kanit_durumu": "kismi"}],
            [{"bulgu_id": "a", "adimlar": ["dogrudan-istem"], "etki_turu": "salt-metin", "kanit_durumu": "kesin"}],
            [{"bulgu_id": "a", "adimlar": ["dogrudan-istem"], "etki_turu": "salt-metin", "kanit_durumu": "kismi", "ek": 1}],
        ]:
            try:
                zincir_onceliklendir(bb)
                return False
            except ValueError:
                pass

        env = [
            {"iz_id": "iz1", "tur": "rag-zehir-belgesi", "durum": "silindi", "dogrulama_sorgusu_temiz": True},
            {"iz_id": "iz3", "tur": "kalici-bellek-kaydi", "durum": "silindi", "dogrulama_sorgusu_temiz": False},
            {"iz_id": "iz2", "tur": "gecici-vekil-canary", "durum": "aktif", "dogrulama_sorgusu_temiz": True},
        ]
        tam_temiz = [{"iz_id": f"t{i}", "tur": "yerel-model-oturumu", "durum": "silindi", "dogrulama_sorgusu_temiz": True} for i in range(30)]
        tek_iz = [tam_temiz[0]]
        if (
            kapanis_temizlik_dogrula(copy.deepcopy(env)) != D.kapanis_temizlik_referans(env)
            or kapanis_temizlik_dogrula(copy.deepcopy(tam_temiz)) != D.kapanis_temizlik_referans(tam_temiz)
            or kapanis_temizlik_dogrula(copy.deepcopy(tek_iz)) != D.kapanis_temizlik_referans(tek_iz)
        ):
            return False
        for be in [
            None, [], "liste", [None], [{}],
            [{"iz_id": f"t{i}", "tur": "yerel-model-oturumu", "durum": "silindi", "dogrulama_sorgusu_temiz": True} for i in range(31)],
            [{"iz_id": "", "tur": "rag-zehir-belgesi", "durum": "silindi", "dogrulama_sorgusu_temiz": True}],
            [{"iz_id": 1, "tur": "rag-zehir-belgesi", "durum": "silindi", "dogrulama_sorgusu_temiz": True}],
            [{"iz_id": "a", "tur": "rag-zehir-belgesi", "durum": "silindi", "dogrulama_sorgusu_temiz": True},
             {"iz_id": "a", "tur": "kalici-bellek-kaydi", "durum": "silindi", "dogrulama_sorgusu_temiz": True}],
            [{"iz_id": "a", "tur": "log-kaydi", "durum": "silindi", "dogrulama_sorgusu_temiz": True}],
            [{"iz_id": "a", "tur": "rag-zehir-belgesi", "durum": "beklemede", "dogrulama_sorgusu_temiz": True}],
            [{"iz_id": "a", "tur": "rag-zehir-belgesi", "durum": "silindi", "dogrulama_sorgusu_temiz": 1}],
            [{"iz_id": "a", "tur": "rag-zehir-belgesi", "durum": "silindi", "dogrulama_sorgusu_temiz": True, "ek": 1}],
        ]:
            try:
                kapanis_temizlik_dogrula(be)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(_sinir_ve_sema_kontrol(), "kapsam matrisi, zincir önceliklendirme ve kapanış temizliği tüm sınır ve şema kurallarını geçti")

if not all(checks):
    stop()

try:
    r = D.deney(kapsam_matrisi, zincir_onceliklendir, kapanis_temizlik_dogrula)
except Exception as e:
    ok(False, f"GERÇEK KAPANIŞ VE ZİNCİR DENEYİ YAPILAMADI: {type(e).__name__}: {e}")
    stop()

for ad, deger in r["kontroller"].items():
    ok(deger, "gerçek deney: " + ad)

ai_lab.kanit_yaz("saldiri-37-red-team-metodoloji-ii", {
    "kaynak": "gercek",
    "kabul": all(checks),
    "ders": "ai-saldiri-37",
    "ortam": r["ortam"],
    "ayarlar": r["ayarlar"],
    "deney": r,
    "ozet": r["ozet"],
})
o = r["ozet"]
ok(
    True,
    f"BULGU ({r['ortam']['model']['ad']}): kapsam oranı={o['kapsam_orani']}, "
    f"kör noktalar={o['kor_noktalar']}, en yüksek öncelik={o['en_yuksek_oncelik']}, "
    f"kapanış/temizlik onayı={o['kapanis_onayi']}.",
)
```

```solution
import ai_lab

def kapsam_matrisi(aktif_katmanlar, kosulan_testler):
    bilinen = (
        "dogrudan-istem",
        "dolayli-rag",
        "arac-yetki",
        "bellek-oturum",
        "cikti-tuketici",
        "ag-ssrf",
    )
    if not isinstance(aktif_katmanlar, list) or not aktif_katmanlar:
        raise ValueError("aktif_katmanlar boş olmayan liste olmalı")
    if any(not isinstance(k, str) or k not in bilinen for k in aktif_katmanlar):
        raise ValueError("bilinmeyen katman")
    if len(set(aktif_katmanlar)) != len(aktif_katmanlar):
        raise ValueError("yinelenen aktif katman")
    if not isinstance(kosulan_testler, list) or len(kosulan_testler) > 50:
        raise ValueError("kosulan_testler 0..50 öğeli liste olmalı")

    aktif_kume = set(aktif_katmanlar)
    sirali = sorted(aktif_kume)
    ozet = {
        k: {"gecerli_deneme": 0, "hata": 0, "basari": 0, "farkli_teknik": 0, "kapsandi": False}
        for k in sirali
    }
    teknikler = {k: set() for k in sirali}
    gorulen = set()

    for t in kosulan_testler:
        if not isinstance(t, dict) or set(t) != {"test_id", "katman", "teknik", "durum"}:
            raise ValueError("test şeması geçersiz")
        tid = t["test_id"]
        katman = t["katman"]
        teknik = t["teknik"]
        durum = t["durum"]
        if not isinstance(tid, str) or not tid or tid in gorulen:
            raise ValueError("test_id geçersiz")
        if not isinstance(katman, str) or katman not in aktif_kume:
            raise ValueError("katman aktif değil")
        if not isinstance(teknik, str) or not teknik:
            raise ValueError("teknik geçersiz")
        if durum not in ("basari", "basarisiz", "hata"):
            raise ValueError("durum geçersiz")
        gorulen.add(tid)

        if durum == "hata":
            ozet[katman]["hata"] += 1
        else:
            ozet[katman]["gecerli_deneme"] += 1
            teknikler[katman].add(teknik)
            if durum == "basari":
                ozet[katman]["basari"] += 1

    kor_noktalar = []
    for k in sirali:
        ft = len(teknikler[k])
        ozet[k]["farkli_teknik"] = ft
        ozet[k]["kapsandi"] = ft >= 2
        if not ozet[k]["kapsandi"]:
            kor_noktalar.append(k)

    kapsanan = len(sirali) - len(kor_noktalar)
    return {
        "katman_ozeti": ozet,
        "kor_noktalar": kor_noktalar,
        "kapsam_orani": round(kapsanan / len(sirali), 4),
    }

def zincir_onceliklendir(bulgular):
    bilinen_katmanlar = {
        "dogrudan-istem",
        "dolayli-rag",
        "arac-yetki",
        "bellek-oturum",
        "cikti-tuketici",
        "ag-ssrf",
    }
    yurutme = {"arac-yetki", "cikti-tuketici", "ag-ssrf"}
    etki_taban = {
        "salt-metin": 20,
        "veri-sizintisi": 40,
        "yetkisiz-arac": 60,
        "dis-ag-exfil": 70,
    }
    kanit_puan = {
        "dogrulandi": 20,
        "kismi": 5,
        "teorik": 0,
    }
    if not isinstance(bulgular, list) or not 1 <= len(bulgular) <= 30:
        raise ValueError("bulgular 1..30 öğeli liste olmalı")
    gorulen = set()
    sonuc = []

    for b in bulgular:
        if not isinstance(b, dict) or set(b) != {"bulgu_id", "adimlar", "etki_turu", "kanit_durumu"}:
            raise ValueError("bulgu şeması geçersiz")
        bid = b["bulgu_id"]
        adimlar = b["adimlar"]
        etki = b["etki_turu"]
        kanit = b["kanit_durumu"]
        if not isinstance(bid, str) or not bid or bid in gorulen:
            raise ValueError("bulgu_id geçersiz")
        if not isinstance(adimlar, list) or not 1 <= len(adimlar) <= 5:
            raise ValueError("adimlar 1..5 öğeli liste olmalı")
        if any(not isinstance(a, str) or a not in bilinen_katmanlar for a in adimlar) or len(set(adimlar)) != len(adimlar):
            raise ValueError("adimlar geçersiz")
        if etki not in etki_taban:
            raise ValueError("etki_turu geçersiz")
        if kanit not in kanit_puan:
            raise ValueError("kanit_durumu geçersiz")
        gorulen.add(bid)

        bonus = 15 if len(adimlar) >= 2 and any(a in yurutme for a in adimlar) else 0
        puan = min(100, etki_taban[etki] + kanit_puan[kanit] + bonus)
        if kanit == "teorik":
            oncelik = "izleme"
        elif puan >= 80:
            oncelik = "p1-acil"
        elif puan >= 55:
            oncelik = "p2-yuksek"
        else:
            oncelik = "p3-normal"

        sonuc.append({
            "bulgu_id": bid,
            "zincir_uzunlugu": len(adimlar),
            "puan": puan,
            "oncelik": oncelik,
        })

    return sorted(sonuc, key=lambda r: (-r["puan"], r["bulgu_id"]))

def kapanis_temizlik_dogrula(envanter):
    bilinen_turler = (
        "rag-zehir-belgesi",
        "kalici-bellek-kaydi",
        "gecici-vekil-canary",
        "yerel-model-oturumu",
    )
    if not isinstance(envanter, list) or not 1 <= len(envanter) <= 30:
        raise ValueError("envanter 1..30 öğeli liste olmalı")
    gorulen = set()
    temizlenen = 0
    kalan_izler = []
    riskli_turler = set()

    for kayit in envanter:
        if not isinstance(kayit, dict) or set(kayit) != {"iz_id", "tur", "durum", "dogrulama_sorgusu_temiz"}:
            raise ValueError("envanter şeması geçersiz")
        iid = kayit["iz_id"]
        tur = kayit["tur"]
        durum = kayit["durum"]
        sorgu_temiz = kayit["dogrulama_sorgusu_temiz"]
        if not isinstance(iid, str) or not iid or iid in gorulen:
            raise ValueError("iz_id geçersiz")
        if tur not in bilinen_turler:
            raise ValueError("tur geçersiz")
        if durum not in ("silindi", "aktif"):
            raise ValueError("durum geçersiz")
        if not isinstance(sorgu_temiz, bool):
            raise ValueError("dogrulama_sorgusu_temiz bool olmalı")
        gorulen.add(iid)

        if durum == "silindi" and sorgu_temiz:
            temizlenen += 1
        else:
            kalan_izler.append(iid)
            riskli_turler.add(tur)

    return {
        "toplam_iz": len(envanter),
        "temizlenen_iz": temizlenen,
        "kalan_izler": sorted(kalan_izler),
        "riskli_turler": sorted(riskli_turler),
        "kapanis_onayi": len(kalan_izler) == 0,
    }

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_37 as deney
    deney.goster(kapsam_matrisi, zincir_onceliklendir, kapanis_temizlik_dogrula)
```

```hint
Önceki üç görevdeki çözümlerini birleştir; canlı deneyde önce zehirli RAG bağlamı sınanır, ardından temizlenmiş bağlamda doğrulama sorgusuyla kapanış onayı üretilir.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
### Bulgu derinliği ile kanıt gücü ayrı eksenlerdir

Çok aşamalı zincir çizmek her okun gerçekten geçildiğini göstermez. Kapsam matrisi test edilmemiş katmanı, kanıt durumu doğrulanmamış etkiyi açık tutar. Önceliklendirme normal işlev ve gerçek etkiyle desteklenir. Teardown yalnız bu deneyin oluşturduğu geçici kaynakların kapatılmasıdır; diğer kullanıcının süreçlerini durdurmak değildir.

| Yaygın yanlış | Doğru sınır |
|---|---|
| Uzun zincir yüksek güven demektir | Her aşamanın ayrı kanıtı ve açık kör noktası vardır. |

Sonraki bağlantı: ai-savunma-24. [Birincil kaynak](https://docs.ollama.com/api/chat). Kaynak mekanizmanın ilgili API veya yöntemini açıklar; bu labın başarı oranının kanıtı yerel ham koşudur.
:::
