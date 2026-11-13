---
id: ai-savunma-39
title: Unlearning Doğrulaması · Yanlış Cevap Vermek Unutmak mı?
summary: Gerçek torch modelinde approximate unlearning sonucunu retain-only retrain ve unchanged kontrolleriyle karşılaştır.
esleme: ai-saldiri-48; ai-savunma-33; ai-guvence-07
timeout: 240
---

::: anlat Kayıp arttı diye silinme kanıtlanmaz
| Parça | Gerçek araç | Ölçüm |
|---|---|---|
| Eğitim | Kurulu torch CPU, 24 parametreli Linear(12, 2) | Full ve retain-only 120 adım |
| Unlearning | Gerçek autograd, retain loss − alpha × forget loss | 50 adım, gradient normu / ağırlık hashi |
| Karşılaştırma | Gerçek softmax posteriorları | Accuracy, NLL, retrain TV farkı |
| Görünür veri | unlearning/ornek.json | Sentetik çalışma örneği |

> [!NOT]
> Bu bir pretrained LLM değildir. Sıfırdan eğitilen, 12 sentetik one-hot kimliği iki sınıfa ayıran küçük bir modeldir. Yeni model/paket indirilmez. Sonuç, kişisel verinin matematiksel olarak silindiği garantisi değildir.

Unlearning görevinde hedef, seçilen eğitim kayıtlarının etkisini kaldırırken kalan görevi korumaktır. Bir modelin daha çok yanlış cevap vermesi bu hedefi tek başına karşılamaz. Bütün ağırlıkları rastgele yaparsan forget accuracy düşer; ama retain tarafı da bozulabilir. Ters yönde çok güçlü eğitim yaparsan model, unutulacak örneğe eskisinden daha kararlı biçimde yanlış sınıf verebilir. Bu davranış, o örneği hiç görmemiş bir modelin belirsiz cevabıyla aynı değildir. İşte bu dersin merkezi sorusu budur: yanlış cevap ile unutulmuş etkiyi hangi ölçümler ayırır?

Önce unlearning/ornek.json dosyasını aç. İlk görevde dosyanın ids ve forget alanlarını kullanarak ayrımı yazdır; dosyada bir kimliği değiştirip sonucu tekrar oku. Çalışma kopyası her çağrıda geçici klasörde yeniden hazırlanır. Değişikliğin sonraki çalıştırmaya kalacağı söylenmez. Gerçek eğitimde kullanılacak kimlikler görünür örnekten farklıdır; gizli testi dosya düzenleyerek değiştiremezsin. Gerçek giriş matrisleri, etiketler, ayrım listeleri ve posteriorlar kanıt dosyasında bulunur. Böylece fixture üzerinde biçim öğrenmek ile gerçek model üzerinde ölçüm yapmak birbirinden ayrılır.

Veri ayrımı tam ve ayrık olmalı. Her kaynak kimliği retain ya da forget içinde tam bir kez bulunur; iki listede birden bulunamaz. Kaynak sırası korunur. Boş forget veya bütün veriyi forget yapmak bu deneyin kapsamı dışında olduğu için hata verir. Bu yalnız bir liste işlemi değildir: yanlış ayrım, retrain modelinin unutulacak veriyi tekrar görmesine yol açar. Sonra modelin aynı bilgiyi üretmesine bakıp yöntemi başarısız veya başarılı ilan etmen anlamsızlaşır. Gerçek deney retrain eğitim kimliklerini ayrıca kaydeder; forget ile kesişimin boş olduğunu ölçer.

Full model 12 kimlikle eğitilir. Retrain modeli aynı sıfır başlangıçtan yalnız 8 retain kimliğiyle eğitilir. Approximate unlearning modeli full modelin kopyasıdır; 50 güncellemede retain cross-entropy azaltılırken forget cross-entropy artırılır. Bu ders gradient-ascent temelli yöntemi en iyi yöntem diye önermez. Tam tersine, ölçümün neden dikkatli yapılması gerektiğini gösteren küçük bir karşılaştırma kurar. Unchanged kontrolü full modelin hiç güncellenmemiş kopyasıdır. Unchanged hash'i full ile aynı değilse kontrol deneyi bozulmuştur. Unlearn hash'i değişmediyse gerçek güncelleme yapılmamıştır. İki durum da kabul edilmez.

