---
id: p08
title: Koşullar · if / elif / else
summary: Program yol ayrımına gelir; girinti blokları, elif zinciri ve koşullu ifade.
kazanim: PCEP 1.2, PCEP 2.1
---

::: anlat Yol ayrımı ve girinti
`if` bir koşulu sınar; doğruysa altındaki **bloğu** çalıştırır. Blok, `if` satırının sonundaki **iki noktadan** (`:`) sonra başlayan girintili satırlardır. Bu derslerde standart olarak 4 boşluk kullanıyoruz; aynı blokta girinti tutarlı olmalıdır.

```python
port = 22
if port == 22:                   #! iki nokta: blok başlıyor
    print("SSH portu")           #! 4 boşluk içeride = bloğun içinde
    print("anahtar tabanlı giriş önerilir")
print("kontrol bitti")           #! girinti geri geldi = blok bitti
```

Python'da girinti **süs değildir, sözdizimidir.** Başka dillerdeki `{ }` parantezlerinin işini girinti görür. Tezgah `:` yazıp Enter'a bastığında otomatik 4 boşluk açar.

### else ve elif
```python
puan = 75
if puan >= 90:
    print("A")
elif puan >= 70:                 #! önceki koşullar yanlışsa bu denenir
    print("B")
elif puan >= 50:
    print("C")
else:                            #! hiçbiri tutmadıysa
    print("F")
```

Zincir **yukarıdan aşağı** denenir ve **ilk doğru** olan dal çalışır; gerisine hiç bakılmaz. Bu yüzden koşulların sırası önemlidir: `puan >= 50` en üstte olsaydı 95 alan da "C" alırdı.

> [!TUZAK]
> `if puan >= 50:` ve altına `if puan >= 70:` yazmak (elif yerine), 75 puan için **iki** dalı da çalıştırır. Birbirini dışlayan durumlar için `elif` kullan.
:::

::: tahmin
Çıktı ne olur?

```python
puan = 75
if puan >= 90:
    print("A")
elif puan >= 70:
    print("B")
elif puan >= 50:
    print("C")
else:
    print("F")
print("bitti")
```

???

`B`, sonra `bitti`. 75 ilk koşulu geçemez, ikincisini geçer; sonraki `elif` (`>= 50`, o da doğru olmasına rağmen) **hiç denenmez**. Son satır bloğun dışında olduğu için her durumda çalışır.
:::

::: anlat Koşullu ifade, pass ve erken çıkış
Tek satırlık seçimler için **koşullu ifade** (ternary) vardır: `A if koşul else B`.

```python
yas = 20
durum = "yetişkin" if yas >= 18 else "reşit değil"
print(durum)

liste = []
if liste:                        #! boş liste yanlış sayılır (P07)
    print("dolu")
else:
    print("boş")

deger = None
if deger is None:                #! None kontrolü için == değil, is kullanılır
    print("değer yok")

if yas > 100:
    pass                         #! "burada şimdilik bir şey yok" — boş blok yasak
```

İç içe `if`'ler derinleşince kod okunmaz hale gelir. İç içe yazmak yerine koşulları `and` ile birleştirmeyi ya da (fonksiyonlarda) **erken çıkışı** tercih et:

```python norun
# kötü: ok biçimi (arrow code)
if kullanici:
    if kullanici_aktif:
        if yetkili:
            izin_ver()

# iyi: düz okunur
if kullanici and kullanici_aktif and yetkili:
    izin_ver()
```

Buradaki `izin_ver()` ileride P20'de kendi yazacağımız türden bir fonksiyon çağrısı örneğidir.

> [!ZEN]
> Düz olan, iç içe olandan iyidir. (*Flat is better than nested.*)
:::

::: tahmin
İki satır:

```python
x = 0
durum = "pozitif" if x > 0 else "sıfır" if x == 0 else "negatif"
print(durum)
if x:
    print("doğru")
print(x or "boş")
```

???

`sıfır`, sonra `boş`. Koşullu ifadeler zincirlenebilir (ama okunabilirliği çabuk bozar). `if x:` sıfır yanlış olduğu için atlanır. `x or "boş"` ise `0` yanlış olduğu için ikinciyi döndürür.
:::

::: gorev HTTP durum kodu
Girdiden bir HTTP durum kodu oku ve sınıfını yazdır:

| Aralık | Yazdır |
|---|---|
| 200–299 | `başarılı` |
| 300–399 | `yönlendirme` |
| 400–499 | `istemci hatası` |
| 500–599 | `sunucu hatası` |
| diğer | `geçersiz` |

```starter
# Kusurlu başlangıç: görevdeki koşul ve çıktıyla karşılaştır.
kod = int(input())
if kod >= 200:
    print("başarılı")
else:
    print("geçersiz")
```

```stdin
404
```

```test
eq(run("200").strip(), "başarılı", "200 → başarılı")
eq(run("299").strip(), "başarılı", "299 → başarılı")
eq(run("301").strip(), "yönlendirme", "301 → yönlendirme")
eq(run("404").strip(), "istemci hatası", "404 → istemci hatası")
eq(run("503").strip(), "sunucu hatası", "503 → sunucu hatası")
eq(run("99").strip(), "geçersiz", "99 → geçersiz")
eq(run("600").strip(), "geçersiz", "600 → geçersiz")
for kod, beklenen in [(199, "geçersiz"), (300, "yönlendirme"), (399, "yönlendirme"), (400, "istemci hatası"), (499, "istemci hatası"), (500, "sunucu hatası"), (599, "sunucu hatası")]:
    eq(run(str(kod)).strip(), beklenen, "HTTP aralık sınırı " + str(kod))
```

