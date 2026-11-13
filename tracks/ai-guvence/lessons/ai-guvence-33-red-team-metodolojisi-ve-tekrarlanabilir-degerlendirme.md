---
id: ai-guvence-33
title: "Red Team Metodolojisi ve Tekrarlanabilir Değerlendirme"
summary: Kapsam ve kuralı doğrula, bulguyu şiddetle puanla ve birleştir, iddiayı tek koşuyla değil gerçek modelde N koşunun tekrarlanabilirliğiyle kanıtla.
esleme: ai-guvence-01, ai-guvence-29, ai-guvence-30
timeout: 45
---

::: anlat Metodoloji: kapsam, kural, ölçüm ve raporlama bir disiplindir
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Red team değerlendirmesi kapsam, ölçüt, ham yanıt ve tekrarlı koşuları birlikte kaydeder | İlk üç görevde `veri/kapsam.json` ve `veri/bulgular.json` içinde elle yazılmış sentetik kapsam/bulgular; son görevde yerel Ollama modeliyle üç zararsız probe ve beşer canlı koşu | Beş koşu genellenebilir güvenlik oranı değildir; bu dersin aynı bool sonucuna “tekrarlanabilir” demesi tam metinlerin aynı olduğunu veya farklı cihazlarda yeniden üretilebilirliği kanıtlamaz |

> [!NOT]
> Dosyalar **sentetik eğitim örneğidir**, gerçek olay veya model kaydı değildir. **Çalıştır** kodu JSON dosyasını okuyup içeriğini ve sonucunu gösterir. Aynı çalıştırmada geçici kopyayı koddan değiştirebilirsin; sonraki çalıştırmada kaynak yeniden kopyalanır, kalıcılık yoktur. Gizli testler ayrı girdiler kullanır. Son görev gerçek model çağırır; teknik çağrı hatası ders kabulünü engeller, modelin probe'u geçememesi ise ölçülen bulgudur.

Bir AI red team çalışması "modeli kurcalayıp ilginç bir şey bulmak" değildir; tekrarlanabilir, savunulabilir ve zarar vermeyen bir **disiplindir**. İlk adım **kapsam** (scope) ve **angajman kuralları** (rules of engagement): hangi hedefler kapsam içinde, hangileri açıkça yasak, hangi eylemlere izin var. Kapsamsız bir test ya eksik kalır ya da yetkisiz bir yere dokunur; bu yüzden kapsam en başta yazılır ve hedefle yasak listesi çakışmaz. Bulunan her sorun **şiddetle** (severity) puanlanır — etkisi ve sömürülebilirliği (erişim kolaylığı) birleştirilerek düşük/orta/yüksek/kritik bir seviyeye oturtulur; bu, hangi bulgunun önce düzeltileceğini belirler. Aynı kök nedenin farklı yerlerdeki tekrarları tek bir **birleştirilmiş** bulguya indirgenir ki rapor gürültüye boğulmasın.

Ama metodolojinin kalbi şudur: bir dil modeli olasılıkçıdır, aynı girdi farklı koşularda farklı çıktı verebilir. Bu yüzden **tek bir koşu genel başarı oranını kanıtlamaz.** Bir başarılı sızıntı kendi koşulu için karşı örnek olabilir; yaygınlık ve güvenilirlik iddiası ayrıca ölçülür. "Model bu jailbreak'e düştü" ya da "bu savunma işe yarıyor" demek için aynı testi birçok kez (farklı tohumlarla) koşturur, **geçme oranını** ve **tekrarlanabilirliği** (sonuç her koşuda aynı mı) ölçersin. Tekrarlanabilir olmayan bir bulgu — bazen olup bazen olmayan — raporda bu belirsizliğiyle yazılır; "bir kez gördüm" ile "beş koşuda beşinde de oldu" aynı şey değildir.
:::

