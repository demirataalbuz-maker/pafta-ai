---
id: p21
title: Parametreler Derinlemesine
summary: Konumsal ve anahtar sözcüklü argüman, varsayılan değer, *args, **kwargs, / ve * sınırları.
kazanim: PCEP 4.2, PCPP1 1.4
---

::: anlat Argüman vermenin yolları
Bir fonksiyona argümanı iki biçimde verebilirsin:

```python
def baglan(host, port, zaman_asimi):
    return f"{host}:{port} (t={zaman_asimi})"

print(baglan("web01", 443, 5))                         #! konumsal: sıraya göre
print(baglan(host="web01", zaman_asimi=5, port=443))   #! anahtar sözcüklü: isme göre, sıra serbest
print(baglan("web01", zaman_asimi=5, port=443))        #! karışık: önce konumsallar
```

**Varsayılan değerli** parametreler çağrıda verilmezse varsayılanı alır:

```python
def baglan(host, port=22, zaman_asimi=5):
    return f"{host}:{port} (t={zaman_asimi})"

print(baglan("web01"))                  #! port=22, zaman_asimi=5
print(baglan("web01", 2222))
print(baglan("web01", zaman_asimi=30))  #! sadece istediğini değiştir
```

### *args ve **kwargs
- `*args`: fazladan **konumsal** argümanları bir **demette** toplar.
- `**kwargs`: fazladan **anahtar sözcüklü** argümanları bir **sözlükte** toplar.

```python
def toplam(*sayilar):                   #! istediğin kadar argüman
    return sum(sayilar)
print(toplam(), toplam(1, 2), toplam(1, 2, 3, 4))

def olay(tur, **alanlar):
    return tur, alanlar
print(olay("giris", kullanici="root", ip="10.0.0.7"))

def baglan(host, port=22):
    return f"{host}:{port}"

degerler = [1, 2, 3]
ayarlar = {"port": 8443}
print(toplam(*degerler))                #! çağrıda * listeyi argümanlara açar
print(baglan("web01", **ayarlar))       #! ** sözlüğü anahtar sözcüklü argümanlara açar
```

İsimler gelenektir; önemli olan yıldızlardır. `args` ve `kwargs` yaygın geleneksel adlardır; `sayilar` gibi açıklayıcı adlar da uygundur.
:::

::: tahmin
İki satır:

```python
def f(a, b=2, *args, c=10, **kw):
    print(a, b, args, c, kw)

f(1)
f(1, 3, 4, 5, c=6, d=7)
```

???

`1 2 () 10 {}`, sonra `1 3 (4, 5) 6 {'d': 7}`. İkinci çağrıda 1 → a, 3 → b, kalan konumsallar (4, 5) → args. `c` sadece isimle verilebilir; tanınmayan `d` ise kw'ye düşer.
:::

::: anlat Sınırlar: * ve /
Parametre listesine çıplak bir `*` koyarsan ondan **sonraki** parametreler **sadece isimle** verilebilir (keyword-only). `/` koyarsan ondan **önceki** parametreler **sadece konumla** verilebilir (positional-only):

```python
def tara(hedef, /, port=80, *, zaman_asimi=5, gizli=False):
    return hedef, port, zaman_asimi, gizli

print(tara("10.0.0.5", 443, zaman_asimi=2))
```

```python norun
tara("10.0.0.5", 443, 2)          #! TypeError: zaman_asimi isimle verilmeli
tara(hedef="10.0.0.5")            #! TypeError: hedef konumla verilmeli
```

Neden? `tara("x", 443, 2, True)` çağrısında `2` ve `True`'nun ne olduğunu kimse bilemez. `zaman_asimi=2, gizli=True` ise kendini anlatır. Önemli bayrakları (`sil=True`, `dogrulama=False`) **keyword-only** yapmak, yanlışlıkla verilmelerini önler.

Tam sıra: `def f(konum_only, /, normal, *args, kw_only, **kwargs)`.

