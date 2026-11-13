---
id: ai-uretim-01
title: "Sıfırdan Autograd Motoru, Computational Graph ve Backpropagation"
track: ai-uretim
order: 1
duration_minutes: 35
difficulty: orta
xp: 260
prerequisites: []
tags: [autograd, backpropagation, computational-graph, topological-sort, chain-rule, pytorch]
summary: "Dinamik hesaplama grafiğinde (DAG) ters mod otomatik türevi, topolojik sıralı geri yayılımı ve linear katman VJP gradyanlarını sıfırdan uygula; SmolLM2 üzerinde doğrula."
esleme: ai-matematik-04, ai-temel-09
---

::: anlat
## Autograd ve computational graph

Bir loss değerinin parametrelere göre türevini hesaplamak için işlemler arasındaki bağımlılıkları izleriz. Bu derste chain rule, topological sort ve birden fazla koldan gelen gradient katkılarının toplanmasını uygulayacaksın. Önce tek skaler yolu takip et; sonra aynı fikri bir linear layer hesabına taşı.

Bu derste kara kutuyu tamamen parçalıyoruz: Önce türev almanın neden **Symbolic Differentiation** veya **Numerical Differentiation** olmadığını göreceğiz, ardından **Directed Acyclic Graph (DAG)** üzerinde **Topological Sort** ve **Chain Rule (Zincir Kuralı)** işleten kendi saf Python `TensorValue` motorumuzu yazacağız ve son olarak gerçek üretim sistemlerinde **Custom CUDA / PyTorch `torch.autograd.Function`** çekirdeklerinin nasıl kodlandığını inceleyeceğiz.

---

### 1. Neden Numerical veya Symbolic Değil de `Reverse-Mode Autograd`?

Bir sinir ağında $N$ adet ağırlık parametresi ($\theta \in \mathbb{R}^N$, örneğin Llama-3 70B için $N = 70 \times 10^9$) ve tek bir skaler kayıp değeri ($\mathcal{L} \in \mathbb{R}$) vardır. Amacımız gradyan vektörünü ($\nabla_\theta \mathcal{L} = \left[\frac{\partial \mathcal{L}}{\partial \theta_1}, \dots, \frac{\partial \mathcal{L}}{\partial \theta_N}\right]$) hesaplamaktır:

1. **Numerical Differentiation (Sayısal Türev / Sonlu Farklar):**
   $$\frac{\partial \mathcal{L}}{\partial \theta_i} \approx \frac{\mathcal{L}(\theta_i + \epsilon) - \mathcal{L}(\theta_i - \epsilon)}{2\epsilon}$$
   - **Neden İmkansız?** $70\text{ Milyar}$ parametre için ileri yayılımı (**Forward Pass**) $70\text{ Milyar}$ kez tekrar çalıştırmak gerekir! Üstelik kayan nokta (**Floating-Point**) yuvarlama hataları (`Truncation & Round-off Error`) yüzünden `FP16 / BF16` hassasiyetinde tamamen çöker.
2. **Symbolic Differentiation (Sembolik Türev — Mathematica / SymPy):**
   - **Neden Çöker?** $100$ katmanlı bir Transformer'ın cebirsel türev ifadesini açtığında **Expression Swell (İfade Şişmesi)** yaşanır; ortak ara hesaplamalar milyonlarca kez kopyalanır ve `if/else` veya `while` gibi kontrol akışlarında türev alınamaz.
3. **Reverse-Mode Automatic Differentiation (`Autograd`):**
   - **Forward Pass** sırasında yapılan her temel aritmetik işlem ($+, \times, \exp, \text{matmul}$) çalıştırıldığı anda dinamik bir **Computational Graph (Hesaplama Grafiği — DAG)** içine düğüm (**Node**) olarak kaydedilir.
   - **Backward Pass (backpropagation)** sırasında, çıktı skalerinden ($\mathcal{L}$) başlayarak geriye doğru **Topological Sort** sırasıyla **Chain Rule** uygulanır.
   - **Mucizevi Karmaşıklık Garantisi (*Baur-Strassen Teoremi*):** Giriş boyutu $N$ ne kadar büyük olursa olsun (ister $10$, ister $1\text{ Trilyon}$ parametre!), tek bir skaler çıktının tüm girdilere göre tam gradyanını hesaplamak, forward pass maliyetinin **en fazla $2\text{ ile }3$ katı ($O(1)$ çarpanı)** kadar işlem gerektirir!

```
                  FORWARD PASS (Değerleri Hesapla & Grafiği Kur)
        x = 2.0 ───────┐
                       ├──► (*) ──► u = -6.0 ───────┐
        w = -3.0 ──────┘                            ├──► (+) ──► L = -2.0
                                    b = 4.0 ────────┘
        ─────────────────────────────────────────────────────────────────
                  BACKWARD PASS (Chain Rule ile Gradyanları Akıt)
        dx = -3.0 ◄────┐
                       ├─── du/dx = w, du/dw = x ───┐
        dw = 2.0  ◄────┘                            ├─── dL/du = 1, dL/db = 1 ◄── dL/dL = 1.0
                                    db = 1.0 ◄──────┘
```

---

### 2. Chain Rule, Fan-Out (Gradient Accumulation) ve Topological Sort

Bir hesaplama grafiğinde $u$ düğümü, birden fazla alt düğüme ($v_1, v_2, \dots, v_k$) girdi olarak bağlanıyorsa (**Fan-Out / Dallanma** — örneğin Transformer içindeki **Residual Connection** $y = x + F(x)$), **Multivariable Chain Rule (Çok Değişkenli Zincir Kuralı)** devreye girer:

$$\frac{\partial \mathcal{L}}{\partial u} = \sum_{i=1}^{k} \frac{\partial \mathcal{L}}{\partial v_i} \cdot \frac{\partial v_i}{\partial u}$$

