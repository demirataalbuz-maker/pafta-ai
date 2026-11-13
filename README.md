# Pafta AI

Türkçe, ücretsiz ve tamamen yerelde çalışan AI güvenlik eğitimi: AI red team, AI savunma, gerçek AI güvenlik olayları ve kuantum kriptografi.

Her ders önce anlatır, sonra çıktıyı tahmin ettirir, ardından Python ile çözülen görevler verir; her görevin cevabı testlerle sınanır. Teknik terimler orijinal haliyle kalır, anlatım Türkçedir.

## İçerik

| Yol | Ne öğretir |
|---|---|
| `ai-temel` | Token, attention, RAG, ajanlar: modelin nasıl çalıştığı |
| `ai-saldiri` | AI red team: prompt injection, jailbreak, araç zinciri, AI-SSRF, veri sızdırma |
| `ai-savunma` | AI blue team: guardrail, telemetri, tespit kuralları, olay müdahalesi |
| `ai-ile-guvenlik` | AI ile güvenlik işi: zafiyet avı, SOC triyajı, otonom savunma |
| `ai-olay` | Gerçek AI güvenlik olayları, kaynağıyla ve yerel kopyasıyla |
| `ai-ctf` | Yerel hedeflerde bayrak kapma ve yama |
| `ai-bulut` | Bulut AI altyapısı: IAM, günlükler, kiracı yalıtımı, LLMjacking |
| `ai-matematik` | Lineer cebirden pekiştirmeli öğrenmeye AI matematiği |
| `ai-uretim` | Sıfırdan LLM bileşenleri |
| `ai-guvence` | Değerlendirme, istatistik, araştırma yöntemi |
| `kuantum` | Kuantum hesaplama, kuantum sonrası kriptografi |

Bu depoda yalnız bağımsız denetimden geçmiş dersler var; diğerleri denetlendikçe eklenir. Hiçbir ders gerçek bir sisteme saldırmaz: hedefler yereldir, veriler sentetiktir, sırlar kanaryadır.

## Çalıştırma

Gerekenler: Windows, Python 3.11 ya da üstü, Microsoft Edge.

```
python Pafta.pyw
```

Ya da `tools/PaftaYerelLauncher.cs` dosyasını derleyip `Pafta.exe` ile açın (derleme komutu dosyanın başında yazılı).

## Gerçek deney adımları

Derslerin çoğu yalnız Python ile çalışır. Bazı derslerin son adımı küçük açık modellerle gerçek deney yapar; bunun için:

- **Ollama** ve küçük modeller (örneğin `qwen3:4b-instruct-2507-q4_K_M`)
- Proje klasöründe `.ai-venv` adlı Python ortamı (torch, transformers)

Kurulum listesi, sürümler ve boyutlar: `docs/ai-gercek-kurulum-onayi.md`. Ortam yoksa ilgili adım "kurulu değil" der; dersin geri kalanı çalışır. NVIDIA kartı varsa deneyler onu kullanır, yoksa CPU'da çalışır.

## Durum

Dersleri AI modelleri yazdı ve birbirini denetledi; henüz insanlar tarafından baştan sona denenmedi. Hata görürseniz issue açın.
