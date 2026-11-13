---
id: ai-guvence-25
title: Yerel Model Tedarik Zinciri Değerlendirmesi
summary: Yerel modelin indirme, kaynak, bağımlılık, dosya biçimi ve yalıtım katmanlarını ayrı bulgularla değerlendir; ölçülebilir karar raporu üret.
esleme: ai-guvence-21, ai-guvence-22, ai-uretim-36
timeout: 45
---

::: anlat Model dosyası tedarik zincirinin yalnız bir parçasıdır
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Dosya byte'ları, hash, kaynak/sürüm kaydı ve yüklemeden önce politika kararı | Görevler 1–3 görünür sentetik JSON tedarik kayıtları; son görev gerçekten eğitilmiş kendi küçük modelini safetensors olarak kaydeder, değiştirilmiş dosyayı ve manifestleri sınar | Hash eşleşmesi imza veya güvenilir kaynak kanıtı değildir; yerel politika kapısı tam sandbox, Syft veya modelscan taraması değildir |

> [!NOT]
> `veri/tedarik_kayitlari.json` sentetik öğretim dosyasıdır, indirme/tarama kaydı değildir. Setup her çalıştırmada geçici dizine yeniden kopyalar; kalıcılık yoktur. Üç görev aynı dosyayı gerçekten okur; aynı çalıştırmada bellekte kopyasını değiştirerek deneyebilirsin. Son gerçek deneyin `PAFTA_DATA/calisma/ai-guvence-25/ayar.json` kopyası ayrıdır ve kalıcıdır; varsa üzerine yazılmaz. Gizli kontrol girdileri bu dosyadan bağımsızdır. Yalnız laboratuvarın ürettiği model yüklenir; dış dosya veya model indirilmez.

Yerel model değerlendirmesi dosya biçimiyle sınırlı değildir. Kaynağın bilinip bilinmediği, indirme kanalı, bağımlılıkların sürümleri ve çalıştırma yalıtımı birlikte ele alınır. Safetensors veya GGUF biçimi, bilinmeyen kaynaklı dosyayı kendiliğinden güvenilir yapmaz.

Bu derste Ollama, modelscan veya Syft çalıştırılmaz; dosya indirilmez. Görevler 1–3 sentetik dosya kayıtlarından katman bulguları üretir. Son görev gerçek CPU eğitimiyle oluşturulan safetensors dosyasını hash ve manifest kapısıyla yükler. Bulgu puanı inceleme önceliği içindir, gerçek bir güvenlik taramasının yerine geçmez.
:::

::: anlat Karar ile kanıt düzeyi birbirinden ayrılmalıdır
HTTP indirme ve pickle biçimi bu dersin politikasında durdurma nedenidir. Bilinmeyen kaynak, sabitlenmemiş bağımlılık veya eksik yalıtım inceleme gerektirir. Bir kayıtta birden fazla bulgu varsa yalnız en yüksek puanlı bulguyu raporlamak diğer riskleri gizler.

Kararlar `devam`, `incele` ve `durdur` olarak verilir. `devam`, yalnız tanımlı kayıt alanlarında bulgu olmadığını gösterir; modelin veya tedarik zincirinin tamamen güvenli olduğu anlamına gelmez.
:::

::: anlat Kaynak kaydından gerçek yükleme kapısına
Bir model paketini değerlendirirken dosya biçimi, kaynak kimliği ve çalıştırma ortamını ayrı sorular olarak ele almalısın. Güvenli veri serileştirmesi bazı riskleri azaltabilir; yanlış eğitim verisi, kötü amaçlı davranış veya hatalı bağımlılık sürümü gibi sorunları tek başına çözmez. Bu derste safetensors adı bir güven damgası değildir. İlk görevlerde resmi kaynak alanı da sentetik bir etikettir; bir imzanın kriptografik doğrulaması veya uzak sunucunun kimlik denetimi yapılmış olmaz. Hangi kontrolün gerçekten çalıştığını ve hangisinin yalnız girdi olarak verildiğini raporda açık tutmak gerekir.

Önce `veri/tedarik_kayitlari.json` dosyasını ham biçimde yazdır. Her kayıtta kimlik, kaynak, indirme kanalı, bağımlılık durumu, biçim ve yalıtım alanları bulunur. İlk görev bunların izinli değerlerle geldiğini denetler; bu şema kontrolü dosyanın zararsızlığını kanıtlamaz. Yalıtım alanının bool olması önemlidir: boş olmayan bir metni doğru saymak güvenlik durumunu sessizce değiştirebilir. Kimlik kopyalarının birbirinden bağımsız olmasını koru. Aynı dosyadaki kayıtları sonraki görevde tekrar okuyarak ham alan ile verilen karar arasında bağlantı kurabilirsin.

