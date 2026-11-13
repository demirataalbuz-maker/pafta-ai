---
id: ai-guvence-21
title: Model ve Veri SBOM Envanteri
summary: Model, veri, bağımlılık ve temel imajı SHA-256 ve bağlantılarla ilişkilendir; SBOM grafiğini ve değişikliklerini denetle.
esleme: ai-guvence-22, ai-guvence-25, ai-uretim-36
timeout: 45
---

::: anlat SBOM model dosyasından daha geniş bir envanterdir
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Dosya/paket kimliği, sürüm, gerçek hash ve bağımlılık bağlantıları | Görevler 1–3 görünür sentetik SBOM JSON'u; son görev gerçekten eğitilen model ve veri/sürüm dosyalarının byte hash ve boyutlarını okur | Bu özel yerel envanter Syft taraması veya CycloneDX uyumlu belge değildir; hash ve grafik model güvenilirliğini kanıtlamaz |

> [!NOT]
> `veri/sbom_eski.json` ve `veri/sbom_yeni.json` sentetik öğretim dosyalarıdır. Tekrarlanan harflerden hash alanları gerçek dosya özeti değildir. Setup her çalıştırmada geçici kopya oluşturur, kalıcılık yoktur. Başlangıçlar dosyaları gerçekten okur; aynı çalıştırmada bellekte kopyayla deneyebilirsin. Gerçek deneyin `PAFTA_DATA/calisma/ai-guvence-21/ayar.json` kopyası ayrıdır ve kalıcıdır; varsa üzerine yazılmaz. Kontrol bağımsız girdiler ve kendi ürettiği dosyalarla sınar.

Yazılım malzeme listesi yalnız paketleri değil, modeli, eğitim verisini, bağımlılıkları ve temel imajı da kapsamalıdır. Her bileşenin kararlı kimliği, sürümü ve SHA-256 özeti bulunur; `bagimliliklar` alanı doğrudan kullandığı diğer bileşen kimliklerini gösterir.

Bu derste Syft, CycloneDX veya DVC çağrılmaz; dosya ve paket indirilmez. İlk üç görev sentetik JSON bileşenleriyle çalışır; son görev gerçek CPU eğitimiyle üretilen ağırlık ve yerel veri/sürüm dosyalarını gerçekten okur. Amaç envanterin şemasını, bağlantı bütünlüğünü ve değişiklik raporunu deterministik biçimde üretmektir.
:::

::: anlat Bağlantı bütünlüğü ve değişiklik izi birlikte gerekir
Envanterde her bağımlılık kimliği mevcut bir bileşeni göstermeli ve bağımlılık grafiği döngü içermemelidir. Başka bileşen tarafından referans verilmeyen bileşenler kök, bağımlılığı olmayanlar yaprak olarak raporlanır.

İki envanter karşılaştırılırken yeni kimlikler eklenen, yalnız eskide kalanlar kaldırılan bileşenlerdir. Ortak kimlikte tür, sürüm, SHA-256 veya bağımlılık listesi değiştiyse bileşen değişmiş sayılır. Hash aynıyken yalnız görünüm sırasının değişmesi içerik değişikliği değildir.
:::

::: anlat Görünür grafikten gerçek dosya hashlerine
Bir model paketinin envanteri yalnız tek ağırlık dosyasının adından ibaret değildir. Aynı model farklı veri sürümü, bağımlılık sürümü veya temel imajla çalıştığında sonucu değişebilir. Bu nedenle bileşen kimliği ile dosya hash'ini ayrı tutarız. Kimlik bileşeni izlemeye, hash ise belirli byte içeriğini ayırt etmeye yarar. İki dosyanın adı aynıyken içerikleri farklı olabilir. Aynı içerik farklı bir adla kopyalandığında hash aynı kalabilir. Hash eşleşmesinden dosyanın lisansını, yazarının güvenilirliğini veya modelin davranış güvenliğini çıkaramazsın; bunlar başka kanıtlar gerektirir.

İlk görevde `veri/sbom_eski.json` dosyasını okuyup bileşenleri ham biçimde yazdır. Model, veri, bağımlılık ve temel imaj alanları burada özel bir öğretim şemasına aittir. Bu dosya gerçek bir CycloneDX veya SPDX belgesi olarak adlandırılmaz. Hash alanında aynı harfin tekrarlanması yalnız altmış dört küçük onaltılık karakterlik biçimi gösterir; arkasında var olan dosya yoktur. İlk görev kimlik, tür, sürüm ve bağlantıların biçimini doğrular. Bağımlılık listesinin sırasını normalize etmek görünüş değişimini içerik değişimi gibi raporlamayı önler. Girdideki iç listeyi paylaşmak yerine bağımsız sonuç üret.

İkinci görev aynı dosyada bağlantı bütünlüğünü denetler. Bir bileşenin adını bağımlılık listesine yazmak o bileşeni var etmez; referans verilen kimlik envanterde bulunmalıdır. Grafik döngüsünü tespit ederken ziyaret ediliyor ve tamamlandı durumlarını ayır. Yalnız daha önce görüldü diye her ikinci ziyareti hata sayarsan ortak bağımlılığa giden iki yolu da döngü sanarsın. Gerçek döngü, halen açık ziyaret zincirindeki düğüme dönmektir. Bu dersin kök tanımı başkası tarafından referans verilmeyen, yaprak tanımı bağımlılığı olmayan bileşendir. Grafiğin ok yönünü ters yorumlamak bu iki grubu değiştirir.

