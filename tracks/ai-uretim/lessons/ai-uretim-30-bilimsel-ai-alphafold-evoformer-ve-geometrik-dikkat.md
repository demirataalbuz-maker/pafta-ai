---
id: ai-uretim-30
title: "Bilimsel AI İnşası (AlphaFold Mimarisi): Evoformer, Triangle Multiplicative Update ve 3D Yapı"
summary: "Nobel Ödüllü AlphaFold 2/3 ve biyoloji AI modellerinin iç mimarisi: MSA (Multiple Sequence Alignment) evrimsel ortak değişimi, Pair Representation, Triangle Multiplicative Update geometrik kısıtları ve SE(3) Invariant Point Attention (IPA)."
track: ai-uretim
order: 30
duration_minutes: 40
difficulty: ileri
xp: 320
prerequisites: [ai-uretim-29]
tags: [alphafold, evoformer, scientific-ai, structural-biology, triangle-attention, se3-invariant, protein-folding]
esleme: ai-uretim-29, ai-guvence-29
---

::: anlat
## Protein temsillerinde geometrik tutarlılık

AlphaFold 2, sequence/MSA ve pair representation üzerinde çalışan çok sayıda bileşeni birleştirir. Bu derste triangle update içindeki bir işlemi ve koordinat dönüşümlerinde değişmeyen mesafeleri hesaplayacaksın. Küçük örnekler protein katlama kabulü değildir; tek bir neural katman tüm fiziksel kısıtları kesin uygulatmaz.

2020 ve 2024 yıllarında DeepMind'ın geliştirdiği **AlphaFold 2** ve **AlphaFold 3** (John Jumper ve Demis Hassabis'e 2024 Kimya Nobel Ödülü'nü kazandıran çalışma), bilinen 200 milyondan fazla proteinin 3D atomik yapısını atom altı hassasiyetle çözerek tıp ve biyoloji tarihini değiştirdi.

Peki AlphaFold bir standart `Transformer` mıdır? **Hayır!** AlphaFold, biyolojinin evrimsel kurallarını ve 3D Öklid uzayının geometrik simetrilerini doğrudan sinir ağı katmanlarına mühürleyen **`Evoformer`** ve **`Structure Module`** mimarisine dayanır.

```
┌────────────────────────────────────────────────────────────────────────────┐
│                    ALPHAFOLD 2 / 3 EVOFORMER ÇEKİRDEK MİMARİSİ             │
├────────────────────────┬─────────────────────────┬─────────────────────────┤
│ 1. MSA TEMSİLİ         │ 2. PAIR REPRESENTATION  │ 3. STRUCTURE MODULE     │
│    (Evrimsel Kovaryans)│    (Üçgen Kısıtları)    │    (SE(3) Eşdeğişirlik) │
│ ────────────────────── │ ─────────────────────── │ ─────────────────────── │
│ • S × N amino asit     │ • N × N kalıntı çifti   │ • Öklid uzayında        │
│ • Homolog türlerde iki │ • Üçgen Eşitsizliği:    │   Dönme (SO(3)) ve      │
│   kalıntı hep BİRLİKTE │   (i, j) mesafesi,      │   Öteleme (T(3))        │
│   mutasyona uğruyorsa, │   (i, k) ve (k, j)      │   simetrilerine tam     │
│   3D uzayda birbirine  │   kenarlarıyla kısıtlı! │   bağışık Invariant     │
│   kesinlikle DEĞİYOR!  │ • Triangle Mult Update  │   Point Attention (IPA) │
└────────────────────────┴─────────────────────────┴─────────────────────────┘
```

---

### 1. MSA (Multiple Sequence Alignment) ve Pair Representation Etkileşimi

AlphaFold tek bir protein dizisine bakmaz; genetik veritabanlarını tarayarak bakterilerden memelilere kadar milyonlarca türdeki **homolog (akraba) protein dizilerini** alt alta dizer (**`Multiple Sequence Alignment - MSA`**):
- **Evrimsel Kovaryans (Covariation):** Diyelim ki 42. sıradaki amino asit pozitif yüklü `Lizin`den negatif yüklü `Aspartat`a mutasyona uğradığında; 189. sıradaki amino asit de hayatta kalabilmek için negatiften pozitife mutasyona uğruyor. Milyonlarca yıllık evrim boyunca bu iki pozisyon hep senkronize değişmişse, bu kalıntılar 1D dizilimde birbirinden 150 harf uzakta olsa bile **3D uzayda kafa kafaya gelip tuz köprüsü kurmaktadır!**
- **İki Kanallı Bilgi Akışı:**
  1. `MSA Representation` ($m_{si} \in \mathbb{R}^{S \times N \times c_m}$): $S$ farklı türdeki $N$ kalıntının temsili.
  2. `Pair Representation` ($z_{ij} \in \mathbb{R}^{N \times N \times c_z}$): $i$ ve $j$ kalıntıları arasındaki 3D uzaysal ilişki matrisi.
  3. `Outer Product Mean`: MSA kanalından tüm türler üzerinden dış çarpım ortalaması alınarak çiftler matrisine $z_{ij} \leftarrow z_{ij} + \frac{1}{S} \sum_s (m_{si} \otimes m_{sj})$ aktarılır.

---

### 2. 3D Geometriyi Sinir Ağına Kazımak: `Triangle Multiplicative Update`

Düz bir dikkat matrisi $A_{ij}$ istediği değeri alabilir. Ancak 3D fiziksel uzayda kalıntılar birer noktadır ve **Üçgen Eşitsizliğine (`Triangle Inequality`)** uymak zorundadır:
> $i$ noktası ile $k$ noktası birbirine çok yakınsa ($1\text{ Å}$) ve $k$ noktası ile $j$ noktası da birbirine çok yakınsa ($1\text{ Å}$), $i$ ile $j$ arasındaki mesafe asla $100\text{ Å}$ olamaz!

AlphaFold, bu 3 düğümlü döngüsel kısıtı sağlamak için her $i$ ve $j$ çiftini, uzaydaki **tüm olası $k$ üçüncü düğümleri üzerinden** güncelleyen **`Triangle Multiplicative Update`** katmanını geliştirmiştir:

$$z_{ij} \leftarrow z_{ij} + W_{\text{out}} \left( \sum_{k=1}^N \left( \text{proj}_A(z_{ik}) \odot \text{proj}_B(z_{jk}) \right) \right)$$

Burada $z_{ik}$ (giden kenar) ile $z_{jk}$ (gelen kenar) vektörleri eleman bazında çarpılır ($\odot$), tüm $k$ aracı kalıntıları üzerinden toplanır ve $z_{ij}$ kenarını günceller. Bu işlem, bilinen grafik sinir ağlarından farklı olarak doğrudan $O(N^3)$ geometri tutarlılığı sağlar.

```python
# Triangle Multiplicative Update (Basit 1D Kanal Gösterimi)
import math

def basit_triangle_update(z_matris):
    N = len(z_matris)
    yeni_z = [[0.0] * N for _ in range(N)]
    for i in range(N):
        for j in range(N):
            toplam = 0.0
            for k in range(N):
                toplam += z_matris[i][k] * z_matris[j][k]
            yeni_z[i][j] = round(z_matris[i][j] + toplam / math.sqrt(N), 4)
    return yeni_z

ornek = [[1.0, 0.5], [0.5, 1.0]]
print("Guncellenmis Cift:", basit_triangle_update(ornek))
```

---

### 3. SE(3) Eşdeğişirliği ve Invariant Point Attention (IPA)

Bir proteini masanın üzerinde $90^\circ$ döndürdüğünde veya 5 metre sağa kaydırdığında (**$\text{SE}(3)$ Dönüşümleri: 3D Rotations $\text{SO}(3)$ + Translations $\text{T}(3)$**), proteinin iç yapısı, enerjisi veya katlanması zerre kadar değişmez!
- Eğer standart bir sinir ağına atom koordinatlarını $(x, y, z)$ doğrudan verirsen, protein döndürüldüğünde koordinatlar değişeceği için yapay zeka onu "bambaşka bir molekül" zanneder!
- AlphaFold'un **`Structure Module`** bileşeni, her amino asit kalıntısına yerel bir koordinat çerçevesi (**Rigid Body Frame** $T_i = (R_i, \vec{t}_i)$) atar.
- **`Invariant Point Attention (IPA)`**: attention mekanizması sorguları ve anahtarları hem soyut öznitelik uzayında hem de 3D Öklid uzayındaki yerel koordinatlarda üretir. Kalıntılar arasındaki Öklid mesafeleri $\frac{w_C}{2} \|T_i^{-1} \vec{x}_j - \vec{x}_i\|^2$ dönüşümlerden etkilenmediği için, sistem küresel koordinat sisteminden tamamen bağımsız (`Globally Invariant`) çalışır.

```python norun
# Gerçek PyTorch AlphaFold Triangle Multiplicative Update Üretim Kodu
import torch
import torch.nn as nn

class TriangleMultiplicativeUpdateOutgoing(nn.Module):
    def __init__(self, c_z: int):
        super().__init__()
        self.norm = nn.LayerNorm(c_z)
        self.proj_a = nn.Linear(c_z, c_z)
        self.proj_b = nn.Linear(c_z, c_z)
        self.gate_a = nn.Linear(c_z, c_z)
        self.gate_b = nn.Linear(c_z, c_z)
        self.proj_out = nn.Linear(c_z, c_z)
        self.gate_out = nn.Linear(c_z, c_z)

    def forward(self, z: torch.Tensor, mask: torch.Tensor = None) -> torch.Tensor:
        # z: [Batch, N, N, c_z]
        z_norm = self.norm(z)
        a = self.proj_a(z_norm) * torch.sigmoid(self.gate_a(z_norm))  # [B, N, N, c_z]
        b = self.proj_b(z_norm) * torch.sigmoid(self.gate_b(z_norm))  # [B, N, N, c_z]
        if mask is not None:
            a = a * mask.unsqueeze(-1)
            b = b * mask.unsqueeze(-1)
        # i ve j ciftini tum k ara dugumleri uzerinden bilesik carp: Einstein summation
        # a_{ik} * b_{jk} -> out_{ij}
        g = torch.einsum("bikc,bjkc->bijc", a, b)
        g = self.proj_out(g) * torch.sigmoid(self.gate_out(z_norm))
        return z + g
```

