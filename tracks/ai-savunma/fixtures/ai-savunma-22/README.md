# ai-savunma-22 · Görünür Sentetik Örnek Veri

Bu klasördeki dosyalar **tamamen sentetiktir**. Gerçek bir OpenTelemetry ya da SigNoz dışa aktarımı değildir. `detay` alanı yapay bir etikettir; gerçek prompt, kullanıcı verisi veya sır taşımaz.

## veri/telemetri_politikasi.json

- `politika`: En çok 20 olay ve 5000 ms süre sınırı tanımlar. İz ve sürüm kuralları zorunludur.
- `bozuk_politikalar`: Reddedilmesi gereken dört kayıt var: isteğe bağlı iz, 0 olay, 600000 ms süre ve bool olay sınırı.

## veri/otel_olaylari.json

Üç iz, dışa aktarımdaki gibi **karışık sırada** gelir:

| İz | Durum | Beklenen sonuç |
|---|---|---|
| `iz-7f3a` | Dört tür de birer kez var, 910 ms sürüyor | `tam` |
| `iz-91bc` | Guardrail zaman aşımından sonra yeniden denenmiş. İki guardrail olayı aynı 40 ms zamanında; sıralama kimliğe göre yapılır. 6300 ms sürüyor ve istek ortasında model sürümü `q4`'ten `q8`'e geçmiş. | `yinelenen`, `sure`, `surum` |
| `iz-c044` | Model bir araç çağrısı yaptığını söylüyor ama `arac` olayı hiç loglanmamış | `eksik` |

`bozuk_olaylar` listesindeki kayıtlar reddedilmelidir:

- bool zaman damgası
- boşluklu model sürümü
- başta boşluk ve TAB içeren detay
- tanımsız `log` türü

## Kalıcılık ve kontrol

Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar, **kalıcılık yoktur**. Kontrol adımı bu dosyalardan bağımsız, gizli verilerle sınar.

Son adımdaki gerçek deney bu dosyaları kullanmaz. O adımda olaylar, yerel Ollama modelinin araç çağrılı gerçek bir isteğinden ve gerçek zaman ölçümlerinden üretilir.
