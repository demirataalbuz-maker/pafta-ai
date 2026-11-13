# ai-savunma-30 — Sentetik Veri Seti (Uçtan Uca Yerel Purple Tatbikatı)

Bu klasördeki tüm dosyalar **elle yazılmış sentetik** eğitim verisidir; gerçek bir tatbikatın, telemetri sisteminin veya modelin kaydı değildir.

- `tatbikat/faz_kayitlari.json`: Tek tek faz kayıtları (`kayitlar`). Bazıları kuralları bozar (kanıtsız telemetri, bool zaman); doğrulama bunları reddetmelidir.
- `tatbikat/tatbikat_akisi.json`: Karışık sırayla verilmiş beş fazlı bir akış (`kayitlar`).
- `tatbikat/purple_kayitlari.json`: Guardrail fazı başarısız olan bir tatbikat (`kayitlar`).

Çalışma klasörüne her çalıştırmada yeniden kopyalanır; değişikliklerin kalıcı değildir. Testler bu dosyalardan ayrı, görmediğin verilerle sınar.
