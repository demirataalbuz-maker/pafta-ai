# ai-savunma-33 · Görünür Sentetik Örnek Veri

`veri/devre.json` **sentetiktir**: kosinüs değerleri, temsil vektörleri ve "üretimler" elle yazılmıştır; gerçek model çıktısı ya da gerçek eğitim kaydı değildir.

## Alanlar

- `rr_ornekleri` (Görev 1): Eğitimin başında, ortasında ve sonunda representation rerouting kaybının girdileri (zararlı dizilerde kosinüs, koru dizilerinde L2 uzaklık).
- `temsil_kayitlari` ve `esik` (Görev 2): Eğitim öncesi ve sonrası küçük (3 boyutlu) temsil vektörleri.
- `denemeler` (Görev 3): Üç model (taban, ret_egitimi, devre_kesici) ve üç küme (dogrudan, saldiri, koru) için birer sentetik üretim. `t-s1` sırrı rakamlar arasına tire koyarak yazar.

## Kalıcılık ve kontrol

Setup her Çalıştır/Kontrol Et adımında dosyayı yeniden kopyalar; **kalıcılık yoktur**. Kontrol adımı bu dosyadan bağımsız, gizli verilerle sınar. Final bu dosyayı kullanmaz; kurulu Qwen2.5-0.5B-Instruct modelini gerçekten eğitir.
