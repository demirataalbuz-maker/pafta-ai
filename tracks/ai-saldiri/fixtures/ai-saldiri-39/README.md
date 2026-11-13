# ai-saldiri-39 Görünür Veri Dosyaları (Sentetik Fixture)

Bu klasördeki JSON dosyaları `ai-saldiri-39` (*LLM Uygulama Pentest Köprüsü · İstemci Sırları, Çapraz Oturum IDOR ve AI-SSRF Zinciri*) dersinin ilk üç görevinde kullanılan **sentetik eğitim verileridir (`sentetik_fikstur`)**:

- `uygulama/istemci_paketleri.json`: Ön-yüz paketlerinde veya SSE akış zarflarında unutulan sentetik API anahtarları (`sk-pafta-...`) ve iç servis uç noktaları.
- `uygulama/api_oturum_izleri.json`: Çok kiracılı (multi-tenant) LLM uygulamasının konuşma (`thread`), vektör alanı (`namespace`) ve belge yükleme (`belge`) uç noktalarındaki örnek HTTP izleri.
- `uygulama/saldiri_zincirleri.json`: Uygulama katmanı açıklıklarının model üzerinden çapraz oturum sızıntısına, RAG zehirlemesine veya AI-SSRF'e dönüştüğü örnek zincirler.

> **Önemli:** Bu dosyalar sentetik eğitim örnekleridir; gerçek API anahtarı veya gerçek sistem adresi içermez. Son görevde yerel Ollama modeliyle canlı çapraz-oturum bağlam sızıntısı ve iç uç nokta SSRF zinciri deneyi yürütülür.
