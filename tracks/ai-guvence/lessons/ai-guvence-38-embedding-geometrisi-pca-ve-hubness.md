---
id: ai-guvence-38
title: Embedding Geometrisi · Yoğunlaşma, PCA ve Hubness
summary: Kosinüs-öklid kimliğini, güç iterasyonuyla PCA'yı ve hubness raporunu yaz; gerçek all-minilm vektörlerinde etkin boyutu, göreli kontrastı ve komşuluk çarpıklığını Gaussian tabanla karşılaştırarak ölç.
esleme: ai-guvence-31, ai-temel-22
timeout: 60
---

::: anlat 384 boyut, ama kaçı gerçekten kullanılıyor?
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Gerçek embedding'ler 384 boyutun tamamını kullanmaz; rastgele vektörlerden çok daha düşük etkin boyutta yaşar | İlk üç görev: `veri/geometri.json` içindeki **sentetik** küçük vektörler. Final: yerel Ollama `all-minilm:22m`, sentetik şablon cümleleri, torch ile `eigh`, aynı boyutta Gaussian taban | Başka embedding modelinin veya gerçek bir vektör veritabanının değerlerini söylemez |
| Benzerlik, konudan çok cümle yapısını yakalayabilir | Aynı konu/farklı kalıp ve aynı kalıp/farklı konu çiftlerinin kosinüs ortalaması | Tek derleme dayanır; "yapı her zaman baskındır" genellemesi yapılamaz |
| Bazı noktalar orantısız sıklıkta "yakın komşu" olur (hubness) | k-NN listelerinden `N_k` dağılımı, çarpıklık, anti-hub | Küçük örnekte hubness kararsızdır; bu çarpıklık bir saldırı başarısı değildir |

> [!NOT]
> Görevler `veri/geometri.json` dosyasını okur; dosya sentetiktir. Setup her Çalıştır/Kontrol Et adımında geçici kopya kurar; değişiklikler taşınmaz, **kalıcılık yoktur**. Ekranda ayrı dosya görüntüleyici yoktur; içeriği görmek için `print` kullan. Gizli testler ayrıdır. Final kurulu `all-minilm` modelini kullanır, indirme yapmaz; çalışan Ollama sunucusunu kapatmaz. Görev kodu saf Python'dur, `eigh` yalnız sandbox'ın bağımsız kontrolüdür.

ai-guvence-31 embedding inversion, ai-temel-22 retrieval kalitesi ölçer. Bu ders o derslerin dayandığı geometriyi ölçer.

**Kosinüs ve öklid aynı şeyin iki yüzü olabilir.** Birim vektörlerde kimlik şudur: `‖â - b̂‖² = 2 - 2·cos(a,b)`. Yani normalize edilmiş bir indekste kosinüs sıralaması ile öklid sıralaması aynıdır. Normalize edilmemişse değildir: `[3,4]` ile `[6,8]` aynı yönü gösterir (cos=1), ama ham uzaklıkları 5'tir. Bir vektör veritabanı raporu okurken ilk soru hangi metrik ve normalize edilip edilmediğidir.

**Yüksek boyutta sezgi kırılır.** Rastgele yönlerde kosinüs 0 etrafında toplanır, standart sapması yaklaşık `1/√d` olur. En yakın ile en uzak komşu arasındaki fark da erir (Beyer vd. 1999): bu yoğunlaşma (concentration) etkisidir. Bunu ölçmek için göreli kontrast kullanılır: `(d_max - d_min)/d_min`. Değer küçüldükçe "en yakın komşu" anlamını yitirir.

**Ama gerçek embedding'ler rastgele değildir.** Etkin boyut, varyansın çoğunu taşıyan bileşen sayısıdır. Hesabı için PCA gerekir. PCA aslında kovaryans matrisinin özvektörlerini bulmaktır ve en büyüğü için güç iterasyonu yeter: `v ← Cv / ‖Cv‖`. Bu yöntem `C`'yi açıkça kurmaya gerek bırakmaz: `Cv = Yᵀ(Yv)/(n-1)`. **Veriyi merkezlemek şarttır;** merkezlenmemiş veride ilk "bileşen" çoğunlukla sadece ortalamayı gösterir. Görev 2 bunu sınar.

**Hubness.** Radovanović vd. (2010), yüksek boyutta bazı noktaların orantısız sıklıkta başka noktaların k-NN listesine girdiğini gösterir. `N_k(x)`, `x`'in kaç listede göründüğüdür. Dağılımın sağa çarpıklığı hubness ölçüsüdür. `N_k=0` olan noktalar anti-hub'dır: hiçbir sorgu onları kolay bulmaz.

**Saldırgan ne dener?** RAG'de bir belgeyi çok sorguya yakın kılmak ister. Birçok çalışma (ör. PoisonedRAG, Zou vd. 2024) bu tür hedefli zehirlemeyi inceler. Geometri bu dersin konusu; biz hedefli saldırı yazmıyoruz, ama finaldeki gözlem önemlidir: benzerlik yapıdan etkileniyorsa, belgenin **kalıbı** da erişimi etkiler. Sorgu kalıbına benzeyen bir içerik konudan bağımsız öne çıkabilir.

**Savunma neden kırılır?** "Eşik 0.7, altını almıyoruz" gibi sabit bir kosinüs kuralı dağılımı bilmeden konursa anlamsızdır: finalde rastgele iki şablon cümlesinin ortalaması bile bu civarda çıkabilir. Eşik, o modelin ve derlemin dağılımından seçilmelidir. Hub kontrolü de yapılmazsa bazı belgelerin her sorguda gelmesi "iyi eşleşme" sanılır.

**Görev 1'de sık tuzaklar:** Normalize etmeden iç çarpımı kosinüs saymak büyük vektörleri kayırır. Ham uzaklığı ve birim uzaklığı karıştırmak kimliği bozar.

