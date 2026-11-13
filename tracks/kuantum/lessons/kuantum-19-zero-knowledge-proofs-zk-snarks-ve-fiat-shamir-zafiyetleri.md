---
id: kuantum-19
title: "Zero-Knowledge Proofs (zk-SNARKs / zk-STARKs) ve Zayıf Fiat-Shamir / Under-Constrained Circuit Hackleme"
track: kuantum
order: 19
duration_minutes: 40
difficulty: ileri
xp: 330
prerequisites: [kuantum-18]
tags: [zero-knowledge-proofs, zk-snarks, zk-starks, r1cs, fiat-shamir, frozen-heart, under-constrained-circuits]
summary: "Sonlu cisim üzerinde R1CS ((A·w)∘(B·w) ≡ C·w mod p) aritmetik devre kısıtlarını doğrula; zayıf Fiat-Shamir dönüşümündeki Frozen Heart (eksik bağlam özeti) ve under-constrained devre zafiyetlerini denetle."
esleme: kuantum-14, kuantum-18
---

::: anlat
## Zero-knowledge proof için aritmetik kısıtlar

Bir proof sisteminde yalnız beklenen hesap değil, bütün gerekli kısıtların tanımlanması önemlidir. Bu derste küçük R1CS ve transcript hesabını inceleyeceksin. Yerel kısıt kontrolü, tek başına bir zk-SNARK prover/verifier veya zero-knowledge privacy kanıtı değildir.

Bir kanıtlayıcı (**`Prover`** — Peggy), bir doğrulayıcıya (**`Verifier`** — Victor):
- *"Ben bu Sudoku bulmacasının çözümünü biliyorum ama çözümden tek bir rakamı bile sana göstermeyeceğim!"* veya
- *"Benim banka hesabımda 1 Milyon Dolardan fazla para var ve kara para listesinde değilim; ama kimliğimi, bakiyemi ve işlem geçmişimi hiç açıklamadan bunun matematiksel kanıtını (`Proof` $\pi$) sunuyorum!"* diyebilir.

---

### 1. Bir `Zero-Knowledge Proof` Sisteminin 3 Matematiksel Garantisi

Herhangi bir protokolün gerçek bir **`ZKP`** sayılabilmesi için şu 3 özelliği aynı anda sağlaması şarttır:
1. **`Completeness` (Tamlık):** Eğer iddia doğruysa ve `Prover` gizli tanığı (**`Secret Witness` $w$**) gerçekten biliyorsa, dürüst `Verifier` kanıtı her zaman kabul eder.
2. **`Soundness` (Sağlamlık — Sahte Kanıt Üretilemezlik):** Eğer iddia yanlışsa (veya `Prover` sırrı bilmiyorsa), hilekar bir `Prover`'ın `Verifier`'ı kandırıp sahte kanıt (**`Forged Proof`**) kabul ettirme olasılığı ihmal edilebilir düzeydedir ($\le 2^{-128}$).
3. **`Zero-Knowledge` (Sıfır Bilgi Sızıntısı):** `Verifier`, kanıtı doğruladığında iddianın doğru olduğu gerçeği dışında gizli tanık $w$ hakkında **sıfır bit bilgi** öğrenir! (Hatta kanıt transkripti, sırrı hiç bilmeyen bir **`Simulator`** tarafından da istatistiksel olarak ayırt edilemez biçimde üretilebilir).

---

### 2. Bilgisayar Programını Polinomlara Çevirmek: `R1CS (Rank-1 Constraint System)`

Bir bilgisayar programını (`SHA-256`, `ECDSA` doğrulaması veya bir `ZK-Rollup` blok geçişini) sıfır bilgi kanıtına dönüştürmek için önce kodu **aritmetik devreye (`Arithmetic Circuit` over $\mathbb{F}_p$)**, ardından **`R1CS (Rank-1 Constraint System)`** matris denklemine çeviririz (**`Arithmetization`**).

Örneğin `Prover`, gizli bir $x$ sayısının $x^3 + x + 5 = 35$ denklemini sağladığını ($x=3$ olduğunu açıklamadan!) kanıtlamak istiyor.
Bu denklemi her satırda **yalnızca tek bir çarpma kapısı (`Rank-1`)** olacak şekilde düzleştiririz (**`Flattening`**):
- **Kapı 1:** $v_1 = x \cdot x$
- **Kapı 2:** $v_2 = v_1 \cdot x$
- **Kapı 3:** $(v_2 + x + 5) \cdot 1 = \text{out}$

