# ai-savunma-19 · Görünür Sentetik Örnek Veri

Bu klasördeki dosyalar **tamamen sentetiktir**. Gerçek bir Qdrant koleksiyonu, gerçek müşteri ya da gerçek sözleşme değildir. Kiracı adları uydurmadır.

## veri/vektor_politikasi.json

- `politika`: İzinli kiracılar `acme` ve `globex`. En düşük skor 0.5, en çok 3 sonuç. Filtre zorunlu, kiracılar arası erişim kapalı.
- `bozuk_politikalar`: Reddedilmesi gereken beş politika var: kiracılar arası erişim açık, filtre isteğe bağlı, `*` kiracısı, 500 sonuç sınırı, bool skor.

## veri/vektor_sorgulari.json

| Sorgu | Ne gösterir | Doğru sonuç |
|---|---|---|
| `q-normal` | Olağan sorgu | kabul |
| `q-filtre-oyunu` | `acme` oturumu `globex` filtresi gönderiyor | `filtre` |
| `q-tanimsiz` | İzinli olmayan kiracı | `kiraci` |
| `q-genis` | 50 sonuç istiyor | `top_k` |
| `q-hepsi` | Üç nedenin hepsi | `kiraci`, `filtre`, `top_k` |
| `q-sinir` | Sınıra tam eşit `top_k=3` | kabul |

Kiracı **oturumdan**, filtre ise **istemciden** gelir. Filtreye güvenmek, istemciye başka kiracıyı seçme hakkı vermek demektir.

## veri/vektor_kayitlari.json

Filtresiz bir vektör aramasından dönen yedi ham sonuç. `getirme_sorgusu` (`acme`, `top_k=3`) için doğru sonuç `a-iade`, `a-sss`, `a-kargo` olur:

- **`g-sozlesme` (0.97) ve `g-iade` (0.90):** En yüksek skorlu iki kayıt `globex` kiracısına aittir, sonuca **girmez**. Bunlardan biri başka bir müşterinin özel indirim sözleşmesidir. Kiracılar arası bir sızıntıda tam olarak bu tür bir veri dışarı çıkar.
- **`a-iade` ve `a-sss`:** Eşit skorludur (0.88), bu yüzden kimlik sırasına göre dizilir.
- **`a-sinir` (0.5):** Eşiğe eşittir, yani skor açısından uygundur. Ama `top_k=3` sınırı dolduğu için dışarıda kalır.
- **`a-alakasiz` (0.32):** Eşiğin altındadır.

`bozuk_kayitlar` içinde reddedilmesi gereken üç kayıt var: 1.2 skor, boşluklu kimlik, NUL karakterli metin.

## Kalıcılık ve kontrol

Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar, **kalıcılık yoktur**. Kontrol adımı bu dosyalardan bağımsız, gizli verilerle sınar.

Son adımdaki gerçek deney bu dosyaları kullanmaz. O adımda skorlar kurulu `all-minilm:22m` gömme modeliyle gerçekten hesaplanır.
