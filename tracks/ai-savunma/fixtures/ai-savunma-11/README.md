# ai-savunma-11 · Görünür Sentetik Örnek Veri

Bu klasördeki dosyalar **tamamen sentetiktir**. Hiçbir araç gerçekten çalıştırılmaz. Dosya yolları, adresler ve yetkiler örnek amaçlıdır.

## veri/arac_semalari.json

Üç dar araç şeması (`dosya_oku`, `web_getir`, `rapor_yaz`) ve reddedilmesi gereken beş bozuk şema içerir:

- `genis-dosya-yetkisi`: Okuma aracı yazma yetkisi de istiyor.
- `yan-etki-gizli`: Yazma aracı `yan_etkili=false` olarak işaretlenmiş.
- `fazla-parametre`: `web_getir` aracına `yontem` parametresi eklenmiş.
- `genel-arac`: Tanımsız ve geniş bir `dosya_yonet` aracı.
- `sinirsiz-zaman`: Zaman aşımı 0.

## veri/arac_cagrilari.json

Bir modelin ürettiği gibi yazılmış 12 çağrı. Bunlardan yalnız `c-01`, `c-06` ve `c-11` geçerlidir. Diğerleri tek tek şu tuzakları gösterir:

| Çağrı | Tuzak |
|---|---|
| `c-02` | Yol gezintisi (`../../`) |
| `c-03` | Mutlak yol |
| `c-04` | Ters eğik çizgi ile Windows gezintisi |
| `c-05` | Sürücü harfi |
| `c-07` | HTTP |
| `c-08` | `@` ile kullanıcı bilgisi; gerçek hedef bulut metadata IP'si |
| `c-09` | Açık port |
| `c-10` | İzinli alan adıyla **başlayan** başka bir alan adı |
| `c-12` | Başında boşluk olan başlık |

## veri/yetki_istekleri.json

Araç başına istenen yetki ile oturum yetkilerini karşılaştıran beş istek. Her biri bir durumu gösterir:

- `i-oku`: Oturum geniş olsa da istek tam ve en az kapsamlı; çalıştırılır.
- `i-genis`: Fazla yetki istiyor.
- `i-yanlis`: Gerekli yetkiyi istemiyor, yerine başka bir yetki istiyor. Bu yüzden iki neden birden alır: `eksik_istek` ve `fazla_yetki`.
- `i-oturumsuz`: Gerekli yetki oturumda yok.
- `i-hepsi`: Üç neden birden.

`bozuk_istekler` içinde tanımsız bir araç, yinelenen bir yetki ve tanımsız `admin` yetkisi var; bunlar reddedilmelidir.

## Kalıcılık ve kontrol

Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar, yani **kalıcılık yoktur**. Kontrol adımı bu dosyalardan bağımsız, gizli verilerle sınar.

Son adımdaki gerçek deney bu dosyaları kullanmaz. O adımda araç çağrılarını yerel Ollama modeli gerçekten üretir.
