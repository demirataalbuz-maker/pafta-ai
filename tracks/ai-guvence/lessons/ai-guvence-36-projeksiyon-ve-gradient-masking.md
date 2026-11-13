---
id: ai-guvence-36
title: Projeksiyon ve Gradient Masking · Sahte Sağlamlığı Ölçmek
summary: L∞ ve L2 projeksiyonunu yaz, kararlı cross-entropy ve margin loss hesapla; aynı kararları veren logit ölçekli modelde float32 doygunluğunun ürettiği sahte sağlamlığı GPU'da ölç ve tanı raporuyla işaretle.
esleme: ai-guvence-08, ai-guvence-35, ai-savunma-33
timeout: 60
---

::: anlat PGD bir şey bulamadıysa ne öğrendik?
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Aynı kararları veren iki modelden biri, yalnız float32 doygunluğu yüzünden gradient saldırısına "sağlam" görünebilir | İlk üç görev: `veri/masking.json` içindeki **sentetik** logit ve raporlar. Final: `load_digits` üzerinde gerçekten eğitilen MLP, GPU'da float32 autograd, aynı ağırlıkların logitleri 1000 ile çarpılmış kopyası | Gerçek bir savunmanın maskeli olduğunu bu tek düzenekten çıkaramaz; bu ölçekleme yapay bir örnektir |
| Başka bir loss aynı modeli kırabilir | Cross-entropy ve margin loss ile PGD, tek adım FGSM, rastgele gürültü | Margin loss ile kırılmayan bir modelin sağlam olduğunu kanıtlamaz; PGD yalnız bir alt sınır verir |

> [!NOT]
> Görevler `veri/masking.json` dosyasını okur; dosya sentetiktir. Setup her Çalıştır/Kontrol Et adımında geçici kopya kurar; değişiklikler taşınmaz, **kalıcılık yoktur**. Ekranda ayrı dosya görüntüleyici yoktur; içeriği görmek için `print` kullan. Gizli testler ayrıdır. Final yeni model indirmez ve GPU varsa onu kullanır. Bu olgu float32'ye bağlıdır; doygunluk eşiği dtype ile değişir.

ai-guvence-08 PGD'yi uygular ve eğrisini çıkarır. Bu ders şu soruyu sorar: **PGD bir şey bulamadıysa bu ne anlama gelir?**

**PGD bir optimizasyon yöntemidir.** Yukarı adım atar, sonra kısıt kümesine geri döner: `x ← Π(x + α·yön)`. `Π` öklidyen projeksiyondur, yani küme içindeki en yakın noktayı döndürür. L∞ topunda koordinat koordinat kırpma tam olarak bunu yapar. L2 topunda ise farkı bütün olarak küçültmek gerekir; koordinat koordinat kırpmak yönü bozar. Küme bir top ile `[0,1]` kutusunun kesişimi olunca işler değişir: L∞ için iki kırpmanın ardışık uygulanması tam projeksiyondur. L2 için kırpma sonrası nokta artık en yakın nokta olmayabilir; yine de bütçe içinde kalır. Pratikte yaygın kullanılan ve bu derste de yapılan budur; farkı bilmek gerekir.

**PGD bir alt sınır verir.** Bulduğu her örnek sağlamlığın kırıldığını kanıtlar. Hiçbir şey bulamaması kanıt değildir: optimizasyon başarısız olmuş olabilir. Bu boşluk gradient masking denen yanılsamayı doğurur (Athalye vd. 2018): saldırının aldığı sinyal bozulmuştur, ama karar sınırı yerindedir.

**En basit mekanizma doygunluktur.** CE'nin logitlere göre gradient'i `p - e_y`'dir. Yani gradient'in büyüklüğü `1 - p_y` ile orantılıdır. Logitleri büyük bir sabitle çarparsan kararlar **hiç değişmez**, çünkü sıralama aynı kalır. Ama `p_y` float32'de tam 1 olur, gradient tam sıfır olur ve `sign(0)=0` yüzünden saldırı yerinden kımıldamaz. Rapor "%100 robust" der. Model aynı modeldir.

**Çare mekanizmayı anlamaktan gelir.** Margin loss `max_{j≠y} z_j - z_y` (Carlini ve Wagner 2017) softmax'tan geçmez, doygunluk yaşamaz. Kırılan şey model değil, kullanılan loss'un sayısal davranışıydı. AutoAttack da (Croce ve Hein 2020) bu yüzden birkaç farklı loss ve yöntemi birlikte kullanır.

**Sayısal taraf aynı dersin parçasıdır.** Logit `1000` ise `exp(1000)` taşar. Kararlı hesap, en büyük logiti çıkarmaktır: `log Σ exp(z_j - m) - (z_y - m)`. Ayrıca `1 - p_y` çok küçükse çıkarma sonucu 0'a yuvarlanır; doğrusu diğer sınıfların olasılıklarını toplamaktır.

**Saldırgan ne dener?** Bir "sağlam" iddiası gördüğünde önce başka bir loss, sonra sayısal olarak kararlı bir gradient dener. Sadece ölçeği düzeltmek çoğu yanılsamayı kırar.

**Savunma neden kırılır?** Değerlendirme tek saldırı ve tek loss ile yapıldıysa, ölçülen şey sağlamlık değil o saldırının başarısızlığıdır. Tek adımlı FGSM'in çok adımlı PGD'den güçlü çıkması, rastgele gürültünün gradient saldırısından güçlü çıkması veya gradient'lerin çoğunun sıfır olması, Athalye vd. 2018'in saydığı uyarı işaretleridir. Görev 3 bunları makine tarafından okunabilir hâle getirir.

**Görev 1'de sık tuzaklar:** L∞'da top kısıtını unutup yalnız kutuya kırpmak bütçeyi aşar. L2'de koordinat koordinat kırpmak en yakın noktayı vermez.

