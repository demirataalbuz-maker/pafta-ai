# ai-savunma-37 · Görünür Örnek Veri

## Alanlar

- `okumalar` (Görev 1): Yazarın gerçek `c2patool 0.28.4` koşusundan alınmış **ham** çıktılar (`rc`, `stdout`, `stderr`). Görüntü yazarın ürettiği sentetik 96×64 PNG'dir. İmza c2patool'un örnek **TEST** sertifikasıyla, saldırgan imzası ise koşu sırasında üretilip atılan yerel bir sertifikayla atılmıştır. Gerçek bir kişi ya da kurum yoktur.
- `degerler`, `bitler`, `tekrar`, `bozulmus` (Görev 2): Elle yazılmış küçük piksel değerleri. `bozulmus`, gömülmüş dizinin bazı değerleri ±1/±2 değiştirilmiş hâlidir.
- `esikler`, `kayitlar` (Görev 3): Elle yazılmış dönüşüm kayıtları.

## Kalıcılık ve kontrol

Setup her Çalıştır/Kontrol Et adımında dosyayı yeniden kopyalar; **kalıcılık yoktur**. Kontrol adımı bu dosyadan bağımsız, gizli verilerle sınar. Final bu dosyayı kullanmaz; her koşuda yeni bitler ve yeni saldırgan sertifikası üretip c2patool'u gerçekten çalıştırır.
