---
id: ai-saldiri-40
title: "Denial-of-Wallet Saldırısı: Pahalı Üretim, Bağlam Şişirme ve Ajan Döngüsü"
summary: OWASP LLM10 kapsamında aşırı çıkış üretimi (sponge/sayma tetikleyicileri), bağlam doldurma ve özyinelemeli ajan döngüleriyle token/süre maliyetini katlayan saldırıları analiz et ve gerçek modelde ölç.
timeout: 300
---

::: anlat Gerçek biçimi bil, sentetik temsili ayırt et
Klasik hizmet engelleme (DoS) saniyede binlerce ağ paketiyle bant genişliğini tüketirken, LLM sistemlerinde **Denial-of-Wallet (Cüzdan Tüketimi / OWASP LLM10: Unbounded Consumption)** tek bir masum görünümlü istekle bile binlerce çıkış tokenı, tam context window (KV-cache) ve tekrarlayan ajan araç çağrıları ürettirerek hem GPU kuyruğunu kilitler hem de API faturasını katlar.

| Gerçek araç / model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Bulut sağlayıcılarının (OpenAI, Anthropic, Bedrock) fatura dökümlerini, vLLM/Ollama `eval_count` / `prompt_eval_count` sayaçlarını, `done_reason="length"` kesilmelerini ve ajan orkestratör izlerini | İlk üç görevde `tuketim/*.json` altındaki **sentetik** üretim, bağlam ve ajan döngüsü izlerini; son görevde `ai_lab.SohbetOturumu` ile yerel Ollama modelinde gerçek sponge vs normal üretim ölçümünü | Yerel `3B–4B` modelde ölçülen milisaniye ve token sayısının, çok kiracılı bir vLLM kümesindeki tam dolar faturasına veya PagedAttention bellek doygunluğuna bire bir karşılık geldiğini söyleyemez |

> [!GÜVENLİK]
> **Kapsam ve dürüstlük sınırı:** Denial-of-Wallet testleri yalnızca yerel modellerde veya açıkça kota/bütçe tavanı tanımlanmış yetkili test ortamlarında yürütülür; üçüncü taraf üretim API'leri bu yerel laboratuvarın kapsamında değildir. İlk üç görevdeki `tuketim/uretim_adaylari.json`, `tuketim/baglam_oturumlari.json` ve `tuketim/ajan_donguleri.json` dosyaları **sentetik** eğitim verisidir ve her çalıştırmada (`setup`) yeniden kopyalanır (kalıcılık yoktur).
:::

::: anlat Çıkış tokenı girişten pahalıdır, çok turlu bağlam ve ajan döngüsü maliyeti karesel büyütür
Denial-of-Wallet saldırganı üç farklı maliyet çarpanını hedefler:

1. **Pahalı üretim (Sponge / Genişletme İstemleri):** Otoregresif dil modellerinde giriş tokenları (prefill) paralel işlenirken, her **çıkış tokenı (decode)** tüm model ağırlıklarının bellekten tekrar okunmasını gerektirir; bu derste maliyeti ayırmak için çıkış tokenına **3 katsayısı** verilir; bu sentetik muhasebe ağırlığı güncel bir sağlayıcı fiyatı değildir. Kısa bir istemle (`giris_token=20`) modeli `max_tokens` / `num_predict` tavanına (`bitis_nedeni == "length"`) kadar saymaya, ağaç açmaya veya çok dilli tekrara zorlayan istemlere **sponge (sünger) istemi** denir.
2. **Bağlam doldurma ve karesel geçmiş birikimi (Context Stuffing):** Durumsuz (stateless) sohbet API'lerinde her turda sistem istemi, RAG belgeleri ve önceki turların yanıtları modele yeniden gönderilir. Taban giriş maliyeti `taban = sistem_token + sum(rag_parcalari)` olduğunda, `t` (`0..T-1`) turundaki giriş `taban + t * tur_basi_cikis` olur; `T` tur sonunda toplam giriş maliyeti $\mathcal{O}(T^2)$ hızında büyür.
3. **Özyinelemeli ajan döngüsü (Agent Loop Exhaustion):** Dolaylı prompt enjeksiyonu veya kendini referans veren bir araç çıktısı, ajanın aynı `(arac, arg_ozeti)` çağrısını `tur_siniri` tavanına kadar tekrarlamasına yol açar; ilk tekrar adımından itibaren harcanan tüm tokenlar saf israftır.

> **Savunma köprüsü:** Bu saldırıların deterministik savunması (token bucket ile oran sınırlama, istemci bazlı maliyet muhasebesi ve `min(istenen, kalan, tavan)` ile `num_predict` bütçe kesimi) `ai-savunma-31` (*Sınırsız Tüketim Savunması: Bütçe ve Oran Sınırı*) dersinde adım adım kurulur.
:::

::: anlat Bulguyu sınırlı ve doğrulanabilir yaz: token çarpanını, tavan kesilmesini ve döngü adımını ayır
Bir maliyet/tüketim bulgusu *"Model yavaşladı"* diye yazılmaz; hangi mekanizmanın hangi çarpanı ürettiği sayısal olarak ayrıştırılır:

- **Sponge genişleme oranı:** Kısa bir girdinin (`giris_token`) kaç katı çıkış (`cikis_token / giris_token`) ürettiği ve üretimin doğal bitişle mi (`stop`) yoksa üst sınırda mı (`length`) kesildiği.
- **Oturum şişirme kaynağı:** Maliyetin tek turdaki şişkin RAG parçalarından mı (`sum(rag_parcalari) >= 2000`) yoksa çok turlu geçmiş birikiminden mi (`tur_sayisi >= 6`) kaynaklandığı.
- **Ajan döngüsü israfı:** Ajanın hangi adımda aynı `(arac, arg_ozeti)` çiftini tekrarlamaya başladığı ve bu noktadan `tur_siniri` sınırına kadar kaç token (`israf_token`) yaktığı.
:::

::: tahmin Çok turlu sohbette biriken giriş token maliyetini tahmin et
Üç turlu bir oturumda her turda önceki asistan yanıtlarının bağlama eklendiği aşağıdaki kodu incele:

```python
sistem = 100
rag = [200, 100]
taban = sistem + sum(rag)
turlar = 3
cikis = 50

girisler = [taban + t * cikis for t in range(turlar)]
print(girisler, sum(girisler))
```

???

```cikti
[400, 450, 500] 1350
```

İlk turda (`t=0`) yalnız sistem + RAG parçaları (`100 + 300 = 400` token) gönderilir. İkinci turda önceki turun `50` tokenlık yanıtı bağlama eklenir (`450`), üçüncü turda iki yanıt birikir (`500`). Böylece 3 turda toplam giriş tokenı `3 * 400 = 1200` değil `1350` olur; tur sayısı arttıkça geçmiş birikimi karesel maliyet yaratır.
:::

::: gorev 1 · Üretim şişirme (sponge) adaylarını ve ağırlıklı token maliyetini analiz et
`uretim_sisirme_analizi(adaylar)` işlevini yaz. `adaylar`, `1..20` öğeli bir listedir; her öğe tam olarak `{"istek_id", "tur", "giris_token", "cikis_token", "sure_ms", "bitis_nedeni"}` anahtarlarını taşır:

- `istek_id`: boş olmayan ve listede benzersiz `str`.
- `tur`: `"normal"`, `"sayma-sponge"`, `"agac-genisletme"` veya `"cok-dilli-tekrar"`.
- `giris_token`, `cikis_token`, `sure_ms`: `bool` olmayan ve `>= 1` olan `int`.
- `bitis_nedeni`: `"stop"` veya `"length"`.
- Geçersiz şema, tür veya değer durumunda `ValueError` yükselt. Girdiyi değiştirme.

Her kayıt için şu değerleri hesapla:
- `genisleme_orani`: `round(cikis_token / giris_token, 2)`
- `agirlikli_token`: `giris_token + 3 * cikis_token` (çıkış tokenının 3 kat ağırlıklı maliyeti)
- `tavan_vuruldu`: `bitis_nedeni == "length"` ise `True`, değilse `False`.

Ayrıca:
- `sponge_idleri`: `tur != "normal"` olan **ve** (`genisleme_orani >= 8.0` **veya** `tavan_vuruldu == True`) koşulunu sağlayan kayıtların `istek_id` değerlerinin alfabetik (`sorted`) listesi.
- `en_pahali_id`: `agirlikli_token` değeri en yüksek olan kaydın `istek_id`'si (eşitlikte alfabetik olarak küçük `istek_id` seçilir).

Dönüş sözlüğü:

```text
{
  "kayitlar": [
    {"istek_id": str, "genisleme_orani": float, "agirlikli_token": int, "tavan_vuruldu": bool},
    ...
  ],
  "sponge_idleri": [str, ...],
  "en_pahali_id": str
}
```

