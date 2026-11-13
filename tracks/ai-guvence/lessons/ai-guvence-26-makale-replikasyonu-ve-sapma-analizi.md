---
id: ai-guvence-26
title: Makale Replikasyonu ve Sapma Analizi
summary: Referans ve replikasyon ölçümlerini karşılaştır; sonuç sapmasını veri, hiperparametre, kod sürümü ve örnek sayısı farklarıyla birlikte analiz et.
esleme: ai-guvence-01, ai-guvence-05, ai-guvence-35
timeout: 45
---

::: anlat Replikasyon yalnız son puanı yeniden üretmek değildir
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Bir replikasyon aynı yöntem, veri, ayar ve kod koşullarındaki ölçümleri karşılaştırır | Görevler 1–3 açılabilir sentetik JSON kayıtları; son görevde gerçek PyTorch eğitimi ve autograd FGSM ile aynı ayarlı iki kol ve yalnız learning rate değişen üçüncü kol | Küçük sentetik FGSM uygulaması, kaynak makaledeki MNIST/maxout deneyinin veya skorlarının birebir tekrarı değildir |

> [!NOT]
> `veri/replikasyon_kayitlari.json` ve `veri/esikler.json` elle hazırlanmış sentetik öğretim verisidir. Setup her çalıştırmada bunları geçici çalışma dizinine yeniden kopyalar; kalıcılık yoktur. Başlangıç kodundaki okuma satırları ham kayıtları görmeni sağlar. Aynı çalıştırmada bellekte bir kopyayı değiştirebilirsin. Gerçek deneyin `PAFTA_DATA/calisma/ai-guvence-26/ayar.json` dosyası ayrıdır ve kalıcıdır; varsa üzerine yazılmaz. Kontrol örnek dosyalarından bağımsız girdiler kullanır.

Bir makaledeki deneyi yeniden üretirken veri sürümü, rastgele tohum, hiperparametreler, kod sürümü ve örnek sayısı kaydedilir. Başarı oranındaki farkı doğru yorumlamak için referans ve replikasyon kayıtlarının hangi alanlarda ayrıştığını bilmek gerekir.

Görevler 1–3 sentetik kayıtlarla çalışır; son adım yerel PyTorch modeli eğitir ve gerçek autograd FGSM ölçümü üretir. ART, MLflow ve JupyterLab bu deneyin yürütücüsü değildir. Referans ve replikasyon kolları aynı deney kimliğiyle eşleştirilir; oran farkı ve değişen alanlar birlikte raporlanır.
:::

::: anlat Sapma tek bir nedene otomatik bağlanamaz
Değişen alan yoksa iki ölçüm doğrudan karşılaştırılabilir. Veri, tohum, learning rate, kod sürümü veya toplam örnek sayısı değişmişse gözlenen sapmayı tek bir faktöre bağlamak için ek kontrollü deneyler gerekir.

Sapma eşiği yalnız farkın büyüklüğünü işaretler. Tam eşikteki fark eşiği aşmış sayılmaz. Değişen alanların bulunması da sapmanın nedenini kanıtlamaz; yalnız faktörlerin ayrıştırılması gerektiğini gösterir.
:::

::: anlat Dosyadan kontrollü yöntem replikasyonuna
Bir makale sonucunu yeniden üretirken ilk sorunun hangi iddiayı sınadığın olmalıdır. Bir yöntemin formülünü kendi kodunda uygulamak, aynı veri kümesi ve mimariyle aynı sonuç tablosunu elde etmekten daha dar bir hedeftir. Bu dersin canlı kısmı FGSM yöntemini küçük sentetik sınıflandırıcıda yeniden uygular; makalenin bütün deney düzenini yeniden kurmaz. Dolayısıyla raporda yöntem replikasyonu ifadesini kullanırız. Makale skoruyla küçük modelin skorunu doğrudan karşılaştırıp başarı veya başarısızlık ilan etmek farklı sistemleri aynı ölçüm gibi sunar. Kapsamın sınırını açık yazmak deneyin değerini azaltmaz, hangi sonucun desteklendiğini anlaşılır kılar.

İlk üç görevde dosyadan başlayacaksın. `veri/replikasyon_kayitlari.json` içindeki her satır bir kimlik ve kol taşır; aynı kimliğin referans ve replikasyon satırları eşleşir. Önce ham JSON'u yazdır, hangi alanların aynı kaldığını işaretle. Sayısal başarı adedi tek başına yeterli değildir: seksen başarı yüz örnekte farklı, bin örnekte farklı orandır. Başarı sayısının toplamı aşması, toplamın sıfır olması ve iki referans kolunun aynı kimliğe yazılması geçersiz kayıt üretir. Tür denetiminde bool değerlerini kabul etmemek ve sonlu olmayan öğrenme oranlarını reddetmek rapor hattına sessizce bozuk veri girmesini önler.

İkinci görev aynı dosyadan kolları eşleştirir ve replikasyon eksi referans oranını hesaplar. İşaret yönünü ters çevirmek, bir iyileşmeyi düşüş gibi gösterebilir. Değişen alanları tarifteki sabit sırayla yaz; dosya sırasının veya sözlük dolaşımının bilimsel önem taşıdığı varsayımını yapma. Sonuçların farklı olması tek başına kod hatasını göstermez. Veri sürümü, seed, örnek sayısı ve learning rate aynı anda değişmişse hangi faktörün etkili olduğunu bu karşılaştırmadan ayıramazsın. Üçüncü görevde eşik dosyası yalnız farkın büyüklüğünü işaretler. Tam eşikte sapma alarmı yoktur; karar ham mutlak farkla verilir, yuvarlanmış görünümle değil.

Canlı görevde PyTorch modeli gerçekten eğitilir. Adam, eğitim bölümündeki çapraz entropi kaybının ağırlık türevlerini kullanır. FGSM ise ağırlıkları güncellemez; değerlendirilen girdinin türevini hesaplar. Girdinin bağımsız bir kopyasında requires_grad açılır, autograd ile giriş gradyanı alınır ve epsilon çarpı gradyanın işareti girdiye eklenir. Sonra değerler izinli sıfır-bir aralığına kırpılır. Girdiyi yerinde değiştirmek temiz karşılaştırmayı bozabilir; gradyanı ters işaretle kullanmak veya kırpmayı kaldırmak tarif edilen yöntemi değiştirir. Burada temiz ve bozulmuş örneklerin tahminleri aynı model üzerinden ayrı ölçülür.

