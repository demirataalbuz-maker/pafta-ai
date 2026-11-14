---
id: p02
title: Değişkenler ve İsimler
summary: Atama bir kutuya koymak değil, bir nesneye etiket yapıştırmaktır.
kazanim: PCEP 1.3
---

::: anlat İsim = etiket
Bir değeri sonra kullanmak için ona **isim** verirsin. Bu işleme **atama** denir ve `=` ile yapılır:

```python
hedef = "10.0.0.5"        #! sağdaki değer oluşur, soldaki isim ona bağlanır
port = 443
print(hedef, port)
port = 8443               #! aynı isim artık başka bir nesneyi gösteriyor
print(hedef, port)
```

`=` matematikteki "eşittir" değildir. "**Sağdakini hesapla, soldaki ismi ona bağla**" demektir. Bu yüzden `sayac = sayac + 1` mantıklı bir satırdır: önce sağ taraf hesaplanır, sonra isim yeni sonuca bağlanır.

Çoğu kitap değişkeni "içine değer konan kutu" diye anlatır. Python için daha doğru bir model var: **değişken, nesneye yapıştırılmış bir etikettir.** Nesne bir yerde durur, isim sadece onu gösterir. Aynı nesneye birden fazla etiket yapıştırılabilir.

Bu modeli gözünle gör: tezgahta **◎ Röntgen**'e bas, sonra `▶` ile adım adım ilerle. Her satırda hangi ismin hangi değeri gösterdiğini ve hangi ismin yeni değiştiğini (sarı) göreceksin.

### İsim kuralları
- Harf, rakam ve alt çizgi `_` kullanılabilir. Rakamla **başlayamaz**: `2hedef` olmaz, `hedef2` olur.
- Boşluk ve tire olmaz: `port no` ve `port-no` geçersiz, `port_no` geçerli.
- Büyük-küçük harf farklıdır: `Port` ile `port` iki ayrı isimdir.
- `if`, `for`, `class` gibi **anahtar kelimeler** isim olamaz.
- Python geleneği: değişken adları `kucuk_harf_alt_cizgi` (snake_case) yazılır. Bu bir yazım geleneğidir; Python farklı bir geçerli ismi de kabul eder.

> [!NOT]
> Türkçe karakterler (`ş`, `ğ`, `ı`) isimlerde **çalışır**, Python 3 Unicode isimlere izin verir. Ama ekip projelerinde ve açık kaynakta İngilizce/ASCII isimler standarttır. Bu paftalarda Türkçe ama ASCII isimler kullanıyoruz: `sayac`, `kullanici`.
:::

::: tahmin
Son satır ne yazdırır?

```python
x = 5
y = x
x = 10
print(y)
```

???

**5** yazar. `y = x` satırı "y de x'in gösterdiği nesneyi göstersin" demektir. O an x `5`'i gösteriyordu, yani y de `5`'e bağlandı. Sonra `x = 10` sadece **x etiketini** yeni bir nesneye taşır; y'ye dokunmaz.

Bunu Röntgen'de izle: üçüncü satırdan sonra x ve y farklı renkli karelerle görünür, yani artık farklı nesneleri gösterirler.
:::

::: anlat Türü olan nesnedir, isim değil
Python **dinamik tiplidir**: bir isim önce sayıyı, sonra metni gösterebilir. Tür bilgisi **nesnenin** üzerindedir, ismin değil. `type()` bir nesnenin türünü, `id()` ise kimliğini (nesnenin ömrü boyunca sabit ve aynı anda yaşayan nesnelerde benzersiz bir tam sayıyı) söyler.

```python
deger = 42
print(type(deger))        #! <class 'int'>
deger = "kırk iki"
print(type(deger))        #! <class 'str'> — aynı isim, başka nesne
a = b = 0                 #! zincir atama: ikisi de aynı 0'ı gösterir
x, y = 3, 4               #! çoklu atama: sırayla eşleşir
print(a, b, x, y)
```

Çoklu atamanın güzel bir hilesi var: iki değişkenin değerini **geçici değişken olmadan** takas etmek.

```python
sol, sag = "kırmızı", "mavi"
sol, sag = sag, sol       #! sağ taraf önce tamamen hesaplanır, sonra dağıtılır
print(sol, sag)
```

> [!DERİN]
> İsimler aslında bir **sözlükte** tutulur. Modül düzeyindeki isimler `globals()` sözlüğündedir: `x = 5` yazmak kabaca `globals()["x"] = 5` demektir. Python bir ismi gördüğünde bu sözlüklere bakar ve bulamazsa `NameError` verir. Bu bilgi P22'de (kapsam) ve P63'da (nitelik erişimi) her şeyi açıklayacak.
:::

::: tahmin
Çıktı ne olur?

```python
a, b = 1, 2
a, b = b, a + b
a, b = b, a + b
print(a, b)
```

???

Sağ taraf **eski** değerlerle hesaplanır, sonra atanır:

- Başta: a=1, b=2
- 1. takas: a = 2, b = 1+2 = 3
- 2. takas: a = 3, b = 2+3 = 5

