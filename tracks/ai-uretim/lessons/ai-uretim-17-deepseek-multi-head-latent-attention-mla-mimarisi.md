---
id: ai-uretim-17
title: "Multi-Head Latent Attention (MLA), Low-Rank KV Sıkıştırma ve Decoupled RoPE"
summary: "Uzun bağlam çıkarımında KV önbelleğini düşük dereceli ortak gizli vektöre sıkıştıran Multi-Head Latent Attention (MLA), matris yutma (Matrix Absorption) hilesi ve ayrıştırılmış RoPE (Decoupled RoPE) tasarımı."
esleme: ai-uretim-12, ai-uretim-18, ai-temel-08
track: ai-uretim
order: 17
duration_minutes: 45
difficulty: ileri
xp: 330
prerequisites: [ai-uretim-16]
tags: [deepseek, multi-head-latent-attention, mla, low-rank-kv-compression, matrix-absorption, decoupled-rope]
---

::: anlat
## MLA ve latent KV temsili

MLA, Key/Value bilgisini daha küçük bir latent temsille saklayarak cache maliyetini değiştiren bir attention tasarımıdır. Bu derste low-rank projeksiyon, matrix absorption ve ayrı RoPE bileşeninin boyutlarını hesaplayacaksın. Tasarruf oranı seçilen boyutlara bağlıdır; her model için sabit değildir.

2024 yılında **DeepSeek** mühendisleri (*DeepSeek-V2 & V3 Technical Report*) bütün yapay zeka dünyasını sarsan şu soruyu sordu:
> *"Neden KV-Cache'i küçültmek için başları (`Heads`) kaba kuvvetle silip birbirine kopyalıyoruz? Ya her bir dikkat başının kendi benzersiz `Key` ve `Value` matrisine sahip olmasına izin versek, **fakat KV-Cache belleğinde tüm başları ayrı ayrı saklamak yerine hepsini üreten ortak, çok küçük bir Gizli Vektörü (`Low-Rank Latent Vector` $c_t^{KV}$) saklasak?**"*

İşte bu dâhiyane mimariye **`Multi-Head Latent Attention (MLA)`** denir! `MLA` sayesinde DeepSeek-V3/R1, standart `MHA`'dan bile **daha yüksek doğruluk (düşük Perplexity)** elde ederken, **KV-Cache belleğini `%93.3` oranında küçültür!**

---

### 1. `MLA` Mimarisi: `Low-Rank Joint KV Compression` (Ortak Düşük-Ranklı Sıkıştırma)

Klasik `MHA`'da gizli durum $h_t \in \mathbb{R}^{d}$ (örneğin $d = 5120$, $n_h = 128$ baş, $d_h = 128$), doğrudan dev $K_t, V_t \in \mathbb{R}^{n_h d_h}$ ($16,384$ eleman!) vektörlerine izdüşürülür ve KV-Cache'te token başına **$2 \times 16,384 = 32,768$** sayı saklanır.