İkinci görev her risk katmanını ayrı bulguya dönüştürür. HTTP indirme ve pickle biçimi burada seçilmiş politikanın durdurma nedenleridir; bilinmeyen kaynak veya sabitlenmemiş bağımlılık ise inceleme gerektirir. Bunlar dersin karar kurallarıdır; bütün olası ortamlarda yalnız bu alanlara bakarak kesin güvenlik hükmü verilemez. Bir kayıtta birden çok bulgu varsa hepsini yaz. Yalnız en yüksek puanı korumak, diğer katmanda neyin düzeltilmesi gerektiğini gizler. Puan inceleme önceliğidir; tek sayıyı bütün sisteme ait olasılık veya risk yüzdesi gibi yorumlama.

Üçüncü görev aynı kayıtları bir araya getirir ve bulgu sayılarını her başlık için üretir. Sıfır bulgu anahtarlarının da bulunması farklı raporların aynı biçimde karşılaştırılmasını sağlar. Genel karar, toplam puana rastgele bir eşik uygulayarak değil, kayıt kararları arasındaki öncelikten çıkarılır. Bir tek durdur kaydı varken diğer iyi kayıtların puanı bunu telafi edemez. Dosyada bir kaydın yalıtım alanını bellekte kopyalayıp değiştir; hangi bulgu sayılarının ve genel kararın değiştiğine bak. Görünür örnekleri değiştirmek gizli testin beklenen cevabını değiştirmez.

Son görev küçük bir modeli gerçekten autograd ile eğitir ve ağırlıklarını safetensors dosyasına kaydeder. Öğrencinin kapısı gerçek dosyanın byte hash'i ile manifestteki hash'i karşılaştırır; kaynak, biçim ve torch sürümü koşullarını da birlikte arar. Değiştirilmiş dosya vakasında dosyanın sonuna bir byte eklenir; yeniden hesaplanan hash artık eşleşmez. Dosya adı aynı kaldığı için yalnız isme güvenen politika bu değişimi kaçırır. Diğer vakalarda kaynak, biçim ve sürüm tek tek bozulur. Eksik manifest alanları kapalı karara yol açmalıdır; olumlu varsayım kullanma.

Kapı izin verdiğinde gerçekten yükleme ve küçük bir ileri hesap yapılır; kararın sözlükte doğru görünmesi yeterli değildir. Ek koruma yalnız kendi ürettiğimiz ve byte'ları bilinen dosyanın deserializasyonuna izin verir. Dolayısıyla bu laboratuvarın hatalı öğrenci politikasını sınamak için bilinmeyen zararlı model çalıştırdığı iddia edilmez. Kaynak allowlist'i gerçek imza doğrulaması değildir; bir saldırgan hem dosyayı hem manifesti değiştirebiliyorsa hash alanını da yenileyebilir. Güvenilir manifestin nereden geldiği ayrı sorudur. Yükleme sınaması, bağımlılık yönetimi ve gerçek işletim sistemi yalıtımı birlikte değerlendirilmelidir. Sonuçta devam kararı yalnız bu tanımlı kontrolleri geçtiğini söyler; modelin bütün davranışlarının güvenli olduğunu söylemez.
:::

::: tahmin Katman bulgularını ve kararını tahmin et
Üç çıktı satırını yaz:

```python
bulgular = ["kaynak_dogrulanmali", "bagimlilik_sabitlenmeli", "yalitim_eksik"]
print(sum([3, 2, 3]))
print("durdur" if "riskli_bicim" in bulgular else "incele" if bulgular else "devam")
print(len([]))
```

???

```cikti
8
incele
0
```

İlk satır üç bulgunun öncelik puanını, ikinci satır kritik biçim bulunmayan kaydın inceleme kararını, üçüncü satır bulgusuz kaydın bulgu sayısını gösterir.
:::

::: gorev 1 · Tedarik zinciri kaydını doğrula
`tedarik_kaydi_dogrula(kayit)` işlevini yaz. Kayıt tam olarak `id`, `kaynak`, `indirme`, `bagimlilik`, `bicim`, `yalitim` alanlarını taşır. Kimlik 1–64 karakterlik, ASCII harf/rakamla başlayan ve yalnız ASCII harf, rakam, alt çizgi veya tire içeren stringdir.

Kaynak yalnız `resmi`, `topluluk`, `bilinmeyen`; indirme yalnız `https`, `http`, `yerel`; bağımlılık yalnız `sabit`, `degisken`; biçim yalnız `safetensors`, `gguf`, `pickle` olur. Yalıtım bool olmalıdır. Geçersiz veride `ValueError` yükselt. Bağımsız sözlük kopyası döndür ve girdiyi değiştirme.

```starter
def tedarik_kaydi_dogrula(kayit):
    # KUSURLU BAŞLANGIÇ KODU: şema ve bool yalıtım alanını doğrulamadan kopyalıyor.
    return dict(kayit)

from ai_guvence_veri import json_yukle
for kayit in json_yukle("veri/tedarik_kayitlari.json"):
    print(tedarik_kaydi_dogrula(kayit))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-25")
```

