# ai-guvence-35 · Görünür Sentetik Örnek Veri

`veri/taylor.json` **sentetiktir**: elle yazılmış bir kayıp fonksiyonu (`x0^3+2*x0*x1`), gradyanlar ve Taylor satırlarıdır; gerçek model çıktısı değildir.

## Alanlar

- `katsayilar`, `nokta`, `dogru_gradyan`, `yanlis_gradyan`, `h`, `tol` (Görev 1): Denetlenecek nokta ve doğru/bilerek bozuk gradyan.
- `gradyan`, `eps` (Görev 2): Üç norm için bozuntu girdisi.
- `taylor_satirlari`, `tol_taylor` (Görev 3): Bilerek karışık sıralı satırlar; 0.2 satırındaki uyuşma tesadüftür ve geçerli bölge sayılmamalıdır.

## Kalıcılık ve kontrol

Setup her Çalıştır/Kontrol Et adımında dosyayı yeniden kopyalar; **kalıcılık yoktur**. Kontrol bu dosyadan bağımsız, gizli verilerle sınar. Final bu dosyayı kullanmaz.
