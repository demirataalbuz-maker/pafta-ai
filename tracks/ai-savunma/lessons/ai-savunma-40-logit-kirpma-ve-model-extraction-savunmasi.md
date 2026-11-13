---
id: ai-savunma-40
title: Logit Kırpma ve Model Extraction Savunması · SVD Sızıntısını Bastırmak
summary: Top-k logit kırpma ve gürültülü quantization uygula; model extraction saldırısında gizli boyut kestirimi, altuzay geri kazanımı ve argmax karar korunmasını GPU'da ölç.
esleme: ai-savunma-33, ai-savunma-39, ai-guvence-36
timeout: 60
---

::: anlat Tam logit vektörü döndüren bir API ne sızdırır?
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Üretimdeki bir çıkarım API'sinin tam `logit` veya `logprob` vektörü döndürmesi, saldırganın SVD (`Singular Value Decomposition`) ile son katman altuzayını ve gizli boyutu kurtarmasına izin verir | İlk üç görev: `veri/logit_savunma.json` içindeki **sentetik** logit vektörleri ve matrisleri. Final: kurulu SmolLM2-135M API log-olasılıklarında gerçek `torch.linalg.svdvals` ve son katman altuzay karşılaştırması | Yalnız logit kırpmanın tüm `model extraction` saldırılarını tamamen durdurduğunu kanıtlamaz; etiket tabanlı aktif öğrenme saldırıları ayrı bir bütçeyle yine çalışabilir |
| `top-k masking` ve `quantization` ile karar korunması ve geri kazanılan altuzay birlikte ölçülür; dönüşüm her girdide argmax koruma veya spektrumu bastırma garantisi vermez | `topk_logit_kirp`, `logit_nicemle_gurultu` ve merkezlenmiş varyans enerjisiyle `extraction_savunma_raporu` | Sıcaklık ölçekleme veya API hız sınırının (`rate limiting`) operasyonel maliyetini tek başına ölçmez |

> [!NOT]
> Görevler `veri/logit_savunma.json` dosyasını okur; dosya sentetiktir. Setup her Çalıştır/Kontrol Et adımında geçici kopya kurar; değişiklikler taşınmaz, **kalıcılık yoktur**. Ekranda ayrı dosya görüntüleyici yoktur; içeriği görmek için `print` kullan. Gizli testler ayrıdır. Final yeni model indirmez ve GPU varsa onu kullanır.

