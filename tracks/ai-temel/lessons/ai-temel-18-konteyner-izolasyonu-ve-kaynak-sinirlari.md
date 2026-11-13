---
id: ai-temel-18
title: "Konteyner İzolasyonu ve Kaynak Sınırları"
summary: Docker bellek ve CPU sınırlarını HostConfig alanlarına çevir, docker run argümanlarını izolasyon açıklarına karşı denetle ve bind mount isteklerini kök ve kip politikasıyla süz; son adımda sertleştirme bayraklarını üret ve izolasyonun gerçek Docker konteynerinde uygulandığını ölç.
esleme: ai-temel-17, ai-temel-19, ai-savunma-20
timeout: 45
---

::: anlat Konteyner ayrı makine değil, paylaşılan çekirdekte daraltılmış bir görünümdür

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| `docker run` bayrakları Docker Engine API'sinde `HostConfig` alanlarına iner. Linux çekirdeği bunları namespace, cgroup v2 (`memory.max`, `pids.max`, `cpu.max`), capability ve seccomp olarak uygular. `docker inspect` ile `State.OOMKilled` ve uygulanan sınırlar okunur. | Görev 1–3: `veri/kaynak_sinirlari.json`, `veri/run_komutlari.json` ve `veri/baglamalar.json` içindeki **sentetik** dizgeler, token listeleri ve bağlama istekleri. Son adım: kurulu Docker daemon'ı ve yerelde bulunan küçük `busybox` imajıyla sertleştirilmiş ve sınırsız iki gerçek `docker run --rm` konteyneri; cgroup değerleri konteyner içinden okunur. | Çekirdek açığı, konteyner kaçışı, seccomp profili içeriği, symlink çözümü ve rootless/user-namespace kurulumu sınanmaz. Tek imaj ve tek host bütün Docker kurulumlarını temsil etmez. Görev 2'nin ayrıştırıcısı Docker CLI'ın yalnız metinde yazılan alt kümesini tanır. |

> [!NOT]
> Görev 1–3 sentetik veriyle çalışır. Bu görevlerde Docker çağrılmaz, konteyner başlatılmaz. Son adımdaki **Gerçek deney** görevi yalnız çalışan Docker daemon'ını ve yerelde zaten bulunan imajı kullanır; imaj indirilmez, konteynerler `--rm` ile kendiliğinden silinir. `veri/` dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalanır; kopyada yaptığın değişiklik bir sonraki çalıştırmada sıfırlanır, **kalıcılık yoktur**. Kontrol bu dosyalardan ayrı, gizli verilerle sınar.

Docker konteyneri sanal makine değildir: süreçleri host çekirdeğinde çalışır; Linux namespace'leri (pid, mnt, net, uts, ipc, isteğe bağlı user) onlara ayrı süreç ağacı, dosya sistemi ve ağ yığını görünümü verir, cgroup'lar ise bellek, CPU ve süreç sayısını sınırlar. Bu yüzden bir çekirdek açığı ya da fazladan verilmiş ayrıcalık doğrudan host'a kaçış yoludur; user namespace eşlemesi kurulmamışsa konteynerdeki root, host'ta da UID 0'dır. `--privileged` bütün capability'leri ve host aygıtlarını açıp seccomp/AppArmor kısıtlarını kaldırır; `--network host` host'un ağ namespace'ini paylaştırır ve host'ta yalnız localhost'a bağlı servisleri de erişilebilir yapar. `/var/run/docker.sock` bağlamak daemon API'sini konteynere verir: içerideki saldırgan host'un `/` dizinini bağlayan yeni bir ayrıcalıklı konteyner başlatabildiği için bu fiilen host root'udur.

Model servisinde savunmanın amacı, ele geçirilmiş bir sunucu sürecinin yapabileceklerini daraltarak yayılımı kesmektir. `--read-only` kök dosya sistemini salt okunur bağlar, geçici yazma için `--tmpfs /tmp` eklenir; model ağırlıkları `:ro` ile bağlanınca saldırgan ağırlıkları değiştirip kalıcı arka kapı bırakamaz. `--cap-drop ALL` Docker'ın varsayılan capability kümesini (ör. NET_RAW, CHOWN) de kaldırır, `--security-opt no-new-privileges` çekirdeğin no_new_privs bitini açarak setuid ikililerle yetki yükseltmeyi engeller, `--user 1000:1000` süreci root olmayan kullanıcıyla başlatır. Ağda `--network none` ya da `docker network create --internal` ile kurulan iç ağ ve yalnız bir çıkış vekili üzerinden izinli hedefler, veri sızdırma kanalını kapatır. `--gpus` ise HostConfig.DeviceRequests üzerinden host aygıtlarını açar; GPU sürücüsü de saldırı yüzeyine girdiği için yalnız gereken aygıt verilmelidir.
:::

::: anlat Kaynak sınırları HostConfig alanlarına bayt ve nano-CPU birimiyle iner
`docker run` bayrakları Docker Engine API'sinde `POST /containers/create` gövdesinin `HostConfig` nesnesine çevrilir: `--memory` → `Memory` (bayt), `--memory-swap` → `MemorySwap`, `--cpus` → `NanoCpus`, `--pids-limit` → `PidsLimit`, `--read-only` → `ReadonlyRootfs`, `--cap-drop` → `CapDrop`, `--security-opt` → `SecurityOpt`, `--network` → `NetworkMode`, `--privileged` → `Privileged`, bind mount'lar → `"kaynak:hedef[:ro]"` biçimli `Binds`; `--user` ise HostConfig'te değil, üst düzey `Config.User` alanındadır. Bellek dizgelerinde b, k, m, g ekleri 1024 tabanlıdır ve Docker belgeleri `--memory` için en az 6m ister. `MemorySwap` yalnız takas değil bellek+takas toplamıdır: `Memory` ile eşitse takas yoktur, `-1` sınırsız takas demektir, verilmezse ya da 0 verilirse ayarlanmamış sayılır ve host'ta takas varsa konteyner bellek kadar takas kullanabilir; 0 dışında bellekten küçük değer reddedilir. `--cpus=1.5` CFS kotasına `NanoCpus=1500000000` olarak iner; daemon 0.01'den küçük ya da host'taki CPU sayısından büyük değerleri reddeder.

Sınırın aşılma biçimi de farklıdır: CPU kotası aşılınca süreç yalnız kısılır, bellek sınırı aşılınca çekirdeğin OOM killer'ı cgroup içindeki bir süreci SIGKILL ile öldürür. Öldürülen süreç konteynerin ana süreci (PID 1) ise konteyner 137 (128+9) koduyla çıkar ve `docker inspect` çıktısında `State.OOMKilled` true görünür; yalnız bir alt süreç öldürülürse konteyner çalışmayı sürdürebilir. Uzun bağlamlı istekler model servisini bu yoldan düşürebilir; ders 17'deki token sınırı bellek sınırıyla birlikte tasarlanmalıdır. `--pids-limit` fork bombasını cgroup düzeyinde durdurur, 0 ya da -1 ise sınırsız demektir. Bind mount yolunu dizge önekiyle karşılaştırmak hatalıdır: `/srv/modeller-yedek` dizge olarak `/srv/modeller` ile başlar ama onun altında değildir, `..` bileşenleri de normalleştirmeden sonra izinli kökten çıkabilir. `posixpath.normpath` baştaki tam iki `/` işaretini POSIX gereği korur (`//models`), bu yüzden karşılaştırmadan önce tek `/` yapılmalıdır. Dizge denetimi sembolik bağlantıları da çözmez: izinli kökün altındaki bir symlink host'ta başka bir dizini gösterebilir; bunu yalnız host tarafında `realpath` ile çözmek ve dizin sahipliğini kısıtlamak kapatır. Görev 1–3'te Docker çalıştırılmaz ve konteyner başlatılmaz; bu görevler gerçek CLI token'larını, bellek/CPU dizgelerini ve `Binds` biçimini deterministik olarak işler ve Docker'ın kabul ettiği biçimlerin (ör. `1.5g`, `512mb`, kısa `-v`) yalnız görev metninde yazılan alt kümesini kabul eder. Son adım ise ürettiğin bayraklarla gerçek bir konteyner başlatır ve sınırların çekirdekte uygulandığını konteyner içinden ölçer.

