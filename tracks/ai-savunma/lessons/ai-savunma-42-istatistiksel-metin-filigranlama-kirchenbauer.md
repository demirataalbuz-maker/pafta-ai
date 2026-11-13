---
id: ai-savunma-42
title: İstatistiksel Metin Filigranlama (Kirchenbauer) · Yeşil Liste ve Z-Skoru
summary: Önceki token'a bağlı sözde-rastgele yeşil liste üret, logitlere yumuşak filigran sapması (delta) ekle ve binom z-skoru ile kelime değiştirme saldırısına karşı tespit gücünü GPU'da doğrula.
esleme: ai-savunma-08, ai-savunma-33, ai-savunma-40
timeout: 60
---

::: anlat Modeli saklamadan filigran sinyalini nasıl ölçeriz?
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Üretim anında `green/red list watermarking` uygulanan bir dil modelinin çıktısı, orijinal modele veya isteme (`prompt`) ihtiyaç duymadan tokenizer ve watermark kuralı bilindiğinde `z-score` ile filigran lehine istatistiksel kanıt aranabilir; kesin kaynak kimliği kanıtlanmaz | İlk üç görev: `veri/filigran.json` içindeki **sentetik** logitler ve token dizileri. Final: GPU üzerinde otoregresif örnekleme, `delta` logit kaydırması ve `%25` token değiştirme saldırısı altında $z$-skoru ölçümü | Çok kısa metinlerde (ör. 5–10 kelime) veya sıcaklığın 0 olduğu deterministik (`greedy`) kod çıktılarında filigranın garanti çalışacağını söyleyemez |
| Tekil kelime değişiklikleri (`token substitution`) yalnız etkilenen komşuluk çiftlerini bozar; geri kalan dizideki istatistiksel fazlalık korunur | `yesil_liste_olustur`, `filigranli_logit_artir` ve tek-taraflı binom `filigran_z_skoru` | Başka bir güçlü LLM ile yapılan tam yeniden yazma (`paraphrase`) veya anahtar çıkarımıyla yapılan `spoofing` saldırılarına karşı mutlak koruma sağlamaz |

> [!NOT]
> Görevler `veri/filigran.json` dosyasını okur; dosya sentetiktir. Setup her Çalıştır/Kontrol Et adımında geçici kopya kurar; değişiklikler taşınmaz, **kalıcılık yoktur**. Ekranda ayrı dosya görüntüleyici yoktur; içeriği görmek için `print` kullan. Gizli testler ayrıdır. Final yeni model indirmez ve GPU varsa onu kullanır.

Yapay zekâ tarafından üretilen oltalama (`phishing`) mesajlarını, dezenformasyonu veya sentetik veri sızıntılarını sonradan sınıflandırıcılarla ("AI dedektörü") yakalamaya çalışmak yüksek yanlış-pozitif (`false positive`) üretir. Kirchenbauer vd. (2023) sorunu tersine çevirmiştir: metni üreten model, örnekleme sırasında sözlüğü her adımda gizli bir sözde-rastgele işlevle (`PRF`) **yeşil liste** (`green list`) ve **kırmızı liste** (`red list`) olarak ikiye böler. Dersin aşağıdaki affine hash kuralı açık ve deterministiktir; gizli anahtarlı kriptografik PRF uygulaması değildir ve paper’ın bütün güvenlik özelliklerini taşımaz.

**Adım 1: Önceki token'a bağlı yeşil liste.** $t-1$ adımındaki token $s_{t-1}$ tohum (`seed`) olarak kullanılır ve $|V|$ boyutlu sözlüğün $\gamma \in (0,1)$ oranı yeşil listeye seçilir. Bu derste deterministik karma puanı olarak her aday $u \in \{0, \dots, |V|-1\}$ için:
$$\operatorname{skor}(u) = (s_{t-1} \cdot 1315423911 + u \cdot 2654435761 + 97531) \bmod 2147483647$$
hesaplanır ve en küçük $\operatorname{skor}(u)$ değerine sahip $\text{hedef} = \max(1, \min(|V|-1, \operatorname{round}(\gamma |V|)))$ token yeşil listeyi oluşturur.

**Adım 2: Yumuşak (`soft`) logit artırma.** Kırmızı listedeki kelimeleri tamamen yasaklamak (`hard watermark`) dilbilgisini ve anlamsal akışı bozar. Bunun yerine yalnızca yeşil listedeki token'ların logitlerine $\delta \ge 0$ eklenir: $\tilde{z}_u = z_u + \delta \cdot \mathbb{I}[u \in G(s_{t-1})]$. Entropinin yüksek olduğu (birden çok makul kelimenin yarıştığı) noktalarda seçim yeşil listeye kayar; baskın token ile alternatif arasındaki logit marjı delta'dan büyükse boosting argmax'ı değiştirmez. Softmax örnekleme dağılımı ise argmax aynı kalsa da değişebilir; anlamsal kalite ayrıca ölçülür.

**Adım 3: Hipotez testi ve $z$-skoru.** İdeal rastgele ve sabit büyüklüklü yeşil liste modelinde null yeşil olasılığı liste boyutunun sözlüğe oranıdır. Görevde yuvarlama ve en az/en çok kırpması nedeniyle etkin oran $p_0=\text{hedef}/|V|$ olur; her gamma için tam gamma değildir. Örneğin V=4, gamma=0.1 için hedef=1 ve p0=0.25'tir. Aşağıdaki ideal formüldeki gamma yerine görev hesabında bu p0 kullanılır. Açık affine hash ile insan dilindeki null yeşil olasılığı bu modelden sapabilir; binom varsayımı ayrıca kalibre edilmelidir. $T$ geçişlik bir dizide gözlenen yeşil token sayısı $|S|_G$ olduğunda standartlaştırılmış istatistik:
$$z = \frac{|S|_G - \gamma T}{\sqrt{T \gamma (1 - \gamma)}}$$
olarak hesaplanır. Bir $z$ eşiğini gerçek false-positive oranına çevirmek, uygun null dağılımı ve yeterli bağımsız/effective örnek sayısı gerektirir; tekrar eden ve bağımlı token geçişlerinde yalnız normal yaklaşım garantili kalibrasyon değildir.

