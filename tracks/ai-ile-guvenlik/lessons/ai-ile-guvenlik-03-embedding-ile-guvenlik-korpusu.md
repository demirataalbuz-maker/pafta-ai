---
id: ai-ile-guvenlik-03
title: "Embedding ile Güvenlik Korpusu ve Benzer Zafiyet Arama"
summary: Güvenlik zafiyeti kayıtlarını ve yama özetlerini embedding vektörleriyle indeksle, kosinüs benzerliğiyle en yakın vakaları getir ve eşik kalibrasyonuyla yanlış eşleşmeleri ölç.
esleme: ai-temel-16, ai-guvence-31
timeout: 300
---

::: anlat Gerçek biçimi bil, sentetik temsili ayırt et
Güvenlik ekipleri her yeni olayda sıfırdan araştırma yapmaz: geçmiş zafiyet raporları, CVE özetleri ve yama notları bir **güvenlik korpusu** içinde tutulur. Kelime tabanlı arama (`grep`) `"SQL SELECT birleştirme"` ile `"veritabanı sorgusunda filtresiz parametre"` arasındaki anlamsal yakınlığı kaçırabilir. `ai-temel-16` ve `ai-guvence-31` derslerinde gördüğümüz gömme (embedding) modelleri (`all-minilm:22m`) metinleri sabit boyutlu vektörlere dönüştürerek kosinüs benzerliğiyle benzer zafiyetleri bulmamızı sağlar.

| Gerçek araç / model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Yerel Ollama embedding modelinin (`all-minilm:22m`, 384 boyut) zafiyet açıklamalarından ürettiği gerçek vektörleri ve kosinüs benzerliği sıralamasını | İlk üç görevde `zafiyet_korpusu.json` ve `sorgu_vektorleri.json` içindeki 4-boyutlu **sentetik** vektörleri; son görevde gerçek `all-minilm:22m` gömmeleriyle benzer zafiyet arama deneyini | Yüksek kosinüs benzerliğine sahip iki zafiyet kaydının her zaman aynı kök yamayla (`yama_ozeti`) çözülebileceğini söyleyemez |

> [!GÜVENLİK]
> **Kapsam ve dürüstlük sınırı:** İlk üç görevdeki örnek dosyalar **sentetik** eğitim verisidir ve her çalıştırmada (`setup`) çalışma klasörüne yeniden kopyalanır (kalıcılık yoktur). Gömme benzerliği yalnızca aday yama önerisi getirir; yamanın uygunluğu mühendis ve testler tarafından doğrulanır.
:::

::: anlat Uzunluk yanlılığını önlemek için iç çarpım değil kosinüs benzerliği kullanılır
Güvenlik korpusunda benzerlik araması üç kurala dayanır:

1. **Birim Uzunluk Normalizasyonu (`kosinus_benzerligi`):** İki vektörün yalnız iç çarpımını (`dot product`) almak uzun vektörleri yapay olarak öne çıkarır. Kosinüs benzerliği $\frac{v_1 \cdot v_2}{\|v_1\| \|v_2\|}$ formülüyle yön yakınlığını ölçer. Sıfır vektör ($\|v\| = 0$) tanımsız bölme üreteceği için baştan reddedilir.
2. **Eşikli Getirme (`benzer_zafiyet_ara`):** Her sorguda mutlaka `k` sonuç döndürmek, korpusta hiç karşılığı olmayan yeni bir zafiyet türünde alakasız kayıtların getirilmesine yol açar. Yalnızca `benzerlik >= esik` koşulunu sağlayan adaylar döndürülür.
3. **Eşik Kalibrasyonu (`esik_kalibrasyonu_olc`):** Eşik çok düşük seçilirse `"yanlis_eslesme"` (farklı kategorideki zafiyetle eşleşme) artar; çok yüksek seçilirse bilinen zafiyetler `"cevapsiz"` kalır. Bilinmeyen (`"bilinmeyen"`) kategorideki bir sorgu için eşik altında kalıp boş sonuç döndürmek ise **doğru eşleşme** (doğru reddetme) sayılır.
:::

::: anlat Bulguyu sınırlı ve doğrulanabilir yaz: gömme yakınlığını kesin tanı sanma
Gömme tabanlı güvenlik arama sonuçları kullanılırken iki sınır korunmalıdır:

- **Eşik altı sessizlik:** En yakın komşunun benzerliği `esik` değerinin altındaysa sistem `"benzer kayıt bulunamadı"` demelidir; en yüksek skorlu alakasız kaydı zorla önermemelidir.
- **Kategori doğrulaması:** Kalibrasyon ölçümünde hem bilinen kategorilerin doğru yakalanması hem de korpusta bulunmayan (`"bilinmeyen"`) vakaların yanlış kategoriye atanmaması birlikte raporlanmalıdır.
:::

::: tahmin İç çarpım ile kosinüs benzerliği arasındaki sıralama farkını tahmin et
Aşağıdaki Python kodunun çıktısını tahmin et:

```python
import math

sorgu = [1.0, 0.0]
aday_a = [0.9, 0.0]      # aynı yön, kısa vektör
aday_b = [2.0, 2.0]      # 45 derece sapmış ama uzun vektör

ic_carpim_en_iyi = "A" if sum(x * y for x, y in zip(sorgu, aday_a)) > sum(x * y for x, y in zip(sorgu, aday_b)) else "B"
kos_a = sum(x * y for x, y in zip(sorgu, aday_a)) / math.sqrt(sum(x * x for x in aday_a))
kos_b = sum(x * y for x, y in zip(sorgu, aday_b)) / math.sqrt(sum(x * x for x in aday_b))
kosinus_en_iyi = "A" if kos_a > kos_b else "B"
print(ic_carpim_en_iyi, kosinus_en_iyi)
```

???

```cikti
B A
```

Normalizasyon yapılmadığında iç çarpım uzunluğu büyük olan `aday_b` vektörünü (`2.0 > 0.9`) seçer (`B`). Kosinüs benzerliği ise vektör boyunu normalize ederek sorguyla bire bir aynı yönde olan `aday_a` vektörünü (`1.0 > 0.7071`) doğru şekilde öne çıkarır (`A`).
:::

::: gorev 1 · İki embedding vektörü arasındaki kosinüs benzerliğini hesapla
`kosinus_benzerligi(v1, v2)` işlevini yaz.