Kaynaklar: [Beyer vd. 1999](https://doi.org/10.1007/3-540-49257-7_15), [Radovanović vd. 2010](https://www.jmlr.org/papers/v11/radovanovic10a.html), [Zou vd. 2024 · PoisonedRAG](https://arxiv.org/abs/2402.07867). Bu dersteki bütün sayılar yalnız yerel kanıttan gelir.

Köprü: ai-guvence-31 embedding inversion, ai-temel-22 retrieval kalitesi.
:::

::: tahmin Aynı yön, farklı uzunluk
Çıktıyı tahmin et, sonra Çalıştır ile karşılaştır.
```python
a = [3.0, 4.0]
b = [6.0, 8.0]
nb = sum(v * v for v in b) ** 0.5
na = sum(v * v for v in a) ** 0.5
print(sum(p * q for p, q in zip(a, b)) / (na * nb))
print(sum((p - q) ** 2 for p, q in zip(a, b)) ** 0.5)
print(round(sum((p / na - q / nb) ** 2 for p, q in zip(a, b)), 6))
```
???
```cikti
1.0
5.0
0.0
```
Tahmininle gerçek çıktı arasındaki farkı tezgâhta yorum satırı olarak yaz: normalize edilmemiş bir indekste bu iki vektör "yakın" mı sayılır? Sonra üç kusurlu başlangıç kodunu çalıştır ve her birinin neyi yanlış ölçtüğünü önce kendin teşhis et; açıklama çözümün ardından gelir.
:::

::: gorev 1 · Kosinüs ve birim uzaklık kimliği
`kosinus_kimligi(a,b)`: `a`, `b` aynı uzunlukta dolu liste; bool olmayan sonlu sayılar; ikisi de sıfır vektör olamaz. `{"kosinus":..,"ham_l2":‖a-b‖₂,"birim_l2_kare":‖â-b̂‖₂²,"kimlik_farki":|birim_l2_kare-(2-2·kosinus)|}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-38")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def kosinus_kimligi(a,b):
    c=sum(p*q for p,q in zip(a,b))
    d2=sum((p-q)**2 for p,q in zip(a,b))
    return {"kosinus":c,"ham_l2":math.sqrt(d2),"birim_l2_kare":d2,"kimlik_farki":abs(d2-(2-2*c))}

from ai_guvence_veri import json_yukle
v=json_yukle("veri/geometri.json")
for c in v["ciftler"]:
    print(c["ad"],kosinus_kimligi(c["a"],c["b"]))
```
```test
def sinama1(f):
    import copy,math,random
    def _r(a,b):
        na=math.sqrt(sum(v*v for v in a));nb=math.sqrt(sum(v*v for v in b));c=sum(p*q for p,q in zip(a,b))/(na*nb)
        d=sum((p/na-q/nb)**2 for p,q in zip(a,b))
        return {"kosinus":c,"ham_l2":math.sqrt(sum((p-q)**2 for p,q in zip(a,b))),"birim_l2_kare":d,"kimlik_farki":abs(d-(2-2*c))}
    try:
        a=[3.0,4.0];b=[6.0,8.0];old=(list(a),list(b))
        r=f(a,b)
        if (a,b)!=old or abs(r["kosinus"]-1)>1e-12 or r["ham_l2"]!=5.0 or r["birim_l2_kare"]>1e-20 or r["kimlik_farki"]>1e-12 or set(r)!={"kosinus","ham_l2","birim_l2_kare","kimlik_farki"}:return False
        r=f([1.0,0.0],[-2.0,0.0])
        if r["kosinus"]!=-1.0 or r["ham_l2"]!=3.0 or abs(r["birim_l2_kare"]-4)>1e-12:return False
        rng=random.Random(38)
        for _ in range(20):
            n=rng.randint(1,8);u=[rng.uniform(-5,5) for _ in range(n)];w=[rng.uniform(-5,5) for _ in range(n)]
            q=f(list(u),list(w));e=_r(u,w)
            if any(abs(q[k]-e[k])>1e-9 for k in e) or q["kimlik_farki"]>1e-9:return False
        for bad in ((None,[1.0]),([1.0],None),([],[]),((1.0,),[1.0]),([1.0],(1.0,)),([1.0],[1.0,2.0]),([True],[1.0]),([1.0],[float("nan")]),([float("inf")],[1.0]),(["a"],[1.0]),([0.0],[1.0]),([1.0],[0.0])):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama1(kosinus_kimligi),"normalize kosinüs, ham ve birim uzaklık, kimlik ve geçersiz girdi")
for ad,mut in [("kosinüs normalize değil",lambda a,b:dict(kosinus_kimligi(a,b),kosinus=sum(p*q for p,q in zip(a,b)))),("birim yerine ham uzaklık",lambda a,b:dict(kosinus_kimligi(a,b),birim_l2_kare=kosinus_kimligi(a,b)["ham_l2"]**2)),("ham yerine birim",lambda a,b:dict(kosinus_kimligi(a,b),ham_l2=kosinus_kimligi(a,b)["birim_l2_kare"]**.5))]:
    ok(not sinama1(mut),"mutant reddedildi: "+ad)
```
```solution
import math
def kosinus_kimligi(a,b):
    if not isinstance(a,list) or not isinstance(b,list) or not a or len(a)!=len(b):raise ValueError("girdi")
    for v in a+b:
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError("sayı")
    na=math.sqrt(sum(v*v for v in a));nb=math.sqrt(sum(v*v for v in b))
    if na==0 or nb==0:raise ValueError("sıfır vektör")
    c=sum(p*q for p,q in zip(a,b))/(na*nb)
    d2=sum((p/na-q/nb)**2 for p,q in zip(a,b))
    return {"kosinus":c,"ham_l2":math.sqrt(sum((p-q)**2 for p,q in zip(a,b))),"birim_l2_kare":d2,"kimlik_farki":abs(d2-(2-2*c))}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    v=json_yukle("veri/geometri.json")
    for c in v["ciftler"]:
        print(c["ad"],kosinus_kimligi(c["a"],c["b"]))
```
```hint
Önce iki normu al. Kosinüs ve birim uzaklık normlara bölünerek hesaplanır, ham uzaklık bölünmez.
```
:::

::: anlat Güç iterasyonu ne bulur?
Her adımda vektör, kovaryansın en büyük özdeğerinin yönüne doğru büyür; normalize etmek taşmayı önler. Yeterli adımda `v` baskın özvektöre yaklaşır, özdeğer Rayleigh oranıdır: `vᵀCv`. Toplam varyans `Σ‖y_i‖²/(n-1)`, açıklanan oran ise `ozdeger/toplam`.

Özvektörün işareti keyfidir: `v` ile `-v` aynı yöndür. Karşılaştırılabilir sonuç için en büyük mutlak koordinatı pozitif yaparız (eşitlikte ilk koordinat).

**Görev 2'de sık tuzaklar:** Merkezlememek ortalamayı bileşen sanmaktır; `X` görünür örneğinde bütün noktaları `(10,10)` etrafına kaydırdık. Payda `n-1`'dir; `n` kullanmak özdeğeri küçültür. `v0` değiştirilmemeli ve sıfır olamaz. Sabit veri (toplam varyans 0) tanımsızdır, `ValueError` verir.
:::

::: gorev 2 · Merkezli güç iterasyonu
`guc_iterasyonu(X,v0,adim)`: `X` en az 2 satırlı dikdörtgen liste; hücreler bool olmayan sonlu sayı. `v0` sütun sayısı uzunluğunda, sıfır olmayan liste. `adim` bool olmayan int, `>=1`. Sütun ortalamalarını çıkar. `Cu=Yᵀ(Yu)/(n-1)`. `v0`'ı normalize et, `adim` kez `v←Cv/‖Cv‖` uygula. `ozdeger=vᵀCv`, `aciklanan_oran=ozdeger/toplam_varyans`. En büyük mutlak koordinat pozitif olacak şekilde işareti düzelt. `{"bilesen","ozdeger","aciklanan_oran"}` döndür. Toplam varyans veya `Cv` sıfırsa `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-38")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def guc_iterasyonu(X,v0,adim):
    n=len(X);d=len(X[0])
    v=list(v0)
    def carp(u):
        p=[sum(a*b for a,b in zip(s,u)) for s in X]
        return [sum(X[i][j]*p[i] for i in range(n))/n for j in range(d)]
    for _ in range(adim):
        v=carp(v)
    lam=sum(a*b for a,b in zip(v,carp(v)))
    return {"bilesen":v,"ozdeger":lam,"aciklanan_oran":1.0}

from ai_guvence_veri import json_yukle
v=json_yukle("veri/geometri.json")
print(guc_iterasyonu(v["X"],v["v0"],v["adim"]))
```
```test
def sinama2(f):
    import copy,math,random
    try:
        X=[[2.0,0.0],[-2.0,0.0],[0.0,1.0],[0.0,-1.0]];old=copy.deepcopy(X);v0=[.5,.25]
        r=f(X,v0,50)
        if X!=old or v0!=[.5,.25] or set(r)!={"bilesen","ozdeger","aciklanan_oran"}:return False
        if abs(r["bilesen"][0]-1)>1e-9 or abs(r["bilesen"][1])>1e-9 or abs(r["ozdeger"]-8/3)>1e-9 or abs(r["aciklanan_oran"]-.8)>1e-9:return False
        r=f([[12.0,10.0],[8.0,10.0],[10.0,11.0],[10.0,9.0]],[.5,.25],50)
        if abs(r["bilesen"][0]-1)>1e-9 or abs(r["ozdeger"]-8/3)>1e-9 or abs(r["aciklanan_oran"]-.8)>1e-9:return False
        r=f([[-2.0,0.0],[2.0,0.0],[0.0,1.0],[0.0,-1.0]],[-.5,.25],50)
        if r["bilesen"][0]<=0:return False
        r=f([[0.0,-2.0],[0.0,2.0],[1.0,0.0],[-1.0,0.0]],[.25,-.5],50)
        if abs(r["bilesen"][1]-1)>1e-9:return False
        t=f(X,[1.0,1.0],1)
        if abs(t["bilesen"][0]-4/math.sqrt(17))>1e-12 or abs(t["bilesen"][1]-1/math.sqrt(17))>1e-12:return False
        if abs(f(X,[2.0,2.0],1)["bilesen"][0]-4/math.sqrt(17))>1e-12:return False
        if abs(f(X,[1e100,0.0],1)["bilesen"][0]-1.0)>1e-12:return False
        if abs(f([[1.0,0.0],[-1.0,0.0],[0.0,0.0]],[1.0,0.0],1)["ozdeger"]-1.0)>1e-12:return False
        rng=random.Random(383)
        Y=[[rng.gauss(0,3),rng.gauss(0,1),rng.gauss(0,.5)] for _ in range(30)]
        q=f(Y,[1.0,1.0,1.0],200);v=q["bilesen"]
        if abs(sum(a*a for a in v)-1)>1e-9 or not 0<q["aciklanan_oran"]<=1:return False
        m=[sum(s[j] for s in Y)/30 for j in range(3)];Z=[[s[j]-m[j] for j in range(3)] for s in Y]
        lam=sum(sum(a*b for a,b in zip(s,v))**2 for s in Z)/29
        if abs(lam-q["ozdeger"])>1e-9:return False
        tp=sum(a*a for s in Z for a in s)/29
        if abs(q["aciklanan_oran"]-lam/tp)>1e-9:return False
        for w in ([1.0,0.0,0.0],[0.0,1.0,0.0],[.3,-.7,.2]):
            n=math.sqrt(sum(a*a for a in w));w=[a/n for a in w]
            if sum(sum(a*b for a,b in zip(s,w))**2 for s in Z)/29>lam+1e-9:return False
        g=[1.0,2.0];G=[[1.0,2.0],[3.0,5.0]]
        if f(G,[1.0,1.0],5)["bilesen"][1]<=0:return False
        for bad in (([(1.0,2.0),[3.0,5.0]],[1.0,1.0],1),(None,g,1),([g],g,1),([],g,1),((g,g),g,1),([g,[1.0]],g,1),([[],[]],[],1),([g,None],g,1),([[True,2.0],[3.0,5.0]],g,1),([[float("nan"),2.0],g],g,1),([["a",2.0],g],g,1),(G,None,1),(G,[1.0],1),(G,(1.0,2.0),1),(G,[True,1.0],1),(G,["a",1.0],1),(G,[float("inf"),1.0],1),(G,[0.0,0.0],1),([[1.0,0.0],[-1.0,0.0]],[0.0,1.0],1),(G,g,0),(G,g,True),(G,g,1.5),([g,g],g,1)):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama2(guc_iterasyonu),"merkezleme, normalize adım, işaret, oran ve geçersiz girdi")
