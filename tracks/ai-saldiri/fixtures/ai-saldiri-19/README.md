# ai-saldiri-19 · Görünür Sentetik Örnek Veri

Bu klasördeki oturumlar, nesneler, onaylar ve karar kayıtları **sentetiktir**. Gerçek bir giriş sağlayıcısı, OAuth akışı ya da veritabanı yoktur; hiçbir dosya silinmez. `admin` gibi adlar, modelin araç çağrısına yazabileceği ama kimlik sayılmaması gereken değerlerdir.

## veri/oturum_cagrilari.json (Görev 1)

On bir örnek vardır; `beklenen: null` değeri `ValueError` demektir.

| Örnek | Sonuç | Neden |
|---|---|---|
| `k-01`, `k-11` | `bagli` | Doğrulanmış oturum ve aynı kullanıcı (`oku`, `paylas`) |
| `k-02` | `kimlik-uyusmazligi` | Model çağrıya `admin` yazmış; oturum kullanıcısı `ayse` |
| `k-03`, `k-04` | `oturum-dogrulanmamis` | Önce oturum denetlenir; ad eşleşse bile reddedilir |
| `k-09` | `kimlik-uyusmazligi` | `Ayse` ≠ `ayse`; ad normalleştirilmez |
| `k-05`, `k-06` | `ValueError` | `dogrulanmis` alanı `1` ya da `"true"`; bool değil |
| `k-07` | `ValueError` | Çağrıda ek `rol` alanı |
| `k-08` | `ValueError` | `sil` bu sözleşmede desteklenen eylem değil |
| `k-10` | `ValueError` | Oturumda boş kullanıcı |

## veri/nesne_istekleri.json (Görev 2)

Nesne `d1`'in sahibi `ayse`, paylaşım listesinde `mehmet` vardır. On beş istek vardır.

- **İzinli:** `n-01` (sahip okur), `n-02` (paylaşımlı okur), `n-06` (sahip, `d1`+`sil` onayıyla siler).
- **Reddedilen:**
  - `n-03`, `n-09`: paylaşımlı kullanıcı yazamaz, geçerli onayla bile silemez → `sahiplik-gerekli`.
  - `n-04`, `n-10`: yabancı kullanıcı okur (IDOR); okuma isteğindeki onay kararı değiştirmez → `nesne-erisimi-yok`.
  - `n-05`, `n-07`, `n-08`: onaysız, başka nesnenin onayıyla ya da `yaz` onayıyla silme → `islem-onayi-gerekli`.
- **`ValueError`:** `n-11` (`True` global onay), `n-12` (onayda ek `kapsam`), `n-13` (yinelenen paylaşım), `n-14` (paylaşım string), `n-15` (`paylas` eylemi).

## veri/karar_kayitlari.json (Görev 3)

Sekiz regresyon kaydı vardır. Beklenen rapor şudur:

```json
{"vaka": 8, "karar_bypassi": ["r-admin-adi", "r-baska-onay"], "calisma_bypassi": ["r-admin-adi", "r-idor-oku"], "yanlis_ret": ["r-hepsini-reddet", "r-onayli-sil"], "tutarli": ["r-sahip-yaz", "r-yabanci-sil"]}
```

- `r-idor-oku`: Politika `reddet` dedi, ama dispatcher yine de çalıştırdı. Karar doğru görünür; **çalışma bypass'ı** vardır.
- `r-baska-onay`: Karar bypass'ı var, ama eylem çalışmadı. Yalnız karar listesine girer.
- `r-paylasim-oku`: Karar doğru (`izinli`), ama meşru eylem çalışmadı. Hiçbir bypass listesine girmez, `tutarli` da değildir.
- `r-hepsini-reddet`: Beklenen `izinli`, karar `reddet`; eylem yine de çalıştı. `yanlis_ret` listesine girer. Beklenen `izinli` olduğu için çalışma bypass'ı sayılmaz.

Dört bozuk girdi `ValueError` almalıdır: yinelenen vaka, geçersiz karar, bool olmayan `calistirildi` ve ek `kullanici` alanı.

## Kalıcılık ve kontrol

Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar; **kalıcılık yoktur**. Kontrol adımı bu dosyalardan bağımsız, gizli verilerle sınar.

Son adımın kendi dosyası ayrıdır: `web/data/ai-saldiri-19-istekler.txt`. Bu dosyanın kalıcı kopyası `calisma/ai-saldiri-19/istekler.json` yolunda tutulur.
