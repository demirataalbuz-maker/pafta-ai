# ai-guvence-11 · Görünür Sentetik Örnek Veri

Bu klasördeki dosyalar **tamamen sentetik** eğitim örnekleridir; gerçek bir veri gölü soykütüğü (data lineage) veya canlı üretim kaydı değildir:

- `veri/koken_kayitlari.json`: Kaynak, sürüm ve dönüşüm geçmişi içeren örnek kayıt (`id`, `kaynak`, `surum`, `donusumler`).
- `veri/dagilim_ve_profil.json`: Beklenen/gözlenen kategori sayımları ve şüpheli kayıt adayları (`id`, `kaynak`, `sapma`, `etiket_degisti`).

Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar (**kalıcılık yoktur**). Kontrol adımı bu dosyalardan bağımsız gizli verilerle sınama yapar.