```test
import copy
K = {"id": "model-1", "kaynak": "resmi", "indirme": "https", "bagimlilik": "sabit", "bicim": "safetensors", "yalitim": True}
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        if fn(K) != K or fn(K) is K or K != once:
            return False
        sinir = dict(K, id="a" * 64, kaynak="bilinmeyen", indirme="http", bagimlilik="degisken", bicim="pickle", yalitim=False)
        if fn(sinir) != sinir or fn(dict(K, kaynak="topluluk", indirme="yerel", bicim="gguf"))["bicim"] != "gguf":
            return False
        for kayit in [
            None, [], dict(K, ek=1), dict(K, id=""), dict(K, id="a b"), dict(K, id="a" * 65), dict(K, id=None),
            dict(K, kaynak="diger"), dict(K, kaynak=None), dict(K, kaynak=1),
            dict(K, indirme="ftp"), dict(K, indirme=None), dict(K, indirme=1),
            dict(K, bagimlilik="diger"), dict(K, bagimlilik=None), dict(K, bagimlilik=1),
            dict(K, bicim="pt"), dict(K, bicim=None), dict(K, bicim=1),
            dict(K, yalitim=1), dict(K, yalitim="true"), dict(K, yalitim=None),
        ]:
            try:
                fn(kayit)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(tedarik_kaydi_dogrula), "tedarik şeması, katman değerleri ve yalıtım türü korunmalı")
def m_kaynak(kayit):
    return tedarik_kaydi_dogrula(dict(kayit, kaynak="diger"))
def m_indirme(kayit):
    return tedarik_kaydi_dogrula(dict(kayit, indirme="ftp"))
def m_bicim(kayit):
    return tedarik_kaydi_dogrula(dict(kayit, bicim="pt"))
def m_yalitim(kayit):
    return tedarik_kaydi_dogrula(dict(kayit, yalitim=1))
for ad, mutant in [("kaynağı bozan", m_kaynak), ("indirmeyi bozan", m_indirme), ("biçimi bozan", m_bicim), ("yalıtımı bozan", m_yalitim)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def tedarik_kaydi_dogrula(kayit):
    import re
    if not isinstance(kayit, dict):
        raise ValueError("kayıt sözlük olmalı")
    if set(kayit) != {"id", "kaynak", "indirme", "bagimlilik", "bicim", "yalitim"}:
        raise ValueError("kayıt şeması geçersiz")
    if not isinstance(kayit["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
        raise ValueError("kimlik geçersiz")
    if kayit["kaynak"] not in ("resmi", "topluluk", "bilinmeyen"):
        raise ValueError("kaynak geçersiz")
    if kayit["indirme"] not in ("https", "http", "yerel"):
        raise ValueError("indirme geçersiz")
    if kayit["bagimlilik"] not in ("sabit", "degisken"):
        raise ValueError("bağımlılık geçersiz")
    if kayit["bicim"] not in ("safetensors", "gguf", "pickle"):
        raise ValueError("biçim geçersiz")
    if not isinstance(kayit["yalitim"], bool):
        raise ValueError("yalıtım bool olmalı")
    return dict(kayit)

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    for kayit in json_yukle("veri/tedarik_kayitlari.json"):
        print(tedarik_kaydi_dogrula(kayit))
```

```hint
Her katmanın izinli stringlerini ayrı denetle. Yalıtım için `1` veya metin yerine yalnız bool kabul et.
```
:::

::: gorev 2 · Katman bulgularını ve kararını hesapla
`tedarik_kaydi_degerlendir(kayit)` işlevini yaz. Kayıt ilk görevdeki şemadadır; geçersiz veride `ValueError` yükselt. Girdiyi değiştirmeden `{"id":D,"bulgular":B,"puan":P,"karar":K}` döndür.

Bulgular ve puanları sırasıyla: HTTP indirme için `guvensiz_indirme` ve 4; bilinmeyen kaynak için `kaynak_dogrulanmali` ve 3; değişken bağımlılık için `bagimlilik_sabitlenmeli` ve 2; pickle için `riskli_bicim` ve 5; yalıtım yoksa `yalitim_eksik` ve 3. Yalnız ilgili bulgular bu sırayla eklenir, puan toplamlarıdır.

`guvensiz_indirme` veya `riskli_bicim` varsa karar `durdur`; bunlar yokken en az bir bulgu varsa `incele`; bulgu yoksa `devam` olur.

