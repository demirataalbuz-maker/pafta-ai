# ai-saldiri-38 Görünür Veri Dosyaları (Sentetik Fixture)

Bu klasördeki JSON dosyaları `ai-saldiri-38` (*AI Kapı Bekçisini (Gatekeeper) Atlatma · Sınıflandırıcı ve Guardrail Evasion*) dersinin ilk üç görevinde kullanılan **sentetik eğitim verileridir (`sentetik_fikstur`)**:

- `kapilar/moderasyon_kurallari.json`: Örnek bir metin sınıflandırıcısının riskli ve iyi huylu terim ağırlıkları ile karar eşiği.
- `kapilar/aday_metinler.json`: Orijinal, karakter parçalamalı, eşanlam ikameli, iyi huylu dolgulu ve etiket sarmalamalı örnek girdiler.
- `kapilar/atlatma_ciftleri.json`: Moderasyon, spam filtresi ve özgeçmiş eleme kapılarında denenen orijinal/varyant çiftleri ve niyet korunumu kayıtları.

> **Önemli:** Bu dosyalar sentetik eğitim örnekleridir. Son görevde yerel Ollama modeli canlı bir **AI kapı bekçisi (LLM guardrail yargıcı)** olarak çalıştırılır ve atlatma tekniklerine verdiği gerçek kararlar ölçülür.
