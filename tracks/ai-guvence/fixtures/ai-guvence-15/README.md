# ai-guvence-15 — Sentetik Veri Seti (Veri Ayıklama Yöntemlerinin Kanıt Değeri)

Bu klasördeki tüm dosyalar **elle yazılmış sentetik** eğitim verisidir; gerçek bir veri kümesinden, üretim sisteminden veya canlı deneyden alınmamıştır.

- `veri/ayiklama_kayitlari.json`: Gerçek durumu bilinen kayıtlar ve bir yöntemin ayıklama kararları (`kayitlar`).
- `veri/sayimlar.json`: TP/FP/TN/FN sayım örnekleri (`ornekler`); biri sıfır paydalı durumu gösterir.
- `veri/yontem_sonuclari.json`: Yöntem başına sayımlar (`yontemler`) ve veri kaybı üst sınırı (`kayip_ust_sinir`).

Çalışma klasörüne her çalıştırmada yeniden kopyalanır; değişikliklerin kalıcı değildir. Testler bu dosyalardan ayrı, görmediğin verilerle sınar.
