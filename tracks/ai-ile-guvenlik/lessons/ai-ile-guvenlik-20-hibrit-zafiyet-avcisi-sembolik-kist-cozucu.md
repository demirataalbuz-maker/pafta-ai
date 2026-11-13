---
id: ai-ile-guvenlik-20
title: Hibrit Zafiyet Avcısı · Fuzzing ve Sembolik Kısıt Çözücü
summary: Dal kısıtlarını (path conditions) değerlendir, sembolik aralık daraltma ile sihirli başlık (magic-byte) engellerini çöz ve rastgele fuzzing ile hibrit çözücüyü gerçek hedef programlarda karşılaştır.
esleme: ai-ile-guvenlik-06, ai-ile-guvenlik-08, ai-ile-guvenlik-18
timeout: 300
---

::: anlat Rastgele fuzzer neden tek bir `if (magic == 0xBEEF)` satırında takılır?
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Kapsam güdümlü (`coverage-guided`) bir fuzzer sığ dalları hızla keşfeder, ancak dar `magic-byte` ve çoklu aralık kısıtlarında (`path condition`) `symbolic execution` veya LLM destekli `constraint solver` olmadan takılır | İlk üç görev: `veri/sembolik_avci.json` içindeki **sentetik** dal kısıtları ve aday girdiler. Final: 12 gerçek hedef programda (sınır dışı yazma hatalı paket ayrıştırıcısı) 4096 bütçeli kör ve kapsam güdümlü fuzzer ile kaynak koddan çıkarılan yol koşullarını çözen hibrit yaklaşımın karşılaştırması; tetikleyiciler gerçek programda doğrulanır | Kriptografik özetlerin (`SHA-256`) veya karmaşık yığın (`heap`) durum makinelerinin basit aralık daraltmayla çözülebileceğini söyleyemez |
| Çözücünün ürettiği her aday girdi yürütücü (`executor`) tarafından gerçek kısıt listesinde doğrulanmalıdır | `dal_kisiti_degerlendir`, `sembolik_aralik_daralt` ve `hibrit_tetikleyici_bul` | Yol patlaması (`path explosion`) yaşayan milyonlarca dallı ikili dosyada hangi dalın seçileceğini tek başına belirlemez |

> [!NOT]
> Görevler `veri/sembolik_avci.json` dosyasını okur; dosya sentetiktir. Setup her Çalıştır/Kontrol Et adımında geçici kopya kurar; değişiklikler taşınmaz, **kalıcılık yoktur**. Ekranda ayrı dosya görüntüleyici yoktur; içeriği görmek için `print` kullan. Gizli testler ayrıdır. Final yeni model indirmez; hedef programları CPU'da ve varsa yerel Ollama modelini kullanarak çalıştırır.

DARPA AIxCC (`AI Cyber Challenge`) mimarilerinde ve Driller (Stephens vd. 2016) gibi hibrit zafiyet avcılarında temel gözlem şudur: mutasyon tabanlı `fuzzing` ucuzdur ve geniş durum uzaylarını saniyede binlerce kez tarar; ancak kodun içinde:
```
if (sihirli_baslik == 48879 && paket_boyutu > 1024 && paket_boyutu <= 1040 && bayrak == 7)
```
gibi dar bir kapı (`narrow branch` / `magic-byte check`) varsa, `[0, 65535]` aralığından rastgele seçilen üç değişkenin bu koşulu aynı anda tutturma olasılığı yaklaşık $3.6 \times 10^{-13}$'tür.

**Yürütücü doğrulaması (`dal_kisiti_degerlendir`).** Ne fuzzer'a ne de LLM/çözücü önerisine körü körüne güvenilir. Bir aday girdi sözlüğü verildiğinde kısıtlar sırayla çalıştırılır; kaç kısıtın geçildiği (`gecen_sayisi`) ve ilk hangi kısıtta (`ilk_engel_indisi`) takılındığı kaydedilir. `ilk_engel_indisi`, hibrit ajanın tam olarak hangi dal koşulunu çözmesi gerektiğini gösterir.

**Sembolik aralık daraltma (`sembolik_aralik_daralt`).** Her değişken başlangıçta $[L_0, U_0]$ aralığındadır. Yol üzerindeki her kısıt bu aralığı daraltır:
- `x == c` $\implies [\max(L, c), \min(U, c)]$
- `x >= c` $\implies [\max(L, c), U]$ ve `x > c` $\implies [\max(L, c+1), U]$
- `x <= c` $\implies [L, \min(U, c)]$ ve `x < c` $\implies [L, \min(U, c-1)]$

Bütün kısıtlar işlendiğinde her değişken için $L \le U$ ise dal **çözülebilirdir** (`satisfiable` / `cozulebilir=True`) ve $\lfloor(L+U)/2\rfloor$ somut bir tetikleyici girdi verir. Herhangi bir değişkende $L > U$ oluşursa o dal **ölü koddur** (`unsatisfiable`).

**Saldırgan / Avcı ne dener?** Önce ucuz rastgele adaylarla (`fuzzer`) dalı geçmeyi dener; takıldığı noktada `path condition` listesini sembolik çözücüye devreder ve üretilen somut girdiyi tekrar `dal_kisiti_degerlendir` ile doğrulayarak zafiyeti tetikler.

**Savunma / Otomasyon neden kırılır?** LLM tabanlı bir ajan kısıtları yanlış çevirip `>` yerine `>=` yazarsa sınır değerinde (`off-by-one`) ürettiği girdi gerçek yürütücüde reddedilir. Bu yüzden `hibrit_tetikleyici_bul` çözücünün çıktısını bile yürütücüde tekrar sınamadan `basarili=True` demez.

**Görev 1'de sık tuzaklar:** Birden fazla kısıt yanlış olduğunda `ilk_engel_indisi` son yanlış kısıtı değil, **ilk** yanlış kısıtın indisini tutmalıdır.

