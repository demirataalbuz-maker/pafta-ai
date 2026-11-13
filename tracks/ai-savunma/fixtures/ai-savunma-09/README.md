# ai-savunma-09 · Görünür Sentetik Örnek Veri

Bu klasördeki metinler, dönüşüm örnekleri ve DLP olayları **sentetiktir**. Gerçek kişi verisi değildir:

- E-postalar `example.test` ve benzeri örnek alanlardadır.
- IP adresleri RFC 5737 dokümantasyon aralığındadır (`192.0.2.0/24`).
- Kartlar bilinen ödeme testi numaralarıdır.
- Telefon numarası yapaydır.

Hiçbir model ya da dış servis çağrılmaz.

## veri/pii_metinleri.json (Görev 1)

On bir metin vardır. `beklenen` değeri varlık listesidir (yalnız tür ve ofset; değer yok). `null`, `ValueError` demektir.

- **Bulunanlar:**
  - `p-01`: Dört tür birden.
  - `p-06`: Tireli Mastercard test numarası.
  - `p-07`: 13 haneli kart.
  - `p-10`: Virgülle ayrılmış iki e-posta.
- **Bulunmayanlar:**
  - `p-03`: `256.10.0.1`; aralık dışı IP parçası.
  - `p-04`: `1.2.3.4.5` sürüm numarası.
  - `p-05`: Luhn'u geçmeyen 16 hane.
  - `p-08`: Biçimi farklı telefon. Dar tanıyıcının **bilinçli sınırıdır**.
  - `p-09`: Uzantısız `admin@localhost`.
- `p-11`: NUL içeren metin → `ValueError`.

## veri/donusum_ornekleri.json (Görev 2)

Dokuz örnek vardır.

- `d-01`: Standart politika. Sonuç: `[PII:eposta] ************1111 [PII:telefon] 192.0.2.10`, `islem_sayisi: 3`. IP korunduğu için sayılmaz.
- `d-02`, `d-03`: Her şey redakte (4 işlem) ve her şey korunur (0 işlem).
- `d-04`: `123` dört karakterden kısadır, tamamen `***` olur.
- `d-05`: Bitişik iki aralık.
- `d-06` … `d-09` → `ValueError`: çakışan aralık, eksik politika türü, `sil` eylemi, metin dışına taşan bitiş.

## veri/dlp_olaylari.json (Görev 3)

Dokuz olay vardır.

- **Log kanalı:** Herhangi bir PII varsa durdurulur. IP de buna dahildir (`log-ip`).
- **Dış API:**
  - Kart varsa durdurulur (`api-kart`).
  - Yalnız telefon varsa redakte edilir.
  - Yalnız IP varsa incelemeye gider.
- **Yanıt kanalı:** Kart redakte edilir, IP serbesttir.
- **Boş varlık:** Her kanalda geçer.

Dört bozuk girdi `ValueError` almalıdır: yinelenen kimlik, bilinmeyen kanal, yinelenen tür ve bilinmeyen `tc_kimlik` türü.

## Kalıcılık ve kontrol

Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar; **kalıcılık yoktur**. Kontrol adımı bu dosyalardan bağımsız, gizli verilerle sınar. Son adım bu dosyaları kullanmaz; yerel modelin sentetik bir kayıttan ürettiği gerçek çıktıyla çalışır.
