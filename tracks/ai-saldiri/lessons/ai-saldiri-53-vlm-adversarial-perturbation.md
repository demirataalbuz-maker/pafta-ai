---
id: ai-saldiri-53
title: VLM Adversarial Perturbation · Gerçek Piksel Gradienti
summary: Donuk SmolVLM üzerinde gerçek autograd; hedefli PGD, piksel bütçesi, PNG round-trip ve iki next-token tercihinin karşılaştırılması.
esleme: ai-guvence-07, ai-saldiri-12
timeout: 300
---

::: anlat Bir VLM'nin gördüğü pikseli değiştir
Bu deneyde gerçek pretrained SmolVLM görüntüyü ve soruyu birlikte işler. Ağırlıkları dondururuz; yalnız giriş pikselinden gerçek autograd gradienti alırız. Ders bir LLM jailbreak'i veya belgeye gizlenmiş talimat değildir: sayısal pixel perturbation ve iki next-token adayının göreli tercihi ölçülür. ai-saldiri-12'deki multimodal injection'dan, ai-guvence-07'deki küçük sınıflandırıcıdan bu nedenle ayrılır.

| Adım | Senin kodun | Gerçek deney kanıtı |
|---|---|---|
| İkili skor | Stabil softmax ve tie kuralı | VLM'nin red/blue logitleri |
| Targeted PGD | Gradient yönünde iniş + x0 merkezli projeksiyon | Gerçek autograd gradient normu |
| Yeniden okuma | PNG'yi yaz, tekrar oku | Yeniden okunan piksel bütçesi ve model skoru |
| Rapor | Önceden hedefte olanı ayır | Epsilon 0 kontrolü ve attack grubu |

> [!NOT] Model ve ölçüm sınırı
> Model HuggingFaceTB/SmolVLM-256M-Instruct, sabit revizyon 7e3e67edbbed1bf9888184d9df282b700a323964, Apache 2.0. İndirmesi kullanıcı tarafından ayrıca onaylanmıştır; ders otomatik indirme yapmaz. GPU varsa kullanılır, CPU da mümkündür. Performans ve bellek cihazda ölçülür; yalnız ağırlık boyutu toplam VRAM değildir. Yalnız kendi Python koşusu yönetilir; kullanıcı Ollama/WSL/Docker süreçleri kapatılmaz.

İki aday ` red` ve ` blue` tek tokenizer tokenı olmalıdır. Softmax yalnız bu iki logitte alınır: sonuç tüm vocabulary olasılığı, üretilmiş serbest yanıt veya gerçek renk doğruluğu değildir. Baseline'da tercih edilmeyen aday hedef seçilir. Targeted loss=logsumexp(iki logit)−hedef logit. Gradient descent hedefin göreli skorunu artırmayı amaçlar; başarı garanti edilmez.

`vlm/ornek.json` küçük diziler içeren sentetik fixture'dır; önceden hazırlanmış gerçek gradient değildir. Görev editöründe `from pathlib import Path` yazıp `Path('vlm/ornek.json').read_text(encoding='utf-8')` ile aç; aynı çalıştırmada değiştir. Setup yeni geçici kopya oluşturur; sonraki çalıştırmaya kalıcılık yoktur. Son görev her seferinde gerçek modele ileri/geri geçiş yapar. Kaynaklar: [resmî model card](https://huggingface.co/HuggingFaceTB/SmolVLM-256M-Instruct), [PyTorch autograd.grad](https://docs.pytorch.org/docs/2.14/generated/torch.autograd.grad.html). Orijinal 512 RGB görseller laboratuvarda üretilir; kişisel görsel kullanılmaz.
:::

::: gorev 1 · İki tokenın göreli skorunu ölç
`ikili_skor(logitler)` tam iki sonlu sayı içeren liste alır (bool değil); diğer girdiler ValueError. Max çıkararak stabil softmax hesapla. `{'olasilik':[p0,p1],'secim':0 veya 1}` döndür; eşitse 0. Büyük logitler exp overflow üretmemeli.

