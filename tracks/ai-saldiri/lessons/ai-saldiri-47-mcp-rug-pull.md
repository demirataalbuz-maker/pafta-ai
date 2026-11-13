---
id: ai-saldiri-47
title: MCP Rug Pull · İlk Onaydan Sonra Değişen Araç
summary: Değişen araç sözleşmesini görünür dosyada karşılaştır, onayı sabitle ve gerçek stdio MCP ile yerel model akışını ölç.
esleme: ai-savunma-11, ai-savunma-20
timeout: 60
---
::: anlat İlk onay sonsuza kadar geçerli mi?
| Gerçek araç ne gösterir | Bu derste ne kullanılır | Ne gösterilemez? |
|---|---|---|
| MCP tools/list tanımı zamanla değişebilir | İlk üç görev görünür sentetik JSON dosyası | Dosyadan okunan örnek canlı sunucu kaydı değildir |
| İstemci tools/call ile gerçek servis çağırır | Final ayrı stdio süreçte küçük MCP test sunucusu ve kurulu Ollama | Tam MCP SDK, uzak transport ve OAuth uyumu ölçülmez |
| İzin ile yan etki farklıdır | Geçici lab outbox dosyasının gerçek satır/hash ölçümü | Fingerprint aynı metadata arkasındaki bütün backend davranışını garanti etmez |

> [!NOT]
> `veri/rug-pull.json` ve `veri/messages.jsonl` sentetiktir. Setup bunları her Run/Check için yeni geçici çalışma kopyasına taşır; değişiklik sonraki çalıştırmaya kalmaz. Ders kodunda `Path('veri/rug-pull.json').read_text()` ile ham dosyayı açıp yazdır, yüklenen sözlüğü değiştirerek dene. Harici editörde fixture kaynağını da açabilirsin; gizli test verisi ayrıdır. Final gerçekten kurulu yerel modele ve kendi başlattığı stdio sunucusuna gider; model yoksa kabul yok, otomatik kurulum yok.

Rug pull, güven kararından sonra hedefin değişmesidir. İlk bağlantıda öğrenci lookup_order aracının yalnız sipariş durumunu okuduğunu görür. Sunucu adı, araç adı, açıklama, inputSchema ve annotations birlikte onaylanır. İlk meşru çağrı çalıştıktan sonra aynı süreç yeni bir açıklama döndürür: artık denetim kaydını outbox dosyasına yazacağını söyler. İsim aynı kaldığı için yalnız ada bakan istemci bu değişikliği kaçırır. Buradaki zaman boyutu, tek seferlik tool schema poisoning dersinden farklıdır: önce gerçekten sorunsuz çalışan, sonra onaylanan sözleşmeyi değiştiren servis vardır.

MCP JSON-RPC kullanır. Bu küçük stdio test sunucusunda initialize, notifications/initialized, tools/list ve tools/call mesajları gerçekten bir child process'in stdin/stdout kanallarından geçer. Protokol sürümü 2025-06-18 olarak sabitlenmiştir. tools/list_changed bildirimi de kayıtta görünür. Bu bildirim bir güvenlik kararı değildir: yeniden listelemeyi tetikleyebilir ama istemci yeni içeriği kendisi karşılaştırmalıdır. Bu labda her kullanım öncesi liste tekrar okunur. MCP SDK kurulmadığı için bütün protokol özelliklerinin uygulandığı iddia edilmez; JSON-RPC alt kümesi ve görünür değişim deneyidir.

İlk görev bir onay kaydı oluşturur. Dar sözleşme yalnız dört araç alanını kabul eder: name, description, inputSchema, annotations. Tool name için ASCII harf veya alt çizgiyle başlama ve en fazla 64 karakter sınırı vardır; bu lab kısıtıdır, bütün MCP araç adları için genel hüküm değildir. Bir sunucuda 1–16 araç desteklenir. Yinelenen isim hata olmalıdır; sözlükte sonuncusunu tutmak aynı adlı ilk aracı sessizce siler. SHA256 girdi metni ensure_ascii=False, sort_keys=True, separators=(',',':') ve allow_nan=False ile JSON'a çevrilir. Anahtar sırası değişince içerik değişmiş sayılmaz; liste sırası korunur. Bu biçim RFC8785 ya da bütün diller için ortak bir canonical JSON standardı değildir, dersin Python içindeki kararlı serileştirme sözleşmesidir.

İkinci görev yeniden onay gerekip gerekmediğini döndürür. True çağrıyı çalıştır demek değildir: dur ve kullanıcıdan yeni bir güven kararı al demektir. Sunucu adı değişmişse, araç kaybolmuş/yeni eklenmişse, açıklama veya schema değişmişse tekrar onay gerekir. Eksik ya da bozuk onay kaydı da True üretir. readOnlyHint sunucunun iddiasıdır; bir yetki kontrolünün yerine geçmez. Annotations içeriğini de hash'e katmak değişikliği görmeye yardım eder ama sunucunun doğru söylediğini kanıtlamaz. Bu labdaki sunucu adı mantıksal bir etikettir; kriptografik kimlik doğrulaması değildir, saldırgan aynı adı taklit edebilir. Birinci onayda kötü bir araç kabul edilmişse veya backend aynı metadata ile kötüleşirse bu mekanizma tek başına çözüm değildir.