Üçüncü görev `veri/sbom_yeni.json` ile önceki envanteri karşılaştırır. Yeni kimlik eklenmiş, yalnız eskide kalan kimlik kaldırılmıştır. Ortak kimlikte sürüm, tür, hash ve normalize bağlantı listesini ayrı alanlar olarak karşılaştır. Bir sürüm etiketi değişip hash aynı kalabilir; böyle bir değişikliği sessizce silme. Tersine yalnız giriş satırlarının sırası değiştiğinde dosyanın içeriği değişmiş gibi davranma. Öğrenci dosyasında bir bileşenin hash alanını bellekte kopyalayıp değiştirerek fark raporunun hangi alanı gösterdiğini dene. Görünür veriyi değiştirmek gizli testin beklenen sonucunu değiştirmez.

Son görev gerçek bir küçük modeli autograd ile eğitir ve ağırlıkları diske yazar. Veri dosyası burada tam ham veri kümesi değil, sentetik verinin üretim tarifi ve eğitim kaydıdır; bunu bütün eğitim verisinin eksiksiz arşivi gibi sunma. Torch sürüm kaydı da gerçek paket metadatasından alınır. Öğrenci işlevi tanımlardaki dosyaları açıp byte içeriğinden SHA-256 ve boyut hesaplar. Ardından veri dosyasına satır sonu ve boşluk eklenir. JSON'un anlamsal alanları değişmese de byte hash'i ve dosya boyutu değişir; bu fark beklenir ve raporda görülmelidir.

Dosya yolları yalnız deney kökü içinde çözülmelidir. Mutlak yol, dışarı kaçan göreli yol veya dışarı yönlenen bağlantı hedefi öğrencinin başka dosyaları okumasına yol açmamalıdır. Çözülmüş hedefin kök içinde kalması ve dosyanın var olması birlikte denetlenir. Bu basit kontrol eşzamanlı dosya değiştirmelerine karşı işletim sistemi düzeyinde tam yarış koruması değildir. Saldırgan hem model dosyasını hem envanteri değiştirebiliyorsa hash'i de yenileyebilir; güvenilir envanterin saklandığı yer ayrı bir güven sınırıdır. Bu ders değişiklik izini ve yerel bağlantı bütünlüğünü öğretir; tedarik zincirinin tamamını güvenli ilan etmez.
:::

::: tahmin SBOM sayımlarını tahmin et
Üç çıktı satırını yaz:

```python
print(len("a" * 64))
print(sorted(["model", "veri", "model"]).count("model"))
print({"tür", "sürüm"} == {"sürüm", "tür"})
```

???

```cikti
64
2
True
```

İlk satır SHA-256 metninin uzunluğunu, ikinci satır model bileşeni sayısını, üçüncü satır değişen alan adlarının sıradan bağımsız karşılaştırıldığını gösterir.
:::

::: gorev 1 · SBOM bileşenini doğrula
`sbom_bileseni_dogrula(bilesen)` işlevini yaz. Bileşen tam olarak `id`, `tur`, `surum`, `sha256`, `bagimliliklar` alanlarını taşır. Kimlik 1–64 karakterlik, ASCII harf/rakamla başlayan ve yalnız ASCII harf, rakam, alt çizgi veya tire içeren stringdir. Tür yalnız `model`, `veri`, `bagimlilik`, `temel_imaj` olur.

Sürüm 1–64 karakterlik, ASCII harf/rakamla başlayan ve yalnız ASCII harf, rakam, nokta, alt çizgi, artı veya tire içeren stringdir. SHA-256 tam 64 küçük onaltılık karakterdir. Bağımlılıklar benzersiz kimliklerden oluşan listedir; boş olabilir ancak bileşen kendi kimliğini içeremez. Geçersiz veride `ValueError` yükselt. Bağımlılıkları alfabetik sıralanmış bağımsız kopyayla döndür ve girdiyi değiştirme.

```starter
def sbom_bileseni_dogrula(bilesen):
    # KUSURLU BAŞLANGIÇ KODU: şema, hash ve bağımlılık kurallarını denetlemiyor; iç listeyi paylaşıyor.
    return dict(bilesen)

from ai_guvence_veri import json_yukle
for bilesen in json_yukle("veri/sbom_eski.json"):
    print(sbom_bileseni_dogrula(bilesen))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-21")
```

