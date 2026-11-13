---
id: ai-guvence-39
title: Üyelik Çıkarımının İstatistiği · Likelihood Ratio ve Güven Aralığı
summary: Logit güven dönüşümünü, örnek başına Gaussian likelihood ratio testini ve Clopper-Pearson aralığını yaz; gerçek shadow modellerle loss eşiği ve LiRA tarzı testi aynı örneklerde düşük FPR'de karşılaştır.
esleme: ai-guvence-17, ai-saldiri-48, ai-savunma-39
timeout: 60
---

::: anlat Rakam değil, test ve belirsizlik
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Aynı model, aynı örnekler: loss eşiği rastgeleden ayırt edilemezken örnek başına likelihood ratio belirgin bir sızıntı bulabilir | İlk üç görev: `veri/mi.json` içindeki **sentetik** değerler. Final: `load_digits`, etiketlerin bir kısmı bozulmuş hedef MLP, GPU, 16 shadow model | LiRA'nın tam yeniden üretimi değildir; gerçek bir modelin gizlilik riskini söylemez. Hedef bilerek ezberletilmiştir |
| Küçük bir oran tek başına anlamsızdır; güven aralığı olmadan iki sayı karşılaştırılamaz | Clopper-Pearson ile TPR ve gerçekleşen FPR aralıkları | Çoklu karşılaştırma düzeltmesi yapmaz; tek koşudan genel bir oran çıkarmaz |

> [!NOT]
> Görevler `veri/mi.json` dosyasını okur; dosya sentetiktir. Setup her Çalıştır/Kontrol Et adımında geçici kopya kurar; değişiklikler taşınmaz, **kalıcılık yoktur**. Ekranda ayrı dosya görüntüleyici yoktur; içeriği görmek için `print` kullan. Gizli testler ayrıdır. Final yeni model indirmez, yalnız küçük modelleri GPU'da eğitir ve belleği serbest bırakır.

ai-guvence-17 ROC ve AUC üzerinden üyelik ölçer, ai-saldiri-48 LoRA üzerinde loss farkını gösterir. Bu dersin sorusu: **neden loss eşiği yetersiz kalır, en güçlü test nedir, bir oranın belirsizliği ne kadardır?**

**Hipotez testi olarak üyelik.** `H1`: örnek eğitimdeydi. `H0`: değildi. Neyman-Pearson lemması (1933) belirli bir yanlış pozitif oranında **en güçlü testin likelihood ratio** olduğunu söyler: `Λ(x) = p(x|H1) / p(x|H0)`. Sabit bir eşiğin yanılması bundan gelir: basit eşik bütün örneklere aynı dağılım varsayar.

**Örnek başına dağılım.** Carlini vd. (2022, LiRA) buradan yola çıkar. Bazı örnekler doğası gereği kolaydır; hiçbir modelin eğitimine girmese de düşük loss alır. Bir örnek için `p(x|H1)` ve `p(x|H0)` dağılımlarını öğrenmek için shadow model eğitilir: bazıları o örnekle, bazıları onsuz. Örnek başına Gaussian uydurulur ve log oran hesaplanır. Bu, ai-saldiri-48'deki kalibrasyonun istatistiksel olarak tam hâlidir.

**Neden logit güven?** Güven değeri `p` 0 ile 1 arasına sıkışmıştır; özellikle 1'e yakın yığılır ve Gaussian değildir. `φ = log(p/(1-p))` değeri çok daha simetrik dağılır (LiRA da bu ölçeği kullanır). Doğrudan `p/(1-p)` yazmak `p=1` için sıfıra bölme hatası verir; bu yüzden `p` önce `[1e-12, 1-1e-12]` aralığına çekilir.

**Varyans tabanı neden gerekli?** Shadow sayısı azsa bir örneğin logitleri neredeyse aynı çıkabilir: varyans 0'a yaklaşır, Gaussian yoğunluğu patlar. Tabansız bir test tek bir sayısal rastlantıya büyük güven atar. Bu dersteki `taban` bunu sınırlar; ayrıca dağılım örnekten kestirildiği için paydada `n-1` kullanılır.

**Clopper-Pearson.** 400 üye-olmayanda 20 yanlış pozitif, `0.05` demektir ama kesin değildir. Normal yaklaşım (Wald, `p ± 1.96√(p(1-p)/n)`) bu dersin sık yapılan hatasıdır: `k=0` iken aralığı `[0,0]` verir, "hiç sızıntı olamaz" der. Clopper-Pearson (1934) Binomial'i doğrudan kullanır:

- Alt sınır `p`: `P(X≥k|p) = α/2`
- Üst sınır `p`: `P(X≤k|p) = α/2`

