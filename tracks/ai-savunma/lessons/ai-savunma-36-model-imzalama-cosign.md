---
id: ai-savunma-36
title: Model İmzalama · Gerçek Cosign ve Yerel Keyless Kimlik
summary: Manifest bütünlüğünü ve signer/issuer politikasını ayır, gerçek model dosyasında imza ve tahrifat kontrollerini çalıştır.
esleme: ai-saldiri-47, ai-saldiri-51
timeout: 60
---
::: anlat Hash, imza ve kimlik farklı sorulardır
| Gerçek araç ne gösterir | Bu derste ne yapılır | Ne söylenemez? |
|---|---|---|
| SHA256 aynı dosyayı görüp görmediğini gösterir | İlk görev açılabilir dosyayı akışla hash eder | Hash tek başına yazarı doğrulamaz |
| Cosign bir imzayı public key ya da sertifika ile doğrular | Final gerçek küçük model ağırlığında key-pair ve yerel keyless karşılaştırır | Sentetik verify.json gerçek CLI kaydı değildir |
| Yerel Fulcio test issuer'ına bağlı sertifika üretebilir | Ayrı onaylanan resmi Fulcio, geçici test OIDC ve pinlenmiş root | Test kimliği gerçek kişinin kimliği değildir; public Sigstore şeffaflık güvencesi yoktur |

> [!NOT]
> İlk üç görevde `veri/model.safetensors` yerelde elle hazırlanmış, geçerli safetensors biçimindeki küçük sentetik weight/bias tensörleridir; eğitim sonucu değildir. `manifest.json`, `policy.json`, `verify.json` da sentetiktir. Setup her Run/Check için yeni geçici çalışma kopyası kurar; düzenleme sonraki çalıştırmaya kalmaz. Ham veriyi Path ile açıp yazdırabilir ve sözlük üzerinde deneyebilirsin. Final ise torch ile gerçekten eğitilen Linear modelin safetensors ağırlığını imzalar. Eksik Cosign/Fulcio/servis gerçek kabul vermez; düğme kurulum yapmaz.

Modeli indirdikten sonra bir SHA256 özeti görmek rahatlatıcıdır ama iki ayrı soru vardır. Dosya beklenen baytlarla aynı mı? Beklenen özeti ve dosyayı kim yayımladı? Saldırgan ikisini birlikte değiştirebiliyorsa hash kontrolü geçer. Bu yüzden birinci görev bütünlük kontrolüdür; kimlik kanıtı veya üretici güvenilirliği değildir. İkinci ve son görevler imzayı, güvenilen anahtarı ve kimlik politikasını ayrıca ele alır. Bir imzanın matematiksel olarak doğru olması, o anahtarın doğru kişiye ait olduğuna tek başına karar vermez.

Görünür örnek weight=[2,4] ve bias=[2] biçiminde geçerli safetensors tensörleridir. Bunlar bir eğitim koşusunun çıktısı değildir; yalnız dosya biçimini ve bütünlük kontrolünü kurcalamak için elle hazırlanmıştır. Finalde kullanılan dosya ise gerçekten eğitilir.

İlk görev tek dosyalı dar bir manifest sözleşmesi uygular. Dosya adı 1–80 ASCII harf/rakam/alt çizgi/tire/nokta karakterli bir gövde ve tam küçük harf .safetensors uzantısıdır; ilk karakter nokta olamaz. Alt dizin, mutlak yol, sürücü yolu ve symlink kabul edilmez. SHA256 64 küçük hexadecimal karakter olmalıdır. Dosyanın gerçekten var olması, regular file olması ve hash'in uyuşması gerekir. Bu kurallar bütün paket yöneticilerine ait evrensel bir manifest standardı değildir; görevin sınırlı çalışma alanını açık tutar. Safetensors uzantısı da içeriğin yüklenebilir ya da güvenilir olduğunu garanti etmez.

Dosya kontrolü ile dosya kullanımı arasına başka bir yazar girerse TOCTOU riski vardır. Bu ders tek süreçli izole lab içinde çalışır; sistem çapında yarışları veya model yükleyicisindeki bütün açıkları çözdüğünü iddia etmez. Gerçek deneyde ağırlık dosyası oluşturulduktan sonra safetensors ile tekrar yüklenir ve parametreler karşılaştırılır. Böylece yalnız rastgele bir metin dosyasını model diye imzalamış olmayız. Küçük modelin görevi iki sınıflı sentetik veriyi ayırmaktır; model kalitesi burada bir siber güvenlik sertifikası değildir.

Key-pair akışında cosign kalıcı bir private/public anahtar çifti üretir. Model dosyası private key ile imzalanır; beklenen public key ile doğrulanır. Başka bir anahtarın aynı dosyada geçerli imzası olması, ilk üreticinin imzası olarak kabul edilmez. Private key ve parolayı kanıt dosyasına koymak gerekmez; yalnız public key ve artifact/imza özetleri, komut sürümü ve sonuçları saklanır. Lab anahtarları gerçek hesabın anahtarları değildir ve öğrenciye işletim sistemi kimliği kazandırmaz.

Keyless akışta istemcinin uzun ömürlü imza private key'ini önceden saklaması gerekmez. Cosign geçici anahtar üretir; issuer tarafından imzalanmış kısa ömürlü OIDC tokenı gerçek Fulcio'ya gider. Yerel test issuer'ı discovery ve JWKS uçlarını container loopback'inde sunar. Fulcio token imzası, audience, süre ve email_verified alanlarını kontrol edip test email kimliğine bağlı sertifika verir. Bu küçük issuer öğrenciye gerçek bir kişinin kimliğini kanıtlamaz. Dış Google/GitHub/Microsoft oturumu açılmaz; gerçek kullanıcı tokenı veya kişisel veri gönderilmez.

