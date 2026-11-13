---
id: ai-saldiri-51
title: ML Altyapısında Gerçek CVE · MLflow Source Güven Sınırı
summary: Görünür HTTP kaydını incele, source policy ve canary kanıtını ayır, iki gerçek MLflow sürümünde meşru artifact kontrolüyle karşılaştır.
esleme: ai-savunma-11, ai-savunma-20
timeout: 60
---
::: anlat Model sunucusu da bir uygulamadır
| Gerçek araç ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| MLflow model kaynağı ile artifact okuma arasında güven sınırı kurar | İlk üç görev görünür sentetik HTTP/JSON; final iki gerçek MLflow sürümünü çalıştırır | Fixture sonucu gerçek CVE kanıtı değildir |
| Bir yama belirli source türünü reddedebilir | Eski 2.1.1 ile 2.2.1 karşılaştırması; yalnız lab canary dosyası | 2.2.1 güncel veya bütün açıklara karşı güvenli sürüm değildir |

> [!NOT]
> Gerçek deney, önceden kurulan iki izole MLflow imajını kullanır. Ders düğmesi imaj indirmez veya kurulum yapmaz. `veri/ornek.json` ve `veri/create-version.http` sentetiktir. Setup her Run/Check için yeni geçici çalışma kopyası kurar; değişiklikler sonraki çalıştırmaya taşınmaz. Kaynağı haricî editörde veya yüklenen sözlüğü kodda değiştirebilirsin. Gizli testler ayrıdır. Final imaj yoksa PASS vermez ve kendi başına indirme yapmaz.

Bir dil modeli saldırı zincirindeki tek bileşen değildir. Model dosyalarını kaydeden registry, notebook arayüzü ve dosya sunan servis kendi giriş doğrulamasına ihtiyaç duyar. Buradaki konu modelin cevabını yönlendirmek değil, ML altyapısındaki gerçek bir servisin dosya erişim sınırını incelemektir. Gradio, Jupyter ve MLflow farklı ürünlerdir; birindeki gözlemi diğerine kanıt diye taşımayacağız. Bu dersin gerçek lab hedefi yalnız MLflow CVE-2023-1177 olarak seçildi. Diğer ürünlerdeki dosya erişimi ve token riskleri kavramsal bağlamdır, burada çalıştırılmış test değildir.

Vendor advisory, 2.2.0 ve öncesinin etkilendiğini ve 2.2.1 ile bu bulgunun yamalandığını belirtir. Sürüm numarası tek başına çalışan lab sonucu değildir. Kaynak incelemesinde eski create-model-version handler source alanını registry'ye iletirken karşılaştırma sürümünde local URI için ret kontrolü görülür. Deneyde bu farkı aynı sentetik girdilerle HTTP üzerinden ölçeceğiz. Düzeltme salt path içindeki iki nokta denetimi değildir: source URI'nin başka bir dizini kök olarak seçmesi de güven sınırını değiştirebilir. Son artifact dosya adı normal görünse bile kök kaynağın kim tarafından seçildiği önemlidir.

İlk görev dar bir uygulama policy'si kurar. Yalnız mlflow-artifacts scheme'i ve netsiz, query/fragment içermeyen mutlak path görünümü kabul edilir. Bu, MLflow'un bütün desteklediği scheme'lerin genel doğrulayıcısı değildir. File URI, http veya başka scheme bu lab sözleşmesinde reddedilir. URL decoding bir kez yapılır; path segmentlerinde boşluk değil boş segment, nokta ve iki nokta denetlenir. Böyle bir yardımcı her framework'ün decode sırasını, symlink davranışını veya SSRF sorunlarını çözmüş sayılmaz. Görev kendi dar sözleşmesini öğretir; canlı servis yaması bu yardımcıyla değiştirilmez.

İkinci görev HTTP gözleminden bulgu çıkarır. HTTP 200 tek başına sır okundu anlamına gelmez; gövde beklenen rastgele canary ile tam eşleşmelidir. Bir hata sayfasında aynı işaretin geçmesi, yanına açıklama eklenmesi veya HTML'de görünmesi aynı kanıt değildir. 4xx cevabı bu ölçümde ret sınıfıdır; hangi yetki kontrolünün neden çalıştığını tek başına ispatlamaz. 404 ile 403 aynı genel ret sınıfına girebilir, ama birinin kaynağı bulunamadı demesiyle diğerinin policy reddi olması aynı gerekçe değildir. Ham cevap ve register adımı ayrı tutulur. 5xx veya 3xx cevap güvenli ret sayılmaz; deney ya da transport hatası olarak incelenir.