```starter
from ai_saldiri_veri import json_yukle

adaylar = json_yukle("tuketim/uretim_adaylari.json")

def uretim_sisirme_analizi(adaylar):
    # HATA: Çıkış tokenının 3 kat ağırlığını ve bitis_nedeni == "length" durumunu hesaba katmıyor.
    kayitlar = []
    for a in adaylar:
        oran = round(a["cikis_token"] / a["giris_token"], 2)
        kayitlar.append({
            "istek_id": a["istek_id"],
            "genisleme_orani": oran,
            "agirlikli_token": a["giris_token"] + a["cikis_token"],
            "tavan_vuruldu": False,
        })
    return {"kayitlar": kayitlar, "sponge_idleri": [], "en_pahali_id": adaylar[0]["istek_id"]}

print(uretim_sisirme_analizi(adaylar))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-40")
```

```test
import copy
from pathlib import Path

ok(Path("tuketim/uretim_adaylari.json").is_file(), "görünür üretim adayları dosyası hazır")

ORNEK_ADAYLAR = [
    {"istek_id": "r1", "tur": "normal", "giris_token": 10, "cikis_token": 90, "sure_ms": 500, "bitis_nedeni": "stop"},
    {"istek_id": "r2", "tur": "sayma-sponge", "giris_token": 25, "cikis_token": 200, "sure_ms": 1800, "bitis_nedeni": "stop"},
    {"istek_id": "r3", "tur": "agac-genisletme", "giris_token": 40, "cikis_token": 120, "sure_ms": 1100, "bitis_nedeni": "length"},
    {"istek_id": "r4", "tur": "cok-dilli-tekrar", "giris_token": 30, "cikis_token": 239, "sure_ms": 1900, "bitis_nedeni": "stop"},
]

def sozlesme(fn):
    try:
        once = copy.deepcopy(ORNEK_ADAYLAR)
        r = fn(ORNEK_ADAYLAR)
        if ORNEK_ADAYLAR != once:
            return False
        if r != {
            "kayitlar": [
                {"istek_id": "r1", "genisleme_orani": 9.0, "agirlikli_token": 280, "tavan_vuruldu": False},
                {"istek_id": "r2", "genisleme_orani": 8.0, "agirlikli_token": 625, "tavan_vuruldu": False},
                {"istek_id": "r3", "genisleme_orani": 3.0, "agirlikli_token": 400, "tavan_vuruldu": True},
                {"istek_id": "r4", "genisleme_orani": 7.97, "agirlikli_token": 747, "tavan_vuruldu": False},
            ],
            "sponge_idleri": ["r2", "r3"],
            "en_pahali_id": "r4",
        }:
            return False
        esit = [
            {"istek_id": "b", "tur": "normal", "giris_token": 10, "cikis_token": 10, "sure_ms": 10, "bitis_nedeni": "stop"},
            {"istek_id": "a", "tur": "normal", "giris_token": 10, "cikis_token": 10, "sure_ms": 10, "bitis_nedeni": "stop"},
        ]
        if fn(esit)["en_pahali_id"] != "a":
            return False
        yirmi = [{"istek_id": f"k{i:02d}", "tur": "normal", "giris_token": 1, "cikis_token": 1, "sure_ms": 1, "bitis_nedeni": "stop"} for i in range(20)]
        if len(fn(yirmi)["kayitlar"]) != 20 or len(fn([yirmi[0]])["kayitlar"]) != 1:
            return False
        for b in [
            None, [], "adaylar", [None], [{}],
            [{"istek_id": f"k{i}", "tur": "normal", "giris_token": 1, "cikis_token": 1, "sure_ms": 1, "bitis_nedeni": "stop"} for i in range(21)],
            [{"istek_id": "", "tur": "normal", "giris_token": 1, "cikis_token": 1, "sure_ms": 1, "bitis_nedeni": "stop"}],
            [{"istek_id": 1, "tur": "normal", "giris_token": 1, "cikis_token": 1, "sure_ms": 1, "bitis_nedeni": "stop"}],
            [{"istek_id": "a", "tur": "normal", "giris_token": 1, "cikis_token": 1, "sure_ms": 1, "bitis_nedeni": "stop"},
             {"istek_id": "a", "tur": "normal", "giris_token": 1, "cikis_token": 1, "sure_ms": 1, "bitis_nedeni": "stop"}],
            [{"istek_id": "a", "tur": "bilinmeyen", "giris_token": 1, "cikis_token": 1, "sure_ms": 1, "bitis_nedeni": "stop"}],
            [{"istek_id": "a", "tur": "normal", "giris_token": 0, "cikis_token": 1, "sure_ms": 1, "bitis_nedeni": "stop"}],
            [{"istek_id": "a", "tur": "normal", "giris_token": True, "cikis_token": 1, "sure_ms": 1, "bitis_nedeni": "stop"}],
            [{"istek_id": "a", "tur": "normal", "giris_token": 1.5, "cikis_token": 1, "sure_ms": 1, "bitis_nedeni": "stop"}],
            [{"istek_id": "a", "tur": "normal", "giris_token": 1, "cikis_token": 0, "sure_ms": 1, "bitis_nedeni": "stop"}],
            [{"istek_id": "a", "tur": "normal", "giris_token": 1, "cikis_token": True, "sure_ms": 1, "bitis_nedeni": "stop"}],
            [{"istek_id": "a", "tur": "normal", "giris_token": 1, "cikis_token": 1.5, "sure_ms": 1, "bitis_nedeni": "stop"}],
            [{"istek_id": "a", "tur": "normal", "giris_token": 1, "cikis_token": 1, "sure_ms": 0, "bitis_nedeni": "stop"}],
            [{"istek_id": "a", "tur": "normal", "giris_token": 1, "cikis_token": 1, "sure_ms": True, "bitis_nedeni": "stop"}],
            [{"istek_id": "a", "tur": "normal", "giris_token": 1, "cikis_token": 1, "sure_ms": 1.5, "bitis_nedeni": "stop"}],
            [{"istek_id": "a", "tur": "normal", "giris_token": 1, "cikis_token": 1, "sure_ms": 1, "bitis_nedeni": "iptal"}],
            [{"istek_id": "a", "tur": "normal", "giris_token": 1, "cikis_token": 1, "sure_ms": 1, "bitis_nedeni": "stop", "ek": 1}],
        ]:
            try:
                fn(b)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(uretim_sisirme_analizi), "sponge genişleme oranı, tavan vurulması ve ağırlıklı token maliyeti doğru hesaplanmalı")
def m_normal_dahil(a):
    r = uretim_sisirme_analizi(a)
    r["sponge_idleri"] = sorted(k["istek_id"] for k in r["kayitlar"] if k["genisleme_orani"] >= 8.0 or k["tavan_vuruldu"])
    return r
def m_agirliksiz(a):
    r = uretim_sisirme_analizi(a)
    for k, x in zip(r["kayitlar"], a):
        k["agirlikli_token"] = x["giris_token"] + x["cikis_token"]
    return r
for ad, mutant in [("normal isteği sponge sayan", m_normal_dahil), ("çıkış ağırlığını 1x alan", m_agirliksiz)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def uretim_sisirme_analizi(adaylar):
    turler = ("normal", "sayma-sponge", "agac-genisletme", "cok-dilli-tekrar")
    nedenler = ("stop", "length")
    if not isinstance(adaylar, list) or not 1 <= len(adaylar) <= 20:
        raise ValueError("adaylar geçersiz")
    gorulen = set()
    kayitlar = []
    sponge_idleri = []

    for a in adaylar:
        if not isinstance(a, dict) or set(a) != {"istek_id", "tur", "giris_token", "cikis_token", "sure_ms", "bitis_nedeni"}:
            raise ValueError("aday şeması geçersiz")
        iid = a["istek_id"]
        tur = a["tur"]
        giris = a["giris_token"]
        cikis = a["cikis_token"]
        sure = a["sure_ms"]
        neden = a["bitis_nedeni"]
        if not isinstance(iid, str) or not iid or iid in gorulen:
            raise ValueError("istek_id geçersiz")
        if tur not in turler:
            raise ValueError("tur geçersiz")
        if isinstance(giris, bool) or not isinstance(giris, int) or giris < 1:
            raise ValueError("giris_token geçersiz")
        if isinstance(cikis, bool) or not isinstance(cikis, int) or cikis < 1:
            raise ValueError("cikis_token geçersiz")
        if isinstance(sure, bool) or not isinstance(sure, int) or sure < 1:
            raise ValueError("sure_ms geçersiz")
        if neden not in nedenler:
            raise ValueError("bitis_nedeni geçersiz")
        gorulen.add(iid)

        oran = round(cikis / giris, 2)
        tavan = neden == "length"
        agirlikli = giris + 3 * cikis
        if tur != "normal" and (oran >= 8.0 or tavan):
            sponge_idleri.append(iid)

        kayitlar.append({
            "istek_id": iid,
            "genisleme_orani": oran,
            "agirlikli_token": agirlikli,
            "tavan_vuruldu": tavan,
        })

    en_pahali_id = min(kayitlar, key=lambda r: (-r["agirlikli_token"], r["istek_id"]))["istek_id"]
    return {
        "kayitlar": kayitlar,
        "sponge_idleri": sorted(sponge_idleri),
        "en_pahali_id": en_pahali_id,
    }
```

