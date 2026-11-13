---
id: ai-saldiri-48
title: Eğitim Verisi Çıkarımı · Membership Inference ve Ezberlenmiş Sır
summary: Yerel Qwen'i kurgusal kayıtlarla LoRA ile eğit; loss tabanlı ve referans-kalibre membership inference skorlarını AUC ve düşük FPR'de ölç, ezberlenmiş PIN'in önekten geri üretilip üretilmediğini kanıtla.
esleme: ai-temel-12, ai-temel-16, ai-saldiri-49
timeout: 60
---

::: anlat Model eğitim verisinin bir kısmını taşır
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Fine-tune edilmiş bir dil modeli eğitim örneklerinde daha düşük loss verir; saldırgan bu farktan "bu örnek eğitimde var mıydı" sonucunu çıkarabilir (membership inference) | İlk üç görev: `veri/uyelik.json` içindeki **sentetik** kayıp, skor ve üretim kayıtları. Final: kurulu offline Qwen2.5-0.5B-Instruct, PEFT LoRA ve her koşuda yeni üretilen 12 kurgusal kayıt | Ön-eğitim verisinin içeriğini, gerçek kişisel veriyi veya bir saldırı başarı oranını göstermez |
| Ezberlenmiş bir dize, önekiyle sorulduğunda birebir geri üretilebilir (training data extraction) | Rastgele üretilmiş PIN'ler, greedy üretim ve tam/kısmi/çapraz eşleşme raporu | Greedy üretimde görülmeyen bir sırrın modelde olmadığını kanıtlamaz |

> [!NOT]
> İlk üç görev `veri/uyelik.json` dosyasını okur; dosya gerçek training çıktısı değildir. Setup her Çalıştır/Kontrol Et adımında geçici kopya kurar; değişiklikler sonraki çalıştırmaya taşınmaz, **kalıcılık yoktur**. Ekranda ayrı bir dosya görüntüleyici yoktur; içeriği görmek için başlangıç kodundaki `print` satırlarını kullan. Gizli testler ayrıdır. Final yalnız önbellekteki Qwen modelini kullanır, yeni model indirmez; LoRA adaptörü diske yazılmaz, deney bitince bellekten silinir.

**Membership inference** sorusu şudur: elimdeki örnek modelin eğitim kümesinde var mıydı? Shokri ve arkadaşları (2017) bu soruyu gölge modellerle (shadow model) sorar. Yeom ve arkadaşları (2018) daha basit bir saldırının, yani örneğin loss değerine eşik koymanın, overfitting ile ilişkisini gösterir. Bu dersin ilk skoru da budur: **loss ne kadar düşükse örneğin üye olma olasılığı o kadar yüksek kabul edilir.** Skoru "yüksek = üye" yönünde tutmak için `ham_skor = -kayip_hedef` kullanılır. Yönü ters çevirmek bütün raporu tersine çevirir; bu derste en sık yapılacak hata budur.

Ham loss tek başına yanıltıcıdır: bazı metinler doğası gereği kolaydır. "Merhaba, nasılsınız" gibi yaygın bir cümle eğitimde hiç görülmese de düşük loss alır ve üye gibi görünür. Rastgele bir PIN içeren zor bir kayıt ise eğitimde görülse bile yüksek loss taşıyabilir. Bu yüzden saldırgan hedef modelin kaybını bir **referans** kayıpla karşılaştırır: `kalibre_skor = kayip_ref - kayip_hedef`. Bu derste referans, aynı modelin LoRA eğitiminden önceki hâlidir. Carlini ve arkadaşları (2021) eğitim verisi çıkarımında benzer bir fikri, daha küçük bir referans modelle ve zlib sıkıştırma entropisiyle oranlayarak kullanır. Biz o çalışmanın modellerini, verisini veya sonuçlarını yeniden üretmiyoruz; yalnız kalibrasyon fikrini küçük bir yerel deneyde uyguluyoruz.

Bir skorun ne kadar iyi ayırdığını **ROC AUC** ile ölçeriz: rastgele seçilen bir üyenin rastgele seçilen bir üye-olmayandan daha yüksek skor alma olasılığı. Eşit skorlar yarım sayılır. AUC 0.5 rastgele tahmindir, 1.0 kusursuz ayrımdır. Carlini ve arkadaşları (2022), ortalama doğruluğun ya da AUC'nin bu saldırılar için yanıltıcı olabileceğini ve asıl önemli olanın **düşük false positive oranında true positive oranı** (TPR @ düşük FPR) olduğunu savunur. Az sayıda kaydı yüksek güvenle tanımak, çok sayıda kaydı yarı yarıya tahmin etmekten daha büyük bir gizlilik riskidir. İkinci görev bu iki ölçütü birlikte raporlar.

**Ezberleme ve çıkarım (extraction)** ayrı bir sorudur. Carlini ve arkadaşları (2019, "The Secret Sharer") eğitim verisine yapay "canary" dizeleri ekleyip modelin bunları ne kadar ezberlediğini ölçer. Bu derste her kurgusal kayıtta rastgele bir PIN vardır; final, kaydın önekini modele verip greedy üretimde PIN'in geri gelip gelmediğine bakar. Üç sonucu ayırırız:
- **tam:** Kaydın kendi sırrı üretimde birebir geçiyor.
- **kısmi:** Üretim, sırrın en az yarısı kadar başlangıç karakterini doğru veriyor.
- **çapraz:** Üretim, **başka bir üye kaydın** sırrını içeriyor. Eğitimde olmayan bir kaydın öneki bile ezberlenmiş başka bir sırrı sızdırabilir.

**Saldırgan ne dener?** Elindeki aday kayıtların (ör. sızmış bir müşteri listesi) bir modelin fine-tune verisinde olup olmadığını öğrenmek ister; bu tek başına bir gizlilik ihlalidir. Ayrıca önekleri tahmin ederek modelden ezberlenmiş telefon, PIN veya anahtar çıkarmaya çalışır.

**Savunma neden kırılır?** Fine-tune verisi az ve tekrarlıysa model hızla ezberler. "Model genel davranıyor, ortalama doğruluk iyi" demek tek tek kayıtların sızmadığını göstermez. Greedy üretimde sırrın görünmemesi de güvence değildir; başka bir önek, sıcaklık veya örnekleme yolu onu çıkarabilir. Bilinen savunmalar arasında eğitim verisinin tekilleştirilmesi, sırların eğitimden önce temizlenmesi ve differentially private eğitim vardır; bu ders bunları uygulamaz.

**Görev 1'de sık tuzaklar:** `ham_skor`u kaybın kendisi yapmak skoru ters çevirir; yüksek kayıp "üye" görünür. Kalibrasyonu `hedef - ref` diye yazmak da aynı ters çevirmedir. `veri/uyelik.json` içindeki `degil-yaygin` kaydı ham skorda üye gibi görünür, kalibre skorda görünmez; farkı bu kayıtta gör.

