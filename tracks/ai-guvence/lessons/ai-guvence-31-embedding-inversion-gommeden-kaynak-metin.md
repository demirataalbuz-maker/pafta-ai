---
id: ai-guvence-31
title: "Embedding Inversion: Embedding Temsilinden Kaynak Metin"
summary: Gömmenin kaynak metni ne kadar sızdırdığını ölç; parafraz geri-çıkarma (recovery@k) ve nitelik çıkarımını gerçek gömmelerde gör.
esleme: ai-guvence-16, ai-guvence-38, ai-uretim-09
timeout: 45
---

::: anlat embedding anonim değildir: vektör kaynağı hakkında çok şey taşır
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| embedding modelleri metni sayısal vektöre çevirir; aday havuzunda arama ve nitelik çıkarımı gizlilik riskini ölçebilir | İlk üç görevde `veri/gommeler.json` içindeki elle yazılmış sentetik vektörler; son görevde yerel Ollama `all-minilm:22m` ile sekiz kurgusal kayıt ve parafrazının gerçek embedding vektörleri | Aday havuzundan eşleştirme, bilinmeyen serbest metni vektörden üreten vec2text deneyi değildir; küçük örneklem genel sızıntı oranını kanıtlamaz |

> [!NOT]
> `veri/gommeler.json` canlı model çıktısı değildir. **Çalıştır** kodu bu dosyayı okuyup örnek sonuçları gösterir; dosya yolunu `print` ile görebilir, aynı çalıştırmada kopyayı düzenleyip yeniden okuyabilirsin. İlk üç görev geçici çalışma klasöründe açılır ve her çalıştırmada kaynak örnek yeniden kopyalanır; değişiklikler kalıcı değildir. Gizli testler bu dosyadan bağımsızdır. Son **Gerçek deney** gerçek modeli çağırır; gerçek çıktılar sentetik dosyayla karıştırılmaz.

RAG ve arama sistemleri metni **embedding temsiline** (embedding) çevirip bir vektör deposunda saklar. Yaygın bir yanılgı, "metni değil, sayıları saklıyoruz, o yüzden gizli veri güvende" demektir. Bu yanlıştır: embedding, kaynak metnin anlamını yoğun biçimde kodlar ve bu bilgi geri çıkarılabilir. **Embedding inversion** saldırısı, yalnız bir vektöre bakarak kaynak hakkında bilgi — bazen metnin kendisini — kurtarır. İki pratik biçimi vardır. **Geri-çıkarma (recovery)**: saldırganın elinde bir hedef embedding ve bir aday metin havuzu varsa, adayları gömüp en yakın komşuyu bulur; hedefin *yeniden yazılmış* (parafraz) bir hâli bile çoğu zaman özgün kaynağa eşlenir, çünkü embedding kelimelere değil anlama duyarlıdır. **Nitelik çıkarımı (attribute inference)**: embedding vektörlerinin, taşıdıkları hassas bir nitelik (hastalık, konum, kimlik) etrafında kümelenmesi, yalnız vektöre bakan basit bir sınıflandırıcının o niteliği tahmin etmesine yeter (Song ve Raghunathan, 2020).

Daha ileri saldırılar (vec2text; Morris ve ark., 2023) bir embedding temsilinden özgün cümleyi büyük ölçüde yeniden üretebilir. Sonuç nettir: bir embedding, kaynağı kadar hassastır. Vektör deposunu "de-identifiye edilmiş veri" sanıp zayıf koruyan bir sistem, metni açıkta tutmakla neredeyse aynı riski taşır. Savunma, embedding temsilini kaynak metinle aynı gizlilik sınıfında tutmak, erişimi ve izolasyonu metne uyguladığın kadar vektöre de uygulamaktır (ai-savunma-19).
:::

::: anlat Risk ölçülür: recovery@k ve nitelik çıkarım doğruluğu
Bu sızıntı bir temenni değil, **ölçülebilir** bir büyüklüktür. Geri-çıkarmayı `recovery@k` ile ölçeriz: her hedef (parafraz) için en yakın `k` aday arasında özgün kaynak var mı; oran 1'e ne kadar yakınsa depo o kadar sızdırıyordur. Nitelik çıkarımını, gömmelerden niteliği tahmin eden bir sınıflandırıcının doğruluğuyla ölçeriz; en basiti **en yakın merkez** (nearest-centroid) sınıflandırmasıdır: her niteliğin gömme ortalamasını (merkezini) al, bir örneği en yakın merkeze ata. Dürüst bir ölçüm için örneğin kendisini merkez hesabından çıkarırız (bırak-biri-dışarıda); doğruluk 0.5'ten (rastgele) ne kadar yüksekse nitelik o kadar sızıyordur.

