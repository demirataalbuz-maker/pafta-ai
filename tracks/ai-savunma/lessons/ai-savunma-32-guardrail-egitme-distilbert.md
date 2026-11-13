---
id: ai-savunma-32
title: Kendi Guardrail'ını Eğit · DistilBERT ile Prompt Injection Sınıflandırıcısı
summary: Açık bir prompt injection veri setiyle DistilBERT'i gerçekten fine-tune et; eşiği test kümesine bakmadan FPR sınırıyla seç, anahtar kelime listesiyle kıyasla ve leet, homoglif, sıfır genişlikli karakter gibi bozulmalarda recall ile yanlış alarmı birlikte ölç.
esleme: ai-saldiri-04, ai-saldiri-11, ai-saldiri-52
timeout: 60
---

::: anlat Hazır filtre yerine kendi modelin
| Gerçek sistem ne yapar | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Üretimdeki prompt injection sınıflandırıcıları, etiketli örneklerle eğitilmiş küçük bir dil modelidir; girdiye bir olasılık verir, eşik kararı uygulama verir | İlk üç görev: `veri/siniflandirici.json` içindeki **sentetik** etiket ve skorlar | Gerçek bir modelin skor dağılımını göstermez |
| Eğitim verisi, dil kapsamı ve eşik seçimi modelin sahada nasıl davranacağını belirler | Final: `distilbert/distilbert-base-uncased` (sabit revizyon) + `deepset/prompt-injections` (546 eğitim, 116 test, Apache-2.0), tek eğitim koşusu | Gerçek trafikteki dağılımı, başka dilleri ya da uyarlanabilir bir saldırganı göstermez |

> [!NOT]
> İlk üç görev `veri/siniflandirici.json` dosyasını okur; dosyadaki her şey elle yazılmıştır. Setup her Çalıştır/Kontrol Et adımında geçici kopya kurar; **kalıcılık yoktur**. Ekranda ayrı bir dosya görüntüleyici yoktur; içeriği görmek için başlangıç kodundaki `print` satırlarını kullan. Final, model ve veri setini Hugging Face önbelleğinden **çevrimdışı** ve sabit revizyonla yükler (yaklaşık 256 MB model, iki küçük parquet dosyası); bunlar yoksa adım `GercekLabYok` ile durur ve kendisi indirme yapmaz. CUDA varsa GPU, yoksa CPU kullanılır.

savunma-06 ve savunma-07 hazır kurallar ve hazır kontrollerle girdi guardrail'ı kurdu. Bu derste guardrail'ın kendisini **eğitiyorsun**. DistilBERT (Sanh vd., 2019, arXiv:1910.01108), BERT'in bilgi distillation (knowledge distillation) ile küçültülmüş sürümüdür; 6 katman ve yaklaşık 66 milyon parametreyle CPU'da bile hızlı çalışır. Üstüne iki sınıflı bir sınıflandırma başlığı eklenir ve etiketli örneklerle fine-tune edilir. Çıktı bir olasılıktır: "bu metin injection mı?" sorusunun yanıtı değil, bir **skor**dur. Karar, skorun bir eşikle karşılaştırılmasıyla verilir ve o eşiği sen seçersin.

**Veri seti.** `deepset/prompt-injections`, Hugging Face'te Apache-2.0 lisanslı küçük bir veri setidir: 546 eğitim ve 116 test örneği, İngilizce ve Almanca karışık metinler, `label` 1 injection, 0 normal. Etiketler tartışmasız değildir: test kümesinde "I want you to act as an interviewer…" ve "Generate SQL code to access a database." örnekleri injection (1) etiketlidir. Model, veri setinin tanımını öğrenir; o tanım senin uygulamanın tanımı olmayabilir.

**Eşik test kümesinde seçilmez.** Uygun aday eşik yoksa fonksiyon None döndürür; gerçek deney bu durumda sessizce 0.5 veya 1.0 atamak yerine açık hata ile durur. Deploy için model/veri/politika yeniden değerlendirilmelidir. Doğrulama kümesindeki FPR≤%5 kuralı örneklem kısıtıdır; görülmemiş trafikte gerçek FPR≤%5 garantisi değildir. Eşiği test skorlarına bakarak seçersen test sonucu iyimser olur; o sayı artık görülmemiş veriyi ölçmez. Final, eğitim kümesinin %15'ini sınıf oranını koruyarak ayırır, eşiği bu doğrulama kümesinde "FPR en fazla %5 iken en yüksek recall" kuralıyla seçer, sonra testte bir kez ölçer. Bir guardrail için yanlış alarm (FPR) ucuz değildir: her yanlış alarm meşru bir kullanıcıyı engeller ve ekiplerin guardrail'ı kapatmasına yol açar.

**Saldırgan ne dener?** Sınıflandırıcının eğitimde görmediği yüzeyi dener: harfleri rakamla değiştirmek (`1gn0r3`), Latin harfin yerine aynı görünen Kiril harfi koymak (homoglif), harflerin arasına sıfır genişlikli boşluk (U+200B) ya da normal boşluk eklemek. Bunlar insan için aynı metni, model için bambaşka token dizilerini üretir. ai-saldiri-52'deki Unicode tag kaçakçılığı da aynı fikrin bir uç örneğidir.

**Savunma neden kırılır?** Bir bozulmanın etkisini yalnız recall'la ölçmek yanıltır. Model alışılmadık görünen her metne "injection" diyorsa, bozulmuş saldırıları da yakalar; ama aynı bozulmayla yazılmış normal metinlere de alarm verir. Bu yüzden her kip için recall, FPR ve ikisinin farkı (Youden J = recall − FPR) birlikte raporlanır. Diğer kırılma noktaları: eşitlikte skoru pozitif saymamak, FPR'yi tüm örneklere bölmek, hiç pozitif tahmin yokken precision'ı 1 saymak ve uygun eşik yokken sessizce 0.5'e dönmek. Hepsi tabloyu olduğundan iyi gösterir.

