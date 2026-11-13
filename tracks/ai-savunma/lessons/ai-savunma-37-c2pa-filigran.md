---
id: ai-savunma-37
title: C2PA ve Filigran · İmza Bütünlüğü, İmzacı Güveni ve İçerik Gerçekliği Ayrı Sorulardır
summary: Sentetik bir PNG'yi onaylı yerel c2patool 0.28.4 ile TEST sertifikasıyla imzala, aynı görüntüye LSB filigranı göm; metadata ekleme, yeniden kaydetme, JPEG, ölçekleme ve saldırganın kendi sertifikasıyla yeniden imzalaması sonrasında hangi kanıtın sağ kaldığını ve ne söylediğini ölç.
esleme: ai-savunma-36, ai-savunma-20, ai-saldiri-53
timeout: 60
---

::: anlat Kaynak kanıtı: ne kanıtlar, ne kanıtlamaz?
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| C2PA (Coalition for Content Provenance and Authenticity) manifesti: dosyaya gömülü, X.509 sertifikasıyla imzalanmış köken iddiaları ve dosya baytlarının hash'i | Final: kullanıcı onayıyla `.deps` altına kurulan resmî `c2patool 0.28.4` (Windows, sha256 doğrulamalı), sentetik 96×64 PNG, c2patool'un örnek **TEST** sertifikası, koşu sırasında üretilen yerel bir saldırgan sertifikası | Üretim güven listesini, gerçek bir kamera ya da yayıncı imzasını, başka dosya türlerini ölçmez |
| Görünmez filigran (watermark): içeriğin kendisine gömülü işaret | Final: R kanalının en düşük bitine 5'er tekrarla gömülen 32 rastgele bit (LSB) | Ticari, dayanıklı (robust) filigranların ya da üretken model filigranlarının davranışını göstermez |

> [!NOT]
> Görev 1'deki `okumalar` yazarın gerçek c2patool koşusundan alınmış ham çıktılardır; görüntü sentetiktir, imza TEST sertifikasıyladır, gerçek kişi ya da kurum yoktur. Görev 2 ve 3'teki değerler elle yazılmıştır. Setup her Çalıştır/Kontrol Et adımında geçici kopya kurar; **kalıcılık yoktur**. Ekranda ayrı bir dosya görüntüleyici yoktur; içeriği görmek için başlangıç kodundaki `print` satırlarını kullan. Final ağ kullanmaz (zaman damgası sunucusu yok), otomatik indirme yapmaz; c2patool eksikse açıkça durur. Geçici dosyalar koşu sonunda silinir.

**C2PA nedir?** Bir dosyaya gömülen, imzalı bir **manifest**tir. Manifestin içinde iddialar (assertion) vardır: "bu görüntü dijital olarak oluşturuldu", "şu araçla düzenlendi" gibi. Her iddianın hash'i talep (claim) içinde tutulur, talep de imzalanır. **Hard binding** dosyanın baytlarını hash'ler (`c2pa.hash.data`); dosyada manifest dışındaki tek bir bayt değişirse hash tutmaz. İmza, imzacının X.509 sertifikasıyla atılır.

**Üç ayrı soru.** Doğrulayıcı bir dosyaya bakınca üç farklı soruyu cevaplar ve bunları karıştırmak en sık hatadır:
1. **Bütünlük:** Manifest ve dosya imzalandıktan sonra değişti mi? (`assertion.dataHash.mismatch` → `Invalid`)
2. **İmzacı güveni:** İmzayı atan sertifika, doğrulayıcının güvendiği bir köke (trust anchor) bağlanıyor mu? Bağlanmıyorsa imza matematiksel olarak geçerli olsa bile `signingCredential.untrusted` yazılır ve durum `Valid` kalır, `Trusted` olmaz.
3. **İçerik gerçekliği:** Görüntüdeki şey gerçekten oldu mu? C2PA buna cevap vermez. Spesifikasyon, köken verisinin "iyi" ya da "kötü" olduğuna dair değer yargısı vermemesi gerektiğini söyler.

Bu laboratuvarda c2patool çıktısındaki `validation_state` alanı üç değer alır: `Trusted`, `Valid`, `Invalid`. Manifest hiç yoksa araç hata kodu ile çıkar ve "No claim found" yazar. Dikkat: `Valid` durumundaki bir dosyanın `failure` listesi boş değildir; güvensiz imzacı orada bir "başarısızlık" kodu olarak durur.

**Filigran neden ayrı?** C2PA manifesti dosyanın **yanında** taşınır; görüntüyü yeniden kaydeden, ekran görüntüsü alan ya da sosyal ağa yükleyen bir işlem manifesti siler. Filigran ise piksellerin **içindedir**; yeniden kaydetmede kalabilir, ama sıkıştırma ve ölçekleme gibi pikselleri değiştiren işlemlerde bozulabilir. C2PA spesifikasyonu filigranı ve parmak izini **soft binding** olarak tanımlar: manifesti silinmiş bir dosyayı, başka bir yerde saklanan manifestle yeniden eşleştirmek için. Filigran bir imza değildir; kim koyduğunu kanıtlamaz.

**Saldırgan ne dener?** (1) Manifesti silmek: dosyayı yeniden kaydeder; "manifest yok" sonucu çoğu yerde "kanıt yok" diye okunur, "sahte" diye değil. (2) Kendi sertifikasıyla yeniden imzalamak: pikselleri değiştirir ve "Haber Ajansı" adını taşıyan kendi ürettiği bir sertifikayla imzalar. İmza matematiksel olarak geçerlidir. (3) Arayüzün "imzalı ✓" rozetine güvenmek: rozet bütünlüğü gösterip imzacının kim olduğunu ve güvenilip güvenilmediğini saklarsa, saldırganın imzası da aynı rozeti alır.

**Savunma neden kırılır?** Doğrulayıcı `Valid` ile `Trusted`'ı aynı sayarsa, saldırganın kendi imzası kabul edilir. "Manifest yok"u "sahte" sayarsa, meşru yeniden kaydedilmiş her dosya suçlanır; "manifest yok"u "temiz" sayarsa, manifesti silmek saldırganın tek işi olur. Güven listesine bir **TEST** kökü eklemek, o kökle imzalanan her şeyi "güvenilen" yapar; bu derste test kökü bilerek eklenir ve sonuç asla üretim güveni diye sunulmaz.