::: anlat Ölçüm gerçek koşular üzerinden, raporlama şiddet sırasına göre
Tekrarlanabilirlik basit bir orandır: N koşunun kaçında test geçti. Oran eşiğe eşit veya yüksekse "geçti" denir; ama asıl bilgi, sonucun **tutarlı** olup olmadığıdır — hepsi geçti ya da hepsi kaldıysa sonuç tekrarlanabilirdir, karışıksa model kararsızdır ve bu da bir bulgudur. Şiddet ise bu dersin öğretim amaçlı sabit kuralıyla (etki + erişim) belirlenir ki iki farklı değerlendirici aynı bulguya aynı seviyeyi versin; öznel "bence kritik" yerine yazılı bir ölçüt kullanılır. Rapor, bulguları şiddet sırasına göre dizer: önce kritik, sonra yüksek — okuyan önce en acil olanı görsün.

Bu derste önce kapsam doğrulamayı, şiddet puanlamayı ve bulgu birleştirmeyi saf Python'la kurarsın. `veri/kapsam.json` hedefleri, yasakları ve izinleri; `veri/bulgular.json` bulgu kategorilerini, etki/erişim etiketlerini ve şiddetleri içerir. Üç görev bu dosyaları okuyarak ilerler. Çalıştır çıktısından ham JSON'a bakabilir, koddan kopyayı değiştirip aynı çalıştırmada tekrar ölçebilirsin; sonraki çalıştırmada örnek sıfırlanır. Son görevdeki tekrarlanabilirlik ise **canlı gerçek deneydir**: zararsız birkaç probe gerçek yerel modele farklı tohumlarla beş kez koşturulur ve geçme oranı/tutarlılık senin özetinle ölçülür.
:::

::: tahmin Şiddet, tekrarlanabilirlik ve sıralama çıktısını tahmin et
Üç çıktı satırını yaz:

```python
E = {"dusuk": 1, "orta": 2, "yuksek": 3}
A = {"zor": 1, "orta": 2, "kolay": 3}
toplam = E["orta"] + A["kolay"]
print(toplam, {2: "dusuk", 3: "orta", 4: "yuksek", 5: "kritik", 6: "kritik"}[toplam])
kosular = [True, True, False, True, True]
print(round(sum(kosular) / len(kosular), 4), sum(kosular) in (0, len(kosular)))
rank = {"kritik": 3, "yuksek": 2, "orta": 1, "dusuk": 0}
print(sorted(["orta", "kritik", "dusuk"], key=lambda s: -rank[s]))
```

???

```cikti
5 kritik
0.8 False
['kritik', 'orta', 'dusuk']
```

İlk satır şiddet puanıdır: orta etki (2) + kolay erişim (3) = 5 → kritik; sabit kural öznel yargıyı dışlar. İkinci satır tekrarlanabilirlik: beş koşunun dördü geçmiş (oran 0.8) ama hepsi aynı olmadığından sonuç tekrarlanabilir **değildir** — model kararsız. Üçüncü satır bulguları şiddet sırasına dizer; rapor önce en acili gösterir.
:::

::: gorev 1 · Kapsam ve angajman kuralını doğrula
`kapsam_dogrula(kapsam)` işlevini yaz. `kapsam` tam `hedefler`, `yasak`, `izinli_eylemler` anahtarlı sözlüktür. `hedefler` 1–100 öğeli, boş olmayan, yinelenmeyen string listesidir (kapsam içi). `yasak` 0–100 öğeli, boş olmayan, yinelenmeyen string listesidir (açıkça kapsam dışı). `izinli_eylemler` 1–20 öğeli, her öğesi `{"oku", "sorgula", "olc", "raporla"}` kümesinden, yinelenmeyen listedir. `hedefler` ile `yasak` **kesişmemelidir**. Geçersiz veride `ValueError` yükselt.

`{"hedefler": sıralı, "yasak": sıralı, "izinli_eylemler": sıralı}` (hepsi alfabetik) döndür.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-33")
```

```starter
from ai_guvence_veri import json_yukle

def kapsam_dogrula(kapsam):
    # KUSURLU BAŞLANGIÇ KODU: listeleri sıralıyor ama kapsam/yasak çakışmasını ve geçersiz izinleri reddetmiyor.
    return {k:sorted(v) for k,v in kapsam.items()}

