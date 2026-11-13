---
id: ai-saldiri-54
title: Güvenlik ML Dedektörünü Atlatma · Bütçeli Black-box Arama
summary: Gerçek scikit-learn metin sınıflandırıcısını eğit; işlevi koruyan eklemelerle query-bounded evasion ölç; ASR paydasını ve meşru kontrol false-positive oranını ayır.
esleme: ai-savunma-33, ai-guvence-07
timeout: 120
---

::: anlat Modelin kararını değiştirirken görevi koru
Sentetik phishing metinlerini ayıran küçük bir güvenlik ML dedektörüne karşı black-box evasion yaparsın. Bir sohbet modelinden jailbreak istemek yerine, gerçek fit edilmiş sınıflandırıcının phishing skorunu sorgularsın. Veri indirilmez, URL açılmaz, e-posta gönderilmez. `.invalid` adresler eğitim işaretidir. Gerçek phishing kampanyası veya gerçek kurum taklidi yoktur.

| Bileşen | Yapacağın iş | Kanıt |
|---|---|---|
| Aday üretimi | Orijinali aynen tut, yalnız sonuna metin ekle | Eklenen karakter sayısı |
| Black-box arama | En çok q adayın gerçek skorunu sorgula | Her query ve predict_proba sonucu |
| Ölçüm | Başlangıçta yakalanan örneğin kaçışı ve meşru kontrolü ayır | ASR, başlangıç yakalama, false-positive |
| Savunma karşılaştırması | Dar bir özellik seçimini aynı adaylarda dene | Önce/sonra skor farkı |

> [!NOT] Veri ve araç sınırı
> Train/test elle üretilmiş sentetik metinlerdir; test metinleri eğitimde yoktur ama aynı dar kurguya aittir. Bağımsız gerçek dünya veri kümesi veya genelleme kanıtı değildir. Sınıflandırıcı gerçek scikit-learn ile her deneyde yeniden fit edilir. Fixture okumak gerçek fit yerine geçmez. GPU veya LLM gerekmez; kurulu sklearn CPU üzerinde çalışır.

`dedektor/ornek.json` açılabilir öğrenci dosyasıdır. `dedektor/corpus.json` ayrıca 48 train / 12 test sentetik metnini gösterir; bunlar gerçek model çıktısı değildir. Gerçek deney kendi bağımsız kaynak verisini kullanır; çalışma kopyasını değiştirerek gizli testin cevabını değiştiremezsin. Setup bunu geçici çalışma alanına kopyalar. `Path('dedektor/ornek.json').read_text(encoding='utf-8')` ile oku; aynı çalıştırmada kopyadaki suffix/bütçe değerini değiştirip dene. Sonraki Çalıştır yeni kopyadır; kalıcılık vaat edilmez. Görünür örnek, gizli test girdileri ve son gerçek deney ayrıdır.

TF-IDF `norm='l2'` belge vektörünü normalize eder; eklenen bilinen sözcükler vektörü ve LogisticRegression skorunu değiştirebilir. Sınıflandırıcının `predict_proba` çıktısı gerçek phishing yaygınlığına göre kalibre edilmiş risk garantisi değildir. Eşik burada 0.5'tir; model sınıf sırasını okuyup etiket 1'in sütununu kullanırız. Resmî kaynaklar: [TfidfVectorizer](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html), [LogisticRegression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html).
:::

::: gorev 1 · İşlevi koruyan adaylar
`adaylar(metin,ekler,butce)` orijinali ilk öğe olarak döndürsün. Boş/yalnız whitespace suffix'i atla; diğerlerini değiştirmeden tek boşlukla ekle. Eklenen karakter sayısı (boşluk dahil) butce değerini aşmasın. Tekrarlanan adayı yalnız bir kere yaz, sıra korunsun. Metin boş olmayan str, ekler str listesi, butce bool olmayan sıfır veya pozitif int; diğerlerinde ValueError.

```starter
def adaylar(metin,ekler,butce):
    return [metin+' '+e for e in ekler]
```

