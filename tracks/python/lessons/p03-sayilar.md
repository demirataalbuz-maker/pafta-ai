---
id: p03
title: Sayılar
summary: int, float, yedi aritmetik işleç, kayan nokta tuzağı ve onaltılık sayılar.
kazanim: PCEP 1.3, PCEP 1.4
---

::: anlat İki sayı türü, yedi işleç
Python'da iki temel sayı türü var: **int** (tam sayı: `42`, `-7`, `0`) ve **float** (ondalıklı: `3.14`, `2.0`). Bunlarla yapabileceğin işlemler:

| İşleç | Anlamı | Örnek | Sonuç |
|---|---|---|---|
| `+` `-` `*` | toplama, çıkarma, çarpma | `6 * 7` | `42` |
| `/` | bölme (**her zaman float**) | `8 / 2` | `4.0` |
| `//` | tam bölme (aşağı yuvarlar) | `7 // 2` | `3` |
| `%` | mod (kalan) | `7 % 2` | `1` |
| `**` | üs | `2 ** 10` | `1024` |

```python
print(7 / 2)       #! 3.5 — / daima float verir
print(7 // 2)      #! 3   — kaç tam kez sığar
print(7 % 2)       #! 1   — geriye ne kalır
print(2 + 3 * 4)   #! 14  — çarpma önce
print((2 + 3) * 4) #! 20  — parantez önceliği değiştirir
print(2 ** 100)    #! sabit 64 bit sınırı yok; bellek yine sınırlıdır
print(1_000_000)   #! alt çizgi okunabilirlik içindir: 1000000
```

İşlem önceliği okulda öğrendiğin gibidir: önce `**`, sonra `*` `/` `//` `%`, en son `+` `-`. Şüphedeysen parantez koy; okunabilirlik için de iyidir.

`//` ve `%` ikilisi her yerde karşına çıkar: saniyeyi dakikaya çevirmek, bir sayının çift olup olmadığına bakmak (`n % 2 == 0`), bir listeyi sayfalara bölmek.

> [!DERİN]
> Python'da `int` sabit bir bit genişliğiyle sınırlı değildir; kullanılabilir bellek sınırlıdır: `2 ** 1000` 302 basamaklı bir sayıyı sorunsuz hesaplar. C ya da Java'da 64 bitlik tam sayı ~9.2 × 10¹⁸'de taşar. CPython büyük sayıları 30 bitlik "basamaklar" dizisi olarak saklar. Bu yüzden kriptografide (RSA gibi devasa sayılar) Python çok rahattır. Bedeli hızdır.

> [!TUZAK]
> Negatif sayılarda `//` **aşağı** (eksi sonsuza doğru) yuvarlar, sıfıra doğru değil: `-7 // 2` → `-4`, `-7 % 2` → `1`. Tam sayılarda ve `b != 0` iken `(a // b) * b + (a % b) == a` eşitliği korunur. Float yuvarlaması ayrıca değerlendirilir.
:::

::: tahmin
Çıktı tek satır:

```python
print(7 / 2, 7 // 2, 7 % 2, 2 ** 3, -7 // 2)
```

???

`3.5 3 1 8 -4`. Son değer tuzağın kendisi: `-3.5` aşağı yuvarlanınca `-4` olur.
:::

::: anlat Kayan nokta ve sayı tabanları
Ondalıklı sayılar bilgisayarda **ikilik tabanda yaklaşık** olarak saklanır. `0.1` ikilik tabanda tam ifade edilemez, tıpkı `1/3`'ün onluk tabanda `0.3333...` olması gibi. Sonuç:

```python
print(0.1 + 0.2)              #! 0.30000000000000004
print(0.1 + 0.2 == 0.3)       #! False!
print(round(0.1 + 0.2, 2))    #! 0.3 — yuvarlayarak karşılaştır
print(abs(-5), min(3, 9), max(3, 9))
print(divmod(17, 5))          #! (3, 2): tam bölüm ve kalan birlikte
```

Para hesabında float kullanma: kuruşları int olarak tut ya da `decimal` modülünü kullan (P35).

**Artırılmış atama** kısayolları: `x += 1` aslında `x = x + 1` demektir. `-=`, `*=`, `//=`, `%=`, `**=` de vardır.

