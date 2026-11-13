# ai-saldiri-18 · Görünür Sentetik Örnek Veri

Bu klasördeki dosyaların hepsi **sentetiktir**. Gerçek bir kimlik sağlayıcı oturumu, gerçek belge veya gerçek ajan günlüğü değildir. `paylas:dis` kapsamı bu derste yalnız yerel bir sentetik arşivi temsil eder; dış ağa hiçbir veri gitmez.

## Dosyalar

### `veri/oturum_ve_belgeler.json`

- **Oturum:** Kimliği doğrulanmış kullanıcı `ayse`, rolleri `user` ve `readonly`.
- **Belgeler:** Üç belge var. İkisi yetki iddiası taşır:
  - `tedarikci-notu`: `rol=admin`, `onay=true`
  - `web-ozet`: `yetkili=evet`, `imza=BT-Mudurlugu`

  Bu beyanlar kanıt olarak saklanır ama **yetki vermez**.
- **`bozuk_girdiler`:** Reddedilmesi gereken dört kayıt var:
  - boş rol listesi
  - yinelenen rol
  - sayı değerli beyan
  - oturumda fazladan `token` alanı

### `veri/kapsamlar.json`

Dört delegasyon senaryosu var:

| Senaryo | Ne olur |
|---|---|
| `ayse-paylasim-istegi` | Klasik confused deputy. Ajan `paylas:dis` yetkisine sahip, kullanıcı değil. Sonuç: `ajan_asimi = ["paylas:dis"]`. |
| `editor-duzeltme` | Ters durum. Kullanıcı `yaz:rapor` yetkisine sahip, ajan değil. İstek reddedilir ama bu bir ajan aşımı değildir. |
| `tam-yetki` | İki taraf da izinlidir. |
| `bos-istek` | İstek listesi boştur. |

`bozuk_senaryolar` içinde `*`, büyük harfli kapsam ve yinelenen kapsam örnekleri var.

### `veri/vekil_kayitlari.json`

Ajanın eylem günlüğünden alınmış altı vaka var:

- **İçerikten tetiklenen ihlaller:** `v-tedarikci` (belgeden) ve `v-tool-zinciri` (tool çıktısından).
- **Kullanıcıdan gelen ihlal:** `v-yanlis-tikla`.
- **Engellenen yetkisiz istek:** `v-web-yazma`.
- **Yetkili ve çalıştırılmamış:** `v-bekleyen`. Bu kayıt engellenen sayılmaz.

`bozuk_kayitlar` içinde `system` kaynağı, `*` kapsamı ve bool yerine sayı örnekleri var.

## Kalıcılık ve kontrol

Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar; **kalıcılık yoktur**. Kontrol adımı bu dosyalardan bağımsız, gizli verilerle sınar.

Son adımın düzenlenebilir belgesi bu klasörde değil, `web/data/ai-saldiri-18-belge.txt` dosyasındadır. Bu belgenin kalıcı kopyası `calisma/ai-saldiri-18/belge.json` yolunda tutulur.
