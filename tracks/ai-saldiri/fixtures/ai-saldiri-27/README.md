# ai-saldiri-27 — Sentetik Veri Seti (Değerlendirici Zafiyetleri ve ASR Güvenilirliği)

Bu klasördeki tüm dosyalar **elle yazılmış sentetik** eğitim verisidir; gerçek bir hakem modelinin çıktısı veya canlı saldırı kaydı değildir. Başarı sinyali yalnız zararsız bir canary kodudur.

- `hakem/ham_hakem_ciktilari.json`: Bir değerlendiricinin ham çıktı örnekleri (`ciktilar`). Bazıları katı şemaya uymaz (kod çitli JSON, ek alan, düz metin); bunlar belirsiz karar değil, ölçüm altyapısı hatasıdır.
- `hakem/hakem_olaylari.json`: Referans etiketi ve hakem kararı olan olaylar (`olaylar`).
- `hakem/asr_sonuclari.json`: Belirsiz kararlar da içeren saldırı sonuçları (`sonuclar`).

Çalışma klasörüne her çalıştırmada yeniden kopyalanır; değişikliklerin kalıcı değildir. Testler bu dosyalardan ayrı, görmediğin verilerle sınar.