Binomial'in kapalı tersi yok ama monoton olduğu için ikiye bölme yeterlidir. `k=0` iken alt sınır 0, `k=n` iken üst sınır 1 tanım gereğidir. Düşük FPR'de aralık özellikle önemlidir: çok az olay vardır. Ölçülen "FPR≤0.1%" 1000 üye-olmayanla 1 olaydır.

**Saldırgan ne dener?** Elinde benzer veri ve model mimarisi varsa kendi shadow modellerini eğitir ve hedefin çıktısını örnek bazında test eder. Sorgu başına maliyet küçüktür, hazırlık maliyeti shadow eğitimidir.

**Savunma neden kırılır?** "Ortalama AUC 0.6, sızıntı düşük" raporu yanıltır. Hem AUC düşük FPR bölgesini gizler hem de zayıf bir test, zayıf test olduğunu söylemez. Sonuç: bir gizlilik iddiası hangi saldırıya, hangi FPR'ye ve hangi güven aralığına karşı olduğunu yazmalıdır. Düzenleyici veya denetçi bu üçünü sormalıdır.

**Görev 1'de sık tuzaklar:** Kırpmayı unutmak `p=0` ve `p=1` için hata verir; bu değerler float32 softmax'ta gerçekten çıkar (bkz. ai-guvence-36).

Kaynaklar: [Carlini vd. 2022 · LiRA](https://arxiv.org/abs/2112.03570), [Shokri vd. 2017](https://arxiv.org/abs/1610.05820), [Yeom vd. 2018](https://arxiv.org/abs/1709.01604). Bu dersteki bütün sayılar yalnız yerel kanıttan gelir.

Köprü: ai-guvence-17 ve ai-saldiri-48 üyelik ölçümü; ai-savunma-39 unlearning sonrası doğrulama için aynı istatistik gerekir.
:::

::: tahmin Güven değeri ne kadar sıkışık?
Çıktıyı tahmin et, sonra Çalıştır ile karşılaştır.
```python
import math
for p in (0.5, 0.99, 0.999999):
    print(round(math.log(p) - math.log(1 - p), 3))
```
???
```cikti
0.0
4.595
13.816
```
Tahmininle gerçek çıktı arasındaki farkı tezgâhta yorum satırı olarak yaz: `p` 0.99'dan 0.999999'a çok az büyürken logit neden bu kadar büyüdü? Bir model bu aralıkta ne kadar bilgi taşıyor olabilir? Sonra üç kusurlu başlangıç kodunu çalıştır ve neyi yanlış yaptıklarını önce kendin teşhis et; açıklama çözümün ardından gelir.
:::

::: gorev 1 · Kırpılmış logit güven
`logit_guven(p)`: `p` bool olmayan, sonlu ve `0<=p<=1` olan sayı. `q=min(max(p,1e-12),1-1e-12)`. `log(q)-log(1-q)` döndür. Geçersiz girdide `ValueError`.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-39")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def logit_guven(p):
    return math.log(p/(1-p))

from ai_guvence_veri import json_yukle
v=json_yukle("veri/mi.json")
for p in v["guvenler"]:
    print(p,logit_guven(p))
```
```test
def sinama1(f):
    import math
    try:
        if f(.5)!=0.0 or abs(f(.75)-math.log(3))>1e-12 or abs(f(.25)+math.log(3))>1e-12:return False
        q=1-1e-12;u=math.log(q)-math.log(1-q);w=math.log(1e-12)-math.log(1-1e-12)
        if f(1)!=u or f(1.0)!=u or f(0)!=w or f(0.0)!=w:return False
        if f(1e-13)!=w or f(1-1e-13)!=u:return False
        if abs(f(1e-6)-(math.log(1e-6)-math.log(1-1e-6)))>1e-12:return False
        for p in (.1,.3,.6,.9,.999):
            if abs(f(p)+f(1-p))>1e-9:return False
        for bad in (None,"a",True,False,-.1,1.1,float("nan"),float("inf"),[.5]):
            try:f(bad);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama1(logit_guven),"kırpma, simetri ve geçersiz girdi")
for ad,mut in [("kırpma yok",lambda p:logit_guven(.5) if p in (0,1) else logit_guven(p)),("işaret ters",lambda p:-logit_guven(p)),("sabit",lambda p:0.0)]:
    ok(not sinama1(mut),"mutant reddedildi: "+ad)
```
```solution
import math
def logit_guven(p):
    if isinstance(p,bool) or not isinstance(p,(int,float)) or not math.isfinite(p) or not 0<=p<=1:raise ValueError("p")
    q=min(max(p,1e-12),1-1e-12)
    return math.log(q)-math.log(1-q)

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    v=json_yukle("veri/mi.json")
    for p in v["guvenler"]:
        print(p,logit_guven(p))
