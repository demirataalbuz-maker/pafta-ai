---
id: p29
title: Veri Biçimleri · JSON, CSV, SQLite
summary: json ile serileştirme, csv okuma-yazma ve parametreli SQL sorgusuyla injection'dan korunma.
kazanim: PCPP1 4.3, PCPP1 5.1, PCPP1 5.2
---

::: anlat JSON: makinelerin ortak dili
API'ler, log toplayıcılar, yapılandırma dosyaları... Sıklıkla **JSON** kullanılır. `json` modülü Python nesnelerini JSON metnine (**serileştirme**) ve geri (**ayrıştırma**) çevirir:

| Python | JSON |
|---|---|
| `dict` | nesne `{}` |
| `list`, `tuple` | dizi `[]` |
| `str` | metin |
| `int`, `float` | sayı |
| `True` / `False` | `true` / `false` |
| `None` | `null` |

```python
import json

olay = {"kullanici": "Ayşe", "basarili": False, "portlar": [22, 443], "not": None}
metin = json.dumps(olay)                              #! Python → JSON metni
print(metin)
print(json.dumps(olay, ensure_ascii=False, indent=2)) #! Türkçe karakterler + girinti
geri = json.loads('{"ip": "10.0.0.7", "deneme": 5}')  #! JSON metni → Python
print(geri["deneme"] + 1)

with open("olay.json", "w", encoding="utf-8") as f:   #! dump/load: dosyaya/dosyadan
    json.dump(olay, f, ensure_ascii=False)
with open("olay.json", encoding="utf-8") as f:
    print(json.load(f)["portlar"])
```

İsimlendirme: **s**'li olanlar (`dumps`, `loads`) **string** ile, s'siz olanlar dosya ile çalışır.

**JSON Lines** (`.jsonl`): her satır ayrı bir JSON nesnesidir. Log ve olay akışları için standarttır, çünkü dosyayı satır satır okuyabilirsin:

```python
import json
satirlar = ['{"tur": "giris", "k": "ali"}', '{"tur": "cikis", "k": "ali"}']
for s in satirlar:
    olay = json.loads(s)
    print(olay["tur"], olay["k"])
```

> [!TUZAK]
> JSON'da demet yoktur (listeye döner), sözlük anahtarları **her zaman metindir** (`{1: "a"}` → `{"1": "a"}`) ve `datetime` gibi nesneler doğrudan serileştirilemez (`TypeError`). Bozuk JSON `json.JSONDecodeError` verir; dışarıdan gelen veride bunu yakala.

> [!GÜVENLİK]
> Güvenilmeyen veriyi **asla `pickle` ile açma**. `pickle.loads` keyfi kod çalıştırabilir; saldırganın hazırladığı bir pickle dosyası makineni ele geçirir. JSON ayrıştırmak pickle gibi doğrudan nesne kodu çalıştırmaz. Buna rağmen boyut/derinlik sınırı, veri şeması ve sonraki kullanımın güvenliği ayrıca kontrol edilmelidir. Aynı uyarı `yaml.load` için de geçerlidir (`yaml.safe_load` kullan).
:::

::: tahmin
İki satır:

```python
import json
veri = {"ad": "Ayşe", "yetkiler": ["oku"], "aktif": True, "not": None}
print(json.dumps(veri, ensure_ascii=False))
print(json.loads('[1, 2.5, "x", false, null]'))
```

???

`{"ad": "Ayşe", "yetkiler": ["oku"], "aktif": true, "not": null}` ve `[1, 2.5, 'x', False, None]`. İlki **JSON metnidir** (çift tırnak, true, null). İkincisi ayrıştırılmış bir **Python listesidir** ve Python'un kendi gösterimiyle basılır.
:::

::: anlat CSV ve parametreli SQL
**CSV**: virgülle ayrılmış tablo. Elle `split(",")` yapma; değerin içinde virgül ya da tırnak olabilir. `csv` modülü bunları doğru işler:

```python
import csv

with open("kullanicilar.csv", "w", newline="", encoding="utf-8") as f:   #! newline="" şart
    w = csv.writer(f)
    w.writerow(["ad", "rol", "not"])
    w.writerow(["ali", "admin", "yetkili, dikkat"])     #! içinde virgül var
    w.writerow(["veli", "user", ""])

with open("kullanicilar.csv", newline="", encoding="utf-8") as f:
    for satir in csv.DictReader(f):                     #! başlık satırı → sözlük anahtarları
        print(satir["ad"], "|", satir["rol"], "|", satir["not"])
```

### SQL: f-string değil, parametre
P05'teki uyarının uygulaması. Python yerleşik bir veritabanıyla gelir: `sqlite3`.

```python
import sqlite3

db = sqlite3.connect(":memory:")                     #! bellekte geçici veritabanı
db.execute("CREATE TABLE k (ad TEXT, rol TEXT)")
db.executemany("INSERT INTO k VALUES (?, ?)", [("ali", "user"), ("root", "admin")])

girdi = "x' OR '1'='1"                               #! kötü niyetli kullanıcı girdisi
kotu = f"SELECT ad, rol FROM k WHERE ad = '{girdi}'"
print(kotu)                                          #! sorgunun ANLAMI değişti
print(db.execute(kotu).fetchall())                   #! bütün tablo döndü!

iyi = db.execute("SELECT ad, rol FROM k WHERE ad = ?", (girdi,)).fetchall()
print(iyi)                                           #! [] — girdi sadece VERİ olarak kaldı
```

`?` yer tutucusunda değer, sorgu metnine **hiç karışmaz**: veritabanı sürücüsü sorguyu ve veriyi ayrı kanallardan iletir. Kullanıcı ne yazarsa yazsın sorgunun yapısını değiştiremez. `db.execute(...)` arka planda bir **imleç** (`Cursor`, `cur = db.cursor()`) döndürür; sonuçları `fetchone()` (tek satır) ya da `fetchall()` (tüm satırlar) ile okursun. Veri değiştiren CRUD işlemlerinde (`INSERT`, `UPDATE`, `DELETE`) diskteki bir veritabanında (`sqlite3.connect("veri.db")`) değişiklikleri kalıcı kılmak için işlem sonunda `db.commit()` (ya da `with db:` bloğu) ve kapanışta `db.close()` çağrılır.

> [!GÜVENLİK]
> SQL injection 25 yılı aşkın süredir en çok sömürülen açıklardan biri ve **tek bir alışkanlıkla** önlenir: sorguya değer **asla** metin birleştirme ya da f-string ile girmez. Tablo ve sütun adları parametre olamaz; onları dinamik seçmen gerekiyorsa sabit bir izin listesinden seç.
:::

::: tahmin
Çıktı tek satır:

```python
import sqlite3
db = sqlite3.connect(":memory:")
db.execute("CREATE TABLE k (ad TEXT, rol TEXT)")
db.executemany("INSERT INTO k VALUES (?, ?)", [("ali", "user"), ("root", "admin")])
girdi = "x' OR '1'='1"
kotu = db.execute(f"SELECT ad FROM k WHERE ad = '{girdi}'").fetchall()
iyi = db.execute("SELECT ad FROM k WHERE ad = ?", (girdi,)).fetchall()
print(len(kotu), len(iyi))
```

???

`2 0`. f-string'li sorgu `WHERE ad = 'x' OR '1'='1'` olur; `'1'='1'` her satırda doğru olduğu için iki satır da döner. Parametreli sorgu ise `x' OR '1'='1` adında bir kullanıcı arar ve bulamaz.
:::

::: gorev Olay türü sayımı
`olaylar.jsonl` dosyasında her satır bir JSON olayı. Dosyayı `encoding="utf-8"` ile aç; her olayın `"tur"` alanına göre kaç olay olduğunu say ve sonucu **anahtarları sıralı** bir JSON metni olarak tek satırda yazdır (`json.dumps(..., sort_keys=True)`). Bozuk (JSON olmayan) satırları atla. Bu alıştırmada geçerli JSON satırları `tur` alanı metin olan olay sözlükleridir; genel JSON şema doğrulaması bu görevin kapsamında değildir.