```starter
def ikili_skor(logitler):
    return {'olasilik':[0.5,0.5],'secim':0}
```

```solution
def ikili_skor(logitler):
    import math
    if not isinstance(logitler,list) or len(logitler)!=2 or any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in logitler):raise ValueError('iki sonlu logit')
    m=max(logitler);a=[math.exp(x-m) for x in logitler];z=sum(a)
    return {'olasilik':[x/z for x in a],'secim':0 if logitler[0]>=logitler[1] else 1}

from pathlib import Path
print(Path("vlm/ornek.json").read_text(encoding="utf-8"))
```

```test
need('ikili_skor')
for v,w in [([0,0],0),([1000,999],0),([-1000,-999],1),([0,1],1)]:
    r=ikili_skor(v);eq(r['secim'],w,'ikili tercih ve tie')
    yakin(sum(r['olasilik']),1,'normalizasyon')
    import math
    yakin(r['olasilik'][0],1/(1+math.exp(v[1]-v[0])),'stabil softmax')
for bad in ([],[1],[1,2,3],(1,2),[True,0],[float('nan'),0],[0,float('inf')],['1',0]):raises(ValueError,ikili_skor,bad,msg='iki sonlu logit gerekli')
```

```setup
import sys,importlib
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parents[1]))
if 'ai_lab' not in sys.modules:sys.modules['ai_lab']=importlib.import_module('sandbox.ai_gercek_lab')
from sandbox.ai_gercek_ai_saldiri_53 import hazirla
hazirla()
```

```hint
Sınırları ve sıfır gradient/epsilon durumunu ayrı dene; input listelerini yerinde değiştirme.
```
:::

::: gorev 2 · Targeted adımı epsilon kutusuna projekte et
`pgd_adimi(x0,xt,g,eps,alpha)` aynı uzunlukta boş olmayan düz listeleri alır. Hepsi sonlu sayı, bool değil; x0/xt pikseli 0–1; eps ve alpha 0–1 sonlu sayı. Diğerlerinde ValueError. Her piksel için y=xt−alpha*sign(g), sonra x0±eps aralığına ve 0–1'e clamp uygula. g=0 adım üretmez. Girdileri değiştirme. Liste döndür. Epsilon tüm iterasyonlar boyunca ilk x0'a göre ölçülür, önceki adıma göre değil.

```starter
def pgd_adimi(x0,xt,g,eps,alpha):
    return [b+alpha for b in xt]
```

```solution
def pgd_adimi(x0,xt,g,eps,alpha):
    import math
    if not all(isinstance(v,list) for v in (x0,xt,g)) or not x0 or len(x0)!=len(xt) or len(x0)!=len(g):raise ValueError('boyut')
    for v in (eps,alpha):
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<=v<=1:raise ValueError('butce')
    for row in (x0,xt,g):
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in row):raise ValueError('piksel/gradient')
    if any(not 0<=v<=1 for row in (x0,xt) for v in row):raise ValueError('piksel araligi')
    out=[]
    for a,b,c in zip(x0,xt,g):
        sign=1 if c>0 else -1 if c<0 else 0
        y=b-alpha*sign
        out.append(max(0,min(1,max(a-eps,min(a+eps,y)))))
    return out

from pathlib import Path
print(Path("vlm/ornek.json").read_text(encoding="utf-8"))
```

