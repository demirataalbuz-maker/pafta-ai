# Context ve konum çalışma verisi

baglam.json elle hazırlanmış sentetik örnektir; gerçek model/tokenizer çıktısı değildir. İlk görev tokenlar/sinir, ikinci pozisyonlar, üçüncü mesajlar/butce ve aralik_ornegi alanlarını okur. Doğru pencere son iki etiket; konum 0 için [0.0,1.0]; bütçe5 için a,b, aralık tuzağında yalnız new seçilir. Bunlar gizli test cevaplarının yerine geçmez.

Setup ai_temel_veri.hazirla ile dosyayı her çalıştırmada geçici veri/baglam.json konumuna kopyalar. Dersin ilk Çalıştır çıktısı ham JSON'u gösterir. Projedeki kaynak dosyayı haricî editörde aç veya yüklenen sözlükteki bütçe, uzunluk, konumları kodda değiştirip Çalıştır. Geçici kopya değişiklikleri sonraki çalıştırmada korunmaz; uygulamada dosya editörü bulunduğu vaat edilmez. Öğrenci verisi silinmez. Final bu dosyaya bağımlı değildir; kurulu model ile ayrı gerçek metinler kullanır.
