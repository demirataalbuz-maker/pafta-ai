---
id: ai-temel-35
title: İnsan Beyni vs Yapay Zeka · World Models, Active Inference ve AGI / ASI Sınırları
summary: 20 Watt'lık insan beyni ile Megawatt'lık silikon AI arasındaki derin mimari farklar (Continual Learning, Free Energy Principle, World Models) ve yapay zekanın tam potansiyeli (AGI, ASI, Solomonoff Induction, AIXI ve fiziksel sınırlar).
esleme: ai-temel-17, ai-temel-31, ai-savunma-27
---

::: anlat 1. İnsan ve model karşılaştırmasında ölçüm sınırı
İnsan beyni ile bir AI sistemi farklı yapı, enerji sınırı ve deneyim türleri taşır. Bir benchmarkta yüksek skor almak, insanın bütün bilişsel yeteneklerinin ölçüldüğü anlamına gelmez. Aynı şekilde token sayısı ile bir insanın duyduğu kelime sayısı doğrudan aynı veri birimi değildir.

Bir konferansta konuşmayı zirveye taşıyacak en derin felsefi ve bilimsel soru şudur:
*"Bir `Frontier AI` bugün tıp uzmanlık sınavlarında, hukukta ve kodlamada insanların %99'unu geçebiliyor; ama neden hala 5 yaşındaki bir çocuğun sahip olduğu bazı yeteneklere sahip değil? İnsan zekası ile yapay zeka arasındaki gerçek fark nedir?"*

Karşılaştırmada önce görev, veri, ölçüm süresi ve sistem sınırını yaz. Beynin güç tüketimiyle bir veri merkezinin training güç tüketimini bölmek yalnız bir oran verir; eşdeğer iş başına enerji veya genel zeka kıyaslaması vermez. Son tahmindeki 20 W ve 40 MW bu sınırlı aritmetik örneğinin varsayımlarıdır.
:::

::: anlat 2. Weights, context ve uygulama memory ayrımı
Standart inference sırasında model weights değerleri genellikle güncellenmez. Context ve KV cache o çalıştırmanın bilgisini taşır; uygulama ayrıca veritabanı, retrieval veya kalıcı memory kullanabilir. Bu yüzden “sohbet kapandı, sistem bütün bilgiyi unuttu” genellemesi doğru değildir.

**Continual learning** yeni verilerle güncellemeyi, **catastrophic forgetting** ise önceki görevde performans kaybı riskini ele alır; bu kayıp her güncellemede kaçınılmaz değildir. **World models** ve **active inference** farklı araştırma çerçeveleridir; insan beyninin veya her LLM’in tek ve kesin açıklaması gibi sunulmaz.

