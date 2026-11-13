# Tercih verisi çalışma dosyası

tercih.json elle hazırlanmıştır; gerçek eğitim/insan etiketi kaydı değildir. İlk görev tercih_ciftleri alanını temizler, ikinci logp_deneyi üzerinde DPO kaybını hesaplar, üçüncü degerlendirme alanındaki iki ayrı etiketi sayar. Doğru örnek kayıplar 0.126928,0.126928,1000.0; değerlendirme doğruluğu0.666667,güvenli_oran0.333333. Bunlar genel güvenlik kabulü değildir, gizli testleri değiştirmez.

Setup mevcut ai_temel_veri.hazirla ile her Run/Check için geçici veri/tercih.json kopyası oluşturur; değişiklikler sonraki çalıştırmada korunmaz. Kaynak dosyayı haricî editörde aç veya kodda yüklenen sözlüğü değiştirip Çalıştır. İlk görev ham JSON'u ekrana basar. Görevler aynı dosya üzerinde ilerler. Finalde kurulu LM ile ayrı istemlerden gerçek logitler hesaplanır; görünür dosyanın sayıları gerçek deney yerine kullanılmaz. Yeni indirme ve kalıcı model dosyası güncellemesi yoktur.
