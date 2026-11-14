---
id: p24
title: Özyineleme
summary: Kendini çağıran fonksiyon; temel durum, çağrı yığını, iç içe yapılar ve hafızalama.
kazanim: PCEP 4.1
---

::: anlat Kendini çağıran fonksiyon
**Özyineleme** (recursion), bir fonksiyonun problemi **daha küçük bir kopyasına** indirgeyip kendini çağırmasıdır. Sonlanması beklenen bu özyinelemeli örneklerin iki parçası vardır:

1. **Temel durum** (base case): cevabın doğrudan bilindiği en küçük hal, yani durma noktası
2. **Özyinelemeli durum**: problemi küçültüp kendini çağırma

Bu faktöriyel örneğinin girdisi negatif olmayan tam sayıdır.

```python
def faktoriyel(n):
    if n <= 1:                     #! temel durum: 1! = 1
        return 1
    return n * faktoriyel(n - 1)   #! n! = n × (n-1)!

print(faktoriyel(5))               #! 5 × 4 × 3 × 2 × 1 = 120
```

Bunu **Röntgen'de mutlaka izle**: `faktoriyel(5)` çağrısı `faktoriyel(4)`'ü, o da `faktoriyel(3)`'ü çağırır... Çerçeveler üst üste yığılır. Bu yapıya **çağrı yığını** (call stack) denir. En tepedeki `faktoriyel(1)` 1 döndürünce yığın geriye doğru çözülür ve her çerçeve kendi çarpımını yapıp döner.

### Temel durum unutulursa
```python norun
def sonsuz(n):
    return sonsuz(n - 1)     # hiç durmaz
sonsuz(5)                    # RecursionError: maximum recursion depth exceeded
```

Python yığının sonsuza büyüyüp belleği tüketmesini önlemek için varsayılan olarak ~1000 derinlikte durur (`sys.getrecursionlimit()`).

> [!DERİN]
> Bazı diller (Scheme, Haskell) "kuyruk çağrısı optimizasyonu" yapar: son işlem kendini çağırmaksa yeni çerçeve açmaz. Python bunu **bilinçli olarak yapmaz**. Guido'nun gerekçesi: traceback'ler bozulur ve hata ayıklama zorlaşır. Sonuç olarak Python'da derin özyineleme yerine döngü tercih edilir. Özyinelemeyi **doğası gereği ağaç biçimli** problemlere sakla: iç içe klasörler, JSON, sözdizimi ağaçları (P73'da kendi yorumlayıcını yazarken).
:::

::: tahmin
Çıktıyı satır satır yaz:

```python
def geri(n):
    if n == 0:
        print("son")
        return
    print(n)
    geri(n - 1)
    print("dönüş", n)

geri(2)
```

???

```cikti
2
1
son
dönüş 1
dönüş 2
```

Özyinelemeli çağrıdan **önceki** satırlar iniş sırasında (2, 1), **sonraki** satırlar ise yığın çözülürken ters sırayla (1, 2) çalışır. Bu "iniş-çıkış" sezgisi özyinelemeyi anlamanın anahtarıdır.
:::

::: anlat İç içe yapılar ve hafızalama
Özyinelemenin parladığı yer, **derinliği bilinmeyen iç içe yapılardır**:

```python
def toplam(veri):
    """İç içe listelerdeki tüm sayıları toplar."""
    sonuc = 0
    for oge in veri:
        if isinstance(oge, list):   #! liste ise: aynı problemin küçüğü
            sonuc += toplam(oge)
        else:
            sonuc += oge
    return sonuc

print(toplam([1, [2, 3], [[4], 5], []]))
```

`isinstance(x, list)` bir değerin türünü sorar. Döngüyle bu problemi çözmek için kendi yığınını yönetmen gerekirdi.

### Saf Fibonacci'nin üstel patlaması
```python
def fib(n):
    return n if n < 2 else fib(n - 1) + fib(n - 2)
print([fib(i) for i in range(10)])
```

Güzel ama korkunç yavaş: `fib(5)`, `fib(3)`'ü iki kez, `fib(2)`'yi üç kez hesaplar. `fib(40)` yüz milyonlarca çağrı eder. Çözüm **hafızalama** (memoization): bir kez hesaplananı sakla.

