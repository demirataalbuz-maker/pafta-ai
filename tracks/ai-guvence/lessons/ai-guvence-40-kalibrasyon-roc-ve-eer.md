---
id: ai-guvence-40
title: Kalibrasyon, ROC ve EER · Dedektör Olasılığına Güvenmek
summary: ECE ve MCE hesapla, NLL'i en aza indirerek temperature scaling uygula, eşitlikleri doğru işleyen ROC ve interpolasyonlu EER yaz; gerçek prompt-injection verisinde kalibrasyonun AUC'yi değiştirmediğini ama sabit eşikli alarmı değiştirdiğini ölç.
esleme: ai-savunma-32, ai-saldiri-55, ai-guvence-27, ai-guvence-39
timeout: 60
---

::: anlat Dedektör %90 dediğinde gerçekten %90 mı?
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Temperature scaling güven değerlerini değiştirir, sıralamayı değiştirmez. Yani AUC ve EER aynı kalır ama sabit eşikli alarm değişir | İlk üç görev: `veri/kalibrasyon.json` içindeki **sentetik** değerler. Final: `deepset/prompt-injections` (gerçek etiketli veri, önbellekten) ve `distilbert` özellikleri üzerinde eğitilen küçük sınıflayıcı, GPU | Bu dedektörün sahada ne yapacağını söylemez; test kümesi küçüktür, dağılım kayması ve adaptif saldırgan ölçülmez |
| ECE tek sayı değildir: kova sayısı ile oynar | 5, 10, 20 kovada ECE ve reliability satırları | Yüksek ya da düşük bir ECE'nin üretim için yeterli olduğunu söylemez |

> [!NOT]
> Görevler `veri/kalibrasyon.json` dosyasını okur; dosya sentetiktir. Setup her Çalıştır/Kontrol Et adımında geçici kopya kurar; değişiklikler taşınmaz, **kalıcılık yoktur**. Ekranda ayrı dosya görüntüleyici yoktur; içeriği görmek için `print` kullan. Gizli testler ayrıdır. Final yeni indirme yapmaz; ai-savunma-32 için önbelleğe alınmış sabit revizyonları kullanır.

ai-saldiri-55 ve dedektör dersleri EER/ROC raporlar, ai-guvence-27 eval kalibrasyonunu insan uyumu üzerinden ele alır. Bu ders olasılığın kendisini sınar: **dedektör "%90" dediğinde gerçekten %90 mı?**

**İki ayrı soru.** Ayrım (discrimination) "pozitifler negatiflerden daha yüksek skor alıyor mu?" sorusudur; AUC ve EER bunu ölçer. Kalibrasyon ise "skor bir olasılık olarak doğru mu?" sorusudur. İki özellik bağımsızdır: mükemmel sıralayan bir model aşırı özgüvenli olabilir. Guo vd. (2017) modern derin ağların sık sık aşırı özgüvenli olduğunu göstermiştir.

**ECE.** Tahminleri olasılığa göre eşit genişlikli kovalara böl. Her kovada ortalama güven ile gerçek oranı karşılaştır. `ECE = Σ (n_b/N) · |doğruluk_b - güven_b|`, `MCE` ise en kötü kovanın hatasıdır (Naeini vd. 2015). Bu derste ikili sınıf için pozitif sınıf olasılığı kullanılır. Dikkat: ECE bir kestirimdir. Az veride kova sayısı değişince değeri oynar, boş kovalar görünmez. Bu yüzden rapor kova sayısını ve `n`'yi yazmalıdır.

**Temperature scaling.** Tek parametreli, en basit düzeltme: logiti `T`'ye böl. `p = σ(z/T)`. `T>1` özgüveni azaltır, `T<1` artırır. `T`, **ayrı bir doğrulama kümesinde** NLL en aza indirilerek seçilir; test kümesinde seçmek veri sızıntısıdır ve sonuç iyimser olur. NLL `T`'ye göre tek tepelidir, bu yüzden golden-section araması yeterlidir.

**Değişmezlik kanıtı.** `z/T` her `T>0` için sıralamayı korur. AUC ve ROC'un tamamı yalnız sıraya bağlıdır; bu yüzden aynı kalır. Bu, ölçüm hatası değil matematiksel gerekliliktir. Değişirse kodda hata vardır.

**EER.** Yanlış red (FNR) ile yanlış kabul (FPR) oranının eşit olduğu noktadır. ROC'tan: `d=1-TPR-FPR` işaret değiştirdiği iki komşu nokta arasında doğrusal interpolasyon yapılır. Skor eşitlikleri bir grup olarak işlenmelidir: tek tek yürümek, eşit skorlu örneklerin sırasına göre rastgele bir eğri üretir ve AUC'yi girdi sırasına bağlar.

**Saldırgan ne dener?** Bir dedektörün sabit eşiğini biliyorsa kendi girdisini eşiğin altına indirmeye çalışır. Eşik kalibre edilmemiş bir skora konduysa modelin her güncellenmesinde anlamı sessizce kayar; bu kaymayı fark etmek saldırgan için bir fırsattır.

**Savunma neden kırılır?** Asıl tuzak şudur: AUC aynı kaldığı için "model aynı" denir, ama **sabit eşikli alarm değişmiştir**. Finalde `p>=0.9` kuralının TPR'si kalibrasyonla değişebilir. Yani kalibrasyon sonrası eşikler yeniden seçilmezse dedektör sessizce daha çok kaçırır ya da daha çok alarm üretir. Ayrıca EER tek bir çalışma noktasıdır; güvenlik sistemi genelde düşük FPR'de çalışır, EER oraya yetmez.

**Görev 1'de sık tuzaklar:** `p=1.0` son kovaya aittir; `int(p*k)` dizinin dışına çıkar. Kovaları eşit ağırlıkla ortalamak az örnekli kovayı şişirir. MCE mutlak farkın maksimumudur, işaretli değil.

