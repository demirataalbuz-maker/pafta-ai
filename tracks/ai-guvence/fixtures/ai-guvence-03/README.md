# ai-guvence-03 · Görünür Sentetik Örnek Veri

Bu klasördeki dosyalar **tamamen sentetik** eğitim örnekleridir; gerçek bir tehdit istihbaratı veya canlı saldırı ölçümü değildir:

- `veri/tehdit_karti.json`: Örnek bir ML tehdit kartı (`id`, `kategori`, `varlik`, `aktor`, `varsayim`).
- `veri/olcumler.json`: Taban ve deney koşularına ait tekrarlı sentetik ölçümler (`tekrar`, `taban`, `deney`).

Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar (**kalıcılık yoktur**). Kontrol adımı bu dosyalardan bağımsız gizli verilerle sınama yapar.
