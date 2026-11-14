---
id: p11
title: İç İçe Döngüler ve Döngü-else
summary: Döngü içinde döngü, break'in kapsamı ve Python'a özgü for/while ... else.
kazanim: PCEP 2.2
---

::: anlat Döngü içinde döngü
Bir döngünün bloğunda başka bir döngü olabilir. İçteki döngüye dıştakinin her turunda yeniden girilir; break gibi bir çıkış iç döngüyü erken bitirebilir:

```python
for satir in range(1, 4):
    for sutun in range(1, 4):
        print(satir * sutun, end="\t")   #! \t sekme: sütunları hizalar
    print()                              #! iç döngü bitti → satır sonu
```

Dış döngü 3, iç döngü 3 tur → toplam **9** kez çalışır. 1000 × 1000'lik iç içe döngü bir milyon tur eder: iç içe döngüler hızla pahalılaşır. Bu bedeli P68'te "karmaşıklık" (Big-O) olarak ölçeceğiz.

Tipik kullanımlar: tablo/ızgara dolaşmak, **her çifti** karşılaştırmak, desen çizmek.

```python
kullanicilar = ["ali", "veli", "ali", "ayse"]
for i in range(len(kullanicilar)):
    for j in range(i + 1, len(kullanicilar)):   #! j hep i'den sonra: her çift bir kez
        if kullanicilar[i] == kullanicilar[j]:
            print("tekrar:", kullanicilar[i], "→ konum", i, "ve", j)
```

> [!TUZAK]
> `break` sadece **içinde bulunduğu** döngüden çıkar. İç döngüde `break` dersen dış döngü devam eder. İki döngüden birden çıkmak istiyorsan ya bir bayrak kullan ya da kodu bir fonksiyona koyup `return` et (P20).
:::

::: tahmin
Üç satırda ne yazdırır?

```python
for i in range(1, 4):
    for j in range(1, 4):
        if j > i:
            break
        print(i * j, end=" ")
    print()
```

???

Üç satırda sırasıyla `1 `, `2 4 ` ve `3 6 9 ` yazdırır (`end=" "` yüzünden her satırın sonunda bir boşluk da vardır). Her satırda `j`, `i`'yi geçince iç döngü kırılır ama dış döngü devam eder; böylece bir **üçgen** oluşur.
:::

::: anlat Döngü-else: "hiç break olmadıysa"
Python'un pek bilinmeyen bir özelliği: `for` ve `while` döngülerinin de bir `else` dalı olabilir. Bu dal, döngü **break ile kesilmeden** normal biçimde bittiğinde çalışır.

Klasik kullanım **arama**dır: "aradığımı bulursam break; hiç bulamazsam else":

```python
yasakli = ["root", "admin", "test"]
kullanici = "ayse"
for y in yasakli:
    if kullanici == y:
        print("yasaklı kullanıcı adı!")
        break
else:                              #! döngü break'siz bitti = hiç eşleşme yok
    print(kullanici, "kullanılabilir")
```

Döngü-else olmasaydı bir bayrak gerekirdi:

```python norun
bulundu = False
for y in yasakli:
    if kullanici == y:
        bulundu = True
        break
if not bulundu:
    print("kullanılabilir")
```

> [!NOT]
> Bu else kolunu arama örneklerinde kafanda "**nobreak**" diye oku: `for ... nobreak:`. P09'daki hesap kilidi görevini `while ... else` ile çözdüysen zaten kullandın.
:::

::: tahmin
Ne yazdırır?

```python
for n in [3, 5, 7]:
    if n % 2 == 0:
        print("çift bulundu")
        break
else:
    print("çift yok")
```

???

`çift yok`. Listedeki hiçbir sayı çift olmadığı için `break` hiç çalışmaz; döngü normal biter ve `else` dalı çalışır.
:::

::: gorev Yıldız üçgeni
Girdiden sıfır veya pozitif bir tam sayı n oku ve n satırlık bir üçgen çiz: 1. satırda 1 yıldız, n. satırda n yıldız. **İç içe döngü** kullan (`"*" * i` hilesi yok).

```cikti
*
**
***
```

```starter
# Kusurlu başlangıç: görevle karşılaştırıp hatayı düzelt.
n = int(input())
for i in range(1, n):
    for j in range(i):
        print("*", end="")
    print()
```

```stdin
3
```

```test
eq(run("3").strip().splitlines(), ["*", "**", "***"], "3 → üç satır")
eq(run("5").strip().splitlines(), ["*" * i for i in range(1, 6)], "5 → beş satır")
eq(run("0"), "", "sıfır satırlık üçgen")
eq(run("1"), "*\n", "tek satırlık üçgen")
ok(sum(1 for node in __import__("ast").walk(tree) if isinstance(node, __import__("ast").For)) >= 2, "İki for döngüsü (iç içe) kullan")
ok('"*" *' not in src and "'*' *" not in src and '* "*"' not in src, "Metin çarpma hilesi olmadan, döngüyle çiz")
```

```solution
n = int(input())
for i in range(1, n + 1):
    for j in range(i):
        print("*", end="")
    print()
```