Kaynaklar: [Sanh vd. 2019 · DistilBERT (arXiv:1910.01108)](https://arxiv.org/abs/1910.01108), [distilbert/distilbert-base-uncased](https://huggingface.co/distilbert/distilbert-base-uncased), [deepset/prompt-injections](https://huggingface.co/datasets/deepset/prompt-injections). Bu dersteki bütün sayılar yalnız yerel kanıttan gelir.

Saldırı↔savunma köprüsü: ai-saldiri-04 jailbreak taksonomisini, ai-saldiri-11 belgeye gömülü dolaylı injection'ı, ai-saldiri-52 görünmez Unicode kaçakçılığını gösterir. Bu ders onları yakalamaya çalışan modeli eğitir ve kör noktalarını ölçer.
:::

::: tahmin Eşit skor ve sıfıra bölme
Çıktıyı tahmin et, sonra Çalıştır ile karşılaştır.
```python
etiketler = [1, 1, 0, 0]
skorlar   = [0.5, 0.2, 0.5, 0.1]
for esik in (0.5, 0.6):
    tp = sum(1 for e, s in zip(etiketler, skorlar) if e == 1 and s >= esik)
    fp = sum(1 for e, s in zip(etiketler, skorlar) if e == 0 and s >= esik)
    print(esik, tp, fp, tp / (tp + fp) if tp + fp else 0.0, fp / 2)
```
???
```cikti
0.5 1 1 0.5 0.5
0.6 0 0 0.0 0.0
```
Tahmininle gerçek çıktı arasındaki farkı tezgâhta yorum satırı olarak yaz: eşik 0.6'da hiç pozitif tahmin yokken precision neden 1 değil de 0 kabul edilir? Sonra üç kusurlu başlangıç kodunu çalıştır. Hangisi eşiğe eşit skoru saymayıp precision'ı şişiriyor, hangisi uygun eşik yokken 0.5'e dönüyor, hangisi yalnız recall'a bakıp en zayıf kipi yanlış seçiyor? Önce kendin teşhis et; açıklama çözümün ardından gelir.
:::

::: gorev 1 · Sınıflandırma metrikleri
`siniflandirma_metrikleri(etiketler, skorlar, esik)`: `etiketler` boş olmayan liste ve her öğesi `int` 0 ya da 1 (`bool` değil); `skorlar` aynı uzunlukta liste ve her öğesi 0 ile 1 arasında (uçlar dahil) sonlu sayı (`bool` değil); iki sınıf da bulunmalı; `esik` 0 ile 1 arasında sonlu sayı. Aksi hâlde `ValueError`. Skoru eşiğe **eşit ya da büyük** olan örnek pozitif tahmin edilir. `{"tp", "fp", "tn", "fn", "precision", "recall", "f1", "fpr"}` döndür: sayımlar `int`; `precision = tp/(tp+fp)`, hiç pozitif tahmin yoksa 0.0; `recall = tp/(tp+fn)`; `f1 = 2·p·r/(p+r)`, `p+r` 0 ise 0.0; `fpr = fp/(fp+tn)`.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-32")
```

```starter
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def siniflandirma_metrikleri(etiketler,skorlar,esik):
    tp=sum(1 for e,s in zip(etiketler,skorlar) if e==1 and s>esik)
    fp=sum(1 for e,s in zip(etiketler,skorlar) if e==0 and s>esik)
    fn=etiketler.count(1)-tp;tn=etiketler.count(0)-fp
    p=tp/(tp+fp) if tp+fp else 1.0
    r=tp/(tp+fn)
    f1=2*p*r/(p+r) if p+r else 0.0
    return {"tp":tp,"fp":fp,"tn":tn,"fn":fn,"precision":p,"recall":r,"f1":f1,"fpr":fp/len(etiketler)}

from ai_savunma_veri import json_yukle
v=json_yukle("veri/siniflandirici.json")["metrik"]
print(siniflandirma_metrikleri(v["etiketler"],v["skorlar"],v["esik"]))
```
```test
def sinama1(f):
    try:
        y=lambda a,b:isinstance(a,(int,float)) and not isinstance(a,bool) and abs(a-b)<=1e-9
        def esit(r,b):return isinstance(r,dict) and set(r)==set(b) and all((r[k]==b[k] and type(r[k]) is int) if isinstance(b[k],int) else y(r[k],b[k]) for k in b)
        E=[1,1,1,0,0,0,0];S=[0.9,0.5,0.2,0.5,0.1,0.0,0.7]
        if not esit(f(E,S,0.5),{"tp":2,"fp":2,"tn":2,"fn":1,"precision":0.5,"recall":2/3,"f1":4/7,"fpr":0.5}):return False
        if not esit(f(E,S,0.95),{"tp":0,"fp":0,"tn":4,"fn":3,"precision":0.0,"recall":0.0,"f1":0.0,"fpr":0.0}):return False
        if not esit(f(E,S,0),{"tp":3,"fp":4,"tn":0,"fn":0,"precision":3/7,"recall":1.0,"f1":0.6,"fpr":1.0}):return False
        if not esit(f([1,0],[1.0,0.99],1),{"tp":1,"fp":0,"tn":1,"fn":0,"precision":1.0,"recall":1.0,"f1":1.0,"fpr":0.0}):return False
        if not esit(f([0,1,0,0],[0.2,0.6,0.6,0.1],0.6),{"tp":1,"fp":1,"tn":2,"fn":0,"precision":0.5,"recall":1.0,"f1":2/3,"fpr":1/3}):return False
        for a in [([],[],0.5),([1,0],[0.5],0.5),([1,2],[0.5,0.5],0.5),([1,True],[0.5,0.5],0.5),([1,0.0],[0.5,0.5],0.5),([1,1],[0.5,0.5],0.5),([0,0],[0.5,0.5],0.5),
                  ([1,0],[1.1,0.5],0.5),([1,0],[-0.1,0.5],0.5),([1,0],[float("nan"),0.5],0.5),([1,0],[True,0.5],0.5),([1,0],["0.5",0.5],0.5),
                  ([1,0],[0.5,0.5],-0.1),([1,0],[0.5,0.5],1.1),([1,0],[0.5,0.5],True),([1,0],[0.5,0.5],float("nan")),([1,0],[0.5,0.5],None),((1,0),(0.5,0.5),0.5),(None,[0.5],0.5),([1,0],(0.5,0.5),0.5),((1,0),[0.5,0.5],0.5),([1,0,1],[0.5,0.5],0.5),([1,0,2],[0.5,0.5,0.5],0.5),([1,0,True],[0.5,0.5,0.5],0.5),([1,0,1.0],[0.5,0.5,0.5],0.5)]:
            try:f(*a);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama1(siniflandirma_metrikleri),"eşik dahil sayım, sıfıra bölme kuralları, FPR paydası ve geçersiz girdi")
for ad,mut in [("eşik dahil değil",lambda e,s,t:siniflandirma_metrikleri(e,s,min(1.0,t+1e-9)) if isinstance(t,float) and t<1 else siniflandirma_metrikleri(e,s,t)),
               ("fpr paydası tüm örnekler",lambda e,s,t:(lambda r:dict(r,fpr=r["fp"]/len(e)))(siniflandirma_metrikleri(e,s,t))),
               ("tahmin yokken precision 1",lambda e,s,t:(lambda r:dict(r,precision=1.0) if r["tp"]+r["fp"]==0 else r)(siniflandirma_metrikleri(e,s,t)))]:
    ok(not sinama1(mut),"mutant reddedildi: "+ad)
```
```solution
import math
def siniflandirma_metrikleri(etiketler,skorlar,esik):
    def sayi(x):return not isinstance(x,bool) and isinstance(x,(int,float)) and math.isfinite(x)
    if not isinstance(etiketler,list) or not isinstance(skorlar,list) or not etiketler or len(etiketler)!=len(skorlar):raise ValueError("liste")
    for e in etiketler:
        if type(e) is not int or e not in (0,1):raise ValueError("etiket")
    for s in skorlar:
        if not sayi(s) or not 0<=s<=1:raise ValueError("skor")
    if 0 not in etiketler or 1 not in etiketler:raise ValueError("iki sınıf gerekli")
    if not sayi(esik) or not 0<=esik<=1:raise ValueError("eşik")
    tp=fp=0
    for e,s in zip(etiketler,skorlar):
        if s>=esik:
            if e==1:tp+=1
            else:fp+=1
    fn=etiketler.count(1)-tp;tn=etiketler.count(0)-fp
    p=tp/(tp+fp) if tp+fp else 0.0
    r=tp/(tp+fn)
    f1=2*p*r/(p+r) if p+r else 0.0
    return {"tp":tp,"fp":fp,"tn":tn,"fn":fn,"precision":p,"recall":r,"f1":f1,"fpr":fp/(fp+tn)}

