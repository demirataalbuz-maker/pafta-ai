# ai-uretim-37 örnek verisi

`profiler_olaylari.json`: elle yazılmış, **sentetik** bir profiler kaydı. Gerçek bir eğitimden alınmadı; yalnız biçimi gösterir.

- İki `train_step`; her biri `data_load`, `forward` (içinde `conv` ve `linear`) ve `backward` içerir. Üç düzey iç içedir.
- Süreler milisaniye sayılabilir; birim görev için önemli değildir.
- İkinci adımda `data_load` 30'dan 45'e çıkar: darboğazın veri yüklemeye kaydığı durumu görmek için.

Denemek için: bir olayın `bit` değerini ebeveyninin dışına taşır (kısmen kesişme, `ValueError` beklenir) ya da `backward` içine yeni bir çocuk olay ekle ve `kendi` süresinin nasıl değiştiğine bak.
