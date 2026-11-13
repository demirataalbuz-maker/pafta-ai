---
id: ai-uretim-13
title: "Tensör Bellek Düzeni: Strides, Contiguous Memory, Broadcasting ve Einops Motoru"
track: ai-uretim
order: 13
duration_minutes: 35
difficulty: orta
xp: 280
prerequisites: [ai-uretim-12]
tags: [tensor, strides, contiguous-memory, zero-copy-view, broadcasting, einops]
summary: "C-contiguous bellek adım kaymalarını (strides), sıfır kopyalı transpose görünümlerini, zero-stride broadcasting kurallarını ve einops rearrange planlayıcısını SmolLM2 tensörlerinde doğrula."
esleme: ai-uretim-12, ai-uretim-14
---

::: anlat
## Tensor shape, stride ve broadcasting

Bir tensorun shape bilgisi ile verinin bellekteki yerleşimi aynı şey değildir. Stride hesabıyla bir indeksin ofsetini bulacak, transpose işleminin kopya üretmeden neleri değiştirebildiğini görecek ve broadcasting için boyut uyumluluğunu denetleyeceksin.

Fiziksel bellek yalnızca $0, 1, 2, \dots, N-1$ adreslerinden oluşan **tek boyutlu düz bir şerittir (`1D Flat Contiguous Storage`)**. Peki PyTorch veya NumPy, tek boyutlu düz bir bellek bloğunu nasıl olur da tensor verisini kopyalamadan (`Zero-Copy`) 3 boyutlu, 4 boyutlu veya devrik (`Transposed`) bir tensör gibi gösterebilir?

Cevap, bir `torch.Tensor` nesnesinin kaputun altında iki parçadan oluşmasıdır:
1. **`Storage` (`data_ptr`):** Fiziksel bellekteki ham sayıların tutulduğu tek boyutlu düz tampon (`1D Buffer`).
2. **`Metadata Header` (`shape`, `strides`, `storage_offset`, `dtype`):** Çok boyutlu indeksleri $(i_0, i_1, \dots, i_{k-1})$ tek boyutlu fiziksel bellek adresine çeviren matematiksel harita!

---

### 1. `Shape` ve `Strides` Matematiği: Çok Boyutlu İndeksten Fiziksel Adrese

Elinde şekli $\text{shape} = (d_0, d_1, \dots, d_{k-1})$ ve adım kaymaları $\text{strides} = (s_0, s_1, \dots, s_{k-1})$ olan bir tensör olsun. Sen `T[i_0, i_1, ..., i_{k-1}]` elemanını okumak istediğinde PyTorch arka planda tek bir doğrusal çarpım-toplam yapar:

$$\text{PhysicalIndex}(i_0, \dots, i_{k-1}) = \text{storage\_offset} + \sum_{m=0}^{k-1} i_m \cdot s_m$$

- **`Row-Major` (`C-Contiguous` — PyTorch/NumPy Varsayılanı):** Bellekte en son eksen (`axis = -1`) yan yana dizilir. Bir $(d_0, d_1, d_2)$ tensörünün standart bitişik (`Contiguous`) adım kaymaları sağdan sola boyutların kümülatif çarpımıdır:
  $$s_2 = 1, \qquad s_1 = d_2, \qquad s_0 = d_1 \cdot d_2$$

```
     MANTIKSAL 2x3 MATRİS: shape=(2, 3), strides=(3, 1)
           Sütun 0   Sütun 1   Sütun 2
  Satır 0 [  10        20        30   ]   --> Satırda 1 ilerlemek için bellekte +3 atla (stride_0 = 3)
  Satır 1 [  40        50        60   ]   --> Sütunda 1 ilerlemek için bellekte +1 atla (stride_1 = 1)

     FİZİKSEL 1D DÜZ BELLEK (Flat Storage):
     Adres:   0    1    2    3    4    5
     Değer: [10,  20,  30,  40,  50,  60]
     Örnek: T[1, 2] -> offset = 1*3 + 2*1 = 5 -> Storage[5] = 60!
```

---

### 2. `Zero-Copy Transpose` ve Neden `.view()` Patlayınca `.contiguous()` Çağrılır?

Şimdi yukarıdaki $(2, 3)$ matrisin devriğini (`x.transpose(0, 1)`) aldığımızda PyTorch bellekteki 60 milyar parametreyi kopyalar mı? **Hayır (`Zero-Copy View`)!**
- Yalnızca `shape` bilgisini `(2, 3) -> (3, 2)` ve `strides` bilgisini `(3, 1) -> (1, 3)` olarak yer değiştirir (tensor verisi kopyalanmaz; yeni görünüm için metadata belleği gerekir).
- **Ancak bir bedeli vardır (`Non-Contiguous Memory`):** Artık matrisi satır satır okuduğunda fiziksel bellekte elemanlar `0, 1, 2, 3...` diye ardışık gitmez; `0, 3, 1, 4, 2, 5` diye zıplayarak gider!
- Bu duruma **`Non-Contiguous Tensor`** denir. Böyle bir tensörün üzerinde `.view(-1)` çağırmaya kalkarsan PyTorch `RuntimeError: view size is not compatible with input tensor's size and stride` hatası fırlatır; çünkü zıplayan adresleri tek bir sabit `stride` ile düzleştirmek matematiksel olarak imkansızdır! İşte `.contiguous()` çağrısı bu noktada fiziksel bellekte yeni ve ardışık bir kopya oluşturarak düzeni sıfırlar.

Şimdi saf Python ile sıfır kopyalı (`Zero-Copy`) `transpose`, `slice` ve `contiguous` kontrolünü çalıştıran bir `StridedTensorView` motoru yazalım:

```python
class StridedTensorView:
    def __init__(self, storage, shape, strides=None, offset=0):
        self.storage = storage
        self.shape = tuple(shape)
        self.offset = offset
        if strides is None:
            # Sağdan sola C-Contiguous stride hesabı
            st = [1] * len(shape)
            for i in range(len(shape) - 2, -1, -1):
                st[i] = st[i + 1] * shape[i + 1]
            self.strides = tuple(st)
        else:
            self.strides = tuple(strides)

    def get(self, *indices):
        fiziksel_indis = self.offset + sum(i * s for i, s in zip(indices, self.strides))
        return self.storage[fiziksel_indis]

    def transpose(self, dim0, dim1):
        yeni_shape = list(self.shape)
        yeni_strides = list(self.strides)
        yeni_shape[dim0], yeni_shape[dim1] = yeni_shape[dim1], yeni_shape[dim0]
        yeni_strides[dim0], yeni_strides[dim1] = yeni_strides[dim1], yeni_strides[dim0]
        return StridedTensorView(self.storage, yeni_shape, yeni_strides, self.offset)

    def is_contiguous(self):
        beklenen = 1
        for d, s in zip(reversed(self.shape), reversed(self.strides)):
            if d > 1:
                if s != beklenen:
                    return False
                beklenen *= d
        return True

ham_bellek = [10, 20, 30, 40, 50, 60]
t = StridedTensorView(ham_bellek, shape=(2, 3))
t_devrik = t.transpose(0, 1)
print(f"Orijinal: shape={t.shape}, strides={t.strides}, contiguous={t.is_contiguous()}, T[1,2]={t.get(1, 2)}")
print(f"Devrik  : shape={t_devrik.shape}, strides={t_devrik.strides}, contiguous={t_devrik.is_contiguous()}, T^T[2,1]={t_devrik.get(2, 1)}")
```

---

### 3. `Broadcasting Rules` (Sanal Stride `0` Hilesi) ve `Einops` Felsefeli Kodlama