```test
need('pgd_adimi')
for v in ('0.2',float('nan'),float('inf')):
    raises(ValueError,pgd_adimi,[0],[0],[1],v,0.1,msg='eps tipi/sonluluk')
    raises(ValueError,pgd_adimi,[0],[0],[1],0.2,v,msg='alpha tipi/sonluluk')
for args in [(['0'],[0],[1],0.2,0.1),([0],[0],['1'],0.2,0.1),([False],[0],[1],0.2,0.1),([0],[False],[1],0.2,0.1),([0],[0],[1],0.2,True)]:raises(ValueError,pgd_adimi,*args,msg='sayı yerine string/bool ret')
import copy
_x0=[0,0.25,0.5,0.75,1];_xt=list(_x0);_grad=[-1,2,0,-2,1];_inputs=copy.deepcopy((_x0,_xt,_grad))
_got=pgd_adimi(_x0,_xt,_grad,0.25,0.125)
eq((_got,(_x0,_xt,_grad)),([0.125,0.125,0.5,0.875,0.875],_inputs),'targeted step doğru; girdiler değişmedi')
eq(pgd_adimi([0,1],[0.75,0.25],[-1,1],0.25,1),[0.25,0.75],'x0 merkezli epsilon projeksiyonu')
eq(pgd_adimi([0,1],[0,1],[1,-1],1,1),[0,1],'piksel clamp')
eq(pgd_adimi([0.5],[0.75],[1],0,0.25),[0.5],'eps0 x0 döndürür')
eq(pgd_adimi([0.5],[0.5],[1],0.25,0),[0.5],'alpha0')
for args in [([],[],[],0,0),([0],[0,1],[1],0.2,0.1),([0],[0],[1,2],0.2,0.1),((0,),[0],[1],0.2,0.1),([0],[0],[True],0.2,0.1),([0],[0],[float('nan')],0.2,0.1),([-1],[0],[1],0.2,0.1),([0],[2],[1],0.2,0.1),([0],[0],[1],True,0.1),([0],[0],[1],-0.1,0.1),([0],[0],[1],1.1,0.1),([0],[0],[1],0.2,-0.1),([0],[0],[1],0.2,1.1)]:raises(ValueError,pgd_adimi,*args,msg='boyut/tip/sonlu/bütçe doğrulaması')
```

```setup
import sys,importlib
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parents[1]))
if 'ai_lab' not in sys.modules:sys.modules['ai_lab']=importlib.import_module('sandbox.ai_gercek_lab')
from sandbox.ai_gercek_ai_saldiri_53 import hazirla
hazirla()
```

```hint
Sınırları ve sıfır gradient/epsilon durumunu ayrı dene; input listelerini yerinde değiştirme.
```
:::

::: gorev 3 · Tercih değişimi raporunu doğru say
`degisim_raporu(rows)` tam id/hedef/once/sonra alanlı boş olmayan dict listesi alır. id benzersiz boş olmayan str; diğerleri bool olmayan 0/1 int. Diğerlerinde ValueError. Dönen alanlar toplam, hedef_zaten_once, hedef_sonra, hedefe_donen, yeni_basari_orani. Yeni başarı yalnız once!=hedef ve sonra==hedef. Payda toplam−hedef_zaten_once; sıfırsa None.

```starter
def degisim_raporu(rows):
    return {'yeni_basari_orani':1}
```

```solution
def degisim_raporu(rows):
    import math
    if not isinstance(rows,list) or not rows:raise ValueError('kayit')
    ids=set();once=sonra=donen=0
    for r in rows:
        if not isinstance(r,dict) or set(r)!={'id','hedef','once','sonra'} or not isinstance(r['id'],str) or not r['id'] or r['id'] in ids:raise ValueError('sema')
        ids.add(r['id'])
        if any(type(r[k]) is not int or r[k] not in (0,1) for k in ('hedef','once','sonra')):raise ValueError('indeks')
        once+=r['once']==r['hedef'];sonra+=r['sonra']==r['hedef'];donen+=r['once']!=r['hedef'] and r['sonra']==r['hedef']
    n=len(rows)-once
    return {'toplam':len(rows),'hedef_zaten_once':once,'hedef_sonra':sonra,'hedefe_donen':donen,'yeni_basari_orani':donen/n if n else None}

from pathlib import Path
print(Path("vlm/ornek.json").read_text(encoding="utf-8"))
```