Her seed için önce aynı ayarlı referans ve replikasyon eğitimi çalışır; üçüncü kolda yalnız learning rate farklıdır. Ağırlık hash'i ve ham logitler sonuçların hangi modelden geldiğini izlemeyi sağlar. Aynı seed tek başına bütün donanım ve kütüphane sürümlerinde bit düzeyinde eşitlik garantisi değildir; bu dersin CPU koşullarında tekrar denetlenir. Üçüncü kolun doğruluğu mutlaka düşmek zorunda değildir. Amaç saldırının kazanmasını sağlamak değil, tanımlı yöntemi doğru yürütmek ve ölçüm farkını doğru raporlamaktır.

Saldırgan veya kötü hazırlanmış bir değerlendirme raporu yalnız başarılı seed'i seçebilir, başarısız koşuları saklayabilir ya da değişen veri sürümünü belirtmeyebilir. Savunma raporu yalnız son puanı doğrularsa bu seçiciliği kaçırır. Ham sayımlar, toplamlar ve ayarlar birlikte saklanmalı; nedensel yorum için başka faktörler sabit tutularak yeni deney yapılmalıdır. Çalıştır kendi kalıcı ayar kopyanı kullanır, Kontrol ise ayrı tohumla sınar. Görünür dosyayı değiştirip beklenen cevabı değiştiremezsin. Son kanıtı okurken kapsam, veri kökeni ve yöntem sapmasını sonuç puanıyla birlikte değerlendir; tek küçük deneyi genel dayanıklılık sertifikası sayma.
:::

::: tahmin Replikasyon farkını ve sınırı tahmin et
Üç çıktı satırını yaz:

```python
print(round(2 / 3 - 1 / 3, 6))
print(abs(0.25 - 0.5) > 0.25)
print([alan for alan in ("veri", "tohum", "kod_surumu") if alan in {"tohum", "kod_surumu"}])
```

???

```cikti
0.333333
False
['tohum', 'kod_surumu']
```

İlk satır replikasyon eksi referans farkını, ikinci satır tam eşiğin aşılmadığını, üçüncü satır değişen alan sırasını gösterir.
:::

::: gorev 1 · Replikasyon ölçüm kaydını doğrula
`replikasyon_olcum_dogrula(kayit)` işlevini yaz. Kayıt tam olarak `id`, `kol`, `veri`, `tohum`, `ogrenme_orani`, `kod_surumu`, `basari`, `toplam` alanlarını taşır. Kimlik 1–64 karakterlik, ASCII harf/rakamla başlayan ve yalnız ASCII harf, rakam, alt çizgi veya tire içeren stringdir.

Kol yalnız `referans` veya `replikasyon`; veri ve kod sürümü 1–64 karakterlik stringdir. Tohum bool olmayan, 0–1000000 arasında tam sayıdır. learning rate bool olmayan, sonlu, 0'dan büyük ve en fazla 1 olan `int` veya `float` olur. Toplam bool olmayan, 1–10000 arasında tam sayı; başarı bool olmayan, 0 ile toplam arasında tam sayıdır. Geçersiz veride `ValueError` yükselt. Bağımsız sözlük kopyası döndür ve girdiyi değiştirme.

```starter
def replikasyon_olcum_dogrula(kayit):
    # KUSURLU BAŞLANGIÇ KODU: şema ve sayım sınırlarını denetlemeden kaydı kopyalıyor.
    return dict(kayit)

from ai_guvence_veri import json_yukle
for kayit in json_yukle("veri/replikasyon_kayitlari.json"):
    print(replikasyon_olcum_dogrula(kayit))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-26")
```

```test
import copy
K = {"id": "deney-1", "kol": "referans", "veri": "v1", "tohum": 7, "ogrenme_orani": 0.1, "kod_surumu": "a", "basari": 80, "toplam": 100}
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        if fn(K) != K or fn(K) is K or K != once:
            return False
        sinir = dict(K, id="a" * 64, kol="replikasyon", veri="v" * 64, tohum=1000000, ogrenme_orani=1, kod_surumu="k" * 64, basari=10000, toplam=10000)
        alt = dict(K, tohum=0, ogrenme_orani=0.000001, basari=0, toplam=1)
        if fn(sinir) != sinir or fn(alt) != alt or fn(dict(K, veri="v"))["veri"] != "v":
            return False
        for kayit in [
            None, [], dict(K, ek=1), dict(K, id=""), dict(K, id="a b"), dict(K, id="a" * 65), dict(K, id=None),
            dict(K, kol="diger"), dict(K, kol=None), dict(K, kol=1),
            dict(K, veri=""), dict(K, veri="v" * 65), dict(K, veri=None), dict(K, veri=1),
            dict(K, tohum=-1), dict(K, tohum=1000001), dict(K, tohum=1.5), dict(K, tohum=True), dict(K, tohum=None),
            dict(K, ogrenme_orani=0), dict(K, ogrenme_orani=-0.1), dict(K, ogrenme_orani=1.1), dict(K, ogrenme_orani=float("nan")), dict(K, ogrenme_orani=float("inf")), dict(K, ogrenme_orani=True), dict(K, ogrenme_orani=None),
            dict(K, kod_surumu=""), dict(K, kod_surumu="k" * 65), dict(K, kod_surumu=None), dict(K, kod_surumu=1),
            dict(K, basari=-1), dict(K, basari=101), dict(K, basari=1.5), dict(K, basari=True), dict(K, basari=None),
            dict(K, basari=0, toplam=0), dict(K, toplam=10001), dict(K, toplam=100.0), dict(K, basari=0, toplam=False), dict(K, basari=0, toplam=True), dict(K, toplam=None),
        ]:
            try:
                fn(kayit)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(replikasyon_olcum_dogrula), "deney şeması, hiperparametreler ve sayım sınırları korunmalı")
def m_kol(kayit):
    return replikasyon_olcum_dogrula(dict(kayit, kol="diger"))
def m_tohum(kayit):
    return replikasyon_olcum_dogrula(dict(kayit, tohum=-1))
def m_oran(kayit):
    return replikasyon_olcum_dogrula(dict(kayit, ogrenme_orani=0))
def m_basari(kayit):
    return replikasyon_olcum_dogrula(dict(kayit, basari=101))
for ad, mutant in [("kolu bozan", m_kol), ("tohumu bozan", m_tohum), ("oranı bozan", m_oran), ("başarıyı bozan", m_basari)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def replikasyon_olcum_dogrula(kayit):
    import math
    import re
    if not isinstance(kayit, dict):
        raise ValueError("kayıt sözlük olmalı")
    if set(kayit) != {"id", "kol", "veri", "tohum", "ogrenme_orani", "kod_surumu", "basari", "toplam"}:
        raise ValueError("kayıt şeması geçersiz")
    if not isinstance(kayit["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
        raise ValueError("kimlik geçersiz")
    if kayit["kol"] not in ("referans", "replikasyon"):
        raise ValueError("kol geçersiz")
    if not isinstance(kayit["veri"], str) or not 1 <= len(kayit["veri"]) <= 64:
        raise ValueError("veri geçersiz")
    if not isinstance(kayit["tohum"], int) or isinstance(kayit["tohum"], bool) or not 0 <= kayit["tohum"] <= 1000000:
        raise ValueError("tohum geçersiz")
    oran = kayit["ogrenme_orani"]
    if not isinstance(oran, (int, float)) or isinstance(oran, bool) or not math.isfinite(oran) or not 0 < oran <= 1:
        raise ValueError("öğrenme oranı geçersiz")
    if not isinstance(kayit["kod_surumu"], str) or not 1 <= len(kayit["kod_surumu"]) <= 64:
        raise ValueError("kod sürümü geçersiz")
    if not isinstance(kayit["toplam"], int) or isinstance(kayit["toplam"], bool) or not 1 <= kayit["toplam"] <= 10000:
        raise ValueError("toplam geçersiz")
    if not isinstance(kayit["basari"], int) or isinstance(kayit["basari"], bool) or not 0 <= kayit["basari"] <= kayit["toplam"]:
        raise ValueError("başarı sayısı geçersiz")
    return dict(kayit)

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    for kayit in json_yukle("veri/replikasyon_kayitlari.json"):
        print(replikasyon_olcum_dogrula(kayit))
```

