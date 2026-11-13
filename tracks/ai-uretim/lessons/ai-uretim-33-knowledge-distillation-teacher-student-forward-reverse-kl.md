---
id: ai-uretim-33
title: "Knowledge Distillation: Teacher–Student ve Forward/Reverse KL"
summary: "671B parametreli öğretmen modelin (Teacher) karanlık bilgisini (Dark Knowledge) T sıcaklıklı Softmax, Forward KL (Mode-Covering), Reverse KL (MiniLLM Mode-Seeking) ve hibrit SFT kaybıyla küçük öğrenci modele (Student) damıtmak."
track: ai-uretim
order: 33
duration_minutes: 35
difficulty: orta
xp: 290
prerequisites: [ai-uretim-32]
esleme: ai-matematik-06, ai-uretim-10, ai-uretim-11
tags: [distillation, knowledge-distillation, kl-divergence, reverse-kl, minillm, teacher-student]
---

::: anlat
## Knowledge distillation

Teacher modelin dağılımı, yalnız en olası tokenı değil diğer adayların göreli skorlarını da taşır. Bu derste temperature, forward/reverse KL ve SFT ile birleşen distillation loss hesabını inceleyeceksin. Student modelin gerçek görev kalitesi bu loss sayısından tek başına belirlenmez.

Klasik Denetimli İnce Ayarda (`Supervised Fine-Tuning - SFT`), öğrenci modele yalnızca tek bir doğru token (`Hard Target / One-Hot`: ör. `"Paris" = 1.0`, diğer tüm `128,000` kelime `= 0.0`) gösterilir.
Oysa **Hinton et al. (2015 — `Distilling the Knowledge in a Neural Network`)** çok derin bir gerçeği ortaya koydu:
Bir öğretmen model `"Fransa'nın başkenti ..."` cümlesini tamamlarken yalnızca `"Paris"` kelimesine yüksek olasılık vermez; `"Lyon"` kelimesine `1e-3`, `"elma"` kelimesine ise `1e-9` olasılık verir! Yanlış cevapların kendi aralarındaki bu bağıl olasılık oranlarına **Karanlık Bilgi (`Dark Knowledge`)** denir ve öğretmenin kavramlar arasındaki anlamsal benzerlik haritasını taşır!

```
┌────────────────────────────────────────────────────────────────────────────┐
│       KNOWLEDGE DISTILLATION: DARK KNOWLEDGE & FORWARD vs REVERSE KL       │
├─────────────────────────────────────┬──────────────────────────────────────┤
│ 1. TEMPERATURE SCALING (T > 1)      │ 2. FORWARD KL vs REVERSE KL (MiniLLM)│
│ ─────────────────────────────────── │ ──────────────────────────────────── │
│ • T = 1.0 iken Softmax çok sivridir │ • Forward KL: D_KL(P_T || Q_T)       │
│   ([0.99, 0.009, 0.001]) -> Karanlık│   "Mode-Covering": Öğretmenin >0     │
│   bilgi sıfıra ezilir!              │   olduğu her yeri kapsamaya çalışır; │
│ • Logitleri T (ör. T=2.0..4.0) ile  │   iki tepe ortasındaki boşluğa       │
│   böldüğümüzde dağılım yumuşar:     │   olasılık atayıp halüsinasyon yapar!│
│   p_i^(T) = exp(z_i/T) / Σ exp(z/T) │ • Reverse KL: D_KL(Q_T || P_T)       │
│ • Gradyan büyüklüğü 1/T^2 oranında  │   "Mode-Seeking": Öğrenci kapasitesi │
│   küçüldüğü için kayıp T^2 ile      │   yetmediğinde öğretmenin EN GÜÇLÜ   │
│   çarpılarak dengelenir!            │   tepesine odaklanır, boşluğa düşmez!│
└─────────────────────────────────────┴──────────────────────────────────────┘
```

---

### 1. Sıcaklık Ölçekli (`Temperature-Scaled`) Softmax ve $T^2$ Çarpanı

Öğretmen modelin logit vektörü $z^{(t)} \in \mathbb{R}^V$ ve öğrenci modelin logit vektörü $z^{(s)} \in \mathbb{R}^V$ olsun. Sıcaklık $T > 0$ ile yumuşatılmış olasılık dağılımları ($P_T$ ve $Q_T$):

$$P_T(i) = \frac{\exp(z_i^{(t)} / T)}{\sum_{j=1}^V \exp(z_j^{(t)} / T)}, \qquad Q_T(i) = \frac{\exp(z_i^{(s)} / T)}{\sum_{j=1}^V \exp(z_j^{(s)} / T)}$$

Logitler $T$'ye bölündüğünde, `KL Divergence` kaybının öğrenci logitlerine ($z^{(s)}$) göre türevi yüksek $T$ limitinde $1/T^2$ ile ölçeklenir. Hibrit kayıpta gerçek etiket (`Cross-Entropy`) gradyanlarıyla aynı büyüklük mertebesinde kalması için distillation kaybı **$T^2$ ile çarpılır**:

$$\mathcal{L}_{\text{KD}} = (1 - \alpha) \cdot \mathcal{L}_{\text{CE}}(y, Q_{T=1}) + \alpha \cdot T^2 \cdot D_{\text{KL}}(P_T, Q_T)$$

---

### 2. Üretken LLM'lerde `Forward KL` vs `Reverse KL` (`MiniLLM`, Gu et al. ICLR 2024)

Sınıflandırma modellerinde klasik `Forward KL` kullanılırken, açık uçlu metin üreten LLM'lerde (`Generative LLMs`) iki yön arasında hayati bir fark vardır:

1. **`Forward KL` ($D_{\text{KL}}(P_T \| Q_T)$ — `Mode-Covering / Mean-Seeking`):**
   $$D_{\text{KL}}(P_T \| Q_T) = \sum_{i=1}^V P_T(i) \log \frac{P_T(i)}{Q_T(i)}$$
   Burada $P_T(i) > 0$ olan herhangi bir tokenda öğrenci $Q_T(i) \to 0$ verirse $\log(P_T / Q_T) \to \infty$ olur! Bu yüzden küçük öğrenci model, öğretmenin olasılık verdiği **tüm modları (farklı geçerli yanıt tarzlarını) aynı anda kapsamaya** zorlanır. Kapasitesi yetmediğinde iki uzak modun tam ortasındaki **düşük olasılıklı (anlamsız/halüsinasyon) bölgeye** kütle atar!

2. **`Reverse KL` ($D_{\text{KL}}(Q_T \| P_T)$ — `Mode-Seeking`):**
   $$D_{\text{KL}}(Q_T \| P_T) = \sum_{i=1}^V Q_T(i) \log \frac{Q_T(i)}{P_T(i)}$$
   Burada ise öğretmenin $P_T(i) \approx 0$ dediği bir tokenda öğrenci $Q_T(i) > 0$ verirse sonsuz ceza yer! Buna karşılık öğretmenin bir modunu tamamen es geçmenin cezası sınırlıdır. Böylece öğrenci model tüm olası cevapları yarım yamalak ezberlemek yerine, **öğretmenin en emin olduğu ana tepeye (`Mode-Seeking`) odaklanır** ve çok daha keskin, halüsinasyonsuz metin üretir!

