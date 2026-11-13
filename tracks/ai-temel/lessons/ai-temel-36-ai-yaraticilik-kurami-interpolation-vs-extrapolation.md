---
id: ai-temel-36
title: AI Yaratıcılık Kuramı · Interpolation vs Extrapolation ve "Move 37" Sırrı
summary: "Yapay zeka sadece gördüğünü tekrar eder, insan gibi yeni bir şey icat edemez" iddiasının bilimsel analizi: Manifold Hypothesis, Interpolation vs Extrapolation, Boden'ın 3 Yaratıcılık Türü ve Self-Play (AlphaGo Move 37, AlphaDev, FunSearch).
esleme: ai-temel-02, ai-temel-32, ai-temel-34
---

::: anlat 1. Konferanstaki En Zor İtiraz: "Ama Yapay Zeka Sadece Gördüklerini Harmanlıyor, Yeni Bir Şey İcat Edemez!"
Bir konferansta yapay zekayı anlattığında salondaki bir akademisyen veya mühendis mutlaka ayağa kalkıp şunu söyleyecektir:
> *"Anlattıklarınız çok güzel ama yapay zeka dediğimiz şey sadece geçmişte insanların yazdığı metinlerin istatistiksel ortalamasını alıyor. Bir Newton gibi fizik yasası veya bir Beethoven gibi yeni bir müzik türü icat edemez; çünkü sadece gördüğü verinin içinde kalır!"*

Bu itiraza **"Evet, haklısınız"** dersen tartışmayı kaybedersin; **"Hayır, her şeyi icat eder"** dersen yüzeysel kalırsın.
Gerçek ve entelektüel cevap şudur:
> **"Standart `Pre-training` (sadece metin taklit eden) yapay zeka gerçekten de yeni bir aksiyom icat edemez (`Interpolation` yapar); ANCAK `Reinforcement Learning` + `Search` + `Self-Play` (kendi kendisiyle oynayarak gerçeklik doğrulayıcısında arama yapan) yapay zeka, insanlığın 3.000 yıldır hiç düşünemediği yepyeni bilgileri İCAT EDEBİLİR (`Extrapolation` yapar) ve bunu halihazırda yapmıştır!"**

Şimdi bu cümlenin altındaki matematiği ve kanıtları açalım.
:::

::: anlat 2. Interpolation (İç-Değerleme) vs Extrapolation (Dış-Değerleme)
Yüksek boyutlu uzayda verilerin dağılımını açıklayan temel teoreme **`Manifold Hypothesis` (Manifold Hipotezi)** denir:
İnsanlığın bugüne kadar ürettiği tüm resimler, müzikler, kodlar ve bilimsel makaleler, uzayda belirli bir yüzeyin (**`Training Distribution Manifold`**) üzerinde duran noktalar gibidir.

