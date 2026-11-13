---
id: ai-guvence-35
title: Dual Norm ve Taylor · FGSM'in Matematiği
summary: Merkezi farkla autograd'ı doğrula, L∞/L2/L1 bütçelerinde en iyi bozuntuyu dual norm ile türet ve gerçek bir MLP'de birinci derece Taylor tahmininin koptuğu ε değerini ölç.
esleme: ai-guvence-07, ai-guvence-08, ai-guvence-36
timeout: 60
---

::: anlat FGSM bir hile değil, bir optimizasyon cevabıdır
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| FGSM'in `sign(g)` kullanması keyfî değildir: L∞ topu içinde loss'un birinci derece artışını en büyükleyen çözümdür; L2 ve L1 için çözüm başkadır | İlk üç görev: `veri/taylor.json` içindeki **sentetik** gradyan ve Taylor satırları. Final: sklearn `load_digits` üzerinde gerçekten eğitilen 64-48-10 GELU MLP, torch autograd, float64, CPU | Büyük modellerde, ReLU ağlarda veya `[0,1]` kutusu uygulanınca kopma noktasının nerede olacağını söylemez |
| Birinci derece tahmin küçük ε'da doğrudur, sonra kopar; kopma noktası ölçülebilir | Hessian-vector product ile ikinci derece tahmin ve gerçek loss farkı | Hiçbir norm için saldırının en iyi olduğunu kanıtlamaz; yalnız yerel doğrusal yaklaşımı ölçer |

> [!NOT]
> Görevler `veri/taylor.json` dosyasını okur; dosya sentetiktir, gerçek model çıktısı değildir. Setup her Çalıştır/Kontrol Et adımında geçici kopya kurar; değişiklikler sonraki çalıştırmaya taşınmaz, **kalıcılık yoktur**. Ekranda ayrı dosya görüntüleyici yoktur; içeriği görmek için `print` kullan. Gizli testler ayrıdır. Final yeni model indirmez; `load_digits` scikit-learn ile gelir. Final bilerek CPU'da koşar: merkezi fark float64 ister, model küçüktür.

ai-guvence-07 FGSM'i uygular, ai-guvence-08 PGD eğrisini çıkarır. Bu ders **neden o formül** sorusunu sorar.

**Başlangıç noktası Taylor açılımıdır.** Girdiyi `x`'ten `x+δ`'ya taşıyınca loss yaklaşık şu kadar değişir: `L(x+δ) - L(x) ≈ gᵀδ + ½ δᵀHδ`. Burada `g` girdiye göre gradient, `H` Hessian'dır. δ küçükse ikinci terim önemsizdir ve saldırganın problemi doğrusal bir hâle gelir: `‖δ‖ ≤ ε` kısıtı altında `gᵀδ` değerini en büyükle.

**Bu problemin cevabı dual norm'dur.** Tanım: `‖g‖* = max {gᵀδ : ‖δ‖ ≤ 1}`. Yani bütçe topunun şekli, hangi yönün en iyi olduğunu ve kazancın ne kadar olacağını birlikte belirler:

| Bütçe | En iyi δ | Birinci derece kazanç |
|---|---|---|
| L∞ (her koordinat ±ε) | `ε · sign(g)` | `ε · ‖g‖₁` |
| L2 (toplam enerji ε) | `ε · g / ‖g‖₂` | `ε · ‖g‖₂` |
| L1 (toplam değişim ε) | tüm ε, mutlak gradient'i en büyük koordinata | `ε · ‖g‖∞` |

FGSM bu tablonun ilk satırıdır: küçük bir hile değil, doğrusal problemin kapalı çözümüdür (Goodfellow vd. 2015). Sonuç olarak aynı ε iki farklı normda aynı saldırı gücü demek değildir. 64 boyutta `‖g‖₁`, `‖g‖₂`'nin katlarıdır; rapor edilen "ε=0.1" normu yazılmadan anlamsızdır.

**Önce gradient'in doğruluğu.** Bütün bu hesaplar gradient doğruysa geçerlidir. Bunu sınamanın klasik yolu merkezi farktır: `(L(x+h·e_i) - L(x-h·e_i)) / 2h`. İleri farkın hatası O(h), merkezi farkın O(h²)'dir. Bu yüzden görev 1 ileri farkı kabul etmez. float32'de merkezi fark gürültüye boğulur; final bu nedenle float64 kullanır.

**Saldırgan ne dener?** Elindeki bütçeye uygun yönü seçer. Kısa hesap: gradient seyrek değilse L∞'da kazanç boyutla büyür; bu yüzden yüksek boyutlu girdiler L∞ altında daha kırılgandır.

**Savunma neden kırılır?** "Gradient küçük, model sağlam" çıkarımı yanlıştır. Çok güvenli tahminde softmax doygundur, `g` küçülür; birinci derece tahmin çok az artış öngörür. Ama loss doğrusal değildir: az bir ilerleme doygunluktan çıkarır ve gerçek artış tahminin onlarca katına çıkabilir. Final tablosunda bunu kendi ölçümünle göreceksin. ai-guvence-36 bu boşluğun bir savunma yanılsamasına nasıl dönüştüğünü gösterir.

**Görev 1'de sık tuzaklar:** İleri fark kullanmak hatayı büyütür ve `h` seçimine bağlı kılar. Mutlak hata, büyük gradient'lerde her şeyi hata gösterir; bu yüzden `max(1, |n|, |a|)` paydası kullanılır. Tol sınırı dahildir.

