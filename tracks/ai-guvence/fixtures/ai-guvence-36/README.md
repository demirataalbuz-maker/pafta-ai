# ai-guvence-36 · Görünür Sentetik Örnek Veri

`veri/masking.json` **sentetiktir**: logitler ve saldırı raporları elle yazılmıştır, gerçek model çıktısı değildir.

## Alanlar

- `projeksiyon` (Görev 1): Top ve kutu sınırlarına değen küçük bir örnek.
- `logitler` (Görev 2): Normal, doygun ve yanlış sınıflanmış örnek.
- `raporlar`, `tol`, `sinir` (Görev 3): `gercek_sald_sonucu` bayraksızdır; `cok_iyi_savunma_iddiasi` maskeleme izleri taşır.

## Kalıcılık ve kontrol

Setup her Çalıştır/Kontrol Et adımında dosyayı yeniden kopyalar; **kalıcılık yoktur**. Kontrol bu dosyadan bağımsız, gizli verilerle sınar. Final bu dosyayı kullanmaz.