Kaynaklar: [Guo vd. 2017](https://arxiv.org/abs/1706.04599), [Naeini vd. 2015](https://ojs.aaai.org/index.php/AAAI/article/view/9602). Bu dersteki bütün sayılar yalnız yerel kanıttan gelir.

Köprü: ai-savunma-32 aynı veride distilbert muhafızı eğitir; ai-saldiri-55 EER raporlar; ai-guvence-27 eval kalibrasyonu; ai-guvence-39 oran belirsizliği.
:::

::: tahmin Sıcaklık neyi değiştirir?
Çıktıyı tahmin et, sonra Çalıştır ile karşılaştır.
```python
import math
z = 3.0
for T in (1, 3):
    print(round(1 / (1 + math.exp(-z / T)), 3))
print(sorted([2.0, -1.0, 4.0]) == [v * 3 for v in sorted([2.0 / 3, -1.0 / 3, 4.0 / 3])])
```
???
```cikti
0.953
0.731
True
```
Tahmininle gerçek çıktı arasındaki farkı tezgâhta yorum satırı olarak yaz: `T=3` olasılığı düşürdü, peki `p>=0.9` kuralı ne yapar? Sıralama değişti mi? Sonra üç kusurlu başlangıç kodunu çalıştır ve neyi yanlış ölçtüklerini önce kendin teşhis et; açıklama çözümün ardından gelir.
:::

::: gorev 1 · ECE, MCE ve reliability
`ece_raporu(p,y,kova)`: `p`, `y` aynı uzunlukta dolu liste. `p` bool olmayan, sonlu, `[0,1]`. `y` gerçek int, 0 ya da 1 (bool olamaz). `kova` bool olmayan int, `>=1`. Kova indeksi `min(int(p*kova),kova-1)`. Boş kovalar raporlanmaz. Her kova için `{"kova","adet","guven":p ortalaması,"dogruluk":y ortalaması}` üret; indekse göre sırala. `{"ece":Σ(n_b/N)|dogruluk-guven|,"mce":en büyük |dogruluk-guven|,"kovalar":[...]}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-40")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def ece_raporu(p,y,kova):
    b={}
    for a,c in zip(p,y):
        b.setdefault(min(int(a*kova),kova-1),[]).append((a,c))
    out=[];ece=0.0;mce=0.0
    for i in sorted(b):
        g=sum(a for a,_ in b[i])/len(b[i])
        d=sum(c for _,c in b[i])/len(b[i])
        ece+=abs(d-g)/len(b)
        mce=max(mce,d-g)
        out.append({"kova":i,"adet":len(b[i]),"guven":g,"dogruluk":d})
    return {"ece":ece,"mce":mce,"kovalar":out}

from ai_guvence_veri import json_yukle
v=json_yukle("veri/kalibrasyon.json")
print(ece_raporu(v["p"],v["y"],v["kova"]))
```
```test
def sinama1(f):
    import copy,random
    def _y(a,b):return abs(a-b)<1e-12
    try:
        p=[.125,.375,.875,.75];y=[0,1,1,0];old=(list(p),list(y))
        r=f(p,y,2)
        if (p,y)!=old or set(r)!={"ece","mce","kovalar"}:return False
        if r["kovalar"]!=[{"kova":0,"adet":2,"guven":.25,"dogruluk":.5},{"kova":1,"adet":2,"guven":.8125,"dogruluk":.5}]:return False
        if not _y(r["ece"],.5*.25+.5*.3125) or not _y(r["mce"],.3125):return False
        a=f([.5,1.0,0.0,1],[1,1,0,1],2)
        if [k["adet"] for k in a["kovalar"]]!=[1,3] or a["kovalar"][0]["kova"]!=0:return False
        if f([.5],[1],2)["kovalar"][0]["kova"]!=1:return False
        w=f([.125,.125,.125,.875],[1,1,1,1],4)
        if not _y(w["ece"],.75*.875+.25*.125) or not _y(w["mce"],.875) or [k["kova"] for k in w["kovalar"]]!=[0,3]:return False
        q=f([.875,.875],[0,0],1)
        if q["kovalar"]!=[{"kova":0,"adet":2,"guven":.875,"dogruluk":0.0}] or q["ece"]!=.875:return False
        if f([.25,.25],[1,0],1)["ece"]!=.25:return False
        rng=random.Random(40)
        for _ in range(15):
            n=rng.randint(1,20);u=[rng.random() for _ in range(n)];c=[rng.randint(0,1) for _ in range(n)];k=rng.randint(1,8)
            r=f(list(u),list(c),k)
            if sum(b["adet"] for b in r["kovalar"])!=n:return False
            if abs(r["ece"]-sum(b["adet"]/n*abs(b["dogruluk"]-b["guven"]) for b in r["kovalar"]))>1e-9:return False
        for bad in ((None,[1],1),([.5],None,1),([],[],1),((.5,),[1],1),([.5],(1,),1),([.5],[1,0],1),([1.5],[1],1),([-.1],[1],1),([True],[1],1),([float("nan")],[1],1),(["a"],[1],1),([.5],[2],1),([.5],[True],1),([.5],[1.0],1),([.5],[1],0),([.5],[1],True),([.5],[1],1.5)):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama1(ece_raporu),"kova sınırı, ağırlık, MCE ve geçersiz girdi")
for ad,mut in [("ece sıfır",lambda p,y,k:dict(ece_raporu(p,y,k),ece=0.0)),("mce yerine ece",lambda p,y,k:dict(ece_raporu(p,y,k),mce=ece_raporu(p,y,k)["ece"])),("kova listesi boş",lambda p,y,k:dict(ece_raporu(p,y,k),kovalar=[]))]:
    ok(not sinama1(mut),"mutant reddedildi: "+ad)
```
```solution
import math
def ece_raporu(p,y,kova):
    if not isinstance(p,list) or not isinstance(y,list) or not y or len(p)!=len(y):raise ValueError("liste")
    for v in p:
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<=v<=1:raise ValueError("p")
    for v in y:
        if type(v) is not int or v not in (0,1):raise ValueError("etiket")
    if isinstance(kova,bool) or not isinstance(kova,int) or kova<1:raise ValueError("kova")
    b={}
    for a,c in zip(p,y):
        b.setdefault(min(int(a*kova),kova-1),[]).append((a,c))
    out=[];ece=0.0;mce=0.0
    for i in sorted(b):
        g=sum(a for a,_ in b[i])/len(b[i])
        d=sum(c for _,c in b[i])/len(b[i])
        ece+=len(b[i])/len(p)*abs(d-g)
        mce=max(mce,abs(d-g))
        out.append({"kova":i,"adet":len(b[i]),"guven":g,"dogruluk":d})
    return {"ece":ece,"mce":mce,"kovalar":out}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    v=json_yukle("veri/kalibrasyon.json")
    print(ece_raporu(v["p"],v["y"],v["kova"]))
```
```hint
Kovaya min(int(p*kova),kova-1) ile yerleştir. ECE her kovayı örnek oranıyla ağırlıklar; MCE mutlak farkların en büyüğü.
```
:::

::: anlat Sıcaklık nasıl seçilir?
İkili NLL: `y=1` için `log(1+e^{-z/T})`, `y=0` için `log(1+e^{z/T})`, ortalama alınır. Doğrudan `math.exp` büyük logitte taşar; `u>30` iken `log(1+e^u)≈u` kullanmak yeterince hassas ve güvenlidir.

Analitik bir kontrol: bütün logitler aynıysa (`z=1`) ve pozitif oranı `q` ise en iyi çözüm `1/T = log(q/(1-q))` olur. Aynı veri için model hep doğru ise `T` alt sınıra, hep yanlış ise üst sınıra gider. `nll_once` değeri `T=1`'deki NLL'dir, aralığın dışında kalsa bile raporlanır.

**Görev 2'de sık tuzaklar:** Kaba bir ızgarada `T` seçmek optimumu kaçırır. Olasılığı `1e-9`'a kırpmak büyük hataların cezasını sınırlar ve `T`'yi yanlış yere iter. Test kümesinde seçim yapmak finaldeki ayrımı boşa çıkarır.
:::

::: gorev 2 · NLL ile temperature scaling
`sicaklik_bul(z,y,alt,ust)`: `z`, `y` aynı uzunlukta dolu liste. `z`, `alt`, `ust` bool olmayan sonlu sayı. `y` gerçek int, 0 ya da 1. `0<alt<ust`. `[alt,ust]` içinde ortalama NLL'yi en küçükleyen `T`'yi bul (golden-section önerilir; yanıt `1e-4` hassasiyette olmalı). `{"T":..,"nll_once":NLL(T=1),"nll_sonra":NLL(T)}` döndür. Büyük logitte taşmamalı. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-40")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def sicaklik_bul(z,y,alt,ust):
    def nll(T):
        t=0.0
        for a,c in zip(z,y):
            p=1/(1+math.exp(-a/T))
            t-=math.log(max(p if c==1 else 1-p,1e-9))
        return t/len(z)
    T=min((alt,1.0,ust),key=nll)
    return {"T":T,"nll_once":nll(1.0),"nll_sonra":nll(T)}

from ai_guvence_veri import json_yukle
v=json_yukle("veri/kalibrasyon.json")
print(sicaklik_bul(v["z"],v["zy"],v["alt"],v["ust"]))
```
```test
def sinama2(f):
    import copy,math
    def _n(z,y,T):
        t=0.0
        for a,c in zip(z,y):
            u=-a/T if c==1 else a/T
            t+=u+math.log1p(math.exp(-u)) if u>0 else math.log1p(math.exp(u))
        return t/len(z)
    try:
        z=[1.0,1.0,1.0,1.0];y=[1,1,1,0];old=(list(z),list(y))
        r=f(z,y,.05,50.0)
        if (z,y)!=old or set(r)!={"T","nll_once","nll_sonra"}:return False
        if abs(r["T"]-1/math.log(3))>1e-4 or abs(r["nll_once"]-_n(z,y,1.0))>1e-9 or abs(r["nll_sonra"]-_n(z,y,r["T"]))>1e-9:return False
        a=f([5.0,-5.0],[1,0],.5,4.0)
        if abs(a["T"]-.5)>1e-4:return False
        b=f([5.0,-5.0],[0,1],.5,4.0)
        if abs(b["T"]-4.0)>1e-4:return False
        c=f([900.0,-900.0],[1,1],1.0,100.0)
        if not math.isfinite(c["nll_sonra"]) or abs(c["nll_once"]-_n([900.0,-900.0],[1,1],1.0))>1e-6:return False
        d=f([40.0,-3.0,2.0,-1.0,.5,4.0,-6.0],[1,0,0,0,1,1,1],.05,50.0)
        Z=[40.0,-3.0,2.0,-1.0,.5,4.0,-6.0];Y=[1,0,0,0,1,1,1]
        if d["nll_sonra"]>min(_n(Z,Y,.05+i*.05) for i in range(1000))+1e-9:return False
        for bad in ((None,[1],.1,1),([1.0],None,.1,1),([],[],.1,1),((1.0,),[1],.1,1),([1.0],(1,),.1,1),([1.0],[1,0],.1,1),([True],[1],.1,1),([float("nan")],[1],.1,1),(["a"],[1],.1,1),([1.0],[2],.1,1),([1.0],[True],.1,1),([1.0],[1],0,1),([1.0],[1],-1,1),([1.0],[1],2,1),([1.0],[1],1,1),([1.0],[1],True,2),([1.0],[1],.1,float("inf")),([1.0],[1],float("nan"),1)):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama2(sicaklik_bul),"analitik T, sınırlar, taşma, en küçük NLL ve geçersiz girdi")