Farklı şekillerdeki iki tensörü topladığında (örneğin `X` şekli `(32, 1024, 512)` ve `bias` şekli `(512,)`) PyTorch `bias` vektörünü $32 \times 1024$ kez bellekte çoğaltır mı? **Asla!**
#### 📏 `Broadcasting` Kuralları ve `stride = 0` Sihri:
1. İki tensörün şekilleri **sağdan sola (en son eksenden başa doğru)** hizalanır; kısa olanın soluna `1` boyutları eklenir: `(512,) -> (1, 1, 512)`.
2. Her eksende boyutlar ya **birbirine eşit olmalı** ya da **birinden biri `1` olmalıdır** (aksi halde `BroadcastError`).
3. Boyutu `1` olan eksen $D$ boyutuna genişletilirken fiziksel bellekte veri kopyalanmaz; yalnızca o eksenin adım kayması **`stride = 0`** yapılır!
   $$\text{offset} = i_0 \cdot 0 + i_1 \cdot 0 + i_2 \cdot 1 = i_2$$
   Böylece döngü $i_0$ ve $i_1$ üzerinde ilerlerken çarpım $0$ olduğu için GPU her seferinde aynı fiziksel `bias[i_2]` adresini okur!

#### 🧩 `Einops` & `Einsum`: Okunaksız `.view().transpose().permute()` Zincirlerine Son!
Çok başlı dikkat (**Multi-Head Attention**) yazarken klasik `x.view(B, S, H, D).transpose(1, 2)` kodu hataya çok açıktır. **Alex Rogozhnikov'un `einops`** standardı, eksenleri cebirsel isimleriyle yeniden şekillendirir:

```python norun
import torch
from einops import rearrange, einsum

# Gerçek Üretim Kodu: GQA Attention içinde Stride-Farkındalıklı Einops Kullanımı
B, S, H_q, H_kv, D = 4, 2048, 32, 8, 128
q_proj = torch.randn(B, S, H_q * D, device="cuda", dtype=torch.bfloat16)
k_proj = torch.randn(B, S, H_kv * D, device="cuda", dtype=torch.bfloat16)

# 1. Tek satırda hem başları ayır hem de grup boyutunu (g = H_q // H_kv = 4) açıkça kur:
q = rearrange(q_proj, "b s (h_kv g d) -> b h_kv g s d", h_kv=H_kv, d=D)
k = rearrange(k_proj, "b s (h_kv d) -> b h_kv s d", h_kv=H_kv)

# 2. Einsum ile GQA dikkat skorlarını (grup yayınlamasıyla) tek adımda hesapla:
scores = einsum(q, k, "b h_kv g s_q d, b h_kv s_k d -> b h_kv g s_q s_k") / (D ** 0.5)
```

**Uygulama sınırı:** Görevler Python ile küçük, denetlenebilir hesaplar yapar. `python norun` blokları PyTorch/GPU tarafını incelemek içindir; bu tezgâhta otomatik çalıştırılıp gerçek training/serving kabulü yapılmaz.

