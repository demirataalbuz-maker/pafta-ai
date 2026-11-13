# ai-saldiri-37 Görünür Veri Dosyaları (Sentetik Fixture)

Bu klasördeki JSON dosyaları `ai-saldiri-37` (*Red Team Metodolojisi II · Kapsam Matrisi, Saldırı Zinciri Önceliklendirme ve Operasyon Kapanışı*) dersinin ilk üç görevinde kullanılan **sentetik eğitim verileridir (`sentetik_fikstur`)**:

- `kampanya/kapsam_kayitlari.json`: Hedef sistemin aktif katmanları ve yürütülen saldırı testlerinin örnek listesi.
- `kampanya/zincir_bulgulari.json`: Çok adımlı saldırı zinciri bulguları ve kanıt durumları.
- `kampanya/kapanis_envanteri.json`: Operasyon sonunda temizlenmesi gereken RAG zehir belgeleri, kalıcı bellek kayıtları, vekil canary'ler ve yerel model oturumlarının örnek envanteri.

> **Önemli:** Bu dosyalar sentetik eğitim örnekleridir; her çalıştırmada geçici çalışma klasörüne yeniden kopyalanır. Son görevde yerel Ollama modeliyle canlı saldırı-zinciri ve kapanış/temizlik doğrulama deneyi yürütülür.
