---
id: p16
title: Sözlükler
summary: Anahtar → değer eşlemesi; get, sayma ve gruplama kalıpları, iç içe yapılar.
kazanim: PCEP 3.3
---

::: anlat Anahtar → değer
Sözlük (dict), **anahtarları değerlere** eşler. Liste "kaçıncı?" sorusunu cevaplar, sözlük ise "**hangisi?**" sorusunu:

```python
servis = {"ssh": 22, "http": 80, "https": 443}
print(servis["https"])          #! anahtarla erişim
servis["rdp"] = 3389            #! yeni anahtar ekle
servis["http"] = 8080           #! var olanı güncelle
del servis["ssh"]               #! sil
print(servis, len(servis))
print("rdp" in servis)          #! in ANAHTARLARA bakar
print(80 in servis)             #! False — değerlere değil!
```

Olmayan bir anahtarı `d["x"]` ile okumak `KeyError` verir. Güvenli okumak için `get` kullanılır:

```python
servis = {"ssh": 22}
print(servis.get("ftp"))         #! None — hata yok
print(servis.get("ftp", 21))     #! varsayılan değer
print(servis.pop("ssh", None))   #! çıkar ve döndür; yoksa varsayılan
```

### Dolaşma
```python
servis = {"ssh": 22, "http": 80}
for ad in servis:                #! varsayılan: anahtarlar
    print(ad)
for ad, port in servis.items():  #! anahtar-değer çiftleri (demet)
    print(f"{ad}:{port}")
print(list(servis.keys()), list(servis.values()))
```

Python 3.7'den beri sözlükler **ekleme sırasını korur**.

> [!DERİN]
> Sözlük bir **hash tablosudur**. Anahtar `hash()` ile bir sayıya çevrilir, bu sayıdan arama konumu hesaplanır; farklı anahtarların aynı hash değerine sahip olması mümkündür ve çakışmalar ayrıca çözülür. Bu yüzden erişim, sözlük milyon elemanlı da olsa ortalama **O(1)**, yani sabit sürelidir. Bedeli şu: anahtar **hash'lenebilir** olmalıdır: hash değeri ömrü boyunca sabit kalmalı ve eşit anahtarların hash değerleri eşit olmalıdır. Değiştirilemez olmak tek başına yetmez; içinde liste bulunan demet hash'lenemez. `d[[1, 2]] = 3` → `TypeError: unhashable type: 'list'`. Demet olur: `d[(1, 2)] = 3`. CPython 3.6'dan beri "kompakt" sözlük kullanır: indeks dizisi ve sıralı giriş dizisi ayrıdır. Sıranın korunması bu tasarımın yan ürünüdür.
:::

::: tahmin
İki satır:

```python
d = {"a": 1, "b": 2}
d["c"] = 3
d["a"] = 10
print(d)
print(d.get("z", 0), "b" in d, 2 in d)
```

???

`{'a': 10, 'b': 2, 'c': 3}`, sonra `0 True False`. Var olan anahtara atama sırayı değiştirmez, sadece değeri günceller. `in` anahtarlara bakar; `2` bir değerdir, anahtar değil.
:::

::: anlat Sayma, gruplama, iç içe
Güvenlik verisinin büyük kısmı iki soruyla analiz edilir: "**kaç tane**?" ve "**kime ait**?"

```python
# SAYMA: get(…, 0) + 1 kalıbı
olaylar = ["10.0.0.7", "10.0.0.9", "10.0.0.7", "10.0.0.7"]
sayim = {}
for ip in olaylar:
    sayim[ip] = sayim.get(ip, 0) + 1
print(sayim)

# GRUPLAMA: setdefault ile anahtar yoksa boş liste aç
baglantilar = [("10.0.0.7", 22), ("10.0.0.9", 80), ("10.0.0.7", 443)]
gruplar = {}
for ip, port in baglantilar:
    gruplar.setdefault(ip, []).append(port)
print(gruplar)

# İÇ İÇE: JSON gibi yapılar
olay = {"kullanici": {"ad": "root", "uid": 0}, "kaynak": {"ip": "10.0.0.7"}}
print(olay["kullanici"]["ad"], olay["kaynak"]["ip"])

# BİRLEŞTİRME (3.9+)
varsayilan = {"zaman_asimi": 5, "yeniden": 3}
kullanici = {"zaman_asimi": 10}
print(varsayilan | kullanici)   #! sağdaki kazanır
```

