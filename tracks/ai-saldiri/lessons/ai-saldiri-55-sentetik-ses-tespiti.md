---
id: ai-saldiri-55
title: Sentetik Ses Tespiti · Mükemmel Skorun Arkasındaki Kısayol ve Görülmemiş Üretici
summary: Onaylı yerel LibriSpeech örneklerini Piper (LJSpeech) TTS ile aynı metinlerden üretilmiş seslerle karşılaştıran basit bir sentetik ses dedektörü eğit; metne göre doğru bölme, EER, gürültü, telefon bandı, yeniden örnekleme ve görülmemiş bir üretici (Windows SAPI) altında neyin gerçekten kırıldığını ölç.
esleme: ai-saldiri-54, ai-saldiri-53, ai-savunma-37
timeout: 60
---

::: anlat Sahte sesi yakalamak mı, kısayolu yakalamak mı?
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Sentetik konuşma (TTS), ses dönüştürme ve tekrar oynatma saldırıları; bunlara karşı spoof karşı önlemleri ve büyük ölçekli değerlendirme setleri (ör. ASVspoof 2019) | Final: kullanıcı onayıyla `.deps` altına indirilen sabit sürümler — Piper TTS 1.8.0 ve LJSpeech medium sesi (tek konuşmacı, kamu malı veri), LibriSpeech'ten 73 örneklik küçük test alt kümesi (tek konuşmacı, 16 kHz) — ve Windows'ta yerleşik SAPI "Microsoft Zira" sesi | Gerçek bir kişinin sesinin klonlanmasını, ses dönüştürmeyi, tekrar oynatmayı ve büyük setlerdeki başarıyı göstermez |
| Spektral özelliklerle eğitilmiş bir sınıflandırıcının eşikte TPR/FPR ve EER değerleri | Final: 24 bantlık log spektrum + düzlük + sıfır geçiş özellikleri, lojistik regresyon, 45 metin (30 eğitim / 15 test) | Derin öğrenme tabanlı modern dedektörlerin davranışını göstermez |

> [!NOT]
> İlk üç görev `veri/ses.json` dosyasını okur; kayıtlar, skorlar ve satırlar elle yazılmıştır, ses ya da model çıktısı değildir. Setup her Çalıştır/Kontrol Et adımında geçici kopya kurar; **kalıcılık yoktur**. Ekranda ayrı bir dosya görüntüleyici yoktur; içeriği görmek için başlangıç kodundaki `print` satırlarını kullan. Final ağ kullanmaz, otomatik indirme yapmaz; onaylı dosyaların sha256'sını doğrular, eksikse açıkça durur. Kimsenin sesi kaydedilmez ya da klonlanmaz; mikrofon kullanılmaz. Ses dosyaları geçici klasörde üretilir ve koşu sonunda silinir.

**Saldırı yüzeyi.** Bir çağrı merkezi, bir sesli doğrulama sistemi ya da bir haber doğrulama ekibi "bu ses sentetik mi?" diye soran bir dedektöre güvenebilir. Saldırganın amacı sentetik sesi bu dedektöre "gerçek" diye geçirmektir. Literatür bu saldırıları üç ana türde toplar: konuşma sentezi (TTS), ses dönüştürme ve kaydı tekrar oynatma. ASVspoof 2019 veri seti bu türleri büyük ölçekte toplar ve karşı önlemleri karşılaştırır. Bu tür değerlendirmelerde eşik seçiminden bağımsız bir ölçü olarak **EER** (eşit hata oranı: yanlış kabul ile yanlış reddin eşitlendiği nokta) yaygın kullanılır.

**Bu laboratuvardaki kurulum.** Gerçek sınıf: LibriSpeech'ten tek bir konuşmacının 16 kHz kayıtları. Sentetik sınıf: Piper'ın LJSpeech sesiyle **aynı metinlerin** okunması (22050 Hz). İki model eğitilir. **A** sesi kendi örnekleme hızında işler: Piper 22050 Hz olduğu için 8 kHz'in üstünde enerji taşır, gerçek kayıtlar 16 kHz olduğu için taşımaz. **B** iki sınıfı da önce 16 kHz'e indirir. Test kümesinde beş koşul ölçülür: temiz, 20 dB gürültü, telefon bandı (300–3400 Hz), sentetik sesin 16 kHz'e indirilmesi ve hiç görülmemiş bir üretici (SAPI).