**Uygulama sınırı:** Görevler Python ile küçük, denetlenebilir hesaplar yapar. `python norun` blokları PyTorch/GPU tarafını incelemek içindir; bu tezgâhta otomatik çalıştırılıp gerçek training/serving kabulü yapılmaz.

**Birincil kaynak:** [AlphaFold 2 kaynak kodu](https://github.com/google-deepmind/alphafold). Kaynak, yöntemin ayrıntıları içindir; dersteki küçük örnek ölçülmüş üretim benchmarkı değildir.
:::

::: tahmin AlphaFold Üçgen Eşitsizliği ve Geometrik Kısıtlar
3 düğümlü bir moleküler çizgede $i, j, k$ noktaları bulunmaktadır. $i$ ile $k$ arasındaki mesafe $d_{ik} = 3\text{ Å}$, $k$ ile $j$ arasındaki mesafe $d_{kj} = 4\text{ Å}$ ise, Öklid üçgen eşitsizliği gereği $i$ ile $j$ arasındaki $d_{ij}$ mesafesi teorik olarak hangi kapalı aralıkta kalmak zorundadır?

```python
d_ik = 3.0
d_kj = 4.0
min_mesafe = abs(d_ik - d_kj)
maks_mesafe = d_ik + d_kj
print(f"Izin Verilen Aralik: [{min_mesafe}, {maks_mesafe}]")
```

???

```cikti
Izin Verilen Aralik: [1.0, 7.0]
```
Üçgen eşitsizliğine göre bir kenar diğer iki kenarın farkının mutlak değerinden küçük olamaz ve toplamından büyük olamaz: $|3 - 4| \le d_{ij} \le 3 + 4$, yani $1.0\text{ Å} \le d_{ij} \le 7.0\text{ Å}$ aralığında olmak zorundadır. Geometrik üçgen eşitsizliği bu aralığı verir; neural triangle update katmanı tek başına sert bir mesafe-kısıt çözücüsü değildir.
:::

::: gorev 1 · AlphaFold Triangle Multiplicative Update (Giden/Outgoing Kenar Güncellemesi)
AlphaFold'un `Triangle Multiplicative Update (Outgoing)` mantığını simüle eden `ucgen_carpimsal_guncelle(cift_matrisi, sol_agirlik, sag_agirlik)` işlevini yaz:
1. `cift_matrisi`, $N \times N$ boyutunda float listelerin listesidir ($z_{ij}$).
2. $A$ ve $B$ matrislerini oluştur: $A_{ij} = z_{ij} \cdot \text{sol\_agirlik}$ ve $B_{ij} = z_{ij} \cdot \text{sag\_agirlik}$.
3. Her $(i, j)$ çifti için tüm $k \in [0, N-1]$ üzerinden ara düğüm etkileşimini topla:
   $$\text{guncelleme}_{ij} = \sum_{k=0}^{N-1} (A_{ik} \cdot B_{jk})$$
4. Çıktı matrisini hesapla: $\text{yeni\_z}_{ij} = \text{round}(z_{ij} + \frac{\text{guncelleme}_{ij}}{\sqrt{N}}, 4)$.
5. $N \times N$ boyutlu güncellenmiş matrisi döndür.

```starter
# KUSURLU BAŞLANGIÇ KODU: Triangle Multiplicative Update algoritmasını tamamla.
def ucgen_carpimsal_guncelle(cift_matrisi, sol_agirlik, sag_agirlik):
    return [list(satir) for satir in cift_matrisi]

print(ucgen_carpimsal_guncelle([[1.0, 0.0], [0.0, 1.0]], 1.0, 1.0))
```
```test
f = need("ucgen_carpimsal_guncelle")

# Test 1: 2x2 birim matris
# A = [[1, 0], [0, 1]], B = [[1, 0], [0, 1]]
# i=0, j=0: A[0][0]*B[0][0] + A[0][1]*B[0][1] = 1*1 + 0*0 = 1.0 -> 1.0 + 1.0/sqrt(2) = 1.0 + 0.7071 = 1.7071
# i=0, j=1: A[0][0]*B[1][0] + A[0][1]*B[1][1] = 1*0 + 0*1 = 0.0 -> 0.0 + 0.0 = 0.0
# i=1, j=0: A[1][0]*B[0][0] + A[1][1]*B[0][1] = 0*1 + 1*0 = 0.0 -> 0.0
# i=1, j=1: A[1][0]*B[1][0] + A[1][1]*B[1][1] = 0*0 + 1*1 = 1.0 -> 1.7071
r1 = f([[1.0, 0.0], [0.0, 1.0]], 1.0, 1.0)
ok(r1 == [[1.7071, 0.0], [0.0, 1.7071]], "2x2 birim matris ucgen guncellemesi dogru hesaplandi")

# Test 2: 3x3 tumu 1.0 olan matris, sol=0.5, sag=2.0
# A tumu 0.5, B tumu 2.0 -> her k icin A[i][k]*B[j][k] = 0.5 * 2.0 = 1.0
# k toplami = 3 * 1.0 = 3.0 -> guncelleme = 3.0 / sqrt(3) = 1.73205... -> 1.0 + 1.7321 = 2.7321
r2 = f([[1.0]*3 for _ in range(3)], 0.5, 2.0)
ok(r2[0][0] == 2.7321 and r2[1][2] == 2.7321, "3x3 homojen matris ucgen carpimi 2.7321 verdi")

# Test 3: Simetrik olmayan 2x2 matris
m3 = [[2.0, 1.0], [3.0, 4.0]]
# A = m3, B = m3
# i=0, j=1: A[0][0]*B[1][0] + A[0][1]*B[1][1] = 2*3 + 1*4 = 10 -> 1.0 + 10/sqrt(2) = 1.0 + 7.0711 = 8.0711
r3 = f(m3, 1.0, 1.0)
ok(r3[0][1] == 8.0711, "Simetrik olmayan 2x2 matriste capraz carpim basariyla dogrulandi")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile('import math\n\ndef ucgen_carpimsal_guncelle(cift_matrisi, sol_agirlik, sag_agirlik):\n    N = len(cift_matrisi)\n    A = [[cift_matrisi[i][j] * sol_agirlik for j in range(N)] for i in range(N)]\n    B = [[cift_matrisi[i][j] * sag_agirlik for j in range(N)] for i in range(N)]\n    yeni_z = []\n    kok_N = math.sqrt(N)\n    for i in range(N):\n        satir = []\n        for j in range(N):\n            toplam = 0.0\n            for k in range(N):\n                toplam += A[i][k] * B[j][k]\n            val = cift_matrisi[i][j] + toplam / kok_N\n            satir.append(round(val, 4))\n        yeni_z.append(satir)\n    return yeni_z', 'referans', 'exec'), _REF)
_t, _g = _ff(ucgen_carpimsal_guncelle, _REF['ucgen_carpimsal_guncelle'], ([[1.0, 0.0], [0.0, 1.0]], 1.0, 1.0), tohum=3576, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (ucgen_carpimsal_guncelle): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math

def ucgen_carpimsal_guncelle(cift_matrisi, sol_agirlik, sag_agirlik):
    N = len(cift_matrisi)
    A = [[cift_matrisi[i][j] * sol_agirlik for j in range(N)] for i in range(N)]
    B = [[cift_matrisi[i][j] * sag_agirlik for j in range(N)] for i in range(N)]
    
    yeni_z = []
    kok_N = math.sqrt(N)
    for i in range(N):
        satir = []
        for j in range(N):
            toplam = 0.0
            for k in range(N):
                toplam += A[i][k] * B[j][k]
            val = cift_matrisi[i][j] + (toplam / kok_N)
            satir.append(round(val, 4))
        yeni_z.append(satir)
    return yeni_z
```
```hint
`A[i][k]` ile `B[j][k]` değerlerini $k \in [0, N-1]$ döngüsünde topla; `cift_matrisi[i][j] + (toplam / math.sqrt(N))` sonucunu `round(..., 4)` ile yuvarla.
```
:::

::: gorev 2 · 3D Atom Koordinatlarından SE(3) Değişmez (Rotation/Translation Invariant) Mesafe ve RMSD Hesabı
Biyolojik yapılarda iki konformasyonun benzerliği, küresel koordinatlardan bağımsız olarak **Kalıntı Mesafeleri Matrisi (`Distance Matrix`)** ve **Root Mean Square Deviation (RMSD)** ile ölçülür.

`se3_degismez_rmsd(koordinatlar_a, koordinatlar_b)` işlevini yaz:
1. Girdiler $N$ adet 3D atom koordinatını içeren listelerdir: `koordinatlar_a = [[x1, y1, z1], [x2, y2, z2], ...]`.
2. Her iki yapı için $N \times N$ boyutlu Öklid mesafe matrislerini ($D^A$ ve $D^B$) hesapla:
   $$D_{ij} = \sqrt{(x_i - x_j)^2 + (y_i - y_j)^2 + (z_i - z_j)^2}$$
3. İki mesafe matrisi arasındaki mesafe farklarının karekök ortalamasını (**`Distance RMSD / dRMSD`**) hesapla:
   $$\text{dRMSD} = \sqrt{\frac{1}{N^2} \sum_{i=0}^{N-1} \sum_{j=0}^{N-1} (D_{ij}^A - D_{ij}^B)^2}$$
4. Sözlük döndür:
   - `"mesafe_matrisi_a"`: $N \times N$ liste (tüm değerler `round(..., 4)` ile yuvarlanmış)
   - `"drmsd"`: `round(drmsd_degeri, 4)`
   - `"ozdes_yapi_mi"`: `bool(drmsd < 0.001)` (Öteleme veya dönme olsa dahi iç yapı aynıysa `True` olmalı!)

```starter
# KUSURLU BAŞLANGIÇ KODU: Öklid mesafe matrislerini ve dRMSD metriğini tamamla.
def se3_degismez_rmsd(koordinatlar_a, koordinatlar_b):
    return {
        "mesafe_matrisi_a": [],
        "drmsd": 0.0,
        "ozdes_yapi_mi": False
    }

print(se3_degismez_rmsd([[0,0,0], [1,0,0]], [[0,0,0], [0,1,0]]))
```
```test
f = need("se3_degismez_rmsd")

# Test 1: 2 atom: [0,0,0] ve [3,4,0] -> aralarindaki mesafe 5.0
# Yapi B: 90 derece dondurulmus ve ötelenmis hali: [10, 10, 0] ve [10, 15, 0] -> mesafe yine 5.0!
a1 = [[0.0, 0.0, 0.0], [3.0, 4.0, 0.0]]
b1 = [[10.0, 10.0, 0.0], [10.0, 10.0, 5.0]]
r1 = f(a1, b1)
ok(r1["mesafe_matrisi_a"] == [[0.0, 5.0], [5.0, 0.0]], "Mesafe matrisi A dogru hesaplandi")
ok(r1["drmsd"] == 0.0 and r1["ozdes_yapi_mi"] is True, "Rotasyon/öteleme altinda dRMSD=0.0 ve ozdes_yapi_mi=True")

# Test 2: 3 atom: Ucgen yapisi bozulmus
a2 = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
b2 = [[0.0, 0.0, 0.0], [2.0, 0.0, 0.0], [0.0, 2.0, 0.0]]
r2 = f(a2, b2)
eq(r2["drmsd"], 0.9428, "N=3 için dRMSD paydası N*N=9 olarak hesaplanır")
ok(r2["drmsd"] > 0.5 and r2["ozdes_yapi_mi"] is False, "Farkli konformasyonlar icin dRMSD pozitif ve ozdes_yapi_mi=False")

# Dört matris hücresinin ikisi değişir. Aralık d ise dRMSD = sqrt(2*d*d/4).
# Bu aralık, Python float hesabında yuvarlama öncesi tam 0.001 üretir.
_esik_aralik = 0.001414213562373095
_cakisan = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]
_esik = f(_cakisan, [[0.0, 0.0, 0.0], [_esik_aralik, 0.0, 0.0]])
eq(_esik["drmsd"], 0.001, "Tam eşikte raporlanan dRMSD")
ok(_esik["ozdes_yapi_mi"] is False, "Tam eşikte katı küçüktür koşulu sağlanmaz")
_alt = f(_cakisan, [[0.0, 0.0, 0.0], [0.0014, 0.0, 0.0]])
eq(_alt["drmsd"], 0.001, "Eşik altındaki değer de ekranda 0.001'e yuvarlanır")
ok(_alt["ozdes_yapi_mi"] is True, "Karar yuvarlanmamış dRMSD ile verilir")


# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef se3_degismez_rmsd(koordinatlar_a, koordinatlar_b):\n    N = len(koordinatlar_a)\n\n    def mesafe_matrisi(k):\n        m = []\n        for i in range(N):\n            satir = []\n            for j in range(N):\n                dx = k[i][0] - k[j][0]\n                dy = k[i][1] - k[j][1]\n                dz = k[i][2] - k[j][2]\n                dist = math.sqrt(dx * dx + dy * dy + dz * dz)\n                satir.append(dist)\n            m.append(satir)\n        return m\n    DA = mesafe_matrisi(koordinatlar_a)\n    DB = mesafe_matrisi(koordinatlar_b)\n    toplam_fark_kare = 0.0\n    for i in range(N):\n        for j in range(N):\n            fark = DA[i][j] - DB[i][j]\n            toplam_fark_kare += fark * fark\n    drmsd = math.sqrt(toplam_fark_kare / (N * N))\n    da_yuvarli = [[round(DA[i][j], 4) for j in range(N)] for i in range(N)]\n    return {'mesafe_matrisi_a': da_yuvarli, 'drmsd': round(drmsd, 4), 'ozdes_yapi_mi': bool(drmsd < 0.001)}", 'referans', 'exec'), _REF)
_t, _g = _ff(se3_degismez_rmsd, _REF['se3_degismez_rmsd'], ([[0, 0, 0], [1, 0, 0]], [[0, 0, 0], [0, 1, 0]]), tohum=2804, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (se3_degismez_rmsd): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math

def se3_degismez_rmsd(koordinatlar_a, koordinatlar_b):
    N = len(koordinatlar_a)
    def mesafe_matrisi(k):
        m = []
        for i in range(N):
            satir = []
            for j in range(N):
                dx = k[i][0] - k[j][0]
                dy = k[i][1] - k[j][1]
                dz = k[i][2] - k[j][2]
                dist = math.sqrt(dx * dx + dy * dy + dz * dz)
                satir.append(dist)
            m.append(satir)
        return m

    DA = mesafe_matrisi(koordinatlar_a)
    DB = mesafe_matrisi(koordinatlar_b)

    toplam_fark_kare = 0.0
    for i in range(N):
        for j in range(N):
            fark = DA[i][j] - DB[i][j]
            toplam_fark_kare += fark * fark

    drmsd = math.sqrt(toplam_fark_kare / (N * N))
    da_yuvarli = [[round(DA[i][j], 4) for j in range(N)] for i in range(N)]

    return {
        "mesafe_matrisi_a": da_yuvarli,
        "drmsd": round(drmsd, 4),
        "ozdes_yapi_mi": bool(drmsd < 0.001)
    }
```
```hint
Her $i, j$ çifti için $\sqrt{(x_i-x_j)^2 + (y_i-y_j)^2 + (z_i-z_j)^2}$ Öklid mesafesini hesapla; $D^A$ ve $D^B$ matrisleri arasındaki fark karelerinin ortalamasının karekökünü al.
```
:::

::: gorev 3 · Evoformer MSA Satır Dikkati (Pair Bias'lı, Kapılı)
Evoformer'da MSA'nın her satırı (bir dizi) kendi kalıntıları arasında dikkat uygular; dikkat skorlarına **pair temsili**nden gelen bir önyargı eklenir ve çıktı bir sigmoid **kapı** ile çarpılır. Böylece yapı bilgisi (pair) dizilim bilgisini (MSA) yönlendirir. Tek başlı bir sürüm yaz: `msa_satir_dikkati(msa_satiri, pair_bias, Wq, Wk, Wv, Wg)`.

**Girdiler:** `msa_satiri`: $L \times c$; `pair_bias`: $L \times L$; `Wq, Wk, Wv, Wg`: $c \times h$ matrisler (liste listesi).

**Hesap:** $q_i = x_i W_q$, $k_j = x_j W_k$, $v_j = x_j W_v$, $g_i = \sigma(x_i W_g)$ (öğe öğe);
$$\ell_{ij} = \frac{q_i \cdot k_j}{\sqrt{h}} + b_{ij}, \qquad a_{ij} = \text{softmax}_j(\ell_{ij}), \qquad o_i = g_i \odot \sum_j a_{ij} v_j$$
Softmax'ı satır maksimumunu çıkararak kararlı hesapla.

Çıktı: `{"dikkat": L×L, "cikti": L×h}` (öğeler `round(·, 6)`). Boyutlar uyuşmazsa (boş, düzensiz ya da yanlış boyutlu matris) `ValueError`.

```starter
def msa_satir_dikkati(msa_satiri, pair_bias, Wq, Wk, Wv, Wg):
    # KUSURLU BAŞLANGIÇ: pair bias ve kapıyı yok sayıp düzgün dağılımlı dikkat veriyor
    L, h = len(msa_satiri), len(Wv[0])
    a = [[1.0 / L] * L for _ in range(L)]
    v = [[sum(x * w[k] for x, w in zip(msa_satiri[j], Wv)) for k in range(h)] for j in range(L)]
    o = [[sum(a[i][j] * v[j][k] for j in range(L)) for k in range(h)] for i in range(L)]
    return {"dikkat": a, "cikti": o}

print(msa_satir_dikkati([[1.0, 0.0], [0.0, 1.0]], [[0.0, 0.0], [0.0, 0.0]], [[1.0], [0.0]], [[1.0], [0.0]], [[1.0], [2.0]], [[0.0], [0.0]]))
```

```test
import math
fn = need("msa_satir_dikkati")
x = [[1.0, 0.0], [0.0, 1.0]]
r = fn(x, [[0.0, 0.0], [0.0, 0.0]], [[1.0], [0.0]], [[1.0], [0.0]], [[1.0], [2.0]], [[0.0], [0.0]])
s = math.e / (math.e + 1)
eq(r["dikkat"], [[round(s, 6), round(1 - s, 6)], [0.5, 0.5]], "satır 0 skorları [1, 0], satır 1 [0, 0]")
eq(r["cikti"], [[round(0.5 * (s + 2 * (1 - s)), 6)], [0.75]], "v = [1, 2]; kapı σ(0) = 0.5")
r2 = fn(x, [[0.0, -1e9], [0.0, 0.0]], [[1.0], [0.0]], [[1.0], [0.0]], [[1.0], [2.0]], [[0.0], [0.0]])
eq(r2["dikkat"][0], [1.0, 0.0], "çok negatif pair bias bağlantıyı keser")
eq(r2["cikti"][0], [0.5], "yalnız v0 = 1, kapı 0.5")
r3 = fn(x, [[0.0, 0.0], [0.0, 0.0]], [[1.0, 1.0], [0.0, 0.0]], [[1.0, 1.0], [0.0, 0.0]], [[1.0, 0.0], [0.0, 1.0]], [[0.0, 0.0], [0.0, 0.0]])
z = math.exp(2 / math.sqrt(2))
eq(r3["dikkat"][0], [round(z / (z + 1), 6), round(1 / (z + 1), 6)], "skor q·k = 2, √h = √2 ile ölçeklenir")
eq(r3["cikti"][1], [0.25, 0.25], "q1 = 0: düzgün dikkat, v ortalaması [0.5, 0.5] × 0.5")
r4 = fn(x, [[0.0, 0.0], [0.0, 0.0]], [[1.0], [0.0]], [[1.0], [0.0]], [[1.0], [2.0]], [[100.0], [0.0]])
eq(r4["cikti"][0], [round(s + 2 * (1 - s), 6)], "kapı σ(100) ≈ 1: çıktı açık")
raises(ValueError, fn, [], [], [[1.0]], [[1.0]], [[1.0]], [[1.0]])
raises(ValueError, fn, x, [[0.0, 0.0]], [[1.0], [0.0]], [[1.0], [0.0]], [[1.0], [2.0]], [[0.0], [0.0]])
raises(ValueError, fn, x, [[0.0, 0.0], [0.0, 0.0]], [[1.0]], [[1.0], [0.0]], [[1.0], [2.0]], [[0.0], [0.0]])
raises(ValueError, fn, [[1.0, 0.0], [0.0]], [[0.0, 0.0], [0.0, 0.0]], [[1.0], [0.0]], [[1.0], [0.0]], [[1.0], [2.0]], [[0.0], [0.0]])
raises(ValueError, fn, "bad", [[0.0]], [[1.0]], [[1.0]], [[1.0]], [[1.0]])
raises(ValueError, fn, [[]], [[0.0]], [[1.0]], [[1.0]], [[1.0]], [[1.0]])
raises(ValueError, fn, ["a"], [[0.0]], [[1.0]], [[1.0]], [[1.0]], [[1.0]])
raises(ValueError, fn, ([1.0],), [[0.0]], [[1.0]], [[1.0]], [[1.0]], [[1.0]])
raises(ValueError, fn, [[1.0]], [[0.0]], [[]], [[]], [[]], [[]])
raises(ValueError, fn, x, [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]], [[1.0], [0.0]], [[1.0], [0.0]], [[1.0], [2.0]], [[0.0], [0.0]])
eq(fn(x, [[1000.0, 1000.0], [1000.0, 1000.0]], [[1.0], [0.0]], [[1.0], [0.0]], [[1.0], [2.0]], [[0.0], [0.0]])["dikkat"][1], [0.5, 0.5], "büyük skorlarda taşma korumalı softmax")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef _matris(m, satir=None, sutun=None):\n    if not isinstance(m, list) or not m or (not all((isinstance(r, list) and r for r in m))):\n        raise ValueError('matris boş olmayan liste listesi olmalı')\n    n = len(m[0])\n    if any((len(r) != n for r in m)) or (satir is not None and len(m) != satir) or (sutun is not None and n != sutun):\n        raise ValueError('matris boyutları uyuşmuyor')\n    return (len(m), n)\n\ndef msa_satir_dikkati(msa_satiri, pair_bias, Wq, Wk, Wv, Wg):\n    L, c = _matris(msa_satiri)\n    _matris(pair_bias, L, L)\n    _, h = _matris(Wq, c)\n    for W in (Wk, Wv, Wg):\n        _matris(W, c, h)\n\n    def carp(x, W):\n        return [sum((x[t] * W[t][k] for t in range(c))) for k in range(h)]\n    q = [carp(x, Wq) for x in msa_satiri]\n    k = [carp(x, Wk) for x in msa_satiri]\n    v = [carp(x, Wv) for x in msa_satiri]\n    g = [[1.0 / (1.0 + math.exp(-z)) for z in carp(x, Wg)] for x in msa_satiri]\n    dikkat, cikti = ([], [])\n    for i in range(L):\n        skor = [sum((q[i][t] * k[j][t] for t in range(h))) / math.sqrt(h) + pair_bias[i][j] for j in range(L)]\n        m = max(skor)\n        e = [math.exp(s - m) for s in skor]\n        top = sum(e)\n        a = [x / top for x in e]\n        o = [g[i][t] * sum((a[j] * v[j][t] for j in range(L))) for t in range(h)]\n        dikkat.append([round(x, 6) for x in a])\n        cikti.append([round(x, 6) for x in o])\n    return {'dikkat': dikkat, 'cikti': cikti}", 'referans', 'exec'), _REF)
_t, _g = _ff(msa_satir_dikkati, _REF['msa_satir_dikkati'], ([[1.0, 0.0], [0.0, 1.0]], [[0.0, 0.0], [0.0, 0.0]], [[1.0], [0.0]], [[1.0], [0.0]], [[1.0], [2.0]], [[0.0], [0.0]]), tohum=2848, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (msa_satir_dikkati): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
import math

def _matris(m, satir=None, sutun=None):
    if not isinstance(m, list) or not m or not all(isinstance(r, list) and r for r in m):
        raise ValueError("matris boş olmayan liste listesi olmalı")
    n = len(m[0])
    if any(len(r) != n for r in m) or (satir is not None and len(m) != satir) or (sutun is not None and n != sutun):
        raise ValueError("matris boyutları uyuşmuyor")
    return len(m), n

def msa_satir_dikkati(msa_satiri, pair_bias, Wq, Wk, Wv, Wg):
    L, c = _matris(msa_satiri)
    _matris(pair_bias, L, L)
    _, h = _matris(Wq, c)
    for W in (Wk, Wv, Wg):
        _matris(W, c, h)

    def carp(x, W):
        return [sum(x[t] * W[t][k] for t in range(c)) for k in range(h)]

    q = [carp(x, Wq) for x in msa_satiri]
    k = [carp(x, Wk) for x in msa_satiri]
    v = [carp(x, Wv) for x in msa_satiri]
    g = [[1.0 / (1.0 + math.exp(-z)) for z in carp(x, Wg)] for x in msa_satiri]
    dikkat, cikti = [], []
    for i in range(L):
        skor = [sum(q[i][t] * k[j][t] for t in range(h)) / math.sqrt(h) + pair_bias[i][j] for j in range(L)]
        m = max(skor)
        e = [math.exp(s - m) for s in skor]
        top = sum(e)
        a = [x / top for x in e]
        o = [g[i][t] * sum(a[j] * v[j][t] for j in range(L)) for t in range(h)]
        dikkat.append([round(x, 6) for x in a])
        cikti.append([round(x, 6) for x in o])
    return {"dikkat": dikkat, "cikti": cikti}
```

```hint
Önce q, k, v ve kapı vektörlerini her kalıntı için hesapla; her satırda skorlara pair bias ekleyip maksimumu çıkararak softmax al.
```
:::

::: gorev 4 · Outer Product Mean: MSA'dan Pair Temsiline Bilgi Akışı
Evoformer'da bilgi iki yönde akar: pair temsili MSA dikkatine önyargı verir (görev 3), MSA da pair temsilini **outer product mean** ile günceller. İki konumun MSA'daki dizilerde **birlikte değişmesi** (ko-varyasyon) pair temsilinde iz bırakır: kalıntı $i$ ve $j$ birlikte değişiyorsa ortalaması büyük olur. `outer_product_mean(msa, Wa, Wb)` işlevini yaz.

**Girdiler:** `msa`: $S \times L \times c$ (S dizi, her biri L kalıntı, her kalıntı c boyutlu vektör); `Wa`, `Wb`: $c \times p$.

**Hesap:** $a_{si} = x_{si} W_a$, $b_{sj} = x_{sj} W_b$ ($p$ boyutlu);
$$\text{opm}_{ij} = \text{vec}\Big(\frac{1}{S}\sum_{s} a_{si} \otimes b_{sj}\Big)$$
Dış çarpım $p \times p$'lik matristir; satır satır düzleştir (önce $u$, sonra $v$: öğe $u \cdot p + v$, değeri $a_{si}[u] \cdot b_{sj}[v]$).

Çıktı: `{"opm": L × L × p²}` (öğeler `round(·, 6)`). MSA boşsa, dizilerin uzunlukları ya da vektör boyutları farklıysa, öğeler sonlu sayı değilse (`bool` dahil) ya da `Wa`/`Wb` $c \times p$ değilse (iki p eşit olmalı) `ValueError` ver.

```starter
def outer_product_mean(msa, Wa, Wb):
    # KUSURLU BAŞLANGIÇ: dizilerin ortalamasını önce alıp sonra dış çarpım yapıyor (ko-varyasyonu kaybeder)
    S, L, c, p = len(msa), len(msa[0]), len(msa[0][0]), len(Wa[0])
    ort = [[sum(msa[s][i][t] for s in range(S)) / S for t in range(c)] for i in range(L)]
    a = [[sum(x[t] * Wa[t][k] for t in range(c)) for k in range(p)] for x in ort]
    b = [[sum(x[t] * Wb[t][k] for t in range(c)) for k in range(p)] for x in ort]
    return {"opm": [[[round(a[i][u] * b[j][v], 6) for u in range(p) for v in range(p)] for j in range(L)] for i in range(L)]}

print(outer_product_mean([[[1.0], [2.0]], [[3.0], [0.0]]], [[1.0]], [[1.0]]))
```

```test
fn = need("outer_product_mean")
eq(fn([[[1.0], [2.0]], [[3.0], [0.0]]], [[1.0]], [[1.0]]), {"opm": [[[5.0], [1.0]], [[1.0], [2.0]]]}, "x[:,0] = [1, 3], x[:,1] = [2, 0]: opm_00 = (1+9)/2, opm_01 = (2+0)/2, opm_11 = (4+0)/2")
eq(fn([[[1.0], [2.0]], [[3.0], [0.0]]], [[1.0, 0.0]], [[0.0, 1.0]])["opm"][0][0], [0.0, 5.0, 0.0, 0.0], "p = 2: a = [x, 0], b = [0, x]; yalnız (u=0, v=1) öğesi dolu")
eq(fn([[[1.0], [2.0]], [[3.0], [0.0]]], [[1.0, 0.0]], [[0.0, 1.0]])["opm"][1][0], [0.0, 1.0, 0.0, 0.0], "opm_10 = (2·1 + 0·3)/2")
eq(fn([[[1.0, 0.0], [1.0, 0.0]], [[0.0, 1.0], [0.0, 1.0]], [[1.0, 0.0], [0.0, 1.0]]], [[1.0], [-1.0]], [[1.0], [-1.0]]),
   {"opm": [[[1.0], [0.333333]], [[0.333333], [1.0]]]}, "iki konum 3 dizinin 2'sinde birlikte değişiyor: ko-varyasyon 1/3")
eq(fn([[[2.0]]], [[1.0]], [[3.0]]), {"opm": [[[12.0]]]}, "tek dizi, tek kalıntı: a = 2·1, b = 2·3, a·b = 12")
raises(ValueError, fn, [], [[1.0]], [[1.0]])
raises(ValueError, fn, [[[1.0], [2.0]], [[3.0]]], [[1.0]], [[1.0]])
raises(ValueError, fn, [[[1.0, 0.0], [2.0]]], [[1.0], [0.0]], [[1.0], [0.0]])
raises(ValueError, fn, [[[1.0], [2.0]]], [[1.0, 0.0]], [[1.0]])
raises(ValueError, fn, [[[1.0], [2.0]]], [[1.0], [0.0]], [[1.0], [0.0]])
raises(ValueError, fn, [[[True], [2.0]]], [[1.0]], [[1.0]])
raises(ValueError, fn, [[[float("nan")], [2.0]]], [[1.0]], [[1.0]])
raises(ValueError, fn, [[], []], [[1.0]], [[1.0]])
raises(ValueError, fn, [[[]]], [[1.0]], [[1.0]])
raises(ValueError, fn, [[[]]], [], [])
raises(ValueError, fn, [[["a"]]], [[1.0]], [[1.0]])
raises(ValueError, fn, [[[1.0]]], [[]], [[]])
raises(ValueError, fn, [[[1.0, 2.0]]], [[1.0, 0.0], [1.0]], [[1.0, 0.0], [1.0, 0.0]])

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef _msa(msa):\n    if not isinstance(msa, list) or not msa or (not all((isinstance(r, list) and r for r in msa))):\n        raise ValueError('msa boş olmayan S × L × c liste olmalı')\n    L = len(msa[0])\n    c = None\n    for r in msa:\n        if len(r) != L:\n            raise ValueError('bütün diziler aynı uzunlukta olmalı')\n        for x in r:\n            if not isinstance(x, list) or not x or (c is not None and len(x) != c):\n                raise ValueError('kalıntı vektörleri aynı boyutta olmalı')\n            c = len(x)\n            for v in x:\n                if isinstance(v, bool) or not isinstance(v, (int, float)) or (not math.isfinite(v)):\n                    raise ValueError('sonlu sayı gerekli')\n    return (len(msa), L, c)\n\ndef _agirlik(W, c, p=None):\n    if not isinstance(W, list) or len(W) != c or (not all((isinstance(r, list) and r for r in W))):\n        raise ValueError('ağırlık c × p olmalı')\n    n = len(W[0])\n    if any((len(r) != n for r in W)) or (p is not None and n != p):\n        raise ValueError('ağırlık boyutları uyuşmuyor')\n    return n\n\ndef outer_product_mean(msa, Wa, Wb):\n    S, L, c = _msa(msa)\n    p = _agirlik(Wa, c)\n    _agirlik(Wb, c, p)\n\n    def carp(x, W):\n        return [sum((x[t] * W[t][k] for t in range(c))) for k in range(p)]\n    a = [[carp(x, Wa) for x in r] for r in msa]\n    b = [[carp(x, Wb) for x in r] for r in msa]\n    out = []\n    for i in range(L):\n        satir = []\n        for j in range(L):\n            satir.append([round(sum((a[s][i][u] * b[s][j][v] for s in range(S))) / S, 6) for u in range(p) for v in range(p)])\n        out.append(satir)\n    return {'opm': out}", 'referans', 'exec'), _REF)
_t, _g = _ff(outer_product_mean, _REF['outer_product_mean'], ([[[1.0], [2.0]], [[3.0], [0.0]]], [[1.0]], [[1.0]]), tohum=2988, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (outer_product_mean): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
import math

def _msa(msa):
    if not isinstance(msa, list) or not msa or not all(isinstance(r, list) and r for r in msa):
        raise ValueError("msa boş olmayan S × L × c liste olmalı")
    L = len(msa[0])
    c = None
    for r in msa:
        if len(r) != L:
            raise ValueError("bütün diziler aynı uzunlukta olmalı")
        for x in r:
            if not isinstance(x, list) or not x or (c is not None and len(x) != c):
                raise ValueError("kalıntı vektörleri aynı boyutta olmalı")
            c = len(x)
            for v in x:
                if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
                    raise ValueError("sonlu sayı gerekli")
    return len(msa), L, c

def _agirlik(W, c, p=None):
    if not isinstance(W, list) or len(W) != c or not all(isinstance(r, list) and r for r in W):
        raise ValueError("ağırlık c × p olmalı")
    n = len(W[0])
    if any(len(r) != n for r in W) or (p is not None and n != p):
        raise ValueError("ağırlık boyutları uyuşmuyor")
    return n

def outer_product_mean(msa, Wa, Wb):
    S, L, c = _msa(msa)
    p = _agirlik(Wa, c)
    _agirlik(Wb, c, p)

    def carp(x, W):
        return [sum(x[t] * W[t][k] for t in range(c)) for k in range(p)]
    a = [[carp(x, Wa) for x in r] for r in msa]
    b = [[carp(x, Wb) for x in r] for r in msa]
    out = []
    for i in range(L):
        satir = []
        for j in range(L):
            satir.append([round(sum(a[s][i][u] * b[s][j][v] for s in range(S)) / S, 6) for u in range(p) for v in range(p)])
        out.append(satir)
    return {"opm": out}
```

```hint
Ortalamayı dış çarpımdan **sonra** al: önce her dizi için $a_{si} \otimes b_{sj}$, sonra diziler üzerinden ortalama. Tersini yaparsan ko-varyasyon kaybolur.
```
:::

::: gorev 5 · Evoformer MSA Sütun Dikkati (Diziler Arası, Kapılı)
Satır dikkati (görev 3) bir dizinin kalıntıları arasında çalışır. **Sütun dikkati** aynı kalıntı konumunu farklı dizilerde karşılaştırır: her sütun $j$ için o sütundaki $S$ vektör $x_{1j}, \dots, x_{Sj}$ arasında dikkat uygulanır (pair bias yoktur, kapı vardır). Sütunlar birbirinden bağımsızdır. `msa_sutun_dikkati(msa, Wq, Wk, Wv, Wg)` işlevini yaz.

**Girdiler:** `msa`: $S \times L \times c$; `Wq, Wk, Wv, Wg`: $c \times h$.

**Hesap:** her sütun $j$ ve dizi $s$ için $q_{s} = x_{sj} W_q$, $k_r$, $v_r$ aynı biçimde, $g_s = \sigma(x_{sj} W_g)$;
$$a^{(j)}_{sr} = \text{softmax}_r\Big(\frac{q_s \cdot k_r}{\sqrt{h}}\Big), \qquad o_{sj} = g_s \odot \sum_r a^{(j)}_{sr} v_r$$

Çıktı: `{"dikkat": L × S × S, "cikti": S × L × h}` (öğeler `round(·, 6)`, softmax satır maksimumu çıkarılarak). Boyutlar uyuşmazsa ya da öğeler sonlu sayı değilse `ValueError`.

```starter
def msa_sutun_dikkati(msa, Wq, Wk, Wv, Wg):
    # KUSURLU BAŞLANGIÇ: dikkati diziler yerine bir dizinin kalıntıları arasında kuruyor (satır dikkati) ve kapıyı unutuyor
    S, L, h = len(msa), len(msa[0]), len(Wv[0])
    v = [[[sum(x[t] * Wv[t][k] for t in range(len(x))) for k in range(h)] for x in r] for r in msa]
    return {"dikkat": [[[1.0 / S] * S for _ in range(S)] for _ in range(L)],
            "cikti": [[[round(sum(v[s][jj][k] for jj in range(L)) / L, 6) for k in range(h)] for j in range(L)] for s in range(S)]}

print(msa_sutun_dikkati([[[1.0, 0.0]], [[0.0, 1.0]]], [[1.0], [0.0]], [[1.0], [0.0]], [[1.0], [2.0]], [[0.0], [0.0]]))
```

```test
import math
fn = need("msa_sutun_dikkati")
s = math.e / (math.e + 1)
r = fn([[[1.0, 0.0]], [[0.0, 1.0]]], [[1.0], [0.0]], [[1.0], [0.0]], [[1.0], [2.0]], [[0.0], [0.0]])
eq(r["dikkat"], [[[round(s, 6), round(1 - s, 6)], [0.5, 0.5]]], "tek sütun: görev 3'teki satır dikkatinin aynısı, bu kez diziler arasında")
eq(r["cikti"], [[[round(0.5 * (s + 2 * (1 - s)), 6)]], [[0.75]]], "v = [1, 2]; kapı σ(0) = 0.5")
r2 = fn([[[1.0, 0.0], [0.0, 1.0]], [[0.0, 1.0], [1.0, 0.0]]], [[1.0], [0.0]], [[1.0], [0.0]], [[1.0], [2.0]], [[0.0], [0.0]])
eq(r2["dikkat"][1], [[0.5, 0.5], [round(1 - s, 6), round(s, 6)]], "ikinci sütunda diziler yer değiştirmiş: dikkat de değişir")
eq(r2["cikti"], [[[round(0.5 * (s + 2 * (1 - s)), 6)], [0.75]], [[0.75], [round(0.5 * (s + 2 * (1 - s)), 6)]]], "sütunlar bağımsız; çıktı S × L × h")
r3 = fn([[[1.0, 0.0]], [[0.0, 1.0]]], [[1.0], [0.0]], [[1.0], [0.0]], [[1.0], [2.0]], [[100.0], [0.0]])
eq(r3["cikti"][0][0], [round(s + 2 * (1 - s), 6)], "kapı σ(100) ≈ 1: çıktı açık")
eq(fn([[[3.0]]], [[1.0]], [[1.0]], [[2.0]], [[0.0]]), {"dikkat": [[[1.0]]], "cikti": [[[3.0]]]}, "tek dizi: dikkat 1, çıktı 0.5 · v")
raises(ValueError, fn, [], [[1.0]], [[1.0]], [[1.0]], [[1.0]])
raises(ValueError, fn, [[[1.0], [2.0]], [[3.0]]], [[1.0]], [[1.0]], [[1.0]], [[1.0]])
raises(ValueError, fn, [[[1.0, 0.0]]], [[1.0]], [[1.0], [0.0]], [[1.0], [0.0]], [[1.0], [0.0]])
raises(ValueError, fn, [[[1.0, 0.0]]], [[1.0], [0.0]], [[1.0, 0.0], [0.0, 1.0]], [[1.0], [0.0]], [[1.0], [0.0]])
raises(ValueError, fn, [[[True, 0.0]]], [[1.0], [0.0]], [[1.0], [0.0]], [[1.0], [0.0]], [[1.0], [0.0]])
raises(ValueError, fn, [[[float("nan"), 0.0]]], [[1.0], [0.0]], [[1.0], [0.0]], [[1.0], [0.0]], [[1.0], [0.0]])
raises(ValueError, fn, [[], []], [[1.0]], [[1.0]], [[1.0]], [[1.0]])
raises(ValueError, fn, [[[]]], [[1.0]], [[1.0]], [[1.0]], [[1.0]])
raises(ValueError, fn, [[[]]], [], [], [], [])
raises(ValueError, fn, [[["a"]]], [[1.0]], [[1.0]], [[1.0]], [[1.0]])
raises(ValueError, fn, [[[1.0]]], [[]], [[]], [[]], [[]])
raises(ValueError, fn, [[[1.0, 2.0]]], [[1.0, 0.0], [1.0]], [[1.0, 0.0], [1.0, 0.0]], [[1.0, 0.0], [1.0, 0.0]], [[1.0, 0.0], [1.0, 0.0]])
_z5 = math.exp(2 / math.sqrt(2))
eq(fn([[[1.0, 0.0]], [[0.0, 1.0]]], [[1.0, 1.0], [0.0, 0.0]], [[1.0, 1.0], [0.0, 0.0]], [[1.0, 0.0], [0.0, 1.0]], [[0.0, 0.0], [0.0, 0.0]])["dikkat"][0][0], [round(_z5 / (_z5 + 1), 6), round(1 / (_z5 + 1), 6)], "h=2 için sqrt(h) ölçeklemesi")
eq(fn([[[1000.0]], [[1000.0]]], [[1.0]], [[1.0]], [[1.0]], [[0.0]])["dikkat"][0][0], [0.5, 0.5], "büyük skorlarda taşma korumalı sütun softmax")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef _msa(msa):\n    if not isinstance(msa, list) or not msa or (not all((isinstance(r, list) and r for r in msa))):\n        raise ValueError('msa boş olmayan S × L × c liste olmalı')\n    L = len(msa[0])\n    c = None\n    for r in msa:\n        if len(r) != L:\n            raise ValueError('bütün diziler aynı uzunlukta olmalı')\n        for x in r:\n            if not isinstance(x, list) or not x or (c is not None and len(x) != c):\n                raise ValueError('kalıntı vektörleri aynı boyutta olmalı')\n            c = len(x)\n            for v in x:\n                if isinstance(v, bool) or not isinstance(v, (int, float)) or (not math.isfinite(v)):\n                    raise ValueError('sonlu sayı gerekli')\n    return (len(msa), L, c)\n\ndef _agirlik(W, c, p=None):\n    if not isinstance(W, list) or len(W) != c or (not all((isinstance(r, list) and r for r in W))):\n        raise ValueError('ağırlık c × p olmalı')\n    n = len(W[0])\n    if any((len(r) != n for r in W)) or (p is not None and n != p):\n        raise ValueError('ağırlık boyutları uyuşmuyor')\n    return n\n\ndef msa_sutun_dikkati(msa, Wq, Wk, Wv, Wg):\n    S, L, c = _msa(msa)\n    h = _agirlik(Wq, c)\n    for W in (Wk, Wv, Wg):\n        _agirlik(W, c, h)\n\n    def carp(x, W):\n        return [sum((x[t] * W[t][k] for t in range(c))) for k in range(h)]\n    dikkat = []\n    cikti = [[None] * L for _ in range(S)]\n    for j in range(L):\n        X = [msa[s][j] for s in range(S)]\n        q, k, v = ([carp(x, Wq) for x in X], [carp(x, Wk) for x in X], [carp(x, Wv) for x in X])\n        g = [[1.0 / (1.0 + math.exp(-z)) for z in carp(x, Wg)] for x in X]\n        sutun = []\n        for s in range(S):\n            skor = [sum((q[s][t] * k[r][t] for t in range(h))) / math.sqrt(h) for r in range(S)]\n            m = max(skor)\n            e = [math.exp(x - m) for x in skor]\n            top = sum(e)\n            a = [x / top for x in e]\n            sutun.append([round(x, 6) for x in a])\n            cikti[s][j] = [round(g[s][t] * sum((a[r] * v[r][t] for r in range(S))), 6) for t in range(h)]\n        dikkat.append(sutun)\n    return {'dikkat': dikkat, 'cikti': cikti}", 'referans', 'exec'), _REF)
_t, _g = _ff(msa_sutun_dikkati, _REF['msa_sutun_dikkati'], ([[[1.0, 0.0]], [[0.0, 1.0]]], [[1.0], [0.0]], [[1.0], [0.0]], [[1.0], [2.0]], [[0.0], [0.0]]), tohum=2876, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (msa_sutun_dikkati): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
import math

def _msa(msa):
    if not isinstance(msa, list) or not msa or not all(isinstance(r, list) and r for r in msa):
        raise ValueError("msa boş olmayan S × L × c liste olmalı")
    L = len(msa[0])
    c = None
    for r in msa:
        if len(r) != L:
            raise ValueError("bütün diziler aynı uzunlukta olmalı")
        for x in r:
            if not isinstance(x, list) or not x or (c is not None and len(x) != c):
                raise ValueError("kalıntı vektörleri aynı boyutta olmalı")
            c = len(x)
            for v in x:
                if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
                    raise ValueError("sonlu sayı gerekli")
    return len(msa), L, c

def _agirlik(W, c, p=None):
    if not isinstance(W, list) or len(W) != c or not all(isinstance(r, list) and r for r in W):
        raise ValueError("ağırlık c × p olmalı")
    n = len(W[0])
    if any(len(r) != n for r in W) or (p is not None and n != p):
        raise ValueError("ağırlık boyutları uyuşmuyor")
    return n

def msa_sutun_dikkati(msa, Wq, Wk, Wv, Wg):
    S, L, c = _msa(msa)
    h = _agirlik(Wq, c)
    for W in (Wk, Wv, Wg):
        _agirlik(W, c, h)

    def carp(x, W):
        return [sum(x[t] * W[t][k] for t in range(c)) for k in range(h)]
    dikkat = []
    cikti = [[None] * L for _ in range(S)]
    for j in range(L):
        X = [msa[s][j] for s in range(S)]
        q, k, v = [carp(x, Wq) for x in X], [carp(x, Wk) for x in X], [carp(x, Wv) for x in X]
        g = [[1.0 / (1.0 + math.exp(-z)) for z in carp(x, Wg)] for x in X]
        sutun = []
        for s in range(S):
            skor = [sum(q[s][t] * k[r][t] for t in range(h)) / math.sqrt(h) for r in range(S)]
            m = max(skor)
            e = [math.exp(x - m) for x in skor]
            top = sum(e)
            a = [x / top for x in e]
            sutun.append([round(x, 6) for x in a])
            cikti[s][j] = [round(g[s][t] * sum(a[r] * v[r][t] for r in range(S)), 6) for t in range(h)]
        dikkat.append(sutun)
    return {"dikkat": dikkat, "cikti": cikti}
```

```hint
Her sütunu ayrı bir "satır dikkati" problemi gibi düşün: o sütundaki S vektör, görev 3'teki L kalıntının yerini alır ve pair bias sıfırdır.
```
:::

::: anlat Gerçek deney: Gerçek ubikuitin yapısında (PDB 1UBQ) SE(3) değişmezlik, ayna ve kiralite
Final gerçek bir protein yapısını kullanır: **ubikuitin, PDB 1UBQ** (1987, 1.8 Å; dosya `tracks/ai-uretim/veri/1UBQ.pdb`). 76 kalıntının N, CA, C, CB atomları okunur; dizi `MQIFVKTLTGK…` olarak çıkar.

- **SE(3) değişmezlik:** CA koordinatları rastgele bir dönme ve ötelemeyle taşınır, 0.5 Å gürültüyle bozulur ve x ekseninde aynalanır. Senin `se3_degismez_rmsd` işlevin üç kopyada da dRMSD hesaplar; sonuç bağımsız bir mesafe matrisi hesabıyla ve hizalamalı Kabsch RMSD ile karşılaştırılır. Dönmüş kopya özdeştir. Ayna görüntüsü de dRMSD'de **özdeş görünür**, oysa Kabsch RMSD ~10 Å'dur: mesafe matrisi aynayı göremez.
- **Kiralite:** her kalıntının CA'sı etrafında N, C ve CB yönlerinin işaretli hacmi ölçülür. Gerçek proteinde (L-aminoasitler) hepsi aynı işaretlidir; aynada hepsi döner. Yapı üreten bir modeli yalnız mesafeyle denetlersen biyolojik olarak imkânsız ayna proteinleri gözden kaçırırsın.
- **Üçgen çarpımsal güncelleme:** gerçek CA mesafelerinden $z_{ij} = e^{-d_{ij}/8}$ çift temsili kurulur ve senin `ucgen_carpimsal_guncelle` işlevine verilir; sonuç torch ile karşılaştırılır. Doğrudan teması olmayan ama ortak bir komşusu olan çiftlerin değeri uzak çiftlerden fazla artar: üçgen eşitsizliği bilgisi bu güncellemeyle yayılır.
- **MSA satır dikkati:** gerçek dizinin one-hot temsili ve mesafeden gelen çift yanlılığı ($-d_{ij}/4$) senin `msa_satir_dikkati` işlevine verilir; sonuç torch ile karşılaştırılır. Çift yanlılığıyla dikkatin büyük kısmı 8 Å içindeki kalıntılara gider.

**Güvenlik yönü — değerlendirme ölçütü oyunlaştırılabilir:** Bir yapı tahmin modelini yalnız dRMSD ile ödüllendiren ya da kabul eden bir değerlendirme düşünelim: "dRMSD < 1 Å ise kabul". Dört aday bu kapıdan geçirilir: dönmüş kopya, 0.5 Å gürültülü kopya, ayna görüntüsü ve 3.8 Å adımlı rastgele bir zincir. Yalnız dRMSD'ye bakan kapı ayna görüntüsünü **kusursuz** (dRMSD 0) diye kabul eder; kapıya kiralite koşulu (≥ 0.8) eklenince ayna reddedilir, gerçek kopyalar kabul edilmeye devam eder. Bir model değerlendirme ölçütüne karşı optimize edildiğinde ölçütün göremediği hataları (burada ayna) üretmeyi öğrenebilir (Goodhart). Değerlendirme ölçütleri, bilinen kör noktaları kapatan ek kontrollerle birlikte kullanılmalıdır (NIST AI RMF: geçerlilik ölçümü).

Kabul: üç işlevin farksal taramayı geçmesi; dRMSD'lerin bağımsız hesapla aynı olması; dönmüş kopyanın özdeş çıkması; aynanın dRMSD'de özdeş, Kabsch'ta farklı çıkması; kiralitenin aynayı ayırt etmesi; üçgen güncelleme ve MSA dikkatinin torch ile aynı olması. Ayrıca yalnız dRMSD'ye bakan kapı aynayı kabul etmeli, kiralite eklenmiş kapı reddetmeli; dönmüş kopya iki kapıdan da geçmeli, rastgele zincir geçmemelidir.

**Kanıt dosyasını oku:** `se3`, `kiralite_orijinal`, `kiralite_ayna`, `ucgen_artis_dolayli`, `ucgen_artis_uzak`, `komsu_dikkat_payi`. Soru 1: Gürültülü kopyada dRMSD ile Kabsch RMSD neden farklı ama aynı mertebede? Soru 2: AlphaFold'un yapı modülü kiraliteyi nasıl korur? Soru 3: Çift yanlılığı olmadan dikkat neden komşulara odaklanmıyor?
:::

::: gorev Gerçek deney · PDB 1UBQ ubikuitinde dRMSD, ayna/kiralite, üçgen güncelleme ve MSA satır dikkati
Önceki görevlerdeki `ucgen_carpimsal_guncelle`, `se3_degismez_rmsd`, `msa_satir_dikkati` işlevlerini buraya birleştir (çözümlerini kopyalayabilirsin). Çalıştır gerçek ölçüm tablosunu gösterir; Kontrol Et önce işlevlerini gizli verilerle ve farksal taramayla sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
timeout: 180
```
```starter
import ai_lab
def ucgen_carpimsal_guncelle(cift_matrisi, sol_agirlik, sag_agirlik):
    return [list(satir) for satir in cift_matrisi]

def se3_degismez_rmsd(koordinatlar_a, koordinatlar_b):
    return {'mesafe_matrisi_a': [], 'drmsd': 0.0, 'ozdes_yapi_mi': False}

def msa_satir_dikkati(msa_satiri, pair_bias, Wq, Wk, Wv, Wg):
    L, h = (len(msa_satiri), len(Wv[0]))
    a = [[1.0 / L] * L for _ in range(L)]
    v = [[sum((x * w[k] for x, w in zip(msa_satiri[j], Wv))) for k in range(h)] for j in range(L)]
    o = [[sum((a[i][j] * v[j][k] for j in range(L))) for k in range(h)] for i in range(L)]
    return {'dikkat': a, 'cikti': o}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_30 as D
    D.goster(ucgen_carpimsal_guncelle, se3_degismez_rmsd, msa_satir_dikkati)
```
```test
import ai_lab
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('_kabsch', '_kiralite', 'pdb_oku', 'kanit_yaz'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
ucgen_carpimsal_guncelle = need("ucgen_carpimsal_guncelle")
se3_degismez_rmsd = need("se3_degismez_rmsd")
msa_satir_dikkati = need("msa_satir_dikkati")
# farksal tarama (görev çözümlerinden derlenen referans)
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef ucgen_carpimsal_guncelle(cift_matrisi, sol_agirlik, sag_agirlik):\n    N = len(cift_matrisi)\n    A = [[cift_matrisi[i][j] * sol_agirlik for j in range(N)] for i in range(N)]\n    B = [[cift_matrisi[i][j] * sag_agirlik for j in range(N)] for i in range(N)]\n    yeni_z = []\n    kok_N = math.sqrt(N)\n    for i in range(N):\n        satir = []\n        for j in range(N):\n            toplam = 0.0\n            for k in range(N):\n                toplam += A[i][k] * B[j][k]\n            val = cift_matrisi[i][j] + toplam / kok_N\n            satir.append(round(val, 4))\n        yeni_z.append(satir)\n    return yeni_z\n\nimport math\n\ndef se3_degismez_rmsd(koordinatlar_a, koordinatlar_b):\n    N = len(koordinatlar_a)\n\n    def mesafe_matrisi(k):\n        m = []\n        for i in range(N):\n            satir = []\n            for j in range(N):\n                dx = k[i][0] - k[j][0]\n                dy = k[i][1] - k[j][1]\n                dz = k[i][2] - k[j][2]\n                dist = math.sqrt(dx * dx + dy * dy + dz * dz)\n                satir.append(dist)\n            m.append(satir)\n        return m\n    DA = mesafe_matrisi(koordinatlar_a)\n    DB = mesafe_matrisi(koordinatlar_b)\n    toplam_fark_kare = 0.0\n    for i in range(N):\n        for j in range(N):\n            fark = DA[i][j] - DB[i][j]\n            toplam_fark_kare += fark * fark\n    drmsd = math.sqrt(toplam_fark_kare / (N * N))\n    da_yuvarli = [[round(DA[i][j], 4) for j in range(N)] for i in range(N)]\n    return {'mesafe_matrisi_a': da_yuvarli, 'drmsd': round(drmsd, 4), 'ozdes_yapi_mi': bool(drmsd < 0.001)}\n\nimport math\n\ndef _matris(m, satir=None, sutun=None):\n    if not isinstance(m, list) or not m or (not all((isinstance(r, list) and r for r in m))):\n        raise ValueError('matris boş olmayan liste listesi olmalı')\n    n = len(m[0])\n    if any((len(r) != n for r in m)) or (satir is not None and len(m) != satir) or (sutun is not None and n != sutun):\n        raise ValueError('matris boyutları uyuşmuyor')\n    return (len(m), n)\n\ndef msa_satir_dikkati(msa_satiri, pair_bias, Wq, Wk, Wv, Wg):\n    L, c = _matris(msa_satiri)\n    _matris(pair_bias, L, L)\n    _, h = _matris(Wq, c)\n    for W in (Wk, Wv, Wg):\n        _matris(W, c, h)\n\n    def carp(x, W):\n        return [sum((x[t] * W[t][k] for t in range(c))) for k in range(h)]\n    q = [carp(x, Wq) for x in msa_satiri]\n    k = [carp(x, Wk) for x in msa_satiri]\n    v = [carp(x, Wv) for x in msa_satiri]\n    g = [[1.0 / (1.0 + math.exp(-z)) for z in carp(x, Wg)] for x in msa_satiri]\n    dikkat, cikti = ([], [])\n    for i in range(L):\n        skor = [sum((q[i][t] * k[j][t] for t in range(h))) / math.sqrt(h) + pair_bias[i][j] for j in range(L)]\n        m = max(skor)\n        e = [math.exp(s - m) for s in skor]\n        top = sum(e)\n        a = [x / top for x in e]\n        o = [g[i][t] * sum((a[j] * v[j][t] for j in range(L))) for t in range(h)]\n        dikkat.append([round(x, 6) for x in a])\n        cikti.append([round(x, 6) for x in o])\n    return {'dikkat': dikkat, 'cikti': cikti}", 'referans', 'exec'), _REF)
_t, _g = _ff(ucgen_carpimsal_guncelle, _REF['ucgen_carpimsal_guncelle'], ([[1.0, 0.0], [0.0, 1.0]], 1.0, 1.0), tohum=3576, en_cok=600, mod='gecerli', butce='oto')
kontrol(_t, "farksal tarama (ucgen_carpimsal_guncelle): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(se3_degismez_rmsd, _REF['se3_degismez_rmsd'], ([[0, 0, 0], [1, 0, 0]], [[0, 0, 0], [0, 1, 0]]), tohum=2804, en_cok=600, mod='gecerli', butce='oto')
kontrol(_t, "farksal tarama (se3_degismez_rmsd): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(msa_satir_dikkati, _REF['msa_satir_dikkati'], ([[1.0, 0.0], [0.0, 1.0]], [[0.0, 0.0], [0.0, 0.0]], [[1.0], [0.0]], [[1.0], [0.0]], [[1.0], [2.0]], [[0.0], [0.0]]), tohum=2848, en_cok=600, mod='gecerli', butce='oto')
kontrol(_t, "farksal tarama (msa_satir_dikkati): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
def _birim_30():
    if se3_degismez_rmsd([[0.0, 0.0, 0.0], [0.0, 0.0, 3.0], [0.0, 1.0, 0.0]], [[0.0, 0.0, 0.0], [0.0, 0.0, 6.0], [0.0, 2.0, 0.0]]) != _REF['se3_degismez_rmsd']([[0.0, 0.0, 0.0], [0.0, 0.0, 3.0], [0.0, 1.0, 0.0]], [[0.0, 0.0, 0.0], [0.0, 0.0, 6.0], [0.0, 2.0, 0.0]]):
        return False
    for _d in (0.001414213562373095, 0.0014):
        if se3_degismez_rmsd([[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]], [[0.0, 0.0, 0.0], [_d, 0.0, 0.0]]) != _REF['se3_degismez_rmsd']([[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]], [[0.0, 0.0, 0.0], [_d, 0.0, 0.0]]):
            return False
    _x30 = [[1.0, 0.0], [0.0, 1.0]]
    if msa_satir_dikkati(_x30, [[0.0, 0.0], [0.0, 0.0]], [[1.0, 1.0], [0.0, 0.0]], [[1.0, 1.0], [0.0, 0.0]], [[1.0, 0.0], [0.0, 1.0]], [[0.0, 0.0], [0.0, 0.0]]) != _REF['msa_satir_dikkati'](_x30, [[0.0, 0.0], [0.0, 0.0]], [[1.0, 1.0], [0.0, 0.0]], [[1.0, 1.0], [0.0, 0.0]], [[1.0, 0.0], [0.0, 1.0]], [[0.0, 0.0], [0.0, 0.0]]):
        return False
    if msa_satir_dikkati(_x30, [[1000.0, 1000.0], [1000.0, 1000.0]], [[1.0], [0.0]], [[1.0], [0.0]], [[1.0], [2.0]], [[0.0], [0.0]])["dikkat"][1] != [0.5, 0.5]:
        return False
    for _args in (
        ("bad", [[0.0]], [[1.0]], [[1.0]], [[1.0]], [[1.0]]),
        ([], [], [[1.0]], [[1.0]], [[1.0]], [[1.0]]),
        ([[]], [[0.0]], [[1.0]], [[1.0]], [[1.0]], [[1.0]]),
        (["a"], [[0.0]], [[1.0]], [[1.0]], [[1.0]], [[1.0]]),
        (([1.0],), [[0.0]], [[1.0]], [[1.0]], [[1.0]], [[1.0]]),
        ([[1.0]], [[0.0]], [[]], [[]], [[]], [[]]),
        ([[1.0, 0.0], [0.0]], [[0.0, 0.0], [0.0, 0.0]], [[1.0], [0.0]], [[1.0], [0.0]], [[1.0], [2.0]], [[0.0], [0.0]]),
        (_x30, [[0.0, 0.0]], [[1.0], [0.0]], [[1.0], [0.0]], [[1.0], [2.0]], [[0.0], [0.0]]),
        (_x30, [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]], [[1.0], [0.0]], [[1.0], [0.0]], [[1.0], [2.0]], [[0.0], [0.0]]),
    ):
        try:
            msa_satir_dikkati(*_args)
            return False
        except ValueError:
            pass
    return True
kontrol(_birim_30(), "dRMSD 3B/N^2/eşik ve MSA satır dikkati sqrt(h)/taşma/boyut sözleşmesi")
if not all(checks): stop()
from sandbox import ai_gercek_ai_uretim_30 as D
try: r = D.deney(ucgen_carpimsal_guncelle, se3_degismez_rmsd, msa_satir_dikkati)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r['drmsd_ayni'] and r['donme_degismez'], 'dRMSD gerçek yapıda bağımsız hesapla aynı; dönmüş kopya özdeş')
kontrol(r['ayna_gorunmez'] and r['kiralite_ayirt_ediyor'], "ayna dRMSD'de görünmüyor, Kabsch ve kiralite ölçüsü onu ayırt ediyor")
kontrol(r['ucgen_ayni'] and r['msa_ayni'], 'üçgen güncelleme ve MSA satır dikkati gerçek yapı verisiyle torch ile aynı')
kontrol(r['metrik_oyunu_olculdu'], 'dRMSD kapısı ayna yapıyı kabul etti, kiralite eklenince reddetti; gerçek kopya kabul, rastgele zincir red')
ai_lab.kanit_yaz("ai-uretim-30-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-uretim-30", "deney": r})
```
```solution
import ai_lab
import math

def ucgen_carpimsal_guncelle(cift_matrisi, sol_agirlik, sag_agirlik):
    N = len(cift_matrisi)
    A = [[cift_matrisi[i][j] * sol_agirlik for j in range(N)] for i in range(N)]
    B = [[cift_matrisi[i][j] * sag_agirlik for j in range(N)] for i in range(N)]
    yeni_z = []
    kok_N = math.sqrt(N)
    for i in range(N):
        satir = []
        for j in range(N):
            toplam = 0.0
            for k in range(N):
                toplam += A[i][k] * B[j][k]
            val = cift_matrisi[i][j] + toplam / kok_N
            satir.append(round(val, 4))
        yeni_z.append(satir)
    return yeni_z

import math

def se3_degismez_rmsd(koordinatlar_a, koordinatlar_b):
    N = len(koordinatlar_a)

    def mesafe_matrisi(k):
        m = []
        for i in range(N):
            satir = []
            for j in range(N):
                dx = k[i][0] - k[j][0]
                dy = k[i][1] - k[j][1]
                dz = k[i][2] - k[j][2]
                dist = math.sqrt(dx * dx + dy * dy + dz * dz)
                satir.append(dist)
            m.append(satir)
        return m
    DA = mesafe_matrisi(koordinatlar_a)
    DB = mesafe_matrisi(koordinatlar_b)
    toplam_fark_kare = 0.0
    for i in range(N):
        for j in range(N):
            fark = DA[i][j] - DB[i][j]
            toplam_fark_kare += fark * fark
    drmsd = math.sqrt(toplam_fark_kare / (N * N))
    da_yuvarli = [[round(DA[i][j], 4) for j in range(N)] for i in range(N)]
    return {'mesafe_matrisi_a': da_yuvarli, 'drmsd': round(drmsd, 4), 'ozdes_yapi_mi': bool(drmsd < 0.001)}

import math

def _matris(m, satir=None, sutun=None):
    if not isinstance(m, list) or not m or (not all((isinstance(r, list) and r for r in m))):
        raise ValueError('matris boş olmayan liste listesi olmalı')
    n = len(m[0])
    if any((len(r) != n for r in m)) or (satir is not None and len(m) != satir) or (sutun is not None and n != sutun):
        raise ValueError('matris boyutları uyuşmuyor')
    return (len(m), n)

def msa_satir_dikkati(msa_satiri, pair_bias, Wq, Wk, Wv, Wg):
    L, c = _matris(msa_satiri)
    _matris(pair_bias, L, L)
    _, h = _matris(Wq, c)
    for W in (Wk, Wv, Wg):
        _matris(W, c, h)

    def carp(x, W):
        return [sum((x[t] * W[t][k] for t in range(c))) for k in range(h)]
    q = [carp(x, Wq) for x in msa_satiri]
    k = [carp(x, Wk) for x in msa_satiri]
    v = [carp(x, Wv) for x in msa_satiri]
    g = [[1.0 / (1.0 + math.exp(-z)) for z in carp(x, Wg)] for x in msa_satiri]
    dikkat, cikti = ([], [])
    for i in range(L):
        skor = [sum((q[i][t] * k[j][t] for t in range(h))) / math.sqrt(h) + pair_bias[i][j] for j in range(L)]
        m = max(skor)
        e = [math.exp(s - m) for s in skor]
        top = sum(e)
        a = [x / top for x in e]
        o = [g[i][t] * sum((a[j] * v[j][t] for j in range(L))) for t in range(h)]
        dikkat.append([round(x, 6) for x in a])
        cikti.append([round(x, 6) for x in o])
    return {'dikkat': dikkat, 'cikti': cikti}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_30 as D
    D.goster(ucgen_carpimsal_guncelle, se3_degismez_rmsd, msa_satir_dikkati)
```
```hint
Üç görevin çözümlerini olduğu gibi buraya koy.
```
:::

::: anlat Sınır
Görevler triangle multiplicative update'i ve 3 boyutlu koordinatlardan SE(3) değişmez mesafe matrisi ile mesafe tabanlı RMSD'yi küçük örneklerle hesaplatır; final adım gerçek bir protein yapısını (PDB 1UBQ) kullanır, AlphaFold modeli çalıştırılmaz; Evoformer'dan tek başlı MSA satır ve sütun dikkati ile outer product mean küçük örneklerle görevdedir; çok başlı dikkat, triangle attention ve Evoformer'ın tam bloğu (katman normları, geçiş katmanları, 48 tekrar) yoktur; outer product mean ve sütun dikkati final adımda gerçek bir MSA ile çalıştırılmaz. Mesafe matrisi tabanlı karşılaştırma yansımayı (ayna görüntüsünü) ayırt edemez; kiralite için ek kontrol gerekir. Koordinat RMSD'si ise önce Kabsch hizalaması ister. AlphaFold tahminleri yüksek güvenle yanlış olabilir; pLDDT ve PAE güven ölçüleri birlikte okunmalıdır.

Kaynaklar: [Jumper vd. 2021 - Highly accurate protein structure prediction with AlphaFold](https://doi.org/10.1038/s41586-021-03819-2), [Abramson vd. 2024 - Accurate structure prediction of biomolecular interactions with AlphaFold 3](https://doi.org/10.1038/s41586-024-07487-w).
:::

::: dusun
AlphaFold 2 yalnızca proteinleri çözerken; 2024'te yayınlanan **AlphaFold 3**, proteinlerin yanında **DNA, RNA, ligandlar (küçük ilaç molekülleri) ve iyonları** da tek birleşik modelde çözebilmektedir. DeepMind, AlphaFold 3'te `Evoformer`'ı sadeleştirip yerine doğrudan görüntü modellerindeki **`Diffusion Transformer (DiT)`** benzeri bir **`Pairformer + Diffusion Module`** koymuştur.

Bir yapay zeka mühendisi olarak düşün: Neden karmaşık bir biyolojik sistemi modellemek için deterministik bir koordinat tahmini yerine, rastgele gürültüden atomları yavaş yavaş doğru 3D konumlarına çeken bir **`Diffusion Module`** kullanmak esnekliği ve birden fazla olası moleküler bağlanma durumunu modellemeyi kolaylaştırır?
:::

::: ozet
- **AlphaFold 2 ve 3**, biyolojinin 50 yıllık protein katlanma problemini çözerek 2024 Kimya Nobel Ödülü'nü almıştır.
- Model, genetik veritabanlarındaki akraba türlerin evrimsel senkronize mutasyonlarını **`Multiple Sequence Alignment (MSA)`** ile yakalar ve kalıntı çiftleri matrisine (**`Pair Representation`**) aktarır.
- 3D Öklid uzayının geometrik kısıtları, her $(i, j)$ çiftini tüm $k$ üçüncü düğümleri üzerinden güncelleyen **`Triangle Multiplicative Update`** ile modele kazınır.
- Proteinin 3D uzaydaki rastgele dönme ve ötelenmelerinden etkilenmemesi için **$\text{SE}(3)$ Invariant Point Attention (IPA)** ve yerel sert çerçeveler (**Rigid Body Frames**) kullanılır.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Evrimsel eş-değişimden çift matrisine (30 sn).** "MSA'da iki sütunun birlikte mutasyon geçirmesi 3B uzayda temas ipucudur; `outer product mean` bu sinyali $(L \times L)$ çift temsiline yazar, üçgen güncellemesi ise $i\text{-}k$ ve $k\text{-}j$ kenarlarından üçgen eşitsizliği tutarlılığını yayar."
2. **$\text{SE}(3)$ değişmezliği ve yerel çerçeveler (35 sn).** "Proteini uzayda döndürmek veya ötelemek fiziği değiştirmez; `IPA` noktaları her kalıntının yerel sert çerçevesinde (`rigid frame`) değerlendirdiği için küresel $\text{SE}(3)$ dönüşümlerine değişmez kalır."
3. **Ayna görüntüsü (`kiralite`) sınırı (30 sn).** "Yalnız uzaklıklara bakan `dRMSD` bir proteini ayna görüntüsünden (`reflection`) ayıramaz; L-amino asit kiralitesini korumak için işaretli dihedral açı veya `Kabsch` $\det(R)=+1$ koşulu şarttır."
4. **Soru (25 sn).** "Ubikuitin (`1UBQ`) deneyinde düz ayna yansıması `dRMSD = 0` verirken biyolojik olarak neden geçersiz bir katlanmadır?"
:::