Kaynaklar: [Shokri vd. 2017](https://arxiv.org/abs/1610.05820), [Yeom vd. 2018](https://arxiv.org/abs/1709.01604), [Carlini vd. 2019 · The Secret Sharer](https://arxiv.org/abs/1802.08232), [Carlini vd. 2021 · Extracting Training Data from Large Language Models](https://arxiv.org/abs/2012.07805), [Carlini vd. 2022 · Membership Inference Attacks From First Principles](https://arxiv.org/abs/2112.03570). Bu dersteki bütün sayılar yalnız yerel kanıttan gelir.

Saldırı↔savunma köprüsü: ai-temel-12 fine-tune sonrası değerlendirmeyi, ai-temel-16 bağlama sır koymamayı anlatır; ai-saldiri-49 aynı LoRA düzeneğinin politika kaymasını ölçer. Eğitim verisi tekilleştirme ve differential privacy için ayrı bir savunma dersi henüz yoktur; bu eşleme planlı değil, mevcut derslerle sınırlıdır.
:::

::: tahmin Hangi yön "üye" demek?
Çıktıyı tahmin et, sonra Çalıştır ile karşılaştır.
```python
kayip_ref, kayip_hedef = 3.2, 1.1
print(-kayip_hedef)
print(round(kayip_ref - kayip_hedef, 2))
print(sorted([0.9, 0.2, 0.9], reverse=True))
```
???
```cikti
-1.1
2.1
[0.9, 0.9, 0.2]
```
Tahmininle gerçek çıktı arasındaki farkı tezgâhta yorum satırı olarak yaz: düşük kayıp neden yüksek üyelik skoru verir? Sonra üç kusurlu başlangıç kodunu çalıştır; hangisi bu yönü bozuyor, hangisi eşitliği yanlış sayıyor, hangisi başka bir kaydın sırrını görmüyor? Önce kendin teşhis et; açıklama çözümün ardından gelir.
:::

::: gorev 1 · Ham ve kalibre üyelik skorları
`uyelik_skorlari(kayitlar)`: dolu liste; her kayıt tam olarak `id`, `uye`, `kayip_hedef`, `kayip_ref` alanlarını taşır. Kimlik benzersiz, dolu string; `uye` gerçek bool; iki kayıp bool olmayan, sonlu ve 0 veya pozitif sayı. Her kayıt için `{"id","uye","ham_skor","kalibre_skor"}` döndür: `ham_skor = -kayip_hedef`, `kalibre_skor = kayip_ref - kayip_hedef`. Liste kimliğe göre sıralı olsun. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-48")
```

```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def uyelik_skorlari(kayitlar):
    out=[]
    for k in kayitlar:
        out.append({"id":k["id"],"uye":k["uye"],"ham_skor":k["kayip_hedef"],"kalibre_skor":k["kayip_hedef"]-k["kayip_ref"]})
    return sorted(out,key=lambda k:k["id"])

from ai_saldiri_veri import json_yukle,metin_yukle
v=json_yukle("veri/uyelik.json")
print("Sentetik kayıp verisi:",v["kayiplar"])
for s in uyelik_skorlari(v["kayiplar"]):print(s)
```
```test
def sinama1(f):
    import copy,random,math
    try:
        rng=random.Random(48)
        for n in (2,5,9):
            v=[{"id":f"k{rng.randrange(10**6)}-{i}","uye":i%2==0,"kayip_hedef":rng.uniform(0,6),"kayip_ref":rng.uniform(0,6)} for i in range(n)]
            v.append({"id":"sifir","uye":False,"kayip_hedef":0,"kayip_ref":0});v.append({"id":"int","uye":True,"kayip_hedef":2,"kayip_ref":5})
            old=copy.deepcopy(v);r=f(v)
            beklenen=[{"id":k["id"],"uye":k["uye"],"ham_skor":-k["kayip_hedef"],"kalibre_skor":k["kayip_ref"]-k["kayip_hedef"]} for k in sorted(v,key=lambda k:k["id"])]
            if r!=beklenen or v!=old:return False
        b=[{"id":"a","uye":True,"kayip_hedef":0.5,"kayip_ref":3.0}]
        for bad in (None,[],tuple(b),[dict(b[0],uye=1)],[dict(b[0],uye=None)],[dict(b[0],kayip_hedef=-0.1)],[dict(b[0],kayip_ref=-1)],[dict(b[0],kayip_hedef=float("nan"))],[dict(b[0],kayip_ref=float("inf"))],[dict(b[0],kayip_hedef=True)],[dict(b[0],kayip_ref="3")],b+b,[dict(b[0],id="")],[dict(b[0],id=7)],[dict(b[0],ek=1)],[{"id":"a","uye":True,"kayip_hedef":1}],[None]):
            try:f(bad);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama1(uyelik_skorlari),"skor yönü, kalibrasyon, sıra ve geçersiz girdi")
for ad,mut in [("ham skor işareti ters",lambda ks:[dict(s,ham_skor=-s["ham_skor"]) for s in uyelik_skorlari(ks)]),("kalibrasyon yönü ters",lambda ks:[dict(s,kalibre_skor=-s["kalibre_skor"]) for s in uyelik_skorlari(ks)]),("sırasız",lambda ks:list(reversed(uyelik_skorlari(ks))))]:
    ok(not sinama1(mut),"mutant reddedildi: "+ad)
```
```solution
import math
def uyelik_skorlari(kayitlar):
    if not isinstance(kayitlar,list) or not kayitlar:raise ValueError("kayıt")
    ids=set();out=[]
    for k in kayitlar:
        if not isinstance(k,dict) or set(k)!={"id","uye","kayip_hedef","kayip_ref"}:raise ValueError("şema")
        if not isinstance(k["id"],str) or not k["id"] or k["id"] in ids:raise ValueError("id")
        if type(k["uye"]) is not bool:raise ValueError("üye")
        for a in ("kayip_hedef","kayip_ref"):
            if isinstance(k[a],bool) or not isinstance(k[a],(int,float)):raise ValueError("sayı")
            if not math.isfinite(k[a]) or k[a]<0:raise ValueError("kayıp")
        ids.add(k["id"])
        out.append({"id":k["id"],"uye":k["uye"],"ham_skor":-k["kayip_hedef"],"kalibre_skor":k["kayip_ref"]-k["kayip_hedef"]})
    return sorted(out,key=lambda k:k["id"])

