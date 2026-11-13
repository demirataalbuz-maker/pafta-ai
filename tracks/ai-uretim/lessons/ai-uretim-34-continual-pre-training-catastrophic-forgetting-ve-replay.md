---
id: ai-uretim-34
title: "Continual Pre-Training: Alan Uzmanlaştırma, Catastrophic Forgetting Önleme ve EWC / Replay"
summary: "Eğitilmiş bir temel modeli yeni bir dile veya alana (Tıp, Hukuk, Siber Güvenlik) adapte ederken oluşan Catastrophic Forgetting (Yıkıcı Unutma) sorunu, Fisher Information Matrix tabanlı Elastic Weight Consolidation (EWC) ve Experience Replay veri karıştırma."
esleme: ai-temel-10, ai-temel-12, ai-uretim-33
track: ai-uretim
order: 34
duration_minutes: 35
difficulty: orta
xp: 290
prerequisites: [ai-uretim-33]
tags: [continual-pretraining, catastrophic-forgetting, ewc, fisher-information, experience-replay]
---

::: anlat
## Continual training ve forgetting

Yeni verilerle training yapmak önceki görevlerdeki performansı değiştirebilir. Bu derste EWC cezasını ve replay karışımını hesaplayacak; yeni görev kazanımını önceki görevdeki değişimden ayrı raporlayacaksın. Hiç forgetting oluşmayacağını garanti eden genel bir formül yoktur.

Ancak modeli doğrudan yeni alan verisine sokup standart öğrenme oranıyla (`Learning Rate`) eğittiğimizde felaket bir olgu yaşanır: **`Catastrophic Forgetting` (Yıkıcı Unutma)!**
Model yeni tıp veya hukuk terimlerini hızla öğrenirken, daha önce bildiği **Python kodlama, matematiksel muhakeme ve genel talimat izleme yeteneklerini tamamen unutur!** Çünkü gradyan inişi, yeni görevin kaybını düşürmek için eski görevin bellek izlerini taşıyan ağırlıkları acımasızca ezer.

Frontier AI laboratuvarları `Continual Pre-Training` aşamasında yıkıcı unutmayı önlemek için üç temel mekanizmayı birlikte kullanır:
1. **`Experience Replay (Data Mixing)`:** Yeni alan verisinin içine **%5 ila %15 oranında orijinal genel ön-eğitim verisi** karıştırmak!
2. **`Elastic Weight Consolidation (EWC — Kirkpatrick et al., DeepMind)`:** Eski görev için hayati önem taşıyan ağırlıkları **Fisher Bilgi Matrisi (`Fisher Information Matrix` $F_i$)** ile tespit edip o ağırlıklara "sert bir yay" bağlamak!
3. **`Embedding Warmup & Low-Peak Cosine/WSD Schedule`:** Yeni tokenizer kelimeleri eklendiyse önce gövdeyi dondurup yeni embedding vektörleri ısıtmak (`Warmup`), ardından ana ön-eğitimin tepe öğrenme oranının sadece %10–%20'si ile devam etmek.

```
┌────────────────────────────────────────────────────────────────────────────┐
│         CONTINUAL PRE-TRAINING (CPT) & ANTI-FORGETTING MİMARİSİ            │
├─────────────────────────────────────┬──────────────────────────────────────┤
│ 1. ELASTIC WEIGHT CONSOLIDATION     │ 2. EXPERIENCE REPLAY & WARMUP        │
│    (KIRKPATRICK ET AL., PNAS 2017)  │ ──────────────────────────────────── │
│ ─────────────────────────────────── │ • Sadece %100 Yeni Alan Verisi       │
│ • Eski görev sonunda optimal ağırlık│   verilirse genel yetenekler çöker!  │
│   θ* ve her parametrenin hassasiyeti│ • Çözüm: %85-%90 Yeni Alan Verisi +  │
│   Fisher F_i = E[(∂log p / ∂θ_i)^2] │   %10-%15 Orijinal Genel/Kod Replay! │
│ • F_i büyükse o ağırlık eski görev  │ • Yeni tokenlar eklendiyse:          │
│   için KRİTİKTİR (hareket edemez!). │   Adım 1: Transformer bloklarını     │
│ • Toplam Kayıp:                     │   dondur, yalnız Embedding ısıt!     │
│   L(θ) = L_yeni(θ)                  │   Adım 2: Tüm modeli düşük LR ile    │
│        + (λ/2) Σ_i F_i (θ_i - θ*_i)^2│   birlikte güncelle.                 │
└─────────────────────────────────────┴──────────────────────────────────────┘
```

---

### 1. `Elastic Weight Consolidation (EWC)` ve `Fisher Information` Diyagonali

Eski genel eğitim bittiğinde modelin parametre vektörü $\theta^*$ olsun. Hangi parametrelerin $\theta_i^*$ değerinden uzaklaşmasının eski genel görevi (`Task A`) bozacağını nereden biliriz?
Olasılıksal olarak, eski veri dağılımı üzerindeki log-olabilirliğin ikinci türev eğriliği, yani **Ampirik Fisher Bilgi Matrisinin Diyagonali (`Diagonal Fisher Information` $F_i$)** tam olarak bu hassasiyeti ölçer:

$$F_i = \mathbb{E}_{x \sim \mathcal{D}_{\text{eski}}} \left[ \left( \frac{\partial \log p_\theta(x)}{\partial \theta_i} \right)^2 \right] \ge 0$$

- Eğer bir ağırlık için $F_i$ **çok büyükse**, o ağırlıktaki en ufak bir değişim eski görevin kaybını patlatır!
- Eğer $F_i \approx 0$ ise, o ağırlık eski görev için "boş kapasitedir (`Slack Capacity`)"; yeni görev bu ağırlığı dilediği gibi değiştirebilir!

`EWC`, yeni görev kaybı $\mathcal{L}_{\text{yeni}}(\theta)$ üzerine $F_i$ sertliğinde karesel bir yay cezası ekler:

$$\mathcal{L}_{\text{EWC}}(\theta) = \mathcal{L}_{\text{yeni}}(\theta) + \frac{\lambda}{2} \sum_{i} F_i \left(\theta_i - \theta_i^*\right)^2$$

Bu kaybın $\theta_i$ parametresine göre toplam gradyanı:

$$\frac{\partial \mathcal{L}_{\text{EWC}}}{\partial \theta_i} = g_{\text{yeni}, i} + \lambda \cdot F_i \cdot (\theta_i - \theta_i^*)$$

```python
# EWC Yay Cezasının Kritik vs Esnek Parametre Üzerindeki Etkisi
teta_eski = [1.00, 1.00]       # Eski görev sonundaki optimal ağırlıklar θ*
teta_mevcut = [1.50, 1.50]     # İki ağırlık da +0.50 kaymış olsun
fisher = [100.0, 0.01]         # 0. ağırlık eski görev için ÇOK KRİTİK (F=100), 1. ağırlık ESNEK (F=0.01)
lam = 0.5

geri_cekme_kuvveti = [lam * f * (t - t_eski) for f, t, t_eski in zip(fisher, teta_mevcut, teta_eski)]
print(f"Kritik Agirlik Geri Cekme Gradyani : {geri_cekme_kuvveti[0]:.3f} (Sert yay!)")
print(f"Esnek  Agirlik Geri Cekme Gradyani : {geri_cekme_kuvveti[1]:.4f} (Serbest hareket!)")
```