Bir modelin son katmanı $z = W h + b$ biçimindedir. Eğer API her sorguda tüm sınıfların (veya sözlükteki binlerce token'ın) ham `logit` değerlerini döndürürse, saldırgan $N$ rastgele sorgunun yanıtlarını üst üste dizerek $Z \in \mathbb{R}^{N \times D}$ matrisini kurar. Carlini vd. (2024) bu matrisin tekil değerlerinin (`singular values`) modelin iç darboğaz boyutunu (`hidden dimension`) ve son projeksiyon matrisini doğrudan ele verdiğini göstermiştir.

**SVD'nin gördüğü yapı.** Satırları sorgu olan ham matris $Z=H W^T+\mathbf{1}b^T$ için sütun ortalamalarını çıkarmak sabit bias'ı kaldırır; merkezlenmiş matrisin rank'ı en çok hidden dimension olur. Logprob'larda ek bir sorguya bağlı normalizasyon sabiti her sütuna eklenir; çift yönlü merkezleme bu satır ve sütun sabitlerini kaldırır. Boyutu geri kazanmak için yeterince farklı hidden state, yeterli sorgu/sütun ve sayısal hassasiyet gerekir. SVD tek başına özgün W'yi tek bir koordinat sistemiyle belirlemez; $H R$ ve $W R^{-T}$ çifti aynı çarpımı verir ([Carlini vd., Bölüm 4](https://arxiv.org/html/2403.06634v2#S4)).

**Top-k masking (`logit truncation`) ilk savunma hattıdır.** Kullanıcıya veya aşağı akış uygulamasına çoğu zaman bütün sınıfların tam skoru gerekmez; yalnızca en olası $k$ adayın skoru yeterlidir. İlk $k$ dışındaki tüm indisleri sabit bir `taban_deger` (ör. `-10.0` veya `0.0`) seviyesine çekmek, düşük olasılıklı kuyruk sınıfları üzerinden akan doğrusal altuzay bilgisini keser.

**Quantization ve gürültü ikinci hattır. Differential privacy garantisi için ayrıca sensitivity ve privacy budget tanımı gerekir; bu ders böyle bir garanti vermez.** İlk $k$ logit bile tam kayan nokta (`float64` / `float32`) hassasiyetiyle verildiğinde sonlu farklarla (`finite differences`) yerel eğim tahmin edilebilir. Logitlere küçük bir gürültü vektörü ekleyip $\Delta$ (`adim_boyutu`) ızgarasına yuvarlamak:
$$\tilde{z}_i = \operatorname{round}\!\left(\frac{z_i + \eta_i}{\Delta}\right) \cdot \Delta$$
aynı hücrede kalan farkları kaldırır; hücre sınırını geçen küçük farklar yine farklı çıktılar üretir. Argmax korunma oranı logit marjına ve gürültüye bağlıdır, ölçülmelidir.

**Saldırgan ne dener?** `top-k` kısıtını aşmak için hedef token'ların logitlerini öne çıkaracak önekler (`prefix Bias` / `logit bias`) gönderir ve gürültüyü bastırmak için aynı sorguyu birçok kez tekrarlayıp ortalamasını alır.

**Savunma neden kırılır?** Taban değer maksimumu aşarsa argmax bozulabilir; maksimuma eşit olması da tie nedeniyle tehlikelidir. Örneğin `[1,3]`, k=1, taban=3 sonucu `[3,3]` olur ve ilk indis argmax kuralı kararı 1'den 0'a taşır. Tek maksimumu korumak için tabanı maksimumdan kesin küçük seçmek gerekir. Bağımsız, sıfır ortalamalı ek gürültüde m tekrar ortalamasının standart sapması ideal olarak sigma/sqrt(m) olur. Ancak quantization doğrusal değildir; tekrarlı sorgular her durumda özgün logiti tarafsız ve tam geri vermez. Sabit girdiye aynı gürültüyü veren bir kural da bu ortalama modelinden farklıdır; uyarlanabilir saldırı ayrıca ölçülür.

**Görev 1'de sık tuzaklar:** Yalnızca en büyük $k$ elemanı içeren kısa bir liste döndürmek indeks bilgisini yok eder; çıktı listesi girişle aynı uzunlukta kalmalı ve elenen indisler `taban_deger` almalıdır. Eşit değerli logitlerde küçük indisli olan önceliklidir.

Kaynaklar: [Carlini vd. 2024 — Stealing Part of a Production Language Model](https://arxiv.org/abs/2403.06634), [Tramèr vd. 2016 — Stealing Machine Learning Models via Prediction APIs](https://arxiv.org/abs/1609.02943), [Orekondy vd. 2019 — Knockoff Nets](https://arxiv.org/abs/1812.02766). Bu dersteki bütün sayılar yalnız yerel kanıttan gelir.

Köprü: ai-savunma-33 güvenlik eşiklerini kalibre eder; ai-guvence-36 logit ölçeklemenin gradient üzerindeki etkisini inceler; bu ders tek seferlik SVD extraction karşısında çıktı dönüşümünün etkisini ölçer; genel model extraction engelleme garantisi vermez.
:::

::: tahmin Kuyruk logitleri silinirse matris enerjisine ne olur?
Çıktıyı tahmin et, sonra Çalıştır ile karşılaştır.
```python
z = [6.0, 2.0, -1.0, -3.0]
secilen = set(sorted(range(len(z)), key=lambda i: (-z[i], i))[:2])
kirpilmis = [float(v) if i in secilen else -10.0 for i, v in enumerate(z)]
print(kirpilmis)
print(z.index(max(z)) == kirpilmis.index(max(kirpilmis)))
print(round((2.13 - 0.05) / 0.5) * 0.5)
```
???
```cikti
[6.0, 2.0, -10.0, -10.0]
True
2.0
```
Tahmininle gerçek çıktı arasındaki farkı tezgâhta yorum satırı olarak yaz: üçüncü ve dördüncü sınıfların ikisi de `-10.0` olduğunda saldırgan bu iki sınıf arasındaki göreli fark hakkında ne öğrenebilir? Sonra üç kusurlu başlangıç kodunu çalıştır ve her birinin neyi kaçırdığını önce kendin teşhis et; açıklama çözümün ardından gelir.
:::

::: gorev 1 · Top-k logit kırpma (`topk_logit_kirp`)
`topk_logit_kirp(logitler,k,taban_deger)`: `logitler` en az 2 elemanlı liste, elemanları ve `taban_deger` bool olmayan sonlu sayı; `k` bool olmayan int ve `1 <= k <= len(logitler)`. En büyük `k` elemanı (eşitlikte küçük indis öncelikli) `float` olarak koru, diğer tüm indisleri `float(taban_deger)` yap ve aynı uzunlukta yeni liste döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-40")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def topk_logit_kirp(logitler,k,taban_deger):
    return sorted(logitler,reverse=True)[:k]

from ai_savunma_veri import json_yukle
v=json_yukle("veri/logit_savunma.json")
print("Kırpılmış:",topk_logit_kirp(v["ornek_logit"],v["k"],v["taban_deger"]))
```
```test
def sinama1(f):
    import math,random
    def _r(z,k,t):
        s=set(sorted(range(len(z)),key=lambda i:(-z[i],i))[:k])
        return [float(v) if i in s else float(t) for i,v in enumerate(z)]
    try:
        z=[4.2,1.8,-0.5,3.1,-2.0];old=list(z)
        if f(z,2,-10.0)!=[4.2,-10.0,-10.0,3.1,-10.0] or z!=old:return False
        if f([1.0,3.0,3.0,2.0],2,0.0)!=[0.0,3.0,3.0,0.0]:return False
        if f([5.0,5.0,5.0],1,-1.0)!=[5.0,-1.0,-1.0]:return False
        if f([2.0,-1.0,4.0],3,-9.0)!=[2.0,-1.0,4.0]:return False
        if f([1.0,3.0],1,3.0)!=[3.0,3.0]:return False
        rng=random.Random(40)
        for _ in range(25):
            n=rng.randint(2,8);p=[round(rng.uniform(-5,5),3) for _ in range(n)];k=rng.randint(1,n);t=round(rng.uniform(-20,-5),2)
            if f(list(p),k,t)!=_r(p,k,t):return False
        for bad in ((None,1,0.0),([],1,0.0),([1.0],1,0.0),((1.0,2.0),1,0.0),([True,2.0],1,0.0),([float("nan"),2.0],1,0.0),([float("inf"),2.0],1,0.0),([1.0,2.0],0,0.0),([1.0,2.0],3,0.0),([1.0,2.0],True,0.0),([1.0,2.0],1.5,0.0),([1.0,2.0],1,True),([1.0,2.0],1,float("nan")),([1.0,2.0],1,"x")):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama1(topk_logit_kirp),"top-k koruma, eşitlik önceliği, taban değer ve geçersiz girdi")
for ad,mut in [("kısa liste",lambda z,k,t:sorted(z,reverse=True)[:k]),("taban sıfır sabit",lambda z,k,t:topk_logit_kirp(z,k,0.0)),("hiç kırpma yok",lambda z,k,t:[float(v) for v in z])]:
    ok(not sinama1(mut),"mutant reddedildi: "+ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(topk_logit_kirp, _il.import_module('ai_gercek_ai_savunma_40').referans_topk, ([4.2, 1.8, -0.5, 3.1, -2.0], 2, -10.0), tohum=2772)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def topk_logit_kirp(logitler,k,taban_deger):
    if not isinstance(logitler,list) or len(logitler)<2:raise ValueError("logitler")
    for v in logitler+[taban_deger]:
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError("sayı")
    if isinstance(k,bool) or not isinstance(k,int) or not 1<=k<=len(logitler):raise ValueError("k")
    sec=set(sorted(range(len(logitler)),key=lambda i:(-logitler[i],i))[:k])
    return [float(v) if i in sec else float(taban_deger) for i,v in enumerate(logitler)]

from ai_savunma_veri import json_yukle
v=json_yukle("veri/logit_savunma.json")
print("Kırpılmış:",topk_logit_kirp(v["ornek_logit"],v["k"],v["taban_deger"]))
```
```hint
İndisleri `(-logitler[i], i)` anahtarıyla sıralayıp ilk `k` indisi kümede tut; kümede olmayan indisleri `float(taban_deger)` yap.
```
:::

::: anlat Gürültülü quantization neden sonlu farkları körleştirir?
Saldırgan $x$ ve $x + \delta$ gibi birbirine çok yakın iki girdi gönderdiğinde logitlerdeki $10^{-5}$ mertebesindeki değişimi okuyabiliyorsa yerel Jacobian'ı yaklaşık hesaplayabilir. Gürültü ekleyip `adim_boyutu` ızgarasına yuvarlamak, aynı hücre içinde kalan değişimleri aynı basamağa eşler. Fakat Δ=0.5 için 0.2499999 ile 0.2500001 arasındaki yalnız 2e-7 fark, iki farklı basamağa geçer. Python round tam yarıda çift tamsayıya yuvarlar; sınır davranışı sonlu fark analizinde önemlidir.

Formül her bileşen için `round((round((logitler[i] + gurultu_vektoru[i]) / adim_boyutu) * adim_boyutu), 8)` şeklindedir.

**Görev 2'de sık tuzaklar:** Gürültüyü yuvarlamadan *sonra* eklemek, gürültünün kendisini ızgara dışına taşır ve quantization işleminin adım yapısını bozar. Önce topla, sonra ızgaraya yuvarla.
:::

::: gorev 2 · Gürültülü quantization (`logit_nicemle_gurultu`)
`logit_nicemle_gurultu(logitler,adim_boyutu,gurultu_vektoru)`: `logitler` ve `gurultu_vektoru` aynı uzunlukta (`>=2`) dolu listeler; tüm elemanlar ve `adim_boyutu` bool olmayan sonlu sayı; `adim_boyutu > 0`. Her `i` için `round(round((logitler[i] + gurultu_vektoru[i]) / adim_boyutu) * adim_boyutu, 8)` değerini yeni listede döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-40")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def logit_nicemle_gurultu(logitler,adim_boyutu,gurultu_vektoru):
    return [round(a/adim_boyutu)*adim_boyutu+g for a,g in zip(logitler,gurultu_vektoru)]

from ai_savunma_veri import json_yukle
v=json_yukle("veri/logit_savunma.json")
print("Nicemlenmiş:",logit_nicemle_gurultu(v["ornek_logit"],v["adim_boyutu"],v["gurultu"]))
```
```test
def sinama2(f):
    import math,random
    def _r(z,s,g):return [round(round((a+b)/s)*s,8) for a,b in zip(z,g)]
    try:
        z=[4.2,1.8,-0.5];g=[0.06,-0.06,0.01];old=(list(z),list(g))
        if f(z,0.5,g)!=[4.5,1.5,-0.5] or (z,g)!=old:return False
        if f([1.12,2.38],0.25,[0.02,-0.02])!=[1.25,2.25]:return False
        if f([0.1,0.2,0.3],0.1,[0.04,0.04,0.04])!=[0.1,0.2,0.3]:return False
        if f([1e-8,2e-8],1e-8,[0.0,0.0])!=[1e-8,2e-8]:return False
        if f([0.123456789,0.0],0.123456789,[0.0,0.0])!=[0.12345679,0.0]:return False
        if f([0.25,0.75,-0.25,-0.75],0.5,[0.0]*4)!=[0.0,1.0,0.0,-1.0]:return False
        if f([0.2499999,0.2500001],0.5,[0.0,0.0])!=[0.0,0.5]:return False
        rng=random.Random(4040)
        for _ in range(25):
            n=rng.randint(2,7);p=[rng.uniform(-4,4) for _ in range(n)];q=[rng.uniform(-0.2,0.2) for _ in range(n)];s=rng.choice([0.1,0.2,0.25,0.5])
            if f(list(p),s,list(q))!=_r(p,s,q):return False
        for bad in ((None,0.5,[0.0,0.0]),([1.0,2.0],0.5,None),([1.0],0.5,[0.0]),([1.0,2.0],0.5,[0.0]),([1.0,2.0],0.0,[0.0,0.0]),([1.0,2.0],-0.5,[0.0,0.0]),([1.0,2.0],True,[0.0,0.0]),([True,2.0],0.5,[0.0,0.0]),([1.0,2.0],0.5,[False,0.0]),([float("nan"),2.0],0.5,[0.0,0.0]),([1.0,2.0],float("inf"),[0.0,0.0])):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama2(logit_nicemle_gurultu),"gürültü sonrası ızgara yuvarlama ve geçersiz girdi")
for ad,mut in [("gürültüsüz",lambda z,s,g:logit_nicemle_gurultu(z,s,[0.0]*len(g))),("yuvarlama yok",lambda z,s,g:[round(a+b,8) for a,b in zip(z,g)]),("sonra gürültü",lambda z,s,g:[round(round(a/s)*s+b,8) for a,b in zip(z,g)])]:
    ok(not sinama2(mut),"mutant reddedildi: "+ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(logit_nicemle_gurultu, _il.import_module('ai_gercek_ai_savunma_40').referans_nicemle, ([4.2, 1.8, -0.5, 3.1, -2.0], 0.5, [0.04, -0.08, 0.02, -0.03, 0.05]), tohum=3413)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def logit_nicemle_gurultu(logitler,adim_boyutu,gurultu_vektoru):
    if not isinstance(logitler,list) or not isinstance(gurultu_vektoru,list) or len(logitler)<2 or len(logitler)!=len(gurultu_vektoru):raise ValueError("boyut")
    for v in logitler+gurultu_vektoru+[adim_boyutu]:
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError("sayı")
    if adim_boyutu<=0:raise ValueError("adim")
    return [round(round((a+b)/adim_boyutu)*adim_boyutu,8) for a,b in zip(logitler,gurultu_vektoru)]

from ai_savunma_veri import json_yukle
v=json_yukle("veri/logit_savunma.json")
print("Nicemlenmiş:",logit_nicemle_gurultu(v["ornek_logit"],v["adim_boyutu"],v["gurultu"]))
```
```hint
Önce `logitler[i] + gurultu_vektoru[i]` toplamını `adim_boyutu`'na bölüp `round` ile en yakın tam sayıya yuvarla, sonra `adim_boyutu` ile çarp.
```
:::

::: anlat Savunmanın başarısı nasıl ölçülür?
Görev 3 şu iki koşulu kullanan öğretici bir rapor bayrağı tanımlar; bu bayrak genel extraction güvenliği kanıtı değildir:
1. **Görev doğruluğu bozulmamalıdır:** Her satırdaki en yüksek logit indisi (`argmax`) en az `%80` oranında (`argmax_korunma >= 0.8`) orijinal modelle aynı kalmalıdır.
2. **Spektral varyans enerjisi daralmalıdır:** Sütun ortalamaları çıkarılmış (`merkezlenmiş`) matrisin Frobenius enerjisi $\sum_{i,j} (M_{i,j} - \bar{M}_{\cdot,j})^2$, tekil değerlerin kareleri toplamına ($\sum_k \sigma_k^2$) eşittir. Korunan matrisin enerjisinin orijinal matrisin enerjisine oranı `enerji_orani <= tekil_oran_esik` olmalıdır.

Frobenius enerjisi aynı kalırken spektrum farklı rank ve altuzaylar üzerinde dağılabilir. Enerji azalması saldırganın gizli boyutu veya son katman altuzayını geri kazanamadığını tek başına kanıtlamaz. Gerçek finalde bu nedenle ayrıca saldırının boyut ve altuzay sonuçları ölçülür.

**Görev 3'te sık tuzaklar:** Sütun ortalamasını çıkarmadan doğrudan kareler toplamı almak, sabit `taban_deger` kaymasını enerji sanır. `savunma_basarili` alanı hem `argmax_korunma >= 0.8` hem de `enerji_orani <= tekil_oran_esik` şartını birlikte arar.
:::

::: gorev 3 · Extraction savunma raporu (`extraction_savunma_raporu`)
`extraction_savunma_raporu(orijinal_logitler,korunan_logitler,tekil_oran_esik)`: İki matris aynı boyutta (`N>=2` satır, `D>=2` sütun) sayı listeleri; `0 < tekil_oran_esik <= 1` bool olmayan sonlu sayı. `{"argmax_korunma":..., "ortalama_l2_sapma":..., "enerji_orani":..., "savunma_basarili": bool(argmax_korunma >= 0.8 and enerji_orani <= tekil_oran_esik)}` döndür (orijinal enerji `<=1e-12` ise `enerji_orani=0.0`). Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-40")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def extraction_savunma_raporu(orijinal_logitler,korunan_logitler,tekil_oran_esik):
    n=len(orijinal_logitler);d=len(orijinal_logitler[0])
    ak=sum(1 for a,b in zip(orijinal_logitler,korunan_logitler) if a.index(max(a))==b.index(max(b)))/n
    l2=sum(math.sqrt(sum((x-y)**2 for x,y in zip(a,b))) for a,b in zip(orijinal_logitler,korunan_logitler))/n
    oa=[sum(orijinal_logitler[i][j] for i in range(n))/n for j in range(d)]
    ob=[sum(korunan_logitler[i][j] for i in range(n))/n for j in range(d)]
    ea=sum((orijinal_logitler[i][j]-oa[j])**2 for i in range(n) for j in range(d))
    eb=sum((korunan_logitler[i][j]-ob[j])**2 for i in range(n) for j in range(d))
    oran=eb/ea if ea>1e-12 else 0.0
    return {"argmax_korunma":ak,"ortalama_l2_sapma":l2,"enerji_orani":oran,"savunma_basarili":ak>=0.8}

from ai_savunma_veri import json_yukle
v=json_yukle("veri/logit_savunma.json")
for ad,m in v["senaryolar"].items():
    print(ad,extraction_savunma_raporu(v["orijinal_matris"],m,v["tekil_oran_esik"]))
```
```test
def sinama3(f):
    import copy,math
    try:
        a=[[5.0,2.0,-1.0,-3.0],[1.0,6.0,-2.0,-4.0],[-2.0,1.0,5.5,-3.5],[-3.0,-1.0,2.0,6.5]]
        b=[[2.0,0.0,0.0,0.0],[0.0,2.0,0.0,0.0],[0.0,0.0,2.0,0.0],[0.0,0.0,0.0,2.0]]
        old=(copy.deepcopy(a),copy.deepcopy(b))
        r=f(a,b,0.25)
        if (a,b)!=old or r["argmax_korunma"]!=1.0 or not r["savunma_basarili"] or not (0.05<r["enerji_orani"]<0.2):return False
        r2=f(a,a,0.25)
        if r2["argmax_korunma"]!=1.0 or r2["ortalama_l2_sapma"]!=0.0 or abs(r2["enerji_orani"]-1.0)>1e-9 or r2["savunma_basarili"] is not False:return False
        ters=[[0.0,2.0,0.0,0.0],[2.0,0.0,0.0,0.0],[2.0,0.0,0.0,0.0],[2.0,0.0,0.0,0.0]]
        r3=f(a,ters,0.5)
        if r3["argmax_korunma"]!=0.0 or r3["savunma_basarili"] is not False:return False
        aa=[[-2.0,0.0],[2.0,0.0]];bb=[[-1.0,0.0],[1.0,0.0]]
        if f(aa,bb,0.25)["savunma_basarili"] is not True:return False
        if f(aa,bb,math.nextafter(0.25,0.0))["savunma_basarili"] is not False:return False
        sabit=[[1.0,2.0],[1.0,2.0]]
        if f(sabit,sabit,0.5)["enerji_orani"]!=0.0:return False
        if f([[-6e-7,6e-7],[6e-7,-6e-7]],[[-6e-7,6e-7],[6e-7,-6e-7]],0.5)["enerji_orani"]!=1.0:return False
        if f([[-4e-7,4e-7],[4e-7,-4e-7]],[[-4e-7,4e-7],[4e-7,-4e-7]],0.5)["enerji_orani"]!=0.0:return False
        if f([[-5e-7,5e-7],[5e-7,-5e-7]],[[-5e-7,5e-7],[5e-7,-5e-7]],1.0)["enerji_orani"]!=0.0:return False
        if f([[2.0,0.0],[2.0,0.0]],[[2.0,0.0],[0.0,2.0]],1.0)["savunma_basarili"] is not False:return False
        if f([[2.0,0.0]]*5,[[2.0,0.0]]*4+[[0.0,2.0]],1.0)["savunma_basarili"] is not True:return False
        for bad in ((None,b,0.25),(a,None,0.25),([[1.0,2.0]],[[1.0,2.0]],0.25),([[1.0],[2.0]],[[1.0],[2.0]],0.25),(a,b[:-1],0.25),([[1.0,2.0],[3.0]],[[1.0,2.0],[3.0,4.0]],0.25),(a,b,0.0),(a,b,1.2),(a,b,True),(a,b,float("nan")),([[True,1.0],[1.0,2.0]],[[1.0,1.0],[1.0,2.0]],0.25)):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama3(extraction_savunma_raporu),"argmax korunma, merkezlenmiş enerji oranı, savunma kararı ve geçersiz girdi")
for ad,mut in [("yalnız argmax",lambda a,b,e:dict(extraction_savunma_raporu(a,b,e),savunma_basarili=extraction_savunma_raporu(a,b,e)["argmax_korunma"]>=0.8)),("hep başarılı",lambda a,b,e:dict(extraction_savunma_raporu(a,b,e),savunma_basarili=True)),("enerji sıfır",lambda a,b,e:dict(extraction_savunma_raporu(a,b,e),enerji_orani=0.0))]:
    ok(not sinama3(mut),"mutant reddedildi: "+ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(extraction_savunma_raporu, _il.import_module('ai_gercek_ai_savunma_40').referans_rapor, ([[5.0, 2.0, -1.0, -3.0], [1.0, 6.0, -2.0, -4.0], [-2.0, 1.0, 5.5, -3.5], [-3.0, -1.0, 2.0, 6.5]], [[5.0, 1.9, -1.0, -2.9], [1.0, 5.9, -2.0, -3.9], [-2.0, 1.0, 5.4, -3.4], [-3.0, -1.0, 2.0, 6.4]], 0.25), tohum=3862)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_a40=[[-5e-7,5e-7],[5e-7,-5e-7]]
ok(sum(v*v for row in _a40 for v in row)==1e-12,"tam enerji eşiği örneği")
eq(extraction_savunma_raporu(_a40,_a40,1.0)["enerji_orani"],0.0,"orijinal enerji tam 1e-12 ise sıfır oran")
_a40=[[2.0,0.0] for _ in range(5)];_b40=[[2.0,0.0] for _ in range(4)]+[[0.0,2.0]]
_r40=extraction_savunma_raporu(_a40,_b40,1.0)
ok(_r40["argmax_korunma"]==0.8 and _r40["savunma_basarili"] is True,"argmax korunma tam 0.8 dahil")
```
```solution
import math
def extraction_savunma_raporu(orijinal_logitler,korunan_logitler,tekil_oran_esik):
    if not isinstance(orijinal_logitler,list) or not isinstance(korunan_logitler,list) or len(orijinal_logitler)<2 or len(orijinal_logitler)!=len(korunan_logitler):raise ValueError("matris")
    if isinstance(tekil_oran_esik,bool) or not isinstance(tekil_oran_esik,(int,float)) or not math.isfinite(tekil_oran_esik) or not 0<tekil_oran_esik<=1:raise ValueError("esik")
    d=len(orijinal_logitler[0]) if isinstance(orijinal_logitler[0],list) else 0
    if d<2:raise ValueError("sutun")
    for a,b in zip(orijinal_logitler,korunan_logitler):
        if not isinstance(a,list) or not isinstance(b,list) or len(a)!=d or len(b)!=d:raise ValueError("satir")
        for v in a+b:
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError("hucre")
    n=len(orijinal_logitler)
    kor=0;l2=0.0
    for a,b in zip(orijinal_logitler,korunan_logitler):
        if max(range(d),key=lambda j:a[j])==max(range(d),key=lambda j:b[j]):kor+=1
        l2+=math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))
    oa=[sum(orijinal_logitler[i][j] for i in range(n))/n for j in range(d)]
    ob=[sum(korunan_logitler[i][j] for i in range(n))/n for j in range(d)]
    ea=sum((orijinal_logitler[i][j]-oa[j])**2 for i in range(n) for j in range(d))
    eb=sum((korunan_logitler[i][j]-ob[j])**2 for i in range(n) for j in range(d))
    oran=eb/ea if ea>1e-12 else 0.0
    ak=kor/n
    return {"argmax_korunma":ak,"ortalama_l2_sapma":l2/n,"enerji_orani":oran,"savunma_basarili":bool(ak>=0.8 and oran<=tekil_oran_esik)}

