---
id: ai-guvence-09
title: "GCG ve AutoDAN: Ayrık Token Optimizasyonu"
summary: Ayrık adayları karşılaştır; arama izlerini sorgu bütçesiyle özetle, transfer başarısını raporla ve sonda gerçek dil modeli üzerinde koordinat gradyanı (GCG) sonek araması yürüt.
esleme: ai-guvence-07, ai-guvence-37, ai-saldiri-09
timeout: 300
---

::: anlat Ayrık arama sürekli gradyanı doğrudan tokena çeviremez

| Gerçek araç / model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| GCG (Greedy Coordinate Gradients) / AutoDAN otomatik ayrık optimizasyon ve transfer saldırıları yürütür | İlk 3 görev ayrık aday seçimi, arama izi özeti ve model transfer başarı raporu | Tüm açık kaynaklı veya kapalı uçlu LLM'lerin aynı soneklerle kırılabileceği veya mutlak saldırı garantisi değildir |
| SmolLM2-135M ve PyTorch backward() kancaları gerçek koordinat gradyanı ve çapraz entropi kaybı üretir | Gerçek deney hedef canary dizgesi için gerçek embedding gradyanı, aday seçimi ve ileri geçiş kaybı ölçümü | Üretim modellerinde korumaların aşıldığı veya gradyan tabanlı saldırıların her zaman küresel minimuma ulaştığı kanıtı değildir |

> [!NOT]
> `veri/optimizasyon.json` dosyası sentetik ayrık token adayları, arama izleri ve transfer skorlarını içerir; canlı saldırı kaydı veya model çıktısı değildir. İlk 3 görev bu yerel fixture verisini okur. Her Run/Check işleminde `hazirla("ai-guvence-09")` geçici kopya oluşturur; kalıcı değişiklik saklanmaz. Kodunuzu veya verinizi editörde inceleyebilirsiniz. Gizli değerlendirme testleri ayrı doğrulamalar koşturur. Gerçek deney adımı yerel PyTorch ve SmolLM2-135M modeliyle koordinat gradyanını doğrudan hesaplar; yeni paket veya model indirilmez.

Sürekli girdi uzaylarında çalışan geleneksel derin öğrenme modellerinde (örneğin görüntü sınıflandırma), karşıt saldırılar (adversarial attacks; FGSM, PGD) doğrudan piksel değerlerine gradyan inişi ($\mathbf{x} \leftarrow \mathbf{x} - \eta \nabla_{\mathbf{x}} \mathcal{L}$) uygulanarak optimize edilir. Ancak büyük dil modellerinde (LLM) girdi uzayı sürekli değil, sonlu ve ayrık bir sözlükten ($V$) seçilen token kimliklerinden oluşur. Modelin gömme (embedding) katmanında hesaplanan sürekli gradyan vektörü, sözlükteki herhangi bir gerçek tokene birebir karşılık gelmez. Bu nedenle ayrık token optimizasyonu (discrete token optimization), sürekli gradyan bilgisini ayrık seçim uzayına aktaran özel arama stratejileri gerektirir.

Açık kaynaklı güvenlik araştırmalarında iki temel yöntem öne çıkar:
1. **`Greedy Coordinate Gradient (GCG)` (Zou ve ark., 2023):** white-box erişiminde modelin embedding matrisi $E$ üzerindeki gradyanlardan yararlanır. Hedef çıktının (örneğin bir canary veya "Sure, here's how to...") kaybı $\mathcal{L}$ için birinci derece Taylor açılımı yapılarak, sözlükteki her aday token $v \in V$ için yaklaşık kayıp değişimi hesaplanır:
   $$\text{skor}(v) = (e_v - e_i) \cdot \nabla_{e_i} \mathcal{L}$$
   Burada en düşük (en negatif) skora sahip adaylar belirlenen bütçeyle (`ayrik_adaylari_sec`) filtrelenir; ardından bu adaylar modelin ileri geçişinde (`forward pass`) gerçek kayıpla doğrulanır.
2. **AutoDAN (Liu ve ark., 2023):** Doğal dil akışını koruyarak şaşkınlık (perplexity) filtrelerine takılmayan genetik ve hiyerarşik ayrık arama yürütür. (Aynı adı taşıyan Zhu ve ark., 2023 çalışması ise gradyan rehberli, okunabilir sonekleri soldan sağa token token üreten ayrı bir yöntemdir; literatürde ikisini karıştırmamak gerekir.) İstemleri anlamsal olarak akıcı tutmak için mutasyon, çaprazlama ve dil modeli rehberliği kullanır.
:::

::: anlat En iyi kayıp tek başına arama maliyetini anlatmaz
Ayrık optimizasyon süreçlerinin başarısını değerlendirirken yalnızca ulaşılan en düşük kayıp değerine bakmak yanıltıcıdır. Optimizasyonun hesaplama ve sorgu maliyeti, sürecin pratik uygulanabilirliğini belirler. Bu nedenle her yöntem için arama adımları, kümülatif sorgu sayıları ve gözlenen kayıplar birlikte kaydedilir.

Arama izi özetinde (`arama_izini_ozetle`):
- `en_iyi_kayip`: Arama boyunca gözlenen en düşük kayıptır (altı ondalık basamağa yuvarlanır). Eşit kayıp durumunda daha erken (küçük) adım tercih edilir.
- `toplam_sorgu`: Son adımın kümülatif sorgu değeridir. Adımlar boyunca sorgu sayısının katı biçimde artması zorunludur.

Transfer başarısı (`transfer_ozeti`):
Bir model üzerinde optimize edilen zararlı sonekin (adversarial suffix) başka hedef modellere genellenebilirliği siber güvenlikte en kritik tehdit unsurudur (Black-Box Transferability). Bir saldırgan yerel bir modelde (örneğin SmolLM veya Llama) gradyan tabanlı optimize ettiği bir soneki, kapalı ve tescilli modellere (GPT-4, Claude vb.) transfer edebilir. Bu durum iki metrikle izlenir:
1. `transfer_orani`: Başarılı deneme sayısının toplam denemeye oranı (`basari / deneme`). Başarı alanı kesinlikle katı `bool` türünde olmalıdır (`1` veya `"true"` kabul edilmez).
2. `ortalama_yetenek`: Hedef modellerin genel dünya bilgisini ve akıl yürütme kabiliyetini koruma düzeyidir.