```setup
satirlar = [
    '{"tur": "giris", "k": "ali", "basarili": true}',
    '{"tur": "giris", "k": "root", "basarili": false}',
    'BOZUK SATIR {{',
    '{"tur": "dosya", "k": "ali", "yol": "/etc/shadow"}',
    '{"tur": "giris", "k": "veli", "basarili": true}',
    '',
    '{"tur": "cikis", "k": "ali"}',
]
with open("olaylar.jsonl", "w", encoding="utf-8") as f:
    f.write("\n".join(satirlar) + "\n")
```

```starter
import json
sayim = {}
with open("olaylar.jsonl", encoding="utf-8") as f:
    for satir in f:
        olay = json.loads(satir)
        sayim[olay["tur"]] = sayim.get(olay["tur"], 0) + 1
print(json.dumps(sayim, sort_keys=True))
```

```test
eq(out.strip(), '{"cikis": 1, "dosya": 1, "giris": 3}', "sıralı JSON sayım")
ok(uses("try"), "bozuk satırlar için JSONDecodeError yakala")
import ast as _ast
_opens = [n for n in _ast.walk(_ast.parse(src)) if isinstance(n, _ast.Call) and getattr(n.func, "id", "") == "open"]
ok(bool(_opens) and all(any(k.arg == "encoding" for k in n.keywords) for n in _opens), "open çağrısında encoding='utf-8' belirt")
with open("olaylar.jsonl", "w", encoding="utf-8") as f:
    f.write('BOZUK\n\n{"tur":"z"}\n{"tur":"a"}\n{"tur":"z"}')
eq(run().strip(), '{"a": 1, "z": 2}', "bozuk/boş satır ve değişen türler")
with open("olaylar.jsonl", "w", encoding="utf-8") as f:
    f.write("")
eq(run().strip(), "{}", "boş olay dosyası")
```

```solution
import json

sayim = {}
with open("olaylar.jsonl", encoding="utf-8") as f:
    for satir in f:
        try:
            olay = json.loads(satir)
        except json.JSONDecodeError:
            continue
        sayim[olay["tur"]] = sayim.get(olay["tur"], 0) + 1
print(json.dumps(sayim, sort_keys=True))
```

```hint
Her satırı `json.loads` ile dene; `except json.JSONDecodeError: continue`. Boş satır da JSONDecodeError verir.
```
:::

::: gorev Yöneticiler
`kullanicilar.csv` dosyasında `ad,rol,son_giris` sütunları var. Dosyayı `newline=""` ve `encoding="utf-8"` ile açıp `csv.DictReader` kullan; rolü `admin` olanların adlarını **alfabetik sırayla** virgülle birleştirip yazdır.

```setup
import csv
with open("kullanicilar.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["ad", "rol", "son_giris"])
    w.writerows([["zeynep", "admin", "2026-10-18"], ["ali", "user", "2026-10-19"],
                 ["Baran, Kaya", "admin", "2026-09-01"], ["ayse", "admin", "2026-10-19"],
                 ["veli", "user", ""]])
```

```starter
import csv
with open("kullanicilar.csv", encoding="utf-8") as f:
    next(f)
    adlar = [s.split(",")[0] for s in f if s.split(",")[1] == "admin"]
print(",".join(sorted(adlar)))
```

