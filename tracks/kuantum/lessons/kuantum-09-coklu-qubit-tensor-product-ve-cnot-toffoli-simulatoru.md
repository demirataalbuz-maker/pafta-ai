---
id: kuantum-09
title: "Çoklu-Qubit Tensor Product (Kronecker) ve CNOT/Toffoli Evrensel Kuantum Devre Simülatörü"
summary: "İki ve daha fazla Qubit'i Tensor Product (Kronecker çarpımı) ile birleştir, determinant ve Concurrence ile Entanglement (entanglement) testi yap; CNOT, CZ ve Toffoli (CCX) kapılarıyla kendi N-Qubit evrensel kuantum simülatörünü sıfırdan kodla."
track: kuantum
order: 9
duration_minutes: 35
difficulty: orta
xp: 280
prerequisites: [kuantum-08]
tags: [tensor-product, kronecker, entanglement, concurrence, cnot, toffoli, ghz-state, quantum-simulator]
esleme: kuantum-01, kuantum-10
---

::: anlat Çoklu-Qubit Matematiği: Tensor Product (Kronecker Product ⊗)
## Çoklu-qubit state vector

Birden fazla qubit'in ortak uzayı tensor product ile kurulur. Bu derste iki-qubit durumunun ayrılabilirliğini ve küçük bir state vector üzerinde CNOT/Toffoli etkisini hesaplayacaksın. Simülatör boyutu qubit sayısıyla üstel büyür; görev gerçek quantum donanım çalıştırmaz.

Bir konferansta ya da teknik mülakatta *"Tek bir `Qubit`'in $\alpha|0\rangle + \beta|1\rangle$ olduğunu anladık; peki iki `Qubit` yan yana geldiğinde neden $2 + 2 = 4$ değil de $2^n$ boyutlu bir uzay oluşuyor ve kendi kuantum simülatörümüzü Python'da sıfırdan nasıl yazarız?"* sorusu geldiğinde cevap tek bir matematiksel operatördür: **`Tensor Product` (`Kronecker Product`, $\otimes$)**.

### 1. İki Qubit Nasıl Birleşir? (`Separable / Product State`)
Elinde iki bağımsız `Qubit` olsun:
$$|q_0\rangle = \begin{bmatrix} a_0 \\ a_1 \end{bmatrix}, \qquad |q_1\rangle = \begin{bmatrix} b_0 \\ b_1 \end{bmatrix}$$

Bu iki `Qubit`'in birleşik durumu $|q_0\rangle \otimes |q_1\rangle = |q_0 q_1\rangle$, birincinin her elemanının ikinci vektörün tamamıyla çarpılmasıyla (**`Kronecker Product`**) elde edilen $4$ elemanlı bir sütun vektörüdür:

$$|q_0\rangle \otimes |q_1\rangle = \begin{bmatrix} a_0 \begin{bmatrix} b_0 \\ b_1 \end{bmatrix} \\ a_1 \begin{bmatrix} b_0 \\ b_1 \end{bmatrix} \end{bmatrix} = \begin{bmatrix} a_0 b_0 \\ a_0 b_1 \\ a_1 b_0 \\ a_1 b_1 \end{bmatrix} \begin{matrix} \leftarrow |00\rangle \\ \leftarrow |01\rangle \\ \leftarrow |10\rangle \\ \leftarrow |11\rangle \end{matrix}$$

### 2. Bir Durumun Dolaşık (`Entangled`) Olduğunu Matematiksel Olarak Nasıl Kanıtlarız?
Elinde iki qubit için dört genlikle ifade edilen normalize bir saf durum var:
$$|\Psi\rangle = c_{00}|00\rangle + c_{01}|01\rangle + c_{10}|10\rangle + c_{11}|11\rangle$$

**Kritik Soru:** Bu $|\Psi\rangle$ durumu iki ayrı `Qubit`'in çarpımı ($|q_0\rangle \otimes |q_1\rangle$) olarak ayrıştırılabilir mi (**`Separable / Product State`**), yoksa kuantum dolaşık mıdır (**`Entangled / Non-Separable State`**)?