**Saldırgan ne dener?** (1) **Kısayolu kırmak:** Dedektör "sentetik"i sesin kendisinden değil, örnekleme hızı ya da bant genişliği gibi yan bir izden öğrendiyse, saldırgan yalnız o izi siler (ör. 16 kHz'e yeniden örnekler). (2) **Kanal değiştirmek:** Sesi telefon bandından ya da gürültülü bir ortamdan geçirir; dedektörün eşiği kayar. (3) **Başka bir üretici kullanmak:** Dedektör eğitimde gördüğü TTS'yi tanıyorsa, başka bir TTS'yi tanımayabilir.

**Savunma neden kırılır?** Küçük ve tek kaynaklı veride sınıflandırıcı en kolay ayrımı öğrenir; bu ayrım sentezle ilgili olmak zorunda değildir. Bu derste gerçek sınıf **tek bir konuşmacıdan**, sentetik sınıf **tek bir TTS sesinden** gelir. Bu yüzden dedektör "bu ses LibriSpeech'teki o konuşmacı mı?" sorusunu öğrenmiş olabilir. Bu deney bu ihtimali **ayıramaz**; sonuçlar buna göre okunmalıdır. Aynı metnin gerçek ve sentetik kaydı eğitim ile teste dağılırsa, model metin içeriğini ezberleyip test başarısını şişirebilir. Görev 1 bunu metne göre bölerek engeller. Son olarak, eşikte TPR ile EER aynı şeyi söylemez: skorlar hâlâ doğru sıralanırken sabit eşik kayabilir.

Kaynaklar: [Wang vd. · ASVspoof 2019 (arXiv:1911.01601)](https://arxiv.org/abs/1911.01601), [Piper TTS 1.8.0 (PyPI)](https://pypi.org/project/piper-tts/1.8.0/), [rhasspy/piper-voices · LJSpeech medium](https://huggingface.co/rhasspy/piper-voices/tree/e7229f7d33a10e145e109b886d661984201ac3c4/en/en_US/ljspeech/medium), [hf-internal-testing/librispeech_asr_dummy](https://huggingface.co/datasets/hf-internal-testing/librispeech_asr_dummy). Bu dersteki bütün sayılar yalnız yerel kanıttan gelir.

Saldırı↔savunma köprüsü: ai-saldiri-54 bir güvenlik ML dedektörünü atlatır, ai-saldiri-53 görüntüde piksel düzeyinde saldırır; bu ders aynı soruyu sese taşır. ai-savunma-37 medyanın kökenini imzayla kanıtlamaya çalışır; içerik tabanlı tespit bu imzanın olmadığı yerde başvurulan ikinci yoldur.
:::

::: tahmin round ve eşik
Çıktıyı tahmin et, sonra Çalıştır ile karşılaştır.
```python
print(round(2.5), round(3.5), round(15 * 0.34))
s, e = [0.9, 0.6, 0.6, 0.2], [1, 0, 1, 0]
print(sum(1 for x, y in zip(s, e) if y and x > 0.6), sum(1 for x, y in zip(s, e) if y and x >= 0.6))
```
???
```cikti
2 4 5
1 2
```
Tahmininle gerçek çıktı arasındaki farkı tezgâhta yorum satırı olarak yaz: Python `round` 2.5'i neden 2'ye yuvarladı, eşik `>` mı `>=` mı olmalı? Sonra üç kusurlu başlangıç kodunu çalıştır. Hangisi aynı metni hem eğitime hem teste koyuyor, hangisi oranları toplam örnek sayısına bölüp EER yerine toplam hatayı küçültüyor, hangisi düşüşün işaretini ters alıp temizde zaten kötü olan modeli de "kırılgan" sayıyor? Önce kendin teşhis et; açıklama çözümün ardından gelir.
:::

::: gorev 1 · Metne göre grup bölmesi
`grup_bol(kayitlar, test_orani)`: `test_orani` int ya da float (bool değil), 0 < oran < 1. `kayitlar` boş olmayan liste; her kayıt tam olarak `id` (benzersiz dolu string), `metin` (dolu string), `kaynak` (`gercek` ya da `sentetik`). Aksi hâlde `ValueError`. Farklı metinler (gruplar) `hashlib.sha256(metin.encode("utf-8")).hexdigest()` değerine göre sıralanır; `n = round(grup_sayisi * test_orani)` (Python `round`). `n`, 1 ile `grup_sayisi - 1` arasında değilse `ValueError`. Sıradaki ilk `n` grubun **bütün** kayıtları teste, kalanlar eğitime gider. İki tarafta da hem `gercek` hem `sentetik` kayıt olmalı; yoksa `ValueError`. `{"egitim": [...], "test": [...]}` döndür; listeler sıralı kimlikler. Girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-55")
```

```starter
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def grup_bol(kayitlar,test_orani):
    adim=round(1/test_orani)
    test=[k["id"] for i,k in enumerate(kayitlar) if i%adim==0]
    return {"egitim":[k["id"] for k in kayitlar if k["id"] not in test],"test":test}

from ai_saldiri_veri import json_yukle
v=json_yukle("veri/ses.json")
b=grup_bol(v["kayitlar"],v["test_orani"])
metin={k["id"]:k["metin"] for k in v["kayitlar"]}
print("eğitim:",b["egitim"]);print("test:",b["test"])
print("iki tarafta da olan metin:",sorted({metin[i] for i in b["egitim"]}&{metin[i] for i in b["test"]}))
```
```test
def sinama1(f):
    import hashlib,copy
    try:
        H=lambda m:hashlib.sha256(m.encode("utf-8")).hexdigest()
        def kk(ms):
            r=[]
            for i,m in enumerate(ms):r+=[{"id":f"g{i}","metin":m,"kaynak":"gercek"},{"id":f"s{i}","metin":m,"kaynak":"sentetik"}]
            return r
        def bek(K,n):
            sira=sorted({k["metin"] for k in K},key=H);t=set(sira[:n])
            return {"egitim":sorted(k["id"] for k in K if k["metin"] not in t),"test":sorted(k["id"] for k in K if k["metin"] in t)}
        M=["çay saati","kuzey rüzgârı","ship at dawn","old door","quiet town","short letter"]
        K=kk(M);e=copy.deepcopy(K);r=f(K,0.34)
        if K!=e or r!=bek(K,2) or f(list(reversed(K)),0.34)!=r:return False
        if f(K,0.5)!=bek(K,3) or f(K,0.2)!=bek(K,1) or f(K,0.75)!=bek(K,4):return False
        K10=kk([f"metin {i}" for i in range(10)])
        K4=kk(["p","q","r","s"])
        if f(K10,0.25)!=bek(K10,2) or f(K10,0.75)!=bek(K10,8) or f(K4,0.375)!=bek(K4,2) or f(K4,0.625)!=bek(K4,2):return False
        if any(set(r["egitim"])&set(r["test"]) for r in (f(K,0.5),f(K10,0.25))):return False
        T3=kk(["a1","b2","c3"])
        for o in (0.1,0.9):
            try:f(T3,o);return False
            except ValueError:pass
        sira=sorted(M,key=H);Y=[k for k in kk(M) if not (k["metin"]==sira[0] and k["kaynak"]=="sentetik")]
        try:f(Y,0.2);return False
        except ValueError:pass
        Z=[k for k in kk(M) if not (k["metin"]==sira[-1] and k["kaynak"]=="sentetik")]
        if f(Z,0.2)!=bek(Z,1):return False
        Z2=[k for k in kk(M) if not (k["metin"]!=sira[0] and k["kaynak"]=="gercek")]
        try:f(Z2,0.2);return False
        except ValueError:pass
        T=lambda **d:[dict(K[0],**d)]+K[1:]
        for bad,o in ((K,0),(K,1),(K,True),(K,"0.3"),(K,None),(K,-0.2),(K,float("inf")),(K,float("nan")),(None,0.3),([],0.3),(tuple(K),0.3),(K+[K[0]],0.3),(T(id=""),0.3),(T(id=3),0.3),
                      (T(metin=""),0.3),(T(metin=None),0.3),(T(metin=123),0.3),(T(kaynak="x"),0.3),(T(ek=1),0.3),([{"id":"q","metin":"m"}]+K[1:],0.3),([None]+K,0.3)):
            try:f(bad,o);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama1(grup_bol),"metin grubu bölmesi, hash sırası, round, iki kaynak ve geçersiz girdi")
for ad,mut in [("bir test kaydı eğitime sızıyor",lambda K,o:dict(grup_bol(K,o),egitim=sorted(grup_bol(K,o)["egitim"]+grup_bol(K,o)["test"][:1]))),("eğitim/test yer değiştirdi",lambda K,o:{"egitim":grup_bol(K,o)["test"],"test":grup_bol(K,o)["egitim"]}),("sırasız",lambda K,o:{a:list(reversed(b)) for a,b in grup_bol(K,o).items()})]:
    ok(not sinama1(mut),"mutant reddedildi: "+ad)
```
```solution
import hashlib
def grup_bol(kayitlar,test_orani):
    if type(test_orani) not in (int,float) or not 0<test_orani<1:raise ValueError("oran")
    if not isinstance(kayitlar,list) or not kayitlar:raise ValueError("liste")
    ids=set()
    for k in kayitlar:
        if not isinstance(k,dict) or set(k)!={"id","metin","kaynak"}:raise ValueError("şema")
        if not isinstance(k["id"],str) or not k["id"] or k["id"] in ids:raise ValueError("id")
        if not isinstance(k["metin"],str) or not k["metin"] or k["kaynak"] not in ("gercek","sentetik"):raise ValueError("alan")
        ids.add(k["id"])
    gruplar=sorted({k["metin"] for k in kayitlar},key=lambda m:hashlib.sha256(m.encode("utf-8")).hexdigest())
    n=round(len(gruplar)*test_orani)
    if not 1<=n<len(gruplar):raise ValueError("bölünemez")
    test=set(gruplar[:n])
    b={"egitim":sorted(k["id"] for k in kayitlar if k["metin"] not in test),"test":sorted(k["id"] for k in kayitlar if k["metin"] in test)}
    for ad in b:
        if {k["kaynak"] for k in kayitlar if k["id"] in b[ad]}!={"gercek","sentetik"}:raise ValueError("iki kaynak da gerekli")
    return b

from ai_saldiri_veri import json_yukle
v=json_yukle("veri/ses.json")
b=grup_bol(v["kayitlar"],v["test_orani"])
metin={k["id"]:k["metin"] for k in v["kayitlar"]}
print("eğitim:",b["egitim"]);print("test:",b["test"])
print("iki tarafta da olan metin:",sorted({metin[i] for i in b["egitim"]}&{metin[i] for i in b["test"]}))
```
```hint
Önce kayıtları değil, farklı metinleri sırala. Bir metnin gerçek ve sentetik kaydı her zaman aynı tarafa düşmeli.
```
:::

::: anlat Eşik ile sıralama ayrı şeylerdir
Bir dedektör her örneğe bir skor verir. **Eşikte** ölçülen TPR ve FPR, o eşiğin bugünkü veriye uygun olup olmadığını da ölçer. **EER** ise eşiği taradığı için skorların sınıfları ne kadar iyi **sıraladığını** gösterir. Koşul değişince (telefon bandı gibi) skorlar topluca kayabilir. O zaman EER düşük kalırken sabit eşikte TPR sıfıra inebilir. Bu bir "kalibrasyon kayması"dır ve sahada sabit eşikle çalışan bir sistemde gerçek bir açıktır. Görev 2 ikisini de hesaplar.
:::

::: gorev 2 · Eşikte TPR/FPR ve eşit hata oranı (EER)
Ortak kurallar: `skorlar` ve `etiketler` aynı uzunlukta boş olmayan listeler; skorlar int ya da float (bool değil); etiketler yalnız 0/1 int (1 = sentetik) ve iki sınıf da var. Aksi hâlde `ValueError`. `esik_metrikleri(skorlar, etiketler, esik)`: `esik` int ya da float (bool değil). Tahmin `skor >= esik` ise sentetik. `tpr` = doğru yakalanan sentetik / sentetik sayısı; `fpr` = yanlışlıkla sentetik denilen gerçek / gerçek sayısı; `dogruluk` = doğru tahmin / toplam. `{"tpr", "fpr", "dogruluk"}` döndür. `esit_hata(skorlar, etiketler)`: aday eşikler skorların farklı değerleri (artan sırada). Her aday için `fpr` ve `fnr = 1 - tpr`; şu sırayla en küçük olanı seç: `abs(fpr - fnr)`, sonra `(fpr + fnr) / 2`, sonra eşik. `{"eer": (fpr + fnr) / 2, "esik", "fpr", "fnr"}` döndür. Girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-55")
```

```starter
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def esik_metrikleri(skorlar,etiketler,esik):
    tp=sum(1 for s,e in zip(skorlar,etiketler) if e and s>esik);fp=sum(1 for s,e in zip(skorlar,etiketler) if not e and s>esik)
    n=len(etiketler)
    return {"tpr":tp/n,"fpr":fp/n,"dogruluk":(tp+n-fp)/n}

# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def esit_hata(skorlar,etiketler):
    en=None
    for t in sorted(set(skorlar)):
        m=esik_metrikleri(skorlar,etiketler,t);fpr=m["fpr"];fnr=1-m["tpr"]
        if en is None or fpr+fnr<en[0]:en=(fpr+fnr,{"eer":(fpr+fnr)/2,"esik":t,"fpr":fpr,"fnr":fnr})
    return en[1]

from ai_saldiri_veri import json_yukle
v=json_yukle("veri/ses.json");o=v["skor_ornek"]
for esik in v["esikler"]:print("eşik",esik,"→",esik_metrikleri(o["skorlar"],o["etiketler"],esik))
print("EER:",esit_hata(o["skorlar"],o["etiketler"]))
```
```test
def sinama2(m,eer):
    import copy
    try:
        S=[0.9,0.2,0.6,0.4];E=[1,0,1,0];s0=list(S)
        if m(S,E,0.5)!={"tpr":1.0,"fpr":0.0,"dogruluk":1.0} or S!=s0:return False
        if m(S,E,0.6)!={"tpr":1.0,"fpr":0.0,"dogruluk":1.0} or m(S,E,0.61)!={"tpr":0.5,"fpr":0.0,"dogruluk":0.75} or m(S,E,0.4)!={"tpr":1.0,"fpr":0.5,"dogruluk":0.75}:return False
        if m([0.8,0.7,0.3,0.6,0.1],[1,0,0,0,1],0.5)!={"tpr":0.5,"fpr":2/3,"dogruluk":0.4} or m([1,0],[1,0],1)!={"tpr":1.0,"fpr":0.0,"dogruluk":1.0}:return False
        if eer([0,1,2],[0,1,0])!={"eer":0.25,"esik":1,"fpr":0.5,"fnr":0.0}:return False
        if eer([0.9,0.8,0.7,0.6],[1,0,1,0])!={"eer":0.5,"esik":0.8,"fpr":0.5,"fnr":0.5}:return False
        if eer([0.9,0.1,0.8,0.2],[1,0,1,0])!={"eer":0.0,"esik":0.8,"fpr":0.0,"fnr":0.0}:return False
        if eer([0.9,0.5,0.1],[1,0,1])!={"eer":0.25,"esik":0.9,"fpr":0.0,"fnr":0.5}:return False
        if eer([0.3,0.3,0.7,0.7],[0,1,0,1])!={"eer":0.5,"esik":0.7,"fpr":0.5,"fnr":0.5}:return False
        if eer([0.6,0.2,0.4],[1,0,0])!={"eer":0.0,"esik":0.6,"fpr":0.0,"fnr":0.0}:return False
        for bad in (([0.1],[1]),([0.1,0.2],[1,1]),([0.1,0.2],[0,0]),([0.1],[1,0]),([],[]),([0.1,0.2],[1,2]),([0.1,0.2],[1,True]),([0.1,0.2,0.3],[1,0,True]),([0.1,"0.2"],[1,0]),([0.1,True],[1,0]),((0.1,0.2),[1,0]),([0.1,0.2],(1,0)),([0.1,None],[1,0])):
            for fn,a in ((m,bad+(0.5,)),(eer,bad)):
                try:fn(*a);return False
                except ValueError:pass
        for es in ("0.5",None,True):
            try:m([0.1,0.2],[1,0],es);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama2(esik_metrikleri,esit_hata),"eşik metrikleri, paydalar, EER seçimi ve geçersiz girdi")
def _toplam(S,E):
    r=esit_hata(S,E);en=None
    for t in sorted(set(S)):
        m=esik_metrikleri(S,E,t);a=(m["fpr"]+1-m["tpr"],t)
        if en is None or a<en[0]:en=(a,{"eer":a[0]/2,"esik":t,"fpr":m["fpr"],"fnr":1-m["tpr"]})
    return en[1] if r else r
for ad,mm,ee in [("katı eşik",lambda S,E,t:esik_metrikleri(S,E,t+1e-9),esit_hata),("toplam hatayı küçült",esik_metrikleri,_toplam),("fpr paydası tüm örnekler",lambda S,E,t:dict(esik_metrikleri(S,E,t),fpr=esik_metrikleri(S,E,t)["fpr"]*(len(E)-sum(E))/len(E)),esit_hata)]:
    ok(not sinama2(mm,ee),"mutant reddedildi: "+ad)
```
```solution
def _dogrula(skorlar,etiketler):
    if not isinstance(skorlar,list) or not isinstance(etiketler,list) or not skorlar or len(skorlar)!=len(etiketler):raise ValueError("liste")
    if any(type(s) not in (int,float) for s in skorlar) or any(type(e) is not int or e not in (0,1) for e in etiketler):raise ValueError("değer")
    if set(etiketler)!={0,1}:raise ValueError("iki sınıf")

def esik_metrikleri(skorlar,etiketler,esik):
    _dogrula(skorlar,etiketler)
    if type(esik) not in (int,float):raise ValueError("eşik")
    P=sum(etiketler);N=len(etiketler)-P
    tp=sum(1 for s,e in zip(skorlar,etiketler) if e and s>=esik);fp=sum(1 for s,e in zip(skorlar,etiketler) if not e and s>=esik)
    return {"tpr":tp/P,"fpr":fp/N,"dogruluk":(tp+N-fp)/len(etiketler)}

def esit_hata(skorlar,etiketler):
    _dogrula(skorlar,etiketler)
    en=None
    for t in sorted(set(skorlar)):
        m=esik_metrikleri(skorlar,etiketler,t);fpr=m["fpr"];fnr=1-m["tpr"]
        a=(abs(fpr-fnr),fpr+fnr,t)
        if en is None or a<en[0]:en=(a,{"eer":(fpr+fnr)/2,"esik":t,"fpr":fpr,"fnr":fnr})
    return en[1]

from ai_saldiri_veri import json_yukle
v=json_yukle("veri/ses.json");o=v["skor_ornek"]
for esik in v["esikler"]:print("eşik",esik,"→",esik_metrikleri(o["skorlar"],o["etiketler"],esik))
print("EER:",esit_hata(o["skorlar"],o["etiketler"]))
```
```hint
Paydalar sınıf büyüklükleridir, toplam örnek sayısı değil. EER, toplam hatayı değil iki hata oranının eşitliğini arar.
```
:::

::: anlat Kırılganlık nasıl raporlanır?
Tek bir "doğruluk" sayısı bir dedektörün nerede kırıldığını saklar. Görev 3 her model için temiz değerleri ve her koşuldaki düşüşü ayrı raporlar. `kirilan` eşikte yarıdan az yakalanan koşulları, `en_kotu` sıralama kalitesinin (EER) en çok bozulduğu koşulu gösterir. `kirilgan` ise iki şartın birlikte sağlandığı modelleri işaretler: temizde neredeyse kusursuz görünür ama en az bir koşulda yakalamanın yarısını kaybeder. Temizde zaten kötü bir model bu tanımla "kırılgan" sayılmaz; o sadece kötüdür.
:::

::: gorev 3 · Koşul raporu: hangi model nerede kırıldı?
`kosul_raporu(satirlar)`: boş olmayan liste; her satır tam olarak `model`, `kosul` (dolu string), `tpr`, `fpr`, `eer` (int ya da float, bool değil, 0–1). Bir modelde aynı koşul iki kez olamaz; her modelin `temiz` satırı olmalı. Aksi hâlde `ValueError`. Her model için (model adına göre sıralı): `temiz` = `{"tpr", "fpr", "eer"}`; `kosullar` = temiz dışındaki her koşul için (ada göre sıralı) `{"tpr_dusus": temiz_tpr - tpr, "fpr_artis": fpr - temiz_fpr, "eer_artis": eer - temiz_eer}`; `kirilan` = `tpr < 0.5` olan koşullar (sıralı); `en_kotu` = `eer_artis` değeri en büyük koşul (eşitlikte ada göre ilk; koşul yoksa `None`). `kirilgan` = temiz `eer <= 0.1` olan ve en az bir koşulda `tpr_dusus >= 0.5` olan modeller (sıralı). `{"modeller", "kirilgan"}` döndür. Girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-55")
```

```starter
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def kosul_raporu(satirlar):
    tab={}
    for s in satirlar:tab.setdefault(s["model"],{})[s["kosul"]]=s
    out={};kir=[]
    for m in tab:
        t=tab[m]["temiz"];ks={}
        for k in tab[m]:
            if k=="temiz":continue
            x=tab[m][k];ks[k]={"tpr_dusus":x["tpr"]-t["tpr"],"fpr_artis":x["fpr"]-t["fpr"],"eer_artis":x["eer"]-t["eer"]}
        en=max(ks,key=lambda k:ks[k]["tpr_dusus"]) if ks else None
        out[m]={"temiz":{"tpr":t["tpr"],"fpr":t["fpr"],"eer":t["eer"]},"kosullar":ks,"kirilan":[k for k in ks if tab[m][k]["tpr"]<=0.5],"en_kotu":en}
        if any(v["tpr_dusus"]>=0.5 for v in ks.values()):kir.append(m)
    return {"modeller":out,"kirilgan":kir}

from ai_saldiri_veri import json_yukle
v=json_yukle("veri/ses.json")
r=kosul_raporu(v["satirlar"])
for m,x in r["modeller"].items():print(m,"| temiz:",x["temiz"],"| kırılan:",x["kirilan"],"| en kötü:",x["en_kotu"],"|",x["kosullar"])
print("kırılgan modeller:",r["kirilgan"])
```
```test
def sinama3(f):
    import copy
    try:
        def s(m,k,t,fp,e):return {"model":m,"kosul":k,"tpr":t,"fpr":fp,"eer":e}
        S=[s("B","temiz",0.75,0.25,0.25),s("A","sapi",0.5,0.0,0.5),s("A","temiz",1,0.0,0.0),s("A","gurultu",0.75,0.25,0.125),s("A","ornek",0.0,0.0,0.5),
           s("B","tel",0.25,0.5,0.375),s("C","temiz",0.5,0.5,0.5),s("D","temiz",1.0,0.0,0.1),s("D","x",0.5,0.0,0.1)]
        e=copy.deepcopy(S);r=f(S)
        if S!=e:return False
        if r!={"modeller":{"A":{"temiz":{"tpr":1,"fpr":0.0,"eer":0.0},"kosullar":{"gurultu":{"tpr_dusus":0.25,"fpr_artis":0.25,"eer_artis":0.125},"ornek":{"tpr_dusus":1.0,"fpr_artis":0.0,"eer_artis":0.5},"sapi":{"tpr_dusus":0.5,"fpr_artis":0.0,"eer_artis":0.5}},"kirilan":["ornek"],"en_kotu":"ornek"},
                           "B":{"temiz":{"tpr":0.75,"fpr":0.25,"eer":0.25},"kosullar":{"tel":{"tpr_dusus":0.5,"fpr_artis":0.25,"eer_artis":0.125}},"kirilan":["tel"],"en_kotu":"tel"},
                           "C":{"temiz":{"tpr":0.5,"fpr":0.5,"eer":0.5},"kosullar":{},"kirilan":[],"en_kotu":None},
                           "D":{"temiz":{"tpr":1.0,"fpr":0.0,"eer":0.1},"kosullar":{"x":{"tpr_dusus":0.5,"fpr_artis":0.0,"eer_artis":0.0}},"kirilan":[],"en_kotu":"x"}},"kirilgan":["A","D"]}:return False
        if f(list(reversed(S)))!=r or list(r["modeller"])!=["A","B","C","D"] or list(r["modeller"]["A"]["kosullar"])!=["gurultu","ornek","sapi"]:return False
        if f([s("E","temiz",1.0,0.0,0.11),s("E","y",0.0,0.0,0.5)])["kirilgan"]!=[] or f([s("F","temiz",1.0,0.0,0.0),s("F","y",0.51,0.0,0.0)])["kirilgan"]!=[]:return False
        if f([s("G","temiz",1.0,0.0,0.0),s("G","b",0.2,0.0,0.3),s("G","a",0.9,0.0,0.4)])["modeller"]["G"]["en_kotu"]!="a":return False
        T=lambda **d:[dict(S[0],**d)]+S[1:]
        for bad in (None,[],tuple(S),S[1:4]+S[5:6],S+[S[0]],T(tpr=1.5),T(tpr=float("nan")),S+[s(5,"temiz",1.0,0.0,0.0)],T(fpr=-0.1),T(eer=True),T(tpr="0.5"),T(eer=None),T(model=""),T(model=5),T(kosul=5),T(model=None),[dict(S[3],kosul="")]+S[:3]+S[4:],[dict(S[3],kosul=5)]+S[:3]+S[4:],S+[s("","temiz",1.0,0.0,0.0)],S+[s(None,"temiz",1.0,0.0,0.0)],T(ek=1),[{k:v for k,v in S[0].items() if k!="eer"}]+S[1:],[None]+S):
            try:f(bad);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama3(kosul_raporu),"düşüş/artış, kırılan, en kötü, kırılgan ve geçersiz girdi")
