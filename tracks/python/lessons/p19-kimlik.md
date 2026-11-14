---
id: p19
title: Kimlik ve Değiştirilebilirlik
summary: is ile == farkı, değiştirilebilir/değiştirilemez türler, hash'lenebilirlik ve += tuzağı.
kazanim: PCAP 4.5, PCPP1 1.10
---

::: anlat Eşit mi, aynı mı?
Her nesnenin üç özelliği vardır: **kimlik** (`id()`), **tür** (`type()`) ve **değer**. İki ayrı soru sorabilirsin:

- `a == b`: **değerleri** eşit mi?
- `a is b`: **aynı nesne** mi? (yani `id(a) == id(b)`)

```python
a = [1, 2, 3]
b = [1, 2, 3]
c = a
print(a == b, a is b, a is not b)    #! True False True — eşit ama ayrı nesneler
print(a == c, a is c)                #! True True — c bir takma ad
print(id(a) == id(c))
```

İkiz kardeşler gibi düşün: `==` "aynı görünüyorlar mı?", `is` ise "aynı kişi mi?" diye sorar.

**`is`'i ne zaman kullanırsın?** Neredeyse sadece tekil nesnelerde: `x is None`, `x is True`. Değer karşılaştırması için **`==` kullan**.

### Değiştirilebilir ve değiştirilemez türler

| Değiştirilemez (immutable) | Değiştirilebilir (mutable) |
|---|---|
| `int`, `float`, `bool`, `str` | `list` |
| `tuple`, `frozenset` | `dict`, `set` |
| `bytes`, `None` | `bytearray`, kendi sınıfların (çoğu) |

Değiştirilemez nesnede "değişiklik" gibi görünen her şey aslında **yeni bir nesne** üretip ismi ona taşır:

```python
s = "ab"
eski = s                 #! eski nesneye başvuru kalsın
print(id(s))
s += "c"                #! yeni metin nesnesi; s artık onu gösteriyor
print(id(s))            #! farklı id
l = [1]
print(id(l))
l += [2]                #! liste yerinde genişler
print(id(l))            #! aynı id!
```

> [!TUZAK]
> `+=` listelerde **yerinde** değişiklik yapar (`extend` gibi), metinlerde ve demetlerde ise yeni nesne üretir. Yani `b = a; a += [3]` sonrası `b` de değişir, ama `b = s; s += "x"` sonrası `b` değişmez.
:::

::: tahmin
İki satır:

```python
a = [1, 2]
b = [1, 2]
print(a == b, a is b)
c = a
c += [3]
print(a)
```

???

`True False`, sonra `[1, 2, 3]`. `c` takma addır ve `+=` listeyi **yerinde** genişletir, bu yüzden değişiklik `a`'dan da görünür.
:::

::: anlat Hash'lenebilirlik ve önbellek sırları
Bir nesnenin sözlük anahtarı ya da küme elemanı olabilmesi için **hash'lenebilir** olması gerekir: ömrü boyunca hash değeri değişmemelidir. Değiştirilebilir koleksiyonlar bu yüzden hash'lenemez:

```python
print(hash("admin"), hash(42), hash((1, 2)))
konumlar = {(0, 0): "başlangıç", (2, 3): "hedef"}   #! demet anahtar: olur
print(konumlar[(2, 3)])
```

```python norun
d = {[1, 2]: "x"}         #! TypeError: unhashable type: 'list'
t = (1, [2, 3])
hash(t)                   #! TypeError: bu demet, liste içerdiği için hash'lenemez!
```

İçinde liste olan bir demet **yine de değiştirilebilir bir parça taşır**: demetin kendisi aynı nesneleri gösterir ama gösterdiği liste değişebilir.

