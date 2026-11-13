# ai-saldiri-22 · Görünür Sentetik Örnek Veri

Bu klasördeki dosyaların hepsi **sentetiktir**. Hiçbir adrese ağ isteği gönderilmez. `public.test` ve `internal.test` uydurma adlardır. `169.254.169.254` bulut metadata servisinin bilinen adresidir; burada yalnız örnek olarak geçer.

## veri/url_ornekleri.json

On URL var. Doğru sonuçlar:

| URL | Sonuç |
|---|---|
| `http://public.test:80/belge?x=1` | `http://public.test:80` |
| `http://PUBLIC.test.:80/a` | `http://public.test:80` (küçük harf, sondaki nokta silinir) |
| `http://169.254.169.254:80/...` | Biçim olarak **geçerli** bir origin üretir. Bunu reddetmek origin üretmenin değil, izin listesinin işidir. |
| `http://public.test/ok` | Red: açık port yok |
| `https://...` | Red: yalnız `http` kabul edilir |
| `http://user@...` | Red: userinfo |
| `...#bolum` | Red: fragment |
| `http://public.test:80\@internal.test/` | Red: ters eğik çizgi. Farklı ayrıştırıcılar bu URL'de farklı host görür. |
| `:0` portlu URL | Red |
| `[::1]` | Red: IPv6 bu politikanın dışında |

## veri/redirect_zincirleri.json

İzinli origin `http://public.test:80`, en fazla 3 yönlendirme.

| Zincir | Sonuç |
|---|---|
| `ayni-origin` | 2 yönlendirme, kabul |
| `ag-yolu-referansi` | `//internal.test:80/...` hostu değiştirir; red |
| `port-degisimi` | Red |
| `buyuk-harf-host` | `PUBLIC.TEST.:80` kanonik biçimde aynı origin'dir; kabul |
| `hop-asimi` | 4 yönlendirme; red |
| `ikinci-hopta-kacis` | İlk yönlendirme izinli, ikincisi metadata adresine gider; bütün zincir reddedilir |

## veri/dns_kayitlari.json

Beş vaka ve üç bozuk kayıt var.

| Vaka | Sınıf |
|---|---|
| `v-temiz` | temiz |
| `v-rebinding` | cevap değişti ve izinsiz IP döndü; socket son cevaba gittiği için socket sapması **yok** |
| `v-ara-cevap` | ilk ve son cevap aynı ama aradaki cevap iç ağ adresi; rebinding ve yetkisiz DNS |
| `v-socket-sapma` | DNS temiz ama socket metadata IP'sine bağlanmış |
| `v-hep-ic` | cevap tutarlı ama izinsiz; yalnız yetkisiz DNS |

Bozuk kayıtlar: IPv6, boş çözüm listesi, IP yerine hostname.

## Kalıcılık ve kontrol

Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar, yani **kalıcılık yoktur**. Kontrol adımı bu dosyalardan bağımsız, gizli verilerle sınar.

Son adımın düzenlenebilir dosyası ayrıdır: `web/data/ai-saldiri-22-url-vakalari.txt`. Bu dosyanın kalıcı kopyası `calisma/ai-saldiri-22/url-vakalari.json` yolunda tutulur.
