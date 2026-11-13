---
id: ai-temel-38
title: "LLM Neden İnsan Gibi Düşünmez? · Next-Token Prediction, World Model Tartışması ve Kanıtlar"
summary: Next-token prediction hedefinin ne öğrettiğini küçük bir modelde ölç; reversal curse ve calibration deneyleriyle "anlıyor mu?" sorusunu ölçülebilir parçalara ayır ve iki dakikada anlat.
---

::: anlat 1. Soru: "Bu kadar iyi konuşuyorsa neden insan gibi düşünmüyor?"
Bir konferansta en sık gelen soru budur ve iki kolay cevabı vardır; ikisi de eksiktir:

- **"Sadece otomatik tamamlama, hiçbir şey anlamıyor."** Bu cevap, modellerin eğitim verisinde aynen bulunmayan problemleri çözebilmesini açıklayamaz.
- **"İnsan gibi düşünüyor, sadece daha hızlı."** Bu cevap, modellerin insanın yapmayacağı türden hatalarını açıklayamaz.

Bu derste soruyu ölçülebilir üç parçaya böleceksin:

| Parça | Ölçtüğün şey | Görev |
|---|---|---|
| Eğitim hedefi | Next-token prediction bir metinden ne çıkarır? | 1 |
| Yön asimetrisi | "A, B'dir" öğrenen model "B, A'dır" sorusunu bilir mi? | 2 |
| Kendini bilme | Modelin güveni ile doğruluğu örtüşür mü (`calibration`)? | 3 |

> [!NOT]
> Görevlerdeki modeller senin yazdığın küçük sayım modelleridir; gerçek bir LLM değildir. Amaç, tartışmada kullanılan ölçüleri kendi elinle hesaplamaktır. Gerçek modellerdeki bulgular "Kanıtlar" bölümünde kaynaklarıyla verilir.
:::

::: anlat 2. Next-token prediction ne öğretir?
Bir LLM'in temel eğitimi (`pre-training`) tek bir hedefle yapılır: önündeki token dizisine bakıp sıradaki tokenın olasılık dağılımını tahmin etmek. Sonraki aşamalar (`instruction fine-tuning`, insan tercihlerinden `RLHF`) başka hedefler ekler; ama modelin bilgisinin büyük kısmı bu ilk aşamadan gelir. Ön eğitimin kayıp fonksiyonu `cross-entropy`'dir:

$$\mathcal{L} = -\sum_{t} \log p_\theta(x_t \mid x_{<t})$$

Bu hedef basit görünür ama iyi tahmin için gereken şey basit değildir. "Satranç maçının 30. hamlesinden sonra en olası hamle" sorusunu iyi cevaplamak için tahtanın durumunu bir biçimde izlemek işe yarar. Hedef bunu **zorunlu kılmaz**, yalnız **ödüllendirir**: model aynı kaybı ezberle de, kısa yoldan bir istatistikle de düşürebilir.

Buradan iki sonuç çıkar:

1. Model ne öğrendiğini söylemez; hangi iç temsili kurduğu ayrıca ölçülmelidir (`probing`, `intervention`).
2. Model eğitildiği **yönde** iyi olmaya yatkındır. Hedef "soldan sağa tahmin" olduğu için, eğitim verisinde yalnız bir yönde geçen bir bilgi ters yönde sorulduğunda geri çağrılamayabilir. Bu, belirli eğitim ve sınama koşullarında ölçülmüş bir bulgudur; her bilginin tek yönde depolandığının genel kanıtı değildir. Görev 2 bunu ölçer.

İnsanla temel farklar (bunlar mimari gerçeklerdir, görüş değildir):

| Özellik | LLM | İnsan |
|---|---|---|
| Öğrenme zamanı | Eğitimde; kullanım sırasında `weights` değişmez | Sürekli (`continual learning`) |
| Bellek | `context window` içindeki metin; oturum bitince kaybolur | Kalıcı, yeniden düzenlenen |
| Veri | Trilyon token mertebesinde metin | Çok daha az dil, ama beden ve duyularla |
| Hata sinyali | Sıradaki token doğru mu? | Dünyadan gelen sonuç |
| Kendi bilgisini bilme | Ayrıca eğitilmedikçe zayıf (`calibration`) | Kusurlu ama var |
:::

