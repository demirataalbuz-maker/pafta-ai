# ai-saldiri-09 · Görünür Sentetik Örnek Veri

Bu klasördeki metinlerin hepsi **sentetik model çıktılarıdır**. İçlerindeki `<img onerror>`, `<script>` ve `javascript:` parçaları ölçülecek veridir. Bunlar tarayıcıda çalıştırılmaz ve hiçbir adrese istek gönderilmez.

## veri/html_ornekleri.json (Görev 1)

| Örnek | Beklenen çıktı |
|---|---|
| `h-01` | `&lt;img src=x onerror=&quot;alert(1)&quot;&gt;` |
| `h-02` | `Fiyat: 5 &lt; 7 &amp; &#x27;indirim&#x27; &gt; 0` |
| `h-03` | `&amp;lt;b&amp;gt; zaten kaçışlı görünüyor` (ham girdi bir kez kodlanır) |
| `h-04` | `&lt;a title=&#x27;x&#x27; href=&quot;#&quot;&gt;bağlantı&lt;/a&gt;` |
| `h-05` | boş string |

Üç bozuk girdi (`null`, `42`, liste) `ValueError` almalıdır.

## veri/url_ornekleri.json (Görev 2)

Yalnız ilk iki adres aynen döner:

- `https://docs.pafta.test/ders?id=9#bolum`
- `HTTPS://Pafta.test/`: şema karşılaştırması büyük/küçük harfe duyarsızdır.

Diğer on adres `None` döner:

- `javascript:` ve `JaVaScRiPt:`
- `data:`
- Kullanıcı adı ve parola taşıyan adres
- `https:///yol` (host yok)
- `:99999` (geçersiz port)
- Boşluk içeren adres
- `\\` içeren adres
- Sekme içeren adres
- Şemasız `//pafta.test/x`

İki bozuk girdi (`null`, `12`) `ValueError` almalıdır.

## veri/markdown_ornekleri.json (Görev 3)

| Örnek | Beklenen çıktı |
|---|---|
| `m-01` | `Kaynak: [belge](https://docs.pafta.test/a?x=1&amp;y=2)` |
| `m-02` | `tıkla)` (dar regex ilk `)` karakterinde durur; geriye kalan parantez düz metin olur) |
| `m-03` | `&lt;img src=x onerror=&quot;alert(1)&quot;&gt; ve [site](https://pafta.test)` |
| `m-04` | `gizli` (kullanıcı bilgili hedef atılır) |
| `m-05` | `[çok\nsatır](https://pafta.test)` (çok satırlı bağlantı ayrıştırılmaz; düz metin olarak kalır) |
| `m-06` | `[&quot;&gt;&lt;script&gt;x&lt;/script&gt;](https://pafta.test)` |

Hiçbir sonuçta ham `<` karakteri kalmamalıdır. İki bozuk girdi `ValueError` almalıdır.

## Kalıcılık ve kontrol

Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar; **kalıcılık yoktur**. Kontrol adımı bu dosyalardan bağımsız, gizli verilerle sınar.

Son adımın düzenlenebilir dosyası ayrıdır: `web/data/ai-saldiri-09-ciktilar.txt`. Bu dosyanın kalıcı kopyası `calisma/ai-saldiri-09/ciktilar.json` yolunda tutulur.
