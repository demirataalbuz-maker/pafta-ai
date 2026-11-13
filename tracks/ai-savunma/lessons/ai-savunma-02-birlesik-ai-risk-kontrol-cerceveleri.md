---
id: ai-savunma-02
title: Birleşik AI Risk ve Kontrol Çerçeveleri
summary: OWASP LLM, MITRE ATLAS ve NIST AI RMF eşlemelerini normalize et, kontrol matrisi kur ve test kanıtlarıyla kapsam durumunu hesapla.
timeout: 45
esleme: ai-saldiri-03, ai-saldiri-36
---

::: anlat Çerçeveler farklı sorulara cevap verir

| Gerçek araç / model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| OWASP Top 10 for LLM, MITRE ATLAS ve NIST AI RMF kurumsal yapay zekâ risk ve kontrol standartlarını tanımlar | İlk 3 görev çapraz çerçeve eşlemeleri, sahip atamalı kontrol matrisi ve test kanıtlı güvence raporu | Yasal uyumluluk (EU AI Act, ISO 42001) denetim sertifikası veya sızma testi bağışıklık garantisi değildir |
| Ollama yerel LLM ve canary enjeksiyon testleri canlı model güvenliğini ve prompt sızıntısını ölçer | Gerçek deney LLM01 kontrolü için gerçek model üzerinde canary sızıntı deneyiyle güvence kanıtı üretir | Çok aşamalı jailbreak saldırılarına karşı mutlak direnç veya sıfır gün zafiyetlerine karşı tam koruma kanıtı değildir |

> [!NOT]
> `veri/cerceve.json` dosyası sentetik risk eşleme, kontrol matrisi ve test kanıtı kayıtlarını içerir; resmi kurumsal uyumluluk veya canlı telemetri verisi değildir. İlk 3 görev bu yerel fixture verisini okur. Her Run/Check işleminde `hazirla("ai-savunma-02")` geçici kopya oluşturur; kalıcı değişiklik saklanmaz. Kodunuzu veya verinizi editörde inceleyebilirsiniz. Gizli değerlendirme testleri ayrı doğrulamalar koşturur. Gerçek deney adımı kurulu Ollama ve yerel modeli doğrudan çağırır; yeni paket veya model indirilmez.

Kurumsal ortamlarda yapay zekâ sistemlerinin güvenliğini sağlamak, tek bir mühendislik ekibinin veya tek bir güvenlik uzmanının altından kalkabileceği bir görev değildir. Bir yapay zekâ uygulamasının yaşam döngüsünde farklı disiplinler farklı sorular sorar ve farklı kavram setleriyle çalışır. CISO ve risk yöneticileri "Hangi risk başlıklarına maruz kalıyoruz?", güvenlik operasyonları ve kırmızı takımlar (red team) "Saldırgan sistemimize hangi taktik ve tekniklerle saldırabilir?", uyumluluk ve iç denetim ekipleri ise "Bu riskleri yönetişimin ve süreçlerin hangi aşamasında kontrol altına alıyoruz?" sorularına yanıt arar. Eğer bu ekipler birbirinden kopuk çalışırsa, güvenlik çalışmaları silolar hâlinde yürütülür; kontroller mükerrer yazılır veya daha kötüsü, bazı kritik riskler bütünüyle sahipsiz kalır. Bu derste modern siber güvenlik mimarisinde kabul gören üç ana çerçeveyi—OWASP Top 10 for LLM, MITRE ATLAS ve NIST AI RMF—birleşik bir kontrol matrisinde ve test kanıtlarıyla harmanlayan güvence mimarisini inceliyoruz.

Bu üç çerçeve birbirinin alternatifi veya rakibi değildir; aksine birbirini tamamlayan üç farklı boyuttur:
1. OWASP Top 10 for LLM (Risk Boyutu): LLM tabanlı uygulamalarda neyin yanlış gidebileceğini, sistemin hangi temel zaaflara sahip olduğunu kategorize eder. `LLM01` (Prompt Injection) seviyesinden `LLM10` seviyesine kadar uzanan 10 temel risk başlığı tanımlar. Numaralar sürüme göre değişir: 2023 (v1.1) listesinde `LLM10` "Model Theft" iken 2025 listesinde "Unbounded Consumption" olmuştur; bu yüzden bir eşlemede liste sürümü de kaydedilmelidir. Bu kimlikler standart olarak `LLM01`–`LLM10` biçiminde çift haneli rakamlarla ifade edilir.
2. MITRE ATLAS (Saldırı Tekniği Boyutu): Adversarial Threat Landscape for AI Systems projesi, saldırganların makine öğrenimi ve LLM sistemlerini hedef alırken kullandığı somut taktik ve teknikleri listeler. Örneğin prompt enjeksiyonu riski (`LLM01`), ATLAS kapsamında `AML.T0051` (LLM Prompt Injection) ve `AML.T0054` (LLM Jailbreak) gibi birden çok teknikle gerçekleştirilebilir. Her teknik kimliği `AML.T` ön eki ve dört haneli sayıdan oluşur.
3. NIST AI RMF (Yönetişim ve Süreç Boyutu): National Institute of Standards and Technology Yapay Zekâ Risk Yönetim Çerçevesi, yapay zekâ risklerinin kurumsal yaşam döngüsünde hangi aşamada ele alınacağını dört temel işlevle tanımlar:
   - `GOVERN` (Yönetişim): Kurumsal kültür, politikalar, roller ve yasal sorumlulukların belirlenmesi.
   - `MAP` (Haritalama): Sistemin bağlamının, paydaşlarının, sınırlarının ve potansiyel risklerinin tespit edilmesi.
   - `MEASURE` (Ölçme): Risklerin, performans metriklerinin, testlerin ve değerlendirme araçlarının işletilmesi.
   - `MANAGE` (Yönetme): Önceliklendirilen risklere karşı kontrollerin uygulanması, izlenmesi ve hafifletilmesi.

Bir risk tek bir çerçeve maddesiyle sınırlı kalmaz; birden çok ATLAS saldırı tekniği barındırabilir ve birden çok NIST işlevinde çalışma gerektirebilir. Bu eşlemelerin kayıp ve yinelenme olmadan normalize edilmesi, kurumsal risk haritasının omurgasını oluşturur. Ancak kâğıt üzerindeki eşlemeler tek başına koruma sağlamaz; bu eşlemelerin somut kontrollere (`kontroller`) ve her kontrolün açık bir sahibe (`sahip`) bağlanması şarttır. Sahibi belirlenmemiş bir güvenlik kontrolü, hiçbir zaman işletilmeyen ölü bir kuraldan ibarettir. Kontrol kimlikleri `K-` ön ekiyle tanımlanır (örneğin `K-GIRD-1`, `K-DLP-2`) ve kontrolün ait olduğu NIST işlevi, riskin normalize eşlemesinde yer alan işlevlerden biri olmak zorundadır. Eğer bir risk için tanımlanmış hiçbir kontrol yoksa, o risk `kontrolsuz` olarak işaretlenir. Kontrolsüz riskleri rapordan gizlemek veya silmek, kuruma sahte bir güvence hissi verir ve en tehlikeli yönetim tuzağıdır.

Daha da önemlisi: Bir kontrolün matriste yer alması, o kontrolün çalıştığını veya etkili olduğunu kanıtlamaz. Güvenlik mühendisliğinde temel kural "Doğrulanmamış kontrol, mevcut olmayan kontroldür" ilkesidir. Her kontrol için yürütülen testlerin sonuçları (`gecti`, `kaldi`, `uygulanmadi`) toplanmalı ve riskin genel güvence durumu katı bir öncelik sırasıyla hesaplanmalıdır:
- `kontrolsuz`: Risk için matriste hiçbir kontrol tanımlanmamıştır.
- `kritik`: Tanımlı kontrollerden en az bir tanesinin testi başarısız olmuştur (`kaldi`). Diğer kontroller geçmiş olsa bile tek bir başarısız test tüm riski kritik seviyeye çeker.
- `eksik_kanit`: Başarısız kontrol yoktur ancak bazı kontrollerin testi hiç yapılmamıştır (`test_yok`) veya test uygulanmamıştır (`uygulanmadi`).
- `kapsali`: Riskin tüm kontrolleri test edilmiş ve tamamı başarıyla geçmiştir (`gecti`).

Saldırganlar kurumsal AI mimarilerini hedeflerken şu açık noktaları istismar eder:
- Kâğıt Üzerinde Uyum (Paper Compliance) Açıkları: Şirketin politika belgelerinde "prompt enjeksiyonu engellenmektedir" yazmasına rağmen, gerçekte kontrolün test kanıtının bulunmamasını (`eksik_kanit`) fırsat bilerek doğrudan enjeksiyon denemeleri yapmak.
- Sorumluluk Boşlukları (Ownership Gaps): Geliştirme ekibi ile altyapı ekibi arasında sahibi netleştirilmemiş kontrollerin güncellenmemesini veya bypass edilmesini istismar etmek.
- Canary ve Sistem İpucu Sızıntısı: Modele sağlanan gizli sistem promptunu veya gizli anahtarları dışarı sızdırmak için dolaylı manipülasyonlar yürütmek.

