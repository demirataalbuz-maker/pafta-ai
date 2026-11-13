---
id: ai-saldiri-62
title: Donanım Bit-Flip Saldırısı (Rowhammer / BFA) · Üstel Bit Çevrimi ve Ağırlık Bütünlüğü
summary: Float32/BFloat16 ağırlıklarda tek bir üstel bit çevriminin (bit-flip) ürettiği çarpan patlamasını hesapla; gradyan duyarlılığıyla en kırılgan ağırlıkları seç ve bütünlük sınır denetimiyle bozulan ağırlığı GPU'da onar.
esleme: ai-saldiri-51, ai-guvence-23, ai-savunma-33
timeout: 60
---

::: anlat Milyonlarca parametre içinde tek bir bit tüm modeli nasıl çökertir?
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Paylaşımlı DRAM/VRAM üzerinde `Rowhammer` veya donanım hata enjeksiyonu (`Bit-Flip Attack` - BFA) bir ağırlığın üstel (`exponent`) bitini $0 \to 1$ çevirdiğinde ağırlık $2^{2^b}$ kat büyür ve tek bir çarpma tüm ağın aktivasyonlarını doyurur (Rakin vd. 2019, Hong vd. 2019) | İlk üç görev: `veri/bitflip.json` içindeki **sentetik** ağırlık ve gradyanlar. Final: kurulu SmolLM2-135M ağırlıklarında yazılımla exponent bitini çevirip gerçek model kaybı ve onarımını ölçme | Fiziksel DRAM satır komşuluğunu ve ECC donanım düzeltme kodlarının yan kanallarını yazılım simülasyonuyla göstermez |
| Üstel aralık denetimi (`weight clipping / radical weight zeroing`) anormal büyüyen ağırlığı $0.0$'a çekerek felaket etkisini sönümler | IEEE-754 yanlı üstel (`biased exponent`) XOR çevrimi, gradyan×ağırlık duyarlılığı ve mutlak sınır onarımı | Küçük işaret (`sign`) veya mantissa bit çevrimleriyle yapılan gizli arka kapıları (`Trojan BFA`) yalnız mutlak sınırla yakalayamaz |

> [!NOT]
> Görevler `veri/bitflip.json` dosyasını okur; dosya sentetiktir. Setup her Çalıştır/Kontrol Et adımında geçici kopya kurar; değişiklikler taşınmaz, **kalıcılık yoktur**. Ekranda ayrı dosya görüntüleyici yoktur; içeriği görmek için `print` kullan. Gizli testler ayrıdır. Final yeni model indirmez ve GPU varsa onu kullanır.

IEEE-754 `float32` ve `bfloat16` sayıları 1 işaret biti, **8 üstel (`exponent`) biti** ($b \in \{0, \dots, 7\}$, yanlılık `bias = 127`) ve kesir (`mantissa`) bitlerinden oluşur. Bu formülün normal, sonlu sayı aralığında sıfırdan farklı bir $x$ sayısı `m, e = math.frexp(abs(x))` ile $|x| = m \cdot 2^e$ ($0.5 \le m < 1$) biçiminde yazıldığında, IEEE-754 yanlı üstel değeri:
$$E_{\text{eski}} = (e - 1) + 127 = e + 126$$
olur.

**Bit-Flip Etkisi:** Saldırgan `Rowhammer` ile $b$'inci üstel bitini ters çevirdiğinde (`XOR`):
$$E_{\text{yeni}} = E_{\text{eski}} \oplus 2^b$$
Eğer $b$'inci bit başlangıçta $0$ idiyse, üstel $2^b$ artar ve ağırlık yeni exponent da normal ve sonlu aralıkta kaldığında $2^{2^b}$ katına çıkar; reserved exponent veya subnormal geçişleri bu formülle yorumlanmaz. Örneğin $b = 5$ biti $0 \to 1$ olduğunda ağırlık $2^{32} \approx 4.29 \times 10^9$ ile çarpılır; tek bir nöron tüm katmanı domine eder ("Terminal Brain Damage", Hong vd. 2019).

**Saldırgan ne dener?** Progressive Bit Search (Rakin vd. 2019) yaklaşımıyla kayıp fonksiyonunun ağırlıklara göre gradyanını ($\nabla_w \mathcal{L}$) hesaplar; $|\nabla_{w_i} \mathcal{L}| \cdot \max(|w_i|, 10^{-6})$ duyarlılığı en yüksek olan ilk $k$ ağırlığı hedef alır.

**Savunma neden kırılır?** Standart model dosyası (`safetensors`) diskte sağlam olsa bile saldırı çalışma anında (`runtime`) RAM/VRAM üzerinde gerçekleşir. Çalışma anında ağırlıkların maksimum mutlak değerini (`max_mutlak_sinir`) veya blok sağlama toplamlarını denetleyip sınırı aşan ağırlığı `0.0` yapmak (`weight zeroing`), tek bir patlayan ağırlığın tüm ağı kör etmesini engeller.

**Görev 1'de sık tuzaklar:** Bit çevrimini `+ (1 << b)` ile toplama olarak yazmak, bit zaten `1` olduğunda biti sıfırlamak yerine taşma yapar; doğru işlem bit düzeyinde `^ (1 << b)` (`XOR`) işlemidir.