**`MLA`** ise bunu iki aşamalı bir darboğazdan (**Low-Rank Bottleneck**) geçirir:
1. **Down-Projection (Sıkıştırma — KV-Cache'e Yazılan Tek Şey!):**
   Gizli durum $h_t$, çok küçük boyutlu ($d_c = 512 \ll n_h d_h$) ortak bir **Latent KV Vektörüne ($c_t^{KV}$)** sıkıştırılır:
   $$c_t^{KV} = h_t W^{DKV} \in \mathbb{R}^{d_c}$$
   **Kritik Nokta:** Çıkarım (`Inference`) sırasında KV-Cache belleğine dev $K_t$ ve $V_t$ **YAZILMAZ!** Yalnızca bu minik $c_t^{KV}$ vektörü (512 sayı!) yazılır!
2. **Up-Projection (Geri Açma):**
   $c_t^{KV}$ vektöründen tüm başların kendine özel $K_t^C$ ve $V_t^C$ içerik vektörleri yukarı projeksiyon matrisleriyle ($W^{UK}, W^{UV}$) üretilir:
   $$k_t^C = c_t^{KV} W^{UK}, \qquad v_t^C = c_t^{KV} W^{UV}$$

```
  KLASİK MHA (KV-Cache: 2 * n_h * d_h = 32,768 eleman / token)
  h_t ──┬──► K_t (16,384) ──► [ KV-CACHE ]
        └──► V_t (16,384) ──► [ KV-CACHE ]

  DEEPSEEK MLA (KV-Cache: d_c + d_R = 512 + 64 = Yalnızca 576 eleman / token! -> %93+ Tasarruf!)
  h_t ──┬──► W^DKV ──► c_t^KV (512) ──► [ SIKIŞTIRILMIŞ LATENT KV-CACHE ] ──┬──► W^UK (W^Q içine emilir!)
        └──► RoPE(W^KR) ──► k_t^R (64) ──► [ DECOUPLED ROPE CACHE ]          └──► W^UV (W^O içine emilir!)
```

---

### 2. `Matrix Absorption Trick` (Matris Yutma Hilesi): $c_t^{KV}$'yi Hiç Açmadan Dikkat Hesaplamak!

Burada hemen aklına şu soru gelmeli: *"Hocam, KV-Cache'te küçük $c_t^{KV}$'yi sakladık ama her yeni token üretirken geçmişteki 100.000 tokenın $c_t^{KV}$ vektörünü tekrar $W^{UK}$ ile çarpıp dev $K_t$ matrisine açarsak hesaplama çok yavaşlamaz mı?"*

İşte `MLA`'nın ikinci büyüsü: **Doğrusal Cebirde Birleşme Özelliği (`Associativity of Matrix Multiplication` — Matrix Absorption)!**
$i$. dikkat başında sorgu $q_{t,i} = h_t W_i^Q$ ile sıkıştırılmış anahtar $k_{j,i}^C = c_j^{KV} W_i^{UK}$ arasındaki iç çarpıma bak:

$$q_{t,i} \cdot (k_{j,i}^C)^T = \left(h_t W_i^Q\right) \left(c_j^{KV} W_i^{UK}\right)^T = h_t \underbrace{\left(W_i^Q (W_i^{UK})^T\right)}_{W_i^{Q\text{-absorbed}}} (c_j^{KV})^T$$

- **Mucizeye Bak:** $W_i^{UK}$ matrisi doğrusal bir matristir (arada doğrusal olmayan aktivasyon yoktur!). Bu yüzden çıkarım sırasında $W_i^{UK}$ matrisini **sorgu projeksiyonunun içine yutarız (`Absorb` $W_i^{UK}$ into $W_i^Q$)**!
- Aynı şekilde $W_i^{UV}$ matrisini de çıktı projeksiyonunun ($W^O$) içine yutarız! Böylece geçmiş tokenların $c_j^{KV}$ vektörlerini **HİÇBİR ZAMAN** dev $K$ ve $V$ matrislerine geri açmayız; doğrudan sıkıştırılmış uzayda dikkat hesaplarız!

---

### 3. Neden `Decoupled RoPE` Gerekir? (Konum ve İçeriği Ayırmak)

Peki önünde tek bir engel kalır: 3. derste öğrendiğimiz **`RoPE (Rotary Position Embedding)`**!
Eğer $K_t$ üzerine `RoPE` rotasyon matrisi $R(j)$ uygularsan, $W_i^Q \, R(t - j) \, (W_i^{UK})^T$ ifadesinin ortasına pozisyona bağlı ($t - j$) değişen bir matris girdiği için **$W_i^Q$ ile $(W_i^{UK})^T$'yi önceden çarpıp birleştiremezsin!**

DeepSeek bu engeli **`Decoupled RoPE` (Ayrıştırılmış RoPE)** ile çözdü:
- Anahtarların büyük kısmını ($k_t^C$: **Content** — `RoPE` uygulanmayan içerik kolu) $c_t^{KV}$ içinde sıkıştırır ve `Matrix Absorption` yapar.
- Pozisyon bilgisini taşımak için ise tüm başların paylaştığı **çok küçük tek bir `RoPE` anahtarı ($k_t^R \in \mathbb{R}^{d_R}$, örneğin $d_R = 64$)** üretir!
- Toplam dikkat skoru, **İçerik Skoru (`Content Score`) + Konum Skoru (`RoPE Score`)** toplamıdır:

$$s_{t,j} = \frac{q_t^{\text{emilmiş}} \cdot (c_j^{KV})^T + q_t^R \cdot (k_j^R)^T}{\sqrt{d_h + d_R}}$$

Şimdi saf Python ile `MLA` içindeki **Matrix Absorption** özdeşliğinin açık (`Unabsorbed`) hesaplamayla virgülden sonraki son basamağa kadar aynı sonucu verdiğini kanıtlayalım:

```python
# MLA Matrix Absorption Kanıtı: (q @ W_uk^T) @ c_kv^T == q @ (c_kv @ W_uk)^T
q = [1.5, -0.5, 2.0]                    # d_head = 3
c_kv = [2.0, 3.0]                       # d_c = 2 (Sıkıştırılmış Latent KV)
W_uk = [[0.5, -1.0, 2.0], [1.5, 0.5, -0.5]]  # d_c x d_head (2 x 3)

# Yöntem 1 (Klasik Açarak): Önce k = c_kv @ W_uk üret, sonra q . k iç çarpımı al
k_acik = [sum(c_kv[r] * W_uk[r][d] for r in range(2)) for d in range(3)]
skor_acik = round(sum(q[d] * k_acik[d] for d in range(3)), 6)

# Yöntem 2 (Matrix Absorption): c_kv'yi hiç açmadan q_emilmis = q @ W_uk^T ile doğrudan c_kv'yi çarp!
q_emilmis = [sum(q[d] * W_uk[r][d] for d in range(3)) for r in range(2)]  # Boyut: d_c = 2!
skor_emilmis = round(sum(q_emilmis[r] * c_kv[r] for r in range(2)), 6)

print(f"Açık Skor: {skor_acik} | Absorbed Skor: {skor_emilmis} | Eşit Mi: {skor_acik == skor_emilmis}")
```

---

### 4. Gerçek Üretim Kodu: DeepSeek-V3 Tarzı `MultiHeadLatentAttention` (`nn.Module`)

```python norun
import torch
import torch.nn as nn
import torch.nn.functional as F

class DeepSeekMLA(nn.Module):
    def __init__(self, d_model: int = 5120, n_heads: int = 128, d_head: int = 128, d_c: int = 512, d_rope: int = 64):
        super().__init__()
        self.n_heads = n_heads
        self.d_head = d_head
        self.d_c = d_c
        self.d_rope = d_rope
        self.scale = (d_head + d_rope) ** -0.5

        # Ortak KV Down-Projection (c_t^KV) ve Decoupled RoPE Key (k_t^R)
        self.kv_down_proj = nn.Linear(d_model, d_c, bias=False)
        self.kv_RMSNorm   = nn.RMSNorm(d_c)
        self.k_rope_proj  = nn.Linear(d_model, d_rope, bias=False)

        # Up-Projections (Çıkarımda W_q ve W_o içine emilir!)
        self.k_up_proj = nn.Linear(d_c, n_heads * d_head, bias=False)
        self.v_up_proj = nn.Linear(d_c, n_heads * d_head, bias=False)

        # Query Content + RoPE Projections
        self.q_content_proj = nn.Linear(d_model, n_heads * d_head, bias=False)
        self.q_rope_proj    = nn.Linear(d_model, n_heads * d_rope, bias=False)
        self.out_proj       = nn.Linear(n_heads * d_head, d_model, bias=False)

    def forward_cached(self, h_t: torch.Tensor, kv_cache_c: torch.Tensor, kv_cache_k_rope: torch.Tensor):
        # KV-Cache'te yalnızca c_t^KV [B, S, d_c] ve k_t^R [B, S, d_rope] tutulur!
        c_t = self.kv_RMSNorm(self.kv_down_proj(h_t))
        k_r = self.k_rope_proj(h_t)  # Üzerine RoPE uygulanır
        return c_t, k_r
```

**Uygulama sınırı:** Görevler Python ile küçük, denetlenebilir hesaplar yapar. `python norun` blokları PyTorch/GPU tarafını incelemek içindir; bu tezgâhta otomatik çalıştırılıp gerçek training/serving kabulü yapılmaz.

**Birincil kaynak:** [DeepSeek-V2 teknik raporu](https://arxiv.org/abs/2405.04434). Kaynak, yöntemin ayrıntıları içindir; dersteki küçük örnek ölçülmüş üretim benchmarkı değildir.
:::

::: tahmin Klasik MHA vs GQA vs DeepSeek MLA KV-Cache Boyutu Karşılaştırması
Bir modelde $n_h = 128$ dikkat başı ve baş boyutu $d_h = 128$ bulunuyor:
- **Klasik MHA:** Token başına $2 \times n_h \times d_h = 2 \times 128 \times 128 = 32,768$ eleman saklar.
- **DeepSeek MLA:** Token başına yalnızca ortak gizli vektör $d_c = 512$ ve paylaşımlı RoPE anahtarı $d_R = 64$ olmak üzere toplam $d_c + d_R = 576$ eleman saklar!
Aşağıdaki kod `MLA`'nın klasik `MHA`'ya göre KV-Cache'i yüzde kaç küçülttüğünü hesaplar. Çıktı nedir?

```python
mha_eleman = 2 * 128 * 128
mla_eleman = 512 + 64
kuculme_yuzdesi = round((1.0 - mla_eleman / mha_eleman) * 100, 1)
kat_orani = round(mha_eleman / mla_eleman, 1)
print(f"MHA={mha_eleman} | MLA={mla_eleman} | Tasarruf=%{kuculme_yuzdesi} ({kat_orani}x)")
```

???

```cikti
MHA=32768 | MLA=576 | Tasarruf=%98.2 (56.9x)
```
Klasik `MHA` her token için `32,768` kayan noktalı sayı saklarken, `DeepSeek MLA` yalnızca `512 + 64 = 576` sayı saklar. Böylece KV-Cache belleği `%98.2` oranında (`56.9x` kat!) küçülür.
:::

::: gorev 1 · MLA Low-Rank Ortak KV Sıkıştırma ve Matrix Absorption Eşdeğerliği
`mla_kv_sikistir_ve_ac(h, q, W_dkv, W_uk, W_uv)` işlevini yaz.

Bir tokenın gizli durumu `h` ($d_{\text{model}}$ uzunluğunda), sorgu vektörü `q` ($d_{\text{head}}$ uzunluğunda) ve `MLA` projeksiyon matrisleri verilmektedir:
- `W_dkv`: Down-projection matrisi ($d_{\text{model}} \times d_c$ boyutunda 2B liste).
- `W_uk`: Key Up-projection matrisi ($d_c \times d_{\text{head}}$ boyutunda 2B liste).
- `W_uv`: Value Up-projection matrisi ($d_c \times d_{\text{head}}$ boyutunda 2B liste).

İşlevin yapması gerekenler:
1. Girdi listelerini değiştirme. Ortak sıkıştırılmış gizli vektörü hesapla:
   $$c_{kv} = h \cdot W_{\text{dkv}} \quad (\text{uzunluk: } d_c)$$
2. Yukarı projeksiyonla açık içerik anahtarını ve değerini hesapla:
   $$k_c = c_{kv} \cdot W_{\text{uk}}, \qquad v_c = c_{kv} \cdot W_{\text{uv}} \quad (\text{uzunluk: } d_{\text{head}})$$
3. **Matrix Absorption** ile sorguyu $d_c$ uzayına emdir:
   $$q_{\text{emilmis}} = q \cdot W_{\text{uk}}^T \quad (\text{uzunluk: } d_c)$$
4. Hem açık dikkat skorunu ($s_{\text{acik}} = q \cdot k_c$) hem de emilmiş dikkat skorunu ($s_{\text{emilmis}} = q_{\text{emilmis}} \cdot c_{kv}$) hesapla ve ikisinin birbirine eşit olduğunu (`abs(s_acik - s_emilmis) < 1e-6`) doğrula.
5. Tüm sayıları `round(val, 6)` ile yuvarlayarak şu sözlüğü döndür:
   - `"c_kv"`: `list[float]`
   - `"k_c"`: `list[float]`
   - `"v_c"`: `list[float]`
   - `"q_emilmis"`: `list[float]`
   - `"dikkat_skoru"`: `round(s_emilmis, 6)`
   - `"emilim_esdeger_mi"`: `bool` (`True`)

```starter
def mla_kv_sikistir_ve_ac(h, q, W_dkv, W_uk, W_uv):
    # KUSURLU BAŞLANGIÇ KODU: Low-rank sıkıştırma ve Matrix Absorption hesabını yapmıyor!
    d_c = len(W_dkv[0])
    d_head = len(q)
    return {
        "c_kv": [0.0] * d_c,
        "k_c": [0.0] * d_head,
        "v_c": [0.0] * d_head,
        "q_emilmis": [0.0] * d_c,
        "dikkat_skoru": 0.0,
        "emilim_esdeger_mi": False,
    }

h_orn = [1.0, 2.0, -1.0]
q_orn = [0.5, 1.5, -0.5]
W_dkv_orn = [[1.0, 0.0], [0.5, 1.0], [-1.0, 2.0]]
W_uk_orn = [[1.0, 2.0, -1.0], [0.5, -0.5, 1.0]]
W_uv_orn = [[2.0, 0.0, 1.0], [-1.0, 1.0, 0.5]]
print("MLA:", mla_kv_sikistir_ve_ac(h_orn, q_orn, W_dkv_orn, W_uk_orn, W_uv_orn))
```

```test
import copy

def sozlesme(fn):
    try:
        h = [1.0, 2.0, -1.0]
        q = [0.5, 1.5, -0.5]
        W_dkv = [[1.0, 0.0], [0.5, 1.0], [-1.0, 2.0]]   # 3 x 2
        W_uk = [[1.0, 2.0, -1.0], [0.5, -0.5, 1.0]]     # 2 x 3
        W_uv = [[2.0, 0.0, 1.0], [-1.0, 1.0, 0.5]]      # 2 x 3
        hk = copy.deepcopy(h)
        r = fn(h, q, W_dkv, W_uk, W_uv)
        if h != hk or not isinstance(r, dict):
            return False
        # c_kv = h @ W_dkv = [1*1 + 2*0.5 + (-1)*(-1), 1*0 + 2*1 + (-1)*2] = [3.0, 0.0]
        # k_c = c_kv @ W_uk = [3.0, 6.0, -3.0]
        # v_c = c_kv @ W_uv = [6.0, 0.0, 3.0]
        # q_emilmis = q @ W_uk^T = [0.5*1 + 1.5*2 + (-0.5)*(-1), 0.5*0.5 + 1.5*(-0.5) + (-0.5)*1] = [4.0, -1.0]
        # skor = q_emilmis . c_kv = 4.0*3.0 + (-1.0)*0.0 = 12.0 (veya q . k_c = 1.5 + 9.0 + 1.5 = 12.0)
        beklenen = {
            "c_kv": [3.0, 0.0],
            "k_c": [3.0, 6.0, -3.0],
            "v_c": [6.0, 0.0, 3.0],
            "q_emilmis": [4.0, -1.0],
            "dikkat_skoru": 12.0,
            "emilim_esdeger_mi": True,
        }
        return r == beklenen
    except Exception:
        return False

ok(sozlesme(mla_kv_sikistir_ve_ac), "c_kv sıkıştırması, k_c/v_c geri açımı ve q_emilmis = q @ W_uk^T Matrix Absorption skoru doğru hesaplanmalı")

def m_skor_bozuk(h, q, W_dkv, W_uk, W_uv):
    r = mla_kv_sikistir_ve_ac(h, q, W_dkv, W_uk, W_uv)
    r["dikkat_skoru"] += 1.0
    return r

def m_q_emilmis_bozuk(h, q, W_dkv, W_uk, W_uv):
    r = mla_kv_sikistir_ve_ac(h, q, W_dkv, W_uk, W_uv)
    r["q_emilmis"] = [0.0 for _ in r["q_emilmis"]]
    return r

for ad, mutant in [("dikkat skorunu yanlış hesaplayan", m_skor_bozuk), ("q_emilmis projeksiyonunu sıfırlayan", m_q_emilmis_bozuk)]:
    ok(not sozlesme(mutant), "hatalı çözüm/mutant yakalanmalı: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def mla_kv_sikistir_ve_ac(h, q, W_dkv, W_uk, W_uv):\n    d_model = len(h)\n    d_c = len(W_dkv[0])\n    d_head = len(q)\n    c_kv = [sum((h[i] * W_dkv[i][r] for i in range(d_model))) for r in range(d_c)]\n    k_c = [sum((c_kv[r] * W_uk[r][d] for r in range(d_c))) for d in range(d_head)]\n    v_c = [sum((c_kv[r] * W_uv[r][d] for r in range(d_c))) for d in range(d_head)]\n    q_emilmis = [sum((q[d] * W_uk[r][d] for d in range(d_head))) for r in range(d_c)]\n    skor_acik = sum((q[d] * k_c[d] for d in range(d_head)))\n    skor_emilmis = sum((q_emilmis[r] * c_kv[r] for r in range(d_c)))\n    esdeger = abs(skor_acik - skor_emilmis) < 1e-06\n    return {'c_kv': [round(v, 6) for v in c_kv], 'k_c': [round(v, 6) for v in k_c], 'v_c': [round(v, 6) for v in v_c], 'q_emilmis': [round(v, 6) for v in q_emilmis], 'dikkat_skoru': round(skor_emilmis, 6), 'emilim_esdeger_mi': esdeger}", 'referans', 'exec'), _REF)
_t, _g = _ff(mla_kv_sikistir_ve_ac, _REF['mla_kv_sikistir_ve_ac'], ([1.0, 2.0, -1.0], [0.5, 1.5, -0.5], [[1.0, 0.0], [0.5, 1.0], [-1.0, 2.0]], [[1.0, 2.0, -1.0], [0.5, -0.5, 1.0]], [[2.0, 0.0, 1.0], [-1.0, 1.0, 0.5]]), tohum=3274, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (mla_kv_sikistir_ve_ac): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
ok(mla_kv_sikistir_ve_ac([0.1234567], [0.2345678], [[0.91]], [[0.83]], [[0.73]]) == _REF['mla_kv_sikistir_ve_ac']([0.1234567], [0.2345678], [[0.91]], [[0.83]], [[0.73]]), "6 basamak MLA yuvarlaması korunmalı")
```

```solution
def mla_kv_sikistir_ve_ac(h, q, W_dkv, W_uk, W_uv):
    d_model = len(h)
    d_c = len(W_dkv[0])
    d_head = len(q)

    # 1. Down-projection: c_kv = h @ W_dkv
    c_kv = [sum(h[i] * W_dkv[i][r] for i in range(d_model)) for r in range(d_c)]

    # 2. Up-projections: k_c = c_kv @ W_uk, v_c = c_kv @ W_uv
    k_c = [sum(c_kv[r] * W_uk[r][d] for r in range(d_c)) for d in range(d_head)]
    v_c = [sum(c_kv[r] * W_uv[r][d] for r in range(d_c)) for d in range(d_head)]

    # 3. Matrix Absorption: q_emilmis = q @ W_uk^T
    q_emilmis = [sum(q[d] * W_uk[r][d] for d in range(d_head)) for r in range(d_c)]

    skor_acik = sum(q[d] * k_c[d] for d in range(d_head))
    skor_emilmis = sum(q_emilmis[r] * c_kv[r] for r in range(d_c))
    esdeger = abs(skor_acik - skor_emilmis) < 1e-6

    return {
        "c_kv": [round(v, 6) for v in c_kv],
        "k_c": [round(v, 6) for v in k_c],
        "v_c": [round(v, 6) for v in v_c],
        "q_emilmis": [round(v, 6) for v in q_emilmis],
        "dikkat_skoru": round(skor_emilmis, 6),
        "emilim_esdeger_mi": esdeger,
    }
```

```hint
`c_kv[r] = sum(h[i] * W_dkv[i][r] for i in range(d_model))` hesapladıktan sonra `q_emilmis[r] = sum(q[d] * W_uk[r][d] for d in range(d_head))` ile sorguyu `d_c` boyutuna indir ve `c_kv` ile iç çarpımını al.
```
:::

::: gorev 2 · Decoupled RoPE + Emilen Latent KV ile MLA Dikkat Hesabı
`mla_bellek_ve_dikkat(q_emilmis, q_rope, c_kv_gecmisi, k_rope_gecmisi, d_head)` işlevini yaz.

DeepSeek `MLA` çıkarım adımında geçmiş $S$ token için KV-Cache'te yalnızca `c_kv_gecmisi` ($S \times d_c$) ve `k_rope_gecmisi` ($S \times d_{\text{rope}}$) tutulmaktadır!

Parametreler:
- `q_emilmis`: $W^{UK}$ içine emilmiş içerik sorgusu ($d_c$ uzunluğunda `list[float]`).
- `q_rope`: Döndürülmüş RoPE sorgu vektörü ($d_{\text{rope}}$ uzunluğunda `list[float]`).
- `c_kv_gecmisi`: Geçmiş $S$ tokenın sıkıştırılmış gizli vektörleri ($S \times d_c$ boyutunda 2B liste).
- `k_rope_gecmisi`: Geçmiş $S$ tokenın paylaşımlı RoPE anahtarları ($S \times d_{\text{rope}}$ boyutunda 2B liste).
- `d_head`: Orijinal dikkat başı boyutu (`int`).

Hesaplanacaklar:
1. Her geçmiş token $t \in \{0, \dots, S-1\}$ için:
   - İçerik çarpımı: $\text{icerik\_t} = q_{\text{emilmis}} \cdot c_{\text{kv}, t}$
   - Konum (RoPE) çarpımı: $\text{rope\_t} = q_{\text{rope}} \cdot k_{\text{rope}, t}$
   - Ölçeklenmiş toplam dikkat skoru:
     $$s_t = \frac{\text{icerik\_t} + \text{rope\_t}}{\sqrt{d_{\text{head}} + d_{\text{rope}}}}$$
2. $s_t$ skorlarına kararlı `Softmax` uygulayarak `"dikkat_agirliklari"` listesini üret.
3. Sıkıştırılmış gizli uzayda ağırlıklı toplam çıktı vektörünü hesapla:
   $$\text{latent\_cikti} = \sum_{t=0}^{S-1} \text{agirlik}_t \cdot c_{\text{kv}, t} \quad (\text{uzunluk: } d_c)$$
4. Tüm sayıları `round(val, 6)` ile yuvarlayarak `{"skorlar": ..., "dikkat_agirliklari": ..., "latent_cikti": ...}` sözlüğünü döndür.

```starter
def mla_bellek_ve_dikkat(q_emilmis, q_rope, c_kv_gecmisi, k_rope_gecmisi, d_head):
    # KUSURLU BAŞLANGIÇ KODU: İçerik + Decoupled RoPE skor birleşimini ve Softmax hesabını yapmıyor!
    s = len(c_kv_gecmisi)
    d_c = len(q_emilmis)
    return {
        "skorlar": [0.0] * s,
        "dikkat_agirliklari": [0.0] * s,
        "latent_cikti": [0.0] * d_c,
    }

print(
    "MLA Dikkat:",
    mla_bellek_ve_dikkat(
        [2.0, 0.0], [1.0, 0.0],
        [[1.5, 1.0], [0.0, 2.0]],
        [[1.0, 0.0], [-1.0, 0.0]],
        d_head=2,
    ),
)
```

```test
import copy
import math

def sozlesme(fn):
    try:
        q_em = [2.0, 0.0]      # d_c = 2
        q_r  = [1.0, 0.0]      # d_rope = 2
        c_kv = [[1.5, 1.0], [0.0, 2.0]]
        k_r  = [[1.0, 0.0], [-1.0, 0.0]]
        # d_head = 2, d_rope = 2 -> sqrt(2 + 2) = 2.0
        # Token 0: icerik = 2*1.5 + 0 = 3.0, rope = 1*1 + 0 = 1.0 -> s0 = (3+1)/2 = 2.0
        # Token 1: icerik = 0.0, rope = -1.0 -> s1 = -1.0 / 2 = -0.5
        q_k = copy.deepcopy(q_em)
        r = fn(q_em, q_r, c_kv, k_r, 2)
        if q_em != q_k or not isinstance(r, dict):
            return False
        if r.get("skorlar") != [2.0, -0.5]:
            return False
        w0 = math.exp(0.0) / (1.0 + math.exp(-2.5))
        w1 = math.exp(-2.5) / (1.0 + math.exp(-2.5))
        if r.get("dikkat_agirliklari") != [round(w0, 6), round(w1, 6)]:
            return False
        b_cikti = [round(w0 * 1.5 + w1 * 0.0, 6), round(w0 * 1.0 + w1 * 2.0, 6)]
        return r.get("latent_cikti") == b_cikti
    except Exception:
        return False

ok(sozlesme(mla_bellek_ve_dikkat), "Decoupled RoPE + içerik skoru, sqrt(d_head + d_rope) ölçeklemesi ve latent çıktı doğru hesaplanmalı")

def m_rope_unutan(q_emilmis, q_rope, c_kv_gecmisi, k_rope_gecmisi, d_head):
    r = mla_bellek_ve_dikkat(q_emilmis, q_rope, c_kv_gecmisi, k_rope_gecmisi, d_head)
    r["skorlar"] = [0.0 for _ in r["skorlar"]]
    return r

def m_yanlis_payda(q_emilmis, q_rope, c_kv_gecmisi, k_rope_gecmisi, d_head):
    r = mla_bellek_ve_dikkat(q_emilmis, q_rope, c_kv_gecmisi, k_rope_gecmisi, d_head)
    r["latent_cikti"][0] += 1.0
    return r

for ad, mutant in [("Decoupled RoPE skorunu unutan", m_rope_unutan), ("latent çıktıyı yanlış ağırlıklandıran", m_yanlis_payda)]:
    ok(not sozlesme(mutant), "hatalı çözüm/mutant yakalanmalı: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef mla_bellek_ve_dikkat(q_emilmis, q_rope, c_kv_gecmisi, k_rope_gecmisi, d_head):\n    d_c = len(q_emilmis)\n    d_rope = len(q_rope)\n    olcek = math.sqrt(d_head + d_rope)\n    skorlar = []\n    for c_t, kr_t in zip(c_kv_gecmisi, k_rope_gecmisi):\n        icerik_skoru = sum((q_emilmis[i] * c_t[i] for i in range(d_c)))\n        rope_skoru = sum((q_rope[j] * kr_t[j] for j in range(d_rope)))\n        skorlar.append((icerik_skoru + rope_skoru) / olcek)\n    m = max(skorlar)\n    exps = [math.exp(s - m) for s in skorlar]\n    payda = sum(exps)\n    agirliklar = [e / payda for e in exps]\n    latent_cikti = [round(sum((agirliklar[t] * c_kv_gecmisi[t][i] for t in range(len(c_kv_gecmisi)))), 6) for i in range(d_c)]\n    return {'skorlar': [round(s, 6) for s in skorlar], 'dikkat_agirliklari': [round(w, 6) for w in agirliklar], 'latent_cikti': latent_cikti}", 'referans', 'exec'), _REF)
_t, _g = _ff(mla_bellek_ve_dikkat, _REF['mla_bellek_ve_dikkat'], ([2.0, 0.0], [1.0, 0.0], [[1.5, 1.0], [0.0, 2.0]], [[1.0, 0.0], [-1.0, 0.0]], 2), tohum=3131, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (mla_bellek_ve_dikkat): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
ok(mla_bellek_ve_dikkat([1000.0], [0.0], [[2.0], [0.5]], [[0.0], [0.0]], 1) == _REF['mla_bellek_ve_dikkat']([1000.0], [0.0], [[2.0], [0.5]], [[0.0], [0.0]], 1), "büyük skor softmax kararlılığı korunmalı")
```

```solution
import math

def mla_bellek_ve_dikkat(q_emilmis, q_rope, c_kv_gecmisi, k_rope_gecmisi, d_head):
    d_c = len(q_emilmis)
    d_rope = len(q_rope)
    olcek = math.sqrt(d_head + d_rope)

    skorlar = []
    for c_t, kr_t in zip(c_kv_gecmisi, k_rope_gecmisi):
        icerik_skoru = sum(q_emilmis[i] * c_t[i] for i in range(d_c))
        rope_skoru = sum(q_rope[j] * kr_t[j] for j in range(d_rope))
        skorlar.append((icerik_skoru + rope_skoru) / olcek)

    m = max(skorlar)
    exps = [math.exp(s - m) for s in skorlar]
    payda = sum(exps)
    agirliklar = [e / payda for e in exps]

    latent_cikti = [
        round(sum(agirliklar[t] * c_kv_gecmisi[t][i] for t in range(len(c_kv_gecmisi))), 6)
        for i in range(d_c)
    ]

    return {
        "skorlar": [round(s, 6) for s in skorlar],
        "dikkat_agirliklari": [round(w, 6) for w in agirliklar],
        "latent_cikti": latent_cikti,
    }
```

```hint
Her token için `(sum(q_emilmis * c_t) + sum(q_rope * kr_t)) / math.sqrt(d_head + len(q_rope))` ile skoru bul. Softmax ağırlıklarını hesapladıktan sonra `c_kv_gecmisi` satırlarının ağırlıklı toplamını al.
```
:::

::: anlat Gerçek deney: SmolLM2'nin gerçek K/V ağırlıklarından MLA latent'i ve rank–kalite dengesi
SmolLM2-135M MLA ile eğitilmemiştir; final, gerçek ağırlıklarından bir MLA latent'i **çıkarır** (indirme yok):

- 4. katmanın `k_proj` ve `v_proj` ağırlıkları yan yana konur: $M = [W_k^\top \mid W_v^\top]$ (576×384), yani $h M = [k \mid v]$. SVD ile $M \approx (U_r S_r) V_r^\top$ ayrıştırılır: $W_{dkv} = U_r S_r$ ortak aşağı projeksiyon, $V_r^\top$'nin anahtar ve değer sütunları $W_{uk}$, $W_{uv}$ yukarı projeksiyonlardır.
- Gerçek bir gizli durum ve gerçek bir sorguyla senin `mla_kv_sikistir_ve_ac` işlevin çağrılır: `c_kv`, açılmış `k`/`v`, emilmiş sorgu ve skor torch ile karşılaştırılır. Emilim (absorption) sayesinde önbellekte yalnız `c_kv` (r sayı) tutulur.
- **Decoupled RoPE:** gerçek sorgu ve anahtarın son 16 boyutu gerçek RoPE ile döndürülür ve küçük bir konum kolu olur. Senin `mla_bellek_ve_dikkat` işlevin içerik skorunu latent üzerinden, konum skorunu bu koldan hesaplar; ağırlıklar ve latent çıktı torch ile karşılaştırılır.
- **Rank–kalite dengesi:** tüm 30 katmanın K/V'si rank r latent'ten üretilir ve gerçek bir paragrafta perplexity ölçülür. İki yöntem karşılaştırılır: yalnız ağırlığın SVD'si ve **aktivasyon farkında** SVD (kalibrasyon metninden gizli durum kovaryansıyla beyazlatılmış SVD; $\min \lVert X(M - M_r) \rVert$). Tam rankta (384) model birebir geri gelmelidir.

**Güvenlik yönü — sıkıştırılmış KV-cache hâlâ kişisel veridir:** KV-cache'i sıkıştırmak içeriği gizlemez. 1. katmanın K/V'si 6 000 tokenlık gerçek İngilizce metinle toplanır ve KV'den (ya da rank r latent'ten) token gömmesine giden doğrusal bir ridge eşlemesi öğrenilir. Bu eşleme hiç görmediği bir müşteri notunun önbelleğine uygulanır ve her konumda en yakın token aranır. Tam KV'den metnin büyük kısmı (isim, fatura sözcüğü, cümle yapısı) geri gelir; düşük rank latent daha az, ama sıfırdan çok daha fazla sızdırır. Paylaşılan ya da diske yazılan önbellekler (prefix caching, oturumlar arası KV paylaşımı) erişim denetimi gerektiren kişisel veridir.

Kabul: iki işlevin farksal taramayı geçmesi; MLA çıktılarının torch'tan göreli `1e-5` altında ve emilimin eşdeğer olması; decoupled RoPE'lu dikkatin torch ile aynı olması; tam rankta perplexity'nin değişmemesi; rank 192'de aktivasyon farkında SVD'nin ağırlık SVD'sinden iyi olması. Ayrıca tam KV'den görülmemiş metnin token doğruluğu en az 0.7 olmalı, rank 128 latent 0.2'yi aşmalı ve doğruluk rankla artmalıdır.

**Kanıt dosyasını oku:** `tekil_degerler_ilk8`, `rank_r_k_goreli_hata`, `rank_egrisi` (`ppl_agirlik_svd`, `ppl_aktivasyon_svd`, `kv_sayi_token`), `kv_sayi_token_gqa`. Soru 1: Ağırlığın enerjisinin büyük kısmı ilk tekil değerlerdeyken neden ağırlık SVD'si perplexity'yi bu kadar bozuyor? Soru 2: DeepSeek gibi baştan MLA ile eğitilen bir model neden aynı rankta çok daha iyi olur? Soru 3: Hangi rankta KV-cache GQA'dan küçük olur ve kalite ne durumda?
:::

::: gorev Gerçek deney · SmolLM2 K/V ağırlıklarından SVD ile MLA latent'i, emilim ve rank–perplexity eğrisi
Önceki görevlerdeki `mla_kv_sikistir_ve_ac`, `mla_bellek_ve_dikkat` işlevlerini buraya birleştir (çözümlerini kopyalayabilirsin). Çalıştır gerçek ölçüm tablosunu gösterir; Kontrol Et önce işlevlerini gizli verilerle ve farksal taramayla sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
timeout: 240
```
```starter
import ai_lab
def mla_kv_sikistir_ve_ac(h, q, W_dkv, W_uk, W_uv):
    d_c = len(W_dkv[0])
    d_head = len(q)
    return {'c_kv': [0.0] * d_c, 'k_c': [0.0] * d_head, 'v_c': [0.0] * d_head, 'q_emilmis': [0.0] * d_c, 'dikkat_skoru': 0.0, 'emilim_esdeger_mi': False}

def mla_bellek_ve_dikkat(q_emilmis, q_rope, c_kv_gecmisi, k_rope_gecmisi, d_head):
    s = len(c_kv_gecmisi)
    d_c = len(q_emilmis)
    return {'skorlar': [0.0] * s, 'dikkat_agirliklari': [0.0] * s, 'latent_cikti': [0.0] * d_c}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_17 as D
    D.goster(mla_kv_sikistir_ve_ac, mla_bellek_ve_dikkat)
```
```test
import ai_lab
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('_ortak_svd', '_dusuk_rank_model', '_kalibrasyon', 'kanit_yaz'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
mla_kv_sikistir_ve_ac = need("mla_kv_sikistir_ve_ac")
mla_bellek_ve_dikkat = need("mla_bellek_ve_dikkat")
# farksal tarama (görev çözümlerinden derlenen referans)
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def mla_kv_sikistir_ve_ac(h, q, W_dkv, W_uk, W_uv):\n    d_model = len(h)\n    d_c = len(W_dkv[0])\n    d_head = len(q)\n    c_kv = [sum((h[i] * W_dkv[i][r] for i in range(d_model))) for r in range(d_c)]\n    k_c = [sum((c_kv[r] * W_uk[r][d] for r in range(d_c))) for d in range(d_head)]\n    v_c = [sum((c_kv[r] * W_uv[r][d] for r in range(d_c))) for d in range(d_head)]\n    q_emilmis = [sum((q[d] * W_uk[r][d] for d in range(d_head))) for r in range(d_c)]\n    skor_acik = sum((q[d] * k_c[d] for d in range(d_head)))\n    skor_emilmis = sum((q_emilmis[r] * c_kv[r] for r in range(d_c)))\n    esdeger = abs(skor_acik - skor_emilmis) < 1e-06\n    return {'c_kv': [round(v, 6) for v in c_kv], 'k_c': [round(v, 6) for v in k_c], 'v_c': [round(v, 6) for v in v_c], 'q_emilmis': [round(v, 6) for v in q_emilmis], 'dikkat_skoru': round(skor_emilmis, 6), 'emilim_esdeger_mi': esdeger}\n\nimport math\n\ndef mla_bellek_ve_dikkat(q_emilmis, q_rope, c_kv_gecmisi, k_rope_gecmisi, d_head):\n    d_c = len(q_emilmis)\n    d_rope = len(q_rope)\n    olcek = math.sqrt(d_head + d_rope)\n    skorlar = []\n    for c_t, kr_t in zip(c_kv_gecmisi, k_rope_gecmisi):\n        icerik_skoru = sum((q_emilmis[i] * c_t[i] for i in range(d_c)))\n        rope_skoru = sum((q_rope[j] * kr_t[j] for j in range(d_rope)))\n        skorlar.append((icerik_skoru + rope_skoru) / olcek)\n    m = max(skorlar)\n    exps = [math.exp(s - m) for s in skorlar]\n    payda = sum(exps)\n    agirliklar = [e / payda for e in exps]\n    latent_cikti = [round(sum((agirliklar[t] * c_kv_gecmisi[t][i] for t in range(len(c_kv_gecmisi)))), 6) for i in range(d_c)]\n    return {'skorlar': [round(s, 6) for s in skorlar], 'dikkat_agirliklari': [round(w, 6) for w in agirliklar], 'latent_cikti': latent_cikti}", 'referans', 'exec'), _REF)
_t, _g = _ff(mla_kv_sikistir_ve_ac, _REF['mla_kv_sikistir_ve_ac'], ([1.0, 2.0, -1.0], [0.5, 1.5, -0.5], [[1.0, 0.0], [0.5, 1.0], [-1.0, 2.0]], [[1.0, 2.0, -1.0], [0.5, -0.5, 1.0]], [[2.0, 0.0, 1.0], [-1.0, 1.0, 0.5]]), tohum=3274, en_cok=600, mod='gecerli', butce='oto')
kontrol(_t, "farksal tarama (mla_kv_sikistir_ve_ac): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(mla_bellek_ve_dikkat, _REF['mla_bellek_ve_dikkat'], ([2.0, 0.0], [1.0, 0.0], [[1.5, 1.0], [0.0, 2.0]], [[1.0, 0.0], [-1.0, 0.0]], 2), tohum=3131, en_cok=600, mod='gecerli', butce='oto')
kontrol(_t, "farksal tarama (mla_bellek_ve_dikkat): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
kontrol(mla_kv_sikistir_ve_ac([0.1234567], [0.2345678], [[0.91]], [[0.83]], [[0.73]]) == _REF['mla_kv_sikistir_ve_ac']([0.1234567], [0.2345678], [[0.91]], [[0.83]], [[0.73]]), "6 basamak MLA yuvarlaması korunmalı")
kontrol(mla_bellek_ve_dikkat([1000.0], [0.0], [[2.0], [0.5]], [[0.0], [0.0]], 1) == _REF['mla_bellek_ve_dikkat']([1000.0], [0.0], [[2.0], [0.5]], [[0.0], [0.0]], 1), "büyük skor softmax kararlılığı korunmalı")
if not all(checks): stop()
from sandbox import ai_gercek_ai_uretim_17 as D
try: r = D.deney(mla_kv_sikistir_ve_ac, mla_bellek_ve_dikkat)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r['mla_ayni'], 'MLA sıkıştırma/açma ve emilmiş skor gerçek ağırlıklarla torch ile aynı')
kontrol(r['dikkat_ayni'], "decoupled RoPE'lu latent dikkat gerçek değerlerle torch ile aynı")
kontrol(r['tam_rank_ayni'], 'tam rankta (384) perplexity orijinal modelle aynı')
kontrol(r['aktivasyon_svd_daha_iyi'], "rank 192'de aktivasyon farkında SVD ağırlık SVD'sinden düşük perplexity veriyor")
kontrol(r['kv_sizdiriyor'], "görülmemiş müşteri notu KV'den doğrusal bir eşlemeyle büyük ölçüde geri okundu; latent rankı azaldıkça sızıntı azaldı ama sıfırlanmadı")
ai_lab.kanit_yaz("ai-uretim-17-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-uretim-17", "deney": r})
```
```solution
import ai_lab
def mla_kv_sikistir_ve_ac(h, q, W_dkv, W_uk, W_uv):
    d_model = len(h)
    d_c = len(W_dkv[0])
    d_head = len(q)
    c_kv = [sum((h[i] * W_dkv[i][r] for i in range(d_model))) for r in range(d_c)]
    k_c = [sum((c_kv[r] * W_uk[r][d] for r in range(d_c))) for d in range(d_head)]
    v_c = [sum((c_kv[r] * W_uv[r][d] for r in range(d_c))) for d in range(d_head)]
    q_emilmis = [sum((q[d] * W_uk[r][d] for d in range(d_head))) for r in range(d_c)]
    skor_acik = sum((q[d] * k_c[d] for d in range(d_head)))
    skor_emilmis = sum((q_emilmis[r] * c_kv[r] for r in range(d_c)))
    esdeger = abs(skor_acik - skor_emilmis) < 1e-06
    return {'c_kv': [round(v, 6) for v in c_kv], 'k_c': [round(v, 6) for v in k_c], 'v_c': [round(v, 6) for v in v_c], 'q_emilmis': [round(v, 6) for v in q_emilmis], 'dikkat_skoru': round(skor_emilmis, 6), 'emilim_esdeger_mi': esdeger}

import math

def mla_bellek_ve_dikkat(q_emilmis, q_rope, c_kv_gecmisi, k_rope_gecmisi, d_head):
    d_c = len(q_emilmis)
    d_rope = len(q_rope)
    olcek = math.sqrt(d_head + d_rope)
    skorlar = []
    for c_t, kr_t in zip(c_kv_gecmisi, k_rope_gecmisi):
        icerik_skoru = sum((q_emilmis[i] * c_t[i] for i in range(d_c)))
        rope_skoru = sum((q_rope[j] * kr_t[j] for j in range(d_rope)))
        skorlar.append((icerik_skoru + rope_skoru) / olcek)
    m = max(skorlar)
    exps = [math.exp(s - m) for s in skorlar]
    payda = sum(exps)
    agirliklar = [e / payda for e in exps]
    latent_cikti = [round(sum((agirliklar[t] * c_kv_gecmisi[t][i] for t in range(len(c_kv_gecmisi)))), 6) for i in range(d_c)]
    return {'skorlar': [round(s, 6) for s in skorlar], 'dikkat_agirliklari': [round(w, 6) for w in agirliklar], 'latent_cikti': latent_cikti}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_17 as D
    D.goster(mla_kv_sikistir_ve_ac, mla_bellek_ve_dikkat)
```
```hint
İki görevin çözümlerini olduğu gibi buraya koy.
```
:::

::: anlat Sınır
Görevler MLA'nın düşük ranklı ortak KV sıkıştırmasını, matris yutma (absorption) eşdeğerliğini ve decoupled RoPE ile dikkat skorunu küçük matrislerle hesaplatır; final adım latent'i gerçek SmolLM2 ağırlıklarından SVD ile çıkarır (gerçek bir DeepSeek modeli kullanılmaz). Absorption yalnız RoPE uygulanmayan kısım için geçerlidir; RoPE konuma bağlı olduğundan ayrı ve küçük bir anahtar kolu (decoupled RoPE) gerekir. Sıkıştırma oranı ile kalite dengesi eğitimle öğrenilir; eğitilmiş bir GQA modelini ek eğitim olmadan düşük ranklı yaklaşımla MLA'ya çevirmek kalite kaybettirir. Absorption hesap sırasını değiştirdiği için sayısal sonuçlar toleransla karşılaştırılmalıdır.

Kaynaklar: [DeepSeek-AI 2024 - DeepSeek-V2: A Strong, Economical, and Efficient Mixture-of-Experts Language Model](https://arxiv.org/abs/2405.04434), [DeepSeek-AI 2024 - DeepSeek-V3 Technical Report](https://arxiv.org/abs/2412.19437).
:::

::: dusun
DeepSeek-V2/V3 makalesinde yalnızca Anahtar ve Değer (`KV`) sıkıştırıldığı halde **Sorgu (`Query` $q_t$) vektörlerine de `Low-Rank Compression` ($c_t^Q = h_t W^{DQ}$)** uygulandığı görülür.
Oysa çıkarım (`Inference`) sırasında Sorgu ($Q$) vektörleri **KV-Cache içinde saklanmaz** (yalnızca o anki aktif token için hesaplanıp atılır).

Madem Sorgu ($Q$) vektörleri KV-Cache belleğinde yer kaplamıyor, DeepSeek mühendisleri neden $Q$ projeksiyonunu da düşük-ranklı bir darboğazdan ($c_t^Q \in \mathbb{R}^{1536}$) geçirmiştir? Bir önceki derste öğrendiğin **Eğitim Sırasındaki Aktivasyon Belleği (`Training Activation Memory`)** ve **Parametre Sayısı** açısından bu kararın sebebini açıkla.
:::

::: ozet
- **Multi-Head Latent Attention (`MLA`)**, tüm dikkat başlarının `Key` ve `Value` matrislerini ayrı ayrı önbelleğe almak yerine onları ortak, düşük boyutlu bir gizli vektöre (**`Low-Rank Latent Vector` $c_t^{KV} \in \mathbb{R}^{d_c}$**) sıkıştırarak KV-Cache belleğini `%93`'ten fazla küçültür.
- **`Matrix Absorption Trick`**, doğrusal yukarı projeksiyon matrisleri $W^{UK}$ ve $W^{UV}$'yi çıkarım sırasında $W^Q$ ve $W^O$ ağırlıklarının içine yutarak $c_t^{KV}$ vektörlerini hiç genişletmeden doğrudan sıkıştırılmış uzayda dikkat hesaplanmasını sağlar.
- `RoPE` rotasyonu araya pozisyona bağımlı bir matris sokarak `Matrix Absorption` özelliğini bozacağı için, **`Decoupled RoPE`** tekniğiyle konum bilgisi küçük ve paylaşımlı bir $k_t^R$ anahtar koluna ayrıştırılır.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **GQA'nın ötesinde `KV Cache` sıkıştırma (30 sn).** "Uzun bağlamlı çıkarımda her token için tüm kafa anahtar ve değerlerini saklamak belleği tıkar; `MLA`, $K$ ve $V$'yi $d_c \ll n_h d_h$ boyutlu tek bir ortak gizli vektöre ($c_t^{KV}$) indirerek önbellekte yalnız bu sıkıştırılmış vektörü tutar."
2. **Matris yutma (`Matrix Absorption`) (35 sn).** "Çıkarım anında $c_t^{KV}$'yi tekrar tam boyuta açmak yerine yukarı-projeksiyon matrisi sorgu tarafına ($W^{UQ}$ içine) cebirsel olarak yutulur; böylece önbellek hiç açılmadan doğrudan gizli uzayda dikkat skoru hesaplanır."
3. **Neden `Decoupled RoPE` şarttır? (30 sn).** "Konuma bağlı dönme matrisi $R_t$ araya girdiğinde sabit matris yutma bozulur; bu yüzden küçük bir konumsal dal (`k^R`) sıkıştırmadan ayrı taşınıp skor aşamasında eklenir."
4. **Soru (25 sn).** "Gizli boyut $d_c$ aşırı küçültüldüğünde hangi tür ince taneli anahtar-değer geri çağırma (`exact key lookup`) görevleri ilk olarak bozulur?"
:::
