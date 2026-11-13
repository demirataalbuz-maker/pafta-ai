# ai-savunma-20 · Görünür Sentetik Örnek Veri

Bu klasördeki dosyalar **tamamen sentetiktir**. Özetler örnek dosya adlarının SHA-256 değeridir. Gerçek bir model dosyası, Cosign imzası, Trivy taraması veya CVE kaydı değildir.

- `veri/tedarik_politikasi.json`
  - `politika`: Yalnız `resmi`/`kurumsal` kaynak ve `model`/`paket` türü kabul edilir. Yalnız `dusuk` risk izinlidir. Boyut en çok 1000 MB'tır ve imza zorunludur.
  - `bozuk_politikalar`: Reddedilmesi gereken dört kayıt var: imza isteğe bağlı, boş tür listesi, yinelenen risk, 50000 MB sınır.
- `veri/bilesenler.json`
  - `kabul_kayitlari` (görev 2):
    - `ozet-modeli` boyut sınırına **tam eşittir**; kabul edilir.
    - `api-imaji` izin verilmeyen bir türdür.
    - `topluluk-ince-ayar` dört nedenin üçünü birden taşır.
    - `tokenizer` imzasızdır.
  - `surum_kayitlari` (görev 3):
    - `ozet-modeli-ayna` beklenen özetten yalnız **son karakteriyle** ayrılır; `butunluk` nedeniyle karantinaya girer.
    - `yardimci-paket` için özet eşleşir ama `kritik` ve `orta` riskleri vardır. `risk` nedeni yalnız **bir kez** yazılır.
  - `bozuk_kayitlar`: Reddedilmesi gereken kayıtlar. Büyük harfli özet, 63 karakterlik özet ve yinelenen risk.

Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar (**kalıcılık yoktur**). Kontrol adımı bu dosyalardan bağımsız, gizli verilerle sınar.

Son adımdaki gerçek deney bu dosyaları kullanmaz. O adım kurulu Ollama modelinin manifest'ini ve blob dosyalarını salt okunur açar, her katmanın SHA-256 özetini gerçekten hesaplar.