Üçüncü görev eski ve yama sürümündeki meşru kontrolü birlikte tutar. Her sürüm için normal artifact ve yerel source denemesi vardır. Yerel okuma yamada reddedilip normal artifact de bozulduysa hizmetin düzgün çalıştığı gösterilmiş olmaz. Bu yüzden normal_akis, deney_tamam ve yama_gozlendi ayrı alanlardır. Gerçek gözlemin tamamlanması, istediğimiz açıklık sonucunun ortaya çıkmasıyla aynı koşul değildir. Eski sürüm de reddederse bunu raporlamak gerekir; testi geçsin diye eskiye `okundu` yazılamaz. Aynı şekilde yama sürümü okursa yanlışlanmış hipotezi saklamamalısın. Hedef bu ölçüm ayrımını doğru kodlamaktır.

Lab tasarımı runtime'da network none kullanır. Host portu yayınlanmaz; istemci container'ın kendi loopback servisine docker exec ile girer. Host klasörleri ve Docker socket bağlanmaz. Nonroot kullanıcı, cap-drop ve no-new-privileges ayarları inspect kaydından doğrulanır. Bunlar bütün container escape tehditlerini ortadan kaldırdığı iddiası değildir; bu kontrollü dosya okuma deneyinin erişim alanını daraltır. Build aşamasında bağımlılık için kullanılan ağ ile runtime'ın kapalı ağı birbirine karıştırılmaz. Kurulum kullanıcı onayıyla ayrı işlemdir; ders düğmesi sessizce image pull veya pip install yapmaz.

Öğrenci ham create-version.http dosyasını açınca source alanının yerel dizini seçtiğini görür. Bu dosya gerçek sunucu yanıtı değildir; istek biçimini öğrenmek için hazırlanmıştır. Önce tahmin et, sonra kusurlu starterı çalıştır ve farkı kendi cümlenle yorum olarak yaz. Çözümü açınca yalnız bir karşılaştırma işaretine bakma: hangi girişin neden reddedildiğini ve hangi kanıtın eksik olduğunu açıkla. Gerçek final kanıtında image ID, MLflow sürümü, ayarlar, HTTP adımları, gövde ve cleanup bulunmalıdır. Kullanıcının başka Docker container'larını kapatmak bu dersin cleanup'ı değildir; yalnız kendi benzersiz container kimlikleri silinir, imajlar korunur.

Saldırı↔savunma köprüsü `ai-savunma-11` en az ayrıcalık ve `ai-savunma-20` model tedarik zinciri konularıdır. Registry yetkisi ve artifact kökü ayrı düşünülür; modelin zararsız cevap vermesi altyapı dosya okumasını engellemez.