Geliştiricilerin sık yaptığı hatalar:
- Kontrol Varlığını Güvence Zannetmek: Test kanıtı olmadan matrise eklenen her kontrolü başarılı kabul etmek.
- Durum Önceliklerini Karıştırmak: Bir kontrol kaldığında (`kaldi`), diğer üç kontrol geçtiği için çoğunluk kuralına dayanıp riski "kapsalı" veya "orta" ilan etmek.
- Uygulanmamış Teste Kanıt Yazmak: `uygulanmadi` durumundaki bir teste içi dolu açıklama koyarak test sözleşmesini bozmak.
- Girdi Verilerini Değiştirmek: Parametre listelerini yerinde sıralayarak çağıran uygulamanın belleğini kirletmek.
:::

::: tahmin Normalize etme sıra ve yinelenmeyi yönetir
Üç çıktı satırını yaz:

```python
print(sorted(["MANAGE", "MAP"]))
print(len({"AML.T0051", "AML.T0051"}))
print("LLM01" == "LLM1")
```

???

```cikti
['MANAGE', 'MAP']
1
False
```

Sıfırlı risk kimliği normalize edilirken başka bir biçime çevrilmez; kimlik aynen korunur.
:::

::: gorev 1 · Çoklu çerçeve eşlemelerini normalize et
`risk_eslemelerini_normalize(kayitlar)` işlevini yaz. Girdi liste olmalı; her kayıt tam olarak `owasp`, `atlas`, `nist` alanlarını taşımalıdır. `owasp`, `LLM01`–`LLM10` aralığında benzersiz bir stringdir. `atlas`, boş olmayan ve yinelenmeyen teknik kimlikleri listesidir; her kimlik `AML.T` sonrası tam dört rakam içerir. `nist`, boş olmayan ve yinelenmeyen `GOVERN`, `MAP`, `MEASURE`, `MANAGE` değerleri listesidir. Geçersiz veride `ValueError` yükselt.

Her kaydın `owasp`, `atlas`, `nist` alanlarını yeni bir sözlükte döndür; ATLAS ve NIST listelerini alfabetik, riskleri OWASP kimliğine göre sırala. Boş girdi için boş liste döndür ve girdiyi değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-02")
```

```starter
from ai_savunma_veri import json_yukle

def risk_eslemelerini_normalize(kayitlar):
    # KUSURLU BAŞLANGIÇ KODU: şema doğrulaması yapmaz, ATLAS ve NIST listelerini alfabetik sıralamaz ve OWASP sırasını bozabilir.
    return [{"owasp": k.get("owasp"), "atlas": k.get("atlas", []), "nist": k.get("nist", [])} for k in (kayitlar or [])]

