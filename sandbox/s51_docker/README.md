# Saldırı51 Docker labı — kurulum onayı bekliyor

Bu klasördeki Dockerfile ve runtime kaynağı hazırlanmıştır; imajlar henüz build edilmedi ve gerçek CVE kabulü yapılmadı.

Salt okunur kontrol: `python -X utf8 tools/ai_s51_kur.py --kontrol`.
YALNIZ kullanıcı SALDIRI-51-KURULUM-ONAYI.md listesini onayladıktan sonra: `python -X utf8 tools/ai_s51_kur.py --kur`.
Bu ikinci komut imaj/paket indirir,300–600MBindirme/1–2GBdisk planlama tahmini vardır. Onaysız çalıştırma.

Kurulum aracı iki ayrı image tag üretir,base image digest'i sabittir. Her build logu,image inspect ve pip'in bağımlılık kaynak/hash raporu outputs/s51-kurulum altında zamanlı kaydedilir. Kurulum bitti demek dersin gerçek kabulü geçti demek değildir. `--kontrol` eksik imajda exit2döndürür ve indirmez. Ders runtime'ı hiçbir build/pull yapmaz. `--kur` hiç çalıştırılmadı.

Build sırasında ağ kullanılır;deney runtime'ı networknone/nonroot/read-only/capdropALL/no-new-privileges,tmpfs ve kaynak limitleriyle açılır. Host portu,host klasörü veya Docker socket bağlanmaz. HTTP container'ın iç loopback adresindedir. Yalnız kendi açtığı containerkimlikleri kapatılır;imajlar/diğercontainerlar korunur. Etkilenen ve karşılaştırma MLflow sürümleri eski sürümlerdir;genel amaçlı servis için kullanılmaz. Gerçek test ve kaynak sınırları CODEX-YENI-ai-saldiri-51.md raporundadır.
