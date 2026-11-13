---
id: ai-temel-29
title: Glitch Token Keşfi ve Non-Canonical BPE · Sözlük Anomalilerini Yakalamak
summary: Sözlük embedding matrisinde düşük L2 normlu ve yüksek çıktı entropili glitch token adaylarını tara, kanonik olmayan BPE parçalamalarını doğrula.
esleme: ai-temel-01, ai-temel-02, ai-guvence-05
timeout: 60
---

::: anlat Bir token modelin davranışını neden aniden bozar?
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Tokenizer sözlüğüne girmiş ancak eğitim derleminde filtrelendiği için hiç güncellenmemiş `glitch token` örnekleri (ör. `SolidGoldMagikarp`), embedding uzayında başlangıç gürültüsüne yakın kalır ve yüksek çıktı entropisi üretir | İlk üç görev: `veri/glitch_bpe.json` içindeki **sentetik** embedding vektörleri, entropiler ve `BPE` birleştirme kuralları. Final: GPU üzerinde 16 tokenlı PyTorch embedding ve LM başlığı eğitimi | Düşük normlu her tokenın her istemde (prompt) modeli çökerteceğini söyleyemez |
| Doğrudan token ID dizisi kabul eden API'lerde saldırgan bir kelimeyi birleştirilmemiş alt-parçalarla (non-canonical `BPE`) göndererek kelime tabanlı güvenlik filtrelerini atlatabilir | Bağıl L2 norm oranı, komşu çiftlerin `BPE` birleştirme kurallarıyla denetimi ve çift eşikli glitch taraması | Kanonik `BPE` zorlamasının karakter düzeyindeki (homoglyph/leetspeak) tüm kaçışları engellediğini kanıtlamaz |

> [!NOT]
> Görevler `veri/glitch_bpe.json` dosyasını okur; dosya sentetiktir. Setup her Çalıştır/Kontrol Et adımında geçici kopya kurar; değişiklikler taşınmaz, **kalıcılık yoktur**. Ekranda ayrı dosya görüntüleyici yoktur; içeriği görmek için `print` kullan. Gizli testler ayrıdır. Final yeni model indirmez ve GPU varsa onu kullanır.

ai-temel-01 `BPE` (Byte-Pair Encoding) birleştirme kurallarını, ai-temel-02 ise token embedding uzayını inceler. Bu ders şu soruyu sorar: **Tokenizer eğitimi ile model ön-eğitimi (pre-training) arasındaki veri uyumsuzluğu sözlükte nasıl "hayalet" (`glitch token`) girdiler bırakır ve kanonik olmayan `BPE` dizileri filtreleri nasıl yanıltır?**

**`glitch token` nasıl oluşur?** Tokenizer (ör. `cl100k_base` veya Llama BPE) ham web verisi üzerinde eğitilirken, bir Reddit kullanıcı adı veya kaynak kodu dizgesi çok sık geçtiği için tek bir token ID alır. Ancak daha sonra model ön-eğitim verisi temizlenirken o kaynak tamamen filtrelenirse, bu token eğitim boyunca **hiç (veya neredeyse hiç) görülmez** (Rumbelow ve Watkins 2023; Land ve Bartolo 2024).

**Embedding normu ve çıktı entropisi imzası.** Eğitim gören normal tokenların embedding vektörleri $v_i \in \mathbb{R}^D$ gradyan güncellemeleriyle büyürken, eğitimsiz `glitch token` vektörleri sıfıra yakın başlangıç normunda ($\|v_i\|_2 \ll \bar{n}$) asılı kalır. Bu vektör son doğrusal katmana (LM head) girdiğinde bütün logitler sıfıra yakın çıkar ve softmax dağılımı tekdüzeye (uniform) yaklaşarak **çok yüksek Shannon entropisi** $H(p) = -\sum_j p_j \log p_j$ üretir. Modele "Bu kelimeyi tekrar et" dendiğinde model rastgele kelimeler uydurur, döngüye girer veya güvenlik yönergelerini unutur.

**Kanonik olmayan (Non-Canonical) `BPE` saldırısı.** Bir metin normalde `BPE` birleştirme kuralları öncelik sırasıyla tüketilerek tek bir kanonik token dizisine dönüştürülür. Ancak saldırgan API'ye metin yerine doğrudan parçalanmış token ID'leri gönderirse veya ara bölmelerle (`["ka", "ra", "kut", "u"]`) yan yana duran ve birleşmesi gereken bir çifti birleştirmeden bırakırsa, tam token eşleşmesine bakan güvenlik duvarı kelimeyi tanıyamazken model alt-parçaları birleştirip anlamı çözebilir.

**Saldırgan ne dener?** Hedef modelin açık ağırlıklarından embedding matrisini tarayıp en düşük L2 normlu `glitch token` listesini çıkarır (Magikarp avı) ve bunları sistem istemini bozmak (jailbreak / DoS) ya da kanonik olmayan `BPE` parçalarıyla içerik filtresini atlatmak için kullanır.

**Savunma neden kırılır?** Yalnızca metin düzeyinde regex filtresi uygulanıp token dizisinin kanonik `BPE` olup olmadığı denetlenmezse parçalanmış girdiler filtreden geçer; dağıtım öncesinde sözlükteki düşük normlu/yüksek entropili tokenlar taranmazsa model öngörülemez çıktılara açık kalır.

**Görev 1'de sık tuzaklar:** L2 normunda karekök almayı unutmak veya tüm vektörler sıfır olduğunda (`ortalama_norm <= 1e-12`) sıfıra bölme hatasını yakalamamak.

