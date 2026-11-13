---
id: ai-temel-01
title: "Tokenizasyon: Metinden Modele Giren Birimler"
summary: Sentetik BPE birleştirmelerini öncelik sırasıyla uygula; kelime sınırlarını koru ve metin ile token filtrelerinin farklarını ölç.
esleme: ai-temel-02, ai-temel-13, ai-savunma-02
timeout: 45
---

::: anlat Gerçek tokenizer'ı bil, sentetik BPE'yi ayırt et
Bu dersin ilk üç görevi küçük ve sentetik bir BPE kullanır; son görev bilgisayarda kurulu gerçek SmolLM2 tokenizer'ını çalıştırır. İkisi aynı fikre dayanır, ama ayrıntıları farklıdır:

| | Gerçek tokenizer (SmolLM2, GPT-2 tarzı byte düzeyi BPE) | Bu dersteki sentetik BPE | Ne söyleyemez? |
|---|---|---|---|
| Başlangıç birimi | UTF-8 baytları; her bayt bir başlangıç sembolüdür | ASCII küçük harfler | Sentetik sürüm Unicode ve emoji bölünmesini göstermez |
| Kelime sınırı | Önceki boşluk tokena katılır ve `Ġ` (U+0120) ile gösterilir: `Ġsifre` | Kelime sonu `</w>` ile işaretlenir: `sifre</w>` | Aynı kelime iki tokenizer'da farklı sınırlarla bölünür |
| Kurallar | `merges.txt`: öncelik sırasıyla on binlerce birleştirme | `veri/kurallar.json`: birkaç kural | Kuralların sayısı ve sırası modele ve sürüme bağlıdır |
| Çıktı | Tamsayı token kimlikleri ve karakter aralıkları | Sembol listeleri | Sembol listesi kimlik numarası değildir |

> [!NOT]
> Görevlerde örnek dosyalar çalışma klasörünün `veri/` altına kopyalanır: `kurallar.json`, `ornekler.json` ve gerçek `merges.txt` biçimini gösteren `merges_ornek.txt`. Bunları okuyabilir, kodunda değiştirerek deneyebilirsin. Kontrol bu dosyaları değil, görmediğin ayrı verileri kullanır; örneklere göre sabit cevap yazmak işe yaramaz.
>
> Dosyalar her Çalıştır/Kontrol Et adımında kaynaktan yeniden kopyalanır; `veri/` altında yaptığın değişiklik bir sonraki çalıştırmada sıfırlanır, **kalıcılık yoktur**. Ekranda ayrı bir dosya görüntüleyici de yoktur: içeriği görmek için kodunda `json_yukle(...)` ile oku ve `print` et ya da yüklediğin sözlüğü kodda değiştirerek dene.
:::

::: anlat BPE karakterleri öncelikli kurallarla birleştirir
Byte Pair Encoding yaklaşımında metin küçük sembollere ayrılır ve sıralı birleştirme kuralları tekrar uygulanır. Her adımda önceliği en yüksek, yani listede daha önce gelen uygulanabilir kural seçilir. Seçilen kural soldan sağa ve çakışmayan eşleşmelerle uygulanır; birleştirme token sayısını azalttığı için işlem sonlanır.

İlk üç görevde Hugging Face tokenizers çalıştırılmaz ve model indirilmez; küçük, deterministik bir sentetik BPE sürümü kullanılır. Gerçek tokenizer yalnız son görevde, kurulu yerel modelden okunur. Semboller ASCII küçük harflerden veya kelime sonunu gösteren `</w>` işaretinden oluşur. Amaç gerçek tokenizerın bütün özelliklerini kopyalamak değil, birleştirme önceliğini ve token sınırlarını görünür kılmaktır.
:::

::: anlat Metin eşleşmesi ile token eşleşmesi farklıdır
Kelime sonu işareti, ayrı kelimelerin birleştirme sırasında birbirine karışmasını önler. Her kelime kendi sembol dizisinde işlenir ve sonuçlar sırayla birleştirilir. Böylece bir kelimenin son karakteriyle sonraki kelimenin ilk karakteri arasında kural çalışmaz.

Güvenlik filtresi ham metinde alt string ararsa başka, üretilen tokenların tamamını karşılaştırırsa başka sonuç verebilir. Örneğin ham metindeki `abc` alt stringi tek bir `abc` tokenına karşılık gelmeyebilir; tersine `ab</w>` tokenı ham metinde aynen bulunmaz. Bu nedenle token sınırları filtre kararlarını etkiler; tek filtre biçimi bütün kaçışları kapsamaz.
:::

::: tahmin Kural önceliğini ve filtre farkını tahmin et
Üç çıktı satırını yaz:

```python
def uygula(s, sol, sag):
    yeni, i = [], 0
    while i < len(s):
        if s[i:i + 2] == [sol, sag]:
            yeni.append(sol + sag)
            i += 2
        else:
            yeni.append(s[i])
            i += 1
    return yeni

s = ["a", "b", "c", "</w>"]
for sol, sag in [("b", "c"), ("a", "b"), ("a", "bc")]:
    s = uygula(s, sol, sag)
print(s)
print("ab" in "x abc", "ab" in s)
print(len(s), len("abc"))
```

