# ai-saldiri-04 · Görünür Sentetik Örnek Veri

Bu klasördeki metinler **sentetik ve zararsızdır**. `önceki talimatı yok say`, `<|SYSTEM|>`, `Developer Mode` ya da Base64 parçaları sınıflandırılacak veridir; uygulanacak talimat değildir. Base64 parçaları yalnız `SELAM DENEME` ve `test-key-only` gibi zararsız metinleri kodlar.

## veri/metinler.json (Görev 1)

On iki metin vardır. Her birinin `beklenen` alanında, alfabetik sıralı sinyal listesi bulunur.

| Örnek | Beklenen | Neden |
|---|---|---|
| `t-01` | `base64` | `Base64` sözcüğü ve 16 karakterlik token |
| `t-02` | — | `abcbase64xyz`: sözcük içinde geçen `base64` sinyal değildir |
| `t-03` | `base64`, `hex` | `0x48656c6c6f2c21`: 14 hex hanesi; aynı token 16 karakterlik Base64 benzeri token da sayılır |
| `t-04` | — | `0x414243` çok kısa |
| `t-05` | `sahte-rol` | `<\|SYSTEM\|>` ve `Developer Mode`, `casefold()` ile bulunur |
| `t-06` | `kurgu` | `senaryo`, `hypothetical` |
| `t-07` | `onceki-talimati-yok-say` | `ÖNCEKİ`: `casefold()` ile `İ` harfi `i` + birleşik nokta olur; nokta atılmadan eşleşmez |
| `t-08` | — | `yok say` tek başına yetmez |
| `t-09` | — | Yalnız rakamdan oluşan token Base64 adayı değildir |
| `t-10` | dört sinyal | `Admin onaylı`, `roleplay`, `önceki talimatı yok say`, `base64` |
| `t-11` | `base64` | `=` dolgulu token |
| `t-12` | `hex`, `kurgu`, `sahte-rol` | `<\|developer\|>`, `hex` sözcüğü, `kurgu` |

İki bozuk girdi (`null`, `42`) `ValueError` almalıdır.

## veri/vakalar.json (Görev 2)

Altı vaka ve dosyanın `beklenen` alanında çok etiketli sonuç vardır. `v-03` üç etiket taşır. `v-05` aynı sinyali iki kez içerir ve tek `donusturme` etiketi üretir. `v-06` ise `kurgu` ile `sahte-rol` sinyallerini tek `baglam-manipulasyonu` etiketine indirir.

Dört bozuk küme `ValueError` almalıdır: bilinmeyen sinyal, boş kimlik, `null` metin ve yinelenen kimlik. Girdi listesi ve sinyal listeleri değişmemelidir.

## veri/olcum_vakalari.json (Görev 3)

Yedi vakada elle verilmiş `beklenen` etiketler ve bir sınıflandırıcının `tahmin` etiketleri vardır. Dosyanın `beklenen` alanında sınıf bazlı rapor bulunur. Dikkat:

- `politika-catistirma` hiç tahmin edilmemiştir. `tp+fp=0` olduğu için precision `null` olur. Recall ölçülebilir ve `0.0` çıkar. Oranlardan biri `null` olduğu için F1 de `null` olur. Burada `0.0` yazmak, ölçülemeyen bir değeri başarısız gibi gösterir.
- `donusturme` sınıfında `o-03` bir yanlış pozitif üretir: `dogrudan-istek` ile birlikte tahmin edilmiştir.

İki bozuk küme `ValueError` almalıdır: rapor dışı tahmin etiketi ve rapor dışı beklenen etiket.

## Kalıcılık ve kontrol

Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar; **kalıcılık yoktur**. Kontrol adımı bu dosyalardan bağımsız, gizli verilerle sınar.

Son adımın kendi dosyası ayrıdır: `web/data/ai-saldiri-04-vakalar.jsonl`. Bu dosyanın kalıcı kopyası `calisma/ai-saldiri-04/vakalar.jsonl` yolunda tutulur.
