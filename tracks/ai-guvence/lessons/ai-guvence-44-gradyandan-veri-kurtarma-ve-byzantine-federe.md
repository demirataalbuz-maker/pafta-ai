---
id: ai-guvence-44
title: Gradyandan Veri Kurtarma ve Byzantine-Robust Federe Öğrenme
summary: Deep Leakage from Gradients (DLG) gradyan eşleştirme kaybını yaz, federe öğrenmede Krum ve koordinat bazlı kırpılmış ortalamayla (trimmed mean) Bizans saldırısını GPU'da filtrele.
esleme: ai-guvence-11, ai-guvence-16, ai-guvence-35
timeout: 60
---

::: anlat "Veriyi göndermedim, yalnız gradyan gönderdim" neden gizlilik sağlamaz?
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Tek bir eğitim örneğinin ağırlık gradyanı $\nabla_\theta \mathcal{L}(x, y)$ paylaşıldığında, rastgele bir sahte girdi (`dummy input`) gradyan eşleştirme ile optimize edilerek gizli girdi kurtarılabilir (`Deep Leakage from Gradients`) | İlk üç görev: `veri/dlg_federe.json` içindeki **sentetik** gradyan vektörleri. Final: gerçek el yazısı rakam görüntüsünün ikinci mertebe autograd ile gradyandan kurtarılması (`DLG`) ve 7 istemcili gerçek federe eğitimde Bizans saldırısına karşı `FedAvg` / `Krum` / `trimmed mean` test doğruluğu | Büyük yığın (`batch`) boyutlarında ve yüksek gürültülü diferansiyel gizlilik altında her örneğin piksel piksel kurtarılabileceğini kanıtlamaz |
| Tek bir Bizans (`Byzantine`) istemcisi düz ortalamayı (`FedAvg`) istediği yöne çekebilir; `Krum` ve kırpılmış ortalama uç değerleri dışlar | Kare Öklidyen uzaklık, kosinüs uzaklığı, `Krum` komşu skoru ve koordinat bazlı kırpılmış ortalama | $n < 2f + 3$ olduğunda veya saldırganlar dürüst kümenin içine sızdığında `Krum`'un zehirlemeyi tamamen durduracağını garanti etmez |

> [!NOT]
> Görevler `veri/dlg_federe.json` dosyasını okur; dosya sentetiktir. Setup her Çalıştır/Kontrol Et adımında geçici kopya kurar; değişiklikler taşınmaz, **kalıcılık yoktur**. Ekranda ayrı dosya görüntüleyici yoktur; içeriği görmek için `print` kullan. Gizli testler ayrıdır. Final yeni model indirmez ve GPU varsa onu kullanır.

Federe öğrenme (`federated learning`) ham veriyi istemcide tutup sunucuya yalnızca ağırlık gradyanlarını göndermeyi vaat eder. Ancak bu mimari iki temel güvence sorusuyla karşılaşır: **Meraklı sunucu gradyandan veriyi geri çözebilir mi (`privacy`)?** ve **Kötücül bir istemci sahte gradyanla merkezi modeli bozabilir mi (`integrity`)?**