```test
eq(out.strip(), "Baran, Kaya,ayse,zeynep", "adminler alfabetik (içinde virgül olan ad dahil)")
ok(calls("DictReader"), "csv.DictReader kullan")
import ast as _ast
_opens = [n for n in _ast.walk(_ast.parse(src)) if isinstance(n, _ast.Call) and getattr(n.func, "id", "") == "open"]
ok(bool(_opens) and all({k.arg for k in n.keywords} >= {"newline", "encoding"} for n in _opens), "csv dosyasını newline='' ve encoding='utf-8' ile aç")
import csv
with open("kullanicilar.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["ad", "rol", "son_giris"])
    w.writerows([["z", "user", ""], ["a", "admin", ""], ['b"c', "admin", ""]])
eq(run().strip(), 'a,b"c', "tırnaklı alan ve yeni kayıtlar")
with open("kullanicilar.csv", "w", encoding="utf-8", newline="") as f:
    csv.writer(f).writerow(["ad", "rol", "son_giris"])
eq(run().strip(), "", "başlık var, kullanıcı yok")
```

```solution
import csv

with open("kullanicilar.csv", newline="", encoding="utf-8") as f:
    adminler = sorted(s["ad"] for s in csv.DictReader(f) if s["rol"] == "admin")
print(",".join(adminler))
```

```hint
`for s in csv.DictReader(f): if s["rol"] == "admin": ...` sonra `sorted` ve `",".join`.
```

```hint
"Baran, Kaya" adında virgül var; `split(",")` ile ayrıştırsaydın bozulurdu. csv modülü tırnaklı alanı doğru okur.
```
:::

::: gorev Injection'a dayanıklı sorgu
`rol_bul(db, ad)` fonksiyonunu yaz: `k` tablosunda verilen adın rolünü döndürsün, yoksa `None` döndürsün. Sorguyu **parametreli** yaz; kötü niyetli girdiler sonuç döndürmemeli.

```starter
def rol_bul(db, ad):
    satir = db.execute(f"SELECT rol FROM k WHERE ad = '{ad}'").fetchone()
    return satir[0] if satir else None
```

```test
import sqlite3
need("rol_bul")
db = sqlite3.connect(":memory:")
db.execute("CREATE TABLE k (ad TEXT, rol TEXT)")
db.executemany("INSERT INTO k VALUES (?, ?)", [("ali", "user"), ("root", "admin"), ("o'brien", "user")])
eq(rol_bul(db, "root"), "admin", "root → admin")
eq(rol_bul(db, "yok"), None, "olmayan → None")
eq(rol_bul(db, "o'brien"), "user", "adında tırnak olan kullanıcı da bulunmalı")
eq(rol_bul(db, "x' OR '1'='1"), None, "injection girdisi → None")
eq(rol_bul(db, "' UNION SELECT 'admin' --"), None, "UNION injection → None")
ok("?" in src or ":" in src, "parametreli sorgu (? yer tutucusu) kullan")
```

```solution
def rol_bul(db, ad):
    satir = db.execute("SELECT rol FROM k WHERE ad = ?", (ad,)).fetchone()
    return satir[0] if satir else None
```

```hint
`db.execute("SELECT rol FROM k WHERE ad = ?", (ad,))`. Parametre demeti tek elemanlıysa virgülü unutma: `(ad,)`.
```
:::


::: anlat Yaygın yanlışlar
| Yanlış yaklaşım | Neden kırılır? | Doğrusu |
|---|---|---|
| CSV alanlarını virgülden bölmek | Tırnaklı alanın içindeki virgül de bölünür. | `csv.DictReader` kullan. |
| JSON ayrıştıysa veriye güvenmek | Geçerli JSON yanlış şema veya aşırı büyük veri olabilir. | Girdi sözleşmesini ve kaynak sınırlarını ayrıca doğrula. |
| SQL değerini f-string ile eklemek | Veri sorgu sözdizimine dönüşebilir. | `?` ve parametre demeti kullan. |
:::

::: anlat AI derslerinde nerede?
- `ai-saldiri-11` çözümünde `json.loads(paket)` ile belge paketi okunur; ayrıştırma hatası ile şema hatası ayrı kontrol edilir.
- `ai-saldiri-17` gerçek model adaptörünün setup kodunda HTTP cevabı `json.loads` ile okunur, sonra modelin JSON cevabındaki `cagrilar` alanı alınır.
:::