from ai_saldiri_veri import json_yukle,metin_yukle
v=json_yukle("veri/uyelik.json")
print("Sentetik kayıp verisi:",v["kayiplar"])
for s in uyelik_skorlari(v["kayiplar"]):print(s)
```
```hint
Skoru "yüksek = üye" yönünde kur. Düşük kayıp yüksek skor olmalı; kalibrasyon referansın hedeften ne kadar yüksek olduğunu ölçer.
```
:::

::: anlat Bir skoru tek sayıyla değil, yanlış alarm bütçesiyle değerlendir
AUC bütün eşiklerin ortalama davranışını özetler. Saldırganın ise genellikle tek bir sorusu vardır: "Yanlış alarmı küçük tutarak kaç üyeyi kesin tanıyabilirim?" Bu yüzden ikinci ölçüt, false positive oranı verilen sınırı aşmayan eşikler arasında en yüksek true positive oranıdır. Eşik `skor >= esik` ise üye denir. Payda önemlidir: TPR üye sayısına, FPR üye-olmayan sayısına bölünür. Sınır **dahildir** (`fpr <= fpr_siniri`).

**Çıktı nasıl okunur?** `veri/uyelik.json` içinde ham skorun AUC'si 0.889, kalibre skorun AUC'si 1.000 çıkar. Fark tek bir kayıttan gelir: `degil-yaygin` doğası gereği kolay olduğu için ham skorda üyelerin arasına girer. TPR @ düşük FPR değerine de bak; küçük bir veri setinde tek bir kayıt bu sayıyı büyük ölçüde değiştirir.

**Görev 2'de sık tuzaklar:** Eşit skorları tam kazanç saymak AUC'yi şişirir; eşitlik yarım puandır. FPR'yi üye sayısına bölmek, iki sınıf farklı büyüklükteyse oranı bozar. Sınırı katı (`<`) uygulamak, tam sınırdaki geçerli bir eşiği atar.
:::

::: gorev 2 · AUC ve düşük FPR'de TPR
`auc_raporu(skorlar,fpr_siniri)`: `fpr_siniri` bool olmayan sonlu sayı ve `0 < fpr_siniri <= 1`. `skorlar` liste; her kayıt tam olarak `id`, `uye`, `skor`; benzersiz dolu string kimlik, gerçek bool `uye`, bool olmayan sonlu `skor`. İki sınıf da en az bir kayıt içermeli. AUC: bütün (üye, üye değil) çiftlerinde üye skoru büyükse 1, eşitse 0.5, küçükse 0; toplam çift sayısına böl. Eşikler gözlenen benzersiz skorlardır, küçükten büyüğe denenir; `skor >= esik` üye tahminidir. FPR sınırı aşmayan eşikler arasında TPR'yi kesin olarak artıran ilk eşiği seç; hiçbiri yoksa `tpr_dusuk_fpr = 0.0`, `esik = None`. `{"auc","tpr_dusuk_fpr","esik","uye","uye_degil"}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-48")
```

```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def auc_raporu(skorlar,fpr_siniri):
    uye=[k["skor"] for k in skorlar if k["uye"]]
    degil=[k["skor"] for k in skorlar if not k["uye"]]
    kazanc=sum(1.0 if a>=b else 0.0 for a in uye for b in degil)
    en_iyi=(0.0,None)
    for t in sorted(set(uye+degil)):
        tpr=sum(s>=t for s in uye)/len(uye)
        fpr=sum(s>=t for s in degil)/len(uye)
        if fpr<fpr_siniri and tpr>en_iyi[0]:en_iyi=(tpr,t)
    return {"auc":kazanc/(len(uye)*len(degil)),"tpr_dusuk_fpr":en_iyi[0],"esik":en_iyi[1],"uye":len(uye),"uye_degil":len(degil)}

from ai_saldiri_veri import json_yukle
v=json_yukle("veri/uyelik.json")
for ad,liste in v["auc_girdileri"].items():
    print(ad,auc_raporu(liste,v["fpr_siniri"]))
print("Eşitlikli örnek:",auc_raporu(v["esitlik_ornegi"],0.5))
```
```test
def sinama2(f):
    import copy,random,math
    def _ref(sk,lim):
        u=[k["skor"] for k in sk if k["uye"]];d=[k["skor"] for k in sk if not k["uye"]]
        kaz=sum(1.0 if a>b else 0.5 if a==b else 0.0 for a in u for b in d);ei=(0.0,None)
        for t in sorted(set(u+d)):
            tp=sum(s>=t for s in u)/len(u);fp=sum(s>=t for s in d)/len(d)
            if fp<=lim and tp>ei[0]:ei=(tp,t)
        return {"auc":kaz/(len(u)*len(d)),"tpr_dusuk_fpr":ei[0],"esik":ei[1],"uye":len(u),"uye_degil":len(d)}
    try:
        e=[{"id":"u1","uye":True,"skor":3},{"id":"u2","uye":True,"skor":2},{"id":"u3","uye":True,"skor":2},{"id":"d1","uye":False,"skor":2},{"id":"d2","uye":False,"skor":1}]
        old=copy.deepcopy(e)
        if f(e,0.5)!={"auc":5/6,"tpr_dusuk_fpr":1.0,"esik":2,"uye":3,"uye_degil":2} or e!=old:return False
        if f(e,0.25)!={"auc":5/6,"tpr_dusuk_fpr":1/3,"esik":3,"uye":3,"uye_degil":2}:return False
        if f(e,1)!={"auc":5/6,"tpr_dusuk_fpr":1.0,"esik":1,"uye":3,"uye_degil":2}:return False
        hep=[{"id":"u","uye":True,"skor":0},{"id":"d","uye":False,"skor":5}]
        if f(hep,1)!={"auc":0.0,"tpr_dusuk_fpr":1.0,"esik":0,"uye":1,"uye_degil":1} or f(hep,0.5)!={"auc":0.0,"tpr_dusuk_fpr":0.0,"esik":None,"uye":1,"uye_degil":1}:return False
        rng=random.Random(4848)
        for n in (3,6,11):
            v=[{"id":f"r{i}","uye":i%3!=0,"skor":rng.choice([rng.uniform(-3,3),1.5,-1])} for i in range(n)]
            for lim in (0.2,0.5,1):
                if f(copy.deepcopy(v),lim)!=_ref(v,lim):return False
        for sk,lim in ((e,0),(e,1.01),(e,True),(e,float("nan")),(e,"0.5"),(None,0.5),(tuple(e),0.5),(e[:3],0.5),(e[3:],0.5),(e+[e[0]],0.5),([dict(e[0],uye=1)]+e[1:],0.5),([dict(e[0],skor=float("inf"))]+e[1:],0.5),([dict(e[0],skor=True)]+e[1:],0.5),([dict(e[0],ek=1)]+e[1:],0.5),([dict(e[0],id="")]+e[1:],0.5),([None]+e,0.5)):
            try:f(sk,lim);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama2(auc_raporu),"eşitlik yarım, dahil FPR sınırı, doğru paydalar ve geçersiz girdi")