```
```hint
Önce [1e-12, 1-1e-12] aralığına kırp; bölme yerine iki logaritmanın farkını al.
```
:::

::: anlat Kolay örnek neden artık yanıltmaz?
`veri/mi.json` içindeki `kolay_ornek` için `ic` ve `dis` dağılımları neredeyse aynıdır: model o örneği üye olsun olmasın iyi bilir. Sabit eşik onu "üye" sayardı; log oran ise yaklaşık 0 verir. `zor_uye_degil` tam tersi durumdur: değeri `dis` dağılımına uyar ve negatif log oran alır. Yön: **pozitif, üyeliği destekler.**

Gaussian log yoğunluğunda `-½log(2πσ²)` terimi önemlidir: iki varyans farklıysa birbirini götürmez. Atlanırsa dar dağılımın yoğunluk avantajı kaybolur.

**Görev 2'de sık tuzaklar:** Popülasyon varyansı (`n`) örnekten kestirimi küçültür. Taban yoksa sabit dağılım sıfıra bölme üretir. `ic` ve `dis` yönünü ters çevirmek bütün skorları tersine döndürür.
:::

::: gorev 2 · Örnek başına log likelihood ratio
`log_lr(x,ic,dis,taban)`: `x`, `taban` bool olmayan sonlu sayı, `taban>0`. `ic`, `dis` en az iki elemanlı liste; bool olmayan sonlu sayılar. Her liste için `m` ortalama, `s²=max(Σ(v-m)²/(n-1),taban)`. `log N(x;m,s²)=-½log(2πs²)-(x-m)²/(2s²)`. `log N(x;ic)-log N(x;dis)` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-39")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def log_lr(x,ic,dis,taban):
    def uyum(l):
        m=sum(l)/len(l)
        return m,sum((v-m)**2 for v in l)/len(l)
    def log_n(v,m,s2):
        return -(v-m)**2/(2*s2)
    mi,vi=uyum(ic)
    md,vd=uyum(dis)
    return log_n(x,md,vd)-log_n(x,mi,vi)

from ai_guvence_veri import json_yukle
v=json_yukle("veri/mi.json")
for o in v["ornekler"]:
    try:
        print(o["ad"],log_lr(o["x"],o["ic"],o["dis"],v["taban"]))
    except ZeroDivisionError as e:
        print(o["ad"],"HATA:",e)
```
```test
def sinama2(f):
    import copy,math,random
    def _n(v,m,s):return -.5*math.log(2*math.pi*s)-(v-m)**2/(2*s)
    def _r(x,a,b,t):
        def u(l):
            m=sum(l)/len(l);return m,max(sum((v-m)**2 for v in l)/(len(l)-1),t)
        p,q=u(a),u(b);return _n(x,*p)-_n(x,*q)
    try:
        a=[1.0,3.0];b=[-1.0,1.0];old=(list(a),list(b))
        if abs(f(0.0,a,b,1e-4)+1.0)>1e-12 or (a,b)!=old:return False
        if abs(f(2.0,a,b,1e-4)-1.0)>1e-12:return False
        if abs(f(1.0,[1.0,1.0],[0.0,2.0],.25)-.5*math.log(8))>1e-12:return False
        if abs(f(1.0,[0.0,2.0],[1.0,1.0],.25)+.5*math.log(8))>1e-12:return False
        if abs(f(1.0,[1.0,1.0],[1.0,1.0],.25))>1e-12:return False
        if abs(f(1.0,[0.0,2.0],[0.0,2.0],4.0))>1e-12 or abs(f(9.0,[0.0,2.0],[5.0,7.0],4.0)-((-(9-1)**2+(9-6)**2)/8))>1e-12:return False
        if abs(f(0.0,[0.0,0.0,3.0],[0.0,1.0],.25)-_r(0.0,[0.0,0.0,3.0],[0.0,1.0],.25))>1e-12:return False
        rng=random.Random(39)
        for _ in range(25):
            u=[rng.gauss(2,1) for _ in range(rng.randint(2,9))];w=[rng.gauss(-1,2) for _ in range(rng.randint(2,9))];x=rng.uniform(-4,4);t=rng.choice([1e-4,.5,2.0])
            if abs(f(x,list(u),list(w),t)-_r(x,u,w,t))>1e-9:return False
        g=[1.0,2.0]
        for bad in ((None,g,g,.1),("a",g,g,.1),(True,g,g,.1),(float("nan"),g,g,.1),(0.0,None,g,.1),(0.0,g,None,.1),(0.0,[1.0],g,.1),(0.0,g,[1.0],.1),(0.0,(1.0,2.0),g,.1),(0.0,g,(1.0,2.0),.1),(0.0,[True,1.0],g,.1),(0.0,g,[float("inf"),1.0],.1),(0.0,["a",1.0],g,.1),(0.0,g,g,0),(0.0,g,g,-1),(0.0,g,g,True),(0.0,g,g,float("nan")),(0.0,g,g,"a")):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama2(log_lr),"n-1 varyans, taban, yön, normal sabiti ve geçersiz girdi")
for ad,mut in [("yön ters",lambda x,a,b,t:-log_lr(x,a,b,t)),("sabit sıfır",lambda x,a,b,t:0.0),("taban yok say",lambda x,a,b,t:log_lr(x,a,b,1e-9))]:
    ok(not sinama2(mut),"mutant reddedildi: "+ad)
```
```solution
import math
def log_lr(x,ic,dis,taban):
    for v in (x,taban):
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError("sayı")
    if taban<=0:raise ValueError("taban")
    for l in (ic,dis):
        if not isinstance(l,list) or len(l)<2:raise ValueError("liste")
        for v in l:
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError("sayı")
    def uyum(l):
        m=sum(l)/len(l)
        return m,max(sum((v-m)**2 for v in l)/(len(l)-1),taban)
    def log_n(v,m,s2):
        return -0.5*math.log(2*math.pi*s2)-(v-m)**2/(2*s2)
    mi,vi=uyum(ic)
    md,vd=uyum(dis)
    return log_n(x,mi,vi)-log_n(x,md,vd)

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    v=json_yukle("veri/mi.json")
    for o in v["ornekler"]:
        print(o["ad"],log_lr(o["x"],o["ic"],o["dis"],v["taban"]))
```
```hint
Bir uyum yardımcısı (ortalama ve tabanlı varyans), bir log yoğunluk yardımcısı yaz. Sonuç: içeri eksi dışarı.
```
:::