for ad,mut in [("oran hep bir",lambda X,v,a:dict(guc_iterasyonu(X,v,a),aciklanan_oran=1.0)),("işaret ters",lambda X,v,a:dict(guc_iterasyonu(X,v,a),bilesen=[-p for p in guc_iterasyonu(X,v,a)["bilesen"]])),("özdeğer 2 kat",lambda X,v,a:dict(guc_iterasyonu(X,v,a),ozdeger=2*guc_iterasyonu(X,v,a)["ozdeger"]))]:
    ok(not sinama2(mut),"mutant reddedildi: "+ad)
```
```solution
import math
def guc_iterasyonu(X,v0,adim):
    if not isinstance(X,list) or len(X)<2:raise ValueError("X")
    for s in X:
        if not isinstance(s,list) or not s or len(s)!=len(X[0]):raise ValueError("satır")
        for v in s:
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError("sayı")
    d=len(X[0])
    if not isinstance(v0,list) or len(v0)!=d:raise ValueError("v0")
    for v in v0:
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError("sayı")
    if isinstance(adim,bool) or not isinstance(adim,int) or adim<1:raise ValueError("adim")
    n=len(X)
    m=[sum(s[j] for s in X)/n for j in range(d)]
    Y=[[s[j]-m[j] for j in range(d)] for s in X]
    toplam=sum(v*v for s in Y for v in s)/(n-1)
    nv=math.sqrt(sum(v*v for v in v0))
    if nv==0 or toplam==0:raise ValueError("sıfır")
    def carp(u):
        p=[sum(a*b for a,b in zip(s,u)) for s in Y]
        return [sum(Y[i][j]*p[i] for i in range(n))/(n-1) for j in range(d)]
    v=[x/nv for x in v0]
    for _ in range(adim):
        w=carp(v)
        nw=math.sqrt(sum(x*x for x in w))
        if nw==0:raise ValueError("sıfır")
        v=[x/nw for x in w]
    lam=sum(a*b for a,b in zip(v,carp(v)))
    i=max(range(d),key=lambda j:abs(v[j]))
    if v[i]<0:v=[-x for x in v]
    return {"bilesen":v,"ozdeger":lam,"aciklanan_oran":lam/toplam}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    v=json_yukle("veri/geometri.json")
    print(guc_iterasyonu(v["X"],v["v0"],v["adim"]))
