---
id: ai-guvence-37
title: GCG-lite · Birinci Derece Tahmin Ayrık Uzayda Ne Kadar Doğru?
summary: One-hot gradient ile token ikamesinin etkisini tahmin et; zararsız bir hedefle gerçek modelde tahmin ile gerçek loss farkının Spearman ve top-k ilişkisini ölç, aynı sorgu bütçesinde gradient ve rastgele adayları karşılaştır.
esleme: ai-guvence-09, ai-guvence-35
timeout: 60
---

::: anlat Gradient bir karar değil, bir budamadır
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Token uzayı ayrıktır; gradient yalnız bir **tahmin** verir, her aday yine de gerçek loss ile denenmek zorundadır | İlk üç görev: `veri/gcg.json` içindeki **sentetik** gradient ve kayıtlar. Final: SmolLM2-135M, GPU, one-hot gradient ve her aday için gerçek ileri geçiş | Güvenlik hizalamasını, jailbreak başarısını ya da transferi ölçmez. Hedef zararsız ` muz` kelimesidir |
| Birinci derece tahmin ile gerçek değişim arasındaki sıra ilişkisi ölçülebilir | Spearman, top-k kesişimi ve aynı sorgu bütçesinde gradient ile rastgele aday karşılaştırması | Başka model, uzun hedef veya tam GCG davranışı hakkında genel oran vermez |

> [!NOT]
> Görevler `veri/gcg.json` dosyasını okur; dosya sentetiktir. Setup her Çalıştır/Kontrol Et adımında geçici kopya kurar; değişiklikler taşınmaz, **kalıcılık yoktur**. Ekranda ayrı dosya görüntüleyici yoktur; içeriği görmek için `print` kullan. Gizli testler ayrıdır. Final önbellekteki modeli kullanır, indirme yapmaz; zararlı içerik üretmez ve üretmeye çalışmaz.

ai-guvence-09 GCG arama izlerini ve transferi ele alır. Bu ders daha dar bir matematik sorusu sorar: **gradient, ayrık bir değişikliği ne kadar iyi öngörür?**

**Sorun:** Token'lar süreklidir diye davranamayız. `x` token id'si bir tam sayıdır, türevi yoktur. HotFlip (Ebrahimi vd. 2018) ve GCG (Zou vd. 2023) şu hileyi kullanır: pozisyonu bir one-hot vektörü olarak yaz, embedding'i `one_hot @ E` ile hesapla. Artık `g = ∂L/∂one_hot` tanımlıdır ve sözlük boyutunda bir vektördür.

**Tahmin formülü:** `mevcut` tokeni `j` ile değiştirmek one-hot'ta `e_j - e_mevcut` adımıdır. Birinci derece Taylor ile `ΔL(j) ≈ g[j] - g[mevcut]`. Loss düşürmek istediğimiz için **en küçük** değerler adaydır. Formül ai-guvence-35'teki `gᵀδ`'nın aynısıdır, ama bir farkla: adım küçük değildir. `e_j - e_mevcut` köşeden köşeye atlar. Üstelik one-hot'un bir köşesindeki gradient, başka bir köşeyi öngörmeye çalışır. Tahminin zayıf olması şaşırtıcı değil, beklenendir.

**Bu yüzden GCG adayları dener.** Gradient yalnız sözlüğü budar, kararı gerçek ileri geçiş verir. Bu dersin sorusu budama ne kadar değerli olduğudur.

**Spearman neden Pearson değil?** Top-k seçiminde önemli olan büyüklük değil **sıradır**. Spearman, iki listenin sıralarının Pearson korelasyonudur; eşit değerlere ortalama sıra verilir. Sabit bir listenin sırası yoktur, bu durumda korelasyon tanımsızdır ve `None` döner.

**Ölçüm tuzağı · seçim yanlılığı.** Korelasyonu "tahminin en iyi k adayı + rastgele adaylar" kümesinde ölçersen, küme tahmine göre seçildiği için sonuç şişebilir ya da kayabilir. Final iki değeri de raporlar: tüm kümede ve yalnız rastgele adaylarda. Yansız olan ikincisidir.

**Top-k değeri nasıl okunur?** `kesisim`, tahminin k adayı ile gerçekten en iyi k adayın ortak oranıdır; rastgele bir seçimin beklentisi `k/n`'dir. Karşılaştırmasız bir kesişim anlamsızdır. Ayrıca `ort_gercek_topk` ile `ort_gercek_tum` farkı, budamanın gerçek kazancını gösterir.

**Saldırgan ne dener?** Bütçe sınırlıysa her sorguyu değerli adaylara harcar; aynı bütçede rastgele adaylardan daha düşük loss elde etmeyi umar. Bazen fark küçüktür; o zaman gradient hesaplamanın maliyetine değmeyebilir.

**Savunma neden kırılır?** Gradient'i gizlemek (örn. white-box erişimini kaldırmak) budamayı engeller, ama rastgele arama yine çalışır. Yalnız `top-k` sonucu bakıp "gradient sinyali yok" demek de hatalıdır; ölçüm örnek boyutuna ve seçime bağlıdır. Bu dersin rakamları tek bir modelin tek başlangıcıdır.

**Görev 1'de sık tuzaklar:** En büyük gradient'i seçmek loss'u artırır, yön terstir. Mevcut token aday değildir. Yasak (ascii olmayan, özel) tokenlar elenmelidir. Eşitlikte küçük token id'si önce gelir.

