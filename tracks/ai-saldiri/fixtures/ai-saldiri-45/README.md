# ai-saldiri-45 · Görünür Sentetik Örnek Veri

Bu klasördeki tüm dosyalar **sentetik** eğitim verisidir; gerçek üretim günlüklerinden veya canlı saldırı kampanyalarından alınmamıştır. Her çalıştırmada (`setup`) çalışma klasörüne yeniden kopyalanır (**kalıcılık yoktur**).

- `cok_dilli_denemeler.jsonl`: İngilizce, Türkçe, düşük kaynaklı dil (`dusuk_kaynak`), kod değiştirme (`kod_degistirme`) ve çeviri zinciri (`ceviri_zinciri`) kiplerinde aynı zararsız vekil (`canary`) isteğin sentetik model yanıtları.
- `ceviri_kapisi_adaylari.json`: Dil bağımsız / çevirip denetleme savunma kapısını (`cok_dilli_guvenlik_kapisi`) sınamak için hazırlanmış sentetik istek ve çeviri adayları.