```starter
def tedarik_kaydi_degerlendir(kayit):
    import re
    if not isinstance(kayit, dict) or set(kayit) != {"id", "kaynak", "indirme", "bagimlilik", "bicim", "yalitim"}:
        raise ValueError("kayıt şeması geçersiz")
    if not isinstance(kayit["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
        raise ValueError("kimlik geçersiz")
    if kayit["kaynak"] not in ("resmi", "topluluk", "bilinmeyen"):
        raise ValueError("kaynak geçersiz")
    if kayit["indirme"] not in ("https", "http", "yerel"):
        raise ValueError("indirme geçersiz")
    if kayit["bagimlilik"] not in ("sabit", "degisken"):
        raise ValueError("bağımlılık geçersiz")
    if kayit["bicim"] not in ("safetensors", "gguf", "pickle"):
        raise ValueError("biçim geçersiz")
    if not isinstance(kayit["yalitim"], bool):
        raise ValueError("yalıtım bool olmalı")
    # KUSURLU BAŞLANGIÇ KODU: tek kritik bulgu yerine iki kritik bulguyu birlikte arıyor.
    bulgular = []
    puanlar = []
    if kayit["indirme"] == "http":
        bulgular.append("guvensiz_indirme")
        puanlar.append(4)
    if kayit["kaynak"] == "bilinmeyen":
        bulgular.append("kaynak_dogrulanmali")
        puanlar.append(3)
    if kayit["bagimlilik"] == "degisken":
        bulgular.append("bagimlilik_sabitlenmeli")
        puanlar.append(2)
    if kayit["bicim"] == "pickle":
        bulgular.append("riskli_bicim")
        puanlar.append(5)
    if not kayit["yalitim"]:
        bulgular.append("yalitim_eksik")
        puanlar.append(3)
    if "guvensiz_indirme" in bulgular and "riskli_bicim" in bulgular:
        karar = "durdur"
    elif bulgular:
        karar = "incele"
    else:
        karar = "devam"
    return {"id": kayit["id"], "bulgular": bulgular, "puan": sum(puanlar), "karar": karar}

from ai_guvence_veri import json_yukle
for kayit in json_yukle("veri/tedarik_kayitlari.json"):
    print(tedarik_kaydi_degerlendir(kayit))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-25")
```

```test
import copy
K = {"id": "model-1", "kaynak": "resmi", "indirme": "https", "bagimlilik": "sabit", "bicim": "safetensors", "yalitim": True}
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        if fn(K) != {"id": "model-1", "bulgular": [], "puan": 0, "karar": "devam"} or K != once:
            return False
        tumu = dict(K, id="a" * 64, kaynak="bilinmeyen", indirme="http", bagimlilik="degisken", bicim="pickle", yalitim=False)
        if fn(tumu) != {"id": "a" * 64, "bulgular": ["guvensiz_indirme", "kaynak_dogrulanmali", "bagimlilik_sabitlenmeli", "riskli_bicim", "yalitim_eksik"], "puan": 17, "karar": "durdur"}:
            return False
        durumlar = [
            (dict(K, indirme="http"), ["guvensiz_indirme"], 4, "durdur"),
            (dict(K, kaynak="bilinmeyen"), ["kaynak_dogrulanmali"], 3, "incele"),
            (dict(K, bagimlilik="degisken"), ["bagimlilik_sabitlenmeli"], 2, "incele"),
            (dict(K, bicim="pickle"), ["riskli_bicim"], 5, "durdur"),
            (dict(K, yalitim=False), ["yalitim_eksik"], 3, "incele"),
            (dict(K, kaynak="topluluk", indirme="yerel", bicim="gguf"), [], 0, "devam"),
        ]
        for kayit, bulgular, puan, karar in durumlar:
            if fn(kayit) != {"id": "model-1", "bulgular": bulgular, "puan": puan, "karar": karar}:
                return False
        for kayit in [
            None, [], dict(K, ek=1), dict(K, id="a b"), dict(K, id="a" * 65), dict(K, id=None),
            dict(K, kaynak="diger"), dict(K, indirme="ftp"), dict(K, bagimlilik="diger"),
            dict(K, bicim="pt"), dict(K, yalitim=1), dict(K, yalitim=None),
        ]:
            try:
                fn(kayit)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(tedarik_kaydi_degerlendir), "bulgu sırası, ağırlıklar ve karar önceliği korunmalı")
def m_kaynak(kayit):
    return tedarik_kaydi_degerlendir(dict(kayit, kaynak="resmi"))
def m_bicim(kayit):
    return tedarik_kaydi_degerlendir(dict(kayit, bicim="safetensors"))
def m_yalitim(kayit):
    return tedarik_kaydi_degerlendir(dict(kayit, yalitim=True))
def m_indirme(kayit):
    return tedarik_kaydi_degerlendir(dict(kayit, indirme="https"))
for ad, mutant in [("kaynağı gizleyen", m_kaynak), ("biçimi gizleyen", m_bicim), ("yalıtımı gizleyen", m_yalitim), ("indirmeyi gizleyen", m_indirme)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def tedarik_kaydi_degerlendir(kayit):
    import re
    if not isinstance(kayit, dict) or set(kayit) != {"id", "kaynak", "indirme", "bagimlilik", "bicim", "yalitim"}:
        raise ValueError("kayıt şeması geçersiz")
    if not isinstance(kayit["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
        raise ValueError("kimlik geçersiz")
    if kayit["kaynak"] not in ("resmi", "topluluk", "bilinmeyen"):
        raise ValueError("kaynak geçersiz")
    if kayit["indirme"] not in ("https", "http", "yerel"):
        raise ValueError("indirme geçersiz")
    if kayit["bagimlilik"] not in ("sabit", "degisken"):
        raise ValueError("bağımlılık geçersiz")
    if kayit["bicim"] not in ("safetensors", "gguf", "pickle"):
        raise ValueError("biçim geçersiz")
    if not isinstance(kayit["yalitim"], bool):
        raise ValueError("yalıtım bool olmalı")
    bulgular = []
    puanlar = []
    if kayit["indirme"] == "http":
        bulgular.append("guvensiz_indirme")
        puanlar.append(4)
    if kayit["kaynak"] == "bilinmeyen":
        bulgular.append("kaynak_dogrulanmali")
        puanlar.append(3)
    if kayit["bagimlilik"] == "degisken":
        bulgular.append("bagimlilik_sabitlenmeli")
        puanlar.append(2)
    if kayit["bicim"] == "pickle":
        bulgular.append("riskli_bicim")
        puanlar.append(5)
    if not kayit["yalitim"]:
        bulgular.append("yalitim_eksik")
        puanlar.append(3)
    if "guvensiz_indirme" in bulgular or "riskli_bicim" in bulgular:
        karar = "durdur"
    elif bulgular:
        karar = "incele"
    else:
        karar = "devam"
    return {"id": kayit["id"], "bulgular": bulgular, "puan": sum(puanlar), "karar": karar}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    for kayit in json_yukle("veri/tedarik_kayitlari.json"):
        print(tedarik_kaydi_degerlendir(kayit))
```