from ai_savunma_veri import json_yukle
v=json_yukle("veri/siniflandirici.json")["metrik"]
print(siniflandirma_metrikleri(v["etiketler"],v["skorlar"],v["esik"]))
```
```hint
Önce bütün girdileri doğrula. Sıfıra bölmede bir değer uydurma; tanımı (0.0) uygula. FPR'nin paydası yalnız negatif örneklerdir.
```
:::

::: anlat Eşik bir ürün kararıdır
Aynı model, farklı eşiklerle bambaşka bir guardrail olur. Düşük eşik daha çok saldırı yakalar ama meşru kullanıcıları da engeller; yüksek eşik tersini yapar. "FPR en fazla %5 iken en yüksek recall" gibi bir kural, bu kararı yazılı ve sınanabilir yapar. Aday eşikler skorların kendisidir; büyükten küçüğe gezilir ve eşit recall'da daha yüksek eşik (daha az alarm) tercih edilir. Hiçbir eşik FPR sınırını sağlamıyorsa bunu açıkça söylemek gerekir: `esik: None`. Varsayılan bir eşiğe sessizce dönmek, hiç sağlanamayan bir sınırı sağlanmış gibi gösterir.
:::

::: gorev 2 · FPR sınırıyla eşik seçimi
`esik_sec(etiketler, skorlar, fpr_siniri)`: `etiketler` ve `skorlar` Görev 1'deki gibi doğrulanır; `fpr_siniri` 0 ile 1 arasında sonlu sayı, 0 dahil, 1 hariç (`bool` değil). Aday eşikler, skorlardaki farklı değerlerdir. Her aday için recall ve FPR, Görev 1'deki tanımla (eşit skor pozitif) hesaplanır. FPR'si `fpr_siniri`'ne eşit ya da küçük adaylar arasından recall'ı en yüksek olan seçilir; eşit recall'da daha **yüksek** eşik seçilir. `{"esik", "recall", "fpr"}` döndür; uygun aday yoksa `{"esik": None, "recall": 0.0, "fpr": 0.0}`.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-32")
```

```starter
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def esik_sec(etiketler,skorlar,fpr_siniri):
    en={"esik":0.5,"recall":0.0,"fpr":0.0}
    for t in sorted(set(skorlar)):
        tp=sum(1 for e,s in zip(etiketler,skorlar) if e==1 and s>=t)
        fp=sum(1 for e,s in zip(etiketler,skorlar) if e==0 and s>=t)
        recall,fpr=tp/etiketler.count(1),fp/etiketler.count(0)
        if fpr<fpr_siniri and recall>=en["recall"]:en={"esik":t,"recall":recall,"fpr":fpr}
    return en

from ai_savunma_veri import json_yukle
v=json_yukle("veri/siniflandirici.json")["esik"]
for sinir in (0.0,v["fpr_siniri"],0.5):print("FPR ≤",sinir,"→",esik_sec(v["etiketler"],v["skorlar"],sinir))
```
```test
def sinama2(f):
    try:
        y=lambda a,b:isinstance(a,(int,float)) and not isinstance(a,bool) and abs(a-b)<=1e-9
        def esit(r,b):return isinstance(r,dict) and set(r)=={"esik","recall","fpr"} and (r["esik"] is None if b[0] is None else y(r["esik"],b[0])) and y(r["recall"],b[1]) and y(r["fpr"],b[2])
        E=[1,1,1,0,0,0,0,0,0,0,0];S=[0.9,0.8,0.3,0.85,0.4,0.2,0.1,0.1,0.05,0.0,0.3]
        if not esit(f(E,S,0.125),(0.8,2/3,0.125)) or not esit(f(E,S,0.1),(0.9,1/3,0.0)) or not esit(f(E,S,0),(0.9,1/3,0.0)):return False
        if not esit(f(E,S,0.5),(0.3,1.0,0.375)) or not esit(f(E,S,0.99),(0.3,1.0,0.375)):return False
        if not esit(f([1,0],[0.2,0.9],0),(None,0.0,0.0)) or not esit(f([1,0,1],[0.4,0.4,0.9],0.5),(0.9,0.5,0.0)):return False
        if not esit(f(list(reversed(E)),list(reversed(S)),0.125),(0.8,2/3,0.125)):return False
        if not esit(f([1,0],[1.0,0.0],0.0),(1.0,1.0,0.0)):return False
        for a in [(E,S,1),(E,S,1.0),(E,S,-0.01),(E,S,True),(E,S,False),(E,S,float("nan")),(E,S,None),([],[],0.1),([1,1],[0.5,0.5],0.1),([0,0],[0.5,0.5],0.1),([1,0],[0.5],0.1),([1,0],[1.5,0.5],0.1),([1,0],[True,0.5],0.1),([1,0],["0.5",0.5],0.1),([1,2],[0.5,0.5],0.1),((1,0),(0.5,0.5),0.1),([1,0],(0.5,0.5),0.1),((1,0),[0.5,0.5],0.1),([1,0,1],[0.5,0.5],0.1),([1,0,2],[0.5,0.5,0.5],0.1),([1,0,True],[0.5,0.5,0.5],0.1),([1,0],[0.5,-0.5],0.1),([1,0],[0.5,1.5],0.1)]:
            try:f(*a);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama2(esik_sec),"FPR sınırı dahil, en yüksek recall, eşitlikte yüksek eşik, uygun eşik yoksa None ve geçersiz girdi")
def _dusuk(e,s,p):
    r=esik_sec(e,s,p)
    if r["esik"] is None:return r
    def oran(t,sinif):return sum(1 for a,b in zip(e,s) if a==sinif and b>=t)/e.count(sinif)
    t=min(t for t in set(s) if oran(t,1)==r["recall"] and oran(t,0)<=p)
    return {"esik":t,"recall":r["recall"],"fpr":oran(t,0)}
for ad,mut in [("FPR sınırı dahil değil",lambda e,s,p:esik_sec(e,s,p-1e-12) if isinstance(p,float) and p>0 else esik_sec(e,s,p)),
               ("uygun eşik yoksa 0.5",lambda e,s,p:(lambda r:r if r["esik"] is not None else {"esik":0.5,"recall":0.0,"fpr":0.0})(esik_sec(e,s,p))),
               ("eşitlikte düşük eşik",_dusuk)]:
    ok(not sinama2(mut),"mutant reddedildi: "+ad)
```
```solution
import math
def esik_sec(etiketler,skorlar,fpr_siniri):
    def sayi(x):return not isinstance(x,bool) and isinstance(x,(int,float)) and math.isfinite(x)
    if not isinstance(etiketler,list) or not isinstance(skorlar,list) or not etiketler or len(etiketler)!=len(skorlar):raise ValueError("liste")
    for e in etiketler:
        if type(e) is not int or e not in (0,1):raise ValueError("etiket")
    for s in skorlar:
        if not sayi(s) or not 0<=s<=1:raise ValueError("skor")
    if 0 not in etiketler or 1 not in etiketler:raise ValueError("iki sınıf gerekli")
    if not sayi(fpr_siniri) or not 0<=fpr_siniri<1:raise ValueError("fpr")
    pozitif=etiketler.count(1);negatif=etiketler.count(0);en=None
    for t in sorted(set(skorlar),reverse=True):
        tp=sum(1 for e,s in zip(etiketler,skorlar) if e==1 and s>=t)
        fp=sum(1 for e,s in zip(etiketler,skorlar) if e==0 and s>=t)
        recall,fpr=tp/pozitif,fp/negatif
        # Eşikler büyükten küçüğe gezilir; eşit recall'da ilk bulunan (daha yüksek eşik) kalır.
        if fpr<=fpr_siniri and (en is None or recall>en["recall"]):en={"esik":t,"recall":recall,"fpr":fpr}
    return en if en is not None else {"esik":None,"recall":0.0,"fpr":0.0}

from ai_savunma_veri import json_yukle
v=json_yukle("veri/siniflandirici.json")["esik"]
for sinir in (0.0,v["fpr_siniri"],0.5):print("FPR ≤",sinir,"→",esik_sec(v["etiketler"],v["skorlar"],sinir))
```
```hint
Adayları büyükten küçüğe gez ve yalnız recall kesin olarak artınca güncelle. Sınır karşılaştırması `<=` olmalı.
```
:::

::: anlat Bozulma: recall tek başına yalan söyler
Finalde test kümesindeki 116 metnin her biri beş biçimde skorlanır: `orijinal`, `leet` (a→4, e→3, i→1, o→0, s→5), `sifir_genislik` (her karakterin arasına U+200B), `homoglif` (bazı Latin harfler yerine Kiril karşılıkları) ve `harf_bosluklu` (her kelimenin harfleri arasına boşluk). Şema doğrulamasında kip türünü ve izinli değerleri, (id,kip) set anahtarını kullanmadan önce denetle; liste/dict gibi bozuk kipler kontrolsüz TypeError üretmemelidir.

