---
id: ai-guvence-14
title: Backdoor Tetikleyici Deneyi
summary: Tetikleyici yerleşimini küçük matrislerde uygula; temiz doğruluk ve hedef sınıf başarısını yerleşim biçimine göre karşılaştır.
esleme: ai-guvence-12, ai-guvence-13, ai-guvence-24
timeout: 45
---

::: anlat Gerçek biçimi bil, sentetik temsili ayırt et: Yerleşim deneyi kontrollü başlar
Bir tetikleyici deneyinde tetikleyicinin boyutu ve konumu değiştirilirken diğer koşulların sabit tutulması gerekir. Matris üzerinde yerleşim, tetikleyici satır ve sütunlarının belirlenen başlangıç konumundan itibaren görüntüdeki karşılık gelen hücreleri değiştirmesidir. Tetikleyici görüntü sınırlarını aşamaz.

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| BadNets türü araştırmalarda eğitim görüntülerinin küçük bir kısmına tetikleyici basılıp etiket hedef sınıfa çevrilir; model yeniden eğitilir, temiz doğruluk ve tetikli örneklerde hedef başarı (ASR) birlikte raporlanır | İlk üç görevde `veri/goruntu_ornekleri.json`, `veri/deney_kayitlari.json` ve `veri/yerlesim_olcumleri.json` içindeki **sentetik** matris ve ölçümler; son görevde 6x6 sentetik görüntülerle sıfırdan eğitilen küçük bir PyTorch modeli (yerel CPU, ağa erişim yok) | Tek veri kümesi ve tek küçük modeldeki yerleşim sıralaması, gerçek görüntü modelleri veya başka tetikleyiciler için genel bir "en etkili yerleşim" kuralı vermez |

> [!NOT]
> İlk üç görevde çalışma dizinine kopyalanan `veri/` dosyaları **sentetik** eğitim örnekleridir. Her çalıştırmada yeniden kopyalanır; çalıştırmalar arasında **kalıcılık yoktur**. Son adımdaki **Gerçek deney** görevinde yazdığın üç işlev canlı eğitim sonuçlarıyla sınanır. Amaç saldırı üretmek değil, bir modelin bu tür zehirlemeye ne kadar açık olduğunu **ölçmeyi** ve ölçümü doğru okumayı öğrenmektir.
:::

::: anlat Hedef başarı ile temiz davranış birlikte okunur
Yalnız tetikleyici varken hedef sınıf başarısına bakmak yeterli değildir. Aynı yerleşimin temiz örneklerdeki doğruluğu da raporlanmalıdır. Yüksek hedef başarıya rağmen temiz doğruluğu alt sınırın altına düşen yerleşim seçilemez.

Birden fazla uygun yerleşim varsa en yüksek ortalama hedef başarı seçilir. Eşitlikte daha yüksek temiz doğruluk, onda da eşitlik varsa alfabetik olarak küçük yerleşim adı tercih edilir. Alt sınıra eşit temiz doğruluk uygundur.
:::

::: tahmin Yerleşim ve seçim sonucunu tahmin et
Üç çıktı satırını yaz:

```python
g = [[0, 0], [0, 0]]
g[0][1] = 1
print(g)
print(round(2 / 3, 6))
print(max([("a", 0.5), ("b", 0.7)], key=lambda x: x[1])[0])
```

???

```cikti
[[0, 1], [0, 0]]
0.666667
b
```

İlk satır tetikli matrisi, ikinci satır başarı oranını, üçüncü satır daha yüksek hedef başarılı yerleşimi gösterir.
:::

::: gorev 1 · Tetikleyiciyi matrise yerleştir
`tetik_yerlestir(goruntu, tetik, satir, sutun)` işlevini yaz. Görüntü ve tetik boş olmayan, dikdörtgen liste listeleridir; bütün hücreler bool olmayan sonlu sayı ve `[0,1]` aralığındadır. Satır ve sütun bool olmayan, sıfır veya pozitif tamsayılardır. Tetikleyici belirtilen konumda görüntüye tam sığmalıdır. Geçersiz veride `ValueError` yükselt.

Görüntünün bağımsız satır kopyalarını içeren yeni matris döndür ve tetikleyici hücrelerini konuma yaz. Girdileri değiştirme.

```starter
from ai_guvence_veri import json_yukle

def tetik_yerlestir(goruntu, tetik, satir, sutun):
    # KUSURLU BAŞLANGIÇ KODU: görüntüyü kopyalamadan yerinde değiştiriyor ve sığma sınırını denetlemiyor!
    for i in range(len(tetik)):
        for j in range(len(tetik[0])):
            if satir + i < len(goruntu) and sutun + j < len(goruntu[0]):
                goruntu[satir + i][sutun + j] = tetik[i][j]
    return goruntu

veri = json_yukle("veri/goruntu_ornekleri.json")
for y in veri["yerlesimler"]:
    try:
        print(y["ad"], tetik_yerlestir(veri["goruntuler"][0]["matris"], veri["tetik"], y["satir"], y["sutun"]))
    except ValueError as hata:
        print(y["ad"], "reddedildi:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-14")
```

