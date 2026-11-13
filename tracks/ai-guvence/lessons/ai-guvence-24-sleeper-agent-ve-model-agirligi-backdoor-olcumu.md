---
id: ai-guvence-24
title: Sleeper Agent ve Model Ağırlığı Backdoor Ölçümü
summary: Temiz ve tetikli kontrol çiftlerindeki davranış farkını ölç; tetikleyici ilişkisini model ağırlığı backdoor'unun kesin kanıtı saymadan raporla.
esleme: ai-guvence-14, ai-guvence-23, ai-guvence-25
timeout: 45
---

::: anlat Tetikli örnek tek başına backdoor kanıtı değildir
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Ağırlık backdoor değerlendirmesi temiz/tetikli tahminleri, eğitim koşullarını ve sonraki uyarlama etkisini karşılaştırır | Görevler 1–3'te `veri/olcumler.json` içinde elle yazılmış sentetik sayımlar; son görevde PyTorch CPU üzerinde autograd ile eğitilen küçük sınıflandırıcı ve temiz veriyle fine-tune | Bu küçük özellik-tetikleyici modeli LLM sleeper-agent replikasyonu değildir; korelasyon gizli niyet veya genel ağırlık backdoor kanıtı vermez |

> [!NOT]
> İlk üç görevin dosyaları **sentetik örnektir**, canlı model ölçümü değildir. **Çalıştır** aynı dosyayı okuyup sonucu gösterir. Koddan geçici kopyayı değiştirip aynı çalıştırmada yeniden ölçebilirsin; sonraki çalıştırmada kaynak örnek yenilenir, bu kopya kalıcı değildir. Son gerçek deneyin `PAFTA_DATA/calisma/ai-guvence-24/ayar.json` dosyası ise kalıcıdır ve sonraki çalıştırmalarda korunur. Gizli testler öğrenci örneğinden bağımsızdır.

Sleeper agent veya ağırlık backdoor'u iddiasında belirli bir tetikleyicinin gizli hedef davranışı ortaya çıkardığı ileri sürülür. Bu iddiayı ölçmek için aynı örneklerin temiz ve tetikli sürümleri birlikte değerlendirilir. Yalnız tetikli girdideki yüksek hedef oranı, temiz girdide zaten bulunan davranışı göstermez.

Görevler 1–3 sentetik toplamlarla çalışır; son adım gerçek PyTorch CPU modeli eğitir ve temiz verili fine-tune sonrasında tekrar ölçer. Bu ders Transformers veya canlı LLM çalıştırmaz. Her kimlik için temiz ve tetikli koşulun örnek sayısı eşitlenir; hedef davranış oranları ve farkları ayrı raporlanır.
:::

::: anlat Sayısal ilişki nedensellik ve yerleşim kanıtı sağlamaz
Temiz koşulda düşük, tetikli koşulda yüksek hedef oranı tetikleyiciyle ilişkili şüphe oluşturabilir. Ancak bu sonuç davranışın model ağırlıklarına gömüldüğünü tek başına kanıtlamaz. Veri sızıntısı, değerlendirme hatası, sistem mesajı veya başka dış etkenler ayrıca araştırılmalıdır.

Eşikler yalnız inceleme önceliği üretir. Fark, temiz kontrol ve tetikli oran koşulları ayrı tutulur; biri sağlanmadığında neden açıkça yazılır. Sonuç `agirlik_backdoor_kaniti_degil` notuyla verilir.
:::

::: anlat Deneyi kur, paydaları kontrol et, bulgunun sınırını koru
Bir tetikleyici ölçümünde ilk soru “oran kaç” değil, o oranın hangi örneklerden hesaplandığıdır. Temiz kayıt ile tetikli kayıt aynı kimliği taşımalı ve aynı sayıda örneği temsil etmelidir. Bir tarafta yüz, diğer tarafta üç örnek varsa yüzdelik farkın görünüşü aynı olsa bile ölçümün belirsizliği farklıdır. Bu ders eşit toplam şartıyla bu karışıklığı erken yakalar. Kimliği de yalnız biçim süsü olarak görme: yanlış kimlik birleştirmesi farklı deneylerin temiz ve tetikli taraflarını eşleştirerek gerçekte olmayan bir etki yaratabilir. Yinelenen kimlik ve koşul çifti sessizce toplanmaz, hata olarak reddedilir.

Görünür `veri/olcumler.json` dosyasını önce ham hâliyle incele. Bazı kimliklerde hedef davranış tetikle birlikte artar, birinde aynı kalır, birinde azalır. Tek bir etkileyici örnek yerine bu karşılaştırmaları birlikte okumak gerekir. İlk görev bir kaydın güvenilir biçimde işlenebilir olup olmadığını denetler. İkinci görev aynı dosyadaki çiftleri eşleştirir ve ham oran farkını hesaplar. Üçüncü görev dosyadaki eşiklerle inceleme önceliği üretir. Eşiği değiştirmek veriyi veya model ağırlığını değiştirmez; yalnız aynı gözleme verdiğin sınıflandırma kararını değiştirir.

