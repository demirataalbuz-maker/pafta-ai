---
id: ai-guvence-04
title: Yanlış Pozitiflerin Güvenlik Maliyeti
summary: Farklı eşiklerde hata matrisi, yanlış pozitif oranı ve maliyet değişimini hesaplayarak eşik seçimini gerekçelendir.
esleme: ai-guvence-02, ai-guvence-40, ai-savunma-01
timeout: 45
---

::: anlat Gerçek maliyet optimizasyonunu bil, sentetik temsili ayırt et
Siber güvenlik operasyon merkezlerinde (SOC) makine öğrenmesi ve yapay zeka modellerinin karar sınırlarını belirlemek, standart veri bilimi sınıflandırmasından temelde farklı dinamiklere sahiptir. Genel makine öğrenmesi problemlerinde genellikle simetrik doğruluk (`accuracy`) veya $0.5$ varsayılan olasılık eşiği kullanılır; oysa siber savunmada hataların maliyeti asla simetrik değildir. Bir saldırının tespit edilemeyerek kaçırılması (Yanlış Negatif - False Negative / FN), sistemlerin ele geçirilmesi, fidye yazılımı yayılımı veya veri sızıntısı gibi yıkıcı güvenlik felaketlerine yol açarken; meşru bir kullanıcı veya sistem eyleminin yanlışlıkla tehdit olarak işaretlenmesi (Yanlış Pozitif - False Positive / FP), güvenlik analistlerinin alarm yorgunluğu (alert fatigue) yaşamasına, inceleme kuyruklarının tıkanmasına ve meşru iş süreçlerinin kesintiye uğramasına neden olur. Bu nedenle güvenlik modellerinde eşik seçimi, doğruluğu maksimize etmek yerine toplam beklenen güvenlik maliyetini minimize eden maliyet duyarlı eşik kalibrasyonuna (cost-sensitive thresholding) dayanmalıdır.

| Gerçek araç / model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| SOC/güvenlik eşik kalibrasyonu: Analist inceleme süresi ve operasyonel yük (FP maliyeti) ile kaçırılan saldırının potansiyel hasarı (FN maliyeti) | İlk 3 görevde `veri/maliyet_profili.json` sentetik profili; son görevde FN-ağır ve FP-ağır iki canlı profil | Sabit doğrusal maliyet modeli, eşzamanlı alarm fırtınasında analist kapasitesinin doygunluğunu ve kuyruk çöküşünü tam olarak modellemez |
| Eşik taraması: ROC/PR eğrisi üzerinde beklenen toplam güvenlik maliyetini minimize eden optimal karar eşiği ($\tau^*$) | İlk 3 görevde `veri/skor_kayitlari.json` sentetik skorları; son görevde gerçek `LogisticRegression` `predict_proba` skorları | Doğrulama kümesinde seçilen en iyi eşik, üretim ortamında sınıf taban oranları (base rate / class prior) değiştiğinde optimal kalmayabilir |

> [!NOT]
> İlk üç görevde örnek dosyalar çalışma klasörünün `veri/` altına kopyalanır: `veri/maliyet_profili.json` ve `veri/skor_kayitlari.json` (tümü **sentetik**). Bu dosyaları kodundan okuyup inceleyebilirsin; ancak her çalıştırmada temiz kopya yeniden yazılır (**kalıcılık yoktur**). Kontrol adımı bu dosyalardan bağımsız gizli verilerle sınama yapar. Gerçek deney adımında ise `scikit-learn` ile eğitilen canlı bir sınıflandırıcının olasılık skorları üzerinde iki farklı maliyet profili sınanır.

### Aracın Altında Ne Olur?
Maliyet optimizasyon motoru şu adımları işletir:
1. **Maliyet Profilinin Doğrulanması:** İşletmenin operasyonel gerçeklerine göre belirlenen FP maliyeti ($c_{FP} \ge 0$), FN maliyeti ($c_{FN} \ge 0$) ve para birimi (`TRY`, `USD`, `EUR`) doğrulanır. Finansal veya kritik altyapı sistemlerinde genellikle $c_{FN} \gg c_{FP}$ iken, yoğun kullanıcı trafiği alan tüketici servislerinde $c_{FP}$ baskın olabilir.
2. **Eşik Tabanlı Hata Matrisi Üretimi:** Modelin ürettiği her olasılık skoru ($s \in [0, 1]$), test edilen karar eşiği $\tau$ ile karşılaştırılır. Kural açıktır: Skor eşiğe eşit veya büyükse ($s \ge \tau$) tahmin pozitif (`yelkovan` / şüpheli), aksi halde ($s < \tau$) negatif (`diger` / temiz) olarak belirlenir. Gerçek etiket ve tahmin birleşimine göre $TP, FP, FN, TN$ hücreleri toplanır.
3. **Yanlış Pozitif Oranı (FPR) ve Maliyet Hesabı:** Yanlış Pozitif Oranı $FPR = \frac{FP}{FP + TN}$ formülüyle hesaplanır; eğer payda sıfır ise (`FP + TN == 0`) oran tanımsızdır ve `None` döndürülür. Eşiğin toplam güvenlik maliyeti ise doğrusal risk formülüyle bulunur:
   $$\text{Maliyet}(\tau) = FP(\tau) \cdot c_{FP} + FN(\tau) \cdot c_{FN}$$
4. **Optimal Karar Eşiğinin Seçimi:** Aday eşikler taranır; toplam maliyeti en küçük olan eşik ($\tau^* = \arg\min_\tau \text{Maliyet}(\tau)$) optimal çalışma noktası olarak seçilir. İki eşiğin ham maliyeti eşit çıktığında, güvenlik tarafında kalmak (daha fazla şüpheliyi yakalamak) amacıyla daha düşük eşik tercih edilir.

### Çıktı Nasıl Okunur?
- **En İyi Eşik (`en_iyi_esik`):** Verilen maliyet profiline göre işletme açısından riski ve operasyonel yükü minimize eden karar sınırıdır.
- **Satırlar (`satirlar`):** Eşiğe göre artan sırada listelenen hata matrisi dökümüdür. Eşik yükseldikçe genellikle $FP$ azalır, $FN$ artar; eşik düştükçe $FP$ yükselir, $FN$ sıfıra yaklaşır.
- **Yanlış Pozitif Oranı (`fpr`):** Temiz trafiğin yüzde kaçının gereksiz yere alarmla sonuçlandığını gösterir; analist yükünün kestirilmesinde anahtar metriktir.

