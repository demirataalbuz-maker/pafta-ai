# ai-guvence-02 · Görünür Sentetik Örnek Veri

Bu klasördeki dosyalar **tamamen sentetik** eğitim örnekleridir; gerçek bir veri kümesi veya canlı model olasılığı değildir:

- `veri/ayrim_kayitlari.json`: Eğitim ve test bölümü kayıtları (`id`, `etiket`, `bolum`).
- `veri/taban_tahminleri.json`: Sentetik gerçek/tahmin sınıf etiketleri ve pozitif sınıf olasılıkları (`gercek`, `tahmin`, `olasiliklar`).

Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar (**kalıcılık yoktur**). Kontrol adımı bu dosyalardan bağımsız gizli verilerle sınama yapar.