Yukarıdaki Kronecker çarpımına dikkatle bak! Eğer $|\Psi\rangle$ ayrıştırılabilir bir çarpım durumuysa:
$$c_{00} c_{11} = (a_0 b_0)(a_1 b_1) = (a_0 b_1)(a_1 b_0) = c_{01} c_{10}$$
olmak **zorundadır!** Yani katsayıları $2 \times 2$ bir matrise yerleştirdiğimizde determinant sıfırdır:
$$\det\begin{bmatrix} c_{00} & c_{01} \\ c_{10} & c_{11} \end{bmatrix} = c_{00} c_{11} - c_{01} c_{10} = 0 \iff \text{Separable (Ayrılabilir)}$$

Eğer $\det(C) = c_{00} c_{11} - c_{01} c_{10} \neq 0$ ise, evrendeki **hiçbir** $(a_0, a_1)$ ve $(b_0, b_1)$ seçimi bu durumu ayrı ayrı üretemez; sistem **%100 kanıtlı olarak `Entangled` (Dolaşık)** durumdadır!
Sıfır determinantlı, normalize katsayı matrisi rankı birdir ve iki vektörün dış çarpımı olarak yazılabilir. Bu da ayrılabilirlik iddiasının ters yönünü kanıtlar. Karışık durumlar yoğunluk matrisiyle temsil edilir ve ikiden fazla qubit için önce bir bölümleme seçilir. Aşağıdaki $2\times 2$ determinant formülünün kapsamı iki qubit'li saf durumlardır.

Kuantum bilgi teorisinde **Wootters Concurrence** ölçütü, dolaşıklığın şiddetini $[0, 1]$ aralığında tam olarak bu determinantın iki katıyla ölçer:
$$\mathcal{C}(|\Psi\rangle) = 2 \cdot |c_{00} c_{11} - c_{01} c_{10}|$$
- Çarpım durumunda (ör. $|++\rangle = \frac{1}{2}(|00\rangle + |01\rangle + |10\rangle + |11\rangle)$): $\mathcal{C} = 2 |0.25 - 0.25| = 0$ (entanglement yok!).
- Maksimum dolaşık **`Bell State`** ($|\Phi^+\rangle = \frac{1}{\sqrt{2}}|00\rangle + \frac{1}{\sqrt{2}}|11\rangle$) durumunda: $\mathcal{C} = 2 |0.5 - 0| = 1.0$ (**Maksimum entanglement!**).

```python
import math

def dolasiklik_analizi(c00, c01, c10, c11):
    det = c00 * c11 - c01 * c10
    concurrence = round(2 * abs(det), 6)
    return {"det": round(det, 6), "concurrence": concurrence, "entangled": abs(det) > 1e-6}

s = 1 / math.sqrt(2)
print("Bell |Φ+⟩ :", dolasiklik_analizi(s, 0.0, 0.0, s))
print("Çarpım |++⟩:", dolasiklik_analizi(0.5, 0.5, 0.5, 0.5))
```

**Kaynak ve sınır:** [IBM Quantum: temel quantum information](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information). Sayısal örnekler eğitim ölçeğindedir; gerçek quantum hardware, standart PQC ürünü veya ağ üzerindeki bir hedef üzerinde kabul testi yapılmaz.
:::

::: anlat Çoklu-Qubit Kapıları: CNOT, CZ, Toffoli (CCX) ve GHZ State
Tek-qubit kapılarıyla ($H, X, Z$) süperpozisyon yaratırız; ancak `Qubit`'leri birbirine bağlamak ve evrensel hesaplama (**`Universal Quantum Computation`**) yapmak için çoklu-qubit kapılarına ihtiyacımız vardır:

```
  |q0⟩ ───●───────●───      CNOT: q0=1 ise q1'e X (NOT) uygular.
          │       │
  |q1⟩ ───⊕───────●───      Toffoli (CCX): q0=1 VE q1=1 ise q2'ye X uygular.
                  │         (Klasik tersinir NAND/AND kapısının kuantum karşılığı!)
  |q2⟩ ───────────⊕───
```

| Kapı Adı | Qubit Sayısı | Dönüşüm Kuralı (Bit Düzeyinde) | Kuantum Hacker & Kriptografi Önemi |
| :--- | :---: | :--- | :--- |
| **`CNOT` (`CX`)** | 2 | $|c, t\rangle \to |c, t \oplus c\rangle$ | `Bell Pair` üretir, hata sendromu (`Syndrome`) çıkarır. |
| **`Controlled-Z` (`CZ`)** | 2 | $|11\rangle \to -|11\rangle$ (diğerleri sabit) | Kontrol ve hedef simetriktir! Faz kehanetlerinde (`Phase Oracle`) kullanılır. |
| **`Toffoli Gate` (`CCX`)** | 3 | $|c_1, c_2, t\rangle \to |c_1, c_2, t \oplus (c_1 \land c_2)\rangle$ | `Shor` modüler aritmetik devrelerinin ve `Grover` AES/SHA-256 tersinir (`Reversible`) kapılarının temel yapıtaşıdır! |
| **`GHZ State` Devresi** | $n \ge 3$ | $H_0 \to \text{CNOT}_{0\to 1} \to \text{CNOT}_{0\to 2}$ | $\frac{|000\rangle + |111\rangle}{\sqrt{2}}$ çok-taraflı kuantum gizli paylaşım (`Quantum Secret Sharing`) durumunu üretir. |

```python
import math

# 3-Qubit (8 boyutlu) uzayda |000⟩ durumundan GHZ State (|000⟩ + |111⟩)/√2 üretimi
s = 1 / math.sqrt(2)
durum = [0.0] * 8
durum[0] = 1.0  # |000⟩

# 1. Qubit 0 üzerinde Hadamard: (|000⟩ + |100⟩)/√2  (indis 0 ve indis 4)
durum[0], durum[4] = s, s

# 2. CNOT(0 -> 1): q0=1 olan indis 4 (|100⟩) -> indis 6 (|110⟩) olur
durum[4], durum[6] = durum[6], durum[4]

# 3. CNOT(0 -> 2): q0=1 olan indis 6 (|110⟩) -> indis 7 (|111⟩) olur
durum[6], durum[7] = durum[7], durum[6]
print("GHZ Durumu |000⟩ ve |111⟩ genlikleri:", round(durum[0], 4), round(durum[7], 4))
```
:::

::: tahmin Çarpım Durumu (Separable) mu Yoksa Dolaşık (Entangled) mı?
Bir kuantum devresinin çıkışında 2-Qubit durum vektörü $|\psi\rangle = [0.5, -0.5, -0.5, 0.5]$ olarak verilmiştir. Hesaplama tabanındaki bir ölçüm tek bir bit dizisi verir. Bu örnekte genlikler hesap girdisidir. Bu durumun determinantı ve `Concurrence` değeri nedir?

```python
c00, c01, c10, c11 = 0.5, -0.5, -0.5, 0.5
det = round(c00 * c11 - c01 * c10, 4)
concurrence = round(2 * abs(det), 4)
print(f"Determinant={det} | Concurrence={concurrence}")
```

???

```cikti
Determinant=0.0 | Concurrence=0.0
```
İlk bakışta eksi işaretleri yüzünden dolaşık gibi görünse de $|\psi\rangle = |-\rangle \otimes |-\rangle = \frac{1}{\sqrt{2}}(|0\rangle - |1\rangle) \otimes \frac{1}{\sqrt{2}}(|0\rangle - |1\rangle)$ tam bir çarpım durumudur (`Separable State`)! Nitekim $c_{00}c_{11} - c_{01}c_{10} = (0.5)(0.5) - (-0.5)(-0.5) = 0.25 - 0.25 = 0.0$ çıkar ve `Concurrence=0.0` bunu anında kanıtlar.
:::

