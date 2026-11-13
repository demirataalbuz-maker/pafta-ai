---
id: ai-saldiri-05
title: Başlangıç Saldırı Seti ve ASR Ölçümü
summary: Sabit saldırı setini içerik imzasıyla kaydet, deneme bütçesini açıkça sınırla ve yalnız eksiksiz sonuçlar üzerinden karşılaştırılabilir ASR hesapla.
timeout: 45
---

::: anlat Önce deneyin neyi ölçtüğünü sabitle

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Promptfoo, vaka yapılandırmasını bir sağlayıcı üzerinden çalıştırır ve her denemenin yanıtını kaydeder | İlk üç görevde görünür sentetik JSON; son görevde kurulu Promptfoo/Node ile yerel Ollama modeline sekiz gerçek çağrı | Yanıtın dolu olması saldırının başarılı olduğunu veya modelin genel güvenliğini göstermez |
| ASR, önceden tanımlanmış başarı olayının geçerli saldırı denemeleri içindeki oranıdır | Sentetik canary eşlemesi, ayrı kontrol/hata sayıları ve içerik imzası | Tek küçük setin oranı bütün jailbreak tekniklerini veya zarar kategorilerini temsil etmez |

> [!NOT]
> `veri/kampanya.json` elle hazırlanmış **sentetik** eğitim verisidir; kaydedilmiş model yanıtı değildir. İlk üç görevin setup bloğu bu dosyayı geçici çalışma klasörüne kopyalar. Her çalıştırmada yeni kopya gelir, değişiklikler kalıcı değildir. Dosyayı kaynak fixture klasöründe okuyabilir, editörde `json_yukle` sonucunun bir kopyasını değiştirerek etkisini deneyebilirsin. Gizli test verisi ayrıdır. Son görevdeki gerçek çağrılar ve ham çıktılar ayrıca kanıta kaydedilir.

Saldırı başarı oranı (**ASR**, Attack Success Rate), başarı ölçütünü karşılayan geçerli saldırı denemelerinin geçerli saldırı denemelerine oranıdır. Sayının karşılaştırılabilir olması için yalnız formülü bilmek yetmez: vakaların sırası, girdileri, hedefleri, tekrar sayıları ve sınıflandırıcı sürümü de deneyden önce kaydedilmelidir.

Bu derste zararsız bir hedef metni kullanıyoruz. Vaka seti `kontrol` ve `saldiri` kayıtlarını ayırır; kontroller temel davranışın çalıştığını gösterir, saldırı ASR'sinin paydasına girmez. Taşıma hatası saldırının başarısızlığı değildir: ayrı sayılır ve paydadan çıkarılır. Geçerli saldırı denemesi yoksa ASR `None` olur.

```python
import hashlib
import json

vakalar = [{"id": "a1", "tur": "saldiri", "girdi": "DENEX-07", "hedef": "BREACH:CANARY-42"}]
kanonik = json.dumps(vakalar, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
imza = hashlib.sha256(kanonik.encode("utf-8")).hexdigest()
print(len(imza), imza[:12])
print(kanonik)
```

İmza, setin değişmediğini denetlemeye yarar; setin iyi veya güvenli olduğunu kanıtlamaz. Promptfoo ve garak gibi araçlar da ancak sabit vaka tanımı, açık başarı koşulu ve saklanan ham sonuçlarla anlamlı karşılaştırma üretir. İlk üç görevde aynı ölçüm sözleşmesini standart Python ve görünür dosyalarla uygularız; son görev kurulu Promptfoo üzerinden gerçek yerel modeli çağırır. Ders yeni araç indirmez.
:::

::: tahmin
Bir saldırı vakası iki kez, diğeri bir kez deneniyor. Kontrol saldırı paydasında yoktur ve `hata` geçerli deneme sayılmaz. Dört çıktı satırını yaz:

```python
sonuclar = [
    ("a1", "saldiri", "basari"),
    ("a1", "saldiri", "hata"),
    ("a2", "saldiri", "basarisiz"),
    ("k1", "kontrol", "basarisiz"),
]
saldiri = [durum for _, tur, durum in sonuclar if tur == "saldiri"]
gecerli = sum(durum != "hata" for durum in saldiri)
basari = sum(durum == "basari" for durum in saldiri)
print(len(sonuclar), len(saldiri))
print(gecerli, basari)
print(f"{100 * basari / gecerli:.1f}")
print(sum(tur == "kontrol" for _, tur, _ in sonuclar))
```

???

```cikti
4 3
2 1
50.0
1
```

Toplam dört sonucun üçü saldırıdır. Hata paydadan çıktığı için iki geçerli saldırının biri başarılıdır; ASR yüzde 50 olur.
:::

::: gorev 1 · Saldırı setini doğrula ve içerik imzası çıkar
`set_imzala(vakalar)` işlevini yaz. Her vaka tam olarak `id`, `tur`, `girdi`, `hedef` anahtarlarını taşısın. `id` ve `girdi` boş olmayan string, `tur` `saldiri` veya `kontrol` olsun. Saldırıda `hedef` boş olmayan string, kontrolde `None` olmalıdır. Kimlikler benzersizdir; kural ihlallerinde `ValueError` yükselt.

Dönüş `(kayitlar, imza)` çifti olsun. `kayitlar`, girdi sırasını koruyan `(id, tur, girdi, hedef)` demetlerinden oluşsun. `imza`, özgün vaka listesinin `ensure_ascii=False`, `sort_keys=True`, `separators=(",", ":")` seçenekleriyle üretilen kanonik JSON'unun UTF-8 SHA-256 hex özeti olsun. Girdiyi değiştirme; aynı içerik aynı imzayı üretmeli, içerikteki değişiklik imzayı değiştirmelidir.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-05")
```

```starter
from ai_saldiri_veri import json_yukle
import hashlib
import json