Kaynaklar: [Rakin vd. 2019 - Bit-Flip Attack: Crushing Neural Network with Progressive Bit Search](https://arxiv.org/abs/1903.12269), [Hong vd. 2019 - Terminal Brain Damage: Exposing the Graceless Degradation in Deep Neural Networks](https://arxiv.org/abs/1906.01017), [Yao vd. 2020 - DeepHammer: Targeted Chain of Bit Flips](https://arxiv.org/abs/2003.13746). Bu dersteki bütün sayılar yalnız yerel kanıttan gelir.

Köprü: ai-guvence-23 model nicelemesini (`quantization`) inceler; bu ders kayan noktalı ağırlıkların üstel bitlerine yönelik donanım `bit-flip` saldırısını ve çalışma anı onarımını modeller.
:::

::: tahmin XOR ile üstel bit çevrimi: büyüme mi küçülme mi?
Çıktıyı tahmin et, sonra Çalıştır ile karşılaştır.
```python
import math
for b in (4, 5):
    m, e = math.frexp(0.25)
    eski_u = e + 126
    yeni_u = eski_u ^ (1 << b)
    yeni_d = m * (2.0 ** (yeni_u - 126))
    print(f"bit={b}: eski_u={eski_u} yeni_u={yeni_u} çarpan={yeni_d / 0.25}")
```
???
```cikti
bit=4: eski_u=125 yeni_u=109 çarpan=1.52587890625e-05
bit=5: eski_u=125 yeni_u=93 çarpan=2.3283064365386963e-10
```
Tahmininle gerçek çıktı arasındaki farkı tezgâhta yorum satırı olarak yaz: `0.25` sayısının yanlı üsteli `125` (`01111101` ikili) olduğu için 4. ve 5. bitleri zaten `1`'dir (`125 ^ 16 = 109`); peki hangi bit indisi (`0..7`) `125` sayısında `0`'dır ve çevrilince sayıyı büyütür? Sonra üç kusurlu başlangıç kodunu çalıştır ve her birinin neyi kaçırdığını önce kendin teşhis et; açıklama çözümün ardından gelir.
:::

::: gorev 1 · Üstel bit çevir etkisi
`ustel_bit_cevir_etkisi(deger, ustel_bit_indisi)`: `deger` sıfırdan farklı, `abs(deger) < 100.0` olan bool olmayan sonlu sayı; `ustel_bit_indisi` bool olmayan `int` ve `0 <= ustel_bit_indisi <= 7`. `m, e = math.frexp(abs(deger))` ile `eski_ustel = e + 126` hesapla; `yeni_ustel = eski_ustel ^ (1 << ustel_bit_indisi)` ile yeni değeri (`deger` ile aynı işaretli) ve `buyume_carpani = abs(yeni_deger / deger)` değerini bul. `{"eski_ustel": int, "yeni_ustel": int, "yeni_deger": float, "buyume_carpani": float}` döndür. Geçersiz girdide `ValueError`.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-62")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def ustel_bit_cevir_etkisi(deger, ustel_bit_indisi):
    m, e = math.frexp(abs(deger))
    eu = e + 126
    yu = eu + ustel_bit_indisi
    yd = m * (2.0 ** (yu - 126))
    return {"eski_ustel": eu, "yeni_ustel": yu, "yeni_deger": yd, "buyume_carpani": abs(yd / deger)}

from ai_saldiri_veri import json_yukle
v = json_yukle("veri/bitflip.json")
print(ustel_bit_cevir_etkisi(v["ornek_agirlik"], v["ustel_bit_indisi"]))
```
```test
def sinama1(f):
    import math
    def _y(a, b):
        return isinstance(a, dict) and set(a) == set(b) and a["eski_ustel"] == b["eski_ustel"] and a["yeni_ustel"] == b["yeni_ustel"] and abs(a["yeni_deger"] - b["yeni_deger"]) <= 1e-12 * max(1.0, abs(b["yeni_deger"])) and abs(a["buyume_carpani"] - b["buyume_carpani"]) <= 1e-12 * max(1.0, abs(b["buyume_carpani"]))
    try:
        if not _y(f(0.25, 1), {"eski_ustel": 125, "yeni_ustel": 127, "yeni_deger": 1.0, "buyume_carpani": 4.0}):
            return False
        if not _y(f(-0.25, 1), {"eski_ustel": 125, "yeni_ustel": 127, "yeni_deger": -1.0, "buyume_carpani": 4.0}):
            return False
        if not _y(f(0.25, 4), {"eski_ustel": 125, "yeni_ustel": 109, "yeni_deger": 0.25 / 65536.0, "buyume_carpani": 1.0 / 65536.0}):
            return False
        if not _y(f(64.0, 0), {"eski_ustel": 133, "yeni_ustel": 132, "yeni_deger": 32.0, "buyume_carpani": 0.5}):
            return False
        for bad in ((0.0, 1), (100.0, 1), (-150.0, 1), (True, 1), (float("nan"), 1), (0.5, -1), (0.5, 8), (0.5, True), (0.5, 1.0)):
            try:
                f(*bad); return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sinama1(ustel_bit_cevir_etkisi), "XOR üstel bit çevrimi, işaret koruma ve geçersiz girdi")