Öğrencinin kayip_birlestir fonksiyonu minimize edilecek skaler objective'i hesaplar: retain_loss − alpha × forget_loss. Torch tarafı aynı objective'i tensorlarla kurup gerçekten backward ve optimizer.step yapar; saf fonksiyondaki float hesabı gradient grafiğinin yerine geçmez. Her adımda öğrenci hesabı gerçek objective ile karşılaştırılır ve gradient normu kaydedilir. Burada 50 adım yapılması, 50 adımın herhangi bir üretim modeli için yeterli olacağı anlamına gelmez. Learning rate ve alpha laboratuvar ayarıdır; genel başarı garantisi değildir. Alpha 0 ile forget gradient etkisi yok olur; alpha 1 de sözleşmeye dahildir. Negatif/sonsuz/NaN değerler ölçümü bozduğu için reddedilir.

Accuracy sınıf kararını, NLL doğru sınıfa verilen olasılığı ölçer. Aynı accuracy'ye sahip iki modelin olasılık dağılımları farklı olabilir. Bu nedenle unlearn ile retrain arasında iki sınıflı posteriorların TV farkını da hesaplarsın: iki mutlak farkın toplamı bölü 2. Bu örnek başına farkın grup ortalamasıdır. Doğal log kullanılır; doğru sınıf olasılığı 0 ise log tanımsızlığını önlemek için 1e-12 alt sınırı uygulanır ve bu sınır açıkça belirtilir. Tie durumunda ilk sınıf seçilir. Retain veya forget grubu ölçümde yoksa sıfır uydurmak yerine None döndürülür. Gerçek deney her iki grubu da içerir.

**One-hot sınırını gradient'ten türet.** Bias olmayan $z=W x$ sınıflandırıcısında, cross-entropy için $\partial\ell/\partial W_{j,k}=(p_j-\mathbf{1}[j=y])x_k$ olur. Girdi kimlik $k$'nın one-hot vektörüyse diğer sütunların gradient'i sıfırdır. Ayrık retain ve forget kimlikleri bu yüzden farklı parametre sütunlarına dokunur; dil modelinde paylaşılan temsil böyle ayrışmaz. Sıfır başlangıçlı retain-only retrain, hiç görmediği forget sütunlarını sıfırda bırakır ve iki sınıfa $[0.5,0.5]$ verir. Gradient ascent ile doğru sınıf olasılığını 0.001'e itmek ise bu referanstan TV=0.499 uzağa götürür. Dolayısıyla forget NLL yükselirken retrain yakınlığı kötüleşebilir; retain yararının korunması da bu mimarideki ayrışmanın sonucu olabilir.

Modelin girdi temsili bilerek basittir: her kimliğin bağımsız bir one-hot sütunu vardır, bias yoktur. Bu yüzden retain ve forget etkileşimi gerçek dil modellerindeki gibi karmaşık değildir. Eğitimde başlangıç sıfır olduğundan iki seed aynı öğrenme dinamiğini tekrarlar; seed çeşitliliği iddiası yoktur. Bu bir tekrarlanabilirlik kontrolüdür. Ağırlıklar .pt olarak kaydedilir; weights_only ile yeniden okunup canlı tensorlarla eşitliği doğrulanır. Kurulu araç yoksa gerçek deney yapılamaz ve PASS sayılmaz. Kullanıcı kurulumları veya öğrenci verileri silinmez; yalnız CPU nesneleri kullanılır.