```python
import math

# İki modlu (Bimodal) bir öğretmen dağılımı P: 0. ve 2. tokenlar doğru yanıt, ortadaki 1. token ise YANLIŞ (boşluk)!
P = [0.495, 0.010, 0.495]

# Geniş/Yayvan Öğrenci (Q_yayvan: iki modu birden kapsamaya çalışırken ortadaki yanlış tokena 0.30 veriyor)
Q_yayvan = [0.35, 0.30, 0.35]

# Odaklı Öğrenci (Q_odakli: sadece 0. moda odaklanıyor, yanlış olan 1. tokena 0.005 veriyor)
Q_odakli = [0.98, 0.005, 0.015]

def kl_hesapla(p_dist, q_dist):
    return sum(pi * math.log(pi / qi) for pi, qi in zip(p_dist, q_dist) if pi > 0)

print(f"Forward KL(P || Q_yayvan) = {kl_hesapla(P, Q_yayvan):.4f} vs Forward KL(P || Q_odakli) = {kl_hesapla(P, Q_odakli):.4f}")
print(f"Reverse KL(Q_yayvan || P) = {kl_hesapla(Q_yayvan, P):.4f} vs Reverse KL(Q_odakli || P) = {kl_hesapla(Q_odakli, P):.4f}")
```

---

### 3. Gerçek PyTorch Üretim Kodu: `DistillationTrainerLoss`

Gerçek bir `DeepSeek-R1-Distill` veya `MiniLLM` eğitim döngüsünde `Forward / Reverse KL` ve `Hard-Label CE` kaybını birleştiren PyTorch modülü:

```python norun
import torch
import torch.nn as nn
import torch.nn.functional as F

class LLMKnowledgeDistillationLoss(nn.Module):
    def __init__(self, temperature: float = 2.0, alpha: float = 0.5, mode: str = "reverse_kl"):
        super().__init__()
        self.T = temperature
        self.alpha = alpha
        self.mode = mode

    def forward(
        self,
        student_logits: torch.Tensor,  # (Batch, SeqLen, VocabSize)
        teacher_logits: torch.Tensor,  # (Batch, SeqLen, VocabSize)
        labels: torch.Tensor,          # (Batch, SeqLen)
    ) -> torch.Tensor:
        # 1. Standart SFT Cross-Entropy Kaybı (T = 1.0)
        ce_loss = F.cross_entropy(
            student_logits.view(-1, student_logits.size(-1)),
            labels.view(-1),
            ignore_index=-100,
        )

        # 2. Sıcaklık Ölçekli Log-Olasılıklar
        log_p = F.log_softmax(teacher_logits / self.T, dim=-1)
        log_q = F.log_softmax(student_logits / self.T, dim=-1)
        p = log_p.exp()
        q = log_q.exp()

        if self.mode == "forward_kl":
            kl_per_token = (p * (log_p - log_q)).sum(dim=-1)
        else:  # reverse_kl: D_KL(Q || P)
            kl_per_token = (q * (log_q - log_p)).sum(dim=-1)

        mask = (labels != -100).float()
        kd_loss = (kl_per_token * mask).sum() / mask.sum().clamp(min=1.0)
        return (1.0 - self.alpha) * ce_loss + self.alpha * (self.T ** 2) * kd_loss
```

**Uygulama sınırı:** Görevler Python ile küçük, denetlenebilir hesaplar yapar. `python norun` blokları PyTorch/GPU tarafını incelemek içindir; bu tezgâhta otomatik çalıştırılıp gerçek training/serving kabulü yapılmaz.