for ad,mut in [("T hep bir",lambda z,y,a,u:dict(sicaklik_bul(z,y,a,u),T=1.0)),("nll sonra=nll önce",lambda z,y,a,u:dict(sicaklik_bul(z,y,a,u),nll_sonra=sicaklik_bul(z,y,a,u)["nll_once"])),("alt sınır",lambda z,y,a,u:dict(sicaklik_bul(z,y,a,u),T=a))]:
    ok(not sinama2(mut),"mutant reddedildi: "+ad)
```
```solution
import math
def sicaklik_bul(z,y,alt,ust):
    if not isinstance(z,list) or not isinstance(y,list) or not y or len(z)!=len(y):raise ValueError("liste")
    for v in z+[alt,ust]:
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError("sayı")
    for v in y:
        if type(v) is not int or v not in (0,1):raise ValueError("etiket")
    if alt<=0 or alt>=ust:raise ValueError("aralık")
    def nll(T):
        t=0.0
        for a,c in zip(z,y):
            u=-a/T if c==1 else a/T
            t+=u if u>30 else math.log1p(math.exp(u))
        return t/len(z)
    o=(math.sqrt(5)-1)/2
    a,b=alt,ust
    c,d=b-o*(b-a),a+o*(b-a)
    fc,fd=nll(c),nll(d)
    for _ in range(80):
        if fc<=fd:
            b,d,fd=d,c,fc
            c=b-o*(b-a)
            fc=nll(c)
        else:
            a,c,fc=c,d,fd
            d=a+o*(b-a)
            fd=nll(d)
    T=(a+b)/2
    return {"T":T,"nll_once":nll(1.0),"nll_sonra":nll(T)}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    v=json_yukle("veri/kalibrasyon.json")
    print(sicaklik_bul(v["z"],v["zy"],v["alt"],v["ust"]))
