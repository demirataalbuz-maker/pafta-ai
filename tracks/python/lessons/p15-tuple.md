---
id: p15
title: Demetler ve Paketten Çıkarma
summary: tuple değiştirilemez kayıttır; unpacking, *geri kalan, zip ve enumerate.
kazanim: PCEP 3.2
---

::: anlat Değiştirilemez sıralı kayıt
**Demet** (tuple), listenin değiştirilemez kardeşidir. Normal parantezle (ya da hiç parantez kullanmadan, sadece virgülle) yazılır:

```python
nokta = (3, 4)
kayit = "web01", "10.0.0.5", 443     #! parantezsiz de demet: virgül yapar
print(kayit[1], kayit[:2], len(kayit))   #! indeks ve dilim listeyle aynı
print(type(kayit))
tek = (5,)                           #! tek elemanlı demette virgül ŞART
degil = (5)                          #! bu sadece parantezli bir 5
print(type(tek), type(degil))
```

Boş olmayan demeti oluşturan işaret **virgüldür**. Boş demet özel olarak `()` ile yazılır. Parantez sadece gruplama için gerekir. Demetler değiştirilemez olduğu için `kayit[0] = "db01"` gibi bir atama `TypeError` fırlatır.

### Ne zaman liste, ne zaman demet?
- **Liste**: aynı türden, sayısı değişebilen elemanlar ("tarama sırasındaki portlar").
- **Demet**: farklı anlamlardaki alanlardan oluşan **sabit yapılı kayıt** ("(host, ip, port)"). Kayıt sabit olduğu için değiştirilemezlik bir güvencedir.

Bir tuple, bütün öğeleri hashlenebilir olduğunda **sözlük anahtarı** ve **küme elemanı** olabilir (p16, p17). `(1, 2)` uygundur; `(1, [2])` içinde liste tuttuğundan uygun değildir. Tuple içindeki öğe bağları değişmez ama içindeki liste değiştirilebilir.

### Paketten çıkarma (unpacking)
```python
host, ip, port = ("web01", "10.0.0.5", 443)   #! sayılar eşleşmeli
print(host, port)
ilk, *orta, son = [1, 2, 3, 4, 5]             #! * geri kalanı listeye toplar
print(ilk, orta, son)
a, b = 1, 2
a, b = b, a                                    #! P02'deki takas = demet paketleme + çıkarma
print(a, b)
```

> [!DERİN]
> `a, b = b, a` arka planda geçici bir demet kurmaz. CPython bu kalıbı geçici bir tuple oluşturmadan yığın komutlarıyla yürütebilir; kesin bytecode sürüme ve bağlama bağlıdır. Bytecode sekmesinde bak. Sayı uyuşmazsa (`a, b = 1, 2, 3`) `ValueError: too many values to unpack` alırsın.
:::

::: tahmin
İki satır:

```python
t = (1, 2, 3)
a, *b = t
print(a, b)
x = (5)
y = (5,)
print(type(x).__name__, type(y).__name__)
```

???

`1 [2, 3]`, sonra `int tuple`. Yıldızlı hedef **her zaman liste** toplar, kaynak demet olsa bile. `(5)` sadece parantezli bir sayıdır; demet yapan virgüldür.
:::

::: anlat zip, enumerate ve iç içe çıkarma
**`zip`** birden fazla diziyi **yan yana** dolaşır ve her adımda bir demet üretir. En kısa dizi bitince durur:

```python
hostlar = ["web01", "db01", "dc01"]
ipler = ["10.0.0.5", "10.0.0.6"]
for host, ip in zip(hostlar, ipler):        #! demet anında paketten çıkar
    print(f"{host} → {ip}")

ciftler = [("ssh", 22), ("http", 80)]
for i, (ad, port) in enumerate(ciftler, 1): #! iç içe çıkarma
    print(i, ad, port)

matris = [[1, 2, 3], [4, 5, 6]]
print(list(zip(*matris)))                   #! * ile açıp zip'le = transpoz
```

`zip(*matris)` hilesini anla: `*matris` listeyi argümanlara açar, yani `zip([1, 2, 3], [4, 5, 6])` olur. Bu da sütunları demet olarak verir. Satırlar sütun olur.

> [!NOT]
> `zip` uzunluk farkını sessizce yutar: üçüncü host'un IP'si yok ama hata almadın. Python 3.10+ `zip(a, b, strict=True)` uzunluklar farklıysa hata verir. Veri bütünlüğü önemliyse onu kullan.
:::

::: tahmin
Üç satır:

```python
isimler = ["web", "db", "dc"]
portlar = [80, 5432]
for ad, port in zip(isimler, portlar):
    print(ad, port)
print(list(zip(*[(1, 2), (3, 4)])))
```

???

`web 80`, `db 5432`, `[(1, 3), (2, 4)]`. zip en kısa dizi bitince durur, bu yüzden `dc` hiç görünmez. Son satır transpozdur.
:::