Kaynaklar: [MLflow vendor advisory](https://github.com/mlflow/mlflow/security/advisories/GHSA-xg73-94fp-g449), [eski handler](https://github.com/mlflow/mlflow/blob/v2.1.1/mlflow/server/handlers.py), [karşılaştırma handler](https://github.com/mlflow/mlflow/blob/v2.2.1/mlflow/server/handlers.py). Kaynak incelemesi gerçek lab kabulünün yerine geçmez.
:::
::: tahmin HTTP 200 tek başına yeterli mi?
Çıktıyı tahmin et; sonra Çalıştır ve farkı kendi cümlenle yorum satırı olarak yaz.
```python
canary="CANARY-X"
print(canary=="CANARY-X extra")
print(400<=499<500)
print(400<=500<500)
```
???
```cikti
False
True
False
```
Kusurlu başlangıçların hangisi bu ayrımı kaybediyor? Çözümü görmeden önce dosyadaki somut bir satırla gerekçelendir.
:::
::: gorev 1 · Source policy
`kaynak_izinli(uri)` işlevini yaz. Boş olmayan, başında/sonunda boşluk ve içinde kontrol karakteri bulunmayan string gerekir; bu biçim hatalarında `ValueError` ver. Diğer uygunsuz URI'lerde `False` döndür.

Yalnız `mlflow-artifacts` scheme'i, boş netloc/query/fragment ve tek `/` ile başlayan path kabul edilir. Path bir kez `unquote` edildikten sonra backslash veya boş, `.` ve `..` segmentleri bulunmamalıdır. Koşullar sağlanırsa gerçek bool `True` döndür. Bu dar lab policy'sidir; genel URL/SSRF doğrulayıcısı değildir.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-51")
```
```starter
# KUSURLU BAŞLANGIÇ KODU: önce sonucu tahmin et ve nedenini teşhis et.
def kaynak_izinli(uri):
    from urllib.parse import urlsplit,unquote
    if not isinstance(uri,str) or not uri or uri!=uri.strip():raise ValueError("URI")
    if any(ord(c)<32 for c in uri):raise ValueError("kontrol karakteri")
    try:u=urlsplit(uri)
    except ValueError:return False
    if u.scheme not in ("mlflow-artifacts","file") or u.netloc or u.query or u.fragment:return False
    path=unquote(u.path)
    if not path.startswith("/") or path.startswith("//") or "\\" in path:return False
    parts=path[1:].split("/")
    if any(x in ("",".","..") for x in parts):return False
    return True

from ai_saldiri_veri import json_yukle,metin_yukle
v=json_yukle("veri/ornek.json")
print("Sentetik JSON:",v)
print("Ham sentetik istek:\n",metin_yukle("veri/create-version.http"))
print("Source:",kaynak_izinli(v["uri"]))
```
```test
def sinama(fn):
    try:
        for x in ["mlflow-artifacts:/normal","mlflow-artifacts:/a/ok.txt","mlflow-artifacts:/model card"]:
            if fn(x) is not True:return False
        for x in ["file:///tmp/private","/tmp/private","mlflow-artifacts:normal","http://127.0.0.1/a","mlflow-artifacts://host/a","mlflow-artifacts://[","mlflow-artifacts:/a/../b","mlflow-artifacts:/a/%2e%2e/b","mlflow-artifacts:/a//b","mlflow-artifacts:/a/./b","mlflow-artifacts://a","mlflow-artifacts:/a?x=1","mlflow-artifacts:/a#b","mlflow-artifacts:/a\\b","mlflow-artifacts:/"]:
            if fn(x) is not False:return False
        for x in (None,1,""," mlflow-artifacts:/a","mlflow-artifacts:/a\n","mlflow-artifacts:/a\x1fb"):
            try:fn(x);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama(kaynak_izinli),"dar source şeması, netloc ve path sınırları")
```
```solution
def kaynak_izinli(uri):
    from urllib.parse import urlsplit,unquote
    if not isinstance(uri,str) or not uri or uri!=uri.strip():raise ValueError("URI")
    if any(ord(c)<32 for c in uri):raise ValueError("kontrol karakteri")
    try:u=urlsplit(uri)
    except ValueError:return False
    if u.scheme!="mlflow-artifacts" or u.netloc or u.query or u.fragment:return False
    path=unquote(u.path)
    if not path.startswith("/") or path.startswith("//") or "\\" in path:return False
    parts=path[1:].split("/")
    if any(x in ("",".","..") for x in parts):return False
    return True