```
```hint
Önce taşmayan bir NLL yaz: u>30 ise u, değilse log1p(exp(u)). Sonra tek tepeli fonksiyon için aralığı daralt.
```
:::

::: anlat Eşitlikler ve interpolasyon
Eşikler gözlenen **benzersiz** skorlardır, büyükten küçüğe. Her eşikte `skor>=esik` pozitif tahmindir. İlk nokta `{esik:None, fpr:0, tpr:0}` olur. AUC trapez kuralıdır; eşitlikleri bir grup olarak işlediğin için çapraz bir parça oluşur ve bu, Mann-Whitney istatistiğine eşittir (ai-saldiri-48'deki yarım puan kuralı).

EER için ROC üzerinde `d=1-TPR-FPR` değerini izle. `d` 1'den başlar, -1'e iner. `d0>0>=d1` olan ilk parçada `eer = fpr0 + d0/(d0-d1)·(fpr1-fpr0)`.

**Görev 3'te sık tuzaklar:** Örnekleri tek tek gezmek eşitliği girdi sırasına bağlar. Dikdörtgen toplam AUC'yi yanlış verir. En yakın noktayı seçmek interpolasyonu atlar ve küçük testlerde EER'i kaba bir değere yuvarlar.
:::

::: gorev 3 · Eşitlik güvenli ROC ve EER
`roc_raporu(s,y)`: `s`, `y` aynı uzunlukta dolu liste. `s` bool olmayan sonlu sayı. `y` gerçek int, 0 ya da 1; iki sınıf da bulunmalı. `noktalar` ilk eleman `{"esik":None,"fpr":0.0,"tpr":0.0}`, sonra her benzersiz skor için büyükten küçüğe `{"esik","fpr","tpr"}`. `auc` trapez toplamı. `eer`, `d=1-tpr-fpr` için `d0>0>=d1` olan ilk parçada doğrusal interpolasyon. `{"noktalar","auc","eer"}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-40")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def roc_raporu(s,y):
    P=sum(y);N=len(y)-P
    nok=[{"esik":None,"fpr":0.0,"tpr":0.0}]
    tp=fp=0
    for a,c in sorted(zip(s,y),reverse=True):
        tp+=c==1;fp+=c==0
        nok.append({"esik":a,"fpr":fp/N,"tpr":tp/P})
    auc=sum((n["fpr"]-m["fpr"])*n["tpr"] for m,n in zip(nok,nok[1:]))
    en=min(nok,key=lambda n:abs(1-n["tpr"]-n["fpr"]))
    return {"noktalar":nok,"auc":auc,"eer":en["fpr"]}

from ai_guvence_veri import json_yukle
v=json_yukle("veri/kalibrasyon.json")
r=roc_raporu(v["p"],v["y"])
for n in r["noktalar"]:print(n)
print("AUC",r["auc"],"EER",r["eer"])
```
```test
def sinama3(f):
    import copy,random
    def _a(s,y):
        u=[a for a,c in zip(s,y) if c==1];d=[a for a,c in zip(s,y) if c==0]
        return sum(1.0 if p>q else .5 if p==q else 0.0 for p in u for q in d)/(len(u)*len(d))
    try:
        s=[.9,.8,.7,.6];y=[1,0,1,0];old=(list(s),list(y))
        r=f(s,y)
        if (s,y)!=old or set(r)!={"noktalar","auc","eer"}:return False
        if r["noktalar"]!=[{"esik":None,"fpr":0.0,"tpr":0.0},{"esik":.9,"fpr":0.0,"tpr":.5},{"esik":.8,"fpr":.5,"tpr":.5},{"esik":.7,"fpr":.5,"tpr":1.0},{"esik":.6,"fpr":1.0,"tpr":1.0}] or r["auc"]!=.75 or r["eer"]!=.5:return False
        e=f([.5,.5],[1,0])
        if e["noktalar"]!=[{"esik":None,"fpr":0.0,"tpr":0.0},{"esik":.5,"fpr":1.0,"tpr":1.0}] or e["auc"]!=.5 or e["eer"]!=.5:return False
        if f([.9,.1],[1,0])["auc"]!=1.0 or f([.9,.1],[1,0])["eer"]!=0.0:return False
        if f([.1,.9],[1,0])["auc"]!=0.0 or f([.1,.9],[1,0])["eer"]!=1.0:return False
        g=f([4,3,2,1],[1,1,0,0])
        if g["eer"]!=0.0 or g["auc"]!=1.0:return False
        k=f([5,4,3,2,1],[1,0,1,1,0])
        if abs(k["auc"]-_a([5,4,3,2,1],[1,0,1,1,0]))>1e-12 or abs(k["eer"]-(.5+(1-2/3-.5)/((1-2/3-.5)-(1-1-.5))*0))>1e-12:return False
        h=f([.5,.5,.5,.2],[1,0,1,0])
        if h["noktalar"][1]!={"esik":.5,"fpr":.5,"tpr":1.0} or abs(h["eer"]-1/3)>1e-12:return False
        if abs(f([4.0,3.0,2.0,2.0,1.0],[1,0,1,0,1])["eer"]-0.6)>1e-12:return False
        rng=random.Random(404)
        for _ in range(25):
            n=rng.randint(2,15);u=[rng.choice([0,1,2,3,rng.random()]) for _ in range(n)];c=[i%2 for i in range(n)]
            q=f(list(u),list(c))
            if abs(q["auc"]-_a(u,c))>1e-9 or q["eer"] is None or not 0<=q["eer"]<=1:return False
            if q["noktalar"][-1]["fpr"]!=1.0 or q["noktalar"][-1]["tpr"]!=1.0:return False
        for bad in ((None,[1,0]),([.5,.5],None),([],[]),((.5,.5),[1,0]),([.5,.5],(1,0)),([.5],[1,0]),([True,.5],[1,0]),([float("nan"),.5],[1,0]),([float("inf"),.5],[1,0]),(["a",.5],[1,0]),([.5,.5],[2,0]),([.9,.5,.1],[2,0,0]),([.9,.5,.1],[-1,1,1]),([.5,.5],[True,0]),([.5,.5],[1.0,0]),([.5,.5],[1,1]),([.5,.5],[0,0])):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama3(roc_raporu),"eşitlik grupları, trapez AUC, interpolasyonlu EER ve geçersiz girdi")
