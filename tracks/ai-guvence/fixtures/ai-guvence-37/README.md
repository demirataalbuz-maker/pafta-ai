# ai-guvence-37 · Görünür Sentetik Örnek Veri

`veri/gcg.json` **sentetiktir**: gradient satırı ve token kayıtları elle yazılmıştır, gerçek model çıktısı değildir.

## Alanlar

- `aday` (Görev 1): Gradient satırı, mevcut token, `k` ve yasak tokenlar.
- `kayitlar`, `k` (Görev 2 ve 3): Tahmin ve gerçek loss farkı; en iyi tahminlerin her zaman gerçekten en iyi olmadığı görülür.
- `esitlik` (Görev 2): Ortalama sıra örneği.

## Kalıcılık ve kontrol

Setup her Çalıştır/Kontrol Et adımında dosyayı yeniden kopyalar; **kalıcılık yoktur**. Kontrol bu dosyadan bağımsız, gizli verilerle sınar. Final bu dosyayı kullanmaz.