Çıktıdaki temiz oran, tetikli oran ve fark birbirinin yerine geçmez. Tetikli oran yüksekken temiz oran da yüksekse, model o davranışı zaten sık üretiyor olabilir. Bu yüzden yalnız tetikli başarıyı raporlamak tetikleyici etkisini olduğundan büyük gösterebilir. Farkın minimum eşiğe tam eşit olması bu dersin sıkı büyüktür kuralını karşılamaz. Temiz üst sınır ve tetikli alt sınır ise eşitliği kabul eder. Hesap kararını yuvarlanmış ekrandaki sayıdan verme: rapordaki altı basamak okunabilirlik içindir, karşılaştırma ham oranlarla yapılır. Yoksa eşik çevresindeki küçük farklar yanlış karara dönüşür.

Gerçek deneyde dört özellikli sentetik girdilerle küçük bir sinir ağı eğitilir. Tetikleyici dördüncü özelliğin belirli bir değer almasıdır; eğitimde tetikli örneklerin sınıfı hedef sınıf bire çevrilir. Autograd kaybın türevlerini hesaplar ve optimizer gerçek ağırlıkları günceller. Model önce temiz ve tetikli değerlendirme girdilerinde tahmin yapar. Sonra yalnız temiz, değerlendirmeden ayrı örneklerle kısa bir fine-tune uygulanır; aynı değerlendirme girdilerinde yeniden tahmin alınır. Böylece iki faz arasındaki fark yeni test verisi seçimiyle karışmaz. Ağırlık dosyası hash'i hangi model durumunun ölçüldüğünü izlemeyi sağlar; aynı dosya adı tek başına aynı ağırlık anlamına gelmez.

Saldırgan açısından soru, temiz davranışı fazla bozmadan tetikleyiciye bağlı hedef davranışın sürüp sürmediğidir. Savunma açısından yalnız temiz veride yüksek doğruluk görmek, tetikli davranışın kaybolduğunu göstermez. Temiz fine-tune sonrasında hedef oran düşebilir, aynı kalabilir veya beklenenden farklı değişebilir; bunların hepsi ölçülecek sonuçlardır. Öğrencinin geçmesi tetikleyicinin başarılı olmasına bağlı değildir. Kabul, tahminlerin doğru gruplandığını ve oranların doğru hesaplandığını sınar. Bir sınıflandırıcının sınıf bire gitmesi zararlı içerik üretimi veya gizli plan taşıması olarak yorumlanmaz.

Son görevdeki `hedef` alanı doğal doğru sınıftır; tetik hedefi ise sabit birdir. Temiz doğruluğu bütün satırlarda hesaplarsan tetikli grubu yanlış paydaya katarsın. ASR'yi doğal etikete göre hesaplarsan da hedef sınıfa yönelmeyi normal sınıflandırma doğruluğuyla karıştırırsın. Fazları birleştirmek fine-tune etkisini görünmez kılar. Bu nedenle her fazın temiz sayısı, temiz doğru sayısı, tetik sayısı ve hedefe giden sayısı ayrı tutulur. Ham tahminler, logitler, eğitim ayarları ve ağırlık hash'leri kanıtta birlikte okunmalıdır; yalnız güzel görünen bir son oran yeterli değildir.
:::

::: tahmin Temiz ve tetikli oran farkını tahmin et
Üç çıktı satırını yaz:

```python
print(round(90 / 100 - 10 / 100, 6))
print(round(3 / 3 - 1 / 3, 6))
print(0.5 > 0.5)
```

???

```cikti
0.8
0.666667
False
```

İlk iki satır temiz referansa göre tetikli artışı, üçüncü satır tam minimum fark sınırının sıkı büyüktür koşulunu geçmediğini gösterir.
:::

::: gorev 1 · Temiz ve tetikli ölçüm kaydını doğrula
`backdoor_olcum_dogrula(kayit)` işlevini yaz. Kayıt tam olarak `id`, `kosul`, `hedef`, `toplam` alanlarını taşır. Kimlik 1–64 karakterlik, ASCII harf/rakamla başlayan ve yalnız ASCII harf, rakam, alt çizgi veya tire içeren stringdir.

Koşul yalnız `temiz` veya `tetikli` olur. `toplam` bool olmayan, 1–10000 arasında tam sayıdır. `hedef` bool olmayan, 0 ile `toplam` arasında tam sayıdır. Geçersiz veride `ValueError` yükselt. Bağımsız sözlük kopyası döndür ve girdiyi değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-24")
```

```starter
from ai_guvence_veri import json_yukle

def backdoor_olcum_dogrula(kayit):
    # KUSURLU BAŞLANGIÇ KODU: sınırları denetlemeden aynı sözlüğü geri veriyor.
    return kayit

