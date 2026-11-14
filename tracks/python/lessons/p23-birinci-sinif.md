---
id: p23
title: Fonksiyon da Bir Nesnedir
summary: Fonksiyonu değişkene atamak, argüman vermek, döndürmek; lambda, sorted key, map ve filter.
kazanim: PCAP 5.2
---

::: anlat Birinci sınıf vatandaş
Python'da fonksiyonlar **sıradan nesnelerdir**: bir isme atanabilir, listeye konabilir, başka bir fonksiyona argüman olarak verilebilir, bir fonksiyondan döndürülebilir. Buna "fonksiyonlar birinci sınıf nesnedir" denir.

```python
def bagir(s):
    return s.upper() + "!"

f = bagir                        #! parantez YOK: çağırmıyoruz, nesneyi alıyoruz
print(f("dikkat"))               #! aynı fonksiyon, başka isim
print(type(bagir), bagir.__name__)

islemler = [str.lower, str.upper, bagir]   #! fonksiyon listesi
for islem in islemler:
    print(islem("Pafta"))

def iki_kez(fonk, deger):        #! fonksiyon alan fonksiyon
    return fonk(fonk(deger))
print(iki_kez(bagir, "hey"))
```

`bagir` fonksiyon **nesnesidir**, `bagir("x")` ise onu **çağırmaktır**. Parantez, "şimdi çalıştır" demektir.

Fonksiyon alan ya da döndüren fonksiyonlara **higher-order function** denir. P13'te `sorted(..., key=str.lower)` yazarken zaten birini kullandın: `sorted`'a bir fonksiyon verdin, o da her eleman için onu çağırdı.
:::

::: tahmin
Çıktı tek satır:

```python
def kucult(s):
    return s.lower()

islem = kucult
print(islem("ABC"), islem is kucult, type(kucult).__name__)
```

???

`abc True function`. `islem` ve `kucult` aynı fonksiyon nesnesini gösteren iki etikettir.
:::

::: anlat lambda, sorted, map, filter
**`lambda`** tek ifadelik, isimsiz bir fonksiyon yazar. Kısa bir anahtar fonksiyonu için idealdir:

```python
kare = lambda x: x * x            #! lambda parametreler: ifade
print(kare(7))

olaylar = [("ali", 3), ("root", 9), ("veli", 5)]
print(sorted(olaylar, key=lambda o: o[1]))                 #! 2. alana göre
print(max(olaylar, key=lambda o: o[1]))                    #! max/min da key alır
kayitlar = [{"ad": "db", "risk": 7}, {"ad": "web", "risk": 9}]
print(sorted(kayitlar, key=lambda k: -k["risk"])[0]["ad"])
print(sorted(olaylar, key=lambda o: (-o[1], o[0])))       #! çoklu anahtar: demet döndür
```

Demet döndüren anahtar, **çok kriterli sıralamanın** anahtarıdır: Python demetleri önce ilk elemana, eşitse ikinciye göre karşılaştırır. Sayısal alanı ters çevirmek için başına `-` koyarsın.

**`map(f, dizi)`** her elemana f'yi uygular, **`filter(f, dizi)`** f'nin doğru döndüğü elemanları tutar. İkisi de tembeldir; sonuç için `list()`'e sarılır:

```python
print(list(map(int, ["22", "80", "443"])))           #! metinleri sayıya
print(list(filter(lambda p: p < 1024, [22, 8080, 443])))
print([int(x) for x in ["22", "80"]])                #! çoğu zaman üreteç daha okunaklı
```

### Dağıtım sözlüğü
Fonksiyonlar değer olduğuna göre bir sözlükte saklanabilirler. Uzun bir `if/elif` zincirinin yerini alırlar:

```python
islemler = {
    "topla": lambda a, b: a + b,
    "carp":  lambda a, b: a * b,
}
print(islemler["carp"](6, 7))
```

> [!NOT]
> `lambda` sadece **tek bir ifade** içerebilir: `return`, normal atama ve döngü deyimleri içermez; sonuç tek ifadeden gelir. Koşullu ifade ve comprehension bu ifadenin içinde bulunabilir. Bir isme atayacaksan (`f = lambda ...`) bunun yerine `def` yaz; hata mesajlarında `<lambda>` yerine gerçek ismi görürsün. lambda'nın yeri, bir fonksiyona yerinde verilen tek kullanımlık anahtardır.

> [!DERİN]
> `map` ve `filter` liste değil **yineleyici** (iterator) döndürür: elemanları istendikçe hesaplar ve bir kez tüketilir. `m = map(...)` sonra iki kez `list(m)` dersen ikincisi boş gelir. Bu davranışın arkasındaki protokolü P44'de göreceksin.
:::

::: tahmin
Üç satır:

```python
kayitlar = [("ali", 3), ("root", 9), ("veli", 5)]
print(sorted(kayitlar, key=lambda k: k[1], reverse=True)[0][0])
print(list(map(lambda x: x * 2, [1, 2, 3])))
print(list(filter(None, [0, 1, "", "a"])))
```

???

`root`, `[2, 4, 6]`, `[1, 'a']`. `filter(None, ...)` özel bir kullanımdır: fonksiyon yerine None verilirse doğruluk değeri doğru olan elemanları tutar.
:::

::: gorev uygula
`uygula(fonk, liste)` fonksiyonunu yaz: listedeki her elemana `fonk`'u uygulayıp sonuçları **yeni bir liste** olarak döndürsün.

```starter
def uygula(fonk, liste):
    for x in liste:
        fonk(x)
    return liste
```