v=json_yukle("veri/kapsam.json")
print("Sentetik kapsam:",v)
print("Doğrulanmış kapsam:",kapsam_dogrula(v))
```

```test
def sozlesme(fn):
    try:
        k = {"hedefler": ["model-a", "model-b"], "yasak": ["prod"], "izinli_eylemler": ["sorgula", "oku"]}
        if fn(k) != {"hedefler": ["model-a", "model-b"], "yasak": ["prod"], "izinli_eylemler": ["oku", "sorgula"]}:
            return False
        if fn({"hedefler": ["x"], "yasak": [], "izinli_eylemler": ["olc"]}) != {"hedefler": ["x"], "yasak": [], "izinli_eylemler": ["olc"]}:
            return False
        iyi = {"hedefler": ["a"], "yasak": ["b"], "izinli_eylemler": ["oku"]}
        for kotu in [None, [], {"hedefler": ["a"]}, dict(iyi, ek=1), {**iyi, "hedefler": []}, {**iyi, "hedefler": ["a", "a"]},
                     {**iyi, "hedefler": [""]}, {**iyi, "hedefler": [1]}, {**iyi, "yasak": ["b", "b"]}, {**iyi, "yasak": [""]},
                     {**iyi, "izinli_eylemler": []}, {**iyi, "izinli_eylemler": ["ucus"]}, {**iyi, "izinli_eylemler": ["oku", "oku"]},
                     {"hedefler": ["a"], "yasak": ["a"], "izinli_eylemler": ["oku"]}]:
            try:
                fn(kotu)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(kapsam_dogrula), "kapsam/RoE doğrulama (çakışma ve izinli eylem) doğru; geçersiz girdi reddedilmeli")
def m_cakisma(k):
    return {"hedefler": sorted(k["hedefler"]), "yasak": sorted(k["yasak"]), "izinli_eylemler": sorted(k["izinli_eylemler"])}  # çakışma denetimi yok
def m_eylem(k):
    import copy
    kk = copy.deepcopy(k); kk["izinli_eylemler"] = list(kk["izinli_eylemler"]) + ["ucus"]
    return {"hedefler": sorted(kk["hedefler"]), "yasak": sorted(kk["yasak"]), "izinli_eylemler": sorted(set(kk["izinli_eylemler"]))}
ok(not sozlesme(m_cakisma), "yanlış çözüm/mutant yakalanmalı: hedef-yasak çakışmasını denetlemeyen")
import copy
sinir={"hedefler":["h"+str(i) for i in range(100)],"yasak":["y"+str(i) for i in range(100)],"izinli_eylemler":["raporla","oku","sorgula","olc"]}
yedek=copy.deepcopy(sinir)
eq(kapsam_dogrula(sinir),{k:sorted(v) for k,v in sinir.items()},"yüz hedef/yasak sınırı dahil ve dört izin")
eq(sinir,yedek,"girdi değişmemeli")
for arg in [dict(sinir,hedefler=["h"+str(i) for i in range(101)]),dict(sinir,yasak=["y"+str(i) for i in range(101)]),dict(sinir,yasak=None),dict(sinir,yasak=[5]),dict(sinir,hedefler="x"),dict(sinir,izinli_eylemler="oku"),dict(sinir,izinli_eylemler=[1])]:
    try:
        kapsam_dogrula(arg)
        ok(False,"bozuk kapsam reddedilmeli")
    except ValueError:
        ok(True,"bozuk kapsam reddedildi")
```

```solution
from ai_guvence_veri import json_yukle
def kapsam_dogrula(kapsam):
    IZIN = {"oku", "sorgula", "olc", "raporla"}
    if not isinstance(kapsam, dict) or set(kapsam) != {"hedefler", "yasak", "izinli_eylemler"}:
        raise ValueError("kapsam alanları: hedefler, yasak, izinli_eylemler")
    def liste(ad, v, alt, ust):
        if not isinstance(v, list) or not alt <= len(v) <= ust or any(not isinstance(x, str) or not x for x in v) or len(set(v)) != len(v):
            raise ValueError(f"{ad} geçersiz")
    liste("hedefler", kapsam["hedefler"], 1, 100)
    liste("yasak", kapsam["yasak"], 0, 100)
    liste("izinli_eylemler", kapsam["izinli_eylemler"], 1, len(IZIN))
    if any(e not in IZIN for e in kapsam["izinli_eylemler"]):
        raise ValueError("izinli_eylemler yalnız oku/sorgula/olc/raporla olabilir")
    if set(kapsam["hedefler"]) & set(kapsam["yasak"]):
        raise ValueError("hedefler ile yasak çakışamaz")
    return {"hedefler": sorted(kapsam["hedefler"]), "yasak": sorted(kapsam["yasak"]),
            "izinli_eylemler": sorted(kapsam["izinli_eylemler"])}

