# ai-saldiri-40 · Görünür Örnek Veri (Sentetik)

Bu klasördeki dosyalar `ai-saldiri-40` (**Denial-of-Wallet Saldırısı: Pahalı Üretim, Bağlam Şişirme ve Ajan Döngüsü**) dersinin deterministik görevleri için hazırlanmış **sentetik** örnek verilerdir (canlı fatura veya üretim telemetrisi değildir):

- `tuketim/uretim_adaylari.json` — Normal kısa sorgular ile aşırı çıkış üretimi tetikleyen (`sayma-sponge`, `agac-genisletme`, `cok-dilli-tekrar`) isteklerin giriş/çıkış token, süre ve bitiş nedeni (`stop` / `length`) kayıtları.
- `tuketim/baglam_oturumlari.json` — Çok turlu sohbetlerde RAG parça şişirmesi ve geçmiş birikiminin toplam giriş/çıkış token maliyetini nasıl katladığını gösteren oturum profilleri.
- `tuketim/ajan_donguleri.json` — Dolaylı enjeksiyon veya hatalı araç geri bildirimi yüzünden aynı `(arac, arg_ozeti)` çağrısını tekrarlayarak tur sınırına vuran ajan izleri.

> **Kalıcılık notu:** Her çalıştırmada (`setup`) bu dosyalar geçici çalışma klasörüne yeniden kopyalanır; çalışma zamanında yapılan değişiklikler kalıcı değildir.