```hint
Her bulguyla puanını aynı anda ekle. Durdurma kararını iki kritik bulguya, inceleme kararını kalan bulgulara bağla.
```
:::

::: gorev 3 · Çok kayıtlı tedarik zinciri raporu üret
`tedarik_zinciri_raporu(kayitlar)` işlevini yaz. Girdi ilk görevdeki kayıtların boş olmayan listesidir; kimlikler yinelenemez. Geçersiz veride `ValueError` yükselt.

Her kayıt için ikinci görevdeki bulgu, puan ve karar kurallarını uygula; girdi sırasını koru. `bulgu_sayilari` sözlüğü beş bulgunun tamamını her zaman şu sırayla içersin: `guvensiz_indirme`, `kaynak_dogrulanmali`, `bagimlilik_sabitlenmeli`, `riskli_bicim`, `yalitim_eksik`. Değerler tüm kayıtlardaki görünme sayılarıdır.

`{"kayitlar":[...],"bulgu_sayilari":S,"toplam_puan":P,"genel_karar":K}` döndür. Herhangi bir kayıt `durdur` ise genel karar `durdur`; yoksa herhangi bir kayıt `incele` ise `incele`; tümü `devam` ise `devam` olur. Girdiyi değiştirme.

```starter
def tedarik_zinciri_raporu(kayitlar):
    import re
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar boş olmayan liste olmalı")
    temiz = []
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"id", "kaynak", "indirme", "bagimlilik", "bicim", "yalitim"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(kayit["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
            raise ValueError("kimlik geçersiz")
        if kayit["kaynak"] not in ("resmi", "topluluk", "bilinmeyen"):
            raise ValueError("kaynak geçersiz")
        if kayit["indirme"] not in ("https", "http", "yerel"):
            raise ValueError("indirme geçersiz")
        if kayit["bagimlilik"] not in ("sabit", "degisken"):
            raise ValueError("bağımlılık geçersiz")
        if kayit["bicim"] not in ("safetensors", "gguf", "pickle"):
            raise ValueError("biçim geçersiz")
        if not isinstance(kayit["yalitim"], bool):
            raise ValueError("yalıtım bool olmalı")
        temiz.append(dict(kayit))
    if len({x["id"] for x in temiz}) != len(temiz):
        raise ValueError("kimlikler yinelenemez")
    agirliklar = {"guvensiz_indirme": 4, "kaynak_dogrulanmali": 3, "bagimlilik_sabitlenmeli": 2, "riskli_bicim": 5, "yalitim_eksik": 3}
    sayim = {ad: 0 for ad in agirliklar}
    sonuc_kayitlar = []
    for kayit in temiz:
        bulgular = []
        if kayit["indirme"] == "http":
            bulgular.append("guvensiz_indirme")
        if kayit["kaynak"] == "bilinmeyen":
            bulgular.append("kaynak_dogrulanmali")
        if kayit["bagimlilik"] == "degisken":
            bulgular.append("bagimlilik_sabitlenmeli")
        if kayit["bicim"] == "pickle":
            bulgular.append("riskli_bicim")
        if not kayit["yalitim"]:
            bulgular.append("yalitim_eksik")
        for bulgu in bulgular:
            sayim[bulgu] += 1
        if "guvensiz_indirme" in bulgular or "riskli_bicim" in bulgular:
            karar = "durdur"
        elif bulgular:
            karar = "incele"
        else:
            karar = "devam"
        sonuc_kayitlar.append({"id": kayit["id"], "bulgular": bulgular, "puan": sum(agirliklar[x] for x in bulgular), "karar": karar})
    kararlar = {x["karar"] for x in sonuc_kayitlar}
    # KUSURLU BAŞLANGIÇ KODU: durdurma bulgusunu genel raporda incele seviyesine indiriyor.
    genel = "incele" if "durdur" in kararlar else "incele" if "incele" in kararlar else "devam"
    return {"kayitlar": sonuc_kayitlar, "bulgu_sayilari": sayim, "toplam_puan": sum(x["puan"] for x in sonuc_kayitlar), "genel_karar": genel}

from ai_guvence_veri import json_yukle
print(tedarik_zinciri_raporu(json_yukle("veri/tedarik_kayitlari.json")))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-25")
```

