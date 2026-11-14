---
id: p05
title: Metinler II · Metotlar ve f-string
summary: strip, split, join, replace ve biçimlendirmenin kralı f-string.
kazanim: PCEP 3.4, PCAP 3.2, PCAP 3.3
---

::: anlat Metinlerin metotları
Metinler, kendilerine bağlı fonksiyonlarla gelir; bunlara **metot** denir ve nokta ile çağrılır: `metin.metot()`. Metinler değiştirilemez olduğu için metotlar orijinali **değiştirmez**, dönüş türü metoda bağlıdır. Örneğin `lower()` metin, `split()` liste, `count()` tam sayı, `startswith()` bool döndürür.

```python
s = "  Admin@Ornek.COM  "
print(s.strip())             #! baştaki/sondaki boşlukları at
print(s.lower())             #! hepsi küçük harf
print(s.upper())             #! hepsi büyük harf
print(s.strip().lower())     #! zincirleme: önce strip, sonucu lower
print(s.replace("COM", "net"))
print(s.count("m"))          #! kaç kez geçiyor
print(s.find("@"))           #! ilk geçtiği indeks, yoksa -1
print("GET /admin".startswith("GET"))
print("rapor.pdf".endswith(".pdf"))
print("2026".isdigit())      #! hepsi rakam mı?
```

| Metot | Ne yapar |
|---|---|
| `strip()` / `lstrip()` / `rstrip()` | kenar boşlukları (ya da verdiğin karakterleri) temizler |
| `lower()` / `upper()` / `title()` | harf dönüşümü |
| `replace(eski, yeni)` | tüm geçişleri değiştirir |
| `split(ayrac)` | metni parçalara böler, **liste** döndürür |
| `ayrac.join(parcalar)` | parçaları ayraçla birleştirir |
| `find(x)` / `rfind(x)` / `index(x)` | konum: `find` soldan, `rfind` sağdan arar (yoksa -1); `index` yoksa `ValueError` verir |
| `startswith` / `endswith` | baş/son kontrolü |
| `isdigit` / `isalpha` / `isalnum` / `isspace` | içerik kontrolü (`sorted("cab")` ise karakterleri sıralayıp `['a', 'b', 'c']` listesi döndürür) |

> [!TUZAK]
> `s.strip()` yazıp sonucu bir yere atamazsan hiçbir şey olmaz; `s` aynı kalır. Doğrusu: `s = s.strip()`.
:::

::: tahmin
Çıktı tek satır:

```python
s = "  Admin  "
print(s.strip().lower(), len(s))
```

???

`admin 9`. `strip().lower()` yeni bir metin üretir; `s`'in kendisi hâlâ 9 karakterlik orijinaldir (2 boşluk + 5 harf + 2 boşluk).
:::

::: anlat split ve join: metni parçala, geri birleştir
Log ayrıştırmanın yarısı `split`'tir. Ayraç vermezsen **her türlü boşluğa** göre böler ve art arda gelen boşlukları tek sayar.

```python
satir = "2026-10-19 08:15:02 FAIL root 10.0.0.7"
parcalar = satir.split()          #! ['2026-10-19', '08:15:02', 'FAIL', 'root', '10.0.0.7']
print(parcalar)
print(parcalar[2], parcalar[-1])  #! liste de indekslenir
print("a,b,,c".split(","))        #! ayraç verirsen boş parçalar da gelir
ip = "10.0.0.7"
print(ip.split("."))
print("-".join(["10", "0", "0", "7"]))   #! join: ayraç.join(liste)
yol = "/var/log/auth.log"
print(yol.rsplit("/", 1))          #! sağdan, en fazla 1 kez böl
```

`split` sonucu bir **liste**dir. Listeleri P13'te derinlemesine göreceğiz; şimdilik indekslenebildiğini bilmen yeterli.

> [!NOT]
> `join` bir metin metodudur, liste metodu değil: `", ".join(liste)`. İlk görüşte ters gelir ama mantıklıdır: ayraç birleştirmeyi bilen şeydir ve listenin içindekilerin metin olması şarttır.
:::