Kaynaklar: [Ebrahimi vd. 2018 · HotFlip](https://arxiv.org/abs/1712.06751), [Zou vd. 2023 · GCG](https://arxiv.org/abs/2307.15043). Bu dersteki bütün sayılar yalnız yerel kanıttan gelir.

Köprü: ai-guvence-09 GCG arama izi ve transfer; ai-guvence-35 Taylor kopması. ai-saldiri-35 çok turlu jailbreak ayrı bir konudur, burada kullanılmaz.
:::

::: tahmin Hangi aday önce gelir?
Çıktıyı tahmin et, sonra Çalıştır ile karşılaştır.
```python
g = [0.5, -0.25, 0.25, -1.0]
mevcut = 0
d = sorted((g[j] - g[mevcut], j) for j in range(4) if j != mevcut)
print(d[0])
print(d[-1])
```
???
```cikti
(-1.5, 3)
(-0.25, 2)
```
Tahmininle gerçek çıktı arasındaki farkı tezgâhta yorum satırı olarak yaz: birinci satırdaki sayı gerçek bir loss farkı mı, bir tahmin mi? Bunu öğrenmek için ne yapmak gerekir? Sonra üç kusurlu başlangıç kodunu çalıştır ve neyi yanlış ölçtüklerini önce kendin teşhis et; açıklama çözümün ardından gelir.
:::

::: gorev 1 · One-hot gradient'ten aday seç
`aday_tahmini(g,mevcut,k,yasak)`: `g` en az iki elemanlı liste, bool olmayan sonlu sayılar. `mevcut` bool olmayan int ve geçerli indis. `k` bool olmayan int, `k>=1`. `yasak` `set` veya `frozenset`. `mevcut` ve `yasak` dışındaki her `j` için `tahmin=g[j]-g[mevcut]`. `(tahmin,j)` çiftine göre küçükten büyüğe sırala, en fazla `k` tanesini `[{"token":j,"tahmin":...}]` olarak döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-37")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def aday_tahmini(g,mevcut,k,yasak):
    a=sorted(((g[j],j) for j in range(len(g))),reverse=True)
    return [{"token":j,"tahmin":d} for d,j in a[:k]]

from ai_guvence_veri import json_yukle
v=json_yukle("veri/gcg.json")
a=v["aday"]
print(aday_tahmini(a["g"],a["mevcut"],a["k"],set(a["yasak"])))
```
```test
def sinama1(f):
    import copy,random
    try:
        g=[.5,-.25,.25,-.25,1.0,-1.0];old=list(g)
        if f(g,0,3,set())!=[{"token":5,"tahmin":-1.5},{"token":1,"tahmin":-.75},{"token":3,"tahmin":-.75}] or g!=old:return False
        if f(g,0,3,{5})!=[{"token":1,"tahmin":-.75},{"token":3,"tahmin":-.75},{"token":2,"tahmin":-.25}]:return False
        if f(g,5,1,frozenset())!=[{"token":1,"tahmin":.75}]:return False
        if f([.25,1.0],0,1,set())!=[{"token":1,"tahmin":.75}]:return False
        if len(f(g,0,99,set()))!=5 or f(g,0,1,{1,2,3,4,5})!=[]:return False
        y={1};f(g,0,2,y)
        if y!={1}:return False
        rng=random.Random(37)
        for _ in range(15):
            h=[rng.uniform(-2,2) for _ in range(12)];m=rng.randrange(12);ys=set(rng.sample(range(12),3));n=rng.randint(1,5)
            b=sorted((h[j]-h[m],j) for j in range(12) if j!=m and j not in ys)[:n]
            if f(list(h),m,n,set(ys))!=[{"token":j,"tahmin":d} for d,j in b]:return False
        for bad in ((None,0,1,set()),([1.0],0,1,set()),((1.0,2.0),0,1,set()),([True,1.0],0,1,set()),([float("nan"),1.0],0,1,set()),([float("inf"),1.0],0,1,set()),(["a",1.0],0,1,set()),([1.0,2.0],2,1,set()),([1.0,2.0],-1,1,set()),([1.0,2.0],True,1,set()),([1.0,2.0],.5,1,set()),([1.0,2.0],0,0,set()),([1.0,2.0],0,True,set()),([1.0,2.0],0,1.5,set()),([1.0,2.0],0,1,[1]),([1.0,2.0],0,1,None)):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama1(aday_tahmini),"yön, mevcut ve yasak eleme, eşitlik sırası, geçersiz girdi")
for ad,mut in [("yön ters",lambda g,m,k,y:[dict(d,tahmin=-d["tahmin"]) for d in aday_tahmini(g,m,k,y)]),("yasak yok",lambda g,m,k,y:aday_tahmini(g,m,k,set())),("k yok say",lambda g,m,k,y:aday_tahmini(g,m,len(g),y))]:
    ok(not sinama1(mut),"mutant reddedildi: "+ad)
```
```solution
import math
def aday_tahmini(g,mevcut,k,yasak):
    if not isinstance(g,list) or len(g)<2:raise ValueError("g")
    for v in g:
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError("sayı")
    if isinstance(mevcut,bool) or not isinstance(mevcut,int) or not 0<=mevcut<len(g):raise ValueError("mevcut")
    if isinstance(k,bool) or not isinstance(k,int) or k<1 or not isinstance(yasak,(set,frozenset)):raise ValueError("ayar")
    a=sorted((g[j]-g[mevcut],j) for j in range(len(g)) if j!=mevcut and j not in yasak)
    return [{"token":j,"tahmin":d} for d,j in a[:k]]

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    v=json_yukle("veri/gcg.json")
    a=v["aday"]
    print(aday_tahmini(a["g"],a["mevcut"],a["k"],set(a["yasak"])))