```test
import copy
K = [
    {"id": "a", "kaynak": "resmi", "indirme": "https", "bagimlilik": "sabit", "bicim": "safetensors", "yalitim": True},
    {"id": "b", "kaynak": "bilinmeyen", "indirme": "yerel", "bagimlilik": "degisken", "bicim": "gguf", "yalitim": False},
    {"id": "c", "kaynak": "topluluk", "indirme": "http", "bagimlilik": "degisken", "bicim": "pickle", "yalitim": False},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        sonuc = fn(K)
        if K != once or sonuc["toplam_puan"] != 22 or sonuc["genel_karar"] != "durdur":
            return False
        if [x["id"] for x in sonuc["kayitlar"]] != ["a", "b", "c"] or [x["karar"] for x in sonuc["kayitlar"]] != ["devam", "incele", "durdur"]:
            return False
        if sonuc["kayitlar"][1] != {"id": "b", "bulgular": ["kaynak_dogrulanmali", "bagimlilik_sabitlenmeli", "yalitim_eksik"], "puan": 8, "karar": "incele"}:
            return False
        if sonuc["kayitlar"][2]["bulgular"] != ["guvensiz_indirme", "bagimlilik_sabitlenmeli", "riskli_bicim", "yalitim_eksik"] or sonuc["kayitlar"][2]["puan"] != 14:
            return False
        if sonuc["bulgu_sayilari"] != {"guvensiz_indirme": 1, "kaynak_dogrulanmali": 1, "bagimlilik_sabitlenmeli": 2, "riskli_bicim": 1, "yalitim_eksik": 2}:
            return False
        if fn([K[0]]) != {"kayitlar": [{"id": "a", "bulgular": [], "puan": 0, "karar": "devam"}], "bulgu_sayilari": {"guvensiz_indirme": 0, "kaynak_dogrulanmali": 0, "bagimlilik_sabitlenmeli": 0, "riskli_bicim": 0, "yalitim_eksik": 0}, "toplam_puan": 0, "genel_karar": "devam"}:
            return False
        if fn(K[:2])["genel_karar"] != "incele" or fn(K[:2])["toplam_puan"] != 8:
            return False
        sinir = dict(K[0], id="a" * 64, kaynak="bilinmeyen", indirme="http", bagimlilik="degisken", bicim="pickle", yalitim=False)
        if fn([sinir])["toplam_puan"] != 17:
            return False
        if fn([dict(K[0], indirme="http")])["genel_karar"] != "durdur" or fn([dict(K[0], bicim="pickle")])["genel_karar"] != "durdur":
            return False
        for kayitlar in [
            None, {}, tuple(K), [], [None], [dict(K[0], ek=1)], [dict(K[0], id="a b")], [dict(K[0], id="a" * 65)], [dict(K[0], id=None)],
            [dict(K[0], kaynak="diger")], [dict(K[0], indirme="ftp")], [dict(K[0], bagimlilik="diger")],
            [dict(K[0], bicim="pt")], [dict(K[0], yalitim=1)], [K[0], K[0]],
        ]:
            try:
                fn(kayitlar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(tedarik_zinciri_raporu), "sıralama, bulgu sayıları, puan toplamı ve genel karar korunmalı")
def m_sil(kayitlar):
    return tedarik_zinciri_raporu(kayitlar[:1])
def m_yalitim(kayitlar):
    return tedarik_zinciri_raporu([dict(x, yalitim=True) for x in kayitlar])
def m_bicim(kayitlar):
    return tedarik_zinciri_raporu([dict(x, bicim="gguf") for x in kayitlar])
def m_kaynak(kayitlar):
    return tedarik_zinciri_raporu([dict(x, kaynak="resmi") for x in kayitlar])
for ad, mutant in [("kayıtları silen", m_sil), ("yalıtımı gizleyen", m_yalitim), ("biçimi gizleyen", m_bicim), ("kaynağı gizleyen", m_kaynak)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def tedarik_zinciri_raporu(kayitlar):
    import re
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar boş olmayan liste olmalı")
    temiz = []
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"id", "kaynak", "indirme", "bagimlilik", "bicim", "yalitim"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(kayit["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
            raise ValueError("kimlik geçersiz")
        if kayit["kaynak"] not in ("resmi", "topluluk", "bilinmeyen"):
            raise ValueError("kaynak geçersiz")
        if kayit["indirme"] not in ("https", "http", "yerel"):
            raise ValueError("indirme geçersiz")
        if kayit["bagimlilik"] not in ("sabit", "degisken"):
            raise ValueError("bağımlılık geçersiz")
        if kayit["bicim"] not in ("safetensors", "gguf", "pickle"):
            raise ValueError("biçim geçersiz")
        if not isinstance(kayit["yalitim"], bool):
            raise ValueError("yalıtım bool olmalı")
        temiz.append(dict(kayit))
    if len({x["id"] for x in temiz}) != len(temiz):
        raise ValueError("kimlikler yinelenemez")
    agirliklar = {"guvensiz_indirme": 4, "kaynak_dogrulanmali": 3, "bagimlilik_sabitlenmeli": 2, "riskli_bicim": 5, "yalitim_eksik": 3}
    sayim = {ad: 0 for ad in agirliklar}
    sonuc_kayitlar = []
    for kayit in temiz:
        bulgular = []
        if kayit["indirme"] == "http":
            bulgular.append("guvensiz_indirme")
        if kayit["kaynak"] == "bilinmeyen":
            bulgular.append("kaynak_dogrulanmali")
        if kayit["bagimlilik"] == "degisken":
            bulgular.append("bagimlilik_sabitlenmeli")
        if kayit["bicim"] == "pickle":
            bulgular.append("riskli_bicim")
        if not kayit["yalitim"]:
            bulgular.append("yalitim_eksik")
        for bulgu in bulgular:
            sayim[bulgu] += 1
        if "guvensiz_indirme" in bulgular or "riskli_bicim" in bulgular:
            karar = "durdur"
        elif bulgular:
            karar = "incele"
        else:
            karar = "devam"
        sonuc_kayitlar.append({"id": kayit["id"], "bulgular": bulgular, "puan": sum(agirliklar[x] for x in bulgular), "karar": karar})
    kararlar = {x["karar"] for x in sonuc_kayitlar}
    genel = "durdur" if "durdur" in kararlar else "incele" if "incele" in kararlar else "devam"
    return {"kayitlar": sonuc_kayitlar, "bulgu_sayilari": sayim, "toplam_puan": sum(x["puan"] for x in sonuc_kayitlar), "genel_karar": genel}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    print(tedarik_zinciri_raporu(json_yukle("veri/tedarik_kayitlari.json")))
```