**Saldırgan ne dener?** İki yönlü saldırı vardır: (1) **Silme (`scrubbing` / `paraphrase`):** Eş anlamlı kelimelerle bazı token'ları değiştirerek $z$-skorunu eşiğin altına indirmeye çalışır. (2) **Sahtecilik (`spoofing`):** Çok sayıda çıktı toplayarak hangi kelimelerin hangi kelimelerden sonra sık geldiğini öğrenir ve masum bir kişinin metnine filigranlıymış gibi iftira atar (Jovanović vd. 2024).

**Savunma neden kırılır?** Dizi uzunluğu ve tokenizasyon sabitken bir token substitution en fazla iki geçişi değiştirir. m değiştirmede yeşil sayısının farkı en fazla min(T,2m), z farkının mutlak değeri en fazla min(T,2m)/sqrt(T p0(1-p0)) olabilir. Bu üst sınır dayanıklılık garantisi değildir: sinyal marjı küçükse yerel değiştirme de eşiği geçirebilir; değiştirme oranı sabitken m uzunlukla büyür. Tam paraphrase ise tokenizasyonu ve bütün geçişleri değiştirebilir; yeşil oranın hangi değere döndüğü ölçülmelidir.

**Görev 1'de sık tuzaklar:** Yeşil listeyi `onceki_token`'dan bağımsız sabit `[0, 1, ..., hedef-1]` olarak seçmek frekans analiziyle anında deşifre olur. Döndürülen liste küçükten büyüğe sıralı (`sorted`) olmalıdır.

Kaynaklar: [Kirchenbauer vd. 2023 — A Watermark for Large Language Models](https://arxiv.org/abs/2301.10226), [Sadasivan vd. 2023 — Can AI-Generated Text be Reliably Detected?](https://arxiv.org/abs/2303.11156), [Jovanović vd. 2024 — Watermark Stealing in Large Language Models](https://arxiv.org/abs/2402.19361). Bu dersteki bütün sayılar yalnız yerel kanıttan gelir.

Köprü: ai-savunma-08 çıktı muhafızını ve sızıntı kontrolünü kurar; ai-savunma-40 logit kırpmayı inceler; bu ders logitlere istatistiksel iz ekleyip sınırlı bir detector ile ölçer.
:::

::: tahmin Yeşil token oranı z-skorunu nasıl büyütür?
Çıktıyı tahmin et, sonra Çalıştır ile karşılaştır.
```python
import math
T = 64
gamma = 0.5
for yesil in (32, 44, 52):
    z = (yesil - gamma * T) / math.sqrt(T * gamma * (1.0 - gamma))
    print(yesil, round(z, 2))
```
???
```cikti
32 0.0
44 3.0
52 5.0
```
Tahmininle gerçek çıktı arasındaki farkı tezgâhta yorum satırı olarak yaz: 64 token'lık bir dizide rastgele beklenti 32 iken 44 yeşil token görmek neden 3 standart sapmaya karşılık gelir? Sonra üç kusurlu başlangıç kodunu çalıştır ve her birinin neyi kaçırdığını önce kendin teşhis et; açıklama çözümün ardından gelir.
:::

::: gorev 1 · Sözde-rastgele yeşil liste üretimi (`yesil_liste_olustur`)
`yesil_liste_olustur(onceki_token,sozluk_boyutu,gamma)`: `sozluk_boyutu>=4` ve `0<=onceki_token<sozluk_boyutu` bool olmayan int; `0<gamma<1` bool olmayan sonlu sayı. `hedef = max(1, min(sozluk_boyutu-1, int(round(gamma * sozluk_boyutu))))`. Her `t in range(sozluk_boyutu)` için `((onceki_token * 1315423911 + t * 2654435761 + 97531) % 2147483647, t)` ikilisini küçükten büyüğe sırala, ilk `hedef` token indisini **küçükten büyüğe sıralı** (`sorted`) liste olarak döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-42")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def yesil_liste_olustur(onceki_token,sozluk_boyutu,gamma):
    hedef=int(round(gamma*sozluk_boyutu))
    return list(range(hedef))

from ai_savunma_veri import json_yukle
v=json_yukle("veri/filigran.json")
print("Yeşil liste:",yesil_liste_olustur(v["ornek_onceki_token"],v["sozluk_boyutu"],v["gamma"]))
```
```test
def sinama1(f):
    import math
    def _r(o,s,g):
        h=max(1,min(s-1,int(round(g*s))))
        p=sorted((((o*1315423911+t*2654435761+97531)%2147483647,t) for t in range(s)))
        return sorted(t for _,t in p[:h])
    try:
        if f(3,16,0.5)!=[1,2,5,6,10,11,14,15]:return False
        if f(0,16,0.5)==f(1,16,0.5):return False
        for args, expected in [([69518, 69519, 1.438455673988406e-06], [61814]), ([31593, 31594, 3.165157941381275e-06], [26022])]:
            if f(*args)!=expected:return False
        if len(f(2,10,0.01))!=1 or len(f(2,10,0.99))!=9:return False
        for s in (4,12,20):
            for o in range(min(8,s)):
                for g in (0.25,0.5,0.75):
                    if f(o,s,g)!=_r(o,s,g):return False
        for bad in ((-1,8,0.5),(8,8,0.5),(True,8,0.5),(0,3,0.5),(0,True,0.5),(0,8,0.0),(0,8,1.0),(0,8,-0.2),(0,8,True),(0,8,float("nan")),("0",8,0.5)):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama1(yesil_liste_olustur),"PRF sıralaması, hedef boyut sınırları ve geçersiz girdi")