```
```hint
Düşük tahmin iyi aday demek. Farkı mevcut tokene göre al, mevcut ve yasaklıları ele, küçükten büyüğe sırala.
```
:::

::: anlat Sıra neden yeter?
Tahmin ile gerçek değerin birimleri ölçeği aynı olmak zorunda değildir: final kanıtında mutlak tahmin ortalaması gerçek değişimin birkaç katı olabilir. Top-k seçimi için önemli olan yalnız sıradır. Pearson ham değerlerdeki aykırı noktalara duyarlıdır; Spearman değildir.

**Ortalama sıra:** `[1,1,2]` değerleri için sıralar `[1.5, 1.5, 3]` olur. Bağları keyfî sırayla kırmak korelasyonu girdi sırasına bağlar.

**Görev 2'de sık tuzaklar:** Ham değerde Pearson hesaplamak yüksek değerlerin ağırlığını büyütür. Sabit liste sıfıra bölme yaratır; tanımsız sonucu `None` olarak döndür.
:::

::: gorev 2 · Eşitlik doğru Spearman
`spearman(a,b)`: `a`, `b` aynı uzunlukta, en az iki elemanlı liste; bool olmayan sonlu sayılar. Her liste için bağlara ortalama sıra ver (sıralar 1'den başlar), sıraların Pearson korelasyonunu döndür. Listelerden birinin sıraları sabitse `None` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-37")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def spearman(a,b):
    mx=sum(a)/len(a);my=sum(b)/len(b)
    sxx=sum((v-mx)**2 for v in a);syy=sum((v-my)**2 for v in b)
    return sum((p-mx)*(q-my) for p,q in zip(a,b))/math.sqrt(sxx*syy)

from ai_guvence_veri import json_yukle
v=json_yukle("veri/gcg.json")
k=v["kayitlar"]
print("Spearman:",spearman([r["tahmin"] for r in k],[r["gercek"] for r in k]))
print("Eşitlikli:",spearman(v["esitlik"]["a"],v["esitlik"]["b"]))
```
```test
def sinama2(f):
    import copy,math,random
    def _s(a,b):
        def r(v):
            return [sum(w<x for w in v)+(sum(w==x for w in v)+1)/2 for x in v]
        x=r(a);y=r(b);m=sum(x)/len(x);n=sum(y)/len(y)
        c=sum((p-m)**2 for p in x);d=sum((q-n)**2 for q in y)
        if c==0 or d==0:return None
        return sum((p-m)*(q-n) for p,q in zip(x,y))/math.sqrt(c*d)
    try:
        a=[1.0,2.0,3.0,4.0];b=[10.0,100.0,1000.0,10000.0];old=(list(a),list(b))
        if abs(f(a,b)-1)>1e-12 or (a,b)!=old:return False
        if abs(f(a,b[::-1])+1)>1e-12:return False
        if f([1.0,1.0],[1.0,2.0]) is not None or f([1.0,2.0],[3.0,3.0]) is not None:return False
        if abs(f([1.0,2.0,2.0,3.0],[1.0,3.0,2.0,4.0])-_s([1.0,2.0,2.0,3.0],[1.0,3.0,2.0,4.0]))>1e-12:return False
        if abs(f([1,1,1,2],[1,2,3,4])-_s([1,1,1,2],[1,2,3,4]))>1e-12:return False
        if abs(f([2,1,1,1],[1,2,3,4])-_s([2,1,1,1],[1,2,3,4]))>1e-12:return False
        rng=random.Random(373)
        for _ in range(25):
            n=rng.randint(2,10);u=[rng.choice([0,1,2,rng.random()]) for _ in range(n)];w=[rng.choice([0,1,rng.random()]) for _ in range(n)]
            e=_s(u,w);q=f(list(u),list(w))
            if (e is None)!=(q is None) or (e is not None and abs(e-q)>1e-9):return False
        for bad in ((None,[1,2]),([1,2],None),((1,2),[1,2]),([1,2],(1,2)),([1],[1]),([],[]),([1,2],[1,2,3]),([True,2],[1,2]),([1,float("nan")],[1,2]),([1,2],[1,float("inf")]),(["a",1],[1,2])):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama2(spearman),"sıra korelasyonu, ortalama sıra, sabit liste ve geçersiz girdi")
for ad,mut in [("işaret ters",lambda a,b:(lambda v:None if v is None else -v)(spearman(a,b))),("sabit 0",lambda a,b:0.0),("None yerine 0",lambda a,b:(lambda v:0.0 if v is None else v)(spearman(a,b)))]:
    ok(not sinama2(mut),"mutant reddedildi: "+ad)
```
```solution
import math
def spearman(a,b):
    if not isinstance(a,list) or not isinstance(b,list) or len(a)!=len(b) or len(a)<2:raise ValueError("girdi")
    for v in a+b:
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError("sayı")
    def sira(v):
        s=sorted(range(len(v)),key=lambda i:v[i])
        r=[0.0]*len(v)
        i=0
        while i<len(s):
            j=i
            while j+1<len(s) and v[s[j+1]]==v[s[i]]:j+=1
            for t in range(i,j+1):r[s[t]]=(i+j)/2+1
            i=j+1
        return r
    x=sira(a);y=sira(b)
    mx=sum(x)/len(x);my=sum(y)/len(y)
    sxx=sum((v-mx)**2 for v in x);syy=sum((v-my)**2 for v in y)
    if sxx==0 or syy==0:return None
    return sum((p-mx)*(q-my) for p,q in zip(x,y))/math.sqrt(sxx*syy)

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    v=json_yukle("veri/gcg.json")
    k=v["kayitlar"]
    print("Spearman:",spearman([r["tahmin"] for r in k],[r["gercek"] for r in k]))
    print("Eşitlikli:",spearman(v["esitlik"]["a"],v["esitlik"]["b"]))
```
```hint
Önce her listeyi sıraya çevir; aynı değerler aynı ortalama sırayı alsın. Sonra normal Pearson uygula; payda sıfırsa None.
```
:::