Kaynaklar: [C2PA Teknik Spesifikasyonu 2.1](https://spec.c2pa.org/specifications/specifications/2.1/specs/C2PA_Specification.html), [c2patool v0.28.4 sürümü](https://github.com/contentauth/c2patool/releases/tag/v0.28.4). Bu dersteki bütün sayılar yalnız yerel kanıttan gelir.

Saldırı↔savunma köprüsü: ai-savunma-36 model dosyasını cosign ile imzalar; bu ders aynı imza/güven ayrımını medya köken kanıtında kurar. ai-savunma-20 tedarik zinciri güvenini, ai-saldiri-53 görüntü üzerinde piksel düzeyinde saldırıyı anlatır.
:::

::: tahmin En düşük bit nasıl yazılır?
Çıktıyı tahmin et, sonra Çalıştır ile karşılaştır.
```python
v = 203
print(v | 0, v & 254 | 0)
print(bin(v)[-3:], bin(v & 254)[-3:])
print(sum([1, 0, 1, 1, 0]) * 2 > 5)
```
???
```cikti
203 202
011 010
True
```
Tahmininle gerçek çıktı arasındaki farkı tezgâhta yorum satırı olarak yaz: `v | 0` neden 203 kaldı, sıfır bitini yazmak için ne gerekir? Sonra üç kusurlu başlangıç kodunu çalıştır. Hangisi güvenilmeyen ama geçerli bir imzayı "geçersiz" sayıyor ve "manifest yok"u "geçersiz" yapıyor, hangisi 0 bitini hiç yazamıyor ve tek değere bakıp çoğunluğu atlıyor, hangisi bozulmuş manifesti "imzalı" sayıp güveni yanlış okumadan alıyor? Önce kendin teşhis et; açıklama çözümün ardından gelir.
:::

::: gorev 1 · c2patool çıktısını sınıflandır
`c2pa_durumu(okuma)`: `okuma` tam olarak `rc` (int, bool değil), `stdout`, `stderr` (string) alanlarından oluşan sözlük; değilse `ValueError`. `rc` sıfır değilse: `stderr` içinde `No claim found` geçiyorsa `{"durum": "manifest-yok", "hatalar": [], "imzaci": None}`; geçmiyorsa araç hatasıdır, `ValueError`. `rc` sıfırsa `stdout` JSON'dur (çözülemezse `ValueError`); kök bir sözlük olmalı ve `validation_state` değeri `Trusted` → `guvenilen`, `Valid` → `gecerli-guvenilmeyen`, `Invalid` → `gecersiz` olmalı (başka değer ya da eksikse `ValueError`). `hatalar`: `validation_results.activeManifest.failure` içindeki `code` değerleri, tekrarsız ve sıralı (alan yoksa boş liste). `imzaci`: **aktif** manifestin (`manifests[active_manifest]`) `signature_info` alanından `{"issuer", "common_name"}` (yoksa `None`). Girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-37")
```

```starter
import json
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def c2pa_durumu(okuma):
    if okuma["rc"]:return {"durum":"gecersiz","hatalar":[],"imzaci":None}
    j=json.loads(okuma["stdout"])
    hata=[f["code"] for f in j.get("validation_results",{}).get("activeManifest",{}).get("failure",[])]
    si=list(j["manifests"].values())[0]["signature_info"]
    durum="gecersiz" if hata else "guvenilen"
    return {"durum":durum,"hatalar":hata,"imzaci":{"issuer":si.get("issuer"),"common_name":si.get("common_name")}}

from ai_savunma_veri import json_yukle
v=json_yukle("veri/c2pa.json")
for o in v["okumalar"]:
    r=c2pa_durumu(o["okuma"])
    print(o["id"],"| rc:",o["okuma"]["rc"],"|",r["durum"],"| hatalar:",r["hatalar"],"| imzacı:",r["imzaci"])
```
```test
def sinama1(f):
    import json,copy
    try:
        def J(st,fails,si=None,vr=True):
            si={"issuer":"Kok A","common_name":"Imzaci A"} if si is None else si
            j={"active_manifest":"urn:b","manifests":{"urn:a":{"signature_info":{"issuer":"Eski","common_name":"Eski"}},"urn:b":{"signature_info":si}},"validation_state":st}
            if vr:j["validation_results"]={"activeManifest":{"failure":[{"code":c} for c in fails],"success":[{"code":"claimSignature.validated"}]}}
            return {"rc":0,"stdout":json.dumps(j),"stderr":""}
        I={"issuer":"Kok A","common_name":"Imzaci A"}
        U="signingCredential.untrusted";H="assertion.dataHash.mismatch"
        V=[(J("Trusted",[]),{"durum":"guvenilen","hatalar":[],"imzaci":I}),
           (J("Valid",[U]),{"durum":"gecerli-guvenilmeyen","hatalar":[U],"imzaci":I}),
           (J("Invalid",[U,H,H]),{"durum":"gecersiz","hatalar":[H,U],"imzaci":I}),
           (J("Valid",[],vr=False),{"durum":"gecerli-guvenilmeyen","hatalar":[],"imzaci":I}),
           (J("Invalid",[H],si={"issuer":"Sahte Org"}),{"durum":"gecersiz","hatalar":[H],"imzaci":{"issuer":"Sahte Org","common_name":None}}),
           ({"rc":1,"stdout":"","stderr":" Error: No claim found\n"},{"durum":"manifest-yok","hatalar":[],"imzaci":None}),
           ({"rc":2,"stdout":"{}","stderr":"Error: No claim found"},{"durum":"manifest-yok","hatalar":[],"imzaci":None})]
        for o,b in V:
            e=copy.deepcopy(o)
            if f(o)!=b or o!=e:return False
        for bad in (None,[],{"rc":0,"stdout":"{}"},dict(J("Valid",[]),ek=1),dict(J("Valid",[]),rc=True),dict(J("Valid",[]),rc="0"),dict(J("Valid",[]),stdout=None),
                    dict(J("Valid",[]),stderr=5),{"rc":1,"stdout":"","stderr":"Error: file not found"},{"rc":0,"stdout":"değil json","stderr":""},
                    {"rc":0,"stdout":"[]","stderr":""},dict(J("Valid",[]),stdout=J("Valid",[])["stdout"].replace("Valid","Unknown")),
                    {"rc":0,"stdout":json.dumps({"manifests":{}}),"stderr":""}):
            try:f(bad);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama1(c2pa_durumu),"durum eşlemesi, aktif manifest, hata kodları, manifest yok ve geçersiz girdi")
import json as _json
for ad,mut in [("hata listesi varsa geçersiz",lambda o:dict(c2pa_durumu(o),durum="gecersiz") if c2pa_durumu(o)["hatalar"] else c2pa_durumu(o)),("manifest yok = geçersiz",lambda o:dict(c2pa_durumu(o),durum="gecersiz") if c2pa_durumu(o)["durum"]=="manifest-yok" else c2pa_durumu(o)),("imzacı ilk manifestten",lambda o:dict(c2pa_durumu(o),imzaci={"issuer":"Eski","common_name":"Eski"}) if o["rc"]==0 and "urn:a" in o["stdout"] else c2pa_durumu(o))]:
    ok(not sinama1(mut),"mutant reddedildi: "+ad)
# --- carbon-c8-ek-bas ---
raises(ValueError, c2pa_durumu, {"rc": 0.0, "stdout": "{}", "stderr": ""}, msg="rc int olmalı")
raises(ValueError, c2pa_durumu, {"rc": True, "stdout": "{}", "stderr": ""}, msg="rc bool olamaz")
raises(ValueError, c2pa_durumu, {"rc": 0, "stdout": 123, "stderr": ""}, msg="stdout str olmalı")
raises(ValueError, c2pa_durumu, {"rc": 0, "stdout": "{}", "stderr": 123}, msg="stderr str olmalı")
_ok_json37 = '{"active_manifest":"m","manifests":{"m":{"signature_info":{"issuer":"A","common_name":"B"}}},"validation_state":"Trusted"}'
raises(ValueError, c2pa_durumu, {"rc": False, "stdout": _ok_json37, "stderr": ""}, msg="rc bool False reddedilmeli")
raises(ValueError, c2pa_durumu, {"rc": 1, "stdout": _ok_json37, "stderr": "Error: io"}, msg="sıfır dışı rc geçerli stdout olsa da reddedilmeli")
# --- carbon-c8-ek-son ---
```
```solution
import json
def c2pa_durumu(okuma):
    esle={"Trusted":"guvenilen","Valid":"gecerli-guvenilmeyen","Invalid":"gecersiz"}
    if not isinstance(okuma,dict) or set(okuma)!={"rc","stdout","stderr"}:raise ValueError("şema")
    if type(okuma["rc"]) is not int or not isinstance(okuma["stdout"],str) or not isinstance(okuma["stderr"],str):raise ValueError("alan")
    if okuma["rc"]:
        if "No claim found" in okuma["stderr"]:return {"durum":"manifest-yok","hatalar":[],"imzaci":None}
        raise ValueError("araç hatası")
    j=json.loads(okuma["stdout"])
    if not isinstance(j,dict) or j.get("validation_state") not in esle:raise ValueError("durum")
    si=j["manifests"][j["active_manifest"]]["signature_info"]
    hata=sorted({f["code"] for f in j.get("validation_results",{}).get("activeManifest",{}).get("failure",[])})
    return {"durum":esle[j["validation_state"]],"hatalar":hata,"imzaci":{"issuer":si.get("issuer"),"common_name":si.get("common_name")}}

from ai_savunma_veri import json_yukle
v=json_yukle("veri/c2pa.json")
for o in v["okumalar"]:
    r=c2pa_durumu(o["okuma"])
    print(o["id"],"| rc:",o["okuma"]["rc"],"|",r["durum"],"| hatalar:",r["hatalar"],"| imzacı:",r["imzaci"])
```
```hint
Önce `rc` ve `stderr`'e bak; JSON'a ancak araç başarılı döndüyse geç. `failure` listesinin boş olmaması tek başına geçersizlik demek değildir.
```
:::

::: anlat Filigran: kapasite, tekrar ve çoğunluk
LSB filigranı her piksel değerinin en düşük bitini taşıyıcı olarak kullanır: değer en fazla 1 değişir, göz fark etmez. Aynı biti birkaç değere (`tekrar`) yazıp okurken çoğunluk oyu almak, tek tük bozulmalara karşı dayanıklılık sağlar; tekrar sayısı tek olmalıdır ki eşitlik çıkmasın. Bedeli kapasitedir: `bit sayısı × tekrar` kadar değer gerekir. Bu yöntem basittir ve **dayanıklı değildir**: JPEG sıkıştırması ve ölçekleme en düşük bitleri yeniden hesaplar. Finalde bunun gerçekten olup olmadığını bit hata oranıyla (BER) ölçeceksin.
:::

::: gorev 2 · LSB filigranı göm ve çoğunlukla oku
`filigran_gom(degerler, bitler, tekrar)`: `degerler` 0–255 arası int listesi (bool değil); `bitler` boş olmayan, yalnız 0/1 int listesi; `tekrar` tek sayı ve ≥ 1; `len(bitler) * tekrar <= len(degerler)`. Aksi hâlde `ValueError`. `i`. bit, `i*tekrar` ile `i*tekrar + tekrar - 1` arasındaki her değerin en düşük bitine yazılır (`(v & 254) | bit`); kalan değerler aynen kalır. Yeni liste döndür, girdi değişmez. `filigran_oku(degerler, n, tekrar)`: aynı değer/tekrar kuralları, `n` ≥ 1 int ve `n * tekrar <= len(degerler)`. Her grubun en düşük bitlerinde **çoğunluk** oyu: 1'lerin sayısı yarıdan fazlaysa 1, değilse 0. `n` bitlik liste döndür.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-37")
```

