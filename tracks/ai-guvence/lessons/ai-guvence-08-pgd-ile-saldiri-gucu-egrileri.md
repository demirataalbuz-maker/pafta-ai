---
id: ai-guvence-08
title: PGD ile Saldırı Gücü Eğrileri
summary: PGD adımlarını bütçe içine projekte et; epsilon ve adım sayısı boyunca doğruluk kaybı eğrilerini karşılaştır.
esleme: ai-guvence-07, ai-guvence-35, ai-guvence-36
timeout: 45
---

::: anlat Gerçek PGD saldırı eğrisini bil, sentetik temsili ayırt et
Projected Gradient Descent (PGD), derin öğrenme modellerinin güvenilirlik ve sağlamlık (adversarial robustness) değerlendirmelerinde endüstri standardı kabul edilen çok adımlı, yinelemeli bir birinci derece saldırı yöntemidir. Tek adımlı Fast Gradient Sign Method (FGSM) saldırısının aksine PGD, kayıp fonksiyonunun gradyanı yönünde küçük adımlar atarak ilerler ve her adımın ardından elde edilen perturbasyonu belirlenen $L_\infty$ epsilon ($\varepsilon$) hiper-küpü ile geçerli girdi uzayı ($[0, 1]$ piksel/özellik sınırları) arakesitine geri projekte eder. Adım büyüklüğü $\alpha$ (alpha) ve toplam perturbasyon bütçesi $\varepsilon$ birbirinden bağımsızdır; $\alpha \le \varepsilon$ koşulu sağlandığında saldırgan modelin karar sınırlarına doğru kontrollü ve yerel kayıp yüzeyindeki doğrusal olmayan dalgalanmaları aşabilen çok adımlı bir tırmanış gerçekleştirir.

| Gerçek araç / model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Çok adımlı PGD sağlamlık değerlendirmesinde her iterasyonda `torch.autograd.grad` ile kayıp türevi $\nabla_x \mathcal{L}$, $\alpha \cdot \text{sign}(\nabla_x \mathcal{L})$ gradyan tırmanışı ve $[x_0 - \varepsilon, x_0 + \varepsilon] \cap [0, 1]$ projeksiyonu | İlk 3 görevde `veri/pgd_ayari.json` sentetik gradyanları; son görevde `ai_lab.fgsm_siniflandirici()` (64-32-4 PyTorch MLP) üzerinde canlı `autograd` PGD adımları | Sabit $\varepsilon$ altında yüksek PGD doğruluğu, gradyan maskelemesi (obfuscated gradients) yoksa anlamlıdır; tek başına sertifikalı sağlamlık kanıtı değildir |
| Farklı $\varepsilon$ bütçeleri ve iterasyon ($t = 0..K$) boyunca doğruluk kaybı eğrisi ile gerçekleşen $L_\infty$ normu izi | İlk 3 görevde `veri/pgd_kayitlari.json` sentetik gözlemleri; son görevde $\varepsilon \in \{0.1, 0.2\}$ ve $t \in \{0, 1, 2, 3\}$ canlı eğrisi | $L_\infty$ bütçesiyle ölçülen sağlamlık, $L_2$ kürelerine veya anlamsal/geometrik dönüşümlere doğrudan taşınamaz |

> [!NOT]
> İlk üç görevde örnek dosyalar çalışma klasörünün `veri/` altına kopyalanır: `veri/pgd_ayari.json` ve `veri/pgd_kayitlari.json` (tümü **sentetik**). Bu dosyaları kodundan okuyup inceleyebilirsin; ancak her çalıştırmada temiz kopya yeniden yazılır (**kalıcılık yoktur**). Kontrol adımı bu dosyalardan bağımsız gizli verilerle sınama yapar. Gerçek deney adımında ise PyTorch üzerinde canlı eğitilmiş bir MLP modeli üzerinde gerçek gradyanlar hesaplanır.

### Aracın Altında Ne Olur?
PGD değerlendirme motoru şu adımları işletir:
1. **Girdi ve Parametre Doğrulaması:** Saldırı bütçesi $\varepsilon \in [0, 1]$, adım boyu $\alpha \in [0, 1]$ ve toplam adım sayısı $K \in \mathbb{Z}^+$ doğrulanır. $\alpha \le \varepsilon$ denetimi ile saldırının bütçe sınırını tek adımda kontrolsüz aşması engellenir.
2. **Yinelemeli Gradyan Tırmanışı:** $t = 0$ anında modelin temiz örneği $x_0$ alınır. Her iterasyonda $t = 1..K$ için:
   $$y_{t} = x_{t-1} + \alpha \cdot \text{sign}\left(\nabla_x \mathcal{L}(\theta, x_{t-1}, y_{\text{true}})\right)$$
   hesaplanır.
3. **Kırpma ve Çift Kademeli Projeksiyon:** Girdi önce geçerli fiziksel uzaya kırpılır: $\tilde{y}_t = \text{clip}(y_t, 0, 1)$. Ardından başlangıç noktası çevresindeki $L_\infty$ hiper-küpüne projekte edilir:
   $$x_t = \Pi_{x_0, \varepsilon}(\tilde{y}_t) = \text{clip}(\tilde{y}_t, x_0 - \varepsilon, x_0 + \varepsilon)$$
   Bu işlem, her adımda perturbasyonun başlangıç noktasından en fazla $\varepsilon$ uzaklaşabilmesini garanti eder.
4. **$L_\infty$ Normu ve İz Takibi:** Her adımda gerçekleşen perturbasyon normu $\|x_t - x_0\|_\infty = \max_i |x_{t,i} - x_{0,i}|$ ölçülür ve kayıt altına alınır.
5. **Epsilon-Adım Eğrilerinin Çıkarılması:** Farklı $\varepsilon$ ve adım sayıları için test kümesindeki doğruluk oranları toplanır. Adım 0 (`adim=0`) taban doğruluk (baseline clean accuracy) olarak sabitlenir ve her adım için doğruluk kaybı $\text{kayıp}(t) = \text{doğruluk}(0) - \text{doğruluk}(t)$ şeklinde hesaplanır.

### Çıktı Nasıl Okunur?
- **Taban Doğruluk ($t = 0$):** Modelin hiçbir saldırı uygulanmadığındaki temiz performansıdır; bu adımda $L_\infty = 0$ olmak zorundadır.
- **Doğruluk Kaybı (Accuracy Drop):** Epsilon bütçesi ve adım sayısı arttıkça model doğruluğundaki düşüşü gösterir. Başarılı bir saldırıda bu değer pozitif yönde büyür.
- **Doyum Noktası (Saturation):** PGD adım sayısı arttıkça eğrinin düzleştiği noktadır; belirli bir adımdan sonra (örneğin $t \ge 3$) kayıp artmıyorsa saldırı o bütçe için yerel optimuma ulaşmıştır.
- **Maksimum Kayıp:** İlgili epsilon seviyesinde gözlemlenen en yüksek doğruluk kaybıdır ve modelin o tehdit seviyesindeki kırılganlık sınırını temsil eder.