???

```cikti
['abc', '</w>']
True False
2 3
```

`(b, c)` kuralı önce geldiği için `ab` tokenı hiç oluşmaz; `a` doğrudan `bc` ile birleşir. Ham metinde `ab` alt stringi vardır, token listesinde yoktur: filtre hangi düzeyde arıyorsa sonucu ona göre değişir. Üç karakterlik kelime iki token olur; token sayısı karakter sayısı değildir.
:::

::: gorev 1 · Öncelikli sentetik BPE birleştirmesini uygula
`bpe_birlestir(semboller, kurallar)` işlevini yaz. Semboller 1–64 öğeli listedir; her sembol `[a-z]+`, `[a-z]+</w>` veya `</w>` biçiminde, en çok 32 karakterlik stringdir. Kurallar 1–64 öğeli listedir ve her kural tam olarak `sol`, `sag`, `yeni` anahtarlı sözlüktür. Bu üç değer de aynı sembol biçimine uyar. `(sol, sag)` çiftleri yinelenemez. Geçersiz veride `ValueError` yükselt.

Kural listesinin sırası önceliktir. Her turda sembol dizisinde uygulanabilen en küçük indeksli kuralı bul ve o kuralın bütün çakışmayan eşleşmelerini soldan sağa uygula. Hiçbir kural uygulanamıyorsa dur. Yeni liste döndür; sembol ve kural girdilerini değiştirme.

```starter
from ai_temel_veri import json_yukle
kurallar = json_yukle("veri/kurallar.json")

def bpe_birlestir(semboller, kurallar):
    sonuc = list(semboller)
    for kural in kurallar:
        yeni, i = [], 0
        while i < len(sonuc):
            if sonuc[i:i + 2] == [kural["sol"], kural["sag"]]:
                yeni.append(kural["yeni"])
                i += 2
            else:
                yeni.append(sonuc[i])
                i += 1
        sonuc = yeni
    return sonuc

for ornek in json_yukle("veri/ornekler.json"):
    for kelime in ornek["metin"].split(" "):
        print(kelime, "→", bpe_birlestir(list(kelime) + ["</w>"], kurallar))
```
```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-01")
```