Kaynaklar: [Madry vd. 2018](https://arxiv.org/abs/1706.06083), [Carlini ve Wagner 2017](https://arxiv.org/abs/1608.04644), [Athalye vd. 2018](https://arxiv.org/abs/1802.00420), [Croce ve Hein 2020](https://arxiv.org/abs/2003.01690). Bu dersteki bütün sayılar yalnız yerel kanıttan gelir.

Köprü: ai-guvence-35 doygunluğun Taylor tahminini nasıl yanılttığını ölçer; ai-guvence-08 PGD eğrisini çıkarır.
:::

::: tahmin Büyük logit ne yapar?
Çıktıyı tahmin et, sonra Çalıştır ile karşılaştır.
```python
import math
z = [1000.0, 0.0]
try:
    print(math.exp(z[0]))
except OverflowError:
    print("taşma")
print(math.exp(z[1] - z[0]))
print(z[1] - z[0])
```
???
```cikti
taşma
0.0
-1000.0
```
Tahmininle gerçek çıktı arasındaki farkı tezgâhta yorum satırı olarak yaz: ikinci satırdaki 0.0, CE gradient'i için ne demektir? Üçüncü satır o bilgiyi neden hâlâ taşıyor? Sonra üç kusurlu başlangıç kodunu çalıştır ve her birinin neyi kaçırdığını önce kendin teşhis et; açıklama çözümün ardından gelir.
:::

::: gorev 1 · L∞ ve L2 projeksiyonu
`projeksiyon(x,x0,eps,norm,alt,ust)`: `x`, `x0` aynı uzunlukta dolu liste; `x`, `x0`, `eps`, `alt`, `ust` değerleri bool olmayan sonlu sayı; `eps>0`, `alt<ust`; `norm` `linf` ya da `l2`. L∞: her koordinatı `[x0-eps, x0+eps]` aralığına kırp. L2: fark `d=x-x0`; `‖d‖₂>eps` ise `d`'yi `eps/‖d‖₂` ile çarp, değilse değiştirme. Sonra her iki durumda her koordinatı `[alt,ust]` kutusuna kırp ve yeni liste döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-36")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def projeksiyon(x,x0,eps,norm,alt,ust):
    if norm=="linf":
        return [min(max(a,alt),ust) for a in x]
    return [b+min(max(a-b,-eps),eps) for a,b in zip(x,x0)]

from ai_guvence_veri import json_yukle
v=json_yukle("veri/masking.json")
p=v["projeksiyon"]
print("L∞:",projeksiyon(p["x"],p["x0"],p["eps"],"linf",p["alt"],p["ust"]))
print("L2:",projeksiyon(p["x"],p["x0"],p["eps"],"l2",p["alt"],p["ust"]))
```
```test
def sinama1(f):
    import copy,math,random
    def _r(x,o,e,n,a,u):
        if n=="linf":y=[min(max(p,q-e),q+e) for p,q in zip(x,o)]
        else:
            d=[p-q for p,q in zip(x,o)];m=math.sqrt(sum(v*v for v in d));k=e/m if m>e else 1.0
            y=[q+k*v for q,v in zip(o,d)]
        return [min(max(v,a),u) for v in y]
    def _y(a,b):return len(a)==len(b) and all(abs(p-q)<1e-12 for p,q in zip(a,b))
    try:
        x=[.875,.125,.5];o=[.5,.5,.5];old=(list(x),list(o))
        if f(x,o,.25,"linf",0,1)!=[.75,.25,.5] or (x,o)!=old:return False
        if f([2.0],[.75],.5,"linf",0,1)!=[1.0] or f([-2.0],[.25],.5,"linf",0,1)!=[0.0]:return False
        if not _y(f([3.0,4.0],[0.0,0.0],2.5,"l2",-9,9),[1.5,2.0]) or f([3.0,4.0],[0.0,0.0],5.0,"l2",-9,9)!=[3.0,4.0]:return False
        if f([3.0,4.0],[0.0,0.0],7.0,"l2",-9,9)!=[3.0,4.0]:return False
        if f([3.0,4.0],[0.0,0.0],5.0,"l2",0,1)!=[1,1] or f([-3.0,-4.0],[0.0,0.0],5.0,"l2",-1,0)!=[-1,-1]:return False
        if not _y(f([4.0,5.0],[1.0,1.0],2.5,"l2",-9,9),[2.5,3.0]):return False
        rng=random.Random(36)
        for _ in range(25):
            n=rng.randint(1,6);p=[rng.uniform(-2,3) for _ in range(n)];q=[rng.uniform(0,1) for _ in range(n)];e=rng.uniform(.01,1)
            for m in ("linf","l2"):
                if not _y(f(list(p),list(q),e,m,0,1),_r(p,q,e,m,0,1)):return False
        g=[.5]
        for bad in ((None,g,.1,"l2",0,1),(g,None,.1,"l2",0,1),([],[],.1,"l2",0,1),(g,[.5,.5],.1,"l2",0,1),((.5,),g,.1,"l2",0,1),(g,(.5,),.1,"l2",0,1),(g,g,.1,"l1",0,1),(g,g,0,"l2",0,1),(g,g,-.1,"l2",0,1),(g,g,True,"l2",0,1),(g,g,float("nan"),"l2",0,1),([True],g,.1,"l2",0,1),(g,[float("inf")],.1,"l2",0,1),(["a"],g,.1,"l2",0,1),(g,g,.1,"l2",1,1),(g,g,.1,"l2",2,1),(g,g,.1,"l2",float("nan"),1),(g,g,.1,"l2",0,float("inf"))):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama1(projeksiyon),"top kısıtı, L2 ölçekleme, kutu, sınır ve geçersiz girdi")
for ad,mut in [("kutu yok",lambda x,o,e,n,a,u:[p+0.0 for p in x]),("x0 döndür",lambda x,o,e,n,a,u:list(o)),("L2 yerine L∞",lambda x,o,e,n,a,u:projeksiyon(x,o,e,"linf",a,u))]:
    ok(not sinama1(mut),"mutant reddedildi: "+ad)