Kaynak: [Machine Unlearning of Pre-trained Large Language Models, ACL 2024](https://aclanthology.org/2024.acl-long.457/) gradient-ascent ve retain hedeflerini araştırır; buradaki 24 parametreli sınıflandırıcı o çalışmanın LLM benchmark'ı veya yeniden üretimi değildir. Bu dersin sayıları yalnız kendi koşundan gelir. ai-saldiri-48 ile eğitim verisi etkisini ölçmenin neden zor olduğunu; ai-savunma-33 ile ret eğitiminin silinme kanıtından neden farklı olduğunu karşılaştır. Kanıttaki forget accuracy, retain accuracy ve retrain TV farkını birlikte yorumlamadan “unlearning başarılı” diye yazma.
:::

::: gorev 1 · Retain ve forget ayrımını doğrula
ids benzersiz, boş olmayan string listesi; forget benzersiz, boş olmayan gerçek altküme listesi. Retain de boş kalamaz. Kaynak sırasında retain/forget dict döndür; bozuk girdi ValueError.
KUSURLU başlangıcın neden yanlış güven verdiğini teşhis et.

```starter
def veri_bol(ids,forget):
    return {"retain":ids,"forget":forget}
```

```solution
def veri_bol(ids,forget):
    if not isinstance(ids,list) or any(not isinstance(x,str) or not x for x in ids) or len(set(ids))!=len(ids):raise ValueError('ids')
    if not isinstance(forget,list) or not forget or any(not isinstance(x,str) or x not in ids for x in forget) or len(set(forget))!=len(forget) or len(forget)==len(ids):raise ValueError('forget')
    return {'retain':[x for x in ids if x not in forget],'forget':[x for x in ids if x in forget]}
```

```test
need('veri_bol')
from collections import UserString
raises(ValueError,veri_bol,['a','b'],[UserString('a')],msg='str ile eşit karşılaştırılan UserString yine str değildir')
for ids,f in [(('a','b'),['a']),([1,'b'],['b']),(['','b'],['b'])]:
    raises(ValueError,veri_bol,ids,f,msg='geçerli forget bozuk ids listesini meşrulaştırmaz')
for ids,forget in [(['a','b','c'],['c','a']),(['z','q'],['z']),(['b','c','a','d'],['a','c'])]:
    eq(veri_bol(ids,forget),{'retain':[i for i in ids if i not in forget],'forget':[i for i in ids if i in forget]},'ayrık birleşim ve kaynak sırası')
for ids,f in [([],['a']),([''],['']),([1,'b'],[1]),(['a','a','b'],['a']),(['a','b'],[]),(['a','b'],['a','b']),(['a','b'],['x']),(['a','b'],['a','a']),(['a','b','c'],['a','a']),(['a','b'],('a',))]:raises(ValueError,veri_bol,ids,f,msg='ayrım şema/sınır')

```

```setup
import sys,importlib
from pathlib import Path
_root=Path(sys.modules["__main__"].__file__).resolve().parents[1]
sys.path.insert(0,str(_root))
if 'ai_lab' not in sys.modules:sys.modules['ai_lab']=importlib.import_module('sandbox.ai_gercek_lab')
from sandbox.ai_gercek_ai_savunma_39 import hazirla
hazirla()

```

```hint
ids benzersiz, boş olmayan string listesi; forget benzersiz, boş olmayan gerçek altküme listesi. Retain de boş kalamaz. Kaynak sırasında retain/forget dict döndür; bozuk girdi ValueError.
```
:::

::: gorev 2 · Gradient işaretini doğru kur
Üç girdi sonlu int/float, bool değil. Loss değerleri ≥ 0, alpha [0, 1]. retain_loss-alpha*forget_loss döndür; bozuk girdi ValueError.
KUSURLU başlangıcın neden yanlış güven verdiğini teşhis et.

```starter
def kayip_birlestir(retain_loss,forget_loss,alpha):
    return retain_loss+alpha*forget_loss
```

```solution
def kayip_birlestir(retain_loss,forget_loss,alpha):
    import math
    for x in (retain_loss,forget_loss,alpha):
        if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x):raise ValueError('sayi')
    if retain_loss<0 or forget_loss<0 or not 0<=alpha<=1:raise ValueError('aralik')
    return retain_loss-alpha*forget_loss
```

```test
need('kayip_birlestir')
for r,f,a in [(0,0,0),(0.2,1.4,0.5),(1,0,1),(0,1,1),(0.8,0.4,0)]:eq(kayip_birlestir(r,f,a),r-a*f,'minimize retain-alpha*forget; sınırlar dahil')
for r,f,a in [(-0.1,1,0.5),(1,-0.1,0.5),(1,1,-0.1),(1,1,1.01),(True,1,0.5),(1,False,0.5),(1,1,True),(float('nan'),1,0.5),(1,float('inf'),0.5),(1,1,'0.5')]:raises(ValueError,kayip_birlestir,r,f,a,msg='sonlu sayısal loss/alpha')

```

```setup
import sys,importlib
from pathlib import Path
_root=Path(sys.modules["__main__"].__file__).resolve().parents[1]
sys.path.insert(0,str(_root))
if 'ai_lab' not in sys.modules:sys.modules['ai_lab']=importlib.import_module('sandbox.ai_gercek_lab')
from sandbox.ai_gercek_ai_savunma_39 import hazirla
hazirla()

```

```hint
Üç girdi sonlu int/float, bool değil. Loss değerleri ≥ 0, alpha [0, 1]. retain_loss-alpha*forget_loss döndür; bozuk girdi ValueError.
```
:::

::: gorev 3 · Posteriorları retrain ile karşılaştır
rows boş olmayan liste; her dict tam id/grup/y/full/unlearn/retrain şeması. id benzersiz boş olmayan string, grup retain/forget, y int 0/1 (bool değil). Posteriorlar iki sonlu sayısal [0, 1] listesi, toplam 1 tolerans 1e-6. Her grup için n, her modelin acc/nll değeri, unlearn_retrain_tv döndür; olmayan grup None. Tie 0, log clamp 1e-12; yanlış şema ValueError.
KUSURLU başlangıcın neden yanlış güven verdiğini teşhis et.

```starter
def posterior_raporu(rows):
    return {"retain":None,"forget":None}
```

```solution
def posterior_raporu(rows):
    import math
    if not isinstance(rows,list) or not rows:raise ValueError('liste')
    seen=set()
    for r in rows:
        if not isinstance(r,dict) or set(r)!={'id','grup','y','full','unlearn','retrain'} or not isinstance(r['id'],str) or not r['id'] or r['id'] in seen or r['grup'] not in ('retain','forget') or type(r['y']) is not int or r['y'] not in (0,1):raise ValueError('sema')
        seen.add(r['id'])
        for name in ('full','unlearn','retrain'):
            p=r[name]
            if not isinstance(p,list) or len(p)!=2 or any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or not 0<=x<=1 for x in p) or abs(sum(p)-1)>1e-6:raise ValueError('posterior')
    out={}
    for group in ('retain','forget'):
        a=[r for r in rows if r['grup']==group]
        if not a:out[group]=None;continue
        stats={'n':len(a)}
        for name in ('full','unlearn','retrain'):
            stats[name+'_acc']=sum((0 if r[name][0]>=r[name][1] else 1)==r['y'] for r in a)/len(a)
            stats[name+'_nll']=sum(-math.log(max(r[name][r['y']],1e-12)) for r in a)/len(a)
        stats['unlearn_retrain_tv']=sum(sum(abs(x-y) for x,y in zip(r['unlearn'],r['retrain']))/2 for r in a)/len(a)
        out[group]=stats
    return out
```

```test
need('posterior_raporu')
import math,copy
base={'id':'x','grup':'forget','y':0,'full':[0.9,0.1],'unlearn':[0.1,0.9],'retrain':[0.5,0.5]}
r=posterior_raporu([base]);eq(r['retain'],None,'olmayan grup ölçülmedi')
for n,v in [('full_acc',1.0),('unlearn_acc',0.0),('retrain_acc',1.0),('unlearn_retrain_tv',0.4)]:eq(r['forget'][n],v,'tie0 ve posterior farkı')
for n,p in [('full',0.9),('unlearn',0.1),('retrain',0.5)]:eq(r['forget'][n+'_nll'],-math.log(p),'NLL doğal log')
other=dict(base,id='y',grup='retain',y=1,full=[0,1],unlearn=[1,0],retrain=[1,0]);r=posterior_raporu([other]);eq(r['forget'],None,'forget yoksa None');eq(r['retain']['unlearn_nll'],-math.log(1e-12),'log0 clamp');eq(r['retain']['unlearn_retrain_tv'],0.0,'eşit dağılımlar')
mixed=posterior_raporu([base,dict(base,id='q',full=[0.2,0.8],unlearn=[0.6,0.4],retrain=[0.3,0.7])]);eq(mixed['forget']['full_acc'],0.5,'ortalama');eq(mixed['forget']['unlearn_acc'],0.5,'ortalama');eq(mixed['forget']['n'],2,'örnek sayısı')
for bad in ([],[None],[base,base],[dict(base,id='')],[dict(base,y=True)],[dict(base,grup='other')],[dict(base,extra=1)],[dict(base,unlearn=[0.5,0.4])],[dict(base,full=[-0.1,1.1])],[dict(base,full=[-5e-7,1.0])],[dict(base,retrain=[True,0])],[dict(base,full=[float('nan'),0])],[dict(base,full=[1])]):raises(ValueError,posterior_raporu,bad,msg='tam şema/sonlu olasılık/simplex')
tol=dict(base,id='tol',full=[0.5,0.5000015])
raises(ValueError,posterior_raporu,[tol],msg='simplex toleransı dışı')
eq(posterior_raporu([dict(base,id='tol',full=[0.5,0.5000005])])['forget']['n'],1,'simplex toleransı içi')
for bad in ([dict(base,id=1)],[dict(base,full=(0.9,0.1))],[dict(base,y=2)],[dict(base,full=[0.5,'0.5'])],tuple([base])):
    raises(ValueError,posterior_raporu,bad,msg='posterior şema/tip')
raises(ValueError,posterior_raporu,[dict(base,full=[1.0000005,0])],msg='üst olasılık sınırı simplex toleransından bağımsız')
correct_one=posterior_raporu([dict(base,id='one',y=1,full=[0,1],unlearn=[0,1],retrain=[0,1])])
for name in ('full','unlearn','retrain'):
    eq(correct_one['forget'][name+'_acc'],1.0,'ikinci sınıf doğru kararı')
    eq(correct_one['forget'][name+'_nll'],0.0,'ikinci sınıf tam olasılık')
old=copy.deepcopy(base);posterior_raporu([base]);eq(base,old,'posterior girdisi korunur')
# Aynı yanlış accuracy, farklı NLL ve retrain yakınlığı: hata unutma değildir.
near=posterior_raporu([dict(base,id='near',unlearn=[0.1,0.9])])['forget']
far=posterior_raporu([dict(base,id='far',unlearn=[0.001,0.999])])['forget']
eq(near['unlearn_acc'],far['unlearn_acc'],'iki model de yanlış sınıf seçer')
ok(far['unlearn_nll']>near['unlearn_nll'],'daha kararlı yanlış cevap daha yüksek NLL')
ok(far['unlearn_retrain_tv']>near['unlearn_retrain_tv'],'daha yüksek forget NLL retrain yakınlığını bozabilir')


# Her grupta iki farklı posterior; tek elemanlı test ortalama mutantını ayıramaz.
import math as _m39
_rows39=[]
for _g39 in ("retain","forget"):
    _rows39.extend([{"id":_g39+"1","grup":_g39,"y":0,"full":[0.8,0.2],"unlearn":[0.6,0.4],"retrain":[0.5,0.5]},
                    {"id":_g39+"2","grup":_g39,"y":1,"full":[0.1,0.9],"unlearn":[0.3,0.7],"retrain":[0.2,0.8]}])
_r39=posterior_raporu(_rows39)
for _g39 in ("retain","forget"):
    eq(_r39[_g39]["n"],2,"iki posteriorun grup sayısı")
    ok(abs(_r39[_g39]["unlearn_retrain_tv"]-0.1)<1e-12,"TV toplam değil ortalama")
    for _name39,_probs39 in (("full",(0.8,0.9)),("unlearn",(0.6,0.7)),("retrain",(0.5,0.8))):
        ok(abs(_r39[_g39][_name39+"_nll"]-sum(-_m39.log(p) for p in _probs39)/2)<1e-12,"iki örnekte ortalama NLL: "+_name39)
```

```setup
import sys,importlib
from pathlib import Path
_root=Path(sys.modules["__main__"].__file__).resolve().parents[1]
sys.path.insert(0,str(_root))
if 'ai_lab' not in sys.modules:sys.modules['ai_lab']=importlib.import_module('sandbox.ai_gercek_lab')
from sandbox.ai_gercek_ai_savunma_39 import hazirla
hazirla()

```

```hint
rows boş olmayan liste; her dict tam id/grup/y/full/unlearn/retrain şeması. id benzersiz boş olmayan string, grup retain/forget, y int 0/1 (bool değil). Posteriorlar iki sonlu sayısal [0, 1] listesi, toplam 1 tolerans 1e-6. Her grup için n, her modelin acc/nll değeri, unlearn_retrain_tv döndür; olmayan grup None. Tie 0, log clamp 1e-12; yanlış şema ValueError.
```
:::

::: tahmin Düşük loss mu, yüksek loss mu?
```python
retain_loss=0.2
forget_loss=1.4
alpha=0.5
print(round(retain_loss-alpha*forget_loss,2))
```
???
```cikti
-0.5
```
Çalıştırıp tahmininle farkını yaz. Minimize edilen objective'in negatif olabilmesi hata değildir. Bu örnek model eğitimi değil, sentetik skaler hesaptır.
:::

::: anlat Hata vitrini · Kararlı yanlış cevap
Sentetik karşı örnek: doğru sınıf 0, unlearn posterioru [0.001, 0.999], retrain posterioru [0.5, 0.5]. Unlearn accuracy 0 olduğu için “unuttu” diyebilirsin; fakat TV farkı 0.499 ve model çok kararlı yanlış cevap veriyor. Bu rakamlar örnektir, ölçülmüş model çıktısı diye sunulmaz. Gerçek deneyde aynı ölçümleri kendi dosyandan oku. Retain yararı ve retrain yakınlığı birlikte değerlendirilmeden silinme iddiası kurma. Yeni bir membership inference saldırısı veya kişisel veri çıkarma bu dersin parçası değildir.
:::

::: gorev Gerçek deney · Full, unlearn, retrain ve unchanged modellerini ölç
Üç fonksiyonu birleştir, CALISTIR bloğunu koru. Gerçek CPU eğitimleri çalışır; iki koşunun posteriorlarını, ağırlık hashlerini, 100 unlearning gradient adımını ve dosyadan yeniden okunan ağırlıkları incele. Sonuçta forget accuracy'nin düşmesi kabul koşulu değildir; gerçek doğru deney ve raporlama koşuldur. Sonuç unutmanın başarısız olduğunu da gösterebilir. Kanıtta retrain hangi kimlikleri hiç görmedi? Unchanged neden gerekli? İki koşunun seed'leri farklı olduğu halde modelin başlangıcı neden aynı? Kendi çıktınla açıkla.

```starter
def veri_bol(*a):return {}
def kayip_birlestir(*a):return {}
def posterior_raporu(*a):return {}
```

```solution
def veri_bol(ids,forget):
    if not isinstance(ids,list) or any(not isinstance(x,str) or not x for x in ids) or len(set(ids))!=len(ids):raise ValueError('ids')
    if not isinstance(forget,list) or not forget or any(not isinstance(x,str) or x not in ids for x in forget) or len(set(forget))!=len(forget) or len(forget)==len(ids):raise ValueError('forget')
    return {'retain':[x for x in ids if x not in forget],'forget':[x for x in ids if x in forget]}

def kayip_birlestir(retain_loss,forget_loss,alpha):
    import math
    for x in (retain_loss,forget_loss,alpha):
        if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x):raise ValueError('sayi')
    if retain_loss<0 or forget_loss<0 or not 0<=alpha<=1:raise ValueError('aralik')
    return retain_loss-alpha*forget_loss

def posterior_raporu(rows):
    import math
    if not isinstance(rows,list) or not rows:raise ValueError('liste')
    seen=set()
    for r in rows:
        if not isinstance(r,dict) or set(r)!={'id','grup','y','full','unlearn','retrain'} or not isinstance(r['id'],str) or not r['id'] or r['id'] in seen or r['grup'] not in ('retain','forget') or type(r['y']) is not int or r['y'] not in (0,1):raise ValueError('sema')
        seen.add(r['id'])
        for name in ('full','unlearn','retrain'):
            p=r[name]
            if not isinstance(p,list) or len(p)!=2 or any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or not 0<=x<=1 for x in p) or abs(sum(p)-1)>1e-6:raise ValueError('posterior')
    out={}
    for group in ('retain','forget'):
        a=[r for r in rows if r['grup']==group]
        if not a:out[group]=None;continue
        stats={'n':len(a)}
        for name in ('full','unlearn','retrain'):
            stats[name+'_acc']=sum((0 if r[name][0]>=r[name][1] else 1)==r['y'] for r in a)/len(a)
            stats[name+'_nll']=sum(-math.log(max(r[name][r['y']],1e-12)) for r in a)/len(a)
        stats['unlearn_retrain_tv']=sum(sum(abs(x-y) for x,y in zip(r['unlearn'],r['retrain']))/2 for r in a)/len(a)
        out[group]=stats
    return out

import ai_lab
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_39 as D
    D.goster(veri_bol,kayip_birlestir,posterior_raporu)

```

```test
import ai_lab
checks=[]
def kontrol(x,msg):checks.append(bool(x));ok(x,msg)
_eq=eq;_raises=raises
def eq(*a,**k):
    r=_eq(*a,**k);checks.append(r);return r
def raises(*a,**k):
    r=_raises(*a,**k);checks.append(r);return r
issues=ai_lab.kod_denetimi(src,('ref_veri_bol','ref_kayip_birlestir','ref_posterior_raporu','kanit_yaz'),izin=())
import ast
_tree=ast.parse(src);_imports=set()
for _node in ast.walk(_tree):
    if isinstance(_node,(ast.Import,ast.ImportFrom)):
        _imports.update(_a.asname or _a.name.split('.')[0] for _a in _node.names)
def _root_name(_target):
    while isinstance(_target,(ast.Attribute,ast.Subscript)):_target=_target.value
    return _target.id if isinstance(_target,ast.Name) else None
for _node in ast.walk(_tree):
    _targets=_node.targets if isinstance(_node,ast.Assign) else [_node.target] if isinstance(_node,(ast.AugAssign,ast.AnnAssign)) else []
    for _target in _targets:
        if isinstance(_target,(ast.Attribute,ast.Subscript)) and _root_name(_target) in _imports:issues.append('import edilen modül yamalanamaz')
    if isinstance(_node,ast.Attribute) and _node.attr=='__globals__':issues.append('fonksiyon globals erişimi yasak')
kontrol(not issues,'kopya/yama koruması: '+str(issues))
if issues:stop()
need('veri_bol')
from collections import UserString
raises(ValueError,veri_bol,['a','b'],[UserString('a')],msg='str ile eşit karşılaştırılan UserString yine str değildir')
for ids,f in [(('a','b'),['a']),([1,'b'],['b']),(['','b'],['b'])]:
    raises(ValueError,veri_bol,ids,f,msg='geçerli forget bozuk ids listesini meşrulaştırmaz')
for ids,forget in [(['a','b','c'],['c','a']),(['z','q'],['z']),(['b','c','a','d'],['a','c'])]:
    eq(veri_bol(ids,forget),{'retain':[i for i in ids if i not in forget],'forget':[i for i in ids if i in forget]},'ayrık birleşim ve kaynak sırası')
for ids,f in [([],['a']),([''],['']),([1,'b'],[1]),(['a','a','b'],['a']),(['a','b'],[]),(['a','b'],['a','b']),(['a','b'],['x']),(['a','b'],['a','a']),(['a','b','c'],['a','a']),(['a','b'],('a',))]:raises(ValueError,veri_bol,ids,f,msg='ayrım şema/sınır')

need('kayip_birlestir')
for r,f,a in [(0,0,0),(0.2,1.4,0.5),(1,0,1),(0,1,1),(0.8,0.4,0)]:eq(kayip_birlestir(r,f,a),r-a*f,'minimize retain-alpha*forget; sınırlar dahil')
for r,f,a in [(-0.1,1,0.5),(1,-0.1,0.5),(1,1,-0.1),(1,1,1.01),(True,1,0.5),(1,False,0.5),(1,1,True),(float('nan'),1,0.5),(1,float('inf'),0.5),(1,1,'0.5')]:raises(ValueError,kayip_birlestir,r,f,a,msg='sonlu sayısal loss/alpha')

need('posterior_raporu')
import math,copy
base={'id':'x','grup':'forget','y':0,'full':[0.9,0.1],'unlearn':[0.1,0.9],'retrain':[0.5,0.5]}
r=posterior_raporu([base]);eq(r['retain'],None,'olmayan grup ölçülmedi')
for n,v in [('full_acc',1.0),('unlearn_acc',0.0),('retrain_acc',1.0),('unlearn_retrain_tv',0.4)]:eq(r['forget'][n],v,'tie0 ve posterior farkı')
for n,p in [('full',0.9),('unlearn',0.1),('retrain',0.5)]:eq(r['forget'][n+'_nll'],-math.log(p),'NLL doğal log')
other=dict(base,id='y',grup='retain',y=1,full=[0,1],unlearn=[1,0],retrain=[1,0]);r=posterior_raporu([other]);eq(r['forget'],None,'forget yoksa None');eq(r['retain']['unlearn_nll'],-math.log(1e-12),'log0 clamp');eq(r['retain']['unlearn_retrain_tv'],0.0,'eşit dağılımlar')
mixed=posterior_raporu([base,dict(base,id='q',full=[0.2,0.8],unlearn=[0.6,0.4],retrain=[0.3,0.7])]);eq(mixed['forget']['full_acc'],0.5,'ortalama');eq(mixed['forget']['unlearn_acc'],0.5,'ortalama');eq(mixed['forget']['n'],2,'örnek sayısı')
for bad in ([],[None],[base,base],[dict(base,id='')],[dict(base,y=True)],[dict(base,grup='other')],[dict(base,extra=1)],[dict(base,unlearn=[0.5,0.4])],[dict(base,full=[-0.1,1.1])],[dict(base,full=[-5e-7,1.0])],[dict(base,retrain=[True,0])],[dict(base,full=[float('nan'),0])],[dict(base,full=[1])]):raises(ValueError,posterior_raporu,bad,msg='tam şema/sonlu olasılık/simplex')
tol=dict(base,id='tol',full=[0.5,0.5000015])
raises(ValueError,posterior_raporu,[tol],msg='simplex toleransı dışı')
eq(posterior_raporu([dict(base,id='tol',full=[0.5,0.5000005])])['forget']['n'],1,'simplex toleransı içi')
for bad in ([dict(base,id=1)],[dict(base,full=(0.9,0.1))],[dict(base,y=2)],[dict(base,full=[0.5,'0.5'])],tuple([base])):
    raises(ValueError,posterior_raporu,bad,msg='posterior şema/tip')
raises(ValueError,posterior_raporu,[dict(base,full=[1.0000005,0])],msg='üst olasılık sınırı simplex toleransından bağımsız')
correct_one=posterior_raporu([dict(base,id='one',y=1,full=[0,1],unlearn=[0,1],retrain=[0,1])])
for name in ('full','unlearn','retrain'):
    eq(correct_one['forget'][name+'_acc'],1.0,'ikinci sınıf doğru kararı')
    eq(correct_one['forget'][name+'_nll'],0.0,'ikinci sınıf tam olasılık')
old=copy.deepcopy(base);posterior_raporu([base]);eq(base,old,'posterior girdisi korunur')
# Aynı yanlış accuracy, farklı NLL ve retrain yakınlığı: hata unutma değildir.
near=posterior_raporu([dict(base,id='near',unlearn=[0.1,0.9])])['forget']
far=posterior_raporu([dict(base,id='far',unlearn=[0.001,0.999])])['forget']
eq(near['unlearn_acc'],far['unlearn_acc'],'iki model de yanlış sınıf seçer')
ok(far['unlearn_nll']>near['unlearn_nll'],'daha kararlı yanlış cevap daha yüksek NLL')
ok(far['unlearn_retrain_tv']>near['unlearn_retrain_tv'],'daha yüksek forget NLL retrain yakınlığını bozabilir')

_rows39=[]
for _g39 in ("retain","forget"):
    _rows39.extend([{"id":_g39+"1","grup":_g39,"y":0,"full":[0.8,0.2],"unlearn":[0.6,0.4],"retrain":[0.5,0.5]},
                    {"id":_g39+"2","grup":_g39,"y":1,"full":[0.1,0.9],"unlearn":[0.3,0.7],"retrain":[0.2,0.8]}])
_r39=posterior_raporu(_rows39)
for _g39 in ("retain","forget"):
    eq(_r39[_g39]["n"],2,"iki posteriorun grup sayısı")
    kontrol(abs(_r39[_g39]["unlearn_retrain_tv"]-0.1)<1e-12,"TV toplam değil ortalama")
    for _name39,_probs39 in (("full",(0.8,0.9)),("unlearn",(0.6,0.7)),("retrain",(0.5,0.8))):
        kontrol(abs(_r39[_g39][_name39+"_nll"]-sum(-math.log(p) for p in _probs39)/2)<1e-12,"iki örnekte ortalama NLL: "+_name39)

if not all(checks):stop()
from sandbox import ai_gercek_ai_savunma_39 as D
d=D.deney(veri_bol,kayip_birlestir,posterior_raporu)
kontrol(len(d['runs'])==2,'iki gerçek eğitim/ölçüm koşusu')
kontrol(all(r['weights_sha256']['full']!=r['weights_sha256']['unlearn'] and r['weights_sha256']['full']==r['weights_sha256']['unchanged'] for r in d['runs']),'gerçek ağırlık değişimi ve unchanged kontrolü')
kontrol(all(len(r['training_log'])==50 and all(t['grad_norm']>0 for t in r['training_log']) for r in d['runs']),'100 gerçek unlearning autograd adımı')
kontrol(all(set(r['train_ids']['retrain']).isdisjoint(r['split']['forget']) for r in d['runs']),'retrain forget verisini görmedi')
ai_lab.kanit_yaz('unlearning39-kabul',{'kaynak':'gercek','kabul':all(checks),'ders':'ai-savunma-39','deney':d})

```

```setup
import sys,importlib
from pathlib import Path
_root=Path(sys.modules["__main__"].__file__).resolve().parents[1]
sys.path.insert(0,str(_root))
if 'ai_lab' not in sys.modules:sys.modules['ai_lab']=importlib.import_module('sandbox.ai_gercek_lab')
from sandbox.ai_gercek_ai_savunma_39 import hazirla
hazirla()

```

```meta
motor: ai-gercek
gereksinim: torch
timeout: 240
```

```hint
İşaret, veri ayrımı ve olasılık doğrulamasını ayrı ayrı sına; unutma başarısını zorlayan çıktı yazma.
```
:::

::: anlat Sınır
Bu ders küçük sentetik kimlik sınıflandırıcısında gerçek autograd ve retrain karşılaştırmasını gösterir; LLM bilgisinin silindiğini, kişisel veri gizliliğini veya certified unlearning garantisini kanıtlamaz.
:::


::: anlat Bunu iki dakikada nasıl anlatırsın?
Unlearn modelin forget örneğine kararlı yanlış yanıt vermesi, veriyi hiç görmemiş retrain modele benzediği anlamına gelmez. Retain/forget ayrımını önce doğrula; sonra retain loss − alpha·forget loss gradyanının işaretini türet. Full, unlearn, retain-only retrain ve unchanged modellerin posteriorlarını aynı girdilerde karşılaştır. Accuracy ve NLL yararı, TV uzaklığı retrain yakınlığını farklı açılardan gösterir; tek ölçüt silinme sertifikası değildir.

Önkoşul ve yol köprüsü: ai-guvence-17 gizlilik ölçümü.

| Yaygın yanlış | Mekanizma ve sınır |
|---|---|
| Forget accuracy sıfırsa veri silindi | Model yanlış cevabı hâlâ yüksek güvenle ezberlemiş olabilir |

Dinleyiciye sor: Savunma güvenlik metriğini iyileştirirken meşru kullanıma ne kaybettirebilir? Ham çıktı ve ölçüm paydalarıyla cevapla.
:::


::: anlat Birincil kaynak ve deney sınırı
[PyTorch autograd](https://docs.pytorch.org/tutorials/beginner/basics/autogradqs_tutorial.html): Gerçek gradient hesabı için araç referansı. Bu küçük retain/forget karşılaştırması certified unlearning kanıtı değildir. Çalışan sürüm ve gerçek sonuç kanıtta kayıtlıdır.
:::
