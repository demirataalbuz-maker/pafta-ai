# ai-saldiri-48 · Görünür Sentetik Örnek Veri

Bu klasördeki `veri/uyelik.json` dosyası **sentetiktir**: kayıplar, skorlar ve üretimler elle yazılmıştır, gerçek model çıktısı değildir. PIN'ler rastgele, kayıtlar kurgusaldır; gerçek kişi verisi yoktur.

## Alanlar

- `kayiplar` (Görev 1): Altı kayıt. `degil-yaygin` doğası gereği kolay bir metindir; ham skorda üye gibi görünür, kalibre skorda görünmez. `uye-b-zor` zor bir metindir; ham skoru düşüktür ama kalibrasyonla üye olduğu ortaya çıkar.
- `auc_girdileri` ve `beklenen_auc` (Görev 2): Görev 1'in çözümünden üretilmiş ham ve kalibre skor listeleri, `fpr_siniri = 0.25`. Ham skor AUC'si 0.889, kalibre skor AUC'si 1.000.
- `esitlik_ornegi` (Görev 2): Eşit skorların yarım sayıldığı küçük örnek; `fpr_siniri = 0.5` ile AUC 5/6.
- `denemeler` ve `beklenen_cikarim` (Görev 3): Tam, kısmi ve yok sonuçları; `degil-capraz` bir üyenin PIN'ini birebir sızdırır; `degil-alinti` reddetme cümlesidir.

## Kalıcılık ve kontrol

Setup her Çalıştır/Kontrol Et adımında bu dosyayı yeniden kopyalar; **kalıcılık yoktur**. Kontrol adımı bu dosyadan bağımsız, gizli verilerle sınar. Final bu dosyayı kullanmaz; her koşuda yeni kurgusal kayıtlar üretir ve kurulu Qwen modelini offline kullanır.