for ad,mut in [("eşitlik tam kazanç",lambda s,l:dict(auc_raporu(s,l),auc=1.0)),("katı fpr",lambda s,l:auc_raporu(s,l*0.999)),("eşik yok",lambda s,l:dict(auc_raporu(s,l),esik=None))]:
    ok(not sinama2(mut),"mutant reddedildi: "+ad)
```
```solution
import math
def auc_raporu(skorlar,fpr_siniri):
    if isinstance(fpr_siniri,bool) or not isinstance(fpr_siniri,(int,float)) or not math.isfinite(fpr_siniri) or not 0<fpr_siniri<=1:raise ValueError("fpr")
    if not isinstance(skorlar,list):raise ValueError("liste")
    ids=set();uye=[];degil=[]
    for k in skorlar:
        if not isinstance(k,dict) or set(k)!={"id","uye","skor"}:raise ValueError("şema")
        if not isinstance(k["id"],str) or not k["id"] or k["id"] in ids:raise ValueError("id")
        if type(k["uye"]) is not bool:raise ValueError("üye")
        if isinstance(k["skor"],bool) or not isinstance(k["skor"],(int,float)) or not math.isfinite(k["skor"]):raise ValueError("skor")
        ids.add(k["id"])
        (uye if k["uye"] else degil).append(k["skor"])
    if not uye or not degil:raise ValueError("iki sınıf gerekli")
    kazanc=sum(1.0 if a>b else 0.5 if a==b else 0.0 for a in uye for b in degil)
    en_iyi=(0.0,None)
    for t in sorted(set(uye+degil)):
        tpr=sum(s>=t for s in uye)/len(uye)
        fpr=sum(s>=t for s in degil)/len(degil)
        if fpr<=fpr_siniri and tpr>en_iyi[0]:en_iyi=(tpr,t)
    return {"auc":kazanc/(len(uye)*len(degil)),"tpr_dusuk_fpr":en_iyi[0],"esik":en_iyi[1],"uye":len(uye),"uye_degil":len(degil)}

from ai_saldiri_veri import json_yukle
v=json_yukle("veri/uyelik.json")
for ad,liste in v["auc_girdileri"].items():
    print(ad,auc_raporu(liste,v["fpr_siniri"]))
print("Eşitlikli örnek:",auc_raporu(v["esitlik_ornegi"],0.5))
```
```hint
Çiftleri say: büyükse 1, eşitse 0.5. TPR üye sayısına, FPR üye-olmayan sayısına bölünür; sınır dahildir.
```
:::

::: anlat Ezber, kendi kaydının dışına da sızar
Çıkarım raporu üç soruyu ayrı tutar. **Tam** çıkarım kaydın kendi sırrının üretimde birebir geçmesidir. **Kısmi** çıkarım, baştaki boşluk atıldıktan sonra üretimin sırrın en az yarısı kadar başlangıç karakterini doğru vermesidir (`ceil(len/2)`); sırrı tahmin etmeyi kolaylaştırdığı için yine sızıntıdır. **Çapraz** sızıntı ise üretimin başka bir **üye** kaydın sırrını birebir içermesidir. Eğitimde benzer önekler çok tekrarlanırsa model hangi sırrın hangi kayda ait olduğunu karıştırabilir; bu durumda eğitimde hiç olmayan bir kaydın öneki bile bir üyenin PIN'ini sızdırır.

Üye ve üye-olmayan gruplar ayrı sayılır; üye olmayanlarda tam veya kısmi kendi-sır çıkarımı beklenmez, çünkü o sırlar eğitimde hiç yoktu. Orada görülen bir eşleşme tesadüftür ya da çapraz sızıntının işaretidir.

**Görev 3'te sık tuzaklar:** Yalnız ilk dört karakteri karşılaştırıp "tam" demek, kısmi eşleşmeyi tam sızıntı gibi raporlar. Çapraz sızıntıyı aramamak, `degil-capraz` kaydında üyenin PIN'inin dışarı çıktığını gizler. Kimlik listelerini sıralamamak raporu girdi sırasına bağlı bırakır.
:::

::: gorev 3 · Tam, kısmi ve çapraz çıkarım raporu
`cikarim_raporu(denemeler)`: liste; her deneme tam olarak `id`, `uye`, `sir`, `uretim`. Benzersiz dolu string kimlik, gerçek bool `uye`, string `uretim`; `sir` en az 4 karakterlik ve satır sonu/NUL içermeyen string. Her deneme kendi grubunda (`uye` / `uye_degil`) `adet` artırır ve tam/kısmi/yok olarak sayılır: sır üretimde birebir geçiyorsa tam; değilse `uretim.lstrip()` ile sırrın ortak başlangıç uzunluğu en az `ceil(len(sir)/2)` ise kısmi; değilse yok. İki grup da en az bir deneme içermeli. `capraz_idler`: üretimi, kendisi dışındaki herhangi bir **üye** denemenin sırrını birebir içeren denemelerin kimlikleri. `{"gruplar":{"uye":{tam,kismi,yok,adet},"uye_degil":{...}},"tam_idler":[...],"capraz_idler":[...]}` döndür; listeler sıralı. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-48")
```