```test
need('adaylar')
eq(adaylar('x',['a','a','','  ','abc'],2),['x','x a'],'dedup ve boş suffix')
eq(adaylar('x',['abc'],4),['x','x abc'],'karakter sınırı dahil')
eq(adaylar('x',['abc'],3),['x'],'sınır dışı')
eq(adaylar('x',['a'],0),['x'],'sıfır ekleme')
for text in ('phishing-a','diger-7'):
    eq(adaylar(text,['ok','longer'],3),[text,text+' ok'],'farklı orijinal korunur')
for args in [('',[],2),(123,[],2),('x',(),2),('x',[2],2),('x',[],True),('x',[],-1)]:raises(ValueError,adaylar,*args,msg='geçersiz aday girdisi')
eq(adaylar("a",["   ","\t","\n","b"],99),["a","a b"],"yalnız boşluk suffix aday üretmez")
```

```solution
def adaylar(metin,ekler,butce):
    if not isinstance(metin,str) or not metin or not isinstance(ekler,list) or any(not isinstance(x,str) for x in ekler) or type(butce) is not int or butce<0:raise ValueError('girdi')
    out=[metin]
    for ek in ekler:
        if not ek.strip():continue
        yeni=metin+' '+ek
        if len(yeni)-len(metin)<=butce and yeni not in out:out.append(yeni)
    return out

from pathlib import Path
print(Path("dedektor/ornek.json").read_text(encoding="utf-8"))
```

```setup
import sys,importlib
from pathlib import Path
_root=Path(sys.modules["__main__"].__file__).resolve().parents[1]
sys.path.insert(0,str(_root))
if 'ai_lab' not in sys.modules:
    sys.modules['ai_lab']=importlib.import_module('sandbox.ai_gercek_lab')
from sandbox.ai_gercek_ai_saldiri_54 import hazirla
hazirla()
```

```hint
Önce dosyayı incele. Bütçe ve eşik sınırlarını, boş paydanın anlamını ayrı düşün.
```
:::

::: gorev 2 · Her query sayılır
`en_az_risk(hedef,adaylar,q)` ilk min(q,len(adaylar)) metni sırayla tam birer kez sorgulasın. Sonuç `{'secilen':metin,'sorgular':[{'metin':...,'skor':...}]}`. En küçük skoru seç; eşitse ilk aday. Adaylar boş olmayan str listesi; q bool olmayan pozitif int. Skor bool olmayan sonlu 0–1 sayısı; hatalı girdi/skor ValueError. Callback hatası saklanmaz. Seçilmeyen query de bütçeye dahildir. Deneyin ayrıca yaptığı baseline/sonuç ölçümleri ve ikinci model karşılaştırmaları saldırı query bütçesinden ayrı sayılıp kanıtta açıkça kaydedilir.

```starter
def en_az_risk(hedef,adaylar,q):
    return {'secilen':adaylar[-1],'sorgular':[]}
```

```test
need('en_az_risk')
for value in (0,1,0.5):
    r=en_az_risk(lambda x:value,['sinir'],1)
    eq(r,{'secilen':'sinir','sorgular':[{'metin':'sinir','skor':value}]},'0/1 geçerli skor sınırları')
for a,q in [(('a',),1),('a',1),([1],1),(['a'],1.5),(['a','b'],-1)]:raises(ValueError,en_az_risk,lambda x:0.2,a,q,msg='tip ve bütçe sınırı')
for q in (1,2,3,7):
    calls=[];scores={'a':0.8,'b':0.2,'c':0.2}
    def f(x):calls.append(x);return scores[x]
    r=en_az_risk(f,['a','b','c'],q)
    eq(calls,['a','b','c'][:q],'tam query bütçesi')
    eq(r,{'secilen':'a' if q==1 else 'b','sorgular':[{'metin':x,'skor':scores[x]} for x in calls]},'minimum risk; tie ilk')
for value in (-0.1,1.1,float('nan'),True,'0.5'):
    raises(ValueError,en_az_risk,lambda x:value,['a'],1,msg='bozuk skor ret')
for a,q in [([],1),(['a'],0),(['a'],True),([''],2)]:raises(ValueError,en_az_risk,lambda x:0.2,a,q,msg='query girdisi ret')
```