```
```solution
import math
def projeksiyon(x,x0,eps,norm,alt,ust):
    if not isinstance(x,list) or not isinstance(x0,list) or not x or len(x)!=len(x0) or norm not in ("linf","l2"):raise ValueError("girdi")
    for v in x+x0+[eps,alt,ust]:
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError("sayı")
    if eps<=0 or alt>=ust:raise ValueError("ayar")
    if norm=="linf":
        y=[min(max(a,b-eps),b+eps) for a,b in zip(x,x0)]
    else:
        d=[a-b for a,b in zip(x,x0)]
        n=math.sqrt(sum(v*v for v in d))
        k=eps/n if n>eps else 1.0
        y=[b+k*v for b,v in zip(x0,d)]
    return [min(max(v,alt),ust) for v in y]

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    v=json_yukle("veri/masking.json")
    p=v["projeksiyon"]
    print("L∞:",projeksiyon(p["x"],p["x0"],p["eps"],"linf",p["alt"],p["ust"]))
    print("L2:",projeksiyon(p["x"],p["x0"],p["eps"],"l2",p["alt"],p["ust"]))
```
```hint
L∞ koordinat koordinat, L2 tek bir ölçek çarpanıyla çalışır. Kutu kırpması en sonda ve iki normda da uygulanır.
```
:::

::: anlat Aynı karar, farklı loss sinyali
Margin'in işareti önemlidir: bu derste "yüksek = saldırgan için iyi" yönünü kullanıyoruz. `marjin = max_{j≠y} z_j - z_y`. Pozitifse örnek zaten yanlış sınıflanmıştır, negatifse doğrudur. Saldırgan bu değeri artırır.

`doygunluk`, CE gradient'inin büyüklüğünü belirleyen `1-p_y` değeridir. Bunu `1-p_y` diye yazarsan küçük değerler 0'a yuvarlanır; yanılsamayı raporlayacak değer yok olur. Doğrusu diğer olasılıkları toplamaktır. Yine de değer aşırı küçükse (ör. `e^-1000`) double'da bile gerçekten 0'a iner; önemli olan kaybedilen hassasiyeti yanlış hesapla artırmamaktır.

**Görev 2'de sık tuzaklar:** Doğrudan `exp` kullanmak büyük logitte taşar. `max(logit)`'i etiketi hariç tutmadan almak, doğru sınıflanmış örnekte margin'i hep 0 gösterir.
:::

::: gorev 2 · Kararlı CE, margin ve doygunluk
`kayip_raporu(logit,etiket)`: `logit` en az iki elemanlı liste, bool olmayan sonlu sayılar; `etiket` bool olmayan int ve geçerli indis. `m=max(logit)`, `p_j=exp(z_j-m)`, `t=Σp_j`. `{"ce":log(t)-(z_y-m),"marjin":max_{j≠y} z_j - z_y,"doygunluk":Σ_{j≠y} p_j/t}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-36")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def kayip_raporu(logit,etiket):
    p=[math.exp(v) for v in logit]
    t=sum(p)
    q=p[etiket]/t
    return {"ce":-math.log(q),"marjin":logit[etiket]-max(logit),"doygunluk":1-q}

from ai_guvence_veri import json_yukle
v=json_yukle("veri/masking.json")
for o in v["logitler"]:
    print(o["ad"],kayip_raporu(o["logit"],o["etiket"]))
```
```test
def sinama2(f):
    import copy,math,random
    def _r(z,y):
        m=max(z);p=[math.exp(v-m) for v in z];t=sum(p)
        return {"ce":math.log(t)-(z[y]-m),"marjin":max(v for j,v in enumerate(z) if j!=y)-z[y],"doygunluk":sum(v/t for j,v in enumerate(p) if j!=y)}
    try:
        z=[1000.0,0.0,-1000.0];old=list(z)
        if f(z,0)!={"ce":0.0,"marjin":-1000.0,"doygunluk":0.0} or z!=old:return False
        q=f(z,1)
        if q["ce"]!=1000.0 or q["marjin"]!=1000.0 or q["doygunluk"]!=1.0:return False
        if f([40.0,0.0],0)["doygunluk"]<=0 or abs(f([40.0,0.0],0)["doygunluk"]-math.exp(-40))>1e-25:return False
        if f([-5000.0,-5001.0],0)["marjin"]!=-1.0:return False
        if abs(f([1.0,1.0],0)["ce"]-math.log(2))>1e-12 or f([1.0,1.0],0)["marjin"]!=0.0 or f([1,1],1)["doygunluk"]!=.5:return False
        if f([3.0,5.0,1.0],0)["marjin"]!=2.0 or f([5.0,3.0,4.0],0)["marjin"]!=-1.0:return False
        rng=random.Random(3636)
        for _ in range(25):
            w=[rng.uniform(-30,30) for _ in range(rng.randint(2,7))];y=rng.randrange(len(w))
            if f(list(w),y)!=_r(w,y):return False
        for bad in ((None,0),([],0),([1.0],0),((1.0,2.0),0),([True,1.0],0),([float("nan"),1.0],0),([float("inf"),1.0],0),(["a",1.0],0),([1.0,2.0],2),([1.0,2.0],-1),([1.0,2.0],True),([1.0,2.0],1.0),([1.0,2.0],None)):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama2(kayip_raporu),"büyük logit, kararlı doygunluk, margin yönü ve geçersiz girdi")
for ad,mut in [("margin ters",lambda z,y:dict(kayip_raporu(z,y),marjin=-kayip_raporu(z,y)["marjin"])),("doygunluk sıfır",lambda z,y:dict(kayip_raporu(z,y),doygunluk=0.0)),("CE işaret ters",lambda z,y:dict(kayip_raporu(z,y),ce=-kayip_raporu(z,y)["ce"]-1))]:
    ok(not sinama2(mut),"mutant reddedildi: "+ad)
