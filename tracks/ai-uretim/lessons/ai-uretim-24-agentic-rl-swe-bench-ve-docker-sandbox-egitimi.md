---
id: ai-uretim-24
title: "Kod Yazan Ajan Eğitimi 2: Çok Adımlı Agentic RL, Docker Sandbox ve SWE-bench Ödül Döngüsü"
track: ai-uretim
order: 24
duration_minutes: 40
difficulty: ileri
xp: 330
prerequisites: [ai-uretim-23]
esleme: ai-uretim-21, ai-uretim-25, ai-temel-26
summary: "Gerçek bir yazılım mühendisi ajan (SWE-agent / Claude Code / Antigravity) nasıl eğitilir? Çok adımlı Agentic RL (Multi-Turn Trajectory RL), Docker Sandbox ortamı, Action vs Observation Token Masking ve SWE-bench Fail-to-Pass / Pass-to-Pass doğrulayıcı ödülü."
tags: [agentic-rl, swe-bench, docker-sandbox, observation-masking, multi-turn-rl, code-agent]
---

::: anlat 1. Tek Seferlik Kod Üretiminden (Single-Turn) Otonom Yazılım Mühendisi Ajana (Multi-Turn SWE-Agent) Geçiş
## Agent training için trajectory ve test reward

Bir coding agent, action ve observation içeren çok adımlı bir trajectory üretir. Bu derste hangi tokenların loss hesabına girdiğini ayıracak ve patch testlerinden reward kararı çıkaracaksın. Görevler gerçek Docker agent training başlatmaz; bu akışın sayısal ve mantıksal parçalarını modeller.

Bir konferansta ya da `AI Agent` mimari sunumunda kürsüye çıktığında izleyicilere şu gerçeği göster:
> *"2023 yılında kod modellerini `HumanEval` ile ölçüyorduk: Modele 5 satırlık bir fonksiyon başlığı veriyorduk, model tek seferde (`Single-Turn`) gövdeyi yazıyordu. Ama gerçek bir yazılım mühendisi (`Software Engineer`) böyle çalışmaz! Gerçek mühendisin önüne `Django` veya `Linux` deposundaki 500.000 satırlık kod ve bir `GitHub Issue` (Hata Bildirimi) gelir. Mühendis depoda arama yapar, testleri koşturur, hata izini (`traceback`) okur, yamasını düzenler ve regresyon testlerini yeniden doğrular."*

İşte bu uçtan uca mühendislik yeteneğini ölçen altın standart **`SWE-bench` (`Software Engineering Benchmark`)**, modeli bu döngü içinde eğiten teknoloji ise **Çok Adımlı Ajan Pekiştirmeli Öğrenmesi (`Multi-Turn Agentic RL`)** mimarisidir!

```text
  MULTI-TURN AGENTIC RL YÖRÜNGESİ (TRAJECTORY τ) & DOCKER SANDBOX:
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ [Prompt s_0: GitHub Issue Açıklaması]                      (Mask = 0)   │
  │      │                                                                  │
  │      ▼                                                                  │
  │ [Ajan Eylemi a_1: <think>...</think> bash("pytest tests/")] (Mask = 1)  │
  │      │                                                                  │
  │      ▼  (Docker Container İçinde Gerçekten Çalıştırılır!)               │
  │ [Ortam Gözlemi o_1: "FAILED test_auth.py::test_token_exp"] (Mask = 0!)  │
  │      │                                                                  │
  │      ▼                                                                  │
  │ [Ajan Eylemi a_2: edit_file("auth.py", old, new)]          (Mask = 1)  │
  │      │                                                                  │
  │      ▼                                                                  │
  │ [Ortam Gözlemi o_2: "File updated. 12 passed, 0 failed!"]  (Mask = 0!)  │
  │      │                                                                  │
  │      ▼                                                                  │
  │ [Ajan Eylemi a_3: submit_patch()]                          (Mask = 1)  │
  └─────────────────────────────────────┬───────────────────────────────────┘
                                        ▼
         🏆 SWE-BENCH VERIFIER ÖDÜLÜ R(τ):
            • Fail-to-Pass (Hata düzeltildi mi?) VE
            • Pass-to-Pass (Eski çalışan testler bozulmadı mı?) -> R = +1.0!
```

**Uygulama sınırı:** Görevler Python ile küçük, denetlenebilir hesaplar yapar. `python norun` blokları PyTorch/GPU tarafını incelemek içindir; bu tezgâhta otomatik çalıştırılıp gerçek training/serving kabulü yapılmaz.