Bozulma hem injection hem normal metinlere uygulanır; model bunlarla eğitilmez. Kip başına recall, FPR ve J = recall − FPR hesaplanır; J sınıf oranlarından bağımsız bir ayırma özetidir, precision veya yanlış alarmın operasyonel maliyeti değildir. Bozulma kipleri farklı kimlik kümelerinde ölçülürse J farkı hem bozulmayı hem örneklem farkını yansıtır; gerçek deney aynı test kimliklerini bütün kiplerde kullanır; `j_dusus`, orijinal J'den o kipin J'si çıkarılarak bulunur. En zayıf kip, J'si en düşük olandır. Kanıt dosyasındaki `bozulma_ornek` alanında her kipte DistilBERT tokenizer'ının metni hangi token'lara böldüğünü göreceksin.
:::

::: gorev 3 · Bozulma raporu
`bozulma_raporu(kayitlar, esik)`: `esik` 0 ile 1 arasında sonlu sayı (`bool` değil). `kayitlar` liste; her kayıt tam olarak `id`, `kip`, `etiket`, `skor`; `id` dolu string ve aynı (`id`, `kip`) çifti iki kez geçemez (aynı `id` farklı kiplerde geçebilir); `kip` ∈ `orijinal`, `leet`, `sifir_genislik`, `homoglif`, `harf_bosluklu`; `etiket` `int` 0/1 (`bool` değil); `skor` 0 ile 1 arasında sonlu sayı. `orijinal` kip bulunmalı ve bulunan her kipte iki sınıf da olmalı. Skoru eşiğe eşit ya da büyük olan pozitif sayılır. Bulunan her kip için `{"recall", "fpr", "j", "j_dusus"}`: `j = recall − fpr`, `j_dusus = orijinal j − bu kipin j'si`. `en_zayif`: j'si en düşük kip; eşitlikte yukarıdaki kip sırasında önce gelen. `{"kipler", "en_zayif"}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-32")
```

```starter
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def bozulma_raporu(kayitlar,esik):
    out={}
    for kip in sorted({k["kip"] for k in kayitlar}):
        poz=[k for k in kayitlar if k["kip"]==kip and k["etiket"]==1]
        neg=[k for k in kayitlar if k["kip"]==kip and k["etiket"]==0]
        r=sum(k["skor"]>=esik for k in poz)/len(poz);f=sum(k["skor"]>=esik for k in neg)/len(neg)
        out[kip]={"recall":r,"fpr":f,"j":r-f}
    for kip in out:out[kip]["j_dusus"]=out["orijinal"]["recall"]-out[kip]["recall"]
    return {"kipler":out,"en_zayif":min(out,key=lambda k:out[k]["recall"])}

from ai_savunma_veri import json_yukle
v=json_yukle("veri/siniflandirici.json")["bozulma"]
r=bozulma_raporu(v["kayitlar"],v["esik"])
for kip,x in r["kipler"].items():print(kip,x)
print("en zayıf:",r["en_zayif"])
```
```test
def sinama3(f):
    import copy
    try:
        y=lambda a,b:isinstance(a,(int,float)) and not isinstance(a,bool) and abs(a-b)<=1e-9
        def k(i,kip,e,s):return {"id":i,"kip":kip,"etiket":e,"skor":s}
        def grup(kip,p1,p2,n1,n2):return [k("a",kip,1,p1),k("b",kip,1,p2),k("c",kip,0,n1),k("d",kip,0,n2)]
        L=grup("orijinal",0.9,0.5,0.1,0.2)+grup("leet",0.9,0.9,0.9,0.6)+grup("homoglif",0.1,0.6,0.1,0.1)+grup("sifir_genislik",0.9,0.5,0.1,0.2)
        old=copy.deepcopy(L);r=f(L,0.5)
        if L!=old or set(r)!={"kipler","en_zayif"} or set(r["kipler"])!={"orijinal","leet","homoglif","sifir_genislik"} or r["en_zayif"]!="leet":return False
        bek={"orijinal":(1,0,1,0),"leet":(1,1,0,1),"homoglif":(0.5,0,0.5,0.5),"sifir_genislik":(1,0,1,0)}
        for kip,(a,b,c,d) in bek.items():
            x=r["kipler"][kip]
            if set(x)!={"recall","fpr","j","j_dusus"} or not (y(x["recall"],a) and y(x["fpr"],b) and y(x["j"],c) and y(x["j_dusus"],d)):return False
        if f(list(reversed(L)),0.5)!=r:return False
        r2=f(grup("orijinal",0.9,0.1,0.9,0.1)+grup("harf_bosluklu",0.9,0.9,0.9,0.9)+grup("leet",0.1,0.1,0.1,0.1),0.5)
        if r2["en_zayif"]!="orijinal" or not y(r2["kipler"]["harf_bosluklu"]["j_dusus"],0.0):return False
        r3=f(grup("orijinal",0.9,0.9,0.1,0.1)+grup("harf_bosluklu",0.9,0.1,0.9,0.1)+grup("homoglif",0.9,0.9,0.9,0.9),0.5)
        if r3["en_zayif"]!="homoglif" or set(r3["kipler"])!={"orijinal","harf_bosluklu","homoglif"}:return False
        if f(grup("orijinal",0.3,0.3,0.0,0.0),0.3)["kipler"]["orijinal"]["recall"]!=1.0:return False
        u=f(grup("orijinal",1.0,0.0,0.3,0.0),0.3)["kipler"]["orijinal"]
        if not (y(u["recall"],0.5) and y(u["fpr"],0.5)):return False
        if not y(f(grup("orijinal",1.0,0.0,1.0,0.0),1)["kipler"]["orijinal"]["fpr"],0.5) or not y(f(grup("orijinal",1.0,0.0,1.0,0.0),0)["kipler"]["orijinal"]["recall"],1.0):return False
        from collections import UserString
        for kip in ([],{},None,7,UserString("orijinal")):
            try:
                f([dict(L[0],kip=kip)]+L[1:],0.5)
                return False
            except ValueError:
                pass
        try:
            f([dict(L[0],skor=True)]+L[1:],0.5)
            return False
        except ValueError:
            pass
        for kk,e in [(L,1.5),(L,-0.1),(L,True),(L,float("nan")),(L,None),(None,0.5),(tuple(L),0.5),([],0.5),(L[4:],0.5),(L+[L[0]],0.5),(L[:4]+[k("a","leet",1,0.5)],0.5),
                     (L[:4]+[k("a","yeni",1,0.5),k("c","yeni",0,0.5)],0.5),([dict(L[0],etiket=True)]+L[1:],0.5),([dict(L[0],etiket=2)]+L[1:],0.5),([dict(L[0],skor=1.2)]+L[1:],0.5),
                     ([dict(L[0],skor=None)]+L[1:],0.5),([dict(L[0],skor=-0.5)]+L[1:],0.5),([dict(L[0],id="")]+L[1:],0.5),([dict(L[0],id=123)]+L[1:],0.5),([dict(L[0],ek=1)]+L[1:],0.5),([None]+L,0.5),(L[:2]+L[4:],0.5),(L[2:],0.5)]:
            try:f(kk,e);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama3(bozulma_raporu),"kip başına recall/FPR/J, J düşüşü, en zayıf kip ve geçersiz girdi")
for ad,mut in [("recall'a göre en zayıf",lambda k,e:(lambda r:dict(r,en_zayif=min(r["kipler"],key=lambda q:r["kipler"][q]["recall"])))(bozulma_raporu(k,e))),
               ("eşik dahil değil",lambda k,e:bozulma_raporu(k,min(1.0,e+1e-9)) if isinstance(e,float) and e<1 else bozulma_raporu(k,e)),
               ("j düşüşü ters",lambda k,e:(lambda r:dict(r,kipler={q:dict(x,j_dusus=-x["j_dusus"]) for q,x in r["kipler"].items()}))(bozulma_raporu(k,e)))]:
    ok(not sinama3(mut),"mutant reddedildi: "+ad)