::: gorev İlk, son ve orta
Girdiden boşlukla ayrılmış en az iki eleman oku. **Yıldızlı paketten çıkarma** ile ilk ve son elemanı ayır; ortada kaç eleman kaldığını bul ve şu biçimde yazdır:

```cikti
ilk=a son=e orta=3
```

```starter
# Kusurlu başlangıç: görevle karşılaştırıp hatayı düzelt.
parcalar = input().split()
ilk, *orta, son = parcalar
print(f"ilk={ilk} son={son} orta={len(parcalar)}")
```

```stdin
a b c d e
```

```test
eq(run("a b c d e").strip(), "ilk=a son=e orta=3", "a b c d e")
eq(run("x y").strip(), "ilk=x son=y orta=0", "iki eleman → orta=0")
eq(run("1 2 3").strip(), "ilk=1 son=3 orta=1", "üç eleman")
ok(uses("starred"), "Yıldızlı paketten çıkarma (*orta) kullan")
```

```solution
parcalar = input().split()
ilk, *orta, son = parcalar
print(f"ilk={ilk} son={son} orta={len(orta)}")
```

```hint
`ilk, *orta, son = parcalar`
```
:::

::: gorev Host-IP eşleştirme
İlk satırda boşlukla ayrılmış host adları, ikinci satırda aynı sırada IP adresleri var. `zip` ile eşleştirip her çifti `host -> ip` biçiminde ayrı satıra yazdır.

```cikti
web01 -> 10.0.0.5
db01 -> 10.0.0.6
```

```starter
# Kusurlu başlangıç: görevle karşılaştırıp hatayı düzelt.
hostlar = input().split()
ipler = input().split()
for host, ip in zip(ipler, hostlar):
    print(f"{host} -> {ip}")
```

```stdin
web01 db01
10.0.0.5 10.0.0.6
```

```test
eq(run("web01 db01\n10.0.0.5 10.0.0.6").strip().splitlines(), ["web01 -> 10.0.0.5", "db01 -> 10.0.0.6"], "iki çift")
eq(run("a\n1.1.1.1").strip().splitlines(), ["a -> 1.1.1.1"], "tek çift")
eq(run("a b\n1").strip().splitlines(), ["a -> 1"], "zip varsayılan olarak en kısa girdide durur")
ok(calls("zip"), "zip kullan")
```

```solution
hostlar = input().split()
ipler = input().split()
for host, ip in zip(hostlar, ipler):
    print(f"{host} -> {ip}")
```

```hint
`for host, ip in zip(hostlar, ipler):`
```
:::

::: gorev Transpoz
Girdide 3 satır var; her satırda boşlukla ayrılmış aynı sayıda değer bulunuyor. Satırları sütuna çevir (transpoz) ve her yeni satırı boşlukla ayırarak yazdır. `zip(*...)` kullan.

```cikti
1 4 7
2 5 8
3 6 9
```

```starter
# Kusurlu başlangıç: görevle karşılaştırıp hatayı düzelt.
satirlar = []
for satir_no in range(3):
    satirlar.append(input().split())
for sutun in zip(satirlar):
    print(*sutun)
```

```stdin
1 2 3
4 5 6
7 8 9
```

```test
eq(run("1 2 3\n4 5 6\n7 8 9").strip().splitlines(), ["1 4 7", "2 5 8", "3 6 9"], "3×3 transpoz")
eq(run("a b\nc d\ne f").strip().splitlines(), ["a c e", "b d f"], "3×2 → 2×3")
ok(calls("zip") and uses("starred"), "zip(*satirlar) ile yıldızlı açma kullan")
```

```solution
satirlar = []
for satir_no in range(3):
    satirlar.append(input().split())
for sutun in zip(*satirlar):
    print(*sutun)
```

```hint
`zip(*satirlar)` her adımda bir sütunu demet olarak verir. `print(*demet)` boşlukla yazar.
```
:::

::: anlat Yaygın yanlışlar
| Yanlış yaklaşım | Neden kırılır? | Doğrusu |
|---|---|---|
| (5) yazıp tuple beklemek | Bu yalnız parantezli bir sayıdır. | Tek elemanlı tuple için (5,) yaz. |
| Her tuple sözlük anahtarı olabilir sanmak | İçeride liste gibi hashlenemeyen öğe olabilir. | Bütün öğelerin de hashlenebilir olduğunu doğrula. |
| zip tüm elemanları işler sanmak | Varsayılan zip en kısa girdi bittiğinde durur. | Uzunluk eşitliği gerekiyorsa strict=True kullan. |
:::

::: anlat AI derslerinde nerede?
- `ai-savunma-32` — Sınıflandırma metriğinde gerçek etiket ile skor zip kullanılarak yan yana işlenir.
- `ai-uretim-09` — LoRA/DoRA testleri beklenen ve gerçekleşen vektör koordinatlarını zip ile karşılaştırır.
:::