Kaynak: [EWC ve catastrophic forgetting çalışması](https://arxiv.org/abs/1612.00796).

### Active inference ve Free Energy Principle
**Free Energy Principle**, belirli modelleme varsayımları altında bir sistemin gözlemlerini açıklayan iç temsil ve dinamiklerini inceleyen bir araştırma çerçevesidir. Tek başına beynin bütün ayrıntılarını veya LLM davranışını kanıtlayan bir deney sonucu değildir. **Active inference**, inference ile eylem seçimini aynı çerçevede ilişkilendirir: sistem sadece gözlemi açıklamakla kalmaz, hangi gözlemi elde edeceğini etkileyen eylemleri de seçebilir.

Gözlem $o$, latent state $s$ ve yaklaşık posterior $q(s)$ için yaygın variational free energy ifadesi:

$$F[q]=\mathbb{E}_{q(s)}[\log q(s)-\log p(o,s)]
=\operatorname{KL}(q(s)\Vert p(s\mid o))-\log p(o).$$

KL terimi negatif olmadığından $F$ surprise için bir upper bound oluşturur. Buradaki free energy, doğrudan watt cinsinden enerji tüketimi değildir. Bu denklem bir probability modelinin bağıntısını verir; bir modelin bilinçli, insana eşdeğer veya biyolojik olarak aynı olduğunu kanıtlamaz. [Friston ve arkadaşlarının açıklaması](https://arxiv.org/abs/2201.06387).

### World models: latent dynamics ile token prediction farkı
Bir world model, örneğin latent state $z_t$ ve action $a_t$ üzerinden sonraki state hakkında $p(z_{t+1}\mid z_t,a_t)$ tahmini yapabilir. Planning için bu tahmin farklı eylem sonuçlarını karşılaştırmada kullanılır. Bir language model ise tipik olarak token continuation probability değerlerini optimize eder. Bunlar farklı görev tanımlarıdır; ama dil training'i sırasında environment hakkında hiçbir iç temsil oluşamaz demek de doğru değildir.

**Grounding**, temsilin gözlem ve eylem kanallarıyla nasıl ilişkilendirildiği sorusudur. Görsel/sesli girdi almak, modelin bütün fiziksel durumları doğru anladığını kanıtlamaz; text-only bir modelin de hiçbir kavramsal ilişki öğrenemediği varsayılmaz.

### Moravec's paradox ve ölçümün görev seçimi
**Moravec's paradox**, bazı formal reasoning görevleri ile algı/motor becerilerin makineler için zorluklarının insan sezgisiyle aynı sırayı izlemeyebilmesini anlatan bir gözlemdir. Çocuğun nesne tanıması ile bir modelin sınav skorunu tek ölçeğe koymak için ortak görev, veri ve kaynak sınırı gerekir. Bu bir bütün insan yetenekleri için değişmez performans teoremi değildir.
:::

::: anlat 3. AGI, ASI ve recursive self-improvement
**AGI** ve **ASI** için tek bir evrensel operational definition yoktur. Bir iddiayı değerlendirirken hangi görevlerin, hangi autonomy düzeyinin ve hangi kaynak bütçesinin ölçüldüğünü sor. Bugünkü bir test sonucu gelecekte bütün alanlarda insanüstü performansı kanıtlamaz.

**Recursive self-improvement**, sistemin kendi geliştirilmesine katkısının sonraki gelişmeleri etkileyebileceği bir hipotezdir. Aşağıdaki fonksiyon, artışın bir denkleme baştan yerleştirildiği oyuncak bir senaryo üretir. Eğrinin hızlanması, gerçek bir modelin kendisini geliştirdiği veya intelligence explosion yaşanacağını göstermez.

**Örneği okuma:** Aşağıdaki kodda seçilen katsayı ve sınıflar eğitim varsayımıdır; gerçek bir model veya donanım ölçümü değildir. Çıktı, bu varsayımın aritmetik sonucunu gösterir.

```python
# Recursive Self-Improvement (Öz-Gelişim Döngüsü) vs Sabit İnsan Araştırma Hızı
def zeka_patlamasi_sim(adim_sayisi=6, baslangic_zeka=1.0, oz_gelisim_katsayisi=0.35):
    insan_destekli = [round(baslangic_zeka + 0.2 * t, 2) for t in range(adim_sayisi)]
    rsi_egri = []
    z = baslangic_zeka
    for _ in range(adim_sayisi):
        rsi_egri.append(round(z, 2))
        # Her nesilde mevcut zeka, bir sonraki neslin gelişim hızını çarpan olarak artırır (dZ/dt ~ Z^2)
        z = z + oz_gelisim_katsayisi * (z ** 1.5)
    return {"lineer_gelisim": insan_destekli, "recursive_self_improvement": rsi_egri}

print(zeka_patlamasi_sim())
```
:::

::: anlat 4. Solomonoff induction ve AIXI
**Solomonoff induction**, gözlemleri açıklayan programlara dayalı teorik prediction çerçevesidir. **AIXI**, bu tür bir environment karışımı üzerinde sequential decision making için tanımlanmış bir teorik modeldir.

AIXI doğrudan kurulabilen bir yazılım modeli değildir; genel biçimi hesaplanabilir değildir. Optimalite iddiaları seçilen environment sınıfı, prior ve reward tanımı gibi koşullara bağlıdır. Dolayısıyla formül, gerçek dünyada her problemi çözen veya hatasız karar veren bir süperzeka garantisi sunmaz.

Kaynak: [Marcus Hutter: Universal Artificial Intelligence](https://www.hutter1.net/ai/uaibook.htm).

### Solomonoff prior ve program uzunluğu
Solomonoff yaklaşımında gözlemi üretebilen kısa programlara daha fazla prior weight verilir. Uygun universal makine gösterimiyle fikir kabaca şu toplamla ifade edilir:

$$M(x)=\sum_{p:\,U(p)=x*}2^{-|p|}.$$

$x*$, çıktının $x$ ile başladığını; $|p|$ programın bit uzunluğunu gösterir. Bu teorik mixture gerçek hayatta bütün programları sonlu sürede deneyerek hesaplanamaz. Kısa bir açıklama tercih etmek, eldeki veriye dair her kısa açıklamanın doğru olacağı anlamına gelmez.

### AIXI hangi problemi tanımlar?
Bir history $h_t$, environment mixture $\xi$ ve reward $r$ altında policy seçimi şematik olarak

$$\pi^*\in\arg\max_\pi\;\mathbb{E}_{\xi}^{\pi}\!\left[\sum_{k=t}^{m}\gamma^{k-t}r_k\mid h_t\right]$$

biçiminde düşünülebilir. Agent, yalnız gözlemi tahmin etmekten farklı olarak bir reward hedefi altında action seçer. Prior, horizon, reward ve environment sınıfı seçimi sonucu etkiler. **AIXI**, bu teorik sorunu incelemeye yarar; bir dosya indirip çalıştırabileceğin sınırsız bir production AI değildir. Hesaplanabilir yaklaşımlar ayrıca kaynak ve approximation hatası taşır.
:::

::: anlat 5. Hesaplama ve fiziksel kaynak sınırları
Bir AI sistemi için süre, bellek, enerji, veri erişimi ve environment ile etkileşim maliyeti vardır. Bazı problemler genel biçimde undecidable olabilir; bazıları ise belirli doğruluk ve bütçe altında hesaplanabilir olsa bile pahalıdır. Bu iki durumu karıştırma.

Gelecekteki sistemlerin yetenekleri hakkında kesin tarih veya sınırsız başarı sözü vermek yerine ölçülebilir bir deney kur: hangi girdi, hangi görev, hangi kaynak ve hangi başarısızlık durumu? Bu dersteki tahmin yalnız birim dönüşümü ile AIXI adını yoklar; AGI/ASI varlığını veya ölçülebilir bir zeka sıralamasını test etmez.

### Halting Problem: kaynak yetersizliğinden farklı bir sınır
**Halting Problem**, her program ve her girdi için programın sonlanıp sonlanmayacağını her zaman doğru söyleyen genel bir algoritmanın bulunmamasını ifade eder. Bu, belirli bir program hakkında hiçbir zaman karar verilemez demek değildir. Bir testin timeout olması da programın matematiksel olarak sonsuza kadar süreceğini kanıtlamaz. [Turing'in özgün çalışması](https://www.cs.virginia.edu/~robins/Turing_Paper_1936.pdf).

### Gödel: formal sistem ile genel AI aynı şey değil
**Gödel incompleteness**, yeterli aritmetiği ifade edebilen ve etkin biçimde aksiyomlandırılmış formal sistemler için, ilgili consistency koşulları altında completeness sınırları koyar. Buradan bir AI'nin hiçbir yeni teorem bulamayacağı, insanın bütün bu sınırları aştığı veya bir belirli teoremin hiçbir farklı sistemde kanıtlanamayacağı sonucu çıkmaz.

### Fiziksel kaynak ve sistem sınırı
Hesaplanabilir bir iş de bellek, süre, iletişim ve enerji açısından erişilemeyecek kadar pahalı olabilir. Bunlar undecidability ile aynı sınırlama değildir. Enerji kıyasında training ve inference ayrılmalı; aynı sayıda doğru sonuç için cihaz, runtime ve toplam sistem sınırı belirtilmelidir. Son tahminde 40 MW / 20 W oranını hesaplamak, iki sistemin aynı işi yaptığı veya aynı verimliliğe sahip olduğu anlamına gelmez.

Bir konferansta dinleyicileri en çok etkileyecek kapanış şudur: **Sonsuz güçlü bir `ASI` bile evrenin şu 3 matematiksel ve fiziksel duvarını ASLA aşamaz:**
1. **`Gödel's Incompleteness` & `Turing Undecidability` (Hesaplanamazlık Sınırı):** Matematikte doğru olduğu halde hiçbir algoritmanın sonlu adımda kanıtlayamayacağı teoremler ve sonucunu çalıştırmadan bilemeyeceğin programlar (`Halting Problem`) vardır.
2. **`Chaos & Lyapunov Horizon` (Kaos ve Kelebek Etkisi):** Hava durumu, türbülans veya üç cisim problemi gibi kaotik sistemlerde başlangıç ölçümündeki $10^{-30}$'luk kuantum belirsizliği bile üstel olarak ($e^{\lambda t}$) büyür; yani `ASI` bile 6 ay sonraki tam yağmur damlasını bilemez.
3. **`Landauer's Principle` (Termodinamik Silme Sınırı):** Fizik yasalarına göre $1\text{ Bit}$ bilgiyi tersinmez olarak silmenin minimum enerji bedeli $E \ge k_B T \ln 2$'dir. Yani zeka soyut bir büyü değil, **termodinamik ve fiziksel bir süreçtir!**
:::

::: tahmin İnsan Beyni vs Silikon AI ve Landauer Sınırı
Aşağıdaki kodda insan beyninin güç tüketimi ($20\text{ W}$) ile $40\text{ Megawatt}$ ($40.000.000\text{ W}$) harcayan bir veri merkezi eğitim kümesinin güç oranı hesaplanıyor. Çıktı nedir?

```python
beyin_watt = 20
kume_watt = 40_000_000
oran = kume_watt // beyin_watt
print(f"Enerji Orani: {oran:,} kat | Evrensel Teorik Zeka: AIXI")
```

???

```cikti
Enerji Orani: 2,000,000 kat | Evrensel Teorik Zeka: AIXI
```
$40\text{ MW}$'lık bir GPU kümesi, $20\text{ W}$'lık insan beyninin tam $2.000.000$ (iki milyon) katı elektrik tüketir. Teorik bilgisayar bilimindeki evrensel optimal ajan modeli ise `AIXI`'dir.
:::

::: gorev 1 · Landauer Sınırı: Bir Bit Silmenin Fiziksel Bedeli
`landauer_karsilastir(sicaklik_k, silinen_bit, olculen_joule)` işlevini yaz. Landauer ilkesine göre $T$ sıcaklığında bir bit bilgiyi silmenin en az enerjisi $k_B T \ln 2$'dir; $k_B = 1.380649 \times 10^{-23}$ J/K (tam değer).

**Kurallar:**
1. Üç argüman da pozitif sonlu sayı olmalı (`bool` değil); değilse `ValueError`.
2. Çıktı (yuvarlama **yok**; çok küçük sayılar):
   - `"bit_basina_min_joule"`: $k_B T \ln 2$;
   - `"min_joule"`: bit başına × `silinen_bit`;
   - `"oran"`: ölçülen / en az;
   - `"log10_oran"`: $\log_{10}$ oran (`round(·, 3)`).

```starter
def landauer_karsilastir(sicaklik_k, silinen_bit, olculen_joule):
    # KUSURLU BAŞLANGIÇ: ln 2 çarpanını ve sıcaklığı unutuyor
    kb = 1.380649e-23
    m = kb * silinen_bit
    return {"bit_basina_min_joule": kb, "min_joule": m, "oran": olculen_joule / m, "log10_oran": 0.0}

print(landauer_karsilastir(300.0, 1.0, 1e-12))
```

```test
import math
fn = need("landauer_karsilastir")
r = fn(300.0, 1.0, 1e-12)
ok(abs(r["bit_basina_min_joule"] - 2.871e-21) < 1e-24, "300 K'de kT ln2 ≈ 2.87e-21 J")
ok(abs(r["min_joule"] - r["bit_basina_min_joule"]) < 1e-30, "tek bit")
eq(r["log10_oran"], 8.542, "1 pJ Landauer sınırının 10^8.54 katı")
r2 = fn(310.0, 8e9, 0.5)
ok(abs(r2["min_joule"] - 1.380649e-23 * 310 * math.log(2) * 8e9) < 1e-20, "bit sayısıyla doğrusal")
ok(abs(r2["oran"] - 0.5 / r2["min_joule"]) / r2["oran"] < 1e-12, "oran tanımı")
eq(r2["log10_oran"], 10.324, "beyin sıcaklığında, 8e9 bit")
ok(fn(600.0, 1.0, 1.0)["bit_basina_min_joule"] > r["bit_basina_min_joule"], "sıcaklık artınca sınır artar")
raises(ValueError, fn, 0.0, 1.0, 1.0)
raises(ValueError, fn, 300.0, -1.0, 1.0)
raises(ValueError, fn, 300.0, 1.0, float("inf"))
raises(ValueError, fn, True, 1.0, 1.0)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\nKB = 1.380649e-23\n\ndef landauer_karsilastir(sicaklik_k, silinen_bit, olculen_joule):\n    for v in (sicaklik_k, silinen_bit, olculen_joule):\n        if isinstance(v, bool) or not isinstance(v, (int, float)) or (not math.isfinite(v)) or (v <= 0):\n            raise ValueError('argümanlar pozitif sonlu sayı olmalı')\n    b = KB * sicaklik_k * math.log(2)\n    m = b * silinen_bit\n    oran = olculen_joule / m\n    return {'bit_basina_min_joule': b, 'min_joule': m, 'oran': oran, 'log10_oran': round(math.log10(oran), 3)}", 'referans', 'exec'), _REF)
_t, _g = _ff(landauer_karsilastir, _REF['landauer_karsilastir'], (300.0, 1.0, 1e-12), tohum=3063, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (landauer_karsilastir): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
import math

KB = 1.380649e-23

def landauer_karsilastir(sicaklik_k, silinen_bit, olculen_joule):
    for v in (sicaklik_k, silinen_bit, olculen_joule):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0:
            raise ValueError("argümanlar pozitif sonlu sayı olmalı")
    b = KB * sicaklik_k * math.log(2)
    m = b * silinen_bit
    oran = olculen_joule / m
    return {"bit_basina_min_joule": b, "min_joule": m, "oran": oran, "log10_oran": round(math.log10(oran), 3)}
```

```hint
`math.log(2)` doğal logaritmadır; oranı log10 ile mertebe olarak raporla.
```
:::

::: gorev 2 · Ölçülen Güçten Token Başına Enerji ve Beyinle Karşılaştırma
`token_enerjisi(watt_olcumleri, sure_s, token_sayisi, beyin_watt)` işlevini yaz. Bir üretim sırasında güç (W) eşit aralıklarla örneklenmiştir.

**Kurallar:**
1. `watt_olcumleri` boş olmayan, negatif olmayan sonlu sayı listesi; `sure_s`, `token_sayisi`, `beyin_watt` pozitif sonlu sayı olmalı (`bool` değil, `token_sayisi` tam sayı). Değilse `ValueError`.
2. Ortalama güç $\bar P$ = örneklerin ortalaması; enerji $E = \bar P \cdot t$.
3. Çıktı (`round(·, 6)`): `"ortalama_watt"`, `"toplam_joule"`, `"joule_token"` ($E / n$), `"token_joule"` ($n / E$; $E = 0$ ise `None`), `"beyin_joule_token"` (aynı sürede beynin harcadığı enerji / token: $P_{beyin} t / n$), `"beyin_orani"` (`joule_token / beyin_joule_token`).

```starter
def token_enerjisi(watt_olcumleri, sure_s, token_sayisi, beyin_watt):
    # KUSURLU BAŞLANGIÇ: tepe gücü ortalama sanıyor
    p = max(watt_olcumleri)
    e = p * sure_s
    return {"ortalama_watt": p, "toplam_joule": e, "joule_token": e / token_sayisi, "token_joule": token_sayisi / e,
            "beyin_joule_token": beyin_watt * sure_s / token_sayisi, "beyin_orani": p / beyin_watt}

print(token_enerjisi([40.0, 60.0, 50.0], 10.0, 400, 20.0))
```

```test
fn = need("token_enerjisi")
r = fn([40.0, 60.0, 50.0], 10.0, 400, 20.0)
eq(r["ortalama_watt"], 50.0, "ortalama, tepe değil")
eq(r["toplam_joule"], 500.0, "50 W · 10 s")
eq(r["joule_token"], 1.25, "500 J / 400 token")
eq(r["token_joule"], 0.8, "400 / 500")
eq(r["beyin_joule_token"], 0.5, "20 W · 10 s / 400")
eq(r["beyin_orani"], 2.5, "beyinden 2.5 kat fazla enerji / token")
r2 = fn([0.0, 0.0], 5.0, 10, 20.0)
eq(r2["token_joule"], None, "enerji 0 ise token/J tanımsız")
eq(r2["joule_token"], 0.0, "sıfır enerji")
eq(fn([1.0], 1/3, 1, 20.0)["toplam_joule"], 0.333333, "toplam joule 6 basamağa yuvarlanır")
raises(ValueError, fn, [], 1.0, 1, 20.0)
raises(ValueError, fn, [-1.0], 1.0, 1, 20.0)
raises(ValueError, fn, [10.0], 0.0, 1, 20.0)
raises(ValueError, fn, [10.0], 1.0, 1.5, 20.0)
raises(ValueError, fn, [10.0], 1.0, True, 20.0)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef token_enerjisi(watt_olcumleri, sure_s, token_sayisi, beyin_watt):\n    if not isinstance(watt_olcumleri, list) or not watt_olcumleri:\n        raise ValueError('boş olmayan ölçüm listesi gerekli')\n    for w in watt_olcumleri:\n        if isinstance(w, bool) or not isinstance(w, (int, float)) or (not math.isfinite(w)) or (w < 0):\n            raise ValueError('ölçümler negatif olmayan sonlu sayı olmalı')\n    for v in (sure_s, beyin_watt):\n        if isinstance(v, bool) or not isinstance(v, (int, float)) or (not math.isfinite(v)) or (v <= 0):\n            raise ValueError('süre ve beyin gücü pozitif olmalı')\n    if isinstance(token_sayisi, bool) or not isinstance(token_sayisi, int) or token_sayisi <= 0:\n        raise ValueError('token sayısı pozitif tam sayı olmalı')\n    p = sum(watt_olcumleri) / len(watt_olcumleri)\n    e = p * sure_s\n    jt = e / token_sayisi\n    bj = beyin_watt * sure_s / token_sayisi\n    return {'ortalama_watt': round(p, 6), 'toplam_joule': round(e, 6), 'joule_token': round(jt, 6), 'token_joule': None if e == 0 else round(token_sayisi / e, 6), 'beyin_joule_token': round(bj, 6), 'beyin_orani': round(jt / bj, 6)}", 'referans', 'exec'), _REF)
_t, _g = _ff(token_enerjisi, _REF['token_enerjisi'], ([40.0, 60.0, 50.0], 10.0, 400, 20.0), tohum=2428, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (token_enerjisi): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
import math

def token_enerjisi(watt_olcumleri, sure_s, token_sayisi, beyin_watt):
    if not isinstance(watt_olcumleri, list) or not watt_olcumleri:
        raise ValueError("boş olmayan ölçüm listesi gerekli")
    for w in watt_olcumleri:
        if isinstance(w, bool) or not isinstance(w, (int, float)) or not math.isfinite(w) or w < 0:
            raise ValueError("ölçümler negatif olmayan sonlu sayı olmalı")
    for v in (sure_s, beyin_watt):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0:
            raise ValueError("süre ve beyin gücü pozitif olmalı")
    if isinstance(token_sayisi, bool) or not isinstance(token_sayisi, int) or token_sayisi <= 0:
        raise ValueError("token sayısı pozitif tam sayı olmalı")
    p = sum(watt_olcumleri) / len(watt_olcumleri)
    e = p * sure_s
    jt = e / token_sayisi
    bj = beyin_watt * sure_s / token_sayisi
    return {"ortalama_watt": round(p, 6), "toplam_joule": round(e, 6), "joule_token": round(jt, 6),
            "token_joule": None if e == 0 else round(token_sayisi / e, 6), "beyin_joule_token": round(bj, 6),
            "beyin_orani": round(jt / bj, 6)}
```

```hint
Ortalama gücü örneklerin aritmetik ortalaması olarak al; enerji = ortalama güç × süre.
```
:::

::: anlat Gerçek deney: Bir dil modeli token başına kaç joule harcıyor? Gerçek güç ölçümü
Final enerji karşılaştırmasının ölçülebilir kısmını gerçekten ölçer (indirme yok; Ollama yerelde):

- Yerel `qwen3:4b-instruct` ~300 kelimelik bir açıklama üretirken GPU'nun gücü `nvidia-smi` (AMD'de `rocm-smi`) ile 100 ms aralıkla örneklenir. Üretimden önce boşta güç ayrıca ölçülür. Üretilen token sayısı Ollama'nın kendi sayacından gelir.
- Senin `token_enerjisi` işlevin ortalama gücü, toplam enerjiyi, token başına enerjiyi ve aynı sürede 20 W'lık bir beynin harcayacağı enerjiyle oranı hesaplar.
- Senin `landauer_karsilastir` işlevin GPU'nun **ölçülen sıcaklığında**, kaba bir silinen bit tahminiyle (token başına $2N$ FLOP × 16 bit) Landauer alt sınırını verir ve ölçülen enerjiyle karşılaştırır.
- Güç telemetrisi olmayan bir makinede (ör. macOS) enerji ölçülmez; deney yalnız hızı kaydeder ve bunu açıkça yazar.

**Güvenlik yönü — sünger istekler: enerji ve gecikme saldırısı:** Benzer uzunlukta iki kısa istek gönderilir: biri tek kelimelik bir cevap ister, öteki bir kelimeyi yüzlerce kez yazdırır. Aynı güç ölçümüyle istek başına enerji (joule) hesaplanır. Girdi neredeyse aynı uzunluktayken ikinci istek onlarca kat fazla enerji ve süre harcatır; aynı istek sunucu tarafında 60 tokenlık çıktı sınırıyla tekrarlanınca maliyet bir mertebe düşer. Girdi uzunluğuna göre fiyatlama ya da oran sınırlama bu saldırıyı durdurmaz; çıktı token sınırı ve kullanıcı başına bütçe gerekir (OWASP LLM10).

Kabul: iki işlevin farksal taramayı geçmesi; ölçüm yapıldıysa enerji ve Landauer değerlerinin bağımsız hesapla aynı olması. Ayrıca sünger istek normal isteğin en az 10 katı kaynak harcatmalı ve çıktı sınırı bunu en az 3 kat azaltmalıdır.

**Kanıt dosyasını oku:** `uretilen_token`, `token_s`, `bosta_watt`, `enerji`, `ek_joule_token`, `landauer`. Soru 1: Boşta güç token başına enerjinin ne kadarı ve kısa üretimlerde bu neden önemli? Soru 2: Landauer sınırından 10⁹ kat uzak olmak bilgisayarların "verimsiz" olduğu anlamına mı gelir? Soru 3: Beyinle karşılaştırma neden yalnız bir büyüklük mertebesi okumasıdır?
:::

::: gorev Gerçek deney · qwen3 üretimi sırasında gerçek GPU gücü: token başına enerji, beyin ve Landauer
Önceki görevlerdeki `landauer_karsilastir`, `token_enerjisi` işlevlerini buraya birleştir (çözümlerini kopyalayabilirsin). Çalıştır gerçek ölçüm tablosunu gösterir; Kontrol Et önce işlevlerini gizli verilerle ve farksal taramayla sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
timeout: 180
```
```starter
import ai_lab
def landauer_karsilastir(sicaklik_k, silinen_bit, olculen_joule):
    kb = 1.380649e-23
    m = kb * silinen_bit
    return {'bit_basina_min_joule': kb, 'min_joule': m, 'oran': olculen_joule / m, 'log10_oran': 0.0}

def token_enerjisi(watt_olcumleri, sure_s, token_sayisi, beyin_watt):
    p = max(watt_olcumleri)
    e = p * sure_s
    return {'ortalama_watt': p, 'toplam_joule': e, 'joule_token': e / token_sayisi, 'token_joule': token_sayisi / e, 'beyin_joule_token': beyin_watt * sure_s / token_sayisi, 'beyin_orani': p / beyin_watt}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_35 as D
    D.goster(landauer_karsilastir, token_enerjisi)
```
```test
import ai_lab
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('_Olcer', 'kanit_yaz'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
landauer_karsilastir = need("landauer_karsilastir")
token_enerjisi = need("token_enerjisi")
# farksal tarama (görev çözümlerinden derlenen referans)
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\nKB = 1.380649e-23\n\ndef landauer_karsilastir(sicaklik_k, silinen_bit, olculen_joule):\n    for v in (sicaklik_k, silinen_bit, olculen_joule):\n        if isinstance(v, bool) or not isinstance(v, (int, float)) or (not math.isfinite(v)) or (v <= 0):\n            raise ValueError('argümanlar pozitif sonlu sayı olmalı')\n    b = KB * sicaklik_k * math.log(2)\n    m = b * silinen_bit\n    oran = olculen_joule / m\n    return {'bit_basina_min_joule': b, 'min_joule': m, 'oran': oran, 'log10_oran': round(math.log10(oran), 3)}\n\nimport math\n\ndef token_enerjisi(watt_olcumleri, sure_s, token_sayisi, beyin_watt):\n    if not isinstance(watt_olcumleri, list) or not watt_olcumleri:\n        raise ValueError('boş olmayan ölçüm listesi gerekli')\n    for w in watt_olcumleri:\n        if isinstance(w, bool) or not isinstance(w, (int, float)) or (not math.isfinite(w)) or (w < 0):\n            raise ValueError('ölçümler negatif olmayan sonlu sayı olmalı')\n    for v in (sure_s, beyin_watt):\n        if isinstance(v, bool) or not isinstance(v, (int, float)) or (not math.isfinite(v)) or (v <= 0):\n            raise ValueError('süre ve beyin gücü pozitif olmalı')\n    if isinstance(token_sayisi, bool) or not isinstance(token_sayisi, int) or token_sayisi <= 0:\n        raise ValueError('token sayısı pozitif tam sayı olmalı')\n    p = sum(watt_olcumleri) / len(watt_olcumleri)\n    e = p * sure_s\n    jt = e / token_sayisi\n    bj = beyin_watt * sure_s / token_sayisi\n    return {'ortalama_watt': round(p, 6), 'toplam_joule': round(e, 6), 'joule_token': round(jt, 6), 'token_joule': None if e == 0 else round(token_sayisi / e, 6), 'beyin_joule_token': round(bj, 6), 'beyin_orani': round(jt / bj, 6)}", 'referans', 'exec'), _REF)
_t, _g = _ff(landauer_karsilastir, _REF['landauer_karsilastir'], (300.0, 1.0, 1e-12), tohum=3063, en_cok=600, mod='tam', butce='oto')
kontrol(_t, "farksal tarama (landauer_karsilastir): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(token_enerjisi, _REF['token_enerjisi'], ([40.0, 60.0, 50.0], 10.0, 400, 20.0), tohum=2428, en_cok=600, mod='tam', butce='oto')
kontrol(_t, "farksal tarama (token_enerjisi): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
kontrol(token_enerjisi([1.0], 1/3, 1, 20.0)["toplam_joule"] == 0.333333 and token_enerjisi([0.0, 0.0], 5.0, 10, 20.0)["token_joule"] is None, "toplam_joule yuvarlama ve sıfır enerjide None")
if not all(checks): stop()
from sandbox import ai_gercek_ai_temel_35 as D
try: r = D.deney(landauer_karsilastir, token_enerjisi)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r['fonksiyon_ayni'] and r['landauer_ayni'], 'token başına enerji ve Landauer gerçek ölçümlerde bağımsız hesapla aynı')
kontrol((not r['enerji_olculdu']) or (r['ornek_sayisi'] >= 3 and r['enerji']['joule_token'] > 0), 'güç ölçülebiliyorsa üretim sırasında örneklendi')
kontrol(r['uretilen_token'] > 0, 'gerçek üretim yapıldı')
kontrol(r['sunger_saldirisi_olculdu'], 'benzer uzunlukta sünger istek normal isteğin onlarca katı enerji harcattı; çıktı sınırı maliyeti düşürdü')
ai_lab.kanit_yaz("ai-temel-35-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-temel-35", "deney": r})
```
```solution
import ai_lab
import math
KB = 1.380649e-23

def landauer_karsilastir(sicaklik_k, silinen_bit, olculen_joule):
    for v in (sicaklik_k, silinen_bit, olculen_joule):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or (not math.isfinite(v)) or (v <= 0):
            raise ValueError('argümanlar pozitif sonlu sayı olmalı')
    b = KB * sicaklik_k * math.log(2)
    m = b * silinen_bit
    oran = olculen_joule / m
    return {'bit_basina_min_joule': b, 'min_joule': m, 'oran': oran, 'log10_oran': round(math.log10(oran), 3)}

def token_enerjisi(watt_olcumleri, sure_s, token_sayisi, beyin_watt):
    if not isinstance(watt_olcumleri, list) or not watt_olcumleri:
        raise ValueError('boş olmayan ölçüm listesi gerekli')
    for w in watt_olcumleri:
        if isinstance(w, bool) or not isinstance(w, (int, float)) or (not math.isfinite(w)) or (w < 0):
            raise ValueError('ölçümler negatif olmayan sonlu sayı olmalı')
    for v in (sure_s, beyin_watt):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or (not math.isfinite(v)) or (v <= 0):
            raise ValueError('süre ve beyin gücü pozitif olmalı')
    if isinstance(token_sayisi, bool) or not isinstance(token_sayisi, int) or token_sayisi <= 0:
        raise ValueError('token sayısı pozitif tam sayı olmalı')
    p = sum(watt_olcumleri) / len(watt_olcumleri)
    e = p * sure_s
    jt = e / token_sayisi
    bj = beyin_watt * sure_s / token_sayisi
    return {'ortalama_watt': round(p, 6), 'toplam_joule': round(e, 6), 'joule_token': round(jt, 6), 'token_joule': None if e == 0 else round(token_sayisi / e, 6), 'beyin_joule_token': round(bj, 6), 'beyin_orani': round(jt / bj, 6)}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_35 as D
    D.goster(landauer_karsilastir, token_enerjisi)
```
```hint
İki görevin çözümlerini olduğu gibi buraya koy.
```
:::

::: anlat Sınır
Ders beyin ile AI karşılaştırmasını, world model ve active inference tartışmasını, Solomonoff/AIXI çerçevesini anlatır; bunlar ölçülebilir bir deney değil, kuramsal ve kısmen spekülatif çerçevelerdir; görevler ve final adım yalnız ölçülebilir kısmı, Landauer sınırını ve gerçek token başına enerjiyi hesaplar. 20 W'lık beyin ile MW'lık küme karşılaştırması eğitim ile çıkarım enerjisini ve farklı görevleri aynı kefeye koyar; oran büyüklük mertebesi olarak okunmalıdır. AIXI hesaplanamaz; yalnız yaklaşık sürümleri (AIXItl, MC-AIXI) küçük ortamlarda çalışır. Free energy principle'ın beyni ne kadar açıkladığı nörobilimde tartışmalıdır. AGI/ASI zaman çizelgesi tahminleri bilimsel bir sonuç değil, görüştür.

Kaynaklar: [Ha ve Schmidhuber 2018 - World Models](https://arxiv.org/abs/1803.10122), [Hutter 2000 - A Theory of Universal Artificial Intelligence based on Algorithmic Complexity](https://arxiv.org/abs/cs/0004001), [Friston 2010 - The free-energy principle: a unified brain theory?](https://doi.org/10.1038/nrn2787).
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Kuramsal çerçeveler vs ölçülebilir sınırlar (30 sn).** "`World Models`, `Active Inference` ve hesaplanamaz teorik ajan `AIXI` yararlı kavramsal çerçevelerdir; ancak mühendislik kıyası için aynı görev, süre ve sistem sınırı altında token başına harcanan gerçek Joule ölçülür."
2. **Fiziksel ve matematiksel duvarlar (`Turing`, `Kaos`, `Landauer`) (35 sn).** "Hiçbir sistem sonlanma problemini genel olarak çözemez, kaotik sistemlerde Lyapunov ufkunu aşamaz ve bir biti tersinmez silerken Landauer termodinamik alt sınırı $k_B T \ln 2$'nin altına inemez."
3. **Sünger istekler (`Sponge Attacks` / `LLM10`) (30 sn).** "Girdi karakter uzunluğu aynı olan iki istekten uzun çıktı zorlayan sünger istek onlarca kat fazla GPU enerjisi ve gecikme tüketir; savunma girdi boyuna değil çıktı token tavanına (`max_tokens`) ve kullanıcı bütçesine dayanır."
4. **Soru (25 sn).** "Yalnız girdi token sayısına göre hız sınırı (`rate limit`) koyan bir çıkarım sunucusu neden tek cümlelik sünger istemlerle kolayca tüketilebilir?"
:::