```
```solution
import math
def kayip_raporu(logit,etiket):
    if not isinstance(logit,list) or len(logit)<2:raise ValueError("logit")
    for v in logit:
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError("sayı")
    if isinstance(etiket,bool) or not isinstance(etiket,int) or not 0<=etiket<len(logit):raise ValueError("etiket")
    m=max(logit)
    p=[math.exp(v-m) for v in logit]
    t=sum(p)
    return {"ce":math.log(t)-(logit[etiket]-m),"marjin":max(v for j,v in enumerate(logit) if j!=etiket)-logit[etiket],"doygunluk":sum(v/t for j,v in enumerate(p) if j!=etiket)}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    v=json_yukle("veri/masking.json")
    for o in v["logitler"]:
        print(o["ad"],kayip_raporu(o["logit"],o["etiket"]))
```
```hint
En büyük logiti çıkarıp üstel al. Margin ve doygunluk için etiketi hariç tutan toplama ve maksimum kullan.
```
:::

::: anlat Bir sağlamlık sayısı nasıl sorgulanır?
Tanı raporu bir kanıt değil, **şüphe listesidir**. Beş bayrak kullanılır:

- `etkisiz`: `temiz - pgd_ce <= tol`. Saldırı doğruluğu neredeyse hiç düşürmemiş.
- `kayip_farki`: `pgd_marjin + tol < pgd_ce`. Başka bir loss daha güçlü.
- `rastgele`: `rastgele + tol < pgd_ce`. Rastgele gürültü gradient saldırısını geçmiş.
- `sifir_grad`: `sifir_grad > sinir`. Örneklerin çoğunda gradient tam sıfır.
- `tek_adim`: `fgsm + tol < pgd_ce`. Tek adım çok adımı geçmiş.

Raporlanacak sağlamlık değeri tek bir saldırının değil, **bütün saldırıların en düşüğüdür**. Sağlamlık alt sınırı en güçlü saldırıyla belirlenir; `temiz` bu minimuma girmez. Bayrak listesi alfabetik sıradadır.

**Görev 3'te sık tuzaklar:** Yalnız `pgd_ce` raporlamak yanılsamayı olduğu gibi aktarır. `tol` karşılaştırmaları katıdır, yalnız `etkisiz` dahil sınır kullanır; küçük bir örneklem gürültüsü bayrak üretmesin diye vardır.
:::

::: gorev 3 · Maskeleme tanı raporu
`maskeleme_tanisi(r,tol,sinir)`: `r` tam olarak `temiz`, `fgsm`, `pgd_ce`, `pgd_marjin`, `rastgele`, `sifir_grad` alanlarını taşır; hepsi bool olmayan sonlu sayı ve `[0,1]` içinde. `tol>=0`, `0<=sinir<=1`, ikisi de bool olmayan sonlu sayı. Yukarıdaki beş bayrağı alfabetik listele. `{"bayraklar":[...],"maskeli":liste doluysa True,"en_dusuk_robust":min(fgsm,pgd_ce,pgd_marjin,rastgele)}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-36")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def maskeleme_tanisi(r,tol,sinir):
    b=[]
    if r["fgsm"]<r["pgd_ce"]:b.append("tek_adim")
    return {"bayraklar":b,"maskeli":bool(b),"en_dusuk_robust":r["pgd_ce"]}

from ai_guvence_veri import json_yukle
v=json_yukle("veri/masking.json")
for ad,r in v["raporlar"].items():
    print(ad,maskeleme_tanisi(r,v["tol"],v["sinir"]))
```
```test
def sinama3(f):
    import copy
    try:
        t={"temiz":1.0,"fgsm":.5,"pgd_ce":.25,"pgd_marjin":.25,"rastgele":.875,"sifir_grad":0.0};old=dict(t)
        if f(t,.0,.5)!={"bayraklar":[],"maskeli":False,"en_dusuk_robust":.25} or t!=old:return False
        m={"temiz":1.0,"fgsm":.5,"pgd_ce":1.0,"pgd_marjin":.25,"rastgele":.875,"sifir_grad":1.0}
        if f(m,.0,.5)!={"bayraklar":["etkisiz","kayip_farki","rastgele","sifir_grad","tek_adim"],"maskeli":True,"en_dusuk_robust":.25}:return False
        if f(dict(t,temiz=.5),.25,.5)["bayraklar"]!=["etkisiz"]:return False
        if f(dict(t,temiz=.5),.125,.5)["bayraklar"]!=[]:return False
        b={"temiz":1.0,"fgsm":.75,"pgd_ce":.5,"pgd_marjin":.25,"rastgele":.75,"sifir_grad":0.0}
        if f(b,.25,.5)["bayraklar"]!=[] or f(b,.125,.5)["bayraklar"]!=["kayip_farki"]:return False
        if f(b,.25,.5)["maskeli"] is not False or f(b,.125,.5)["maskeli"] is not True:return False
        c=dict(b,rastgele=.25,pgd_marjin=.5)
        if f(c,.25,.5)["bayraklar"]!=[] or f(c,.125,.5)["bayraklar"]!=["rastgele"]:return False
        d=dict(b,fgsm=.25,pgd_marjin=.5)
        if f(d,.25,.5)["bayraklar"]!=[] or f(d,.125,.5)["bayraklar"]!=["tek_adim"]:return False
        e=dict(b,pgd_marjin=.5,sifir_grad=.5)
        if f(e,.0,.5)["bayraklar"]!=[] or f(e,.0,.25)["bayraklar"]!=["sifir_grad"]:return False
        if f(dict(e,sifir_grad=0.0),.0,0)["bayraklar"]!=[] or f(dict(e,sifir_grad=.125),.0,0)["bayraklar"]!=["sifir_grad"]:return False
        for a,v in (("fgsm",.125),("pgd_ce",.125),("pgd_marjin",.125),("rastgele",.125)):
            q=dict(t,fgsm=.75,pgd_ce=.5,pgd_marjin=.625,rastgele=.875);q[a]=v
            if f(q,1,1)["en_dusuk_robust"]!=.125:return False
        for r,tl,s in ((None,.1,.5),(dict(t,ek=1),.1,.5),({k:v for k,v in t.items() if k!="fgsm"},.1,.5),(dict(t,fgsm=1.5),.1,.5),(dict(t,fgsm=-.1),.1,.5),(dict(t,fgsm=True),.1,.5),(dict(t,temiz=float("nan")),.1,.5),(dict(t,fgsm="a"),.1,.5),(t,-.1,.5),(t,True,.5),(t,float("nan"),.5),(t,.1,-.1),(t,.1,1.5),(t,.1,True),(t,.1,float("nan")),(t,"a",.5)):
            try:f(r,tl,s);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama3(maskeleme_tanisi),"beş bayrak, sınırlar, en düşük robust ve geçersiz girdi")