```hint
Metin uzunlukları ile sayısal aralıkları ayrı denetle. Bool değerleri tam sayı veya oran olarak kabul etme; öğrenme oranında alt sınır hariçtir.
```
:::

::: gorev 2 · Referans ve replikasyon farkını açıkla
`replikasyon_fark_raporu(kayitlar)` işlevini yaz. Girdi ilk görevdeki kayıtların boş olmayan listesidir. Her kimlikte bir `referans` ve bir `replikasyon` kaydı bulunmalı; aynı `id`-`kol` çifti yinelenemez. Diğer alanlar farklı olabilir. Geçersiz veride `ValueError` yükselt.

Her kimliğin ilk görüldüğü sırayla `{"id":D,"referans_oran":R,"replikasyon_oran":E,"fark":F,"degisen_alanlar":A}` üret. Oranlar `basari / toplam`, fark ham replikasyon eksi referans oranıdır. Üç alan 6 ondalığa yuvarlanır.

`degisen_alanlar`, iki kol arasında farklı olan alanları şu sabit sırayla içerir: `veri`, `tohum`, `ogrenme_orani`, `kod_surumu`, `toplam`. Alan yoksa boş liste döner. Sonuç `{"satirlar":[...]}` biçimindedir. Girdiyi değiştirme.

```starter
def replikasyon_fark_raporu(kayitlar):
    import math
    import re
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar boş olmayan liste olmalı")
    temiz = []
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"id", "kol", "veri", "tohum", "ogrenme_orani", "kod_surumu", "basari", "toplam"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(kayit["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
            raise ValueError("kimlik geçersiz")
        if kayit["kol"] not in ("referans", "replikasyon"):
            raise ValueError("kol geçersiz")
        if not isinstance(kayit["veri"], str) or not 1 <= len(kayit["veri"]) <= 64:
            raise ValueError("veri geçersiz")
        if not isinstance(kayit["tohum"], int) or isinstance(kayit["tohum"], bool) or not 0 <= kayit["tohum"] <= 1000000:
            raise ValueError("tohum geçersiz")
        oran = kayit["ogrenme_orani"]
        if not isinstance(oran, (int, float)) or isinstance(oran, bool) or not math.isfinite(oran) or not 0 < oran <= 1:
            raise ValueError("öğrenme oranı geçersiz")
        if not isinstance(kayit["kod_surumu"], str) or not 1 <= len(kayit["kod_surumu"]) <= 64:
            raise ValueError("kod sürümü geçersiz")
        if not isinstance(kayit["toplam"], int) or isinstance(kayit["toplam"], bool) or not 1 <= kayit["toplam"] <= 10000:
            raise ValueError("toplam geçersiz")
        if not isinstance(kayit["basari"], int) or isinstance(kayit["basari"], bool) or not 0 <= kayit["basari"] <= kayit["toplam"]:
            raise ValueError("başarı sayısı geçersiz")
        temiz.append(dict(kayit))
    gruplar = {}
    gorulen = set()
    for kayit in temiz:
        cift = (kayit["id"], kayit["kol"])
        if cift in gorulen:
            raise ValueError("yinelenen kimlik-kol çifti")
        gorulen.add(cift)
        gruplar.setdefault(kayit["id"], {})[kayit["kol"]] = kayit
    alanlar = ("veri", "tohum", "ogrenme_orani", "kod_surumu", "toplam")
    # KUSURLU BAŞLANGIÇ KODU: rapordaki farkın işaretini ters hesaplıyor.
    satirlar = []
    for kimlik, grup in gruplar.items():
        if set(grup) != {"referans", "replikasyon"}:
            raise ValueError("referans ve replikasyon çifti gerekli")
        ref = grup["referans"]
        rep = grup["replikasyon"]
        ref_oran = ref["basari"] / ref["toplam"]
        rep_oran = rep["basari"] / rep["toplam"]
        satirlar.append({"id": kimlik, "referans_oran": round(ref_oran, 6), "replikasyon_oran": round(rep_oran, 6), "fark": round(ref_oran - rep_oran, 6), "degisen_alanlar": [alan for alan in alanlar if ref[alan] != rep[alan]]})
    return {"satirlar": satirlar}

from ai_guvence_veri import json_yukle
print(replikasyon_fark_raporu(json_yukle("veri/replikasyon_kayitlari.json")))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-26")
```