for ad,mut in [("auc sabit",lambda s,y:dict(roc_raporu(s,y),auc=.5)),("eer yok",lambda s,y:dict(roc_raporu(s,y),eer=None)),("noktalar ters",lambda s,y:dict(roc_raporu(s,y),noktalar=roc_raporu(s,y)["noktalar"][::-1]))]:
    ok(not sinama3(mut),"mutant reddedildi: "+ad)
```
```solution
import math
def roc_raporu(s,y):
    if not isinstance(s,list) or not isinstance(y,list) or not y or len(s)!=len(y):raise ValueError("liste")
    for v in s:
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError("skor")
    for v in y:
        if type(v) is not int or v not in (0,1):raise ValueError("etiket")
    P=sum(y);N=len(y)-P
    if P==0 or N==0:raise ValueError("sınıf")
    nok=[{"esik":None,"fpr":0.0,"tpr":0.0}]
    for e in sorted(set(s),reverse=True):
        tp=sum(1 for a,c in zip(s,y) if a>=e and c==1)
        fp=sum(1 for a,c in zip(s,y) if a>=e and c==0)
        nok.append({"esik":e,"fpr":fp/N,"tpr":tp/P})
    auc=sum((n["fpr"]-m["fpr"])*(n["tpr"]+m["tpr"])/2 for m,n in zip(nok,nok[1:]))
    eer=None
    for m,n in zip(nok,nok[1:]):
        d0=1-m["tpr"]-m["fpr"];d1=1-n["tpr"]-n["fpr"]
        if d0>0>=d1:
            eer=m["fpr"]+d0/(d0-d1)*(n["fpr"]-m["fpr"])
            break
    return {"noktalar":nok,"auc":auc,"eer":eer}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    v=json_yukle("veri/kalibrasyon.json")
    r=roc_raporu(v["p"],v["y"])
    for n in r["noktalar"]:print(n)
    print("AUC",r["auc"],"EER",r["eer"])
