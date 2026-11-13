---
id: ai-uretim-18
title: "1M–10M Uzun Bağlam Mühendisliği: Position Interpolation, NTK-Aware RoPE, YaRN ve Ring Attention"
summary: "Eğitim bağlam penceresini aşarken RoPE frekanslarını koruyan Position Interpolation, NTK-Aware ölçekleme ve YaRN rampa/sıcaklık düzeltmesi ile milyon tokenlık dizileri GPU halkasında bölen Ring Attention."
esleme: ai-uretim-12, ai-uretim-17, ai-temel-07
track: ai-uretim
order: 18
duration_minutes: 40
difficulty: ileri
xp: 320
prerequisites: [ai-uretim-17]
tags: [long-context, position-interpolation, ntk-aware-rope, yarn, ring-attention, distributed-attention]
---

::: anlat
## Uzun context için position ölçekleme

Context uzatmak yalnızca daha büyük bir sayı ayarı vermek değildir; position temsili, training verisi ve hesap düzeni birlikte etkilenir. YaRN frekans ölçeklemesini ve Ring Attention blok hesabını inceleyeceksin. Bu görev, gerçek bir modelin milyonlarca tokenda doğru çalıştığını ölçmez.

Ancak $L_{\text{orig}} = 4,096$ ile eğitilmiş bir modele doğrudan $m = 32,768$. pozisyondaki bir token'ı verirsen model anında saçmalamaya başlar (`Perplexity Explosion`)! Çünkü modelin **RoPE (`Rotary Position Embedding`)** saat ibreleri eğitim boyunca $m > 4096$ açılarını **hiç görmemiştir (`Out-of-Distribution Rotation Angles`)**!

Peki 4K'da eğitilmiş bir modeli 128K veya 1M bağlama çıkarırken karşılaştığımız **iki dev mühendislik engelini** nasıl aşarız?
1. **Matematiksel Engel (`RoPE Extrapolation`):** Saat ibrelerinin yüksek frekanslı yerel hassasiyetini bozmadan uzun mesafeleri nasıl temsil ederiz? $\longrightarrow$ **`NTK-Aware Scaling` & `YaRN`**
2. **Donanımsal Engel (`Single-GPU Memory Limit`):** 1 Milyon tokenlık bir dizinin aktivasyonları ve KV-Cache'i tek bir `80 GB H100` GPU'ya **fiziksel olarak sığmaz!** $\longrightarrow$ **`Ring Attention` (Dağıtık Halka Dikkat)**

---

### 1. Saat İbresi Benzetmesi: Neden Düz `Position Interpolation (PI)` Yerel Detayları Bozar?

`RoPE` içindeki $d/2$ adet 2B düzlem çiftini bir **kol saatinin ibreleri** gibi düşün ($\theta_i = b^{-2i/d}$, dalga boyu $\lambda_i = \frac{2\pi}{\theta_i}$):
- **İlk boyutlar ($i \approx 0$, Yüksek Frekans / Kısa Dalga Boyu):** Saniye ibresi gibidir; her token'da hızlıca döner ve **yan yana duran kelimelerin (`"not good"` vs `"good not"`) yerel sırasını** ayırt eder.
- **Son boyutlar ($i \approx d/2$, Düşük Frekans / Uzun Dalga Boyu):** Akrep/Takvim ibresi gibidir; binlerce token'da bir çok yavaş döner ve **paragraf/bölüm mesafesini** ölçer.

```
  1. LINEAR POSITION INTERPOLATION (PI): m' = m / s
     • Tüm ibreleri (saniye dahil!) s = 8 kat yavaşlatır.
     • SONUÇ: Yan yana duran kelimelerin açı farkı birbirine yapışır -> Yerel çözünürlük bozulur!

  2. YaRN (NTK-by-Parts Ramp): Frekansları 3 Bölgeye Ayır!
     • Yüksek Frekans (Saniye ibresi, r_i > beta)  --> HİÇ DOKUNMA! (gamma = 1.0, yerel sıra korunsun)
     • Düşük Frekans  (Akrep ibresi,  r_i < alpha) --> TAM İNTERPOLE ET! (theta' = theta / s)
     • Orta Frekans   (Yelkovan, alpha <= r_i <= beta) --> Yumuşak Rampa (Smooth Ramp) ile geçiş yap!
```

