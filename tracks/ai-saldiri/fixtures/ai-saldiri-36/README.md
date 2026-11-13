# ai-saldiri-36 Görünür Veri Dosyaları (Sentetik Fixture)

Bu klasördeki JSON dosyaları `ai-saldiri-36` (*Red Team Metodolojisi I · Yasal Kapsam (RoE), Sistem Anatomisi ve Güven Sınırları*) dersinin ilk üç görevinde kullanılan **sentetik eğitim verileridir (`sentetik_fikstur`)**:

- `kapsam/roe_sozlesmesi.json`: İzinli hedefleri, hız limitini, üçüncü taraf model API şartlarını, kanıt saklama süresini ve yasak yük kategorilerini tanımlayan örnek RoE (Rules of Engagement) belgesi.
- `kapsam/aday_test_plani.json`: Red team ekibinin koşturmayı planladığı aday test senaryoları (uyumlu ve kapsam dışı/yasaklı örnekler).
- `sistemler/musteri_asistani_mimari.json`: Hedef AI sisteminin 6 bileşenli anatomisini (`model`, `sistem_istemi`, `rag`, `araclar`, `bellek`, `cikti_tuketici`) gösteren örnek mimari tanımı.

> **Önemli:** Bu dosyalar gerçek bir kuruma ait sözleşme veya sistem envanteri değildir. Görev değerlendirmeleri bu dosyalardan bağımsız görünmeyen test verileriyle yapılır; son görevde ise yerel Ollama modeliyle canlı keşif ve RoE denetimi deneyi yürütülür.
