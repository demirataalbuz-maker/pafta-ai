# Görünür logit örneği

logitler.json elle yazılmış sentetik örnektir, model yanıtı değildir. Helper çalışma alanında veri/logitler.json yoluna kopyalar. İlk üç görev aynı logit/token/hedef alanlarını okur. Kaynak dosyayı editörle aç; editörde yüklenen listenin kopyasını değiştirip Run ile dene. Her çalıştırmada yeni geçici kopya, kalıcılık yok; gizli testler ayrı.

Örnek softmax [0.090031,0.244728,0.665241], greedy üçüncü aday, hedef0 kaybı2.407606. buyuk_logitler aynı dağılımı üretir. Son görev kurulu gerçek tokenizer/model ile bütün sözlükte dağılım ölçer; indirme yok.
