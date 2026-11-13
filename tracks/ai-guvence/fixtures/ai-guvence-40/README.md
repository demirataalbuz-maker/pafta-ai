# ai-guvence-40 · Görünür Sentetik Örnek Veri

`veri/kalibrasyon.json` **sentetiktir**: olasılıklar, logitler ve etiketler elle yazılmıştır, gerçek model çıktısı değildir.

## Alanlar

- `p`, `y`, `kova` (Görev 1 ve 3): Aşırı özgüvenli küçük bir örnek; `0.91` değeri iki kez geçer, biri pozitif biri negatif.
- `z`, `zy`, `alt`, `ust` (Görev 2): Sıcaklık araması için logitler.

## Kalıcılık ve kontrol

Setup her Çalıştır/Kontrol Et adımında dosyayı yeniden kopyalar; **kalıcılık yoktur**. Kontrol bu dosyadan bağımsız, gizli verilerle sınar. Final bu dosyayı kullanmaz.
