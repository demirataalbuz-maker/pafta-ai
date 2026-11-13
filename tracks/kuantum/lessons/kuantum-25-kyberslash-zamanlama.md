---
id: kuantum-25
title: "KyberSlash · Secret-Dependent İşlem ve Zamanlama"
summary: Güvenli bir algoritmanın gizli değere bağlı işlem süresi yüzünden nasıl güvensiz uygulanabildiğini KyberSlash üzerinden anlat; iki zamanlama örneklemini Welch t ile karşılaştır ve sızıntı ile sabit adımlı karşılaştırmayı adım sayısıyla modelle.
esleme: kuantum-21, kuantum-26, kuantum-28, kuantum-23
timeout: 30
---

::: anlat 1. Algoritma güvenli, uygulama sızdırıyor
Bernstein, Bhargavan, Bhasin ve arkadaşlarının *KyberSlash: Exploiting secret-dependent division timings in Kyber implementations* çalışması (IACR ePrint 2024/1049, TCHES 2025), bazı Kyber uygulamalarında iki zamanlama açığı (KyberSlash1 ve KyberSlash2) buldu. Sorun matematiksel değildi. Uygulamalar gizli bir değere bağlı bir **bölme** işlemi yapıyordu ve bu işlemin süresi işlemcide girdiye göre değişiyordu. Saldırgan yanıt sürelerini ölçerek gizli anahtar hakkında bilgi topladı. Makaleye göre Raspberry Pi 2 (Arm Cortex-A7) ve Arm Cortex-M4 üzerinde gizli anahtar KyberSlash2 için dakikalar, KyberSlash1 için birkaç saat içinde güvenilir biçimde kurtarıldı. Açıklar bildirimin ardından yamalandı.

Ders şudur: ML-KEM'in güvenlik varsayımı bu saldırıyla kırılmadı. Kırılan, **uygulamanın** gizli değere bağlı süre harcamasıydı. Güvenli bir algoritma, işlem süresi gizli veriye bağlı olan bir kodla güvensiz uygulanabilir. Bu yüzden kriptografik kodda gizli veriye bağlı dallanma, bellek erişimi ve değişken süreli işlem (bölme gibi) kaçınılacak şeylerdir.

> [!NOTE]
> Bu derste gerçek bir anahtar kurtarma ya da yerel (*native*) zamanlama ölçümü yapılmaz. Zamanlama örnekleri **sentetiktir**. Görev 2'deki "adım sayısı", işlem süresinin deterministik bir **modelidir**. Python'da koşulsuz görünen bir kodun gerçekten sabit zamanlı olduğu iddia edilmez.
:::

::: anlat 2. Mekanizma: iki örneklemi karşılaştırmak
Zamanlama sızıntısını aramanın en basit yolu, iki girdi grubunu (ör. "gizli bit 0" ve "gizli bit 1") ayrı ayrı ölçüp ortalamaları karşılaştırmaktır. Ama tek başına ortalama farkı anlamsızdır: gürültü büyükse büyük bir fark tesadüf olabilir. **Welch t istatistiği** farkı standart hata ölçeğine koyar:

`t = (ort(a) − ort(b)) / √(var(a)/n + var(b)/m)`

Burada `var`, örneklem varyansıdır (`n − 1` paydalı). Welch'in sürümü iki grubun varyanslarının eşit olduğunu varsaymaz. Büyük bir |t| "bu fark gürültüyle açıklanması zor" der; nedenini söylemez. Önbellek, işlemci frekansı, zamanlayıcı ve ölçüm sırası da fark üretebilir. Grupları karıştırarak ölçmek ve örnek sayısını önceden belirlemek gerekir.

Önleyici tarafta hedef, işlem süresinin gizli veriden **bağımsız** olmasıdır. Basit bir örnek: iki dizgeyi karşılaştırırken ilk farkta durmak (erken çıkış), farkın nerede olduğunu süreye yansıtır. Bütün baytları her zaman dolaşıp farkları biriktirmek ise süreyi yalnız uzunluğa bağlar.

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| "Algoritma kırılmadı, uygulama güvenli" | Gizli değere bağlı işlem süresi bilgi sızdırır | Uygulamayı ayrıca sabit zamanlılık için denetle |
| Yalnız ortalama farkına bakmak | Gürültü büyükse fark tesadüf olabilir | Farkı standart hatayla ölçekle (t) |
| Varyansta `n` paydası | Küçük örneklemde varyansı küçük tahmin eder | Örneklem varyansı: `n − 1` |
| Büyük |t| = anahtar kurtarıldı | t yalnız fark olduğunu söyler, nedenini ve sömürülebilirliği değil | t bir alarmdır, kanıt değil |
| İlk farkta duran karşılaştırma | Süre farkın konumunu sızdırır | Bütün baytları dolaş, farkları biriktir |
:::