Girdi kuralları:
- `v1` ve `v2`: boş olmayan ve eşit uzunlukta `list`.
- Her eleman `bool` olmayan `int` veya `float` olmalıdır.
- Sıfır vektör (tüm elemanlarının kareleri toplamı `0` olan vektör) kabul edilmez.
- Geçersiz girdi, boyut uyuşmazlığı veya sıfır vektörde `ValueError` yükselt.

Hesaplama kuralları:
- Kosinüs benzerliğini $\frac{\sum v_{1,i} v_{2,i}}{\sqrt{\sum v_{1,i}^2}\sqrt{\sum v_{2,i}^2}}$ formülüyle hesapla ve `round(..., 4)` ile döndür.

```starter
from ai_ile_guvenlik_veri import json_yukle

korpus = json_yukle("zafiyet_korpusu.json")["kayitlar"]

def kosinus_benzerligi(v1, v2):
    # HATA: Vektör boylarını normalize etmeden yalnız iç çarpım alıyor.
    return round(sum(a * b for a, b in zip(v1, v2)), 4)

print(kosinus_benzerligi(korpus[0]["vektor"], korpus[1]["vektor"]))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-03")
```

```test
need("kosinus_benzerligi")

def sozlesme(fn):
    try:
        if fn([3.0, 0.0], [6.0, 0.0]) != 1.0:
            return False
        if fn([1.0, 0.0], [0.0, 5.0]) != 0.0:
            return False
        if fn([1.0, 2.0, 3.0], [2.0, 1.0, 0.0]) != 0.4781:
            return False
        if fn([1.0, -1.0], [-1.0, 1.0]) != -1.0:
            return False

        hatalilar = [
            (None, [1.0]),
            ([1.0], None),
            ([], [1.0]),
            ([1.0], []),
            ("liste", [1.0]),
            ([1.0], "liste"),
            ([1.0, 2.0], [1.0]),
            ([True, 1.0], [1.0, 1.0]),
            ([1.0, 1.0], [False, 1.0]),
            (["1.0"], [1.0]),
            ([0.0, 0.0], [1.0, 1.0]),
            ([1.0, 1.0], [0, 0]),
            ([float("nan"), 1.0], [1.0, 1.0]),
            ([1.0, 1.0], [float("inf"), 1.0]),
            ([float("-inf"), 1.0], [1.0, 1.0]),
        ]
        for a_in, b_in in hatalilar:
            try:
                fn(a_in, b_in)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(kosinus_benzerligi), "kosinüs benzerliği birim normalizasyonla ve sıfır vektör kontrolüyle hesaplanmalı")
def m_ic_carpim(a, b):
    return round(sum(x * y for x, y in zip(a, b)), 4)
def m_yuvarlamasiz(a, b):
    return round(kosinus_benzerligi(a, b), 2)
for ad, mutant in [("normalizasyon yapmayan", m_ic_carpim), ("yuvarlama basamağını bozan", m_yuvarlamasiz)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
import math

def _vektor_boyu(v):
    if not isinstance(v, list):
        raise ValueError("vektör liste olmalı")
    toplam = 0.0
    for x in v:
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
            raise ValueError("vektör elemanları sayısal olmalı")
        toplam += float(x) * float(x)
    if toplam <= 0.0:
        raise ValueError("boş veya sıfır vektör kullanılamaz")
    return math.sqrt(toplam)

def kosinus_benzerligi(v1, v2):
    b1 = _vektor_boyu(v1)
    b2 = _vektor_boyu(v2)
    if len(v1) != len(v2):
        raise ValueError("vektör boyutları eşit olmalı")
    carpim = sum(float(a) * float(b) for a, b in zip(v1, v2))
    return round(carpim / (b1 * b2), 4)
```

```hint
Her iki vektörün Öklid boyunu (`math.sqrt(sum(x*x for x in v))`) ayrı ayrı hesapla; boy `0.0` ise `ValueError` yükselt.
```
:::

::: gorev 2 · Güvenlik korpusunda eşikli benzer zafiyet araması yap
`benzer_zafiyet_ara(sorgu_vektoru, korpus, esik=0.75, en_cok=3)` işlevini yaz.

Girdi kuralları:
- `sorgu_vektoru`: 1. görevdeki geçerli vektör kurallarına uymalıdır.
- `korpus`: boş olmayan `list`; her öğesi tam olarak `{"kayit_id", "kategori", "vektor", "yama_ozeti"}` anahtarlarını taşımalıdır.
  - `kayit_id`: boş olmayan benzersiz `str`.
  - `kategori`, `yama_ozeti`: boş olmayan `str`.
  - `vektor`: `sorgu_vektoru` ile aynı boyutta geçerli vektör.
- `esik`: `bool` olmayan, `0.0` ile `1.0` (dahil) arasında `int` veya `float`.
- `en_cok`: `bool` olmayan pozitif (`1` veya daha büyük) `int`.
- Geçersiz girdi veya şemada `ValueError` yükselt.

Arama kuralları:
- Korpustaki her kayıt için `benzerlik = kosinus_benzerligi(sorgu_vektoru, kayit["vektor"])` hesapla.
- Yalnızca `benzerlik >= esik` olan kayıtları al.
- Sonuçları önce `benzerlik` değerine göre azalan (`-benzerlik`), eşitlikte `kayit_id` değerine göre artan sırada sırala ve ilk `en_cok` öğeyi döndür:
  `[{"kayit_id": str, "kategori": str, "benzerlik": float, "yama_ozeti": str}, ...]`

```starter
from ai_ile_guvenlik_veri import json_yukle

korpus = json_yukle("zafiyet_korpusu.json")["kayitlar"]
sorgular = json_yukle("sorgu_vektorleri.json")

def benzer_zafiyet_ara(sorgu_vektoru, korpus, esik=0.75, en_cok=3):
    # HATA: Eşik kontrolü ve benzerlik sıralaması yapmadan ilk kayıtları döndürüyor.
    return [
        {
            "kayit_id": k["kayit_id"],
            "kategori": k["kategori"],
            "benzerlik": 1.0,
            "yama_ozeti": k["yama_ozeti"],
        }
        for k in korpus[:en_cok]
    ]

print(benzer_zafiyet_ara(sorgular["sorgular"][0]["vektor"], korpus, sorgular["esik"]))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-03")
```