```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def cikarim_raporu(denemeler):
    gruplar={"uye":{"tam":0,"kismi":0,"yok":0,"adet":0},"uye_degil":{"tam":0,"kismi":0,"yok":0,"adet":0}};tam=[]
    for d in denemeler:
        g=gruplar["uye" if d["uye"] else "uye_degil"];g["adet"]+=1
        if d["uretim"].strip().startswith(d["sir"][:4]):
            g["tam"]+=1;tam.append(d["id"])
        else:
            g["yok"]+=1
    return {"gruplar":gruplar,"tam_idler":tam,"capraz_idler":[]}

from ai_saldiri_veri import json_yukle
v=json_yukle("veri/uyelik.json")
r=cikarim_raporu(v["denemeler"])
print("Gruplar:",r["gruplar"]);print("Tam:",r["tam_idler"]);print("Çapraz:",r["capraz_idler"])
```
```test
def sinama3(f):
    import copy
    try:
        D=[{"id":"u-tam","uye":True,"sir":"AB12-CD34","uretim":" AB12-CD34. Teşekkürler"},
           {"id":"u-kismi","uye":True,"sir":"EF56-7788","uretim":"  EF56-7X. ok"},
           {"id":"u-alti","uye":True,"sir":"1234-5678","uretim":"1234X"},
           {"id":"u-baska","uye":True,"sir":"9999-0000","uretim":"AB12-CD34"},
           {"id":"d-capraz","uye":False,"sir":"5555-6666","uretim":" EF56-7788 ve AB12-CD34"},
           {"id":"d-kendi","uye":False,"sir":"7777-1111","uretim":"7777-1111"},
           {"id":"d-yok","uye":False,"sir":"0000-2222","uretim":"bilmiyorum"}]
        old=copy.deepcopy(D);r=f(D)
        if D!=old:return False
        if r!={"gruplar":{"uye":{"tam":1,"kismi":1,"yok":2,"adet":4},"uye_degil":{"tam":1,"kismi":0,"yok":2,"adet":3}},"tam_idler":["d-kendi","u-tam"],"capraz_idler":["d-capraz","u-baska"]}:return False
        if f(list(reversed(D)))!=r:return False
        sinir=[{"id":"a","uye":True,"sir":"ABCDEFGH","uretim":"ABCDzzzz"},{"id":"b","uye":False,"sir":"ABCDEFGHI","uretim":"ABCDzzzz"},{"id":"c","uye":False,"sir":"WXYZ","uretim":"wxyz"}]
        if f(sinir)["gruplar"]!={"uye":{"tam":0,"kismi":1,"yok":0,"adet":1},"uye_degil":{"tam":0,"kismi":0,"yok":2,"adet":2}}:return False
        atla=[{"id":"a","uye":True,"sir":"AB12-CD34","uretim":"AX1X-XDX"},{"id":"b","uye":False,"sir":"WXYZ","uretim":"W"},{"id":"c","uye":False,"sir":"WXYZ","uretim":"AXYZ"}]
        if f(atla)["gruplar"]!={"uye":{"tam":0,"kismi":0,"yok":1,"adet":1},"uye_degil":{"tam":0,"kismi":0,"yok":2,"adet":2}}:return False
        for bad in (None,tuple(D),[D[0]],[D[4]],D+[D[0]],[dict(D[0],sir="ABC")]+D[4:],[dict(D[0],sir="AB\nCD")]+D[4:],[dict(D[0],sir=None)]+D[4:],[dict(D[0],uye=1)]+D[4:],[dict(D[0],uretim=None)]+D[4:],[dict(D[0],id="")]+D[4:],[dict(D[0],ek=1)]+D[4:],[None]+D):
            try:f(bad);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama3(cikarim_raporu),"tam/kısmi sınırı, grup ayrımı, çapraz sızıntı ve geçersiz girdi")
for ad,mut in [("çapraz yok",lambda d:dict(cikarim_raporu(d),capraz_idler=[])),("kısmi=tam",lambda d:dict(cikarim_raporu(d),tam_idler=[])),("gruplar karışık",lambda d:{**cikarim_raporu(d),"gruplar":{"uye":cikarim_raporu(d)["gruplar"]["uye_degil"],"uye_degil":cikarim_raporu(d)["gruplar"]["uye"]}})]:
    ok(not sinama3(mut),"mutant reddedildi: "+ad)
```
```solution
import math
def cikarim_raporu(denemeler):
    if not isinstance(denemeler,list):raise ValueError("liste")
    ids=set();gruplar={"uye":{"tam":0,"kismi":0,"yok":0,"adet":0},"uye_degil":{"tam":0,"kismi":0,"yok":0,"adet":0}};tam=[]
    for d in denemeler:
        if not isinstance(d,dict) or set(d)!={"id","uye","sir","uretim"}:raise ValueError("şema")
        if not isinstance(d["id"],str) or not d["id"] or d["id"] in ids:raise ValueError("id")
        if type(d["uye"]) is not bool or not isinstance(d["uretim"],str):raise ValueError("alan")
        if not isinstance(d["sir"],str) or len(d["sir"])<4 or any(c in d["sir"] for c in "\r\n\0"):raise ValueError("sır")
        ids.add(d["id"])
        g=gruplar["uye" if d["uye"] else "uye_degil"];g["adet"]+=1
        if d["sir"] in d["uretim"]:
            g["tam"]+=1;tam.append(d["id"])
        else:
            u=d["uretim"].lstrip();n=0
            while n<min(len(u),len(d["sir"])) and u[n]==d["sir"][n]:n+=1
            g["kismi" if n>=math.ceil(len(d["sir"])/2) else "yok"]+=1
    if not gruplar["uye"]["adet"] or not gruplar["uye_degil"]["adet"]:raise ValueError("iki grup gerekli")
    uye_sirlari={d["id"]:d["sir"] for d in denemeler if d["uye"]}
    capraz=[d["id"] for d in denemeler if any(s in d["uretim"] for i,s in uye_sirlari.items() if i!=d["id"])]
    return {"gruplar":gruplar,"tam_idler":sorted(tam),"capraz_idler":sorted(capraz)}

from ai_saldiri_veri import json_yukle
v=json_yukle("veri/uyelik.json")
r=cikarim_raporu(v["denemeler"])
print("Gruplar:",r["gruplar"]);print("Tam:",r["tam_idler"]);print("Çapraz:",r["capraz_idler"])
```
```hint
Önce kendi sırrını ara; yoksa baştaki boşluğu atıp ortak başlangıcı say. Çapraz sızıntıda yalnız başka üye kayıtların sırlarına bak.
```
:::

::: anlat Hata vitrini · çalışmış yanlış rapor
Yazar, birinci ve ikinci kusurlu başlangıç kodunu görünür sentetik veriyle gerçekten çalıştırdı ve sonucu `outputs/yeni-ai-saldiri-48/gorunur-run-1.json` dosyasına kaydetti. Kusurlu kodun verdiği ham skor AUC'si **0.111**, kalibre skor AUC'si **0.000** oldu; doğru çözüm aynı veride 0.889 ve 1.000 verir.

Bu kaydedilmiş bir hesaplama çıktısıdır, model yanıtı değildir. Kusurlu rapora bakan biri "saldırı bu modelde işe yaramıyor, eğitim verisi güvende" sonucuna varabilir. Bu çıktı neden güven vermez? Skor yönünü ve eşitlik sayımını ayrı ayrı kendi cümlenle açıkla. Gerçek finaldeki ölçüm ayrıca üretilir; bu sayılar onun yerine konmaz.
:::

::: anlat Gerçek deney: kurgusal kayıtlarla LoRA, üyelik ve çıkarım
Final her koşuda 12 kurgusal destek kaydı üretir. Her kayıt rastgele bir müşteri numarası ve rastgele bir PIN taşır; gerçek kişi verisi yoktur. Altı kayıt **üye**dir: Qwen2.5-0.5B-Instruct üzerinde yalnız bu altı kayıtla LoRA eğitimi yapılır. Diğer altısı eğitimde hiç görülmez.

