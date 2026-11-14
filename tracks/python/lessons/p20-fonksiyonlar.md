---
id: p20
title: Fonksiyonlar · def ve return
summary: Kodu isimlendirip yeniden kullanmak; parametre, dönüş değeri, None ve print/return farkı.
kazanim: PCEP 4.1
---

::: anlat Kodu isimlendirmek
Fonksiyon, bir iş yapan kod parçasına verilmiş **isimdir**. Bir kez tanımlarsın, istediğin kadar çağırırsın:

```python
def selamla(ad):                  #! def isim(parametreler):
    """Verilen ada selam metni döndürür."""   #! docstring: fonksiyonun belgesi
    return f"Merhaba, {ad}!"      #! return: sonucu çağırana geri ver

mesaj = selamla("Ayşe")           #! çağrı: "Ayşe" → ad parametresine bağlanır
print(mesaj)
print(selamla("root"))
```

- **Parametre**: tanımdaki isim (`ad`). **Argüman**: çağrıda verilen değer (`"Ayşe"`).
- `return` fonksiyonu **hemen bitirir** ve değeri çağrının yerine koyar.
- `return` yoksa (ya da çıplak `return` varsa) fonksiyon **`None`** döndürür.

Neden fonksiyon? Üç sebep: **tekrarı önler** (aynı kodu 5 yere kopyalamak yerine 1 tanım), **isim verir** (`ip_gecerli_mi(x)` bir yorum satırından daha açıklayıcıdır) ve **test edilebilir** (bu paftadan itibaren görev testleri fonksiyonlarını doğrudan çağıracak). Kendi kendini çağıran özyinelemeli fonksiyonları P24'te, `yield` ile adım adım değer üreten üreteç fonksiyonlarını ise P45'te göreceğiz.

Röntgen'i bir fonksiyon çağrısında dene: çağrı anında yeni bir **çerçeve** (frame) açılır ve fonksiyonun kendi değişkenleri orada yaşar. `return` ile çerçeve kapanır ve "↩ döndürülen" değeri görürsün.

> [!TUZAK]
> **print ≠ return.** `print` değeri ekrana yazar ve unutur. `return` değeri çağırana **verir**, böylece başka bir işlemde kullanılabilir. Ekrana yazan ama döndürmeyen fonksiyonun sonucu `None`'dır. Görevlerde "döndür" yazıyorsa testler `return`'ü kontrol eder; ekrana basmak işe yaramaz.
:::

::: tahmin
İki satır:

```python
def kare(x):
    return x * x

def yaz_kare(x):
    print(x * x)

a = kare(3)
b = yaz_kare(4)
print(a, b)
```

???

`16`, sonra `9 None`. `yaz_kare(4)` çağrılırken ekrana `16` basar ama hiçbir şey döndürmez, yani `b` `None` olur. `kare(3)` ise 9'u döndürür ve hiçbir şey yazmaz.
:::

::: anlat Erken dönüş, çoklu dönüş, belgeleme
```python
def bol(a, b):
    """a'yı b'ye böler; (bölüm, kalan) döndürür. b sıfırsa None."""
    if b == 0:
        return None               #! erken dönüş: istisnai durumu önce ele al
    return a // b, a % b          #! virgül = demet: birden çok değer döndür

bolum, kalan = bol(17, 5)         #! dönen demeti paketten çıkar
print(bolum, kalan)
print(bol(1, 0))
help(bol)                          #! docstring'i gösterir
```

"Erken dönüş" (guard clause) kalıbı, P08'de konuştuğumuz iç içe `if` ok biçimini düzleştirmenin en temiz yoludur: önce geçersiz durumları `return` ile ele, sonra asıl işi girintisiz yaz.

> [!DERİN]
> `def` bir **çalıştırılabilir deyimdir**: Python o satıra geldiğinde bir fonksiyon nesnesi oluşturur ve isme bağlar. Fonksiyon gövdesi o anda **çalışmaz**, sadece derlenmiş bytecode'u (`selamla.__code__`) saklanır. Bu yüzden bir fonksiyonun içinde henüz tanımlanmamış başka bir fonksiyonu çağırabilirsin, yeter ki **çağrı anında** tanımlı olsun.
:::