```test
import copy
S = ["a", "b", "a", "b", "</w>"]
R = [{"sol": "a", "sag": "b", "yeni": "ab"}, {"sol": "ab", "sag": "</w>", "yeni": "ab</w>"}, {"sol": "b", "sag": "c", "yeni": "bc"}]
def sozlesme(fn):
    try:
        s_once = copy.deepcopy(S)
        r_once = copy.deepcopy(R)
        if fn(S, R) != ["ab", "ab</w>"] or S != s_once or R != r_once:
            return False
        if fn(["a", "b", "c", "</w>"], R) != ["ab", "c", "</w>"]:
            return False
        oncelik = [{"sol": "a", "sag": "b", "yeni": "ab"}, {"sol": "b", "sag": "c", "yeni": "bc"}]
        if fn(["a", "b", "c"], oncelik) != ["ab", "c"] or fn(["a", "b", "c"], list(reversed(oncelik))) != ["a", "bc"]:
            return False
        if fn(["a", "a", "a"], [{"sol": "a", "sag": "a", "yeni": "aa"}]) != ["aa", "a"] or fn(["a", "b", "c", "b"], [{"sol": "a", "sag": "b", "yeni": "ab"}]) != ["ab", "c", "b"]:
            return False
        if fn(["a"], [{"sol": "b", "sag": "c", "yeni": "bc"}]) != ["a"]:
            return False
        uzun = "a" * 32
        if fn([uzun], [{"sol": "b", "sag": "c", "yeni": "bc"}]) != [uzun] or fn(["a"] * 64, [{"sol": "b", "sag": "c", "yeni": "bc"}]) != ["a"] * 64:
            return False
        k64 = [{"sol": "a" * (i % 20 + 1), "sag": "b" * (i // 20 + 1), "yeni": "c"} for i in range(64)]
        k65 = k64 + [{"sol": "a" * 21, "sag": "bbbb", "yeni": "c"}]
        if fn(["c"], k64) != ["c"]:
            return False
        for args in [
            (None, R), ({}, R), ([], R), ([None], R), ([""], R), (["A"], R), (["a" * 33], R), (["a"] * 65, R),
            (S, None), (S, {}), (S, []), (S, [None]), (S, [dict(R[0], ek=1)]), (S, [{"sol": "a", "sag": "b"}]),
            (S, [{"sol": "A", "sag": "b", "yeni": "ab"}]), (S, [{"sol": "a", "sag": None, "yeni": "ab"}]), (S, [{"sol": "a", "sag": "b", "yeni": "a" * 33}]),
            (S, [R[0], R[0]]), (S, k65),
        ]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(bpe_birlestir), "BPE önceliği, soldan sağa birleştirme ve şema korunmalı")
def m_kural(semboller, kurallar):
    return bpe_birlestir(semboller, list(reversed(kurallar)))
def m_sembol(semboller, kurallar):
    return bpe_birlestir(semboller[:1], kurallar)
def m_yeni(semboller, kurallar):
    degisen = [dict(x, yeni="degisti") for x in kurallar]
    return bpe_birlestir(semboller, degisen)
def m_cift(semboller, kurallar):
    return bpe_birlestir(semboller, kurallar + kurallar)
for ad, mutant in [("önceliği bozan", m_kural), ("sembolleri silen", m_sembol), ("yeni tokenı değiştiren", m_yeni), ("kuralları yineleyen", m_cift)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def bpe_birlestir(semboller, kurallar):
    import re
    def gecerli_sembol(deger):
        return isinstance(deger, str) and len(deger) <= 32 and re.fullmatch(r"(?:[a-z]+(?:</w>)?|</w>)", deger) is not None
    if not isinstance(semboller, list) or not 1 <= len(semboller) <= 64:
        raise ValueError("sembol listesi geçersiz")
    if any(not gecerli_sembol(x) for x in semboller):
        raise ValueError("sembol geçersiz")
    if not isinstance(kurallar, list) or not 1 <= len(kurallar) <= 64:
        raise ValueError("kural listesi geçersiz")
    ciftler = set()
    for kural in kurallar:
        if not isinstance(kural, dict) or set(kural) != {"sol", "sag", "yeni"}:
            raise ValueError("kural şeması geçersiz")
        if any(not gecerli_sembol(kural[a]) for a in ("sol", "sag", "yeni")):
            raise ValueError("kural sembolü geçersiz")
        cift = (kural["sol"], kural["sag"])
        if cift in ciftler:
            raise ValueError("kural çifti yinelenemez")
        ciftler.add(cift)
    sonuc = list(semboller)
    while True:
        secim = None
        for indeks, kural in enumerate(kurallar):
            if any(sonuc[i] == kural["sol"] and sonuc[i + 1] == kural["sag"] for i in range(len(sonuc) - 1)):
                secim = (indeks, kural)
                break
        if secim is None:
            return sonuc
        _, kural = secim
        yeni = []
        i = 0
        while i < len(sonuc):
            if i + 1 < len(sonuc) and sonuc[i] == kural["sol"] and sonuc[i + 1] == kural["sag"]:
                yeni.append(kural["yeni"])
                i += 2
            else:
                yeni.append(sonuc[i])
                i += 1
        sonuc = yeni
```

```hint
Her turda kuralları baştan ve öncelik sırasıyla tara. Seçilen çifti soldan sağa birleştirirken eşleşme sonrasında iki sembol ilerle.
```
:::

::: gorev 2 · Kelime sınırlarını koruyarak metni tokenlaştır
`bpe_tokenize(metin, kurallar)` işlevini yaz. Metin 1–64 karakterlik, en çok sekiz ASCII küçük harf kelimesinden oluşan stringdir. Kelimeler tek boşlukla ayrılır; başta/sonda boşluk, ardışık boşluk veya başka karakter bulunamaz. Kurallar ilk görevdeki şemaya uyar. Geçersiz veride `ValueError` yükselt.

Her kelimeyi karakterlerine ayır ve sonuna `</w>` ekle. İlk görevdeki öncelikli BPE algoritmasını her kelimeye ayrı uygula, sonra çıktıları kelime sırasıyla tek listede birleştir. Kelimeler arasında birleştirme yapma. Girdileri değiştirme.

```starter
from ai_temel_veri import json_yukle
kurallar = json_yukle("veri/kurallar.json")

def bpe_tokenize(metin, kurallar):
    semboller = list(metin.replace(" ", "")) + ["</w>"]
    degisti = True
    while degisti:
        degisti = False
        for kural in kurallar:
            for i in range(len(semboller) - 1):
                if semboller[i:i + 2] == [kural["sol"], kural["sag"]]:
                    semboller[i:i + 2] = [kural["yeni"]]
                    degisti = True
                    break
            if degisti:
                break
    return semboller

for ornek in json_yukle("veri/ornekler.json"):
    print(ornek["metin"], "→", bpe_tokenize(ornek["metin"], kurallar))
```
```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-01")
```

