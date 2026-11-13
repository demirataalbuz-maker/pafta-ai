# ai-guvence-01 · Görünür Sentetik Örnek Veri

Bu klasördeki dosyalar **tamamen sentetik** eğitim örnekleridir; gerçek bir model eğitimi veya canlı saha telemetrisi değildir:

- `veri/plan.json`: Örnek bir ML güvenliği deney planı (`id`, `veri`, `model`, `tehdit`, `olcutler`, `tohum`).
- `veri/olcumler.json`: Aynı plana ait tekrarlı ölçüm kayıtları (`olcut`, `tekrar`, `deger`); kasıtlı olarak bir ölçüt-tekrar çifti eksik bırakılmıştır.

Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar (**kalıcılık yoktur**). Kontrol adımı bu dosyalardan bağımsız gizli verilerle sınama yapar.