---

### 2. `Experience Replay` Karışım Oranı ve `Perplexity` Unutma Analizi

Büyük ölçekli `Continual Pre-Training` çalışmalarında (ör. `CodeLlama`, `Med-PaLM`, `BloombergGPT`), `EWC` bellekte $\theta^*$ ve $F$ kopyalarını tutmayı gerektirdiği için genellikle **Veri Düzeyinde Replay Karışımı (`Data Replay Mixing`)** ile desteklenir:
- Yeni alan derlemi $N_{\text{alan}}$ adet token içeriyorsa ve toplam eğitim karışımının $r_{\text{replay}} \in (0, 1)$ oranında (ör. $r = 0.10$, yani %10) eski genel veriden oluşması isteniyorsa:
  $$N_{\text{toplam}} = \frac{N_{\text{alan}}}{1 - r_{\text{replay}}}, \qquad N_{\text{replay}} = N_{\text{toplam}} - N_{\text{alan}} = N_{\text{alan}} \cdot \frac{r_{\text{replay}}}{1 - r_{\text{replay}}}$$
- **Unutma Ölçümü (`Forgetting Metric`):** Eski genel doğrulama kümesindeki başlangıç kaybı $\mathcal{L}_{\text{eski}}^{(0)}$ (`Perplexity` $\text{PPL}_0 = \exp(\mathcal{L}_{\text{eski}}^{(0)})$) ile CPT sonrası kayıp $\mathcal{L}_{\text{eski}}^{(1)}$ ($\text{PPL}_1 = \exp(\mathcal{L}_{\text{eski}}^{(1)})$) arasındaki artış izlenir.

---

### 3. Gerçek PyTorch Üretim Kodu: `EWCRegularizer`

Gerçek bir PyTorch `Continual Pre-Training` döngüsünde Fisher matrisini tahmin eden ve `EWC` cezasını hesaplayan modül:

```python norun
import torch
import torch.nn as nn

class EWCContinualWrapper:
    def __init__(self, model: nn.Module, lambda_ewc: float = 100.0):
        self.model = model
        self.lambda_ewc = lambda_ewc
        self.params_star: dict[str, torch.Tensor] = {}
        self.fisher_diag: dict[str, torch.Tensor] = {}

    @torch.no_grad()
    def snapshot_old_task(self):
        for name, param in self.model.named_parameters():
            if param.requires_grad:
                self.params_star[name] = param.detach().clone()
                self.fisher_diag[name] = torch.zeros_like(param)

    def accumulate_fisher(self, loss_loglik: torch.Tensor, n_batches: int):
        self.model.zero_grad()
        loss_loglik.backward()
        with torch.no_grad():
            for name, param in self.model.named_parameters():
                if param.requires_grad and param.grad is not None:
                    self.fisher_diag[name] += (param.grad.pow(2)) / n_batches

    def penalty_loss(self) -> torch.Tensor:
        ewc_loss = torch.tensor(0.0, device=next(self.model.parameters()).device)
        for name, param in self.model.named_parameters():
            if name in self.params_star:
                diff = param - self.params_star[name]
                ewc_loss = ewc_loss + (self.fisher_diag[name] * diff.pow(2)).sum()
        return 0.5 * self.lambda_ewc * ewc_loss
```

**Uygulama sınırı:** Görevler Python ile küçük, denetlenebilir hesaplar yapar. `python norun` blokları PyTorch/GPU tarafını incelemek içindir; bu tezgâhta otomatik çalıştırılıp gerçek training/serving kabulü yapılmaz.

