# Görünür attention verisi

attention.json elle yazılmış sentetik örnektir, gerçek model kaydı değildir. Helper çalışma alanında veri/attention.json yoluna kopyalar. İlk görev aynı dosyanın vektor/kafa_sayisi alanlarını, diğer ikisi skorlar/pozisyon alanlarını okur. Doğru bölme [[1,2],[3,4]], maske [0,1,None], ağırlık [0.268941,0.731059,0.0]. value_ornegi yalnız yorumlama için görünür ek veridir, görev çıktısına dahil değildir.

Kaynak dosyayı editörle aç; editörde yüklenen listenin kopyasını değiştir ve Run ile incele. Her çalıştırmada yeni geçici kopya, kalıcılık yok. Gizli testler ayrı. Son görev gerçek model katmanından Q/K/V ve bağlam çıkarır; maskenin güvenlik rolü/izin denetimi olduğu iddia edilmez. Yeni indirme yok.
