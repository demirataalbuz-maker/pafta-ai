# ai-savunma-13 · Görünür Sentetik Örnek Veri

Bu klasördeki profiller, komut istekleri ve yürütme sonuçları **sentetiktir**. Hiçbir komut çalıştırılmaz, konteyner başlatılmaz. Plan ve rapor yalnız veri üretir.

## veri/profiller.json (Görev 1)

Dokuz profil vardır. `beklenen: null` değeri `ValueError` demektir.

- **Geçerli:** `f-01` ve `f-02`. `f-02` uç değerleri kullanır: 5000 ms ve 65536 bayt.
- **`ValueError`:**
  - `f-03`: `ag: 0`; bool değil.
  - `f-04`: Kök `/`.
  - `f-05`: Kök `/sandbox/../etc`.
  - `f-06`: Kullanıcı `root`.
  - `f-07`: İzin listesinde `bash`.
  - `f-08`: Süre 10 s.
  - `f-09`: Kök `/sandbox/`; sonda eğik çizgi.

## veri/komut_istekleri.json (Görev 2)

Profil, dokuz istek ve beklenen plan vardır.

- **`hazir`:**
  - `analiz`.
  - `kok-dizin`: Çalışma dizini kökün kendisidir.
  - `metakarakter`: `a.py; cat /etc/passwd` kabuk olmadığı için **tek bir argümandır**. Python bunu dosya adı olarak görür; komut ayracı olarak yorumlanmaz.
- **`reddet`:**
  - `indir`: `curl` izinli değil.
  - `kacis`: `/sandbox/../etc`.
  - `onek`: `/sandboxx/is`. Dizge öneki tutar, ama kökün altında değildir.
  - `gezinti`: `../../etc/shadow`.
  - `mutlak`: `/etc/passwd`.
  - `kabuk`: Üç neden birden.

Dört bozuk girdi `ValueError` almalıdır: yinelenen kimlik, NUL, 201 karakter ve metin olarak gelen argümanlar.

## veri/yurutme_sonuclari.json (Görev 3)

Altı sonuç vardır (profil: 2000 ms, 8192 bayt).

- `tam-sinir`: Tam sınırdadır → `tamamlandi`.
- `bir-fazla-sure` ve `bir-fazla-cikti`: Bir birim fazla → ihlal.
- `negatif-cikis`: Çıkış kodu −9 → `basarisiz`. Sıfırdan farklı her kod başarısızdır.
- `sistem`: `OOMKilled` → `calisamadi`. Dört neden birden korunur.

Dört bozuk girdi `ValueError` almalıdır.

## Kalıcılık ve kontrol

Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar; **kalıcılık yoktur**. Kontrol adımı bu dosyalardan bağımsız, gizli verilerle sınar. Son adım bu dosyaları kullanmaz; yerel modelin `komut_oner` aracıyla ürettiği gerçek önerileri planlar.
