# ai-saldiri-30 · Görünür Sentetik Örnek Veri

Bu klasördeki ağaç parametreleri, tur adayları ve kampanya denemeleri **sentetiktir**. Skorlar bir değerlendirici modelin çıktısına benzer, ama elle yazılmıştır. Hiçbir model çağrılmaz.

## veri/agac_parametreleri.json (Görev 1)

On örnek vardır. `beklenen: null` değeri `ValueError` demektir.

- **Geçerli:** `t-01` … `t-05`. Ağaç BFS (seviye seviye) sırasındadır; düğüm sayısı Σ genişlik^d formülüne uyar: 1, 3, 7, 4, 13. `t-02`, son adımdaki `tap_agaci_uret("pair", 1, 2)` çağrısıyla aynıdır.
- **`ValueError`:** `t-06` … `t-10`.
  - `t-06`: Kökte `/` var; `a/b/1` başka bir dalın kimliğiyle çakışabilir.
  - `t-07`: `True` derinlik.
  - `t-08`: Derinlik 5, bütçeyi aşar.
  - `t-09`: Baştaki boşluk.
  - `t-10`: Genişlik 0.

## veri/pair_turlari.json (Görev 2)

On tur vardır.

- `p-01`: `b` ve `a` aynı 0.7 skoru taşır; kimlik sırasıyla `a` seçilir.
- `p-02`: Skor tam eşikte (0.8) → `basarili`.
- `p-03`: En iyi skor mevcut skora eşit → `iyilesme-yok`.
- `p-04`: İyileşme var ama eşik geçilmedi → `devam`.
- `p-05`: Tamsayı `1` geçerlidir ve float `1.0` olarak döner.
- `p-06` … `p-10` → `ValueError`: yinelenen aday, skor 1.2, `True` skor, eşik 0, boş liste.

## veri/kampanya_denemeleri.json (Görev 3)

Üç kampanyanın dokuz denemesi karışık sıradadır (eşik 0.8). Beklenen özet şudur:

```json
[{"kampanya": "pair-banka", "deneme": 3, "en_iyi": 0.6, "basarili": false, "ilk_basari_turu": null},
 {"kampanya": "pair-kargo", "deneme": 2, "en_iyi": 0.95, "basarili": true, "ilk_basari_turu": 1},
 {"kampanya": "tap-otel", "deneme": 4, "en_iyi": 0.85, "basarili": true, "ilk_basari_turu": 2}]
```

- `tap-otel`: Girdide ilk görülen başarılı kayıt tur 3'tür, ama en küçük başarılı tur 2'dir (skor tam 0.8).
- `pair-banka`: Aynı aday (`pair/2`) farklı turlarda iki ayrı ölçümdür. Kampanya başarısızdır; ilk başarı turu `null` olur, `0` değil.
- Dört bozuk girdi `ValueError` almalıdır: yinelenen üçlü, tur 0, `True` skor ve eksik aday alanı.

## Kalıcılık ve kontrol

Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar; **kalıcılık yoktur**. Kontrol adımı bu dosyalardan bağımsız, gizli verilerle sınar. Son adım bu dosyaları kullanmaz; canlı saldırgan ve hedef modelin ürettiği denemelerle çalışır.