::: gorev 1 · İki Qubit Kronecker Çarpımı (Tensor Product) ve entanglement (Concurrence) Testi
`tensor_carpim_ve_dolasiklik(q0, q1, birlesik_durum)` işlevini yaz:
1. `q0 = [a0, a1]` ve `q1 = [b0, b1]` listelerinin Kronecker çarpımını (`[a0*b0, a0*b1, a1*b0, a1*b1]`, her eleman `round(v, 6)`) `tensor_carpim` alanına yaz.
2. `birlesik_durum = [c00, c01, c10, c11]` vektörü için `determinant = round(c00 * c11 - c01 * c10, 6)`, `concurrence = round(2 * abs(c00 * c11 - c01 * c10), 6)` ve `dolasik_mi = bool(abs(c00 * c11 - c01 * c10) > 1e-6)` hesaplayıp sözlük olarak döndür.

```starter
# KUSURLU BAŞLANGIÇ KODU: Kronecker çarpımını ve determinantı düzelt.
def tensor_carpim_ve_dolasiklik(q0, q1, birlesik_durum):
    return {
        "tensor_carpim": [q0[0] + q1[0], 0.0, 0.0, q0[1] + q1[1]],
        "determinant": 0.0,
        "concurrence": 0.0,
        "dolasik_mi": False
    }

s = 2 ** -0.5
print(tensor_carpim_ve_dolasiklik([1.0, 0.0], [s, s], [s, 0.0, 0.0, s]))
```
```test
f = need("tensor_carpim_ve_dolasiklik")
import math
s = 1 / math.sqrt(2)
r1 = f([1.0, 0.0], [s, s], [s, 0.0, 0.0, s])
ok(r1["tensor_carpim"] == [round(s, 6), round(s, 6), 0.0, 0.0], "|0⟩ ⊗ |+⟩ Kronecker çarpımı doğru")
ok(abs(r1["determinant"] - 0.5) < 1e-5 and abs(r1["concurrence"] - 1.0) < 1e-5 and r1["dolasik_mi"] is True, "Bell durumu |Φ+⟩ maksimum dolaşık (Concurrence=1.0) bulundu")
r2 = f([s, -s], [s, -s], [0.5, -0.5, -0.5, 0.5])
ok(r2["tensor_carpim"] == [0.5, -0.5, -0.5, 0.5] and r2["concurrence"] == 0.0 and r2["dolasik_mi"] is False, "|--⟩ çarpım durumu ayrılabilir (Separable) bulundu")
r3 = f([0.6, 0.8], [1.0, 0.0], [0.0, s, -s, 0.0])
ok(r3["tensor_carpim"] == [0.6, 0.0, 0.8, 0.0] and abs(r3["determinant"] - 0.5) < 1e-5 and r3["dolasik_mi"] is True, "Singlet durumu |Ψ-⟩ determinant ve Concurrence testi geçti")
ok(f([1.0, 0.0], [1.0, 0.0], [1.0, 1e-6, 1.0, 0.0])["dolasik_mi"] is False, "|det| == 1e-6 esikte ayrilabilir")
ok(f([1.0, 0.0], [1.0, 0.0], [1.0, 7e-7, 1.0, 0.0])["dolasik_mi"] is False, "|det| = 7e-7 <= 1e-6 ayrilabilir")
ok(f([1.0, 0.0], [1.0, 0.0], [1.0, 1.5e-6, 1.0, 0.0])["dolasik_mi"] is True, "|det| = 1.5e-6 > 1e-6 dolasik")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def tensor_carpim_ve_dolasiklik(q0, q1, birlesik_durum):\n    a0, a1 = q0\n    b0, b1 = q1\n    tc = [round(a0 * b0, 6), round(a0 * b1, 6), round(a1 * b0, 6), round(a1 * b1, 6)]\n    c00, c01, c10, c11 = birlesik_durum\n    det = c00 * c11 - c01 * c10\n    conc = 2.0 * abs(det)\n    return {'tensor_carpim': tc, 'determinant': round(det, 6), 'concurrence': round(conc, 6), 'dolasik_mi': bool(abs(det) > 1e-06)}", 'referans', 'exec'), _REF)
_t, _g = _ff(tensor_carpim_ve_dolasiklik, _REF['tensor_carpim_ve_dolasiklik'], ([1.0, 0.0], [0.7071067811865476, 0.7071067811865476], [0.7071067811865476, 0.0, 0.0, 0.7071067811865476]), tohum=3793, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (tensor_carpim_ve_dolasiklik): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
def tensor_carpim_ve_dolasiklik(q0, q1, birlesik_durum):
    a0, a1 = q0
    b0, b1 = q1
    tc = [round(a0 * b0, 6), round(a0 * b1, 6), round(a1 * b0, 6), round(a1 * b1, 6)]
    c00, c01, c10, c11 = birlesik_durum
    det = c00 * c11 - c01 * c10
    conc = 2.0 * abs(det)
    return {
        "tensor_carpim": tc,
        "determinant": round(det, 6),
        "concurrence": round(conc, 6),
        "dolasik_mi": bool(abs(det) > 1e-6)
    }

if __name__ == "__main__":
    s = 2 ** -0.5
    print(tensor_carpim_ve_dolasiklik([1.0, 0.0], [s, s], [s, 0.0, 0.0, s]))
```
```hint
Kronecker çarpımı `[a0*b0, a0*b1, a1*b0, a1*b1]` sırasındadır; dolaşıklık determinantı ise `c00*c11 - c01*c10` formülüyle hesaplanır.
```
:::