```test
import copy
K = [
    {"id": "a", "kol": "referans", "veri": "v1", "tohum": 7, "ogrenme_orani": 0.1, "kod_surumu": "a", "basari": 80, "toplam": 100},
    {"id": "a", "kol": "replikasyon", "veri": "v2", "tohum": 7, "ogrenme_orani": 0.01, "kod_surumu": "a", "basari": 60, "toplam": 100},
    {"id": "b", "kol": "replikasyon", "veri": "v1", "tohum": 7, "ogrenme_orani": 0.1, "kod_surumu": "b", "basari": 75, "toplam": 100},
    {"id": "b", "kol": "referans", "veri": "v1", "tohum": 7, "ogrenme_orani": 0.1, "kod_surumu": "a", "basari": 50, "toplam": 100},
    {"id": "c", "kol": "referans", "veri": "v1", "tohum": 7, "ogrenme_orani": 0.1, "kod_surumu": "a", "basari": 70, "toplam": 100},
    {"id": "c", "kol": "replikasyon", "veri": "v1", "tohum": 7, "ogrenme_orani": 0.1, "kod_surumu": "a", "basari": 70, "toplam": 100},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        sonuc = fn(K)
        if K != once or sonuc["satirlar"] != [
            {"id": "a", "referans_oran": 0.8, "replikasyon_oran": 0.6, "fark": -0.2, "degisen_alanlar": ["veri", "ogrenme_orani"]},
            {"id": "b", "referans_oran": 0.5, "replikasyon_oran": 0.75, "fark": 0.25, "degisen_alanlar": ["kod_surumu"]},
            {"id": "c", "referans_oran": 0.7, "replikasyon_oran": 0.7, "fark": 0.0, "degisen_alanlar": []},
        ]:
            return False
        uc = [dict(K[0], id="a" * 64, basari=1, toplam=3), dict(K[1], id="a" * 64, veri="v1", ogrenme_orani=0.1, tohum=8, kod_surumu="z", basari=2, toplam=3)]
        if fn(uc)["satirlar"][0] != {"id": "a" * 64, "referans_oran": 0.333333, "replikasyon_oran": 0.666667, "fark": 0.333333, "degisen_alanlar": ["tohum", "kod_surumu"]}:
            return False
        alt = [dict(K[0], tohum=0, ogrenme_orani=0.000001, basari=0, toplam=1), dict(K[1], tohum=0, ogrenme_orani=0.000001, basari=0, toplam=1)]
        ust = [dict(K[0], tohum=1000000, ogrenme_orani=1, basari=10000, toplam=10000), dict(K[1], tohum=1000000, ogrenme_orani=1, basari=10000, toplam=10000)]
        if fn(alt)["satirlar"][0]["fark"] != 0.0 or fn(ust)["satirlar"][0]["replikasyon_oran"] != 1.0:
            return False
        def ayni_cift(**degisiklik):
            return [dict(K[0], **degisiklik), dict(K[1], **degisiklik)]
        if fn(ayni_cift(veri="v", kod_surumu="k"))["satirlar"][0]["degisen_alanlar"] != ["ogrenme_orani"]:
            return False
        if fn(ayni_cift(veri="v" * 64, kod_surumu="k" * 64))["satirlar"][0]["degisen_alanlar"] != ["ogrenme_orani"]:
            return False
        for kayitlar in [
            None, {}, tuple(K), [], [None], [dict(K[0], ek=1)] + K[1:], ayni_cift(id="a" * 65), ayni_cift(id=None),
            [dict(K[0], kol=[])] + K, ayni_cift(veri=""), ayni_cift(veri="v" * 65), ayni_cift(veri=None),
            ayni_cift(tohum=-1), ayni_cift(tohum=1000001), ayni_cift(tohum=1.5), ayni_cift(tohum=True),
            ayni_cift(ogrenme_orani=0), ayni_cift(ogrenme_orani=1.1), ayni_cift(ogrenme_orani=float("nan")), ayni_cift(ogrenme_orani=True), ayni_cift(ogrenme_orani="0.1"),
            ayni_cift(kod_surumu=""), ayni_cift(kod_surumu="k" * 65), ayni_cift(kod_surumu=None),
            ayni_cift(basari=-1), ayni_cift(basari=101), ayni_cift(basari=1.5), ayni_cift(basari=True),
            ayni_cift(basari=0, toplam=0), ayni_cift(toplam=10001), ayni_cift(toplam=100.0), ayni_cift(basari=0, toplam=True),
            [K[0]], [K[1]], [K[0], K[0], K[1]],
        ]:
            try:
                fn(kayitlar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(replikasyon_fark_raporu), "eşleştirme, oran farkı ve değişen alan sırası korunmalı")
def m_basari(kayitlar):
    return replikasyon_fark_raporu([dict(x, basari=0) for x in kayitlar])
def m_kol(kayitlar):
    return replikasyon_fark_raporu([dict(x, kol="referans") for x in kayitlar])
def m_veri(kayitlar):
    return replikasyon_fark_raporu([dict(x, veri="v1") for x in kayitlar])
def m_sil(kayitlar):
    return replikasyon_fark_raporu(kayitlar[:2])
for ad, mutant in [("başarıları silen", m_basari), ("kolları silen", m_kol), ("veri farkını silen", m_veri), ("kayıtları silen", m_sil)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def replikasyon_fark_raporu(kayitlar):
    import math
    import re
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar boş olmayan liste olmalı")
    temiz = []
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"id", "kol", "veri", "tohum", "ogrenme_orani", "kod_surumu", "basari", "toplam"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(kayit["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
            raise ValueError("kimlik geçersiz")
        if kayit["kol"] not in ("referans", "replikasyon"):
            raise ValueError("kol geçersiz")
        if not isinstance(kayit["veri"], str) or not 1 <= len(kayit["veri"]) <= 64:
            raise ValueError("veri geçersiz")
        if not isinstance(kayit["tohum"], int) or isinstance(kayit["tohum"], bool) or not 0 <= kayit["tohum"] <= 1000000:
            raise ValueError("tohum geçersiz")
        oran = kayit["ogrenme_orani"]
        if not isinstance(oran, (int, float)) or isinstance(oran, bool) or not math.isfinite(oran) or not 0 < oran <= 1:
            raise ValueError("öğrenme oranı geçersiz")
        if not isinstance(kayit["kod_surumu"], str) or not 1 <= len(kayit["kod_surumu"]) <= 64:
            raise ValueError("kod sürümü geçersiz")
        if not isinstance(kayit["toplam"], int) or isinstance(kayit["toplam"], bool) or not 1 <= kayit["toplam"] <= 10000:
            raise ValueError("toplam geçersiz")
        if not isinstance(kayit["basari"], int) or isinstance(kayit["basari"], bool) or not 0 <= kayit["basari"] <= kayit["toplam"]:
            raise ValueError("başarı sayısı geçersiz")
        temiz.append(dict(kayit))
    gruplar = {}
    gorulen = set()
    for kayit in temiz:
        cift = (kayit["id"], kayit["kol"])
        if cift in gorulen:
            raise ValueError("yinelenen kimlik-kol çifti")
        gorulen.add(cift)
        gruplar.setdefault(kayit["id"], {})[kayit["kol"]] = kayit
    alanlar = ("veri", "tohum", "ogrenme_orani", "kod_surumu", "toplam")
    satirlar = []
    for kimlik, grup in gruplar.items():
        if set(grup) != {"referans", "replikasyon"}:
            raise ValueError("referans ve replikasyon çifti gerekli")
        ref = grup["referans"]
        rep = grup["replikasyon"]
        ref_oran = ref["basari"] / ref["toplam"]
        rep_oran = rep["basari"] / rep["toplam"]
        satirlar.append({"id": kimlik, "referans_oran": round(ref_oran, 6), "replikasyon_oran": round(rep_oran, 6), "fark": round(rep_oran - ref_oran, 6), "degisen_alanlar": [alan for alan in alanlar if ref[alan] != rep[alan]]})
    return {"satirlar": satirlar}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    print(replikasyon_fark_raporu(json_yukle("veri/replikasyon_kayitlari.json")))
```