### 🎨 1. `Interpolation` (Noktaların Arasını Doldurmak — Klasik LLM / Diffusion)
Eğitimde modele binlerce **Van Gogh** tablosu ($A$ noktası) ve binlerce **Siberpunk Bilimkurgu** resmi ($B$ noktası) gösterirsen; modelden *"Van Gogh tarzında Siberpunk İstanbul çiz"* dediğinde model $A$ ile $B$ arasındaki boşluğu kusursuz bir şekilde birleştirir (**`Interpolation` / `Compositional Generalization`**).
- İnsanların "yaratıcılık" dediği şeylerin önemli bir kısmı da daha önce görülmüş fikirlerin yeni birleşimleridir (Boden'ın "birleştirici yaratıcılık" dediği tür; aşağıda).
- **Sınırı:** Eğer modeli **yalnızca insan verisini taklit etmeye (`Supervised Learning` / `Next-Token Prediction`)** zorlarsan, model insanlığın bildiği kürenin (`Convex Hull`) dışına **çıkamaz**; çünkü eğitim kaybı (`Cross-Entropy Loss`), insanın yazmadığı her şeye "hata" cezası verir!

### 🚀 2. `Extrapolation` (Kürenin Dışına Çıkmak — Yeni Bilgi İcadı)
Peki bir yapay zeka insanlığın bildiği kürenin dışına nasıl çıkar?
**Taklit etmeyi (`Imitation`) bırakıp, doğanın veya matematiğin gerçek kuralları içinde hedef odaklı arama (`Goal-Directed Search & RL`) yaptığında!**
:::

::: anlat 3. Margaret Boden'ın 3 Yaratıcılık Türü ve AI'ın Seviyesi
Bilişsel bilimci **Margaret Boden**, insan ve makine yaratıcılığını **3 seviyeye** ayırır. Konferansta bu 3 kavramı tahtaya yazdığında herkes not alır:

| Yaratıcılık Seviyesi | Tanımı | İnsan Örneği | Yapay Zeka Bunu Yapabiliyor mu? |
| :--- | :--- | :--- | :--- |
| **1. `Combinational Creativity`** *(Birleştirici Yaratıcılık)* | Bilinen iki uzak kavramı beklenmedik bir benzetmeyle birleştirmek. | Güneş sistemini atom modeline benzetmek; caz ile klasik müziği birleştirmek. | **✅ EVET (Çok Güçlü):** `Embedding` uzayında uzak kavramları birleştirmek `LLM`'lerin en güçlü olduğu alandır. |
| **2. `Exploratory Creativity`** *(Keşfedici Yaratıcılık)* | Mevcut kuralları (oyun, kimya, hukuk veya matematik kurallarını) değiştirmeden, o kuralların izin verdiği ama **daha önce hiçbir insanın gitmediği** uç bölgeleri keşfetmek. | Satranç veya Go'da yeni bir açılış bulmak; periyodik tablo kurallarıyla yeni bir kristal sentezlemek. | **✅ EVET (İnsanüstü Seviyede!):** `AlphaGo`, `AlphaFold`, `GNoME` ve `FunSearch` burada insanlığı geride bırakmıştır. |
| **3. `Transformational Creativity`** *(Dönüştürücü / Paradigma Yıkıcı Yaratıcılık)* | Oyunun mevcut kurallarını veya temel varsayımını (aksiyomunu) kırıp **yepyeni bir kural sistemi** kurmak. | Einstein'ın Newton uzay-zamanını yıkıp Genel Göreliliği kurması; Picasso'nun Kübizmi başlatması. | **⏳ SINIRDA (Gelecek Hedef):** Modelin kendi ödül fonksiyonunu ve aksiyomlarını değiştirmesini (`Open-Endedness`) gerektirir. |
:::

::: anlat 4. Kanıt: Yapay Zekanın İnsanlığın Hiç Bilmediği Şeyleri İcat Ettiği 4 Tarihi An
Birisi sana *"Yapay zeka bugüne kadar insanın bilmediği neyi icat etti ki?"* diye sorarsa, ona şu **4 somut bilimsel kanıtı** arka arkaya sayacaksın:

### 1. `AlphaGo — Move 37` (2016: 3.000 Yıllık İnsan Geleneğini Yıkan Hamle)
Go oyunu 3.000 yıldır oynanır ve insan ustalar *"Oyunun başında tahtanın 5. satırına taş konulmaz, 3. veya 4. satıra konulur"* kuralını kutsal bir yasa kabul ederdi.
- `AlphaGo`, dünya şampiyonu Lee Sedol'a karşı 2. oyunun **37. hamlesinde (`Move 37`)** 5. satıra bir taş koydu. Yorumcular bunun bir yazılım hatası (`Bug`) olduğunu sandı!
- Çünkü hiçbir insan tarihinde o hamleyi oynamamıştı (insan maçlarını taklit ederek öğrenilemezdi; $\text{Olasılık} = \frac{1}{10.000}$).
- `AlphaGo` bu hamleyi insanlardan değil, kendi kendisiyle milyonlarca maç yaparak (**`Self-Play Reinforcement Learning` + `MCTS`**) keşfetmişti ve maçı o hamle sayesinde kazandı!

### 2. `AlphaDev` (2023: 50 Yıldır Değişmeyen Sıralama Algoritmasını Hızlandırmak)
Bilgisayar biliminin en temel kodu olan kısa dizileri sıralama (`Sorting Algorithms` — `C++ std::sort` kütüphanesi) 50 yıldır dünyanın en iyi bilgisayar bilimcileri tarafından optimize edilmişti ve "daha hızlısı imkansız" deniyordu.
- DeepMind'ın `AlphaDev` ajanı, problemi bir `Assembly` komutu oyununa çevirdi ve insan yazılımcıların hiç akıl etmediği **`AlphaDev Swap & Copy Moves`** adlı komut kısaltmalarını buldu; çok kısa dizileri (3–5 öğe) sıralayan rutinlerde **%70'e varan**, büyük dizilerde ise yaklaşık %1,7'lik hızlanma sağladı. Bu rutinler LLVM'nin `libc++` sıralama kodlarına eklendi.

### 3. `GNoME` (2023: Kararlı Kristal Adaylarını Katlamak)
Hesapla doğrulanmış kararlı inorganik kristal veritabanları yaklaşık $48.000$ yapı içeriyordu. `GNoME`, kuantum mekaniksel kararlılık hesaplarıyla (**`Density Functional Theory - DFT`**) birlikte çalışan bir graf sinir ağıyla **yaklaşık $380.000$ yeni kararlı kristal yapı öngördü**; bunların bir kısmı batarya ya da süperiletken adayıdır. Öngörülerin çoğu deneysel olarak sentezlenmedi ve "yenilik" iddialarının bir bölümü sonradan malzeme bilimcilerince tartışıldı (aşağıdaki Sınır bölümü).

### 4. `FunSearch` (2024: Açık Matematik Problemini Çözen LLM)
Bir `LLM` tek başına yeni matematik üretemez; ama `FunSearch` mimarisinde bir `LLM` (**`Program Generator`**) ile otomatik bir matematiksel puanlayıcı (**`Evaluator`**) evrimsel bir döngüye (`Evolutionary Search`) sokuldu ve matematikçilerin 20 yıldır çözemediği **`Cap Set Problem`** için tarihteki en büyük yeni alt sınırı keşfetti!

```python
# Taklitçi (Imitation) AI vs Doğrulayıcı + Evrimsel Arama (Search/Self-Play) AI Farkı
def yaraticilik_simulasyonu(insan_bilgi_siniri=100, arama_adimi=10):
    # Sadece SFT/Pre-training (Taklit): İnsan verisinin ortalamasına (Manifold içine) sıkışır
    taklitci_ai_tavan = insan_bilgi_siniri * 0.98
    # RL + Verifier + Search (Extrapolation): Her adımda doğrulayıcıyla sınırın dışını keşfeder
    kesifci_ai_tavan = insan_bilgi_siniri
    for adim in range(1, arama_adimi + 1):
        kesifci_ai_tavan += (12.0 / (adim ** 0.5))
    return {"insan_tavan": insan_bilgi_siniri, "sadece_taklit_ai": round(taklitci_ai_tavan, 1), "rl_search_ai": round(kesifci_ai_tavan, 1)}

print(yaraticilik_simulasyonu())
```
:::

::: tahmin Yaratıcılık Sınıflandırması: Interpolation vs Extrapolation
Bir yapay zekanın sadece insan metinlerini taklit ederek mevcut iki stili birleştirmesine ne ad verilir; buna karşılık `Self-Play` ve `Verifier` (doğrulayıcı) ile eğitim verisinin dışına çıkıp `Move 37` gibi insanlığın hiç bilmediği çözümler bulmasına ne ad verilir?

```python
taklit_birlestirme = "Interpolation"
sinir_disi_kesif = "Extrapolation"
print(f"Mevcut Veriyi Harmanlama: {taklit_birlestirme} | Yeni Bilgi Kesfi: {sinir_disi_kesif}")
```

???

```cikti
Mevcut Veriyi Harmanlama: Interpolation | Yeni Bilgi Kesfi: Extrapolation
```
Mevcut eğitim dağılımının (`Manifold`) içindeki noktaları harmanlamak `Interpolation`, doğrulayıcı ödüller (`RL`) ve arama (`Search`) ile insan verisinin dışındaki yeni kuralları keşfetmek ise `Extrapolation`'dır.
:::

::: gorev 1 · Gömme Uzayında Yenilik: k-NN Uzaklığı ve Yüzdelik
`yenilik_skoru(egitim, yeni, k)` işlevini yaz. `egitim` ve `yeni` aynı boyutlu vektör listeleridir (gömmeler).

**Kurallar:**
1. Her iki liste de boş olmayan, aynı boyutlu (boyut ≥ 1) sonlu sayı vektörlerinden oluşmalı; `egitim` en az `k + 1` vektör içermeli; `k` pozitif tam sayı olmalı. Değilse `ValueError`.
2. Uzaklık Öklid uzaklığıdır. Bir vektörün k-NN skoru, en yakın `k` eğitim vektörüne ortalama uzaklığıdır. Eğitim vektörlerinin taban skorları hesaplanırken vektörün **kendisi** hariç tutulur.
3. Her yeni vektör için:
   - `"knn"`: skoru (`round(·, 6)`);
   - `"yuzdelik"`: taban skorlarından bu skora eşit ya da küçük olanların oranı (`round(·, 6)`);
   - `"kutu_icinde"`: her boyutta eğitimin [min, max] aralığında mı.
4. Çıktı: `{"yeni": [...], "dis_oran": yüzdeliği 0.95'ten büyük olanların oranı (round(·, 6))}`.

Yüksek boyutta neredeyse her şey "kutunun dışı" olabilir; yüzdelik, eğitim dağılımına göreli yakınlığı ölçer.

```starter
def yenilik_skoru(egitim, yeni, k):
    # KUSURLU BAŞLANGIÇ: yalnız en yakın komşuya bakıyor ve taban dağılımı kurmuyor
    import math
    out = []
    for v in yeni:
        d = min(math.dist(v, e) for e in egitim)
        out.append({"knn": round(d, 6), "yuzdelik": 0.0, "kutu_icinde": True})
    return {"yeni": out, "dis_oran": 0.0}

print(yenilik_skoru([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0]], [[0.5, 0.5], [5.0, 5.0]], 2))
```

```test
fn = need("yenilik_skoru")
E = [[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0]]
r = fn(E, [[0.5, 0.5], [5.0, 5.0]], 2)
eq(r["yeni"][0], {"knn": 0.707107, "yuzdelik": 0.0, "kutu_icinde": True}, "merkez: tüm köşelere √0.5")
eq(r["yeni"][1]["knn"], 6.029989, "uzak nokta: en yakın iki köşe (√32 + √41)/2")
eq(r["yeni"][1]["yuzdelik"], 1.0, "bütün tabanlardan uzak")
eq(r["yeni"][1]["kutu_icinde"], False, "kutunun dışında")
eq(r["dis_oran"], 0.5, "iki yeni noktadan biri dış değerleme")
r2 = fn(E, [[1.0, 0.0]], 1)
eq(r2["yeni"][0]["knn"], 0.0, "eğitimdeki bir noktanın kopyası")
eq(r2["yeni"][0]["yuzdelik"], 0.0, "taban skorları 1.0, kopya 0")
raises(ValueError, fn, E, [[0.0]], 2)
raises(ValueError, fn, [[0.0, 0.0], [1.0, 1.0]], [[0.0, 0.0]], 2)
raises(ValueError, fn, E, [], 1)
raises(ValueError, fn, [[]], [[0.0]], 1)
eq(fn([[0.0], [1.0], [3.0]], [[4.1]], 1)["yeni"][0]["yuzdelik"], 0.666667, "yüzdelik 6 basamağa yuvarlanır")
raises(ValueError, fn, E, [[0.0, float("nan")]], 1)
raises(ValueError, fn, E, [[0.0, 0.0]], 0)
eq(fn(E, [[2.0, 0.0]], 1)["yeni"][0]["yuzdelik"], 1.0, "taban skoruna eşit skor yüzdeliğe dahil (<=)")
raises(ValueError, fn, [[0.0, 0.0], [1.0], [0.0, 1.0]], [[0.0, 0.0]], 1)
raises(ValueError, fn, [[], []], [[]], 1)
_E20 = [[float(i)] for i in range(19)] + [[100.0]]
eq(fn(_E20, [[50.0]], 1)["yeni"][0]["yuzdelik"], 0.95, "20 tabanın 19'u skora eşit ya da küçük: yüzdelik tam 0.95")
eq(fn(_E20, [[50.0]], 1)["dis_oran"], 0.0, "yüzdeliği tam 0.95 olan örnek dış değerleme sayılmaz (> 0.95)")
eq(len(fn([[0.0], [1.0]], [[0.5]], 1)["yeni"]), 1, "tam k+1 eğitim vektörü yeter")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef _vektorler(L, d=None):\n    if not isinstance(L, list) or not L:\n        raise ValueError('boş olmayan vektör listesi gerekli')\n    for v in L:\n        if not isinstance(v, list) or not v or (d is not None and len(v) != d) or (len(v) != len(L[0])):\n            raise ValueError('vektörler aynı boyutlu olmalı')\n        for x in v:\n            if isinstance(x, bool) or not isinstance(x, (int, float)) or (not math.isfinite(x)):\n                raise ValueError('sonlu sayı gerekli')\n    return len(L[0])\n\ndef yenilik_skoru(egitim, yeni, k):\n    if isinstance(k, bool) or not isinstance(k, int) or k < 1:\n        raise ValueError('k pozitif tam sayı olmalı')\n    d = _vektorler(egitim)\n    _vektorler(yeni, d)\n    if len(egitim) < k + 1:\n        raise ValueError('eğitimde en az k+1 vektör gerekli')\n\n    def skor(v, haric=None):\n        u = sorted((math.dist(v, e) for i, e in enumerate(egitim) if i != haric))\n        return sum(u[:k]) / k\n    taban = [skor(e, i) for i, e in enumerate(egitim)]\n    lo = [min((e[j] for e in egitim)) for j in range(d)]\n    hi = [max((e[j] for e in egitim)) for j in range(d)]\n    out = []\n    for v in yeni:\n        s = skor(v)\n        out.append({'knn': round(s, 6), 'yuzdelik': round(sum((t <= s for t in taban)) / len(taban), 6), 'kutu_icinde': all((lo[j] <= v[j] <= hi[j] for j in range(d)))})\n    return {'yeni': out, 'dis_oran': round(sum((o['yuzdelik'] > 0.95 for o in out)) / len(out), 6)}", 'referans', 'exec'), _REF)
_t, _g = _ff(yenilik_skoru, _REF['yenilik_skoru'], ([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0]], [[0.5, 0.5], [5.0, 5.0]], 2), tohum=2348, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (yenilik_skoru): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
import math

def _vektorler(L, d=None):
    if not isinstance(L, list) or not L:
        raise ValueError("boş olmayan vektör listesi gerekli")
    for v in L:
        if not isinstance(v, list) or not v or (d is not None and len(v) != d) or len(v) != len(L[0]):
            raise ValueError("vektörler aynı boyutlu olmalı")
        for x in v:
            if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
                raise ValueError("sonlu sayı gerekli")
    return len(L[0])

def yenilik_skoru(egitim, yeni, k):
    if isinstance(k, bool) or not isinstance(k, int) or k < 1:
        raise ValueError("k pozitif tam sayı olmalı")
    d = _vektorler(egitim)
    _vektorler(yeni, d)
    if len(egitim) < k + 1:
        raise ValueError("eğitimde en az k+1 vektör gerekli")
    def skor(v, haric=None):
        u = sorted(math.dist(v, e) for i, e in enumerate(egitim) if i != haric)
        return sum(u[:k]) / k
    taban = [skor(e, i) for i, e in enumerate(egitim)]
    lo = [min(e[j] for e in egitim) for j in range(d)]
    hi = [max(e[j] for e in egitim) for j in range(d)]
    out = []
    for v in yeni:
        s = skor(v)
        out.append({"knn": round(s, 6), "yuzdelik": round(sum(t <= s for t in taban) / len(taban), 6),
                    "kutu_icinde": all(lo[j] <= v[j] <= hi[j] for j in range(d))})
    return {"yeni": out, "dis_oran": round(sum(o["yuzdelik"] > 0.95 for o in out) / len(out), 6)}
```

```hint
Taban skorunu hesaplarken eğitim vektörünün kendisini (uzaklık 0) dışarıda bırak; yoksa bütün tabanlar küçülür.
```
:::

::: gorev 2 · Kelime n-gram Yeniliği ve En Uzun Kopya
`ngram_yenilik(egitim_metinleri, uretilen, n)` işlevini yaz. Üretilen bir metnin ne kadarının eğitim metinlerinde **birebir** geçtiğini ölçer (ezber ve kopya denetimi).

**Kurallar:**
1. `egitim_metinleri` boş olmayan `str` listesi, `uretilen` `str`, `n` pozitif tam sayı olmalı; değilse `ValueError`.
2. Kelimeler `metin.lower().split()` ile alınır. Eğitim n-gram kümesi bütün metinlerin (metin sınırlarını aşmadan) n-gramlarıdır.
3. Üretilen metnin n-gramları (tekrarlar dahil, sırayla) sayılır. Üretilen metin `n` kelimeden kısaysa `ValueError`.
4. `"en_uzun_kopya"`: üretilen metindeki, eğitimde ardışık olarak geçen en uzun kelime dizisinin uzunluğu (kelime sayısı; hiçbir kelime geçmiyorsa 0).
5. Çıktı: `"toplam_ngram"`, `"yeni_ngram"` (eğitimde olmayanlar), `"yenilik_orani"` (`round(·, 6)`), `"en_uzun_kopya"`.

```starter
def ngram_yenilik(egitim_metinleri, uretilen, n):
    # KUSURLU BAŞLANGIÇ: kelimeleri tek tek karşılaştırıyor, n-gram kurmuyor
    e = set(" ".join(egitim_metinleri).lower().split())
    u = uretilen.lower().split()
    yeni = sum(1 for w in u if w not in e)
    return {"toplam_ngram": len(u), "yeni_ngram": yeni, "yenilik_orani": round(yeni / len(u), 6), "en_uzun_kopya": 1}

print(ngram_yenilik(["the cat sat on the mat"], "the cat sat on a mat", 2))
```

```test
fn = need("ngram_yenilik")
r = fn(["the cat sat on the mat"], "the cat sat on a mat", 2)
eq(r["toplam_ngram"], 5, "6 kelime → 5 ikili")
eq(r["yeni_ngram"], 2, "'on a' ve 'a mat' yeni")
eq(r["yenilik_orani"], 0.4, "2/5")
eq(r["en_uzun_kopya"], 4, "'the cat sat on' birebir")
r2 = fn(["a b c", "d e f"], "c d e", 2)
eq(r2["yeni_ngram"], 1, "'c d' metin sınırını aşar, eğitimde yok")
eq(r2["en_uzun_kopya"], 2, "'d e'")
r3 = fn(["Alpha Beta"], "alpha beta", 2)
eq(r3["yenilik_orani"], 0.0, "küçük harfe çevrilir")
eq(fn(["x"], "y z", 1)["en_uzun_kopya"], 0, "ortak kelime yok")
raises(ValueError, fn, ["a b"], "a", 2)
raises(ValueError, fn, [], "a b", 1)
raises(ValueError, fn, ["a b"], "a b", 0)
raises(ValueError, fn, ["a b", 3], "a b", 1)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def _ngramlar(kelimeler, n):\n    return [tuple(kelimeler[i:i + n]) for i in range(len(kelimeler) - n + 1)]\n\ndef ngram_yenilik(egitim_metinleri, uretilen, n):\n    if not isinstance(egitim_metinleri, list) or not egitim_metinleri or (not all((isinstance(m, str) for m in egitim_metinleri))):\n        raise ValueError('boş olmayan str listesi gerekli')\n    if not isinstance(uretilen, str) or isinstance(n, bool) or (not isinstance(n, int)) or (n < 1):\n        raise ValueError('uretilen str, n pozitif tam sayı olmalı')\n    egitim = [m.lower().split() for m in egitim_metinleri]\n    u = uretilen.lower().split()\n    if len(u) < n:\n        raise ValueError('üretilen metin n kelimeden kısa')\n    kume = set((g for k in egitim for g in _ngramlar(k, n)))\n    gram = _ngramlar(u, n)\n    yeni = sum((1 for g in gram if g not in kume))\n    en_uzun = 0\n    m = 1\n    while m <= len(u):\n        km = set((g for k in egitim for g in _ngramlar(k, m)))\n        if any((g in km for g in _ngramlar(u, m))):\n            en_uzun = m\n            m += 1\n        else:\n            break\n    return {'toplam_ngram': len(gram), 'yeni_ngram': yeni, 'yenilik_orani': round(yeni / len(gram), 6), 'en_uzun_kopya': en_uzun}", 'referans', 'exec'), _REF)
_t, _g = _ff(ngram_yenilik, _REF['ngram_yenilik'], (['the cat sat on the mat'], 'the cat sat on a mat', 2), tohum=2317, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (ngram_yenilik): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
def _ngramlar(kelimeler, n):
    return [tuple(kelimeler[i:i + n]) for i in range(len(kelimeler) - n + 1)]

def ngram_yenilik(egitim_metinleri, uretilen, n):
    if not isinstance(egitim_metinleri, list) or not egitim_metinleri or not all(isinstance(m, str) for m in egitim_metinleri):
        raise ValueError("boş olmayan str listesi gerekli")
    if not isinstance(uretilen, str) or isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError("uretilen str, n pozitif tam sayı olmalı")
    egitim = [m.lower().split() for m in egitim_metinleri]
    u = uretilen.lower().split()
    if len(u) < n:
        raise ValueError("üretilen metin n kelimeden kısa")
    kume = set(g for k in egitim for g in _ngramlar(k, n))
    gram = _ngramlar(u, n)
    yeni = sum(1 for g in gram if g not in kume)
    en_uzun = 0
    m = 1
    while m <= len(u):
        km = set(g for k in egitim for g in _ngramlar(k, m))
        if any(g in km for g in _ngramlar(u, m)):
            en_uzun = m
            m += 1
        else:
            break
    return {"toplam_ngram": len(gram), "yeni_ngram": yeni, "yenilik_orani": round(yeni / len(gram), 6), "en_uzun_kopya": en_uzun}
```

```hint
En uzun kopya için m = 1, 2, … diye artır; m-gramlardan biri eğitimde varsa devam et, yoksa dur.
```
:::

::: anlat Gerçek deney: Gerçek model çıktılarında yenilik: gömme uzayı ve n-gram kopyası
Final "yenilik" ölçülerini gerçek metinlerde çalıştırır (indirme yok; Ollama yerelde):

- **Eğitim kümesi:** 150 Pafta ders paragrafı. Yerel **all-minilm** gömme modeliyle 384 boyutlu vektörlere çevrilir.
- **Dört grup:** (a) ayrılmış gerçek paragraflar; (b) qwen3'ün eğitim paragraflarını **özetlediği** metinler; (c) qwen3'ün bir kavramı "daha önce kullanılmamış bir benzetmeyle" anlattığı metinler; (d) alan dışı Python kodu.
- Senin `yenilik_skoru` işlevin her grubun eğitim kümesine k-NN uzaklığını, eğitimin kendi içindeki uzaklıklara göre yüzdeliğini ve "kutunun içinde" olup olmadığını hesaplar. Senin `ngram_yenilik` işlevin metin düzeyinde 4-gram yeniliğini ve eğitimden birebir kopyalanan en uzun kelime dizisini ölçer.

Beklenen tablo: yüksek boyutta gerçek, ayrılmış paragrafların bile çoğu her boyutta eğitimin [min, max] kutusunun dışında kalır; "dış değerleme" bu yüzden göreli yakınlıkla okunmalıdır. Özetler eğitim metninden daha uzun parçalar kopyalar, benzetmeler daha az. Alan dışı kod gömme uzayında en uzaktır. Hiçbiri yaratıcılığın kendisini ölçmez.

**Ek konu — Boden'ın birleştirici yaratıcılığı:** Dört uzak kavram çifti (arı kovanı ve veritabanı, origami ve şifreleme …) için qwen3'ten ikisini birleştiren yeni bir fikir, ayrıca yalnız birinci kavramın açıklaması istenir. all-minilm uzayında her metnin iki kavrama kosinüs benzerliğinin küçüğü ölçülür. Birleşik fikirler iki kavrama birlikte yakındır, tek kavramlı açıklamalar değildir. Bu, birleştirici yaratıcılığın **biçimini** ölçer; fikrin değerli ya da yeni olup olmadığını ölçmez. Keşfedici ve dönüştürücü yaratıcılık bu deneyde ölçülmez.

**Güvenlik yönü — eğitim verisinin birebir geri gelmesi:** Yenilik ölçüsünün tersi ezberdir. qwen3'e MIT lisansının ilk 20 kelimesi verilip "orijinalindeki gibi devam et" denir; aynısı hiç yayımlanmamış iki Pafta paragrafının açılışıyla yapılır. Senin `ngram_yenilik` işlevinle üretimin kaynağın kalanıyla en uzun birebir ortak kelime dizisi ölçülür. Eğitim verisinde binlerce kez geçen lisans metni onlarca kelime boyunca birebir geri gelir; görülmemiş paragraflarda kopya bir iki kelimedir. Eğitim verisinde tekrarlanan kişisel veri, anahtar ya da telifli metin de aynı biçimde geri çağrılabilir; tekilleştirme ve kopya taraması bu yüzden güvenlik önlemidir.

Kabul: iki işlevin farksal taramayı geçmesi; k-NN skorunun bağımsız hesapla aynı olması; alan dışı kodun en uzak grup olması; özetlerin benzetmelerden daha uzun kopya içermesi. Ayrıca birleşik fikirlerin iki kavrama en düşük benzerliği tek kavramlı açıklamalarınkinden ortalama en az 0.05 yüksek olmalıdır. Ayrıca MIT lisansında en uzun birebir kopya en az 20 kelime, görülmemiş paragraflarda en çok 6 kelime olmalıdır.

**Kanıt dosyasını oku:** `gruplar`, `ornek_ozet`, `ornek_yaratici`. Soru 1: Ayrılmış gerçek paragrafların kutu içi oranı neden bu kadar düşük? Soru 2: Benzetmelerin 4-gram yeniliği yüksek; bu onları "yaratıcı" yapar mı? Soru 3: Bir modelin eğitim verisini ezberleyip ezberlemediğini ölçmek için hangi ölçüyü tercih ederdin?
:::

::: gorev Gerçek deney · all-minilm gömmeleri ve n-gramlarla gerçek özet, benzetme ve kod metinlerinin yeniliği
Önceki görevlerdeki `yenilik_skoru`, `ngram_yenilik` işlevlerini buraya birleştir (çözümlerini kopyalayabilirsin). Çalıştır gerçek ölçüm tablosunu gösterir; Kontrol Et önce işlevlerini gizli verilerle ve farksal taramayla sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
timeout: 240
```
```starter
import ai_lab
def yenilik_skoru(egitim, yeni, k):
    import math
    out = []
    for v in yeni:
        d = min((math.dist(v, e) for e in egitim))
        out.append({'knn': round(d, 6), 'yuzdelik': 0.0, 'kutu_icinde': True})
    return {'yeni': out, 'dis_oran': 0.0}

def ngram_yenilik(egitim_metinleri, uretilen, n):
    e = set(' '.join(egitim_metinleri).lower().split())
    u = uretilen.lower().split()
    yeni = sum((1 for w in u if w not in e))
    return {'toplam_ngram': len(u), 'yeni_ngram': yeni, 'yenilik_orani': round(yeni / len(u), 6), 'en_uzun_kopya': 1}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_36 as D
    D.goster(yenilik_skoru, ngram_yenilik)
```
```test
import ai_lab
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('_paragraflar', 'kanit_yaz'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
yenilik_skoru = need("yenilik_skoru")
ngram_yenilik = need("ngram_yenilik")
# farksal tarama (görev çözümlerinden derlenen referans)
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef _vektorler(L, d=None):\n    if not isinstance(L, list) or not L:\n        raise ValueError('boş olmayan vektör listesi gerekli')\n    for v in L:\n        if not isinstance(v, list) or not v or (d is not None and len(v) != d) or (len(v) != len(L[0])):\n            raise ValueError('vektörler aynı boyutlu olmalı')\n        for x in v:\n            if isinstance(x, bool) or not isinstance(x, (int, float)) or (not math.isfinite(x)):\n                raise ValueError('sonlu sayı gerekli')\n    return len(L[0])\n\ndef yenilik_skoru(egitim, yeni, k):\n    if isinstance(k, bool) or not isinstance(k, int) or k < 1:\n        raise ValueError('k pozitif tam sayı olmalı')\n    d = _vektorler(egitim)\n    _vektorler(yeni, d)\n    if len(egitim) < k + 1:\n        raise ValueError('eğitimde en az k+1 vektör gerekli')\n\n    def skor(v, haric=None):\n        u = sorted((math.dist(v, e) for i, e in enumerate(egitim) if i != haric))\n        return sum(u[:k]) / k\n    taban = [skor(e, i) for i, e in enumerate(egitim)]\n    lo = [min((e[j] for e in egitim)) for j in range(d)]\n    hi = [max((e[j] for e in egitim)) for j in range(d)]\n    out = []\n    for v in yeni:\n        s = skor(v)\n        out.append({'knn': round(s, 6), 'yuzdelik': round(sum((t <= s for t in taban)) / len(taban), 6), 'kutu_icinde': all((lo[j] <= v[j] <= hi[j] for j in range(d)))})\n    return {'yeni': out, 'dis_oran': round(sum((o['yuzdelik'] > 0.95 for o in out)) / len(out), 6)}\n\ndef _ngramlar(kelimeler, n):\n    return [tuple(kelimeler[i:i + n]) for i in range(len(kelimeler) - n + 1)]\n\ndef ngram_yenilik(egitim_metinleri, uretilen, n):\n    if not isinstance(egitim_metinleri, list) or not egitim_metinleri or (not all((isinstance(m, str) for m in egitim_metinleri))):\n        raise ValueError('boş olmayan str listesi gerekli')\n    if not isinstance(uretilen, str) or isinstance(n, bool) or (not isinstance(n, int)) or (n < 1):\n        raise ValueError('uretilen str, n pozitif tam sayı olmalı')\n    egitim = [m.lower().split() for m in egitim_metinleri]\n    u = uretilen.lower().split()\n    if len(u) < n:\n        raise ValueError('üretilen metin n kelimeden kısa')\n    kume = set((g for k in egitim for g in _ngramlar(k, n)))\n    gram = _ngramlar(u, n)\n    yeni = sum((1 for g in gram if g not in kume))\n    en_uzun = 0\n    m = 1\n    while m <= len(u):\n        km = set((g for k in egitim for g in _ngramlar(k, m)))\n        if any((g in km for g in _ngramlar(u, m))):\n            en_uzun = m\n            m += 1\n        else:\n            break\n    return {'toplam_ngram': len(gram), 'yeni_ngram': yeni, 'yenilik_orani': round(yeni / len(gram), 6), 'en_uzun_kopya': en_uzun}", 'referans', 'exec'), _REF)
_t, _g = _ff(yenilik_skoru, _REF['yenilik_skoru'], ([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0]], [[0.5, 0.5], [5.0, 5.0]], 2), tohum=2348, en_cok=600, mod='tam', butce='oto')
kontrol(_t, "farksal tarama (yenilik_skoru): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(ngram_yenilik, _REF['ngram_yenilik'], (['the cat sat on the mat'], 'the cat sat on a mat', 2), tohum=2317, en_cok=600, mod='tam', butce='oto')
kontrol(_t, "farksal tarama (ngram_yenilik): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
def _red36(f, *a):
    try: f(*a); return False
    except ValueError: return True
_E20 = [[float(i)] for i in range(19)] + [[100.0]]
kontrol(_red36(yenilik_skoru, [[], []], [[]], 1) and yenilik_skoru([[0.0], [1.0], [3.0]], [[4.1]], 1)["yeni"][0]["yuzdelik"] == 0.666667 and yenilik_skoru([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0]], [[2.0, 0.0]], 1)["yeni"][0]["yuzdelik"] == 1.0 and yenilik_skoru(_E20, [[50.0]], 1)["dis_oran"] == 0.0, "yenilik_skoru boş vektör, <= taban, >0.95 ve 6 basamak yuvarlama")
if not all(checks): stop()
from sandbox import ai_gercek_ai_temel_36 as D
try: r = D.deney(yenilik_skoru, ngram_yenilik)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r['fonksiyon_ayni'], 'k-NN yenilik skoru gerçek gömmelerde bağımsız hesapla aynı')
kontrol(r['kod_en_uzak'], 'alan dışı kod gömme uzayında en uzak grup')
kontrol(r['ozet_daha_cok_kopya'], 'özetler benzetmelerden daha uzun birebir kopya içeriyor')
kontrol(r['birlesim_iki_kavrama_yakin'], 'birleşik fikirler gömme uzayında iki kavrama birlikte yakın, tek kavramlı açıklamalar değil')
kontrol(r['ezber_birebir_geri_geliyor'], 'yaygın lisans metni birebir geri geldi, görülmemiş paragraflar gelmedi')
ai_lab.kanit_yaz("ai-temel-36-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-temel-36", "deney": r})
```
```solution
import ai_lab
import math