::: gorev 2 · N-Qubit Durum Vektörü Üzerinde CNOT ve Toffoli (CCX) Kapı Simülatörü
`kuantum_kapi_uygula(durum_vektoru, kapi_tipi, kontrol_bitleri, hedef_bit)` işlevini yaz:
- `durum_vektoru` uzunluğu $2^n$ ($n = \text{int}(\log_2(\text{len}))$) olan genlik listesidir. Bir $i$ indisinin $b$-inci qubit biti (`0` en sol MSB) `(i >> (n - 1 - b)) & 1` ile okunur; `hedef_bit` ters çevrilmiş eşlenik indis `i ^ (1 << (n - 1 - hedef_bit))` olur.
- `kontrol_bitleri` listesindeki tüm bitler `1` olduğunda:
  - `kapi_tipi` `"X"`, `"CNOT"` veya `"TOFFOLI"` ise `i` indisiyle eşlenik indisin genliklerini yer değiştir (`yeni[eslenik] = durum_vektoru[i]`).
  - `kapi_tipi` `"Z"` veya `"CZ"` ise ve `hedef_bit` de `1` ise genliği `-1` ile çarp (`yeni[i] = -durum_vektoru[i]`).
- `{"yeni_durum": [round(v, 6) ...], "olasiliklar": [round(v*v, 6) ...], "norm_korundu_mu": bool}` döndür.

