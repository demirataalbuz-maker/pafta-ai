---
id: p06
title: Girdi ve Tür Dönüşümü
summary: input() her zaman metin döndürür; int, float, str ile türler arası geçiş.
kazanim: PCEP 1.4, PCEP 1.5
---

::: anlat input(): kullanıcıdan bir satır
`input()` programı durdurur, kullanıcının bir satır yazıp Enter'a basmasını bekler ve yazılanı **metin olarak** döndürür.

```python norun
ad = input("Adın: ")          #! parantez içindeki metin soru olarak gösterilir
print(f"Merhaba {ad}")
```

Tezgahta klavyeden canlı girdi yok. Onun yerine alttaki **Girdi ▸** kutusuna satırları önceden yazarsın; her `input()` çağrısı sıradaki satırı alır. Çıktıda girdi, terminaldeki gibi sarı görünür. Bu örneği tezgaha al, Girdi kutusuna adını yaz ve çalıştır.

> [!NOT]
> Görevlerde testler programına kendi girdilerini verir. Soru metni (`input("Sayı: ")`) test çıktısına karışmaz, rahatça kullanabilirsin.

### Altın kural: input() daima str döndürür
Kullanıcı `42` yazsa bile gelen şey `"42"` metnidir. Sayı gibi kullanmak istiyorsan **dönüştürmelisin**:

```python
a = "3"
b = "4"
print(a + b)              #! '34' — metin birleştirme!
print(int(a) + int(b))    #! 7 — önce sayıya çevir
print(float("2.5") * 2)   #! 5.0
print(str(80) + "/tcp")   #! sayıyı metne çevirip birleştir
```

| Dönüşüm | Örnek | Sonuç |
|---|---|---|
| `int(x)` | `int("42")`, `int(3.99)` | `42`, `3` (kırpar, yuvarlamaz) |
| `float(x)` | `float("1e3")` | `1000.0` |
| `str(x)` | `str(443)` | `"443"` |
| `int(x, taban)` | `int("ff", 16)` | `255` |
:::

::: tahmin
Girdi kutusunda iki satır var: `3` ve `4`. Çıktı ne olur?

```python
a = input()
b = input()
print(a + b)
print(int(a) + int(b))
```

```stdin
3
4
```

???

`34`, sonra `7`. Gelen ikisi de metindir; `+` metinleri birleştirir. Sayıya çevrilince gerçek toplama yapılır. Bu, yeni başlayanların bir numaralı hatasıdır.
:::

::: anlat Dönüşüm patladığında: ValueError
Her metin sayıya çevrilemez. `int("abc")` ya da `int("3.5")` → `ValueError`. Bir sayıyı metne eklemeye çalışmak ise `TypeError` verir:

```python norun
print(int("3.5"))          #! ValueError: int() ondalıklı metni kabul etmez
print("port: " + 80)       #! TypeError: str ile int toplanamaz
```

Çözümler:

```python
print(int(float("3.5")))   #! önce float, sonra int → 3
print("port: " + str(80))  #! açık dönüşüm
print(f"port: {80}")       #! ya da f-string, dönüşümü kendisi yapar
print(int("  42  "))       #! kenar boşluklarını int() kendisi tolere eder
```

Kullanıcı girdisinin hatalı gelme ihtimalini `try/except` ile yönetmeyi P25'te öğreneceksin. O zamana kadar girdinin düzgün olduğunu varsay.

> [!GÜVENLİK]
> **Kullanıcı girdisine asla güvenme**, güvenliğin birinci kuralıdır. Python 2'de `input()` girilen metni **kod olarak çalıştırırdı**: kullanıcı `__import__('os').system('...')` yazsa komut çalışırdı. Python 3 bunu düzeltti, `input()` artık sadece metin döndürür. Aynı hatayı `eval(input())` yazarak sen geri getirme. `eval` alınan metni kod olarak yürütür; P54'de daha güvenli alternatiflerini göreceğiz.
:::

::: tahmin
Çıktı tek satır:

```python
print(int("42") + 1, str(42) + "1", int(3.99), float("1e3"))
```

???

`43 421 3 1000.0`. `int(3.99)` yuvarlamaz, ondalığı **atar** (sıfıra doğru kırpar). Yuvarlamak istersen `round(3.99)` → `4`. `"1e3"` bilimsel gösterimdir: 1 × 10³.
:::