if __name__ == "__main__":
    v=json_yukle("veri/kapsam.json")
    print("Sentetik kapsam:",v)
    print("Doğrulanmış kapsam:",kapsam_dogrula(v))
```

```hint
Her listeyi ayrı doğrula (boş olmama, yinelenmeme, uzunluk), `izinli_eylemler`'i sabit kümeyle sınırla ve en önemlisi `hedefler` ile `yasak`'ın **kesişmediğini** denetle — kapsam içi ve açıkça yasak bir hedef aynı anda olamaz. Hepsini `sorted` ile döndür.
```
:::

::: gorev 2 · Bulguyu şiddetle puanla
`siddet(etki, erisim)` işlevini yaz. `etki` `{"dusuk", "orta", "yuksek"}` kümesinden (etki büyüklüğü), `erisim` `{"zor", "orta", "kolay"}` kümesinden (sömürü/erişim kolaylığı) bir stringdir. Geçersiz veride `ValueError` yükselt.

Her ikisini 1–3 arası puana çevir (dusuk/zor=1, orta=2, yuksek/kolay=3), topla. Toplam 2 → `"dusuk"`, 3 → `"orta"`, 4 → `"yuksek"`, 5 veya 6 → `"kritik"` döndür.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-33")
```

```starter
from ai_guvence_veri import json_yukle

def siddet(etki, erisim):
    # KUSURLU BAŞLANGIÇ KODU: erişim kolaylığını yok sayıp yalnız etkiyi kullanıyor.
    return {"dusuk":"dusuk","orta":"orta","yuksek":"kritik"}[etki]

v=json_yukle("veri/bulgular.json")
print("Sentetik bulgular:",v)
for b in v:
    print(b["kategori"],siddet(b["etki"],b["erisim"]))
```

```test
def sozlesme(fn):
    try:
        beklenen = {("dusuk", "zor"): "dusuk", ("dusuk", "orta"): "orta", ("orta", "zor"): "orta",
                    ("orta", "orta"): "yuksek", ("dusuk", "kolay"): "yuksek", ("yuksek", "zor"): "yuksek",
                    ("orta", "kolay"): "kritik", ("yuksek", "orta"): "kritik", ("yuksek", "kolay"): "kritik"}
        for (e, a), s in beklenen.items():
            if fn(e, a) != s:
                return False
        for kotu in [(None, "zor"), ("dusuk", None), ("belirsiz", "zor"), ("dusuk", "cok"), (1, "zor"), ("dusuk", 2), ("Dusuk", "zor")]:
            try:
                fn(*kotu)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(siddet), "etki + erişim şiddet kuralı doğru; geçersiz girdi reddedilmeli")
def m_tek(e, a):
    return {"dusuk": "dusuk", "orta": "orta", "yuksek": "kritik"}[e]  # yalnız etkiye bakar
def m_esik(e, a):
    t = {"dusuk": 1, "orta": 2, "yuksek": 3}[e] + {"zor": 1, "orta": 2, "kolay": 3}[a]
    return {2: "dusuk", 3: "orta", 4: "orta", 5: "yuksek", 6: "kritik"}[t]  # eşikleri kaydırır
for ad, mut in [("yalnız etkiye bakan", m_tek), ("şiddet eşiğini kaydıran", m_esik)]:
    ok(not sozlesme(mut), "yanlış çözüm/mutant yakalanmalı: " + ad)
for args in [([],"zor"),("dusuk",{}),(True,"zor"),("dusuk",False)]:
    try:
        siddet(*args)
        ok(False,"şiddet alanı string olmalı")
    except ValueError:
        ok(True,"şiddet alanı reddedildi")
```