```hint
`sponge_idleri` listesine yalnızca `tur != "normal"` olan ve (`oran >= 8.0` veya `bitis_nedeni == "length"`) koşulunu sağlayan kayıtları ekle.
```
:::

::: gorev 2 · Çok turlu oturumlarda bağlam doldurma ve geçmiş birikimi çarpanını hesapla
`baglam_doldurma_carpani(oturumlar)` işlevini yaz. `oturumlar`, `1..20` öğeli bir listedir; her öğe tam olarak `{"oturum_id", "sistem_token", "rag_parcalari", "tur_sayisi", "tur_basi_cikis"}` anahtarlarını taşır:

- `oturum_id`: boş olmayan ve listede benzersiz `str`.
- `sistem_token`, `tur_basi_cikis`: `bool` olmayan ve `>= 1` olan `int`.
- `rag_parcalari`: `1..20` öğeli, her öğesi `bool` olmayan ve `>= 1` olan `int` listesi.
- `tur_sayisi`: `bool` olmayan ve `1 <= tur_sayisi <= 20` olan `int`.
- Geçersiz şema, tür veya değer durumunda `ValueError` yükselt. Girdiyi değiştirme.

Her oturum için:
- Taban giriş tokenı `taban = sistem_token + sum(rag_parcalari)` olarak hesaplanır.
- Durumsuz sohbette `t` (`0 <= t < tur_sayisi`) turunda gönderilen giriş tokenı `taban + t * tur_basi_cikis` olur; `toplam_giris` tüm turların giriş tokenları toplamıdır.
- `toplam_cikis = tur_sayisi * tur_basi_cikis`.
- `agirlikli_maliyet = toplam_giris + 3 * toplam_cikis`.
- `sisirme_var`: `sum(rag_parcalari) >= 2000` **veya** `tur_sayisi >= 6` ise `True`, aksi hâlde `False`.

Girdi sırasıyla `{"oturum_id": str, "toplam_giris": int, "toplam_cikis": int, "agirlikli_maliyet": int, "sisirme_var": bool}` listesi döndür.

```starter
from ai_saldiri_veri import json_yukle

oturumlar = json_yukle("tuketim/baglam_oturumlari.json")

def baglam_doldurma_carpani(oturumlar):
    # HATA: Önceki turların çıkışlarının sonraki turlarda girişe eklendiğini hesaba katmıyor.
    sonuc = []
    for o in oturumlar:
        taban = o["sistem_token"] + sum(o["rag_parcalari"])
        giris = taban * o["tur_sayisi"]
        cikis = o["tur_sayisi"] * o["tur_basi_cikis"]
        sonuc.append({
            "oturum_id": o["oturum_id"],
            "toplam_giris": giris,
            "toplam_cikis": cikis,
            "agirlikli_maliyet": giris + 3 * cikis,
            "sisirme_var": False,
        })
    return sonuc

print(baglam_doldurma_carpani(oturumlar))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-40")
```

```test
import copy
from pathlib import Path

ok(Path("tuketim/baglam_oturumlari.json").is_file(), "görünür bağlam oturumları dosyası hazır")

ORNEK_OTURUMLAR = [
    {"oturum_id": "o1", "sistem_token": 100, "rag_parcalari": [500, 1499], "tur_sayisi": 5, "tur_basi_cikis": 40},
    {"oturum_id": "o2", "sistem_token": 100, "rag_parcalari": [1000, 1000], "tur_sayisi": 2, "tur_basi_cikis": 50},
    {"oturum_id": "o3", "sistem_token": 100, "rag_parcalari": [200], "tur_sayisi": 6, "tur_basi_cikis": 30},
]

def sozlesme(fn):
    try:
        once = copy.deepcopy(ORNEK_OTURUMLAR)
        r = fn(ORNEK_OTURUMLAR)
        if ORNEK_OTURUMLAR != once:
            return False
        if r != [
            {"oturum_id": "o1", "toplam_giris": 10895, "toplam_cikis": 200, "agirlikli_maliyet": 11495, "sisirme_var": False},
            {"oturum_id": "o2", "toplam_giris": 4250, "toplam_cikis": 100, "agirlikli_maliyet": 4550, "sisirme_var": True},
            {"oturum_id": "o3", "toplam_giris": 2250, "toplam_cikis": 180, "agirlikli_maliyet": 2790, "sisirme_var": True},
        ]:
            return False
        yirmi_parca = [{"oturum_id": f"x{i}", "sistem_token": 1, "rag_parcalari": [1] * 20, "tur_sayisi": 20, "tur_basi_cikis": 1} for i in range(20)]
        if len(fn(yirmi_parca)) != 20 or len(fn([{"oturum_id": "tek", "sistem_token": 1, "rag_parcalari": [1], "tur_sayisi": 1, "tur_basi_cikis": 1}])) != 1:
            return False
        for b in [
            None, [], "oturum", [None], [{}],
            [{"oturum_id": f"x{i}", "sistem_token": 1, "rag_parcalari": [1], "tur_sayisi": 1, "tur_basi_cikis": 1} for i in range(21)],
            [{"oturum_id": "", "sistem_token": 1, "rag_parcalari": [1], "tur_sayisi": 1, "tur_basi_cikis": 1}],
            [{"oturum_id": 1, "sistem_token": 1, "rag_parcalari": [1], "tur_sayisi": 1, "tur_basi_cikis": 1}],
            [{"oturum_id": "a", "sistem_token": 1, "rag_parcalari": [1], "tur_sayisi": 1, "tur_basi_cikis": 1},
             {"oturum_id": "a", "sistem_token": 1, "rag_parcalari": [1], "tur_sayisi": 1, "tur_basi_cikis": 1}],
            [{"oturum_id": "a", "sistem_token": 0, "rag_parcalari": [1], "tur_sayisi": 1, "tur_basi_cikis": 1}],
            [{"oturum_id": "a", "sistem_token": True, "rag_parcalari": [1], "tur_sayisi": 1, "tur_basi_cikis": 1}],
            [{"oturum_id": "a", "sistem_token": 1.5, "rag_parcalari": [1], "tur_sayisi": 1, "tur_basi_cikis": 1}],
            [{"oturum_id": "a", "sistem_token": 1, "rag_parcalari": [], "tur_sayisi": 1, "tur_basi_cikis": 1}],
            [{"oturum_id": "a", "sistem_token": 1, "rag_parcalari": (1,), "tur_sayisi": 1, "tur_basi_cikis": 1}],
            [{"oturum_id": "a", "sistem_token": 1, "rag_parcalari": [1] * 21, "tur_sayisi": 1, "tur_basi_cikis": 1}],
            [{"oturum_id": "a", "sistem_token": 1, "rag_parcalari": [0], "tur_sayisi": 1, "tur_basi_cikis": 1}],
            [{"oturum_id": "a", "sistem_token": 1, "rag_parcalari": [True], "tur_sayisi": 1, "tur_basi_cikis": 1}],
            [{"oturum_id": "a", "sistem_token": 1, "rag_parcalari": [1.5], "tur_sayisi": 1, "tur_basi_cikis": 1}],
            [{"oturum_id": "a", "sistem_token": 1, "rag_parcalari": "10", "tur_sayisi": 1, "tur_basi_cikis": 1}],
            [{"oturum_id": "a", "sistem_token": 1, "rag_parcalari": [1], "tur_sayisi": 0, "tur_basi_cikis": 1}],
            [{"oturum_id": "a", "sistem_token": 1, "rag_parcalari": [1], "tur_sayisi": 21, "tur_basi_cikis": 1}],
            [{"oturum_id": "a", "sistem_token": 1, "rag_parcalari": [1], "tur_sayisi": True, "tur_basi_cikis": 1}],
            [{"oturum_id": "a", "sistem_token": 1, "rag_parcalari": [1], "tur_sayisi": 1.5, "tur_basi_cikis": 1}],
            [{"oturum_id": "a", "sistem_token": 1, "rag_parcalari": [1], "tur_sayisi": 1, "tur_basi_cikis": 0}],
            [{"oturum_id": "a", "sistem_token": 1, "rag_parcalari": [1], "tur_sayisi": 1, "tur_basi_cikis": True}],
            [{"oturum_id": "a", "sistem_token": 1, "rag_parcalari": [1], "tur_sayisi": 1, "tur_basi_cikis": 1.5}],
            [{"oturum_id": "a", "sistem_token": 1, "rag_parcalari": [1], "tur_sayisi": 1, "tur_basi_cikis": 1, "ek": 1}],
        ]:
            try:
                fn(b)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(baglam_doldurma_carpani), "çok turlu geçmiş birikimi ve RAG şişirme maliyeti doğru hesaplanmalı")
def m_sabit_giris(o):
    r = baglam_doldurma_carpani(o)
    for k, x in zip(r, o):
        k["toplam_giris"] = (x["sistem_token"] + sum(x["rag_parcalari"])) * x["tur_sayisi"]
    return r
def m_sisirme_yok(o):
    return [dict(x, sisirme_var=False) for x in baglam_doldurma_carpani(o)]
for ad, mutant in [("geçmiş birikimini saymayan", m_sabit_giris), ("şişirme bayrağını kapatan", m_sisirme_yok)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def baglam_doldurma_carpani(oturumlar):
    if not isinstance(oturumlar, list) or not 1 <= len(oturumlar) <= 20:
        raise ValueError("oturumlar geçersiz")
    gorulen = set()
    sonuc = []

    for o in oturumlar:
        if not isinstance(o, dict) or set(o) != {"oturum_id", "sistem_token", "rag_parcalari", "tur_sayisi", "tur_basi_cikis"}:
            raise ValueError("oturum şeması geçersiz")
        oid = o["oturum_id"]
        sistem = o["sistem_token"]
        rag = o["rag_parcalari"]
        turlar = o["tur_sayisi"]
        cikis_basi = o["tur_basi_cikis"]
        if not isinstance(oid, str) or not oid or oid in gorulen:
            raise ValueError("oturum_id geçersiz")
        if isinstance(sistem, bool) or not isinstance(sistem, int) or sistem < 1:
            raise ValueError("sistem_token geçersiz")
        if not isinstance(rag, list) or not 1 <= len(rag) <= 20:
            raise ValueError("rag_parcalari geçersiz")
        for p in rag:
            if isinstance(p, bool) or not isinstance(p, int) or p < 1:
                raise ValueError("rag parçası geçersiz")
        if isinstance(turlar, bool) or not isinstance(turlar, int) or not 1 <= turlar <= 20:
            raise ValueError("tur_sayisi geçersiz")
        if isinstance(cikis_basi, bool) or not isinstance(cikis_basi, int) or cikis_basi < 1:
            raise ValueError("tur_basi_cikis geçersiz")
        gorulen.add(oid)

        rag_toplam = sum(rag)
        taban = sistem + rag_toplam
        toplam_giris = sum(taban + t * cikis_basi for t in range(turlar))
        toplam_cikis = turlar * cikis_basi
        agirlikli = toplam_giris + 3 * toplam_cikis
        sisirme = rag_toplam >= 2000 or turlar >= 6

        sonuc.append({
            "oturum_id": oid,
            "toplam_giris": toplam_giris,
            "toplam_cikis": toplam_cikis,
            "agirlikli_maliyet": agirlikli,
            "sisirme_var": sisirme,
        })
    return sonuc
```