```python
hafiza = {}
def fib(n):
    if n in hafiza:
        return hafiza[n]
    sonuc = n if n < 2 else fib(n - 1) + fib(n - 2)
    hafiza[n] = sonuc
    return sonuc
print(fib(90))
```

Python'da bunun hazır bir dekoratörü var: `@functools.lru_cache`. Dekoratörleri P46'te kendin yazacaksın.
:::

::: tahmin
Ne yazdırır?

```python
def f(n):
    return 1 if n <= 1 else f(n - 1) + f(n - 2)

print([f(i) for i in range(7)])
```

???

`[1, 1, 2, 3, 5, 8, 13]`. f(0) ve f(1) temel durumdur ve 1 döndürür; sonrası Fibonacci kuralıdır.
:::

::: gorev Özyinelemeli üs
`us(taban, ust)` fonksiyonunu **özyinelemeyle** yaz: `taban ** ust` değerini döndürsün (ust ≥ 0 tam sayı; bu doğrudan özyinelemeli çözümde üs çağrı derinliği sınırının altında olmalıdır). `**` ve `pow` kullanmak yok.

```starter
def us(taban, ust):
    if ust == 0:
        return 0
    return taban * us(taban, ust - 1)
```

```test
import ast
need("us")
eq(us(0, 0), 1, "Python gibi sıfırın sıfırıncı kuvveti")
eq(us(-2, 3), -8, "negatif taban tek üs")
eq(us(-2, 4), 16, "negatif taban çift üs")
eq(us(2, 10), 1024, "us(2, 10) → 1024")
eq(us(5, 0), 1, "us(5, 0) → 1")
eq(us(3, 1), 3, "us(3, 1) → 3")
eq(us(10, 5), 100000, "us(10, 5) → 100000")
fn = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "us"), None)
ok(fn is not None and any(isinstance(c, ast.Call) and getattr(c.func, "id", None) == "us" for c in ast.walk(fn)), "us kendini çağırmalı")
ok("**" not in src and not calls("pow"), "** ve pow kullanmadan")
```

```solution
def us(taban, ust):
    if ust == 0:
        return 1
    return taban * us(taban, ust - 1)
```

```hint
Temel durum: `ust == 0` → 1. Özyineleme: `taban * us(taban, ust - 1)`.
```

