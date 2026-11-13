---
id: ai-savunma-41
title: GraphRAG Anomali ve Köprü Karantinası · Çizge Zehirlenmesini Kesmek
summary: Topluluklar arası kenar oranını ve kaynak itibar filtresini hesapla; çok adımlı GraphRAG erişiminde sahte köprü düğümlerini tespit edip GPU'da karantinaya al.
esleme: ai-savunma-18, ai-savunma-36, ai-savunma-37
timeout: 60
---

::: anlat Tek bir sahte belge bütün bilgi çizgesini nasıl birbirine bağlar?
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| `GraphRAG` sistemlerinde dışarıdan enjekte edilen tek bir zehirli belge, birbirinden bağımsız topluluklardaki (`community`) popüler varlıklara sahte ilişkiler kurarak `bridge entity` hâline gelebilir | İlk üç görev: `veri/graphrag_savunma.json` içindeki **sentetik** çizge, topluluk etiketleri ve belge güven skorları. Final: yerel LLM ile kurulan gerçek GraphRAG indeksinde karantina öncesi/sonrası bağlam ve cevap zehirlenmesi; zehirli çizgenin kendi toplulukları ile güvenilir alt çizge toplulukları karşılaştırması | Yalnız çizge topolojisine bakarak metnin anlamsal doğruluğunu kanıtlayamaz; yapısal filtre içerik doğrulamasının yerini tutmaz |
| Topolojik anomali (`inter-community edge ratio`) ile kaynak itibarını (`provenance reputation`) birleştirmek, meşru denetim köprülerini korurken sahte köprüleri karantinaya alır | `topluluklar_arasi_oran`, `kaynak_itibar_filtresi` ve `cizge_karantina_raporu` | Yüksek itibarlı iç belgelerin bizzat ele geçirildiği (`insider poisoning`) senaryoları tek başına yakalayamaz |

> [!NOT]
> Görevler `veri/graphrag_savunma.json` dosyasını okur; dosya sentetiktir. Setup her Çalıştır/Kontrol Et adımında geçici kopya kurar; değişiklikler taşınmaz, **kalıcılık yoktur**. Ekranda ayrı dosya görüntüleyici yoktur; içeriği görmek için `print` kullan. Gizli testler ayrıdır. Final yeni model indirmez ve GPU varsa onu kullanır.

Vektör RAG'de ilk erişim benzerlik sıralamasına dayanır; zehirli bir parçanın etkisi sorgulara ve sonraki bağlam kullanımına bağlıdır, tek bir embedding komşuluğuyla kesin sınırlı değildir. Oysa `GraphRAG` (Edge vd. 2024) metinlerden varlık (`entity`) ve ilişki (`relation`) çıkarıp çok adımlı (`multi-hop`) alt-çizgeler ve topluluk özetleri üretir. Saldırgan tek bir belgede *"Sahte_Köprü varlığı; Kimlik_Doğrulama, Ödeme_Ağ_Geçidi ve Fatura_Motoru tarafından zorunlu kılınmıştır"* dediğinde, çıkarım boru hattı bu sahte düğümü tüm toplulukların merkezine bağlar.

**Topolojik sinyal: Topluluklar arası kenar oranı.** Normal bir varlık çoğunlukla kendi anlamsal topluluğu (`community`) içindeki düğümlerle komşudur. Bir $u$ düğümünün komşu kümesi $N(u)$ içinde kendi topluluğundan farklı bir topluluğa ait olanların oranı:
$$\rho(u) = \frac{|\{v \in N(u) : c(v) \neq c(u)\}|}{|N(u)|}$$
yüksekse, $u$ bir köprü düğümüdür (`bridge entity`).

**Kaynak sinyali: Nereden geldi (`provenance`)?** Her köprü düğümü zararlı değildir; örneğin kurumsal `denetim_kaydi` servisi gerçekten hem `kimlik` hem `finans` topluluklarına bağlanır. Ancak meşru bir kurumsal köprü birden fazla yüksek güvenilirlikli iç belgede (`min_kaynak_sayisi` ve `min_guven`) geçerken, saldırganın enjekte ettiği sahte köprü düşük itibarlı tekil dış kaynaklardan türetilmiştir.

**Saldırgan ne dener?** `GraphRAG` indeksleme aşamasında yüksek merkezilik (`betweenness centrality`) kazanmak için her anahtar topluluktan birer varlık adını aynı paragrafta geçiren "tutkal cümleler" enjekte eder.

**Savunma neden kırılır?** Yalnızca topolojik orana ($\rho(u)$) bakılırsa meşru mimari köprüler silinir ve sistemin çok adımlı muhakeme yeteneği felç olur. Yalnızca kaynak güvenine bakılırsa, düşük güvenilirlikli ama zararsız yaprak düğümler için gereksiz alarm üretilir. İki koşulun kesişimi (`VE` kapısı) bu dersin hedefli karantina politikasıdır; saldırgan bu koşullardan birinin altında kalırsa kaçabilir. İtibar puanı metnin kendi iddiasından veya LLM'nin yazdığı sayıdan alınmaz; uygulamanın kaynak kataloğundan gelmelidir.

**Görev 1'de sık tuzaklar:** Yönsüz çizgede `[u, v]` ve `[v, u]` olarak iki kez yazılmış kenarları iki ayrı komşu saymak dereceyi şişirir; komşular kümesi (`set`) üzerinden hesap yapılmalıdır.