**Görev 1'de sık tuzaklar:** Ekleri 1000 tabanlı saymak `512m` değerini yaklaşık %5 küçük yazar (`veri/kaynak_sinirlari.json`, `r-07`). `--memory-swap` değerini bellek üstüne eklenecek takas sanmak, `3g`yi 5 GiB yapar (`r-02`). `float(cpus) * 1e9` bazı kesirlerde bir nano-CPU kayar (`r-05`). Takasın bellekten küçük olması ve 0.01 CPU altı gibi sınırları denetlememek, daemon'ın reddedeceği bir yapılandırmayı "geçerli" gösterir.

Kaynaklar: [Docker Docs — Runtime Privilege and Linux Capabilities](https://docs.docker.com/engine/containers/run/#runtime-privilege-and-linux-capabilities), [Linux Kernel Documentation — Control Group v2 (cgroups)](https://docs.kernel.org/admin-guide/cgroup-v2.html).
:::

::: tahmin Sınır birimlerini ve önek tuzağını tahmin et
Dört çıktı satırını yaz:

```python
import posixpath
bellek, toplam = 2 * 1024 ** 3, 3 * 1024 ** 3
print(bellek, toplam - bellek)
tam, kesir = "1.5".split(".")
print(int(tam) * 10 ** 9 + int(kesir) * 10 ** (9 - len(kesir)))
y = posixpath.normpath("/srv/modeller/../modeller-eski/w.bin")
print(y, y.startswith("/srv/modeller"), y.startswith("/srv/modeller/"))
print(128 + 9)
```

???

```cikti
2147483648 1073741824
1500000000
/srv/modeller-eski/w.bin True False
137
```

İlk satır `--memory 2g --memory-swap 3g` için `Memory` değerini ve toplamdan kalan 1 GiB takası gösterir; ikinci satır `--cpus 1.5` değerinin kayan nokta kullanmadan `NanoCpus` tamsayısına çevrilmesidir. Üçüncü satırda normalleştirilmiş yol dizge öneki testini geçer ama `/` ile biten kök önekini geçemez; izinli kök denetimi ikincisiyle yapılmalıdır. Son satır OOM killer'ın gönderdiği SIGKILL (9) sonrasında görülen konteyner çıkış kodudur.
:::

::: gorev 1 · Bellek ve CPU sınırlarını HostConfig alanlarına çevir
`kaynak_siniri(bellek, takas, cpus, cekirdek)` işlevini yaz ve `{"Memory": int, "MemorySwap": int, "NanoCpus": int}` döndür; üç değer de `int` türünde olmalıdır. Geçersiz veride `ValueError` yükselt.

`bellek` bir stringdir: bir ya da daha çok ASCII rakam, ardından isteğe bağlı tek ek `b`, `k`, `m` veya `g` (büyük harf de kabul edilir). Ekler 1, 1024, 1024², 1024³ çarpanıdır; ek yoksa değer bayttır. İşaret, boşluk, ondalık nokta veya iki harfli ek (`mb`) geçersizdir. `Memory` en az 6m (6291456 bayt) olmalıdır.

`takas` `None`, tam `"-1"` stringi ya da `bellek` ile aynı biçimde bir stringdir. `None` → `MemorySwap` 0 (belirtilmemiş), `"-1"` → -1 (sınırsız); diğer durumda değer bayta çevrilir. Sonuç 0 ise Docker'daki gibi belirtilmemiş sayılır ve `MemorySwap` 0 olur; 0 değilse ve `Memory` değerinden küçükse geçersizdir (eşitlik takassız demektir).

`cpus` bir stringdir: bir ya da daha çok ASCII rakam, isteğe bağlı olarak nokta ve ardından 1–9 ASCII rakam. `NanoCpus` değeri × 10⁹ olarak kayan nokta kullanmadan tam hesaplanır ve 10000000 (0.01 CPU) ile `cekirdek` × 10⁹ arasında (iki uç dahil) olmalıdır. `cekirdek` en az 1 olan `int` değeridir; `bool` kabul edilmez.

Görünür veri: `veri/kaynak_sinirlari.json`. Her örneğin `beklenen` alanı vardır; `null`, `ValueError` demektir.

```starter
import json
from ai_temel_veri import json_yukle

def kaynak_siniri(bellek, takas, cpus, cekirdek):
    # KUSURLU BAŞLANGIÇ KODU: ekleri 1000 tabanlı sayıyor, "mb" ve boşluklu değerleri kırpıp kabul ediyor, takası bellekten ayrı miktar sanıp toplamı yanlış yazıyor, NanoCpus'u float çarpımıyla hesaplıyor ve alt/üst sınırları denetlemiyor!
    carpan = {"b": 1, "k": 1000, "m": 1000 ** 2, "g": 1000 ** 3}
    def bayt(s):
        s = s.strip().lower().rstrip("b") or "0"
        if s[-1] in carpan:
            return int(float(s[:-1]) * carpan[s[-1]])
        return int(s)
    mem = bayt(bellek)
    if takas is None:
        swap = 0
    elif takas == "-1":
        swap = -1
    else:
        swap = mem + bayt(takas)
    return {"Memory": mem, "MemorySwap": swap, "NanoCpus": int(float(cpus) * 1e9)}

veri = json_yukle("veri/kaynak_sinirlari.json")
for o in veri["ornekler"]:
    try:
        sonuc = json.loads(json.dumps(kaynak_siniri(o["bellek"], o["takas"], o["cpus"], o["cekirdek"])))
    except ValueError:
        sonuc = None
    except Exception as hata:
        sonuc = type(hata).__name__
    print(o["id"], "doğru" if sonuc == o["beklenen"] else "YANLIŞ", o["aciklama"], sonuc)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-18")
```

```test
def sozlesme(fn):
    try:
        M = 1024 ** 2
        for args, exp in [
            (("512m", None, "1.5", 4), {"Memory": 512 * M, "MemorySwap": 0, "NanoCpus": 1500000000}),
            (("1G", "2g", "0.25", 2), {"Memory": 1024 * M, "MemorySwap": 2048 * M, "NanoCpus": 250000000}),
            (("6291456b", "6m", "0.01", 1), {"Memory": 6 * M, "MemorySwap": 6 * M, "NanoCpus": 10000000}),
            (("6144k", "-1", "1.000000001", 2), {"Memory": 6 * M, "MemorySwap": -1, "NanoCpus": 1000000001}),
            (("6291456", "1g", "1", 1), {"Memory": 6 * M, "MemorySwap": 1024 * M, "NanoCpus": 1000000000}),
            (("8M", "8388608", "2", 2), {"Memory": 8 * M, "MemorySwap": 8 * M, "NanoCpus": 2000000000}),
            (("1g", None, "2.01", 4), {"Memory": 1024 * M, "MemorySwap": 0, "NanoCpus": 2010000000}),
            (("512m", "0", "1", 1), {"Memory": 512 * M, "MemorySwap": 0, "NanoCpus": 1000000000}),
            (("512m", "0g", "1", 1), {"Memory": 512 * M, "MemorySwap": 0, "NanoCpus": 1000000000}),
            (("6m", None, "123456789.123456789", 123456790), {"Memory": 6 * M, "MemorySwap": 0, "NanoCpus": 123456789123456789}),
        ]:
            r = fn(*args)
            if r != exp or any(type(v) is not int for v in r.values()):
                return False
        gecersiz = [(b, None, "1", 1) for b in [None, b"512m", "", "m", "512x", "+512m", " 512m", "512mb", "1.5g", "６m", "6291455b", "6143k", "512m\n", "512\n"]]
        gecersiz += [("512m", t, "1", 1) for t in ["511m", "1", "", "-2", "-1m", True, b"1g", -1, "1g\n", "-1\n"]]
        gecersiz += [("512m", None, c, 2) for c in [None, 1.5, b"1", "", ".5", "1.", "+1", "1.+5", "１", "1.5.5", "0.009999999", "1.0000000001", "2.000000001", "3", "1\n", "1.5\n"]]
        gecersiz += [("512m", None, "1", k) for k in [0, -1, True, 2.0, None, "2"]]
        gecersiz += [("512m", None, "1.000000001", 1)]
        for args in gecersiz:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(kaynak_siniri), "bellek birimleri, takas toplamı, NanoCpus ve sınırlar korunmalı")
def m_takas(b, t, c, k):
    r = kaynak_siniri(b, t, c, k)
    return dict(r, MemorySwap=r["MemorySwap"] + r["Memory"]) if r["MemorySwap"] > 0 else r
def m_float(b, t, c, k):
    r = kaynak_siniri(b, t, c, k)
    return dict(r, NanoCpus=r["NanoCpus"] / 1)
def m_cekirdek(b, t, c, k):
    return kaynak_siniri(b, t, c, k + 1)
for ad, mutant in [("takası toplam saymayan", m_takas), ("NanoCpus'u float yapan", m_float), ("çekirdek sınırını gevşeten", m_cekirdek)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def kaynak_siniri(bellek, takas, cpus, cekirdek):
    carpan = {"b": 0, "k": 1, "m": 2, "g": 3}
    def bayt(s):
        if not isinstance(s, str):
            raise ValueError("bellek")
        govde, ek = s[:-1], s[-1:].lower()
        if ek not in carpan:
            govde, ek = s, "b"
        if not (govde.isascii() and govde.isdigit()):
            raise ValueError("bellek")
        return int(govde) * 1024 ** carpan[ek]
    if isinstance(cekirdek, bool) or not isinstance(cekirdek, int) or cekirdek < 1:
        raise ValueError("çekirdek")
    mem = bayt(bellek)
    if mem < 6 * 1024 ** 2:
        raise ValueError("bellek")
    if takas is None:
        swap = 0
    elif takas == str(-1):
        swap = -1
    else:
        swap = bayt(takas)
        if swap and swap < mem:
            raise ValueError("takas")
    if not isinstance(cpus, str):
        raise ValueError("cpus")
    tam, nokta, kesir = cpus.partition(".")
    if not (cpus.isascii() and tam.isdigit() and (kesir.isdigit() or not nokta) and len(kesir) < 10):
        raise ValueError("cpus")
    milyar = 10 ** 9
    nano = int(tam) * milyar + int(kesir or 0) * 10 ** (9 - len(kesir))
    if nano < 10 ** 7 or nano > cekirdek * milyar:
        raise ValueError("cpus")
    return {"Memory": mem, "MemorySwap": swap, "NanoCpus": nano}
```

```hint
Kesirli CPU değerini noktadan böl ve kesir hanelerini 10'un kuvvetiyle tamamla; `float(cpus) * 1e9` bazı değerlerde tam sonucu vermez. Bellekte son karakter ek değilse bütün dizgeyi bayt olarak oku.
```
:::

::: gorev 2 · docker run komutunu izolasyon açıklarına karşı denetle
`run_denetle(argv)` işlevini yaz. `argv` kabuğun böldüğü token listesidir: öğeleri `str`, ilk iki öğesi tam `"docker"`, `"run"`. Sonra seçenekler gelir; seçenek konumunda `-` ile başlamayan ilk token imaj adıdır ve ondan sonraki tokenlar konteyner komutuna aittir, denetlenmez. İmaj token'ı yoksa ya da boşsa veri geçersizdir. Geçersiz veride `ValueError` yükselt. Girdileri değiştirme.

Yalnız şu uzun seçenekler tanınır. Değersiz bayraklar: `--privileged`, `--read-only`, `--rm` (`=` ile yazılırlarsa geçersiz). Değerli seçenekler: `--memory`, `--cpus`, `--pids-limit`, `--user`, `--network`, `--cap-drop`, `--security-opt`, `--volume`, `--tmpfs`; değer `--ad değer` biçiminde bir sonraki tokendır (`-` ile başlasa bile) ya da `--ad=değer` biçiminde ilk `=` işaretinden sonrasıdır ve boş olamaz. Yalnız `--cap-drop`, `--security-opt`, `--volume`, `--tmpfs` tekrarlanabilir. Tanınmayan seçenek, başka bir seçeneğin tekrarı ve eksik değer geçersizdir. `--pids-limit` değeri isteğe bağlı tek `-` işareti ve ardından en az bir ASCII rakamdan oluşmalıdır.

Koşulu sağlanan bulgu kodlarını şu sırayla liste olarak döndür:
- `privileged`: `--privileged` var.
- `host_ag`: `--network` değeri tam `host`.
- `varsayilan_ag`: `--network` yok ya da değeri tam `bridge` veya `default`; varsayılan bridge ağı konteynere dış ağa çıkış verir.
- `docker_sock`: bir `--volume` değerinin ilk `:` öncesi kaynak kısmı `posixpath.normpath` ile (baştaki `//` ardından tek `/` yapılarak) `/var/run/docker.sock` ya da `/run/docker.sock` oluyor.
- `salt_okunur_yok`: `--read-only` yok.
- `cap_drop_yok`: büyük harfe çevrildiğinde `ALL` olan bir `--cap-drop` değeri yok.
- `nnp_yok`: `--security-opt` değerlerinden hiçbiri `no-new-privileges`, `no-new-privileges:true` veya `no-new-privileges=true` değil.
- `bellek_siniri_yok`: `--memory` yok.
- `pids_siniri_yok`: `--pids-limit` yok ya da sayısal değeri 0 veya negatif.
- `root_kullanici`: `--user` yok ya da değerin ilk `:` öncesi kısmı `root` veya `str.isdecimal()` olup `int` değeri 0.

Görünür veri: `veri/run_komutlari.json`. Her komutun `beklenen` bulgu listesi vardır; `null`, `ValueError` demektir.

**Sık tuzaklar:** Komutu tek metne birleştirip aramak, imajdan sonraki konteyner argümanlarını Docker bayrağı sanar (`d-03`). Yolu normalleştirmeden karşılaştırmak `/var/run/../run/docker.sock` bağlamasını kaçırır (`d-04`). `--pids-limit -1` bir sınır değildir ve `--user 00:0` hâlâ root'tur (`d-05`).

```starter
import json
from ai_temel_veri import json_yukle

def run_denetle(argv):
    # KUSURLU BAŞLANGIÇ KODU: argv'yi tek metne birleştirip alt metin arıyor (imajdan sonraki konteyner komutu da denetlenir), docker.sock yolunu normalleştirmiyor, --ad=değer biçimini ve küçük harfli "all" değerini tanımıyor, pids/user değerlerini yorumlamıyor ve seçenekleri doğrulamıyor!
    metin = " ".join(argv)
    bulgular = []
    if "--privileged" in metin:
        bulgular.append("privileged")
    if "--network host" in metin:
        bulgular.append("host_ag")
    if "--network" not in metin:
        bulgular.append("varsayilan_ag")
    if "/var/run/docker.sock:" in metin:
        bulgular.append("docker_sock")
    if "--read-only" not in metin:
        bulgular.append("salt_okunur_yok")
    if "--cap-drop ALL" not in metin:
        bulgular.append("cap_drop_yok")
    if "no-new-privileges" not in metin:
        bulgular.append("nnp_yok")
    if "--memory" not in metin:
        bulgular.append("bellek_siniri_yok")
    if "--pids-limit" not in metin:
        bulgular.append("pids_siniri_yok")
    if "--user" not in metin:
        bulgular.append("root_kullanici")
    return bulgular

veri = json_yukle("veri/run_komutlari.json")
for o in veri["ornekler"]:
    try:
        sonuc = json.loads(json.dumps(run_denetle(o["argv"])))
    except ValueError:
        sonuc = None
    except Exception as hata:
        sonuc = type(hata).__name__
    print(o["id"], "doğru" if sonuc == o["beklenen"] else "YANLIŞ", o["aciklama"], sonuc)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-18")
```

```test
import copy
SIRA = ["privileged", "host_ag", "varsayilan_ag", "docker_sock", "salt_okunur_yok", "cap_drop_yok", "nnp_yok", "bellek_siniri_yok", "pids_siniri_yok", "root_kullanici"]
SERT = ["docker", "run", "--rm", "--read-only", "--tmpfs", "/tmp", "--cap-drop=all", "--security-opt", "no-new-privileges", "--memory", "8g", "--cpus=4", "--pids-limit", "256", "--user", "1000:1000", "--network", "none", "--volume", "/srv/modeller/llama:/models:ro", "ornek/llm-sunucu:1.0", "--privileged", "--port=8000"]
KOTU = ["docker", "run", "--privileged", "--network=host", "--volume", "/var/run/../run/docker.sock:/var/run/docker.sock", "--cap-drop", "NET_RAW", "--security-opt=no-new-privileges:false", "--pids-limit", "-1", "img"]
def sozlesme(fn):
    try:
        girdi = copy.deepcopy(SERT)
        if fn(girdi) != [] or girdi != SERT or fn(copy.deepcopy(KOTU)) != [k for k in SIRA if k != "varsayilan_ag"]:
            return False
        if fn(["docker", "run", "img"]) != SIRA[2:3] + SIRA[4:]:
            return False
        TAM = ["docker", "run", "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--memory", "1g", "--pids-limit", "100", "--user", "1000", "--network", "ic-ag"]
        for ek, bek in [([], []), (["--volume", "//var/run/docker.sock:/s"], ["docker_sock"]), (["--volume", "/var//run/./docker.sock:/s:ro"], ["docker_sock"]),
                        (["--volume", "/home/u/docker.sock:/s"], []), (["--cap-drop", "NET_RAW"], []), (["--security-opt", "no-new-privilegesx"], []), (["--tmpfs", "/a", "--tmpfs", "/b"], [])]:
            if fn(TAM + ek + ["img"]) != bek:
                return False
        if fn(TAM[:-2] + ["img"]) != ["varsayilan_ag"] or fn(TAM[:-1] + ["default", "img"]) != ["varsayilan_ag"] or fn(TAM[:-1] + ["host", "img"]) != ["host_ag"] or fn(TAM[:-1] + ["vekil-ag", "img"]) != []:
            return False
        if fn([t for t in TAM if t != "ALL" and t != "--cap-drop"] + ["--cap-drop", "ALL", "--cap-drop", "NET_RAW", "img"]) != []:
            return False
        if fn([t for t in TAM if t != "no-new-privileges" and t != "--security-opt"] + ["--security-opt", "no-new-privilegesx", "img"]) != ["nnp_yok"]:
            return False
        if fn([("+0" if t == "1000" else t) for t in TAM] + ["img"]) != [] or fn([("-0" if t == "1000" else t) for t in TAM] + ["img"]) != []:
            return False
        d = ["docker", "run", "--user", "root", "--pids-limit=0", "--security-opt=no-new-privileges=true", "--volume", "/srv/a:/b", "--volume=/run/docker.sock:/s", "--network", "bridge", "img"]
        if fn(d) != ["varsayilan_ag", "docker_sock", "salt_okunur_yok", "cap_drop_yok", "bellek_siniri_yok", "pids_siniri_yok", "root_kullanici"]:
            return False
        e = ["docker", "run", "--read-only", "--security-opt", "label=disable", "--security-opt", "no-new-privileges:true", "--cap-drop", "NET_RAW", "--cap-drop", "ALL", "--memory=512m", "--user=app", "--pids-limit=1", "--network=ic-ag", "img"]
        if fn(e) != [] or fn([("--user=0:1000" if t == "--user=app" else t) for t in e]) != ["root_kullanici"] or fn([("--user=1000:0" if t == "--user=app" else t) for t in e]) != []:
            return False
        for argv in [None, ("docker", "run", "img"), ["docker", "run"], ["docker", "build", "img"], ["docker", "run", b"img"], ["docker", "run", ""], ["docker", "run", "--privileged"], ["docker", "run", "--memory"], ["docker", "run", "--memory=", "img"], ["docker", "run", "--memory", "", "img"], ["docker", "run", "--privileged=true", "img"], ["docker", "run", "--cap-add", "ALL", "img"], ["docker", "run", "-v", "/a:/b", "img"], ["docker", "run", "--memory", "1g", "--memory=2g", "img"], ["docker", "run", "--rm", "--rm", "img"], ["docker", "run", "--user", "a", "--user", "b", "img"], ["docker", "run", "--pids-limit", "+5", "img"], ["docker", "run", "--pids-limit", "--5", "img"], ["docker", "run", "--pids-limit=-", "img"], ["docker", "run", "--pids-limit=abc", "img"], ["docker", "run", "--pids-limit=\u0661", "img"], ["docker", "run", "--", "img"], ["docker", "run", "--network", "none", "--network", "none", "img"], ["docker", "run", "--cpus", "1", "--cpus=2", "img"]]:
            try:
                fn(argv)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(run_denetle), "seçenek ayrıştırma, bulgu sırası ve komut sınırı korunmalı")
def m_ayricalik(a):
    return run_denetle([t for t in a if t != "--privileged"])
def m_sira(a):
    return sorted(run_denetle(a))
def m_kullanici(a):
    return [x for x in run_denetle(a) if x != "root_kullanici"]
for ad, mutant in [("privileged'ı yok sayan", m_ayricalik), ("bulgu sırasını bozan", m_sira), ("root kullanıcıyı görmeyen", m_kullanici)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def run_denetle(argv):
    import posixpath
    bayraklar = {"--privileged", "--read-only", "--rm"}
    degerliler = {"--memory", "--cpus", "--pids-limit", "--user", "--network", "--cap-drop", "--security-opt", "--volume", "--tmpfs"}
    tekrarli = {"--cap-drop", "--security-opt", "--volume", "--tmpfs"}
    if not isinstance(argv, list) or any(not isinstance(t, str) for t in argv) or argv[:2] != ["docker", "run"]:
        raise ValueError("argv")
    secenek, i = {}, 2
    while i < len(argv) and argv[i].startswith("-"):
        ad, esit, deger = argv[i].partition("=")
        if ad in bayraklar and not esit:
            deger = True
        elif ad in degerliler:
            if not esit:
                i += 1
                if i >= len(argv):
                    raise ValueError("değer")
                deger = argv[i]
            if not deger:
                raise ValueError("değer")
        else:
            raise ValueError("seçenek")
        if ad in secenek and ad not in tekrarli:
            raise ValueError("tekrar")
        secenek.setdefault(ad, []).append(deger)
        i += 1
    if i >= len(argv) or not argv[i]:
        raise ValueError("imaj")
    def tek(ad):
        return secenek.get(ad, [None])[0]
    pids, kullanici = tek("--pids-limit"), tek("--user")
    if pids is not None:
        govde = pids[1:] if pids.startswith("-") else pids
        if not (govde.isascii() and govde.isdigit()):
            raise ValueError("pids")
    ilk = kullanici.split(":")[0] if kullanici else ""
    def normal(y):
        y = posixpath.normpath(y)
        return y[1:] if y.startswith("//") else y
    kaynaklar = [normal(v.split(":")[0]) for v in secenek.get("--volume", [])]
    nnp = {"no-new-privileges", "no-new-privileges:true", "no-new-privileges=true"}
    kontroller = [
        ("privileged", "--privileged" in secenek),
        ("host_ag", tek("--network") == "host"),
        ("varsayilan_ag", tek("--network") in (None, "bridge", "default")),
        ("docker_sock", any(k in ("/var/run/docker.sock", "/run/docker.sock") for k in kaynaklar)),
        ("salt_okunur_yok", "--read-only" not in secenek),
        ("cap_drop_yok", all(c.upper() != "ALL" for c in secenek.get("--cap-drop", []))),
        ("nnp_yok", all(s not in nnp for s in secenek.get("--security-opt", []))),
        ("bellek_siniri_yok", "--memory" not in secenek),
        ("pids_siniri_yok", pids is None or int(pids) <= 0),
        ("root_kullanici", kullanici is None or ilk == "root" or ilk.isdecimal() and int(ilk) == 0),
    ]
    return [kod for kod, kosul in kontroller if kosul]
```

```hint
Önce seçenekleri tek geçişte bir sözlükte topla: değerli seçenekte `=` yoksa değeri sonraki tokendan al ve indeksi ilerlet. İmaj tokenına gelince dur; sonrasındaki `--privileged` konteyner komutunun argümanıdır, Docker'ın değil.
```
:::

::: gorev 3 · Bind mount isteklerini kök ve kip politikasıyla süz
`baglama_politikasi(baglamalar, izinli_kokler, model_dizini)` işlevini yaz. Geçersiz veride `ValueError` yükselt. Girdileri değiştirme.

`izinli_kokler` boş olmayan, yinelenmeyen bir `str` listesidir; her öğe `/` ile başlar, `//` ile başlamaz, `/` değildir ve `posixpath.normpath` ile değişmez. `model_dizini` aynı kurallara uyan tek bir yoldur. `baglamalar` (boş olabilir) `HostConfig.Binds` biçiminde `str` listesidir: `kaynak:hedef` ya da `kaynak:hedef:kip`; `:` ile bölünce 2 ya da 3 parça çıkar, kaynak ve hedef `/` ile başlar, kip tam `ro` ya da `rw` olur. Kip yoksa `rw` sayılır.

Kaynak ve hedef `posixpath.normpath` ile normalleştirilir; normpath'in koruduğu baştaki `//` ardından tek `/` yapılır. Model kaynakları, listedeki normal hedefi `model_dizini` ya da onun altında olan ve aşağıdaki 1–4. kurallara takılmayan bütün bağlamaların normal kaynaklarıdır (giriş sırasından bağımsız). Her bağlamayı sırayla değerlendir ve ilk uyan red nedenini seç:
1. `kacis`: ham kaynakta ya da ham hedefte `/` ile ayrılmış bir `..` bileşeni var.
2. `kok`: normal kaynak ya da normal hedef `/`.
3. `sock`: normal kaynak `/var/run/docker.sock` ya da `/run/docker.sock`.
4. `izinsiz`: normal kaynak hiçbir izinli köke eşit değil ve hiçbirinin `kök + "/"` önekiyle başlamıyor.
5. `yinelenen`: normal hedef, daha önce izin verilmiş bir bağlamanın normal hedefiyle aynı.
6. `yazilabilir_model`: kip `ro` değil ve ya normal hedef `model_dizini` ya da onun altında (aynı önek kuralı), ya da normal kaynak bir model kaynağıyla aynı, onun altında ya da onun üstünde; böylece aynı ağırlıklar başka bir hedefe yazılabilir bağlanamaz.

Hiçbiri uymazsa bağlamaya izin verilir. `{"Binds": [...], "red": [...]}` döndür: `Binds` izinli bağlamaları giriş sırasıyla `normal_kaynak:normal_hedef:kip` biçiminde (kip her zaman yazılır), `red` ise reddedilenleri giriş sırasıyla `(sıra, neden)` demetleri olarak içerir; sıra 0 tabanlı giriş konumudur.

Görünür veri: `veri/baglamalar.json`. Dosyada izinli kökler, model dizini, on bir bağlama ve beklenen sonuç vardır; JSON'da demetler liste olarak yazılır.

**Sık tuzaklar:** `kaynak.startswith(kok)` denetimi `/srv/modeller-yedek` yolunu kabul eder; `kok + "/"` gerekir. `..` bileşenini normalleştirmeden sonra aramak hiçbir zaman bulamaz; ham yolda ara. Model ağırlıklarını `/models` altında `ro` bağlayıp aynı kaynağı başka bir hedefe `rw` bağlamak, salt okunurluğu boşa çıkarır (`[7, "yazilabilir_model"]`).

```starter
import json
from ai_temel_veri import json_yukle

def baglama_politikasi(baglamalar, izinli_kokler, model_dizini):
    # KUSURLU BAŞLANGIÇ KODU: kökü "/" olmadan dizge önekiyle denetliyor (/srv/modeller-yedek geçer), ".." bileşenini normalleştirmeden sonra aradığı için kaçışı göremiyor, docker.sock ve kök bağlamasını reddetmiyor, yinelenen hedefi ve yazılabilir model bağlamasını denetlemiyor!
    import posixpath
    binds, red = [], []
    for sira, b in enumerate(baglamalar):
        parca = b.split(":")
        kaynak, hedef = posixpath.normpath(parca[0]), posixpath.normpath(parca[1])
        kip = parca[2] if len(parca) > 2 else "rw"
        if ".." in kaynak.split("/"):
            red.append((sira, "kacis"))
        elif not any(kaynak.startswith(k) for k in izinli_kokler):
            red.append((sira, "izinsiz"))
        else:
            binds.append(kaynak + ":" + hedef + ":" + kip)
    return {"Binds": binds, "red": red}

veri = json_yukle("veri/baglamalar.json")
try:
    sonuc = json.loads(json.dumps(baglama_politikasi(veri["baglamalar"], veri["izinli_kokler"], veri["model_dizini"])))
except Exception as hata:
    sonuc = {"Binds": [], "red": [], "hata": type(hata).__name__}
print("Binds", "doğru" if sonuc["Binds"] == veri["beklenen"]["Binds"] else "YANLIŞ", sonuc["Binds"])
for r in veri["beklenen"]["red"]:
    print("red", r, "doğru" if r in sonuc["red"] else "YANLIŞ: bulunamadı")
fazla = [r for r in sonuc["red"] if r not in veri["beklenen"]["red"]]
print("fazla red", "doğru" if not fazla else "YANLIŞ", fazla)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-18")
```

```test
import copy
KOK = ["/srv/modeller", "/srv/veri"]
B = ["/srv/modeller/llama:/models:ro", "/srv/veri/girdi/:/data/", "/var/run/docker.sock:/var/run/docker.sock", "/srv/veri/../..:/x", "/:/host:ro", "/srv/veri:/", "/srv/modeller-yedek/w:/yedek:ro", "/srv/veri/b:/models/", "/srv/modeller/qwen:/models/qwen", "/srv/modeller/qwen:/models/qwen:rw", "/srv/veri/c:/modelsx", "/srv/modeller:/m2:ro", "/srv//veri/./d:/tmp/x:ro", "/opt/x:/data", "/srv/veri/a:/data/../etc", "/srv/modeller/../veri/f:/f:ro"]
BEK = {"Binds": ["/srv/modeller/llama:/models:ro", "/srv/veri/girdi:/data:rw", "/srv/veri/c:/modelsx:rw", "/srv/modeller:/m2:ro", "/srv/veri/d:/tmp/x:ro"],
       "red": [(2, "sock"), (3, "kacis"), (4, "kok"), (5, "kok"), (6, "izinsiz"), (7, "yinelenen"), (8, "yazilabilir_model"), (9, "yazilabilir_model"), (13, "izinsiz"), (14, "kacis"), (15, "kacis")]}
def sozlesme(fn):
    try:
        b, k = copy.deepcopy(B), copy.deepcopy(KOK)
        if fn(b, k, "/models") != BEK or b != B or k != KOK:
            return False
        if fn(["/opt/x:/models:ro", "/srv/veri/a:/models:ro", "/srv/veri/a:/models:ro"], ["/srv/veri"], "/models") != {"Binds": ["/srv/veri/a:/models:ro"], "red": [(0, "izinsiz"), (2, "yinelenen")]}:
            return False
        if fn(["/srv/veri/a..b:/ab", "/srv/veri:/.", "/.:/y", "/srv/modeller/q://models:rw", "/srv/veri/x://models/a", "//var/run/docker.sock:/s", "//srv/veri/e://e"], KOK, "/models") != {"Binds": ["/srv/veri/a..b:/ab:rw", "/srv/veri/e:/e:rw"], "red": [(1, "kok"), (2, "kok"), (3, "yazilabilir_model"), (4, "yazilabilir_model"), (5, "sock")]}:
            return False
        if fn(["/srv/modeller:/yedek:rw", "/srv/modeller/llama:/models:ro", "/srv/modeller/llama/w.bin:/w", "/srv/modeller/qwen:/q:rw", "/srv/modeller/llama:/okuma:ro", "/srv/veri/x:/models/../models2"], ["/srv/modeller", "/srv/veri"], "/models") != {"Binds": ["/srv/modeller/llama:/models:ro", "/srv/modeller/qwen:/q:rw", "/srv/modeller/llama:/okuma:ro"], "red": [(0, "yazilabilir_model"), (2, "yazilabilir_model"), (5, "kacis")]}:
            return False
        if fn(["/:/models:ro", "/srv/veri/a:/a"], KOK, "/models") != {"Binds": ["/srv/veri/a:/a:rw"], "red": [(0, "kok")]} or fn(["/srv:/models:ro", "/srv/veri/a:/a"], ["/srv/veri"], "/models") != {"Binds": ["/srv/veri/a:/a:rw"], "red": [(0, "izinsiz")]}:
            return False
        if fn([], ["/srv"], "/m") != {"Binds": [], "red": []} or fn(["/run/docker.sock:/d:ro"], ["/run"], "/m") != {"Binds": [], "red": [(0, "sock")]}:
            return False
        for args in [(None, KOK, "/m"), (tuple(B), KOK, "/m"), (B, None, "/m"), (B, tuple(KOK), "/m"), (B, [], "/m"), (B, ["srv"], "/m"), (B, ["/srv/"], "/m"), (B, ["/"], "/m"), (B, ["/srv", "/srv"], "/m"), (B, [b"/srv"], "/m"), (B, ["/srv/../etc"], "/m"), (B, ["//srv"], "/m"), (B, KOK, "//models"),
                     (B, KOK, None), (B, KOK, "/"), (B, KOK, "models"), (B, KOK, "/models/"), (B, KOK, b"/models"),
                     ([b"/a:/b"], KOK, "/m"), ([None], KOK, "/m"), (["/a"], KOK, "/m"), (["/a:/b:ro:x"], KOK, "/m"), (["veri:/b"], KOK, "/m"), (["/a:b"], KOK, "/m"), (["/a:/b:x"], KOK, "/m"), (["/a:/b:"], KOK, "/m"), (["/a:/b:RO"], KOK, "/m"), ([":/b"], KOK, "/m")]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(baglama_politikasi), "normalleştirme, kök sınırı, neden önceliği ve kip korunmalı")
def m_kok(b, k, m):
    return baglama_politikasi(b, [x.rsplit("/", 1)[0] or x for x in k], m)
def m_kip(b, k, m):
    return baglama_politikasi([x + ":ro" if isinstance(x, str) and x.count(":") == 1 else x for x in b], k, m)
def m_sira(b, k, m):
    r = baglama_politikasi(b, k, m)
    return {"Binds": r["Binds"], "red": r["red"][::-1]}
for ad, mutant in [("izinli kökü genişleten", m_kok), ("kipi ro'ya zorlayan", m_kip), ("red sırasını bozan", m_sira)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def baglama_politikasi(baglamalar, izinli_kokler, model_dizini):
    import posixpath
    def mutlak(p):
        return isinstance(p, str) and p.startswith("/") and not p.startswith("//") and p != "/" and posixpath.normpath(p) == p
    def normal(y):
        y = posixpath.normpath(y)
        return y[1:] if y.startswith("//") else y
    def altinda(yol, kok):
        return yol == kok or yol.startswith(kok + "/")
    if not isinstance(izinli_kokler, list) or not izinli_kokler or not all(mutlak(k) for k in izinli_kokler) or len(set(izinli_kokler)) != len(izinli_kokler):
        raise ValueError("kökler")
    if not mutlak(model_dizini) or not isinstance(baglamalar, list):
        raise ValueError("girdi")
    girdiler = []
    for b in baglamalar:
        parca = b.split(":") if isinstance(b, str) else []
        if len(parca) < 2 or not all(p.startswith("/") for p in parca[:2]) or parca[2:] not in ([], ["ro"], ["rw"]):
            raise ValueError("bağlama")
        kaynak, hedef = normal(parca[0]), normal(parca[1])
        if ".." in parca[0].split("/") + parca[1].split("/"):
            on_neden = "kacis"
        elif "/" in (kaynak, hedef):
            on_neden = "kok"
        elif kaynak in ("/var/run/docker.sock", "/run/docker.sock"):
            on_neden = "sock"
        elif not any(altinda(kaynak, k) for k in izinli_kokler):
            on_neden = "izinsiz"
        else:
            on_neden = None
        girdiler.append((kaynak, hedef, (parca[2:] or ["rw"])[0], on_neden))
    model_kaynaklari = [k for k, h, _, n in girdiler if n is None and altinda(h, model_dizini)]
    binds, red, hedefler = [], [], set()
    for sira, (kaynak, hedef, kip, neden) in enumerate(girdiler):
        if neden:
            pass
        elif hedef in hedefler:
            neden = "yinelenen"
        elif kip != "ro" and (altinda(hedef, model_dizini) or any(altinda(kaynak, m) or altinda(m, kaynak) for m in model_kaynaklari)):
            neden = "yazilabilir_model"
        else:
            hedefler.add(hedef)
            binds.append(kaynak + ":" + hedef + ":" + kip)
            continue
        red.append((sira, neden))
    return {"Binds": binds, "red": red}
```

```hint
Kök denetimini `yol == kok or yol.startswith(kok + "/")` ile yap; yalnız `startswith(kok)` `/srv/modeller-yedek` yolunu da kabul eder. `..` denetimini normalleştirmeden önceki ham yolda, diğer denetimleri normal yolda uygula ve yinelenen hedef için yalnız izin verilmiş hedefleri bir kümede tut. Model kaynaklarını döngüden önce ayrı bir geçişte topla; yazılabilir bir bağlama listede model bağlamasından önce gelse de yakalanmalıdır.
```
:::

::: gorev Gerçek deney · Sertleştirme bayraklarını üret, izolasyonu gerçek konteynerde doğrula
`sertlestirme_argv(spec)` işlevini yaz. `spec` tam olarak `imaj`, `bellek_mb`, `pids`, `cpus`, `ag`, `salt_okunur`, `yetki_dus` anahtarlı sözlüktür. `imaj` boş olmayan string; `bellek_mb` bool olmayan 1–65536 tamsayısı; `pids` bool olmayan 1–4096 tamsayısı; `cpus` ya `None` ya bool olmayan, `0 < cpus ≤ 64` sonlu sayı; `ag`, `salt_okunur`, `yetki_dus` bool. Geçersiz veride `ValueError` yükselt.

Bayrakları **tam şu sırayla** üret (koşul sağlanmıyorsa o bayrak atlanır):

1. `--memory=<bellek_mb>m`
2. `--memory-swap=<bellek_mb>m`
3. `--cpus=<cpus>` (yalnız `cpus` None değilse)
4. `--pids-limit=<pids>`
5. `--network=none` (yalnız `ag` False ise)
6. `--read-only` (yalnız `salt_okunur` True ise)
7. `--cap-drop=ALL` ve `--security-opt=no-new-privileges` (yalnız `yetki_dus` True ise)

Bayrak listesini döndür. Sayısal değerleri olduğu gibi yaz (ör. `cpus=0.5` → `--cpus=0.5`). `imaj` bayrak listesine girmez (deney onu ayrıca ekler).

```meta
motor: ai-gercek
gereksinim: docker
timeout: 300
```

```starter
import ai_lab

def sertlestirme_argv(spec):
    # KUSURLU BAŞLANGIÇ KODU: --memory-swap eklemiyor (takas açık kalır), ağ kararını tersine çeviriyor (ag=True iken --network=none), --cap-drop'u küçük harfle ve no-new-privileges olmadan yazıyor ve spec'i doğrulamıyor!
    argv = ["--memory=%dm" % spec["bellek_mb"]]
    if spec["cpus"] is not None:
        argv.append("--cpus=%s" % spec["cpus"])
    argv.append("--pids-limit=%d" % spec["pids"])
    if spec["ag"]:
        argv.append("--network=none")
    if spec["salt_okunur"]:
        argv.append("--read-only")
    if spec["yetki_dus"]:
        argv.append("--cap-drop=all")
    return argv

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_18 as deney
    deney.goster(sertlestirme_argv)
```

```test
import ai_lab
sonuclar = []
def kontrol(kosul, mesaj):
    sonuclar.append(bool(kosul))
    return ok(kosul, mesaj)
import ast
_yasak = ("referans", "referans_argv", "getattr", "kanit_yaz")
sorun = list(ai_lab.kod_denetimi(src, _yasak))
for _n in ast.walk(ast.parse(src)):
    if isinstance(_n, ast.ImportFrom) and any(a.name in _yasak or a.name == "*" for a in _n.names):
        sorun.append("referans importu yasak")
    if isinstance(_n, (ast.Import, ast.ImportFrom)) and any(x and x.split(".")[0] in ("inspect", "importlib", "runpy") for x in [a.name for a in _n.names] + ([_n.module] if isinstance(_n, ast.ImportFrom) else [])):
        sorun.append("kaynak okuma/dinamik import yasak")
    if isinstance(_n, ast.Name) and _n.id in ("exec", "eval", "compile", "__builtins__"):
        sorun.append("dinamik kod çalıştırma yasak: " + _n.id)
sorun = sorted(set(sorun))
if not kontrol(not sorun, "laboratuvar yamalanmamalı, referans kullanılmamalı " + ", ".join(sorun)):
    stop()
fn = need("sertlestirme_argv")
from sandbox import ai_gercek_ai_temel_18 as D
TAM = {"imaj": "busybox:1.36", "bellek_mb": 32, "pids": 16, "cpus": 0.5, "ag": False, "salt_okunur": True, "yetki_dus": True}
specler = [TAM, dict(TAM, ag=True), dict(TAM, salt_okunur=False), dict(TAM, yetki_dus=False), dict(TAM, cpus=None),
           dict(TAM, bellek_mb=1, pids=1, cpus=64), dict(TAM, bellek_mb=65536, pids=4096, cpus=64.0),
           dict(TAM, bellek_mb=256, pids=64, cpus=2)]
def sozlesme(f):
    try:
        for s in specler:
            if f(dict(s)) != D.referans_argv(dict(s)):
                return False
        for kotu in [None, [], {"imaj": "x"}, dict(TAM, ek=1), {k: TAM[k] for k in TAM if k != "pids"},
                     dict(TAM, imaj=""), dict(TAM, imaj=5),
                     dict(TAM, bellek_mb=0), dict(TAM, bellek_mb=65537), dict(TAM, bellek_mb=True), dict(TAM, bellek_mb=1.0), dict(TAM, bellek_mb="32"),
                     dict(TAM, pids=0), dict(TAM, pids=4097), dict(TAM, pids=True), dict(TAM, pids="16"),
                     dict(TAM, cpus=0), dict(TAM, cpus=-1), dict(TAM, cpus=65), dict(TAM, cpus=True), dict(TAM, cpus="1"), dict(TAM, cpus=float("inf")), dict(TAM, cpus=float("-inf")), dict(TAM, cpus=float("nan")),
                     dict(TAM, ag=1), dict(TAM, salt_okunur="e"), dict(TAM, yetki_dus=None)]:
            try:
                f(kotu)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
kontrol(sozlesme(fn), "sertleştirme bayrakları (sıra ve koşullar) doğru; geçersiz spec reddedilmeli")
for ad, kw in [("swap kaçağına izin veren", {"swap": False}), ("pids sınırı koymayan", {"pids": False}),
               ("ağ izolasyonu olmayan", {"ag": False}), ("salt-okunur olmayan", {"salt": False}),
               ("yetki düşürmeyen", {"yetki": False}), ("cpu sınırı koymayan", {"cpu": False})]:
    kontrol(not sozlesme(lambda s, kw=kw: D.referans_argv(s, **kw)), "hatalı çözüm reddedilmeli: " + ad)
kontrol(not sozlesme(lambda s: D.referans_argv(TAM)), "hatalı çözüm reddedilmeli: ezber (her spec için aynı argv)")
r, oz = None, None
if all(sonuclar):
    try:
        r = D.deney(fn)
    except ai_lab.GercekLabYok as e:
        kontrol(False, f"GERÇEK DOCKER YOK, deney yapılmadı: {e}")
        stop()
    kontrol(r["argv_sert"] == r["argv_ref"], "öğrenci bayrakları referansla birebir aynı")
    ks, kb = r["sert"]["karar"], r["baz"]["karar"]
    kontrol(all(ks.values()), f"sertleştirilmiş konteynerde 4 denetim de gerçekten uygulandı: {sorted(k for k in ks if ks[k])}")
    kontrol(not any(kb.values()), f"sınırsız tabanda denetimler uygulanmıyor (blast radius açık): {sorted(k for k in kb if kb[k]) or 'hiçbiri'}")
    kontrol(r["sert"]["gozlem"]["memory_max"] == r["beklenen_bellek_bayt"],
            f"bellek limiti çekirdekte: memory.max={r['sert']['gozlem']['memory_max']} (beklenen {r['beklenen_bellek_bayt']})")
    oz = D.ozet(r)
yol = ai_lab.kanit_yaz("temel-konteyner", {"kaynak": "gercek", "kabul": all(sonuclar), "ders": "ai-temel-18",
                                           "ortam": (r or {}).get("ortam"), "deney": r, "ozet": oz})
if oz:
    ok(True, f"BULGU (Docker {r['ortam']['docker_surumu']}, {r['ortam']['imaj']}): sertleştirmeyle kapatılan denetimler {oz['blast_kapatilan']}; "
             f"memory.max {oz['bellek_bayt']} bayt (beklenen {oz['beklenen_bellek_bayt']}), pids fork engellendi: {oz['fork_engellendi']}; "
             f"sınırsız tabanda uygulanan denetim: {oz['taban_uygulanan'] or 'hiçbiri'}. Tam izole: {oz['tam_izole']}.")
```

```solution
import ai_lab

def sertlestirme_argv(spec):
    import math
    if not isinstance(spec, dict) or set(spec) != {"imaj", "bellek_mb", "pids", "cpus", "ag", "salt_okunur", "yetki_dus"}:
        raise ValueError("spec alanları: imaj, bellek_mb, pids, cpus, ag, salt_okunur, yetki_dus")
    if not isinstance(spec["imaj"], str) or not spec["imaj"]:
        raise ValueError("imaj boş olmayan string olmalı")
    if isinstance(spec["bellek_mb"], bool) or not isinstance(spec["bellek_mb"], int) or not 1 <= spec["bellek_mb"] <= 65536:
        raise ValueError("bellek_mb 1-65536 tamsayı olmalı")
    if isinstance(spec["pids"], bool) or not isinstance(spec["pids"], int) or not 1 <= spec["pids"] <= 4096:
        raise ValueError("pids 1-4096 tamsayı olmalı")
    cpus = spec["cpus"]
    if cpus is not None:
        if isinstance(cpus, bool) or not isinstance(cpus, (int, float)) or not 0 < cpus <= 64:
            raise ValueError("cpus None ya da 0<cpus<=64 olmalı")
    for a in ("ag", "salt_okunur", "yetki_dus"):
        if not isinstance(spec[a], bool):
            raise ValueError(f"{a} bool olmalı")
    f = [f"--memory={spec['bellek_mb']}m", f"--memory-swap={spec['bellek_mb']}m"]
    if cpus is not None:
        f.append(f"--cpus={cpus}")
    f.append(f"--pids-limit={spec['pids']}")
    if not spec["ag"]:
        f.append("--network=none")
    if spec["salt_okunur"]:
        f.append("--read-only")
    if spec["yetki_dus"]:
        f.append("--cap-drop=ALL")
        f.append("--security-opt=no-new-privileges")
    return f

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_18 as deney
    deney.goster(sertlestirme_argv)
```

```hint
Önce spec alanlarını tek tek doğrula (bool'u int'ten önce ele; `cpus` None olabilir). Sonra bayrakları görevdeki **tam sırayla** ekle: bellek ve swap her zaman, `cpus` yalnız None değilse, `--network=none` yalnız `ag` False iken, `--read-only` ve yetenek bayrakları ilgili bool True iken. `imaj`'ı listeye koyma.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Konteyner sanal makine değildir (30 sn).** "Konteyner konakla aynı çekirdeği paylaşır; `namespaces` görüş alanını, `cgroups` bellek/CPU/PID bütçesini, `capabilities` ve `seccomp` ise çekirdek çağrı yetkisini daraltır."
2. **Tehlikeli bayraklar ve bağlama önek tuzağı (35 sn).** "`--privileged`, `--network=host` veya `docker.sock` bağlaması izolasyonu fiilen kaldırır; `bind mount` kök denetiminde `startswith('/srv/m')` yerine bileşen sınırı (`yol == kok or yol.startswith(kok + '/')`) kullanılmazsa `/srv/m-gizli` dizini sızar ve model ağırlıkları her bağlamada `ro` kalmalıdır."
3. **Kaynak tavanı (`MemorySwap`, `pids-limit`) (30 sn).** "`--memory-swap` bellek sınırına eşitlenmezse süreç takas alanına taşar, `--pids-limit` konmazsa çatal bombası (`fork bomb`) konak süreç tablosunu tüketir."
4. **Soru (25 sn).** "Model ağırlıkları `/models:ro` olarak salt-okunur bağlanmışken aynı konak klasörü başka bir hedefe `/yedek:rw` ile bağlanırsa model bütünlüğü neden bozulur?"
:::