Kaynaklar: [Land ve Bartolo 2024 - Fishing for Magikarp: Automatically Detecting Under-trained Tokens in Large Language Models](https://arxiv.org/abs/2405.05417), [Li vd. 2024 - GlitchProber: Advancing Effective Detection and Mitigation of Glitch Tokens in LLMs](https://arxiv.org/abs/2408.04905), [Sennrich vd. 2016 - Neural Machine Translation of Rare Words with Subword Units (BPE)](https://arxiv.org/abs/1508.07909). Bu dersteki bütün sayılar yalnız yerel kanıttan gelir.

Köprü: ai-temel-01 `BPE` birleştirmesini, ai-temel-02 embedding matrisini kurar; bu ders her ikisindeki yapısal anomalileri güvenlik taramasına dönüştürür.
:::

::: tahmin Eğitimsiz bir embedding vektörü LM başlığında nasıl entropi üretir?
Çıktıyı tahmin et, sonra Çalıştır ile karşılaştır.
```python
import math
def entropi(logitler):
    m = max(logitler)
    exps = [math.exp(z - m) for z in logitler]
    t = sum(exps)
    p = [e / t for e in exps]
    return -sum(pi * math.log(pi) for pi in p if pi > 0)

normal_logit = [4.5, -1.2, -0.8, -2.0]
glitch_logit = [0.01, -0.01, 0.02, -0.02]
print("Normal entropi:", round(entropi(normal_logit), 4))
print("Glitch entropi:", round(entropi(glitch_logit), 4), "| Maksimum (ln 4):", round(math.log(4), 4))
```
???
```cikti
Normal entropi: 0.0646
Glitch entropi: 1.3862 | Maksimum (ln 4): 1.3863
```
Tahmininle gerçek çıktı arasındaki farkı tezgâhta yorum satırı olarak yaz: `Glitch entropi` neden teorik maksimum olan $\ln(4)$ değerine neredeyse eşit çıktı? Sonra üç kusurlu başlangıç kodunu çalıştır ve her birinin neyi kaçırdığını önce kendin teşhis et; açıklama çözümün ardından gelir.
:::

::: gorev 1 · Gömme L2 normu ve bağıl anomali skoru
`gomme_anomali_skoru(vektorler)`: `vektorler` en az 2 elemanlı `list`; her eleman aynı boyutta (`D >= 1`) bool olmayan sonlu sayı listesi. Her vektörün Öklidyen L2 normunu (`normlar`), bu normların ortalamasını (`ortalama_norm`, eğer `<= 1e-12` ise `ValueError`) ve her normun ortalamaya oranını (`bagil_oranlar`) hesaplayarak `{"normlar": [...], "ortalama_norm": float, "bagil_oranlar": [...]}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-29")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def gomme_anomali_skoru(vektorler):
    normlar = [sum(abs(x) for x in v) for v in vektorler]
    ort = sum(normlar) / len(normlar)
    return {"normlar": normlar, "ortalama_norm": ort, "bagil_oranlar": normlar}

from ai_temel_veri import json_yukle
v = json_yukle("veri/glitch_bpe.json")
print("Anomali skoru:", gomme_anomali_skoru(v["sozluk_vektorleri"]))
```
```test
def sinama1(f):
    import copy, math, random
    def _r(vk):
        nl = [math.sqrt(sum(x * x for x in r)) for r in vk]
        ort = sum(nl) / len(nl)
        return {"normlar": nl, "ortalama_norm": ort, "bagil_oranlar": [x / ort for x in nl]}
    def _y(a, b):
        return set(a) == {"normlar", "ortalama_norm", "bagil_oranlar"} and abs(a["ortalama_norm"] - b["ortalama_norm"]) < 1e-12 and len(a["normlar"]) == len(b["normlar"]) and all(abs(x - y) < 1e-12 for x, y in zip(a["normlar"], b["normlar"])) and all(abs(x - y) < 1e-12 for x, y in zip(a["bagil_oranlar"], b["bagil_oranlar"]))
    try:
        vk = [[3.0, 4.0], [0.0, 5.0], [0.0, 0.0]]; old = copy.deepcopy(vk)
        c = f(vk)
        if not _y(c, {"normlar": [5.0, 5.0, 0.0], "ortalama_norm": 10.0 / 3.0, "bagil_oranlar": [1.5, 1.5, 0.0]}) or vk != old:
            return False
        if not _y(f([[2e-12], [2e-12]]), {"normlar": [2e-12, 2e-12], "ortalama_norm": 2e-12, "bagil_oranlar": [1.0, 1.0]}):
            return False
        rng = random.Random(29)
        for _ in range(25):
            V = rng.randint(2, 8); D = rng.randint(1, 6)
            mat = [[rng.uniform(-5, 5) for _ in range(D)] for _ in range(V)]
            if not _y(f(copy.deepcopy(mat)), _r(mat)): return False
        for bad in (
            None, [], [[1.0, 2.0]], [[], []], [[], [1.0]], [[1.0], []], [[1.0], [1.0, 2.0]],
            [[0.0, 0.0], [0.0, 0.0]], [[1e-12], [1e-12]], [[True, 1.0], [1.0, 1.0]],
            [[float("nan")], [1.0]], [[float("inf")], [1.0]], [("1.0",), ("2.0",)]
        ):
            try:
                f(bad)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sinama1(gomme_anomali_skoru), "L2 normu, ortalama norm, bağıl oranlar ve sıfır/geçersiz girdi")
for ad, mut in [
    ("L1 normu", lambda vk: {"normlar": [sum(abs(x) for x in r) for r in vk], "ortalama_norm": 1.0, "bagil_oranlar": [1.0] * len(vk)}),
    ("karekök yok", lambda vk: dict(gomme_anomali_skoru(vk), normlar=[sum(x * x for x in r) for r in vk])),
    ("bağıl oran sabit 1", lambda vk: dict(gomme_anomali_skoru(vk), bagil_oranlar=[1.0] * len(vk)))
]:
    ok(not sinama1(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(gomme_anomali_skoru, _il.import_module('ai_gercek_ai_temel_29').referans_gomme_anomali, ([[1.2, -0.9, 1.5, 0.8], [1.0, 1.4, -1.1, 0.7], [0.04, -0.03, 0.02, 0.01], [-1.3, 1.1, 0.9, -1.0], [0.02, 0.01, -0.02, 0.03]],), tohum=2958)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def gomme_anomali_skoru(vektorler):
    if not isinstance(vektorler, list) or len(vektorler) < 2:
        raise ValueError("vektorler")
    boyut = None
    normlar = []
    for v in vektorler:
        if not isinstance(v, list) or not v:
            raise ValueError("vektor_boyut")
        if boyut is not None and len(v) != boyut:
            raise ValueError("farkli_boyut")
        boyut = len(v)
        for x in v:
            if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
                raise ValueError("sayi")
        normlar.append(math.sqrt(sum(x * x for x in v)))
    ort = sum(normlar) / float(len(normlar))
    if ort <= 1e-12:
        raise ValueError("sifir_norm")
    return {
        "normlar": normlar,
        "ortalama_norm": ort,
        "bagil_oranlar": [n / ort for n in normlar],
    }

if __name__ == "__main__":
    from ai_temel_veri import json_yukle
    v = json_yukle("veri/glitch_bpe.json")
    print("Anomali skoru:", gomme_anomali_skoru(v["sozluk_vektorleri"]))
```
```hint
Her vektörün aynı boyutta olduğunu denetle, `math.sqrt(sum(x * x for x in v))` ile L2 normunu al ve ortalamaya böl.
```
:::

::: anlat Kanonik olmayan (Non-Canonical) BPE parçalamasını yakalamak
Bir token dizisi `parcalar = [p_0, p_1, ..., p_{m-1}]` içinde yan yana duran her `(parcalar[i], parcalar[i+1])` komşu çiftine bakılır.
- Eğer bu komşu çiftlerden herhangi biri `birlesme_kurallari` içinde yer alıyorsa, standart bir `BPE` tokenizer bu çifti birleştireceği için dizi **kanonik değildir** (`kanonik = False`).
- `ihlal_sayisi`: `parcalar` içindeki `(parcalar[i], parcalar[i+1])` komşu konumlarından kaç tanesinin `birlesme_kurallari` kümesinde yer aldığı.
- `ilk_ihlal`: `birlesme_kurallari` listesindeki **öncelik sırasına göre** `parcalar` içinde komşu çift olarak bulunan ilk kural `[sol, sag]` (hiç ihlal yoksa `None`).

**Görev 2'de sık tuzaklar:** `ilk_ihlal` değerini `birlesme_kurallari` öncelik sırası yerine `parcalar` dizisindeki soldan sağa sıraya göre seçmek!
:::

::: gorev 2 · Kanonik BPE doğrulaması
`bpe_kanonik_mi(parcalar, birlesme_kurallari)`: `parcalar` boş olmayan `list`, her eleman boş olmayan `str`; `birlesme_kurallari` `list`, her eleman tam 2 adet boş olmayan `str` içeren `[sol, sag]` listesi. Yukarıdaki kuralla `{"kanonik": bool, "ihlal_sayisi": int, "ilk_ihlal": list[str] veya None}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-29")
```
```starter
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def bpe_kanonik_mi(parcalar, birlesme_kurallari):
    return {"kanonik": True, "ihlal_sayisi": 0, "ilk_ihlal": None}

from ai_temel_veri import json_yukle
v = json_yukle("veri/glitch_bpe.json")
for o in v["bpe_ornekleri"]:
    print(o["ad"], bpe_kanonik_mi(o["parcalar"], v["birlesme_kurallari"]))
```
```test
def sinama2(f):
    import copy
    try:
        kr = [["b", "c"], ["a", "b"], ["c", "d"]]
        p1 = ["a", "b", "c"]
        old = (list(p1), copy.deepcopy(kr))
        c1 = f(p1, kr)
        if c1 != {"kanonik": False, "ihlal_sayisi": 2, "ilk_ihlal": ["b", "c"]} or (p1, kr) != old:
            return False
        if f(["ab", "cd"], kr) != {"kanonik": True, "ihlal_sayisi": 0, "ilk_ihlal": None}:
            return False
        if f(["tek"], kr) != {"kanonik": True, "ihlal_sayisi": 0, "ilk_ihlal": None}:
            return False
        if f(["x", "y"], []) != {"kanonik": True, "ihlal_sayisi": 0, "ilk_ihlal": None}:
            return False
        if f(["a", "b", "a", "b"], [["a", "b"]]) != {"kanonik": False, "ihlal_sayisi": 2, "ilk_ihlal": ["a", "b"]}:
            return False
        for bad in (
            (None, kr), ([], kr), ([""], kr), ([123], kr), (("a", "b"), kr),
            (["a", "b"], None), (["a", "b"], "ab"), (["a", "b"], [["a"]]),
            (["a", "b"], [["a", "b", "c"]]), (["a", "b"], [["", "b"]]),
            (["a", "b"], [("a", "b")]), (["a", "b"], [[1, "b"]])
        ):
            try:
                f(*bad)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sinama2(bpe_kanonik_mi), "komşu çift ihlali, kural öncelik sırası ve geçersiz girdi")
for ad, mut in [
    ("dizi sırasına göre ilk ihlal", lambda p, kr: dict(bpe_kanonik_mi(p, kr), ilk_ihlal=next(([p[i], p[i+1]] for i in range(len(p)-1) if [p[i], p[i+1]] in kr), None))),
    ("hep kanonik", lambda p, kr: {"kanonik": True, "ihlal_sayisi": 0, "ilk_ihlal": None}),
    ("ihlal sayısı sabit 1", lambda p, kr: dict(bpe_kanonik_mi(p, kr), ihlal_sayisi=1 if not bpe_kanonik_mi(p, kr)["kanonik"] else 0))
]:
    ok(not sinama2(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(bpe_kanonik_mi, _il.import_module('ai_gercek_ai_temel_29').referans_bpe_kanonik, (['karakut', 'u'], [['ka', 'ra'], ['kara', 'kut'], ['kut', 'u']]), tohum=2396)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
def bpe_kanonik_mi(parcalar, birlesme_kurallari):
    if not isinstance(parcalar, list) or not parcalar:
        raise ValueError("parcalar")
    for p in parcalar:
        if not isinstance(p, str) or not p:
            raise ValueError("parca_str")
    if not isinstance(birlesme_kurallari, list):
        raise ValueError("kurallar")
    kural_listesi = []
    for k in birlesme_kurallari:
        if not isinstance(k, list) or len(k) != 2 or not isinstance(k[0], str) or not isinstance(k[1], str) or not k[0] or not k[1]:
            raise ValueError("kural_sema")
        kural_listesi.append((k[0], k[1]))
    kural_kumesi = set(kural_listesi)
    ciftler = [(parcalar[i], parcalar[i + 1]) for i in range(len(parcalar) - 1)]
    ihlal_sayisi = sum(1 for c in ciftler if c in kural_kumesi)
    ilk_ihlal = None
    for kural in kural_listesi:
        if kural in ciftler:
            ilk_ihlal = [kural[0], kural[1]]
            break
    return {
        "kanonik": bool(ihlal_sayisi == 0),
        "ihlal_sayisi": ihlal_sayisi,
        "ilk_ihlal": ilk_ihlal,
    }

if __name__ == "__main__":
    from ai_temel_veri import json_yukle
    v = json_yukle("veri/glitch_bpe.json")
    for o in v["bpe_ornekleri"]:
        print(o["ad"], bpe_kanonik_mi(o["parcalar"], v["birlesme_kurallari"]))
```
```hint
Komşu çiftleri `ciftler = [(parcalar[i], parcalar[i+1]) for i in range(len(parcalar)-1)]` olarak çıkar; `ilk_ihlal` için `birlesme_kurallari` üzerinde döngü kurup `ciftler` içinde yer alan ilk kuralı seç.
```
:::

::: anlat Çift eşikli glitch token taraması
Sözlükteki $V$ tokenın embedding vektörleri `sozluk_vektorleri` ve her token tek başına modele verildiğinde ölçülen sonraki-token çıktı entropisi `cikti_entropileri` verilir.
1. Görev 1'deki `bagil_oranlar` hesaplanır.
2. Hem `bagil_oranlar[i] < norm_esik` hem de `cikti_entropileri[i] > entropi_esik` koşulunu sağlayan tüm indisler küçükten büyüğe `glitch_adaylari` listesine eklenir.
3. `glitch_orani = len(glitch_adaylari) / V` hesaplanır.
4. `en_riskli_token`: tüm sözlükte `cikti_entropileri[i] - bagil_oranlar[i]` farkı en yüksek olan token indisi (eşitlikte küçük indis).

**Görev 3'te sık tuzaklar:** İki koşulu `and` yerine `or` ile bağlamak veya `norm_esik` sınırını (`0 < norm_esik <= 1`) denetlememek.
:::

::: gorev 3 · Glitch token tarama raporu
`glitch_tarama_raporu(sozluk_vektorleri, cikti_entropileri, norm_esik, entropi_esik)`: `sozluk_vektorleri` Görev 1 kurallarına uyar ($V \ge 2$); `cikti_entropileri` uzunluğu $V$ olan `>= 0` sonlu sayı listesi; `0 < norm_esik <= 1` ve `entropi_esik > 0` bool olmayan sonlu sayılar. `{"glitch_adaylari": list[int], "glitch_orani": float, "en_riskli_token": int}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-29")
```
```starter
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def glitch_tarama_raporu(sozluk_vektorleri, cikti_entropileri, norm_esik, entropi_esik):
    return {"glitch_adaylari": [], "glitch_orani": 0.0, "en_riskli_token": 0}

from ai_temel_veri import json_yukle
v = json_yukle("veri/glitch_bpe.json")
print("Tarama:", glitch_tarama_raporu(v["sozluk_vektorleri"], v["cikti_entropileri"], v["norm_esik"], v["entropi_esik"]))
```
```test
def sinama3(f):
    import copy, math, random
    def _r(sv, ce, ne, ee):
        nl = [math.sqrt(sum(x * x for x in v)) for v in sv]
        ort = sum(nl) / len(nl)
        bo = [x / ort for x in nl]
        ad = [i for i in range(len(sv)) if bo[i] < ne and ce[i] > ee]
        er = max(range(len(sv)), key=lambda i: (ce[i] - bo[i], -i))
        return {"glitch_adaylari": ad, "glitch_orani": len(ad) / len(sv), "en_riskli_token": er}
    try:
        sv = [[3.0, 4.0], [0.03, 0.04], [4.0, 3.0]]; ce = [0.5, 2.1, 0.4]
        old = (copy.deepcopy(sv), list(ce))
        c = f(sv, ce, 0.5, 1.5)
        if c != {"glitch_adaylari": [1], "glitch_orani": 1.0 / 3.0, "en_riskli_token": 1} or (sv, ce) != old:
            return False
        if f(sv, [0.5, 1.0, 0.4], 0.5, 1.5)["glitch_adaylari"] != []:
            return False
        if f([[1.0, 0.0], [3.0, 0.0]], [3.0, 0.1], 0.5, 1.0)["glitch_adaylari"] != []:   # bağıl oran tam eşikte (0.5): aday değil (<)
            return False
        if f([[1.0, 0.0], [3.0, 0.0]], [1.0, 0.1], 0.6, 1.0)["glitch_adaylari"] != []:   # entropi tam eşikte (1.0): aday değil (>)
            return False
        if f([[2e-12], [2e-12]], [0.5, 2.0], 0.5, 1.0)["en_riskli_token"] != 1:
            return False
        if f([[1.0, 0.0], [1.0, 0.0]], [2.0, 2.0], 0.5, 1.0)["en_riskli_token"] != 0:
            return False
        rng = random.Random(2903)
        for _ in range(25):
            V = rng.randint(2, 8); D = rng.randint(2, 5)
            s_m = [[rng.uniform(-3, 3) for _ in range(D)] for _ in range(V)]
            c_e = [rng.uniform(0.1, 3.0) for _ in range(V)]
            if f(copy.deepcopy(s_m), list(c_e), 0.6, 1.2) != _r(s_m, c_e, 0.6, 1.2):
                return False
        for bad in (
            ([[], [1.0]], [0.5, 0.5], 0.5, 1.0), ([[1.0], []], [0.5, 0.5], 0.5, 1.0),
            ([[0.0], [0.0]], [0.5, 0.5], 0.5, 1.0), ([[1e-12], [1e-12]], [0.5, 0.5], 0.5, 1.0),
            ([[1.0]], [0.5], 0.5, 1.0), ([[1.0], [2.0]], [0.5], 0.5, 1.0),
            ([[1.0], [2.0]], [-0.1, 0.5], 0.5, 1.0), ([[1.0], [2.0]], [0.5, 0.5], 0.0, 1.0),
            ([[1.0], [2.0]], [0.5, 0.5], 1.2, 1.0), ([[1.0], [2.0]], [0.5, 0.5], 0.5, 0.0),
            ([[1.0], [2.0]], [0.5, 0.5], True, 1.0), ([[1.0], [2.0]], [0.5, 0.5], 0.5, float("nan"))
        ):
            try:
                f(*bad)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sinama3(glitch_tarama_raporu), "norm ve entropi kesişimi, en riskli token ve geçersiz girdi")
for ad, mut in [
    ("or bağlacı", lambda sv, ce, ne, ee: dict(glitch_tarama_raporu(sv, ce, ne, ee), glitch_adaylari=[i for i in range(len(sv)) if ce[i] > ee])),
    ("en riskli hep 0", lambda sv, ce, ne, ee: dict(glitch_tarama_raporu(sv, ce, ne, ee), en_riskli_token=0)),
    ("boş aday listesi", lambda sv, ce, ne, ee: dict(glitch_tarama_raporu(sv, ce, ne, ee), glitch_adaylari=[], glitch_orani=0.0))
]:
    ok(not sinama3(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(glitch_tarama_raporu, _il.import_module('ai_gercek_ai_temel_29').referans_glitch_rapor, ([[1.2, -0.9, 1.5, 0.8], [1.0, 1.4, -1.1, 0.7], [0.04, -0.03, 0.02, 0.01], [-1.3, 1.1, 0.9, -1.0], [0.02, 0.01, -0.02, 0.03]], [0.42, 0.55, 1.92, 0.38, 2.05], 0.45, 1.6), tohum=3054)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def glitch_tarama_raporu(sozluk_vektorleri, cikti_entropileri, norm_esik, entropi_esik):
    if not isinstance(sozluk_vektorleri, list) or len(sozluk_vektorleri) < 2:
        raise ValueError("vektorler")
    V = len(sozluk_vektorleri)
    if not isinstance(cikti_entropileri, list) or len(cikti_entropileri) != V:
        raise ValueError("entropi_boyut")
    boyut = None
    normlar = []
    for v in sozluk_vektorleri:
        if not isinstance(v, list) or not v:
            raise ValueError("vektor_boyut")
        if boyut is not None and len(v) != boyut:
            raise ValueError("farkli_boyut")
        boyut = len(v)
        for x in v:
            if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
                raise ValueError("sayi")
        normlar.append(math.sqrt(sum(x * x for x in v)))
    ort = sum(normlar) / float(V)
    if ort <= 1e-12:
        raise ValueError("sifir_norm")
    for h in cikti_entropileri:
        if isinstance(h, bool) or not isinstance(h, (int, float)) or not math.isfinite(h) or h < 0.0:
            raise ValueError("entropi_deger")
    for v in (norm_esik, entropi_esik):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError("esik_sayi")
    if not 0.0 < norm_esik <= 1.0 or entropi_esik <= 0.0:
        raise ValueError("esik_sinir")
    oranlar = [n / ort for n in normlar]
    adaylar = [i for i in range(V) if oranlar[i] < norm_esik and cikti_entropileri[i] > entropi_esik]
    en_riskli = max(range(V), key=lambda i: (cikti_entropileri[i] - oranlar[i], -i))
    return {
        "glitch_adaylari": adaylar,
        "glitch_orani": len(adaylar) / float(V),
        "en_riskli_token": en_riskli,
    }

if __name__ == "__main__":
    from ai_temel_veri import json_yukle
    v = json_yukle("veri/glitch_bpe.json")
    print("Tarama:", glitch_tarama_raporu(v["sozluk_vektorleri"], v["cikti_entropileri"], v["norm_esik"], v["entropi_esik"]))
```
```hint
Bağıl norm oranlarını hesapla, `oranlar[i] < norm_esik and cikti_entropileri[i] > entropi_esik` filtresini uygula ve `cikti_entropileri[i] - oranlar[i]` farkını maksimize eden indisi seç.
```
:::

::: anlat Hata vitrini · çalışmış yanlış rapor
Yazar, kusurlu başlangıç kodlarını görünür sentetik veriyle gerçekten çalıştırdı ve sonucu `outputs/yeni-ai-temel-29/gorunur-run-1.json` dosyasına kaydetti. `kanonik_olmayan_saldiri` örneği (`["ka", "ra", "kut", "u"]`) için kusurlu kod `kanonik=True`, `ihlal_sayisi=0` verirken; doğru kod `kanonik=False`, `ihlal_sayisi=2`, `ilk_ihlal=["ka", "ra"]` döndürür. Ayrıca sözlük taramasında kusurlu kod `glitch_adaylari=[]` verirken doğru kod `[2, 4]` indisli iki hayalet tokenı yakalar.

Bu kaydedilmiş bir hesaplama çıktısıdır, model yanıtı değildir ve rapor sentetiktir. Bir güvenlik filtresi yalnızca tam `"karakutu"` token ID'sini yasaklıyorsa, `["ka", "ra", "kut", "u"]` dizisini `kanonik=True` sanıp geçirmek neye yol açar? Kendi cümlenle açıkla. Gerçek finaldeki ölçüm ayrıca üretilir; bu sayılar onun yerine konmaz.
:::

::: anlat Gerçek deney: kontrollü glitch tokenı, sonra gerçek SmolLM2'de norm taraması ve BPE ile filtre atlatma
Final iki kısımdır.

**1 · Kontrollü deney (ayrık gömme).** GPU üzerinde 16 tokenlı bir `torch.nn.Embedding` ve ayrı bir LM çıkış katmanı kurar. Eğitim boyunca `[3, 11, 14]` indisli 3 token derlemden hariç tutulur; diğerleri güncellenirken bu 3 token başlangıç gürültüsünde kalır. Senin işlevlerin bu üç tokenı düşük norm + yüksek entropiyle bulmalıdır. Burada doğru cevap bilinir, çünkü glitch'i biz yarattık.

**2 · Gerçek model (SmolLM2-135M, yerel önbellek, indirme yok).** Aynı işlevler gerçek sözlüğün en düşük normlu 150 tokenı ile 150 rastgele kontrol tokenı üzerinde koşar ve gerçek tek-token çıktı entropileri ölçülür. SmolLM2'nin girdi gömmesi ile çıkış katmanı **bağlıdır** (`tie_word_embeddings`); en düşük normlu tokenlar sık geçen isimler çıkar ve "x -> x" kopyalama sınamasında kontrol tokenlarından kötü davranmazlar. Ders, yöntemin hangi mimari varsayıma dayandığını burada ölçerek gösterir. İkinci olarak modelin **gerçek BPE birleştirme kuralları** (48.900 kural) ile 18 güvenlik kelimesi kanonik ve ikişer harfe bölünmüş biçimde kodlanır:
- token kimliği kara listesi kanonik biçimi yakalar, bölünmüşü kaçırır (filtre atlatma);
- senin `bpe_kanonik_mi` işlevinin komşu çift kuralı bölünmüşlerin yalnız bir kısmını yakalar; metni yeniden kodlayıp karşılaştırmak hepsini yakalar;
- SmolLM2-135M kanonik kelimeyi kopyalar, bölünmüşü kopyalayamaz: bu küçük modelde atlatma filtreyi geçse de anlamı da bozar.

**3 · Gerçek glitch tokenları (Qwen2.5-0.5B-Instruct, yerel önbellek).** Bağlı gömmede norm işe yaramadığına göre gerçek modelde eğitilmemiş tokenlar nasıl bulunur? Qwen'in sözlük matrisi 151 936 satırdır ama tokenizer'da 151 665 token vardır: aradaki 271 satıra karşılık gelen hiçbir metin yoktur, yani eğitimde hiç görülmemişlerdir. Land ve Bartolo'nun (2024) yöntemiyle her gerçek tokenın gömmesi (ortalama ve ortak bileşen çıkarıldıktan sonra) bu kullanılmayan satırların ortalamasıyla karşılaştırılır; en benzer 60 token, metinden üretilebilenler arasından aday seçilir. Model her birini "bu dizgeyi aynen tekrar et" isteğiyle dener; 60 rastgele kontrol tokenı da aynı sınamadan geçer. Adayların neredeyse hepsi tekrar edilemez (` ForCanBeConvertedToF`, `$PostalCodesNL`, `Cumhurbaş` gibi tokenizer'a girmiş ama eğitimde neredeyse hiç görülmemiş parçalar), kontrollerin çoğu edilir. Bu tokenlar modelin öngörülemez davrandığı girdilerdir: filtreleri ve değerlendirmeleri şaşırtmak için kullanılabilirler.