```
```solution
import math
def bozulma_raporu(kayitlar,esik):
    kipler=("orijinal","leet","sifir_genislik","homoglif","harf_bosluklu")
    def sayi(x):return not isinstance(x,bool) and isinstance(x,(int,float)) and math.isfinite(x)
    if not sayi(esik) or not 0<=esik<=1:raise ValueError("eşik")
    if not isinstance(kayitlar,list):raise ValueError("liste")
    g={};gorulen=set()
    for k in kayitlar:
        if not isinstance(k,dict) or set(k)!={"id","kip","etiket","skor"}:raise ValueError("şema")
        if not isinstance(k["kip"],str) or k["kip"] not in kipler:raise ValueError("kip")
        if not isinstance(k["id"],str) or not k["id"] or (k["id"],k["kip"]) in gorulen:raise ValueError("id")
        if k["kip"] not in kipler or type(k["etiket"]) is not int or k["etiket"] not in (0,1):raise ValueError("alan")
        if not sayi(k["skor"]) or not 0<=k["skor"]<=1:raise ValueError("skor")
        gorulen.add((k["id"],k["kip"]))
        x=g.setdefault(k["kip"],{"pozitif":0,"yakalanan":0,"negatif":0,"yanlis_alarm":0})
        if k["etiket"]==1:
            x["pozitif"]+=1
            if k["skor"]>=esik:x["yakalanan"]+=1
        else:
            x["negatif"]+=1
            if k["skor"]>=esik:x["yanlis_alarm"]+=1
    if "orijinal" not in g:raise ValueError("orijinal kip gerekli")
    for x in g.values():
        if not x["pozitif"] or not x["negatif"]:raise ValueError("her kipte iki sınıf gerekli")
    out={}
    for kip in kipler:
        if kip in g:
            r=g[kip]["yakalanan"]/g[kip]["pozitif"];f=g[kip]["yanlis_alarm"]/g[kip]["negatif"]
            out[kip]={"recall":r,"fpr":f,"j":r-f}
    for kip in out:out[kip]["j_dusus"]=out["orijinal"]["j"]-out[kip]["j"]
    en_zayif=min(out,key=lambda k:(out[k]["j"],kipler.index(k)))
    return {"kipler":out,"en_zayif":en_zayif}