::: tahmin Aynı fark, farklı gürültü
İki deneyde gruplar arasındaki ortalama fark aynı: 2 birim. Birinde gürültü az, diğerinde çok. t değerleri nasıl karşılaştırılır?

```python
import statistics, math

def t(a, b):
    return (statistics.mean(a) - statistics.mean(b)) / math.sqrt(statistics.variance(a) / len(a) + statistics.variance(b) / len(b))

az_gurultu = ([101, 102, 101, 102], [99, 100, 99, 100])
cok_gurultu = ([90, 112, 95, 109], [99, 100, 99, 100])
print(round(t(*az_gurultu), 3), round(t(*cok_gurultu), 3))
```

???

```cikti
4.899 0.375
```
İki deneyde de ortalama fark 2. Az gürültülü deneyde bu fark standart hatanın yaklaşık 4,9 katıdır; çok gürültülü deneyde yarısından bile azdır. Aynı farkın anlamı gürültüye göre değişir.
:::

::: gorev 1 · Welch t ile iki sentetik zamanlama örneklemini karşılaştır
`welch_olc(a, b)` işlevini yaz.

- `a` ve `b` en az iki öğeli `list`'ler; her öğe `bool` olmayan, sonlu (`math.isfinite`) bir `int` ya da `float`. Değilse `ValueError`.
- `fark = mean(a) − mean(b)`; varyans örneklem varyansıdır (`statistics.variance`, `n − 1` paydalı).
- `t = fark / √(var(a)/len(a) + var(b)/len(b))`.
- Payda `0` ise: `fark == 0` → `t = 0.0`; aksi halde `t = None` (sonlu değil).
- Dönüş: `{'fark': round(fark, 6), 't': round(t, 6) ya da None}`.

KUSURLU başlangıç varyansı `n` paydasıyla (`pvariance`) hesaplıyor ve sıfır paydada bölme hatası veriyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
Path('ornek.json').write_text('[[101, 102, 101, 102], [99, 100, 99, 100]]', encoding='utf-8')
```

```starter
import math, statistics

def welch_olc(a, b):
    fark = statistics.mean(a) - statistics.mean(b)
    t = fark / math.sqrt(statistics.pvariance(a) / len(a) + statistics.pvariance(b) / len(b))
    return {'fark': round(fark, 6), 't': round(t, 6)}

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(welch_olc(*_args))
```

```solution
import math, statistics

def welch_olc(a, b):
    for x in (a, b):
        if (not isinstance(x, list) or len(x) < 2
                or any(type(v) not in (int, float) or not math.isfinite(v) for v in x)):
            raise ValueError('her orneklem en az iki sonlu sayi olmali')
    fark = statistics.mean(a) - statistics.mean(b)
    payda = math.sqrt(statistics.variance(a) / len(a) + statistics.variance(b) / len(b))
    if payda:
        t = fark / payda
    else:
        t = 0.0 if fark == 0 else None
    return {'fark': round(fark, 6), 't': round(t, 6) if t is not None else None}

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(welch_olc(*_args))
```

```test
need('welch_olc')
import copy
_a, _b = [101, 102, 101, 102], [99, 100, 99, 100]
_yedek = copy.deepcopy((_a, _b))
eq(welch_olc(_a, _b), {'fark': 2.0, 't': 4.898979}, 'az gürültü: t ≈ 4,90 (n - 1 paydalı varyans)')
eq((_a, _b), _yedek, 'girdiler değişmemeli')
eq(welch_olc([90, 112, 95, 109], _b), {'fark': 2.0, 't': 0.374634}, 'aynı fark, çok gürültü: t küçük')
eq(welch_olc(_b, _a), {'fark': -2.0, 't': -4.898979}, 'grupların sırası işareti çevirir')
eq(welch_olc([1, 2, 3], [1, 2]), {'fark': 0.5, 't': 0.654654}, 'farklı örneklem boyutları')
eq(welch_olc([5, 5], [5, 5]), {'fark': 0.0, 't': 0.0}, 'sıfır payda ve sıfır fark: t = 0.0')
eq(welch_olc([6, 6], [5, 5]), {'fark': 1.0, 't': None}, 'sıfır payda ama fark var: t tanımsız (None)')
eq(welch_olc([1.5, 2.5], [0.5, 0.5]), {'fark': 1.5, 't': 3.0}, 'float örnekler')
eq(welch_olc([1, 2, 3, 4], [1, 2, 3, 3])['t'], 0.311086, '6 basamağa yuvarlanır')
eq(welch_olc([1, 2, 2], [0, 1]), {'fark': 1.166667, 't': 1.941451}, 'devirli fark ve t 6 basamağa yuvarlanır')
for _arg in (([1], [1, 2]), ([1, 2], [3]), ([1, 2], []), ((1, 2), [1, 2]), ([1, True], [1, 2]), ([1, '2'], [1, 2]),
             ([1, float('nan')], [1, 2]), ([1, 2], [float('inf'), 2]), ([1, None], [1, 2])):
    raises(ValueError, welch_olc, *_arg, msg=f'bozuk örneklem ValueError: {_arg!r}')