Değere göre sıralamak için: `sorted(sayim.items(), key=lambda kv: kv[1], reverse=True)`. `lambda`'yı P23'te açacağız. P32'deki `collections.Counter` ise sayma işini tek satıra indirir.

> [!GÜVENLİK]
> Neredeyse her tespit kuralının altında bu iki kalıp yatar: "aynı IP'den 5 dakikada 10'dan fazla başarısız giriş" = IP'ye göre **sayma**; "bir kullanıcının giriş yaptığı farklı makineler" = kullanıcıya göre **gruplama**. SIEM sorgu dillerindeki (KQL'de `summarize count() by ip`) ilk komut budur.
:::

::: tahmin
Ne yazdırır?

```python
sayim = {}
for k in "abracadabra":
    sayim[k] = sayim.get(k, 0) + 1
print(sayim["a"], len(sayim))
```

???

`5 5`. "abracadabra" içinde 5 tane `a` var. Farklı harfler a, b, r, c, d olmak üzere 5 tanedir, yani sözlükte 5 anahtar olur.
:::

::: gorev Başarısız giriş sayacı
İlk satırda olay sayısı N, ardından N satır gelir: `kullanici durum` (durum `OK` ya da `FAIL`). Her kullanıcının **FAIL** sayısını say. En az bir FAIL'i olan kullanıcıları **ada göre alfabetik** sırada `kullanici: sayı` biçiminde yazdır.

```cikti
ali: 2
root: 3
```

```starter
n = int(input())
sayim = {}
for _ in range(n):
    kullanici, durum = input().split()
    sayim[kullanici] = sayim.get(kullanici, 0) + 1
for kullanici in sorted(sayim):
    print(f"{kullanici}: {sayim[kullanici]}")
```

```stdin
6
root FAIL
ali FAIL
root FAIL
veli OK
ali FAIL
root FAIL
```

```test
eq(run("0").strip(), "", "sıfır olay")
eq(run("6\nroot FAIL\nali FAIL\nroot FAIL\nveli OK\nali FAIL\nroot FAIL").strip().splitlines(), ["ali: 2", "root: 3"], "örnek girdi")
eq(run("2\nx OK\ny OK").strip(), "", "hiç FAIL yoksa çıktı boş")
eq(run("3\nzeynep FAIL\nayse FAIL\nzeynep OK").strip().splitlines(), ["ayse: 1", "zeynep: 1"], "alfabetik sıra")
```

```solution
n = int(input())
sayim = {}
for _ in range(n):
    kullanici, durum = input().split()
    if durum == "FAIL":
        sayim[kullanici] = sayim.get(kullanici, 0) + 1
for kullanici in sorted(sayim):
    print(f"{kullanici}: {sayim[kullanici]}")
```

```hint
`for _ in range(n):` ile N satır oku; `kullanici, durum = input().split()`.
```

```hint
`sorted(sozluk)` anahtarları sıralı verir.
```
:::

::: gorev IP'ye göre portlar
İlk satırda N, ardından N satır `ip port`. Her IP'nin portlarını grupla. IP'leri **ilk görüldükleri sırayla**, portları da geldikleri sırayla `ip: p1,p2` biçiminde yazdır.

```cikti
10.0.0.7: 22,443
10.0.0.9: 80
```