Kaynaklar: [Edge vd. 2024 — From Local to Global: A Graph RAG Approach](https://arxiv.org/abs/2404.16130), [Zou vd. 2024 — PoisonedRAG](https://arxiv.org/abs/2402.07867), [Xiang vd. 2024 — Certifiably Robust RAG against Retrieval Corruption](https://arxiv.org/abs/2405.15556). Bu dersteki bütün sayılar yalnız yerel kanıttan gelir.

Köprü: ai-savunma-18 ve ai-savunma-36 RAG kaynak güvenini ve erişim karantinasını inceler; bu ders aynı ilkeyi `GraphRAG` topolojisine ve topluluklar arası köprü düğümlerine taşır.
:::

::: tahmin Meşru köprü ile sahte köprü nasıl ayrılır?
Çıktıyı tahmin et, sonra Çalıştır ile karşılaştır.
```python
kenarlar = [["k", "a1"], ["k", "b1"], ["k", "b2"]]
topluluk = {"k": "A", "a1": "A", "b1": "B", "b2": "B"}
komsular = {v if u == "k" else u for u, v in kenarlar if "k" in (u, v)}
farkli = sum(1 for v in komsular if topluluk[v] != topluluk["k"])
print(len(komsular), farkli, round(farkli / len(komsular), 4))
```
???
```cikti
3 2 0.6667
```
Tahmininle gerçek çıktı arasındaki farkı tezgâhta yorum satırı olarak yaz: `k` düğümünün komşularının üçte ikisi farklı bir topluluktadır; bu düğümün sahte mi yoksa meşru mu olduğuna karar vermek için hangi ek veriye bakmalıyız? Sonra üç kusurlu başlangıç kodunu çalıştır ve her birinin neyi kaçırdığını önce kendin teşhis et; açıklama çözümün ardından gelir.
:::

::: gorev 1 · Topluluklar arası kenar oranı (`topluluklar_arasi_oran`)
`topluluklar_arasi_oran(kenarlar,topluluklar,dugum)`: `kenarlar` en az 1 elemanlı `[u,v]` (`u!=v`, boş olmayan `str`) listesi; `topluluklar` boş olmayan `str->str` sözlüğü; tüm uçlar ve `dugum` `topluluklar` içinde olmalı. Yönsüz komşu kümesi $N(\text{dugum})$ üzerinden `{"derece": d, "farkli_topluluk": f, "oran": f/d if d>0 else 0.0}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-41")
```
```starter
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def topluluklar_arasi_oran(kenarlar,topluluklar,dugum):
    komsular=[v for u,v in kenarlar if u==dugum]
    d=len(komsular)
    f=sum(1 for v in komsular if topluluklar[v]!=topluluklar[dugum])
    return {"derece":d,"farkli_topluluk":f,"oran":f/d if d else 0.0}

from ai_savunma_veri import json_yukle
v=json_yukle("veri/graphrag_savunma.json")
for d in ("kimlik_dogrulama","sahte_kopru_dugumu","denetim_kaydi"):
    print(d,topluluklar_arasi_oran(v["kenarlar"],v["topluluklar"],d))
```
```test
def sinama1(f):
    import copy
    try:
        k=[["a","b"],["b","a"],["a","c"],["c","d"]];t={"a":"T1","b":"T1","c":"T2","d":"T2","yalniz":"T1"}
        old=(copy.deepcopy(k),dict(t))
        if f(k,t,"a")!={"derece":2,"farkli_topluluk":1,"oran":0.5} or (k,t)!=old:return False
        if f(k,t,"c")!={"derece":2,"farkli_topluluk":1,"oran":0.5}:return False
        if f(k,t,"d")!={"derece":1,"farkli_topluluk":0,"oran":0.0}:return False
        if f(k,t,"yalniz")!={"derece":0,"farkli_topluluk":0,"oran":0.0}:return False
        for bad in ((None,t,"a"),([],t,"a"),(k,{},"a"),(k,t,"yok"),(k,t,""),([["a","a"]],t,"a"),([["a","z"]],t,"a"),([["a"]],t,"a"),([("a","b")],t,"a"),(k,{"a":""},"a"),(k,t,None)):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama1(topluluklar_arasi_oran),"yönsüz tekil komşuluk, farklı topluluk oranı ve geçersiz girdi")
for ad,mut in [("yalnız giden kenar",lambda k,t,u:{"derece":len([v for a,v in k if a==u]),"farkli_topluluk":0,"oran":0.0}),("oran hep sıfır",lambda k,t,u:dict(topluluklar_arasi_oran(k,t,u),oran=0.0)),("derece iki kat",lambda k,t,u:dict(topluluklar_arasi_oran(k,t,u),derece=topluluklar_arasi_oran(k,t,u)["derece"]+1))]:
    ok(not sinama1(mut),"mutant reddedildi: "+ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(topluluklar_arasi_oran, _il.import_module('ai_gercek_ai_savunma_41').referans_oran, ([['kimlik_dogrulama', 'oauth_servisi'], ['oauth_servisi', 'token_dogrulayici'], ['odeme_ag_gecidi', 'fatura_motoru'], ['fatura_motoru', 'vergi_hesaplayici'], ['sahte_kopru_dugumu', 'kimlik_dogrulama'], ['sahte_kopru_dugumu', 'odeme_ag_gecidi'], ['sahte_kopru_dugumu', 'fatura_motoru'], ['denetim_kaydi', 'kimlik_dogrulama'], ['denetim_kaydi', 'odeme_ag_gecidi']], {'kimlik_dogrulama': 'kimlik', 'oauth_servisi': 'kimlik', 'token_dogrulayici': 'kimlik', 'odeme_ag_gecidi': 'finans', 'fatura_motoru': 'finans', 'vergi_hesaplayici': 'finans', 'sahte_kopru_dugumu': 'kimlik', 'denetim_kaydi': 'kimlik'}, 'kimlik_dogrulama'), tohum=3521)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
def topluluklar_arasi_oran(kenarlar,topluluklar,dugum):
    if not isinstance(kenarlar,list) or not kenarlar or not isinstance(topluluklar,dict) or not topluluklar or not isinstance(dugum,str) or not dugum.strip():raise ValueError("girdi")
    for k,v in topluluklar.items():
        if not isinstance(k,str) or not k.strip() or not isinstance(v,str) or not v.strip():raise ValueError("topluluk")
    if dugum not in topluluklar:raise ValueError("dugum")
    komsular=set()
    for e in kenarlar:
        if not isinstance(e,list) or len(e)!=2 or not isinstance(e[0],str) or not isinstance(e[1],str) or not e[0].strip() or not e[1].strip() or e[0]==e[1]:raise ValueError("kenar")
        if e[0] not in topluluklar or e[1] not in topluluklar:raise ValueError("bilinmeyen")
        if e[0]==dugum:komsular.add(e[1])
        elif e[1]==dugum:komsular.add(e[0])
    d=len(komsular)
    if d==0:return {"derece":0,"farkli_topluluk":0,"oran":0.0}
    f=sum(1 for v in komsular if topluluklar[v]!=topluluklar[dugum])
    return {"derece":d,"farkli_topluluk":f,"oran":f/d}

from ai_savunma_veri import json_yukle
v=json_yukle("veri/graphrag_savunma.json")
for d in ("kimlik_dogrulama","sahte_kopru_dugumu","denetim_kaydi"):
    print(d,topluluklar_arasi_oran(v["kenarlar"],v["topluluklar"],d))
```
```hint
Her kenarda `e[0] == dugum` ise `e[1]`'i, `e[1] == dugum` ise `e[0]`'ı bir `set` içine ekle; böylece yönsüz ve tekrarsız komşu kümesini bulursun.
```
:::

::: anlat Kaynak itibarı ve bağımsız tanık sayısı
Saldırgan aynı zehirli belge kimliğini (`dis_wiki_99`) düğüm listesine üç kez yazarak çok kaynaklı görünmeye çalışabilir. Bu yüzden her düğümün kaynak belgeleri önce tekilleştirilmeli (`set`), ardından:
- Tekil kaynakların ortalama güven skoru `< min_guven` **veya**
- Tekil kaynak sayısı `< min_kaynak_sayisi`
olan düğümler şüpheli olarak işaretlenmelidir.

**Görev 2'de sık tuzaklar:** Tekrarlı belge kimliklerini `set` ile tekilleştirmeden `len(belgeler)` almak sahte çoklu-kaynak yanılsamasına kanar.
:::

::: gorev 2 · Kaynak itibar filtresi (`kaynak_itibar_filtresi`)
`kaynak_itibar_filtresi(dugum_kaynaklari,guven_skorlari,min_guven,min_kaynak_sayisi)`: `dugum_kaynaklari` boş olmayan `str -> dolu str listesi` sözlüğü; `guven_skorlari` boş olmayan `str -> [0,1] sayı` sözlüğü; `0 <= min_guven <= 1` sayı, `min_kaynak_sayisi >= 1` int. Tekil kaynak ortalaması `< min_guven` veya tekil kaynak sayısı `< min_kaynak_sayisi` olan düğümleri alfabetik sıralı listede döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-41")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def kaynak_itibar_filtresi(dugum_kaynaklari,guven_skorlari,min_guven,min_kaynak_sayisi):
    return sorted(u for u,b in dugum_kaynaklari.items() if sum(guven_skorlari[x] for x in b)/len(b)<min_guven)

from ai_savunma_veri import json_yukle
v=json_yukle("veri/graphrag_savunma.json")
print("Şüpheli düğümler:",kaynak_itibar_filtresi(v["dugum_kaynaklari"],v["guven_skorlari"],v["min_guven"],v["min_kaynak_sayisi"]))
```
```test
def sinama2(f):
    import copy,math
    try:
        dk={"d1":["b1","b2"],"d2":["b1","b1"],"d3":["b3","b2"]};gs={"b1":0.9,"b2":0.8,"b3":0.2}
        old=(copy.deepcopy(dk),dict(gs))
        if f(dk,gs,0.7,2)!=["d2","d3"] or (dk,gs)!=old:return False
        if f(dk,gs,0.5,2)!=["d2"]:return False
        if f(dk,gs,0.7,1)!=["d3"]:return False
        if f(dk,gs,0.95,1)!=["d1","d2","d3"]:return False
        if f({"esit":["x","y"]},{"x":0.5,"y":1.0},0.75,2)!=[]:return False
        if f({"esit":["x","y"]},{"x":0.5,"y":1.0},math.nextafter(0.75,1.0),2)!=["esit"]:return False
        if f({"sifir":["x"]},{"x":0.0},0.0,1)!=[]:return False
        if f({"bir":["x"]},{"x":1.0},1.0,1)!=[]:return False

        for bad in ((None,gs,0.5,1),(dk,None,0.5,1),({},gs,0.5,1),(dk,{},0.5,1),({"d1":[]},gs,0.5,1),({"d1":["yok"]},gs,0.5,1),(dk,{"b1":1.5,"b2":0.8,"b3":0.2},0.5,1),(dk,{"b1":True,"b2":0.8,"b3":0.2},0.5,1),(dk,gs,-0.1,1),(dk,gs,1.1,1),(dk,gs,True,1),(dk,gs,0.5,0),(dk,gs,0.5,True)):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama2(kaynak_itibar_filtresi),"tekil kaynak sayısı, ortalama güven ve geçersiz girdi")