```test
import copy
G = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
T = [[1, 1], [1, 1]]
BEKLENEN = [[0, 0, 0], [0, 1, 1], [0, 1, 1]]
def sozlesme(fn):
    try:
        gonce = copy.deepcopy(G)
        tonce = copy.deepcopy(T)
        sonuc = fn(G, T, 1, 1)
        if sonuc != BEKLENEN or G != gonce or T != tonce or any(sonuc[i] is G[i] for i in range(3)):
            return False
        if fn([[0, 0], [0, 0]], [[1]], 0, 1) != [[0, 1], [0, 0]]:
            return False
        if fn([[0, 1]], [[0.5]], 0, 1) != [[0, 0.5]]:
            return False
        for goruntu, tetik, satir, sutun in [
            (None, T, 0, 0), (G, None, 0, 0), ({}, T, 0, 0), (G, {}, 0, 0), (tuple(G), T, 0, 0), (G, tuple(T), 0, 0), ([], T, 0, 0), (G, [], 0, 0),
            ([1, 2], T, 0, 0), (G, [1, 2], 0, 0), ([[]], T, 0, 0), (G, [[]], 0, 0), ([[0, 0, 0], (0, 0, 0)], T, 0, 0), (G, [[1, 1], (1, 1)], 0, 0),
            ([[0], []], [[1]], 0, 0), (G, [[1], []], 0, 0),
            ([[True]], [[1]], 0, 0), ([["0"]], [[1]], 0, 0), ([[float("nan")]], [[1]], 0, 0),
            ([[-0.1]], [[1]], 0, 0), ([[1.1]], [[1]], 0, 0),
            (G, [[True]], 0, 0), (G, [["1"]], 0, 0), (G, [[float("inf")]], 0, 0),
            (G, [[-0.1]], 0, 0), (G, [[1.1]], 0, 0),
            (G, T, True, 0), (G, T, 0, True), (G, T, 1.0, 0), (G, T, 0, 1.0),
            (G, T, -1, 0), (G, T, 0, -1), (G, T, 2, 0), (G, T, 0, 2),
        ]:
            try:
                fn(goruntu, tetik, satir, sutun)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(tetik_yerlestir), "matris biçimi, sınırlar, yerleşim ve kopya korunmalı")
def m_tetik(goruntu, tetik, satir, sutun):
    return tetik_yerlestir(goruntu, [[0 for _ in tetik[0]] for _ in tetik], satir, sutun)
def m_konum(goruntu, tetik, satir, sutun):
    return tetik_yerlestir(goruntu, tetik, 0, 0)
def m_goruntu(goruntu, tetik, satir, sutun):
    return tetik_yerlestir([[0 for _ in goruntu[0]] for _ in goruntu], tetik, satir, sutun)
for ad, mutant in [("tetikleyiciyi silen", m_tetik), ("konumu değiştiren", m_konum), ("görüntüyü değiştiren", m_goruntu)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def tetik_yerlestir(goruntu, tetik, satir, sutun):
    import math
    if not isinstance(goruntu, list):
        raise ValueError("matrisler liste olmalı")
    if not isinstance(tetik, list):
        raise ValueError("matrisler liste olmalı")
    if not goruntu:
        raise ValueError("matrisler boş olamaz")
    if not tetik:
        raise ValueError("matrisler boş olamaz")
    for matris in (goruntu, tetik):
        if not isinstance(matris[0], list):
            raise ValueError("matris satırları geçersiz")
        if not matris[0]:
            raise ValueError("matris satırları geçersiz")
        genislik = len(matris[0])
        for satir_veri in matris:
            if not isinstance(satir_veri, list) or len(satir_veri) != genislik:
                raise ValueError("matris dikdörtgen olmalı")
            for deger in satir_veri:
                if isinstance(deger, bool):
                    raise ValueError("hücre sayı olmalı")
                if not isinstance(deger, (int, float)):
                    raise ValueError("hücre sayı olmalı")
                if not math.isfinite(deger):
                    raise ValueError("hücre sonlu olmalı")
                if deger < 0 or deger > 1:
                    raise ValueError("hücre aralık dışında")
    for konum in (satir, sutun):
        if isinstance(konum, bool):
            raise ValueError("konum tamsayı olmalı")
        if not isinstance(konum, int):
            raise ValueError("konum tamsayı olmalı")
        if konum < 0:
            raise ValueError("konum negatif olamaz")
    if satir + len(tetik) > len(goruntu) or sutun + len(tetik[0]) > len(goruntu[0]):
        raise ValueError("tetikleyici görüntüye sığmıyor")
    sonuc = [list(satir_veri) for satir_veri in goruntu]
    for i in range(len(tetik)):
        for j in range(len(tetik[0])):
            sonuc[satir + i][sutun + j] = tetik[i][j]
    return sonuc
```

```hint
Önce iki matrisi de dikdörtgenlik ve hücre kurallarıyla doğrula. Sonra sığma sınırını denetle ve yalnız satır kopyaları üzerinde yaz.
```
:::

::: gorev 2 · Yerleşim bazında temiz ve hedef başarıyı ölç
`tetik_deneyi_ozeti(kayitlar)` işlevini yaz. Kayıtlar boş olmayan listedir; her kayıt tam olarak `yerlesim`, `temiz_dogru`, `hedef_basarili` alanlarını taşır. Yerleşim 1–64 karakterlik, ASCII harf/rakamla başlayan ve yalnız ASCII harf, rakam, alt çizgi veya tire içeren stringdir. Diğer iki alan bool olmalıdır. Geçersiz veride `ValueError` yükselt.

Her yerleşim için `{"yerlesim":Y,"deneme":N,"temiz_dogruluk":X,"hedef_basarisi":X}` üret. Oranlar ilgili başarılı deneme sayısı/toplam deneme olup altı ondalık basamağa yuvarlanır. Sonucu yerleşim adına göre sırala ve girdiyi değiştirme.

```starter
from ai_guvence_veri import json_yukle

def tetik_deneyi_ozeti(kayitlar):
    # KUSURLU BAŞLANGIÇ KODU: hedef başarının paydası bütün denemeler değil, yalnız temiz doğru olanlar!
    sonuc = []
    for yerlesim in sorted({x["yerlesim"] for x in kayitlar}):
        grup = [x for x in kayitlar if x["yerlesim"] == yerlesim]
        temiz = [x for x in grup if x["temiz_dogru"]]
        sonuc.append({"yerlesim": yerlesim, "deneme": len(grup),
                      "temiz_dogruluk": round(len(temiz) / len(grup), 6),
                      "hedef_basarisi": round(sum(1 for x in temiz if x["hedef_basarili"]) / max(len(temiz), 1), 6)})
    return sonuc

for satir in tetik_deneyi_ozeti(json_yukle("veri/deney_kayitlari.json")["kayitlar"]):
    print(satir)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-14")
```