```solution
from ai_guvence_veri import json_yukle
def siddet(etki, erisim):
    E = {"dusuk": 1, "orta": 2, "yuksek": 3}
    A = {"zor": 1, "orta": 2, "kolay": 3}
    if not isinstance(etki, str) or etki not in E:
        raise ValueError("etki dusuk/orta/yuksek olmalı")
    if not isinstance(erisim, str) or erisim not in A:
        raise ValueError("erisim zor/orta/kolay olmalı")
    toplam = E[etki] + A[erisim]
    return {2: "dusuk", 3: "orta", 4: "yuksek", 5: "kritik", 6: "kritik"}[toplam]

if __name__ == "__main__":
    v=json_yukle("veri/bulgular.json")
    print("Sentetik bulgular:",v)
    for b in v:
        print(b["kategori"],siddet(b["etki"],b["erisim"]))
```

```hint
Etki ve erişimi 1–3 puana çevirip topla; toplam 2–6 arasıdır. Sabit bir eşleme (2=düşük, 3=orta, 4=yüksek, 5-6=kritik) öznel yargıyı dışlar; iki değerlendirici aynı bulguya aynı seviyeyi verir.
```
:::

::: gorev 3 · Bulguları birleştir ve şiddete göre sırala
`bulgu_birlestir(bulgular)` işlevini yaz. `bulgular` 1–1000 öğeli listedir; her öğe tam `kategori` (boş olmayan str) ve `siddet` (`{"dusuk", "orta", "yuksek", "kritik"}`) anahtarlı sözlüktür. Geçersiz veride `ValueError` yükselt.

Aynı `kategori`'deki bulguları tek kayda indirge: o kategorinin adedi (kaç bulgu) ve **en yüksek** şiddeti. Sonucu şiddete göre azalan (kritik > yüksek > orta > düşük), eşitlikte kategoriye göre alfabetik sırala. Her öğe `{"kategori": …, "adet": …, "siddet": en yüksek}` olsun; liste döndür.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-33")
```

```starter
from ai_guvence_veri import json_yukle

def bulgu_birlestir(bulgular):
    # KUSURLU BAŞLANGIÇ KODU: aynı kategoride en yüksek yerine son görülen şiddeti tutuyor.
    kat={}
    for b in bulgular:
        k=b["kategori"]
        kat[k]={"kategori":k,"adet":kat.get(k,{}).get("adet",0)+1,"siddet":b["siddet"]}
    return sorted(kat.values(),key=lambda b:b["kategori"])

v=json_yukle("veri/bulgular.json")
print("Sentetik bulgular:",v)
print("Birleştirilmiş:",bulgu_birlestir([{"kategori":b["kategori"],"siddet":b["siddet"]} for b in v]))
```

```test
def b(k, s):
    return {"kategori": k, "siddet": s}
def sozlesme(fn):
    try:
        g = [b("injection", "orta"), b("injection", "kritik"), b("ssrf", "yuksek"), b("log", "dusuk"), b("injection", "dusuk")]
        if fn(g) != [{"kategori": "injection", "adet": 3, "siddet": "kritik"}, {"kategori": "ssrf", "adet": 1, "siddet": "yuksek"}, {"kategori": "log", "adet": 1, "siddet": "dusuk"}]:
            return False
        if fn([b("x", "orta")]) != [{"kategori": "x", "adet": 1, "siddet": "orta"}]:
            return False
        if fn([b("b", "yuksek"), b("a", "yuksek")]) != [{"kategori": "a", "adet": 1, "siddet": "yuksek"}, {"kategori": "b", "adet": 1, "siddet": "yuksek"}]:
            return False
        for kotu in [None, [], "x", [123], [b("a", "orta"), {"kategori": "b"}], [b("", "orta")], [b("a", "belirsiz")], [{"kategori": "a", "siddet": "orta", "ek": 1}], [b(1, "orta")]]:
            try:
                fn(kotu)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(bulgu_birlestir), "kategoriye göre birleştirme, en yüksek şiddet ve sıralama doğru")