for ad,mut in [("hep temiz",lambda r,t,s:dict(maskeleme_tanisi(r,t,s),bayraklar=[],maskeli=False)),("yalnız PGD robust",lambda r,t,s:dict(maskeleme_tanisi(r,t,s),en_dusuk_robust=r["pgd_ce"])),("maskeli hep doğru",lambda r,t,s:dict(maskeleme_tanisi(r,t,s),maskeli=True))]:
    ok(not sinama3(mut),"mutant reddedildi: "+ad)
```
```solution
import math
def maskeleme_tanisi(r,tol,sinir):
    alan={"temiz","fgsm","pgd_ce","pgd_marjin","rastgele","sifir_grad"}
    if not isinstance(r,dict) or set(r)!=alan:raise ValueError("şema")
    for k in alan:
        if isinstance(r[k],bool) or not isinstance(r[k],(int,float)) or not math.isfinite(r[k]) or not 0<=r[k]<=1:raise ValueError("oran")
    for v in (tol,sinir):
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError("ayar")
    if tol<0 or not 0<=sinir<=1:raise ValueError("ayar")
    b=[]
    if r["temiz"]-r["pgd_ce"]<=tol:b.append("etkisiz")
    if r["pgd_marjin"]+tol<r["pgd_ce"]:b.append("kayip_farki")
    if r["rastgele"]+tol<r["pgd_ce"]:b.append("rastgele")
    if r["sifir_grad"]>sinir:b.append("sifir_grad")
    if r["fgsm"]+tol<r["pgd_ce"]:b.append("tek_adim")
    return {"bayraklar":b,"maskeli":bool(b),"en_dusuk_robust":min(r["fgsm"],r["pgd_ce"],r["pgd_marjin"],r["rastgele"])}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    v=json_yukle("veri/masking.json")
    for ad,r in v["raporlar"].items():
        print(ad,maskeleme_tanisi(r,v["tol"],v["sinir"]))