İkinci görev, sertifikadan elde edilen kimlik ve issuer'ı izin politikasına tam eşleştirir. Birinin doğru olması yeterli değildir. Email'in başına boşluk eklemek, issuer'ın sonuna slash koymak veya büyük/küçük harfi değiştirmek bu labda aynı değer sayılmaz. Normalize edip başka bir kimliği yanlışlıkla kabul etmek yerine açık politika kullanılır. Bu işlev bir JWT doğrulayıcısı veya sertifika zinciri doğrulayıcısı değildir; finalde kriptografik doğrulamayı gerçek cosign yapar. Öğrenci bu ayrımı gözlem kaydında da görmelidir.

Yerel keyless labda sertifika kökü deney dosyasından pinlenir; Windows güven deposuna CA eklenmez. Aynı artifact bir bayt değiştirilince, beklenen email veya issuer değiştirilince, başka root kullanıldığında imza reddedilmelidir. Doğru artifact ve doğru politika ise geçmeye devam etmelidir. Sunucu kapanıp bütün doğrulamaların hata vermesi başarılı savunma değildir. Üçüncü görev bu nedenle calisti ve dogrulandi alanlarını ayırır. Sekiz benzersiz vakanın tümü bulunmadan tam rapor verilemez; hata, beklenmeyen karar ve gerçekten doğrulanan vakalar ayrı listelenir.

Bu özel kurulum public Rekor ya da CT logu kurmaz. Yerel private-lab doğrulama seçenekleri ve atlanan transparency/SCT adımları kanıtta açıkça yazılır. Bunları gizleyip public Sigstore şeffaflığı veya geçmişe dönük zaman damgası kanıtı var demek yanlıştır. Bu dersin gerçek hedefi model artifact bütünlüğü, imza ve yerel issuer/root/subject bağını birlikte ölçmektir. Bir kuruluşun production dağıtım politikası ek transparency, timestamp ve tedarik zinciri kontrolleri isteyebilir.

Ham verify.json dosyasındaki örnekte komut çalışmamışken dogrulandi=False görülür. Tahminini yaz: bu güvenli ret midir, deney hatası mıdır? Kusurlu starterı Çalıştır düğmesiyle incele; kendi cümlenle farkı açıkla. Final kanıtında sadece kabul alanına bakma. Orijinal ve tahrif edilmiş dosyanın hash'leri, cosign binary hash'i, root ve imza dosyası hash'i, sabit model seed'i, gerçek stdout/stderr/exit code ve ikinci koşuda kararların tutarlılığı birlikte incelenir. Token ve private key kanıtta yer almaz.

Saldırı–savunma köprüsü ai-saldiri-47 rug pull ve ai-saldiri-51 altyapı güven sınırıdır. İmza doğrulanan bir modelin çevresindeki servis yine kötü davranabilir. Üreticinin kimliği kadar hangi artifact ve hangi sürümün onaylandığı da önemlidir. Öğrenci burada başarıyı bir sözlüğe imzali=True yazmakla değil, gerçekten değiştirilmiş dosyanın CLI tarafından reddedilmesiyle gösterecek.

