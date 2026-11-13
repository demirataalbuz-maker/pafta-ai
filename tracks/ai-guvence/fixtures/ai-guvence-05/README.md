# ai-guvence-05 · Görünür Sentetik Örnek Veri

Bu klasördeki dosyalar **tamamen sentetik** eğitim örnekleridir; gerçek bir kriptografik derleme veya canlı model ağırlığı değildir:

- `veri/manifest.json`: Deney manifesti (`id`, `veri_surumu`, `model_surumu`, `tohum`, `ortam`).
- `veri/dosyalar.json`: Kanıt paketi dosya özetleri (`yol`, `sha256`, `boyut`).

Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar (**kalıcılık yoktur**). Kontrol adımı bu dosyalardan bağımsız gizli verilerle sınama yapar.