**1. `Deep Leakage from Gradients` (`DLG`):** Bir doğrusal katmanda $\frac{\partial \mathcal{L}}{\partial W}$ gradyanı, katman girdisi $x$ ile hata sinyalinin dış çarpımıdır. Zhu vd. 2019 (`DLG`) ve Geiping vd. 2020, sunucunun rastgele bir sahte girdi $x'$ başlatıp gerçek gradyan $g$ ile sahte gradyan $g' = \nabla_\theta \mathcal{L}(x', y')$ arasındaki farkı minimize ederek $x' \to x$ kurtarması yapabildiğini göstermiştir:
$$\mathcal{L}_{\text{DLG}}(g, g') = \|g - g'\|_2^2 = \sum_{j=1}^d (g_j - g'_j)^2, \qquad d_{\cos}(g, g') = 1 - \frac{g \cdot g'}{\|g\|_2 \|g'\|_2}$$

**2. `Byzantine-robust` Federe Birleştirme (`Krum` ve `Trimmed Mean`):** Standart `FedAvg` ($\frac{1}{n}\sum_{i=1}^n g_i$) tek bir Bizans (`Byzantine`) istemcisinin $g_{\text{kötü}} = -1000 \cdot g_{\text{dürüst}}$ göndermesiyle tamamen çökertilebilir.
- **`Krum` (Blanchard vd. 2017):** $n$ istemciden en fazla $f$ tanesi Bizans ise ($n \ge 2f + 3$), her istemci $i$ için diğer istemcilere olan kare Öklidyen uzaklıklar $\|g_i - g_j\|_2^2$ ($j \ne i$) küçükten büyüğe sıralanır ve en yakın $n - f - 2$ komşunun uzaklıkları toplanarak $S(i)$ skoru bulunur. En düşük $S(i)$ skoruna sahip istemci (eşitlikte küçük indis) seçilir.
- **Koordinat bazlı kırpılmış ortalama (`Trimmed Mean`, Yin vd. 2018):** Her koordinat $j$ bağımsız olarak sıralanır, en küçük $k$ ve en büyük $k$ değer ($2k < n$) atılır ve kalan $n - 2k$ değerin aritmetik ortalaması alınır.

**Saldırgan ne dener?** `Krum` savunmasını aşmak için uzak bir uç değer göndermek yerine, dürüst istemcilerin varyans kabuğunun hemen kenarına birden fazla işbirlikçi (`colluding`) Bizans vektörü yerleştirerek `Krum`'un kötücül vektörü "merkez" sanmasını dener (Fang vd. 2020).

**Savunma neden kırılır?** Gradyan sıkıştırma veya diferansiyel gizlilik (`DP-SGD`) uygulanmadan paylaşılan ham gradyanlar `DLG` saldırısına açıktır; `FedAvg` ise hiçbir aykırı değer kontrolü yapmadığı için tek bir bozuk istemciye bile dayanıksızdır.

**Görev 1 ve 2'de sık tuzaklar:** `kosinus_uzaklik` için benzerliği `1.0`'dan çıkarmayı unutmak. `Krum` içinde $i = j$ uzaklığını (`0.0`) komşu listesine dahil edip $n - f - 2$ komşudan birini boşa harcamak.

Kaynaklar: [Zhu vd. 2019](https://arxiv.org/abs/1906.08935), [Geiping vd. 2020](https://arxiv.org/abs/2003.14053), [Blanchard vd. 2017](https://arxiv.org/abs/1703.02757), [Yin vd. 2018](https://arxiv.org/abs/1803.01498). Bu dersteki bütün sayılar yalnız yerel kanıttan gelir.

Köprü: ai-guvence-11 veri zehirlemesini, ai-guvence-16 diferansiyel gizliliği inceler; bu ders federe gradyan paylaşımında hem gizlilik sızıntısını (`DLG`) hem Bizans sağlamlığını (`Krum`) birleştirir.
:::

::: tahmin Tek bir Bizans istemcisi düz ortalamayı ne kadar saptırır?
Çıktıyı tahmin et, sonra Çalıştır ile karşılaştır.
```python
istemciler = [0.10, 0.12, 0.09, 0.11, -15.0]
duz_ort = sum(istemciler) / len(istemciler)
sirali = sorted(istemciler)[1:-1]
kirpilmis = sum(sirali) / len(sirali)
print("Düz ortalama (FedAvg):", round(duz_ort, 4))
print("Kırpılmış ortalama (k=1):", round(kirpilmis, 4))
```
???
```cikti
Düz ortalama (FedAvg): -2.916
Kırpılmış ortalama (k=1): 0.1
```
Tahmininle gerçek çıktı arasındaki farkı tezgâhta yorum satırı olarak yaz: 4 dürüst istemci `+0.1` civarındayken tek bir `-15.0` istemcisi `FedAvg` işaretini neden tamamen tersine çevirdi? Sonra üç kusurlu başlangıç kodunu çalıştır ve her birinin neyi kaçırdığını önce kendin teşhis et; açıklama çözümün ardından gelir.
:::

::: gorev 1 · DLG gradyan eşleştirme kaybı
`gradyan_eslestirme_kaybi(gercek_grad, sahte_grad)`: Aynı uzunlukta ($d \ge 1$) iki dolu liste, elemanları bool olmayan sonlu sayı ve her iki vektörün L2 normu $> 0$. Kare Öklidyen fark $\sum_j (g_j - s_j)^2$ ve kosinüs uzaklığı $1 - \frac{g \cdot s}{\|g\|_2 \|s\|_2}$ değerlerini `{"l2_fark": float, "kosinus_uzaklik": float}` olarak döndür. Geçersiz girdide veya sıfır normda `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-44")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def gradyan_eslestirme_kaybi(gercek_grad, sahte_grad):
    l2 = sum(abs(g - s) for g, s in zip(gercek_grad, sahte_grad))
    return {"l2_fark": l2, "kosinus_uzaklik": 0.0}

from ai_guvence_veri import json_yukle
v = json_yukle("veri/dlg_federe.json")["dlg"]
print("Başlangıç:", gradyan_eslestirme_kaybi(v["gercek_grad"], v["sahte_grad_baslangic"]))
print("Kurtarılmış:", gradyan_eslestirme_kaybi(v["gercek_grad"], v["sahte_grad_kurtarilmis"]))
```
```test
def sinama1(f):
    import copy, math, random
    def _r(g, s):
        ng = math.sqrt(sum(x * x for x in g)); ns = math.sqrt(sum(x * x for x in s))
        return {"l2_fark": float(sum((a - b) ** 2 for a, b in zip(g, s))), "kosinus_uzaklik": float(1.0 - sum(a * b for a, b in zip(g, s)) / (ng * ns))}
    def _y(a, b): return isinstance(a, dict) and set(a) == set(b) and all(abs(a[k] - b[k]) < 1e-12 for k in b)
    try:
        g = [3.0, 4.0]; s = [3.0, 4.0]; old = (list(g), list(s))
        if not _y(f(g, s), {"l2_fark": 0.0, "kosinus_uzaklik": 0.0}) or (g, s) != old: return False
        if not _y(f([1.0, 0.0], [-1.0, 0.0]), {"l2_fark": 4.0, "kosinus_uzaklik": 2.0}): return False
        if not _y(f([1.0, 0.0], [0.0, 2.0]), {"l2_fark": 5.0, "kosinus_uzaklik": 1.0}): return False
        rng = random.Random(44)
        for _ in range(25):
            d = rng.randint(2, 7)
            rg = [rng.uniform(-3, 3) for _ in range(d)]; rs = [rng.uniform(-3, 3) for _ in range(d)]
            if not _y(f(list(rg), list(rs)), _r(rg, rs)): return False
        for bad in ((None, s), (g, None), ([], []), ([0.0, 0.0], s), (g, [0.0, 0.0]), ([1.0], s), ([True, 1.0], s), (g, [float("nan"), 1.0])):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
ok(sinama1(gradyan_eslestirme_kaybi), "kare L2 farkı, kosinüs uzaklığı, sıfır norm kontrolü ve geçersiz girdi")
for ad, mut in [
    ("kosinüs benzerliği", lambda g, s: dict(gradyan_eslestirme_kaybi(g, s), kosinus_uzaklik=1.0 - gradyan_eslestirme_kaybi(g, s)["kosinus_uzaklik"])),
    ("L2 karekök", lambda g, s: dict(gradyan_eslestirme_kaybi(g, s), l2_fark=math.sqrt(gradyan_eslestirme_kaybi(g, s)["l2_fark"]) + 0.1)),
    ("hep sıfır", lambda g, s: {"l2_fark": 0.0, "kosinus_uzaklik": 0.0})
]:
    ok(not sinama1(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(gradyan_eslestirme_kaybi, _il.import_module('ai_gercek_ai_guvence_44').referans_gradyan_kaybi, ([0.6, -0.8, 0.4, 0.2], [-0.3, 0.5, -0.1, 0.4]), tohum=3690)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def gradyan_eslestirme_kaybi(gercek_grad, sahte_grad):
    if not isinstance(gercek_grad, list) or not isinstance(sahte_grad, list) or not gercek_grad or len(gercek_grad) != len(sahte_grad):
        raise ValueError("gradyan")
    for v in gercek_grad + sahte_grad:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v): raise ValueError("sayı")
    ng = math.sqrt(sum(g * g for g in gercek_grad))
    ns = math.sqrt(sum(s * s for s in sahte_grad))
    if ng <= 0 or ns <= 0: raise ValueError("sıfır norm")
    l2 = sum((g - s) ** 2 for g, s in zip(gercek_grad, sahte_grad))
    kos = 1.0 - sum(g * s for g, s in zip(gercek_grad, sahte_grad)) / (ng * ns)
    return {"l2_fark": float(l2), "kosinus_uzaklik": float(kos)}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    v = json_yukle("veri/dlg_federe.json")["dlg"]
    print("Başlangıç:", gradyan_eslestirme_kaybi(v["gercek_grad"], v["sahte_grad_baslangic"]))
    print("Kurtarılmış:", gradyan_eslestirme_kaybi(v["gercek_grad"], v["sahte_grad_kurtarilmis"]))
```
```hint
`l2_fark` için kare farkların toplamını al (karekök alma); `kosinus_uzaklik` için `1.0 - kosinus_benzerligi` hesapla.
```
:::

::: anlat Krum seçimiyle Bizans istemcisini dışlamak
$n$ istemci ve $f$ Bizans istemcisi için `Krum` önkoşulu $n \ge 2f + 3$'tür ($f \ge 0$). Her istemci $i$ için:
1. $j \ne i$ olan tüm diğer istemcilere kare Öklidyen uzaklık $d^2(i, j) = \sum_k (g_{i,k} - g_{j,k})^2$ hesaplanır.
2. Bu $n - 1$ uzaklık küçükten büyüğe sıralanır ve ilk $n - f - 2$ tanesinin toplamı `skorlar[i]` olur.
3. En küçük skora sahip indis (`min(range(n), key=lambda i: (skorlar[i], i))`) seçilir.

**Görev 2'de sık tuzaklar:** $n < 2f + 3$ olduğunda `ValueError` yükseltmemek. Kendisine olan uzaklığı (`i == j`) listeye katmak.
:::

::: gorev 2 · Byzantine-robust Krum seçimi
`krum_secimi(istemci_gradyanlari, bizans_sayisi)`: `istemci_gradyanlari` $n$ adet aynı uzunlukta ($d \ge 1$) dolu listeden oluşan liste; `bizans_sayisi` ($f \ge 0$) bool olmayan `int` ve $n \ge 2f + 3$. En yakın $n - f - 2$ komşunun kare Öklidyen uzaklık toplamını en küçük yapan istemciyi bul ve `{"secilen_indis": int, "secilen_gradyan": [...], "skorlar": [...]}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-44")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def krum_secimi(istemci_gradyanlari, bizans_sayisi):
    n = len(istemci_gradyanlari)
    d = len(istemci_gradyanlari[0])
    ort = [sum(g[j] for g in istemci_gradyanlari) / n for j in range(d)]
    return {"secilen_indis": 0, "secilen_gradyan": ort, "skorlar": [0.0] * n}

from ai_guvence_veri import json_yukle
v = json_yukle("veri/dlg_federe.json")["federe"]
print(krum_secimi(v["istemci_gradyanlari"], v["bizans_sayisi"]))
```
```test
def sinama2(f):
    import copy, math, random
    def _r(ig, b):
        n = len(ig); m = n - b - 2; sk = []
        for i in range(n):
            u = sorted(sum((x - y) ** 2 for x, y in zip(ig[i], ig[j])) for j in range(n) if i != j)
            sk.append(float(sum(u[:m])))
        sec = min(range(n), key=lambda i: (sk[i], i))
        return {"secilen_indis": int(sec), "secilen_gradyan": [float(v) for v in ig[sec]], "skorlar": sk}
    def _y(a, b):
        if not isinstance(a, dict) or set(a) != set(b) or a["secilen_indis"] != b["secilen_indis"]: return False
        if any(len(a[alan]) != len(b[alan]) for alan in ("secilen_gradyan", "skorlar")):
            return False
        return all(abs(p - q) < 1e-12 for p, q in zip(a["secilen_gradyan"], b["secilen_gradyan"])) and all(abs(p - q) < 1e-12 for p, q in zip(a["skorlar"], b["skorlar"]))
    try:
        ig = [[0.1, 0.2], [0.11, 0.19], [0.09, 0.21], [0.1, 0.2], [10.0, -10.0]]; old = copy.deepcopy(ig)
        if not _y(f(ig, 1), _r(ig, 1)) or ig != old: return False
        if f(ig, 1)["secilen_indis"] == 4: return False
        for bozuk in ([[], [], []], [[1.0], [1.0], 1]):
            try:
                f(bozuk, 0)
                return False
            except ValueError:
                pass
        rng = random.Random(4444)
        for _ in range(25):
            b = rng.randint(0, 2); n = rng.randint(2 * b + 3, 2 * b + 6); d = rng.randint(2, 5)
            rig = [[rng.uniform(-2, 2) for _ in range(d)] for _ in range(n)]
            if not _y(f([list(x) for x in rig], b), _r(rig, b)): return False
        for bad in ((None, 1), ([], 0), ([[1.0], [2.0], [3.0], [4.0]], 1), (ig, -1), (ig, 2), (ig, True), ([[1.0, 2.0], [1.0], [1.0, 2.0]], 0), ([[True, 1.0], [1.0, 1.0], [1.0, 1.0]], 0)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
ok(sinama2(krum_secimi), "Krum komşu uzaklığı, 2f+3 önkoşulu, seçim ve geçersiz girdi")
for ad, mut in [
    ("max skor seç", lambda ig, b: dict(krum_secimi(ig, b), secilen_indis=max(range(len(ig)), key=lambda i: krum_secimi(ig, b)["skorlar"][i]))),
    ("tüm komşuları topla", lambda ig, b: krum_secimi(ig, 0) if b > 0 else dict(krum_secimi(ig, b), skorlar=[0.0] * len(ig))),
    ("sabit 0", lambda ig, b: {"secilen_indis": 0, "secilen_gradyan": list(ig[0]), "skorlar": [0.0] * len(ig)})
]:
    ok(not sinama2(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(krum_secimi, _il.import_module('ai_gercek_ai_guvence_44').referans_krum, ([[0.1, -0.2, 0.3], [0.12, -0.18, 0.28], [0.09, -0.22, 0.31], [0.11, -0.19, 0.29], [-15.0, 20.0, -12.0]], 1), tohum=2321)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def krum_secimi(istemci_gradyanlari, bizans_sayisi):
    if not isinstance(istemci_gradyanlari, list) or not istemci_gradyanlari: raise ValueError("liste")
    if isinstance(bizans_sayisi, bool) or not isinstance(bizans_sayisi, int) or bizans_sayisi < 0: raise ValueError("bizans")
    n = len(istemci_gradyanlari)
    if n < 2 * bizans_sayisi + 3: raise ValueError("n < 2f + 3")
    if not isinstance(istemci_gradyanlari[0], list) or not istemci_gradyanlari[0]: raise ValueError("vektör")
    d = len(istemci_gradyanlari[0])
    for g in istemci_gradyanlari:
        if not isinstance(g, list) or len(g) != d: raise ValueError("boyut")
        for v in g:
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v): raise ValueError("sayı")
    m = n - bizans_sayisi - 2
    skorlar = []
    for i in range(n):
        uz = sorted(sum((a - b) ** 2 for a, b in zip(istemci_gradyanlari[i], istemci_gradyanlari[j])) for j in range(n) if i != j)
        skorlar.append(float(sum(uz[:m])))
    sec = min(range(n), key=lambda i: (skorlar[i], i))
    return {"secilen_indis": int(sec), "secilen_gradyan": [float(v) for v in istemci_gradyanlari[sec]], "skorlar": skorlar}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    v = json_yukle("veri/dlg_federe.json")["federe"]
    print(krum_secimi(v["istemci_gradyanlari"], v["bizans_sayisi"]))
```
```hint
Her `i` için `j != i` olanların kare fark toplamlarını sırala, ilk `n - bizans_sayisi - 2` tanesini topla ve en küçük toplamı veren indisi seç.
```
:::

::: anlat Koordinat bazlı kırpılmış ortalama (Trimmed Mean)
`Krum` tek bir istemcinin gradyanını seçerken, **koordinat bazlı kırpılmış ortalama (`trimmed mean`)** her koordinatta en küçük `kirpma_k` ve en büyük `kirpma_k` değeri atıp kalan $n - 2k$ istemcinin ortalamasını alır ($2k < n$). Sıralama değerlerin hangi istemciden geldiğini bilmez. Dürüst bir güncelleme de uçta kalabilir ve her koordinatta farklı istemciler elenebilir.

**Yerel PyTorch ölçümü.** Sentetik hedeflerle beş istemci gradyanı hesaplandı. Dördü birbirine yakın, beşincisi aykırıydı. Temiz ölçüm kaybı başlangıçta 4,0000 idi. Aynı öğrenme adımından sonra düz ortalamayla 7,8400, Krum ile 3,2761 ve kırpılmış ortalamayla 3,2640 oldu. Bu kayıt tek bir eğitim adımını gösterir. Deney betiği ve ham ölçümler proje çıktılarındaki ai-guvence-44-federasyon-deneyi.py ve ai-guvence-44-federasyon-kanit.json dosyalarındadır.

Krum bir istemcinin güncellemesini seçerken kırpılmış ortalama birden fazla istemciden değer alır. Bu iki işlem aykırı güncellemelerin etkisini azaltmayı amaçlar. İstemci gradyanlarını kimlerin görebildiği ve yayımlanan sonucun ne kadar bilgi taşıdığı ayrı gizlilik sorularıdır. Kayıp düşse bile hangi gizlilik sorusu yanıtsız kalır?

**Görev 3'te sık tuzaklar:** $2 \cdot \text{kirpma\_k} \ge n$ olduğunda boş dilim oluşmasını engellememek. Koordinat bazlı sıralamak yerine vektör normuna göre sıralamak.
:::

::: gorev 3 · Koordinat bazlı kırpılmış ortalama
`kirpilmis_ortalama(istemci_gradyanlari, kirpma_k)`: `istemci_gradyanlari` $n$ adet aynı uzunlukta ($d \ge 1$) dolu liste; `kirpma_k` ($\ge 0$) bool olmayan `int` ve $2 \cdot \text{kirpma\_k} < n$. Her koordinatta sıralı değerlerin `[kirpma_k : n - kirpma_k]` diliminin aritmetik ortalamasını içeren yeni `float` listesi döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-44")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def kirpilmis_ortalama(istemci_gradyanlari, kirpma_k):
    n = len(istemci_gradyanlari)
    d = len(istemci_gradyanlari[0])
    return [sum(g[j] for g in istemci_gradyanlari) / n for j in range(d)]

from ai_guvence_veri import json_yukle
v = json_yukle("veri/dlg_federe.json")["federe"]
print(kirpilmis_ortalama(v["istemci_gradyanlari"], v["kirpma_k"]))
```
```test
def sinama3(f):
    import copy, math, random
    def _r(ig, k):
        n = len(ig); d = len(ig[0])
        return [float(sum(sorted(g[j] for g in ig)[k : n - k]) / (n - 2 * k)) for j in range(d)]
    def _y(a, b): return isinstance(a, list) and len(a) == len(b) and all(abs(p - q) < 1e-12 for p, q in zip(a, b))
    try:
        ig = [[1.0, 10.0], [2.0, 20.0], [3.0, 30.0], [100.0, -500.0], [-50.0, 40.0]]; old = copy.deepcopy(ig)
        if not _y(f(ig, 1), [2.0, 20.0]) or ig != old: return False
        if not _y(f(ig, 0), _r(ig, 0)): return False
        for bozuk in ([[], [], []], [[1.0], [1.0], 1]):
            try:
                f(bozuk, 0)
                return False
            except ValueError:
                pass
        rng = random.Random(4445)
        for _ in range(25):
            k = rng.randint(0, 2); n = rng.randint(2 * k + 1, 2 * k + 6); d = rng.randint(1, 6)
            rig = [[rng.uniform(-10, 10) for _ in range(d)] for _ in range(n)]
            if not _y(f([list(x) for x in rig], k), _r(rig, k)): return False
        for bad in ((None, 0), ([], 0), ([[]], 0), ([[1.0], [2.0]], 1), ([[1.0], [2.0], [3.0]], 2), (ig, -1), (ig, True), ([[1.0, 2.0], [1.0]], 0), ([[True, 1.0], [1.0, 2.0], [1.0, 2.0]], 0)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
ok(sinama3(kirpilmis_ortalama), "koordinat sıralaması, uç kırpma, 2k<n sınırı ve geçersiz girdi")
for ad, mut in [
    ("kırpma yok", lambda ig, k: [sum(g[j] for g in ig) / len(ig) for j in range(len(ig[0]))]),
    ("yalnız üstten kırp", lambda ig, k: [sum(sorted(g[j] for g in ig)[:len(ig) - k]) / (len(ig) - k) for j in range(len(ig[0]))]),
    ("yanlış payda", lambda ig, k: [x * (len(ig) - 2 * k) / len(ig) for x in kirpilmis_ortalama(ig, k)])
]:
    ok(not sinama3(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(kirpilmis_ortalama, _il.import_module('ai_gercek_ai_guvence_44').referans_kirpilmis_ortalama, ([[0.1, -0.2, 0.3], [0.12, -0.18, 0.28], [0.09, -0.22, 0.31], [0.11, -0.19, 0.29], [-15.0, 20.0, -12.0]], 1), tohum=3069)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def kirpilmis_ortalama(istemci_gradyanlari, kirpma_k):
    if not isinstance(istemci_gradyanlari, list) or not istemci_gradyanlari: raise ValueError("liste")
    if isinstance(kirpma_k, bool) or not isinstance(kirpma_k, int) or kirpma_k < 0: raise ValueError("kirpma_k")
    n = len(istemci_gradyanlari)
    if 2 * kirpma_k >= n: raise ValueError("2k >= n")
    if not isinstance(istemci_gradyanlari[0], list) or not istemci_gradyanlari[0]: raise ValueError("vektör")
    d = len(istemci_gradyanlari[0])
    for g in istemci_gradyanlari:
        if not isinstance(g, list) or len(g) != d: raise ValueError("boyut")
        for v in g:
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v): raise ValueError("sayı")
    out = []
    for j in range(d):
        s = sorted(g[j] for g in istemci_gradyanlari)[kirpma_k : n - kirpma_k]
        out.append(float(sum(s) / len(s)))
    return out

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    v = json_yukle("veri/dlg_federe.json")["federe"]
    print(kirpilmis_ortalama(v["istemci_gradyanlari"], v["kirpma_k"]))
```
```hint
`kirpma_k == 0` iken tüm elemanları koru (`[0 : n]`); `kirpma_k > 0` iken `sorted(...)[kirpma_k : n - kirpma_k]` diliminin toplamını `n - 2 * kirpma_k` değerine böl.
```
:::

::: anlat Hata vitrini · çalışmış yanlış rapor
Yazar, kusurlu başlangıç kodlarını görünür sentetik veriyle gerçekten çalıştırdı ve sonucu `outputs/yeni-ai-guvence-44/gorunur-run-1.json` dosyasına kaydetti. 5 istemciden 4'ü `[0.10, -0.20, 0.30]` civarında dürüst gradyan gönderirken 5. istemci `[-15.0, 20.0, -12.0]` Bizans gradyanı gönderdiğinde, kusurlu kod `[-2.916, 3.842, -2.164]` döndürerek merkezi güncellemeyi tamamen ters yöne saptırır. Doğru `Krum` kodu 3. dürüst istemciyi (`[0.11, -0.19, 0.29]`, skor `0.0009`, Bizans skoru `1525.13`) seçer; doğru kırpılmış ortalama ise `[0.1033, -0.1967, 0.2967]` üretir.

Bu kaydedilmiş bir hesaplama çıktısıdır, model yanıtı değildir ve rapor sentetiktir. Federe sunucuda düz ortalama kullanan bir sistemde tek bir bozuk istemcinin bütün turu nasıl ele geçirdiğini kendi cümlenle açıkla. Gerçek finaldeki ölçüm ayrıca üretilir; bu sayılar onun yerine konmaz.
:::

::: anlat Gerçek deney: gerçek rakam görüntüsünü gradyandan kurtarmak ve gerçek federe eğitimde Bizans istemcisi
Final, `sklearn` `load_digits` (1797 gerçek el yazısı rakam, 8×8 piksel) üzerinde iki gerçek deney yürütür.

**1. Deep Leakage from Gradients (DLG).** Bir istemcinin test kümesinden alınan **gerçek bir rakam görüntüsü**, sigmoid aktivasyonlu bir MLP'den (64 → 32 → 10) geçirilir. İstemcinin federe öğrenmede sunucuya göndereceği gradyan alınır. Saldırgan (merak eden sunucu) rastgele bir görüntüden başlar. `torch.autograd.grad(..., create_graph=True)` ile ikinci mertebe türev alarak, sahte görüntünün gradyanını gerçek gradyana eşleştirir (300 Adam adımı). Kurtarılan görüntü, ayrı eğitilmiş bağımsız bir rakam sınıflandırıcısına gösterilir. Başlangıç ve son gradyan kayıplarını **senin `gradyan_eslestirme_kaybi` işlevin** ölçer.

**2. Bizans dayanıklı federe eğitim.** Eğitim verisi 7 istemciye bölünür. Küresel model 40 tur eğitilir: her turda her istemci kendi verisinden 64 örneklik gradyan gönderir, sunucu birleştirir ve bir adım atar. Bir istemci Bizans saldırganıdır: dürüst ortalamanın **−10 katını** gönderir. Dört koşu karşılaştırılır:
- saldırısız FedAvg,
- saldırılı FedAvg,
- saldırılı Krum,
- saldırılı kırpılmış ortalama.

Saldırılı ilk turun gerçek gradyanlarında **senin `krum_secimi` ve `kirpilmis_ortalama` işlevlerin** bağımsız referansla karşılaştırılır.

Yazarın sekiz GPU koşusunda (her biri ~2–8 sn) şu sonuçlar alındı:
- **DLG her seferinde tam kurtarma yaptı.** Gradyan L2 farkı 0.35–0.56'dan ~1e-14'e indi. Piksel MSE ~0'dır (rastgele bir görüntünün MSE'si 0.22–0.29); korelasyon 1.000. Gizli "3", "5", "6", "7" görüntüleri piksel piksel geri geldi ve bağımsız sınıflandırıcı hepsini doğru rakam olarak tanıdı. Tek örnekli batch, bilinen etiket ve pürüzsüz (sigmoid) aktivasyon, DLG'nin en güçlü olduğu durumdur.
- **Tek bir Bizans istemcisi FedAvg'ı çökertti:** test doğruluğu saldırısız 0.62–0.82'den saldırılı **0.08–0.12**'ye indi (şans 0.10).
- **Kırpılmış ortalama** saldırı altında 0.48–0.70'te kaldı.
- **Krum** 0.37–0.78'de kaldı. Krum Bizans istemcisini her koşuda reddetti, ama her turda **tek bir** istemcinin gürültülü gradyanını kullanır. Bu yüzden sonucu koşudan koşuya çok oynar; kimi koşuda kırpılmış ortalamadan iyi, kimi koşuda çok kötüdür. Sağlamlığın bir bedeli vardır.

**Kanıt dosyasını oku:** Soru 1: `gizli_goruntu` ile `kurtarilan_goruntu` neden birebir aynı? Batch'te 8 görüntü olsaydı ya da gradyana gürültü eklenseydi (diferansiyel gizlilik) ne değişirdi? Soru 2: Krum'un düşük doğruluğu ile kırpılmış ortalamanın yüksek doğruluğu arasındaki farkı, her birinin kaç istemcinin bilgisini kullandığıyla açıkla. Cevabını tezgâhta yorum olarak yaz; otomatik test bu serbest açıklamayı puanlamaz.
:::

::: gorev Gerçek deney · Autograd ile DLG girdi kurtarma ve Krum/Trimmed Mean birleştirme
Önceki üç görevin `gradyan_eslestirme_kaybi`, `krum_secimi` ve `kirpilmis_ortalama` işlevlerini birleştir. Çalıştır gerçek tabloyu gösterir; Kontrol Et önce üç sözleşmeyi gizli verilerle sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
ortam: gpu
timeout: 180
```
```starter
import ai_lab
import math
def gradyan_eslestirme_kaybi(gercek_grad, sahte_grad):
    l2 = sum(abs(g - s) for g, s in zip(gercek_grad, sahte_grad))
    return {"l2_fark": l2, "kosinus_uzaklik": 0.0}
def krum_secimi(istemci_gradyanlari, bizans_sayisi):
    n = len(istemci_gradyanlari)
    d = len(istemci_gradyanlari[0])
    ort = [sum(g[j] for g in istemci_gradyanlari) / n for j in range(d)]
    return {"secilen_indis": 0, "secilen_gradyan": ort, "skorlar": [0.0] * n}
def kirpilmis_ortalama(istemci_gradyanlari, kirpma_k):
    n = len(istemci_gradyanlari)
    d = len(istemci_gradyanlari[0])
    return [sum(g[j] for g in istemci_gradyanlari) / n for j in range(d)]
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_44 as D
    D.goster(gradyan_eslestirme_kaybi, krum_secimi, kirpilmis_ortalama)
```
```test
import ai_lab, math
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('referans_gradyan_kaybi', 'referans_krum', 'referans_kirpilmis_ortalama', 'kanit_yaz', '_yakin'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
gradyan_eslestirme_kaybi = need("gradyan_eslestirme_kaybi")
krum_secimi = need("krum_secimi")
kirpilmis_ortalama = need("kirpilmis_ortalama")
def sinama1(f):
    import copy, math, random
    def _r(g, s):
        ng = math.sqrt(sum(x * x for x in g)); ns = math.sqrt(sum(x * x for x in s))
        return {"l2_fark": float(sum((a - b) ** 2 for a, b in zip(g, s))), "kosinus_uzaklik": float(1.0 - sum(a * b for a, b in zip(g, s)) / (ng * ns))}
    def _y(a, b): return isinstance(a, dict) and set(a) == set(b) and all(abs(a[k] - b[k]) < 1e-12 for k in b)
    try:
        g = [3.0, 4.0]; s = [3.0, 4.0]; old = (list(g), list(s))
        if not _y(f(g, s), {"l2_fark": 0.0, "kosinus_uzaklik": 0.0}) or (g, s) != old: return False
        if not _y(f([1.0, 0.0], [-1.0, 0.0]), {"l2_fark": 4.0, "kosinus_uzaklik": 2.0}): return False
        rng = random.Random(44)
        for _ in range(25):
            d = rng.randint(2, 7)
            rg = [rng.uniform(-3, 3) for _ in range(d)]; rs = [rng.uniform(-3, 3) for _ in range(d)]
            if not _y(f(list(rg), list(rs)), _r(rg, rs)): return False
        for bad in ((None, s), ([0.0, 0.0], s), (g, [0.0, 0.0]), ([1.0], s), ([True, 1.0], s)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama1(gradyan_eslestirme_kaybi), "kare L2 farkı, kosinüs uzaklığı, sıfır norm kontrolü ve geçersiz girdi")
for ad, mut in [
    ("kosinüs benzerliği", lambda g, s: dict(gradyan_eslestirme_kaybi(g, s), kosinus_uzaklik=1.0 - gradyan_eslestirme_kaybi(g, s)["kosinus_uzaklik"])),
    ("L2 karekök", lambda g, s: dict(gradyan_eslestirme_kaybi(g, s), l2_fark=math.sqrt(gradyan_eslestirme_kaybi(g, s)["l2_fark"]) + 0.1)),
    ("hep sıfır", lambda g, s: {"l2_fark": 0.0, "kosinus_uzaklik": 0.0})
]:
    kontrol(not sinama1(mut), "mutant reddedildi: " + ad)
def sinama2(f):
    import copy, math, random
    def _r(ig, b):
        n = len(ig); m = n - b - 2; sk = []
        for i in range(n):
            u = sorted(sum((x - y) ** 2 for x, y in zip(ig[i], ig[j])) for j in range(n) if i != j)
            sk.append(float(sum(u[:m])))
        sec = min(range(n), key=lambda i: (sk[i], i))
        return {"secilen_indis": int(sec), "secilen_gradyan": [float(v) for v in ig[sec]], "skorlar": sk}
    def _y(a, b):
        if not isinstance(a, dict) or set(a) != set(b) or a["secilen_indis"] != b["secilen_indis"]: return False
        if any(len(a[alan]) != len(b[alan]) for alan in ("secilen_gradyan", "skorlar")):
            return False
        return all(abs(p - q) < 1e-12 for p, q in zip(a["secilen_gradyan"], b["secilen_gradyan"])) and all(abs(p - q) < 1e-12 for p, q in zip(a["skorlar"], b["skorlar"]))
    try:
        ig = [[0.1, 0.2], [0.11, 0.19], [0.09, 0.21], [0.1, 0.2], [10.0, -10.0]]; old = copy.deepcopy(ig)
        if not _y(f(ig, 1), _r(ig, 1)) or ig != old: return False
        for bozuk in ([[], [], []], [[1.0], [1.0], 1]):
            try:
                f(bozuk, 0)
                return False
            except ValueError:
                pass
        rng = random.Random(4444)
        for _ in range(25):
            b = rng.randint(0, 2); n = rng.randint(2 * b + 3, 2 * b + 6); d = rng.randint(2, 5)
            rig = [[rng.uniform(-2, 2) for _ in range(d)] for _ in range(n)]
            if not _y(f([list(x) for x in rig], b), _r(rig, b)): return False
        for bad in ((None, 1), ([[1.0], [2.0], [3.0], [4.0]], 1), (ig, -1), (ig, 2), (ig, True)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama2(krum_secimi), "Krum komşu uzaklığı, 2f+3 önkoşulu, seçim ve geçersiz girdi")
for ad, mut in [
    ("max skor seç", lambda ig, b: dict(krum_secimi(ig, b), secilen_indis=max(range(len(ig)), key=lambda i: krum_secimi(ig, b)["skorlar"][i]))),
    ("tüm komşuları topla", lambda ig, b: krum_secimi(ig, 0) if b > 0 else dict(krum_secimi(ig, b), skorlar=[0.0] * len(ig))),
    ("sabit 0", lambda ig, b: {"secilen_indis": 0, "secilen_gradyan": list(ig[0]), "skorlar": [0.0] * len(ig)})
]:
    kontrol(not sinama2(mut), "mutant reddedildi: " + ad)
def sinama3(f):
    import copy, math, random
    def _r(ig, k):
        n = len(ig); d = len(ig[0])
        return [float(sum(sorted(g[j] for g in ig)[k : n - k]) / (n - 2 * k)) for j in range(d)]
    def _y(a, b): return isinstance(a, list) and len(a) == len(b) and all(abs(p - q) < 1e-12 for p, q in zip(a, b))
    try:
        ig = [[1.0, 10.0], [2.0, 20.0], [3.0, 30.0], [100.0, -500.0], [-50.0, 40.0]]; old = copy.deepcopy(ig)
        if not _y(f(ig, 1), [2.0, 20.0]) or ig != old: return False
        for bozuk in ([[], [], []], [[1.0], [1.0], 1]):
            try:
                f(bozuk, 0)
                return False
            except ValueError:
                pass
        rng = random.Random(4445)
        for _ in range(25):
            k = rng.randint(0, 2); n = rng.randint(2 * k + 1, 2 * k + 6); d = rng.randint(1, 6)
            rig = [[rng.uniform(-10, 10) for _ in range(d)] for _ in range(n)]
            if not _y(f([list(x) for x in rig], k), _r(rig, k)): return False
        for bad in ((None, 0), ([[1.0], [2.0]], 1), (ig, -1), (ig, True)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama3(kirpilmis_ortalama), "koordinat sıralaması, uç kırpma, 2k<n sınırı ve geçersiz girdi")
for ad, mut in [
    ("kırpma yok", lambda ig, k: [sum(g[j] for g in ig) / len(ig) for j in range(len(ig[0]))]),
    ("yalnız üstten kırp", lambda ig, k: [sum(sorted(g[j] for g in ig)[:len(ig) - k]) / (len(ig) - k) for j in range(len(ig[0]))]),
    ("yanlış payda", lambda ig, k: [x * (len(ig) - 2 * k) / len(ig) for x in kirpilmis_ortalama(ig, k)])
]:
    kontrol(not sinama3(mut), "mutant reddedildi: " + ad)
# farksal tarama (final)
import importlib as _il
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_R = _il.import_module('sandbox.ai_gercek_ai_guvence_44')
for _ad, _ref, _taban, _toh in (
    ('gradyan_eslestirme_kaybi', 'referans_gradyan_kaybi', ([0.6, -0.8, 0.4, 0.2], [-0.3, 0.5, -0.1, 0.4]), 4212),
    ('krum_secimi', 'referans_krum', ([[0.1, -0.2, 0.3], [0.12, -0.18, 0.28], [0.09, -0.22, 0.31], [0.11, -0.19, 0.29], [-15.0, 20.0, -12.0]], 1), 2843),
    ('kirpilmis_ortalama', 'referans_kirpilmis_ortalama', ([[0.1, -0.2, 0.3], [0.12, -0.18, 0.28], [0.09, -0.22, 0.31], [0.11, -0.19, 0.29], [-15.0, 20.0, -12.0]], 1), 3591),
):
    _t, _g = _ff(need(_ad), getattr(_R, _ref), _taban, tohum=_toh)
    kontrol(_t, "farksal tarama (" + _ad + "): bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
if not all(checks): stop()
from sandbox import ai_gercek_ai_guvence_44 as D
try: r = D.deney(gradyan_eslestirme_kaybi, krum_secimi, kirpilmis_ortalama)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r["kayip_ayni"], "gerçek DLG gradyanlarında eşleştirme kaybı bağımsız hesapla aynı")
kontrol(r["krum_ayni"], "gerçek istemci gradyanlarında Krum seçimi bağımsız hesapla aynı")
kontrol(r["kirp_ayni"], "gerçek istemci gradyanlarında kırpılmış ortalama bağımsız hesapla aynı")
kontrol(r["dlg_son_kayip"]["l2_fark"] < r["dlg_ilk_kayip"]["l2_fark"], "DLG optimizasyonu gradyan eşleştirme kaybını düşürdü")
kontrol(r["kurtarma_mse"] < 0.1 * r["rastgele_goruntu_mse"] and r["rakam_kurtarildi"], "gizli rakam görüntüsü gradyandan kurtarıldı: MSE %.4f (rastgele %.4f), bağımsız sınıflandırıcı %d gördü (gerçek %d)" % (r["kurtarma_mse"], r["rastgele_goruntu_mse"], r["hakem_tahmini"], r["gizli_rakam"]))
kontrol(r["krum_secilen_indis"] != r["bizans_indis"], "Krum Bizans istemcisini reddetti")
fl = r["federe_test_dogrulugu"]
kontrol(fl["saldiri_fedavg"] < fl["temiz_fedavg"] - 0.4, "tek Bizans istemcisi FedAvg eğitimini çökertti: %.3f -> %.3f" % (fl["temiz_fedavg"], fl["saldiri_fedavg"]))
kontrol(fl["saldiri_kirpilmis"] > fl["saldiri_fedavg"] + 0.3 and fl["saldiri_krum"] > fl["saldiri_fedavg"] + 0.15, "kırpılmış ortalama (%.3f) ve Krum (%.3f) saldırı altında öğrenmeyi sürdürdü" % (fl["saldiri_kirpilmis"], fl["saldiri_krum"]))
ai_lab.kanit_yaz("ai-guvence-44-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-guvence-44", "deney": r})
```
```solution
import ai_lab
import math
def gradyan_eslestirme_kaybi(gercek_grad, sahte_grad):
    if not isinstance(gercek_grad, list) or not isinstance(sahte_grad, list) or not gercek_grad or len(gercek_grad) != len(sahte_grad):
        raise ValueError("gradyan")
    for v in gercek_grad + sahte_grad:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v): raise ValueError("sayı")
    ng = math.sqrt(sum(g * g for g in gercek_grad))
    ns = math.sqrt(sum(s * s for s in sahte_grad))
    if ng <= 0 or ns <= 0: raise ValueError("sıfır norm")
    l2 = sum((g - s) ** 2 for g, s in zip(gercek_grad, sahte_grad))
    kos = 1.0 - sum(g * s for g, s in zip(gercek_grad, sahte_grad)) / (ng * ns)
    return {"l2_fark": float(l2), "kosinus_uzaklik": float(kos)}
def krum_secimi(istemci_gradyanlari, bizans_sayisi):
    if not isinstance(istemci_gradyanlari, list) or not istemci_gradyanlari: raise ValueError("liste")
    if isinstance(bizans_sayisi, bool) or not isinstance(bizans_sayisi, int) or bizans_sayisi < 0: raise ValueError("bizans")
    n = len(istemci_gradyanlari)
    if n < 2 * bizans_sayisi + 3: raise ValueError("n < 2f + 3")
    if not isinstance(istemci_gradyanlari[0], list) or not istemci_gradyanlari[0]: raise ValueError("vektör")
    d = len(istemci_gradyanlari[0])
    for g in istemci_gradyanlari:
        if not isinstance(g, list) or len(g) != d: raise ValueError("boyut")
        for v in g:
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v): raise ValueError("sayı")
    m = n - bizans_sayisi - 2
    skorlar = []
    for i in range(n):
        uz = sorted(sum((a - b) ** 2 for a, b in zip(istemci_gradyanlari[i], istemci_gradyanlari[j])) for j in range(n) if i != j)
        skorlar.append(float(sum(uz[:m])))
    sec = min(range(n), key=lambda i: (skorlar[i], i))
    return {"secilen_indis": int(sec), "secilen_gradyan": [float(v) for v in istemci_gradyanlari[sec]], "skorlar": skorlar}
def kirpilmis_ortalama(istemci_gradyanlari, kirpma_k):
    if not isinstance(istemci_gradyanlari, list) or not istemci_gradyanlari: raise ValueError("liste")
    if isinstance(kirpma_k, bool) or not isinstance(kirpma_k, int) or kirpma_k < 0: raise ValueError("kirpma_k")
    n = len(istemci_gradyanlari)
    if 2 * kirpma_k >= n: raise ValueError("2k >= n")
    if not isinstance(istemci_gradyanlari[0], list) or not istemci_gradyanlari[0]: raise ValueError("vektör")
    d = len(istemci_gradyanlari[0])
    for g in istemci_gradyanlari:
        if not isinstance(g, list) or len(g) != d: raise ValueError("boyut")
        for v in g:
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v): raise ValueError("sayı")
    out = []
    for j in range(d):
        s = sorted(g[j] for g in istemci_gradyanlari)[kirpma_k : n - kirpma_k]
        out.append(float(sum(s) / len(s)))
    return out
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_44 as D
    D.goster(gradyan_eslestirme_kaybi, krum_secimi, kirpilmis_ortalama)
```
```hint
Üç işlevi aynen birleştir. DLG gradyan kaybının düşüşünü ve Krum/kırpılmış ortalamanın Bizans sapmasını nasıl bastırdığını incele.
```
:::

::: anlat Sınır
Bu ders küçük bir sigmoid MLP'de, tek örnekli batch ve bilinen etiketle `Deep Leakage from Gradients` kurtarmasını gösterir. Büyük batch'ler, ReLU ağları, gradyan sıkıştırma ve diferansiyel gizlilik altında kurtarma çok zorlaşır; tam kurtarma garantisi verilmez. Federe kısım 8×8 rakamlarla 7 istemcili gerçek bir eğitimdir. Ama tek ve kaba bir Bizans saldırısı vardır; dürüst gradyanlara yakın kalan uyarlanabilir saldırılar (ör. ALIE, IPM) ve koordineli Bizans kümeleri ölçülmez.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **'Yalnız gradyan gönderdim' yanılgısı (`DLG`) (35 sn).** "Doğrusal katman gradyanı doğrudan katman girdisiyle hata sinyalinin dış çarpımını taşır; meraklı sunucu sahte bir girdiyi $\|g - g'\|_2^2$ gradyan farkını ikinci mertebe türevle küçülterek optimize ettiğinde tek örnekli rakam görüntüsünü piksel piksel geri kurtarır."
2. **Bizans çöküşü vs `Krum` ve `Trimmed Mean` (35 sn).** "Tek bir Bizans istemcisinin $-10\times$ zıt gradyanı düz `FedAvg` ortalamasını şans düzeyine çökertir; `Krum` en yakın $n-f-2$ komşulu tek istemciyi seçerek, koordinat bazlı kırpılmış ortalama ise her boyutta uç $k$ değeri atarak öğrenmeyi korur."
3. **Sağlamlık–varyans–gizlilik üçgeni (25 sn).** "`Krum` tek istemci seçtiği için varyansı yüksektir; üstelik sağlam birleştirme bütünlüğü korur ama sunucunun bireysel gradyanları görmesini engellemez."
4. **Soru (25 sn).** "Federe eğitimde hem `DLG` sızıntısını hem Bizans saptırmasını aynı anda azaltmak için güvenli toplama (`secure aggregation`) ile sağlam birleştirmeyi nasıl birleştirmek gerekir?"
:::