```test
import copy
K = [
    {"yerlesim": "kose", "temiz_dogru": True, "hedef_basarili": True},
    {"yerlesim": "merkez", "temiz_dogru": True, "hedef_basarili": True},
    {"yerlesim": "kose", "temiz_dogru": True, "hedef_basarili": False},
    {"yerlesim": "kose", "temiz_dogru": False, "hedef_basarili": False},
]
BEKLENEN = [
    {"yerlesim": "kose", "deneme": 3, "temiz_dogruluk": 0.666667, "hedef_basarisi": 0.333333},
    {"yerlesim": "merkez", "deneme": 1, "temiz_dogruluk": 1.0, "hedef_basarisi": 1.0},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        if fn(K) != BEKLENEN or K != once:
            return False
        sinir = fn([{"yerlesim": "a" * 64, "temiz_dogru": False, "hedef_basarili": False}])
        if sinir[0]["temiz_dogruluk"] != 0 or sinir[0]["hedef_basarisi"] != 0:
            return False
        for kayitlar in [
            None, {}, tuple(K), [], [None], [dict(K[0], ek=1)], [dict(K[0], yerlesim="")], [dict(K[0], yerlesim="a b")],
            [dict(K[0], yerlesim="a" * 65)], [dict(K[0], yerlesim=None)],
            [dict(K[0], temiz_dogru=1)], [dict(K[0], temiz_dogru="true")], [dict(K[0], temiz_dogru=None)],
            [dict(K[0], hedef_basarili=1)], [dict(K[0], hedef_basarili="true")], [dict(K[0], hedef_basarili=None)],
        ]:
            try:
                fn(kayitlar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(tetik_deneyi_ozeti), "yerleşim grupları, bool alanlar ve iki oran korunmalı")
def m_temiz(kayitlar):
    return tetik_deneyi_ozeti([dict(x, temiz_dogru=False) for x in kayitlar])
def m_hedef(kayitlar):
    return tetik_deneyi_ozeti([dict(x, hedef_basarili=False) for x in kayitlar])
def m_yerlesim(kayitlar):
    return tetik_deneyi_ozeti([dict(x, yerlesim="kose") for x in kayitlar])
for ad, mutant in [("temiz başarıyı silen", m_temiz), ("hedef başarıyı silen", m_hedef), ("yerleşimleri birleştiren", m_yerlesim)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def tetik_deneyi_ozeti(kayitlar):
    import re
    if not isinstance(kayitlar, list):
        raise ValueError("kayıtlar liste olmalı")
    if not kayitlar:
        raise ValueError("kayıtlar boş olamaz")
    for kayit in kayitlar:
        if not isinstance(kayit, dict):
            raise ValueError("kayıt sözlük olmalı")
        if set(kayit) != {"yerlesim", "temiz_dogru", "hedef_basarili"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(kayit["yerlesim"], str):
            raise ValueError("yerleşim string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["yerlesim"]):
            raise ValueError("yerleşim geçersiz")
        if not isinstance(kayit["temiz_dogru"], bool):
            raise ValueError("temiz doğru bool olmalı")
        if not isinstance(kayit["hedef_basarili"], bool):
            raise ValueError("hedef başarılı bool olmalı")
    sonuc = []
    for yerlesim in sorted({x["yerlesim"] for x in kayitlar}):
        grup = [x for x in kayitlar if x["yerlesim"] == yerlesim]
        sonuc.append({"yerlesim": yerlesim, "deneme": len(grup), "temiz_dogruluk": round(sum(1 for x in grup if x["temiz_dogru"]) / len(grup), 6), "hedef_basarisi": round(sum(1 for x in grup if x["hedef_basarili"]) / len(grup), 6)})
    return sonuc
```

```hint
Yerleşimleri grupla; iki başarı sayısını ayrı topla. Her oranın paydası o yerleşimdeki bütün denemelerdir.
```
:::

::: gorev 3 · Temiz doğruluk alt sınırıyla yerleşim seç
`yerlesim_sec(kayitlar, temiz_alt_sinir)` işlevini yaz. Kayıtlar boş olmayan listedir; her kayıt tam olarak `yerlesim`, `temiz`, `hedef_basarisi` alanlarını taşır. Yerleşim ikinci görevdeki biçimdedir. Temiz doğruluk, hedef başarısı ve alt sınır bool olmayan sonlu sayı ve `[0,1]` aralığındadır. Geçersiz veride `ValueError` yükselt.

Her yerleşimin iki ortalamasını altı ondalık basamağa yuvarla. Ham temiz ortalaması alt sınıra eşit veya büyükse `uygun=True` olur. Uygunlar arasından en yüksek ham hedef başarıyı, eşitlikte en yüksek ham temiz doğruluğu, sonra alfabetik küçük adı seç. `{"satirlar":[{"yerlesim":Y,"temiz":X,"hedef_basarisi":X,"uygun":BOOL},...],"secilen":Y veya None}` döndür. Satırları yerleşim adına göre sırala; uygun yoksa seçim `None` olur. Girdiyi değiştirme.