from ai_savunma_veri import json_yukle
v=json_yukle("veri/siniflandirici.json")["bozulma"]
r=bozulma_raporu(v["kayitlar"],v["esik"])
for kip,x in r["kipler"].items():print(kip,x)
print("en zayıf:",r["en_zayif"])
```
```hint
Kip başına dört sayaç tut (pozitif, yakalanan, negatif, yanlış alarm). En zayıf kipi recall'a göre değil J'ye göre seç.
```
:::

::: anlat Hata vitrini · "bozulmaya dayanıklı" görünen model
Yazar, finaldekiyle aynı eğitimi önceden koşturdu; kayıt `outputs/yeni-ai-savunma-32/yazar-sondasi.json` dosyasında model ve veri revizyonlarıyla durur:

- `leet`, `homoglif` ve `harf_bosluklu` kiplerinde recall **1.0** çıktı; orijinal metinde 0.9'du. İlk bakışta model bozulmuş saldırıları daha **iyi** yakalıyor gibi görünür. Aynı kiplerde FPR 0.875, 0.839 ve 1.0 oldu: model bozulmuş görünen **her** metne alarm verdi.
- `sifir_genislik` kipinde skorlar orijinalle aynı çıktı. Bunun nedeni modelin dayanıklılığı değil, tokenizer'dır: `bozulma_ornek` alanındaki token listesi orijinalle aynıdır, çünkü tokenizer bu görünmez karakterleri metinden siliyor. Aynı karakter, bu temizliği yapmayan başka bir bileşende (ör. bir anahtar kelime filtresi ya da log araması) metni gerçekten değiştirir.
- Anahtar kelime listesi (`ignore`, `forget`, `vergiss` …) test kümesinde recall 0.35'te kaldı; eğitilen modelin 0.5 eşiğindeki recall'ı 0.817 idi.

Bu çıktılar neden güven vermez? Recall'ın artması, ayırt etme gücünün arttığı anlamına gelmez. "Bozulma etkisiz" sonucu da modelin değil, ön işlemenin bir özelliği olabilir. Kendi cümlenle açıkla. Bu kayıt finalin yerine geçmez; final kendi koşusunu ayrıca üretir ve sayılar değişebilir.
:::

::: anlat Gerçek deney: eğit, eşiği seç, boz
Final, `distilbert/distilbert-base-uncased` modelini ve `deepset/prompt-injections` veri setini sabit revizyonla çevrimdışı yükler; veri dosyalarının sha256 değerlerini doğrular. Eğitim kümesini sınıf oranını koruyarak eğitim ve doğrulama diye ayırır, sabit seed ile 3 tur fine-tune eder. Eşiği doğrulama kümesinde senin `esik_sec` işlevinle aynı kuralla seçer, test kümesinde 0.5 ve seçilen eşikle ölçer, anahtar kelime listesini aynı test kümesinde ölçer, sonra beş bozulma kipini skorlar.

Kabul; üç işlevinin gerçek skorlar üzerinde bağımsız referansla aynı sonucu vermesine, eşiğin test kümesine bakılmadan seçilmesine, veri ve model revizyonlarının doğru olmasına ve eğitimin gerçekten yapılmasına (kayıp düştü, ağırlıklar değişti) bağlıdır. **Modelin ne kadar iyi olduğu kabul şartı değildir**.

**Kanıt dosyasını oku:** Çalıştır ya da Kontrol Et sonunda kanıt dosyasının yolu yazılır. `metrik.test_0.5` ile `metrik.test_secilen` arasında recall ve FPR nasıl değişti? Seçilen eşik neden 0.5'ten bu kadar farklı olabilir? `bozulma.en_zayif` hangi kip; `bozulma_ornek` içindeki token'lar bunu açıklıyor mu? `veri_dosyalari` alanındaki sha256 değerleri neden kanıtta? Cevabını tezgâhta yorum olarak yaz; otomatik test bu serbest açıklamayı puanlamaz.
:::

::: gorev Gerçek deney · DistilBERT ile injection sınıflandırıcısı eğit
Önceki üç görevin `siniflandirma_metrikleri`, `esik_sec` ve `bozulma_raporu` işlevlerini birleştir. Çalıştır gerçek metrikleri ve bozulma raporunu gösterir; Kontrol Et önce üç sözleşmeyi gizli verilerle sınar, sonra gerçek eğitimi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
ortam: gpu
timeout: 300
```
```starter
import ai_lab
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def siniflandirma_metrikleri(etiketler,skorlar,esik):
    tp=sum(1 for e,s in zip(etiketler,skorlar) if e==1 and s>esik)
    fp=sum(1 for e,s in zip(etiketler,skorlar) if e==0 and s>esik)
    fn=etiketler.count(1)-tp;tn=etiketler.count(0)-fp
    p=tp/(tp+fp) if tp+fp else 1.0
    r=tp/(tp+fn)
    f1=2*p*r/(p+r) if p+r else 0.0
    return {"tp":tp,"fp":fp,"tn":tn,"fn":fn,"precision":p,"recall":r,"f1":f1,"fpr":fp/len(etiketler)}

# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def esik_sec(etiketler,skorlar,fpr_siniri):
    en={"esik":0.5,"recall":0.0,"fpr":0.0}
    for t in sorted(set(skorlar)):
        tp=sum(1 for e,s in zip(etiketler,skorlar) if e==1 and s>=t)
        fp=sum(1 for e,s in zip(etiketler,skorlar) if e==0 and s>=t)
        recall,fpr=tp/etiketler.count(1),fp/etiketler.count(0)
        if fpr<fpr_siniri and recall>=en["recall"]:en={"esik":t,"recall":recall,"fpr":fpr}
    return en

# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def bozulma_raporu(kayitlar,esik):
    out={}
    for kip in sorted({k["kip"] for k in kayitlar}):
        poz=[k for k in kayitlar if k["kip"]==kip and k["etiket"]==1]
        neg=[k for k in kayitlar if k["kip"]==kip and k["etiket"]==0]
        r=sum(k["skor"]>=esik for k in poz)/len(poz);f=sum(k["skor"]>=esik for k in neg)/len(neg)
        out[kip]={"recall":r,"fpr":f,"j":r-f}
    for kip in out:out[kip]["j_dusus"]=out["orijinal"]["recall"]-out[kip]["recall"]
    return {"kipler":out,"en_zayif":min(out,key=lambda k:out[k]["recall"])}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_32 as D
    D.goster(siniflandirma_metrikleri,esik_sec,bozulma_raporu)
```
```test
import ai_lab
checks=[]
def kontrol(x,m):checks.append(bool(x));ok(x,m)
issues=ai_lab.kod_denetimi(src,("referans_metrik","referans_esik","referans_bozulma","kanit_yaz"),izin=())
kontrol(not issues,"kopya/yama/dinamik kod yok: "+str(issues))
if issues:stop()
siniflandirma_metrikleri=need("siniflandirma_metrikleri");esik_sec=need("esik_sec");bozulma_raporu=need("bozulma_raporu")
def sinama1(f):
    try:
        y=lambda a,b:isinstance(a,(int,float)) and not isinstance(a,bool) and abs(a-b)<=1e-9
        def esit(r,b):return isinstance(r,dict) and set(r)==set(b) and all((r[k]==b[k] and type(r[k]) is int) if isinstance(b[k],int) else y(r[k],b[k]) for k in b)
        E=[1,1,1,0,0,0,0];S=[0.9,0.5,0.2,0.5,0.1,0.0,0.7]
        if not esit(f(E,S,0.5),{"tp":2,"fp":2,"tn":2,"fn":1,"precision":0.5,"recall":2/3,"f1":4/7,"fpr":0.5}):return False
        if not esit(f(E,S,0.95),{"tp":0,"fp":0,"tn":4,"fn":3,"precision":0.0,"recall":0.0,"f1":0.0,"fpr":0.0}):return False
        if not esit(f(E,S,0),{"tp":3,"fp":4,"tn":0,"fn":0,"precision":3/7,"recall":1.0,"f1":0.6,"fpr":1.0}):return False
        if not esit(f([1,0],[1.0,0.99],1),{"tp":1,"fp":0,"tn":1,"fn":0,"precision":1.0,"recall":1.0,"f1":1.0,"fpr":0.0}):return False
        if not esit(f([0,1,0,0],[0.2,0.6,0.6,0.1],0.6),{"tp":1,"fp":1,"tn":2,"fn":0,"precision":0.5,"recall":1.0,"f1":2/3,"fpr":1/3}):return False
        for a in [([],[],0.5),([1,0],[0.5],0.5),([1,2],[0.5,0.5],0.5),([1,True],[0.5,0.5],0.5),([1,0.0],[0.5,0.5],0.5),([1,1],[0.5,0.5],0.5),([0,0],[0.5,0.5],0.5),
                  ([1,0],[1.1,0.5],0.5),([1,0],[-0.1,0.5],0.5),([1,0],[float("nan"),0.5],0.5),([1,0],[True,0.5],0.5),([1,0],["0.5",0.5],0.5),
                  ([1,0],[0.5,0.5],-0.1),([1,0],[0.5,0.5],1.1),([1,0],[0.5,0.5],True),([1,0],[0.5,0.5],float("nan")),([1,0],[0.5,0.5],None),((1,0),(0.5,0.5),0.5),(None,[0.5],0.5),([1,0],(0.5,0.5),0.5),((1,0),[0.5,0.5],0.5),([1,0,1],[0.5,0.5],0.5),([1,0,2],[0.5,0.5,0.5],0.5),([1,0,True],[0.5,0.5,0.5],0.5),([1,0,1.0],[0.5,0.5,0.5],0.5)]:
            try:f(*a);return False
            except ValueError:pass
        return True
    except Exception:return False
def sinama2(f):
    try:
        y=lambda a,b:isinstance(a,(int,float)) and not isinstance(a,bool) and abs(a-b)<=1e-9
        def esit(r,b):return isinstance(r,dict) and set(r)=={"esik","recall","fpr"} and (r["esik"] is None if b[0] is None else y(r["esik"],b[0])) and y(r["recall"],b[1]) and y(r["fpr"],b[2])
        E=[1,1,1,0,0,0,0,0,0,0,0];S=[0.9,0.8,0.3,0.85,0.4,0.2,0.1,0.1,0.05,0.0,0.3]
        if not esit(f(E,S,0.125),(0.8,2/3,0.125)) or not esit(f(E,S,0.1),(0.9,1/3,0.0)) or not esit(f(E,S,0),(0.9,1/3,0.0)):return False
        if not esit(f(E,S,0.5),(0.3,1.0,0.375)) or not esit(f(E,S,0.99),(0.3,1.0,0.375)):return False
        if not esit(f([1,0],[0.2,0.9],0),(None,0.0,0.0)) or not esit(f([1,0,1],[0.4,0.4,0.9],0.5),(0.9,0.5,0.0)):return False
        if not esit(f(list(reversed(E)),list(reversed(S)),0.125),(0.8,2/3,0.125)):return False
        if not esit(f([1,0],[1.0,0.0],0.0),(1.0,1.0,0.0)):return False
        for a in [(E,S,1),(E,S,1.0),(E,S,-0.01),(E,S,True),(E,S,False),(E,S,float("nan")),(E,S,None),([],[],0.1),([1,1],[0.5,0.5],0.1),([0,0],[0.5,0.5],0.1),([1,0],[0.5],0.1),([1,0],[1.5,0.5],0.1),([1,0],[True,0.5],0.1),([1,0],["0.5",0.5],0.1),([1,2],[0.5,0.5],0.1),((1,0),(0.5,0.5),0.1),([1,0],(0.5,0.5),0.1),((1,0),[0.5,0.5],0.1),([1,0,1],[0.5,0.5],0.1),([1,0,2],[0.5,0.5,0.5],0.1),([1,0,True],[0.5,0.5,0.5],0.1),([1,0],[0.5,-0.5],0.1),([1,0],[0.5,1.5],0.1)]:
            try:f(*a);return False
            except ValueError:pass
        return True
    except Exception:return False
def sinama3(f):
    import copy
    try:
        y=lambda a,b:isinstance(a,(int,float)) and not isinstance(a,bool) and abs(a-b)<=1e-9
        def k(i,kip,e,s):return {"id":i,"kip":kip,"etiket":e,"skor":s}
        def grup(kip,p1,p2,n1,n2):return [k("a",kip,1,p1),k("b",kip,1,p2),k("c",kip,0,n1),k("d",kip,0,n2)]
        L=grup("orijinal",0.9,0.5,0.1,0.2)+grup("leet",0.9,0.9,0.9,0.6)+grup("homoglif",0.1,0.6,0.1,0.1)+grup("sifir_genislik",0.9,0.5,0.1,0.2)
        old=copy.deepcopy(L);r=f(L,0.5)
        if L!=old or set(r)!={"kipler","en_zayif"} or set(r["kipler"])!={"orijinal","leet","homoglif","sifir_genislik"} or r["en_zayif"]!="leet":return False
        bek={"orijinal":(1,0,1,0),"leet":(1,1,0,1),"homoglif":(0.5,0,0.5,0.5),"sifir_genislik":(1,0,1,0)}
        for kip,(a,b,c,d) in bek.items():
            x=r["kipler"][kip]
            if set(x)!={"recall","fpr","j","j_dusus"} or not (y(x["recall"],a) and y(x["fpr"],b) and y(x["j"],c) and y(x["j_dusus"],d)):return False
        if f(list(reversed(L)),0.5)!=r:return False
        r2=f(grup("orijinal",0.9,0.1,0.9,0.1)+grup("harf_bosluklu",0.9,0.9,0.9,0.9)+grup("leet",0.1,0.1,0.1,0.1),0.5)
        if r2["en_zayif"]!="orijinal" or not y(r2["kipler"]["harf_bosluklu"]["j_dusus"],0.0):return False
        r3=f(grup("orijinal",0.9,0.9,0.1,0.1)+grup("harf_bosluklu",0.9,0.1,0.9,0.1)+grup("homoglif",0.9,0.9,0.9,0.9),0.5)
        if r3["en_zayif"]!="homoglif" or set(r3["kipler"])!={"orijinal","harf_bosluklu","homoglif"}:return False
        if f(grup("orijinal",0.3,0.3,0.0,0.0),0.3)["kipler"]["orijinal"]["recall"]!=1.0:return False
        u=f(grup("orijinal",1.0,0.0,0.3,0.0),0.3)["kipler"]["orijinal"]
        if not (y(u["recall"],0.5) and y(u["fpr"],0.5)):return False
        if not y(f(grup("orijinal",1.0,0.0,1.0,0.0),1)["kipler"]["orijinal"]["fpr"],0.5) or not y(f(grup("orijinal",1.0,0.0,1.0,0.0),0)["kipler"]["orijinal"]["recall"],1.0):return False
        from collections import UserString
        for kip in ([],{},None,7,UserString("orijinal")):
            try:
                f([dict(L[0],kip=kip)]+L[1:],0.5)
                return False
            except ValueError:
                pass
        try:
            f([dict(L[0],skor=True)]+L[1:],0.5)
            return False
        except ValueError:
            pass
        for kk,e in [(L,1.5),(L,-0.1),(L,True),(L,float("nan")),(L,None),(None,0.5),(tuple(L),0.5),([],0.5),(L[4:],0.5),(L+[L[0]],0.5),(L[:4]+[k("a","leet",1,0.5)],0.5),
                     (L[:4]+[k("a","yeni",1,0.5),k("c","yeni",0,0.5)],0.5),([dict(L[0],etiket=True)]+L[1:],0.5),([dict(L[0],etiket=2)]+L[1:],0.5),([dict(L[0],skor=1.2)]+L[1:],0.5),
                     ([dict(L[0],skor=None)]+L[1:],0.5),([dict(L[0],skor=-0.5)]+L[1:],0.5),([dict(L[0],id="")]+L[1:],0.5),([dict(L[0],id=123)]+L[1:],0.5),([dict(L[0],ek=1)]+L[1:],0.5),([None]+L,0.5),(L[:2]+L[4:],0.5),(L[2:],0.5)]:
            try:f(kk,e);return False
            except ValueError:pass
        return True
    except Exception:return False
def yakin(a,b):
    if isinstance(a,dict):return isinstance(b,dict) and set(a)==set(b) and all(yakin(a[k],b[k]) for k in a)
    if isinstance(a,list):return isinstance(b,list) and len(a)==len(b) and all(yakin(x,y) for x,y in zip(a,b))
    if isinstance(a,float) or isinstance(b,float):return all(isinstance(x,(int,float)) and not isinstance(x,bool) for x in (a,b)) and abs(a-b)<=1e-9
    return a==b and type(a) is type(b)
kontrol(sinama1(siniflandirma_metrikleri),"sınıflandırma metrikleri")
kontrol(sinama2(esik_sec),"FPR sınırlı eşik seçimi")
kontrol(sinama3(bozulma_raporu),"bozulma raporu")
for ad,mut in [("eşik dahil değil",lambda e,s,t:siniflandirma_metrikleri(e,s,min(1.0,t+1e-9)) if isinstance(t,float) and t<1 else siniflandirma_metrikleri(e,s,t)),
               ("fpr paydası tüm örnekler",lambda e,s,t:(lambda r:dict(r,fpr=r["fp"]/len(e)))(siniflandirma_metrikleri(e,s,t))),
               ("tahmin yokken precision 1",lambda e,s,t:(lambda r:dict(r,precision=1.0) if r["tp"]+r["fp"]==0 else r)(siniflandirma_metrikleri(e,s,t)))]:
    kontrol(not sinama1(mut),"mutant reddedildi: "+ad)
def _dusuk(e,s,p):
    r=esik_sec(e,s,p)
    if r["esik"] is None:return r
    def oran(t,sinif):return sum(1 for a,b in zip(e,s) if a==sinif and b>=t)/e.count(sinif)
    t=min(t for t in set(s) if oran(t,1)==r["recall"] and oran(t,0)<=p)
    return {"esik":t,"recall":r["recall"],"fpr":oran(t,0)}
for ad,mut in [("FPR sınırı dahil değil",lambda e,s,p:esik_sec(e,s,p-1e-12) if isinstance(p,float) and p>0 else esik_sec(e,s,p)),
               ("uygun eşik yoksa 0.5",lambda e,s,p:(lambda r:r if r["esik"] is not None else {"esik":0.5,"recall":0.0,"fpr":0.0})(esik_sec(e,s,p))),
               ("eşitlikte düşük eşik",_dusuk)]:
    kontrol(not sinama2(mut),"mutant reddedildi: "+ad)
for ad,mut in [("recall'a göre en zayıf",lambda k,e:(lambda r:dict(r,en_zayif=min(r["kipler"],key=lambda q:r["kipler"][q]["recall"])))(bozulma_raporu(k,e))),
               ("eşik dahil değil",lambda k,e:bozulma_raporu(k,min(1.0,e+1e-9)) if isinstance(e,float) and e<1 else bozulma_raporu(k,e)),
               ("j düşüşü ters",lambda k,e:(lambda r:dict(r,kipler={q:dict(x,j_dusus=-x["j_dusus"]) for q,x in r["kipler"].items()}))(bozulma_raporu(k,e)))]:
    kontrol(not sinama3(mut),"mutant reddedildi: "+ad)
if not all(checks):stop()
from sandbox import ai_gercek_ai_savunma_32 as D
try:r=D.deney(siniflandirma_metrikleri,esik_sec,bozulma_raporu)
except ai_lab.GercekLabYok as e:
    kontrol(False,"gerçek deney yok: "+str(e));stop()
kontrol(yakin(r["metrik"],r["metrik_referans"]),"gerçek skorlarda metrikler referansla aynı (test 0.5, test seçilen eşik, anahtar kelime, doğrulama)")
kontrol(yakin(r["esik"],r["esik_referans"]),"doğrulama kümesinde seçilen eşik referansla aynı")
kontrol(yakin(r["bozulma"],r["bozulma_referans"]),"gerçek bozulma raporu referansla aynı")
B=r["boyut"]
kontrol(B["egitim"]+B["dogrulama"]==546 and B["test"]==116 and not set(r["dogrulama_idleri"])&set(r["egitim_idleri"]) and all(i.startswith("test-") for i in r["test_idleri"]),"eşik test kümesinde değil, eğitimden ayrılan doğrulama kümesinde seçildi")
kontrol({a:x["sha256"] for a,x in r["veri_dosyalari"].items()}==D.VERI_SHA and r["veri_revizyon"]==D.VERI_REV and r["revizyon"]==D.REV,"veri dosyaları ve model sabit revizyonla, hash'leri doğru")
K=[k["kayip"] for k in r["kayip"]];n=max(1,len(K)//6)
kontrol(len(K)>=30 and sum(K[-n:])/n<sum(K[:n])/n and r["agirlik_hash"][0]!=r["agirlik_hash"][1],"model gerçekten eğitildi (kayıp düştü, ağırlıklar değişti)")
kontrol(len(r["bozulma_kayit"])==5*116 and len(r["test_skor"]["skor"])==116,"beş kip × 116 test metni gerçekten skorlandı")
ai_lab.kanit_yaz("savunma32-kabul",{"kaynak":"gercek","kabul":all(checks),"ders":"ai-savunma-32","deney":r})
```
```solution
import ai_lab
import math
def siniflandirma_metrikleri(etiketler,skorlar,esik):
    def sayi(x):return not isinstance(x,bool) and isinstance(x,(int,float)) and math.isfinite(x)
    if not isinstance(etiketler,list) or not isinstance(skorlar,list) or not etiketler or len(etiketler)!=len(skorlar):raise ValueError("liste")
    for e in etiketler:
        if type(e) is not int or e not in (0,1):raise ValueError("etiket")
    for s in skorlar:
        if not sayi(s) or not 0<=s<=1:raise ValueError("skor")
    if 0 not in etiketler or 1 not in etiketler:raise ValueError("iki sınıf gerekli")
    if not sayi(esik) or not 0<=esik<=1:raise ValueError("eşik")
    tp=fp=0
    for e,s in zip(etiketler,skorlar):
        if s>=esik:
            if e==1:tp+=1
            else:fp+=1
    fn=etiketler.count(1)-tp;tn=etiketler.count(0)-fp
    p=tp/(tp+fp) if tp+fp else 0.0
    r=tp/(tp+fn)
    f1=2*p*r/(p+r) if p+r else 0.0
    return {"tp":tp,"fp":fp,"tn":tn,"fn":fn,"precision":p,"recall":r,"f1":f1,"fpr":fp/(fp+tn)}

def esik_sec(etiketler,skorlar,fpr_siniri):
    def sayi(x):return not isinstance(x,bool) and isinstance(x,(int,float)) and math.isfinite(x)
    if not isinstance(etiketler,list) or not isinstance(skorlar,list) or not etiketler or len(etiketler)!=len(skorlar):raise ValueError("liste")
    for e in etiketler:
        if type(e) is not int or e not in (0,1):raise ValueError("etiket")
    for s in skorlar:
        if not sayi(s) or not 0<=s<=1:raise ValueError("skor")
    if 0 not in etiketler or 1 not in etiketler:raise ValueError("iki sınıf gerekli")
    if not sayi(fpr_siniri) or not 0<=fpr_siniri<1:raise ValueError("fpr")
    pozitif=etiketler.count(1);negatif=etiketler.count(0);en=None
    for t in sorted(set(skorlar),reverse=True):
        tp=sum(1 for e,s in zip(etiketler,skorlar) if e==1 and s>=t)
        fp=sum(1 for e,s in zip(etiketler,skorlar) if e==0 and s>=t)
        recall,fpr=tp/pozitif,fp/negatif
        # Eşikler büyükten küçüğe gezilir; eşit recall'da ilk bulunan (daha yüksek eşik) kalır.
        if fpr<=fpr_siniri and (en is None or recall>en["recall"]):en={"esik":t,"recall":recall,"fpr":fpr}
    return en if en is not None else {"esik":None,"recall":0.0,"fpr":0.0}

def bozulma_raporu(kayitlar,esik):
    kipler=("orijinal","leet","sifir_genislik","homoglif","harf_bosluklu")
    def sayi(x):return not isinstance(x,bool) and isinstance(x,(int,float)) and math.isfinite(x)
    if not sayi(esik) or not 0<=esik<=1:raise ValueError("eşik")
    if not isinstance(kayitlar,list):raise ValueError("liste")
    g={};gorulen=set()
    for k in kayitlar:
        if not isinstance(k,dict) or set(k)!={"id","kip","etiket","skor"}:raise ValueError("şema")
        if not isinstance(k["kip"],str) or k["kip"] not in kipler:raise ValueError("kip")
        if not isinstance(k["id"],str) or not k["id"] or (k["id"],k["kip"]) in gorulen:raise ValueError("id")
        if k["kip"] not in kipler or type(k["etiket"]) is not int or k["etiket"] not in (0,1):raise ValueError("alan")
        if not sayi(k["skor"]) or not 0<=k["skor"]<=1:raise ValueError("skor")
        gorulen.add((k["id"],k["kip"]))
        x=g.setdefault(k["kip"],{"pozitif":0,"yakalanan":0,"negatif":0,"yanlis_alarm":0})
        if k["etiket"]==1:
            x["pozitif"]+=1
            if k["skor"]>=esik:x["yakalanan"]+=1
        else:
            x["negatif"]+=1
            if k["skor"]>=esik:x["yanlis_alarm"]+=1
    if "orijinal" not in g:raise ValueError("orijinal kip gerekli")
    for x in g.values():
        if not x["pozitif"] or not x["negatif"]:raise ValueError("her kipte iki sınıf gerekli")
    out={}
    for kip in kipler:
        if kip in g:
            r=g[kip]["yakalanan"]/g[kip]["pozitif"];f=g[kip]["yanlis_alarm"]/g[kip]["negatif"]
            out[kip]={"recall":r,"fpr":f,"j":r-f}
    for kip in out:out[kip]["j_dusus"]=out["orijinal"]["j"]-out[kip]["j"]
    en_zayif=min(out,key=lambda k:(out[k]["j"],kipler.index(k)))
    return {"kipler":out,"en_zayif":en_zayif}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_32 as D
    D.goster(siniflandirma_metrikleri,esik_sec,bozulma_raporu)
```
```hint
Üç işlevi aynen birleştir. Raporu okurken recall'ı FPR'den ayrı yorumlama.
```
:::