```
```hint
Merkezle, normalize et, sonra döngüye gir. Her adımda normalize etmeyi unutma; özdeğeri son v ile hesapla.
```
:::

::: anlat Çarpıklık neyi söyler?
Her nokta tam k komşu listelediği için `N_k` ortalaması her zaman k'dır; bilgi ortalamada değil **şekildedir**. Çarpıklık `E[(N-μ)³]/σ³` değeridir. Pozitif büyük değer birkaç noktanın orantısız sık geçtiğini söyler. Standart sapma 0 ise tüm noktalar eşit görünmüştür, çarpıklık 0 alınır.

Bir nokta kendi komşusu sayılmaz: listeye kendini koyan bir `k-NN` kodu her noktanın `N_k` değerini 1 şişirir ve anti-hub'ları yok eder. Finalde bu listeyi sandbox üretir, kendi noktası zaten dışarıda bırakılır; görevde bunu geçersiz girdi sayarsın.

**Görev 3'te sık tuzaklar:** Kendini saymak anti-hub'ları gizler. `(maks-ortalama)/std` bir aykırılık ölçüsüdür, çarpıklık değildir. Eşitlikte en küçük indeksli hub seçilir.
:::

::: gorev 3 · k-NN listesinden hubness
`hubness_raporu(komsular)`: en az iki elemanlı liste; her eleman aynı uzunlukta dolu liste; komşular bool olmayan int, geçerli indis, kendi indeksi olamaz, aynı listede tekrar edemez. `N_j`, `j`'nin bütün listelerde görülme sayısıdır. `{"n_k":N,"carpiklik":popülasyon çarpıklığı (σ=0 ise 0.0),"anti_hub":N=0 sayısı,"en_buyuk_hub":N en büyük ilk indeks,"en_buyuk_hub_n":o değer}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-38")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def hubness_raporu(komsular):
    n=len(komsular);N=[0]*n
    for i,ks in enumerate(komsular):
        N[i]+=1
        for j in ks:N[j]+=1
    mu=sum(N)/n
    s2=sum((v-mu)**2 for v in N)/n
    i=max(range(n),key=lambda j:N[j])
    return {"n_k":N,"carpiklik":(max(N)-mu)/s2**.5,"anti_hub":sum(v==0 for v in N),"en_buyuk_hub":i,"en_buyuk_hub_n":N[i]}

from ai_guvence_veri import json_yukle
v=json_yukle("veri/geometri.json")
print(hubness_raporu(v["komsular"]))
```
```test
def sinama3(f):
    import copy,math,random
    def _r(K):
        n=len(K);N=[0]*n
        for s in K:
            for j in s:N[j]+=1
        m=sum(N)/n;v=sum((x-m)**2 for x in N)/n
        return N,(0.0 if v==0 else sum((x-m)**3 for x in N)/n/v**1.5)
    try:
        K=[[1,2],[0,2],[0,1],[0,1]];old=copy.deepcopy(K)
        r=f(K)
        N,s=_r(K)
        if K!=old or r["n_k"]!=[3,3,2,0] or abs(r["carpiklik"]-s)>1e-12 or r["anti_hub"]!=1 or r["en_buyuk_hub"]!=0 or r["en_buyuk_hub_n"]!=3 or set(r)!={"n_k","carpiklik","anti_hub","en_buyuk_hub","en_buyuk_hub_n"}:return False
        d=f([[1],[0]])
        if d!={"n_k":[1,1],"carpiklik":0.0,"anti_hub":0,"en_buyuk_hub":0,"en_buyuk_hub_n":1}:return False
        e=f([[3],[3],[3],[0]])
        if e["en_buyuk_hub"]!=3 or e["en_buyuk_hub_n"]!=3 or e["anti_hub"]!=2 or abs(e["carpiklik"]-_r([[3],[3],[3],[0]])[1])>1e-12:return False
        rng=random.Random(38383)
        for _ in range(15):
            n=rng.randint(3,12);k=rng.randint(1,2)
            H=[rng.sample([j for j in range(n) if j!=i],k) for i in range(n)]
            q=f(copy.deepcopy(H));N,s=_r(H)
            if q["n_k"]!=N or abs(q["carpiklik"]-s)>1e-9 or q["en_buyuk_hub_n"]!=max(N) or q["en_buyuk_hub"]!=N.index(max(N)) or q["anti_hub"]!=N.count(0):return False
        for bad in (None,[],[[1]],((1,),(0,)),[(1,),(0,)],[[1],None],[[],[]],[[1],[0,1]],[[1],[0,2],[0]],[[0],[0]],[[1],[2]],[[1],[-1]],[[True],[0]],[[1.0],[0]],[["a"],[0]],[[1,1],[0,2],[0,1]]):
            try:f(bad);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama3(hubness_raporu),"N_k, çarpıklık, anti-hub, hub eşitliği ve geçersiz girdi")