for ad, mut in [("işaret kayboldu", lambda d, b: dict(ustel_bit_cevir_etkisi(d, b), yeni_deger=abs(ustel_bit_cevir_etkisi(d, b)["yeni_deger"]))), ("XOR yerine toplama", lambda d, b: dict(ustel_bit_cevir_etkisi(d, b), yeni_ustel=ustel_bit_cevir_etkisi(d, b)["eski_ustel"] + (1 << b))), ("çarpan hep 2", lambda d, b: dict(ustel_bit_cevir_etkisi(d, b), buyume_carpani=2.0))]:
    ok(not sinama1(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(ustel_bit_cevir_etkisi, _il.import_module('ai_gercek_ai_saldiri_62').referans_bit_cevir, (0.25, 4), tohum=3487)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def ustel_bit_cevir_etkisi(deger, ustel_bit_indisi):
    if isinstance(deger, bool) or not isinstance(deger, (int, float)) or not math.isfinite(deger) or deger == 0 or abs(deger) >= 100.0:
        raise ValueError("deger")
    if isinstance(ustel_bit_indisi, bool) or not isinstance(ustel_bit_indisi, int) or not 0 <= ustel_bit_indisi <= 7:
        raise ValueError("indis")
    m, e = math.frexp(abs(deger))
    eu = e + 126
    yu = eu ^ (1 << ustel_bit_indisi)
    yd = math.copysign(m * (2.0 ** (yu - 126)), deger)
    return {"eski_ustel": eu, "yeni_ustel": yu, "yeni_deger": yd, "buyume_carpani": abs(yd / deger)}

from ai_saldiri_veri import json_yukle
v = json_yukle("veri/bitflip.json")
print(ustel_bit_cevir_etkisi(v["ornek_agirlik"], v["ustel_bit_indisi"]))
```
```hint
`yeni_ustel = eski_ustel ^ (1 << ustel_bit_indisi)` kullan ve `math.copysign` ile `deger` işaretini koru.
```
:::

::: anlat Hassas ağırlıklar nasıl sıralanır?
Bir ağırlığın üstel bit çevrimine karşı duyarlılığı, hem kayıp gradyanının büyüklüğüne hem de ağırlığın mevcut ölçeğine bağlıdır:
$$\text{duyarlılık}_i = |\nabla_{w_i} \mathcal{L}| \cdot \max(|w_i|, 10^{-6})$$
Saldırgan bu duyarlılığı en yüksek olan ilk `k` indisi (eşitlikte küçük indis önce) seçer.

**Görev 2'de sık tuzaklar:** İşaretli çarpım (`g * w`) kullanmak negatif gradyanlı veya negatif ağırlıklı çok hassas parametreleri listenin sonuna iter; mutlak değerler çarpılmalıdır.
:::

::: gorev 2 · Gradyan duyarlılığıyla hassas ağırlık seçimi
`hassas_agirlik_sec(agirliklar, gradyanlar, k)`: `agirliklar` ve `gradyanlar` eşit uzunlukta boş olmayan listeler (bool olmayan sonlu sayılar); `k` bool olmayan `int` ve `1 <= k <= len(agirliklar)`. Her indis için `duyarlilik = abs(gradyanlar[i]) * max(abs(agirliklar[i]), 1e-6)` hesapla; azalan duyarlılığa göre (eşitlikte küçük indis önce) ilk `k` elemanı `[{"indis": i, "duyarlilik": float}, ...]` olarak döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-62")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def hassas_agirlik_sec(agirliklar, gradyanlar, k):
    s = sorted(range(len(agirliklar)), key=lambda i: agirliklar[i] * gradyanlar[i], reverse=True)[:k]
    return [{"indis": i, "duyarlilik": agirliklar[i] * gradyanlar[i]} for i in s]

from ai_saldiri_veri import json_yukle
v = json_yukle("veri/bitflip.json")
print(hassas_agirlik_sec(v["agirliklar"], v["gradyanlar"], v["k"]))
```
```test
def sinama2(f):
    import copy
    try:
        w = [0.5, -0.5, 0.25]; g = [1.0, -2.0, 2.0]; old = (list(w), list(g))
        r = f(w, g, 2)
        if (w, g) != old or r != [{"indis": 1, "duyarlilik": 1.0}, {"indis": 0, "duyarlilik": 0.5}]:
            return False
        if f([0.0, 0.5], [10.0, 1.0], 1) != [{"indis": 1, "duyarlilik": 0.5}]:
            return False
        if f([0.0, 1e-6], [1.5, 1.0], 1) != [{"indis": 0, "duyarlilik": 1.5e-6}]:
            return False
        for bad in ((None, [1.0], 1), ([], [], 1), ([1.0], [1.0, 2.0], 1), ([True], [1.0], 1), ([1.0], [1.0], 0), ([1.0], [1.0], 2), ([1.0], [1.0], True)):
            try:
                f(*bad); return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sinama2(hassas_agirlik_sec), "mutlak duyarlılık sıralaması, eşitlik kuralı ve geçersiz girdi")
for ad, mut in [("mutlak değer yok", lambda w, g, k: [{"indis": i, "duyarlilik": w[i]*g[i]} for i in range(k)]), ("artan sıra", lambda w, g, k: list(reversed(hassas_agirlik_sec(w, g, len(w))))[:k]), ("yalnız gradyan", lambda w, g, k: [{"indis": i, "duyarlilik": abs(g[i])} for i in sorted(range(len(g)), key=lambda j: -abs(g[j]))[:k]])]:
    ok(not sinama2(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(hassas_agirlik_sec, _il.import_module('ai_gercek_ai_saldiri_62').referans_hassas_sec, ([0.125, -0.5, 0.25, 0.0625, -0.25], [0.4, -2.5, 1.8, 0.1, -3.0], 2), tohum=3027)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def hassas_agirlik_sec(agirliklar, gradyanlar, k):
    if not isinstance(agirliklar, list) or not isinstance(gradyanlar, list) or not agirliklar or len(agirliklar) != len(gradyanlar):
        raise ValueError("liste")
    for v in agirliklar + gradyanlar:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError("sayı")
    if isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= len(agirliklar):
        raise ValueError("k")
    skor = [(abs(g) * max(abs(w), 1e-6), i) for i, (w, g) in enumerate(zip(agirliklar, gradyanlar))]
    skor.sort(key=lambda x: (-x[0], x[1]))
    return [{"indis": i, "duyarlilik": d} for d, i in skor[:k]]

from ai_saldiri_veri import json_yukle
v = json_yukle("veri/bitflip.json")
print(hassas_agirlik_sec(v["agirliklar"], v["gradyanlar"], v["k"]))
```
```hint
Her indis için `abs(g) * max(abs(w), 1e-6)` hesapla ve `(-duyarlilik, indis)` anahtarıyla sırala.
```
:::

::: anlat Ağırlık bütünlük kontrolü ve sıfırlama onarımı
Çalışma anı koruyucusu `eski_agirliklar` referansı (veya beklenen `max_mutlak_sinir` eşiği) ile `yeni_agirliklar` dizisini karşılaştırır:
- `degisen_indisler`: `eski_agirliklar[i] != yeni_agirliklar[i]` olan indisler (artan sırada).
- `sinir_asan_indisler`: `abs(yeni_agirliklar[i]) > max_mutlak_sinir` olan indisler (artan sırada).
- `saldiri_tespit = len(sinir_asan_indisler) > 0`.
- `onarilmis_agirliklar`: Sınırı aşan (`abs(v) > max_mutlak_sinir`) ağırlıkların `0.0` ile değiştirildiği, diğerlerinin korunduğu yeni liste.

**Görev 3'te sık tuzaklar:** Sınırı aşan ağırlığı eski ağırlıkla değil, yedek ağırlık tablosu tutulmayan hafif savunma moduna uygun olarak `0.0` ile sıfırlamalısın (`radical weight zeroing`).
:::

::: gorev 3 · Ağırlık bütünlük kontrolü ve üstel patlama onarımı
`agirlik_butunluk_kontrolu(eski_agirliklar, yeni_agirliklar, max_mutlak_sinir)`: `eski_agirliklar` ve `yeni_agirliklar` eşit uzunlukta boş olmayan listeler (bool olmayan sonlu sayılar); `max_mutlak_sinir > 0` bool olmayan sonlu sayı. `{"degisen_indisler": [...], "sinir_asan_indisler": [...], "saldiri_tespit": bool, "onarilmis_agirliklar": [...]}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-62")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def agirlik_butunluk_kontrolu(eski_agirliklar, yeni_agirliklar, max_mutlak_sinir):
    deg = [i for i, (a, b) in enumerate(zip(eski_agirliklar, yeni_agirliklar)) if a != b]
    return {"degisen_indisler": deg, "sinir_asan_indisler": [], "saldiri_tespit": False, "onarilmis_agirliklar": list(yeni_agirliklar)}

from ai_saldiri_veri import json_yukle
v = json_yukle("veri/bitflip.json")
print(agirlik_butunluk_kontrolu(v["agirliklar"], v["yeni_agirliklar"], v["max_mutlak_sinir"]))
```
```test
def sinama3(f):
    import copy
    try:
        e = [0.5, -0.25, 0.125]; y = [0.5, -50.0, 0.25]; old = (list(e), list(y))
        r = f(e, y, 10.0)
        if (e, y) != old or r != {"degisen_indisler": [1, 2], "sinir_asan_indisler": [1], "saldiri_tespit": True, "onarilmis_agirliklar": [0.5, 0.0, 0.25]}:
            return False
        if f(e, e, 10.0) != {"degisen_indisler": [], "sinir_asan_indisler": [], "saldiri_tespit": False, "onarilmis_agirliklar": [0.5, -0.25, 0.125]}:
            return False
        for bad in ((None, y, 10.0), ([], [], 10.0), ([1.0], [1.0, 2.0], 10.0), ([True], [1.0], 10.0), (e, y, 0.0), (e, y, -5.0), (e, y, True), (e, y, float("nan"))):
            try:
                f(*bad); return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sinama3(agirlik_butunluk_kontrolu), "değişen indisler, sınır aşımı, sıfırlama onarımı ve geçersiz girdi")
for ad, mut in [("onarımda sıfırlama yok", lambda e, y, s: dict(agirlik_butunluk_kontrolu(e, y, s), onarilmis_agirliklar=list(y))), ("saldiri_tespit hep False", lambda e, y, s: dict(agirlik_butunluk_kontrolu(e, y, s), saldiri_tespit=False)), ("mutlak değer unutuldu", lambda e, y, s: dict(agirlik_butunluk_kontrolu(e, y, s), sinir_asan_indisler=[i for i, v in enumerate(y) if v > s]))]:
    ok(not sinama3(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(agirlik_butunluk_kontrolu, _il.import_module('ai_gercek_ai_saldiri_62').referans_butunluk, ([0.125, -0.5, 0.25, 0.0625, -0.25], [0.125, -0.5, 16384.0, 0.0625, -0.25], 10.0), tohum=3853)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def agirlik_butunluk_kontrolu(eski_agirliklar, yeni_agirliklar, max_mutlak_sinir):
    if not isinstance(eski_agirliklar, list) or not isinstance(yeni_agirliklar, list) or not eski_agirliklar or len(eski_agirliklar) != len(yeni_agirliklar):
        raise ValueError("liste")
    for v in eski_agirliklar + yeni_agirliklar:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError("sayı")
    if isinstance(max_mutlak_sinir, bool) or not isinstance(max_mutlak_sinir, (int, float)) or not math.isfinite(max_mutlak_sinir) or max_mutlak_sinir <= 0:
        raise ValueError("sınır")
    deg = [i for i, (a, b) in enumerate(zip(eski_agirliklar, yeni_agirliklar)) if a != b]
    asan = [i for i, b in enumerate(yeni_agirliklar) if abs(b) > max_mutlak_sinir]
    onar = [0.0 if abs(b) > max_mutlak_sinir else float(b) for b in yeni_agirliklar]
    return {"degisen_indisler": deg, "sinir_asan_indisler": asan, "saldiri_tespit": len(asan) > 0, "onarilmis_agirliklar": onar}

from ai_saldiri_veri import json_yukle
v = json_yukle("veri/bitflip.json")
print(agirlik_butunluk_kontrolu(v["agirliklar"], v["yeni_agirliklar"], v["max_mutlak_sinir"]))
```
```hint
`abs(b) > max_mutlak_sinir` olan indisleri `sinir_asan_indisler` listesine ekle ve `onarilmis_agirliklar` içinde bu elemanları `0.0` yap.
```
:::

::: anlat Hata vitrini · çalışmış yanlış rapor
Yazar, kusurlu başlangıç kodlarını görünür sentetik veriyle çalıştırdı ve sonucu `outputs/yeni-ai-saldiri-62/gorunur-run-1.json` dosyasına kaydetti. Kusurlu kod üstel biti `XOR` ile çevirmek yerine topladığı için `0.25` sayısının 4. bit çevriminde `109` yerine `129` bulur; ayrıca bütünlük kontrolünde `16384.0` değerini olduğu gibi bırakır. Doğru kod ise sınırı aşan 2. indisi yakalayıp `0.0` ile sıfırlar.

Bu kaydedilmiş bir hesaplama çıktısıdır, canlı model yanıtı değildir ve rapor sentetiktir. Bozuk bir ağırlığı tam değerini bilmeden yalnızca `0.0` yapmak (dropout gibi) neden onu `16384.0` olarak bırakmaktan çok daha güvenlidir? Kendi cümlenle açıkla.
:::

::: anlat Gerçek deney: SmolLM2'de tek ağırlığın tek biti
Final, yerel önbellekteki gerçek **SmolLM2-135M** modelini (float32, indirme yok) yükler. 0. katmanın `mlp.down_proj` ağırlığından 4.096 elemanlık bir dilim alır ve gerçek bir İngilizce paragraftaki dil modeli kaybının bu ağırlıklara göre gradyanını hesaplar. Senin `hassas_agirlik_sec` işlevin en duyarlı ağırlığı seçer, `ustel_bit_cevir_etkisi` o ağırlığın üstel alanındaki **en yüksek biti (bit 7)** çevirir; büyüme çarpanı yaklaşık $2^{128}$ olur. Aynı paragrafta perplexity temiz, bozuk ve onarılmış hâlde ölçülür.

Karşılaştırma için deney, aynı ağırlıkta bit 0-6 içindeki en çok büyüten çevirmeyi de ölçer. Gerçek modellerde ağırlıkların çoğu $|w| < 1$ olduğundan üstel alan `0111xxxx` biçimindedir: alt bitlerin büyük kısmı zaten 1'dir ve çevrilebilen sıfır bitler yalnız 2-16 katlık büyüme verir. Perplexity bu yüzden neredeyse değişmez. Bit-flip saldırılarının (Rakin vd. 2019, DeepHammer) üstel alanın en yüksek bitini hedeflemesinin nedeni budur. Bütünlük denetiminin sınırı temiz dilimdeki en büyük mutlak ağırlığın 2 katıdır; senin `agirlik_butunluk_kontrolu` işlevin sınırı aşan ağırlığı bulup `0.0` yapar.

Kabul: üç işlevin bağımsız referansla aynı sonucu vermesi, bit 7 çevriminin perplexity'yi en az 10 kat bozması, sınır denetiminin tam olarak bozulan ağırlığı yakalaması ve onarım sonrası perplexity'nin temiz değerin %5 yakınına dönmesi.

**Kanıt dosyasını oku:** `temiz_ppl`, `bozuk_ppl`, `onarilmis_ppl` ve `kucuk_bit_karsilastirma` alanlarını karşılaştır. Soru 1: 2,3 milyonluk bir matristen (`down_proj`) tek bir ağırlığın tek biti neden bütün paragrafın perplexity'sini çökertebiliyor (RMSNorm ve artık bağlantıları düşün)? Soru 2: Bit 0-6 çevirmesi neden neredeyse etkisiz kaldı? Soru 3: Ağırlıklar bf16 ya da Int8 olsaydı en yüksek üstel bitin etkisi nasıl değişirdi; sıfırlama yerine ağırlığın temiz kopyadan geri yüklenmesi (`geri_yuklenen_ppl`) neden daha iyidir?
:::

::: gorev Gerçek deney · GPU ağırlıklarında bit-flip saldırısı ve bütünlük onarımı
Önceki üç görevin `ustel_bit_cevir_etkisi`, `hassas_agirlik_sec` ve `agirlik_butunluk_kontrolu` işlevlerini birleştir. Çalıştır gerçek tabloyu gösterir; Kontrol Et önce üç sözleşmeyi gizli verilerle sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
ortam: gpu
timeout: 180
```
```starter
import ai_lab
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def ustel_bit_cevir_etkisi(deger, ustel_bit_indisi):
    m, e = math.frexp(abs(deger)); eu = e + 126; yu = eu + ustel_bit_indisi
    yd = m * (2.0 ** (yu - 126))
    return {"eski_ustel": eu, "yeni_ustel": yu, "yeni_deger": yd, "buyume_carpani": abs(yd / deger)}

def hassas_agirlik_sec(agirliklar, gradyanlar, k):
    return [{"indis": i, "duyarlilik": agirliklar[i] * gradyanlar[i]} for i in range(k)]

def agirlik_butunluk_kontrolu(eski_agirliklar, yeni_agirliklar, max_mutlak_sinir):
    return {"degisen_indisler": [], "sinir_asan_indisler": [], "saldiri_tespit": False, "onarilmis_agirliklar": list(yeni_agirliklar)}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_62 as D
    D.goster(ustel_bit_cevir_etkisi, hassas_agirlik_sec, agirlik_butunluk_kontrolu)
```
```test
import ai_lab, math
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('referans_bit_cevir', 'referans_hassas_sec', 'referans_butunluk', 'kanit_yaz', '_yakin'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
ustel_bit_cevir_etkisi = need("ustel_bit_cevir_etkisi")
hassas_agirlik_sec = need("hassas_agirlik_sec")
agirlik_butunluk_kontrolu = need("agirlik_butunluk_kontrolu")
def sinama1(f):
    import math
    def _y(a, b):
        return isinstance(a, dict) and set(a) == set(b) and a["eski_ustel"] == b["eski_ustel"] and a["yeni_ustel"] == b["yeni_ustel"] and abs(a["yeni_deger"] - b["yeni_deger"]) <= 1e-12 * max(1.0, abs(b["yeni_deger"])) and abs(a["buyume_carpani"] - b["buyume_carpani"]) <= 1e-12 * max(1.0, abs(b["buyume_carpani"]))
    try:
        if not _y(f(0.25, 1), {"eski_ustel": 125, "yeni_ustel": 127, "yeni_deger": 1.0, "buyume_carpani": 4.0}): return False
        if not _y(f(-0.25, 1), {"eski_ustel": 125, "yeni_ustel": 127, "yeni_deger": -1.0, "buyume_carpani": 4.0}): return False
        if not _y(f(0.25, 4), {"eski_ustel": 125, "yeni_ustel": 109, "yeni_deger": 0.25 / 65536.0, "buyume_carpani": 1.0 / 65536.0}) or not _y(f(64.0, 0), {"eski_ustel": 133, "yeni_ustel": 132, "yeni_deger": 32.0, "buyume_carpani": 0.5}): return False
        for bad in ((0.0, 1), (100.0, 1), (True, 1), (0.5, -1), (0.5, 8), (0.5, True)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama1(ustel_bit_cevir_etkisi), "XOR üstel bit çevrimi ve işaret koruma")
for ad, mut in [("işaret kayboldu", lambda d, b: dict(ustel_bit_cevir_etkisi(d, b), yeni_deger=abs(ustel_bit_cevir_etkisi(d, b)["yeni_deger"]))), ("XOR yerine toplama", lambda d, b: dict(ustel_bit_cevir_etkisi(d, b), yeni_ustel=ustel_bit_cevir_etkisi(d, b)["eski_ustel"] + (1 << b))), ("çarpan hep 2", lambda d, b: dict(ustel_bit_cevir_etkisi(d, b), buyume_carpani=2.0))]:
    kontrol(not sinama1(mut), "mutant reddedildi: " + ad)
def sinama2(f):
    try:
        w = [0.5, -0.5, 0.25]; g = [1.0, -2.0, 2.0]; old = (list(w), list(g))
        if f(w, g, 2) != [{"indis": 1, "duyarlilik": 1.0}, {"indis": 0, "duyarlilik": 0.5}] or (w, g) != old: return False
        if f([0.0, 0.5], [10.0, 1.0], 1) != [{"indis": 1, "duyarlilik": 0.5}] or f([0.0, 1e-6], [1.5, 1.0], 1) != [{"indis": 0, "duyarlilik": 1.5e-6}]: return False
        for bad in ((None, [1.0], 1), ([], [], 1), ([1.0], [1.0], 0), ([1.0], [1.0], 2), ([1.0], [1.0], True)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama2(hassas_agirlik_sec), "mutlak duyarlılık sıralaması")
for ad, mut in [("mutlak değer yok", lambda w, g, k: [{"indis": i, "duyarlilik": w[i]*g[i]} for i in range(k)]), ("artan sıra", lambda w, g, k: list(reversed(hassas_agirlik_sec(w, g, len(w))))[:k]), ("yalnız gradyan", lambda w, g, k: [{"indis": i, "duyarlilik": abs(g[i])} for i in sorted(range(len(g)), key=lambda j: -abs(g[j]))[:k]])]:
    kontrol(not sinama2(mut), "mutant reddedildi: " + ad)
def sinama3(f):
    try:
        e = [0.5, -0.25, 0.125]; y = [0.5, -50.0, 0.25]; old = (list(e), list(y))
        if f(e, y, 10.0) != {"degisen_indisler": [1, 2], "sinir_asan_indisler": [1], "saldiri_tespit": True, "onarilmis_agirliklar": [0.5, 0.0, 0.25]} or (e, y) != old: return False
        if f(e, e, 10.0) != {"degisen_indisler": [], "sinir_asan_indisler": [], "saldiri_tespit": False, "onarilmis_agirliklar": [0.5, -0.25, 0.125]}: return False
        for bad in ((None, y, 10.0), ([], [], 10.0), (e, y, 0.0), (e, y, True)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama3(agirlik_butunluk_kontrolu), "sınır aşımı ve sıfırlama onarımı")
for ad, mut in [("onarımda sıfırlama yok", lambda e, y, s: dict(agirlik_butunluk_kontrolu(e, y, s), onarilmis_agirliklar=list(y))), ("saldiri_tespit hep False", lambda e, y, s: dict(agirlik_butunluk_kontrolu(e, y, s), saldiri_tespit=False)), ("mutlak değer unutuldu", lambda e, y, s: dict(agirlik_butunluk_kontrolu(e, y, s), sinir_asan_indisler=[i for i, v in enumerate(y) if v > s]))]:
    kontrol(not sinama3(mut), "mutant reddedildi: " + ad)
# farksal tarama (final)
import importlib as _il
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_R = _il.import_module('sandbox.ai_gercek_ai_saldiri_62')
for _ad, _ref, _taban, _toh in (
    ('ustel_bit_cevir_etkisi', 'referans_bit_cevir', (0.25, 4), 4009),
    ('hassas_agirlik_sec', 'referans_hassas_sec', ([0.125, -0.5, 0.25, 0.0625, -0.25], [0.4, -2.5, 1.8, 0.1, -3.0], 2), 3549),
    ('agirlik_butunluk_kontrolu', 'referans_butunluk', ([0.125, -0.5, 0.25, 0.0625, -0.25], [0.125, -0.5, 16384.0, 0.0625, -0.25], 10.0), 4375),
):
    _t, _g = _ff(need(_ad), getattr(_R, _ref), _taban, tohum=_toh)
    kontrol(_t, "farksal tarama (" + _ad + "): bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
if not all(checks): stop()
from sandbox import ai_gercek_ai_saldiri_62 as D
try: r = D.deney(ustel_bit_cevir_etkisi, hassas_agirlik_sec, agirlik_butunluk_kontrolu)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r["bit_ayni"], "gerçek ağırlıkta üstel bit çevrimi bağımsız referansla aynı")
kontrol(r["hassas_ayni"], "gerçek gradyanlarda hassas ağırlık seçimi bağımsız referansla aynı")
kontrol(r["butunluk_ayni"], "gerçek ağırlıklarda bütünlük kontrolü bağımsız referansla aynı")
kontrol(r["secilen_bit"] == 7 and r["bit_etkisi"]["buyume_carpani"] > 1e30, "en duyarlı gerçek ağırlığın en yüksek üstel biti çevrildi (büyüme > 1e30)")
kontrol(r["bozuk_ppl"] > 10 * r["temiz_ppl"], "tek bit çevrimi gerçek metinde perplexity'yi en az 10 kat bozdu")
kontrol(r["saldiri_tespit"] and r["sinir_asan_sayisi"] == 1, "bütünlük sınırı tam olarak bozulan tek ağırlığı yakaladı (yanlış pozitif yok)")
kontrol(abs(r["onarilmis_ppl"] - r["temiz_ppl"]) <= 0.05 * r["temiz_ppl"], "sıfırlama onarımı perplexity'yi temiz değerin %5 yakınına döndürdü")
kontrol(r["kucuk_bit_karsilastirma"] is None or r["kucuk_bit_karsilastirma"]["ppl"] < 2 * r["temiz_ppl"], "bit 0-6 içindeki en büyük çevirme perplexity'yi çökertmedi (karşılaştırma)")
ai_lab.kanit_yaz("ai-saldiri-62-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-saldiri-62", "deney": r})
```
```solution
import ai_lab
import math
def ustel_bit_cevir_etkisi(deger, ustel_bit_indisi):
    if isinstance(deger, bool) or not isinstance(deger, (int, float)) or not math.isfinite(deger) or deger == 0 or abs(deger) >= 100.0:
        raise ValueError("deger")
    if isinstance(ustel_bit_indisi, bool) or not isinstance(ustel_bit_indisi, int) or not 0 <= ustel_bit_indisi <= 7:
        raise ValueError("indis")
    m, e = math.frexp(abs(deger))
    eu = e + 126
    yu = eu ^ (1 << ustel_bit_indisi)
    yd = math.copysign(m * (2.0 ** (yu - 126)), deger)
    return {"eski_ustel": eu, "yeni_ustel": yu, "yeni_deger": yd, "buyume_carpani": abs(yd / deger)}

def hassas_agirlik_sec(agirliklar, gradyanlar, k):
    if not isinstance(agirliklar, list) or not isinstance(gradyanlar, list) or not agirliklar or len(agirliklar) != len(gradyanlar):
        raise ValueError("liste")
    for v in agirliklar + gradyanlar:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError("sayı")
    if isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= len(agirliklar):
        raise ValueError("k")
    skor = [(abs(g) * max(abs(w), 1e-6), i) for i, (w, g) in enumerate(zip(agirliklar, gradyanlar))]
    skor.sort(key=lambda x: (-x[0], x[1]))
    return [{"indis": i, "duyarlilik": d} for d, i in skor[:k]]

def agirlik_butunluk_kontrolu(eski_agirliklar, yeni_agirliklar, max_mutlak_sinir):
    if not isinstance(eski_agirliklar, list) or not isinstance(yeni_agirliklar, list) or not eski_agirliklar or len(eski_agirliklar) != len(yeni_agirliklar):
        raise ValueError("liste")
    for v in eski_agirliklar + yeni_agirliklar:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError("sayı")
    if isinstance(max_mutlak_sinir, bool) or not isinstance(max_mutlak_sinir, (int, float)) or not math.isfinite(max_mutlak_sinir) or max_mutlak_sinir <= 0:
        raise ValueError("sınır")
    deg = [i for i, (a, b) in enumerate(zip(eski_agirliklar, yeni_agirliklar)) if a != b]
    asan = [i for i, b in enumerate(yeni_agirliklar) if abs(b) > max_mutlak_sinir]
    onar = [0.0 if abs(b) > max_mutlak_sinir else float(b) for b in yeni_agirliklar]
    return {"degisen_indisler": deg, "sinir_asan_indisler": asan, "saldiri_tespit": len(asan) > 0, "onarilmis_agirliklar": onar}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_62 as D
    D.goster(ustel_bit_cevir_etkisi, hassas_agirlik_sec, agirlik_butunluk_kontrolu)
```
```hint
Üç işlevi birleştir; `ustel_bit_cevir_etkisi` içinde `XOR` ve işaret korumasını, `agirlik_butunluk_kontrolu` içinde sıfırlamayı uygula.
```
:::

::: anlat Sınır
Bu ders gerçek SmolLM2-135M'in float32 ağırlıklarında üstel `bit-flip` etkisini ve mutlak değer sınırı/sıfırlama savunmasını yazılım düzeyinde inceler; fiziksel DRAM satır çekiçleme (`Rowhammer`) adreslemesini, ECC'yi, quantization ölçek çarpanı saldırılarını ve sınırın altında kalan küçük ama hedefli çevirme zincirlerini kapsamaz.
:::


::: anlat Bunu iki dakikada nasıl anlatırsın?
Float32 değerini işaret, 8 bit exponent ve 23 bit mantissa olarak ayır. Exponent bitine XOR uygulamak mantissayı korurken ölçeği büyük ölçüde değiştirebilir; NaN/Inf sınıfları ayrıca denetlenir. Büyük mutlak ağırlığı sıfırlamanın basit bir bütünlük savunması olduğunu, küçük fakat hedefli flipleri ve fiziksel Rowhammer koşullarını kapsamadığını belirt. Yazılımla bit değiştirme deneyi DRAM sömürüsü kanıtı değildir.

Önkoşul ve yol köprüsü: ai-saldiri-51 model dosyası güvenini; ai-savunma-40 model/çıktı sınırını tamamlar.

| Yaygın yanlış | Mekanizma ve sınır |
|---|---|
| Büyük değer yoksa bütünlük korunmuştur | Sınır altındaki hedefli değişiklikler kaçabilir |

Dinleyiciye sor: Bu dersin kanıtı hangi gözlemi gösterir; hangi daha güçlü iddia için ek deney gerekir? Kanıtın model, ayar, veri kökeni ve hata alanlarını açarak cevabını gerekçelendir.
:::