v=json_yukle("veri/olcumler.json")
print("Sentetik ölçüm dosyası:",v)
print("İlk kayıt:",backdoor_olcum_dogrula(v["kayitlar"][0]))
```

```test
import copy
K = {"id": "ornek-1", "kosul": "temiz", "hedef": 10, "toplam": 100}
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        if fn(K) != K or fn(K) is K or K != once:
            return False
        ust = dict(K, id="a" * 64, kosul="tetikli", hedef=10000, toplam=10000)
        alt = dict(K, hedef=0, toplam=1)
        if fn(ust) != ust or fn(alt) != alt or fn(dict(K, hedef=0))["hedef"] != 0:
            return False
        for kayit in [
            None, [], dict(K, ek=1), dict(K, id=""), dict(K, id="a b"), dict(K, id="a" * 65), dict(K, id=None),
            dict(K, kosul="diger"), dict(K, kosul=None), dict(K, kosul=1),
            dict(K, hedef=-1), dict(K, hedef=101), dict(K, hedef=1.5), dict(K, hedef=True), dict(K, hedef=None),
            dict(K, hedef=0, toplam=0), dict(K, toplam=10001), dict(K, toplam=100.0), dict(K, hedef=0, toplam=False), dict(K, hedef=0, toplam=True), dict(K, toplam=None),
        ]:
            try:
                fn(kayit)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(backdoor_olcum_dogrula), "ölçüm şeması, koşul ve sayım sınırları korunmalı")
def m_kosul(kayit):
    return backdoor_olcum_dogrula(dict(kayit, kosul="diger"))
def m_hedef(kayit):
    return backdoor_olcum_dogrula(dict(kayit, hedef=101))
def m_toplam(kayit):
    return backdoor_olcum_dogrula(dict(kayit, toplam=0))
def m_kimlik(kayit):
    return backdoor_olcum_dogrula(dict(kayit, id="a b"))