#### A) `NTK-Aware Scaling` (Taban Frekansı $\theta_{\text{base}}$ Büyütme)
Pozisyonu $m/s$ diye bölmek yerine **RoPE tabanını (`base` $b = 10,000$)** büyütürüz:
$$b' = b \cdot s^{\frac{d}{d-2}}$$
Böylece düşük frekanslı boyutlar daha çok yavaşlarken yüksek frekanslı boyutlar neredeyse hiç bozulmaz! (Llama-3'ün tabanı $10,000$'den $500,000$'e çıkarmasının sebebi budur!).

#### B) `YaRN` (*Yet another RoPE extensioN* — Peng et al., 2023; DeepSeek & Qwen Standardı)
**`YaRN`**, her boyut çiftinin eğitim bağlamı $L_{\text{orig}}$ içinde kaç tam tur attığını ($r_i = \frac{L_{\text{orig}}}{\lambda_i}$) hesaplar ve bir **Rampa Fonksiyonu $\gamma(r_i) \in [0, 1]$** (`alpha=1`, `beta=32` sınırlarıyla) tanımlar:

$$\gamma(r) = \begin{cases} 0, & r < \alpha \quad (\text{Düşük Frekans: Tam İnterpolasyon}) \\ 1, & r > \beta \quad (\text{Yüksek Frekans: Ekstrapolasyon / Dokunma!}) \\ \frac{r - \alpha}{\beta - \alpha}, & \alpha \le r \le \beta \quad (\text{Orta Frekans: Doğrusal Rampa}) \end{cases}$$

$$\theta_i^{\text{YaRN}} = (1 - \gamma(r_i)) \frac{\theta_i}{s} + \gamma(r_i) \theta_i$$

Ayrıca bağlam uzadıkça Softmax entropisinin dağılmasını önlemek için dikkat skorlarını bir **Sıcaklık Çarpanıyla (`Attention Temperature Scaling` $\sqrt{1/t} = 0.1 \ln(s) + 1$)** keskinleştirir!

---

### 2. `Ring Attention` (Liu et al., 2023): 1 Milyon Token'ı $N$ GPU Halkasında Döndürmek!

Şimdi 1 Milyon tokenlık bir diziyi $N = 8$ GPU'ya nasıl böleceğimize bakalım:
- Diziyi $8$ eşit parçaya ($125\text{K}$ token/GPU) böleriz: `GPU 0` ilk $Q_0, K_0, V_0$ bloğunu, `GPU 1` ikinci $Q_1, K_1, V_1$ bloğunu tutar.
- **Sorun:** Attention hesabı için `GPU 7`'deki sorguların (`Q_7`), diğer tüm GPU'lardaki $K_0 \dots K_6$ bloklarını görmesi gerekir! Hepsini tek bir GPU'da toplarsak bellek patlar!
- **`Ring Attention` Çözümü:** Sorgular ($Q_i$) kendi GPU'sunda **sabit durur**. GPU'lar sanal bir **Halka (`Ring Topology`)** oluşturur:
  1. Her adımda her GPU, elindeki $(K, V)$ bloğunu kullanarak yerel $Q_i$ için **4. derste öğrendiğimiz `FlashAttention Online Softmax` ($m_i, \ell_i, O_i$)** akümülatörünü günceller!
  2. **Aynı anda arka planda (`Asynchronous P2P Communication Overlap`)**, elindeki $(K, V)$ bloğunu sağındaki komşu GPU'ya (`GPU k -> GPU (k+1) % N`) gönderir ve solundaki komşudan yeni $(K, V)$ bloğunu alır!
  3. Tam $N$ adım sonunda her $(K, V)$ bloğu halkayı tam tur dönmüş olur ve her GPU kendi $O_i$ çıktısını **hiçbir zaman tüm diziyi belleğinde toplamadan, sıfır iletişim darboğazıyla** tam (`exact`) olarak hesaplar!

```
          ┌───► [ GPU 0: Q_0 sabit ] ─── (K,V Gönder) ───► [ GPU 1: Q_1 sabit ] ───┐
          │       (Online Softmax m0, l0, O0)                (Online Softmax m1, l1, O1)
   (K,V Gönder)                                                              (K,V Gönder)
          │       (Online Softmax m3, l3, O3)                (Online Softmax m2, l2, O2)
          └─── [ GPU 3: Q_3 sabit ] ◄─── (K,V Gönder) ──── [ GPU 2: Q_2 sabit ] ◄──┘
```

Şimdi saf Python ile hem `YaRN` frekans rampasını hem de `Ring Attention` halka güncellemesini çalıştıralım:

```python
import math

def yarn_rampa(r, alpha=1.0, beta=32.0):
    if r < alpha:
        return 0.0
    if r > beta:
        return 1.0
    return (r - alpha) / (beta - alpha)

# Örnek: 3 farklı RoPE boyutunun tur sayısı r_i = L / dalga_boyu
for etiket, r_degeri in [("Akrep (r=0.5)", 0.5), ("Yelkovan (r=16.5)", 16.5), ("Saniye (r=64.0)", 64.0)]:
    g = yarn_rampa(r_degeri)
    print(f"{etiket:18s} -> Rampa gamma = {g:.2f} (Orijinal Frekans Korunma Oranı: %{g*100:.0f})")
```

---

### 3. Gerçek Üretim Kodu: PyTorch `YaRNRotaryEmbedding` ve Dağıtık `RingAttention`

```python norun
import math
import torch
import torch.nn as nn
import torch.distributed as dist

class YaRNRotaryEmbedding(nn.Module):
    def __init__(self, dim: int, max_pos: int = 131072, orig_max_pos: int = 4096, base: float = 10000.0, scale: float = 32.0, alpha: float = 1.0, beta: float = 32.0):
        super().__init__()
        pos_freqs = base ** (torch.arange(0, dim, 2).float() / dim)
        inv_freq_extrapolation = 1.0 / pos_freqs
        inv_freq_interpolation = 1.0 / (scale * pos_freqs)

        # Her boyutun orijinal bağlamdaki tur sayısı: r = L_orig / (2 * pi * base^(2i/d))
        wavelengths = 2 * math.pi * pos_freqs
        r = orig_max_pos / wavelengths
        ramp = torch.clamp((r - alpha) / (beta - alpha), 0.0, 1.0)

        # YaRN Birleşik Frekans ve Dikkat Sıcaklık Ölçeklemesi (mscale)
        inv_freq = inv_freq_interpolation * (1.0 - ramp) + inv_freq_extrapolation * ramp
        self.register_buffer("inv_freq", inv_freq, persistent=False)
        self.mscale = float(0.1 * math.log(scale) + 1.0)

def ring_pass_kv_async(k_block: torch.Tensor, v_block: torch.Tensor, group: dist.ProcessGroup):
    """Mevcut GPU'daki FlashAttention hesabı sürerken KV bloğunu asenkron olarak sonraki GPU'ya aktarır."""
    rank = dist.get_rank(group)
    world_size = dist.get_world_size(group)
    next_rank = (rank + 1) % world_size
    prev_rank = (rank - 1 + world_size) % world_size

    k_recv, v_recv = torch.empty_like(k_block), torch.empty_like(v_block)
    ops = [
        dist.P2POp(dist.isend, k_block, next_rank, group),
        dist.P2POp(dist.isend, v_block, next_rank, group),
        dist.P2POp(dist.irecv, k_recv, prev_rank, group),
        dist.P2POp(dist.irecv, v_recv, prev_rank, group),
    ]
    reqs = dist.batch_isend_irecv(ops)
    return reqs, k_recv, v_recv
```

**Uygulama sınırı:** Görevler Python ile küçük, denetlenebilir hesaplar yapar. `python norun` blokları PyTorch/GPU tarafını incelemek içindir; bu tezgâhta otomatik çalıştırılıp gerçek training/serving kabulü yapılmaz.

**Birincil kaynak:** [YaRN makalesi](https://arxiv.org/abs/2309.00071). Kaynak, yöntemin ayrıntıları içindir; dersteki küçük örnek ölçülmüş üretim benchmarkı değildir.
:::

::: tahmin NTK-Aware Taban Ölçekleme ve YaRN Dikkat Sıcaklığı (mscale)
Bir modelin bağlam uzunluğu $s = 16$ kat (`4K -> 64K`) uzatılıyor. `YaRN` makalesindeki dikkat sıcaklık ölçeği formülü $\text{mscale} = 0.1 \cdot \ln(s) + 1.0$ olarak tanımlıdır. Ayrıca $N = 8$ GPU'lu bir `Ring Attention` kümesinde $1,000,000$ tokenlık dizi eşit bölündüğünde GPU başına düşen yerel sekans uzunluğu ve tam dikkat için gereken halka adım sayısı nedir?

```python
import math
s = 16.0
mscale = round(0.1 * math.log(s) + 1.0, 4)
gpu_sayisi = 8
yerel_token = 1_000_000 // gpu_sayisi
print(f"YaRN_mscale={mscale} | YerelToken={yerel_token} | HalkaAdimi={gpu_sayisi}")
```

???

```cikti
YaRN_mscale=1.2773 | YerelToken=125000 | HalkaAdimi=8
```
Bağlam $s = 16$ kat uzatıldığında Softmax keskinliğini koruyan `YaRN_mscale` çarpanı $0.1 \ln(16) + 1 \approx 1.2773$ olur. 1 milyon token 8 GPU'ya bölündüğünde her GPU yalnızca `125,000` token tutar ve tüm KV bloklarının halkayı dolaşması için tam `8` halka adımı (`HalkaAdimi=8`) gerekir.
:::

::: gorev 1 · YaRN Dalga Boyu Rampa Fonksiyonu ve Frekans Ölçekleme
`yarn_frekans_olcekle(tur_sayilari, orijinal_frekanslar, olcek_s, alpha=1.0, beta=32.0)` işlevini yaz.

Parametreler:
- `tur_sayilari`: Her RoPE boyut çiftinin orijinal eğitim bağlamındaki tur sayısı listesi $r_i = L_{\text{orig}} / \lambda_i$ (`list[float]`).
- `orijinal_frekanslar`: Her boyutun orijinal frekansı $\theta_i$ (`list[float]`).
- `olcek_s`: Bağlam uzatma katsayısı $s > 1$ (`float`, ör. `8.0` veya `16.0`).
- `alpha`, `beta`: YaRN rampa alt ve üst sınırları (`float`).

Hesaplanacaklar:
1. Her boyut $i$ için rampa katsayısı $\gamma_i \in [0.0, 1.0]$ değerini hesapla:
   - $r_i < \alpha$ ise $\gamma_i = 0.0$ (tam interpolasyon bölgesi),
   - $r_i > \beta$ ise $\gamma_i = 1.0$ (tam ekstrapolasyon / dokunulmayan yüksek frekans bölgesi),
   - $\alpha \le r_i \le \beta$ ise $\gamma_i = \frac{r_i - \alpha}{\beta - \alpha}$.
2. Her boyutun yeni **`YaRN` frekansını** hesapla:
   $$\theta_i^{\text{yarn}} = (1.0 - \gamma_i) \cdot \frac{\theta_i}{\text{olcek\_s}} + \gamma_i \cdot \theta_i$$
3. YaRN dikkat sıcaklık çarpanını hesapla:
   $$\text{mscale} = 0.1 \cdot \ln(\text{olcek\_s}) + 1.0$$
4. Tüm sayıları `round(val, 6)` ile yuvarlayarak şu sözlüğü döndür:
   - `"rampa_gamma"`: `list[float]`
   - `"yarn_frekanslar"`: `list[float]`
   - `"mscale"`: `float`

```starter
def yarn_frekans_olcekle(tur_sayilari, orijinal_frekanslar, olcek_s, alpha=1.0, beta=32.0):
    # KUSURLU BAŞLANGIÇ KODU: YaRN 3-bölgeli rampa ve mscale hesabını yapmıyor!
    n = len(tur_sayilari)
    return {
        "rampa_gamma": [0.0] * n,
        "yarn_frekanslar": list(orijinal_frekanslar),
        "mscale": 1.0,
    }

print("YaRN:", yarn_frekans_olcekle([0.5, 16.5, 64.0], [0.01, 0.1, 1.0], olcek_s=8.0))
```

```test
import copy
import math

def sozlesme(fn):
    try:
        r_list = [0.5, 16.5, 64.0]
        f_list = [0.08, 0.16, 1.0]
        rk, fk = copy.deepcopy(r_list), copy.deepcopy(f_list)
        # alpha=1.0, beta=32.0, s=8.0
        # i=0: r=0.5 < 1.0 -> gamma=0.0 -> f_yarn = 0.08 / 8.0 = 0.01
        # i=1: r=16.5 -> gamma = (16.5 - 1.0)/31.0 = 0.5 -> f_yarn = 0.5*(0.16/8.0) + 0.5*0.16 = 0.01 + 0.08 = 0.09
        # i=2: r=64.0 > 32.0 -> gamma=1.0 -> f_yarn = 1.0 (hiç değişmez!)
        res = fn(r_list, f_list, 8.0, 1.0, 32.0)
        if r_list != rk or f_list != fk or not isinstance(res, dict):
            return False
        if res.get("rampa_gamma") != [0.0, 0.5, 1.0]:
            return False
        if res.get("yarn_frekanslar") != [0.01, 0.09, 1.0]:
            return False
        beklenen_mscale = round(0.1 * math.log(8.0) + 1.0, 6)
        return res.get("mscale") == beklenen_mscale
    except Exception:
        return False

ok(sozlesme(yarn_frekans_olcekle), "YaRN 3-bölgeli rampa fonksiyonu, frekans harmanlaması ve mscale sıcaklığı doğru hesaplanmalı")

def m_duz_pi(tur_sayilari, orijinal_frekanslar, olcek_s, alpha=1.0, beta=32.0):
    # Tüm frekansları s'ye bölen düz Position Interpolation mutantı
    r = yarn_frekans_olcekle(tur_sayilari, orijinal_frekanslar, olcek_s, alpha, beta)
    r["yarn_frekanslar"] = [round(f / olcek_s, 6) for f in orijinal_frekanslar]
    return r

def m_mscale_sabit(tur_sayilari, orijinal_frekanslar, olcek_s, alpha=1.0, beta=32.0):
    r = yarn_frekans_olcekle(tur_sayilari, orijinal_frekanslar, olcek_s, alpha, beta)
    r["mscale"] = 1.0
    return r

for ad, mutant in [("yüksek frekansları da bölen düz PI", m_duz_pi), ("mscale sıcaklığını hesaplamayan", m_mscale_sabit)]:
    ok(not sozlesme(mutant), "hatalı çözüm/mutant yakalanmalı: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef yarn_frekans_olcekle(tur_sayilari, orijinal_frekanslar, olcek_s, alpha=1.0, beta=32.0):\n    rampa = []\n    yarn_frek = []\n    for r, theta in zip(tur_sayilari, orijinal_frekanslar):\n        if r < alpha:\n            g = 0.0\n        elif r > beta:\n            g = 1.0\n        else:\n            g = (r - alpha) / (beta - alpha)\n        rampa.append(round(g, 6))\n        yeni_theta = (1.0 - g) * (theta / olcek_s) + g * theta\n        yarn_frek.append(round(yeni_theta, 6))\n    mscale = round(0.1 * math.log(olcek_s) + 1.0, 6)\n    return {'rampa_gamma': rampa, 'yarn_frekanslar': yarn_frek, 'mscale': mscale}", 'referans', 'exec'), _REF)
_t, _g = _ff(yarn_frekans_olcekle, _REF['yarn_frekans_olcekle'], ([0.5, 16.5, 64.0], [0.01, 0.1, 1.0], 8.0, 1.0, 32.0), tohum=3172, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (yarn_frekans_olcekle): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
ok(yarn_frekans_olcekle([0.7, 10.0, 40.0], [1.0, 0.5, 0.1], 4.0) == _REF['yarn_frekans_olcekle']([0.7, 10.0, 40.0], [1.0, 0.5, 0.1], 4.0), "varsayılan alpha=1.0 ve beta=32.0 korunmalı")
```

```solution
import math

def yarn_frekans_olcekle(tur_sayilari, orijinal_frekanslar, olcek_s, alpha=1.0, beta=32.0):
    rampa = []
    yarn_frek = []

    for r, theta in zip(tur_sayilari, orijinal_frekanslar):
        if r < alpha:
            g = 0.0
        elif r > beta:
            g = 1.0
        else:
            g = (r - alpha) / (beta - alpha)
        rampa.append(round(g, 6))

        yeni_theta = (1.0 - g) * (theta / olcek_s) + g * theta
        yarn_frek.append(round(yeni_theta, 6))

    mscale = round(0.1 * math.log(olcek_s) + 1.0, 6)

    return {
        "rampa_gamma": rampa,
        "yarn_frekanslar": yarn_frek,
        "mscale": mscale,
    }
```

```hint
Her `r` için `g = max(0.0, min(1.0, (r - alpha) / (beta - alpha)))` hesapla. Ardından `(1.0 - g) * (theta / olcek_s) + g * theta` ile frekansı ve `0.1 * math.log(olcek_s) + 1.0` ile `mscale` değerini bul.
```
:::

::: gorev 2 · Dağıtık Ring Attention (KV Blok Halkası + Online Softmax Birleştirme)
`ring_attention_adimlari(q_yerel, kv_halka_listesi)` işlevini yaz.

Bir GPU üzerindeki yerel sorgu vektörü `q_yerel` ($d$ uzunluğunda `list[float]`) sabit dururken, $N$ GPU'luk halkadan sırasıyla `kv_halka_listesi` içindeki $(K^{(p)}, V^{(p)})$ blokları gelmektedir:
- `kv_halka_listesi`: Uzunluğu $N$ (GPU sayısı) olan bir listedir; her öğesi `{"k": k_matrisi, "v": v_matrisi}` sözlüğüdür (`k_matrisi` ve `v_matrisi` boyutu $B_{\text{blok}} \times d$ olan 2B listelerdir).

İşlevin yapması gerekenler:
1. Girdileri değiştirme. $m = -\infty$, $\ell = 0.0$ ve $O = [0.0, \dots, 0.0]$ akümülatörlerini başlat.
2. Halkadan gelen her `adim` ($0 \dots N-1$) bloğu için:
   - Bloğun içindeki her anahtar $k_j$ ile ölçeklenmiş dikkat skorunu $s_j = \frac{q_{\text{yerel}} \cdot k_j}{\sqrt{d}}$ olarak hesapla.
   - **Online Softmax** güncellemesiyle yeni maksimum $m_{\text{yeni}}$, yeniden ölçekleme çarpanı $\alpha = e^{m - m_{\text{yeni}}}$, yeni payda $\ell_{\text{yeni}}$ ve güncellenmiş çıktı vektörü $O$'yu hesapla.
   - Her halka adımı sonunda oluşan kısmi maksimumu `adim_makslari` listesine (`round(m, 6)`) kaydet.
3. $N$ halka adımı tamamlandığında şu sözlüğü döndür:
   - `"halka_adim_sayisi"`: $N$ (`len(kv_halka_listesi)`),
   - `"adim_makslari"`: Her halka adımından sonraki yürüyen maksimum $m$ listesi (`list[float]`),
   - `"son_cikti"`: Halkadaki tüm GPU blokları gezildikten sonraki tam (`exact`) dikkat çıktısı $O$ (`round(val, 6)` ile yuvarlanmış `list[float]`).

```starter
def ring_attention_adimlari(q_yerel, kv_halka_listesi):
    # KUSURLU BAŞLANGIÇ KODU: Halka boyunca KV bloklarını Online Softmax ile birleştirmiyor!
    n = len(kv_halka_listesi)
    d = len(q_yerel)
    return {
        "halka_adim_sayisi": n,
        "adim_makslari": [0.0] * n,
        "son_cikti": [0.0] * d,
    }

q_orn = [2.0, 0.0, 0.0, 0.0]
halka_orn = [
    {"k": [[1.0, 0.0, 0.0, 0.0]], "v": [[10.0, 20.0, 0.0, 0.0]]},
    {"k": [[3.0, 0.0, 0.0, 0.0]], "v": [[30.0, 40.0, 0.0, 0.0]]},
]
print("Ring Attention:", ring_attention_adimlari(q_orn, halka_orn))
```

```test
import copy
import math

def sozlesme(fn):
    try:
        # d = 4 -> sqrt(d) = 2.0
        q = [2.0, 0.0, 0.0, 0.0]
        halka = [
            {"k": [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]], "v": [[10.0, 0.0, 0.0, 0.0], [0.0, 20.0, 0.0, 0.0]]},
            {"k": [[3.0, 0.0, 0.0, 0.0]], "v": [[0.0, 0.0, 30.0, 0.0]]},
        ]
        # Adım 0 skorları: [2*1/2 = 1.0, 0.0] -> m0 = 1.0
        # Adım 1 skorları: [2*3/2 = 3.0] -> m1 = 3.0
        qk, hk = copy.deepcopy(q), copy.deepcopy(halka)
        r = fn(q, halka)
        if q != qk or halka != hk or not isinstance(r, dict):
            return False
        if r.get("halka_adim_sayisi") != 2:
            return False
        if r.get("adim_makslari") != [1.0, 3.0]:
            return False

        # Tam referans Softmax([1.0, 0.0, 3.0]):
        e0, e1, e2 = math.exp(-2.0), math.exp(-3.0), 1.0
        s = e0 + e1 + e2
        b_out = [
            round((e0 / s) * 10.0, 6),
            round((e1 / s) * 20.0, 6),
            round((e2 / s) * 30.0, 6),
            0.0,
        ]
        return r.get("son_cikti") == b_out
    except Exception:
        return False

ok(sozlesme(ring_attention_adimlari), "Ring Attention halka geçişleri ve Online Softmax birleştirmesi tam dikkat sonucuyla örtüşmeli")

def m_sadece_son_gpu(q_yerel, kv_halka_listesi):
    # Önceki GPU'ların katkısını silen hatalı mutant
    r = ring_attention_adimlari(q_yerel, kv_halka_listesi)
    r["son_cikti"][0] = 0.0
    return r

def m_maks_bozuk(q_yerel, kv_halka_listesi):
    r = ring_attention_adimlari(q_yerel, kv_halka_listesi)
    r["adim_makslari"] = [0.0 for _ in r["adim_makslari"]]
    return r

for ad, mutant in [("önceki GPU bloklarını unutan", m_sadece_son_gpu), ("yürüyen maksimumları kaydetmeyen", m_maks_bozuk)]:
    ok(not sozlesme(mutant), "hatalı çözüm/mutant yakalanmalı: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef ring_attention_adimlari(q_yerel, kv_halka_listesi):\n    d = len(q_yerel)\n    olcek = math.sqrt(d)\n    m = float('-inf')\n    l = 0.0\n    O = [0.0] * d\n    adim_makslari = []\n    for paket in kv_halka_listesi:\n        k_blok = paket['k']\n        v_blok = paket['v']\n        s_blok = [sum((q_yerel[i] * k_vec[i] for i in range(d))) / olcek for k_vec in k_blok]\n        m_blok = max(s_blok)\n        m_yeni = max(m, m_blok)\n        alpha = math.exp(m - m_yeni) if m != float('-inf') else 0.0\n        exps = [math.exp(s - m_yeni) for s in s_blok]\n        l_yeni = alpha * l + sum(exps)\n        for i in range(d):\n            katki = sum((exps[t] * v_blok[t][i] for t in range(len(s_blok))))\n            O[i] = (alpha * l * O[i] + katki) / l_yeni\n        m = m_yeni\n        l = l_yeni\n        adim_makslari.append(round(m, 6))\n    return {'halka_adim_sayisi': len(kv_halka_listesi), 'adim_makslari': adim_makslari, 'son_cikti': [round(v, 6) for v in O]}", 'referans', 'exec'), _REF)
_t, _g = _ff(ring_attention_adimlari, _REF['ring_attention_adimlari'], ([2.0, 0.0, 0.0, 0.0], [{'k': [[1.0, 0.0, 0.0, 0.0]], 'v': [[10.0, 20.0, 0.0, 0.0]]}, {'k': [[3.0, 0.0, 0.0, 0.0]], 'v': [[30.0, 40.0, 0.0, 0.0]]}]), tohum=3498, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (ring_attention_adimlari): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
ok(ring_attention_adimlari([0.1234567], [{"k": [[1.0]], "v": [[2.0]]}]) == _REF['ring_attention_adimlari']([0.1234567], [{"k": [[1.0]], "v": [[2.0]]}]), "adim_makslari 6 basamak yuvarlama korunmalı")
```

```solution
import math

def ring_attention_adimlari(q_yerel, kv_halka_listesi):
    d = len(q_yerel)
    olcek = math.sqrt(d)
    m = float("-inf")
    l = 0.0
    O = [0.0] * d
    adim_makslari = []

    for paket in kv_halka_listesi:
        k_blok = paket["k"]
        v_blok = paket["v"]
        s_blok = [
            sum(q_yerel[i] * k_vec[i] for i in range(d)) / olcek
            for k_vec in k_blok
        ]

        m_blok = max(s_blok)
        m_yeni = max(m, m_blok)
        alpha = math.exp(m - m_yeni) if m != float("-inf") else 0.0
        exps = [math.exp(s - m_yeni) for s in s_blok]
        l_yeni = alpha * l + sum(exps)

        for i in range(d):
            katki = sum(exps[t] * v_blok[t][i] for t in range(len(s_blok)))
            O[i] = (alpha * l * O[i] + katki) / l_yeni

        m = m_yeni
        l = l_yeni
        adim_makslari.append(round(m, 6))

    return {
        "halka_adim_sayisi": len(kv_halka_listesi),
        "adim_makslari": adim_makslari,
        "son_cikti": [round(v, 6) for v in O],
    }
```

```hint
Her halka paketinde `s_blok` skorlarını `math.sqrt(d)` ile bölerek hesapla. Ardından Online Softmax (`alpha = math.exp(m - m_yeni)`, `l_yeni = alpha * l + sum(exps)`) ile `O` vektörünü güncelle ve her adım sonunda `round(m, 6)` değerini `adim_makslari` listesine ekle.
```
:::

::: gorev 3 · Position Interpolation ve NTK-Aware RoPE Frekansları
Bağlamı `olcek` katına uzatmanın iki klasik yolu vardır. **Position Interpolation (PI)** tüm pozisyonları `olcek`'e böler, yani bütün frekanslar aynı oranda yavaşlar ve kısa mesafe ayrımı da bozulur. **NTK-aware** ölçekleme ise tabanı büyütür: yüksek frekanslar neredeyse aynı kalır, yalnız düşük frekanslar interpolasyona uğrar. `rope_olcekleme_karsilastir(d, taban, olcek, pozisyon)` işlevini yaz.

**Hesap:** $\theta_i = \text{taban}^{-2i/d}$, $i = 0..d/2-1$.
- PI açısı: $(\text{pozisyon}/\text{olcek}) \cdot \theta_i$.
- NTK tabanı: $\text{taban}' = \text{taban} \cdot \text{olcek}^{d/(d-2)}$; açı: $\text{pozisyon} \cdot \theta'_i$, $\theta'_i = \text{taban}'^{-2i/d}$.
- Oranlar: PI için her frekansta $1/\text{olcek}$; NTK için $\theta'_i / \theta_i$.

Çıktı (sayılar `round(·, 6)`): `"ntk_taban"`, `"pi_acilari"`, `"ntk_acilari"`, `"pi_oranlari"`, `"ntk_oranlari"`.

`d` en az 4 olan çift `int` değilse, `taban <= 1`, `olcek < 1`, `pozisyon < 0` ise ya da değerler sayı değilse (`bool` dahil) `ValueError`.

```starter
def rope_olcekleme_karsilastir(d, taban, olcek, pozisyon):
    # KUSURLU BAŞLANGIÇ: iki yöntemi de PI gibi hesaplıyor
    acilar = [(pozisyon / olcek) * taban ** (-2 * i / d) for i in range(d // 2)]
    return {"ntk_taban": taban, "pi_acilari": acilar, "ntk_acilari": acilar,
            "pi_oranlari": [1 / olcek] * (d // 2), "ntk_oranlari": [1 / olcek] * (d // 2)}

print(rope_olcekleme_karsilastir(4, 10000.0, 4.0, 8))
```

```test
fn = need("rope_olcekleme_karsilastir")
r = fn(4, 10000.0, 4.0, 8)
eq(r["ntk_taban"], 160000.0, "10000 · 4^(4/2)")
eq(r["pi_acilari"], [2.0, 0.02], "θ = [1, 0.01]; 8/4 = 2")
eq(r["ntk_acilari"], [8.0, 0.02], "en yüksek frekans korunur; en düşük frekans PI ile aynı (160000^-0.5 = 0.0025)")
eq(r["pi_oranlari"], [0.25, 0.25], "PI her frekansı 1/4 yavaşlatır")
eq(r["ntk_oranlari"], [1.0, 0.25], "NTK: yüksek frekans 1, düşük frekans 1/olcek")
r2 = fn(8, 10000.0, 2.0, 1)
eq(r2["ntk_oranlari"], [1.0, 0.793701, 0.629961, 0.5], "oran 2^(-i/3)")
eq(r2["pi_acilari"], [0.5, 0.05, 0.005, 0.0005], "θ = [1, 0.1, 0.01, 0.001], pozisyon/2")
eq(fn(4, 500000.0, 1.0, 3)["ntk_oranlari"], [1.0, 1.0], "olcek 1: değişiklik yok")
raises(ValueError, fn, 5, 10000.0, 2.0, 1)
raises(ValueError, fn, 2, 10000.0, 2.0, 1)
raises(ValueError, fn, 4, 1.0, 2.0, 1)
raises(ValueError, fn, 4, 10000.0, 0.5, 1)
raises(ValueError, fn, 4, 10000.0, 2.0, -1)
raises(ValueError, fn, True, 10000.0, 2.0, 1)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef rope_olcekleme_karsilastir(d, taban, olcek, pozisyon):\n    if isinstance(d, bool) or not isinstance(d, int) or d < 4 or d % 2:\n        raise ValueError('d en az 4 olan çift tam sayı olmalı')\n    for v in (taban, olcek, pozisyon):\n        if isinstance(v, bool) or not isinstance(v, (int, float)) or (not math.isfinite(v)):\n            raise ValueError('taban, olcek, pozisyon sonlu sayı olmalı')\n    if taban <= 1 or olcek < 1 or pozisyon < 0:\n        raise ValueError('taban > 1, olcek >= 1, pozisyon >= 0 olmalı')\n    k = d // 2\n    teta = [taban ** (-2 * i / d) for i in range(k)]\n    taban2 = taban * olcek ** (d / (d - 2))\n    teta2 = [taban2 ** (-2 * i / d) for i in range(k)]\n    return {'ntk_taban': round(taban2, 6), 'pi_acilari': [round(pozisyon / olcek * t, 6) for t in teta], 'ntk_acilari': [round(pozisyon * t, 6) for t in teta2], 'pi_oranlari': [round(1 / olcek, 6)] * k, 'ntk_oranlari': [round(b / a, 6) for a, b in zip(teta, teta2)]}", 'referans', 'exec'), _REF)
_t, _g = _ff(rope_olcekleme_karsilastir, _REF['rope_olcekleme_karsilastir'], (4, 10000.0, 4.0, 8), tohum=3825, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (rope_olcekleme_karsilastir): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
ok(rope_olcekleme_karsilastir(6, 10.0, 1.7, 5) == _REF['rope_olcekleme_karsilastir'](6, 10.0, 1.7, 5), "ntk_taban 6 basamak yuvarlama korunmalı")
```

```solution
import math

def rope_olcekleme_karsilastir(d, taban, olcek, pozisyon):
    if isinstance(d, bool) or not isinstance(d, int) or d < 4 or d % 2:
        raise ValueError("d en az 4 olan çift tam sayı olmalı")
    for v in (taban, olcek, pozisyon):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError("taban, olcek, pozisyon sonlu sayı olmalı")
    if taban <= 1 or olcek < 1 or pozisyon < 0:
        raise ValueError("taban > 1, olcek >= 1, pozisyon >= 0 olmalı")
    k = d // 2
    teta = [taban ** (-2 * i / d) for i in range(k)]
    taban2 = taban * olcek ** (d / (d - 2))
    teta2 = [taban2 ** (-2 * i / d) for i in range(k)]
    return {"ntk_taban": round(taban2, 6),
            "pi_acilari": [round((pozisyon / olcek) * t, 6) for t in teta],
            "ntk_acilari": [round(pozisyon * t, 6) for t in teta2],
            "pi_oranlari": [round(1 / olcek, 6)] * k,
            "ntk_oranlari": [round(b / a, 6) for a, b in zip(teta, teta2)]}
```

```hint
NTK oranı kapalı formda `olcek ** (-2 * i / (d - 2))`'dir; i = 0'da 1, i = d/2 − 1'de 1/olcek çıkar.
```
:::

::: anlat Gerçek deney: transformers'ın RoPE ölçeklemeleri ve SmolLM2'yi eğitim uzunluğunun iki katında çalıştırmak
Final senin frekans hesaplarını Hugging Face transformers'ın **gerçek** RoPE ölçekleme kodlarıyla karşılaştırır ve bağlam uzatmayı gerçek bir modelde ölçer (indirme yok; GPU varsa kullanılır):

- **YaRN:** SmolLM2'nin `head_dim` 64 ve `rope_theta` 100 000 değerleriyle, 8 192 tokenlık eğitim uzunluğu ve $s = 2$ için senin `yarn_frekans_olcekle` çıktın `transformers`'ın `yarn` başlatıcısıyla karşılaştırılır. Saf bölgelerde (tam dış değerleme ve tam interpolasyon) aynı olmalıdır. Rampa bölgesinde küçük bir fark beklenir: HF rampayı boyut indeksinde kurar ve sınırları tamsayıya yuvarlar, senin rampan dönüş sayısı $r$ üzerindedir. `mscale` HF'nin `attention_factor` değeriyle aynı olmalıdır.
- **PI ve NTK:** `rope_olcekleme_karsilastir` açıları HF `linear` ve `dynamic` başlatıcılarıyla karşılaştırılır. HF dynamic NTK tabanı dizi uzunluğuna göre büyütür; etkin ölçeğin $s$ olduğu uzunlukta senin statik NTK tabanınla aynıdır.
- **Ring attention:** 3. katmanın gerçek sorgusu ve anahtar/değer blokları dört "cihaza" bölünür; senin `ring_attention_adimlari` çıktın tam dikkatle karşılaştırılır.
- **Uzun bağlam:** Pafta'nın ders metinlerinden 16 384 tokenlık gerçek bir dizi (CPU'da 10 240) modelden dört RoPE kipiyle geçirilir: varsayılan, PI, dinamik NTK, YaRN. Kayıp 8K öncesi ve 8K ötesi için ayrı ölçülür. İnce ayar yapılmaz.

**Güvenlik yönü — uzun bağlam many-shot jailbreak yüzeyidir:** Uzun bağlamın bedeli yalnız bellek değildir. SmolLM2 temel modeline, istenmeyen bir cevabın (sahte bir yönetici parolası, kanarya) kalıbını tekrarlayan 0, 2, 8, 32 ve 128 örnek diyalog verilir; ardından aynı soru sorulur ve kanarya cevabın log-olasılığı ölçülür. Örnek sayısı arttıkça model kalıba kilitlenir: birkaç örnekten sonra cevap neredeyse kesinleşir. Bağlam ne kadar uzunsa saldırgan o kadar çok örnek sığdırabilir (Anil vd. 2024, many-shot jailbreaking).

Kabul: üç işlevin farksal taramayı geçmesi; YaRN'ın saf bölgelerde HF ile en çok `1e-6` farklı ve `mscale`'in aynı olması; PI ve NTK açılarının HF ile aynı olması; ring attention'ın tam dikkatle aynı olması; NTK ya da YaRN'ın 8K ötesinde varsayılan RoPE'tan düşük kayıp vermesi. Ayrıca kanarya cevabın log-olasılığı birkaç örnekle 10 nattan fazla artmalı, çok örnekle −1'in üstüne çıkmalı ve ilk tokenın olasılığı 0.5'i geçmelidir.

**Kanıt dosyasını oku:** `yarn_uc_bolge_fark`, `yarn_ara_bolge_fark`, `ntk_taban`, `dynamic_seq_len`, `kipler`. Soru 1: PI neden 8K ötesinde neredeyse hiç yardım etmiyor da NTK ve YaRN ediyor? Soru 2: 8K içi kayıp hangi kipte en çok bozuldu ve neden? Soru 3: Uzun bağlam neden many-shot jailbreak yüzeyini büyütür?
:::

::: gorev Gerçek deney · HF RoPE ölçeklemeleriyle karşılaştırma, ring attention ve SmolLM2'de 16K bağlam
Önceki görevlerdeki `yarn_frekans_olcekle`, `ring_attention_adimlari`, `rope_olcekleme_karsilastir` işlevlerini buraya birleştir (çözümlerini kopyalayabilirsin). Çalıştır gerçek ölçüm tablosunu gösterir; Kontrol Et önce işlevlerini gizli verilerle ve farksal taramayla sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
ortam: gpu
timeout: 300
```
```starter
import ai_lab
def yarn_frekans_olcekle(tur_sayilari, orijinal_frekanslar, olcek_s, alpha=1.0, beta=32.0):
    n = len(tur_sayilari)
    return {'rampa_gamma': [0.0] * n, 'yarn_frekanslar': list(orijinal_frekanslar), 'mscale': 1.0}

def ring_attention_adimlari(q_yerel, kv_halka_listesi):
    n = len(kv_halka_listesi)
    d = len(q_yerel)
    return {'halka_adim_sayisi': n, 'adim_makslari': [0.0] * n, 'son_cikti': [0.0] * d}

def rope_olcekleme_karsilastir(d, taban, olcek, pozisyon):
    acilar = [pozisyon / olcek * taban ** (-2 * i / d) for i in range(d // 2)]
    return {'ntk_taban': taban, 'pi_acilari': acilar, 'ntk_acilari': acilar, 'pi_oranlari': [1 / olcek] * (d // 2), 'ntk_oranlari': [1 / olcek] * (d // 2)}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_18 as D
    D.goster(yarn_frekans_olcekle, ring_attention_adimlari, rope_olcekleme_karsilastir)
```
```test
import ai_lab
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('_cfg', 'uzun_metin', 'kanit_yaz'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
yarn_frekans_olcekle = need("yarn_frekans_olcekle")
ring_attention_adimlari = need("ring_attention_adimlari")
rope_olcekleme_karsilastir = need("rope_olcekleme_karsilastir")
# farksal tarama (görev çözümlerinden derlenen referans)
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef yarn_frekans_olcekle(tur_sayilari, orijinal_frekanslar, olcek_s, alpha=1.0, beta=32.0):\n    rampa = []\n    yarn_frek = []\n    for r, theta in zip(tur_sayilari, orijinal_frekanslar):\n        if r < alpha:\n            g = 0.0\n        elif r > beta:\n            g = 1.0\n        else:\n            g = (r - alpha) / (beta - alpha)\n        rampa.append(round(g, 6))\n        yeni_theta = (1.0 - g) * (theta / olcek_s) + g * theta\n        yarn_frek.append(round(yeni_theta, 6))\n    mscale = round(0.1 * math.log(olcek_s) + 1.0, 6)\n    return {'rampa_gamma': rampa, 'yarn_frekanslar': yarn_frek, 'mscale': mscale}\n\nimport math\n\ndef ring_attention_adimlari(q_yerel, kv_halka_listesi):\n    d = len(q_yerel)\n    olcek = math.sqrt(d)\n    m = float('-inf')\n    l = 0.0\n    O = [0.0] * d\n    adim_makslari = []\n    for paket in kv_halka_listesi:\n        k_blok = paket['k']\n        v_blok = paket['v']\n        s_blok = [sum((q_yerel[i] * k_vec[i] for i in range(d))) / olcek for k_vec in k_blok]\n        m_blok = max(s_blok)\n        m_yeni = max(m, m_blok)\n        alpha = math.exp(m - m_yeni) if m != float('-inf') else 0.0\n        exps = [math.exp(s - m_yeni) for s in s_blok]\n        l_yeni = alpha * l + sum(exps)\n        for i in range(d):\n            katki = sum((exps[t] * v_blok[t][i] for t in range(len(s_blok))))\n            O[i] = (alpha * l * O[i] + katki) / l_yeni\n        m = m_yeni\n        l = l_yeni\n        adim_makslari.append(round(m, 6))\n    return {'halka_adim_sayisi': len(kv_halka_listesi), 'adim_makslari': adim_makslari, 'son_cikti': [round(v, 6) for v in O]}\n\nimport math\n\ndef rope_olcekleme_karsilastir(d, taban, olcek, pozisyon):\n    if isinstance(d, bool) or not isinstance(d, int) or d < 4 or d % 2:\n        raise ValueError('d en az 4 olan çift tam sayı olmalı')\n    for v in (taban, olcek, pozisyon):\n        if isinstance(v, bool) or not isinstance(v, (int, float)) or (not math.isfinite(v)):\n            raise ValueError('taban, olcek, pozisyon sonlu sayı olmalı')\n    if taban <= 1 or olcek < 1 or pozisyon < 0:\n        raise ValueError('taban > 1, olcek >= 1, pozisyon >= 0 olmalı')\n    k = d // 2\n    teta = [taban ** (-2 * i / d) for i in range(k)]\n    taban2 = taban * olcek ** (d / (d - 2))\n    teta2 = [taban2 ** (-2 * i / d) for i in range(k)]\n    return {'ntk_taban': round(taban2, 6), 'pi_acilari': [round(pozisyon / olcek * t, 6) for t in teta], 'ntk_acilari': [round(pozisyon * t, 6) for t in teta2], 'pi_oranlari': [round(1 / olcek, 6)] * k, 'ntk_oranlari': [round(b / a, 6) for a, b in zip(teta, teta2)]}", 'referans', 'exec'), _REF)
_t, _g = _ff(yarn_frekans_olcekle, _REF['yarn_frekans_olcekle'], ([0.5, 16.5, 64.0], [0.01, 0.1, 1.0], 8.0, 1.0, 32.0), tohum=3172, en_cok=600, mod='gecerli', butce='oto')
kontrol(_t, "farksal tarama (yarn_frekans_olcekle): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(ring_attention_adimlari, _REF['ring_attention_adimlari'], ([2.0, 0.0, 0.0, 0.0], [{'k': [[1.0, 0.0, 0.0, 0.0]], 'v': [[10.0, 20.0, 0.0, 0.0]]}, {'k': [[3.0, 0.0, 0.0, 0.0]], 'v': [[30.0, 40.0, 0.0, 0.0]]}]), tohum=3498, en_cok=600, mod='gecerli', butce='oto')
kontrol(_t, "farksal tarama (ring_attention_adimlari): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(rope_olcekleme_karsilastir, _REF['rope_olcekleme_karsilastir'], (4, 10000.0, 4.0, 8), tohum=3825, en_cok=600, mod='tam', butce='oto')
kontrol(_t, "farksal tarama (rope_olcekleme_karsilastir): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
kontrol(yarn_frekans_olcekle([0.7, 10.0, 40.0], [1.0, 0.5, 0.1], 4.0) == _REF['yarn_frekans_olcekle']([0.7, 10.0, 40.0], [1.0, 0.5, 0.1], 4.0), "varsayılan alpha=1.0 ve beta=32.0 korunmalı")
kontrol(ring_attention_adimlari([0.1234567], [{"k": [[1.0]], "v": [[2.0]]}]) == _REF['ring_attention_adimlari']([0.1234567], [{"k": [[1.0]], "v": [[2.0]]}]), "adim_makslari 6 basamak yuvarlama korunmalı")
kontrol(rope_olcekleme_karsilastir(6, 10.0, 1.7, 5) == _REF['rope_olcekleme_karsilastir'](6, 10.0, 1.7, 5), "ntk_taban 6 basamak yuvarlama korunmalı")
if not all(checks): stop()
from sandbox import ai_gercek_ai_uretim_18 as D
try: r = D.deney(yarn_frekans_olcekle, ring_attention_adimlari, rope_olcekleme_karsilastir)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r['yarn_ayni'], 'YaRN frekansları saf bölgelerde HF yarn ile aynı, mscale HF attention_factor ile aynı')
kontrol(r['pi_ntk_ayni'], 'PI ve NTK açıları HF linear ve dynamic RoPE ile aynı')
kontrol(r['ring_ayni'], 'ring attention gerçek bloklarda tam dikkatle aynı')
kontrol(r['olceklenmis_daha_iyi'], "NTK ya da YaRN eğitim uzunluğunun ötesinde varsayılan RoPE'tan düşük kayıp veriyor")
kontrol(r['many_shot_artiyor'], 'örnek diyalog sayısı arttıkça kanarya cevabın log-olasılığı keskin biçimde arttı')
ai_lab.kanit_yaz("ai-uretim-18-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-uretim-18", "deney": r})
```
```solution
import ai_lab
import math

def yarn_frekans_olcekle(tur_sayilari, orijinal_frekanslar, olcek_s, alpha=1.0, beta=32.0):
    rampa = []
    yarn_frek = []
    for r, theta in zip(tur_sayilari, orijinal_frekanslar):
        if r < alpha:
            g = 0.0
        elif r > beta:
            g = 1.0
        else:
            g = (r - alpha) / (beta - alpha)
        rampa.append(round(g, 6))
        yeni_theta = (1.0 - g) * (theta / olcek_s) + g * theta
        yarn_frek.append(round(yeni_theta, 6))
    mscale = round(0.1 * math.log(olcek_s) + 1.0, 6)
    return {'rampa_gamma': rampa, 'yarn_frekanslar': yarn_frek, 'mscale': mscale}

import math

def ring_attention_adimlari(q_yerel, kv_halka_listesi):
    d = len(q_yerel)
    olcek = math.sqrt(d)
    m = float('-inf')
    l = 0.0
    O = [0.0] * d
    adim_makslari = []
    for paket in kv_halka_listesi:
        k_blok = paket['k']
        v_blok = paket['v']
        s_blok = [sum((q_yerel[i] * k_vec[i] for i in range(d))) / olcek for k_vec in k_blok]
        m_blok = max(s_blok)
        m_yeni = max(m, m_blok)
        alpha = math.exp(m - m_yeni) if m != float('-inf') else 0.0
        exps = [math.exp(s - m_yeni) for s in s_blok]
        l_yeni = alpha * l + sum(exps)
        for i in range(d):
            katki = sum((exps[t] * v_blok[t][i] for t in range(len(s_blok))))
            O[i] = (alpha * l * O[i] + katki) / l_yeni
        m = m_yeni
        l = l_yeni
        adim_makslari.append(round(m, 6))
    return {'halka_adim_sayisi': len(kv_halka_listesi), 'adim_makslari': adim_makslari, 'son_cikti': [round(v, 6) for v in O]}

import math

def rope_olcekleme_karsilastir(d, taban, olcek, pozisyon):
    if isinstance(d, bool) or not isinstance(d, int) or d < 4 or d % 2:
        raise ValueError('d en az 4 olan çift tam sayı olmalı')
    for v in (taban, olcek, pozisyon):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or (not math.isfinite(v)):
            raise ValueError('taban, olcek, pozisyon sonlu sayı olmalı')
    if taban <= 1 or olcek < 1 or pozisyon < 0:
        raise ValueError('taban > 1, olcek >= 1, pozisyon >= 0 olmalı')
    k = d // 2
    teta = [taban ** (-2 * i / d) for i in range(k)]
    taban2 = taban * olcek ** (d / (d - 2))
    teta2 = [taban2 ** (-2 * i / d) for i in range(k)]
    return {'ntk_taban': round(taban2, 6), 'pi_acilari': [round(pozisyon / olcek * t, 6) for t in teta], 'ntk_acilari': [round(pozisyon * t, 6) for t in teta2], 'pi_oranlari': [round(1 / olcek, 6)] * k, 'ntk_oranlari': [round(b / a, 6) for a, b in zip(teta, teta2)]}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_18 as D
    D.goster(yarn_frekans_olcekle, ring_attention_adimlari, rope_olcekleme_karsilastir)
```
```hint
Üç görevin çözümlerini olduğu gibi buraya koy.
```
:::

::: anlat Sınır
Görevler YaRN rampa fonksiyonunu ve frekans ölçeklemesini, ring attention'da KV bloklarının online softmax ile birleştirilmesini saf Python ile hesaplatır; final adım SmolLM2'nin bağlamını ince ayarsız uzatıp gerçek metinde kaybı ölçer. PI ve NTK-aware görevi frekansları karşılaştırır; final adım bunları HF'nin gerçeklemeleriyle sınar. Bağlam uzatma çoğunlukla az miktarda uzun bağlamlı ince ayar ister; yalnız frekans ölçeklemek uzun mesafedeki bilginin kullanılacağını garanti etmez ve 'needle' testini geçmek gerçek uzun bağlam muhakemesi demek değildir. Ring attention iletişimi hesapla örtüştürebildiği sürece verimlidir. Uzun bağlam many-shot jailbreak gibi saldırıların yüzeyini de büyütür.

Kaynaklar: [Chen vd. 2023 - Extending Context Window of Large Language Models via Positional Interpolation](https://arxiv.org/abs/2306.15595), [Peng vd. 2023 - YaRN: Efficient Context Window Extension of Large Language Models](https://arxiv.org/abs/2309.00071), [Liu vd. 2023 - Ring Attention with Blockwise Transformers for Near-Infinite Context](https://arxiv.org/abs/2310.01889).
:::

::: dusun
Standart **`Ring Attention`** ile nedensel maskeli (**Causal Mask** — her token yalnız kendisinden önceki tokenlara bakabilir) bir LLM eğitirken çok ilginç bir **Yük Dengesizliği (`Load Imbalance`)** sorunu ortaya çıkar:
- Dizinin ilk parçasını (Token `0..125K`) tutan `GPU 0`, yalnız kendi bloğuna dikkat hesaplar; `GPU 1..7`'den gelen gelecekteki blokların tamamı nedensel maske (`Causal Mask`) yüzünden sıfırdır (`GPU 0` zamanın `%87`'sinde boşta yatar!).
- Dizinin son parçasını (Token `875K..1M`) tutan `GPU 7` ise tüm GPU'lardan gelen blokların tamamını hesaplamak zorunda kalır!

Bu darboğazı çözmek için geliştirilen **`Striped Attention` / `ZigZag Ring Attention`** tekniği, tokenları GPU'lara ardışık bloklar (`[0, 1, 2, 3]`, `[4, 5, 6, 7]`) halinde dağıtmak yerine nasıl bir simetrik indeksleme (`GPU 0`'a hem en baştan hem en sondan token vererek!) kullanır? Açıkla.
:::

::: ozet
- Kısa bağlamda eğitilmiş bir modeli uzun bağlama taşırken düz **Position Interpolation (`PI`)** tüm RoPE saat ibrelerini eşit yavaşlatarak yerel kelime sırası çözünürlüğünü bozar.
- **`NTK-Aware Scaling`** ve **`YaRN`**, RoPE boyutlarını dalga boylarına göre 3 bölgeye ayırır: yüksek frekanslı yerel boyutlara hiç dokunmaz ($\gamma = 1$), düşük frekanslı boyutları interpole eder ($\gamma = 0$), orta bölgeyi doğrusal rampayla birleştirir ve dikkat entropisini **$\text{mscale} = 0.1\ln(s)+1$** sıcaklığıyla dengeler.
- **`Ring Attention`**, milyon tokenlık dizileri $N$ GPU'ya bölerek sorguları sabit tutar; $(K, V)$ bloklarını halka topolojisinde asenkron döndürürken **Online Softmax** ile birleştirerek tek GPU bellek sınırını ortadan kaldırır.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Düz konum sıkıştırmanın tuzağı (30 sn).** "4K bağlamda eğitilmiş bir `RoPE` modelinde tüm konumları doğrusal olarak $t/s$ ile bölmek (`Position Interpolation`) yüksek frekanslı yerel token farklarını ezerek yakın kelime çözünürlüğünü bulanıklaştırır."
2. **NTK-Aware ve `YaRN` dalga boyu ayrımı (35 sn).** "`YaRN`, kısa dalga boylu yüksek frekans boyutlarını hiç sıkıştırmadan korur (yerel dilbilgisi bozulmaz), uzun dalga boylu düşük frekans boyutlarını enterpole eder ve uzayan entropiyi dikkat sıcaklığı düzeltmesiyle dengeler."
3. **`Ring Attention` ile bellek sınırını aşmak (30 sn).** "Tek GPU'ya sığmayan milyon tokenlık diziler cihaz halkasına bölünür; her cihaz kendi sorgu dilimi üzerinde çevrimiçi `Softmax` istatistiklerini güncellerken $K, V$ bloklarını komşu GPU'ya elden ele aktarır."
4. **Soru (25 sn).** "Bir modelin bağlam penceresini `YaRN` ile 128K'ya uzatmak, modelin ortadaki kritik bir güvenlik kuralını (`Lost-in-the-Middle`) gerçekten izleyeceğini garanti eder mi?"
:::