::: anlat f-string: biçimlendirmenin kralı
Değişkenleri metnin içine yerleştirmenin en modern ve okunaklı yolu **f-string**'dir: tırnağın önüne `f` koy, değişkenleri `{}` içine yaz. Süslü parantezin içine **herhangi bir ifade** yazabilirsin.

```python
kullanici, deneme = "root", 7
print(f"{kullanici} {deneme} kez denedi")
print(f"{deneme * 2} toplam, büyük harf: {kullanici.upper()}")
```

İki noktadan `:` sonra **biçim tanımı** gelir. Rapor ve tablo yazarken çok işine yarar:

```python
pi, n, oran = 3.14159, 42, 0.873
print(f"{pi:.2f}")        #! 3.14 — 2 ondalık
print(f"{n:5d}|")         #! '   42|' — 5 karakterlik alan, sağa yaslı
print(f"{n:<5}|")         #! '42   |' — sola yasla
print(f"{n:^7}|")         #! ortala
print(f"{n:05d}")         #! 00042 — sıfırla doldur
print(f"{oran:.1%}")      #! 87.3% — yüzde
print(f"{1234567:,}")     #! 1,234,567 — binlik ayraç
print(f"{255:x} {255:08b}")  #! ff 11111111 — hex ve ikilik
print(f"{n=}")            #! n=42 — hata ayıklama kısayolu
```

> [!DERİN]
> f-string çalışma anında bir `str.format` çağrısına değil, Python sürümüne bağlı biçimlendirme bytecode komutlarına derlenir. Hız, ifadeye ve Python sürümüne göre ölçülür; burada amaç okunabilir biçimlendirmedir. Bytecode düğmesiyle bak: `f"{x}"` için ayrı bir fonksiyon çağrısı göremezsin.

> [!GÜVENLİK]
> f-string'i **SQL sorgusu ya da kabuk komutu** kurmak için asla kullanma: `f"SELECT * FROM users WHERE ad='{ad}'"`. Kullanıcı `ad` olarak `' OR '1'='1` verirse sorgunun anlamı değişir. Bu SQL injection'ın ta kendisidir. Doğrusu parametreli sorgudur (P29) ve kabuk için argüman listesidir (P54).
:::

::: tahmin
Çıktı tek satır. Boşluklara dikkat:

```python
port = 22
oran = 0.4567
print(f"{port:>5}|{oran:.1%}|{port:04d}")
```

???

`   22|45.7%|0022`. `>5` 5 karakterlik alanda sağa yaslar (3 boşluk + 22), `.1%` 100 ile çarpıp 1 ondalık yüzde yazar, `04d` 4 haneye sıfırla tamamlar.
:::

::: gorev Log satırı ayrıştır
`satir` değişkenini `split()` ile parçala ve **f-string** ile şu biçimde yazdır: `kullanıcı@ip: durum`. Kodun başka satırlarla da çalışmalı.

```cikti
root@10.0.0.7: FAIL
```

```starter
# Kusurlu başlangıç: çıktıyı ve kullanılan işlemi görevle karşılaştır.
satir = "2026-10-19 08:15:02 FAIL root 10.0.0.7"
p = satir.split()
print(f"{p[2]}@{p[4]}: {p[3]}")
```

```test
eq(out.strip(), "root@10.0.0.7: FAIL", "Çıktı: root@10.0.0.7: FAIL")
eq(run_code(src.replace("2026-10-19 08:15:02 FAIL root 10.0.0.7", "2026-10-19 09:00:00 OK admin 192.168.0.4")).strip(),
   "admin@192.168.0.4: OK", "Başka satırda da: admin@192.168.0.4: OK")
ok(uses("fstring"), "f-string kullan")
ok(calls("split"), "split() kullan")
```

```solution
satir = "2026-10-19 08:15:02 FAIL root 10.0.0.7"
p = satir.split()
print(f"{p[3]}@{p[4]}: {p[2]}")
```

```hint
`satir.split()` 5 parçalı bir liste verir: tarih, saat, durum, kullanıcı, ip. İndeksleri 0'dan say.
```
:::