```test
need('degisim_raporu')
eq(degisim_raporu([{'id':'flip','hedef':0,'once':1,'sonra':0}]),{'toplam':1,'hedef_zaten_once':0,'hedef_sonra':1,'hedefe_donen':1,'yeni_basari_orani':1.0},'tek yeni hedef değişimi')
raises(ValueError,degisim_raporu,[{'id':1,'hedef':0,'once':0,'sonra':1}],msg='id string olmalı')
rows=[{'id':'a','hedef':1,'once':0,'sonra':1},{'id':'b','hedef':1,'once':1,'sonra':1},{'id':'c','hedef':0,'once':1,'sonra':1},{'id':'d','hedef':1,'once':1,'sonra':0}]
eq(degisim_raporu(rows),{'toplam':4,'hedef_zaten_once':2,'hedef_sonra':2,'hedefe_donen':1,'yeni_basari_orani':0.5},'zaten hedefte olanı veya hedeften çıkanı karıştırma')
eq(degisim_raporu([rows[1]])['yeni_basari_orani'],None,'payda sıfırsa None')
eq(degisim_raporu([rows[2]])['yeni_basari_orani'],0,'yeni başarı yok')
for bad in ([],tuple(rows),[None],[dict(rows[0],id='')],rows+[rows[0]],[dict(rows[0],once=True)],[dict(rows[0],hedef=2)],[dict(rows[0],sonra='1')],[dict(rows[0],extra=1)]):raises(ValueError,degisim_raporu,bad,msg='tam şema ve indeks')
```

```setup
import sys,importlib
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parents[1]))
if 'ai_lab' not in sys.modules:sys.modules['ai_lab']=importlib.import_module('sandbox.ai_gercek_lab')
from sandbox.ai_gercek_ai_saldiri_53 import hazirla
hazirla()
```

```hint
Sınırları ve sıfır gradient/epsilon durumunu ayrı dene; input listelerini yerinde değiştirme.
```
:::

::: tahmin Hedefli kayıpta piksel yönü
Targeted loss için pozitif gradient görülen piksel hangi yönde hareket eder?
```python
x0=0.5
gradient=2
alpha=0.125
print(x0-alpha*(1 if gradient>0 else -1))
```
???
```cikti
0.375
```
Targeted loss'u azaltmak için gradient descent uygulanır. Bu sentetik skaler hesap, gerçek VLM gradienti değildir. Tahmininle çıktı arasındaki farkı kendi cümlenle yaz; artı işareti kullansaydın hedefli kaybın hangi yönde zorlanacağını açıkla.
:::

::: anlat Hata vitrini · hedef token logiti arttı, tercih neden değişmedi?
Gerçek ilk fizibilite sondasında red/blue logitleri önce 11.798/9.888, sonra 16.478/10.450 oldu. Blue logiti artsa da red daha fazla arttı; “blue'ya atlatıldı” demek yanlıştı. Bu kaydedilmiş tek sonda `outputs/vlm53-kurulum/probe-*` dosyasında `kabul=false` olarak saklıdır; genel model başarısı değildir. Son deneyin amacı iki token arasındaki göreli targeted loss olduğundan objective'i de buna göre kurar. Serbest model yanıtının değiştiği iddia edilmez.

PNG'ye yazmadan yalnız float tensoru ölçmek de yanıltır: uint8 yuvarlaması pikseli değiştirebilir. Gerçek son görev kaydedilmiş PNG'yi yeniden okuyup hem L-infinity bütçesini hem VLM skorunu tekrar ölçer. Epsilon 0 kontrolü tekrar üretilemiyorsa deney kabul edilmez. Savunma bağlantısı: bütçe/ölçüm doğruluğu ai-guvence-07'nin kavramıdır; burada model VLM ve saldırı hedefi next-token tercihidir.
:::

