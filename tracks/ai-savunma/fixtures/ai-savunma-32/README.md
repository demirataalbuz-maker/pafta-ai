# ai-savunma-32 · Görünür Sentetik Örnek Veri

`veri/siniflandirici.json` **sentetiktir**: etiketler ve skorlar elle yazılmıştır; gerçek model çıktısı değildir.

## Alanlar

- `metrik` (Görev 1): On örnek, skorlar ve 0.5 eşiği. İki skor eşiğe tam eşittir.
- `esik` (Görev 2): On bir örnek ve bir FPR sınırı.
- `bozulma` (Görev 3): Aynı dört metnin `orijinal`, `leet` ve `harf_bosluklu` biçimlerindeki skorları.

## Kalıcılık ve kontrol

Setup her Çalıştır/Kontrol Et adımında dosyayı yeniden kopyalar; **kalıcılık yoktur**. Kontrol adımı bu dosyadan bağımsız, gizli verilerle sınar. Final bu dosyayı kullanmaz; `deepset/prompt-injections` veri setiyle DistilBERT'i gerçekten eğitir.
