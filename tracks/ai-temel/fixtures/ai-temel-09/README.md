# Görünür eğitim verisi

egitim.json elle hazırlanmış sentetik örnektir, gerçek eğitim kaydı değildir. Helper geçici çalışma alanında veri/egitim.json yoluna kopyalar. İlk görev tahmin/hedef, ikinci agirliklar/gradyan/oran, üçüncü tek_agirlik alanını okur. Doğru MSE4.0, SGD [0.95,2.05,2.9], tek ağırlık0.488 ve kayıplar [1.0,0.64,0.4096].

Kaynak dosyayı editörle aç; ders kodunda yüklenen kopyayı değiştirerek Run ile karşılaştır. Her çalıştırma yeni geçici kopyadır, kalıcılık yok; gizli testler ayrı. Son görev kurulu PyTorch ile gerçek backward ve optimizer.step çalıştırır; yeni model/araç indirmez.