```starter
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def filigran_gom(degerler,bitler,tekrar):
    y=list(degerler)
    for i,b in enumerate(bitler):
        for r in range(tekrar):y[i*tekrar+r]=y[i*tekrar+r]|b
    return y

# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def filigran_oku(degerler,n,tekrar):
    return [degerler[i*tekrar]&1 for i in range(n)]

from ai_savunma_veri import json_yukle
v=json_yukle("veri/c2pa.json")
g=filigran_gom(v["degerler"],v["bitler"],v["tekrar"])
print("gömülmüş:",g)
print("temizden oku:",filigran_oku(g,len(v["bitler"]),v["tekrar"]),"| beklenen:",v["bitler"])
print("bozulmuştan oku:",filigran_oku(v["bozulmus"],len(v["bitler"]),v["tekrar"]))
```
```test
def sinama2(gom,oku):
    import random,copy
    try:
        d=[10,11,12,13,14,15];e=list(d)
        if gom(d,[1,0],3)!=[11,11,13,12,14,14] or d!=e:return False
        if gom([255,0,7,8],[0],1)!=[254,0,7,8] or gom([0,0,0],[1],3)!=[1,1,1] or gom([1,2,3,4,5,6,7],[0,1],3)!=[0,2,2,5,5,7,7]:return False
        if oku([1,1,0,0,0,1],2,3)!=[1,0] or oku([1,0,1,0,1],1,5)!=[1] or oku([0,0,1,1,1],1,5)!=[1] or oku([3,2,2],1,3)!=[0] or oku([2,3,3,9],1,3)!=[1]:return False
        if oku([0],1,1)!=[0] or oku([255],1,1)!=[1] or oku([1,1,0,0,0],1,5)!=[0] or oku([1,1,1,0,0,0,0],1,7)!=[0] or oku([0,255],2,1)!=[0,1]:return False
        rng=random.Random(37)
        for n,t in ((1,1),(5,3),(12,5),(3,7)):
            v=[rng.randrange(256) for _ in range(n*t+rng.randrange(4))];b=[rng.randrange(2) for _ in range(n)];v0=list(v)
            g=gom(v,b,t)
            if v!=v0 or len(g)!=len(v) or g[n*t:]!=v[n*t:] or oku(g,n,t)!=b or any(abs(x-y)>1 for x,y in zip(g,v)):return False
            if t>1:
                k=list(g)
                for i in range(n):k[i*t]^=1
                if oku(k,n,t)!=b:return False
        for args in (([1,2,3],[1],2),([1,2,3],[1],0),([1,2,3],[1],True),([1,2],[1,0],3),([1,2,3],[],1),([256],[1],1),([-1],[1],1),([1.0],[1],1),([True],[1],1),(["1"],[1],1),
                     ([1,2,3],[2],1),([1,2,3],[True],1),([1,2,3],[-1],1),([1,2,3],["1"],1),((1,2,3),[1],1),([1,2,3],(1,),1),([1,2,3],[1],-1),([1,2,3],[1],1.0)):
            try:gom(*args);return False
            except ValueError:pass
        for args in (([1,2,3],0,1),([1,2,3],True,1),([1,2,3],1,2),([1,2,3],1,0),([1,2],1,3),([1,2,3],2,3),([256],1,1),([-1],1,1),([True],1,1),((1,),1,1),([1,2,3],1,1.0),([1,2,3],1.0,1),([1,2,3],-1,1)):
            try:oku(*args);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama2(filigran_gom,filigran_oku),"LSB gömme, çoğunluk oylaması, kapasite ve geçersiz girdi")
def _or_gom(d,b,t):
    g=filigran_gom(d,b,t)
    return [x|bb for x,bb in zip(d,[b[i//t] if i<len(b)*t else 0 for i in range(len(d))])] if g else g
for ad,g,o in [("OR ile gömme",_or_gom,filigran_oku),("çoğunluk yok",filigran_gom,lambda d,n,t:[d[i*t]&1 for i in range(n)] if filigran_oku(d,n,t) is not None else None),("kalan değerler sıfır",lambda d,b,t:filigran_gom(d,b,t)[:len(b)*t]+[0]*(len(d)-len(b)*t),filigran_oku)]:
    ok(not sinama2(g,o),"mutant reddedildi: "+ad)
# --- carbon-c8-ek-bas ---
raises(ValueError, filigran_gom, [1, 2, 3], [True], 3, msg="bit bool olamaz")
raises(ValueError, filigran_gom, [True, 2, 3], [1], 3, msg="değer bool olamaz")
raises(ValueError, filigran_oku, [1, 2, 3], True, 3, msg="n bool olamaz")
raises(ValueError, filigran_oku, [1, 2, 3], 1, -3, msg="negatif tek tekrar reddedilmeli")
raises(ValueError, filigran_oku, [True, 2, 3], 1, 3, msg="filigran_oku değer bool olamaz")
# --- carbon-c8-ek-son ---
```
```solution
def filigran_gom(degerler,bitler,tekrar):
    if not isinstance(bitler,list) or any(type(b) is not int or b not in (0,1) for b in bitler):raise ValueError("bitler")
    if not isinstance(degerler,list) or any(type(v) is not int or not 0<=v<=255 for v in degerler):raise ValueError("değerler")
    if type(tekrar) is not int or tekrar<1 or tekrar%2==0 or not bitler or len(bitler)*tekrar>len(degerler):raise ValueError("tekrar/kapasite")
    y=list(degerler)
    for i,b in enumerate(bitler):
        for r in range(tekrar):y[i*tekrar+r]=(y[i*tekrar+r]&254)|b
    return y

def filigran_oku(degerler,n,tekrar):
    if not isinstance(degerler,list) or any(type(v) is not int or not 0<=v<=255 for v in degerler):raise ValueError("değerler")
    if type(n) is not int or n<1 or type(tekrar) is not int or tekrar<1 or tekrar%2==0 or n*tekrar>len(degerler):raise ValueError("n/tekrar/kapasite")
    return [int(sum(degerler[i*tekrar+r]&1 for r in range(tekrar))*2>tekrar) for i in range(n)]

from ai_savunma_veri import json_yukle
v=json_yukle("veri/c2pa.json")
g=filigran_gom(v["degerler"],v["bitler"],v["tekrar"])
print("gömülmüş:",g)
print("temizden oku:",filigran_oku(g,len(v["bitler"]),v["tekrar"]),"| beklenen:",v["bitler"])
print("bozulmuştan oku:",filigran_oku(v["bozulmus"],len(v["bitler"]),v["tekrar"]))
```
```hint
Biti yazmadan önce eski en düşük biti temizle; aksi hâlde 0 yazamazsın. Okurken grubun tamamını say.
```
:::

::: anlat Kanıtı dönüşüm dönüşüm okumak
Finalde aynı imzalı dosyadan altı dosya çıkar ve her biri iki kez okunur: varsayılan ayarla ve yalnız c2patool'un örnek TEST kökünü güvenilir sayan ayarla. Raporu kurarken üç tuzaktan kaçın: bozulmuş (`gecersiz`) bir manifest "imzalı" değildir; güven bilgisi test kök okumasından gelir; filigranın kaldığına `ber <= esik` ile karar verilir. `yalniz_filigran` listesi, C2PA'nın kaybolduğu ama soft binding'in hâlâ iz taşıdığı durumları gösterir. `imzali_guvenilmeyen` listesi ise "imzalı ✓" rozetinin tek başına neden yetmediğini gösterir.
:::

::: gorev 3 · Hangi kanıt hangi dönüşümden sağ çıktı?
`kanit_raporu(kayitlar, esik)`: `esik` int ya da float (bool değil), 0 ≤ esik ≤ 1. `kayitlar` boş olmayan liste; her kayıt tam olarak `id` (benzersiz dolu string), `varsayilan` ve `test_kok` (`manifest-yok`, `gecersiz`, `gecerli-guvenilmeyen`, `guvenilen` değerlerinden biri), `ber` (int ya da float, bool değil, 0–1). Aksi hâlde `ValueError`. Her kayıt için `{"id", "c2pa", "guvenilen", "filigran_kaldi"}`: `c2pa` varsayılan okumadan `manifest-yok` → `yok`, `gecersiz` → `bozuk`, diğerleri → `imzali`; `guvenilen` = `test_kok == "guvenilen"`; `filigran_kaldi` = `ber <= esik`. Satırlar `id`'ye göre sıralı. Listeler (sıralı): `yalniz_filigran` (c2pa yok ama filigran kaldı), `hicbiri` (c2pa yok ve filigran kalmadı), `imzali_guvenilmeyen` (c2pa imzalı ama güvenilen değil). `{"satirlar", "yalniz_filigran", "hicbiri", "imzali_guvenilmeyen"}` döndür. Girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-37")
```

```starter
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def kanit_raporu(kayitlar,esik):
    sat=[]
    for k in kayitlar:
        c="yok" if k["varsayilan"]=="manifest-yok" else "imzali"
        sat.append({"id":k["id"],"c2pa":c,"guvenilen":k["varsayilan"]!="gecersiz","filigran_kaldi":k["ber"]<esik})
    return {"satirlar":sat,"yalniz_filigran":[s["id"] for s in sat if s["c2pa"]=="yok" and s["filigran_kaldi"]],
            "hicbiri":[s["id"] for s in sat if s["c2pa"]=="yok" and not s["filigran_kaldi"]],
            "imzali_guvenilmeyen":[s["id"] for s in sat if s["c2pa"]=="imzali" and not s["guvenilen"]]}