from ai_savunma_veri import json_yukle
v=json_yukle("veri/logit_savunma.json")
for ad,m in v["senaryolar"].items():
    print(ad,extraction_savunma_raporu(v["orijinal_matris"],m,v["tekil_oran_esik"]))
```
```hint
Her sütunun ortalamasını ayrı ayrı çıkarıp kareler toplamını al; `savunma_basarili` için hem `argmax_korunma >= 0.8` hem de `enerji_orani <= tekil_oran_esik` şartını kontrol et.
```
:::

::: anlat Hata vitrini · çalışmış yanlış rapor
Yazar, kusurlu başlangıç kodlarını görünür sentetik veriyle gerçekten çalıştırdı ve sonucu `outputs/yeni-ai-savunma-40/gorunur-run-1.json` dosyasına kaydetti. `korumasiz_api` senaryosunda `enerji_orani=0.9854` olduğu (yani logit uzayının neredeyse tamamı sızdığı) hâlde, 3. görevin kusurlu kodu yalnız `argmax_korunma >= 0.8` kontrolü yaptığı için `savunma_basarili=True` döndürür. Doğru kod `savunma_basarili=False` verir.

Bu kaydedilmiş bir hesaplama çıktısıdır, model yanıtı değildir ve rapor sentetiktir. Yalnız modelin doğruluğuna bakıp API'yi güvenli ilan eden bir ekip neyi gözden kaçırır? Kendi cümlenle açıkla. Gerçek finaldeki ölçüm ayrıca üretilir; bu sayılar onun yerine konmaz.
:::

::: anlat Gerçek deney: SmolLM2 API'sinde Carlini saldırısını savunmadan önce ve sonra koşmak
Final, yerel önbellekteki gerçek **SmolLM2-135M** modelini bir API gibi sorgular (sabit revizyon, indirme yok): 700 rastgele kısa isteme, sözlüğün sabit 1.024 sütunu üzerinde log-olasılık döndürür. Saldırgan ai-saldiri-57'deki saldırıyı iki kez koşar: önce ham yanıtlara, sonra her satırı senin `topk_logit_kirp` (k=5, taban −30) ve `logit_nicemle_gurultu` (adım 0.1, Gaussian σ=0.02) işlevlerinden geçen yanıtlara.

Savunmasız API'de çift yönlü merkezleme + SVD modelin gerçek gizli boyutunu (576) bulur, 576. tekil değerde binlerce katlık bir uçurum oluşur ve kurtarılan altuzay gerçek `lm_head` ile örtüşür. Savunmadan sonra tahmini boyut yanlıştır, uçurum kaybolur (oran ≈ 1) ve altuzay örtüşmesi sıfıra iner; buna karşın kullanıcıya dönen en olası token (argmax) yanıtların büyük çoğunluğunda aynı kalır. `extraction_savunma_raporu`'ndaki enerji eşiği (0.65) bu deneyde ölçüldü: log-olasılıklarda kırpılmış matrisin merkezli enerjisi ham enerjinin yaklaşık %60'ı kalır; asıl başarı ölçütü uçurumun ve altuzay örtüşmesinin kaybolmasıdır.

**Kanıt dosyasını oku:** `saldiri_savunmasiz` ve `saldiri_savunmali` alanlarını karşılaştır. Soru 1: savunmadan sonra `tahmini_boyut` neden 576 yerine sorgu sayısına yakın bir değer çıkıyor? Soru 2: `altuzay_kosinus_min` 1'den ~0'a düştü; saldırgan aynı istemi 1.000 kez sorup gürültüyü ortalasaydı hangi bileşen (kırpma mı, gürültü mü) yine de koruma sağlardı? Cevabını tezgâhta yorum olarak yaz; otomatik test bu serbest açıklamayı puanlamaz.
:::

::: gorev Gerçek deney · GPU'da logit kırpma ve SVD sızıntı analizi
Önceki üç görevin `topk_logit_kirp`, `logit_nicemle_gurultu` ve `extraction_savunma_raporu` işlevlerini birleştir. Çalıştır gerçek SVD tablosunu gösterir; Kontrol Et önce üç sözleşmeyi gizli verilerle sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
ortam: gpu
timeout: 180
```
```starter
import ai_lab
import math
def topk_logit_kirp(logitler,k,taban_deger):
    return sorted(logitler,reverse=True)[:k]
def logit_nicemle_gurultu(logitler,adim_boyutu,gurultu_vektoru):
    return [round(a/adim_boyutu)*adim_boyutu+g for a,g in zip(logitler,gurultu_vektoru)]
def extraction_savunma_raporu(orijinal_logitler,korunan_logitler,tekil_oran_esik):
    return {"argmax_korunma":1.0,"ortalama_l2_sapma":0.0,"enerji_orani":1.0,"savunma_basarili":True}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_40 as D
    D.goster(topk_logit_kirp,logit_nicemle_gurultu,extraction_savunma_raporu)
```
```test
import ai_lab,math
checks=[]
def kontrol(x,m):checks.append(bool(x));ok(x,m)
issues=ai_lab.kod_denetimi(src,('referans_topk', 'referans_nicemle', 'referans_rapor', 'kanit_yaz', '_yakin'),izin=())
kontrol(not issues,"kopya/yama/dinamik kod yok: "+str(issues))
if issues:stop()
topk_logit_kirp=need("topk_logit_kirp")
logit_nicemle_gurultu=need("logit_nicemle_gurultu")
extraction_savunma_raporu=need("extraction_savunma_raporu")
def sinama1(f):
    import math,random
    def _r(z,k,t):
        s=set(sorted(range(len(z)),key=lambda i:(-z[i],i))[:k])
        return [float(v) if i in s else float(t) for i,v in enumerate(z)]
    try:
        z=[4.2,1.8,-0.5,3.1,-2.0];old=list(z)
        if f(z,2,-10.0)!=[4.2,-10.0,-10.0,3.1,-10.0] or z!=old:return False
        if f([1.0,3.0,3.0,2.0],2,0.0)!=[0.0,3.0,3.0,0.0]:return False
        if f([5.0,5.0,5.0],1,-1.0)!=[5.0,-1.0,-1.0]:return False
        if f([2.0,-1.0,4.0],3,-9.0)!=[2.0,-1.0,4.0]:return False
        if f([1.0,3.0],1,3.0)!=[3.0,3.0]:return False
        rng=random.Random(40)
        for _ in range(25):
            n=rng.randint(2,8);p=[round(rng.uniform(-5,5),3) for _ in range(n)];k=rng.randint(1,n);t=round(rng.uniform(-20,-5),2)
            if f(list(p),k,t)!=_r(p,k,t):return False
        for bad in ((None,1,0.0),([],1,0.0),([1.0],1,0.0),((1.0,2.0),1,0.0),([True,2.0],1,0.0),([float("nan"),2.0],1,0.0),([float("inf"),2.0],1,0.0),([1.0,2.0],0,0.0),([1.0,2.0],3,0.0),([1.0,2.0],True,0.0),([1.0,2.0],1.5,0.0),([1.0,2.0],1,True),([1.0,2.0],1,float("nan")),([1.0,2.0],1,"x")):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
kontrol(sinama1(topk_logit_kirp),"top-k koruma, eşitlik önceliği, taban değer ve geçersiz girdi")
for ad,mut in [("kısa liste",lambda z,k,t:sorted(z,reverse=True)[:k]),("taban sıfır sabit",lambda z,k,t:topk_logit_kirp(z,k,0.0)),("hiç kırpma yok",lambda z,k,t:[float(v) for v in z])]:
    kontrol(not sinama1(mut),"mutant reddedildi: "+ad)
def sinama2(f):
    import math,random
    def _r(z,s,g):return [round(round((a+b)/s)*s,8) for a,b in zip(z,g)]
    try:
        z=[4.2,1.8,-0.5];g=[0.06,-0.06,0.01];old=(list(z),list(g))
        if f(z,0.5,g)!=[4.5,1.5,-0.5] or (z,g)!=old:return False
        if f([1.12,2.38],0.25,[0.02,-0.02])!=[1.25,2.25]:return False
        if f([0.1,0.2,0.3],0.1,[0.04,0.04,0.04])!=[0.1,0.2,0.3]:return False
        if f([1e-8,2e-8],1e-8,[0.0,0.0])!=[1e-8,2e-8]:return False
        if f([0.123456789,0.0],0.123456789,[0.0,0.0])!=[0.12345679,0.0]:return False
        if f([0.25,0.75,-0.25,-0.75],0.5,[0.0]*4)!=[0.0,1.0,0.0,-1.0]:return False
        if f([0.2499999,0.2500001],0.5,[0.0,0.0])!=[0.0,0.5]:return False
        rng=random.Random(4040)
        for _ in range(25):
            n=rng.randint(2,7);p=[rng.uniform(-4,4) for _ in range(n)];q=[rng.uniform(-0.2,0.2) for _ in range(n)];s=rng.choice([0.1,0.2,0.25,0.5])
            if f(list(p),s,list(q))!=_r(p,s,q):return False
        for bad in ((None,0.5,[0.0,0.0]),([1.0,2.0],0.5,None),([1.0],0.5,[0.0]),([1.0,2.0],0.5,[0.0]),([1.0,2.0],0.0,[0.0,0.0]),([1.0,2.0],-0.5,[0.0,0.0]),([1.0,2.0],True,[0.0,0.0]),([True,2.0],0.5,[0.0,0.0]),([1.0,2.0],0.5,[False,0.0]),([float("nan"),2.0],0.5,[0.0,0.0]),([1.0,2.0],float("inf"),[0.0,0.0])):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
kontrol(sinama2(logit_nicemle_gurultu),"gürültü sonrası ızgara yuvarlama ve geçersiz girdi")
for ad,mut in [("gürültüsüz",lambda z,s,g:logit_nicemle_gurultu(z,s,[0.0]*len(g))),("yuvarlama yok",lambda z,s,g:[round(a+b,8) for a,b in zip(z,g)]),("sonra gürültü",lambda z,s,g:[round(round(a/s)*s+b,8) for a,b in zip(z,g)])]:
    kontrol(not sinama2(mut),"mutant reddedildi: "+ad)
def sinama3(f):
    import copy,math
    try:
        a=[[5.0,2.0,-1.0,-3.0],[1.0,6.0,-2.0,-4.0],[-2.0,1.0,5.5,-3.5],[-3.0,-1.0,2.0,6.5]]
        b=[[2.0,0.0,0.0,0.0],[0.0,2.0,0.0,0.0],[0.0,0.0,2.0,0.0],[0.0,0.0,0.0,2.0]]
        old=(copy.deepcopy(a),copy.deepcopy(b))
        r=f(a,b,0.25)
        if (a,b)!=old or r["argmax_korunma"]!=1.0 or not r["savunma_basarili"] or not (0.05<r["enerji_orani"]<0.2):return False
        r2=f(a,a,0.25)
        if r2["argmax_korunma"]!=1.0 or r2["ortalama_l2_sapma"]!=0.0 or abs(r2["enerji_orani"]-1.0)>1e-9 or r2["savunma_basarili"] is not False:return False
        ters=[[0.0,2.0,0.0,0.0],[2.0,0.0,0.0,0.0],[2.0,0.0,0.0,0.0],[2.0,0.0,0.0,0.0]]
        r3=f(a,ters,0.5)
        if r3["argmax_korunma"]!=0.0 or r3["savunma_basarili"] is not False:return False
        aa=[[-2.0,0.0],[2.0,0.0]];bb=[[-1.0,0.0],[1.0,0.0]]
        if f(aa,bb,0.25)["savunma_basarili"] is not True:return False
        if f(aa,bb,math.nextafter(0.25,0.0))["savunma_basarili"] is not False:return False
        sabit=[[1.0,2.0],[1.0,2.0]]
        if f(sabit,sabit,0.5)["enerji_orani"]!=0.0:return False
        if f([[-6e-7,6e-7],[6e-7,-6e-7]],[[-6e-7,6e-7],[6e-7,-6e-7]],0.5)["enerji_orani"]!=1.0:return False
        if f([[-4e-7,4e-7],[4e-7,-4e-7]],[[-4e-7,4e-7],[4e-7,-4e-7]],0.5)["enerji_orani"]!=0.0:return False
        if f([[-5e-7,5e-7],[5e-7,-5e-7]],[[-5e-7,5e-7],[5e-7,-5e-7]],1.0)["enerji_orani"]!=0.0:return False
        if f([[2.0,0.0],[2.0,0.0]],[[2.0,0.0],[0.0,2.0]],1.0)["savunma_basarili"] is not False:return False
        if f([[2.0,0.0]]*5,[[2.0,0.0]]*4+[[0.0,2.0]],1.0)["savunma_basarili"] is not True:return False
        for bad in ((None,b,0.25),(a,None,0.25),([[1.0,2.0]],[[1.0,2.0]],0.25),([[1.0],[2.0]],[[1.0],[2.0]],0.25),(a,b[:-1],0.25),([[1.0,2.0],[3.0]],[[1.0,2.0],[3.0,4.0]],0.25),(a,b,0.0),(a,b,1.2),(a,b,True),(a,b,float("nan")),([[True,1.0],[1.0,2.0]],[[1.0,1.0],[1.0,2.0]],0.25)):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
kontrol(sinama3(extraction_savunma_raporu),"argmax korunma, merkezlenmiş enerji oranı, savunma kararı ve geçersiz girdi")
for ad,mut in [("yalnız argmax",lambda a,b,e:dict(extraction_savunma_raporu(a,b,e),savunma_basarili=extraction_savunma_raporu(a,b,e)["argmax_korunma"]>=0.8)),("hep başarılı",lambda a,b,e:dict(extraction_savunma_raporu(a,b,e),savunma_basarili=True)),("enerji sıfır",lambda a,b,e:dict(extraction_savunma_raporu(a,b,e),enerji_orani=0.0))]:
    kontrol(not sinama3(mut),"mutant reddedildi: "+ad)
# farksal tarama (final)
import importlib as _il
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_R = _il.import_module('sandbox.ai_gercek_ai_savunma_40')
for _ad, _ref, _taban, _toh in (
    ('topk_logit_kirp', 'referans_topk', ([4.2, 1.8, -0.5, 3.1, -2.0], 2, -10.0), 3294),
    ('logit_nicemle_gurultu', 'referans_nicemle', ([4.2, 1.8, -0.5, 3.1, -2.0], 0.5, [0.04, -0.08, 0.02, -0.03, 0.05]), 3935),
    ('extraction_savunma_raporu', 'referans_rapor', ([[5.0, 2.0, -1.0, -3.0], [1.0, 6.0, -2.0, -4.0], [-2.0, 1.0, 5.5, -3.5], [-3.0, -1.0, 2.0, 6.5]], [[5.0, 1.9, -1.0, -2.9], [1.0, 5.9, -2.0, -3.9], [-2.0, 1.0, 5.4, -3.4], [-3.0, -1.0, 2.0, 6.4]], 0.25), 4384),
):
    _t, _g = _ff(need(_ad), getattr(_R, _ref), _taban, tohum=_toh)
    kontrol(_t, "farksal tarama (" + _ad + "): bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
if not all(checks):stop()
from sandbox import ai_gercek_ai_savunma_40 as D
try:r=D.deney(topk_logit_kirp,logit_nicemle_gurultu,extraction_savunma_raporu)
except ai_lab.GercekLabYok as e:
    kontrol(False,"gerçek deney yok: "+str(e));stop()
kontrol(r["topk_ayni"],"gerçek logitlerde top-k kırpma bağımsız referansla aynı")
kontrol(r["nicemle_ayni"],"gerçek logitlerde gürültülü nicemleme bağımsız referansla aynı")
kontrol(r["rapor_ayni"],"gerçek matriste savunma raporu bağımsız referansla aynı")
kontrol(r["rapor"]["argmax_korunma"]>=0.9,"700 gerçek API yanıtında argmax (kullanıcıya dönen token) en az %90 korundu")
kontrol(r["rapor"]["savunma_basarili"],"savunma raporu: argmax korundu ve merkezli enerji eşiğin altında")
kontrol(r["saldiri_savunmasiz"]["tahmini_boyut"]==r["gercek_gizli_boyut"] and r["saldiri_savunmasiz"]["altuzay_kosinus_min"]>0.999,"savunmasız API'de saldırı gerçek gizli boyutu (576) ve son katman altuzayını kurtardı")
kontrol(r["saldiri_savunmali"]["tahmini_boyut"]!=r["gercek_gizli_boyut"],"savunmadan sonra saldırının tahmini gizli boyutu yanlış")
kontrol(r["saldiri_savunmali"]["ucurum_gercek_boyutta"]<10,"savunmadan sonra gerçek gizli boyuttaki spektral uçurum kayboldu")
kontrol(r["saldiri_savunmali"]["altuzay_kosinus_min"]<0.1,"savunmadan sonra kurtarılan altuzay gerçek lm_head ile örtüşmüyor")
ai_lab.kanit_yaz("ai-savunma-40-kabul",{"kaynak":"gercek","kabul":all(checks),"ders":"ai-savunma-40","deney":r})
```
```solution
import ai_lab
import math
def topk_logit_kirp(logitler,k,taban_deger):
    if not isinstance(logitler,list) or len(logitler)<2:raise ValueError("logitler")
    for v in logitler+[taban_deger]:
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError("sayı")
    if isinstance(k,bool) or not isinstance(k,int) or not 1<=k<=len(logitler):raise ValueError("k")
    sec=set(sorted(range(len(logitler)),key=lambda i:(-logitler[i],i))[:k])
    return [float(v) if i in sec else float(taban_deger) for i,v in enumerate(logitler)]
def logit_nicemle_gurultu(logitler,adim_boyutu,gurultu_vektoru):
    if not isinstance(logitler,list) or not isinstance(gurultu_vektoru,list) or len(logitler)<2 or len(logitler)!=len(gurultu_vektoru):raise ValueError("boyut")
    for v in logitler+gurultu_vektoru+[adim_boyutu]:
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError("sayı")
    if adim_boyutu<=0:raise ValueError("adim")
    return [round(round((a+b)/adim_boyutu)*adim_boyutu,8) for a,b in zip(logitler,gurultu_vektoru)]
def extraction_savunma_raporu(orijinal_logitler,korunan_logitler,tekil_oran_esik):
    if not isinstance(orijinal_logitler,list) or not isinstance(korunan_logitler,list) or len(orijinal_logitler)<2 or len(orijinal_logitler)!=len(korunan_logitler):raise ValueError("matris")
    if isinstance(tekil_oran_esik,bool) or not isinstance(tekil_oran_esik,(int,float)) or not math.isfinite(tekil_oran_esik) or not 0<tekil_oran_esik<=1:raise ValueError("esik")
    d=len(orijinal_logitler[0]) if isinstance(orijinal_logitler[0],list) else 0
    if d<2:raise ValueError("sutun")
    for a,b in zip(orijinal_logitler,korunan_logitler):
        if not isinstance(a,list) or not isinstance(b,list) or len(a)!=d or len(b)!=d:raise ValueError("satir")
        for v in a+b:
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError("hucre")
    n=len(orijinal_logitler)
    kor=0;l2=0.0
    for a,b in zip(orijinal_logitler,korunan_logitler):
        if max(range(d),key=lambda j:a[j])==max(range(d),key=lambda j:b[j]):kor+=1
        l2+=math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))
    oa=[sum(orijinal_logitler[i][j] for i in range(n))/n for j in range(d)]
    ob=[sum(korunan_logitler[i][j] for i in range(n))/n for j in range(d)]
    ea=sum((orijinal_logitler[i][j]-oa[j])**2 for i in range(n) for j in range(d))
    eb=sum((korunan_logitler[i][j]-ob[j])**2 for i in range(n) for j in range(d))
    oran=eb/ea if ea>1e-12 else 0.0
    ak=kor/n
    return {"argmax_korunma":ak,"ortalama_l2_sapma":l2/n,"enerji_orani":oran,"savunma_basarili":bool(ak>=0.8 and oran<=tekil_oran_esik)}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_40 as D
    D.goster(topk_logit_kirp,logit_nicemle_gurultu,extraction_savunma_raporu)
```
```hint
Üç işlevi aynen birleştir. Korunan matrisin SVD spektrumundaki daralmayı orijinal spektrumla karşılaştır.
```
:::