```
```hint
Eşikleri set ile benzersiz yap ve büyükten küçüğe sırala. Trapez ortalama TPR kullanır. EER'i işaret değişiminde interpole et.
```
:::

::: anlat Hata vitrini · çalışmış yanlış rapor
Yazar, kusurlu başlangıç kodlarını görünür sentetik veriyle gerçekten çalıştırdı ve sonucu `outputs/yeni-ai-guvence-40/gorunur-run-1.json` dosyasına kaydetti. Aynı veride kusurlu kod `ECE=0.217`, doğru kod `ECE=0.259` verir. `T` için kusurlu kaba ızgara `50.0`, doğru arama `4.349` bulur. AUC kusurlu kodda `0.714`, doğru kodda `0.706` çıkar; eşitlikli `0.91` skoru bu farkı yaratır.

Bu kaydedilmiş bir hesaplama çıktısıdır, model yanıtı değildir ve veri sentetiktir. Bu sayılardan birinde hata yapmak dedektörün eşiğini nasıl etkiler? Bir tanesini seç, kendi cümlenle açıkla. Gerçek finaldeki ölçüm ayrıca üretilir; bu sayılar onun yerine konmaz.
:::

::: anlat Gerçek deney: dedektör kalibrasyonu
Final `deepset/prompt-injections` verisini önbellekten okur. Eğitim kümesi her koşuda rastgele karıştırılır, 150 örnek doğrulama için ayrılır; verinin kendi test kümesi hiç eğitimde veya sıcaklık seçiminde kullanılmaz. `distilbert` donuk bir özellik çıkarıcıdır (ortalama havuz), üstüne küçük bir sınıflayıcı başlık GPU'da eğitilir ve bilerek uzun eğitilir ki özgüven oluşsun.

Sonra: (1) **senin `sicaklik_bul`** doğrulama logitlerinde koşar. (2) **senin `ece_raporu`** test kümesinde önce/sonra ve 5, 10, 20 kovayla çalışır. (3) **senin `roc_raporu`** önce/sonra olasılıklara uygulanır. (4) Sabit `p>=0.9` alarmının TPR ve FPR'si önce/sonra ölçülür.

Kabul; işlevlerin referansla uyumuna ve **matematiksel değişmezliğe** bağlıdır: AUC ve EER, kalibrasyonla değişmemelidir. `T>1` veya ECE düşüşü kabul şartı **değildir;** bazı koşularda ECE düşmeyebilir.

**Kanıt dosyasını oku:** Soru 1: `ece_kova_duyarlilik` satırlarında kova sayısı ECE'yi ne kadar oynatıyor? Bu, tek bir ECE sayısını raporlamak için ne demek? Soru 2: `alarm.once` ve `alarm.sonra` farkı AUC ile aynı mı? Bir SOC ekibi kalibrasyondan sonra ne yapmalı? Soru 3: `kovalar_once` satırlarını okuyarak modelin hangi bölgede özgüvenli olduğunu söyle. Bu test kümesinde kaç örnek var ve hangi yargıyı taşımaz? Cevabını tezgâhta yorum olarak yaz; otomatik test bu serbest açıklamayı puanlamaz.
:::

::: gorev Gerçek deney · Prompt-injection dedektöründe ECE, sıcaklık ve EER
Önceki üç görevin `ece_raporu`, `sicaklik_bul` ve `roc_raporu` işlevlerini birleştir. Çalıştır gerçek ölçümü gösterir; Kontrol Et önce üç sözleşmeyi gizli verilerle sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
ortam: gpu
timeout: 240
```
```starter
import ai_lab
import math
def ece_raporu(p,y,kova):
    b={}
    for a,c in zip(p,y):
        b.setdefault(min(int(a*kova),kova-1),[]).append((a,c))
    out=[];ece=0.0;mce=0.0
    for i in sorted(b):
        g=sum(a for a,_ in b[i])/len(b[i])
        d=sum(c for _,c in b[i])/len(b[i])
        ece+=abs(d-g)/len(b)
        mce=max(mce,d-g)
        out.append({"kova":i,"adet":len(b[i]),"guven":g,"dogruluk":d})
    return {"ece":ece,"mce":mce,"kovalar":out}
def sicaklik_bul(z,y,alt,ust):
    def nll(T):
        t=0.0
        for a,c in zip(z,y):
            p=1/(1+math.exp(-a/T))
            t-=math.log(max(p if c==1 else 1-p,1e-9))
        return t/len(z)
    T=min((alt,1.0,ust),key=nll)
    return {"T":T,"nll_once":nll(1.0),"nll_sonra":nll(T)}
def roc_raporu(s,y):
    P=sum(y);N=len(y)-P
    nok=[{"esik":None,"fpr":0.0,"tpr":0.0}]
    tp=fp=0
    for a,c in sorted(zip(s,y),reverse=True):
        tp+=c==1;fp+=c==0
        nok.append({"esik":a,"fpr":fp/N,"tpr":tp/P})
    auc=sum((n["fpr"]-m["fpr"])*n["tpr"] for m,n in zip(nok,nok[1:]))
    en=min(nok,key=lambda n:abs(1-n["tpr"]-n["fpr"]))
    return {"noktalar":nok,"auc":auc,"eer":en["fpr"]}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_40 as D
    D.goster(ece_raporu,sicaklik_bul,roc_raporu)
```
```test
import ai_lab,math
checks=[]
def kontrol(x,m):checks.append(bool(x));ok(x,m)
issues=ai_lab.kod_denetimi(src,('referans_ece', 'referans_sicaklik', 'referans_roc', 'kanit_yaz', '_yakin', '_nll'),izin=())
kontrol(not issues,"kopya/yama/dinamik kod yok: "+str(issues))
if issues:stop()
ece_raporu=need("ece_raporu")
sicaklik_bul=need("sicaklik_bul")
roc_raporu=need("roc_raporu")
def sinama1(f):
    import copy,random
    def _y(a,b):return abs(a-b)<1e-12
    try:
        p=[.125,.375,.875,.75];y=[0,1,1,0];old=(list(p),list(y))
        r=f(p,y,2)
        if (p,y)!=old or set(r)!={"ece","mce","kovalar"}:return False
        if r["kovalar"]!=[{"kova":0,"adet":2,"guven":.25,"dogruluk":.5},{"kova":1,"adet":2,"guven":.8125,"dogruluk":.5}]:return False
        if not _y(r["ece"],.5*.25+.5*.3125) or not _y(r["mce"],.3125):return False
        a=f([.5,1.0,0.0,1],[1,1,0,1],2)
        if [k["adet"] for k in a["kovalar"]]!=[1,3] or a["kovalar"][0]["kova"]!=0:return False
        if f([.5],[1],2)["kovalar"][0]["kova"]!=1:return False
        w=f([.125,.125,.125,.875],[1,1,1,1],4)
        if not _y(w["ece"],.75*.875+.25*.125) or not _y(w["mce"],.875) or [k["kova"] for k in w["kovalar"]]!=[0,3]:return False
        q=f([.875,.875],[0,0],1)
        if q["kovalar"]!=[{"kova":0,"adet":2,"guven":.875,"dogruluk":0.0}] or q["ece"]!=.875:return False
        if f([.25,.25],[1,0],1)["ece"]!=.25:return False
        rng=random.Random(40)
        for _ in range(15):
            n=rng.randint(1,20);u=[rng.random() for _ in range(n)];c=[rng.randint(0,1) for _ in range(n)];k=rng.randint(1,8)
            r=f(list(u),list(c),k)
            if sum(b["adet"] for b in r["kovalar"])!=n:return False
            if abs(r["ece"]-sum(b["adet"]/n*abs(b["dogruluk"]-b["guven"]) for b in r["kovalar"]))>1e-9:return False
        for bad in ((None,[1],1),([.5],None,1),([],[],1),((.5,),[1],1),([.5],(1,),1),([.5],[1,0],1),([1.5],[1],1),([-.1],[1],1),([True],[1],1),([float("nan")],[1],1),(["a"],[1],1),([.5],[2],1),([.5],[True],1),([.5],[1.0],1),([.5],[1],0),([.5],[1],True),([.5],[1],1.5)):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
kontrol(sinama1(ece_raporu),"kova sınırı, ağırlık, MCE ve geçersiz girdi")
for ad,mut in [("ece sıfır",lambda p,y,k:dict(ece_raporu(p,y,k),ece=0.0)),("mce yerine ece",lambda p,y,k:dict(ece_raporu(p,y,k),mce=ece_raporu(p,y,k)["ece"])),("kova listesi boş",lambda p,y,k:dict(ece_raporu(p,y,k),kovalar=[]))]:
    kontrol(not sinama1(mut),"mutant reddedildi: "+ad)
def sinama2(f):
    import copy,math
    def _n(z,y,T):
        t=0.0
        for a,c in zip(z,y):
            u=-a/T if c==1 else a/T
            t+=u+math.log1p(math.exp(-u)) if u>0 else math.log1p(math.exp(u))
        return t/len(z)
    try:
        z=[1.0,1.0,1.0,1.0];y=[1,1,1,0];old=(list(z),list(y))
        r=f(z,y,.05,50.0)
        if (z,y)!=old or set(r)!={"T","nll_once","nll_sonra"}:return False
        if abs(r["T"]-1/math.log(3))>1e-4 or abs(r["nll_once"]-_n(z,y,1.0))>1e-9 or abs(r["nll_sonra"]-_n(z,y,r["T"]))>1e-9:return False
        a=f([5.0,-5.0],[1,0],.5,4.0)
        if abs(a["T"]-.5)>1e-4:return False
        b=f([5.0,-5.0],[0,1],.5,4.0)
        if abs(b["T"]-4.0)>1e-4:return False
        c=f([900.0,-900.0],[1,1],1.0,100.0)
        if not math.isfinite(c["nll_sonra"]) or abs(c["nll_once"]-_n([900.0,-900.0],[1,1],1.0))>1e-6:return False
        d=f([40.0,-3.0,2.0,-1.0,.5,4.0,-6.0],[1,0,0,0,1,1,1],.05,50.0)
        Z=[40.0,-3.0,2.0,-1.0,.5,4.0,-6.0];Y=[1,0,0,0,1,1,1]
        if d["nll_sonra"]>min(_n(Z,Y,.05+i*.05) for i in range(1000))+1e-9:return False
        for bad in ((None,[1],.1,1),([1.0],None,.1,1),([],[],.1,1),((1.0,),[1],.1,1),([1.0],(1,),.1,1),([1.0],[1,0],.1,1),([True],[1],.1,1),([float("nan")],[1],.1,1),(["a"],[1],.1,1),([1.0],[2],.1,1),([1.0],[True],.1,1),([1.0],[1],0,1),([1.0],[1],-1,1),([1.0],[1],2,1),([1.0],[1],1,1),([1.0],[1],True,2),([1.0],[1],.1,float("inf")),([1.0],[1],float("nan"),1)):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
kontrol(sinama2(sicaklik_bul),"analitik T, sınırlar, taşma, en küçük NLL ve geçersiz girdi")
for ad,mut in [("T hep bir",lambda z,y,a,u:dict(sicaklik_bul(z,y,a,u),T=1.0)),("nll sonra=nll önce",lambda z,y,a,u:dict(sicaklik_bul(z,y,a,u),nll_sonra=sicaklik_bul(z,y,a,u)["nll_once"])),("alt sınır",lambda z,y,a,u:dict(sicaklik_bul(z,y,a,u),T=a))]:
    kontrol(not sinama2(mut),"mutant reddedildi: "+ad)
def sinama3(f):
    import copy,random
    def _a(s,y):
        u=[a for a,c in zip(s,y) if c==1];d=[a for a,c in zip(s,y) if c==0]
        return sum(1.0 if p>q else .5 if p==q else 0.0 for p in u for q in d)/(len(u)*len(d))
    try:
        s=[.9,.8,.7,.6];y=[1,0,1,0];old=(list(s),list(y))
        r=f(s,y)
        if (s,y)!=old or set(r)!={"noktalar","auc","eer"}:return False
        if r["noktalar"]!=[{"esik":None,"fpr":0.0,"tpr":0.0},{"esik":.9,"fpr":0.0,"tpr":.5},{"esik":.8,"fpr":.5,"tpr":.5},{"esik":.7,"fpr":.5,"tpr":1.0},{"esik":.6,"fpr":1.0,"tpr":1.0}] or r["auc"]!=.75 or r["eer"]!=.5:return False
        e=f([.5,.5],[1,0])
        if e["noktalar"]!=[{"esik":None,"fpr":0.0,"tpr":0.0},{"esik":.5,"fpr":1.0,"tpr":1.0}] or e["auc"]!=.5 or e["eer"]!=.5:return False
        if f([.9,.1],[1,0])["auc"]!=1.0 or f([.9,.1],[1,0])["eer"]!=0.0:return False
        if f([.1,.9],[1,0])["auc"]!=0.0 or f([.1,.9],[1,0])["eer"]!=1.0:return False
        g=f([4,3,2,1],[1,1,0,0])
        if g["eer"]!=0.0 or g["auc"]!=1.0:return False
        k=f([5,4,3,2,1],[1,0,1,1,0])
        if abs(k["auc"]-_a([5,4,3,2,1],[1,0,1,1,0]))>1e-12 or abs(k["eer"]-(.5+(1-2/3-.5)/((1-2/3-.5)-(1-1-.5))*0))>1e-12:return False
        h=f([.5,.5,.5,.2],[1,0,1,0])
        if h["noktalar"][1]!={"esik":.5,"fpr":.5,"tpr":1.0} or abs(h["eer"]-1/3)>1e-12:return False
        if abs(f([4.0,3.0,2.0,2.0,1.0],[1,0,1,0,1])["eer"]-0.6)>1e-12:return False
        rng=random.Random(404)
        for _ in range(25):
            n=rng.randint(2,15);u=[rng.choice([0,1,2,3,rng.random()]) for _ in range(n)];c=[i%2 for i in range(n)]
            q=f(list(u),list(c))
            if abs(q["auc"]-_a(u,c))>1e-9 or q["eer"] is None or not 0<=q["eer"]<=1:return False
            if q["noktalar"][-1]["fpr"]!=1.0 or q["noktalar"][-1]["tpr"]!=1.0:return False
        for bad in ((None,[1,0]),([.5,.5],None),([],[]),((.5,.5),[1,0]),([.5,.5],(1,0)),([.5],[1,0]),([True,.5],[1,0]),([float("nan"),.5],[1,0]),([float("inf"),.5],[1,0]),(["a",.5],[1,0]),([.5,.5],[2,0]),([.9,.5,.1],[2,0,0]),([.9,.5,.1],[-1,1,1]),([.5,.5],[True,0]),([.5,.5],[1.0,0]),([.5,.5],[1,1]),([.5,.5],[0,0])):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
kontrol(sinama3(roc_raporu),"eşitlik grupları, trapez AUC, interpolasyonlu EER ve geçersiz girdi")
for ad,mut in [("auc sabit",lambda s,y:dict(roc_raporu(s,y),auc=.5)),("eer yok",lambda s,y:dict(roc_raporu(s,y),eer=None)),("noktalar ters",lambda s,y:dict(roc_raporu(s,y),noktalar=roc_raporu(s,y)["noktalar"][::-1]))]:
    kontrol(not sinama3(mut),"mutant reddedildi: "+ad)
if not all(checks):stop()
from sandbox import ai_gercek_ai_guvence_40 as D
try:r=D.deney(ece_raporu,sicaklik_bul,roc_raporu)
except ai_lab.GercekLabYok as e:
    kontrol(False,"gerçek deney yok: "+str(e));stop()
kontrol(r["ece_ayni"],"gerçek olasılıklarda ECE raporu bağımsız hesapla aynı")
kontrol(r["sicaklik_cozum_nll"] is not None and abs(r["sicaklik_cozum_nll"]-r["sicaklik"]["nll_sonra"])<1e-6,"seçilen sıcaklık bağımsız arama kadar iyi")
kontrol(r["roc_ayni"],"gerçek skorlarda ROC bağımsız hesapla aynı")
kontrol(abs(r["auc"]["once"]-r["auc"]["sonra"])<1e-9,"kalibrasyon AUC'yi değiştirmedi")
kontrol(abs(r["eer"]["once"]-r["eer"]["sonra"])<1e-9,"kalibrasyon EER'i değiştirmedi")
kontrol(abs(r["auc"]["once"]-r["auc"]["logit"])<1e-9,"logit ve olasılık aynı sıralamayı verdi")
kontrol(r["boyut"]["test"]>0 and r["boyut"]["dogrulama"]>0,"ayrı doğrulama ve test kümesi kullanıldı")
kontrol(r["sicaklik"]["nll_sonra"]<=r["sicaklik"]["nll_once"]+1e-9,"doğrulama NLL kötüleşmedi")
ai_lab.kanit_yaz("ai-guvence-40-kabul",{"kaynak":"gercek","kabul":all(checks),"ders":"ai-guvence-40","deney":r})
```
```solution
import ai_lab
import math
def ece_raporu(p,y,kova):
    if not isinstance(p,list) or not isinstance(y,list) or not y or len(p)!=len(y):raise ValueError("liste")
    for v in p:
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<=v<=1:raise ValueError("p")
    for v in y:
        if type(v) is not int or v not in (0,1):raise ValueError("etiket")
    if isinstance(kova,bool) or not isinstance(kova,int) or kova<1:raise ValueError("kova")
    b={}
    for a,c in zip(p,y):
        b.setdefault(min(int(a*kova),kova-1),[]).append((a,c))
    out=[];ece=0.0;mce=0.0
    for i in sorted(b):
        g=sum(a for a,_ in b[i])/len(b[i])
        d=sum(c for _,c in b[i])/len(b[i])
        ece+=len(b[i])/len(p)*abs(d-g)
        mce=max(mce,abs(d-g))
        out.append({"kova":i,"adet":len(b[i]),"guven":g,"dogruluk":d})
    return {"ece":ece,"mce":mce,"kovalar":out}
def sicaklik_bul(z,y,alt,ust):
    if not isinstance(z,list) or not isinstance(y,list) or not y or len(z)!=len(y):raise ValueError("liste")
    for v in z+[alt,ust]:
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError("sayı")
    for v in y:
        if type(v) is not int or v not in (0,1):raise ValueError("etiket")
    if alt<=0 or alt>=ust:raise ValueError("aralık")
    def nll(T):
        t=0.0
        for a,c in zip(z,y):
            u=-a/T if c==1 else a/T
            t+=u if u>30 else math.log1p(math.exp(u))
        return t/len(z)
    o=(math.sqrt(5)-1)/2
    a,b=alt,ust
    c,d=b-o*(b-a),a+o*(b-a)
    fc,fd=nll(c),nll(d)
    for _ in range(80):
        if fc<=fd:
            b,d,fd=d,c,fc
            c=b-o*(b-a)
            fc=nll(c)
        else:
            a,c,fc=c,d,fd
            d=a+o*(b-a)
            fd=nll(d)
    T=(a+b)/2
    return {"T":T,"nll_once":nll(1.0),"nll_sonra":nll(T)}
def roc_raporu(s,y):
    if not isinstance(s,list) or not isinstance(y,list) or not y or len(s)!=len(y):raise ValueError("liste")
    for v in s:
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError("skor")
    for v in y:
        if type(v) is not int or v not in (0,1):raise ValueError("etiket")
    P=sum(y);N=len(y)-P
    if P==0 or N==0:raise ValueError("sınıf")
    nok=[{"esik":None,"fpr":0.0,"tpr":0.0}]
    for e in sorted(set(s),reverse=True):
        tp=sum(1 for a,c in zip(s,y) if a>=e and c==1)
        fp=sum(1 for a,c in zip(s,y) if a>=e and c==0)
        nok.append({"esik":e,"fpr":fp/N,"tpr":tp/P})
    auc=sum((n["fpr"]-m["fpr"])*(n["tpr"]+m["tpr"])/2 for m,n in zip(nok,nok[1:]))
    eer=None
    for m,n in zip(nok,nok[1:]):
        d0=1-m["tpr"]-m["fpr"];d1=1-n["tpr"]-n["fpr"]
        if d0>0>=d1:
            eer=m["fpr"]+d0/(d0-d1)*(n["fpr"]-m["fpr"])
            break
    return {"noktalar":nok,"auc":auc,"eer":eer}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_40 as D
    D.goster(ece_raporu,sicaklik_bul,roc_raporu)
```
```hint
Üç işlevi aynen birleştir. Değişmezlik başarısızsa önce eşik sırasını ve eşitlik gruplamasını kontrol et.
```
:::

