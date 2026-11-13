# ai-savunma-14 · Görünür Sentetik Örnek Veri

Bu klasördeki politikalar, URL'ler ve DNS çözümleri **sentetiktir**. Hiçbir HTTP isteği ya da DNS sorgusu yapılmaz. `evil.test` ayrılmış test alanıdır. IP adresleri ya dokümantasyon/örnek adresleridir ya da bilinen özel ve metadata aralıklarıdır.

## veri/politikalar.json (Görev 1)

Dokuz politika vardır. `beklenen: null` değeri `ValueError` demektir.

- **Geçerli:** `e-01` ve `e-02`.
- **`ValueError`:**
  - `e-03`: Varsayılan `izin`.
  - `e-04`: IP literal `169.254.169.254`.
  - `e-05`: Büyük harfli alan.
  - `e-06`: Joker `*.ornek.com`.
  - `e-07`: Port 80.
  - `e-08`: Yönlendirme 10.
  - `e-09`: Sondaki nokta.

## veri/url_istekleri.json (Görev 2)

On bir URL vardır.

- **`hazir`:**
  - `api`.
  - `buyuk-harf`: `urlsplit().hostname` küçük harfe çevirir.
  - `acik-443`.
- **`reddet`:**
  - `metadata`: `http://169.254.169.254/...` → `sema`, `alan`.
  - `gcp-metadata`: `sema`, `alan`.
  - `kullanici-hilesi`: `https://api.ornek.com@evil.test/`. Gerçek host `evil.test`'tir → `kimlik`, `alan`.
  - `sonek-hilesi`: `api.ornek.com.evil.test` → `alan`.
  - `loopback-ipv6`: `[::1]` → `alan`.
  - `port-8080` → `port`.
  - `ftp` → `sema`.
  - `cok-yonlendirme` → `yonlendirme`.

Dört bozuk girdi `ValueError` almalıdır: yinelenen kimlik, URL içinde boşluk, ayrıştırılamayan port ve negatif yönlendirme.

## veri/dns_cozumleri.json (Görev 3)

Sekiz çözüm vardır.

- `genel`: Genel IPv4 ve IPv6 → `hazir`.
- `rebinding`: Genel bir adresin yanında `127.0.0.1` var. **Tek bir genel olmayan adres bütün kaydı reddeder.**
- `link-local`, `cgnat`, `ipv4-mapped`, `multicast` → `ip`. Sırasıyla `169.254.169.254`, `100.64.0.10`, `::ffff:10.0.0.5` ve `224.0.0.251`.
- `bos-yanit` → `dns`.
- `baska-alan` → `alan`.

Dört bozuk girdi `ValueError` almalıdır.

## Kalıcılık ve kontrol

Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar; **kalıcılık yoktur**. Kontrol adımı bu dosyalardan bağımsız, gizli verilerle sınar. Son adım bu dosyaları kullanmaz; yerel modelin `istek_at` aracıyla ürettiği gerçek URL önerilerini denetler.
