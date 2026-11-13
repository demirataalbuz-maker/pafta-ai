---
id: ai-uretim-23
title: "Monte Carlo Tree Search (MCTS), PUCT Formülü ve AlphaZero/AlphaProof Düşünce Ağacı"
track: ai-uretim
order: 23
duration_minutes: 45
difficulty: ileri
xp: 330
prerequisites: [ai-uretim-22]
summary: "Bir LLM veya Reasoning AI en zorlu olimpiyat matematiği (AlphaProof) ve strateji problemlerini çözerken nasıl ileriye dönük arama (Lookahead Tree Search) yapar? Monte Carlo Tree Search (MCTS): Selection (PUCT), Expansion, Evaluation (PRM/Value) ve Backpropagation."
esleme: ai-temel-26, ai-uretim-24, ai-uretim-30
tags: [mcts, puct, alphazero, alphaproof, tree-of-thoughts, process-reward-model, reasoning-search]
---

::: anlat 1. Tek Çizgili Düşünmekten (Linear CoT) Ağaç Aramasıyla Düşünmeye (MCTS / AlphaProof) Geçiş
## MCTS ve PUCT ile arama

MCTS, denenen yolların değerini ve ziyaret sayısını kullanarak aramayı yönlendirir. Bu derste PUCT seçim skorunu ve seçilen yoldan yukarı değer aktarımını hesaplayacaksın. Sık ziyaret edilen dalı seçmek ile doğruluğu bağımsız bir verifier ile göstermek farklı görevlerdir.

Bir konferansta kürsüye çıktığında izleyicilere şu soruyu sor:
> *"Dünya satranç şampiyonu Magnus Carlsen veya Uluslararası Matematik Olimpiyatı (`IMO`) altın madalyalı bir matematikçi zor bir teoremi kanıtlarken aklına gelen ilk yolu silgisiz tükenmez kalemle dümdüz yazıp (`Greedy / Linear Chain-of-Thought`) geçer mi? **Hayır!** Zihninde bir **Düşünce Ağacı (`Tree of Thoughts`)** açar: `'Önce tümevarım yolunu deneyeyim... 3 adım ilerledim, çıkmaza girdi! Şimdi geri dönüp (`Backtrack`) çelişkiyle kanıt (`Proof by Contradiction`) dalını araştırayım!'` der. Peki bir dil modeline bu ileriye dönük arama (`Lookahead Tree Search`) ve çıkmaz sokaktan geri dönme yeteneğini nasıl kazandırırız?"*

İşte Google DeepMind'ın Go şampiyonunu yenen **`AlphaGo / AlphaZero`** sisteminden, 2024'te Uluslararası Matematik Olimpiyatı (`IMO`) sorularını çözen **`AlphaProof`** ve ileri düzey **`System-2 Reasoning LLM`** motorlarına uzanan algoritmanın adı: **`Monte Carlo Tree Search (MCTS)`**!

```text
                       [KÖK DÜĞÜM s_0: Olimpiyat Problemi]
                                (N = 10 Ziyaret)
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
             [Dal A: Tümevarım]  [Dal B: Çelişki]   [Dal C: Cebirsel]
              N=6, Q=0.45         N=3, Q=0.82        N=1, Q=0.50
              P=0.50              P=0.35             P=0.15
                                       │
                        ┌──────────────┴──────────────┐
                        ▼                             ▼
                 [Alt-Adım B1]                 [Alt-Adım B2]
                  N=2, Q=0.90                   N=1, Q=0.65
```

### 🧠 Bir LLM'de `MCTS` Düğümü (`Node`) ve Kenarı (`Edge / Action`) Nedir?
Satrançta her hamle (`Action` $a$) bir taş oynatmaktır (`"e2 -> e4"`). Bir **`Reasoning LLM`** veya **`AlphaProof (Lean 4 Theorem Prover)`** modelinde ise:
- **Durum (`State` $s$):** Şimdiye kadar yazılmış olan problem metni + ara düşünce adımları dizisidir.
- **Eylem (`Action` $a$):** Tek bir harf değil; **bir sonraki mantıksal düşünce adımı (`Reasoning Step` / Cümle / `Lean 4 Tactic`)** bloğudur!
- **Politika Ağı (`Policy Network` $\pi_\theta(a \mid s)$):** Dil modelinin kendisidir! Mevcut $s$ durumunda hangi yeni düşünce adımlarının ($a_1, a_2, \dots, a_k$) üretilebileceğini ve bunların önsel olasılıklarını (**`Prior Probability` $P(s, a)$**) verir.
- **Değer Ağı (`Value Network` $V_\phi(s)$ veya `Process Reward Model - PRM`):** O düşünce adımının doğru çözüme ne kadar yakın olduğunu $[-1, 1]$ veya $[0, 1]$ aralığında puanlayan değerlendirici ağdır!

**Uygulama sınırı:** Görevler Python ile küçük, denetlenebilir hesaplar yapar. `python norun` blokları PyTorch/GPU tarafını incelemek içindir; bu tezgâhta otomatik çalıştırılıp gerçek training/serving kabulü yapılmaz.