### Onaltılık ve ikilik: güvenlikçinin günlük dili
Bellek adresleri, renk kodları, hash'ler ve paket baytları hep onaltılık (hex) yazılır. Python bunları doğrudan anlar:

```python
print(0xff, 0b1010, 0o17)     #! 255 10 15 — hex, ikilik, sekizlik yazım
print(hex(255), bin(10))      #! '0xff' '0b1010' — sayıdan metne
print(int("ff", 16))          #! 255 — metinden sayıya, taban 16
print(int("1010", 2))         #! 10
```

Tam sayıların bitleri üzerinde doğrudan çalışan **bit işleçleri** de vardır: `&` (bit-VE), `|` (bit-VEYA), `^` (bit-XOR: farklıysa 1), `~` (bit-DEĞİL: `~x == -(x + 1)`), `<<` (sola kaydır: her adım 2 ile çarpar) ve `>>` (sağa kaydır: her adım 2'ye tam böler). Örneğin `0b1010 & 0b1100` → `8` (`0b1000`), `1 << 3` → `8`.

> [!GÜVENLİK]
> `0xff` = 255 = `0b11111111`: bir baytın alabileceği en büyük değer. IP adresinin her parçası, renk kanallarının her biri ve paket başlıklarındaki çoğu alan bir bayttır. Onaltılık ile ikilik arasında kafandan geçiş yapabilmek ağ ve tersine mühendislik işinde sürekli lazım: her hex basamak tam 4 bit eder.
:::

::: tahmin
İki satır yazar:

```python
print(0.1 + 0.2 == 0.3)
print(round(0.1 + 0.2, 2) == 0.3)
```

???

`False`, sonra `True`. İkilik tabanda yaklaşık saklama yüzünden toplam `0.30000000000000004` olur. Yuvarladıktan sonra eşitlik tutar. Gerçek kodda `math.isclose(a, b)` kullanılır.
:::

::: gorev Saniye çözücü
`toplam` saniyeyi saat, dakika ve saniyeye ayır ve tek satırda boşlukla ayırarak yazdır. `//` ve `%` kullan. Kodun **her** `toplam` değerinde çalışmalı; testler sayıyı değiştirip tekrar deneyecek.

`toplam = 3725` için:

```cikti
1 2 5
```

```starter
# Kusurlu başlangıç: çıktıyı ve kullanılan işlemi görevle karşılaştır.
toplam = 3725
saat = toplam / 3600
dakika = toplam // 60
saniye = toplam % 60
print(saat, dakika, saniye)
```

```test
eq(out, "1 2 5\n", "3725 saniye → 1 2 5")
eq(run_code(src.replace("3725", "86399")), "23 59 59\n", "86399 saniye → 23 59 59")
eq(run_code(src.replace("3725", "61")), "0 1 1\n", "61 saniye → 0 1 1")
for deger, beklenen in [(0, "0 0 0"), (59, "0 0 59"), (60, "0 1 0"), (3599, "0 59 59"), (3600, "1 0 0"), (3660, "1 1 0")]:
    eq(run_code(src.replace("3725", str(deger))).strip(), beklenen, "tam bölüm/kalan sınırı " + str(deger))
ok("//" in src and "%" in src, "// ve % işleçlerini kullan")
```

```solution
toplam = 3725
saat = toplam // 3600
dakika = toplam % 3600 // 60
saniye = toplam % 60
print(saat, dakika, saniye)
```

```hint
Bir saatte 3600 saniye var. `toplam // 3600` saati verir.
```

```hint
Saatten artan kısım `toplam % 3600`. Onu 60'a tam bölünce dakika çıkar.
```
:::

::: gorev Arşiv aktarımı
Bir log arşivi `4.2` GiB. 1 GiB = 1024 MiB. Hat hızı saniyede `25` MiB. Aktarım kaç saniye sürer? Sonucu `round(..., 1)` ile 1 ondalığa yuvarlayıp yazdır.

```cikti
172.0
```

```starter
# Kusurlu başlangıç: çıktıyı ve kullanılan işlemi görevle karşılaştır.
boyut_gb = 4.2
hiz_mb_s = 25
sure = boyut_gb / hiz_mb_s
print(round(sure, 1))
```

```test
eq(out.strip(), "172.0", "Sonuç 172.0 olmalı")
eq(run_code(src.replace("4.2", "1").replace("25", "8")).strip(), "128.0", "1 GiB ve 8 MiB/s ile 128.0")
eq(run_code(src.replace("4.2", "1").replace("25", "3")).strip(), "341.3", "1 GiB / 3 MiB/s bir ondalıkla")
ok(calls("round"), "round() kullan")
```

```solution
boyut_gb = 4.2
hiz_mb_s = 25
sure = boyut_gb * 1024 / hiz_mb_s
print(round(sure, 1))
```

```hint
Önce GiB'ı MiB'a çevir (`* 1024`), sonra hıza böl.
```
:::

::: gorev Taban çevirici
Şu üç satırı **fonksiyonlarla hesaplayarak** yazdır. Hazır metin yazma, sırasıyla `hex()`, `bin()` ve `int(..., 16)` kullan:

```cikti
0xff
0b1010
255
```

- 1. satır: `255` sayısının onaltılık hali
- 2. satır: `10` sayısının ikilik hali
- 3. satır: `"ff"` metninin onluk değeri

```starter
# Kusurlu başlangıç: çıktıyı ve kullanılan işlemi görevle karşılaştır.
print(hex(255))
print(bin(10))
print("ff")
```

```test
import ast
eq(lines, ["0xff", "0b1010", "255"], "Satırlar: 0xff, 0b1010, 255")
ok(calls("hex") and calls("bin") and calls("int"), "hex(), bin() ve int() kullan")
int_16 = any(
    isinstance(n, ast.Call)
    and isinstance(n.func, ast.Name)
    and n.func.id == "int"
    and len(n.args) == 2
    and isinstance(n.args[1], ast.Constant)
    and n.args[1].value == 16
    for n in ast.walk(tree)
)
ok(int_16, "Üçüncü satırda int(..., 16) ile 16 tabanından çevir")
ok('"0xff"' not in src and "'0xff'" not in src and '"0b1010"' not in src and "'0b1010'" not in src,
   "Çıktıları hazır metin olarak yazma — hex() ve bin() ile hesapla")
```

```solution
print(hex(255))
print(bin(10))
print(int("ff", 16))
```

```hint
`int()` ikinci argüman olarak tabanı alır: `int("ff", 16)`.
```
:::

::: anlat İşaret, üs ve yuvarlama sınırı
Üs alma tekli eksiden önce değerlendirilir. `-2 ** 2` sonucu `-4`, `(-2) ** 2` sonucu `4` olur. `round()` tam ortadaki değeri en yakın çift sonuca yuvarlar; `round(2.5)` `2`, `round(3.5)` `4` verir. Float gösterimindeki yaklaşık değer de sonucu etkileyebilir. GB/MB ondalık birimlerdir; aktarım görevindeki ikilik çarpan GiB/MiB birimleriyle verilmiştir.
:::

::: anlat Yaygın yanlışlar
| Yanlış yaklaşım | Neden kırılır? | Doğrusu |
|---|---|---|
| Süre hesabında `/` ile tam bölüm beklemek | Bölme float sonuç verir. | Saat ve dakika parçalarında `//`, kalan için `%` kullan. |
| GB ile GiB birimini aynı saymak | Ondalık ve ikilik birimler farklıdır. | Bu görevde 1 GiB = 1024 MiB kabulünü izle. |
| `0.1 + 0.2 == 0.3` beklemek | Bazı ondalıklar ikilikte yaklaşık saklanır. | Görevde istenen basamağa yuvarla; sayısal karşılaştırmada toleransı belirle. |
:::

::: anlat AI derslerinde nerede?
- `ai-savunma-31` — Token maliyetleri sayıları çarpıp toplayarak hesaplanır.
- `ai-guvence-43` — TIES kırpmasında boyut ile yoğunluk çarpılır ve tam sayıya çevrilir.

Bu bağlantılardaki sözlük, fonksiyon ve model ayrıntıları ileride öğrenilecek. Burada yalnız bu derste gördüğün Python parçasını tanıman yeterli.
:::