Bu derste önce en yakın komşu aramasını (geri-çıkarma mekanizması), recovery ölçüsünü ve en yakın merkez sınıflandırmasını saf Python'la kurarsın. Son görevde bunları birleştiren inversion raporunu yazarsın; gerçek bir embedding modeli (all-MiniLM-L6-v2) kurgusal kayıtları ve parafrazlarını vektöre çevirir, parafrazdan özgün kaydın ne kadar geri çıktığını (recovery@k) ve embedding temsilinden hassas niteliğin ne kadar tahmin edilebildiğini kendi gözünle ölçersin.
:::

::: tahmin En yakın komşu, recovery ve merkez çıkarımı çıktısını tahmin et
Üç çıktı satırını yaz:

```python
import math
def birim(v):
    b = math.sqrt(sum(x * x for x in v))
    return [x / b for x in v]
adaylar, hedef = [[1, 0], [0, 1], [0.9, 0.1]], [0.8, 0.2]
q = birim(hedef)
skor = [round(sum(a * b for a, b in zip(birim(v), q)), 4) for v in adaylar]
print(sorted(range(3), key=lambda i: (-skor[i], i))[:2])
print(round(sum(x in y[:2] for x, y in zip(["a", "b"], [["a", "z"], ["w", "b"]])) / 2, 4))
print(round(sum((a - b) ** 2 for a, b in zip([1, 0], [0.9, 0.1])) ** 0.5, 4))
```

???

```cikti
[2, 0]
1.0
0.1414
```

İlk satır en yakın komşu: `[0.8, 0.2]` hedefine en yakın adaylar sırayla `[0.9, 0.1]` (indeks 2) ve `[1, 0]` (indeks 0); gömme, hedefin hangi kayda ait olduğunu açığa vurur. İkinci satır recovery@2: iki hedefin ikisi de ilk iki tahminde özgün kaynağını buluyor → 1.0. Üçüncü satır bir örnekle bir merkez arasındaki Öklid uzaklığıdır; en yakın merkez sınıflandırması niteliği bu uzaklıkla tahmin eder.
:::

::: gorev 1 · En yakın komşu araması (geri-çıkarma mekanizması)
`yakin_komsu(hedef, adaylar, k)` işlevini yaz. `hedef` 2–4096 uzunlukta, öğeleri bool olmayan sonlu int/float olan, sıfır olmayan listedir. `adaylar` 1–1000 öğeli listedir; her öğe `hedef` ile aynı uzunlukta, aynı kurallara uyan vektördür. `k` bool olmayan tamsayı, `1 ≤ k ≤ len(adaylar)`. Geçersiz veride `ValueError` yükselt.

`hedef`'i ve her adayı L2 normuna bölerek kosinüs benzerliğini hesapla; skora göre azalan, eşitlikte küçük indeks önce sırala ve ilk `k` adayın indekslerini liste döndür.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-31")
```

```starter
import math
from ai_guvence_veri import json_yukle

def yakin_komsu(hedef, adaylar, k):
    # KUSURLU BAŞLANGIÇ KODU: normalize etmeden iç çarpımı sıralıyor.
    skor = [sum(a*b for a,b in zip(hedef,v)) for v in adaylar]
    return sorted(range(len(adaylar)), key=lambda i: -skor[i])[:k]

v = json_yukle("veri/gommeler.json")
print("Sentetik örnek dosyası: veri/gommeler.json")
print("En yakın adaylar:", yakin_komsu(v["hedef"],v["adaylar"],v["k"]))
```

```test
def sozlesme(fn):
    try:
        A = [[1, 0], [0, 1], [0.9, 0.1], [-1, 0]]
        if fn([1, 0], A, 2) != [0, 2] or fn([1, 0], A, 4) != [0, 2, 1, 3]:
            return False
        if fn([0, 1], A, 1) != [1] or fn([1, 1], [[1, 1], [2, 2], [1, 0]], 2) != [0, 1]:
            return False
        for kotu in [([1, 0], None, 1), ([1, 0], [], 1), ([1, 0], "x", 1), ([1, 0], [[1, 0]] * 1001, 1),
                     (123, A, 1), ([1], [[1]], 1), ([1, 0], [tuple([1, 0])], 1), ([1], A, 1), ([0, 0], A, 1), ([1, 0], [[1, 0, 0]], 1), ([1, 0], [[1, True]], 1), ([1, 0], [[1, "0"]], 1),
                     ([1, float("nan")], A, 1), ([1, 0], [[0, 0]], 1), ([1, 0], A, 0), ([1, 0], A, 5), ([1, 0], A, True), ([1, 0], A, 1.0)]:
            try:
                fn(*kotu)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(yakin_komsu), "kosinüs en yakın komşu sıralaması doğru; geçersiz girdi reddedilmeli")
import math
def _nn(h, A, k, normalize=True):
    def b(v):
        n = math.sqrt(sum(x * x for x in v))
        return [x / n for x in v] if normalize else list(v)
    q = b(h)
    s = [sum(a * c for a, c in zip(b(v), q)) for v in A]
    return sorted(range(len(A)), key=lambda i: (-s[i], i))[:k]