from ai_saldiri_veri import json_yukle,metin_yukle
v=json_yukle("veri/ornek.json")
print("Sentetik JSON:",v)
print("Ham sentetik istek:\n",metin_yukle("veri/create-version.http"))
print("Source:",kaynak_izinli(v["uri"]))
```
```hint
Yerel source normal görünümlü dosya adını başka köke bağlayabilir.
```
:::
::: gorev 2 · HTTP canary kanıtı
`http_bulgusu(k)` işlevini yaz. Girdi tam olarak `status`, `govde`, `canary` alanlarını taşıyan sözlüktür. Status, bool olmayan 100–599 aralığında int; gövde string; canary boş olmayan string olmalıdır. Geçersiz girdide `ValueError` ver ve girdiyi değiştirme.

- Status 200 ve gövde canary ile tam eşleşirse `okundu`.
- Status 200 fakat gövde farklıysa `uyusmazlik`.
- Status 400–499 aralığındaysa `reddedildi`.
- Diğer durumlarda `hata`.

Gövde içinde canary geçmesi tam eşleşme değildir.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-51")
```
```starter
# KUSURLU BAŞLANGIÇ KODU: önce sonucu tahmin et ve nedenini teşhis et.
def http_bulgusu(k):
    if not isinstance(k,dict) or set(k)!={"status","govde","canary"}:raise ValueError("şema")
    if type(k["status"]) is not int or not 100<=k["status"]<=599:raise ValueError("status")
    if not isinstance(k["govde"],str) or not isinstance(k["canary"],str) or not k["canary"]:raise ValueError("metin")
    if k["status"]==200:
        return "okundu" if k["canary"] in k["govde"] else "uyusmazlik"
    if 400<=k["status"]<500:return "reddedildi"
    return "hata"

from ai_saldiri_veri import json_yukle,metin_yukle
v=json_yukle("veri/ornek.json")
print("Sentetik JSON:",v)
print("HTTP bulgusu:",http_bulgusu(v["http"]))
```
```test
def sinama(fn):
    try:
        for c in ("CANARY-A","CANARY-"+str(__import__('random').randint(1,999999))):
            for status,body,want in [(200,c,"okundu"),(200,c+"x","uyusmazlik"),(200,"","uyusmazlik"),(399,c,"hata"),(400,c,"reddedildi"),(499,c,"reddedildi"),(500,c,"hata"),(599,c,"hata"),(302,c,"hata"),(100,c,"hata")]:
                k={"status":status,"govde":body,"canary":c};old=dict(k)
                if fn(k)!=want or k!=old:return False
        for k in (None,{}, {"status":True,"govde":"x","canary":"x"},{"status":99,"govde":"x","canary":"x"},{"status":600,"govde":"x","canary":"x"},{"status":200,"govde":None,"canary":"x"},{"status":200,"govde":"x","canary":""},{"status":200,"govde":"x","canary":"x","ek":1}):
            try:fn(k);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama(http_bulgusu),"tam içerik, HTTP sınırı ve hata ayrımı")
```
```solution
def http_bulgusu(k):
    if not isinstance(k,dict) or set(k)!={"status","govde","canary"}:raise ValueError("şema")
    if type(k["status"]) is not int or not 100<=k["status"]<=599:raise ValueError("status")
    if not isinstance(k["govde"],str) or not isinstance(k["canary"],str) or not k["canary"]:raise ValueError("metin")
    if k["status"]==200:
        return "okundu" if k["govde"]==k["canary"] else "uyusmazlik"
    if 400<=k["status"]<500:return "reddedildi"
    return "hata"

from ai_saldiri_veri import json_yukle,metin_yukle
v=json_yukle("veri/ornek.json")
print("Sentetik JSON:",v)
print("HTTP bulgusu:",http_bulgusu(v["http"]))
```
```hint
Yanıtın tam gövdesi ile yalnız içinde geçen metni ayır.
```
:::
::: gorev 3 · Eski/yama karşılaştırması
`yama_raporu(kayitlar)` işlevini yaz. Girdi tam dört kayıt içeren listedir. Her kayıt tam `surum`, `tur`, `bulgu` alanlarını taşır. Sürüm `2.1.1` veya `2.2.1`; tür `normal` veya `yerel-kaynak`; bulgu `okundu`, `reddedildi`, `uyusmazlik` veya `hata` olmalıdır. Her sürüm/tür çifti tam bir kez yer alır. Geçersiz girdide `ValueError` ver; girdiyi değiştirme.

Dönen sözlük tam dört alan taşır:

- `surumler`: sürüm → tür → bulgu biçimindeki iç içe sözlük.
- `normal_akis`: her iki normal kontrolün `okundu` olması.
- `deney_tamam`: normal akış doğruyken iki yerel denemenin de `okundu` veya `reddedildi` olarak gözlenmiş olması.
- `yama_gozlendi`: normal akış doğruyken eski sürümde yerel okuma, karşılaştırma sürümünde yerel ret gözlenmesi.

