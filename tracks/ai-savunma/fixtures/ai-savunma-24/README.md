# ai-savunma-24 · Görünür Sentetik Örnek Veri

Bu klasördeki kurallar ve olaylar **sentetiktir**. Gerçek bir SOC kural seti, gerçek log ya da gerçek kimlik bilgisi değildir.

## veri/sigma/

Bu klasörde gerçek **Sigma YAML biçiminde** iki dosya var: `llm_injection.yml` ve `llm_egress_yetki.yml`. İçlerinde beş kural bulunur. Kuralların ortak özellikleri:

- `logsource` değeri `product: llm` ve `category: injection|egress|yetki`.
- Eşleşme `metin|contains` ile yapılır; bazı kurallarda `|all` belirleyicisi de vardır.
- `level` değerleri `high`, `medium` ve `critical`.

pySigma kural kimliğinin UUID olmasını zorunlu tutar, bu yüzden kimlikler UUID'dir. Dosyalar kurulu pySigma 2.0.1 ile ayrıştırılabilir.

## veri/kurallar.json

YAML dosyalarındaki beş kuralın ders şemasına (`id, baslik, seviye, alan, eslesmeler, kosul, aktif`) çevrilmiş hâli. Çeviri pySigma ile ayrıştırılarak yapıldı.

`bozuk_kurallar` listesinde doğrulamanın reddetmesi gereken dört kural var:

- pasif kural
- büyük harfli eşleşme
- yinelenen eşleşme
- `network` alanı

## veri/olaylar.json

On olay var. Bazıları kuralların **kaçırdığı** ya da **yanlış alarm verdiği** durumları bilerek gösterir:

| Olay | Sonuç | Neden |
|---|---|---|
| `e-02` | Alarm, seviye `yuksek` | İki kural eşleşir; en yüksek seviye seçilir. |
| `e-03` | Temiz (**yanlış negatif**) | Türkçe talimat ezme. |
| `e-04` | Temiz (**yanlış negatif**) | `https://` ile metadata servisine gidiyor; kural yalnız `http://` arıyor. |
| `e-05` | Temiz (**yanlış negatif**) | `169.254.169.254` IP adresi ve `meta-data` yazımı; kural `metadata` arıyor. |
| `e-08` | Alarm (**yanlış pozitif**) | Destek kaydı `ignore previous` uyarısını alıntılıyor. |
| `e-10` | Alarm, seviye `kritik` | Hem `kritik` metadata kuralı hem `orta` URL kısaltıcı kuralı eşleşir. Seviye öncelik sırasına göre seçilir, alfabetik sıraya göre değil. |
| `e-09` | Temiz | Metin injection kalıbı taşıyor ama alanı `yetki`; kural yalnız kendi alanına uygulanır. |

`bozuk_olaylar` listesinde reddedilmesi gereken dört olay var:

- `network` alanı
- başında boşluk olan metin
- TAB içeren metin
- boş metin

## Kalıcılık ve kontrol

Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar, **kalıcılık yoktur**. Kontrol adımı bu dosyalardan bağımsız, gizli verilerle sınar.

Son adımdaki gerçek deney kendi Sigma YAML'ını pySigma ile ayrıştırır. Olaylarını da yerel Ollama modelinin gerçek girdi, yanıt ve araç çağrısından üretir.