for ad,mut in [("çarpıklık sıfır",lambda K:dict(hubness_raporu(K),carpiklik=0.0)),("anti hub yok",lambda K:dict(hubness_raporu(K),anti_hub=0)),("hub son indeks",lambda K:dict(hubness_raporu(K),en_buyuk_hub=len(K)-1-hubness_raporu(K)["n_k"][::-1].index(hubness_raporu(K)["en_buyuk_hub_n"])))]:
    ok(not sinama3(mut),"mutant reddedildi: "+ad)
```
```solution
import math
def hubness_raporu(komsular):
    if not isinstance(komsular,list) or len(komsular)<2:raise ValueError("liste")
    n=len(komsular)
    for k in komsular:
        if not isinstance(k,list) or not k or len(k)!=len(komsular[0]):raise ValueError("k")
    N=[0]*n
    for i,ks in enumerate(komsular):
        if len(set(ks))!=len(ks):raise ValueError("tekrar")
        for j in ks:
            if isinstance(j,bool) or not isinstance(j,int) or not 0<=j<n or j==i:raise ValueError("komşu")
            N[j]+=1
    mu=sum(N)/n
    s2=sum((v-mu)**2 for v in N)/n
    sk=0.0 if s2==0 else sum((v-mu)**3 for v in N)/n/s2**1.5
    i=max(range(n),key=lambda j:N[j])
    return {"n_k":N,"carpiklik":sk,"anti_hub":sum(v==0 for v in N),"en_buyuk_hub":i,"en_buyuk_hub_n":N[i]}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    v=json_yukle("veri/geometri.json")
    print(hubness_raporu(v["komsular"]))