from ai_savunma_veri import json_yukle
v=json_yukle("veri/c2pa.json")
for esik in v["esikler"]:
    r=kanit_raporu(v["kayitlar"],esik)
    print("eşik",esik,"| yalnız filigran:",r["yalniz_filigran"],"| hiçbiri:",r["hicbiri"],"| imzalı ama güvenilmeyen:",r["imzali_guvenilmeyen"])
    for s in r["satirlar"]:print("   ",s)
```
```test
def sinama3(f):
    import copy
    try:
        def k(i,v,t,b):return {"id":i,"varsayilan":v,"test_kok":t,"ber":b}
        def s(i,c,g,fk):return {"id":i,"c2pa":c,"guvenilen":g,"filigran_kaldi":fk}
        K=[k("b-jpeg","manifest-yok","manifest-yok",0.5),k("a-imza","gecerli-guvenilmeyen","guvenilen",0.0),k("c-png","manifest-yok","manifest-yok",0.1),
           k("d-meta","gecersiz","gecersiz",0.0),k("e-sald","gecerli-guvenilmeyen","gecerli-guvenilmeyen",0.03125),k("f-x","guvenilen","guvenilen",1)]
        e=copy.deepcopy(K);r=f(K,0.1)
        if K!=e:return False
        if r!={"satirlar":[s("a-imza","imzali",True,True),s("b-jpeg","yok",False,False),s("c-png","yok",False,True),s("d-meta","bozuk",False,True),s("e-sald","imzali",False,True),s("f-x","imzali",True,False)],
               "yalniz_filigran":["c-png"],"hicbiri":["b-jpeg"],"imzali_guvenilmeyen":["e-sald"]}:return False
        if f(list(reversed(K)),0.1)!=r:return False
        r0=f(K,0)
        if r0["yalniz_filigran"]!=[] or r0["hicbiri"]!=["b-jpeg","c-png"] or [x["filigran_kaldi"] for x in r0["satirlar"]]!=[True,False,False,True,False,False]:return False
        r1=f(K,1)
        if r1["yalniz_filigran"]!=["b-jpeg","c-png"] or r1["hicbiri"]!=[] or not all(x["filigran_kaldi"] for x in r1["satirlar"]):return False
        T=lambda **d:[dict(K[0],**d)]+K[1:]
        for bad,es in ((K,-0.1),(K,1.5),(K,float("nan")),(K,float("inf")),(T(ber=float("nan")),0.1),(T(ber=float("inf")),0.1),(K,True),(K,"0.1"),(K,None),(None,0.1),([],0.1),(tuple(K),0.1),(K+[K[0]],0.1),(T(id=""),0.1),(T(id=5),0.1),
                       (T(varsayilan="x"),0.1),(T(test_kok=None),0.1),(T(ber=-0.01),0.1),(T(ber=1.01),0.1),(T(ber=True),0.1),(T(ber="0"),0.1),(T(ber=None),0.1),
                       (T(ek=1),0.1),([{x:y for x,y in K[0].items() if x!="ber"}]+K[1:],0.1),([None]+K,0.1)):
            try:f(bad,es);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama3(kanit_raporu),"c2pa sınıfı, güven, eşik sınırı, listeler ve geçersiz girdi")
for ad,mut in [("bozuk imzalı sayılıyor",lambda K,e:dict(kanit_raporu(K,e),imzali_guvenilmeyen=sorted(x["id"] for x in kanit_raporu(K,e)["satirlar"] if x["c2pa"]!="yok" and not x["guvenilen"]))),("eşik katı",lambda K,e:kanit_raporu(K,e-1e-9) if e>0 else kanit_raporu(K,e)),("sırasız",lambda K,e:dict(kanit_raporu(K,e),satirlar=list(reversed(kanit_raporu(K,e)["satirlar"]))))]:
    ok(not sinama3(mut),"mutant reddedildi: "+ad)
# --- carbon-c8-ek-bas ---
_kr37 = {"id": "k1", "varsayilan": "guvenilen", "test_kok": "guvenilen", "ber": 0.1}
raises(ValueError, kanit_raporu, [dict(_kr37, id=123)], 0.2, msg="id str olmalı")
raises(ValueError, kanit_raporu, [dict(_kr37, ber=True)], 0.2, msg="ber bool olamaz")
raises(ValueError, kanit_raporu, [dict(_kr37, ber=float("nan"))], 0.2, msg="NaN ber ret")
raises(ValueError, kanit_raporu, [_kr37], True, msg="eşik bool olamaz")
raises(ValueError, kanit_raporu, [_kr37], float("nan"), msg="NaN eşik ret")
# --- carbon-c8-ek-son ---
```
```solution
def kanit_raporu(kayitlar,esik):
    import math
    durumlar=("manifest-yok","gecersiz","gecerli-guvenilmeyen","guvenilen")
    if type(esik) not in (int,float) or not math.isfinite(esik) or not 0<=esik<=1:raise ValueError("eşik")
    if not isinstance(kayitlar,list) or not kayitlar:raise ValueError("liste")
    ids=set();sat=[]
    for k in kayitlar:
        if not isinstance(k,dict) or set(k)!={"id","varsayilan","test_kok","ber"}:raise ValueError("şema")
        if not isinstance(k["id"],str) or not k["id"] or k["id"] in ids:raise ValueError("id")
        if k["varsayilan"] not in durumlar or k["test_kok"] not in durumlar:raise ValueError("durum")
        if type(k["ber"]) not in (int,float) or not math.isfinite(k["ber"]) or not 0<=k["ber"]<=1:raise ValueError("ber")
        ids.add(k["id"])
        c="yok" if k["varsayilan"]=="manifest-yok" else "bozuk" if k["varsayilan"]=="gecersiz" else "imzali"
        sat.append({"id":k["id"],"c2pa":c,"guvenilen":k["test_kok"]=="guvenilen","filigran_kaldi":k["ber"]<=esik})
    sat.sort(key=lambda s:s["id"])
    return {"satirlar":sat,"yalniz_filigran":[s["id"] for s in sat if s["c2pa"]=="yok" and s["filigran_kaldi"]],
            "hicbiri":[s["id"] for s in sat if s["c2pa"]=="yok" and not s["filigran_kaldi"]],
            "imzali_guvenilmeyen":[s["id"] for s in sat if s["c2pa"]=="imzali" and not s["guvenilen"]]}

from ai_savunma_veri import json_yukle
v=json_yukle("veri/c2pa.json")
for esik in v["esikler"]:
    r=kanit_raporu(v["kayitlar"],esik)
    print("eşik",esik,"| yalnız filigran:",r["yalniz_filigran"],"| hiçbiri:",r["hicbiri"],"| imzalı ama güvenilmeyen:",r["imzali_guvenilmeyen"])
    for s in r["satirlar"]:print("   ",s)