::: anlat Binomial'i tersine çevirmek
`kdf(s,p)=Σ_{i≤s} C(n,i)pⁱ(1-p)ⁿ⁻ⁱ`. Büyük `n` için taşmamak adına log uzayında `lgamma` ile hesaplanır. Kuyruk olasılığı `p` ile monotondur, bu yüzden ikiye bölme çalışır: alt sınır için `1-kdf(k-1,p)<α/2` iken yukarı git, üst sınır için `kdf(k,p)>=α/2` iken yukarı git. 50 adım double hassasiyetine yeter ve `p`'yi tam 1'e yuvarlatmaz.

**Görev 3'te sık tuzaklar:** Wald formülü `k=0` iken sıfır genişlikli aralık verir. `guven` parametresini yok sayıp 1.96 gömmek başka seviyeleri bozar. `k=0` ve `k=n` özel durumdur, ayrı ele alınmazsa `log(0)` hatası çıkar.
:::

::: gorev 3 · Clopper-Pearson aralığı
`clopper_pearson(k,n,guven)`: `k`, `n` bool olmayan int, `n>=1`, `0<=k<=n`. `guven` bool olmayan sonlu sayı, `0<guven<1`. `a=(1-guven)/2`. Alt sınır `k=0` ise 0, değilse `P(X≥k|p)=a` kökü. Üst sınır `k=n` ise 1, değilse `P(X≤k|p)=a` kökü. Kökler ikiye bölme ile bulunur. `{"oran":k/n,"alt":..,"ust":..}` döndür. Geçersiz girdide `ValueError`.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-39")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def clopper_pearson(k,n,guven):
    p=k/n
    e=1.96*math.sqrt(p*(1-p)/n)
    return {"oran":p,"alt":max(0.0,p-e),"ust":min(1.0,p+e)}

from ai_guvence_veri import json_yukle
v=json_yukle("veri/mi.json")
for k,n in v["sayimlar"]:
    print(k,"/",n,clopper_pearson(k,n,v["guven"]))
```
```test
def sinama3(f):
    import math
    def y(a,b):return abs(a-b)<1e-5
    try:
        r=f(0,10,.95)
        if r["oran"]!=0.0 or r["alt"]!=0.0 or not y(r["ust"],1-.025**(1/10)) or set(r)!={"oran","alt","ust"}:return False
        r=f(10,10,.95)
        if r["oran"]!=1.0 or r["ust"]!=1.0 or not y(r["alt"],.025**(1/10)):return False
        r=f(5,10,.95)
        if r["oran"]!=.5 or not y(r["alt"],0.187086) or not y(r["ust"],0.812914):return False
        r=f(0,50,.9)
        if not y(r["ust"],1-.05**(1/50)):return False
        r=f(1,1,.9)
        if r["ust"]!=1.0 or not y(r["alt"],.05):return False
        r=f(0,1,.9)
        if r["alt"]!=0.0 or not y(r["ust"],.95):return False
        r=f(1,2,.5)
        if not y(r["alt"],1-math.sqrt(.75)) or not y(r["ust"],math.sqrt(.75)):return False
        for k,n in ((3,20),(7,40),(1,100),(99,100)):
            a=f(k,n,.95);b=f(n-k,n,.95)
            if not y(a["alt"],1-b["ust"]) or not y(a["ust"],1-b["alt"]) or not a["alt"]<k/n<a["ust"]:return False
            c=f(k,n,.8)
            if not (a["alt"]<c["alt"] and c["ust"]<a["ust"]):return False
        for bad in ((None,1,.9),(1,None,.9),(True,1,.9),(1,True,.9),(1.0,2,.9),(1,2.0,.9),(0,0,.9),(1,0,.9),(-1,2,.9),(3,2,.9),(1,2,0),(1,2,1),(1,2,-.1),(1,2,1.5),(1,2,True),(1,2,float("nan")),(1,2,"a")):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama3(clopper_pearson),"k=0 ve k=n, bilinen aralık, simetri ve geçersiz girdi")