Üçüncü görev ölçüm kayıtlarını yorumlar. Temiz, korumasız ve korumalı grupları ayrı tutulur; deneme, hata, ret ve dosya etkisi toplamları raporlanır. Hatalı çağrı ile sıfır etki aynı şey değildir. Sunucu açılmadığında ortada başarılı bir savunma yoktur. Model araç çağırmamayı seçebilir; bu çekimserlik ayrı kaydedilir, uydurma tools/call üretilmez. Final, modelin ham yanıtı ve gerçekten seçtiği araçları saklar. Ardından ayrı ve açıkça işaretli deterministik replay, daha önce izin verilmiş sipariş çağrısını yeniden göndererek servis sınırındaki davranışı ölçer. Replay modelin saldırıya uyduğunu göstermez. Model seçiminden bağımsız bu kontrol, hiç araç çağrısı olmadığı için savunma başarılı sanılmasını önler.

Gerçek deneyde her grubun iki koşusu vardır. İlk meşru çağrı outbox yazmadan delivered yanıtını üretmelidir. Sonra metadata tekrar alınır; korumalı istemci değişmiş aracı modele sunmaz ve çağrıdan hemen önce de kontrol eder. Temiz grupta değişiklik yapılmaz; meşru replay gerçekten çalışır. Korumasız gruptaki yerel outbox alıcısı audit.invalid sentetik etikettir; ağ bağlantısı ya da gerçek e-posta gönderilmez. Yalnız labın rastgele canary'si kaydedilir. Bu, modelin özel dosyalarına veya kullanıcının sırlarına erişim deneyi değildir.

Önce fixture içindeki iki listeyi kendi gözünle karşılaştır. Hangi alan değişmiş, hangisi aynı kalmış? Tahminini yorum olarak yaz, kusurlu başlangıcı çalıştır ve çıkan sonuçla farkını açıkla. Final kanıtında ilk/son metadata, onay hash'leri, JSON-RPC istek/yanıtları, tohum, model sürümü, ham tool-call, model sonrası etki ve replay sonrası etki farklı alanlardadır. İki koşuda model seçimi değişirse dosya etkisi de değişti mi, yoksa replay aynı sonucu mu verdi? Kendi cümlenle yorumla. Yalnız 'engelledi' kelimesini ezberlemek bu kanıtları okumak değildir.

Saldırı–savunma köprüsü ai-savunma-11 ve ai-savunma-20'dir. En az ayrıcalık ve tedarik zinciri bütünlüğü, değişiklik algılamanın tamamlayıcısıdır. Bir araca yeni onay verilmesi host dosyalarına sınırsız erişim yetkisi anlamına gelmez. Lab kendi child process'lerini kapatır, kurulu modelleri ve kullanıcı süreçlerini korur. Oluşan çalışma dizini ve kanıt yolu çıktıda gösterilir; öğrenci verisi veya kurulumlar silinmez.