```
```hint
`gecersiz` bir manifest imzalı sayılmaz. Güveni varsayılan okumadan değil, test kök okumasından al.
```
:::

::: anlat Hata vitrini · yazar koşusu
Yazar finaldeki deneyi referans işlevlerle bir kez çalıştırdı; kayıt `outputs/yeni-ai-savunma-37/yazar-sondasi.json` dosyasındadır (c2patool 0.28.4, exe sha256 `9a447201…`).

- **Pikseller aynı, manifest "geçersiz".** `meta_eklendi` dosyasına yalnız bir `tEXt` yorum parçası eklendi; R kanalından okunan filigranın bit hata oranı 0'dı, yani pikseller değişmedi. c2patool yine `assertion.dataHash.mismatch` ile `Invalid` dedi. Hard binding içeriğin değil **baytların** bütünlüğünü korur.
- **Manifest gitti, filigran kaldı.** `png_yeniden` Pillow ile yeniden kaydedildi: c2patool "No claim found" dedi, filigranın bit hata oranı 0 kaldı. `jpeg_q85` ve `olcek_yarim`'da ise ikisi de kayboldu (BER 0.47 ve 0.34).
- **Saldırganın imzası "Valid".** `saldirgan_imzali` dosyası manifesti silinmiş görüntünün altına kırmızı bir şerit çizilip "Haber Ajansi (sahte)" adlı, koşu sırasında üretilmiş bir sertifikayla imzalandı. c2patool `Valid` dedi; tek fark `signingCredential.untrusted` koduydu ve test kökü eklense de değişmedi. Aynı dosyanın filigranı (BER 0) hâlâ asıl kaynağın bitlerini taşıyordu.

Bu sonuçlar neden tek başına güven vermez? `Valid` görmek "doğru kişi imzaladı" demek değildir; "manifest yok" görmek "sahte" demek değildir; filigranın kalması kimin koyduğunu kanıtlamaz. Kendi cümlenle açıkla. Bu kayıt finalin yerine geçmez; final kendi koşusunu ayrıca üretir.
:::

::: anlat Gerçek deney: altı dönüşüm, iki okuma kipi
Final c2patool'un sha256'sını doğrular, geçici bir klasörde sentetik PNG üretir, 32 rastgele biti senin `filigran_gom` işlevinle değil bağımsız referansla gömer (senin çıktın ayrıca karşılaştırılır) ve dosyayı TEST sertifikasıyla imzalar. Ardından altı dosya üretir: `imzali`, `meta_eklendi`, `png_yeniden`, `jpeg_q85`, `olcek_yarim`, `saldirgan_imzali`. Her biri varsayılan ve test kök kipinde okunur (12 gerçek c2patool çağrısı). Kabul, dört işlevinin gerçek çıktılarda referansla birebir aynı sonuç vermesine, test kökünün imzalı dosyayı gerçekten `Trusted` yapmasına, saldırgan imzasının bu koşuda üretilen sertifikayla atılmış olmasına ve imzalı dosyadaki filigranın hatasız okunmasına bağlıdır. JPEG ya da ölçeklemede filigranın kalıp kalmaması **kabul şartı değildir**; bu, ölçülen bir sonuçtur.

**Üretken model filigranı (metin).** LSB filigranı içeriğe sonradan eklenir; üretken modellerde filigran **üretim sırasında** konur. Final SmolLM2-135M ile Kirchenbauer vd. (2023) yöntemini uygular: her adımda önceki tokena ve gizli bir anahtara bağlı bir "yeşil liste" (sözlüğün %25'i) seçilir ve bu tokenların logitine δ = 2 eklenir. Dört istemle 120'şer token filigranlı ve filigransız üretilir. Tespit yalnız tokenlara bakar ve modele ihtiyaç duymaz: yeşil token sayısının beklenen değerden sapması z skoru olarak ölçülür. Filigranlı metinlerde z 7–11, filigransızlarda 0 civarındadır. Tokenların %30'u rastgele değiştirilince z yaklaşık yarıya iner ama tespit eşiğinin üstünde kalır. Bir LLM ile yeniden yazma (parafraz) bundan çok daha güçlü bir saldırıdır; metin filigranı tek başına kaynak kanıtı sayılmamalıdır.

**Kanıt dosyasını oku:** Çalıştır ya da Kontrol Et sonunda kanıt dosyasının yolu yazılır. `okumalar` içinde `meta_eklendi` okumasının `stdout` alanında `failure` listesini bul; hangi kod var? `saldirgan_imzali` için `signature_info` ne diyor? `ber` alanında hangi dönüşümler filigranı bozdu? `rapor.yalniz_filigran` ve `rapor.imzali_guvenilmeyen` ne çıktı? Bir haber sitesinde yalnız "imzalı ✓" rozeti gösterilseydi bu dosyalardan hangisi yanlış güven verirdi? Cevabını tezgâhta yorum olarak yaz; otomatik test bu serbest açıklamayı puanlamaz.
:::

::: gorev Gerçek deney · c2patool ile imza, güven ve filigran
Önceki üç görevin `c2pa_durumu`, `filigran_gom`, `filigran_oku` ve `kanit_raporu` işlevlerini birleştir. Çalıştır gerçek okumaları ve raporunu gösterir; Kontrol Et önce üç sözleşmeyi gizli verilerle sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
timeout: 300
```
```starter
import ai_lab
import json
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def c2pa_durumu(okuma):
    if okuma["rc"]:return {"durum":"gecersiz","hatalar":[],"imzaci":None}
    j=json.loads(okuma["stdout"])
    hata=[f["code"] for f in j.get("validation_results",{}).get("activeManifest",{}).get("failure",[])]
    si=list(j["manifests"].values())[0]["signature_info"]
    durum="gecersiz" if hata else "guvenilen"
    return {"durum":durum,"hatalar":hata,"imzaci":{"issuer":si.get("issuer"),"common_name":si.get("common_name")}}

# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def filigran_gom(degerler,bitler,tekrar):
    y=list(degerler)
    for i,b in enumerate(bitler):
        for r in range(tekrar):y[i*tekrar+r]=y[i*tekrar+r]|b
    return y

# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def filigran_oku(degerler,n,tekrar):
    return [degerler[i*tekrar]&1 for i in range(n)]

# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def kanit_raporu(kayitlar,esik):
    sat=[]
    for k in kayitlar:
        c="yok" if k["varsayilan"]=="manifest-yok" else "imzali"
        sat.append({"id":k["id"],"c2pa":c,"guvenilen":k["varsayilan"]!="gecersiz","filigran_kaldi":k["ber"]<esik})
    return {"satirlar":sat,"yalniz_filigran":[s["id"] for s in sat if s["c2pa"]=="yok" and s["filigran_kaldi"]],
            "hicbiri":[s["id"] for s in sat if s["c2pa"]=="yok" and not s["filigran_kaldi"]],
            "imzali_guvenilmeyen":[s["id"] for s in sat if s["c2pa"]=="imzali" and not s["guvenilen"]]}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_37 as D
    D.goster(c2pa_durumu,filigran_gom,filigran_oku,kanit_raporu)
```
```test
import ai_lab
checks=[]
def kontrol(x,m):checks.append(bool(x));ok(x,m)
issues=ai_lab.kod_denetimi(src,("referans_durum","referans_gom","referans_oku","referans_rapor","kanit_yaz"),izin=())
kontrol(not issues,"kopya/yama/dinamik kod yok: "+str(issues))
if issues:stop()
c2pa_durumu=need("c2pa_durumu");filigran_gom=need("filigran_gom");filigran_oku=need("filigran_oku");kanit_raporu=need("kanit_raporu")
def sinama1(f):
    import json,copy
    try:
        def J(st,fails,si=None,vr=True):
            si={"issuer":"Kok A","common_name":"Imzaci A"} if si is None else si
            j={"active_manifest":"urn:b","manifests":{"urn:a":{"signature_info":{"issuer":"Eski","common_name":"Eski"}},"urn:b":{"signature_info":si}},"validation_state":st}
            if vr:j["validation_results"]={"activeManifest":{"failure":[{"code":c} for c in fails],"success":[{"code":"claimSignature.validated"}]}}
            return {"rc":0,"stdout":json.dumps(j),"stderr":""}
        I={"issuer":"Kok A","common_name":"Imzaci A"}
        U="signingCredential.untrusted";H="assertion.dataHash.mismatch"
        V=[(J("Trusted",[]),{"durum":"guvenilen","hatalar":[],"imzaci":I}),
           (J("Valid",[U]),{"durum":"gecerli-guvenilmeyen","hatalar":[U],"imzaci":I}),
           (J("Invalid",[U,H,H]),{"durum":"gecersiz","hatalar":[H,U],"imzaci":I}),
           (J("Valid",[],vr=False),{"durum":"gecerli-guvenilmeyen","hatalar":[],"imzaci":I}),
           (J("Invalid",[H],si={"issuer":"Sahte Org"}),{"durum":"gecersiz","hatalar":[H],"imzaci":{"issuer":"Sahte Org","common_name":None}}),
           ({"rc":1,"stdout":"","stderr":" Error: No claim found\n"},{"durum":"manifest-yok","hatalar":[],"imzaci":None}),
           ({"rc":2,"stdout":"{}","stderr":"Error: No claim found"},{"durum":"manifest-yok","hatalar":[],"imzaci":None})]
        for o,b in V:
            e=copy.deepcopy(o)
            if f(o)!=b or o!=e:return False
        for bad in (None,[],{"rc":0,"stdout":"{}"},dict(J("Valid",[]),ek=1),dict(J("Valid",[]),rc=True),dict(J("Valid",[]),rc="0"),dict(J("Valid",[]),stdout=None),
                    dict(J("Valid",[]),stderr=5),{"rc":1,"stdout":"","stderr":"Error: file not found"},{"rc":0,"stdout":"değil json","stderr":""},
                    {"rc":0,"stdout":"[]","stderr":""},dict(J("Valid",[]),stdout=J("Valid",[])["stdout"].replace("Valid","Unknown")),
                    {"rc":0,"stdout":json.dumps({"manifests":{}}),"stderr":""}):
            try:f(bad);return False
            except ValueError:pass
        return True
    except Exception:return False
def sinama2(gom,oku):
    import random,copy
    try:
        d=[10,11,12,13,14,15];e=list(d)
        if gom(d,[1,0],3)!=[11,11,13,12,14,14] or d!=e:return False
        if gom([255,0,7,8],[0],1)!=[254,0,7,8] or gom([0,0,0],[1],3)!=[1,1,1] or gom([1,2,3,4,5,6,7],[0,1],3)!=[0,2,2,5,5,7,7]:return False
        if oku([1,1,0,0,0,1],2,3)!=[1,0] or oku([1,0,1,0,1],1,5)!=[1] or oku([0,0,1,1,1],1,5)!=[1] or oku([3,2,2],1,3)!=[0] or oku([2,3,3,9],1,3)!=[1]:return False
        if oku([0],1,1)!=[0] or oku([255],1,1)!=[1] or oku([1,1,0,0,0],1,5)!=[0] or oku([1,1,1,0,0,0,0],1,7)!=[0] or oku([0,255],2,1)!=[0,1]:return False
        rng=random.Random(37)
        for n,t in ((1,1),(5,3),(12,5),(3,7)):
            v=[rng.randrange(256) for _ in range(n*t+rng.randrange(4))];b=[rng.randrange(2) for _ in range(n)];v0=list(v)
            g=gom(v,b,t)
            if v!=v0 or len(g)!=len(v) or g[n*t:]!=v[n*t:] or oku(g,n,t)!=b or any(abs(x-y)>1 for x,y in zip(g,v)):return False
            if t>1:
                k=list(g)
                for i in range(n):k[i*t]^=1
                if oku(k,n,t)!=b:return False
        for args in (([1,2,3],[1],2),([1,2,3],[1],0),([1,2,3],[1],True),([1,2],[1,0],3),([1,2,3],[],1),([256],[1],1),([-1],[1],1),([1.0],[1],1),([True],[1],1),(["1"],[1],1),
                     ([1,2,3],[2],1),([1,2,3],[True],1),([1,2,3],[-1],1),([1,2,3],["1"],1),((1,2,3),[1],1),([1,2,3],(1,),1),([1,2,3],[1],-1),([1,2,3],[1],1.0)):
            try:gom(*args);return False
            except ValueError:pass
        for args in (([1,2,3],0,1),([1,2,3],True,1),([1,2,3],1,2),([1,2,3],1,0),([1,2],1,3),([1,2,3],2,3),([256],1,1),([-1],1,1),([True],1,1),((1,),1,1),([1,2,3],1,1.0),([1,2,3],1.0,1),([1,2,3],-1,1)):
            try:oku(*args);return False
            except ValueError:pass
        return True
    except Exception:return False
def sinama3(f):
    import copy
    try:
        def k(i,v,t,b):return {"id":i,"varsayilan":v,"test_kok":t,"ber":b}
        def s(i,c,g,fk):return {"id":i,"c2pa":c,"guvenilen":g,"filigran_kaldi":fk}
        K=[k("b-jpeg","manifest-yok","manifest-yok",0.5),k("a-imza","gecerli-guvenilmeyen","guvenilen",0.0),k("c-png","manifest-yok","manifest-yok",0.1),
           k("d-meta","gecersiz","gecersiz",0.0),k("e-sald","gecerli-guvenilmeyen","gecerli-guvenilmeyen",0.03125),k("f-x","guvenilen","guvenilen",1)]
        e=copy.deepcopy(K);r=f(K,0.1)
        if K!=e:return False
        if r!={"satirlar":[s("a-imza","imzali",True,True),s("b-jpeg","yok",False,False),s("c-png","yok",False,True),s("d-meta","bozuk",False,True),s("e-sald","imzali",False,True),s("f-x","imzali",True,False)],
               "yalniz_filigran":["c-png"],"hicbiri":["b-jpeg"],"imzali_guvenilmeyen":["e-sald"]}:return False
        if f(list(reversed(K)),0.1)!=r:return False
        r0=f(K,0)
        if r0["yalniz_filigran"]!=[] or r0["hicbiri"]!=["b-jpeg","c-png"] or [x["filigran_kaldi"] for x in r0["satirlar"]]!=[True,False,False,True,False,False]:return False
        r1=f(K,1)
        if r1["yalniz_filigran"]!=["b-jpeg","c-png"] or r1["hicbiri"]!=[] or not all(x["filigran_kaldi"] for x in r1["satirlar"]):return False
        T=lambda **d:[dict(K[0],**d)]+K[1:]
        for bad,es in ((K,-0.1),(K,1.5),(K,float("nan")),(K,float("inf")),(T(ber=float("nan")),0.1),(T(ber=float("inf")),0.1),(K,True),(K,"0.1"),(K,None),(None,0.1),([],0.1),(tuple(K),0.1),(K+[K[0]],0.1),(T(id=""),0.1),(T(id=5),0.1),
                       (T(varsayilan="x"),0.1),(T(test_kok=None),0.1),(T(ber=-0.01),0.1),(T(ber=1.01),0.1),(T(ber=True),0.1),(T(ber="0"),0.1),(T(ber=None),0.1),
                       (T(ek=1),0.1),([{x:y for x,y in K[0].items() if x!="ber"}]+K[1:],0.1),([None]+K,0.1)):
            try:f(bad,es);return False
            except ValueError:pass
        return True
    except Exception:return False
kontrol(sinama1(c2pa_durumu),"durum eşlemesi, aktif manifest, hata kodları")
kontrol(sinama2(filigran_gom,filigran_oku),"LSB gömme, çoğunluk, kapasite")
kontrol(sinama3(kanit_raporu),"c2pa sınıfı, güven, eşik")
import json as _json
for ad,mut in [("hata listesi varsa geçersiz",lambda o:dict(c2pa_durumu(o),durum="gecersiz") if c2pa_durumu(o)["hatalar"] else c2pa_durumu(o)),("manifest yok = geçersiz",lambda o:dict(c2pa_durumu(o),durum="gecersiz") if c2pa_durumu(o)["durum"]=="manifest-yok" else c2pa_durumu(o)),("imzacı ilk manifestten",lambda o:dict(c2pa_durumu(o),imzaci={"issuer":"Eski","common_name":"Eski"}) if o["rc"]==0 and "urn:a" in o["stdout"] else c2pa_durumu(o))]:
    kontrol(not sinama1(mut),"mutant reddedildi: "+ad)
def _or_gom(d,b,t):
    g=filigran_gom(d,b,t)
    return [x|bb for x,bb in zip(d,[b[i//t] if i<len(b)*t else 0 for i in range(len(d))])] if g else g
for ad,g,o in [("OR ile gömme",_or_gom,filigran_oku),("çoğunluk yok",filigran_gom,lambda d,n,t:[d[i*t]&1 for i in range(n)] if filigran_oku(d,n,t) is not None else None),("kalan değerler sıfır",lambda d,b,t:filigran_gom(d,b,t)[:len(b)*t]+[0]*(len(d)-len(b)*t),filigran_oku)]:
    kontrol(not sinama2(g,o),"mutant reddedildi: "+ad)
for ad,mut in [("bozuk imzalı sayılıyor",lambda K,e:dict(kanit_raporu(K,e),imzali_guvenilmeyen=sorted(x["id"] for x in kanit_raporu(K,e)["satirlar"] if x["c2pa"]!="yok" and not x["guvenilen"]))),("eşik katı",lambda K,e:kanit_raporu(K,e-1e-9) if e>0 else kanit_raporu(K,e)),("sırasız",lambda K,e:dict(kanit_raporu(K,e),satirlar=list(reversed(kanit_raporu(K,e)["satirlar"]))))]:
    kontrol(not sinama3(mut),"mutant reddedildi: "+ad)
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
    c2pa_durumu = need('c2pa_durumu')
    filigran_gom = need('filigran_gom')
    filigran_oku = need('filigran_oku')
    kanit_raporu = need('kanit_raporu')
    def _birim_adim_1():
        def sinama1(f):
            import json,copy
            try:
                def J(st,fails,si=None,vr=True):
                    si={"issuer":"Kok A","common_name":"Imzaci A"} if si is None else si
                    j={"active_manifest":"urn:b","manifests":{"urn:a":{"signature_info":{"issuer":"Eski","common_name":"Eski"}},"urn:b":{"signature_info":si}},"validation_state":st}
                    if vr:j["validation_results"]={"activeManifest":{"failure":[{"code":c} for c in fails],"success":[{"code":"claimSignature.validated"}]}}
                    return {"rc":0,"stdout":json.dumps(j),"stderr":""}
                I={"issuer":"Kok A","common_name":"Imzaci A"}
                U="signingCredential.untrusted";H="assertion.dataHash.mismatch"
                V=[(J("Trusted",[]),{"durum":"guvenilen","hatalar":[],"imzaci":I}),
                   (J("Valid",[U]),{"durum":"gecerli-guvenilmeyen","hatalar":[U],"imzaci":I}),
                   (J("Invalid",[U,H,H]),{"durum":"gecersiz","hatalar":[H,U],"imzaci":I}),
                   (J("Valid",[],vr=False),{"durum":"gecerli-guvenilmeyen","hatalar":[],"imzaci":I}),
                   (J("Invalid",[H],si={"issuer":"Sahte Org"}),{"durum":"gecersiz","hatalar":[H],"imzaci":{"issuer":"Sahte Org","common_name":None}}),
                   ({"rc":1,"stdout":"","stderr":" Error: No claim found\n"},{"durum":"manifest-yok","hatalar":[],"imzaci":None}),
                   ({"rc":2,"stdout":"{}","stderr":"Error: No claim found"},{"durum":"manifest-yok","hatalar":[],"imzaci":None})]
                for o,b in V:
                    e=copy.deepcopy(o)
                    if f(o)!=b or o!=e:return False
                for bad in (None,[],{"rc":0,"stdout":"{}"},dict(J("Valid",[]),ek=1),dict(J("Valid",[]),rc=True),dict(J("Valid",[]),rc="0"),dict(J("Valid",[]),stdout=None),
                            dict(J("Valid",[]),stderr=5),{"rc":1,"stdout":"","stderr":"Error: file not found"},{"rc":0,"stdout":"değil json","stderr":""},
                            {"rc":0,"stdout":"[]","stderr":""},dict(J("Valid",[]),stdout=J("Valid",[])["stdout"].replace("Valid","Unknown")),
                            {"rc":0,"stdout":json.dumps({"manifests":{}}),"stderr":""}):
                    try:f(bad);return False
                    except ValueError:pass
                return True
            except Exception:return False
        ok(sinama1(c2pa_durumu),"durum eşlemesi, aktif manifest, hata kodları, manifest yok ve geçersiz girdi")
        import json as _json
        for ad,mut in [("hata listesi varsa geçersiz",lambda o:dict(c2pa_durumu(o),durum="gecersiz") if c2pa_durumu(o)["hatalar"] else c2pa_durumu(o)),("manifest yok = geçersiz",lambda o:dict(c2pa_durumu(o),durum="gecersiz") if c2pa_durumu(o)["durum"]=="manifest-yok" else c2pa_durumu(o)),("imzacı ilk manifestten",lambda o:dict(c2pa_durumu(o),imzaci={"issuer":"Eski","common_name":"Eski"}) if o["rc"]==0 and "urn:a" in o["stdout"] else c2pa_durumu(o))]:
            ok(not sinama1(mut),"mutant reddedildi: "+ad)
        raises(ValueError, c2pa_durumu, {"rc": 0.0, "stdout": "{}", "stderr": ""}, msg="rc int olmalı")
        raises(ValueError, c2pa_durumu, {"rc": True, "stdout": "{}", "stderr": ""}, msg="rc bool olamaz")
        raises(ValueError, c2pa_durumu, {"rc": 0, "stdout": 123, "stderr": ""}, msg="stdout str olmalı")
        raises(ValueError, c2pa_durumu, {"rc": 0, "stdout": "{}", "stderr": 123}, msg="stderr str olmalı")
        _ok_json37 = '{"active_manifest":"m","manifests":{"m":{"signature_info":{"issuer":"A","common_name":"B"}}},"validation_state":"Trusted"}'
        raises(ValueError, c2pa_durumu, {"rc": False, "stdout": _ok_json37, "stderr": ""}, msg="rc bool False reddedilmeli")
        raises(ValueError, c2pa_durumu, {"rc": 1, "stdout": _ok_json37, "stderr": "Error: io"}, msg="sıfır dışı rc geçerli stdout olsa da reddedilmeli")
    try:
        _birim_adim_1()
    except Exception:
        _u.append(False)
    def _birim_adim_2():
        def sinama2(gom,oku):
            import random,copy
            try:
                d=[10,11,12,13,14,15];e=list(d)
                if gom(d,[1,0],3)!=[11,11,13,12,14,14] or d!=e:return False
                if gom([255,0,7,8],[0],1)!=[254,0,7,8] or gom([0,0,0],[1],3)!=[1,1,1] or gom([1,2,3,4,5,6,7],[0,1],3)!=[0,2,2,5,5,7,7]:return False
                if oku([1,1,0,0,0,1],2,3)!=[1,0] or oku([1,0,1,0,1],1,5)!=[1] or oku([0,0,1,1,1],1,5)!=[1] or oku([3,2,2],1,3)!=[0] or oku([2,3,3,9],1,3)!=[1]:return False
                if oku([0],1,1)!=[0] or oku([255],1,1)!=[1] or oku([1,1,0,0,0],1,5)!=[0] or oku([1,1,1,0,0,0,0],1,7)!=[0] or oku([0,255],2,1)!=[0,1]:return False
                rng=random.Random(37)
                for n,t in ((1,1),(5,3),(12,5),(3,7)):
                    v=[rng.randrange(256) for _ in range(n*t+rng.randrange(4))];b=[rng.randrange(2) for _ in range(n)];v0=list(v)
                    g=gom(v,b,t)
                    if v!=v0 or len(g)!=len(v) or g[n*t:]!=v[n*t:] or oku(g,n,t)!=b or any(abs(x-y)>1 for x,y in zip(g,v)):return False
                    if t>1:
                        k=list(g)
                        for i in range(n):k[i*t]^=1
                        if oku(k,n,t)!=b:return False
                for args in (([1,2,3],[1],2),([1,2,3],[1],0),([1,2,3],[1],True),([1,2],[1,0],3),([1,2,3],[],1),([256],[1],1),([-1],[1],1),([1.0],[1],1),([True],[1],1),(["1"],[1],1),
                             ([1,2,3],[2],1),([1,2,3],[True],1),([1,2,3],[-1],1),([1,2,3],["1"],1),((1,2,3),[1],1),([1,2,3],(1,),1),([1,2,3],[1],-1),([1,2,3],[1],1.0)):
                    try:gom(*args);return False
                    except ValueError:pass
                for args in (([1,2,3],0,1),([1,2,3],True,1),([1,2,3],1,2),([1,2,3],1,0),([1,2],1,3),([1,2,3],2,3),([256],1,1),([-1],1,1),([True],1,1),((1,),1,1),([1,2,3],1,1.0),([1,2,3],1.0,1),([1,2,3],-1,1)):
                    try:oku(*args);return False
                    except ValueError:pass
                return True
            except Exception:return False
        ok(sinama2(filigran_gom,filigran_oku),"LSB gömme, çoğunluk oylaması, kapasite ve geçersiz girdi")
        def _or_gom(d,b,t):
            g=filigran_gom(d,b,t)
            return [x|bb for x,bb in zip(d,[b[i//t] if i<len(b)*t else 0 for i in range(len(d))])] if g else g
        for ad,g,o in [("OR ile gömme",_or_gom,filigran_oku),("çoğunluk yok",filigran_gom,lambda d,n,t:[d[i*t]&1 for i in range(n)] if filigran_oku(d,n,t) is not None else None),("kalan değerler sıfır",lambda d,b,t:filigran_gom(d,b,t)[:len(b)*t]+[0]*(len(d)-len(b)*t),filigran_oku)]:
            ok(not sinama2(g,o),"mutant reddedildi: "+ad)
        raises(ValueError, filigran_gom, [1, 2, 3], [True], 3, msg="bit bool olamaz")
        raises(ValueError, filigran_gom, [True, 2, 3], [1], 3, msg="değer bool olamaz")
        raises(ValueError, filigran_oku, [1, 2, 3], True, 3, msg="n bool olamaz")
        raises(ValueError, filigran_oku, [1, 2, 3], 1, -3, msg="negatif tek tekrar reddedilmeli")
        raises(ValueError, filigran_oku, [True, 2, 3], 1, 3, msg="filigran_oku değer bool olamaz")
    try:
        _birim_adim_2()
    except Exception:
        _u.append(False)
    def _birim_adim_3():
        def sinama3(f):
            import copy
            try:
                def k(i,v,t,b):return {"id":i,"varsayilan":v,"test_kok":t,"ber":b}
                def s(i,c,g,fk):return {"id":i,"c2pa":c,"guvenilen":g,"filigran_kaldi":fk}
                K=[k("b-jpeg","manifest-yok","manifest-yok",0.5),k("a-imza","gecerli-guvenilmeyen","guvenilen",0.0),k("c-png","manifest-yok","manifest-yok",0.1),
                   k("d-meta","gecersiz","gecersiz",0.0),k("e-sald","gecerli-guvenilmeyen","gecerli-guvenilmeyen",0.03125),k("f-x","guvenilen","guvenilen",1)]
                e=copy.deepcopy(K);r=f(K,0.1)
                if K!=e:return False
                if r!={"satirlar":[s("a-imza","imzali",True,True),s("b-jpeg","yok",False,False),s("c-png","yok",False,True),s("d-meta","bozuk",False,True),s("e-sald","imzali",False,True),s("f-x","imzali",True,False)],
                       "yalniz_filigran":["c-png"],"hicbiri":["b-jpeg"],"imzali_guvenilmeyen":["e-sald"]}:return False
                if f(list(reversed(K)),0.1)!=r:return False
                r0=f(K,0)
                if r0["yalniz_filigran"]!=[] or r0["hicbiri"]!=["b-jpeg","c-png"] or [x["filigran_kaldi"] for x in r0["satirlar"]]!=[True,False,False,True,False,False]:return False
                r1=f(K,1)
                if r1["yalniz_filigran"]!=["b-jpeg","c-png"] or r1["hicbiri"]!=[] or not all(x["filigran_kaldi"] for x in r1["satirlar"]):return False
                T=lambda **d:[dict(K[0],**d)]+K[1:]
                for bad,es in ((K,-0.1),(K,1.5),(K,float("nan")),(K,float("inf")),(T(ber=float("nan")),0.1),(T(ber=float("inf")),0.1),(K,True),(K,"0.1"),(K,None),(None,0.1),([],0.1),(tuple(K),0.1),(K+[K[0]],0.1),(T(id=""),0.1),(T(id=5),0.1),
                               (T(varsayilan="x"),0.1),(T(test_kok=None),0.1),(T(ber=-0.01),0.1),(T(ber=1.01),0.1),(T(ber=True),0.1),(T(ber="0"),0.1),(T(ber=None),0.1),
                               (T(ek=1),0.1),([{x:y for x,y in K[0].items() if x!="ber"}]+K[1:],0.1),([None]+K,0.1)):
                    try:f(bad,es);return False
                    except ValueError:pass
                return True
            except Exception:return False
        ok(sinama3(kanit_raporu),"c2pa sınıfı, güven, eşik sınırı, listeler ve geçersiz girdi")
        for ad,mut in [("bozuk imzalı sayılıyor",lambda K,e:dict(kanit_raporu(K,e),imzali_guvenilmeyen=sorted(x["id"] for x in kanit_raporu(K,e)["satirlar"] if x["c2pa"]!="yok" and not x["guvenilen"]))),("eşik katı",lambda K,e:kanit_raporu(K,e-1e-9) if e>0 else kanit_raporu(K,e)),("sırasız",lambda K,e:dict(kanit_raporu(K,e),satirlar=list(reversed(kanit_raporu(K,e)["satirlar"]))))]:
            ok(not sinama3(mut),"mutant reddedildi: "+ad)
        _kr37 = {"id": "k1", "varsayilan": "guvenilen", "test_kok": "guvenilen", "ber": 0.1}
        raises(ValueError, kanit_raporu, [dict(_kr37, id=123)], 0.2, msg="id str olmalı")
        raises(ValueError, kanit_raporu, [dict(_kr37, ber=True)], 0.2, msg="ber bool olamaz")
        raises(ValueError, kanit_raporu, [dict(_kr37, ber=float("nan"))], 0.2, msg="NaN ber ret")
        raises(ValueError, kanit_raporu, [_kr37], True, msg="eşik bool olamaz")
        raises(ValueError, kanit_raporu, [_kr37], float("nan"), msg="NaN eşik ret")
    try:
        _birim_adim_3()
    except Exception:
        _u.append(False)
    return bool(_u) and all(_u)
kontrol(_c8_birim_denetimi(), "deney öncesi tam birim sözleşmesi korunmalı")
# --- carbon-c8-g4-son ---
if not all(checks):stop()
from sandbox import ai_gercek_ai_savunma_37 as D
try:r=D.deney(c2pa_durumu,filigran_gom,filigran_oku,kanit_raporu)
except ai_lab.GercekLabYok as e:
    kontrol(False,"gerçek deney yok: "+str(e));stop()
kontrol(r["durum"]==r["durum_referans"],"12 gerçek c2patool okumasının sınıflandırması referansla aynı")
kontrol(r["gom"]==r["gom_referans"],"gerçek görüntüye gömülen filigran referansla aynı")
kontrol(r["oku"]==r["oku_referans"],"altı dönüşümde okunan bitler referansla aynı")
kontrol(r["rapor"]==r["rapor_referans"],"gerçek kanıt raporu referansla aynı")
O=r["okumalar"];DR={(o["id"],o["kip"]):d for o,d in zip(O,r["durum_referans"])}
kontrol(r["arac"]["surum"]=="c2patool 0.28.4" and len(O)==12 and len(set(r["dosya_sha256"].values()))==6,"onaylı araç sürümü, 6 dönüşüm × 2 kip, 6 farklı dosya")
kontrol(DR[("imzali","varsayilan")]["durum"]=="gecerli-guvenilmeyen" and DR[("imzali","test_kok")]["durum"]=="guvenilen","güven kökü gerçekten uygulandı: aynı dosya varsayılanda güvenilmeyen, test kökle güvenilen")
kontrol(DR[("saldirgan_imzali","varsayilan")]["imzaci"]=={"issuer":"Sahte Org","common_name":"Haber Ajansi (sahte)"},"saldırgan imzası gerçekten bu koşuda üretilen sertifikayla atıldı")
kontrol(len(r["bitler"])==32 and r["ber"]["imzali"]==0,"32 rastgele bit gömüldü ve imzalı dosyadan hatasız okundu")
kontrol(r["metin_filigrani_dayanikli"],"SmolLM2 yeşil liste filigranı: filigranlı metin z ≥ 4, filigransız |z| ≤ 2.5, %%30 bozulmuş metin hâlâ z ≥ 2.5 (ortalamalar %.1f / %.1f / %.1f)"%(r["metin_filigrani"]["z_ortalama"]["filigranli"],r["metin_filigrani"]["z_ortalama"]["filigransiz"],r["metin_filigrani"]["z_ortalama"]["bozulmus"]))
ai_lab.kanit_yaz("savunma37-kabul",{"kaynak":"gercek","kabul":all(checks),"ders":"ai-savunma-37","deney":r})
```
```solution
import ai_lab
import json
def c2pa_durumu(okuma):
    esle={"Trusted":"guvenilen","Valid":"gecerli-guvenilmeyen","Invalid":"gecersiz"}
    if not isinstance(okuma,dict) or set(okuma)!={"rc","stdout","stderr"}:raise ValueError("şema")
    if type(okuma["rc"]) is not int or not isinstance(okuma["stdout"],str) or not isinstance(okuma["stderr"],str):raise ValueError("alan")
    if okuma["rc"]:
        if "No claim found" in okuma["stderr"]:return {"durum":"manifest-yok","hatalar":[],"imzaci":None}
        raise ValueError("araç hatası")
    j=json.loads(okuma["stdout"])
    if not isinstance(j,dict) or j.get("validation_state") not in esle:raise ValueError("durum")
    si=j["manifests"][j["active_manifest"]]["signature_info"]
    hata=sorted({f["code"] for f in j.get("validation_results",{}).get("activeManifest",{}).get("failure",[])})
    return {"durum":esle[j["validation_state"]],"hatalar":hata,"imzaci":{"issuer":si.get("issuer"),"common_name":si.get("common_name")}}

def filigran_gom(degerler,bitler,tekrar):
    if not isinstance(bitler,list) or any(type(b) is not int or b not in (0,1) for b in bitler):raise ValueError("bitler")
    if not isinstance(degerler,list) or any(type(v) is not int or not 0<=v<=255 for v in degerler):raise ValueError("değerler")
    if type(tekrar) is not int or tekrar<1 or tekrar%2==0 or not bitler or len(bitler)*tekrar>len(degerler):raise ValueError("tekrar/kapasite")
    y=list(degerler)
    for i,b in enumerate(bitler):
        for r in range(tekrar):y[i*tekrar+r]=(y[i*tekrar+r]&254)|b
    return y

def filigran_oku(degerler,n,tekrar):
    if not isinstance(degerler,list) or any(type(v) is not int or not 0<=v<=255 for v in degerler):raise ValueError("değerler")
    if type(n) is not int or n<1 or type(tekrar) is not int or tekrar<1 or tekrar%2==0 or n*tekrar>len(degerler):raise ValueError("n/tekrar/kapasite")
    return [int(sum(degerler[i*tekrar+r]&1 for r in range(tekrar))*2>tekrar) for i in range(n)]

def kanit_raporu(kayitlar,esik):
    import math
    durumlar=("manifest-yok","gecersiz","gecerli-guvenilmeyen","guvenilen")
    if type(esik) not in (int,float) or not math.isfinite(esik) or not 0<=esik<=1:raise ValueError("eşik")
    if not isinstance(kayitlar,list) or not kayitlar:raise ValueError("liste")
    ids=set();sat=[]
    for k in kayitlar:
        if not isinstance(k,dict) or set(k)!={"id","varsayilan","test_kok","ber"}:raise ValueError("şema")
        if not isinstance(k["id"],str) or not k["id"] or k["id"] in ids:raise ValueError("id")
        if k["varsayilan"] not in durumlar or k["test_kok"] not in durumlar:raise ValueError("durum")
        if type(k["ber"]) not in (int,float) or not math.isfinite(k["ber"]) or not 0<=k["ber"]<=1:raise ValueError("ber")
        ids.add(k["id"])
        c="yok" if k["varsayilan"]=="manifest-yok" else "bozuk" if k["varsayilan"]=="gecersiz" else "imzali"
        sat.append({"id":k["id"],"c2pa":c,"guvenilen":k["test_kok"]=="guvenilen","filigran_kaldi":k["ber"]<=esik})
    sat.sort(key=lambda s:s["id"])
    return {"satirlar":sat,"yalniz_filigran":[s["id"] for s in sat if s["c2pa"]=="yok" and s["filigran_kaldi"]],
            "hicbiri":[s["id"] for s in sat if s["c2pa"]=="yok" and not s["filigran_kaldi"]],
            "imzali_guvenilmeyen":[s["id"] for s in sat if s["c2pa"]=="imzali" and not s["guvenilen"]]}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_37 as D
    D.goster(c2pa_durumu,filigran_gom,filigran_oku,kanit_raporu)
```
```hint
Dört işlevi aynen birleştir. Raporu okurken `Valid` ile `Trusted`'ı ve "manifest yok" ile "geçersiz"i karıştırma.
```
:::