::: anlat 3. World model tartışması: iki görüş ve kanıtları
Buradan sonrası tartışmalıdır. Aşağıdaki iki pozisyon **görüştür**; altlarındaki deneyler ise yayımlanmış ölçümlerdir.

**Görüş A · "İstatistiksel papağan".** Bender ve arkadaşları (2021), dil modelinin biçimi öğrendiğini, anlamı öğrenmediğini savunur: model, anlama referansı olmadan olası kelime dizilerini birleştirir.

**Görüş B · "İç dünya modeli kuruyor".** Bu görüşe göre iyi tahmin için model verinin arkasındaki süreci temsil etmeyi öğrenir.

Kanıtlar iki yöne de vardır:

- **B lehine:** Li ve arkadaşları (2023), yalnız Othello hamle dizileriyle eğitilmiş bir GPT'nin iç aktivasyonlarından tahta durumunun okunabildiğini gösterdi. Tahta modele hiç gösterilmemişti. Aktivasyona müdahale edip tahtadaki bir taşı "değiştirdiklerinde" modelin önerdiği hamleler de buna uygun değişti. Nanda ve arkadaşları (2023) bu temsilin doğrusal olduğunu gösterdi.
- **A lehine:** Berglund ve arkadaşları (2023), "A, B'dir" cümleleriyle eğitilen modellerin "B kimdir?" sorusunu rastgele düzeyde cevapladığını ölçtü (`reversal curse`). Bir insan "Ayşe'nin annesi Fatma'dır" bilgisinden "Fatma'nın çocuğu Ayşe'dir" sonucunu çıkarır; model, bilgi `context window` içinde değilse çıkaramaz.

Bu ikisi çelişmez. Model bazı alanlarda verinin arkasındaki yapıyı temsil eder, bazı alanlarda yüzey istatistiğinde kalır. Hangisinin olduğu alana, veriye ve modele göre değişir ve **her iddia için ayrıca ölçülmelidir**. "Anlıyor" ya da "anlamıyor" tek kelimelik cevapları bu yüzden yanlıştır.

> [!NOT]
> Othello sonucu küçük ve kapalı bir oyun içindir; "LLM'ler fiziksel dünyanın modelini kurar" iddiasını kanıtlamaz. Reversal curse sonucu da "LLM mantık yürütemez" demek değildir: bilgi istemde verildiğinde modeller ters yönü çıkarabilir.
:::

::: tahmin Ters yönde sorulan soru
Aşağıdaki sayım modeli yalnız "sıradaki kelime" sayar. Üç cümleyle eğitiliyor. `ayse` ve `fatma` için en olası sıradaki kelime ne yazdırılır?

```python
from collections import Counter, defaultdict

cumleler = ["ayse nin annesi fatma", "ali nin annesi zeynep", "can in annesi elif"]
sonraki = defaultdict(Counter)
for c in cumleler:
    k = c.split()
    for a, b in zip(k, k[1:]):
        sonraki[a][b] += 1

print("ayse ->", sonraki["ayse"].most_common(1))
print("fatma ->", sonraki["fatma"].most_common(1))
```

???

```cikti
ayse -> [('nin', 1)]
fatma -> []
```
`fatma` eğitimde yalnız cümle **sonunda** geçti; ondan sonra gelen bir kelime hiç görülmedi. Model "fatma" ile "ayse" arasındaki ilişkiyi tek yönde sakladı. Bu, `reversal curse`'ün en küçük hâlidir. Gerçek LLM'lerde mekanizma çok daha karmaşıktır; Berglund ve arkadaşları benzer bir asimetriyi belirli eğitim ve sınama koşullarında ölçtü.
:::

::: gorev 1 · Next-token dağılımını metinden çıkar
`sonraki_token_dagilimi(cumleler)` işlevini yaz. Bu, bir dil modelinin eğitim hedefinin en küçük sürümüdür.

- `cumleler`: boş olmayan `str` listesi. Token ayırma `split()` ile yapılır.
- Dönüş: `{kelime: [[sonraki, olasilik], ...]}`. Olasılık, o kelimeden sonra gelenlerin sayımının toplam sayıma oranıdır, 6 basamağa yuvarlanır.
- Her liste önce olasılığa göre azalan, eşitlikte alfabetik sıralanır.
- Kendisinden sonra hiçbir kelime gelmeyen kelime sözlükte **bulunmaz**.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç her çift için önceki sayımı siliyor ve olasılığı hep 1 yazıyor.