Kabul: iki kısımda da üç işlevin bağımsız referansla aynı sonucu vermesi, kontrollü glitch tokenlarının tam yakalanması, gerçek modelde kara listenin kanonik kelimelerin hepsini yakalayıp bölünmüşlerin hiçbirini yakalayamaması, yeniden kodlamanın bölünmüşlerin hepsini yakalaması ve modelin kanonik kelimelerin en az %80'ini kopyalaması; Qwen'de eğitilmemiş token adaylarının tekrar edilememe oranının kontrol tokenlarınınkinden en az 0.3 yüksek olması.

**Kanıt dosyasını oku:** `gercek_model` altındaki `en_dusuk_norm_10`, `kopya_basarisi_dusuk_norm` / `kopya_basarisi_kontrol` ve `parcalida_cift_kurali_yakaladi` / `parcalida_yeniden_kodlama_yakaladi` alanlarına bak. Soru 1: Bağlı gömmede en düşük normlu tokenlar neden sık isimler olabilir; bu, norm göstergesinin hangi varsayımını bozar? Soru 2: Komşu çift kuralı neden `['Ġpa', 'ss', 'wo', 'rd']` gibi bir bölünmeyi kaçırabilir (BPE ara tokenlar üzerinden birleştirir)? Soru 3: Daha büyük bir model bölünmüş kelimeyi okuyabilseydi kara liste tabanlı bir filtre için bu ne anlama gelirdi? Cevabını tezgâhta yorum olarak yaz; otomatik test bu serbest açıklamayı puanlamaz.
:::