```test
need("benzer_zafiyet_ara")

KORPUS = [
    {"kayit_id": "Z-2", "kategori": "sql", "vektor": [1.0, 0.0, 0.0], "yama_ozeti": "Yama 2"},
    {"kayit_id": "Z-1", "kategori": "sql", "vektor": [2.0, 0.0, 0.0], "yama_ozeti": "Yama 1"},
    {"kayit_id": "Z-3", "kategori": "sql", "vektor": [0.8, 0.6, 0.0], "yama_ozeti": "Yama 3"},
    {"kayit_id": "Z-4", "kategori": "ssrf", "vektor": [0.0, 0.0, 1.0], "yama_ozeti": "Yama 4"},
]

def sozlesme(fn):
    try:
        r = fn([1.0, 0.0, 0.0], KORPUS)
        if r != [
            {"kayit_id": "Z-1", "kategori": "sql", "benzerlik": 1.0, "yama_ozeti": "Yama 1"},
            {"kayit_id": "Z-2", "kategori": "sql", "benzerlik": 1.0, "yama_ozeti": "Yama 2"},
            {"kayit_id": "Z-3", "kategori": "sql", "benzerlik": 0.8, "yama_ozeti": "Yama 3"},
        ]:
            return False

        if len(fn([1.0, 0.0, 0.0], KORPUS, 0.8, 1)) != 1:
            return False
        if fn([1.0, 0.0, 0.0], KORPUS, 0.85, 3) != r[:2]:
            return False
        if fn([0.0, 1.0, 0.0], KORPUS, 0.75, 3) != []:
            return False
        if len(fn([1.0, 0.0, 0.0], KORPUS, 0.0)) != 3:
            return False
        if len(fn([1.0, 0.0, 0.0], KORPUS, 0.0, 4)) != 4:
            return False
        if len(fn([1.0, 0.0, 0.0], KORPUS, 1.0, 3)) != 2:
            return False
        if fn([1.0, 2.0, 3.0], [{"kayit_id": "Z-X", "kategori": "sql", "vektor": [2.0, 1.0, 0.0], "yama_ozeti": "Y"}], 0.1, 1)[0]["benzerlik"] != 0.4781:
            return False
        kor_def = KORPUS + [{"kayit_id": "Z-5", "kategori": "sql", "vektor": [0.6, 0.8, 0.0], "yama_ozeti": "Yama 5"}]
        if len(fn([1.0, 0.0, 0.0], kor_def)) != 3 or len(fn([0.6, 0.8, 0.0], kor_def)) != 2:
            return False

        k0 = KORPUS[0]
        hatalilar = [
            (None, KORPUS, 0.5, 2),
            ((1.0, 0.0, 0.0), KORPUS, 0.5, 2),
            ([1.0, 0.0, 0.0], tuple(KORPUS), 0.5, 2),
            ("liste", KORPUS, 0.5, 2),
            ([], KORPUS, 0.5, 2),
            ([0.0, 0.0, 0.0], KORPUS, 0.5, 2),
            ([1.0, 0.0], KORPUS, 0.5, 2),
            ([True, 1.0, 0.0], KORPUS, 0.5, 2),
            (["1.0", 1.0, 0.0], KORPUS, 0.5, 2),
            ([1.0, 0.0, 0.0], [dict(k0, vektor="v")], 0.5, 2),
            ([1.0, 0.0, 0.0], [dict(k0, vektor=[])], 0.5, 2),
            ([1.0, 0.0, 0.0], [dict(k0, vektor=[True, 1.0, 0.0])], 0.5, 2),
            ([1.0, 0.0, 0.0], [dict(k0, vektor=["1", 1.0, 0.0])], 0.5, 2),
            ([1.0, 0.0, 0.0], None, 0.5, 2),
            ([1.0, 0.0, 0.0], [], 0.5, 2),
            ([1.0, 0.0, 0.0], ["bozuk"], 0.5, 2),
            ([1.0, 0.0, 0.0], [{"kayit_id": "x"}], 0.5, 2),
            ([1.0, 0.0, 0.0], [k0, k0], 0.5, 2),
            ([1.0, 0.0, 0.0], [dict(k0, kayit_id=" ")], 0.5, 2),
            ([1.0, 0.0, 0.0], [dict(k0, kayit_id=1)], 0.5, 2),
            ([1.0, 0.0, 0.0], [dict(k0, kategori=" ")], 0.5, 2),
            ([1.0, 0.0, 0.0], [dict(k0, kategori=1)], 0.5, 2),
            ([1.0, 0.0, 0.0], [dict(k0, yama_ozeti=" ")], 0.5, 2),
            ([1.0, 0.0, 0.0], [dict(k0, yama_ozeti=1)], 0.5, 2),
            ([1.0, 0.0, 0.0], KORPUS, -0.1, 2),
            ([1.0, 0.0, 0.0], KORPUS, 1.1, 2),
            ([1.0, 0.0, 0.0], KORPUS, True, 2),
            ([1.0, 0.0, 0.0], KORPUS, "0.5", 2),
            ([1.0, 0.0, 0.0], KORPUS, float("nan"), 2),
            ([1.0, 0.0, 0.0], KORPUS, float("inf"), 2),
            ([float("nan"), 0.0, 0.0], KORPUS, 0.5, 2),
            ([1.0, 0.0, 0.0], [dict(k0, vektor=[float("inf"), 0.0, 0.0])], 0.5, 2),
            ([1.0, 0.0, 0.0], KORPUS, 0.5, 0),
            ([1.0, 0.0, 0.0], KORPUS, 0.5, True),
            ([1.0, 0.0, 0.0], KORPUS, 0.5, "2"),
        ]
        for s_in, k_in, e_in, c_in in hatalilar:
            try:
                fn(s_in, k_in, e_in, c_in)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(benzer_zafiyet_ara), "benzer zafiyet araması eşik filtresini ve sıralamayı doğru uygulamalı")
def m_esiksiz(s, k, e=0.75, c=3):
    return benzer_zafiyet_ara(s, k, 0.0, c)
def m_ters_sira(s, k, e=0.75, c=3):
    return list(reversed(benzer_zafiyet_ara(s, k, e, c)))
for ad, mutant in [("eşik filtresini atlayan", m_esiksiz), ("sıralamayı ters çeviren", m_ters_sira)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
import math

def _vektor_boyu(v):
    if not isinstance(v, list):
        raise ValueError("vektör liste olmalı")
    toplam = 0.0
    for x in v:
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
            raise ValueError("vektör elemanları sayısal olmalı")
        toplam += float(x) * float(x)
    if toplam <= 0.0:
        raise ValueError("boş veya sıfır vektör kullanılamaz")
    return math.sqrt(toplam)

def _kosinus(v1, v2):
    b1 = _vektor_boyu(v1)
    b2 = _vektor_boyu(v2)
    if len(v1) != len(v2):
        raise ValueError("vektör boyutları eşit olmalı")
    return round(sum(float(a) * float(b) for a, b in zip(v1, v2)) / (b1 * b2), 4)

def benzer_zafiyet_ara(sorgu_vektoru, korpus, esik=0.75, en_cok=3):
    _vektor_boyu(sorgu_vektoru)
    if not isinstance(korpus, list) or not korpus:
        raise ValueError("korpus boş olmayan liste olmalı")
    if isinstance(esik, bool) or not isinstance(esik, (int, float)) or not math.isfinite(esik) or esik < 0 or esik > 1:
        raise ValueError("eşik geçersiz")
    if isinstance(en_cok, bool) or not isinstance(en_cok, int) or en_cok < 1:
        raise ValueError("en_cok pozitif tam sayı olmalı")

    beklenen = {"kayit_id", "kategori", "vektor", "yama_ozeti"}
    gorulen = set()
    adaylar = []
    for k in korpus:
        if not isinstance(k, dict) or set(k.keys()) != beklenen:
            raise ValueError("korpus kaydı şeması geçersiz")
        kid = k["kayit_id"]
        if not isinstance(kid, str) or not kid.strip() or kid in gorulen:
            raise ValueError("kayıt kimliği geçersiz")
        gorulen.add(kid)
        for alan in ("kategori", "yama_ozeti"):
            if not isinstance(k[alan], str) or not k[alan].strip():
                raise ValueError("metin alanı boş olamaz")
        skor = _kosinus(sorgu_vektoru, k["vektor"])
        if skor >= esik:
            adaylar.append({
                "kayit_id": kid,
                "kategori": k["kategori"],
                "benzerlik": skor,
                "yama_ozeti": k["yama_ozeti"],
            })

    adaylar.sort(key=lambda x: (-x["benzerlik"], x["kayit_id"]))
    return adaylar[:en_cok]
```

