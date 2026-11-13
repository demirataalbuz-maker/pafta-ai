# Görünür kampanya verisi

veri/kampanya.json elle yazılmış sentetik örnektir, canlı/kaydedilmiş model çıktısı değildir. Kaynak dosyayı metin editörüyle aç; görevlerin çalışma dizininde aynı göreli yol vardır. İlk görev vakalar, ikinci butce, üçüncü plan/sonuclar alanlarını okur. Üçüncü örneğin ASR değeri 1.0, saldırı hatası 1, sağlam kontrolü 1/1 olur. Bunlar gerçek deney sonucu değildir.

Setup mevcut ai_saldiri_veri.hazirla ile geçici kopya oluşturur; her Run/Check yeni çalışma alanıdır ve değişiklikler kalıcı değildir. Editörde json_yukle sonucunu bir değişkene alıp kopyasını düzenle ve yeniden Çalıştır. Öğrenci verisi gizli test beklentisini değiştirmez. Son görev gerçek Promptfoo ve yerel Ollama kullanır; eksik bağımlılık PASS değildir.