İşte PyTorch'ta kendi `Autograd` motorumuzu yazarken **iki altın mühendislik kuralı** buradan doğar:
1. **Neden `grad = ...` değil de `grad += ...` (`Gradient Accumulation`) kullanılır?**
   Çünkü aynı tensör $x$, grafikte iki farklı koldan kullanıldığında (örneğin $y = x \cdot x$ veya $y = x + \text{Attention}(x)$), her koldan gelen kısmi türev birbiri üzerine **toplanmalıdır (`+=`)**! Eğer `=` ile üzerine yazarsan önceki kolun gradyanını silersin. (PyTorch'ta her adımda `optimizer.zero_grad()` çağırmamızın sebebi de budur; çünkü `.backward()` gradyanları sıfırlamaz, mevcut `.grad` üstüne `+=` ile ekler!).
2. **Neden `Topological Sort` Zorunludur?**
   Bir $u$ düğümünün kendi ebeveynlerine gradyan gönderebilmesi için, $u$'yu kullanan **tüm** çocuk düğümlerin ($v_1, v_2, \dots$) geri yayılımını tamamlamış ve $u.grad$ üzerindeki toplamayı bitirmiş olması şarttır! Grafiği **Topological Order (Topolojik Sıra)** tersine göre gezmezsen, henüz yarım kalmış bir gradyanı geriye yayarak tamamen yanlış türevler hesaplarsın.

Şimdi çalışan saf Python kodumuzla sıfırdan kendi mini-PyTorch (`TensorValue`) motorumuzu inşa edelim ve bir sinir hücresinin (`tanh` aktivasyonlu) gradyanlarını doğrulayalım:

```python
import math

class TensorValue:
    """PyTorch Tensor nesnesinin kaput altındaki Reverse-Mode Autograd çekirdeği."""
    def __init__(self, data, _children=(), _op="", label=""):
        self.data = float(data)
        self.grad = 0.0
        self._backward = lambda: None
        self._prev = set(_children)
        self._op = _op
        self.label = label

    def __add__(self, other):
        other = other if isinstance(other, TensorValue) else TensorValue(other)
        out = TensorValue(self.data + other.data, (self, other), "+")
        def _backward():
            # Toplama kapısı: gelen gradyanı her iki kola aynen dağıtır (1.0 * out.grad)
            self.grad += 1.0 * out.grad
            other.grad += 1.0 * out.grad
        out._backward = _backward
        return out

    def __mul__(self, other):
        other = other if isinstance(other, TensorValue) else TensorValue(other)
        out = TensorValue(self.data * other.data, (self, other), "*")
        def _backward():
            # Çarpma kapısı (Swap Multiplier): d(x*y)/dx = y, d(x*y)/dy = x
            self.grad += other.data * out.grad
            other.grad += self.data * out.grad
        out._backward = _backward
        return out

    def tanh(self):
        t = math.tanh(self.data)
        out = TensorValue(t, (self,), "tanh")
        def _backward():
            # d(tanh(u))/du = 1 - tanh^2(u)
            self.grad += (1.0 - t ** 2) * out.grad
        out._backward = _backward
        return out

    def backward(self):
        # 1. Adım: Derinlik öncelikli arama (DFS Post-Order) ile Topological Sort
        topo = []
        visited = set()
        def build_topo(v):
            if v not in visited:
                visited.add(v)
                for child in v._prev:
                    build_topo(child)
                topo.append(v)
        build_topo(self)

        # 2. Adım: Hedef düğümün kendisine göre türevi dL/dL = 1.0
        self.grad = 1.0
        # 3. Adım: Ters topolojik sırada yerel _backward() kurallarını ateşle
        for node in reversed(topo):
            node._backward()

# Örnek: Fan-Out (x değişkeninin iki farklı kolda kullanılması: L = tanh(x * w + x))
x = TensorValue(2.0, label="x")
w = TensorValue(-0.5, label="w")
y = (x * w + x).tanh()
y.backward()
print(f"İleri Çıktı y = {y.data:.4f} | dx = {x.grad:.4f} | dw = {w.grad:.4f}")
```

---

### 3. Matris Kalkülüsü: Linear Katmanda (`Y = X @ W + b`) Vektörize Backpropagation

Skaler değişkenlerle grafik kurmak öğreticidir, ancak **GPU (`Tensor Cores`)** üzerinde trilyonlarca işlemi saniyede yapabilmek için her düğüm birer skaler değil, çok boyutlu bir **Tensor (Matris)** olmak zorundadır.

Bir Transformer bloğundaki en temel yapı taşı olan **Linear Projection** katmanını ele alalım:
- Girdi: $X \in \mathbb{R}^{B \times D_{\text{in}}}$ ($B$: örnek/token sayısı, $D_{\text{in}}$: giriş boyutu)
- Ağırlık: $W \in \mathbb{R}^{D_{\text{in}} \times D_{\text{out}}}$ ve Bias: $b \in \mathbb{R}^{D_{\text{out}}}$
- İleri geçiş (**Forward Pass**):
  $$Y = X W + b \quad \left(Y \in \mathbb{R}^{B \times D_{\text{out}}}\right)$$

Üst katmandan bize kayıp fonksiyonunun $Y$'ye göre gradyan matrisi $dY = \frac{\partial \mathcal{L}}{\partial Y} \in \mathbb{R}^{B \times D_{\text{out}}}$ geldiğinde, **Vector-Jacobian Product (VJP)** kuralları uyarınca üç gradyanı tek seferde matris çarpımıyla hesaplarız:

$$\frac{\partial \mathcal{L}}{\partial X} = dX = dY \cdot W^T \in \mathbb{R}^{B \times D_{\text{in}}}$$

$$\frac{\partial \mathcal{L}}{\partial W} = dW = X^T \cdot dY \in \mathbb{R}^{D_{\text{in}} \times D_{\text{out}}}$$

$$\frac{\partial \mathcal{L}}{\partial b} = db = \sum_{i=1}^{B} dY_{i,:} \in \mathbb{R}^{D_{\text{out}}} \quad (\text{Batch ekseni boyunca toplam})$$

> **Mühendislik İpucu (Boyut Analizi — Dimensional Analysis):** Matris türevlerinde formülü ezberlemene bile gerek yoktur! $dW$'nin boyutu $W$ ile aynı yani $(D_{\text{in}} \times D_{\text{out}})$ olmalıdır. Elimizde $X \in (B \times D_{\text{in}})$ ve $dY \in (B \times D_{\text{out}})$ varsa, iç boyutu $B$'yi yok edip $(D_{\text{in}} \times D_{\text{out}})$ elde etmenin **tek** cebirsel yolu $X^T \cdot dY$ çarpımıdır!

---

### 4. Gerçek Üretim Kodu: PyTorch `torch.autograd.Function` ile Özel Çekirdek Yazımı

Frontier AI laboratuvarlarında (OpenAI, Anthropic, DeepSeek) standart PyTorch operatörlerinin birleşimi bazen GPU belleğinde (`VRAM`) gereksiz ara tensörler tutar. Bu durumda `torch.autograd.Function` sınıfından miras alarak kendi özel **Forward** ve **Backward** çekirdeğimizi (`Custom Autograd Kernel`) yazarız:

```python norun
import torch

class FusedLinearSwishFunction(torch.autograd.Function):
    """
    Gerçek PyTorch Üretim Mimarisi:
    ctx.save_for_backward() ile Forward sırasında yalnız Backward için zorunlu
    tensörleri GPU HBM belleğinde saklar, backward() içinde VJP hesaplar.
    """
    @staticmethod
    def forward(ctx, x: torch.Tensor, weight: torch.Tensor, bias: torch.Tensor) -> torch.Tensor:
        # x: [B, D_in], weight: [D_in, D_out], bias: [D_out]
        ctx.save_for_backward(x, weight)
        return x.matmul(weight) + bias

    @staticmethod
    def backward(ctx, grad_output: torch.Tensor):
        # grad_output (dY): [B, D_out]
        x, weight = ctx.saved_tensors
        grad_x = grad_output.matmul(weight.t())          # dX = dY @ W^T
        grad_weight = x.t().matmul(grad_output)          # dW = X^T @ dY
        grad_bias = grad_output.sum(dim=0)               # db = sum(dY, axis=0)
        return grad_x, grad_weight, grad_bias
```

**Uygulama sınırı:** Görevler Python ile küçük, denetlenebilir hesaplar yapar. `python norun` blokları PyTorch/GPU tarafını incelemek içindir; bu tezgâhta otomatik çalıştırılıp gerçek training/serving kabulü yapılmaz.

**Birincil kaynak:** [PyTorch autograd](https://docs.pytorch.org/tutorials/beginner/blitz/autograd_tutorial.html). Kaynak, yöntemin ayrıntıları içindir; dersteki küçük örnek ölçülmüş üretim benchmarkı değildir.
:::

::: tahmin Gradient Accumulation ve Residual Dallanma Tuzağı
Aşağıdaki hesaplama grafiğinde $x = 3.0$ değişkeni hem karesel kolda ($u = x \cdot x$) hem de doğrusal kolda ($y = u + x$) kullanılıyor ve ardından `geri_yay()` fonksiyonu **iki kez üst üste** (`zero_grad` yapılmadan!) çağrılıyor. Kodu çalıştırdığında ekrana ne yazar?

```python
class Dugum:
    def __init__(self, val):
        self.val = val
        self.grad = 0.0

x = Dugum(3.0)
# Fonksiyon: y = x * x + x  -->  dy/dx = 2*x + 1 = 7.0
def geri_yay(dugum):
    dy_du = 1.0
    du_dx = 2.0 * dugum.val   # x * x kolundan gelen türev: 6.0
    dy_dx_dogrudan = 1.0      # + x kolundan gelen türev: 1.0
    dugum.grad += dy_du * du_dx + dy_dx_dogrudan

geri_yay(x)
birinci_adim = x.grad
geri_yay(x)
ikinci_adim = x.grad
print(f"1.Backward={birinci_adim} | 2.Backward(Sifirlamadan)={ikinci_adim}")
```

???

```cikti
1.Backward=7.0 | 2.Backward(Sifirlamadan)=14.0
```
İlk `geri_yay(x)` çağrısında $y = x^2 + x$ fonksiyonunun $x=3.0$ noktasındaki türevi iki koldan toplanarak $2(3.0) + 1.0 = 7.0$ olur. Ancak `x.grad = 0.0` (`zero_grad()`) yapılmadan ikinci kez `geri_yay(x)` çağrıldığında, `+=` operatörü yüzünden yeni gradyan eski gradyanın üzerine eklenir (**Gradient Accumulation**) ve sonuç `14.0` çıkar!
:::

::: gorev 1 · Skaler Hesaplama Grafiğinde Topological Sort ve Backward
`geriye_yayilim(dugumler, hedef_id)` işlevini yaz.

Bir **Directed Acyclic Graph (DAG)** içindeki düğümler `dugumler` listesiyle verilmektedir. Her düğüm şu alanları içeren bir sözlüktür:
- `"id"`: Düğümün benzersiz string kimliği (ör. `"x"`, `"w"`, `"u"`, `"L"`).
- `"op"`: İşlem türü:
  - `"leaf"`: Giriş/yaprak düğümü (`"inputs": []`, `"val": float`).
  - `"add"`: Toplama (`"inputs": [a_id, b_id]`, ileri değeri $a + b$).
  - `"mul"`: Çarpma (`"inputs": [a_id, b_id]`, ileri değeri $a \cdot b$).
  - `"relu"`: ReLU aktivasyonu (`"inputs": [a_id]`, ileri değeri $\max(0.0, a)$; yerel türevi $a > 0$ ise $1.0$, aksi halde $0.0$).

İşlevin yapması gerekenler:
1. Girdi listesini değiştirme (`in-place mutation` yapma).
2. `hedef_id` düğümünden ulaşılabilen alt grafikte **Topological Sort** sırasıyla önce tüm düğümlerin ileri (`forward`) değerlerini hesapla.
3. `hedef_id` düğümünün gradyanını `1.0` başlatıp ters topolojik sırada **Chain Rule** ve **Gradient Accumulation (`+=`)** uygulayarak her düğümün `hedef_id` çıktısına göre türevini hesapla.
4. Sonuç olarak `{dugum_id: round(grad, 6)}` biçiminde (`hedef_id`'den ulaşılabilen tüm düğümler için) bir sözlük döndür.

```starter
def geriye_yayilim(dugumler, hedef_id):
    # KUSURLU BAŞLANGIÇ KODU: Topolojik sıralama ve zincir kuralı uygulamadan 0.0 döndürüyor!
    return {d["id"]: 0.0 for d in dugumler}

ornek_graf = [
    {"id": "x", "op": "leaf", "inputs": [], "val": 2.0},
    {"id": "w", "op": "leaf", "inputs": [], "val": -3.0},
    {"id": "u", "op": "mul", "inputs": ["x", "w"]},
    {"id": "z", "op": "add", "inputs": ["u", "x"]},  # Residual bağlantı: x iki kez kullanılıyor!
    {"id": "L", "op": "relu", "inputs": ["z"]},
]
print("Gradyanlar:", geriye_yayilim(ornek_graf, "L"))
```

```test
import copy

def sozlesme(fn):
    try:
        # Test 1: Residual (Fan-out) bağlantı ve pozitif ReLU
        # u = x * w = 3.0 * 2.0 = 6.0
        # z = u + x = 6.0 + 3.0 = 9.0
        # L = relu(z) = 9.0
        # dL/dL = 1, dL/dz = 1, dL/du = 1, dL/dw = x = 3.0, dL/dx = w + 1 = 2.0 + 1.0 = 3.0
        g1 = [
            {"id": "L", "op": "relu", "inputs": ["z"]},
            {"id": "z", "op": "add", "inputs": ["u", "x"]},
            {"id": "x", "op": "leaf", "inputs": [], "val": 3.0},
            {"id": "u", "op": "mul", "inputs": ["x", "w"]},
            {"id": "w", "op": "leaf", "inputs": [], "val": 2.0},
        ]
        g1_kopya = copy.deepcopy(g1)
        r1 = fn(g1, "L")
        if g1 != g1_kopya or not isinstance(r1, dict):
            return False
        beklenen1 = {"x": 3.0, "w": 3.0, "u": 1.0, "z": 1.0, "L": 1.0}
        if r1 != beklenen1:
            return False

        # Test 2: ReLU negatif bölgede (Ölü nöron -> geriye 0.0 gradyan akmalı)
        g2 = [
            {"id": "x", "op": "leaf", "inputs": [], "val": 2.0},
            {"id": "w", "op": "leaf", "inputs": [], "val": -3.0},
            {"id": "u", "op": "mul", "inputs": ["x", "w"]},  # -6.0
            {"id": "L", "op": "relu", "inputs": ["u"]},      # 0.0
        ]
        r2 = fn(g2, "L")
        if r2 != {"x": 0.0, "w": 0.0, "u": 0.0, "L": 1.0}:
            return False

        # Test 3: Aynı değişkenin kendisiyle çarpımı (y = x * x -> dy/dx = 2*x)
        g3 = [
            {"id": "x", "op": "leaf", "inputs": [], "val": 4.5},
            {"id": "y", "op": "mul", "inputs": ["x", "x"]},
        ]
        if fn(g3, "y") != {"x": 9.0, "y": 1.0}:
            return False

        return True
    except Exception:
        return False

_graf_sifir = [
    {"id": "z", "op": "relu", "inputs": ["x"]},
    {"id": "x", "op": "leaf", "inputs": [], "val": 0.0},
    {"id": "ayri", "op": "leaf", "inputs": [], "val": 17.0},
]
eq(geriye_yayilim(_graf_sifir, "z"), {"z": 1.0, "x": 0.0},
   "ReLU türevi sıfırda sıfırdır ve hedefe bağlı olmayan düğüm dönmez")
eq(geriye_yayilim(_graf_sifir, "x"), {"x": 1.0},
   "Yaprak hedefin kendine göre türevi birdir")

# ReLU çıktısı sonraki çarpımın türevinde kullanılır.
for deger, beklenen in ((0.123456789, 0.246914), (-0.25, 0.0), (0.0, 0.0)):
    _paylasilan_relu = [
        {"id": "x", "op": "leaf", "inputs": [], "val": deger},
        {"id": "r", "op": "relu", "inputs": ["x"]},
        {"id": "y", "op": "mul", "inputs": ["r", "r"]},
    ]
    eq(geriye_yayilim(_paylasilan_relu, "y"),
       {"x": beklenen, "r": beklenen, "y": 1.0},
       "Paylaşılan ara düğüm bir kez işlenir ve ileri değeri türeve girer")
# ReLU'nun hatalı negatif çıktısı başka yaprağın türevine de yansır.
eq(geriye_yayilim([
    {"id": "x", "op": "leaf", "inputs": [], "val": -0.25},
    {"id": "w", "op": "leaf", "inputs": [], "val": 3.0},
    {"id": "r", "op": "relu", "inputs": ["x"]},
    {"id": "y", "op": "mul", "inputs": ["r", "w"]},
], "y"), {"x": 0.0, "w": 0.0, "r": 3.0, "y": 1.0},
   "Negatif ReLU ileri değeri sıfır olmalıdır")

ok(sozlesme(geriye_yayilim), "topolojik sıralama, ileri hesaplama ve zincir kuralı (fan-out dahil) doğru çalışmalı")

def m_atama(dugumler, hedef_id):
    # += yerine = kullanan hatalı mutant (fan-out'ta çuvallar)
    sonuc = geriye_yayilim(dugumler, hedef_id)
    if "x" in sonuc:
        sonuc["x"] = 1.0
    return sonuc

def m_relu_bozuk(dugumler, hedef_id):
    sonuc = geriye_yayilim(dugumler, hedef_id)
    for k in sonuc:
        if k != hedef_id and sonuc[k] == 0.0:
            sonuc[k] = 1.0
    return sonuc

for ad, mutant in [("gradyan biriktirmeyen (= kullanan)", m_atama), ("negatif ReLU türevini kesmeyen", m_relu_bozuk)]:
    ok(not sozlesme(mutant), "hatalı çözüm/mutant yakalanmalı: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def geriye_yayilim(dugumler, hedef_id):\n    harita = {d['id']: d for d in dugumler}\n    ziyaret = set()\n    topo = []\n\n    def dfs(nid):\n        if nid not in ziyaret:\n            ziyaret.add(nid)\n            for inp in harita[nid].get('inputs', []):\n                dfs(inp)\n            topo.append(nid)\n    dfs(hedef_id)\n    deger = {}\n    for nid in topo:\n        d = harita[nid]\n        op = d['op']\n        if op == 'leaf':\n            deger[nid] = float(d['val'])\n        elif op == 'add':\n            a, b = d['inputs']\n            deger[nid] = deger[a] + deger[b]\n        elif op == 'mul':\n            a, b = d['inputs']\n            deger[nid] = deger[a] * deger[b]\n        elif op == 'relu':\n            a = d['inputs'][0]\n            deger[nid] = deger[a] if deger[a] > 0.0 else 0.0\n    grad = {nid: 0.0 for nid in topo}\n    grad[hedef_id] = 1.0\n    for nid in reversed(topo):\n        d = harita[nid]\n        op = d['op']\n        g = grad[nid]\n        if op == 'add':\n            a, b = d['inputs']\n            grad[a] += g\n            grad[b] += g\n        elif op == 'mul':\n            a, b = d['inputs']\n            grad[a] += deger[b] * g\n            grad[b] += deger[a] * g\n        elif op == 'relu':\n            a = d['inputs'][0]\n            if deger[a] > 0.0:\n                grad[a] += g\n    return {nid: round(grad[nid], 6) for nid in topo}", 'referans', 'exec'), _REF)
_t, _g = _ff(geriye_yayilim, _REF['geriye_yayilim'], ([{'id': 'x', 'op': 'leaf', 'inputs': [], 'val': 2.0}, {'id': 'w', 'op': 'leaf', 'inputs': [], 'val': -3.0}, {'id': 'u', 'op': 'mul', 'inputs': ['x', 'w']}, {'id': 'z', 'op': 'add', 'inputs': ['u', 'x']}, {'id': 'L', 'op': 'relu', 'inputs': ['z']}], 'L'), tohum=2557, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (geriye_yayilim): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
def geriye_yayilim(dugumler, hedef_id):
    harita = {d["id"]: d for d in dugumler}
    ziyaret = set()
    topo = []

    def dfs(nid):
        if nid not in ziyaret:
            ziyaret.add(nid)
            for inp in harita[nid].get("inputs", []):
                dfs(inp)
            topo.append(nid)

    dfs(hedef_id)

    deger = {}
    for nid in topo:
        d = harita[nid]
        op = d["op"]
        if op == "leaf":
            deger[nid] = float(d["val"])
        elif op == "add":
            a, b = d["inputs"]
            deger[nid] = deger[a] + deger[b]
        elif op == "mul":
            a, b = d["inputs"]
            deger[nid] = deger[a] * deger[b]
        elif op == "relu":
            a = d["inputs"][0]
            deger[nid] = deger[a] if deger[a] > 0.0 else 0.0

    grad = {nid: 0.0 for nid in topo}
    grad[hedef_id] = 1.0

    for nid in reversed(topo):
        d = harita[nid]
        op = d["op"]
        g = grad[nid]
        if op == "add":
            a, b = d["inputs"]
            grad[a] += g
            grad[b] += g
        elif op == "mul":
            a, b = d["inputs"]
            grad[a] += deger[b] * g
            grad[b] += deger[a] * g
        elif op == "relu":
            a = d["inputs"][0]
            if deger[a] > 0.0:
                grad[a] += g

    return {nid: round(grad[nid], 6) for nid in topo}
```

```hint
Önce `hedef_id` düğümünden başlayarak DFS (post-order) ile topolojik listeyi (`topo`) çıkar. İleri geçişte `topo` sırasıyla her düğümün `deger[nid]` sonucunu hesapla. Geri geçişte `reversed(topo)` sırasıyla `grad[inp] += ...` biriktirmesi yap.
```
:::

::: gorev 2 · Matris Çarpımı (Linear Layer) İleri ve backpropagation Gradyanları
`linear_geri_yayilim(X, W, dY)` işlevini yaz.

Bir `Linear` katmanda ileri geçiş $Y = X \cdot W + b$ olarak tanımlıdır:
- `X`: Boyutu $B \times D_{\text{in}}$ olan iki boyutlu liste (`list[list[float]]`).
- `W`: Boyutu $D_{\text{in}} \times D_{\text{out}}$ olan iki boyutlu liste.
- `dY`: Üst katmandan gelen $\frac{\partial \mathcal{L}}{\partial Y}$ gradyan matrisi ($B \times D_{\text{out}}$).

İşlev, girdileri değiştirmeden (`in-place mutation` yapmadan) tüm elemanları `round(val, 6)` ile yuvarlanmış şu sözlüğü döndürmelidir:
- `"dX"`: $dY \cdot W^T$ matrisi ($B \times D_{\text{in}}$ boyutunda)
- `"dW"`: $X^T \cdot dY$ matrisi ($D_{\text{in}} \times D_{\text{out}}$ boyutunda)
- `"db"`: $dY$'nin satırları ($B$ ekseni) boyunca sütun toplamları ($D_{\text{out}}$ uzunluğunda tek boyutlu liste)

```starter
def linear_geri_yayilim(X, W, dY):
    # KUSURLU BAŞLANGIÇ KODU: Matris çarpımı ve transpoz kurallarını uygulamadan sıfır döndürüyor!
    B, D_in = len(X), len(X[0])
    D_out = len(W[0])
    return {
        "dX": [[0.0] * D_in for _ in range(B)],
        "dW": [[0.0] * D_out for _ in range(D_in)],
        "db": [0.0] * D_out,
    }

X_orn = [[1.0, 2.0], [3.0, 4.0]]
W_orn = [[0.5, -1.0], [1.5, 2.0]]
dY_orn = [[1.0, 0.0], [0.0, 2.0]]
print("Linear VJP:", linear_geri_yayilim(X_orn, W_orn, dY_orn))
```

```test
import copy

def sozlesme(fn):
    try:
        X = [[1.0, 2.0, -1.0], [0.5, -1.0, 2.0]]   # 2 x 3
        W = [[0.5, 1.0], [-0.5, 2.0], [1.5, -1.0]] # 3 x 2
        dY = [[2.0, -1.0], [1.0, 3.0]]             # 2 x 2
        x_k, w_k, dy_k = copy.deepcopy(X), copy.deepcopy(W), copy.deepcopy(dY)
        res = fn(X, W, dY)
        if X != x_k or W != w_k or dY != dy_k or not isinstance(res, dict):
            return False
        # dX = dY @ W^T (2x2 @ 2x3 -> 2x3)
        # Satır 0: [2*0.5 + (-1)*1.0, 2*(-0.5) + (-1)*2.0, 2*1.5 + (-1)*(-1.0)] = [0.0, -3.0, 4.0]
        # Satır 1: [1*0.5 + 3*1.0, 1*(-0.5) + 3*2.0, 1*1.5 + 3*(-1.0)] = [3.5, 5.5, -1.5]
        beklenen_dX = [[0.0, -3.0, 4.0], [3.5, 5.5, -1.5]]
        # dW = X^T @ dY (3x2 @ 2x2 -> 3x2)
        # Satır 0: [1*2 + 0.5*1, 1*(-1) + 0.5*3] = [2.5, 0.5]
        # Satır 1: [2*2 + (-1)*1, 2*(-1) + (-1)*3] = [3.0, -5.0]
        # Satır 2: [(-1)*2 + 2*1, (-1)*(-1) + 2*3] = [0.0, 7.0]
        beklenen_dW = [[2.5, 0.5], [3.0, -5.0], [0.0, 7.0]]
        # db = sum(dY, axis=0) = [2.0 + 1.0, -1.0 + 3.0] = [3.0, 2.0]
        beklenen_db = [3.0, 2.0]
        return res == {"dX": beklenen_dX, "dW": beklenen_dW, "db": beklenen_db}
    except Exception:
        return False

eq(linear_geri_yayilim([[0.1234567]], [[0.2345678, -0.3456789]], [[1.0, 0.0]]), {
    "dX": [[0.234568]],
    "dW": [[0.123457, 0.0]],
    "db": [1.0, 0.0],
}, "Tek örnek ve iki çıkış: dX ve dW altı basamağa yuvarlanır")
eq(linear_geri_yayilim([[2.0], [-3.0]], [[4.0]], [[0.1234567], [-0.0123456]]), {
    "dX": [[0.493827], [-0.049382]],
    "dW": [[0.28395]],
    "db": [0.111111],
}, "Tek çıkış: db iki örneği toplar ve altı basamağa yuvarlanır")

ok(sozlesme(linear_geri_yayilim), "dX = dY @ W^T, dW = X^T @ dY ve db = sum(dY, axis=0) doğru hesaplanmalı")

def m_db_bozuk(X, W, dY):
    r = linear_geri_yayilim(X, W, dY)
    r["db"] = [0.0 for _ in r["db"]]
    return r

def m_dw_bozuk(X, W, dY):
    r = linear_geri_yayilim(X, W, dY)
    r["dW"][0][0] += 1.0
    return r

for ad, mutant in [("bias gradyanını sıfırlayan", m_db_bozuk), ("ağırlık gradyanını bozan", m_dw_bozuk)]:
    ok(not sozlesme(mutant), "hatalı çözüm/mutant yakalanmalı: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def linear_geri_yayilim(X, W, dY):\n    B = len(X)\n    D_in = len(X[0])\n    D_out = len(W[0])\n    dX = [[round(sum((dY[b][o] * W[i][o] for o in range(D_out))), 6) for i in range(D_in)] for b in range(B)]\n    dW = [[round(sum((X[b][i] * dY[b][o] for b in range(B))), 6) for o in range(D_out)] for i in range(D_in)]\n    db = [round(sum((dY[b][o] for b in range(B))), 6) for o in range(D_out)]\n    return {'dX': dX, 'dW': dW, 'db': db}", 'referans', 'exec'), _REF)
_t, _g = _ff(linear_geri_yayilim, _REF['linear_geri_yayilim'], ([[1.0, 2.0], [3.0, 4.0]], [[0.5, -1.0], [1.5, 2.0]], [[1.0, 0.0], [0.0, 2.0]]), tohum=3065, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (linear_geri_yayilim): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
def linear_geri_yayilim(X, W, dY):
    B = len(X)
    D_in = len(X[0])
    D_out = len(W[0])

    # dX = dY @ W^T  (B x D_out) @ (D_out x D_in) -> (B x D_in)
    dX = [
        [round(sum(dY[b][o] * W[i][o] for o in range(D_out)), 6) for i in range(D_in)]
        for b in range(B)
    ]

    # dW = X^T @ dY  (D_in x B) @ (B x D_out) -> (D_in x D_out)
    dW = [
        [round(sum(X[b][i] * dY[b][o] for b in range(B)), 6) for o in range(D_out)]
        for i in range(D_in)
    ]

    # db = sum(dY, axis=0) -> (D_out,)
    db = [round(sum(dY[b][o] for b in range(B)), 6) for o in range(D_out)]

    return {"dX": dX, "dW": dW, "db": db}
```

```hint
`dX[b][i]` için `o` indeksleri üzerinden `dY[b][o] * W[i][o]` toplamını al. `dW[i][o]` için `b` (batch) indeksleri üzerinden `X[b][i] * dY[b][o]` toplamını al. `db[o]` için `b` üzerinden `dY[b][o]` değerlerini topla.
```
:::

::: anlat Gerçek deney: Gerçek SmolLM2 değerleriyle autograd karşılaştırması ve gradyan sızıntısı
Final, yerel önbellekteki gerçek **SmolLM2-135M** modelini kullanır (indirme yok). Senin iki işlevin modelin **kendi sayılarıyla** beslenir ve sonuç `torch.autograd` ile karşılaştırılır:

- **Skaler graf:** 2. katmandaki gerçek bir gizli durumun ilk 6 değeri ve `gate_proj`'un gerçek bir nöronunun 6 ağırlığıyla $L = \text{relu}(\sum_i x_i w_i + b + x_0)$ grafı kurulur. $x_0$ iki kez kullanılır (fan-out): doğru backward iki yoldan gelen gradyanı **toplar**. Beklenen değer aynı grafın torch'taki `backward()` sonucudur.
- **Linear katman:** gerçek gizli durumlardan 3×16'lık `X`, gerçek `q_proj` ağırlığından 16×8'lik `W` ve gerçek bir kaybın ($\lVert Y - T \rVert^2$) çıktı gradyanı `dY`. Senin `dX`, `dW`, `db` değerlerin autograd'ın verdiğiyle karşılaştırılır.

**Güvenlik yüzü: gradyan sızıntısı.** Federe öğrenmede istemci ham veriyi değil gradyanı gönderir; bu gizlilik sağlıyormuş gibi görünür. Tek örnekli bir batch'te bias'lı doğrusal katman için $\partial L / \partial W_{:,o} = x \cdot \partial L / \partial b_o$ olduğundan girdi **birebir** geri çıkar: $x = dW_{:,o} / db_o$. Deney gizli bir tokenın (`" password"`) gerçek gömmesini senin `linear_geri_yayilim` çıktından geri hesaplar ve modelin 49 152 tokenlık sözlüğünde en yakın tokenı arar.

Kabul: iki işlevin farksal taramayı geçmesi; skaler graf gradyanlarının autograd'dan en çok `1e-5`, linear katmanın göreli `1e-5` farklı olması; sızıntıda geri çıkan tokenın gizli tokenla aynı ve hatanın `1e-4` altında olması.

**Kanıt dosyasını oku:** `graf_en_buyuk_fark`, `x0_fanout_grad`, `linear_goreli_fark`, `geri_cikan_token`, `sizinti_en_buyuk_hata`. Soru 1: `x0_fanout_grad` neden `w0`'dan tam 1 fazla? Soru 2: Sızıntı hatası neden 1e-7 mertebesinde de sıfır değil? Soru 3: Batch 32 olsaydı aynı bölme neyi verirdi ve saldırgan ne yapmak zorunda kalırdı?
:::

::: gorev Gerçek deney · Gerçek SmolLM2 değerleriyle autograd karşılaştırması ve gradyandan girdi geri çıkarma
Önceki görevlerdeki `geriye_yayilim`, `linear_geri_yayilim` işlevlerini buraya birleştir (çözümlerini kopyalayabilirsin). Çalıştır gerçek ölçüm tablosunu gösterir; Kontrol Et önce işlevlerini gizli verilerle ve farksal taramayla sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
timeout: 180
```
```starter
import ai_lab
def geriye_yayilim(dugumler, hedef_id):
    return {d['id']: 0.0 for d in dugumler}

def linear_geri_yayilim(X, W, dY):
    B, D_in = (len(X), len(X[0]))
    D_out = len(W[0])
    return {'dX': [[0.0] * D_in for _ in range(B)], 'dW': [[0.0] * D_out for _ in range(D_in)], 'db': [0.0] * D_out}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_01 as D
    D.goster(geriye_yayilim, linear_geri_yayilim)
```
```test
import ai_lab
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('_ref_graf_ve_grad', 'kanit_yaz'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
geriye_yayilim = need("geriye_yayilim")
linear_geri_yayilim = need("linear_geri_yayilim")
# farksal tarama (görev çözümlerinden derlenen referans)
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def geriye_yayilim(dugumler, hedef_id):\n    harita = {d['id']: d for d in dugumler}\n    ziyaret = set()\n    topo = []\n\n    def dfs(nid):\n        if nid not in ziyaret:\n            ziyaret.add(nid)\n            for inp in harita[nid].get('inputs', []):\n                dfs(inp)\n            topo.append(nid)\n    dfs(hedef_id)\n    deger = {}\n    for nid in topo:\n        d = harita[nid]\n        op = d['op']\n        if op == 'leaf':\n            deger[nid] = float(d['val'])\n        elif op == 'add':\n            a, b = d['inputs']\n            deger[nid] = deger[a] + deger[b]\n        elif op == 'mul':\n            a, b = d['inputs']\n            deger[nid] = deger[a] * deger[b]\n        elif op == 'relu':\n            a = d['inputs'][0]\n            deger[nid] = deger[a] if deger[a] > 0.0 else 0.0\n    grad = {nid: 0.0 for nid in topo}\n    grad[hedef_id] = 1.0\n    for nid in reversed(topo):\n        d = harita[nid]\n        op = d['op']\n        g = grad[nid]\n        if op == 'add':\n            a, b = d['inputs']\n            grad[a] += g\n            grad[b] += g\n        elif op == 'mul':\n            a, b = d['inputs']\n            grad[a] += deger[b] * g\n            grad[b] += deger[a] * g\n        elif op == 'relu':\n            a = d['inputs'][0]\n            if deger[a] > 0.0:\n                grad[a] += g\n    return {nid: round(grad[nid], 6) for nid in topo}\n\ndef linear_geri_yayilim(X, W, dY):\n    B = len(X)\n    D_in = len(X[0])\n    D_out = len(W[0])\n    dX = [[round(sum((dY[b][o] * W[i][o] for o in range(D_out))), 6) for i in range(D_in)] for b in range(B)]\n    dW = [[round(sum((X[b][i] * dY[b][o] for b in range(B))), 6) for o in range(D_out)] for i in range(D_in)]\n    db = [round(sum((dY[b][o] for b in range(B))), 6) for o in range(D_out)]\n    return {'dX': dX, 'dW': dW, 'db': db}", 'referans', 'exec'), _REF)
_t, _g = _ff(geriye_yayilim, _REF['geriye_yayilim'], ([{'id': 'x', 'op': 'leaf', 'inputs': [], 'val': 2.0}, {'id': 'w', 'op': 'leaf', 'inputs': [], 'val': -3.0}, {'id': 'u', 'op': 'mul', 'inputs': ['x', 'w']}, {'id': 'z', 'op': 'add', 'inputs': ['u', 'x']}, {'id': 'L', 'op': 'relu', 'inputs': ['z']}], 'L'), tohum=2557, en_cok=600, mod='gecerli', butce='oto')
kontrol(_t, "farksal tarama (geriye_yayilim): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(linear_geri_yayilim, _REF['linear_geri_yayilim'], ([[1.0, 2.0], [3.0, 4.0]], [[0.5, -1.0], [1.5, 2.0]], [[1.0, 0.0], [0.0, 2.0]]), tohum=3065, en_cok=600, mod='gecerli', butce='oto')
kontrol(_t, "farksal tarama (linear_geri_yayilim): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_g0 = [{"id": "z", "op": "relu", "inputs": ["x"]}, {"id": "x", "op": "leaf", "inputs": [], "val": 0.0}, {"id": "ayri", "op": "leaf", "inputs": [], "val": 17.0}]
kontrol(geriye_yayilim(_g0, "z") == {"z": 1.0, "x": 0.0} and geriye_yayilim(_g0, "x") == {"x": 1.0}, "ReLU sıfır noktası ve izole düğüm sözleşmesi")
for _v, _b in ((0.123456789, 0.246914), (-0.25, 0.0), (0.0, 0.0)):
    kontrol(geriye_yayilim([{"id": "x", "op": "leaf", "inputs": [], "val": _v}, {"id": "r", "op": "relu", "inputs": ["x"]}, {"id": "y", "op": "mul", "inputs": ["r", "r"]}], "y") == {"x": _b, "r": _b, "y": 1.0}, "paylaşılan ReLU ileri/geri ve 6 basamak yuvarlama: " + str(_v))
kontrol(geriye_yayilim([{"id": "x", "op": "leaf", "inputs": [], "val": -0.25}, {"id": "w", "op": "leaf", "inputs": [], "val": 3.0}, {"id": "r", "op": "relu", "inputs": ["x"]}, {"id": "y", "op": "mul", "inputs": ["r", "w"]}], "y") == {"x": 0.0, "w": 0.0, "r": 3.0, "y": 1.0}, "negatif ReLU ileri değeri sıfır olmalı")
kontrol(linear_geri_yayilim([[0.1234567]], [[0.2345678, -0.3456789]], [[1.0, 0.0]]) == {"dX": [[0.234568]], "dW": [[0.123457, 0.0]], "db": [1.0, 0.0]}, "dikdörtgen matris ve dX/dW 6 basamak yuvarlama")
kontrol(linear_geri_yayilim([[2.0], [-3.0]], [[4.0]], [[0.1234567], [-0.0123456]]) == {"dX": [[0.493827], [-0.049382]], "dW": [[0.28395]], "db": [0.111111]}, "çok örnekli db toplama ve 6 basamak yuvarlama")
if not all(checks): stop()
from sandbox import ai_gercek_ai_uretim_01 as D
try: r = D.deney(geriye_yayilim, linear_geri_yayilim)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r['graf_ayni'], 'skaler graf gradyanları torch.autograd ile aynı (fan-out dahil, fark < 1e-5)')
kontrol(r['linear_ayni'], 'linear katman dX/dW/db gerçek değerlerde autograd ile aynı (göreli fark < 1e-5)')
kontrol(r['sizinti_token_ayni'] and r['sizinti_hassas'], 'tek örnekli gradyandan gizli tokenın gömmesi birebir geri çıkarıldı')
ai_lab.kanit_yaz("ai-uretim-01-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-uretim-01", "deney": r})
```
```solution
import ai_lab
def geriye_yayilim(dugumler, hedef_id):
    harita = {d['id']: d for d in dugumler}
    ziyaret = set()
    topo = []

    def dfs(nid):
        if nid not in ziyaret:
            ziyaret.add(nid)
            for inp in harita[nid].get('inputs', []):
                dfs(inp)
            topo.append(nid)
    dfs(hedef_id)
    deger = {}
    for nid in topo:
        d = harita[nid]
        op = d['op']
        if op == 'leaf':
            deger[nid] = float(d['val'])
        elif op == 'add':
            a, b = d['inputs']
            deger[nid] = deger[a] + deger[b]
        elif op == 'mul':
            a, b = d['inputs']
            deger[nid] = deger[a] * deger[b]
        elif op == 'relu':
            a = d['inputs'][0]
            deger[nid] = deger[a] if deger[a] > 0.0 else 0.0
    grad = {nid: 0.0 for nid in topo}
    grad[hedef_id] = 1.0
    for nid in reversed(topo):
        d = harita[nid]
        op = d['op']
        g = grad[nid]
        if op == 'add':
            a, b = d['inputs']
            grad[a] += g
            grad[b] += g
        elif op == 'mul':
            a, b = d['inputs']
            grad[a] += deger[b] * g
            grad[b] += deger[a] * g
        elif op == 'relu':
            a = d['inputs'][0]
            if deger[a] > 0.0:
                grad[a] += g
    return {nid: round(grad[nid], 6) for nid in topo}

def linear_geri_yayilim(X, W, dY):
    B = len(X)
    D_in = len(X[0])
    D_out = len(W[0])
    dX = [[round(sum((dY[b][o] * W[i][o] for o in range(D_out))), 6) for i in range(D_in)] for b in range(B)]
    dW = [[round(sum((X[b][i] * dY[b][o] for b in range(B))), 6) for o in range(D_out)] for i in range(D_in)]
    db = [round(sum((dY[b][o] for b in range(B))), 6) for o in range(D_out)]
    return {'dX': dX, 'dW': dW, 'db': db}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_01 as D
    D.goster(geriye_yayilim, linear_geri_yayilim)
```
```hint
Görev 1 ve görev 2 çözümlerini olduğu gibi buraya koy. Deney işlevlerini gerçek değerlerle çağırır; işlevler doğruysa ek bir şey yapman gerekmez.
```
:::

::: anlat Sınır
Görevler skaler hesaplama grafiğinde topolojik sıralı backward'ı ve linear katmanın ileri/geri gradyanlarını saf Python ile yazdırır; final adım sonuçları gerçek SmolLM2 değerlerinde torch.autograd ile karşılaştırır ve tek örnekli gradyandan girdinin geri çıkarılabildiğini gösterir. Skaler graf her işlem için bir düğüm tutar; gerçek çerçeveler tensör düzeyinde çalışır, ara değerleri bellek için serbest bırakır ve in-place işlemleri izler. `backward`'ı ikinci kez çağırmadan önce gradyanı sıfırlamamak, tahminde görüldüğü gibi gradyanı biriktirip ikiye katlar; fan-out'ta ise biriktirme doğru davranıştır. Kontrol akışı ve ikinci türev (create_graph) burada desteklenmez. Gradyan hatalarını yakalamanın standart yolu sayısal türevle (finite differences) karşılaştırmaktır.

Kaynaklar: [Baydin vd. 2018 - Automatic differentiation in machine learning: a survey](https://arxiv.org/abs/1502.05767), [Karpathy - micrograd](https://github.com/karpathy/micrograd).
:::

::: dusun
Sahnede bir sistem mühendisi sana şunu sordu:
*"Hocam, 70 Milyar parametreli bir modeli eğitirken neden ağırlıkların kendisi GPU'da `140 GB` yer kapladığı halde, eğitim (`Forward + Backward`) başladığında `VRAM` kullanımı bir anda `800 GB`'a fırlıyor ve `Out-Of-Memory (OOM)` alıyoruz?"*

Az önce yazdığın `linear_geri_yayilim(X, W, dY)` ve `ctx.save_for_backward(x, weight)` mekanizmasına bakarak bu soruyu yanıtla: $dW = X^T \cdot dY$ gradyanını hesaplayabilmek için her katmandaki ara aktivasyon matrisi $X$'in **Forward Pass**'ten **Backward Pass**'e kadar GPU belleğinde tutulması zorunluluğunu (**Activation Memory Bottleneck**) ve bunu çözmek için **Activation Checkpointing (`Gradient Checkpointing`)** tekniğinin bellek ile işlem gücü arasında nasıl bir takas yaptığını açıkla.
:::

::: ozet
- **Reverse-Mode Automatic Differentiation (`Autograd`)**, ileri geçişte dinamik bir **Computational Graph (DAG)** kurar ve geri geçişte tek bir skaler kayıptan ($O(1)$ çarpan maliyetiyle) milyarlarca parametrenin tam türevini hesaplar.
- Bir düğüm birden fazla alt işleme girdi olduğunda (**Fan-Out / Residual Connection**), **Multivariable Chain Rule** gereği tüm kollardan gelen gradyanlar `+=` ile biriktirilir (**Gradient Accumulation**) ve bu işlem mutlaka **Topological Sort** ters sırasıyla yürütülür.
- Matris seviyesinde (`Y = X @ W + b`), üst katmandan gelen $dY$ gradyanı ile **Vector-Jacobian Product (VJP)** kuralları işletilerek $dX = dY \cdot W^T$, $dW = X^T \cdot dY$ ve $db = \sum_B dY$ hesaplanır.
- $dW = X^T \cdot dY$ denklemi ileri geçişteki $X$ aktivasyonlarına ihtiyaç duyduğu için, derin ağlarda en büyük GPU bellek (`HBM`) tüketimi ağırlıklardan değil, backpropagation için saklanan ara aktivasyonlardan (`ctx.save_for_backward`) kaynaklanır.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **İleri grafik, ters zincir (25 sn).** "Sayısal türev $N$ parametre için $N+1$ ileri geçiş ister; `reverse-mode autograd` ise dinamik hesap çizgesini ters topolojik sırayla yürüyerek tek bir skaler kayıptan bütün parametre türevlerini tek geri geçişte üretir."
2. **Dallanma ve `+=` birikimi (30 sn).** "Artık bağlantıda bir düğüm iki kola giderse, çok değişkenli zincir kuralı gereği iki koldan gelen gradyanlar üzerine yazılmaz (`=`), toplanır (`+=`); aksi hâlde ana yolun türevi silinir."
3. **VJP ve aktivasyon belleği (35 sn).** "Doğrusal katmanda $dW = X^T dY$ ileri geçişteki $X$ tensörünü saklamayı zorunlu kılar; bu yüzden büyük modellerde GPU belleğini ağırlıklardan önce ara aktivasyonlar doldurur."
4. **Güvenlik bağlantısı (30 sn).** "Ağırlık gradyanı doğrudan katman girdisi $X$'i taşıdığı için, paylaşılan tek örnekli gradyandan gizli girdi geri çözülebilir; hız optimizasyonu olan ara aktivasyon ve gradyanlar aynı zamanda gizlilik yüzeyidir."
:::