```

```hint
Önce iki örneklemi aynı kurallarla doğrula. `statistics.variance` örneklem varyansıdır (`n − 1`); `pvariance` değil. Paydanın sıfır olduğu durumu bölmeden önce ele al.
```
:::

::: gorev 2 · Erken çıkışlı ve sabit adımlı karşılaştırmayı modelle
İşlem süresini adım sayısıyla modelleyen `karsilastir(a, b, sabit)` işlevini yaz.

- `a` ve `b` `bytes`; `sabit` bir `bool`. Değilse `ValueError`.
- Uzunluklar farklıysa: `{'esit': False, 'adim': 0}` (uzunluk açık bilgidir; bu modelde gizli sayılmaz).
- Uzunluklar eşitse ve `sabit is False` (erken çıkış): baytları baştan gez; her karşılaştırma bir adımdır; ilk farkta dur. `adim` = yapılan karşılaştırma sayısı.
- Uzunluklar eşitse ve `sabit is True`: bütün baytları gez (`adim = len(a)`), farkları XOR ile biriktir; `esit` = biriken değer 0 mı?
- Dönüş: `{'esit': bool, 'adim': int}`.

Test, gizli bir değerin farklı konumlarda farklılaştığı girdilerde erken çıkışlı sürümün adım sayısının farkın konumunu ele verdiğini, sabit adımlı sürümün ise hep aynı adımı attığını sınar.

KUSURLU başlangıç `sabit = True` olduğunda da ilk farkta duruyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def karsilastir(a, b, sabit):
    if len(a) != len(b):
        return {'esit': False, 'adim': 0}
    adim = 0
    for x, y in zip(a, b):
        adim += 1
        if x != y:
            return {'esit': False, 'adim': adim}
    return {'esit': True, 'adim': adim}
```

```solution
def karsilastir(a, b, sabit):
    if type(a) is not bytes or type(b) is not bytes or type(sabit) is not bool:
        raise ValueError('a ve b bytes, sabit bool olmali')
    if len(a) != len(b):
        return {'esit': False, 'adim': 0}
    if sabit:
        fark = 0
        for x, y in zip(a, b):
            fark |= x ^ y
        return {'esit': fark == 0, 'adim': len(a)}
    adim = 0
    for x, y in zip(a, b):
        adim += 1
        if x != y:
            return {'esit': False, 'adim': adim}
    return {'esit': True, 'adim': adim}
```