::: tahmin
Çıktı tek satır:

```python
def sinifla(n):
    if n < 0:
        return "negatif"
    if n == 0:
        return "sıfır"
    return "pozitif"
    print("buraya gelinmez")

print(sinifla(-2), sinifla(0), sinifla(5))
```

???

`negatif sıfır pozitif`. Her `return` fonksiyonu anında bitirir; son satırdaki `print` hiçbir zaman çalışmaz ("ölü kod"). Elif zincirine gerek kalmadı, çünkü her dal `return` ile çıkıyor.
:::

::: gorev Ortalama
`ortalama(sayilar)` fonksiyonunu yaz: bir sayı listesinin ortalamasını **döndürsün**. Liste boşsa `None` döndürsün (sıfıra bölme yok!).

```starter
def ortalama(sayilar):
    print(sum(sayilar) / len(sayilar))
```

```test
need("ortalama")
eq(ortalama([1, 2, 3, 4]), 2.5, "ortalama([1, 2, 3, 4]) → 2.5")
eq(ortalama([10]), 10, "ortalama([10]) → 10")
eq(ortalama([]), None, "ortalama([]) → None")
yakin(ortalama([0.1, 0.2]), 0.15, "ortalama([0.1, 0.2]) ≈ 0.15")
```

```solution
def ortalama(sayilar):
    if not sayilar:
        return None
    return sum(sayilar) / len(sayilar)
```

```hint
Erken dönüş: `if not sayilar: return None`
```
:::

::: gorev IPv4 doğrulayıcı
`ip_gecerli_mi(ip)` fonksiyonunu yaz. Metin geçerli bir IPv4 adresiyse `True`, değilse `False` döndürsün:

- Noktayla ayrılmış **tam 4** parça
- Her parça yalnız ASCII `0`–`9` rakamlarından oluşmalı ve 0–255 arası olmalı
- Başında sıfır olmamalı (`"0"` olur, `"01"` olmaz)

> [!GÜVENLİK]
> Girdi doğrulamayı **izin listesi** mantığıyla yap: "geçerli olan neyse onu kabul et", "kötü olan neyse onu reddet" değil. `"10.0.0.1; rm -rf /"` gibi bir girdiyi ancak katı bir doğrulama durdurur.

```starter
def ip_gecerli_mi(ip):
    return len(ip.split(".")) == 4
```

```test
need("ip_gecerli_mi")
for bozuk in ["9" * 5000 + ".1.1.1","².1.1.1", "１２.1.1.1", "١.1.1.1", "+1.2.3.4", " 1.2.3.4", "1.2.3.4 "]:
    eq(ip_gecerli_mi(bozuk), False, "ASCII rakam dışında girdi reddi: " + bozuk)
eq(ip_gecerli_mi("192.168.1.10"), True, "192.168.1.10 → True")
eq(ip_gecerli_mi("0.0.0.0"), True, "0.0.0.0 → True")
eq(ip_gecerli_mi("255.255.255.255"), True, "255.255.255.255 → True")
eq(ip_gecerli_mi("256.1.1.1"), False, "256.1.1.1 → False (255'i aşıyor)")
eq(ip_gecerli_mi("1.2.3"), False, "1.2.3 → False (3 parça)")
eq(ip_gecerli_mi("1.2.3.4.5"), False, "1.2.3.4.5 → False (5 parça)")
eq(ip_gecerli_mi("1.2.3.a"), False, "1.2.3.a → False")
eq(ip_gecerli_mi("01.2.3.4"), False, "01.2.3.4 → False (baştaki sıfır)")
eq(ip_gecerli_mi("1.2.3.4; ls"), False, "1.2.3.4; ls → False")
eq(ip_gecerli_mi(""), False, "boş metin → False")
eq(ip_gecerli_mi("1..2.3"), False, "1..2.3 → False (boş parça)")
```