Deneyin tamamlanması ile beklenen yama etkisinin görülmesi ayrı ölçütlerdir.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-51")
```
```starter
# KUSURLU BAŞLANGIÇ KODU: önce sonucu tahmin et ve nedenini teşhis et.
def yama_raporu(kayitlar):
    if not isinstance(kayitlar,list) or len(kayitlar)!=4:raise ValueError("dört kayıt")
    out={};seen=set()
    for k in kayitlar:
        if not isinstance(k,dict) or set(k)!={"surum","tur","bulgu"}:raise ValueError("şema")
        if k["surum"] not in ("2.1.1","2.2.1") or k["tur"] not in ("normal","yerel-kaynak"):raise ValueError("kimlik")
        if k["bulgu"] not in ("okundu","reddedildi","uyusmazlik","hata"):raise ValueError("bulgu")
        key=(k["surum"],k["tur"])
        if key in seen:raise ValueError("yinelenen")
        seen.add(key);out.setdefault(k["surum"],{})[k["tur"]]=k["bulgu"]
    normal=all(out[v]["normal"]=="okundu" for v in ("2.1.1","2.2.1"))
    tamam=True and all(out[v]["yerel-kaynak"] in ("okundu","reddedildi") for v in ("2.1.1","2.2.1"))
    yama=True and out["2.1.1"]["yerel-kaynak"]=="okundu" and out["2.2.1"]["yerel-kaynak"]=="reddedildi"
    return {"surumler":out,"normal_akis":normal,"deney_tamam":tamam,"yama_gozlendi":yama}

from ai_saldiri_veri import json_yukle,metin_yukle
v=json_yukle("veri/ornek.json")
print("Sentetik JSON:",v)
print("Yama raporu:",yama_raporu(v["kayitlar"]))
```
```test
def sinama(fn):
    import copy,itertools
    try:
        for old,new,n1,n2 in itertools.product(["okundu","reddedildi","uyusmazlik","hata"],repeat=4):
            v=[{"surum":"2.1.1","tur":"normal","bulgu":n1},{"surum":"2.1.1","tur":"yerel-kaynak","bulgu":old},{"surum":"2.2.1","tur":"normal","bulgu":n2},{"surum":"2.2.1","tur":"yerel-kaynak","bulgu":new}];bak=copy.deepcopy(v);a=fn(v)
            expected={"2.1.1":{"normal":n1,"yerel-kaynak":old},"2.2.1":{"normal":n2,"yerel-kaynak":new}}
            good=n1==n2=="okundu"
            if a!={"surumler":expected,"normal_akis":good,"deney_tamam":good and old in ("okundu","reddedildi") and new in ("okundu","reddedildi"),"yama_gozlendi":good and old=="okundu" and new=="reddedildi"} or v!=bak or fn(list(reversed(v)))!=a:return False
        for bad in (None,tuple(v),v[:3],v+[v[0]],[v[0]]*4,[dict(v[0],surum="3.0"),*v[1:]],[dict(v[0],tur="x"),*v[1:]],[dict(v[0],bulgu="gecti"),*v[1:]],[dict(v[0],ek=1),*v[1:]]):
            try:fn(bad);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama(yama_raporu),"meşru kontrol, iki sürüm, bütün sonuç kombinasyonları ve hata")
```
```solution
def yama_raporu(kayitlar):
    if not isinstance(kayitlar,list) or len(kayitlar)!=4:raise ValueError("dört kayıt")
    out={};seen=set()
    for k in kayitlar:
        if not isinstance(k,dict) or set(k)!={"surum","tur","bulgu"}:raise ValueError("şema")
        if k["surum"] not in ("2.1.1","2.2.1") or k["tur"] not in ("normal","yerel-kaynak"):raise ValueError("kimlik")
        if k["bulgu"] not in ("okundu","reddedildi","uyusmazlik","hata"):raise ValueError("bulgu")
        key=(k["surum"],k["tur"])
        if key in seen:raise ValueError("yinelenen")
        seen.add(key);out.setdefault(k["surum"],{})[k["tur"]]=k["bulgu"]
    normal=all(out[v]["normal"]=="okundu" for v in ("2.1.1","2.2.1"))
    tamam=normal and all(out[v]["yerel-kaynak"] in ("okundu","reddedildi") for v in ("2.1.1","2.2.1"))
    yama=normal and out["2.1.1"]["yerel-kaynak"]=="okundu" and out["2.2.1"]["yerel-kaynak"]=="reddedildi"
    return {"surumler":out,"normal_akis":normal,"deney_tamam":tamam,"yama_gozlendi":yama}