::: gorev Gerçek deney · GPU üzerinde eğitilmiş embedding matrisinde glitch token ve BPE denetimi
Önceki üç görevin `gomme_anomali_skoru`, `bpe_kanonik_mi` ve `glitch_tarama_raporu` işlevlerini birleştir. Çalıştır gerçek tabloyu gösterir; Kontrol Et önce üç sözleşmeyi gizli verilerle sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
ortam: gpu
timeout: 180
```
```starter
import ai_lab
import math
def gomme_anomali_skoru(vektorler):
    normlar = [sum(abs(x) for x in v) for v in vektorler]
    ort = sum(normlar) / len(normlar)
    return {"normlar": normlar, "ortalama_norm": ort, "bagil_oranlar": normlar}
def bpe_kanonik_mi(parcalar, birlesme_kurallari):
    return {"kanonik": True, "ihlal_sayisi": 0, "ilk_ihlal": None}
def glitch_tarama_raporu(sozluk_vektorleri, cikti_entropileri, norm_esik, entropi_esik):
    return {"glitch_adaylari": [], "glitch_orani": 0.0, "en_riskli_token": 0}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_29 as D
    D.goster(gomme_anomali_skoru, bpe_kanonik_mi, glitch_tarama_raporu)
```
```test
import ai_lab, math
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('referans_gomme_anomali', 'referans_bpe_kanonik', 'referans_glitch_rapor', 'kanit_yaz', '_yakin'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
gomme_anomali_skoru = need("gomme_anomali_skoru")
bpe_kanonik_mi = need("bpe_kanonik_mi")
glitch_tarama_raporu = need("glitch_tarama_raporu")
def sinama1(f):
    import copy, math, random
    def _r(vk):
        nl = [math.sqrt(sum(x * x for x in r)) for r in vk]; ort = sum(nl) / len(nl)
        return {"normlar": nl, "ortalama_norm": ort, "bagil_oranlar": [x / ort for x in nl]}
    def _y(a, b): return set(a) == {"normlar", "ortalama_norm", "bagil_oranlar"} and abs(a["ortalama_norm"] - b["ortalama_norm"]) < 1e-12 and len(a["normlar"]) == len(b["normlar"]) and all(abs(x - y) < 1e-12 for x, y in zip(a["normlar"], b["normlar"])) and all(abs(x - y) < 1e-12 for x, y in zip(a["bagil_oranlar"], b["bagil_oranlar"]))
    try:
        vk = [[3.0, 4.0], [0.0, 5.0], [0.0, 0.0]]; old = copy.deepcopy(vk)
        if not _y(f(vk), {"normlar": [5.0, 5.0, 0.0], "ortalama_norm": 10.0 / 3.0, "bagil_oranlar": [1.5, 1.5, 0.0]}) or vk != old: return False
        if not _y(f([[2e-12], [2e-12]]), {"normlar": [2e-12, 2e-12], "ortalama_norm": 2e-12, "bagil_oranlar": [1.0, 1.0]}): return False
        rng = random.Random(29)
        for _ in range(25):
            V = rng.randint(2, 8); D = rng.randint(1, 6); mat = [[rng.uniform(-5, 5) for _ in range(D)] for _ in range(V)]
            if not _y(f(copy.deepcopy(mat)), _r(mat)): return False
        for bad in (None, [], [[1.0, 2.0]], [[], []], [[], [1.0]], [[1.0], []], [[1.0], [1.0, 2.0]], [[0.0, 0.0], [0.0, 0.0]], [[1e-12], [1e-12]], [[True, 1.0], [1.0, 1.0]], [[float("nan")], [1.0]], [[float("inf")], [1.0]], [("1.0",), ("2.0",)]):
            try: f(bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama1(gomme_anomali_skoru), "L2 normu, ortalama norm, bağıl oranlar ve sıfır/geçersiz girdi")
for ad, mut in [("L1 normu", lambda vk: {"normlar": [sum(abs(x) for x in r) for r in vk], "ortalama_norm": 1.0, "bagil_oranlar": [1.0] * len(vk)}), ("karekök yok", lambda vk: dict(gomme_anomali_skoru(vk), normlar=[sum(x * x for x in r) for r in vk])), ("bağıl oran sabit 1", lambda vk: dict(gomme_anomali_skoru(vk), bagil_oranlar=[1.0] * len(vk)))]:
    kontrol(not sinama1(mut), "mutant reddedildi: " + ad)
def sinama2(f):
    import copy
    try:
        kr = [["b", "c"], ["a", "b"], ["c", "d"]]; p1 = ["a", "b", "c"]; old = (list(p1), copy.deepcopy(kr))
        if f(p1, kr) != {"kanonik": False, "ihlal_sayisi": 2, "ilk_ihlal": ["b", "c"]} or (p1, kr) != old: return False
        if f(["ab", "cd"], kr) != {"kanonik": True, "ihlal_sayisi": 0, "ilk_ihlal": None}: return False
        for bad in ((None, kr), ([], kr), ([""], kr), ([123], kr), (("a", "b"), kr), (["a", "b"], None), (["a", "b"], "ab"), (["a", "b"], [["a"]]), (["a", "b"], [["a", "b", "c"]]), (["a", "b"], [["", "b"]]), (["a", "b"], [("a", "b")]), (["a", "b"], [[1, "b"]])):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama2(bpe_kanonik_mi), "komşu çift ihlali, kural öncelik sırası ve geçersiz girdi")