```solution
def en_az_risk(hedef,adaylar,q):
    import math
    if not isinstance(adaylar,list) or not adaylar or any(not isinstance(x,str) or not x for x in adaylar) or type(q) is not int or q<1:raise ValueError('girdi')
    rows=[]
    for text in adaylar[:q]:
        score=hedef(text)
        if isinstance(score,bool) or not isinstance(score,(int,float)) or not math.isfinite(score) or not 0<=score<=1:raise ValueError('skor')
        rows.append({'metin':text,'skor':score})
    return {'secilen':min(rows,key=lambda r:r['skor'])['metin'],'sorgular':rows}

from pathlib import Path
print(Path("dedektor/ornek.json").read_text(encoding="utf-8"))
```

```setup
import sys,importlib
from pathlib import Path
_root=Path(sys.modules["__main__"].__file__).resolve().parents[1]
sys.path.insert(0,str(_root))
if 'ai_lab' not in sys.modules:
    sys.modules['ai_lab']=importlib.import_module('sandbox.ai_gercek_lab')
from sandbox.ai_gercek_ai_saldiri_54 import hazirla
hazirla()
```

```hint
Önce dosyayı incele. Bütçe ve eşik sınırlarını, boş paydanın anlamını ayrı düşün.
```
:::

::: gorev 3 · Yanlış ASR güven verir
`olcum_raporu(rows)` her kayıtta tam `id, etiket, once, sonra` alanlarını ister. id boş olmayan benzersiz str; etiket bool olmayan 0/1 int; skorlar bool olmayan sonlu 0–1. Boş liste/bozuk kayıt ValueError. Etiket 1 phishing, 0 meşru. Karar skor >= 0.5. ASR paydası yalnız başlangıçta yakalanan phishing; payı bunlardan sonradan eşik altına inenler. Payda sıfırsa None. Kontrol false-positive paydası tüm etiket 0 kayıtları; kontrol yoksa None. Dönen alanlar: phishing_sayisi, baslangicta_yakalanan, atlatilan, asr, kontrol_sayisi, kontrol_fp_once, kontrol_fp_sonra.

```starter
def olcum_raporu(rows):
    return {'asr':sum(r['sonra']<0.5 for r in rows)/len(rows)}
```

```test
need('olcum_raporu')
edges=[{'id':'x','etiket':1,'once':0,'sonra':1},{'id':'y','etiket':1,'once':1,'sonra':0},{'id':'z','etiket':0,'once':0,'sonra':0.5}]
eq(olcum_raporu(edges),{'phishing_sayisi':2,'baslangicta_yakalanan':1,'atlatilan':1,'asr':1.0,'kontrol_sayisi':1,'kontrol_fp_once':0.0,'kontrol_fp_sonra':1.0},'0/1 ve kontrolde son eşik dahil')
for bad in (tuple(edges),[None],[{'id':'x'}],[dict(edges[0],id=1)],[dict(edges[0],etiket=2)],[dict(edges[0],etiket='1')],[dict(edges[0],once=-0.1)],[dict(edges[0],sonra=-0.1)],[dict(edges[0],once=1.1)],[dict(edges[0],sonra=True)],[dict(edges[0],sonra=float('inf'))],[dict(edges[0],once='0.5')]):raises(ValueError,olcum_raporu,bad,msg='tam şema/tip/skor doğrulaması')
rows=[{'id':'p1','etiket':1,'once':0.5,'sonra':0.49},{'id':'p2','etiket':1,'once':0.49,'sonra':0.1},{'id':'p3','etiket':1,'once':0.8,'sonra':0.5},{'id':'c','etiket':0,'once':0.5,'sonra':0.1}]
eq(olcum_raporu(rows),{'phishing_sayisi':3,'baslangicta_yakalanan':2,'atlatilan':1,'asr':0.5,'kontrol_sayisi':1,'kontrol_fp_once':1.0,'kontrol_fp_sonra':0.0},'yalnız önce yakalananlar ASR paydası; eşik dahil')
r=olcum_raporu([rows[1]])
eq(r['asr'],None,'payda sıfır: ölçülmedi')
eq((r['kontrol_fp_once'],r['kontrol_fp_sonra']),(None,None),'kontrol yoksa sıfır uydurma')
for bad in ([],rows+[rows[0]],[dict(rows[0],once=True)],[dict(rows[0],etiket=True)],[dict(rows[0],once=float('nan'))],[dict(rows[0],sonra=2)],[dict(rows[0],id='')],[dict(rows[0],ek=1)]):raises(ValueError,olcum_raporu,bad,msg='bozuk rapor ret')
ctrl=olcum_raporu([{'id':'c1','etiket':0,'once':0.8,'sonra':0.49},{'id':'c2','etiket':0,'once':0.49,'sonra':0.8}])
eq((ctrl['kontrol_fp_once'],ctrl['kontrol_fp_sonra']),(0.5,0.5),'iki kontrol oranı: sayı yerine bölme')
```

