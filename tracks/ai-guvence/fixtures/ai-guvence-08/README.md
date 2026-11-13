# ai-guvence-08 · Görünür Sentetik Örnek Veri

Bu klasördeki dosyalar **tamamen sentetik** eğitim örnekleridir; gerçek bir sinir ağı gradyanı veya canlı PGD saldırısı değildir:

- `veri/pgd_ayari.json`: PGD bütçe ve adım ayarı (`id`, `epsilon`, `alpha`, `adim`) ile örnek başlangıç vektörü ve gradyanları.
- `veri/pgd_kayitlari.json`: Farklı `epsilon` ve `adim` noktalarındaki doğruluk ve `l_inf` gözlemleri.

Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar (**kalıcılık yoktur**). Kontrol adımı bu dosyalardan bağımsız gizli verilerle sınama yapar.
