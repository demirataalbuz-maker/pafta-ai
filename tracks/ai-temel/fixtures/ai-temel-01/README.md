# ai-temel-01 örnek verileri

Bu klasördeki bütün dosyalar elle yazılmış, küçük ve sentetiktir. Hiçbiri gerçek bir tokenizer'dan alınmamıştır.

- `kurallar.json`: Görevlerdeki sentetik BPE'nin öncelik sıralı birleştirme kuralları (`sol`, `sag`, `yeni`). Listedeki sıra önceliktir.
- `ornekler.json`: Kurcalamak için örnek metinler ve yasak listeleri. Kontrol bu dosyayı değil, ayrı ve görünmeyen verileri kullanır.
- `merges_ornek.txt`: Hugging Face BPE `merges.txt` **biçimini** gösteren uydurma birkaç satır. Gerçek dosyada ilk satır sürüm başlığıdır, sonraki her satır öncelik sırasıyla bir birleştirmedir. `Ġ` (U+0120), GPT-2 tarzı byte düzeyi BPE'de kelimenin önündeki boşluğu gösterir; bu dersteki sentetik BPE ise kelime sonunu `</w>` ile işaretler.