for ad, mut in [("dizi sırasına göre ilk ihlal", lambda p, kr: dict(bpe_kanonik_mi(p, kr), ilk_ihlal=next(([p[i], p[i+1]] for i in range(len(p)-1) if [p[i], p[i+1]] in kr), None))), ("hep kanonik", lambda p, kr: {"kanonik": True, "ihlal_sayisi": 0, "ilk_ihlal": None}), ("ihlal sayısı sabit 1", lambda p, kr: dict(bpe_kanonik_mi(p, kr), ihlal_sayisi=1 if not bpe_kanonik_mi(p, kr)["kanonik"] else 0))]:
    kontrol(not sinama2(mut), "mutant reddedildi: " + ad)
def sinama3(f):
    import copy, math, random
    def _r(sv, ce, ne, ee):
        nl = [math.sqrt(sum(x * x for x in v)) for v in sv]; ort = sum(nl) / len(nl); bo = [x / ort for x in nl]
        ad = [i for i in range(len(sv)) if bo[i] < ne and ce[i] > ee]; er = max(range(len(sv)), key=lambda i: (ce[i] - bo[i], -i))
        return {"glitch_adaylari": ad, "glitch_orani": len(ad) / len(sv), "en_riskli_token": er}
    try:
        sv = [[3.0, 4.0], [0.03, 0.04], [4.0, 3.0]]; ce = [0.5, 2.1, 0.4]; old = (copy.deepcopy(sv), list(ce))
        if f(sv, ce, 0.5, 1.5) != {"glitch_adaylari": [1], "glitch_orani": 1.0 / 3.0, "en_riskli_token": 1} or (sv, ce) != old: return False
        if f([[1.0, 0.0], [3.0, 0.0]], [3.0, 0.1], 0.5, 1.0)["glitch_adaylari"] != []: return False
        if f([[2e-12], [2e-12]], [0.5, 2.0], 0.5, 1.0)["en_riskli_token"] != 1: return False
        if f([[1.0, 0.0], [1.0, 0.0]], [2.0, 2.0], 0.5, 1.0)["en_riskli_token"] != 0: return False
        rng = random.Random(2903)
        for _ in range(25):
            V = rng.randint(2, 8); D = rng.randint(2, 5); s_m = [[rng.uniform(-3, 3) for _ in range(D)] for _ in range(V)]; c_e = [rng.uniform(0.1, 3.0) for _ in range(V)]
            if f(copy.deepcopy(s_m), list(c_e), 0.6, 1.2) != _r(s_m, c_e, 0.6, 1.2): return False
        for bad in (([[], [1.0]], [0.5, 0.5], 0.5, 1.0), ([[0.0], [0.0]], [0.5, 0.5], 0.5, 1.0), ([[1e-12], [1e-12]], [0.5, 0.5], 0.5, 1.0), ([[1.0]], [0.5], 0.5, 1.0), ([[1.0], [2.0]], [0.5], 0.5, 1.0), ([[1.0], [2.0]], [-0.1, 0.5], 0.5, 1.0), ([[1.0], [2.0]], [0.5, 0.5], 0.0, 1.0), ([[1.0], [2.0]], [0.5, 0.5], 1.2, 1.0), ([[1.0], [2.0]], [0.5, 0.5], 0.5, 0.0), ([[1.0], [2.0]], [0.5, 0.5], True, 1.0), ([[1.0], [2.0]], [0.5, 0.5], 0.5, float("nan"))):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama3(glitch_tarama_raporu), "norm ve entropi kesişimi, en riskli token ve geçersiz girdi")
