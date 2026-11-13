# ai-savunma-10 · Görünür Sentetik Örnek Veri

Bu klasördeki guardrail sonuçları, deneme geçmişleri ve yanıt adayları **sentetiktir**. `api_key=...`, `Bearer ...` ve PEM başlıkları gerçek sır değildir. Hiçbir model, guardrail servisi ya da gerçek bekleme (`sleep`) kullanılmaz.

## veri/guardrail_sonuclari.json (Görev 1)

On sonuç vardır. `beklenen: null` değeri `ValueError` demektir.

- `g-01`: Model kanalını açan **tek** durum budur: `tamam + izin + risk yok`.
- `g-02`, `g-03`: İzin verilmiş ama risk taşıyan sonuç ve açık ret → `guvenli_yedek` / `politika`.
- `g-04`, `g-05`: Servis hatası ve zaman aşımı → `yeniden_dene_degerlendir`.
- `g-06`: Akıştan atlanan guardrail → `guvenli_yedek` / `guardrail_atladi`. **İzin sayılmaz.**
- `g-07` … `g-10` → `ValueError`: hata durumunda `izin` kararı, `tamam` durumunda boş karar, ters sıralı riskler, bilinmeyen `devre_disi` durumu.

## veri/deneme_senaryolari.json (Görev 2)

Sekiz senaryo vardır (ayar: en fazla 4 deneme, taban 250 ms, tavan 800 ms).

- `r-01`: 250 ms + 500 ms bekleme, sonra başarı (`dur`).
- `r-02`: Üçüncü bekleme 1000 ms yerine tavan nedeniyle 800 ms olur. Dördüncü denemede bütçe dolar → `guvenli_yedek`. Toplam bekleme 1550 ms.
- `r-03`, `r-04`: Kalıcı hata ve tek denemelik bütçe → hemen `guvenli_yedek`.
- `r-05` … `r-08` → `ValueError`: kalıcı hatadan sonra deneme, bütçeden fazla kayıt, tabandan küçük tavan, float taban.

## veri/geri_donus_kayitlari.json (Görev 3)

Yedi aday vardır.

- Yalnız `temiz` aynen geçer (`ham_icerik_tasindi: true`).
- `bearer`, `pem`, `bosluk` ve `bos` model kanalında olsalar da sabit güvenli yedeğe düşer.
- `yedek-hata` adayı `api_key=` içeren bir teknik hata izi taşır. Kullanıcıya bu metin değil, sabit yedek cümle gider.
- `tekrar` → `yeniden_dene`, `yanit: null`.

Dört bozuk girdi `ValueError` almalıdır: yinelenen kimlik, bilinmeyen kanal, 2001 karakterlik aday ve `None` aday.

## Kalıcılık ve kontrol

Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar; **kalıcılık yoktur**. Kontrol adımı bu dosyalardan bağımsız, gizli verilerle sınar. Son adım bu dosyaları kullanmaz; yerel modelin iki senaryodaki gerçek çıktılarıyla çalışır.