```test
import copy
B = {"id": "model-1", "tur": "model", "surum": "1.2.0", "sha256": "a" * 64, "bagimliliklar": ["veri-1", "lib-1"]}
def sozlesme(fn):
    try:
        once = copy.deepcopy(B)
        sonuc = fn(B)
        if sonuc != dict(B, bagimliliklar=["lib-1", "veri-1"]) or B != once or sonuc["bagimliliklar"] is B["bagimliliklar"]:
            return False
        sinir = {"id": "a" * 64, "tur": "temel_imaj", "surum": "a" * 64, "sha256": "0123456789abcdef" * 4, "bagimliliklar": []}
        if fn(sinir) != sinir:
            return False
        for bilesen in [
            None, [], dict(B, ek=1), dict(B, id=""), dict(B, id="a b"), dict(B, id="a" * 65), dict(B, id=None),
            dict(B, tur="diger"), dict(B, tur=None), dict(B, tur=1),
            dict(B, surum=""), dict(B, surum="1 2"), dict(B, surum=".1"), dict(B, surum="a" * 65), dict(B, surum=1),
            dict(B, sha256="a" * 63), dict(B, sha256="a" * 65), dict(B, sha256="A" * 64), dict(B, sha256="g" * 64), dict(B, sha256=None),
            dict(B, bagimliliklar=None), dict(B, bagimliliklar={}), dict(B, bagimliliklar="lib-1"),
            dict(B, bagimliliklar=["lib-1", "lib-1"]), dict(B, bagimliliklar=["model-1"]), dict(B, bagimliliklar=["a b"]), dict(B, bagimliliklar=[1]),
        ]:
            try:
                fn(bilesen)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(sbom_bileseni_dogrula), "bileşen şeması, SHA-256, sürüm ve bağımlılıklar korunmalı")
def m_hash(bilesen):
    return sbom_bileseni_dogrula(dict(bilesen, sha256="A" * 64))
def m_tur(bilesen):
    return sbom_bileseni_dogrula(dict(bilesen, tur="diger"))
def m_bag(bilesen):
    return sbom_bileseni_dogrula(dict(bilesen, bagimliliklar=[bilesen["id"]]))
for ad, mutant in [("hash doğrulamasını silen", m_hash), ("türü bozan", m_tur), ("kendine bağımlılık ekleyen", m_bag)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def sbom_bileseni_dogrula(bilesen):
    import re
    if not isinstance(bilesen, dict):
        raise ValueError("bileşen sözlük olmalı")
    if set(bilesen) != {"id", "tur", "surum", "sha256", "bagimliliklar"}:
        raise ValueError("bileşen şeması geçersiz")
    desen = r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}"
    if not isinstance(bilesen["id"], str) or not re.fullmatch(desen, bilesen["id"]):
        raise ValueError("kimlik geçersiz")
    if bilesen["tur"] not in ("model", "veri", "bagimlilik", "temel_imaj"):
        raise ValueError("tür geçersiz")
    if not isinstance(bilesen["surum"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,63}", bilesen["surum"]):
        raise ValueError("sürüm geçersiz")
    if not isinstance(bilesen["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", bilesen["sha256"]):
        raise ValueError("SHA-256 geçersiz")
    baglar = bilesen["bagimliliklar"]
    if not isinstance(baglar, list):
        raise ValueError("bağımlılıklar liste olmalı")
    if any(not isinstance(x, str) or not re.fullmatch(desen, x) for x in baglar):
        raise ValueError("bağımlılık kimliği geçersiz")
    if len(set(baglar)) != len(baglar):
        raise ValueError("bağımlılıklar yinelenemez")
    if bilesen["id"] in baglar:
        raise ValueError("bileşen kendine bağımlı olamaz")
    return {"id": bilesen["id"], "tur": bilesen["tur"], "surum": bilesen["surum"], "sha256": bilesen["sha256"], "bagimliliklar": sorted(baglar)}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    for bilesen in json_yukle("veri/sbom_eski.json"):
        print(sbom_bileseni_dogrula(bilesen))
```

```hint
Kimlik desenini bağımlılıklarda da kullan. SHA-256 için yalnız küçük `a-f` ve rakamları kabul et.
```
:::

::: gorev 2 · Bağlantı bütünlüğü olan envanteri oluştur
`sbom_envanteri_olustur(bilesenler)` işlevini yaz. Girdi ilk görevdeki bileşenlerden oluşan boş olmayan listedir; kimlikler benzersizdir, her bağımlılık mevcut bir bileşeni gösterir ve grafik döngü içeremez. Geçersiz veride `ValueError` yükselt.

Bileşenleri kimliğe göre sıralanmış bağımsız kopyalarla döndür. `{"toplam":N,"tur_sayilari":{...},"kokler":[...],"yapraklar":[...],"bilesenler":[...]}` üret. Tür sayıları dört izinli türü de içerir. Kökler hiçbir bağımlılık listesinde geçmeyen, yapraklar bağımlılığı olmayan bileşenlerdir; iki liste de alfabetik sıralıdır. Girdiyi değiştirme.

```starter
def sbom_envanteri_olustur(bilesenler):
    import re
    if not isinstance(bilesenler, list) or not bilesenler:
        raise ValueError("bileşenler boş olmayan liste olmalı")
    desen = r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}"
    temiz = []
    for b in bilesenler:
        if not isinstance(b, dict) or set(b) != {"id", "tur", "surum", "sha256", "bagimliliklar"}:
            raise ValueError("bileşen şeması geçersiz")
        if not isinstance(b["id"], str) or not re.fullmatch(desen, b["id"]):
            raise ValueError("kimlik geçersiz")
        if b["tur"] not in ("model", "veri", "bagimlilik", "temel_imaj"):
            raise ValueError("tür geçersiz")
        if not isinstance(b["surum"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,63}", b["surum"]):
            raise ValueError("sürüm geçersiz")
        if not isinstance(b["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", b["sha256"]):
            raise ValueError("SHA-256 geçersiz")
        if not isinstance(b["bagimliliklar"], list) or any(not isinstance(x, str) or not re.fullmatch(desen, x) for x in b["bagimliliklar"]):
            raise ValueError("bağımlılıklar geçersiz")
        if len(set(b["bagimliliklar"])) != len(b["bagimliliklar"]) or b["id"] in b["bagimliliklar"]:
            raise ValueError("bağımlılıklar benzersiz olmalı ve kendini içermemeli")
        temiz.append({"id": b["id"], "tur": b["tur"], "surum": b["surum"], "sha256": b["sha256"], "bagimliliklar": sorted(b["bagimliliklar"])})
    if len({x["id"] for x in temiz}) != len(temiz):
        raise ValueError("kimlikler yinelenemez")
    idler = {x["id"] for x in temiz}
    if any(bag not in idler for x in temiz for bag in x["bagimliliklar"]):
        raise ValueError("bağımlılık bulunamadı")
    harita = {x["id"]: x for x in temiz}
    ziyaret_ediliyor = set()
    tamamlandi = set()
    def ziyaret(kimlik):
        if kimlik in ziyaret_ediliyor:
            raise ValueError("bağımlılık döngüsü")
        if kimlik in tamamlandi:
            return
        ziyaret_ediliyor.add(kimlik)
        for bag in harita[kimlik]["bagimliliklar"]:
            ziyaret(bag)
        ziyaret_ediliyor.remove(kimlik)
        tamamlandi.add(kimlik)
    for kimlik in harita:
        ziyaret(kimlik)
    # KUSURLU BAŞLANGIÇ KODU: kökleri başkalarının referans verdiği düğümler sanıyor.
    referansli = {bag for x in temiz for bag in x["bagimliliklar"]}
    return {"toplam": len(temiz), "tur_sayilari": {tur: sum(1 for x in temiz if x["tur"] == tur) for tur in ("model", "veri", "bagimlilik", "temel_imaj")}, "kokler": sorted(x["id"] for x in temiz if x["id"] in referansli), "yapraklar": sorted(x["id"] for x in temiz if not x["bagimliliklar"]), "bilesenler": sorted(temiz, key=lambda x: x["id"])}

from ai_guvence_veri import json_yukle
print(sbom_envanteri_olustur(json_yukle("veri/sbom_eski.json")))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-21")
```