```starter
# KUSURLU BAŞLANGIÇ KODU: kontrol bitlerini ve hedef bit dönüşümünü uygula.
def kuantum_kapi_uygula(durum_vektoru, kapi_tipi, kontrol_bitleri, hedef_bit):
    return {
        "yeni_durum": list(durum_vektoru),
        "olasiliklar": [round(v * v, 6) for v in durum_vektoru],
        "norm_korundu_mu": False
    }

s = 2 ** -0.5
print(kuantum_kapi_uygula([s, 0.0, s, 0.0], "CNOT", [0], 1))
```
```test
f = need("kuantum_kapi_uygula")
import math
s = 1 / math.sqrt(2)
# 2-Qubit: (|00⟩ + |10⟩)/√2 üzerinde CNOT(0 -> 1) => Bell |Φ+⟩ = (|00⟩ + |11⟩)/√2
r_bell = f([s, 0.0, s, 0.0], "CNOT", [0], 1)
ok(r_bell["yeni_durum"] == [round(s, 6), 0.0, 0.0, round(s, 6)] and r_bell["olasiliklar"] == [0.5, 0.0, 0.0, 0.5] and r_bell["norm_korundu_mu"] is True, "CNOT kapısı |+0⟩ durumunu Bell |Φ+⟩ durumuna dönüştürdü")

# 3-Qubit (8 boyut): (|000⟩ + |110⟩)/√2 üzerinde TOFFOLI([0, 1] -> 2) => GHZ (|000⟩ + |111⟩)/√2
g_girdi = [s, 0.0, 0.0, 0.0, 0.0, 0.0, s, 0.0]
r_ghz = f(g_girdi, "TOFFOLI", [0, 1], 2)
ok(r_ghz["yeni_durum"] == [round(s, 6), 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, round(s, 6)] and r_ghz["norm_korundu_mu"] is True, "Toffoli (CCX) kapısı 3-Qubit GHZ durumunu üretti")

# CZ kapısı: |11⟩ fazını ters çevirmeli
r_cz = f([0.5, 0.5, 0.5, 0.5], "CZ", [0], 1)
ok(r_cz["yeni_durum"] == [0.5, 0.5, 0.5, -0.5] and r_cz["olasiliklar"] == [0.25, 0.25, 0.25, 0.25], "CZ kapısı yalnız |11⟩ genliğine Phase Flip (-1) uyguladı")
ok(f([1.0, 0.0, 0.0, 0.0], "X", [], 0)["yeni_durum"] == [0.0, 0.0, 1.0, 0.0], "hedef_bit=0 yuksek anlamli bitte X kapisi")
ok(f([0.5, 0.5, 0.5, 0.5], "Z", [], 0)["yeni_durum"] == [0.5, 0.5, -0.5, -0.5], "hedef_bit=0 yuksek anlamli bitte Z kapisi")
ok(f([0.0, 1.0], "I", [], 0)["yeni_durum"] == [0.0, 1.0], "tanimsiz/birim kapi durumu degistirmez")
ok(f([(1.0 + 7e-6)**0.5, 0.0], "I", [], 0)["norm_korundu_mu"] is True, "1e-5 norm toleransi ici")
ok(f([(1.0 + 1.5e-5)**0.5, 0.0], "I", [], 0)["norm_korundu_mu"] is False, "1e-5 norm toleransi disi")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef kuantum_kapi_uygula(durum_vektoru, kapi_tipi, kontrol_bitleri, hedef_bit):\n    boyut = len(durum_vektoru)\n    n = int(round(math.log2(boyut)))\n    yeni = list(durum_vektoru)\n    maske = 1 << n - 1 - hedef_bit\n    for i, amp in enumerate(durum_vektoru):\n        if all((i >> n - 1 - c & 1 == 1 for c in kontrol_bitleri)):\n            if kapi_tipi in ('X', 'CNOT', 'TOFFOLI', 'CCX'):\n                yeni[i ^ maske] = amp\n            elif kapi_tipi in ('Z', 'CZ') and i >> n - 1 - hedef_bit & 1 == 1:\n                yeni[i] = -amp\n    olas = [round(v * v, 6) for v in yeni]\n    norm_ok = abs(sum((v * v for v in yeni)) - 1.0) < 1e-05\n    return {'yeni_durum': [round(v, 6) for v in yeni], 'olasiliklar': olas, 'norm_korundu_mu': bool(norm_ok)}", 'referans', 'exec'), _REF)
_t, _g = _ff(kuantum_kapi_uygula, _REF['kuantum_kapi_uygula'], ([0.7071067811865476, 0.0, 0.7071067811865476, 0.0], 'CNOT', [0], 1), tohum=2970, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (kuantum_kapi_uygula): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def kuantum_kapi_uygula(durum_vektoru, kapi_tipi, kontrol_bitleri, hedef_bit):
    boyut = len(durum_vektoru)
    n = int(round(math.log2(boyut)))
    yeni = list(durum_vektoru)
    maske = 1 << (n - 1 - hedef_bit)
    for i, amp in enumerate(durum_vektoru):
        if all(((i >> (n - 1 - c)) & 1) == 1 for c in kontrol_bitleri):
            if kapi_tipi in ("X", "CNOT", "TOFFOLI", "CCX"):
                yeni[i ^ maske] = amp
            elif kapi_tipi in ("Z", "CZ") and ((i >> (n - 1 - hedef_bit)) & 1) == 1:
                yeni[i] = -amp
    olas = [round((v * v), 6) for v in yeni]
    norm_ok = abs(sum(v * v for v in yeni) - 1.0) < 1e-5
    return {
        "yeni_durum": [round(v, 6) for v in yeni],
        "olasiliklar": olas,
        "norm_korundu_mu": bool(norm_ok)
    }

if __name__ == "__main__":
    s = 2 ** -0.5
    print(kuantum_kapi_uygula([s, 0.0, s, 0.0], "CNOT", [0], 1))
```
```hint
Her `i` indisi için `all(((i >> (n - 1 - c)) & 1) == 1 for c in kontrol_bitleri)` kontrolünü yap; `X/CNOT/TOFFOLI` için `yeni[i ^ (1 << (n - 1 - hedef_bit))] = durum_vektoru[i]` ata.
```
:::