```hint
Sayım sözlüğünü bütün bulgu adlarıyla sıfırdan başlat. Genel kararı kayıt kararlarından türet; puanı karar eşiği olarak kullanma.
```
:::


::: anlat Gerçek deney · Görünür ayar ve kalıcı öğrenci kopyası
Önce `/data/ai-guvence-25-deney.txt` adresini ders sunucusunda açıp sentetik JSON ayarını incele. Kaynak proje dosyası `web/data/ai-guvence-25-deney.txt`.

Çalıştır ilk kullanımda örneği `PAFTA_DATA/calisma/ai-guvence-25/ayar.json` dosyasına yalnız yoksa kopyalar; sonraki çalıştırmalar düzenlemeni korur. Göreli PAFTA_DATA proje köküne göre çözülür. Çalıştır çıktısındaki tam yolu bir metin editöründe aç, seed veya adim değiştir ve yeniden Çalıştır. Dahili dosya editörü yoktur. Kopyayı sıfırlamak için başka ada taşı; kendi düzenlemelerin otomatik silinmez. Kontrol ayrı geçici, görülmemiş girdiler kullanır.

Yalnız kendi sentetik yerel `safetensors` artefaktımız yüklenir. Kaynak izin listesi yerel politika girdisidir; imza veya uzak sunucu kimlik doğrulaması değildir. Bu bir `modelscan`/`Syft` taraması veya tam yalıtım güvencesi değildir. Saldırının başarılı olması geçme koşulu değildir. Bağımlılık veya çağrı eksikse deney başarısız olur. Gerçek ağırlıklar Çalıştır klasöründe, girişler/çıktılar/hash/sürümler kabul kanıtında tutulur.