::: gorev Gerçek deney · Piksel PGD ve PNG round-trip
Önceki üç fonksiyonu birleştir. CALISTIR bloğunu koru: Çalıştır gerçek VLM/autograd ölçümü ve deneme kanıtı üretir; Kontrol ayrıca kabul kanıtı yazar. İki sentetik görsel, epsilon 0 ve 8/255, alpha 2/255, 3 adım. Gerçek gradient tensorü öğrenci fonksiyonuna düz sayı listesi olarak verilir; bu, önceden yazılmış gradient tablosu değildir. Modelin normalize edilmiş girişine geçiş de autograd zincirinin içindedir. Parametreler güncellenmez.

Kanıt dosyası token ID, model SHA-256, revizyon, sürüm, prompt, normalize ayarı, gradient normu, logit, piksel bütçesi ve PNG yollarını içerir. Çıktıdaki görsel klasörü yolunu Dosya Gezgini'ne yapıştır. Kendi temiz ve attack PNG'lerini aç; epsilon 0 ile attack grubunun iki token tercihini kendi cümlenle karşılaştır. Saldırının başarılı olması geçme şartı değildir. Model yokluğu, sıfır/bozuk gradient, yanlış projeksiyon veya yapılmamış ölçüm PASS değildir.

```starter
import ai_lab
def ikili_skor(logitler):return {}
def pgd_adimi(x0,xt,g,eps,alpha):return xt
def degisim_raporu(rows):return {}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_53 as D
    D.goster(ikili_skor,pgd_adimi,degisim_raporu)
```

```solution
import ai_lab

def ikili_skor(logitler):
    import math
    if not isinstance(logitler,list) or len(logitler)!=2 or any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in logitler):raise ValueError('iki sonlu logit')
    m=max(logitler);a=[math.exp(x-m) for x in logitler];z=sum(a)
    return {'olasilik':[x/z for x in a],'secim':0 if logitler[0]>=logitler[1] else 1}

def pgd_adimi(x0,xt,g,eps,alpha):
    import math
    if not all(isinstance(v,list) for v in (x0,xt,g)) or not x0 or len(x0)!=len(xt) or len(x0)!=len(g):raise ValueError('boyut')
    for v in (eps,alpha):
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<=v<=1:raise ValueError('butce')
    for row in (x0,xt,g):
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in row):raise ValueError('piksel/gradient')
    if any(not 0<=v<=1 for row in (x0,xt) for v in row):raise ValueError('piksel araligi')
    out=[]
    for a,b,c in zip(x0,xt,g):
        sign=1 if c>0 else -1 if c<0 else 0
        y=b-alpha*sign
        out.append(max(0,min(1,max(a-eps,min(a+eps,y)))))
    return out

def degisim_raporu(rows):
    import math
    if not isinstance(rows,list) or not rows:raise ValueError('kayit')
    ids=set();once=sonra=donen=0
    for r in rows:
        if not isinstance(r,dict) or set(r)!={'id','hedef','once','sonra'} or not isinstance(r['id'],str) or not r['id'] or r['id'] in ids:raise ValueError('sema')
        ids.add(r['id'])
        if any(type(r[k]) is not int or r[k] not in (0,1) for k in ('hedef','once','sonra')):raise ValueError('indeks')
        once+=r['once']==r['hedef'];sonra+=r['sonra']==r['hedef'];donen+=r['once']!=r['hedef'] and r['sonra']==r['hedef']
    n=len(rows)-once
    return {'toplam':len(rows),'hedef_zaten_once':once,'hedef_sonra':sonra,'hedefe_donen':donen,'yeni_basari_orani':donen/n if n else None}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_53 as D
    D.goster(ikili_skor,pgd_adimi,degisim_raporu)
```