**Birincil kaynak:** [PyTorch tensor views](https://docs.pytorch.org/docs/stable/tensor_view.html). Kaynak, yöntemin ayrıntıları içindir; dersteki küçük örnek ölçülmüş üretim benchmarkı değildir.
:::

::: tahmin Zero-Copy Transpose Sonrası Fiziksel Bellek Ofseti ve Contiguous Durumu
Şekli `shape = (2, 3, 4)` olan C-Contiguous bir tensörün başlangıç adım kaymaları `strides = (12, 4, 1)`'dir. Bu tensörün `0.` ve `2.` eksenleri `transpose(0, 2)` ile yer değiştirildiğinde yeni şekil `(4, 3, 2)` olur. Bu devrik tensörde `(3, 1, 1)` indeksli elemanın tek boyutlu düz bellekteki fiziksel ofseti (`offset`) ve tensörün `contiguous` olup olmadığı nedir?

```python
eski_strides = (12, 4, 1)
yeni_strides = (eski_strides[2], eski_strides[1], eski_strides[0])  # (1, 4, 12)
indis = (3, 1, 1)
ofset = sum(i * s for i, s in zip(indis, yeni_strides))
contiguous_mu = (yeni_strides == (6, 2, 1))
print(f"YeniStrides={yeni_strides} | Ofset={ofset} | Contiguous={contiguous_mu}")
```

???

```cikti
YeniStrides=(1, 4, 12) | Ofset=19 | Contiguous=False
```
`transpose(0, 2)` işlemi fiziksel belleğe dokunmadan yalnızca `strides` demetinin 0. ve 2. elemanlarını değiştirerek `(1, 4, 12)` yapar. `(3, 1, 1)` indeksinin fiziksel ofseti $3 \times 1 + 1 \times 4 + 1 \times 12 = 19$ olur. Yeni şekil `(4, 3, 2)` için bitişik (`contiguous`) adımların `(6, 2, 1)` olması gerektiğinden `Contiguous=False` döner.
:::

::: gorev 1 · Çok Boyutlu İndeksten Bellek Ofseti (Stride Offset) ve Zero-Copy Transpose
`stride_ofset_ve_devrik(boyutlar, indeksler, eksen_a, eksen_b)` işlevini yaz.

Parametreler:
- `boyutlar`: Tensörün başlangıç C-Contiguous `shape` dizisi (`list[int]`, ör. `[2, 3, 4]`).
- `indeksler`: Orijinal tensörde erişilmek istenen çok boyutlu indeks (`list[int]`, ör. `[1, 2, 3]`).
- `eksen_a`, `eksen_b`: `transpose(eksen_a, eksen_b)` ile yer değiştirilecek iki eksen indisi (`int`).

İşlevin yapması gerekenler:
1. Girdi listelerini değiştirme. `boyutlar` için standart `Row-Major (C-Contiguous)` adım kaymalarını (`orijinal_strides`) sağdan sola hesapla ($s_{k-1} = 1$, $s_i = s_{i+1} \cdot d_{i+1}$).
2. `indeksler` konumunun düz bellekteki fiziksel ofsetini ($\sum i_m \cdot s_m$) hesapla (`orijinal_ofset`).
3. `eksen_a` ve `eksen_b` eksenlerini yer değiştirerek `devrik_boyutlar` ve `devrik_strides` listelerini oluştur.
4. Devrik tensörün hala `C-Contiguous` olup olmadığını denetle (`devrik_contiguous_mu`: boyutu `1`'den büyük olan tüm eksenlerde adım kayması sağdan sola kümülatif çarpıma eşitse `True`, değilse `False`).
5. Sonuç olarak şu sözlüğü döndür:
   - `"orijinal_strides"`: `list[int]`
   - `"orijinal_ofset"`: `int`
   - `"devrik_boyutlar"`: `list[int]`
   - `"devrik_strides"`: `list[int]`
   - `"devrik_contiguous_mu"`: `bool`

```starter
def stride_ofset_ve_devrik(boyutlar, indeksler, eksen_a, eksen_b):
    # KUSURLU BAŞLANGIÇ KODU: Stride adımlarını ve ofseti hesaplamadan sıfır döndürüyor!
    n = len(boyutlar)
    return {
        "orijinal_strides": [1] * n,
        "orijinal_ofset": 0,
        "devrik_boyutlar": list(boyutlar),
        "devrik_strides": [1] * n,
        "devrik_contiguous_mu": True,
    }

print("Stride Analizi:", stride_ofset_ve_devrik([2, 3, 4], [1, 2, 3], 0, 2))
```

```test
import copy

def sozlesme(fn):
    try:
        b = [2, 3, 4]
        idx = [1, 2, 3]
        bk, ik = copy.deepcopy(b), copy.deepcopy(idx)
        r = fn(b, idx, 0, 2)
        if b != bk or idx != ik or not isinstance(r, dict):
            return False
        # strides = [12, 4, 1], ofset = 1*12 + 2*4 + 3*1 = 23
        if r.get("orijinal_strides") != [12, 4, 1] or r.get("orijinal_ofset") != 23:
            return False
        if r.get("devrik_boyutlar") != [4, 3, 2] or r.get("devrik_strides") != [1, 4, 12]:
            return False
        if r.get("devrik_contiguous_mu") is not False:
            return False

        # Kendi ekseniyle transpose (eksen_a == eksen_b) veya boyutu 1 olan eksenle transpose -> Contiguous kalmalı!
        r2 = fn([1, 5, 4], [0, 3, 2], 0, 1)
        # orijinal_strides = [20, 4, 1], devrik_boyutlar = [5, 1, 4], devrik_strides = [4, 20, 1]
        # Boyutu > 1 olan eksenler: dim 0 (boyut 5, stride 4) ve dim 2 (boyut 4, stride 1) -> Contiguous!
        if r2.get("orijinal_strides") != [20, 4, 1] or r2.get("orijinal_ofset") != 14:
            return False
        if r2.get("devrik_boyutlar") != [5, 1, 4] or r2.get("devrik_strides") != [4, 20, 1]:
            return False
        if r2.get("devrik_contiguous_mu") is not True:
            return False

        return True
    except Exception:
        return False

ok(sozlesme(stride_ofset_ve_devrik), "C-contiguous stride hesabı, bellek ofseti ve zero-copy transpose contiguous kontrolü doğru çalışmalı")

def m_hep_false(boyutlar, indeksler, eksen_a, eksen_b):
    r = stride_ofset_ve_devrik(boyutlar, indeksler, eksen_a, eksen_b)
    r["devrik_contiguous_mu"] = False
    return r

def m_ofset_bozuk(boyutlar, indeksler, eksen_a, eksen_b):
    r = stride_ofset_ve_devrik(boyutlar, indeksler, eksen_a, eksen_b)
    r["orijinal_ofset"] += 1
    return r

for ad, mutant in [("boyutu 1 olan eksende contiguous kontrolünü şaşıran", m_hep_false), ("bellek ofsetini yanlış hesaplayan", m_ofset_bozuk)]:
    ok(not sozlesme(mutant), "hatalı çözüm/mutant yakalanmalı: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def stride_ofset_ve_devrik(boyutlar, indeksler, eksen_a, eksen_b):\n    n = len(boyutlar)\n    strides = [1] * n\n    for i in range(n - 2, -1, -1):\n        strides[i] = strides[i + 1] * boyutlar[i + 1]\n    ofset = sum((ind * st for ind, st in zip(indeksler, strides)))\n    devrik_boyut = list(boyutlar)\n    devrik_stride = list(strides)\n    devrik_boyut[eksen_a], devrik_boyut[eksen_b] = (devrik_boyut[eksen_b], devrik_boyut[eksen_a])\n    devrik_stride[eksen_a], devrik_stride[eksen_b] = (devrik_stride[eksen_b], devrik_stride[eksen_a])\n    beklenen_stride = 1\n    contiguous = True\n    for d, s in zip(reversed(devrik_boyut), reversed(devrik_stride)):\n        if d > 1:\n            if s != beklenen_stride:\n                contiguous = False\n                break\n            beklenen_stride *= d\n    return {'orijinal_strides': strides, 'orijinal_ofset': ofset, 'devrik_boyutlar': devrik_boyut, 'devrik_strides': devrik_stride, 'devrik_contiguous_mu': contiguous}", 'referans', 'exec'), _REF)
_t, _g = _ff(stride_ofset_ve_devrik, _REF['stride_ofset_ve_devrik'], ([2, 3, 4], [1, 2, 3], 0, 2), tohum=3399, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (stride_ofset_ve_devrik): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
def stride_ofset_ve_devrik(boyutlar, indeksler, eksen_a, eksen_b):
    n = len(boyutlar)
    strides = [1] * n
    for i in range(n - 2, -1, -1):
        strides[i] = strides[i + 1] * boyutlar[i + 1]

    ofset = sum(ind * st for ind, st in zip(indeksler, strides))

    devrik_boyut = list(boyutlar)
    devrik_stride = list(strides)
    devrik_boyut[eksen_a], devrik_boyut[eksen_b] = devrik_boyut[eksen_b], devrik_boyut[eksen_a]
    devrik_stride[eksen_a], devrik_stride[eksen_b] = devrik_stride[eksen_b], devrik_stride[eksen_a]

    beklenen_stride = 1
    contiguous = True
    for d, s in zip(reversed(devrik_boyut), reversed(devrik_stride)):
        if d > 1:
            if s != beklenen_stride:
                contiguous = False
                break
            beklenen_stride *= d

    return {
        "orijinal_strides": strides,
        "orijinal_ofset": ofset,
        "devrik_boyutlar": devrik_boyut,
        "devrik_strides": devrik_stride,
        "devrik_contiguous_mu": contiguous,
    }
```

```hint
Sağdan sola `strides[i] = strides[i+1] * boyutlar[i+1]` ile adımları kur. Devrik tensörün `contiguous` olup olmadığını kontrol ederken sağdan sola `d > 1` olan eksenlerde `s == beklenen_stride` şartını denetle ve `beklenen_stride *= d` ile ilerle.
```
:::

::: gorev 2 · Numpy/PyTorch Broadcasting Uyumluluk ve Çıktı Boyutu Hesaplayıcı
`broadcast_boyut_hesapla(sekil_a, sekil_b)` işlevini yaz.

İki tensör şekli `sekil_a` ve `sekil_b` (`list[int]`, her boyut sıfır veya pozitif; `[]` skaler) verildiğinde PyTorch/NumPy **Broadcasting** kurallarını uygulayarak:
1. Kısa olan şeklin sol tarafını `1` değerleriyle uzun olanın boyut sayısına (`max_ndim`) tamamla.
2. Sağdan sola her eksende boyutların uyumlu olup olmadığını (`d_a == d_b` veya `d_a == 1` veya `d_b == 1`) kontrol et.
   - Eğer herhangi bir eksende uyuşmazlık varsa `{"uyumlu_mu": False, "cikti_sekli": [], "genisletilmis_stride_a": [], "genisletilmis_stride_b": []}` döndür.
3. Uyumluysa:
   - `"uyumlu_mu"`: `True`
   - `"cikti_sekli"`: Uyumlu her eksende `d_a == 1` ise `d_b`, değilse `d_a` seçilir. Pozitif boyutlarda bu `max(d_a, d_b)` ile aynıdır; ancak `0` ve `1` için çıktı `0` olur (boş eksen).
   - `"genisletilmis_stride_a"` ve `"genisletilmis_stride_b"`: Her iki tensörün kendi başlangıç C-Contiguous adım kaymalarını hesapladıktan sonra (boş boyutta PyTorch gibi sağdan sola `st[i] = st[i+1] * max(1, sekil[i+1])` kullan), sol tarafa eklenen veya boyutu `1` iken `1` dışında bir boyuta (0 dahil) yayınlanan (**Broadcasted**) eksenlerin adım kaymasını **`0`** (`zero-stride trick`) yaparak oluşturulan `max_ndim` uzunluğundaki adım listeleri! (Not: Eğer çıktı boyutunun kendisi de o eksende `1` ise veya eksen değiştirilmediyse orijinal stride korunur; yalnız `d == 1` iken hedef boyut `> 1` olduğunda veya sol tarafa yeni eklendiğinde stride `0` olur; daha genel kural olarak `d == 1` olan tüm yayın eksenlerinde `cikti_d != 1` ise stride `0` yapılır).

```starter
def broadcast_boyut_hesapla(sekil_a, sekil_b):
    # KUSURLU BAŞLANGIÇ KODU: Broadcasting uyumluluk ve sanal 0-stride hesabını yapmıyor!
    return {
        "uyumlu_mu": False,
        "cikti_sekli": [],
        "genisletilmis_stride_a": [],
        "genisletilmis_stride_b": [],
    }

print("Broadcast:", broadcast_boyut_hesapla([4, 1, 8], [3, 8]))
```

```test
import copy

def sozlesme(fn):
    try:
        # Test 1: [4, 1, 8] (strides: [8, 8, 1]) ile [3, 8] (strides: [8, 1] -> soluna 1 eklenir: [1, 3, 8])
        # Çıktı şekli: [4, 3, 8]
        # A için dim 1 (1 -> 3) yayınlandı -> stride_a = [8, 0, 1]
        # B için dim 0 (1 -> 4) yayınlandı -> stride_b = [0, 8, 1]
        a, b = [4, 1, 8], [3, 8]
        ak, bk = copy.deepcopy(a), copy.deepcopy(b)
        r1 = fn(a, b)
        if a != ak or b != bk or not isinstance(r1, dict):
            return False
        beklenen1 = {
            "uyumlu_mu": True,
            "cikti_sekli": [4, 3, 8],
            "genisletilmis_stride_a": [8, 0, 1],
            "genisletilmis_stride_b": [0, 8, 1],
        }
        if r1 != beklenen1:
            return False

        # Test 2: Uyumsuz şekiller [4, 5] ve [4, 3]
        r2 = fn([4, 5], [4, 3])
        if r2 != {
            "uyumlu_mu": False,
            "cikti_sekli": [],
            "genisletilmis_stride_a": [],
            "genisletilmis_stride_b": [],
        }:
            return False

        if fn([2], [1, 2]) != {"uyumlu_mu": True, "cikti_sekli": [1, 2], "genisletilmis_stride_a": [0, 1], "genisletilmis_stride_b": [2, 1]}: return False
        # Kurulu torch.broadcast_shapes/broadcast_to ile doğrulanmış boş eksenler.
        for a, b, sonuc, sa, sb in (
            ([0], [1], [0], [1], [0]),
            ([1], [0], [0], [0], [1]),
            ([3, 0], [1, 0], [3, 0], [1, 1], [0, 1]),
        ):
            if fn(a, b) != {"uyumlu_mu": True, "cikti_sekli": sonuc, "genisletilmis_stride_a": sa, "genisletilmis_stride_b": sb}: return False
        if fn([0], [2])["uyumlu_mu"]: return False
        # Hedef boyut 2: >1 sınırını >2 yapan ve 1'i 2 yapan mutantlar.
        for a, b, beklenen in (
            ([1], [2], {"uyumlu_mu": True, "cikti_sekli": [2], "genisletilmis_stride_a": [0], "genisletilmis_stride_b": [1]}),
            ([2], [1], {"uyumlu_mu": True, "cikti_sekli": [2], "genisletilmis_stride_a": [1], "genisletilmis_stride_b": [0]}),
            ([1], [1], {"uyumlu_mu": True, "cikti_sekli": [1], "genisletilmis_stride_a": [1], "genisletilmis_stride_b": [1]}),
            ([2, 1], [2, 1], {"uyumlu_mu": True, "cikti_sekli": [2, 1], "genisletilmis_stride_a": [1, 1], "genisletilmis_stride_b": [1, 1]}),
        ):
            if fn(a, b) != beklenen: return False
        return True
    except Exception:
        return False

ok(sozlesme(broadcast_boyut_hesapla), "Broadcasting kuralları, çıktı şekli ve zero-stride (0 adım kayması) doğru hesaplanmalı")

def m_stride_sifirlamayan(sekil_a, sekil_b):
    r = broadcast_boyut_hesapla(sekil_a, sekil_b)
    if r["genisletilmis_stride_a"]:
        r["genisletilmis_stride_a"] = [1] * len(r["cikti_sekli"])
    return r

def m_hep_uyumlu(sekil_a, sekil_b):
    r = broadcast_boyut_hesapla(sekil_a, sekil_b)
    r["uyumlu_mu"] = True
    return r

for ad, mutant in [("yayınlanan eksende stride=0 yapmayan", m_stride_sifirlamayan), ("uyumsuz boyutları reddetmeyen", m_hep_uyumlu)]:
    ok(not sozlesme(mutant), "hatalı çözüm/mutant yakalanmalı: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def _c_strides(sekil):\n    n = len(sekil)\n    st = [1] * n\n    for i in range(n - 2, -1, -1):\n        st[i] = st[i + 1] * max(1, sekil[i + 1])\n    return st\n\ndef broadcast_boyut_hesapla(sekil_a, sekil_b):\n    st_a = _c_strides(sekil_a)\n    st_b = _c_strides(sekil_b)\n    ndim = max(len(sekil_a), len(sekil_b))\n    pad_a = [1] * (ndim - len(sekil_a)) + list(sekil_a)\n    pad_b = [1] * (ndim - len(sekil_b)) + list(sekil_b)\n    pad_st_a = [0] * (ndim - len(sekil_a)) + st_a\n    pad_st_b = [0] * (ndim - len(sekil_b)) + st_b\n    cikti = []\n    yeni_st_a = []\n    yeni_st_b = []\n    for da, db, sa, sb in zip(pad_a, pad_b, pad_st_a, pad_st_b):\n        if da != db and da != 1 and (db != 1):\n            return {'uyumlu_mu': False, 'cikti_sekli': [], 'genisletilmis_stride_a': [], 'genisletilmis_stride_b': []}\n        hedef = db if da == 1 else da\n        cikti.append(hedef)\n        yeni_st_a.append(0 if da == 1 and hedef != 1 else sa)\n        yeni_st_b.append(0 if db == 1 and hedef != 1 else sb)\n    return {'uyumlu_mu': True, 'cikti_sekli': cikti, 'genisletilmis_stride_a': yeni_st_a, 'genisletilmis_stride_b': yeni_st_b}", 'referans', 'exec'), _REF)
_t, _g = _ff(broadcast_boyut_hesapla, _REF['broadcast_boyut_hesapla'], ([4, 1, 8], [3, 8]), tohum=3488, en_cok=600, mod='gecerli', butce='oto', ekler=[([4, 1, 8], [2, 8], ), ([3, 8], [4, 1, 8], ), ([8], [2, 3, 8], )])
ok(_t, "farksal tarama (broadcast_boyut_hesapla): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
def _c_strides(sekil):
    n = len(sekil)
    st = [1] * n
    for i in range(n - 2, -1, -1):
        st[i] = st[i + 1] * max(1, sekil[i + 1])
    return st

def broadcast_boyut_hesapla(sekil_a, sekil_b):
    st_a = _c_strides(sekil_a)
    st_b = _c_strides(sekil_b)

    ndim = max(len(sekil_a), len(sekil_b))
    pad_a = [1] * (ndim - len(sekil_a)) + list(sekil_a)
    pad_b = [1] * (ndim - len(sekil_b)) + list(sekil_b)
    pad_st_a = [0] * (ndim - len(sekil_a)) + st_a
    pad_st_b = [0] * (ndim - len(sekil_b)) + st_b

    cikti = []
    yeni_st_a = []
    yeni_st_b = []

    for da, db, sa, sb in zip(pad_a, pad_b, pad_st_a, pad_st_b):
        if da != db and da != 1 and db != 1:
            return {
                "uyumlu_mu": False,
                "cikti_sekli": [],
                "genisletilmis_stride_a": [],
                "genisletilmis_stride_b": [],
            }
        hedef = db if da == 1 else da
        cikti.append(hedef)
        yeni_st_a.append(0 if (da == 1 and hedef != 1) else sa)
        yeni_st_b.append(0 if (db == 1 and hedef != 1) else sb)

    return {
        "uyumlu_mu": True,
        "cikti_sekli": cikti,
        "genisletilmis_stride_a": yeni_st_a,
        "genisletilmis_stride_b": yeni_st_b,
    }
```

```hint
Önce her iki şeklin kendi C-Contiguous adımlarını (`_c_strides`) bul. Kısa olan şeklin soluna `1`, adım listesinin soluna `0` ekle. Her eksende `da != db and da != 1 and db != 1` ise uyumsuz döndür; uyumluysa `da == 1 and hedef != 1` olan eksenlerin adımını `0` yap.
```
:::

::: gorev 3 · Einops Desen Motoru: rearrange Eksen Sırası ve Çıktı Boyutu
`einops.rearrange(x, "b h w c -> b c (h w)")` gibi bir desen, eksenlerin **permütasyonunu** ve bazı eksenlerin **birleştirilmesini** tek satırda anlatır. `einops_rearrange_plan(desen, sekil)` işlevini yaz.

**Kurallar:**
1. `desen` tam olarak bir `->` içeren `str` olmalı. Sol taraf yalnız eksen adlarından oluşur (parantez yok); sağ taraf ad ya da `( ... )` grubu içerebilir. Adlar `[A-Za-z_][A-Za-z0-9_]*` biçiminde olmalı.
2. Her ad her tarafta tam bir kez geçmeli ve iki tarafın ad kümesi aynı olmalı. `sekil` uzunluğu sol taraftaki ad sayısına eşit, öğeleri en az 1 olan `int` (`bool` değil) olmalı. Değilse `ValueError`.
3. `"permutasyon"`: sağ taraftaki adlar (gruplar açılarak) soldan sağa okunduğunda her birinin sol taraftaki indeksi.
4. `"cikti_sekli"`: sağ taraftaki her öğe için boyut (grup ise içindeki boyutların çarpımı).
5. Bu basit planlayıcıda `"gorunum_yeterli"` yalnız yeterli bir koşulu bildirir; `False`, her tensörde kopya gerektiğinin kanıtı değildir (örneğin singleton eksen permütasyonu). `"gorunum_yeterli"`: permütasyon birim (`[0, 1, ..., n-1]`) ise `True`. Bu durumda yalnız komşu eksenler birleşir ve kopya gerekmez.

```starter
def einops_rearrange_plan(desen, sekil):
    # KUSURLU BAŞLANGIÇ: deseni yok sayıp şekli aynen döndürüyor
    return {"permutasyon": list(range(len(sekil))), "cikti_sekli": list(sekil), "gorunum_yeterli": True}

print(einops_rearrange_plan("b h w c -> b c h w", [2, 3, 4, 5]))
```

```test
fn = need("einops_rearrange_plan")
r = fn("b h w c -> b c h w", [2, 3, 4, 5])
eq(r["permutasyon"], [0, 3, 1, 2], "NHWC → NCHW")
eq(r["cikti_sekli"], [2, 5, 3, 4], "boyutlar permütasyonla taşınır")
eq(r["gorunum_yeterli"], False, "basit planlayıcı permütasyon için görünümü garanti etmez")
r2 = fn("b h w c -> b (h w) c", [2, 3, 4, 5])
eq(r2["permutasyon"], [0, 1, 2, 3], "sıra değişmiyor")
eq(r2["cikti_sekli"], [2, 12, 5], "h·w = 12")
eq(r2["gorunum_yeterli"], True, "komşu eksen birleşimi görünümle yapılır")
eq(fn("b c h w -> b (c h w)", [2, 3, 4, 5])["cikti_sekli"], [2, 60], "düzleştirme")
r3 = fn("h w c -> c (w h)", [3, 4, 5])
eq(r3["permutasyon"], [2, 1, 0], "c, w, h sırası")
eq(r3["cikti_sekli"], [5, 12], "w·h = 12")
eq(fn("x->x", [7])["cikti_sekli"], [7], "boşluksuz desen")
raises(ValueError, fn, "b h -> b", [2, 3])
raises(ValueError, fn, "b h -> b h h", [2, 3])
raises(ValueError, fn, "(b h) -> b h", [6])
raises(ValueError, fn, "b h -> h b", [2])
raises(ValueError, fn, "b h -> h b", [2, 0])
raises(ValueError, fn, "b h h b", [2, 3])
raises(ValueError, fn, "b h -> (h b", [2, 3])
eq(fn("batch token_dim -> token_dim batch", [2, 3]), {"permutasyon": [1, 0], "cikti_sekli": [3, 2], "gorunum_yeterli": False}, "çok karakterli eksen adları parçalanmaz")
for desen, sekil in (
    ("a -> a (", [2]),
    ("a -> ((a))", [2]),
    ("a -> ((a)", [2]),
    ("a -> () a", [2]),
    ("a a -> a", [2, 2]),
    ("bad-name -> bad-name", [2]),
    ("1a -> 1a", [2]),
    ("a -> a)", [2]),
):
    raises(ValueError, fn, desen, sekil)


# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile('import re\n_AD = re.compile(\'^[A-Za-z_][A-Za-z0-9_]*$\')\n\ndef _parcala(taraf, grup_izinli):\n    jetonlar = taraf.replace(\'(\', \' ( \').replace(\')\', \' ) \').split()\n    ogeler, grup = ([], None)\n    for j in jetonlar:\n        if j == \'(\':\n            if not grup_izinli or grup is not None:\n                raise ValueError(\'bu tarafta grup kullanılamaz\')\n            grup = []\n        elif j == \')\':\n            if grup is None or not grup:\n                raise ValueError(\'parantez hatası\')\n            ogeler.append(grup)\n            grup = None\n        else:\n            if not _AD.match(j):\n                raise ValueError(\'geçersiz eksen adı: \' + j)\n            (grup if grup is not None else ogeler).append(j)\n    if grup is not None:\n        raise ValueError(\'kapanmayan parantez\')\n    return ogeler\n\ndef einops_rearrange_plan(desen, sekil):\n    if not isinstance(desen, str) or desen.count(\'->\') != 1:\n        raise ValueError("desen tek bir \'->\' içeren str olmalı")\n    sol_m, sag_m = desen.split(\'->\')\n    sol = _parcala(sol_m, False)\n    sag = _parcala(sag_m, True)\n    sag_duz = [a for o in sag for a in (o if isinstance(o, list) else [o])]\n    if len(set(sol)) != len(sol) or len(set(sag_duz)) != len(sag_duz) or set(sol) != set(sag_duz):\n        raise ValueError(\'her ad iki tarafta tam bir kez geçmeli\')\n    if not isinstance(sekil, list) or len(sekil) != len(sol):\n        raise ValueError(\'sekil uzunluğu sol taraftaki ad sayısına eşit olmalı\')\n    for d in sekil:\n        if isinstance(d, bool) or not isinstance(d, int) or d < 1:\n            raise ValueError(\'boyutlar en az 1 olan tam sayı olmalı\')\n    boy = dict(zip(sol, sekil))\n    perm = [sol.index(a) for a in sag_duz]\n    cikti = []\n    for o in sag:\n        if isinstance(o, list):\n            carpim = 1\n            for a in o:\n                carpim *= boy[a]\n            cikti.append(carpim)\n        else:\n            cikti.append(boy[o])\n    return {\'permutasyon\': perm, \'cikti_sekli\': cikti, \'gorunum_yeterli\': perm == list(range(len(sol)))}', 'referans', 'exec'), _REF)
_t, _g = _ff(einops_rearrange_plan, _REF['einops_rearrange_plan'], ('b h w c -> b c h w', [2, 3, 4, 5]), tohum=3276, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (einops_rearrange_plan): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
import re

_AD = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

def _parcala(taraf, grup_izinli):
    jetonlar = taraf.replace("(", " ( ").replace(")", " ) ").split()
    ogeler, grup = [], None
    for j in jetonlar:
        if j == "(":
            if not grup_izinli or grup is not None:
                raise ValueError("bu tarafta grup kullanılamaz")
            grup = []
        elif j == ")":
            if grup is None or not grup:
                raise ValueError("parantez hatası")
            ogeler.append(grup)
            grup = None
        else:
            if not _AD.match(j):
                raise ValueError("geçersiz eksen adı: " + j)
            (grup if grup is not None else ogeler).append(j)
    if grup is not None:
        raise ValueError("kapanmayan parantez")
    return ogeler

def einops_rearrange_plan(desen, sekil):
    if not isinstance(desen, str) or desen.count("->") != 1:
        raise ValueError("desen tek bir '->' içeren str olmalı")
    sol_m, sag_m = desen.split("->")
    sol = _parcala(sol_m, False)
    sag = _parcala(sag_m, True)
    sag_duz = [a for o in sag for a in (o if isinstance(o, list) else [o])]
    if len(set(sol)) != len(sol) or len(set(sag_duz)) != len(sag_duz) or set(sol) != set(sag_duz):
        raise ValueError("her ad iki tarafta tam bir kez geçmeli")
    if not isinstance(sekil, list) or len(sekil) != len(sol):
        raise ValueError("sekil uzunluğu sol taraftaki ad sayısına eşit olmalı")
    for d in sekil:
        if isinstance(d, bool) or not isinstance(d, int) or d < 1:
            raise ValueError("boyutlar en az 1 olan tam sayı olmalı")
    boy = dict(zip(sol, sekil))
    perm = [sol.index(a) for a in sag_duz]
    cikti = []
    for o in sag:
        if isinstance(o, list):
            carpim = 1
            for a in o:
                carpim *= boy[a]
            cikti.append(carpim)
        else:
            cikti.append(boy[o])
    return {"permutasyon": perm, "cikti_sekli": cikti, "gorunum_yeterli": perm == list(range(len(sol)))}
```

```hint
Parantezleri boşluklu jetona çevirip `split()` ile ayrıştır; sağ taraftaki grupları liste olarak tut, permütasyon için düzleştir.
```
:::

::: anlat Gerçek deney: SmolLM2'nin gerçek dikkat tensörlerinde stride, broadcasting ve einops
Final, SmolLM2-135M'in gerçek ara tensörlerini kullanır (indirme yok):

- **Stride ve devrik:** Hugging Face Llama gerçeklemesi sorgu vektörünü önce `(b, t, h, d)` şekline `view` eder, sonra `transpose(1, 2)` ile `(b, h, t, d)` yapar. Bu tensör, gizli durumlar, `gate_proj` ağırlığı ve başlara bölünmüş `q_proj` ağırlığı üzerinde 40 rastgele indeks ve eksen çifti seçilir. Senin işlevinin stride, ofset, devrik şekil/stride ve `contiguous` sonucu torch'un `.stride()`, `storage_offset()` ve `is_contiguous()` değerleriyle karşılaştırılır.
- **Broadcasting:** modelin içindeki gerçek şekil çiftleri: RMSNorm ağırlığı × gizli durum, dikkat skoru + maske, RoPE `cos` × sorgu, uyumsuz q/k boyutları. Sonuç `torch.broadcast_shapes` ve `broadcast_to(...).stride()` ile karşılaştırılır.
- **Sessiz hata:** gerçek token log-olasılıkları `(N,)` şeklinde, hedef yanlışlıkla `(N, 1)`. İkisinin farkı hata vermeden `(N, N)` olur ve kayıp binlerce kat büyür. Senin işlevin bu çifti "uyumlu" bulur: broadcasting kuralı açısından doğrudur, anlam açısından yanlıştır.
- **einops:** gerçek sorgu tensörü üzerinde dört desen (`b t h d -> b h t d`, dikkat çıktısını birleştiren `b h t d -> b t (h d)` vb.) `einops.rearrange` ile çalıştırılır; şekil, permütasyon ve sonucun kopyasız ve bitişik (contiguous) bir görünüm olup olmadığı karşılaştırılır.

**Güvenlik yönü — tensör dosyalarında kod çalıştırma:** Tensörlerin diske yazılma biçimi de bir güvenlik kararıdır. Gerçek bir SmolLM2 ağırlığı, açıldığında geçici klasörde zararsız bir kanarya dosyası oluşturan bir pickle yüküyle birlikte `torch.save` ile kaydedilir. `torch.load(weights_only=False)` dosyayı açarken yükü çalıştırır, `weights_only=True` reddeder. Aynı ağırlık safetensors ile kaydedilince dosya yalnız bir JSON başlık (dtype, shape, bayt aralığı) ve ham baytlardır: dersin bellek düzeninin diskteki karşılığı. Başlıkta şekli veriden büyük gösteren bozuk bir dosya reddedilir.

Kabul: üç işlevin farksal taramayı geçmesi ve gerçek tensörlerde torch/einops ile tüm karşılaştırmaların aynı çıkması. Ayrıca kanarya yükü weights_only=False ile çalışmalı, weights_only=True ile engellenmeli; safetensors başlığı bayt aralığıyla tutarlı olmalı ve bozuk başlık reddedilmelidir.

**Kanıt dosyasını oku:** `q_ornek`, `broadcast_tablo`, `sessiz_hata_dogru_kayip`, `sessiz_hata_yayilmis_kayip`, `einops_tablo`. Soru 1: HF neden `transpose(1, 2)` sonrasında `contiguous()` çağırmadan `view` yapamaz? Soru 2: `b h t d -> b t (h d)` neden kopya gerektirir? Soru 3: Sessiz broadcasting hatasını yakalamak için eğitim koduna hangi tek satırlık kontrolü eklerdin?
:::

::: gorev Gerçek deney · SmolLM2 tensörlerinde stride, broadcasting ve einops karşılaştırması
Önceki görevlerdeki `stride_ofset_ve_devrik`, `broadcast_boyut_hesapla`, `einops_rearrange_plan` işlevlerini buraya birleştir (çözümlerini kopyalayabilirsin). Çalıştır gerçek ölçüm tablosunu gösterir; Kontrol Et önce işlevlerini gizli verilerle ve farksal taramayla sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
timeout: 180
```
```starter
import ai_lab
def stride_ofset_ve_devrik(boyutlar, indeksler, eksen_a, eksen_b):
    n = len(boyutlar)
    return {'orijinal_strides': [1] * n, 'orijinal_ofset': 0, 'devrik_boyutlar': list(boyutlar), 'devrik_strides': [1] * n, 'devrik_contiguous_mu': True}

def broadcast_boyut_hesapla(sekil_a, sekil_b):
    return {'uyumlu_mu': False, 'cikti_sekli': [], 'genisletilmis_stride_a': [], 'genisletilmis_stride_b': []}

def einops_rearrange_plan(desen, sekil):
    return {'permutasyon': list(range(len(sekil))), 'cikti_sekli': list(sekil), 'gorunum_yeterli': True}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_13 as D
    D.goster(stride_ofset_ve_devrik, broadcast_boyut_hesapla, einops_rearrange_plan)
```
```test
import ai_lab
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('_gercek_tensorler', 'kanit_yaz'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
stride_ofset_ve_devrik = need("stride_ofset_ve_devrik")
broadcast_boyut_hesapla = need("broadcast_boyut_hesapla")
einops_rearrange_plan = need("einops_rearrange_plan")
# farksal tarama (görev çözümlerinden derlenen referans)
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile('def stride_ofset_ve_devrik(boyutlar, indeksler, eksen_a, eksen_b):\n    n = len(boyutlar)\n    strides = [1] * n\n    for i in range(n - 2, -1, -1):\n        strides[i] = strides[i + 1] * boyutlar[i + 1]\n    ofset = sum((ind * st for ind, st in zip(indeksler, strides)))\n    devrik_boyut = list(boyutlar)\n    devrik_stride = list(strides)\n    devrik_boyut[eksen_a], devrik_boyut[eksen_b] = (devrik_boyut[eksen_b], devrik_boyut[eksen_a])\n    devrik_stride[eksen_a], devrik_stride[eksen_b] = (devrik_stride[eksen_b], devrik_stride[eksen_a])\n    beklenen_stride = 1\n    contiguous = True\n    for d, s in zip(reversed(devrik_boyut), reversed(devrik_stride)):\n        if d > 1:\n            if s != beklenen_stride:\n                contiguous = False\n                break\n            beklenen_stride *= d\n    return {\'orijinal_strides\': strides, \'orijinal_ofset\': ofset, \'devrik_boyutlar\': devrik_boyut, \'devrik_strides\': devrik_stride, \'devrik_contiguous_mu\': contiguous}\n\ndef _c_strides(sekil):\n    n = len(sekil)\n    st = [1] * n\n    for i in range(n - 2, -1, -1):\n        st[i] = st[i + 1] * max(1, sekil[i + 1])\n    return st\n\ndef broadcast_boyut_hesapla(sekil_a, sekil_b):\n    st_a = _c_strides(sekil_a)\n    st_b = _c_strides(sekil_b)\n    ndim = max(len(sekil_a), len(sekil_b))\n    pad_a = [1] * (ndim - len(sekil_a)) + list(sekil_a)\n    pad_b = [1] * (ndim - len(sekil_b)) + list(sekil_b)\n    pad_st_a = [0] * (ndim - len(sekil_a)) + st_a\n    pad_st_b = [0] * (ndim - len(sekil_b)) + st_b\n    cikti = []\n    yeni_st_a = []\n    yeni_st_b = []\n    for da, db, sa, sb in zip(pad_a, pad_b, pad_st_a, pad_st_b):\n        if da != db and da != 1 and (db != 1):\n            return {\'uyumlu_mu\': False, \'cikti_sekli\': [], \'genisletilmis_stride_a\': [], \'genisletilmis_stride_b\': []}\n        hedef = db if da == 1 else da\n        cikti.append(hedef)\n        yeni_st_a.append(0 if da == 1 and hedef != 1 else sa)\n        yeni_st_b.append(0 if db == 1 and hedef != 1 else sb)\n    return {\'uyumlu_mu\': True, \'cikti_sekli\': cikti, \'genisletilmis_stride_a\': yeni_st_a, \'genisletilmis_stride_b\': yeni_st_b}\n\nimport re\n_AD = re.compile(\'^[A-Za-z_][A-Za-z0-9_]*$\')\n\ndef _parcala(taraf, grup_izinli):\n    jetonlar = taraf.replace(\'(\', \' ( \').replace(\')\', \' ) \').split()\n    ogeler, grup = ([], None)\n    for j in jetonlar:\n        if j == \'(\':\n            if not grup_izinli or grup is not None:\n                raise ValueError(\'bu tarafta grup kullanılamaz\')\n            grup = []\n        elif j == \')\':\n            if grup is None or not grup:\n                raise ValueError(\'parantez hatası\')\n            ogeler.append(grup)\n            grup = None\n        else:\n            if not _AD.match(j):\n                raise ValueError(\'geçersiz eksen adı: \' + j)\n            (grup if grup is not None else ogeler).append(j)\n    if grup is not None:\n        raise ValueError(\'kapanmayan parantez\')\n    return ogeler\n\ndef einops_rearrange_plan(desen, sekil):\n    if not isinstance(desen, str) or desen.count(\'->\') != 1:\n        raise ValueError("desen tek bir \'->\' içeren str olmalı")\n    sol_m, sag_m = desen.split(\'->\')\n    sol = _parcala(sol_m, False)\n    sag = _parcala(sag_m, True)\n    sag_duz = [a for o in sag for a in (o if isinstance(o, list) else [o])]\n    if len(set(sol)) != len(sol) or len(set(sag_duz)) != len(sag_duz) or set(sol) != set(sag_duz):\n        raise ValueError(\'her ad iki tarafta tam bir kez geçmeli\')\n    if not isinstance(sekil, list) or len(sekil) != len(sol):\n        raise ValueError(\'sekil uzunluğu sol taraftaki ad sayısına eşit olmalı\')\n    for d in sekil:\n        if isinstance(d, bool) or not isinstance(d, int) or d < 1:\n            raise ValueError(\'boyutlar en az 1 olan tam sayı olmalı\')\n    boy = dict(zip(sol, sekil))\n    perm = [sol.index(a) for a in sag_duz]\n    cikti = []\n    for o in sag:\n        if isinstance(o, list):\n            carpim = 1\n            for a in o:\n                carpim *= boy[a]\n            cikti.append(carpim)\n        else:\n            cikti.append(boy[o])\n    return {\'permutasyon\': perm, \'cikti_sekli\': cikti, \'gorunum_yeterli\': perm == list(range(len(sol)))}', 'referans', 'exec'), _REF)
_t, _g = _ff(stride_ofset_ve_devrik, _REF['stride_ofset_ve_devrik'], ([2, 3, 4], [1, 2, 3], 0, 2), tohum=3399, en_cok=600, mod='gecerli', butce='oto')
kontrol(_t, "farksal tarama (stride_ofset_ve_devrik): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(broadcast_boyut_hesapla, _REF['broadcast_boyut_hesapla'], ([4, 1, 8], [3, 8]), tohum=3488, en_cok=600, mod='gecerli', butce='oto', ekler=[([4, 1, 8], [2, 8], ), ([3, 8], [4, 1, 8], ), ([8], [2, 3, 8], )])
kontrol(_t, "farksal tarama (broadcast_boyut_hesapla): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(einops_rearrange_plan, _REF['einops_rearrange_plan'], ('b h w c -> b c h w', [2, 3, 4, 5]), tohum=3276, en_cok=600, mod='tam', butce='oto')
kontrol(_t, "farksal tarama (einops_rearrange_plan): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
def _birim_13():
    if stride_ofset_ve_devrik([1, 5, 4], [0, 3, 2], 0, 1) != _REF['stride_ofset_ve_devrik']([1, 5, 4], [0, 3, 2], 0, 1):
        return False
    for _a, _b in (([0], [1]), ([1], [0]), ([3, 0], [1, 0]), ([2], [1, 2]), ([1], [1]), ([2, 1], [2, 1])):
        if broadcast_boyut_hesapla(_a, _b) != _REF['broadcast_boyut_hesapla'](_a, _b):
            return False
    for _d, _s in (("b h w c -> b (h w) c", [2, 3, 4, 5]), ("h w c -> c (w h)", [3, 4, 5]), ("batch token_dim -> token_dim batch", [2, 3])):
        if einops_rearrange_plan(_d, _s) != _REF['einops_rearrange_plan'](_d, _s):
            return False
    for _d, _s in (("(b h) -> b h", [6]), ("b h -> (h b", [2, 3]), ("a -> a (", [2]), ("a -> ((a))", [2]), ("a -> ((a)", [2]), ("a -> () a", [2]), ("a a -> a", [2, 2]), ("a -> a a", [2]), ("b h -> b", [2, 3]), ("a -> b", [2]), ("1a -> 1a", [2]), ("a -> a)", [2]), ("a b", [2, 3])):
        try:
            einops_rearrange_plan(_d, _s)
            return False
        except ValueError:
            pass
    return True
kontrol(_birim_13(), "tekil stride, boş eksen broadcasting ve einops grup/hata sözleşmesi")
if not all(checks): stop()
from sandbox import ai_gercek_ai_uretim_13 as D
try: r = D.deney(stride_ofset_ve_devrik, broadcast_boyut_hesapla, einops_rearrange_plan)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r['stride_ayni'], 'stride, ofset ve devrik sonuçları gerçek tensörlerde torch ile aynı')
kontrol(r['broadcast_ayni'], "broadcasting şekil ve genişletilmiş stride'ları torch.broadcast_shapes/broadcast_to ile aynı")
kontrol(r['einops_ayni'] and r['hf_transpose_ayni'], 'einops planı gerçek q tensöründe einops.rearrange ile aynı')
kontrol(r['sessiz_hata_kat'] > 10, '(N,) − (N,1) broadcasting hatası kaybı sessizce büyütüyor')
kontrol(r['serilestirme_guvenligi'], "pickle yükü weights_only=False'ta çalıştı, True'da engellendi; safetensors tutarlı, bozuk başlık reddedildi")
ai_lab.kanit_yaz("ai-uretim-13-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-uretim-13", "deney": r})
```
```solution
import ai_lab
def stride_ofset_ve_devrik(boyutlar, indeksler, eksen_a, eksen_b):
    n = len(boyutlar)
    strides = [1] * n
    for i in range(n - 2, -1, -1):
        strides[i] = strides[i + 1] * boyutlar[i + 1]
    ofset = sum((ind * st for ind, st in zip(indeksler, strides)))
    devrik_boyut = list(boyutlar)
    devrik_stride = list(strides)
    devrik_boyut[eksen_a], devrik_boyut[eksen_b] = (devrik_boyut[eksen_b], devrik_boyut[eksen_a])
    devrik_stride[eksen_a], devrik_stride[eksen_b] = (devrik_stride[eksen_b], devrik_stride[eksen_a])
    beklenen_stride = 1
    contiguous = True
    for d, s in zip(reversed(devrik_boyut), reversed(devrik_stride)):
        if d > 1:
            if s != beklenen_stride:
                contiguous = False
                break
            beklenen_stride *= d
    return {'orijinal_strides': strides, 'orijinal_ofset': ofset, 'devrik_boyutlar': devrik_boyut, 'devrik_strides': devrik_stride, 'devrik_contiguous_mu': contiguous}

def _c_strides(sekil):
    n = len(sekil)
    st = [1] * n
    for i in range(n - 2, -1, -1):
        st[i] = st[i + 1] * max(1, sekil[i + 1])
    return st

def broadcast_boyut_hesapla(sekil_a, sekil_b):
    st_a = _c_strides(sekil_a)
    st_b = _c_strides(sekil_b)
    ndim = max(len(sekil_a), len(sekil_b))
    pad_a = [1] * (ndim - len(sekil_a)) + list(sekil_a)
    pad_b = [1] * (ndim - len(sekil_b)) + list(sekil_b)
    pad_st_a = [0] * (ndim - len(sekil_a)) + st_a
    pad_st_b = [0] * (ndim - len(sekil_b)) + st_b
    cikti = []
    yeni_st_a = []
    yeni_st_b = []
    for da, db, sa, sb in zip(pad_a, pad_b, pad_st_a, pad_st_b):
        if da != db and da != 1 and (db != 1):
            return {'uyumlu_mu': False, 'cikti_sekli': [], 'genisletilmis_stride_a': [], 'genisletilmis_stride_b': []}
        hedef = db if da == 1 else da
        cikti.append(hedef)
        yeni_st_a.append(0 if da == 1 and hedef != 1 else sa)
        yeni_st_b.append(0 if db == 1 and hedef != 1 else sb)
    return {'uyumlu_mu': True, 'cikti_sekli': cikti, 'genisletilmis_stride_a': yeni_st_a, 'genisletilmis_stride_b': yeni_st_b}

import re
_AD = re.compile('^[A-Za-z_][A-Za-z0-9_]*$')

def _parcala(taraf, grup_izinli):
    jetonlar = taraf.replace('(', ' ( ').replace(')', ' ) ').split()
    ogeler, grup = ([], None)
    for j in jetonlar:
        if j == '(':
            if not grup_izinli or grup is not None:
                raise ValueError('bu tarafta grup kullanılamaz')
            grup = []
        elif j == ')':
            if grup is None or not grup:
                raise ValueError('parantez hatası')
            ogeler.append(grup)
            grup = None
        else:
            if not _AD.match(j):
                raise ValueError('geçersiz eksen adı: ' + j)
            (grup if grup is not None else ogeler).append(j)
    if grup is not None:
        raise ValueError('kapanmayan parantez')
    return ogeler

def einops_rearrange_plan(desen, sekil):
    if not isinstance(desen, str) or desen.count('->') != 1:
        raise ValueError("desen tek bir '->' içeren str olmalı")
    sol_m, sag_m = desen.split('->')
    sol = _parcala(sol_m, False)
    sag = _parcala(sag_m, True)
    sag_duz = [a for o in sag for a in (o if isinstance(o, list) else [o])]
    if len(set(sol)) != len(sol) or len(set(sag_duz)) != len(sag_duz) or set(sol) != set(sag_duz):
        raise ValueError('her ad iki tarafta tam bir kez geçmeli')
    if not isinstance(sekil, list) or len(sekil) != len(sol):
        raise ValueError('sekil uzunluğu sol taraftaki ad sayısına eşit olmalı')
    for d in sekil:
        if isinstance(d, bool) or not isinstance(d, int) or d < 1:
            raise ValueError('boyutlar en az 1 olan tam sayı olmalı')
    boy = dict(zip(sol, sekil))
    perm = [sol.index(a) for a in sag_duz]
    cikti = []
    for o in sag:
        if isinstance(o, list):
            carpim = 1
            for a in o:
                carpim *= boy[a]
            cikti.append(carpim)
        else:
            cikti.append(boy[o])
    return {'permutasyon': perm, 'cikti_sekli': cikti, 'gorunum_yeterli': perm == list(range(len(sol)))}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_13 as D
    D.goster(stride_ofset_ve_devrik, broadcast_boyut_hesapla, einops_rearrange_plan)
```
```hint
Üç görevin çözümlerini olduğu gibi buraya koy.
```
:::

::: anlat Sınır
Görevler stride ile bellek ofsetini, zero-copy transpose'u ve broadcasting uyumluluğunu saf Python ile hesaplatır; final adım bunları gerçek SmolLM2 tensörlerinde torch ve einops ile karşılaştırır; einops görevi rearrange'in yalnız sağ tarafta birleştirme yapan alt kümesini kapsar (eksen bölme ve tekrar yoktur). PyTorch'ta stride eleman cinsindendir, NumPy'de ise bayt cinsindendir; ikisini karıştırmak yanlış ofset verir. Gerçek kodda sıfır stride (broadcast, expand) ve NumPy'de negatif stride (ters çevirme) bulunur. .view() yalnız bitişik ya da uyumlu stride'lı tensörde çalışır; .reshape() gerekirse sessizce kopya yapar ve bu bellek/performans maliyetini gizler.

Kaynaklar: [PyTorch - torch.Tensor.stride belgesi](https://docs.pytorch.org/docs/stable/generated/torch.Tensor.stride.html), [NumPy - Broadcasting belgesi](https://numpy.org/doc/stable/user/basics.broadcasting.html), [Rogozhnikov - einops](https://github.com/arogozhnikov/einops).
:::

::: dusun
PyTorch'ta çok sık yapılan ölümcül bir performans hatası şudur:
Bir mühendis `x = x.transpose(1, 2)` yaptıktan sonra döngü içinde `y = x + 1.0` gibi eleman bazlı işlemler çalıştırır ve GPU kullanımının (`Kernel Bandwidth Utilization`) `%90`'dan `%15`'e çakıldığını görür!

Bunun donanımsal sebebi **GPU Memory Coalescing (Bellek Birleştirme)** kuralıdır: Bir GPU `Warp`'ındaki 32 iş parçacığı (`Thread`), aynı saat vuruşunda bellekte yan yana (`stride = 1`) duran 32 adresi tek bir `128-Byte Cache Line` işlemiyle okuyabilir. Eğer son eksenin `stride` değeri `1` değilse (örneğin `transpose` sonrası `stride = 4096` olduysa), 32 thread belleğin 32 farklı yerine dağılır (**Uncoalesced Strided Access**) ve bellek bant genişliği 32 kat israf edilir! Bu bilgi ışığında neden özel CUDA/Triton çekirdeklerine girmeden önce son eksenin `stride == 1` olmasının hayati olduğunu açıkla.
:::

::: ozet
- Bir tensör fiziksel bellekte (`RAM / GPU HBM`) çok boyutlu bir küp olarak değil, **tek boyutlu düz bir dizi (`1D Flat Storage`)** olarak yaşar; şekil algısını yaratan şey `shape` ve `strides` üst-verisidir ($\text{offset} = \sum i_m \cdot s_m$).
- `transpose()`, `permute()`, `slice` ve `expand()` işlemleri bellekte hiçbir veriyi kopyalamaz (**`Zero-Copy View`**); yalnızca `shape` ve `strides` demetlerini $O(1)$ zamanda günceller.
- Adım kaymaları sağdan sola kümülatif boyut çarpımını bozduğunda tensör **`Non-Contiguous`** olur; `.view()` çağrısının çalışması veya GPU'da **Coalesced Memory Access** sağlanması için `.contiguous()` ile fiziksel kopya oluşturulması gerekir.
- **Broadcasting**, boyutu `1` olan eksenin adım kaymasını sanal olarak **`stride = 0`** yaparak bellekte tek bir bayt bile çoğaltmadan farklı boyutlu tensörler arasında vektörize işlem yapılmasını sağlar.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
Bir 2×3 tensoru altı hücrelik storage olarak çiz; [1,2] indeksini 1×3+2×1=5 ofsetine dönüştür. Sonra shape ve stride yer değiştirirken storage'ın aynı kaldığını göster: transpose görünümü veriyi kopyalamaz, metadata üretir. Broadcasting'de tekrar kullanılan eksenin stride'ını 0 yap; [1] ile [0] çiftinin boş [0] çıktısı verdiğini ve max kuralının bu sınırda neden yanlış olduğunu sor. Son bölümde einops desenini önce eksen permütasyonuna, sonra grup çarpımlarına ayır. Planlayıcının görünüm bayrağı yalnız yeterli bir koşuldur; gerçek kopya gereksinimini tensorun stride'ları belirler. Dinleyiciye son soru: “Shape aynıysa storage adresleri de aynı sırada mıdır?”
:::
