---
id: p07
title: Doğru, Yanlış ve Mantık
summary: bool, karşılaştırma, and/or/not, doğruluk değeri ve kısa devre.
kazanim: PCEP 1.4
---

::: anlat bool: iki değerli dünya
Karar veren her program `True` ve `False` üzerine kuruludur. Bu iki değerin türü **bool**'dur. Karşılaştırma işleçleri bool üretir:

| İşleç | Anlamı |
|---|---|
| `==` / `!=` | eşit / eşit değil |
| `<` `<=` `>` `>=` | küçük, küçük-eşit, büyük, büyük-eşit |
| `in` / `not in` | içinde mi |
| `is` / `is not` | **aynı nesne** mi (P19) |

```python
port = 443
print(port == 443)            #! True
print(port != 80)             #! True
print(1 < port < 1024)        #! zincir: 1 < port VE port < 1024
print("admin" in "/admin/panel")
print("Z" < "a")              #! True — metinler Unicode koduna göre sıralanır
```

`=` ile `==`'yi karıştırma: tek eşittir **atar**, çift eşittir **karşılaştırır**.

### and, or, not
- `a and b`: ikisi de doğruysa doğru
- `a or b`: en az biri doğruysa doğru
- `not a`: tersi

Öncelik: `not` > `and` > `or`. `a or b and c` aslında `a or (b and c)` demektir. Karışık ifadelerde parantez koy.

```python
yetkili = True
mesai = False
print(yetkili and mesai)      #! False
print(yetkili or mesai)       #! True
print(not mesai)              #! True
print(True + True)            #! 2 — bool aslında int'in alt türüdür
```

> [!DERİN]
> `bool`, `int`'in alt sınıfıdır: `True == 1` ve `False == 0`. Bu yüzden `sum([True, False, True])` → `2` yazıp bir listedeki doğruları sayabilirsin. Bu tarihsel bir karardır; Python'a bool 2.3'te eklendiğinde eski kodlar `1`/`0` kullanıyordu.
:::

::: tahmin
Çıktı tek satır:

```python
print(3 > 2 > 1, 1 == 1.0, "a" < "b", not 0)
```

???

`True True True True`. `3 > 2 > 1` zincirdir: `3 > 2 and 2 > 1`. (Başka dillerde bu `(3 > 2) > 1` → `True > 1` → yanlış olurdu!) `1 == 1.0` değer karşılaştırması olduğu için doğrudur. `not 0` → `0` yanlış sayılır, tersi doğrudur.
:::

::: anlat Doğruluk değeri ve kısa devre
Python'da **her** nesnenin bir doğruluk değeri vardır. Şunlar **yanlış** (falsy) sayılır, geri kalan her şey doğrudur:

- `False`, `None`
- sıfır: `0`, `0.0`
- boş koleksiyonlar: `""`, `[]`, `{}`, `()`, `set()`

```python
print(bool(""), bool("0"), bool([]), bool([0]))   #! False True False True
```