**Birincil kaynak:** [AlphaZero makalesi](https://arxiv.org/abs/1712.01815). Kaynak, yöntemin ayrıntıları içindir; dersteki küçük örnek ölçülmüş üretim benchmarkı değildir.
:::

::: anlat 2. MCTS Döngüsünün 4 Kutsal Aşaması ve AlphaZero PUCT Denklemi
`MCTS`, kendisine verilen düşünme bütçesi (`Search Budget`, örn. $800$ simülasyon) boyunca **4 adımlı bir döngüyü** tekrarlar. Her düğüm-eylem çifti $(s, a)$ üzerinde **4 istatistik** tutulur:
- $N(s, a)$: Bu düşünce dalının şimdiye kadar kaç kez ziyaret edildiği (**`Visit Count`**).
- $W(s, a)$: Bu daldan elde edilen toplam kümülatif ödül/değer (**`Total Action Value`**).
- $Q(s, a) = \frac{W(s, a)}{N(s, a)}$: Bu dalın ortalama başarısı (**`Mean Action Value / Exploitation`**; $N=0$ ise $Q=0.0$).
- $P(s, a)$: Dil modelinin ($\pi_\theta$) bu düşünce adımına verdiği başlangıç olasılığı (**`Policy Prior`**).

### 1. `Selection` (Seçim — `PUCT` Formülü ile Yaprağa İnmek)
Kök düğümden ($s_0$) başlayarak bir yaprak düğüme (`Leaf Node`) ulaşana kadar her adımda **`PUCT` (`Predictor + Upper Confidence Bound for Trees`)** skorunu maksimize eden alt dal $a^*$ seçilir:

$$a^* = \arg\max_{a} \Big( \underbrace{Q(s, a)}_{\text{Sömürü (Exploitation)}} + \underbrace{c_{\text{puct}} \cdot P(s, a) \cdot \frac{\sqrt{\sum_{b} N(s, b)}}{1 + N(s, a)}}_{\text{Keşif Ödülü (Exploration Bonus } U(s, a)\text{)}} \Big)$$

**Bu denklemin güzelliğine dikkat et:**
- İlk terim olan **$Q(s, a)$**, şimdiye kadar yüksek puan almış başarılı yolları seçmek ister (**`Exploitation`**).
- İkinci terim olan **$U(s, a)$** ise paydasındaki $1 + N(s, a)$ sayesinde **henüz hiç denenmemiş ($N(s,a)=0$) ama dil modelinin yüksek olasılık ($P(s,a)$) verdiği umut vadeden yeni yolları** seçmeye zorlar (**`Exploration`**)! Dal ziyaret edildikçe $1 + N(s,a)$ büyür, keşif bonusu küçülür ve arama başka dallara kayar!

### 2. `Expansion` (Genişletme)
Yaprak düğüm $s_L$'e ulaştığımızda (eğer çözüm henüz bitmediyse), politika ağımız ($\pi_\theta$) çalıştırılarak $K$ adet yeni aday düşünce adımı ($a_1, \dots, a_K$) örneklenir ve ağaca yeni çocuk düğümler olarak eklenir.

### 3. `Evaluation` (Değerlendirme — `Value Head / PRM / Rollout`)
Klasik MCTS'de oyun sonuna kadar rastgele oynanırdı (`Random Rollout`), ancak bir LLM'de her seferinde 2000 `token` sonuna kadar üretmek çok yavaştır! Bunun yerine `AlphaZero` tarzı MCTS'de yaprak düğüm $s_L$ doğrudan **`Process Reward Model (PRM)` / `Value Network`** ile anında değerlendirilerek bir $v \in [0, 1]$ (veya $[-1, 1]$) değeri alınır!

### 4. `Backpropagation` (backpropagation — İstatistikleri Köke Kadar Güncellemek)
Yaprak düğümden elde edilen $v$ ödülü, **yapraktan kök düğüme ($s_0$) kadar çıkılan yol üzerindeki bütün ata düğümlere (`Ancestors`)** geri yayılır:

$$N(s, a) \leftarrow N(s, a) + 1, \qquad W(s, a) \leftarrow W(s, a) + v, \qquad Q(s, a) \leftarrow \frac{W(s, a)}{N(s, a)}$$

```text
  MCTS 4 ADIMLI ARAMA DÖNGÜSÜ:
  [1. SELECTION (PUCT)] ──► [2. EXPANSION (Policy π_θ)] ──► [3. EVALUATION (Value V_φ / PRM)]
           ▲                                                                │
           └────────── [4. BACKPROPAGATION (N += 1, W += v, Q = W/N)] ◄─────┘
```
:::

::: anlat 3. Arama Sonunda Nihai Karar ve Kendi Kendini Eğitme (Expert Iteration / AlphaZero Loop)
800 simülasyon bittiğinde kök düğümden hangi düşünce adımını seçip ekrana yazdırırız?
En yüksek $Q$ değerine bakan gürültülü seçim yerine, **en çok ziyaret edilen (`Most Visited` $\arg\max_a N(s_0, a)$)** veya ziyaret sayılarını sıcaklıkla olasılığa çeviren dağılım kullanılır:

$$\pi_{\text{MCTS}}(a \mid s_0) = \frac{N(s_0, a)^{1 / \tau}}{\sum_{b} N(s_0, b)^{1 / \tau}}$$

### 🔄 `Expert Iteration`: MCTS Neden Modeli "Kendi Kendinin Öğretmeni" Yapar?
- Tek başına dil modeli ($\pi_\theta$) zayıf bir tahmincidir; ancak `MCTS` aramasıyla desteklenmiş $\pi_{\text{MCTS}}$ dağılımı çok daha zeki bir **"Uzman (`Expert`)"** politikadır!
- Arama bittikten sonra dil modelini $\pi_\theta(a \mid s) \to \pi_{\text{MCTS}}(a \mid s)$ hedefine yaklaşacak şekilde (`Cross-Entropy Loss`) ve değer ağını $V_\phi(s) \to z$ (gerçek çözüm sonucu) hedefine yaklaşacak şekilde (`MSE Loss`) eğittiğimizde, **bir sonraki nesilde dil modeli artık ağaç araması yapmadan bile ilk seferde doğru düşünce adımını tahmin etmeye başlar!**

```python norun
import math
import torch
import torch.nn as nn

class MCTSReasoningNode:
    def __init__(self, state_text: str, prior_p: float, parent=None):
        self.state_text = state_text
        self.parent = parent
        self.children = {}   # action_step -> MCTSReasoningNode
        self.N = 0           # Ziyaret sayısı
        self.W = 0.0         # Toplam ödül
        self.Q = 0.0         # Ortalama değer (W / N)
        self.P = prior_p     # Policy prior olasılığı

    def select_child_puct(self, c_puct: float = 1.5):
        total_parent_N = sum(child.N for child in self.children.values())
        sqrt_total = math.sqrt(total_parent_N)
        best_score = -float("inf")
        best_action, best_child = None, None
        for action, child in self.children.items():
            u_score = c_puct * child.P * (sqrt_total / (1.0 + child.N))
            puct_score = child.Q + u_score
            if puct_score > best_score:
                best_score = puct_score
                best_action, best_child = action, child
        return best_action, best_child

    def backpropagate(self, value: float):
        node = self
        while node is not None:
            node.N += 1
            node.W += value
            node.Q = node.W / node.N
            node = node.parent
```
:::

::: tahmin PUCT Keşif (Exploration) ve Sömürü (Exploitation) Dengesi Hesabı
Bir düşünce düğümünün iki alt dalı (`Dal_A` ve `Dal_B`) bulunuyor ve toplam ebeveyn ziyareti $\sum_b N(s, b) = 9$ (`karekökü = 3.0`):
- **`Dal_A`:** Çok ziyaret edilmiş ($N_A = 8$), ortalama değeri yüksek ($Q_A = 0.75$) ve önsel olasılığı $P_A = 0.60$.
- **`Dal_B`:** Sadece 1 kez ziyaret edilmiş ($N_B = 1$), ortalama değeri $Q_B = 0.50$ ve önsel olasılığı $P_B = 0.40$.
Keşif katsayısı $c_{\text{puct}} = 2.0$ olduğunda `Dal_A` ve `Dal_B`'nin `PUCT` skorları nedir ve MCTS hangi dalı seçer?

```python
import math

c_puct = 2.0
sqrt_toplam_n = math.sqrt(8 + 1)  # 3.0

puct_A = 0.75 + c_puct * 0.60 * (sqrt_toplam_n / (1 + 8))
puct_B = 0.50 + c_puct * 0.40 * (sqrt_toplam_n / (1 + 1))
secilen = "Dal_B" if puct_B > puct_A else "Dal_A"
print(f"PUCT_A: {puct_A:.2f} | PUCT_B: {puct_B:.2f} -> Secilen: {secilen}")
```

???

```cikti
PUCT_A: 1.15 | PUCT_B: 1.70 -> Secilen: Dal_B
```
`Dal_A` için keşif bonusu $2.0 \times 0.60 \times (3.0 / 9) = 0.40$ olup $\text{PUCT}_A = 0.75 + 0.40 = 1.15$ çıkar. `Dal_B` ise henüz sadece 1 kez ziyaret edildiği için keşif bonusu $2.0 \times 0.40 \times (3.0 / 2) = 1.20$ olur ve $\text{PUCT}_B = 0.50 + 1.20 = 1.70$ ile **`Dal_B` seçilir**! İşte `PUCT` formülü böylece az ziyaret edilmiş dalların keşfedilmesini garanti eder.
:::

::: gorev 1 · AlphaZero PUCT Seçim Skoru ve En İyi Düşünce Dalını Seçme
Bir ebeveyn düşünce düğümünün alt dalları (`dugum_cocuklari`) arasından `AlphaZero PUCT` formülüne göre en yüksek skorlu dalı seçen `puct_dal_sec(dugum_cocuklari, c_puct)` işlevini yaz:

1. **Girdiler:**
   - `dugum_cocuklari`: Her biri `{"dal_id": str, "N": int, "W": float, "P": float}` biçiminde olan alt dal sözlüklerinin listesi (`N >= 0`: ziyaret sayısı, `W`: toplam ödül, `P`: politika önsel olasılığı).
   - `c_puct`: Keşif katsayısı ($c_{\text{puct}} > 0$, `float`).
2. **Matematiksel Kurallar:**
   - Tüm çocukların toplam ziyaret sayısını hesapla:
     $$N_{\text{toplam}} = \sum_{b} N_b$$
   - Her çocuk dal için:
     - **Ortalama Değer ($Q$):** Eğer $N > 0$ ise $Q = W / N$, eğer $N == 0$ ise $Q = 0.0$.
     - **Keşif Terimi ($U$):**
       $$U = c_{\text{puct}} \cdot P \cdot \frac{\sqrt{N_{\text{toplam}}}}{1 + N}$$
     - **PUCT Skoru:** $\text{PUCT} = Q + U$.
   - Tüm dalların `{"dal_id": str, "Q": float, "U": float, "puct": float}` (`round(val, 6)` ile yuvarlanmış) bilgilerini `dal_skorlari` listesinde (girdi sırasıyla) tut.
   - En yüksek **yuvarlanmamış (veya `1e-9` hassasiyetli) `PUCT`** skoruna sahip dalın kimliğini `secilen_dal_id` olarak belirle (eşitlik durumunda listede daha önce gelen dalı seç).
3. **Dönüş Değeri:**
   `{"secilen_dal_id": str, "toplam_ziyaret": int, "dal_skorlari": [dict, ...]}` sözlüğü döndür. Girdileri değiştirme.

```starter
def puct_dal_sec(dugum_cocuklari, c_puct=1.5):
    # KUSURLU BAŞLANGIÇ KODU: PUCT keşif bonusunu (U) hesaplamadan sadece ilk dalı seçiyor!
    return {
        "secilen_dal_id": dugum_cocuklari[0]["dal_id"],
        "toplam_ziyaret": 0,
        "dal_skorlari": [
            {"dal_id": d["dal_id"], "Q": 0.0, "U": 0.0, "puct": 0.0}
            for d in dugum_cocuklari
        ],
    }

ornek_dallar = [
    {"dal_id": "Tumevarim", "N": 8, "W": 6.0, "P": 0.6},
    {"dal_id": "Celiski", "N": 1, "W": 0.5, "P": 0.4},
]
print(puct_dal_sec(ornek_dallar, c_puct=2.0))
```

```test
import copy, math

def _ref_puct(cocuklar, c):
    top_n = sum(d["N"] for d in cocuklar)
    kok_n = math.sqrt(top_n)
    skorlar = []
    en_iyi_id = None
    en_iyi_skor = -float("inf")
    for d in cocuklar:
        q = (d["W"] / d["N"]) if d["N"] > 0 else 0.0
        u = c * d["P"] * (kok_n / (1.0 + d["N"]))
        puct = q + u
        if puct > en_iyi_skor + 1e-12:
            en_iyi_skor = puct
            en_iyi_id = d["dal_id"]
        skorlar.append({
            "dal_id": d["dal_id"],
            "Q": round(q, 6),
            "U": round(u, 6),
            "puct": round(puct, 6),
        })
    return {
        "secilen_dal_id": en_iyi_id,
        "toplam_ziyaret": top_n,
        "dal_skorlari": skorlar,
    }

def sozlesme(fn):
    try:
        v1 = [
            {"dal_id": "Tumevarim", "N": 8, "W": 6.0, "P": 0.6},
            {"dal_id": "Celiski", "N": 1, "W": 0.5, "P": 0.4},
        ]
        v2 = [
            {"dal_id": "A", "N": 0, "W": 0.0, "P": 0.2},
            {"dal_id": "B", "N": 4, "W": 3.2, "P": 0.5},
            {"dal_id": "C", "N": 0, "W": 0.0, "P": 0.3},
        ]
        for v, c in [(v1, 2.0), (v1, 0.2), (v2, 1.5)]:
            v_k = copy.deepcopy(v)
            if fn(v, c) != _ref_puct(v, c) or v != v_k:
                return False
        return True
    except Exception:
        return False

ok(sozlesme(puct_dal_sec), "puct_dal_sec Q(s,a) + U(s,a) PUCT formülünü ve N=0 durumunu doğru hesaplamalı")

def m_sadece_q(cocuklar, c=1.5):
    return puct_dal_sec(cocuklar, 0.0)

def m_payda_n(cocuklar, c=1.5):
    r = copy.deepcopy(_ref_puct(cocuklar, c))
    r["toplam_ziyaret"] += 999
    return r

for ad, m in [("Keşif terimi U'yu sıfırlayıp sadece Q ile seçen", m_sadece_q), ("Toplam ziyareti yanlış hesaplayan", m_payda_n)]:
    ok(not sozlesme(m), f"Yanlış çözüm/mutant yakalanmalı: {ad}")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef puct_dal_sec(dugum_cocuklari, c_puct=1.5):\n    toplam_ziyaret = sum((d['N'] for d in dugum_cocuklari))\n    kok_toplam = math.sqrt(toplam_ziyaret)\n    dal_skorlari = []\n    secilen_id = None\n    en_yuksek = -float('inf')\n    for d in dugum_cocuklari:\n        n = d['N']\n        q = d['W'] / n if n > 0 else 0.0\n        u = c_puct * d['P'] * (kok_toplam / (1.0 + n))\n        puct = q + u\n        if puct > en_yuksek + 1e-12:\n            en_yuksek = puct\n            secilen_id = d['dal_id']\n        dal_skorlari.append({'dal_id': d['dal_id'], 'Q': round(q, 6), 'U': round(u, 6), 'puct': round(puct, 6)})\n    return {'secilen_dal_id': secilen_id, 'toplam_ziyaret': toplam_ziyaret, 'dal_skorlari': dal_skorlari}", 'referans', 'exec'), _REF)
_t, _g = _ff(puct_dal_sec, _REF['puct_dal_sec'], ([{'dal_id': 'Tumevarim', 'N': 8, 'W': 6.0, 'P': 0.6}, {'dal_id': 'Celiski', 'N': 1, 'W': 0.5, 'P': 0.4}], 2.0), tohum=2309, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (puct_dal_sec): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
ok(puct_dal_sec([{"dal_id": "a", "N": 2, "W": 1.0, "P": 0.2}, {"dal_id": "b", "N": 0, "W": 0.0, "P": 0.8}]) == _REF['puct_dal_sec']([{"dal_id": "a", "N": 2, "W": 1.0, "P": 0.2}, {"dal_id": "b", "N": 0, "W": 0.0, "P": 0.8}]), "varsayılan c_puct=1.5 ve N=0 dalı korunmalı")
ok(puct_dal_sec([{"dal_id": "a", "N": 1, "W": 0.5, "P": 0.5}, {"dal_id": "b", "N": 1, "W": 0.5, "P": 0.5}]) == _REF['puct_dal_sec']([{"dal_id": "a", "N": 1, "W": 0.5, "P": 0.5}, {"dal_id": "b", "N": 1, "W": 0.5, "P": 0.5}]), "eşit PUCT skorunda ilk dal korunmalı")
```

```solution
import math

def puct_dal_sec(dugum_cocuklari, c_puct=1.5):
    toplam_ziyaret = sum(d["N"] for d in dugum_cocuklari)
    kok_toplam = math.sqrt(toplam_ziyaret)
    dal_skorlari = []
    secilen_id = None
    en_yuksek = -float("inf")

    for d in dugum_cocuklari:
        n = d["N"]
        q = (d["W"] / n) if n > 0 else 0.0
        u = c_puct * d["P"] * (kok_toplam / (1.0 + n))
        puct = q + u
        if puct > en_yuksek + 1e-12:
            en_yuksek = puct
            secilen_id = d["dal_id"]
        dal_skorlari.append({
            "dal_id": d["dal_id"],
            "Q": round(q, 6),
            "U": round(u, 6),
            "puct": round(puct, 6),
        })

    return {
        "secilen_dal_id": secilen_id,
        "toplam_ziyaret": toplam_ziyaret,
        "dal_skorlari": dal_skorlari,
    }
```

```hint
Önce `toplam_ziyaret = sum(d["N"] for d in dugum_cocuklari)` ve karekökünü bul. Her dal için `q = d["W"] / d["N"] if d["N"] > 0 else 0.0` ve `u = c_puct * d["P"] * ( math.sqrt(toplam_ziyaret) / (1 + d["N"]) )` hesaplayıp en yüksek `q + u` değerine sahip dalı seç.
```
:::

::: gorev 2 · MCTS Ağacında backpropagation ve Ziyaret/Değer Güncellemesi
Bir `MCTS` düşünce ağacında değerlendirilen yaprak düğümden (`yaprak_id`) başlayıp kök düğüme (`parent == None`) kadar tüm ata düğümlerin (`Ancestors`) ziyaret ($N$), toplam değer ($W$) ve ortalama değer ($Q$) istatistiklerini güncelleyen `mcts_geri_yayilim(agac_dugumleri, yaprak_id, odul_degeri)` işlevini yaz:

1. **Girdiler:**
   - `agac_dugumleri`: Anahtarları düğüm kimliği (`str`), değerleri ise `{"parent": str veya None, "N": int, "W": float, "Q": float}` olan sözlük.
   - `yaprak_id`: Değerlendirmenin yapıldığı başlangıç yaprak düğümünün kimliği (`str`).
   - `odul_degeri`: Değerlendirici ağdan (`PRM / Value Network`) gelen ödül skoru $v$ (`float`).
2. **Kurallar:**
   - Girdi `agac_dugumleri` sözlüğünü doğrudan değiştirme; derin bir kopyası (`deepcopy`) üzerinde çalış!
   - `yaprak_id` düğümünden başla ve `parent` bağlantısını takip ederek kök düğüme (`None` olana) kadar ilerle:
     - Ziyaret edilen her düğümün kimliğini sırasıyla `guncellenen_yol` listesine ekle (örn. `["yaprak", "ara_dugum", "kok"]`).
     - Yol üzerindeki her düğüm için:
       $$N \leftarrow N + 1, \qquad W \leftarrow \text{round}(W + \text{odul\_degeri}, 6), \qquad Q \leftarrow \text{round}(W_{\text{yeni}} / N_{\text{yeni}}, 6)$$
     - Yol üzerinde **olmayan** yan dallardaki düğümlerin istatistiklerine kesinlikle dokunma!
3. **Dönüş Değeri:**
   `{"guncellenen_yol": [str, ...], "kok_yeni_Q": float, "guncel_agac": dict}` sözlüğü döndür (`kok_yeni_Q`, yolun sonundaki kök düğümün yeni `Q` değeridir).

```starter
import copy

def mcts_geri_yayilim(agac_dugumleri, yaprak_id, odul_degeri):
    # KUSURLU BAŞLANGIÇ KODU: ebeveyn (parent) zincirini takip edip N, W, Q güncellemesi yapmıyor!
    yeni_agac = copy.deepcopy(agac_dugumleri)
    return {
        "guncellenen_yol": [yaprak_id],
        "kok_yeni_Q": 0.0,
        "guncel_agac": yeni_agac,
    }

ornek_agac = {
    "kok": {"parent": None, "N": 2, "W": 1.0, "Q": 0.5},
    "dal_1": {"parent": "kok", "N": 1, "W": 0.4, "Q": 0.4},
    "dal_2": {"parent": "kok", "N": 1, "W": 0.6, "Q": 0.6},
    "yaprak_1a": {"parent": "dal_1", "N": 0, "W": 0.0, "Q": 0.0},
}
print(mcts_geri_yayilim(ornek_agac, "yaprak_1a", 0.8))
```

```test
import copy

def _ref_backprop(agac, yaprak, v):
    yeni = copy.deepcopy(agac)
    yol = []
    cur = yaprak
    while cur is not None:
        yol.append(cur)
        dugum = yeni[cur]
        dugum["N"] += 1
        dugum["W"] = round(dugum["W"] + v, 6)
        dugum["Q"] = round(dugum["W"] / dugum["N"], 6)
        cur = dugum["parent"]
    kok_id = yol[-1]
    return {
        "guncellenen_yol": yol,
        "kok_yeni_Q": yeni[kok_id]["Q"],
        "guncel_agac": yeni,
    }

def sozlesme(fn):
    try:
        agac = {
            "kok": {"parent": None, "N": 2, "W": 1.0, "Q": 0.5},
            "dal_1": {"parent": "kok", "N": 1, "W": 0.4, "Q": 0.4},
            "dal_2": {"parent": "kok", "N": 1, "W": 0.6, "Q": 0.6},
            "yaprak_1a": {"parent": "dal_1", "N": 0, "W": 0.0, "Q": 0.0},
        }
        for yaprak, v in [("yaprak_1a", 0.8), ("dal_2", 1.0), ("kok", 0.2)]:
            a_kopya = copy.deepcopy(agac)
            sonuc = fn(agac, yaprak, v)
            bek = _ref_backprop(agac, yaprak, v)
            if sonuc != bek or agac != a_kopya:
                return False
        return True
    except Exception:
        return False

ok(sozlesme(mcts_geri_yayilim), "mcts_geri_yayilim yapraktan köke kadar yalnızca ata düğümlerin N, W ve Q değerlerini doğru güncellemeli")

def m_tum_agaci_guncelle(agac, yaprak, v):
    r = copy.deepcopy(_ref_backprop(agac, yaprak, v))
    for k, d in r["guncel_agac"].items():
        d["N"] += 1
    return r

def m_sadece_yaprak(agac, yaprak, v):
    r = copy.deepcopy(_ref_backprop(agac, yaprak, v))
    r["guncellenen_yol"] = [yaprak]
    return r

for ad, m in [("Yol dışındaki yan dalları da yanlışlıkla güncelleyen", m_tum_agaci_guncelle), ("Ata düğümlere çıkmayıp sadece yaprakta kalan", m_sadece_yaprak)]:
    ok(not sozlesme(m), f"Yanlış çözüm/mutant yakalanmalı: {ad}")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import copy\n\ndef mcts_geri_yayilim(agac_dugumleri, yaprak_id, odul_degeri):\n    guncel_agac = copy.deepcopy(agac_dugumleri)\n    guncellenen_yol = []\n    mevcut = yaprak_id\n    while mevcut is not None:\n        guncellenen_yol.append(mevcut)\n        dugum = guncel_agac[mevcut]\n        dugum['N'] += 1\n        dugum['W'] = round(dugum['W'] + odul_degeri, 6)\n        dugum['Q'] = round(dugum['W'] / dugum['N'], 6)\n        mevcut = dugum['parent']\n    kok_id = guncellenen_yol[-1]\n    return {'guncellenen_yol': guncellenen_yol, 'kok_yeni_Q': guncel_agac[kok_id]['Q'], 'guncel_agac': guncel_agac}", 'referans', 'exec'), _REF)
_t, _g = _ff(mcts_geri_yayilim, _REF['mcts_geri_yayilim'], ({'kok': {'parent': None, 'N': 2, 'W': 1.0, 'Q': 0.5}, 'dal_1': {'parent': 'kok', 'N': 1, 'W': 0.4, 'Q': 0.4}, 'dal_2': {'parent': 'kok', 'N': 1, 'W': 0.6, 'Q': 0.6}, 'yaprak_1a': {'parent': 'dal_1', 'N': 0, 'W': 0.0, 'Q': 0.0}}, 'yaprak_1a', 0.8), tohum=2873, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (mcts_geri_yayilim): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
ok(mcts_geri_yayilim({"root": {"parent": None, "N": 1, "W": 0.1234564, "Q": 0.123456}}, "root", 0.0000003) == _REF['mcts_geri_yayilim']({"root": {"parent": None, "N": 1, "W": 0.1234564, "Q": 0.123456}}, "root", 0.0000003), "W 6 basamak yuvarlama korunmalı")
```

```solution
import copy

def mcts_geri_yayilim(agac_dugumleri, yaprak_id, odul_degeri):
    guncel_agac = copy.deepcopy(agac_dugumleri)
    guncellenen_yol = []
    mevcut = yaprak_id

    while mevcut is not None:
        guncellenen_yol.append(mevcut)
        dugum = guncel_agac[mevcut]
        dugum["N"] += 1
        dugum["W"] = round(dugum["W"] + odul_degeri, 6)
        dugum["Q"] = round(dugum["W"] / dugum["N"], 6)
        mevcut = dugum["parent"]

    kok_id = guncellenen_yol[-1]
    return {
        "guncellenen_yol": guncellenen_yol,
        "kok_yeni_Q": guncel_agac[kok_id]["Q"],
        "guncel_agac": guncel_agac,
    }
```

```hint
`copy.deepcopy(agac_dugumleri)` ile kopya al. `mevcut = yaprak_id` ile başlayıp `while mevcut is not None:` döngüsü içinde `N += 1`, `W = round(W + odul_degeri, 6)` ve `Q = round(W / N, 6)` güncellemesini yapıp `mevcut = dugum["parent"]` adımına geç.
```
:::

::: anlat Gerçek deney: Gerçek bir oyunda tam MCTS ajanı ve minimax'a karşı
Final senin iki işlevini tam bir MCTS ajanının içine koyar ve gerçek bir oyunda, **tic-tac-toe**'da oynatır:

- Ajan her hamlede ağacı büyütür: seçim aşamasında senin `puct_dal_sec` işlevin çocuklar arasından seçer (öncül olasılıklar tekdüze), yaprak genişletilir, rastgele oyunla sonuç alınır ve senin `mcts_geri_yayilim` işlevin ziyaret ve değerleri günceller. Ödül her düğümde o hamleyi yapan oyuncu açısından verilir.
- Her çağrı bağımsız bir referansla denetlenir (bir milyonu aşkın çağrı).
- **Tuzak pozisyonlar:** oyunun tüm ağacı minimax ile çözülür ve tek doğru hamlesi olan 12 gerçek pozisyon bulunur. Ajan 16, 64, 256 ve 1024 simülasyon bütçesiyle bu pozisyonlarda denenir: bütçe arttıkça doğru hamle sayısı nasıl değişiyor?
- **Oyunlar:** 1024 simülasyonla 20 oyun rastgele oyuncuya, 20 oyun kusursuz oynayan minimax'a karşı oynanır. Tic-tac-toe kusursuz oyunda beraberedir; iyi bir ajan minimax'a kaybetmemelidir.

**Güvenlik yönü — arama, ödüldeki hatayı büyütür:** Doğrulayıcının kazanma çizgileri tablosuna tek bir yazım hatası konur: (0, 4, 8) çaprazı yerine (0, 4, 7). Sahte çizgiyi tek hamlede tamamlayabildiği ama bunun gerçek en iyi hamle olmadığı 12 gerçek pozisyonda, aynı MCTS ajanı (senin işlevlerinle) hatalı ve doğru ödülle 16–1024 bütçeyle çalıştırılır. Hatalı ödülde bütçe arttıkça ajan sahte hamleyi **daha sık** seçer; doğru ödülde hata sıfıra iner. Daha çok arama ya da optimizasyon kusurlu bir doğrulayıcıyı daha güçlü sömürür (ödül hacklemesi, Goodhart); LLM akıl yürütme aramasında doğrulayıcının açıkları aynı biçimde bulunur.

Kabul: iki işlevin farksal taramayı geçmesi; tüm çağrıların referansla aynı olması; bütçe arttıkça tuzak pozisyonlarda doğru hamlenin artması; ajanın rastgeleye ve minimax'a hiç kaybetmemesi. Ayrıca hatalı ödülde sahte hamle sayısı bütçeyle artmalı ve en büyük bütçede pozisyonların en az %75'ine çıkmalı, doğru ödülde sıfır olmalıdır.

**Kanıt dosyasını oku:** `cagri`, `butce_tablosu`, `oyunlar`. Soru 1: 16 simülasyonla ajan neden tuzakların yarısından fazlasını kaçırıyor? Soru 2: Değer ağı ve öğrenilmiş öncül olasılıklar bütçe ihtiyacını nasıl değiştirirdi? Soru 3: Bir LLM akıl yürütme ağacında "rastgele oyun" yerine ne kullanılır ve onu kandırmanın riski nedir?
:::

::: gorev Gerçek deney · Tic-tac-toe'da tam MCTS ajanı, tuzak pozisyonlar ve minimax'a karşı oyunlar
Önceki görevlerdeki `puct_dal_sec`, `mcts_geri_yayilim` işlevlerini buraya birleştir (çözümlerini kopyalayabilirsin). Çalıştır gerçek ölçüm tablosunu gösterir; Kontrol Et önce işlevlerini gizli verilerle ve farksal taramayla sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
timeout: 180
```
```starter
import ai_lab
def puct_dal_sec(dugum_cocuklari, c_puct=1.5):
    return {'secilen_dal_id': dugum_cocuklari[0]['dal_id'], 'toplam_ziyaret': 0, 'dal_skorlari': [{'dal_id': d['dal_id'], 'Q': 0.0, 'U': 0.0, 'puct': 0.0} for d in dugum_cocuklari]}

import copy

def mcts_geri_yayilim(agac_dugumleri, yaprak_id, odul_degeri):
    yeni_agac = copy.deepcopy(agac_dugumleri)
    return {'guncellenen_yol': [yaprak_id], 'kok_yeni_Q': 0.0, 'guncel_agac': yeni_agac}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_23 as D
    D.goster(puct_dal_sec, mcts_geri_yayilim)
```
```test
import ai_lab
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('_ref_puct', '_minimax', 'kanit_yaz'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
puct_dal_sec = need("puct_dal_sec")
mcts_geri_yayilim = need("mcts_geri_yayilim")
# farksal tarama (görev çözümlerinden derlenen referans)
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef puct_dal_sec(dugum_cocuklari, c_puct=1.5):\n    toplam_ziyaret = sum((d['N'] for d in dugum_cocuklari))\n    kok_toplam = math.sqrt(toplam_ziyaret)\n    dal_skorlari = []\n    secilen_id = None\n    en_yuksek = -float('inf')\n    for d in dugum_cocuklari:\n        n = d['N']\n        q = d['W'] / n if n > 0 else 0.0\n        u = c_puct * d['P'] * (kok_toplam / (1.0 + n))\n        puct = q + u\n        if puct > en_yuksek + 1e-12:\n            en_yuksek = puct\n            secilen_id = d['dal_id']\n        dal_skorlari.append({'dal_id': d['dal_id'], 'Q': round(q, 6), 'U': round(u, 6), 'puct': round(puct, 6)})\n    return {'secilen_dal_id': secilen_id, 'toplam_ziyaret': toplam_ziyaret, 'dal_skorlari': dal_skorlari}\n\nimport copy\n\ndef mcts_geri_yayilim(agac_dugumleri, yaprak_id, odul_degeri):\n    guncel_agac = copy.deepcopy(agac_dugumleri)\n    guncellenen_yol = []\n    mevcut = yaprak_id\n    while mevcut is not None:\n        guncellenen_yol.append(mevcut)\n        dugum = guncel_agac[mevcut]\n        dugum['N'] += 1\n        dugum['W'] = round(dugum['W'] + odul_degeri, 6)\n        dugum['Q'] = round(dugum['W'] / dugum['N'], 6)\n        mevcut = dugum['parent']\n    kok_id = guncellenen_yol[-1]\n    return {'guncellenen_yol': guncellenen_yol, 'kok_yeni_Q': guncel_agac[kok_id]['Q'], 'guncel_agac': guncel_agac}", 'referans', 'exec'), _REF)
_t, _g = _ff(puct_dal_sec, _REF['puct_dal_sec'], ([{'dal_id': 'Tumevarim', 'N': 8, 'W': 6.0, 'P': 0.6}, {'dal_id': 'Celiski', 'N': 1, 'W': 0.5, 'P': 0.4}], 2.0), tohum=2309, en_cok=600, mod='gecerli', butce='oto')
kontrol(_t, "farksal tarama (puct_dal_sec): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(mcts_geri_yayilim, _REF['mcts_geri_yayilim'], ({'kok': {'parent': None, 'N': 2, 'W': 1.0, 'Q': 0.5}, 'dal_1': {'parent': 'kok', 'N': 1, 'W': 0.4, 'Q': 0.4}, 'dal_2': {'parent': 'kok', 'N': 1, 'W': 0.6, 'Q': 0.6}, 'yaprak_1a': {'parent': 'dal_1', 'N': 0, 'W': 0.0, 'Q': 0.0}}, 'yaprak_1a', 0.8), tohum=2873, en_cok=600, mod='gecerli', butce='oto')
kontrol(_t, "farksal tarama (mcts_geri_yayilim): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
kontrol(puct_dal_sec([{"dal_id": "a", "N": 2, "W": 1.0, "P": 0.2}, {"dal_id": "b", "N": 0, "W": 0.0, "P": 0.8}]) == _REF['puct_dal_sec']([{"dal_id": "a", "N": 2, "W": 1.0, "P": 0.2}, {"dal_id": "b", "N": 0, "W": 0.0, "P": 0.8}]), "varsayılan c_puct=1.5 ve N=0 dalı korunmalı")
kontrol(puct_dal_sec([{"dal_id": "a", "N": 1, "W": 0.5, "P": 0.5}, {"dal_id": "b", "N": 1, "W": 0.5, "P": 0.5}]) == _REF['puct_dal_sec']([{"dal_id": "a", "N": 1, "W": 0.5, "P": 0.5}, {"dal_id": "b", "N": 1, "W": 0.5, "P": 0.5}]), "eşit PUCT skorunda ilk dal korunmalı")
kontrol(mcts_geri_yayilim({"root": {"parent": None, "N": 1, "W": 0.1234564, "Q": 0.123456}}, "root", 0.0000003) == _REF['mcts_geri_yayilim']({"root": {"parent": None, "N": 1, "W": 0.1234564, "Q": 0.123456}}, "root", 0.0000003), "W 6 basamak yuvarlama korunmalı")
if not all(checks): stop()
from sandbox import ai_gercek_ai_uretim_23 as D
try: r = D.deney(puct_dal_sec, mcts_geri_yayilim)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r['cagri_ayni'], 'tüm PUCT ve geri yayılım çağrıları gerçek oyunda referansla aynı')
kontrol(r['butce_iyilestirdi'], 'simülasyon bütçesi arttıkça tuzak pozisyonlarda doğru hamle arttı')
kontrol(r['minimaxa_kaybetmedi'] and r['rastgeleye_kaybetmedi'], "1024 simülasyonlu ajan rastgeleye ve minimax'a kaybetmedi")
kontrol(r['arama_hatayi_somuruyor'], 'bütçe arttıkça MCTS hatalı ödüldeki sahte çizgiyi daha sık seçti; doğru ödülle hiç seçmedi')
ai_lab.kanit_yaz("ai-uretim-23-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-uretim-23", "deney": r})
```
```solution
import ai_lab
import math

def puct_dal_sec(dugum_cocuklari, c_puct=1.5):
    toplam_ziyaret = sum((d['N'] for d in dugum_cocuklari))
    kok_toplam = math.sqrt(toplam_ziyaret)
    dal_skorlari = []
    secilen_id = None
    en_yuksek = -float('inf')
    for d in dugum_cocuklari:
        n = d['N']
        q = d['W'] / n if n > 0 else 0.0
        u = c_puct * d['P'] * (kok_toplam / (1.0 + n))
        puct = q + u
        if puct > en_yuksek + 1e-12:
            en_yuksek = puct
            secilen_id = d['dal_id']
        dal_skorlari.append({'dal_id': d['dal_id'], 'Q': round(q, 6), 'U': round(u, 6), 'puct': round(puct, 6)})
    return {'secilen_dal_id': secilen_id, 'toplam_ziyaret': toplam_ziyaret, 'dal_skorlari': dal_skorlari}

import copy

def mcts_geri_yayilim(agac_dugumleri, yaprak_id, odul_degeri):
    guncel_agac = copy.deepcopy(agac_dugumleri)
    guncellenen_yol = []
    mevcut = yaprak_id
    while mevcut is not None:
        guncellenen_yol.append(mevcut)
        dugum = guncel_agac[mevcut]
        dugum['N'] += 1
        dugum['W'] = round(dugum['W'] + odul_degeri, 6)
        dugum['Q'] = round(dugum['W'] / dugum['N'], 6)
        mevcut = dugum['parent']
    kok_id = guncellenen_yol[-1]
    return {'guncellenen_yol': guncellenen_yol, 'kok_yeni_Q': guncel_agac[kok_id]['Q'], 'guncel_agac': guncel_agac}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_23 as D
    D.goster(puct_dal_sec, mcts_geri_yayilim)
```
```hint
İki görevin çözümlerini olduğu gibi buraya koy.
```
:::

::: anlat Sınır
Görevler PUCT seçim skorunu ve MCTS geri yayılımını küçük ağaçlarda hesaplatır; final adım bunları gerçek bir oyunda (tic-tac-toe) tam bir MCTS ajanında kullanır; dil modeliyle arama yapılmaz. PUCT'deki c_puct ve öncül olasılıklar keşif dengesini belirler; LLM'de öncül token düzeyinde değil adım düzeyinde tanımlanmalıdır. Değer tahmini (value head ya da PRM) yanlıysa arama yanlışı büyütür; arama derinleştikçe doğrulayıcının istismar edilme riski artar. LLM'de aynı eylem farklı devamlar üretebilir ve durum geçişleri oyun kuralları gibi kesin değildir; AlphaZero'nun güvenceleri doğrudan taşınmaz.

Kaynaklar: [Silver vd. 2017 - Mastering Chess and Shogi by Self-Play with a General Reinforcement Learning Algorithm](https://arxiv.org/abs/1712.01815), [Anthony vd. 2017 - Thinking Fast and Slow with Deep Learning and Tree Search](https://arxiv.org/abs/1705.08439), [Hao vd. 2023 - Reasoning with Language Model is Planning with World Model](https://arxiv.org/abs/2305.14992).
:::

::: dusun
Sahnede bir araştırmacı el kaldırdı:
*"Hocam, `AlphaGo` ve `AlphaProof` (Lean 4) sistemlerinde `MCTS` muazzam çalışıyor; fakat genel açık uçlu sohbet veya doğal dilde matematik (`Natural Language Reasoning`) yürütürken `DeepSeek-R1` makalesinin yazarları çıkarım anında (`Inference-Time`) karmaşık `MCTS + Value Network` kullanmak yerine doğrudan tek bir uzun düşünce zinciri (`Long CoT` `<think>...</think>`) içinde modelin kendi kendine geri dönmesini (`In-Context Self-Correction`) tercih ettiler. Doğal dilde `MCTS` çalıştırmanın en büyük 2 zorluğu nedir?"*

Bu soruya **1) Doğal dilde eylem uzayının (`Action Space`) sonsuz olması ve birbirinin eşanlamlısı olan 10 farklı cümlenin ağacı gereksiz yere dallandırıp patlatması (`Semantic Duplication in Tree Branching`)** ve **2) Doğal dil ara adımlarını puanlayan bir `Process Reward Model (PRM)` / `Value Network` eğitirken modelin ödül ağını kandırması (`Reward Hacking`)** zorlukları üzerinden nasıl cevap verirsin?
:::

::: ozet
- **`Monte Carlo Tree Search (MCTS)`**, düşünce sürecini tek bir doğrusal zincir olmaktan çıkarıp ileriye dönük arama (`Lookahead Search`) ve çıkmaz dallardan geri dönme (`Backtracking`) yapabilen bir düşünce ağacına dönüştürür.
- **`Selection (PUCT)`**, $Q(s,a) + c_{\text{puct}} P(s,a) \frac{\sqrt{\sum_b N(s,b)}}{1 + N(s,a)}$ formülüyle bilinen en iyi yolu sömürme (**`Exploitation`**) ile dil modelinin önerdiği az ziyaret edilmiş yolları keşfetme (**`Exploration`**) arasında matematiksel denge kurar.
- **`Expansion`**, **`Evaluation` (`PRM / Value Network`)** ve **`Backpropagation`** ($N \leftarrow N+1, W \leftarrow W+v, Q = W/N$) adımlarıyla ağaç istatistikleri köke kadar güncellenir ve **`Expert Iteration`** ile model kendi kendinin öğretmeni olarak eğitilir.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Tek geçişli üretimden ağaç aramasına (30 sn).** "Zorlu ispat ve planlama sorularında tek bir otoregresif dalda yapılan erken bir mantık hatası tüm çözümü çökertir; `MCTS` alternatif düşünce adımlarını dallanan bir arama ağacı olarak keşfeder."
2. **`PUCT` sömürü-keşif dengesi (35 sn).** "Seçim aşamasında her dal için bugüne kadarki ortalama başarı değeri $Q(s,a)$ ile politika modelinin önsel olasılığı $P(s,a)$ ve az ziyaret edilmişlik çarpanı $\frac{\sqrt{N(s)}}{1 + N(s,a)}$ toplanarak hem umut vaat eden hem de henüz denenmemiş dallar dengelenir."
3. **Değerlendirme ve `Backpropagation` (30 sn).** "Yaprak düğümün kalitesi değer/süreç ödül modeliyle (`Value / PRM`) tahmin edilir ve elde edilen skor köke kadar tüm ata düğümlerin ziyaret sayısına ve toplam değerine geri yayılır."
4. **Soru (25 sn).** "Yaprakları puanlayan ödül modeli kusurluysa yüksek arama bütçesi (`daha fazla MCTS simülasyonu`) çözümü iyileştirir mi yoksa ödül istismarını (`reward hacking`) mı derinleştirir?"
:::