```hint
Her turda `taban + t * tur_basi_cikis` (`t in range(tur_sayisi)`) kadar giriş tokenı harcanır; `sisirme_var` ise `sum(rag_parcalari) >= 2000 or tur_sayisi >= 6` olduğunda `True` döner.
```
:::

::: gorev 3 · Ajan araç döngülerinde tekrar israfını ve tur sınırı aşımını tespit et
`ajan_dongusu_tuketimi(izler, tur_siniri)` işlevini yaz:

- `tur_siniri`: `bool` olmayan ve `2 <= tur_siniri <= 20` olan `int`.
- `izler`: `1..20` öğeli liste; her öğe tam olarak `{"iz_id", "adimlar"}` anahtarlarını taşır:
  - `iz_id`: boş olmayan ve listede benzersiz `str`.
  - `adimlar`: `1..30` öğeli liste; her adım tam olarak `{"arac", "arg_ozeti", "giris_token", "cikis_token"}` anahtarlarını taşır (`arac` ve `arg_ozeti` boş olmayan `str`; `giris_token` ve `cikis_token` `bool` olmayan ve `>= 1` olan `int`).
- Geçersiz şema, tür veya değer durumunda `ValueError` yükselt. Girdiyi değiştirme.

Her iz için:
- `tekrar_dongusu`: `adimlar` içinde aynı `(arac, arg_ozeti)` çifti en az ikinci kez görülüyorsa `True`, yoksa `False`.
- `sinir_asimi`: `len(adimlar) >= tur_siniri` ise `True`, yoksa `False`.
- `israf_token`: `tekrar_dongusu == True` ise, **ilk tekrar eden adımın indeksinden başlayarak** dizinin sonuna kadar tüm adımların `giris_token + cikis_token` toplamı; `tekrar_dongusu == False` ise `0`.
- `durum`:
  - `tekrar_dongusu` ve `sinir_asimi` → `"sonsuz-dongu-tuketimi"`
  - Yalnız `tekrar_dongusu` → `"tekrarli-arac-israfi"`
  - Yalnız `sinir_asimi` → `"uzun-zincir"`
  - İkisi de `False` → `"normal"`

Girdi sırasıyla `{"iz_id": str, "tekrar_dongusu": bool, "sinir_asimi": bool, "israf_token": int, "durum": str}` listesi döndür.

```starter
from ai_saldiri_veri import json_yukle

izler = json_yukle("tuketim/ajan_donguleri.json")

def ajan_dongusu_tuketimi(izler, tur_siniri):
    # HATA: Aynı (arac, arg_ozeti) tekrarını ve israf edilen tokenları hesaplamıyor.
    return [
        {
            "iz_id": iz["iz_id"],
            "tekrar_dongusu": False,
            "sinir_asimi": len(iz["adimlar"]) >= tur_siniri,
            "israf_token": 0,
            "durum": "normal",
        }
        for iz in izler
    ]

print(ajan_dongusu_tuketimi(izler, 4))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-40")
```