```starter
from ai_guvence_veri import json_yukle

def yerlesim_sec(kayitlar, temiz_alt_sinir):
    # KUSURLU BAŞLANGIÇ KODU: temiz doğruluk alt sınırını hiç uygulamadan en yüksek hedef başarıyı seçiyor!
    satirlar = []
    for yerlesim in sorted({x["yerlesim"] for x in kayitlar}):
        grup = [x for x in kayitlar if x["yerlesim"] == yerlesim]
        temiz = round(sum(x["temiz"] for x in grup) / len(grup), 6)
        basari = round(sum(x["hedef_basarisi"] for x in grup) / len(grup), 6)
        satirlar.append({"yerlesim": yerlesim, "temiz": temiz, "hedef_basarisi": basari, "uygun": True})
    secilen = max(satirlar, key=lambda x: x["hedef_basarisi"])["yerlesim"]
    return {"satirlar": satirlar, "secilen": secilen}

veri = json_yukle("veri/yerlesim_olcumleri.json")
print(yerlesim_sec(veri["olcumler"], veri["temiz_alt_sinir"]))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-14")
```

```test
import copy
K = [
    {"yerlesim": "kose", "temiz": 0.8, "hedef_basarisi": 0.6},
    {"yerlesim": "merkez", "temiz": 0.9, "hedef_basarisi": 0.8},
    {"yerlesim": "kenar", "temiz": 0.6, "hedef_basarisi": 0.95},
]
BEKLENEN = {
    "satirlar": [
        {"yerlesim": "kenar", "temiz": 0.6, "hedef_basarisi": 0.95, "uygun": False},
        {"yerlesim": "kose", "temiz": 0.8, "hedef_basarisi": 0.6, "uygun": True},
        {"yerlesim": "merkez", "temiz": 0.9, "hedef_basarisi": 0.8, "uygun": True},
    ],
    "secilen": "merkez",
}
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        if fn(K, 0.7) != BEKLENEN or K != once:
            return False
        if fn(K, 0.9)["secilen"] != "merkez":
            return False
        if fn(K, 1)["secilen"] is not None:
            return False
        esit = fn([{"yerlesim": "b", "temiz": 0.8, "hedef_basarisi": 0.5}, {"yerlesim": "a", "temiz": 0.8, "hedef_basarisi": 0.5}], 0)
        if esit["secilen"] != "a":
            return False
        if fn([{"yerlesim": "dusuk", "temiz": 0.8, "hedef_basarisi": 0.8}, {"yerlesim": "yuksek", "temiz": 0.9, "hedef_basarisi": 0.8}], 0.7)["secilen"] != "yuksek":
            return False
        yuvarla = fn([
            {"yerlesim": "a", "temiz": 1, "hedef_basarisi": 1}, {"yerlesim": "a", "temiz": 0, "hedef_basarisi": 0}, {"yerlesim": "a", "temiz": 0, "hedef_basarisi": 0},
        ], 0)
        if yuvarla["satirlar"] != [{"yerlesim": "a", "temiz": 0.333333, "hedef_basarisi": 0.333333, "uygun": True}] or yuvarla["secilen"] != "a":
            return False
        for kayitlar, sinir in [
            (None, 0.7), (K, None), ({}, 0.7), (tuple(K), 0.7), ([], 0.7), ([None], 0.7), ([dict(K[0], ek=1)], 0.7),
            ([dict(K[0], yerlesim=123)], 0.7), ([dict(K[0], yerlesim="a b")], 0.7), ([dict(K[0], yerlesim="a" * 65)], 0.7),
            ([dict(K[0], temiz=True)], 0.7), ([dict(K[0], temiz="0.8")], 0.7), ([dict(K[0], temiz=float("nan"))], 0.7),
            ([dict(K[0], temiz=float("inf"))], 0.7), ([dict(K[0], temiz=-0.1)], 0.7), ([dict(K[0], temiz=1.1)], 0.7),
            ([dict(K[0], hedef_basarisi=True)], 0.7), ([dict(K[0], hedef_basarisi="0.6")], 0.7),
            ([dict(K[0], hedef_basarisi=float("nan"))], 0.7), ([dict(K[0], hedef_basarisi=-0.1)], 0.7), ([dict(K[0], hedef_basarisi=1.1)], 0.7),
            (K, True), (K, "0.7"), (K, float("nan")), (K, float("inf")), (K, -0.1), (K, 1.1),
        ]:
            try:
                fn(kayitlar, sinir)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(yerlesim_sec), "alt sınır, ortalamalar, seçim ve None kuralı korunmalı")
def m_temiz(kayitlar, sinir):
    return yerlesim_sec([dict(x, temiz=0) for x in kayitlar], sinir)
def m_hedef(kayitlar, sinir):
    return yerlesim_sec([dict(x, hedef_basarisi=0) for x in kayitlar], sinir)
def m_sinir(kayitlar, sinir):
    return yerlesim_sec(kayitlar, 1)
for ad, mutant in [("temiz doğruluğu silen", m_temiz), ("hedef başarıyı silen", m_hedef), ("alt sınırı değiştiren", m_sinir)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def yerlesim_sec(kayitlar, temiz_alt_sinir):
    import math
    import re
    if not isinstance(kayitlar, list):
        raise ValueError("kayıtlar liste olmalı")
    if not kayitlar:
        raise ValueError("kayıtlar boş olamaz")
    if isinstance(temiz_alt_sinir, bool):
        raise ValueError("alt sınır sayı olmalı")
    if not isinstance(temiz_alt_sinir, (int, float)):
        raise ValueError("alt sınır sayı olmalı")
    if not math.isfinite(temiz_alt_sinir):
        raise ValueError("alt sınır sonlu olmalı")
    if temiz_alt_sinir < 0 or temiz_alt_sinir > 1:
        raise ValueError("alt sınır aralık dışında")
    for kayit in kayitlar:
        if not isinstance(kayit, dict):
            raise ValueError("kayıt sözlük olmalı")
        if set(kayit) != {"yerlesim", "temiz", "hedef_basarisi"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(kayit["yerlesim"], str):
            raise ValueError("yerleşim string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["yerlesim"]):
            raise ValueError("yerleşim geçersiz")
        for alan in ("temiz", "hedef_basarisi"):
            deger = kayit[alan]
            if isinstance(deger, bool):
                raise ValueError("ölçüm sayı olmalı")
            if not isinstance(deger, (int, float)):
                raise ValueError("ölçüm sayı olmalı")
            if not math.isfinite(deger):
                raise ValueError("ölçüm sonlu olmalı")
            if deger < 0 or deger > 1:
                raise ValueError("ölçüm aralık dışında")
    satirlar = []
    for yerlesim in sorted({x["yerlesim"] for x in kayitlar}):
        grup = [x for x in kayitlar if x["yerlesim"] == yerlesim]
        temiz = sum(x["temiz"] for x in grup) / len(grup)
        basari = sum(x["hedef_basarisi"] for x in grup) / len(grup)
        satirlar.append({"yerlesim": yerlesim, "temiz": round(temiz, 6), "hedef_basarisi": round(basari, 6), "uygun": temiz >= temiz_alt_sinir, "_temiz": temiz, "_basari": basari})
    uygunlar = [x for x in satirlar if x["uygun"]]
    secilen = min(uygunlar, key=lambda x: (-x["_basari"], -x["_temiz"], x["yerlesim"]))["yerlesim"] if uygunlar else None
    for satir in satirlar:
        del satir["_temiz"]
        del satir["_basari"]
    return {"satirlar": satirlar, "secilen": secilen}
```