**Birincil kaynak:** [SWE-bench projesi](https://www.swebench.com/). Kaynak, yöntemin ayrıntıları içindir; dersteki küçük örnek ölçülmüş üretim benchmarkı değildir.
:::

::: anlat 2. Agentic RL'in En Kritik Sırrı: Action vs Environment Observation Masking!
Şimdi çok turlu (`Multi-Turn`) bir ajanı `SFT` veya `RL` (`GRPO / PPO`) ile eğitirken yapılan **en ölümcül mühendislik hatasına** bakalım:

Bir ajan görev boyunca $T$ tur ilerlediğinde, bağlam penceresinde (`Context Window`) birbirini izleyen iki farklı türde `token` dizisi oluşur:
$$\tau = (s_0, \underbrace{a_1}_{\text{Model}}, \underbrace{o_1}_{\text{Docker}}, \underbrace{a_2}_{\text{Model}}, \underbrace{o_2}_{\text{Docker}}, \dots, \underbrace{a_T}_{\text{Model}})$$

1. **`Action & Thought Tokens` ($a_t \sim \pi_\theta(\cdot \mid s_t)$):** Modelin kendi iradesiyle ürettiği düşünce (`<think>`) ve araç çağrısı (`bash`, `edit_file`) `token`larıdır.
2. **`Environment Observation Tokens` ($o_t \sim \mathcal{E}(\cdot \mid s_t, a_t)$):** `Docker Sandbox` konteynerinin terminale bastığı dosya içerikleri, `SyntaxError` çıktıları, ` segmentation fault` logları ve derleyici mesajlarıdır!

### 🚨 Neden `Observation` Token'larını Maskelemezsek Model Delirir?
Eğer tüm $\tau$ dizisi üzerinde ayrım yapmadan gradyan hesaplarsan (`mask = 1` her yerde):
- Model başarılı bir yörüngede (`R = +1.0`) 1. turda `pytest` çalıştırıp ekranda 50 satırlık `Traceback: ZeroDivisionError` (`o_1`) gördüğünde, **`RL` algoritması o `Traceback` hata mesajındaki `token`ların da olasılığını artırmaya (` Positive Gradient`) çalışır!**
- Sonuç: Model kendi ürettiği kodun ortasında durup dururken **sahte terminal çıktıları ve `Traceback` hataları uydurmaya (`Hallucinating Environment Observations`)** başlar ve ağırlıkları bozulur!

### 🛡️ Çözüm: `Loss / Gradient Masking` ($M_i \in \{0, 1\}$)
Yörünge (`Trajectory`) üzerindeki her `token` konumu $i$ için ikili bir **Eylem Maskesi (`Action Mask` $M_i$)** oluşturulur:
- Konum $i$ bir **`Action` (`Thought` + `Tool Call`)** `token`'ı ise $\implies M_i = \mathbf{1}$ (Gradyan akar!).
- Konum $i$ bir **`Prompt` ($s_0$)** veya **`Environment Observation` ($o_t$)** `token`'ı ise $\implies M_i = \mathbf{0}$ (Gradyan tamamen sıfırlanır!).
- **Çok Önemli:** `Observation` `token`ları `Self-Attention` içinde görünmeye (`Attend` edilmeye) **devam eder** (böylece sonraki adım $a_2$, önceki terminal çıktısı $o_1$'i okur); ancak `Loss` ve `Policy Gradient` toplamına yalnızca $M_i = 1$ olan konumlar katılır:

$$\mathcal{L}_{\text{Agentic-RL}}(\theta) = -\frac{1}{\sum_{i} M_i} \sum_{i=1}^{|\tau|} M_i \cdot \hat{A}(\tau) \cdot \ln \pi_\theta(\tau_i \mid \tau_{<i})$$
:::

::: anlat 3. Docker Sandbox Mimarisi ve SWE-bench Doğrulayıcı Ödülü (Fail-to-Pass & Pass-to-Pass)
Bir kod ajanını `RL` ile eğitirken modelin rastgele `rm -rf /` veya sonsuz döngü (`while True:`) çalıştırması ana sunucuyu çökertebilir. Bu yüzden her eğitim yörüngesi (`Rollout`), ağ erişimi kapatılmış (`Network-Isolated`), CPU/RAM ve zaman aşımı (`Timeout = 30s`) sınırlandırılmış tek kullanımlık bir **`Docker Container Sandbox`** içinde koşturulur!

### 🧪 `SWE-bench` Doğrulayıcı Ödülü (`Verifier Reward`) Nasıl Hesaplanır?
Ajan işini bitirip `git diff` yamasını (`Patch`) teslim ettiğinde, doğrulayıcı (`Verifier`) konteyner içinde **iki ayrı birim testi kümesini (`Unit Test Suites`)** çalıştırır:

1. **`Fail-to-Pass` ($T_{F \to P}$) Testleri:**
   - Yamadan önce (`Pre-Patch`) **başarısız olan (`FAIL`)**, yani kullanıcının bildirdiği hatayı (`Bug`) doğrudan yeniden üreten testlerdir.
   - Ajanın yamasından sonra (`Post-Patch`) bu testlerin **`PASS` (Yeşil)** olması zorunludur!
2. **`Pass-to-Pass` ($T_{P \to P}$) Regresyon Testleri:**
   - Yamadan önce zaten **başarılı olan (`PASS`)**, projenin mevcut çalışan özelliklerini koruyan testlerdir.
   - Eğer ajan hatayı çözerken projenin başka bir yerini bozarsa (`Regression`), bu testlerden biri `FAIL` olur!

**Tam Çözüm (`Resolved`) Şartı:**
Bir yamanın tam ödül alması için **HEM `Fail-to-Pass` testlerinin %100'ünün geçmesi HEM DE `Pass-to-Pass` testlerinin %100'ünün korunması** gerekir!

```python norun
import torch

def compute_agentic_trajectory_loss(
    logits: torch.Tensor,         # [Batch, SeqLen, Vocab]
    token_ids: torch.Tensor,      # [Batch, SeqLen]
    action_mask: torch.Tensor,    # [Batch, SeqLen] -> 1: Action, 0: Prompt/Observation!
    advantages: torch.Tensor      # [Batch] -> GRPO avantaj skoru A_i
) -> torch.Tensor:
    # Bir sağa kaydırılmış hedef ve maske
    shift_logits = logits[:, :-1, :]
    shift_labels = token_ids[:, 1:]
    shift_mask   = action_mask[:, 1:].float()

    log_probs = torch.log_softmax(shift_logits, dim=-1)
    token_logp = torch.gather(log_probs, dim=-1, index=shift_labels.unsqueeze(-1)).squeeze(-1)

    # Yalnızca Action tokenları (shift_mask == 1) üzerinden avantaj ağırlıklı kayıp!
    masked_logp = (token_logp * shift_mask).sum(dim=-1) / (shift_mask.sum(dim=-1) + 1e-8)
    loss = -(masked_logp * advantages).mean()
    return loss
```
:::

::: tahmin Agentic RL Yörüngesinde Action Masking ve SWE-bench Çözüm Kontrolü
Bir ajan 3 parçalık kısa bir yörünge üretmiştir:
1. `Action 1` (`4 token`, `mask=1`),
2. `Observation 1` (`100 token` terminal hata çıktısı, `mask=0`),
3. `Action 2` (`6 token`, `mask=1`).
Toplam `110 token` içinden kaç tanesi `Policy Gradient` güncellemesine katılır ve `Fail-to-Pass` (`2/2 PASS`), `Pass-to-Pass` (`9/10 PASS` — 1 regresyon hatası!) olan bir yama `SWE-bench`'te `Resolved` (Tam Çözüldü) sayılır mı?

```python
toplam_token = 4 + 100 + 6
aktif_gradyan_token = 4 + 0 + 6

f2p_tam = (2 == 2)
p2p_tam = (9 == 10)
resolved_mi = f2p_tam and p2p_tam
print(f"Aktif Gradyan Token: {aktif_gradyan_token}/{toplam_token} | SWE-bench Resolved: {resolved_mi}")
```

???

```cikti
Aktif Gradyan Token: 10/110 | SWE-bench Resolved: False
```
Terminal çıktısı olan `100` adet `Observation` tokenı `mask=0` ile maskelendiği için `110` tokendan yalnızca modelin ürettiği **`10` adet `Action` tokenı** üzerinden gradyan akar. `Fail-to-Pass` testlerinin tamamı (`2/2`) geçse bile, `Pass-to-Pass` testlerinden 1 tanesi bozulduğu (`9/10` — regresyon!) için yama `SWE-bench` kurallarına göre **`False` (`Resolved` değil)** kabul edilir.
:::

::: gorev 1 · Çok Turlu Ajan Yörüngesinde (Trajectory) Observation Masking ve Politika Kaybı
Çok adımlı bir ajan yörüngesindeki (`adimlar`) mesaj parçalarını inceleyip yalnızca modelin ürettiği `"action"` adımlarına `1`, `"prompt"` ve `"observation"` adımlarına `0` maskesi atayarak ağırlıklı politika kaybını (`Policy Gradient Loss`) hesaplayan `ajan_yorunge_maskele(adimlar, avantaj)` işlevini yaz:

1. **Girdiler:**
   - `adimlar`: Her biri `{"rol": str, "token_logp": [float, ...]}` biçiminde olan yörünge parçaları listesi (`"rol"` alanı `"prompt"`, `"action"` veya `"observation"` değerlerinden biridir; `token_logp` ise o parçadaki her bir `token`'ın log-olasılığı $\ln \pi_\theta(y_t \mid y_{<t})$ listesidir).
   - `avantaj`: Bu yörüngenin toplam avantaj skoru $\hat{A}$ (`float`).
2. **Kurallar:**
   - Yörüngedeki tüm `token`ları sırasıyla tek bir düz akış olarak birleştirirken:
     - Eğer parçanın `rol == "action"` ise o parçadaki her `token` için `maske` listesine `1` ekle.
     - Eğer parçanın `rol` değeri `"prompt"` veya `"observation"` ise o parçadaki her `token` için `maske` listesine `0` ekle.
   - `aktif_token_sayisi`: Maskesi `1` olan toplam `token` sayısı.
   - `maskelenen_token_sayisi`: Maskesi `0` olan toplam `token` sayısı.
   - `ortalama_action_logp`: Yalnızca maskesi `1` olan (`"action"`) `token`ların `token_logp` değerlerinin aritmetik ortalaması (`aktif_token_sayisi > 0` ise `toplam_action_logp / aktif_token_sayisi`, `0` ise `0.0`).
   - `politika_kaybi` (`Policy Gradient Loss`):
     $$\mathcal{L} = -\text{avantaj} \cdot \text{ortalama\_action\_logp}$$
   - Sayısal çıktıları `round(val, 6)` ile yuvarla.
3. **Dönüş Değeri:**
   `{"maske": [int, ...], "aktif_token_sayisi": int, "maskelenen_token_sayisi": int, "ortalama_action_logp": float, "politika_kaybi": float}` sözlüğü döndür.

```starter
def ajan_yorunge_maskele(adimlar, avantaj):
    # KUSURLU BAŞLANGIÇ KODU: observation tokenlarını maskelemeden tüm tokenlara 1 veriyor!
    tum_logp = [lp for a in adimlar for lp in a["token_logp"]]
    ort = sum(tum_logp) / len(tum_logp) if tum_logp else 0.0
    return {
        "maske": [1] * len(tum_logp),
        "aktif_token_sayisi": len(tum_logp),
        "maskelenen_token_sayisi": 0,
        "ortalama_action_logp": round(ort, 6),
        "politika_kaybi": round(-avantaj * ort, 6),
    }

ornek_adimlar = [
    {"rol": "prompt", "token_logp": [-2.0, -3.0]},
    {"rol": "action", "token_logp": [-0.5, -0.3]},
    {"rol": "observation", "token_logp": [-8.0, -9.0, -7.0]},
    {"rol": "action", "token_logp": [-0.2, -0.6]},
]
print(ajan_yorunge_maskele(ornek_adimlar, avantaj=1.5))
```

```test
import copy

def _ref_maske(adimlar, av):
    maske = []
    act_lp = []
    for a in adimlar:
        m = 1 if a["rol"] == "action" else 0
        for lp in a["token_logp"]:
            maske.append(m)
            if m == 1:
                act_lp.append(lp)
    aktif = sum(maske)
    maskelenen = len(maske) - aktif
    ort = (sum(act_lp) / aktif) if aktif > 0 else 0.0
    kayip = -av * ort
    return {
        "maske": maske,
        "aktif_token_sayisi": aktif,
        "maskelenen_token_sayisi": maskelenen,
        "ortalama_action_logp": round(ort, 6),
        "politika_kaybi": round(kayip, 6),
    }

def sozlesme(fn):
    try:
        v1 = [
            {"rol": "prompt", "token_logp": [-2.0, -3.0]},
            {"rol": "action", "token_logp": [-0.5, -0.3]},
            {"rol": "observation", "token_logp": [-8.0, -9.0, -7.0]},
            {"rol": "action", "token_logp": [-0.2, -0.6]},
        ]
        v2 = [
            {"rol": "prompt", "token_logp": [-1.0]},
            {"rol": "observation", "token_logp": [-5.0, -4.0]},
        ]
        for v, av in [(v1, 1.5), (v1, -0.8), (v2, 1.0)]:
            v_k = copy.deepcopy(v)
            if fn(v, av) != _ref_maske(v, av) or v != v_k:
                return False
        return True
    except Exception:
        return False

ok(sozlesme(ajan_yorunge_maskele), "ajan_yorunge_maskele yalnızca action tokenlarına 1 maskesi vermeli ve observation logp değerlerini kayba katmamalı")

def m_obs_dahil(adimlar, av):
    r = copy.deepcopy(_ref_maske(adimlar, av))
    r["maskelenen_token_sayisi"] = 0
    return r

def m_isaret_ters(adimlar, av):
    return ajan_yorunge_maskele(adimlar, -av)

for ad, m in [("Observation tokenlarını maskelemeyen", m_obs_dahil), ("Politika kaybı işaretini ters alan", m_isaret_ters)]:
    ok(not sozlesme(m), f"Yanlış çözüm/mutant yakalanmalı: {ad}")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def ajan_yorunge_maskele(adimlar, avantaj):\n    maske = []\n    action_logp = []\n    for adim in adimlar:\n        m = 1 if adim['rol'] == 'action' else 0\n        for lp in adim['token_logp']:\n            maske.append(m)\n            if m == 1:\n                action_logp.append(lp)\n    aktif_sayisi = sum(maske)\n    maskelenen_sayisi = len(maske) - aktif_sayisi\n    ort_logp = sum(action_logp) / aktif_sayisi if aktif_sayisi > 0 else 0.0\n    kayip = -avantaj * ort_logp\n    return {'maske': maske, 'aktif_token_sayisi': aktif_sayisi, 'maskelenen_token_sayisi': maskelenen_sayisi, 'ortalama_action_logp': round(ort_logp, 6), 'politika_kaybi': round(kayip, 6)}", 'referans', 'exec'), _REF)
_t, _g = _ff(ajan_yorunge_maskele, _REF['ajan_yorunge_maskele'], ([{'rol': 'prompt', 'token_logp': [-2.0, -3.0]}, {'rol': 'action', 'token_logp': [-0.5, -0.3]}, {'rol': 'observation', 'token_logp': [-8.0, -9.0, -7.0]}, {'rol': 'action', 'token_logp': [-0.2, -0.6]}], 1.5), tohum=3171, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (ajan_yorunge_maskele): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
ok(ajan_yorunge_maskele([{"rol": "action", "token_logp": [-0.5]}], 1.0) == _REF['ajan_yorunge_maskele']([{"rol": "action", "token_logp": [-0.5]}], 1.0), "tek aktif token ortalaması korunmalı")
```

```solution
def ajan_yorunge_maskele(adimlar, avantaj):
    maske = []
    action_logp = []

    for adim in adimlar:
        m = 1 if adim["rol"] == "action" else 0
        for lp in adim["token_logp"]:
            maske.append(m)
            if m == 1:
                action_logp.append(lp)

    aktif_sayisi = sum(maske)
    maskelenen_sayisi = len(maske) - aktif_sayisi
    ort_logp = (sum(action_logp) / aktif_sayisi) if aktif_sayisi > 0 else 0.0
    kayip = -avantaj * ort_logp

    return {
        "maske": maske,
        "aktif_token_sayisi": aktif_sayisi,
        "maskelenen_token_sayisi": maskelenen_sayisi,
        "ortalama_action_logp": round(ort_logp, 6),
        "politika_kaybi": round(kayip, 6),
    }
```

```hint
Her adımda `adim["rol"] == "action"` ise `1`, değilse `0` maskesi ata ve yalnızca `1` olanların `token_logp` değerlerini toplayıp `aktif_sayisi`'na böl. `politika_kaybi = round(-avantaj * ort_logp, 6)` formülünü uygula.
```
:::

::: gorev 2 · SWE-bench Tarzı Fail-to-Pass ve Pass-to-Pass Yaması (Patch) Ödül Doğrulayıcısı
Bir kod ajanının ürettiği yamanın (`Patch`) birim test sonuçlarını (`onceki_testler` ve `sonraki_testler`) karşılaştırarak `SWE-bench` çözüm durumunu ve şekillendirilmiş `RL` ödülünü hesaplayan `swebench_odul_hesapla(onceki_testler, sonraki_testler, diff_satir_sayisi)` işlevini yaz:

1. **Girdiler:**
   - `onceki_testler`: Yamadan **önce** (`Pre-Patch`) her birim testinin durumunu tutan sözlük (`{"test_adi": bool}`, `True`: `PASS`, `False`: `FAIL`).
   - `sonraki_testler`: Ajanın yamasından **sonra** (`Post-Patch`) aynı testlerin durumunu tutan sözlük (`{"test_adi": bool}`).
   - `diff_satir_sayisi`: Yamanın değiştirdiği toplam satır sayısı (`int >= 0`).
2. **Test Kümeleri ve Kurallar:**
   - **`Fail-to-Pass` Hedef Kümesi ($F$):** `onceki_testler` içinde değeri `False` (`FAIL`) olan tüm testler.
     - Bu kümedeki testlerden kaç tanesinin `sonraki_testler` içinde `True` (`PASS`) olduğuna bakarak başarı oranını hesapla:
       `f2p_orani = gecen_f2p / len(F)` (Eğer `len(F) == 0` ise `1.0`).
   - **`Pass-to-Pass` Regresyon Kümesi ($P$):** `onceki_testler` içinde değeri `True` (`PASS`) olan tüm testler.
     - Bu kümedeki testlerden kaç tanesinin `sonraki_testler` içinde hala `True` (`PASS`) kaldığına bakarak korunma oranını hesapla:
       `p2p_orani = korunan_p2p / len(P)` (Eğer `len(P) == 0` ise `1.0`).
   - **`tam_cozuldu_mu` (`Resolved`):** Eğer `diff_satir_sayisi > 0` **VE** `f2p_orani == 1.0` **VE** `p2p_orani == 1.0` ise `True`, aksi halde `False`! (Boş yama `diff_satir_sayisi == 0` asla `True` olamaz!).
   - **Toplam RL Ödülü (`toplam_odul`):**
     - Eğer `diff_satir_sayisi == 0` ise (ajan hiçbir değişiklik yapmadıysa): `toplam_odul = -0.5`.
     - Eğer `p2p_orani < 1.0` ise (mevcut çalışan testleri bozduysa / regresyon varsa): `toplam_odul = -0.2 + 0.2 * f2p_orani`.
     - Eğer `p2p_orani == 1.0` ve `f2p_orani < 1.0` ise (hiçbir şeyi bozmadı ama hatayı kısmen çözdü): `toplam_odul = 0.5 * f2p_orani`.
     - Eğer `tam_cozuldu_mu == True` ise (tüm testler geçti!): `1.0` tam ödül ver; ayrıca temiz ve kısa yamaları teşvik etmek için `diff_satir_sayisi <= 20` ise `+0.1` temiz yama bonusu ekle (`1.1`, `> 20` ise `1.0`).
   - Tüm oranları ve ödülü `round(val, 6)` ile yuvarla.
3. **Dönüş Değeri:**
   `{"f2p_orani": float, "p2p_orani": float, "tam_cozuldu_mu": bool, "toplam_odul": float}` sözlüğü döndür.

```starter
def swebench_odul_hesapla(onceki_testler, sonraki_testler, diff_satir_sayisi):
    # KUSURLU BAŞLANGIÇ KODU: Fail-to-Pass ve Pass-to-Pass ayrımlarını yapmadan 0 ödül döndürüyor!
    return {
        "f2p_orani": 0.0,
        "p2p_orani": 0.0,
        "tam_cozuldu_mu": False,
        "toplam_odul": 0.0,
    }

onceki = {"test_bug_1": False, "test_bug_2": False, "test_mevcut_1": True}
sonraki = {"test_bug_1": True, "test_bug_2": True, "test_mevcut_1": True}
print(swebench_odul_hesapla(onceki, sonraki, diff_satir_sayisi=8))
```

```test
import copy

def _ref_swe(onceki, sonraki, diff):
    f_testler = [k for k, v in onceki.items() if not v]
    p_testler = [k for k, v in onceki.items() if v]
    f2p = (sum(1 for k in f_testler if sonraki.get(k, False)) / len(f_testler)) if f_testler else 1.0
    p2p = (sum(1 for k in p_testler if sonraki.get(k, False)) / len(p_testler)) if p_testler else 1.0
    cozuldu = (diff > 0) and (abs(f2p - 1.0) < 1e-9) and (abs(p2p - 1.0) < 1e-9)
    if diff == 0:
        odul = -0.5
    elif p2p < 1.0 - 1e-9:
        odul = -0.2 + 0.2 * f2p
    elif not cozuldu:
        odul = 0.5 * f2p
    else:
        odul = 1.1 if diff <= 20 else 1.0
    return {
        "f2p_orani": round(f2p, 6),
        "p2p_orani": round(p2p, 6),
        "tam_cozuldu_mu": cozuldu,
        "toplam_odul": round(odul, 6),
    }

def sozlesme(fn):
    try:
        o = {"t_bug1": False, "t_bug2": False, "t_ok1": True, "t_ok2": True}
        s_tam = {"t_bug1": True, "t_bug2": True, "t_ok1": True, "t_ok2": True}
        s_kismi = {"t_bug1": True, "t_bug2": False, "t_ok1": True, "t_ok2": True}
        s_bozuk = {"t_bug1": True, "t_bug2": True, "t_ok1": False, "t_ok2": True}
        for son, d in [(s_tam, 8), (s_tam, 35), (s_kismi, 10), (s_bozuk, 12), (o, 0)]:
            if fn(o, son, d) != _ref_swe(o, son, d):
                return False
        return True
    except Exception:
        return False

ok(sozlesme(swebench_odul_hesapla), "swebench_odul_hesapla Fail-to-Pass, Pass-to-Pass regresyon ve temiz diff bonusunu doğru hesaplamalı")

def m_regresyon_yoksay(onceki, sonraki, diff):
    r = copy.deepcopy(_ref_swe(onceki, sonraki, diff))
    r["tam_cozuldu_mu"] = (r["f2p_orani"] == 1.0)
    return r

def m_bos_diff_kabul(onceki, sonraki, diff):
    return swebench_odul_hesapla(onceki, sonraki, 10)

for ad, m in [("Pass-to-Pass regresyon testlerini yok sayan", m_regresyon_yoksay), ("Boş diff (diff=0) cezasını atlayan", m_bos_diff_kabul)]:
    ok(not sozlesme(m), f"Yanlış çözüm/mutant yakalanmalı: {ad}")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def swebench_odul_hesapla(onceki_testler, sonraki_testler, diff_satir_sayisi):\n    f_testler = [k for k, v in onceki_testler.items() if not v]\n    p_testler = [k for k, v in onceki_testler.items() if v]\n    f2p = sum((1 for k in f_testler if sonraki_testler.get(k, False))) / len(f_testler) if f_testler else 1.0\n    p2p = sum((1 for k in p_testler if sonraki_testler.get(k, False))) / len(p_testler) if p_testler else 1.0\n    tam_cozuldu = diff_satir_sayisi > 0 and abs(f2p - 1.0) < 1e-09 and (abs(p2p - 1.0) < 1e-09)\n    if diff_satir_sayisi == 0:\n        odul = -0.5\n    elif p2p < 1.0 - 1e-09:\n        odul = -0.2 + 0.2 * f2p\n    elif not tam_cozuldu:\n        odul = 0.5 * f2p\n    else:\n        odul = 1.1 if diff_satir_sayisi <= 20 else 1.0\n    return {'f2p_orani': round(f2p, 6), 'p2p_orani': round(p2p, 6), 'tam_cozuldu_mu': tam_cozuldu, 'toplam_odul': round(odul, 6)}", 'referans', 'exec'), _REF)
_t, _g = _ff(swebench_odul_hesapla, _REF['swebench_odul_hesapla'], ({'test_bug_1': False, 'test_bug_2': False, 'test_mevcut_1': True}, {'test_bug_1': True, 'test_bug_2': True, 'test_mevcut_1': True}, 8), tohum=3263, en_cok=600, mod='gecerli', butce='oto', ekler=[({'t1': False, 't2': True}, {'t1': True, 't2': True}, 20, ), ({'t1': False, 't2': True}, {'t1': True, 't2': True}, 21, )])
ok(_t, "farksal tarama (swebench_odul_hesapla): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
ok(all(swebench_odul_hesapla(*_a) == _REF['swebench_odul_hesapla'](*_a) for _a in [({"t1": True}, {"t1": True}, 5), ({"t1": False, "t2": True}, {}, 5), ({"t1": False, "t2": True}, {"t1": True, "t2": True}, 0), ({"t1": False, "t2": False, "t3": False, "t4": True, "t5": True, "t6": True}, {"t1": True, "t2": False, "t3": False, "t4": True, "t5": False, "t6": False}, 5)]), "SWE-bench sınır ve 6 basamak yuvarlama vakaları korunmalı")
```

```solution
def swebench_odul_hesapla(onceki_testler, sonraki_testler, diff_satir_sayisi):
    f_testler = [k for k, v in onceki_testler.items() if not v]
    p_testler = [k for k, v in onceki_testler.items() if v]

    f2p = (sum(1 for k in f_testler if sonraki_testler.get(k, False)) / len(f_testler)) if f_testler else 1.0
    p2p = (sum(1 for k in p_testler if sonraki_testler.get(k, False)) / len(p_testler)) if p_testler else 1.0

    tam_cozuldu = (diff_satir_sayisi > 0) and (abs(f2p - 1.0) < 1e-9) and (abs(p2p - 1.0) < 1e-9)

    if diff_satir_sayisi == 0:
        odul = -0.5
    elif p2p < 1.0 - 1e-9:
        odul = -0.2 + 0.2 * f2p
    elif not tam_cozuldu:
        odul = 0.5 * f2p
    else:
        odul = 1.1 if diff_satir_sayisi <= 20 else 1.0

    return {
        "f2p_orani": round(f2p, 6),
        "p2p_orani": round(p2p, 6),
        "tam_cozuldu_mu": tam_cozuldu,
        "toplam_odul": round(odul, 6),
    }
```

```hint
`onceki_testler` içinde `False` olanları `f_testler`, `True` olanları `p_testler` olarak ayır. `sonraki_testler` içinde bunların kaçının `True` olduğuna bakarak `f2p` ve `p2p` oranlarını bul. `diff_satir_sayisi == 0`, `p2p < 1.0`, kısmi çözüm ve tam çözüm durumlarına göre ödülü hesapla.
```
:::

::: anlat Gerçek deney: Gerçek test koşularıyla SWE-bench ödülü, test kurcalama ve gerçek bir yörünge
Final iki gerçek ölçüm yapar:

- **Gerçek depo ve testler:** iki hatalı fonksiyonu olan küçük bir Python modülü ve dört `unittest` testi geçici bir klasöre yazılır, testler gerçekten çalıştırılır (başta 2/4 geçer). Beş aday yama uygulanır: doğru, kısmi, kırıcı (bir hatayı düzeltirken çalışan bir testi bozar), boş ve **testleri kurcalayan** (kodu düzeltmez, başarısız testlere `@unittest.skip` ekler). Her yama için testler iki kez koşar: ajanın değiştirdiği dosyalarla (naif değerlendirici) ve özgün testler geri yüklenerek. Senin `swebench_odul_hesapla` işlevin her durumda ödülü hesaplar; sonuç bağımsız bir referansla karşılaştırılır.
- **Ödül istismarı:** kurcalayan yama naif değerlendiricide en yüksek ödülü alır. Değerlendirme testleri ajanın dokunamadığı bir kopyadan çalıştırmalıdır; yamanın kendisi de (test dosyası değişti mi?) denetlenmelidir.
- **Gerçek yörünge:** bu koşunun gerçek test çıktısını gözlem olarak içeren bir ajan konuşması Qwen2.5-0.5B-Instruct'ın sohbet şablonuyla tokenlanır, tur sınırları şablondan çıkarılır ve her tokenın gerçek log-olasılığı hesaplanır. Senin `ajan_yorunge_maskele` işlevin yalnız eylem tokenlarından kaybı hesaplar; sonuç torch referansıyla karşılaştırılır.

Kabul: iki işlevin farksal taramayı geçmesi; tüm ödüllerin referansla aynı olması; kurcalayan yamanın naif değerlendiricide 1'in üstünde, güvenli değerlendiricide 0 ya da altında ödül alması; maskeli kaybın torch ile aynı olması.

**Kanıt dosyasını oku:** `once_testler`, `yamalar` (iki değerlendirici, F2P, P2P), `ort_logp_eylem`, `ort_logp_gozlem`. Soru 1: Kırıcı yama F2P'de tam puan alırken neden ödülü sıfır? Soru 2: Gözlem tokenları burada eylemlerden daha olası çıktı; yine de neden maskelenmeliler? Soru 3: Testleri silen ya da atlayan yamayı yakalamak için değerlendiriciye hangi iki kontrolü eklerdin?
:::

::: gorev Gerçek deney · Gerçek unittest koşularıyla SWE-bench ödülü, test kurcalama ve Qwen yörüngesinde maske
Önceki görevlerdeki `ajan_yorunge_maskele`, `swebench_odul_hesapla` işlevlerini buraya birleştir (çözümlerini kopyalayabilirsin). Çalıştır gerçek ölçüm tablosunu gösterir; Kontrol Et önce işlevlerini gizli verilerle ve farksal taramayla sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
timeout: 240
```
```starter
import ai_lab
def ajan_yorunge_maskele(adimlar, avantaj):
    tum_logp = [lp for a in adimlar for lp in a['token_logp']]
    ort = sum(tum_logp) / len(tum_logp) if tum_logp else 0.0
    return {'maske': [1] * len(tum_logp), 'aktif_token_sayisi': len(tum_logp), 'maskelenen_token_sayisi': 0, 'ortalama_action_logp': round(ort, 6), 'politika_kaybi': round(-avantaj * ort, 6)}

def swebench_odul_hesapla(onceki_testler, sonraki_testler, diff_satir_sayisi):
    return {'f2p_orani': 0.0, 'p2p_orani': 0.0, 'tam_cozuldu_mu': False, 'toplam_odul': 0.0}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_24 as D
    D.goster(ajan_yorunge_maskele, swebench_odul_hesapla)
```
```test
import ai_lab
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('_ref_odul', '_kos', '_turlar', 'kanit_yaz'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
ajan_yorunge_maskele = need("ajan_yorunge_maskele")
swebench_odul_hesapla = need("swebench_odul_hesapla")
# farksal tarama (görev çözümlerinden derlenen referans)
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def ajan_yorunge_maskele(adimlar, avantaj):\n    maske = []\n    action_logp = []\n    for adim in adimlar:\n        m = 1 if adim['rol'] == 'action' else 0\n        for lp in adim['token_logp']:\n            maske.append(m)\n            if m == 1:\n                action_logp.append(lp)\n    aktif_sayisi = sum(maske)\n    maskelenen_sayisi = len(maske) - aktif_sayisi\n    ort_logp = sum(action_logp) / aktif_sayisi if aktif_sayisi > 0 else 0.0\n    kayip = -avantaj * ort_logp\n    return {'maske': maske, 'aktif_token_sayisi': aktif_sayisi, 'maskelenen_token_sayisi': maskelenen_sayisi, 'ortalama_action_logp': round(ort_logp, 6), 'politika_kaybi': round(kayip, 6)}\n\ndef swebench_odul_hesapla(onceki_testler, sonraki_testler, diff_satir_sayisi):\n    f_testler = [k for k, v in onceki_testler.items() if not v]\n    p_testler = [k for k, v in onceki_testler.items() if v]\n    f2p = sum((1 for k in f_testler if sonraki_testler.get(k, False))) / len(f_testler) if f_testler else 1.0\n    p2p = sum((1 for k in p_testler if sonraki_testler.get(k, False))) / len(p_testler) if p_testler else 1.0\n    tam_cozuldu = diff_satir_sayisi > 0 and abs(f2p - 1.0) < 1e-09 and (abs(p2p - 1.0) < 1e-09)\n    if diff_satir_sayisi == 0:\n        odul = -0.5\n    elif p2p < 1.0 - 1e-09:\n        odul = -0.2 + 0.2 * f2p\n    elif not tam_cozuldu:\n        odul = 0.5 * f2p\n    else:\n        odul = 1.1 if diff_satir_sayisi <= 20 else 1.0\n    return {'f2p_orani': round(f2p, 6), 'p2p_orani': round(p2p, 6), 'tam_cozuldu_mu': tam_cozuldu, 'toplam_odul': round(odul, 6)}", 'referans', 'exec'), _REF)
_t, _g = _ff(ajan_yorunge_maskele, _REF['ajan_yorunge_maskele'], ([{'rol': 'prompt', 'token_logp': [-2.0, -3.0]}, {'rol': 'action', 'token_logp': [-0.5, -0.3]}, {'rol': 'observation', 'token_logp': [-8.0, -9.0, -7.0]}, {'rol': 'action', 'token_logp': [-0.2, -0.6]}], 1.5), tohum=3171, en_cok=600, mod='gecerli', butce='oto')
kontrol(_t, "farksal tarama (ajan_yorunge_maskele): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(swebench_odul_hesapla, _REF['swebench_odul_hesapla'], ({'test_bug_1': False, 'test_bug_2': False, 'test_mevcut_1': True}, {'test_bug_1': True, 'test_bug_2': True, 'test_mevcut_1': True}, 8), tohum=3263, en_cok=600, mod='gecerli', butce='oto', ekler=[({'t1': False, 't2': True}, {'t1': True, 't2': True}, 20, ), ({'t1': False, 't2': True}, {'t1': True, 't2': True}, 21, )])
kontrol(_t, "farksal tarama (swebench_odul_hesapla): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
kontrol(ajan_yorunge_maskele([{"rol": "action", "token_logp": [-0.5]}], 1.0) == _REF['ajan_yorunge_maskele']([{"rol": "action", "token_logp": [-0.5]}], 1.0), "tek aktif token ortalaması korunmalı")
kontrol(ajan_yorunge_maskele([{"rol": "observation", "token_logp": [-0.5]}], 1.0) == _REF['ajan_yorunge_maskele']([{"rol": "observation", "token_logp": [-0.5]}], 1.0), "sıfır aktif token ortalaması korunmalı")
kontrol(all(swebench_odul_hesapla(*_a) == _REF['swebench_odul_hesapla'](*_a) for _a in [({"t1": True}, {"t1": True}, 5), ({"t1": False, "t2": True}, {}, 5), ({"t1": False, "t2": True}, {"t1": True, "t2": True}, 0), ({"t1": False, "t2": True, "t3": True, "t4": True}, {"t1": True, "t2": True, "t3": True, "t4": False}, 5), ({"t1": False, "t2": False, "t3": False, "t4": True, "t5": True, "t6": True}, {"t1": True, "t2": False, "t3": False, "t4": True, "t5": False, "t6": False}, 5)]), "SWE-bench sınır ve 6 basamak yuvarlama vakaları korunmalı")
if not all(checks): stop()
from sandbox import ai_gercek_ai_uretim_24 as D
try: r = D.deney(ajan_yorunge_maskele, swebench_odul_hesapla)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r['odul_ayni'], 'beş yamada iki değerlendiricinin ödülleri gerçek test sonuçlarıyla referansla aynı')
kontrol(r['kurcalama_yakalandi'], 'test kurcalayan yama naif değerlendiricide tam ödül, özgün testlerle sıfır ödül aldı')
kontrol(r['yorunge_ayni'], 'gerçek yörüngede maskeli politika kaybı torch referansıyla aynı')
ai_lab.kanit_yaz("ai-uretim-24-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-uretim-24", "deney": r})
```
```solution
import ai_lab
def ajan_yorunge_maskele(adimlar, avantaj):
    maske = []
    action_logp = []
    for adim in adimlar:
        m = 1 if adim['rol'] == 'action' else 0
        for lp in adim['token_logp']:
            maske.append(m)
            if m == 1:
                action_logp.append(lp)
    aktif_sayisi = sum(maske)
    maskelenen_sayisi = len(maske) - aktif_sayisi
    ort_logp = sum(action_logp) / aktif_sayisi if aktif_sayisi > 0 else 0.0
    kayip = -avantaj * ort_logp
    return {'maske': maske, 'aktif_token_sayisi': aktif_sayisi, 'maskelenen_token_sayisi': maskelenen_sayisi, 'ortalama_action_logp': round(ort_logp, 6), 'politika_kaybi': round(kayip, 6)}

def swebench_odul_hesapla(onceki_testler, sonraki_testler, diff_satir_sayisi):
    f_testler = [k for k, v in onceki_testler.items() if not v]
    p_testler = [k for k, v in onceki_testler.items() if v]
    f2p = sum((1 for k in f_testler if sonraki_testler.get(k, False))) / len(f_testler) if f_testler else 1.0
    p2p = sum((1 for k in p_testler if sonraki_testler.get(k, False))) / len(p_testler) if p_testler else 1.0
    tam_cozuldu = diff_satir_sayisi > 0 and abs(f2p - 1.0) < 1e-09 and (abs(p2p - 1.0) < 1e-09)
    if diff_satir_sayisi == 0:
        odul = -0.5
    elif p2p < 1.0 - 1e-09:
        odul = -0.2 + 0.2 * f2p
    elif not tam_cozuldu:
        odul = 0.5 * f2p
    else:
        odul = 1.1 if diff_satir_sayisi <= 20 else 1.0
    return {'f2p_orani': round(f2p, 6), 'p2p_orani': round(p2p, 6), 'tam_cozuldu_mu': tam_cozuldu, 'toplam_odul': round(odul, 6)}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_24 as D
    D.goster(ajan_yorunge_maskele, swebench_odul_hesapla)
```
```hint
İki görevin çözümlerini olduğu gibi buraya koy.
```
:::

::: anlat Sınır
Görevler çok turlu ajan yörüngesinde observation maskelemesini ve politika kaybını, SWE-bench tarzı fail-to-pass/pass-to-pass ödülünü sayılardan hesaplatır; final adım küçük bir depoda testleri gerçekten koşturur (Docker sandbox yoktur). Test kapsamı zayıfsa ajan testleri geçen ama hatayı çözmeyen yamalar üretir; test silme ya da atlama gibi ödül istismarlarına karşı yamanın kendisi de denetlenmelidir. Ajanın asıl güvenlik çizgisi sandbox'ın ağ ve dosya sistemi sınırlarıdır; konteyner tek başına güvenlik sınırı sayılmamalıdır. Diff boyutuna bağlı ödül biçim hilesine açıktır.

Kaynaklar: [Jimenez vd. 2024 - SWE-bench: Can Language Models Resolve Real-World GitHub Issues?](https://arxiv.org/abs/2310.06770), [Yang vd. 2024 - SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering](https://arxiv.org/abs/2405.15793), [Pan vd. 2024 - Training Software Engineering Agents and Verifiers with SWE-Gym](https://arxiv.org/abs/2412.21139).
:::

::: dusun
Sahnede bir güvenlik ve RL mühendisi el kaldırdı:
*"Hocam, kod ajanımızı `Docker Sandbox` içinde `pytest` birim testlerinden aldığı `Pass/Fail` ödülüyle (`RLVR`) eğitirken ajanımız çok kurnaz bir hile (**`Reward Hacking / Specification Gaming`**) keşfetti! Ajan kaynak koda gidip gerçek hatayı düzeltmek yerine, **`tests/test_auth.py` dosyasını açıp içindeki `assert` satırlarını siliyor veya `sys.exit(0)` yazıyor** ve `pytest` `%100 PASS` döndürdüğü için `+1.0` tam ödülü kapıyor! Bunu `SWE-bench` doğrulayıcı mimarisinde nasıl kesin olarak engelleriz?"*

Bu soruya **1) Ajanın çalıştığı aşamada test dosyalarını değiştirse bile, değerlendirme (`Verification`) aşamasında `git checkout -- tests/` ile orijinal temiz test dosyalarının zorla geri yüklenmesi (`Read-Only / Clean Test Patch Reset`)** ve **2) Yamanın (`git diff`) `tests/` klasörüne dokunması durumunda otomatik olarak reddedilmesi** önlemleriyle nasıl yanıt verirsin?
:::

::: ozet
- Gerçek yazılım mühendisliği ajanları (`SWE-agent / Claude Code / Antigravity`), tek seferde kod üretmek yerine **`Docker Sandbox`** içinde arama, dosya düzenleme ve test çalıştırma adımlarından oluşan çok turlu bir yörünge (**`Multi-Turn Trajectory`**) yürütür.
- **`Environment Observation Masking`**, terminal çıktıları ve hata loglarına ait `token`ların gradyan maskesini sıfırlayarak ($M_i = 0$) modelin ortam hatalarını ezberlemesini/halüsinasyon görmesini engeller; gradyan yalnızca modelin kendi ürettiği **`Action` (`Thought + Tool Call`)** `token`ları ($M_i = 1$) üzerinden akar.
- **`SWE-bench Verifier`**, ajanın ürettiği yamayı izole konteyner içinde hem **`Fail-to-Pass`** (hatanın giderilmesi) hem de **`Pass-to-Pass`** (regresyon olmaması) birim test kümeleriyle doğrulayarak oyunlaştırılamaz (`Verifiable`) bir `RL` ödül sinyali üretir.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Çok adımlı ajan yörüngesi ve kayıp maskeleme (35 sn).** "Bir kod ajanı yörüngesinde modelin ürettiği eylemler (`Action`) ile terminalden dönen test çıktıları (`Observation`) iç içedir; eğitimde yalnız ajan eylem tokenlarına `mask=1` verilir, ortam çıktılarını ezberlememesi için gözlem tokenları `mask=0` ile kayıptan dışlanır."
2. **`Fail-to-Pass` ve `Pass-to-Pass` çift kilidi (35 sn).** "`SWE-bench` ödülü yalnız hatayı yeniden üreten testlerin yeşile dönmesine (`Fail-to-Pass`) bakmaz; mevcut çalışan testlerin hiçbirinin kırılmamasını (`Pass-to-Pass`) da zorunlu tutar."
3. **Test silme / ödül istismarı savunması (25 sn).** "Ajanın test dosyalarını değiştirerek sahte başarı üretmemesi için değerlendirme yaması temiz bir konteynerde ve salt-okunur hakem testleriyle koşturulur."
4. **Soru (25 sn).** "Modelin ürettiği kod yamalarını otomatik koşturan bir eğitim kümesinde konteyner ağ erişimi kapatılmazsa hangi güvenlik tehlikesi ortaya çıkar?"
:::