```hint
Dış döngü satırları (1..n), iç döngü o satırdaki yıldızları basar. Satır sonunda boş `print()`.
```
:::

::: gorev İlk tekrar eden karakter
Girdiden bir metin oku. Soldan sağa bakıldığında, metinde **daha sonra tekrar geçen ilk karakteri** yazdır. Yoksa `yok` yaz. İç içe döngü ve döngü-else kullan.

- `abcdbe` → `b`
- `abccba` → `a` (a sonda tekrar geçiyor)
- `abc` → `yok`

```starter
# Kusurlu başlangıç: görevle karşılaştırıp hatayı düzelt.
metin = input()
for i in range(len(metin)):
    for j in range(i + 1, len(metin)):
        if metin[i] == metin[j]:
            print(metin[i])
            break
```

```stdin
abcdbe
```

```test
eq(run("abcdbe").strip(), "b", "abcdbe → b")
eq(run("abccba").strip(), "a", "abccba → a")
eq(run("abc").strip(), "yok", "abc → yok")
eq(run("aa").strip(), "a", "aa → a")
eq(run("x").strip(), "yok", "x → yok")
eq(run("\n").strip(), "yok", "boş metinde tekrar yok")
eq(run("abcbad").strip(), "a", "ilk aday ile ilk tamamlanan tekrar farklı")
ok(sum(1 for node in __import__("ast").walk(tree) if isinstance(node, (__import__("ast").For, __import__("ast").While))) >= 2, "İç içe döngü kullan")
ok(any(isinstance(node, (__import__("ast").For, __import__("ast").While)) and node.orelse for node in __import__("ast").walk(tree)), "Döngü-else kullan")
```

```solution
metin = input()
for i in range(len(metin)):
    for j in range(i + 1, len(metin)):
        if metin[i] == metin[j]:
            break
    else:
        continue
    print(metin[i])
    break
else:
    print("yok")
```

```hint
Her i için, i'den sonraki j'lere bak. Eşleşme bulursan cevabı yazıp **iki döngüden de** çıkman lazım.
```

```hint
Hile: iç döngünün `else: continue` dalı "eşleşme yoksa dış döngüye devam et" der. İç döngü break ile biterse continue atlanır ve alttaki satırlar çalışır.
```
:::

::: gorev Asal listesi
Girdiden n oku ve n'ye kadar (n dahil) bütün asal sayıları aralarında boşlukla tek satırda yazdır. İç içe döngü ve döngü-else kullan.

```cikti
2 3 5 7 11 13 17 19
```

```starter
# Kusurlu başlangıç: görevle karşılaştırıp hatayı düzelt.
n = int(input())
for sayi in range(2, n + 1):
    for b in range(2, int(sayi ** 0.5) + 1):
        if sayi % b == 0:
            break
    print(sayi, end=" ")
```

```stdin
20
```

```test
eq(run("20").strip(), "2 3 5 7 11 13 17 19", "20 → tek satırda boşlukla 2 3 5 7 11 13 17 19")
ok(len(run("20").splitlines()) == 1, "asal sayılar tek satırda yazılmalı")
eq(run("2").strip(), "2", "2 → 2")
eq(run("1").split(), [], "1 → boş")
eq(run("1"), "\n", "boş asal listesinde de satır sonu")
eq(len(run("1000").split()), 168, "1000'e kadar 168 asal var")
ok(sum(1 for node in __import__("ast").walk(tree) if isinstance(node, (__import__("ast").For, __import__("ast").While))) >= 2, "İç içe döngü kullan")
ok(any(isinstance(node, (__import__("ast").For, __import__("ast").While)) and node.orelse for node in __import__("ast").walk(tree)), "Döngü-else kullan")
```

```solution
n = int(input())
for sayi in range(2, n + 1):
    for b in range(2, int(sayi ** 0.5) + 1):
        if sayi % b == 0:
            break
    else:
        print(sayi, end=" ")
print()
```

```hint
Dış döngü 2..n arası her sayı, iç döngü olası bölenler. İç döngü break'siz biterse (else) sayı asaldır.
```
:::

::: anlat Yaygın yanlışlar
| Yanlış yaklaşım | Neden kırılır? | Doğrusu |
|---|---|---|
| İç döngüde break ile iki döngüden çıkmayı beklemek | break en yakın döngüden çıkar. | Dış döngü için ayrı çıkış veya bayrak kur. |
| for-else kolunu if ile eşlemek | else döngünün girintisindeyse normal tamamlanmaya bağlıdır. | else girintisini hangi yapıya ait olduğuna göre yaz. |
| İlk tekrarın ikinci görülme anını seçmek | abccba örneğinde c erken tekrar eder ama soldaki ilk aday a’dır. | Dış döngüde aday konumunu soldan sağa seç. |
:::

::: anlat AI derslerinde nerede?
- `ai-uretim-09` — LoRA hesapları çıktı satırları ile giriş koordinatlarını iç içe dolaşır.
- `ai-guvence-43` — TIES her vektörün koordinatlarında seçim yapar; iç içe gezinme aynı kalıbı kullanır.
:::
