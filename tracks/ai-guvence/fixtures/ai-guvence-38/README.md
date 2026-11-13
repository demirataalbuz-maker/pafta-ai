# ai-guvence-38 · Görünür Sentetik Örnek Veri

`veri/geometri.json` **sentetiktir**: vektörler ve komşu listesi elle yazılmıştır, gerçek gömme modeli çıktısı değildir.

## Alanlar

- `ciftler` (Görev 1): Aynı yön, dik ve kısa ama ters yönlü vektörler.
- `X`, `v0`, `adim` (Görev 2): `(10,10)` etrafına kaydırılmış küçük veri; merkezleme hatasını gösterir.
- `komsular` (Görev 3): `0` ve `1` hub, bazı noktalar anti-hub.

## Kalıcılık ve kontrol

Setup her Çalıştır/Kontrol Et adımında dosyayı yeniden kopyalar; **kalıcılık yoktur**. Kontrol bu dosyadan bağımsız, gizli verilerle sınar. Final bu dosyayı kullanmaz.