```solution
def olcum_raporu(rows):
    import math
    if not isinstance(rows,list) or not rows:raise ValueError('liste')
    ids=set()
    for r in rows:
        if not isinstance(r,dict) or set(r)!={'id','etiket','once','sonra'} or not isinstance(r['id'],str) or not r['id'] or r['id'] in ids or type(r['etiket']) is not int or r['etiket'] not in (0,1):raise ValueError('sema')
        ids.add(r['id'])
        for k in ('once','sonra'):
            v=r[k]
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<=v<=1:raise ValueError('skor')
    ph=[r for r in rows if r['etiket']==1];ctl=[r for r in rows if r['etiket']==0]
    detected=[r for r in ph if r['once']>=0.5];escaped=[r for r in detected if r['sonra']<0.5]
    return {'phishing_sayisi':len(ph),'baslangicta_yakalanan':len(detected),'atlatilan':len(escaped),'asr':len(escaped)/len(detected) if detected else None,'kontrol_sayisi':len(ctl),'kontrol_fp_once':sum(r['once']>=0.5 for r in ctl)/len(ctl) if ctl else None,'kontrol_fp_sonra':sum(r['sonra']>=0.5 for r in ctl)/len(ctl) if ctl else None}

from pathlib import Path
print(Path("dedektor/ornek.json").read_text(encoding="utf-8"))
```

```setup
import sys,importlib
from pathlib import Path
_root=Path(sys.modules["__main__"].__file__).resolve().parents[1]
sys.path.insert(0,str(_root))
if 'ai_lab' not in sys.modules:
    sys.modules['ai_lab']=importlib.import_module('sandbox.ai_gercek_lab')
from sandbox.ai_gercek_ai_saldiri_54 import hazirla
hazirla()
```

```hint
Önce dosyayı incele. Bütçe ve eşik sınırlarını, boş paydanın anlamını ayrı düşün.
```
:::

::: tahmin ASR paydasında başlangıç kaçışı
Üç phishing örneğinin yalnız ikisi başlangıçta yakalanıyor. Bu ikiden biri sonradan kaçıyor. Başlangıçta zaten kaçan üçüncü örneği de yeni başarı sayan rapor hangi hatayı yapar?
```python
once=[0.8,0.9,0.2]
sonra=[0.3,0.7,0.1]
payda=sum(p>=0.5 for p in once)
pay=sum(a>=0.5 and b<0.5 for a,b in zip(once,sonra))
print(pay,payda,pay/payda)
```
???
```cikti
1 2 0.5
```
Başlangıçtaki kaçışı yeni saldırı başarısı saymazsın. 2/3 hesaplayan rapor farklı bir oranı ASR diye sunar. Bu hesap fixture'dır; model ölçümü değildir. Çalıştırdıktan sonra kendi tahmininle çıktı arasındaki farkı ve paydanın neden 2 olduğunu kendi cümlenle açıkla.
:::

::: anlat Hata vitrini ve savunma köprüsü
`once=0.2, sonra=0.1` için “atlatıldı” yazmak yanlış güvenlik bulgusudur: model bu örneği başta da yakalamıyordu. Skor düşmesi ile karar değişmesi aynı şey değildir. Query bütçesini yalnız seçilen aday sayısıyla ölçmek de yanlıştır; denenip elenen bütün adaylar maliyettir. Karakter bütçesi query bütçesinin yerine geçmez.

Bir düşük skor elde etmek için phishing isteğini silersen görevi değiştirmiş olursun. Burada orijinal metin/URL aynen korunur; yalnız benign görünümlü ekler yapılır. Bunun gerçek kullanıcıların algısını veya gerçek phishing işlevini koruduğuna dair genel bir iddia yoktur: bu labın append-only vekil kuralıdır. Savunma tarafında aynı adayları dar sabit risk kelimeleri ve norm=None kullanan ikinci modele veririz. Bu kontrollü karşılaştırma genel bir evasion savunması değildir; kelime değişimi ve yeni diller gibi saldırılar ölçülmez. Adversarial training için ai-savunma-33, gerçek gradient deneyleri için ai-guvence-07 ile ilişki kur.
:::