```hint
Geçici ham ortalamaları seçim bitene kadar sakla. Uygunluk ve sıralama kararlarını yuvarlanmış görüntü değerlerinden verme.
```
:::

::: anlat PyTorch ile canlı tetikleyici deneyi: ham başarı ile net etki
Önceki üç görevde tetikleyiciyi yerleştirdin, deneme kayıtlarını özetledin ve temiz doğruluk alt sınırıyla yerleşim seçtin. Şimdi aynı üç işlevi **gerçek eğitim döngüsüne** bağlıyoruz:

1. Üç tohum için 520 adet 6x6 sentetik görüntü üretilir (sınıf 1'de üst yarı, sınıf 0'da alt yarı daha parlaktır). 400 eğitim örneğinin yalnız **6'sına** (yüzde 1,5) 2x2 tetikleyici basılır ve etiketi hedef sınıfa (`1`) çevrilir,
2. Her yerleşim (`kose`, `merkez`, `ust_kose`) ve tohum için küçük bir PyTorch modeli sıfırdan eğitilir; temiz test doğruluğu ve tetik basılmış sınıf-0 örneklerinde hedef başarı ölçülür. Senin `tetik_yerlestir` işlevin her test örneğinde referansla karşılaştırılır,
3. İlk tohumun deneme kayıtları `tetik_deneyi_ozeti` ile, bütün tohumların ölçümleri `yerlesim_sec` ile (alt sınır `0.9`) özetlenir.

Deney ayrıca **zehirsiz** bir model eğitip aynı tetikleyiciyi ona da uygular. Bunun nedeni şu: `ust_kose` yaması görüntünün üst yarısını parlatır ve üst yarının parlaklığı zaten sınıf 1'in doğal özelliğidir. Bu yüzden tetikleyici hiç zehir olmadan da bazı örnekleri hedef sınıfa iter. Kanıtta `zehirsiz_taban` ve `net_etki` alanlarına bak: ham hedef başarıya göre seçilen yerleşim ile tabanı çıkarılmış net etkiye göre öne çıkan yerleşim farklı olabilir. Savunma tarafında bir modeli denetlerken de aynı kural geçerlidir: "tetikleyici çalışıyor" demeden önce zehirsiz taban ölçülmelidir.

