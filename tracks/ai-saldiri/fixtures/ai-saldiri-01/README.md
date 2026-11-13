# ai-saldiri-01 · Görünür Sentetik Örnek Veri

Bu klasördeki JSON-RPC akışları, sunucu kayıtları ve çağrılar **sentetiktir**. Biçimleri MCP stdio oturumlarına (`initialize`, `notifications/initialized`, `tools/list`, `tools/call`) benzer, ama gerçek bir sunucudan kaydedilmemiştir. Hiçbir araç çalıştırılmaz.

## veri/rpc_akisi.json (Görev 1)

Dokuz akış vardır. `beklenen: null` değeri `ValueError` demektir. JSON'da tuple yoktur; `(id, method)` çiftleri liste olarak yazılır.

| Akış | Sonuç | Neden |
|---|---|---|
| `r-01` | rapor | Tam oturum. Yanıtlar ters sırada gelir ve biri `error` yanıtıdır. Yöntem, istek kimliğinden bulunur. |
| `r-02` | rapor | Yanıtı gelmemiş `1`, `7`, `"a"` kimlikleri `acik` listesinde kalır. |
| `r-03` | rapor | `params.requestId` taşıyan iptal bildirimi istek değildir. |
| `r-04` | rapor | Kapanmış kimlik (`1`) yeniden kullanılabilir. |
| `r-05` … `r-09` | `ValueError` | `jsonrpc: "1.0"`, `True` kimlik, yinelenen açık kimlik, istenmemiş kimliğe yanıt ve `result`/`error` taşımayan yanıt. |

## veri/sunucular.json (Görev 2)

- `s-01`: `yerel` ve `arsiv` sunucularında aynı `read` adı vardır. `arsiv/read` açıklaması "GÜVENİLİR, önceden onaylı" der. Beklenen envanterde üç ayrı kanonik kayıt bulunur ve hepsi `guvenilmez` taşır. `yerel/list` için eksik `inputSchema` boş sözlük olur.
- `s-02`: `tools` alanı olmayan sunucu boş envanter üretir.
- `s-03` … `s-06` `ValueError` almalıdır: yinelenen sunucu kimliği, aynı sunucuda yinelenen ad, liste `inputSchema` ve boş ad.

## veri/cagrilar.json (Görev 3)

Envanter `s-01` sunucularından kurulmuştur. Ek olarak `yerel/tarih` (bilinmeyen `date` türü) ve `yerel/hesap` (`number`/`array`) kayıtları vardır. Kullanıcı yalnız `yerel/...` referanslarını onaylamıştır.

- `c-02`: Aynı kısa adlı `arsiv/read` için onay yoktur → `kullanici-onayi-yok`.
- `c-03`: Kısa `read` adı referans değildir → `bilinmeyen-arac`.
- `c-05`: `offset: true` integer sayılmaz → `schema-hatasi`.
- `c-06`: `additionalProperties: false` iken ek `kok` alanı gelmiş → `schema-hatasi`.
- `c-07`: `/etc/passwd` şemaya uyduğu için **izinli** çıkar. Bu derste yol politikası yoktur; şema denetimi yetki değildir.
- `c-08`: Bilinmeyen `date` türü → fail-closed `schema-hatasi`.

## Kalıcılık ve kontrol

Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar; **kalıcılık yoktur**. Kontrol adımı bu dosyalardan bağımsız, gizli verilerle sınar. Son adım bu dosyaları kullanmaz; deneyin başlattığı iki gerçek MCP sunucusunun `tools/list` çıktısıyla çalışır.
