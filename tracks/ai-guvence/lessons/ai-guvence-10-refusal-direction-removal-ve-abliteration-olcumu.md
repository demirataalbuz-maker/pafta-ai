---
id: ai-guvence-10
title: Refusal Direction Removal ve Abliteration Ölçümü
summary: Ortogonal projeksiyonun matematiğini uygula, güvenlik ve genel yetenek etkisini taban karşılaştırmasıyla ölç ve sonda TransformerLens + torch ile Qwen2.5-0.5B-Instruct üzerinde canlı abliteration deneyi yürüt.
esleme: ai-guvence-06, ai-guvence-41, ai-guvence-43
timeout: 300
---

::: anlat Yön çıkarma bir projeksiyon işlemidir

| Gerçek araç / model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| TransformerLens / PyTorch kancaları residual stream aktivasyon tensorlerini ve refusal yönünü çıkarır | İlk 3 görev saf Python normalizasyonu, ortogonal projeksiyon formülü ve iki eksenli ablasyon karşılaştırması | Büyük dil modellerinde tüm güvenlik mekanizmalarının tek bir vektöre indirgenebileceği veya kalıcı güvenlik garantisi değildir |
| Qwen2.5-0.5B-Instruct yerel ağırlıkları katman 14 forward hook ile canlı refusal yönü ablasyonunu uygular | Gerçek deney TransformerLens köprüsü, katman 14 rezidüel kancası, canlı taban/ablite güvenlik ve yetenek ölçümü | Üretim ortamında jailbreak bağışıklığı, zararlı kullanımın tamamen engellendiği veya genel akıl yürütme kaybı olmadığı kanıtı değildir |

> [!NOT]
> `veri/abliteration.json` dosyası sentetik yön vektörü, aktivasyon ve skor kayıtlarını içerir; model ağırlığı veya canlı aktivasyon çıktısı değildir. İlk 3 görev bu yerel fixture verisini okur. Her Run/Check işleminde `hazirla("ai-guvence-10")` geçici kopya oluşturur; kalıcı değişiklik saklanmaz. Kodunuzu veya verinizi editörde inceleyebilirsiniz. Gizli değerlendirme testleri ayrı doğrulamalar koşturur. Gerçek deney adımı yerel PyTorch ve TransformerLens ile Qwen2.5-0.5B-Instruct modelinde katman 14 kancasını doğrudan çalıştırır; yeni paket veya model indirilmez.

Modern büyük dil modellerinde güvenlik hizalaması (RLHF, DPO veya KTO), modelin zararlı, yasa dışı veya etik dışı komutları tespit edip reddetmesini ("I cannot fulfill this request...") sağlar. Son dönem mekanistik yorumlanabilirlik (Mechanistic Interpretability) ve temsil mühendisliği (Representation Engineering; Zou ve ark., 2023; Arditi ve ark., 2024) araştırmaları, bu reddetme mekanizmasının modelin artık akışında (residual stream) çoğunlukla baskın, neredeyse doğrusal tek bir yön (Refusal Direction) boyunca kodlandığını ortaya koymuştur. Model, zararlı bir girdiyle karşılaştığında orta ve geç katmanlardaki aktivasyonlarını bu refusal vektörü doğrultusunda kaydırır; bu kayma nihai logits katmanında standart red şablonlarının olasılığını zirveye taşır.

Matematiksel olarak bir aktivasyon vektöründen ($\mathbf{x} \in \mathbb{R}^d$) bu refusal yönünü ($\mathbf{y} \in \mathbb{R}^d$) silme işlemi bir **Ortogonal Projeksiyon (Orthogonal Projection)** problemidir. İlk adım, hedef yönü birim uzunluğa normalize etmektir:
$$\mathbf{u} = \frac{\mathbf{y}}{\|\mathbf{y}\|_2} = \frac{\mathbf{y}}{\sqrt{\sum_{i=1}^d y_i^2}}$$
Burada $\|\mathbf{y}\|_2 > 0$ olmalıdır; sıfır vektör veya tanımsız değerler matematiksel olarak anlamsızdır. Birim yön $\mathbf{u}$ elde edildikten sonra, aktivasyonun bu doğrultudaki skaler izdüşümü iç çarpım ile hesaplanır: $\text{proj}_{\mathbf{u}}(\mathbf{x}) = (\mathbf{x} \cdot \mathbf{u}) \mathbf{u} = \left(\sum_{i=1}^d x_i u_i\right) \mathbf{u}$. Aktivasyondan bu bileşen çıkarıldığında arta kalan vektör refusal yönüne tam olarak dik (ortogonal) hale gelir:
$$\mathbf{x}_{\text{ablite}} = \mathbf{x} - (\mathbf{x} \cdot \mathbf{u}) \mathbf{u}$$
Böylece aktivasyonun refusal yönündeki iz düşümü ideal olarak sıfırlanırken ($\mathbf{x}_{\text{ablite}} \cdot \mathbf{u} = 0$), diğer tüm anlamsal boyutlar korunur. Bu işleme literatürde **Abliteration (Ablasyon + Obliteration)** adı verilir.
:::