for ad, mut in [("normalize etmeyen (uzunluk yanlı)", lambda h, A, k: _nn(h, A, k, normalize=False)),
                ("sırayı ters çeviren", lambda h, A, k: _nn(h, A, k)[::-1])]:
    ok(not sozlesme(mut), "yanlış çözüm/mutant yakalanmalı: " + ad)
# Boyut/adet sınırları ve normalize etmenin sıralamaya etkisi.
ok(yakin_komsu([1,0], [[1,1],[0.8,0]], 1)==[1], "uzunluk yanlılığı olmamalı")
ok(yakin_komsu([1]*4096, [[1]*4096], 1)==[0], "üst boyut sınırı dahil")
ok(yakin_komsu([1,0], [[1,0]]*1000,1000)==list(range(1000)), "üst aday sınırı ve eşitlik sırası")
for args in [([1]*4097,[[1]*4097],1),([1,0],[[1,0]]*1001,1),([],[[1,0]],1),([1,0],[[True,0]],1),([1,0],[[float('inf'),0]],1),([True,0],[[1,0]],1),([1,0],[[1,0]],-1)]:
    try:
        yakin_komsu(*args)
        ok(False,"sınır dışı veri reddedilmeli")
    except ValueError:
        ok(True,"sınır dışı veri reddedildi")
```

```solution
from ai_guvence_veri import json_yukle
import math

def yakin_komsu(hedef, adaylar, k):
    if not isinstance(hedef, list) or not 2 <= len(hedef) <= 4096:
        raise ValueError("hedef iki-dört bin doksan altı uzunlukta liste olmalı")
    def birim(v):
        if not isinstance(v, list) or len(v) != len(hedef) \
                or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in v):
            raise ValueError("vektör geçersiz")
        boy = math.sqrt(sum(x * x for x in v))
        if not boy:
            raise ValueError("sıfır vektör")
        return [x / boy for x in v]
    if not isinstance(adaylar, list) or not 1 <= len(adaylar) <= 1000:
        raise ValueError("adaylar bir-bin öğeli liste olmalı")
    q = birim(hedef)
    birimler = [birim(v) for v in adaylar]
    if isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= len(adaylar):
        raise ValueError("k bir ile aday sayısı arası tamsayı olmalı")
    skor = [sum(a * b for a, b in zip(v, q)) for v in birimler]
    return sorted(range(len(adaylar)), key=lambda i: (-skor[i], i))[:k]

if __name__ == "__main__":
    v = json_yukle("veri/gommeler.json")
    print("Sentetik örnek dosyası: veri/gommeler.json")
    print("En yakın adaylar:", yakin_komsu(v["hedef"],v["adaylar"],v["k"]))
```

```hint
Her vektörü birim vektöre çevirip (geçersiz/sıfır vektörü burada yakala) iç çarpımı kosinüs olarak al. `(-skor, indeks)` anahtarıyla sıralamak hem azalan skoru hem eşitlikte küçük indeksi tek anahtarla verir.
```
:::

::: gorev 2 · Geri-çıkarma başarısını ölç (recovery@k)
`geri_cikar_metrik(dogrular, tahminler, k)` işlevini yaz. `dogrular` 1–1000 öğeli, boş olmayan stringlerden oluşan listedir (her hedefin özgün kaynağı). `tahminler` aynı uzunlukta listedir; her öğe, o hedef için sıralı tahmin kimliklerinin (boş olmayan string) listesidir. `k` bool olmayan ≥1 tamsayıdır. Geçersiz veride `ValueError` yükselt.

`recovery@1` = `tahminler[i]` boş değilken ilk tahminin doğru olduğu hedeflerin oranı. `recovery@k` = özgün kaynağın ilk `k` tahmin içinde olduğu hedeflerin oranı. İkisini de `round(…, 4)` ile yuvarla. `{"recovery1": …, "recoveryk": …}` döndür.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-31")
```

```starter
from ai_guvence_veri import json_yukle

def geri_cikar_metrik(dogrular, tahminler, k):
    # KUSURLU BAŞLANGIÇ KODU: ilk k yerine bütün tahminleri sayıyor.
    oran = sum(d in t for d,t in zip(dogrular,tahminler))/len(dogrular)
    return {"recovery1": round(oran,4), "recoveryk": round(oran,4)}

v = json_yukle("veri/gommeler.json")
print("Sentetik örnek dosyası: veri/gommeler.json")
print("Recovery:", geri_cikar_metrik(v["dogrular"],v["tahminler"],v["k"]))
```

