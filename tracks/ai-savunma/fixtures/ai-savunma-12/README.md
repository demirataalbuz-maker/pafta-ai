# ai-savunma-12 · Görünür Sentetik Örnek Veri

Bu klasördeki politikalar, araç çağrıları ve onay kayıtları **sentetiktir**. Open Policy Agent kural tablolarının ve bir onay uç noktasının JSON karşılığına benzer, ama hiçbir politika motoru ya da servis çağrılmaz.

## veri/politikalar.json (Görev 1)

Sekiz politika vardır. `beklenen: null` değeri `ValueError` demektir.

- **Geçerli:** `p-01`, `p-02`. Fail-closed varsayılan kullanırlar; boş kural listesi geçerlidir.
- **`ValueError`:**
  - `p-03`: `varsayilan: izin`. Bilinmeyen her çağrı açık kalırdı.
  - `p-04`: Kural kaynağı (`belge`) izinli kaynaklarda yok.
  - `p-05`: Aynı üçlü iki kez, çelişen kararlarla. Hangisinin uygulanacağı sıraya bağlı kalırdı.
  - `p-06`: Bilinmeyen `shell` aracı.
  - `p-07`: Yinelenen kaynak.
  - `p-08`: Ek `oncelik` alanı.

## veri/arac_cagrilari.json (Görev 2)

Politika ve sekiz çağrı vardır. Beklenen rapordan önemli satırlar:

- `oku-belgeden`, `oku-yuksek`: Tam üçlü kural yoktur, varsayılan `reddet` uygulanır. Yalnız araç adına bakmak bunları yanlışlıkla çalıştırırdı.
- `kimliksiz-web`: Kimlik yok → `reddet`, ama `onay` nedeni de korunur: `["kimlik", "onay"]`.
- `model-rapor`: Üç neden birden: `["kimlik", "baglam", "politika"]`.
- `web-onay`, `rapor-onay` → `insan_onayi`. Araç çalışmaz.

Dört bozuk girdi `ValueError` almalıdır.

## veri/onaylar.json (Görev 3)

Tek bir `rapor_yaz` çağrısı için on iki onay ve "şimdi" zamanı vardır (ms).

- **Geçerli:** `o-01` ve `o-02`. `o-02` son geçerlilik anının kendisidir; aralık iki ucu da kapsar.
- **Geçersiz:**
  - `o-03`, `o-04`: Zaman dışı.
  - `o-05`: Başka çağrının onayı (yeniden oynatma).
  - `o-06`: Farklı eylem.
  - `o-07`: Model kendine onay üretmiş.
  - `o-08`: İnsan reddetmiş.
  - `o-09`: Daha önce kullanılmış.
  - `o-10`: Dört neden birden.
- **`ValueError`:** `o-11` (süre sıfır) ve `o-12` (`kullanildi: 0`).

## Kalıcılık ve kontrol

Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar; **kalıcılık yoktur**. Kontrol adımı bu dosyalardan bağımsız, gizli verilerle sınar. Son adım bu dosyaları kullanmaz; yerel modelin gerçek araç çağrılarını geçici bir sandbox klasöründe çalıştırır.
