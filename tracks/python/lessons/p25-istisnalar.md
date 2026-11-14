---
id: p25
title: İstisnalar · try / except
summary: Hatayı yakalamak; belirli istisnalar, else, finally, raise ve hata hiyerarşisi.
kazanim: PCEP 4.3, PCEP 4.4, PCAP 2.1
---

::: anlat Hatayı yakala, programı ayakta tut
Şimdiye kadar her hata programı durdurdu. Gerçek araçlar ise hatayı **yakalar** ve ne yapacağına karar verir. Python'da hata = **istisna** (exception) nesnesidir; `try` bloğunda bir istisna yükselirse akış, ona uyan `except` bloğuna atlar:

```python
girdiler = ["443", "http", "70000"]
for g in girdiler:
    try:
        port = int(g)                    #! burada ValueError yükselebilir
        print("port:", port)
    except ValueError:                   #! sadece bu türü yakala
        print(f"'{g}' sayı değil, atlandı")
print("program devam ediyor")
```

`try` bloğunda hata olduğu an bloğun geri kalanı **atlanır**, `except` çalışır ve akış `try/except`'ten sonra devam eder.

### Birden fazla except ve istisna nesnesi
```python
def oku(liste, i):
    try:
        return 100 // liste[i]
    except IndexError:
        return "indeks yok"
    except ZeroDivisionError as e:       #! as e: istisna nesnesinin kendisi (e.args mesaj demetidir)
        return f"bölme hatası: {e.args[0]}"
    except (TypeError, ValueError):      #! demetle birden çok tür
        return "tür sorunu"

print(oku([5, 0], 0), oku([5, 0], 1), oku([5, 0], 9), oku(["x"], 0))
```

İstisna nesnesi oluşturulduğunda verilen argümanları `e.args` demetinde saklar (`str(e)` bunu metne çevirir). `except` dalları **yukarıdan aşağıya sırayla** denenir; bu yüzden alt istisna türünü (`ZeroDivisionError`) her zaman üst türünden (`ArithmeticError` veya `Exception`) **önce** yazmalısın, yoksa üst dal tüm hataları yutar ve alttaki dala hiç ulaşılmaz.

> [!TUZAK]
> **Çıplak `except:`** ya da `except Exception:` yazıp her şeyi yutma. `except Exception` beklenmeyen `NameError` gibi programlama hatalarını da gizleyebilir. Çıplak `except:` ayrıca `KeyboardInterrupt` ve `SystemExit` gibi çıkış sinyallerini de yakalar; `except Exception` bunları yakalamaz. Programın yanlış çalışır ama neden olduğunu asla bilemezsin. **Sadece ne yapacağını bildiğin** istisnaları yakala.

> [!ZEN]
> Hatalar asla sessizce geçiştirilmemeli. Açıkça susturulmadıkça. (*Errors should never pass silently. Unless explicitly silenced.*)
:::

::: tahmin
Üç satır:

```python
for x in ["10", "abc", "0"]:
    try:
        print(100 // int(x))
    except ValueError:
        print("sayı değil")
    except ZeroDivisionError:
        print("sıfır")
```

???

`10`, `sayı değil`, `sıfır`. Her turda ayrı bir `try` çalışır. "abc" `int()`'te ValueError, "0" bölmede ZeroDivisionError verir.
:::

::: anlat else, finally ve raise
Tam yapı:

```python
def dosya_oku(ad):
    try:
        f = open(ad, encoding="utf-8")
    except FileNotFoundError:
        print("yok:", ad)
        return None
    else:                        #! open başarılı olduysa çalışır
        try:
            return f.read()
        finally:
            f.close()            #! okuma hatasında da dosyayı kapat
    finally:                     #! NE OLURSA OLSUN çalışır (return olsa bile)
        print("kontrol bitti:", ad)

dosya_oku("olmayan.txt")
```

- **`else`**: `try` bloğu hatasız bittiyse çalışır. `try`'ı kısa tutmanı sağlar: sadece hata beklediğin satır `try`'da, gerisi `else`'de.
- **`finally`**: her durumda çalışır: hata olsa, yakalansa, yakalanmasa, hatta `return` olsa bile. Kaynak temizliği (dosya, bağlantı, kilit) içindir. P27'de göreceğin `with` bunu otomatikleştirir.

