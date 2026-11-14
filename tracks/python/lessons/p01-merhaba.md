---
id: p01
title: Merhaba Python
summary: Program yukarıdan aşağı okunan bir tariftir; print, yorumlar ve hata okumak.
kazanim: PCEP 1.1, PCEP 1.2, PCEP 1.5
---

::: anlat Program bir tariftir
Bir Python programı, **yukarıdan aşağıya** sırayla okunan talimatlardır. Python'u çalıştırdığında yorumlayıcı (interpreter) dosyayı ilk satırdan başlayıp tek tek yürütür. Bu ilk örneklerde çağrılar sırayla tamamlanır. SyntaxError varsa dosya yürütülmeden önce durabilir.

Yazdığın dosyaya **kaynak kod** denir. C veya Go gibi dillerde bir **derleyici** (compiler) kaynak kodun tamamını çalıştırmadan önce doğrudan makine koduna çevirir; Python'da ise **yorumlayıcı** (interpreter) kaynak kodu okuyup adım adım yürütür. İnsan dilindeki her cümle Python komutu değildir: kelimelerin nasıl yazıldığına **sözcük yapısı** (lexis), parantez ve tırnak düzenine **sözdizimi** (syntax), kurallara uygun bir satırın ne iş yaptığına ise **anlam** (semantics) denir.

İlk aracın `print`: parantez içine ne verirsen ekrana yazar. Metinler **tırnak** içinde yazılır. Tek tırnak `'...'` ya da çift tırnak `"..."` fark etmez, yeter ki açtığın tırnakla kapat.

```python
print("Merhaba, dünya!")      #! tırnak içi = metin (str)
print('Tek tırnak da olur')
print(2026)                    #! sayılar tırnaksız yazılır
# Bu satır bir yorum: Python onu tamamen yok sayar
print("Bitti")                 #! satırlar sırayla çalışır
```

Metin tırnaklarının dışındaki `#` işaretinden satır sonuna kadar olan bölüm **yorumdur**: Yorum kod olarak yürütülmez; sana ve kodu okuyacak diğer insanlara nottur.

Sağdaki tezgahta bu kod duruyor. **▶ Çalıştır**'a bas (ya da `Ctrl+Enter`), sonra bir satırı değiştirip tekrar çalıştır. Öğrenmenin en hızlı yolu kurcalamak.

> [!DERİN]
> Python dosyayı satır satır "okuyup çalıştırıyor" gibi görünse de aslında önce tüm kodu **bytecode** denen ara bir dile derler, sonra o bytecode'u bir sanal makinede yürütür. Tezgahtaki **Bytecode** düğmesine basarsan bu çeviriyi görürsün: `print("Bitti")` satırı `LOAD_NAME print`, `LOAD_CONST 'Bitti'`, `CALL` gibi komutlara dönüşür. Şimdilik sadece bil: P66'de o makinenin içine gireceğiz.
:::

::: tahmin
Bu kod ekrana ne yazdırır?

```python
print("bir")
# print("iki")
print("üç")
```

???

`#` ile başlayan satır yorum olduğu için hiç çalışmaz. Çıktı iki satırdır: `bir` ve `üç`. Yorumu, bir satırı silmeden **geçici olarak devre dışı bırakmak** için de kullanırsın. Tezgahta `Ctrl+/` seçili satırları yoruma alır ya da yorumdan çıkarır.
:::

::: anlat print'in gizli ayarları: sep ve end
`print`'e virgülle ayrılmış birden fazla şey verebilirsin. Hepsini **arasına bir boşluk koyarak** yazar ve en sona **satır sonu** ekler.

Bu iki davranışın da bir adı var ve ikisi de değiştirilebilir:

- `sep` (ayraç): değerlerin arasına ne konacağı. Varsayılanı `" "` (bir boşluk).
- `end` (son): en sona ne ekleneceği. Varsayılanı `"\n"` (yeni satır).

```python
print("10", "0", "0", "1")                #! 10 0 0 1  (sep varsayılan: boşluk)
print("10", "0", "0", "1", sep=".")       #! 10.0.0.1
print("tarama", end="... ")               #! satır sonu yerine "... "
print("bitti")                            #! aynı satıra devam eder
print("a", "b", sep="")                   #! ab  (ayraç yok)
```