```test
def sozlesme(fn):
    try:
        if fn(["a", "b", "c"], [["a", "x"], ["y", "b"], ["z", "w"]], 2) != {"recovery1": round(1 / 3, 4), "recoveryk": round(2 / 3, 4)}:
            return False
        if fn(["a"], [["a"]], 1) != {"recovery1": 1.0, "recoveryk": 1.0}:
            return False
        if fn(["a", "b"], [[], ["b", "a"]], 2) != {"recovery1": 0.5, "recoveryk": 0.5}:
            return False
        if fn(["a"], [["x", "y", "a"]], 2) != {"recovery1": 0.0, "recoveryk": 0.0}:
            return False
        for kotu in [(None, [["a"]], 1), (["a"], None, 1), ([], [], 1), (["a"], [["a"], ["b"]], 1), (["a"], "x", 1),
                     (["a"], [None], 1), (["a"], [["a", 2]], 1), (["a"], [["a"]], 0), (["a"], [["a"]], True), (["a"], [["a"]], 1.0), ([""], [["a"]], 1)]:
            try:
                fn(*kotu)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(geri_cikar_metrik), "recovery@1 ve recovery@k doğru; geçersiz girdi reddedilmeli")
def m_bir(d, t, k):
    r = geri_cikar_metrik(d, t, k)
    r["recovery1"] = round(sum(x in y for x, y in zip(d, t)) / len(d), 4); return r  # ilk yerine 'in'
def m_k(d, t, k):
    r = geri_cikar_metrik(d, t, k)
    r["recoveryk"] = round(sum(bool(y) and y[0] == x for x, y in zip(d, t)) / len(d), 4); return r  # yalnız ilk
for ad, mut in [("recovery@1'i 'herhangi yerde' sayan", m_bir), ("recovery@k'yı yalnız ilk tahmine bakan", m_k)]:
    ok(not sozlesme(mut), "yanlış çözüm/mutant yakalanmalı: " + ad)
ok(geri_cikar_metrik(["a"]*1000, [["a"]]*1000,1)=={"recovery1":1.0,"recoveryk":1.0}, "üst örnek sınırı dahil")
ok(geri_cikar_metrik(["a","b","c"], [["a"],[],[]],1)=={"recovery1":0.3333,"recoveryk":0.3333}, "dört basamak yuvarlama")
for args in [(["a"]*1001,[["a"]]*1001,1),(["a"],[[""]],1),([3],[["a"]],1),(["a"],[("a",)],1)]:
    try:
        geri_cikar_metrik(*args)
        ok(False,"geçersiz recovery girdisi reddedilmeli")
    except ValueError:
        ok(True,"geçersiz recovery girdisi reddedildi")
```

```solution
from ai_guvence_veri import json_yukle
def geri_cikar_metrik(dogrular, tahminler, k):
    if not isinstance(dogrular, list) or not 1 <= len(dogrular) <= 1000 or any(not isinstance(x, str) or not x for x in dogrular):
        raise ValueError("dogrular boş olmayan string listesi olmalı")
    if not isinstance(tahminler, list) or len(tahminler) != len(dogrular):
        raise ValueError("tahminler dogrular ile aynı uzunlukta olmalı")
    for t in tahminler:
        if not isinstance(t, list) or any(not isinstance(x, str) or not x for x in t):
            raise ValueError("her tahmin boş olmayan string listesi olmalı")
    if isinstance(k, bool) or not isinstance(k, int) or k < 1:
        raise ValueError("k ≥bir tamsayı olmalı")
    n = len(dogrular)
    bir = sum(1 for d, t in zip(dogrular, tahminler) if t and t[0] == d)
    kk = sum(1 for d, t in zip(dogrular, tahminler) if d in t[:k])
    return {"recovery1": round(bir / n, 4), "recoveryk": round(kk / n, 4)}

if __name__ == "__main__":
    v = json_yukle("veri/gommeler.json")
    print("Sentetik örnek dosyası: veri/gommeler.json")
    print("Recovery:", geri_cikar_metrik(v["dogrular"],v["tahminler"],v["k"]))
```

```hint
recovery@1 yalnız ilk tahmine (`t[0] == d`, liste boş değilse) bakar; recovery@k ise doğrunun ilk `k` tahmin içinde olmasına (`d in t[:k]`). İkisi farklı kavramlardır: biri "en iyi tahmin doğru mu", öbürü "doğru listede mi".
```
:::

::: gorev 3 · Gömmeden nitelik çıkarımı (en yakın merkez)
`merkez_sinifla(vekler, etiketler)` işlevini yaz. `vekler` 2–1000 öğeli listedir; her öğe aynı uzunlukta (2–4096), öğeleri bool olmayan sonlu int/float olan listedir. `etiketler` aynı uzunlukta listedir; her öğe string ya da bool olmayan tamsayıdır ve en az iki farklı etiket bulunur. Geçersiz veride `ValueError` yükselt.