`"0"` metni doğrudur, çünkü boş değil! `[0]` de doğrudur, çünkü içinde bir eleman var. (Köşeli parantez `[]` liste, `{}` sözlük, `()` demet, `set()` kümedir; bu koleksiyonları P13–P17'de ayrıntılı göreceğiz, şimdilik sadece **içi boş olan her kabın yanlış sayıldığını** bilmen yeterli.)

### and/or bool döndürmez, işlenen döndürür
`a or b`: a doğruysa **a'yı**, değilse **b'yi** döndürür. `a and b`: a yanlışsa **a'yı**, değilse **b'yi** döndürür. Sonuç belli olunca gerisine **hiç bakılmaz**; buna **kısa devre** denir.

```python
ad = ""
print(ad or "misafir")        #! boşsa varsayılan değer — yaygın kalıp
kullanici = None
print(kullanici and kullanici.upper())   #! None ise .upper() hiç çağrılmaz
```

> [!GÜVENLİK]
> Kısa devre sırası güvenlik kontrollerinde önemlidir: `if kullanici is not None and kullanici.yetkili:` önce varlığı kontrol eder. Sırayı ters çevirirsen `None.yetkili` hata verir. Yetki kontrollerini de ucuz ve kesin olandan başlayarak sırala.
:::

::: tahmin
Dört satır:

```python
print(0 or "yok")
print([] or [1])
print(5 and 7)
print(None and 1 / 0)
```

???

- `0` yanlış → `or` ikinciyi döndürür: `yok`
- `[]` yanlış → `[1]`
- `5` doğru → `and` ikinciyi döndürür: `7`
- `None` yanlış → `and` hemen `None` döndürür; `1 / 0` **hiç çalışmaz**, hata yok. Kısa devre budur.
:::

::: gorev Parola politikası
Girdiden bir parola oku. Şu dört koşulun **hepsi** sağlanıyorsa `True`, değilse `False` yazdır (tek `print`, `if` kullanmadan):

1. en az 12 karakter
2. en az bir büyük harf içeriyor (ipucu: küçük harfe çevrilince değişiyorsa büyük harf vardır)
3. en az bir küçük harf içeriyor
4. sadece harflerden oluşmuyor (rakam ya da sembol var)

```starter
# Kusurlu başlangıç: görevdeki koşul ve çıktıyla karşılaştır.
parola = input()
print(len(parola) >= 12 or not parola.isalpha())
```

```stdin
Guvenli-Parola-2026
```

```test
eq(run("Guvenli-Parola-2026").strip(), "True", "Guvenli-Parola-2026 → True")
eq(run("Kisa1").strip(), "False", "Kisa1 → False (kısa)")
eq(run("uzunamahepsikucuk1").strip(), "False", "büyük harf yok → False")
eq(run("ABCDEFGHIJK1").strip(), "False", "küçük harf yok → False")
eq(run("UzunParolaYokRakam").strip(), "False", "sadece harf → False")
for parola_girdisi, beklenen in [("Abcdefghij1", "False"), ("Abcdefghijk1", "True"), ("Abcdefghijk-", "True"), ("Abcdefghijk ", "True"), ("123456789012", "False")]:
    eq(run(parola_girdisi).strip(), beklenen, "politika sınırı " + repr(parola_girdisi))
ok(not uses("if"), "Bu görevi if kullanmadan, tek mantık ifadesiyle çöz")
```

```solution
parola = input()
print(len(parola) >= 12 and parola != parola.lower() and parola != parola.upper() and not parola.isalpha())
```

```hint
`parola != parola.lower()` ancak içinde büyük harf varsa doğrudur.
```

```hint
Dört koşulu `and` ile bağla: `print(k1 and k2 and k3 and k4)`
```
:::

::: gorev Artık yıl
Girdiden bir yıl oku. Artık yılsa `True`, değilse `False` yazdır. Kural: **4'e bölünür ve 100'e bölünmez**, **ya da** 400'e bölünür.

```starter
# Kusurlu başlangıç: görevdeki koşul ve çıktıyla karşılaştır.
yil = int(input())
print(yil % 4 == 0)
```

```stdin
2024
```

```test
eq(run("2024").strip(), "True", "2024 → True")
eq(run("1900").strip(), "False", "1900 → False (100'e bölünür, 400'e değil)")
eq(run("2000").strip(), "True", "2000 → True (400'e bölünür)")
eq(run("2026").strip(), "False", "2026 → False")
eq(run("100000000000000000100").strip(), "False", "büyük tam sayılı yüzyıl 400 ile bölünmüyor")
```

```solution
yil = int(input())
print((yil % 4 == 0 and yil % 100 != 0) or yil % 400 == 0)
```

```hint
"Bölünür" = kalan sıfır: `yil % 4 == 0`
```
:::

::: gorev Varsayılan ad
Girdiden bir ad oku ve `Merhaba, <ad>` yazdır. Ad **boş** gelirse `Merhaba, misafir` yazsın. `if` kullanma, `or`'un davranışından yararlan.

```starter
# Kusurlu başlangıç: görevdeki koşul ve çıktıyla karşılaştır.
ad = input()
print(f"Merhaba, {ad and 'misafir'}")
```

```stdin
Ali
```

```test
eq(run("Ali").strip(), "Merhaba, Ali", "Ali → Merhaba, Ali")
eq(run("\n").strip(), "Merhaba, misafir", "boş → Merhaba, misafir")
ok(not uses("if") and not uses("ifexp"), "if kullanmadan çöz")
```

```solution
ad = input()
print(f"Merhaba, {ad or 'misafir'}")
```

```hint
`ad or "misafir"` — boş metin yanlış sayılır.
```
:::

::: anlat Harf dışı karakter ne demek?
`not parola.isalpha()` rakam zorunluluğu koymaz. Tire veya boşluk da bu koşulu sağlar. Bu görev mantık alıştırmasıdır; gerçek bir parola standardı belirlemez.
:::

::: anlat Yaygın yanlışlar
| Yanlış yaklaşım | Neden kırılır? | Doğrusu |
|---|---|---|
| Koşulları or ile bağlamak | Tek şartın sağlanması yeterli olur. | Hepsi gerekiyorsa and kullan. |
| "0" metnini yanlış saymak | Boş olmayan metin doğru sayılır. | Boş metin ile sıfır sayısını ayırt et. |
| and/or daima bool döndürür sanmak | İşleçler işlenenlerden birini döndürür. | Varsayılan adda ad or "misafir" kullan. |
:::

::: anlat AI derslerinde nerede?
- `ai-olay-01` — Dış bağlantı (egress) kararında şema, alan adı ve kullanıcı alanı koşulları `and`, `or` ve `not` ile birleştirilir.
- `ai-guvence-43` — Silinme oranında zıt işaret ve yeterli büyüklük `and` ile birlikte aranır.

Bu örneklerin fonksiyon ve model ayrıntıları ileride öğrenilecek; burada tanıdığın Python işlemini izlemen yeterli.
:::