::: anlat Rapor kehanet kullanmamalı
Saldırgan `gercek` değerini sorgu yapmadan bilemez. Bu yüzden top-k kümesi **tahmine** göre seçilir, gerçek değer yalnız değerlendirmede kullanılır. Gerçeğe göre seçmek (kehanet) kesişimi her zaman 1 yapar ve hiçbir bilgi taşımaz.

`isabet`: gerçekten en iyi token top-k içinde mi? `kesisim`: tahmin ve gerçek top-k kümelerinin ortak oranı. `rastgele_beklenti`: rastgele k seçimin kesişim beklentisi `k/n`. `iyilesen_oran`: top-k içinde gerçekten loss düşürenlerin oranı (`gercek<0`; sıfır iyileşme değildir). `ort_gercek_topk` ve `ort_gercek_tum`: budamanın ortalama kazancı.

**Görev 3'te sık tuzaklar:** Yanlış paydaya bölmek (`k` yerine `n`) oranı küçültür. Eşitliği kırmamak sonucu girdi sırasına bağlar; eşitlikte küçük token önce gelir.
:::

::: gorev 3 · Top-k raporu ve rastgele karşılaştırma
`topk_isabet(kayitlar,k)`: `kayitlar` dolu liste; her kayıt tam olarak `token` (bool olmayan int, benzersiz), `tahmin`, `gercek` (bool olmayan sonlu sayı). `k` bool olmayan int, `1<=k<=len`. `(tahmin,token)` ile top-k `P`, `(gercek,token)` ile top-k `Q` bul. `{"isabet":(gercek,token) en küçük token P içinde mi,"kesisim":|P∩Q|/k,"rastgele_beklenti":k/n,"iyilesen_oran":P içinde gercek<0 oranı,"ort_gercek_topk":P gerçek ortalaması,"ort_gercek_tum":tüm gerçek ortalaması}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-37")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def topk_isabet(kayitlar,k):
    p=sorted(kayitlar,key=lambda r:r["gercek"])[:k]
    en_iyi=min(kayitlar,key=lambda r:r["gercek"])["token"]
    pk={r["token"] for r in p}
    return {"isabet":en_iyi in pk,"kesisim":1.0,"rastgele_beklenti":k/len(kayitlar),"iyilesen_oran":sum(r["gercek"]<=0 for r in p)/len(kayitlar),"ort_gercek_topk":sum(r["gercek"] for r in p)/k,"ort_gercek_tum":sum(r["gercek"] for r in kayitlar)/len(kayitlar)}

from ai_guvence_veri import json_yukle
v=json_yukle("veri/gcg.json")
print(topk_isabet(v["kayitlar"],v["k"]))
```
```test
def sinama3(f):
    import copy
    try:
        K=[{"token":3,"tahmin":-1.0,"gercek":.5},{"token":1,"tahmin":-.5,"gercek":-.25},{"token":2,"tahmin":.0,"gercek":-1.0},{"token":4,"tahmin":.5,"gercek":.0}];old=copy.deepcopy(K)
        r=f(K,2)
        if K!=old:return False
        if r!={"isabet":False,"kesisim":.5,"rastgele_beklenti":.5,"iyilesen_oran":.5,"ort_gercek_topk":.125,"ort_gercek_tum":-.1875}:return False
        if f(K,3)!={"isabet":True,"kesisim":2/3,"rastgele_beklenti":.75,"iyilesen_oran":2/3,"ort_gercek_topk":-.25,"ort_gercek_tum":-.1875}:return False
        if f(K,1)["kesisim"]!=0.0 or f(K,4)["kesisim"]!=1.0:return False
        e=[{"token":5,"tahmin":.0,"gercek":.0},{"token":2,"tahmin":.0,"gercek":.0},{"token":9,"tahmin":.5,"gercek":.5}]
        if f(e,1)!={"isabet":True,"kesisim":1.0,"rastgele_beklenti":1/3,"iyilesen_oran":.0,"ort_gercek_topk":.0,"ort_gercek_tum":1/6}:return False
        if f(list(reversed(K)),2)!=r:return False
        a=K[0]
        for sa,k in ((None,1),([],1),(K,0),(K,5),(K,True),(K,1.0),((a,),1),([None],1),([dict(a,ek=1)],1),([{"token":1,"tahmin":1}],1),([dict(a,token=True)],1),([dict(a,token="a")],1),([a,a],1),([dict(a,tahmin=True)],1),([dict(a,gercek=float("nan"))],1),([dict(a,tahmin=float("inf"))],1),([dict(a,gercek="a")],1)):
            try:f(sa,k);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama3(topk_isabet),"tahmine göre seçim, kesişim, beklenti, eşitlik ve geçersiz girdi")
for ad,mut in [("kesişim hep 1",lambda s,k:dict(topk_isabet(s,k),kesisim=1.0)),("beklenti yok",lambda s,k:dict(topk_isabet(s,k),rastgele_beklenti=0.0)),("isabet ters",lambda s,k:dict(topk_isabet(s,k),isabet=not topk_isabet(s,k)["isabet"]))]:
    ok(not sinama3(mut),"mutant reddedildi: "+ad)
```
```solution
import math
def topk_isabet(kayitlar,k):
    if not isinstance(kayitlar,list) or not kayitlar or isinstance(k,bool) or not isinstance(k,int) or not 1<=k<=len(kayitlar):raise ValueError("girdi")
    gorulen=set()
    for r in kayitlar:
        if not isinstance(r,dict) or set(r)!={"token","tahmin","gercek"}:raise ValueError("şema")
        if isinstance(r["token"],bool) or not isinstance(r["token"],int) or r["token"] in gorulen:raise ValueError("token")
        for a in ("tahmin","gercek"):
            if isinstance(r[a],bool) or not isinstance(r[a],(int,float)) or not math.isfinite(r[a]):raise ValueError("sayı")
        gorulen.add(r["token"])
    p=sorted(kayitlar,key=lambda r:(r["tahmin"],r["token"]))[:k]
    q=sorted(kayitlar,key=lambda r:(r["gercek"],r["token"]))[:k]
    en_iyi=min(kayitlar,key=lambda r:(r["gercek"],r["token"]))["token"]
    pk={r["token"] for r in p}
    return {"isabet":en_iyi in pk,"kesisim":len(pk&{r["token"] for r in q})/k,"rastgele_beklenti":k/len(kayitlar),"iyilesen_oran":sum(r["gercek"]<0 for r in p)/k,"ort_gercek_topk":sum(r["gercek"] for r in p)/k,"ort_gercek_tum":sum(r["gercek"] for r in kayitlar)/len(kayitlar)}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    v=json_yukle("veri/gcg.json")
    print(topk_isabet(v["kayitlar"],v["k"]))
```
```hint
P tahmine, Q gerçeğe göre seçilir. Eşitliği token ile kır. Oranlar k'ya bölünür, tüm ortalama n'ye.
```
:::