def _katisiz(S):
    r=kosul_raporu(S)
    return dict(r,kirilgan=sorted(m for m,x in r["modeller"].items() if any(v["tpr_dusus"]>=0.5 for v in x["kosullar"].values())))
for ad,mut in [("temiz şartı yok",_katisiz),("en kötü tpr düşüşüne göre",lambda S:dict(kosul_raporu(S),modeller={m:dict(x,en_kotu=max(sorted(x["kosullar"]),key=lambda k:x["kosullar"][k]["tpr_dusus"]) if x["kosullar"] else None) for m,x in kosul_raporu(S)["modeller"].items()})),("kırılan <= 0.5",lambda S:dict(kosul_raporu(S),modeller={m:dict(x,kirilan=sorted(k for k,v in x["kosullar"].items() if x["temiz"]["tpr"]-v["tpr_dusus"]<=0.5)) for m,x in kosul_raporu(S)["modeller"].items()}))]:
    ok(not sinama3(mut),"mutant reddedildi: "+ad)
```
```solution
def kosul_raporu(satirlar):
    if not isinstance(satirlar,list) or not satirlar:raise ValueError("liste")
    tab={}
    for s in satirlar:
        if not isinstance(s,dict) or set(s)!={"model","kosul","tpr","fpr","eer"}:raise ValueError("şema")
        if not isinstance(s["model"],str) or not s["model"] or not isinstance(s["kosul"],str) or not s["kosul"]:raise ValueError("ad")
        if any(type(s[k]) not in (int,float) or not 0<=s[k]<=1 for k in ("tpr","fpr","eer")):raise ValueError("oran")
        if s["kosul"] in tab.setdefault(s["model"],{}):raise ValueError("tekrar")
        tab[s["model"]][s["kosul"]]=s
    if any("temiz" not in k for k in tab.values()):raise ValueError("temiz gerekli")
    out={};kir=[]
    for m in sorted(tab):
        t=tab[m]["temiz"];ks={}
        for k in sorted(tab[m]):
            if k=="temiz":continue
            x=tab[m][k];ks[k]={"tpr_dusus":t["tpr"]-x["tpr"],"fpr_artis":x["fpr"]-t["fpr"],"eer_artis":x["eer"]-t["eer"]}
        en=min(ks,key=lambda k:(-ks[k]["eer_artis"],k)) if ks else None
        out[m]={"temiz":{"tpr":t["tpr"],"fpr":t["fpr"],"eer":t["eer"]},"kosullar":ks,"kirilan":sorted(k for k in ks if tab[m][k]["tpr"]<0.5),"en_kotu":en}
        if t["eer"]<=0.1 and any(v["tpr_dusus"]>=0.5 for v in ks.values()):kir.append(m)
    return {"modeller":out,"kirilgan":kir}