### Saldırgan Neyi Dener?
- **Yerel Minimumları Aşma:** Tek adımlı saldırıların takıldığı yerel düzlükleri aşmak için küçük $\alpha$ adımlarıyla çok sayıda iterasyon dener.
- **Rastgele Başlatma (Random Restarts):** $x_0$ çevresinde rastgele bir noktadan başlayarak ($x_0 + \mathcal{U}(-\varepsilon, \varepsilon)$) farklı kayıp vadilerini keşfeder.
- **Kritik Epsilon Sınırını Tespit:** Doğruluğun aniden çöktüğü eşik epsilon bütçesini belirleyerek en az fark edilebilir gürültüyle modeli yanıltmayı hedefler.

### Savunma Neden Kırılır?
- **Gradyan Maskelemesi (Gradient Masking / Obfuscation):** Bazı savunmalar gradyanı sıfırlar, kırar ya da rastgeleleştirir. Bu durumda yalnız FGSM değil, düz PGD de yanılır ve model sahte biçimde dayanıklı görünür (Athalye vd., 2018). Böyle bir savunmayı sınamak için BPDA, EOT, rastgele yeniden başlatma veya başka modelden transfer saldırısı gerekir; "PGD kıramadı" sonucu tek başına dayanıklılık kanıtı değildir.
- **Kayıp Yüzeyi Parçalanması:** Defansif distilasyon gibi yöntemler softmax'ı doyurarak gradyanı küçültür; kayıp yerine logitler üzerinden kurulan saldırılar (ör. Carlini–Wagner) bu savunmayı aşmıştır. Eğri düz çıkıyorsa önce gradyanın gerçekten bilgi taşıyıp taşımadığı kontrol edilmelidir.
- **Tek Metrik Yanılgısı:** $L_\infty$ normunda yüksek direnç gösteren bir model, $L_2$ veya dönüşüm saldırılarına karşı tamamen savunmasız kalabilir.

### Sık Yapılan Geliştirici Tuzakları
- **Projeksiyonu Güncel Noktaya Uygulama Hatası:** Projeksiyon sınırlarını $x_{t-1} \pm \varepsilon$ olarak almak yerine daima ilk temiz örnek $x_0 \pm \varepsilon$ üzerinden hesaplamak şarttır; aksi takdirde kümülatif gürültü $K \cdot \alpha$ seviyesine fırlayarak bütçeyi deler.
- **Kırpma Sıralaması ve Eşzamanlılık:** $[0, 1]$ aralığına kırpma ile $[x_0-\varepsilon, x_0+\varepsilon]$ projeksiyonunun bağımsız koordinatlar üzerinde tutarlı işletilmesi gerekir.
- **Bool Tip Tuzağı:** Python'da `isinstance(True, int) == True` olduğundan `type(v) is bool` veya `isinstance(v, bool)` ile açık tip denetimi yapılmalıdır.
- **Taban Adımı Eksikliği:** Adım 0 kaydı olmayan veya sıfırıncı adımda $L_\infty > 0$ olan kayıtların rapora dahil edilmesi taban kaybı hesabını bozar ve `ValueError` ile engellenmelidir.
- **Float Yuvarlama Sapmaları:** $L_\infty$ değerinin $\varepsilon$ sınırını $1e-9$ seviyesindeki kayan nokta sapmalarıyla aşabilmesi durumunda `1e-9` toleransı tanınmalıdır.
:::

::: anlat Projeksiyon ve taban adımı eğriyi karşılaştırılabilir yapar
Her koordinatta önce girdi `[0,1]` aralığına kırpılır, sonra başlangıç değerinin `x0-epsilon` ile `x0+epsilon` aralığına projekte edilir. Gerçekleşen `L∞`, son nokta ile başlangıç noktası arasındaki en büyük mutlak farktır.

Her epsilon eğrisi `adim=0` tabanını içermelidir; sıfırıncı adımda `L∞=0` olur. Satır kaybı aynı epsilonun taban doğruluğu eksi o adımdaki doğruluktur. Eğriler epsilon ve adım numarasına göre sıralanır; özet son adımı ve en yüksek ham kaybı gösterir.