**Birincil kaynak:** [EWC makalesi](https://arxiv.org/abs/1612.00796). Kaynak, yöntemin ayrıntıları içindir; dersteki küçük örnek ölçülmüş üretim benchmarkı değildir.
:::

::: tahmin EWC Yay Cezası ve Toplam Gradyan Hesabı
Tek bir parametre için eski görev optimal değeri $\theta^* = 2.0$, mevcut değeri $\theta = 2.5$, Fisher bilgisi $F = 8.0$ ve `EWC` katsayısı $\lambda = 0.5$ olarak veriliyor.
Yeni görevden gelen ham gradyan $g_{\text{yeni}} = -1.2$ (parametreyi daha da büyütmek istiyor!) olduğuna göre:
1. `EWC` ceza kaybı $\mathcal{L}_{\text{ceza}} = \frac{\lambda}{2} F (\theta - \theta^*)^2$ kaçtır?
2. Birleştirilmiş toplam gradyan $g_{\text{toplam}} = g_{\text{yeni}} + \lambda F (\theta - \theta^*)$ kaç olur ve parametre hangi yöne hareket eder?

```python
teta = 2.5
teta_yildiz = 2.0
F = 8.0
lam = 0.5
g_yeni = -1.2

ewc_ceza = 0.5 * lam * F * ((teta - teta_yildiz) ** 2)
g_toplam = g_yeni + lam * F * (teta - teta_yildiz)

print(f"EWC Ceza Kaybi={ewc_ceza:.2f} | Toplam Gradyan={g_toplam:.2f}")
```

???

```cikti
EWC Ceza Kaybi=0.50 | Toplam Gradyan=0.80
```
Fark $\theta - \theta^* = 0.5$ olduğu için ceza kaybı $0.5 \times 0.5 \times 8.0 \times (0.5)^2 = 0.50$ olur. Ceza gradyanı ise $\lambda F (\theta - \theta^*) = 0.5 \times 8.0 \times 0.5 = +2.0$ olur. Yeni görevin $-1.2$ gradyanıyla toplandığında $g_{\text{toplam}} = -1.2 + 2.0 = +0.80$ çıkar! Gradyan inişinde ($\theta \leftarrow \theta - \eta g_{\text{toplam}}$) pozitif gradyan parametreyi tekrar $\theta^* = 2.0$'a doğru geri çeker ve eski görevin unutulmasını engeller!
:::

::: gorev 1 · Elastic Weight Consolidation (EWC) Fisher Cezalı Kayıp ve Güncelleme
Mevcut parametre vektörü (`mevcut_teta`), eski görev optimal parametreleri (`eski_teta_yildiz`), diyagonal Fisher bilgisi (`fisher_diyagonal`), yeni görev gradyanı (`gorev_gradyani`) ve düzenlileştirme katsayısı (`lambda_ewc`) verildiğinde `EWC` ceza kaybını ve toplam gradyanı hesaplayan `ewc_kayip_ve_grad(mevcut_teta, eski_teta_yildiz, fisher_diyagonal, gorev_gradyani, lambda_ewc)` işlevini yaz.

**Girdi Kuralları ve Doğrulama:**
- `mevcut_teta`, `eski_teta_yildiz`, `fisher_diyagonal`, `gorev_gradyani`: Aynı uzunlukta ($D \ge 1$) sonlu sayı listeleri (`list[float]`).
- `fisher_diyagonal` içindeki tüm elemanlar negatif olmayan sayılar ($F_i \ge 0$) olmalıdır.
- `lambda_ewc`: `bool` olmayan sonlu sayı ve $\lambda \ge 0$.

**Hesaplama Kuralları:**
1. **EWC Ceza Kaybı (`ewc_ceza_kaybi`):**
   $$\mathcal{L}_{\text{EWC}} = \frac{\lambda}{2.0} \sum_{i=0}^{D-1} F_i \cdot (\theta_i - \theta_i^*)^2$$
2. **Toplam Gradyan (`toplam_gradyan`):** Her parametre $i \in \{0, \dots, D-1\}$ için:
   $$g_{\text{toplam}}[i] = g_{\text{yeni}}[i] + \lambda \cdot F_i \cdot (\theta_i - \theta_i^*)$$
3. **Maksimum Korumalı Parametre İndisi (`en_kritik_indis`):** `fisher_diyagonal` içinde en büyük $F_i$ değerine sahip parametrenin indisi (eşitlik durumunda en küçük indis, `int`).
4. İşlev şu sözlüğü döndürmelidir:
   `{"ewc_ceza_kaybi": float, "toplam_gradyan": list[float], "en_kritik_indis": int}`
- Geçersiz herhangi bir girdide `ValueError` yükseltilmelidir.

```starter
import math

# KUSURLU BAŞLANGIÇ KODU: Fisher ağırlıklarını (F_i) kullanmadan düz L2 cezası hesaplıyor!
def ewc_kayip_ve_grad(mevcut_teta, eski_teta_yildiz, fisher_diyagonal, gorev_gradyani, lambda_ewc):
    ceza = 0.5 * lambda_ewc * sum((t - ts) ** 2 for t, ts in zip(mevcut_teta, eski_teta_yildiz))
    grad = [g + lambda_ewc * (t - ts) for g, t, ts in zip(gorev_gradyani, mevcut_teta, eski_teta_yildiz)]
    return {
        "ewc_ceza_kaybi": ceza,
        "toplam_gradyan": grad,
        "en_kritik_indis": 0,
    }

print(ewc_kayip_ve_grad([2.5, 1.5], [2.0, 1.0], [8.0, 20.0], [-1.2, 0.5], lambda_ewc=0.5))
```
```test
def sinama_ewc(f):
    import copy, math, random
    def _ref(t, ts, fi, g, lam):
        lam = float(lam)
        ceza = 0.5 * lam * sum(float(f_i) * ((float(ti) - float(tsi)) ** 2) for ti, tsi, f_i in zip(t, ts, fi))
        grad = [float(gi) + lam * float(f_i) * (float(ti) - float(tsi)) for ti, tsi, f_i, gi in zip(t, ts, fi, g)]
        krit = max(range(len(fi)), key=lambda i: float(fi[i]))
        return {"ewc_ceza_kaybi": ceza, "toplam_gradyan": grad, "en_kritik_indis": krit}
    def _yakin(a, b):
        keys = {"ewc_ceza_kaybi", "toplam_gradyan", "en_kritik_indis"}
        if not isinstance(a, dict) or set(a.keys()) != keys:
            return False
        if type(a["en_kritik_indis"]) is not int or a["en_kritik_indis"] != b["en_kritik_indis"]:
            return False
        if abs(a["ewc_ceza_kaybi"] - b["ewc_ceza_kaybi"]) > 1e-10:
            return False
        return isinstance(a["toplam_gradyan"], list) and len(a["toplam_gradyan"]) == len(b["toplam_gradyan"]) and all(abs(x - y) <= 1e-10 for x, y in zip(a["toplam_gradyan"], b["toplam_gradyan"]))
    try:
        t, ts, fi, g = [2.5, 1.5], [2.0, 1.0], [8.0, 20.0], [-1.2, 0.5]
        old = (copy.deepcopy(t), copy.deepcopy(ts), copy.deepcopy(fi), copy.deepcopy(g))
        out = f(t, ts, fi, g, 0.5)
        if (t, ts, fi, g) != old or not _yakin(out, _ref(t, ts, fi, g, 0.5)):
            return False
        if out["en_kritik_indis"] != 1 or abs(out["ewc_ceza_kaybi"] - 1.75) > 1e-10:
            return False

        rng = random.Random(3401)
        for _ in range(20):
            d = rng.randint(1, 6)
            tt = [rng.uniform(-3.0, 3.0) for _ in range(d)]
            tts = [rng.uniform(-3.0, 3.0) for _ in range(d)]
            ffi = [rng.uniform(0.0, 50.0) for _ in range(d)]
            gg = [rng.uniform(-2.0, 2.0) for _ in range(d)]
            lam = rng.uniform(0.0, 2.0)
            if not _yakin(f(tt, tts, ffi, gg, lam), _ref(tt, tts, ffi, gg, lam)):
                return False

        bad_cases = [
            ([], [], [], [], 0.5),
            ([1.0, 2.0], [1.0], [1.0, 1.0], [0.0, 0.0], 0.5),
            ([1.0], [1.0], [-0.1], [0.0], 0.5),   # negatif Fisher
            ([1.0], [1.0], [1.0], [0.0], -0.5),   # negatif lambda
            ([1.0], [1.0], [1.0], [0.0], True),
            ([float("nan")], [1.0], [1.0], [0.0], 0.5),
        ]
        for bt, bts, bfi, bg, bl in bad_cases:
            try:
                f(bt, bts, bfi, bg, bl)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ewc_kayip_ve_grad = need("ewc_kayip_ve_grad")
ok(sinama_ewc(ewc_kayip_ve_grad), "EWC Fisher ağırlıklı ceza kaybı, birleşik gradyan ve en kritik parametre tespiti")
for ad, mut in [
    ("1/2 çarpanını unutan", lambda t, ts, fi, g, l: dict(ewc_kayip_ve_grad(t, ts, fi, g, l), ewc_ceza_kaybi=ewc_kayip_ve_grad(t, ts, fi, g, l)["ewc_ceza_kaybi"] * 2.0 + 0.1)),
    ("gradyana ceza eklemeyen", lambda t, ts, fi, g, l: dict(ewc_kayip_ve_grad(t, ts, fi, g, l), toplam_gradyan=list(g))),
]:
    ok(not sinama_ewc(mut), "mutant reddedildi: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef _sayi_mi(v):\n    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)\n\ndef ewc_kayip_ve_grad(mevcut_teta, eski_teta_yildiz, fisher_diyagonal, gorev_gradyani, lambda_ewc):\n    for lst in (mevcut_teta, eski_teta_yildiz, fisher_diyagonal, gorev_gradyani):\n        if not isinstance(lst, list) or not lst or (not all((_sayi_mi(v) for v in lst))):\n            raise ValueError('parametre ve gradyan listeleri boş olmayan sonlu sayı listesi olmalı')\n    d = len(mevcut_teta)\n    if len(eski_teta_yildiz) != d or len(fisher_diyagonal) != d or len(gorev_gradyani) != d:\n        raise ValueError('tüm vektörler eşit uzunlukta olmalı')\n    if any((float(f) < 0.0 for f in fisher_diyagonal)):\n        raise ValueError('Fisher bilgi değerleri >= 0 olmalı')\n    if not _sayi_mi(lambda_ewc) or float(lambda_ewc) < 0.0:\n        raise ValueError('lambda_ewc >= 0 olmalı')\n    lam = float(lambda_ewc)\n    ceza = 0.5 * lam * sum((float(fi) * (float(ti) - float(tsi)) ** 2 for ti, tsi, fi in zip(mevcut_teta, eski_teta_yildiz, fisher_diyagonal)))\n    toplam_grad = [float(gi) + lam * float(fi) * (float(ti) - float(tsi)) for ti, tsi, fi, gi in zip(mevcut_teta, eski_teta_yildiz, fisher_diyagonal, gorev_gradyani)]\n    en_kritik = max(range(d), key=lambda i: float(fisher_diyagonal[i]))\n    return {'ewc_ceza_kaybi': ceza, 'toplam_gradyan': toplam_grad, 'en_kritik_indis': en_kritik}", 'referans', 'exec'), _REF)
_t, _g = _ff(ewc_kayip_ve_grad, _REF['ewc_kayip_ve_grad'], ([2.5, 1.5], [2.0, 1.0], [8.0, 20.0], [-1.2, 0.5], 0.5), tohum=2836, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (ewc_kayip_ve_grad): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math

def _sayi_mi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)

def ewc_kayip_ve_grad(mevcut_teta, eski_teta_yildiz, fisher_diyagonal, gorev_gradyani, lambda_ewc):
    for lst in (mevcut_teta, eski_teta_yildiz, fisher_diyagonal, gorev_gradyani):
        if not isinstance(lst, list) or not lst or not all(_sayi_mi(v) for v in lst):
            raise ValueError("parametre ve gradyan listeleri boş olmayan sonlu sayı listesi olmalı")
    d = len(mevcut_teta)
    if len(eski_teta_yildiz) != d or len(fisher_diyagonal) != d or len(gorev_gradyani) != d:
        raise ValueError("tüm vektörler eşit uzunlukta olmalı")
    if any(float(f) < 0.0 for f in fisher_diyagonal):
        raise ValueError("Fisher bilgi değerleri >= 0 olmalı")
    if not _sayi_mi(lambda_ewc) or float(lambda_ewc) < 0.0:
        raise ValueError("lambda_ewc >= 0 olmalı")

    lam = float(lambda_ewc)
    ceza = 0.5 * lam * sum(
        float(fi) * ((float(ti) - float(tsi)) ** 2)
        for ti, tsi, fi in zip(mevcut_teta, eski_teta_yildiz, fisher_diyagonal)
    )
    toplam_grad = [
        float(gi) + lam * float(fi) * (float(ti) - float(tsi))
        for ti, tsi, fi, gi in zip(mevcut_teta, eski_teta_yildiz, fisher_diyagonal, gorev_gradyani)
    ]
    en_kritik = max(range(d), key=lambda i: float(fisher_diyagonal[i]))

    return {
        "ewc_ceza_kaybi": ceza,
        "toplam_gradyan": toplam_grad,
        "en_kritik_indis": en_kritik,
    }

if __name__ == "__main__":
    print(ewc_kayip_ve_grad([2.5, 1.5], [2.0, 1.0], [8.0, 20.0], [-1.2, 0.5], lambda_ewc=0.5))
```
```hint
Her indis için farkı `fark = float(ti) - float(tsi)` olarak hesapla; ceza kaybına `0.5 * lam * fi * (fark ** 2)` ekle, gradyana ise `gi + lam * fi * fark` uygula.
```
:::

::: gorev 2 · Continual Pre-Training Replay Karışım Oranı ve Unutma (Forgetting) Metriği
Bir `Continual Pre-Training` aşamasında hedef alan veri kümesi boyutu (`alan_verisi_boyutu`, token sayısı), istenen genel veri tekrar oranı (`replay_orani` $\in [0.0, 0.5]$), eski genel doğrulama kümesindeki başlangıç kaybı (`eski_kayip`) ve eğitim sonrası yeni kayıp (`yeni_eski_kayip`) verildiğinde Replay bütçesini ve `Perplexity` değişimini hesaplayan `cpt_replay_planla(alan_verisi_boyutu, replay_orani, eski_kayip, yeni_eski_kayip)` işlevini yaz.

**Girdi Kuralları ve Doğrulama:**
- `alan_verisi_boyutu`: Yeni alan derlemindeki token sayısı (`bool` olmayan `int`, $\ge 1$).
- `replay_orani`: Toplam eğitim karışımı içindeki genel veri oranı $r$ (`bool` olmayan sonlu sayı, $0.0 \le r \le 0.5$).
- `eski_kayip`, `yeni_eski_kayip`: Eski genel doğrulama kümesindeki `Cross-Entropy` kayıpları (`bool` olmayan sonlu sayı, $> 0.0$ ve $\le 20.0$).

**Hesaplama Kuralları:**
1. Toplam eğitim karışımında `replay_orani` ($r$) kadar eski genel veri bulunması için gereken **eklenecek Replay token sayısını** (`eklenecek_replay_token`, en yakın tam sayıya `round(...)` ile yuvarlanmış `int`) hesapla:
   $$N_{\text{replay}} = \text{round}\left( N_{\text{alan}} \cdot \frac{r}{1.0 - r} \right), \qquad N_{\text{toplam}} = N_{\text{alan}} + N_{\text{replay}}$$
2. Eski ve yeni `Perplexity` değerlerini hesapla:
   $$\text{eski\_ppl} = \exp(\text{eski\_kayip}), \qquad \text{yeni\_ppl} = \exp(\text{yeni\_eski\_kayip})$$
3. Bağıl `Perplexity` artış oranını (`ppl_artis_orani`) hesapla:
   $$\text{ppl\_artis\_orani} = \frac{\text{yeni\_ppl} - \text{eski\_ppl}}{\text{eski\_ppl}}$$
4. Eğer `ppl_artis_orani > 0.15` (%15'ten fazla Perplexity bozulması) ise `yikici_unutma_uyarisi = True`, değilse `False` olarak işaretle.
5. İşlev şu sözlüğü döndürmelidir:
   `{"eklenecek_replay_token": int, "toplam_egitim_token": int, "eski_ppl": float, "yeni_ppl": float, "ppl_artis_orani": float, "yikici_unutma_uyarisi": bool}`
- Geçersiz herhangi bir girdide `ValueError` yükseltilmelidir.

```starter
import math

# KUSURLU BAŞLANGIÇ KODU: Replay token sayısını N_alan * r olarak yanlış hesaplıyor (karışımdaki oranı r olmuyor)!
def cpt_replay_planla(alan_verisi_boyutu, replay_orani, eski_kayip, yeni_eski_kayip):
    rep = round(alan_verisi_boyutu * replay_orani)
    ep = math.exp(eski_kayip)
    yp = math.exp(yeni_eski_kayip)
    artis = (yp - ep) / ep
    return {
        "eklenecek_replay_token": rep,
        "toplam_egitim_token": alan_verisi_boyutu + rep,
        "eski_ppl": ep,
        "yeni_ppl": yp,
        "ppl_artis_orani": artis,
        "yikici_unutma_uyarisi": False,
    }

print(cpt_replay_planla(alan_verisi_boyutu=9000, replay_orani=0.10, eski_kayip=2.0, yeni_eski_kayip=2.25))
```
```test
def sinama_cpt(f):
    import math, random
    def _ref(n_alan, r, l0, l1):
        r, l0, l1 = float(r), float(l0), float(l1)
        rep = int(round(n_alan * (r / (1.0 - r))))
        ep, yp = math.exp(l0), math.exp(l1)
        artis = (yp - ep) / ep
        return {
            "eklenecek_replay_token": rep,
            "toplam_egitim_token": n_alan + rep,
            "eski_ppl": ep,
            "yeni_ppl": yp,
            "ppl_artis_orani": artis,
            "yikici_unutma_uyarisi": artis > 0.15,
        }
    def _yakin(a, b):
        keys = {"eklenecek_replay_token", "toplam_egitim_token", "eski_ppl", "yeni_ppl", "ppl_artis_orani", "yikici_unutma_uyarisi"}
        if not isinstance(a, dict) or set(a.keys()) != keys:
            return False
        if type(a["eklenecek_replay_token"]) is not int or type(a["toplam_egitim_token"]) is not int or type(a["yikici_unutma_uyarisi"]) is not bool:
            return False
        if a["eklenecek_replay_token"] != b["eklenecek_replay_token"] or a["toplam_egitim_token"] != b["toplam_egitim_token"] or a["yikici_unutma_uyarisi"] != b["yikici_unutma_uyarisi"]:
            return False
        return all(abs(a[k] - b[k]) <= 1e-10 for k in ("eski_ppl", "yeni_ppl", "ppl_artis_orani"))
    try:
        # 9000 alan tokenı ve %10 replay -> toplam 10000 token (1000 replay) olmalı!
        out = f(9000, 0.10, 2.0, 2.25)
        if not _yakin(out, _ref(9000, 0.10, 2.0, 2.25)):
            return False
        if out["eklenecek_replay_token"] != 1000 or out["toplam_egitim_token"] != 10000 or out["yikici_unutma_uyarisi"] is not True:
            return False

        out2 = f(8000, 0.20, 2.0, 2.05)
        if out2["eklenecek_replay_token"] != 2000 or out2["yikici_unutma_uyarisi"] is not False:
            return False
        for b_args in [(1000, 0.1, 20.0, 20.0), (1000, 0.1, 15.0, 15.0), (1000, 0.1, 1.0, 1.1), (1000, 0.1, 0.14, 0.2797619423751588)]:
            if not _yakin(f(*b_args), _ref(*b_args)):
                return False

        rng = random.Random(3402)
        for _ in range(20):
            na = rng.randint(100, 50000)
            rr = rng.uniform(0.0, 0.5)
            l0 = rng.uniform(1.0, 5.0)
            l1 = rng.uniform(1.0, 5.5)
            if not _yakin(f(na, rr, l0, l1), _ref(na, rr, l0, l1)):
                return False

        bad_cases = [
            (0, 0.1, 2.0, 2.1),
            (1000, float("inf"), 2.0, 2.1),
            (1000, 0.1, 25.0, 2.1),
            (True, 0.1, 2.0, 2.1),
            (1000, -0.05, 2.0, 2.1),
            (1000, 0.6, 2.0, 2.1),
            (1000, 0.1, 0.0, 2.1),
            (1000, 0.1, 2.0, 25.0),
            (1000, False, 2.0, 2.1),
        ]
        for bn, br, bl0, bl1 in bad_cases:
            try:
                f(bn, br, bl0, bl1)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

cpt_replay_planla = need("cpt_replay_planla")
ok(sinama_cpt(cpt_replay_planla), "Replay veri karışım oranı r/(1-r), Perplexity artışı ve yıkıcı unutma uyarısı")
for ad, mut in [
    ("1-r paydasını unutan", lambda n, r, l0, l1: dict(cpt_replay_planla(n, r, l0, l1), eklenecek_replay_token=int(round(n * r)))),
    ("uyarıyı hep False döndüren", lambda n, r, l0, l1: dict(cpt_replay_planla(n, r, l0, l1), yikici_unutma_uyarisi=False)),
]:
    ok(not sinama_cpt(mut), "mutant reddedildi: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef _sayi_mi(v):\n    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)\n\ndef cpt_replay_planla(alan_verisi_boyutu, replay_orani, eski_kayip, yeni_eski_kayip):\n    if isinstance(alan_verisi_boyutu, bool) or not isinstance(alan_verisi_boyutu, int) or alan_verisi_boyutu < 1:\n        raise ValueError('alan_verisi_boyutu >= 1 tam sayı olmalı')\n    if not _sayi_mi(replay_orani) or not 0.0 <= float(replay_orani) <= 0.5:\n        raise ValueError('replay_orani [0.0, 0.5] aralığında olmalı')\n    if not _sayi_mi(eski_kayip) or not 0.0 < float(eski_kayip) <= 20.0:\n        raise ValueError('geçersiz eski_kayip')\n    if not _sayi_mi(yeni_eski_kayip) or not 0.0 < float(yeni_eski_kayip) <= 20.0:\n        raise ValueError('geçersiz yeni_eski_kayip')\n    r = float(replay_orani)\n    eklenecek = int(round(float(alan_verisi_boyutu) * (r / (1.0 - r))))\n    toplam = alan_verisi_boyutu + eklenecek\n    eski_ppl = math.exp(float(eski_kayip))\n    yeni_ppl = math.exp(float(yeni_eski_kayip))\n    artis_orani = (yeni_ppl - eski_ppl) / eski_ppl\n    return {'eklenecek_replay_token': eklenecek, 'toplam_egitim_token': toplam, 'eski_ppl': eski_ppl, 'yeni_ppl': yeni_ppl, 'ppl_artis_orani': artis_orani, 'yikici_unutma_uyarisi': bool(artis_orani > 0.15)}", 'referans', 'exec'), _REF)
_t, _g = _ff(cpt_replay_planla, _REF['cpt_replay_planla'], (9000, 0.1, 2.0, 2.25), tohum=2859, en_cok=600, mod='tam', butce='oto', ekler=[(9000, 0.1, 2.0, 2.139761942375159, )])
ok(_t, "farksal tarama (cpt_replay_planla): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math

def _sayi_mi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)

def cpt_replay_planla(alan_verisi_boyutu, replay_orani, eski_kayip, yeni_eski_kayip):
    if isinstance(alan_verisi_boyutu, bool) or not isinstance(alan_verisi_boyutu, int) or alan_verisi_boyutu < 1:
        raise ValueError("alan_verisi_boyutu >= 1 tam sayı olmalı")
    if not _sayi_mi(replay_orani) or not (0.0 <= float(replay_orani) <= 0.5):
        raise ValueError("replay_orani [0.0, 0.5] aralığında olmalı")
    if not _sayi_mi(eski_kayip) or not (0.0 < float(eski_kayip) <= 20.0):
        raise ValueError("geçersiz eski_kayip")
    if not _sayi_mi(yeni_eski_kayip) or not (0.0 < float(yeni_eski_kayip) <= 20.0):
        raise ValueError("geçersiz yeni_eski_kayip")

    r = float(replay_orani)
    eklenecek = int(round(float(alan_verisi_boyutu) * (r / (1.0 - r))))
    toplam = alan_verisi_boyutu + eklenecek

    eski_ppl = math.exp(float(eski_kayip))
    yeni_ppl = math.exp(float(yeni_eski_kayip))
    artis_orani = (yeni_ppl - eski_ppl) / eski_ppl

    return {
        "eklenecek_replay_token": eklenecek,
        "toplam_egitim_token": toplam,
        "eski_ppl": eski_ppl,
        "yeni_ppl": yeni_ppl,
        "ppl_artis_orani": artis_orani,
        "yikici_unutma_uyarisi": bool(artis_orani > 0.15),
    }

if __name__ == "__main__":
    print(cpt_replay_planla(alan_verisi_boyutu=9000, replay_orani=0.10, eski_kayip=2.0, yeni_eski_kayip=2.25))
```
```hint
$N_{\text{replay}} / (N_{\text{alan}} + N_{\text{replay}}) = r$ eşitliğinden $N_{\text{replay}} = \text{round}(N_{\text{alan}} \cdot r / (1 - r))$ formülünü kullan ve `artis_orani > 0.15` koşuluyla yıkıcı unutma uyarısını belirle.
```
:::

::: anlat Gerçek deney: SmolLM2'yi Türkçeye uyarlarken İngilizceyi unutmak: düz, EWC ve replay
Final yıkıcı unutmayı gerçek bir modelde ölçer (indirme yok, CPU):

- **Eski bilgi:** İngilizce (`deepset/prompt-injections` metinleri). **Yeni alan:** Türkçe (Pafta ders metinleri). SmolLM2'nin son 4 katmanı 60 Türkçe parça (her biri 128 token) üzerinde eğitilir.
- **Fisher:** 8 İngilizce parçada kayıp gradyanının karesi alınarak gerçek bir empirik Fisher köşegeni hesaplanır.
- **Üç yol:** (a) düz ince ayar; (b) EWC: her adımda gradyana $\lambda F (\theta - \theta^*)$ eklenir; (c) replay: senin `cpt_replay_planla` işlevinin %30 oran için verdiği token sayısı kadar ayrı ve tekrarsız İngilizce parça Türkçe akışa serpiştirilir.
- **Öğrencinin EWC'si:** EWC eğitiminin ortasında gerçek parametre, $\theta^*$, Fisher ve görev gradyanından 64'lük bir dilim senin `ewc_kayip_ve_grad` işlevine verilir; ceza, toplam gradyan ve en kritik indis torch referansıyla karşılaştırılır.
- **Unutma raporu:** her yolun eğitimden önceki ve sonraki İngilizce kaybı senin işlevine verilir: perplexity artış oranı ve %15 eşikli "yıkıcı unutma" uyarısı.

**Güvenlik yönü — güvenlik hizalaması da unutulur:** Aynı Türkçe eğitim SmolLM2-Instruct'a uygulanır ve 10 istenmeyen (sahte banka e-postası, zorbalık mesajı …) ile 6 zararsız istekte modelin ürettiği cevaplarda ret oranı ölçülür (anahtar kelimeyle kaba tespit). Zararsız görünen alan uyarlaması retleri tamamen siler. Dört ret örneğini (farklı istemler, farklı bir ret cümlesi) eğitime iki kez karıştırmak retleri geri getirir, ama model bu cümleyi ezberleyip **zararsız isteklere de** uygular: aşırı ret. Ret örneklerini orijinal modelin zararsız sorulara verdiği kendi cevaplarıyla karıştıran dengeli replay ödünleşimi belirgin biçimde iyileştirir. İnce ayardan sonra güvenlik değerlendirmesi hem ret hem aşırı ret yönünden tekrarlanmalıdır (Qi vd. 2023).

Kabul: iki işlevin farksal taramayı geçmesi; EWC diliminin ve unutma raporlarının referansla aynı olması; düz ince ayarın İngilizceyi unutup uyarı vermesi; EWC'nin ve replay'in unutmayı düz ince ayara göre azaltması; üç yolun da Türkçeyi öğrenmesi. Ayrıca düz ince ayar istenmeyen isteklerde ret oranını ve ret cümlesinin marjını düşürmeli; tek tip güvenlik replay'i retleri geri getirirken zararsız isteklerin de en az yarısını reddetmeli; dengeli replay düz ince ayardan çok ret ve tek tip replay'den az aşırı ret vermelidir.

**Kanıt dosyasını oku:** `once`, `sonuc`, `unutma_raporu`, `replay_plani`. Soru 1: Replay neden EWC'den çok daha etkili oldu? Soru 2: İlk denemede aynı 8 İngilizce parçayı tekrar tekrar karıştırmak İngilizceyi daha da bozdu; neden? Soru 3: Bir güvenlik ayarlı modeli alan verisiyle uyarlarken hangi değerlendirmeyi de tekrarlamalısın?
:::

::: gorev Gerçek deney · SmolLM2'de Türkçe uyarlama sırasında İngilizce unutma: düz, EWC ve replay
Önceki görevlerdeki `ewc_kayip_ve_grad`, `cpt_replay_planla` işlevlerini buraya birleştir (çözümlerini kopyalayabilirsin). Çalıştır gerçek ölçüm tablosunu gösterir; Kontrol Et önce işlevlerini gizli verilerle ve farksal taramayla sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
timeout: 300
```
```starter
import ai_lab
import math

def ewc_kayip_ve_grad(mevcut_teta, eski_teta_yildiz, fisher_diyagonal, gorev_gradyani, lambda_ewc):
    ceza = 0.5 * lambda_ewc * sum(((t - ts) ** 2 for t, ts in zip(mevcut_teta, eski_teta_yildiz)))
    grad = [g + lambda_ewc * (t - ts) for g, t, ts in zip(gorev_gradyani, mevcut_teta, eski_teta_yildiz)]
    return {'ewc_ceza_kaybi': ceza, 'toplam_gradyan': grad, 'en_kritik_indis': 0}

import math

def cpt_replay_planla(alan_verisi_boyutu, replay_orani, eski_kayip, yeni_eski_kayip):
    rep = round(alan_verisi_boyutu * replay_orani)
    ep = math.exp(eski_kayip)
    yp = math.exp(yeni_eski_kayip)
    artis = (yp - ep) / ep
    return {'eklenecek_replay_token': rep, 'toplam_egitim_token': alan_verisi_boyutu + rep, 'eski_ppl': ep, 'yeni_ppl': yp, 'ppl_artis_orani': artis, 'yikici_unutma_uyarisi': False}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_34 as D
    D.goster(ewc_kayip_ve_grad, cpt_replay_planla)
```
```test
import ai_lab
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('_parcalar', 'kanit_yaz'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
ewc_kayip_ve_grad = need("ewc_kayip_ve_grad")
cpt_replay_planla = need("cpt_replay_planla")
# farksal tarama (görev çözümlerinden derlenen referans)
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef _sayi_mi(v):\n    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)\n\ndef ewc_kayip_ve_grad(mevcut_teta, eski_teta_yildiz, fisher_diyagonal, gorev_gradyani, lambda_ewc):\n    for lst in (mevcut_teta, eski_teta_yildiz, fisher_diyagonal, gorev_gradyani):\n        if not isinstance(lst, list) or not lst or (not all((_sayi_mi(v) for v in lst))):\n            raise ValueError('parametre ve gradyan listeleri boş olmayan sonlu sayı listesi olmalı')\n    d = len(mevcut_teta)\n    if len(eski_teta_yildiz) != d or len(fisher_diyagonal) != d or len(gorev_gradyani) != d:\n        raise ValueError('tüm vektörler eşit uzunlukta olmalı')\n    if any((float(f) < 0.0 for f in fisher_diyagonal)):\n        raise ValueError('Fisher bilgi değerleri >= 0 olmalı')\n    if not _sayi_mi(lambda_ewc) or float(lambda_ewc) < 0.0:\n        raise ValueError('lambda_ewc >= 0 olmalı')\n    lam = float(lambda_ewc)\n    ceza = 0.5 * lam * sum((float(fi) * (float(ti) - float(tsi)) ** 2 for ti, tsi, fi in zip(mevcut_teta, eski_teta_yildiz, fisher_diyagonal)))\n    toplam_grad = [float(gi) + lam * float(fi) * (float(ti) - float(tsi)) for ti, tsi, fi, gi in zip(mevcut_teta, eski_teta_yildiz, fisher_diyagonal, gorev_gradyani)]\n    en_kritik = max(range(d), key=lambda i: float(fisher_diyagonal[i]))\n    return {'ewc_ceza_kaybi': ceza, 'toplam_gradyan': toplam_grad, 'en_kritik_indis': en_kritik}\n\nimport math\n\ndef _sayi_mi(v):\n    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)\n\ndef cpt_replay_planla(alan_verisi_boyutu, replay_orani, eski_kayip, yeni_eski_kayip):\n    if isinstance(alan_verisi_boyutu, bool) or not isinstance(alan_verisi_boyutu, int) or alan_verisi_boyutu < 1:\n        raise ValueError('alan_verisi_boyutu >= 1 tam sayı olmalı')\n    if not _sayi_mi(replay_orani) or not 0.0 <= float(replay_orani) <= 0.5:\n        raise ValueError('replay_orani [0.0, 0.5] aralığında olmalı')\n    if not _sayi_mi(eski_kayip) or not 0.0 < float(eski_kayip) <= 20.0:\n        raise ValueError('geçersiz eski_kayip')\n    if not _sayi_mi(yeni_eski_kayip) or not 0.0 < float(yeni_eski_kayip) <= 20.0:\n        raise ValueError('geçersiz yeni_eski_kayip')\n    r = float(replay_orani)\n    eklenecek = int(round(float(alan_verisi_boyutu) * (r / (1.0 - r))))\n    toplam = alan_verisi_boyutu + eklenecek\n    eski_ppl = math.exp(float(eski_kayip))\n    yeni_ppl = math.exp(float(yeni_eski_kayip))\n    artis_orani = (yeni_ppl - eski_ppl) / eski_ppl\n    return {'eklenecek_replay_token': eklenecek, 'toplam_egitim_token': toplam, 'eski_ppl': eski_ppl, 'yeni_ppl': yeni_ppl, 'ppl_artis_orani': artis_orani, 'yikici_unutma_uyarisi': bool(artis_orani > 0.15)}", 'referans', 'exec'), _REF)
_t, _g = _ff(ewc_kayip_ve_grad, _REF['ewc_kayip_ve_grad'], ([2.5, 1.5], [2.0, 1.0], [8.0, 20.0], [-1.2, 0.5], 0.5), tohum=2836, en_cok=600, mod='tam', butce='oto')
kontrol(_t, "farksal tarama (ewc_kayip_ve_grad): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(cpt_replay_planla, _REF['cpt_replay_planla'], (9000, 0.1, 2.0, 2.25), tohum=2859, en_cok=600, mod='tam', butce='oto', ekler=[(9000, 0.1, 2.0, 2.139761942375159, )])
kontrol(_t, "farksal tarama (cpt_replay_planla): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
def _sinir34():
    try:
        for b_args in [(1000, 0.1, 20.0, 20.0), (1000, 0.1, 15.0, 15.0), (1000, 0.1, 1.0, 1.1), (1000, 0.1, 0.14, 0.2797619423751588)]:
            if cpt_replay_planla(*b_args) != _REF['cpt_replay_planla'](*b_args):
                return False
        for bad_ in [(1000, 0.1, 25.0, 2.1), (1000, 0.1, 2.0, 25.0)]:
            try:
                cpt_replay_planla(*bad_)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
kontrol(_sinir34(), 'CPT replay kayıp üst sınırı ve %15 eşik kontrolleri')
if not all(checks): stop()
from sandbox import ai_gercek_ai_uretim_34 as D
try: r = D.deney(ewc_kayip_ve_grad, cpt_replay_planla)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r['ewc_ayni'] and r['rapor_ayni'], 'EWC dilimi ve unutma raporları gerçek değerlerde referansla aynı')
kontrol(r['duz_unutuyor'], 'düz ince ayar İngilizceyi unutturdu ve yıkıcı unutma uyarısı verdi')
kontrol(r['ewc_azaltiyor'] and r['replay_azaltiyor'] and r['yeni_alan_ogrenildi'], 'EWC ve replay unutmayı azalttı; üç yol da Türkçeyi öğrendi')
kontrol(r['guvenlik_unutuluyor'], 'Türkçe alan uyarlaması Instruct modelin istenmeyen isteklere retlerini azalttı')
kontrol(r['tek_tip_replay_asiri_ret'] and r['dengeli_replay_daha_iyi'], "tek tip ret replay'i aşırı ret üretti; dengeli replay ret ile yardımseverliği daha iyi dengeledi")
ai_lab.kanit_yaz("ai-uretim-34-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-uretim-34", "deney": r})
```
```solution
import ai_lab
import math

def _sayi_mi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)