::: anlat Güvenlik etkisi yetenek maliyetinden ayrı raporlanır
Bir modelin güvenlik mekanizmasına müdahale edildiğinde en kritik hata, yalnız red davranışının azalmasına odaklanmaktır. Refusal yönünün residual stream'den çıkarılması, modelin "zararlı talepleri yerine getirmesini" sağlarken aynı zamanda modelin genel dil kabiliyetini, olgusal bilgisini, matematiksel akıl yürütmesini veya kodlama yeteneğini ciddi biçimde bozabilir. Çünkü yüksek boyutlu temsil uzaylarında kavramlar nadiren tamamen bağımsızdır; güvenlik yönü ile genel yetenek yönleri arasında kısmi örtüşmeler (polysemanticity ve interference) mevcuttur.

Bu nedenle abliteration deneyi iki eksenli bir değerlendirme çerçevesiyle yürütülmelidir:
1. **Güvenlik Ekseni (`guvenlik`):** Zararlı veya riskli istemlere karşı modelin doğru davranış sergileme (güvenlik filtrelerini koruma) puanıdır. `guvenlik_degisimi = ablite_guvenlik - taban_guvenlik` formülüyle hesaplanır. Güvenlik değişiminin negatif olması, modelin korumalarının zayıfladığını veya çöktüğünü ifade eder.
2. **Genel Yetenek Ekseni (`yetenek`):** Modelin genel dünya bilgisi ve mantıksal tamamlama performansıdır (örneğin `"The capital of France is" -> "Paris"`). `yetenek_kaybi = taban_yetenek - ablite_yetenek` formülüyle hesaplanır. Yetenek kaybının pozitif olması, müdahalenin modelin genel bilişsel zekâsına zarar verdiğini kanıtlar.

Saldırganlar açık kaynaklı modeller üzerinde şu teknikleri dener:
- **Ağırlık Seviyesinde Abliteration (Weight-Level Uncensoring):** Çıkarım anında kanca takmak yerine modelin ağırlık matrislerine rank-1 güncelleme uygulayarak ($W \leftarrow W - \mathbf{u} \mathbf{u}^T W$) sansürsüz (uncensored) modeller türetmek ve bunları dağıtmak.
- **Kritik Katman Arama:** Modelin tüm katmanlarına müdahale etmek yerine, yetenek kaybının en düşük olduğu ve red sinyalinin en yoğun toplandığı katmanı izole etmek. Bu katman modelden modele değişir ve aday katmanlar taranarak ölçülür; bu dersin gerçek deneyindeki 24 katmanlı Qwen2.5-0.5B için kullanılan katman 14 sabit bir seçimdir, kanıtlanmış en iyi katman değildir.
- **Güvenlik Eğitimi Atlama:** Sistem istemlerini (system prompt) veya ince ayar (fine-tuning) kısıtlamalarını baypas ederek modelin zararlı içerik üretimini zorlamak.

Geliştiricilerin düştüğü başlıca tuzaklar şunlardır:
- Yön vektörünü normalize etmeden ham vektörle çıkarma yapmak; bu durum aktivasyonu anlamsız ölçekte bozarak model çıktısını anlamsız token çorbasına dönüştürür.
- Ara hesaplamalarda iç çarpımı erken yuvarlamak; kayan nokta hassasiyetinin kaybolması ortogonaliteyi bozar. Yuvarlama yalnız en son raporda (`round(x, 6)`) yapılmalıdır.
- Güvenlik değişimi ve yetenek kaybı formüllerindeki işaretleri ters yazmak veya koşul gruplarını (`taban`, `ablite`) birbirine karıştırmak.
- Puanların $[0, 1]$ aralığında sonlu sayılar olduğunu denetlememek veya tek bir koşuldan gelen verilerle ortalama almaya kalkışmak.

Kaynaklar: [Arditi vd. 2024 — Refusal in Language Models Is Mediated by a Single Direction (arXiv:2406.11717)](https://arxiv.org/abs/2406.11717), [Qi vd. 2024 — Fine-tuning Aligned Language Models Compromises Safety (arXiv:2310.03693)](https://arxiv.org/abs/2310.03693).
:::

::: tahmin Projeksiyon ve farkları tahmin et
Üç çıktı satırını yaz:

```python
print(round((3 ** 2 + 4 ** 2) ** 0.5, 6))
print(round(1 - 2.2 * 0.6, 6))
print(round(0.8 - 0.65, 6))
```

???

```cikti
5.0
-0.32
0.15
```

İlk satır yön normunu, ikinci satır projeksiyonun ilk koordinatını, üçüncü satır taban eksi ablite farkını gösterir.
:::

::: gorev 1 · Yön vektörünü normalize et
`yon_normallestir(yon)` işlevini yaz. Yön boş olmayan, bool olmayan sonlu sayılardan oluşan bir listedir. Euclidean normu sıfırdan büyük olmalıdır; sıfır vektör ve geçersiz veri için `ValueError` yükselt.

Her koordinatı norma böl, altı ondalık basamağa yuvarlanmış yeni liste döndür ve girdiyi değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-10")
```

```starter
from ai_guvence_veri import json_yukle

def yon_normallestir(yon):
    # KUSURLU BAŞLANGIÇ KODU: vektörü normalize etmeden sabit 1.0 koordinatları döndürür.
    return [1.0 for _ in yon] if isinstance(yon, list) else []

v = json_yukle("veri/abliteration.json")["yon"]
print("Normalize yön örneği:", yon_normallestir(v))
```

```test
import copy
Y = [3, 4]
def sozlesme(fn):
    try:
        once = copy.deepcopy(Y)
        if fn(Y) != [0.6, 0.8] or Y != once:
            return False
        if fn([-3, 0]) != [-1.0, 0.0] or fn([0, 2]) != [0.0, 1.0]:
            return False
        if fn([1, 1, 1]) != [0.57735, 0.57735, 0.57735] or fn([1, 2]) != [0.447214, 0.894427]:
            return False
        for yon in [None, tuple(Y), {}, [], "12", [None], [True], ["3"], [float("nan")], [float("inf")], [0], [0, 0]]:
            try:
                fn(yon)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(yon_normallestir), "normalizasyon, sıfır norm ve veri kuralları korunmalı")