from ai_saldiri_veri import json_yukle
v=json_yukle("veri/ses.json")
r=kosul_raporu(v["satirlar"])
for m,x in r["modeller"].items():print(m,"| temiz:",x["temiz"],"| kırılan:",x["kirilan"],"| en kötü:",x["en_kotu"],"|",x["kosullar"])
print("kırılgan modeller:",r["kirilgan"])
```
```hint
Düşüş temizden koşula doğru hesaplanır. `kirilgan` için iki şart birlikte gerekir: temizde iyi görünmek ve bir koşulda çökmek.
```
:::

::: anlat Hata vitrini · yazar koşusu
Yazar finaldeki deneyi referans işlevlerle çalıştırdı; kayıt `outputs/yeni-ai-saldiri-55/yazar-sondasi.json` dosyasındadır (Piper 1.8.0, onnxruntime 1.31.1, scikit-learn 1.9.1; 30 eğitim / 15 test metni).

- **Mükemmel skor bir kısayoldu.** A modeli temiz testte TPR 1.0 ve EER 0 verdi. Aynı sentetik sesler yalnızca 16 kHz'e yeniden örneklenince TPR **0**'a indi. Saldırgan sesi değiştirmedi; yalnız örnekleme hızını değiştirdi. B modeli (iki sınıf da 16 kHz) bu koşulda TPR 1.0'da kaldı.
- **Eşik kaydı, sıralama kalmadı mı?** A modeli telefon bandında eşik 0.5'te TPR **0** verdi, ama EER yine **0**'dı: skorlar sınıfları hâlâ ayırıyordu, sabit eşik kaymıştı. B aynı koşulda TPR 0.93'te kaldı.
- **Görülmemiş üretici.** SAPI'nin Zira sesi iki modelde de TPR 0 aldı. B modelinin SAPI koşulunda EER'i **0.87** çıktı; yani skor sıralaması rastgeleden de kötüydü ve SAPI sesleri gerçek kayıtlardan daha "gerçek" görüldü. Bu, dedektörün "sentetik ses"i değil "Piper'ın LJSpeech sesi"ni ya da "LibriSpeech'teki o konuşmacı olmayan her şey"i öğrenmiş olabileceğiyle uyumludur. Bu deney ikisini ayıramaz.

Bu sonuçlar neden tek başına güven vermez? Temiz testte kusursuz görünen bir dedektör, saldırganın tek bir dönüşümüyle çökebilir; test kümesi saldırganın değiştirebileceği her şeyi içermelidir. Kendi cümlenle açıkla. Bu kayıt finalin yerine geçmez; final kendi koşusunu ayrıca üretir. Piper'ın çıktısı koşudan koşuya küçük farklar gösterebilir; sayılar değişebilir.
:::

::: anlat Gerçek deney: iki model, beş koşul
Final, onaylı dosyaların sha256'sını doğrular. LibriSpeech alt kümesinden en kısa 45 metni alır ve Piper ile aynı metinleri okutur (45 gerçek sentez). Metinleri senin `grup_bol` işlevin değil bağımsız referans böler (senin çıktın ayrıca karşılaştırılır). Test metinleri için Windows SAPI Zira sesiyle 15 ses daha üretir. Sonra A ve B modellerini yalnız temiz eğitim verisiyle eğitir ve beş koşulda skorlar: 2 model × 5 koşul × 30 test örneği. Kabul şunlara bağlıdır: dört işlevinin gerçek skorlar ve kayıtlarda referansla birebir aynı sonuç vermesi, aynı metnin iki tarafta olmaması, kapsamın (16 kHz tek konuşmacı, 22050 Hz Piper, SAPI Zira) kanıtta yazılı olması. **Dedektörün başarılı olması ya da kırılması kabul şartı değildir**; ölçülen sonuçtur.

**Dedektör ne öğrendi? Konuşmacı kısayolu sondası.** Gerçek sınıfta tek bir konuşmacı olduğu için dedektör "sentetik sesi" değil "bu kişinin sesi olmayanı" öğrenmiş olabilir. Bunu ayırmak için aynı gerçek test kayıtları sentez izi eklemeden yalnız tınısı değiştirilerek verilir: bant hızı 0.85 ve 1.18 kat değiştirilir (perde ve tempo birlikte değişir; ses artık aynı kişiye benzemez). Dedektör tının değişimini "sentetik" sayıyorsa konuşmacıyı öğrenmiştir. Yazarın koşusunda iki model de perdesi kaydırılmış gerçek kayıtların hiçbirini sentetik saymadı. Buna karşılık eğitimde görmediği SAPI Zira sesini de hiç yakalayamadı. İkisi birlikte şunu söyler: dedektör tek konuşmacının tınısını değil, **Piper'a (LJSpeech) özgü bir izi** öğrenmiştir; bu da onu genel bir "sentetik ses" dedektörü yapmaz. Makinede ikinci bir SAPI sesi varsa o da eğitimde görülmemiş bir sentetik ses olarak denenir.

**Kanıt dosyasını oku:** Çalıştır ya da Kontrol Et sonunda kanıt dosyasının yolu yazılır. `satirlar` içinde A ve B'nin `ornekleme_16k` satırlarını karşılaştır. `telefon` satırında `tpr` ile `eer` aynı şeyi mi söylüyor? `sapi` satırında `eer` 0.5'in üstündeyse bu ne demektir? `gercek` alanındaki `konusmaci` değerlerine bak: bu dedektörün "sentetik ses" öğrendiğini nasıl bir ek deneyle sınardın? Cevabını tezgâhta yorum olarak yaz; otomatik test bu serbest açıklamayı puanlamaz.
:::

::: gorev Gerçek deney · Piper, LibriSpeech ve SAPI ile sentetik ses tespiti
Önceki üç görevin `grup_bol`, `esik_metrikleri`, `esit_hata` ve `kosul_raporu` işlevlerini birleştir. Çalıştır gerçek koşul tablosunu gösterir; Kontrol Et önce üç sözleşmeyi gizli verilerle sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
timeout: 300
```
```starter
import ai_lab
import hashlib
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def grup_bol(kayitlar,test_orani):
    adim=round(1/test_orani)
    test=[k["id"] for i,k in enumerate(kayitlar) if i%adim==0]
    return {"egitim":[k["id"] for k in kayitlar if k["id"] not in test],"test":test}

# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def esik_metrikleri(skorlar,etiketler,esik):
    tp=sum(1 for s,e in zip(skorlar,etiketler) if e and s>esik);fp=sum(1 for s,e in zip(skorlar,etiketler) if not e and s>esik)
    n=len(etiketler)
    return {"tpr":tp/n,"fpr":fp/n,"dogruluk":(tp+n-fp)/n}

# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def esit_hata(skorlar,etiketler):
    en=None
    for t in sorted(set(skorlar)):
        m=esik_metrikleri(skorlar,etiketler,t);fpr=m["fpr"];fnr=1-m["tpr"]
        if en is None or fpr+fnr<en[0]:en=(fpr+fnr,{"eer":(fpr+fnr)/2,"esik":t,"fpr":fpr,"fnr":fnr})
    return en[1]

# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def kosul_raporu(satirlar):
    tab={}
    for s in satirlar:tab.setdefault(s["model"],{})[s["kosul"]]=s
    out={};kir=[]
    for m in tab:
        t=tab[m]["temiz"];ks={}
        for k in tab[m]:
            if k=="temiz":continue
            x=tab[m][k];ks[k]={"tpr_dusus":x["tpr"]-t["tpr"],"fpr_artis":x["fpr"]-t["fpr"],"eer_artis":x["eer"]-t["eer"]}
        en=max(ks,key=lambda k:ks[k]["tpr_dusus"]) if ks else None
        out[m]={"temiz":{"tpr":t["tpr"],"fpr":t["fpr"],"eer":t["eer"]},"kosullar":ks,"kirilan":[k for k in ks if tab[m][k]["tpr"]<=0.5],"en_kotu":en}
        if any(v["tpr_dusus"]>=0.5 for v in ks.values()):kir.append(m)
    return {"modeller":out,"kirilgan":kir}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_55 as D
    D.goster(grup_bol,esik_metrikleri,esit_hata,kosul_raporu)
```
```test
import ai_lab
checks=[]
def kontrol(x,m):checks.append(bool(x));ok(x,m)
issues=ai_lab.kod_denetimi(src,("referans_bol","referans_metrik","referans_eer","referans_rapor","kanit_yaz"),izin=())
kontrol(not issues,"kopya/yama/dinamik kod yok: "+str(issues))
if issues:stop()
grup_bol=need("grup_bol");esik_metrikleri=need("esik_metrikleri");esit_hata=need("esit_hata");kosul_raporu=need("kosul_raporu")
def sinama1(f):
    import hashlib,copy
    try:
        H=lambda m:hashlib.sha256(m.encode("utf-8")).hexdigest()
        def kk(ms):
            r=[]
            for i,m in enumerate(ms):r+=[{"id":f"g{i}","metin":m,"kaynak":"gercek"},{"id":f"s{i}","metin":m,"kaynak":"sentetik"}]
            return r
        def bek(K,n):
            sira=sorted({k["metin"] for k in K},key=H);t=set(sira[:n])
            return {"egitim":sorted(k["id"] for k in K if k["metin"] not in t),"test":sorted(k["id"] for k in K if k["metin"] in t)}
        M=["çay saati","kuzey rüzgârı","ship at dawn","old door","quiet town","short letter"]
        K=kk(M);e=copy.deepcopy(K);r=f(K,0.34)
        if K!=e or r!=bek(K,2) or f(list(reversed(K)),0.34)!=r:return False
        if f(K,0.5)!=bek(K,3) or f(K,0.2)!=bek(K,1) or f(K,0.75)!=bek(K,4):return False
        K10=kk([f"metin {i}" for i in range(10)])
        K4=kk(["p","q","r","s"])
        if f(K10,0.25)!=bek(K10,2) or f(K10,0.75)!=bek(K10,8) or f(K4,0.375)!=bek(K4,2) or f(K4,0.625)!=bek(K4,2):return False
        if any(set(r["egitim"])&set(r["test"]) for r in (f(K,0.5),f(K10,0.25))):return False
        T3=kk(["a1","b2","c3"])
        for o in (0.1,0.9):
            try:f(T3,o);return False
            except ValueError:pass
        sira=sorted(M,key=H);Y=[k for k in kk(M) if not (k["metin"]==sira[0] and k["kaynak"]=="sentetik")]
        try:f(Y,0.2);return False
        except ValueError:pass
        Z=[k for k in kk(M) if not (k["metin"]==sira[-1] and k["kaynak"]=="sentetik")]
        if f(Z,0.2)!=bek(Z,1):return False
        Z2=[k for k in kk(M) if not (k["metin"]!=sira[0] and k["kaynak"]=="gercek")]
        try:f(Z2,0.2);return False
        except ValueError:pass
        T=lambda **d:[dict(K[0],**d)]+K[1:]
        for bad,o in ((K,0),(K,1),(K,True),(K,"0.3"),(K,None),(K,-0.2),(K,float("inf")),(K,float("nan")),(None,0.3),([],0.3),(tuple(K),0.3),(K+[K[0]],0.3),(T(id=""),0.3),(T(id=3),0.3),
                      (T(metin=""),0.3),(T(metin=None),0.3),(T(metin=123),0.3),(T(kaynak="x"),0.3),(T(ek=1),0.3),([{"id":"q","metin":"m"}]+K[1:],0.3),([None]+K,0.3)):
            try:f(bad,o);return False
            except ValueError:pass
        return True
    except Exception:return False
def sinama2(m,eer):
    import copy
    try:
        S=[0.9,0.2,0.6,0.4];E=[1,0,1,0];s0=list(S)
        if m(S,E,0.5)!={"tpr":1.0,"fpr":0.0,"dogruluk":1.0} or S!=s0:return False
        if m(S,E,0.6)!={"tpr":1.0,"fpr":0.0,"dogruluk":1.0} or m(S,E,0.61)!={"tpr":0.5,"fpr":0.0,"dogruluk":0.75} or m(S,E,0.4)!={"tpr":1.0,"fpr":0.5,"dogruluk":0.75}:return False
        if m([0.8,0.7,0.3,0.6,0.1],[1,0,0,0,1],0.5)!={"tpr":0.5,"fpr":2/3,"dogruluk":0.4} or m([1,0],[1,0],1)!={"tpr":1.0,"fpr":0.0,"dogruluk":1.0}:return False
        if eer([0,1,2],[0,1,0])!={"eer":0.25,"esik":1,"fpr":0.5,"fnr":0.0}:return False
        if eer([0.9,0.8,0.7,0.6],[1,0,1,0])!={"eer":0.5,"esik":0.8,"fpr":0.5,"fnr":0.5}:return False
        if eer([0.9,0.1,0.8,0.2],[1,0,1,0])!={"eer":0.0,"esik":0.8,"fpr":0.0,"fnr":0.0}:return False
        if eer([0.9,0.5,0.1],[1,0,1])!={"eer":0.25,"esik":0.9,"fpr":0.0,"fnr":0.5}:return False
        if eer([0.3,0.3,0.7,0.7],[0,1,0,1])!={"eer":0.5,"esik":0.7,"fpr":0.5,"fnr":0.5}:return False
        if eer([0.6,0.2,0.4],[1,0,0])!={"eer":0.0,"esik":0.6,"fpr":0.0,"fnr":0.0}:return False
        for bad in (([0.1],[1]),([0.1,0.2],[1,1]),([0.1,0.2],[0,0]),([0.1],[1,0]),([],[]),([0.1,0.2],[1,2]),([0.1,0.2],[1,True]),([0.1,0.2,0.3],[1,0,True]),([0.1,"0.2"],[1,0]),([0.1,True],[1,0]),((0.1,0.2),[1,0]),([0.1,0.2],(1,0)),([0.1,None],[1,0])):
            for fn,a in ((m,bad+(0.5,)),(eer,bad)):
                try:fn(*a);return False
                except ValueError:pass
        for es in ("0.5",None,True):
            try:m([0.1,0.2],[1,0],es);return False
            except ValueError:pass
        return True
    except Exception:return False
def sinama3(f):
    import copy
    try:
        def s(m,k,t,fp,e):return {"model":m,"kosul":k,"tpr":t,"fpr":fp,"eer":e}
        S=[s("B","temiz",0.75,0.25,0.25),s("A","sapi",0.5,0.0,0.5),s("A","temiz",1,0.0,0.0),s("A","gurultu",0.75,0.25,0.125),s("A","ornek",0.0,0.0,0.5),
           s("B","tel",0.25,0.5,0.375),s("C","temiz",0.5,0.5,0.5),s("D","temiz",1.0,0.0,0.1),s("D","x",0.5,0.0,0.1)]
        e=copy.deepcopy(S);r=f(S)
        if S!=e:return False
        if r!={"modeller":{"A":{"temiz":{"tpr":1,"fpr":0.0,"eer":0.0},"kosullar":{"gurultu":{"tpr_dusus":0.25,"fpr_artis":0.25,"eer_artis":0.125},"ornek":{"tpr_dusus":1.0,"fpr_artis":0.0,"eer_artis":0.5},"sapi":{"tpr_dusus":0.5,"fpr_artis":0.0,"eer_artis":0.5}},"kirilan":["ornek"],"en_kotu":"ornek"},
                           "B":{"temiz":{"tpr":0.75,"fpr":0.25,"eer":0.25},"kosullar":{"tel":{"tpr_dusus":0.5,"fpr_artis":0.25,"eer_artis":0.125}},"kirilan":["tel"],"en_kotu":"tel"},
                           "C":{"temiz":{"tpr":0.5,"fpr":0.5,"eer":0.5},"kosullar":{},"kirilan":[],"en_kotu":None},
                           "D":{"temiz":{"tpr":1.0,"fpr":0.0,"eer":0.1},"kosullar":{"x":{"tpr_dusus":0.5,"fpr_artis":0.0,"eer_artis":0.0}},"kirilan":[],"en_kotu":"x"}},"kirilgan":["A","D"]}:return False
        if f(list(reversed(S)))!=r or list(r["modeller"])!=["A","B","C","D"] or list(r["modeller"]["A"]["kosullar"])!=["gurultu","ornek","sapi"]:return False
        if f([s("E","temiz",1.0,0.0,0.11),s("E","y",0.0,0.0,0.5)])["kirilgan"]!=[] or f([s("F","temiz",1.0,0.0,0.0),s("F","y",0.51,0.0,0.0)])["kirilgan"]!=[]:return False
        if f([s("G","temiz",1.0,0.0,0.0),s("G","b",0.2,0.0,0.3),s("G","a",0.9,0.0,0.4)])["modeller"]["G"]["en_kotu"]!="a":return False
        T=lambda **d:[dict(S[0],**d)]+S[1:]
        for bad in (None,[],tuple(S),S[1:4]+S[5:6],S+[S[0]],T(tpr=1.5),T(tpr=float("nan")),S+[s(5,"temiz",1.0,0.0,0.0)],T(fpr=-0.1),T(eer=True),T(tpr="0.5"),T(eer=None),T(model=""),T(model=5),T(kosul=5),T(model=None),[dict(S[3],kosul="")]+S[:3]+S[4:],[dict(S[3],kosul=5)]+S[:3]+S[4:],S+[s("","temiz",1.0,0.0,0.0)],S+[s(None,"temiz",1.0,0.0,0.0)],T(ek=1),[{k:v for k,v in S[0].items() if k!="eer"}]+S[1:],[None]+S):
            try:f(bad);return False
            except ValueError:pass
        return True
    except Exception:return False
kontrol(sinama1(grup_bol),"metin grubu bölmesi, hash sırası, iki kaynak")
kontrol(sinama2(esik_metrikleri,esit_hata),"eşik metrikleri ve EER")
kontrol(sinama3(kosul_raporu),"koşul raporu ve kırılganlık")
for ad,mut in [("bir test kaydı eğitime sızıyor",lambda K,o:dict(grup_bol(K,o),egitim=sorted(grup_bol(K,o)["egitim"]+grup_bol(K,o)["test"][:1]))),("eğitim/test yer değiştirdi",lambda K,o:{"egitim":grup_bol(K,o)["test"],"test":grup_bol(K,o)["egitim"]}),("sırasız",lambda K,o:{a:list(reversed(b)) for a,b in grup_bol(K,o).items()})]:
    kontrol(not sinama1(mut),"mutant reddedildi: "+ad)
def _toplam(S,E):
    r=esit_hata(S,E);en=None
    for t in sorted(set(S)):
        m=esik_metrikleri(S,E,t);a=(m["fpr"]+1-m["tpr"],t)
        if en is None or a<en[0]:en=(a,{"eer":a[0]/2,"esik":t,"fpr":m["fpr"],"fnr":1-m["tpr"]})
    return en[1] if r else r
for ad,mm,ee in [("katı eşik",lambda S,E,t:esik_metrikleri(S,E,t+1e-9),esit_hata),("toplam hatayı küçült",esik_metrikleri,_toplam),("fpr paydası tüm örnekler",lambda S,E,t:dict(esik_metrikleri(S,E,t),fpr=esik_metrikleri(S,E,t)["fpr"]*(len(E)-sum(E))/len(E)),esit_hata)]:
    kontrol(not sinama2(mm,ee),"mutant reddedildi: "+ad)
def _katisiz(S):
    r=kosul_raporu(S)
    return dict(r,kirilgan=sorted(m for m,x in r["modeller"].items() if any(v["tpr_dusus"]>=0.5 for v in x["kosullar"].values())))
for ad,mut in [("temiz şartı yok",_katisiz),("en kötü tpr düşüşüne göre",lambda S:dict(kosul_raporu(S),modeller={m:dict(x,en_kotu=max(sorted(x["kosullar"]),key=lambda k:x["kosullar"][k]["tpr_dusus"]) if x["kosullar"] else None) for m,x in kosul_raporu(S)["modeller"].items()})),("kırılan <= 0.5",lambda S:dict(kosul_raporu(S),modeller={m:dict(x,kirilan=sorted(k for k,v in x["kosullar"].items() if x["temiz"]["tpr"]-v["tpr_dusus"]<=0.5)) for m,x in kosul_raporu(S)["modeller"].items()}))]:
    kontrol(not sinama3(mut),"mutant reddedildi: "+ad)
if not all(checks):stop()
from sandbox import ai_gercek_ai_saldiri_55 as D
try:r=D.deney(grup_bol,esik_metrikleri,esit_hata,kosul_raporu)
except ai_lab.GercekLabYok as e:
    kontrol(False,"gerçek deney yok: "+str(e));stop()
kontrol(r["bol"]==r["bol_referans"],"gerçek 90 kaydın bölmesi referansla aynı")
kontrol(r["metrik"]==r["metrik_referans"] and r["eer"]==r["eer_referans"],"10 model×koşul için eşik metrikleri ve EER referansla aynı")
kontrol(r["rapor"]==r["rapor_referans"],"gerçek koşul raporu referansla aynı")
B=r["bol_referans"];M={k["id"]:k["metin"] for k in r["kayitlar"]}
kontrol(len(r["kayitlar"])==90 and not ({M[i] for i in B["egitim"]}&{M[i] for i in B["test"]}) and r["egitim_metin"]==30 and r["test_metin"]==15,"45 metin, 30 eğitim / 15 test, aynı metin iki tarafta yok")
kontrol(all(g["hz"]==16000 and g["konusmaci"]==1272 for g in r["gercek"]) and r["sentetik_hz"]==[22050] and r["sapi_sesi"]=="Microsoft Zira Desktop","gerçek ses 16 kHz tek konuşmacı, Piper 22050 Hz, SAPI Zira; kapsam kanıtta")
kontrol(len(r["skorlar"])==10 and all(len(s["skorlar"])==30 and s["etiketler"].count(1)==15 for s in r["skorlar"]),"2 model × 5 koşul, her biri 15 gerçek + 15 sentetik gerçek skor")
kontrol(r["konusmaci_sondasi_metrik_ayni"] and r["piper_izi_ogrenildi"],"konuşmacı sondası: perdesi kaydırılmış gerçek sesler gerçek kaldı, görülmemiş SAPI sesi yakalanmadı; dedektör Piper izini öğrendi: "+str(r["konusmaci_sondasi"]))
ai_lab.kanit_yaz("saldiri55-kabul",{"kaynak":"gercek","kabul":all(checks),"ders":"ai-saldiri-55","deney":r})
```
```solution
import ai_lab
import hashlib
def grup_bol(kayitlar,test_orani):
    if type(test_orani) not in (int,float) or not 0<test_orani<1:raise ValueError("oran")
    if not isinstance(kayitlar,list) or not kayitlar:raise ValueError("liste")
    ids=set()
    for k in kayitlar:
        if not isinstance(k,dict) or set(k)!={"id","metin","kaynak"}:raise ValueError("şema")
        if not isinstance(k["id"],str) or not k["id"] or k["id"] in ids:raise ValueError("id")
        if not isinstance(k["metin"],str) or not k["metin"] or k["kaynak"] not in ("gercek","sentetik"):raise ValueError("alan")
        ids.add(k["id"])
    gruplar=sorted({k["metin"] for k in kayitlar},key=lambda m:hashlib.sha256(m.encode("utf-8")).hexdigest())
    n=round(len(gruplar)*test_orani)
    if not 1<=n<len(gruplar):raise ValueError("bölünemez")
    test=set(gruplar[:n])
    b={"egitim":sorted(k["id"] for k in kayitlar if k["metin"] not in test),"test":sorted(k["id"] for k in kayitlar if k["metin"] in test)}
    for ad in b:
        if {k["kaynak"] for k in kayitlar if k["id"] in b[ad]}!={"gercek","sentetik"}:raise ValueError("iki kaynak da gerekli")
    return b

def _dogrula(skorlar,etiketler):
    if not isinstance(skorlar,list) or not isinstance(etiketler,list) or not skorlar or len(skorlar)!=len(etiketler):raise ValueError("liste")
    if any(type(s) not in (int,float) for s in skorlar) or any(type(e) is not int or e not in (0,1) for e in etiketler):raise ValueError("değer")
    if set(etiketler)!={0,1}:raise ValueError("iki sınıf")

def esik_metrikleri(skorlar,etiketler,esik):
    _dogrula(skorlar,etiketler)
    if type(esik) not in (int,float):raise ValueError("eşik")
    P=sum(etiketler);N=len(etiketler)-P
    tp=sum(1 for s,e in zip(skorlar,etiketler) if e and s>=esik);fp=sum(1 for s,e in zip(skorlar,etiketler) if not e and s>=esik)
    return {"tpr":tp/P,"fpr":fp/N,"dogruluk":(tp+N-fp)/len(etiketler)}

def esit_hata(skorlar,etiketler):
    _dogrula(skorlar,etiketler)
    en=None
    for t in sorted(set(skorlar)):
        m=esik_metrikleri(skorlar,etiketler,t);fpr=m["fpr"];fnr=1-m["tpr"]
        a=(abs(fpr-fnr),fpr+fnr,t)
        if en is None or a<en[0]:en=(a,{"eer":(fpr+fnr)/2,"esik":t,"fpr":fpr,"fnr":fnr})
    return en[1]

def kosul_raporu(satirlar):
    if not isinstance(satirlar,list) or not satirlar:raise ValueError("liste")
    tab={}
    for s in satirlar:
        if not isinstance(s,dict) or set(s)!={"model","kosul","tpr","fpr","eer"}:raise ValueError("şema")
        if not isinstance(s["model"],str) or not s["model"] or not isinstance(s["kosul"],str) or not s["kosul"]:raise ValueError("ad")
        if any(type(s[k]) not in (int,float) or not 0<=s[k]<=1 for k in ("tpr","fpr","eer")):raise ValueError("oran")
        if s["kosul"] in tab.setdefault(s["model"],{}):raise ValueError("tekrar")
        tab[s["model"]][s["kosul"]]=s
    if any("temiz" not in k for k in tab.values()):raise ValueError("temiz gerekli")
    out={};kir=[]
    for m in sorted(tab):
        t=tab[m]["temiz"];ks={}
        for k in sorted(tab[m]):
            if k=="temiz":continue
            x=tab[m][k];ks[k]={"tpr_dusus":t["tpr"]-x["tpr"],"fpr_artis":x["fpr"]-t["fpr"],"eer_artis":x["eer"]-t["eer"]}
        en=min(ks,key=lambda k:(-ks[k]["eer_artis"],k)) if ks else None
        out[m]={"temiz":{"tpr":t["tpr"],"fpr":t["fpr"],"eer":t["eer"]},"kosullar":ks,"kirilan":sorted(k for k in ks if tab[m][k]["tpr"]<0.5),"en_kotu":en}
        if t["eer"]<=0.1 and any(v["tpr_dusus"]>=0.5 for v in ks.values()):kir.append(m)
    return {"modeller":out,"kirilgan":kir}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_55 as D
    D.goster(grup_bol,esik_metrikleri,esit_hata,kosul_raporu)
```
```hint
Dört işlevi aynen birleştir. Tabloyu okurken eşikte TPR ile EER'i ve "kırılan" ile "kırılgan"ı karıştırma.
```
:::

