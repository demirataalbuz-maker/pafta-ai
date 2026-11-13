# AI gerçek pilotlar · kurulum/indirme onay listesi

Durum: **ONAYLANDI ve KURULDU (2026-10-28)**; ayrıntı: ai-gercek-pilot-raporu.md. Sürümler ve boyutlar 2026-10-28'de resmî dizinlerden okundu.

Mevcut ve yeniden kullanılacaklar (indirme yok): Python 3.13.14, Ollama 0.40.11 (sunucu zaten çalışıyor), Ollama'da `llama3.2:3b` ve `qwen3:8b`. Saldırı ve Savunma pilotları bunlarla **şimdiden** geliştirilip denenebiliyor.

| # | Ne | Resmî kaynak | Sürüm | Yaklaşık boyut | Lisans | Amaç |
|---|---|---|---|---|---|---|
| 1 | Ayrı Python sanal ortamı `.ai-venv` (proje klasöründe, sistem Python'unu değiştirmez) | Python `venv` | 3.13.14 (kurulu) | ~20 MB | PSF | Torch derslerini diğer Pafta koşucularından ayırmak |
| 2 | PyTorch **CPU** | download.pytorch.org/whl/cpu | 2.14.1+cpu | 124 MB indirme, ~450 MB disk | BSD-3 | Temel (ileri hesap/logit) ve Güvence (otomatik türev ile FGSM) |
| 3 | transformers | pypi.org | 5.21.0 | 13 MB | Apache-2.0 | Gerçek tokenizer + model yükleme |
| 4 | tokenizers, safetensors, huggingface_hub, numpy (+ küçük bağımlılıklar: filelock, regex, pyyaml, tqdm, requests…) | pypi.org | 0.23.3 / 0.8.0 / 2.3.0 / 2.5.4 | ~35 MB toplam | Apache-2.0 / BSD | Tokenizer, ağırlık dosyası, model indirme |
| 5 | Model: `HuggingFaceTB/SmolLM2-135M` (commit `93efa2f0…`, sabitlenir) | huggingface.co | 135M parametre | ~270 MB | Apache-2.0 | Temel pilotu: gerçek token kimliği, logit, olasılık |
| 6 | Ollama modeli `qwen3:4b-instruct-2507-q4_K_M` | registry.ollama.ai | manifest katmanı `sha256:85e4a5b7…` | 2,50 GB | Apache-2.0 (manifestte lisans katmanı var, indirince doğrulanacak) | Ortak sohbet modeli adayı; bellek kabulü indirme sonrası ölçülecek |

İsteğe bağlı, **önermiyorum**: PyTorch CUDA (cu128) ~2,9 GB. Pilotlardaki 135M model ve küçük sınıflandırıcı CPU'da saniyeler içinde çalışıyor; RTX 5050 için CUDA yalnız daha büyük beyaz kutu derslerinde gerekebilir.

Kurulum komutları (onaydan sonra çalıştırılacak, proje klasöründe):

```text
python -m venv .ai-venv
.ai-venv\Scripts\python -m pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu
.ai-venv\Scripts\python -m pip install transformers==5.21.0 tokenizers==0.23.3 safetensors==0.8.0 huggingface_hub==2.3.0 numpy==2.5.4
.ai-venv\Scripts\python tools/ai_gercek_kur.py --model-indir        (SmolLM2-135M, sabit commit, HF önbelleğine)
ollama pull qwen3:4b-instruct-2507-q4_K_M
```

Hiçbir ücretli hizmet, hesap ya da API anahtarı gerekmez. Silme/kaldırma yapılmaz.

## Ek onay (2026-10-28): gömme modeli

| # | Ne | Resmî kaynak | Sürüm | Boyut | Lisans | Amaç | Durum |
|---|---|---|---|---|---|---|---|
| 7 | Ollama modeli `all-minilm:22m` (all-MiniLM-L6-v2, 23M parametre, 384 boyut, num_ctx 256) | registry.ollama.ai/library/all-minilm | id `1b226e2802db` | ~46 MB | Apache-2.0 (manifest lisans katmanı) | ai-temel-21 gerçek RAG: gömme + tam top-k arama | Kullanıcı onayladı, `ollama pull all-minilm:22m` ile kuruldu |

Neden: SmolLM2 gizli durum ortalaması gömme olarak zayıftı (6 sorudan 2'sinde doğru parça ilk sırada); Qwen3 4B Ollama'da `/api/embed` desteklemiyor (HTTP 501).