```solution
def ip_gecerli_mi(ip):
    parcalar = ip.split(".")
    if len(parcalar) != 4:
        return False
    for p in parcalar:
        if not p.isascii() or not p.isdigit():
            return False
        if len(p) > 1 and p[0] == "0":
            return False
        if len(p) > 3 or int(p) > 255:
            return False
    return True
```

```hint
Önce `split(".")` ve parça sayısını kontrol et. Sonra her parça için sırayla: ASCII rakam mı, baştaki sıfır var mı, üç karakterden uzun ya da 255'ten büyük mü? Uzunluğu önce elemek, çok uzun sayıyı `int` ile dönüştürmeyi önler. İlk kusurda `return False`.
```

```hint
`"".isdigit()` False döndürür, yani boş parça kendiliğinden elenir. `isdigit` bazı Unicode rakamlarını da kabul eder; `isascii` ile yalnız ASCII rakamlarını kabul ederiz.
```
:::

::: gorev Hazır fonksiyonsuz min-max
`min_max(sayilar)` fonksiyonunu yaz: boş olmayan bir listenin **en küçük ve en büyük** elemanını `(en_kucuk, en_buyuk)` demeti olarak döndürsün. `min()`, `max()` ve `sorted()` kullanmak yok; listeyi **bir kez** dolaş.

```starter
def min_max(sayilar):
    kucuk = buyuk = 0
    for n in sayilar:
        if n < kucuk: kucuk = n
        if n > buyuk: buyuk = n
    return kucuk, buyuk
```

```test
need("min_max")
eq(min_max([1, 2, 3]), (1, 3), "ilk eleman minimum")
eq(min_max([3, 2, 1]), (1, 3), "ilk eleman maksimum")
eq(min_max([4, 4, 4]), (4, 4), "tüm değerler eşit")
eq(min_max([3, 1, 4, 1, 5, 9, 2]), (1, 9), "min_max([3,1,4,1,5,9,2]) → (1, 9)")
eq(min_max([7]), (7, 7), "tek eleman → (7, 7)")
eq(min_max([-5, -1, -10]), (-10, -1), "negatifler")
ok(not calls("min") and not calls("max") and not calls("sorted") and not calls("sort"), "min/max/sorted kullanmadan")
ok(sum(1 for node in __import__("ast").walk(tree) if isinstance(node, (__import__("ast").For, __import__("ast").While))) == 1, "Listeyi tek döngüde bir kez dolaş")
```

```solution
def min_max(sayilar):
    kucuk = buyuk = sayilar[0]
    for n in sayilar[1:]:
        if n < kucuk:
            kucuk = n
        elif n > buyuk:
            buyuk = n
    return kucuk, buyuk
```

```hint
İlk elemanla başla: `kucuk = buyuk = sayilar[0]`. Sonra kalanları karşılaştır.
```
:::


::: anlat Yaygın yanlışlar
| Yanlış yaklaşım | Neden kırılır? | Doğrusu |
|---|---|---|
| Sonucu `print` edip döndürmemek | Çağıran `None` alır. | Hesaplanan değeri `return` ile ver. |
| IPv4 için yalnız parça sayısına bakmak | Aralık, boş parça ve karakter hataları kaçar. | Her parçayı ayrı ayrı doğrula. |
| Min-max değerlerini sıfırla başlatmak | Tamamı pozitif veya negatif listelerde yanlış sınır üretir. | Boş olmayan listenin ilk elemanıyla başla. |
:::

::: anlat AI derslerinde nerede?
- `ai-savunma-19` çözümündeki fonksiyonlar politika kontrolünün sonucunu çağırana döndürür; sonuç daha sonra test tarafından karşılaştırılır.
- `ai-uretim-09` çözümündeki fonksiyonlar eğitim ve karşılaştırma işlerini yeniden kullanılabilir parçalara ayırır. `return` ile verilen sonuçlar başka hesaplara girer.
:::
