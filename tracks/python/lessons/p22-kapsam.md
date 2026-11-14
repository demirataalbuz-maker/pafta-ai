---
id: p22
title: Kapsam · LEGB
summary: İsimler nerede aranır; yerel, kapsayan, global, yerleşik; global, nonlocal ve gölgeleme.
kazanim: PCEP 4.2, PCAP 5.3
---

::: anlat Her fonksiyonun kendi isim alanı
Bir fonksiyonun içinde atanan isimler **yereldir**: normalde o fonksiyonun kapsamından erişilir. Bir closure bu bağları fonksiyon döndükten sonra da yaşatabilir; bunu aşağıda göreceğiz. Aynı adlı global bir değişkeni etkilemezler:

```python
x = "global"

def f():
    x = "yerel"            #! fonksiyon içinde atama → yeni YEREL isim
    print("içeride:", x)

f()
print("dışarıda:", x)      #! global x değişmedi
```

Röntgen'de çerçeveleri izle: `f()` çağrılınca yeni bir çerçeve açılır ve kendi `x`'i orada yaşar. Global çerçevedeki `x` ona dokunulmadan durur.

### LEGB: isim arama sırası
Python bir ismi okurken dört katmana **sırayla** bakar ve ilk bulduğunu kullanır:

1. **L**ocal: şu anki fonksiyonun içi
2. **E**nclosing: dıştaki (kapsayan) fonksiyonların içi
3. **G**lobal: modülün en üst düzeyi
4. **B**uilt-in: `print`, `len`, `list` gibi yerleşikler

Hiçbirinde yoksa `NameError` alırsın. Ancak derleyici ismi yerel kabul etmişse, henüz değer bağlanmamış yerel isim için dış kapsamlar aranmaz: `UnboundLocalError` oluşur.

```python
oran = 0.18                     #! global

def fiyat(net):
    return net * (1 + oran)     #! oran yerelde yok → global'de bulunur

print(fiyat(100))
```

Global bir değeri **okumak** serbesttir. Sorun **atamada** başlar.
:::

::: tahmin
İki satır:

```python
x = "global"
def f():
    x = "yerel"
    print(x)
f()
print(x)
```

???

`yerel`, sonra `global`. Fonksiyon içindeki atama yeni bir yerel isim yaratır; global `x`'e dokunmaz.
:::

::: anlat UnboundLocalError, global ve nonlocal
Python bir ismin yerel mi olduğuna **fonksiyonu derlerken** karar verir: gövdenin **herhangi bir yerinde** o isme atama varsa isim o fonksiyonda baştan sona yereldir. Bu yüzden şu kod patlar:

```python norun
sayac = 0
def artir():
    sayac += 1     # atama var → sayac yerel → ama henüz değeri yok!
artir()            # UnboundLocalError
```

Global'i değiştirmek istediğini açıkça söylemelisin:

```python
sayac = 0
def artir():
    global sayac               #! "bu isim global olanı göstersin"
    sayac += 1

artir(); artir()
print(sayac)
```

İç içe fonksiyonlarda kapsayan fonksiyonun değişkenini değiştirmek için **`nonlocal`** kullanılır:

```python
def sayac_olustur():
    n = 0
    def say():
        nonlocal n             #! dıştaki fonksiyonun n'i
        n += 1
        return n
    return say                 #! fonksiyon döndür (P23'te derinleşecek)

s = sayac_olustur()
print(s(), s(), s())
```

`say` fonksiyonu, `sayac_olustur` bittikten **sonra** bile `n`'i hatırlar. Buna **closure** denir ve P46'te dekoratörlerin temeli olacak.

> [!NOT]
> `global` kullanmak çoğu zaman tasarım kokusudur: fonksiyonun ne yaptığını sadece imzasından anlayamazsın. Değeri parametre olarak al ve sonucu `return` et. `global` yalnızca gerçekten modül düzeyinde bir durum (yapılandırma, sayaç) tutman gerektiğinde makuldür.

> [!TUZAK]
> **Yerleşikleri gölgeleme**: `list = ["web01"]`, `max = 5`, `id = "abc"` gibi atamalar yerleşik fonksiyonu o kapsamda **gizler**. Sonra `list("abc")` yazınca `TypeError: 'list' object is not callable` alırsın. Değişkenlerine yerleşik isimleri verme.
:::

::: tahmin
Bu düzeltilmiş kod ne yazdırır?

```python
sayac = 0
def artir():
    global sayac
    sayac += 1
artir()
print(sayac)
```

???

`1`. `global sayac`, atamanın modül kapsamındaki sayaca yapılmasını sağlar. Bildirim kaldırılırsa yukarıdaki hata örneğindeki gibi `UnboundLocalError` oluşur.
:::

::: tahmin
Ne yazdırır?

