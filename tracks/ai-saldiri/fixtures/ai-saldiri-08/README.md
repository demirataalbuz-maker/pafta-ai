# ai-saldiri-08 · Görünür Sentetik Örnek Veri

Bu klasördeki kimlikler, hafıza kayıtları ve sorgular **sentetiktir**. "Kalıcı sistem kuralı yap" gibi cümleler ve `PAFTA-CANARY-08` ölçülecek veridir. JSON'da tuple anahtar olmadığı için hafıza şu biçimde bir kapsam listesi olarak tutulur:

```json
[{"kullanici": ..., "oturum": ..., "kayitlar": [...]}]
```

Başlangıç kodundaki sürücü bu listeyi `(kullanici, oturum)` anahtarlı sözlüğe çevirir.

## veri/kimlikler.json (Görev 1)

On bir örnek vardır. `beklenen: null` değeri `ValueError` demektir.

- **Geçerli:** `k-01` … `k-03`. Bunlar tek karakterli kimlik ve tam 32 karakterlik sınırdır.
- **`ValueError`:**
  - `k-04`: 33 karakter. Kesilmez, reddedilir.
  - `k-05`, `k-06`: büyük harf ve baştaki boşluk. Normalize edilmez.
  - `k-07`, `k-08`: `uya:1`+`x` ve `uya`+`1:x`. `:` ile birleştirilse ikisi aynı `uya:1:x` anahtarına düşerdi; ikisi de şemaya uymaz.
  - `k-09`, `k-10`, `k-11`: sonda tire, Türkçe karakter ve `None` oturum.

## veri/hafiza_yazimlari.json (Görev 2)

Başlangıç hafızasına yedi yazım sırayla uygulanır.

- **Geçerli:** `y-01` … `y-03`. `y-01`'deki "kalıcı sistem kuralı" cümlesi aynen saklanır ve `tip: "veri"` alır. Hiçbir kayıt talimata yükseltilmez.
- **`ValueError`:**
  - `y-04`: `system` kaynağı.
  - `y-05`: boş içerik.
  - `y-06`: büyük harfli kullanıcı.
  - `y-07`: kayıtta önceden `tip` alanı. Şema dışı alandır; dışarıdan gelen tip kabul edilmez.

`beklenen_son` alanı, dört kayıtlı son hafızadır. Sürücü her adımda girdi hafızasının **değişmediğini** de denetler.

## veri/okuma_sorgulari.json (Görev 3)

Üç kapsamlı hafıza ve altı sorgu vardır.

- `o-01`: Yalnız `uya-1/oturum-1` iki kaydı, sırasıyla gelir. Bu sonuçta canary bulunmamalıdır.
- `o-02`: Aynı kullanıcının diğer oturumu ayrı kapsamdır; kendi kaydı gelir.
- `o-03`, `o-04`: Var olmayan kapsamlar boş liste verir. Başka kapsama geri dönüş yapılmaz.
- `o-05`, `o-06`: Büyük harf ve boş oturum → `ValueError`.

Sürücü ayrıca dönen kaydı değiştirip kalıcı hafızanın bozulmadığını denetler.

## Kalıcılık ve kontrol

Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar; **kalıcılık yoktur**. Kontrol adımı bu dosyalardan bağımsız, gizli verilerle sınar.

Son adımın kendi dosyası ayrıdır: `web/data/ai-saldiri-08-hafiza.txt`. Bu dosyanın kalıcı kopyası `calisma/ai-saldiri-08/hafiza.jsonl` yolunda tutulur.