```starter
def sonraki_token_dagilimi(cumleler):
    out = {}
    for c in cumleler:
        k = c.split()
        for a, b in zip(k, k[1:]):
            out[a] = [[b, 1.0]]
    return out
```

```solution
def sonraki_token_dagilimi(cumleler):
    if not isinstance(cumleler, list) or not cumleler or any(not isinstance(c, str) for c in cumleler):
        raise ValueError('cumleler boş olmayan str listesi olmalı')
    say = {}
    for c in cumleler:
        k = c.split()
        for a, b in zip(k, k[1:]):
            say.setdefault(a, {})
            say[a][b] = say[a].get(b, 0) + 1
    out = {}
    for a, d in say.items():
        toplam = sum(d.values())
        out[a] = sorted(([b, round(n / toplam, 6)] for b, n in d.items()), key=lambda x: (-x[1], x[0]))
    return out
```

```test
need('sonraki_token_dagilimi')
import random

def _ref(cumleler):
    say = {}
    for c in cumleler:
        k = c.split()
        for i in range(len(k) - 1):
            say.setdefault(k[i], {})
            say[k[i]][k[i + 1]] = say[k[i]].get(k[i + 1], 0) + 1
    return {a: sorted(([b, round(n / sum(d.values()), 6)] for b, n in d.items()), key=lambda x: (-x[1], x[0])) for a, d in say.items()}

eq(sonraki_token_dagilimi(["a b", "a c", "a b"]), {"a": [["b", 0.666667], ["c", 0.333333]]}, 'sayım ve normalizasyon')
eq(sonraki_token_dagilimi(["x z", "x y"]), {"x": [["y", 0.5], ["z", 0.5]]}, 'eşit olasılıkta alfabetik sıra')
eq(sonraki_token_dagilimi(["tek"]), {}, 'ardılı olmayan kelime sözlükte yok')
eq(sonraki_token_dagilimi(["ayse nin annesi fatma"]).get("fatma"), None, 'cümle sonundaki kelimenin ardılı yok')
rng = random.Random(3817)
for _ in range(25):
    sozluk = [f"k{i}" for i in range(rng.randint(2, 6))]
    cumleler = [" ".join(rng.choice(sozluk) for _ in range(rng.randint(1, 7))) for _ in range(rng.randint(1, 8))]
    eq(sonraki_token_dagilimi(cumleler), _ref(cumleler), 'rastgele derlemde bağımsız referansla aynı')
girdi = ["a b c"]
sonraki_token_dagilimi(girdi)
eq(girdi, ["a b c"], 'girdi değişmez')
for kotu in (None, [], "a b", [1], ["a", None], ("a b",)):
    raises(ValueError, sonraki_token_dagilimi, kotu, msg='bozuk girdi reddedilir')
```

```hint
Önce iç içe sözlükte say (`say[a][b] += 1`), sonra her `a` için toplamı bulup oranla. Sıralama anahtarı `(-olasilik, kelime)`.
```
:::

::: gorev 2 · Yön asimetrisini ölç (reversal curse)
Bir modelin "A → B" bilgisini ters yönde de bilip bilmediğini ölçen `yon_asimetrisi(tahmin_et, ciftler)` işlevini yaz. Bu ölçü modelden bağımsızdır: `tahmin_et` bir sayım modeli de, gerçek bir LLM çağrısı da olabilir.

- `tahmin_et`: tek `str` alıp tahminini (`str` ya da `None`) döndüren çağrılabilir.
- `ciftler`: boş olmayan liste; her öğe iki boş olmayan `str` içeren `(a, b)` demeti ya da listesi.
- `ileri`: `tahmin_et(a) == b` olan çiftlerin oranı. `geri`: `tahmin_et(b) == a` olan çiftlerin oranı.
- Dönüş: `{'ileri': ..., 'geri': ..., 'fark': ileri - geri}`; değerler 4 basamağa yuvarlanır.
- `tahmin_et` hata fırlatırsa o sorgu **yanlış** sayılır; ölçüm durmaz.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç yalnız ileri yönü ölçüp aynı sayıyı geri yön diye raporluyor: asimetriyi görünmez kılan hata budur.

```starter
def yon_asimetrisi(tahmin_et, ciftler):
    dogru = sum(1 for a, b in ciftler if tahmin_et(a) == b)
    oran = round(dogru / len(ciftler), 4)
    return {'ileri': oran, 'geri': oran, 'fark': 0.0}
```

