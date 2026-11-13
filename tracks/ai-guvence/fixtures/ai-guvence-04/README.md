# ai-guvence-04 · Görünür Sentetik Örnek Veri

Bu klasördeki dosyalar **tamamen sentetik** eğitim örnekleridir; gerçek bir SOC maliyet muhasebesi veya canlı model skoru değildir:

- `veri/maliyet_profili.json`: Yanlış pozitif (`fp_maliyeti`), yanlış negatif (`fn_maliyeti`) ve para birimi (`para_birimi`) profili.
- `veri/skor_kayitlari.json`: Gerçek etiket ve model olasılık skoru içeren sentetik kayıtlar (`id`, `gercek`, `skor`).

Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar (**kalıcılık yoktur**). Kontrol adımı bu dosyalardan bağımsız gizli verilerle sınama yapar.