for ad, mut in [("or bağlacı", lambda sv, ce, ne, ee: dict(glitch_tarama_raporu(sv, ce, ne, ee), glitch_adaylari=[i for i in range(len(sv)) if ce[i] > ee])), ("en riskli hep 0", lambda sv, ce, ne, ee: dict(glitch_tarama_raporu(sv, ce, ne, ee), en_riskli_token=0)), ("boş aday listesi", lambda sv, ce, ne, ee: dict(glitch_tarama_raporu(sv, ce, ne, ee), glitch_adaylari=[], glitch_orani=0.0))]:
    kontrol(not sinama3(mut), "mutant reddedildi: " + ad)
# farksal tarama (final)
import importlib as _il
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_R = _il.import_module('sandbox.ai_gercek_ai_temel_29')
for _ad, _ref, _taban, _toh in (
    ('gomme_anomali_skoru', 'referans_gomme_anomali', ([[1.2, -0.9, 1.5, 0.8], [1.0, 1.4, -1.1, 0.7], [0.04, -0.03, 0.02, 0.01], [-1.3, 1.1, 0.9, -1.0], [0.02, 0.01, -0.02, 0.03]],), 3480),
    ('bpe_kanonik_mi', 'referans_bpe_kanonik', (['karakut', 'u'], [['ka', 'ra'], ['kara', 'kut'], ['kut', 'u']]), 2918),
    ('glitch_tarama_raporu', 'referans_glitch_rapor', ([[1.2, -0.9, 1.5, 0.8], [1.0, 1.4, -1.1, 0.7], [0.04, -0.03, 0.02, 0.01], [-1.3, 1.1, 0.9, -1.0], [0.02, 0.01, -0.02, 0.03]], [0.42, 0.55, 1.92, 0.38, 2.05], 0.45, 1.6), 3576),
):
    _t, _g = _ff(need(_ad), getattr(_R, _ref), _taban, tohum=_toh)
    kontrol(_t, "farksal tarama (" + _ad + "): bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
if not all(checks): stop()
from sandbox import ai_gercek_ai_temel_29 as D
try: r = D.deney(gomme_anomali_skoru, bpe_kanonik_mi, glitch_tarama_raporu)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r["anomali_ayni"], "16 gerçek gömme vektöründe anomali skoru bağımsız referansla aynı")
kontrol(r["bpe_ayni"], "BPE kanoniklik denetimi referansla aynı")
kontrol(r["tarama_ayni"], "glitch tarama raporu referansla aynı")
kontrol(r["glitch_tam_yakalandi"], "eğitimsiz 3 glitch tokenın tamamı yanlış pozitifsiz yakalandı")
g = r["gercek_model"]
kontrol(g["anomali_ayni"] and g["tarama_ayni"], "gerçek SmolLM2 gömmelerinde (300 token) anomali skoru ve tarama raporu referansla aynı")
kontrol(g["bpe_ayni"], "gerçek BPE birleştirme kurallarıyla kanoniklik denetimi referansla aynı")
kontrol(g["bpe_kelime_sayisi"] >= 15 and g["kanonikte_cift_kurali_ihlali"] == 0, "tokenizer'ın kanonik çıktısında hiçbir komşu çift birleştirme kuralı ihlal etmiyor")
kontrol(g["kara_liste_kanonik_yakaladi"] == g["bpe_kelime_sayisi"] and g["kara_liste_parcali_yakaladi"] == 0, "token kimliği kara listesi kanonik kelimelerin hepsini yakaladı, bölünmüşlerin hiçbirini yakalayamadı")
kontrol(g["parcalida_yeniden_kodlama_yakaladi"] == g["bpe_kelime_sayisi"], "yeniden kodlama karşılaştırması bölünmüş kodlamaların hepsini yakaladı")
kontrol(g["model_kanonik_kopyaladi"] >= 0.8 * g["bpe_kelime_sayisi"], "gerçek model kanonik kelimelerin en az %80'ini kopyaladı (ölçüm geçerli)")
kontrol(r["gercek_glitch_bulundu"], "Qwen2.5'te kullanılmayan sözlük satırlarına benzeyen gerçek tokenlar kontrol tokenlarından çok daha sık tekrar edilemedi (gerçek glitch tokenları)")
ai_lab.kanit_yaz("ai-temel-29-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-temel-29", "deney": r})
```
```solution
import ai_lab
import math
def gomme_anomali_skoru(vektorler):
    if not isinstance(vektorler, list) or len(vektorler) < 2:
        raise ValueError("vektorler")
    boyut = None
    normlar = []
    for v in vektorler:
        if not isinstance(v, list) or not v:
            raise ValueError("vektor_boyut")
        if boyut is not None and len(v) != boyut:
            raise ValueError("farkli_boyut")
        boyut = len(v)
        for x in v:
            if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
                raise ValueError("sayi")
        normlar.append(math.sqrt(sum(x * x for x in v)))
    ort = sum(normlar) / float(len(normlar))
    if ort <= 1e-12:
        raise ValueError("sifir_norm")
    return {
        "normlar": normlar,
        "ortalama_norm": ort,
        "bagil_oranlar": [n / ort for n in normlar],
    }