**Birincil kaynak:** [Knowledge distillation makalesi](https://arxiv.org/abs/1503.02531). Kaynak, yöntemin ayrıntıları içindir; dersteki küçük örnek ölçülmüş üretim benchmarkı değildir.
:::

::: tahmin Sıcaklık T Artışı ve Karanlık Bilgi (Dark Knowledge) Olasılığı
Öğretmen modelin 3 kelimelik bir sözlükteki logitleri $z^{(t)} = [4.0, \; 2.0, \; 0.0]$ olarak veriliyor.
1. Sıcaklık $T = 1.0$ iken ikinci en olası tokenın ($z_1 = 2.0$) softmax olasılığı kaçtır?
2. Sıcaklık $T = 2.0$ yapıldığında aynı ikinci tokenın yumuşatılmış olasılığı $P_{T=2}(1)$ kaç katına çıkar?

```python
import math

z = [4.0, 2.0, 0.0]

def yumusak_softmax(logitler, T):
    exps = [math.exp(v / T) for v in logitler]
    toplam = sum(exps)
    return [e / toplam for e in exps]

p_t1 = yumusak_softmax(z, 1.0)
p_t2 = yumusak_softmax(z, 2.0)

print(f"T=1.0 -> P(1) = {p_t1[1]:.4f}")
print(f"T=2.0 -> P(1) = {p_t2[1]:.4f} (Artis: {p_t2[1] / p_t1[1]:.2f}x)")
```

???

```cikti
T=1.0 -> P(1) = 0.1173
T=2.0 -> P(1) = 0.2447 (Artis: 2.09x)
```
$T = 1.0$ iken $P(1) = e^2 / (e^4 + e^2 + 1) \approx 0.1173$ (%11.7) seviyesindedir. Sıcaklık $T = 2.0$'a çıkarıldığında ölçeklenmiş logitler $[2.0, 1.0, 0.0]$ olur ve $P_{T=2}(1) = e^1 / (e^2 + e^1 + 1) \approx 0.2447$ (%24.5) seviyesine, yani **2.09 katına** çıkar! Böylece öğrenci model ikinci alternatifin üçüncüden çok daha makul olduğunu net bir gradyan sinyaliyle öğrenir.
:::

::: gorev 1 · Sıcaklık Ölçekli (Temperature-Scaled) Forward KL ve Reverse KL distillation Kaybı
Öğretmen logitleri (`ogretmen_logit`), öğrenci logitleri (`ogrenci_logit`) ve sıcaklık (`sicaklik_T`) verildiğinde yumuşatılmış dağılımları ($P_T, Q_T$) ve $T^2$ ile ölçeklenmiş `Forward KL` ($T^2 D_{\text{KL}}(P_T \| Q_T)$) veya `Reverse KL` ($T^2 D_{\text{KL}}(Q_T \| P_T)$) distillation kaybını hesaplayan `damitma_kl_kaybi(ogretmen_logit, ogrenci_logit, sicaklik_T, mod)` işlevini yaz.

**Girdi Kuralları ve Doğrulama:**
- `ogretmen_logit`, `ogrenci_logit`: Aynı uzunlukta ($V \ge 2$) sayı listeleri (`list[float]`). Tüm elemanlar `bool` olmayan sonlu sayı olmalıdır.
- `sicaklik_T`: Sıcaklık parametresi $T$ (`bool` olmayan sonlu sayı, $T > 0$).
- `mod`: `"forward"` veya `"reverse"` dizgisi (`str`).

**Hesaplama Kuralları:**
1. Her iki logit vektörünü $T$ (`sicaklik_T`) ile böl ve sayısal kararlı softmax ($\max$ çıkararak) ile $P_T$ (`ogretmen_olasilik`) ve $Q_T$ (`ogrenci_olasilik`) dağılımlarını hesapla:
   $$\log P_T(i) = \frac{z_i^{(t)}}{T} - \log \sum_{j=0}^{V-1} \exp\left(\frac{z_j^{(t)}}{T}\right), \qquad P_T(i) = \exp(\log P_T(i))$$
2. Seçilen `mod` değerine göre ham `KL Divergence` hesapla:
   - `mod == "forward"` ise:
     $$D_{\text{KL}} = \sum_{i=0}^{V-1} P_T(i) \cdot (\log P_T(i) - \log Q_T(i))$$
   - `mod == "reverse"` ise:
     $$D_{\text{KL}} = \sum_{i=0}^{V-1} Q_T(i) \cdot (\log Q_T(i) - \log P_T(i))$$
3. Sıcaklık dengeli distillation kaybı: `olcekli_kayip = (T ** 2) * D_KL`.
4. İşlev şu sözlüğü döndürmelidir:
   `{"ham_kl": float, "olcekli_kayip": float, "ogretmen_olasilik": list[float], "ogrenci_olasilik": list[float]}`
- Geçersiz herhangi bir girdide `ValueError` yükseltilmelidir.

```starter
import math

# KUSURLU BAŞLANGIÇ KODU: T^2 ölçeklemesini yapmıyor ve Reverse KL modunu desteklemiyor!
def damitma_kl_kaybi(ogretmen_logit, ogrenci_logit, sicaklik_T, mod):
    ex_p = [math.exp(z / sicaklik_T) for z in ogretmen_logit]
    ex_q = [math.exp(z / sicaklik_T) for z in ogrenci_logit]
    sp, sq = sum(ex_p), sum(ex_q)
    P = [v / sp for v in ex_p]
    Q = [v / sq for v in ex_q]
    kl = sum(pi * math.log(pi / qi) for pi, qi in zip(P, Q))
    return {
        "ham_kl": kl,
        "olcekli_kayip": kl,
        "ogretmen_olasilik": P,
        "ogrenci_olasilik": Q,
    }

if __name__ == "__main__":
    z_t = [4.0, 2.0, 0.0]
    z_s = [2.0, 2.0, 1.0]
    print("Forward:", damitma_kl_kaybi(z_t, z_s, sicaklik_T=2.0, mod="forward"))
    print("Reverse:", damitma_kl_kaybi(z_t, z_s, sicaklik_T=2.0, mod="reverse"))
```
```test
def sinama_kd1(f):
    import copy, math, random
    def _log_softmax(z, T):
        s = [float(v) / float(T) for v in z]
        m = max(s)
        lse = m + math.log(sum(math.exp(v - m) for v in s))
        lp = [v - lse for v in s]
        p = [math.exp(v) for v in lp]
        return lp, p
    def _ref(zt, zs, T, mod):
        lpt, pt = _log_softmax(zt, T)
        lps, ps = _log_softmax(zs, T)
        if mod == "forward":
            kl = sum(p * (lp - lq) for p, lp, lq in zip(pt, lpt, lps))
        else:
            kl = sum(q * (lq - lp) for q, lq, lp in zip(ps, lps, lpt))
        return {"ham_kl": kl, "olcekli_kayip": (float(T) ** 2) * kl, "ogretmen_olasilik": pt, "ogrenci_olasilik": ps}
    def _yakin(a, b):
        keys = {"ham_kl", "olcekli_kayip", "ogretmen_olasilik", "ogrenci_olasilik"}
        if not isinstance(a, dict) or set(a.keys()) != keys:
            return False
        if abs(a["ham_kl"] - b["ham_kl"]) > 1e-10 or abs(a["olcekli_kayip"] - b["olcekli_kayip"]) > 1e-10:
            return False
        for k in ("ogretmen_olasilik", "ogrenci_olasilik"):
            if not isinstance(a[k], list) or len(a[k]) != len(b[k]) or any(abs(u - v) > 1e-10 for u, v in zip(a[k], b[k])):
                return False
        return True
    try:
        zt, zs = [4.0, 2.0, 0.0], [2.0, 2.0, 1.0]
        old = (copy.deepcopy(zt), copy.deepcopy(zs))
        o_fwd = f(zt, zs, 2.0, "forward")
        o_rev = f(zt, zs, 2.0, "reverse")
        if (zt, zs) != old or not _yakin(o_fwd, _ref(zt, zs, 2.0, "forward")) or not _yakin(o_rev, _ref(zt, zs, 2.0, "reverse")):
            return False
        if abs(o_fwd["ham_kl"] - o_rev["ham_kl"]) < 1e-6:
            return False

        # Büyük logitlerde sayısal kararlılık testi
        if not _yakin(f([1000.0, 998.0], [999.0, 999.0], 2.0, "forward"), _ref([1000.0, 998.0], [999.0, 999.0], 2.0, "forward")):
            return False

        rng = random.Random(3301)
        for _ in range(20):
            v = rng.randint(2, 6)
            tt = [rng.uniform(-5.0, 5.0) for _ in range(v)]
            ss = [rng.uniform(-5.0, 5.0) for _ in range(v)]
            T = rng.uniform(0.5, 4.0)
            for m in ("forward", "reverse"):
                if not _yakin(f(tt, ss, T, m), _ref(tt, ss, T, m)):
                    return False

        bad_cases = [
            ([], [], 1.0, "forward"),
            ([1.0], [1.0], 1.0, "forward"),
            ([1.0, 2.0], [1.0], 1.0, "forward"),
            (zt, zs, 0.0, "forward"),
            (zt, zs, -1.0, "forward"),
            (zt, zs, 1.0, "yanlis_mod"),
            (zt, zs, True, "forward"),
            ([1.0, float("nan")], [1.0, 2.0], 1.0, "forward"),
        ]
        for bt, bs, bT, bm in bad_cases:
            try:
                f(bt, bs, bT, bm)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

damitma_kl_kaybi = need("damitma_kl_kaybi")
ok(sinama_kd1(damitma_kl_kaybi), "Sıcaklık ölçekli kararlı Softmax, Forward/Reverse KL ve T^2 ölçekleme")
for ad, mut in [
    ("T^2 ile çarpmayan", lambda zt, zs, t, m: dict(damitma_kl_kaybi(zt, zs, t, m), olcekli_kayip=damitma_kl_kaybi(zt, zs, t, m)["ham_kl"])),
    ("hep forward hesaplayan", lambda zt, zs, t, m: damitma_kl_kaybi(zt, zs, t, "forward")),
]:
    ok(not sinama_kd1(mut), "mutant reddedildi: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile('import math\n\ndef _sayi_mi(v):\n    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)\n\ndef _log_softmax_sicaklik(logitler, T):\n    olcekli = [float(z) / float(T) for z in logitler]\n    m = max(olcekli)\n    lse = m + math.log(sum((math.exp(v - m) for v in olcekli)))\n    log_p = [v - lse for v in olcekli]\n    p = [math.exp(v) for v in log_p]\n    return (log_p, p)\n\ndef damitma_kl_kaybi(ogretmen_logit, ogrenci_logit, sicaklik_T, mod):\n    if not isinstance(ogretmen_logit, list) or not isinstance(ogrenci_logit, list) or len(ogretmen_logit) < 2 or (len(ogretmen_logit) != len(ogrenci_logit)):\n        raise ValueError(\'logit listeleri eşit uzunlukta (>= 2) olmalı\')\n    if not all((_sayi_mi(v) for v in ogretmen_logit)) or not all((_sayi_mi(v) for v in ogrenci_logit)):\n        raise ValueError(\'logit elemanları sonlu sayı olmalı\')\n    if not _sayi_mi(sicaklik_T) or float(sicaklik_T) <= 0.0:\n        raise ValueError(\'sicaklik_T > 0 olmalı\')\n    if mod not in (\'forward\', \'reverse\'):\n        raise ValueError("mod \'forward\' veya \'reverse\' olmalı")\n    T = float(sicaklik_T)\n    log_p, p = _log_softmax_sicaklik(ogretmen_logit, T)\n    log_q, q = _log_softmax_sicaklik(ogrenci_logit, T)\n    if mod == \'forward\':\n        ham_kl = sum((pi * (lpi - lqi) for pi, lpi, lqi in zip(p, log_p, log_q)))\n    else:\n        ham_kl = sum((qi * (lqi - lpi) for qi, lqi, lpi in zip(q, log_q, log_p)))\n    return {\'ham_kl\': ham_kl, \'olcekli_kayip\': T * T * ham_kl, \'ogretmen_olasilik\': p, \'ogrenci_olasilik\': q}', 'referans', 'exec'), _REF)
_t, _g = _ff(damitma_kl_kaybi, _REF['damitma_kl_kaybi'], ([4.0, 2.0, 0.0], [2.0, 2.0, 1.0], 2.0, 'forward'), tohum=2722, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (damitma_kl_kaybi): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math

def _sayi_mi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)

def _log_softmax_sicaklik(logitler, T):
    olcekli = [float(z) / float(T) for z in logitler]
    m = max(olcekli)
    lse = m + math.log(sum(math.exp(v - m) for v in olcekli))
    log_p = [v - lse for v in olcekli]
    p = [math.exp(v) for v in log_p]
    return log_p, p

def damitma_kl_kaybi(ogretmen_logit, ogrenci_logit, sicaklik_T, mod):
    if not isinstance(ogretmen_logit, list) or not isinstance(ogrenci_logit, list) or len(ogretmen_logit) < 2 or len(ogretmen_logit) != len(ogrenci_logit):
        raise ValueError("logit listeleri eşit uzunlukta (>= 2) olmalı")
    if not all(_sayi_mi(v) for v in ogretmen_logit) or not all(_sayi_mi(v) for v in ogrenci_logit):
        raise ValueError("logit elemanları sonlu sayı olmalı")
    if not _sayi_mi(sicaklik_T) or float(sicaklik_T) <= 0.0:
        raise ValueError("sicaklik_T > 0 olmalı")
    if mod not in ("forward", "reverse"):
        raise ValueError("mod 'forward' veya 'reverse' olmalı")

    T = float(sicaklik_T)
    log_p, p = _log_softmax_sicaklik(ogretmen_logit, T)
    log_q, q = _log_softmax_sicaklik(ogrenci_logit, T)

    if mod == "forward":
        ham_kl = sum(pi * (lpi - lqi) for pi, lpi, lqi in zip(p, log_p, log_q))
    else:
        ham_kl = sum(qi * (lqi - lpi) for qi, lqi, lpi in zip(q, log_q, log_p))

    return {
        "ham_kl": ham_kl,
        "olcekli_kayip": (T * T) * ham_kl,
        "ogretmen_olasilik": p,
        "ogrenci_olasilik": q,
    }

if __name__ == "__main__":
    z_t = [4.0, 2.0, 0.0]
    z_s = [2.0, 2.0, 1.0]
    print("Forward:", damitma_kl_kaybi(z_t, z_s, sicaklik_T=2.0, mod="forward"))
    print("Reverse:", damitma_kl_kaybi(z_t, z_s, sicaklik_T=2.0, mod="reverse"))
```
```hint
Logitleri $T$'ye böldükten sonra `m = max(olcekli)` çıkararak kararlı `log_p` ve `p` vektörlerini üret. `forward` modunda $\sum p_i (\log p_i - \log q_i)$, `reverse` modunda ise $\sum q_i (\log q_i - \log p_i)$ hesaplayıp $T^2$ ile çarp.
```
:::

::: gorev 2 · Hibrit SFT + Distillation Kaybı ve Karanlık Bilgi (Dark Knowledge) Entropi Analizi
Bir eğitim adımında gerçek hedef token (`gercek_hedef_id`) üzerinden hesaplanan standart $T=1$ `Cross-Entropy` kaybı ile $T$ sıcaklıklı `Forward KL` distillation kaybını birleştiren ve öğretmenin hedef dışındaki tokenlara verdiği **Karanlık Bilgi Kütlesini (`dark_knowledge_kutlesi`)** ölçen `hibrit_damitma_adimi(ogretmen_logit, ogrenci_logit, gercek_hedef_id, sicaklik_T, alpha_ce)` işlevini yaz.

**Girdi Kuralları ve Doğrulama:**
- `ogretmen_logit`, `ogrenci_logit`: Aynı uzunlukta ($V \ge 2$) sonlu sayı listeleri.
- `gercek_hedef_id`: Doğru token indisi (`bool` olmayan `int`, $0 \le \text{gercek\_hedef\_id} < V$).
- `sicaklik_T`: Sıcaklık $T$ (`bool` olmayan sonlu sayı, $T > 0$).
- `alpha_ce`: Gerçek etiket `Cross-Entropy` ağırlığı $\alpha_{\text{ce}}$ (`bool` olmayan sonlu sayı, $0.0 \le \alpha_{\text{ce}} \le 1.0$).

**Hesaplama Kuralları:**
1. **Standart SFT Kaybı (`ce_kaybi`):** Öğrenci logitlerinde $T = 1.0$ için `gercek_hedef_id` tokenının negatif log-olasılığı:
   $$\mathcal{L}_{\text{CE}} = -\log Q_{T=1}(\text{gercek\_hedef\_id})$$
2. **Ölçekli distillation Kaybı (`kd_kaybi`):** $T = \text{sicaklik\_T}$ sıcaklığında $T^2 \cdot D_{\text{KL}}(P_T \| Q_T)$.
3. **Toplam Hibrit Kayıp (`toplam_kayip`):**
   $$\mathcal{L}_{\text{toplam}} = \alpha_{\text{ce}} \cdot \mathcal{L}_{\text{CE}} + (1.0 - \alpha_{\text{ce}}) \cdot \mathcal{L}_{\text{KD}}$$
4. **Karanlık Bilgi Kütlesi (`karanlik_bilgi_kutlesi`):** Öğretmenin yumuşatılmış $P_T$ dağılımında `gercek_hedef_id` **dışındaki** tüm tokenların toplam olasılığı ($1.0 - P_T(\text{gercek\_hedef\_id})$).
5. İşlev şu sözlüğü döndürmelidir:
   `{"ce_kaybi": float, "kd_kaybi": float, "toplam_kayip": float, "karanlik_bilgi_kutlesi": float}`
- Geçersiz herhangi bir girdide `ValueError` yükseltilmelidir.

```starter
import math

# KUSURLU BAŞLANGIÇ KODU: CE kaybını da T sıcaklığıyla hesaplıyor ve karanlık bilgi kütlesini 0 döndürüyor!
def hibrit_damitma_adimi(ogretmen_logit, ogrenci_logit, gercek_hedef_id, sicaklik_T, alpha_ce):
    ex_q = [math.exp(z / sicaklik_T) for z in ogrenci_logit]
    q_t = [v / sum(ex_q) for v in ex_q]
    ce = -math.log(q_t[gercek_hedef_id])
    return {
        "ce_kaybi": ce,
        "kd_kaybi": 0.0,
        "toplam_kayip": ce,
        "karanlik_bilgi_kutlesi": 0.0,
    }

if __name__ == "__main__":
    print(hibrit_damitma_adimi([5.0, 2.5, 0.5], [2.0, 1.5, 0.5], gercek_hedef_id=0, sicaklik_T=2.0, alpha_ce=0.3))
```
```test
def sinama_kd2(f):
    import copy, math, random
    def _lsm(z, T):
        s = [float(v) / float(T) for v in z]
        m = max(s)
        lse = m + math.log(sum(math.exp(v - m) for v in s))
        lp = [v - lse for v in s]
        return lp, [math.exp(v) for v in lp]
    def _ref(zt, zs, y, T, a):
        lp1, _ = _lsm(zs, 1.0)
        ce = -lp1[y]
        lpt, pt = _lsm(zt, T)
        lps, _ = _lsm(zs, T)
        kd = (float(T) ** 2) * sum(p * (lp - lq) for p, lp, lq in zip(pt, lpt, lps))
        top = float(a) * ce + (1.0 - float(a)) * kd
        dark = sum(pt[i] for i in range(len(pt)) if i != y)
        return {"ce_kaybi": ce, "kd_kaybi": kd, "toplam_kayip": top, "karanlik_bilgi_kutlesi": dark}
    def _yakin(a, b):
        keys = {"ce_kaybi", "kd_kaybi", "toplam_kayip", "karanlik_bilgi_kutlesi"}
        if not isinstance(a, dict) or set(a.keys()) != keys:
            return False
        return all(abs(a[k] - b[k]) <= 1e-10 for k in keys)
    try:
        zt, zs = [5.0, 2.5, 0.5], [2.0, 1.5, 0.5]
        old = (copy.deepcopy(zt), copy.deepcopy(zs))
        out = f(zt, zs, 0, 2.0, 0.3)
        if (zt, zs) != old or not _yakin(out, _ref(zt, zs, 0, 2.0, 0.3)):
            return False

        rng = random.Random(3302)
        for _ in range(20):
            v = rng.randint(2, 6)
            tt = [rng.uniform(-4.0, 6.0) for _ in range(v)]
            ss = [rng.uniform(-4.0, 6.0) for _ in range(v)]
            y = rng.randint(0, v - 1)
            T = rng.uniform(1.0, 4.0)
            al = rng.uniform(0.0, 1.0)
            if not _yakin(f(tt, ss, y, T, al), _ref(tt, ss, y, T, al)):
                return False

        bad_cases = [
            ([1.0], [1.0], 0, 2.0, 0.5),
            (zt, zs, -1, 2.0, 0.5),
            (zt, zs, 3, 2.0, 0.5),
            (zt, zs, True, 2.0, 0.5),
            (zt, zs, 0, 0.0, 0.5),
            (zt, zs, 0, 2.0, -0.1),
            (zt, zs, 0, 2.0, 1.1),
            (zt, zs, 0, 2.0, False),
        ]
        for bt, bs, by, bT, ba in bad_cases:
            try:
                f(bt, bs, by, bT, ba)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

hibrit_damitma_adimi = need("hibrit_damitma_adimi")
ok(sinama_kd2(hibrit_damitma_adimi), "T=1 CE kaybı, T ölçekli KD kaybı ve karanlık bilgi kütlesi hesabı")
for ad, mut in [
    ("CE kaybında T kullanan", lambda zt, zs, y, t, a: dict(hibrit_damitma_adimi(zt, zs, y, t, a), ce_kaybi=hibrit_damitma_adimi(zt, zs, y, t, a)["ce_kaybi"] / t)),
    ("karanlık bilgiyi sıfırlayan", lambda zt, zs, y, t, a: dict(hibrit_damitma_adimi(zt, zs, y, t, a), karanlik_bilgi_kutlesi=0.0)),
]:
    ok(not sinama_kd2(mut), "mutant reddedildi: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef _sayi_mi(v):\n    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)\n\ndef _log_softmax_sicaklik(logitler, T):\n    olcekli = [float(z) / float(T) for z in logitler]\n    m = max(olcekli)\n    lse = m + math.log(sum((math.exp(v - m) for v in olcekli)))\n    log_p = [v - lse for v in olcekli]\n    p = [math.exp(v) for v in log_p]\n    return (log_p, p)\n\ndef hibrit_damitma_adimi(ogretmen_logit, ogrenci_logit, gercek_hedef_id, sicaklik_T, alpha_ce):\n    if not isinstance(ogretmen_logit, list) or not isinstance(ogrenci_logit, list) or len(ogretmen_logit) < 2 or (len(ogretmen_logit) != len(ogrenci_logit)):\n        raise ValueError('logit listeleri eşit uzunlukta (>= 2) olmalı')\n    if not all((_sayi_mi(v) for v in ogretmen_logit)) or not all((_sayi_mi(v) for v in ogrenci_logit)):\n        raise ValueError('logit elemanları sonlu sayı olmalı')\n    V = len(ogretmen_logit)\n    if isinstance(gercek_hedef_id, bool) or not isinstance(gercek_hedef_id, int) or (not 0 <= gercek_hedef_id < V):\n        raise ValueError('geçersiz gercek_hedef_id')\n    if not _sayi_mi(sicaklik_T) or float(sicaklik_T) <= 0.0:\n        raise ValueError('sicaklik_T > 0 olmalı')\n    if not _sayi_mi(alpha_ce) or not 0.0 <= float(alpha_ce) <= 1.0:\n        raise ValueError('alpha_ce [0, 1] aralığında olmalı')\n    T = float(sicaklik_T)\n    a = float(alpha_ce)\n    log_q_t1, _ = _log_softmax_sicaklik(ogrenci_logit, 1.0)\n    ce_kaybi = -log_q_t1[gercek_hedef_id]\n    log_p_t, p_t = _log_softmax_sicaklik(ogretmen_logit, T)\n    log_q_t, _ = _log_softmax_sicaklik(ogrenci_logit, T)\n    kd_kaybi = T * T * sum((pi * (lpi - lqi) for pi, lpi, lqi in zip(p_t, log_p_t, log_q_t)))\n    toplam_kayip = a * ce_kaybi + (1.0 - a) * kd_kaybi\n    karanlik_kutle = sum((p_t[i] for i in range(V) if i != gercek_hedef_id))\n    return {'ce_kaybi': ce_kaybi, 'kd_kaybi': kd_kaybi, 'toplam_kayip': toplam_kayip, 'karanlik_bilgi_kutlesi': karanlik_kutle}", 'referans', 'exec'), _REF)
_t, _g = _ff(hibrit_damitma_adimi, _REF['hibrit_damitma_adimi'], ([5.0, 2.5, 0.5], [2.0, 1.5, 0.5], 0, 2.0, 0.3), tohum=3137, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (hibrit_damitma_adimi): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math

def _sayi_mi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)

def _log_softmax_sicaklik(logitler, T):
    olcekli = [float(z) / float(T) for z in logitler]
    m = max(olcekli)
    lse = m + math.log(sum(math.exp(v - m) for v in olcekli))
    log_p = [v - lse for v in olcekli]
    p = [math.exp(v) for v in log_p]
    return log_p, p

def hibrit_damitma_adimi(ogretmen_logit, ogrenci_logit, gercek_hedef_id, sicaklik_T, alpha_ce):
    if not isinstance(ogretmen_logit, list) or not isinstance(ogrenci_logit, list) or len(ogretmen_logit) < 2 or len(ogretmen_logit) != len(ogrenci_logit):
        raise ValueError("logit listeleri eşit uzunlukta (>= 2) olmalı")
    if not all(_sayi_mi(v) for v in ogretmen_logit) or not all(_sayi_mi(v) for v in ogrenci_logit):
        raise ValueError("logit elemanları sonlu sayı olmalı")
    V = len(ogretmen_logit)
    if isinstance(gercek_hedef_id, bool) or not isinstance(gercek_hedef_id, int) or not (0 <= gercek_hedef_id < V):
        raise ValueError("geçersiz gercek_hedef_id")
    if not _sayi_mi(sicaklik_T) or float(sicaklik_T) <= 0.0:
        raise ValueError("sicaklik_T > 0 olmalı")
    if not _sayi_mi(alpha_ce) or not (0.0 <= float(alpha_ce) <= 1.0):
        raise ValueError("alpha_ce [0, 1] aralığında olmalı")

    T = float(sicaklik_T)
    a = float(alpha_ce)

    log_q_t1, _ = _log_softmax_sicaklik(ogrenci_logit, 1.0)
    ce_kaybi = -log_q_t1[gercek_hedef_id]

    log_p_t, p_t = _log_softmax_sicaklik(ogretmen_logit, T)
    log_q_t, _ = _log_softmax_sicaklik(ogrenci_logit, T)

    kd_kaybi = (T * T) * sum(pi * (lpi - lqi) for pi, lpi, lqi in zip(p_t, log_p_t, log_q_t))
    toplam_kayip = a * ce_kaybi + (1.0 - a) * kd_kaybi
    karanlik_kutle = sum(p_t[i] for i in range(V) if i != gercek_hedef_id)

    return {
        "ce_kaybi": ce_kaybi,
        "kd_kaybi": kd_kaybi,
        "toplam_kayip": toplam_kayip,
        "karanlik_bilgi_kutlesi": karanlik_kutle,
    }

if __name__ == "__main__":
    print(hibrit_damitma_adimi([5.0, 2.5, 0.5], [2.0, 1.5, 0.5], gercek_hedef_id=0, sicaklik_T=2.0, alpha_ce=0.3))
```
```hint
`ce_kaybi` için `ogrenci_logit` üzerinde $T=1.0$ ile negatif log-olasılığı al. `kd_kaybi` için $T = \text{sicaklik\_T}$ kullan ve `karanlik_bilgi_kutlesi` için $P_T$ içindeki `i != gercek_hedef_id` olasılıklarını topla.
```
:::

::: anlat Gerçek deney: SmolLM2-Instruct'tan SmolLM2'ye gerçek damıtma
Final gerçek bir öğretmen–öğrenci çifti kullanır (indirme yok, CPU): öğretmen **SmolLM2-135M-Instruct**, öğrenci **SmolLM2-135M** (base). İkisi aynı sözlüğü (49 152 token) paylaşır, bu yüzden logit düzeyinde damıtma doğrudan yapılabilir.

- **Öğrencinin işlevleri:** öğretmenin gerçek bir yanıtındaki bir konumda iki modelin 49 152'lik logit vektörleri alınır. Senin `damitma_kl_kaybi` işlevin ileri ve ters KL'yi ($T = 2$), `hibrit_damitma_adimi` işlevin CE + KD karışımını hesaplar; sonuçlar torch'un `kl_div` ve `cross_entropy` değerleriyle karşılaştırılır.
- **Karanlık bilgi:** öğretmenin hedef dışı olasılık kütlesi $T = 1, 2, 4$ için ölçülür. $T = 1$'de neredeyse sıfırdır; sıcaklık arttıkça öğretmenin "yanlış ama makul" tokenlara verdiği bilgi görünür olur.
- **Kısa gerçek damıtma:** 8 güvenlik sorusuna öğretmenin greedy yanıtları üretilir. Öğrencinin son 4 katmanı 30 adım üç yolla eğitilir: (a) öğretmenin yanıt tokenlarıyla sert etiketli SFT, (b) ileri KL damıtması, (c) ters KL damıtması. Ayrılmış 3 soruda öğrencinin öğretmene KL'si ve top-1 uyumu ölçülür.

Kabul: iki işlevin farksal taramayı geçmesi; KL ve hibrit kaybın gerçek dağılımlarda torch ile aynı olması; karanlık bilgi kütlesinin sıcaklıkla artması; damıtmanın öğrenciyi eğitimsiz hâline göre öğretmene yaklaştırması ve ileri KL damıtmasının sert etiketli SFT'den iyi olması.

**Kanıt dosyasını oku:** `karanlik_bilgi`, `egitim` (dört durumun KL'si ve top-1 uyumu). Soru 1: Sert etiketli SFT aynı adımda öğrenciyi öğretmenden neden uzaklaştırdı? Soru 2: Ters KL'nin top-1 uyumu ileri KL'ye göre nasıl ve bu mod arama davranışıyla nasıl ilişkili? Soru 3: Bir API'nin logprob döndürmesi damıtma yoluyla model çıkarmayı neden kolaylaştırır?
:::

::: gorev Gerçek deney · SmolLM2-Instruct → SmolLM2 gerçek KL damıtması, karanlık bilgi ve SFT karşılaştırması
Önceki görevlerdeki `damitma_kl_kaybi`, `hibrit_damitma_adimi` işlevlerini buraya birleştir (çözümlerini kopyalayabilirsin). Çalıştır gerçek ölçüm tablosunu gösterir; Kontrol Et önce işlevlerini gizli verilerle ve farksal taramayla sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
timeout: 240
```
```starter
import ai_lab
import math

def damitma_kl_kaybi(ogretmen_logit, ogrenci_logit, sicaklik_T, mod):
    ex_p = [math.exp(z / sicaklik_T) for z in ogretmen_logit]
    ex_q = [math.exp(z / sicaklik_T) for z in ogrenci_logit]
    sp, sq = (sum(ex_p), sum(ex_q))
    P = [v / sp for v in ex_p]
    Q = [v / sq for v in ex_q]
    kl = sum((pi * math.log(pi / qi) for pi, qi in zip(P, Q)))
    return {'ham_kl': kl, 'olcekli_kayip': kl, 'ogretmen_olasilik': P, 'ogrenci_olasilik': Q}

import math

def hibrit_damitma_adimi(ogretmen_logit, ogrenci_logit, gercek_hedef_id, sicaklik_T, alpha_ce):
    ex_q = [math.exp(z / sicaklik_T) for z in ogrenci_logit]
    q_t = [v / sum(ex_q) for v in ex_q]
    ce = -math.log(q_t[gercek_hedef_id])
    return {'ce_kaybi': ce, 'kd_kaybi': 0.0, 'toplam_kayip': ce, 'karanlik_bilgi_kutlesi': 0.0}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_33 as D
    D.goster(damitma_kl_kaybi, hibrit_damitma_adimi)
```
```test
import ai_lab
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('_ornekler', '_dagilimlar', 'kanit_yaz'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
damitma_kl_kaybi = need("damitma_kl_kaybi")
hibrit_damitma_adimi = need("hibrit_damitma_adimi")
# farksal tarama (görev çözümlerinden derlenen referans)
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile('import math\n\ndef _sayi_mi(v):\n    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)\n\ndef _log_softmax_sicaklik(logitler, T):\n    olcekli = [float(z) / float(T) for z in logitler]\n    m = max(olcekli)\n    lse = m + math.log(sum((math.exp(v - m) for v in olcekli)))\n    log_p = [v - lse for v in olcekli]\n    p = [math.exp(v) for v in log_p]\n    return (log_p, p)\n\ndef damitma_kl_kaybi(ogretmen_logit, ogrenci_logit, sicaklik_T, mod):\n    if not isinstance(ogretmen_logit, list) or not isinstance(ogrenci_logit, list) or len(ogretmen_logit) < 2 or (len(ogretmen_logit) != len(ogrenci_logit)):\n        raise ValueError(\'logit listeleri eşit uzunlukta (>= 2) olmalı\')\n    if not all((_sayi_mi(v) for v in ogretmen_logit)) or not all((_sayi_mi(v) for v in ogrenci_logit)):\n        raise ValueError(\'logit elemanları sonlu sayı olmalı\')\n    if not _sayi_mi(sicaklik_T) or float(sicaklik_T) <= 0.0:\n        raise ValueError(\'sicaklik_T > 0 olmalı\')\n    if mod not in (\'forward\', \'reverse\'):\n        raise ValueError("mod \'forward\' veya \'reverse\' olmalı")\n    T = float(sicaklik_T)\n    log_p, p = _log_softmax_sicaklik(ogretmen_logit, T)\n    log_q, q = _log_softmax_sicaklik(ogrenci_logit, T)\n    if mod == \'forward\':\n        ham_kl = sum((pi * (lpi - lqi) for pi, lpi, lqi in zip(p, log_p, log_q)))\n    else:\n        ham_kl = sum((qi * (lqi - lpi) for qi, lqi, lpi in zip(q, log_q, log_p)))\n    return {\'ham_kl\': ham_kl, \'olcekli_kayip\': T * T * ham_kl, \'ogretmen_olasilik\': p, \'ogrenci_olasilik\': q}\n\nimport math\n\ndef _sayi_mi(v):\n    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)\n\ndef _log_softmax_sicaklik(logitler, T):\n    olcekli = [float(z) / float(T) for z in logitler]\n    m = max(olcekli)\n    lse = m + math.log(sum((math.exp(v - m) for v in olcekli)))\n    log_p = [v - lse for v in olcekli]\n    p = [math.exp(v) for v in log_p]\n    return (log_p, p)\n\ndef hibrit_damitma_adimi(ogretmen_logit, ogrenci_logit, gercek_hedef_id, sicaklik_T, alpha_ce):\n    if not isinstance(ogretmen_logit, list) or not isinstance(ogrenci_logit, list) or len(ogretmen_logit) < 2 or (len(ogretmen_logit) != len(ogrenci_logit)):\n        raise ValueError(\'logit listeleri eşit uzunlukta (>= 2) olmalı\')\n    if not all((_sayi_mi(v) for v in ogretmen_logit)) or not all((_sayi_mi(v) for v in ogrenci_logit)):\n        raise ValueError(\'logit elemanları sonlu sayı olmalı\')\n    V = len(ogretmen_logit)\n    if isinstance(gercek_hedef_id, bool) or not isinstance(gercek_hedef_id, int) or (not 0 <= gercek_hedef_id < V):\n        raise ValueError(\'geçersiz gercek_hedef_id\')\n    if not _sayi_mi(sicaklik_T) or float(sicaklik_T) <= 0.0:\n        raise ValueError(\'sicaklik_T > 0 olmalı\')\n    if not _sayi_mi(alpha_ce) or not 0.0 <= float(alpha_ce) <= 1.0:\n        raise ValueError(\'alpha_ce [0, 1] aralığında olmalı\')\n    T = float(sicaklik_T)\n    a = float(alpha_ce)\n    log_q_t1, _ = _log_softmax_sicaklik(ogrenci_logit, 1.0)\n    ce_kaybi = -log_q_t1[gercek_hedef_id]\n    log_p_t, p_t = _log_softmax_sicaklik(ogretmen_logit, T)\n    log_q_t, _ = _log_softmax_sicaklik(ogrenci_logit, T)\n    kd_kaybi = T * T * sum((pi * (lpi - lqi) for pi, lpi, lqi in zip(p_t, log_p_t, log_q_t)))\n    toplam_kayip = a * ce_kaybi + (1.0 - a) * kd_kaybi\n    karanlik_kutle = sum((p_t[i] for i in range(V) if i != gercek_hedef_id))\n    return {\'ce_kaybi\': ce_kaybi, \'kd_kaybi\': kd_kaybi, \'toplam_kayip\': toplam_kayip, \'karanlik_bilgi_kutlesi\': karanlik_kutle}', 'referans', 'exec'), _REF)
_t, _g = _ff(damitma_kl_kaybi, _REF['damitma_kl_kaybi'], ([4.0, 2.0, 0.0], [2.0, 2.0, 1.0], 2.0, 'forward'), tohum=2722, en_cok=600, mod='tam', butce='oto')
kontrol(_t, "farksal tarama (damitma_kl_kaybi): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(hibrit_damitma_adimi, _REF['hibrit_damitma_adimi'], ([5.0, 2.5, 0.5], [2.0, 1.5, 0.5], 0, 2.0, 0.3), tohum=3137, en_cok=600, mod='tam', butce='oto')
kontrol(_t, "farksal tarama (hibrit_damitma_adimi): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
kontrol(damitma_kl_kaybi([4.0, 1.0], [1.0, 3.0], 2.0, "reverse") == _REF['damitma_kl_kaybi']([4.0, 1.0], [1.0, 3.0], 2.0, "reverse"), "reverse KL ve 2 elemanlı logit korunmalı")
kontrol(hibrit_damitma_adimi([4.0, 1.0], [1.0, 3.0], 1, 2.0, 0.3) == _REF['hibrit_damitma_adimi']([4.0, 1.0], [1.0, 3.0], 1, 2.0, 0.3), "2 elemanlı hibrit damıtma korunmalı")
for _fn, _args in [
    (damitma_kl_kaybi, ([1.0], [1.0], 2.0, "forward")),
    (damitma_kl_kaybi, ([], [], 2.0, "forward")),
    (hibrit_damitma_adimi, ([1.0], [1.0], 0, 2.0, 0.3)),
    (hibrit_damitma_adimi, ([], [], 0, 2.0, 0.3)),
]:
    try:
        _fn(*_args)
        kontrol(False, "2 elemandan kısa logit ValueError fırlatmalı")
    except ValueError:
        kontrol(True, "2 elemandan kısa logit ValueError fırlattı")
if not all(checks): stop()
from sandbox import ai_gercek_ai_uretim_33 as D
try: r = D.deney(damitma_kl_kaybi, hibrit_damitma_adimi)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r['kl_ayni'], "ileri/ters KL ve hibrit kayıp 49 152'lik gerçek dağılımlarda torch ile aynı")
kontrol(r['karanlik_artiyor'], 'karanlık bilgi kütlesi sıcaklıkla artıyor')
kontrol(r['damitma_ogretmene_yaklastirdi'] and r['kd_sftden_iyi'], "damıtma öğrenciyi öğretmene yaklaştırdı; ileri KL sert etiketli SFT'den iyi")
ai_lab.kanit_yaz("ai-uretim-33-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-uretim-33", "deney": r})
```
```solution
import ai_lab
import math

def _sayi_mi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)

def _log_softmax_sicaklik(logitler, T):
    olcekli = [float(z) / float(T) for z in logitler]
    m = max(olcekli)
    lse = m + math.log(sum((math.exp(v - m) for v in olcekli)))
    log_p = [v - lse for v in olcekli]
    p = [math.exp(v) for v in log_p]
    return (log_p, p)

def damitma_kl_kaybi(ogretmen_logit, ogrenci_logit, sicaklik_T, mod):
    if not isinstance(ogretmen_logit, list) or not isinstance(ogrenci_logit, list) or len(ogretmen_logit) < 2 or (len(ogretmen_logit) != len(ogrenci_logit)):
        raise ValueError('logit listeleri eşit uzunlukta (>= 2) olmalı')
    if not all((_sayi_mi(v) for v in ogretmen_logit)) or not all((_sayi_mi(v) for v in ogrenci_logit)):
        raise ValueError('logit elemanları sonlu sayı olmalı')
    if not _sayi_mi(sicaklik_T) or float(sicaklik_T) <= 0.0:
        raise ValueError('sicaklik_T > 0 olmalı')
    if mod not in ('forward', 'reverse'):
        raise ValueError("mod 'forward' veya 'reverse' olmalı")
    T = float(sicaklik_T)
    log_p, p = _log_softmax_sicaklik(ogretmen_logit, T)
    log_q, q = _log_softmax_sicaklik(ogrenci_logit, T)
    if mod == 'forward':
        ham_kl = sum((pi * (lpi - lqi) for pi, lpi, lqi in zip(p, log_p, log_q)))
    else:
        ham_kl = sum((qi * (lqi - lpi) for qi, lqi, lpi in zip(q, log_q, log_p)))
    return {'ham_kl': ham_kl, 'olcekli_kayip': T * T * ham_kl, 'ogretmen_olasilik': p, 'ogrenci_olasilik': q}

def hibrit_damitma_adimi(ogretmen_logit, ogrenci_logit, gercek_hedef_id, sicaklik_T, alpha_ce):
    if not isinstance(ogretmen_logit, list) or not isinstance(ogrenci_logit, list) or len(ogretmen_logit) < 2 or (len(ogretmen_logit) != len(ogrenci_logit)):
        raise ValueError('logit listeleri eşit uzunlukta (>= 2) olmalı')
    if not all((_sayi_mi(v) for v in ogretmen_logit)) or not all((_sayi_mi(v) for v in ogrenci_logit)):
        raise ValueError('logit elemanları sonlu sayı olmalı')
    V = len(ogretmen_logit)
    if isinstance(gercek_hedef_id, bool) or not isinstance(gercek_hedef_id, int) or (not 0 <= gercek_hedef_id < V):
        raise ValueError('geçersiz gercek_hedef_id')
    if not _sayi_mi(sicaklik_T) or float(sicaklik_T) <= 0.0:
        raise ValueError('sicaklik_T > 0 olmalı')
    if not _sayi_mi(alpha_ce) or not 0.0 <= float(alpha_ce) <= 1.0:
        raise ValueError('alpha_ce [0, 1] aralığında olmalı')
    T = float(sicaklik_T)
    a = float(alpha_ce)
    log_q_t1, _ = _log_softmax_sicaklik(ogrenci_logit, 1.0)
    ce_kaybi = -log_q_t1[gercek_hedef_id]
    log_p_t, p_t = _log_softmax_sicaklik(ogretmen_logit, T)
    log_q_t, _ = _log_softmax_sicaklik(ogrenci_logit, T)
    kd_kaybi = T * T * sum((pi * (lpi - lqi) for pi, lpi, lqi in zip(p_t, log_p_t, log_q_t)))
    toplam_kayip = a * ce_kaybi + (1.0 - a) * kd_kaybi
    karanlik_kutle = sum((p_t[i] for i in range(V) if i != gercek_hedef_id))
    return {'ce_kaybi': ce_kaybi, 'kd_kaybi': kd_kaybi, 'toplam_kayip': toplam_kayip, 'karanlik_bilgi_kutlesi': karanlik_kutle}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_33 as D
    D.goster(damitma_kl_kaybi, hibrit_damitma_adimi)
```
```hint
İki görevin çözümlerini olduğu gibi buraya koy.
```
:::

::: anlat Sınır
Görevler sıcaklık ölçekli forward/reverse KL damıtma kaybını, hibrit SFT + KD kaybını ve dark knowledge entropisini küçük dağılımlarla hesaplatır; final adım gerçek bir öğretmen–öğrenci çiftinde kısa bir damıtma eğitimi yapar. Forward KL öğrenciyi öğretmenin bütün modlarını kapsamaya, reverse KL ise tek bir moda odaklanmaya iter; hangisinin iyi olduğu göreve bağlıdır. Öğretmen ve öğrenci farklı tokenizer kullanıyorsa logit düzeyinde damıtma doğrudan yapılamaz. Bir API'nin olasılık çıktıları damıtma yoluyla model çıkarmaya (model extraction) imkân verir; logprob paylaşmak bu yüzden bir güvenlik kararıdır.

Kaynaklar: [Hinton vd. 2015 - Distilling the Knowledge in a Neural Network](https://arxiv.org/abs/1503.02531), [Gu vd. 2023 - MiniLLM: On-Policy Distillation of Large Language Models](https://arxiv.org/abs/2306.08543), [Agarwal vd. 2023 - On-Policy Distillation of Language Models: Learning from Self-Generated Mistakes](https://arxiv.org/abs/2306.13649).
:::

::: dusun
**Mimari Soru:** `DeepSeek-R1-Distill-Qwen-32B` modelini eğitirken `671B` parametreli öğretmenin tüm `128.000` kelimelik logit vektörünü diskte saklamak terabaytlarca yer kaplar. Bunun yerine öğretmenin ürettiği `<think> ... </think>` düşünce zincirleri (`Reasoning Traces`) üzerinde dizi düzeyinde distillation (**`Sequence-Level Distillation`**) ve yalnızca **Top-$K$ (ör. Top-64) logit damıtması** birleştirildiğinde depolama maliyeti nasıl %99.9 düşürülür?
:::

::: ozet
- **`Knowledge Distillation (Hinton et al.)`**, öğretmen modelin $T > 1$ sıcaklıkla yumuşatılmış dağılımındaki **Karanlık Bilgiyi (`Dark Knowledge`)** $T^2 \cdot D_{\text{KL}}(P_T \| Q_T)$ kaybıyla küçük öğrenci modele aktarır.
- Üretken LLM'lerde **`Forward KL` ($D_{\text{KL}}(P \| Q)$)** tüm modları kapsamaya çalışırken (`Mode-Covering`) modlar arasındaki boşluğa olasılık atayabilir; **`Reverse KL` ($D_{\text{KL}}(Q \| P)$, `MiniLLM`)** ise öğrenciyi öğretmenin en güçlü tepelerine odaklar (`Mode-Seeking`).
- Hibrit distillation adımı, gerçek etiket `Cross-Entropy` ($T=1$) ile yumuşak hedef `KL` ($T > 1$) kaybını $\alpha_{\text{ce}}$ katsayısıyla dengeler.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Karanlık bilgi ve $T^2$ ölçeği (30 sn).** "Sert etiket yalnız doğru tokena `1` verir; sıcaklık $T>1$ öğretmenin yakın anlamlı ikincil adaylara verdiği olasılık oranlarını (`dark knowledge`) açığa çıkarır, $T^2$ çarpanı ise yumuşatılmış logit gradyanlarının büyüklüğünü dengeler."
2. **`Forward KL` vs `Reverse KL` (35 sn).** "$D_{\text{KL}}(P \| Q)$ öğretmenin pozitif olduğu her bölgeyi kapsamaya çalışır (`mode-covering`), küçük öğrencide olasılığı tepeler arasına yayabilir; $D_{\text{KL}}(Q \| P)$ ise öğrenciyi öğretmenin en güçlü modlarına odaklar (`mode-seeking`)."
3. **API güvenliği boyutu (30 sn).** "Bir model sunucusunun tam `top-k logprobs` döndürmesi, meşru damıtmada kullanılan aynı KL sinyaliyle model davranışının daha ucuza kopyalanmasını (`model extraction`) kolaylaştırır."
4. **Soru (25 sn).** "Öğretmen ve öğrenci farklı `tokenizer` sözlükleri kullanıyorsa token-düzeyi logit KL damıtması neden doğrudan uygulanamaz?"
:::