::: anlat Sınır
Bu ders tek bir küçük açık veri setiyle (546 + 116 örnek, İngilizce ve Almanca, tartışmalı etiketler içerir), tek eğitim koşusu ve beş basit bozulmayla bir DistilBERT sınıflandırıcısını ölçer; gerçek trafikteki dağılımda, başka dillerde ya da sınıflandırıcıyı hedefleyen uyarlanabilir bir saldırgana karşı nasıl davranacağını gösteremez.
:::


::: anlat Bunu iki dakikada nasıl anlatırsın?
Bir classifier skoru ile engelleme kararı farklıdır. TP/FP/FN/TN sayımlarından precision, recall ve FPR paydalarını türet. FPR tavanı altında recall seçimi bir ürün kısıtıdır; eşiği ölçümden sonra başarıya göre değiştirme. Ardından aynı örneklerin bozulmuş sürümlerinde recall değişimini hesapla. DistilBERT eğitiminin gerçek olması küçük, dil kapsamı sınırlı veri setinin üretim genellemesini kanıtlamaz.

Önkoşul ve yol köprüsü: ai-savunma-07 tespit; ai-guvence-10 değerlendirme.

| Yaygın yanlış | Mekanizma ve sınır |
|---|---|
| Doğruluk yüksekse guardrail güvenlidir | Sınıf dengesizliği ve meşru istek FPR’ı ayrı ölçülür |

Dinleyiciye sor: Savunma güvenlik metriğini iyileştirirken meşru kullanıma ne kaybettirebilir? Ham çıktı ve ölçüm paydalarıyla cevapla.
:::


::: anlat Birincil kaynak ve deney sınırı
[Hugging Face DistilBERT](https://huggingface.co/docs/transformers/model_doc/distilbert): Model/sınıflandırma arabirimi için araç referansı; veri ve eğitim ayarları gerçek kanıtta ayrı saklanır. Çalışan sürüm ve gerçek sonuç kanıtta kayıtlıdır.
:::