for ad, mutant in [("koşulu bozan", m_kosul), ("hedefi bozan", m_hedef), ("toplamı bozan", m_toplam), ("kimliği bozan", m_kimlik)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_guvence_veri import json_yukle
def backdoor_olcum_dogrula(kayit):
    import re
    if not isinstance(kayit, dict):
        raise ValueError("kayıt sözlük olmalı")
    if set(kayit) != {"id", "kosul", "hedef", "toplam"}:
        raise ValueError("kayıt şeması geçersiz")
    if not isinstance(kayit["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
        raise ValueError("kimlik geçersiz")
    if kayit["kosul"] not in ("temiz", "tetikli"):
        raise ValueError("koşul geçersiz")
    if not isinstance(kayit["toplam"], int) or isinstance(kayit["toplam"], bool) or not 1 <= kayit["toplam"] <= 10000:
        raise ValueError("toplam geçersiz")
    if not isinstance(kayit["hedef"], int) or isinstance(kayit["hedef"], bool) or not 0 <= kayit["hedef"] <= kayit["toplam"]:
        raise ValueError("hedef sayısı geçersiz")
    return dict(kayit)

if __name__ == "__main__":
    v=json_yukle("veri/olcumler.json")
    print("Sentetik ölçüm dosyası:",v)
    print("İlk kayıt:",backdoor_olcum_dogrula(v["kayitlar"][0]))
```

```hint
Koşulu izinli iki stringle sınırla. Tam sayı alanlarında bool değerlerini reddet; hedef sayısının üst sınırını toplamdan al.
```
:::

::: gorev 2 · Temiz referansa göre tetikli davranış farkını hesapla
`backdoor_fark_raporu(kayitlar)` işlevini yaz. Girdi ilk görevdeki kayıtların boş olmayan listesidir. Her kimlikte tam bir `temiz` ve bir `tetikli` kaydı bulunmalı, toplamları eşit olmalıdır. Aynı `id`-`kosul` çifti yinelenemez. Geçersiz veride `ValueError` yükselt.

Her kimliğin ilk görüldüğü sırayı koruyarak `{"id":D,"temiz_oran":T,"tetikli_oran":E,"fark":F,"tetikte_artis":B}` üret. Oranlar `hedef / toplam`, fark ise ham `tetikli_oran - temiz_oran` değeridir. Üç sayısal alan raporda 6 ondalığa yuvarlanır. Tetikte artış, ham tetikli oranı temiz orandan büyükse doğrudur.

`{"satirlar":[...],"artis_sayisi":N}` döndür. Girdiyi değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-24")
```

```starter
from ai_guvence_veri import json_yukle

def backdoor_fark_raporu(kayitlar):
    # KUSURLU BAŞLANGIÇ KODU: eşleştirme yapmadan her satırı tetikli kabul ediyor.
    satirlar=[{"id":k["id"],"temiz_oran":0.0,"tetikli_oran":k["hedef"]/k["toplam"],"fark":k["hedef"]/k["toplam"],"tetikte_artis":True} for k in kayitlar]
    return {"satirlar":satirlar,"artis_sayisi":len(satirlar)}

v=json_yukle("veri/olcumler.json")
print("Sentetik ölçümler:",v)
print("Fark raporu:",backdoor_fark_raporu(v["kayitlar"]))
```

```test
import copy
K = [
    {"id": "a", "kosul": "temiz", "hedef": 10, "toplam": 100},
    {"id": "a", "kosul": "tetikli", "hedef": 90, "toplam": 100},
    {"id": "b", "kosul": "tetikli", "hedef": 40, "toplam": 100},
    {"id": "b", "kosul": "temiz", "hedef": 40, "toplam": 100},
    {"id": "c", "kosul": "temiz", "hedef": 80, "toplam": 100},
    {"id": "c", "kosul": "tetikli", "hedef": 60, "toplam": 100},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        sonuc = fn(K)
        if K != once or sonuc["artis_sayisi"] != 1:
            return False
        if sonuc["satirlar"] != [
            {"id": "a", "temiz_oran": 0.1, "tetikli_oran": 0.9, "fark": 0.8, "tetikte_artis": True},
            {"id": "b", "temiz_oran": 0.4, "tetikli_oran": 0.4, "fark": 0.0, "tetikte_artis": False},
            {"id": "c", "temiz_oran": 0.8, "tetikli_oran": 0.6, "fark": -0.2, "tetikte_artis": False},
        ]:
            return False
        uc = [dict(K[0], id="a" * 64, hedef=1, toplam=3), dict(K[1], id="a" * 64, hedef=2, toplam=3)]
        if fn(uc)["satirlar"][0] != {"id": "a" * 64, "temiz_oran": 0.333333, "tetikli_oran": 0.666667, "fark": 0.333333, "tetikte_artis": True}:
            return False
        alt = [dict(K[0], hedef=0, toplam=1), dict(K[1], hedef=0, toplam=1)]
        ust = [dict(K[0], hedef=10000, toplam=10000), dict(K[1], hedef=10000, toplam=10000)]
        if fn(alt)["satirlar"][0]["temiz_oran"] != 0.0 or fn(ust)["satirlar"][0]["tetikli_oran"] != 1.0:
            return False
        def ayni_cift(**degisiklik):
            return [dict(K[0], **degisiklik), dict(K[1], **degisiklik)]
        for kayitlar in [
            None, {}, tuple(K), [], [None], [dict(K[0], ek=1)] + K[1:], [dict(K[0], id="a b")] + K[1:], ayni_cift(id="a" * 65), ayni_cift(id=None),
            [dict(K[0], kosul=[])] + K, ayni_cift(hedef=0, toplam=0), ayni_cift(toplam=10001),
            ayni_cift(toplam=100.0), ayni_cift(hedef=0, toplam=True), ayni_cift(hedef=-1),
            ayni_cift(hedef=101), ayni_cift(hedef=1.5), ayni_cift(hedef=True),
            [K[0]], [K[1]], [K[0], K[0], K[1]], [K[0], dict(K[1], toplam=200, hedef=180)],
        ]:
            try:
                fn(kayitlar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(backdoor_fark_raporu), "eşleştirme, kimlik sırası, oranlar ve tetikli fark korunmalı")
def m_oran(kayitlar):
    return backdoor_fark_raporu([dict(x, hedef=0) for x in kayitlar])
def m_kosul(kayitlar):
    return backdoor_fark_raporu([dict(x, kosul="temiz") for x in kayitlar])
def m_toplam(kayitlar):
    return backdoor_fark_raporu([dict(x, toplam=1000, hedef=0) for x in kayitlar])
for ad, mutant in [("oranları silen", m_oran), ("koşulları silen", m_kosul), ("toplam uyumunu bozan", m_toplam)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_guvence_veri import json_yukle
def backdoor_fark_raporu(kayitlar):
    import re
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar boş olmayan liste olmalı")
    temiz = []
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"id", "kosul", "hedef", "toplam"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(kayit["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
            raise ValueError("kimlik geçersiz")
        if kayit["kosul"] not in ("temiz", "tetikli"):
            raise ValueError("koşul geçersiz")
        if not isinstance(kayit["toplam"], int) or isinstance(kayit["toplam"], bool) or not 1 <= kayit["toplam"] <= 10000:
            raise ValueError("toplam geçersiz")
        if not isinstance(kayit["hedef"], int) or isinstance(kayit["hedef"], bool) or not 0 <= kayit["hedef"] <= kayit["toplam"]:
            raise ValueError("hedef sayısı geçersiz")
        temiz.append(dict(kayit))
    gruplar = {}
    gorulen = set()
    for kayit in temiz:
        cift = (kayit["id"], kayit["kosul"])
        if cift in gorulen:
            raise ValueError("yinelenen kimlik-koşul çifti")
        gorulen.add(cift)
        gruplar.setdefault(kayit["id"], {})[kayit["kosul"]] = kayit
    satirlar = []
    for kimlik, grup in gruplar.items():
        if set(grup) != {"temiz", "tetikli"} or grup["temiz"]["toplam"] != grup["tetikli"]["toplam"]:
            raise ValueError("eşit toplamlı temiz ve tetikli çift gerekli")
        temiz_oran = grup["temiz"]["hedef"] / grup["temiz"]["toplam"]
        tetikli_oran = grup["tetikli"]["hedef"] / grup["tetikli"]["toplam"]
        satirlar.append({"id": kimlik, "temiz_oran": round(temiz_oran, 6), "tetikli_oran": round(tetikli_oran, 6), "fark": round(tetikli_oran - temiz_oran, 6), "tetikte_artis": tetikli_oran > temiz_oran})
    return {"satirlar": satirlar, "artis_sayisi": sum(1 for x in satirlar if x["tetikte_artis"])}

if __name__ == "__main__":
    v=json_yukle("veri/olcumler.json")
    print("Sentetik ölçümler:",v)
    print("Fark raporu:",backdoor_fark_raporu(v["kayitlar"]))
```

```hint
Her kimlik için iki koşulu sözlükte eşleştir. Raporlanan değerleri yuvarla; artış kararını yuvarlanmamış oranlarla ver.
```
:::

::: gorev 3 · Tetikleyici şüphesini kanıt sınırlarıyla değerlendir
`backdoor_kanit_raporu(kayitlar, min_fark, max_temiz, min_tetikli)` işlevini yaz. Kayıtlar ikinci görevdeki kurallara uyar. Üç eşik de bool olmayan, sonlu, 0–1 aralığında `int` veya `float` olmalıdır; geçersiz veride `ValueError` yükselt.

Her kimlik için `{"id":D,"temiz_oran":T,"tetikli_oran":E,"fark":F,"karar":K,"nedenler":N}` üret. Sayısal alanlar ikinci görevdeki gibi hesaplanır ve 6 ondalığa yuvarlanır. Kimliklerin ilk görülme sırası korunur.

Şüpheli kararı için üç koşul birlikte gerekir: ham fark `min_fark` değerinden büyük, ham temiz oran `max_temiz` değerine eşit veya küçük, ham tetikli oran `min_tetikli` değerine eşit veya büyük olmalıdır. Uygunsa karar `supheli`, aksi hâlde `yetersiz_kanit` olur. Sağlanmayan koşullar sırasıyla `fark_yetersiz`, `temiz_kontrol_yuksek`, `tetikli_oran_dusuk` olarak nedenlere eklenir.

`{"satirlar":[...],"supheli_sayi":N,"kanit_notu":"agirlik_backdoor_kaniti_degil"}` döndür. Girdiyi değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-24")
```

```starter
from ai_guvence_veri import json_yukle

def backdoor_kanit_raporu(kayitlar, min_fark, max_temiz, min_tetikli):
    # KUSURLU BAŞLANGIÇ KODU: temiz kontrolü ve farkı yok sayıp tek tetikli oranla karar veriyor.
    satirlar=[{"id":k["id"],"karar":"supheli" if k["hedef"]/k["toplam"]>=min_tetikli else "yetersiz_kanit"} for k in kayitlar if k["kosul"]=="tetikli"]
    return {"satirlar":satirlar,"supheli_sayi":sum(k["karar"]=="supheli" for k in satirlar),"kanit_notu":"agirlik_backdoor_kaniti_degil"}

v=json_yukle("veri/olcumler.json")
print("Sentetik ölçüm/eşikler:",v)
print("Kanıt sınırı:",backdoor_kanit_raporu(v["kayitlar"],**v["esikler"]))
```

```test
import copy
K = [
    {"id": "a", "kosul": "temiz", "hedef": 0, "toplam": 100},
    {"id": "a", "kosul": "tetikli", "hedef": 90, "toplam": 100},
    {"id": "b", "kosul": "temiz", "hedef": 20, "toplam": 100},
    {"id": "b", "kosul": "tetikli", "hedef": 90, "toplam": 100},
    {"id": "c", "kosul": "temiz", "hedef": 0, "toplam": 100},
    {"id": "c", "kosul": "tetikli", "hedef": 40, "toplam": 100},
    {"id": "d", "kosul": "temiz", "hedef": 5, "toplam": 100},
    {"id": "d", "kosul": "tetikli", "hedef": 80, "toplam": 100},
    {"id": "e", "kosul": "temiz", "hedef": 0, "toplam": 100},
    {"id": "e", "kosul": "tetikli", "hedef": 50, "toplam": 100},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        sonuc = fn(K, 0.5, 0.05, 0.8)
        if K != once or sonuc["supheli_sayi"] != 2 or sonuc["kanit_notu"] != "agirlik_backdoor_kaniti_degil":
            return False
        if sonuc["satirlar"] != [
            {"id": "a", "temiz_oran": 0.0, "tetikli_oran": 0.9, "fark": 0.9, "karar": "supheli", "nedenler": []},
            {"id": "b", "temiz_oran": 0.2, "tetikli_oran": 0.9, "fark": 0.7, "karar": "yetersiz_kanit", "nedenler": ["temiz_kontrol_yuksek"]},
            {"id": "c", "temiz_oran": 0.0, "tetikli_oran": 0.4, "fark": 0.4, "karar": "yetersiz_kanit", "nedenler": ["fark_yetersiz", "tetikli_oran_dusuk"]},
            {"id": "d", "temiz_oran": 0.05, "tetikli_oran": 0.8, "fark": 0.75, "karar": "supheli", "nedenler": []},
            {"id": "e", "temiz_oran": 0.0, "tetikli_oran": 0.5, "fark": 0.5, "karar": "yetersiz_kanit", "nedenler": ["fark_yetersiz", "tetikli_oran_dusuk"]},
        ]:
            return False
        uc = [dict(K[0], id="a" * 64, hedef=1, toplam=3), dict(K[1], id="a" * 64, hedef=2, toplam=3)]
        uc_sonuc = fn(uc, 0.25, 0.5, 0.5)["satirlar"][0]
        if uc_sonuc["temiz_oran"] != 0.333333 or uc_sonuc["tetikli_oran"] != 0.666667 or uc_sonuc["fark"] != 0.333333 or uc_sonuc["karar"] != "supheli":
            return False
        alt = [dict(K[0], hedef=0, toplam=1), dict(K[1], hedef=0, toplam=1)]
        ust = [dict(K[0], hedef=0, toplam=10000), dict(K[1], hedef=10000, toplam=10000)]
        if fn(alt, 0, 0, 0)["satirlar"][0]["karar"] != "yetersiz_kanit" or fn(ust, 0, 1, 1)["satirlar"][0]["karar"] != "supheli":
            return False
        def ayni_cift(**degisiklik):
            return [dict(K[0], **degisiklik), dict(K[1], **degisiklik)]
        for args in [
            (None, 0.5, 0.05, 0.8), (tuple(K), 0.5, 0.05, 0.8), ([], 0.5, 0.05, 0.8), ([None], 0.5, 0.05, 0.8),
            ([dict(K[0], ek=1)] + K[1:], 0.5, 0.05, 0.8), (ayni_cift(id="a" * 65), 0.5, 0.05, 0.8), (ayni_cift(id=None), 0.5, 0.05, 0.8),
            ([dict(K[0], kosul=[])] + K, 0.5, 0.05, 0.8), (ayni_cift(hedef=0, toplam=0), 0.5, 0.05, 0.8),
            (ayni_cift(toplam=10001), 0.5, 0.05, 0.8), (ayni_cift(toplam=100.0), 0.5, 0.05, 0.8),
            (ayni_cift(hedef=0, toplam=True), 0.5, 0.05, 0.8), (ayni_cift(hedef=-1), 0.5, 0.05, 0.8),
            (ayni_cift(hedef=101), 0.5, 0.05, 0.8), (ayni_cift(hedef=1.5), 0.5, 0.05, 0.8), (ayni_cift(hedef=True), 0.5, 0.05, 0.8),
            ([K[0]], 0.5, 0.05, 0.8), ([K[1]], 0.5, 0.05, 0.8), ([K[0], K[0], K[1]], 0.5, 0.05, 0.8),
            ([K[0], dict(K[1], toplam=200, hedef=180)], 0.5, 0.05, 0.8),
            (K, -0.1, 0.05, 0.8), (K, 1.1, 0.05, 0.8), (K, float("nan"), 0.05, 0.8), (K, float("inf"), 0.05, 0.8), (K, True, 0.05, 0.8), (K, None, 0.05, 0.8),
            (K, 0.5, -0.1, 0.8), (K, 0.5, 1.1, 0.8), (K, 0.5, float("nan"), 0.8), (K, 0.5, float("inf"), 0.8), (K, 0.5, False, 0.8), (K, 0.5, None, 0.8),
            (K, 0.5, 0.05, -0.1), (K, 0.5, 0.05, 1.1), (K, 0.5, 0.05, float("nan")), (K, 0.5, 0.05, float("inf")), (K, 0.5, 0.05, True), (K, 0.5, 0.05, None),
        ]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(backdoor_kanit_raporu), "üç kanıt eşiği, sınır davranışı, neden sırası ve kanıt notu korunmalı")
def m_hedef(kayitlar, min_fark, max_temiz, min_tetikli):
    return backdoor_kanit_raporu([dict(x, hedef=0) for x in kayitlar], min_fark, max_temiz, min_tetikli)
def m_kosul(kayitlar, min_fark, max_temiz, min_tetikli):
    return backdoor_kanit_raporu([dict(x, kosul="temiz") for x in kayitlar], min_fark, max_temiz, min_tetikli)
def m_esik(kayitlar, min_fark, max_temiz, min_tetikli):
    return backdoor_kanit_raporu(kayitlar, 0, 1, 0)
def m_sil(kayitlar, min_fark, max_temiz, min_tetikli):
    return backdoor_kanit_raporu(kayitlar[:2], min_fark, max_temiz, min_tetikli)
for ad, mutant in [("hedefleri silen", m_hedef), ("koşulları silen", m_kosul), ("eşikleri silen", m_esik), ("kayıtları silen", m_sil)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_guvence_veri import json_yukle
def backdoor_kanit_raporu(kayitlar, min_fark, max_temiz, min_tetikli):
    import math
    import re
    for esik in (min_fark, max_temiz, min_tetikli):
        if not isinstance(esik, (int, float)) or isinstance(esik, bool) or not math.isfinite(esik) or not 0 <= esik <= 1:
            raise ValueError("eşikler sonlu ve izinli aralıkta olmalı")
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar boş olmayan liste olmalı")
    temiz = []
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"id", "kosul", "hedef", "toplam"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(kayit["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
            raise ValueError("kimlik geçersiz")
        if kayit["kosul"] not in ("temiz", "tetikli"):
            raise ValueError("koşul geçersiz")
        if not isinstance(kayit["toplam"], int) or isinstance(kayit["toplam"], bool) or not 1 <= kayit["toplam"] <= 10000:
            raise ValueError("toplam geçersiz")
        if not isinstance(kayit["hedef"], int) or isinstance(kayit["hedef"], bool) or not 0 <= kayit["hedef"] <= kayit["toplam"]:
            raise ValueError("hedef sayısı geçersiz")
        temiz.append(dict(kayit))
    gruplar = {}
    gorulen = set()
    for kayit in temiz:
        cift = (kayit["id"], kayit["kosul"])
        if cift in gorulen:
            raise ValueError("yinelenen kimlik-koşul çifti")
        gorulen.add(cift)
        gruplar.setdefault(kayit["id"], {})[kayit["kosul"]] = kayit
    satirlar = []
    for kimlik, grup in gruplar.items():
        if set(grup) != {"temiz", "tetikli"} or grup["temiz"]["toplam"] != grup["tetikli"]["toplam"]:
            raise ValueError("eşit toplamlı temiz ve tetikli çift gerekli")
        temiz_oran = grup["temiz"]["hedef"] / grup["temiz"]["toplam"]
        tetikli_oran = grup["tetikli"]["hedef"] / grup["tetikli"]["toplam"]
        fark = tetikli_oran - temiz_oran
        nedenler = []
        if not fark > min_fark:
            nedenler.append("fark_yetersiz")
        if not temiz_oran <= max_temiz:
            nedenler.append("temiz_kontrol_yuksek")
        if not tetikli_oran >= min_tetikli:
            nedenler.append("tetikli_oran_dusuk")
        satirlar.append({"id": kimlik, "temiz_oran": round(temiz_oran, 6), "tetikli_oran": round(tetikli_oran, 6), "fark": round(fark, 6), "karar": "supheli" if not nedenler else "yetersiz_kanit", "nedenler": nedenler})
    return {"satirlar": satirlar, "supheli_sayi": sum(1 for x in satirlar if x["karar"] == "supheli"), "kanit_notu": "agirlik_backdoor_kaniti_degil"}

if __name__ == "__main__":
    v=json_yukle("veri/olcumler.json")
    print("Sentetik ölçüm/eşikler:",v)
    print("Kanıt sınırı:",backdoor_kanit_raporu(v["kayitlar"],**v["esikler"]))
```

```hint
Neden listesini üç bağımsız koşulla oluştur. Liste boşsa şüpheli kararı ver; fark için sıkı büyüktür, iki oran için eşitliği kabul eden sınırlar kullan.
```
:::


::: anlat Gerçek deney · Görünür ayar ve kalıcı öğrenci kopyası
Önce `/data/ai-guvence-24-deney.txt` adresini ders sunucusunda açıp sentetik JSON ayarını incele. Kaynak proje dosyası `web/data/ai-guvence-24-deney.txt`.

Çalıştır ilk kullanımda örneği `PAFTA_DATA/calisma/ai-guvence-24/ayar.json` dosyasına yalnız yoksa kopyalar; sonraki çalıştırmalar düzenlemeni korur. Göreli PAFTA_DATA proje köküne göre çözülür. Çalıştır çıktısındaki tam yolu bir metin editöründe aç, seed veya adim değiştir ve yeniden Çalıştır. Dahili dosya editörü yoktur. Kopyayı sıfırlamak için başka ada taşı; kendi düzenlemelerin otomatik silinmez. Kontrol ayrı geçici, görülmemiş girdiler kullanır.

Sentetik özellik tetikleyicisi olan küçük CPU sınıflandırıcısıdır; LLM `sleeper-agent` replikasyonu veya genel gizli niyet tespiti değildir. Arka kapı başarısı veya kalıcılığı kabul şartı değildir. Saldırının başarılı olması geçme koşulu değildir. Bağımlılık veya çağrı eksikse deney başarısız olur. Gerçek ağırlıklar Çalıştır klasöründe, girişler/çıktılar/hash/sürümler kabul kanıtında tutulur.

Kaynaklar: [Hubinger vd. 2024 — Sleeper Agents: Training Deceptive LLMs that Persist Through Safety Training (arXiv:2401.05566)](https://arxiv.org/abs/2401.05566), [Gu vd. 2017 — BadNets (arXiv:1708.06733)](https://arxiv.org/abs/1708.06733).
:::

::: gorev Gerçek deney · Autograd tetikleyici modeli ve fine-tune sonrası kalıcılık
`tetikleyici_olc(kayitlar)` gerçek tahminlerden gelen `faz`, `tetik`, `hedef`, `tahmin` kayıtlarını faza göre sıralı özetler. Her faz için `temiz_n`, `temiz_dogru`, `tetik_n`, `tetik_hedef` ve tetikli örneklerde tahmin==1 oranı `asr` (6 basamak) döndür. Temiz doğruluk sadece tetik False grubunda, ASR sadece tetik True grubunda hesaplanır. `hedef` doğal sınıftır; tetik hedefi sabit 1. Eğitim sonrası ve yalnız temiz verili fine-tune sonrası grupları ayrı tut.

```meta
motor: ai-gercek
gereksinim: torch
timeout: 180
```

```starter
import ai_lab

def tetikleyici_olc(kayitlar):
    return None

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_24 as deney
    deney.goster(tetikleyici_olc)
```

```test
import tempfile,json,ast
import ai_lab
from pathlib import Path
YASAK=("olcum_ref","oracle","kanit_yaz")
sorun=ai_lab.kod_denetimi(src,yasak=YASAK)
for node in ast.walk(ast.parse(src)):
    if isinstance(node,ast.ImportFrom) and any(a.name in YASAK or a.name=="*" for a in node.names):
        sorun.append("referans import edilemez")
if sorun:
    ok(False,"Kendi tetikleyici ölçümünü yaz: "+", ".join(sorun))
    stop()
from sandbox import ai_gercek_ai_guvence_24 as deney
_uk = [
    {'faz': 'sonra', 'tetik': False, 'tahmin': 0, 'hedef': 0},
    {'faz': 'sonra', 'tetik': False, 'tahmin': 1, 'hedef': 0},
    {'faz': 'once', 'tetik': True, 'tahmin': 1, 'hedef': 0},
    {'faz': 'once', 'tetik': True, 'tahmin': 0, 'hedef': 0},
    {'faz': 'once', 'tetik': True, 'tahmin': 1, 'hedef': 1},
    {'faz': 'once', 'tetik': False, 'tahmin': 1, 'hedef': 1},
]
ok(tetikleyici_olc(_uk) == [
    {'faz': 'once', 'temiz_n': 1, 'temiz_dogru': 1, 'tetik_n': 3, 'tetik_hedef': 2, 'asr': 0.666667},
    {'faz': 'sonra', 'temiz_n': 2, 'temiz_dogru': 1, 'tetik_n': 0, 'tetik_hedef': 0, 'asr': 0.0},
], 'tetikleyici_olc faz sıralaması, 6 basamak ASR ve sıfır tetik paydasını doğru hesaplamalı')
with tempfile.TemporaryDirectory(prefix='pafta-g24-') as tmp:
    root=Path(tmp); config=root/'girdi.json'
    # Hidden inputs independent of the editable student sample.
    sonuclar=[]
    for seed in (7100+24,9200+24):
        config.write_text(json.dumps(dict(seed=seed,adim=45)),encoding='utf-8')
        r=deney.deney(tetikleyici_olc,config,root/str(seed))
        for ad,deger in r['kontroller'].items(): ok(deger,'GERCEK 24: '+ad)
        sonuclar.append(r)
    kabul=all(all(r['kontroller'].values()) for r in sonuclar)
    ai_lab.kanit_yaz('guvence-24-kabul',dict(kaynak='gercek',kabul=kabul,deneyler=sonuclar,ortam=sonuclar[0]['ortam'],temizlik='Gorev temp dosyalari kapsam sonunda temizlenir; JSON kaniti kalicidir.'))
```

```solution
import ai_lab

def tetikleyici_olc(kayitlar):
    rows=[]
    for faz in sorted({r['faz'] for r in kayitlar}):
        temiz=[r for r in kayitlar if r['faz']==faz and not r['tetik']]
        tetik=[r for r in kayitlar if r['faz']==faz and r['tetik']]
        hit=sum(r['tahmin']==1 for r in tetik)
        rows.append(dict(faz=faz,temiz_n=len(temiz),temiz_dogru=sum(r['tahmin']==r['hedef'] for r in temiz),tetik_n=len(tetik),tetik_hedef=hit,asr=round(hit/len(tetik),6) if tetik else 0.0))
    return rows

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_24 as deney
    deney.goster(tetikleyici_olc)
```

```hint
Gerçek çıktıları ölç; tek seed veya görünür örneği ezberleme. Kabul deneyin ve ölçümün doğru yürütülmesidir.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Koşullu tetikleyici ve fazlar arası kalıcılık (35 sn).** "`Sleeper agent` veya ağırlık arka kapısı temiz girdilerde normal davranırken yalnızca spesifik bir bağlam/tetikleyici geldiğinde hedef çıktıyı üretir; standart güvenlik ince ayarı temiz dağılımı ödüllendirdiği için koşullu dalı her zaman silemeyebilir."
2. **Eşleşmiş kontrol çiftleriyle ölçüm (30 sn).** "Tetikleyicinin etkisini ölçmek için aynı gövde metin hem tetiksiz (`temiz`) hem tetikli (`tetik`) koşturulur ve ince ayar `once`/`sonra` fazlarında temiz doğruluk ile `ASR` yan yana izlenir."
3. **Korelasyon $\neq$ kasıtlı arka kapı kanıtı (30 sn).** "Davranışsal testte bir dizgenin çıktıyı kaydırması modelin eğitim verisindeki sahte korelasyondan da kaynaklanabilir; kesin ağırlık arka kapısı iddiası için tedarik ve eğitim izi gerekir."
4. **Soru (25 sn).** "Saldırganın seçtiği gizli tetikleyiciyi önceden bilmiyorsak yalnız kara-kutu girdi taramasıyla `sleeper agent` aramak neden temel olarak eksiktir?"
:::