for ad,mut in [("kaynak sayısı kontrolü yok",lambda dk,gs,mg,mk:kaynak_itibar_filtresi(dk,gs,mg,1)),("boş liste",lambda dk,gs,mg,mk:[]),("tüm düğümler",lambda dk,gs,mg,mk:sorted(dk))]:
    ok(not sinama2(mut),"mutant reddedildi: "+ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(kaynak_itibar_filtresi, _il.import_module('ai_gercek_ai_savunma_41').referans_filtre, ({'kimlik_dogrulama': ['dok_1', 'dok_2'], 'oauth_servisi': ['dok_1', 'dok_2'], 'token_dogrulayici': ['dok_1', 'dok_3'], 'odeme_ag_gecidi': ['dok_4', 'dok_5'], 'fatura_motoru': ['dok_4', 'dok_5'], 'vergi_hesaplayici': ['dok_4', 'dok_5'], 'sahte_kopru_dugumu': ['dis_wiki_99'], 'denetim_kaydi': ['dok_1', 'dok_4']}, {'dok_1': 0.95, 'dok_2': 0.9, 'dok_3': 0.88, 'dok_4': 0.92, 'dok_5': 0.91, 'dis_wiki_99': 0.2}, 0.7, 2), tohum=3486)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def kaynak_itibar_filtresi(dugum_kaynaklari,guven_skorlari,min_guven,min_kaynak_sayisi):
    if not isinstance(dugum_kaynaklari,dict) or not dugum_kaynaklari or not isinstance(guven_skorlari,dict) or not guven_skorlari:raise ValueError("sozluk")
    if isinstance(min_guven,bool) or not isinstance(min_guven,(int,float)) or not math.isfinite(min_guven) or not 0<=min_guven<=1:raise ValueError("min_guven")
    if isinstance(min_kaynak_sayisi,bool) or not isinstance(min_kaynak_sayisi,int) or min_kaynak_sayisi<1:raise ValueError("min_kaynak")
    for k,s in guven_skorlari.items():
        if not isinstance(k,str) or not k.strip() or isinstance(s,bool) or not isinstance(s,(int,float)) or not math.isfinite(s) or not 0<=s<=1:raise ValueError("skor")
    supheli=[]
    for u,belgeler in dugum_kaynaklari.items():
        if not isinstance(u,str) or not u.strip() or not isinstance(belgeler,list) or not belgeler:raise ValueError("dugum")
        tekil=set()
        for b in belgeler:
            if not isinstance(b,str) or not b.strip() or b not in guven_skorlari:raise ValueError("belge")
            tekil.add(b)
        ort=sum(guven_skorlari[b] for b in tekil)/len(tekil)
        if ort<min_guven or len(tekil)<min_kaynak_sayisi:supheli.append(u)
    return sorted(supheli)

from ai_savunma_veri import json_yukle
v=json_yukle("veri/graphrag_savunma.json")
print("Şüpheli düğümler:",kaynak_itibar_filtresi(v["dugum_kaynaklari"],v["guven_skorlari"],v["min_guven"],v["min_kaynak_sayisi"]))
```
```hint
Her düğümün belge listesini `set(belgeler)` ile tekilleştir; hem `len(tekil) < min_kaynak_sayisi` hem de ortalama güven `< min_guven` durumunu kontrol et.
```
:::

::: anlat Çift koşullu köprü karantinası
Şimdi iki sinyali birleştiriyoruz: bir düğüm **hem** `topluluklar_arasi_oran >= oran_esik` koşulunu sağlıyor **hem de** `kaynak_itibar_filtresi` tarafından şüpheli bulunuyorsa karantinaya alınır. Karantinaya alınan düğümlerin uç olduğu tüm kenarlar çizgeden kesilir. Böylece `denetim_kaydi` gibi yüksek itibarlı meşru köprüler korunurken `sahte_kopru_dugumu` çizgeden izole edilir.

Şüpheli kümesi boş olsa da çizge şeması doğrulanmalıdır. Aksi halde `u in supheli and ...` kısa devresi topluluk/kenar kontrolünü atlar ve yüksek itibar bozuk girdiyi meşrulaştırır.

**Görev 3'te sık tuzaklar:** `VE` yerine `VEYA` kullanmak meşru köprüleri de siler. `topluluklar` ile `dugum_kaynaklari` anahtar kümelerinin birebir aynı olduğu doğrulanmalıdır.
:::

::: gorev 3 · Çizge karantina raporu (`cizge_karantina_raporu`)
`cizge_karantina_raporu(kenarlar,topluluklar,dugum_kaynaklari,guven_skorlari,oran_esik,min_guven,min_kaynak_sayisi)`: `set(topluluklar)==set(dugum_kaynaklari)` ve `0 < oran_esik <= 1`. Hem topluluklar arası oranı `>= oran_esik` olan hem de kaynak filtresine takılan düğümleri `karantina_dugumleri` (alfabetik) olarak ayır; bu düğümlere değmeyen kenarları `temiz_kenarlar` içinde koru ve `{"karantina_dugumleri":..., "temiz_kenar_sayisi":..., "elenen_kenar_sayisi":..., "temiz_kenarlar":...}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-41")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def cizge_karantina_raporu(kenarlar,topluluklar,dugum_kaynaklari,guven_skorlari,oran_esik,min_guven,min_kaynak_sayisi):
    karantina=[]
    for u in sorted(topluluklar):
        komsu=[v if a==u else a for a,v in kenarlar if u in (a,v)]
        oran=sum(1 for v in komsu if topluluklar[v]!=topluluklar[u])/len(komsu) if komsu else 0.0
        if oran>=oran_esik:karantina.append(u)
    temiz=[list(e) for e in kenarlar if e[0] not in karantina and e[1] not in karantina]
    return {"karantina_dugumleri":karantina,"temiz_kenar_sayisi":len(temiz),"elenen_kenar_sayisi":len(kenarlar)-len(temiz),"temiz_kenarlar":temiz}

from ai_savunma_veri import json_yukle
v=json_yukle("veri/graphrag_savunma.json")
print(cizge_karantina_raporu(v["kenarlar"],v["topluluklar"],v["dugum_kaynaklari"],v["guven_skorlari"],v["oran_esik"],v["min_guven"],v["min_kaynak_sayisi"]))
```
```test
def sinama3(f):
    import copy
    try:
        k=[["a","b"],["b","c"],["z","a"],["z","c"],["m","a"],["m","c"]]
        t={"a":"T1","b":"T1","c":"T2","z":"T1","m":"T1"}
        dk={"a":["d1","d2"],"b":["d1","d2"],"c":["d1","d2"],"z":["d_kotu"],"m":["d1","d2"]}
        gs={"d1":0.9,"d2":0.85,"d_kotu":0.2}
        old=(copy.deepcopy(k),dict(t),copy.deepcopy(dk),dict(gs))
        r=f(k,t,dk,gs,0.5,0.7,2)
        if (k,t,dk,gs)!=old:return False
        if r!={"karantina_dugumleri":["z"],"temiz_kenar_sayisi":4,"elenen_kenar_sayisi":2,"temiz_kenarlar":[["a","b"],["b","c"],["m","a"],["m","c"]]}:return False
        # Kaynak filtresinin boş şüpheli kümesi çizge doğrulamasını atlatmamalı.
        guvenli={u:["iyi"] for u in ("a","b")};tt={"a":"T1","b":"T2"}
        for kk,top in (([],tt),([["a","a"]],tt),([["a","b"]],{"a":5,"b":"T2"})):
            try:
                f(kk,top,guvenli,{"iyi":1.0},0.5,0.5,1)
                return False
            except ValueError:
                pass
        if f(k,t,dk,gs,0.5000000000000001,0.7,2)["karantina_dugumleri"]!=[]:return False
        r2=f(k,t,dk,gs,0.9,0.7,2)
        if r2["karantina_dugumleri"]!=[] or r2["elenen_kenar_sayisi"]!=0:return False
        for bad in ((k,t,{"a":["d1"]},gs,0.5,0.7,2),(k,{},{},gs,0.5,0.7,2),(k,t,dk,gs,0.0,0.7,2),(k,t,dk,gs,1.2,0.7,2),(k,t,dk,gs,True,0.7,2)):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama3(cizge_karantina_raporu),"çift koşullu köprü karantinası, kenar temizliği ve geçersiz girdi")