Çıktı `3 5`. Bu kalıp Fibonacci dizisinin kalbidir. Döngüleri öğrenince onu sonsuza kadar sürdüreceksin.
:::

::: gorev Takas
`sol` ile `sag` değişkenlerinin değerlerini takas et, sonra ikisini yazdır. Metinleri yeniden **elle yazmak yok**: `"mavi"` ve `"kırmızı"` kodda yalnızca bir kez geçmeli.

```cikti
mavi kırmızı
```

```starter
# Kusurlu başlangıç: sırayla atama yapınca eski sol değeri kaybolur.
sol = "kırmızı"
sag = "mavi"
sol = sag
sag = sol

print(sol, sag)
```

```test
import re
eq(sol, "mavi", "sol artık 'mavi' olmalı")
eq(sag, "kırmızı", "sag artık 'kırmızı' olmalı")
eq(out, "mavi kırmızı\n", "Çıktı: mavi kırmızı")
ok(bool(re.search(r'^\s*sol\s*=\s*["\']kırmızı["\']', src, re.M)) and bool(re.search(r'^\s*sag\s*=\s*["\']mavi["\']', src, re.M)),
   "İlk iki satırdaki başlangıç atamalarını koru, sonrasında takas yap")
ok(src.count('"mavi"') + src.count("'mavi'") == 1 and src.count('"kırmızı"') + src.count("'kırmızı'") == 1,
   "Metinleri yeniden yazmadan takas et")
```

```solution
sol = "kırmızı"
sag = "mavi"
sol, sag = sag, sol

print(sol, sag)
```

```hint
Çoklu atama sağ tarafı önce hesaplar: `a, b = b, a`
```
:::

::: gorev Hedef kartı
Üç değişken tanımla: `hedef` → `"10.0.0.5"`, `port` → `443` (sayı, tırnaksız), `servis` → `"https"`. Sonra **değişkenleri kullanarak** tek bir `print` ile şunu yazdır:

```cikti
10.0.0.5:443 (https)
```

```starter
# Kusurlu başlangıç: çıktıyı ve kullanılan işlemi görevle karşılaştır.
hedef = "10.0.0.5"
port = "443"
servis = "https"
print(hedef, ":", port, " (", servis, ")")
```

```test
eq(hedef, "10.0.0.5", "hedef = '10.0.0.5'")
eq(port, 443, "port = 443")
ok(type(port) is int, "port bir sayı (int) olmalı, metin değil", got=type(port).__name__)
eq(servis, "https", "servis = 'https'")
eq(out, "10.0.0.5:443 (https)\n", "Çıktı: 10.0.0.5:443 (https)")
ok("10.0.0.5:443" not in src, "Çıktıyı hazır metin olarak yazma — değişkenlerden üret")
```

```solution
hedef = "10.0.0.5"
port = 443
servis = "https"
print(hedef, ":", port, " (", servis, ")", sep="")
```

```hint
`print(hedef, ":", port, sep="")` arada boşluk bırakmadan birleştirir. Parantezleri ve boşluğu da ayrı parçalar olarak ver.
```
:::

::: gorev İsimleri tamir et
Bu kod çalışmıyor çünkü üç isim de kurallara aykırı. İsimleri sırasıyla `hedef2`, `port_no` ve `sinif` olarak düzelt; değerlere dokunma.

```starter
2hedef = "web01"
port-no = 80
class = "A"
print(2hedef, port-no, class)
```

```test
eq(kullanici.get("hedef2"), "web01", "hedef2 = 'web01'")
eq(kullanici.get("port_no"), 80, "port_no = 80")
eq(kullanici.get("sinif"), "A", "sinif = 'A'")
eq(out, "web01 80 A\n", "Çıktı: web01 80 A")
```

```solution
hedef2 = "web01"
port_no = 80
sinif = "A"
print(hedef2, port_no, sinif)
```

```hint
Önce bir kez çalıştır ve hata kartını oku: hangi satırı işaretliyor?
```

```hint
Rakamla başlamak, tire ve anahtar kelime yasak. `print` satırını da düzeltmeyi unutma.
```
:::

::: anlat Yaygın yanlışlar
| Yanlış yaklaşım | Neden kırılır? | Doğrusu |
|---|---|---|
| Takas için önce `sol = sag` yapmak | Eski sol değerini kaybedersin. | Sağ tarafı birlikte hesaplayan `sol, sag = sag, sol` kullan. |
| Sayıyı `"443"` diye tutmak | Bu değer metindir. | Port sayısını `443` olarak ata. |
| `=` ile karşılaştırma beklemek | Atama ismi yeni değere bağlar. | Değeri incelemek için `print` kullan; karşılaştırma p07’de. |
:::

::: anlat AI derslerinde nerede?
- `ai-savunma-31` — Bütçe hesabında `kapasite` bir değeri adlandırır.
- `ai-guvence-43` — Birleştirmede `k`, korunacak koordinat sayısına atanır.

Bu bağlantılardaki sözlük, fonksiyon ve model ayrıntıları ileride öğrenilecek. Burada yalnız bu derste gördüğün Python parçasını tanıman yeterli.
:::