RANK = {s:i for i,s in enumerate(("dusuk","orta","yuksek","kritik"))}
def m_adet(bl):
    cat = {}
    for x in bl:
        cat.setdefault(x["kategori"], []).append(x["siddet"])
    out = [{"kategori": k, "adet": 1, "siddet": max(v, key=lambda s: RANK[s])} for k, v in cat.items()]  # adet hep 1
    return sorted(out, key=lambda r: (-RANK[r["siddet"]], r["kategori"]))
def m_sira(bl):
    cat = {}
    for x in bl:
        cat.setdefault(x["kategori"], []).append(x["siddet"])
    out = [{"kategori": k, "adet": len(v), "siddet": max(v, key=lambda s: RANK[s])} for k, v in cat.items()]
    return sorted(out, key=lambda r: r["kategori"])  # şiddete göre sıralamaz
for ad, mut in [("adedi saymayan", m_adet), ("şiddete göre sıralamayan", m_sira)]:
    ok(not sozlesme(mut), "yanlış çözüm/mutant yakalanmalı: " + ad)
import copy
v=[{"kategori":"x","siddet":"orta"} for _ in range(1000)]
yedek=copy.deepcopy(v)
eq(bulgu_birlestir(v),[{"kategori":"x","adet":1000,"siddet":"orta"}],"bin bulgu sınırı dahil")
eq(v,yedek,"bulgular değişmemeli")
seq=[{"kategori":k,"siddet":s} for k,s in [("a","dusuk"),("b","orta"),("c","yuksek"),("d","kritik")]]
eq(bulgu_birlestir(seq),[{"kategori":x["kategori"],"adet":1,"siddet":x["siddet"]} for x in reversed(seq)],"bütün komşu şiddetler azalan sırada")
for arg in [v+[v[0]],[{"kategori":"x","siddet":[]}],[{"kategori":"x","siddet":True}],[{"kategori":"x","siddet":None}],[[]]]:
    try:
        bulgu_birlestir(arg)
        ok(False,"bozuk bulgu reddedilmeli")
    except ValueError:
        ok(True,"bozuk bulgu reddedildi")
```

```solution
from ai_guvence_veri import json_yukle
def bulgu_birlestir(bulgular):
    RANK = {s:i for i,s in enumerate(("dusuk","orta","yuksek","kritik"))}
    if not isinstance(bulgular, list) or not 1 <= len(bulgular) <= 1000:
        raise ValueError("bulgular bir ile bin öğeli liste olmalı")
    for x in bulgular:
        if not isinstance(x, dict) or set(x) != {"kategori", "siddet"} or not isinstance(x["kategori"], str) or not x["kategori"] or not isinstance(x["siddet"], str) or x["siddet"] not in RANK:
            raise ValueError("bulgu kategori(str) ve geçerli siddet içermeli")
    kat = {}
    for x in bulgular:
        kat.setdefault(x["kategori"], []).append(x["siddet"])
    sonuc = [{"kategori": k, "adet": len(v), "siddet": max(v, key=lambda s: RANK[s])} for k, v in kat.items()]
    return sorted(sonuc, key=lambda r: (-RANK[r["siddet"]], r["kategori"]))

if __name__ == "__main__":
    v=json_yukle("veri/bulgular.json")
    print("Sentetik bulgular:",v)
    print("Birleştirilmiş:",bulgu_birlestir([{"kategori":b["kategori"],"siddet":b["siddet"]} for b in v]))