```test
import ai_lab
checks=[]
def kontrol(x,msg):checks.append(bool(x));ok(x,msg)
_eq=eq;_raises=raises;_yakin=yakin
def eq(*a,**k):r=_eq(*a,**k);checks.append(r);return r
def raises(*a,**k):r=_raises(*a,**k);checks.append(r);return r
def yakin(*a,**k):r=_yakin(*a,**k);checks.append(r);return r
issues=ai_lab.kod_denetimi(src,('ref_ikili_skor','ref_pgd_adimi','ref_degisim_raporu','kanit_yaz'),izin=())
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
need('ikili_skor')
for v,w in [([0,0],0),([1000,999],0),([-1000,-999],1),([0,1],1)]:
    r=ikili_skor(v);eq(r['secim'],w,'ikili tercih ve tie')
    yakin(sum(r['olasilik']),1,'normalizasyon')
    import math
    yakin(r['olasilik'][0],1/(1+math.exp(v[1]-v[0])),'stabil softmax')
for bad in ([],[1],[1,2,3],(1,2),[True,0],[float('nan'),0],[0,float('inf')],['1',0]):raises(ValueError,ikili_skor,bad,msg='iki sonlu logit gerekli')

need('pgd_adimi')
for v in ('0.2',float('nan'),float('inf')):
    raises(ValueError,pgd_adimi,[0],[0],[1],v,0.1,msg='eps tipi/sonluluk')
    raises(ValueError,pgd_adimi,[0],[0],[1],0.2,v,msg='alpha tipi/sonluluk')
for args in [(['0'],[0],[1],0.2,0.1),([0],[0],['1'],0.2,0.1),([False],[0],[1],0.2,0.1),([0],[False],[1],0.2,0.1),([0],[0],[1],0.2,True)]:raises(ValueError,pgd_adimi,*args,msg='sayı yerine string/bool ret')
import copy
_x0=[0,0.25,0.5,0.75,1];_xt=list(_x0);_grad=[-1,2,0,-2,1];_inputs=copy.deepcopy((_x0,_xt,_grad))
_got=pgd_adimi(_x0,_xt,_grad,0.25,0.125)
eq((_got,(_x0,_xt,_grad)),([0.125,0.125,0.5,0.875,0.875],_inputs),'targeted step doğru; girdiler değişmedi')
eq(pgd_adimi([0,1],[0.75,0.25],[-1,1],0.25,1),[0.25,0.75],'x0 merkezli epsilon projeksiyonu')
eq(pgd_adimi([0,1],[0,1],[1,-1],1,1),[0,1],'piksel clamp')
eq(pgd_adimi([0.5],[0.75],[1],0,0.25),[0.5],'eps0 x0 döndürür')
eq(pgd_adimi([0.5],[0.5],[1],0.25,0),[0.5],'alpha0')
for args in [([],[],[],0,0),([0],[0,1],[1],0.2,0.1),([0],[0],[1,2],0.2,0.1),((0,),[0],[1],0.2,0.1),([0],[0],[True],0.2,0.1),([0],[0],[float('nan')],0.2,0.1),([-1],[0],[1],0.2,0.1),([0],[2],[1],0.2,0.1),([0],[0],[1],True,0.1),([0],[0],[1],-0.1,0.1),([0],[0],[1],1.1,0.1),([0],[0],[1],0.2,-0.1),([0],[0],[1],0.2,1.1)]:raises(ValueError,pgd_adimi,*args,msg='boyut/tip/sonlu/bütçe doğrulaması')

need('degisim_raporu')
eq(degisim_raporu([{'id':'flip','hedef':0,'once':1,'sonra':0}]),{'toplam':1,'hedef_zaten_once':0,'hedef_sonra':1,'hedefe_donen':1,'yeni_basari_orani':1.0},'tek yeni hedef değişimi')
raises(ValueError,degisim_raporu,[{'id':1,'hedef':0,'once':0,'sonra':1}],msg='id string olmalı')
rows=[{'id':'a','hedef':1,'once':0,'sonra':1},{'id':'b','hedef':1,'once':1,'sonra':1},{'id':'c','hedef':0,'once':1,'sonra':1},{'id':'d','hedef':1,'once':1,'sonra':0}]
eq(degisim_raporu(rows),{'toplam':4,'hedef_zaten_once':2,'hedef_sonra':2,'hedefe_donen':1,'yeni_basari_orani':0.5},'zaten hedefte olanı veya hedeften çıkanı karıştırma')
eq(degisim_raporu([rows[1]])['yeni_basari_orani'],None,'payda sıfırsa None')
eq(degisim_raporu([rows[2]])['yeni_basari_orani'],0,'yeni başarı yok')
for bad in ([],tuple(rows),[None],[dict(rows[0],id='')],rows+[rows[0]],[dict(rows[0],once=True)],[dict(rows[0],hedef=2)],[dict(rows[0],sonra='1')],[dict(rows[0],extra=1)]):raises(ValueError,degisim_raporu,bad,msg='tam şema ve indeks')

if not all(checks):stop()
from sandbox import ai_gercek_ai_saldiri_53 as D
try:r=D.deney(ikili_skor,pgd_adimi,degisim_raporu)
except ai_lab.GercekLabYok as e:
    kontrol(False,'gerçek deney yok: '+str(e));stop()
kontrol(all(r['kontroller']) and len(r['observations'])==4,'gerçek VLM ölçümü ve epsilon 0 kontrolü')
kontrol(r['model']['parameters_frozen'],'model parametreleri donuk')
kontrol(all(len(o['steps'])==3 and all(s['grad_norm']>0 for s in o['steps']) for o in r['observations']),'12 gerçek piksel autograd adımı')
kontrol(all(o['linf_png']<=o['eps']+1e-6 for o in r['observations']),'PNG yeniden okuma bütçesi')
ai_lab.kanit_yaz('saldiri53-kabul',{'kaynak':'gercek','kabul':all(checks),'ders':'ai-saldiri-53','deney':r})
```