> [!TUZAK]
> **Değiştirilebilir varsayılan değer, Python'un en ünlü tuzağıdır.** Varsayılan değer fonksiyon **tanımlanırken bir kez** oluşturulur, her çağrıda değil:
>
> ```python norun
> def ekle(x, liste=[]):      # aynı liste her çağrıda paylaşılır!
>     liste.append(x)
>     return liste
> ```
>
> Doğrusu: `def ekle(x, liste=None):` ve gövdede `if liste is None: liste = []`.

> [!DERİN]
> Varsayılanlar fonksiyon nesnesinin üzerinde durur: `ekle.__defaults__`. Tuzağa düşmüş bir fonksiyonun `__defaults__`'ına bakarsan listenin çağrıdan çağrıya büyüdüğünü görürsün. Bu bilinçli bir tasarımdır; bazen önbellek olarak bile kullanılır (`def f(x, _cache={})`). Ama niyetin bu değilse bir hatadır.
:::

::: tahmin
İki satır:

```python
def ekle(x, liste=[]):
    liste.append(x)
    return liste

print(ekle(1))
print(ekle(2))
```

???

`[1]`, sonra `[1, 2]`. Varsayılan liste fonksiyon tanımlanırken **bir kez** oluşturuldu ve iki çağrıda da aynı liste kullanıldı. Röntgen'de bak: iki çağrıdaki `liste` aynı renkli kareyi gösterir.
:::

::: gorev Değişken sayıda argüman
`topla(*sayilar)` fonksiyonunu yaz: kaç argüman verilirse verilsin toplamlarını döndürsün. Hiç argüman yoksa 0 döndürsün.

```starter
def topla(*sayilar):
    return sayilar
```

```test
import inspect
need("topla")
eq(topla(), 0, "topla() → 0")
eq(topla(5), 5, "topla(5) → 5")
eq(topla(1, 2, 3, 4), 10, "topla(1, 2, 3, 4) → 10")
eq(topla(*range(101)), 5050, "topla(*range(101)) → 5050")
ok(any(p.kind == p.VAR_POSITIONAL for p in inspect.signature(topla).parameters.values()), "*sayilar parametresi kullan")
```

```solution
def topla(*sayilar):
    sonuc = 0
    for n in sayilar:
        sonuc += n
    return sonuc
```

```hint
`def topla(*sayilar):` ile sayilar bir demet olur.
```
:::

::: gorev Paylaşılan liste hatası
Bu fonksiyon her çağrıda yeni bir olay listesi başlatmalı ama önceki çağrıların olaylarını da taşıyor. Varsayılanı `None` yaparak düzelt.

```starter
def kayit_ekle(olay, kayitlar=[]):
    kayitlar.append(olay)
    return kayitlar
```

```test
need("kayit_ekle")
bos = []
ok(kayit_ekle("ilk", bos) is bos, "verilen boş liste aynı nesne olarak güncellenmeli")
eq(bos, ["ilk"], "boş dış liste kaybolmamalı")
eq(kayit_ekle("a"), ["a"], "kayit_ekle('a') → ['a']")
eq(kayit_ekle("b"), ["b"], "ikinci çağrı da yeni liste: ['b']")
mevcut = ["x"]
eq(kayit_ekle("y", mevcut), ["x", "y"], "verilen listeye eklemeli")
ok(mevcut == ["x", "y"], "verilen liste yerinde güncellenmeli")
ok(kayit_ekle.__defaults__ == (None,), "varsayılan değer None olmalı", got=kayit_ekle.__defaults__)
```

```solution
def kayit_ekle(olay, kayitlar=None):
    if kayitlar is None:
        kayitlar = []
    kayitlar.append(olay)
    return kayitlar
```

```hint
`def kayit_ekle(olay, kayitlar=None):` ve gövdenin başında `if kayitlar is None: kayitlar = []`
```
:::

::: gorev Sadece isimle verilen ayarlar
`baglan(host, port=22, *, zaman_asimi=5, sifreli=True)` imzasıyla bir fonksiyon yaz. Şu metni döndürsün:

```cikti
web01:22 t=5 s=True
```

`zaman_asimi` ve `sifreli` **sadece isimle** verilebilmeli: `baglan("h", 22, 9)` `TypeError` vermeli.