```hint
Alan adlarını sabit bir sırayla gez ve iki koldaki değerlerini karşılaştır. Oran farkını her zaman replikasyon eksi referans olarak hesapla.
```
:::

::: gorev 3 · Sapma büyüklüğü ve karışan faktörleri raporla
`replikasyon_sapma_raporu(kayitlar, sapma_esigi)` işlevini yaz. Kayıtlar ikinci görevdeki kurallara uyar. Eşik bool olmayan, sonlu, 0–1 aralığında `int` veya `float` olmalıdır; geçersiz veride `ValueError` yükselt.

Her kimlik için ikinci görevdeki alanlara ek olarak `sapma` ve `analiz` içeren satır üret: `{"id":D,"referans_oran":R,"replikasyon_oran":E,"fark":F,"degisen_alanlar":A,"sapma":S,"analiz":N}`. Ham farkın mutlak değeri eşikten büyükse sapma doğrudur; tam eşitte yanlıştır.

Değişen alan yoksa analiz `alanlar_kontrollu`, en az bir değişen alan varsa `faktorler_ayristirilmali` olur. `{"satirlar":[...],"sapma_sayisi":N,"not":"sapma_tek_nedene_baglanamaz"}` döndür. Kimlik sırasını koru ve girdiyi değiştirme.

```starter
def replikasyon_sapma_raporu(kayitlar, sapma_esigi):
    import math
    import re
    if not isinstance(sapma_esigi, (int, float)) or isinstance(sapma_esigi, bool) or not math.isfinite(sapma_esigi) or not 0 <= sapma_esigi <= 1:
        raise ValueError("eşik sonlu ve izinli aralıkta olmalı")
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar boş olmayan liste olmalı")
    temiz = []
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"id", "kol", "veri", "tohum", "ogrenme_orani", "kod_surumu", "basari", "toplam"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(kayit["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
            raise ValueError("kimlik geçersiz")
        if kayit["kol"] not in ("referans", "replikasyon"):
            raise ValueError("kol geçersiz")
        if not isinstance(kayit["veri"], str) or not 1 <= len(kayit["veri"]) <= 64:
            raise ValueError("veri geçersiz")
        if not isinstance(kayit["tohum"], int) or isinstance(kayit["tohum"], bool) or not 0 <= kayit["tohum"] <= 1000000:
            raise ValueError("tohum geçersiz")
        oran = kayit["ogrenme_orani"]
        if not isinstance(oran, (int, float)) or isinstance(oran, bool) or not math.isfinite(oran) or not 0 < oran <= 1:
            raise ValueError("öğrenme oranı geçersiz")
        if not isinstance(kayit["kod_surumu"], str) or not 1 <= len(kayit["kod_surumu"]) <= 64:
            raise ValueError("kod sürümü geçersiz")
        if not isinstance(kayit["toplam"], int) or isinstance(kayit["toplam"], bool) or not 1 <= kayit["toplam"] <= 10000:
            raise ValueError("toplam geçersiz")
        if not isinstance(kayit["basari"], int) or isinstance(kayit["basari"], bool) or not 0 <= kayit["basari"] <= kayit["toplam"]:
            raise ValueError("başarı sayısı geçersiz")
        temiz.append(dict(kayit))
    gruplar = {}
    gorulen = set()
    for kayit in temiz:
        cift = (kayit["id"], kayit["kol"])
        if cift in gorulen:
            raise ValueError("yinelenen kimlik-kol çifti")
        gorulen.add(cift)
        gruplar.setdefault(kayit["id"], {})[kayit["kol"]] = kayit
    alanlar = ("veri", "tohum", "ogrenme_orani", "kod_surumu", "toplam")
    # KUSURLU BAŞLANGIÇ KODU: tam eşikte de sapma alarmı veriyor.
    satirlar = []
    for kimlik, grup in gruplar.items():
        if set(grup) != {"referans", "replikasyon"}:
            raise ValueError("referans ve replikasyon çifti gerekli")
        ref = grup["referans"]
        rep = grup["replikasyon"]
        ref_oran = ref["basari"] / ref["toplam"]
        rep_oran = rep["basari"] / rep["toplam"]
        fark = rep_oran - ref_oran
        degisen = [alan for alan in alanlar if ref[alan] != rep[alan]]
        satirlar.append({"id": kimlik, "referans_oran": round(ref_oran, 6), "replikasyon_oran": round(rep_oran, 6), "fark": round(fark, 6), "degisen_alanlar": degisen, "sapma": abs(fark) >= sapma_esigi, "analiz": "faktorler_ayristirilmali" if degisen else "alanlar_kontrollu"})
    return {"satirlar": satirlar, "sapma_sayisi": sum(1 for x in satirlar if x["sapma"]), "not": "sapma_tek_nedene_baglanamaz"}

from ai_guvence_veri import json_yukle
esikler = json_yukle("veri/esikler.json")
print(replikasyon_sapma_raporu(json_yukle("veri/replikasyon_kayitlari.json"), **esikler))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-26")
```