for ad,mut in [("sıfır genişlik",lambda k,n,g:{"oran":k/n,"alt":k/n,"ust":k/n}),("güven yok say",lambda k,n,g:clopper_pearson(k,n,.95)),("alt üst ters",lambda k,n,g:(lambda r:dict(r,alt=r["ust"],ust=r["alt"]))(clopper_pearson(k,n,g)))]:
    ok(not sinama3(mut),"mutant reddedildi: "+ad)
```
```solution
import math
def clopper_pearson(k,n,guven):
    if isinstance(k,bool) or isinstance(n,bool) or not isinstance(k,int) or not isinstance(n,int) or n<1 or not 0<=k<=n:raise ValueError("sayım")
    if isinstance(guven,bool) or not isinstance(guven,(int,float)) or not math.isfinite(guven) or not 0<guven<1:raise ValueError("güven")
    a=(1-guven)/2
    def kdf(s,p):
        return sum(math.exp(math.lgamma(n+1)-math.lgamma(i+1)-math.lgamma(n-i+1)+i*math.log(p)+(n-i)*math.log(1-p)) for i in range(s+1))
    def ikiye(devam):
        lo,hi=0.0,1.0
        for _ in range(50):
            m=(lo+hi)/2
            if devam(m):lo=m
            else:hi=m
        return (lo+hi)/2
    alt=0.0 if k==0 else ikiye(lambda p:1-kdf(k-1,p)<a)
    ust=1.0 if k==n else ikiye(lambda p:kdf(k,p)>=a)
    return {"oran":k/n,"alt":alt,"ust":ust}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    v=json_yukle("veri/mi.json")
    for k,n in v["sayimlar"]:
        print(k,"/",n,clopper_pearson(k,n,v["guven"]))
