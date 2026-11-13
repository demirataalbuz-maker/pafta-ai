# ai-temel-18 · Görünür Sentetik Örnek Veri

Bu klasördeki dosyalar **sentetiktir**. Docker CLI token'larının, bellek/CPU dizgelerinin ve `HostConfig.Binds` biçiminin yalnız görünümünü izler. Görev 1–3'te hiçbir komut çalıştırılmaz, konteyner başlatılmaz. Setup bu dosyaları çalışma klasöründe `veri/` altına kopyalar.

## kaynak_sinirlari.json (Görev 1)

On üç örnek vardır. `beklenen: null` değeri `ValueError` demektir.

- **Geçerli:** `r-01` … `r-07`.
  - `r-02`: `--memory 2g --memory-swap 3g` → `MemorySwap` toplamdır (3 GiB), takas 1 GiB'tır.
  - `r-05`: `"0"` takası belirtilmemiş sayılır; `1.000000001` CPU kayan nokta olmadan `1000000001` olur.
  - `r-07`: `6144k` = 6 MiB. Çarpanlar 1024 tabanlıdır.
- **`ValueError`:** `r-08` … `r-13`. Bunlar iki harfli `mb`, ondalık bellek, bellekten küçük takas, 6m altı, çekirdekten fazla CPU ve 0.01 altı CPU.

## run_komutlari.json (Görev 2)

Dokuz komut vardır.

- `d-01`: Sertleştirilmiş llama.cpp sunucusu → bulgu yok. İmajdan sonraki `--host 0.0.0.0` konteyner komutuna aittir.
- `d-02`: Sertleştirmesiz model sunucusu → yedi bulgu.
- `d-03`: İmajdan sonraki `--privileged` konteyner komutunun argümanıdır, Docker bayrağı değildir. Ayrıca `--cap-drop all` küçük harfle de `ALL` sayılır.
- `d-04`: `/var/run/../run/docker.sock` normalleştirilince `/run/docker.sock` olur → `docker_sock`.
- `d-05`: `--pids-limit -1` sınırsızdır; `--user 00:0` root'tur.
- `d-06` … `d-09` → `ValueError`: kısa `-v`, tekrarlanan `--memory`, imajsız komut, `--read-only=true`.

## baglamalar.json (Görev 3)

Model dizini `/models`, izinli kökler `/srv/modeller` ve `/srv/veri`. On bir bağlama vardır. Beklenen sonuç:

- İzinli bağlamalar: `llama:/models:ro`, `girdi:/data:rw`, `//srv/veri/./d` → `/srv/veri/d`, `/srv/modeller:/tum:ro`.
- Reddedilenler:
  - `2 izinsiz`: `/srv/modeller-yedek` dizge önekiyle geçer, ama kökün altında değildir.
  - `3 kacis`: kaynakta `..` var.
  - `4 sock`: docker.sock bağlaması.
  - `5 kok`: `/` bağlaması.
  - `6 yinelenen`: `/data` ikinci kez hedef.
  - `7 yazilabilir_model`: aynı ağırlıklar başka hedefe `rw` bağlanmak isteniyor.
  - `8 yazilabilir_model`: `/models` altına `rw` bağlama.

## Kalıcılık ve kontrol

Setup her çalıştırmada bu dosyaları yeniden kopyalar; **kalıcılık yoktur**. Kontrol adımı bu dosyalardan bağımsız, gizli verilerle sınar. Son adım bu dosyaları kullanmaz; yerel `busybox` imajıyla gerçek `docker run --rm` konteynerleri başlatır.
