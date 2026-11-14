---
id: p17
title: Kümeler
summary: Benzersiz elemanlar, hızlı üyelik ve küme cebiri: birleşim, kesişim, fark.
---

::: anlat Benzersiz, sırasız, hızlı
Küme (set), **her elemanın en fazla bir kez** bulunduğu, **sırasız** bir koleksiyondur. Süslü parantezle yazılır:

```python
ipler = {"10.0.0.1", "10.0.0.2", "10.0.0.1"}   #! tekrar otomatik atılır
print(ipler, len(ipler))
tekil = set([3, 1, 3, 2, 1])                    #! listeden küme
print(tekil)
bos = set()                                     #! DİKKAT: {} boş SÖZLÜKTÜR
bos.add("x")
bos.add("x")                                    #! ikinci ekleme etkisiz
bos.discard("yok")                              #! yoksa sessiz geçer (remove hata verir)
print(bos, "x" in bos)
```

Kümeler indekslenemez (`s[0]` olmaz), çünkü sıraları yoktur. Elemanlar sözlük anahtarları gibi **hash'lenebilir** olmalıdır.

### Asıl güç: üyelik testi
`x in liste` listeyi baştan sona tarar: O(n). `x in kume` hash ile doğrudan yuvaya bakar: ortalama O(1). Gerçek süre; veri, donanım, hash çakışmaları ve ölçüm yöntemine bağlıdır. Küme oluşturmanın da zaman ve bellek maliyeti vardır; ortalama O(1), her aramanın aynı sürede biteceği garantisi değildir (`import time`, Python ile hazır gelen kronometre modülünü yükler; modülleri P31'de göreceğiz).

```python
import time
liste = list(range(2_000_000))
kume = set(liste)
t = time.perf_counter(); 1_999_999 in liste; t1 = time.perf_counter() - t
t = time.perf_counter(); 1_999_999 in kume; t2 = time.perf_counter() - t
print(f"liste: {t1*1000:.2f} ms   küme: {t2*1000:.4f} ms")
```

> [!GÜVENLİK]
> IOC listeleri (kötü IP, alan adı, hash), izin listeleri ve yasak listeleri **küme** olarak tutulur. Milyonlarca olayı bir IOC listesine karşı süzerken liste kullanmak, SOC'un analiz hattını kilitleyen klasik bir performans hatasıdır.
:::

::: anlat Küme cebiri
Matematikteki küme işlemleri birebir vardır:

| İşleç | Metot | Anlamı |
|---|---|---|
| `a \| b` | `a.union(b)` | birleşim: ikisinden herhangi birinde |
| `a & b` | `a.intersection(b)` | kesişim: ikisinde de |
| `a - b` | `a.difference(b)` | fark: a'da var, b'de yok |
| `a ^ b` | `a.symmetric_difference(b)` | sadece birinde |
| `a <= b` | `a.issubset(b)` | a, b'nin alt kümesi mi |

```python
dun = {"22", "80", "443"}
bugun = {"22", "443", "4444"}
print("yeni açılan:", bugun - dun)       #! dün yoktu, bugün var → şüpheli!
print("kapanan:", dun - bugun)
print("değişmeyen:", dun & bugun)
print("değişen:", dun ^ bugun)
```

Sırayı koruyarak tekrarları atmak istiyorsan kümeyi değil sözlüğü kullan: `list(dict.fromkeys(liste))`. Sözlük hem benzersizdir hem ekleme sırasını korur.

> [!DERİN]
> Değiştirilemez küme de var: `frozenset`. Hash'lenebilir olduğu için sözlük anahtarı ya da başka bir kümenin elemanı olabilir. Küçük tam sayıların hash'i kendisine eşit olduğundan `{3, 1, 2}` çoğu zaman sıralı **görünür**, ama buna asla güvenme; metin kümelerinin sırası her çalıştırmada değişebilir (hash rastgeleleştirme, P19).
:::

::: tahmin
Çıktı tek satır:

```python
a = {1, 2, 3}
b = {2, 3, 4}
print(sorted(a & b), sorted(a | b), sorted(a - b), sorted(a ^ b))
```

???

`[2, 3] [1, 2, 3, 4] [1] [1, 4]`. Kesişim ortak olanlar, birleşim hepsi, fark a'da olup b'de olmayanlar, simetrik fark ise sadece birinde olanlardır.
:::

::: tahmin
Çıktı tek satır:

```python
s = set("banana")
print(len(s), "n" in s, {} == set(), type({}).__name__)
```

???

`3 True False dict`. "banana" harfleri b, a, n'dir. `{}` boş sözlüktür, boş küme değil; ikisi eşit sayılmaz.
:::

::: gorev Port farkı
İki satır var: A sunucusunun açık portları ve B sunucusunun açık portları (boşlukla ayrılmış). İki satır yazdır:

1. **İkisinde de** açık olan portlar, küçükten büyüğe
2. **Sadece A'da** açık olan portlar, küçükten büyüğe

Hiç yoksa boş satır yaz. Portları sayı olarak sırala.

```cikti
22 443
80
```

```starter
a = set(input().split())
b = set(input().split())
print(*sorted(a & b))
print(*sorted(a - b))
```

```stdin
22 80 443
443 22 3389
```

```test
eq(run("\n\n").split("\n")[:2], ["", ""], "iki boş küme")
eq(run("2 2 10\n2 2").split("\n")[:2], ["2", "10"], "tekrarlar")
eq(run("22 80 443\n443 22 3389").split("\n")[:2], ["22 443", "80"], "örnek")
eq(run("9 100 10\n100 9").split("\n")[:2], ["9 100", "10"], "sayısal sıralama")
eq(run("1 2\n3 4").split("\n")[:2], ["", "1 2"], "ortak yok → ilk satır boş")
ok(uses("setcomp") or calls("set"), "kümelerle çöz")
```

```solution
a = set()
for x in input().split():
    a.add(int(x))
b = set()
for x in input().split():
    b.add(int(x))
print(*sorted(a & b))
print(*sorted(a - b))
```

```hint
Önce sayıya çevirip küme yap. `sorted(a & b)` sıralı liste verir; `print(*liste)` boşlukla yazar (boş listede boş satır).
```
:::

::: gorev İzin listesi
İlk satır izinli kullanıcılar, ikinci satır giriş denemesi yapan kullanıcılar (tekrar edebilir). İzin listesinde **olmayan** kullanıcıları alfabetik ve tekrarsız olarak, boşlukla ayrılmış şekilde yazdır. Hepsi izinliyse `temiz` yaz.

```starter
izinli = set(input().split())
denemeler = set(input().split())
print(" ".join(sorted(izinli - denemeler)))
```

```stdin
ali ayse root
ali mallory root eve mallory
```

```test
eq(run("ali ayse root\nali mallory root eve mallory").strip(), "eve mallory", "örnek")
eq(run("a b\na a b").strip(), "temiz", "hepsi izinli → temiz")
eq(run("ali\n\n").strip(), "temiz", "hiç deneme yoksa temiz")
eq(run("x\nz y z").strip(), "y z", "alfabetik ve tekrarsız")
```

```solution
izinli = set(input().split())
denemeler = set(input().split())
yabanci = sorted(denemeler - izinli)
print(" ".join(yabanci) if yabanci else "temiz")
```

```hint
`denemeler - izinli` farkı izinsizleri verir. `sorted` hem sıralar hem listeye çevirir.
```
:::

::: gorev Pangram
`import string`, Python ile gelen standart kütüphane modülünü yükler; kurulum gerekmez. `string.ascii_lowercase`, `abcdefghijklmnopqrstuvwxyz` metnidir.

Girdiden bir cümle oku. İngiliz alfabesinin 26 harfinin **hepsini** içeriyorsa (büyük-küçük harf fark etmez) `True`, yoksa `False` yazdır. Alt küme işleciyle çöz.

```starter
import string
cumle = input()
alfabe = set(string.ascii_lowercase)
print(alfabe <= set(cumle))
```

```stdin
The quick brown fox jumps over the lazy dog
```

```test
eq(run("ABCDEFGHIJKLMNOPQRSTUVWXYZ").strip(), "True", "tam büyük alfabe")
eq(run("abcdefghijklmnopqrstuvwxy").strip(), "False", "yalnız z eksik")
eq(run("\n").strip(), "False", "boş cümle")
eq(run("The quick brown fox jumps over the lazy dog").strip(), "True", "klasik pangram")
eq(run("Hello world").strip(), "False", "eksik harfler")
eq(run("Pack my box with five dozen liquor jugs!").strip(), "True", "noktalama olsa da")
ok("<=" in src or calls("issubset") or ">=" in src or calls("issuperset"), "alt küme işleci (<=) ya da issubset kullan")
```

```solution
import string
cumle = input()
alfabe = set(string.ascii_lowercase)
print(alfabe <= set(cumle.lower()))
```

```hint
`alfabe <= set(cumle.lower())`: alfabenin her harfi cümlede var mı?
```
:::


::: anlat Yaygın yanlışlar
| Yanlış yaklaşım | Neden kırılır? | Doğrusu |
|---|---|---|
| `{}` ile boş küme açmak | Boş sözlük oluşturur. | `set()` kullan. |
| Küme çıktısının sırasına güvenmek | Yineleme sırası garanti edilmez. | Görüntüleme için `sorted` kullan. |
| Metin portlarını sıralamak | `100`, metin sıralamasında `9` önüne gelir. | Önce `int` ile dönüştür. |
:::

::: anlat AI derslerinde nerede?
- `ai-savunma-19` çözümü `set(politika)` ile sözlük anahtarlarını kümeye çevirip beklenen alanlarla karşılaştırır. Eksik ve fazla alanlar böyle bulunur.
- `ai-guvence-43` çözümündeki küme işlemleri, seçilen indisleri benzersiz tutar. `sec = set(...)`, her vektörden seçilen boyutları tutar; `j in sec` bu seçimi denetler.
:::
