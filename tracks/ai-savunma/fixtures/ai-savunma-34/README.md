# ai-savunma-34 · Görünür Sentetik Örnek Veri

`veri/mimari.json` **sentetiktir**: belgeler, planlar, değişken değerleri ve gönderim kayıtları elle yazılmıştır; gerçek model çıktısı değildir.

## Alanlar

- `belgeler` (Görev 1): Sekme, çift boşluk ve satır sonu içeren bir fatura; kendi sahte kapanış sınırlayıcısını (`<</veri>>`) taşıyan bir belge; `^` karakteri içeren bir belge.
- `planlar` ve `degiskenler` (Görev 2): Privileged LLM'in döndürebileceği planlar (`$OZET`, `$YANIT_ADRESI`) ve Quarantined LLM'in doldurduğu değerler. `$OZET` değerinin içinde `$ANAHTAR` yazar; `$OZET_UZUN` adı `$OZET` ile başlar; `bilinmeyen` planı tanımsız bir değişken kullanır.
- `rehber` ve `eylemler` (Görev 3): Kullanıcının güvendiği adresler ve kaynak etiketli eylemler.
- `kosular` (Görev 3): Dört mimarinin her biri için birer sentetik koşu kaydı.

## Kalıcılık ve kontrol

Setup her Çalıştır/Kontrol Et adımında dosyayı yeniden kopyalar; **kalıcılık yoktur**. Kontrol adımı bu dosyadan bağımsız, gizli verilerle sınar. Final bu dosyayı kullanmaz; her koşuda yeni canary üretir ve kurulu Ollama modelini kullanır.