```test
import copy
R = [{"sol": "a", "sag": "b", "yeni": "ab"}, {"sol": "ab", "sag": "</w>", "yeni": "ab</w>"}, {"sol": "b", "sag": "c", "yeni": "bc"}]
def sozlesme(fn):
    try:
        once = copy.deepcopy(R)
        if fn("ab abc", R) != ["ab</w>", "ab", "c", "</w>"] or R != once:
            return False
        if fn("a a", R) != ["a", "</w>", "a", "</w>"]:
            return False
        if fn("abc", R) != ["ab", "c", "</w>"] or fn("ab ab", R) != ["ab</w>", "ab</w>"]:
            return False
        sinir = [{"sol": "a" * 32, "sag": "b", "yeni": "ab"}]
        if fn("a" * 64, sinir) != list("a" * 64) + ["</w>"]:
            return False
        sekiz = " ".join(["a"] * 8)
        if len(fn(sekiz, R)) != 16 or fn("a", R) != ["a", "</w>"]:
            return False
        k64 = [{"sol": "a" * (i % 20 + 1), "sag": "b" * (i // 20 + 1), "yeni": "c"} for i in range(64)]
        k65 = k64 + [{"sol": "a" * 21, "sag": "bbbb", "yeni": "c"}]
        if fn("a", k64) != ["a", "</w>"] or fn("a", [{"sol": "</w>", "sag": "a", "yeni": "a"}]) != ["a", "</w>"]:
            return False
        for args in [
            (None, R), (1, R), ("", R), (" a", R), ("a ", R), ("a  b", R), ("A", R), ("a-b", R), ("a\nb", R), ("a" * 65, R), (" ".join(["a"] * 9), R),
            ("ab", None), ("ab", []), ("ab", [None]), ("ab", [dict(R[0], ek=1)]), ("ab", [{"sol": "A", "sag": "b", "yeni": "ab"}]),
            ("ab", [{"sol": 1, "sag": "b", "yeni": "ab"}]), ("ab", [{"sol": "a", "sag": "b", "yeni": "a" * 33}]), ("ab", [R[0], R[0]]), ("ab", k65),
        ]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(bpe_tokenize), "kelime sınırları, metin şeması ve BPE çıktısı korunmalı")
def m_metin(metin, kurallar):
    return bpe_tokenize(metin.replace(" ", ""), kurallar)
def m_kural(metin, kurallar):
    return bpe_tokenize(metin, list(reversed(kurallar)))
def m_son(metin, kurallar):
    return bpe_tokenize(metin, [dict(x, sag="x" if x["sag"] == "</w>" else x["sag"]) for x in kurallar])
def m_cift(metin, kurallar):
    return bpe_tokenize(metin, kurallar + kurallar)
for ad, mutant in [("kelimeyi değiştiren", m_metin), ("önceliği bozan", m_kural), ("kelime sonunu silen", m_son), ("kuralları yineleyen", m_cift)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def bpe_tokenize(metin, kurallar):
    import re
    def gecerli_sembol(deger):
        return isinstance(deger, str) and len(deger) <= 32 and re.fullmatch(r"(?:[a-z]+(?:</w>)?|</w>)", deger) is not None
    if not isinstance(metin, str) or not 1 <= len(metin) <= 64 or not re.fullmatch(r"[a-z]+(?: [a-z]+){0,7}", metin):
        raise ValueError("metin geçersiz")
    if not isinstance(kurallar, list) or not 1 <= len(kurallar) <= 64:
        raise ValueError("kural listesi geçersiz")
    ciftler = set()
    for kural in kurallar:
        if not isinstance(kural, dict) or set(kural) != {"sol", "sag", "yeni"}:
            raise ValueError("kural şeması geçersiz")
        if any(not gecerli_sembol(kural[a]) for a in ("sol", "sag", "yeni")):
            raise ValueError("kural sembolü geçersiz")
        cift = (kural["sol"], kural["sag"])
        if cift in ciftler:
            raise ValueError("kural çifti yinelenemez")
        ciftler.add(cift)
    sonuc = []
    for kelime in metin.split(" "):
        semboller = list(kelime) + ["</w>"]
        while True:
            secilen = None
            for kural in kurallar:
                if any(semboller[i] == kural["sol"] and semboller[i + 1] == kural["sag"] for i in range(len(semboller) - 1)):
                    secilen = kural
                    break
            if secilen is None:
                break
            yeni = []
            i = 0
            while i < len(semboller):
                if semboller[i:i + 2] == [secilen["sol"], secilen["sag"]]:
                    yeni.append(secilen["yeni"])
                    i += 2
                else:
                    yeni.append(semboller[i])
                    i += 1
            semboller = yeni
        sonuc.extend(semboller)
    return sonuc
```

```hint
Metni önce kelimelere ayır. Her kelimenin sembol listesine `</w>` ekleyip BPE döngüsünü yalnız o liste üzerinde çalıştır.
```
:::

::: gorev 3 · Ham metin ve token filtrelerinin farkını raporla
`token_filtre_raporu(metin, kurallar, yasaklar)` işlevini yaz. Metin ve kurallar ikinci görevdeki kurallara uyar. Yasaklar 1–32 öğeli, yinelenmeyen stringlerden oluşan listedir; her yasak `[a-z]+`, `[a-z]+</w>` veya `</w>` biçiminde ve en çok 32 karakterdir. Geçersiz veride `ValueError` yükselt.