```
```hint
Önce N listesini say. Ortalama ve popülasyon varyansından üçüncü merkezi momenti hesapla; σ=0 durumunu ayrı ele al.
```
:::

::: anlat Hata vitrini · çalışmış yanlış rapor
Yazar, kusurlu başlangıç kodlarını görünür sentetik veriyle gerçekten çalıştırdı ve sonucu `outputs/yeni-ai-guvence-38/gorunur-run-1.json` dosyasına kaydetti. `X` örneğinde bütün noktalar `(10,10)` etrafındadır. Doğru kod `bilesen=[1.0, 0.0]`, `aciklanan_oran=0.800` verir. Kusurlu kod merkezlemediği ve normalize etmediği için `bilesen=[5.798172474156993e+114, 5.754849251908493e+114]` ve sabit `aciklanan_oran=1.0` verir.

Bu kaydedilmiş bir hesaplama çıktısıdır, model yanıtı değildir ve veri sentetiktir. Kusurlu çıktıyı görüp "verinin tek boyutu var" diyen biri neyi kaçırır? Merkezlememe ve normalize etmeme etkisini ayrı ayrı kendi cümlenle açıkla. Gerçek finaldeki ölçüm ayrıca üretilir; bu sayılar onun yerine konmaz.
:::

::: anlat Gerçek deney: all-minilm ile rastgele taban
Final 8 konu, 3 ifade ve 8 cümle kalıbından oluşan 192 sentetik şablon cümlenin rastgele 120 tanesini seçer ve yerel `all-minilm:22m` ile gömer. Aynı sayıda ve boyutta rastgele Gaussian birim vektör taban olarak kullanılır.

Ölçümler: (1) `kosinus_kimligi` 200 rastgele gerçek çifte uygulanır. Çiftler `aynı konu/farklı kalıp`, `aynı kalıp/farklı konu` ve `ikisi de farklı` diye gruplanır. (2) `guc_iterasyonu` gerçek matriste koşar, `eigh` ile bağımsız karşılaştırılır. (3) `hubness_raporu` iki k-NN grafiğine (k=5) uygulanır. (4) Göreli kontrast ve %90 varyans için gereken bileşen sayısı raporlanır.

Kabul; çıktılarının bağımsız hesapla aynı olmasına, kimlik farkının küçük kalmasına ve güç iterasyonunun `eigh` ile uyuşmasına bağlıdır. Hangi grubun daha yüksek çıkacağı kabul şartı **değildir;** gözlemdir.

**Kanıt dosyasını oku:** Soru 1: `gruplar` içinde hangi kosinüs ortalaması yüksek? Bu, retrieval için ne ima eder? Soru 2: `analiz` içinde `bilesen_90` ve `goreli_kontrast` iki veri için nasıl farklı? Soru 3: İki veride de `hub.carpiklik` değerine bak. n=120 için fark güçlü bir sonuç mu? Bir hub'ı çıkarıp yeniden ölçmek için ne yapmak gerekir? Cevabını tezgâhta yorum olarak yaz; otomatik test bu serbest açıklamayı puanlamaz.
:::

::: gorev Gerçek deney · all-minilm vektörlerinde geometri ölçümü
Önceki üç görevin `kosinus_kimligi`, `guc_iterasyonu` ve `hubness_raporu` işlevlerini birleştir. Çalıştır gerçek ölçümü gösterir; Kontrol Et önce üç sözleşmeyi gizli verilerle sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
timeout: 240
```
```starter
import ai_lab
import math
def kosinus_kimligi(a,b):
    c=sum(p*q for p,q in zip(a,b))
    d2=sum((p-q)**2 for p,q in zip(a,b))
    return {"kosinus":c,"ham_l2":math.sqrt(d2),"birim_l2_kare":d2,"kimlik_farki":abs(d2-(2-2*c))}
def guc_iterasyonu(X,v0,adim):
    n=len(X);d=len(X[0])
    v=list(v0)
    def carp(u):
        p=[sum(a*b for a,b in zip(s,u)) for s in X]
        return [sum(X[i][j]*p[i] for i in range(n))/n for j in range(d)]
    for _ in range(adim):
        v=carp(v)
    lam=sum(a*b for a,b in zip(v,carp(v)))
    return {"bilesen":v,"ozdeger":lam,"aciklanan_oran":1.0}
def hubness_raporu(komsular):
    n=len(komsular);N=[0]*n
    for i,ks in enumerate(komsular):
        N[i]+=1
        for j in ks:N[j]+=1
    mu=sum(N)/n
    s2=sum((v-mu)**2 for v in N)/n
    i=max(range(n),key=lambda j:N[j])
    return {"n_k":N,"carpiklik":(max(N)-mu)/s2**.5,"anti_hub":sum(v==0 for v in N),"en_buyuk_hub":i,"en_buyuk_hub_n":N[i]}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_38 as D
    D.goster(kosinus_kimligi,guc_iterasyonu,hubness_raporu)
```
```test
import ai_lab,math
checks=[]
def kontrol(x,m):checks.append(bool(x));ok(x,m)
issues=ai_lab.kod_denetimi(src,('referans_kosinus', 'referans_pca', 'referans_hubness', 'kanit_yaz', '_yakin'),izin=())
kontrol(not issues,"kopya/yama/dinamik kod yok: "+str(issues))
if issues:stop()
kosinus_kimligi=need("kosinus_kimligi")
guc_iterasyonu=need("guc_iterasyonu")
hubness_raporu=need("hubness_raporu")
def sinama1(f):
    import copy,math,random
    def _r(a,b):
        na=math.sqrt(sum(v*v for v in a));nb=math.sqrt(sum(v*v for v in b));c=sum(p*q for p,q in zip(a,b))/(na*nb)
        d=sum((p/na-q/nb)**2 for p,q in zip(a,b))
        return {"kosinus":c,"ham_l2":math.sqrt(sum((p-q)**2 for p,q in zip(a,b))),"birim_l2_kare":d,"kimlik_farki":abs(d-(2-2*c))}
    try:
        a=[3.0,4.0];b=[6.0,8.0];old=(list(a),list(b))
        r=f(a,b)
        if (a,b)!=old or abs(r["kosinus"]-1)>1e-12 or r["ham_l2"]!=5.0 or r["birim_l2_kare"]>1e-20 or r["kimlik_farki"]>1e-12 or set(r)!={"kosinus","ham_l2","birim_l2_kare","kimlik_farki"}:return False
        r=f([1.0,0.0],[-2.0,0.0])
        if r["kosinus"]!=-1.0 or r["ham_l2"]!=3.0 or abs(r["birim_l2_kare"]-4)>1e-12:return False
        rng=random.Random(38)
        for _ in range(20):
            n=rng.randint(1,8);u=[rng.uniform(-5,5) for _ in range(n)];w=[rng.uniform(-5,5) for _ in range(n)]
            q=f(list(u),list(w));e=_r(u,w)
            if any(abs(q[k]-e[k])>1e-9 for k in e) or q["kimlik_farki"]>1e-9:return False
        for bad in ((None,[1.0]),([1.0],None),([],[]),((1.0,),[1.0]),([1.0],(1.0,)),([1.0],[1.0,2.0]),([True],[1.0]),([1.0],[float("nan")]),([float("inf")],[1.0]),(["a"],[1.0]),([0.0],[1.0]),([1.0],[0.0])):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
kontrol(sinama1(kosinus_kimligi),"normalize kosinüs, ham ve birim uzaklık, kimlik ve geçersiz girdi")
for ad,mut in [("kosinüs normalize değil",lambda a,b:dict(kosinus_kimligi(a,b),kosinus=sum(p*q for p,q in zip(a,b)))),("birim yerine ham uzaklık",lambda a,b:dict(kosinus_kimligi(a,b),birim_l2_kare=kosinus_kimligi(a,b)["ham_l2"]**2)),("ham yerine birim",lambda a,b:dict(kosinus_kimligi(a,b),ham_l2=kosinus_kimligi(a,b)["birim_l2_kare"]**.5))]:
    kontrol(not sinama1(mut),"mutant reddedildi: "+ad)
def sinama2(f):
    import copy,math,random
    try:
        X=[[2.0,0.0],[-2.0,0.0],[0.0,1.0],[0.0,-1.0]];old=copy.deepcopy(X);v0=[.5,.25]
        r=f(X,v0,50)
        if X!=old or v0!=[.5,.25] or set(r)!={"bilesen","ozdeger","aciklanan_oran"}:return False
        if abs(r["bilesen"][0]-1)>1e-9 or abs(r["bilesen"][1])>1e-9 or abs(r["ozdeger"]-8/3)>1e-9 or abs(r["aciklanan_oran"]-.8)>1e-9:return False
        r=f([[12.0,10.0],[8.0,10.0],[10.0,11.0],[10.0,9.0]],[.5,.25],50)
        if abs(r["bilesen"][0]-1)>1e-9 or abs(r["ozdeger"]-8/3)>1e-9 or abs(r["aciklanan_oran"]-.8)>1e-9:return False
        r=f([[-2.0,0.0],[2.0,0.0],[0.0,1.0],[0.0,-1.0]],[-.5,.25],50)
        if r["bilesen"][0]<=0:return False
        r=f([[0.0,-2.0],[0.0,2.0],[1.0,0.0],[-1.0,0.0]],[.25,-.5],50)
        if abs(r["bilesen"][1]-1)>1e-9:return False
        t=f(X,[1.0,1.0],1)
        if abs(t["bilesen"][0]-4/math.sqrt(17))>1e-12 or abs(t["bilesen"][1]-1/math.sqrt(17))>1e-12:return False
        if abs(f(X,[2.0,2.0],1)["bilesen"][0]-4/math.sqrt(17))>1e-12:return False
        if abs(f(X,[1e100,0.0],1)["bilesen"][0]-1.0)>1e-12:return False
        if abs(f([[1.0,0.0],[-1.0,0.0],[0.0,0.0]],[1.0,0.0],1)["ozdeger"]-1.0)>1e-12:return False
        rng=random.Random(383)
        Y=[[rng.gauss(0,3),rng.gauss(0,1),rng.gauss(0,.5)] for _ in range(30)]
        q=f(Y,[1.0,1.0,1.0],200);v=q["bilesen"]
        if abs(sum(a*a for a in v)-1)>1e-9 or not 0<q["aciklanan_oran"]<=1:return False
        m=[sum(s[j] for s in Y)/30 for j in range(3)];Z=[[s[j]-m[j] for j in range(3)] for s in Y]
        lam=sum(sum(a*b for a,b in zip(s,v))**2 for s in Z)/29
        if abs(lam-q["ozdeger"])>1e-9:return False
        tp=sum(a*a for s in Z for a in s)/29
        if abs(q["aciklanan_oran"]-lam/tp)>1e-9:return False
        for w in ([1.0,0.0,0.0],[0.0,1.0,0.0],[.3,-.7,.2]):
            n=math.sqrt(sum(a*a for a in w));w=[a/n for a in w]
            if sum(sum(a*b for a,b in zip(s,w))**2 for s in Z)/29>lam+1e-9:return False
        g=[1.0,2.0];G=[[1.0,2.0],[3.0,5.0]]
        if f(G,[1.0,1.0],5)["bilesen"][1]<=0:return False
        for bad in (([(1.0,2.0),[3.0,5.0]],[1.0,1.0],1),(None,g,1),([g],g,1),([],g,1),((g,g),g,1),([g,[1.0]],g,1),([[],[]],[],1),([g,None],g,1),([[True,2.0],[3.0,5.0]],g,1),([[float("nan"),2.0],g],g,1),([["a",2.0],g],g,1),(G,None,1),(G,[1.0],1),(G,(1.0,2.0),1),(G,[True,1.0],1),(G,["a",1.0],1),(G,[float("inf"),1.0],1),(G,[0.0,0.0],1),([[1.0,0.0],[-1.0,0.0]],[0.0,1.0],1),(G,g,0),(G,g,True),(G,g,1.5),([g,g],g,1)):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
kontrol(sinama2(guc_iterasyonu),"merkezleme, normalize adım, işaret, oran ve geçersiz girdi")
for ad,mut in [("oran hep bir",lambda X,v,a:dict(guc_iterasyonu(X,v,a),aciklanan_oran=1.0)),("işaret ters",lambda X,v,a:dict(guc_iterasyonu(X,v,a),bilesen=[-p for p in guc_iterasyonu(X,v,a)["bilesen"]])),("özdeğer 2 kat",lambda X,v,a:dict(guc_iterasyonu(X,v,a),ozdeger=2*guc_iterasyonu(X,v,a)["ozdeger"]))]:
    kontrol(not sinama2(mut),"mutant reddedildi: "+ad)
def sinama3(f):
    import copy,math,random
    def _r(K):
        n=len(K);N=[0]*n
        for s in K:
            for j in s:N[j]+=1
        m=sum(N)/n;v=sum((x-m)**2 for x in N)/n
        return N,(0.0 if v==0 else sum((x-m)**3 for x in N)/n/v**1.5)
    try:
        K=[[1,2],[0,2],[0,1],[0,1]];old=copy.deepcopy(K)
        r=f(K)
        N,s=_r(K)
        if K!=old or r["n_k"]!=[3,3,2,0] or abs(r["carpiklik"]-s)>1e-12 or r["anti_hub"]!=1 or r["en_buyuk_hub"]!=0 or r["en_buyuk_hub_n"]!=3 or set(r)!={"n_k","carpiklik","anti_hub","en_buyuk_hub","en_buyuk_hub_n"}:return False
        d=f([[1],[0]])
        if d!={"n_k":[1,1],"carpiklik":0.0,"anti_hub":0,"en_buyuk_hub":0,"en_buyuk_hub_n":1}:return False
        e=f([[3],[3],[3],[0]])
        if e["en_buyuk_hub"]!=3 or e["en_buyuk_hub_n"]!=3 or e["anti_hub"]!=2 or abs(e["carpiklik"]-_r([[3],[3],[3],[0]])[1])>1e-12:return False
        rng=random.Random(38383)
        for _ in range(15):
            n=rng.randint(3,12);k=rng.randint(1,2)
            H=[rng.sample([j for j in range(n) if j!=i],k) for i in range(n)]
            q=f(copy.deepcopy(H));N,s=_r(H)
            if q["n_k"]!=N or abs(q["carpiklik"]-s)>1e-9 or q["en_buyuk_hub_n"]!=max(N) or q["en_buyuk_hub"]!=N.index(max(N)) or q["anti_hub"]!=N.count(0):return False
        for bad in (None,[],[[1]],((1,),(0,)),[(1,),(0,)],[[1],None],[[],[]],[[1],[0,1]],[[1],[0,2],[0]],[[0],[0]],[[1],[2]],[[1],[-1]],[[True],[0]],[[1.0],[0]],[["a"],[0]],[[1,1],[0,2],[0,1]]):
            try:f(bad);return False
            except ValueError:pass
        return True
    except Exception:return False
kontrol(sinama3(hubness_raporu),"N_k, çarpıklık, anti-hub, hub eşitliği ve geçersiz girdi")
for ad,mut in [("çarpıklık sıfır",lambda K:dict(hubness_raporu(K),carpiklik=0.0)),("anti hub yok",lambda K:dict(hubness_raporu(K),anti_hub=0)),("hub son indeks",lambda K:dict(hubness_raporu(K),en_buyuk_hub=len(K)-1-hubness_raporu(K)["n_k"][::-1].index(hubness_raporu(K)["en_buyuk_hub_n"])))]:
    kontrol(not sinama3(mut),"mutant reddedildi: "+ad)
if not all(checks):stop()
from sandbox import ai_gercek_ai_guvence_38 as D
try:r=D.deney(kosinus_kimligi,guc_iterasyonu,hubness_raporu)
except ai_lab.GercekLabYok as e:
    kontrol(False,"gerçek deney yok: "+str(e));stop()
kontrol(r["kos_ayni"],"gerçek çiftlerde kosinüs raporu bağımsız hesapla aynı")
kontrol(r["kimlik_max"]<1e-9,"birim kimlik gerçek vektörlerde doğrulandı")
kontrol(r["pca_ayni"],"gerçek matriste güç iterasyonu bağımsız hesapla aynı")
kontrol(r["pca_eigh_fark"]<0.02,"güç iterasyonu eigh özdeğeriyle uyuştu")
kontrol(r["hub_ayni"],"iki k-NN grafiğinde hubness raporu bağımsız hesapla aynı")
kontrol(r["boyut"]>=2 and r["ornek"]==r["ayarlar"]["ornek"],"gerçek gömme boyutu ve örnek sayısı doğru")
kontrol(r["analiz"]["gaussian"]["bilesen_90"]>0,"taban ölçüldü")
ai_lab.kanit_yaz("ai-guvence-38-kabul",{"kaynak":"gercek","kabul":all(checks),"ders":"ai-guvence-38","deney":r})
```
```solution
import ai_lab
import math
def kosinus_kimligi(a,b):
    if not isinstance(a,list) or not isinstance(b,list) or not a or len(a)!=len(b):raise ValueError("girdi")
    for v in a+b:
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError("sayı")
    na=math.sqrt(sum(v*v for v in a));nb=math.sqrt(sum(v*v for v in b))
    if na==0 or nb==0:raise ValueError("sıfır vektör")
    c=sum(p*q for p,q in zip(a,b))/(na*nb)
    d2=sum((p/na-q/nb)**2 for p,q in zip(a,b))
    return {"kosinus":c,"ham_l2":math.sqrt(sum((p-q)**2 for p,q in zip(a,b))),"birim_l2_kare":d2,"kimlik_farki":abs(d2-(2-2*c))}
def guc_iterasyonu(X,v0,adim):
    if not isinstance(X,list) or len(X)<2:raise ValueError("X")
    for s in X:
        if not isinstance(s,list) or not s or len(s)!=len(X[0]):raise ValueError("satır")
        for v in s:
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError("sayı")
    d=len(X[0])
    if not isinstance(v0,list) or len(v0)!=d:raise ValueError("v0")
    for v in v0:
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError("sayı")
    if isinstance(adim,bool) or not isinstance(adim,int) or adim<1:raise ValueError("adim")
    n=len(X)
    m=[sum(s[j] for s in X)/n for j in range(d)]
    Y=[[s[j]-m[j] for j in range(d)] for s in X]
    toplam=sum(v*v for s in Y for v in s)/(n-1)
    nv=math.sqrt(sum(v*v for v in v0))
    if nv==0 or toplam==0:raise ValueError("sıfır")
    def carp(u):
        p=[sum(a*b for a,b in zip(s,u)) for s in Y]
        return [sum(Y[i][j]*p[i] for i in range(n))/(n-1) for j in range(d)]
    v=[x/nv for x in v0]
    for _ in range(adim):
        w=carp(v)
        nw=math.sqrt(sum(x*x for x in w))
        if nw==0:raise ValueError("sıfır")
        v=[x/nw for x in w]
    lam=sum(a*b for a,b in zip(v,carp(v)))
    i=max(range(d),key=lambda j:abs(v[j]))
    if v[i]<0:v=[-x for x in v]
    return {"bilesen":v,"ozdeger":lam,"aciklanan_oran":lam/toplam}
def hubness_raporu(komsular):
    if not isinstance(komsular,list) or len(komsular)<2:raise ValueError("liste")
    n=len(komsular)
    for k in komsular:
        if not isinstance(k,list) or not k or len(k)!=len(komsular[0]):raise ValueError("k")
    N=[0]*n
    for i,ks in enumerate(komsular):
        if len(set(ks))!=len(ks):raise ValueError("tekrar")
        for j in ks:
            if isinstance(j,bool) or not isinstance(j,int) or not 0<=j<n or j==i:raise ValueError("komşu")
            N[j]+=1
    mu=sum(N)/n
    s2=sum((v-mu)**2 for v in N)/n
    sk=0.0 if s2==0 else sum((v-mu)**3 for v in N)/n/s2**1.5
    i=max(range(n),key=lambda j:N[j])
    return {"n_k":N,"carpiklik":sk,"anti_hub":sum(v==0 for v in N),"en_buyuk_hub":i,"en_buyuk_hub_n":N[i]}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_38 as D
    D.goster(kosinus_kimligi,guc_iterasyonu,hubness_raporu)
```
```hint
Üç işlevi aynen birleştir. Çıktıyı Gaussian taban olmadan yorumlama; aynı sayının rastgele veride ne olduğuna bak.
```
:::

