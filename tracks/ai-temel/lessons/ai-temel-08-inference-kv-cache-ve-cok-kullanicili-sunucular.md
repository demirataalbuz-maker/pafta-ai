---
id: ai-temel-08
title: "Inference, KV Cache ve Çok Kullanıcılı Sunucular"
summary: Sentetik bütçe kurallarını, gerçek modelde KV cache eşdeğerliğini ve Ollama uygulamasında eşzamanlı HTTP/kiracı görünürlüğünü ölç.
esleme: ai-temel-04, ai-temel-07, ai-savunma-29
timeout: 45
---

::: anlat KV cache önceki hesabı yeniden kullanır

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Transformer modeli tokenlar için gerçek attention K/V tensörlerini tutar | İlk üç görevde görünür sentetik JSON ve küçük listeler; CPU görevinde kurulu modelin gerçek past_key_values nesnesi | Küçük tamsayı listesi gerçek tensör boyutunu veya GPU bellek kullanımını ölçmez |
| Çok kullanıcılı sunucu istekleri zamanlar ve kaynakları paylaşır | Bütçe seçimi ve kiracı filtresi temel görevlerde açık bir uygulama sözleşmesidir | Liste filtresi vLLM/llama.cpp/Ollama sunucusunun KV cache yalıtımının kanıtı değildir |

> [!NOT]
> `veri/cache.json` elle yazılmış **sentetik** örnektir; gerçek sunucudan alınmamıştır. İlk üç görevin setup'ı dosyayı geçici çalışma klasörüne kopyalar; her Run/Check yeni kopya üretir, düzenlemeler kalıcı değildir. Kaynak fixture dosyasını editörle okuyabilir, ders kodunda yüklenen verinin kopyasını değiştirerek gözlem yapabilirsin. Gizli test verisi ayrıdır. Gerçek CPU görevi kurulu modeli çalıştırır; ardından ayrı Ollama görevi gerçek eşzamanlı HTTP isteklerini ve uygulama kiracı görünürlüğünü ölçer. İndirme yapılmaz; vLLM/llama.cpp karşılaştırması veya backend KV yalıtımı iddiası yoktur.

Autoregressive üretim her adımda yeni token ekler. Key/Value cache önceki tokenların attention ara sonuçlarını saklayarak aynı hesabın yinelenmesini azaltır. Cache büyüdükçe bellek tüketimi artar ve istek yaşam döngüsüyle doğru ilişkilendirilmesi gerekir.

Görevler 1–3 küçük K/V listeleri ve sentetik verilerle çalışır; CPU adımı gerçek yerel dil modelini çalıştırır. Sekiz parçalık sınır yalnız ilk görevlerin sözleşmesidir; sunucu veya gerçek model kapasitesi değildir. vLLM/llama.cpp sunucu karşılaştırması bu listelerden çıkarılamaz.
:::

::: anlat Paylaşılan sunucuda bütçe ve yalıtım birlikte gerekir

Önce `veri/cache.json` dosyasını aç. `cache` ve `parca` ilk görevdeki K/V eşleşmesini, `istekler` ve `kapasite` ikinci görevdeki bütçeyi, `kayitlar` ve `kiraci` üçüncü görevdeki erişim kapsamını taşır. Görevler ham veriyi ve hesapladıkları sonucu birlikte yazar. Aynı dosyanın alanlarını okumak, kavramlar arasındaki ilişkiyi görünür kılar; bunlar modelden kaydedilmiş tensörler değildir. Bir isteğin bellek değerini değiştirip seçimin nasıl değiştiğini gözle; sonra ilk girdinin değişmediğini kontrol et.

Gerçek üretimde önce önekin bütün tokenları işlenir; buna prefill denir. Sonraki üretim adımı önceki K/V değerlerinden yararlanabilir. Cache önceki yanıt metninin kopyası değildir; her katmanın attention hesabına ait ara değerlerdir. Girdi uzunluğu, model yapısı ve veri türü kaynak ihtiyacını etkiler. Dersin ilk görevindeki sekiz tamsayı sınırından gerçek VRAM gereksinimi hesaplanamaz. Son deney bu yüzden listelerin uzunluğunu gerçek ölçüm diye sunmaz, modelin cache nesnesine doğrudan bakar.

Cache nesnesi yerinde büyüyebilir. Önek sonundaki uzunluğu o anda sayı olarak saklamazsan devamdan sonra iki kez aynı nesneye bakıp iki uzunluğu eşit görebilirsin. Bu bir ölçüm hatasıdır. Devam çağrısında öneki yeniden gönderirsen bağlam iki kez işlenir; yalnız yeni tokenları göndermek gerekir. Tam hesap kolu ise cache almadan bütün tokenları bir kez işler. İki kolun son logitleri tolerans içinde eşdeğer olmalıdır. Tek bir argmax eşleşmesi bütün dağılımın eşit olduğunu göstermez.

Zamanlayıcı örneğinde istek sırası korunur; sığmayan istek atlanır, sonraki küçük istek yine seçilebilir. Bu basit kural gerçek sürekli batching algoritmasının tamamı değildir. Saldırgan büyük veya uzun isteklerle ortak kaynağı tüketmeyi deneyebilir. Kaynak bütçesi olmadan iyi niyetli kullanıcıların beklemesi uzayabilir. Dersin sözleşmesi bellek birimlerini sayar; gerçek bir sunucuda token ve sıra sınırları, iptal, zaman aşımı ve adalet politikaları ayrıca değerlendirilir. Sığmayan ilk istekte tamamen durmak ile sonraki isteğe geçmek farklı davranışlardır.

