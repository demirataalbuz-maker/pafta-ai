# ai-saldiri-33 · Görünür Sentetik Örnek Veri

Bu klasördeki bütün süreler **sentetik** milisaniyelerdir. Gerçek bir sunucudan ölçülmemiştir ve hiçbir promptun içeriğini temsil etmez.

## veri/grup_olcumleri.json (Görev 1)

- **Hit süreleri:** 41,2 · 43,0 · 39,8 · 950,0. Sonuncusu, GC ya da kuyruk gecikmesi gibi tek bir aykırı ölçümdür.
- **Miss süreleri:** 88,1 · 91,4 · 86,9.
- **Doğru özet:** hit medyanı **42,1**, miss medyanı **88,1**, fark yaklaşık **46,0**. Ortalama kullanılsaydı hit değeri 268,5 çıkardı ve sonuç anlamsızlaşırdı.

Beş bozuk liste reddedilmelidir: `HIT`, 0 ms, `true`, `"40"` ve yalnız tek grup.

## veri/esik_olcumleri.json (Görev 2)

Eşik 60 ms; eşiğe eşit süre **hit** tahmin edilir.

| Ölçüm | Gerçek | Tahmin | Sonuç |
|---|---|---|---|
| 41 | hit | hit | TP |
| 60 | hit | hit (eşit) | TP |
| 95 | hit | miss | FN |
| 88 | miss | miss | TN |
| 55 | miss | hit | FP |
| 91 | miss | miss | TN |

Doğruluk, TPR ve TNR değerlerinin üçü de 2/3'tür. `yalniz_miss` verisinde gerçek hit yoktur. Bu yüzden `tpr` **`None`** olmalı, `0.0` değil.

Üç bozuk liste reddedilmelidir: `hit?`, -3 ms ve boş liste.

## veri/aday_olcumleri.json (Görev 3)

Kurallar: `min_ornek=3`, `min_fark_ms=5.0`. Medyan farkına göre doğru sıra:

| Aday | Fark | Sinyal |
|---|---|---|
| `aday-ortak-onek` | 50,0 | evet |
| `aday-a` | 6,0 | evet |
| `aday-b` | 6,0 | evet; eşitlik ada göre çözülür |
| `aday-esik-sinirinda` | 5,0 | evet; eşiğe eşit |
| `aday-tek-sansli` | 1,0 | hayır; ortalama kullanılsa tek 10 ms'lik ölçüm 26 ms'lik sahte fark üretirdi |
| `aday-gurultu` | 0,0 | hayır; kontrol adayı |

Üç bozuk liste reddedilmelidir: yalnız 2 örnek, yinelenen ad ve negatif süre.

## Kalıcılık ve kontrol

Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar, **kalıcılık yoktur**. Kontrol adımı bu dosyalardan bağımsız, gizli verilerle sınar. Son adım kendi ölçümlerini yerel Ollama'dan alır.