Kaynaklar: [Goodfellow vd. 2015](https://arxiv.org/abs/1412.6572), [Madry vd. 2018](https://arxiv.org/abs/1706.06083). Bu dersteki bütün sayılar yalnız yerel kanıttan gelir.

Köprü: ai-guvence-07 FGSM, ai-guvence-08 PGD. Sıradaki ai-guvence-36 aynı doygunluğu gradient masking olarak ölçer.
:::

::: tahmin Aynı gradient, üç farklı bütçe
Çıktıyı tahmin et, sonra Çalıştır ile karşılaştır.
```python
g = [3.0, -4.0, 0.0]
eps = 0.1
print(round(eps * sum(abs(v) for v in g), 4))
print(round(eps * sum(v * v for v in g) ** 0.5, 4))
print(round(eps * max(abs(v) for v in g), 4))
```
???
```cikti
0.7
0.5
0.4
```
Tahmininle gerçek çıktı arasındaki farkı tezgâhta yorum satırı olarak yaz: hangi satır hangi normun kazancı, neden aynı ε üç farklı sonuç veriyor? Sonra üç kusurlu başlangıç kodunu çalıştır. Hangisi fark yöntemini, hangisi dual norm'u, hangisi kopma noktasını bozuyor? Önce kendin teşhis et; açıklama çözümün ardından gelir.
:::

::: gorev 1 · Autograd'ı merkezi farkla denetle
`gradyan_denetle(f,x,analitik,h,tol)`: `x` ve `analitik` aynı uzunlukta, dolu liste; elemanlar bool olmayan sonlu sayı. `h` ve `tol` bool olmayan, sonlu, pozitif sayı. Her koordinat için merkezi fark `(f(x+h·e_i)-f(x-h·e_i))/(2h)` hesapla (`f`'e yeni liste ver). Göreli hata `|n-a|/max(1,|n|,|a|)`; en büyüğünü al. `{"sayisal":[...],"maks_goreli_hata":...,"gecti":hata<=tol}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-35")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def gradyan_denetle(f,x,analitik,h,tol):
    sayisal=[];hata=0.0
    for i in range(len(x)):
        a=list(x)
        a[i]+=h
        n=(f(a)-f(x))/h
        sayisal.append(n)
        hata=max(hata,abs(n-analitik[i]))
    return {"sayisal":sayisal,"maks_goreli_hata":hata,"gecti":hata<tol}

from ai_guvence_veri import json_yukle
v=json_yukle("veri/taylor.json")
k=v["katsayilar"]
def kayip(x):return x[0]**k[0]+k[1]*x[0]*x[1]
print("Doğru gradyan:",gradyan_denetle(kayip,v["nokta"],v["dogru_gradyan"],v["h"],v["tol"]))
print("Yanlış gradyan:",gradyan_denetle(kayip,v["nokta"],v["yanlis_gradyan"],v["h"],v["tol"]))
```
```test
def sinama1(f):
    import copy,math
    def _r(k,x,a,h,tol):
        s=[];e=0.0
        for i in range(len(x)):
            p=list(x);q=list(x);p[i]+=h;q[i]-=h
            n=(k(p)-k(q))/(2*h);s.append(n);e=max(e,abs(n-a[i])/max(1.0,abs(n),abs(a[i])))
        return {"sayisal":s,"maks_goreli_hata":e,"gecti":e<=tol}
    try:
        kup=lambda v:v[0]**3+math.sin(v[1])*v[2]
        x=[2.0,0.5,-1.5];a=[12.0,-1.5*math.cos(0.5),math.sin(0.5)];old=(list(x),list(a))
        if f(kup,x,a,1e-3,1e-4)!=_r(kup,x,a,1e-3,1e-4) or (x,a)!=old:return False
        if not f(kup,x,a,1e-3,1e-4)["gecti"]:return False
        k=lambda v:0.0
        if f(k,[1.0],[0.5],0.5,0.5)!={"sayisal":[0.0],"maks_goreli_hata":0.5,"gecti":True}:return False
        if f(k,[1.0],[0.5],0.5,0.25)["gecti"] is not False:return False
        if f(k,[1.0],[4.0],0.5,0.25)["maks_goreli_hata"]!=1.0:return False
        d=lambda v:1000.0*v[0]
        if abs(f(d,[1.0],[1024.0],0.5,0.5)["maks_goreli_hata"]-24/1024)>1e-9:return False
        if abs(f(lambda v:-1000.0*v[0],[1.0],[-1024.0],0.5,0.5)["maks_goreli_hata"]-24/1024)>1e-9:return False
        if abs(f(lambda v:1024.0*v[0],[1.0],[1000.0],0.5,0.5)["maks_goreli_hata"]-24/1024)>1e-9:return False
        if abs(f(lambda v:v[0]+3*v[1],[1.0,1.0],[1.0,3.5],0.5,0.5)["maks_goreli_hata"]-0.5/3.5)>1e-9:return False
        if f(lambda v:v[0]+3*v[1],[1.0,1.0],[1.5,3.0],0.5,0.5)["maks_goreli_hata"]!=0.5/1.5:return False
        g=[1.0]
        for bad in ((k,None,g,.1,.1),(k,[],[],.1,.1),(k,g,[],.1,.1),(k,g,None,.1,.1),(k,(1.0,),g,.1,.1),(k,[True],g,.1,.1),(k,[float("nan")],g,.1,.1),(k,g,[float("inf")],.1,.1),(k,g,g,0,.1),(k,g,g,-.1,.1),(k,g,g,.1,0),(k,g,g,.1,-1),(k,g,g,True,.1),(k,g,g,.1,True),(k,g,g,float("nan"),.1),(k,g,g,.1,float("inf")),(k,g,g,"a",.1)):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama1(gradyan_denetle),"merkezi fark, göreli hata, dahil tol ve geçersiz girdi")
for ad,mut in [("ileri fark",lambda k,x,a,h,t:dict(gradyan_denetle(k,x,a,h,t),sayisal=[(k([v+h if j==i else v for j,v in enumerate(x)])-k(x))/h for i in range(len(x))])),("sonuç her zaman geçer",lambda k,x,a,h,t:dict(gradyan_denetle(k,x,a,h,t),gecti=True)),("hata hep sıfır",lambda k,x,a,h,t:dict(gradyan_denetle(k,x,a,h,t),maks_goreli_hata=0.0))]:
    ok(not sinama1(mut),"mutant reddedildi: "+ad)
```
```solution
import math
def gradyan_denetle(f,x,analitik,h,tol):
    if not isinstance(x,list) or not x or not isinstance(analitik,list) or len(analitik)!=len(x):raise ValueError("boyut")
    for v in x+analitik+[h,tol]:
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError("sayı")
    if h<=0 or tol<=0:raise ValueError("ayar")
    sayisal=[];hata=0.0
    for i in range(len(x)):
        a=list(x);b=list(x)
        a[i]+=h;b[i]-=h
        n=(f(a)-f(b))/(2*h)
        sayisal.append(n)
        hata=max(hata,abs(n-analitik[i])/max(1.0,abs(n),abs(analitik[i])))
    return {"sayisal":sayisal,"maks_goreli_hata":hata,"gecti":hata<=tol}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    v=json_yukle("veri/taylor.json")
    k=v["katsayilar"]
    def kayip(x):return x[0]**k[0]+k[1]*x[0]*x[1]
    print("Doğru gradyan:",gradyan_denetle(kayip,v["nokta"],v["dogru_gradyan"],v["h"],v["tol"]))
    print("Yanlış gradyan:",gradyan_denetle(kayip,v["nokta"],v["yanlis_gradyan"],v["h"],v["tol"]))
```
```hint
İki yönlü fark al ve payda olarak max(1,|n|,|a|) kullan. Her koordinat için x'in iki ayrı kopyasını oluştur.
```
:::

::: anlat Doğrusal problem çözüldü, peki ne zaman geçerli?
Görev 2'deki kapalı çözüm yalnız `gᵀδ` için en iyidir. İki özelliği her zaman sınayabilirsin: `gᵀδ` değeri `tahmini_artis` değerine eşit olmalı ve δ'nın ilgili normu tam ε olmalıdır (gradient sıfır değilse). Bu iki eşitlik görevin testinde rastgele gradient'lerle sınanır.

**Görev 2'de sık tuzaklar:** `sign(0)` değerini -1 saymak sıfır gradient'li koordinatı boşuna bozar ve L∞ kazancını yanlış gösterir. L2'de normalize etmemek bütçeyi aşar. L1'de bütün koordinatlara dağıtmak bütçeyi aşar; en büyük `|g|` koordinatında eşitlik varsa en küçük indis seçilir. Kazanç formülünü başka normla yazmak dual norm eşlemesini bozar.
:::

::: gorev 2 · Bütçeye göre en iyi bozuntu
`en_iyi_bozuntu(g,eps,norm)`: `g` dolu liste, elemanları ve `eps` bool olmayan sonlu sayı, `eps>0`; `norm` tam olarak `linf`, `l2` ya da `l1`. Tablodaki kapalı çözümü `{"delta":[...],"tahmini_artis":...}` olarak döndür. `sign(0)=0`. L2'de `‖g‖₂=0` ise δ sıfırdır. L1'de `|g|` en büyük olan **ilk** koordinat seçilir; o da sıfırsa δ sıfırdır. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-35")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def en_iyi_bozuntu(g,eps,norm):
    if norm=="linf":
        return {"delta":[eps*(1.0 if v>0 else -1.0) for v in g],"tahmini_artis":eps*math.sqrt(sum(v*v for v in g))}
    if norm=="l2":
        return {"delta":[eps*v for v in g],"tahmini_artis":eps*sum(abs(v) for v in g)}
    return {"delta":[eps*(1.0 if v>0 else -1.0) for v in g],"tahmini_artis":eps*max(g)}

from ai_guvence_veri import json_yukle
v=json_yukle("veri/taylor.json")
for norm in ("linf","l2","l1"):
    print(norm,en_iyi_bozuntu(v["gradyan"],v["eps"],norm))
```
```test
def sinama2(f):
    import copy,math,random
    def _y(a,b):return len(a)==len(b) and all(abs(p-q)<1e-12 for p,q in zip(a,b))
    try:
        g=[3.0,-4.0,0.0];old=list(g)
        r=f(g,0.5,"linf")
        if r!={"delta":[0.5,-0.5,0.0],"tahmini_artis":3.5} or g!=old:return False
        r=f(g,0.5,"l2")
        if not _y(r["delta"],[0.3,-0.4,0.0]) or abs(r["tahmini_artis"]-2.5)>1e-12 or set(r)!={"delta","tahmini_artis"}:return False
        if f(g,0.5,"l1")!={"delta":[0.0,-0.5,0.0],"tahmini_artis":2.0}:return False
        if f([2.0,-2.0],1.0,"l1")!={"delta":[1.0,0.0],"tahmini_artis":2.0}:return False
        if f([-2.0,2.0],1.0,"l1")!={"delta":[-1.0,0.0],"tahmini_artis":2.0}:return False
        if not _y(f([0.3,-0.4],0.5,"l2")["delta"],[0.3,-0.4]) or abs(f([0.3,-0.4],0.5,"l2")["tahmini_artis"]-0.25)>1e-12:return False
        if f([0.5,-0.25],1.0,"l1")!={"delta":[1.0,0.0],"tahmini_artis":0.5} or f([-0.5,0.25],1.0,"l1")!={"delta":[-1.0,0.0],"tahmini_artis":0.5}:return False
        for n in ("linf","l2","l1"):
            if f([0.0,0.0],1.0,n)!={"delta":[0.0,0.0],"tahmini_artis":0.0}:return False
        rng=random.Random(35)
        for _ in range(20):
            h=[rng.uniform(-3,3) for _ in range(6)];e=rng.uniform(.01,1)
            for n in ("linf","l2","l1"):
                q=f(list(h),e,n)
                if abs(sum(a*b for a,b in zip(h,q["delta"]))-q["tahmini_artis"])>1e-9:return False
                m={"linf":max(abs(v) for v in q["delta"]),"l2":math.sqrt(sum(v*v for v in q["delta"])),"l1":sum(abs(v) for v in q["delta"])}[n]
                if abs(m-e)>1e-9:return False
        for bad in ((None,.1,"l2"),([],.1,"l2"),((1.0,),.1,"l2"),([True],.1,"l2"),([float("nan")],.1,"l2"),([float("inf")],.1,"linf"),(["a"],.1,"l1"),([1.0],0,"l2"),([1.0],-.1,"l2"),([1.0],True,"l2"),([1.0],float("nan"),"l2"),([1.0],float("inf"),"l2"),([1.0],"x","l2"),([1.0],.1,"L2"),([1.0],.1,None)):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama2(en_iyi_bozuntu),"L∞/L2/L1 kapalı çözümü, sıfır gradient, eşitlik ve geçersiz girdi")
for ad,mut in [("kazanç yanlış norm",lambda g,e,n:dict(en_iyi_bozuntu(g,e,n),tahmini_artis=e*max(abs(v) for v in g))),("delta sıfır",lambda g,e,n:dict(en_iyi_bozuntu(g,e,n),delta=[0.0]*len(g))),("yön ters",lambda g,e,n:dict(en_iyi_bozuntu(g,e,n),delta=[-v for v in en_iyi_bozuntu(g,e,n)["delta"]]))]:
    ok(not sinama2(mut),"mutant reddedildi: "+ad)
```
```solution
import math
def en_iyi_bozuntu(g,eps,norm):
    if not isinstance(g,list) or not g or norm not in ("linf","l2","l1"):raise ValueError("girdi")
    for v in g+[eps]:
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError("sayı")
    if eps<=0:raise ValueError("eps")
    if norm=="linf":
        return {"delta":[eps*(1.0 if v>0 else -1.0 if v<0 else 0.0) for v in g],"tahmini_artis":eps*sum(abs(v) for v in g)}
    if norm=="l2":
        n=math.sqrt(sum(v*v for v in g))
        return {"delta":[eps*v/n for v in g] if n>0 else [0.0]*len(g),"tahmini_artis":eps*n}
    i=max(range(len(g)),key=lambda j:abs(g[j]))
    d=[0.0]*len(g)
    if g[i]!=0:d[i]=eps if g[i]>0 else -eps
    return {"delta":d,"tahmini_artis":eps*abs(g[i])}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    v=json_yukle("veri/taylor.json")
    for norm in ("linf","l2","l1"):
        print(norm,en_iyi_bozuntu(v["gradyan"],v["eps"],norm))
```
```hint
Tabloyu aynen uygula: L∞ için işaret ve ‖g‖₁, L2 için normalize ve ‖g‖₂, L1 için tek koordinat ve ‖g‖∞.
```
:::

::: anlat Tahmin nerede geçerli sayılır?
Birinci derece tahmini gerçek loss farkıyla karşılaştırırsın. Göreli hatanın paydası **gerçek** değerdir, çünkü soru "ölçülen olgu tahminden ne kadar uzak" sorusudur. Gerçek değer sıfıra yakınsa bölme patlamasın diye payda `1e-12` ile tabanlanır.

Rapor ε'ları küçükten büyüğe sıralar. `kopma_eps` hatanın `tol` değerini ilk aştığı ε'dur; `gecerli_eps` ondan önce geçen son ε'dur. Kopmadan sonra hata tesadüfen küçülürse bu rapor bunu "tekrar geçerli" saymaz. Yaklaşım büyük ε'da şans eseri tutabilir, ama bu güvenilir bir bölge değildir.

**Görev 3'te sık tuzaklar:** Tahmine bölmek, tahmin küçükken hatayı patlatır. Sıralamamak raporu girdi sırasına bağlar. Son kopmayı saklamak, tesadüfi uyuşmadan sonra kopma noktasını kaydırır.
:::

::: gorev 3 · Taylor tahmininin kopma noktası
`taylor_raporu(satirlar,tol)`: `tol` bool olmayan, sonlu, pozitif sayı. `satirlar` dolu liste; her satır tam olarak `eps`, `tahmin`, `gercek` alanlarını taşır; hepsi bool olmayan sonlu sayı; `eps>0` ve benzersiz. ε'a göre küçükten büyüğe işle: `goreli_hata=|tahmin-gercek|/max(|gercek|,1e-12)`. `{"satirlar":[{"eps","goreli_hata"}...],"gecerli_eps":...,"kopma_eps":...}` döndür. `kopma_eps`, `goreli_hata>tol` olan **ilk** ε, yoksa `None`. `gecerli_eps`, ilk kopmadan önceki son ε, yoksa `None`. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-35")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def taylor_raporu(satirlar,tol):
    out=[];kopma=None;gecerli=None
    for s in satirlar:
        e=abs(s["tahmin"]-s["gercek"])/abs(s["tahmin"])
        out.append({"eps":s["eps"],"goreli_hata":e})
        if e>tol:kopma=s["eps"]
        else:gecerli=s["eps"]
    return {"satirlar":out,"gecerli_eps":gecerli,"kopma_eps":kopma}

from ai_guvence_veri import json_yukle
v=json_yukle("veri/taylor.json")
print(taylor_raporu(v["taylor_satirlari"],v["tol_taylor"]))
```
```test
def sinama3(f):
    import copy
    try:
        s=[{"eps":.5,"tahmin":1.0,"gercek":2.0},{"eps":.25,"tahmin":1.0,"gercek":1.25},{"eps":.125,"tahmin":1.0,"gercek":1.0},{"eps":1.0,"tahmin":1.0,"gercek":1.0}];old=copy.deepcopy(s)
        r=f(s,.25)
        if s!=old:return False
        if r!={"satirlar":[{"eps":.125,"goreli_hata":0.0},{"eps":.25,"goreli_hata":.2},{"eps":.5,"goreli_hata":.5},{"eps":1.0,"goreli_hata":0.0}],"gecerli_eps":.25,"kopma_eps":.5}:return False
        if f(s,.125)["gecerli_eps"]!=.125 or f(s,.125)["kopma_eps"]!=.25:return False
        t=[{"eps":.5,"tahmin":1.5,"gercek":1.0}]
        if f(t,.5)!={"satirlar":[{"eps":.5,"goreli_hata":.5}],"gecerli_eps":.5,"kopma_eps":None}:return False
        if f(t,.25)!={"satirlar":[{"eps":.5,"goreli_hata":.5}],"gecerli_eps":None,"kopma_eps":.5}:return False
        if f([{"eps":1,"tahmin":-1.0,"gercek":-2.0}],1)["satirlar"][0]["goreli_hata"]!=.5:return False
        z=f([{"eps":1,"tahmin":1.0,"gercek":0.0}],1)["satirlar"][0]["goreli_hata"]
        if abs(z-1e12)>1:return False
        k=s[0]
        for sa,tol in ((s,0),(s,-1),(s,True),(s,float("nan")),(s,float("inf")),(s,"a"),(None,1),([],1),((k,),1),([None],1),([dict(k,ek=1)],1),([{"eps":1,"tahmin":1}],1),([dict(k,eps=0)],1),([dict(k,eps=-1)],1),([k,k],1),([dict(k,tahmin=True)],1),([dict(k,gercek=float("nan"))],1),([dict(k,eps=float("inf"))],1),([dict(k,tahmin="a")],1)):
            try:f(sa,tol);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama3(taylor_raporu),"sıralama, gerçeğe göre hata, ilk kopma ve geçersiz girdi")