```starter
def baglan(host, port=22, zaman_asimi=5, sifreli=True):
    return f"{host}:{port} t={zaman_asimi} s={sifreli}"
```

```test
import inspect
need("baglan")
eq(baglan("web01"), "web01:22 t=5 s=True", "baglan('web01')")
eq(baglan("db", 5432, sifreli=False), "db:5432 t=5 s=False", "baglan('db', 5432, sifreli=False)")
eq(baglan("x", zaman_asimi=30), "x:22 t=30 s=True", "baglan('x', zaman_asimi=30)")
raises(TypeError, baglan, "h", 22, 9, msg="baglan('h', 22, 9) TypeError vermeli")
ps = inspect.signature(baglan).parameters
ok(ps["zaman_asimi"].kind == inspect.Parameter.KEYWORD_ONLY and ps["sifreli"].kind == inspect.Parameter.KEYWORD_ONLY, "zaman_asimi ve sifreli keyword-only olmalı")
```

```solution
def baglan(host, port=22, *, zaman_asimi=5, sifreli=True):
    return f"{host}:{port} t={zaman_asimi} s={sifreli}"
```

```hint
Parametre listesine `port=22`'den sonra çıplak bir `*` ekle.
```
:::

::: gorev Yapılandırılmış log satırı
`log_yaz(seviye, mesaj, **alanlar)` fonksiyonunu yaz. Seviyeyi büyük harfle köşeli parantez içine al, mesajı ekle, sonra her alanı verildiği sırayla `anahtar=değer` olarak boşlukla ekle ve metni döndür.

```cikti
[UYARI] giriş başarısız kullanici=root ip=10.0.0.7
```

```starter
def log_yaz(seviye, mesaj, **alanlar):
    return f"[{seviye.upper()}] {mesaj} {alanlar}"
```

```test
import inspect
need("log_yaz")
eq(log_yaz("uyari", "giriş başarısız", kullanici="root", ip="10.0.0.7"), "[UYARI] giriş başarısız kullanici=root ip=10.0.0.7", "örnek")
eq(log_yaz("bilgi", "başladı"), "[BILGI] başladı", "alan yoksa sadece seviye + mesaj")
eq(log_yaz("hata", "x", kod=500), "[HATA] x kod=500", "sayı değerli alan")
ok(any(p.kind == p.VAR_KEYWORD for p in inspect.signature(log_yaz).parameters.values()), "**alanlar parametresi kullan")
```

```solution
def log_yaz(seviye, mesaj, **alanlar):
    parcalar = [f"[{seviye.upper()}]", mesaj]
    for k, v in alanlar.items():
        parcalar.append(f"{k}={v}")
    return " ".join(parcalar)
```

```hint
`**alanlar` bir sözlüktür ve ekleme sırasını korur: `for k, v in alanlar.items():`
```

```hint
Parçaları bir listede toplayıp sonunda `" ".join(...)` yap.
```
:::


::: anlat Yaygın yanlışlar
| Yanlış yaklaşım | Neden kırılır? | Doğrusu |
|---|---|---|
| Varsayılan listeyi `[]` yapmak | Aynı liste çağrılar arasında paylaşılır. | `None` varsayılanı ve içeride yeni liste kullan. |
| `if not kayitlar` ile varsayılanı ayırt etmek | Çağıranın verdiği boş listeyi de değiştirirsin. | `kayitlar is None` kullan. |
| Keyword-only ayarı konumla vermek | İmza bu çağrıyı reddeder. | Ayarın adını açıkça yaz. |
:::

::: anlat AI derslerinde nerede?
- `ai-savunma-19` çözümündeki politika fonksiyonları girdiyi parametre olarak alır; çağrıdaki argümanın hangi parametreye bağlandığını anlamak politika denetimini takip etmeyi sağlar.
- `ai-uretim-09` çözümündeki `lora_ileri(x, W0, A, B, alpha, r)` farklı sayısal parametrelerle çağrılır. Argüman sırası bu matrislerin ve katsayıların doğru yere gitmesi için önemlidir.
:::
