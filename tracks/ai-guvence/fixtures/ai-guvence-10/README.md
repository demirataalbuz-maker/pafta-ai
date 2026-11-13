# ai-guvence-10 — Görünür Sentetik Örnek Veri

Bu klasördeki dosyalar **tamamen sentetik** eğitim örnekleridir; gerçek model ağırlığı veya canlı aktivasyon tensorü değildir:

- `veri/abliteration.json`: Örnek yön vektörü (`yon`), aktivasyon vektörü (`aktivasyon`) ve taban/ablite güvenlik-yetenek kayıtları (`kayitlar`).

İlk 3 görevin `setup` adımı `sandbox.ai_guvence_veri.hazirla("ai-guvence-10")` ile bu dosyaları çalışma klasörüne kopyalar (**kalıcılık yoktur**). Görev 1 normalize yönü, Görev 2 ortogonal projeksiyonu, Görev 3 ise taban-ablite karşılaştırmasını bu dosyadan okur. Gerçek deney adımı PyTorch ve TransformerLens ile yerel Qwen2.5-0.5B-Instruct modeli üzerinde katman 14 refusal yönünü canlı olarak kaldırır.