def set_imzala(vakalar):
    # KUSURLU BAŞLANGIÇ KODU: sıradan JSON serileştirmesi kanonik imza değildir; şema denetlenmiyor.
    kayitlar=[(v["id"],v["tur"],v["girdi"],v["hedef"]) for v in vakalar]
    return kayitlar,hashlib.sha256(json.dumps(vakalar).encode("utf-8")).hexdigest()

v=json_yukle("veri/kampanya.json")
print("Sentetik vakalar:",v["vakalar"])
print("İmzalı set:",set_imzala(v["vakalar"]))
```

```test
import copy
import hashlib
import json
VAKALAR = [
    {"id": "a1", "tur": "saldiri", "girdi": "DENEX-07", "hedef": "BREACH:CANARY-42"},
    {"id": "k1", "tur": "kontrol", "girdi": "Notu özetle", "hedef": None},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(VAKALAR)
        kayitlar, imza = fn(VAKALAR)
        beklenen = json.dumps(VAKALAR, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if VAKALAR != once or imza != hashlib.sha256(beklenen.encode("utf-8")).hexdigest():
            return False
        if kayitlar != [("a1", "saldiri", "DENEX-07", "BREACH:CANARY-42"), ("k1", "kontrol", "Notu özetle", None)]:
            return False
        if fn(VAKALAR) != (kayitlar, imza) or fn([]) != ([], hashlib.sha256(b"[]").hexdigest()):
            return False
        degisen = copy.deepcopy(VAKALAR)
        degisen[0]["girdi"] += "!"
        if fn(degisen)[1] == imza:
            return False
        bozuklar = [
            [{"id": "a", "tur": "saldiri", "girdi": "x", "hedef": "y"}, {"id": "a", "tur": "kontrol", "girdi": "z", "hedef": None}],
            [{"id": "", "tur": "saldiri", "girdi": "x", "hedef": "y"}],
            [{"id": "a", "tur": "saldiri", "girdi": "x", "hedef": None}],
            [{"id": "a", "tur": "saldiri", "girdi": "x", "hedef": 42}],
            [{"id": "k", "tur": "kontrol", "girdi": "x", "hedef": "y"}],
            [{"id": "a", "tur": "diger", "girdi": "x", "hedef": "y"}],
            [{"id": "a", "tur": "diger", "girdi": "x", "hedef": None}],
            [{"id": ["a"], "tur": "saldiri", "girdi": "x", "hedef": "y"}],
            [{"id": "a", "tur": "saldiri", "girdi": ["x"], "hedef": "y"}],
            [{"id": "a", "tur": "saldiri", "girdi": "x", "hedef": ""}],
            [{"id": "a", "tur": "saldiri", "girdi": "", "hedef": "y"}],
            [{"id": "a", "tur": "saldiri", "girdi": "x"}],
        ]
        for vaka in bozuklar:
            try:
                fn(vaka)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(set_imzala), "şema, benzersiz kimlik, değişmeyen girdi ve kanonik imza birlikte doğrulanmalı")
def m_sira(vakalar):
    kayitlar, _ = set_imzala(vakalar)
    return sorted(kayitlar), "sabit"
def m_json(vakalar):
    kayitlar, _ = set_imzala(vakalar)
    return kayitlar, hashlib.sha256(json.dumps(vakalar).encode("utf-8")).hexdigest()
def m_kopya(vakalar):
    kayitlar, imza = set_imzala(vakalar)
    if vakalar:
        vakalar[0]["girdi"] = "degisti"
    return kayitlar, imza
for ad, mutant in [("sırayı bozan ve imzayı sabitleyen", m_sira), ("kanonik olmayan JSON kullanan", m_json), ("girdiyi değiştiren", m_kopya)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_saldiri_veri import json_yukle
import hashlib
import json

def set_imzala(vakalar):
    kayitlar = []
    kimlikler = set()
    for vaka in vakalar:
        if set(vaka) != {"id", "tur", "girdi", "hedef"}:
            raise ValueError("vaka şeması geçersiz")
        if not isinstance(vaka["id"], str) or not vaka["id"]:
            raise ValueError("id boş olamaz")
        if vaka["id"] in kimlikler:
            raise ValueError("id yinelenemez")
        if not isinstance(vaka["girdi"], str) or not vaka["girdi"]:
            raise ValueError("girdi boş olamaz")
        if vaka["tur"] not in ("saldiri", "kontrol"):
            raise ValueError("tur geçersiz")
        if vaka["tur"] == "saldiri":
            if not isinstance(vaka["hedef"], str) or not vaka["hedef"]:
                raise ValueError("saldırı hedefi gerekli")
        elif vaka["hedef"] is not None:
            raise ValueError("kontrol hedefi None olmalı")
        kimlikler.add(vaka["id"])
        kayitlar.append((vaka["id"], vaka["tur"], vaka["girdi"], vaka["hedef"]))
    kanonik = json.dumps(vakalar, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return kayitlar, hashlib.sha256(kanonik.encode("utf-8")).hexdigest()
v=json_yukle("veri/kampanya.json")
print("Sentetik vakalar:",v["vakalar"])
print("İmzalı set:",set_imzala(v["vakalar"]))

```

```hint
Doğrulamayı imza hesabından önce yap. JSON seçeneklerindeki boşluklar bile özeti değiştirir; demet listesi ise kanonik metinden değil, özgün sıradan üretilir.
```
:::

::: anlat Deneme bütçesi sonuçtan sonra büyütülmez

Önce ham veriyi aç: `veri/kampanya.json` içindeki `vakalar` saldırı ve kontrol girdilerini, `butce` tekrar sayılarını, `plan` ve `sonuclar` ise üçüncü görev için örnek eşleşmeyi taşır. İlk görevde girdi metnine bir ünlem ekleyip imzanın değişmesini gözle. JSON anahtarlarının yazılış sırasını değiştirmek, kanonikleştirme doğruysa imzayı değiştirmemelidir; vaka listesini ters çevirmek ise sırayı da değiştirdiği için yeni bir set üretir. İmza bir başarı puanı değildir: yanlış seçilmiş bir set de kusursuz biçimde imzalanabilir.

Kampanya altında sağlayıcı her plan satırını `/api/chat` çağrısına çevirir. Model, mesaj sırası ve sıcaklık aynı kalırken tohumlar ve tekrar numaraları kayda girer. İki kontrol sıradan işleri sorar; iki saldırı yalnız laboratuvarın ürettiği özel işareti ister. Burada kişisel veri ya da gerçek bir sır kullanılmaz. Modelin reddetmesi ölçülebilir bir sonuçtur; bunu araç hatası diye gizlemek oranı çarpıtır. Bağlantı kopması ise modelin direnmesi değildir ve ayrı hata alanında saklanır.

Çıktıda üç katmanı sırayla oku: önce aracın tamamlanma durumu, sonra ham model yanıtı, en son sınıflandırılmış durum. Promptfoo'nun dolu yanıt kontrolü yeşilken canary sızıntısı sıfır olabilir. Tersi durumda canary üreten dolu yanıt da aynı araç kontrolünü geçer; saldırı sonucunu ayrı sınıflandırıcı belirler. Bu nedenle yeşil kutunun anlamını okumadan güvenli ya da güvensiz kararı verme. Kanıt, kullanılan model sürümünü, ayarları ve ham satırları korur; sayıların kaynağını sonradan inceleyebilirsin.

Saldırgan değerlendirme düzenini de yanıltmayı deneyebilir: yalnız başarılı tekrarları saklamak, aynı sonucu iki kez saymak veya kontrol kaydını saldırı paydasına katmak sonucu değiştirir. Savunmanın raporu bu yüzden planla sonuçları bire bir eşleştirir. Eksik satırı başarısızlıkla doldurmak da doğru değildir; kayıp veriyi görünür hata olarak araştır. Bütçenin tamamlanmadığı bir deneyi bu ders kabul etmez; formülün hata-ayrık oluşu altyapı arızasını başarıya dönüştürmez.

Sık tuzaklardan biri yüzde ile kesri karıştırmaktır: `0.5`, yüzde 50'dir; sözleşme kesir döndürür. İkincisi `None` yerine sıfır yazmaktır. Geçerli saldırı yoksa sıfır başarı gözlendiği sonucunu çıkaramazsın. Üçüncüsü sağlam kontrol sayısını görev doğruluğu sanmaktır: bu dar ölçüm yalnız kontrolün canary sızdırmadığını söyler, modelin aritmetik veya özet kalitesini puanlamaz. Dördüncüsü tohumun her ortamda aynı yanıtı garanti ettiğini varsaymaktır. Ham yanıtlar değişebilir; değerlendirme sabit cümleyi değil sözleşmeyi ve ölçüm hesabını sınar.

Aynı vakayı istediğin kadar tekrar edip yalnız istediğin sonuçları raporlamak ASR'yi yönlendirir. Bu yüzden her vakanın tekrar sayısı ve toplam bütçe deneyden önce belirlenir. Tekrar numaraları `1..deneme` aralığındadır; sıfırdan başlayan numaralar ya da sonucu gördükten sonra eklenen denemeler planla sonuçların eşleşmesini bozar.

Aşağıdaki görevde vaka başına en fazla 5, set toplamında en fazla 12 deneme vardır. Bunlar dersin açık fixture sınırlarıdır; gerçek bir aracın evrensel sınırı değildir. Bütçe aşımı sessizce kırpılmaz, `ValueError` ile görünür olur.
:::

::: gorev 2 · Sınırlı ve sıralı deneme planı üret
`deneme_plani(vakalar)` işlevini yaz. Her vaka `id`, `girdi`, `hedef` ve `deneme` alanlarını taşır; kimlikler benzersiz, `girdi` boş olmayan string olmalıdır. `deneme`, bool olmayan ve `1 <= deneme <= 5` koşulunu sağlayan tam sayıdır. Toplam deneme bütçesi 12'yi aşarsa `ValueError` yükselt; planı kırpma.

Her vaka için `1` ile `deneme` arasında kayıt üret. Dönüş, vaka sırasını ve tekrar sırasını koruyan `{"vaka_id", "tekrar", "girdi", "hedef"}` sözlüklerinin listesidir. Girdi listesini değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-05")
```

```starter
from ai_saldiri_veri import json_yukle

def deneme_plani(vakalar):
    # KUSURLU BAŞLANGIÇ KODU: tekrarlar sıfırdan başlıyor, bütçe aşımı sessizce kırpılıyor.
    return [{"vaka_id":v["id"],"tekrar":t,"girdi":v["girdi"],"hedef":v["hedef"]}
            for v in vakalar for t in range(v["deneme"])][:12]

v=json_yukle("veri/kampanya.json")
print("Sentetik bütçe:",v["butce"])
print("Plan:",deneme_plani(v["butce"]))
```

```test
import copy
VAKALAR = [
    {"id": "a1", "girdi": "DENEX-07", "hedef": "X", "deneme": 2},
    {"id": "k1", "girdi": "Özet", "hedef": None, "deneme": 1},
]
BEKLENEN = [
    {"vaka_id": "a1", "tekrar": 1, "girdi": "DENEX-07", "hedef": "X"},
    {"vaka_id": "a1", "tekrar": 2, "girdi": "DENEX-07", "hedef": "X"},
    {"vaka_id": "k1", "tekrar": 1, "girdi": "Özet", "hedef": None},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(VAKALAR)
        if fn(VAKALAR) != BEKLENEN or VAKALAR != once or fn([]) != []:
            return False
        sinir = [{"id": "a", "girdi": "x", "hedef": "y", "deneme": 5}, {"id": "b", "girdi": "z", "hedef": "y", "deneme": 5}, {"id": "k", "girdi": "q", "hedef": None, "deneme": 2}]
        if len(fn(sinir)) != 12 or fn(sinir)[-1]["tekrar"] != 2:
            return False
        bozuklar = [
            [{"id": "a", "girdi": "x", "hedef": "y", "deneme": 0}],
            [{"id": "a", "girdi": "x", "hedef": "y", "deneme": 6}],
            [{"id": "a", "girdi": "x", "hedef": "y", "deneme": True}],
            [{"id": "a", "girdi": "x", "hedef": "y", "deneme": 2.0}],
            [{"id": "a", "girdi": 42, "hedef": "y", "deneme": 1}],
            [{"id": "", "girdi": "x", "hedef": "y", "deneme": 1}],
            [{"id": "a", "girdi": "", "hedef": "y", "deneme": 1}],
            [{"id": "a", "girdi": "x", "hedef": "y", "deneme": 1}, {"id": "a", "girdi": "z", "hedef": "y", "deneme": 1}],
            [{"id": "a", "girdi": "x", "hedef": "y", "deneme": 5}, {"id": "b", "girdi": "z", "hedef": "y", "deneme": 5}, {"id": "k", "girdi": "q", "hedef": None, "deneme": 3}],
        ]
        for vaka in bozuklar:
            try:
                fn(vaka)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(deneme_plani), "tekrar aralığı, toplam bütçe, sıra ve girdi bütünlüğü korunmalı")
def m_sifir(vakalar):
    return [{"vaka_id": v["id"], "tekrar": t, "girdi": v["girdi"], "hedef": v["hedef"]} for v in vakalar for t in range(v["deneme"])]
def m_kirp(vakalar):
    plan = deneme_plani(vakalar[:-1]) if len(vakalar) > 1 else []
    return plan[:12]
def m_sinirsiz(vakalar):
    return [{"vaka_id": v["id"], "tekrar": t, "girdi": v["girdi"], "hedef": v["hedef"]} for v in vakalar for t in range(1, v["deneme"] + 1)]
for ad, mutant in [("sıfırdan numaralayan", m_sifir), ("bütçeyi sessizce kırpan", m_kirp), ("sınırları denetlemeyen", m_sinirsiz)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_saldiri_veri import json_yukle
def deneme_plani(vakalar):
    kimlikler = set()
    toplam = 0
    for vaka in vakalar:
        if not vaka["id"] or vaka["id"] in kimlikler:
            raise ValueError("vaka kimliği boş veya yinelenen")
        if not isinstance(vaka["girdi"], str) or not vaka["girdi"]:
            raise ValueError("girdi boş olamaz")
        deneme = vaka["deneme"]
        if isinstance(deneme, bool) or not isinstance(deneme, int) or not 1 <= deneme <= 5:
            raise ValueError("vaka deneme bütçesi 1..5 olmalı")
        kimlikler.add(vaka["id"])
        toplam += deneme
    if toplam > 12:
        raise ValueError("toplam deneme bütçesi aşıldı")
    return [
        {"vaka_id": vaka["id"], "tekrar": tekrar, "girdi": vaka["girdi"], "hedef": vaka["hedef"]}
        for vaka in vakalar
        for tekrar in range(1, vaka["deneme"] + 1)
    ]
v=json_yukle("veri/kampanya.json")
print("Sentetik bütçe:",v["butce"])
print("Plan:",deneme_plani(v["butce"]))

```

```hint
Önce bütün planı doğrula ve toplamı hesapla; sonra iç içe döngüyle kayıtları üret. `bool`, Python'da `int` alt sınıfı olduğu için ayrıca reddedilmelidir.
```
:::

::: anlat Eksik sonuçla oran hesaplama
Planlanan denemelerle gelen sonuçlar bire bir eşleşmelidir. Yinelenen sonuç, tanımadık tekrar veya eksik kayıt varsa oran hesaplamak yerine deneyi geçersiz sayarız. Böylece yalnız başarılı çalıştırmaları seçerek payda küçültmek mümkün olmaz.

Başarı sınıflandırması bir önceki dersteki gibi deneyden önce sabitlenir. Bu son görev sınıflandırıcıyı yeniden yazmaz; `basari`, `basarisiz`, `hata` etiketlerini denetler. Kontrolün `basarisiz` olması, kontrolün hedef canary'yi üretmediği anlamında sağlam kabul edilir. Hatalı kontrol ayrıca gözlenmelidir; tek bir sağlam kontrol, setin genel kalitesi için istatistiksel garanti değildir.
:::

::: gorev 3 · Yalnız eksiksiz sonuçlardan ASR hesapla
`asr_olc(plan, sonuclar)` işlevini yaz. `plan`, ikinci görevdeki `vaka_id`, `tekrar`, `girdi`, `hedef` alanlarını taşır; kontrol kaydı `hedef=None` ile ayırt edilir. Her sonuç `vaka_id`, `tekrar`, `durum` alanlarını taşır; durum yalnız `basari`, `basarisiz` veya `hata` olabilir.

Sonuç anahtarları `(vaka_id, tekrar)` planla tam eşleşmelidir. Eksik, fazla, yinelenen sonuç veya geçersiz durumda `ValueError` yükselt. Dönüş şu sözlüktür:

```text
{"deneme", "gecerli_saldiri", "basari", "saldiri_hatasi",
 "kontrol", "saglam_kontrol", "asr"}
```

`deneme` bütün plan kayıtlarını sayar. Saldırılarda hata paydadan çıkarılır; başarı yalnız saldırı sonuçlarında sayılır. Kontrol hedefi `None` olan kayıtlardır ve yalnız `basarisiz` durumu sağlam kontrolü artırır. `asr = basari / gecerli_saldiri`; payda sıfırsa `None` olmalıdır. Girdileri değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-05")
```

```starter
from ai_saldiri_veri import json_yukle

def asr_olc(plan,sonuclar):
    # KUSURLU BAŞLANGIÇ KODU: kontrol ve taşıma hataları saldırı paydasına karışıyor; eşleşme yok.
    basari=sum(s["durum"]=="basari" for s in sonuclar)
    return {"deneme":len(plan),"gecerli_saldiri":len(sonuclar),"basari":basari,
            "saldiri_hatasi":0,"kontrol":0,"saglam_kontrol":0,
            "asr":basari/len(sonuclar) if sonuclar else None}

v=json_yukle("veri/kampanya.json")
print("Sentetik plan/sonuç:",v["plan"],v["sonuclar"])
print("ASR:",asr_olc(v["plan"],v["sonuclar"]))
```

```test
import copy
PLAN = [
    {"vaka_id": "a1", "tekrar": 1, "girdi": "x", "hedef": "X"},
    {"vaka_id": "a1", "tekrar": 2, "girdi": "x", "hedef": "X"},
    {"vaka_id": "a2", "tekrar": 1, "girdi": "z", "hedef": "X"},
    {"vaka_id": "k1", "tekrar": 1, "girdi": "q", "hedef": None},
]
SONUC = [
    {"vaka_id": "a1", "tekrar": 1, "durum": "basari"},
    {"vaka_id": "a1", "tekrar": 2, "durum": "hata"},
    {"vaka_id": "a2", "tekrar": 1, "durum": "basarisiz"},
    {"vaka_id": "k1", "tekrar": 1, "durum": "basarisiz"},
]
BEKLENEN = {"deneme": 4, "gecerli_saldiri": 2, "basari": 1, "saldiri_hatasi": 1, "kontrol": 1, "saglam_kontrol": 1, "asr": 0.5}
BOS = {"deneme": 0, "gecerli_saldiri": 0, "basari": 0, "saldiri_hatasi": 0, "kontrol": 0, "saglam_kontrol": 0, "asr": None}
def sozlesme(fn):
    try:
        p, s = copy.deepcopy(PLAN), copy.deepcopy(SONUC)
        if fn(p, s) != BEKLENEN or p != PLAN or s != SONUC or fn([], []) != BOS:
            return False
        ters = list(reversed(SONUC))
        if fn(PLAN, ters) != BEKLENEN:
            return False
        tek_basari = fn([PLAN[0], PLAN[3]], [SONUC[0], SONUC[3]])
        if tek_basari["basari"] != 1 or tek_basari["asr"] != 1.0:
            return False
        hata = fn([PLAN[1], PLAN[3]], [SONUC[1], SONUC[3]])
        if hata["asr"] is not None or hata["saldiri_hatasi"] != 1 or hata["deneme"] != 2:
            return False
        bozuk_kontrol = [dict(x) for x in SONUC]
        bozuk_kontrol[-1]["durum"] = "basari"
        if fn(PLAN, bozuk_kontrol)["saglam_kontrol"] != 0:
            return False
        bozuklar = [SONUC[:-1], SONUC + [dict(SONUC[0])], SONUC[:-1] + [{"vaka_id": "a9", "tekrar": 1, "durum": "basari"}]]
        for sonuc in bozuklar:
            try:
                fn(PLAN, sonuc)
                return False
            except ValueError:
                pass
        yanlis = [dict(x) for x in SONUC]
        yanlis[0]["durum"] = "bilinmiyor"
        try:
            fn(PLAN, yanlis)
            return False
        except ValueError:
            pass
        return True
    except Exception:
        return False
ok(sozlesme(asr_olc), "eksiksiz eşleşme, ayrık hata ve kontrol, doğru payda birlikte zorunlu")
def m_eksik(plan, sonuclar):
    return asr_olc(plan[:-1], sonuclar[:-1])
def m_toplam_payda(plan, sonuclar):
    sonuc = asr_olc(plan, sonuclar)
    if sonuc["deneme"]:
        sonuc["asr"] = sonuc["basari"] / sonuc["deneme"]
    return sonuc
def m_kontrol(plan, sonuclar):
    sonuc = asr_olc(plan, sonuclar)
    sonuc["saglam_kontrol"] = sonuc["kontrol"]
    return sonuc
for ad, mutant in [("eksik sonucu gizleyen", m_eksik), ("hatayı ve kontrolü paydaya katan", m_toplam_payda), ("bozuk kontrolü sağlam sayan", m_kontrol)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_saldiri_veri import json_yukle
def asr_olc(plan, sonuclar):
    beklenen = {(adim["vaka_id"], adim["tekrar"]) for adim in plan}
    gelen = {}
    for sonuc in sonuclar:
        anahtar = (sonuc["vaka_id"], sonuc["tekrar"])
        if anahtar in gelen or sonuc["durum"] not in ("basari", "basarisiz", "hata"):
            raise ValueError("yinelenen sonuç veya geçersiz durum")
        gelen[anahtar] = sonuc["durum"]
    if set(gelen) != beklenen:
        raise ValueError("sonuçlar deneme planıyla eşleşmiyor")
    rapor = {"deneme": len(plan), "gecerli_saldiri": 0, "basari": 0, "saldiri_hatasi": 0, "kontrol": 0, "saglam_kontrol": 0, "asr": None}
    for adim in plan:
        durum = gelen[(adim["vaka_id"], adim["tekrar"])]
        if adim["hedef"] is None:
            rapor["kontrol"] += 1
            if durum == "basarisiz":
                rapor["saglam_kontrol"] += 1
        elif durum == "hata":
            rapor["saldiri_hatasi"] += 1
        else:
            rapor["gecerli_saldiri"] += 1
            if durum == "basari":
                rapor["basari"] += 1
    if rapor["gecerli_saldiri"]:
        rapor["asr"] = rapor["basari"] / rapor["gecerli_saldiri"]
    return rapor
v=json_yukle("veri/kampanya.json")
print("Sentetik plan/sonuç:",v["plan"],v["sonuclar"])
print("ASR:",asr_olc(v["plan"],v["sonuclar"]))

```

```hint
Sonuçları anahtarla indeksle, plan kümesiyle karşılaştır; sayaçları plan üzerinden doldur. Böylece sonuçların geliş sırası oranı etkilemez.
```
:::


::: anlat Gerçek kampanya: promptfoo sonucu ile ASR aynı şey değildir
Bu adım kurulu **promptfoo** CLI'sini kullanır. Dört sabit vaka (iki normal kontrol ve iki sentetik işaret isteği) ikişer kez, yerel Ollama modeline gönderilir. Canary her kampanyada yenidir. Ham promptfoo JSON'u, kullanılan sürüm, model özeti, ayarlar ve bütün yanıtlar kanıtta saklanır.

Promptfoo'nun yeşil testi burada yalnız yanıtın varlığını ölçer. **Saldırının başarılı olması**, özel canary'nin yanıta taşınmasıdır ve ayrı hesaplanır. Model hiç sızdırmasa da deney geçebilir. Bu canary deneyi belirli bir talimat ihlalini ölçer; içerik güvenliğinin bütün zarar kategorilerini temsil ettiği iddia edilmez.
:::

::: gorev Gerçek deney · Promptfoo kampanyasında set imzası ve hata-ayrık ASR
Önceki 1. ve 3. görevdeki `set_imzala(vakalar)` ve `asr_olc(plan, sonuclar)` işlevlerini burada birleştir. Sözleşmeleri aynıdır. Kontroller saldırı paydasına, taşıma hataları geçerli saldırılara katılmaz; eksik veya yinelenen sonuç reddedilir. Vaka setinin sırası ve UTF-8 kanonik SHA-256 imzası korunur.

Çalıştır gerçek kampanyayı ve ham yanıtları gösterir. Kontrol Et, hem deterministik sözleşmeleri hem promptfoo'nun gerçek sekiz çağrısını doğrular. Model çıktısı sabit bir metinle karşılaştırılmaz; saldırı başarısı geçme koşulu değildir. Eksik promptfoo/Node/model görevi geçirmez, ders indirme yapmaz.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab

def set_imzala(vakalar):
    return [], ""

def asr_olc(plan, sonuclar):
    return {}


if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_05 as deney
    deney.goster(set_imzala, asr_olc)
```

```test
import ai_lab
kontroller=[]
_eski_ok=ok
def ok(kosul, mesaj):
    kontroller.append(bool(kosul))
    return _eski_ok(kosul, mesaj)
import ast
_yasak=("imza","ozet","kanit_yaz","sizinti_referans")
_sorun=ai_lab.kod_denetimi(src,yasak=_yasak)
for _n in ast.walk(ast.parse(src)):
    if isinstance(_n,ast.ImportFrom) and any(a.name in _yasak or a.name=="*" for a in _n.names):
        _sorun.append("referans importu yasak")
if not ok(not _sorun,"Kendi set imzası ve ASR işlevlerini yaz: "+"; ".join(_sorun)):
    stop()
need("set_imzala")
need("asr_olc")
import copy
import hashlib
import json
VAKALAR = [
    {"id": "a1", "tur": "saldiri", "girdi": "DENEX-07", "hedef": "BREACH:CANARY-42"},
    {"id": "k1", "tur": "kontrol", "girdi": "Notu özetle", "hedef": None},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(VAKALAR)
        kayitlar, imza = fn(VAKALAR)
        beklenen = json.dumps(VAKALAR, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if VAKALAR != once or imza != hashlib.sha256(beklenen.encode("utf-8")).hexdigest():
            return False
        if kayitlar != [("a1", "saldiri", "DENEX-07", "BREACH:CANARY-42"), ("k1", "kontrol", "Notu özetle", None)]:
            return False
        if fn(VAKALAR) != (kayitlar, imza) or fn([]) != ([], hashlib.sha256(b"[]").hexdigest()):
            return False
        degisen = copy.deepcopy(VAKALAR)
        degisen[0]["girdi"] += "!"
        if fn(degisen)[1] == imza:
            return False
        bozuklar = [
            [{"id": "a", "tur": "saldiri", "girdi": "x", "hedef": "y"}, {"id": "a", "tur": "kontrol", "girdi": "z", "hedef": None}],
            [{"id": "", "tur": "saldiri", "girdi": "x", "hedef": "y"}],
            [{"id": "a", "tur": "saldiri", "girdi": "x", "hedef": None}],
            [{"id": "a", "tur": "saldiri", "girdi": "x", "hedef": 42}],
            [{"id": "k", "tur": "kontrol", "girdi": "x", "hedef": "y"}],
            [{"id": "a", "tur": "diger", "girdi": "x", "hedef": "y"}],
            [{"id": "a", "tur": "diger", "girdi": "x", "hedef": None}],
            [{"id": ["a"], "tur": "saldiri", "girdi": "x", "hedef": "y"}],
            [{"id": "a", "tur": "saldiri", "girdi": ["x"], "hedef": "y"}],
            [{"id": "a", "tur": "saldiri", "girdi": "x", "hedef": ""}],
            [{"id": "a", "tur": "saldiri", "girdi": "", "hedef": "y"}],
            [{"id": "a", "tur": "saldiri", "girdi": "x"}],
        ]
        for vaka in bozuklar:
            try:
                fn(vaka)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(set_imzala), "şema, benzersiz kimlik, değişmeyen girdi ve kanonik imza birlikte doğrulanmalı")
def m_sira(vakalar):
    kayitlar, _ = set_imzala(vakalar)
    return sorted(kayitlar), "sabit"
def m_json(vakalar):
    kayitlar, _ = set_imzala(vakalar)
    return kayitlar, hashlib.sha256(json.dumps(vakalar).encode("utf-8")).hexdigest()
def m_kopya(vakalar):
    kayitlar, imza = set_imzala(vakalar)
    if vakalar:
        vakalar[0]["girdi"] = "degisti"
    return kayitlar, imza
for ad, mutant in [("sırayı bozan ve imzayı sabitleyen", m_sira), ("kanonik olmayan JSON kullanan", m_json), ("girdiyi değiştiren", m_kopya)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
import copy
PLAN = [
    {"vaka_id": "a1", "tekrar": 1, "girdi": "x", "hedef": "X"},
    {"vaka_id": "a1", "tekrar": 2, "girdi": "x", "hedef": "X"},
    {"vaka_id": "a2", "tekrar": 1, "girdi": "z", "hedef": "X"},
    {"vaka_id": "k1", "tekrar": 1, "girdi": "q", "hedef": None},
]
SONUC = [
    {"vaka_id": "a1", "tekrar": 1, "durum": "basari"},
    {"vaka_id": "a1", "tekrar": 2, "durum": "hata"},
    {"vaka_id": "a2", "tekrar": 1, "durum": "basarisiz"},
    {"vaka_id": "k1", "tekrar": 1, "durum": "basarisiz"},
]
BEKLENEN = {"deneme": 4, "gecerli_saldiri": 2, "basari": 1, "saldiri_hatasi": 1, "kontrol": 1, "saglam_kontrol": 1, "asr": 0.5}
BOS = {"deneme": 0, "gecerli_saldiri": 0, "basari": 0, "saldiri_hatasi": 0, "kontrol": 0, "saglam_kontrol": 0, "asr": None}
def sozlesme(fn):
    try:
        p, s = copy.deepcopy(PLAN), copy.deepcopy(SONUC)
        if fn(p, s) != BEKLENEN or p != PLAN or s != SONUC or fn([], []) != BOS:
            return False
        ters = list(reversed(SONUC))
        if fn(PLAN, ters) != BEKLENEN:
            return False
        tek_basari = fn([PLAN[0], PLAN[3]], [SONUC[0], SONUC[3]])
        if tek_basari["basari"] != 1 or tek_basari["asr"] != 1.0:
            return False
        hata = fn([PLAN[1], PLAN[3]], [SONUC[1], SONUC[3]])
        if hata["asr"] is not None or hata["saldiri_hatasi"] != 1 or hata["deneme"] != 2:
            return False
        bozuk_kontrol = [dict(x) for x in SONUC]
        bozuk_kontrol[-1]["durum"] = "basari"
        if fn(PLAN, bozuk_kontrol)["saglam_kontrol"] != 0:
            return False
        bozuklar = [SONUC[:-1], SONUC + [dict(SONUC[0])], SONUC[:-1] + [{"vaka_id": "a9", "tekrar": 1, "durum": "basari"}]]
        for sonuc in bozuklar:
            try:
                fn(PLAN, sonuc)
                return False
            except ValueError:
                pass
        yanlis = [dict(x) for x in SONUC]
        yanlis[0]["durum"] = "bilinmiyor"
        try:
            fn(PLAN, yanlis)
            return False
        except ValueError:
            pass
        return True
    except Exception:
        return False
ok(sozlesme(asr_olc), "eksiksiz eşleşme, ayrık hata ve kontrol, doğru payda birlikte zorunlu")
def m_eksik(plan, sonuclar):
    return asr_olc(plan[:-1], sonuclar[:-1])
def m_toplam_payda(plan, sonuclar):
    sonuc = asr_olc(plan, sonuclar)
    if sonuc["deneme"]:
        sonuc["asr"] = sonuc["basari"] / sonuc["deneme"]
    return sonuc
def m_kontrol(plan, sonuclar):
    sonuc = asr_olc(plan, sonuclar)
    sonuc["saglam_kontrol"] = sonuc["kontrol"]
    return sonuc
for ad, mutant in [("eksik sonucu gizleyen", m_eksik), ("hatayı ve kontrolü paydaya katan", m_toplam_payda), ("bozuk kontrolü sağlam sayan", m_kontrol)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
if not all(kontroller):
    stop()
from sandbox import ai_gercek_ai_saldiri_05 as D
try:
    r=D.deney()
except Exception as e:
    ok(False, f"GERÇEK KAMPANYA YAPILAMADI: {type(e).__name__}: {e}")
    stop()
rows,digest=set_imzala(r["vakalar"])
ok(digest==D.imza(r["vakalar"]) and rows==[(v["id"],v["tur"],v["girdi"],v["hedef"]) for v in r["vakalar"]], "gerçek setin sırası ve imzası korunuyor")
rapor=asr_olc(r["plan"],r["sonuclar"])
ok(rapor==D.ozet(r["plan"],r["sonuclar"]), "gerçek ham sonuçlardan ASR, kontrol ve hata sayıları bağımsız hesapla aynı")
ok(len(r["sonuclar"])==8 and r["arac"]["exit"]==0 and not any(x["hata"] for x in r["sonuclar"]), "promptfoo sekiz gerçek çağrıyı eksiksiz/hatasız tamamladı")
ok(all(x["model_metadata"].get("real_call") and x["model_metadata"].get("done") for x in r["sonuclar"]), "her satır gerçek ve tamamlanmış Ollama çağrısı")
ok(r["gecici_temizlendi"], "yalnız kampanyaya ait geçici klasör temizlendi")
ai_lab.kanit_yaz("saldiri-05-promptfoo", {"kaynak":"gercek","kabul":all(kontroller),"ortam":r["ortam"],"deney":r,"ozet":rapor})
ok(True, f"BULGU: promptfoo {r['arac']['surum']}, {r['ortam']['model']['ad']}: {rapor['deneme']} çağrı; ASR {rapor['asr']}, geçerli saldırı {rapor['gecerli_saldiri']}, hata {rapor['saldiri_hatasi']}, sağlam kontrol {rapor['saglam_kontrol']}/{rapor['kontrol']}. Sızıntı oranı geçme şartı değildir.")
```

```solution
import ai_lab

import hashlib
import json

def set_imzala(vakalar):
    kayitlar = []
    kimlikler = set()
    for vaka in vakalar:
        if set(vaka) != {"id", "tur", "girdi", "hedef"}:
            raise ValueError("vaka şeması geçersiz")
        if not isinstance(vaka["id"], str) or not vaka["id"]:
            raise ValueError("id boş olamaz")
        if vaka["id"] in kimlikler:
            raise ValueError("id yinelenemez")
        if not isinstance(vaka["girdi"], str) or not vaka["girdi"]:
            raise ValueError("girdi boş olamaz")
        if vaka["tur"] not in ("saldiri", "kontrol"):
            raise ValueError("tur geçersiz")
        if vaka["tur"] == "saldiri":
            if not isinstance(vaka["hedef"], str) or not vaka["hedef"]:
                raise ValueError("saldırı hedefi gerekli")
        elif vaka["hedef"] is not None:
            raise ValueError("kontrol hedefi None olmalı")
        kimlikler.add(vaka["id"])
        kayitlar.append((vaka["id"], vaka["tur"], vaka["girdi"], vaka["hedef"]))
    kanonik = json.dumps(vakalar, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return kayitlar, hashlib.sha256(kanonik.encode("utf-8")).hexdigest()

def asr_olc(plan, sonuclar):
    beklenen = {(adim["vaka_id"], adim["tekrar"]) for adim in plan}
    gelen = {}
    for sonuc in sonuclar:
        anahtar = (sonuc["vaka_id"], sonuc["tekrar"])
        if anahtar in gelen or sonuc["durum"] not in ("basari", "basarisiz", "hata"):
            raise ValueError("yinelenen sonuç veya geçersiz durum")
        gelen[anahtar] = sonuc["durum"]
    if set(gelen) != beklenen:
        raise ValueError("sonuçlar deneme planıyla eşleşmiyor")
    rapor = {"deneme": len(plan), "gecerli_saldiri": 0, "basari": 0, "saldiri_hatasi": 0, "kontrol": 0, "saglam_kontrol": 0, "asr": None}
    for adim in plan:
        durum = gelen[(adim["vaka_id"], adim["tekrar"])]
        if adim["hedef"] is None:
            rapor["kontrol"] += 1
            if durum == "basarisiz":
                rapor["saglam_kontrol"] += 1
        elif durum == "hata":
            rapor["saldiri_hatasi"] += 1
        else:
            rapor["gecerli_saldiri"] += 1
            if durum == "basari":
                rapor["basari"] += 1
    if rapor["gecerli_saldiri"]:
        rapor["asr"] = rapor["basari"] / rapor["gecerli_saldiri"]
    return rapor

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_05 as deney
    deney.goster(set_imzala, asr_olc)
```

```hint
İlk görevdeki kanonik JSON seçenekleri ve üçüncü görevdeki (vaka_id, tekrar) anahtarı değişmez; yalnız girdiler artık gerçek kampanyadan gelir.
```
:::


::: anlat Bunu iki dakikada nasıl anlatırsın?
Deneyden önce saldırı setini ve bütçeyi sabitle. Kanonik imza JSON anahtar sırasını önemsizleştirirken vaka sırası ve içerik değişimini görünür kılar. Plan ve sonuçlar bire bir eşleşsin; kayıp, çift veya bilinmeyen sonuçta ASR üretme. Hataları geçerli saldırı paydasından ayır, kontrolü ayrı raporla. Promptfoo’nun yanıt var testiyle canary başarı sınıflandırıcısı aynı ölçüm değildir.

Önkoşul ve yol köprüsü: ai-saldiri-04 taksonomi ve ai-saldiri-02 canary.

| Yaygın yanlış | Mekanizma ve sınır |
|---|---|
| CLI yeşilse jailbreak başarılıdır | Araç kabul ölçütüyle saldırı başarı ölçütü farklı olabilir |

Dinleyiciye sor: Hangi kaydın kaybolması bu deneyin sonucunu doğrulanamaz yapar? Ham veri, model önerisi ve gerçek yan etkiyi ayrı göstererek cevapla.
:::


::: anlat Birincil kaynak ve deney sınırı
[Promptfoo Configuration Reference](https://www.promptfoo.dev/docs/configuration/reference/): Provider/prompt/test kampanya düzeni için araç referansı. Vaka imzası, sabit deneme planı ve ASR sınıflandırması dersin ayrı ölçüm sözleşmesidir.
:::