```solution
def yon_asimetrisi(tahmin_et, ciftler):
    if not callable(tahmin_et):
        raise ValueError('tahmin_et çağrılabilir olmalı')
    if not isinstance(ciftler, list) or not ciftler:
        raise ValueError('ciftler boş olmayan liste olmalı')
    for c in ciftler:
        if not isinstance(c, (tuple, list)) or len(c) != 2 or any(not isinstance(x, str) or not x for x in c):
            raise ValueError('her çift iki boş olmayan str içermeli')

    def dogru_mu(soru, beklenen):
        try:
            return tahmin_et(soru) == beklenen
        except Exception:
            return False

    n = len(ciftler)
    ileri = sum(1 for a, b in ciftler if dogru_mu(a, b)) / n
    geri = sum(1 for a, b in ciftler if dogru_mu(b, a)) / n
    return {'ileri': round(ileri, 4), 'geri': round(geri, 4), 'fark': round(ileri - geri, 4)}
```

```test
need('yon_asimetrisi')
import random

ciftler = [("ayse", "fatma"), ("ali", "zeynep"), ("can", "elif"), ("ece", "nur")]
tek_yon = {a: b for a, b in ciftler}
cift_yon = dict(tek_yon); cift_yon.update({b: a for a, b in ciftler})
eq(yon_asimetrisi(tek_yon.get, ciftler), {'ileri': 1.0, 'geri': 0.0, 'fark': 1.0}, 'yalnız ileri yönü bilen model')
eq(yon_asimetrisi(cift_yon.get, ciftler), {'ileri': 1.0, 'geri': 1.0, 'fark': 0.0}, 'iki yönü bilen model')
eq(yon_asimetrisi({b: a for a, b in ciftler}.get, ciftler), {'ileri': 0.0, 'geri': 1.0, 'fark': -1.0}, 'yalnız ters yönü bilen model: fark negatif')
eq(yon_asimetrisi(lambda s: None, ciftler), {'ileri': 0.0, 'geri': 0.0, 'fark': 0.0}, 'hiçbir şey bilmeyen model')

def patlayan(s):
    if s == "ali":
        raise RuntimeError('model hatası')
    return tek_yon.get(s)
eq(yon_asimetrisi(patlayan, ciftler), {'ileri': 0.75, 'geri': 0.0, 'fark': 0.75}, 'hata fırlatan sorgu yanlış sayılır, ölçüm sürer')

rng = random.Random(3802)
for _ in range(20):
    n = rng.randint(1, 9)
    cc = [(f"a{i}", f"b{i}") for i in range(n)]
    tablo = {}
    for a, b in cc:
        if rng.random() < 0.6:
            tablo[a] = b
        if rng.random() < 0.3:
            tablo[b] = a
    il = sum(1 for a, b in cc if tablo.get(a) == b) / n
    ge = sum(1 for a, b in cc if tablo.get(b) == a) / n
    eq(yon_asimetrisi(tablo.get, cc), {'ileri': round(il, 4), 'geri': round(ge, 4), 'fark': round(il - ge, 4)}, 'rastgele tabloda bağımsız hesapla aynı')
eq(yon_asimetrisi(tek_yon.get, [["ayse", "fatma"]]), {'ileri': 1.0, 'geri': 0.0, 'fark': 1.0}, 'liste biçimli çift kabul edilir')
for kotu in (None, [], [("a",)], [("a", "b", "c")], [{"a": 1, "b": 2}], [("a", 1)], [("", "b")], "ab", (("a", "b"),)):
    raises(ValueError, yon_asimetrisi, tek_yon.get, kotu, msg='bozuk çift listesi reddedilir')
raises(ValueError, yon_asimetrisi, "model", ciftler, msg='çağrılamayan model reddedilir')
```

```hint
İki ayrı sayım yap: biri `tahmin_et(a) == b`, diğeri `tahmin_et(b) == a`. Çağrıyı `try/except` içine al; hata yanlış sayılır.
```
:::

::: gorev 3 · Güven ile doğruluk örtüşüyor mu? (Expected Calibration Error)
İnsan "bilmiyorum" diyebilir. Bir modelin bunu yapabilmesi için verdiği olasılığın gerçek doğruluk oranıyla örtüşmesi gerekir; buna `calibration` denir. `kalibrasyon_hatasi(guvenler, dogrular, kutu_sayisi)` işlevini yaz.