```test
import copy
K = [
    {"id": "m", "tur": "model", "surum": "1.0", "sha256": "a" * 64, "bagimliliklar": ["d", "l"]},
    {"id": "d", "tur": "veri", "surum": "2.0", "sha256": "b" * 64, "bagimliliklar": []},
    {"id": "l", "tur": "bagimlilik", "surum": "3.0", "sha256": "c" * 64, "bagimliliklar": ["b"]},
    {"id": "b", "tur": "temel_imaj", "surum": "4.0", "sha256": "d" * 64, "bagimliliklar": []},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        sonuc = fn(K)
        if K != once or sonuc["toplam"] != 4 or sonuc["kokler"] != ["m"] or sonuc["yapraklar"] != ["b", "d"]:
            return False
        if sonuc["tur_sayilari"] != {"model": 1, "veri": 1, "bagimlilik": 1, "temel_imaj": 1}:
            return False
        if [x["id"] for x in sonuc["bilesenler"]] != ["b", "d", "l", "m"] or sonuc["bilesenler"][3]["bagimliliklar"] != ["d", "l"]:
            return False
        ikinci_kok = fn(K + [dict(K[1], id="x")])
        if ikinci_kok["kokler"] != ["m", "x"] or ikinci_kok["tur_sayilari"]["veri"] != 2:
            return False
        sinir = fn([dict(K[0], id="a" * 64, bagimliliklar=[])])
        if sinir["kokler"] != ["a" * 64] or sinir["yapraklar"] != ["a" * 64]:
            return False
        for bilesenler in [
            None, {}, tuple(K), [], [None], [dict(K[1], ek=1)], [K[1], K[1]],
            [dict(K[1], id="a b")], [dict(K[1], id=None)], [dict(K[1], id="a" * 65)], [dict(K[1], tur="diger")],
            [dict(K[1], surum=1)], [dict(K[1], surum="a" * 65)], [dict(K[1], sha256="A" * 64)], [dict(K[1], sha256=None)],
            [dict(K[1], bagimliliklar=None)], [dict(K[1], bagimliliklar=[1])], [dict(K[1], bagimliliklar=[[]])], [dict(K[1], bagimliliklar=["a b"])], [dict(K[1], bagimliliklar=["d"])], [dict(K[0], bagimliliklar=["yok"])],
            [dict(K[0], bagimliliklar=["d", "d"])] + K[1:], [dict(K[0], bagimliliklar=["m"])] + K[1:],
            [dict(K[0], bagimliliklar=["d"]), dict(K[1], bagimliliklar=["m"])],
            [dict(K[0], bagimliliklar=["d"]), dict(K[1], bagimliliklar=["l"]), dict(K[2], bagimliliklar=["m"])],
        ]:
            try:
                fn(bilesenler)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(sbom_envanteri_olustur), "benzersizlik, referanslar, döngüler ve kök-yaprak hesabı korunmalı")
def m_bag(bilesenler):
    return sbom_envanteri_olustur([dict(x, bagimliliklar=[]) for x in bilesenler])
def m_tur(bilesenler):
    return sbom_envanteri_olustur([dict(x, tur="model") for x in bilesenler])
def m_id(bilesenler):
    return sbom_envanteri_olustur([dict(x, id="m") for x in bilesenler])
for ad, mutant in [("bağlantıları silen", m_bag), ("türleri birleştiren", m_tur), ("kimlikleri birleştiren", m_id)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def sbom_envanteri_olustur(bilesenler):
    import re
    if not isinstance(bilesenler, list) or not bilesenler:
        raise ValueError("bileşenler boş olmayan liste olmalı")
    desen = r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}"
    temiz = []
    for b in bilesenler:
        if not isinstance(b, dict) or set(b) != {"id", "tur", "surum", "sha256", "bagimliliklar"}:
            raise ValueError("bileşen şeması geçersiz")
        if not isinstance(b["id"], str) or not re.fullmatch(desen, b["id"]):
            raise ValueError("kimlik geçersiz")
        if b["tur"] not in ("model", "veri", "bagimlilik", "temel_imaj"):
            raise ValueError("tür geçersiz")
        if not isinstance(b["surum"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,63}", b["surum"]):
            raise ValueError("sürüm geçersiz")
        if not isinstance(b["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", b["sha256"]):
            raise ValueError("SHA-256 geçersiz")
        if not isinstance(b["bagimliliklar"], list) or any(not isinstance(x, str) or not re.fullmatch(desen, x) for x in b["bagimliliklar"]):
            raise ValueError("bağımlılıklar geçersiz")
        if len(set(b["bagimliliklar"])) != len(b["bagimliliklar"]) or b["id"] in b["bagimliliklar"]:
            raise ValueError("bağımlılıklar benzersiz olmalı ve kendini içermemeli")
        temiz.append({"id": b["id"], "tur": b["tur"], "surum": b["surum"], "sha256": b["sha256"], "bagimliliklar": sorted(b["bagimliliklar"])})
    if len({x["id"] for x in temiz}) != len(temiz):
        raise ValueError("kimlikler yinelenemez")
    idler = {x["id"] for x in temiz}
    if any(bag not in idler for x in temiz for bag in x["bagimliliklar"]):
        raise ValueError("bağımlılık bulunamadı")
    harita = {x["id"]: x for x in temiz}
    ziyaret_ediliyor = set()
    tamamlandi = set()
    def ziyaret(kimlik):
        if kimlik in ziyaret_ediliyor:
            raise ValueError("bağımlılık döngüsü")
        if kimlik in tamamlandi:
            return
        ziyaret_ediliyor.add(kimlik)
        for bag in harita[kimlik]["bagimliliklar"]:
            ziyaret(bag)
        ziyaret_ediliyor.remove(kimlik)
        tamamlandi.add(kimlik)
    for kimlik in harita:
        ziyaret(kimlik)
    referansli = {bag for x in temiz for bag in x["bagimliliklar"]}
    return {"toplam": len(temiz), "tur_sayilari": {tur: sum(1 for x in temiz if x["tur"] == tur) for tur in ("model", "veri", "bagimlilik", "temel_imaj")}, "kokler": sorted(x["id"] for x in temiz if x["id"] not in referansli), "yapraklar": sorted(x["id"] for x in temiz if not x["bagimliliklar"]), "bilesenler": sorted(temiz, key=lambda x: x["id"])}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    print(sbom_envanteri_olustur(json_yukle("veri/sbom_eski.json")))
```

