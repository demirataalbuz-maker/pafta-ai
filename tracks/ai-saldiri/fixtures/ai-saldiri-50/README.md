# ai-saldiri-50 · Görünür Sentetik Örnek Veri

`veri/solucan.json` **sentetiktir**: e-postalar ve kayıtlar elle yazılmıştır, gerçek model çıktısı değildir. `PAFTA-` kodları kurgusaldır.

## Alanlar

- `ciftler` (Görev 1): Gelen e-posta (`girdi`) ve asistanın yazdığı taslak (`cikti`) çiftleri: meşru iletme, solucan kopyası, kısa yanıt.
- `zincir` (Görev 2): Üç ajanlı e-posta zinciri. Her adımın `girdi`'si bir önceki adımın `cikti`'sıdır; her ajanın kendi `canary`'si vardır. 2. ajan 1. ajanın kodunu yalnız taşır; 3. ajan kendi kodunu küçük harfle yazar.
- `kopuk_zincir` (Görev 2): 2. adımın girdisi bir önceki çıktıyla aynı değil; geçersiz kayıttır.
- `esikler` (Görev 3): Örnekte denenecek iki bekçi eşiği.
- `bekci_zincirleri` (Görev 3): Hop başına önceden hesaplanmış `uzunluk` (girdi-çıktı en uzun ortak kelime dizisi), `kopyaladi`, `sizdirdi` alanlarıyla iki solucan ve iki normal zincir.

## Kalıcılık ve kontrol

Setup her Çalıştır/Kontrol Et adımında dosyayı yeniden kopyalar; **kalıcılık yoktur**. Kontrol adımı bu dosyadan bağımsız, gizli verilerle sınar. Final bu dosyayı kullanmaz; kurulu Ollama modeliyle her koşuda yeni kodlar üretir.
