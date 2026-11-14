---
id: p09
title: while Döngüsü
summary: Koşul doğru oldukça tekrarla; sayaçlar, sonsuz döngü, break ve continue.
kazanim: PCEP 2.2
---

::: anlat Koşul doğru oldukça
`while`, koşulu her turun **başında** sınar ve doğru oldukça bloğu tekrarlar:

```python
sayac = 1
while sayac <= 5:            #! her turun başında sınanır
    print("tur", sayac)
    sayac += 1               #! bunu unutursan döngü sonsuza gider
print("çıktım, sayac =", sayac)
```

Röntgen'de izle: `sayac` her turda sarıya döner ve koşul yanlış olduğu an (`sayac = 6`) akış döngünün altına atlar.

Her `while` döngüsünün üç parçası vardır:
1. **Başlangıç**: döngüden önce değişkeni hazırla (`sayac = 1`)
2. **Koşul**: ne zaman devam edileceği (`sayac <= 5`)
3. **İlerleme**: koşulu bir gün yanlış yapacak değişiklik (`sayac += 1`)

Koşul başka bir olayla değişmiyorsa ilerlemenin eksikliği **sonsuz döngü** oluşturabilir. Tezgah programı birkaç saniye sonra durdurur ve "zaman aşımı" der. Gerçek bir terminalde `Ctrl+C` ile kesersin.