```starter
n = int(input())
gruplar = {}
for _ in range(n):
    ip, port = input().split()
    gruplar[ip] = [port]
for ip, portlar in gruplar.items():
    print(f"{ip}: {','.join(portlar)}")
```

```stdin
3
10.0.0.7 22
10.0.0.9 80
10.0.0.7 443
```

```test
eq(run("0").strip(), "", "sıfır bağlantı")
eq(run("3\na 22\na 22\na 80").strip(), "a: 22,22,80", "tekrarlar ve sıra korunur")
eq(run("3\n10.0.0.7 22\n10.0.0.9 80\n10.0.0.7 443").strip().splitlines(), ["10.0.0.7: 22,443", "10.0.0.9: 80"], "örnek")
eq(run("1\n1.1.1.1 53").strip(), "1.1.1.1: 53", "tek satır")
eq(run("3\nb 1\na 2\nb 3").strip().splitlines(), ["b: 1,3", "a: 2"], "ilk görülme sırası")
```

```solution
n = int(input())
gruplar = {}
for _ in range(n):
    ip, port = input().split()
    gruplar.setdefault(ip, []).append(port)
for ip, portlar in gruplar.items():
    print(f"{ip}: {','.join(portlar)}")
```

```hint
`gruplar.setdefault(ip, []).append(port)`. Sözlük ekleme sırasını korur.
```
:::

::: gorev Ters sözlük
`servisler` sözlüğünden **port → ad** eşlemesi yapan `port_adi` adında yeni bir sözlük üret. Sonra girdiden bir port oku ve adını yazdır; yoksa `bilinmiyor` yaz.

```starter
servisler = {"ssh": 22, "http": 80, "https": 443, "dns": 53}
port = int(input())
port_adi = {}
for ad, p in servisler.items():
    port_adi[ad] = p
print(port_adi.get(port, "bilinmiyor"))
```

```stdin
443
```

```test
eq(port_adi, {22: "ssh", 80: "http", 443: "https", 53: "dns"}, "port_adi = {22: 'ssh', 80: 'http', ...}")
eq(run("443").strip(), "https", "443 → https")
eq(run("53").strip(), "dns", "53 → dns")
eq(run("3389").strip(), "bilinmiyor", "3389 → bilinmiyor")
```

```solution
servisler = {"ssh": 22, "http": 80, "https": 443, "dns": 53}
port = int(input())
port_adi = {}
for ad, p in servisler.items():
    port_adi[p] = ad
print(port_adi.get(port, "bilinmiyor"))
```

```hint
`for ad, p in servisler.items(): port_adi[p] = ad`
```

```hint
Yoksa varsayılan: `port_adi.get(port, "bilinmiyor")`
```
:::


::: anlat Yaygın yanlışlar
| Yanlış yaklaşım | Neden kırılır? | Doğrusu |
|---|---|---|
| `80 in servisler` ile port aramak | `in` anahtarları inceler. | Değerleri arıyorsan `80 in servisler.values()` kullan. |
| Her olayda `gruplar[ip] = [port]` yazmak | Önceki port listesini siler. | `setdefault(ip, []).append(port)` ile mevcut listeye ekle. |
| `get` çağrısının varsayılanı sözlüğe eklediğini sanmak | `get` yalnız değer döndürür. | Kaydetmek için atama; eksik anahtarı oluşturmak için `setdefault` kullan. |
:::

::: anlat AI derslerinde nerede?
- `ai-savunma-32` çözümünde `g.setdefault(k["kip"], {...})`, sonuçları çalışma kipine göre gruplar. Buradaki IP gruplama kalıbının aynısıdır; her grubun değeri bu kez bir sayaç sözlüğüdür.
- `ai-savunma-19` çözümünde `set(politika)` ile politika sözlüğünün anahtarları kontrol edilir. Sözlüğü doğrudan dolaşmanın değerleri değil anahtarları verdiği burada şema denetimi için kullanılır. Küme işlemlerini sonraki derste göreceğiz.
:::
