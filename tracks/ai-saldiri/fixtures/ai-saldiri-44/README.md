# ai-saldiri-44 · Görünür Sentetik Örnek Veri

Bu klasördeki dosyalar **sentetik** eğitim verisidir; gerçek üretim ajan belleklerinden alınmamıştır ve her çalıştırmada (`setup`) çalışma klasörüne yeniden kopyalanır (**kalıcılık yoktur**).

- `kalici_bellek.jsonl`: Ajanın diskteki kalıcı belleğine farklı oturumlarda ve farklı kaynaklardan (`kullanici_tercihi`, `rag_belgesi`, `web_sayfasi`, `arac_ciktisi`) yazılmış sentetik bellek kayıtları.
- `oturum_izleri.json`: Sonraki oturumlarda bu kalıcı bellek kayıtları yüklendiğinde ajanın ürettiği sentetik yanıtlar.
- `bellek_denetim_adayi.json`: Kaynak etiketi, kullanıcı onayı, süre sınırı (TTL) ve zehir temizleme kapısını (`bellek_yazim_ve_denetim_kapisi`) sınamak için hazırlanmış sentetik veri.