> [!NOT]
> Ne zaman `while`, ne zaman `for`? Kaç kez döneceğini **biliyorsan** (bir listenin elemanları, 1'den 10'a) `for` (P10). **Bir şey olana kadar** dönüyorsan (kullanıcı "çık" yazana kadar, bağlantı kurulana kadar, sayı 1'e inene kadar) `while`.
:::

::: tahmin
Ne yazdırır?

```python
n = 1
while n < 100:
    n *= 3
print(n)
```

???

`243`. n sırayla 1 → 3 → 9 → 27 → 81 → 243 olur. 81 hâlâ 100'den küçük olduğu için bir tur daha döner ve 243 olur. Koşul turun **başında** sınandığı için son değer sınırı aşabilir. "Sınırı aşan ilk değer" kalıbı budur.
:::

::: anlat break, continue ve while True
- `break`: döngüden **hemen çık**.
- `continue`: bu turun geri kalanını atla, **sonraki tura** geç.

En yaygın kalıp **`while True` + `break`**'tir: "çıkış koşulu sağlanana kadar dön":

```python norun
while True:
    komut = input("> ")
    if komut == "cik":
        break                    #! döngüyü bitir
    if komut == "":
        continue                 #! boş satırı yok say, başa dön
    print("komut:", komut)
print("görüşürüz")
```

Bu örneği tezgaha al ve Girdi kutusuna şunları alt alta yaz: `ls`, boş satır, `pwd`, `cik`. Çıktıda boş satırın atlandığını göreceksin.

> [!TUZAK]
> Girdi kutusunda `cik` satırı yoksa döngü girdisi bitince `input()` `EOFError` verir. Terminalde yeni satır beklenir; giriş akışı kapatılırsa orada da EOFError oluşabilir. Çıkış yolunu her zaman düşün.

> [!DERİN]
> `while` koşulu her turda yeniden değerlendirilir; Bytecode sekmesinde döngünün sonunda başa dönen bir **atlama** (`JUMP_BACKWARD`) ve koşul yanlışsa döngünün dışına atlayan `POP_JUMP_IF_FALSE` göreceksin. Bütün döngüler, hatta `for`, makine düzeyinde koşullu atlamalardan ibarettir.
:::

::: tahmin
Çıktı tek satır:

```python
i = 0
while True:
    i += 1
    if i % 2 == 0:
        continue
    if i > 7:
        break
    print(i, end=" ")
```

???

`1 3 5 7 ` (her sayının sonunda `end=" "` boşluğuyla). Çift sayılarda `continue` turu atlar (`print`'e gelmez). `i = 9` olduğunda tek olduğu için `continue`'dan geçer ama `i > 7` olduğundan `break` döngüyü bitirir.
:::

::: gorev Geri sayım
Girdiden bir n sayısı oku. `while` ile n'den 1'e kadar her sayıyı ayrı satıra yazdır, en sonda `Ateş!` yaz.

```cikti
3
2
1
Ateş!
```

```starter
# Kusurlu başlangıç: görevdeki koşul ve çıktıyla karşılaştır.
n = int(input())
while n > 1:
    print(n)
    n -= 1
print("Ateş!")
```

```stdin
3
```

```test
eq(run("3").strip().splitlines(), ["3", "2", "1", "Ateş!"], "3 → 3, 2, 1, Ateş!")
eq(run("1").strip().splitlines(), ["1", "Ateş!"], "1 → 1, Ateş!")
eq(run("0").strip().splitlines(), ["Ateş!"], "0 → sadece Ateş!")
ok(uses("while"), "while kullan")
```

```solution
n = int(input())
while n >= 1:
    print(n)
    n -= 1
print("Ateş!")
```

```hint
Koşul `n >= 1`, ilerleme `n -= 1`.
```
:::

::: gorev Collatz adımları
Bir n sayısıyla başla: çiftse ikiye böl, tekse `3n + 1` yap. 1'e ulaşana kadar tekrarla. Girdiden pozitif bir tam sayı olan n'yi oku ve **kaç adımda** 1'e ulaştığını yazdır. Bu görevde 0 veya negatif girdi verilmeyecek.

6 → 3 → 10 → 5 → 16 → 8 → 4 → 2 → 1 : **8 adım**

```starter
# Kusurlu başlangıç: görevdeki koşul ve çıktıyla karşılaştır.
n = int(input())
adim = 0
while n != 1:
    if n % 2 == 0:
        n //= 2
    else:
        n = 3 * n + 1
print(adim)
```

```stdin
6
```

```test
eq(run("6").strip(), "8", "6 → 8 adım")
eq(run("1").strip(), "0", "1 → 0 adım")
eq(run("27").strip(), "111", "27 → 111 adım")
eq(run("2").strip(), "1", "2 → 1 adım")
eq(run("18014398509481985").strip(), "411", "büyük tam sayıda hassasiyet korunmalı")
```

```solution
n = int(input())
adim = 0
while n != 1:
    if n % 2 == 0:
        n = n // 2
    else:
        n = 3 * n + 1
    adim += 1
print(adim)
```

```hint
Döngü koşulu `n != 1`. Çift kontrolü: `n % 2 == 0`. Bölmede `//` kullan ki n tam sayı kalsın.
```

```hint
Collatz sanısı: her pozitif tam sayının sonunda 1'e ulaştığı düşünülüyor ama bu hâlâ **kanıtlanamadı**. 27 gibi küçük bir sayı bile 9232'ye kadar çıkıyor.
```
:::

::: anlat while döngüsünün else kolu
Bir `while` döngüsünün altına, **`while` ile aynı girinti hizasında** `else:` yazabilirsin. Döngü koşulu yanlış olup normal yoldan biterse `else` bloğu çalışır; döngüden `break` ile erken çıkılırsa `else` bloğu **atlanır**:

```python
hak = 2
while hak > 0:
    hak -= 1
    if hak == 99:          #! hiç tutmaz, break çalışmaz
        break
else:
    print("haklar bitti")  #! break çalışmadığı için burası çalışır
```

Üç yanlış girişten sonra kilit mesajı basmak için bu ayrım birebirdir.
:::

::: gorev Hesap kilidi
Girdiden parolaları satır satır oku. Doğru parola `kapı`.

- Doğru parola gelirse `Giriş başarılı (N. deneme)` yaz ve dur.
- **3 yanlış** denemeden sonra `Hesap kilitlendi` yaz ve dur. Dördüncü satırı **okuma**.

```starter
# Kusurlu başlangıç: görevdeki koşul ve çıktıyla karşılaştır.
deneme = 0
while deneme < 3:
    parola = input()
    deneme += 1
    if parola == "kapı":
        print(f"Giriş başarılı ({deneme}. deneme)")
        break
print("Hesap kilitlendi")
```

```stdin
asd
123
kapı
```

```test
eq(run("asd\n123\nkapı").strip(), "Giriş başarılı (3. deneme)", "3. denemede doğru")
eq(run("kapı").strip(), "Giriş başarılı (1. deneme)", "ilk denemede doğru")
eq(run("yanlis\nkapı").strip(), "Giriş başarılı (2. deneme)", "ikinci denemede doğru")
eq(run("a\nb\nc\nkapı").strip(), "Hesap kilitlendi", "3 yanlıştan sonra kilit (4. satır okunmaz)")
eq(run("a\nb\nc").strip(), "Hesap kilitlendi", "3 yanlış → kilit")
```

```solution
deneme = 0
while deneme < 3:
    parola = input()
    deneme += 1
    if parola == "kapı":
        print(f"Giriş başarılı ({deneme}. deneme)")
        break
else:
    print("Hesap kilitlendi")
```

```hint
Döngü koşulu deneme sayısını sınırlasın: `while deneme < 3:`
```

```hint
Döngü bittiğinde başarılı mı oldu, kilitlendi mi? Bir bayrak değişkeni (`basarili = False`) tutabilirsin. Ya da bu derste açıklanan `while ... else` yapısını kullan.
```
:::

::: anlat Yaygın yanlışlar
| Yanlış yaklaşım | Neden kırılır? | Doğrusu |
|---|---|---|
| Sayacı güncellememek | Koşul hiç değişmeyebilir. | Her gerekli yolda ilerleme sağla. |
| continue öncesi ilerlemeyi atlamak | Aynı durum tekrar edebilir. | Atlanan satırları kontrol et. |
| Kilit mesajını koşulsuz yazmak | Başarılı girişte de kilit görünür. | while ... else kullan; break else kolunu atlar. |
:::

::: anlat AI derslerinde nerede?
- `ai-uretim-02` — Tokenizasyon imleci while döngüsüyle ilerler.
- `ai-temel-01` — BPE örneği birleştirme kalmayınca break ile çıkar.

Bu örneklerin fonksiyon ve model ayrıntıları ileride öğrenilecek; burada tanıdığın Python işlemini izlemen yeterli.
:::