```
```hint
Önce log uzayında Binomial KDF yaz. Sonra iki monoton kök için aynı ikiye bölme yardımcısını kullan. k=0 ve k=n ayrı.
```
:::

::: anlat Hata vitrini · çalışmış yanlış rapor
Yazar, kusurlu başlangıç kodlarını görünür sentetik veriyle gerçekten çalıştırdı ve sonucu `outputs/yeni-ai-guvence-39/gorunur-run-1.json` dosyasına kaydetti. `0/50` için kusurlu Wald kodu `[0.000, 0.000]` verir; doğru Clopper-Pearson `[0.000, 0.071]` verir. `zor_uye` örneğinde doğru log oran `73.83`, kusurlu kod `-98.25` verir: yön terstir.

Bu kaydedilmiş bir hesaplama çıktısıdır, model yanıtı değildir ve veri sentetiktir. "50 denemede sızıntı yok, risk sıfır" cümlesi kusurlu aralığa dayanıyorsa neden yanlıştır? Kendi cümlenle açıkla. Gerçek finaldeki ölçüm ayrıca üretilir; bu sayılar onun yerine konmaz.
:::

::: anlat Gerçek deney: aynı model, iki test
Final `load_digits`'ten rastgele 800 örnek seçer ve her koşuda etiketlerin küçük bir kısmını bozar. Bu bilinçli bir tercihtir: bozuk etiketleri öğrenmek ezberdir, bu yüzden hedef model üyelik sızıntısı üretir. Küçük görev gürültüsüz hâlde neredeyse hiç sızıntı vermez.

Hedef MLP havuzun yarısıyla eğitilir. Ardından 16 shadow model, her biri rastgele bir yarıyla eğitilir ve her örnek için üye olduğu ve olmadığı modellerdeki logit güven listeleri toplanır. **Senin `logit_guven`, `log_lr` ve `clopper_pearson`** işlevlerin bu gerçek değerlere uygulanır.

İki skor karşılaştırılır: küresel eşik (hedefin logit güveni) ve örnek başına likelihood ratio. TPR, FPR≤0.05 bütçesinde ölçülür; TPR ile gerçekleşen FPR'ye aralık verilir.

Kabul; işlevlerinin referansla aynı olmasına ve gerçekten üye/üye-değil örneklerin ölçülmesine bağlıdır. **LiRA'nın kazanması kabul şartı değildir.** Bazı koşularda aralıklar çakışabilir.

**Kanıt dosyasını oku:** Soru 1: `sonuc.kayip_esigi` için TPR aralığı FPR'yi içeriyor mu? O zaman ne söyleyebilirsin? Soru 2: `lira` aralığı ile karşılaştır. Fark gerçek mi, tek koşu mu? İkinci kez çalıştırıp gör. Soru 3: AUC farkı ile TPR farkı aynı büyüklükte mi? Bu, hangi metriğin neden raporlanması gerektiğini nasıl değiştirir? Cevabını tezgâhta yorum olarak yaz; otomatik test bu serbest açıklamayı puanlamaz.
:::

::: gorev Gerçek deney · Shadow modellerle loss eşiği ve likelihood ratio
Önceki üç görevin `logit_guven`, `log_lr` ve `clopper_pearson` işlevlerini birleştir. Çalıştır gerçek ölçümü gösterir; Kontrol Et önce üç sözleşmeyi gizli verilerle sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
ortam: gpu
timeout: 240
```
```starter
import ai_lab
import math
def logit_guven(p):
    return math.log(p/(1-p))
def log_lr(x,ic,dis,taban):
    def uyum(l):
        m=sum(l)/len(l)
        return m,sum((v-m)**2 for v in l)/len(l)
    def log_n(v,m,s2):
        return -(v-m)**2/(2*s2)
    mi,vi=uyum(ic)
    md,vd=uyum(dis)
    return log_n(x,md,vd)-log_n(x,mi,vi)
def clopper_pearson(k,n,guven):
    p=k/n
    e=1.96*math.sqrt(p*(1-p)/n)
    return {"oran":p,"alt":max(0.0,p-e),"ust":min(1.0,p+e)}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_39 as D
    D.goster(logit_guven,log_lr,clopper_pearson)
```
```test
import ai_lab,math
checks=[]
def kontrol(x,m):checks.append(bool(x));ok(x,m)
issues=ai_lab.kod_denetimi(src,('referans_logit', 'referans_lr', 'referans_cp', 'kanit_yaz', '_yakin'),izin=())
kontrol(not issues,"kopya/yama/dinamik kod yok: "+str(issues))
if issues:stop()
logit_guven=need("logit_guven")
log_lr=need("log_lr")
clopper_pearson=need("clopper_pearson")
def sinama1(f):
    import math
    try:
        if f(.5)!=0.0 or abs(f(.75)-math.log(3))>1e-12 or abs(f(.25)+math.log(3))>1e-12:return False
        q=1-1e-12;u=math.log(q)-math.log(1-q);w=math.log(1e-12)-math.log(1-1e-12)
        if f(1)!=u or f(1.0)!=u or f(0)!=w or f(0.0)!=w:return False
        if f(1e-13)!=w or f(1-1e-13)!=u:return False
        if abs(f(1e-6)-(math.log(1e-6)-math.log(1-1e-6)))>1e-12:return False
        for p in (.1,.3,.6,.9,.999):
            if abs(f(p)+f(1-p))>1e-9:return False
        for bad in (None,"a",True,False,-.1,1.1,float("nan"),float("inf"),[.5]):
            try:f(bad);return False
            except ValueError:pass
        return True
    except Exception:return False
kontrol(sinama1(logit_guven),"kırpma, simetri ve geçersiz girdi")
for ad,mut in [("kırpma yok",lambda p:logit_guven(.5) if p in (0,1) else logit_guven(p)),("işaret ters",lambda p:-logit_guven(p)),("sabit",lambda p:0.0)]:
    kontrol(not sinama1(mut),"mutant reddedildi: "+ad)
def sinama2(f):
    import copy,math,random
    def _n(v,m,s):return -.5*math.log(2*math.pi*s)-(v-m)**2/(2*s)
    def _r(x,a,b,t):
        def u(l):
            m=sum(l)/len(l);return m,max(sum((v-m)**2 for v in l)/(len(l)-1),t)
        p,q=u(a),u(b);return _n(x,*p)-_n(x,*q)
    try:
        a=[1.0,3.0];b=[-1.0,1.0];old=(list(a),list(b))
        if abs(f(0.0,a,b,1e-4)+1.0)>1e-12 or (a,b)!=old:return False
        if abs(f(2.0,a,b,1e-4)-1.0)>1e-12:return False
        if abs(f(1.0,[1.0,1.0],[0.0,2.0],.25)-.5*math.log(8))>1e-12:return False
        if abs(f(1.0,[0.0,2.0],[1.0,1.0],.25)+.5*math.log(8))>1e-12:return False
        if abs(f(1.0,[1.0,1.0],[1.0,1.0],.25))>1e-12:return False
        if abs(f(1.0,[0.0,2.0],[0.0,2.0],4.0))>1e-12 or abs(f(9.0,[0.0,2.0],[5.0,7.0],4.0)-((-(9-1)**2+(9-6)**2)/8))>1e-12:return False
        if abs(f(0.0,[0.0,0.0,3.0],[0.0,1.0],.25)-_r(0.0,[0.0,0.0,3.0],[0.0,1.0],.25))>1e-12:return False
        rng=random.Random(39)
        for _ in range(25):
            u=[rng.gauss(2,1) for _ in range(rng.randint(2,9))];w=[rng.gauss(-1,2) for _ in range(rng.randint(2,9))];x=rng.uniform(-4,4);t=rng.choice([1e-4,.5,2.0])
            if abs(f(x,list(u),list(w),t)-_r(x,u,w,t))>1e-9:return False
        g=[1.0,2.0]
        for bad in ((None,g,g,.1),("a",g,g,.1),(True,g,g,.1),(float("nan"),g,g,.1),(0.0,None,g,.1),(0.0,g,None,.1),(0.0,[1.0],g,.1),(0.0,g,[1.0],.1),(0.0,(1.0,2.0),g,.1),(0.0,g,(1.0,2.0),.1),(0.0,[True,1.0],g,.1),(0.0,g,[float("inf"),1.0],.1),(0.0,["a",1.0],g,.1),(0.0,g,g,0),(0.0,g,g,-1),(0.0,g,g,True),(0.0,g,g,float("nan")),(0.0,g,g,"a")):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
kontrol(sinama2(log_lr),"n-1 varyans, taban, yön, normal sabiti ve geçersiz girdi")
for ad,mut in [("yön ters",lambda x,a,b,t:-log_lr(x,a,b,t)),("sabit sıfır",lambda x,a,b,t:0.0),("taban yok say",lambda x,a,b,t:log_lr(x,a,b,1e-9))]:
    kontrol(not sinama2(mut),"mutant reddedildi: "+ad)
def sinama3(f):
    import math
    def y(a,b):return abs(a-b)<1e-5
    try:
        r=f(0,10,.95)
        if r["oran"]!=0.0 or r["alt"]!=0.0 or not y(r["ust"],1-.025**(1/10)) or set(r)!={"oran","alt","ust"}:return False
        r=f(10,10,.95)
        if r["oran"]!=1.0 or r["ust"]!=1.0 or not y(r["alt"],.025**(1/10)):return False
        r=f(5,10,.95)
        if r["oran"]!=.5 or not y(r["alt"],0.187086) or not y(r["ust"],0.812914):return False
        r=f(0,50,.9)
        if not y(r["ust"],1-.05**(1/50)):return False
        r=f(1,1,.9)
        if r["ust"]!=1.0 or not y(r["alt"],.05):return False
        r=f(0,1,.9)
        if r["alt"]!=0.0 or not y(r["ust"],.95):return False
        r=f(1,2,.5)
        if not y(r["alt"],1-math.sqrt(.75)) or not y(r["ust"],math.sqrt(.75)):return False
        for k,n in ((3,20),(7,40),(1,100),(99,100)):
            a=f(k,n,.95);b=f(n-k,n,.95)
            if not y(a["alt"],1-b["ust"]) or not y(a["ust"],1-b["alt"]) or not a["alt"]<k/n<a["ust"]:return False
            c=f(k,n,.8)
            if not (a["alt"]<c["alt"] and c["ust"]<a["ust"]):return False
        for bad in ((None,1,.9),(1,None,.9),(True,1,.9),(1,True,.9),(1.0,2,.9),(1,2.0,.9),(0,0,.9),(1,0,.9),(-1,2,.9),(3,2,.9),(1,2,0),(1,2,1),(1,2,-.1),(1,2,1.5),(1,2,True),(1,2,float("nan")),(1,2,"a")):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
kontrol(sinama3(clopper_pearson),"k=0 ve k=n, bilinen aralık, simetri ve geçersiz girdi")
for ad,mut in [("sıfır genişlik",lambda k,n,g:{"oran":k/n,"alt":k/n,"ust":k/n}),("güven yok say",lambda k,n,g:clopper_pearson(k,n,.95)),("alt üst ters",lambda k,n,g:(lambda r:dict(r,alt=r["ust"],ust=r["alt"]))(clopper_pearson(k,n,g)))]:
    kontrol(not sinama3(mut),"mutant reddedildi: "+ad)
if not all(checks):stop()
from sandbox import ai_gercek_ai_guvence_39 as D
try:r=D.deney(logit_guven,log_lr,clopper_pearson)
except ai_lab.GercekLabYok as e:
    kontrol(False,"gerçek deney yok: "+str(e));stop()
kontrol(r["logit_ayni"],"gerçek güvenlerde logit bağımsız hesapla aynı")
kontrol(r["lr_ayni"],"gerçek shadow dağılımlarında log oran bağımsız hesapla aynı")
kontrol(r["cp_ayni"],"gerçek sayımlarda aralık bağımsız hesapla aynı")
kontrol(r["uye"]>0 and r["uye_degil"]>0,"iki grup da gerçekten ölçüldü")
kontrol(r["ic_ort_adet"]>=2 and r["dis_ort_adet"]>=2,"her örnek için yeterli shadow var")
kontrol(r["egitim_dogrulugu"]>r["test_dogrulugu"],"hedef model gerçekten ezberledi")
kontrol(set(r["sonuc"])=={"kayip_esigi","lira"},"iki test aynı örneklerde raporlandı")
ai_lab.kanit_yaz("ai-guvence-39-kabul",{"kaynak":"gercek","kabul":all(checks),"ders":"ai-guvence-39","deney":r})
```
```solution
import ai_lab
import math
def logit_guven(p):
    if isinstance(p,bool) or not isinstance(p,(int,float)) or not math.isfinite(p) or not 0<=p<=1:raise ValueError("p")
    q=min(max(p,1e-12),1-1e-12)
    return math.log(q)-math.log(1-q)
def log_lr(x,ic,dis,taban):
    for v in (x,taban):
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError("sayı")
    if taban<=0:raise ValueError("taban")
    for l in (ic,dis):
        if not isinstance(l,list) or len(l)<2:raise ValueError("liste")
        for v in l:
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError("sayı")
    def uyum(l):
        m=sum(l)/len(l)
        return m,max(sum((v-m)**2 for v in l)/(len(l)-1),taban)
    def log_n(v,m,s2):
        return -0.5*math.log(2*math.pi*s2)-(v-m)**2/(2*s2)
    mi,vi=uyum(ic)
    md,vd=uyum(dis)
    return log_n(x,mi,vi)-log_n(x,md,vd)
def clopper_pearson(k,n,guven):
    if isinstance(k,bool) or isinstance(n,bool) or not isinstance(k,int) or not isinstance(n,int) or n<1 or not 0<=k<=n:raise ValueError("sayım")
    if isinstance(guven,bool) or not isinstance(guven,(int,float)) or not math.isfinite(guven) or not 0<guven<1:raise ValueError("güven")
    a=(1-guven)/2
    def kdf(s,p):
        return sum(math.exp(math.lgamma(n+1)-math.lgamma(i+1)-math.lgamma(n-i+1)+i*math.log(p)+(n-i)*math.log(1-p)) for i in range(s+1))
    def ikiye(devam):
        lo,hi=0.0,1.0
        for _ in range(50):
            m=(lo+hi)/2
            if devam(m):lo=m
            else:hi=m
        return (lo+hi)/2
    alt=0.0 if k==0 else ikiye(lambda p:1-kdf(k-1,p)<a)
    ust=1.0 if k==n else ikiye(lambda p:kdf(k,p)>=a)
    return {"oran":k/n,"alt":alt,"ust":ust}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_39 as D
    D.goster(logit_guven,log_lr,clopper_pearson)
```
```hint
Üç işlevi aynen birleştir. Sonucu okurken tek bir sayıya değil, aralıkların çakışıp çakışmadığına bak.
```
:::