Kaynaklar: [Stephens vd. 2016 — Driller: Augmenting Fuzzing Through Selective Symbolic Execution](https://www.ndss-symposium.org/ndss2016/ndss-2016-programme/driller-augmenting-fuzzing-through-selective-symbolic-execution/), [Cadar vd. 2008 — KLEE](https://llvm.org/pubs/2008-12-OSDI-KLEE.pdf), [Meng vd. 2024 — Large Language Model guided Protocol Fuzzing](https://www.ndss-symposium.org/ndss-paper/large-language-model-guided-protocol-fuzzing/). Bu dersteki bütün sayılar yalnız yerel kanıttan gelir.

Köprü: ai-ile-guvenlik-08 akıllı yük üretimini ve kapsam kilidini kurar; ai-ile-guvenlik-18 güvenlik ajanını değerlendirir; bu ders ise fuzzer'ın takıldığı dar dalları sembolik kısıt çözümüyle aşan hibrit mimariyi tamamlar.
:::

::: tahmin Sıkı eşitsizlik (`>`) tam sayı aralığını nasıl daraltır?
Çıktıyı tahmin et, sonra Çalıştır ile karşılaştır.
```python
alt, ust = 0, 65535
for op, deger in [(">", 1024), ("<=", 1040)]:
    if op == ">":
        alt = max(alt, deger + 1)
    elif op == "<=":
        ust = min(ust, deger)
print([alt, ust], (alt + ust) // 2)
```
???
```cikti
[1025, 1040] 1032
```
Tahmininle gerçek çıktı arasındaki farkı tezgâhta yorum satırı olarak yaz: `paket_boyutu > 1024` kısıtında alt sınır neden `1024` değil de `1025` oldu? Sonra üç kusurlu başlangıç kodunu çalıştır ve her birinin neyi kaçırdığını önce kendin teşhis et; açıklama çözümün ardından gelir.
:::

::: gorev 1 · Dal kısıtı değerlendirici (`dal_kisiti_degerlendir`)
`dal_kisiti_degerlendir(kisitlar,aday_girdi)`: `kisitlar` en az 1 elemanlı sözlük listesi (`{"degisken": dolu str, "op": ("==","!=",">=","<=",">","<"), "deger": bool olmayan int}`); `aday_girdi` boş olmayan `str -> bool olmayan int` sözlüğü ve tüm kısıt değişkenlerini içerir. Sırayla değerlendirip `{"gecen_sayisi":..., "toplam_kisit":..., "ilk_engel_indisi": ilk yanlış indis veya None, "tam_cozum": bool}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-20")
```
```starter
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def dal_kisiti_degerlendir(kisitlar,aday_girdi):
    gecen=0;engel=None
    for i,k in enumerate(kisitlar):
        if aday_girdi[k["degisken"]]==k["deger"]:gecen+=1
        else:engel=i
    return {"gecen_sayisi":gecen,"toplam_kisit":len(kisitlar),"ilk_engel_indisi":engel,"tam_cozum":gecen==len(kisitlar)}

from ai_ile_guvenlik_veri import json_yukle
v=json_yukle("veri/sembolik_avci.json")
kl=v["kisit_listesi"][v["hedef_dal"]]
for a in v["rastgele_adaylar"]:
    print(a,dal_kisiti_degerlendir(kl,a))
```
```test
def sinama1(f):
    import copy
    try:
        kl=[{"degisken":"x","op":"==","deger":10},{"degisken":"y","op":">","deger":5},{"degisken":"z","op":"!=","deger":0}]
        ad={"x":10,"y":6,"z":1};old=(copy.deepcopy(kl),dict(ad))
        if f(kl,ad)!={"gecen_sayisi":3,"toplam_kisit":3,"ilk_engel_indisi":None,"tam_cozum":True} or (kl,ad)!=old:return False
        if f(kl,{"x":10,"y":5,"z":0})!={"gecen_sayisi":1,"toplam_kisit":3,"ilk_engel_indisi":1,"tam_cozum":False}:return False
        kl2=[{"degisken":"a","op":">=","deger":3},{"degisken":"a","op":"<=","deger":5},{"degisken":"a","op":"<","deger":5}]
        if f(kl2,{"a":5})!={"gecen_sayisi":2,"toplam_kisit":3,"ilk_engel_indisi":2,"tam_cozum":False}:return False
        if f(kl2,{"a":3})!={"gecen_sayisi":3,"toplam_kisit":3,"ilk_engel_indisi":None,"tam_cozum":True}:return False
        for bad in ((None,ad),(kl,None),([],ad),(kl,{}),([{"degisken":"x","op":"==","deger":10}],{"y":10}),([{"degisken":"x","op":"~","deger":10}],ad),([{"degisken":"x","op":"==","deger":True}],ad),(kl,{"x":True,"y":6,"z":1}),([{"degisken":"","op":"==","deger":10}],ad)):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama1(dal_kisiti_degerlendir),"altı karşılaştırma operatörü, ilk engel indisi ve geçersiz girdi")
for ad,mut in [("son engel indisi",lambda kl,a:dict(dal_kisiti_degerlendir(kl,a),ilk_engel_indisi=len(kl)-1 if not dal_kisiti_degerlendir(kl,a)["tam_cozum"] else None)),("hep tam çözüm",lambda kl,a:dict(dal_kisiti_degerlendir(kl,a),tam_cozum=True)),("gecen sıfır",lambda kl,a:dict(dal_kisiti_degerlendir(kl,a),gecen_sayisi=0))]:
    ok(not sinama1(mut),"mutant reddedildi: "+ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(dal_kisiti_degerlendir, _il.import_module('ai_gercek_ai_ile_guvenlik_20').referans_degerlendir, ([{'degisken': 'sihirli_baslik', 'op': '==', 'deger': 48879}, {'degisken': 'paket_boyutu', 'op': '>', 'deger': 1024}, {'degisken': 'paket_boyutu', 'op': '<=', 'deger': 1040}, {'degisken': 'bayrak', 'op': '==', 'deger': 7}], {'sihirli_baslik': 1204, 'paket_boyutu': 512, 'bayrak': 1}), tohum=3923)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
# hedefli tablo: dal_kisiti_degerlendir her operatör ve sınır
_R20 = _il.import_module("ai_gercek_ai_ile_guvenlik_20")
_ek = tuple(([{"degisken": "a", "op": o, "deger": 5}, {"degisken": "b", "op": "==", "deger": 1}], {"a": x, "b": 1}) for o in ("==", "!=", ">=", "<=", ">", "<") for x in (4, 5, 6))
_t, _g = _ff(dal_kisiti_degerlendir, _R20.referans_degerlendir, _ek[0], en_cok=0, ekler=_ek)
ok(_t, "her operatör (==, !=, >=, <=, >, <) için x<val, x=val, x>val sınırları referansla aynı" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
def dal_kisiti_degerlendir(kisitlar,aday_girdi):
    if not isinstance(kisitlar,list) or not kisitlar or not isinstance(aday_girdi,dict) or not aday_girdi:raise ValueError("girdi")
    for k,v in aday_girdi.items():
        if not isinstance(k,str) or not k.strip() or isinstance(v,bool) or not isinstance(v,int):raise ValueError("aday")
    ops=("==","!=",">=","<=",">","<")
    gecen=0;engel=None
    for i,k in enumerate(kisitlar):
        if not isinstance(k,dict) or set(k)!={"degisken","op","deger"}:raise ValueError("şema")
        d,op,val=k["degisken"],k["op"],k["deger"]
        if not isinstance(d,str) or not d.strip() or op not in ops or isinstance(val,bool) or not isinstance(val,int) or d not in aday_girdi:raise ValueError("kisit")
        x=aday_girdi[d]
        ok_mu=(x==val if op=="==" else x!=val if op=="!=" else x>=val if op==">=" else x<=val if op=="<=" else x>val if op==">" else x<val)
        if ok_mu:gecen+=1
        elif engel is None:engel=i
    return {"gecen_sayisi":gecen,"toplam_kisit":len(kisitlar),"ilk_engel_indisi":engel,"tam_cozum":gecen==len(kisitlar)}

from ai_ile_guvenlik_veri import json_yukle
v=json_yukle("veri/sembolik_avci.json")
kl=v["kisit_listesi"][v["hedef_dal"]]
for a in v["rastgele_adaylar"]:
    print(a,dal_kisiti_degerlendir(kl,a))
```
```hint
Her kısıtın operatörünü (`==`, `!=`, `>=`, `<=`, `>`, `<`) ayrı ayrı uygula; `engel` yalnızca `None` iken ilk başarısız indisle güncellenmelidir.
```
:::

::: anlat Sembolik aralık daraltma ve ölü dal tespiti
Tam sayı değişkenler üzerinde `>` ve `<` operatörleri sınırı 1 kaydırır: `x > 1024` demek en az `1025` (`deger + 1`), `x < 200` demek en çok `199` (`deger - 1`) demektir. Tüm kısıtlar daraltıldıktan sonra her değişken için `alt <= ust` sağlanıyorsa orta nokta `(alt + ust) // 2` somut aday olarak üretilir.

**Görev 2'de sık tuzaklar:** `==` kısıtında yalnız alt sınırı veya yalnız üst sınırı güncellemek aralığı tek noktaya kilitlemez; hem `alt = max(alt, deger)` hem `ust = min(ust, deger)` uygulanmalıdır. Böylece daha önce `x > 500` denmişken sonra `x == 200` gelirse `[501, 200]` oluşur ve çelişki (`cozulebilir=False`) doğru yakalanır.
:::

::: gorev 2 · Sembolik aralık daraltıcı (`sembolik_aralik_daralt`)
`sembolik_aralik_daralt(kisitlar,baslangic_alt,baslangic_ust)`: `kisitlar` en az 1 elemanlı kısıt listesi (`op` `("==",">=","<=",">","<")` içinde); `baslangic_alt <= baslangic_ust` bool olmayan int. Her değişkeni `[baslangic_alt, baslangic_ust]` aralığından başlatıp daralt; tümünde `alt <= ust` ise `cozulebilir=True` ve `aday={deg: (alt+ust)//2}`, değilse `cozulebilir=False` ve `aday=None` ile `{"araliklar":..., "cozulebilir":..., "aday":...}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-20")
```
```starter
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def sembolik_aralik_daralt(kisitlar,baslangic_alt,baslangic_ust):
    ar={k["degisken"]:[baslangic_alt,baslangic_ust] for k in kisitlar}
    for k in kisitlar:
        a,u=ar[k["degisken"]]
        if k["op"] in (">",">="):a=max(a,k["deger"])
        elif k["op"] in ("<","<="):u=min(u,k["deger"])
        ar[k["degisken"]]=[a,u]
    return {"araliklar":ar,"cozulebilir":True,"aday":{d:(a+u)//2 for d,(a,u) in ar.items()}}

from ai_ile_guvenlik_veri import json_yukle
v=json_yukle("veri/sembolik_avci.json")
for ad,kl in v["kisit_listesi"].items():
    print(ad,sembolik_aralik_daralt(kl,v["alt_sinir"],v["ust_sinir"]))
```
```test
def sinama2(f):
    import copy
    try:
        kl=[{"degisken":"s","op":"==","deger":48879},{"degisken":"p","op":">","deger":1024},{"degisken":"p","op":"<=","deger":1040}]
        old=copy.deepcopy(kl)
        r=f(kl,0,65535)
        if kl!=old or r!={"araliklar":{"s":[48879,48879],"p":[1025,1040]},"cozulebilir":True,"aday":{"s":48879,"p":1032}}:return False
        olu=[{"degisken":"p","op":">","deger":500},{"degisken":"p","op":"<","deger":501}]
        r2=f(olu,0,1000)
        if r2["cozulebilir"] is not False or r2["aday"] is not None or r2["araliklar"]["p"]!=[501,500]:return False
        olu2=[{"degisken":"p","op":">=","deger":100},{"degisken":"p","op":"==","deger":50}]
        if f(olu2,0,1000)["cozulebilir"] is not False:return False
        for bad in ((None,0,10),([],0,10),(kl,20,10),(kl,True,10),(kl,0,False),([{"degisken":"x","op":"!=","deger":5}],0,10),([{"degisken":"x","op":"==","deger":True}],0,10)):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama2(sembolik_aralik_daralt),"aralık daraltma, sıkı eşitsizlik kaydırma, çelişkili dal tespiti ve geçersiz girdi")
for ad,mut in [("sıkı eşitsizlik kaydırmaz",lambda kl,a,u:dict(sembolik_aralik_daralt([dict(k,op=">=" if k["op"]==">" else "<=" if k["op"]=="<" else k["op"]) for k in kl],a,u))),("hep çözülebilir",lambda kl,a,u:dict(sembolik_aralik_daralt(kl,a,u),cozulebilir=True)),("aday hep None",lambda kl,a,u:dict(sembolik_aralik_daralt(kl,a,u),aday=None))]:
    ok(not sinama2(mut),"mutant reddedildi: "+ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(sembolik_aralik_daralt, _il.import_module('ai_gercek_ai_ile_guvenlik_20').referans_daralt, ([{'degisken': 'sihirli_baslik', 'op': '==', 'deger': 48879}, {'degisken': 'paket_boyutu', 'op': '>', 'deger': 1024}, {'degisken': 'paket_boyutu', 'op': '<=', 'deger': 1040}, {'degisken': 'bayrak', 'op': '==', 'deger': 7}], 0, 65535), tohum=3922)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
# hedefli tablo: sembolik_aralik_daralt her operatör, tek noktalık ve boş aralık
_R20b = _il.import_module("ai_gercek_ai_ile_guvenlik_20")
_ek = tuple(([{"degisken": "a", "op": o, "deger": v}], 0, 10) for o in ("==", ">=", "<=", ">", "<") for v in (0, 5, 10))
_ek += (([{"degisken": "a", "op": ">", "deger": 5}, {"degisken": "a", "op": "<", "deger": 7}], 0, 10), ([{"degisken": "a", "op": ">", "deger": 5}, {"degisken": "a", "op": "<", "deger": 6}], 0, 10),
        ([{"degisken": "a", "op": ">=", "deger": 3}, {"degisken": "b", "op": "<=", "deger": 2}], 0, 10), ([{"degisken": "a", "op": "!=", "deger": 3}], 0, 10))
_t, _g = _ff(sembolik_aralik_daralt, _R20b.referans_daralt, _ek[0], en_cok=0, ekler=_ek)
ok(_t, "her operatör, tek noktalık aralık (a = u) ve boş aralık (a = u + 1) referansla aynı" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
def sembolik_aralik_daralt(kisitlar,baslangic_alt,baslangic_ust):
    if not isinstance(kisitlar,list) or not kisitlar or isinstance(baslangic_alt,bool) or isinstance(baslangic_ust,bool) or not isinstance(baslangic_alt,int) or not isinstance(baslangic_ust,int) or baslangic_alt>baslangic_ust:raise ValueError("girdi")
    ops=("==",">=","<=",">","<")
    ar={}
    for k in kisitlar:
        if not isinstance(k,dict) or set(k)!={"degisken","op","deger"}:raise ValueError("şema")
        d,op,val=k["degisken"],k["op"],k["deger"]
        if not isinstance(d,str) or not d.strip() or op not in ops or isinstance(val,bool) or not isinstance(val,int):raise ValueError("kisit")
        if d not in ar:ar[d]=[baslangic_alt,baslangic_ust]
        a,u=ar[d]
        if op=="==":a=max(a,val);u=min(u,val)
        elif op==">=":a=max(a,val)
        elif op=="<=":u=min(u,val)
        elif op==">":a=max(a,val+1)
        elif op=="<":u=min(u,val-1)
        ar[d]=[a,u]
    coz=all(a<=u for a,u in ar.values())
    aday={d:(a+u)//2 for d,(a,u) in ar.items()} if coz else None
    return {"araliklar":ar,"cozulebilir":coz,"aday":aday}

from ai_ile_guvenlik_veri import json_yukle
v=json_yukle("veri/sembolik_avci.json")
for ad,kl in v["kisit_listesi"].items():
    print(ad,sembolik_aralik_daralt(kl,v["alt_sinir"],v["ust_sinir"]))
```
```hint
`>` için `max(a, val + 1)`, `<` için `min(u, val - 1)`, `==` için hem `max(a, val)` hem `min(u, val)` uygula.
```
:::

::: anlat Hibrit orkestrasyon: önce fuzzer, takılırsa sembolik çözücü
`hibrit_tetikleyici_bul` işlevi gerçek bir hibrit zafiyet avcısının karar döngüsünü uygular:
1. Önce `rastgele_adaylar` sırayla `dal_kisiti_degerlendir` ile sınanır ve en yüksek `gecen_sayisi` değeri `rastgele_en_iyi` olarak tutulur.
2. Eğer rastgele adaylardan biri `tam_cozum` sağlarsa çözücüye hiç gerek kalmadan `"yontem": "fuzzer"` ile o aday döndürülür.
3. Rastgele adayların hiçbiri tam çözüm sağlayamazsa `sembolik_aralik_daralt` çağrılır; üretilen `aday` yürütücüyle doğrulanırsa `"yontem": "sembolik_cozucu"`, dal çelişkiliyse `"yontem": "basarisiz"` döndürülür.

**Görev 3'te sık tuzaklar:** `kisit_listesi` içindeki tüm dalların geçerli kısıt şemasına sahip olduğu başta doğrulanmalıdır.
:::

::: gorev 3 · Hibrit tetikleyici bulucu (`hibrit_tetikleyici_bul`)
`hibrit_tetikleyici_bul(kisit_listesi,rastgele_adaylar,alt_sinir,ust_sinir,hedef_dal)`: `kisit_listesi` boş olmayan `dal_adi -> kisitlar` sözlüğü (`sembolik_aralik_daralt` kurallarında); `hedef_dal` bunun içinde; `rastgele_adaylar` en az 1 elemanlı aday sözlüğü listesi; `alt_sinir <= ust_sinir`. `{"yontem": "fuzzer"|"sembolik_cozucu"|"basarisiz", "tetikleyici": aday veya None, "rastgele_en_iyi":..., "toplam_kisit":..., "basarili": bool}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-20")
```
```starter
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def hibrit_tetikleyici_bul(kisit_listesi,rastgele_adaylar,alt_sinir,ust_sinir,hedef_dal):
    kl=kisit_listesi[hedef_dal]
    return {"yontem":"fuzzer","tetikleyici":rastgele_adaylar[0],"rastgele_en_iyi":len(kl),"toplam_kisit":len(kl),"basarili":True}

from ai_ile_guvenlik_veri import json_yukle
v=json_yukle("veri/sembolik_avci.json")
print(hibrit_tetikleyici_bul(v["kisit_listesi"],v["rastgele_adaylar"],v["alt_sinir"],v["ust_sinir"],v["hedef_dal"]))
```
```test
def sinama3(f):
    import copy
    try:
        ks={
            "dar":[{"degisken":"s","op":"==","deger":48879},{"degisken":"p","op":">","deger":1024},{"degisken":"p","op":"<=","deger":1040}],
            "olu":[{"degisken":"s","op":">","deger":500},{"degisken":"s","op":"<","deger":200}]
        }
        ra=[{"s":10,"p":500},{"s":48879,"p":200}]
        old=(copy.deepcopy(ks),copy.deepcopy(ra))
        r=f(ks,ra,0,65535,"dar")
        if (ks,ra)!=old or r!={"yontem":"sembolik_cozucu","tetikleyici":{"s":48879,"p":1032},"rastgele_en_iyi":2,"toplam_kisit":3,"basarili":True}:return False
        r_fuz=f(ks,[{"s":48879,"p":1030}],0,65535,"dar")
        if r_fuz!={"yontem":"fuzzer","tetikleyici":{"s":48879,"p":1030},"rastgele_en_iyi":3,"toplam_kisit":3,"basarili":True}:return False
        r_olu=f(ks,ra,0,65535,"olu")
        if r_olu!={"yontem":"basarisiz","tetikleyici":None,"rastgele_en_iyi":1,"toplam_kisit":2,"basarili":False}:return False
        if f(ks,[{"s":48879,"p":200},{"s":10,"p":500}],0,65535,"dar")["rastgele_en_iyi"]!=2:return False
        if f(ks,[{"s":300}],0,65535,"olu")["rastgele_en_iyi"]!=0:return False
        for bad in ((None,ra,0,100,"dar"),(ks,None,0,100,"dar"),(ks,[],0,100,"dar"),(ks,ra,0,100,"yok"),(ks,ra,200,100,"dar"),(ks,ra,True,100,"dar")):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama3(hibrit_tetikleyici_bul),"fuzzer önceliği, sembolik çözücüye devir, ölü dal reddi ve geçersiz girdi")
for ad,mut in [("hep fuzzer",lambda ks,ra,a,u,h:dict(hibrit_tetikleyici_bul(ks,ra,a,u,h),yontem="fuzzer")),("sembolik yok",lambda ks,ra,a,u,h:{"yontem":"basarisiz","tetikleyici":None,"rastgele_en_iyi":0,"toplam_kisit":len(ks[h]),"basarili":False}),("ilerleme sıfır",lambda ks,ra,a,u,h:dict(hibrit_tetikleyici_bul(ks,ra,a,u,h),rastgele_en_iyi=0))]:
    ok(not sinama3(mut),"mutant reddedildi: "+ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(hibrit_tetikleyici_bul, _il.import_module('ai_gercek_ai_ile_guvenlik_20').referans_hibrit, ({'kritik_bellek_tasmasi': [{'degisken': 'sihirli_baslik', 'op': '==', 'deger': 48879}, {'degisken': 'paket_boyutu', 'op': '>', 'deger': 1024}, {'degisken': 'paket_boyutu', 'op': '<=', 'deger': 1040}, {'degisken': 'bayrak', 'op': '==', 'deger': 7}], 'celiskili_olu_dal': [{'degisken': 'paket_boyutu', 'op': '>', 'deger': 500}, {'degisken': 'paket_boyutu', 'op': '<', 'deger': 200}]}, [{'sihirli_baslik': 1204, 'paket_boyutu': 512, 'bayrak': 1}, {'sihirli_baslik': 48879, 'paket_boyutu': 200, 'bayrak': 0}, {'sihirli_baslik': 48879, 'paket_boyutu': 1030, 'bayrak': 3}], 0, 65535, 'kritik_bellek_tasmasi'), tohum=3957)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(dal_kisiti_degerlendir, _il.import_module('ai_gercek_ai_ile_guvenlik_20').referans_degerlendir, ([{'degisken': 'sihirli_baslik', 'op': '==', 'deger': 48879}, {'degisken': 'paket_boyutu', 'op': '>', 'deger': 1024}, {'degisken': 'paket_boyutu', 'op': '<=', 'deger': 1040}, {'degisken': 'bayrak', 'op': '==', 'deger': 7}], {'sihirli_baslik': 1204, 'paket_boyutu': 512, 'bayrak': 1}), tohum=3923)
ok(_t, "farksal tarama (dal_kisiti_degerlendir): bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(sembolik_aralik_daralt, _il.import_module('ai_gercek_ai_ile_guvenlik_20').referans_daralt, ([{'degisken': 'sihirli_baslik', 'op': '==', 'deger': 48879}, {'degisken': 'paket_boyutu', 'op': '>', 'deger': 1024}, {'degisken': 'paket_boyutu', 'op': '<=', 'deger': 1040}, {'degisken': 'bayrak', 'op': '==', 'deger': 7}], 0, 65535), tohum=3922)
ok(_t, "farksal tarama (sembolik_aralik_daralt): bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
# hedefli tablo: dal_kisiti_degerlendir her operatör ve sınır
_R20 = _il.import_module("ai_gercek_ai_ile_guvenlik_20")
_ek = tuple(([{"degisken": "a", "op": o, "deger": 5}, {"degisken": "b", "op": "==", "deger": 1}], {"a": x, "b": 1}) for o in ("==", "!=", ">=", "<=", ">", "<") for x in (4, 5, 6))
_t, _g = _ff(dal_kisiti_degerlendir, _R20.referans_degerlendir, _ek[0], en_cok=0, ekler=_ek)
ok(_t, "her operatör (==, !=, >=, <=, >, <) için x<val, x=val, x>val sınırları referansla aynı" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
# hedefli tablo: sembolik_aralik_daralt her operatör, tek noktalık ve boş aralık
_R20b = _il.import_module("ai_gercek_ai_ile_guvenlik_20")
_ek = tuple(([{"degisken": "a", "op": o, "deger": v}], 0, 10) for o in ("==", ">=", "<=", ">", "<") for v in (0, 5, 10))
_ek += (([{"degisken": "a", "op": ">", "deger": 5}, {"degisken": "a", "op": "<", "deger": 7}], 0, 10), ([{"degisken": "a", "op": ">", "deger": 5}, {"degisken": "a", "op": "<", "deger": 6}], 0, 10),
        ([{"degisken": "a", "op": ">=", "deger": 3}, {"degisken": "b", "op": "<=", "deger": 2}], 0, 10), ([{"degisken": "a", "op": "!=", "deger": 3}], 0, 10))
_t, _g = _ff(sembolik_aralik_daralt, _R20b.referans_daralt, _ek[0], en_cok=0, ekler=_ek)
ok(_t, "her operatör, tek noktalık aralık (a = u) ve boş aralık (a = u + 1) referansla aynı" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
# hedefli tablo: hibrit bulucu, sembolik aday != kısıtını bozarsa başarı sayılmaz
_R20c = _il.import_module("ai_gercek_ai_ile_guvenlik_20")
_ek = (({"h": [{"degisken": "a", "op": "!=", "deger": 5}]}, [{"a": 5}], 0, 10, "h"),
       ({"h": [{"degisken": "a", "op": "!=", "deger": 4}]}, [{"a": 4}], 0, 10, "h"),
       ({"h": [{"degisken": "a", "op": ">", "deger": 5}, {"degisken": "a", "op": "<", "deger": 6}]}, [{"a": 5}], 0, 10, "h"),
       ({"h": [{"degisken": "a", "op": "==", "deger": 7}], "g": [{"degisken": "a", "op": "<", "deger": 3}]}, [{"a": 1}], 0, 10, "h"))
_t, _g = _ff(hibrit_tetikleyici_bul, _R20c.referans_hibrit, _ek[0], en_cok=0, ekler=_ek)
ok(_t, "sembolik aday yalnız gerçekten bütün kısıtları sağlıyorsa başarı; != ve boş aralık durumları referansla aynı" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
def dal_kisiti_degerlendir(kisitlar,aday_girdi):
    if not isinstance(kisitlar,list) or not kisitlar or not isinstance(aday_girdi,dict) or not aday_girdi:raise ValueError("girdi")
    for k,v in aday_girdi.items():
        if not isinstance(k,str) or not k.strip() or isinstance(v,bool) or not isinstance(v,int):raise ValueError("aday")
    ops=("==","!=",">=","<=",">","<")
    gecen=0;engel=None
    for i,k in enumerate(kisitlar):
        if not isinstance(k,dict) or set(k)!={"degisken","op","deger"}:raise ValueError("şema")
        d,op,val=k["degisken"],k["op"],k["deger"]
        if not isinstance(d,str) or not d.strip() or op not in ops or isinstance(val,bool) or not isinstance(val,int) or d not in aday_girdi:raise ValueError("kisit")
        x=aday_girdi[d]
        ok_mu=(x==val if op=="==" else x!=val if op=="!=" else x>=val if op==">=" else x<=val if op=="<=" else x>val if op==">" else x<val)
        if ok_mu:gecen+=1
        elif engel is None:engel=i
    return {"gecen_sayisi":gecen,"toplam_kisit":len(kisitlar),"ilk_engel_indisi":engel,"tam_cozum":gecen==len(kisitlar)}

def sembolik_aralik_daralt(kisitlar,baslangic_alt,baslangic_ust):
    if not isinstance(kisitlar,list) or not kisitlar or isinstance(baslangic_alt,bool) or isinstance(baslangic_ust,bool) or not isinstance(baslangic_alt,int) or not isinstance(baslangic_ust,int) or baslangic_alt>baslangic_ust:raise ValueError("girdi")
    ops=("==",">=","<=",">","<")
    ar={}
    for k in kisitlar:
        if not isinstance(k,dict) or set(k)!={"degisken","op","deger"}:raise ValueError("şema")
        d,op,val=k["degisken"],k["op"],k["deger"]
        if not isinstance(d,str) or not d.strip() or op not in ops or isinstance(val,bool) or not isinstance(val,int):raise ValueError("kisit")
        if d not in ar:ar[d]=[baslangic_alt,baslangic_ust]
        a,u=ar[d]
        if op=="==":a=max(a,val);u=min(u,val)
        elif op==">=":a=max(a,val)
        elif op=="<=":u=min(u,val)
        elif op==">":a=max(a,val+1)
        elif op=="<":u=min(u,val-1)
        ar[d]=[a,u]
    coz=all(a<=u for a,u in ar.values())
    aday={d:(a+u)//2 for d,(a,u) in ar.items()} if coz else None
    return {"araliklar":ar,"cozulebilir":coz,"aday":aday}

def hibrit_tetikleyici_bul(kisit_listesi,rastgele_adaylar,alt_sinir,ust_sinir,hedef_dal):
    if not isinstance(kisit_listesi,dict) or not kisit_listesi or not isinstance(hedef_dal,str) or not hedef_dal.strip() or hedef_dal not in kisit_listesi:raise ValueError("hedef")
    if not isinstance(rastgele_adaylar,list) or not rastgele_adaylar or isinstance(alt_sinir,bool) or isinstance(ust_sinir,bool) or not isinstance(alt_sinir,int) or not isinstance(ust_sinir,int) or alt_sinir>ust_sinir:raise ValueError("ayar")
    for d_ad,kl in kisit_listesi.items():
        if not isinstance(d_ad,str) or not d_ad.strip():raise ValueError("dal")
        sembolik_aralik_daralt(kl,alt_sinir,ust_sinir)
    hedef_k=kisit_listesi[hedef_dal]
    en_iyi=0;ilk_tam=None
    for ad in rastgele_adaylar:
        s=dal_kisiti_degerlendir(hedef_k,ad)
        if s["gecen_sayisi"]>en_iyi:en_iyi=s["gecen_sayisi"]
        if s["tam_cozum"] and ilk_tam is None:ilk_tam=dict(ad)
    if ilk_tam is not None:
        return {"yontem":"fuzzer","tetikleyici":ilk_tam,"rastgele_en_iyi":en_iyi,"toplam_kisit":len(hedef_k),"basarili":True}
    dar=sembolik_aralik_daralt(hedef_k,alt_sinir,ust_sinir)
    if dar["cozulebilir"] and dar["aday"] is not None and dal_kisiti_degerlendir(hedef_k,dar["aday"])["tam_cozum"]:
        return {"yontem":"sembolik_cozucu","tetikleyici":dar["aday"],"rastgele_en_iyi":en_iyi,"toplam_kisit":len(hedef_k),"basarili":True}
    return {"yontem":"basarisiz","tetikleyici":None,"rastgele_en_iyi":en_iyi,"toplam_kisit":len(hedef_k),"basarili":False}

from ai_ile_guvenlik_veri import json_yukle
v=json_yukle("veri/sembolik_avci.json")
print(hibrit_tetikleyici_bul(v["kisit_listesi"],v["rastgele_adaylar"],v["alt_sinir"],v["ust_sinir"],v["hedef_dal"]))
```
```hint
Önce `rastgele_adaylar` üzerinde döngü kurup `dal_kisiti_degerlendir` çağır; tam çözüm çıkmazsa `sembolik_aralik_daralt` sonucunu dene.
```
:::

::: anlat Hata vitrini · çalışmış yanlış rapor
Yazar, kusurlu başlangıç kodlarını görünür sentetik veriyle gerçekten çalıştırdı ve sonucu `outputs/yeni-ai-ile-guvenlik-20/gorunur-run-1.json` dosyasına kaydetti. 2. görevin kusurlu kodu `==` operatörünü işlemediği ve `>` kısıtında sınırı 1 artırmadığı için `sihirli_baslik` aralığını `[0, 65535]` bırakır ve aday olarak `sihirli_baslik=32767, bayrak=32767` üretir. Doğru kod ise aralığı `[48879, 48879]` ve `[7, 7]` olarak daraltıp tam tetikleyiciyi üretir.

Bu kaydedilmiş bir hesaplama çıktısıdır, model yanıtı değildir ve rapor sentetiktir. Çözücünün ürettiği adayı yürütücüde tekrar doğrulamadan "zafiyet tetiklendi" raporu yazan bir güvenlik ajanı ne tür bir yanlış-pozitif (`hallucinated PoC`) üretir? Kendi cümlenle açıkla. Gerçek finaldeki ölçüm ayrıca üretilir; bu sayılar onun yerine konmaz.
:::

::: anlat Gerçek deney: gerçek hedef programlarda kör fuzzer, kapsam güdümlü fuzzer ve hibrit çözücü
Final, uydurma kısıt listeleri yerine **gerçek hedef programlar** kurar. 12 hedefin her biri, 8 baytlık bir ağ paketini ayrıştıran bir Python fonksiyonudur (`ayristir`). Hepsinde aynı tür hata vardır: sihirli başlık (16 bit) belirli bir değerse, paket boyutu dar bir aralıktaysa ve bayrak belirli bir bayt ise, kod uzunluk alanına güvenip 16 baytlık bir tampona **sınır dışı yazar**. Python bunu `IndexError` olarak yakalar; C'de bu, sessiz bir bellek bozulması olurdu. Her hedefin sabitleri rastgeledir. Ayrıca her hedefte hiçbir girdiyle ulaşılamayan bir **ölü dal** vardır (`> 50000` ve `< 10000`).

Her hedefe 4096 girdi bütçesiyle üç yöntem uygulanır:
1. **Kör rastgele fuzzer:** Rastgele 8 baytlık paketler gerçek ayrıştırıcıda çalışır.
2. **Kapsam güdümlü mutasyon fuzzer'ı (AFL benzeri):** Programda daha derine (yeni bir dala) ulaşan girdiler havuza alınır, sonra 1–3 bayt değiştirilerek ya da bit çevrilerek mutasyona uğratılır.
3. **Hibrit:** Yol koşulları programın **kaynak kodundan** Python'un `ast` modülüyle çıkarılır: çökme dalına giden iç içe `if` koşulları ve ölü dalın koşulları. Senin `hibrit_tetikleyici_bul` işlevin önce fuzzer derlemine bakar, bulamazsa `sembolik_aralik_daralt` ile tetikleyici üretir. Tetikleyici baytlara çevrilip **gerçek programda çalıştırılır**: çöktü mü?

Yazarın üç koşusunda (her biri <1 sn) sonuçlar aynıydı:
- **Kör fuzzer: 0/12** hedefte çöküş. Programda ilerlediği ortalama dal derinliği 0–0.17/4: rastgele girdi 16 bitlik sihirli başlığı nadiren tutturur.
- **Kapsam güdümlü fuzzer: 0/12**, derinlik 0/4. Sihirli başlık geçilmedikçe yeni bir dal açılmaz, bu yüzden kapsam geri bildirimi hiç sinyal vermez. Bu, AFL'nin bilinen kör noktasıdır. Çözümü ya karşılaştırmaları bayt bayt bölmek (laf-intel, CmpLog) ya da sembolik yürütmedir (Driller).
- **Hibrit: 12/12** hedefte tetikleyici üretildi ve tetikleyicilerin **12/12'si gerçek programı çökertti.**
- **Ölü dal** her hedefte çözülemez bulundu.

**4. LLM ile yol koşulu çıkarımı (AIxCC tarzı).** Plan, kısıtları bir LLM'in programdan çıkarmasını istiyordu. Final bunu da dener: yerel Ollama `qwen3:4b-instruct` 6 yeni hedefin kaynak kodunu okur ve "HATA satırına ulaşmak için gereken koşulları" JSON olarak yazar. Bu kısıtlar **senin `sembolik_aralik_daralt` işlevinle** çözülür ve gerçek programda çalıştırılır. Ollama yoksa bu bölüm atlanır ve kabulü etkilemez. Yazarın üç koşusunda:
- **Ham LLM çıktısı: 0/6.** Hiçbir hedefte `ast` ile aynı kısıtları vermedi ve çözümü hiçbir hedefi çökertmedi. Hata türleri:
  - Ölü dalın koşullarını (`> 50000`, `< 10000`) yola kattı: 6/6.
  - Değişken adında yazım hatası yaptı (`sirihli_baslik`): 6/6.
  - Bir koşulu (çoğunlukla `paket_boyutu <= üst`) atladı: 3–5/6.
- **Doğrulayıcıyla onarım: 1–3/6.** Adlar en yakın gerçek alana eşlenir. Çelişki çözülene kadar en az sayıda kısıt atılır. Her aday gerçek programda denenir.
- **Bir geri bildirim turuyla: 5–6/6.** Program hata satırına ulaşmazsa, adayın değerleri ve programın gerçek dönüş değeri ("buyuk", "kucuk") LLM'e söylenir; LLM listesini düzeltir.

Ders: LLM tek başına güvenilir bir kısıt çıkarıcı değildir. **Doğrulayıcı + yürütme geri bildirimi** döngüsüne bağlandığında işe yarar hâle gelir. AIxCC sistemleri de LLM'i böyle bir döngüde kullanır.

**Kanıt dosyasını oku:** Soru 1: Kapsam güdümlü fuzzer neden kör fuzzer'dan bile iyi değildi? Hangi tek değişiklik (ör. sihirli başlık karşılaştırmasını iki ayrı bayt karşılaştırmasına bölmek) onu kurtarırdı? Soru 2: Dal koşulunda `sha256(veri) == hedef` olsaydı `sembolik_aralik_daralt` neden yardımcı olamazdı? Soru 3: `ast` ile koşul çıkarmak hangi hedeflerde işe yaramaz (ör. koşul bir fonksiyon çağrısının sonucuna bağlıysa)? Cevabını tezgâhta yorum olarak yaz; otomatik test bu serbest açıklamayı puanlamaz.
:::

::: gorev Gerçek deney · Gerçek hedef programlarda hibrit zafiyet avcısı ve dar dal erişimi
Önceki üç görevin `dal_kisiti_degerlendir`, `sembolik_aralik_daralt` ve `hibrit_tetikleyici_bul` işlevlerini birleştir. Çalıştır gerçek karşılaştırma tablosunu gösterir; Kontrol Et önce üç sözleşmeyi gizli verilerle sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```
```starter
import ai_lab
def dal_kisiti_degerlendir(kisitlar,aday_girdi):
    return {"gecen_sayisi":0,"toplam_kisit":len(kisitlar),"ilk_engel_indisi":0,"tam_cozum":False}
def sembolik_aralik_daralt(kisitlar,baslangic_alt,baslangic_ust):
    return {"araliklar":{},"cozulebilir":False,"aday":None}
def hibrit_tetikleyici_bul(kisit_listesi,rastgele_adaylar,alt_sinir,ust_sinir,hedef_dal):
    return {"yontem":"basarisiz","tetikleyici":None,"rastgele_en_iyi":0,"toplam_kisit":len(kisit_listesi[hedef_dal]),"basarili":False}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_ile_guvenlik_20 as D
    D.goster(dal_kisiti_degerlendir,sembolik_aralik_daralt,hibrit_tetikleyici_bul)
```
```test
import ai_lab
checks=[]
def kontrol(x,m):checks.append(bool(x));ok(x,m)
issues=ai_lab.kod_denetimi(src,('referans_degerlendir', 'referans_daralt', 'referans_hibrit', 'kanit_yaz', '_yakin'),izin=())
kontrol(not issues,"kopya/yama/dinamik kod yok: "+str(issues))
if issues:stop()
dal_kisiti_degerlendir=need("dal_kisiti_degerlendir")
sembolik_aralik_daralt=need("sembolik_aralik_daralt")
hibrit_tetikleyici_bul=need("hibrit_tetikleyici_bul")
def sinama1(f):
    import copy
    try:
        kl=[{"degisken":"x","op":"==","deger":10},{"degisken":"y","op":">","deger":5},{"degisken":"z","op":"!=","deger":0}]
        ad={"x":10,"y":6,"z":1};old=(copy.deepcopy(kl),dict(ad))
        if f(kl,ad)!={"gecen_sayisi":3,"toplam_kisit":3,"ilk_engel_indisi":None,"tam_cozum":True} or (kl,ad)!=old:return False
        if f(kl,{"x":10,"y":5,"z":0})!={"gecen_sayisi":1,"toplam_kisit":3,"ilk_engel_indisi":1,"tam_cozum":False}:return False
        kl2=[{"degisken":"a","op":">=","deger":3},{"degisken":"a","op":"<=","deger":5},{"degisken":"a","op":"<","deger":5}]
        if f(kl2,{"a":5})!={"gecen_sayisi":2,"toplam_kisit":3,"ilk_engel_indisi":2,"tam_cozum":False}:return False
        if f(kl2,{"a":3})!={"gecen_sayisi":3,"toplam_kisit":3,"ilk_engel_indisi":None,"tam_cozum":True}:return False
        for bad in ((None,ad),(kl,None),([],ad),(kl,{}),([{"degisken":"x","op":"==","deger":10}],{"y":10}),([{"degisken":"x","op":"~","deger":10}],ad),([{"degisken":"x","op":"==","deger":True}],ad),(kl,{"x":True,"y":6,"z":1}),([{"degisken":"","op":"==","deger":10}],ad)):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
kontrol(sinama1(dal_kisiti_degerlendir),"altı karşılaştırma operatörü, ilk engel indisi ve geçersiz girdi")
for ad,mut in [("son engel indisi",lambda kl,a:dict(dal_kisiti_degerlendir(kl,a),ilk_engel_indisi=len(kl)-1 if not dal_kisiti_degerlendir(kl,a)["tam_cozum"] else None)),("hep tam çözüm",lambda kl,a:dict(dal_kisiti_degerlendir(kl,a),tam_cozum=True)),("gecen sıfır",lambda kl,a:dict(dal_kisiti_degerlendir(kl,a),gecen_sayisi=0))]:
    kontrol(not sinama1(mut),"mutant reddedildi: "+ad)
def sinama2(f):
    import copy
    try:
        kl=[{"degisken":"s","op":"==","deger":48879},{"degisken":"p","op":">","deger":1024},{"degisken":"p","op":"<=","deger":1040}]
        old=copy.deepcopy(kl)
        r=f(kl,0,65535)
        if kl!=old or r!={"araliklar":{"s":[48879,48879],"p":[1025,1040]},"cozulebilir":True,"aday":{"s":48879,"p":1032}}:return False
        olu=[{"degisken":"p","op":">","deger":500},{"degisken":"p","op":"<","deger":501}]
        r2=f(olu,0,1000)
        if r2["cozulebilir"] is not False or r2["aday"] is not None or r2["araliklar"]["p"]!=[501,500]:return False
        olu2=[{"degisken":"p","op":">=","deger":100},{"degisken":"p","op":"==","deger":50}]
        if f(olu2,0,1000)["cozulebilir"] is not False:return False
        for bad in ((None,0,10),([],0,10),(kl,20,10),(kl,True,10),(kl,0,False),([{"degisken":"x","op":"!=","deger":5}],0,10),([{"degisken":"x","op":"==","deger":True}],0,10)):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
kontrol(sinama2(sembolik_aralik_daralt),"aralık daraltma, sıkı eşitsizlik kaydırma, çelişkili dal tespiti ve geçersiz girdi")
for ad,mut in [("sıkı eşitsizlik kaydırmaz",lambda kl,a,u:dict(sembolik_aralik_daralt([dict(k,op=">=" if k["op"]==">" else "<=" if k["op"]=="<" else k["op"]) for k in kl],a,u))),("hep çözülebilir",lambda kl,a,u:dict(sembolik_aralik_daralt(kl,a,u),cozulebilir=True)),("aday hep None",lambda kl,a,u:dict(sembolik_aralik_daralt(kl,a,u),aday=None))]:
    kontrol(not sinama2(mut),"mutant reddedildi: "+ad)
def sinama3(f):
    import copy
    try:
        ks={
            "dar":[{"degisken":"s","op":"==","deger":48879},{"degisken":"p","op":">","deger":1024},{"degisken":"p","op":"<=","deger":1040}],
            "olu":[{"degisken":"s","op":">","deger":500},{"degisken":"s","op":"<","deger":200}]
        }
        ra=[{"s":10,"p":500},{"s":48879,"p":200}]
        old=(copy.deepcopy(ks),copy.deepcopy(ra))
        r=f(ks,ra,0,65535,"dar")
        if (ks,ra)!=old or r!={"yontem":"sembolik_cozucu","tetikleyici":{"s":48879,"p":1032},"rastgele_en_iyi":2,"toplam_kisit":3,"basarili":True}:return False
        r_fuz=f(ks,[{"s":48879,"p":1030}],0,65535,"dar")
        if r_fuz!={"yontem":"fuzzer","tetikleyici":{"s":48879,"p":1030},"rastgele_en_iyi":3,"toplam_kisit":3,"basarili":True}:return False
        r_olu=f(ks,ra,0,65535,"olu")
        if r_olu!={"yontem":"basarisiz","tetikleyici":None,"rastgele_en_iyi":1,"toplam_kisit":2,"basarili":False}:return False
        if f(ks,[{"s":48879,"p":200},{"s":10,"p":500}],0,65535,"dar")["rastgele_en_iyi"]!=2:return False
        if f(ks,[{"s":300}],0,65535,"olu")["rastgele_en_iyi"]!=0:return False
        for bad in ((None,ra,0,100,"dar"),(ks,None,0,100,"dar"),(ks,[],0,100,"dar"),(ks,ra,0,100,"yok"),(ks,ra,200,100,"dar"),(ks,ra,True,100,"dar")):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
kontrol(sinama3(hibrit_tetikleyici_bul),"fuzzer önceliği, sembolik çözücüye devir, ölü dal reddi ve geçersiz girdi")
for ad,mut in [("hep fuzzer",lambda ks,ra,a,u,h:dict(hibrit_tetikleyici_bul(ks,ra,a,u,h),yontem="fuzzer")),("sembolik yok",lambda ks,ra,a,u,h:{"yontem":"basarisiz","tetikleyici":None,"rastgele_en_iyi":0,"toplam_kisit":len(ks[h]),"basarili":False}),("ilerleme sıfır",lambda ks,ra,a,u,h:dict(hibrit_tetikleyici_bul(ks,ra,a,u,h),rastgele_en_iyi=0))]:
    kontrol(not sinama3(mut),"mutant reddedildi: "+ad)
# farksal tarama (final)
import importlib as _il
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_R = _il.import_module('sandbox.ai_gercek_ai_ile_guvenlik_20')
for _ad, _ref, _taban, _toh in (
    ('dal_kisiti_degerlendir', 'referans_degerlendir', ([{'degisken': 'sihirli_baslik', 'op': '==', 'deger': 48879}, {'degisken': 'paket_boyutu', 'op': '>', 'deger': 1024}, {'degisken': 'paket_boyutu', 'op': '<=', 'deger': 1040}, {'degisken': 'bayrak', 'op': '==', 'deger': 7}], {'sihirli_baslik': 1204, 'paket_boyutu': 512, 'bayrak': 1}), 4445),
    ('sembolik_aralik_daralt', 'referans_daralt', ([{'degisken': 'sihirli_baslik', 'op': '==', 'deger': 48879}, {'degisken': 'paket_boyutu', 'op': '>', 'deger': 1024}, {'degisken': 'paket_boyutu', 'op': '<=', 'deger': 1040}, {'degisken': 'bayrak', 'op': '==', 'deger': 7}], 0, 65535), 4444),
    ('hibrit_tetikleyici_bul', 'referans_hibrit', ({'kritik_bellek_tasmasi': [{'degisken': 'sihirli_baslik', 'op': '==', 'deger': 48879}, {'degisken': 'paket_boyutu', 'op': '>', 'deger': 1024}, {'degisken': 'paket_boyutu', 'op': '<=', 'deger': 1040}, {'degisken': 'bayrak', 'op': '==', 'deger': 7}], 'celiskili_olu_dal': [{'degisken': 'paket_boyutu', 'op': '>', 'deger': 500}, {'degisken': 'paket_boyutu', 'op': '<', 'deger': 200}]}, [{'sihirli_baslik': 1204, 'paket_boyutu': 512, 'bayrak': 1}, {'sihirli_baslik': 48879, 'paket_boyutu': 200, 'bayrak': 0}, {'sihirli_baslik': 48879, 'paket_boyutu': 1030, 'bayrak': 3}], 0, 65535, 'kritik_bellek_tasmasi'), 4479),
):
    _t, _g = _ff(need(_ad), getattr(_R, _ref), _taban, tohum=_toh)
    kontrol(_t, "farksal tarama (" + _ad + "): bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
if not all(checks):stop()
from sandbox import ai_gercek_ai_ile_guvenlik_20 as D
try:r=D.deney(dal_kisiti_degerlendir,sembolik_aralik_daralt,hibrit_tetikleyici_bul)
except ai_lab.GercekLabYok as e:
    kontrol(False,"gerçek deney yok: "+str(e));stop()
kontrol(r["deg_ayni"],"tüm adaylarda dal kısıtı değerlendirmesi bağımsız referansla aynı")
kontrol(r["daralt_ayni"],"tüm hedeflerde sembolik aralık daraltma bağımsız referansla aynı")
kontrol(r["hibrit_ayni"],"tüm hedeflerde ve ölü dallarda hibrit çözücü bağımsız referansla aynı")
kontrol(r["hibrit_basari_orani"]==1.0,"hibrit çözücü 12 gerçek hedef programın tamamında tetikleyici üretti")
kontrol(r["gercek_cokme_orani"]==1.0,"çözücünün tetikleyicileri gerçek programlarda sınır dışı yazma hatasını tetikledi (12/12)")
kontrol(r["hibrit_basari_orani"]>r["yalniz_fuzzer_basari_orani"] and r["hibrit_basari_orani"]>r["kapsam_fuzzer_basari_orani"],"hibrit yaklaşım kör (%.2f) ve kapsam güdümlü (%.2f) fuzzer'ı geçti"%(r["yalniz_fuzzer_basari_orani"],r["kapsam_fuzzer_basari_orani"]))
ai_lab.kanit_yaz("ai-ile-guvenlik-20-kabul",{"kaynak":"gercek","kabul":all(checks),"ders":"ai-ile-guvenlik-20","deney":r})
```
```solution
import ai_lab
def dal_kisiti_degerlendir(kisitlar,aday_girdi):
    if not isinstance(kisitlar,list) or not kisitlar or not isinstance(aday_girdi,dict) or not aday_girdi:raise ValueError("girdi")
    for k,v in aday_girdi.items():
        if not isinstance(k,str) or not k.strip() or isinstance(v,bool) or not isinstance(v,int):raise ValueError("aday")
    ops=("==","!=",">=","<=",">","<")
    gecen=0;engel=None
    for i,k in enumerate(kisitlar):
        if not isinstance(k,dict) or set(k)!={"degisken","op","deger"}:raise ValueError("şema")
        d,op,val=k["degisken"],k["op"],k["deger"]
        if not isinstance(d,str) or not d.strip() or op not in ops or isinstance(val,bool) or not isinstance(val,int) or d not in aday_girdi:raise ValueError("kisit")
        x=aday_girdi[d]
        ok_mu=(x==val if op=="==" else x!=val if op=="!=" else x>=val if op==">=" else x<=val if op=="<=" else x>val if op==">" else x<val)
        if ok_mu:gecen+=1
        elif engel is None:engel=i
    return {"gecen_sayisi":gecen,"toplam_kisit":len(kisitlar),"ilk_engel_indisi":engel,"tam_cozum":gecen==len(kisitlar)}
def sembolik_aralik_daralt(kisitlar,baslangic_alt,baslangic_ust):
    if not isinstance(kisitlar,list) or not kisitlar or isinstance(baslangic_alt,bool) or isinstance(baslangic_ust,bool) or not isinstance(baslangic_alt,int) or not isinstance(baslangic_ust,int) or baslangic_alt>baslangic_ust:raise ValueError("girdi")
    ops=("==",">=","<=",">","<")
    ar={}
    for k in kisitlar:
        if not isinstance(k,dict) or set(k)!={"degisken","op","deger"}:raise ValueError("şema")
        d,op,val=k["degisken"],k["op"],k["deger"]
        if not isinstance(d,str) or not d.strip() or op not in ops or isinstance(val,bool) or not isinstance(val,int):raise ValueError("kisit")
        if d not in ar:ar[d]=[baslangic_alt,baslangic_ust]
        a,u=ar[d]
        if op=="==":a=max(a,val);u=min(u,val)
        elif op==">=":a=max(a,val)
        elif op=="<=":u=min(u,val)
        elif op==">":a=max(a,val+1)
        elif op=="<":u=min(u,val-1)
        ar[d]=[a,u]
    coz=all(a<=u for a,u in ar.values())
    aday={d:(a+u)//2 for d,(a,u) in ar.items()} if coz else None
    return {"araliklar":ar,"cozulebilir":coz,"aday":aday}
def hibrit_tetikleyici_bul(kisit_listesi,rastgele_adaylar,alt_sinir,ust_sinir,hedef_dal):
    if not isinstance(kisit_listesi,dict) or not kisit_listesi or not isinstance(hedef_dal,str) or not hedef_dal.strip() or hedef_dal not in kisit_listesi:raise ValueError("hedef")
    if not isinstance(rastgele_adaylar,list) or not rastgele_adaylar or isinstance(alt_sinir,bool) or isinstance(ust_sinir,bool) or not isinstance(alt_sinir,int) or not isinstance(ust_sinir,int) or alt_sinir>ust_sinir:raise ValueError("ayar")
    for d_ad,kl in kisit_listesi.items():
        if not isinstance(d_ad,str) or not d_ad.strip():raise ValueError("dal")
        sembolik_aralik_daralt(kl,alt_sinir,ust_sinir)
    hedef_k=kisit_listesi[hedef_dal]
    en_iyi=0;ilk_tam=None
    for ad in rastgele_adaylar:
        s=dal_kisiti_degerlendir(hedef_k,ad)
        if s["gecen_sayisi"]>en_iyi:en_iyi=s["gecen_sayisi"]
        if s["tam_cozum"] and ilk_tam is None:ilk_tam=dict(ad)
    if ilk_tam is not None:
        return {"yontem":"fuzzer","tetikleyici":ilk_tam,"rastgele_en_iyi":en_iyi,"toplam_kisit":len(hedef_k),"basarili":True}
    dar=sembolik_aralik_daralt(hedef_k,alt_sinir,ust_sinir)
    if dar["cozulebilir"] and dar["aday"] is not None and dal_kisiti_degerlendir(hedef_k,dar["aday"])["tam_cozum"]:
        return {"yontem":"sembolik_cozucu","tetikleyici":dar["aday"],"rastgele_en_iyi":en_iyi,"toplam_kisit":len(hedef_k),"basarili":True}
    return {"yontem":"basarisiz","tetikleyici":None,"rastgele_en_iyi":en_iyi,"toplam_kisit":len(hedef_k),"basarili":False}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_ile_guvenlik_20 as D
    D.goster(dal_kisiti_degerlendir,sembolik_aralik_daralt,hibrit_tetikleyici_bul)
```
```hint
Üç işlevi aynen birleştir. Yalnız fuzzer ile hibrit çözücünün dar dal başarı oranlarını karşılaştır.
```
:::

::: anlat Sınır
Bu ders değişken başına aralık daraltma ile çözülebilen dar dal koşullarını (`magic-byte` ve sınır kontrolleri) gösterir. Gerçek deneydeki hedefler küçük, tek fonksiyonlu ve yazarın şablonundan üretilmiş Python programlarıdır. Yol koşulları yalnız "değişken op sabit" biçimindeki `if`'lerden çıkarılır. Değişkenler arası doğrusal olmayan bağıntılar (`x * y == z`), kriptografik özetler ve döngüsel durum patlaması (`path explosion`) tam teşekküllü SMT çözücüleri (ör. Z3) ve alan-özel önceliklendirme gerektirir; burada kullanılmazlar. LLM bölümü küçük bir yerel modelle, tek bir hedef şablonu ve tek bir geri bildirim turuyla yapılır. AIxCC sistemlerindeki LLM destekli tohum üretimi ve yama yazımı ölçülmez.
:::


::: anlat Bunu iki dakikada nasıl anlatırsın?
Random fuzzing dar bir magic değerini bütçede bulamayabilir. Yol koşullarındaki tamsayı eşitlik ve eşitsizlikleri aralık olarak kesiştir; sıkı sınırda bir ekle/çıkar adımının neden gerektiğini türet. Aralık boşsa çözümsüzlük, doluysa üretilen adayı gerçek koşulda tekrar doğrula. İlk tam fuzzer adayıyla symbolic adayın yöntem etiketini ayrı sakla. Bu tek değişkenli aralık kesişimi genel SMT solver veya concolic engine değildir.

Önkoşul ve yol köprüsü: ai-ile-guvenlik-04 AST ön elemesi.

| Yaygın yanlış | Mekanizma ve sınır |
|---|---|
| Symbolic aday üretildiğinde hata kesin tetiklendi | Aday gerçek hedef programda yeniden sınanır |

Dinleyiciye sor: Bir model önerisini gerçek güvenlik kararı hâline getiren hangi uygulama denetimidir? Veri kökenini ve kalan sınırı koruyarak cevapla.
:::


### Birincil kaynak ve deneyin sınırı

[Python AST belgeleri](https://docs.python.org/3/library/ast.html). Üretilen programın sözdizim ağacını incelemek, tüm olası yürütmeler için güvenlik ispatı değildir.
