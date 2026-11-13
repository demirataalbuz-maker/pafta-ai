# ai-savunma-08 · Görünür Sentetik Örnek Veri

Bu klasördeki model çıktıları, metinler ve guardrail kayıtları **sentetiktir**. `api_key=...`, `Bearer ...`, PEM başlıkları ve `BREACH:CANARY-42` gerçek sır değildir; tarayıcının neyi yakalayıp neyi kaçırdığını göstermek için yazılmıştır. Hiçbir model çağrılmaz.

## veri/model_ciktilari.json (Görev 1)

On iki örnek vardır. `beklenen: null` değeri `ValueError` demektir.

- **Geçerli:** `m-01` … `m-03`. Güven `0` ve tamsayı `1` geçerlidir; boş kaynak listesi geçerlidir.
- **`ValueError`:**
  - `m-04`: Şemaya eklenmiş `sistem_notu` alanı. Gizli değer bu ek alanla taşınabilir; ek alan sessizce atılmaz, çıktı reddedilir.
  - `m-05`: Özette sondaki boşluk. Kırpılmaz, reddedilir.
  - `m-06`, `m-07`, `m-08`: Güven `True`, `1.5` ve `"0.9"`.
  - `m-09`: Kaynak kimliğine gömülmüş `; rm -rf`.
  - `m-10`, `m-11`, `m-12`: Yinelenen kaynak, altı kaynak, bilinmeyen etiket.

## veri/cikti_metinleri.json (Görev 2)

On iki metin vardır.

- **Yakalananlar:**
  - `s-02`: RSA başlığı.
  - `s-03`: Küçük harfli `bearer` ve 8 karakter.
  - `s-05`: Tam genişlikli `ＡＰＩ＿ＫＥＹ＝...`; NFKC ile yakalanır.
  - `s-06`: Reddetme cümlesindeki canary de sinyaldir.
  - `s-08`: Aynı tür iki kez geçer, tek sinyal üretir.
  - `s-10`: Dört sinyal sabit sırada.
- **Yakalanmayanlar:**
  - `s-04`: 7 karakterlik Bearer değeri.
  - `s-07`: `BREACH:CANARY-420`; bağımsız işaret değildir.
  - `s-09`: **base64 kodlanmış anahtar**. Dar kalıp tarayıcısının bilerek bırakılmış sınırıdır; bu tür sızıntıyı yalnız yapısal doğrulama ya da çıktı allowlist'i durdurabilir.
- `s-12`: NUL içeren metin → `ValueError`.

## veri/guardrail_kayitlari.json (Görev 3)

Yedi kayıt ve beklenen rapor vardır.

- `yanit-sinir`: Güven tam 0.5 → `gecir`.
- `yanit-dusuk`: Güven 0.49 → `insan_incelemesi`.
- `yanit-sema`: Sızıntı yoktur, ama şema bozuktur → `durdur`.
- `yanit-coklu`: Bütün nedenler korunur: `sema`, `gizli_veri`, `gizli_isaret`. Düşük güven, durdurma nedeni varken eklenmez.

Dört bozuk girdi `ValueError` almalıdır: yinelenen kimlik, sırasız sinyaller, `sema_gecerli: 1` ve güven 1.2.

## Kalıcılık ve kontrol

Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar; **kalıcılık yoktur**. Kontrol adımı bu dosyalardan bağımsız, gizli verilerle sınar. Son adım bu dosyaları kullanmaz; yerel modelin yapısal ve serbest modda ürettiği gerçek çıktılarla çalışır.