::: gorev Gerçek deney · Fit edilmiş güvenlik dedektörüne bütçeli saldırı
Üç fonksiyonu birleştir. Son CALISTIR bloğu Çalıştır'da gerçek fit/predict_proba ölçümünü başlatır; silme. Kontrol aynı deneyi ayrıca ölçer ve yalnız bütün kontroller doğruysa kabul kanıtı yazar. Q 1/3/4, karakter bütçesi 100, eşik 0.5. Her metnin orijinali, adayları, sorguları, skorları, model/veri hash'i, train/test ayrımı, CPU/sürüm ve dar savunma sonucu kaydedilir. Saldırının başarılı olması geçme şartı değildir; doğru deney ve raporlama şarttır.

Çıktıdaki kanıt dosyasını açıp q=1 ile q=4 ASR'sini karşılaştır: daha çok query karar değiştirdi mi, yalnız skoru mu düşürdü? Kontrol false-positive oranı ne oldu? Sayıları kendi dosyandan yorumla; burada önceden garanti edilmiş başarı yüzdesi yoktur.

```starter
import ai_lab
def adaylar(metin,ekler,butce):return [metin]
def en_az_risk(hedef,adaylar,q):return {}
def olcum_raporu(rows):return {}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_54 as D
    D.goster(adaylar,en_az_risk,olcum_raporu)
```

```solution
import ai_lab

def adaylar(metin,ekler,butce):
    if not isinstance(metin,str) or not metin or not isinstance(ekler,list) or any(not isinstance(x,str) for x in ekler) or type(butce) is not int or butce<0:raise ValueError('girdi')
    out=[metin]
    for ek in ekler:
        if not ek.strip():continue
        yeni=metin+' '+ek
        if len(yeni)-len(metin)<=butce and yeni not in out:out.append(yeni)
    return out

def en_az_risk(hedef,adaylar,q):
    import math
    if not isinstance(adaylar,list) or not adaylar or any(not isinstance(x,str) or not x for x in adaylar) or type(q) is not int or q<1:raise ValueError('girdi')
    rows=[]
    for text in adaylar[:q]:
        score=hedef(text)
        if isinstance(score,bool) or not isinstance(score,(int,float)) or not math.isfinite(score) or not 0<=score<=1:raise ValueError('skor')
        rows.append({'metin':text,'skor':score})
    return {'secilen':min(rows,key=lambda r:r['skor'])['metin'],'sorgular':rows}

def olcum_raporu(rows):
    import math
    if not isinstance(rows,list) or not rows:raise ValueError('liste')
    ids=set()
    for r in rows:
        if not isinstance(r,dict) or set(r)!={'id','etiket','once','sonra'} or not isinstance(r['id'],str) or not r['id'] or r['id'] in ids or type(r['etiket']) is not int or r['etiket'] not in (0,1):raise ValueError('sema')
        ids.add(r['id'])
        for k in ('once','sonra'):
            v=r[k]
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<=v<=1:raise ValueError('skor')
    ph=[r for r in rows if r['etiket']==1];ctl=[r for r in rows if r['etiket']==0]
    detected=[r for r in ph if r['once']>=0.5];escaped=[r for r in detected if r['sonra']<0.5]
    return {'phishing_sayisi':len(ph),'baslangicta_yakalanan':len(detected),'atlatilan':len(escaped),'asr':len(escaped)/len(detected) if detected else None,'kontrol_sayisi':len(ctl),'kontrol_fp_once':sum(r['once']>=0.5 for r in ctl)/len(ctl) if ctl else None,'kontrol_fp_sonra':sum(r['sonra']>=0.5 for r in ctl)/len(ctl) if ctl else None}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_54 as D
    D.goster(adaylar,en_az_risk,olcum_raporu)
```

