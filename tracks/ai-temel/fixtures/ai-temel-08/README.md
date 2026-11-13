# Görünür KV/batch/kiracı verisi

cache.json elle yazılmış sentetik örnektir, gerçek K/V tensoru veya sunucu logu değildir. Helper bu dosyayı geçici çalışma alanında veri/cache.json yoluna kopyalar. İlk üç görev aynı dosyanın alanlarını okur. Kaynak dosyayı editörle aç; ders editöründe json_yukle sonucunun kopyasını değiştirip Run ile karşılaştır. Her çalıştırmada yeni kopya gelir, kalıcılık yoktur. Gizli testler ayrı girdilerdir.

Doğru batch sonucu a,c; a kiracısı iki kaydı görür. Son mevcut görev CPU modelinde gerçek cache eşdeğerliği ölçer. Çok kullanıcılı sunucu yalıtımı veya hızlanma kanıtı değildir.

Ek gerçek görevde kurulu Ollama üzerinden iki çakışan HTTP isteği ve uygulama kiracı görünürlüğü ölçülür. Bu, backend KV yalıtımı veya vLLM/llama.cpp karşılaştırması değildir.