::: anlat Sınır
Bu ders tek gerçek konuşmacı (LibriSpeech dummy, speaker 1272), tek Piper sesi (LJSpeech) ve tek SAPI sesiyle, 45 kısa metin üzerinde basit spektral özellikler ve lojistik regresyonla bir kısayolu, bir kalibrasyon kaymasını ve görülmemiş üreticiye genellemeyi ölçer; dedektörün konuşmacı kimliğini öğrenip öğrenmediğini ayıramaz ve genel deepfake ya da ses klonlama tespit başarısını göstermez.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
### Dedektör sesi mi, kaynağın izini mi öğreniyor?

Metne göre bölme aynı cümlenin iki tarafı kirletmesini engeller; konuşmacı ayrımını engellemez. Tek gerçek konuşmacı ile tek Piper sesi arasındaki başarı spektral kaynak farkından gelebilir. Eşit örnekleme oranlı ikinci model bu kolay ipucunu denetler; gürültü, telefon ve SAPI koşulları başka dağılımları sorgular. Bu derste EER ayrık gözlenen eşiklerde en yakın hata dengesidir; sürekli ROC interpolasyonu değildir.

| Yaygın yanlış | Doğru sınır |
|---|---|
| Temiz doğruluk bütün TTS türlerini kapsar | Kaynak/konuşmacı etkisi ve görülmemiş üretici ayrı ölçülür. |

Sonraki bağlantı: ai-savunma-33. [Birincil kaynak](https://arxiv.org/abs/1911.01601). Kaynak mekanizmanın ilgili API veya yöntemini açıklar; bu labın başarı oranının kanıtı yerel ham koşudur.
:::
