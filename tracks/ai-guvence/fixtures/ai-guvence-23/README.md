# ai-guvence-23 görünür sentetik veri

Elle yazılmış başarı sayımlarıdır; gerçek F16/GGUF ölçümü değildir. İlk üç görev aynı quant_olcumleri.json dosyasını doğrular, F16 farkını ve esikler.json alarmlarını hesaplar. hazirla/setup her çalıştırmada geçici kopya oluşturur, kalıcılık yoktur. Kodlar dosyayı okur/yazdırır; aynı çalıştırmada bellekte bir kopyayla deneme yapabilirsin. Gizli testler ayrıdır. Sonraki CPU fake-quant ve gerçek Q4/Q8 GGUF görevleri farklı öğrenme hedefleridir; gerçek GGUF görevi Q8'i F16 diye sunmaz ve modelleri otomatik indirmez.
