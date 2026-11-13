# ai-saldiri-41 · Görünür Örnek Veri (Sentetik)

Bu klasördeki dosyalar `ai-saldiri-41` (**Slopsquatting Saldırısı: Paket Halüsinasyonu Hasadı ve Kayıt Yüzeyi Analizi**) dersinin deterministik görevleri için hazırlanmış **sentetik** örnek verilerdir (gerçek PyPI/npm kayıtları değildir; hiçbir gerçek paket deposuna sorgu veya yükleme yapılmaz):

- `slop/model_onerileri.json` — Farklı istem ve tohumlarda (`seed`) modelin önerdiği paket listeleri.
- `slop/yerel_paket_dizini.json` — Sentetik yerel paket dizinindeki durum kayıtları (`resmi`, `rezerve-yasakli`, `sahipsiz`) ve aday risk profilleri.
- `slop/ajan_kurulum_izleri.json` — Kodlama ajanlarının `pip install` bayrakları (`--only-binary=:all:`), ağ erişimi ve onay kipine göre slopsquatting tetikleme izleri.

> **Kalıcılık notu:** Her çalıştırmada (`setup`) bu dosyalar geçici çalışma klasörüne yeniden kopyalanır; çalışma zamanında yapılan değişiklikler kalıcı değildir.