```hint
Eşit benzerlik puanlarında deterministik sıralama için `key=lambda x: (-x["benzerlik"], x["kayit_id"])` kullan.
```
:::

::: gorev 3 · Benzerlik eşiği kalibrasyonunu ve yanlış eşleşme oranını ölç
`esik_kalibrasyonu_olc(sorgular, korpus, esik)` işlevini yaz.

Girdi kuralları:
- `sorgular`: boş olmayan `list`; her öğesi tam olarak `{"sorgu_id", "beklenen_kategori", "vektor"}` anahtarlarını taşımalıdır (`sorgu_id` boş olmayan benzersiz `str`, `beklenen_kategori` boş olmayan `str`, `vektor` geçerli vektör).
- `korpus` ve `esik`: 2. görevdeki kurallarla aynıdır.
- Geçersiz girdi veya şemada `ValueError` yükselt.

Kalibrasyon kuralları:
- Her sorgu için `benzer_zafiyet_ara(sorgu["vektor"], korpus, esik, 1)` çalıştır:
  - Eğer sonuç listesi **boşsa**:
    - `beklenen_kategori == "bilinmeyen"` ise `dogru_eslesme += 1` (korpusta olmayan zafiyet doğru şekilde eşleşmedi).
    - Aksi hâlde `cevapsiz += 1` (bilinen zafiyet kaçırıldı).
  - Eğer sonuç listesi **doluysa** (`en_iyi = sonuclar[0]`):
    - `en_iyi["kategori"] == beklenen_kategori` ise `dogru_eslesme += 1`.
    - Aksi hâlde `yanlis_eslesme += 1`.
- `isabet_orani = round(dogru_eslesme / len(sorgular), 4)`.
- Döndürülecek sözlük:
  `{"dogru_eslesme": int, "yanlis_eslesme": int, "cevapsiz": int, "isabet_orani": float}`

```starter
from ai_ile_guvenlik_veri import json_yukle

korpus = json_yukle("zafiyet_korpusu.json")["kayitlar"]
veri = json_yukle("sorgu_vektorleri.json")

def esik_kalibrasyonu_olc(sorgular, korpus, esik):
    # HATA: Eşik altında kalan "bilinmeyen" sorguları doğru eşleşme saymıyor.
    return {
        "dogru_eslesme": 0,
        "yanlis_eslesme": 0,
        "cevapsiz": len(sorgular),
        "isabet_orani": 0.0,
    }

print(esik_kalibrasyonu_olc(veri["sorgular"], korpus, veri["esik"]))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-03")
```