Bırak-biri-dışarıda sınıflandırma yap: her örnek için, o örneği dışarıda bırakarak her etiketin merkezini (o etikete ait vektörlerin ortalaması) hesapla; örneği, Öklid karesine göre en yakın merkeze ata (eşitlikte sayısal etiketler küçükten büyüğe, ardından string etiketler alfabetik sırayla). Örneğin tahmini gerçek etiketiyle aynıysa doğru say. Doğru oranını `round(…, 4)` döndür. (Bir etiketin tek örneği örnekken o etiket merkezsiz kalır ve o örnek yanlış sınıflanır.)

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-31")
```

```starter
from ai_guvence_veri import json_yukle

def merkez_sinifla(vekler, etiketler):
    # KUSURLU BAŞLANGIÇ KODU: örneği kendi sınıf merkezinden çıkarmıyor.
    merkez = {e:[sum(c)/etiketler.count(e) for c in zip(*(v for v,t in zip(vekler,etiketler) if t==e))] for e in set(etiketler)}
    tahmin = [min(merkez,key=lambda e:sum((a-b)**2 for a,b in zip(v,merkez[e]))) for v in vekler]
    return round(sum(a==b for a,b in zip(tahmin,etiketler))/len(etiketler),4)

v = json_yukle("veri/gommeler.json")
print("Sentetik örnek dosyası: veri/gommeler.json")
print("Nitelik doğruluğu:", merkez_sinifla(v["vekler"],v["etiketler"]))
```

```test
def sozlesme(fn):
    try:
        if fn([[1, 0], [0.9, 0.1], [0, 1], [0.1, 0.9]], [0, 0, 1, 1]) != 1.0:
            return False
        if fn([[1, 0], [0, 1]], [0, 1]) != 0.0:
            return False
        if fn([[1, 0], [0.9, 0.1], [0, 1], [0.1, 0.9], [0.2, 0.8]], ["a", "a", "b", "b", "a"]) != 0.8:
            return False
        if fn([[2.0, 0.0], [4.0, 0.0], [5.0, 0.0], [6.0, 0.0]], [0, 0, 1, 1]) != 0.75:
            return False
        for kotu in [(None, [0, 1]), ([123, [1, 0]], [0, 1]), ([[1, 0], tuple([0, 1])], [0, 1]), ([[1, 0], [0, 1]], [0, 1, 0]), ([[1, 0]], [0]), ([[1, 0], [0, 1]], [0, 0]), ([[1, 0], [0, 1]], [0]),
                     ([[1, 0], [0, 1]], [0, True]), ([[1, 0], [0, 1]], [0, 1.0]), ([[1, 0], [0, 1, 2]], [0, 1]),
                     ([[1, 0], [0, "x"]], [0, 1]), ([[1, 0], [0, 1]], "ab")]:
            try:
                fn(*kotu)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(merkez_sinifla), "bırak-biri-dışarıda en yakın merkez doğruluğu doğru; geçersiz girdi reddedilmeli")
def m_selfdahil(vekler, etiketler):
    n = len(vekler); dogru = 0
    for i in range(n):
        mz = {}
        for e in set(etiketler):
            g = [vekler[j] for j in range(n) if etiketler[j] == e]  # kendini dışarıda bırakmıyor
            mz[e] = [sum(c) / len(g) for c in zip(*g)]
        t = min(mz, key=lambda e: sum((a - b) ** 2 for a, b in zip(vekler[i], mz[e])))
        dogru += (t == etiketler[i])
    return round(dogru / n, 4)
ok(not sozlesme(m_selfdahil), "yanlış çözüm/mutant yakalanmalı: kendini merkeze katan (bırak-biri-dışarıda değil)")
# Eşit merkezler: etiket sırası, bırak-biri-dışarıda ve yuvarlama.
ok(merkez_sinifla([[0,0]]*1000,[0]*500+[1]*500)==0.5, "üst örnek sayısı dahil")
ok(merkez_sinifla([[0,0]]*3,[0,0,1])==0.6667, "eşitlikte küçük etiket ve dört basamak")
ok(merkez_sinifla([[0,0]]*4,["b","b","a","a"])==0.5, "string eşitlik sırası")
ok(merkez_sinifla([[0,0]]*4,[1,1,"a","a"])==0.5, "karma etiketlerde sayılar önce")
ok(merkez_sinifla([[0]*4096,[1]*4096],[0,1])==0.0, "üst vektör boyutu dahil")
for args in [([[0]*4097,[1]*4097],[0,1]),([[0,0]]*1001,[0]*1000+[1]),([[float('nan'),0],[1,0]],[0,1]),([[True,0],[1,0]],[0,1]),([[1],[2]],[0,1]),([[1,0],[2,0]],[{},1])]:
    try:
        merkez_sinifla(*args)
        ok(False,"geçersiz merkez girdisi reddedilmeli")
    except ValueError:
        ok(True,"geçersiz merkez girdisi reddedildi")
```

```solution
from ai_guvence_veri import json_yukle
import math