`"\n"` iki karakter gibi görünür ama tek bir karakterdir: **yeni satır**. Ters eğik çizgi `\` "sonraki harf özel" demektir. `\t` sekme (tab) karakteridir.

> [!NOT]
> `sep=` ve `end=` gibi `isim=değer` biçimindeki argümanlara **anahtar sözcüklü argüman** (keyword argument) denir. Fonksiyonlar paftasında (P21) bunların nasıl çalıştığını derinlemesine göreceğiz.
:::

::: tahmin
Çıktıyı satır satır yaz:

```python
print("a", "b", "c", sep="-")
print("x", end="")
print("y")
print("1", "2", sep="\n")
```

???

- `sep="-"` değerlerin arasına tire koyar: `a-b-c`
- `end=""` satır sonunu kaldırdığı için sonraki `print("y")` aynı satıra yazar: `xy`
- `sep="\n"` ayraç olarak yeni satır kullanır, yani `1` ve `2` alt alta çıkar.
:::

::: anlat Hata mesajı düşman değil, haritadır
Her programcı her gün hata yapar. İyi programcıyı ayıran şey **hata mesajını okuyabilmesidir**. Python bir hata gördüğünde durur ve sana üç şey söyler: **hangi satırda**, **ne tür bir hata** ve **neden**.

```python norun
print("Merhaba"       #! kapanmamış parantez → SyntaxError
Print("Merhaba")      #! büyük P → NameError: Print tanımlı değil
print(Merhaba)        #! tırnak yok → Python bunu bir değişken adı sanar
```

Bu örneği tezgaha alıp çalıştır. Altta **hata kartı** çıkacak: hatanın Türkçe açıklaması, tıklanabilir satır numarası ve varsa "bunu mu demek istedin?" önerisi gelir.

Üç temel hata türü:

| Hata | Anlamı | Tipik sebep |
|---|---|---|
| `SyntaxError` | Python kodu **okuyamadı** | eksik parantez, tırnak, iki nokta |
| `NameError` | bu **isim** tanımlı değil | yazım hatası, tırnağı unutmak |
| `TypeError` | **tür** uyuşmazlığı | metinle sayıyı toplamak |

> [!TUZAK]
> Python **büyük-küçük harfe duyarlıdır**. `print`, `Print` ve `PRINT` üç farklı isimdir. Sadece ilki tanımlıdır.

> [!GÜVENLİK]
> Hata mesajları saldırganın da haritasıdır. Bir web uygulaması kullanıcıya ham Python hata çıktısı (traceback) gösteriyorsa dosya yolları, kütüphane sürümleri ve bazen sorgular sızar. Bu, OWASP'ta "hassas bilgi ifşası" olarak geçer. Kendi araçlarında hatayı **sen** yakala ve kullanıcıya sade mesaj ver. Bunu P25'te öğreneceksin.
:::

::: gorev İlk satırın
Ekrana tam olarak şunu yazdır. Büyük harf, virgül ve ünlem dahil:

```cikti
Merhaba, Pafta!
```

Yazdıktan sonra **✓ Kontrol et**'e bas (`Ctrl+Shift+Enter`). Testler çıktını harfi harfine karşılaştırır.

```starter
# Kusurlu başlangıç: çıktıyı ve kullanılan işlemi görevle karşılaştır.
print("Merhaba Pafta!")
```

```test
eq(out, "Merhaba, Pafta!\n", "Çıktı tam olarak 'Merhaba, Pafta!' olmalı")
```

```solution
print("Merhaba, Pafta!")
```

```hint
`print("...")` yaz; tırnakların içine metni birebir koy.
```
:::

::: gorev Afiş
Bir güvenlik aracının açılış afişi gibi, şu üç satırı yazdır:

```cikti
=====
PAFTA
=====
```

```starter
# Kusurlu başlangıç: çıktıyı ve kullanılan işlemi görevle karşılaştır.
print("=====", "PAFTA", "=====")
```

```test
ok(len(lines) == 3, "Tam 3 satır olmalı", got=len(lines))
eq(lines, ["=====", "PAFTA", "====="], "Satırlar sırasıyla: =====, PAFTA, =====")
```

```solution
print("=====")
print("PAFTA")
print("=====")
```

```hint
Her satır için ayrı bir `print` kullanabilirsin.
```

```hint
Tek `print` ile de olur: `print("=====", "PAFTA", "=====", sep="\n")`
```
:::

::: gorev sep ile IP adresi
Dört sayı parçasını **tek bir `print` çağrısıyla** ve `sep` ayarını kullanarak `192.168.1.10` biçiminde yazdır. Parçaları ayrı ayrı ver: `"192"`, `"168"`, `"1"`, `"10"`.

```cikti
192.168.1.10
```

```starter
print("192", "168", "1", "10")
```

```test
import ast
eq(out, "192.168.1.10\n", "Çıktı 192.168.1.10 olmalı")
print_cagrilari = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "print"]
eq(len(print_cagrilari), 1, "Tek bir print çağrısı kullanılmalı")
ok(len(print_cagrilari) == 1 and len(print_cagrilari[0].args) == 4, "Dört sayı parçası ayrı argüman olarak verilmeli")
sep_var = any(isinstance(n, ast.keyword) and n.arg == "sep" for n in ast.walk(tree))
ok(sep_var, "print çağrısında sep= kullanılmalı")
ok('"192.168.1.10"' not in src and "'192.168.1.10'" not in src, "Adresi tek parça metin olarak yazmak yok — parçaları sep ile birleştir")
```

```solution
print("192", "168", "1", "10", sep=".")
```

```hint
`sep=` değerlerin arasına ne konacağını belirler. Nokta istiyorsun.
```
:::

::: anlat Yaygın yanlışlar
| Yanlış yaklaşım | Neden kırılır? | Doğrusu |
|---|---|---|
| `Print(...)` yazmak | İsimler büyük-küçük harfe duyarlıdır. | Yerleşik `print(...)` adını kullan. |
| Metni tırnaksız vermek | Python bunu bir isim olarak arar. | Sabit metni eşleşen tırnaklarla yaz. |
| `sep` ile `end` ayarını karıştırmak | Biri değerler arasına, diğeri çağrının sonuna eklenir. | IP parçalarını `sep="."` ile birleştir. |
:::

::: anlat AI derslerinde nerede?
- `ai-savunma-31` — Bütçe dersinde `print(...)` ile hesap sonucu gösterilir.
- `ai-savunma-32` — Guardrail dersinde eşik ve metrik sonuçları ekrana yazılır.

Bu bağlantılardaki sözlük, fonksiyon ve model ayrıntıları ileride öğrenilecek. Burada yalnız bu derste gördüğün Python parçasını tanıman yeterli.
:::
