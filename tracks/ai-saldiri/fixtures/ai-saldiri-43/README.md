# ai-saldiri-43 · Görünür Sentetik Örnek Veri

Bu klasördeki dosyalar **sentetik** eğitim verisidir; gerçek üretim ajan trafiğinden alınmamıştır ve her çalıştırmada (`setup`) çalışma klasörüne yeniden kopyalanır (**kalıcılık yoktur**).

- `a2a_mesajlari.jsonl`: Çok ajanlı bir sistemde (`planlayici`, `arastirmaci`, `icraci`, `denetci`) ajanlar arası mesajları, yetki kapsamlarını ve canary sızıntılarını içeren sentetik JSONL izleri.
- `guven_zincirleri.json`: Düşük güvenilirlikli bir ajandan yüksek yetkili ajanlara yayılan geçişli (transitive) güven kirlenmesini ve kandırılmış vekil (confused deputy) adımlarını temsil eden sentetik zincirler.
- `gorev_zarflari.json`: HMAC-SHA256 imzalı görev devri, en az yetki matrisi ve `<ajan_verisi>` sarmalama kapısını (`imzali_gorev_devri_kapisi`) sınamak için hazırlanmış sentetik zarflar.