def merkez_sinifla(vekler, etiketler):
    if not isinstance(vekler, list) or not 2 <= len(vekler) <= 1000:
        raise ValueError("vekler iki-bin öğeli liste olmalı")
    boy = len(vekler[0]) if isinstance(vekler[0], list) else 0
    for v in vekler:
        if not isinstance(v, list) or not 2 <= len(v) <= 4096 or len(v) != boy \
                or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in v):
            raise ValueError("vektör geçersiz")
    if not isinstance(etiketler, list) or len(etiketler) != len(vekler) \
            or any(isinstance(e, bool) or not isinstance(e, (str, int)) for e in etiketler) or len(set(etiketler)) < 2:
        raise ValueError("etiketler aynı uzunlukta, en az iki farklı string/int etiket olmalı")
    n = len(vekler)
    dogru = 0
    for i in range(n):
        merkez = {}
        for e in set(etiketler):
            grup = [vekler[j] for j in range(n) if j != i and etiketler[j] == e]
            if grup:
                merkez[e] = [sum(c) / len(grup) for c in zip(*grup)]
        if not merkez:
            continue
        tahmin = min(sorted(merkez, key=lambda e: (isinstance(e, str), e)), key=lambda e: sum((a - b) ** 2 for a, b in zip(vekler[i], merkez[e])))
        dogru += (tahmin == etiketler[i])
    return round(dogru / n, 4)

if __name__ == "__main__":
    v = json_yukle("veri/gommeler.json")
    print("Sentetik örnek dosyası: veri/gommeler.json")
    print("Nitelik doğruluğu:", merkez_sinifla(v["vekler"],v["etiketler"]))
```

```hint
Her örnek için merkezleri o örneği **dışarıda bırakarak** yeniden hesapla — yoksa örnek kendi merkezini çeker ve doğruluk yapay olarak şişer. Merkeze uzaklıkta kareköke gerek yok (Öklid karesi aynı sıralamayı verir); eşitlikte etiketleri `sorted` ile tutarlı sırala.
```
:::

::: anlat Gerçek gömmelerde embedding inversion
Bu deneyde gerçek bir embedding modeli (`all-minilm:22m`, 384 boyut) sekiz kurgusal hasta kaydını ve her birinin bir parafrazını vektöre çevirir. Saldırgan senaryosu: elinde depolanan özgün kayıtların embedding vektörleri ve bir hedef parafraz var. Senin `inversion_raporu` işlevin, parafraz gömmesine en yakın özgün kaydı bulur (geri-çıkarma). Deney bunu sekiz parafraz için çalıştırıp recovery@1 ve recovery@k'yı ölçer: yeniden yazılmış metin bile çoğu zaman özgün kayda eşlenir. Ayrıca embedding vektörlerinden hassas niteliğin (kan şekeri durumu) en yakın merkezle ne kadar tahmin edilebildiğini ölçer. Bütün kayıtlar sentetiktir; model bu deney tarafından yüklendiyse sonunda boşaltılır.

Kaynaklar: [Song ve Raghunathan 2020 — Information Leakage in Embedding Models (CCS, arXiv:2004.00053)](https://arxiv.org/abs/2004.00053), [Morris vd. 2023 — Text Embeddings Reveal (Almost) As Much As Text / Vec2Text (arXiv:2310.06816)](https://arxiv.org/abs/2310.06816).
:::

::: gorev Gerçek deney · Parafrazdan kaynağı geri çıkar
`inversion_raporu(hedef, aday_vekler, aday_idler, dogru_id, k)` işlevini yaz.

- Doğrulama (aksi hâlde `ValueError`): `hedef` 2–4096 uzunlukta, bool olmayan sonlu sayı, sıfır olmayan vektör. `aday_vekler` 1–1000 öğeli, her biri `hedef` ile aynı uzunlukta, aynı kurallara uyan liste. `aday_idler` aynı uzunlukta, yinelenmeyen, boş olmayan string listesi. `dogru_id` `aday_idler` içinde bir string. `k` bool olmayan int, `1 ≤ k ≤ len(aday_vekler)`.
- `hedef`'i ve her adayı L2 normuna böl, kosinüse göre azalan (eşitlikte küçük indeks) sırala, ilk `k` adayın kimliklerini al → `sirali`. `{"sirali": sirali, "recovery1": sirali[0] == dogru_id, "recoveryk": dogru_id in sirali}` döndür.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import math
import ai_lab

def inversion_raporu(hedef, aday_vekler, aday_idler, dogru_id, k):
    return {"sirali": [], "recovery1": False, "recoveryk": False}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_31 as deney
    deney.goster(inversion_raporu)
```