Saldırganlar ayrık optimizasyonda başlıca şu stratejileri izler:
- **Evrensel ve Aktarılabilir Sonekler (Universal Adversarial Suffixes):** Birden fazla istem ve modeli aynı anda hedef alarak evrensel red kıran token dizileri üretmek.
- **Şaşkınlık (Perplexity) Gizleme:** AutoDAN gibi yöntemlerle anlamsız GCG harf dizileri yerine grameri düzgün metinler oluşturup girdi filtrelerini atlatmak.
- **Sorgu Bütçesi Optimizasyonu:** Hızlı aday eleme ile hedef modele asgari sayıda istek göndererek hız sınırlarına (rate limiting) takılmamak.

Geliştiricilerin düştüğü sık tuzaklar:
- Aday seçiminde skor eşitliğinde küçük token indeksini öne almamak (`(skor, token)` belirlenimlilik kuralı).
- Sorgu artışının adımlar boyunca katı büyümediğini kontrol etmemek.
- Transfer analizi yaparken `basari` alanında bool yerine integer/string kullanmak.
- Model gradyanı ile ayrık token arasındaki asimetriyi göz ardı edip sürekli vektörü doğrudan token sanmak.

Kaynaklar: [Zou vd. 2023 — Universal and Transferable Adversarial Attacks on Aligned Language Models (GCG, arXiv:2307.15043)](https://arxiv.org/abs/2307.15043), [Liu vd. 2024 — AutoDAN: Generating Stealthy Jailbreak Prompts on Aligned Large Language Models (arXiv:2310.04451)](https://arxiv.org/abs/2310.04451).
:::

::: tahmin Ayrık seçim ve transfer oranını tahmin et
Üç çıktı satırını yaz:

```python
print(min([(0.4, 2), (0.2, 1)])[1])
print(round(2 / 3, 6))
print(sum([True, False, True]))
```

???

```cikti
1
0.666667
2
```

İlk satır düşük puanlı adayı, ikinci satır altı ondalıklı transfer oranını, üçüncü satır yalnız başarılı denemelerin sayısını gösterir.
:::

::: gorev 1 · Ayrık adayları bütçeyle seç
`ayrik_adaylari_sec(adaylar, butce)` işlevini yaz. Adaylar boş olmayan listedir; her aday tam olarak `token` ve `skor` alanlarını taşır. Token bool olmayan, sıfır veya pozitif tamsayıdır ve yinelenemez. Skor bool olmayan sonlu sayıdır. Bütçe bool olmayan pozitif tamsayıdır. Geçersiz veride `ValueError` yükselt.

En düşük skorlu adaylar seçilir; skor eşitliğinde küçük token önce gelir. Bütçe kadar, bütçe aday sayısından büyükse bütün adayları içeren token listesi döndür. Girdiyi değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-09")
```

```starter
from ai_guvence_veri import json_yukle

def ayrik_adaylari_sec(adaylar, butce):
    # KUSURLU BAŞLANGIÇ KODU: adayları skora göre sıralamadan ilk bütçe kadar elemanı olduğu gibi döndürür.
    return [a["token"] for a in adaylar[:butce]] if isinstance(adaylar, list) else []

v = json_yukle("veri/optimizasyon.json")
print("Aday seçimi örneği:", ayrik_adaylari_sec(v["adaylar"], v["butce"]))
```

```test
import copy
A = [
    {"token": 41, "skor": 0.4},
    {"token": 7, "skor": 0.2},
    {"token": 19, "skor": 0.2},
    {"token": 3, "skor": 0.9},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(A)
        if fn(A, 2) != [7, 19] or A != once:
            return False
        if fn(A, 10) != [7, 19, 41, 3] or fn(A, 1) != [7]:
            return False
        if fn([{"token": 0, "skor": -1}, {"token": 2, "skor": 0}], 1) != [0]:
            return False
        for adaylar, butce in [
            (None, 1), (tuple(A), 1), ({}, 1), ([], 1), ([None], 1), ([dict(A[0], ek=1)], 1),
            ([dict(A[0], token=True)], 1), ([dict(A[0], token=1.0)], 1), ([dict(A[0], token=-1)], 1),
            ([A[0], A[0]], 2), ([dict(A[0], skor=True)], 1), ([dict(A[0], skor="0.4")], 1),
            ([dict(A[0], skor=float("nan"))], 1), ([dict(A[0], skor=float("inf"))], 1),
            (A, 0), (A, -1), (A, True), (A, 1.0), (A, None),
        ]:
            try:
                fn(adaylar, butce)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(ayrik_adaylari_sec), "ayrık aday, sıralama ve bütçe kuralları korunmalı")
def m_skor(adaylar, butce):
    return ayrik_adaylari_sec([dict(x, skor=0.8) for x in adaylar], butce)
def m_token(adaylar, butce):
    return ayrik_adaylari_sec([dict(x, token=5) for x in adaylar], butce)
def m_butce(adaylar, butce):
    return ayrik_adaylari_sec(adaylar, 1)
for ad, mutant in [("skorları silen", m_skor), ("tokenları değiştiren", m_token), ("bütçeyi küçülten", m_butce)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def ayrik_adaylari_sec(adaylar, butce):
    import math
    if not isinstance(adaylar, list):
        raise ValueError("adaylar liste olmalı")
    if not adaylar:
        raise ValueError("adaylar boş olamaz")
    if isinstance(butce, bool):
        raise ValueError("bütçe tamsayı olmalı")
    if not isinstance(butce, int):
        raise ValueError("bütçe tamsayı olmalı")
    if butce <= 0:
        raise ValueError("bütçe pozitif olmalı")
    tokenlar = set()
    for aday in adaylar:
        if not isinstance(aday, dict):
            raise ValueError("aday sözlük olmalı")
        if set(aday) != {"token", "skor"}:
            raise ValueError("aday şeması geçersiz")
        token = aday["token"]
        if isinstance(token, bool):
            raise ValueError("token tamsayı olmalı")
        if not isinstance(token, int):
            raise ValueError("token tamsayı olmalı")
        if token < 0:
            raise ValueError("token negatif olamaz")
        if token in tokenlar:
            raise ValueError("token yinelenemez")
        skor = aday["skor"]
        if isinstance(skor, bool):
            raise ValueError("skor sayı olmalı")
        if not isinstance(skor, (int, float)):
            raise ValueError("skor sayı olmalı")
        if not math.isfinite(skor):
            raise ValueError("skor sonlu olmalı")
        tokenlar.add(token)
    sirali = sorted(adaylar, key=lambda x: (x["skor"], x["token"]))
    return [x["token"] for x in sirali[:butce]]
```

```hint
Bütün adayları doğruladıktan sonra `(skor, token)` çiftine göre sırala ve dilimi yalnız çıktı için kullan.
```
:::

::: gorev 2 · GCG ve AutoDAN arama izlerini özetle
`arama_izini_ozetle(kayitlar)` işlevini yaz. Kayıtlar boş olmayan listedir ve her kayıt tam olarak `yontem`, `adim`, `sorgu`, `kayip` alanlarını taşır. Yöntem yalnız `GCG` veya `AutoDAN` olabilir. Adım bool olmayan, sıfır veya pozitif tamsayı; sorgu bool olmayan pozitif tamsayı; kayıp bool olmayan sonlu sayı ve `[0,1]` aralığındadır.

Aynı yöntemde adım yinelenemez ve kümülatif sorgu sayısı adımlar boyunca katı artmalıdır. Geçersiz veride `ValueError` yükselt. Her yöntem için `{"yontem":Y,"en_iyi_adim":N,"en_iyi_kayip":X,"toplam_sorgu":N}` üret; en iyi sonuç en düşük kayıp, eşitlikte en küçük adımdır. Kaybı altı ondalık basamağa yuvarla, toplam sorguyu en büyük adımın kümülatif değeri olarak ver ve özeti yöntem adına göre sırala. Girdiyi değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-09")
```

```starter
from ai_guvence_veri import json_yukle

def arama_izini_ozetle(kayitlar):
    # KUSURLU BAŞLANGIÇ KODU: yöntemleri gruplamadan sabit boş liste veya tek kayıt döndürür.
    return [{"yontem": k["yontem"], "en_iyi_adim": 0, "en_iyi_kayip": 1.0, "toplam_sorgu": 0} for k in kayitlar[:1]]

v = json_yukle("veri/optimizasyon.json")["arama_izi"]
print("Arama izi örneği:", arama_izini_ozetle(v))
```

```test
import copy
K = [
    {"yontem": "GCG", "adim": 2, "sorgu": 12, "kayip": 0.3},
    {"yontem": "AutoDAN", "adim": 0, "sorgu": 3, "kayip": 0.7},
    {"yontem": "GCG", "adim": 0, "sorgu": 4, "kayip": 0.8},
    {"yontem": "GCG", "adim": 1, "sorgu": 8, "kayip": 0.4},
    {"yontem": "AutoDAN", "adim": 1, "sorgu": 6, "kayip": 0.5},
]
BEKLENEN = [
    {"yontem": "AutoDAN", "en_iyi_adim": 1, "en_iyi_kayip": 0.5, "toplam_sorgu": 6},
    {"yontem": "GCG", "en_iyi_adim": 2, "en_iyi_kayip": 0.3, "toplam_sorgu": 12},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        if fn(K) != BEKLENEN or K != once:
            return False
        esit = fn([K[2], dict(K[3], kayip=0.8), dict(K[0], kayip=0.8)])
        if esit[0]["en_iyi_adim"] != 0 or esit[0]["toplam_sorgu"] != 12:
            return False
        sinir = fn([{"yontem": "GCG", "adim": 0, "sorgu": 1, "kayip": 0}, {"yontem": "GCG", "adim": 1, "sorgu": 2, "kayip": 1}])
        if sinir[0]["en_iyi_adim"] != 0:
            return False
        yuvarla = fn([{"yontem": "GCG", "adim": 0, "sorgu": 1, "kayip": 1 / 6}])
        if yuvarla[0]["en_iyi_kayip"] != 0.166667:
            return False
        for kayitlar in [
            None, tuple(K), {}, [], [None], [dict(K[0], ek=1)], [dict(K[0], yontem="gcg")], [dict(K[0], yontem=None)],
            [K[0], K[0]], [K[0], dict(K[0], sorgu=20)], [K[2], dict(K[3], sorgu=4)], [K[2], dict(K[3], sorgu=3)],
            [dict(K[0], adim=True)], [dict(K[0], adim=2.0)], [dict(K[0], adim=-1)],
            [dict(K[0], sorgu=True)], [dict(K[0], sorgu=12.0)], [dict(K[0], sorgu=0)], [dict(K[0], sorgu=-1)],
            [dict(K[0], kayip=True)], [dict(K[0], kayip="0.3")], [dict(K[0], kayip=float("nan"))],
            [dict(K[0], kayip=float("inf"))], [dict(K[0], kayip=-0.1)], [dict(K[0], kayip=1.1)],
        ]:
            try:
                fn(kayitlar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(arama_izini_ozetle), "arama izi, bütçe, en iyi adım ve sıralama korunmalı")
def m_kayip(kayitlar):
    return arama_izini_ozetle([dict(x, kayip=0.9) for x in kayitlar])
def m_sorgu(kayitlar):
    return arama_izini_ozetle([dict(x, sorgu=1) for x in kayitlar])
def m_adim(kayitlar):
    return arama_izini_ozetle([dict(x, adim=0) for x in kayitlar])
for ad, mutant in [("kayıpları silen", m_kayip), ("sorguları silen", m_sorgu), ("adımları silen", m_adim)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def arama_izini_ozetle(kayitlar):
    import math
    if not isinstance(kayitlar, list):
        raise ValueError("kayıtlar liste olmalı")
    if not kayitlar:
        raise ValueError("kayıtlar boş olamaz")
    ciftler = set()
    for kayit in kayitlar:
        if not isinstance(kayit, dict):
            raise ValueError("kayıt sözlük olmalı")
        if set(kayit) != {"yontem", "adim", "sorgu", "kayip"}:
            raise ValueError("kayıt şeması geçersiz")
        if kayit["yontem"] not in ("GCG", "AutoDAN"):
            raise ValueError("yöntem geçersiz")
        adim = kayit["adim"]
        if isinstance(adim, bool):
            raise ValueError("adım tamsayı olmalı")
        if not isinstance(adim, int):
            raise ValueError("adım tamsayı olmalı")
        if adim < 0:
            raise ValueError("adım negatif olamaz")
        sorgu = kayit["sorgu"]
        if isinstance(sorgu, bool):
            raise ValueError("sorgu tamsayı olmalı")
        if not isinstance(sorgu, int):
            raise ValueError("sorgu tamsayı olmalı")
        if sorgu <= 0:
            raise ValueError("sorgu pozitif olmalı")
        kayip = kayit["kayip"]
        if isinstance(kayip, bool):
            raise ValueError("kayıp sayı olmalı")
        if not isinstance(kayip, (int, float)):
            raise ValueError("kayıp sayı olmalı")
        if not math.isfinite(kayip):
            raise ValueError("kayıp sonlu olmalı")
        if kayip < 0 or kayip > 1:
            raise ValueError("kayıp aralık dışında")
        cift = (kayit["yontem"], adim)
        if cift in ciftler:
            raise ValueError("yöntem ve adım çifti yinelenemez")
        ciftler.add(cift)
    sirali = sorted(kayitlar, key=lambda x: (x["yontem"], x["adim"]))
    onceki = {}
    for kayit in sirali:
        yontem = kayit["yontem"]
        if yontem in onceki and kayit["sorgu"] <= onceki[yontem]:
            raise ValueError("kümülatif sorgu katı artmalı")
        onceki[yontem] = kayit["sorgu"]
    ozet = []
    for yontem in sorted({x["yontem"] for x in kayitlar}):
        grup = [x for x in sirali if x["yontem"] == yontem]
        en_iyi = min(grup, key=lambda x: (x["kayip"], x["adim"]))
        ozet.append({"yontem": yontem, "en_iyi_adim": en_iyi["adim"], "en_iyi_kayip": round(en_iyi["kayip"], 6), "toplam_sorgu": grup[-1]["sorgu"]})
    return ozet
```

```hint
Önce kayıtları doğrula, sonra yöntem ve adıma göre sıralayıp sorgu artışını denetle. En iyi adımı `(kayıp, adım)` anahtarıyla seç.
```
:::

::: gorev 3 · Transfer başarısını ve yeteneği raporla
`transfer_ozeti(kayitlar)` işlevini yaz. Kayıtlar boş olmayan listedir; her kayıt tam olarak `yontem`, `hedef`, `sorgu`, `basari`, `yetenek` alanlarını taşır. Yöntem yalnız `GCG` veya `AutoDAN`; hedef 1–64 karakterlik, ASCII harf/rakamla başlayan ve yalnız ASCII harf, rakam, alt çizgi veya tire içeren stringdir. Sorgu bool olmayan pozitif tamsayı, başarı bool, yetenek bool olmayan sonlu sayı ve `[0,1]` aralığındadır. Geçersiz veride `ValueError` yükselt.

Her yöntem için `{"yontem":Y,"deneme":N,"basari":N,"transfer_orani":X,"toplam_sorgu":N,"ortalama_yetenek":X}` döndür. Transfer oranı başarı/deneme, ortalama yetenek bütün denemelerin yetenek ortalamasıdır; ikisini de altı ondalık basamağa yuvarla. Özeti yöntem adına göre sırala ve girdiyi değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-09")
```

```starter
from ai_guvence_veri import json_yukle

def transfer_ozeti(kayitlar):
    # KUSURLU BAŞLANGIÇ KODU: transfer oranını ve ortalama yeteneği hesaplamadan sabit sıfır döndürür.
    return [{"yontem": k["yontem"], "deneme": 1, "basari": 0, "transfer_orani": 0.0, "toplam_sorgu": 0, "ortalama_yetenek": 0.0} for k in kayitlar[:1]]

v = json_yukle("veri/optimizasyon.json")["transfer_kayitlari"]
print("Transfer özeti örneği:", transfer_ozeti(v))
```

```test
import copy
K = [
    {"yontem": "GCG", "hedef": "model-a", "sorgu": 4, "basari": True, "yetenek": 0.8},
    {"yontem": "AutoDAN", "hedef": "model-a", "sorgu": 3, "basari": False, "yetenek": 0.9},
    {"yontem": "GCG", "hedef": "model-b", "sorgu": 5, "basari": False, "yetenek": 0.6},
    {"yontem": "GCG", "hedef": "model-c", "sorgu": 6, "basari": True, "yetenek": 0.7},
    {"yontem": "AutoDAN", "hedef": "model-b", "sorgu": 2, "basari": True, "yetenek": 0.6},
]
BEKLENEN = [
    {"yontem": "AutoDAN", "deneme": 2, "basari": 1, "transfer_orani": 0.5, "toplam_sorgu": 5, "ortalama_yetenek": 0.75},
    {"yontem": "GCG", "deneme": 3, "basari": 2, "transfer_orani": 0.666667, "toplam_sorgu": 15, "ortalama_yetenek": 0.7},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        if fn(K) != BEKLENEN or K != once:
            return False
        sinir = fn([{"yontem": "GCG", "hedef": "a" * 64, "sorgu": 1, "basari": False, "yetenek": 0}, {"yontem": "GCG", "hedef": "b", "sorgu": 1, "basari": False, "yetenek": 1}, {"yontem": "GCG", "hedef": "c", "sorgu": 1, "basari": False, "yetenek": 0}])
        if sinir != [{"yontem": "GCG", "deneme": 3, "basari": 0, "transfer_orani": 0.0, "toplam_sorgu": 3, "ortalama_yetenek": 0.333333}]:
            return False
        for kayitlar in [
            None, tuple(K), {}, [], [None], [dict(K[0], ek=1)], [dict(K[0], hedef=123)], [dict(K[0], yontem="diğer")],
            [dict(K[0], hedef="")], [dict(K[0], hedef="a b")], [dict(K[0], hedef="a" * 65)], [dict(K[0], hedef=None)],
            [dict(K[0], sorgu=True)], [dict(K[0], sorgu=4.0)], [dict(K[0], sorgu=0)], [dict(K[0], sorgu=-1)],
            [dict(K[0], basari=1)], [dict(K[0], basari="true")], [dict(K[0], basari=None)],
            [dict(K[0], yetenek=True)], [dict(K[0], yetenek="0.8")], [dict(K[0], yetenek=float("nan"))],
            [dict(K[0], yetenek=float("inf"))], [dict(K[0], yetenek=-0.1)], [dict(K[0], yetenek=1.1)],
        ]:
            try:
                fn(kayitlar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(transfer_ozeti), "transfer oranı, başarı türü, bütçe ve yetenek korunmalı")
def m_basari(kayitlar):
    return transfer_ozeti([dict(x, basari=False) for x in kayitlar])
def m_sorgu(kayitlar):
    return transfer_ozeti([dict(x, sorgu=1) for x in kayitlar])
def m_yetenek(kayitlar):
    return transfer_ozeti([dict(x, yetenek=0) for x in kayitlar])
for ad, mutant in [("başarıları silen", m_basari), ("sorguları silen", m_sorgu), ("yeteneği silen", m_yetenek)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def transfer_ozeti(kayitlar):
    import math
    import re
    if not isinstance(kayitlar, list):
        raise ValueError("kayıtlar liste olmalı")
    if not kayitlar:
        raise ValueError("kayıtlar boş olamaz")
    for kayit in kayitlar:
        if not isinstance(kayit, dict):
            raise ValueError("kayıt sözlük olmalı")
        if set(kayit) != {"yontem", "hedef", "sorgu", "basari", "yetenek"}:
            raise ValueError("kayıt şeması geçersiz")
        if kayit["yontem"] not in ("GCG", "AutoDAN"):
            raise ValueError("yöntem geçersiz")
        if not isinstance(kayit["hedef"], str):
            raise ValueError("hedef string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["hedef"]):
            raise ValueError("hedef geçersiz")
        sorgu = kayit["sorgu"]
        if isinstance(sorgu, bool):
            raise ValueError("sorgu tamsayı olmalı")
        if not isinstance(sorgu, int):
            raise ValueError("sorgu tamsayı olmalı")
        if sorgu <= 0:
            raise ValueError("sorgu pozitif olmalı")
        if not isinstance(kayit["basari"], bool):
            raise ValueError("başarı bool olmalı")
        yetenek = kayit["yetenek"]
        if isinstance(yetenek, bool):
            raise ValueError("yetenek sayı olmalı")
        if not isinstance(yetenek, (int, float)):
            raise ValueError("yetenek sayı olmalı")
        if not math.isfinite(yetenek):
            raise ValueError("yetenek sonlu olmalı")
        if yetenek < 0 or yetenek > 1:
            raise ValueError("yetenek aralık dışında")
    ozet = []
    for yontem in sorted({x["yontem"] for x in kayitlar}):
        grup = [x for x in kayitlar if x["yontem"] == yontem]
        basari = sum(1 for x in grup if x["basari"])
        ozet.append({"yontem": yontem, "deneme": len(grup), "basari": basari, "transfer_orani": round(basari / len(grup), 6), "toplam_sorgu": sum(x["sorgu"] for x in grup), "ortalama_yetenek": round(sum(x["yetenek"] for x in grup) / len(grup), 6)})
    return ozet
```

```hint
Yöntem gruplarını oluştur; başarıları yalnız bool alanından say. Oran ve ortalamada grup büyüklüğünü payda olarak kullan.
```
:::

::: anlat Gerçek dil modelinde (SmolLM2-135M + torch) koordinat gradyanı ile ayrık sonek araması
İlk üç görevde ayrık aday seçimini, arama izi özetini ve transfer raporunu deterministik fixture'lar üzerinde doğruladın. Şimdi aynı üç işlevi **gerçek `SmolLM2-135M` nedensel dil modeli** (`ai_lab.dil_modeli()`) ve `torch` (`ai_lab.torch_cihazi()`) üzerinde çalışan canlı bir GCG koordinat gradyanı deneyine bağlıyoruz:

1. **embedding Gradyanının Hesaplanması:** Girdi dizgisine eklenen sonekin her token konumu için, modelin embedding katmanındaki tek-sıcak (one-hot) tensör temsilleri üzerinden hedef `PAFTA` tokenının negatif log-olabilirlik (çapraz entropi) kaybı $\mathcal{L}$ türetilir. PyTorch `backward()` çağrısı ile son sonek konumundaki gradyan $\nabla_{e} \mathcal{L}$ alınır.
2. **Koordinat Gradyanı Skoru ve Aday Seçimi:** Modelin tüm sözlük embedding matrisi $W_E \in \mathbb{R}^{V \times d}$ ile bu gradyanın iç çarpımı alınarak sözlükteki $V$ adet tokenin birinci derece Taylor kaybı yaklaşık olarak tahmin edilir: $\text{skor}(v) = - W_E[v] \cdot \nabla_{e} \mathcal{L}$. `ayrik_adaylari_sec` işlevi en düşük skorlu aday tokenları belirlenen bütçeyle (örneğin top-k aday) süzer.
3. **İleri Geçiş (Forward Pass) ile Gerçek Kayıp Ölçümü:** Seçilen en umut verici aday tokenlar tek tek veya toplu olarak soneke yerleştirilerek modelde gerçek ileri geçiş koşturulur. Gerçek çapraz entropi kaybını en çok düşüren token kalıcı olarak kabul edilir.
4. **İz ve Transfer Kaydı:** Adımlar boyunca elde edilen kayıp eğrileri ve hedef denemeleri `arama_izini_ozetle` ve `transfer_ozeti` ile yapısal bir rapora dönüştürülüp `kanit_yaz` ile kaydedilir. Bu deney, sürekli gradyan uzayından ayrık dil uzayına geçişin pratik mekaniğini doğrudan doğrular.
:::

::: gorev Gerçek deney · SmolLM2-135M üzerinde GCG koordinat gradyanı ve ayrık sonek araması
Önceki üç görevde yazdığın `ayrik_adaylari_sec(adaylar, butce)`, `arama_izini_ozetle(kayitlar)` ve `transfer_ozeti(kayitlar)` işlevlerini burada birleştir.

```meta
motor: ai-gercek
gereksinim: torch
ortam: gpu
timeout: 300
```

```starter
import math
import re
import ai_lab
from sandbox import ai_gercek_ai_guvence_09 as L

def ayrik_adaylari_sec(adaylar, butce):
    # KUSURLU BAŞLANGIÇ KODU: skor sırasına bakmadan ilk adayı döndürüyor!
    return [adaylar[0]["token"]] if adaylar else []

def arama_izini_ozetle(kayitlar):
    # KUSURLU BAŞLANGIÇ KODU: yöntemleri gruplamadan boş liste döndürüyor!
    return []

def transfer_ozeti(kayitlar):
    # KUSURLU BAŞLANGIÇ KODU: transfer oranını hesaplamadan boş liste döndürüyor!
    return []

if ai_lab.CALISTIR:
    L.goster(ayrik_adaylari_sec, arama_izini_ozetle, transfer_ozeti)
```

```test
import ast
import copy
import ai_lab
from sandbox import ai_gercek_ai_guvence_09 as L

checks = []
_base_ok = ok
def ok(kosul, mesaj):
    checks.append(bool(kosul))
    return _base_ok(kosul, mesaj)

for s in ai_lab.kod_denetimi(src, yasak=("ayrik_adaylari_sec_referans", "arama_izini_ozetle_referans", "transfer_ozeti_referans", "kanit_yaz", "getattr")):
    ok(False, f"Güvenlik/kopya denetimi: {s}")
def ast_denetle(kaynak):
    try:
        agac = ast.parse(kaynak)
    except Exception:
        return False
    for dugum in ast.walk(agac):
        if isinstance(dugum, ast.ImportFrom):
            if any(a.name == "*" for a in dugum.names):
                return False
            if dugum.module and any(x in dugum.module for x in ("referans", "ai_gercek")):
                return False
        if isinstance(dugum, ast.Import):
            if any(any(x in a.name for x in ("referans", "ai_gercek")) for a in dugum.names):
                return False
        if isinstance(dugum, ast.Name) and "referans" in dugum.id.lower():
            return False
        if isinstance(dugum, ast.Attribute) and "referans" in dugum.attr.lower():
            return False
        if isinstance(dugum, ast.Call):
            if isinstance(dugum.func, ast.Name) and dugum.func.id in ("getattr", "eval", "exec"):
                return False
    return True
ok(ast_denetle(src), "kod referans çözüme doğrudan veya dolaylı erişmemeli")
if not all(checks):
    stop()

def _sozlesme_kontrol():
    try:
        adaylar = [{"token": 41, "skor": 0.4}, {"token": 7, "skor": 0.2}, {"token": 19, "skor": 0.2}, {"token": 3, "skor": 0.9}]
        if ayrik_adaylari_sec(adaylar, 2) != [7, 19] or ayrik_adaylari_sec(adaylar, 10) != [7, 19, 41, 3]:
            return False
        for ba, bb in [(None, 1), ([], 1), ([adaylar[0], adaylar[0]], 2), (adaylar, 0), (adaylar, True), ([dict(adaylar[0], token=-1)], 1)]:
            try:
                ayrik_adaylari_sec(ba, bb)
                return False
            except ValueError:
                pass

        iz = [
            {"yontem": "GCG", "adim": 2, "sorgu": 12, "kayip": 0.3},
            {"yontem": "AutoDAN", "adim": 0, "sorgu": 3, "kayip": 0.7},
            {"yontem": "GCG", "adim": 0, "sorgu": 4, "kayip": 0.8},
            {"yontem": "GCG", "adim": 1, "sorgu": 8, "kayip": 0.4},
            {"yontem": "AutoDAN", "adim": 1, "sorgu": 6, "kayip": 0.5},
        ]
        bek_iz = [
            {"yontem": "AutoDAN", "en_iyi_adim": 1, "en_iyi_kayip": 0.5, "toplam_sorgu": 6},
            {"yontem": "GCG", "en_iyi_adim": 2, "en_iyi_kayip": 0.3, "toplam_sorgu": 12},
        ]
        if arama_izini_ozetle(iz) != bek_iz:
            return False
        for biz in [None, [], [iz[0], iz[0]], [iz[2], dict(iz[3], sorgu=4)], [dict(iz[0], kayip=1.2)], [dict(iz[0], yontem="x")]]:
            try:
                arama_izini_ozetle(biz)
                return False
            except ValueError:
                pass

        tr = [
            {"yontem": "GCG", "hedef": "model-a", "sorgu": 4, "basari": True, "yetenek": 0.8},
            {"yontem": "AutoDAN", "hedef": "model-a", "sorgu": 3, "basari": False, "yetenek": 0.9},
            {"yontem": "GCG", "hedef": "model-b", "sorgu": 5, "basari": False, "yetenek": 0.6},
            {"yontem": "GCG", "hedef": "model-c", "sorgu": 6, "basari": True, "yetenek": 0.7},
            {"yontem": "AutoDAN", "hedef": "model-b", "sorgu": 2, "basari": True, "yetenek": 0.6},
        ]
        bek_tr = [
            {"yontem": "AutoDAN", "deneme": 2, "basari": 1, "transfer_orani": 0.5, "toplam_sorgu": 5, "ortalama_yetenek": 0.75},
            {"yontem": "GCG", "deneme": 3, "basari": 2, "transfer_orani": 0.666667, "toplam_sorgu": 15, "ortalama_yetenek": 0.7},
        ]
        if transfer_ozeti(tr) != bek_tr:
            return False
        for btr in [None, [], [dict(tr[0], basari=1)], [dict(tr[0], hedef="a b")], [dict(tr[0], sorgu=0)]]:
            try:
                transfer_ozeti(btr)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

def _birim1(fn):
    import copy
    A = [
        {"token": 41, "skor": 0.4},
        {"token": 7, "skor": 0.2},
        {"token": 19, "skor": 0.2},
        {"token": 3, "skor": 0.9},
    ]
    def sozlesme(fn):
        try:
            once = copy.deepcopy(A)
            if fn(A, 2) != [7, 19] or A != once:
                return False
            if fn(A, 10) != [7, 19, 41, 3] or fn(A, 1) != [7]:
                return False
            if fn([{"token": 0, "skor": -1}, {"token": 2, "skor": 0}], 1) != [0]:
                return False
            for adaylar, butce in [
                (None, 1), (tuple(A), 1), ({}, 1), ([], 1), ([None], 1), ([dict(A[0], ek=1)], 1),
                ([dict(A[0], token=True)], 1), ([dict(A[0], token=1.0)], 1), ([dict(A[0], token=-1)], 1),
                ([A[0], A[0]], 2), ([dict(A[0], skor=True)], 1), ([dict(A[0], skor="0.4")], 1),
                ([dict(A[0], skor=float("nan"))], 1), ([dict(A[0], skor=float("inf"))], 1),
                (A, 0), (A, -1), (A, True), (A, 1.0), (A, None),
            ]:
                try:
                    fn(adaylar, butce)
                    return False
                except ValueError:
                    pass
            return True
        except Exception:
            return False
    return sozlesme(fn)

def _birim2(fn):
    import copy
    K = [
        {"yontem": "GCG", "adim": 2, "sorgu": 12, "kayip": 0.3},
        {"yontem": "AutoDAN", "adim": 0, "sorgu": 3, "kayip": 0.7},
        {"yontem": "GCG", "adim": 0, "sorgu": 4, "kayip": 0.8},
        {"yontem": "GCG", "adim": 1, "sorgu": 8, "kayip": 0.4},
        {"yontem": "AutoDAN", "adim": 1, "sorgu": 6, "kayip": 0.5},
    ]
    BEKLENEN = [
        {"yontem": "AutoDAN", "en_iyi_adim": 1, "en_iyi_kayip": 0.5, "toplam_sorgu": 6},
        {"yontem": "GCG", "en_iyi_adim": 2, "en_iyi_kayip": 0.3, "toplam_sorgu": 12},
    ]
    def sozlesme(fn):
        try:
            once = copy.deepcopy(K)
            if fn(K) != BEKLENEN or K != once:
                return False
            esit = fn([K[2], dict(K[3], kayip=0.8), dict(K[0], kayip=0.8)])
            if esit[0]["en_iyi_adim"] != 0 or esit[0]["toplam_sorgu"] != 12:
                return False
            sinir = fn([{"yontem": "GCG", "adim": 0, "sorgu": 1, "kayip": 0}, {"yontem": "GCG", "adim": 1, "sorgu": 2, "kayip": 1}])
            if sinir[0]["en_iyi_adim"] != 0:
                return False
            yuvarla = fn([{"yontem": "GCG", "adim": 0, "sorgu": 1, "kayip": 1 / 6}])
            if yuvarla[0]["en_iyi_kayip"] != 0.166667:
                return False
            for kayitlar in [
                None, tuple(K), {}, [], [None], [dict(K[0], ek=1)], [dict(K[0], yontem="gcg")], [dict(K[0], yontem=None)],
                [K[0], K[0]], [K[0], dict(K[0], sorgu=20)], [K[2], dict(K[3], sorgu=4)], [K[2], dict(K[3], sorgu=3)],
                [dict(K[0], adim=True)], [dict(K[0], adim=2.0)], [dict(K[0], adim=-1)],
                [dict(K[0], sorgu=True)], [dict(K[0], sorgu=12.0)], [dict(K[0], sorgu=0)], [dict(K[0], sorgu=-1)],
                [dict(K[0], kayip=True)], [dict(K[0], kayip="0.3")], [dict(K[0], kayip=float("nan"))],
                [dict(K[0], kayip=float("inf"))], [dict(K[0], kayip=-0.1)], [dict(K[0], kayip=1.1)],
            ]:
                try:
                    fn(kayitlar)
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
        {"yontem": "GCG", "hedef": "model-a", "sorgu": 4, "basari": True, "yetenek": 0.8},
        {"yontem": "AutoDAN", "hedef": "model-a", "sorgu": 3, "basari": False, "yetenek": 0.9},
        {"yontem": "GCG", "hedef": "model-b", "sorgu": 5, "basari": False, "yetenek": 0.6},
        {"yontem": "GCG", "hedef": "model-c", "sorgu": 6, "basari": True, "yetenek": 0.7},
        {"yontem": "AutoDAN", "hedef": "model-b", "sorgu": 2, "basari": True, "yetenek": 0.6},
    ]
    BEKLENEN = [
        {"yontem": "AutoDAN", "deneme": 2, "basari": 1, "transfer_orani": 0.5, "toplam_sorgu": 5, "ortalama_yetenek": 0.75},
        {"yontem": "GCG", "deneme": 3, "basari": 2, "transfer_orani": 0.666667, "toplam_sorgu": 15, "ortalama_yetenek": 0.7},
    ]
    def sozlesme(fn):
        try:
            once = copy.deepcopy(K)
            if fn(K) != BEKLENEN or K != once:
                return False
            sinir = fn([{"yontem": "GCG", "hedef": "a" * 64, "sorgu": 1, "basari": False, "yetenek": 0}, {"yontem": "GCG", "hedef": "b", "sorgu": 1, "basari": False, "yetenek": 1}, {"yontem": "GCG", "hedef": "c", "sorgu": 1, "basari": False, "yetenek": 0}])
            if sinir != [{"yontem": "GCG", "deneme": 3, "basari": 0, "transfer_orani": 0.0, "toplam_sorgu": 3, "ortalama_yetenek": 0.333333}]:
                return False
            for kayitlar in [
                None, tuple(K), {}, [], [None], [dict(K[0], ek=1)], [dict(K[0], hedef=123)], [dict(K[0], yontem="diğer")],
                [dict(K[0], hedef="")], [dict(K[0], hedef="a b")], [dict(K[0], hedef="a" * 65)], [dict(K[0], hedef=None)],
                [dict(K[0], sorgu=True)], [dict(K[0], sorgu=4.0)], [dict(K[0], sorgu=0)], [dict(K[0], sorgu=-1)],
                [dict(K[0], basari=1)], [dict(K[0], basari="true")], [dict(K[0], basari=None)],
                [dict(K[0], yetenek=True)], [dict(K[0], yetenek="0.8")], [dict(K[0], yetenek=float("nan"))],
                [dict(K[0], yetenek=float("inf"))], [dict(K[0], yetenek=-0.1)], [dict(K[0], yetenek=1.1)],
            ]:
                try:
                    fn(kayitlar)
                    return False
                except ValueError:
                    pass
            return True
        except Exception:
            return False
    return sozlesme(fn)

ok(_birim1(ayrik_adaylari_sec), "ayrik_adaylari_sec tam birim sözleşmesini geçmeli")
ok(_birim2(arama_izini_ozetle), "arama_izini_ozetle tam birim sözleşmesini geçmeli")
ok(_birim3(transfer_ozeti), "transfer_ozeti tam birim sözleşmesini geçmeli")
ok(_sozlesme_kontrol(), "ayrik_adaylari_sec, arama_izini_ozetle ve transfer_ozeti sözleşme ve sınır kontrollerini geçmeli")
if not all(checks):
    stop()

try:
    rapor = L.deney(ayrik_adaylari_sec, arama_izini_ozetle, transfer_ozeti)
except ai_lab.GercekLabYok as e:
    ok(False, str(e))
    stop()
except Exception as e:
    ok(False, f"GERÇEK GCG SONEK ARAMASI DENEYİ YAPILAMADI: {type(e).__name__}: {e}")
    stop()

k = rapor["kontroller"]
ok(k["aday_secimi_uyumu"], f"ayrik_adaylari_sec gerçek gradyan skorlarında referansla uyuşmalı: {rapor['secilen_tokenlar']}")
ok(k["arama_izi_uyumu"], f"arama_izini_ozetle canlı ileri geçiş kayıplarında referansla uyuşmalı: {rapor['iz_ozeti']}")
ok(k["transfer_ozeti_uyumu"], f"transfer_ozeti canlı kayıtlarda referansla uyuşmalı: {rapor['transfer_ozeti']}")
ok(k["gercek_gradyan_ve_kayip_olculdu"], f"SmolLM2-135M üzerinde gerçek gradyan ve kayıp ölçülmeli: {rapor['ozet']}")

kabul = all(checks)
kanit_yolu = ai_lab.kanit_yaz("guvence-09-gcg-autodan", dict(rapor, kaynak="gercek", kabul=kabul))
o = rapor["ozet"]
print(f"GERÇEK GCG DENEYİ: model={o['model']} cihaz={o['cihaz']} secilen={o['secilen_tokenlar']} iz={o['iz_ozeti']} kanıt={kanit_yolu}")
```

```solution
import math
import re
import ai_lab
from sandbox import ai_gercek_ai_guvence_09 as L

def ayrik_adaylari_sec(adaylar, butce):
    if not isinstance(adaylar, list) or not adaylar:
        raise ValueError("adaylar geçersiz")
    if isinstance(butce, bool) or not isinstance(butce, int) or butce <= 0:
        raise ValueError("bütçe geçersiz")
    tokenlar = set()
    for aday in adaylar:
        if not isinstance(aday, dict) or set(aday) != {"token", "skor"}:
            raise ValueError("aday şeması geçersiz")
        token = aday["token"]
        if isinstance(token, bool) or not isinstance(token, int) or token < 0 or token in tokenlar:
            raise ValueError("token geçersiz")
        skor = aday["skor"]
        if isinstance(skor, bool) or not isinstance(skor, (int, float)) or not math.isfinite(skor):
            raise ValueError("skor geçersiz")
        tokenlar.add(token)
    sirali = sorted(adaylar, key=lambda x: (x["skor"], x["token"]))
    return [x["token"] for x in sirali[:butce]]

def arama_izini_ozetle(kayitlar):
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar geçersiz")
    ciftler = set()
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"yontem", "adim", "sorgu", "kayip"}:
            raise ValueError("kayıt şeması geçersiz")
        if kayit["yontem"] not in ("GCG", "AutoDAN"):
            raise ValueError("yöntem geçersiz")
        adim = kayit["adim"]
        if isinstance(adim, bool) or not isinstance(adim, int) or adim < 0:
            raise ValueError("adım geçersiz")
        sorgu = kayit["sorgu"]
        if isinstance(sorgu, bool) or not isinstance(sorgu, int) or sorgu <= 0:
            raise ValueError("sorgu geçersiz")
        kayip = kayit["kayip"]
        if isinstance(kayip, bool) or not isinstance(kayip, (int, float)) or not math.isfinite(kayip) or kayip < 0 or kayip > 1:
            raise ValueError("kayıp geçersiz")
        cift = (kayit["yontem"], adim)
        if cift in ciftler:
            raise ValueError("yinelenen adım")
        ciftler.add(cift)
    sirali = sorted(kayitlar, key=lambda x: (x["yontem"], x["adim"]))
    onceki = {}
    for kayit in sirali:
        yontem = kayit["yontem"]
        if yontem in onceki and kayit["sorgu"] <= onceki[yontem]:
            raise ValueError("kümülatif sorgu katı artmalı")
        onceki[yontem] = kayit["sorgu"]
    ozet = []
    for yontem in sorted({x["yontem"] for x in kayitlar}):
        grup = [x for x in sirali if x["yontem"] == yontem]
        en_iyi = min(grup, key=lambda x: (x["kayip"], x["adim"]))
        ozet.append({"yontem": yontem, "en_iyi_adim": en_iyi["adim"], "en_iyi_kayip": round(en_iyi["kayip"], 6), "toplam_sorgu": grup[-1]["sorgu"]})
    return ozet

def transfer_ozeti(kayitlar):
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar geçersiz")
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"yontem", "hedef", "sorgu", "basari", "yetenek"}:
            raise ValueError("kayıt şeması geçersiz")
        if kayit["yontem"] not in ("GCG", "AutoDAN"):
            raise ValueError("yöntem geçersiz")
        if not isinstance(kayit["hedef"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["hedef"]):
            raise ValueError("hedef geçersiz")
        sorgu = kayit["sorgu"]
        if isinstance(sorgu, bool) or not isinstance(sorgu, int) or sorgu <= 0:
            raise ValueError("sorgu geçersiz")
        if not isinstance(kayit["basari"], bool):
            raise ValueError("başarı bool olmalı")
        yetenek = kayit["yetenek"]
        if isinstance(yetenek, bool) or not isinstance(yetenek, (int, float)) or not math.isfinite(yetenek) or yetenek < 0 or yetenek > 1:
            raise ValueError("yetenek geçersiz")
    ozet = []
    for yontem in sorted({x["yontem"] for x in kayitlar}):
        grup = [x for x in kayitlar if x["yontem"] == yontem]
        basari = sum(1 for x in grup if x["basari"])
        ozet.append({"yontem": yontem, "deneme": len(grup), "basari": basari, "transfer_orani": round(basari / len(grup), 6), "toplam_sorgu": sum(x["sorgu"] for x in grup), "ortalama_yetenek": round(sum(x["yetenek"] for x in grup) / len(grup), 6)})
    return ozet

if ai_lab.CALISTIR:
    L.goster(ayrik_adaylari_sec, arama_izini_ozetle, transfer_ozeti)
```

```hint
Önceki üç görevde yazdığın `ayrik_adaylari_sec`, `arama_izini_ozetle` ve `transfer_ozeti` işlevlerini eksiksiz taşı; canlı deneyde SmolLM2-135M üzerinde koordinat gradyanı ve ileri geçiş kayıpları hesaplanır.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Sürekli gradyandan ayrık sözlüğe geçiş (`GCG`) (30 sn).** "Dil modellerinde pikseller gibi sürekli adım atılamaz; `GCG`, gömme gradyanıyla sözlükteki tüm tokenların birinci derece Taylor skorunu hesaplar, en umut verici `top-B` adayı seçer ve gerçek ileri geçiş kaybıyla doğrular."
2. **Arama maliyeti ve sorgu bütçesi (35 sn).** "En düşük kayıp tek başına yeterli değildir; adımlar boyunca kümülatif sorgu sayısının nasıl büyüdüğü saldırının hız sınırları altındaki gerçek maliyetini belirler."
3. **Kara kutu transferi ve okunabilirlik (`AutoDAN`) (30 sn).** "Açık ağırlıklı bir modelde bulunan sonek kapalı modellere transfer edilebilir; `AutoDAN` ise şaşkınlık (`perplexity`) filtrelerine yakalanmamak için akıcı dil yapısını koruyan genetik arama yürütür."
4. **Soru (25 sn).** "Birinci derece gradyan skoru en negatif çıkan aday token neden her zaman gerçek ileri geçişte de en düşük çapraz entropi kaybını vermez?"
:::