- `guvenler`: `[0, 1]` aralığında sayılardan oluşan boş olmayan liste (modelin cevabına verdiği olasılık).
- `dogrular`: aynı uzunlukta `bool` listesi (cevap gerçekten doğru muydu).
- `kutu_sayisi`: pozitif `int`. Güven `g`, `min(int(g * kutu_sayisi), kutu_sayisi - 1)` numaralı kutuya düşer.
- Her dolu kutu için ortalama güven ile doğruluk oranının mutlak farkını al; kutudaki örnek oranıyla ağırlıklandırıp topla: bu `ece`'dir.
- Dönüş: `{'ece': ..., 'ortalama_guven': ..., 'dogruluk': ...}`; değerler 6 basamağa yuvarlanır.
- Bozuk girdi `ValueError` (`bool` bir güven değeri değildir).

KUSURLU başlangıç yalnız genel ortalamaları karşılaştırıyor. Aşırı emin olunan yanlışlar ile az emin olunan doğrular birbirini götürür ve model kusursuz kalibre görünür.

```starter
def kalibrasyon_hatasi(guvenler, dogrular, kutu_sayisi):
    g = sum(guvenler) / len(guvenler)
    d = sum(dogrular) / len(dogrular)
    return {'ece': round(abs(g - d), 6), 'ortalama_guven': round(g, 6), 'dogruluk': round(d, 6)}
```

```solution
def kalibrasyon_hatasi(guvenler, dogrular, kutu_sayisi):
    if isinstance(kutu_sayisi, bool) or not isinstance(kutu_sayisi, int) or kutu_sayisi < 1:
        raise ValueError('kutu_sayisi pozitif int olmalı')
    if not isinstance(guvenler, list) or not isinstance(dogrular, list) or not guvenler or len(guvenler) != len(dogrular):
        raise ValueError('listeler boş olmamalı ve aynı uzunlukta olmalı')
    for g in guvenler:
        if isinstance(g, bool) or not isinstance(g, (int, float)) or not 0 <= g <= 1:
            raise ValueError('güven [0, 1] aralığında sayı olmalı')
    if any(not isinstance(d, bool) for d in dogrular):
        raise ValueError('dogrular bool olmalı')
    kutular = [[0, 0.0, 0] for _ in range(kutu_sayisi)]
    for g, d in zip(guvenler, dogrular):
        i = min(int(g * kutu_sayisi), kutu_sayisi - 1)
        kutular[i][0] += 1
        kutular[i][1] += g
        kutular[i][2] += 1 if d else 0
    n = len(guvenler)
    ece = sum((adet / n) * abs(toplam / adet - dogru / adet) for adet, toplam, dogru in kutular if adet)
    return {'ece': round(ece, 6), 'ortalama_guven': round(sum(guvenler) / n, 6), 'dogruluk': round(sum(dogrular) / n, 6)}
```

