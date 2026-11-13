# ai-guvence-14 — Sentetik Veri Seti (Backdoor Tetikleyici Deneyi)

Bu klasördeki tüm dosyalar **elle yazılmış sentetik** eğitim verisidir; gerçek bir görüntü veri kümesinden, üretim modelinden veya canlı deneyden alınmamıştır.

- `veri/goruntu_ornekleri.json`: Küçük gri tonlu matrisler (`goruntuler`), 2x2 tetikleyici (`tetik`) ve denenecek yerleşimler (`yerlesimler`). Bir yerleşim görüntüye sığmaz; doğrulama bunu reddetmelidir.
- `veri/deney_kayitlari.json`: Yerleşim başına deneme kayıtları (`kayitlar`): temiz örnek doğru mu, tetikli örnek hedef sınıfa gitti mi.
- `veri/yerlesim_olcumleri.json`: Tohum başına temiz doğruluk ve hedef başarı ölçümleri (`olcumler`) ile temiz doğruluk alt sınırı (`temiz_alt_sinir`).

Çalışma klasörüne her çalıştırmada yeniden kopyalanır; değişikliklerin kalıcı değildir. Testler bu dosyalardan ayrı, görmediğin verilerle sınar.