from ai_saldiri_veri import json_yukle,metin_yukle
v=json_yukle("veri/ornek.json")
print("Sentetik JSON:",v)
print("Yama raporu:",yama_raporu(v["kayitlar"]))
```
```hint
Meşru akış bozuluyorsa yama kanıtını başarılı sayma.
```
:::
::: gorev Gerçek deney · MLflow eski/yama HTTP karşılaştırması
Üçüncü işlevi kullan. Runtime yalnız önceden kurulmuş `pafta-ai-s51:mlflow-2.1.1` ve `pafta-ai-s51:mlflow-2.2.1` imajlarıyla çalışır. İmaj yoksa indirme yapmadan hata verir. Kanıttaki create-version ve get-artifact kayıtlarını ayır; ikinci sürümün hangi adımda reddettiğini kendi cümlenle yorumla. Yama sonucunun istediğimiz gibi olması tek başına kabul ölçütü değildir, meşru akış çalışmalıdır.
```meta
motor: ai-gercek
gereksinim: docker
timeout: 300
```
```starter
import ai_lab
def yama_raporu(kayitlar):return {}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_51 as D
    D.goster(yama_raporu)
```
```test
import ai_lab,ast
checks=[]
def kontrol(x,msg):checks.append(bool(x));ok(x,msg)
issues=ai_lab.kod_denetimi(src,("referans_rapor","kanit_yaz"),izin=())
try:
    tree=ast.parse(src)
    for node in ast.walk(tree):
        targets=node.targets if isinstance(node,ast.Assign) else [node.target] if isinstance(node,(ast.AugAssign,ast.AnnAssign)) else []
        if any(isinstance(t,ast.Attribute) for t in targets):issues.append("öğrenci kodu laboratuvar niteliği yamalayamaz")
except SyntaxError:issues.append("sözdizimi")
kontrol(not issues,"kopya/yama koruması: "+str(issues))
if issues:stop()
fn=need("yama_raporu")
def sinama(fn):
    import copy,itertools
    try:
        for old,new,n1,n2 in itertools.product(["okundu","reddedildi","uyusmazlik","hata"],repeat=4):
            v=[{"surum":"2.1.1","tur":"normal","bulgu":n1},{"surum":"2.1.1","tur":"yerel-kaynak","bulgu":old},{"surum":"2.2.1","tur":"normal","bulgu":n2},{"surum":"2.2.1","tur":"yerel-kaynak","bulgu":new}];bak=copy.deepcopy(v);a=fn(v)
            expected={"2.1.1":{"normal":n1,"yerel-kaynak":old},"2.2.1":{"normal":n2,"yerel-kaynak":new}}
            good=n1==n2=="okundu"
            if a!={"surumler":expected,"normal_akis":good,"deney_tamam":good and old in ("okundu","reddedildi") and new in ("okundu","reddedildi"),"yama_gozlendi":good and old=="okundu" and new=="reddedildi"} or v!=bak or fn(list(reversed(v)))!=a:return False
        for bad in (None,tuple(v),v[:3],v+[v[0]],[v[0]]*4,[dict(v[0],surum="3.0"),*v[1:]],[dict(v[0],tur="x"),*v[1:]],[dict(v[0],bulgu="gecti"),*v[1:]],[dict(v[0],ek=1),*v[1:]]):
            try:fn(bad);return False
            except ValueError:pass
        return True
    except Exception:return False
kontrol(sinama(fn),"meşru kontrol, iki sürüm, bütün sonuç kombinasyonları ve hata")

if not all(checks):stop()
from sandbox import ai_gercek_ai_saldiri_51 as D
try:r=D.deney(fn)
except ai_lab.GercekLabYok as e:
    kontrol(False,"GERÇEK DENEY YAPILMADI: "+str(e));stop()