def bpe_kanonik_mi(parcalar, birlesme_kurallari):
    if not isinstance(parcalar, list) or not parcalar:
        raise ValueError("parcalar")
    for p in parcalar:
        if not isinstance(p, str) or not p:
            raise ValueError("parca_str")
    if not isinstance(birlesme_kurallari, list):
        raise ValueError("kurallar")
    kural_listesi = []
    for k in birlesme_kurallari:
        if not isinstance(k, list) or len(k) != 2 or not isinstance(k[0], str) or not isinstance(k[1], str) or not k[0] or not k[1]:
            raise ValueError("kural_sema")
        kural_listesi.append((k[0], k[1]))
    kural_kumesi = set(kural_listesi)
    ciftler = [(parcalar[i], parcalar[i + 1]) for i in range(len(parcalar) - 1)]
    ihlal_sayisi = sum(1 for c in ciftler if c in kural_kumesi)
    ilk_ihlal = None
    for kural in kural_listesi:
        if kural in ciftler:
            ilk_ihlal = [kural[0], kural[1]]
            break
    return {
        "kanonik": bool(ihlal_sayisi == 0),
        "ihlal_sayisi": ihlal_sayisi,
        "ilk_ihlal": ilk_ihlal,
    }
def glitch_tarama_raporu(sozluk_vektorleri, cikti_entropileri, norm_esik, entropi_esik):
    anom = gomme_anomali_skoru(sozluk_vektorleri)
    V = len(sozluk_vektorleri)
    if not isinstance(cikti_entropileri, list) or len(cikti_entropileri) != V:
        raise ValueError("entropi_boyut")
    for h in cikti_entropileri:
        if isinstance(h, bool) or not isinstance(h, (int, float)) or not math.isfinite(h) or h < 0.0:
            raise ValueError("entropi_deger")
    for v in (norm_esik, entropi_esik):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError("esik_sayi")
    if not 0.0 < norm_esik <= 1.0 or entropi_esik <= 0.0:
        raise ValueError("esik_sinir")
    oranlar = anom["bagil_oranlar"]
    adaylar = [i for i in range(V) if oranlar[i] < norm_esik and cikti_entropileri[i] > entropi_esik]
    en_riskli = max(range(V), key=lambda i: (cikti_entropileri[i] - oranlar[i], -i))
    return {
        "glitch_adaylari": adaylar,
        "glitch_orani": len(adaylar) / float(V),
        "en_riskli_token": en_riskli,
    }
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_29 as D
    D.goster(gomme_anomali_skoru, bpe_kanonik_mi, glitch_tarama_raporu)