### Saldırgan Neyi Dener?
- **Eşik Altı Gizlenme (Low-and-Slow / Sub-threshold Evasion):** Saldırgan hedef modelin karar eşiğini (örneğin $\tau = 0.5$) tahmin ederek tespit olasılığını eşiğin hemen altında (örneğin $0.45$) tutacak seyreltilmiş ve parçalı saldırı desenleri kullanır.
- **Alarm Boğması ve Dikkat Dağıtma (Alert Flooding):** Kasıtlı olarak çok sayıda yanlış pozitif üreten gürültülü aktiviteler yaparak SOC ekibini yanlış alarmlarla kilitler ve asıl kritik saldırıyı oluşan operasyonel kargaşa sırasında gerçekleştirir.

### Savunma Neden Kırılır?
- **Varsayılan $0.5$ Eşik Hatası:** Çoğu sınıflandırıcı kütüphanesi varsayılan olarak $0.5$ eşiği uygular. Olasılıklar kalibre edilmişse beklenen maliyeti en küçük yapan eşik $\tau^* = \frac{c_{FP}}{c_{FP} + c_{FN}}$ olur. Örneğin $c_{FN} = 100 \cdot c_{FP}$ ise $\tau^* \approx 0.01$ çıkar; yani FN çok pahalıysa eşik $0.5$'in çok altına iner. Model kalibre değilse bu formül yalnız başlangıç noktasıdır; bu derste olduğu gibi aday eşikleri gerçek maliyetle taramak gerekir.
- **Temel Oran Yanılgısı (Base Rate Fallacy):** Laboratuvar ortamında $\%50 - \%50$ dengeli veride seçilen bir eşik, gerçek hayatta saldırı oranının $\%0.01$ olduğu bir ağda işletildiğinde her gün binlerce yanlış alarm üreterek savunmayı felç eder.
- **Statik Eşik Tuzağı:** Saldırganların tekniklerini güncellemesi veya ağ trafiğinin mevsimsel değişimi durumunda eşiklerin periyodik olarak yeniden kalibre edilmemesi modeli körleştirir.

### Sık Yapılan Geliştirici Tuzakları
- **Eşik Karşılaştırma İşareti:** `skor >= esik` yerine `skor > esik` yazmak, tam eşik değerindeki şüpheli kayıtların kaçırılarak yanlışlıkla negatif sınıfa atılmasına yol açar.
- **FPR Sıfıra Bölme Hatası:** Test kümesinde hiç gerçek negatif olmaması durumunda (`fp + tn == 0`) `ZeroDivisionError` oluşmaması için payda kontrolü yapılmalı ve `None` atanmalıdır.
- **Eşitlik Durumunda Karar:** Maliyet eşitliğinde rastgele seçim yapmak veya ilk gelen matrisi almak yerine deterministik olarak daha küçük eşiğin seçilmesi kuralına uyulmalıdır.
- **Bool Tipi Tuzağı:** Python'da `isinstance(False, int) == True` olduğundan sayım ve maliyet alanlarında açıkça `isinstance(v, bool)` kontrolü yapılmalıdır.
- **Tutarsız Veri Kümeleri:** Farklı eşik matrislerinde $TP + FP + FN + TN$ toplamlarının birbirinden farklı olması matrislerin farklı veri kümelerinden geldiğini gösterir ve `ValueError` ile engellenmelidir.
:::

::: anlat Eşik hem matrisi hem maliyeti değiştirir
Skor eşiğe eşit veya büyükse tahmin `yelkovan` olur. Eşiği değiştirmek TP, FP, FN ve TN sayılarını birlikte değiştirebilir. Yanlış pozitif oranı `fp/(fp+tn)` hesaplanır; payda sıfırsa oran `None` döndürülür.

Toplam maliyet `fp*fp_maliyeti + fn*fn_maliyeti` formülüyle bulunur. En düşük maliyetli eşik seçilir; maliyetler eşitse daha düşük eşik kazanır. Bu yalnız fixture üzerinde tanımlı deterministik seçim kuralıdır, evrensel bir güvenlik politikası değildir.