### raise: hatayı sen yükselt
```python
def port_dogrula(p):
    if type(p) is not int:
        raise TypeError(f"port int olmalı, {type(p).__name__} geldi")
    if not 0 < p < 65536:
        raise ValueError(f"port aralık dışı: {p}")
    return p

try:
    port_dogrula(70000)
except ValueError as e:
    print("reddedildi:", e)
```

Geçersiz girdiyi **sessizce düzeltmek** yerine `raise` ile reddetmek, hatayı kaynağında yakalar. Bir fonksiyon içinde yakalanmayan istisna kaybolmaz; çağrı yığını boyunca çağıran fonksiyona, orada da yakalanmazsa en üste kadar **yayılır** (yukarıda `port_dogrula` içindeki `raise`'in dışarıdaki `try/except` tarafından yakalanması gibi). `except` içinde çıplak `raise` yazarsan yakalanan istisna olduğu gibi **yeniden yükseltilir** (logla ve yukarı ilet kalıbı).

> [!DERİN]
> İstisnalar bir **sınıf hiyerarşisidir**:
> - `BaseException` → `SystemExit`, `KeyboardInterrupt` ve `Exception`
> - `Exception` → `ArithmeticError` (`ZeroDivisionError`), `LookupError` (`IndexError`, `KeyError`), `TypeError`, `ValueError`
>
> Üst türü yakalamak alt türlerini de yakalar: örneğin `except LookupError:` hem liste `IndexError` hem sözlük `KeyError` hatalarını yakalar. `KeyboardInterrupt` ve `SystemExit` doğrudan `BaseException`'dan türer, `Exception`'dan değil; böylece `except Exception` Ctrl+C'yi yutmaz (`assert` deyimini ve kendi istisna sınıflarını P26'da göreceğiz). Tüm ağacı görmek için: `help(BaseException)` ya da Python belgelerindeki "Exception hierarchy" sayfası.

> [!GÜVENLİK]
> P01'de söz verdiğimiz konu: kullanıcıya **ham traceback gösterme**. Dosya yolları, sürümler ve iç mantık sızar. Doğru kalıp şudur: istisnayı yakala, ayrıntıyı **log'a** yaz, kullanıcıya genel bir mesaj ve bir olay numarası ver.
:::

::: tahmin
İki satır:

```python
def f():
    try:
        return "try"
    finally:
        print("finally")

print(f())
```

???

`finally`, sonra `try`. `return "try"` değeri hazırlar ama fonksiyon çıkmadan önce `finally` çalışır ve ekrana yazar. Sonra değer döner ve dışarıdaki `print` onu yazar. (finally içinde `return` yazarsan asıl dönüş değerini ezer. Bunu asla yapma.)
:::

::: gorev Güvenli dönüşüm
`guvenli_int(deger, varsayilan=0)` fonksiyonunu yaz: `int(deger)` başarılıysa sonucu, `ValueError` ya da `TypeError` olursa `varsayilan`'ı döndürsün.

```starter
def guvenli_int(deger, varsayilan=0):
    return int(deger)
```

```test
need("guvenli_int")
eq(guvenli_int("42"), 42, "'42' → 42")
eq(guvenli_int(" 7 "), 7, "' 7 ' → 7")
eq(guvenli_int("abc"), 0, "'abc' → 0")
eq(guvenli_int("abc", -1), -1, "varsayılan -1")
eq(guvenli_int(None, 5), 5, "None → TypeError yakalanmalı → 5")
eq(guvenli_int("3.5"), 0, "'3.5' → 0")
ok(uses("try"), "try/except kullan")
ok("except:" not in src.replace(" ", "") and "exceptException" not in src.replace(" ", ""), "Çıplak except ya da except Exception değil, belirli türleri yakala")
```

```solution
def guvenli_int(deger, varsayilan=0):
    try:
        return int(deger)
    except (ValueError, TypeError):
        return varsayilan
```

```hint
`except (ValueError, TypeError):` demetle iki türü birden yakalar.
```
:::