::: anlat Hata vitrini · çalışmış yanlış rapor
Yazar, kusurlu başlangıç kodlarını görünür sentetik veriyle gerçekten çalıştırdı ve sonucu `outputs/yeni-ai-guvence-37/gorunur-run-1.json` dosyasına kaydetti. `veri/gcg.json` kayıtlarında kusurlu kod `kesisim=1.0`, `isabet=True` verir; doğru kod `kesisim=0.333`, `isabet=False`, `rastgele_beklenti=0.375` verir.

Bu kaydedilmiş bir hesaplama çıktısıdır, model yanıtı değildir ve kayıtlar sentetiktir. Kusurlu raporu görüp "gradient tahmini kusursuz" diyen biri neyi kaçırır? Top-k kümesi neye göre seçilmişti? Kendi cümlenle açıkla. Gerçek finaldeki ölçüm ayrıca üretilir; bu sayılar onun yerine konmaz.
:::

::: anlat Gerçek deney: tahmin ve olgu, aynı sorgu bütçesi
Final kısa, zararsız bir Türkçe önek ile 8 rastgele sonek tokeni kurar ve ` muz` hedefinin cross-entropy loss'unu ölçer. Yalnız harf içeren token'lar aday olabilir; özel tokenlar `yasak` kümesindedir.

Rastgele 4 pozisyonda: (1) one-hot gradient alınır, **senin `aday_tahmini`** en iyi 32 adayı seçer. (2) 128 rastgele aday eklenir. (3) Her aday için model gerçekten yeniden koşar ve `gercek` loss farkı ölçülür. (4) `spearman` ve `topk_isabet` raporu üretilir; Spearman hem bütün kümede hem yalnız rastgele adaylarda hesaplanır.

Sonra iki küçük açgözlü arama aynı sorgu bütçesiyle yürür: biri senin `aday_tahmini`, diğeri rastgele aday kullanır. İkisi de aynı başlangıçtan başlar.

Kabul, çıktılarının bağımsız referansla aynı olmasına ve bütçelerin eşit olmasına bağlıdır. **Hedefe ulaşmak kabul şartı değildir;** gradient aramasının rastgeleyi geçmesi de şart değildir.

**Kanıt dosyasını oku:** `pozisyonlar` içinde `spearman` ve `spearman_rastgele` değerlerini karşılaştır. Soru 1: hangisi seçim yanlılığından etkilenir? Soru 2: `tahmin_ort_mutlak` ile `gercek_ort_mutlak` aynı büyüklükte mi; bu sayı top-k için önemli mi? Soru 3: `gradyan_arama` ve `rastgele_arama` izlerini adım adım karşılaştır. Tek koşudan ne kadar genelleyebilirsin? İkinci kez çalıştırıp farkın kaldığını gör. Cevabını tezgâhta yorum olarak yaz; otomatik test bu serbest açıklamayı puanlamaz.
:::