```test
need('kalibrasyon_hatasi')
import random

def _ref(gs, ds, k):
    n = len(gs)
    ece = 0.0
    for i in range(k):
        idx = [j for j in range(n) if min(int(gs[j] * k), k - 1) == i]
        if idx:
            ece += (len(idx) / n) * abs(sum(gs[j] for j in idx) / len(idx) - sum(1 for j in idx if ds[j]) / len(idx))
    return {'ece': round(ece, 6), 'ortalama_guven': round(sum(gs) / n, 6), 'dogruluk': round(sum(1 for d in ds if d) / n, 6)}

r = kalibrasyon_hatasi([0.9, 0.9, 0.1, 0.1], [False, False, True, True], 2)
eq(r, {'ece': 0.9, 'ortalama_guven': 0.5, 'dogruluk': 0.5}, 'ortalamalar eşit ama kutularda hata büyük')
eq(kalibrasyon_hatasi([1.0, 1.0, 0.0, 0.0], [True, True, False, False], 5)['ece'], 0.0, 'kusursuz kalibrasyon')
eq(kalibrasyon_hatasi([1.0], [False], 10), {'ece': 1.0, 'ortalama_guven': 1.0, 'dogruluk': 0.0}, 'g = 1.0 son kutuya düşer')
eq(kalibrasyon_hatasi([0.8, 0.8, 0.8, 0.8, 0.8], [True, True, True, True, False], 10)['ece'], 0.0, '%80 güven, %80 doğruluk')
eq(kalibrasyon_hatasi([0.2, 0.7], [True, False], 1), {'ece': 0.05, 'ortalama_guven': 0.45, 'dogruluk': 0.5}, 'tek kutuda genel ortalamaya iner')
rng = random.Random(3803)
for _ in range(25):
    n = rng.randint(1, 30)
    gs = [round(rng.random(), 3) for _ in range(n)]
    ds = [rng.random() < g for g in gs]
    k = rng.randint(1, 12)
    eq(kalibrasyon_hatasi(gs, ds, k), _ref(gs, ds, k), 'rastgele veride bağımsız referansla aynı')
gs, ds = [0.3, 0.6], [True, False]
kalibrasyon_hatasi(gs, ds, 4)
eq((gs, ds), ([0.3, 0.6], [True, False]), 'girdiler değişmez')
for a in ([[], [], 3], [[0.5], [True, False], 3], [[0.5], (True,), 3], [[1.2], [True], 3], [[-0.1], [True], 3], [[float('nan')], [True], 3], [[True], [True], 3], [[0.5], [1], 3], [[0.5], [True], 0], [[0.5], [True], 2.0], [[0.5], [True], True], [(0.5,), [True], 3], [["0.5"], [True], 3]):
    raises(ValueError, kalibrasyon_hatasi, *a, msg='bozuk girdi reddedilir')
```

```hint
Her kutu için üç şey tut: örnek sayısı, güven toplamı, doğru sayısı. Boş kutuyu atla. `ece = Σ (adet / n) · |ortalama güven − doğruluk|`.
```
:::

::: anlat 4. Yaygın yanlışlar
| Yanlış | Neden yanlış | Doğrusu |
|---|---|---|
| "LLM bir veritabanından cevap arar." | Modelde aranacak ayrı bir kayıt deposu yoktur; `weights` içinde çoğunlukla sıkıştırılmış istatistik vardır. Yine de sık geçen ya da ayırt edici bazı eğitim dizileri `weights` içinde ezberlenir ve sorguyla birebir geri alınabilir (`training data extraction`). | Model cevabı her seferinde token token **üretir**; bu yüzden var olmayan şeyi de akıcı üretebilir. |
| "Sadece otomatik tamamlama." | Othello-GPT gibi deneyler, hedefin basit olmasının öğrenilen temsilin basit olması anlamına gelmediğini gösterdi. | Hedef basit, öğrenilen şey alana göre karmaşık olabilir; iddia başına ölçülür. |
| "Konuşurken öğreniyor." | Kullanım sırasında `weights` değişmez. | Model yalnız `context window` içindekini kullanır; oturum bitince bu bilgi gider (ayrı bir bellek sistemi yoksa). |
| "Emin konuşuyorsa doğrudur." | Akıcılık ve güven, doğrulukla aynı şey değildir (Görev 3). | Güvenin doğrulukla örtüşmesi (`calibration`) ayrıca ölçülür. |
| "Benchmark'ta insanı geçti, demek insan gibi düşünüyor." | Benchmark dar bir yeteneği ölçer; veri eğitim setine sızmış olabilir. | Skor, o test için bir ölçümdür; genel zekâ iddiası değildir. |
:::

::: anlat 5. Bunu iki dakikada nasıl anlatırsın?
Aşağıdaki iskeleti kendi cümlelerinle doldur. Her adım bu derste ölçtüğün bir şeye dayanır.

1. **Tek cümlelik çerçeve (15 sn).** "Bir dil modelinin temel eğitimi tek bir iştir: sıradaki kelimeyi tahmin etmek. İlginç olan, bu işi iyi yapmak için neler öğrenmek zorunda kaldığıdır."
2. **Lehte kanıt (30 sn).** Othello deneyi: model tahtayı hiç görmedi ama içinde tahtanın durumu okunabiliyor. "Yani yalnız kelime saymıyor."
3. **Aleyhte kanıt (30 sn).** Reversal curse: "Ayşe'nin annesi Fatma" öğrenen model "Fatma'nın çocuğu kim?" sorusunu bilemiyor. Bir çocuk bunu bilir. Görev 2'deki sayıyı söyle: ileri 1.0, geri 0.0.
4. **Fark (30 sn).** İnsan konuşurken öğrenir ve neyi bilmediğini bir ölçüde bilir. Model kullanım sırasında öğrenmez ve güveni doğruluğuyla örtüşmeyebilir.
5. **Kapanış (15 sn).** "Soru 'anlıyor mu, anlamıyor mu' değil; 'hangi işte, neyi, ne kadar güvenilir yapıyor' ve bunu ölçebiliyoruz."