::: anlat Sınır
Bu ders küçük bir MLP ve 16 shadow model ile, etiket gürültüsüyle bilerek ezberletilmiş bir hedefte likelihood ratio testini gösterir; LiRA'nın tam yeniden üretimini, gerçek modellerin gizlilik riskini veya çoklu karşılaştırmaya dayanıklı bir sonucu göstermez.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Olasılık sıkışmasına karşı logit dönüşümü (30 sn).** "$p=0.999$ ile $p=0.9999$ farkı ham olasılıkta görünmezken $\phi(p)=\log(p/(1-p))$ dönüşümü kuyruğu gerçek eksene açar ve `shadow` dağılımlarını Gaussian yaklaşıma uygun hale getirir."
2. **Tek eşik yerine `LiRA` olabilirlik oranı (35 sn).** "Zor veya aykırı bir örnek içerideyken bile kolay bir dış örnekten düşük güven alabilir; `LiRA` örneğin kendi `in` ve `out` gölge dağılımlarının log-olabilirlik oranını ($\Lambda$) kurarak örnek zorluğunu kalibre eder."
3. **Düşük FPR'de `Clopper-Pearson` güven aralığı (30 sn).** "Gizlilik denetiminde ortalama doğruluk değil düşük FPR'deki TPR önemlidir; küçük örneklemde `0/50` yanlış pozitif 'sıfır risk' demek değildir ve tam binom güven aralığı belirsizliği dürüstçe raporlar."
4. **Soru (25 sn).** "`%0.1 FPR`'de anlamlı bir üyelik sızıntısı iddiasını kanıtlamak için test kümesinde en az kaç negatif örnek gerekir?"
:::