```test
import ai_lab
checks=[]
def kontrol(x,msg):checks.append(bool(x));ok(x,msg)
_eq=eq;_raises=raises
def kontrol_eq(*args,**kw):
    r=_eq(*args,**kw);checks.append(r);return r
def kontrol_raises(*args,**kw):
    r=_raises(*args,**kw);checks.append(r);return r
issues=ai_lab.kod_denetimi(src,('ref_adaylar','ref_en_az_risk','ref_olcum_raporu','kanit_yaz'),izin=())
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
need('adaylar')
kontrol_eq(adaylar('x',['a','a','','  ','abc'],2),['x','x a'],'dedup ve boş suffix')
kontrol_eq(adaylar('x',['abc'],4),['x','x abc'],'karakter sınırı dahil')
kontrol_eq(adaylar('x',['abc'],3),['x'],'sınır dışı')
kontrol_eq(adaylar('x',['a'],0),['x'],'sıfır ekleme')
for text in ('phishing-a','diger-7'):
    kontrol_eq(adaylar(text,['ok','longer'],3),[text,text+' ok'],'farklı orijinal korunur')
for args in [('',[],2),(123,[],2),('x',(),2),('x',[2],2),('x',[],True),('x',[],-1)]:kontrol_raises(ValueError,adaylar,*args,msg='geçersiz aday girdisi')
kontrol_eq(adaylar("a",["   ","\t","\n","b"],99),["a","a b"],"yalnız boşluk suffix aday üretmez")

need('en_az_risk')
for value in (0,1,0.5):
    r=en_az_risk(lambda x:value,['sinir'],1)
    kontrol_eq(r,{'secilen':'sinir','sorgular':[{'metin':'sinir','skor':value}]},'0/1 geçerli skor sınırları')
for a,q in [(('a',),1),('a',1),([1],1),(['a'],1.5),(['a','b'],-1)]:kontrol_raises(ValueError,en_az_risk,lambda x:0.2,a,q,msg='tip ve bütçe sınırı')
for q in (1,2,3,7):
    calls=[];scores={'a':0.8,'b':0.2,'c':0.2}
    def f(x):calls.append(x);return scores[x]
    r=en_az_risk(f,['a','b','c'],q)
    kontrol_eq(calls,['a','b','c'][:q],'tam query bütçesi')
    kontrol_eq(r,{'secilen':'a' if q==1 else 'b','sorgular':[{'metin':x,'skor':scores[x]} for x in calls]},'minimum risk; tie ilk')
for value in (-0.1,1.1,float('nan'),True,'0.5'):
    kontrol_raises(ValueError,en_az_risk,lambda x:value,['a'],1,msg='bozuk skor ret')
for a,q in [([],1),(['a'],0),(['a'],True),([''],2)]:kontrol_raises(ValueError,en_az_risk,lambda x:0.2,a,q,msg='query girdisi ret')

need('olcum_raporu')
edges=[{'id':'x','etiket':1,'once':0,'sonra':1},{'id':'y','etiket':1,'once':1,'sonra':0},{'id':'z','etiket':0,'once':0,'sonra':0.5}]
kontrol_eq(olcum_raporu(edges),{'phishing_sayisi':2,'baslangicta_yakalanan':1,'atlatilan':1,'asr':1.0,'kontrol_sayisi':1,'kontrol_fp_once':0.0,'kontrol_fp_sonra':1.0},'0/1 ve kontrolde son eşik dahil')
for bad in (tuple(edges),[None],[{'id':'x'}],[dict(edges[0],id=1)],[dict(edges[0],etiket=2)],[dict(edges[0],etiket='1')],[dict(edges[0],once=-0.1)],[dict(edges[0],sonra=-0.1)],[dict(edges[0],once=1.1)],[dict(edges[0],sonra=True)],[dict(edges[0],sonra=float('inf'))],[dict(edges[0],once='0.5')]):kontrol_raises(ValueError,olcum_raporu,bad,msg='tam şema/tip/skor doğrulaması')
rows=[{'id':'p1','etiket':1,'once':0.5,'sonra':0.49},{'id':'p2','etiket':1,'once':0.49,'sonra':0.1},{'id':'p3','etiket':1,'once':0.8,'sonra':0.5},{'id':'c','etiket':0,'once':0.5,'sonra':0.1}]
kontrol_eq(olcum_raporu(rows),{'phishing_sayisi':3,'baslangicta_yakalanan':2,'atlatilan':1,'asr':0.5,'kontrol_sayisi':1,'kontrol_fp_once':1.0,'kontrol_fp_sonra':0.0},'yalnız önce yakalananlar ASR paydası; eşik dahil')
r=olcum_raporu([rows[1]])
kontrol_eq(r['asr'],None,'payda sıfır: ölçülmedi')
kontrol_eq((r['kontrol_fp_once'],r['kontrol_fp_sonra']),(None,None),'kontrol yoksa sıfır uydurma')
for bad in ([],rows+[rows[0]],[dict(rows[0],once=True)],[dict(rows[0],etiket=True)],[dict(rows[0],once=float('nan'))],[dict(rows[0],sonra=2)],[dict(rows[0],id='')],[dict(rows[0],ek=1)]):kontrol_raises(ValueError,olcum_raporu,bad,msg='bozuk rapor ret')
ctrl=olcum_raporu([{'id':'c1','etiket':0,'once':0.8,'sonra':0.49},{'id':'c2','etiket':0,'once':0.49,'sonra':0.8}])
kontrol_eq((ctrl['kontrol_fp_once'],ctrl['kontrol_fp_sonra']),(0.5,0.5),'iki kontrol oranı: sayı yerine bölme')

if not all(checks):stop()
from sandbox import ai_gercek_ai_saldiri_54 as D
try:r=D.deney(adaylar,en_az_risk,olcum_raporu)
except ai_lab.GercekLabYok as e:
    kontrol(False,'gerçek deney yapılamadı: '+str(e));stop()
kontrol(all(r['kontroller']),'gerçek query audit, bütçe ve ASR eşleşti')
kontrol(len(r['train'])==48 and len(r['test'])==12,'gerçek fit ve ayrılmış 12 test örneği')
kontrol(len(r['query_audit'])==36,'3 query bütçesi x 12 örnek ölçüldü')
kontrol(r['model']['n_iter'][0]>0 and bool(r['model']['sha256']),'gerçek fit iterasyonu ve ağırlık hash')
ai_lab.kanit_yaz('saldiri54-kabul',{'kaynak':'gercek','kabul':all(checks),'ders':'ai-saldiri-54','deney':r})
```