```hint
Önce bütün kimlikleri ve referansları doğrula. Döngü için DFS üzerinde ziyaret ediliyor ve tamamlandı durumlarını kullan.
```
:::

::: gorev 3 · İki SBOM envanteri arasındaki değişiklikleri raporla
`sbom_fark_raporu(eski, yeni)` işlevini yaz. İki girdi de ilk görevdeki bileşen listeleridir; boş liste olabilir. Her envanter kendi içinde benzersiz kimliklere, geçerli referanslara ve döngüsüz grafiğe sahip olmalıdır. Geçersiz veride `ValueError` yükselt.

Ortak kimlikte `tur`, `surum`, `sha256` veya `bagimliliklar` değiştiyse bileşeni `{"id":D,"alanlar":[...]}` biçiminde raporla; alanları alfabetik sırala. `{"eklenen":[...],"kaldirilan":[...],"degisen":[...],"ozet":{"eklenen":N,"kaldirilan":N,"degisen":N}}` döndür. Kimlik listelerini ve değişenleri alfabetik sırala. Girdileri değiştirme.

```starter
def sbom_fark_raporu(eski, yeni):
    import copy
    import re
    def dogrula(bilesenler):
        if not isinstance(bilesenler, list):
            raise ValueError("envanter liste olmalı")
        desen = r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}"
        temiz = []
        for b in bilesenler:
            if not isinstance(b, dict) or set(b) != {"id", "tur", "surum", "sha256", "bagimliliklar"}:
                raise ValueError("bileşen şeması geçersiz")
            if not isinstance(b["id"], str) or not re.fullmatch(desen, b["id"]):
                raise ValueError("kimlik geçersiz")
            if b["tur"] not in ("model", "veri", "bagimlilik", "temel_imaj"):
                raise ValueError("tür geçersiz")
            if not isinstance(b["surum"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,63}", b["surum"]):
                raise ValueError("sürüm geçersiz")
            if not isinstance(b["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", b["sha256"]):
                raise ValueError("SHA-256 geçersiz")
            if not isinstance(b["bagimliliklar"], list) or any(not isinstance(x, str) or not re.fullmatch(desen, x) for x in b["bagimliliklar"]):
                raise ValueError("bağımlılıklar geçersiz")
            if len(set(b["bagimliliklar"])) != len(b["bagimliliklar"]) or b["id"] in b["bagimliliklar"]:
                raise ValueError("bağımlılıklar benzersiz olmalı")
            temiz.append({"id": b["id"], "tur": b["tur"], "surum": b["surum"], "sha256": b["sha256"], "bagimliliklar": sorted(b["bagimliliklar"])})
        if len({x["id"] for x in temiz}) != len(temiz):
            raise ValueError("kimlikler yinelenemez")
        harita = {x["id"]: x for x in temiz}
        if any(bag not in harita for x in temiz for bag in x["bagimliliklar"]):
            raise ValueError("bağımlılık bulunamadı")
        ziyaret_ediliyor = set()
        tamamlandi = set()
        def ziyaret(kimlik):
            if kimlik in ziyaret_ediliyor:
                raise ValueError("bağımlılık döngüsü")
            if kimlik in tamamlandi:
                return
            ziyaret_ediliyor.add(kimlik)
            for bag in harita[kimlik]["bagimliliklar"]:
                ziyaret(bag)
            ziyaret_ediliyor.remove(kimlik)
            tamamlandi.add(kimlik)
        for kimlik in harita:
            ziyaret(kimlik)
        return harita
    eski_harita = dogrula(eski)
    yeni_harita = dogrula(yeni)
    # KUSURLU BAŞLANGIÇ KODU: eklenen ve kaldırılan kimlikleri ters hesaplıyor.
    eklenen = sorted(set(eski_harita) - set(yeni_harita))
    kaldirilan = sorted(set(eski_harita) - set(yeni_harita))
    degisen = []
    for kimlik in sorted(set(eski_harita) & set(yeni_harita)):
        alanlar = [alan for alan in ("bagimliliklar", "sha256", "surum", "tur") if eski_harita[kimlik][alan] != yeni_harita[kimlik][alan]]
        if alanlar:
            degisen.append({"id": kimlik, "alanlar": alanlar})
    return {"eklenen": eklenen, "kaldirilan": kaldirilan, "degisen": degisen, "ozet": {"eklenen": len(eklenen), "kaldirilan": len(kaldirilan), "degisen": len(degisen)}}

from ai_guvence_veri import json_yukle
print(sbom_fark_raporu(json_yukle("veri/sbom_eski.json"), json_yukle("veri/sbom_yeni.json")))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-21")
```

