# Temel17 görünür veri

Elle yazılmış sentetik istek/SSE/batching örnekleri, gerçek sunucu kaydı değil. Setup veri/ altına geçici kopya hazırlar; kalıcılık yok. istekler.json görev1/3 içindir; SSE dosyaları görev2. Ham SSE LF satır sonları ve sondaki boş satır korunur. Tam dosya Merhaba dünya/stop/tamamTrue; yarım dosya aynı metin/stop/tamamFalse üretir. Batching1slot: uzun tamam2/3token; kisa kuyrukta zaman_asimi1/0token. Dosyaları editörle aç; kodda yüklenen kopyayı değiştirip Run dene. Gerçek final SSE yerine Ollama NDJSON kullanır.