::: anlat Sınır
Bu ders gerçek SmolLM2-135M API'sinde Carlini SVD saldırısının top-k kırpma ve quantization ile bastırıldığını gösterir; ancak `logit_bias` ile kırpma penceresini kaydıran sorguları, aynı istemi çok kez sorup gürültüyü ortalamayı ve saldırganın yalnızca etiketleri (`hard-label`) kullanarak milyonlarca adaptif sorguyla yürüttüğü model kopyalamayı tek başına durdurmaz. Bulgular tek model ve tek sorgu dağılımı içindir.
:::


::: anlat Bunu iki dakikada nasıl anlatırsın?
Tam logit matrisi son katmanın düşük boyutlu yapısını taşır. Top-k masking bu doğrusal gözlem haritasını değiştirir; quantization ve gürültü hassas farkları bozar. Fakat dönüşümün ardından rank veya toplam enerji artabilir; yalnız enerji azalmasıyla extraction durdu deme. Argmax korunması fayda ölçütü, altuzay geri kazanımı saldırı ölçütüdür. Noise eklemek epsilon/delta bütçesi ve sensitivity hesabı olmadan differential privacy garantisi değildir.

Önkoşul ve yol köprüsü: ai-saldiri-57 SVD saldırısı.

| Yaygın yanlış | Mekanizma ve sınır |
|---|---|
| Gürültü varsa model extraction imkânsızdır | Adaptif sorgu ve tekrar ortalaması ayrıca sınanır |

Dinleyiciye sor: Savunma güvenlik metriğini iyileştirirken meşru kullanıma ne kaybettirebilir? Ham çıktı ve ölçüm paydalarıyla cevapla.
:::


::: anlat Birincil kaynak ve deney sınırı
[Carlini vd., Stealing Part of a Production Language Model](https://arxiv.org/abs/2403.06634): Son katman extraction için birincil çalışma. Dersin savunma sonucu tek model/sorgu dağılımı ve dönüşüm altında ayrıca ölçülür. Çalışan sürüm ve gerçek sonuç kanıtta kayıtlıdır.
:::
