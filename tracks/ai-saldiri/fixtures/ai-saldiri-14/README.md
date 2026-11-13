# ai-saldiri-14 · Görünür Sentetik Örnek Veri

Bu klasördeki belgeler, sorgular ve retrieval kayıtları **sentetiktir**. `BREACH:CANARY-42` satırı ve terim doldurma (keyword stuffing) yapılmış belgeler zararsız eğitim yönlendirmeleridir. Gerçek bir bilgi tabanından alınmamıştır.

## veri/belgeler.json (Görev 1)

Dört belge karışık kimlik sırasıyla verilir. Beklenen manifesto dosyanın `beklenen` alanındadır. Kayıtlar `kb-01`…`kb-04` sırasındadır, belge metni manifestoya kopyalanmaz.

- `kb-02` ve `kb-03` metinleri yalnız sondaki satır sonuyla ayrılır; özetleri farklıdır. Metni `strip()` ile özetlemek iki farklı içeriği aynı özete indirir.
- `kb-01` Türkçe karakter taşır; manifestoda `ensure_ascii=False` gerekir.

Dört bozuk küme `ValueError` almalıdır:

- Yinelenen kimlik
- Boş kaynak
- `null` metin
- Belgenin kendi `guven: "guvenilir"` alanı (şema tam olmalıdır)

## veri/corpus.json (Görev 2)

Beş belge ve beş sorgu vardır; her sorgunun `beklenen` alanı bulunur.

| Sorgu | k | Beklenen | Not |
|---|---|---|---|
| `s-1` `parola sıfırlama nasıl yapılır` | 3 | `d-03`, `d-01`, `d-04` | Zehirli `d-03` terim tekrarıyla 5 skor alır ve ilk sıraya çıkar |
| `s-2` `PAROLA parola` | 2 | `d-03`, `d-01` | Sorgudaki tekrar bir kez sayılır; `d-01` ile `d-04` eşittir, kimlik sırası kazanır |
| `s-3` `vpn kılavuzu` | 2 | `d-02` | `VPN'e` metni `\w+` ile `vpn` ve `e` belirteçlerine ayrılır. Yalnız bir belge pozitif skorludur |
| `s-4` `parola` | 0 | — | Girdi yine doğrulanır |
| `s-5` `toplantı odası` | 2 | — | Sıfır skorlu belgeler getirilmez |

Altı bozuk girdi `ValueError` almalıdır: `k=True`, `k=6`, `k=-1`, boş sorgu, yinelenen kimlik ve fazladan alan.

## veri/retrieval_kayitlari.json (Görev 3)

Üç vakanın temiz ve zehirli retrieval kayıtları karışık sıradadır. Beklenen rapor dosyanın `beklenen` alanındadır.

- `q-parola`: Canary yalnız zehirli kümede (`d-03`).
- `q-vpn`: `d-09` iki kümede de canary taşır. Bu, zehirlemenin yeni bir etkisi değildir; `her_iki` alanına yazılır.
- `q-izin`: Temiz kümedeki `d-07` (`\r\n` satır sonlu) zehirli kümede kaybolur. Zehirli kümedeki `d-06` canary'yi yalnız alıntılar. Vaka `farkli` listesindedir, ama `yalniz_zehirli` boştur.

Dört bozuk girdi `ValueError` almalıdır: eksik zehirli kayıt, yinelenen küme, küme içinde yinelenen belge kimliği ve boş canary.

## Kalıcılık ve kontrol

Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar; **kalıcılık yoktur**. Kontrol adımı bu dosyalardan bağımsız, gizli verilerle sınar.

Son adımın kendi dosyası ayrıdır: `web/data/ai-saldiri-14-corpus.txt`. Bu dosyanın kalıcı kopyası `calisma/ai-saldiri-14/corpus.json` yolunda tutulur.