```test
import copy
from pathlib import Path

ok(Path("tuketim/ajan_donguleri.json").is_file(), "görünür ajan döngüleri dosyası hazır")

ORNEK_IZLER = [
    {
        "iz_id": "i1",
        "adimlar": [
            {"arac": "ara", "arg_ozeti": "q=1", "giris_token": 100, "cikis_token": 20},
            {"arac": "oku", "arg_ozeti": "id=2", "giris_token": 150, "cikis_token": 30},
        ],
    },
    {
        "iz_id": "i2",
        "adimlar": [
            {"arac": "ara", "arg_ozeti": "q=1", "giris_token": 100, "cikis_token": 20},
            {"arac": "oku", "arg_ozeti": "id=loop", "giris_token": 200, "cikis_token": 40},
            {"arac": "oku", "arg_ozeti": "id=loop", "giris_token": 300, "cikis_token": 40},
            {"arac": "oku", "arg_ozeti": "id=loop", "giris_token": 400, "cikis_token": 40},
        ],
    },
    {
        "iz_id": "i3",
        "adimlar": [
            {"arac": "ara", "arg_ozeti": "q=1", "giris_token": 100, "cikis_token": 20},
            {"arac": "ara", "arg_ozeti": "q=1", "giris_token": 150, "cikis_token": 25},
            {"arac": "yaz", "arg_ozeti": "ad=son", "giris_token": 180, "cikis_token": 30},
        ],
    },
    {
        "iz_id": "i4",
        "adimlar": [
            {"arac": "a1", "arg_ozeti": "x=1", "giris_token": 50, "cikis_token": 10},
            {"arac": "a2", "arg_ozeti": "x=2", "giris_token": 60, "cikis_token": 10},
            {"arac": "a3", "arg_ozeti": "x=3", "giris_token": 70, "cikis_token": 10},
            {"arac": "a4", "arg_ozeti": "x=4", "giris_token": 80, "cikis_token": 10},
        ],
    },
]

def sozlesme(fn):
    try:
        once = copy.deepcopy(ORNEK_IZLER)
        r = fn(ORNEK_IZLER, 4)
        if ORNEK_IZLER != once:
            return False
        if r != [
            {"iz_id": "i1", "tekrar_dongusu": False, "sinir_asimi": False, "israf_token": 0, "durum": "normal"},
            {"iz_id": "i2", "tekrar_dongusu": True, "sinir_asimi": True, "israf_token": 780, "durum": "sonsuz-dongu-tuketimi"},
            {"iz_id": "i3", "tekrar_dongusu": True, "sinir_asimi": False, "israf_token": 385, "durum": "tekrarli-arac-israfi"},
            {"iz_id": "i4", "tekrar_dongusu": False, "sinir_asimi": True, "israf_token": 0, "durum": "uzun-zincir"},
        ]:
            return False
        otuz_adim = [{"iz_id": f"z{i}", "adimlar": [{"arac": f"a{j}", "arg_ozeti": "k", "giris_token": 1, "cikis_token": 1} for j in range(30)]} for i in range(20)]
        if len(fn(otuz_adim, 20)) != 20 or fn([{"iz_id": "t", "adimlar": [{"arac": "a", "arg_ozeti": "b", "giris_token": 1, "cikis_token": 1}]}], 2)[0]["sinir_asimi"] is not False:
            return False
        for b_iz, b_sinir in [
            (None, 4), ([], 4), ("iz", 4), ([None], 4), ([{}], 4),
            (ORNEK_IZLER, 1), (ORNEK_IZLER, 21), (ORNEK_IZLER, True), (ORNEK_IZLER, "4"),
            ([{"iz_id": f"z{i}", "adimlar": [{"arac": "a", "arg_ozeti": "b", "giris_token": 1, "cikis_token": 1}]} for i in range(21)], 4),
            ([{"iz_id": "", "adimlar": [{"arac": "a", "arg_ozeti": "b", "giris_token": 1, "cikis_token": 1}]}], 4),
            ([{"iz_id": 1, "adimlar": [{"arac": "a", "arg_ozeti": "b", "giris_token": 1, "cikis_token": 1}]}], 4),
            ([{"iz_id": "a", "adimlar": [{"arac": "a", "arg_ozeti": "b", "giris_token": 1, "cikis_token": 1}]},
              {"iz_id": "a", "adimlar": [{"arac": "a", "arg_ozeti": "b", "giris_token": 1, "cikis_token": 1}]}], 4),
            ([{"iz_id": "a", "adimlar": []}], 4),
            ([{"iz_id": "a", "adimlar": [{"arac": "a", "arg_ozeti": "b", "giris_token": 1, "cikis_token": 1}] * 31}], 4),
            ([{"iz_id": "a", "adimlar": "adim"}], 4),
            ([{"iz_id": "a", "adimlar": ({"arac": "a", "arg_ozeti": "b", "giris_token": 1, "cikis_token": 1},)}], 4),
            ([{"iz_id": "a", "adimlar": [["arac", "arg_ozeti", "giris_token", "cikis_token"]]}], 4),
            ([{"iz_id": "a", "adimlar": [{}]}], 4),
            ([{"iz_id": "a", "adimlar": [{"arac": "", "arg_ozeti": "b", "giris_token": 1, "cikis_token": 1}]}], 4),
            ([{"iz_id": "a", "adimlar": [{"arac": 1, "arg_ozeti": "b", "giris_token": 1, "cikis_token": 1}]}], 4),
            ([{"iz_id": "a", "adimlar": [{"arac": "a", "arg_ozeti": "", "giris_token": 1, "cikis_token": 1}]}], 4),
            ([{"iz_id": "a", "adimlar": [{"arac": "a", "arg_ozeti": 1, "giris_token": 1, "cikis_token": 1}]}], 4),
            ([{"iz_id": "a", "adimlar": [{"arac": "a", "arg_ozeti": "b", "giris_token": 0, "cikis_token": 1}]}], 4),
            ([{"iz_id": "a", "adimlar": [{"arac": "a", "arg_ozeti": "b", "giris_token": True, "cikis_token": 1}]}], 4),
            ([{"iz_id": "a", "adimlar": [{"arac": "a", "arg_ozeti": "b", "giris_token": 1.5, "cikis_token": 1}]}], 4),
            ([{"iz_id": "a", "adimlar": [{"arac": "a", "arg_ozeti": "b", "giris_token": 1, "cikis_token": 0}]}], 4),
            ([{"iz_id": "a", "adimlar": [{"arac": "a", "arg_ozeti": "b", "giris_token": 1, "cikis_token": True}]}], 4),
            ([{"iz_id": "a", "adimlar": [{"arac": "a", "arg_ozeti": "b", "giris_token": 1, "cikis_token": 1.5}]}], 4),
            ([{"iz_id": "a", "adimlar": [{"arac": "a", "arg_ozeti": "b", "giris_token": 1, "cikis_token": 1}], "ek": 1}], 4),
        ]:
            try:
                fn(b_iz, b_sinir)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(ajan_dongusu_tuketimi), "ajan araç döngüsü tekrarı, tur sınırı aşımı ve israf token hesabı doğru olmalı")
def m_israf_sifir(iz, ts):
    return [dict(x, israf_token=0) for x in ajan_dongusu_tuketimi(iz, ts)]
def m_durum_hep_normal(iz, ts):
    return [dict(x, durum="normal") for x in ajan_dongusu_tuketimi(iz, ts)]
for ad, mutant in [("israf tokenı sıfırlayan", m_israf_sifir), ("döngü durumunu gizleyen", m_durum_hep_normal)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def ajan_dongusu_tuketimi(izler, tur_siniri):
    if isinstance(tur_siniri, bool) or not isinstance(tur_siniri, int) or not 2 <= tur_siniri <= 20:
        raise ValueError("tur_siniri geçersiz")
    if not isinstance(izler, list) or not 1 <= len(izler) <= 20:
        raise ValueError("izler geçersiz")
    gorulen = set()
    sonuc = []

    for iz in izler:
        if not isinstance(iz, dict) or set(iz) != {"iz_id", "adimlar"}:
            raise ValueError("iz şeması geçersiz")
        iid = iz["iz_id"]
        adimlar = iz["adimlar"]
        if not isinstance(iid, str) or not iid or iid in gorulen:
            raise ValueError("iz_id geçersiz")
        if not isinstance(adimlar, list) or not 1 <= len(adimlar) <= 30:
            raise ValueError("adimlar geçersiz")
        gorulen.add(iid)

        cagrilan = set()
        ilk_tekrar_indeksi = None
        for idx, adim in enumerate(adimlar):
            if not isinstance(adim, dict) or set(adim) != {"arac", "arg_ozeti", "giris_token", "cikis_token"}:
                raise ValueError("adım şeması geçersiz")
            arac = adim["arac"]
            arg = adim["arg_ozeti"]
            gt = adim["giris_token"]
            ct = adim["cikis_token"]
            if not isinstance(arac, str) or not arac or not isinstance(arg, str) or not arg:
                raise ValueError("arac ve arg_ozeti geçersiz")
            if isinstance(gt, bool) or not isinstance(gt, int) or gt < 1:
                raise ValueError("giris_token geçersiz")
            if isinstance(ct, bool) or not isinstance(ct, int) or ct < 1:
                raise ValueError("cikis_token geçersiz")
            anahtar = (arac, arg)
            if anahtar in cagrilan and ilk_tekrar_indeksi is None:
                ilk_tekrar_indeksi = idx
            cagrilan.add(anahtar)

        tekrar = ilk_tekrar_indeksi is not None
        sinir = len(adimlar) >= tur_siniri
        israf = sum(a["giris_token"] + a["cikis_token"] for a in adimlar[ilk_tekrar_indeksi:]) if tekrar else 0
        if tekrar and sinir:
            durum = "sonsuz-dongu-tuketimi"
        elif tekrar:
            durum = "tekrarli-arac-israfi"
        elif sinir:
            durum = "uzun-zincir"
        else:
            durum = "normal"

        sonuc.append({
            "iz_id": iid,
            "tekrar_dongusu": tekrar,
            "sinir_asimi": sinir,
            "israf_token": israf,
            "durum": durum,
        })
    return sonuc
```

```hint
`(arac, arg_ozeti)` çiftlerini bir kümede izle; kümede zaten bulunan ilk çiftin indeksini `ilk_tekrar_indeksi` olarak kaydet ve `adimlar[ilk_tekrar_indeksi:]` dilimindeki `giris_token + cikis_token` toplamını `israf_token` yap.
```
:::

::: gorev Gerçek deney · Yerel modelde sponge üretimi ve maliyet çarpanı ölçümü
Önceki üç görevdeki `uretim_sisirme_analizi`, `baglam_doldurma_carpani` ve `ajan_dongusu_tuketimi` işlevlerini burada birleştir.

Canlı deneyde `ai_lab.SohbetOturumu` ile yerel Ollama modeline aynı `num_predict=140` tavanı altında iki gerçek istek gönderilir:
1. **`canli-normal`:** Tek cümlelik yanıt isteyen normal sorgu (erken `stop` ile düşük token ve düşük süre).
2. **`canli-sponge`:** Modeli 1'den 250'ye kadar okunuş ve kareleriyle satır satır yazmaya zorlayan sponge istemi (tavana kadar üretim, yüksek `eval_count` ve yüksek süre).

Üretilen gerçek token ve süre ölçümleri senin `uretim_sisirme_analizi` işlevine verilerek sponge çarpanı doğrulanır ve kanıta yazılır.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab
from ai_saldiri_veri import json_yukle

def uretim_sisirme_analizi(adaylar):
    return {"kayitlar": [], "sponge_idleri": [], "en_pahali_id": ""}

def baglam_doldurma_carpani(oturumlar):
    return []

def ajan_dongusu_tuketimi(izler, tur_siniri):
    return []

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_40 as deney
    deney.goster(uretim_sisirme_analizi, baglam_doldurma_carpani, ajan_dongusu_tuketimi)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-40")
```

```test
import ai_lab
import copy
from sandbox import ai_gercek_ai_saldiri_40 as D

checks = []
_base_ok = ok
def ok(kosul, mesaj):
    checks.append(bool(kosul))
    return _base_ok(kosul, mesaj)

for ad in ("uretim_sisirme_analizi", "baglam_doldurma_carpani", "ajan_dongusu_tuketimi"):
    need(ad)