```

```hint
Kategoriye göre grupla; her grubun adedi eleman sayısı, şiddeti ise en yüksek şiddet (`RANK` ile karşılaştır). Sıralama anahtarı `(-RANK[siddet], kategori)` — önce şiddet azalan, sonra kategori alfabetik.
```
:::

::: anlat Gerçek modelde tekrarlanabilir değerlendirme
Bu deneyde üç zararsız probe (basit aritmetik, bir olgu sorusu, bir biçim talimatı) gerçek yerel modele farklı tohumlarla **beşer kez** koşturulur; her koşuda beklenen yanıtın verilip verilmediği işaretlenir. Senin `tekrar_ozeti` işlevin her probe için geçme oranını ve sonucun tutarlı (hepsi aynı) olup olmadığını hesaplar. Böylece "bir kez çalıştı" ile "beş koşuda beşinde de geçiyor" ayrımını kendi ölçümünle görürsün — metodolojinin özü budur: tek koşu kanıt değildir. Bu deneyin değerlendiricisi normalize yanıtta beklenen işaretin bulunmasına bakar; örneğin bir sayının metinde geçmesi tüm cevabın doğru olduğunu ispatlamaz. Bu basit ölçüt genel bir anlamsal veya güvenlik hakemi değildir. “Tekrarlanabilir” burada yalnız geçme/kalmaların aynı olmasıdır; ham yanıtlar farklı olabilir. Beş koşunun oranına belirsizlik payı ve bu küçük probe kümesinin kapsam sınırı eşlik eder. Probe'lar zararsızdır; model bu deney tarafından yüklendiyse sonunda boşaltılır.

Kaynaklar: [NIST AI 600-1 — Artificial Intelligence Risk Management Framework: Generative AI Profile](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence), [Ganguli vd. 2022 — Red Teaming Language Models to Reduce Harms (arXiv:2209.07858)](https://arxiv.org/abs/2209.07858).
:::

::: gorev Gerçek deney · Tekrarlanabilirliği gerçek koşularda ölç
`tekrar_ozeti(kosular, esik)` işlevini yaz. `kosular` 1–1000 öğeli, her öğesi bool olan listedir (bir probe'un her koşusunda test geçti mi). `esik` bool olmayan, `0 ≤ esik ≤ 1` sayıdır (geçme oranı eşiği). Geçersiz veride `ValueError` yükselt.

`{"calisma": koşu sayısı, "gecen": geçen koşu sayısı, "oran": geçen/koşu (round 4), "tekrarlanabilir": bütün koşular aynı sonucu verdiyse (hepsi geçti ya da hepsi kaldı) True, "gecti": oran ≥ esik}` döndür.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab

def tekrar_ozeti(kosular, esik):
    return {}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_33 as deney
    deney.goster(tekrar_ozeti)
```

```test
import ai_lab
sonuclar = []
def kontrol(kosul, mesaj):
    sonuclar.append(bool(kosul))
    return ok(kosul, mesaj)
import ast
YASAK=("referans","referans_ozet","kanit_yaz","getattr")
sorun=ai_lab.kod_denetimi(src,YASAK)
for node in ast.walk(ast.parse(src)):
    if isinstance(node,ast.ImportFrom) and any(a.name in YASAK or a.name=="*" for a in node.names):
        sorun.append("referans import edilemez")
kontrol(not sorun,"Kendi tekrar özetini yaz; laboratuvar yamalanmamalı: "+", ".join(sorun))
if sorun:
    stop()
fn = need("tekrar_ozeti")
from sandbox import ai_gercek_ai_guvence_33 as D
def sozlesme(f):
    try:
        for ks, e in [([True] * 5, 0.8), ([True, True, False, True, True], 0.8), ([True, True, False, True, True], 0.81), ([False] * 3, 0.5), ([True, False], 0.5), ([True], 1.0), ([False],0), ([True]*1000,1), ([True,False,False],1/3), ([True,False,False],0.3334)]:
            if f(list(ks), e) != D.referans_ozet(list(ks), e):
                return False
        for kotu in [(None, 0.8), ([], 0.8), ("x", 0.8), ([True, 1], 0.8), ([True, "x"], 0.8), ([True], -0.1), ([True], 1.1), ([True], True), ([True], "0.8"), ([True]*1001,0.8), ([True],float("nan")), ([True],float("inf"))]:
            try:
                f(*kotu)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
kontrol(sozlesme(fn), "tekrarlanabilirlik özeti (oran, tutarlılık, geçti) doğru; geçersiz girdi reddedilmeli")
kontrol(not sozlesme(lambda ks, e: D.referans_ozet(ks, e, tekrar_gevsek=True)), "hatalı çözüm reddedilmeli: tekrarlanabilirliği orana bağlayan")
r, oz = None, None
if all(sonuclar):
    try:
        r = D.deney(fn)
    except ai_lab.GercekLabYok as e:
        kontrol(False, f"GERÇEK MODEL YOK, deney yapılmadı: {e}")
        stop()
    g = [k for k in r["kayitlar"]]
    kontrol(len(g)==len(D.PROBELER) and all(len(k["kosular"]) == D.TEKRAR for k in g), f"her probe {D.TEKRAR} kez koşturuldu")
    kontrol(all(k["ozet"] == D.referans_ozet(k["kosular"], D.ESIK) for k in g), "tekrarlanabilirlik özeti bağımsız hesapla aynı")
    kontrol(all(len(k["cagrilar"]) == D.TEKRAR and all(c["hata"] is None for c in k["cagrilar"]) for k in g), "bütün gerçek model çağrıları teknik hatasız tamamlanmalı")
    oz = D.ozet(r)
    kontrol(oz["probe"] >= 1, f"{oz['probe']} probe değerlendirildi")
yol = ai_lab.kanit_yaz("guvence-metodoloji", {"kaynak": "gercek", "kabul": all(sonuclar), "ders": "ai-guvence-33",
                                              "ortam": (r or {}).get("ortam"), "ozet": oz, "deney": r})
if oz:
    ok(True, f"BULGU ({r['ortam']['model']['ad']}): {oz['probe']} probe × {oz['tekrar']} koşu; {oz['gecen_probe']} probe geçti, "
             f"{oz['tekrarlanabilir_probe']} tekrarlanabilir. Oranlar: {oz['oranlar']}. Tek koşu kanıt değildir; metodoloji N koşuyla ölçer.")
```