::: gorev Geçerli port gelene kadar
Girdiden satır satır oku. Bu alıştırmanın girdisinde en az bir geçerli port satırı vardır; o satırda durmalısın. Her satır için:

- Tam sayıya çevrilemiyorsa ya da 1–65535 dışındaysa `geçersiz` yaz ve sonraki satıra geç
- Geçerliyse `port: N` yaz ve dur

```starter
while True:
    satir = input()
    port = int(satir)
    print(f"port: {port}")
    break
```

```stdin
abc
70000
443
```

```test
eq(run("65536\n1\n80").strip().splitlines(), ["geçersiz", "port: 1"], "üst sınır dışı ve ilk geçerlide dur")
eq(run("abc\n70000\n443").strip().splitlines(), ["geçersiz", "geçersiz", "port: 443"], "abc, 70000, 443")
eq(run("22").strip(), "port: 22", "ilk satır geçerli")
eq(run("0\n-5\n65535").strip().splitlines(), ["geçersiz", "geçersiz", "port: 65535"], "sınırlar")
eq(run("8.5\n80").strip().splitlines(), ["geçersiz", "port: 80"], "ondalık geçersiz")
ok(uses("try"), "try/except kullan")
```

```solution
while True:
    satir = input()
    try:
        port = int(satir)
        if not 1 <= port <= 65535:
            raise ValueError("aralık dışı")
    except ValueError:
        print("geçersiz")
        continue
    print(f"port: {port}")
    break
```

```hint
Aralık kontrolünü de istisnaya çevirebilirsin: `raise ValueError(...)`. Böylece tek bir `except` iki durumu da yakalar.
```
:::

::: gorev Doğrulayıcı raise etsin
`yas_dogrula(yas)` fonksiyonunu yaz:

- `yas` int değilse (bool da kabul edilmez): `TypeError` yükselt
- 0–150 aralığı dışındaysa: `ValueError` yükselt
- Geçerliyse `yas`'ı döndür

```starter
def yas_dogrula(yas):
    if not isinstance(yas, int):
        raise TypeError("int gerekli")
    return yas
```

```test
need("yas_dogrula")
eq(yas_dogrula(30), 30, "30 → 30")
eq(yas_dogrula(150), 150, "üst sınır dahil")
eq(yas_dogrula(0), 0, "0 → 0")
raises(ValueError, yas_dogrula, -1, msg="-1 → ValueError")
raises(ValueError, yas_dogrula, 151, msg="151 → ValueError")
raises(TypeError, yas_dogrula, "30", msg="'30' → TypeError")
raises(TypeError, yas_dogrula, 30.0, msg="30.0 → TypeError")
raises(TypeError, yas_dogrula, True, msg="True → TypeError (bool, int'in alt sınıfı ama kabul etme)")
ok(uses("raise"), "raise kullan")
```

```solution
def yas_dogrula(yas):
    if type(yas) is not int:
        raise TypeError(f"yaş int olmalı, {type(yas).__name__} geldi")
    if not 0 <= yas <= 150:
        raise ValueError(f"geçersiz yaş: {yas}")
    return yas
```

```hint
`isinstance(True, int)` True döner, çünkü bool int'in alt sınıfıdır. Tam tür kontrolü için `type(yas) is not int`.
```
:::


::: anlat Yaygın yanlışlar
| Yanlış yaklaşım | Neden kırılır? | Doğrusu |
|---|---|---|
| `except Exception` ile her hatayı gizlemek | Programlama hatası da normal girdi hatası gibi görünür. | Yalnız beklenen istisna türlerini yakala. |
| Bool değerini yaş saymak | Bool, int alt türüdür. | Görev tam int istiyorsa `type(yas) is int` kontrol et. |
| `finally` içinde return kullanmak | Asıl dönüşü veya istisnayı bastırabilir. | Finally bloğunu temizleme için kullan. |
:::

::: anlat AI derslerinde nerede?
- `ai-savunma-19` çözümü geçersiz politika alanlarında `ValueError` yükseltir; hatalı girdiye normal sonuç üretmek yerine reddeder.
- `ai-uretim-09` çözümü matris boyutu ve geçersiz token kaybında `ValueError` yükseltir. Testler normal sonuç ile hata davranışını ayrı denetler.
:::