İkinci görevdeki tokenları üret. `metin_eslesmeleri`, yasağın ham metinde alt string olarak bulunduğu; `token_eslesmeleri`, yasağın üretilen tokenlardan birine tam eşit olduğu yasakları orijinal yasak sırasıyla içerir. `farklar`, iki listeden yalnız birinde bulunan yasakları yine orijinal sırayla içerir. `{"tokenler":T,"metin_eslesmeleri":M,"token_eslesmeleri":E,"farklar":F}` döndür ve girdileri değiştirme.

```starter
from ai_temel_veri import json_yukle
kurallar = json_yukle("veri/kurallar.json")

def token_filtre_raporu(metin, kurallar, yasaklar):
    tokenler = []
    for kelime in metin.split(" "):
        semboller = list(kelime) + ["</w>"]
        degisti = True
        while degisti:
            degisti = False
            for kural in kurallar:
                for i in range(len(semboller) - 1):
                    if semboller[i:i + 2] == [kural["sol"], kural["sag"]]:
                        semboller[i:i + 2] = [kural["yeni"]]
                        degisti = True
                        break
                if degisti:
                    break
        tokenler.extend(semboller)
    birlesik = "".join(tokenler)
    metin_e = [y for y in yasaklar if y in metin]
    token_e = [y for y in yasaklar if y in birlesik]
    return {"tokenler": tokenler, "metin_eslesmeleri": metin_e, "token_eslesmeleri": token_e,
            "farklar": [y for y in yasaklar if (y in metin_e) != (y in token_e)]}

for ornek in json_yukle("veri/ornekler.json"):
    print(token_filtre_raporu(ornek["metin"], kurallar, ornek["yasaklar"]))
```
```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-01")
```

```test
import copy
R = [{"sol": "a", "sag": "b", "yeni": "ab"}, {"sol": "ab", "sag": "</w>", "yeni": "ab</w>"}, {"sol": "b", "sag": "c", "yeni": "bc"}]
Y = ["ab</w>", "ab", "c", "abc", "z"]
def sozlesme(fn):
    try:
        once_r = copy.deepcopy(R)
        once_y = copy.deepcopy(Y)
        sonuc = fn("ab abc", R, Y)
        if once_r != R or once_y != Y or sonuc != {"tokenler": ["ab</w>", "ab", "c", "</w>"], "metin_eslesmeleri": ["ab", "c", "abc"], "token_eslesmeleri": ["ab</w>", "ab", "c"], "farklar": ["ab</w>", "abc"]}:
            return False
        if fn("a", R, ["a", "aa", "</w>"])["farklar"] != ["</w>"]:
            return False
        if fn("ab", R, ["ab</w>", "ab"])["metin_eslesmeleri"] != ["ab"]:
            return False
        if fn("abc", R, ["abc", "ab</w>"])["farklar"] != ["abc"]:
            return False
        uzun = "a" * 32
        if fn("a", R, [uzun])["token_eslesmeleri"] != [] or len(fn("a", R, ["a"] * 1)["tokenler"]) != 2:
            return False
        k64 = [{"sol": "a" * (i % 20 + 1), "sag": "b" * (i // 20 + 1), "yeni": "c"} for i in range(64)]
        k65 = k64 + [{"sol": "a" * 21, "sag": "bbbb", "yeni": "c"}]
        y32 = ["a" * (i + 1) for i in range(32)]
        y33 = y32 + ["a</w>"]
        if fn("a", [{"sol": "</w>", "sag": "a", "yeni": "a"}], ["a"])["tokenler"] != ["a", "</w>"] or fn("a", [R[0]], ["a"])["farklar"] != [] or fn("a", k64, ["a"])["farklar"] != [] or fn("a", R, y32)["metin_eslesmeleri"] != ["a"]:
            return False
        if len(fn("a" * 64, R, ["a"])["tokenler"]) != 65 or len(fn(" ".join(["a"] * 8), R, ["a"])["tokenler"]) != 16:
            return False
        for args in [
            (None, R, Y), ("", R, Y), (" a", R, Y), ("a  b", R, Y), ("A", R, Y), ("a" * 65, R, Y), (" ".join(["a"] * 9), R, Y),
            ("ab", None, Y), ("ab", [], Y), ("ab", [None], Y), ("ab", [dict(R[0], ek=1)], Y), ("ab", [{"sol": "a", "sag": "b"}], Y), ("ab", [{"sol": "A", "sag": "b", "yeni": "ab"}], Y), ("ab", [{"sol": 1, "sag": "b", "yeni": "ab"}], Y), ("ab", [R[0], R[0]], Y), ("ab", k65, Y),
            ("ab", R, None), ("ab", R, {}), ("ab", R, []), ("ab", R, [None]), ("ab", R, [""]), ("ab", R, ["A"]), ("ab", R, ["a" * 33]), ("ab", R, ["a", "a"]), ("ab", R, y33),
        ]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(token_filtre_raporu), "ham metin, tam token ve filtre farkları korunmalı")
def m_metin(metin, kurallar, yasaklar):
    return token_filtre_raporu(metin.replace("abc", "zzz"), kurallar, yasaklar)
def m_kural(metin, kurallar, yasaklar):
    return token_filtre_raporu(metin, list(reversed(kurallar)), yasaklar)
def m_yasak(metin, kurallar, yasaklar):
    return token_filtre_raporu(metin, kurallar, list(reversed(yasaklar)))
def m_cift(metin, kurallar, yasaklar):
    return token_filtre_raporu(metin, kurallar + kurallar, yasaklar)
for ad, mutant in [("metni değiştiren", m_metin), ("tokenları değiştiren", m_kural), ("yasak sırasını bozan", m_yasak), ("kuralları yineleyen", m_cift)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def token_filtre_raporu(metin, kurallar, yasaklar):
    import re
    def gecerli_sembol(deger):
        return isinstance(deger, str) and len(deger) <= 32 and re.fullmatch(r"(?:[a-z]+(?:</w>)?|</w>)", deger) is not None
    if not isinstance(metin, str) or not 1 <= len(metin) <= 64 or not re.fullmatch(r"[a-z]+(?: [a-z]+){0,7}", metin):
        raise ValueError("metin geçersiz")
    if not isinstance(kurallar, list) or not 1 <= len(kurallar) <= 64:
        raise ValueError("kural listesi geçersiz")
    ciftler = set()
    for kural in kurallar:
        if not isinstance(kural, dict) or set(kural) != {"sol", "sag", "yeni"}:
            raise ValueError("kural şeması geçersiz")
        if any(not gecerli_sembol(kural[a]) for a in ("sol", "sag", "yeni")):
            raise ValueError("kural sembolü geçersiz")
        cift = (kural["sol"], kural["sag"])
        if cift in ciftler:
            raise ValueError("kural çifti yinelenemez")
        ciftler.add(cift)
    if not isinstance(yasaklar, list) or not 1 <= len(yasaklar) <= 32:
        raise ValueError("yasak listesi geçersiz")
    if any(not gecerli_sembol(x) for x in yasaklar) or len(set(yasaklar)) != len(yasaklar):
        raise ValueError("yasaklar geçersiz")
    tokenler = []
    for kelime in metin.split(" "):
        semboller = list(kelime) + ["</w>"]
        while True:
            secilen = None
            for kural in kurallar:
                if any(semboller[i] == kural["sol"] and semboller[i + 1] == kural["sag"] for i in range(len(semboller) - 1)):
                    secilen = kural
                    break
            if secilen is None:
                break
            yeni = []
            i = 0
            while i < len(semboller):
                if semboller[i:i + 2] == [secilen["sol"], secilen["sag"]]:
                    yeni.append(secilen["yeni"])
                    i += 2
                else:
                    yeni.append(semboller[i])
                    i += 1
            semboller = yeni
        tokenler.extend(semboller)
    metin_eslesmeleri = [x for x in yasaklar if x in metin]
    token_eslesmeleri = [x for x in yasaklar if x in tokenler]
    farklar = [x for x in yasaklar if (x in metin_eslesmeleri) != (x in token_eslesmeleri)]
    return {"tokenler": tokenler, "metin_eslesmeleri": metin_eslesmeleri, "token_eslesmeleri": token_eslesmeleri, "farklar": farklar}
```

