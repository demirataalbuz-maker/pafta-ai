# ai-savunma-16 · Görünür Sentetik Örnek Veri

Bu klasördeki dosyalar **tamamen sentetiktir**. Gerçek bir Qdrant koleksiyonu, gerçek belge ya da gerçek gömme skoru değildir. `metin_sha256` değerleri örnek metinlerin gerçek SHA-256 özetleridir.

## veri/kaynak_defteri.json

Beş kaynak var:

| Kaynak | Güven | Not |
|---|---|---|
| `politika-wiki` | yüksek | Kurumsal, imzalı, aktif |
| `destek-sss` | orta | Sürüm `1.0.12`: bileşen iki basamaklı olabilir |
| `forum-arsivi` | düşük | Açık kaynak |
| `eski-kilavuz` | yüksek | **Pasif** |
| `kullanici-notu` | orta | **İmzasız** |

`bozuk_defterler` içinde beş defter var:

- Başında sıfır olan sürüm (`3.01.0`)
- `v` önekli sürüm
- Tanımsız güven düzeyi
- Bool yerine `1`
- Yinelenen kaynak kimliği

## veri/getirilen_parcalar.json

"İade süresi kaç gün?" sorgusu için getirilen yedi parça. Skorlar elle yazılmıştır. Parçalar ve doğru provenance:

| Parça | Skor | Doğru provenance |
|---|---|---|
| `p-tahrif` | 0.93 (en yüksek) | Defterde `3.1.0` olan kaynağın `3.1.1` sürümünü iddia ediyor. Neden: `surum`. |
| `p-yetim` | 0.88 | Defterde olmayan bir kaynaktan geliyor. Neden: `kaynak`, güven `bilinmiyor`. |
| `p-eski` | 0.79 | Yüksek güvenli ama pasif kaynak. Neden: `durum`. |
| `p-not` | 0.72 | İmzasız kaynak. Neden: `imza`. |
| `p-politika`, `p-sss`, `p-forum` | — | Doğrulanabilir. |

## veri/provenance_kayitlari.json

Yukarıdaki parçalardan üretilmiş provenance kayıtları. `orta` eşiğinde doğru seçim, skor sırasıyla `p-politika` ve `p-sss` olur. En yüksek skorlu dört parçanın üçü seçime **girmez**. `dusuk` eşiğinde `p-forum` da eklenir.

`bozuk_kayitlar` içinde üç kayıt var:

- `dogrulanabilir=True` ama neden listesi dolu (çelişkili)
- Yinelenen neden
- Tanımsız `kritik` güven düzeyi

## Kalıcılık ve kontrol

Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar, **kalıcılık yoktur**. Kontrol adımı bu dosyalardan bağımsız, gizli verilerle sınar.

Son adımdaki gerçek deney bu dosyaları kullanmaz. O adımda skorlar, kurulu `all-minilm:22m` gömme modeliyle gerçekten hesaplanır.
