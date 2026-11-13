# ai-guvence-07 · Görünür Sentetik Örnek Veri

Bu klasördeki dosyalar **tamamen sentetik** eğitim örnekleridir. Gerçek bir sinir ağının gradyanı, canlı FGSM saldırısı veya ölçüm kaydı değildir:

- `veri/fgsm_ornekleri.json`: 8 pikselli girdi satırları (`x`, `[0,1]` aralığında) ve aynı boyutta gradyanlar. `satir-02-kirpma` 0 ve 1 sınırına yakın değerlerle kırpmayı, `satir-03-sifir-gradyan` işaretin sıfır olduğu durumu gösterir. `bozuk-aralik` (1.2 değeri) ve `bozuk-boyut` (x ile gradyan boyu farklı) bilerek geçersizdir; doğrulama işlevin bunları reddetmelidir.
- `veri/epsilon_gozlemleri.json`: ε-doğruluk eğrisi gözlemleri. ε=0.3 satırında kırpma yüzünden `l_inf` ε'dan küçüktür; ε=0.2 ve 0.3 aynı kaybı verir (doyma, eşitlikte düşük ε seçilir). `bozuk_gozlem` L∞ bütçesini aştığı için reddedilmelidir.

Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar (**kalıcılık yoktur**; kopyada yaptığın değişiklik bir sonraki çalıştırmada sıfırlanır). Kontrol adımı bu dosyalardan bağımsız, gizli verilerle sınar. Son adımdaki gerçek deney bu dosyaları kullanmaz; gradyanı eğitilmiş bir PyTorch modelinden autograd ile alır.