kontrol(bool(r["referans"]) and r["rapor"]==r["referans"],"rapor gerçek HTTP kayıtlarıyla aynı")
kontrol(not r["hatalar"] and len(r["kayitlar"])==4,"dört gerçek gözlem ve transport başarıyla tamam")
kontrol((r["rapor"] or {}).get("deney_tamam",False),"iki meşru kontrol çalıştı; yerel denemeler gözlendi")
kontrol(all(x["izolasyon_dogrulandi"] and x["temizlendi"] for x in r["ortamlar"]),"runtime izolasyonu ve yalnız kendi container cleanup'ı doğrulandı")
ai_lab.kanit_yaz("saldiri51-kabul",{"kaynak":"gercek","kabul":all(checks),"ders":"ai-saldiri-51","deney":r})
```
```solution
import ai_lab
def yama_raporu(kayitlar):
    if not isinstance(kayitlar,list) or len(kayitlar)!=4:raise ValueError("dört kayıt")
    out={};seen=set()
    for k in kayitlar:
        if not isinstance(k,dict) or set(k)!={"surum","tur","bulgu"}:raise ValueError("şema")
        if k["surum"] not in ("2.1.1","2.2.1") or k["tur"] not in ("normal","yerel-kaynak"):raise ValueError("kimlik")
        if k["bulgu"] not in ("okundu","reddedildi","uyusmazlik","hata"):raise ValueError("bulgu")
        key=(k["surum"],k["tur"])
        if key in seen:raise ValueError("yinelenen")
        seen.add(key);out.setdefault(k["surum"],{})[k["tur"]]=k["bulgu"]
    normal=all(out[v]["normal"]=="okundu" for v in ("2.1.1","2.2.1"))
    tamam=normal and all(out[v]["yerel-kaynak"] in ("okundu","reddedildi") for v in ("2.1.1","2.2.1"))
    yama=normal and out["2.1.1"]["yerel-kaynak"]=="okundu" and out["2.2.1"]["yerel-kaynak"]=="reddedildi"
    return {"surumler":out,"normal_akis":normal,"deney_tamam":tamam,"yama_gozlendi":yama}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_51 as D
    D.goster(yama_raporu)
```
:::
::: anlat Hata vitrini · yanlış güven
Üçüncü kusurlu starterın gerçek Python Run çıktısı, sentetik örnekte yama sürümünün normal akışı reddedildiği hâlde `normal_akis=False, deney_tamam=True, yama_gozlendi=True` verdi. Kaydedilmiş hesaplama `outputs/yeni-ai-saldiri-51/gorunur-run-3-starter.json` içindedir; gerçek MLflow çıktısı değildir. Bu üç alan neden birbiriyle tutarsız? Meşru akış bozulmuşken yama başarılı diyebilir misin? İkinci starter da `CANARY-EXAMPLE extra` gövdesini tam eşleşme sanarak `okundu` verdi. Doğru çözüm farklı gövdeyi uyusmazlik sınıfına alır. Gerçek deneyin kendi yanıtları imaj kurulumundan sonra ayrıca üretilmelidir.
:::
::: anlat Sınır
Bu ders yalnız kendi izole MLflow laboratuvarındaki canary dosyasını ve belirli CVE akışını gösterebilir; Gradio/Jupyter açıklığını, container escape güvenliğini veya 2.2.1 sürümünün genel güvenliğini gösteremez.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
### Başarılı HTTP ile dosya okuma kanıtını ayır

Model registry source alanını kabul edince sonraki artifact okuma işleminin hangi kökü kullanacağını etkiler. Risk yalnız son dosya adındaki ../ dizisi değildir; kök kaynağının seçimini de içerir. HTTP 200 gövdesi rastgele canary ile tam eşleşmedikçe lab dosyası okunmuş sayılmaz. Yamalı sürümde meşru artifact da okunabilmelidir; her şeyi reddeden servis güvenli işlevsellik karşılaştırması değildir. Bu deneyde belirli eski sürüm farkı ölçülür, sürüm 2.2.1 için genel güvenlilik iddiası kurulmaz.

| Yaygın yanlış | Mekanizmanın söylediği |
|---|---|
| Sürüm numarası kanıttır | Çalışan image kimliği, gerçek HTTP yanıtı ve normal kontrol birlikte gerekir. |

Sonraki bağlantı: ai-savunma-20 ile tedarik zinciri sürüm politikası.
:::