```
```hint
Bayrakları tek tek ve alfabetik sırayla ekle. Raporlanan sağlamlık bütün saldırıların minimumudur.
```
:::

::: anlat Hata vitrini · çalışmış yanlış rapor
Yazar, kusurlu başlangıç kodlarını görünür sentetik veriyle gerçekten çalıştırdı ve sonucu `outputs/yeni-ai-guvence-36/gorunur-run-1.json` dosyasına kaydetti. `cok_iyi_savunma_iddiasi` raporu için kusurlu kod `bayraklar=[]`, `en_dusuk_robust=0.97` verir. Doğru kod `bayraklar=['etkisiz', 'kayip_farki', 'rastgele', 'sifir_grad']`, `en_dusuk_robust=0.31` verir. Aynı satırlar, iki farklı sonuç.

Bu kaydedilmiş bir hesaplama çıktısıdır, model yanıtı değildir ve rapor sentetiktir. Kusurlu çıktıyı görüp "PGD'ye karşı %97 sağlam" diyen biri neyi kaçırır? Hangi alan onu uyarabilirdi? Kendi cümlenle açıkla. Gerçek finaldeki ölçüm ayrıca üretilir; bu sayılar onun yerine konmaz.
:::

::: anlat Gerçek deney: aynı model, iki farklı rapor
Final, `load_digits` üzerinde ReLU MLP'yi eğitir ve her koşuda doğru sınıflanan 128 rastgele test örneği seçer. İkinci "model" yeni bir model değildir: aynı ağırlıkların çıktısı 1000 ile çarpılır. Kararların bütün test kümesinde aynı olduğu ayrıca doğrulanır.

Her iki model için temiz doğruluk, FGSM, CE-PGD, margin-PGD ve rastgele işaret gürültüsü ölçülür; ayrıca CE gradient'inin tam sıfır olduğu örneklerin oranı hesaplanır. PGD adımlarında projeksiyonu **senin `projeksiyon` işlevin** yapar. `kayip_raporu` iki modelin gerçek logitlerinde, `maskeleme_tanisi` iki gerçek raporda sınanır. Ayrıca margin-PGD L2 bütçesiyle de koşar.

Kabul; çıktılarının bağımsız referansla aynı olmasına, kararların değişmemesine, bütçe ve kutunun aşılmamasına bağlıdır. **Saldırının başarılı olması kabul şartı değildir.** Maskeleme sayıları koşudan koşuya değişebilir.

**Kanıt dosyasını oku:** `taban` ve `maskeli` satırlarını yan yana koy. Soru 1: hangi sütunlar farklı, hangileri aynı? Margin-PGD neden aynı kaldı? Soru 2: `kayip_ornekleri` içinde `doygunluk` değerleri ne söylüyor? Soru 3: logit ölçeğini 1000 yerine 10 yapsaydın ne beklerdin; `taban` ile `maskeli` arasında bir yerde mi olurdu? Cevabını tezgâhta yorum olarak yaz; otomatik test bu serbest açıklamayı puanlamaz.
:::

::: gorev Gerçek deney · Logit ölçekli modelde sahte sağlamlık ve margin ile kırılması
Önceki üç görevin `projeksiyon`, `kayip_raporu` ve `maskeleme_tanisi` işlevlerini birleştir. Çalıştır gerçek tabloyu gösterir; Kontrol Et önce üç sözleşmeyi gizli verilerle sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
ortam: gpu
timeout: 180
```
```starter
import ai_lab
import math
def projeksiyon(x,x0,eps,norm,alt,ust):
    if norm=="linf":
        return [min(max(a,alt),ust) for a in x]
    return [b+min(max(a-b,-eps),eps) for a,b in zip(x,x0)]
def kayip_raporu(logit,etiket):
    p=[math.exp(v) for v in logit]
    t=sum(p)
    q=p[etiket]/t
    return {"ce":-math.log(q),"marjin":logit[etiket]-max(logit),"doygunluk":1-q}
def maskeleme_tanisi(r,tol,sinir):
    b=[]
    if r["fgsm"]<r["pgd_ce"]:b.append("tek_adim")
    return {"bayraklar":b,"maskeli":bool(b),"en_dusuk_robust":r["pgd_ce"]}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_36 as D
    D.goster(projeksiyon,kayip_raporu,maskeleme_tanisi)
```
```test
import ai_lab,math
checks=[]
def kontrol(x,m):checks.append(bool(x));ok(x,m)
issues=ai_lab.kod_denetimi(src,('referans_projeksiyon', 'referans_kayip', 'referans_tani', 'kanit_yaz', '_yakin'),izin=())
kontrol(not issues,"kopya/yama/dinamik kod yok: "+str(issues))
if issues:stop()
projeksiyon=need("projeksiyon")
kayip_raporu=need("kayip_raporu")
maskeleme_tanisi=need("maskeleme_tanisi")
def sinama1(f):
    import copy,math,random
    def _r(x,o,e,n,a,u):
        if n=="linf":y=[min(max(p,q-e),q+e) for p,q in zip(x,o)]
        else:
            d=[p-q for p,q in zip(x,o)];m=math.sqrt(sum(v*v for v in d));k=e/m if m>e else 1.0
            y=[q+k*v for q,v in zip(o,d)]
        return [min(max(v,a),u) for v in y]
    def _y(a,b):return len(a)==len(b) and all(abs(p-q)<1e-12 for p,q in zip(a,b))
    try:
        x=[.875,.125,.5];o=[.5,.5,.5];old=(list(x),list(o))
        if f(x,o,.25,"linf",0,1)!=[.75,.25,.5] or (x,o)!=old:return False
        if f([2.0],[.75],.5,"linf",0,1)!=[1.0] or f([-2.0],[.25],.5,"linf",0,1)!=[0.0]:return False
        if not _y(f([3.0,4.0],[0.0,0.0],2.5,"l2",-9,9),[1.5,2.0]) or f([3.0,4.0],[0.0,0.0],5.0,"l2",-9,9)!=[3.0,4.0]:return False
        if f([3.0,4.0],[0.0,0.0],7.0,"l2",-9,9)!=[3.0,4.0]:return False
        if f([3.0,4.0],[0.0,0.0],5.0,"l2",0,1)!=[1,1] or f([-3.0,-4.0],[0.0,0.0],5.0,"l2",-1,0)!=[-1,-1]:return False
        if not _y(f([4.0,5.0],[1.0,1.0],2.5,"l2",-9,9),[2.5,3.0]):return False
        rng=random.Random(36)
        for _ in range(25):
            n=rng.randint(1,6);p=[rng.uniform(-2,3) for _ in range(n)];q=[rng.uniform(0,1) for _ in range(n)];e=rng.uniform(.01,1)
            for m in ("linf","l2"):
                if not _y(f(list(p),list(q),e,m,0,1),_r(p,q,e,m,0,1)):return False
        g=[.5]
        for bad in ((None,g,.1,"l2",0,1),(g,None,.1,"l2",0,1),([],[],.1,"l2",0,1),(g,[.5,.5],.1,"l2",0,1),((.5,),g,.1,"l2",0,1),(g,(.5,),.1,"l2",0,1),(g,g,.1,"l1",0,1),(g,g,0,"l2",0,1),(g,g,-.1,"l2",0,1),(g,g,True,"l2",0,1),(g,g,float("nan"),"l2",0,1),([True],g,.1,"l2",0,1),(g,[float("inf")],.1,"l2",0,1),(["a"],g,.1,"l2",0,1),(g,g,.1,"l2",1,1),(g,g,.1,"l2",2,1),(g,g,.1,"l2",float("nan"),1),(g,g,.1,"l2",0,float("inf"))):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
kontrol(sinama1(projeksiyon),"top kısıtı, L2 ölçekleme, kutu, sınır ve geçersiz girdi")
for ad,mut in [("kutu yok",lambda x,o,e,n,a,u:[p+0.0 for p in x]),("x0 döndür",lambda x,o,e,n,a,u:list(o)),("L2 yerine L∞",lambda x,o,e,n,a,u:projeksiyon(x,o,e,"linf",a,u))]:
    kontrol(not sinama1(mut),"mutant reddedildi: "+ad)
def sinama2(f):
    import copy,math,random
    def _r(z,y):
        m=max(z);p=[math.exp(v-m) for v in z];t=sum(p)
        return {"ce":math.log(t)-(z[y]-m),"marjin":max(v for j,v in enumerate(z) if j!=y)-z[y],"doygunluk":sum(v/t for j,v in enumerate(p) if j!=y)}
    try:
        z=[1000.0,0.0,-1000.0];old=list(z)
        if f(z,0)!={"ce":0.0,"marjin":-1000.0,"doygunluk":0.0} or z!=old:return False
        q=f(z,1)
        if q["ce"]!=1000.0 or q["marjin"]!=1000.0 or q["doygunluk"]!=1.0:return False
        if f([40.0,0.0],0)["doygunluk"]<=0 or abs(f([40.0,0.0],0)["doygunluk"]-math.exp(-40))>1e-25:return False
        if f([-5000.0,-5001.0],0)["marjin"]!=-1.0:return False
        if abs(f([1.0,1.0],0)["ce"]-math.log(2))>1e-12 or f([1.0,1.0],0)["marjin"]!=0.0 or f([1,1],1)["doygunluk"]!=.5:return False
        if f([3.0,5.0,1.0],0)["marjin"]!=2.0 or f([5.0,3.0,4.0],0)["marjin"]!=-1.0:return False
        rng=random.Random(3636)
        for _ in range(25):
            w=[rng.uniform(-30,30) for _ in range(rng.randint(2,7))];y=rng.randrange(len(w))
            if f(list(w),y)!=_r(w,y):return False
        for bad in ((None,0),([],0),([1.0],0),((1.0,2.0),0),([True,1.0],0),([float("nan"),1.0],0),([float("inf"),1.0],0),(["a",1.0],0),([1.0,2.0],2),([1.0,2.0],-1),([1.0,2.0],True),([1.0,2.0],1.0),([1.0,2.0],None)):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
kontrol(sinama2(kayip_raporu),"büyük logit, kararlı doygunluk, margin yönü ve geçersiz girdi")
for ad,mut in [("margin ters",lambda z,y:dict(kayip_raporu(z,y),marjin=-kayip_raporu(z,y)["marjin"])),("doygunluk sıfır",lambda z,y:dict(kayip_raporu(z,y),doygunluk=0.0)),("CE işaret ters",lambda z,y:dict(kayip_raporu(z,y),ce=-kayip_raporu(z,y)["ce"]-1))]:
    kontrol(not sinama2(mut),"mutant reddedildi: "+ad)
def sinama3(f):
    import copy
    try:
        t={"temiz":1.0,"fgsm":.5,"pgd_ce":.25,"pgd_marjin":.25,"rastgele":.875,"sifir_grad":0.0};old=dict(t)
        if f(t,.0,.5)!={"bayraklar":[],"maskeli":False,"en_dusuk_robust":.25} or t!=old:return False
        m={"temiz":1.0,"fgsm":.5,"pgd_ce":1.0,"pgd_marjin":.25,"rastgele":.875,"sifir_grad":1.0}
        if f(m,.0,.5)!={"bayraklar":["etkisiz","kayip_farki","rastgele","sifir_grad","tek_adim"],"maskeli":True,"en_dusuk_robust":.25}:return False
        if f(dict(t,temiz=.5),.25,.5)["bayraklar"]!=["etkisiz"]:return False
        if f(dict(t,temiz=.5),.125,.5)["bayraklar"]!=[]:return False
        b={"temiz":1.0,"fgsm":.75,"pgd_ce":.5,"pgd_marjin":.25,"rastgele":.75,"sifir_grad":0.0}
        if f(b,.25,.5)["bayraklar"]!=[] or f(b,.125,.5)["bayraklar"]!=["kayip_farki"]:return False
        if f(b,.25,.5)["maskeli"] is not False or f(b,.125,.5)["maskeli"] is not True:return False
        c=dict(b,rastgele=.25,pgd_marjin=.5)
        if f(c,.25,.5)["bayraklar"]!=[] or f(c,.125,.5)["bayraklar"]!=["rastgele"]:return False
        d=dict(b,fgsm=.25,pgd_marjin=.5)
        if f(d,.25,.5)["bayraklar"]!=[] or f(d,.125,.5)["bayraklar"]!=["tek_adim"]:return False
        e=dict(b,pgd_marjin=.5,sifir_grad=.5)
        if f(e,.0,.5)["bayraklar"]!=[] or f(e,.0,.25)["bayraklar"]!=["sifir_grad"]:return False
        if f(dict(e,sifir_grad=0.0),.0,0)["bayraklar"]!=[] or f(dict(e,sifir_grad=.125),.0,0)["bayraklar"]!=["sifir_grad"]:return False
        for a,v in (("fgsm",.125),("pgd_ce",.125),("pgd_marjin",.125),("rastgele",.125)):
            q=dict(t,fgsm=.75,pgd_ce=.5,pgd_marjin=.625,rastgele=.875);q[a]=v
            if f(q,1,1)["en_dusuk_robust"]!=.125:return False
        for r,tl,s in ((None,.1,.5),(dict(t,ek=1),.1,.5),({k:v for k,v in t.items() if k!="fgsm"},.1,.5),(dict(t,fgsm=1.5),.1,.5),(dict(t,fgsm=-.1),.1,.5),(dict(t,fgsm=True),.1,.5),(dict(t,temiz=float("nan")),.1,.5),(dict(t,fgsm="a"),.1,.5),(t,-.1,.5),(t,True,.5),(t,float("nan"),.5),(t,.1,-.1),(t,.1,1.5),(t,.1,True),(t,.1,float("nan")),(t,"a",.5)):
            try:f(r,tl,s);return False
            except ValueError:pass
        return True
    except Exception:return False
kontrol(sinama3(maskeleme_tanisi),"beş bayrak, sınırlar, en düşük robust ve geçersiz girdi")
for ad,mut in [("hep temiz",lambda r,t,s:dict(maskeleme_tanisi(r,t,s),bayraklar=[],maskeli=False)),("yalnız PGD robust",lambda r,t,s:dict(maskeleme_tanisi(r,t,s),en_dusuk_robust=r["pgd_ce"])),("maskeli hep doğru",lambda r,t,s:dict(maskeleme_tanisi(r,t,s),maskeli=True))]:
    kontrol(not sinama3(mut),"mutant reddedildi: "+ad)
if not all(checks):stop()
from sandbox import ai_gercek_ai_guvence_36 as D
try:r=D.deney(projeksiyon,kayip_raporu,maskeleme_tanisi)
except ai_lab.GercekLabYok as e:
    kontrol(False,"gerçek deney yok: "+str(e));stop()
kontrol(r["karar_ayni"],"ölçekli model bütün test kümesinde aynı kararı verdi")
kontrol(r["proj_ayni"],"gerçek noktalarda projeksiyon bağımsız hesapla aynı")
kontrol(r["kayip_ayni"],"gerçek logitlerde kayıp raporu bağımsız hesapla aynı")
kontrol(r["tani"]==r["tani_referans"],"iki gerçek raporun tanısı bağımsız hesapla aynı")
kontrol(r["linf_max"]<=r["ayarlar"]["eps"]+1e-5,"L∞ bütçesi aşılmadı")
kontrol(r["l2_max"]<=r["ayarlar"]["eps_l2"]+1e-4,"L2 bütçesi aşılmadı")
kontrol(r["kutu_icinde"],"bozuk örnekler [0,1] içinde")
kontrol(len(set(r["secim"]))==r["ayarlar"]["ornek"],"128 ayrı gerçek örnek ölçüldü")
kontrol(r["maskeli"]["temiz"]==r["taban"]["temiz"],"iki modelde temiz doğruluk aynı")
ai_lab.kanit_yaz("ai-guvence-36-kabul",{"kaynak":"gercek","kabul":all(checks),"ders":"ai-guvence-36","deney":r})
```
```solution
import ai_lab
import math
def projeksiyon(x,x0,eps,norm,alt,ust):
    if not isinstance(x,list) or not isinstance(x0,list) or not x or len(x)!=len(x0) or norm not in ("linf","l2"):raise ValueError("girdi")
    for v in x+x0+[eps,alt,ust]:
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError("sayı")
    if eps<=0 or alt>=ust:raise ValueError("ayar")
    if norm=="linf":
        y=[min(max(a,b-eps),b+eps) for a,b in zip(x,x0)]
    else:
        d=[a-b for a,b in zip(x,x0)]
        n=math.sqrt(sum(v*v for v in d))
        k=eps/n if n>eps else 1.0
        y=[b+k*v for b,v in zip(x0,d)]
    return [min(max(v,alt),ust) for v in y]
def kayip_raporu(logit,etiket):
    if not isinstance(logit,list) or len(logit)<2:raise ValueError("logit")
    for v in logit:
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError("sayı")
    if isinstance(etiket,bool) or not isinstance(etiket,int) or not 0<=etiket<len(logit):raise ValueError("etiket")
    m=max(logit)
    p=[math.exp(v-m) for v in logit]
    t=sum(p)
    return {"ce":math.log(t)-(logit[etiket]-m),"marjin":max(v for j,v in enumerate(logit) if j!=etiket)-logit[etiket],"doygunluk":sum(v/t for j,v in enumerate(p) if j!=etiket)}
def maskeleme_tanisi(r,tol,sinir):
    alan={"temiz","fgsm","pgd_ce","pgd_marjin","rastgele","sifir_grad"}
    if not isinstance(r,dict) or set(r)!=alan:raise ValueError("şema")
    for k in alan:
        if isinstance(r[k],bool) or not isinstance(r[k],(int,float)) or not math.isfinite(r[k]) or not 0<=r[k]<=1:raise ValueError("oran")
    for v in (tol,sinir):
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError("ayar")
    if tol<0 or not 0<=sinir<=1:raise ValueError("ayar")
    b=[]
    if r["temiz"]-r["pgd_ce"]<=tol:b.append("etkisiz")
    if r["pgd_marjin"]+tol<r["pgd_ce"]:b.append("kayip_farki")
    if r["rastgele"]+tol<r["pgd_ce"]:b.append("rastgele")
    if r["sifir_grad"]>sinir:b.append("sifir_grad")
    if r["fgsm"]+tol<r["pgd_ce"]:b.append("tek_adim")
    return {"bayraklar":b,"maskeli":bool(b),"en_dusuk_robust":min(r["fgsm"],r["pgd_ce"],r["pgd_marjin"],r["rastgele"])}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_36 as D
    D.goster(projeksiyon,kayip_raporu,maskeleme_tanisi)
```
```hint
Üç işlevi aynen birleştir. Sonucu okurken aynı modelin iki satırını karşılaştır; fark modelde değil, ölçümdedir.
```
:::