::: gorev Gerçek deney · SmolLM2 üzerinde birinci derece tahminin ölçümü
Önceki üç görevin `aday_tahmini`, `spearman` ve `topk_isabet` işlevlerini birleştir. Çalıştır gerçek ölçümü gösterir; Kontrol Et önce üç sözleşmeyi gizli verilerle sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
ortam: gpu
timeout: 280
```
```starter
import ai_lab
import math
def aday_tahmini(g,mevcut,k,yasak):
    a=sorted(((g[j],j) for j in range(len(g))),reverse=True)
    return [{"token":j,"tahmin":d} for d,j in a[:k]]
def spearman(a,b):
    mx=sum(a)/len(a);my=sum(b)/len(b)
    sxx=sum((v-mx)**2 for v in a);syy=sum((v-my)**2 for v in b)
    return sum((p-mx)*(q-my) for p,q in zip(a,b))/math.sqrt(sxx*syy)
def topk_isabet(kayitlar,k):
    p=sorted(kayitlar,key=lambda r:r["gercek"])[:k]
    en_iyi=min(kayitlar,key=lambda r:r["gercek"])["token"]
    pk={r["token"] for r in p}
    return {"isabet":en_iyi in pk,"kesisim":1.0,"rastgele_beklenti":k/len(kayitlar),"iyilesen_oran":sum(r["gercek"]<=0 for r in p)/len(kayitlar),"ort_gercek_topk":sum(r["gercek"] for r in p)/k,"ort_gercek_tum":sum(r["gercek"] for r in kayitlar)/len(kayitlar)}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_37 as D
    D.goster(aday_tahmini,spearman,topk_isabet)
```
```test
import ai_lab,math
checks=[]
def kontrol(x,m):checks.append(bool(x));ok(x,m)
issues=ai_lab.kod_denetimi(src,('referans_aday', 'referans_spearman', 'referans_isabet', 'kanit_yaz', '_yakin'),izin=())
kontrol(not issues,"kopya/yama/dinamik kod yok: "+str(issues))
if issues:stop()
aday_tahmini=need("aday_tahmini")
spearman=need("spearman")
topk_isabet=need("topk_isabet")
def sinama1(f):
    import copy,random
    try:
        g=[.5,-.25,.25,-.25,1.0,-1.0];old=list(g)
        if f(g,0,3,set())!=[{"token":5,"tahmin":-1.5},{"token":1,"tahmin":-.75},{"token":3,"tahmin":-.75}] or g!=old:return False
        if f(g,0,3,{5})!=[{"token":1,"tahmin":-.75},{"token":3,"tahmin":-.75},{"token":2,"tahmin":-.25}]:return False
        if f(g,5,1,frozenset())!=[{"token":1,"tahmin":.75}]:return False
        if f([.25,1.0],0,1,set())!=[{"token":1,"tahmin":.75}]:return False
        if len(f(g,0,99,set()))!=5 or f(g,0,1,{1,2,3,4,5})!=[]:return False
        y={1};f(g,0,2,y)
        if y!={1}:return False
        rng=random.Random(37)
        for _ in range(15):
            h=[rng.uniform(-2,2) for _ in range(12)];m=rng.randrange(12);ys=set(rng.sample(range(12),3));n=rng.randint(1,5)
            b=sorted((h[j]-h[m],j) for j in range(12) if j!=m and j not in ys)[:n]
            if f(list(h),m,n,set(ys))!=[{"token":j,"tahmin":d} for d,j in b]:return False
        for bad in ((None,0,1,set()),([1.0],0,1,set()),((1.0,2.0),0,1,set()),([True,1.0],0,1,set()),([float("nan"),1.0],0,1,set()),([float("inf"),1.0],0,1,set()),(["a",1.0],0,1,set()),([1.0,2.0],2,1,set()),([1.0,2.0],-1,1,set()),([1.0,2.0],True,1,set()),([1.0,2.0],.5,1,set()),([1.0,2.0],0,0,set()),([1.0,2.0],0,True,set()),([1.0,2.0],0,1.5,set()),([1.0,2.0],0,1,[1]),([1.0,2.0],0,1,None)):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
kontrol(sinama1(aday_tahmini),"yön, mevcut ve yasak eleme, eşitlik sırası, geçersiz girdi")
for ad,mut in [("yön ters",lambda g,m,k,y:[dict(d,tahmin=-d["tahmin"]) for d in aday_tahmini(g,m,k,y)]),("yasak yok",lambda g,m,k,y:aday_tahmini(g,m,k,set())),("k yok say",lambda g,m,k,y:aday_tahmini(g,m,len(g),y))]:
    kontrol(not sinama1(mut),"mutant reddedildi: "+ad)