def ewc_kayip_ve_grad(mevcut_teta, eski_teta_yildiz, fisher_diyagonal, gorev_gradyani, lambda_ewc):
    for lst in (mevcut_teta, eski_teta_yildiz, fisher_diyagonal, gorev_gradyani):
        if not isinstance(lst, list) or not lst or (not all((_sayi_mi(v) for v in lst))):
            raise ValueError('parametre ve gradyan listeleri boş olmayan sonlu sayı listesi olmalı')
    d = len(mevcut_teta)
    if len(eski_teta_yildiz) != d or len(fisher_diyagonal) != d or len(gorev_gradyani) != d:
        raise ValueError('tüm vektörler eşit uzunlukta olmalı')
    if any((float(f) < 0.0 for f in fisher_diyagonal)):
        raise ValueError('Fisher bilgi değerleri >= 0 olmalı')
    if not _sayi_mi(lambda_ewc) or float(lambda_ewc) < 0.0:
        raise ValueError('lambda_ewc >= 0 olmalı')
    lam = float(lambda_ewc)
    ceza = 0.5 * lam * sum((float(fi) * (float(ti) - float(tsi)) ** 2 for ti, tsi, fi in zip(mevcut_teta, eski_teta_yildiz, fisher_diyagonal)))
    toplam_grad = [float(gi) + lam * float(fi) * (float(ti) - float(tsi)) for ti, tsi, fi, gi in zip(mevcut_teta, eski_teta_yildiz, fisher_diyagonal, gorev_gradyani)]
    en_kritik = max(range(d), key=lambda i: float(fisher_diyagonal[i]))
    return {'ewc_ceza_kaybi': ceza, 'toplam_gradyan': toplam_grad, 'en_kritik_indis': en_kritik}

