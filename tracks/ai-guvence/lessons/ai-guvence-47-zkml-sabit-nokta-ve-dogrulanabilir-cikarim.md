---
id: ai-guvence-47
title: zkML, Sabit Nokta Aritmetiği ve Doğrulanabilir Çıkarım · Kanıtlanabilir Model Hesabı
summary: Kayan noktalı ağırlıkları sabit nokta (fixed-point) tam sayılarına nicemle, ölçekli iç çarpım ve bölme kalanı kısıtını kur; ağırlık taahhüdü (commitment) ile çıkarım kanıtını GPU'da doğrula.
esleme: ai-guvence-22, ai-guvence-25, ai-guvence-36
timeout: 60
---

::: anlat Uzaktaki sunucunun gerçekten ilan ettiği modeli çalıştırdığını nasıl kanıtlarsın?
**Deneyin tam sınırı:** Gerçek MLP hesabından alınan ağırlıklarla fixed-point arithmetic ve hash doğrulaması yapılır. Görev kriptografik bir ZK prover/verifier çalıştırmaz; zero-knowledge privacy veya tam SNARK güvenliği kabulü değildir.

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Kriptografik kanıt sistemleri (`zkML` / `SNARK`) IEEE-754 işlemlerini doğrudan aritmetik devrede temsil etmek maliyetli olabilir; birçok tasarım modeli $S = 2^k$ ölçekli **`fixed-point arithmetic`** tam sayı devresine çevirir | İlk üç görev: `veri/zkml.json` içindeki **sentetik** sabit nokta vektörleri ve SHA-256 özeti. Final: GPU'da eğitilen MLP'nin gerçek ağırlıklarının $2^{10}$ ölçeğinde nicemlenmesi ve devre doğrulaması | Sabit nokta aritmetik doğrulamasının tek başına sıfır-bilgi (`zero-knowledge`) gizliliği sağladığını kanıtlamaz; gizlilik için ayrıca sonlu cisim üzerinde polinom taahhüdü gerekir |
| İlan edilen ağırlık taahhüdü (`commitment`) ve tam sayı bölme kısıtı ($H = Q \cdot S + R$), sunucunun gizlice daha ucuz veya hileli bir model çalıştırmasını engeller | Sabit nokta quantization, $S^2 \to S$ yeniden ölçekleme kısıtı ve SHA-256 ağırlık taahhüdü | Nicemlenmiş modelin her girdide `float32` modelle bire bir aynı argmax kararını vereceğini garanti etmez |

> [!NOT]
> Görevler `veri/zkml.json` dosyasını okur; dosya sentetiktir. Setup her Çalıştır/Kontrol Et adımında geçici kopya kurar; değişiklikler taşınmaz, **kalıcılık yoktur**. Ekranda ayrı dosya görüntüleyici yoktur; içeriği görmek için `print` kullan. Gizli testler ayrıdır. Final yeni model indirmez ve GPU varsa onu kullanır.

Bir API sağlayıcısı "güvenlik denetiminden geçmiş `Model-A` ağırlıklarını çalıştırıyorum" dediğinde, istemciye yalnızca çıktı vektörünü gönderir. Sağlayıcının maliyeti düşürmek için daha küçük bir model çalıştırmadığını veya çıktıyı elle değiştirmediğini kanıtlamak **`verifiable inference` (`zkML`)** alanıdır (Kang vd. 2022; Liu vd. 2021; Sun vd. 2024).

**1. Neden `fixed-point arithmetic` gerekir?** Aritmetik devreler sonlu cisim tam sayıları üzerinde çalışır. Kayan noktalı bir sayı $x \in \mathbb{R}$, ölçek üssü $k$ ($S = 2^k$) kullanılarak tam sayıya nicemlenir (`quantization`):
$$q = \lfloor x \cdot S + 0.5 \rfloor, \qquad \hat{x} = \frac{q}{S}$$