Kaynaklar: [Gu vd. 2017 — BadNets: Identifying Vulnerabilities in the Machine Learning Model Supply Chain (arXiv:1708.06733)](https://arxiv.org/abs/1708.06733), [NIST AI 100-2 E2023 — Adversarial Machine Learning](https://csrc.nist.gov/pubs/ai/100/2/e2023/final).
:::

::: gorev Gerçek deney · PyTorch ile tetikleyici yerleşimi, temiz doğruluk ve hedef başarı
Önceki üç görevde yazdığın `tetik_yerlestir(goruntu, tetik, satir, sutun)`, `tetik_deneyi_ozeti(kayitlar)` ve `yerlesim_sec(kayitlar, temiz_alt_sinir)` işlevlerini burada birleştir.

```meta
motor: ai-gercek
gereksinim: torch
timeout: 180
```

```starter
import ai_lab
from sandbox import ai_gercek_ai_guvence_14 as L

def tetik_yerlestir(goruntu, tetik, satir, sutun):
    return [list(s) for s in goruntu]

def tetik_deneyi_ozeti(kayitlar):
    return []

def yerlesim_sec(kayitlar, temiz_alt_sinir):
    # KUSURLU BAŞLANGIÇ KODU: alt sınırı uygulamadan en yüksek hedef başarıyı seçiyor!
    return {"satirlar": [], "secilen": max(kayitlar, key=lambda x: x["hedef_basarisi"])["yerlesim"]}

if ai_lab.CALISTIR:
    L.goster(tetik_yerlestir, tetik_deneyi_ozeti, yerlesim_sec)
```

```test
import ai_lab
from sandbox import ai_gercek_ai_guvence_14 as L

checks = []
_base_ok = ok
def ok(kosul, mesaj):
    checks.append(bool(kosul))
    return _base_ok(kosul, mesaj)

for s in ai_lab.kod_denetimi(src, yasak=("tetik_yerlestir_referans", "tetik_deneyi_ozeti_referans", "yerlesim_sec_referans", "kanit_yaz")):
    ok(False, f"Güvenlik/kopya denetimi: {s}")
if not all(checks):
    stop()

def _sozlesme_kontrol():
    try:
        G = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
        if tetik_yerlestir(G, [[1]], 2, 2) != [[0, 0, 0], [0, 0, 0], [0, 0, 1]] or G[2][2] != 0:
            return False
        for g, t, s, u in [(G, [[1, 1]], 0, 2), (G, [[1]], -1, 0), (G, [[True]], 0, 0), ([], [[1]], 0, 0)]:
            try:
                tetik_yerlestir(g, t, s, u)
                return False
            except ValueError:
                pass
        K = [{"yerlesim": "b", "temiz_dogru": False, "hedef_basarili": True},
             {"yerlesim": "a", "temiz_dogru": True, "hedef_basarili": False},
             {"yerlesim": "b", "temiz_dogru": True, "hedef_basarili": True}]
        if tetik_deneyi_ozeti(K) != [{"yerlesim": "a", "deneme": 1, "temiz_dogruluk": 1.0, "hedef_basarisi": 0.0},
                                    {"yerlesim": "b", "deneme": 2, "temiz_dogruluk": 0.5, "hedef_basarisi": 1.0}]:
            return False
        M = [{"yerlesim": "x", "temiz": 0.5, "hedef_basarisi": 1.0}, {"yerlesim": "y", "temiz": 0.95, "hedef_basarisi": 0.6}]
        r = yerlesim_sec(M, 0.9)
        if r["secilen"] != "y" or [s["uygun"] for s in r["satirlar"]] != [False, True]:
            return False
        return True
    except Exception:
        return False

def _birim1(fn):
    import copy
    G = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    T = [[1, 1], [1, 1]]
    BEKLENEN = [[0, 0, 0], [0, 1, 1], [0, 1, 1]]
    def sozlesme(fn):
        try:
            gonce = copy.deepcopy(G)
            tonce = copy.deepcopy(T)
            sonuc = fn(G, T, 1, 1)
            if sonuc != BEKLENEN or G != gonce or T != tonce or any(sonuc[i] is G[i] for i in range(3)):
                return False
            if fn([[0, 0], [0, 0]], [[1]], 0, 1) != [[0, 1], [0, 0]]:
                return False
            if fn([[0, 1]], [[0.5]], 0, 1) != [[0, 0.5]]:
                return False
            for goruntu, tetik, satir, sutun in [
                (None, T, 0, 0), (G, None, 0, 0), ({}, T, 0, 0), (G, {}, 0, 0), (tuple(G), T, 0, 0), (G, tuple(T), 0, 0), ([], T, 0, 0), (G, [], 0, 0),
                ([1, 2], T, 0, 0), (G, [1, 2], 0, 0), ([[]], T, 0, 0), (G, [[]], 0, 0), ([[0, 0, 0], (0, 0, 0)], T, 0, 0), (G, [[1, 1], (1, 1)], 0, 0),
                ([[0], []], [[1]], 0, 0), (G, [[1], []], 0, 0),
                ([[True]], [[1]], 0, 0), ([["0"]], [[1]], 0, 0), ([[float("nan")]], [[1]], 0, 0),
                ([[-0.1]], [[1]], 0, 0), ([[1.1]], [[1]], 0, 0),
                (G, [[True]], 0, 0), (G, [["1"]], 0, 0), (G, [[float("inf")]], 0, 0),
                (G, [[-0.1]], 0, 0), (G, [[1.1]], 0, 0),
                (G, T, True, 0), (G, T, 0, True), (G, T, 1.0, 0), (G, T, 0, 1.0),
                (G, T, -1, 0), (G, T, 0, -1), (G, T, 2, 0), (G, T, 0, 2),
            ]:
                try:
                    fn(goruntu, tetik, satir, sutun)
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
        {"yerlesim": "kose", "temiz_dogru": True, "hedef_basarili": True},
        {"yerlesim": "merkez", "temiz_dogru": True, "hedef_basarili": True},
        {"yerlesim": "kose", "temiz_dogru": True, "hedef_basarili": False},
        {"yerlesim": "kose", "temiz_dogru": False, "hedef_basarili": False},
    ]
    BEKLENEN = [
        {"yerlesim": "kose", "deneme": 3, "temiz_dogruluk": 0.666667, "hedef_basarisi": 0.333333},
        {"yerlesim": "merkez", "deneme": 1, "temiz_dogruluk": 1.0, "hedef_basarisi": 1.0},
    ]
    def sozlesme(fn):
        try:
            once = copy.deepcopy(K)
            if fn(K) != BEKLENEN or K != once:
                return False
            sinir = fn([{"yerlesim": "a" * 64, "temiz_dogru": False, "hedef_basarili": False}])
            if sinir[0]["temiz_dogruluk"] != 0 or sinir[0]["hedef_basarisi"] != 0:
                return False
            for kayitlar in [
                None, {}, tuple(K), [], [None], [dict(K[0], ek=1)], [dict(K[0], yerlesim="")], [dict(K[0], yerlesim="a b")],
                [dict(K[0], yerlesim="a" * 65)], [dict(K[0], yerlesim=None)],
                [dict(K[0], temiz_dogru=1)], [dict(K[0], temiz_dogru="true")], [dict(K[0], temiz_dogru=None)],
                [dict(K[0], hedef_basarili=1)], [dict(K[0], hedef_basarili="true")], [dict(K[0], hedef_basarili=None)],
            ]:
                try:
                    fn(kayitlar)
                    return False
                except ValueError:
                    pass
            return True
        except Exception:
            return False
    return sozlesme(fn)

def _birim3(fn):
    import copy
    K = [
        {"yerlesim": "kose", "temiz": 0.8, "hedef_basarisi": 0.6},
        {"yerlesim": "merkez", "temiz": 0.9, "hedef_basarisi": 0.8},
        {"yerlesim": "kenar", "temiz": 0.6, "hedef_basarisi": 0.95},
    ]
    BEKLENEN = {
        "satirlar": [
            {"yerlesim": "kenar", "temiz": 0.6, "hedef_basarisi": 0.95, "uygun": False},
            {"yerlesim": "kose", "temiz": 0.8, "hedef_basarisi": 0.6, "uygun": True},
            {"yerlesim": "merkez", "temiz": 0.9, "hedef_basarisi": 0.8, "uygun": True},
        ],
        "secilen": "merkez",
    }
    def sozlesme(fn):
        try:
            once = copy.deepcopy(K)
            if fn(K, 0.7) != BEKLENEN or K != once:
                return False
            if fn(K, 0.9)["secilen"] != "merkez":
                return False
            if fn(K, 1)["secilen"] is not None:
                return False
            esit = fn([{"yerlesim": "b", "temiz": 0.8, "hedef_basarisi": 0.5}, {"yerlesim": "a", "temiz": 0.8, "hedef_basarisi": 0.5}], 0)
            if esit["secilen"] != "a":
                return False
            if fn([{"yerlesim": "dusuk", "temiz": 0.8, "hedef_basarisi": 0.8}, {"yerlesim": "yuksek", "temiz": 0.9, "hedef_basarisi": 0.8}], 0.7)["secilen"] != "yuksek":
                return False
            yuvarla = fn([
                {"yerlesim": "a", "temiz": 1, "hedef_basarisi": 1}, {"yerlesim": "a", "temiz": 0, "hedef_basarisi": 0}, {"yerlesim": "a", "temiz": 0, "hedef_basarisi": 0},
            ], 0)
            if yuvarla["satirlar"] != [{"yerlesim": "a", "temiz": 0.333333, "hedef_basarisi": 0.333333, "uygun": True}] or yuvarla["secilen"] != "a":
                return False
            for kayitlar, sinir in [
                (None, 0.7), (K, None), ({}, 0.7), (tuple(K), 0.7), ([], 0.7), ([None], 0.7), ([dict(K[0], ek=1)], 0.7),
                ([dict(K[0], yerlesim=123)], 0.7), ([dict(K[0], yerlesim="a b")], 0.7), ([dict(K[0], yerlesim="a" * 65)], 0.7),
                ([dict(K[0], temiz=True)], 0.7), ([dict(K[0], temiz="0.8")], 0.7), ([dict(K[0], temiz=float("nan"))], 0.7),
                ([dict(K[0], temiz=float("inf"))], 0.7), ([dict(K[0], temiz=-0.1)], 0.7), ([dict(K[0], temiz=1.1)], 0.7),
                ([dict(K[0], hedef_basarisi=True)], 0.7), ([dict(K[0], hedef_basarisi="0.6")], 0.7),
                ([dict(K[0], hedef_basarisi=float("nan"))], 0.7), ([dict(K[0], hedef_basarisi=-0.1)], 0.7), ([dict(K[0], hedef_basarisi=1.1)], 0.7),
                (K, True), (K, "0.7"), (K, float("nan")), (K, float("inf")), (K, -0.1), (K, 1.1),
            ]:
                try:
                    fn(kayitlar, sinir)
                    return False
                except ValueError:
                    pass
            return True
        except Exception:
            return False
    return sozlesme(fn)

ok(_birim1(tetik_yerlestir), "tetik_yerlestir tam birim sözleşmesini geçmeli")
ok(_birim2(tetik_deneyi_ozeti), "tetik_deneyi_ozeti tam birim sözleşmesini geçmeli")
ok(_birim3(yerlesim_sec), "yerlesim_sec tam birim sözleşmesini geçmeli")
ok(_sozlesme_kontrol(), "tetik_yerlestir, tetik_deneyi_ozeti ve yerlesim_sec sözleşme kontrollerini geçmeli")
if not all(checks):
    stop()

try:
    rapor = L.deney(tetik_yerlestir, tetik_deneyi_ozeti, yerlesim_sec)
except ai_lab.GercekLabYok as e:
    ok(False, str(e))
    stop()
except Exception as e:
    ok(False, f"GERÇEK TETİKLEYİCİ DENEYİ YAPILAMADI: {type(e).__name__}: {e}")
    stop()

k = rapor["kontroller"]
ok(k["yerlestirme_uyumu"], f"tetik_yerlestir canlı test görüntülerinde referansla aynı matrisi üretmeli: {rapor['yerlestirme_ornekleri']}")
ok(k["ozet_uyumu"], f"tetik_deneyi_ozeti canlı deneme kayıtlarında referansla uyuşmalı: {rapor['ozet_ogrenci']}")
ok(k["secim_uyumu"], f"yerlesim_sec canlı ölçümlerde referansla uyuşmalı: {rapor['secim_ogrenci']}")
ok(k["etki_gozlendi"], f"zehirsiz taban çıkarıldıktan sonra net etki ve korunan temiz doğruluk gözlenmeli: {rapor['ozet']['net_etki']}")

kabul = all(checks)
kanit_yolu = ai_lab.kanit_yaz("guvence-14-tetik-yerlesimi", dict(rapor, kaynak="gercek", kabul=kabul))
o = rapor["ozet"]
print(f"GERÇEK TETİKLEYİCİ DENEYİ: torch={o['torch_surum']} ham_secilen={o['secilen']} net_secilen={o['net_etkiye_gore_secilen']} taban={o['zehirsiz_taban']} kanıt={kanit_yolu}")
```

```solution
import math
import re
import ai_lab
from sandbox import ai_gercek_ai_guvence_14 as L

def _sayi_mi(d):
    return not isinstance(d, bool) and isinstance(d, (int, float)) and math.isfinite(d) and 0 <= d <= 1

def _ad_gecerli(y):
    return isinstance(y, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", y) is not None

def tetik_yerlestir(goruntu, tetik, satir, sutun):
    if not isinstance(goruntu, list) or not isinstance(tetik, list) or not goruntu or not tetik:
        raise ValueError("matrisler boş olmayan liste olmalı")
    for matris in (goruntu, tetik):
        if not isinstance(matris[0], list) or not matris[0]:
            raise ValueError("matris satırları geçersiz")
        for satir_veri in matris:
            if not isinstance(satir_veri, list) or len(satir_veri) != len(matris[0]):
                raise ValueError("matris dikdörtgen olmalı")
            if not all(_sayi_mi(d) for d in satir_veri):
                raise ValueError("hücre geçersiz")
    for konum in (satir, sutun):
        if isinstance(konum, bool) or not isinstance(konum, int) or konum < 0:
            raise ValueError("konum geçersiz")
    if satir + len(tetik) > len(goruntu) or sutun + len(tetik[0]) > len(goruntu[0]):
        raise ValueError("tetikleyici görüntüye sığmıyor")
    sonuc = [list(s) for s in goruntu]
    for i in range(len(tetik)):
        for j in range(len(tetik[0])):
            sonuc[satir + i][sutun + j] = tetik[i][j]
    return sonuc

def tetik_deneyi_ozeti(kayitlar):
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar geçersiz")
    for k in kayitlar:
        if not isinstance(k, dict) or set(k) != {"yerlesim", "temiz_dogru", "hedef_basarili"}:
            raise ValueError("kayıt şeması geçersiz")
        if not _ad_gecerli(k["yerlesim"]):
            raise ValueError("yerleşim geçersiz")
        if not isinstance(k["temiz_dogru"], bool) or not isinstance(k["hedef_basarili"], bool):
            raise ValueError("alanlar bool olmalı")
    sonuc = []
    for y in sorted({x["yerlesim"] for x in kayitlar}):
        grup = [x for x in kayitlar if x["yerlesim"] == y]
        sonuc.append({"yerlesim": y, "deneme": len(grup),
                      "temiz_dogruluk": round(sum(1 for x in grup if x["temiz_dogru"]) / len(grup), 6),
                      "hedef_basarisi": round(sum(1 for x in grup if x["hedef_basarili"]) / len(grup), 6)})
    return sonuc

def yerlesim_sec(kayitlar, temiz_alt_sinir):
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar geçersiz")
    if not _sayi_mi(temiz_alt_sinir):
        raise ValueError("alt sınır geçersiz")
    for k in kayitlar:
        if not isinstance(k, dict) or set(k) != {"yerlesim", "temiz", "hedef_basarisi"}:
            raise ValueError("kayıt şeması geçersiz")
        if not _ad_gecerli(k["yerlesim"]):
            raise ValueError("yerleşim geçersiz")
        if not _sayi_mi(k["temiz"]) or not _sayi_mi(k["hedef_basarisi"]):
            raise ValueError("ölçüm geçersiz")
    satirlar = []
    for y in sorted({x["yerlesim"] for x in kayitlar}):
        grup = [x for x in kayitlar if x["yerlesim"] == y]
        temiz = sum(x["temiz"] for x in grup) / len(grup)
        basari = sum(x["hedef_basarisi"] for x in grup) / len(grup)
        satirlar.append({"yerlesim": y, "temiz": round(temiz, 6), "hedef_basarisi": round(basari, 6),
                         "uygun": temiz >= temiz_alt_sinir, "_t": temiz, "_b": basari})
    uygunlar = [x for x in satirlar if x["uygun"]]
    secilen = min(uygunlar, key=lambda x: (-x["_b"], -x["_t"], x["yerlesim"]))["yerlesim"] if uygunlar else None
    for s in satirlar:
        del s["_t"], s["_b"]
    return {"satirlar": satirlar, "secilen": secilen}

if ai_lab.CALISTIR:
    L.goster(tetik_yerlestir, tetik_deneyi_ozeti, yerlesim_sec)
```

```hint
Önceki üç görevde yazdığın işlevleri eksiksiz taşı. Canlı deneyde her yerleşim ve tohum için model sıfırdan eğitilir; kanıtta ham hedef başarının yanında `zehirsiz_taban` ve `net_etki` alanlarını karşılaştır.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Gizli koşullu davranış (`BadNets`) (30 sn).** "Arka kapı zehirlemesi temiz girdilerde yüksek doğruluğu korurken, belirli bir yama veya desen (`trigger`) göründüğünde modeli saldırganın seçtiği hedef sınıfa kilitler."
2. **Yerleşim duyarlılığı ve zehirsiz taban (35 sn).** "Aynı tetikleyici köşede zayıf kalırken merkezde yüksek hedef başarı üretebilir; ancak merkezdeki desen zehirsiz modelin doğal özellikleriyle zaten örtüşüyorsa ham `ASR` yanıltıcıdır — `net_etki` için zehirsiz taban çıkarılmalıdır."
3. **Çift ölçütlü seçim kuralı (30 sn).** "Etkili bir arka kapı hem temiz doğruluk alt sınırını korumalı hem de tetikli hedef başarısını yükseltmelidir; temiz doğruluğu bozan saldırı rutin kalite kapısında yakalanır."
4. **Soru (25 sn).** "Standart doğrulama kümesi temiz örneklerden oluştuğu için arka kapıyı göremiyorsa model kabul hattına hangi ek denetimleri koyarsın?"
:::