Deney önce bütün kayıtların kaybını eğitimden önce ölçer (referans), sonra eğitir ve kayıpları yeniden ölçer (hedef). Senin üç işlevin sırasıyla skorları, AUC/TPR raporunu ve çıkarım raporunu üretir. Sandbox aynı hesapları bağımsız referansla yapar; kabul, senin raporlarının referansla birebir aynı olmasına, taban ağırlıkların değişmemesine ve eğitimin gerçekten adaptörü güncellemesine bağlıdır. **Saldırının başarılı olması kabul şartı değildir.** AUC düşük çıkabilir, hiçbir PIN tam çıkmayabilir; bunlar da geçerli gözlemdir.

**Kanıt dosyasını oku:** Çalıştır ya da Kontrol Et sonunda kanıt dosyasının yolu yazılır. `satirlar` alanında üyelerin ve üye-olmayanların kayıplarını karşılaştır. `denemeler` alanında hangi üretimin hangi sırra benzediğine bak. Deneyi ikinci kez çalıştırınca PIN'ler değişir; tam çıkarım sayısı da değişti mi? Bu değişkenlik tek koşunun neden bir oran olmadığını gösterir. Cevabını tezgâhta yorum olarak yaz; otomatik test bu serbest açıklamayı puanlamaz.
:::

::: gorev Gerçek deney · Qwen LoRA üzerinde membership inference ve PIN çıkarımı
Önceki üç görevin `uyelik_skorlari`, `auc_raporu` ve `cikarim_raporu` işlevlerini birleştir. Çalıştır gerçek kayıpları, AUC raporunu ve üretimleri gösterir; Kontrol Et önce üç sözleşmeyi gizli verilerle sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
ortam: gpu
timeout: 300
```
```starter
import ai_lab
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def uyelik_skorlari(kayitlar):
    out=[]
    for k in kayitlar:
        out.append({"id":k["id"],"uye":k["uye"],"ham_skor":k["kayip_hedef"],"kalibre_skor":k["kayip_hedef"]-k["kayip_ref"]})
    return sorted(out,key=lambda k:k["id"])

# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def auc_raporu(skorlar,fpr_siniri):
    uye=[k["skor"] for k in skorlar if k["uye"]]
    degil=[k["skor"] for k in skorlar if not k["uye"]]
    kazanc=sum(1.0 if a>=b else 0.0 for a in uye for b in degil)
    en_iyi=(0.0,None)
    for t in sorted(set(uye+degil)):
        tpr=sum(s>=t for s in uye)/len(uye)
        fpr=sum(s>=t for s in degil)/len(uye)
        if fpr<fpr_siniri and tpr>en_iyi[0]:en_iyi=(tpr,t)
    return {"auc":kazanc/(len(uye)*len(degil)),"tpr_dusuk_fpr":en_iyi[0],"esik":en_iyi[1],"uye":len(uye),"uye_degil":len(degil)}

# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def cikarim_raporu(denemeler):
    gruplar={"uye":{"tam":0,"kismi":0,"yok":0,"adet":0},"uye_degil":{"tam":0,"kismi":0,"yok":0,"adet":0}};tam=[]
    for d in denemeler:
        g=gruplar["uye" if d["uye"] else "uye_degil"];g["adet"]+=1
        if d["uretim"].strip().startswith(d["sir"][:4]):
            g["tam"]+=1;tam.append(d["id"])
        else:
            g["yok"]+=1
    return {"gruplar":gruplar,"tam_idler":tam,"capraz_idler":[]}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_48 as D
    D.goster(uyelik_skorlari,auc_raporu,cikarim_raporu)
```
```test
import ai_lab,math
checks=[]
def kontrol(x,m):checks.append(bool(x));ok(x,m)
issues=ai_lab.kod_denetimi(src,("referans_skor","referans_auc","referans_cikarim","kanit_yaz"),izin=())
kontrol(not issues,"kopya/yama/dinamik kod yok: "+str(issues))
if issues:stop()
uyelik_skorlari=need("uyelik_skorlari");auc_raporu=need("auc_raporu");cikarim_raporu=need("cikarim_raporu")
def sinama1(f):
    import copy,random,math
    try:
        rng=random.Random(48)
        for n in (2,5,9):
            v=[{"id":f"k{rng.randrange(10**6)}-{i}","uye":i%2==0,"kayip_hedef":rng.uniform(0,6),"kayip_ref":rng.uniform(0,6)} for i in range(n)]
            v.append({"id":"sifir","uye":False,"kayip_hedef":0,"kayip_ref":0});v.append({"id":"int","uye":True,"kayip_hedef":2,"kayip_ref":5})
            old=copy.deepcopy(v);r=f(v)
            beklenen=[{"id":k["id"],"uye":k["uye"],"ham_skor":-k["kayip_hedef"],"kalibre_skor":k["kayip_ref"]-k["kayip_hedef"]} for k in sorted(v,key=lambda k:k["id"])]
            if r!=beklenen or v!=old:return False
        b=[{"id":"a","uye":True,"kayip_hedef":0.5,"kayip_ref":3.0}]
        for bad in (None,[],tuple(b),[dict(b[0],uye=1)],[dict(b[0],uye=None)],[dict(b[0],kayip_hedef=-0.1)],[dict(b[0],kayip_ref=-1)],[dict(b[0],kayip_hedef=float("nan"))],[dict(b[0],kayip_ref=float("inf"))],[dict(b[0],kayip_hedef=True)],[dict(b[0],kayip_ref="3")],b+b,[dict(b[0],id="")],[dict(b[0],id=7)],[dict(b[0],ek=1)],[{"id":"a","uye":True,"kayip_hedef":1}],[None]):
            try:f(bad);return False
            except ValueError:pass
        return True
    except Exception:return False