::: gorev İki sayı topla
Girdiden iki tam sayı oku (her biri ayrı satırda) ve toplamlarını yazdır.

```starter
a = input()
b = input()
print(a + b)
```

```stdin
3
4
```

```test
eq(run("3\n4").strip(), "7", "3 ve 4 → 7")
eq(run("-10\n25").strip(), "15", "-10 ve 25 → 15")
eq(run("1000000\n1").strip(), "1000001", "1000000 ve 1 → 1000001")
```

```solution
a = int(input())
b = int(input())
print(a + b)
```

```hint
`input()` metin döndürür. `int(input())` doğrudan sayı okur.
```
:::

::: gorev Saat biçimi
Girdiden bir saniye sayısı oku ve `SS:DD:ss` biçiminde, her alanı **2 haneye sıfırla tamamlayarak** yazdır.

```cikti
01:02:05
```

```starter
# Kusurlu başlangıç: çıktıyı ve kullanılan işlemi görevle karşılaştır.
toplam = int(input())
s = toplam // 3600
d = toplam // 60
sn = toplam % 60
print(f"{s:02d}:{d:02d}:{sn:02d}")
```

```stdin
3725
```

```test
eq(run("3725").strip(), "01:02:05", "3725 → 01:02:05")
eq(run("59").strip(), "00:00:59", "59 → 00:00:59")
for deger, beklenen in [(0, "00:00:00"), (60, "00:01:00"), (3599, "00:59:59"), (3600, "01:00:00"), (3660, "01:01:00")]:
    eq(run(str(deger)).strip(), beklenen, "saat sınırı " + str(deger))
eq(run("86399").strip(), "23:59:59", "86399 → 23:59:59")
```

```solution
toplam = int(input())
s = toplam // 3600
d = toplam % 3600 // 60
sn = toplam % 60
print(f"{s:02d}:{d:02d}:{sn:02d}")
```

```hint
P03'teki saniye çözücüyü hatırla. Biçim için f-string'de `:02d` kullan.
```
:::

::: gorev Üç ölçümün ortalaması
Üç ondalıklı sayı oku (ayrı satırlarda) ve ortalamalarını **2 ondalıkla** yazdır.

```cikti
1.67
```

```starter
# Kusurlu başlangıç: çıktıyı ve kullanılan işlemi görevle karşılaştır.
a = float(input())
b = float(input())
c = float(input())
print(f"{a + b + c / 3:.2f}")
```

```stdin
1
2
2
```

```test
eq(run("1\n2\n2").strip(), "1.67", "1, 2, 2 → 1.67")
eq(run("10\n20\n30.5").strip(), "20.17", "10, 20, 30.5 → 20.17")
eq(run("0\n0\n0").strip(), "0.00", "0, 0, 0 → 0.00")
eq(run("1.5\n2.5\n3.5").strip(), "2.50", "üç ölçüm de ondalıklı olabilir")
eq(run("-1.5\n0.5\n1").strip(), "0.00", "işaretli ölçümler")
```

```solution
a = float(input())
b = float(input())
c = float(input())
print(f"{(a + b + c) / 3:.2f}")
```

```hint
`float(input())` ile oku; biçim için `:.2f`.
```
:::

::: anlat Yaygın yanlışlar
| Yanlış yaklaşım | Neden kırılır? | Doğrusu |
|---|---|---|
| İki input sonucunu doğrudan toplamak | `"3" + "4"` metin birleştirir. | Toplamadan önce `int()` ile dönüştür. |
| `int("3.5")` kullanmak | Bu metin tam sayı gösterimi değildir. | Ondalık gerekiyorsa `float()` kullan. |
| Ortalama için yalnız son ölçümü bölmek | Bölme toplamalardan önce yapılır. | `(a + b + c) / 3` yaz. |
:::

::: anlat AI derslerinde nerede?
- `ai-savunma-09` — PII ve kart/IP denetiminde metin içindeki rakam ve oktet parçaları `int(...)` ile tam sayıya çevrilir.
- `ai-guvence-43` — TIES model birleştirmesinde seçilen ağırlıklar `float(...)`, korunacak koordinat sayısı `int(...)` ile dönüştürülür.

Bu bağlantılardaki sözlük, fonksiyon ve model ayrıntıları ileride öğrenilecek. Burada yalnız bu derste gördüğün Python parçasını tanıman yeterli.
:::