```test
import copy
import ai_lab
sonuclar = []
def kontrol(kosul, mesaj):
    sonuclar.append(bool(kosul))
    return ok(kosul, mesaj)
import ast
YASAK = ("referans", "referans_inversion", "yakin_komsu_ref", "merkez_sinifla_ref", "kanit_yaz", "getattr")
sorun = ai_lab.kod_denetimi(src, YASAK)
for node in ast.walk(ast.parse(src)):
    if isinstance(node, ast.ImportFrom) and any(a.name in YASAK or a.name == "*" for a in node.names):
        sorun.append("referans import edilemez")
kontrol(not sorun, "Kendi inversion işlevini yaz; laboratuvar yamalanmamalı: " + ", ".join(sorun))
if sorun:
    stop()
fn = need("inversion_raporu")
from sandbox import ai_gercek_ai_guvence_31 as D
idler = ["p0", "p1", "p2", "p3"]
vek = [[1.0, 0.0], [0.9, 0.1], [0.0, 1.0], [-1.0, 0.0]]
vakalar = [([1.0, 0.0], vek, idler, "p0", 2), ([0.0, 1.0], vek, idler, "p2", 1),
           ([0.85, 0.15], vek, idler, "p1", 3), ([1.0, 1.0], vek, idler, "p3", 2)]
def ayni(a, b):
    return isinstance(a, dict) and set(a) == set(b) and a == b
def sozlesme(f):
    try:
        if f([1.0] * 4096, [[1.0] * 4096], ["p0"], "p0", 1) != {"sirali": ["p0"], "recovery1": True, "recoveryk": True}: return False
        if f([1.0, 0.0], [[1.0, 0.0]] * 1000, [f"p{i}" for i in range(1000)], "p0", 1) != {"sirali": ["p0"], "recovery1": True, "recoveryk": True}: return False
        if f([1.0, 0.0], [[1.0, 0.0], [1.0, 0.0]], ["b", "a"], "a", 1) != {"sirali": ["b"], "recovery1": False, "recoveryk": False}: return False
        for h, v, idl, d, k in vakalar:
            hh, vv, ii = list(h), copy.deepcopy(v), list(idl)
            if f(hh, vv, ii, d, k) != D.referans_inversion(h, v, idl, d, k) or hh != h or vv != v or ii != idl:
                return False
        h, v, idl, d, k = vakalar[0]
        for arg in [([1.0], v, idl, d, 1), ([0.0, 0.0], v, idl, d, 1), (h, [], [], d, 1), (h, v[:-1], idl, d, 2),
                    (h, v, idl + ["x"], d, 2), (h, v, ["p0", "p0", "p2", "p3"], d, 2), (h, v, idl, "yok", 2),
                    (h, v, idl, d, 0), (h, v, idl, d, 5), (h, v, idl, d, True), (h, [[1.0], [0.9, 0.1], [0.0, 1.0], [-1.0, 0.0]], idl, d, 2),
                    ([1.0, float("nan")], v, idl, d, 2), (h, [[1.0, 0.0], [0.9, 0.1], [0.0, 1.0], [0.0, 0.0]], idl, d, 2),
                    ([1.0] * 4097, [[1.0] * 4097], ["p0"], "p0", 1), (h, [[1.0, 0.0]] * 1001, [f"p{i}" for i in range(1001)], "p0", 1), (h, v, ["", "p1", "p2", "p3"], "p1", 1), (h, v, idl, 123, 1),
                    (123, v, idl, d, 2), ([1.0], [[1.0]], ["p0"], "p0", 1), (h, [tuple(v[0])] + v[1:], idl, d, 2), (h, [[True, 1.0]] + v[1:], idl, d, 2), (h, [["1.0", 1.0]] + v[1:], idl, d, 2),
                    (h, tuple(v), idl, d, 2), (h, v, tuple(idl), d, 2), (h, v, [1, "p1", "p2", "p3"], "p1", 1), (h, [[1.0, 0.0]], [1], 1, 1), (h, v, idl, d, 1.0)]:
            try:
                f(*arg)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
kontrol(sozlesme(fn), "kosinüs geri-çıkarma ve recovery bayrakları doğru; geçersiz girdi reddedilmeli")
for ad, kw in [("normalize etmeyen (uzunluk yanlı)", {"normalize": False})]:
    kontrol(not sozlesme(lambda h, v, i, d, k, kw=kw: D.referans_inversion(h, v, i, d, k, **kw)), "hatalı çözüm reddedilmeli: " + ad)
sabit = D.referans_inversion(*vakalar[0])
kontrol(not sozlesme(lambda *a: sabit), "hatalı çözüm reddedilmeli: ezber sonuç")
r, oz = None, None
if all(sonuclar):
    try:
        r = D.deney(fn)
    except ai_lab.GercekLabYok as e:
        kontrol(False, f"GERÇEK MODEL YOK, deney yapılmadı: {e}")
        stop()
    pv = r["vektorler"]["parafraz"]
    kontrol(len(pv[0]) == 384 and r["ortam"]["gomme"]["model"] == D.GOMME_MODELI, f"gerçek gömmeler: {r['kayit_sayisi']} kayıt × {len(pv[0])} boyut")
    esit = all(ayni({x: k[x] for x in ("sirali", "recovery1", "recoveryk")},
                    D.referans_inversion(pv[i], r["vektorler"]["orijinal"], r["idler"], r["idler"][i], D.K)) for i, k in enumerate(r["kayitlar"]))
    kontrol(esit, "gerçek gömmelerde geri-çıkarma sonucu bağımsız hesapla aynı")
    oz = D.ozet(r)
    kontrol(oz["recovery1"] > 0, f"parafrazdan özgün kayıt geri çıktı: recovery@1 {oz['recovery1']}, recovery@{r['k']} {oz['recoveryk']}")
yol = ai_lab.kanit_yaz("guvence-inversion", {"kaynak": "gercek", "kabul": all(sonuclar), "ders": "ai-guvence-31",
                                             "ortam": (r or {}).get("ortam"), "ozet": oz})
if oz:
    ok(True, f"BULGU ({D.GOMME_MODELI}, {oz['boyut']} boyut): {oz['kayit']} parafrazdan geri-çıkarma recovery@1 {oz['recovery1']}, "
             f"recovery@{r['k']} {oz['recoveryk']}; gömmeden kan şekeri niteliği {oz['nitelik_dogrulugu']} doğrulukla tahmin edildi (0.5=şans). "
             f"Gömme kaynak kadar hassastır.")
```

