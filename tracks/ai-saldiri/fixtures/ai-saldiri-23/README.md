# ai-saldiri-23 · Görünür Sentetik Örnek Veri

Bu klasördeki dosyaların hepsi **sentetiktir**. Hiçbir `.test` adına ağ isteği gönderilmez. `CANARY-7` gerçek bir sır değil, iz sürmek için kullanılan bir işaretçidir.

## veri/kanal_olaylari.json

Politika yalnız `http` ve `arac` kanallarına izin verir. İzinli hedefler `rapor.sirket.test` ve `log.sirket.test`'tir.

| Olay | Sonuç |
|---|---|
| `RAPOR.Sirket.test.` | Kanonik biçimi `rapor.sirket.test` olduğu için izinli |
| `dns` kanalı | `kanal-izinsiz` |
| `toplayici.saldirgan.test` | `hedef-izinsiz` |
| `log.sirket.test.saldirgan.test` | İzinli bir adla **başlar** ama başka bir alan adıdır: `hedef-izinsiz` |

`bozuk_olaylar` içinde dört olay var: `smtp` kanalı, `.com` hedefi, boş veri ve alt çizgili host. Bunlar reddedilmelidir.

## veri/alici_olaylari.json

Saldırganın alıcısında görülmüş altı olay vardır. Canary `CANARY-7`'dir.

| Olay | Ne gösterir |
|---|---|
| `e-01` | **Yanlış negatif.** Veri `q-canary-7` diye küçük harfle yazılmış. Substring araması büyük/küçük harfe duyarlı olduğu için iz bulunmaz. DNS etiketleri büyük/küçük harf ayırmaz. Gerçek kör sızdırmada bu yüzden veri kodlanır (gerçek deney base32 kullanır). |
| `e-02` | DNS kanalında canary var, yanıt yok. **Yanıtsız kanıt.** |
| `e-03` | Yanıt boş string (`""`). Bu "cevap yok" (`None`) ile aynı değildir; yanıtsız kanıt sayılmaz. |
| `e-05` | Canary var ama yanıt alınmış. |

`bozuk_olaylar` içinde `smtp` kanalı, sayı türünde yanıt ve ASCII dışı veri var. Bunlar reddedilmelidir.

## veri/regresyon_kayitlari.json

Yedi vaka var:

| Vaka | Durum |
|---|---|
| `v-sessiz` | İzinsiz, olay var, canary var, yanıt yok: **sessiz sızıntı** |
| `v-bypass-yanitli` | Politika bypass'ı, ama yanıt alınmış |
| `v-bypass-temiz-veri` | Politika bypass'ı, canary yok |
| `v-mesru-kor` | İzinli, ama yanıtsız kanıt örneği |
| `v-kayip` | İzinli ama olay gerçekleşmemiş |

`bozuk_kayitlar` içinde iki kayıt var: olay olmadığı hâlde canary görülmüş (tutarsız) ve bool yerine 1. Bunlar reddedilmelidir.

## Kalıcılık ve kontrol

Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar, **kalıcılık yoktur**. Kontrol adımı bu dosyalardan bağımsız, gizli verilerle sınar.

Son adımın düzenlenebilir dosyası ayrıdır: `web/data/ai-saldiri-23-kanallar.txt`. Bu dosyanın kalıcı kopyası `calisma/ai-saldiri-23/kanallar.json` yolunda tutulur.
