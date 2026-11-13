# ai-guvence-09 — Görünür Sentetik Örnek Veri

Bu klasördeki dosyalar **tamamen sentetik** eğitim örnekleridir; gerçek model gradyanı veya canlı saldırı optimizasyon kaydı değildir:

- `veri/optimizasyon.json`: Örnek ayrık token adayları (`adaylar`), seçim bütçesi (`butce`), yöntem bazlı optimizasyon izleri (`arama_izi`) ve model transfer başarı kayıtları (`transfer_kayitlari`).

İlk 3 görevin `setup` adımı `sandbox.ai_guvence_veri.hazirla("ai-guvence-09")` ile bu dosyaları çalışma klasörüne kopyalar (**kalıcılık yoktur**). Görev 1 bütçeli aday seçimini, Görev 2 arama izi özetini, Görev 3 transfer analizini bu dosyadan okur. Gerçek deney adımı yerel SmolLM2-135M modeli üzerinde PyTorch koordinat gradyanı (GCG) ve kayıp ölçümünü canlı yürütür.
