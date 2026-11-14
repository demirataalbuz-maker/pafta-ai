---
id: p04
title: Metinler I · İndeks ve Dilim
summary: str bir karakter dizisidir; indeksleme, dilimleme ve değiştirilemezlik.
kazanim: PCEP 1.3, PCEP 3.4, PCAP 3.2
---

::: anlat Metin bir karakter dizisidir
`str` (string), sıralı karakterlerden oluşan bir dizidir. Her karakterin bir **indeksi** (sıra numarası) vardır ve sayma **0'dan** başlar:

```text
 karakter:   P   A   F   T   A
 indeks:     0   1   2   3   4
 negatif:   -5  -4  -3  -2  -1
```

```python
s = "PAFTA"
print(s[0])        #! 'P' — ilk karakter
print(s[4])        #! 'A' — son karakter (uzunluk - 1)
print(s[-1])       #! 'A' — negatif indeks sondan sayar
print(len(s))      #! 5 — karakter sayısı
print("FT" in s)   #! True — alt metin var mı?
print("X" not in s)#! True — alt metin yok mu?
print("ab" + "cd") #! abcd — birleştirme
print("-" * 10)    #! ---------- — tekrar
```

Metinler `<`, `>`, `==` ile karşılaştırıldığında Python karakterlerin Unicode **kod noktası** numaralarına soldan sağa bakar: `ord("A")` → `65`, `ord("a")` → `97`, tersine `chr(65)` → `"A"`. Bu yüzden `"Z" < "a"` sonucu `True` çıkar (büyük ASCII harfler küçüklerden önce gelir).