```solution
import ai_lab

def tekrar_ozeti(kosular, esik):
    if not isinstance(kosular, list) or not 1 <= len(kosular) <= 1000 or any(not isinstance(x, bool) for x in kosular):
        raise ValueError("kosular 1-1000 öğeli bool listesi olmalı")
    if isinstance(esik, bool) or not isinstance(esik, (int, float)) or not 0 <= esik <= 1:
        raise ValueError("esik 0 ile 1 arası sayı olmalı")
    n = len(kosular)
    gecen = sum(1 for x in kosular if x)
    oran = gecen / n
    return {"calisma": n, "gecen": gecen, "oran": round(oran, 4),
            "tekrarlanabilir": gecen == 0 or gecen == n, "gecti": oran >= esik}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_33 as deney
    deney.goster(tekrar_ozeti)
```

```hint
`oran` geçen koşuların tüm koşulara oranıdır. `tekrarlanabilir`, sonucun **tutarlı** olmasıdır: ya hepsi geçti (`gecen == n`) ya da hiçbiri (`gecen == 0`); aradaki her değer modelin kararsızlığını gösterir ve orandan bağımsızdır. `gecti` ise orana eşik uygular.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Tek ekran görüntüsü metodoloji değildir (35 sn).** "Stokastik örnekleme yapan bir modelde tek bir koşunun geçmesi savunmanın sağlam olduğunu, tek bir şanslı denemenin de kalıcı kırılma olduğunu göstermez; değerlendirme açık kapsam kuralları altında $N$ bağımsız koşuyla yapılır."
2. **Geçme oranı (`gecti`) ile tutarlılık (`tekrarlanabilir`) ayrımı (30 sn).** "Beş koşunun dördünde geçen bir probe `%80` eşiğiyle `gecti=True` alabilir ama `tekrarlanabilir=False` bayrağı modelin sınırda kararsız davrandığını açıkça raporlar."
3. **Tekilleştirme ve şiddet puanlama (30 sn).** "Aynı kök zafiyetin on küçük varyantını on ayrı kritik bulgu diye saymak risk tablosunu şişirir; bulgular kural ve kök neden bazında birleştirilir."
4. **Soru (25 sn).** "`sicaklik = 0` ayarında bile donanım veya yığın (`batch`) farkları yüzünden yanıt değişebiliyorsa üretim öncesi `red team` paketinde kaç tekrar ve hangi tohum stratejisini seçersin?"
:::