sorun = ai_lab.kod_denetimi(src, ("uretim_sisirme_referans", "baglam_doldurma_referans", "ajan_dongusu_referans"))
ok(not sorun, "laboratuvar yamalanmamalı, referans işlevler çağrılmamalı")

ORNEK_ADAYLAR = [
    {"istek_id": "r1", "tur": "normal", "giris_token": 10, "cikis_token": 90, "sure_ms": 500, "bitis_nedeni": "stop"},
    {"istek_id": "r2", "tur": "sayma-sponge", "giris_token": 25, "cikis_token": 200, "sure_ms": 1800, "bitis_nedeni": "stop"},
    {"istek_id": "r3", "tur": "agac-genisletme", "giris_token": 40, "cikis_token": 120, "sure_ms": 1100, "bitis_nedeni": "length"},
    {"istek_id": "r4", "tur": "cok-dilli-tekrar", "giris_token": 30, "cikis_token": 239, "sure_ms": 1900, "bitis_nedeni": "stop"},
]
ORNEK_OTURUMLAR = [
    {"oturum_id": "o1", "sistem_token": 100, "rag_parcalari": [500, 1499], "tur_sayisi": 5, "tur_basi_cikis": 40},
    {"oturum_id": "o2", "sistem_token": 100, "rag_parcalari": [1000, 1000], "tur_sayisi": 2, "tur_basi_cikis": 50},
    {"oturum_id": "o3", "sistem_token": 100, "rag_parcalari": [200], "tur_sayisi": 6, "tur_basi_cikis": 30},
]
ORNEK_IZLER = [
    {
        "iz_id": "i1",
        "adimlar": [
            {"arac": "ara", "arg_ozeti": "q=1", "giris_token": 100, "cikis_token": 20},
            {"arac": "oku", "arg_ozeti": "id=2", "giris_token": 150, "cikis_token": 30},
        ],
    },
    {
        "iz_id": "i2",
        "adimlar": [
            {"arac": "ara", "arg_ozeti": "q=1", "giris_token": 100, "cikis_token": 20},
            {"arac": "oku", "arg_ozeti": "id=loop", "giris_token": 200, "cikis_token": 40},
            {"arac": "oku", "arg_ozeti": "id=loop", "giris_token": 300, "cikis_token": 40},
            {"arac": "oku", "arg_ozeti": "id=loop", "giris_token": 400, "cikis_token": 40},
        ],
    },
    {
        "iz_id": "i3",
        "adimlar": [
            {"arac": "ara", "arg_ozeti": "q=1", "giris_token": 100, "cikis_token": 20},
            {"arac": "ara", "arg_ozeti": "q=1", "giris_token": 150, "cikis_token": 25},
            {"arac": "yaz", "arg_ozeti": "ad=son", "giris_token": 180, "cikis_token": 30},
        ],
    },
    {
        "iz_id": "i4",
        "adimlar": [
            {"arac": "a1", "arg_ozeti": "x=1", "giris_token": 50, "cikis_token": 10},
            {"arac": "a2", "arg_ozeti": "x=2", "giris_token": 60, "cikis_token": 10},
            {"arac": "a3", "arg_ozeti": "x=3", "giris_token": 70, "cikis_token": 10},
            {"arac": "a4", "arg_ozeti": "x=4", "giris_token": 80, "cikis_token": 10},
        ],
    },
]