```test
need("esik_kalibrasyonu_olc")

KORPUS = [
    {"kayit_id": "Z-1", "kategori": "sql", "vektor": [1.0, 0.0, 0.0], "yama_ozeti": "Yama 1"},
    {"kayit_id": "Z-2", "kategori": "ssrf", "vektor": [0.0, 1.0, 0.0], "yama_ozeti": "Yama 2"},
]

SORGULAR = [
    {"sorgu_id": "s-1", "beklenen_kategori": "sql", "vektor": [0.9, 0.1, 0.0]},
    {"sorgu_id": "s-2", "beklenen_kategori": "bilinmeyen", "vektor": [0.0, 0.0, 1.0]},
    {"sorgu_id": "s-3", "beklenen_kategori": "ssrf", "vektor": [0.8, 0.6, 0.0]},
    {"sorgu_id": "s-4", "beklenen_kategori": "sql", "vektor": [0.5, 0.0, 0.866]},
]

def sozlesme(fn):
    try:
        r = fn(SORGULAR, KORPUS, 0.7)
        if r != {
            "dogru_eslesme": 2,
            "yanlis_eslesme": 1,
            "cevapsiz": 1,
            "isabet_orani": 0.5,
        }:
            return False

        if fn(SORGULAR[:3], KORPUS, 0.7)["isabet_orani"] != 0.6667:
            return False
        if fn([{"sorgu_id": "s-esit", "beklenen_kategori": "sql", "vektor": [0.8, 0.6, 0.0]}], KORPUS, 0.8)["dogru_eslesme"] != 1:
            return False
        if fn([{"sorgu_id": "s-sifir", "beklenen_kategori": "sql", "vektor": [1.0, 0.0, 0.0]}], KORPUS, 0.0)["dogru_eslesme"] != 1:
            return False
        if fn([{"sorgu_id": "s-bir", "beklenen_kategori": "sql", "vektor": [1.0, 0.0, 0.0]}], KORPUS, 1.0)["dogru_eslesme"] != 1:
            return False
        if fn([{"sorgu_id": "s-bil-yanlis", "beklenen_kategori": "bilinmeyen", "vektor": [1.0, 0.0, 0.0]}], KORPUS, 0.7)["yanlis_eslesme"] != 1:
            return False
        korpus_esit = [
            {"kayit_id": "Z-B", "kategori": "ssrf", "vektor": [1.0, 0.0, 0.0], "yama_ozeti": "Y"},
            {"kayit_id": "Z-A", "kategori": "sql", "vektor": [1.0, 0.0, 0.0], "yama_ozeti": "Y"},
        ]
        if fn([{"sorgu_id": "s-tie", "beklenen_kategori": "sql", "vektor": [1.0, 0.0, 0.0]}], korpus_esit, 0.5)["dogru_eslesme"] != 1:
            return False
        korpus_hassas = [
            {"kayit_id": "Z-H", "kategori": "sql", "vektor": [2.0, 1.0, 0.0], "yama_ozeti": "Y"},
        ]
        if fn([{"sorgu_id": "s-h", "beklenen_kategori": "sql", "vektor": [1.0, 2.0, 3.0]}], korpus_hassas, 0.4781)["dogru_eslesme"] != 1:
            return False

        s0 = SORGULAR[0]
        k0 = KORPUS[0]
        hatalilar = [
            (None, KORPUS, 0.7),
            (tuple(SORGULAR), KORPUS, 0.7),
            ([], KORPUS, 0.7),
            ("liste", KORPUS, 0.7),
            (["bozuk"], KORPUS, 0.7),
            ([{"sorgu_id": "x"}], KORPUS, 0.7),
            ([s0, s0], KORPUS, 0.7),
            ([dict(s0, sorgu_id=" ")], KORPUS, 0.7),
            ([dict(s0, sorgu_id=1)], KORPUS, 0.7),
            ([dict(s0, beklenen_kategori=" ")], KORPUS, 0.7),
            ([dict(s0, beklenen_kategori=1)], KORPUS, 0.7),
            ([dict(s0, vektor="v")], KORPUS, 0.7),
            ([dict(s0, vektor=(1.0, 0.0, 0.0))], KORPUS, 0.7),
            ([dict(s0, vektor=[])], KORPUS, 0.7),
            ([dict(s0, vektor=[0.0, 0.0, 0.0])], KORPUS, 0.7),
            ([dict(s0, vektor=[1.0, 0.0])], KORPUS, 0.7),
            ([dict(s0, vektor=[True, 1.0, 0.0])], KORPUS, 0.7),
            ([s0], None, 0.7),
            ([s0], tuple(KORPUS), 0.7),
            ([s0], [], 0.7),
            ([s0], ["bozuk"], 0.7),
            ([s0], [{"kayit_id": "x"}], 0.7),
            ([s0], [k0, k0], 0.7),
            ([s0], [dict(k0, kayit_id=" ")], 0.7),
            ([s0], [dict(k0, kayit_id=1)], 0.7),
            ([s0], [dict(k0, kategori=" ")], 0.7),
            ([s0], [dict(k0, kategori=1)], 0.7),
            ([s0], [dict(k0, yama_ozeti=" ")], 0.7),
            ([s0], [dict(k0, yama_ozeti=1)], 0.7),
            ([s0], KORPUS, -0.1),
            ([s0], KORPUS, 1.1),
            ([s0], KORPUS, True),
            ([s0], KORPUS, "0.7"),
            ([s0], KORPUS, float("nan")),
            ([s0], KORPUS, float("inf")),
            ([dict(s0, vektor=[float("nan"), 1.0, 0.0])], KORPUS, 0.7),
            ([s0], [dict(k0, vektor=[float("-inf"), 1.0, 0.0])], 0.7),
        ]
        for s_in, k_in, e_in in hatalilar:
            try:
                fn(s_in, k_in, e_in)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(esik_kalibrasyonu_olc), "eşik kalibrasyonu doğru eşleşme, yanlış eşleşme ve cevapsız sayılarını doğru ölçmeli")
def m_bilinmeyen_cevapsiz(s, k, e):
    r = esik_kalibrasyonu_olc(s, k, e)
    return dict(r, dogru_eslesme=r["dogru_eslesme"] - 1, cevapsiz=r["cevapsiz"] + 1)
def m_yanlis_sifir(s, k, e):
    return dict(esik_kalibrasyonu_olc(s, k, e), yanlis_eslesme=0)
for ad, mutant in [("bilinmeyen sorguyu cevapsız sayan", m_bilinmeyen_cevapsiz), ("yanlış eşleşmeyi sıfırlayan", m_yanlis_sifir)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
_s3=[{"sorgu_id":"scaled","beklenen_kategori":"sql","vektor":[0.5,0.0]}]
_k3=[{"kayit_id":"k","kategori":"sql","vektor":[1.0,0.0],"yama_ozeti":"synthetic"}]
eq(esik_kalibrasyonu_olc(_s3,_k3,0.7),{"dogru_eslesme":1,"yanlis_eslesme":0,"cevapsiz":0,"isabet_orani":1.0},"birim olmayan vektörde kosinüs normalizasyonu kalibrasyona taşınır")
```