**2. Çarpımda ölçek patlaması ($S^2 \to S$) ve bölme kısıtı:** Hem girdi $q_x$ hem ağırlık $q_w$ ölçek $S$ ile çarpılmış olduğundan, iç çarpım $\sum_j q_{x,j} q_{w,j}$ **$S^2$ ölçeğindedir**. Ölçek $S$'deki bias $q_b$'yi toplamak için önce $q_b \cdot S$ ile aynı ölçeğe ($S^2$) getirilir:
$$H = \sum_{j=1}^d q_{x,j}\, q_{w,j} + q_b \cdot S$$
Sonucu tekrar ölçek $S$'ye indirmek için tam sayı bölmesi yapılır:
$$Q = H \mathbin{//} S, \qquad R = H \bmod S, \qquad H = Q \cdot S + R \quad (0 \le R < S)$$
Doğrulayıcı devrede bölme işlemi yerine $H = Q \cdot S + R$ ve $0 \le R < S$ kısıtını kontrol eder; ardından ReLU kapısı $\text{relu\_cikti} = \max(0, Q)$ üretir.

**3. Model ağırlık taahhüdü (`commitment`):** Sağlayıcı denetimden geçen nicemlenmiş ağırlıklarının kanonik temsilini (`"w_0,w_1,...|q_bias|olcek_us"`) kriptografik özet (`SHA-256`) olarak yayınlar. Kanıt doğrulaması hem ağırlık özetinin (`ozet_eslesti`) hem de devre çıktısının (`hesap_dogru`) eşleşmesini şart koşar.

**Saldırgan (hileli sunucu) ne dener?**
- Ağırlıkları değiştirmeden çıktıyı manipüle etmeye çalışır (`hesap_dogru=False` yakalar).
- İddia edilen çıktıyı verecek sahte ağırlıklar uydurur (`ozet_eslesti=False` yakalar).
- Çarpım sonrası $S$'ye bölmeyi atlayıp veya bias'ı yanlış ölçekte ekleyip yuvarlama farkını istismar etmeye çalışır.

**Savunma neden kırılır?** Ölçek üssü $k$ çok küçük seçilirse (`olcek_us=2` gibi) quantization hatası büyür ve dürüst devre bile yanlış sınıf tahmin eder; çok büyük seçilirse sonlu cisim taşması (`field overflow`) yaşanır.

**Görev 1 ve 2'de sık tuzaklar:** Python'un çift sayıya yuvarlayan `round()` işlevi yerine deterministik `int(math.floor(x * S + 0.5))` kullanmamak. İç çarpımda `q_bias` değerini $S$ ile çarpmadan doğrudan $S^2$ ölçekli toplama eklemek.

Kaynaklar: [Liu vd. 2021 (zkCNN)](https://arxiv.org/abs/2106.07076), [Kang vd. 2022 (Scaling up Trustless DNN Inference)](https://arxiv.org/abs/2210.08674), [Sun vd. 2024 (zkLLM)](https://arxiv.org/abs/2404.16109), [Weng vd. 2021 (Mystique)](https://arxiv.org/abs/2105.04709). Bu dersteki bütün sayılar yalnız yerel kanıttan gelir.

Köprü: ai-guvence-22 ve ai-guvence-25 ağırlık bütünlüğünü, ai-guvence-36 sayısal hassasiyeti inceler; bu ders çıkarım hesabının kendisini tam sayı devresiyle doğrular.
:::

::: tahmin İki sabit nokta sayısının çarpımı neden S² ölçeğindedir?
Çıktıyı tahmin et, sonra Çalıştır ile karşılaştır.
```python
S = 1 << 8  # 256
x, w, b = 0.5, 0.5, 0.125
qx, qw, qb = int(x * S), int(w * S), int(b * S)
ham = qx * qw + qb * S
olcekli = ham // S
print("qx, qw, qb:", qx, qw, qb)
print("Yanlış (bölmesiz):", qx * qw + qb, "-> float:", (qx * qw + qb) / S)
print("Doğru ölçekli:", olcekli, "-> float:", olcekli / S)
```
???
```cikti
qx, qw, qb: 128 128 32
Yanlış (bölmesiz): 16416 -> float: 64.125
Doğru ölçekli: 96 -> float: 0.375
```
Tahmininle gerçek çıktı arasındaki farkı tezgâhta yorum satırı olarak yaz: $0.5 \times 0.5 + 0.125 = 0.375$ sonucunu tam sayı devresinde elde etmek için `qb` neden önce `S` ile çarpılıp toplam sonra `S`'ye bölündü? Sonra üç kusurlu başlangıç kodunu çalıştır ve her birinin neyi kaçırdığını önce kendin teşhis et; açıklama çözümün ardından gelir.
:::

::: gorev 1 · Sabit nokta (fixed-point) quantization ve hata ölçümü
`sabit_nokta_nicemle(degerler, olcek_us)`: `degerler` dolu liste, elemanları bool olmayan sonlu sayı; `olcek_us` bool olmayan `int` ve $1 \le \text{olcek\_us} \le 24$. $S = 2^{\text{olcek\_us}}$ için her elemanı `q = int(math.floor(x * S + 0.5))` ile tam sayıya çevir, `g = float(q / S)` ile geri yükle ve `max_hata = max(abs(x - g))` hesapla. `{"tam_sayilar": [...], "geri_yuklenen": [...], "max_hata": float}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-47")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def sabit_nokta_nicemle(degerler, olcek_us):
    q = [int(x * olcek_us) for x in degerler]
    return {"tam_sayilar": q, "geri_yuklenen": [float(v) for v in degerler], "max_hata": 0.0}

from ai_guvence_veri import json_yukle
v = json_yukle("veri/zkml.json")
print(sabit_nokta_nicemle(v["degerler"], v["olcek_us"]))
```
```test
def sinama1(f):
    import copy, math, random
    def _r(deg, u):
        s = 1 << u; q = [int(math.floor(x * s + 0.5)) for x in deg]; g = [float(v / s) for v in q]
        return {"tam_sayilar": q, "geri_yuklenen": g, "max_hata": float(max(abs(x - y) for x, y in zip(deg, g)))}
    def _y(a, b):
        if not isinstance(a, dict) or set(a) != set(b) or a["tam_sayilar"] != b["tam_sayilar"]: return False
        if not all(isinstance(v, int) and not isinstance(v, bool) for v in a["tam_sayilar"]): return False
        return all(abs(p - q) < 1e-12 for p, q in zip(a["geri_yuklenen"], b["geri_yuklenen"])) and abs(a["max_hata"] - b["max_hata"]) < 1e-12
    try:
        d = [0.5, -0.25, 0.125]; old = list(d)
        if not _y(f(d, 4), {"tam_sayilar": [8, -4, 2], "geri_yuklenen": [0.5, -0.25, 0.125], "max_hata": 0.0}) or d != old:
            return False
        # Yarı değer yuvarlaması (floor(x*S + 0.5))
        if f([0.25], 1)["tam_sayilar"] != [1]: return False
        rng = random.Random(47)
        for _ in range(25):
            rd = [rng.uniform(-3, 3) for _ in range(rng.randint(1, 7))]; ru = rng.randint(1, 16)
            if not _y(f(list(rd), ru), _r(rd, ru)): return False
        for bad in ((None, 8), ([], 8), ([True], 8), ([float("nan")], 8), (d, 0), (d, 25), (d, True), (d, 8.0)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
ok(sinama1(sabit_nokta_nicemle), "2^k ölçekleme, floor(x*S+0.5) yuvarlama, max hata ve geçersiz girdi")
for ad, mut in [
    ("max hata sıfır", lambda d, u: dict(sabit_nokta_nicemle(d, u), max_hata=0.0)),
    ("int kesme", lambda d, u: dict(sabit_nokta_nicemle(d, u), tam_sayilar=[int(x * (1 << u)) for x in d])),
    ("yanlış ölçek", lambda d, u: sabit_nokta_nicemle(d, max(1, u - 1)) if u > 1 else dict(sabit_nokta_nicemle(d, u), max_hata=1.0))
]:
    ok(not sinama1(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(sabit_nokta_nicemle, _il.import_module('ai_gercek_ai_guvence_47').referans_sabit_nokta_nicemle, ([0.5, -0.25, 0.75, 0.123], 8), tohum=3143)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def sabit_nokta_nicemle(degerler, olcek_us):
    if not isinstance(degerler, list) or not degerler: raise ValueError("degerler")
    for x in degerler:
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x): raise ValueError("sayı")
    if isinstance(olcek_us, bool) or not isinstance(olcek_us, int) or not 1 <= olcek_us <= 24:
        raise ValueError("olcek_us")
    s = 1 << olcek_us
    q = [int(math.floor(x * s + 0.5)) for x in degerler]
    geri = [float(v / s) for v in q]
    hata = max(abs(x - g) for x, g in zip(degerler, geri))
    return {"tam_sayilar": q, "geri_yuklenen": geri, "max_hata": float(hata)}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    v = json_yukle("veri/zkml.json")
    print(sabit_nokta_nicemle(v["degerler"], v["olcek_us"]))
```
```hint
`s = 1 << olcek_us` kullan ve her sayıyı `int(math.floor(x * s + 0.5))` ile nicemle.
```
:::

::: anlat Sabit nokta iç çarpım ve yeniden ölçekleme kısıtı
Nicemlenmiş girdi $q_x$, ağırlık $q_w$ ve bias $q_b$ (üçü de bool olmayan `int` ve ölçek $S = 2^{\text{olcek\_us}}$) için:
- `ham_toplam`: $H = \sum_j q_{x,j} \cdot q_{w,j} + q_b \cdot S$
- `olcekli_cikti`: $Q = H \mathbin{//} S$
- `kalan`: $R = H \bmod S$
- `relu_cikti`: $\max(0, Q)$

**Görev 2'de sık tuzaklar:** `q_bias` değerini $S$ ile çarpmadan toplamak veya tam sayı bölmesi `//` yerine kayan nokta bölmesi `/` kullanmak.
:::

::: gorev 2 · Sabit nokta iç çarpım ve ReLU kapısı
`sabit_nokta_ic_carpim(q_girdi, q_agirlik, q_bias, olcek_us)`: `q_girdi` ve `q_agirlik` aynı uzunlukta ($d \ge 1$) dolu liste, elemanları bool olmayan `int`; `q_bias` bool olmayan `int`; `olcek_us` bool olmayan `int` ($1 \le \text{olcek\_us} \le 24$). `{"ham_toplam": int, "olcekli_cikti": int, "kalan": int, "relu_cikti": int}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-47")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def sabit_nokta_ic_carpim(q_girdi, q_agirlik, q_bias, olcek_us):
    ham = sum(x * w for x, w in zip(q_girdi, q_agirlik)) + q_bias
    return {"ham_toplam": ham, "olcekli_cikti": ham, "kalan": 0, "relu_cikti": ham}

from ai_guvence_veri import json_yukle
v = json_yukle("veri/zkml.json")
print(sabit_nokta_ic_carpim(v["q_girdi"], v["q_agirlik"], v["q_bias"], v["olcek_us"]))
```
```test
def sinama2(f):
    import copy, math, random
    def _r(qx, qw, qb, u):
        s = 1 << u; h = sum(x * w for x, w in zip(qx, qw)) + qb * s
        return {"ham_toplam": int(h), "olcekli_cikti": int(h // s), "kalan": int(h % s), "relu_cikti": int(max(0, h // s))}
    try:
        qx = [128, 64, 192]; qw = [128, -64, 192]; old = (list(qx), list(qw))
        if f(qx, qw, 32, 8) != {"ham_toplam": 57344, "olcekli_cikti": 224, "kalan": 0, "relu_cikti": 224} or (qx, qw) != old:
            return False
        # Negatif toplam ve kalan testi
        if f([10], [-15], 0, 4) != {"ham_toplam": -150, "olcekli_cikti": -10, "kalan": 10, "relu_cikti": 0}:
            return False
        rng = random.Random(4747)
        for _ in range(25):
            d = rng.randint(1, 6); ru = rng.randint(1, 12)
            rqx = [rng.randint(-500, 500) for _ in range(d)]; rqw = [rng.randint(-500, 500) for _ in range(d)]
            rqb = rng.randint(-200, 200)
            if f(list(rqx), list(rqw), rqb, ru) != _r(rqx, rqw, rqb, ru): return False
        for bad in ((None, qw, 0, 8), (qx, None, 0, 8), ([], [], 0, 8), ([1], qw, 0, 8), ([1.0, 2, 3], qw, 0, 8), ([True, 2, 3], qw, 0, 8), (qx, qw, 1.5, 8), (qx, qw, True, 8), (qx, qw, 0, 0), (qx, qw, 0, 25), (qx, qw, 0, True)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
ok(sinama2(sabit_nokta_ic_carpim), "S² toplamı, tam sayı bölmesi, kalan kısıtı, ReLU ve geçersiz girdi")
for ad, mut in [
    ("bias ölçeklenmedi", lambda x, w, b, u: dict(sabit_nokta_ic_carpim(x, w, b, u), ham_toplam=sum(p * q for p, q in zip(x, w)) + b)),
    ("ReLU yok", lambda x, w, b, u: dict(sabit_nokta_ic_carpim(x, w, b, u), relu_cikti=sabit_nokta_ic_carpim(x, w, b, u)["olcekli_cikti"])),
    ("kalan sıfır", lambda x, w, b, u: dict(sabit_nokta_ic_carpim(x, w, b, u), kalan=0))
]:
    ok(not sinama2(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(sabit_nokta_ic_carpim, _il.import_module('ai_gercek_ai_guvence_47').referans_sabit_nokta_ic_carpim, ([128, 64, 192], [128, -64, 192], 32, 8), tohum=3345)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def sabit_nokta_ic_carpim(q_girdi, q_agirlik, q_bias, olcek_us):
    if not isinstance(q_girdi, list) or not isinstance(q_agirlik, list) or not q_girdi or len(q_girdi) != len(q_agirlik):
        raise ValueError("vektör")
    for v in q_girdi + q_agirlik + [q_bias, olcek_us]:
        if isinstance(v, bool) or not isinstance(v, int): raise ValueError("tam sayı")
    if not 1 <= olcek_us <= 24: raise ValueError("olcek_us")
    s = 1 << olcek_us
    ham = sum(x * w for x, w in zip(q_girdi, q_agirlik)) + q_bias * s
    olcekli = ham // s
    kalan = ham % s
    return {"ham_toplam": int(ham), "olcekli_cikti": int(olcekli), "kalan": int(kalan), "relu_cikti": int(max(0, olcekli))}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    v = json_yukle("veri/zkml.json")
    print(sabit_nokta_ic_carpim(v["q_girdi"], v["q_agirlik"], v["q_bias"], v["olcek_us"]))
```
```hint
`s = 1 << olcek_us` için `ham = sum(x * w for x, w in zip(q_girdi, q_agirlik)) + q_bias * s`, `olcekli = ham // s`, `kalan = ham % s` ve `relu_cikti = max(0, olcekli)` hesapla.
```
:::

::: anlat Ağırlık taahhüdü (commitment) ve devre kanıtı doğrulama
Doğrulayıcı (`verifier`), sunucunun gönderdiği çıkarım iddiasını iki aşamada denetler:
1. **Ağırlık taahhüdü (`commitment`):** `",".join(str(w) for w in q_agirlik) + "|" + str(q_bias) + "|" + str(olcek_us)` metninin UTF-8 `SHA-256` hex özeti (`gercek_ozet`) hesaplanır ve `beklenen_ozet` ile karşılaştırılır (`ozet_eslesti`).
2. **Devre hesabı:** `sabit_nokta_ic_carpim` çalıştırılarak `gercek_cikti = sonuc["relu_cikti"]` bulunur ve `iddia_edilen_cikti == gercek_cikti` kontrol edilir (`hesap_dogru`).
3. İkisi de doğruysa `gecerli = True`, aksi hâlde `False` döner.

**Görev 3'te sık tuzaklar:** Taahhüt dizgesinde boşluk bırakmak (ör. `", "` kullanmak) veya yalnız özeti kontrol edip çıktı eşitliğini atlamak.
:::

::: gorev 3 · Ağırlık taahhüdü ve çıkarım kanıtı doğrulama
`devre_kanit_dogrula(q_girdi, q_agirlik, q_bias, iddia_edilen_cikti, olcek_us, beklenen_ozet)`: Girdiler Görev 2 ile aynı kurallara tabidir; ayrıca `iddia_edilen_cikti` bool olmayan `int` ve `beklenen_ozet` boş olmayan `str` olmalı. `{"gecerli": bool, "ozet_eslesti": bool, "hesap_dogru": bool, "gercek_cikti": int, "gercek_ozet": str}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-47")
```
```starter
import hashlib, math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def devre_kanit_dogrula(q_girdi, q_agirlik, q_bias, iddia_edilen_cikti, olcek_us, beklenen_ozet):
    return {"gecerli": True, "ozet_eslesti": True, "hesap_dogru": True, "gercek_cikti": iddia_edilen_cikti, "gercek_ozet": beklenen_ozet}

from ai_guvence_veri import json_yukle
v = json_yukle("veri/zkml.json")
print("Doğru çıktı:", devre_kanit_dogrula(v["q_girdi"], v["q_agirlik"], v["q_bias"], v["dogru_cikti"], v["olcek_us"], v["beklenen_ozet"]))
print("Sahte çıktı:", devre_kanit_dogrula(v["q_girdi"], v["q_agirlik"], v["q_bias"], v["sahte_cikti"], v["olcek_us"], v["beklenen_ozet"]))
```
```test
def sinama3(f):
    import copy, hashlib
    try:
        qx = [128, 64, 192]; qw = [128, -64, 192]; qb = 32; u = 8
        oz = hashlib.sha256(b"128,-64,192|32|8").hexdigest()
        old = (list(qx), list(qw))
        r1 = f(qx, qw, qb, 224, u, oz)
        if r1 != {"gecerli": True, "ozet_eslesti": True, "hesap_dogru": True, "gercek_cikti": 224, "gercek_ozet": oz} or (qx, qw) != old:
            return False
        # Hileli çıktı
        r2 = f(qx, qw, qb, 225, u, oz)
        if r2["gecerli"] is not False or r2["ozet_eslesti"] is not True or r2["hesap_dogru"] is not False or r2["gercek_cikti"] != 224:
            return False
        # Hileli ağırlık / yanlış taahhüt
        r3 = f(qx, qw, qb, 224, u, "0" * 64)
        if r3["gecerli"] is not False or r3["ozet_eslesti"] is not False or r3["hesap_dogru"] is not True:
            return False
        for bad in ((None, qw, qb, 224, u, oz), ([], [], qb, 224, u, oz), (qx, qw, qb, True, u, oz), (qx, qw, qb, 224.0, u, oz), (qx, qw, qb, 224, u, ""), (qx, qw, qb, 224, u, "   "), (qx, qw, qb, 224, u, None), (qx, qw, qb, 224, 0, oz)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
ok(sinama3(devre_kanit_dogrula), "SHA-256 ağırlık taahhüdü, devre çıktısı doğrulaması ve geçersiz girdi")
for ad, mut in [
    ("hep geçerli", lambda x, w, b, c, u, o: dict(devre_kanit_dogrula(x, w, b, c, u, o), gecerli=True)),
    ("özet kontrolsüz", lambda x, w, b, c, u, o: dict(devre_kanit_dogrula(x, w, b, c, u, o), gecerli=devre_kanit_dogrula(x, w, b, c, u, o)["hesap_dogru"])),
    ("hesap kontrolsüz", lambda x, w, b, c, u, o: dict(devre_kanit_dogrula(x, w, b, c, u, o), gecerli=devre_kanit_dogrula(x, w, b, c, u, o)["ozet_eslesti"]))
]:
    ok(not sinama3(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(devre_kanit_dogrula, _il.import_module('ai_gercek_ai_guvence_47').referans_devre_dogrula, ([128, 64, 192], [128, -64, 192], 32, 224, 8, '30f9289012f1379277f62506d380358250666920c5c75d45fb29a1f168857d3c'), tohum=3157)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import hashlib, math
def devre_kanit_dogrula(q_girdi, q_agirlik, q_bias, iddia_edilen_cikti, olcek_us, beklenen_ozet):
    if not isinstance(q_girdi, list) or not isinstance(q_agirlik, list) or not q_girdi or len(q_girdi) != len(q_agirlik):
        raise ValueError("vektör")
    for v in q_girdi + q_agirlik + [q_bias, iddia_edilen_cikti, olcek_us]:
        if isinstance(v, bool) or not isinstance(v, int): raise ValueError("tam sayı")
    if not 1 <= olcek_us <= 24: raise ValueError("olcek_us")
    if not isinstance(beklenen_ozet, str) or not beklenen_ozet.strip(): raise ValueError("beklenen_ozet")
    s = 1 << olcek_us
    ham = sum(x * w for x, w in zip(q_girdi, q_agirlik)) + q_bias * s
    olcekli = ham // s
    relu_c = int(max(0, olcekli))
    metin = ",".join(str(w) for w in q_agirlik) + "|" + str(q_bias) + "|" + str(olcek_us)
    gercek_ozet = hashlib.sha256(metin.encode("utf-8")).hexdigest()
    ozet_ok = (gercek_ozet == beklenen_ozet)
    hesap_ok = (iddia_edilen_cikti == relu_c)
    return {
        "gecerli": bool(ozet_ok and hesap_ok),
        "ozet_eslesti": bool(ozet_ok),
        "hesap_dogru": bool(hesap_ok),
        "gercek_cikti": relu_c,
        "gercek_ozet": gercek_ozet
    }

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    v = json_yukle("veri/zkml.json")
    print("Doğru çıktı:", devre_kanit_dogrula(v["q_girdi"], v["q_agirlik"], v["q_bias"], v["dogru_cikti"], v["olcek_us"], v["beklenen_ozet"]))
    print("Sahte çıktı:", devre_kanit_dogrula(v["q_girdi"], v["q_agirlik"], v["q_bias"], v["sahte_cikti"], v["olcek_us"], v["beklenen_ozet"]))
```
```hint
`",".join(str(w) for w in q_agirlik) + "|" + str(q_bias) + "|" + str(olcek_us)` dizgesinin SHA-256 özetini al ve hem özetin hem de ReLU çıktısının eşleştiğini doğrula.
```
:::

::: anlat Hata vitrini · çalışmış yanlış rapor
Yazar, kusurlu başlangıç kodlarını görünür sentetik veriyle gerçekten çalıştırdı ve sonucu `outputs/yeni-ai-guvence-47/gorunur-run-1.json` dosyasına kaydetti. Kusurlu iç çarpım kodu `S = 256` bölmesini unuttuğu için `224` yerine `49184` döndürür; kusurlu doğrulama kodu ise sahte çıktı `250` için bile `gecerli=True` vererek hileli sunucuyu onaylar. Doğru kod `gercek_cikti=224` hesaplar ve `sahte_cikti=250` iddiasını `hesap_dogru=False, gecerli=False` ile reddeder.

Bu kaydedilmiş bir hesaplama çıktısıdır, model yanıtı değildir ve rapor sentetiktir. Yalnızca model ağırlık özetini (`ozet_eslesti=True`) kontrol edip devre hesabını doğrulamayan bir denetçinin nasıl kandırılabileceğini kendi cümlenle açıkla. Gerçek finaldeki ölçüm ayrıca üretilir; bu sayılar onun yerine konmaz.
:::

::: anlat Gerçek deney: MLP katmanının sabit nokta devresi ve taahhüt doğrulaması
Final, `load_digits` üzerinde eğitilen bir MLP'nin ilk katman nöronunu alır, ağırlıklarını $S = 2^{10} = 1024$ ölçeğinde **senin `sabit_nokta_nicemle` işlevinle** tam sayılara çevirir ve SHA-256 taahhüdünü oluşturur.

48 gerçek test görüntüsü üzerinde:
1. Girdiler nicemlenir ve **senin `sabit_nokta_ic_carpim` işlevinle** tam sayı ReLU çıktısı hesaplanır; `float32` PyTorch çıktısıyla arasındaki fark (`ort_devre_hatasi`) ölçülür.
2. **Senin `devre_kanit_dogrula` işlevin** hem dürüst çıkarımları hem de çıktısı veya ağırlığı 1 birim değiştirilmiş hileli iddiaları denetler.
3. **Ölçek taraması:** Ağın tamamı (iki katman, 10 logit) test kümesinin hepsinde tamsayı aritmetiğiyle çalıştırılır. Ölçek $2^2$'den $2^{12}$'ye kadar değiştirilir. Gizli katmandan sonra $s^2$ ölçeğindeki birikim $s$'ye bölünerek yeniden ölçeklenir; gerçek devrelerde de aynı işlem yapılır. Float modelle karar uyumu, ortalama logit hatası ve doğruluk ölçülür. zkML'de kanıt maliyeti, tamsayıların bit genişliğiyle (lookup tablolarının ve aralık kısıtlarının boyutuyla) büyür. Bu yüzden "kaç bit yeter?" gerçek bir mühendislik sorusudur.

Yazarın üç GPU koşusunda şu sonuçlar alındı:
- **Tek nöron devresi:** $2^{10}$ ölçekte ortalama ReLU hatası 0.0015–0.0018.
- **Kanıt doğrulama:** Dürüst kanıtlar 48/48 kabul edildi. Hileli çıktı ve sahte ağırlık iddiaları 48/48 reddedildi: ağırlığın tek bir tamsayısını değiştirmek SHA-256 taahhüdünü tümüyle değiştirir.
- **Ölçek taraması (float doğruluk 0.92–0.93):**

| Ölçek | Float ile karar uyumu | Ortalama logit hatası | Doğruluk |
|---|---|---|---|
| $2^2$ | 0.95–0.97 | 1.08–1.24 | 0.90–0.91 |
| $2^3$ | 0.97–0.98 | 0.64–0.74 | 0.91–0.92 |
| $2^4$ | 0.986–0.994 | 0.28–0.35 | 0.92–0.93 |
| $2^6$ | 0.996–1.000 | 0.06–0.08 | float ile aynı |
| $2^8$ ve üstü | 0.998–1.000 | ≤ 0.019 | float ile aynı |

Bu küçük ağ için 6–8 bitlik kesir yeterli. 4 bitin altında kararlar float modelden ayrılmaya başlar. Bu ayrılma önemlidir: doğrulayıcı "devre doğru hesapladı" der, ama devrenin hesapladığı model, sahibinin float modeli değildir.

**Ağırlıkları ifşa etmeden denetim: Merkle taahhüdü ve rastgele açma.** SNARK aracı olmadan ağırlıkların tamamını göstermeden ne kadar güvence alınabilir? Final, SmolLM2-135M'in gerçek `layers.0.mlp.gate_proj` matrisinin 1 536 satırının her biri için bu dersin taahhüt biçiminde bir SHA-256 yaprağı hesaplar ve bunların üstüne bir **Merkle ağacı** kurar. Sağlayıcı yalnız kökü (32 bayt) yayımlar. Bir istek için doğrulayıcı rastgele $k$ satır ister. Sağlayıcı yalnız o satırları ve Merkle yollarını açar, doğrulayıcı da her birini yolla köke bağlar ve senin `devre_kanit_dogrula` işlevinle sınar. Üç durum ölçülür:
- dürüst sağlayıcı 32 rastgele denetimin hepsini geçer;
- **ucuz model** (bütün satırlar 4 bitle hesaplanıyor) satırların yaklaşık yarısında farklı çıktı verir ve 8 satırlık denetimle (ağırlıkların %0.5'i) neredeyse kesin yakalanır;
- **tek satırlık arka kapı** ancak o satır denetlenirse yakalanır: olasılık tam olarak $k/1536$'dır, 128 satırda bile ~%8.

Rastgele denetim, modelin toptan değiştirilmesine karşı ucuz ve güçlüdür; hedefli küçük kurcalamalara karşı zayıftır. Bu ikincisi ve ağırlıkların hiç ifşa edilmemesi için SNARK gerekir. Devre ifadesi bu dersin ReLU nöronudur, SmolLM2'nin kendi SiLU'lu çıktısı değildir.

**Kanıt dosyasını oku:** Soru 1: `olcek_taramasi` içinde karar uyumu 1.0'a hangi ölçekte ulaşıyor? Bit sayısını iki katına çıkarmanın kanıt maliyetine etkisi ne olur? Soru 2: Ağırlığın tek bir koordinatını `+1` değiştirmek `taahhut_ozeti`'ni nasıl etkiledi? Soru 3: Bu düzende doğrulayıcı ağırlıkları (`q_w`) görüyor. Bir SNARK bunu nasıl değiştirir ve geriye neyi açık bırakır? Cevabını tezgâhta yorum olarak yaz; otomatik test bu serbest açıklamayı puanlamaz.
:::

::: gorev Gerçek deney · Gerçek MLP nöronunda sabit nokta devresi ve taahhüt doğrulaması
Önceki üç görevin `sabit_nokta_nicemle`, `sabit_nokta_ic_carpim` ve `devre_kanit_dogrula` işlevlerini birleştir. Çalıştır gerçek tabloyu gösterir; Kontrol Et önce üç sözleşmeyi gizli verilerle sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
ortam: gpu
timeout: 180
```
```starter
import ai_lab
import hashlib, math
def sabit_nokta_nicemle(degerler, olcek_us):
    q = [int(x * olcek_us) for x in degerler]
    return {"tam_sayilar": q, "geri_yuklenen": [float(v) for v in degerler], "max_hata": 0.0}
def sabit_nokta_ic_carpim(q_girdi, q_agirlik, q_bias, olcek_us):
    ham = sum(x * w for x, w in zip(q_girdi, q_agirlik)) + q_bias
    return {"ham_toplam": ham, "olcekli_cikti": ham, "kalan": 0, "relu_cikti": ham}
def devre_kanit_dogrula(q_girdi, q_agirlik, q_bias, iddia_edilen_cikti, olcek_us, beklenen_ozet):
    return {"gecerli": True, "ozet_eslesti": True, "hesap_dogru": True, "gercek_cikti": iddia_edilen_cikti, "gercek_ozet": beklenen_ozet}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_47 as D
    D.goster(sabit_nokta_nicemle, sabit_nokta_ic_carpim, devre_kanit_dogrula)
```
```test
import ai_lab, hashlib, math
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('referans_sabit_nokta_nicemle', 'referans_sabit_nokta_ic_carpim', 'referans_devre_dogrula', 'kanit_yaz', '_yakin'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
sabit_nokta_nicemle = need("sabit_nokta_nicemle")
sabit_nokta_ic_carpim = need("sabit_nokta_ic_carpim")
devre_kanit_dogrula = need("devre_kanit_dogrula")
def sinama1(f):
    import copy, math, random
    def _r(deg, u):
        s = 1 << u; q = [int(math.floor(x * s + 0.5)) for x in deg]; g = [float(v / s) for v in q]
        return {"tam_sayilar": q, "geri_yuklenen": g, "max_hata": float(max(abs(x - y) for x, y in zip(deg, g)))}
    def _y(a, b):
        if not isinstance(a, dict) or set(a) != set(b) or a["tam_sayilar"] != b["tam_sayilar"]: return False
        return all(abs(p - q) < 1e-12 for p, q in zip(a["geri_yuklenen"], b["geri_yuklenen"])) and abs(a["max_hata"] - b["max_hata"]) < 1e-12
    try:
        d = [0.5, -0.25, 0.125]; old = list(d)
        if not _y(f(d, 4), {"tam_sayilar": [8, -4, 2], "geri_yuklenen": [0.5, -0.25, 0.125], "max_hata": 0.0}) or d != old:
            return False
        if f([0.25], 1)["tam_sayilar"] != [1]: return False
        rng = random.Random(47)
        for _ in range(25):
            rd = [rng.uniform(-3, 3) for _ in range(rng.randint(1, 7))]; ru = rng.randint(1, 16)
            if not _y(f(list(rd), ru), _r(rd, ru)): return False
        for bad in ((None, 8), ([], 8), ([True], 8), (d, 0), (d, 25), (d, True)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama1(sabit_nokta_nicemle), "2^k ölçekleme, floor(x*S+0.5) yuvarlama, max hata ve geçersiz girdi")
for ad, mut in [
    ("max hata sıfır", lambda d, u: dict(sabit_nokta_nicemle(d, u), max_hata=0.0)),
    ("int kesme", lambda d, u: dict(sabit_nokta_nicemle(d, u), tam_sayilar=[int(x * (1 << u)) for x in d])),
    ("yanlış ölçek", lambda d, u: sabit_nokta_nicemle(d, max(1, u - 1)) if u > 1 else dict(sabit_nokta_nicemle(d, u), max_hata=1.0))
]:
    kontrol(not sinama1(mut), "mutant reddedildi: " + ad)
def sinama2(f):
    import copy, math, random
    def _r(qx, qw, qb, u):
        s = 1 << u; h = sum(x * w for x, w in zip(qx, qw)) + qb * s
        return {"ham_toplam": int(h), "olcekli_cikti": int(h // s), "kalan": int(h % s), "relu_cikti": int(max(0, h // s))}
    try:
        qx = [128, 64, 192]; qw = [128, -64, 192]; old = (list(qx), list(qw))
        if f(qx, qw, 32, 8) != {"ham_toplam": 57344, "olcekli_cikti": 224, "kalan": 0, "relu_cikti": 224} or (qx, qw) != old:
            return False
        if f([10], [-15], 0, 4) != {"ham_toplam": -150, "olcekli_cikti": -10, "kalan": 10, "relu_cikti": 0}:
            return False
        rng = random.Random(4747)
        for _ in range(25):
            d = rng.randint(1, 6); ru = rng.randint(1, 12)
            rqx = [rng.randint(-500, 500) for _ in range(d)]; rqw = [rng.randint(-500, 500) for _ in range(d)]
            rqb = rng.randint(-200, 200)
            if f(list(rqx), list(rqw), rqb, ru) != _r(rqx, rqw, rqb, ru): return False
        for bad in ((None, qw, 0, 8), ([], [], 0, 8), ([1.0, 2, 3], qw, 0, 8), ([True, 2, 3], qw, 0, 8), (qx, qw, True, 8), (qx, qw, 0, 0), (qx, qw, 0, 25)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama2(sabit_nokta_ic_carpim), "S² toplamı, tam sayı bölmesi, kalan kısıtı, ReLU ve geçersiz girdi")
for ad, mut in [
    ("bias ölçeklenmedi", lambda x, w, b, u: dict(sabit_nokta_ic_carpim(x, w, b, u), ham_toplam=sum(p * q for p, q in zip(x, w)) + b)),
    ("ReLU yok", lambda x, w, b, u: dict(sabit_nokta_ic_carpim(x, w, b, u), relu_cikti=sabit_nokta_ic_carpim(x, w, b, u)["olcekli_cikti"])),
    ("kalan sıfır", lambda x, w, b, u: dict(sabit_nokta_ic_carpim(x, w, b, u), kalan=0))
]:
    kontrol(not sinama2(mut), "mutant reddedildi: " + ad)
def sinama3(f):
    import copy, hashlib
    try:
        qx = [128, 64, 192]; qw = [128, -64, 192]; qb = 32; u = 8
        oz = hashlib.sha256(b"128,-64,192|32|8").hexdigest()
        old = (list(qx), list(qw))
        if f(qx, qw, qb, 224, u, oz)["gecerli"] is not True or (qx, qw) != old: return False
        if f(qx, qw, qb, 225, u, oz)["gecerli"] is not False: return False
        if f(qx, qw, qb, 224, u, "0" * 64)["gecerli"] is not False: return False
        for bad in ((None, qw, qb, 224, u, oz), ([], [], qb, 224, u, oz), (qx, qw, qb, True, u, oz), (qx, qw, qb, 224.0, u, oz), (qx, qw, qb, 224, u, ""), (qx, qw, qb, 224, u, "   "), (qx, qw, qb, 224, u, None)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama3(devre_kanit_dogrula), "SHA-256 ağırlık taahhüdü, devre çıktısı doğrulaması ve geçersiz girdi")
for ad, mut in [
    ("hep geçerli", lambda x, w, b, c, u, o: dict(devre_kanit_dogrula(x, w, b, c, u, o), gecerli=True)),
    ("özet kontrolsüz", lambda x, w, b, c, u, o: dict(devre_kanit_dogrula(x, w, b, c, u, o), gecerli=devre_kanit_dogrula(x, w, b, c, u, o)["hesap_dogru"])),
    ("hesap kontrolsüz", lambda x, w, b, c, u, o: dict(devre_kanit_dogrula(x, w, b, c, u, o), gecerli=devre_kanit_dogrula(x, w, b, c, u, o)["ozet_eslesti"]))
]:
    kontrol(not sinama3(mut), "mutant reddedildi: " + ad)
# farksal tarama (final)
import importlib as _il
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_R = _il.import_module('sandbox.ai_gercek_ai_guvence_47')
for _ad, _ref, _taban, _toh in (
    ('sabit_nokta_nicemle', 'referans_sabit_nokta_nicemle', ([0.5, -0.25, 0.75, 0.123], 8), 3665),
    ('sabit_nokta_ic_carpim', 'referans_sabit_nokta_ic_carpim', ([128, 64, 192], [128, -64, 192], 32, 8), 3867),
    ('devre_kanit_dogrula', 'referans_devre_dogrula', ([128, 64, 192], [128, -64, 192], 32, 224, 8, '30f9289012f1379277f62506d380358250666920c5c75d45fb29a1f168857d3c'), 3679),
):
    _t, _g = _ff(need(_ad), getattr(_R, _ref), _taban, tohum=_toh)
    kontrol(_t, "farksal tarama (" + _ad + "): bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
if not all(checks): stop()
from sandbox import ai_gercek_ai_guvence_47 as D
try: r = D.deney(sabit_nokta_nicemle, sabit_nokta_ic_carpim, devre_kanit_dogrula)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r["nicem_ayni"], "gerçek ağırlık ve girdilerde sabit nokta nicemleme bağımsız hesapla aynı")
kontrol(r["ic_ayni"], "gerçek girdilerde sabit nokta iç çarpım bağımsız hesapla aynı")
kontrol(r["dogrula_ayni"], "gerçek devre kanıtlarında doğrulama bağımsız hesapla aynı")
kontrol(r["durust_gecerli_sayisi"] == r["ayarlar"]["ornek"], "tüm dürüst çıkarım kanıtları doğrulandı")
kontrol(r["sahte_red_sayisi"] == r["ayarlar"]["ornek"], "tüm hileli çıktı ve sahte ağırlık kanıtları reddedildi")
kontrol(r["ort_devre_hatasi"] < 0.05, "sabit nokta devresi float32 ReLU çıktısını yüksek hassasiyetle takip etti")
kontrol(r["denetim_calisiyor"], "SmolLM2 ağırlıklarının Merkle taahhüdü: dürüst sağlayıcı denetimi geçti, ucuz model birkaç satırla yakalandı, tek satır kurcalama ancak k/n olasılıkla yakalandı")
t = r["olcek_taramasi"]
kontrol(t["2^10"]["karar_uyumu"] >= 0.99 and t["2^2"]["ort_logit_hatasi"] > t["2^10"]["ort_logit_hatasi"] * 10, "tam ağ tamsayı devresi 2^10'da float kararlarıyla uyuştu (%.3f), düşük ölçekte hata büyüdü (2^2: %.3f)" % (t["2^10"]["karar_uyumu"], t["2^2"]["ort_logit_hatasi"]))
ai_lab.kanit_yaz("ai-guvence-47-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-guvence-47", "deney": r})
```
```solution
import ai_lab
import hashlib, math
def sabit_nokta_nicemle(degerler, olcek_us):
    if not isinstance(degerler, list) or not degerler: raise ValueError("degerler")
    for x in degerler:
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x): raise ValueError("sayı")
    if isinstance(olcek_us, bool) or not isinstance(olcek_us, int) or not 1 <= olcek_us <= 24:
        raise ValueError("olcek_us")
    s = 1 << olcek_us
    q = [int(math.floor(x * s + 0.5)) for x in degerler]
    geri = [float(v / s) for v in q]
    hata = max(abs(x - g) for x, g in zip(degerler, geri))
    return {"tam_sayilar": q, "geri_yuklenen": geri, "max_hata": float(hata)}
def sabit_nokta_ic_carpim(q_girdi, q_agirlik, q_bias, olcek_us):
    if not isinstance(q_girdi, list) or not isinstance(q_agirlik, list) or not q_girdi or len(q_girdi) != len(q_agirlik):
        raise ValueError("vektör")
    for v in q_girdi + q_agirlik + [q_bias, olcek_us]:
        if isinstance(v, bool) or not isinstance(v, int): raise ValueError("tam sayı")
    if not 1 <= olcek_us <= 24: raise ValueError("olcek_us")
    s = 1 << olcek_us
    ham = sum(x * w for x, w in zip(q_girdi, q_agirlik)) + q_bias * s
    olcekli = ham // s
    kalan = ham % s
    return {"ham_toplam": int(ham), "olcekli_cikti": int(olcekli), "kalan": int(kalan), "relu_cikti": int(max(0, olcekli))}
def devre_kanit_dogrula(q_girdi, q_agirlik, q_bias, iddia_edilen_cikti, olcek_us, beklenen_ozet):
    if not isinstance(iddia_edilen_cikti, int) or isinstance(iddia_edilen_cikti, bool): raise ValueError("iddia")
    if not isinstance(beklenen_ozet, str) or not beklenen_ozet.strip(): raise ValueError("beklenen_ozet")
    ic = sabit_nokta_ic_carpim(q_girdi, q_agirlik, q_bias, olcek_us)
    metin = ",".join(str(w) for w in q_agirlik) + "|" + str(q_bias) + "|" + str(olcek_us)
    gercek_ozet = hashlib.sha256(metin.encode("utf-8")).hexdigest()
    ozet_ok = (gercek_ozet == beklenen_ozet)
    hesap_ok = (iddia_edilen_cikti == ic["relu_cikti"])
    return {
        "gecerli": bool(ozet_ok and hesap_ok),
        "ozet_eslesti": bool(ozet_ok),
        "hesap_dogru": bool(hesap_ok),
        "gercek_cikti": ic["relu_cikti"],
        "gercek_ozet": gercek_ozet
    }
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_47 as D
    D.goster(sabit_nokta_nicemle, sabit_nokta_ic_carpim, devre_kanit_dogrula)
```
```hint
Üç işlevi aynen birleştir. Sabit nokta devresinin float32 ReLU çıktısına ne kadar yaklaştığını ve hileli kanıtların nasıl reddedildiğini incele.
```
:::

::: anlat Sınır
Bu ders `zkML` sistemlerinin temelini oluşturan `fixed-point arithmetic` yeniden ölçekleme kısıtlarını, ağırlık `commitment` doğrulamasını ve ölçek/hassasiyet ödünleşimini gösterir. Burada doğrulayıcı ağırlıkları ve girdiyi görür; yani bu bir sıfır-bilgi kanıtı değil, yeniden hesaplamayla doğrulamadır. Tam bir sıfır-bilgi kanıtı (`zk-SNARK`) için bu aritmetik kısıtların sonlu cisim üzerinde polinom taahhütleriyle sarılması gerekir (ör. Halo2, EZKL). Kanıt üretim süresi ve devre boyutu ölçülmez. Ağ 8×8 rakamlarla eğitilen küçük bir MLP'dir.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Neden kayan nokta yerine sabit nokta devresi? (30 sn).** "Kriptografik kanıt devreleri sonlu cisim tam sayıları üzerinde çalışır; kayan noktalı ağırlık ve girdiler $S=2^k$ ölçeğiyle tam sayıya nicemlenir, çarpım sonrası $S^2$ ölçeği tam bölme ve kalan kısıtıyla (`ham = olcekli * S + kalan`) doğrulanır."
2. **Hesap doğruluğu tek başına yetmez: ağırlık taahhüdü (35 sn).** "Hileli bir sağlayıcı ucuz bir model çalıştırıp onun için geçerli aritmetik kanıt üretebilir; çıktının gerçekten ilan edilen modelden geldiğini bağlamak için ağırlıkların kriptografik özeti (`SHA-256` / `Merkle` taahhüdü) kanıta kilitlenir."
3. **Ölçek–hassasiyet ödünleşimi (30 sn).** "Küçük ölçek ($2^2$) yuvarlama hatasını büyütüp karar uyumunu bozarken, yeterli ölçek ($2^{10}$) tam sayı devresini `float32` kararlarıyla neredeyse bire bir hizalar."
4. **Soru (25 sn).** "Rastgele $k$ ağırlık satırını Merkle kanıtıyla denetlemek ucuz model ikamesini hemen yakalarken, tek satırlık hedefli bir arka kapı kurcalamasını neden kaçırabilir?"
:::