```hint
İki eşleşme listesini ayrı üret: ham metinde alt string, token listesinde tam eşitlik ara. Fark için iki listedeki üyeliğin farklı olmasını kullan.
```
:::

::: anlat Gerçek deney: token kimliği karakter veya kelime değildir
Önceki görevlerdeki BPE kuralları öğretim için sentetikti. Aşağıdaki görevde `ai_lab.dil_modeli()` ile **yerelde kurulu gerçek SmolLM2 tokenizer'ı** kullanılır. Model/tokenizer yoksa test geçmez; ders indirme yapmaz. Ortak yardımcı ağırlıkları da yükler ama bu görevde ileri hesap veya sohbet üretimi yapılmaz: ölçülen gerçek işlem tokenizasyondur.

`add_special_tokens=False` ile yalnız metnin tokenlarını al. `return_offsets_mapping=True`, hızlı tokenizer'ın her token için özgün metindeki `[başlangıç, bitiş)` karakter aralığını verir. Bu aralık Python string indeksidir; UTF-8 bayt indeksi değildir. Byte-level tokenizer'da tek Unicode karakteri birden fazla tokena ayrılabilir; bu tokenların aralıkları çakışabilir. Bu yüzden aralıkları zorla bölümlere ayırma ve her tokenın tek başına decode sonucunu birleştirmeyi metne geri dönüş sayma. Kimliklerin **tam listesini** birlikte decode et; boşluk temizlemeyi kapat.

Token sayısı ne kelime ne karakter sayısıdır. Baştaki boşluk, çift boşluk, yeni satır, emoji ve Unicode normalizasyonu token dizisini değiştirebilir. Hiçbirini sessizce silme veya normalize etme. Token listesine uygulanan bir güvenlik filtresini başka tokenizer'a aynen taşımak güvenli kabul edilemez; kimlikler ve sınırlar tokenizer sürümüne bağlıdır.