```solution
import math

def _vektor_boyu(v):
    if not isinstance(v, list):
        raise ValueError("vektör liste olmalı")
    toplam = 0.0
    for x in v:
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
            raise ValueError("vektör elemanları sayısal olmalı")
        toplam += float(x) * float(x)
    if toplam <= 0.0:
        raise ValueError("boş veya sıfır vektör kullanılamaz")
    return math.sqrt(toplam)

def _kosinus(v1, v2):
    b1 = _vektor_boyu(v1)
    b2 = _vektor_boyu(v2)
    if len(v1) != len(v2):
        raise ValueError("vektör boyutları eşit olmalı")
    return round(sum(float(a) * float(b) for a, b in zip(v1, v2)) / (b1 * b2), 4)

def _ara_en_iyi(sorgu_vektoru, korpus, esik):
    _vektor_boyu(sorgu_vektoru)
    beklenen = {"kayit_id", "kategori", "vektor", "yama_ozeti"}
    gorulen = set()
    adaylar = []
    for k in korpus:
        if not isinstance(k, dict) or set(k.keys()) != beklenen:
            raise ValueError("korpus kaydı şeması geçersiz")
        kid = k["kayit_id"]
        if not isinstance(kid, str) or not kid.strip() or kid in gorulen:
            raise ValueError("kayıt kimliği geçersiz")
        gorulen.add(kid)
        for alan in ("kategori", "yama_ozeti"):
            if not isinstance(k[alan], str) or not k[alan].strip():
                raise ValueError("metin alanı boş olamaz")
        skor = _kosinus(sorgu_vektoru, k["vektor"])
        if skor >= esik:
            adaylar.append({"skor": skor, "id": kid, "kat": k["kategori"]})
    if not adaylar:
        return None
    adaylar.sort(key=lambda x: (-x["skor"], x["id"]))
    return adaylar[0]["kat"]

def esik_kalibrasyonu_olc(sorgular, korpus, esik):
    if not isinstance(sorgular, list) or not sorgular:
        raise ValueError("sorgular boş olamaz")
    if not isinstance(korpus, list) or not korpus:
        raise ValueError("korpus boş olamaz")
    if isinstance(esik, bool) or not isinstance(esik, (int, float)) or not math.isfinite(esik) or esik < 0 or esik > 1:
        raise ValueError("eşik geçersiz")

    beklenen_s = {"sorgu_id", "beklenen_kategori", "vektor"}
    gorulen_s = set()
    dogru_eslesme = 0
    yanlis_eslesme = 0
    cevapsiz = 0

    for s in sorgular:
        if not isinstance(s, dict) or set(s.keys()) != beklenen_s:
            raise ValueError("sorgu şeması geçersiz")
        sid = s["sorgu_id"]
        if not isinstance(sid, str) or not sid.strip() or sid in gorulen_s:
            raise ValueError("sorgu kimliği geçersiz")
        gorulen_s.add(sid)
        bkat = s["beklenen_kategori"]
        if not isinstance(bkat, str) or not bkat.strip():
            raise ValueError("beklenen kategori boş olamaz")
        bulunan_kat = _ara_en_iyi(s["vektor"], korpus, esik)
        if bulunan_kat is None:
            if bkat == "bilinmeyen":
                dogru_eslesme += 1
            else:
                cevapsiz += 1
        elif bulunan_kat == bkat:
            dogru_eslesme += 1
        else:
            yanlis_eslesme += 1

    return {
        "dogru_eslesme": dogru_eslesme,
        "yanlis_eslesme": yanlis_eslesme,
        "cevapsiz": cevapsiz,
        "isabet_orani": round(dogru_eslesme / len(sorgular), 4),
    }
```

```hint
Eşik altında kaldığı için hiçbir sonuç dönmeyen (`bulunan_kat is None`) sorgularda `beklenen_kategori == "bilinmeyen"` ise `dogru_eslesme`, değilse `cevapsiz` sayacını artır.
```
:::

::: gorev Gerçek deney · Yerel `all-minilm:22m` gömme modeliyle zafiyet korpusunda benzerlik araması
Önceki üç görevde yazdığın `kosinus_benzerligi`, `benzer_zafiyet_ara` ve `esik_kalibrasyonu_olc` işlevlerini bu adımda birleştir.

Canlı deneyde:
1. Yerel Ollama `all-minilm:22m` modeli kullanılarak SQL enjeksiyonu, dizin geçişi (`path traversal`) ve SSRF zafiyet açıklamalarının gerçek embedding vektörleri üretilir.
2. Farklı ifadelerle yazılmış zafiyet sorguları `benzer_zafiyet_ara` ile korpusta aranır.
3. `esik_kalibrasyonu_olc` ile gerçek gömme uzayındaki isabet oranı doğrulanır.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab

def kosinus_benzerligi(v1, v2):
    return 0.0

def benzer_zafiyet_ara(sorgu_vektoru, korpus, esik=0.75, en_cok=3):
    return []

def esik_kalibrasyonu_olc(sorgular, korpus, esik):
    return {}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_ile_guvenlik_03 as deney
    deney.goster(kosinus_benzerligi, benzer_zafiyet_ara, esik_kalibrasyonu_olc)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-03")
```

```test
import ai_lab
from sandbox import ai_gercek_ai_ile_guvenlik_03 as D

checks = []
_base_ok = ok
def ok(kosul, mesaj):
    checks.append(bool(kosul))
    return _base_ok(kosul, mesaj)

for ad in ("kosinus_benzerligi", "benzer_zafiyet_ara", "esik_kalibrasyonu_olc"):
    need(ad)

sorun = ai_lab.kod_denetimi(
    src,
    ("kosinus_benzerligi_referans", "benzer_zafiyet_ara_referans", "esik_kalibrasyonu_olc_referans"),
)
ok(not sorun, "laboratuvar yamalanmamalı, referans işlevler çağrılmamalı")

ok(kosinus_benzerligi([1.0, 2.0], [2.0, 4.0]) == D.kosinus_benzerligi_referans([1.0, 2.0], [2.0, 4.0]), "sentetik ön kontrol: kosinüs benzerliği referansla uyumlu")