```solution
kod = int(input())
if 200 <= kod <= 299:
    print("başarılı")
elif 300 <= kod <= 399:
    print("yönlendirme")
elif 400 <= kod <= 499:
    print("istemci hatası")
elif 500 <= kod <= 599:
    print("sunucu hatası")
else:
    print("geçersiz")
```

```hint
Zincir karşılaştırma okunaklıdır: `200 <= kod <= 299`
```
:::

::: gorev Port sınıfı
Girdiden bir port numarası oku:

- 0–1023 → `sistem`
- 1024–49151 → `kayıtlı`
- 49152–65535 → `dinamik`
- başka her şey → `geçersiz`

```starter
# Kusurlu başlangıç: görevdeki koşul ve çıktıyla karşılaştır.
port = int(input())
if port <= 1023:
    print("sistem")
elif port <= 49151:
    print("kayıtlı")
else:
    print("dinamik")
```

```stdin
443
```

```test
eq(run("0").strip(), "sistem", "0 → sistem")
eq(run("443").strip(), "sistem", "443 → sistem")
eq(run("1023").strip(), "sistem", "1023 → sistem")
eq(run("1024").strip(), "kayıtlı", "1024 → kayıtlı")
eq(run("49151").strip(), "kayıtlı", "49151 → kayıtlı")
eq(run("49152").strip(), "dinamik", "49152 → dinamik")
eq(run("65535").strip(), "dinamik", "65535 → dinamik")
eq(run("65536").strip(), "geçersiz", "65536 → geçersiz")
eq(run("-1").strip(), "geçersiz", "-1 → geçersiz")
```

```solution
port = int(input())
if 0 <= port <= 1023:
    print("sistem")
elif 1024 <= port <= 49151:
    print("kayıtlı")
elif 49152 <= port <= 65535:
    print("dinamik")
else:
    print("geçersiz")
```

```hint
Sınır değerlerine dikkat: 1023 sistem, 1024 kayıtlı. Negatif sayıları unutma.
```
:::

::: gorev Güvenli giriş mesajı
İki satır oku: kullanıcı adı ve parola. Doğru bilgiler `admin` / `S3cret!`.

- İkisi de doğruysa: `Hoş geldin, admin`
- **Herhangi biri** yanlışsa: `Giriş başarısız`

> [!GÜVENLİK]
> Neden "kullanıcı bulunamadı" ve "parola yanlış" diye ayrı mesaj vermiyoruz? Çünkü ayrı mesajlar saldırgana **hangi kullanıcı adlarının var olduğunu** söyler. Buna *kullanıcı numaralandırma* (user enumeration) denir ve parola deneme saldırılarının ilk adımıdır. Doğru tasarım iki durumda da aynı mesajı vermektir.

```starter
# Kusurlu başlangıç: görevdeki koşul ve çıktıyla karşılaştır.
kullanici = input()
parola = input()
if kullanici == "admin" or parola == "S3cret!":
    print("Hoş geldin, admin")
else:
    print("Giriş başarısız")
```

```stdin
admin
S3cret!
```

```test
eq(run("admin\nS3cret!").strip(), "Hoş geldin, admin", "doğru bilgiler → Hoş geldin, admin")
eq(run("admin\nyanlis").strip(), "Giriş başarısız", "yanlış parola → Giriş başarısız")
eq(run("root\nS3cret!").strip(), "Giriş başarısız", "yanlış kullanıcı → aynı mesaj")
eq(run("Admin\nS3cret!").strip(), "Giriş başarısız", "büyük-küçük harf önemli")
```

```solution
kullanici = input()
parola = input()
if kullanici == "admin" and parola == "S3cret!":
    print("Hoş geldin, admin")
else:
    print("Giriş başarısız")
```

```hint
İki koşulu `and` ile tek `if`'te birleştir; `else` geri kalan her durumu yakalar.
```
:::

::: anlat Yaygın yanlışlar
| Yanlış yaklaşım | Neden kırılır? | Doğrusu |
|---|---|---|
| elif yerine ayrı if yazmak | Birden çok dal çalışabilir. | Tek seçim için elif zinciri kur. |
| Geniş koşulu önce yazmak | İlk doğru dal diğerlerini engeller. | Dar koşulları ve aralık sınırlarını önce düşün. |
| Girişte or kullanmak | Tek bilginin doğruluğu kabul verir. | İki eşitliği and ile bağla. |
:::

::: anlat AI derslerinde nerede?
- `ai-savunma-31` — Bütçe yetersizliğinde izin veya ret dalı seçilir.
- `ai-guvence-43` — Düşük kosinüste hizalama bayrağı eklenir.

Bu örneklerin fonksiyon ve model ayrıntıları ileride öğrenilecek; burada tanıdığın Python işlemini izlemen yeterli.
:::