::: anlat Sınır
Bu ders küçük bir test kümesinde donuk distilbert özellikleri ve tek bir baş modelle kalibrasyon ve eşik davranışını gösterir; bu dedektörün sahadaki hata oranını, dağılım kaymasına veya adaptif saldırgana dayanıklılığını göstermez.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Sıralama başarısı (`AUC`) ile kalibrasyon (`ECE`) farkı (35 sn).** "Bir güvenlik dedektörü zararlı istemleri temizlerden iyi ayırıp yüksek `ROC-AUC` alabilir ama olasılıkları aşırı özgüvenliyse sabit olasılık eşikleri sahada yanlış alarm veya kaçırma üretir."
2. **Sıcaklık ölçekleme (`temperature scaling`) değişmezliği (30 sn).** "Logitleri pozitif $T$ sayısına bölmek sıralamayı koruduğu için `AUC` ve `EER`'i değiştirmez; doğrulama kümesinde NLL'yi minimize eden $T$ yalnız güven kalibrasyonunu (`ECE`) düzeltir."
3. **Eşit skor gruplaması ve `EER` (30 sn).** "ROC eğrisinde aynı skora sahip örnekleri tek adımda işlemezsek girdi sırasına bağlı yapay köşegenler oluşur; `FPR` ile `FNR = 1 - TPR` dengesi (`EER`) eşik seçimi için ortak referans noktası verir."
4. **Soru (25 sn).** "Sıcaklık ölçekleme `ROC` eğrisini değiştirmiyorsa üretimdeki güvenlik kapısında hangi karar mekanizmaları iyi kalibre edilmiş olasılığa ihtiyaç duyar?"
:::