def cpt_replay_planla(alan_verisi_boyutu, replay_orani, eski_kayip, yeni_eski_kayip):
    if isinstance(alan_verisi_boyutu, bool) or not isinstance(alan_verisi_boyutu, int) or alan_verisi_boyutu < 1:
        raise ValueError('alan_verisi_boyutu >= 1 tam sayı olmalı')
    if not _sayi_mi(replay_orani) or not 0.0 <= float(replay_orani) <= 0.5:
        raise ValueError('replay_orani [0.0, 0.5] aralığında olmalı')
    if not _sayi_mi(eski_kayip) or not 0.0 < float(eski_kayip) <= 20.0:
        raise ValueError('geçersiz eski_kayip')
    if not _sayi_mi(yeni_eski_kayip) or not 0.0 < float(yeni_eski_kayip) <= 20.0:
        raise ValueError('geçersiz yeni_eski_kayip')
    r = float(replay_orani)
    eklenecek = int(round(float(alan_verisi_boyutu) * (r / (1.0 - r))))
    toplam = alan_verisi_boyutu + eklenecek
    eski_ppl = math.exp(float(eski_kayip))
    yeni_ppl = math.exp(float(yeni_eski_kayip))
    artis_orani = (yeni_ppl - eski_ppl) / eski_ppl
    return {'eklenecek_replay_token': eklenecek, 'toplam_egitim_token': toplam, 'eski_ppl': eski_ppl, 'yeni_ppl': yeni_ppl, 'ppl_artis_orani': artis_orani, 'yikici_unutma_uyarisi': bool(artis_orani > 0.15)}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_34 as D
    D.goster(ewc_kayip_ve_grad, cpt_replay_planla)
