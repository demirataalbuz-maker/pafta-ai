# ai-savunma-35 · Görünür Sentetik Örnek Veri

`veri/benchmark.json` **sentetiktir**: hakem kararları ve ajan koşu kayıtları elle yazılmıştır. Zararlı istem ya da yanıt metni içermez.

## Alanlar

- `strongreject` (Görev 1): Üç yanıt için StrongREJECT rubriği (ret 0/1, ikna 1–5, özgüllük 1–5). `sr-b` reddedilmiş ama yüksek puanlıdır.
- `harmbench` (Görev 2): Dört davranış için hakem kararı (`evet`, `hayir`, `gecersiz`).
- `agentdojo` (Görev 3): İki savunma için saldırısız ve saldırılı koşu kayıtları. `saldiri_basarili`, AgentDojo'nun `security` alanıdır: True, saldırının **başarılı** olduğu anlamına gelir.

## Kalıcılık ve kontrol

Setup her Çalıştır/Kontrol Et adımında dosyayı yeniden kopyalar; **kalıcılık yoktur**. Kontrol adımı bu dosyadan bağımsız, gizli verilerle sınar. Final bu dosyayı kullanmaz; kurulu benchmark dosyaları, AgentDojo ve yerel Ollama modeliyle çalışır.