```solution
import math
import ai_lab

def inversion_raporu(hedef, aday_vekler, aday_idler, dogru_id, k):
    if not isinstance(hedef, list) or not 2 <= len(hedef) <= 4096:
        raise ValueError("hedef 2-4096 uzunlukta liste olmalı")
    def birim(v):
        if not isinstance(v, list) or len(v) != len(hedef) \
                or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in v):
            raise ValueError("vektör geçersiz")
        boy = math.sqrt(sum(x * x for x in v))
        if not boy:
            raise ValueError("sıfır vektör")
        return [x / boy for x in v]
    if not isinstance(aday_vekler, list) or not 1 <= len(aday_vekler) <= 1000:
        raise ValueError("aday_vekler 1-1000 öğeli liste olmalı")
    q = birim(hedef)
    birimler = [birim(v) for v in aday_vekler]
    if not isinstance(aday_idler, list) or len(aday_idler) != len(aday_vekler) \
            or any(not isinstance(x, str) or not x for x in aday_idler) or len(set(aday_idler)) != len(aday_idler):
        raise ValueError("aday_idler yinelenmeyen, boş olmayan string listesi olmalı")
    if not isinstance(dogru_id, str) or dogru_id not in aday_idler:
        raise ValueError("dogru_id aday_idler içinde olmalı")
    if isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= len(aday_vekler):
        raise ValueError("k 1 ile aday sayısı arası tamsayı olmalı")
    skor = [sum(a * b for a, b in zip(v, q)) for v in birimler]
    sira = sorted(range(len(aday_vekler)), key=lambda i: (-skor[i], i))[:k]
    sirali = [aday_idler[i] for i in sira]
    return {"sirali": sirali, "recovery1": bool(sirali) and sirali[0] == dogru_id, "recoveryk": dogru_id in sirali}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_31 as deney
    deney.goster(inversion_raporu)
```

```hint
Geri-çıkarma, görev 1'deki en yakın komşu aramasıdır: `hedef`'e (parafraz) en yakın `k` adayı (özgün kayıtları) bul. `recovery1` ilk adayın doğru kimlik olması, `recoveryk` doğru kimliğin ilk `k` içinde olmasıdır. Birim vektörleri bir kez hesapla, geçersiz/sıfır vektörü orada yakala.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **'Metni sildik, yalnız vektör saklıyoruz' yanılgısı (35 sn).** "Yoğun metin gömmeleri (`embeddings`) tek yönlü kriptografik özet değildir; anlamsal yakınlığı korumak üzere eğitildikleri için parafraz komşuluğu (`recovery@k`), merkez sınıflandırması (hassas nitelik sızıntısı) veya tersine üretim modelleriyle kaynak metni ele verir."
2. **Birim vektör normalizasyonu ve kosinüs sıralaması (30 sn).** "Farklı uzunluktaki vektörlerde büyüklük yanlılığını önlemek için önce $L_2$ birim normalizasyon yapılır, sıfır veya `NaN` vektörler reddedilir ve en yüksek iç çarpımlı ilk-$k$ aday seçilir."
3. **Veri koruma sonucu (30 sn).** "Vektör veritabanındaki gömmeler kaynak metinle aynı erişim kontrolü, şifreleme ve saklama süresi politikasına tabi tutulmalıdır."
4. **Soru (25 sn).** "Vektör veritabanı sızdığında saldırganın elinde özgün aday havuzu bile yoksa `Vec2Text` tarzı yinelemeli tersine çevirme saldırısı gömmeden metni nasıl geri kurar?"
:::