Kiracı yalıtımında sadece doğru kaydı seçmek yetmez. Dönen sözlük kaynak kayıtla aynı nesneyse öğrenci sonucu değiştirirken ortak veriyi de değiştirebilir. Bu yüzden bağımsız kopya istenir. Başka kiracının kimliğini isteğe yazmak erişim hakkı vermez; gerçek uygulama kiracı kimliğini doğrulanmış oturumdan almalıdır. Bu liste görevinde kimlik sadece parametredir, kimlik doğrulama sistemi kurulduğu iddia edilmez. Bir filtre testinin geçmesi backend'in paylaşılan cache belleğinde sızıntı olmadığını kanıtlamaz.

Çıktıda önce girdi tokenlarını ve bölme noktasını, sonra cache uzunluklarını, en son maksimum logit farkını oku. Sürenin kısa çıkması tek başına başarı değildir; kısa CPU girdilerinde ölçüm gürültüsü baskın olabilir. Bu derste hızlanma eşiği yoktur. Küçük sayısal farklar kayan nokta hesabından doğabilir; tolerans açıkça belirtilmiştir. Bool'un Python'da int alt sınıfı olması, giriş listelerini append ile değiştirmek ve yalnız ilk sekiz logitte fark aramak sık tuzaklardır. Kabul bütün sözlük boyunca maksimum farkı ve modelin gerçekten aldığı tokenları denetler.

Sürekli batching bekleyen istekleri kapasiteye göre seçer. Bellek hesabı yapılmadan kabul edilen işler bütün kiracıları yavaşlatabilir. İstekleri sırayla gezip sığanları seçmek, basit ve tekrarlanabilir bir zamanlayıcı fixture'ıdır.

Cache kayıtları kiracı kimliğiyle ayrılmalıdır. Bir kiracının başka kiracının K/V verisini okuması yalnız performans değil, gizlilik sorunudur. Filtre çıktısı bağımsız kopyalar içermelidir.

Kaynaklar: [Hugging Face Transformers — KV Cache Rehberi](https://huggingface.co/docs/transformers/kv_cache), [Kwon vd. — Efficient Memory Management for Large Language Model Serving with PagedAttention (arXiv:2309.06180)](https://arxiv.org/abs/2309.06180).
:::

::: tahmin Cache ve batch çıktısını tahmin et
Üç çıktı satırını yaz:

```python
c = {"k": [1], "v": [9]}
print({"k": c["k"] + [2], "v": c["v"] + [8]})
print([x for x in [(2, "a"), (3, "b")] if x[0] <= 2])
kayitlar = [{"tenant": "a", "v": 1}, {"tenant": "b", "v": 2}]
print([x["v"] for x in kayitlar if x["tenant"] == "a"])
```

???

```cikti
{'k': [1, 2], 'v': [9, 8]}
[(2, 'a')]
[1]
```

İlk satır bağımsız cache eklemeyi, ikinci satır kapasite filtresini, üçüncü satır kiracı görünürlüğünü gösterir.
:::

::: gorev 1 · KV cache'e bağımsız parça ekle
`kv_ekle(cache, parca)` işlevini yaz. Cache tam `k`, `v` anahtarlı sözlüktür; iki değer de eşit uzunlukta, 0–7 öğeli, bool olmayan tamsayı listesidir. Parça tam `k`, `v` anahtarlı, iki bool olmayan tamsayı içeren sözlüktür. Geçersiz veride `ValueError` yükselt.

Parçanın değerlerini ilgili listelerin sonuna ekleyen yeni cache döndür. Özgün cache ve iç listeleri değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-08")
```

```starter
from ai_temel_veri import json_yukle

def kv_ekle(cache,parca):
    # KUSURLU BAŞLANGIÇ KODU: cache listelerini yerinde büyütür ve bağımsız sonuç üretmez.
    cache["k"].append(parca["k"])
    cache["v"].append(parca["v"])
    return cache

v=json_yukle("veri/cache.json")
print("Sentetik veri:",v)
print("Cache son:",kv_ekle(v["cache"],v["parca"]))
```

```test
import copy
C = {"k": [1], "v": [9]}
def sozlesme(fn):
    try:
        once = copy.deepcopy(C)
        sonuc = fn(C, {"k": 2, "v": 8})
        if sonuc != {"k": [1, 2], "v": [9, 8]} or C != once or sonuc["k"] is C["k"]:
            return False
        if fn({"k": [], "v": []}, {"k": 1, "v": 2}) != {"k": [1], "v": [2]}:
            return False
        c7={"k":list(range(7)),"v":list(range(20,27))}
        if fn(c7,{"k":7,"v":27})!={"k":list(range(8)),"v":list(range(20,28))}:
            return False
        dolu = {"k": list(range(8)), "v": list(range(8))}
        for args in [(None, {"k": 1, "v": 2}), ({"k": [1]}, {"k": 1, "v": 2}), ({"k": [1], "v": [2], "x": []}, {"k": 1, "v": 2}), ({"k": 1, "v": [2]}, {"k": 1, "v": 2}), ({"k": [1], "v": 2}, {"k": 1, "v": 2}), ({"k": [1], "v": []}, {"k": 1, "v": 2}), ({"k": [True], "v": [1]}, {"k": 1, "v": 2}), ({"k": ["1"], "v": [1]}, {"k": 1, "v": 2}), (dolu, {"k": 1, "v": 2}), (C, None), (C, {"k": 1}), (C, {"k": True, "v": 2}), (C, {"k": "1", "v": 2}), (C, {"k": 1, "v": 2, "x": 0})]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(kv_ekle), "cache kapasitesi, eşleşme ve kopya korunmalı")
