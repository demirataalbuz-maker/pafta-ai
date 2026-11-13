# ai-saldiri-10 · Görünür Sentetik Örnek Veri

Bu klasördeki ham yanıtlar, kararlar ve komut vakaları **sentetiktir**; canlı model çıktısı değildir. `dosya_sil`, `__import__` ve `SHELL` değerleri, reddedilmesi gereken veridir. Hiçbir şey silinmez, hiçbir komut çalıştırılmaz.

## veri/ham_yanitlar.json (Görev 1)

On iki ham metin vardır. Her birinin `beklenen` alanı `kabul` bilgisini ve kabul edilenlerde `repr` biçimindeki değeri taşır.

| Örnek | Sonuç | Neden |
|---|---|---|
| `h-01` | kabul | Baştaki ve sondaki boşluk serbesttir |
| `h-02` | red | ```` ```json ```` kod çiti. "Çiti soyup devam etmek" başka bir ayrıştırıcıyla farklı sonuç doğurabilir |
| `h-03`, `h-04` | red | Belgenin önünde ya da arkasında açıklama var |
| `h-05` | red | `eylem` iki kez geçiyor; `json.loads` sessizce `dosya_sil` değerini tutardı |
| `h-06` | red | İç nesnede yinelenen `rol` |
| `h-07`, `h-08` | red | `NaN`, `-Infinity` |
| `h-09` | red | Art arda iki belge |
| `h-10` | kabul | Nesne olmayan kök; bu görevde serbesttir |
| `h-11` | kabul | `İstanbul` → `İstanbul` |
| `h-12` | kabul (`inf`) | **Sınır:** `1e400` bir `NaN`/`Infinity` sabiti değil, sayı belirtecidir. `parse_constant` onu görmez ve Python `float('inf')` üretir. Görev 2'deki `math.isfinite` kontrolü bu yüzden ayrıca gereklidir. |

Dört bozuk girdi `ValueError` almalıdır: `null`, `42`, boş string ve yalnız boşluk.

## veri/kararlar.json (Görev 2)

On dört karar nesnesi vardır. Her birinin `beklenen_kabul` alanı bulunur. Kabul edilenler `k-01`, `k-10` (120 karakter sınırı), `k-12` (`1`) ve `k-13` (`0`) örnekleridir. Reddedilenler:

- `True`, `"0.9"`, `1.5` ve `-0.1` güvenceler
- Ek `arac` alanı
- `dosya_sil` ve `Ozetle` eylemleri
- Boş, 121 karakterlik ve sayı türündeki metinler

Kabul edilen kararlarda girdi değişmemeli ve dönüş yeni bir dict olmalıdır. İki bozuk girdi (`null` ve liste) `ValueError` almalıdır.

## veri/komut_vakalari.json (Görev 3)

Dokuz vaka vardır; `beklenen: null`, `ValueError` demektir.

- `c-01`: Güvence `0.75` tam eşikte; `OZET` üretir.
- `c-02`: Güvence `0.7499`; `INCELE` üretir.
- `c-05`: Düşük güvenceli kararın metni (`GİZLİ NOT`) inceleme kaydına taşınmaz; `icerik` boş kalır.
- `c-06`, `c-07`: `dosya_sil` ve `__import__` eylemleri hiçbir komuta çevrilmez.

## Kalıcılık ve kontrol

Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar; **kalıcılık yoktur**. Kontrol adımı bu dosyalardan bağımsız, gizli verilerle sınar.

Son adımın kendi dosyası ayrıdır: `web/data/ai-saldiri-10-json.txt`. Bu dosyanın kalıcı kopyası `calisma/ai-saldiri-10/kararlar.json` yolunda tutulur.
