# ai-saldiri-07 · Görünür Sentetik Örnek Veri

Bu klasördeki sorgular, yanıtlar ve gözlemler **elle yazılmış sentetik kayıtlardır**. Hiçbiri gerçek model yanıtı değildir. Bir uç noktadan model çıkarıldığını ya da bir modelin kimliğini göstermez.

## veri/sorgu_seti.json (Görev 1)

- **`sorgular`:** Üç sorgu; toplam 3 + 2 + 1 = 6 çağrı.
- **`kaset`:** Her sorgu metni için sırayla verilecek yanıtlar. Gerçek sistemde bu, kayıttan oynatılan (replay) bir HTTP kaseti gibi düşünülebilir. Başlangıç kodundaki adaptör her çağrıda sıradaki yanıtı verir.
- **`beklenen`:** Altı kayıt; tekrar numaraları `1`'den başlar. `q-renk` üçüncü tekrarda `Hayır.` döndürür; görev 2'de bu vaka kararsız sayılır.
- **`bozuk_setler`:** Yedi bozuk set vardır: `tekrar` değeri `0`, `5`, `true` ya da `2.0`; yinelenen kimlik; ikinci sorgusu boş kimlikli set; `null` metin. Hepsi `ValueError` almalıdır ve model **hiç çağrılmamalıdır**. Altıncı sette ilk sorgu geçerlidir; doğrulamayı çağrılarla iç içe yapan kod bu sorgu için modeli iki kez çağırır.
- **`kesinti`:** Adaptör bu sorgu için `TimeoutError` yükseltir. Hata yutulmamalı, `HATA` gibi sahte bir yanıta da çevrilmemelidir.

## veri/gozlem_kayitlari.json (Görev 2)

Altı kayıt karışık sıradadır. Beklenen sonuç dosyanın `beklenen` alanındadır: `gozlem=6`, `kararli_vaka=2`, `kararlilik=2/3`, `imza=0f7108a858bf…`.

- `q-renk` tekrar 3, `HAYIR\n` yanıtını taşır; satır sonu farkı da farklı yanıt sayılır. `strip()` ile "düzeltmek" vakayı yanlışlıkla kararlı gösterir ve imzayı değiştirir.
- `Türkçe` yanıtı `ensure_ascii=False` gerektirir; `ensure_ascii=True` başka bir imza üretir.
- Kararlılık **vaka** sayısına bölünür (3), kayıt sayısına (6) değil.

Üç bozuk küme `ValueError` almalıdır: yinelenen anahtar, `true` tekrar ve `null` yanıt.

## veri/uc_karsilastirma.json (Görev 3)

İki uç noktanın aynı sorgu setine yanıtları vardır. `uc_b` karışık sıradadır. Beklenen sonuç: `gozlem=5`, `ayni=4`, `eslesme=0.8`, `farkli_vakalar=["q-sayi"]`.

`eksik_uc_b`, `q-sayi` gözlemleri atılmış kayıttır. Yalnız ortak anahtarlarla karşılaştıran bir kod bu durumda yapay olarak `1.0` eşleşme bulur. Doğru davranış `ValueError` yükseltmektir.

Üç bozuk çift `ValueError` almalıdır: eksik anahtar, yinelenen anahtar ve `null` yanıt.

## Kalıcılık ve kontrol

Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar; **kalıcılık yoktur**. Kontrol adımı bu dosyalardan bağımsız, gizli verilerle sınar.

Son adımın kendi örnek dosyası ayrıdır: `ornek_gozlem.jsonl`. Bu dosya `tracks/ai-saldiri/veri/ai-saldiri-07-ornek-gozlem.jsonl` kaynağından kopyalanır.