def m_cache(c, p):
    return kv_ekle({"k": list(reversed(c["k"])), "v": list(reversed(c["v"]))}, p)
def m_parca(c, p):
    return kv_ekle(c, {"k": p["v"], "v": p["k"]})
def m_uzun(c, p):
    return kv_ekle({"k": c["k"] * 2, "v": c["v"] * 2}, p)
for ad, mutant in [("cache'i bozan", m_cache), ("K/V'yi değiştiren", m_parca), ("uzunluğu bozan", m_uzun)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle
def kv_ekle(cache, parca):
    if not isinstance(cache, dict) or set(cache) != {"k", "v"} or any(not isinstance(cache[a], list) for a in ("k", "v")):
        raise ValueError("cache geçersiz")
    if len(cache["k"]) != len(cache["v"]) or len(cache["k"]) >= 8 or any(not isinstance(x, int) or isinstance(x, bool) for a in ("k", "v") for x in cache[a]):
        raise ValueError("cache içeriği geçersiz")
    if not isinstance(parca, dict) or set(parca) != {"k", "v"} or any(not isinstance(parca[a], int) or isinstance(parca[a], bool) for a in ("k", "v")):
        raise ValueError("parça geçersiz")
    return {"k": cache["k"] + [parca["k"]], "v": cache["v"] + [parca["v"]]}
v=json_yukle("veri/cache.json")
print("Sentetik veri:",v)
print("Cache son:",kv_ekle(v["cache"],v["parca"]))

```

```hint
Yeni listeleri `cache["k"] + [parca["k"]]` biçiminde oluştur; `append` kullanırsan girdiyi değiştirirsin.
```
:::

::: gorev 2 · Bellek bütçesine göre batch seç
`batch_sec(istekler, kapasite)` işlevini yaz. İstekler 1–8 öğeli listedir; her istek tam `id`, `bellek` anahtarlarını içerir. Kimlikler farklı ve boş olmayan stringlerdir; bellek bool olmayan 1–4 tamsayısıdır. Kapasite bool olmayan 1–8 tamsayısıdır. Geçersiz veride `ValueError` yükselt.

İstekleri özgün sırayla gez. Sığanı seç ve kalan kapasiteyi azalt; sığmayanı atlayıp sonrakilere devam et. Seçilen kimlikleri liste olarak döndür.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-08")
```

```starter
from ai_temel_veri import json_yukle

def batch_sec(istekler,kapasite):
    # KUSURLU BAŞLANGIÇ KODU: sığmayan ilk istekte durur; sonraki küçük isteği göremez.
    sonuc=[]
    for x in istekler:
        if x["bellek"]>kapasite: break
        sonuc.append(x["id"])
        kapasite-=x["bellek"]
    return sonuc

v=json_yukle("veri/cache.json")
print("Sentetik veri:",v)
print("Batch:",batch_sec(v["istekler"],v["kapasite"]))
```

```test
I = [{"id": "a", "bellek": 2}, {"id": "b", "bellek": 3}, {"id": "c", "bellek": 1}]
def sozlesme(fn):
    try:
        if fn(I, 3) != ["a", "c"] or fn(I, 6) != ["a", "b", "c"] or fn(I, 1) != ["c"] or fn(I, 8) != ["a", "b", "c"]:
            return False
        tek = {"id": "t", "bellek": 4}
        sekiz = [{"id": str(i), "bellek": 1} for i in range(8)]
        if fn([tek], 4) != ["t"] or len(fn(sekiz, 8)) != 8:
            return False
        for args in [(None, 3), ([], 3), ([["id", "bellek"]], 3), (sekiz + [{"id": "9", "bellek": 1}], 8), (I, 0), (I, 9), (I, True), (I, "3"), ([dict(I[0], id=1)], 3), ([dict(I[0], id="")], 3), ([dict(I[0], bellek="2")], 3), ([dict(I[0], bellek=True)], 3), ([dict(I[0], bellek=0)], 3), ([dict(I[0], bellek=5)], 5), ([dict(I[0], ek=1)], 3), ([I[0], I[0]], 4)]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
_sirali_istekler = [{"id": "z", "bellek": 3}, {"id": "b", "bellek": 2},
                   {"id": "a", "bellek": 1}]
_onceki_istekler = [dict(istek) for istek in _sirali_istekler]
eq(batch_sec(_sirali_istekler, 3), ["z"],
   "Sıra korunur ve tam dolduktan sonra yeni istek seçilmez")
eq(batch_sec(_sirali_istekler, 4), ["z", "a"],
   "Aradaki büyük istek atlanır ve son istek bütçeyi tam doldurur")
eq(_sirali_istekler, _onceki_istekler, "Seçim sırasında girdi değiştirilmez")
eq(batch_sec([{"id": "x", "bellek": 2}], 1), [], "Hiçbir istek sığmayabilir")
ok(sozlesme(batch_sec), "batch sırası, atlama ve kapasite korunmalı")
def m_istek(i, k):
    return batch_sec(list(reversed(i)), k)
def m_kapasite(i, k):
    return batch_sec(i, 8)
def m_bellek(i, k):
    return batch_sec([dict(x, bellek=1) for x in i], k)
for ad, mutant in [("sırayı bozan", m_istek), ("kapasiteyi bozan", m_kapasite), ("belleği bozan", m_bellek)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle
def batch_sec(istekler, kapasite):
    if not isinstance(istekler, list) or not 1 <= len(istekler) <= 8:
        raise ValueError("istek listesi geçersiz")
    if any(not isinstance(x, dict) or set(x) != {"id", "bellek"} for x in istekler):
        raise ValueError("istek şeması geçersiz")
    if any(not isinstance(x["id"], str) or not x["id"] or not isinstance(x["bellek"], int) or isinstance(x["bellek"], bool) or not 1 <= x["bellek"] <= 4 for x in istekler):
        raise ValueError("istek değeri geçersiz")
    if len({x["id"] for x in istekler}) != len(istekler) or not isinstance(kapasite, int) or isinstance(kapasite, bool) or not 1 <= kapasite <= 8:
        raise ValueError("kapasite veya kimlik geçersiz")
    secim = []
    kalan = kapasite
    for x in istekler:
        if x["bellek"] <= kalan:
            secim.append(x["id"])
            kalan -= x["bellek"]
    return secim
v=json_yukle("veri/cache.json")
print("Sentetik veri:",v)
print("Batch:",batch_sec(v["istekler"],v["kapasite"]))

```

```hint
Kalan kapasiteyi tut; `bellek <= kalan` ise seç ve düş, aksi halde yalnız sonraki isteğe geç.
```
:::

::: gorev 3 · Cache kayıtlarını kiracıya göre yalıt
`kiraci_cache(kayitlar, kiraci)` işlevini yaz. Kayıtlar 0–8 öğeli listedir; her kayıt tam `tenant`, `k`, `v` anahtarlarını içerir. Tenant boş olmayan string, k/v bool olmayan tamsayıdır. Kiraci boş olmayan stringdir. Geçersiz veride `ValueError` yükselt.

Yalnız istenen kiracının kayıtlarını özgün sırayla ve bağımsız sözlük kopyaları olarak döndür. Girdileri değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-08")
```

```starter
from ai_temel_veri import json_yukle

def kiraci_cache(kayitlar,kiraci):
    # KUSURLU BAŞLANGIÇ KODU: tenant doğru süzülür ama paylaşılan sözlüklerin kendisini döndürür.
    return [x for x in kayitlar if x["tenant"]==kiraci]

v=json_yukle("veri/cache.json")
print("Sentetik veri:",v)
print("Kiracı kayıtları:",kiraci_cache(v["kayitlar"],v["kiraci"]))
```

```test
R = [{"tenant": "a", "k": 1, "v": 9}, {"tenant": "b", "k": 2, "v": 8}]
def sozlesme(fn):
    try:
        sonuc = fn(R, "a")
        sekiz = [dict(R[0], k=i) for i in range(8)]
        if sonuc != [R[0]] or sonuc[0] is R[0] or fn(R, "b") != [R[1]] or fn(R, "c") != [] or fn([], "a") != [] or len(fn(sekiz, "a")) != 8:
            return False
        cok=[R[0],R[1],dict(R[0],k=3,v=7)]
        if fn(cok,"a") != [R[0],cok[2]]:
            return False
        for args in [(None, "a"), ({}, "a"), ([["tenant", "k", "v"]], "a"), (sekiz + [dict(R[0], k=9)], "a"), (R, ""), (R, None), (R, 123), ([dict(R[0], ek=1)], "a"), ([dict(R[0], k=True)], "a"), ([dict(R[0], k="1")], "a"), ([dict(R[0], tenant="")], "a"), ([dict(R[0], tenant=1)], "a")]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(kiraci_cache), "kiracı filtresi ve bağımsız kayıt kopyası korunmalı")
