# ai-saldiri-52 · Görünür Sentetik Örnek Veri

`veri/tag.json` **sentetiktir**: metinler ve "yanıtlar" elle yazılmıştır, gerçek model çıktısı değildir. Dosya `ensure_ascii` ile yazıldı; tag karakterleri dosyada `\udb40\udc..` vekil çifti kaçışları olarak görünür, `json.load` bunları tek kod noktasına (U+E00xx) çevirir.

## Alanlar

- `mesajlar` (Görev 1): Düz metin, ASCII tag ile gizlenmiş bir talimat, meşru İskoçya bayrağı (🏴 + `gbsct` + CANCEL TAG) ve eski dil etiketi (U+E0001 + `tr`).
- `taranacak` (Görev 2): Meşru bayrak, gizli talimat, dil etiketi, bayrağın hemen ardına eklenmiş gizli yük (tek kesintisiz tag dizisi olur) ve tek başına CANCEL TAG.
- `denemeler` ve `kontrolsuz_denemeler` (Görev 3): Dört kipli (`gorunur`, `gizli`, `temizlenmis`, `yansitma`) sentetik deney kayıtları. `g1` canary'yi küçük harf ve boşlukla yazar; `y1` canary'yi yalnız görünmez tag olarak taşır. `kontrolsuz_denemeler` setinde model görünür talimata bile uymamıştır.

## Kalıcılık ve kontrol

Setup her Çalıştır/Kontrol Et adımında dosyayı yeniden kopyalar; **kalıcılık yoktur**. Kontrol adımı bu dosyadan bağımsız, gizli verilerle sınar. Final bu dosyayı kullanmaz; her koşuda yeni canary üretir ve kurulu Ollama modelini kullanır.