```test
import copy
E = [
    {"id": "m", "tur": "model", "surum": "1.0", "sha256": "a" * 64, "bagimliliklar": ["d", "l"]},
    {"id": "d", "tur": "veri", "surum": "2.0", "sha256": "b" * 64, "bagimliliklar": []},
    {"id": "l", "tur": "bagimlilik", "surum": "3.0", "sha256": "c" * 64, "bagimliliklar": ["b"]},
    {"id": "b", "tur": "temel_imaj", "surum": "4.0", "sha256": "d" * 64, "bagimliliklar": []},
]
Y = [
    dict(E[0], sha256="e" * 64, bagimliliklar=["l"]),
    dict(E[2], surum="3.1"),
    E[3],
    {"id": "x", "tur": "veri", "surum": "1.0", "sha256": "f" * 64, "bagimliliklar": []},
]
def sozlesme(fn):
    try:
        once_e, once_y = copy.deepcopy(E), copy.deepcopy(Y)
        sonuc = fn(E, Y)
        if E != once_e or Y != once_y or sonuc["eklenen"] != ["x"] or sonuc["kaldirilan"] != ["d"]:
            return False
        if sonuc["degisen"] != [{"id": "l", "alanlar": ["surum"]}, {"id": "m", "alanlar": ["bagimliliklar", "sha256"]}]:
            return False
        if sonuc["ozet"] != {"eklenen": 1, "kaldirilan": 1, "degisen": 2}:
            return False
        bos = {"eklenen": [], "kaldirilan": [], "degisen": [], "ozet": {"eklenen": 0, "kaldirilan": 0, "degisen": 0}}
        if fn([], []) != bos or fn(E, list(reversed(E))) != bos:
            return False
        if fn([], [E[1]])["eklenen"] != ["d"] or fn([E[1]], [])["kaldirilan"] != ["d"]:
            return False
        for eski, yeni in [
            (None, Y), (E, None), ({}, Y), (E, {}), (tuple(E), Y), (E, tuple(Y)),
            ([None], Y), (E, [None]), ([dict(E[1], ek=1)], Y), ([E[1], E[1]], Y), (E, [Y[3], Y[3]]),
            ([dict(E[1], id="a b")], Y), ([dict(E[1], id=None)], Y), ([dict(E[1], id="a" * 65)], Y), (E, [dict(Y[3], id="a" * 65)]),
            ([dict(E[1], tur="diger")], Y), ([dict(E[1], surum=1)], Y), ([dict(E[1], surum="a" * 65)], Y),
            ([dict(E[1], sha256="A" * 64)], Y), ([dict(E[1], sha256=None)], Y),
            (E, [dict(Y[3], bagimliliklar=None)]), (E, [dict(Y[3], bagimliliklar=[1])]), (E, [dict(Y[3], bagimliliklar=[[]])]), (E, [dict(Y[3], bagimliliklar=["a b"])]), (E, [dict(Y[3], bagimliliklar=["x"])]), (E, [dict(Y[3], bagimliliklar=["yok"])]),
            ([dict(E[0], bagimliliklar=["d", "d"])] + E[1:], Y), ([dict(E[0], bagimliliklar=["m"])] + E[1:], Y),
            ([dict(E[0], bagimliliklar=["d"]), dict(E[1], bagimliliklar=["m"])], Y),
        ]:
            try:
                fn(eski, yeni)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(sbom_fark_raporu), "envanter doğrulama, eklenen-kaldırılan ve alan farkları korunmalı")
def m_eski(eski, yeni):
    return sbom_fark_raporu([], yeni)
def m_yeni(eski, yeni):
    return sbom_fark_raporu(eski, [])
def m_hash(eski, yeni):
    return sbom_fark_raporu(eski, [dict(x, sha256="0" * 64) for x in yeni])
for ad, mutant in [("eski envanteri silen", m_eski), ("yeni envanteri silen", m_yeni), ("hashleri değiştiren", m_hash)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def sbom_fark_raporu(eski, yeni):
    import copy
    import re
    def dogrula(bilesenler):
        if not isinstance(bilesenler, list):
            raise ValueError("envanter liste olmalı")
        desen = r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}"
        temiz = []
        for b in bilesenler:
            if not isinstance(b, dict) or set(b) != {"id", "tur", "surum", "sha256", "bagimliliklar"}:
                raise ValueError("bileşen şeması geçersiz")
            if not isinstance(b["id"], str) or not re.fullmatch(desen, b["id"]):
                raise ValueError("kimlik geçersiz")
            if b["tur"] not in ("model", "veri", "bagimlilik", "temel_imaj"):
                raise ValueError("tür geçersiz")
            if not isinstance(b["surum"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,63}", b["surum"]):
                raise ValueError("sürüm geçersiz")
            if not isinstance(b["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", b["sha256"]):
                raise ValueError("SHA-256 geçersiz")
            if not isinstance(b["bagimliliklar"], list) or any(not isinstance(x, str) or not re.fullmatch(desen, x) for x in b["bagimliliklar"]):
                raise ValueError("bağımlılıklar geçersiz")
            if len(set(b["bagimliliklar"])) != len(b["bagimliliklar"]) or b["id"] in b["bagimliliklar"]:
                raise ValueError("bağımlılıklar benzersiz olmalı")
            temiz.append({"id": b["id"], "tur": b["tur"], "surum": b["surum"], "sha256": b["sha256"], "bagimliliklar": sorted(b["bagimliliklar"])})
        if len({x["id"] for x in temiz}) != len(temiz):
            raise ValueError("kimlikler yinelenemez")
        harita = {x["id"]: x for x in temiz}
        if any(bag not in harita for x in temiz for bag in x["bagimliliklar"]):
            raise ValueError("bağımlılık bulunamadı")
        ziyaret_ediliyor = set()
        tamamlandi = set()
        def ziyaret(kimlik):
            if kimlik in ziyaret_ediliyor:
                raise ValueError("bağımlılık döngüsü")
            if kimlik in tamamlandi:
                return
            ziyaret_ediliyor.add(kimlik)
            for bag in harita[kimlik]["bagimliliklar"]:
                ziyaret(bag)
            ziyaret_ediliyor.remove(kimlik)
            tamamlandi.add(kimlik)
        for kimlik in harita:
            ziyaret(kimlik)
        return harita
    eski_harita = dogrula(eski)
    yeni_harita = dogrula(yeni)
    eklenen = sorted(set(yeni_harita) - set(eski_harita))
    kaldirilan = sorted(set(eski_harita) - set(yeni_harita))
    degisen = []
    for kimlik in sorted(set(eski_harita) & set(yeni_harita)):
        alanlar = [alan for alan in ("bagimliliklar", "sha256", "surum", "tur") if eski_harita[kimlik][alan] != yeni_harita[kimlik][alan]]
        if alanlar:
            degisen.append({"id": kimlik, "alanlar": alanlar})
    return {"eklenen": eklenen, "kaldirilan": kaldirilan, "degisen": degisen, "ozet": {"eklenen": len(eklenen), "kaldirilan": len(kaldirilan), "degisen": len(degisen)}}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    print(sbom_fark_raporu(json_yukle("veri/sbom_eski.json"), json_yukle("veri/sbom_yeni.json")))
```

