# ai-savunma-23 · Görünür Sentetik Örnek Veri

Bu klasördeki dosyalar **tamamen sentetiktir**. Gerçek bir Elastic dışa aktarımı, gerçek kullanıcı ya da gerçek trafik değildir.

## `veri/abuse_politikasi.json`

`politika` şu değerleri tanımlar:

| Ayar | Değer |
|---|---|
| Pencere | 60 sn |
| Jailbreak eşiği | 3 |
| Araç eşiği | 5 |
| Sızıntı eşiği | 1 |
| Bekleme | 30 sn |

`bozuk_politikalar` reddedilmesi gereken dört kayıt içerir:

- 0 eşik
- 1 saatlik pencere
- bool bekleme
- eksik alan

## `veri/olay_akisi.json`

Altı kullanıcı var. Her biri ayrı bir dersi gösterir:

| Kullanıcı | Ne gösterir | Doğru karar |
|---|---|---|
| `u-ali` | **Yavaş saldırgan.** Üç jailbreak denemesini 70'er saniye arayla yapar. Pencerede yalnız 1 deneme kalır. | `izle` |
| `u-bot` | Araç eşiğine tam eşit 5 araç çağrısı. | `beklet` |
| `u-mert` | İlk jailbreak, son olaydan tam 60000 ms öncedir; sınırda sayılır. Toplam 3 deneme. | `beklet` |
| `u-selin` | 2 jailbreak ve 1 sızıntı. Sızıntı önceliklidir. | `engelle`, 60 sn bekleme |
| `u-ece` | Yalnız normal olaylar. | `izin` |
| `u-can` | Eski bir jailbreak var, ama sonraki normal olay referans zamanını ileri taşır. Jailbreak pencere dışına düşer. | `izin` |

`bozuk_olaylar` reddedilmesi gereken dört kayıt içerir:

- tanımsız `spam` türü
- negatif zaman
- boşluklu kullanıcı adı
- bool zaman

## Çalıştırma

- Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar. **Kalıcılık yoktur.**
- Kontrol adımı bu dosyalardan bağımsız, gizli verilerle sınar.
- Son adımdaki gerçek deney bu dosyaları kullanmaz. O adımda girdiler gerçek kural tespitinden ve yerel Ollama modelinin gerçek yanıtlarından geçer.