```test
need("uygula")
veri = [1, 2]
sonuc = uygula(lambda x: x + 1, veri)
eq(veri, [1, 2], "orijinal liste korunmalı")
ok(sonuc is not veri, "yeni liste olmalı")
eq(sonuc, [2, 3], "dönüştürülmüş yeni liste")
eq(uygula(len, ["ssh", "https", ""]), [3, 5, 0], "uygula(len, ...) → [3, 5, 0]")
eq(uygula(str.upper, ["a", "b"]), ["A", "B"], "uygula(str.upper, ...) → ['A', 'B']")
eq(uygula(lambda x: x ** 2, [1, 2, 3]), [1, 4, 9], "uygula(lambda x: x**2, ...) → [1, 4, 9]")
eq(uygula(abs, []), [], "boş liste → []")
```

```solution
def uygula(fonk, liste):
    return [fonk(x) for x in liste]
```

```hint
`fonk` bir fonksiyon nesnesi; her eleman için `fonk(x)` çağır.
```
:::

::: gorev Olay önceliklendirme
Her olay `{"seviye": ..., "zaman": ...}` biçiminde bir sözlük. `sirala(olaylar)` fonksiyonu olayları önce **seviyeye** (kritik > yuksek > orta > dusuk), seviye eşitse **zamana** (küçükten büyüğe) göre sıralanmış **yeni bir liste** olarak döndürsün.

```starter
ONCELIK = {"kritik": 0, "yuksek": 1, "orta": 2, "dusuk": 3}

def sirala(olaylar):
    return sorted(olaylar, key=lambda o: o["zaman"])
```

```test
need("sirala")
o = [
    {"seviye": "orta", "zaman": 5},
    {"seviye": "kritik", "zaman": 9},
    {"seviye": "dusuk", "zaman": 1},
    {"seviye": "kritik", "zaman": 2},
    {"seviye": "yuksek", "zaman": 7},
]
once = [dict(x) for x in o]
s = sirala(o)
ok(s is not o, "yeni liste nesnesi")
eq(o, once, "tüm orijinal olaylar ve sıra korunmalı")
eq([(x["seviye"], x["zaman"]) for x in s],
   [("kritik", 2), ("kritik", 9), ("yuksek", 7), ("orta", 5), ("dusuk", 1)], "seviye, sonra zaman")
ok(o[0]["seviye"] == "orta", "orijinal liste değişmemeli (yeni liste döndür)")
eq(sirala([]), [], "boş liste → []")
```

```solution
ONCELIK = {"kritik": 0, "yuksek": 1, "orta": 2, "dusuk": 3}

def sirala(olaylar):
    return sorted(olaylar, key=lambda o: (ONCELIK[o["seviye"]], o["zaman"]))
```

```hint
`sorted(olaylar, key=lambda o: (ONCELIK[o["seviye"]], o["zaman"]))`. Demet anahtarı çoklu kriter demektir.
```
:::

::: gorev Dağıtım sözlüğü
`hesapla(a, islem, b)` fonksiyonunu yaz. `islem` `"+"`, `"-"`, `"*"` ya da `"/"` olabilir. İşlemleri bir **sözlükte lambda'larla** tut, `if/elif` zinciri kullanma. Bilinmeyen işlemde `None` döndür. Bölmede ikinci sayı sıfırsa Python'un `ZeroDivisionError` hatası değişmeden yükselsin; bu hatayı yakalamayı p25'te öğreneceğiz.

```starter
def hesapla(a, islem, b):
    islemler = {"+": lambda: a + b, "-": lambda: a - b, "*": lambda: a * b, "/": lambda: a / b}
    return islemler[islem]()
```

```test
need("hesapla")
eq(hesapla(6, "*", 7), 42, "6 * 7 → 42")
eq(hesapla(10, "-", 4), 6, "10 - 4 → 6")
eq(hesapla(1, "+", 2), 3, "1 + 2 → 3")
raises(ZeroDivisionError, hesapla, 1, "/", 0, msg="sıfıra bölme hatası korunur")
eq(hesapla(9, "/", 2), 4.5, "9 / 2 → 4.5")
eq(hesapla(2, "^", 3), None, "bilinmeyen işlem → None")
ok(uses("lambda") and "{" in src, "lambda'ları bir sözlükte tut")
ok(not uses("if") and not uses("match"), "if/elif ya da match kullanmadan")
```

```solution
ISLEMLER = {
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "*": lambda a, b: a * b,
    "/": lambda a, b: a / b,
}

def hesapla(a, islem, b):
    fonk = ISLEMLER.get(islem)
    return fonk(a, b) if fonk else None
```

```hint
`ISLEMLER = {"+": lambda a, b: a + b, ...}` sonra `ISLEMLER.get(islem)`.
```

```hint
`if` olmadan None dönmek için: `fonk(a, b) if fonk else None` bir koşullu **ifadedir**, if deyimi değildir. Testler sadece if deyimine bakar.
```
:::


::: anlat Yaygın yanlışlar
| Yanlış yaklaşım | Neden kırılır? | Doğrusu |
|---|---|---|
| Fonksiyonu aktarırken `fonk()` yazmak | Sonucu aktarır, fonksiyon nesnesini değil. | Çağırmadan `fonk` aktar. |
| Yalnız zamana göre sıralamak | Öncelik sırası kaybolur. | `(öncelik, zaman)` demetini anahtar yap. |
| `liste.sort()` sonucunu döndürmek | Yerinde değiştirir ve None döndürür. | Yeni liste için `sorted` kullan. |
:::

::: anlat AI derslerinde nerede?
- `ai-guvence-43` çözümündeki `sorted(range(d), key=lambda j: (-abs(v[j]), j))`, mutlak değer ve indisle çok kriterli sıralama yapar.
- `ai-uretim-09` testlerinde `lambda` ile kusurlu aday fonksiyonlar tanımlanır. Aynı doğrulama farklı fonksiyon nesnelerine uygulanır.
:::