for ad,mut in [("kopma hep yok",lambda s,t:dict(taylor_raporu(s,t),kopma_eps=None)),("satırlar ters",lambda s,t:dict(taylor_raporu(s,t),satirlar=taylor_raporu(s,t)["satirlar"][::-1])),("geçerli eps yok",lambda s,t:dict(taylor_raporu(s,t),gecerli_eps=None))]:
    ok(not sinama3(mut),"mutant reddedildi: "+ad)
```
```solution
import math
def taylor_raporu(satirlar,tol):
    if isinstance(tol,bool) or not isinstance(tol,(int,float)) or not math.isfinite(tol) or tol<=0:raise ValueError("tol")
    if not isinstance(satirlar,list) or not satirlar:raise ValueError("liste")
    gorulen=set()
    for s in satirlar:
        if not isinstance(s,dict) or set(s)!={"eps","tahmin","gercek"}:raise ValueError("şema")
        for k in s:
            if isinstance(s[k],bool) or not isinstance(s[k],(int,float)) or not math.isfinite(s[k]):raise ValueError("sayı")
        if s["eps"]<=0 or s["eps"] in gorulen:raise ValueError("eps")
        gorulen.add(s["eps"])
    out=[];kopma=None;gecerli=None
    for s in sorted(satirlar,key=lambda k:k["eps"]):
        e=abs(s["tahmin"]-s["gercek"])/max(abs(s["gercek"]),1e-12)
        out.append({"eps":s["eps"],"goreli_hata":e})
        if kopma is None:
            if e>tol:kopma=s["eps"]
            else:gecerli=s["eps"]
    return {"satirlar":out,"gecerli_eps":gecerli,"kopma_eps":kopma}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    v=json_yukle("veri/taylor.json")
    print(taylor_raporu(v["taylor_satirlari"],v["tol_taylor"]))
