# ai-guvence-39 · Görünür Sentetik Örnek Veri

`veri/mi.json` **sentetiktir**: güvenler, shadow logitleri ve sayımlar elle yazılmıştır, gerçek model çıktısı değildir.

## Alanlar

- `guvenler` (Görev 1): Uç değerler dışında güven örnekleri; `0` ve `1` için davranış gizli testte sınanır.
- `ornekler`, `taban` (Görev 2): Kolay örnek, üye ve üye olmayan zor örnek, sabit dağılım.
- `sayimlar`, `guven` (Görev 3): `0/50` ve `50/50` uç durumları dahil.

## Kalıcılık ve kontrol

Setup her Çalıştır/Kontrol Et adımında dosyayı yeniden kopyalar; **kalıcılık yoktur**. Kontrol bu dosyadan bağımsız, gizli verilerle sınar. Final bu dosyayı kullanmaz.