::: gorev Hizalı tablo satırı
Üç değişkeni şu düzende tek satır yazdır: servis adı **10 karakterlik alanda sola yaslı**, sonra `|`, port **5 karakter sağa yaslı**, sonra `|`, yük **6 karakterlik alanda 1 ondalıklı yüzde**.

```cikti
ssh       |   22| 87.3%
```

```starter
# Kusurlu başlangıç: çıktıyı ve kullanılan işlemi görevle karşılaştır.
servis = "ssh"
port = 22
yuk = 0.873
print(f"{servis:>10}|{port:<5}|{yuk:>6.1f}")
```

```test
eq(out.rstrip("\n"), "ssh       |   22| 87.3%", "Biçim: ssh       |   22| 87.3%")
v = run_code(src.replace('"ssh"', '"https"').replace("'ssh'", "'https'").replace("22", "8443").replace("0.873", "0.05"))
eq(v.rstrip("\n"), "https     | 8443|  5.0%", "Başka değerlerle: https     | 8443|  5.0%")
```

```solution
servis = "ssh"
port = 22
yuk = 0.873
print(f"{servis:<10}|{port:>5}|{yuk:>6.1%}")
```

```hint
Biçim tanımları: `:<10`, `:>5`, `:>6.1%`
```
:::

::: gorev E-posta metnini düzenle
Kullanıcı girdisi hep kirlidir. `eposta`'nın kenar boşluklarını temizle, küçük harfe çevir ve yazdır; ikinci satırda sadece `@`'den sonraki alan adını yazdır.

```cikti
ali.veli@ornek.com
ornek.com
```

```starter
# Kusurlu başlangıç: çıktıyı ve kullanılan işlemi görevle karşılaştır.
eposta = "  Ali.Veli@Ornek.COM "
eposta.strip()
temiz = eposta.lower()
print(temiz)
print(temiz.split("@")[1])
```

```test
eq(lines, ["ali.veli@ornek.com", "ornek.com"], "İki satır: temiz adres ve alan adı")
v = run_code(src.replace("  Ali.Veli@Ornek.COM ", "Root@Sunucu.Local")).splitlines()
eq(v, ["root@sunucu.local", "sunucu.local"], "Başka adresle de çalışmalı")
```

```solution
eposta = "  Ali.Veli@Ornek.COM "
temiz = eposta.strip().lower()
print(temiz)
print(temiz.split("@")[1])
```

```hint
`strip().lower()` zinciri, sonra `split("@")` iki parçalı liste verir.
```
:::

::: anlat E-posta görevinin sınırı
Bu sentetik örnek bir adet @ içerir. Görev küçük harfe dönüştürme ve parçalama alıştırmasıdır. Gerçek e-posta kimliğinde yerel bölümün harf büyüklüğüyle ilgili kurallar sağlayıcıya bağlı olabilir; bu işlem genel bir adres doğrulayıcı değildir.
:::

::: anlat Yaygın yanlışlar
| Yanlış yaklaşım | Neden kırılır? | Doğrusu |
|---|---|---|
| `strip()` sonucunu kaydetmemek | Başlangıç metni aynı kalır. | Sonucu bir isme ata veya zincirle. |
| `split()` için metin sonucu beklemek | Sonuç, parçaları tutan bir listedir. | p04’teki gibi indeksle; listeler p13’te ayrıntılı işlenecek. |
| Yüzdeyi `.1f` ile yazmak | 0.873 sayısını yüzdeye ölçeklemez. | Yüzde biçimi için `.1%` kullan. |
:::

::: anlat AI derslerinde nerede?
- `ai-temel-01` — Tokenizasyon örneğinde split metni kelime parçalarına ayırır.
- `ai-savunma-31` — Bütçe doğrulamasındaki f-string, geçersiz alanın adını hata mesajına yerleştirir.

Bu bağlantılardaki sözlük, fonksiyon ve model ayrıntıları ileride öğrenilecek. Burada yalnız bu derste gördüğün Python parçasını tanıman yeterli.
:::