def sinama2(f):
    import copy,math,random
    def _s(a,b):
        def r(v):
            return [sum(w<x for w in v)+(sum(w==x for w in v)+1)/2 for x in v]
        x=r(a);y=r(b);m=sum(x)/len(x);n=sum(y)/len(y)
        c=sum((p-m)**2 for p in x);d=sum((q-n)**2 for q in y)
        if c==0 or d==0:return None
        return sum((p-m)*(q-n) for p,q in zip(x,y))/math.sqrt(c*d)
    try:
        a=[1.0,2.0,3.0,4.0];b=[10.0,100.0,1000.0,10000.0];old=(list(a),list(b))
        if abs(f(a,b)-1)>1e-12 or (a,b)!=old:return False
        if abs(f(a,b[::-1])+1)>1e-12:return False
        if f([1.0,1.0],[1.0,2.0]) is not None or f([1.0,2.0],[3.0,3.0]) is not None:return False
        if abs(f([1.0,2.0,2.0,3.0],[1.0,3.0,2.0,4.0])-_s([1.0,2.0,2.0,3.0],[1.0,3.0,2.0,4.0]))>1e-12:return False
        if abs(f([1,1,1,2],[1,2,3,4])-_s([1,1,1,2],[1,2,3,4]))>1e-12:return False
        if abs(f([2,1,1,1],[1,2,3,4])-_s([2,1,1,1],[1,2,3,4]))>1e-12:return False
        rng=random.Random(373)
        for _ in range(25):
            n=rng.randint(2,10);u=[rng.choice([0,1,2,rng.random()]) for _ in range(n)];w=[rng.choice([0,1,rng.random()]) for _ in range(n)]
            e=_s(u,w);q=f(list(u),list(w))
            if (e is None)!=(q is None) or (e is not None and abs(e-q)>1e-9):return False
        for bad in ((None,[1,2]),([1,2],None),((1,2),[1,2]),([1,2],(1,2)),([1],[1]),([],[]),([1,2],[1,2,3]),([True,2],[1,2]),([1,float("nan")],[1,2]),([1,2],[1,float("inf")]),(["a",1],[1,2])):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
kontrol(sinama2(spearman),"sıra korelasyonu, ortalama sıra, sabit liste ve geçersiz girdi")
for ad,mut in [("işaret ters",lambda a,b:(lambda v:None if v is None else -v)(spearman(a,b))),("sabit 0",lambda a,b:0.0),("None yerine 0",lambda a,b:(lambda v:0.0 if v is None else v)(spearman(a,b)))]:
    kontrol(not sinama2(mut),"mutant reddedildi: "+ad)
def sinama3(f):
    import copy
    try:
        K=[{"token":3,"tahmin":-1.0,"gercek":.5},{"token":1,"tahmin":-.5,"gercek":-.25},{"token":2,"tahmin":.0,"gercek":-1.0},{"token":4,"tahmin":.5,"gercek":.0}];old=copy.deepcopy(K)
        r=f(K,2)
        if K!=old:return False
        if r!={"isabet":False,"kesisim":.5,"rastgele_beklenti":.5,"iyilesen_oran":.5,"ort_gercek_topk":.125,"ort_gercek_tum":-.1875}:return False
        if f(K,3)!={"isabet":True,"kesisim":2/3,"rastgele_beklenti":.75,"iyilesen_oran":2/3,"ort_gercek_topk":-.25,"ort_gercek_tum":-.1875}:return False
        if f(K,1)["kesisim"]!=0.0 or f(K,4)["kesisim"]!=1.0:return False
        e=[{"token":5,"tahmin":.0,"gercek":.0},{"token":2,"tahmin":.0,"gercek":.0},{"token":9,"tahmin":.5,"gercek":.5}]
        if f(e,1)!={"isabet":True,"kesisim":1.0,"rastgele_beklenti":1/3,"iyilesen_oran":.0,"ort_gercek_topk":.0,"ort_gercek_tum":1/6}:return False
        if f(list(reversed(K)),2)!=r:return False
        a=K[0]
        for sa,k in ((None,1),([],1),(K,0),(K,5),(K,True),(K,1.0),((a,),1),([None],1),([dict(a,ek=1)],1),([{"token":1,"tahmin":1}],1),([dict(a,token=True)],1),([dict(a,token="a")],1),([a,a],1),([dict(a,tahmin=True)],1),([dict(a,gercek=float("nan"))],1),([dict(a,tahmin=float("inf"))],1),([dict(a,gercek="a")],1)):
            try:f(sa,k);return False
            except ValueError:pass
        return True
    except Exception:return False
kontrol(sinama3(topk_isabet),"tahmine göre seçim, kesişim, beklenti, eşitlik ve geçersiz girdi")
for ad,mut in [("kesişim hep 1",lambda s,k:dict(topk_isabet(s,k),kesisim=1.0)),("beklenti yok",lambda s,k:dict(topk_isabet(s,k),rastgele_beklenti=0.0)),("isabet ters",lambda s,k:dict(topk_isabet(s,k),isabet=not topk_isabet(s,k)["isabet"]))]:
    kontrol(not sinama3(mut),"mutant reddedildi: "+ad)
if not all(checks):stop()
from sandbox import ai_gercek_ai_guvence_37 as D
try:r=D.deney(aday_tahmini,spearman,topk_isabet)
except ai_lab.GercekLabYok as e:
    kontrol(False,"gerçek deney yok: "+str(e));stop()
