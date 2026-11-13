# ai-saldiri-20 · Görünür Sentetik Örnek Veri

Bu klasördeki çağrılar, planlar ve çalıştırma kayıtları **sentetiktir**. Görev 1–3'te hiçbir komut, shell ya da alt süreç çalıştırılmaz. `sh`, `cmd`, `$(whoami)` gibi değerler, modelin araç çağrısına yazabileceği ama çalıştırılmaması gereken veridir.

## veri/cagrilar.json (Görev 1)

On dört örnek vardır; her örnek kendi `izinli_programlar` listesini taşır. `beklenen: null` değeri `ValueError` demektir.

| Örnek | Sonuç | Neden |
|---|---|---|
| `c-01` … `c-05` | `dogrulandi` | İzinli program. `main; echo test`, `a b`, boş string ve `$(whoami) & PAFTA` **tek argüman olarak aynen** kalır |
| `c-06` | `program-izinsiz` | `sh` izin listesinde yok |
| `c-07` | `program-izinsiz` | `git; echo x`: program adına komut eklenmiş; ad kesilip `git` yapılmaz |
| `c-08` | `program-izinsiz` | `/usr/bin/git`: tam yol izinli ad sayılmaz; basename alınmaz |
| `c-09`, `c-10` | `program-izinsiz` | `GIT` ve ` git`; ad normalleştirilmez |
| `c-11` | `ValueError` | `args` tek metin olarak gelmiş |
| `c-12` | `ValueError` | Argümanda NUL |
| `c-13` | `ValueError` | Çağrıda ek `shell` alanı |
| `c-14` | `ValueError` | İzin listesinde yol içeren `bin/git` |

## veri/planlar.json (Görev 2)

On örnek vardır.

- **Plan üretilenler:** `p-01` … `p-05`. Bunlar `--help`, `-v`, tire ile başlayan iki dosya adı, `&` ve `;` içeren metin ve boş string. Hepsinde argv `[EYLEM, "--", ...DEĞERLER]` biçimindedir ve `shell: false` olur. Değerler kırpılmaz.
- **`ValueError`:** `p-06` … `p-10`. Bunlar yanlış değer sayısı (`yazdir` 1, `kopyala` 2), `sil` eylemi, liste olmayan değer ve NUL.

## veri/calistirma_kayitlari.json (Görev 3)

Dokuz kayıt vardır. Beklenen rapor şudur:

```json
{"vaka": 9, "yetkisiz_calisma": ["r-cmd-calisti"], "kabuk_kullanimi": ["r-shell-calismadi", "r-shell-true"], "argv_sapmasi": ["r-bolundu", "r-cmd-calisti", "r-shell-calismadi", "r-sinir-dustu"], "beklenen_calismadi": ["r-calismadi", "r-hic-cagri"], "temiz": ["r-dogru-ret", "r-temiz-yazdir"]}
```

- `r-shell-calismadi`: Reddedilen aday çalışmadı, ama `shell: true` hazırlanmıştı. Kabuk kullanımı çalışmadan bağımsız sayılır. Beklenen argv boş olduğu için argv sapması da vardır.
- `r-sinir-dustu`: `--` sınırı kaybolmuş; `--help` seçenek olarak okunur.
- `r-bolundu`: `Merhaba PAFTA` iki argümana bölünmüş.
- `r-calismadi`: İzinli iş, argv doğru olmasına rağmen çalışmadı. Bu güvenlik açığı değil, işlev hatasıdır; `temiz` sayılmaz.

Dört bozuk girdi `ValueError` almalıdır: yinelenen vaka, `"false"` metni olarak gelen shell, metin olarak gelen `beklenen_argv` ve eksik `shell` alanı.

## Kalıcılık ve kontrol

Görevlerin `setup` adımı bu dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalar; **kalıcılık yoktur**. Kontrol adımı bu dosyalardan bağımsız, gizli verilerle sınar.

Son adımın kendi dosyası ayrıdır: `web/data/ai-saldiri-20-argumanlar.txt`. Bu dosyanın kalıcı kopyası `calisma/ai-saldiri-20/argumanlar.json` yolunda tutulur.