def sinama2(f):
    import copy,random,math
    def _ref(sk,lim):
        u=[k["skor"] for k in sk if k["uye"]];d=[k["skor"] for k in sk if not k["uye"]]
        kaz=sum(1.0 if a>b else 0.5 if a==b else 0.0 for a in u for b in d);ei=(0.0,None)
        for t in sorted(set(u+d)):
            tp=sum(s>=t for s in u)/len(u);fp=sum(s>=t for s in d)/len(d)
            if fp<=lim and tp>ei[0]:ei=(tp,t)
        return {"auc":kaz/(len(u)*len(d)),"tpr_dusuk_fpr":ei[0],"esik":ei[1],"uye":len(u),"uye_degil":len(d)}
    try:
        e=[{"id":"u1","uye":True,"skor":3},{"id":"u2","uye":True,"skor":2},{"id":"u3","uye":True,"skor":2},{"id":"d1","uye":False,"skor":2},{"id":"d2","uye":False,"skor":1}]
        old=copy.deepcopy(e)
        if f(e,0.5)!={"auc":5/6,"tpr_dusuk_fpr":1.0,"esik":2,"uye":3,"uye_degil":2} or e!=old:return False
        if f(e,0.25)!={"auc":5/6,"tpr_dusuk_fpr":1/3,"esik":3,"uye":3,"uye_degil":2}:return False
        if f(e,1)!={"auc":5/6,"tpr_dusuk_fpr":1.0,"esik":1,"uye":3,"uye_degil":2}:return False
        hep=[{"id":"u","uye":True,"skor":0},{"id":"d","uye":False,"skor":5}]
        if f(hep,1)!={"auc":0.0,"tpr_dusuk_fpr":1.0,"esik":0,"uye":1,"uye_degil":1} or f(hep,0.5)!={"auc":0.0,"tpr_dusuk_fpr":0.0,"esik":None,"uye":1,"uye_degil":1}:return False
        rng=random.Random(4848)
        for n in (3,6,11):
            v=[{"id":f"r{i}","uye":i%3!=0,"skor":rng.choice([rng.uniform(-3,3),1.5,-1])} for i in range(n)]
            for lim in (0.2,0.5,1):
                if f(copy.deepcopy(v),lim)!=_ref(v,lim):return False
        for sk,lim in ((e,0),(e,1.01),(e,True),(e,float("nan")),(e,"0.5"),(None,0.5),(tuple(e),0.5),(e[:3],0.5),(e[3:],0.5),(e+[e[0]],0.5),([dict(e[0],uye=1)]+e[1:],0.5),([dict(e[0],skor=float("inf"))]+e[1:],0.5),([dict(e[0],skor=True)]+e[1:],0.5),([dict(e[0],ek=1)]+e[1:],0.5),([dict(e[0],id="")]+e[1:],0.5),([None]+e,0.5)):
            try:f(sk,lim);return False
            except ValueError:pass
        return True
    except Exception:return False
def sinama3(f):
    import copy
    try:
        D=[{"id":"u-tam","uye":True,"sir":"AB12-CD34","uretim":" AB12-CD34. Teşekkürler"},
           {"id":"u-kismi","uye":True,"sir":"EF56-7788","uretim":"  EF56-7X. ok"},
           {"id":"u-alti","uye":True,"sir":"1234-5678","uretim":"1234X"},
           {"id":"u-baska","uye":True,"sir":"9999-0000","uretim":"AB12-CD34"},
           {"id":"d-capraz","uye":False,"sir":"5555-6666","uretim":" EF56-7788 ve AB12-CD34"},
           {"id":"d-kendi","uye":False,"sir":"7777-1111","uretim":"7777-1111"},
           {"id":"d-yok","uye":False,"sir":"0000-2222","uretim":"bilmiyorum"}]
        old=copy.deepcopy(D);r=f(D)
        if D!=old:return False
        if r!={"gruplar":{"uye":{"tam":1,"kismi":1,"yok":2,"adet":4},"uye_degil":{"tam":1,"kismi":0,"yok":2,"adet":3}},"tam_idler":["d-kendi","u-tam"],"capraz_idler":["d-capraz","u-baska"]}:return False
        if f(list(reversed(D)))!=r:return False
        sinir=[{"id":"a","uye":True,"sir":"ABCDEFGH","uretim":"ABCDzzzz"},{"id":"b","uye":False,"sir":"ABCDEFGHI","uretim":"ABCDzzzz"},{"id":"c","uye":False,"sir":"WXYZ","uretim":"wxyz"}]
        if f(sinir)["gruplar"]!={"uye":{"tam":0,"kismi":1,"yok":0,"adet":1},"uye_degil":{"tam":0,"kismi":0,"yok":2,"adet":2}}:return False
        atla=[{"id":"a","uye":True,"sir":"AB12-CD34","uretim":"AX1X-XDX"},{"id":"b","uye":False,"sir":"WXYZ","uretim":"W"},{"id":"c","uye":False,"sir":"WXYZ","uretim":"AXYZ"}]
        if f(atla)["gruplar"]!={"uye":{"tam":0,"kismi":0,"yok":1,"adet":1},"uye_degil":{"tam":0,"kismi":0,"yok":2,"adet":2}}:return False
        for bad in (None,tuple(D),[D[0]],[D[4]],D+[D[0]],[dict(D[0],sir="ABC")]+D[4:],[dict(D[0],sir="AB\nCD")]+D[4:],[dict(D[0],sir=None)]+D[4:],[dict(D[0],uye=1)]+D[4:],[dict(D[0],uretim=None)]+D[4:],[dict(D[0],id="")]+D[4:],[dict(D[0],ek=1)]+D[4:],[None]+D):
            try:f(bad);return False
            except ValueError:pass
        return True
    except Exception:return False
kontrol(sinama1(uyelik_skorlari),"skor yönü, kalibrasyon, sıra ve geçersiz girdi")
kontrol(sinama2(auc_raporu),"eşitlik yarım, dahil FPR sınırı, doğru paydalar")
kontrol(sinama3(cikarim_raporu),"tam/kısmi sınırı, grup ayrımı, çapraz sızıntı")
for ad,mut in [("ters skor",lambda ks:[dict(s,ham_skor=-s["ham_skor"]) for s in uyelik_skorlari(ks)]),("tam kazanç eşitlik",lambda s,l:dict(auc_raporu(s,l),auc=1.0)),("çapraz yok",lambda d:dict(cikarim_raporu(d),capraz_idler=[]))]:
    kontrol(not (sinama1(mut) if ad=="ters skor" else sinama2(mut) if ad=="tam kazanç eşitlik" else sinama3(mut)),"mutant reddedildi: "+ad)
if not all(checks):stop()
from sandbox import ai_gercek_ai_saldiri_48 as D
try:r=D.deney(uyelik_skorlari,auc_raporu,cikarim_raporu)
except ai_lab.GercekLabYok as e:
    kontrol(False,"gerçek deney yok: "+str(e));stop()