v = json_yukle("veri/cerceve.json")["eslemeler"]
print("Normalize eşlemeler örneği:", risk_eslemelerini_normalize(v))
```

```test
import copy
KAYITLAR = [
    {"owasp": "LLM06", "atlas": ["AML.T0051", "AML.T0024"], "nist": ["MANAGE", "GOVERN"]},
    {"owasp": "LLM01", "atlas": ["AML.T0054", "AML.T0051"], "nist": ["MEASURE", "MANAGE", "MAP"]},
]
BEKLENEN = [
    {"owasp": "LLM01", "atlas": ["AML.T0051", "AML.T0054"], "nist": ["MANAGE", "MAP", "MEASURE"]},
    {"owasp": "LLM06", "atlas": ["AML.T0024", "AML.T0051"], "nist": ["GOVERN", "MANAGE"]},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(KAYITLAR)
        if fn(KAYITLAR) != BEKLENEN or KAYITLAR != once or fn(list(reversed(KAYITLAR))) != BEKLENEN:
            return False
        if fn([]) != []:
            return False
        for kayitlar in [
            None, {}, [None], [dict(KAYITLAR[0], ek=1)],
            [dict(KAYITLAR[0], owasp="LLM1")], [dict(KAYITLAR[0], owasp="LLM11")],
            [dict(KAYITLAR[0], owasp=None)], [dict(KAYITLAR[0], atlas=[])],
            [dict(KAYITLAR[0], atlas="AML.T0051")],
            [dict(KAYITLAR[0], atlas=["AML.T051"])],
            [dict(KAYITLAR[0], atlas=["AML.T00051"])],
            [dict(KAYITLAR[0], atlas=["AML.T0051", "AML.T0051"])],
            [dict(KAYITLAR[0], nist=[])], [dict(KAYITLAR[0], nist=["OPERATE"])],
            [dict(KAYITLAR[0], nist=["MAP", "MAP"])], [dict(KAYITLAR[0], nist="MAP")],
            [KAYITLAR[0], KAYITLAR[0]],
        ]:
            try:
                fn(kayitlar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(risk_eslemelerini_normalize), "kimlik biçimleri, çoklu eşlemeler ve sıralama korunmalı")
def m_nist(kayitlar):
    sonuc = risk_eslemelerini_normalize(kayitlar)
    for x in sonuc:
        x["nist"] = ["MAP"]
    return sonuc
def m_atlas(kayitlar):
    sonuc = risk_eslemelerini_normalize(kayitlar)
    for x in sonuc:
        x["atlas"].reverse()
    return sonuc
def m_risk(kayitlar):
    sonuc = risk_eslemelerini_normalize(kayitlar)
    sonuc.reverse()
    return sonuc
for ad, mutant in [("NIST eşlemesini kaybeden", m_nist), ("ATLAS sırasını bozan", m_atlas), ("risk sırasını bozan", m_risk)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
# --- carbon-c8-ek-bas ---
raises(ValueError, risk_eslemelerini_normalize, [dict(KAYITLAR[0], owasp=123)], msg="owasp str olmalı")
for _a02 in KAYITLAR[0]:
    if _a02 != "owasp" and isinstance(KAYITLAR[0][_a02], str):
        raises(ValueError, risk_eslemelerini_normalize, [dict(KAYITLAR[0], **{_a02: 123})], msg=f"{_a02} str olmalı")
raises(ValueError, risk_eslemelerini_normalize, [dict(KAYITLAR[0], atlas=("AML.T0051",))], msg="atlas tuple olamaz")
raises(ValueError, risk_eslemelerini_normalize, [dict(KAYITLAR[0], atlas=[123])], msg="atlas elemanı str olmalı")
raises(ValueError, risk_eslemelerini_normalize, [dict(KAYITLAR[0], nist=("GOVERN",))], msg="nist tuple olamaz")
# --- carbon-c8-ek-son ---
```

```solution
def risk_eslemelerini_normalize(kayitlar):
    import re
    if not isinstance(kayitlar, list):
        raise ValueError("kayıt listesi geçersiz")
    sonuc = []
    riskler = set()
    for kayit in kayitlar:
        if not isinstance(kayit, dict):
            raise ValueError("kayıt geçersiz")
        if set(kayit) != {"owasp", "atlas", "nist"}:
            raise ValueError("kayıt şeması geçersiz")
        owasp = kayit["owasp"]
        if not isinstance(owasp, str):
            raise ValueError("OWASP kimliği geçersiz")
        if not re.fullmatch(r"LLM(0[1-9]|10)", owasp):
            raise ValueError("OWASP kimliği geçersiz")
        if owasp in riskler:
            raise ValueError("OWASP kimliği yinelenemez")
        riskler.add(owasp)
        atlas = kayit["atlas"]
        if not isinstance(atlas, list) or not atlas:
            raise ValueError("ATLAS listesi geçersiz")
        if len(set(atlas)) != len(atlas):
            raise ValueError("ATLAS kimliği yinelenemez")
        for teknik in atlas:
            if not isinstance(teknik, str):
                raise ValueError("ATLAS kimliği geçersiz")
            if not re.fullmatch(r"AML.T[0-9]{4}", teknik):
                raise ValueError("ATLAS kimliği geçersiz")
        nist = kayit["nist"]
        if not isinstance(nist, list) or not nist:
            raise ValueError("NIST listesi geçersiz")
        if len(set(nist)) != len(nist):
            raise ValueError("NIST işlevi yinelenemez")
        for fonksiyon in nist:
            if fonksiyon not in ("GOVERN", "MAP", "MEASURE", "MANAGE"):
                raise ValueError("NIST işlevi geçersiz")
        sonuc.append({"owasp": owasp, "atlas": sorted(atlas), "nist": sorted(nist)})
    return sorted(sonuc, key=lambda x: x["owasp"])
```

```hint
Her listeyi önce tür, boşluk ve yinelenme bakımından doğrula. Kimlikleri değiştirmeden `sorted` ile yeni listeler oluştur.
```
:::

::: anlat Kontrol matrisi eşlemeyi sorumluya bağlar
Bir çapraz referans ancak uygulanabilir kontrollere dönüşürse savunma çalışmasını yönlendirir. Her kontrolün benzersiz kimliği, açık adı, sahibi, ilişkili OWASP riski ve NIST işlevi olmalıdır. Kontrolün NIST işlevi, risk eşlemesinde bulunmayan yeni bir ilişkiymiş gibi sessizce eklenemez.

Matris, kontrolü olmayan riskleri de korur. Bu kayıtları atmak kapsamı olduğundan iyi gösterir; `kontrolsuz` listesi tamamlanmamış savunma işini görünür kılar.
:::

::: gorev 2 · Sahipleri ve NIST işlevleri doğrulanmış kontrol matrisi kur
`kontrol_matrisi_kur(eslemeler, kontroller)` işlevini yaz. `eslemeler`, ilk görevin normalize edilmiş çıktısıdır ve aynı kuralları sağlamalıdır. Her kontrol tam olarak `id`, `owasp`, `ad`, `sahip`, `nist` alanlarını taşısın. Kimlik `K-` ile başlayıp en az bir büyük ASCII harf, rakam veya tire içeren benzersiz stringdir. Ad ve sahip, baş/son boşluğu olmayan boş olmayan stringlerdir. OWASP kimliği kayıtlı olmalı; NIST işlevi o riskin eşlemesinde bulunmalıdır. Geçersiz veride `ValueError` yükselt.

Dönüş:

```text
{"riskler":[{"owasp":R,"atlas":[...],"nist":[...],
 "kontroller":[{"id":K,"ad":AD,"sahip":S,"nist":N},...]},...],
 "kontrolsuz":[R,...]}
```

Riskleri ve kontrolsüz listesini OWASP kimliğine, kontrolleri kontrol kimliğine göre sırala. Kontrol kaydında `owasp` alanını tekrar etme. Girdileri değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-02")
```

```starter
from ai_savunma_veri import json_yukle

def kontrol_matrisi_kur(eslemeler, kontroller):
    # KUSURLU BAŞLANGIÇ KODU: kontrolleri risklerle eşleştirmez, kontrolsüz risk listesini boş döner ve sıralama yapmaz.
    return {"riskler": [{"owasp": e.get("owasp"), "atlas": e.get("atlas", []), "nist": e.get("nist", []), "kontroller": []} for e in (eslemeler or [])], "kontrolsuz": []}

veri = json_yukle("veri/cerceve.json")
e, k = veri["eslemeler"], veri["kontroller"]
print("Örnek kontrol matrisi:", kontrol_matrisi_kur(e, k))
```

```test
import copy
E = [
    {"owasp": "LLM01", "atlas": ["AML.T0051"], "nist": ["MANAGE", "MAP"]},
    {"owasp": "LLM06", "atlas": ["AML.T0024"], "nist": ["GOVERN"]},
]
K = [
    {"id": "K-GIRD-2", "owasp": "LLM01", "ad": "Boyut sınırı", "sahip": "Platform", "nist": "MAP"},
    {"id": "K-GIRD-1", "owasp": "LLM01", "ad": "Şema kontrolü", "sahip": "Uygulama", "nist": "MANAGE"},
]
BEKLENEN = {"riskler": [
    {"owasp": "LLM01", "atlas": ["AML.T0051"], "nist": ["MANAGE", "MAP"], "kontroller": [
        {"id": "K-GIRD-1", "ad": "Şema kontrolü", "sahip": "Uygulama", "nist": "MANAGE"},
        {"id": "K-GIRD-2", "ad": "Boyut sınırı", "sahip": "Platform", "nist": "MAP"},
    ]},
    {"owasp": "LLM06", "atlas": ["AML.T0024"], "nist": ["GOVERN"], "kontroller": []},
], "kontrolsuz": ["LLM06"]}
def sozlesme(fn):
    try:
        once = copy.deepcopy((E, K))
        if fn(E, K) != BEKLENEN or (E, K) != once or fn(E, list(reversed(K))) != BEKLENEN:
            return False
        bos = fn(E, [])
        if bos["kontrolsuz"] != ["LLM01", "LLM06"] or any(x["kontroller"] for x in bos["riskler"]):
            return False
        for eslemeler, kontroller in [
            (None, []), (E, None), (E, [None]), (E, [dict(K[0], ek=1)]),
            (E, [dict(K[0], id="GIRD-1")]), (E, [dict(K[0], id="K-")]),
            (E, [dict(K[0], id=None)]), (E, [dict(K[0], owasp="LLM09")]),
            (E, [dict(K[0], ad="")]), (E, [dict(K[0], ad=" x")]),
            (E, [dict(K[0], sahip=None)]), (E, [dict(K[0], nist="GOVERN")]),
            (E, [K[0], K[0]]), ([dict(E[0], owasp="LLM11")], []),
            ([dict(E[0], atlas=["AML.T00051"])], []),
            ([dict(E[0], nist=["OPERATE"])], []),
        ]:
            try:
                fn(eslemeler, kontroller)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(kontrol_matrisi_kur), "kontrol sahipliği, risk-NIST ilişkisi ve kontrolsüz riskler korunmalı")
def m_sahip(eslemeler, kontroller):
    sonuc = kontrol_matrisi_kur(eslemeler, kontroller)
    for r in sonuc["riskler"]:
        for k in r["kontroller"]:
            k["sahip"] = "bilinmiyor"
    return sonuc
def m_kapsam(eslemeler, kontroller):
    sonuc = kontrol_matrisi_kur(eslemeler, kontroller)
    sonuc["riskler"] = [r for r in sonuc["riskler"] if r["kontroller"]]
    sonuc["kontrolsuz"] = []
    return sonuc
def m_nist(eslemeler, kontroller):
    degisen = [dict(k, nist="MAP") for k in kontroller]
    return kontrol_matrisi_kur(eslemeler, degisen)
for ad, mutant in [("kontrol sahibini kaybeden", m_sahip), ("kontrolsüz riski silen", m_kapsam), ("NIST ilişkisini değiştiren", m_nist)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

raises(ValueError,kontrol_matrisi_kur,E,[dict(K[0],sahip=' Platform ')]+K[1:],msg='kontrol sahibi baş/son boşluğu ret')
# --- carbon-c8-ek-bas ---
raises(ValueError, kontrol_matrisi_kur, [dict(E[0], owasp=123)] + E[1:], K, msg="eşleme owasp str olmalı")
raises(ValueError, kontrol_matrisi_kur, [dict(E[0], atlas="AML.T0051")] + E[1:], K, msg="atlas liste olmalı")
raises(ValueError, kontrol_matrisi_kur, [dict(E[0], atlas=[])] + E[1:], K, msg="boş atlas ret")
raises(ValueError, kontrol_matrisi_kur, [dict(E[0], atlas=[123])] + E[1:], K, msg="atlas str olmalı")
raises(ValueError, kontrol_matrisi_kur, [dict(E[0], nist="GOVERN")] + E[1:], K, msg="nist liste olmalı")
raises(ValueError, kontrol_matrisi_kur, [dict(E[0], nist=[])] + E[1:], K, msg="boş nist ret")
raises(ValueError, kontrol_matrisi_kur, E, [dict(K[0], id=123)] + K[1:], msg="kontrol id str olmalı")
raises(ValueError, kontrol_matrisi_kur, E, [dict(K[0], ad=123)] + K[1:], msg="kontrol ad str olmalı")
raises(ValueError, kontrol_matrisi_kur, E, [dict(K[0], ad=" ad ")] + K[1:], msg="kontrol ad trim ret")
raises(ValueError, kontrol_matrisi_kur, E, [dict(K[0], sahip=123)] + K[1:], msg="sahip str olmalı")
raises(ValueError, kontrol_matrisi_kur, [123], K, msg="eşleme dict olmalı")
raises(ValueError, kontrol_matrisi_kur, [dict(E[0], ek=1)] + E[1:], K, msg="eşleme fazla alan ret")
raises(ValueError, kontrol_matrisi_kur, [E[0], E[0]], K, msg="yinelenen OWASP ret")
raises(ValueError, kontrol_matrisi_kur, [dict(E[0], atlas=("AML.T0051",))] + E[1:], K, msg="atlas tuple olamaz")
raises(ValueError, kontrol_matrisi_kur, [dict(E[0], atlas=["AML.T0054", "AML.T0051"])] + E[1:], K, msg="sırasız atlas ret")
raises(ValueError, kontrol_matrisi_kur, [dict(E[0], nist=("GOVERN",))] + E[1:], K, msg="nist tuple olamaz")
raises(ValueError, kontrol_matrisi_kur, [dict(E[0], nist=["MAP", "GOVERN"])] + E[1:], K, msg="sırasız nist ret")
raises(ValueError, kontrol_matrisi_kur, E, [dict(K[0], sahip="")] + K[1:], msg="boş sahip ret")
raises(ValueError, kontrol_matrisi_kur, [dict(E[0], atlas=123)], [], msg="atlas list değil int olamaz")
raises(ValueError, kontrol_matrisi_kur, [dict(E[0], nist=123)], [], msg="nist list değil int olamaz")
raises(ValueError, kontrol_matrisi_kur, [dict(E[0], nist=[])], [], msg="boş nist listesi ret")
raises(ValueError, kontrol_matrisi_kur, [dict(E[0], nist=["MAP", "GOVERN"])], [], msg="sırasız nist listesi ret")
# --- carbon-c8-ek-son ---
```

```solution
def kontrol_matrisi_kur(eslemeler, kontroller):
    import re
    if not isinstance(eslemeler, list):
        raise ValueError("eşleme listesi geçersiz")
    if not isinstance(kontroller, list):
        raise ValueError("kontrol listesi geçersiz")
    matris = {}
    for e in eslemeler:
        if not isinstance(e, dict):
            raise ValueError("eşleme geçersiz")
        if set(e) != {"owasp", "atlas", "nist"}:
            raise ValueError("eşleme şeması geçersiz")
        if not isinstance(e["owasp"], str):
            raise ValueError("OWASP kimliği geçersiz")
        if not re.fullmatch(r"LLM(0[1-9]|10)", e["owasp"]):
            raise ValueError("OWASP kimliği geçersiz")
        if e["owasp"] in matris:
            raise ValueError("OWASP kimliği yinelenemez")
        if not isinstance(e["atlas"], list):
            raise ValueError("ATLAS listesi geçersiz")
        if not e["atlas"]:
            raise ValueError("ATLAS listesi boş olamaz")
        if e["atlas"] != sorted(set(e["atlas"])):
            raise ValueError("ATLAS listesi normalize değil")
        for a in e["atlas"]:
            if not isinstance(a, str):
                raise ValueError("ATLAS kimliği geçersiz")
            if not re.fullmatch(r"AML.T[0-9]{4}", a):
                raise ValueError("ATLAS kimliği geçersiz")
        if not isinstance(e["nist"], list):
            raise ValueError("NIST listesi geçersiz")
        if not e["nist"]:
            raise ValueError("NIST listesi boş olamaz")
        if e["nist"] != sorted(set(e["nist"])):
            raise ValueError("NIST listesi normalize değil")
        for n in e["nist"]:
            if n not in ("GOVERN", "MAP", "MEASURE", "MANAGE"):
                raise ValueError("NIST işlevi geçersiz")
        matris[e["owasp"]] = {"owasp": e["owasp"], "atlas": list(e["atlas"]), "nist": list(e["nist"]), "kontroller": []}
    kimlikler = set()
    for k in kontroller:
        if not isinstance(k, dict):
            raise ValueError("kontrol geçersiz")
        if set(k) != {"id", "owasp", "ad", "sahip", "nist"}:
            raise ValueError("kontrol şeması geçersiz")
        if not isinstance(k["id"], str):
            raise ValueError("kontrol kimliği geçersiz")
        if not re.fullmatch(r"K-[A-Z0-9-]+", k["id"]):
            raise ValueError("kontrol kimliği geçersiz")
        if k["id"] in kimlikler:
            raise ValueError("kontrol kimliği yinelenemez")
        if k["owasp"] not in matris:
            raise ValueError("kontrol riski geçersiz")
        if not isinstance(k["ad"], str):
            raise ValueError("kontrol adı geçersiz")
        if not k["ad"]:
            raise ValueError("kontrol adı boş olamaz")
        if k["ad"] != k["ad"].strip():
            raise ValueError("kontrol adı boşluklu olamaz")
        if not isinstance(k["sahip"], str):
            raise ValueError("kontrol sahibi geçersiz")
        if not k["sahip"]:
            raise ValueError("kontrol sahibi boş olamaz")
        if k["sahip"] != k["sahip"].strip():
            raise ValueError("kontrol sahibi boşluklu olamaz")
        if k["nist"] not in matris[k["owasp"]]["nist"]:
            raise ValueError("kontrol NIST ilişkisi geçersiz")
        kimlikler.add(k["id"])
        matris[k["owasp"]]["kontroller"].append({"id": k["id"], "ad": k["ad"], "sahip": k["sahip"], "nist": k["nist"]})
    riskler = [matris[r] for r in sorted(matris)]
    for r in riskler:
        r["kontroller"].sort(key=lambda x: x["id"])
    return {"riskler": riskler, "kontrolsuz": [r["owasp"] for r in riskler if not r["kontroller"]]}
```

```hint
Önce risk kimliğinden matris kaydına bir sözlük kur. Her kontrolü riskin mevcut NIST listesiyle karşılaştır, sonra kontrolleri kimliğe göre sırala.
```
:::

::: anlat Matrisin varlığı kanıtın yerine geçmez
Kontrolün yazılmış olması, çalıştığı anlamına gelmez. Her kontrol için en fazla bir güncel test sonucu kabul eden fixture'da `gecti`, `kaldi` ve `uygulanmadi` durumları ayrılır. Başarılı veya başarısız testin boş olmayan kanıt açıklaması; uygulanmamış testin ise boş kanıt alanı olmalıdır.

Risk durumu şu öncelikle hesaplanır: kontrol yoksa `kontrolsuz`; en az bir başarısız test varsa `kritik`; testi olmayan veya uygulanmamış kontrol varsa `eksik_kanit`; bütün kontroller başarılıysa `kapsali`. `kapsali`, sistemin mutlaka güvenli olduğu değil, tanımlı kontrollerin bu fixture'da kanıtlandığı anlamına gelir.
:::

::: gorev 3 · Test kanıtlarından risk güvence durumunu üret
`risk_guvence_raporu(eslemeler, kontroller, testler)` işlevini yaz. Eşlemeler ve kontroller ikinci görevdeki bütün kuralları sağlasın. Her test tam olarak `kontrol`, `durum`, `kanit` alanlarını taşısın. Kontrol kimliği kayıtlı ve testler arasında benzersiz olmalıdır. Durum `gecti` veya `kaldi` ise kanıt baş/son boşluğu olmayan boş olmayan string; `uygulanmadi` ise kanıt boş string olmalıdır. Geçersiz veride `ValueError` yükselt.

Her risk için `owasp`, `toplam`, `gecti`, `kaldi`, `uygulanmadi`, `test_yok`, `durum` alanlarını döndür. Durumu yukarıdaki öncelikle belirle. Son sözlük:

```text
{"riskler":[RISK_RAPORLARI],
 "ozet":{"kapsali":N,"eksik_kanit":N,"kritik":N,"kontrolsuz":N}}
```

Riskleri OWASP kimliğine göre sırala, özet sayaçlarını risk durumlarından üret ve girdileri değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-02")
```

```starter
from ai_savunma_veri import json_yukle

def risk_guvence_raporu(eslemeler, kontroller, testler):
    # KUSURLU BAŞLANGIÇ KODU: durum önceliklerini dikkate almaz, tüm riskleri kapsalı raporlar ve özet sayaçlarını sıfırlar.
    return {"riskler": [{"owasp": e.get("owasp"), "toplam": 0, "gecti": 0, "kaldi": 0, "uygulanmadi": 0, "test_yok": 0, "durum": "kapsali"} for e in (eslemeler or [])], "ozet": {"kapsali": len(eslemeler or []), "eksik_kanit": 0, "kritik": 0, "kontrolsuz": 0}}

veri = json_yukle("veri/cerceve.json")
e, k, t = veri["eslemeler"], veri["kontroller"], veri["testler"]
print("Örnek risk güvence raporu:", risk_guvence_raporu(e, k, t))
```

```test
import copy
E = [
    {"owasp": "LLM01", "atlas": ["AML.T0051"], "nist": ["MANAGE"]},
    {"owasp": "LLM02", "atlas": ["AML.T0024"], "nist": ["MEASURE"]},
    {"owasp": "LLM03", "atlas": ["AML.T0010"], "nist": ["GOVERN"]},
    {"owasp": "LLM04", "atlas": ["AML.T0054"], "nist": ["MAP"]},
]
K = [
    {"id": "K-A", "owasp": "LLM01", "ad": "Filtre", "sahip": "A", "nist": "MANAGE"},
    {"id": "K-B", "owasp": "LLM02", "ad": "Eval", "sahip": "B", "nist": "MEASURE"},
    {"id": "K-C", "owasp": "LLM02", "ad": "İnsan incelemesi", "sahip": "C", "nist": "MEASURE"},
    {"id": "K-D", "owasp": "LLM03", "ad": "İmza", "sahip": "D", "nist": "GOVERN"},
]
T = [
    {"kontrol": "K-A", "durum": "gecti", "kanit": "test-01"},
    {"kontrol": "K-B", "durum": "kaldi", "kanit": "test-02"},
    {"kontrol": "K-D", "durum": "uygulanmadi", "kanit": ""},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy((E, K, T))
        sonuc = fn(E, K, T)
        if (E, K, T) != once or sonuc != fn(E, list(reversed(K)), list(reversed(T))):
            return False
        if [x["durum"] for x in sonuc["riskler"]] != ["kapsali", "kritik", "eksik_kanit", "kontrolsuz"]:
            return False
        if sonuc["riskler"][1]["test_yok"] != 1 or sonuc["riskler"][1]["kaldi"] != 1:
            return False
        if sonuc["ozet"] != {"kapsali": 1, "eksik_kanit": 1, "kritik": 1, "kontrolsuz": 1}:
            return False
        hepsi = T + [{"kontrol": "K-C", "durum": "gecti", "kanit": "test-03"}]
        if fn(E, K, hepsi)["riskler"][1]["durum"] != "kritik":
            return False
        basarili = [{"kontrol": "K-A", "durum": "gecti", "kanit": "ok"}]
        if fn(E[:1], K[:1], basarili)["ozet"]["kapsali"] != 1:
            return False
        for eslemeler, kontroller, testler in [
            (E, K, None), (E, K, [None]), (E, K, [dict(T[0], ek=1)]),
            (E, K, [dict(T[0], kontrol="K-YOK")]),
            (E, K, [dict(T[0], durum="belirsiz")]),
            (E, K, [dict(T[0], kanit="")]), (E, K, [dict(T[0], kanit=" ok")]),
            (E, K, [dict(T[2], kanit="not")]), (E, K, [T[0], T[0]]),
            (None, K, T), (E, None, T), (E, [dict(K[0], owasp="LLM09")], T),
            ([dict(E[0], owasp="LLM11")], [], []),
        ]:
            try:
                fn(eslemeler, kontroller, testler)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(risk_guvence_raporu), "test kanıtları, durum önceliği ve risk sayaçları korunmalı")
def m_basari(eslemeler, kontroller, testler):
    degisen = [dict(t, durum="gecti") for t in testler]
    return risk_guvence_raporu(eslemeler, kontroller, degisen)
def m_testyok(eslemeler, kontroller, testler):
    return risk_guvence_raporu(eslemeler, kontroller, testler + [{"kontrol": "K-C", "durum": "gecti", "kanit": "ok"}])
def m_kontrolsuz(eslemeler, kontroller, testler):
    return risk_guvence_raporu(eslemeler[:3], kontroller, testler)
for ad, mutant in [("başarısız testi başarılı sayan", m_basari), ("eksik test kanıtını kapatan", m_testyok), ("kontrolsüz riski silen", m_kontrolsuz)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

raises(ValueError,risk_guvence_raporu,E,[dict(K[0],sahip=' Platform ')]+K[1:],T,msg='güvence kontrol sahibi baş/son boşluğu ret')
# --- carbon-c8-ek-bas ---
_k02_tek = [k for k in K if k["owasp"] == E[0]["owasp"]][:1]
eq(risk_guvence_raporu(E[:1], _k02_tek, [])["riskler"][0]["durum"], "eksik_kanit", "testi olmayan kontrol eksik_kanit olmalı")
raises(ValueError, risk_guvence_raporu, [dict(E[0], owasp=123)] + E[1:], K, T, msg="eşleme owasp str olmalı")
raises(ValueError, risk_guvence_raporu, [dict(E[0], atlas="AML.T0051")] + E[1:], K, T, msg="atlas liste olmalı")
raises(ValueError, risk_guvence_raporu, [dict(E[0], atlas=[])] + E[1:], K, T, msg="boş atlas ret")
raises(ValueError, risk_guvence_raporu, [dict(E[0], atlas=[123])] + E[1:], K, T, msg="atlas str olmalı")
raises(ValueError, risk_guvence_raporu, [dict(E[0], nist="GOVERN")] + E[1:], K, T, msg="nist liste olmalı")
raises(ValueError, risk_guvence_raporu, [dict(E[0], nist=[])] + E[1:], K, T, msg="boş nist ret")
raises(ValueError, risk_guvence_raporu, E, [dict(K[0], id=123)] + K[1:], T, msg="kontrol id str olmalı")
raises(ValueError, risk_guvence_raporu, E, [dict(K[0], ad=123)] + K[1:], T, msg="kontrol ad str olmalı")
raises(ValueError, risk_guvence_raporu, E, [dict(K[0], ad=" ad ")] + K[1:], T, msg="kontrol ad trim ret")
raises(ValueError, risk_guvence_raporu, E, [dict(K[0], sahip=123)] + K[1:], T, msg="sahip str olmalı")
for _tk02 in T[0]:
    if isinstance(T[0][_tk02], str):
        raises(ValueError, risk_guvence_raporu, E, K, [dict(T[0], **{_tk02: 123})] + T[1:], msg=f"test {_tk02} str olmalı")
raises(ValueError, risk_guvence_raporu, [123], K, T, msg="eşleme dict olmalı")
raises(ValueError, risk_guvence_raporu, [dict(E[0], ek=1)] + E[1:], K, T, msg="eşleme fazla alan ret")
raises(ValueError, risk_guvence_raporu, [E[0], E[0]], K, T, msg="yinelenen risk ret")
raises(ValueError, risk_guvence_raporu, [dict(E[0], atlas=("AML.T0051",))] + E[1:], K, T, msg="atlas tuple olamaz")
raises(ValueError, risk_guvence_raporu, [dict(E[0], atlas=["AML.T0054", "AML.T0051"])] + E[1:], K, T, msg="sırasız atlas ret")
raises(ValueError, risk_guvence_raporu, [dict(E[0], atlas=["AML.X9999"])] + E[1:], K, T, msg="geçersiz atlas biçimi ret")
raises(ValueError, risk_guvence_raporu, [dict(E[0], nist=("GOVERN",))] + E[1:], K, T, msg="nist tuple olamaz")
raises(ValueError, risk_guvence_raporu, [dict(E[0], nist=["MAP", "GOVERN"])] + E[1:], K, T, msg="sırasız nist ret")
raises(ValueError, risk_guvence_raporu, [dict(E[0], nist=["INVALID"])] + E[1:], K, T, msg="geçersiz nist işlevi ret")
raises(ValueError, risk_guvence_raporu, E, [123], T, msg="kontrol dict olmalı")
raises(ValueError, risk_guvence_raporu, E, [dict(K[0], ek=1)] + K[1:], T, msg="kontrol fazla alan ret")
raises(ValueError, risk_guvence_raporu, E, [dict(K[0], id="bad")] + K[1:], T, msg="geçersiz kontrol kimliği ret")
raises(ValueError, risk_guvence_raporu, E, [K[0], K[0]], T, msg="yinelenen kontrol kimliği ret")
raises(ValueError, risk_guvence_raporu, E, [dict(K[0], ad="")] + K[1:], T, msg="boş kontrol adı ret")
raises(ValueError, risk_guvence_raporu, E, [dict(K[0], sahip="")] + K[1:], T, msg="boş kontrol sahibi ret")
raises(ValueError, risk_guvence_raporu, [dict(E[0], nist=["GOVERN"])], [dict(K[0], owasp=E[0]["owasp"], nist="MANAGE")], [], msg="eşleşmeyen NIST ilişkisi ret")
raises(ValueError, risk_guvence_raporu, [E[0], E[0]], [], [], msg="yinelenen risk kimliği boş kontrol listesinde ret")
raises(ValueError, risk_guvence_raporu, [dict(E[0], atlas=123)], [], [], msg="atlas list değil int olamaz")
raises(ValueError, risk_guvence_raporu, [dict(E[0], nist=123)], [], [], msg="nist list değil int olamaz")
raises(ValueError, risk_guvence_raporu, [dict(E[0], nist=[])], [], [], msg="boş nist listesi ret")
raises(ValueError, risk_guvence_raporu, [dict(E[0], nist=["MAP", "GOVERN"])], [], [], msg="sırasız nist listesi ret")
raises(ValueError, risk_guvence_raporu, [dict(E[0], nist=["INVALID"])], [], [], msg="geçersiz nist işlevi ret")
raises(ValueError, risk_guvence_raporu, E, [dict(K[0], id="bad")], [], msg="geçersiz kontrol kimliği boş test listesinde ret")
raises(ValueError, risk_guvence_raporu, E, [K[0], K[0]], [], msg="yinelenen kontrol kimliği boş test listesinde ret")
# --- carbon-c8-ek-son ---
```

```solution
def risk_guvence_raporu(eslemeler, kontroller, testler):
    import re
    if not isinstance(eslemeler, list):
        raise ValueError("eşleme listesi geçersiz")
    if not isinstance(kontroller, list):
        raise ValueError("kontrol listesi geçersiz")
    if not isinstance(testler, list):
        raise ValueError("test listesi geçersiz")
    riskler = {}
    nist_esleme = {}
    for e in eslemeler:
        if not isinstance(e, dict):
            raise ValueError("eşleme geçersiz")
        if set(e) != {"owasp", "atlas", "nist"}:
            raise ValueError("eşleme şeması geçersiz")
        if not isinstance(e["owasp"], str):
            raise ValueError("OWASP kimliği geçersiz")
        if not re.fullmatch(r"LLM(0[1-9]|10)", e["owasp"]):
            raise ValueError("OWASP kimliği geçersiz")
        if e["owasp"] in riskler:
            raise ValueError("risk yinelenemez")
        if not isinstance(e["atlas"], list):
            raise ValueError("ATLAS listesi geçersiz")
        if not e["atlas"]:
            raise ValueError("ATLAS listesi boş olamaz")
        if e["atlas"] != sorted(set(e["atlas"])):
            raise ValueError("ATLAS listesi normalize değil")
        for a in e["atlas"]:
            if not isinstance(a, str):
                raise ValueError("ATLAS kimliği geçersiz")
            if not re.fullmatch(r"AML.T[0-9]{4}", a):
                raise ValueError("ATLAS kimliği geçersiz")
        if not isinstance(e["nist"], list):
            raise ValueError("NIST listesi geçersiz")
        if not e["nist"]:
            raise ValueError("NIST listesi boş olamaz")
        if e["nist"] != sorted(set(e["nist"])):
            raise ValueError("NIST listesi normalize değil")
        for n in e["nist"]:
            if n not in ("GOVERN", "MAP", "MEASURE", "MANAGE"):
                raise ValueError("NIST işlevi geçersiz")
        riskler[e["owasp"]] = []
        nist_esleme[e["owasp"]] = e["nist"]
    bagli = {}
    for k in kontroller:
        if not isinstance(k, dict):
            raise ValueError("kontrol geçersiz")
        if set(k) != {"id", "owasp", "ad", "sahip", "nist"}:
            raise ValueError("kontrol şeması geçersiz")
        if not isinstance(k["id"], str):
            raise ValueError("kontrol kimliği geçersiz")
        if not re.fullmatch(r"K-[A-Z0-9-]+", k["id"]):
            raise ValueError("kontrol kimliği geçersiz")
        if k["id"] in bagli:
            raise ValueError("kontrol kimliği yinelenemez")
        if k["owasp"] not in riskler:
            raise ValueError("kontrol riski geçersiz")
        for alan in ("ad", "sahip"):
            if not isinstance(k[alan], str):
                raise ValueError("kontrol metni geçersiz")
            if not k[alan]:
                raise ValueError("kontrol metni boş olamaz")
            if k[alan] != k[alan].strip():
                raise ValueError("kontrol metni boşluklu olamaz")
        if k["nist"] not in nist_esleme[k["owasp"]]:
            raise ValueError("kontrol NIST ilişkisi geçersiz")
        bagli[k["id"]] = k["owasp"]
        riskler[k["owasp"]].append(k["id"])
    sonuclar = {}
    for t in testler:
        if not isinstance(t, dict):
            raise ValueError("test geçersiz")
        if set(t) != {"kontrol", "durum", "kanit"}:
            raise ValueError("test şeması geçersiz")
        if t["kontrol"] not in bagli:
            raise ValueError("test kontrolü geçersiz")
        if t["kontrol"] in sonuclar:
            raise ValueError("test kontrolü yinelenemez")
        if t["durum"] not in ("gecti", "kaldi", "uygulanmadi"):
            raise ValueError("test durumu geçersiz")
        if not isinstance(t["kanit"], str):
            raise ValueError("kanıt geçersiz")
        if t["durum"] == "uygulanmadi":
            if t["kanit"] != "":
                raise ValueError("uygulanmamış test kanıtı boş olmalı")
        else:
            if not t["kanit"]:
                raise ValueError("test kanıtı boş olamaz")
            if t["kanit"] != t["kanit"].strip():
                raise ValueError("test kanıtı boşluklu olamaz")
        sonuclar[t["kontrol"]] = t["durum"]
    rapor = []
    ozet = {"kapsali": 0, "eksik_kanit": 0, "kritik": 0, "kontrolsuz": 0}
    for owasp in sorted(riskler):
        kimlikler = sorted(riskler[owasp])
        durumlar = [sonuclar.get(k, "test_yok") for k in kimlikler]
        toplam = len(kimlikler)
        if toplam == 0:
            durum = "kontrolsuz"
        elif "kaldi" in durumlar:
            durum = "kritik"
        elif "test_yok" in durumlar:
            durum = "eksik_kanit"
        elif "uygulanmadi" in durumlar:
            durum = "eksik_kanit"
        else:
            durum = "kapsali"
        rapor.append({
            "owasp": owasp, "toplam": toplam,
            "gecti": durumlar.count("gecti"), "kaldi": durumlar.count("kaldi"),
            "uygulanmadi": durumlar.count("uygulanmadi"), "test_yok": durumlar.count("test_yok"),
            "durum": durum,
        })
        ozet[durum] += 1
    return {"riskler": rapor, "ozet": ozet}
```

```hint
Kontrol kimliğinden riske bir eşleme, kontrol kimliğinden test durumuna başka bir eşleme kur. Her riskte durumları say ve öncelik sırasını ayrı `if` dallarıyla uygula.
```
:::

::: anlat Güvence durumu gerçek kanıttan gelmeli
Bir risk güvence raporu ancak beslediği kanıt kadar gerçektir. Buraya kadar test sonuçları sentetik fixture'dı; ama dersin tezi şuydu: *matrisin varlığı kanıtın yerine geçmez.* Son görevde senin `risk_guvence_raporu` işlevin, LLM01 (prompt injection) kontrolü için **gerçek bir model testinden** gelen kanıtla çalışır. Deney yerel modele zararsız bir canary-enjeksiyon savunma testi koşar: belge modeli gizli bir kodu sızdırmaya kışkırtır, sistem promptu bunu yasaklar; model hiç sızdırmazsa test `gecti`, en az bir kez sızdırırsa `kaldi`. Bu gerçek sonuç kontrolün kanıtı olur ve LLM01 güvence durumunu (sızmadıysa `kapsali`, sızdıysa `kritik`) belirler. Böylece raporun yeşili bir temenniden değil, gerçek bir ölçümden gelir.
:::

::: gorev Gerçek deney · Gerçek test kanıtıyla risk güvence raporu
`risk_guvence_raporu(eslemeler, kontroller, testler)` işlevini yaz — kuralları ve çıktısı 3. görevdekiyle **aynıdır**. Deney LLM01 kontrolü için gerçek bir canary-enjeksiyon testi koşar, sonucunu (`gecti`/`kaldi`) `testler` listesine kanıt olarak koyar ve senin raporun LLM01 güvence durumunu bu gerçek sonuca göre üretir.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab

def risk_guvence_raporu(eslemeler, kontroller, testler):
    # KUSURLU BAŞLANGIÇ KODU: durum önceliklerini dikkate almaz, tüm riskleri kapsalı raporlar.
    return {"riskler": [{"owasp": e.get("owasp"), "toplam": 0, "gecti": 0, "kaldi": 0, "uygulanmadi": 0, "test_yok": 0, "durum": "kapsali"} for e in (eslemeler or [])], "ozet": {"kapsali": len(eslemeler or []), "eksik_kanit": 0, "kritik": 0, "kontrolsuz": 0}}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_02 as deney
    deney.goster(risk_guvence_raporu)
```

```test
import ast
import ai_lab

def _ast_denetle(kod):
    agac = ast.parse(kod)
    yasakli = {"eval", "exec", "getattr", "setattr"}
    for dugum in ast.walk(agac):
        if isinstance(dugum, ast.ImportFrom):
            if any(a.name == "*" for a in dugum.names):
                return False, "wildcard import yasak"
            if any("referans" in a.name for a in dugum.names):
                return False, "referans fonksiyonu import edilemez"
        if isinstance(dugum, ast.Call):
            if isinstance(dugum.func, ast.Name) and dugum.func.id in yasakli:
                return False, f"{dugum.func.id} çağrısı yasak"
            if isinstance(dugum.func, ast.Attribute) and dugum.func.attr in yasakli:
                return False, f"{dugum.func.attr} kullanımı yasak"
            if isinstance(dugum.func, ast.Attribute) and "referans" in dugum.func.attr:
                return False, "referans niteliğine doğrudan erişilemez"
    return True, ""

gecerli_kod, gerekce = _ast_denetle(src)
ok(gecerli_kod, f"kod güvenlik denetiminden geçmeli: {gerekce}")

sonuclar = []
def kontrol(kosul, mesaj):
    sonuclar.append(bool(kosul))
    return ok(kosul, mesaj)
sorun = ai_lab.kod_denetimi(src, ("referans", "referans_rapor", "getattr"))
kontrol(not sorun, "laboratuvar yamalanmamalı, referans kullanılmamalı " + ", ".join(sorun))
fn = need("risk_guvence_raporu")
from sandbox import ai_gercek_ai_savunma_02 as D
E = [{"owasp": "LLM01", "atlas": ["AML.T0051"], "nist": ["MANAGE"]}, {"owasp": "LLM02", "atlas": ["AML.T0024"], "nist": ["MEASURE"]}]
K = [{"id": "K-INJ", "owasp": "LLM01", "ad": "Filtre", "sahip": "a", "nist": "MANAGE"}, {"id": "K-EV", "owasp": "LLM02", "ad": "Eval", "sahip": "b", "nist": "MEASURE"}]
def sozlesme(f):
    try:
        for T in [[{"kontrol": "K-INJ", "durum": "gecti", "kanit": "ok"}], [{"kontrol": "K-INJ", "durum": "kaldi", "kanit": "sizdi"}], []]:
            if f([dict(e) for e in E], [dict(k) for k in K], [dict(t) for t in T]) != D.referans_rapor(E, K, T):
                return False
        for e, k, t in [(None, K, []), (E, None, []), (E, K, None), (E, K, [None]), (E, K, [{"kontrol": "K-YOK", "durum": "gecti", "kanit": "x"}]),
                        (E, K, [{"kontrol": "K-INJ", "durum": "belirsiz", "kanit": "x"}]), (E, K, [{"kontrol": "K-INJ", "durum": "gecti", "kanit": ""}]),
                        (E, [dict(K[0], owasp="LLM09")], [])]:
            try:
                f(e, k, t)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
kontrol(sozlesme(fn), "risk güvence raporu doğru; geçersiz girdi reddedilmeli")
r, oz = None, None
# --- carbon-c8-g4-bas ---
def _c8_birim_denetimi():
    _u = []
    def _same(got, exp):
        try:
            if not bool(got == exp):
                return False
        except Exception:
            return False
        if isinstance(exp, bool) or isinstance(got, bool):
            return isinstance(got, bool) and isinstance(exp, bool)
        if isinstance(exp, (int, float)) and isinstance(got, (int, float)):
            return True
        return isinstance(got, type(exp))
    def ok(cond, msg=None, got=None):
        _u.append(bool(cond))
        return bool(cond)
    def eq(got, exp, msg=None):
        r = _same(got, exp)
        _u.append(r)
        return r
    def yakin(got, exp, msg=None, tol=1e-6):
        try:
            r = abs(got - exp) <= tol
        except Exception:
            r = False
        _u.append(bool(r))
        return bool(r)
    def raises(exc, fn_cagri, *a, msg=None, **kw):
        try:
            fn_cagri(*a, **kw)
        except exc:
            _u.append(True)
            return True
        except Exception:
            _u.append(False)
            return False
        _u.append(False)
        return False
    risk_guvence_raporu = need('risk_guvence_raporu')
    def _birim_adim_3():
        import copy
        E = [
            {"owasp": "LLM01", "atlas": ["AML.T0051"], "nist": ["MANAGE"]},
            {"owasp": "LLM02", "atlas": ["AML.T0024"], "nist": ["MEASURE"]},
            {"owasp": "LLM03", "atlas": ["AML.T0010"], "nist": ["GOVERN"]},
            {"owasp": "LLM04", "atlas": ["AML.T0054"], "nist": ["MAP"]},
        ]
        K = [
            {"id": "K-A", "owasp": "LLM01", "ad": "Filtre", "sahip": "A", "nist": "MANAGE"},
            {"id": "K-B", "owasp": "LLM02", "ad": "Eval", "sahip": "B", "nist": "MEASURE"},
            {"id": "K-C", "owasp": "LLM02", "ad": "İnsan incelemesi", "sahip": "C", "nist": "MEASURE"},
            {"id": "K-D", "owasp": "LLM03", "ad": "İmza", "sahip": "D", "nist": "GOVERN"},
        ]
        T = [
            {"kontrol": "K-A", "durum": "gecti", "kanit": "test-01"},
            {"kontrol": "K-B", "durum": "kaldi", "kanit": "test-02"},
            {"kontrol": "K-D", "durum": "uygulanmadi", "kanit": ""},
        ]
        def sozlesme(fn):
            try:
                once = copy.deepcopy((E, K, T))
                sonuc = fn(E, K, T)
                if (E, K, T) != once or sonuc != fn(E, list(reversed(K)), list(reversed(T))):
                    return False
                if [x["durum"] for x in sonuc["riskler"]] != ["kapsali", "kritik", "eksik_kanit", "kontrolsuz"]:
                    return False
                if sonuc["riskler"][1]["test_yok"] != 1 or sonuc["riskler"][1]["kaldi"] != 1:
                    return False
                if sonuc["ozet"] != {"kapsali": 1, "eksik_kanit": 1, "kritik": 1, "kontrolsuz": 1}:
                    return False
                hepsi = T + [{"kontrol": "K-C", "durum": "gecti", "kanit": "test-03"}]
                if fn(E, K, hepsi)["riskler"][1]["durum"] != "kritik":
                    return False
                basarili = [{"kontrol": "K-A", "durum": "gecti", "kanit": "ok"}]
                if fn(E[:1], K[:1], basarili)["ozet"]["kapsali"] != 1:
                    return False
                for eslemeler, kontroller, testler in [
                    (E, K, None), (E, K, [None]), (E, K, [dict(T[0], ek=1)]),
                    (E, K, [dict(T[0], kontrol="K-YOK")]),
                    (E, K, [dict(T[0], durum="belirsiz")]),
                    (E, K, [dict(T[0], kanit="")]), (E, K, [dict(T[0], kanit=" ok")]),
                    (E, K, [dict(T[2], kanit="not")]), (E, K, [T[0], T[0]]),
                    (None, K, T), (E, None, T), (E, [dict(K[0], owasp="LLM09")], T),
                    ([dict(E[0], owasp="LLM11")], [], []),
                ]:
                    try:
                        fn(eslemeler, kontroller, testler)
                        return False
                    except ValueError:
                        pass
                return True
            except Exception:
                return False
        ok(sozlesme(risk_guvence_raporu), "test kanıtları, durum önceliği ve risk sayaçları korunmalı")
        def m_basari(eslemeler, kontroller, testler):
            degisen = [dict(t, durum="gecti") for t in testler]
            return risk_guvence_raporu(eslemeler, kontroller, degisen)
        def m_testyok(eslemeler, kontroller, testler):
            return risk_guvence_raporu(eslemeler, kontroller, testler + [{"kontrol": "K-C", "durum": "gecti", "kanit": "ok"}])
        def m_kontrolsuz(eslemeler, kontroller, testler):
            return risk_guvence_raporu(eslemeler[:3], kontroller, testler)
        for ad, mutant in [("başarısız testi başarılı sayan", m_basari), ("eksik test kanıtını kapatan", m_testyok), ("kontrolsüz riski silen", m_kontrolsuz)]:
            ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

        raises(ValueError,risk_guvence_raporu,E,[dict(K[0],sahip=' Platform ')]+K[1:],T,msg='güvence kontrol sahibi baş/son boşluğu ret')
        _k02_tek = [k for k in K if k["owasp"] == E[0]["owasp"]][:1]
        eq(risk_guvence_raporu(E[:1], _k02_tek, [])["riskler"][0]["durum"], "eksik_kanit", "testi olmayan kontrol eksik_kanit olmalı")
        raises(ValueError, risk_guvence_raporu, [dict(E[0], owasp=123)] + E[1:], K, T, msg="eşleme owasp str olmalı")
        raises(ValueError, risk_guvence_raporu, [dict(E[0], atlas="AML.T0051")] + E[1:], K, T, msg="atlas liste olmalı")
        raises(ValueError, risk_guvence_raporu, [dict(E[0], atlas=[])] + E[1:], K, T, msg="boş atlas ret")
        raises(ValueError, risk_guvence_raporu, [dict(E[0], atlas=[123])] + E[1:], K, T, msg="atlas str olmalı")
        raises(ValueError, risk_guvence_raporu, [dict(E[0], nist="GOVERN")] + E[1:], K, T, msg="nist liste olmalı")
        raises(ValueError, risk_guvence_raporu, [dict(E[0], nist=[])] + E[1:], K, T, msg="boş nist ret")
        raises(ValueError, risk_guvence_raporu, E, [dict(K[0], id=123)] + K[1:], T, msg="kontrol id str olmalı")
        raises(ValueError, risk_guvence_raporu, E, [dict(K[0], ad=123)] + K[1:], T, msg="kontrol ad str olmalı")
        raises(ValueError, risk_guvence_raporu, E, [dict(K[0], ad=" ad ")] + K[1:], T, msg="kontrol ad trim ret")
        raises(ValueError, risk_guvence_raporu, E, [dict(K[0], sahip=123)] + K[1:], T, msg="sahip str olmalı")
        for _tk02 in T[0]:
            if isinstance(T[0][_tk02], str):
                raises(ValueError, risk_guvence_raporu, E, K, [dict(T[0], **{_tk02: 123})] + T[1:], msg=f"test {_tk02} str olmalı")
        raises(ValueError, risk_guvence_raporu, [123], K, T, msg="eşleme dict olmalı")
        raises(ValueError, risk_guvence_raporu, [dict(E[0], ek=1)] + E[1:], K, T, msg="eşleme fazla alan ret")
        raises(ValueError, risk_guvence_raporu, [E[0], E[0]], K, T, msg="yinelenen risk ret")
        raises(ValueError, risk_guvence_raporu, [dict(E[0], atlas=("AML.T0051",))] + E[1:], K, T, msg="atlas tuple olamaz")
        raises(ValueError, risk_guvence_raporu, [dict(E[0], atlas=["AML.T0054", "AML.T0051"])] + E[1:], K, T, msg="sırasız atlas ret")
        raises(ValueError, risk_guvence_raporu, [dict(E[0], atlas=["AML.X9999"])] + E[1:], K, T, msg="geçersiz atlas biçimi ret")
        raises(ValueError, risk_guvence_raporu, [dict(E[0], nist=("GOVERN",))] + E[1:], K, T, msg="nist tuple olamaz")
        raises(ValueError, risk_guvence_raporu, [dict(E[0], nist=["MAP", "GOVERN"])] + E[1:], K, T, msg="sırasız nist ret")
        raises(ValueError, risk_guvence_raporu, [dict(E[0], nist=["INVALID"])] + E[1:], K, T, msg="geçersiz nist işlevi ret")
        raises(ValueError, risk_guvence_raporu, E, [123], T, msg="kontrol dict olmalı")
        raises(ValueError, risk_guvence_raporu, E, [dict(K[0], ek=1)] + K[1:], T, msg="kontrol fazla alan ret")
        raises(ValueError, risk_guvence_raporu, E, [dict(K[0], id="bad")] + K[1:], T, msg="geçersiz kontrol kimliği ret")
        raises(ValueError, risk_guvence_raporu, E, [K[0], K[0]], T, msg="yinelenen kontrol kimliği ret")
        raises(ValueError, risk_guvence_raporu, E, [dict(K[0], ad="")] + K[1:], T, msg="boş kontrol adı ret")
        raises(ValueError, risk_guvence_raporu, E, [dict(K[0], sahip="")] + K[1:], T, msg="boş kontrol sahibi ret")
        raises(ValueError, risk_guvence_raporu, [dict(E[0], nist=["GOVERN"])], [dict(K[0], owasp=E[0]["owasp"], nist="MANAGE")], [], msg="eşleşmeyen NIST ilişkisi ret")
        raises(ValueError, risk_guvence_raporu, [E[0], E[0]], [], [], msg="yinelenen risk kimliği boş kontrol listesinde ret")
        raises(ValueError, risk_guvence_raporu, [dict(E[0], atlas=123)], [], [], msg="atlas list değil int olamaz")
        raises(ValueError, risk_guvence_raporu, [dict(E[0], nist=123)], [], [], msg="nist list değil int olamaz")
        raises(ValueError, risk_guvence_raporu, [dict(E[0], nist=[])], [], [], msg="boş nist listesi ret")
        raises(ValueError, risk_guvence_raporu, [dict(E[0], nist=["MAP", "GOVERN"])], [], [], msg="sırasız nist listesi ret")
        raises(ValueError, risk_guvence_raporu, [dict(E[0], nist=["INVALID"])], [], [], msg="geçersiz nist işlevi ret")
        raises(ValueError, risk_guvence_raporu, E, [dict(K[0], id="bad")], [], msg="geçersiz kontrol kimliği boş test listesinde ret")
        raises(ValueError, risk_guvence_raporu, E, [K[0], K[0]], [], msg="yinelenen kontrol kimliği boş test listesinde ret")
    try:
        _birim_adim_3()
    except Exception:
        _u.append(False)
    return bool(_u) and all(_u)
kontrol(_c8_birim_denetimi(), "deney öncesi tam birim sözleşmesi korunmalı")
# --- carbon-c8-g4-son ---
if all(sonuclar):
    try:
        r = D.deney(fn)
    except ai_lab.GercekLabYok as e:
        kontrol(False, f"GERÇEK MODEL YOK, deney yapılmadı: {e}")
        stop()
    kontrol(r["rapor"] == D.referans_rapor(r["eslemeler"], r["kontroller"], r["testler"]), "gerçek kanıtlı rapor bağımsız hesapla aynı")
    beklenen = "kapsali" if r["gercek_durum"] == "gecti" else "kritik"
    llm01 = next(x for x in r["rapor"]["riskler"] if x["owasp"] == "LLM01")
    kontrol(llm01["durum"] == beklenen, f"LLM01 güvence durumu gerçek test sonucunu yansıttı: test={r['gercek_durum']} → durum={llm01['durum']}")
    oz = D.ozet(r)
yol = ai_lab.kanit_yaz("savunma-guvence", {"kaynak": "gercek", "kabul": all(sonuclar), "ders": "ai-savunma-02",
                                           "ortam": (r or {}).get("ortam"), "ozet": oz})
if oz:
    ok(True, f"BULGU ({r['ortam']['model']['ad']}): LLM01 için gerçek canary-enjeksiyon testi {r['canary_tekrar']} denemede {r['sizan']} sızıntı → "
             f"test '{r['gercek_durum']}'; LLM01 güvence durumu '{oz['llm01_guvence']}'. Özet {oz['ozet']}. Güvence kâğıt kontrolden değil gerçek kanıttan geldi.")
```

```solution
import re
import ai_lab

def risk_guvence_raporu(eslemeler, kontroller, testler):
    if not isinstance(eslemeler, list) or not isinstance(kontroller, list) or not isinstance(testler, list):
        raise ValueError("eşleme/kontrol/test listesi geçersiz")
    riskler, nist_esleme = {}, {}
    for e in eslemeler:
        if not isinstance(e, dict) or set(e) != {"owasp", "atlas", "nist"} or not isinstance(e["owasp"], str) \
                or not re.fullmatch(r"LLM(0[1-9]|10)", e["owasp"]) or e["owasp"] in riskler:
            raise ValueError("eşleme geçersiz")
        if not isinstance(e["atlas"], list) or not e["atlas"] or e["atlas"] != sorted(set(e["atlas"])) \
                or any(not isinstance(a, str) or not re.fullmatch(r"AML.T[0-9]{4}", a) for a in e["atlas"]):
            raise ValueError("ATLAS geçersiz")
        if not isinstance(e["nist"], list) or not e["nist"] or e["nist"] != sorted(set(e["nist"])) \
                or any(n not in ("GOVERN", "MAP", "MEASURE", "MANAGE") for n in e["nist"]):
            raise ValueError("NIST geçersiz")
        riskler[e["owasp"]] = []
        nist_esleme[e["owasp"]] = e["nist"]
    bagli = {}
    for k in kontroller:
        if not isinstance(k, dict) or set(k) != {"id", "owasp", "ad", "sahip", "nist"} or not isinstance(k["id"], str) \
                or not re.fullmatch(r"K-[A-Z0-9-]+", k["id"]) or k["id"] in bagli or k["owasp"] not in riskler:
            raise ValueError("kontrol geçersiz")
        for alan in ("ad", "sahip"):
            if not isinstance(k[alan], str) or not k[alan] or k[alan] != k[alan].strip():
                raise ValueError("kontrol metni geçersiz")
        if k["nist"] not in nist_esleme[k["owasp"]]:
            raise ValueError("kontrol NIST ilişkisi geçersiz")
        bagli[k["id"]] = k["owasp"]
        riskler[k["owasp"]].append(k["id"])
    sonuclar = {}
    for t in testler:
        if not isinstance(t, dict) or set(t) != {"kontrol", "durum", "kanit"} or t["kontrol"] not in bagli or t["kontrol"] in sonuclar:
            raise ValueError("test geçersiz")
        if t["durum"] not in ("gecti", "kaldi", "uygulanmadi") or not isinstance(t["kanit"], str):
            raise ValueError("test durumu/kanıt geçersiz")
        if t["durum"] == "uygulanmadi":
            if t["kanit"] != "":
                raise ValueError("uygulanmamış test kanıtı boş olmalı")
        elif not t["kanit"] or t["kanit"] != t["kanit"].strip():
            raise ValueError("test kanıtı geçersiz")
        sonuclar[t["kontrol"]] = t["durum"]
    rapor, ozet = [], {"kapsali": 0, "eksik_kanit": 0, "kritik": 0, "kontrolsuz": 0}
    for owasp in sorted(riskler):
        kimlikler = sorted(riskler[owasp])
        durumlar = [sonuclar.get(k, "test_yok") for k in kimlikler]
        if not kimlikler:
            durum = "kontrolsuz"
        elif "kaldi" in durumlar:
            durum = "kritik"
        elif "test_yok" in durumlar or "uygulanmadi" in durumlar:
            durum = "eksik_kanit"
        else:
            durum = "kapsali"
        rapor.append({"owasp": owasp, "toplam": len(kimlikler), "gecti": durumlar.count("gecti"), "kaldi": durumlar.count("kaldi"),
                      "uygulanmadi": durumlar.count("uygulanmadi"), "test_yok": durumlar.count("test_yok"), "durum": durum})
        ozet[durum] += 1
    return {"riskler": rapor, "ozet": ozet}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_02 as deney
    deney.goster(risk_guvence_raporu)
```

```hint
Bu işlev 3. görevdeki `risk_guvence_raporu` ile birebir aynıdır; tek fark, LLM01 kontrolünün test kanıtının gerçek bir model testinden gelmesidir. Durum önceliği: kontrol yoksa `kontrolsuz`, bir `kaldi` varsa `kritik`, test eksik/uygulanmadı varsa `eksik_kanit`, hepsi `gecti` ise `kapsali`.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
### Kontrol eşlemesi çalışan kanıtın yerini tutmaz

NIST işlevi, tehdit sınıfı ve kontrol sahibi farklı eksenlerdir. Eşleme bu sorumlulukları düzenler; kontrolün uygulanıp işe yaradığını gerçek test kaydı gösterir. Sahibi eksik veya test kanıtı olmayan satır güvence tamamlandı sayılamaz. Bu dar matris standarda tam uyumluluk veya sertifikasyon sonucu değildir.

| Yaygın yanlış | Mekanizmanın sınırı |
|---|---|
| Çerçeve etiketi riskin kapandığını gösterir | Etiket, sorumlu ve doğrulanmış kanıt birlikte gerekir. |

Saldırı–savunma bağlantısı: ai-saldiri-36.
:::

::: anlat Kaynak ile lab sonucunu ayır
[NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework). Çerçeve risk yönetimini düzenler; bu labın kontrol matrisi sertifikasyon değildir.
:::