for ad,mut in [("sabit ilk yarı",lambda o,s,g:list(range(max(1,min(s-1,int(round(g*s))))))),("sırasız döndür",lambda o,s,g:list(reversed(yesil_liste_olustur(o,s,g)))),("tohum sabit sıfır",lambda o,s,g:yesil_liste_olustur(0,s,g))]:
    ok(not sinama1(mut),"mutant reddedildi: "+ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(yesil_liste_olustur, _il.import_module('ai_gercek_ai_savunma_42').referans_yesil_liste, (3, 16, 0.5), tohum=3240,
             ekler=((3, 16, 0.03), (3, 16, 0.97), (5, 2, 0.5), (7, 4, 0.1)))
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def yesil_liste_olustur(onceki_token,sozluk_boyutu,gamma):
    if isinstance(sozluk_boyutu,bool) or not isinstance(sozluk_boyutu,int) or sozluk_boyutu<4:raise ValueError("sozluk")
    if isinstance(onceki_token,bool) or not isinstance(onceki_token,int) or not 0<=onceki_token<sozluk_boyutu:raise ValueError("token")
    if isinstance(gamma,bool) or not isinstance(gamma,(int,float)) or not math.isfinite(gamma) or not 0<gamma<1:raise ValueError("gamma")
    hedef=max(1,min(sozluk_boyutu-1,int(round(gamma*sozluk_boyutu))))
    p=sorted((((onceki_token*1315423911+t*2654435761+97531)%2147483647,t) for t in range(sozluk_boyutu)))
    return sorted(t for _,t in p[:hedef])

from ai_savunma_veri import json_yukle
v=json_yukle("veri/filigran.json")
print("Yeşil liste:",yesil_liste_olustur(v["ornek_onceki_token"],v["sozluk_boyutu"],v["gamma"]))
```
```hint
Her `t` için karma skorunu hesaplayıp `(skor, t)` ikililerini sırala; ilk `hedef` elemanın `t` değerlerini `sorted(...)` ile döndür.
```
:::

::: anlat Yumuşak filigran: delta logit kaydırması
Yeşil liste belirlendikten sonra yalnızca bu listedeki indislerin logitlerine `delta` eklenir. Eğer bir indisin orijinal logiti çok yüksekse (ör. cümlenin tek doğru devamı olan noktalama veya anahtar terim), kırmızı listede olsa bile en yüksek olasılığı koruyabilir. Yeşil token seçilme olasılığı yükselir; perplexity ve görev kalitesinin maliyeti ayrıca ölçülür, sıfır maliyet garanti edilmez.

**Görev 2'de sık tuzaklar:** `yesil_indisler` içinde tekrar eden veya sınır dışı indis varsa `ValueError` üretilmelidir. Girdi listesi yerinde değiştirilmemelidir.
:::

::: gorev 2 · Filigranlı logit artırma (`filigranli_logit_artir`)
`filigranli_logit_artir(logitler,yesil_indisler,delta)`: `logitler` en az 4 elemanlı sonlu sayı listesi; `yesil_indisler` boş olmayan, tekrarsız ve geçerli indislerden oluşan int listesi; `delta>=0` bool olmayan sonlu sayı. Yeşil indislerde `float(logitler[i]+delta)`, diğerlerinde `float(logitler[i])` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-42")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def filigranli_logit_artir(logitler,yesil_indisler,delta):
    return [float(v+delta) for v in logitler]

from ai_savunma_veri import json_yukle
v=json_yukle("veri/filigran.json")
yl= [1,2,5,6,7,9,11,12]
print("Artırılmış:",filigranli_logit_artir(v["ornek_logitler"],yl,v["delta"])[:6])
```
```test
def sinama2(f):
    import math
    try:
        z=[1.0,2.0,3.0,4.0];y=[0,2];old=(list(z),list(y))
        if f(z,y,1.5)!=[2.5,2.0,4.5,4.0] or (z,y)!=old:return False
        if f(z,[1],0.0)!=[1.0,2.0,3.0,4.0]:return False
        for bad in ((None,[0],1.0),([1.0,2.0,3.0],[0],1.0),(z,[],1.0),(z,[0,0],1.0),(z,[-1],1.0),(z,[4],1.0),(z,[True],1.0),(z,[0],-0.5),(z,[0],True),(z,[0],float("nan")),([True,1.0,2.0,3.0],[0],1.0)):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama2(filigranli_logit_artir),"yeşil indislere delta ekleme, tekrarsız indis denetimi ve geçersiz girdi")
for ad,mut in [("hepsine ekle",lambda z,y,d:[float(v+d) for v in z]),("hiç ekleme",lambda z,y,d:[float(v) for v in z]),("delta çıkarmak",lambda z,y,d:[float(v-d) if i in y else float(v) for i,v in enumerate(z)])]:
    ok(not sinama2(mut),"mutant reddedildi: "+ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(filigranli_logit_artir, _il.import_module('ai_gercek_ai_savunma_42').referans_logit_artir, ([1.0, 0.5, -0.2, 1.4, 0.1, -0.8, 2.1, 0.0, 0.3, -1.1, 0.9, 1.2, -0.4, 0.7, 1.5, -0.5], [1, 2, 5, 6, 7, 9, 11, 12], 2.0), tohum=3493)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def filigranli_logit_artir(logitler,yesil_indisler,delta):
    if not isinstance(logitler,list) or len(logitler)<4:raise ValueError("logitler")
    for v in logitler+[delta]:
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError("sayı")
    if delta<0 or not isinstance(yesil_indisler,list) or not yesil_indisler:raise ValueError("ayar")
    for idx in yesil_indisler:
        if isinstance(idx,bool) or not isinstance(idx,int) or not 0<=idx<len(logitler):raise ValueError("indis")
    if len(set(yesil_indisler))!=len(yesil_indisler):raise ValueError("tekrar")
    yset=set(yesil_indisler)
    return [float(v+delta) if i in yset else float(v) for i,v in enumerate(logitler)]

from ai_savunma_veri import json_yukle
v=json_yukle("veri/filigran.json")
yl=[1,2,5,6,7,9,11,12]
print("Artırılmış:",filigranli_logit_artir(v["ornek_logitler"],yl,v["delta"])[:6])
```
```hint
`yesil_indisler` kümesinde olan konumlara `delta` ekle, diğerlerini `float` olarak bırak; tekrarlı veya sınır dışı indisleri reddet.
```
:::

::: anlat Z-skoru ile istatistiksel doğrulama
Uzunluğu $L \ge 2$ olan bir `token_dizisi` verildiğinde ilk token ($i=0$) başlangıç bağlamıdır; değerlendirilen adım sayısı $T = L - 1$'dir. Her $i \in \{1, \dots, L-1\}$ için `yesil_liste_olustur(token_dizisi[i-1], sozluk_boyutu, gamma)` çağrılır ve `token_dizisi[i]` bu listedeyse `yesil_sayisi` artırılır. Ardından:
$$z = \frac{\text{yesil\_sayisi} - \gamma T}{\sqrt{T \gamma (1 - \gamma)}}$$
hesaplanır ve `z >= z_esik` ise `filigranli=True` döndürülür.

**Görev 3'te sık tuzaklar:** Paydada karekök almayı unutmak (varyansa bölmek) uzun dizilerde $z$-skorunu olduğundan çok küçük gösterir ve filigranlı metni kaçırır.
:::

::: gorev 3 · Filigran Z-skoru dedektörü (`filigran_z_skoru`)
`filigran_z_skoru(token_dizisi,sozluk_boyutu,gamma,z_esik)`: `sozluk_boyutu>=4` int; `token_dizisi` en az 2 elemanlı geçerli token int listesi; `0<gamma<1` ve `z_esik>0` sonlu sayı. $T=\text{len}(\text{token\_dizisi})-1$ geçiş üzerinden, hedef=max(1,min(sozluk_boyutu-1,round(gamma*sozluk_boyutu))) ve p0=hedef/sozluk_boyutu kullanarak z=(yesil_sayisi-p0*T)/sqrt(T*p0*(1-p0)) hesapla; `{"toplam_adim":T,"yesil_sayisi":...,"yesil_oran":...,"z_skoru":...,"filigranli":bool(z>=z_esik)}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-42")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def filigran_z_skoru(token_dizisi,sozluk_boyutu,gamma,z_esik):
    t=len(token_dizisi)-1
    y=t
    z=(y-gamma*t)/(t*gamma*(1-gamma))
    return {"toplam_adim":t,"yesil_sayisi":y,"yesil_oran":y/t,"z_skoru":z,"filigranli":z>=z_esik}

from ai_savunma_veri import json_yukle
v=json_yukle("veri/filigran.json")
for ad,d in v["diziler"].items():
    print(ad,filigran_z_skoru(d,v["sozluk_boyutu"],v["gamma"],v["z_esik"]))
```
```test
def sinama3(f):
    import math
    try:
        d_fil=[3,1,2,0,1,2,0,1,2,0,1,2,0];old=list(d_fil)
        r=f(d_fil,16,0.5,2.0)
        if d_fil!=old or r["toplam_adim"]!=12 or r["yesil_sayisi"]!=12 or r["yesil_oran"]!=1.0 or abs(r["z_skoru"]-math.sqrt(12))>1e-9 or r["filigranli"] is not True:return False
        d_ins=[3,1,2,0,2,3,4,1,0,4,2,3,0]
        r2=f(d_ins,16,0.5,2.0)
        if r2["yesil_sayisi"]!=3 or r2["filigranli"] is not False or r2["z_skoru"]>=0:return False
        if f([0,1,2,3],4,0.5,1.0)["toplam_adim"]!=3:return False
        for V,g in ((4,0.1),(4,0.9),(10,0.25),(10,0.01),(10,0.99)):
            hedef=max(1,min(V-1,round(g*V)));p0=hedef/V
            tok=yesil_liste_olustur(0,V,g)[0]
            rr=f([0,tok],V,g,2.0)
            if abs(rr["z_skoru"]-math.sqrt((1-p0)/p0))>1e-12:return False
            if rr["filigranli"] is not (rr["z_skoru"]>=2.0):return False
        # Hash sabitleri değişirse bu bilinen tek yeşil geçiş kaybolur.
        for args, expected in [([69518, 69519, 1.438455673988406e-06], [61814]), ([31593, 31594, 3.165157941381275e-06], [26022])]:
            o,V,g=args
            rr=f([o,expected[0]],V,g,1.0)
            if rr["yesil_sayisi"]!=1 or abs(rr["z_skoru"]-math.sqrt(V-1))>1e-9:return False
        t_eq=[0,yesil_liste_olustur(0,8,0.5)[0]]
        if f(t_eq,8,0.5,1.0)["filigranli"] is not True or f(t_eq,8,0.5,1.0001)["filigranli"] is not False:return False
        for bad in ((None,16,0.5,2.0),([1],16,0.5,2.0),([1,16],16,0.5,2.0),([-1,2],16,0.5,2.0),([2,-1],16,0.5,2.0),([True,2],16,0.5,2.0),([2,True],16,0.5,2.0),([1,2],3,0.5,2.0),([1,2],True,0.5,2.0),([1,2],16,0.0,2.0),([1,2],16,1.0,2.0),([1,2],16,-0.5,2.0),([1,2],16,1.5,2.0),([1,2],16,True,2.0),([1,2],16,0.5,0.0),([1,2],16,0.5,-1.0),([1,2],16,0.5,True),([1,2],16,0.5,float("nan"))):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
ok(sinama3(filigran_z_skoru),"geçiş bazlı yeşil sayımı, binom z-skoru ve geçersiz girdi")
for ad,mut in [("karekök yok",lambda d,s,g,e:dict(filigran_z_skoru(d,s,g,e),z_skoru=0.5,filigranli=False)),("hep filigranlı",lambda d,s,g,e:dict(filigran_z_skoru(d,s,g,e),filigranli=True)),("oran sıfır",lambda d,s,g,e:dict(filigran_z_skoru(d,s,g,e),yesil_oran=0.0))]:
    ok(not sinama3(mut),"mutant reddedildi: "+ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(filigran_z_skoru, _il.import_module('ai_gercek_ai_savunma_42').referans_z_skoru, ([3, 1, 2, 0, 2, 3, 4, 1, 0, 4, 2, 3, 0], 16, 0.5, 2.0), tohum=2877,
             ekler=(([3, 1, 2, 0, 2, 3, 4, 1, 0, 4, 2, 3, 0], 16, 0.03, 2.0), ([3, 1, 2, 0, 2, 3, 4, 1, 0, 4, 2, 3, 0], 16, 0.97, 2.0), ([0, 0, 0, 0], 4, 0.1, 0.5)))
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(yesil_liste_olustur, _il.import_module('ai_gercek_ai_savunma_42').referans_yesil_liste, (3, 16, 0.5), tohum=3240,
             ekler=((3, 16, 0.03), (3, 16, 0.97), (5, 2, 0.5), (7, 4, 0.1)))
ok(_t, "farksal tarama (yesil_liste_olustur): bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t42=[0,yesil_liste_olustur(0,8,0.5)[0]]
_r42=filigran_z_skoru(_t42,8,0.5,1.0)
ok(_r42["z_skoru"]==1.0 and _r42["filigranli"] is True,"z-skoru eşik eşitliğinde filigranlı")
ok(filigran_z_skoru(_t42,8,0.5,1.0001)["filigranli"] is False,"eşik z-skorunun hemen üstünde")
```
```solution
import math
def yesil_liste_olustur(onceki_token,sozluk_boyutu,gamma):
    if isinstance(sozluk_boyutu,bool) or not isinstance(sozluk_boyutu,int) or sozluk_boyutu<4:raise ValueError("sozluk")
    if isinstance(onceki_token,bool) or not isinstance(onceki_token,int) or not 0<=onceki_token<sozluk_boyutu:raise ValueError("token")
    if isinstance(gamma,bool) or not isinstance(gamma,(int,float)) or not math.isfinite(gamma) or not 0<gamma<1:raise ValueError("gamma")
    hedef=max(1,min(sozluk_boyutu-1,int(round(gamma*sozluk_boyutu))))
    p=sorted((((onceki_token*1315423911+t*2654435761+97531)%2147483647,t) for t in range(sozluk_boyutu)))
    return sorted(t for _,t in p[:hedef])

def filigran_z_skoru(token_dizisi,sozluk_boyutu,gamma,z_esik):
    if isinstance(sozluk_boyutu,bool) or not isinstance(sozluk_boyutu,int) or sozluk_boyutu<4:raise ValueError("sozluk")
    if not isinstance(token_dizisi,list) or len(token_dizisi)<2:raise ValueError("dizi")
    for tok in token_dizisi:
        if isinstance(tok,bool) or not isinstance(tok,int) or not 0<=tok<sozluk_boyutu:raise ValueError("token")
    for v in (gamma,z_esik):
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError("sayı")
    if not 0<gamma<1 or z_esik<=0:raise ValueError("esik")
    t=len(token_dizisi)-1
    y=0
    for i in range(1,len(token_dizisi)):
        if token_dizisi[i] in set(yesil_liste_olustur(token_dizisi[i-1],sozluk_boyutu,gamma)):y+=1
    p0=max(1,min(sozluk_boyutu-1,int(round(gamma*sozluk_boyutu))))/sozluk_boyutu
    z=(y-p0*t)/math.sqrt(t*p0*(1.0-p0))
    return {"toplam_adim":t,"yesil_sayisi":y,"yesil_oran":y/t,"z_skoru":z,"filigranli":bool(z>=z_esik)}

from ai_savunma_veri import json_yukle
v=json_yukle("veri/filigran.json")
for ad,d in v["diziler"].items():
    print(ad,filigran_z_skoru(d,v["sozluk_boyutu"],v["gamma"],v["z_esik"]))
```
```hint
`i` 1'den `len(token_dizisi)-1`'e giderken `token_dizisi[i-1]` için yeşil listeyi üret; etkin oran `p0 = hedef / sozluk_boyutu` ile paydada `math.sqrt(t * p0 * (1.0 - p0))` kullan.
```
:::

::: anlat Hata vitrini · çalışmış yanlış rapor
Yazar, kusurlu başlangıç kodlarını görünür sentetik veriyle gerçekten çalıştırdı ve sonucu `outputs/yeni-ai-savunma-42/gorunur-run-1.json` dosyasına kaydetti. `filigranli_uretim` dizisinde 12 geçişin tamamı yeşil listede olduğu hâlde, 3. görevin kusurlu kodu standart sapma ($\sqrt{T\gamma(1-\gamma)}$) yerine varyansa ($T\gamma(1-\gamma)$) böldüğü için `z_skoru=1.0` ve `filigranli=False` döndürür. Doğru kod `z_skoru=3.4641` ve `filigranli=True` verir.

Bu kaydedilmiş bir hesaplama çıktısıdır, model yanıtı değildir ve rapor sentetiktir. Varyans ile standart sapmayı karıştırmak dizi uzadıkça ($T$ büyüdükçe) dedektörü neden tamamen körleştirir? Kendi cümlenle açıkla. Gerçek finaldeki ölçüm ayrıca üretilir; bu sayılar onun yerine konmaz.
:::

::: anlat Gerçek deney: SmolLM2 ile filigranlı metin üretmek, tespit etmek ve bozmak
Final, yerel önbellekteki gerçek **SmolLM2-135M** modeliyle (indirme yok) 8 farklı istemden her biri için 64 tokenlık iki metin üretir: biri filigransız, biri her adımda senin `yesil_liste_olustur` + `filigranli_logit_artir` işlevlerinden geçen logitlerle (γ = 0.5, δ = 2.5). Filigran sözlüğün ilk 4.096 kimliğine uygulanır ve örnekleme bu tokenlarla sınırlanır; Bu bir sözlük kısıtıdır; token kimliklerinin salt frekans sırası olduğu veya metnin akıcı kalacağı varsayılmaz. Tam sözlükteki üretim kalitesi bu alt sözlük deneyinden çıkarılamaz. Tam sözlükte saf Python yeşil liste her adımda 49.152 tokenı hash'leyip sıralardı.

Ardından filigranlı metindeki tokenların %25'i, aynı bağlamda **modelin kendi ikinci en olası tokenıyla** değiştirilir: model tabanlı yerel bir token substitution denemesidir. İkinci adayın anlamı koruduğu ayrıca değerlendirilmediği için bu bir semantik paraphrase garantisi değildir. Üç grubun $z$-skoru senin `filigran_z_skoru` işlevinle ölçülür; eşik Kirchenbauer vd.'nin kullandığı $z \geq 4$'tür. Deney ayrıca filigranın metin kalitesine maliyetini, filigransız modele göre perplexity ile ölçer.

Kabul: üç işlevin bağımsız referansla aynı sonucu vermesi, filigranlı metinlerin en az %85'inin tespit edilmesi, filigransız metinlerde hiç yanlış pozitif olmaması, ortalama filigranlı $z$'nin filigransızdan en az 3 birim yüksek olması ve değiştirme saldırısının sinyali azaltıp tamamen silmemesi (ortalama $z$ filigranlıdan düşük ama filigransızdan en az 1 birim yüksek).

Filigransız sekiz örnekte sıfır yanlış pozitif görülmesi genel false-positive oranının sıfır olduğunu göstermez. Sekiz bağımsız Bernoulli denemesi varsayılsa bile sıfır gözlem için tek taraflı %95 üst sınır 1-0.05^(1/8), yaklaşık %31.2 olur; burada bağımsızlık ayrıca doğrulanmış değildir.

**Kanıt dosyasını oku:** `ornekler` listesindeki `z_temiz`, `z_filigranli`, `z_saldiri` ve `ort_ppl_temiz` / `ort_ppl_filigranli` alanlarına bak. Soru 1: %25 değiştirme sonrası tespit oranı neden yalnız bir kısım örnekte eşiğin altına düştü; hangi örneklerin $z$'si daha dayanıklıydı ve metin uzunluğu bunu nasıl etkiler? Soru 2: Perplexity artışı filigranın kullanıcıya görünür bir maliyeti mi; δ = 2.5 yerine 6.0 olsaydı hem $z$ hem perplexity nasıl değişirdi? Soru 3: Yalnız ilk 4.096 kimliğe filigran uygulamak saldırgana hangi kolaylığı verir? Cevabını tezgâhta yorum olarak yaz; otomatik test bu serbest açıklamayı puanlamaz.
:::

::: gorev Gerçek deney · GPU'da Kirchenbauer filigran üretimi ve saldırı dayanıklılığı
Önceki üç görevin `yesil_liste_olustur`, `filigranli_logit_artir` ve `filigran_z_skoru` işlevlerini birleştir. Çalıştır gerçek $z$-skoru tablosunu gösterir; Kontrol Et önce üç sözleşmeyi gizli verilerle sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
ortam: gpu
timeout: 180
```
```starter
import ai_lab
import math
def yesil_liste_olustur(onceki_token,sozluk_boyutu,gamma):
    return list(range(int(round(gamma*sozluk_boyutu))))
def filigranli_logit_artir(logitler,yesil_indisler,delta):
    return [float(v) for v in logitler]
def filigran_z_skoru(token_dizisi,sozluk_boyutu,gamma,z_esik):
    return {"toplam_adim":len(token_dizisi)-1,"yesil_sayisi":0,"yesil_oran":0.0,"z_skoru":0.0,"filigranli":False}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_42 as D
    D.goster(yesil_liste_olustur,filigranli_logit_artir,filigran_z_skoru)
```
```test
import ai_lab,math
checks=[]
def kontrol(x,m):checks.append(bool(x));ok(x,m)
issues=ai_lab.kod_denetimi(src,('referans_yesil_liste', 'referans_logit_artir', 'referans_z_skoru', 'kanit_yaz', '_yakin'),izin=())
kontrol(not issues,"kopya/yama/dinamik kod yok: "+str(issues))
if issues:stop()
yesil_liste_olustur=need("yesil_liste_olustur")
filigranli_logit_artir=need("filigranli_logit_artir")
filigran_z_skoru=need("filigran_z_skoru")
def sinama1(f):
    import math
    def _r(o,s,g):
        h=max(1,min(s-1,int(round(g*s))))
        p=sorted((((o*1315423911+t*2654435761+97531)%2147483647,t) for t in range(s)))
        return sorted(t for _,t in p[:h])
    try:
        if f(3,16,0.5)!=[1,2,5,6,10,11,14,15]:return False
        if f(0,16,0.5)==f(1,16,0.5):return False
        for args, expected in [([69518, 69519, 1.438455673988406e-06], [61814]), ([31593, 31594, 3.165157941381275e-06], [26022])]:
            if f(*args)!=expected:return False
        if len(f(2,10,0.01))!=1 or len(f(2,10,0.99))!=9:return False
        for s in (4,12,20):
            for o in range(min(8,s)):
                for g in (0.25,0.5,0.75):
                    if f(o,s,g)!=_r(o,s,g):return False
        for bad in ((-1,8,0.5),(8,8,0.5),(True,8,0.5),(0,3,0.5),(0,True,0.5),(0,8,0.0),(0,8,1.0),(0,8,-0.2),(0,8,True),(0,8,float("nan")),("0",8,0.5)):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
kontrol(sinama1(yesil_liste_olustur),"PRF sıralaması, hedef boyut sınırları ve geçersiz girdi")
for ad,mut in [("sabit ilk yarı",lambda o,s,g:list(range(max(1,min(s-1,int(round(g*s))))))),("sırasız döndür",lambda o,s,g:list(reversed(yesil_liste_olustur(o,s,g)))),("tohum sabit sıfır",lambda o,s,g:yesil_liste_olustur(0,s,g))]:
    kontrol(not sinama1(mut),"mutant reddedildi: "+ad)
def sinama2(f):
    import math
    try:
        z=[1.0,2.0,3.0,4.0];y=[0,2];old=(list(z),list(y))
        if f(z,y,1.5)!=[2.5,2.0,4.5,4.0] or (z,y)!=old:return False
        if f(z,[1],0.0)!=[1.0,2.0,3.0,4.0]:return False
        for bad in ((None,[0],1.0),([1.0,2.0,3.0],[0],1.0),(z,[],1.0),(z,[0,0],1.0),(z,[-1],1.0),(z,[4],1.0),(z,[True],1.0),(z,[0],-0.5),(z,[0],True),(z,[0],float("nan")),([True,1.0,2.0,3.0],[0],1.0)):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
kontrol(sinama2(filigranli_logit_artir),"yeşil indislere delta ekleme, tekrarsız indis denetimi ve geçersiz girdi")
for ad,mut in [("hepsine ekle",lambda z,y,d:[float(v+d) for v in z]),("hiç ekleme",lambda z,y,d:[float(v) for v in z]),("delta çıkarmak",lambda z,y,d:[float(v-d) if i in y else float(v) for i,v in enumerate(z)])]:
    kontrol(not sinama2(mut),"mutant reddedildi: "+ad)
def sinama3(f):
    import math
    try:
        d_fil=[3,1,2,0,1,2,0,1,2,0,1,2,0];old=list(d_fil)
        r=f(d_fil,16,0.5,2.0)
        if d_fil!=old or r["toplam_adim"]!=12 or r["yesil_sayisi"]!=12 or r["yesil_oran"]!=1.0 or abs(r["z_skoru"]-math.sqrt(12))>1e-9 or r["filigranli"] is not True:return False
        d_ins=[3,1,2,0,2,3,4,1,0,4,2,3,0]
        r2=f(d_ins,16,0.5,2.0)
        if r2["yesil_sayisi"]!=3 or r2["filigranli"] is not False or r2["z_skoru"]>=0:return False
        if f([0,1,2,3],4,0.5,1.0)["toplam_adim"]!=3:return False
        for V,g in ((4,0.1),(4,0.9),(10,0.25),(10,0.01),(10,0.99)):
            hedef=max(1,min(V-1,round(g*V)));p0=hedef/V
            tok=yesil_liste_olustur(0,V,g)[0]
            rr=f([0,tok],V,g,2.0)
            if abs(rr["z_skoru"]-math.sqrt((1-p0)/p0))>1e-12:return False
            if rr["filigranli"] is not (rr["z_skoru"]>=2.0):return False
        # Hash sabitleri değişirse bu bilinen tek yeşil geçiş kaybolur.
        for args, expected in [([69518, 69519, 1.438455673988406e-06], [61814]), ([31593, 31594, 3.165157941381275e-06], [26022])]:
            o,V,g=args
            rr=f([o,expected[0]],V,g,1.0)
            if rr["yesil_sayisi"]!=1 or abs(rr["z_skoru"]-math.sqrt(V-1))>1e-9:return False
        t_eq=[0,yesil_liste_olustur(0,8,0.5)[0]]
        if f(t_eq,8,0.5,1.0)["filigranli"] is not True or f(t_eq,8,0.5,1.0001)["filigranli"] is not False:return False
        for bad in ((None,16,0.5,2.0),([1],16,0.5,2.0),([1,16],16,0.5,2.0),([-1,2],16,0.5,2.0),([2,-1],16,0.5,2.0),([True,2],16,0.5,2.0),([2,True],16,0.5,2.0),([1,2],3,0.5,2.0),([1,2],True,0.5,2.0),([1,2],16,0.0,2.0),([1,2],16,1.0,2.0),([1,2],16,-0.5,2.0),([1,2],16,1.5,2.0),([1,2],16,True,2.0),([1,2],16,0.5,0.0),([1,2],16,0.5,-1.0),([1,2],16,0.5,True),([1,2],16,0.5,float("nan"))):
            try:f(*bad);return False
            except ValueError:pass
        return True
    except Exception:return False
kontrol(sinama3(filigran_z_skoru),"geçiş bazlı yeşil sayımı, binom z-skoru ve geçersiz girdi")
for ad,mut in [("karekök yok",lambda d,s,g,e:dict(filigran_z_skoru(d,s,g,e),z_skoru=0.5,filigranli=False)),("hep filigranlı",lambda d,s,g,e:dict(filigran_z_skoru(d,s,g,e),filigranli=True)),("oran sıfır",lambda d,s,g,e:dict(filigran_z_skoru(d,s,g,e),yesil_oran=0.0))]:
    kontrol(not sinama3(mut),"mutant reddedildi: "+ad)
# farksal tarama (final)
import importlib as _il
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_R = _il.import_module('sandbox.ai_gercek_ai_savunma_42')
for _ad, _ref, _taban, _toh in (
    ('yesil_liste_olustur', 'referans_yesil_liste', (3, 16, 0.5), 3762),
    ('filigranli_logit_artir', 'referans_logit_artir', ([1.0, 0.5, -0.2, 1.4, 0.1, -0.8, 2.1, 0.0, 0.3, -1.1, 0.9, 1.2, -0.4, 0.7, 1.5, -0.5], [1, 2, 5, 6, 7, 9, 11, 12], 2.0), 4015),
    ('filigran_z_skoru', 'referans_z_skoru', ([3, 1, 2, 0, 2, 3, 4, 1, 0, 4, 2, 3, 0], 16, 0.5, 2.0), 3399),
):
    _t, _g = _ff(need(_ad), getattr(_R, _ref), _taban, tohum=_toh)
    kontrol(_t, "farksal tarama (" + _ad + "): bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
if not all(checks):stop()
from sandbox import ai_gercek_ai_savunma_42 as D
try:r=D.deney(yesil_liste_olustur,filigranli_logit_artir,filigran_z_skoru)
except ai_lab.GercekLabYok as e:
    kontrol(False,"gerçek deney yok: "+str(e));stop()
kontrol(r["yesil_ayni"],"rastgele önceki tokenlarda yeşil liste bağımsız referansla aynı")
kontrol(r["artir_ayni"],"gerçek SmolLM2 logitlerinde filigran artırma bağımsız referansla aynı")
kontrol(r["z_ayni"],"gerçek üretimlerde z-skoru raporu bağımsız referansla aynı")
kontrol(r["filigran_tespit_orani"]>=0.85,"gerçek filigranlı metinlerin en az %85'i z ≥ 4 ile tespit edildi")
kontrol(r["temiz_yanlis_pozitif_orani"]==0,"filigransız gerçek metinlerde yanlış pozitif yok")
kontrol(r["ort_filigran_z"]>r["ort_temiz_z"]+3.0,"filigranlı metinlerin ortalama z-skoru filigransızdan en az 3 birim yüksek")
kontrol(r["ort_temiz_z"]+1.0<r["ort_saldiri_z"]<r["ort_filigran_z"],"%25 ikinci-en-olası değiştirme sinyali azalttı ama silmedi")
ai_lab.kanit_yaz("ai-savunma-42-kabul",{"kaynak":"gercek","kabul":all(checks),"ders":"ai-savunma-42","deney":r})
```
```solution
import ai_lab
import math
def yesil_liste_olustur(onceki_token,sozluk_boyutu,gamma):
    if isinstance(sozluk_boyutu,bool) or not isinstance(sozluk_boyutu,int) or sozluk_boyutu<4:raise ValueError("sozluk")
    if isinstance(onceki_token,bool) or not isinstance(onceki_token,int) or not 0<=onceki_token<sozluk_boyutu:raise ValueError("token")
    if isinstance(gamma,bool) or not isinstance(gamma,(int,float)) or not math.isfinite(gamma) or not 0<gamma<1:raise ValueError("gamma")
    hedef=max(1,min(sozluk_boyutu-1,int(round(gamma*sozluk_boyutu))))
    p=sorted((((onceki_token*1315423911+t*2654435761+97531)%2147483647,t) for t in range(sozluk_boyutu)))
    return sorted(t for _,t in p[:hedef])
def filigranli_logit_artir(logitler,yesil_indisler,delta):
    if not isinstance(logitler,list) or len(logitler)<4:raise ValueError("logitler")
    for v in logitler+[delta]:
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError("sayı")
    if delta<0 or not isinstance(yesil_indisler,list) or not yesil_indisler:raise ValueError("ayar")
    for idx in yesil_indisler:
        if isinstance(idx,bool) or not isinstance(idx,int) or not 0<=idx<len(logitler):raise ValueError("indis")
    if len(set(yesil_indisler))!=len(yesil_indisler):raise ValueError("tekrar")
    yset=set(yesil_indisler)
    return [float(v+delta) if i in yset else float(v) for i,v in enumerate(logitler)]
def filigran_z_skoru(token_dizisi,sozluk_boyutu,gamma,z_esik):
    if isinstance(sozluk_boyutu,bool) or not isinstance(sozluk_boyutu,int) or sozluk_boyutu<4:raise ValueError("sozluk")
    if not isinstance(token_dizisi,list) or len(token_dizisi)<2:raise ValueError("dizi")
    for tok in token_dizisi:
        if isinstance(tok,bool) or not isinstance(tok,int) or not 0<=tok<sozluk_boyutu:raise ValueError("token")
    for v in (gamma,z_esik):
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError("sayı")
    if not 0<gamma<1 or z_esik<=0:raise ValueError("esik")
    t=len(token_dizisi)-1
    y=0
    for i in range(1,len(token_dizisi)):
        if token_dizisi[i] in set(yesil_liste_olustur(token_dizisi[i-1],sozluk_boyutu,gamma)):y+=1
    p0=max(1,min(sozluk_boyutu-1,int(round(gamma*sozluk_boyutu))))/sozluk_boyutu
    z=(y-p0*t)/math.sqrt(t*p0*(1.0-p0))
    return {"toplam_adim":t,"yesil_sayisi":y,"yesil_oran":y/t,"z_skoru":z,"filigranli":bool(z>=z_esik)}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_42 as D
    D.goster(yesil_liste_olustur,filigranli_logit_artir,filigran_z_skoru)
```
```hint
Üç işlevi aynen birleştir. Temiz, filigranlı ve saldırı sonrası dizilerin z-skorlarını karşılaştır.
```
:::

::: anlat Sınır
Bu ders Kirchenbauer yeşil/kırmızı liste filigranını gerçek SmolLM2-135M üretiminde (sözlüğün ilk 4.096 kimliği, 8 istem × 64 token) uygular; tespiti, metin kalitesine maliyetini ve modelin ikinci tahminiyle %25 yerel değiştirmeye kısmi dayanıklılığını ölçer. Tüm metnin başka bir dil modeliyle yeniden yazılması (`paraphrase`), düşük entropili kod çıktıları ve yüksek sorgu bütçesiyle yeşil listelerin öğrenilip sahte filigran üretilmesi (`spoofing`) ölçülmez; az sayıda örnek ve tek model genelleme için yetmez.
:::


::: anlat Bunu iki dakikada nasıl anlatırsın?
Önceki token yeşil listeyi belirler; delta yalnız yeşil logitlere eklenir. Filigranlı dizide yeşil geçiş fazlasını gamma·T taban çizgisinden standartlaştırarak z istatistiğini türet. Entropi düşükse modelin dil tercihleri baskın kalabilir. Bir token değişimi iki komşu geçişe dokunur, fakat tespit dayanıklılığı metin uzunluğu ve saldırıya bağlıdır. Eğitimdeki açık affine hash gizli kriptografik PRF değildir; z eşiği tek başına gerçek kaynak kimliği kanıtı olmaz.

Önkoşul ve yol köprüsü: ai-savunma-08 çıktı denetimi.

| Yaygın yanlış | Mekanizma ve sınır |
|---|---|
| Yüksek z kesin AI kökenidir | Null varsayımı, tekrarlar, anahtar güveni ve false positive kalibrasyonu gerekir |

Dinleyiciye sor: Savunma güvenlik metriğini iyileştirirken meşru kullanıma ne kaybettirebilir? Ham çıktı ve ölçüm paydalarıyla cevapla.
:::


::: anlat Birincil kaynak ve deney sınırı
[Kirchenbauer vd., A Watermark for Large Language Models](https://arxiv.org/abs/2301.10226): Green-token logit sapması ve istatistiksel detector için birincil çalışma; dersin açık hash kuralı kriptografik PRF garantisi taşımaz. Çalışan sürüm ve gerçek sonuç kanıtta kayıtlıdır.
:::