::: anlat Sınır
Bu ders tek bir sentetik PNG, c2patool 0.28.4, örnek TEST sertifikaları ve yerel bir saldırgan sertifikasıyla C2PA bütünlüğünü, imzacı güvenini ve basit bir LSB filigranının beş dönüşümdeki davranışını ölçer; üretim güven listesini, gerçek kamera ya da yayıncı imzalarını, başka dosya türlerini ve dayanıklı ticari ya da üretken model filigranlarını göstermez.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
### İmza ile dayanıklı filigran farklı koşullarda yaşar

C2PA doğrulaması manifest ve imzalanmış içerik ilişkisini inceler; güven kökü ayrı karardır. LSB filigranı piksel bitlerine gömülüdür ve yeniden kodlama veya gürültüyle bozulabilir. Dönüşüm sonrası hangisinin kaldığı ayrı ölçülür. Manifestin yokluğu görselin sahte olduğunun kanıtı değildir; imza varlığı da sahnenin gerçekliğini garanti etmez.

| Yaygın yanlış | Mekanizmanın sınırı |
|---|---|
| Kaynak kanıtı sahnenin doğruluğudur | Dosya kökeni ile görüntünün iddiası ayrı değerlendirilir. |

Saldırı–savunma bağlantısı: ai-saldiri-53.
:::