def m_yon(yon):
    return yon_normallestir([0 for _ in yon])
def m_sil(yon):
    return yon_normallestir(yon[:1])
def m_degistir(yon):
    return yon_normallestir([1 for _ in yon])
for ad, mutant in [("yönü sıfırlayan", m_yon), ("boyutu silen", m_sil), ("değerleri değiştiren", m_degistir)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def yon_normallestir(yon):
    import math
    if not isinstance(yon, list):
        raise ValueError("yön liste olmalı")
    if not yon:
        raise ValueError("yön boş olamaz")
    for deger in yon:
        if isinstance(deger, bool):
            raise ValueError("koordinat sayı olmalı")
        if not isinstance(deger, (int, float)):
            raise ValueError("koordinat sayı olmalı")
        if not math.isfinite(deger):
            raise ValueError("koordinat sonlu olmalı")
    norm = math.sqrt(sum(deger * deger for deger in yon))
    if norm == 0:
        raise ValueError("yön normu pozitif olmalı")
    return [round(deger / norm, 6) for deger in yon]
```

```hint
Normu bütün koordinatların karelerinden hesapla. Bölmeden önce sıfır normu reddet ve yeni liste oluştur.
```
:::

::: gorev 2 · Aktivasyondan yön bileşenini çıkar
`yon_bilesenini_kaldir(x, yon)` işlevini yaz. `x` ve `yon` aynı boyutta, boş olmayan, bool olmayan sonlu sayı listeleridir; yönün Euclidean normu pozitif olmalıdır. Geçersiz veride `ValueError` yükselt ve girdileri değiştirme.

Yönü işlev içinde normalize et. `u` birim yön olmak üzere her koordinatta `x[i]-dot(x,u)*u[i]` hesapla. Projeksiyon sonucunu altı ondalık basamağa yuvarlanmış yeni liste olarak döndür.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-10")
```

```starter
from ai_guvence_veri import json_yukle

def yon_bilesenini_kaldir(x, yon):
    # KUSURLU BAŞLANGIÇ KODU: yön bileşenini çıkarmak yerine aktivasyon vektörünü olduğu gibi döndürür.
    return [round(float(v), 6) for v in x] if isinstance(x, list) else []

v = json_yukle("veri/abliteration.json")
print("Projeksiyon örneği:", yon_bilesenini_kaldir(v["aktivasyon"], v["yon"]))
```

```test
import copy
X = [1, 2]
Y = [3, 4]
def sozlesme(fn):
    try:
        xonce = copy.deepcopy(X)
        yonce = copy.deepcopy(Y)
        if fn(X, Y) != [-0.32, 0.24] or X != xonce or Y != yonce:
            return False
        if fn([2, 1], [0, 5]) != [2.0, 0.0] or fn([-2, 1], [0, 5]) != [-2.0, 0.0]:
            return False
        yuvarla = fn([1, 0], [1, 1, 1][:-1])
        if yuvarla != [0.5, -0.5]:
            return False
        uc = fn([1, 0, 0], [1, 1, 1])
        if uc != [0.666667, -0.333333, -0.333333]:
            return False
        for x, yon in [
            (None, Y), (X, None), (tuple(X), Y), (X, tuple(Y)), ({}, Y), (X, {}), ([], []), ([], Y), (X, []), ([1], Y), (X, [3]),
            ([True, 2], Y), (["1", 2], Y), ([float("nan"), 2], Y), ([float("inf"), 2], Y),
            (X, [True, 4]), (X, ["3", 4]), (X, [float("nan"), 4]), (X, [float("inf"), 4]), (X, [0, 0]),
        ]:
            try:
                fn(x, yon)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(yon_bilesenini_kaldir), "normalizasyon, iç çarpım ve ortogonal projeksiyon korunmalı")
def m_x(x, yon):
    return yon_bilesenini_kaldir([0 for _ in x], yon)
def m_yon(x, yon):
    return yon_bilesenini_kaldir(x, [1 for _ in yon])
def m_boyut(x, yon):
    return yon_bilesenini_kaldir(x[:1], yon)
for ad, mutant in [("aktivasyonu silen", m_x), ("yönü değiştiren", m_yon), ("boyutu bozan", m_boyut)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def yon_bilesenini_kaldir(x, yon):
    import math
    if not isinstance(x, list):
        raise ValueError("vektörler liste olmalı")
    if not isinstance(yon, list):
        raise ValueError("vektörler liste olmalı")
    if not x:
        raise ValueError("vektörler boş olamaz")
    if not yon:
        raise ValueError("vektörler boş olamaz")
    if len(x) != len(yon):
        raise ValueError("vektör boyutları uyuşmuyor")
    for vektor in (x, yon):
        for deger in vektor:
            if isinstance(deger, bool):
                raise ValueError("koordinat sayı olmalı")
            if not isinstance(deger, (int, float)):
                raise ValueError("koordinat sayı olmalı")
            if not math.isfinite(deger):
                raise ValueError("koordinat sonlu olmalı")
    norm = math.sqrt(sum(deger * deger for deger in yon))
    if norm == 0:
        raise ValueError("yön normu pozitif olmalı")
    u = [deger / norm for deger in yon]
    ic_carpim = sum(a * b for a, b in zip(x, u))
    return [round(a - ic_carpim * b, 6) for a, b in zip(x, u)]
```

```hint
Normalize edilmiş yönü ayrı tut. İç çarpımı ham girdiyle hesapla ve yalnız son koordinatları yuvarla.
```
:::

::: gorev 3 · Taban ve ablite koşullarını karşılaştır
`ablite_karsilastirmasi(kayitlar)` işlevini yaz. Kayıtlar boş olmayan listedir; her kayıt tam olarak `kosul`, `guvenlik`, `yetenek` alanlarını taşır. Koşul yalnız `taban` veya `ablite`; iki puan da bool olmayan sonlu sayı ve `[0,1]` aralığındadır. Her iki koşuldan en az bir kayıt bulunmalıdır. Geçersiz veride `ValueError` yükselt.

Her koşulun güvenlik ve yetenek ortalamasını altı ondalık basamağa yuvarla. `{"taban":{"guvenlik":X,"yetenek":X},"ablite":{"guvenlik":X,"yetenek":X},"guvenlik_degisimi":X,"yetenek_kaybi":X}` döndür. Güvenlik değişimi yuvarlanmamış ablite ortalaması eksi taban ortalaması, yetenek kaybı yuvarlanmamış taban ortalaması eksi ablite ortalamasıdır; farkları da altı ondalık basamağa yuvarla. Girdiyi değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-10")
```

```starter
from ai_guvence_veri import json_yukle

def ablite_karsilastirmasi(kayitlar):
    # KUSURLU BAŞLANGIÇ KODU: koşul ayrımı yapmadan sabit sıfır değişim ve kayıp döndürür.
    return {"taban": {"guvenlik": 0.0, "yetenek": 0.0}, "ablite": {"guvenlik": 0.0, "yetenek": 0.0}, "guvenlik_degisimi": 0.0, "yetenek_kaybi": 0.0}

v = json_yukle("veri/abliteration.json")["kayitlar"]
print("Karşılaştırma örneği:", ablite_karsilastirmasi(v))
```

```test
import copy
K = [
    {"kosul": "taban", "guvenlik": 0.8, "yetenek": 0.9},
    {"kosul": "ablite", "guvenlik": 0.4, "yetenek": 0.6},
    {"kosul": "taban", "guvenlik": 0.6, "yetenek": 0.7},
    {"kosul": "ablite", "guvenlik": 0.2, "yetenek": 0.8},
]
BEKLENEN = {"taban": {"guvenlik": 0.7, "yetenek": 0.8}, "ablite": {"guvenlik": 0.3, "yetenek": 0.7}, "guvenlik_degisimi": -0.4, "yetenek_kaybi": 0.1}
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        if fn(K) != BEKLENEN or K != once:
            return False
        sinir = fn([{"kosul": "taban", "guvenlik": 0, "yetenek": 1}, {"kosul": "ablite", "guvenlik": 1, "yetenek": 0}])
        if sinir != {"taban": {"guvenlik": 0, "yetenek": 1}, "ablite": {"guvenlik": 1, "yetenek": 0}, "guvenlik_degisimi": 1, "yetenek_kaybi": 1}:
            return False
        yuvarla = fn([
            {"kosul": "taban", "guvenlik": 1, "yetenek": 1},
            {"kosul": "taban", "guvenlik": 0, "yetenek": 0},
            {"kosul": "taban", "guvenlik": 0, "yetenek": 0},
            {"kosul": "ablite", "guvenlik": 0, "yetenek": 0},
        ])
        if yuvarla["taban"] != {"guvenlik": 0.333333, "yetenek": 0.333333} or yuvarla["guvenlik_degisimi"] != -0.333333 or yuvarla["yetenek_kaybi"] != 0.333333:
            return False
        ablite_yuvarla = fn([
            {"kosul": "taban", "guvenlik": 0, "yetenek": 0},
            {"kosul": "ablite", "guvenlik": 1, "yetenek": 1},
            {"kosul": "ablite", "guvenlik": 0, "yetenek": 0},
            {"kosul": "ablite", "guvenlik": 0, "yetenek": 0},
        ])
        if ablite_yuvarla["ablite"] != {"guvenlik": 0.333333, "yetenek": 0.333333}:
            return False
        for kayitlar in [
            None, tuple(K), {}, [], [None], [dict(K[0], ek=1), K[1]], [K[0], K[1], dict(K[0], kosul="diger")], [K[0], K[1], dict(K[0], kosul=[])],
            [K[0]], [K[1]], [dict(K[0], kosul=None), K[1]],
            [dict(K[0], guvenlik=True), K[1]], [dict(K[0], guvenlik="0.8"), K[1]],
            [dict(K[0], guvenlik=float("nan")), K[1]], [dict(K[0], guvenlik=float("inf")), K[1]],
            [dict(K[0], guvenlik=-0.1), K[1]], [dict(K[0], guvenlik=1.1), K[1]],
            [dict(K[0], yetenek=True), K[1]], [dict(K[0], yetenek="0.9"), K[1]],
            [dict(K[0], yetenek=float("nan")), K[1]], [dict(K[0], yetenek=float("inf")), K[1]],
            [dict(K[0], yetenek=-0.1), K[1]], [dict(K[0], yetenek=1.1), K[1]],
        ]:
            try:
                fn(kayitlar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(ablite_karsilastirmasi), "koşul ortalamaları ve iki eksenli farklar korunmalı")
def m_guvenlik(kayitlar):
    return ablite_karsilastirmasi([dict(x, guvenlik=0) for x in kayitlar])
def m_yetenek(kayitlar):
    return ablite_karsilastirmasi([dict(x, yetenek=0) for x in kayitlar])
def m_kosul(kayitlar):
    return ablite_karsilastirmasi([dict(x, kosul="taban") for x in kayitlar])
for ad, mutant in [("güvenliği silen", m_guvenlik), ("yeteneği silen", m_yetenek), ("koşulları birleştiren", m_kosul)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def ablite_karsilastirmasi(kayitlar):
    import math
    if not isinstance(kayitlar, list):
        raise ValueError("kayıtlar liste olmalı")
    if not kayitlar:
        raise ValueError("kayıtlar boş olamaz")
    for kayit in kayitlar:
        if not isinstance(kayit, dict):
            raise ValueError("kayıt sözlük olmalı")
        if set(kayit) != {"kosul", "guvenlik", "yetenek"}:
            raise ValueError("kayıt şeması geçersiz")
        if kayit["kosul"] not in ("taban", "ablite"):
            raise ValueError("koşul geçersiz")
        for alan in ("guvenlik", "yetenek"):
            deger = kayit[alan]
            if isinstance(deger, bool):
                raise ValueError("puan sayı olmalı")
            if not isinstance(deger, (int, float)):
                raise ValueError("puan sayı olmalı")
            if not math.isfinite(deger):
                raise ValueError("puan sonlu olmalı")
            if deger < 0 or deger > 1:
                raise ValueError("puan aralık dışında")
    kosullar = {x["kosul"] for x in kayitlar}
    if kosullar != {"taban", "ablite"}:
        raise ValueError("iki koşul da gerekli")
    ortalamalar = {}
    for kosul in ("taban", "ablite"):
        grup = [x for x in kayitlar if x["kosul"] == kosul]
        ortalamalar[kosul] = {alan: sum(x[alan] for x in grup) / len(grup) for alan in ("guvenlik", "yetenek")}
    return {
        "taban": {alan: round(deger, 6) for alan, deger in ortalamalar["taban"].items()},
        "ablite": {alan: round(deger, 6) for alan, deger in ortalamalar["ablite"].items()},
        "guvenlik_degisimi": round(ortalamalar["ablite"]["guvenlik"] - ortalamalar["taban"]["guvenlik"], 6),
        "yetenek_kaybi": round(ortalamalar["taban"]["yetenek"] - ortalamalar["ablite"]["yetenek"], 6),
    }
```

```hint
Ham ortalamaları önce ayrı tut. Çıktı ortalamalarını ve farkları aynı ham değerlerden türet; koşul gruplarını karıştırma.
```
:::

::: anlat TransformerLens + PyTorch ile `Qwen2.5-0.5B-Instruct` üzerinde canlı abliteration (ortogonal projeksiyon) deneyi
İlk üç görevde yön normalizasyonunu (`yon_normallestir`), ortogonal projeksiyonu (`yon_bilesenini_kaldir`) ve taban–ablite karşılaştırmasını (`ablite_karsilastirmasi`) deterministik fixture'larda doğruladın. Şimdi aynı üç işlevi **TransformerLens 4.3 (`TransformerBridge.boot_transformers`) ve PyTorch forward hook** ile yerel `Qwen/Qwen2.5-0.5B-Instruct` (`rev: 7ae557604adf67be50417f59c2c2f167def9a775`) modelinde canlı sınamaya bağlıyoruz:

1. Katman 14'teki (`blocks.14.hook_resid_post`) gerçek refusal–normal aktivasyon farkından birim refusal yönü çıkarılır; 8 boyutlu dilimde `yon_normallestir` ve `yon_bilesenini_kaldir` doğrulanır.
2. Katman 14 çıkışına ortogonal projeksiyon (`h - (h·u)u`) uygulayan bir PyTorch forward hook takılarak **taban** ve **ablite** koşullarında hem refusal olasılığı (`guvenlik`) hem de genel bilgi tamamlaması (`"The capital of France is" -> "Paris"`, `yetenek`) ölçülür. PyTorch kancaları (forward hooks), modelin ileri geçişi (forward pass) sırasında residual stream aktivasyon tensorlerini `(batch, seq, d_model)` biçiminde yakalar. Yön vektörü son boyuta (`d_model`) yayınlanarak (broadcasting) her bir token pozisyonu için bağımsız projeksiyon hesaplanır ve model ağırlıkları değiştirilmeksizin çıkarım zamanında (inference-time) dinamik müdahale sağlanır.
3. Canlı ölçümler `ablite_karsilastirmasi` ile özetlenip kanıt dosyasına kaydedilir. Bu deney, abliteration tekniğinin gerçek bir Transformer mimarisi üzerinde nasıl çalıştığını, güvenlik kalkanını ne ölçüde zayıflattığını ve modelin temel olgusal tamamlama yeteneğinde bir regresyona yol açıp açmadığını doğrudan kanıtlar.
:::

::: gorev Gerçek deney · Qwen2.5-0.5B-Instruct üzerinde ortogonal refusal yönü kaldırma (abliteration)
Önceki üç görevde yazdığın `yon_normallestir(yon)`, `yon_bilesenini_kaldir(x, yon)` ve `ablite_karsilastirmasi(kayitlar)` işlevlerini burada birleştir.

```meta
motor: ai-gercek
gereksinim: torch
timeout: 300
```

```starter
import math
import ai_lab
from sandbox import ai_gercek_ai_guvence_10 as L

def yon_normallestir(yon):
    # KUSURLU BAŞLANGIÇ KODU: L2 normuna bölmek yerine olduğu gibi döndürüyor!
    return [round(float(x), 6) for x in yon] if isinstance(yon, list) else []

def yon_bilesenini_kaldir(x, yon):
    return [round(float(v), 6) for v in x] if isinstance(x, list) else []

def ablite_karsilastirmasi(kayitlar):
    return {"taban": {"guvenlik": 0.0, "yetenek": 0.0}, "ablite": {"guvenlik": 0.0, "yetenek": 0.0}, "guvenlik_degisimi": 0.0, "yetenek_kaybi": 0.0}

if ai_lab.CALISTIR:
    L.goster(yon_normallestir, yon_bilesenini_kaldir, ablite_karsilastirmasi)
```

```test
import ast
import copy
import ai_lab
from sandbox import ai_gercek_ai_guvence_10 as L

checks = []
_base_ok = ok
def ok(kosul, mesaj):
    checks.append(bool(kosul))
    return _base_ok(kosul, mesaj)

for s in ai_lab.kod_denetimi(src, yasak=("yon_normallestir_referans", "yon_bilesenini_kaldir_referans", "ablite_karsilastirmasi_referans", "kanit_yaz", "getattr")):
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
        if yon_normallestir([3, 4]) != [0.6, 0.8] or yon_normallestir([1, 1, 1]) != [0.57735, 0.57735, 0.57735]:
            return False
        for by in [None, [], [0, 0], [True], [float("nan")]]:
            try:
                yon_normallestir(by)
                return False
            except ValueError:
                pass

        if yon_bilesenini_kaldir([1, 2], [3, 4]) != [-0.32, 0.24] or yon_bilesenini_kaldir([1, 0, 0], [1, 1, 1]) != [0.666667, -0.333333, -0.333333]:
            return False
        for bx, byon in [(None, [3, 4]), ([1], [3, 4]), ([1, 2], [0, 0]), ([True, 2], [3, 4])]:
            try:
                yon_bilesenini_kaldir(bx, byon)
                return False
            except ValueError:
                pass

        K = [
            {"kosul": "taban", "guvenlik": 0.8, "yetenek": 0.9},
            {"kosul": "ablite", "guvenlik": 0.4, "yetenek": 0.6},
            {"kosul": "taban", "guvenlik": 0.6, "yetenek": 0.7},
            {"kosul": "ablite", "guvenlik": 0.2, "yetenek": 0.8},
        ]
        bek_k = {"taban": {"guvenlik": 0.7, "yetenek": 0.8}, "ablite": {"guvenlik": 0.3, "yetenek": 0.7}, "guvenlik_degisimi": -0.4, "yetenek_kaybi": 0.1}
        if ablite_karsilastirmasi(K) != bek_k:
            return False
        for bk in [None, [], [K[0]], [dict(K[0], kosul="x"), K[1]], [dict(K[0], guvenlik=1.2), K[1]]]:
            try:
                ablite_karsilastirmasi(bk)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

def _birim1(fn):
    import copy
    Y = [3, 4]
    def sozlesme(fn):
        try:
            once = copy.deepcopy(Y)
            if fn(Y) != [0.6, 0.8] or Y != once:
                return False
            if fn([-3, 0]) != [-1.0, 0.0] or fn([0, 2]) != [0.0, 1.0]:
                return False
            if fn([1, 1, 1]) != [0.57735, 0.57735, 0.57735] or fn([1, 2]) != [0.447214, 0.894427]:
                return False
            for yon in [None, tuple(Y), {}, [], "12", [None], [True], ["3"], [float("nan")], [float("inf")], [0], [0, 0]]:
                try:
                    fn(yon)
                    return False
                except ValueError:
                    pass
            return True
        except Exception:
            return False
    return sozlesme(fn)

def _birim2(fn):
    import copy
    X = [1, 2]
    Y = [3, 4]
    def sozlesme(fn):
        try:
            xonce = copy.deepcopy(X)
            yonce = copy.deepcopy(Y)
            if fn(X, Y) != [-0.32, 0.24] or X != xonce or Y != yonce:
                return False
            if fn([2, 1], [0, 5]) != [2.0, 0.0] or fn([-2, 1], [0, 5]) != [-2.0, 0.0]:
                return False
            yuvarla = fn([1, 0], [1, 1, 1][:-1])
            if yuvarla != [0.5, -0.5]:
                return False
            uc = fn([1, 0, 0], [1, 1, 1])
            if uc != [0.666667, -0.333333, -0.333333]:
                return False
            for x, yon in [
                (None, Y), (X, None), (tuple(X), Y), (X, tuple(Y)), ({}, Y), (X, {}), ([], []), ([], Y), (X, []), ([1], Y), (X, [3]),
                ([True, 2], Y), (["1", 2], Y), ([float("nan"), 2], Y), ([float("inf"), 2], Y),
                (X, [True, 4]), (X, ["3", 4]), (X, [float("nan"), 4]), (X, [float("inf"), 4]), (X, [0, 0]),
            ]:
                try:
                    fn(x, yon)
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
        {"kosul": "taban", "guvenlik": 0.8, "yetenek": 0.9},
        {"kosul": "ablite", "guvenlik": 0.4, "yetenek": 0.6},
        {"kosul": "taban", "guvenlik": 0.6, "yetenek": 0.7},
        {"kosul": "ablite", "guvenlik": 0.2, "yetenek": 0.8},
    ]
    BEKLENEN = {"taban": {"guvenlik": 0.7, "yetenek": 0.8}, "ablite": {"guvenlik": 0.3, "yetenek": 0.7}, "guvenlik_degisimi": -0.4, "yetenek_kaybi": 0.1}
    def sozlesme(fn):
        try:
            once = copy.deepcopy(K)
            if fn(K) != BEKLENEN or K != once:
                return False
            sinir = fn([{"kosul": "taban", "guvenlik": 0, "yetenek": 1}, {"kosul": "ablite", "guvenlik": 1, "yetenek": 0}])
            if sinir != {"taban": {"guvenlik": 0, "yetenek": 1}, "ablite": {"guvenlik": 1, "yetenek": 0}, "guvenlik_degisimi": 1, "yetenek_kaybi": 1}:
                return False
            yuvarla = fn([
                {"kosul": "taban", "guvenlik": 1, "yetenek": 1},
                {"kosul": "taban", "guvenlik": 0, "yetenek": 0},
                {"kosul": "taban", "guvenlik": 0, "yetenek": 0},
                {"kosul": "ablite", "guvenlik": 0, "yetenek": 0},
            ])
            if yuvarla["taban"] != {"guvenlik": 0.333333, "yetenek": 0.333333} or yuvarla["guvenlik_degisimi"] != -0.333333 or yuvarla["yetenek_kaybi"] != 0.333333:
                return False
            ablite_yuvarla = fn([
                {"kosul": "taban", "guvenlik": 0, "yetenek": 0},
                {"kosul": "ablite", "guvenlik": 1, "yetenek": 1},
                {"kosul": "ablite", "guvenlik": 0, "yetenek": 0},
                {"kosul": "ablite", "guvenlik": 0, "yetenek": 0},
            ])
            if ablite_yuvarla["ablite"] != {"guvenlik": 0.333333, "yetenek": 0.333333}:
                return False
            for kayitlar in [
                None, tuple(K), {}, [], [None], [dict(K[0], ek=1), K[1]], [K[0], K[1], dict(K[0], kosul="diger")], [K[0], K[1], dict(K[0], kosul=[])],
                [K[0]], [K[1]], [dict(K[0], kosul=None), K[1]],
                [dict(K[0], guvenlik=True), K[1]], [dict(K[0], guvenlik="0.8"), K[1]],
                [dict(K[0], guvenlik=float("nan")), K[1]], [dict(K[0], guvenlik=float("inf")), K[1]],
                [dict(K[0], guvenlik=-0.1), K[1]], [dict(K[0], guvenlik=1.1), K[1]],
                [dict(K[0], yetenek=True), K[1]], [dict(K[0], yetenek="0.9"), K[1]],
                [dict(K[0], yetenek=float("nan")), K[1]], [dict(K[0], yetenek=float("inf")), K[1]],
                [dict(K[0], yetenek=-0.1), K[1]], [dict(K[0], yetenek=1.1), K[1]],
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

ok(_birim1(yon_normallestir), "yon_normallestir tam birim sözleşmesini geçmeli")
ok(_birim2(yon_bilesenini_kaldir), "yon_bilesenini_kaldir tam birim sözleşmesini geçmeli")
ok(_birim3(ablite_karsilastirmasi), "ablite_karsilastirmasi tam birim sözleşmesini geçmeli")
ok(_sozlesme_kontrol(), "yon_normallestir, yon_bilesenini_kaldir ve ablite_karsilastirmasi sözleşme kontrollerini geçmeli")
if not all(checks):
    stop()

try:
    rapor = L.deney(yon_normallestir, yon_bilesenini_kaldir, ablite_karsilastirmasi)
except ai_lab.GercekLabYok as e:
    ok(False, str(e))
    stop()
except Exception as e:
    ok(False, f"GERÇEK ABLITERATION DENEYİ YAPILAMADI: {type(e).__name__}: {e}")
    stop()

k = rapor["kontroller"]
ok(k["yon_normallestir_uyumu"], f"yon_normallestir canlı refusal yönünde referansla uyuşmalı: {rapor['birim_8d']}")
ok(k["yon_bilesenini_kaldir_uyumu"], f"yon_bilesenini_kaldir canlı aktivasyonda referansla uyuşmalı: {rapor['proj_8d']}")
ok(k["ablite_karsilastirmasi_uyumu"], f"ablite_karsilastirmasi canlı müdahale ölçümlerinde referansla uyuşmalı: {rapor['karsilastirma']}")
ok(k["canli_mudahale_calisti"], f"Qwen2.5-0.5B-Instruct üzerinde ortogonal projeksiyon müdahalesi çalışmalı: {rapor['ozet']}")

kabul = all(checks)
kanit_yolu = ai_lab.kanit_yaz("guvence-10-abliteration", dict(rapor, kaynak="gercek", kabul=kabul))
o = rapor["ozet"]
print(f"GERÇEK ABLITERATION DENEYİ: model={o['model']}@{o['revizyon']} katman={o['katman']} karsilastirma={o['karsilastirma']} kanıt={kanit_yolu}")
```

```solution
import math
import ai_lab
from sandbox import ai_gercek_ai_guvence_10 as L

def yon_normallestir(yon):
    if not isinstance(yon, list) or not yon:
        raise ValueError("yön geçersiz")
    for deger in yon:
        if isinstance(deger, bool) or not isinstance(deger, (int, float)) or not math.isfinite(deger):
            raise ValueError("koordinat geçersiz")
    norm = math.sqrt(sum(deger * deger for deger in yon))
    if norm == 0:
        raise ValueError("yön normu pozitif olmalı")
    return [round(deger / norm, 6) for deger in yon]

def yon_bilesenini_kaldir(x, yon):
    if not isinstance(x, list) or not isinstance(yon, list) or not x or not yon or len(x) != len(yon):
        raise ValueError("vektörler geçersiz")
    for vektor in (x, yon):
        for deger in vektor:
            if isinstance(deger, bool) or not isinstance(deger, (int, float)) or not math.isfinite(deger):
                raise ValueError("koordinat geçersiz")
    norm = math.sqrt(sum(deger * deger for deger in yon))
    if norm == 0:
        raise ValueError("yön normu pozitif olmalı")
    u = [deger / norm for deger in yon]
    ic_carpim = sum(a * b for a, b in zip(x, u))
    return [round(a - ic_carpim * b, 6) for a, b in zip(x, u)]

def ablite_karsilastirmasi(kayitlar):
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar geçersiz")
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"kosul", "guvenlik", "yetenek"}:
            raise ValueError("şema geçersiz")
        if kayit["kosul"] not in ("taban", "ablite"):
            raise ValueError("koşul geçersiz")
        for alan in ("guvenlik", "yetenek"):
            deger = kayit[alan]
            if isinstance(deger, bool) or not isinstance(deger, (int, float)) or not math.isfinite(deger) or deger < 0 or deger > 1:
                raise ValueError("puan geçersiz")
    if {x["kosul"] for x in kayitlar} != {"taban", "ablite"}:
        raise ValueError("iki koşul da gerekli")
    ortalamalar = {}
    for kosul in ("taban", "ablite"):
        grup = [x for x in kayitlar if x["kosul"] == kosul]
        ortalamalar[kosul] = {alan: sum(x[alan] for x in grup) / len(grup) for alan in ("guvenlik", "yetenek")}
    return {
        "taban": {alan: round(deger, 6) for alan, deger in ortalamalar["taban"].items()},
        "ablite": {alan: round(deger, 6) for alan, deger in ortalamalar["ablite"].items()},
        "guvenlik_degisimi": round(ortalamalar["ablite"]["guvenlik"] - ortalamalar["taban"]["guvenlik"], 6),
        "yetenek_kaybi": round(ortalamalar["taban"]["yetenek"] - ortalamalar["ablite"]["yetenek"], 6),
    }

if ai_lab.CALISTIR:
    L.goster(yon_normallestir, yon_bilesenini_kaldir, ablite_karsilastirmasi)
```

```hint
Önceki üç görevde yazdığın `yon_normallestir`, `yon_bilesenini_kaldir` ve `ablite_karsilastirmasi` işlevlerini eksiksiz taşı; canlı deneyde katman 14 refusal yönü ortogonal projeksiyonla kaldırılır.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Ortogonal projeksiyon ile yön silme (`abliteration`) (30 sn).** "Birim refusal yönü $\mathbf{u} = \mathbf{y}/\|\mathbf{y}\|_2$ bulunduğunda rezidüel aktivasyondan $\mathbf{x} - (\mathbf{x}\cdot\mathbf{u})\mathbf{u}$ çıkarılır; böylece aktivasyonun bu yöndeki izdüşümü sıfırlanır."
2. **İki eksenli ölçüm: güvenlik ve genel yetenek (35 sn).** "Yalnız ret oranının düşmesine bakmak yanıltıcıdır; çok anlamlı (`polysemantic`) temsiller nedeniyle müdahale genel bilgi ve akıl yürütmede `yetenek_kaybi` doğurabilir."
3. **Açık ağırlık tedarik riski (30 sn).** "Aynı projeksiyon çıkarım kancası yerine ağırlık matrislerine kalıcı yazılarak 'sansürsüz' türev modeller üretilebilir; savunucu hem güvenlik aşınmasını hem yetenek regresyonunu birlikte denetler."
4. **Soru (25 sn).** "Projeksiyon çıkarmasını birim vektör $\mathbf{u}$ yerine normalize edilmemiş ham fark vektörü $\mathbf{y}$ ile yaparsan model çıktısı neden bozulur?"
:::