```
```hint
Önce sırala, sonra gerçek değere böl. Kopma bir kez bulununca gecerli_eps ve kopma_eps artık değişmemeli.
```
:::

::: anlat Hata vitrini · çalışmış yanlış rapor
Yazar, kusurlu başlangıç kodlarını görünür sentetik veriyle gerçekten çalıştırdı ve sonucu `outputs/yeni-ai-guvence-35/gorunur-run-1.json` dosyasına kaydetti. `veri/taylor.json` satırlarında doğru kod `gecerli_eps=0.02`, `kopma_eps=0.05` verir. Kusurlu kod `gecerli_eps=0.2`, `kopma_eps=0.1` verir: sıralamadığı için son gördüğü satırları yazar ve tesadüfen tutan bir satırı geçerli bölge sayar.

Bu kaydedilmiş bir hesaplama çıktısıdır, model yanıtı değildir. Bu raporu görüp "bu modelde doğrusal yaklaşım büyük ε'a kadar güvenilir" diyen biri neden yanılır? Hatanın paydasını ve satır sırasını ayrı ayrı kendi cümlenle açıkla. Gerçek finaldeki ölçüm ayrıca üretilir; bu sayılar onun yerine konmaz.
:::

::: anlat Gerçek deney: gerçek MLP'de tahmin ile olgu
Final, `load_digits` verisinde 64-48-10 GELU MLP'yi her koşuda sabit tohumla gerçekten eğitir ve test kümesinde doğru sınıflanan örneklerden her koşuda rastgele 48 tanesini seçer. GELU seçimi bilinçlidir: türevlenebilir bir aktivasyonla Hessian anlamlıdır; ReLU'da parçalı doğrusal yüzey ikinci dereceyi başka türlü davranır.

Sırasıyla: (1) `gradyan_denetle` ile autograd merkezi farkla denetlenir. (2) Her norm ve ε için `en_iyi_bozuntu` çağrılır, gerçek loss farkı ölçülür. (3) `taylor_raporu` kopma noktasını bulur. (4) Hessian-vector product ile `gᵀδ + ½δᵀHδ` hesaplanır. (5) 200 rastgele işaret yönünün hiçbirinin dual norm sınırını aşmadığı sınanır; ayrıca FGSM ile 32 rastgele yön gerçek loss üzerinde karşılaştırılır.

Sandbox aynı hesapları bağımsız referansla yapar; kabul senin çıktılarının referansla aynı olmasına, doğruluğun ve autograd denetiminin geçmesine, bütçenin aşılmamasına bağlıdır. **Saldırının başarılı olması kabul şartı değildir.**

**Kanıt dosyasını oku:** Çalıştır sonunda yol yazılır. `tablolar` alanında L∞ için birinci derece, ikinci derece ve gerçek sütunlarını karşılaştır. Soru 1: tahmin gerçeğin altında mı üstünde mi kalıyor, neden? Soru 2: ikinci derece kopmayı ne kadar geciktiriyor ve o da neden sonunda kopuyor? Soru 3: `fgsm_ort_artis` ile `rastgele32_en_iyi_ort_artis` farkı boyut hakkında ne söylüyor? Cevabını tezgâhta yorum olarak yaz; otomatik test bu serbest açıklamayı puanlamaz.
:::

::: gorev Gerçek deney · Gerçek MLP'de dual norm ve Taylor kopması
Önceki üç görevin `gradyan_denetle`, `en_iyi_bozuntu` ve `taylor_raporu` işlevlerini birleştir. Çalıştır gerçek tabloyu gösterir; Kontrol Et önce üç sözleşmeyi gizli verilerle sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
timeout: 180
```
```starter
import ai_lab
import math
def gradyan_denetle(f,x,analitik,h,tol):
    sayisal=[];hata=0.0
    for i in range(len(x)):
        a=list(x)
        a[i]+=h
        n=(f(a)-f(x))/h
        sayisal.append(n)
        hata=max(hata,abs(n-analitik[i]))
    return {"sayisal":sayisal,"maks_goreli_hata":hata,"gecti":hata<tol}
def en_iyi_bozuntu(g,eps,norm):
    if norm=="linf":
        return {"delta":[eps*(1.0 if v>0 else -1.0) for v in g],"tahmini_artis":eps*math.sqrt(sum(v*v for v in g))}
    if norm=="l2":
        return {"delta":[eps*v for v in g],"tahmini_artis":eps*sum(abs(v) for v in g)}
    return {"delta":[eps*(1.0 if v>0 else -1.0) for v in g],"tahmini_artis":eps*max(g)}
def taylor_raporu(satirlar,tol):
    out=[];kopma=None;gecerli=None
    for s in satirlar:
        e=abs(s["tahmin"]-s["gercek"])/abs(s["tahmin"])
        out.append({"eps":s["eps"],"goreli_hata":e})
        if e>tol:kopma=s["eps"]
        else:gecerli=s["eps"]
    return {"satirlar":out,"gecerli_eps":gecerli,"kopma_eps":kopma}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_35 as D
    D.goster(gradyan_denetle,en_iyi_bozuntu,taylor_raporu)
```
```test
import ai_lab,math
checks=[]
def kontrol(x,m):checks.append(bool(x));ok(x,m)
issues=ai_lab.kod_denetimi(src,('referans_denetle', 'referans_bozuntu', 'referans_taylor', 'kanit_yaz', '_yakin'),izin=())
kontrol(not issues,"kopya/yama/dinamik kod yok: "+str(issues))
if issues:stop()
gradyan_denetle=need("gradyan_denetle")
en_iyi_bozuntu=need("en_iyi_bozuntu")
taylor_raporu=need("taylor_raporu")
def sinama1(f):
    import copy,math
    def _r(k,x,a,h,tol):
        s=[];e=0.0
        for i in range(len(x)):
            p=list(x);q=list(x);p[i]+=h;q[i]-=h
            n=(k(p)-k(q))/(2*h);s.append(n);e=max(e,abs(n-a[i])/max(1.0,abs(n),abs(a[i])))
        return {"sayisal":s,"maks_goreli_hata":e,"gecti":e<=tol}
    try:
        kup=lambda v:v[0]**3+math.sin(v[1])*v[2]
        x=[2.0,0.5,-1.5];a=[12.0,-1.5*math.cos(0.5),math.sin(0.5)];old=(list(x),list(a))
        if f(kup,x,a,1e-3,1e-4)!=_r(kup,x,a,1e-3,1e-4) or (x,a)!=old:return False
        if not f(kup,x,a,1e-3,1e-4)["gecti"]:return False
        k=lambda v:0.0
        if f(k,[1.0],[0.5],0.5,0.5)!={"sayisal":[0.0],"maks_goreli_hata":0.5,"gecti":True}:return False
        if f(k,[1.0],[0.5],0.5,0.25)["gecti"] is not False:return False
        if f(k,[1.0],[4.0],0.5,0.25)["maks_goreli_hata"]!=1.0:return False
        d=lambda v:1000.0*v[0]
        if abs(f(d,[1.0],[1024.0],0.5,0.5)["maks_goreli_hata"]-24/1024)>1e-9:return False
        if abs(f(lambda v:-1000.0*v[0],[1.0],[-1024.0],0.5,0.5)["maks_goreli_hata"]-24/1024)>1e-9:return False
        if abs(f(lambda v:1024.0*v[0],[1.0],[1000.0],0.5,0.5)["maks_goreli_hata"]-24/1024)>1e-9:return False
        if abs(f(lambda v:v[0]+3*v[1],[1.0,1.0],[1.0,3.5],0.5,0.5)["maks_goreli_hata"]-0.5/3.5)>1e-9:return False
        if f(lambda v:v[0]+3*v[1],[1.0,1.0],[1.5,3.0],0.5,0.5)["maks_goreli_hata"]!=0.5/1.5:return False
        g=[1.0]
        for bad in ((k,None,g,.1,.1),(k,[],[],.1,.1),(k,g,[],.1,.1),(k,g,None,.1,.1),(k,(1.0,),g,.1,.1),(k,[True],g,.1,.1),(k,[float("nan")],g,.1,.1),(k,g,[float("inf")],.1,.1),(k,g,g,0,.1),(k,g,g,-.1,.1),(k,g,g,.1,0),(k,g,g,.1,-1),(k,g,g,True,.1),(k,g,g,.1,True),(k,g,g,float("nan"),.1),(k,g,g,.1,float("inf")),(k,g,g,"a",.1)):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
kontrol(sinama1(gradyan_denetle),"merkezi fark, göreli hata, dahil tol ve geçersiz girdi")
for ad,mut in [("ileri fark",lambda k,x,a,h,t:dict(gradyan_denetle(k,x,a,h,t),sayisal=[(k([v+h if j==i else v for j,v in enumerate(x)])-k(x))/h for i in range(len(x))])),("sonuç her zaman geçer",lambda k,x,a,h,t:dict(gradyan_denetle(k,x,a,h,t),gecti=True)),("hata hep sıfır",lambda k,x,a,h,t:dict(gradyan_denetle(k,x,a,h,t),maks_goreli_hata=0.0))]:
    kontrol(not sinama1(mut),"mutant reddedildi: "+ad)
def sinama2(f):
    import copy,math,random
    def _y(a,b):return len(a)==len(b) and all(abs(p-q)<1e-12 for p,q in zip(a,b))
    try:
        g=[3.0,-4.0,0.0];old=list(g)
        r=f(g,0.5,"linf")
        if r!={"delta":[0.5,-0.5,0.0],"tahmini_artis":3.5} or g!=old:return False
        r=f(g,0.5,"l2")
        if not _y(r["delta"],[0.3,-0.4,0.0]) or abs(r["tahmini_artis"]-2.5)>1e-12 or set(r)!={"delta","tahmini_artis"}:return False
        if f(g,0.5,"l1")!={"delta":[0.0,-0.5,0.0],"tahmini_artis":2.0}:return False
        if f([2.0,-2.0],1.0,"l1")!={"delta":[1.0,0.0],"tahmini_artis":2.0}:return False
        if f([-2.0,2.0],1.0,"l1")!={"delta":[-1.0,0.0],"tahmini_artis":2.0}:return False
        if not _y(f([0.3,-0.4],0.5,"l2")["delta"],[0.3,-0.4]) or abs(f([0.3,-0.4],0.5,"l2")["tahmini_artis"]-0.25)>1e-12:return False
        if f([0.5,-0.25],1.0,"l1")!={"delta":[1.0,0.0],"tahmini_artis":0.5} or f([-0.5,0.25],1.0,"l1")!={"delta":[-1.0,0.0],"tahmini_artis":0.5}:return False
        for n in ("linf","l2","l1"):
            if f([0.0,0.0],1.0,n)!={"delta":[0.0,0.0],"tahmini_artis":0.0}:return False
        rng=random.Random(35)
        for _ in range(20):
            h=[rng.uniform(-3,3) for _ in range(6)];e=rng.uniform(.01,1)
            for n in ("linf","l2","l1"):
                q=f(list(h),e,n)
                if abs(sum(a*b for a,b in zip(h,q["delta"]))-q["tahmini_artis"])>1e-9:return False
                m={"linf":max(abs(v) for v in q["delta"]),"l2":math.sqrt(sum(v*v for v in q["delta"])),"l1":sum(abs(v) for v in q["delta"])}[n]
                if abs(m-e)>1e-9:return False
        for bad in ((None,.1,"l2"),([],.1,"l2"),((1.0,),.1,"l2"),([True],.1,"l2"),([float("nan")],.1,"l2"),([float("inf")],.1,"linf"),(["a"],.1,"l1"),([1.0],0,"l2"),([1.0],-.1,"l2"),([1.0],True,"l2"),([1.0],float("nan"),"l2"),([1.0],float("inf"),"l2"),([1.0],"x","l2"),([1.0],.1,"L2"),([1.0],.1,None)):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
kontrol(sinama2(en_iyi_bozuntu),"L∞/L2/L1 kapalı çözümü, sıfır gradient, eşitlik ve geçersiz girdi")
for ad,mut in [("kazanç yanlış norm",lambda g,e,n:dict(en_iyi_bozuntu(g,e,n),tahmini_artis=e*max(abs(v) for v in g))),("delta sıfır",lambda g,e,n:dict(en_iyi_bozuntu(g,e,n),delta=[0.0]*len(g))),("yön ters",lambda g,e,n:dict(en_iyi_bozuntu(g,e,n),delta=[-v for v in en_iyi_bozuntu(g,e,n)["delta"]]))]:
    kontrol(not sinama2(mut),"mutant reddedildi: "+ad)
def sinama3(f):
    import copy
    try:
        s=[{"eps":.5,"tahmin":1.0,"gercek":2.0},{"eps":.25,"tahmin":1.0,"gercek":1.25},{"eps":.125,"tahmin":1.0,"gercek":1.0},{"eps":1.0,"tahmin":1.0,"gercek":1.0}];old=copy.deepcopy(s)
        r=f(s,.25)
        if s!=old:return False
        if r!={"satirlar":[{"eps":.125,"goreli_hata":0.0},{"eps":.25,"goreli_hata":.2},{"eps":.5,"goreli_hata":.5},{"eps":1.0,"goreli_hata":0.0}],"gecerli_eps":.25,"kopma_eps":.5}:return False
        if f(s,.125)["gecerli_eps"]!=.125 or f(s,.125)["kopma_eps"]!=.25:return False
        t=[{"eps":.5,"tahmin":1.5,"gercek":1.0}]
        if f(t,.5)!={"satirlar":[{"eps":.5,"goreli_hata":.5}],"gecerli_eps":.5,"kopma_eps":None}:return False
        if f(t,.25)!={"satirlar":[{"eps":.5,"goreli_hata":.5}],"gecerli_eps":None,"kopma_eps":.5}:return False
        if f([{"eps":1,"tahmin":-1.0,"gercek":-2.0}],1)["satirlar"][0]["goreli_hata"]!=.5:return False
        z=f([{"eps":1,"tahmin":1.0,"gercek":0.0}],1)["satirlar"][0]["goreli_hata"]
        if abs(z-1e12)>1:return False
        k=s[0]
        for sa,tol in ((s,0),(s,-1),(s,True),(s,float("nan")),(s,float("inf")),(s,"a"),(None,1),([],1),((k,),1),([None],1),([dict(k,ek=1)],1),([{"eps":1,"tahmin":1}],1),([dict(k,eps=0)],1),([dict(k,eps=-1)],1),([k,k],1),([dict(k,tahmin=True)],1),([dict(k,gercek=float("nan"))],1),([dict(k,eps=float("inf"))],1),([dict(k,tahmin="a")],1)):
            try:f(sa,tol);return False
            except ValueError:pass
        return True
    except Exception:return False
kontrol(sinama3(taylor_raporu),"sıralama, gerçeğe göre hata, ilk kopma ve geçersiz girdi")
for ad,mut in [("kopma hep yok",lambda s,t:dict(taylor_raporu(s,t),kopma_eps=None)),("satırlar ters",lambda s,t:dict(taylor_raporu(s,t),satirlar=taylor_raporu(s,t)["satirlar"][::-1])),("geçerli eps yok",lambda s,t:dict(taylor_raporu(s,t),gecerli_eps=None))]:
    kontrol(not sinama3(mut),"mutant reddedildi: "+ad)
if not all(checks):stop()
from sandbox import ai_gercek_ai_guvence_35 as D
try:r=D.deney(gradyan_denetle,en_iyi_bozuntu,taylor_raporu)
except ai_lab.GercekLabYok as e:
    kontrol(False,"gerçek deney yok: "+str(e));stop()
kontrol(r["dogruluk"]>=0.9,"gerçek model anlamlı doğrulukta eğitildi")
kontrol(r["gradcheck_maks"]<1e-6 and all(k["gecti"] for k in r["gradcheck"]),"autograd merkezi farkla uyuştu")
kontrol(r["denetim_ayni"],"gerçek gradyan denetimi bağımsız hesapla aynı")
kontrol(r["bozuntu_ayni"],"gerçek gradient'lerde bozuntu bağımsız hesapla aynı")
kontrol(r["taylor_ayni"],"Taylor raporu bağımsız hesapla aynı")
kontrol(r["norm_ihlali"]==0,"hiçbir δ bütçeyi aşmadı")
kontrol(r["dual_ihlali"]==0,"rastgele yönler dual norm sınırını aşmadı")
kontrol(len(r["secim"])==48 and len(set(r["secim"]))==48,"48 ayrı gerçek örnek ölçüldü")
ai_lab.kanit_yaz("ai-guvence-35-kabul",{"kaynak":"gercek","kabul":all(checks),"ders":"ai-guvence-35","deney":r})
```
```solution
import ai_lab
import math
def gradyan_denetle(f,x,analitik,h,tol):
    if not isinstance(x,list) or not x or not isinstance(analitik,list) or len(analitik)!=len(x):raise ValueError("boyut")
    for v in x+analitik+[h,tol]:
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError("sayı")
    if h<=0 or tol<=0:raise ValueError("ayar")
    sayisal=[];hata=0.0
    for i in range(len(x)):
        a=list(x);b=list(x)
        a[i]+=h;b[i]-=h
        n=(f(a)-f(b))/(2*h)
        sayisal.append(n)
        hata=max(hata,abs(n-analitik[i])/max(1.0,abs(n),abs(analitik[i])))
    return {"sayisal":sayisal,"maks_goreli_hata":hata,"gecti":hata<=tol}
def en_iyi_bozuntu(g,eps,norm):
    if not isinstance(g,list) or not g or norm not in ("linf","l2","l1"):raise ValueError("girdi")
    for v in g+[eps]:
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError("sayı")
    if eps<=0:raise ValueError("eps")
    if norm=="linf":
        return {"delta":[eps*(1.0 if v>0 else -1.0 if v<0 else 0.0) for v in g],"tahmini_artis":eps*sum(abs(v) for v in g)}
    if norm=="l2":
        n=math.sqrt(sum(v*v for v in g))
        return {"delta":[eps*v/n for v in g] if n>0 else [0.0]*len(g),"tahmini_artis":eps*n}
    i=max(range(len(g)),key=lambda j:abs(g[j]))
    d=[0.0]*len(g)
    if g[i]!=0:d[i]=eps if g[i]>0 else -eps
    return {"delta":d,"tahmini_artis":eps*abs(g[i])}
def taylor_raporu(satirlar,tol):
    if isinstance(tol,bool) or not isinstance(tol,(int,float)) or not math.isfinite(tol) or tol<=0:raise ValueError("tol")
    if not isinstance(satirlar,list) or not satirlar:raise ValueError("liste")
    gorulen=set()
    for s in satirlar:
        if not isinstance(s,dict) or set(s)!={"eps","tahmin","gercek"}:raise ValueError("şema")
        for k in s:
            if isinstance(s[k],bool) or not isinstance(s[k],(int,float)) or not math.isfinite(s[k]):raise ValueError("sayı")
        if s["eps"]<=0 or s["eps"] in gorulen:raise ValueError("eps")
        gorulen.add(s["eps"])
    out=[];kopma=None;gecerli=None
    for s in sorted(satirlar,key=lambda k:k["eps"]):
        e=abs(s["tahmin"]-s["gercek"])/max(abs(s["gercek"]),1e-12)
        out.append({"eps":s["eps"],"goreli_hata":e})
        if kopma is None:
            if e>tol:kopma=s["eps"]
            else:gecerli=s["eps"]
    return {"satirlar":out,"gecerli_eps":gecerli,"kopma_eps":kopma}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_35 as D
    D.goster(gradyan_denetle,en_iyi_bozuntu,taylor_raporu)
```
```hint
Üç işlevi aynen birleştir. Tabloyu okurken tahmin ve gerçek sütununu değil, hatanın ε ile büyüme biçimini takip et.
```
:::

