# ai-saldiri-55 · Görünür Sentetik Örnek Veri

`veri/ses.json` **sentetiktir**: kayıtlar, skorlar ve satırlar elle yazılmıştır; ses dosyası ya da model çıktısı değildir.

## Alanlar

- `kayitlar`, `test_orani` (Görev 1): Altı metnin her biri için bir `gercek` ve bir `sentetik` kayıt. Aynı metnin iki kaydı aynı tarafa düşmelidir.
- `skor_ornek`, `esikler` (Görev 2): Sekiz örneğin "sentetik" skoru ve gerçek etiketi (1 = sentetik).
- `satirlar` (Görev 3): İki modelin koşul koşul `tpr`, `fpr`, `eer` değerleri.

## Kalıcılık ve kontrol

Setup her Çalıştır/Kontrol Et adımında dosyayı yeniden kopyalar; **kalıcılık yoktur**. Kontrol adımı bu dosyadan bağımsız, gizli verilerle sınar. Final bu dosyayı kullanmaz; onaylı yerel LibriSpeech örnekleri, Piper ve Windows SAPI ile gerçek ses üretir ve ölçer.
