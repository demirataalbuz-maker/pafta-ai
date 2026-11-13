# ai-savunma-25 · Görünür Sentetik Örnek Veri

Bu klasördeki dosyalar **tamamen sentetiktir**. Gerçek bir olay kaydı, gerçek kanıt dosyası ya da gerçek kişi değildir. Özetler, örnek dosya adlarının SHA-256 değeridir.

## veri/kanit_manifestolari.json

Bir olaya (`INC-2026-041`) ait üç geçerli manifesto var:

- Bir gateway logu.
- 2,4 GB'lık bir model ağırlığı.
- 0 baytlık boş bir yedek. Boş dosyanın da geçerli bir SHA-256 özeti vardır.

`bozuk_manifestolar` içinde beş kayıt var: büyük harfli özet, 40 karakterlik özet, boşluklu olay kimliği, negatif bayt ve bool zaman.

## veri/olaylar.json

Dört olay, sıralanmamış biçimde verilir:

| Olay | Seviye | Kategori |
|---|---|---|
| `INC-041` | kritik | sızıntı |
| `INC-042` | yüksek | yetkisiz erişim |
| `INC-043` | orta | model sapması |
| `INC-044` | düşük | prompt injection, kanıt listesi boş |

Doğru planda bu sırayla dizilirler. Yalnız kritik ve yüksek olaylar `erisimi_sinirla` adımını alır. `bozuk_olaylar` içinde üç kayıt var: `acil` seviyesi, başında boşluk olan sistem adı ve yinelenen kanıt kimliği.

## veri/devir_zinciri.json

`kayitlar` listesinde iki kanıtın devir kayıtları **karışık sırada** durur:

- `gateway-log`: üç adımda otomatik toplayıcıdan nöbetçi mühendise, oradan olay yöneticisine ve en son adli depoya geçer. Son iki adım aynı saniyede olur; zaman eşitliği geçerlidir.
- `sohbet-kaydi`: tek adımlıktır.

`bozuk_zincirler` içinde reddedilmesi gereken beş zincir var:

- sıra atlayan,
- zamanı geriye giden,
- sahiplik zinciri kopan (gönderen, önceki alıcı değil),
- özeti yol üstünde değişen,
- sıfırdan başlamayan.

## Kalıcılık ve kontrol

Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar, **kalıcılık yoktur**. Kontrol adımı bu dosyalardan bağımsız, gizli verilerle sınar.

Son adımdaki gerçek deney bu dosyaları kullanmaz. O adımda yerel Ollama modelinin yanıtından gerçek bir kanıt dosyası yazılır, gerçek özeti hesaplanır ve dosyanın tahrif edilmiş bir kopyası özet karşılaştırmasıyla yakalanır.
