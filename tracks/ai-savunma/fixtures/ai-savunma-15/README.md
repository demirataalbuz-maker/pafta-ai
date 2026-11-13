# ai-savunma-15 · Görünür Sentetik Örnek Veri

Bu klasördeki log satırları, kimlik bilgisi kapsamları ve broker istekleri **sentetiktir**. `sk-test-...` ve `pg-pass-...` değerleri gerçek anahtar değildir. Hiçbir sır deposu, broker ya da model çağrılmaz.

## veri/log_kayitlari.json (Görev 1)

Altı kayıt vardır. Beklenen rapordan önemli satırlar:

- `http-log`: Aynı token iki satırda geçer → `bulgu: 2`.
- `onek-cakisma`: `sk-test-AB12` ile `sk-test-AB12CD34` birbirinin önekidir. Uzun olan önce maskelenmezse `[GIZLI]CD34` gibi bir kuyruk açıkta kalır.
- `iki-sir`: Farklı iki sır aynı satırda.
- `bolunmus` ve `buyuk-harf`: `bulgu: 0`. Sır satır sonuyla bölünmüş ya da büyük harfle yazılmıştır, birebir eşleşme bulmaz. Bu, **maskelemenin bilinen sınırıdır**. Bu yüzden asıl savunma sırrı bağlama hiç koymamaktır.

Dört bozuk girdi `ValueError` almalıdır: yinelenen kimlik, 3 karakterlik sır, satır sonu içeren sır ve yinelenen sır.

## veri/kapsamlar.json (Görev 2)

Dokuz kapsam vardır. Zamanlar **milisaniyedir**.

- **Geçerli:** `k-01` (300 ms) ve `k-02` (1 ms, veriliş 0).
- **`ValueError`:**
  - `k-03`: 300 **saniye**. Birim karışıklığı.
  - `k-04`: `model_gorebilir: true`.
  - `k-05`: `model_gorebilir: 0`; bool değil.
  - `k-06`: Joker kaynak.
  - `k-07`: `sil` eylemi.
  - `k-08`: Boş kaynak listesi.
  - `k-09`: Son geçerlilik verilişten önce.

## veri/broker_istekleri.json (Görev 3)

Kapsam, `simdi_ms = 10300` (son geçerlilik anının kendisi) ve altı istek vardır.

- `mesru` → `izin`, referans `kisa-omurlu-belirtec`. Gerçek sır **asla** dönmez.
- `baska-kaynak` ve `baska-eylem` → `kapsam`.
- `dogrudan` → `kanal`.
- `tekrar` → `tekrar`.
- `hepsi` → üç neden.
- `gec_kalan`: 1 ms sonra (10301) aynı meşru istek `zaman` nedeniyle reddedilir.

Dört bozuk girdi `ValueError` almalıdır.

## Kalıcılık ve kontrol

Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar; **kalıcılık yoktur**. Kontrol adımı bu dosyalardan bağımsız, gizli verilerle sınar. Son adım bu dosyaları kullanmaz; yerel modelin ürettiği metinleri, sandbox'ın her çalıştırmada ürettiği sentetik sırla maskeler.