for ad,mut in [("yalnız oran",lambda k,t,dk,gs,oe,mg,mk:cizge_karantina_raporu(k,t,dk,gs,oe,1.0,99)),("hiç karantina yok",lambda k,t,dk,gs,oe,mg,mk:{"karantina_dugumleri":[],"temiz_kenar_sayisi":len(k),"elenen_kenar_sayisi":0,"temiz_kenarlar":list(k)}),("kenar silmez",lambda k,t,dk,gs,oe,mg,mk:dict(cizge_karantina_raporu(k,t,dk,gs,oe,mg,mk),temiz_kenar_sayisi=len(k),elenen_kenar_sayisi=0))]:
    ok(not sinama3(mut),"mutant reddedildi: "+ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(cizge_karantina_raporu, _il.import_module('ai_gercek_ai_savunma_41').referans_karantina, ([['kimlik_dogrulama', 'oauth_servisi'], ['oauth_servisi', 'token_dogrulayici'], ['odeme_ag_gecidi', 'fatura_motoru'], ['fatura_motoru', 'vergi_hesaplayici'], ['sahte_kopru_dugumu', 'kimlik_dogrulama'], ['sahte_kopru_dugumu', 'odeme_ag_gecidi'], ['sahte_kopru_dugumu', 'fatura_motoru'], ['denetim_kaydi', 'kimlik_dogrulama'], ['denetim_kaydi', 'odeme_ag_gecidi']], {'kimlik_dogrulama': 'kimlik', 'oauth_servisi': 'kimlik', 'token_dogrulayici': 'kimlik', 'odeme_ag_gecidi': 'finans', 'fatura_motoru': 'finans', 'vergi_hesaplayici': 'finans', 'sahte_kopru_dugumu': 'kimlik', 'denetim_kaydi': 'kimlik'}, {'kimlik_dogrulama': ['dok_1', 'dok_2'], 'oauth_servisi': ['dok_1', 'dok_2'], 'token_dogrulayici': ['dok_1', 'dok_3'], 'odeme_ag_gecidi': ['dok_4', 'dok_5'], 'fatura_motoru': ['dok_4', 'dok_5'], 'vergi_hesaplayici': ['dok_4', 'dok_5'], 'sahte_kopru_dugumu': ['dis_wiki_99'], 'denetim_kaydi': ['dok_1', 'dok_4']}, {'dok_1': 0.95, 'dok_2': 0.9, 'dok_3': 0.88, 'dok_4': 0.92, 'dok_5': 0.91, 'dis_wiki_99': 0.2}, 0.5, 0.7, 2), tohum=3494)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(topluluklar_arasi_oran, _il.import_module('ai_gercek_ai_savunma_41').referans_oran, ([['kimlik_dogrulama', 'oauth_servisi'], ['oauth_servisi', 'token_dogrulayici'], ['odeme_ag_gecidi', 'fatura_motoru'], ['fatura_motoru', 'vergi_hesaplayici'], ['sahte_kopru_dugumu', 'kimlik_dogrulama'], ['sahte_kopru_dugumu', 'odeme_ag_gecidi'], ['sahte_kopru_dugumu', 'fatura_motoru'], ['denetim_kaydi', 'kimlik_dogrulama'], ['denetim_kaydi', 'odeme_ag_gecidi']], {'kimlik_dogrulama': 'kimlik', 'oauth_servisi': 'kimlik', 'token_dogrulayici': 'kimlik', 'odeme_ag_gecidi': 'finans', 'fatura_motoru': 'finans', 'vergi_hesaplayici': 'finans', 'sahte_kopru_dugumu': 'kimlik', 'denetim_kaydi': 'kimlik'}, 'kimlik_dogrulama'), tohum=3521)
ok(_t, "farksal tarama (topluluklar_arasi_oran): bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(kaynak_itibar_filtresi, _il.import_module('ai_gercek_ai_savunma_41').referans_filtre, ({'kimlik_dogrulama': ['dok_1', 'dok_2'], 'oauth_servisi': ['dok_1', 'dok_2'], 'token_dogrulayici': ['dok_1', 'dok_3'], 'odeme_ag_gecidi': ['dok_4', 'dok_5'], 'fatura_motoru': ['dok_4', 'dok_5'], 'vergi_hesaplayici': ['dok_4', 'dok_5'], 'sahte_kopru_dugumu': ['dis_wiki_99'], 'denetim_kaydi': ['dok_1', 'dok_4']}, {'dok_1': 0.95, 'dok_2': 0.9, 'dok_3': 0.88, 'dok_4': 0.92, 'dok_5': 0.91, 'dis_wiki_99': 0.2}, 0.7, 2), tohum=3486)
ok(_t, "farksal tarama (kaynak_itibar_filtresi): bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
eq(topluluklar_arasi_oran([["a","b"]],{"a":"T1","b":"T1","iso":"T1"},"iso"),{"derece":0,"farkli_topluluk":0,"oran":0.0},"izole düğüm derecesi ve oranı")
```
```solution
import math
def topluluklar_arasi_oran(kenarlar,topluluklar,dugum):
    if not isinstance(kenarlar,list) or not kenarlar or not isinstance(topluluklar,dict) or not topluluklar or not isinstance(dugum,str) or not dugum.strip():raise ValueError("girdi")
    for k,v in topluluklar.items():
        if not isinstance(k,str) or not k.strip() or not isinstance(v,str) or not v.strip():raise ValueError("topluluk")
    if dugum not in topluluklar:raise ValueError("dugum")
    komsular=set()
    for e in kenarlar:
        if not isinstance(e,list) or len(e)!=2 or not isinstance(e[0],str) or not isinstance(e[1],str) or not e[0].strip() or not e[1].strip() or e[0]==e[1]:raise ValueError("kenar")
        if e[0] not in topluluklar or e[1] not in topluluklar:raise ValueError("bilinmeyen")
        if e[0]==dugum:komsular.add(e[1])
        elif e[1]==dugum:komsular.add(e[0])
    d=len(komsular)
    if d==0:return {"derece":0,"farkli_topluluk":0,"oran":0.0}
    f=sum(1 for v in komsular if topluluklar[v]!=topluluklar[dugum])
    return {"derece":d,"farkli_topluluk":f,"oran":f/d}

def kaynak_itibar_filtresi(dugum_kaynaklari,guven_skorlari,min_guven,min_kaynak_sayisi):
    if not isinstance(dugum_kaynaklari,dict) or not dugum_kaynaklari or not isinstance(guven_skorlari,dict) or not guven_skorlari:raise ValueError("sozluk")
    if isinstance(min_guven,bool) or not isinstance(min_guven,(int,float)) or not math.isfinite(min_guven) or not 0<=min_guven<=1:raise ValueError("min_guven")
    if isinstance(min_kaynak_sayisi,bool) or not isinstance(min_kaynak_sayisi,int) or min_kaynak_sayisi<1:raise ValueError("min_kaynak")
    for k,s in guven_skorlari.items():
        if not isinstance(k,str) or not k.strip() or isinstance(s,bool) or not isinstance(s,(int,float)) or not math.isfinite(s) or not 0<=s<=1:raise ValueError("skor")
    supheli=[]
    for u,belgeler in dugum_kaynaklari.items():
        if not isinstance(u,str) or not u.strip() or not isinstance(belgeler,list) or not belgeler:raise ValueError("dugum")
        tekil=set()
        for b in belgeler:
            if not isinstance(b,str) or not b.strip() or b not in guven_skorlari:raise ValueError("belge")
            tekil.add(b)
        ort=sum(guven_skorlari[b] for b in tekil)/len(tekil)
        if ort<min_guven or len(tekil)<min_kaynak_sayisi:supheli.append(u)
    return sorted(supheli)

def cizge_karantina_raporu(kenarlar,topluluklar,dugum_kaynaklari,guven_skorlari,oran_esik,min_guven,min_kaynak_sayisi):
    if isinstance(oran_esik,bool) or not isinstance(oran_esik,(int,float)) or not math.isfinite(oran_esik) or not 0<oran_esik<=1:raise ValueError("oran_esik")
    if not isinstance(topluluklar,dict) or not isinstance(dugum_kaynaklari,dict) or set(topluluklar)!=set(dugum_kaynaklari):raise ValueError("kume")
    supheli=set(kaynak_itibar_filtresi(dugum_kaynaklari,guven_skorlari,min_guven,min_kaynak_sayisi))
    topluluklar_arasi_oran(kenarlar,topluluklar,next(iter(topluluklar)))  # Şüpheli kümesi boş olsa da çizgeyi doğrula.
    karantina=sorted(u for u in topluluklar if u in supheli and topluluklar_arasi_oran(kenarlar,topluluklar,u)["oran"]>=oran_esik)
    kset=set(karantina)
    temiz=[[e[0],e[1]] for e in kenarlar if e[0] not in kset and e[1] not in kset]
    return {"karantina_dugumleri":karantina,"temiz_kenar_sayisi":len(temiz),"elenen_kenar_sayisi":len(kenarlar)-len(temiz),"temiz_kenarlar":temiz}

from ai_savunma_veri import json_yukle
v=json_yukle("veri/graphrag_savunma.json")
print(cizge_karantina_raporu(v["kenarlar"],v["topluluklar"],v["dugum_kaynaklari"],v["guven_skorlari"],v["oran_esik"],v["min_guven"],v["min_kaynak_sayisi"]))
```
```hint
Önce `kaynak_itibar_filtresi` ile şüpheli kümesini bul, ardından her düğüm için `topluluklar_arasi_oran` çağırıp iki koşulun kesişimini al.
```
:::

::: anlat Hata vitrini · çalışmış yanlış rapor
Yazar, kusurlu başlangıç kodlarını görünür sentetik veriyle gerçekten çalıştırdı ve sonucu `outputs/yeni-ai-savunma-41/gorunur-run-1.json` dosyasına kaydetti. Kusurlu 3. görev kodu kaynak itibarına bakmadan yalnızca `oran >= 0.5` koşulunu kullandığı için kurumsal `denetim_kaydi` düğümünü de karantinaya alır (`karantina_dugumleri=['denetim_kaydi', 'sahte_kopru_dugumu']`) ve 5 kenarı siler. Doğru kod ise yalnız `sahte_kopru_dugumu` düğümünü karantinaya alır ve meşru denetim bağlarını korur.

Bu kaydedilmiş bir hesaplama çıktısıdır, model yanıtı değildir ve rapor sentetiktir. Meşru köprülerin yanlışlıkla silinmesi çok adımlı sorularda ne tür bir hizmet kesintisine (`availability loss`) yol açar? Kendi cümlenle açıkla. Gerçek finaldeki ölçüm ayrıca üretilir; bu sayılar onun yerine konmaz.
:::

::: anlat Gerçek deney: yerel LLM ile kurulan GraphRAG indeksinde köprü karantinası
Final, ai-saldiri-60'taki gerçek GraphRAG hattını kullanır:
- **Bilgi tabanı:** "Orion Labs"ın 8 iç belgesi ve saldırganın içe alınmış 2 dış forum sayfası.
- **İndeks:** Varlıkları Ollama `qwen3:4b-instruct` çıkarır; aynı belgede geçenler arasına kenar konur.
- **Arama ve cevap:** Yerel arama `all-minilm` gömmeleriyle yapılır, aynı model cevap yazar.
- **Kaynak itibarı:** İç belgeler 0.82–0.98, dış forum sayfaları 0.12–0.35. Gerçek sistemde bu kaynak kataloğundan gelir.

Senin işlevlerin bu gerçek çizgede çalışır. `cizge_karantina_raporu`'nun kararı uygulanır: karantinadaki düğümler ve kenarları aramadan çıkarılır, o düğümü üreten **düşük itibarlı** belgeler de bağlamdan atılır. Dört konu sorusu karantinadan önce ve sonra sorulur.

**Birinci bulgu: zehirli çizgenin kendi toplulukları savunmayı kör eder.** Topluluklar zehirli çizgenin üzerinde (Louvain) hesaplandığında sahte köprü topluluk yapısını kendine göre büker. Yazarın koşularında kimlik ve finans varlıkları zehirli belgelerle tek bir topluluğa karıştı. `quicksync helper`'ın topluluklar arası oranı yalnız **0.25** çıktı ve karantina boş kaldı. Zehirli bağlam (2/4) ve cevaptaki oltalama adresi (1/4) aynen sürdü.

**Çözüm: referans yapıyı yalnız güvenilir veriden kur.** Topluluklar yalnız itibarı ≥ 0.65 olan belgelerin kenarlarından hesaplanır. Yalnız güvenilmeyen kaynaklarda görülen düğümler hiçbir güvenilir topluluğa ait sayılmaz. Bu durumda zehirli düğümlerin bütün komşuları "başka topluluk"tur, oran 1.0 olur. Yazarın dört koşusunun dördünde de şu sonuçlar alındı:
- İki zehirli düğüm (`quicksync helper`, `quicksync-helper.example`) karantinaya alındı; kaçan yok.
- İki dış belge bağlamdan çıktı.
- Zehirli bağlam 2/4 → 0/4, cevapta saldırgan adresi 1/4 → 0/4.
- Her sorgunun kendi konusundaki iç belge bağlamda kaldı (4/4 → 4/4).
- Meşru köprüler (`security operations center`, `service desk`, `orion labs`) karantinaya alınmadı.

**Bedel: yanlış karantina.** Dört koşudan birinde dış belgelere düşük itibar puanları çekildi. Zehirli belgelerin **andığı** meşru varlıkların (okta, service desk, iam team, snowflake) itibar ortalaması 0.65'in altına indi ve bunlar da karantinaya alındı. İç belgeler yalnız düşük itibarlı kaynaklar dışlandığı için bağlamda kaldı ve hizmet kaybı olmadı. Ama bu düğümler çizgeden düştü. Zehirli belge, andığı meşru varlıkların itibarını da kirletir.

**Kanıt dosyasını oku:** Soru 1: `ham_topluluklar.zehirli_oranlari` ile güvenilir topluluklardaki oran neden bu kadar farklı? Topluluk algılamanın hangi özelliği saldırgana yarıyor? Soru 2: Saldırgan dış kaynak yerine meşru iki iç belgeye yazma yetkisi kazansaydı bu filtre ne yapardı? Soru 3: Yanlış karantinayı azaltmak için itibar ortalaması yerine hangi kural (ör. "en az bir yüksek itibarlı kaynak yeter") kullanılabilir, bunun riski ne? Cevabını tezgâhta yorum olarak yaz; otomatik test bu serbest açıklamayı puanlamaz.
:::

::: gorev Gerçek deney · GPU'da GraphRAG köprü karantinası ve bulaşma ölçümü
Önceki üç görevin `topluluklar_arasi_oran`, `kaynak_itibar_filtresi` ve `cizge_karantina_raporu` işlevlerini birleştir. Çalıştır gerçek çizge yayılım tablosunu gösterir; Kontrol Et önce üç sözleşmeyi gizli verilerle sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
ortam: gpu
timeout: 180
```
```starter
import ai_lab
import math
def topluluklar_arasi_oran(kenarlar,topluluklar,dugum):
    return {"derece":0,"farkli_topluluk":0,"oran":0.0}
def kaynak_itibar_filtresi(dugum_kaynaklari,guven_skorlari,min_guven,min_kaynak_sayisi):
    return []
def cizge_karantina_raporu(kenarlar,topluluklar,dugum_kaynaklari,guven_skorlari,oran_esik,min_guven,min_kaynak_sayisi):
    return {"karantina_dugumleri":[],"temiz_kenar_sayisi":len(kenarlar),"elenen_kenar_sayisi":0,"temiz_kenarlar":list(kenarlar)}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_41 as D
    D.goster(topluluklar_arasi_oran,kaynak_itibar_filtresi,cizge_karantina_raporu)
```
```test
import ai_lab,math
checks=[]
def kontrol(x,m):checks.append(bool(x));ok(x,m)
issues=ai_lab.kod_denetimi(src,('referans_oran', 'referans_filtre', 'referans_karantina', 'kanit_yaz', '_yakin'),izin=())
kontrol(not issues,"kopya/yama/dinamik kod yok: "+str(issues))
if issues:stop()
topluluklar_arasi_oran=need("topluluklar_arasi_oran")
kaynak_itibar_filtresi=need("kaynak_itibar_filtresi")
cizge_karantina_raporu=need("cizge_karantina_raporu")
def sinama1(f):
    import copy
    try:
        k=[["a","b"],["b","a"],["a","c"],["c","d"]];t={"a":"T1","b":"T1","c":"T2","d":"T2","yalniz":"T1"}
        old=(copy.deepcopy(k),dict(t))
        if f(k,t,"a")!={"derece":2,"farkli_topluluk":1,"oran":0.5} or (k,t)!=old:return False
        if f(k,t,"c")!={"derece":2,"farkli_topluluk":1,"oran":0.5}:return False
        if f(k,t,"d")!={"derece":1,"farkli_topluluk":0,"oran":0.0}:return False
        if f(k,t,"yalniz")!={"derece":0,"farkli_topluluk":0,"oran":0.0}:return False
        for bad in ((None,t,"a"),([],t,"a"),(k,{},"a"),(k,t,"yok"),(k,t,""),([["a","a"]],t,"a"),([["a","z"]],t,"a"),([["a"]],t,"a"),([("a","b")],t,"a"),(k,{"a":""},"a"),(k,t,None)):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
kontrol(sinama1(topluluklar_arasi_oran),"yönsüz tekil komşuluk, farklı topluluk oranı ve geçersiz girdi")
for ad,mut in [("yalnız giden kenar",lambda k,t,u:{"derece":len([v for a,v in k if a==u]),"farkli_topluluk":0,"oran":0.0}),("oran hep sıfır",lambda k,t,u:dict(topluluklar_arasi_oran(k,t,u),oran=0.0)),("derece iki kat",lambda k,t,u:dict(topluluklar_arasi_oran(k,t,u),derece=topluluklar_arasi_oran(k,t,u)["derece"]+1))]:
    kontrol(not sinama1(mut),"mutant reddedildi: "+ad)
def sinama2(f):
    import copy,math
    try:
        dk={"d1":["b1","b2"],"d2":["b1","b1"],"d3":["b3","b2"]};gs={"b1":0.9,"b2":0.8,"b3":0.2}
        old=(copy.deepcopy(dk),dict(gs))
        if f(dk,gs,0.7,2)!=["d2","d3"] or (dk,gs)!=old:return False
        if f(dk,gs,0.5,2)!=["d2"]:return False
        if f(dk,gs,0.7,1)!=["d3"]:return False
        if f(dk,gs,0.95,1)!=["d1","d2","d3"]:return False
        if f({"esit":["x","y"]},{"x":0.5,"y":1.0},0.75,2)!=[]:return False
        if f({"esit":["x","y"]},{"x":0.5,"y":1.0},math.nextafter(0.75,1.0),2)!=["esit"]:return False
        if f({"sifir":["x"]},{"x":0.0},0.0,1)!=[]:return False
        if f({"bir":["x"]},{"x":1.0},1.0,1)!=[]:return False

        for bad in ((None,gs,0.5,1),(dk,None,0.5,1),({},gs,0.5,1),(dk,{},0.5,1),({"d1":[]},gs,0.5,1),({"d1":["yok"]},gs,0.5,1),(dk,{"b1":1.5,"b2":0.8,"b3":0.2},0.5,1),(dk,{"b1":True,"b2":0.8,"b3":0.2},0.5,1),(dk,gs,-0.1,1),(dk,gs,1.1,1),(dk,gs,True,1),(dk,gs,0.5,0),(dk,gs,0.5,True)):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
kontrol(sinama2(kaynak_itibar_filtresi),"tekil kaynak sayısı, ortalama güven ve geçersiz girdi")
for ad,mut in [("kaynak sayısı kontrolü yok",lambda dk,gs,mg,mk:kaynak_itibar_filtresi(dk,gs,mg,1)),("boş liste",lambda dk,gs,mg,mk:[]),("tüm düğümler",lambda dk,gs,mg,mk:sorted(dk))]:
    kontrol(not sinama2(mut),"mutant reddedildi: "+ad)
def sinama3(f):
    import copy
    try:
        k=[["a","b"],["b","c"],["z","a"],["z","c"],["m","a"],["m","c"]]
        t={"a":"T1","b":"T1","c":"T2","z":"T1","m":"T1"}
        dk={"a":["d1","d2"],"b":["d1","d2"],"c":["d1","d2"],"z":["d_kotu"],"m":["d1","d2"]}
        gs={"d1":0.9,"d2":0.85,"d_kotu":0.2}
        old=(copy.deepcopy(k),dict(t),copy.deepcopy(dk),dict(gs))
        r=f(k,t,dk,gs,0.5,0.7,2)
        if (k,t,dk,gs)!=old:return False
        if r!={"karantina_dugumleri":["z"],"temiz_kenar_sayisi":4,"elenen_kenar_sayisi":2,"temiz_kenarlar":[["a","b"],["b","c"],["m","a"],["m","c"]]}:return False
        # Kaynak filtresinin boş şüpheli kümesi çizge doğrulamasını atlatmamalı.
        guvenli={u:["iyi"] for u in ("a","b")};tt={"a":"T1","b":"T2"}
        for kk,top in (([],tt),([["a","a"]],tt),([["a","b"]],{"a":5,"b":"T2"})):
            try:
                f(kk,top,guvenli,{"iyi":1.0},0.5,0.5,1)
                return False
            except ValueError:
                pass
        if f(k,t,dk,gs,0.5000000000000001,0.7,2)["karantina_dugumleri"]!=[]:return False
        r2=f(k,t,dk,gs,0.9,0.7,2)
        if r2["karantina_dugumleri"]!=[] or r2["elenen_kenar_sayisi"]!=0:return False
        for bad in ((k,t,{"a":["d1"]},gs,0.5,0.7,2),(k,{},{},gs,0.5,0.7,2),(k,t,dk,gs,0.0,0.7,2),(k,t,dk,gs,1.2,0.7,2),(k,t,dk,gs,True,0.7,2)):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
kontrol(sinama3(cizge_karantina_raporu),"çift koşullu köprü karantinası, kenar temizliği ve geçersiz girdi")
for ad,mut in [("yalnız oran",lambda k,t,dk,gs,oe,mg,mk:cizge_karantina_raporu(k,t,dk,gs,oe,1.0,99)),("hiç karantina yok",lambda k,t,dk,gs,oe,mg,mk:{"karantina_dugumleri":[],"temiz_kenar_sayisi":len(k),"elenen_kenar_sayisi":0,"temiz_kenarlar":list(k)}),("kenar silmez",lambda k,t,dk,gs,oe,mg,mk:dict(cizge_karantina_raporu(k,t,dk,gs,oe,mg,mk),temiz_kenar_sayisi=len(k),elenen_kenar_sayisi=0))]:
    kontrol(not sinama3(mut),"mutant reddedildi: "+ad)
# farksal tarama (final)
import importlib as _il
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_R = _il.import_module('sandbox.ai_gercek_ai_savunma_41')
for _ad, _ref, _taban, _toh in (
    ('topluluklar_arasi_oran', 'referans_oran', ([['kimlik_dogrulama', 'oauth_servisi'], ['oauth_servisi', 'token_dogrulayici'], ['odeme_ag_gecidi', 'fatura_motoru'], ['fatura_motoru', 'vergi_hesaplayici'], ['sahte_kopru_dugumu', 'kimlik_dogrulama'], ['sahte_kopru_dugumu', 'odeme_ag_gecidi'], ['sahte_kopru_dugumu', 'fatura_motoru'], ['denetim_kaydi', 'kimlik_dogrulama'], ['denetim_kaydi', 'odeme_ag_gecidi']], {'kimlik_dogrulama': 'kimlik', 'oauth_servisi': 'kimlik', 'token_dogrulayici': 'kimlik', 'odeme_ag_gecidi': 'finans', 'fatura_motoru': 'finans', 'vergi_hesaplayici': 'finans', 'sahte_kopru_dugumu': 'kimlik', 'denetim_kaydi': 'kimlik'}, 'kimlik_dogrulama'), 4043),
    ('kaynak_itibar_filtresi', 'referans_filtre', ({'kimlik_dogrulama': ['dok_1', 'dok_2'], 'oauth_servisi': ['dok_1', 'dok_2'], 'token_dogrulayici': ['dok_1', 'dok_3'], 'odeme_ag_gecidi': ['dok_4', 'dok_5'], 'fatura_motoru': ['dok_4', 'dok_5'], 'vergi_hesaplayici': ['dok_4', 'dok_5'], 'sahte_kopru_dugumu': ['dis_wiki_99'], 'denetim_kaydi': ['dok_1', 'dok_4']}, {'dok_1': 0.95, 'dok_2': 0.9, 'dok_3': 0.88, 'dok_4': 0.92, 'dok_5': 0.91, 'dis_wiki_99': 0.2}, 0.7, 2), 4008),
    ('cizge_karantina_raporu', 'referans_karantina', ([['kimlik_dogrulama', 'oauth_servisi'], ['oauth_servisi', 'token_dogrulayici'], ['odeme_ag_gecidi', 'fatura_motoru'], ['fatura_motoru', 'vergi_hesaplayici'], ['sahte_kopru_dugumu', 'kimlik_dogrulama'], ['sahte_kopru_dugumu', 'odeme_ag_gecidi'], ['sahte_kopru_dugumu', 'fatura_motoru'], ['denetim_kaydi', 'kimlik_dogrulama'], ['denetim_kaydi', 'odeme_ag_gecidi']], {'kimlik_dogrulama': 'kimlik', 'oauth_servisi': 'kimlik', 'token_dogrulayici': 'kimlik', 'odeme_ag_gecidi': 'finans', 'fatura_motoru': 'finans', 'vergi_hesaplayici': 'finans', 'sahte_kopru_dugumu': 'kimlik', 'denetim_kaydi': 'kimlik'}, {'kimlik_dogrulama': ['dok_1', 'dok_2'], 'oauth_servisi': ['dok_1', 'dok_2'], 'token_dogrulayici': ['dok_1', 'dok_3'], 'odeme_ag_gecidi': ['dok_4', 'dok_5'], 'fatura_motoru': ['dok_4', 'dok_5'], 'vergi_hesaplayici': ['dok_4', 'dok_5'], 'sahte_kopru_dugumu': ['dis_wiki_99'], 'denetim_kaydi': ['dok_1', 'dok_4']}, {'dok_1': 0.95, 'dok_2': 0.9, 'dok_3': 0.88, 'dok_4': 0.92, 'dok_5': 0.91, 'dis_wiki_99': 0.2}, 0.5, 0.7, 2), 4016),
):
    _t, _g = _ff(need(_ad), getattr(_R, _ref), _taban, tohum=_toh)
    kontrol(_t, "farksal tarama (" + _ad + "): bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
if not all(checks):stop()
from sandbox import ai_gercek_ai_savunma_41 as D
try:r=D.deney(topluluklar_arasi_oran,kaynak_itibar_filtresi,cizge_karantina_raporu)
except ai_lab.GercekLabYok as e:
    kontrol(False,"gerçek deney yok: "+str(e));stop()
kontrol(r["oran_ayni"],"LLM'in çıkardığı gerçek çizgede (iki topluluk yapısıyla) topluluklar arası oran ve karantina bağımsız referansla aynı")
kontrol(r["filtre_ayni"],"gerçek kaynak listelerinde itibar filtresi bağımsız referansla aynı")
kontrol(r["karantina_ayni"],"güvenilir topluluklarla çizge karantina raporu bağımsız referansla aynı")
kontrol(not r["kacan_zehirli"],"yalnız zehirli belgelerden gelen bütün düğümler karantinaya alındı: "+str(r["karantina_dugumleri"])+" | yanlış karantina: "+str(r["yanlis_karantina"]))
kontrol(r["once"]["zehirli_baglam"]>0,"karantina öncesi zehirli belge gerçek aramada bağlama girdi: %d sorgu"%r["once"]["zehirli_baglam"])
kontrol(r["sonra"]["zehirli_baglam"]==0 and r["sonra"]["kanarya_cevap"]==0,"karantina sonrası zehirli bağlam ve cevaptaki saldırgan adresi sıfırlandı: "+str(r["sonra"]))
kontrol(r["sonra"]["konu_belgesi_baglamda"]>=r["once"]["konu_belgesi_baglamda"],"karantina doğru iç belgeleri bağlamdan düşürmedi")
ai_lab.kanit_yaz("ai-savunma-41-kabul",{"kaynak":"gercek","kabul":all(checks),"ders":"ai-savunma-41","deney":r})
```
```solution
import ai_lab
import math
def topluluklar_arasi_oran(kenarlar,topluluklar,dugum):
    if not isinstance(kenarlar,list) or not kenarlar or not isinstance(topluluklar,dict) or not topluluklar or not isinstance(dugum,str) or not dugum.strip():raise ValueError("girdi")
    for k,v in topluluklar.items():
        if not isinstance(k,str) or not k.strip() or not isinstance(v,str) or not v.strip():raise ValueError("topluluk")
    if dugum not in topluluklar:raise ValueError("dugum")
    komsular=set()
    for e in kenarlar:
        if not isinstance(e,list) or len(e)!=2 or not isinstance(e[0],str) or not isinstance(e[1],str) or not e[0].strip() or not e[1].strip() or e[0]==e[1]:raise ValueError("kenar")
        if e[0] not in topluluklar or e[1] not in topluluklar:raise ValueError("bilinmeyen")
        if e[0]==dugum:komsular.add(e[1])
        elif e[1]==dugum:komsular.add(e[0])
    d=len(komsular)
    if d==0:return {"derece":0,"farkli_topluluk":0,"oran":0.0}
    f=sum(1 for v in komsular if topluluklar[v]!=topluluklar[dugum])
    return {"derece":d,"farkli_topluluk":f,"oran":f/d}
def kaynak_itibar_filtresi(dugum_kaynaklari,guven_skorlari,min_guven,min_kaynak_sayisi):
    if not isinstance(dugum_kaynaklari,dict) or not dugum_kaynaklari or not isinstance(guven_skorlari,dict) or not guven_skorlari:raise ValueError("sozluk")
    if isinstance(min_guven,bool) or not isinstance(min_guven,(int,float)) or not math.isfinite(min_guven) or not 0<=min_guven<=1:raise ValueError("min_guven")
    if isinstance(min_kaynak_sayisi,bool) or not isinstance(min_kaynak_sayisi,int) or min_kaynak_sayisi<1:raise ValueError("min_kaynak")
    for k,s in guven_skorlari.items():
        if not isinstance(k,str) or not k.strip() or isinstance(s,bool) or not isinstance(s,(int,float)) or not math.isfinite(s) or not 0<=s<=1:raise ValueError("skor")
    supheli=[]
    for u,belgeler in dugum_kaynaklari.items():
        if not isinstance(u,str) or not u.strip() or not isinstance(belgeler,list) or not belgeler:raise ValueError("dugum")
        tekil=set()
        for b in belgeler:
            if not isinstance(b,str) or not b.strip() or b not in guven_skorlari:raise ValueError("belge")
            tekil.add(b)
        ort=sum(guven_skorlari[b] for b in tekil)/len(tekil)
        if ort<min_guven or len(tekil)<min_kaynak_sayisi:supheli.append(u)
    return sorted(supheli)
def cizge_karantina_raporu(kenarlar,topluluklar,dugum_kaynaklari,guven_skorlari,oran_esik,min_guven,min_kaynak_sayisi):
    if isinstance(oran_esik,bool) or not isinstance(oran_esik,(int,float)) or not math.isfinite(oran_esik) or not 0<oran_esik<=1:raise ValueError("oran_esik")
    if not isinstance(topluluklar,dict) or not isinstance(dugum_kaynaklari,dict) or set(topluluklar)!=set(dugum_kaynaklari):raise ValueError("kume")
    supheli=set(kaynak_itibar_filtresi(dugum_kaynaklari,guven_skorlari,min_guven,min_kaynak_sayisi))
    topluluklar_arasi_oran(kenarlar,topluluklar,next(iter(topluluklar)))  # Şüpheli kümesi boş olsa da çizgeyi doğrula.
    karantina=sorted(u for u in topluluklar if u in supheli and topluluklar_arasi_oran(kenarlar,topluluklar,u)["oran"]>=oran_esik)
    kset=set(karantina)
    temiz=[[e[0],e[1]] for e in kenarlar if e[0] not in kset and e[1] not in kset]
    return {"karantina_dugumleri":karantina,"temiz_kenar_sayisi":len(temiz),"elenen_kenar_sayisi":len(kenarlar)-len(temiz),"temiz_kenarlar":temiz}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_41 as D
    D.goster(topluluklar_arasi_oran,kaynak_itibar_filtresi,cizge_karantina_raporu)
```
```hint
Üç işlevi aynen birleştir. Karantina öncesi ve sonrası top-3 bulaşma oranlarını karşılaştır.
```
:::

::: anlat Sınır
Bu ders, düşük itibarlı dış kaynaklardan enjekte edilen sahte köprü düğümlerini topolojik oran ve kaynak itibarı kesişimiyle temizler. Gerçek deney küçük bir kurgusal bilgi tabanı ve küçük bir yerel model kullanır. Kaynak itibarı deneyde verilir. Topluluklar Louvain ile bulunur (GraphRAG Leiden kullanır). Yüksek güvenilirlikli birden çok iç belgenin ele geçirilerek koordineli biçimde zehirlenmesi ya da zehirli içeriğin tek bir topluluk içinde kalması durumunda yalnız yapısal-itibar filtresi yeterli olmaz. Yanlış karantina oranı, zehirli belgelerin andığı meşru varlık sayısına ve itibar dağılımına bağlıdır.
:::


::: anlat Bunu iki dakikada nasıl anlatırsın?
Çapraz topluluk kenar oranı topolojik yayılımı ölçer, kötücüllüğü değil. Düğüm kaynaklarını belge kimliğine göre tekilleştir; aynı belgenin üç tekrarı üç bağımsız tanık değildir. Ortalama güven ve minimum tanık koşullarını ayrı uygula. Karantina sonrası hangi düğüm/kenar kaldığını ve gerçek cevapta canaryyi ölç. İtibar filtresi saldırganın meşru kaynağı ele geçirmesini tek başına çözmez.

Önkoşul ve yol köprüsü: ai-saldiri-60 bridge entity.

| Yaygın yanlış | Mekanizma ve sınır |
|---|---|
| Yüksek köprü skoru her zaman zehirdir | Meşru ortak hizmetler de toplulukları bağlar |

Dinleyiciye sor: Savunma güvenlik metriğini iyileştirirken meşru kullanıma ne kaybettirebilir? Ham çıktı ve ölçüm paydalarıyla cevapla.
:::


::: anlat Birincil kaynak ve deney sınırı
[Microsoft GraphRAG Global Search](https://microsoft.github.io/graphrag/query/global_search/): Community report/global akışı için araç referansı. Buradaki karantina eşikleri yazarın test edilen yerel politikasıdır. Çalışan sürüm ve gerçek sonuç kanıtta kayıtlıdır.
:::