::: anlat Sınır
Bu ders yapay bir logit ölçeklemesiyle tek küçük MLP'de gradient masking mekanizmasını gösterir; gerçek bir savunmanın maskelendiğini veya margin-PGD'ye dayanan bir modelin kanıtlanmış sağlam olduğunu göstermez.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **PGD'de projeksiyon sırası (30 sn).** "Kısıt kümesi $B(x_0,\varepsilon) \cap [\text{alt},\text{üst}]^d$ olduğunda önce norm topuna, ardından kutu sınırlarına kesim uygulanır; aksi halde kutudan taşan bileşenler sahte saldırı gücü veya geçersiz girdi üretir."
2. **Sayısal doygunluk ve `gradient masking` tuzağı (35 sn).** "Logitleri büyük katsayıyla ölçeklemek karar sınırını hiç değiştirmez; ama softmax olasılığını `1.0`'a doygunlaştırıp çapraz entropi gradyanını sıfıra gömerek CE-PGD'yi körleştirir."
3. **Ölçekten bağımsız `margin` kaybı ve tanı bayrakları (30 sn).** "$\max_{j\neq y} z_j - z_y$ fark kaybı logit ölçeğinden etkilenmez; sıfıra çökük gradyan normu, FGSM'nin çok adımlı PGD'yi geçmesi veya CE ile margin-PGD arasındaki uçurum doğrudan `gradient masking` alarmıdır."
4. **Soru (25 sn).** "Bir savunma makalesinde yalnız çapraz entropi tabanlı PGD altında yüksek doğruluk raporlanmışsa hangi üç tanı testini istersin?"
:::