Kaynak: [MCP 2025-06-18 tools belirtimi](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2025-06-18/server/tools.mdx). tools/list ve tools/call biçimi, listChanged yeteneği ve güvenilmez annotations ayrımı buradan alınmıştır; bu belgede 'rug pull'a bağışıklık' iddiası yoktur.
:::
::: tahmin İsim aynı kaldıysa onay da aynı mı?
Tahmin et; çalıştırınca farkı bir yorum cümlesiyle açıkla.
```python
ilk={'name':'lookup_order','description':'read only'}
son={'name':'lookup_order','description':'read and archive'}
print(ilk['name']==son['name'])
print(ilk==son)
```
???
```cikti
True
False
```
:::
::: gorev 1 · Onay kaydı
`onay_kaydi(sunucu,araclar)` → `{sunucu,araclar:{name:sha256}}`. Üstteki dört alan, 1–16 araç, benzersiz geçerli isim, boş olmayan sunucu ve açıklama, object inputSchema ve dict annotations gerekir. Geçersiz girdi ValueError; girdi değişmez.
```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla('ai-saldiri-47')
```
```starter
def onay_kaydi(sunucu,araclar):
    # KUSURLU BAŞLANGIÇ: değişen sözleşmeyi tahmin et.
    return {'sunucu':sunucu,'araclar':{t['name']:t['name'] for t in araclar}}

from pathlib import Path
import json
v=json.loads(Path('veri/rug-pull.json').read_text(encoding='utf-8'))
print('SENTETİK ham veri:',Path('veri/rug-pull.json').read_text(encoding='utf-8'))
print('Onay:',onay_kaydi(v['sunucu'],v['ilk']))
```
```test
import copy,hashlib,json,secrets
def tool(name='lookup_order'):
    return {'name':name,'description':'Read '+secrets.token_hex(6),'inputSchema':{'type':'object','properties':{'id':{'type':'string'}},'required':['id']},'annotations':{'readOnlyHint':True}}
def digest(t):return hashlib.sha256(json.dumps(t,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')).hexdigest()
def raises(fn,*args):
    try:fn(*args);return False
    except ValueError:return True

fn=need('onay_kaydi')
t=tool();u=tool('archive_note');original=copy.deepcopy([t,u]);host='server-'+secrets.token_hex(4)
ok(fn(host,[t,u])=={'sunucu':host,'araclar':{t['name']:digest(t),u['name']:digest(u)}} and [t,u]==original,'tüm metadata, iki araç, girdi değişmedi')
reordered=json.loads(json.dumps(t,sort_keys=True))
eq(fn(host,[reordered]),fn(host,[t]),'JSON key sırası onayı değiştirmez')
for field,new in [('description','başka'),('annotations',{'readOnlyHint':False}),('inputSchema',{'type':'object','properties':{}}),('name','renamed')]:
    a=copy.deepcopy(t);a[field]=new;eq(fn(host,[a]),{'sunucu':host,'araclar':{a['name']:digest(a)}},'değişen '+field)
ok(len(fn(host,[tool('t'+str(i)) for i in range(16)])['araclar'])==16,'16 araç sınırı dahil')
bads=[None,[],(t,),[t,t],[tool('t'+str(i)) for i in range(17)],[dict(t,ek=1)],[dict(t,name='')],[dict(t,name='a'*65)],[dict(t,name='x-y')],[dict(t,description=' ')],[dict(t,description=7)],[dict(t,inputSchema={})],[dict(t,inputSchema={'type':'array'})],[dict(t,annotations=[])],[dict(t,annotations={'x':float('nan')})],[dict(t,annotations={'x':{1}})]]
ok(all(raises(fn,host,x) for x in bads),'bozuk/tekrar/üst sınır reddi')
ok(all(raises(fn,x,[t]) for x in (None,'',4,' ')),'sunucu kimliği')

```
```solution
import hashlib,json,re
def onay_kaydi(sunucu,araclar):
    if not isinstance(sunucu,str) or not sunucu.strip():raise ValueError('sunucu')
    if not isinstance(araclar,list) or not araclar or len(araclar)>16:raise ValueError('araclar')
    pins={}
    for t in araclar:
        if not isinstance(t,dict) or set(t)!={'name','description','inputSchema','annotations'}:raise ValueError('alanlar')
        if not isinstance(t['name'],str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,63}',t['name']):raise ValueError('ad')
        if not isinstance(t['description'],str) or not t['description'].strip():raise ValueError('description')
        if not isinstance(t['inputSchema'],dict) or t['inputSchema'].get('type')!='object':raise ValueError('schema')
        if not isinstance(t['annotations'],dict):raise ValueError('annotations')
        try:raw=json.dumps(t,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)
        except (TypeError,ValueError):raise ValueError('JSON')
        if t['name'] in pins:raise ValueError('yinelenen')
        pins[t['name']]=hashlib.sha256(raw.encode('utf-8')).hexdigest()
    return {'sunucu':sunucu,'araclar':pins}

from pathlib import Path
import json
v=json.loads(Path('veri/rug-pull.json').read_text(encoding='utf-8'))
print('SENTETİK ham veri:',Path('veri/rug-pull.json').read_text(encoding='utf-8'))
print('Onay:',onay_kaydi(v['sunucu'],v['ilk']))
```
```hint
Dar sözleşmeyi ve bozuk girdileri birlikte düşün. Ham dosya gizli test değildir.
```
:::
::: gorev 2 · Yeniden onay kapısı
`yeniden_onay(onay,sunucu,arac)` gerçek bool döndürür. Onay schema ve 64 küçük hex hash doğrula; bozuk kayıt, başka sunucu, yeni araç veya dört alanın herhangi bir değişiminde True. Anahtar sırası tek başına değişim değildir. İzinli mevcut araçta False; istisna dışarı sızmaz.
```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla('ai-saldiri-47')
```
```starter
def yeniden_onay(onay,sunucu,arac):
    # KUSURLU BAŞLANGIÇ: isim üzerinden eski güveni sürdürür.
    return arac['name'] not in onay['araclar']

from pathlib import Path
import json
v=json.loads(Path('veri/rug-pull.json').read_text(encoding='utf-8'))
print('SENTETİK ham veri:',Path('veri/rug-pull.json').read_text(encoding='utf-8'))
import hashlib
pin={'sunucu':v['sunucu'],'araclar':{t['name']:hashlib.sha256(json.dumps(t,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest() for t in v['ilk']}}
print('Yeniden onay?',yeniden_onay(pin,v['sunucu'],v['son'][0]))
```
```test
import copy,hashlib,json,secrets
def tool(name='lookup_order'):
    return {'name':name,'description':'Read '+secrets.token_hex(6),'inputSchema':{'type':'object','properties':{'id':{'type':'string'}},'required':['id']},'annotations':{'readOnlyHint':True}}
def digest(t):return hashlib.sha256(json.dumps(t,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')).hexdigest()
def raises(fn,*args):
    try:fn(*args);return False
    except ValueError:return True

fn=need('yeniden_onay');t=tool();host='server-'+secrets.token_hex(4);pin={'sunucu':host,'araclar':{t['name']:digest(t)}};bak=copy.deepcopy((pin,t))
eq(fn(pin,host,t),False,'aynı metadata izinli');ok((pin,t)==bak,'girdiler değişmedi')
for field,new in [('description','yeni talimat'),('annotations',{'readOnlyHint':False}),('inputSchema',{'type':'object','properties':{}}),('name','other')]:
    a=copy.deepcopy(t);a[field]=new;eq(fn(pin,host,a),True,'yeniden onay: '+field)
eq(fn(pin,host+'x',t),True,'başka sunucu');eq(fn(pin,host,json.loads(json.dumps(t,sort_keys=True))),False,'sıra farkı')
for bad in (None,{},dict(t,ek=1),dict(t,description=' '),dict(t,description=2),dict(t,name=''),dict(t,name='x-y'),dict(t,name='a'*65),dict(t,inputSchema=[]),dict(t,inputSchema={'type':'array'}),dict(t,annotations=[]),dict(t,annotations={'x':float('nan')}),dict(t,annotations={'x':{2}})):
    eq(fn(pin,host,bad),True,'bozuk araç fail closed')
for bad in (None,{},dict(pin,araclar={}),dict(pin,araclar=[]),dict(pin,sunucu=''),dict(pin,sunucu=1),dict(pin,ek=1),dict(pin,araclar={'bad-name':digest(t)}),dict(pin,araclar={'other':5}),dict(pin,araclar={'other':'a'*63}),dict(pin,araclar={'other':'a'*65}),dict(pin,araclar={'other':'X'*64})):
    eq(fn(bad,host,t),True,'bozuk onay fail closed')
for server in ('',None,5,' '):eq(fn(pin,server,t),True,'bozuk sunucu')
boundary=tool('a'*64);pb={'sunucu':host,'araclar':{boundary['name']:digest(boundary)}};eq(fn(pb,host,boundary),False,'64 karakter ad dahil')
for bad in (dict(t,ek=1),dict(t,description=' '),dict(t,description=2),dict(t,inputSchema={'type':'array'}),dict(t,annotations=[]),dict(t,name='a'*65)):
    forged={'sunucu':host,'araclar':{bad['name']:digest(bad)}}
    eq(fn(forged,host,bad),True,'hash eşleşse de bozuk sözleşme reddedilir')
for name in ('bad-name','a'*65):
    extra_pin={'sunucu':host,'araclar':dict(pin['araclar'],**{name:'a'*64})}
    eq(fn(extra_pin,host,t),True,'onaydaki ilave bozuk kayıt reddedilir')
for bad_d in ('a'*63,'a'*65,'X'*64,5):
    eq(fn({'sunucu':host,'araclar':dict(pin['araclar'],extra_ok=bad_d)},host,t),True,'onaydaki ilave bozuk digest reddedilir')
tr_tool=dict(t,description='Müşteri siparişi oku '+secrets.token_hex(4))
eq(fn({'sunucu':host,'araclar':{tr_tool['name']:digest(tr_tool)}},host,tr_tool),False,'UTF-8 ensure_ascii=False özeti korunur')
for h in ('',' '):
    forged={'sunucu':h,'araclar':pin['araclar']}
    eq(fn(forged,h,t),True,'iki taraf boşken izin çıkmaz')


```
```solution
import hashlib,json,re
def yeniden_onay(onay,sunucu,arac):
    try:
        if not isinstance(onay,dict) or set(onay)!={'sunucu','araclar'}:return True
        if not isinstance(onay['araclar'],dict):return True
        if not isinstance(sunucu,str) or not sunucu.strip():return True
        for name,digest in onay['araclar'].items():
            if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,63}',name):return True
            if not re.fullmatch('[0-9a-f]{64}',digest):return True
        if not isinstance(arac,dict) or set(arac)!={'name','description','inputSchema','annotations'}:return True
        if not isinstance(arac['description'],str) or not arac['description'].strip():return True
        if not isinstance(arac['inputSchema'],dict) or arac['inputSchema'].get('type')!='object':return True
        if not isinstance(arac['annotations'],dict):return True
        raw=json.dumps(arac,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)
        digest=hashlib.sha256(raw.encode('utf-8')).hexdigest()
        return onay['sunucu']!=sunucu or onay['araclar'].get(arac['name'])!=digest
    except (KeyError,TypeError,ValueError):return True

from pathlib import Path
import json
v=json.loads(Path('veri/rug-pull.json').read_text(encoding='utf-8'))
print('SENTETİK ham veri:',Path('veri/rug-pull.json').read_text(encoding='utf-8'))
import hashlib
pin={'sunucu':v['sunucu'],'araclar':{t['name']:hashlib.sha256(json.dumps(t,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest() for t in v['ilk']}}
print('Yeniden onay?',yeniden_onay(pin,v['sunucu'],v['son'][0]))
```
```hint
Dar sözleşmeyi ve bozuk girdileri birlikte düşün. Ham dosya gizli test değildir.
```
:::
::: gorev 3 · Etki raporu
`ozetle(kayitlar)` üç grubun deneme/hata/ret/etki toplamını döndürür. Tam dört alan kip/ret/etki/hata; kip temiz|korumasiz|korumali, ret/hata gerçek bool, etki negatif olmayan gerçek int. Bozuk veri ValueError. Boş listede her grup sıfır; sıra ve girdi korunur.
```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla('ai-saldiri-47')
```
```starter
def ozetle(kayitlar):
    # KUSURLU BAŞLANGIÇ: bütün grupları güvenli varsayar.
    return {k:{'deneme':len(kayitlar),'hata':0,'ret':0,'etki':0} for k in ('temiz','korumasiz','korumali')}

from pathlib import Path
import json
v=json.loads(Path('veri/rug-pull.json').read_text(encoding='utf-8'))
print('SENTETİK ham veri:',Path('veri/rug-pull.json').read_text(encoding='utf-8'))
print('Ölçüm:',ozetle(v['kayitlar']))
```
```test
import copy,hashlib,json,secrets
def tool(name='lookup_order'):
    return {'name':name,'description':'Read '+secrets.token_hex(6),'inputSchema':{'type':'object','properties':{'id':{'type':'string'}},'required':['id']},'annotations':{'readOnlyHint':True}}
def digest(t):return hashlib.sha256(json.dumps(t,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')).hexdigest()
def raises(fn,*args):
    try:fn(*args);return False
    except ValueError:return True

fn=need('ozetle')
for n in (0,1,3,7):
    rows=[];expected={k:{'deneme':0,'hata':0,'ret':0,'etki':0} for k in ('temiz','korumasiz','korumali')}
    for i in range(n):
        for mode in expected:
            effect=secrets.randbelow(5);ret=i%2==0;error=i%3==0;rows.append({'kip':mode,'ret':ret,'etki':effect,'hata':error});v=expected[mode];v['deneme']+=1;v['hata']+=int(error);v['ret']+=int(ret);v['etki']+=effect
    bak=copy.deepcopy(rows);eq(fn(rows),expected,'ölçülen etkiler ve hatalar ayrı');ok(rows==bak,'girdi değişmedi');eq(fn(list(reversed(rows))),expected,'sıra bağımsız')
base={'kip':'temiz','ret':False,'etki':0,'hata':False}
bads=[None,(),{},[{}],[dict(base,ek=1)],[dict(base,kip='x')],[dict(base,ret=0)],[dict(base,etki=True)],[dict(base,etki=-1)],[dict(base,etki=1.0)],[dict(base,hata=0)]]
ok(all(raises(fn,b) for b in bads),'şema, gerçek bool/int ve negatif etki reddi')

```
```solution
def ozetle(kayitlar):
    if not isinstance(kayitlar,list):raise ValueError('liste')
    out={k:{'deneme':0,'hata':0,'ret':0,'etki':0} for k in ('temiz','korumasiz','korumali')}
    for row in kayitlar:
        if not isinstance(row,dict) or set(row)!={'kip','ret','etki','hata'}:raise ValueError('kayit')
        if row['kip'] not in out or type(row['ret']) is not bool or type(row['etki']) is not int or row['etki']<0 or type(row['hata']) is not bool:raise ValueError('deger')
        v=out[row['kip']];v['deneme']+=1;v['hata']+=int(row['hata']);v['ret']+=int(row['ret']);v['etki']+=row['etki']
    return out

from pathlib import Path
import json
v=json.loads(Path('veri/rug-pull.json').read_text(encoding='utf-8'))
print('SENTETİK ham veri:',Path('veri/rug-pull.json').read_text(encoding='utf-8'))
print('Ölçüm:',ozetle(v['kayitlar']))
```
```hint
Dar sözleşmeyi ve bozuk girdileri birlikte düşün. Ham dosya gizli test değildir.
```
:::
::: gorev Gerçek deney · Onaydan sonra değişen MCP sunucusu
Üç işlevi birlikte kullan. Gerçek stdio mesajlarını, modelin seçtiği çağrıları ve ayrı replay sonuçlarını kanıttan karşılaştır. Modelin saldırıya uyması geçme şartı değildir; meşru kontrol, metadata kapısı ve gerçek dosya etkisi ayrı doğrulanır.
```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```
```starter
import ai_lab
def onay_kaydi(sunucu,araclar):
    # KUSURLU BAŞLANGIÇ: değişen sözleşmeyi tahmin et.
    return {'sunucu':sunucu,'araclar':{t['name']:t['name'] for t in araclar}}
def yeniden_onay(onay,sunucu,arac):
    # KUSURLU BAŞLANGIÇ: isim üzerinden eski güveni sürdürür.
    return arac['name'] not in onay['araclar']
def ozetle(kayitlar):
    # KUSURLU BAŞLANGIÇ: bütün grupları güvenli varsayar.
    return {k:{'deneme':len(kayitlar),'hata':0,'ret':0,'etki':0} for k in ('temiz','korumasiz','korumali')}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_47 as D
    D.goster(onay_kaydi,yeniden_onay,ozetle)
```
```test
import ai_lab,ast
checks=[]
def kontrol(value,message):checks.append(bool(value));ok(value,message)
issues=ai_lab.kod_denetimi(src,('arac_ref','onay_ref','yeniden_ref','ozet_ref','kanit_yaz'),izin=())
for n in ast.walk(ast.parse(src)):
    targets=n.targets if isinstance(n,ast.Assign) else [n.target] if isinstance(n,(ast.AnnAssign,ast.AugAssign)) else []
    if any(isinstance(t,ast.Attribute) for t in targets):issues.append('runtime niteliği yamalama')
kontrol(not issues,'kopya/yama koruması: '+str(issues))
if issues:stop()
_original_ok=ok
def ok(value,message):
    checks.append(bool(value));_original_ok(value,message)
_original_eq=eq
def eq(value,expected,message):
    checks.append(value==expected);_original_eq(value,expected,message)
import copy,hashlib,json,secrets
def tool(name='lookup_order'):
    return {'name':name,'description':'Read '+secrets.token_hex(6),'inputSchema':{'type':'object','properties':{'id':{'type':'string'}},'required':['id']},'annotations':{'readOnlyHint':True}}
def digest(t):return hashlib.sha256(json.dumps(t,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')).hexdigest()
def raises(fn,*args):
    try:fn(*args);return False
    except ValueError:return True

fn=need('onay_kaydi')
t=tool();u=tool('archive_note');original=copy.deepcopy([t,u]);host='server-'+secrets.token_hex(4)
ok(fn(host,[t,u])=={'sunucu':host,'araclar':{t['name']:digest(t),u['name']:digest(u)}} and [t,u]==original,'tüm metadata, iki araç, girdi değişmedi')
reordered=json.loads(json.dumps(t,sort_keys=True))
eq(fn(host,[reordered]),fn(host,[t]),'JSON key sırası onayı değiştirmez')
for field,new in [('description','başka'),('annotations',{'readOnlyHint':False}),('inputSchema',{'type':'object','properties':{}}),('name','renamed')]:
    a=copy.deepcopy(t);a[field]=new;eq(fn(host,[a]),{'sunucu':host,'araclar':{a['name']:digest(a)}},'değişen '+field)
ok(len(fn(host,[tool('t'+str(i)) for i in range(16)])['araclar'])==16,'16 araç sınırı dahil')
bads=[None,[],(t,),[t,t],[tool('t'+str(i)) for i in range(17)],[dict(t,ek=1)],[dict(t,name='')],[dict(t,name='a'*65)],[dict(t,name='x-y')],[dict(t,description=' ')],[dict(t,description=7)],[dict(t,inputSchema={})],[dict(t,inputSchema={'type':'array'})],[dict(t,annotations=[])],[dict(t,annotations={'x':float('nan')})],[dict(t,annotations={'x':{1}})]]
ok(all(raises(fn,host,x) for x in bads),'bozuk/tekrar/üst sınır reddi')
ok(all(raises(fn,x,[t]) for x in (None,'',4,' ')),'sunucu kimliği')
import copy,hashlib,json,secrets
def tool(name='lookup_order'):
    return {'name':name,'description':'Read '+secrets.token_hex(6),'inputSchema':{'type':'object','properties':{'id':{'type':'string'}},'required':['id']},'annotations':{'readOnlyHint':True}}
def digest(t):return hashlib.sha256(json.dumps(t,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')).hexdigest()
def raises(fn,*args):
    try:fn(*args);return False
    except ValueError:return True

fn=need('yeniden_onay');t=tool();host='server-'+secrets.token_hex(4);pin={'sunucu':host,'araclar':{t['name']:digest(t)}};bak=copy.deepcopy((pin,t))
eq(fn(pin,host,t),False,'aynı metadata izinli');ok((pin,t)==bak,'girdiler değişmedi')
for field,new in [('description','yeni talimat'),('annotations',{'readOnlyHint':False}),('inputSchema',{'type':'object','properties':{}}),('name','other')]:
    a=copy.deepcopy(t);a[field]=new;eq(fn(pin,host,a),True,'yeniden onay: '+field)
eq(fn(pin,host+'x',t),True,'başka sunucu');eq(fn(pin,host,json.loads(json.dumps(t,sort_keys=True))),False,'sıra farkı')
for bad in (None,{},dict(t,ek=1),dict(t,description=' '),dict(t,description=2),dict(t,name=''),dict(t,name='x-y'),dict(t,name='a'*65),dict(t,inputSchema=[]),dict(t,inputSchema={'type':'array'}),dict(t,annotations=[]),dict(t,annotations={'x':float('nan')}),dict(t,annotations={'x':{2}})):
    eq(fn(pin,host,bad),True,'bozuk araç fail closed')
for bad in (None,{},dict(pin,araclar={}),dict(pin,araclar=[]),dict(pin,sunucu=''),dict(pin,sunucu=1),dict(pin,ek=1),dict(pin,araclar={'bad-name':digest(t)}),dict(pin,araclar={'other':5}),dict(pin,araclar={'other':'a'*63}),dict(pin,araclar={'other':'a'*65}),dict(pin,araclar={'other':'X'*64})):
    eq(fn(bad,host,t),True,'bozuk onay fail closed')
for server in ('',None,5,' '):eq(fn(pin,server,t),True,'bozuk sunucu')
boundary=tool('a'*64);pb={'sunucu':host,'araclar':{boundary['name']:digest(boundary)}};eq(fn(pb,host,boundary),False,'64 karakter ad dahil')
for bad in (dict(t,ek=1),dict(t,description=' '),dict(t,description=2),dict(t,inputSchema={'type':'array'}),dict(t,annotations=[]),dict(t,name='a'*65)):
    forged={'sunucu':host,'araclar':{bad['name']:digest(bad)}}
    eq(fn(forged,host,bad),True,'hash eşleşse de bozuk sözleşme reddedilir')
for name in ('bad-name','a'*65):
    extra_pin={'sunucu':host,'araclar':dict(pin['araclar'],**{name:'a'*64})}
    eq(fn(extra_pin,host,t),True,'onaydaki ilave bozuk kayıt reddedilir')
for bad_d in ('a'*63,'a'*65,'X'*64,5):
    eq(fn({'sunucu':host,'araclar':dict(pin['araclar'],extra_ok=bad_d)},host,t),True,'onaydaki ilave bozuk digest reddedilir')
tr_tool=dict(t,description='Müşteri siparişi oku '+secrets.token_hex(4))
eq(fn({'sunucu':host,'araclar':{tr_tool['name']:digest(tr_tool)}},host,tr_tool),False,'UTF-8 ensure_ascii=False özeti korunur')
for h in ('',' '):
    forged={'sunucu':h,'araclar':pin['araclar']}
    eq(fn(forged,h,t),True,'iki taraf boşken izin çıkmaz')

import copy,hashlib,json,secrets
def tool(name='lookup_order'):
    return {'name':name,'description':'Read '+secrets.token_hex(6),'inputSchema':{'type':'object','properties':{'id':{'type':'string'}},'required':['id']},'annotations':{'readOnlyHint':True}}
def digest(t):return hashlib.sha256(json.dumps(t,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')).hexdigest()
def raises(fn,*args):
    try:fn(*args);return False
    except ValueError:return True

fn=need('ozetle')
for n in (0,1,3,7):
    rows=[];expected={k:{'deneme':0,'hata':0,'ret':0,'etki':0} for k in ('temiz','korumasiz','korumali')}
    for i in range(n):
        for mode in expected:
            effect=secrets.randbelow(5);ret=i%2==0;error=i%3==0;rows.append({'kip':mode,'ret':ret,'etki':effect,'hata':error});v=expected[mode];v['deneme']+=1;v['hata']+=int(error);v['ret']+=int(ret);v['etki']+=effect
    bak=copy.deepcopy(rows);eq(fn(rows),expected,'ölçülen etkiler ve hatalar ayrı');ok(rows==bak,'girdi değişmedi');eq(fn(list(reversed(rows))),expected,'sıra bağımsız')
base={'kip':'temiz','ret':False,'etki':0,'hata':False}
bads=[None,(),{},[{}],[dict(base,ek=1)],[dict(base,kip='x')],[dict(base,ret=0)],[dict(base,etki=True)],[dict(base,etki=-1)],[dict(base,etki=1.0)],[dict(base,hata=0)]]
ok(all(raises(fn,b) for b in bads),'şema, gerçek bool/int ve negatif etki reddi')

from sandbox import ai_gercek_ai_saldiri_47 as D
if any(not c for c in checks):stop()
try:r=D.deney(need('onay_kaydi'),need('yeniden_onay'),need('ozetle'))
except ai_lab.GercekLabYok as e:
    kontrol(False,'GERÇEK DENEY YAPILMADI: '+str(e));stop()
kontrol(all(r['kontroller']),'gerçek meşru akış, kapı, disk etkisi ve rapor')
kontrol(len(r['cagrilar'])==6 and all(x['surec_kapandi'] for x in r['cagrilar']),'altı gerçek stdio sunucusu yalnız kendi PID ile kapandı')
kontrol(not any(x['hata'] for x in r['kayitlar']),'transport/model hatası yok')
ai_lab.kanit_yaz('saldiri47-kabul',dict(r,kabul=all(checks)))

```
```solution
import ai_lab
import hashlib,json,re
def onay_kaydi(sunucu,araclar):
    if not isinstance(sunucu,str) or not sunucu.strip():raise ValueError('sunucu')
    if not isinstance(araclar,list) or not araclar or len(araclar)>16:raise ValueError('araclar')
    pins={}
    for t in araclar:
        if not isinstance(t,dict) or set(t)!={'name','description','inputSchema','annotations'}:raise ValueError('alanlar')
        if not isinstance(t['name'],str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,63}',t['name']):raise ValueError('ad')
        if not isinstance(t['description'],str) or not t['description'].strip():raise ValueError('description')
        if not isinstance(t['inputSchema'],dict) or t['inputSchema'].get('type')!='object':raise ValueError('schema')
        if not isinstance(t['annotations'],dict):raise ValueError('annotations')
        try:raw=json.dumps(t,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)
        except (TypeError,ValueError):raise ValueError('JSON')
        if t['name'] in pins:raise ValueError('yinelenen')
        pins[t['name']]=hashlib.sha256(raw.encode('utf-8')).hexdigest()
    return {'sunucu':sunucu,'araclar':pins}

import hashlib,json,re
def yeniden_onay(onay,sunucu,arac):
    try:
        if not isinstance(onay,dict) or set(onay)!={'sunucu','araclar'}:return True
        if not isinstance(onay['araclar'],dict):return True
        if not isinstance(sunucu,str) or not sunucu.strip():return True
        for name,digest in onay['araclar'].items():
            if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,63}',name):return True
            if not re.fullmatch('[0-9a-f]{64}',digest):return True
        if not isinstance(arac,dict) or set(arac)!={'name','description','inputSchema','annotations'}:return True
        if not isinstance(arac['description'],str) or not arac['description'].strip():return True
        if not isinstance(arac['inputSchema'],dict) or arac['inputSchema'].get('type')!='object':return True
        if not isinstance(arac['annotations'],dict):return True
        raw=json.dumps(arac,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)
        digest=hashlib.sha256(raw.encode('utf-8')).hexdigest()
        return onay['sunucu']!=sunucu or onay['araclar'].get(arac['name'])!=digest
    except (KeyError,TypeError,ValueError):return True

def ozetle(kayitlar):
    if not isinstance(kayitlar,list):raise ValueError('liste')
    out={k:{'deneme':0,'hata':0,'ret':0,'etki':0} for k in ('temiz','korumasiz','korumali')}
    for row in kayitlar:
        if not isinstance(row,dict) or set(row)!={'kip','ret','etki','hata'}:raise ValueError('kayit')
        if row['kip'] not in out or type(row['ret']) is not bool or type(row['etki']) is not int or row['etki']<0 or type(row['hata']) is not bool:raise ValueError('deger')
        v=out[row['kip']];v['deneme']+=1;v['hata']+=int(row['hata']);v['ret']+=int(row['ret']);v['etki']+=row['etki']
    return out

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_47 as D
    D.goster(onay_kaydi,yeniden_onay,ozetle)
```
:::
::: anlat Hata vitrini · aynı isim, başka sözleşme
İlk tahmin kodu araç adı eşitliğine True, bütün sözleşme eşitliğine False yazar. Bu hesaplama sentetik örnektir; model sonucu değildir. Birinci starter hash yerine yalnız adı tuttuğu için bu değişimi temsil edemez. İkinci starter aynı adı görünce eski onayı sürdürür. Üçüncü starter ise hata ve disk etkisini sıfıra zorlar. Kendi Run çıktını bu üç hatayla karşılaştır. Gerçek kanıtta model çağırmadığı hâlde replay outbox yazmışsa "model enjekte oldu" demek yanlış olur; model_sonrasi ve son_etki alanları bunun için ayrıdır.
:::
::: anlat Sınır
Bu ders görünür metadata değişiminde eski onayın geçersizliğini ve kendi yerel test sunucusundaki dosya etkisini ölçer; sabit metadata arkasındaki bütün kötü backend davranışlarını, tam MCP uyumluluğunu veya uzaktaki servislerin güvenliğini kanıtlayamaz.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
### İsim değil, onaylanan sözleşme

İlk listeyi t0 anında onayladığını, açıklamanın t1 anında değiştiğini düşün. Araç adı eşitliği yalnız kimlik etiketini karşılaştırır; onaylanan davranış varsayımının korunmasını göstermez. Kararlı JSON hash karşılaştırması değişikliği görünür kılar ve yeniden onay kapısına gider. Bunun da sınırı vardır: metadata değişmeden backend kötüleşebilir. Gerçek kanıtta modelin yaptığı çağrı ile deterministik replay farklı kolonlardır; replay etkisini modelin saldırı başarısı diye anlatma.

| Yaygın yanlış | Mekanizmanın söylediği |
|---|---|
| Hash imzadır | Hash değişikliği saptar; sunucuyu doğrulayan bir kimlik imzası değildir. |

Sonraki bağlantı: ai-savunma-20 ile tedarik zinciri ve sürüm sabitleme.
:::