Tüm değişkenleri tek bir **Tanık Vektörü (`Witness Vector` $w$)** içinde toplarız:
$$w = [1, \; \text{out}, \; x, \; v_1, \; v_2]^T = [1, \; 35, \; 3, \; 9, \; 27]^T$$

Her bir kapı, üç satır vektörü ($A_i, B_i, C_i$) ile temsil edilir ve tüm devre şu **Hadamard (eleman bazlı $\circ$) çarpım** denklemine dönüşür:

$$(A \cdot w) \circ (B \cdot w) \equiv (C \cdot w) \pmod p$$

```python
# x^3 + x + 5 = 35 denkleminin R1CS (Rank-1 Constraint System) Matris Dogrulamasi
# w = [1 (sabit), out (35), x (3), v1 (9), v2 (27)]
w = [1, 35, 3, 9, 27]

# Kapi 1: x * x = v1
# Kapi 2: v1 * x = v2
# Kapi 3: (v2 + x + 5*1) * 1 = out
A = [[0, 0, 1, 0, 0], [0, 0, 0, 1, 0], [5, 0, 1, 0, 1]]
B = [[0, 0, 1, 0, 0], [0, 0, 1, 0, 0], [1, 0, 0, 0, 0]]
C = [[0, 0, 0, 1, 0], [0, 0, 0, 0, 1], [0, 1, 0, 0, 0]]

for i in range(3):
    sol = sum(A[i][j] * w[j] for j in range(5))
    sag = sum(B[i][j] * w[j] for j in range(5))
    cikti = sum(C[i][j] * w[j] for j in range(5))
    print(f"Kapi {i+1}: ({sol}) * ({sag}) == {cikti} -> {sol * sag == cikti}")
```

---

### 3. Kuantum Merceğinden: `zk-SNARKs` vs `zk-STARKs`

Bir Kuantum ve Kripto Mimarı olarak sahnede mutlaka şu kritik karşılaştırmayı yapmalısın: **"Kuantum bilgisayarlar (`Shor's Algorithm`) Zero-Knowledge kanıtlarını kırabilir mi?"**

| Özellik | `zk-SNARKs` (`Groth16`, `PLONK`, `Zcash`) | `zk-STARKs` (`Starknet`, `RISC Zero`, `FRI`) |
| :--- | :--- | :--- |
| **Açılımı** | *Zero-Knowledge Succinct Non-Interactive Argument of Knowledge* | *Zero-Knowledge Scalable Transparent Argument of Knowledge* |
| **Kriptografik Temel** | **Eliptik Eğri Çiftlemeleri (`Elliptic Curve Pairings` — `BN254`, `BLS12-381`)** | **Çarpışmaya Dirençli Özet Fonksiyonları (`Collision-Resistant Hash` + `FRI` Reed-Solomon)** |
| **Kurulum (`Setup`)** | **`Trusted Setup` (Güvenilir Tören)** gerekir; törendeki gizli $\tau$ (**`Toxic Waste`**) çalınırsa sahte para basılır! | **`Transparent Setup`** (Tamamen şeffaf, gizli anahtar töreni yoktur!) |
| **Kanıt Boyutu (`Proof Size`)** | Çok küçük ($\approx 128 - 288\text{ Bayt}$) | Daha büyük ($\approx 45 - 150\text{ Kilobayt}$) |
| **Kuantum Direnci (`Post-Quantum`)** | ❌ **KUANTUMA DUYARLI (`Broken by Shor's Algorithm`)!** Eliptik eğri ayrık logaritması kırılınca sahte kanıt üretilir! | ✅ **`POST-QUANTUM SAFE`!** İçinde eliptik eğri yoktur; sadece Hash fonksiyonuna dayanır! |

> **Not:** STARK'lar da teknik olarak kısa ve etkileşimsiz kanıtlardır; tablo yaygın, eşleştirme tabanlı SNARK'ları hash tabanlı STARK'larla karşılaştırır. Şeffaf kurulumlu ve hash tabanlı SNARK'lar da vardır, yani "SNARK = trusted setup" her zaman doğru değildir.

---

### 4. ZK Hacker Saldırıları: ZKP Devreleri Nasıl Hacklenir?

Milyarlarca dolarlık `ZK-Rollup` ve gizlilik köprülerinde (`ZK Bridges`) en tehlikeli iki kriptografik zafiyet şunlardır:

#### 💀 Saldırı 1: `Frozen Heart` Zafiyeti (`Weak Fiat-Shamir Transformation`)
Normalde bir ZKP protokolü etkileşimlidir (`Interactive`): `Prover` bir taahhüt (`Commitment` $T$) gönderir, `Verifier` rastgele bir meydan okuma sayısı (**`Challenge` $c$**) seçip sorar, `Prover` yanıt ($s$) verir.
- Blokzincirde etkileşim olamayacağı için **`Fiat-Shamir Heuristic`** kullanılır: Rastgele meydan okuma $c$, o ana kadarki tüm açık verilerin kriptografik özeti olarak hesaplanır:
  $$c = \text{Hash}(\text{Public\_Inputs} \parallel \text{Protocol\_Params} \parallel \text{Commitment\_T})$$
- **💀 `Frozen Heart` Hatası (2022'de Trail of Bits tarafından raporlandı; Bulletproofs ve birçok PLONK uygulamasında bulundu!):** Eğer yazılımcı `Hash(...)` içine **`Public Inputs` (Açık Girdiler — örneğin alıcı adresi veya çekilen miktar)** ya da **`Commitment`** alanını koymayı unutursa ($c$ sabit kalırsa veya açık girdiden bağımsız olursa), saldırgan denklemi geriye doğru çözüp **gizli tanık $w$'yi hiç bilmeden herhangi bir bakiye için %100 geçerli sahte kanıt (`Proof Forgery`) üretir!** (Yani sistemin **`Soundness`** özelliği tamamen çöker!).

#### 💀 Saldırı 2: `Under-Constrained Circuit` (Eksik Kısıtlı Devre Zafiyeti)
ZK dillerinde (`Circom`, `Halo2`, `Noir`) iki farklı işlem vardır:
1. **Tanık Üretimi (`Witness Generation` `<--`):** Değişkenin değerini hesaplar.
2. **Polinom Kısıtı (`Constraint Enforcement` `===`):** Matematiksel olarak `R1CS` matrisine eşitlik denklemi ekler.
- Eğer geliştirici bir sayının 0 veya 1 (bit) olması gerektiğini düşünüp tanık üretiminde bunu hesaplarsa ama devreye **`b * (b - 1) === 0`** kısıtını eklemeyi unutursa (**`Under-Constrained Witness`**), hilekar bir `Prover` $b$ yerine `99999999` yazıp tüm `R1CS` matris doğrulamasından başarıyla geçebilir!

**İleri okuma:** [Halo2: PLONKish arithmetization](https://zcash.github.io/halo2/concepts/arithmetization.html). PLONKish ile buradaki küçük R1CS örneği aynı encoding değildir; ikisi de hesapların kısıtlarla ifade edilmesi fikrini gösterir.
:::

::: tahmin R1CS Boolean (Bit) Kısıtı ve Under-Constrained Witness İstismarı
Bir ZK devresinde geliştirici `secim_biti` değişkeninin yalnızca `0` veya `1` olmasını istemekte ve bunu `secim_biti * (secim_biti - 1) == 0` kısıtıyla (`Constraint`) denetlemektedir. Eğer geliştirici bu kısıtı devreye eklemeyi unutursa (`Under-Constrained`) ve ödül formülü `odul = secim_biti * 100` ise, hilekar bir `Prover` `secim_biti = 50` verdiğinde:
1. Kısıt varken `secim_biti * (secim_biti - 1) == 0` kontrolü ne döner?
2. Kısıt unutulduğunda saldırgan kaç birim sahte ödül kanıtlar?

```python
secim_biti = 50  # Saldirganin enjekte ettigi sahte tanik (Malicious Witness)
kisit_gecerli_mi = (secim_biti * (secim_biti - 1)) == 0
sahte_odul = secim_biti * 100
print(f"Kisit Kontrolu: {kisit_gecerli_mi} | Kisitsiz Sahte Odul: {sahte_odul}")
```

???

```cikti
Kisit Kontrolu: False | Kisitsiz Sahte Odul: 5000
```
Matematiksel olarak $b \cdot (b - 1) = 0$ denkleminin $\mathbb{F}_p$ cisminde yalnızca iki kökü vardır: $b=0$ ve $b=1$. Bu kısıt varken $50 \times 49 = 2450 \neq 0$ olduğu için saldırganın kanıtı anında reddedilir (`False`). Ancak kısıt unutulursa (`Under-Constrained Circuit`), saldırgan `5000` birimlik sahte ödülü geçerli bir kanıt gibi doğrulatabilir!
:::

::: gorev 1 · R1CS (Rank-1 Constraint System) Aritmetik Devre Doğrulayıcısı ((A·w) ∘ (B·w) == C·w)
Bir **`zk-SNARK`** doğrulama motorunun temelini oluşturan sonlu cisim ($\mathbb{F}_p$) üzerindeki **`R1CS`** matris denetleyicisi `r1cs_dogrula(A_matris, B_matris, C_matris, tanik_w, mod_p)` fonksiyonunu yaz.

**Girdiler:**
- `A_matris`, `B_matris`, `C_matris`: Her biri $m$ satır (kısıt/kapı sayısı) ve $n$ sütundan oluşan tam sayı matrisleri (`list[list[int]]`).
- `tanik_w`: $n$ elemanlı tanık vektörü (`Witness Vector`, `list[int]`).
- `mod_p`: Sonlu cisim asal modülü (`int`).

**Doğrulama Kuralları (`i = 0 .. m-1` her kısıt satırı için):**
1. $a_i = \left(\sum_{j=0}^{n-1} A_{i,j} \cdot w_j\right) \bmod \text{mod\_p}$
2. $b_i = \left(\sum_{j=0}^{n-1} B_{i,j} \cdot w_j\right) \bmod \text{mod\_p}$
3. $c_i = \left(\sum_{j=0}^{n-1} C_{i,j} \cdot w_j\right) \bmod \text{mod\_p}$
4. Eğer $(a_i \cdot b_i) \bmod \text{mod\_p} == c_i$ ise $i$-inci kısıt sağlanmıştır; değilse `bozuk_kisitlar` listesine `i` indisini ekle.

**Çıktı Sözlüğü (`dict`):**
- `"gecerli_mi"`: Tüm kısıtlar sağlandıysa (`len(bozuk_kisitlar) == 0`) `True`, aksi halde `False`
- `"toplam_kisit"`: Toplam satır sayısı $m$ (`int`)
- `"bozuk_kisitlar"`: Sağlanmayan kısıtların satır indisleri listesi (`list[int]`)

```starter
def r1cs_dogrula(A_matris, B_matris, C_matris, tanik_w, mod_p):
    # TODO: Her satir icin ((A_i . w) * (B_i . w)) % mod_p == (C_i . w) % mod_p kontrolu yap
    return {
        "gecerli_mi": False,
        "toplam_kisit": 0,
        "bozuk_kisitlar": [],
    }
```

```test
fn = need("r1cs_dogrula")

# x^3 + x + 5 = 35 devresi (mod 97)
# w = [1, out=35, x=3, v1=9, v2=27]
A = [[0, 0, 1, 0, 0], [0, 0, 0, 1, 0], [5, 0, 1, 0, 1]]
B = [[0, 0, 1, 0, 0], [0, 0, 1, 0, 0], [1, 0, 0, 0, 0]]
C = [[0, 0, 0, 1, 0], [0, 0, 0, 0, 1], [0, 1, 0, 0, 0]]

# 1) Dogru tanik vektoru
r1 = fn(A, B, C, [1, 35, 3, 9, 27], 97)
eq(r1["gecerli_mi"], True, "Dogru tanik vektoru [1, 35, 3, 9, 27] R1CS dogrulamasindan gecmeli")
eq(r1["toplam_kisit"], 3, "Toplam 3 kisit satiri olmali")
eq(r1["bozuk_kisitlar"], [], "Bozuk kisit listesi bos olmali")

# 2) Hileli tanik: v1=9 yerine v1=10 verildi (hem 0. hem 1. kisit bozulur!)
r2 = fn(A, B, C, [1, 35, 3, 10, 27], 97)
eq(r2["gecerli_mi"], False, "Bozuk ara degisken R1CS tarafindan yakalanmali")
eq(r2["bozuk_kisitlar"], [0, 1], "0. ve 1. kapilar bozuk olarak raporlanmali")

# 3) Moduler aritmetik testi: mod 17 uzerinde (3*3=9, 9*3=27==10 mod 17, 10+3+5=18==1 mod 17)
r3 = fn(A, B, C, [1, 1, 3, 9, 10], 17)
eq(r3["gecerli_mi"], True, "Sonlu cisim mod 17 uzerinde denklem dogru calismali")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def r1cs_dogrula(A_matris, B_matris, C_matris, tanik_w, mod_p):\n    bozuk = []\n    m = len(A_matris)\n    for i in range(m):\n        ai = sum((a * w for a, w in zip(A_matris[i], tanik_w))) % mod_p\n        bi = sum((b * w for b, w in zip(B_matris[i], tanik_w))) % mod_p\n        ci = sum((c * w for c, w in zip(C_matris[i], tanik_w))) % mod_p\n        if ai * bi % mod_p != ci:\n            bozuk.append(i)\n    return {'gecerli_mi': len(bozuk) == 0, 'toplam_kisit': m, 'bozuk_kisitlar': bozuk}", 'referans', 'exec'), _REF)
_t, _g = _ff(r1cs_dogrula, _REF['r1cs_dogrula'], ([[0, 0, 1, 0, 0], [0, 0, 0, 1, 0], [5, 0, 1, 0, 1]], [[0, 0, 1, 0, 0], [0, 0, 1, 0, 0], [1, 0, 0, 0, 0]], [[0, 0, 0, 1, 0], [0, 0, 0, 0, 1], [0, 1, 0, 0, 0]], [1, 35, 3, 9, 27], 97), tohum=2146, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (r1cs_dogrula): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
def r1cs_dogrula(A_matris, B_matris, C_matris, tanik_w, mod_p):
    bozuk = []
    m = len(A_matris)

    for i in range(m):
        ai = sum(a * w for a, w in zip(A_matris[i], tanik_w)) % mod_p
        bi = sum(b * w for b, w in zip(B_matris[i], tanik_w)) % mod_p
        ci = sum(c * w for c, w in zip(C_matris[i], tanik_w)) % mod_p
        if (ai * bi) % mod_p != ci:
            bozuk.append(i)

    return {
        "gecerli_mi": len(bozuk) == 0,
        "toplam_kisit": m,
        "bozuk_kisitlar": bozuk,
    }
```

```hint
Her `i` satırı için `ai`, `bi` ve `ci` iç çarpımlarını (`sum(x * w for x, w in zip(satir, tanik_w)) % mod_p`) hesapla ve `(ai * bi) % mod_p != ci` ise `i` indisini `bozuk` listesine ekle.
```
:::

::: gorev 2 · Fiat-Shamir Transcript Denetimi (Frozen Heart Zafiyeti Tespiti)
Etkileşimsiz bir **`ZKP`** protokolünde **`Fiat-Shamir`** meydan okuma özeti $c = \text{Hash}(\dots)$ üretilirken **`Frozen Heart`** (Proof Forgery) zafiyeti olup olmadığını denetleyen `fiat_shamir_denetle(baglam_alanlari, hash_girdisi_alanlari, zorunlu_alanlar)` fonksiyonunu yaz.

**Girdiler:**
- `baglam_alanlari`: Protokol kimliği ve devre parametrelerini içeren sözlük (`dict[str, str]`).
- `hash_girdisi_alanlari`: Geliştiricinin `Fiat-Shamir` özetine (`Transcript`) dahil ettiği alan adlarının sırasıyla listesi (`list[str]`).
- `zorunlu_alanlar`: Güvenli bir `Fiat-Shamir` dönüşümü için özetin içinde **mutlaka bulunması gereken** kritik alan adları kümesi/listesi (ör. `["prover_commitment", "public_inputs", "circuit_id"]`).

**Denetim Kuralları ve Çıktı Sözlüğü (`dict`):**
1. `"eksik_zorunlu_alanlar"`: `zorunlu_alanlar` içinde olup `hash_girdisi_alanlari` içinde **yer almayan** alanların alfabetik sıralı listesi (`sorted(...)`).
2. `"frozen_heart_riski"`: Eğer `eksik_zorunlu_alanlar` boş değilse (en az 1 zorunlu alan unutulmuşsa) `True`, tüm zorunlu alanlar dahil edilmişse `False`.
3. `"challenge_ozeti"`: `hash_girdisi_alanlari` içindeki her `alan` için `f"{alan}={baglam_alanlari.get(alan, '')}"` parçalarını `"|"` ile birleştirip (`"|".join(...)`) UTF-8 **`SHA-256`** `hexdigest()` özetini döndür.

```starter
import hashlib

def fiat_shamir_denetle(baglam_alanlari, hash_girdisi_alanlari, zorunlu_alanlar):
    # TODO: Zorunlu alanlarin Fiat-Shamir transcript ozetine dahil edilip edilmedigini denetle
    return {
        "eksik_zorunlu_alanlar": [],
        "frozen_heart_riski": True,
        "challenge_ozeti": "",
    }
```

```test
import hashlib
fn = need("fiat_shamir_denetle")

baglam = {
    "circuit_id": "zk_bridge_v1",
    "public_inputs": "alici=0xABC,miktar=1000",
    "prover_commitment": "0x99887766",
}
zorunlu = ["circuit_id", "public_inputs", "prover_commitment"]

# 1) Zafiyetli Fiat-Shamir (Frozen Heart!): public_inputs ve circuit_id unutulmus!
r1 = fn(baglam, ["prover_commitment"], zorunlu)
eq(r1["frozen_heart_riski"], True, "Public inputs unutuldugunda Frozen Heart riski True olmali")
eq(r1["eksik_zorunlu_alanlar"], ["circuit_id", "public_inputs"], "Eksik alanlar alfabetik siralanmali")
beklenen_h1 = hashlib.sha256(b"prover_commitment=0x99887766").hexdigest()
eq(r1["challenge_ozeti"], beklenen_h1, "Challenge ozeti dogru formatta hesaplanmali")

# 2) Guvenli Fiat-Shamir: Tum zorunlu alanlar transcript icinde mevcut
girdi_tam = ["circuit_id", "public_inputs", "prover_commitment"]
r2 = fn(baglam, girdi_tam, zorunlu)
eq(r2["frozen_heart_riski"], False, "Tum zorunlu alanlar varken Frozen Heart riski False olmali")
eq(r2["eksik_zorunlu_alanlar"], [], "Eksik alan listesi bos olmali")
metin2 = "circuit_id=zk_bridge_v1|public_inputs=alici=0xABC,miktar=1000|prover_commitment=0x99887766"
eq(r2["challenge_ozeti"], hashlib.sha256(metin2.encode("utf-8")).hexdigest(), "Tam transcript ozeti dogru olmali")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile('import hashlib\n\ndef fiat_shamir_denetle(baglam_alanlari, hash_girdisi_alanlari, zorunlu_alanlar):\n    mevcut_kume = set(hash_girdisi_alanlari)\n    eksikler = sorted((alan for alan in zorunlu_alanlar if alan not in mevcut_kume))\n    parcalar = [f"{alan}={baglam_alanlari.get(alan, \'\')}" for alan in hash_girdisi_alanlari]\n    birlesik = \'|\'.join(parcalar)\n    ozet = hashlib.sha256(birlesik.encode(\'utf-8\')).hexdigest()\n    return {\'eksik_zorunlu_alanlar\': eksikler, \'frozen_heart_riski\': len(eksikler) > 0, \'challenge_ozeti\': ozet}', 'referans', 'exec'), _REF)
_t, _g = _ff(fiat_shamir_denetle, _REF['fiat_shamir_denetle'], ({'circuit_id': 'zk_bridge_v1', 'public_inputs': 'alici=0xABC,miktar=1000', 'prover_commitment': '0x99887766'}, ['prover_commitment'], ['circuit_id', 'public_inputs', 'prover_commitment']), tohum=2915, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (fiat_shamir_denetle): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
import hashlib

def fiat_shamir_denetle(baglam_alanlari, hash_girdisi_alanlari, zorunlu_alanlar):
    mevcut_kume = set(hash_girdisi_alanlari)
    eksikler = sorted(alan for alan in zorunlu_alanlar if alan not in mevcut_kume)

    parcalar = [f"{alan}={baglam_alanlari.get(alan, '')}" for alan in hash_girdisi_alanlari]
    birlesik = "|".join(parcalar)
    ozet = hashlib.sha256(birlesik.encode("utf-8")).hexdigest()

    return {
        "eksik_zorunlu_alanlar": eksikler,
        "frozen_heart_riski": len(eksikler) > 0,
        "challenge_ozeti": ozet,
    }
```

```hint
`eksikler = sorted(alan for alan in zorunlu_alanlar if alan not in set(hash_girdisi_alanlari))` ile unutulan alanları bul. Ardından `hash_girdisi_alanlari` sırasıyla `f"{alan}={baglam_alanlari.get(alan, '')}"` metinlerini `"|"` ile birleştirip `sha256` özetini al.
```
:::

::: anlat Sınır
Görevler R1CS doğrulayıcısını ((A·w)∘(B·w) = C·w) ve Fiat-Shamir transcript denetimini (Frozen Heart) yazdırır; gerçek bir SNARK/STARK ispatı üretilmez ya da doğrulanmaz (polinom taahhüdü ve eşleme yoktur). R1CS denetimi tanığın kısıtları sağladığını gösterir; devrenin amaçlanan hesabı eksiksiz kısıtladığını, yani under-constrained olmadığını kanıtlamaz, bunun için ayrı devre denetimi ya da biçimsel doğrulama gerekir. Zayıf Fiat-Shamir yalnız transcript'e girmeyen açık girdilerle sınırlı değildir; uygulamanın hash'e koyduğu bağlamın tamamı denetlenmelidir.

Kaynaklar: [Groth 2016 - On the Size of Pairing-based Non-interactive Arguments](https://eprint.iacr.org/2016/260), [Ben-Sasson vd. 2018 - Scalable, transparent, and post-quantum secure computational integrity](https://eprint.iacr.org/2018/046), [Dao vd. 2023 - Weak Fiat-Shamir Attacks on Modern Proof Systems](https://eprint.iacr.org/2023/691).
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
Sıfır bilgi kanıtları (ZKP), gizli tanığı açıklamadan bir hesabın doğru yapıldığını $(A \cdot w) \circ (B \cdot w) \equiv C \cdot w \pmod p$ gibi aritmetik devre kısıtlarıyla (R1CS) kanıtlar; eşleştirme tabanlı klasik zk-SNARK'lar kısa kanıt üretse de Shor algoritmasına duyarlıyken, yalnızca özet fonksiyonlarına dayanan zk-STARK'lar şeffaf kurulumlu ve kuantuma dirençlidir.

Uygulamada ZK sistemleri en çok iki mühendislik hatasından kırılır: Fiat-Shamir meydan okuma özetine açık girdileri veya taahhüdü eklemeyi unutmak (Frozen Heart) sahte kanıt üretimine yol açar; tanık hesabını yazıp devreye eşitlik kısıtını (`===`) koymamak (under-constrained circuit) ise hileli tanıkların doğrulamadan geçmesine izin verir.
:::

::: dusun
`Zcash` gibi gizlilik odaklı kripto paralarda kullanılan **`zk-SNARK`** sisteminde eğer **`Trusted Setup`** törenindeki gizli parametre $\tau$ (**`Toxic Waste`**) bir saldırganın eline geçerse (veya gelecekte bir kuantum bilgisayar **`Shor's Algorithm`** ile eliptik eğri tabanlı `CRS` parametrelerinden $\tau$'yu çözerse), saldırgan **gizlilik (`Zero-Knowledge`)** özelliğini mi kırar yoksa **sağlamlık (`Soundness` — sınırsız sahte para basma)** özelliğini mi kırar? Neden blokzincirde kimsenin ruhu bile duymadan karşılıksız milyarlarca coin üretebilir?
:::

::: ozet
- **`Zero-Knowledge Proof (ZKP)`** protokolleri **`Completeness`** (dürüst kanıt geçer), **`Soundness`** (sahte kanıt üretilemez) ve **`Zero-Knowledge`** (gizli tanık $w$ sızmaz) ilkeleri üzerine kurulur; hesaplamalar **`R1CS`** ($(A \cdot w) \circ (B \cdot w) \equiv C \cdot w \pmod p$) aritmetik devrelerine dönüştürülür.
- Eliptik eğri çiftlemelerine dayanan **`zk-SNARKs`** çok küçük kanıt üretir ancak **`Shor's Algorithm`** karşısında kuantuma duyarlıdır; yalnızca özet fonksiyonlarına (`Hash` + `FRI`) dayanan **`zk-STARKs`** ise **`Trusted Setup`** gerektirmez ve **`Post-Quantum Safe`** (kuantuma dirençli) yapıdadır.
- En yaygın iki ZK güvenlik zafiyeti; açık girdilerin meydan okuma özetine dahil edilmemesiyle oluşan **`Frozen Heart` (`Weak Fiat-Shamir`)** saldırısı ve devreye eksik polinom eşitliği yazılmasıyla doğan **`Under-Constrained Circuit`** istismarıdır.
:::