def _sinir_ve_sema_kontrol():
    try:
        esit = [
            {"istek_id": "b", "tur": "normal", "giris_token": 10, "cikis_token": 10, "sure_ms": 10, "bitis_nedeni": "stop"},
            {"istek_id": "a", "tur": "normal", "giris_token": 10, "cikis_token": 10, "sure_ms": 10, "bitis_nedeni": "stop"},
        ]
        yirmi_a = [{"istek_id": f"k{i:02d}", "tur": "normal", "giris_token": 1, "cikis_token": 1, "sure_ms": 1, "bitis_nedeni": "stop"} for i in range(20)]
        if (
            uretim_sisirme_analizi(copy.deepcopy(ORNEK_ADAYLAR)) != D.uretim_sisirme_referans(ORNEK_ADAYLAR)
            or uretim_sisirme_analizi(esit)["en_pahali_id"] != "a"
            or len(uretim_sisirme_analizi(yirmi_a)["kayitlar"]) != 20
            or len(uretim_sisirme_analizi([yirmi_a[0]])["kayitlar"]) != 1
        ):
            return False
        for ba in [
            None, [], "adaylar", [None], [{}],
            [{"istek_id": f"k{i}", "tur": "normal", "giris_token": 1, "cikis_token": 1, "sure_ms": 1, "bitis_nedeni": "stop"} for i in range(21)],
            [{"istek_id": "", "tur": "normal", "giris_token": 1, "cikis_token": 1, "sure_ms": 1, "bitis_nedeni": "stop"}],
            [{"istek_id": 1, "tur": "normal", "giris_token": 1, "cikis_token": 1, "sure_ms": 1, "bitis_nedeni": "stop"}],
            [{"istek_id": "a", "tur": "normal", "giris_token": 1, "cikis_token": 1, "sure_ms": 1, "bitis_nedeni": "stop"},
             {"istek_id": "a", "tur": "normal", "giris_token": 1, "cikis_token": 1, "sure_ms": 1, "bitis_nedeni": "stop"}],
            [{"istek_id": "a", "tur": "bilinmeyen", "giris_token": 1, "cikis_token": 1, "sure_ms": 1, "bitis_nedeni": "stop"}],
            [{"istek_id": "a", "tur": "normal", "giris_token": 0, "cikis_token": 1, "sure_ms": 1, "bitis_nedeni": "stop"}],
            [{"istek_id": "a", "tur": "normal", "giris_token": True, "cikis_token": 1, "sure_ms": 1, "bitis_nedeni": "stop"}],
            [{"istek_id": "a", "tur": "normal", "giris_token": 1.5, "cikis_token": 1, "sure_ms": 1, "bitis_nedeni": "stop"}],
            [{"istek_id": "a", "tur": "normal", "giris_token": 1, "cikis_token": 0, "sure_ms": 1, "bitis_nedeni": "stop"}],
            [{"istek_id": "a", "tur": "normal", "giris_token": 1, "cikis_token": True, "sure_ms": 1, "bitis_nedeni": "stop"}],
            [{"istek_id": "a", "tur": "normal", "giris_token": 1, "cikis_token": 1.5, "sure_ms": 1, "bitis_nedeni": "stop"}],
            [{"istek_id": "a", "tur": "normal", "giris_token": 1, "cikis_token": 1, "sure_ms": 0, "bitis_nedeni": "stop"}],
            [{"istek_id": "a", "tur": "normal", "giris_token": 1, "cikis_token": 1, "sure_ms": True, "bitis_nedeni": "stop"}],
            [{"istek_id": "a", "tur": "normal", "giris_token": 1, "cikis_token": 1, "sure_ms": 1.5, "bitis_nedeni": "stop"}],
            [{"istek_id": "a", "tur": "normal", "giris_token": 1, "cikis_token": 1, "sure_ms": 1, "bitis_nedeni": "iptal"}],
            [{"istek_id": "a", "tur": "normal", "giris_token": 1, "cikis_token": 1, "sure_ms": 1, "bitis_nedeni": "stop", "ek": 1}],
        ]:
            try:
                uretim_sisirme_analizi(ba)
                return False
            except ValueError:
                pass

        yirmi_o = [{"oturum_id": f"x{i}", "sistem_token": 1, "rag_parcalari": [1] * 20, "tur_sayisi": 20, "tur_basi_cikis": 1} for i in range(20)]
        tek_o = [{"oturum_id": "tek", "sistem_token": 1, "rag_parcalari": [1], "tur_sayisi": 1, "tur_basi_cikis": 1}]
        if (
            baglam_doldurma_carpani(copy.deepcopy(ORNEK_OTURUMLAR)) != D.baglam_doldurma_referans(ORNEK_OTURUMLAR)
            or len(baglam_doldurma_carpani(yirmi_o)) != 20
            or len(baglam_doldurma_carpani(tek_o)) != 1
        ):
            return False
        for bo in [
            None, [], "oturum", [None], [{}],
            [{"oturum_id": f"x{i}", "sistem_token": 1, "rag_parcalari": [1], "tur_sayisi": 1, "tur_basi_cikis": 1} for i in range(21)],
            [{"oturum_id": "", "sistem_token": 1, "rag_parcalari": [1], "tur_sayisi": 1, "tur_basi_cikis": 1}],
            [{"oturum_id": 1, "sistem_token": 1, "rag_parcalari": [1], "tur_sayisi": 1, "tur_basi_cikis": 1}],
            [{"oturum_id": "a", "sistem_token": 1, "rag_parcalari": [1], "tur_sayisi": 1, "tur_basi_cikis": 1},
             {"oturum_id": "a", "sistem_token": 1, "rag_parcalari": [1], "tur_sayisi": 1, "tur_basi_cikis": 1}],
            [{"oturum_id": "a", "sistem_token": 0, "rag_parcalari": [1], "tur_sayisi": 1, "tur_basi_cikis": 1}],
            [{"oturum_id": "a", "sistem_token": True, "rag_parcalari": [1], "tur_sayisi": 1, "tur_basi_cikis": 1}],
            [{"oturum_id": "a", "sistem_token": 1.5, "rag_parcalari": [1], "tur_sayisi": 1, "tur_basi_cikis": 1}],
            [{"oturum_id": "a", "sistem_token": 1, "rag_parcalari": [], "tur_sayisi": 1, "tur_basi_cikis": 1}],
            [{"oturum_id": "a", "sistem_token": 1, "rag_parcalari": (1,), "tur_sayisi": 1, "tur_basi_cikis": 1}],
            [{"oturum_id": "a", "sistem_token": 1, "rag_parcalari": [1] * 21, "tur_sayisi": 1, "tur_basi_cikis": 1}],
            [{"oturum_id": "a", "sistem_token": 1, "rag_parcalari": [0], "tur_sayisi": 1, "tur_basi_cikis": 1}],
            [{"oturum_id": "a", "sistem_token": 1, "rag_parcalari": [True], "tur_sayisi": 1, "tur_basi_cikis": 1}],
            [{"oturum_id": "a", "sistem_token": 1, "rag_parcalari": [1.5], "tur_sayisi": 1, "tur_basi_cikis": 1}],
            [{"oturum_id": "a", "sistem_token": 1, "rag_parcalari": "10", "tur_sayisi": 1, "tur_basi_cikis": 1}],
            [{"oturum_id": "a", "sistem_token": 1, "rag_parcalari": [1], "tur_sayisi": 0, "tur_basi_cikis": 1}],
            [{"oturum_id": "a", "sistem_token": 1, "rag_parcalari": [1], "tur_sayisi": 21, "tur_basi_cikis": 1}],
            [{"oturum_id": "a", "sistem_token": 1, "rag_parcalari": [1], "tur_sayisi": True, "tur_basi_cikis": 1}],
            [{"oturum_id": "a", "sistem_token": 1, "rag_parcalari": [1], "tur_sayisi": 1.5, "tur_basi_cikis": 1}],
            [{"oturum_id": "a", "sistem_token": 1, "rag_parcalari": [1], "tur_sayisi": 1, "tur_basi_cikis": 0}],
            [{"oturum_id": "a", "sistem_token": 1, "rag_parcalari": [1], "tur_sayisi": 1, "tur_basi_cikis": True}],
            [{"oturum_id": "a", "sistem_token": 1, "rag_parcalari": [1], "tur_sayisi": 1, "tur_basi_cikis": 1.5}],
            [{"oturum_id": "a", "sistem_token": 1, "rag_parcalari": [1], "tur_sayisi": 1, "tur_basi_cikis": 1, "ek": 1}],
        ]:
            try:
                baglam_doldurma_carpani(bo)
                return False
            except ValueError:
                pass

        otuz_adim = [{"iz_id": f"z{i}", "adimlar": [{"arac": f"a{j}", "arg_ozeti": "k", "giris_token": 1, "cikis_token": 1} for j in range(30)]} for i in range(20)]
        tek_iz = [{"iz_id": "t", "adimlar": [{"arac": "a", "arg_ozeti": "b", "giris_token": 1, "cikis_token": 1}]}]
        if (
            ajan_dongusu_tuketimi(copy.deepcopy(ORNEK_IZLER), 4) != D.ajan_dongusu_referans(ORNEK_IZLER, 4)
            or len(ajan_dongusu_tuketimi(otuz_adim, 20)) != 20
            or ajan_dongusu_tuketimi(tek_iz, 2)[0]["sinir_asimi"] is not False
        ):
            return False
        for b_iz, b_sinir in [
            (None, 4), ([], 4), ("iz", 4), ([None], 4), ([{}], 4),
            (ORNEK_IZLER, 1), (ORNEK_IZLER, 21), (ORNEK_IZLER, True), (ORNEK_IZLER, "4"),
            ([{"iz_id": f"z{i}", "adimlar": [{"arac": "a", "arg_ozeti": "b", "giris_token": 1, "cikis_token": 1}]} for i in range(21)], 4),
            ([{"iz_id": "", "adimlar": [{"arac": "a", "arg_ozeti": "b", "giris_token": 1, "cikis_token": 1}]}], 4),
            ([{"iz_id": 1, "adimlar": [{"arac": "a", "arg_ozeti": "b", "giris_token": 1, "cikis_token": 1}]}], 4),
            ([{"iz_id": "a", "adimlar": [{"arac": "a", "arg_ozeti": "b", "giris_token": 1, "cikis_token": 1}]},
              {"iz_id": "a", "adimlar": [{"arac": "a", "arg_ozeti": "b", "giris_token": 1, "cikis_token": 1}]}], 4),
            ([{"iz_id": "a", "adimlar": []}], 4),
            ([{"iz_id": "a", "adimlar": [{"arac": "a", "arg_ozeti": "b", "giris_token": 1, "cikis_token": 1}] * 31}], 4),
            ([{"iz_id": "a", "adimlar": "adim"}], 4),
            ([{"iz_id": "a", "adimlar": ({"arac": "a", "arg_ozeti": "b", "giris_token": 1, "cikis_token": 1},)}], 4),
            ([{"iz_id": "a", "adimlar": [["arac", "arg_ozeti", "giris_token", "cikis_token"]]}], 4),
            ([{"iz_id": "a", "adimlar": [{}]}], 4),
            ([{"iz_id": "a", "adimlar": [{"arac": "", "arg_ozeti": "b", "giris_token": 1, "cikis_token": 1}]}], 4),
            ([{"iz_id": "a", "adimlar": [{"arac": 1, "arg_ozeti": "b", "giris_token": 1, "cikis_token": 1}]}], 4),
            ([{"iz_id": "a", "adimlar": [{"arac": "a", "arg_ozeti": "", "giris_token": 1, "cikis_token": 1}]}], 4),
            ([{"iz_id": "a", "adimlar": [{"arac": "a", "arg_ozeti": 1, "giris_token": 1, "cikis_token": 1}]}], 4),
            ([{"iz_id": "a", "adimlar": [{"arac": "a", "arg_ozeti": "b", "giris_token": 0, "cikis_token": 1}]}], 4),
            ([{"iz_id": "a", "adimlar": [{"arac": "a", "arg_ozeti": "b", "giris_token": True, "cikis_token": 1}]}], 4),
            ([{"iz_id": "a", "adimlar": [{"arac": "a", "arg_ozeti": "b", "giris_token": 1.5, "cikis_token": 1}]}], 4),
            ([{"iz_id": "a", "adimlar": [{"arac": "a", "arg_ozeti": "b", "giris_token": 1, "cikis_token": 0}]}], 4),
            ([{"iz_id": "a", "adimlar": [{"arac": "a", "arg_ozeti": "b", "giris_token": 1, "cikis_token": True}]}], 4),
            ([{"iz_id": "a", "adimlar": [{"arac": "a", "arg_ozeti": "b", "giris_token": 1, "cikis_token": 1.5}]}], 4),
            ([{"iz_id": "a", "adimlar": [{"arac": "a", "arg_ozeti": "b", "giris_token": 1, "cikis_token": 1}], "ek": 1}], 4),
        ]:
            try:
                ajan_dongusu_tuketimi(b_iz, b_sinir)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(_sinir_ve_sema_kontrol(), "üretim şişirme, bağlam doldurma ve ajan döngüsü işlevleri tüm sınır ve şema kurallarını geçti")

if not all(checks):
    stop()

try:
    r = D.deney(uretim_sisirme_analizi, baglam_doldurma_carpani, ajan_dongusu_tuketimi)
except Exception as e:
    ok(False, f"GERÇEK DENIAL-OF-WALLET DENEYİ YAPILAMADI: {type(e).__name__}: {e}")
    stop()

for ad, deger in r["kontroller"].items():
    ok(deger, "gerçek deney: " + ad)

ai_lab.kanit_yaz("saldiri-40-denial-of-wallet", {
    "kaynak": "gercek",
    "kabul": all(checks),
    "ders": "ai-saldiri-40",
    "ortam": r["ortam"],
    "ayarlar": r["ayarlar"],
    "deney": r,
    "ozet": r["ozet"],
})
o = r["ozet"]
ok(
    True,
    f"BULGU ({r['ortam']['model']['ad']}): normal={o['normal_token']} token ({o['normal_sure_ms']} ms), "
    f"sponge={o['sponge_token']} token ({o['sponge_sure_ms']} ms), çarpan={o['sponge_carpani']}x.",
)
```

```solution
import ai_lab