def m_kayit(r, t):
    return kiraci_cache(list(reversed(r)), t)
def m_kiraci(r, t):
    return kiraci_cache(r, "b")
def m_hepsi(r, t):
    return [dict(x) for x in r]
for ad, mutant in [("kayıtları bozan", m_kayit), ("kiracıyı değiştiren", m_kiraci), ("yalıtımı kaldıran", m_hepsi)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle
def kiraci_cache(kayitlar, kiraci):
    if not isinstance(kayitlar, list) or len(kayitlar) > 8:
        raise ValueError("kayıt listesi geçersiz")
    if any(not isinstance(x, dict) or set(x) != {"tenant", "k", "v"} for x in kayitlar):
        raise ValueError("kayıt şeması geçersiz")
    if any(not isinstance(x["tenant"], str) or not x["tenant"] or any(not isinstance(x[a], int) or isinstance(x[a], bool) for a in ("k", "v")) for x in kayitlar):
        raise ValueError("kayıt değeri geçersiz")
    if not isinstance(kiraci, str) or not kiraci:
        raise ValueError("kiracı geçersiz")
    return [dict(x) for x in kayitlar if x["tenant"] == kiraci]
v=json_yukle("veri/cache.json")
print("Sentetik veri:",v)
print("Kiracı kayıtları:",kiraci_cache(v["kayitlar"],v["kiraci"]))

```

```hint
Liste üretiminde tenant eşitliğini filtrele ve her eşleşme için `dict(x)` kopyası oluştur.
```
:::

::: anlat Gerçek deney: hazır K/V listesi yerine modelin cache nesnesi
Önceki görevler kapasite ve kiracı kurallarını küçük listelerle gösteriyordu. Bu adımda kurulu dil modeli CPU'da gerçekten çalışır: önek bir kez işlenir, modelin ürettiği `past_key_values` kalan tokenlarla yeniden kullanılır. Cache'in önekten sonraki ve devamdan sonraki gerçek uzunluğunu ölçeriz. Aynı metnin cache kullanmadan hesaplanan son logitleriyle sonucu karşılaştırırız.

`DynamicCache` benzeri cache nesneleri devam çağrısında yerinde büyüyebilir. Önek uzunluğunu devam çağrısından **önce** sayı olarak kaydet; nesneyi saklayıp en son bakmak iki ölçümün de son uzunluk görünmesine neden olabilir. Cache varken öneki ikinci kez göndermek de bağlamı çoğaltır; devam çağrısına yalnız henüz işlenmemiş tokenları ver.

Bu tek istekli, kısa CPU deneyidir. Gerçek bir vLLM sunucusunun çok kiracılı yalıtımını, sürekli batching davranışını veya belirli bir hızlanmayı kanıtlamaz. Süreyi başarı şartı yapmayız; doğru cache yeniden kullanımını, gerçek girdi uzunluklarını ve sayısal eşdeğerliği sınarız. Her çağrı kendi yeni cache'ini üretir; başka kullanıcının cache'i kullanılmaz.
:::

::: gorev Gerçek deney · Prefill, cache ile devam ve tam hesap karşılaştırması
`gercek_kv_deneyi(metin, bolme)` işlevini yaz:

- `metin` boşluk dışı karakter içeren `str` olsun. Kurulu gerçek tokenizer özel token eklemeden 2–24 token üretmeli. `bolme` bool olmayan `int`, `1 <= bolme < token_sayisi` olmalı. Diğer girdilerde `ValueError` yükselt; sessiz kırpma yapma.
- `ai_lab.dil_modeli()` ile gerçek tokenizer ve modeli al. `torch.no_grad()` içinde önek `ids[:bolme]` ile `model(..., use_cache=True)` çalıştır. Dönen cache'in `get_seq_length()` değerini **şimdi** kaydet.
- Yalnız `ids[bolme:]` ile devam et; `past_key_values=cache, use_cache=True` ver. Dönen cache uzunluğunu kaydet. Son konumun logitlerini al.
- Aynı tam kimlik dizisini `use_cache=False` ile bağımsız çalıştırıp son konum logitlerini karşılaştır. Float64'a çevirerek mutlak farkların maksimumunu hesapla.
- Tam şu alanları döndür: `token_idleri` (int listesi), `prefill_token` (int), `devam_token` (int), `cache_once` (int), `cache_sonra` (int), `en_olasi_id` (cache'li son logit argmax'ı, int), `cache_logitleri` (cache'li son konumun ilk 8 float logiti), `max_logit_farki` (float).

Gerçek modele cache ile devam çağrısı yapılmadan yalnız doğru sayıları döndürmek yeterli değildir. Test modele giren tokenları ve çağrı anındaki cache uzunluğunu gözlemler. Referans/test işlevlerini çağırma. Sonuçları yuvarlama.

```meta
motor: ai-gercek
gereksinim: torch
timeout: 240
```

```starter
import ai_lab

def gercek_kv_deneyi(metin, bolme):
    return {}

if ai_lab.CALISTIR:
    print(gercek_kv_deneyi("The river flows through the city.", 2))
```

```test
import copy
import random
import ai_lab

sonuclar=[]
def kontrol(c,mesaj):
    sonuclar.append(bool(c))
    return ok(c,mesaj)
import ast
_yasak=("referans_kv_deneyi","kanit_yaz")
sorun=ai_lab.kod_denetimi(src,yasak=_yasak)
for n in ast.walk(ast.parse(src)):
    if isinstance(n,ast.ImportFrom) and any(a.name in _yasak or a.name=="*" for a in n.names):
        sorun.append("referans importu yasak")
if not kontrol(not sorun,"Kendi gerçek KV işlevini yaz: "+"; ".join(sorun)):
    stop()
fn=need("gercek_kv_deneyi")
try:
    import torch
    tok,model,bilgi=ai_lab.dil_modeli()
except (ImportError,ai_lab.GercekLabYok) as e:
    kontrol(False,"GERÇEK MODEL YOK: "+str(e))
    stop()
rng=random.SystemRandom()
metinler=["The river flows through the city.","Bugün İstanbul sakin.",
          rng.choice(["A green", "A blue", "A red"])+" bird has "+str(rng.randrange(100,999))+" notes."]
ayarlar=[(metinler[0],1),(metinler[1],2),(metinler[2],3)]

def hesap(m,b,cache_yok=False,ilk=False,tekrar=False):
    ids=tok(m,add_special_tokens=False)["input_ids"]
    with torch.no_grad():
        ilk_yanit=model(torch.tensor([ids[:b]]),use_cache=True)
        cache=ilk_yanit.past_key_values
        once=int(cache.get_seq_length())
        devam=ids if tekrar else ids[b:]
        son=model(torch.tensor([devam]),past_key_values=None if cache_yok else cache,use_cache=True)
        sonra=int(son.past_key_values.get_seq_length())
        cache_l=son.logits[0,0 if ilk else -1].double()
        tam=model(torch.tensor([ids]),use_cache=False).logits[0,-1].double()
    return {"token_idleri":ids,"prefill_token":b,"devam_token":len(ids)-b,
            "cache_once":once,"cache_sonra":sonra,"en_olasi_id":int(cache_l.argmax().item()),
            "cache_logitleri":cache_l[:8].tolist(),"max_logit_farki":float((cache_l-tam).abs().max().item())}
beklenen=[hesap(m,b) for m,b in ayarlar]
def ayni(a,b):
    try:
        if not isinstance(a,dict) or set(a)!=set(b) or a["token_idleri"]!=b["token_idleri"] or any(type(x) is not int for x in a["token_idleri"]):
            return False
        for k in ["prefill_token","devam_token","cache_once","cache_sonra","en_olasi_id"]:
            if type(a[k]) is not int or a[k]!=b[k]:
                return False
        l=a["cache_logitleri"]
        if not isinstance(l,list) or len(l)!=8 or any(type(x) is not float for x in l):
            return False
        fark=a["max_logit_farki"]
        return type(fark) is float and 0<=fark<=1e-3 and abs(fark-b["max_logit_farki"])<=1e-4 and torch.allclose(torch.tensor(l,dtype=torch.float64),torch.tensor(b["cache_logitleri"],dtype=torch.float64),atol=1e-4,rtol=1e-5)
    except Exception:
        return False

uzun=" the"*40
def sozlesme(f):
    try:
        for (m,b),ref in zip(ayarlar,beklenen):
            cagrilar=[]
            def izle(modul,args,kwargs):
                ids=args[0] if args else kwargs.get("input_ids")
                c=kwargs.get("past_key_values")
                cagrilar.append({"ids":ids.detach().tolist() if isinstance(ids,torch.Tensor) else None,
                                 "cache":int(c.get_seq_length()) if c is not None else 0,
                                 "use_cache":kwargs.get("use_cache")})
            h=model.register_forward_pre_hook(izle,with_kwargs=True)
            try:
                a=f(m,b)
            finally:
                h.remove()
            if not ayni(a,ref):
                return False
            ids=ref["token_idleri"]
            hedefler=[{"ids":[ids[:b]],"cache":0,"use_cache":True},
                      {"ids":[ids[b:]],"cache":b,"use_cache":True},
                      {"ids":[ids],"cache":0,"use_cache":False}]
            if any(x not in cagrilar for x in hedefler):
                return False
        if f(" the" * 2, 1)["token_idleri"] != tok(" the" * 2, add_special_tokens=False)["input_ids"]:
            return False
        if len(f(" the" * 24, 23)["token_idleri"]) != 24:
            return False
        for args in [("",1),("   ",1),(None,1),("hi",1),(metinler[0],0),(metinler[0],True),(metinler[0],1.0),(" the"*2,2),(" the"*24,24),(" the"*25,2),(metinler[0],999),(uzun,2)]:
            try:
                f(*args)
                return False
            except ValueError:
                pass
        from unittest.mock import patch as _patch
        class _SahtePKV:
            def __init__(self, n): self._n = n
            def get_seq_length(self): return self._n
        class _SahteOut:
            def __init__(self, n_tok, cache_n):
                self.logits = torch.zeros((1, n_tok, 8), dtype=torch.float32)
                self.logits[0, -1, 2] = 3.0
                self.past_key_values = _SahtePKV(cache_n)
        class _SahteMdl:
            def __call__(self, input_ids, past_key_values=None, use_cache=False):
                n_tok = int(input_ids.shape[1])
                once = past_key_values.get_seq_length() if past_key_values is not None else 0
                return _SahteOut(n_tok, once + n_tok)
        def _sahte_tok(txt, add_special_tokens=True):
            if add_special_tokens is not False:
                return {"input_ids": [99, 1, 2]}
            return {"input_ids": [10, 11]}
        with _patch.object(ai_lab, "dil_modeli", return_value=(_sahte_tok, _SahteMdl(), {})):
            if f("iki token", 1)["token_idleri"] != [10, 11]:
                return False
            try:
                f("   ", 1)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
kontrol(sozlesme(fn),"gerçek prefill ve cache'li devam tam hesapla eşdeğer; cache uzunluğu ve gerçek çağrılar doğru")
def gecerli(**hatalar):
    def f(m,b):
        if not isinstance(m,str) or not m.strip() or type(b) is not int:
            raise ValueError("girdi")
        ids=tok(m,add_special_tokens=False)["input_ids"]
        if not 2<=len(ids)<=24 or not 1<=b<len(ids):
            raise ValueError("sınır")
        return hesap(m,b,**hatalar)
    return f
sabit=copy.deepcopy(beklenen[0])
for ad,mutant in [("boş kod/işlev",None),("boş sözlük",lambda m,b:{}),
                  ("sabit gerçek rapor",lambda m,b:copy.deepcopy(sabit)),
                  ("devamda cache'i yok sayan",gecerli(cache_yok=True)),
                  ("ilk konum logitlerini alan",gecerli(ilk=True)),
                  ("öneki cache'e yeniden ekleyen",gecerli(tekrar=True))]:
    kontrol(not sozlesme(mutant),"hatalı çözüm reddedilmeli: "+ad)
ciktilar=[fn(m,b) for m,b in ayarlar] if all(sonuclar) else []
ai_lab.kanit_yaz("temel-08-kv-cache",{
    "kaynak":"gercek","kabul":all(sonuclar),"model_bilgisi":bilgi,
    "ayarlar":{"girdiler":[list(a) for a in ayarlar],"max_token":24,"logit_tolerans":1e-3},
    "ciktilar":ciktilar,"olculen":"modelin gerçek KV nesnesi ve cache ile devam hesabı",
    "sinir":"çok kiracılı sunucu, sürekli batching, hızlanma ve GPU bellek kabulü yapılmadı",
    "temizlik":"cache yalnız bu işin yerel değişkenidir; harici sunucu veya süreç başlatılmadı"})
for d in ciktilar:
    print("cache",d["cache_once"],"→",d["cache_sonra"],"devam tokenı",d["devam_token"],"tam hesaba maksimum logit farkı",d["max_logit_farki"])
```

```solution
import ai_lab
import torch

def gercek_kv_deneyi(metin, bolme):
    if not isinstance(metin,str) or not metin.strip() or type(bolme) is not int:
        raise ValueError("metin veya bölme geçersiz")
    tok,model,_=ai_lab.dil_modeli()
    ids=tok(metin,add_special_tokens=False)["input_ids"]
    if not 2<=len(ids)<=24 or not 1<=bolme<len(ids):
        raise ValueError("token sınırı veya bölme geçersiz")
    with torch.no_grad():
        pre=model(torch.tensor([ids[:bolme]]),use_cache=True)
        cache=pre.past_key_values
        once=int(cache.get_seq_length())
        devam=model(torch.tensor([ids[bolme:]]),past_key_values=cache,use_cache=True)
        sonra=int(devam.past_key_values.get_seq_length())
        cache_l=devam.logits[0,-1].double()
        tam=model(torch.tensor([ids]),use_cache=False).logits[0,-1].double()
    return {"token_idleri":ids,"prefill_token":bolme,"devam_token":len(ids)-bolme,
            "cache_once":once,"cache_sonra":sonra,"en_olasi_id":int(cache_l.argmax().item()),
            "cache_logitleri":cache_l[:8].tolist(),"max_logit_farki":float((cache_l-tam).abs().max().item())}

if ai_lab.CALISTIR:
    print(gercek_kv_deneyi("The river flows through the city.",2))
```

```hint
`cache.get_seq_length()` ölçümünü devam çağrısından önce ve sonra al. Devamda yalnız işlenmemiş tokenlar gönderilir; tam hesap için cache aktarılmaz. Logit farkı bütün sözlük üzerinde hesaplanır, yalnız ilk 8 örnek üzerinde değil.
```
:::

::: anlat Sunucu kapsamı: kurulu Ollama ve uygulama yalıtımı
Bu Windows deneyinde sunucu olarak kurulu Ollama kullanılır; vLLM veya llama.cpp ikili sunucusu karşılaştırması yapılmaz. Önceki CPU adımı gerçek backend K/V nesnesini öğretir. Bu ayrı adım iki istemi gerçek yerel HTTP uygulaması üzerinden aynı anda yürütür ve uygulamanın kiracıya göre tuttuğu gerçek çıktı kayıtlarını sınar. Bunlar K/V tensörleri değildir.

İki kimlik için sentetik etiketli istekler gönderilir. Kimlik, gövdeden değil deneye ait geçici Bearer belirtecinden belirlenir; başka tenant yazmak reddedilir. Korumasız negatif kontrol gerçek çıktı kayıtlarını iki kiracıya birden gösterir; korumalı okuma senin kiraci_cache işlevini kullanır. Her kiracı kendi model çıktısını okuyabilmeli, diğerininkini görememelidir. HTTP katmanındaki aktif istek çakışması kaydedilir; bu, Ollama'nın tokenları aynı anda ürettiğini, sürekli batching yaptığını veya cache belleğinin donanım düzeyinde yalıtıldığını kanıtlamaz.

Yalnız bu deneyin dinamik loopback portundaki HTTP sunucusu kapatılır. Kullanıcının Ollama sunucusu kapatılmaz; önceden yüklü model korunur. Hiçbir model/araç indirilmez. Sunucu yanıt metni ya da hız sabit bir beklenen değere bağlanmaz; tamamlanmış çağrılar, gerçek kayıt görünürlüğü, sahte kimlik reddi ve kaynak kapanışı kabul koşuludur.
:::

::: gorev Gerçek deney · Ollama eşzamanlı istek ve kiracı görünürlüğü
`kiraci_cache(kayitlar,kiraci)` işlevini 3. görevle aynı sözleşmeyle yaz. Gerçek sunucu bu işlevi HTTP okuma yolunda çağırır. Bu kayıtlar gerçek model çıktılarının uygulama indeksidir; K/V tensörü değildir. Çalıştır ham yanıtları ve ölçümleri gösterir. Eksik model, hata ve kapanmayan kendi sunucusu kabul değildir.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab

def kiraci_cache(kayitlar,kiraci):
    # KUSURLU BAŞLANGIÇ KODU: tüm kiracıların kayıtlarını verir.
    return [dict(x) for x in kayitlar]

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_08_sunucu as deney
    deney.goster(kiraci_cache)
```

```test
import ai_lab
import ast
checks=[]
_eski_ok=ok

def ok(c,m):
    checks.append(bool(c))
    return _eski_ok(c,m)
_yasak=("kiraci_ref","kontroller","kanit_yaz")
sorun=ai_lab.kod_denetimi(src,yasak=_yasak)
for n in ast.walk(ast.parse(src)):
    if isinstance(n,ast.ImportFrom) and any(a.name in _yasak or a.name=="*" for a in n.names):
        sorun.append("referans importu yasak")
if not ok(not sorun,"Kendi kiracı işlevini yaz: "+"; ".join(sorun)):
    stop()
need("kiraci_cache")
R = [{"tenant": "a", "k": 1, "v": 9}, {"tenant": "b", "k": 2, "v": 8}]
def sozlesme(fn):
    try:
        sonuc = fn(R, "a")
        sekiz = [dict(R[0], k=i) for i in range(8)]
        if sonuc != [R[0]] or sonuc[0] is R[0] or fn(R, "b") != [R[1]] or fn(R, "c") != [] or fn([], "a") != [] or len(fn(sekiz, "a")) != 8:
            return False
        cok=[R[0],R[1],dict(R[0],k=3,v=7)]
        if fn(cok,"a") != [R[0],cok[2]]:
            return False
        for args in [(None, "a"), ({}, "a"), ([["tenant", "k", "v"]], "a"), (sekiz + [dict(R[0], k=9)], "a"), (R, ""), (R, None), (R, 123), ([dict(R[0], ek=1)], "a"), ([dict(R[0], k=True)], "a"), ([dict(R[0], k="1")], "a"), ([dict(R[0], tenant="")], "a"), ([dict(R[0], tenant=1)], "a")]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(kiraci_cache), "kiracı filtresi ve bağımsız kayıt kopyası korunmalı")
def m_kayit(r, t):
    return kiraci_cache(list(reversed(r)), t)
def m_kiraci(r, t):
    return kiraci_cache(r, "b")
def m_hepsi(r, t):
    return [dict(x) for x in r]
for ad, mutant in [("kayıtları bozan", m_kayit), ("kiracıyı değiştiren", m_kiraci), ("yalıtımı kaldıran", m_hepsi)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
if not all(checks):
    stop()
from sandbox import ai_gercek_ai_temel_08_sunucu as D
try:
    r=D.deney(kiraci_cache)
except Exception as e:
    ok(False,"GERÇEK SUNUCU DENEYİ TAMAMLANMADI: "+type(e).__name__+": "+str(e))
    stop()
for name,value in D.kontroller(r).items():
    ok(value,name)
for t,view in r["korumali"].items():
    ok(view["body"]["kayitlar"]==D.kiraci_ref(r["kayitlar"],t),"gerçek HTTP görünümü bağımsız kiracı referansıyla aynı: "+t)
ai_lab.kanit_yaz("temel-08-ollama-sunucu",dict(kaynak="gercek",kabul=all(checks),ortam=r["ortam"],deney=r))
if all(checks):
    print("BULGU: iki gerçek model yanıtı; HTTP istekleri çakıştı, korumalı görünüm yalnız kendi kiracısının kaydını döndürdü. Backend KV yalıtımı/sürekli batching kanıtı değildir.")
```

```solution
import ai_lab
def kiraci_cache(kayitlar, kiraci):
    if not isinstance(kayitlar, list) or len(kayitlar) > 8:
        raise ValueError("kayıt listesi geçersiz")
    if any(not isinstance(x, dict) or set(x) != {"tenant", "k", "v"} for x in kayitlar):
        raise ValueError("kayıt şeması geçersiz")
    if any(not isinstance(x["tenant"], str) or not x["tenant"] or any(not isinstance(x[a], int) or isinstance(x[a], bool) for a in ("k", "v")) for x in kayitlar):
        raise ValueError("kayıt değeri geçersiz")
    if not isinstance(kiraci, str) or not kiraci:
        raise ValueError("kiracı geçersiz")
    return [dict(x) for x in kayitlar if x["tenant"] == kiraci]
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_08_sunucu as deney
    deney.goster(kiraci_cache)
```

```hint
Kimlik uygulamada belirlenir; işlev yalnız doğru tenant kayıtlarını kopyalayarak döndürür. Yanlış tenant'a sessiz geri dönüş yapma.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Yeniden hesap yerine `KV cache` (30 sn).** "Otoregresif üretimde her yeni token için geçmiş anahtar (`K`) ve değer (`V`) tensörlerini baştan hesaplamak $O(T^2)$ maliyet üretir; `past_key_values` önbelleği aynı logitleri tek tokenlık adımla verir."
2. **Sunucu bellek bütçesi (30 sn).** "Eşzamanlı isteklerde GPU belleğini model ağırlıklarından çok aktif isteklerin `KV cache` büyüklüğü doldurur; kabul sırası ve bellek tavanı açık bütçe kuralı gerektirir."
3. **Çok kiracılı (`multi-tenant`) yalıtım (35 sn).** "Önek veya `KV cache` paylaşımı kiracı kimliğiyle (`tenant_id`) ayrılmazsa bir kullanıcının önbelleği başka kullanıcıya hem içerik hem zamanlama yan kanalı sızdırır."
4. **Soru (25 sn).** "İki farklı kiracı aynı sistem istemini paylaşıyorsa hangi önbellek katmanı paylaşılabilir, hangisi kesinlikle kiracıya özel kalmalıdır?"
:::