> [!NOT]
> `hash("admin")` süreçler arasında değişebilir; aynı süreçte sabittir. Python, metinlerin (`str`) ve baytların (`bytes`) hash'ine her süreçte rastgele bir tohum katar: **hash rastgeleleştirme**. Amaç, aynı yere düşecek anahtarlar seçilerek bir sözlüğün kasıtlı olarak yavaşlatılmasını önlemektir. Bu yüzden metin kümelerinin yineleme sırası çalıştırmadan çalıştırmaya değişebilir (P17). Tekrarlanabilir çıktı gerektiğinde elemanları `sorted` ile sırala; hash tohumunu sabitlemek küme sırasını bir dil garantisine dönüştürmez. Tam sayıların hash'i rastgele değildir: `hash(42)` her zaman `42`'dir.

> [!DERİN]
> CPython iki önbellek hilesi yapar ve bunlar `is` ile şaşırtıcı sonuçlar doğurur:
> 1. **Küçük tam sayı önbelleği**: -5 ile 256 arasındaki her int tek bir nesnedir. `a = 256; b = 256; a is b` → True. `a = 257; b = 257` ise ayrı satırlarda yazılırsa False olabilir.
> 2. **Metin stajyerliği (interning)**: tanımlayıcıya benzeyen kısa metinler (`"admin"`) tek kopya tutulur.
>
> Bunlar dilin değil **uygulamanın** (CPython) detaylarıdır, başka bir Python'da farklı olabilir. Çıkarılacak ders: **değer karşılaştırması için asla `is` kullanma.** Röntgen'de küçük sayıları gösteren isimlerin neden aynı renkte olduğunu artık biliyorsun.
:::

::: tahmin
İki satır:

```python
t = (1, [2, 3])
t[1].append(4)
print(t)
s = "ab"
s2 = s
s += "c"
print(s, s2)
```

???

`(1, [2, 3, 4])`, sonra `abc ab`. Demet değiştirilemez ama içindeki **liste** değiştirilebilir; demet hâlâ aynı listeyi gösteriyor. Metinde ise `+=` yeni nesne üretir; `s2` eski `"ab"`'yi göstermeye devam eder.
:::

::: gorev Eşit ama ayrı
`a` hazır. İki isim daha tanımla:

- `b`: `a` ile **eşit** ama **ayrı bir nesne**
- `c`: `a`'nın **kendisi** (takma ad)

Sonra `print(a == b, a is b, a is c)` yazdır.

```cikti
True False True
```

```starter
a = [10, 20, 30]
b = a
c = a.copy()
print(a == b, a is b, a is c)
```

```test
eq(a, [10, 20, 30], "verilen a listesi korunmalı")
ok(b == a, "b, a'ya eşit olmalı")
ok(b is not a, "b, a ile aynı nesne olmamalı")
ok(c is a, "c, a'nın kendisi olmalı")
eq(out.strip(), "True False True", "Çıktı: True False True")
```

```solution
a = [10, 20, 30]
b = a.copy()
c = a
print(a == b, a is b, a is c)
```

```hint
Kopya için `.copy()` ya da `list(a)`; takma ad için düz atama.
```
:::

::: gorev Değişmez yapılandırma
İzinli portlar program çalışırken yanlışlıkla değişmemeli. Verilen listeden iki şey üret:

- `IZINLI`: bir **tuple** (sıralı, değiştirilemez)
- `IZINLI_KUME`: bir **frozenset** (hızlı üyelik, değiştirilemez)

Sonra girdiden bir port oku ve `IZINLI_KUME` içindeyse `izin`, değilse `ret` yazdır.

```starter
portlar = [22, 80, 443]
port = int(input())
IZINLI = portlar
IZINLI_KUME = set(portlar)
print("izin" if port in IZINLI_KUME else "ret")
```

```stdin
443
```