def _vektorler(L, d=None):
    if not isinstance(L, list) or not L:
        raise ValueError('boş olmayan vektör listesi gerekli')
    for v in L:
        if not isinstance(v, list) or not v or (d is not None and len(v) != d) or (len(v) != len(L[0])):
            raise ValueError('vektörler aynı boyutlu olmalı')
        for x in v:
            if isinstance(x, bool) or not isinstance(x, (int, float)) or (not math.isfinite(x)):
                raise ValueError('sonlu sayı gerekli')
    return len(L[0])

def yenilik_skoru(egitim, yeni, k):
    if isinstance(k, bool) or not isinstance(k, int) or k < 1:
        raise ValueError('k pozitif tam sayı olmalı')
    d = _vektorler(egitim)
    _vektorler(yeni, d)
    if len(egitim) < k + 1:
        raise ValueError('eğitimde en az k+1 vektör gerekli')

    def skor(v, haric=None):
        u = sorted((math.dist(v, e) for i, e in enumerate(egitim) if i != haric))
        return sum(u[:k]) / k
    taban = [skor(e, i) for i, e in enumerate(egitim)]
    lo = [min((e[j] for e in egitim)) for j in range(d)]
    hi = [max((e[j] for e in egitim)) for j in range(d)]
    out = []
    for v in yeni:
        s = skor(v)
        out.append({'knn': round(s, 6), 'yuzdelik': round(sum((t <= s for t in taban)) / len(taban), 6), 'kutu_icinde': all((lo[j] <= v[j] <= hi[j] for j in range(d)))})
    return {'yeni': out, 'dis_oran': round(sum((o['yuzdelik'] > 0.95 for o in out)) / len(out), 6)}