```
```hint
Üç işlevi birleştir; `glitch_tarama_raporu` içinde `gomme_anomali_skoru` işlevini doğrudan çağırabilirsin.
```
:::

::: anlat Sınır
Bu ders L2 normu ve tek adımlı entropiyle `glitch token` tespitini kontrollü ayrık (untied) gömmede gösterir ve aynı göstergenin bağlı gömmeli gerçek SmolLM2-135M'de tek başına yetmediğini ölçer; gerçek BPE kurallarıyla kanonik olmayan bölünmenin token kimliği kara listesini atlattığını gösterir. Orta katman dikkat çökmesiyle tetiklenen çok tokenlı glitch dizilerini, bayt düzeyindeki UTF-8 bozulmalarını ve bölünmüş kelimeyi okuyabilen büyük modellerdeki filtre atlatma başarısını kapsamaz.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Tokenizer–eğitim uyumsuzluğu (`Glitch Token`) (30 sn).** "Tokenizer sözlüğüne giren bir alt-sözcük ön-eğitim derleminden filtrelenirse ağırlık vektörü güncellenmez; küçük başlangıç L2 normunda asılı kalır ve LM başlığında tekdüze dağılıma yakın yüksek entropi üretir."
2. **Çift eşikli anomali taraması (35 sn).** "Yalnız düşük L2 normu yeterli değildir; bağıl norm küçüklüğü ile ileri geçiş çıktı entropisi yüksekliği birlikte arandığında eğitimsiz `glitch` adayları düşük yanlış pozitif ile yakalanır."
3. **Kanonik olmayan `BPE` kaçışı (30 sn).** "Doğrudan token ID kabul eden uçlarda birleşmesi gereken komşu çiftlerin ayrı bırakılması (`non-canonical BPE`), tam token kimliğine bakan güvenlik filtrelerini atlatabilir."
4. **Soru (25 sn).** "Token ID listesi kabul eden bir sunucu API'sinde kanonik `BPE` zorlamasını en ucuz ve kesin hangi yeniden-kodlama (`decode -> encode`) denetimiyle uygularsın?"
:::