def _on_sozlesme():
    try:
        if kosinus_benzerligi([3.0, 0.0], [6.0, 0.0]) != 1.0 or kosinus_benzerligi([1.0, 2.0, 3.0], [2.0, 1.0, 0.0]) != 0.4781 or kosinus_benzerligi([1.0, -1.0], [-1.0, 1.0]) != -1.0:
            return False
        for a_in, b_in in [(None, [1.0]), ((1.0,), [1.0]), ([1.0], None), ([], [1.0]), ([1.0], []), ("x", [1.0]), (["1.0"], [1.0]), ([1.0, 2.0], [1.0]), ([True, 1.0], [1.0, 1.0]), ([0.0, 0.0], [1.0, 1.0]), ([float("nan"), 1.0], [1.0, 1.0]), ([1.0, 1.0], [float("inf"), 1.0])]:
            try:
                kosinus_benzerligi(a_in, b_in)
                return False
            except ValueError:
                pass
        kor = [
            {"kayit_id": "Z-2", "kategori": "sql", "vektor": [1.0, 0.0, 0.0], "yama_ozeti": "Yama 2"},
            {"kayit_id": "Z-1", "kategori": "sql", "vektor": [2.0, 0.0, 0.0], "yama_ozeti": "Yama 1"},
            {"kayit_id": "Z-3", "kategori": "sql", "vektor": [0.8, 0.6, 0.0], "yama_ozeti": "Yama 3"},
            {"kayit_id": "Z-4", "kategori": "ssrf", "vektor": [0.0, 0.0, 1.0], "yama_ozeti": "Yama 4"},
        ]
        r_ara = benzer_zafiyet_ara([1.0, 0.0, 0.0], kor)
        if r_ara != [
            {"kayit_id": "Z-1", "kategori": "sql", "benzerlik": 1.0, "yama_ozeti": "Yama 1"},
            {"kayit_id": "Z-2", "kategori": "sql", "benzerlik": 1.0, "yama_ozeti": "Yama 2"},
            {"kayit_id": "Z-3", "kategori": "sql", "benzerlik": 0.8, "yama_ozeti": "Yama 3"},
        ]:
            return False
        kor_def = kor + [
            {"kayit_id": "Z-5", "kategori": "sql", "vektor": [0.6, 0.8, 0.0], "yama_ozeti": "Yama 5"},
            {"kayit_id": "Z-6", "kategori": "sql", "vektor": [3.0, 0.0, 0.0], "yama_ozeti": "Yama 6"},
        ]
        if len(benzer_zafiyet_ara([1.0, 0.0, 0.0], kor_def)) != 3 or len(benzer_zafiyet_ara([0.6, 0.8, 0.0], kor_def)) != 2:
            return False
        if len(benzer_zafiyet_ara([1.0, 0.0, 0.0], kor, 0.8, 1)) != 1 or benzer_zafiyet_ara([1.0, 0.0, 0.0], kor, 0.85, 3) != r_ara[:2]:
            return False
        if len(benzer_zafiyet_ara([1.0, 0.0, 0.0], kor, 0.0, 4)) != 4 or len(benzer_zafiyet_ara([1.0, 0.0, 0.0], kor, 1.0, 3)) != 2:
            return False
        k0 = kor[0]
        for s_in, k_in, e_in, c_in in [
            (None, kor, 0.5, 2), ([], kor, 0.5, 2), ([0.0, 0.0, 0.0], kor, 0.5, 2), ([1.0, 0.0], kor, 0.5, 2),
            ([1.0, 0.0, 0.0], None, 0.5, 2), ([1.0, 0.0, 0.0], tuple(kor), 0.5, 2), ([1.0, 0.0, 0.0], [], 0.5, 2), ([1.0, 0.0, 0.0], ["x"], 0.5, 2),
            ([1.0, 0.0, 0.0], [{"kayit_id": "x"}], 0.5, 2), ([1.0, 0.0, 0.0], [k0, k0], 0.5, 2),
            ([1.0, 0.0, 0.0], [dict(k0, kayit_id=" ")], 0.5, 2), ([1.0, 0.0, 0.0], [dict(k0, kayit_id=1)], 0.5, 2),
            ([1.0, 0.0, 0.0], [dict(k0, kategori=" ")], 0.5, 2), ([1.0, 0.0, 0.0], [dict(k0, kategori=1)], 0.5, 2),
            ([1.0, 0.0, 0.0], [dict(k0, yama_ozeti=" ")], 0.5, 2), ([1.0, 0.0, 0.0], [dict(k0, yama_ozeti=1)], 0.5, 2),
            ([1.0, 0.0, 0.0], kor, -0.1, 2), ([1.0, 0.0, 0.0], kor, 1.1, 2), ([1.0, 0.0, 0.0], kor, True, 2), ([1.0, 0.0, 0.0], kor, "0.5", 2),
            ([1.0, 0.0, 0.0], kor, float("nan"), 2), ([1.0, 0.0, 0.0], kor, 0.5, 0), ([1.0, 0.0, 0.0], kor, 0.5, True), ([1.0, 0.0, 0.0], kor, 0.5, "2"),
        ]:
            try:
                benzer_zafiyet_ara(s_in, k_in, e_in, c_in)
                return False
            except ValueError:
                pass
        kor2 = [
            {"kayit_id": "Z-1", "kategori": "sql", "vektor": [1.0, 0.0, 0.0], "yama_ozeti": "Yama 1"},
            {"kayit_id": "Z-2", "kategori": "ssrf", "vektor": [0.0, 1.0, 0.0], "yama_ozeti": "Yama 2"},
        ]
        sorg = [
            {"sorgu_id": "s-1", "beklenen_kategori": "sql", "vektor": [0.9, 0.1, 0.0]},
            {"sorgu_id": "s-2", "beklenen_kategori": "bilinmeyen", "vektor": [0.0, 0.0, 1.0]},
            {"sorgu_id": "s-3", "beklenen_kategori": "ssrf", "vektor": [0.8, 0.6, 0.0]},
            {"sorgu_id": "s-4", "beklenen_kategori": "sql", "vektor": [0.5, 0.0, 0.866]},
        ]
        if esik_kalibrasyonu_olc(sorg, kor2, 0.7) != {"dogru_eslesme": 2, "yanlis_eslesme": 1, "cevapsiz": 1, "isabet_orani": 0.5}:
            return False
        if esik_kalibrasyonu_olc([sorg[0]], kor2, 0.7) != {"dogru_eslesme": 1, "yanlis_eslesme": 0, "cevapsiz": 0, "isabet_orani": 1.0}:
            return False
        if esik_kalibrasyonu_olc(sorg[:3], kor2, 0.7)["isabet_orani"] != 0.6667:
            return False
        s0 = sorg[0]
        for s_in, k_in, e_in in [
            (None, kor2, 0.7), (tuple(sorg), kor2, 0.7), ([], kor2, 0.7), ("x", kor2, 0.7), (["x"], kor2, 0.7), ([{"sorgu_id": "x"}], kor2, 0.7),
            ([s0, s0], kor2, 0.7), ([dict(s0, sorgu_id=" ")], kor2, 0.7), ([dict(s0, sorgu_id=1)], kor2, 0.7),
            ([dict(s0, beklenen_kategori=" ")], kor2, 0.7), ([dict(s0, beklenen_kategori=1)], kor2, 0.7),
            ([s0], kor2, float("nan")),
        ]:
            try:
                esik_kalibrasyonu_olc(s_in, k_in, e_in)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(_on_sozlesme(), "sentetik ön kontrol: kosinüs, eşikli arama ve kalibrasyon sözleşmesi tam")

if not all(checks):
    stop()

try:
    r = D.deney(kosinus_benzerligi, benzer_zafiyet_ara, esik_kalibrasyonu_olc)
except Exception as e:
    ok(False, f"GERÇEK GÖMME KORPUSU DENEYİ YAPILAMADI: {type(e).__name__}: {e}")
    stop()