```python
def dis():
    n = 0
    def ic():
        nonlocal n
        n += 1
        return n
    ic()
    ic()
    return ic()

print(dis())
```

???

`3`. `ic` her çağrıda kapsayan fonksiyonun aynı `n`'ini artırır: 1, 2, 3. Son çağrının sonucu döndürülür.
:::

::: gorev İstek sayacı
`istek_al()` her çağrıldığında global `istek_sayisi`'ni bir artırıp yeni değeri döndürmeli. Şu an `UnboundLocalError` veriyor; düzelt.

```starter
istek_sayisi = 0

def istek_al():
    istek_sayisi += 1
    return istek_sayisi
```

```test
need("istek_al")
eq(istek_al(), 1, "ilk çağrı → 1")
eq(istek_al(), 2, "ikinci çağrı → 2")
eq(istek_al(), 3, "üçüncü çağrı → 3")
ok(uses("global"), "global anahtar kelimesini kullan")
```

```solution
istek_sayisi = 0

def istek_al():
    global istek_sayisi
    istek_sayisi += 1
    return istek_sayisi
```

```hint
Fonksiyonun ilk satırı: `global istek_sayisi`
```
:::

::: gorev Bağımsız sayaçlar
`sayac_olustur()` her çağrıldığında **yeni ve bağımsız** bir sayaç fonksiyonu döndürsün. Döndürülen fonksiyon her çağrıda kendi sayısını bir artırıp döndürsün. Global değişken kullanma; `nonlocal` kullan.

```starter
def sayac_olustur():
    n = 0
    def say():
        n = 0
        n += 1
        return n
    return say
```

```test
need("sayac_olustur")
a = sayac_olustur()
b = sayac_olustur()
ok(callable(a), "sayac_olustur() bir fonksiyon döndürmeli", got=a)
eq(a(), 1, "a() → 1")
eq(a(), 2, "a() → 2")
eq(b(), 1, "b() bağımsız → 1")
eq(a(), 3, "a() → 3")
ok(uses("nonlocal") and not uses("global"), "global değil, nonlocal kullan")
```

```solution
def sayac_olustur():
    n = 0
    def say():
        nonlocal n
        n += 1
        return n
    return say
```

```hint
Dış fonksiyonda `n = 0`, içte `nonlocal n; n += 1; return n`, dış fonksiyon iç fonksiyonu (parantezsiz!) döndürür.
```
:::

::: gorev Gölgelenen yerleşik
Birisi host listesine `list` adını vermiş ve şimdi `kopyala` fonksiyonu patlıyor. Listeyi `hostlar` olarak yeniden adlandır, böylece `list` yerleşiği tekrar çalışsın.

```starter
list = ["web01", "db01"]

def kopyala(x):
    return list(x)

print(kopyala("abc"))
print(list)
```

```test
need("kopyala")
eq(out.strip().splitlines(), ["['a', 'b', 'c']", "['web01', 'db01']"], "örnek çıktılar")
veri = [1, 2]
kopya = kopyala(veri)
ok(kopya is not veri and kopya == veri, "yeni liste kopyası")
eq(kopyala("abc"), ["a", "b", "c"], "kopyala('abc') → ['a', 'b', 'c']")
eq(kullanici.get("hostlar"), ["web01", "db01"], "hostlar = ['web01', 'db01']")
ok("list" not in kullanici, "global 'list' ismi artık tanımlanmamalı")
```

```solution
hostlar = ["web01", "db01"]

def kopyala(x):
    return list(x)

print(kopyala("abc"))
print(hostlar)
```

```hint
İlk satırdaki ismi ve son `print`'tekini değiştir; fonksiyondaki `list(x)` yerleşiği kastediyor.
```
:::


::: anlat Yaygın yanlışlar
| Yanlış yaklaşım | Neden kırılır? | Doğrusu |
|---|---|---|
| Atamadan önce yerel ismi okumak | Derleyici tüm gövdede onu yerel sayar. | Parametre kullan veya amaçlanan kapsamı `global`/`nonlocal` ile belirt. |
| Her sayaç çağrısında n değerini sıfırlamak | Sayaç önceki çağrıyı hatırlamaz. | n dış fonksiyonda oluşturulur; içeride `nonlocal` kullan. |
| `list` adını değişken yapmak | Yerleşik list dönüşümünü gölgeler. | `hostlar` gibi açıklayıcı bir ad seç. |
:::

::: anlat AI derslerinde nerede?
- `ai-uretim-09` çözümündeki `lora_ileri` fonksiyonunun `d_in`, `d_out` ve `sc` adları o çağrının yerel hesaplarıdır.
- `ai-savunma-19` testlerinin yardımcı fonksiyonlarındaki yerel politika kopyaları, aynı adın başka fonksiyonlardaki bağlarından ayrıdır.
:::