```hint
Her envanteri aynı doğrulamadan geçirip kimlik haritasına çevir. Ortak kimliklerde dört alanı da karşılaştır.
```
:::


::: anlat Gerçek deney · Görünür ayar ve kalıcı öğrenci kopyası
Önce `/data/ai-guvence-21-deney.txt` adresini ders sunucusunda açıp sentetik JSON ayarını incele. Kaynak proje dosyası `web/data/ai-guvence-21-deney.txt`.

Çalıştır ilk kullanımda örneği `PAFTA_DATA/calisma/ai-guvence-21/ayar.json` dosyasına yalnız yoksa kopyalar; sonraki çalıştırmalar düzenlemeni korur. Göreli PAFTA_DATA proje köküne göre çözülür. Çalıştır çıktısındaki tam yolu bir metin editöründe aç, seed veya adim değiştir ve yeniden Çalıştır. Dahili dosya editörü yoktur. Kopyayı sıfırlamak için başka ada taşı; kendi düzenlemelerin otomatik silinmez. Kontrol ayrı geçici, görülmemiş girdiler kullanır.

Bu yerel SHA-256 envanteridir; Syft/CycloneDX taraması, lisans veya kaynağın güvenilirliği ispatı değildir. Saldırının başarılı olması geçme koşulu değildir. Bağımlılık/çağrı eksikse deney başarısız olur. Gerçek ağırlıklar Çalıştır klasöründe, girişler/çıktılar/hash/sürümler kabul kanıtında tutulur.