def uretim_sisirme_analizi(adaylar):
    turler = ("normal", "sayma-sponge", "agac-genisletme", "cok-dilli-tekrar")
    nedenler = ("stop", "length")
    if not isinstance(adaylar, list) or not 1 <= len(adaylar) <= 20:
        raise ValueError("adaylar geçersiz")
    gorulen = set()
    kayitlar = []
    sponge_idleri = []

    for a in adaylar:
        if not isinstance(a, dict) or set(a) != {"istek_id", "tur", "giris_token", "cikis_token", "sure_ms", "bitis_nedeni"}:
            raise ValueError("aday şeması geçersiz")
        iid = a["istek_id"]
        tur = a["tur"]
        giris = a["giris_token"]
        cikis = a["cikis_token"]
        sure = a["sure_ms"]
        neden = a["bitis_nedeni"]
        if not isinstance(iid, str) or not iid or iid in gorulen:
            raise ValueError("istek_id geçersiz")
        if tur not in turler:
            raise ValueError("tur geçersiz")
        if isinstance(giris, bool) or not isinstance(giris, int) or giris < 1:
            raise ValueError("giris_token geçersiz")
        if isinstance(cikis, bool) or not isinstance(cikis, int) or cikis < 1:
            raise ValueError("cikis_token geçersiz")
        if isinstance(sure, bool) or not isinstance(sure, int) or sure < 1:
            raise ValueError("sure_ms geçersiz")
        if neden not in nedenler:
            raise ValueError("bitis_nedeni geçersiz")
        gorulen.add(iid)

        oran = round(cikis / giris, 2)
        tavan = neden == "length"
        agirlikli = giris + 3 * cikis
        if tur != "normal" and (oran >= 8.0 or tavan):
            sponge_idleri.append(iid)

        kayitlar.append({
            "istek_id": iid,
            "genisleme_orani": oran,
            "agirlikli_token": agirlikli,
            "tavan_vuruldu": tavan,
        })

    en_pahali_id = min(kayitlar, key=lambda r: (-r["agirlikli_token"], r["istek_id"]))["istek_id"]
    return {
        "kayitlar": kayitlar,
        "sponge_idleri": sorted(sponge_idleri),
        "en_pahali_id": en_pahali_id,
    }

def baglam_doldurma_carpani(oturumlar):
    if not isinstance(oturumlar, list) or not 1 <= len(oturumlar) <= 20:
        raise ValueError("oturumlar geçersiz")
    gorulen = set()
    sonuc = []

    for o in oturumlar:
        if not isinstance(o, dict) or set(o) != {"oturum_id", "sistem_token", "rag_parcalari", "tur_sayisi", "tur_basi_cikis"}:
            raise ValueError("oturum şeması geçersiz")
        oid = o["oturum_id"]
        sistem = o["sistem_token"]
        rag = o["rag_parcalari"]
        turlar = o["tur_sayisi"]
        cikis_basi = o["tur_basi_cikis"]
        if not isinstance(oid, str) or not oid or oid in gorulen:
            raise ValueError("oturum_id geçersiz")
        if isinstance(sistem, bool) or not isinstance(sistem, int) or sistem < 1:
            raise ValueError("sistem_token geçersiz")
        if not isinstance(rag, list) or not 1 <= len(rag) <= 20:
            raise ValueError("rag_parcalari geçersiz")
        for p in rag:
            if isinstance(p, bool) or not isinstance(p, int) or p < 1:
                raise ValueError("rag parçası geçersiz")
        if isinstance(turlar, bool) or not isinstance(turlar, int) or not 1 <= turlar <= 20:
            raise ValueError("tur_sayisi geçersiz")
        if isinstance(cikis_basi, bool) or not isinstance(cikis_basi, int) or cikis_basi < 1:
            raise ValueError("tur_basi_cikis geçersiz")
        gorulen.add(oid)

        rag_toplam = sum(rag)
        taban = sistem + rag_toplam
        toplam_giris = sum(taban + t * cikis_basi for t in range(turlar))
        toplam_cikis = turlar * cikis_basi
        agirlikli = toplam_giris + 3 * toplam_cikis
        sisirme = rag_toplam >= 2000 or turlar >= 6

        sonuc.append({
            "oturum_id": oid,
            "toplam_giris": toplam_giris,
            "toplam_cikis": toplam_cikis,
            "agirlikli_maliyet": agirlikli,
            "sisirme_var": sisirme,
        })
    return sonuc

def ajan_dongusu_tuketimi(izler, tur_siniri):
    if isinstance(tur_siniri, bool) or not isinstance(tur_siniri, int) or not 2 <= tur_siniri <= 20:
        raise ValueError("tur_siniri geçersiz")
    if not isinstance(izler, list) or not 1 <= len(izler) <= 20:
        raise ValueError("izler geçersiz")
    gorulen = set()
    sonuc = []

    for iz in izler:
        if not isinstance(iz, dict) or set(iz) != {"iz_id", "adimlar"}:
            raise ValueError("iz şeması geçersiz")
        iid = iz["iz_id"]
        adimlar = iz["adimlar"]
        if not isinstance(iid, str) or not iid or iid in gorulen:
            raise ValueError("iz_id geçersiz")
        if not isinstance(adimlar, list) or not 1 <= len(adimlar) <= 30:
            raise ValueError("adimlar geçersiz")
        gorulen.add(iid)

        cagrilan = set()
        ilk_tekrar_indeksi = None
        for idx, adim in enumerate(adimlar):
            if not isinstance(adim, dict) or set(adim) != {"arac", "arg_ozeti", "giris_token", "cikis_token"}:
                raise ValueError("adım şeması geçersiz")
            arac = adim["arac"]
            arg = adim["arg_ozeti"]
            gt = adim["giris_token"]
            ct = adim["cikis_token"]
            if not isinstance(arac, str) or not arac or not isinstance(arg, str) or not arg:
                raise ValueError("arac ve arg_ozeti geçersiz")
            if isinstance(gt, bool) or not isinstance(gt, int) or gt < 1:
                raise ValueError("giris_token geçersiz")
            if isinstance(ct, bool) or not isinstance(ct, int) or ct < 1:
                raise ValueError("cikis_token geçersiz")
            anahtar = (arac, arg)
            if anahtar in cagrilan and ilk_tekrar_indeksi is None:
                ilk_tekrar_indeksi = idx
            cagrilan.add(anahtar)

        tekrar = ilk_tekrar_indeksi is not None
        sinir = len(adimlar) >= tur_siniri
        israf = sum(a["giris_token"] + a["cikis_token"] for a in adimlar[ilk_tekrar_indeksi:]) if tekrar else 0
        if tekrar and sinir:
            durum = "sonsuz-dongu-tuketimi"
        elif tekrar:
            durum = "tekrarli-arac-israfi"
        elif sinir:
            durum = "uzun-zincir"
        else:
            durum = "normal"

        sonuc.append({
            "iz_id": iid,
            "tekrar_dongusu": tekrar,
            "sinir_asimi": sinir,
            "israf_token": israf,
            "durum": durum,
        })
    return sonuc

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_40 as deney
    deney.goster(uretim_sisirme_analizi, baglam_doldurma_carpani, ajan_dongusu_tuketimi)
```

```hint
Önceki üç görevdeki çözümlerini birleştir; canlı deneyde normal sorgu ile sponge sorgusunun gerçek token ve süre farkı ölçülür.
```
:::


::: anlat Bunu iki dakikada nasıl anlatırsın?
Denial-of-Wallet için toplam giriş tokenını T·taban + çıktı·T(T−1)/2 olarak türet. Aynı tur başına çıktı varsayımı altında T tur geçmişin neden karesel biriktiğini göster. Sonra sponge çıktısının tek çağrıda büyümesiyle ajan döngüsünün çok çağrı üretmesini ayır. Yerel token sayacının sağlayıcı faturası olmadığını ve 3 ağırlığının dersin muhasebe seçimi olduğunu belirt.

Önkoşul ve yol köprüsü: ai-savunma-31 bütçenin model dışındaki zorlayıcı sınırını kurar.

| Yaygın yanlış | Mekanizma ve sınır |
|---|---|
| Daha uzun süre her zaman daha pahalıdır | Token sayısı, prefill/decode ve donanım ayrı ölçülür |

Dinleyiciye sor: Bu dersin kanıtı hangi gözlemi gösterir; hangi daha güçlü iddia için ek deney gerekir? Kanıtın model, ayar, veri kökeni ve hata alanlarını açarak cevabını gerekçelendir.
:::


::: anlat Birincil kaynak ve sürüm
Bu dersteki `LLM10` eşlemesi [OWASP LLM10:2025 Unbounded Consumption](https://genai.owasp.org/llmrisk/llm102025-unbounded-consumption/) sayfasına bağlıdır; güncel bütün OWASP sürümlerini kapsadığı iddia edilmez. Kaynak, kontrolsüz inference yüküyle maliyet ve hizmet kullanılabilirliği riskini ilişkilendirir. Dersin 3 katsayısı, 8.0 genişleme eşiği ve tur sınırları eğitim sözleşmesidir; OWASP tarafından belirlenmiş eşikler değildir.
:::