::: anlat Sınır
Görevler iki qubit'li Kronecker çarpımını, concurrence ile dolaşıklık testini ve durum vektörü üzerinde CNOT/Toffoli simülatörünü elle yazdırır. Durum vektörü 2^n boyutludur; bu yöntem bir dizüstü bilgisayarda 30 qubit civarında belleğe sığmaz. Concurrence ve determinant testi yalnız iki qubit'li saf durumlar için geçerlidir; karışık durumlar ve çok qubit'li dolaşıklık (GHZ, W) başka ölçütler (negativity, entanglement witness) ister. Simülatör gürültüsüzdür, kayan nokta toleransına dayanır ve Qiskit/Cirq gibi gerçek bir SDK ile karşılaştırılmamıştır.

Kaynaklar: [Wootters 1998 - Entanglement of Formation of an Arbitrary State of Two Qubits](https://arxiv.org/abs/quant-ph/9709029), [Barenco vd. 1995 - Elementary gates for quantum computation](https://arxiv.org/abs/quant-ph/9503016).
:::

::: dusun
Klasik bilgisayarlarda `NAND` kapısı evrenseldir (`Universal Gate`), fakat iki biti bir bit'e indirdiği için tersinir değildir (`Irreversible`) ve bilgi siler. Kuantum bilgisayarlarda neden `NAND` yerine 3-qubit'lik **`Toffoli Gate (CCX)`** kullanılır? Bir Kuantum Hacker, `Grover` algoritmasıyla `AES-128` veya `SHA-256` kırarken klasik `AND` işlemlerini neden `Toffoli` kapısına ve yardımcı (`Ancilla`) qubit'lere dönüştürmek zorundadır?
:::

::: ozet
- İki veya daha fazla `Qubit`'in durum uzayı **`Tensor Product (Kronecker Product `$\otimes$`)`** ile birleşir ve boyutu $2^n$ olarak büyür.
- Normalize, saf bir 2-Qubit durumunun ayrılabilir (`Separable`) mi yoksa dolaşık (**`Entangled`**) mı olduğu $\det(C) = c_{00}c_{11} - c_{01}c_{10}$ determinantı ve **`Wootters Concurrence`** ($\mathcal{C} = 2|\det(C)|$) ile kesin olarak ölçülür.
- **`CNOT`**, **`CZ`** ve 3-qubit **`Toffoli (CCX)`** kapıları çoklu-qubit dolaşıklığının (`Bell` ve `GHZ` durumları) ve tersinir kriptanaliz devrelerinin temel yapıtaşlarıdır.
:::