Kaynaklar: [OWASP Top 10 for LLM Applications — LLM03 Supply Chain](https://genai.owasp.org/llmrisk/llm032025-supply-chain/), [MITRE ATLAS — ML Supply Chain Compromise (AML.T0010)](https://atlas.mitre.org/techniques/AML.T0010).
:::

::: gorev Gerçek deney · Hash ve kaynak kapısından gerçek yüklemeye
`tedarik_kapisi(manifest, gercek_hash, sabit_surum)` bool döndürür: manifest `sha256` gerçek hash ile aynı, `kaynak` yerel-sentetik, `bicim` safetensors ve `torch` sabit_surum ile aynıysa True. Eksik alanlar False. Karar gerçek safetensors yüklemesinden önce uygulanır. Dosya değişimi, biçim, kaynak ve sürüm ayrı test edilir; kendi artefaktımız dışında dosya yüklenmez.

```meta
motor: ai-gercek
gereksinim: torch
timeout: 180
```

```starter
import ai_lab

def tedarik_kapisi(manifest, gercek_hash, sabit_surum):
    return None

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_25 as deney
    deney.goster(tedarik_kapisi)
```

```test
import ai_lab
import ast
YASAK = ("kapi_ref", "kanit_yaz")
sorun = ai_lab.kod_denetimi(src, yasak=YASAK)
for dugum in ast.walk(ast.parse(src)):
    if isinstance(dugum, ast.ImportFrom) and any(ad.name in YASAK or ad.name == "*" for ad in dugum.names):
        sorun.append("referans veya kanıt yazıcısı içe aktarılamaz")
if sorun:
    ok(False, "Kendi kapı işlevini yaz: " + "; ".join(sorun))
    stop()
import tempfile,json
from pathlib import Path
from sandbox import ai_gercek_ai_guvence_25 as deney
_m0 = {'sha256': 'h1', 'kaynak': 'yerel-sentetik', 'bicim': 'safetensors', 'torch': '2.5.0'}
ok(tedarik_kapisi(_m0, 'h1', '2.5.0') is True, 'tam eşleşen yerel safetensors manifesti kabul edilmeli')
ok(tedarik_kapisi(dict(_m0, sha256='h2'), 'h1', '2.5.0') is False and tedarik_kapisi(dict(_m0, kaynak='uzak'), 'h1', '2.5.0') is False and tedarik_kapisi(dict(_m0, bicim='pickle'), 'h1', '2.5.0') is False and tedarik_kapisi(dict(_m0, torch='2.4.0'), 'h1', '2.5.0') is False and tedarik_kapisi({}, 'h1', '2.5.0') is False, 'tedarik_kapisi her dört katmanı ayrı ayrı zorunlu tutmalı')
with tempfile.TemporaryDirectory(prefix='pafta-g25-') as tmp:
    root=Path(tmp); config=root/'girdi.json'
    # Hidden inputs independent of the editable student sample.
    sonuclar=[]
    for seed in (7100+25,9200+25):
        config.write_text(json.dumps(dict(seed=seed,adim=45)),encoding='utf-8')
        r=deney.deney(tedarik_kapisi,config,root/str(seed))
        for ad,deger in r['kontroller'].items(): ok(deger,'GERCEK 25: '+ad)
        sonuclar.append(r)
    kabul=all(all(r['kontroller'].values()) for r in sonuclar)
    ai_lab.kanit_yaz('guvence-25-kabul',dict(kaynak='gercek',kabul=kabul,deneyler=sonuclar,ortam=sonuclar[0]['ortam'],temizlik='Gorev temp dosyalari kapsam sonunda temizlenir; JSON kaniti kalicidir.'))
```

```solution
import ai_lab

def tedarik_kapisi(manifest, gercek_hash, sabit_surum):
    return (manifest.get('sha256')==gercek_hash and manifest.get('kaynak')=='yerel-sentetik' and manifest.get('bicim')=='safetensors' and manifest.get('torch')==sabit_surum)

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_25 as deney
    deney.goster(tedarik_kapisi)
```

```hint
Gerçek çıktıları ölç; tek seed veya görünür örneği ezberleme. Kabul deneyin ve ölçümün doğru yürütülmesidir.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Tek kontrolle tedarik güvenliği olmaz (30 sn).** "`SHA-256` özeti doğru olan bir `pickle` dosyası hâlâ kod çalıştırabilir; güvenli biçimdeki (`safetensors`) bir model de yanlış çalışma zamanı sürümü veya yetkisiz kaynaktan geldiyse tedarik politikasını deler."
2. **Çok katmanlı tedarik kapısı (35 sn).** "Model yayına alınmadan önce kriptografik özet (`sha256`), izinli kaynak kaydı, güvenli serileştirme biçimi (`safetensors`), sabitlenmiş kütüphane sürümü ve çalışma yalıtımı birlikte doğrulanır."
3. **Yerel politika ile kriptografik imza farkı (30 sn).** "Manifest içindeki `kaynak` alanını okumak yerel politika kapısıdır; manifestin kendisi kriptografik olarak imzalanmadıkça (`Sigstore` / `in-toto`) tek başına kaynak kimliğini kanıtlamaz."
4. **Soru (25 sn).** "Açık ağırlıklı bir modeli kurumsal iç depoya (`mirror`) alırken indirme anı ile çıkarım sunucusuna yükleme anı arasına hangi doğrulama adımlarını koyarsın?"
:::