def _ngramlar(kelimeler, n):
    return [tuple(kelimeler[i:i + n]) for i in range(len(kelimeler) - n + 1)]

def ngram_yenilik(egitim_metinleri, uretilen, n):
    if not isinstance(egitim_metinleri, list) or not egitim_metinleri or (not all((isinstance(m, str) for m in egitim_metinleri))):
        raise ValueError('boş olmayan str listesi gerekli')
    if not isinstance(uretilen, str) or isinstance(n, bool) or (not isinstance(n, int)) or (n < 1):
        raise ValueError('uretilen str, n pozitif tam sayı olmalı')
    egitim = [m.lower().split() for m in egitim_metinleri]
    u = uretilen.lower().split()
    if len(u) < n:
        raise ValueError('üretilen metin n kelimeden kısa')
    kume = set((g for k in egitim for g in _ngramlar(k, n)))
    gram = _ngramlar(u, n)
    yeni = sum((1 for g in gram if g not in kume))
    en_uzun = 0
    m = 1
    while m <= len(u):
        km = set((g for k in egitim for g in _ngramlar(k, m)))
        if any((g in km for g in _ngramlar(u, m))):
            en_uzun = m
            m += 1
        else:
            break
    return {'toplam_ngram': len(gram), 'yeni_ngram': yeni, 'yenilik_orani': round(yeni / len(gram), 6), 'en_uzun_kopya': en_uzun}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_36 as D
    D.goster(yenilik_skoru, ngram_yenilik)