```test
need('karsilastir')
_gizli = bytes(range(16))
_erken, _sabit = [], []
for _konum in range(16):
    _tahmin = bytearray(_gizli)
    _tahmin[_konum] ^= 0xFF
    _tahmin = bytes(_tahmin)
    _erken.append(karsilastir(_gizli, _tahmin, False))
    _sabit.append(karsilastir(_gizli, _tahmin, True))
eq([r['adim'] for r in _erken], list(range(1, 17)), 'erken çıkış: adım sayısı farkın konumunu sızdırır')
eq({r['adim'] for r in _sabit}, {16}, 'sabit adım: her girdide 16 adım')
eq({r['esit'] for r in _erken + _sabit}, {False}, 'iki sürüm de farkı bulur')
eq(karsilastir(_gizli, _gizli, False), {'esit': True, 'adim': 16}, 'eşit girdide erken çıkış da 16 adım')
eq(karsilastir(_gizli, _gizli, True), {'esit': True, 'adim': 16}, 'eşit girdi sabit adımla')
eq(karsilastir(b'\x01\x02', b'\x02\x01', True), {'esit': False, 'adim': 2}, 'XOR birikimi: farklar birbirini silmez')
eq(karsilastir(b'\x03', b'\x00', True), {'esit': False, 'adim': 1}, 'tek bayt fark')
eq(karsilastir(b'abc', b'ab', True), {'esit': False, 'adim': 0}, 'farklı uzunluk')
eq(karsilastir(b'', b'', True), {'esit': True, 'adim': 0}, 'boş girdiler eşit')
eq(karsilastir(b'', b'', False), {'esit': True, 'adim': 0}, 'boş girdiler erken çıkışta da eşit')
for _arg in (('ab', b'ab', True), (b'ab', bytearray(b'ab'), True), (b'ab', b'ab', 1), (b'ab', b'ab', None), (None, b'', False)):
    raises(ValueError, karsilastir, *_arg, msg=f'bozuk girdi ValueError: {_arg!r}')
```

```hint
Sabit adımlı sürümde döngüden hiç erken çıkma; her bayt çiftinin `x ^ y` değerini `|=` ile biriktir ve sonucu döngüden sonra sına.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Olay (25 sn).** "KyberSlash'ta ML-KEM'in matematiği kırılmadı. Bazı uygulamalar gizli değere bağlı bir bölme yapıyordu ve süresi değişiyordu. Makaleye göre gömülü işlemcilerde anahtar dakikalar ya da saatler içinde kurtarıldı."
2. **Ölçüm (30 sn).** "Sızıntı ararken iki grubun ortalamasını değil, farkı standart hatayla ölçekleyen Welch t'yi kullandık. Aynı 2 birimlik fark az gürültüde t = 4,9, çok gürültüde 0,37 çıktı."
3. **t'nin sınırı (20 sn).** "Büyük t bir alarmdır: fark var der, nedenini ve sömürülebilirliğini söylemez. Önbellek ve frekans da fark üretir."
4. **Önleme (30 sn).** "Erken çıkışlı karşılaştırmanın adım sayısı farkın konumuyla birlikte 1'den 16'ya yükseldi. Bütün baytları dolaşıp farkları XOR ile biriktiren sürüm her girdide 16 adım attı."
5. **Sınır (15 sn).** "Adım sayısı bir model; Python'da gerçek sabit zamanlılık iddia etmiyoruz, derlenmiş kod platformda denetlenir."
:::

::: anlat Sınır ve kaynak
Bu derste zamanlamalar sentetiktir ve adım sayısı işlem süresinin bir modelidir. Gerçek sabit zamanlılık derleyiciye, işlemciye ve mikro mimariye bağlıdır. Python düzeyinde koşulsuz görünen bir kod bile yorumlayıcıda değişken süreli olabilir; bu yüzden ders gerçek bir sabit zamanlılık iddiası taşımaz. Welch t'nin eşik değeri ve çoklu karşılaştırma düzeltmesi bu derste işlenmez; gerçek bir sızıntı testinde (ör. ölçüm protokolleriyle) bu kararlar önceden belirlenir. KyberSlash'ın ayrıntıları ve etkilenen uygulamalar makalededir.

- Birincil kaynak: [Bernstein, Bhargavan, Bhasin ve diğerleri — KyberSlash: Exploiting secret-dependent division timings in Kyber implementations (IACR ePrint 2024/1049, TCHES 2025)](https://eprint.iacr.org/2024/1049). Doğrulama tarihi: 11 Kasım 2026.
:::

::: dusun
Bir ekip "kodumuzda gizli değere bağlı dallanma yok, öyleyse sabit zamanlı" diyor. KyberSlash'taki sızıntı bir dallanmadan değil, bir işlemin (bölme) donanımdaki değişken süresinden geliyordu. Bu ekibin kod incelemesine hangi kontrolü eklemesi gerekir?
:::

::: ozet
- KyberSlash'ta algoritma değil, gizli değere bağlı bölme süresi olan uygulamalar kırıldı.
- Welch t ortalama farkını standart hatayla ölçekler; varyans `n − 1` paydalıdır.
- Büyük |t| bir fark alarmıdır; nedenini ve sömürülebilirliği kanıtlamaz.
- Erken çıkışlı karşılaştırma farkın konumunu sızdırır; sabit adımlı karşılaştırma yalnız uzunluğa bağlıdır.
:::