Kaynaklar: [CycloneDX v1.6 — ML-BOM / AI Bill of Materials Specification](https://cyclonedx.org/capabilities/mlbom/), [OWASP Top 10 for Large Language Model Applications — LLM03 Supply Chain](https://genai.owasp.org/llmrisk/llm032025-supply-chain/).
:::

::: gorev Gerçek deney · Diskten model/veri SBOM ve değişiklik izi
`disk_envanteri(kok, tanimlar)` her tanımın `id`, `dosya`, `bagimliliklar` alanlarını alır. Dosyayı gerçekten okuyup `id`, `sha256`, `boyut`, sıralı `bagimliliklar` içeren kayıtları id sırasıyla döndür. Dosya yalnız kök içindeki normal dosya olabilir; mutlak yol, kök dışına kaçış/bağlantı hedefi veya bulunmayan dosya için ValueError yükselt. Aynı dosya değiştiğinde envanter değişmeli. Öğrenci fonksiyonu gerçek ağırlık/veri dosyaları üzerinde çağrılır.

```meta
motor: ai-gercek
gereksinim: torch
timeout: 180
```

```starter
import ai_lab

def disk_envanteri(kok, tanimlar):
    return None

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_21 as deney
    deney.goster(disk_envanteri)
```

```test
import ai_lab
import ast
YASAK = ("envanter_ref", "kanit_yaz")
sorun = ai_lab.kod_denetimi(src, yasak=YASAK)
for dugum in ast.walk(ast.parse(src)):
    if isinstance(dugum, ast.ImportFrom) and any(ad.name in YASAK or ad.name == "*" for ad in dugum.names):
        sorun.append("referans veya kanıt yazıcısı içe aktarılamaz")
if sorun:
    ok(False, "Kendi envanter işlevini yaz: " + "; ".join(sorun))
    stop()
import tempfile,json
from pathlib import Path
from sandbox import ai_gercek_ai_guvence_21 as deney
import hashlib as _hl
with tempfile.TemporaryDirectory(prefix='pafta-g21-u-') as _ut:
    _ur = Path(_ut); (_ur / 'alt').mkdir()
    (_ur / 'b.bin').write_bytes(b'abc'); (_ur / 'alt' / 'a.bin').write_bytes(b'')
    (_ur / 'dis.bin').write_bytes(b'x')
    _bek = [
        {'id': 'a', 'sha256': _hl.sha256(b'').hexdigest(), 'boyut': 0, 'bagimliliklar': ['x', 'y']},
        {'id': 'b', 'sha256': _hl.sha256(b'abc').hexdigest(), 'boyut': 3, 'bagimliliklar': []},
    ]
    ok(disk_envanteri(_ur, [{'id': 'b', 'dosya': 'b.bin', 'bagimliliklar': []}, {'id': 'a', 'dosya': 'alt/a.bin', 'bagimliliklar': ['y', 'x']}]) == _bek, 'disk_envanteri SHA-256, boyut ve sıralamayı doğru üretmeli')
    for _kok_test, _kotu in ((_ur / 'alt', [{'id': 'x', 'dosya': '../dis.bin', 'bagimliliklar': []}]), (_ur, [{'id': 'x', 'dosya': str((_ur / 'b.bin').resolve()), 'bagimliliklar': []}]), (_ur, [{'id': 'x', 'dosya': 'alt', 'bagimliliklar': []}]), (_ur, [{'id': 'x', 'dosya': 'yok.bin', 'bagimliliklar': []}])):
        try:
            disk_envanteri(_kok_test, _kotu); ok(False, 'geçersiz yol ValueError fırlatmalı')
        except ValueError:
            ok(True, 'geçersiz yol reddedildi')
with tempfile.TemporaryDirectory(prefix='pafta-g21-') as tmp:
    root=Path(tmp); config=root/'girdi.json'
    # Hidden inputs independent of the editable student sample.
    sonuclar=[]
    for seed in (7100+21,9200+21):
        config.write_text(json.dumps(dict(seed=seed,adim=45)),encoding='utf-8')
        r=deney.deney(disk_envanteri,config,root/str(seed))
        for ad,deger in r['kontroller'].items(): ok(deger,'GERCEK 21: '+ad)
        sonuclar.append(r)
    kabul=all(all(r['kontroller'].values()) for r in sonuclar)
    ai_lab.kanit_yaz('guvence-21-kabul',dict(kaynak='gercek',kabul=kabul,deneyler=sonuclar,ortam=sonuclar[0]['ortam'],temizlik='Gorev temp dosyalari kapsam sonunda temizlenir; JSON kaniti kalicidir.'))
```

```solution
import ai_lab

def disk_envanteri(kok, tanimlar):
    from pathlib import Path
    import hashlib
    root=Path(kok).resolve(); rows=[]
    for d in tanimlar:
        raw=Path(d['dosya']); p=(root/raw).resolve()
        if raw.is_absolute() or not p.is_relative_to(root) or not p.is_file():
            raise ValueError('dosya kok disinda veya yok')
        b=p.read_bytes()
        rows.append(dict(id=d['id'],sha256=hashlib.sha256(b).hexdigest(),boyut=len(b),bagimliliklar=sorted(d['bagimliliklar'])))
    return sorted(rows,key=lambda r:r['id'])

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_21 as deney
    deney.goster(disk_envanteri)
```

```hint
Gerçek çıktıları ölç; tek seed veya görünür örneği ezberleme. Kabul deneyin ve ölçümün doğru yürütülmesidir.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Kod SBOM'u neden ML için eksik kalır? (30 sn).** "Klasik yazılım envanteri yalnız paket sürümlerini izler; oysa yapay zekâ sisteminde ağırlık dosyası, ince ayar verisi, tokenizer ve temel konteyner imajından herhangi biri değiştiğinde modelin davranışı sessizce değişir (`ML-BOM`)."
2. **Kriptografik özet ve yönlü bağımlılık grafiği (35 sn).** "Her bileşeni `SHA-256` özeti ve yönlü bağımlılık kenarlarıyla bağladığımızda, kırık referanslar, döngüler ve iki sürüm arasındaki sessiz ağırlık veya veri kaymaları (`sbom_fark_raporu`) otomatik yakalanır."
3. **Bütünlük ile kaynak güvenilirliği sınırı (30 sn).** "Yerel `SHA-256` doğrulaması dosyanın yolda veya diskte değişmediğini kanıtlar; ama envanterin kendisi imzasızsa ya da kaynak veri baştan zehirliyse tek başına güvenlik sağlamaz."
4. **Soru (25 sn).** "Üretimdeki model ağırlığının `SHA-256` özeti değişmediği halde sistem çıktıları kaydıysa `ML-BOM` grafiğindeki hangi komşu bileşenleri ilk sırada denetlersin?"
:::