```test
ok(type(IZINLI) is tuple, "IZINLI bir tuple olmalı", got=type(IZINLI).__name__)
eq(IZINLI_KUME, frozenset([22, 80, 443]), "küme tüm izinli portları içermeli")
eq(IZINLI, (22, 80, 443), "IZINLI = (22, 80, 443)")
ok(type(IZINLI_KUME) is frozenset, "IZINLI_KUME bir frozenset olmalı", got=type(IZINLI_KUME).__name__)
eq(run("443").strip(), "izin", "443 → izin")
eq(run("3389").strip(), "ret", "3389 → ret")
```

```solution
portlar = [22, 80, 443]
port = int(input())
IZINLI = tuple(portlar)
IZINLI_KUME = frozenset(portlar)
print("izin" if port in IZINLI_KUME else "ret")
```

```hint
`tuple(liste)` ve `frozenset(liste)` dönüşümleri.
```
:::

::: gorev Ziyaret edilen hücreler
Bir robot `(0, 0)`'dan başlıyor. Girdide `U` (yukarı, `y+1`), `D` (aşağı, `y-1`), `R` (sağ, `x+1`) ve `L` (sol, `x-1`) harflerinden oluşan bir hareket dizisi var. Konumları `(x, y)` **demetleri** olarak `ziyaret` kümesinde tut ve başlangıç dahil **kaç farklı hücre** ziyaret edildiğini yazdır.

`URDL` → (0,0) (0,1) (1,1) (1,0) (0,0) → **4** farklı hücre

```starter
hareketler = input()
x, y = 0, 0
ziyaret = set()
for h in hareketler:
    if h == "U": y += 1
    elif h == "D": y -= 1
    elif h == "R": x += 1
    elif h == "L": x -= 1
    ziyaret.add((x, y))
print(len(ziyaret))
```

```stdin
URDL
```

```test
eq(ziyaret, {(0, 0), (0, 1), (1, 1), (1, 0)}, "URDL sonunda ziyaret kümesi (0, 0)'dan başlayan 4 demet hücreyi tutmalı")
eq(run("LLRR").strip(), "3", "sola ilerle ve başlangıca dön")
eq(run("URRDLU").strip(), "6", "asimetrik yol")
eq(run("URDL").strip(), "4", "URDL → 4")
eq(run("\n").strip(), "1", "hareket yok → 1 (başlangıç)")
eq(run("RRRR").strip(), "5", "RRRR → 5")
eq(run("UDUDUD").strip(), "2", "UDUDUD → 2")
```

```solution
hareketler = input()
x, y = 0, 0
ziyaret = {(x, y)}
for h in hareketler:
    if h == "U":
        y += 1
    elif h == "D":
        y -= 1
    elif h == "R":
        x += 1
    elif h == "L":
        x -= 1
    ziyaret.add((x, y))
print(len(ziyaret))
```

```hint
Başlangıçta `ziyaret = {(0, 0)}`. Her hareketten sonra `ziyaret.add((x, y))`. Liste `[x, y]` kümeye konamaz, demet konur.
```
:::


::: anlat Yaygın yanlışlar
| Yanlış yaklaşım | Neden kırılır? | Doğrusu |
|---|---|---|
| Kopya için `b = a` yazmak | İki isim aynı nesneyi gösterir. | Yeni liste için `a.copy()` kullan. |
| İçinde liste bulunan demeti küme elemanı yapmak | Bu demet hash'lenemez. | Koordinat gibi hash'lenebilir elemanlardan demet kur. |
| Değerleri `is` ile karşılaştırmak | Nesne önbellekleri sonucu yanıltabilir. | Değer için `==`, tekil `None` için `is None` kullan. |
:::

::: anlat AI derslerinde nerede?
- `ai-savunma-19` testleri `copy.deepcopy(P)` ile politika girdisinin bağımsız kopyasını alır; iç içe verilerde takma ad ile kopya farkı önemlidir.
- `ai-uretim-09` testlerindeki `copy.deepcopy`, eğitim deneyi girdilerini birbirinden ayırır; bir denemenin değişikliği diğerine sızmamalıdır.
:::