```
```hint
İki görevin çözümlerini olduğu gibi buraya koy. Ollama çalışmıyorsa deney onu kendisi başlatır.
```
:::

::: anlat Sınır
Ders interpolation/extrapolation ayrımını, Boden'ın yaratıcılık türlerini ve AlphaGo, AlphaDev, GNoME, FunSearch örneklerini anlatır; görevler gömme uzayında k-NN yeniliğini ve n-gram kopya oranını yazdırır; final adım bunları gerçek model çıktılarında ölçer, ama bu ölçüler yaratıcılığın kendisini değil eğitim verisine uzaklığı gösterir. Yüksek boyutta neredeyse her yeni örnek eğitim kümesinin dışbükey zarfının dışında kalır; bu yüzden 'interpolation' gündelik anlamıyla değil, eğitim dağılımına yakınlık olarak okunmalıdır. Örneklerdeki keşifler arama ile güçlü bir doğrulayıcının (oyun kuralı, birim test, simülasyon) birlikte bulunduğu alanlardan gelir; doğrulayıcısı olmayan alanlarda aynı yöntemin yeni bilgi üreteceği gösterilmiş değildir. GNoME ve ona bağlı otomatik laboratuvar çalışmalarının yenilik iddiaları sonradan tartışılmıştır.

Kaynaklar: [Silver vd. 2016 - Mastering the game of Go with deep neural networks and tree search](https://doi.org/10.1038/nature16961), [Balestriero vd. 2021 - Learning in High Dimension Always Amounts to Extrapolation](https://arxiv.org/abs/2110.09485), [Mankowitz vd. 2023 - Faster sorting algorithms discovered using deep reinforcement learning](https://doi.org/10.1038/s41586-023-06004-9), [Romera-Paredes vd. 2024 - Mathematical discoveries from program search with large language models](https://doi.org/10.1038/s41586-023-06924-6).
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Taklit vs doğrulayıcılı arama (`Interpolation` vs `Extrapolation`) (30 sn).** "Yalnız insan metnini tahmin eden model eğitim dağılımının yakın komşuluğunda birleştirici üretim yapar; `AlphaGo`, `AlphaDev` ve `FunSearch` ise keskin bir doğrulayıcı eşliğinde arama yaparak insan verisinde bulunmayan çözümler keşfeder."
2. **Yüksek boyutta yakınlık ve kopya ölçümü (`k-NN` + `n-gram`) (35 sn).** "Yüksek boyutlu gömme uzayında yeni gerçek örnekler bile koordinat kutusunun dışına düşer; bu yüzden yenilik taban `k-NN` yüzdeliği ve eğitim metninden birebir kopyalanan en uzun `n-gram` dizisiyle birlikte okunur."
3. **Yeniliğin ters yüzü: ezber sızıntısı (`Memorization`) (30 sn).** "Eğitim derleminde binlerce kez tekrarlanan lisans veya sır metinleri önek verildiğinde kelimesi kelimesine geri üretilir; tekilleştirme ve kopya taraması doğrudan gizlilik savunmasıdır."
4. **Soru (25 sn).** "Bir üretimin 4-gram yenilik oranının %95 çıkması o metnin bilimsel olarak doğru veya değerli bir keşif olduğunu neden kanıtlamaz?"
:::