::: anlat Sınır
Bu ders tek gömme modeli ve küçük sentetik şablon derleminde kosinüs geometrisini, etkin boyutu ve hubness'i gösterir; gerçek bir derlemin, başka bir modelin hubness değerini veya hedefli RAG zehirlemesinin başarı oranını göstermez.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Birim kürede Öklid–kosinüs özdeşliği (25 sn).** "$L_2$-normalize gömmelerde $\|u - v\|_2^2 = 2(1 - \cos(u,v))$ tam özdeşliği geçerlidir; bu yüzden birim kürede en yakın Öklid komşusu ile en yüksek kosinüs benzerlikli komşu bire bir aynıdır."
2. **Anizotropi ve etkin boyut (`participation ratio`) (35 sn).** "Dil modeli gömmeleri tüm boyutlara eşit yayılmaz; kovaryans özdeğerlerinden hesaplanan $(\sum \lambda_i)^2 / \sum \lambda_i^2$ katılım oranı, 384 boyutlu uzayın pratikte çok daha düşük etkin boyutta sıkıştığını gösterir."
3. **`Hubness` ve RAG zehirleme yüzeyi (35 sn).** "Yüksek boyut ve anizotropi yüzünden bazı vektörler (`hub`) orantısız sayıda sorgunun ilk-$k$ komşusuna girer; çarpıklık (`skewness`) Gaussian tabanın çok üstündeyse saldırgan tek bir merkezî belgeyle geniş sorgu kümesini etkileyebilir."
4. **Soru (25 sn).** "Gömmeleri ortalama çıkarıp beyazlatmak (`whitening`) veya sorgu-belge simetrisini kırmak `hubness` çarpıklığını nasıl değiştirir?"
:::
