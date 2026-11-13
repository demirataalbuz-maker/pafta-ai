# AI gerçek deney pilotları

Mevcut sentetik/fixture görevleri korunur. Dört derse **ayrı, açıkça adlandırılmış** birer gerçek deney görevi eklendi (`Gerçek deney · …`, adım meta'sında `motor: ai-gercek`). Ders ekranında bu adımlar "GERÇEK DENEY" rozetiyle, sonuçları "GERÇEK ÇAĞRI / kabul" kanıt kutusuyla görünür.

| Pilot | Ders · adım | Gerçek araç | Öğrencinin işi | Kabul kanıtı |
|---|---|---|---|---|
| Temel | `ai-temel-03` · 8 | transformers + torch (CPU), `HuggingFaceTB/SmolLM2-135M` @ `93efa2f0` | token kimlikleri, son konum logitleri, sıcaklıklı softmax, top-k | rastgele metin/k/sıcaklıkta bağımsız ileri hesapla aynı sonuç; ağırlık SHA-256, sürümler |
| Saldırı | `ai-saldiri-02` · 10 | Ollama sohbet modeli | kontrol/saldırı vakaları, canary sızıntı tespiti, hata-ayrık ASR | rastgele canary, vaka başına 2 tohumlu gerçek çağrı, ham yanıtlar, hatalar, ASR (başarı şart değil) |
| Savunma | `ai-savunma-12` · 10 | Ollama araç çağrısı + sandbox klasörü | fail-closed araç politikası | diskteki gerçek etki: e-posta/silme/yabancı dosya 0, meşru not yazıldı; korumasız taban çizgisi bulgu olarak |
| Güvence | `ai-guvence-07` · 8 | torch autograd, CPU'da eğitilen 64-32-4 MLP | FGSM ve ε-doğruluk eğrisi | rastgele altküme/ε'da bağımsız autograd FGSM ile aynı bozuntu; gerçek tahminlerden doğruluk |

## Gerçek ↔ fixture ayrımı

- `motor: ai-gercek` adımları `engine/runners.py · AiGercekRunner` ile koşar; kod ve test `import ai_lab` (`sandbox/ai_gercek_lab.py`) kullanır. Laboratuvarda fixture/mocks yoktur; araç yoksa `GercekLabYok` → görev geçmez.
- Koşucu, test geçse bile laboratuvarın yazdığı `kaynak: gercek, kabul: true` kanıtı yoksa sonucu **fail**'e çevirir.
- `gereksinim: torch` adımları `.ai-venv` yorumlayıcısında (`PAFTA_AI_PYTHON` ile değiştirilebilir) koşar; yoksa `BağımlılıkEksik`.
- Kanıtlar `PAFTA_DATA/ai-kanit/*.json` (varsayılan `%LOCALAPPDATA%\Pafta\ai-kanit`): model adı/digest/nicemleme/lisans ilk satırı, Ollama sürümü, gerçek bellek (`/api/ps` size/size_vram), ayarlar ve tohumlar, girdiler, ham çıktılar, cihaz (OS, CPU, RAM, GPU), öğrenci kodunun SHA-256'sı, temizlik sonucu.
- Gerçek deney adımları süreli sınav havuzuna alınmaz.

## Kaynak sahipliği

`SohbetOturumu` çalışan bir Ollama sunucusu bulursa onu kullanır ve **kapatmaz**; modeli kendisi yüklediyse iş bitince yalnız o modeli boşaltır (`keep_alive: 0`), önceden yüklü modele dokunmaz. Sunucu yoksa boş bir portta kendi `ollama serve` sürecini açar ve yalnız o süreç ağacını kapatır. WSL, Docker ve kullanıcının diğer süreçleri etkilenmez; model dosyaları ve öğrenci verisi silinmez.

## Ortam ayarları (yol gömülmez)

`PAFTA_AI_SOHBET_MODELI` (yoksa tercih sırası: `qwen3:4b-instruct-2507-q4_K_M`, `llama3.2:3b`, `qwen3:8b`), `PAFTA_OLLAMA_HOST`, `PAFTA_OLLAMA_EXE`, `PAFTA_AI_PYTHON`, `PAFTA_AI_HF_MODEL`, `PAFTA_AI_HF_REVIZYON`.

## Komutlar

```text
python tools/ai_gercek_kur.py --kontrol      # kurulum/model durumu; hiçbir şey kurmaz
python tools/test_ai_gercek.py               # dört pilot + altyapı senaryoları (gerçek çağrı)
python tools/test_ai_gercek.py saldiri savunma
python tools/validate.py --yol ai-saldiri
```

Kurulum listesi ve onay durumu: [ai-gercek-kurulum-onayi.md](ai-gercek-kurulum-onayi.md).
