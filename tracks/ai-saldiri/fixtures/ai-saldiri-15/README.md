# ai-saldiri-15 · Görünür Sentetik Örnek Veri

Bu klasördeki dosyalar **tamamen sentetiktir**. Gerçek bir arama günlüğü, gerçek vektör veritabanı skoru ya da gerçek müşteri belgesi değildir. Skorlar 0–100 aralığında elle yazılmış tamsayılardır. Bütçe karakter sayısıdır, token sayısı değildir.

## `veri/sorgular.json`

Dört sorgu var:

- Fazla boşluklu ve büyük harfli bir sorgu (`İade SÜRESİ`).
- Aynı sorgunun küçük harfli sade hâli. **Dikkat:** İkisi aynı biçime normalize olmaz. Türkçe `İ` harfi `casefold()` ile `i̇` olur, yani `i` harfi ve birleşik bir nokta işareti. Bu yüzden `\w+` deseni `İade` sözcüğünü `i` ve `ade` diye böler, `SÜRESİ` ise `süresi̇` olur. Bu durum bilerek gösterilir. Özgün sorgunun izde korunması bu yüzden önemlidir.
- Sekme ve satır sonu içeren bir sorgu.
- Talimat görünümlü ifade taşıyan bir sorgu. Bu ifade normalize sorguda silinmez, iz için korunur.

`bozuk_sorgular` içinde yalnız boşluk, boş string ve 201 karakter olmak üzere üç örnek var.

## `veri/aday_belgeler.json`

Bütçe 120 karakter. Beş belge var:

| Belge | Skor | Uzunluk | Ne gösterir |
|---|---|---|---|
| `kampanya-sayfasi` | 97 (en yüksek) | 160 karakter | Bütçeye sığmaz; **atlanır, kırpılmaz**. |
| `iade-politikasi`, `kargo-sss` | 88 (eşit) | — | Eşitlikte kimlik sırası uygulanır. |
| `eski-sss` | 70 | — | Eski ve çelişkili bilgi. Büyük belge atlandığı için bağlama girer. |
| `bos-not` | — | 0 karakter | Boş metin; her zaman seçilebilir. |

Doğru seçim: `iade-politikasi`, `kargo-sss`, `eski-sss`, `bos-not`; 112 karakter kullanılır.

`bozuk_belgeler` içinde 101 skor, bool skor ve boş kimlik var.

## `veri/baglam_kayitlari.json`

Kanıt kimliği `iade-politikasi`. Üç vaka var:

- **`q-iade`:** Manipüle bağlamda `sahte-iade` girer, kanıt çıkar (**kanıt kaybı**).
- **`q-kargo`:** Yalnız sıra değişir. Küme farkı boştur, bu yüzden değişim listesinde görünmez. Sıra değişiminin bu ölçütle görünmediğine dikkat et.
- **`q-saat`:** `reklam` girer ama kanıt kaybı yoktur.

`bozuk_kayitlar` içinde manipüle kolu eksik vaka, iki temiz kolu olan vaka ve yinelenen bağlam kimliği var.

## Kalıcılık ve kontrol

Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar. **Kalıcılık yoktur.** Kontrol adımı bu dosyalardan bağımsız, gizli verilerle sınar.

Son adımın düzenlenebilir bağlam dosyası buradan ayrıdır: `web/data/ai-saldiri-15-baglam.txt`. Bu dosyanın kalıcı kopyası `calisma/ai-saldiri-15/baglam.json` yolunda tutulur.