for ad, deger in r["kontroller"].items():
    ok(deger, "gerçek deney: " + ad)

ai_lab.kanit_yaz("ile-guvenlik-03-embedding", {
    "kaynak": "gercek",
    "kabul": all(checks),
    "ders": "ai-ile-guvenlik-03",
    "ortam": r["ortam"],
    "ayarlar": r["ayarlar"],
    "deney": r,
    "ozet": r["ozet"],
})
o = r["ozet"]
ok(
    True,
    f"BULGU ({o['gomme_modeli']} · {o['boyut']}d): sql_benzerlik={o['sql_benzerlik']}, doğru={o['dogru_eslesme']}, isabet_oranı={o['isabet_orani']}.",
)
```

```solution
import math
import ai_lab

def _vektor_boyu(v):
    if not isinstance(v, list):
        raise ValueError("vektör liste olmalı")
    toplam = 0.0
    for x in v:
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
            raise ValueError("vektör elemanları sayısal olmalı")
        toplam += float(x) * float(x)
    if toplam <= 0.0:
        raise ValueError("boş veya sıfır vektör kullanılamaz")
    return math.sqrt(toplam)

def kosinus_benzerligi(v1, v2):
    b1 = _vektor_boyu(v1)
    b2 = _vektor_boyu(v2)
    if len(v1) != len(v2):
        raise ValueError("vektör boyutları eşit olmalı")
    carpim = sum(float(a) * float(b) for a, b in zip(v1, v2))
    return round(carpim / (b1 * b2), 4)

def benzer_zafiyet_ara(sorgu_vektoru, korpus, esik=0.75, en_cok=3):
    _vektor_boyu(sorgu_vektoru)
    if not isinstance(korpus, list) or not korpus:
        raise ValueError("korpus boş olmayan liste olmalı")
    if isinstance(esik, bool) or not isinstance(esik, (int, float)) or not math.isfinite(esik) or esik < 0 or esik > 1:
        raise ValueError("eşik geçersiz")
    if isinstance(en_cok, bool) or not isinstance(en_cok, int) or en_cok < 1:
        raise ValueError("en_cok pozitif tam sayı olmalı")

    beklenen = {"kayit_id", "kategori", "vektor", "yama_ozeti"}
    gorulen = set()
    adaylar = []
    for k in korpus:
        if not isinstance(k, dict) or set(k.keys()) != beklenen:
            raise ValueError("korpus kaydı şeması geçersiz")
        kid = k["kayit_id"]
        if not isinstance(kid, str) or not kid.strip() or kid in gorulen:
            raise ValueError("kayıt kimliği geçersiz")
        gorulen.add(kid)
        for alan in ("kategori", "yama_ozeti"):
            if not isinstance(k[alan], str) or not k[alan].strip():
                raise ValueError("metin alanı boş olamaz")
        skor = kosinus_benzerligi(sorgu_vektoru, k["vektor"])
        if skor >= esik:
            adaylar.append({
                "kayit_id": kid,
                "kategori": k["kategori"],
                "benzerlik": skor,
                "yama_ozeti": k["yama_ozeti"],
            })

    adaylar.sort(key=lambda x: (-x["benzerlik"], x["kayit_id"]))
    return adaylar[:en_cok]

def esik_kalibrasyonu_olc(sorgular, korpus, esik):
    if not isinstance(sorgular, list) or not sorgular:
        raise ValueError("sorgular boş olamaz")
    beklenen_s = {"sorgu_id", "beklenen_kategori", "vektor"}
    gorulen_s = set()
    dogru_eslesme = 0
    yanlis_eslesme = 0
    cevapsiz = 0

    for s in sorgular:
        if not isinstance(s, dict) or set(s.keys()) != beklenen_s:
            raise ValueError("sorgu şeması geçersiz")
        sid = s["sorgu_id"]
        if not isinstance(sid, str) or not sid.strip() or sid in gorulen_s:
            raise ValueError("sorgu kimliği geçersiz")
        gorulen_s.add(sid)
        bkat = s["beklenen_kategori"]
        if not isinstance(bkat, str) or not bkat.strip():
            raise ValueError("beklenen kategori boş olamaz")
        sonuclar = benzer_zafiyet_ara(s["vektor"], korpus, esik, 1)
        if not sonuclar:
            if bkat == "bilinmeyen":
                dogru_eslesme += 1
            else:
                cevapsiz += 1
        elif sonuclar[0]["kategori"] == bkat:
            dogru_eslesme += 1
        else:
            yanlis_eslesme += 1

    return {
        "dogru_eslesme": dogru_eslesme,
        "yanlis_eslesme": yanlis_eslesme,
        "cevapsiz": cevapsiz,
        "isabet_orani": round(dogru_eslesme / len(sorgular), 4),
    }

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_ile_guvenlik_03 as deney
    deney.goster(kosinus_benzerligi, benzer_zafiyet_ara, esik_kalibrasyonu_olc)
```

```hint
Önceki üç görevdeki `kosinus_benzerligi`, `benzer_zafiyet_ara` ve `esik_kalibrasyonu_olc` çözümlerini birleştir.
```
:::


::: anlat Bunu iki dakikada nasıl anlatırsın?
Embedding benzerliğini iç çarpımdan ayırmak için iki vektörü normlarıyla normalize et. Aynı yönlü yarım uzunlukta vektörün cosine değeri yine birdir; kalibrasyonda bu invariant korunmalı. Eşik altındaki sorguyu zorla bir kategoriye atama. Bilinmeyen kategoride eşleşme bulunmaması ile bilinen kategoriyi kaçırmayı ayrı say. Benzer rapor retrieval sonucu, doğrulanmış bir zafiyet teşhisi değildir.

Önkoşul ve yol köprüsü: ai-temel-16 embedding; ai-savunma-19 tenant sınırı.

| Yaygın yanlış | Mekanizma ve sınır |
|---|---|
| Her sorgu mutlaka top-k sonuç almalıdır | Eşik altındaki yeni kategori için doğru sonuç sessizlik olabilir |

Dinleyiciye sor: Bir model önerisini gerçek güvenlik kararı hâline getiren hangi uygulama denetimidir? Veri kökenini ve kalan sınırı koruyarak cevapla.
:::


### Birincil kaynak ve deneyin sınırı

[Ollama sohbet API sözleşmesi](https://docs.ollama.com/api/chat). Model çağrısı ile Python tarafındaki vektör hesabı ayrı katmanlardır; kosinüs ve eşik kararını öğrenci kodu hesaplar.
