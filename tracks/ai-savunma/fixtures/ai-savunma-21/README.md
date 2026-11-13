# ai-savunma-21 · Görünür Sentetik Örnek Veri

Bu klasördeki dosyalar **tamamen sentetiktir**. Gerçek bir MLflow model registry, Git deposu ya da kişi kaydı değildir. Özetler örnek metinlerin gerçek SHA-256 değerleridir.

## `veri/registry_politikasi.json`

- `politika`: Yalnız `model` ve `prompt` türleri izinlidir. En az 2 bağımsız onay gerekir. Geri alma ve özet değişimi zorunludur.
- `bozuk_politikalar`: Reddedilmesi gereken dört kayıt:
  - 0 onay
  - isteğe bağlı geri alma
  - bilinmeyen `agent` türü
  - bool tipinde onay sınırı

## `veri/degisiklik_kayitlari.json`

### `denetim_kayitlari` (görev 2)

| Kayıt | Ne gösterir | Doğru karar |
|---|---|---|
| `prompt-v3` | Temiz bir değişiklik | aday |
| `prompt-v4-sahip` | Sahip kendi onaycı listesinde. Sahip sayılmadığında tek bağımsız onay kalır | `onay` |
| `guardrail-v4` | İzinli olmayan tür | `tur` |
| `model-v7` | Geri alma sürümü yeni sürüme eşit | `geri_alma` |
| `prompt-v5-noop` | Sürüm artmış, içerik özeti aynı | `ozet` |

### `yayin_kayitlari` (görev 3)

| Kayıt | Ne gösterir | Doğru karar |
|---|---|---|
| `prompt-v3` | Aktif sürüm 2'den 3'e ilerliyor | yayın |
| `model-v6-tekrar` | Aktif sürüm zaten 6 | `surum` |
| `prompt-ilk` | İlk sürüm (aktif 0); geri dönülecek önceki sürüm yok | `geri_alma` |

### `bozuk_kayitlar`

Reddedilmesi gereken kayıtlar:
- yinelenen onaycı
- büyük harfli özet
- bool tipinde sürüm
- ASCII dışı sahip adı (`ayşe`)

## Kalıcılık ve kontrol

- Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar. **Kalıcılık yoktur.**
- Kontrol adımı bu dosyalardan bağımsız, gizli verilerle sınar.
- Son adımdaki gerçek deney bu dosyaları kullanmaz. O adımda prompt sürümlerinin özetleri hesaplanır ve yerel Ollama modeli her iki sürümle gerçekten çalıştırılır.