```test
import copy
K = [
    {"id": "a", "kol": "referans", "veri": "v1", "tohum": 7, "ogrenme_orani": 0.1, "kod_surumu": "a", "basari": 80, "toplam": 100},
    {"id": "a", "kol": "replikasyon", "veri": "v2", "tohum": 7, "ogrenme_orani": 0.01, "kod_surumu": "a", "basari": 60, "toplam": 100},
    {"id": "b", "kol": "replikasyon", "veri": "v1", "tohum": 7, "ogrenme_orani": 0.1, "kod_surumu": "b", "basari": 75, "toplam": 100},
    {"id": "b", "kol": "referans", "veri": "v1", "tohum": 7, "ogrenme_orani": 0.1, "kod_surumu": "a", "basari": 50, "toplam": 100},
    {"id": "c", "kol": "referans", "veri": "v1", "tohum": 7, "ogrenme_orani": 0.1, "kod_surumu": "a", "basari": 70, "toplam": 100},
    {"id": "c", "kol": "replikasyon", "veri": "v1", "tohum": 7, "ogrenme_orani": 0.1, "kod_surumu": "a", "basari": 70, "toplam": 100},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        sonuc = fn(K, 0.25)
        if K != once or sonuc["sapma_sayisi"] != 0 or sonuc["not"] != "sapma_tek_nedene_baglanamaz":
            return False
        if sonuc["satirlar"] != [
            {"id": "a", "referans_oran": 0.8, "replikasyon_oran": 0.6, "fark": -0.2, "degisen_alanlar": ["veri", "ogrenme_orani"], "sapma": False, "analiz": "faktorler_ayristirilmali"},
            {"id": "b", "referans_oran": 0.5, "replikasyon_oran": 0.75, "fark": 0.25, "degisen_alanlar": ["kod_surumu"], "sapma": False, "analiz": "faktorler_ayristirilmali"},
            {"id": "c", "referans_oran": 0.7, "replikasyon_oran": 0.7, "fark": 0.0, "degisen_alanlar": [], "sapma": False, "analiz": "alanlar_kontrollu"},
        ]:
            return False
        buyuk = fn(K, 0.1)
        if buyuk["sapma_sayisi"] != 2 or [x["sapma"] for x in buyuk["satirlar"]] != [True, True, False]:
            return False
        uc = [dict(K[0], id="a" * 64, basari=1, toplam=3), dict(K[1], id="a" * 64, veri="v1", ogrenme_orani=0.1, tohum=8, kod_surumu="z", basari=2, toplam=3)]
        uc_sonuc = fn(uc, 0.25)["satirlar"][0]
        if uc_sonuc["referans_oran"] != 0.333333 or uc_sonuc["replikasyon_oran"] != 0.666667 or uc_sonuc["fark"] != 0.333333 or not uc_sonuc["sapma"]:
            return False
        alt = [dict(K[0], tohum=0, ogrenme_orani=0.000001, basari=0, toplam=1), dict(K[1], tohum=0, ogrenme_orani=0.000001, basari=0, toplam=1)]
        ust = [dict(K[0], tohum=1000000, ogrenme_orani=1, basari=0, toplam=10000), dict(K[1], tohum=1000000, ogrenme_orani=1, basari=10000, toplam=10000)]
        if fn(alt, 0)["satirlar"][0]["sapma"] or fn(ust, 1)["satirlar"][0]["sapma"]:
            return False
        def ayni_cift(**degisiklik):
            return [dict(K[0], **degisiklik), dict(K[1], **degisiklik)]
        if fn(ayni_cift(veri="v", kod_surumu="k"), 0.1)["satirlar"][0]["degisen_alanlar"] != ["ogrenme_orani"]:
            return False
        if fn(ayni_cift(veri="v" * 64, kod_surumu="k" * 64), 0.1)["satirlar"][0]["degisen_alanlar"] != ["ogrenme_orani"]:
            return False
        for args in [
            (None, 0.1), (tuple(K), 0.1), ([], 0.1), ([None], 0.1), ([dict(K[0], ek=1)] + K[1:], 0.1),
            (ayni_cift(id="a" * 65), 0.1), (ayni_cift(id=None), 0.1), ([dict(K[0], kol=[])] + K, 0.1),
            (ayni_cift(veri=""), 0.1), (ayni_cift(veri="v" * 65), 0.1), (ayni_cift(veri=None), 0.1),
            (ayni_cift(tohum=-1), 0.1), (ayni_cift(tohum=1000001), 0.1), (ayni_cift(tohum=1.5), 0.1), (ayni_cift(tohum=True), 0.1),
            (ayni_cift(ogrenme_orani=0), 0.1), (ayni_cift(ogrenme_orani=1.1), 0.1), (ayni_cift(ogrenme_orani=float("nan")), 0.1), (ayni_cift(ogrenme_orani=True), 0.1), (ayni_cift(ogrenme_orani="0.1"), 0.1),
            (ayni_cift(kod_surumu=""), 0.1), (ayni_cift(kod_surumu="k" * 65), 0.1), (ayni_cift(kod_surumu=None), 0.1),
            (ayni_cift(basari=-1), 0.1), (ayni_cift(basari=101), 0.1), (ayni_cift(basari=1.5), 0.1), (ayni_cift(basari=True), 0.1),
            (ayni_cift(basari=0, toplam=0), 0.1), (ayni_cift(toplam=10001), 0.1), (ayni_cift(toplam=100.0), 0.1), (ayni_cift(basari=0, toplam=True), 0.1),
            ([K[0]], 0.1), ([K[1]], 0.1), ([K[0], K[0], K[1]], 0.1),
            (K, -0.1), (K, 1.1), (K, float("nan")), (K, float("inf")), (K, True), (K, None),
        ]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(replikasyon_sapma_raporu), "sapma eşiği, analiz sınıfı ve karışan faktörler korunmalı")
def m_basari(kayitlar, sapma_esigi):
    return replikasyon_sapma_raporu([dict(x, basari=0) for x in kayitlar], sapma_esigi)
def m_veri(kayitlar, sapma_esigi):
    return replikasyon_sapma_raporu([dict(x, veri="v1") for x in kayitlar], sapma_esigi)
def m_esik(kayitlar, sapma_esigi):
    return replikasyon_sapma_raporu(kayitlar, 1)
def m_sil(kayitlar, sapma_esigi):
    return replikasyon_sapma_raporu(kayitlar[:2], sapma_esigi)
for ad, mutant in [("başarıları silen", m_basari), ("veri farkını silen", m_veri), ("eşiği silen", m_esik), ("kayıtları silen", m_sil)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def replikasyon_sapma_raporu(kayitlar, sapma_esigi):
    import math
    import re
    if not isinstance(sapma_esigi, (int, float)) or isinstance(sapma_esigi, bool) or not math.isfinite(sapma_esigi) or not 0 <= sapma_esigi <= 1:
        raise ValueError("eşik sonlu ve izinli aralıkta olmalı")
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar boş olmayan liste olmalı")
    temiz = []
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"id", "kol", "veri", "tohum", "ogrenme_orani", "kod_surumu", "basari", "toplam"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(kayit["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
            raise ValueError("kimlik geçersiz")
        if kayit["kol"] not in ("referans", "replikasyon"):
            raise ValueError("kol geçersiz")
        if not isinstance(kayit["veri"], str) or not 1 <= len(kayit["veri"]) <= 64:
            raise ValueError("veri geçersiz")
        if not isinstance(kayit["tohum"], int) or isinstance(kayit["tohum"], bool) or not 0 <= kayit["tohum"] <= 1000000:
            raise ValueError("tohum geçersiz")
        oran = kayit["ogrenme_orani"]
        if not isinstance(oran, (int, float)) or isinstance(oran, bool) or not math.isfinite(oran) or not 0 < oran <= 1:
            raise ValueError("öğrenme oranı geçersiz")
        if not isinstance(kayit["kod_surumu"], str) or not 1 <= len(kayit["kod_surumu"]) <= 64:
            raise ValueError("kod sürümü geçersiz")
        if not isinstance(kayit["toplam"], int) or isinstance(kayit["toplam"], bool) or not 1 <= kayit["toplam"] <= 10000:
            raise ValueError("toplam geçersiz")
        if not isinstance(kayit["basari"], int) or isinstance(kayit["basari"], bool) or not 0 <= kayit["basari"] <= kayit["toplam"]:
            raise ValueError("başarı sayısı geçersiz")
        temiz.append(dict(kayit))
    gruplar = {}
    gorulen = set()
    for kayit in temiz:
        cift = (kayit["id"], kayit["kol"])
        if cift in gorulen:
            raise ValueError("yinelenen kimlik-kol çifti")
        gorulen.add(cift)
        gruplar.setdefault(kayit["id"], {})[kayit["kol"]] = kayit
    alanlar = ("veri", "tohum", "ogrenme_orani", "kod_surumu", "toplam")
    satirlar = []
    for kimlik, grup in gruplar.items():
        if set(grup) != {"referans", "replikasyon"}:
            raise ValueError("referans ve replikasyon çifti gerekli")
        ref = grup["referans"]
        rep = grup["replikasyon"]
        ref_oran = ref["basari"] / ref["toplam"]
        rep_oran = rep["basari"] / rep["toplam"]
        fark = rep_oran - ref_oran
        degisen = [alan for alan in alanlar if ref[alan] != rep[alan]]
        satirlar.append({"id": kimlik, "referans_oran": round(ref_oran, 6), "replikasyon_oran": round(rep_oran, 6), "fark": round(fark, 6), "degisen_alanlar": degisen, "sapma": abs(fark) > sapma_esigi, "analiz": "faktorler_ayristirilmali" if degisen else "alanlar_kontrollu"})
    return {"satirlar": satirlar, "sapma_sayisi": sum(1 for x in satirlar if x["sapma"]), "not": "sapma_tek_nedene_baglanamaz"}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    esikler = json_yukle("veri/esikler.json")
    print(replikasyon_sapma_raporu(json_yukle("veri/replikasyon_kayitlari.json"), **esikler))
```