Kaynaklar: [Madry vd. 2018 — Towards Deep Learning Models Resistant to Adversarial Attacks (arXiv:1706.06083)](https://arxiv.org/abs/1706.06083), [Athalye vd. 2018 — Obfuscated Gradients Give a False Sense of Security (arXiv:1802.00420)](https://arxiv.org/abs/1802.00420).
:::

::: tahmin PGD projeksiyonunu tahmin et
Üç çıktı satırını yaz:

```python
print(min(0.5 + 0.05, max(0.5 - 0.05, 0.7)))
print(round(0.55 - 0.5, 6))
print(round(0.8 - 0.5, 6))
```

???

```cikti
0.55
0.05
0.3
```

İlk satır alpha kaynaklı `0.7` değerinin epsilon bütçesindeki `0.55` sınırına çekildiğini gösterir.
:::

::: gorev 1 · PGD ayarını doğrula
`pgd_ayari_dogrula(ayar)` işlevini yaz. Ayar tam olarak `id`, `epsilon`, `alpha`, `adim` alanlarını taşısın. Kimlik 1–64 karakterlik, ASCII harf/rakamla başlayan ve yalnız ASCII harf, rakam, alt çizgi veya tire içeren stringdir. Epsilon ve alpha bool olmayan sonlu sayı ve `[0,1]` aralığındadır; `alpha <= epsilon` olmalıdır. Adım bool olmayan pozitif tamsayıdır.

Geçersiz veride `ValueError` yükselt. Alanları koruyan yeni sözlükle döndür ve girdiyi değiştirme. `epsilon=alpha=0` geçerlidir.

```starter
from ai_guvence_veri import json_yukle

def pgd_ayari_dogrula(ayar):
    # KUSURLU BAŞLANGIÇ KODU: alpha <= epsilon şartını denetlemeden doğrudan girdi sözlüğünü döndürüyor!
    return ayar

print("Örnek PGD ayarı:", pgd_ayari_dogrula(json_yukle("veri/pgd_ayari.json")["ayar"]))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-08")
```

```test
import copy
A = {"id": "pgd-1", "epsilon": 0.15, "alpha": 0.1, "adim": 2}
def sozlesme(fn):
    try:
        once = copy.deepcopy(A)
        sonuc = fn(A)
        if sonuc != A or A != once or sonuc is A:
            return False
        if fn(dict(A, id="a" * 64, epsilon=0, alpha=0, adim=1))["adim"] != 1:
            return False
        if fn(dict(A, epsilon=1, alpha=1))["alpha"] != 1:
            return False
        for ayar in [
            None, [], dict(A, ek=1), dict(A, id=""), dict(A, id="a b"), dict(A, id="a" * 65), dict(A, id=None),
            dict(A, epsilon=None), dict(A, epsilon=True), dict(A, epsilon="0.15"), dict(A, epsilon=float("nan")),
            dict(A, epsilon=float("inf")), dict(A, epsilon=-0.1), dict(A, epsilon=1.1),
            dict(A, alpha=None), dict(A, alpha=True), dict(A, alpha="0.1"), dict(A, alpha=float("nan")),
            dict(A, alpha=float("inf")), dict(A, alpha=-0.1), dict(A, alpha=1.1), dict(A, alpha=0.2),
            dict(A, epsilon=0, alpha=0.1), dict(A, adim=0), dict(A, adim=-1), dict(A, adim=True),
            dict(A, adim=1.0), dict(A, adim=None),
        ]:
            try:
                fn(ayar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(pgd_ayari_dogrula), "ayar şeması, bütçe ve adım kuralları korunmalı")
def m_alpha(ayar):
    return pgd_ayari_dogrula(dict(ayar, alpha=0))
def m_epsilon(ayar):
    return pgd_ayari_dogrula(dict(ayar, epsilon=0.2))
def m_adim(ayar):
    return pgd_ayari_dogrula(dict(ayar, adim=1))
for ad, mutant in [("alphayı silen", m_alpha), ("epsilonu değiştiren", m_epsilon), ("adımı değiştiren", m_adim)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def pgd_ayari_dogrula(ayar):
    import math
    import re
    if not isinstance(ayar, dict):
        raise ValueError("ayar sözlük olmalı")
    if set(ayar) != {"id", "epsilon", "alpha", "adim"}:
        raise ValueError("ayar şeması geçersiz")
    if not isinstance(ayar["id"], str):
        raise ValueError("kimlik string olmalı")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", ayar["id"]):
        raise ValueError("kimlik geçersiz")
    for alan in ("epsilon", "alpha"):
        deger = ayar[alan]
        if isinstance(deger, bool) or not isinstance(deger, (int, float)):
            raise ValueError("bütçe sayı olmalı")
        if not math.isfinite(deger):
            raise ValueError("bütçe sonlu olmalı")
        if deger < 0 or deger > 1:
            raise ValueError("bütçe aralık dışında")
    if ayar["alpha"] > ayar["epsilon"]:
        raise ValueError("alpha epsilonu aşamaz")
    if isinstance(ayar["adim"], bool):
        raise ValueError("adım tamsayı olmalı")
    if not isinstance(ayar["adim"], int):
        raise ValueError("adım tamsayı olmalı")
    if ayar["adim"] <= 0:
        raise ValueError("adım pozitif olmalı")
    return {"id": ayar["id"], "epsilon": ayar["epsilon"], "alpha": ayar["alpha"], "adim": ayar["adim"]}
```

```hint
İki bütçeyi aynı döngüde doğrula, sonra aralarındaki sırayı denetle. Adımın türünü ve pozitifliğini ayrı kontrol et.
```
:::

::: gorev 2 · Çok adımlı PGD izini üret
`pgd_izini_uret(x, gradyanlar, ayar)` işlevini yaz. Ayar ilk görevdeki kuralları sağlasın. `x` boş olmayan, bool olmayan sonlu sayılardan oluşan `[0,1]` listesidir. Gradyanların liste sayısı ayarın adımına eşit olmalı; her gradyan `x` ile aynı boyutta, boş olmayan ve bool olmayan sonlu sayılardan oluşmalıdır. Geçersiz veride `ValueError` yükselt.

Başlangıç `x0` olsun. Her adımda `y=x+alpha*isaret(gradyan)` hesapla, önce `[0,1]` aralığına kırp, sonra `[x0-epsilon,x0+epsilon]` aralığına projekte et. `{"id":ID,"son":[X,...],"l_inf":X,"iz":[{"adim":N,"x":[X,...]},...]}` döndür. İzleri adım sırasıyla ver; bütün çıktı koordinatlarını ve `L∞` değerini altı ondalık basamağa yuvarla. Girdileri değiştirme.

```starter
from ai_guvence_veri import json_yukle

def pgd_izini_uret(x, gradyanlar, ayar):
    # KUSURLU BAŞLANGIÇ KODU: adımları uygulamadan ve projekte etmeden başlangıç vektörünü döndürüyor!
    return {"id": ayar.get("id", "") if isinstance(ayar, dict) else "", "son": list(x or []), "l_inf": 0.0, "iz": []}

ornek = json_yukle("veri/pgd_ayari.json")
print("Örnek PGD izi:", pgd_izini_uret(ornek["x"], ornek["gradyanlar"], ornek["ayar"]))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-08")
```

```test
import copy
A = {"id": "pgd-1", "epsilon": 0.15, "alpha": 0.1, "adim": 2}
X = [0.5, 0.95]
G = [[1, 1], [-1, 1]]
BEKLENEN = {"id": "pgd-1", "son": [0.5, 1.0], "l_inf": 0.05, "iz": [{"adim": 1, "x": [0.6, 1.0]}, {"adim": 2, "x": [0.5, 1.0]}]}
def sozlesme(fn):
    try:
        xonce = copy.deepcopy(X)
        gonce = copy.deepcopy(G)
        aonce = copy.deepcopy(A)
        if fn(X, G, A) != BEKLENEN or X != xonce or G != gonce or A != aonce:
            return False
        proje = dict(A, epsilon=0.05, alpha=0.05, adim=1)
        if fn([0.5], [[1]], proje) != {"id": "pgd-1", "son": [0.55], "l_inf": 0.05, "iz": [{"adim": 1, "x": [0.55]}]}:
            return False
        sifir = dict(A, epsilon=0, alpha=0, adim=1)
        if fn([0], [[0]], sifir)["l_inf"] != 0:
            return False
        if fn([0, 1], [[0, 0]], sifir)["son"] != [0, 1]:
            return False
        ust = dict(A, epsilon=1, alpha=1, adim=1)
        if fn([0], [[1]], ust)["son"] != [1] or fn([0.05], [[-1]], dict(A, adim=1))["son"] != [0.0]:
            return False
        sifir_grad = fn([0.5], [[0]], dict(A, adim=1))
        if sifir_grad != {"id": "pgd-1", "son": [0.5], "l_inf": 0, "iz": [{"adim": 1, "x": [0.5]}]}:
            return False
        yuvarla = dict(A, epsilon=1 / 3, alpha=1 / 3, adim=1)
        if fn([0], [[1]], yuvarla) != {"id": "pgd-1", "son": [0.333333], "l_inf": 0.333333, "iz": [{"adim": 1, "x": [0.333333]}]}:
            return False
        for x, gradyanlar, ayar in [
            (None, G, A), (tuple(X), G, A), (X, tuple(G), A), (X, [(1, 1), (-1, 1)], A), ([], [[]], dict(A, adim=1)),
            (X, None, A), (X, G, None), ({}, G, A), ([], G, A), (X, [], A),
            (X, G[:1], A), (X, [[1], [-1, 1]], A), (X, [[1, 1], None], A),
            ([True, 0.95], G, A), (["0.5", 0.95], G, A), ([float("nan"), 0.95], G, A),
            ([-0.1, 0.95], G, A), ([-0.1, 1.1], G, A), ([1.1, 0.95], G, A),
            (X, [[True, 1], [-1, 1]], A), (X, [["1", 1], [-1, 1]], A),
            (X, [[float("inf"), 1], [-1, 1]], A),
            (X, G, dict(A, id="a" * 65)), (X, G, dict(A, alpha=0.2)),
            (X, G, dict(A, epsilon=-0.1, alpha=-0.2)), (X, G, dict(A, epsilon=1.1, alpha=1)),
            (X, G, dict(A, ek=1)), (X, G, dict(A, id=123)), (X, G, dict(A, epsilon="0.1")), (X, G, dict(A, epsilon=float("nan"))),
            (X, [G[0]], dict(A, adim=True)), (X, G, dict(A, adim=2.0)),
            (X, G, dict(A, epsilon=True)), (X, G, dict(A, adim=0)), (X, [], dict(A, adim=0)),
        ]:
            try:
                fn(x, gradyanlar, ayar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(pgd_izini_uret), "adım izi, kırpma, projeksiyon ve L∞ korunmalı")
def m_grad(x, gradyanlar, ayar):
    return pgd_izini_uret(x, [[0 for _ in gradyanlar[0]] for _ in gradyanlar], ayar)
def m_x(x, gradyanlar, ayar):
    return pgd_izini_uret([0.5 for _ in x], gradyanlar, ayar)
def m_adim(x, gradyanlar, ayar):
    return pgd_izini_uret(x, gradyanlar[:1], dict(ayar, adim=1))
for ad, mutant in [("gradyanları silen", m_grad), ("girdiyi değiştiren", m_x), ("adımları azaltan", m_adim)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def pgd_izini_uret(x, gradyanlar, ayar):
    import math
    import re
    if not isinstance(ayar, dict):
        raise ValueError("ayar sözlük olmalı")
    if set(ayar) != {"id", "epsilon", "alpha", "adim"}:
        raise ValueError("ayar şeması geçersiz")
    if not isinstance(ayar["id"], str):
        raise ValueError("kimlik string olmalı")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", ayar["id"]):
        raise ValueError("kimlik geçersiz")
    for alan in ("epsilon", "alpha"):
        deger = ayar[alan]
        if isinstance(deger, bool) or not isinstance(deger, (int, float)):
            raise ValueError("bütçe sayı olmalı")
        if not math.isfinite(deger):
            raise ValueError("bütçe sonlu olmalı")
        if deger < 0 or deger > 1:
            raise ValueError("bütçe aralık dışında")
    if ayar["alpha"] > ayar["epsilon"]:
        raise ValueError("alpha epsilonu aşamaz")
    if isinstance(ayar["adim"], bool):
        raise ValueError("adım tamsayı olmalı")
    if not isinstance(ayar["adim"], int):
        raise ValueError("adım tamsayı olmalı")
    if ayar["adim"] <= 0:
        raise ValueError("adım pozitif olmalı")
    if not isinstance(x, list):
        raise ValueError("x liste olmalı")
    if not x:
        raise ValueError("x boş olamaz")
    for deger in x:
        if isinstance(deger, bool) or not isinstance(deger, (int, float)):
            raise ValueError("girdi sayı olmalı")
        if not math.isfinite(deger):
            raise ValueError("girdi sonlu olmalı")
        if deger < 0 or deger > 1:
            raise ValueError("girdi aralık dışında")
    if not isinstance(gradyanlar, list):
        raise ValueError("gradyanlar liste olmalı")
    if len(gradyanlar) != ayar["adim"]:
        raise ValueError("gradyan adım sayısı ayarla uyuşmuyor")
    for gradyan in gradyanlar:
        if not isinstance(gradyan, list):
            raise ValueError("gradyan liste olmalı")
        if len(gradyan) != len(x):
            raise ValueError("gradyan boyutu uyuşmuyor")
        for deger in gradyan:
            if isinstance(deger, bool) or not isinstance(deger, (int, float)):
                raise ValueError("gradyan sayı olmalı")
            if not math.isfinite(deger):
                raise ValueError("gradyan sonlu olmalı")
    x0 = list(x)
    son = list(x)
    iz = []
    for adim, gradyan in enumerate(gradyanlar, 1):
        yeni = []
        for i, gv in enumerate(gradyan):
            isaret = 1 if gv > 0 else -1 if gv < 0 else 0
            deger = min(1, max(0, son[i] + ayar["alpha"] * isaret))
            deger = min(x0[i] + ayar["epsilon"], max(x0[i] - ayar["epsilon"], deger))
            yeni.append(deger)
        son = yeni
        iz.append({"adim": adim, "x": [round(v, 6) for v in son]})
    return {"id": ayar["id"], "son": [round(v, 6) for v in son], "l_inf": round(max(abs(a - b) for a, b in zip(son, x0)), 6), "iz": iz}
```

```hint
Başlangıç vektörünü ayrı kopyala. Her adımda güncel noktayı kullan, projeksiyon sınırlarını ise daima başlangıç noktasından hesapla.
```
:::

::: gorev 3 · Epsilon-adım eğrilerini özetle
`pgd_egri_raporu(kayitlar)` işlevini yaz. Kayıtlar boş olmayan listedir. Her kayıt tam olarak `epsilon`, `adim`, `dogruluk`, `l_inf` alanlarını taşısın. Epsilon, doğruluk ve `L∞` bool olmayan sonlu sayı ve `[0,1]` aralığındadır. Adım bool olmayan, sıfır veya pozitif tamsayıdır. `(epsilon,adim)` çifti yinelenemez ve `l_inf <= epsilon + 1e-9` olmalıdır.

Her epsilon için tam bir `adim=0` tabanı bulunmalı ve bu satırın `L∞` değeri sıfır olmalıdır. Satır kaybı aynı epsilonun taban doğruluğu eksi satır doğruluğudur. Geçersiz veride `ValueError` yükselt.

`{"satirlar":[KAYIT+kayip,...],"ozet":[OZET,...]}` döndür. Satırları epsilon ve adıma göre sırala, kaybı altı ondalık basamağa yuvarla. Her özet `{"epsilon":E,"taban_dogruluk":X,"son_adim":N,"son_dogruluk":X,"maksimum_kayip":X}` içersin ve epsilona göre sıralı olsun. Son adım en büyük adım, maksimum kayıp o epsilondaki en yüksek ham kayıptır. Girdileri değiştirme.

```starter
from ai_guvence_veri import json_yukle

def pgd_egri_raporu(kayitlar):
    # KUSURLU BAŞLANGIÇ KODU: taban doğruluğundan kayıp hesaplamadan ve özet üretmeden döndürüyor!
    return {"satirlar": list(kayitlar) if isinstance(kayitlar, list) else [], "ozet": []}

print("Örnek PGD eğri raporu:", pgd_egri_raporu(json_yukle("veri/pgd_kayitlari.json")))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-08")
```

```test
import copy
K = [
    {"epsilon": 0.1, "adim": 2, "dogruluk": 0.5, "l_inf": 0.1},
    {"epsilon": 0.1, "adim": 0, "dogruluk": 0.8, "l_inf": 0},
    {"epsilon": 0.2, "adim": 1, "dogruluk": 0.4, "l_inf": 0.2},
    {"epsilon": 0.1, "adim": 1, "dogruluk": 0.6, "l_inf": 0.05},
    {"epsilon": 0.2, "adim": 0, "dogruluk": 0.8, "l_inf": 0},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        sonuc = fn(K)
        if K != once or [(x["epsilon"], x["adim"]) for x in sonuc["satirlar"]] != [(0.1, 0), (0.1, 1), (0.1, 2), (0.2, 0), (0.2, 1)]:
            return False
        if [x["kayip"] for x in sonuc["satirlar"]] != [0.0, 0.2, 0.3, 0.0, 0.4]:
            return False
        if sonuc["ozet"] != [
            {"epsilon": 0.1, "taban_dogruluk": 0.8, "son_adim": 2, "son_dogruluk": 0.5, "maksimum_kayip": 0.3},
            {"epsilon": 0.2, "taban_dogruluk": 0.8, "son_adim": 1, "son_dogruluk": 0.4, "maksimum_kayip": 0.4},
        ]:
            return False
        yuvarla = fn([{"epsilon": 1, "adim": 0, "dogruluk": 1, "l_inf": 0}, {"epsilon": 1, "adim": 1, "dogruluk": 2 / 3, "l_inf": 1}])
        if yuvarla["satirlar"][1]["kayip"] != 0.333333 or yuvarla["ozet"][0]["maksimum_kayip"] != 0.333333:
            return False
        tolerans = fn([{"epsilon": 0.1, "adim": 0, "dogruluk": 0.8, "l_inf": 0}, {"epsilon": 0.1, "adim": 1, "dogruluk": 0.8, "l_inf": 0.1 + 1e-9}])
        if tolerans["satirlar"][1]["l_inf"] != 0.1 + 1e-9:
            return False
        for kayitlar in [
            None, tuple(K), {}, [], [None], [dict(K[1], ek=1)], [K[1], K[0], K[0]], [K[1], dict(K[0], dogruluk=float("nan"))],
            [dict(K[0], epsilon=True), K[1]], [dict(K[0], epsilon="0.1"), K[1]],
            [dict(K[0], epsilon=float("nan")), K[1]], [dict(K[0], epsilon=-0.1), K[1]], [dict(K[0], epsilon=1.1), K[1]],
            [dict(K[0], adim=True), K[1]], [dict(K[0], adim=1.0), K[1]], [dict(K[0], adim=-1), K[1]],
            [dict(K[0], dogruluk=True), K[1]], [dict(K[0], dogruluk="0.5"), K[1]],
            [dict(K[0], dogruluk=float("inf")), K[1]], [dict(K[0], dogruluk=-0.1), K[1]], [dict(K[0], dogruluk=1.1), K[1]],
            [dict(K[0], l_inf=True), K[1]], [dict(K[0], l_inf="0.1"), K[1]],
            [dict(K[0], l_inf=-0.1), K[1]], [dict(K[0], l_inf=0.2), K[1]], [dict(K[0], l_inf=0.1 + 1.5e-9), K[1]],
            [K[0]], [dict(K[1], l_inf=0.1)],
        ]:
            try:
                fn(kayitlar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(pgd_egri_raporu), "taban, eğri sırası, kayıp ve özet korunmalı")
def m_dogruluk(kayitlar):
    return pgd_egri_raporu([dict(x, dogruluk=0.8) for x in kayitlar])
def m_adim(kayitlar):
    return pgd_egri_raporu([dict(x, adim=0, l_inf=0) for x in kayitlar])
def m_sil(kayitlar):
    return pgd_egri_raporu(kayitlar[:3])
for ad, mutant in [("doğruluğu değiştiren", m_dogruluk), ("adımları silen", m_adim), ("noktaları silen", m_sil)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def pgd_egri_raporu(kayitlar):
    import math
    if not isinstance(kayitlar, list):
        raise ValueError("kayıtlar liste olmalı")
    if not kayitlar:
        raise ValueError("kayıtlar boş olamaz")
    ciftler = set()
    tabanlar = {}
    for kayit in kayitlar:
        if not isinstance(kayit, dict):
            raise ValueError("kayıt sözlük olmalı")
        if set(kayit) != {"epsilon", "adim", "dogruluk", "l_inf"}:
            raise ValueError("kayıt şeması geçersiz")
        for alan in ("epsilon", "dogruluk", "l_inf"):
            deger = kayit[alan]
            if isinstance(deger, bool) or not isinstance(deger, (int, float)):
                raise ValueError("ölçüm sayı olmalı")
            if not math.isfinite(deger):
                raise ValueError("ölçüm sonlu olmalı")
            if deger < 0 or deger > 1:
                raise ValueError("ölçüm aralık dışında")
        adim = kayit["adim"]
        if isinstance(adim, bool) or not isinstance(adim, int):
            raise ValueError("adım tamsayı olmalı")
        if adim < 0:
            raise ValueError("adım negatif olamaz")
        cift = (kayit["epsilon"], adim)
        if cift in ciftler:
            raise ValueError("epsilon ve adım çifti yinelenemez")
        if kayit["l_inf"] > kayit["epsilon"] + 1e-9:
            raise ValueError("L∞ epsilon bütçesini aşamaz")
        if adim == 0:
            if kayit["l_inf"] != 0:
                raise ValueError("taban adımında L∞ sıfır olmalı")
            tabanlar[kayit["epsilon"]] = kayit["dogruluk"]
        ciftler.add(cift)
    epsilonlar = {x["epsilon"] for x in kayitlar}
    if any(epsilon not in tabanlar for epsilon in epsilonlar):
        raise ValueError("her epsilon için taban adımı gerekli")
    satirlar = []
    for kayit in kayitlar:
        kayip = tabanlar[kayit["epsilon"]] - kayit["dogruluk"]
        satirlar.append({"epsilon": kayit["epsilon"], "adim": kayit["adim"], "dogruluk": kayit["dogruluk"], "l_inf": kayit["l_inf"], "kayip": round(kayip, 6), "_ham_kayip": kayip})
    satirlar.sort(key=lambda x: (x["epsilon"], x["adim"]))
    ozet = []
    for epsilon in sorted(epsilonlar):
        grup = [x for x in satirlar if x["epsilon"] == epsilon]
        son = max(grup, key=lambda x: x["adim"])
        maksimum = max(x["_ham_kayip"] for x in grup)
        ozet.append({"epsilon": epsilon, "taban_dogruluk": tabanlar[epsilon], "son_adim": son["adim"], "son_dogruluk": son["dogruluk"], "maksimum_kayip": round(maksimum, 6)})
    for satir in satirlar:
        del satir["_ham_kayip"]
    return {"satirlar": satirlar, "ozet": ozet}
```

```hint
Önce bütün tabanları topla, sonra satır kayıplarını hesapla. Özeti epsilon gruplarına ayır; geçici ham kaybı son çıktıdan kaldır.
```
:::

::: anlat PyTorch `autograd` ve 64-32-4 MLP üzerinde canlı çok adımlı PGD eğrisi
İlk üç görevde PGD ayar doğrulamasını, çok adımlı projeksiyon izini ve epsilon-adım eğri raporunu sentetik dosyalar üzerinde kurdun. Şimdi aynı üç işlevi **`ai_lab.fgsm_siniflandirici()` ile gerçekten eğitilen PyTorch 64-32-4 MLP modeline** bağlıyoruz:

1. `canli-pgd-08` ayarı (`epsilon=0.15, alpha=0.06, adim=3`) `pgd_ayari_dogrula` ile doğrulanır.
2. İlk test örneğinde 3 iterasyon boyunca `torch.autograd.grad` ile gerçek çapraz entropi gradyanları hesaplanır ve `pgd_izini_uret` ile adım adım projeksiyon izi doğrulanır.
3. Tüm test kümesinde $\varepsilon \in \{0.1, 0.2\}$ ve $t \in \{0, 1, 2, 3\}$ adımlarında gerçekleşen model doğruluğu ve $L_\infty$ normu ölçülerek `pgd_egri_raporu` ile özetlenip kanıt dosyasına kaydedilir.
:::

::: gorev Gerçek deney · PyTorch autograd ile çok adımlı PGD ve saldırı gücü eğrisi
Önceki üç görevde yazdığın `pgd_ayari_dogrula(ayar)`, `pgd_izini_uret(x, gradyanlar, ayar)` ve `pgd_egri_raporu(kayitlar)` işlevlerini burada birleştir.

```meta
motor: ai-gercek
gereksinim: torch
timeout: 240
```

```starter
import math
import re
import ai_lab
from sandbox import ai_gercek_ai_guvence_08 as L

def pgd_ayari_dogrula(ayar):
    # KUSURLU BAŞLANGIÇ KODU: doğrulama yapmadan girdi sözlüğünü döndürüyor!
    return ayar

def pgd_izini_uret(x, gradyanlar, ayar):
    # KUSURLU BAŞLANGIÇ KODU: adımları ve projeksiyonu işletmeden boş iz döndürüyor!
    return {"id": "", "son": [], "l_inf": 0.0, "iz": []}

def pgd_egri_raporu(kayitlar):
    # KUSURLU BAŞLANGIÇ KODU: taban ve satır kayıplarını hesaplamadan boş rapor döndürüyor!
    return {"satirlar": [], "ozet": []}

if ai_lab.CALISTIR:
    L.goster(pgd_ayari_dogrula, pgd_izini_uret, pgd_egri_raporu)
```

```test
import ast
import copy
import ai_lab
from sandbox import ai_gercek_ai_guvence_08 as L

checks = []
_base_ok = ok
def ok(kosul, mesaj):
    checks.append(bool(kosul))
    return _base_ok(kosul, mesaj)

try:
    _parsed = ast.parse(src)
    for _node in ast.walk(_parsed):
        if isinstance(_node, ast.ImportFrom):
            if any(alias.name == '*' for alias in _node.names):
                ok(False, "Güvenlik/kopya denetimi: wildcard import yasak")
            for alias in _node.names:
                if "referans" in (alias.name or "") or "referans" in (alias.asname or ""):
                    ok(False, "Güvenlik/kopya denetimi: referans fonksiyon içe aktarılamaz")
        if isinstance(_node, ast.Name) and "referans" in _node.id:
            ok(False, "Güvenlik/kopya denetimi: referans kullanımı tespit edildi")
        if isinstance(_node, ast.Attribute) and "referans" in _node.attr:
            ok(False, "Güvenlik/kopya denetimi: referans nitelik kullanımı tespit edildi")
        if isinstance(_node, ast.Call):
            if isinstance(_node.func, ast.Name) and _node.func.id in ("getattr", "eval", "exec"):
                ok(False, f"Güvenlik/kopya denetimi: dinamik çağrı ({_node.func.id}) yasak")
except Exception:
    pass

for s in ai_lab.kod_denetimi(src, yasak=("pgd_ayari_dogrula_referans", "pgd_izini_uret_referans", "pgd_egri_raporu_referans", "kanit_yaz")):
    ok(False, f"Güvenlik/kopya denetimi: {s}")
if not all(checks):
    stop()

def _sozlesme_kontrol():
    try:
        A = {"id": "pgd-1", "epsilon": 0.15, "alpha": 0.1, "adim": 2}
        if pgd_ayari_dogrula(A) != A or pgd_ayari_dogrula(A) is A:
            return False
        for ba in [None, dict(A, alpha=0.2), dict(A, adim=0), dict(A, epsilon=True)]:
            try:
                pgd_ayari_dogrula(ba)
                return False
            except ValueError:
                pass

        X = [0.5, 0.95]
        G = [[1, 1], [-1, 1]]
        if pgd_izini_uret(X, G, A) != {"id": "pgd-1", "son": [0.5, 1.0], "l_inf": 0.05, "iz": [{"adim": 1, "x": [0.6, 1.0]}, {"adim": 2, "x": [0.5, 1.0]}]}:
            return False
        for bx, bg, bay in [(None, G, A), (X, G[:1], A), ([-0.1, 0.5], G, A)]:
            try:
                pgd_izini_uret(bx, bg, bay)
                return False
            except ValueError:
                pass

        K = [
            {"epsilon": 0.1, "adim": 1, "dogruluk": 0.6, "l_inf": 0.05},
            {"epsilon": 0.1, "adim": 0, "dogruluk": 0.8, "l_inf": 0},
        ]
        sk = pgd_egri_raporu(K)
        if sk["ozet"] != [{"epsilon": 0.1, "taban_dogruluk": 0.8, "son_adim": 1, "son_dogruluk": 0.6, "maksimum_kayip": 0.2}]:
            return False
        for bk in [None, [], [K[0]], [dict(K[1], l_inf=0.05)]]:
            try:
                pgd_egri_raporu(bk)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

def _birim1(fn):
    import copy
    A = {"id": "pgd-1", "epsilon": 0.15, "alpha": 0.1, "adim": 2}
    def sozlesme(fn):
        try:
            once = copy.deepcopy(A)
            sonuc = fn(A)
            if sonuc != A or A != once or sonuc is A:
                return False
            if fn(dict(A, id="a" * 64, epsilon=0, alpha=0, adim=1))["adim"] != 1:
                return False
            if fn(dict(A, epsilon=1, alpha=1))["alpha"] != 1:
                return False
            for ayar in [
                None, [], dict(A, ek=1), dict(A, id=""), dict(A, id="a b"), dict(A, id="a" * 65), dict(A, id=None),
                dict(A, epsilon=None), dict(A, epsilon=True), dict(A, epsilon="0.15"), dict(A, epsilon=float("nan")),
                dict(A, epsilon=float("inf")), dict(A, epsilon=-0.1), dict(A, epsilon=1.1),
                dict(A, alpha=None), dict(A, alpha=True), dict(A, alpha="0.1"), dict(A, alpha=float("nan")),
                dict(A, alpha=float("inf")), dict(A, alpha=-0.1), dict(A, alpha=1.1), dict(A, alpha=0.2),
                dict(A, epsilon=0, alpha=0.1), dict(A, adim=0), dict(A, adim=-1), dict(A, adim=True),
                dict(A, adim=1.0), dict(A, adim=None),
            ]:
                try:
                    fn(ayar)
                    return False
                except ValueError:
                    pass
            return True
        except Exception:
            return False
    return sozlesme(fn)

def _birim2(fn):
    import copy
    A = {"id": "pgd-1", "epsilon": 0.15, "alpha": 0.1, "adim": 2}
    X = [0.5, 0.95]
    G = [[1, 1], [-1, 1]]
    BEKLENEN = {"id": "pgd-1", "son": [0.5, 1.0], "l_inf": 0.05, "iz": [{"adim": 1, "x": [0.6, 1.0]}, {"adim": 2, "x": [0.5, 1.0]}]}
    def sozlesme(fn):
        try:
            xonce = copy.deepcopy(X)
            gonce = copy.deepcopy(G)
            aonce = copy.deepcopy(A)
            if fn(X, G, A) != BEKLENEN or X != xonce or G != gonce or A != aonce:
                return False
            proje = dict(A, epsilon=0.05, alpha=0.05, adim=1)
            if fn([0.5], [[1]], proje) != {"id": "pgd-1", "son": [0.55], "l_inf": 0.05, "iz": [{"adim": 1, "x": [0.55]}]}:
                return False
            sifir = dict(A, epsilon=0, alpha=0, adim=1)
            if fn([0], [[0]], sifir)["l_inf"] != 0:
                return False
            if fn([0, 1], [[0, 0]], sifir)["son"] != [0, 1]:
                return False
            ust = dict(A, epsilon=1, alpha=1, adim=1)
            if fn([0], [[1]], ust)["son"] != [1] or fn([0.05], [[-1]], dict(A, adim=1))["son"] != [0.0]:
                return False
            sifir_grad = fn([0.5], [[0]], dict(A, adim=1))
            if sifir_grad != {"id": "pgd-1", "son": [0.5], "l_inf": 0, "iz": [{"adim": 1, "x": [0.5]}]}:
                return False
            yuvarla = dict(A, epsilon=1 / 3, alpha=1 / 3, adim=1)
            if fn([0], [[1]], yuvarla) != {"id": "pgd-1", "son": [0.333333], "l_inf": 0.333333, "iz": [{"adim": 1, "x": [0.333333]}]}:
                return False
            for x, gradyanlar, ayar in [
                (None, G, A), (tuple(X), G, A), (X, tuple(G), A), (X, [(1, 1), (-1, 1)], A), ([], [[]], dict(A, adim=1)),
                (X, None, A), (X, G, None), ({}, G, A), ([], G, A), (X, [], A),
                (X, G[:1], A), (X, [[1], [-1, 1]], A), (X, [[1, 1], None], A),
                ([True, 0.95], G, A), (["0.5", 0.95], G, A), ([float("nan"), 0.95], G, A),
                ([-0.1, 0.95], G, A), ([-0.1, 1.1], G, A), ([1.1, 0.95], G, A),
                (X, [[True, 1], [-1, 1]], A), (X, [["1", 1], [-1, 1]], A),
                (X, [[float("inf"), 1], [-1, 1]], A),
                (X, G, dict(A, id="a" * 65)), (X, G, dict(A, alpha=0.2)),
                (X, G, dict(A, epsilon=-0.1, alpha=-0.2)), (X, G, dict(A, epsilon=1.1, alpha=1)),
                (X, G, dict(A, ek=1)), (X, G, dict(A, id=123)), (X, G, dict(A, epsilon="0.1")), (X, G, dict(A, epsilon=float("nan"))),
                (X, [G[0]], dict(A, adim=True)), (X, G, dict(A, adim=2.0)),
                (X, G, dict(A, epsilon=True)), (X, G, dict(A, adim=0)), (X, [], dict(A, adim=0)),
            ]:
                try:
                    fn(x, gradyanlar, ayar)
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
        {"epsilon": 0.1, "adim": 2, "dogruluk": 0.5, "l_inf": 0.1},
        {"epsilon": 0.1, "adim": 0, "dogruluk": 0.8, "l_inf": 0},
        {"epsilon": 0.2, "adim": 1, "dogruluk": 0.4, "l_inf": 0.2},
        {"epsilon": 0.1, "adim": 1, "dogruluk": 0.6, "l_inf": 0.05},
        {"epsilon": 0.2, "adim": 0, "dogruluk": 0.8, "l_inf": 0},
    ]
    def sozlesme(fn):
        try:
            once = copy.deepcopy(K)
            sonuc = fn(K)
            if K != once or [(x["epsilon"], x["adim"]) for x in sonuc["satirlar"]] != [(0.1, 0), (0.1, 1), (0.1, 2), (0.2, 0), (0.2, 1)]:
                return False
            if [x["kayip"] for x in sonuc["satirlar"]] != [0.0, 0.2, 0.3, 0.0, 0.4]:
                return False
            if sonuc["ozet"] != [
                {"epsilon": 0.1, "taban_dogruluk": 0.8, "son_adim": 2, "son_dogruluk": 0.5, "maksimum_kayip": 0.3},
                {"epsilon": 0.2, "taban_dogruluk": 0.8, "son_adim": 1, "son_dogruluk": 0.4, "maksimum_kayip": 0.4},
            ]:
                return False
            yuvarla = fn([{"epsilon": 1, "adim": 0, "dogruluk": 1, "l_inf": 0}, {"epsilon": 1, "adim": 1, "dogruluk": 2 / 3, "l_inf": 1}])
            if yuvarla["satirlar"][1]["kayip"] != 0.333333 or yuvarla["ozet"][0]["maksimum_kayip"] != 0.333333:
                return False
            tolerans = fn([{"epsilon": 0.1, "adim": 0, "dogruluk": 0.8, "l_inf": 0}, {"epsilon": 0.1, "adim": 1, "dogruluk": 0.8, "l_inf": 0.1 + 1e-9}])
            if tolerans["satirlar"][1]["l_inf"] != 0.1 + 1e-9:
                return False
            for kayitlar in [
                None, tuple(K), {}, [], [None], [dict(K[1], ek=1)], [K[1], K[0], K[0]], [K[1], dict(K[0], dogruluk=float("nan"))],
                [dict(K[0], epsilon=True), K[1]], [dict(K[0], epsilon="0.1"), K[1]],
                [dict(K[0], epsilon=float("nan")), K[1]], [dict(K[0], epsilon=-0.1), K[1]], [dict(K[0], epsilon=1.1), K[1]],
                [dict(K[0], adim=True), K[1]], [dict(K[0], adim=1.0), K[1]], [dict(K[0], adim=-1), K[1]],
                [dict(K[0], dogruluk=True), K[1]], [dict(K[0], dogruluk="0.5"), K[1]],
                [dict(K[0], dogruluk=float("inf")), K[1]], [dict(K[0], dogruluk=-0.1), K[1]], [dict(K[0], dogruluk=1.1), K[1]],
                [dict(K[0], l_inf=True), K[1]], [dict(K[0], l_inf="0.1"), K[1]],
                [dict(K[0], l_inf=-0.1), K[1]], [dict(K[0], l_inf=0.2), K[1]], [dict(K[0], l_inf=0.1 + 1.5e-9), K[1]],
                [K[0]], [dict(K[1], l_inf=0.1)],
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

ok(_birim1(pgd_ayari_dogrula), "pgd_ayari_dogrula tam birim sözleşmesini geçmeli")
ok(_birim2(pgd_izini_uret), "pgd_izini_uret tam birim sözleşmesini geçmeli")
ok(_birim3(pgd_egri_raporu), "pgd_egri_raporu tam birim sözleşmesini geçmeli")
ok(_sozlesme_kontrol(), "pgd_ayari_dogrula, pgd_izini_uret ve pgd_egri_raporu sözleşme kontrollerini geçmeli")
if not all(checks):
    stop()

try:
    rapor = L.deney(pgd_ayari_dogrula, pgd_izini_uret, pgd_egri_raporu)
except ai_lab.GercekLabYok as e:
    ok(False, str(e))
    stop()
except Exception as e:
    ok(False, f"GERÇEK PGD DENEYİ YAPILAMADI: {type(e).__name__}: {e}")
    stop()

k = rapor["kontroller"]
ok(k["ayar_uyumu"], f"pgd_ayari_dogrula canlı PGD ayarında referansla uyuşmalı: {rapor['ayar']}")
ok(k["iz_uyumu"], f"pgd_izini_uret PyTorch autograd gradyanlarında referansla uyuşmalı: {rapor['ornek_iz']}")
ok(k["egri_uyumu"] and k["saldiri_kaybi_pozitif"], f"pgd_egri_raporu canlı PGD eğrisinde referansla uyuşmalı: {rapor['ozet']['egri_ozeti']}")

kabul = all(checks)
kanit_yolu = ai_lab.kanit_yaz("guvence-08-pgd-egri", dict(rapor, kaynak="gercek", kabul=kabul))
o = rapor["ozet"]
print(f"GERÇEK PGD DENEYİ: torch={o['torch_surum']} temiz={o['temiz_dogruluk']} egri={o['egri_ozeti']} kanıt={kanit_yolu}")
```

```solution
import math
import re
import ai_lab
from sandbox import ai_gercek_ai_guvence_08 as L

def pgd_ayari_dogrula(ayar):
    if not isinstance(ayar, dict) or set(ayar) != {"id", "epsilon", "alpha", "adim"}:
        raise ValueError("ayar şeması geçersiz")
    if not isinstance(ayar["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", ayar["id"]):
        raise ValueError("kimlik geçersiz")
    for alan in ("epsilon", "alpha"):
        deger = ayar[alan]
        if isinstance(deger, bool) or not isinstance(deger, (int, float)) or not math.isfinite(deger) or deger < 0 or deger > 1:
            raise ValueError("bütçe geçersiz")
    if ayar["alpha"] > ayar["epsilon"]:
        raise ValueError("alpha epsilonu aşamaz")
    if isinstance(ayar["adim"], bool) or not isinstance(ayar["adim"], int) or ayar["adim"] <= 0:
        raise ValueError("adım geçersiz")
    return {"id": ayar["id"], "epsilon": ayar["epsilon"], "alpha": ayar["alpha"], "adim": ayar["adim"]}

def pgd_izini_uret(x, gradyanlar, ayar):
    a = pgd_ayari_dogrula(ayar)
    if not isinstance(x, list) or not x:
        raise ValueError("x geçersiz")
    for deger in x:
        if isinstance(deger, bool) or not isinstance(deger, (int, float)) or not math.isfinite(deger) or deger < 0 or deger > 1:
            raise ValueError("x öğesi geçersiz")
    if not isinstance(gradyanlar, list) or len(gradyanlar) != a["adim"]:
        raise ValueError("gradyanlar geçersiz")
    for gradyan in gradyanlar:
        if not isinstance(gradyan, list) or len(gradyan) != len(x):
            raise ValueError("gradyan boyutu geçersiz")
        for deger in gradyan:
            if isinstance(deger, bool) or not isinstance(deger, (int, float)) or not math.isfinite(deger):
                raise ValueError("gradyan değeri geçersiz")
    x0 = list(x)
    son = list(x)
    iz = []
    for adim, gradyan in enumerate(gradyanlar, 1):
        yeni = []
        for i, gv in enumerate(gradyan):
            isaret = 1 if gv > 0 else -1 if gv < 0 else 0
            deger = min(1, max(0, son[i] + a["alpha"] * isaret))
            deger = min(x0[i] + a["epsilon"], max(x0[i] - a["epsilon"], deger))
            yeni.append(deger)
        son = yeni
        iz.append({"adim": adim, "x": [round(v, 6) for v in son]})
    return {"id": a["id"], "son": [round(v, 6) for v in son], "l_inf": round(max(abs(u - v) for u, v in zip(son, x0)), 6), "iz": iz}

def pgd_egri_raporu(kayitlar):
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar geçersiz")
    ciftler = set()
    tabanlar = {}
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"epsilon", "adim", "dogruluk", "l_inf"}:
            raise ValueError("kayıt şeması geçersiz")
        for alan in ("epsilon", "dogruluk", "l_inf"):
            deger = kayit[alan]
            if isinstance(deger, bool) or not isinstance(deger, (int, float)) or not math.isfinite(deger) or deger < 0 or deger > 1:
                raise ValueError("ölçüm geçersiz")
        adim = kayit["adim"]
        if isinstance(adim, bool) or not isinstance(adim, int) or adim < 0:
            raise ValueError("adım geçersiz")
        cift = (kayit["epsilon"], adim)
        if cift in ciftler or kayit["l_inf"] > kayit["epsilon"] + 1e-9:
            raise ValueError("çift/l_inf geçersiz")
        if adim == 0:
            if kayit["l_inf"] != 0:
                raise ValueError("taban l_inf sıfır olmalı")
            tabanlar[kayit["epsilon"]] = kayit["dogruluk"]
        ciftler.add(cift)
    epsilonlar = {x["epsilon"] for x in kayitlar}
    if any(e not in tabanlar for e in epsilonlar):
        raise ValueError("taban eksik")
    satirlar = []
    for kayit in kayitlar:
        kayip = tabanlar[kayit["epsilon"]] - kayit["dogruluk"]
        satirlar.append({"epsilon": kayit["epsilon"], "adim": kayit["adim"], "dogruluk": kayit["dogruluk"], "l_inf": kayit["l_inf"], "kayip": round(kayip, 6), "_ham": kayip})
    satirlar.sort(key=lambda x: (x["epsilon"], x["adim"]))
    ozet = []
    for epsilon in sorted(epsilonlar):
        grup = [x for x in satirlar if x["epsilon"] == epsilon]
        son = max(grup, key=lambda x: x["adim"])
        maks = max(x["_ham"] for x in grup)
        ozet.append({"epsilon": epsilon, "taban_dogruluk": tabanlar[epsilon], "son_adim": son["adim"], "son_dogruluk": son["dogruluk"], "maksimum_kayip": round(maks, 6)})
    for s in satirlar:
        del s["_ham"]
    return {"satirlar": satirlar, "ozet": ozet}

if ai_lab.CALISTIR:
    L.goster(pgd_ayari_dogrula, pgd_izini_uret, pgd_egri_raporu)
```

```hint
Önceki üç görevde yazdığın `pgd_ayari_dogrula`, `pgd_izini_uret` ve `pgd_egri_raporu` işlevlerini eksiksiz taşı; canlı deneyde PyTorch `autograd` gradyanlarıyla 3 adımlı PGD izi ve doğruluk eğrisi hesaplanır.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Çok adımlı tırmanış ve çift projeksiyon (`PGD`) (30 sn).** "`PGD`, her iterasyonda $\alpha \cdot \text{sign}(\nabla_x \mathcal{L})$ adımı atar; çıktıyı önce geçerli `[0, 1]` uzayına kırpar, ardından her zaman ilk temiz girdi $x_0$ etrafındaki $[x_0 - \varepsilon, x_0 + \varepsilon]$ kutusuna geri projekte eder."
2. **Adım ve bütçe eğrilerini okumak (35 sn).** "Her $\varepsilon$ serisi `adim = 0` (`L∞ = 0`) temiz tabanıyla başlar; iterasyonlar ilerledikçe doğruluk kaybının nerede doygunluğa ulaştığı tek adımlı FGSM'in kaçırdığı doğrusal olmayan kayıp vadilerini görünür kılar."
3. **Gradyan maskelemesi sınırı (30 sn).** "Eğrinin düz kalması sertifikalı sağlamlık kanıtı değildir; kırık veya rastgeleleştirilmiş gradyanlar düz PGD'yi de yanıltabilir."
4. **Soru (25 sn).** "Projeksiyon kutusunu başlangıçtaki $x_0 \pm \varepsilon$ yerine bir önceki adım $x_{t-1} \pm \varepsilon$ etrafında kurarsan $K$ adım sonunda gerçek $L_\infty$ bütçesi neye dönüşür?"
:::