```setup
import sys,importlib
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parents[1]))
if 'ai_lab' not in sys.modules:sys.modules['ai_lab']=importlib.import_module('sandbox.ai_gercek_lab')
from sandbox.ai_gercek_ai_saldiri_53 import hazirla
hazirla()
```

```meta
motor: ai-gercek
gereksinim: torch
ortam: gpu
timeout: 300
```

```hint
İlk üç sözleşmeyi birleştir; hedefli iniş işaretini ve x0 merkezli projeksiyonu koru. Gerçek model yüklendiğinde CPU/GPU ölçümü kanıta yazılır.
```
:::

::: anlat Sınır
Bu ders iki token tercihine yönelik gerçek VLM piksel perturbation ölçer; genel VLM jailbreak başarısını, serbest üretilmiş yanıt değişimini veya tüm görsel savunmaların dayanıklılığını gösteremez.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
### Hedefli piksel inişi iki kısıtı birlikte korur

Hedef tokenın kaybını azaltmak için xt-alpha*sign(g) adımı atılır; artı işareti hedefli inişi tersine çevirir. Ardından önce x0 merkezli epsilon kutusu, sonra geçerli [0, 1] piksel aralığı korunur. Model ağırlıkları donukken gradient piksel girdisine akar. Epsilon 0 kontrolü değişiklik olmamasını sınar. Float tensördeki bütçe yeterli değildir; PNG kuantizasyonundan sonra dosya tekrar okunup Linf ölçülür. İki token arasındaki tercih değişimi serbest yanıtın jailbreak olduğu sonucunu vermez.

| Yaygın yanlış | Mekanizmanın söylediği |
|---|---|
| Donuk modelde gradient olmaz | Ağırlıkların güncellenmemesi, girişe göre türevin hesaplanmasını engellemez. |

Sonraki bağlantı: ai-guvence-07 ile hedefli/hedefsiz perturbation ayrımı.
:::