kontrol(r["aday_ayni"],"gerçek gradient'te adaylar bağımsız hesapla aynı")
kontrol(r["spearman_ayni"],"gerçek ölçümlerde Spearman bağımsız hesapla aynı")
kontrol(r["isabet_ayni"],"gerçek ölçümlerde top-k raporu bağımsız hesapla aynı")
kontrol(r["gradyan_arama"]["sorgu"]==r["rastgele_arama"]["sorgu"]>0,"iki aramanın sorgu bütçesi eşit")
kontrol(len(r["pozisyonlar"])==r["ayarlar"]["pozisyon"],"bütün pozisyonlar ölçüldü")
kontrol(all(a>=b for a,b in zip(r["gradyan_arama"]["iz"],r["gradyan_arama"]["iz"][1:])),"açgözlü iz kötüleşmedi")
kontrol(r["ayarlar"]["hedef"]==" muz","hedef zararsız sabit kelime")
ai_lab.kanit_yaz("ai-guvence-37-kabul",{"kaynak":"gercek","kabul":all(checks),"ders":"ai-guvence-37","deney":r})
```
```solution
import ai_lab
import math
def aday_tahmini(g,mevcut,k,yasak):
    if not isinstance(g,list) or len(g)<2:raise ValueError("g")
    for v in g:
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError("sayı")
    if isinstance(mevcut,bool) or not isinstance(mevcut,int) or not 0<=mevcut<len(g):raise ValueError("mevcut")
    if isinstance(k,bool) or not isinstance(k,int) or k<1 or not isinstance(yasak,(set,frozenset)):raise ValueError("ayar")
    a=sorted((g[j]-g[mevcut],j) for j in range(len(g)) if j!=mevcut and j not in yasak)
    return [{"token":j,"tahmin":d} for d,j in a[:k]]
def spearman(a,b):
    if not isinstance(a,list) or not isinstance(b,list) or len(a)!=len(b) or len(a)<2:raise ValueError("girdi")
    for v in a+b:
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError("sayı")
    def sira(v):
        s=sorted(range(len(v)),key=lambda i:v[i])
        r=[0.0]*len(v)
        i=0
        while i<len(s):
            j=i
            while j+1<len(s) and v[s[j+1]]==v[s[i]]:j+=1
            for t in range(i,j+1):r[s[t]]=(i+j)/2+1
            i=j+1
        return r
    x=sira(a);y=sira(b)
    mx=sum(x)/len(x);my=sum(y)/len(y)
    sxx=sum((v-mx)**2 for v in x);syy=sum((v-my)**2 for v in y)
    if sxx==0 or syy==0:return None
    return sum((p-mx)*(q-my) for p,q in zip(x,y))/math.sqrt(sxx*syy)
def topk_isabet(kayitlar,k):
    if not isinstance(kayitlar,list) or not kayitlar or isinstance(k,bool) or not isinstance(k,int) or not 1<=k<=len(kayitlar):raise ValueError("girdi")
    gorulen=set()
    for r in kayitlar:
        if not isinstance(r,dict) or set(r)!={"token","tahmin","gercek"}:raise ValueError("şema")
        if isinstance(r["token"],bool) or not isinstance(r["token"],int) or r["token"] in gorulen:raise ValueError("token")
        for a in ("tahmin","gercek"):
            if isinstance(r[a],bool) or not isinstance(r[a],(int,float)) or not math.isfinite(r[a]):raise ValueError("sayı")
        gorulen.add(r["token"])
    p=sorted(kayitlar,key=lambda r:(r["tahmin"],r["token"]))[:k]
    q=sorted(kayitlar,key=lambda r:(r["gercek"],r["token"]))[:k]
    en_iyi=min(kayitlar,key=lambda r:(r["gercek"],r["token"]))["token"]
    pk={r["token"] for r in p}
    return {"isabet":en_iyi in pk,"kesisim":len(pk&{r["token"] for r in q})/k,"rastgele_beklenti":k/len(kayitlar),"iyilesen_oran":sum(r["gercek"]<0 for r in p)/k,"ort_gercek_topk":sum(r["gercek"] for r in p)/k,"ort_gercek_tum":sum(r["gercek"] for r in kayitlar)/len(kayitlar)}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_37 as D
    D.goster(aday_tahmini,spearman,topk_isabet)
```
```hint
Üç işlevi aynen birleştir. Kanıtı okurken yansız Spearman değerine ve rastgeleyle farka bak; tek başına yüksek bir sayıya güvenme.
```
:::

::: anlat Sınır
Bu ders SmolLM2-135M üzerinde zararsız kısa bir hedefle, tek rastgele başlangıçta birinci derece token tahmininin ne kadar doğru olduğunu gösterir; güvenlik hizalaması, jailbreak başarısı, transfer veya büyük modeller için genel bir oran göstermez.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Ayrık token uzayında sürekli gradyan köprüsü (35 sn).** "Token kimliklerinde küçük $\varepsilon$ adımı atamayız; `GCG` mevcut tokenin gömme gradyanı $g$ ile tüm sözlük farklarının iç çarpımı $(e_j - e_{\text{mevcut}})^\top g$'yi hesaplayıp kaybı en çok düşürmesi beklenen ilk-$k$ adayı tek geri yayılımla seçer."
2. **Birinci derece tahminin doğrulanması (30 sn).** "Adayların tahmini $\Delta L$ sıralaması gerçek ileri geçiş kayıplarıyla `Spearman` sıra korelasyonu ve `top-k` kesişimi üzerinden ölçülür; büyük gömme sıçramalarında doğrusal tahmin kusursuz değildir."
3. **Seçim yanlılığına karşı yansız örneklem (30 sn).** "Yalnız tahminin seçtiği uç adaylara bakmak korelasyonu şişirir veya çarpıtır; sözlükten rastgele çekilen yansız örneklemle karşılaştırma gerçek tahmin gücünü gösterir."
4. **Soru (25 sn).** "`GCG` birinci derece gradyan tahminine tam güvenmek yerine neden her adımda ilk-$k$ adayı gerçek ileri geçişle yeniden değerlendirir?"
:::
