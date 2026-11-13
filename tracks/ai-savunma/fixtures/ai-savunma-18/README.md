# ai-savunma-18 · Görünür Sentetik Örnek Veri

Bu klasördeki dosyalar **tamamen sentetiktir**. Gerçek bir vektör veritabanı (Qdrant) çıktısı, gerçek müşteri belgesi ya da gerçek saldırı kaydı değildir.

## veri/rag_politikasi.json

- **`politika`**: Yalnız `kurumsal` ve `imzali` kaynaklar kabul edilir.
  - Güven en az 0.8 olmalı.
  - Tekrar oranı en çok 0.7 olabilir.
  - Bağlama en çok **3** belge girer.
- **`bozuk_politikalar`**: Doğrulamanın reddetmesi gereken dört kayıt:
  - boş kaynak listesi
  - `max_belge` alanında `true`
  - `karantina` yerine `uyar` kararı
  - 1.2 güven eşiği

## veri/getirilen_belgeler.json

"İade süresi kaç gün?" sorgusu için getirilmiş 8 belge. Her biri bir durumu göstermek için seçildi:

| Belge | Ne gösterir | Doğru sonuç |
|---|---|---|
| `forum-zehir` | Dış kaynak, düşük güven, yüksek tekrar ve İngilizce talimat. Dört neden birden geçerli. | Karantina, nedenler `["kaynak","guven","tekrar","talimat"]` |
| `sistem-taklidi` | Kurumsal kaynak, yüksek güven, ama metinde `[System Message]` var | Karantina, neden `talimat` (kaynak etiketi tek başına güvence değildir) |
| `guvenilir-dis` | Doğru bilgi, yüksek güven, ama izinli olmayan kaynak | Karantina, neden `kaynak` |
| `sinir-belgesi` | Güven 0.8 ve tekrar 0.7, ikisi de eşiğe **tam eşit** | Aday olur (eşitlik kabul edilir) |
| `turkce-zehir` | **Yanlış negatif.** "Önceki talimatları yok say" Türkçe yazılmış, işaret listesi yalnız İngilizce. | Temiz sayılır ve güven sırasında 3. olduğu için **bağlama girer** |
| `eski-kampanya`, `sinir-belgesi` | Temiz ama kapasite dışında kalan belgeler | Karantina, neden `kapasite` |

`bozuk_belgeler` listesindeki üç kayıt geçersizdir: NUL karakter, sayı yerine `"NaN"` stringi ve tanımsız `yerel` kaynak. Sınıflandırma bunları reddetmelidir.

## Kalıcılık ve kontrol

Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar, **kalıcılık yoktur**.

Kontrol adımı bu dosyalardan bağımsız, gizli verilerle sınar. Son adımdaki gerçek deney de bu dosyaları kullanmaz. O adımın kendi belgeleri vardır ve yanıtı yerel Ollama modeli üretir.