::: anlat Sınır
Bu ders tek küçük GELU MLP'de, `[0,1]` kutusu uygulanmadan, 48 örneğin ortalamasında Taylor yaklaşımının nerede koptuğunu gösterir; başka mimari, veri ya da büyük modeller için bir kopma noktası veya genel saldırı başarı oranı göstermez.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **FGSM rastgele bir formül değildir (30 sn).** "$L(x+\delta) \approx L(x) + g^\top \delta$ birinci derece Taylor doğrusallaştırmasını sabit norm bütçesi altında maksimize ettiğimizde, dual norm tanımı doğrudan $L_\infty$ için $\varepsilon\,\mathrm{sign}(g)$, $L_2$ için $\varepsilon\,g/\|g\|_2$ ve $L_1$ için en büyük $|g_i|$ bileşenini verir."
2. **Sayısal türevle analitik gradyan denetimi (30 sn).** "Saldırı kodundaki tek bir işaret veya ölçek hatası sahte 'model sağlam' sonucu üretir; merkezi fark $\frac{f(x+he_i)-f(x-he_i)}{2h}$ ile analitik gradyanı doğrulamadan saldırı ölçümüne güvenilmez."
3. **Doğrusal yaklaşımın kopma sınırı (35 sn).** "Küçük $\varepsilon$'da gerçek kayıp artışı $g^\top \delta = \varepsilon \|g\|_*$ tahminini izlerken, bütçe büyüdükçe eğrilik terimi baskınlaşır ve tek adımlı FGSM yerini çok adımlı PGD'ye bırakır."
4. **Soru (25 sn).** "$\varepsilon$ büyüdüğünde tek adımlı FGSM'nin kayıp artışı neden Taylor tahmininin altına düşebilir ve çok adımlı küçük adımlar bunu nasıl aşar?"
:::