### Özel karakterler ve çok satırlı metin
Ters eğik çizgi `\` bir **kaçış** başlatır: `\n` yeni satır, `\t` sekme, `\"` metin içinde tırnak, `\\` gerçek bir ters eğik çizgidir. Üç tırnak `"""..."""` çok satırlı metin yazar.

```python
print("Ad:\tAli\nRol:\tadmin")   #! \t sekme, \n yeni satır
yol = r"C:\Users\yeni"            #! r"..." ham metin: \ kaçış sayılmaz
print(yol)
afis = """Satır bir
Satır iki"""
print(afis)
```

> [!TUZAK]
> Windows yollarında `"C:\new"` yazarsan `\n` yeni satıra dönüşür. Ya ham metin (`r"C:\new"`) ya da ileri eğik çizgi (`"C:/new"`) kullan. Regex desenleri için de ham metin standarttır (P34).

### Metinler değiştirilemez
Bir metnin karakterini yerinde değiştiremezsin. `s[0] = "p"` hata verir. Metinler **değiştirilemez** (immutable) nesnelerdir. Değişiklik istiyorsan **yeni** bir metin üretirsin: `s = "p" + s[1:]`.
:::

::: tahmin
Çıktı tek satır:

```python
s = "PAFTA"
print(s[0], s[-1], len(s), s[1] + s[3])
```

???

`P A 5 AT`. `s[1]` = `A`, `s[3]` = `T`. Birleşince `AT` olur.
:::

::: anlat Dilimleme: [başla:dur:adım]
Tek karakter yerine bir **parça** almak için dilim (slice) kullanırsın: `s[başla:dur]`. **Başlangıç dahil, bitiş hariçtir.**

```python
ip = "192.168.1.10"
print(ip[0:3])     #! '192' — 0,1,2 (3 hariç)
print(ip[:3])      #! başlangıcı boş bırakırsan 0
print(ip[8:])      #! '1.10' — sonu boş bırakırsan sona kadar
print(ip[-2:])     #! '10' — son iki karakter
print(ip[::2])     #! üçüncü sayı adımdır: ikişer atla
print(ip[::-1])    #! adım -1: tersten — '01.1.861.291'
print(ip[100:])    #! '' — dilim taşmaz, hata vermez
```

"Bitiş hariç" kuralının iki güzel sonucu var: `0 <= n <= len(s)` olduğunda `s[:n]` tam **n** karakter verir ve `s[:n] + s[n:]` her zaman `s`'in kendisidir.

> [!DERİN]
> `s[1:4]` aslında `s[slice(1, 4)]` demektir. `slice` gerçek bir nesnedir ve köşeli parantez çağrısı `s.__getitem__(slice(1, 4, None))`'a dönüşür. P39'de kendi sınıflarına dilimleme desteği eklerken bunu kullanacaksın. İndeks taşarsa `IndexError` alırsın, dilim taşarsa almazsın; dilim, sınırları sessizce kırpar.
:::

::: tahmin
Çıktı tek satır:

```python
s = "192.168.1.10"
print(s[:3], s[-2:], s[::4])
```

???

`192 10 111`. `s[::4]` 0, 4 ve 8. indeksleri alır: `s[0]='1'`, `s[4]='1'`, `s[8]='1'`. Üçü de `1`.
:::

::: gorev Dosya adı parçala
`dosya` değişkeninden **dilimleyerek** iki satır yazdır: ilk 5 karakter ve son 6 karakter.

```cikti
rapor
tar.gz
```

```starter
# Kusurlu başlangıç: çıktıyı ve kullanılan işlemi görevle karşılaştır.
dosya = "rapor_2026.tar.gz"
print(dosya[:4])
print(dosya[-5:])
```

```test
eq(lines, ["rapor", "tar.gz"], "Satırlar: rapor, tar.gz")
eq(run_code(src.replace("rapor_2026.tar.gz", "loglar.backup.tar.gz")).split(), ["logla", "tar.gz"],
   "Başka bir adla da çalışmalı (dilimle, elle yazma)")
```

```solution
dosya = "rapor_2026.tar.gz"
print(dosya[:5])
print(dosya[-6:])
```

```hint
İlk 5 karakter `[:5]`. Son 6 karakter için negatif başlangıç kullan.
```
:::

::: gorev Palindrom mu?
`kelime` tersten okununca da aynıysa `True`, değilse `False` yazdır. Karşılaştırmayı `==` ile yap.

```starter
# Kusurlu başlangıç: çıktıyı ve kullanılan işlemi görevle karşılaştır.
kelime = "kayak"
print(kelime == kelime[:1])
```

```test
eq(out.strip(), "True", "'kayak' → True")
eq(run_code(src.replace('"kayak"', '"python"').replace("'kayak'", "'python'")).strip(), "False", "'python' → False")
eq(run_code(src.replace('"kayak"', '"a"').replace("'kayak'", "'a'")).strip(), "True", "'a' → True")
ok("[::-1]" in src, "Tersine çevirmek için [::-1] dilimini kullan")
```

```solution
kelime = "kayak"
print(kelime == kelime[::-1])
```

```hint
`kelime[::-1]` metni ters çevirir. `print(a == b)` doğrudan True/False yazar.
```
:::

::: gorev Kart numarası maskele
Log'a kart numarası yazmak güvenlik ihlalidir; sadece son 4 hane görünmelidir. `kart` uzunluğu ne olursa olsun, son 4 hane hariç her karakterin yerine `*` koyup yazdır. `*` tekrarını ve `len()` kullan.

```cikti
************6467
```

```starter
# Kusurlu başlangıç: çıktıyı ve kullanılan işlemi görevle karşılaştır.
kart = "4539148803436467"
print("*" * 12 + kart[-4:])
```

```test
eq(out.strip(), "************6467", "16 haneli kart → 12 yıldız + 6467")
eq(run_code(src.replace("4539148803436467", "1234567890")).strip(), "******7890", "10 haneli → 6 yıldız + 7890")
ok(calls("len"), "len() ile uzunluğa göre hesapla")
```

```solution
kart = "4539148803436467"
print("*" * (len(kart) - 4) + kart[-4:])
```

```hint
Yıldız sayısı `len(kart) - 4`. `"*" * n` n tane yıldız üretir.
```

```hint
Son dört hane: `kart[-4:]`
```
:::

::: anlat İndeks sınırı
`"abc"[3]` `IndexError` verir. `"abc"[3:]` ise boş metindir (`""`). İndeks tek bir eleman ister, dilim bir aralık alır ve taşan sınırları sessizce kırpar. Unicode metinlerde Python `str` kod noktalarını sayar; ekranda tek işaret gibi görünen birleşik bir yazım birkaç kod noktası içerebilir.
:::

::: anlat Yaygın yanlışlar
| Yanlış yaklaşım | Neden kırılır? | Doğrusu |
|---|---|---|
| Dilim sonunu dahil sanmak | `s[:5]` 0–4 indekslerini alır. | İstenen karakter sayısına göre hariç bitişi seç. |
| `s[0] = "x"` yazmak | str karakterleri yerinde atanamaz. | Dilimleri birleştirerek yeni metin üret. |
| Her kart için 12 yıldız kullanmak | Farklı uzunluktaki kartta maske bozulur. | `len(kart) - 4` kadar yıldız üret. |
:::

::: anlat AI derslerinde nerede?
- `ai-uretim-02` — Tokenizasyon, metin parçalarını dilimle alır.
- `ai-savunma-19` — RAG seçimi ilk top_k adayı bir dilimle sınırlar.

Bu bağlantılardaki sözlük, fonksiyon ve model ayrıntıları ileride öğrenilecek. Burada yalnız bu derste gördüğün Python parçasını tanıman yeterli.
:::