```hint
Bonus: `ust` çiftse `yarim = us(taban, ust // 2); return yarim * yarim` ile çağrı sayısı logaritmik olur. Kriptografideki "hızlı üs alma" budur.
```
:::

::: gorev Düzleştir
`duzlestir(veri)` fonksiyonu, Python'un recursion sınırları içinde kalan, döngüsel başvuru içermeyen iç içe listeleri tek düz listeye çevirsin. Sıra korunmalı.

```starter
def duzlestir(veri):
    sonuc = []
    for oge in veri:
        if isinstance(oge, list):
            sonuc.append(duzlestir(oge))
        else:
            sonuc.append(oge)
    return sonuc
```

```test
need("duzlestir")
eq(duzlestir([1, [2, 3], [[4], 5], []]), [1, 2, 3, 4, 5], "[1, [2, 3], [[4], 5], []] → [1, 2, 3, 4, 5]")
eq(duzlestir([]), [], "[] → []")
eq(duzlestir([[[[["derin"]]]]]), ["derin"], "çok derin iç içe")
eq(duzlestir(["a", ["b", ["c", "d"]], "e"]), ["a", "b", "c", "d", "e"], "metinler")
_fn2 = next((n for n in __import__("ast").walk(tree) if isinstance(n, __import__("ast").FunctionDef) and n.name == "duzlestir"), None)
ok(_fn2 is not None and any(isinstance(c, __import__("ast").Call) and getattr(c.func, "id", None) == "duzlestir" for c in __import__("ast").walk(_fn2)), "duzlestir kendini çağırmalı")
```

```solution
def duzlestir(veri):
    sonuc = []
    for oge in veri:
        if isinstance(oge, list):
            sonuc.extend(duzlestir(oge))
        else:
            sonuc.append(oge)
    return sonuc
```

```hint
Her öğe için: liste ise `sonuc.extend(duzlestir(oge))`, değilse `sonuc.append(oge)`.
```
:::

::: gorev Klasör boyutu
Sentetik bir dosya ağacı, döngüsel başvuru içermeyen ve recursion sınırını aşmayan iç içe sözlüklerle temsil ediliyor: değer **sayıysa** dosya boyutu (bayt), **sözlükse** alt klasör. `boyut(agac)` toplam boyutu döndürsün.

```starter
def boyut(agac):
    toplam = 0
    for deger in agac.values():
        if not isinstance(deger, dict):
            toplam += deger
    return toplam
```

```test
need("boyut")
agac = {"a.txt": 100, "loglar": {"auth.log": 2000, "eski": {"x.gz": 500}}, "b.bin": 50, "bos": {}}
eq(boyut(agac), 2650, "örnek ağaç → 2650")
eq(boyut({}), 0, "boş klasör → 0")
eq(boyut({"tek": 7}), 7, "tek dosya → 7")
_fn3 = next((n for n in __import__("ast").walk(tree) if isinstance(n, __import__("ast").FunctionDef) and n.name == "boyut"), None)
ok(_fn3 is not None and any(isinstance(c, __import__("ast").Call) and getattr(c.func, "id", None) == "boyut" for c in __import__("ast").walk(_fn3)), "boyut kendini çağırmalı")
```

```solution
def boyut(agac):
    toplam = 0
    for deger in agac.values():
        if isinstance(deger, dict):
            toplam += boyut(deger)
        else:
            toplam += deger
    return toplam
```

```hint
`for deger in agac.values():` sözlükse `boyut(deger)` ile özyinele.
```
:::

::: gorev Hızlı Fibonacci
`fib(n)` fonksiyonunu negatif olmayan tam sayı n için yaz (`fib(0) = 0`, `fib(1) = 1`). Recursion kullanan çözüm yine Python çağrı derinliği sınırına tabidir; büyük n için döngü tercih edilebilir. `fib(200)` gibi büyük değerlerde gereksiz tekrar hesap yapmadan cevap vermeli. Saf özyineleme süre sınırını aşar; hafızalama ya da döngü kullan.

```starter
def fib(n):
    a, b = 0, 1
    for _ in range(1, n):
        a, b = b, a + b
    return a
```

```meta
timeout: 8
```

```test
need("fib")
eq(fib(0), 0, "fib(0) → 0")
eq(fib(1), 1, "fib(1) → 1")
eq(fib(10), 55, "fib(10) → 55")
eq(fib(200), 280571172992510140037611932413038677189525, "fib(200) anında hesaplanmalı")
```

```solution
hafiza = {0: 0, 1: 1}

def fib(n):
    if n not in hafiza:
        hafiza[n] = fib(n - 1) + fib(n - 2)
    return hafiza[n]
```

```hint
Bir sözlükte hesaplananları sakla: `if n not in hafiza: hafiza[n] = ...`
```
:::


::: anlat Yaygın yanlışlar
| Yanlış yaklaşım | Neden kırılır? | Doğrusu |
|---|---|---|
| Temel durumu unutmak | Çağrılar sonlanmaz, RecursionError oluşur. | Her yolda daha küçük probleme ve temel duruma yaklaş. |
| Düzleştirirken `append` ile alt liste eklemek | Sonuç iç içe kalır. | Özyineleme sonucunu `extend` ile yay. |
| Fibonacci alt sonuçlarını saklamamak | Aynı alt problem tekrar tekrar hesaplanır. | Memoization veya döngü kullan. |
:::

::: anlat AI derslerinde nerede?
- `ai-savunma-19` politikasındaki iç içe sözlükler, bu dersteki sentetik ağaç gibi katmanlı veridir. O ders sabit şema alanlarını doğrudan kontrol eder; recursion burada değişken derinlik için kullanılan ayrı bir yöntemdir.
- `ai-uretim-09` çözümünde hesaplanan `ax` listesi tekrar kullanılır. Bu, recursion olmadan da ara sonucu saklayıp tekrar hesaplamayı azaltma fikrinin bir örneğidir.
:::