Kaynaklar: [Sennrich vd. 2016 — Neural Machine Translation of Rare Words with Subword Units (arXiv:1508.07909)](https://arxiv.org/abs/1508.07909), [Hugging Face Tokenizers — Fast Tokenizers ve Offset Mapping](https://huggingface.co/docs/tokenizers/index).
:::

::: gorev Gerçek deney · Token kimlikleri ve Unicode karakter aralıkları
`gercek_token_izi(metin)` işlevini yaz. `metin` bir `str` olmalıdır; boş string geçerlidir, diğer türlerde `ValueError` yükselt.

`tokenizer, _, bilgi = ai_lab.dil_modeli()` ile gerçek tokenizer'ı al. Metni değiştirmeden, özel token eklemeden ve `return_offsets_mapping=True` ile kodla. Yeni bir sözlük döndür:

- `token_idleri`: sıralı gerçek tamsayı kimlik listesi.
- `tokenlar`: `convert_ids_to_tokens` ile aynı kimliklerin sözlükteki token gösterimleri.
- `araliklar`: her token için `[baslangic, bitis]` listesi; `metin[baslangic:bitis]` özgün metindeki bölgeyi verir. Çakışmaları koru.
- `cozulen`: tüm kimlikleri birlikte `skip_special_tokens=False, clean_up_tokenization_spaces=False` ile decode et.
- `token_sayisi`: kimlik listesinin uzunluğu.

Kodda sabit kimlik tablosu, karakterleri token saymak, `split()` ile kelime saymak veya Unicode'u normalize etmek çözüm değildir. Aşağıdaki Çalıştır örneği canlı sonuçları gösterir; Kontrol rastgele ek metinlerle bağımsız karşılaştırma yapar.

```meta
motor: ai-gercek
gereksinim: torch
timeout: 240
```

```starter
import ai_lab

def gercek_token_izi(metin):
    return {}

if ai_lab.CALISTIR:
    for m in [" token", "token  token\n", "İstanbul 🧪", "e\u0301"]:
        print(repr(m), gercek_token_izi(m))
```

```test
import copy
import hashlib
import random
import ai_lab

sonuclar = []
def kontrol(kosul, mesaj):
    sonuclar.append(bool(kosul))
    return ok(kosul, mesaj)

sorun = ai_lab.kod_denetimi(src)
kontrol(not sorun, "laboratuvar yamalanmamalı: " + ", ".join(sorun))
fn = need("gercek_token_izi")
try:
    tok, _, bilgi = ai_lab.dil_modeli()
except ai_lab.GercekLabYok as e:
    kontrol(False, "GERÇEK TOKENIZER YOK: " + str(e))
    stop()
kontrol(tok.is_fast, "karakter aralıkları için gerçek hızlı tokenizer gerekli")
if not tok.is_fast:
    stop()

rng = random.SystemRandom()
kelimeler = ["İstanbul", "river", "güvenlik", "öğrenci", "🧪", "e\u0301", "é", "数据"]
metinler = ["", "token", " token", "token  token\n", "İstanbul 🧪", "e\u0301", "é",
            "\t a\n b  ", "hello , world !", "<|im_end|>",
            " ".join(rng.choice(kelimeler) for _ in range(4)) + " " + str(rng.randrange(100000, 999999)),
            "\n" + rng.choice(kelimeler) + "  " + rng.choice(kelimeler)]

def referans(m):
    e = tok(m, add_special_tokens=False, return_offsets_mapping=True)
    ids = list(e["input_ids"])
    return {"token_idleri": ids, "tokenlar": tok.convert_ids_to_tokens(ids),
            "araliklar": [list(x) for x in e["offset_mapping"]],
            "cozulen": tok.decode(ids, skip_special_tokens=False, clean_up_tokenization_spaces=False),
            "token_sayisi": len(ids)}
beklenen = [referans(m) for m in metinler]

def dogru(a, b, m):
    if not isinstance(a, dict) or set(a) != set(b):
        return False
    if not isinstance(a["token_sayisi"], int) or isinstance(a["token_sayisi"], bool):
        return False
    if not isinstance(a["token_idleri"], list) or any(type(x) is not int for x in a["token_idleri"]):
        return False
    if not isinstance(a["araliklar"], list) or any(not isinstance(x, list) or len(x) != 2 or
            any(type(n) is not int for n in x) or not 0 <= x[0] <= x[1] <= len(m) for x in a["araliklar"]):
        return False
    return a == b

def sozlesme(f):
    try:
        for m, b in zip(metinler, beklenen):
            a = f(m)
            if not dogru(a, b, m):
                return False
            # İkinci çağrı önceki sonucu değiştirmemeli; mutable önbellek paylaşımı da sınanır.
            once = copy.deepcopy(a)
            f(m + " yeni")
            if a != once:
                return False
        for m in [None, 42, True, [], {}, b"token"]:
            try:
                f(m)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

kontrol(sozlesme(fn), "gerçek tokenizer: kimlikler, Unicode ofsetleri, tam decode ve boşluklar korunuyor")

def donustur(on, sonra=lambda x: x):
    def f(m):
        if not isinstance(m, str):
            raise ValueError("metin str olmalı")
        return sonra(referans(on(m)))
    return f

sabit = copy.deepcopy(beklenen[1])
mutantlar = [
    ("boş kodun işlevi yok", None),
    ("boş sözlük", lambda m: {}),
    ("sabit gerçek sonuç", lambda m: copy.deepcopy(sabit)),
    ("baştaki ve sondaki boşluğu silen", donustur(lambda m: m.strip())),
    ("karakter sayısını token sayan", donustur(lambda m: m, lambda a: dict(a, token_sayisi=len(a["cozulen"])))),
    ("token sırasını ters çeviren", donustur(lambda m: m, lambda a: dict(a, token_idleri=list(reversed(a["token_idleri"]))))),
    ("Unicode aralıklarını kaydıran", donustur(lambda m: m, lambda a: dict(a, araliklar=[[x+1,y+1] for x,y in a["araliklar"]]))),
]
for ad, mutant in mutantlar:
    kontrol(not sozlesme(mutant), "hatalı çözüm reddedilmeli: " + ad)

gercek = [fn(m) for m in metinler] if all(sonuclar) else []
for m, a in zip(metinler, gercek):
    kontrol(a["cozulen"] == m, "tam kimlik listesi metne kayıpsız dönüyor: " + repr(m))

tokenizer_sha = hashlib.sha256(tok.backend_tokenizer.to_str().encode("utf-8")).hexdigest()
ai_lab.kanit_yaz("temel-01-tokenizasyon", {
    "kaynak": "gercek", "kabul": all(sonuclar),
    "model_bilgisi": dict(bilgi, tokenizer_sha256=tokenizer_sha),
    "islem": "gerçek tokenizer; model ileri hesabı ve sohbet çağrısı yok",
    "ayarlar": {"add_special_tokens": False, "clean_up_tokenization_spaces": False,
                "ofset_birimi": "Python Unicode karakter indeksi", "girdiler": metinler},
    "ciktilar": gercek, "mutant_sayisi": len(mutantlar),
    "temizlik": "CPU üzerinde tokenizer; harici sunucu/süreç başlatılmadı"})
if gercek:
    print("GERÇEK TOKENIZER:", bilgi["model"], bilgi["revizyon"], "sha256", tokenizer_sha)
    for m, a in zip(metinler, gercek):
        print(repr(m), "→", a["token_sayisi"], "token; kimlikler", a["token_idleri"], "aralıklar", a["araliklar"])
```

```solution
import ai_lab

def gercek_token_izi(metin):
    if not isinstance(metin, str):
        raise ValueError("metin str olmalı")
    tok, _, _ = ai_lab.dil_modeli()
    e = tok(metin, add_special_tokens=False, return_offsets_mapping=True)
    ids = list(e["input_ids"])
    return {"token_idleri": ids, "tokenlar": tok.convert_ids_to_tokens(ids),
            "araliklar": [list(x) for x in e["offset_mapping"]],
            "cozulen": tok.decode(ids, skip_special_tokens=False, clean_up_tokenization_spaces=False),
            "token_sayisi": len(ids)}

if ai_lab.CALISTIR:
    for m in [" token", "token  token\n", "İstanbul 🧪", "e\u0301"]:
        print(repr(m), gercek_token_izi(m))
```

```hint
`offset_mapping` tokenizer'dan gelir; karakterleri veya UTF-8 baytlarını sayarak yeniden üretme. `decode` bütün kimlik listesine bir kez uygulanır. Testte boş string geçerlidir; `strip()` ile girdi değiştirilmez.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Karakter değil alt-sözcük (`BPE`) (30 sn).** "Dil modeli ham harfleri veya tam kelimeleri değil, öncelik sırasıyla birleştirilmiş alt-sözcük (`subword`) parçalarını ve bunların tam sayı kimliklerini görür; boşluk ve büyük/küçük harf bile token sınırını değiştirir."
2. **Metin filtresi vs token filtresi uyuşmazlığı (35 sn).** "Ham dizgide geçen bir yasaklı ifade alt-sözcük sınırında ikiye bölündüğünde token listesinde kaybolabilir; tersine masum görünen karakter dizisi birleştirme sonunda yasaklı bir token kimliği üretebilir."
3. **Sürüm ve `offset_mapping` bağı (30 sn).** "Token kimlikleri modele ve tokenizer sürümüne özgüdür; karakter aralığını bayt sayarak tahmin etmek yerine doğrudan tokenizer'ın `offset_mapping` çıktısını kullanmak gerekir."
4. **Soru (25 sn).** "Aynı güvenlik anahtar kelime filtresini hem giriş metninde hem de üretilen token akışında çalıştırdığında görünmez sıfır-genişlikli Unicode karakterleri hangi katmanı yanıltır?"
:::