Salondan gelebilecek iki soru ve dürüst cevapları:

- *"Peki bilinci var mı?"* Bu derste ölçtüğün hiçbir şey bilinç hakkında bir şey söylemez; bilincin üzerinde uzlaşılmış bir ölçüsü yoktur. "Bilmiyoruz ve elimizdeki testler bunu ölçmüyor" doğru cevaptır.
- *"Daha büyük model bu sorunları çözer mi?"* Bazılarını azaltır (bilgi kapsamı), bazıları eğitim hedefinden gelir (yön asimetrisi) ve yalnız büyütmekle kaybolmaz. Ayrıntı `ai-temel-31` (scaling laws) dersindedir.
:::

::: anlat Sınır
Bu ders next-token prediction hedefini, world model tartışmasını ve iki ölçüyü (yön asimetrisi, Expected Calibration Error) anlatır. Görevlerdeki modeller sayım tabloları ve sözlüklerdir; gerçek bir LLM'in iç temsilini ölçmez. Tahmin adımındaki `reversal curse` örneği mekanizmanın en yalın hâlidir: gerçek modellerde bilgi `context window` içinde verildiğinde ters yön çıkarılabilir, sorun `weights` içinde depolanmış bilgidedir. Othello-GPT bulgusu kapalı ve küçük bir oyun içindir; fiziksel dünya modeline genellenemez. "İstatistiksel papağan" ve "iç dünya modeli" pozisyonları görüştür; alan bu konuda uzlaşmış değildir. ECE kutu sayısına duyarlıdır ve tek başına bir modelin "neyi bilmediğini bildiğini" kanıtlamaz. Bilinç, niyet ve öznel deneyim bu dersin ölçülerinin dışındadır.

Kaynaklar: [Carlini vd. 2021 - Extracting Training Data from Large Language Models](https://arxiv.org/abs/2012.07805), [Li vd. 2023 - Emergent World Representations (Othello-GPT)](https://arxiv.org/abs/2210.13382), [Nanda vd. 2023 - Emergent Linear Representations in World Models](https://arxiv.org/abs/2309.00941), [Berglund vd. 2023 - The Reversal Curse](https://arxiv.org/abs/2309.12288), [Bender vd. 2021 - On the Dangers of Stochastic Parrots](https://doi.org/10.1145/3442188.3445922), [Guo vd. 2017 - On Calibration of Modern Neural Networks](https://arxiv.org/abs/1706.04599).
:::

::: dusun
Bir arkadaşın "ChatGPT'ye sordum, çok emin cevap verdi, demek doğru" diyor. Görev 3'teki ilk test örneğini (dört cevap, ortalama güven 0.5, doğruluk 0.5, `ece` 0.9) kullanarak ona 30 saniyede neyin yanlış olduğunu anlat. Sonra kendine sor: aynı örnekte yalnız genel ortalamaya bakan biri hangi sonuca varırdı?
:::

::: ozet
- LLM'in ön eğitimi tek bir hedefle yapılır: `next-token prediction`; `fine-tuning` ve `RLHF` sonraki aşamalarda başka hedefler ekler. Hedef basittir; iyi tahmin için öğrenilen temsil alana göre karmaşık olabilir ve ayrıca ölçülmelidir.
- Bilgi tahmin edildiği yönde geri çağrılmaya yatkındır: "A → B" öğrenen model "B → A"yı bilmeyebilir (`reversal curse`). Yön asimetrisi `ileri − geri` farkıyla ölçülür.
- Model kullanım sırasında öğrenmez; yalnız `context window` içindekini kullanır.
- Akıcılık ve güven doğruluk değildir. `Expected Calibration Error`, güven ile doğruluğun kutu kutu ne kadar ayrıştığını ölçer; genel ortalama bu hatayı gizleyebilir.
- "Anlıyor" ve "anlamıyor" tek kelimelik cevapları yanlıştır. Doğru soru: hangi işte, neyi, ne kadar güvenilir yapıyor?
:::