```
```hint
İki görevin çözümlerini olduğu gibi buraya koy.
```
:::

::: anlat Sınır
Görevler EWC'nin Fisher cezalı kaybını, replay karışım oranını ve unutma metriğini küçük sayılarla hesaplatır; final adım gerçek bir modelde alan uyarlamasını ve unutmayı ölçer. Fisher bilgisi diagonal yaklaşımla hesaplanır ve büyük modellerde parametre önemini ancak kabaca yansıtır. Replay oranı eski verinin erişilebilir olduğunu varsayar; ön eğitim verisi yoksa yakın bir yedek kullanılır ve koruma zayıflar. Alan uyarlaması sırasında güvenlik ve ret davranışı da unutulabilir; yalnız alan perplexity'si değil, güvenlik değerlendirmesi de tekrarlanmalıdır.

Kaynaklar: [Kirkpatrick vd. 2017 - Overcoming catastrophic forgetting in neural networks](https://arxiv.org/abs/1612.00796), [Gupta vd. 2023 - Continual Pre-Training of Large Language Models: How to (re)warm your model?](https://arxiv.org/abs/2308.04014), [Ibrahim vd. 2024 - Simple and Scalable Strategies to Continually Pre-train Large Language Models](https://arxiv.org/abs/2403.08763).
:::

::: dusun
**Mimari Soru:** Bir modele Türkçe hukuk terimleri için `8,000` yeni `BPE` tokenı eklediğimizde, bu yeni tokenların `Embedding` ve `LM Head` satırları rastgele (veya alt-kelime ortalamasıyla) başlar. Eğer ilk adımda tüm Transformer katmanlarını dondurmadan (`Freeze`) doğrudan yüksek öğrenme oranıyla eğitime başlarsak, yeni embedding vektörlerinden geriye yayılan devasa rastgele gradyanlar orta katmanlardaki `Attention` ağırlıklarına ne yapar?
:::

::: ozet
- **`Continual Pre-Training (CPT)`** sırasında yalnız yeni alan verisiyle yüksek öğrenme oranında eğitim yapmak, eski yeteneklerin silinmesine (**`Catastrophic Forgetting`**) yol açar.
- **`Elastic Weight Consolidation (EWC)`**, eski görevdeki log-olabilirlik gradyanlarının karesinden hesaplanan **Fisher Bilgi Matrisi ($F_i$)** ile kritik ağırlıklara $\frac{\lambda}{2}\sum F_i (\theta_i - \theta_i^*)^2$ yay cezası uygular.
- **`Experience Replay Mixing`**, yeni alan verisine $r / (1 - r)$ oranında orijinal genel/kod ön-eğitim verisi karıştırarak genel dil ve muhakeme dağılımını korur.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Alan uyarlamasında `Catastrophic Forgetting` (30 sn).** "Bir temel modeli yalnız yeni alan metinleriyle eğittiğimizde gradyan adımları eski genel dil, kodlama ve güvenlik hizalaması ağırlıklarını ezerek perplexity ve ret davranışını çökertir."
2. **`EWC` Fisher yay cezası (35 sn).** "Eski görevdeki log-olabilirlik gradyanlarının karesinden hesaplanan diyagonal Fisher bilgisi $F_i$, hangi parametrenin eski görev için kritik olduğunu ölçer ve $\frac{\lambda}{2}\sum F_i(\theta_i - \theta_i^*)^2$ cezasıyla o ağırlıkları korur."
3. **Veri düzeyinde `Replay` ve güvenlik dengesi (30 sn).** "Toplam karışımda $r$ oranını tutturmak için $N_{\text{alan}} \cdot \frac{r}{1-r}$ genel token ve hem ret hem zararsız yanıt örnekleri birlikte karıştırılmalıdır."
4. **Soru (25 sn).** "Alan ince ayarına yalnız ret cümleleri karıştırıp zararsız yardımsever örnekler eklemezsek model neden zararsız soruları da reddetmeye (`over-refusal`) başlar?"
:::
