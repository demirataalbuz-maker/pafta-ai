# ai-saldiri-11 · Görünür Sentetik Örnek Veri

Bu klasördeki belgeler, paketler ve yanıtlar **sentetiktir**. İçlerindeki `<|system|>`, `SYSTEM:`, `{"role":"system"}`, `önceki talimatı yok say` ve `BREACH:` metinleri ölçülecek veridir. Bunlar sana ya da uygulamaya verilmiş talimatlar değildir. Gerçek kişisel veri ya da gerçek e-posta yoktur.

## veri/belgeler.json (Görev 1)

Beş belge vardır; her birinin `beklenen` alanında kanonik JSON paketi bulunur.

- `b-pdf-01`: Satır sonları ve `<|system|>` işareti. Pakette satır sonları `\n` kaçışı olarak görünür; yeni bir mesaj oluşmaz.
- `b-web-01`: Çift tırnak ve ters bölü. Elle kurulan JSON burada bozulur.
- `b-eposta-01`: Gövdede JSON biçimli sahte bir `role: system` nesnesi vardır. Bu nesne yalnız bir string değeri olarak kalır. E-posta kaynağı da `guvenilmez` olarak etiketlenir.
- `b-web-02`: `SYSTEM:` ile başlayan talimat; görev 2'de kullanılır.
- `b-pdf-02`: Boş metin; kabul edilir.

Beş bozuk girdi `ValueError` almalıdır:

- `slack` kaynağı
- Boş kimlik
- `null` metin
- **Belgenin kendi `guven: "guvenilir"` alanı.** Saldırgan güven düzeyini belgeyle göndermeye çalışıyor; şema tam olmadığı için reddedilir.
- `null`

## veri/paketler.json (Görev 2)

Görev metni ve dört paket vardır. Beklenen sonuç, dosyanın `beklenen` alanındaki iki mesajlı listedir. Belgeler kullanıcı mesajındaki tek JSON'un `belgeler` dizisinde **nesne** olarak bulunur. Paketlerin string halinin ikinci kez kodlanması yanlıştır.

`b-web-02` paketi `SYSTEM:` metni taşır. Bu paket ayrı bir `system` mesajına dönüşmemelidir.

Dört bozuk girdi `ValueError` almalıdır: `guvenilir` etiketli paket, JSON olmayan ham metin, liste kökü ve boş görev.

## veri/yanit_kayitlari.json (Görev 3)

Dört belge ve beş yanıt vardır.

| Yanıt | Beklenen | Neden |
|---|---|---|
| `y-1` | `e-01`, `w-01` | Aynı canary iki belgede de tam satır; ikisi de korunur |
| `y-2` | — | Yanıt canary'yi yalnız alıntılıyor |
| `y-3` | — | Yanıtta tam satır var, ama `w-02` canary'yi cümle içinde taşıyor |
| `y-4` | `p-01` | `\r\n` satır sonları; `splitlines()` tanır |
| `y-5` | — | Temiz yanıt |

Üç bozuk girdi `ValueError` almalıdır: yinelenen kimlik, 8 karakterden kısa canary ve `null` yanıt.

## Kalıcılık ve kontrol

Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar; **kalıcılık yoktur**. Kontrol adımı bu dosyalardan bağımsız, gizli verilerle sınar.

Son adımın kendi dosyaları ayrıdır: `web/data/ai-saldiri-11/eposta.txt` ve `web.txt`. Bunların kalıcı kopyaları `calisma/ai-saldiri-11/eposta.eml` ve `web.html` yollarında tutulur.