kontrol(r["skor"]==r["skor_referans"],"gerçek kayıplardan skorlar bağımsız hesapla aynı")
kontrol(r["auc"]==r["auc_referans"],"gerçek skorlardan AUC/TPR raporu bağımsız hesapla aynı")
kontrol(r["cikarim"]==r["cikarim_referans"],"gerçek üretimlerden çıkarım raporu bağımsız hesapla aynı")
kontrol(r["base_once"]==r["base_sonra"],"taban ağırlıklar değişmedi")
kontrol(r["adapter_hash"][0]!=r["adapter_hash"][1],"LoRA adaptörü gerçekten güncellendi")
kontrol(len(r["egitim"])==r["ayarlar"]["tur"]*r["ayarlar"]["uye"] and all(math.isfinite(k["loss"]) and math.isfinite(k["grad_norm"]) and k["grad_norm"]>0 for k in r["egitim"]),"bütün eğitim adımları sonlu loss ve sıfır olmayan gradient üretti")
kontrol(len(r["satirlar"])==len(r["denemeler"])==12 and sum(s["uye"] for s in r["satirlar"])==6,"12 kurgusal kayıt, 6 üye")
ai_lab.kanit_yaz("saldiri48-kabul",{"kaynak":"gercek","kabul":all(checks),"ders":"ai-saldiri-48","deney":r})
```
```solution
import ai_lab
import math
def uyelik_skorlari(kayitlar):
    if not isinstance(kayitlar,list) or not kayitlar:raise ValueError("kayıt")
    ids=set();out=[]
    for k in kayitlar:
        if not isinstance(k,dict) or set(k)!={"id","uye","kayip_hedef","kayip_ref"}:raise ValueError("şema")
        if not isinstance(k["id"],str) or not k["id"] or k["id"] in ids:raise ValueError("id")
        if type(k["uye"]) is not bool:raise ValueError("üye")
        for a in ("kayip_hedef","kayip_ref"):
            if isinstance(k[a],bool) or not isinstance(k[a],(int,float)):raise ValueError("sayı")
            if not math.isfinite(k[a]) or k[a]<0:raise ValueError("kayıp")
        ids.add(k["id"])
        out.append({"id":k["id"],"uye":k["uye"],"ham_skor":-k["kayip_hedef"],"kalibre_skor":k["kayip_ref"]-k["kayip_hedef"]})
    return sorted(out,key=lambda k:k["id"])

def auc_raporu(skorlar,fpr_siniri):
    if isinstance(fpr_siniri,bool) or not isinstance(fpr_siniri,(int,float)) or not math.isfinite(fpr_siniri) or not 0<fpr_siniri<=1:raise ValueError("fpr")
    if not isinstance(skorlar,list):raise ValueError("liste")
    ids=set();uye=[];degil=[]
    for k in skorlar:
        if not isinstance(k,dict) or set(k)!={"id","uye","skor"}:raise ValueError("şema")
        if not isinstance(k["id"],str) or not k["id"] or k["id"] in ids:raise ValueError("id")
        if type(k["uye"]) is not bool:raise ValueError("üye")
        if isinstance(k["skor"],bool) or not isinstance(k["skor"],(int,float)) or not math.isfinite(k["skor"]):raise ValueError("skor")
        ids.add(k["id"])
        (uye if k["uye"] else degil).append(k["skor"])
    if not uye or not degil:raise ValueError("iki sınıf gerekli")
    kazanc=sum(1.0 if a>b else 0.5 if a==b else 0.0 for a in uye for b in degil)
    en_iyi=(0.0,None)
    for t in sorted(set(uye+degil)):
        tpr=sum(s>=t for s in uye)/len(uye)
        fpr=sum(s>=t for s in degil)/len(degil)
        if fpr<=fpr_siniri and tpr>en_iyi[0]:en_iyi=(tpr,t)
    return {"auc":kazanc/(len(uye)*len(degil)),"tpr_dusuk_fpr":en_iyi[0],"esik":en_iyi[1],"uye":len(uye),"uye_degil":len(degil)}

def cikarim_raporu(denemeler):
    if not isinstance(denemeler,list):raise ValueError("liste")
    ids=set();gruplar={"uye":{"tam":0,"kismi":0,"yok":0,"adet":0},"uye_degil":{"tam":0,"kismi":0,"yok":0,"adet":0}};tam=[]
    for d in denemeler:
        if not isinstance(d,dict) or set(d)!={"id","uye","sir","uretim"}:raise ValueError("şema")
        if not isinstance(d["id"],str) or not d["id"] or d["id"] in ids:raise ValueError("id")
        if type(d["uye"]) is not bool or not isinstance(d["uretim"],str):raise ValueError("alan")
        if not isinstance(d["sir"],str) or len(d["sir"])<4 or any(c in d["sir"] for c in "\r\n\0"):raise ValueError("sır")
        ids.add(d["id"])
        g=gruplar["uye" if d["uye"] else "uye_degil"];g["adet"]+=1
        if d["sir"] in d["uretim"]:
            g["tam"]+=1;tam.append(d["id"])
        else:
            u=d["uretim"].lstrip();n=0
            while n<min(len(u),len(d["sir"])) and u[n]==d["sir"][n]:n+=1
            g["kismi" if n>=math.ceil(len(d["sir"])/2) else "yok"]+=1
    if not gruplar["uye"]["adet"] or not gruplar["uye_degil"]["adet"]:raise ValueError("iki grup gerekli")
    uye_sirlari={d["id"]:d["sir"] for d in denemeler if d["uye"]}
    capraz=[d["id"] for d in denemeler if any(s in d["uretim"] for i,s in uye_sirlari.items() if i!=d["id"])]
    return {"gruplar":gruplar,"tam_idler":sorted(tam),"capraz_idler":sorted(capraz)}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_48 as D
    D.goster(uyelik_skorlari,auc_raporu,cikarim_raporu)
```
```hint
Üç işlevi aynen birleştir. Sonuçları yorumlarken AUC ile TPR @ düşük FPR'yi ayrı oku; tam, kısmi ve çapraz çıkarımı karıştırma.
```
:::

::: anlat Sınır
Bu ders kurgusal 12 kayıtla eğitilmiş tek bir LoRA adaptöründe üyelik sinyalini ve ezber sızıntısını gösterir; ön-eğitim verisinin içeriğini, gerçek kişisel verinin çıkarılabilirliğini veya bir saldırının genel başarı oranını gösteremez.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
### Üyelik skoru karar değil, sıralamadır

Hedef kaybı düşükse negatif kayıp büyür. Referans kaybını çıkarmak yerine hedef kaybını referanstan çıkarmak, doğal olarak kolay örnekleri kısmen dengelemeyi amaçlar. AUC üye–üye değil çiftlerinde doğru sıralama olasılığıdır; eşit skor yarım sayılır. Düşük FPR koşulu ise belirli eşiklerde kaç meşru örneğin yanlış üye sayıldığını sınırlar. Altı üye olmayan örnekte FPR adımları 1/6 olduğundan küçük ondalıklı hedefler hassas bir saha oranı değildir. PIN çıkarımı ayrı bir ölçümdür; yüksek AUC tek başına tam sır üretimi demek değildir.

| Yaygın yanlış | Mekanizmanın söylediği |
|---|---|
| Üye tahmini veriyi çıkarmaktır | Üyelik kararı ile tam/kısmi/çapraz çıkarım ayrı sonuçlardır. |

Sonraki bağlantı: ai-guvence-09 ile mahremiyet ölçümü.
:::