```hint
Sapmayı ham farkın mutlak değeriyle ve sıkı büyüktür koşuluyla hesapla. Analiz sınıfını sapmadan bağımsız olarak değişen alan listesine bağla.
```
:::


::: anlat Gerçek deney · FGSM yöntem replikasyonu
Önce görünür sentetik [ayar dosyasını](/data/ai-guvence-26-deney.txt) incele: /data/ai-guvence-26-deney.txt. Bu bir sunucu kaydı değildir. Çalıştır ilk kullanımda ayrı kalıcı kopya oluşturur ve gerçek yol/içeriğini gösterir. Yerleşik dosya editörü yoktur; yolu yerel editörde aç, seed veya eps değiştir ve yeniden Çalıştır. Kopya varsa üzerine yazılmaz. Göreli PAFTA_DATA proje köküne göre çözülür; geçici koşucu klasörüne göre değil. Kontrol ayrı görülmemiş ayarı kullanır; öğrenci dosyasını değiştirmek beklenen cevabı değiştirmez.

fgsm_replika(model,x,y,eps): autograd cross entropy giriş gradyanı; x+eps*sign(grad), [0,1] kırpma. replika_ozeti(rows): seed artan sırada, sonra verilen kol sırası; temiz/bozuk oranları ve referansa göre bozuk doğruluk farkını 6 basamakla raporla. `lr` farklıysa `degisen=["lr"]`, yoksa `[]`. Dönen liste satırı tam olarak {seed,kol,temiz,bozuk,fark,degisen} anahtarlarını taşır; seed ve kol girdiden, temiz/bozuk sayımdan üretilir. Aynı tohum/ayar ile iki gerçek eğitim ve yalnız lr değişen üçüncü kol çalışır. Kaynak: [Goodfellow vd.2015](https://arxiv.org/abs/1412.6572v3). Bu yalnız FGSM yönteminin sentetik replikasyonudur; makaledeki MNIST/maxout skorunun tekrarı değildir.

CPU .ai-venv torch ile gerçek Adam/autograd eğitimi, ağırlık hash'i, ham logitler ve ölçüm kanıtı yazılır. Model indirilmez, GPU kullanılmaz. Testte geçici ağırlıklar temizlenir; eğitim/logit/hash kanıtta korunur. Çalıştır çıktıları kalıcı öğrenci klasöründe kalır. Eski adımlar yukarıda fixture olarak korunmuştur; bu ek adım canlı deneydir.
:::

::: gorev Gerçek deney · FGSM yöntem replikasyonu
fgsm_replika(model,x,y,eps): autograd cross entropy giriş gradyanı; x+eps*sign(grad), [0,1] kırpma. replika_ozeti(rows): seed artan sırada, sonra verilen kol sırası; temiz/bozuk oranları ve referansa göre bozuk doğruluk farkını 6 basamakla raporla. `lr` farklıysa `degisen=["lr"]`, yoksa `[]`. Dönen liste satırı tam olarak {seed,kol,temiz,bozuk,fark,degisen} anahtarlarını taşır; seed ve kol girdiden, temiz/bozuk sayımdan üretilir. Aynı tohum/ayar ile iki gerçek eğitim ve yalnız lr değişen üçüncü kol çalışır. Kaynak: [Goodfellow vd.2015](https://arxiv.org/abs/1412.6572v3). Bu yalnız FGSM yönteminin sentetik replikasyonudur; makaledeki MNIST/maxout skorunun tekrarı değildir.

```meta
motor: ai-gercek
gereksinim: torch
timeout: 120
```

```starter
def fgsm_replika(*args):
    return None

def replika_ozeti(*args):
    return None

import ai_lab
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_26 as deney
    deney.goster(fgsm_replika,replika_ozeti)
```

```test
import ai_lab
import ast
YASAK = ("attack_ref", "ozet_ref", "kanit_yaz")
sorunlar = ai_lab.kod_denetimi(src, yasak=YASAK)
for dugum in ast.walk(ast.parse(src)):
    if isinstance(dugum, ast.ImportFrom):
        if any(ad.name in YASAK or ad.name == "*" for ad in dugum.names):
            sorunlar.append("referans veya kanıt yazıcısı içe aktarılamaz")
if sorunlar:
    ok(False, "Kendi ölçüm işlevlerini yaz: " + "; ".join(sorunlar))
    stop()
import tempfile
from pathlib import Path
from sandbox import ai_gercek_ai_guvence_26 as deney
# Test configuration is separate from the persistent editable student copy.
import torch as _tc
_lin = _tc.nn.Linear(2, 2, bias=False)
with _tc.no_grad():
    _lin.weight.copy_(_tc.tensor([[2.0, -1.0], [-2.0, 1.0]]))
_x0 = _tc.tensor([[0.9, 0.1]], dtype=_tc.float32)
_adv = fgsm_replika(_lin, _x0, _tc.tensor([0]), 0.25)
ok(_tc.allclose(_adv, _tc.tensor([[0.65, 0.35]])) and not _adv.requires_grad and _tc.allclose(fgsm_replika(_lin, _tc.tensor([[0.1, 0.9]]), _tc.tensor([0]), 0.25), _tc.tensor([[0.0, 1.0]])), 'fgsm_replika işaret yönünü ve [0,1] kırpmasını doğru uygulamalı')
_oz = replika_ozeti([
    {'seed': 2, 'kol': 'replika', 'temiz': 2, 'bozuk': 1, 'toplam': 3, 'lr': 0.02},
    {'seed': 2, 'kol': 'referans', 'temiz': 3, 'bozuk': 2, 'toplam': 3, 'lr': 0.01},
    {'seed': 1, 'kol': 'referans', 'temiz': 1, 'bozuk': 1, 'toplam': 3, 'lr': 0.01},
])
ok(_oz == [
    {'seed': 1, 'kol': 'referans', 'temiz': 0.333333, 'bozuk': 0.333333, 'fark': 0.0, 'degisen': []},
    {'seed': 2, 'kol': 'replika', 'temiz': 0.666667, 'bozuk': 0.333333, 'fark': -0.333333, 'degisen': ['lr']},
    {'seed': 2, 'kol': 'referans', 'temiz': 1.0, 'bozuk': 0.666667, 'fark': 0.0, 'degisen': []},
], 'replika_ozeti seed sıralaması, 6 basamak oran/fark ve lr sapmasını doğru üretmeli')
with tempfile.TemporaryDirectory(prefix="pafta-guvence-26-") as tmp:
    config=Path(tmp)/"ayar.json"
    config.write_text('{"seed":939,"eps":0.23}',encoding="utf-8")
    r=deney.deney(fgsm_replika,replika_ozeti,config,Path(tmp)/"deney")
    for name,value in r["kontroller"].items():ok(value,"GERCEK: "+name)
    ai_lab.kanit_yaz("guvence-26",dict(r,kabul=all(r["kontroller"].values())))
```

```solution
def fgsm_replika(model,x,y,eps):
    import torch
    z=x.detach().clone().requires_grad_(True)
    grad=torch.autograd.grad(torch.nn.functional.cross_entropy(model(z),y),z)[0]
    return (z.detach()+eps*grad.sign()).clamp(0,1)

def replika_ozeti(rows):
    result=[]
    for seed in sorted({r['seed'] for r in rows}):
        base=next(r for r in rows if r['seed']==seed and r['kol']=='referans')
        for r in rows:
            if r['seed']==seed:result.append(dict(seed=seed,kol=r['kol'],temiz=round(r['temiz']/r['toplam'],6),bozuk=round(r['bozuk']/r['toplam'],6),fark=round(r['bozuk']/r['toplam']-base['bozuk']/base['toplam'],6),degisen=['lr'] if r['lr']!=base['lr'] else []))
    return result

import ai_lab
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_26 as deney
    deney.goster(fgsm_replika,replika_ozeti)
```

```hint
Fonksiyonların etkisini gerçek model/araç akışında koru. Sabit oran veya hep izin/red kullanma. Bağımlılık yoksa gerçek kabul verilmez. Veri sentetiktir, eğitim ve dosya etkileri gerçektir.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Makale skoru neden bire bir çıkmaz? (30 sn).** "Güvenlik makalesindeki bir saldırı/savunma tablosunu yeniden üretirken veri altkümesi, öğrenme oranı (`lr`), rastgelelik tohumu, `[0,1]` kırpması veya kütüphane sürümündeki tek bir fark bile bozuk doğruluk oranını kaydırır."
2. **Aynı tohumlu kontrol kolu + tek değişkenli sapma (35 sn).** "Sapmanın bug mı yoksa hiperparametre etkisi mi olduğunu ayırmak için önce referansla bire bir aynı ayar ve tohumda kontrol koşusu yapılır, ardından yalnız tek bir parametre (`lr`) değiştirilerek fark ölçülür."
3. **Yöntem replikasyonu ile skor replikasyonu ayrımı (30 sn).** "Küçük sentetik ağda `FGSM` gradyan işaret adımını doğrulamak mekanizmanın doğru kodlandığını gösterir; özgün makalenin büyük veri kümesindeki mutlak sayılarını kopyalamakla karıştırılmamalıdır."
4. **Soru (25 sn).** "Bir savunma makalesini replike ederken yazarların koduyla senin bağımsız kodun arasında `%15` sağlam doğruluk farkı çıkarsa ilk hangi gizli varsayımları kontrol edersin?"
:::