Kaynaklar: [Elkan 2001 — The Foundations of Cost-Sensitive Learning (IJCAI)](https://cseweb.ucsd.edu/~elkan/rescale.pdf), [Axelsson 2000 — The Base-Rate Fallacy and the Difficulty of Intrusion Detection (ACM TISSEC)](https://doi.org/10.1145/357830.357849).
:::

::: tahmin Eşik ve maliyet sonucunu tahmin et
Üç çıktı satırını yaz:

```python
print(0.5 >= 0.5)
print(1 * 2.5 + 1 * 10)
print(round(1 / (1 + 1), 6))
```

???

```cikti
True
12.5
0.5
```

İlk satır eşiğe eşit skorun pozitif sınıflandırıldığını gösterir.
:::

::: gorev 1 · Maliyet profilini doğrula
`maliyet_profili_dogrula(profil)` işlevini yaz. Profil tam olarak `fp_maliyeti`, `fn_maliyeti`, `para_birimi` alanlarını taşısın. İki maliyet de bool olmayan, sıfır veya pozitif sonlu sayıdır. Para birimi yalnız `TRY`, `USD` veya `EUR` olabilir. Geçersiz veride `ValueError` yükselt.

Alanları koruyan yeni sözlükle döndür ve girdiyi değiştirme. İki maliyetin aynı anda sıfır olması geçerlidir.

```starter
from ai_guvence_veri import json_yukle

def maliyet_profili_dogrula(profil):
    # KUSURLU BAŞLANGIÇ KODU: negatif maliyetleri ve para birimini denetlemeden doğrudan girdi sözlüğünü döndürüyor!
    return profil

print("Örnek maliyet profili:", maliyet_profili_dogrula(json_yukle("veri/maliyet_profili.json")))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-04")
```

```test
import copy
P = {"fp_maliyeti": 2.5, "fn_maliyeti": 10, "para_birimi": "TRY"}
def sozlesme(fn):
    try:
        once = copy.deepcopy(P)
        sonuc = fn(P)
        if sonuc != P or P != once or sonuc is P:
            return False
        if fn({"fp_maliyeti": 0, "fn_maliyeti": 0, "para_birimi": "EUR"})["fn_maliyeti"] != 0:
            return False
        for profil in [
            None, [], dict(P, ek=1), dict(P, fp_maliyeti=None), dict(P, fp_maliyeti=True),
            dict(P, fp_maliyeti="2.5"), dict(P, fp_maliyeti=float("nan")), dict(P, fp_maliyeti=float("inf")),
            dict(P, fp_maliyeti=-0.1), dict(P, fn_maliyeti=None), dict(P, fn_maliyeti=True),
            dict(P, fn_maliyeti="10"), dict(P, fn_maliyeti=float("nan")), dict(P, fn_maliyeti=float("inf")),
            dict(P, fn_maliyeti=-1), dict(P, para_birimi="GBP"), dict(P, para_birimi="try"), dict(P, para_birimi=None),
        ]:
            try:
                fn(profil)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(maliyet_profili_dogrula), "maliyet türleri, sınırlar ve para birimi korunmalı")
def m_fp(profil):
    return maliyet_profili_dogrula(dict(profil, fp_maliyeti=0))
def m_fn(profil):
    return maliyet_profili_dogrula(dict(profil, fn_maliyeti=0))
def m_birim(profil):
    return maliyet_profili_dogrula(dict(profil, para_birimi="USD"))
for ad, mutant in [("FP maliyetini silen", m_fp), ("FN maliyetini silen", m_fn), ("birimi değiştiren", m_birim)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def maliyet_profili_dogrula(profil):
    import math
    if not isinstance(profil, dict):
        raise ValueError("profil sözlük olmalı")
    if set(profil) != {"fp_maliyeti", "fn_maliyeti", "para_birimi"}:
        raise ValueError("profil şeması geçersiz")
    for alan in ("fp_maliyeti", "fn_maliyeti"):
        deger = profil[alan]
        if isinstance(deger, bool) or not isinstance(deger, (int, float)):
            raise ValueError("maliyet sayı olmalı")
        if not math.isfinite(deger):
            raise ValueError("maliyet sonlu olmalı")
        if deger < 0:
            raise ValueError("maliyet negatif olamaz")
    if profil["para_birimi"] not in ("TRY", "USD", "EUR"):
        raise ValueError("para birimi geçersiz")
    return {"fp_maliyeti": profil["fp_maliyeti"], "fn_maliyeti": profil["fn_maliyeti"], "para_birimi": profil["para_birimi"]}
```

```hint
İki maliyeti aynı döngüde tür, sonluluk ve alt sınır yönünden denetle. Para birimini kapalı listeden doğrula.
```
:::

::: gorev 2 · Verilen eşikte hata matrisi üret
`esik_matrisi(kayitlar, esik)` işlevini yaz. Kayıtlar boş olmayan listedir. Her kayıt tam olarak `id`, `gercek`, `skor` alanlarını taşısın. Kimlik 1–64 karakterlik, ASCII harf/rakamla başlayan ve yalnız ASCII harf, rakam, alt çizgi veya tire içeren benzersiz stringdir. Gerçek etiket `yelkovan` veya `diger`, skor bool olmayan sonlu sayı ve `[0,1]` aralığındadır. Eşik de aynı sayı ve aralık kurallarını sağlar. Geçersiz veride `ValueError` yükselt.

Skor `>= esik` ise tahmin `yelkovan`, aksi halde `diger` olsun. `{"esik":ESIK,"tp":N,"fp":N,"fn":N,"tn":N}` döndür. Girdiyi değiştirme.

```starter
from ai_guvence_veri import json_yukle

def esik_matrisi(kayitlar, esik):
    # KUSURLU BAŞLANGIÇ KODU: skor >= esik yerine skor > esik kullanıyor ve sınır değerini yanlış sınıflandırıyor!
    tp = sum(k.get("gercek") == "yelkovan" and k.get("skor", 0) > esik for k in (kayitlar or []))
    return {"esik": esik, "tp": tp, "fp": 0, "fn": 0, "tn": 0}

print("Örnek eşik matrisi:", esik_matrisi(json_yukle("veri/skor_kayitlari.json"), 0.5))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-04")
```

```test
import copy
K = [
    {"id": "r-1", "gercek": "yelkovan", "skor": 0.5},
    {"id": "r-2", "gercek": "diger", "skor": 0.5},
    {"id": "r-3", "gercek": "yelkovan", "skor": 0},
    {"id": "r-4", "gercek": "diger", "skor": 0},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        if fn(K, 0.5) != {"esik": 0.5, "tp": 1, "fp": 1, "fn": 1, "tn": 1} or K != once:
            return False
        if fn(K, 0) != {"esik": 0, "tp": 2, "fp": 2, "fn": 0, "tn": 0}:
            return False
        if fn(K, 1) != {"esik": 1, "tp": 0, "fp": 0, "fn": 2, "tn": 2}:
            return False
        if fn([dict(K[0], skor=1)], 1)["tp"] != 1:
            return False
        if fn([K[3]], 1) != {"esik": 1, "tp": 0, "fp": 0, "fn": 0, "tn": 1}:
            return False
        if fn([dict(K[0], id="a" * 64)], 0.5)["tp"] != 1:
            return False
        for kayitlar, esik in [
            (None, 0.5), (tuple(K), 0.5), (K, False), ({}, 0.5), ([], 0.5), ([None], 0.5), ([dict(K[0], ek=1)], 0.5), ([dict(K[0], id=123)], 0.5),
            ([dict(K[0], id="")], 0.5), ([dict(K[0], id="a b")], 0.5), ([dict(K[0], id="a" * 65)], 0.5),
            ([dict(K[0], id=None)], 0.5), ([K[0], K[0]], 0.5),
            ([dict(K[0], gercek="baska")], 0.5), ([dict(K[0], gercek=None)], 0.5),
            ([dict(K[0], skor=True)], 0.5), ([dict(K[0], skor="0.5")], 0.5),
            ([dict(K[0], skor=float("nan"))], 0.5), ([dict(K[0], skor=float("inf"))], 0.5),
            ([dict(K[0], skor=-0.1)], 0.5), ([dict(K[0], skor=1.1)], 0.5),
            (K, None), (K, True), (K, "0.5"), (K, float("nan")), (K, float("inf")), (K, -0.1), (K, 1.1),
        ]:
            try:
                fn(kayitlar, esik)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(esik_matrisi), "kayıt şeması, eşik karşılaştırması ve dört hücre korunmalı")
def m_skor(kayitlar, esik):
    return esik_matrisi([dict(x, skor=0) for x in kayitlar], esik)
def m_etiket(kayitlar, esik):
    return esik_matrisi([dict(x, gercek="diger") for x in kayitlar], esik)
def m_esik(kayitlar, esik):
    return esik_matrisi(kayitlar, 1)
for ad, mutant in [("skorları silen", m_skor), ("etiketleri değiştiren", m_etiket), ("eşiği değiştiren", m_esik)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def esik_matrisi(kayitlar, esik):
    import math
    import re
    if isinstance(esik, bool) or not isinstance(esik, (int, float)):
        raise ValueError("eşik sayı olmalı")
    if not math.isfinite(esik):
        raise ValueError("eşik sonlu olmalı")
    if esik < 0 or esik > 1:
        raise ValueError("eşik aralık dışında")
    if not isinstance(kayitlar, list):
        raise ValueError("kayıtlar liste olmalı")
    if not kayitlar:
        raise ValueError("kayıtlar boş olamaz")
    gorulen = set()
    sonuc = {"esik": esik, "tp": 0, "fp": 0, "fn": 0, "tn": 0}
    for kayit in kayitlar:
        if not isinstance(kayit, dict):
            raise ValueError("kayıt sözlük olmalı")
        if set(kayit) != {"id", "gercek", "skor"}:
            raise ValueError("kayıt şeması geçersiz")
        kimlik = kayit["id"]
        if not isinstance(kimlik, str):
            raise ValueError("kimlik string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kimlik):
            raise ValueError("kimlik geçersiz")
        if kimlik in gorulen:
            raise ValueError("kimlik yinelenemez")
        if kayit["gercek"] not in ("yelkovan", "diger"):
            raise ValueError("gerçek etiket geçersiz")
        skor = kayit["skor"]
        if isinstance(skor, bool) or not isinstance(skor, (int, float)):
            raise ValueError("skor sayı olmalı")
        if not math.isfinite(skor):
            raise ValueError("skor sonlu olmalı")
        if skor < 0 or skor > 1:
            raise ValueError("skor aralık dışında")
        tahmin = "yelkovan" if skor >= esik else "diger"
        if kayit["gercek"] == "yelkovan" and tahmin == "yelkovan":
            sonuc["tp"] += 1
        elif kayit["gercek"] == "diger" and tahmin == "yelkovan":
            sonuc["fp"] += 1
        elif kayit["gercek"] == "yelkovan":
            sonuc["fn"] += 1
        else:
            sonuc["tn"] += 1
        gorulen.add(kimlik)
    return sonuc
```

```hint
Tahmini tek karşılaştırmayla üret. Gerçek ve tahmin etiketinin dört birleşimini ilgili hücreye say.
```
:::

::: gorev 3 · Eşikleri güvenlik maliyetiyle karşılaştır
`maliyet_raporu(matrisler, profil)` işlevini yaz. Profil ilk görevdeki kuralları sağlasın. Matrisler boş olmayan listedir; her kayıt tam olarak `esik`, `tp`, `fp`, `fn`, `tn` alanlarını taşısın. Eşikler bool olmayan sonlu sayı, `[0,1]` aralığında ve benzersizdir. Dört sayım bool olmayan, sıfır veya pozitif tamsayıdır. Her matristeki toplam kayıt sayısı sıfırdan büyük ve bütün matrislerde aynı olmalıdır. Geçersiz veride `ValueError` yükselt.

Her satıra `fpr` ve `maliyet` ekle. FPR `fp/(fp+tn)`, payda sıfırsa `None`; maliyet `fp*fp_maliyeti + fn*fn_maliyeti` olsun. İkisini ve maliyeti altı ondalık basamağa yuvarla. Satırları eşiğe göre artan sırala. `{"para_birimi":BIRIM,"en_iyi_esik":ESIK,"satirlar":[SATIR,...]}` döndür. En düşük ham maliyetli eşiği seç; eşitlikte düşük eşik kazansın. Girdileri değiştirme.

```starter
from ai_guvence_veri import json_yukle

def maliyet_raporu(matrisler, profil):
    # KUSURLU BAŞLANGIÇ KODU: maliyet hesabı yapmadan her zaman ilk matrisin eşiğini seçiyor!
    ilk = (matrisler or [{"esik": 0.5}])[0]
    return {"para_birimi": profil.get("para_birimi", "TRY") if isinstance(profil, dict) else "TRY", "en_iyi_esik": ilk.get("esik", 0.5), "satirlar": []}

kayitlar = json_yukle("veri/skor_kayitlari.json")
profil = json_yukle("veri/maliyet_profili.json")
print("Örnek maliyet raporu:", maliyet_raporu([{"esik": 0.5, "tp": 1, "fp": 1, "fn": 1, "tn": 1}], profil))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-04")
```

```test
import copy
P = {"fp_maliyeti": 2.5, "fn_maliyeti": 10, "para_birimi": "TRY"}
M = [
    {"esik": 0.5, "tp": 1, "fp": 1, "fn": 1, "tn": 1},
    {"esik": 0.25, "tp": 2, "fp": 1, "fn": 0, "tn": 1},
    {"esik": 0.75, "tp": 0, "fp": 0, "fn": 2, "tn": 2},
]
def sozlesme(fn):
    try:
        monce = copy.deepcopy(M)
        ponce = copy.deepcopy(P)
        sonuc = fn(M, P)
        if M != monce or P != ponce or sonuc["para_birimi"] != "TRY" or sonuc["en_iyi_esik"] != 0.25:
            return False
        if [x["esik"] for x in sonuc["satirlar"]] != [0.25, 0.5, 0.75]:
            return False
        if sonuc["satirlar"][0]["maliyet"] != 2.5 or sonuc["satirlar"][1]["maliyet"] != 12.5 or sonuc["satirlar"][2]["maliyet"] != 20:
            return False
        if sonuc["satirlar"][0]["fpr"] != 0.5 or sonuc["satirlar"][2]["fpr"] != 0:
            return False
        esit_p = {"fp_maliyeti": 1, "fn_maliyeti": 1, "para_birimi": "USD"}
        esit_m = [{"esik": 0.5, "tp": 0, "fp": 0, "fn": 1, "tn": 0}, {"esik": 0.25, "tp": 0, "fp": 1, "fn": 0, "tn": 0}]
        esit = fn(esit_m, esit_p)
        if esit["en_iyi_esik"] != 0.25 or esit["satirlar"][0]["fpr"] != 1 or esit["satirlar"][1]["fpr"] is not None:
            return False
        yuvarla = fn([{"esik": 1, "tp": 0, "fp": 1, "fn": 0, "tn": 0}], {"fp_maliyeti": 1 / 3, "fn_maliyeti": 0, "para_birimi": "EUR"})
        if yuvarla["satirlar"][0]["maliyet"] != 0.333333:
            return False
        fpr_yuvarla = fn([{"esik": 0, "tp": 0, "fp": 1, "fn": 0, "tn": 2}], P)
        if fpr_yuvarla["satirlar"][0]["fpr"] != 0.333333:
            return False
        for matrisler, profil in [
            (None, P), (tuple(M), P), ({}, P), ([], P), ([None], P), ([dict(M[0], ek=1)], P),
            ([dict(M[0], esik=True)], P), ([dict(M[0], esik="0.5")], P), ([dict(M[0], esik=float("nan"))], P),
            ([dict(M[0], esik=-0.1)], P), ([dict(M[0], esik=1.1)], P), ([M[0], M[0]], P),
            ([dict(M[0], tp=True)], P), ([dict(M[0], tp=1.0)], P), ([dict(M[0], tp=-1)], P),
            ([dict(M[0], fp=True)], P), ([dict(M[0], fp=1.0)], P), ([dict(M[0], fp=-1)], P),
            ([dict(M[0], fn=True)], P), ([dict(M[0], fn=1.0)], P), ([dict(M[0], fn=-1)], P),
            ([dict(M[0], tn=True)], P), ([dict(M[0], tn=1.0)], P), ([dict(M[0], tn=-1)], P),
            ([{"esik": 0.5, "tp": 0, "fp": 0, "fn": 0, "tn": 0}], P),
            ([M[0], dict(M[1], esik=0.75, tn=0)], P),
            (M, None), (M, dict(P, ek=1)), (M, dict(P, fp_maliyeti=True)), (M, dict(P, fp_maliyeti=-1)),
            (M, dict(P, fp_maliyeti=float("inf"))), (M, dict(P, fn_maliyeti="10")), (M, dict(P, fn_maliyeti=-1)),
            (M, dict(P, para_birimi="GBP")),
        ]:
            try:
                fn(matrisler, profil)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(maliyet_raporu), "FPR, maliyet, sıralama ve eşitlik kuralı korunmalı")
def m_maliyet(matrisler, profil):
    return maliyet_raporu(matrisler, dict(profil, fp_maliyeti=100))
def m_fn(matrisler, profil):
    return maliyet_raporu([dict(x, fn=0) for x in matrisler], profil)
def m_sira(matrisler, profil):
    return maliyet_raporu(list(reversed(matrisler)), profil)
for ad, mutant in [("FP maliyetini değiştiren", m_maliyet), ("FN sayılarını silen", m_fn), ("sırayı değiştiren", m_sira)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def maliyet_raporu(matrisler, profil):
    import math
    if not isinstance(profil, dict):
        raise ValueError("profil sözlük olmalı")
    if set(profil) != {"fp_maliyeti", "fn_maliyeti", "para_birimi"}:
        raise ValueError("profil şeması geçersiz")
    for alan in ("fp_maliyeti", "fn_maliyeti"):
        deger = profil[alan]
        if isinstance(deger, bool) or not isinstance(deger, (int, float)):
            raise ValueError("maliyet sayı olmalı")
        if not math.isfinite(deger):
            raise ValueError("maliyet sonlu olmalı")
        if deger < 0:
            raise ValueError("maliyet negatif olamaz")
    if profil["para_birimi"] not in ("TRY", "USD", "EUR"):
        raise ValueError("para birimi geçersiz")
    if not isinstance(matrisler, list):
        raise ValueError("matrisler liste olmalı")
    if not matrisler:
        raise ValueError("matrisler boş olamaz")
    esikler = set()
    satirlar = []
    toplam_kayit = None
    for matris in matrisler:
        if not isinstance(matris, dict):
            raise ValueError("matris sözlük olmalı")
        if set(matris) != {"esik", "tp", "fp", "fn", "tn"}:
            raise ValueError("matris şeması geçersiz")
        esik = matris["esik"]
        if isinstance(esik, bool) or not isinstance(esik, (int, float)):
            raise ValueError("eşik sayı olmalı")
        if not math.isfinite(esik):
            raise ValueError("eşik sonlu olmalı")
        if esik < 0 or esik > 1:
            raise ValueError("eşik aralık dışında")
        if esik in esikler:
            raise ValueError("eşik yinelenemez")
        for alan in ("tp", "fp", "fn", "tn"):
            deger = matris[alan]
            if isinstance(deger, bool) or not isinstance(deger, int):
                raise ValueError("sayım tamsayı olmalı")
            if deger < 0:
                raise ValueError("sayım negatif olamaz")
        toplam = sum(matris[a] for a in ("tp", "fp", "fn", "tn"))
        if toplam == 0:
            raise ValueError("matris boş veri kümesini temsil edemez")
        if toplam_kayit is None:
            toplam_kayit = toplam
        if toplam != toplam_kayit:
            raise ValueError("matrislerin kayıt sayıları farklı")
        fpr = matris["fp"] / (matris["fp"] + matris["tn"]) if matris["fp"] + matris["tn"] else None
        maliyet = matris["fp"] * profil["fp_maliyeti"] + matris["fn"] * profil["fn_maliyeti"]
        satirlar.append({"esik": esik, "tp": matris["tp"], "fp": matris["fp"], "fn": matris["fn"], "tn": matris["tn"], "fpr": round(fpr, 6) if fpr is not None else None, "maliyet": round(maliyet, 6), "_ham_maliyet": maliyet})
        esikler.add(esik)
    satirlar.sort(key=lambda x: x["esik"])
    en_iyi = min(satirlar, key=lambda x: (x["_ham_maliyet"], x["esik"]))["esik"]
    for satir in satirlar:
        del satir["_ham_maliyet"]
    return {"para_birimi": profil["para_birimi"], "en_iyi_esik": en_iyi, "satirlar": satirlar}
```

```hint
Her satırın ham maliyetini geçici olarak sakla. En iyi eşiği ham maliyet ve eşik çiftiyle seçip geçici alanı çıktıdan kaldır.
```
:::

::: anlat Canlı sınıflandırıcı olasılıklarında yanlış pozitif maliyeti ve eşik seçimi
İlk üç görevde maliyet profilini, eşik matrisini ve maliyet raporunu sentetik dosyalar üzerinde kurdun. Şimdi aynı üç işlevi **gerçek `scikit-learn` (`LogisticRegression`) sınıflandırıcısının test kümesi olasılık skorlarına** bağlıyoruz:

1. 120 eğitim örneğiyle eğitilen `LogisticRegression` modeli, 80 test örneği için `predict_proba` olasılık skorları üretir.
2. `esik_matrisi` beş farklı karar eşiğinde (`0.2, 0.35, 0.5, 0.65, 0.8`) canlı karışıklık matrislerini hesaplar.
3. `maliyet_raporu` hem kaçırılan saldırının ağır olduğu (`FN=15 TRY, FP=2 TRY`) hem de yanlış alarmın ağır olduğu (`FP=15 TRY, FN=2 TRY`) iki profilde en düşük maliyetli eşiği seçip kanıt dosyasına yazar.
:::

::: gorev Gerçek deney · Canlı sınıflandırıcı olasılıklarında maliyet duyarlı eşik seçimi
Önceki üç görevde yazdığın `maliyet_profili_dogrula(profil)`, `esik_matrisi(kayitlar, esik)` ve `maliyet_raporu(matrisler, profil)` işlevlerini burada birleştir.

```meta
motor: ai-gercek
gereksinim: torch
timeout: 180
```

```starter
import math
import re
import ai_lab
from sandbox import ai_gercek_ai_guvence_04 as L

def maliyet_profili_dogrula(profil):
    # KUSURLU BAŞLANGIÇ KODU: doğrulama yapmadan girdi sözlüğünü döndürüyor!
    return profil

def esik_matrisi(kayitlar, esik):
    # KUSURLU BAŞLANGIÇ KODU: eşik karşılaştırması yapmadan sabit sıfır hücreler döndürüyor!
    return {"esik": esik, "tp": 0, "fp": 0, "fn": 0, "tn": 0}

def maliyet_raporu(matrisler, profil):
    # KUSURLU BAŞLANGIÇ KODU: maliyet hesabı yapmadan sabit 0.5 eşiği döndürüyor!
    return {"para_birimi": "TRY", "en_iyi_esik": 0.5, "satirlar": []}

if ai_lab.CALISTIR:
    L.goster(maliyet_profili_dogrula, esik_matrisi, maliyet_raporu)
```

```test
import ast
import copy
import ai_lab
from sandbox import ai_gercek_ai_guvence_04 as L

checks = []
_base_ok = ok
def ok(kosul, mesaj):
    checks.append(bool(kosul))
    return _base_ok(kosul, mesaj)

try:
    _parsed = ast.parse(src)
    for _node in ast.walk(_parsed):
        if isinstance(_node, ast.ImportFrom):
            if any(alias.name == '*' for alias in _node.names):
                ok(False, "Güvenlik/kopya denetimi: wildcard import yasak")
            for alias in _node.names:
                if "referans" in (alias.name or "") or "referans" in (alias.asname or ""):
                    ok(False, "Güvenlik/kopya denetimi: referans fonksiyon içe aktarılamaz")
        if isinstance(_node, ast.Name) and "referans" in _node.id:
            ok(False, "Güvenlik/kopya denetimi: referans kullanımı tespit edildi")
        if isinstance(_node, ast.Attribute) and "referans" in _node.attr:
            ok(False, "Güvenlik/kopya denetimi: referans nitelik kullanımı tespit edildi")
        if isinstance(_node, ast.Call):
            if isinstance(_node.func, ast.Name) and _node.func.id in ("getattr", "eval", "exec"):
                ok(False, f"Güvenlik/kopya denetimi: dinamik çağrı ({_node.func.id}) yasak")
except Exception:
    pass

for s in ai_lab.kod_denetimi(src, yasak=("maliyet_profili_dogrula_referans", "esik_matrisi_referans", "maliyet_raporu_referans", "kanit_yaz")):
    ok(False, f"Güvenlik/kopya denetimi: {s}")
if not all(checks):
    stop()

def _sozlesme_kontrol():
    try:
        P = {"fp_maliyeti": 2.5, "fn_maliyeti": 10, "para_birimi": "TRY"}
        if maliyet_profili_dogrula(P) != P or maliyet_profili_dogrula(P) is P:
            return False
        for bp in [None, dict(P, ek=1), dict(P, fp_maliyeti=-1), dict(P, para_birimi="GBP"), dict(P, fn_maliyeti=True)]:
            try:
                maliyet_profili_dogrula(bp)
                return False
            except ValueError:
                pass

        K = [
            {"id": "r-1", "gercek": "yelkovan", "skor": 0.5},
            {"id": "r-2", "gercek": "diger", "skor": 0.5},
            {"id": "r-3", "gercek": "yelkovan", "skor": 0},
            {"id": "r-4", "gercek": "diger", "skor": 0},
        ]
        if esik_matrisi(K, 0.5) != {"esik": 0.5, "tp": 1, "fp": 1, "fn": 1, "tn": 1}:
            return False
        for bk, be in [(None, 0.5), ([], 0.5), ([K[0], K[0]], 0.5), (K, 1.2), (K, True)]:
            try:
                esik_matrisi(bk, be)
                return False
            except ValueError:
                pass

        M = [
            {"esik": 0.5, "tp": 1, "fp": 1, "fn": 1, "tn": 1},
            {"esik": 0.25, "tp": 2, "fp": 1, "fn": 0, "tn": 1},
            {"esik": 0.75, "tp": 0, "fp": 0, "fn": 2, "tn": 2},
        ]
        sr = maliyet_raporu(M, P)
        if sr["en_iyi_esik"] != 0.25 or [x["esik"] for x in sr["satirlar"]] != [0.25, 0.5, 0.75]:
            return False
        for bm, bpr in [(None, P), ([], P), ([M[0], M[0]], P), ([M[0], dict(M[1], tn=0)], P)]:
            try:
                maliyet_raporu(bm, bpr)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

def _birim1(fn):
    import copy
    P = {"fp_maliyeti": 2.5, "fn_maliyeti": 10, "para_birimi": "TRY"}
    def sozlesme(fn):
        try:
            once = copy.deepcopy(P)
            sonuc = fn(P)
            if sonuc != P or P != once or sonuc is P:
                return False
            if fn({"fp_maliyeti": 0, "fn_maliyeti": 0, "para_birimi": "EUR"})["fn_maliyeti"] != 0:
                return False
            for profil in [
                None, [], dict(P, ek=1), dict(P, fp_maliyeti=None), dict(P, fp_maliyeti=True),
                dict(P, fp_maliyeti="2.5"), dict(P, fp_maliyeti=float("nan")), dict(P, fp_maliyeti=float("inf")),
                dict(P, fp_maliyeti=-0.1), dict(P, fn_maliyeti=None), dict(P, fn_maliyeti=True),
                dict(P, fn_maliyeti="10"), dict(P, fn_maliyeti=float("nan")), dict(P, fn_maliyeti=float("inf")),
                dict(P, fn_maliyeti=-1), dict(P, para_birimi="GBP"), dict(P, para_birimi="try"), dict(P, para_birimi=None),
            ]:
                try:
                    fn(profil)
                    return False
                except ValueError:
                    pass
            return True
        except Exception:
            return False
    return sozlesme(fn)

def _birim2(fn):
    import copy
    K = [
        {"id": "r-1", "gercek": "yelkovan", "skor": 0.5},
        {"id": "r-2", "gercek": "diger", "skor": 0.5},
        {"id": "r-3", "gercek": "yelkovan", "skor": 0},
        {"id": "r-4", "gercek": "diger", "skor": 0},
    ]
    def sozlesme(fn):
        try:
            once = copy.deepcopy(K)
            if fn(K, 0.5) != {"esik": 0.5, "tp": 1, "fp": 1, "fn": 1, "tn": 1} or K != once:
                return False
            if fn(K, 0) != {"esik": 0, "tp": 2, "fp": 2, "fn": 0, "tn": 0}:
                return False
            if fn(K, 1) != {"esik": 1, "tp": 0, "fp": 0, "fn": 2, "tn": 2}:
                return False
            if fn([dict(K[0], skor=1)], 1)["tp"] != 1:
                return False
            if fn([K[3]], 1) != {"esik": 1, "tp": 0, "fp": 0, "fn": 0, "tn": 1}:
                return False
            if fn([dict(K[0], id="a" * 64)], 0.5)["tp"] != 1:
                return False
            for kayitlar, esik in [
                (None, 0.5), (tuple(K), 0.5), (K, False), ({}, 0.5), ([], 0.5), ([None], 0.5), ([dict(K[0], ek=1)], 0.5), ([dict(K[0], id=123)], 0.5),
                ([dict(K[0], id="")], 0.5), ([dict(K[0], id="a b")], 0.5), ([dict(K[0], id="a" * 65)], 0.5),
                ([dict(K[0], id=None)], 0.5), ([K[0], K[0]], 0.5),
                ([dict(K[0], gercek="baska")], 0.5), ([dict(K[0], gercek=None)], 0.5),
                ([dict(K[0], skor=True)], 0.5), ([dict(K[0], skor="0.5")], 0.5),
                ([dict(K[0], skor=float("nan"))], 0.5), ([dict(K[0], skor=float("inf"))], 0.5),
                ([dict(K[0], skor=-0.1)], 0.5), ([dict(K[0], skor=1.1)], 0.5),
                (K, None), (K, True), (K, "0.5"), (K, float("nan")), (K, float("inf")), (K, -0.1), (K, 1.1),
            ]:
                try:
                    fn(kayitlar, esik)
                    return False
                except ValueError:
                    pass
            return True
        except Exception:
            return False
    return sozlesme(fn)

def _birim3(fn):
    import copy
    P = {"fp_maliyeti": 2.5, "fn_maliyeti": 10, "para_birimi": "TRY"}
    M = [
        {"esik": 0.5, "tp": 1, "fp": 1, "fn": 1, "tn": 1},
        {"esik": 0.25, "tp": 2, "fp": 1, "fn": 0, "tn": 1},
        {"esik": 0.75, "tp": 0, "fp": 0, "fn": 2, "tn": 2},
    ]
    def sozlesme(fn):
        try:
            monce = copy.deepcopy(M)
            ponce = copy.deepcopy(P)
            sonuc = fn(M, P)
            if M != monce or P != ponce or sonuc["para_birimi"] != "TRY" or sonuc["en_iyi_esik"] != 0.25:
                return False
            if [x["esik"] for x in sonuc["satirlar"]] != [0.25, 0.5, 0.75]:
                return False
            if sonuc["satirlar"][0]["maliyet"] != 2.5 or sonuc["satirlar"][1]["maliyet"] != 12.5 or sonuc["satirlar"][2]["maliyet"] != 20:
                return False
            if sonuc["satirlar"][0]["fpr"] != 0.5 or sonuc["satirlar"][2]["fpr"] != 0:
                return False
            esit_p = {"fp_maliyeti": 1, "fn_maliyeti": 1, "para_birimi": "USD"}
            esit_m = [{"esik": 0.5, "tp": 0, "fp": 0, "fn": 1, "tn": 0}, {"esik": 0.25, "tp": 0, "fp": 1, "fn": 0, "tn": 0}]
            esit = fn(esit_m, esit_p)
            if esit["en_iyi_esik"] != 0.25 or esit["satirlar"][0]["fpr"] != 1 or esit["satirlar"][1]["fpr"] is not None:
                return False
            yuvarla = fn([{"esik": 1, "tp": 0, "fp": 1, "fn": 0, "tn": 0}], {"fp_maliyeti": 1 / 3, "fn_maliyeti": 0, "para_birimi": "EUR"})
            if yuvarla["satirlar"][0]["maliyet"] != 0.333333:
                return False
            fpr_yuvarla = fn([{"esik": 0, "tp": 0, "fp": 1, "fn": 0, "tn": 2}], P)
            if fpr_yuvarla["satirlar"][0]["fpr"] != 0.333333:
                return False
            for matrisler, profil in [
                (None, P), (tuple(M), P), ({}, P), ([], P), ([None], P), ([dict(M[0], ek=1)], P),
                ([dict(M[0], esik=True)], P), ([dict(M[0], esik="0.5")], P), ([dict(M[0], esik=float("nan"))], P),
                ([dict(M[0], esik=-0.1)], P), ([dict(M[0], esik=1.1)], P), ([M[0], M[0]], P),
                ([dict(M[0], tp=True)], P), ([dict(M[0], tp=1.0)], P), ([dict(M[0], tp=-1)], P),
                ([dict(M[0], fp=True)], P), ([dict(M[0], fp=1.0)], P), ([dict(M[0], fp=-1)], P),
                ([dict(M[0], fn=True)], P), ([dict(M[0], fn=1.0)], P), ([dict(M[0], fn=-1)], P),
                ([dict(M[0], tn=True)], P), ([dict(M[0], tn=1.0)], P), ([dict(M[0], tn=-1)], P),
                ([{"esik": 0.5, "tp": 0, "fp": 0, "fn": 0, "tn": 0}], P),
                ([M[0], dict(M[1], esik=0.75, tn=0)], P),
                (M, None), (M, dict(P, ek=1)), (M, dict(P, fp_maliyeti=True)), (M, dict(P, fp_maliyeti=-1)),
                (M, dict(P, fp_maliyeti=float("inf"))), (M, dict(P, fn_maliyeti="10")), (M, dict(P, fn_maliyeti=-1)),
                (M, dict(P, para_birimi="GBP")),
            ]:
                try:
                    fn(matrisler, profil)
                    return False
                except ValueError:
                    pass
            return True
        except Exception:
            return False
    return sozlesme(fn)

ok(_birim1(maliyet_profili_dogrula), "maliyet_profili_dogrula tam birim sözleşmesini geçmeli")
ok(_birim2(esik_matrisi), "esik_matrisi tam birim sözleşmesini geçmeli")
ok(_birim3(maliyet_raporu), "maliyet_raporu tam birim sözleşmesini geçmeli")
ok(_sozlesme_kontrol(), "maliyet_profili_dogrula, esik_matrisi ve maliyet_raporu sözleşme kontrollerini geçmeli")
if not all(checks):
    stop()

try:
    rapor = L.deney(maliyet_profili_dogrula, esik_matrisi, maliyet_raporu)
except ai_lab.GercekLabYok as e:
    ok(False, str(e))
    stop()
except Exception as e:
    ok(False, f"GERÇEK MALİYET DENEYİ YAPILAMADI: {type(e).__name__}: {e}")
    stop()

k = rapor["kontroller"]
ok(k["profil_uyumu"], f"maliyet_profili_dogrula canlı profilde referansla uyuşmalı: {rapor['profil']}")
ok(k["matris_uyumu"], f"esik_matrisi 5 canlı eşikte referansla uyuşmalı")
ok(k["fn_agir_rapor_uyumu"] and k["fp_agir_rapor_uyumu"] and k["maliyet_esigi_kaydirdi"], f"maliyet_raporu FN-ağır ({rapor['ozet']['fn_agir_en_iyi_esik']}) ve FP-ağır ({rapor['ozet']['fp_agir_en_iyi_esik']}) profillerde referansla uyuşmalı")

kabul = all(checks)
kanit_yolu = ai_lab.kanit_yaz("guvence-04-maliyet-esik", dict(rapor, kaynak="gercek", kabul=kabul))
o = rapor["ozet"]
print(f"GERÇEK MALİYET DENEYİ: fn_agir_esik={o['fn_agir_en_iyi_esik']} fp_agir_esik={o['fp_agir_en_iyi_esik']} kanıt={kanit_yolu}")
```

```solution
import math
import re
import ai_lab
from sandbox import ai_gercek_ai_guvence_04 as L

def maliyet_profili_dogrula(profil):
    if not isinstance(profil, dict) or set(profil) != {"fp_maliyeti", "fn_maliyeti", "para_birimi"}:
        raise ValueError("profil şeması geçersiz")
    for alan in ("fp_maliyeti", "fn_maliyeti"):
        deger = profil[alan]
        if isinstance(deger, bool) or not isinstance(deger, (int, float)) or not math.isfinite(deger) or deger < 0:
            raise ValueError("maliyet geçersiz")
    if profil["para_birimi"] not in ("TRY", "USD", "EUR"):
        raise ValueError("para birimi geçersiz")
    return {"fp_maliyeti": profil["fp_maliyeti"], "fn_maliyeti": profil["fn_maliyeti"], "para_birimi": profil["para_birimi"]}

def esik_matrisi(kayitlar, esik):
    if isinstance(esik, bool) or not isinstance(esik, (int, float)) or not math.isfinite(esik) or esik < 0 or esik > 1:
        raise ValueError("eşik geçersiz")
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar geçersiz")
    gorulen = set()
    sonuc = {"esik": esik, "tp": 0, "fp": 0, "fn": 0, "tn": 0}
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"id", "gercek", "skor"}:
            raise ValueError("kayıt şeması geçersiz")
        kimlik = kayit["id"]
        if not isinstance(kimlik, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kimlik) or kimlik in gorulen:
            raise ValueError("kimlik geçersiz")
        if kayit["gercek"] not in ("yelkovan", "diger"):
            raise ValueError("etiket geçersiz")
        skor = kayit["skor"]
        if isinstance(skor, bool) or not isinstance(skor, (int, float)) or not math.isfinite(skor) or skor < 0 or skor > 1:
            raise ValueError("skor geçersiz")
        tahmin = "yelkovan" if skor >= esik else "diger"
        if kayit["gercek"] == "yelkovan" and tahmin == "yelkovan":
            sonuc["tp"] += 1
        elif kayit["gercek"] == "diger" and tahmin == "yelkovan":
            sonuc["fp"] += 1
        elif kayit["gercek"] == "yelkovan":
            sonuc["fn"] += 1
        else:
            sonuc["tn"] += 1
        gorulen.add(kimlik)
    return sonuc

def maliyet_raporu(matrisler, profil):
    p = maliyet_profili_dogrula(profil)
    if not isinstance(matrisler, list) or not matrisler:
        raise ValueError("matrisler geçersiz")
    esikler = set()
    satirlar = []
    toplam_kayit = None
    for matris in matrisler:
        if not isinstance(matris, dict) or set(matris) != {"esik", "tp", "fp", "fn", "tn"}:
            raise ValueError("matris şeması geçersiz")
        esik = matris["esik"]
        if isinstance(esik, bool) or not isinstance(esik, (int, float)) or not math.isfinite(esik) or esik < 0 or esik > 1 or esik in esikler:
            raise ValueError("eşik geçersiz")
        for alan in ("tp", "fp", "fn", "tn"):
            deger = matris[alan]
            if isinstance(deger, bool) or not isinstance(deger, int) or deger < 0:
                raise ValueError("sayım geçersiz")
        toplam = sum(matris[a] for a in ("tp", "fp", "fn", "tn"))
        if toplam == 0:
            raise ValueError("matris boş")
        if toplam_kayit is None:
            toplam_kayit = toplam
        if toplam != toplam_kayit:
            raise ValueError("toplam kayıt sayısı farklı")
        fpr = matris["fp"] / (matris["fp"] + matris["tn"]) if matris["fp"] + matris["tn"] else None
        maliyet = matris["fp"] * p["fp_maliyeti"] + matris["fn"] * p["fn_maliyeti"]
        satirlar.append({"esik": esik, "tp": matris["tp"], "fp": matris["fp"], "fn": matris["fn"], "tn": matris["tn"], "fpr": round(fpr, 6) if fpr is not None else None, "maliyet": round(maliyet, 6), "_ham": maliyet})
        esikler.add(esik)
    satirlar.sort(key=lambda x: x["esik"])
    en_iyi = min(satirlar, key=lambda x: (x["_ham"], x["esik"]))["esik"]
    for s in satirlar:
        del s["_ham"]
    return {"para_birimi": p["para_birimi"], "en_iyi_esik": en_iyi, "satirlar": satirlar}

if ai_lab.CALISTIR:
    L.goster(maliyet_profili_dogrula, esik_matrisi, maliyet_raporu)
```

```hint
Önceki üç görevde yazdığın `maliyet_profili_dogrula`, `esik_matrisi` ve `maliyet_raporu` işlevlerini eksiksiz taşı; canlı deneyde 80 test örneğinin `predict_proba` skorları üzerinde sınanır.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **SOC'ta asimetrik hata maliyeti (30 sn).** "Kaçırılan saldırı (`FN`) veri ihlaline, yanlış alarm (`FP`) ise analist kuyruğunun kilitlenmesine yol açar; bu yüzden varsayılan `0.5` olasılık eşiği güvenlikte nadiren optimaldir."
2. **Maliyet duyarlı eşik taraması (35 sn).** "Her aday $\tau$ eşiğinde hata matrisi ve `FPR` çıkarılır; $FP \cdot c_{FP} + FN \cdot c_{FN}$ toplam maliyetini en küçük yapan eşik seçilir, eşitlikte daha fazla şüpheliyi yakalayan düşük eşik tercih edilir."
3. **Temel oran yanılgısı (`base rate fallacy`) (30 sn).** "Dengeli laboratuvar verisinde iyi görünen bir eşik, saldırı oranının on binde bir olduğu gerçek trafikte binlerce yanlış alarm üretebilir."
4. **Soru (25 sn).** "Farklı aday eşiklere ait hata matrislerinin toplam kayıt sayıları (`tp + fp + fn + tn`) birbirinden farklıysa maliyet karşılaştırması neden geçersizdir?"
:::