```setup
import sys,importlib
from pathlib import Path
_root=Path(sys.modules["__main__"].__file__).resolve().parents[1]
sys.path.insert(0,str(_root))
if 'ai_lab' not in sys.modules:
    sys.modules['ai_lab']=importlib.import_module('sandbox.ai_gercek_lab')
from sandbox.ai_gercek_ai_saldiri_54 import hazirla
hazirla()
```

```meta
motor: ai-gercek
gereksinim: torch
timeout: 120
```

```hint
Üç sözleşmeyi birleştir. Bu deney sklearn ile CPU üzerinde çalışır; gradient veya GPU gerekmez.
```
:::

::: anlat Sınır
Bu ders sentetik metinler üzerinde gerçek sklearn fit ve bütçeli append-only black-box evasion gösterir; gerçek e-posta güvenlik ürünlerini, genel phishing başarısını veya tüm adversarial ML savunmalarını ölçemez.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
### Black-box bütçe her skorlu adayı sayar

Aday üretici orijinali ilk sırada tutar ve yalnız sona ekler; bu dar dönüşüm orijinal metni silmez. Her predict_proba sorgusu bütçeden düşer; seçilmeyen adayın skoru da bir sorgudur. Eşit minimumda ilk aday kalır. ASR paydasına başlangıçta yakalanan saldırılar girer; zaten kaçan örneği yeni başarı saymak oranı şişirir. Meşru kontrolün false-positive oranı başka bir paydadır. L2 normalize TF-IDF vektörüne eklenen sözcükler logit katkılarını değiştirebilir; bu, gerçek phishing ürünü için genelleme kanıtı değildir.

| Yaygın yanlış | Mekanizmanın söylediği |
|---|---|
| Düşük skor güvenli metin demektir | Skor sentetik sınıflandırıcının ölçümüdür; metnin güvenilirliği veya gerçek yaygınlıkta kalibre risk değildir. |

Sonraki bağlantı: ai-savunma-33 ile adversarial training karşılaştırması.
:::