Kaynaklar: [Cosign v3.1.4 sign-blob](https://github.com/sigstore/cosign/blob/v3.1.4/doc/cosign_sign-blob.md), [verify-blob](https://github.com/sigstore/cosign/blob/v3.1.4/doc/cosign_verify-blob.md), [Fulcio v1.9.1](https://github.com/sigstore/fulcio/tree/v1.9.1). Ders bu sürümlerdeki private test akışını hedefler; bütün gelecekteki sürümlerin aynı bayrakları koruduğunu varsaymaz.
:::
::: tahmin Komut hiç çalışmadıysa ret sayılır mı?
Tahminini yaz, çalıştır ve farkı yorumla.
```python
calisti=False
dogrulandi=False
print(not dogrulandi)
print(calisti and not dogrulandi)
```
???
```cikti
True
False
```
:::
::: gorev 1 · Manifest bütünlüğü
`manifest_dogrula(klasor,manifest)` bool döndürür. Tam dosya/sha256 alanları, yukarıdaki ad/hash sözleşmesi, gerçek dosya okuma ve symlink reddi gerekir. Girdi değişmez; bozuk/eksik dosya veya manifest False.
```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules['__main__'].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla('ai-savunma-36')
```
```starter
def manifest_dogrula(klasor,manifest):
    # KUSURLU BAŞLANGIÇ: verilen hash'in varlığı yeterli mi?
    return len(manifest['sha256'])==64

import json
from pathlib import Path
print('SENTETİK HAM VERİ:',Path('veri/verify.json').read_text(encoding='utf-8'))
m=json.loads(Path('veri/manifest.json').read_text(encoding='utf-8'));print('Manifest:',m);print('Bütünlük:',manifest_dogrula('veri',m))
```
```test
from pathlib import Path
import hashlib,tempfile,secrets,copy
raw_fn=need('manifest_dogrula')
def fn(*args):
    value=raw_fn(*args)
    if type(value) is not bool:raise TypeError('bool sonuç gerekli')
    return value
base=Path(tempfile.mkdtemp(prefix='s36-contract-'));payload=secrets.token_bytes(180);p=base/'model.safetensors';p.write_bytes(payload);digest=hashlib.sha256(payload).hexdigest();m={'dosya':p.name,'sha256':digest};bak=copy.deepcopy(m)
eq(fn(base,m),True,'gerçek çalışma dosyasının SHA256 özeti');eq(m,bak,'manifest değişmedi')
eq(fn(str(base),m),True,'str klasör de kabul edilir')
eq(fn(base,dict(m,sha256='0'*64)),False,'yanlış hash')
p.write_bytes(payload+b'!');eq(fn(base,m),False,'dosya değiştiyse eski manifest yetmez');p.write_bytes(payload)
for bad in (None,{},dict(m,ek=1),dict(m,dosya='../model.safetensors'),dict(m,dosya='/model.safetensors'),dict(m,dosya='C:\\x.safetensors'),dict(m,dosya='a/b.safetensors'),dict(m,dosya='a\\b.safetensors'),dict(m,dosya=''),dict(m,dosya=7),dict(m,dosya='model.SAFETENSORS'),dict(m,sha256=None),dict(m,sha256='g'*64),dict(m,sha256='a'*63),dict(m,sha256='a'*65),dict(m,sha256=digest.upper())):
    eq(fn(base,bad),False,'bozuk manifest fail closed')
for n,allowed in ((80,True),(81,False)):
    name='a'*n+'.safetensors';(base/name).write_bytes(payload);eq(fn(base,{'dosya':name,'sha256':digest}),allowed,'dosya adının sınır uzunluğu')
(base/'directory.safetensors').mkdir();eq(fn(base,dict(m,dosya='directory.safetensors')),False,'dizin ağırlık dosyası değildir')
eq(fn(base/'yok',m),False,'eksik çalışma dizini');eq(fn(None,m),False,'bozuk çalışma dizini')
link=base/'linked.safetensors'
try:link.symlink_to(p)
except OSError:pass
else:eq(fn(base,dict(m,dosya=link.name)),False,'symlink kabul edilmez')
# --- carbon-c8-ek-bas ---
import types as _ty36, unittest.mock as _mk36
eq(fn(base, _ty36.MappingProxyType(m)), False, "manifest gerçek dict olmalı")
eq(fn(123, m), False, "klasör str/Path olmalı")
with _mk36.patch.object(Path, "is_symlink", return_value=True):
    eq(fn(base, m), False, "sembolik bağ reddedilmeli")
# --- carbon-c8-ek-son ---
```
```solution
from pathlib import Path
import hashlib,re
def manifest_dogrula(klasor,manifest):
    try:
        if not isinstance(manifest,dict) or set(manifest)!={'dosya','sha256'}:return False
        name=manifest['dosya'];wanted=manifest['sha256']
        if not re.fullmatch(r'[A-Za-z0-9_-][A-Za-z0-9_.-]{0,79}\.safetensors',name):return False
        if not isinstance(wanted,str):return False
        root=Path(klasor).resolve(strict=True);path=root/name
        if path.is_symlink():return False
        with path.open('rb') as f:got=hashlib.file_digest(f,'sha256').hexdigest()
        return got==wanted
    except (OSError,TypeError,ValueError):return False

import json
from pathlib import Path
print('SENTETİK HAM VERİ:',Path('veri/verify.json').read_text(encoding='utf-8'))
m=json.loads(Path('veri/manifest.json').read_text(encoding='utf-8'));print('Manifest:',m);print('Bütünlük:',manifest_dogrula('veri',m))
```
```hint
Negatif kontrolün çalışmış olması gerekir; eksik deney doğru karar değildir.
```
:::
::: gorev 2 · Kimlik ve issuer
`kimlik_uygun(kimlik,issuer,politika)` bool döndürür. Politika yalnız kimlik/issuer alanları taşır; dört değer de boş olmayan str olur. İkisi de birebir eşleşmeli; bozuk politika False. Bu kriptografik sertifika doğrulaması değildir.
```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules['__main__'].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla('ai-savunma-36')
```
```starter
def kimlik_uygun(kimlik,issuer,politika):
    # KUSURLU BAŞLANGIÇ: tek eşleşmeyle izin çıkarır.
    return kimlik==politika['kimlik'] or issuer==politika['issuer']

import json
from pathlib import Path
print('SENTETİK HAM VERİ:',Path('veri/verify.json').read_text(encoding='utf-8'))
p=json.loads(Path('veri/policy.json').read_text(encoding='utf-8'));print('Politika:',p);print('Başka kimlik:',kimlik_uygun('other@pafta.invalid',p['issuer'],p))
```
```test
import secrets,copy
raw_fn=need('kimlik_uygun')
def fn(*args):
    value=raw_fn(*args)
    if type(value) is not bool:raise TypeError('bool sonuç gerekli')
    return value
identity='s-'+secrets.token_hex(6)+'@pafta.invalid';issuer='http://127.0.0.1:5556';policy={'kimlik':identity,'issuer':issuer};bak=copy.deepcopy(policy)
eq(fn(identity,issuer,policy),True,'iki sabit de tam eşleşti');eq(policy,bak,'politika değişmedi')
for who,iss in ((identity+'x',issuer),(identity,issuer+'/'),(identity.upper(),issuer),(identity,issuer.upper()),(' '+identity,issuer),(identity,' '+issuer),(identity+'x',issuer+'x')):
    eq(fn(who,iss,policy),False,'kimlik VE issuer birebir olmalı')
for value in (None,'',' ',7,True,[],{}):
    eq(fn(value,issuer,policy),False,'bozuk kimlik');eq(fn(identity,value,policy),False,'bozuk issuer')
for bad in (None,{},dict(policy,ek=1),dict(policy,kimlik=''),dict(policy,kimlik=' '),dict(policy,kimlik=1),dict(policy,issuer=''),dict(policy,issuer=None)):
    eq(fn(identity,issuer,bad),False,'bozuk politika')
for value in ('',' '):eq(fn(value,value,{'kimlik':value,'issuer':value}),False,'iki taraf boşsa onay yok')
```
```solution
def kimlik_uygun(kimlik,issuer,politika):
    if not isinstance(politika,dict) or set(politika)!={'kimlik','issuer'}:return False
    for value in (kimlik,issuer,politika['kimlik'],politika['issuer']):
        if not isinstance(value,str) or not value.strip():return False
    return kimlik==politika['kimlik'] and issuer==politika['issuer']

import json
from pathlib import Path
print('SENTETİK HAM VERİ:',Path('veri/verify.json').read_text(encoding='utf-8'))
p=json.loads(Path('veri/policy.json').read_text(encoding='utf-8'));print('Politika:',p);print('Başka kimlik:',kimlik_uygun('other@pafta.invalid',p['issuer'],p))
```
```hint
Negatif kontrolün çalışmış olması gerekir; eksik deney doğru karar değildir.
```
:::
::: gorev 3 · Gerçek verify sonuç raporu
`sonuc_raporu(kayitlar)` tam sekiz benzersiz vaka ister: keypair-normal/tahrifat/baska-anahtar ve keyless-normal/tahrifat/baska-kimlik/baska-issuer/baska-root. Her kayıt tam vaka/calisti/dogrulandi alanları; iki durum gerçek bool. İki normal True, altı negatif False beklenir. Hata ile beklenmeyen karar ayrılır. `{kabul,hatalar,beklenmeyen,dogrulanan}` döndür; listeler sıralı. Bozuk girdi ValueError; girdi/sıra sonucu değiştirmez.
```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules['__main__'].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla('ai-savunma-36')
```
```starter
def sonuc_raporu(kayitlar):
    # KUSURLU BAŞLANGIÇ: çalışmayan komutu güvenli sayar.
    return {'kabul':all(not x['dogrulandi'] for x in kayitlar),'hatalar':[],'beklenmeyen':[],'dogrulanan':[]}

import json
from pathlib import Path
print('SENTETİK HAM VERİ:',Path('veri/verify.json').read_text(encoding='utf-8'))
v=json.loads(Path('veri/verify.json').read_text(encoding='utf-8'));print('Rapor:',sonuc_raporu(v))
```
```test
import itertools,copy
fn=need('sonuc_raporu');names=('keypair-normal','keypair-tahrifat','keypair-baska-anahtar','keyless-normal','keyless-tahrifat','keyless-baska-kimlik','keyless-baska-issuer','keyless-baska-root');positive={'keypair-normal','keyless-normal'}
value_checks=[];unchanged_checks=[];order_checks=[]
for values in itertools.product((False,True),repeat=8):
    rows=[{'vaka':n,'calisti':True,'dogrulandi':v} for n,v in zip(names,values)];bak=copy.deepcopy(rows);bad=sorted(n for n,v in zip(names,values) if v!=(n in positive));expect={'kabul':not bad,'hatalar':[],'beklenmeyen':bad,'dogrulanan':sorted(n for n,v in zip(names,values) if v)}
    value_checks.append(fn(rows)==expect);unchanged_checks.append(rows==bak);order_checks.append(fn(list(reversed(rows)))==expect)
ok(len(value_checks)==256 and all(value_checks),'sekiz vakanın 256 sonuç kombinasyonu')
ok(all(unchanged_checks),'256 girdinin hepsi korunur')
ok(all(order_checks),'256 sonuçta sıra bağımsızlığı')
normal=[{'vaka':n,'calisti':True,'dogrulandi':n in positive} for n in names]
for i,n in enumerate(names):
    rows=copy.deepcopy(normal);rows[i]['calisti']=False
    eq(fn(rows),{'kabul':False,'hatalar':[n],'beklenmeyen':[],'dogrulanan':sorted(positive-{n})},'komut hatası güvenli ret değildir')
def reject(v):
    try:fn(v);return False
    except ValueError:return True
bad=[None,(),normal[:7],normal+[normal[0]],[normal[0]]*8,[{},*normal[1:]],[dict(normal[0],vaka='x'),*normal[1:]],[dict(normal[0],calisti=1),*normal[1:]],[dict(normal[0],dogrulandi=1),*normal[1:]],[dict(normal[0],ek=1),*normal[1:]]]
ok(all(reject(x) for x in bad),'şema, sekiz benzersiz vaka ve bool türü')
# --- carbon-c8-ek-bas ---
import types as _ty36c
raises(ValueError, sonuc_raporu, [_ty36c.MappingProxyType(normal[0]), *normal[1:]], msg="kayıt gerçek dict olmalı")
raises(ValueError, sonuc_raporu, [dict(normal[0], vaka=123), *normal[1:]], msg="vaka str olmalı")
# --- carbon-c8-ek-son ---
```
```solution
def sonuc_raporu(kayitlar):
    expected={'keypair-normal':True,'keypair-tahrifat':False,'keypair-baska-anahtar':False,'keyless-normal':True,'keyless-tahrifat':False,'keyless-baska-kimlik':False,'keyless-baska-issuer':False,'keyless-baska-root':False}
    if not isinstance(kayitlar,list) or len(kayitlar)!=8:raise ValueError('sekiz kayıt')
    seen=set();errors=[];wrong=[];verified=[]
    for row in kayitlar:
        if not isinstance(row,dict) or set(row)!={'vaka','calisti','dogrulandi'}:raise ValueError('şema')
        name=row['vaka']
        if name not in expected or name in seen or type(row['calisti']) is not bool or type(row['dogrulandi']) is not bool:raise ValueError('değer')
        seen.add(name)
        if not row['calisti']:errors.append(name)
        else:
            if row['dogrulandi']!=expected[name]:wrong.append(name)
            if row['dogrulandi']:verified.append(name)
    return {'kabul':not errors and not wrong,'hatalar':sorted(errors),'beklenmeyen':sorted(wrong),'dogrulanan':sorted(verified)}

import json
from pathlib import Path
print('SENTETİK HAM VERİ:',Path('veri/verify.json').read_text(encoding='utf-8'))
v=json.loads(Path('veri/verify.json').read_text(encoding='utf-8'));print('Rapor:',sonuc_raporu(v))
```
```hint
Negatif kontrolün çalışmış olması gerekir; eksik deney doğru karar değildir.
```
:::
::: gorev Gerçek deney · Model artifact, imza ve yerel keyless
Üç işlevi birlikte kullan. Cosign kurulu olmalı; Fulcio için ayrı onaylı kurulum gerekir. Gerçek modelin doğru imzası geçerken tahrifat, başka key/subject/issuer/root reddedilir. Komut hatası güvenli ret değildir. Keyless deneyi yapılmadan kabul yoktur.
```meta
motor: ai-gercek
gereksinim: torch
timeout: 300
```
```starter
import ai_lab
def manifest_dogrula(klasor,manifest):
    # KUSURLU BAŞLANGIÇ: verilen hash'in varlığı yeterli mi?
    return len(manifest['sha256'])==64
def kimlik_uygun(kimlik,issuer,politika):
    # KUSURLU BAŞLANGIÇ: tek eşleşmeyle izin çıkarır.
    return kimlik==politika['kimlik'] or issuer==politika['issuer']
def sonuc_raporu(kayitlar):
    # KUSURLU BAŞLANGIÇ: çalışmayan komutu güvenli sayar.
    return {'kabul':all(not x['dogrulandi'] for x in kayitlar),'hatalar':[],'beklenmeyen':[],'dogrulanan':[]}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_36 as D
    D.goster(manifest_dogrula,kimlik_uygun,sonuc_raporu)
```
```test
import ast,ai_lab
checks=[]
base_ok=ok;base_eq=eq
def ok(x,msg):checks.append(bool(x));base_ok(x,msg)
def eq(x,y,msg):checks.append(x==y);base_eq(x,y,msg)
issues=ai_lab.kod_denetimi(src,('manifest_ref','kimlik_ref','rapor_ref','kanit_yaz'),izin=())
for node in ast.walk(ast.parse(src)):
    targets=node.targets if isinstance(node,ast.Assign) else [node.target] if isinstance(node,(ast.AnnAssign,ast.AugAssign)) else []
    if any(isinstance(t,ast.Attribute) for t in targets):issues.append('runtime niteliği yamalama')
ok(not issues,'kopya/yama koruması: '+str(issues))
if issues:stop()
from pathlib import Path
import hashlib,tempfile,secrets,copy
raw_fn=need('manifest_dogrula')
def fn(*args):
    value=raw_fn(*args)
    if type(value) is not bool:raise TypeError('bool sonuç gerekli')
    return value
base=Path(tempfile.mkdtemp(prefix='s36-contract-'));payload=secrets.token_bytes(180);p=base/'model.safetensors';p.write_bytes(payload);digest=hashlib.sha256(payload).hexdigest();m={'dosya':p.name,'sha256':digest};bak=copy.deepcopy(m)
eq(fn(base,m),True,'gerçek çalışma dosyasının SHA256 özeti');eq(m,bak,'manifest değişmedi')
eq(fn(str(base),m),True,'str klasör de kabul edilir')
eq(fn(base,dict(m,sha256='0'*64)),False,'yanlış hash')
p.write_bytes(payload+b'!');eq(fn(base,m),False,'dosya değiştiyse eski manifest yetmez');p.write_bytes(payload)
for bad in (None,{},dict(m,ek=1),dict(m,dosya='../model.safetensors'),dict(m,dosya='/model.safetensors'),dict(m,dosya='C:\\x.safetensors'),dict(m,dosya='a/b.safetensors'),dict(m,dosya='a\\b.safetensors'),dict(m,dosya=''),dict(m,dosya=7),dict(m,dosya='model.SAFETENSORS'),dict(m,sha256=None),dict(m,sha256='g'*64),dict(m,sha256='a'*63),dict(m,sha256='a'*65),dict(m,sha256=digest.upper())):
    eq(fn(base,bad),False,'bozuk manifest fail closed')
for n,allowed in ((80,True),(81,False)):
    name='a'*n+'.safetensors';(base/name).write_bytes(payload);eq(fn(base,{'dosya':name,'sha256':digest}),allowed,'dosya adının sınır uzunluğu')
(base/'directory.safetensors').mkdir();eq(fn(base,dict(m,dosya='directory.safetensors')),False,'dizin ağırlık dosyası değildir')
eq(fn(base/'yok',m),False,'eksik çalışma dizini');eq(fn(None,m),False,'bozuk çalışma dizini')
link=base/'linked.safetensors'
try:link.symlink_to(p)
except OSError:pass
else:eq(fn(base,dict(m,dosya=link.name)),False,'symlink kabul edilmez')
import secrets,copy
raw_fn=need('kimlik_uygun')
def fn(*args):
    value=raw_fn(*args)
    if type(value) is not bool:raise TypeError('bool sonuç gerekli')
    return value
identity='s-'+secrets.token_hex(6)+'@pafta.invalid';issuer='http://127.0.0.1:5556';policy={'kimlik':identity,'issuer':issuer};bak=copy.deepcopy(policy)
eq(fn(identity,issuer,policy),True,'iki sabit de tam eşleşti');eq(policy,bak,'politika değişmedi')
for who,iss in ((identity+'x',issuer),(identity,issuer+'/'),(identity.upper(),issuer),(identity,issuer.upper()),(' '+identity,issuer),(identity,' '+issuer),(identity+'x',issuer+'x')):
    eq(fn(who,iss,policy),False,'kimlik VE issuer birebir olmalı')
for value in (None,'',' ',7,True,[],{}):
    eq(fn(value,issuer,policy),False,'bozuk kimlik');eq(fn(identity,value,policy),False,'bozuk issuer')
for bad in (None,{},dict(policy,ek=1),dict(policy,kimlik=''),dict(policy,kimlik=' '),dict(policy,kimlik=1),dict(policy,issuer=''),dict(policy,issuer=None)):
    eq(fn(identity,issuer,bad),False,'bozuk politika')
for value in ('',' '):eq(fn(value,value,{'kimlik':value,'issuer':value}),False,'iki taraf boşsa onay yok')
import itertools,copy
fn=need('sonuc_raporu');names=('keypair-normal','keypair-tahrifat','keypair-baska-anahtar','keyless-normal','keyless-tahrifat','keyless-baska-kimlik','keyless-baska-issuer','keyless-baska-root');positive={'keypair-normal','keyless-normal'}
value_checks=[];unchanged_checks=[];order_checks=[]
for values in itertools.product((False,True),repeat=8):
    rows=[{'vaka':n,'calisti':True,'dogrulandi':v} for n,v in zip(names,values)];bak=copy.deepcopy(rows);bad=sorted(n for n,v in zip(names,values) if v!=(n in positive));expect={'kabul':not bad,'hatalar':[],'beklenmeyen':bad,'dogrulanan':sorted(n for n,v in zip(names,values) if v)}
    value_checks.append(fn(rows)==expect);unchanged_checks.append(rows==bak);order_checks.append(fn(list(reversed(rows)))==expect)
ok(len(value_checks)==256 and all(value_checks),'sekiz vakanın 256 sonuç kombinasyonu')
ok(all(unchanged_checks),'256 girdinin hepsi korunur')
ok(all(order_checks),'256 sonuçta sıra bağımsızlığı')
normal=[{'vaka':n,'calisti':True,'dogrulandi':n in positive} for n in names]
for i,n in enumerate(names):
    rows=copy.deepcopy(normal);rows[i]['calisti']=False
    eq(fn(rows),{'kabul':False,'hatalar':[n],'beklenmeyen':[],'dogrulanan':sorted(positive-{n})},'komut hatası güvenli ret değildir')
def reject(v):
    try:fn(v);return False
    except ValueError:return True
bad=[None,(),normal[:7],normal+[normal[0]],[normal[0]]*8,[{},*normal[1:]],[dict(normal[0],vaka='x'),*normal[1:]],[dict(normal[0],calisti=1),*normal[1:]],[dict(normal[0],dogrulandi=1),*normal[1:]],[dict(normal[0],ek=1),*normal[1:]]]
ok(all(reject(x) for x in bad),'şema, sekiz benzersiz vaka ve bool türü')

# --- carbon-c8-g4-bas ---
def _c8_birim_denetimi():
    _u = []
    def _same(got, exp):
        try:
            if not bool(got == exp):
                return False
        except Exception:
            return False
        if isinstance(exp, bool) or isinstance(got, bool):
            return isinstance(got, bool) and isinstance(exp, bool)
        if isinstance(exp, (int, float)) and isinstance(got, (int, float)):
            return True
        return isinstance(got, type(exp))
    def ok(cond, msg=None, got=None):
        _u.append(bool(cond))
        return bool(cond)
    def eq(got, exp, msg=None):
        r = _same(got, exp)
        _u.append(r)
        return r
    def yakin(got, exp, msg=None, tol=1e-6):
        try:
            r = abs(got - exp) <= tol
        except Exception:
            r = False
        _u.append(bool(r))
        return bool(r)
    def raises(exc, fn_cagri, *a, msg=None, **kw):
        try:
            fn_cagri(*a, **kw)
        except exc:
            _u.append(True)
            return True
        except Exception:
            _u.append(False)
            return False
        _u.append(False)
        return False
    manifest_dogrula = need('manifest_dogrula')
    kimlik_uygun = need('kimlik_uygun')
    sonuc_raporu = need('sonuc_raporu')
    def _birim_adim_1():
        from pathlib import Path
        import hashlib,tempfile,secrets,copy
        raw_fn=need('manifest_dogrula')
        def fn(*args):
            value=raw_fn(*args)
            if type(value) is not bool:raise TypeError('bool sonuç gerekli')
            return value
        base=Path(tempfile.mkdtemp(prefix='s36-contract-'));payload=secrets.token_bytes(180);p=base/'model.safetensors';p.write_bytes(payload);digest=hashlib.sha256(payload).hexdigest();m={'dosya':p.name,'sha256':digest};bak=copy.deepcopy(m)
        eq(fn(base,m),True,'gerçek çalışma dosyasının SHA256 özeti');eq(m,bak,'manifest değişmedi')
        eq(fn(str(base),m),True,'str klasör de kabul edilir')
        eq(fn(base,dict(m,sha256='0'*64)),False,'yanlış hash')
        p.write_bytes(payload+b'!');eq(fn(base,m),False,'dosya değiştiyse eski manifest yetmez');p.write_bytes(payload)
        for bad in (None,{},dict(m,ek=1),dict(m,dosya='../model.safetensors'),dict(m,dosya='/model.safetensors'),dict(m,dosya='C:\\x.safetensors'),dict(m,dosya='a/b.safetensors'),dict(m,dosya='a\\b.safetensors'),dict(m,dosya=''),dict(m,dosya=7),dict(m,dosya='model.SAFETENSORS'),dict(m,sha256=None),dict(m,sha256='g'*64),dict(m,sha256='a'*63),dict(m,sha256='a'*65),dict(m,sha256=digest.upper())):
            eq(fn(base,bad),False,'bozuk manifest fail closed')
        for n,allowed in ((80,True),(81,False)):
            name='a'*n+'.safetensors';(base/name).write_bytes(payload);eq(fn(base,{'dosya':name,'sha256':digest}),allowed,'dosya adının sınır uzunluğu')
        (base/'directory.safetensors').mkdir();eq(fn(base,dict(m,dosya='directory.safetensors')),False,'dizin ağırlık dosyası değildir')
        eq(fn(base/'yok',m),False,'eksik çalışma dizini');eq(fn(None,m),False,'bozuk çalışma dizini')
        link=base/'linked.safetensors'
        try:link.symlink_to(p)
        except OSError:pass
        else:eq(fn(base,dict(m,dosya=link.name)),False,'symlink kabul edilmez')
        import types as _ty36, unittest.mock as _mk36
        eq(fn(base, _ty36.MappingProxyType(m)), False, "manifest gerçek dict olmalı")
        eq(fn(123, m), False, "klasör str/Path olmalı")
        with _mk36.patch.object(Path, "is_symlink", return_value=True):
            eq(fn(base, m), False, "sembolik bağ reddedilmeli")
    try:
        _birim_adim_1()
    except Exception:
        _u.append(False)
    def _birim_adim_2():
        import secrets,copy
        raw_fn=need('kimlik_uygun')
        def fn(*args):
            value=raw_fn(*args)
            if type(value) is not bool:raise TypeError('bool sonuç gerekli')
            return value
        identity='s-'+secrets.token_hex(6)+'@pafta.invalid';issuer='http://127.0.0.1:5556';policy={'kimlik':identity,'issuer':issuer};bak=copy.deepcopy(policy)
        eq(fn(identity,issuer,policy),True,'iki sabit de tam eşleşti');eq(policy,bak,'politika değişmedi')
        for who,iss in ((identity+'x',issuer),(identity,issuer+'/'),(identity.upper(),issuer),(identity,issuer.upper()),(' '+identity,issuer),(identity,' '+issuer),(identity+'x',issuer+'x')):
            eq(fn(who,iss,policy),False,'kimlik VE issuer birebir olmalı')
        for value in (None,'',' ',7,True,[],{}):
            eq(fn(value,issuer,policy),False,'bozuk kimlik');eq(fn(identity,value,policy),False,'bozuk issuer')
        for bad in (None,{},dict(policy,ek=1),dict(policy,kimlik=''),dict(policy,kimlik=' '),dict(policy,kimlik=1),dict(policy,issuer=''),dict(policy,issuer=None)):
            eq(fn(identity,issuer,bad),False,'bozuk politika')
        for value in ('',' '):eq(fn(value,value,{'kimlik':value,'issuer':value}),False,'iki taraf boşsa onay yok')
    try:
        _birim_adim_2()
    except Exception:
        _u.append(False)
    def _birim_adim_3():
        import itertools,copy
        fn=need('sonuc_raporu');names=('keypair-normal','keypair-tahrifat','keypair-baska-anahtar','keyless-normal','keyless-tahrifat','keyless-baska-kimlik','keyless-baska-issuer','keyless-baska-root');positive={'keypair-normal','keyless-normal'}
        value_checks=[];unchanged_checks=[];order_checks=[]
        for values in itertools.product((False,True),repeat=8):
            rows=[{'vaka':n,'calisti':True,'dogrulandi':v} for n,v in zip(names,values)];bak=copy.deepcopy(rows);bad=sorted(n for n,v in zip(names,values) if v!=(n in positive));expect={'kabul':not bad,'hatalar':[],'beklenmeyen':bad,'dogrulanan':sorted(n for n,v in zip(names,values) if v)}
            value_checks.append(fn(rows)==expect);unchanged_checks.append(rows==bak);order_checks.append(fn(list(reversed(rows)))==expect)
        ok(len(value_checks)==256 and all(value_checks),'sekiz vakanın 256 sonuç kombinasyonu')
        ok(all(unchanged_checks),'256 girdinin hepsi korunur')
        ok(all(order_checks),'256 sonuçta sıra bağımsızlığı')
        normal=[{'vaka':n,'calisti':True,'dogrulandi':n in positive} for n in names]
        for i,n in enumerate(names):
            rows=copy.deepcopy(normal);rows[i]['calisti']=False
            eq(fn(rows),{'kabul':False,'hatalar':[n],'beklenmeyen':[],'dogrulanan':sorted(positive-{n})},'komut hatası güvenli ret değildir')
        def reject(v):
            try:fn(v);return False
            except ValueError:return True
        bad=[None,(),normal[:7],normal+[normal[0]],[normal[0]]*8,[{},*normal[1:]],[dict(normal[0],vaka='x'),*normal[1:]],[dict(normal[0],calisti=1),*normal[1:]],[dict(normal[0],dogrulandi=1),*normal[1:]],[dict(normal[0],ek=1),*normal[1:]]]
        ok(all(reject(x) for x in bad),'şema, sekiz benzersiz vaka ve bool türü')
        import types as _ty36c
        raises(ValueError, sonuc_raporu, [_ty36c.MappingProxyType(normal[0]), *normal[1:]], msg="kayıt gerçek dict olmalı")
        raises(ValueError, sonuc_raporu, [dict(normal[0], vaka=123), *normal[1:]], msg="vaka str olmalı")
    try:
        _birim_adim_3()
    except Exception:
        _u.append(False)
    return bool(_u) and all(_u)
ok(_c8_birim_denetimi(), "deney öncesi tam birim sözleşmesi korunmalı")
# --- carbon-c8-g4-son ---
if not all(checks):stop()
from sandbox import ai_gercek_ai_savunma_36 as D
try:r=D.deney(need('manifest_dogrula'),need('kimlik_uygun'),need('sonuc_raporu'))
except ai_lab.GercekLabYok as e:
    ok(False,'GERÇEK DENEY YAPILMADI: '+str(e));stop()
ok(all(r['kontroller']),'gerçek model, keypair/keyless ve bütün negatif kontroller')
ok(r['temizlendi'],'yalnız kendi container/network ve token cleanup')
ai_lab.kanit_yaz('savunma36-kabul',dict(r,kabul=all(checks)))
```
```solution
import ai_lab
from pathlib import Path
import hashlib,re
def manifest_dogrula(klasor,manifest):
    try:
        if not isinstance(manifest,dict) or set(manifest)!={'dosya','sha256'}:return False
        name=manifest['dosya'];wanted=manifest['sha256']
        if not re.fullmatch(r'[A-Za-z0-9_-][A-Za-z0-9_.-]{0,79}\.safetensors',name):return False
        if not isinstance(wanted,str):return False
        root=Path(klasor).resolve(strict=True);path=root/name
        if path.is_symlink():return False
        with path.open('rb') as f:got=hashlib.file_digest(f,'sha256').hexdigest()
        return got==wanted
    except (OSError,TypeError,ValueError):return False

def kimlik_uygun(kimlik,issuer,politika):
    if not isinstance(politika,dict) or set(politika)!={'kimlik','issuer'}:return False
    for value in (kimlik,issuer,politika['kimlik'],politika['issuer']):
        if not isinstance(value,str) or not value.strip():return False
    return kimlik==politika['kimlik'] and issuer==politika['issuer']

def sonuc_raporu(kayitlar):
    expected={'keypair-normal':True,'keypair-tahrifat':False,'keypair-baska-anahtar':False,'keyless-normal':True,'keyless-tahrifat':False,'keyless-baska-kimlik':False,'keyless-baska-issuer':False,'keyless-baska-root':False}
    if not isinstance(kayitlar,list) or len(kayitlar)!=8:raise ValueError('sekiz kayıt')
    seen=set();errors=[];wrong=[];verified=[]
    for row in kayitlar:
        if not isinstance(row,dict) or set(row)!={'vaka','calisti','dogrulandi'}:raise ValueError('şema')
        name=row['vaka']
        if name not in expected or name in seen or type(row['calisti']) is not bool or type(row['dogrulandi']) is not bool:raise ValueError('değer')
        seen.add(name)
        if not row['calisti']:errors.append(name)
        else:
            if row['dogrulandi']!=expected[name]:wrong.append(name)
            if row['dogrulandi']:verified.append(name)
    return {'kabul':not errors and not wrong,'hatalar':sorted(errors),'beklenmeyen':sorted(wrong),'dogrulanan':sorted(verified)}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_36 as D
    D.goster(manifest_dogrula,kimlik_uygun,sonuc_raporu)
```
:::
::: anlat Hata vitrini · başarısız komut güvenli ret değildir
Kanıttaki `cagrilar` listesini aç ve komutları sırayla oku. `generate-key-pair` key-pair kontrolünün anahtarını üretir; `sign-blob --key signer.key` dosyayı imzalar; `verify-blob --key signer.pub` bu anahtarla denetler. Gerçek keyless çağrısında `--key` verilmez: `--identity-token` geçici lab token dosyasını, `--fulcio-url` yalnız kendi localhost geçidini, `--trusted-root` bu koşunun public CA kökünü seçer. Önce `trusted-root create` ile yalnız özel kök materyali oluşturulur; default public servisler eklenmez. Bunların gerçek argv ve stdout/stderr sonuçları kanıtta ayrı durur. Dış kimlik hesabı açılması gerekmez.

Cosign v3.1.4 varsayılanında sertifika çıktısını base64 kodlayabilir; runtime yalnız kendi ürettiği public sertifikayı PEM'e çözer. Keyless doğrulamadaki `--certificate-identity` ve `--certificate-oidc-issuer` iki ayrı beklentidir. `--ca-roots` ile zincir bizim özel köke bağlanır; yanlış kök denenmesi bu yüzden gerçek bir negatif kontroldür. Kullanılan legacy/private bayraklar bu sürümde deprecated uyarısı üretir; bu uyarılar ham loglarda korunur. Public Tlog/SCT doğrulaması yapılmaması gizlenmez ve production için genel öneri değildir.

Son kaynakta Docker containerı `--network none` çalışır; host portu veya host dizini bağlanmaz. Cosign'ın localhost HTTP isteği sınırlı bir geçit üzerinden `docker exec` ile container loopback'indeki gerçek Fulcio'ya taşınır. Geçit sahte sertifika yanıtı üretmez. Sağlık ve signingCert HTTP sonuçları kanıtta var. Token, private key veya parolayı kayıt dosyasına yapıştırma; public cert/root/imza dosyaları ve redakte edilen komut sonucu yeterlidir. Her koşu yeni geçici kimlik/token/kök üretir; eski port veya tokenı kopyalamak yerine dersi yeniden Çalıştır.

Tahmin kodunun ilk çıktısı True olsa da ikinci çıktı False: komut çalışmadı. Sentetik verify.json bu farkı bilerek içerir; gerçek cosign logu değildir. Üçüncü starter hatayı güvenli saymaya çalışır. Gerçek kanıttaki stderr/exit code ile öğrenci raporunu birlikte oku: hiç çalışmayan bir doğrulama sistemi artifact bütünlüğünü ispatlamaz.
:::
::: anlat Sınır
Bu ders kendi model artifact imzasını ve private test issuer/root bağını ölçebilir; modelin zararsızlığını, gerçek kişinin kimliğini veya public Sigstore transparency/timestamp güvencesini kanıtlayamaz.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
### Bütünlük, kimlik ve yetki üç ayrı sorudur

Artifact hashinin eşleşmesi dosyanın değişmediğini gösterir; tek başına dosyayı kimin ürettiğini söylemez. İmza denetiminde anahtar veya sertifika güven kökü, kimlik ve issuer politikası da doğrulanır. Yerel Fulcio labı gerçek imza akışını özel otoriteyle çalıştırır; kamu Sigstore şeffaflık günlüğünün sağladığı ek kanıtları otomatik sağlamaz. İmzalı kötü model hâlâ kötü model olabilir.

| Yaygın yanlış | Mekanizmanın sınırı |
|---|---|
| Geçerli imza güvenli model demektir | İmza belirli kimlik ve bütünlük kanıtıdır; davranış değerlendirmesi ayrıdır. |

Saldırı–savunma bağlantısı: ai-saldiri-41.
:::
