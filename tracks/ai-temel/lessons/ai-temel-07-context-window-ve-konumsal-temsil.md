---
id: ai-temel-07
title: "Context Window ve Konumsal Temsil"
summary: Token bütçesine göre ardışık bağlam seç, sinüzoidal konum üret ve düşen talimatları raporla.
esleme: ai-temel-01, ai-temel-04, ai-temel-08
timeout: 45
---

::: anlat context window sınırlı bir bütçedir

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Tokenizer metni kimliklere ayırır; model sınırlı bir diziyi işler | İlk üç görev sentetik JSON, final kurulu SmolLM2 tokenizer ve gerçek ileri hesap | Hazır uzunluklar gerçek tokenizer ölçümü değildir |
| Bağlam kırpılması eski bilgiyi kaldırabilir | Kesintisiz son parça seçimi ve modele gönderilen konumların gözlenmesi | Kısa deney tam pencere kapasitesini, güvenlik başarısını veya uzun bağlam kalitesini kanıtlamaz |

> [!NOT]
> `veri/baglam.json` elle hazırlanmış sentetik örnektir; sunucu kaydı değildir. İlk üç görev aynı dosyayı okur. Her Çalıştır/Kontrol geçici bir veri/ kopyası kurar; değişiklikler sonraki çalıştırmaya taşınmaz. Kaynak dosyayı kendi editöründe açabilir veya yüklenen sözlüğü ders kodunda değiştirip Çalıştır ile deneyebilirsin. Gizli testler bu dosyadan bağımsızdır. Final önceden kurulu yerel modeli çalıştırır; yeni indirme veya kalıcı sunucu açmaz.

Modele aynı anda sunulan token sayısı sınırlıdır. Bütçe dolunca eski mesajlar kırpılabilir; kırpma yalnız metni değil, güvenlik talimatlarını ve kanıtları da kapsam dışında bırakabilir. Bu yüzden hangi mesajların kaldığı açıkça ölçülmelidir.

İlk üç görevde model açılmaz ve mesaj uzunlukları hazır sayılardır; son görevde kurulu Transformers modeli gerçekten çalıştırılır. Sondan başlayarak sığan ardışık mesajlar seçilir; sığmayan ilk eski mesajda durulur. Böylece bağlam her zaman özgün dizinin kesintisiz bir son parçasıdır.
:::

::: anlat Konum bilgisi sırayı temsil eder

Önce aynı ham dosyayı oku. tokenlar alanı okunabilir etiketlerden oluşur; gerçek token kimlikleri veya sözcük sınırları olduğunu varsayma. sinir alanını değiştirip ilk görevi Çalıştır: eski başı almakla güncel sonu almak arasındaki fark doğrudan görünür. Kırpılmış liste özgün sırayı korumalıdır. Liste zaten sınıra sığıyorsa bile yeni bir kopya dönmelidir; bir çıktıyı düzenlemek sonraki işleme giden kaynak veriyi sessizce değiştirmemelidir. Negatif dilim sınırları yararlıdır ama Python'da sıfır sınırı bütün listeyi seçebilir. Bu yüzden tür ve aralık doğrulaması dilimlemeden önce gelir. Bool değerinin Python'da int alt sınıfı olması da sınır kontrolünde özellikle ele alınır.

İkinci görev dosyadaki pozisyonlar listesinden yararlanır. Sıfır konumu sıfır vektör değildir: sinüs sıfır, kosinüs birdir. İki kanalı aynı fonksiyondan üretmek veya konumu bir artırmak tabloyu bozabilir. Sonuçları altı ondalığa yuvarlamak bu küçük görevin sözleşmesidir; gerçek modelin bütün konumsal temsillerinin böyle yuvarlandığı anlamına gelmez. Bu iki bileşen klasik sinüzoidal temsilin ilk frekans çiftidir. Modern model başka bir yöntem kullanabilir; finalde modeli bu oyuncak sinüs tablosuyla değiştirmiyoruz. Öğrenci yalnız token dizisine uygun position_ids üretip modelin kendi mekanizmasına gönderir.

Üçüncü görevde dosyadaki mesajlar ve butce alanlarını birlikte incele. Mesaj uzunluğu burada önceden verilmiş sentetik maliyettir. System rolü sayısal bütçeden muaf değildir. En yeni mesaj sığmıyorsa seçilen liste boş kalabilir. Ortadaki büyük bir mesaj sığmayınca daha eski küçük mesajı seçmek, kesintisiz son parça kuralını bozar. Bu yüzden continue ile atlamak yerine ilk aşımda break gerekir. Dosyadaki aralik_ornegi tam bu tuzağı gösterir: son küçük mesaj sığar, ortadaki büyük mesaj sığmaz, en eski küçük mesaj artık aranmaz. Gerçek ürünlerin farklı seçim politikaları olabilir; burada açıkça tanımlanan tek politika ölçülür.

Güvenlik bakımından düşen listesi kayıp talimatları görünür kılar. Bir saldırgan çok miktarda içerikle önceki kısıtları pencere dışına itmeye çalışabilir. Fakat system mesajının listede kalması tek başına itaat veya enjeksiyon direnci kanıtı değildir. Sadece en son mesaja güvenmek de belge içindeki düşük güvenli talimatı yetkili kılmaz. Bu ders saldırının başarı oranını ölçmez; uygulamanın hangi bilgiyi modele gerçekten taşıdığını gözler. Korunması gereken kurallar ve kaynak yetkileri için ayrıca uygulama politikası gerekir. Uzunluk alanına güvenmek yerine üretimde aynı tokenizer ile ölçmek, sohbet şablonu ve çıktı için ayrılacak bütçeyi hesaba katmak gerekir; ilk üç oyuncak görev bu ayrıntıları içermez.

Final metni olduğu gibi tokenize eder. Baştaki boşluğu silmek veya sözcüklere bölmek gerçek kimlikleri değiştirebilir. Tokenların son kısmı seçilir, yeni kısa dizide konumlar sıfırdan başlar ve önbellek kapalı bir ileri hesap yapılır. Bu tercih daha önceki KV cache veya mutlak konum devamlılığını taklit etmez. Modelin config sınırı ayrıca raporlanır; 32 tokenlık laboratuvar sınırını modelin bütün kapasitesi sanma. Bir token, tam 32 token, sığan metin ve kırpılan metin ayrı durumlardır. Çıktıdaki düşen sayı tam token sayısından hesaplanır, görünen karakter sayısından değil.

Logitler olasılık değildir: son konumda sonraki token adaylarına verilen ham sayılardır. Rapordaki ilk sekiz logit sözlük indeksleri sıfırdan yediye aittir; en olası sekiz aday anlamına gelmez. en_olasi_id bütün sözlüğün argmax değeridir. Aynı raporu döndürüp modele başka tokenlar vermek geçerli çözüm değildir; test gerçek forward çağrısının kimliklerini, position_ids değerlerini, use_cache ayarını ve no_grad durumunu gözler. Kanıt özgün girdileri, ayarları, model sürümünü, cihazı ve gerçek sonuçları tutar. Çalıştır keşif kaydı üretir, kabul vermez. Kontrol bütün koşullar sağlanırsa kabul kaydeder. Yerel model eksikse hata görünür ve görev geçmez; ders indirme başlatmaz.

Transformer token sırasını doğrudan bilmez; konumsal temsil bu bilgiyi ekler. Sinüzoidal kodlama farklı frekanslarda sinüs ve kosinüs değerleri kullanır. Biz iki boyutlu, sabit tabanlı küçük bir sürüm kullanacağız.

Konumsal vektör tokenın anlamını tek başına taşımaz. Ayrıca modern modeller farklı konum yöntemleri kullanabilir; buradaki amaç sıra ve pencere kavramlarını deterministik olarak sınamaktır.

Kaynaklar: [Vaswani vd. — Attention Is All You Need (arXiv:1706.03762)](https://arxiv.org/abs/1706.03762), [Hugging Face Transformers — CausalLM Model Çıktıları](https://huggingface.co/docs/transformers/main_classes/output).
:::

::: tahmin Bağlam seçimini tahmin et
Üç çıktı satırını yaz:

```python
print(["a", "b", "c", "d"][-2:])
import math
print([round(math.sin(0), 6), round(math.cos(0), 6)])
uzunluklar = [4, 3, 2]
print(sum(uzunluklar[1:]))
```

???

```cikti
['c', 'd']
[0.0, 1.0]
5
```

İlk satır son iki tokenı, ikinci satır sıfır konumunu, üçüncü satır son iki mesajın bütçesini gösterir.
:::

::: gorev 1 · Tokenları pencere sınırına göre kırp
`pencere_kirp(tokenlar, sinir)` işlevini yaz. Tokenlar 1–8 öğeli, boş olmayan string listesidir; sınır bool olmayan 1–8 tamsayısıdır. Geçersiz veride `ValueError` yükselt.

Son `sinir` tokenı özgün sırayla yeni listede döndür. Sınır mevcut uzunluktan büyükse bütün listeyi kopyala; girdiyi değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-07")
```

```starter
from ai_temel_veri import json_yukle,metin_yukle

def pencere_kirp(tokenlar, sinir):
    # KUSURLU BAŞLANGIÇ KODU: son pencere yerine en eski tokenları korur.
    return list(tokenlar[:sinir])

v=json_yukle("veri/baglam.json")
print("Sentetik ham dosya:\n",metin_yukle("veri/baglam.json"))
print("Pencere:",pencere_kirp(v["tokenlar"],v["sinir"]))
```

```test
import copy
T = ["a", "b", "c", "d"]
def sozlesme(fn):
    try:
        if fn(T, 2) != ["c", "d"] or fn(T, 4) != T or fn(T, 8) != T or fn(T, 1) != ["d"]:
            return False
        if fn(["a"]*8, 1)!=["a"] or fn(["z"],8)!=["z"]:
            return False
        once=list(T)
        fn(T,2)
        if T!=once:return False
        sonuc = fn(T, 4)
        sonuc[0] = "x"
        if T[0] != "a" or fn(["a"], 1) != ["a"] or fn(["a"] * 8, 8) != ["a"] * 8:
            return False
        for args in [(None, 1), ([], 1), ([""], 1), ([1], 1), (T, 0), (T, 9), (T, True), (T, 1.0), (["a"] * 9, 1)]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(pencere_kirp), "son tokenlar, kopya ve pencere sınırı korunmalı")
def m_token(t, s):
    return pencere_kirp(list(reversed(t)), s)
def m_sinir(t, s):
    return pencere_kirp(t, 1)
def m_boyut(t, s):
    return pencere_kirp(t + ["x"], s)
for ad, mutant in [("sırayı bozan", m_token), ("sınırı bozan", m_sinir), ("boyutu bozan", m_boyut)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle,metin_yukle

def pencere_kirp(tokenlar, sinir):
    if not isinstance(tokenlar, list) or not 1 <= len(tokenlar) <= 8 or any(not isinstance(x, str) or not x for x in tokenlar):
        raise ValueError("tokenlar geçersiz")
    if not isinstance(sinir, int) or isinstance(sinir, bool) or not 1 <= sinir <= 8:
        raise ValueError("sınır geçersiz")
    return list(tokenlar[-sinir:])

v=json_yukle("veri/baglam.json")
print("Sentetik ham dosya:\n",metin_yukle("veri/baglam.json"))
print("Pencere:",pencere_kirp(v["tokenlar"],v["sinir"]))
```

```hint
Negatif dilim başlangıcı `tokenlar[-sinir:]` son öğeleri özgün sırayla verir.
```
:::

::: gorev 2 · İki boyutlu sinüzoidal konum üret
`konum_vektoru(pozisyon)` işlevini yaz. Pozisyon bool olmayan 0–127 tamsayısıdır; geçersiz veride `ValueError` yükselt.

`[sin(pozisyon), cos(pozisyon)]` değerlerini altı ondalığa yuvarlayarak döndür. Bu küçük fixture, sinüzoidal kodlamanın ilk iki boyutunu temsil eder.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-07")
```

```starter
from ai_temel_veri import json_yukle,metin_yukle

def konum_vektoru(pozisyon):
    # KUSURLU BAŞLANGIÇ KODU: kosinüs kanalı yerine sinüsü ikinci kez kullanır.
    import math
    return [round(math.sin(pozisyon),6),round(math.sin(pozisyon),6)]

v=json_yukle("veri/baglam.json")
print("Sentetik konumlar:",[(p,konum_vektoru(p)) for p in v["pozisyonlar"]])
```

```test
def sozlesme(fn):
    try:
        if fn(0) != [0.0, 1.0] or fn(1) != [0.841471, 0.540302] or fn(127) != [0.97263, 0.232359]:
            return False
        import math
        for p in [2,64,126]:
            if fn(p)!=[round(math.sin(p),6),round(math.cos(p),6)]:return False
        for deger in [None, True, 1.0, -1, 128]:
            try:
                fn(deger)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(konum_vektoru), "sinüs, kosinüs ve pozisyon sınırı korunmalı")
def m_pozisyon(p):
    return konum_vektoru(p + 1)
def m_sabit(p):
    return [0.0, 1.0]
for ad, mutant in [("pozisyonu kaydıran", m_pozisyon), ("sabit konum", m_sabit)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle,metin_yukle

def konum_vektoru(pozisyon):
    import math
    if not isinstance(pozisyon, int) or isinstance(pozisyon, bool) or not 0 <= pozisyon < 128:
        raise ValueError("pozisyon geçersiz")
    return [round(math.sin(pozisyon), 6), round(math.cos(pozisyon), 6)]

v=json_yukle("veri/baglam.json")
print("Sentetik konumlar:",[(p,konum_vektoru(p)) for p in v["pozisyonlar"]])
```

```hint
Aynı pozisyonu `math.sin` ve `math.cos` işlevlerine verip iki sonucu ayrı yuvarla.
```
:::

::: gorev 3 · Bağlam bütçesine sığan mesajları raporla
`baglam_sec(mesajlar, butce)` işlevini yaz. Mesajlar 1–8 öğeli listedir; her mesaj tam `id`, `rol`, `uzunluk` anahtarlarına sahiptir. Kimlikler birbirinden farklı, boş olmayan stringler; rol `system` veya `user`; uzunluk bool olmayan 1–8 tamsayısıdır. Bütçe bool olmayan 1–16 tamsayısıdır. Geçersiz veride `ValueError` yükselt.

Sondan başa doğru mesajları toplam uzunluk bütçeyi aşmadan ekle. Sığmayan ilk mesajda dur. `{"secilen":[...],"dusen":[...]}` döndür; her iki kimlik listesi de özgün mesaj sırasındadır. Girdileri değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-07")
```

```starter
from ai_temel_veri import json_yukle,metin_yukle

def baglam_sec(mesajlar,butce):
    # KUSURLU BAŞLANGIÇ KODU: sığmayan mesajı atlayıp daha eskilere gider; ardışıklık bozulur.
    secilen=[]
    kalan=butce
    for m in reversed(mesajlar):
        if m["uzunluk"] > kalan:
            continue
        secilen.insert(0,m["id"])
        kalan-=m["uzunluk"]
    return {"secilen":secilen,"dusen":[m["id"] for m in mesajlar if m["id"] not in secilen]}

v=json_yukle("veri/baglam.json")
print("Sentetik mesaj raporu:",baglam_sec(v["mesajlar"],v["butce"]))
print("Aralık tuzağı:",baglam_sec(v["aralik_ornegi"]["mesajlar"],v["aralik_ornegi"]["butce"]))
```

```test
import copy
M = [{"id": "s", "rol": "system", "uzunluk": 4}, {"id": "a", "rol": "user", "uzunluk": 3}, {"id": "b", "rol": "user", "uzunluk": 2}]
def sozlesme(fn):
    try:
        if fn(M, 5) != {"secilen": ["a", "b"], "dusen": ["s"]} or fn(M, 9) != {"secilen": ["s", "a", "b"], "dusen": []}:
            return False
        if fn(M, 2) != {"secilen": ["b"], "dusen": ["s", "a"]} or fn(M, 1) != {"secilen": [], "dusen": ["s", "a", "b"]} or fn(M, 16) != {"secilen": ["s", "a", "b"], "dusen": []}:
            return False
        once=copy.deepcopy(M)
        fn(M,5)
        if M!=once:return False
        trou=[{"id":"old","rol":"system","uzunluk":1},{"id":"big","rol":"user","uzunluk":8},{"id":"new","rol":"user","uzunluk":1}]
        if fn(trou,2)!={"secilen":["new"],"dusen":["old","big"]}:return False
        tek = {"id": "t", "rol": "user", "uzunluk": 1}
        sekiz = [dict(tek, id=str(i), uzunluk=1) for i in range(8)]
        if fn([tek], 1) != {"secilen": ["t"], "dusen": []} or fn([dict(tek, uzunluk=8)], 8)["secilen"] != ["t"] or len(fn(sekiz, 16)["secilen"]) != 8:
            return False
        for args in [(None, 5), ([], 5), ([["id", "rol", "uzunluk"]], 5), (sekiz + [dict(tek, id="9")], 16), (M, 0), (M, 17), (M, True), (M, "5"), ([dict(M[0], id=1)], 5), ([dict(M[0], id="")], 5), ([dict(M[0], rol="tool")], 5), ([dict(M[0], rol=1)], 5), ([dict(M[0], ek=1)], 5), ([dict(M[0], uzunluk="4")], 5), ([dict(M[0], uzunluk=True)], 5), ([dict(M[0], uzunluk=0)], 5), ([dict(M[0], uzunluk=9)], 9), ([M[0], M[0]], 9)]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
_sonu_buyuk = [
    {"id": "eski", "rol": "user", "uzunluk": 1},
    {"id": "son", "rol": "user", "uzunluk": 8},
]
eq(baglam_sec(_sonu_buyuk, 7), {"secilen": [], "dusen": ["eski", "son"]},
   "En yeni mesaj sığmazsa ardışık son ek boştur")
eq(baglam_sec(_sonu_buyuk, 8), {"secilen": ["son"], "dusen": ["eski"]},
   "En yeni mesaj bütçeyi tam doldurabilir")
raises(ValueError, baglam_sec, [dict(_sonu_buyuk[0], id="son"), _sonu_buyuk[1]], 8,
       msg="Düşecek eski mesajın kimliği de denetlenir")
ok(sozlesme(baglam_sec), "ardışık bağlam, bütçe ve düşen talimatlar korunmalı")
def m_mesaj(m, b):
    return baglam_sec(list(reversed(m)), b)
def m_butce(m, b):
    return baglam_sec(m, 16)
def m_boyut(m, b):
    return baglam_sec(m + [dict(m[-1], id="x")], b)
for ad, mutant in [("mesajları bozan", m_mesaj), ("bütçeyi bozan", m_butce), ("boyutu bozan", m_boyut)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle,metin_yukle

def baglam_sec(mesajlar, butce):
    if not isinstance(mesajlar, list) or not 1 <= len(mesajlar) <= 8:
        raise ValueError("mesaj listesi geçersiz")
    if any(not isinstance(m, dict) or set(m) != {"id", "rol", "uzunluk"} for m in mesajlar):
        raise ValueError("mesaj şeması geçersiz")
    if any(not isinstance(m["id"], str) or not m["id"] or m["rol"] not in ("system", "user") or not isinstance(m["uzunluk"], int) or isinstance(m["uzunluk"], bool) or not 1 <= m["uzunluk"] <= 8 for m in mesajlar):
        raise ValueError("mesaj değeri geçersiz")
    if len({m["id"] for m in mesajlar}) != len(mesajlar):
        raise ValueError("kimlikler yinelenemez")
    if not isinstance(butce, int) or isinstance(butce, bool) or not 1 <= butce <= 16:
        raise ValueError("bütçe geçersiz")
    secilen = []
    toplam = 0
    for m in reversed(mesajlar):
        if toplam + m["uzunluk"] > butce:
            break
        secilen.append(m["id"])
        toplam += m["uzunluk"]
    secilen.reverse()
    return {"secilen": secilen, "dusen": [m["id"] for m in mesajlar if m["id"] not in secilen]}

v=json_yukle("veri/baglam.json")
print("Sentetik mesaj raporu:",baglam_sec(v["mesajlar"],v["butce"]))
print("Aralık tuzağı:",baglam_sec(v["aralik_ornegi"]["mesajlar"],v["aralik_ornegi"]["butce"]))
```

```hint
Sondan gezerken toplam uzunluğu tut. Bütçe aşılırsa döngüyü kır; seçim listesini sonunda ters çevir.
```
:::

::: anlat Gerçek deney: pencereye metin değil token sığar
Önceki görevlerde mesaj uzunlukları hazır sayılardı. Şimdi kurulu küçük dil modelinin gerçek tokenizer'ı ve ileri hesabı kullanılacak. Deney metni ham kimliklere dönüştürür, sondaki tokenları korur, düşen token sayısını kaydeder ve kalan diziyle gerçek modelin sonraki-token logitlerini hesaplar. Sözcük veya karakter sayısıyla bütçe hesaplamak geçersizdir.

Bu deneyin bütçesi 1–32 token'dır; modelin gerçek `config.max_position_embeddings` sınırını ayrıca raporlarız. Kısa bütçe, laptopta hızlı ve tekrarlanabilir bir öğretim tercihidir; modelin bütün pencere kapasitesini veya uzun bağlam kalitesini sınadığımız anlamına gelmez. “Metni kestim, system talimatı güvende” gibi bir sonuç da çıkarılmaz; bu görev sohbet rolleri için koruma politikası uygulamaz.

Konumları kırpılmış girdide `0..N-1` olarak yeniden üretip modele açıkça `position_ids` ile vereceğiz. Bu modelin konum mekanizmasını kullanmak, önceki iki boyutlu sinüs tablosunu gerçek modelin mekanizması sanmak değildir. Dönen sayılar gerçek ağırlıklarla ileri hesaplanır. Test, yalnız raporlanan konumlara değil, modele gerçekte gönderilen tokenlara ve konumlara da bakar.
:::

::: gorev Gerçek deney · Token bütçesi, konumlar ve gerçek ileri hesap
`gercek_baglam_raporu(metin, butce)` işlevini yaz:

- `metin` boşluk dışı karakter içeren bir `str`, `butce` bool olmayan 1–32 aralığında `int` olsun. Aksi hâlde `ValueError` yükselt. Metni normalize etme veya kırpma.
- `tok, model, bilgi = ai_lab.dil_modeli()` ile kurulu modeli al. Gerçek model sınırını `int(model.config.max_position_embeddings)` ile oku. Bütçe bu sınırı da aşamaz.
- Özel token eklemeden elde edilen **tam** kimlik listesinin son `butce` tokenını koru. Başlangıç sayısı ile korunan sayıdan düşen sayıyı hesapla.
- `position_ids`, korunan token sayısına göre `[[0, 1, ..., N-1]]` olsun. `torch.no_grad()` içinde gerçek modeli bu kimlikler ve konumlarla, `use_cache=False` vererek çalıştır.
- Son konumun ham logitlerini double'a dönüştür. Tam şu sözlüğü döndür: `model_siniri`, `girdi_token_sayisi`, `dusen_token_sayisi`, `token_idleri`, `konumlar`, `en_olasi_id` (son logitlerin argmax'ı, int), `ornek_logitler` (son konumun sözlükteki ilk 8 tokenına ait float logitler).

`konumlar` düz bir int listesidir. Bütçe aşılırsa başı değil sonu koru, sırayı değiştirme. `ornek_logitler` ilk konumdan alınamaz. Teste ait referans işlevi çağırma. Model/bağımlılık yoksa bu adım geçmez; indirme yapmaz.

```meta
motor: ai-gercek
gereksinim: torch
timeout: 240
```

```starter
import ai_lab

def gercek_baglam_raporu(metin, butce):
    return {}

if ai_lab.CALISTIR:
    from sandbox.ai_gercek_ai_temel_07 import goster
    goster(gercek_baglam_raporu)
```

```test
import copy
import random
import ai_lab

sonuclar = []
def kontrol(c, mesaj):
    sonuclar.append(bool(c))
    return ok(c, mesaj)
import ast
yasak=("referans", "getattr", "kanit_yaz")
ihlal=ai_lab.kod_denetimi(src,yasak=yasak)
try:
    for node in ast.walk(ast.parse(src)):
        if isinstance(node,ast.ImportFrom) and any(a.name in yasak or a.name=="*" for a in node.names):
            ihlal.append("kendi raporunu yaz; referans ithali yasak")
except SyntaxError:
    ihlal.append("sözdizimi")
kontrol(not ihlal,"Kendi bağlam hesabını yaz; referans ve kanıt yordamı çağrılamaz")
if ihlal:stop()
fn = need("gercek_baglam_raporu")
try:
    import torch
    tok, model, bilgi = ai_lab.dil_modeli()
except (ImportError, ai_lab.GercekLabYok) as e:
    kontrol(False, "GERÇEK MODEL YOK: " + str(e))
    stop()

rng = random.SystemRandom()
metinler = ["The original rule is blue. The latest note is green.",
            "  İstanbul is a city; a model reads tokens, not words.",
            "A " + str(rng.randrange(1000,9999)) + " " + rng.choice(["river", "forest", "city"]) + " message with a final word."]
ayarlar = [(metinler[0], 1), (metinler[0], 4), (metinler[1], 8), (metinler[2], 32), (" the"*40,32)]

def hesap(m, b, bas=False, ters=False, ilk=False, sifir=False):
    tum = tok(m, add_special_tokens=False)["input_ids"]
    ids = tum[:b] if bas else tum[-b:]
    if ters:
        ids = list(reversed(ids))
    konum = [0] * len(ids) if sifir else list(range(len(ids)))
    with torch.no_grad():
        logits = model(torch.tensor([ids]), position_ids=torch.tensor([konum]), use_cache=False).logits[0, 0 if ilk else -1].double()
    return {"model_siniri": int(model.config.max_position_embeddings), "girdi_token_sayisi": len(tum),
            "dusen_token_sayisi": len(tum)-len(ids), "token_idleri": ids, "konumlar": konum,
            "en_olasi_id": int(logits.argmax().item()), "ornek_logitler": logits[:8].tolist()}
beklenen = [hesap(m,b) for m,b in ayarlar]

def ayni(a,b):
    if not isinstance(a, dict) or set(a)!=set(b):
        return False
    for k in ["model_siniri", "girdi_token_sayisi", "dusen_token_sayisi", "en_olasi_id"]:
        if type(a[k]) is not int or a[k]!=b[k]:
            return False
    for k in ["token_idleri", "konumlar"]:
        if not isinstance(a[k], list) or any(type(i) is not int for i in a[k]) or a[k]!=b[k]:
            return False
    vals=a["ornek_logitler"]
    return isinstance(vals,list) and len(vals)==8 and all(type(x) is float for x in vals) and bool(torch.isfinite(torch.tensor(vals)).all()) and torch.allclose(torch.tensor(vals,dtype=torch.float64),torch.tensor(b["ornek_logitler"],dtype=torch.float64),atol=1e-4,rtol=1e-5)

def sozlesme(f):
    try:
        for (m,b),ref in zip(ayarlar,beklenen):
            cagrilar=[]
            def izle(modul, args, kwargs):
                ids = args[0] if args else kwargs.get("input_ids")
                pos = kwargs.get("position_ids")
                cagrilar.append({"ids": ids.detach().tolist() if isinstance(ids,torch.Tensor) else None,
                                 "konumlar": pos.detach().tolist() if isinstance(pos,torch.Tensor) else None,
                                 "use_cache": kwargs.get("use_cache"),"grad_acik":torch.is_grad_enabled()})
            handle=model.register_forward_pre_hook(izle, with_kwargs=True)
            try:
                a=f(m,b)
            finally:
                handle.remove()
            if not ayni(a,ref):
                return False
            hedef={"ids":[ref["token_idleri"]],"konumlar":[ref["konumlar"]],"use_cache":False,"grad_acik":False}
            if hedef not in cagrilar:
                return False
        for args in [("",1),("   ",1),(None,1),(True,1),("hi",0),("hi",33),("hi",True),("hi",1.0)]:
            try:
                f(*args)
                return False
            except ValueError:
                pass
        from unittest.mock import patch as _patch
        class _Cfg:
            max_position_embeddings = 8
        class _Out:
            def __init__(self):
                self.logits = torch.arange(24, dtype=torch.float32).reshape(1, 3, 8)
        class _Mdl:
            config = _Cfg()
            def __call__(self, input_ids, position_ids=None, use_cache=None):
                n_tok = int(input_ids.shape[1])
                z = torch.zeros((1, n_tok, 8), dtype=torch.float32)
                z[0, -1, 3] = 5.0
                o = _Out(); o.logits = z
                return o
        def _tok(txt, add_special_tokens=True):
            if add_special_tokens is not False:
                return {"input_ids": [99, 1, 2]}
            if txt == "BOS_TOK":
                return {"input_ids": []}
            return {"input_ids": [4, 5, 6]}
        with _patch.object(ai_lab, "dil_modeli", return_value=(_tok, _Mdl(), {})):
            r_sinir = f("normal", 8)
            if r_sinir["model_siniri"] != 8 or r_sinir["token_idleri"] != [4, 5, 6] or r_sinir["en_olasi_id"] != 3:
                return False
            for k_args in [("normal", 9), ("BOS_TOK", 4)]:
                try:
                    f(*k_args)
                    return False
                except ValueError:
                    pass
        return True
    except Exception:
        return False

kontrol(sozlesme(fn), "gerçek ileri hesap: son token penceresi, gerçek position_ids ve son konum logitleri doğru")
def gecerli(hata=None):
    def f(m,b):
        if not isinstance(m,str) or not m.strip() or type(b) is not int or not 1<=b<=32:
            raise ValueError("girdi")
        return hesap(m,b,**(hata or {}))
    return f
sabit=copy.deepcopy(beklenen[0])
for ad,mutant in [("boş kod/işlev",None),("boş sözlük",lambda m,b:{}),
                  ("sabit gerçek sonuç",lambda m,b:copy.deepcopy(sabit)),
                  ("son yerine ilk tokenlar",gecerli({"bas":True})),
                  ("token sırasını ters çevirme",gecerli({"ters":True})),
                  ("ilk konumun logitleri",gecerli({"ilk":True})),
                  ("bütün konumları sıfırlama",gecerli({"sifir":True}))]:
    kontrol(not sozlesme(mutant), "hatalı çözüm reddedilmeli: "+ad)

ciktilar=[fn(m,b) for m,b in ayarlar] if all(sonuclar) else []
kontrol(any(d["dusen_token_sayisi"]>0 for d in ciktilar), "en az bir gerçek girdi bütçe yüzünden kırpıldı")
kontrol(any(d["dusen_token_sayisi"]==0 for d in ciktilar), "sığan gerçek girdi de sınandı")
ai_lab.kanit_yaz("temel-07-baglam",{
    "kaynak":"gercek","kabul":all(sonuclar),"model_bilgisi":bilgi,
    "ayarlar":{"girdiler":[list(a) for a in ayarlar],"deney_butce_ust_siniri":32,"use_cache":False},
    "ciktilar":ciktilar,"olculen":"gerçek tokenizasyon, konumlarla ileri hesap ve kısa pencere kırpması",
    "sinir":"tam context kapasitesi veya uzun bağlam doğruluğu kabulü yapılmadı",
    "temizlik":"CPU işlemi; kalıcı sunucu, model indirme ve dış süreç yok"})
for (m,b),d in zip(ayarlar,ciktilar):
    print("bütçe",b,"model sınırı",d["model_siniri"],"düşen",d["dusen_token_sayisi"],"tokenlar",d["token_idleri"],"konumlar",d["konumlar"],"sonraki kimlik",d["en_olasi_id"])
```

```solution
import ai_lab
import torch

def gercek_baglam_raporu(metin, butce):
    if not isinstance(metin,str) or not metin.strip() or type(butce) is not int or not 1<=butce<=32:
        raise ValueError("geçersiz metin veya bütçe")
    tok, model, _=ai_lab.dil_modeli()
    sinir=int(model.config.max_position_embeddings)
    if butce>sinir:
        raise ValueError("model sınırı aşılıyor")
    tum=tok(metin,add_special_tokens=False)["input_ids"]
    if not tum:
        raise ValueError("token yok")
    ids=tum[-butce:]
    konum=list(range(len(ids)))
    with torch.no_grad():
        logits=model(torch.tensor([ids]),position_ids=torch.tensor([konum]),use_cache=False).logits[0,-1].double()
    return {"model_siniri":sinir,"girdi_token_sayisi":len(tum),"dusen_token_sayisi":len(tum)-len(ids),
            "token_idleri":ids,"konumlar":konum,"en_olasi_id":int(logits.argmax().item()),
            "ornek_logitler":logits[:8].tolist()}

if ai_lab.CALISTIR:
    from sandbox.ai_gercek_ai_temel_07 import goster
    goster(gercek_baglam_raporu)
```

```hint
Önce tam kimlik sayısını al, sonra `tum[-butce:]` uygula. Model girdisi `[1,N]`, konum tensörü de `[1,N]` olmalı. Sonraki token için son konum logitleri kullanılır; raporladığın konumların modele de gerçekten gitmesi gerekir.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Pencereye karakter değil token sığar (25 sn).** "Bağlam penceresi sonlu bir token bütçesidir; bütçe aşıldığında kırpma kuralı baştaki mesajları düşürürse sistem kuralları veya güvenlik kısıtları sessizce pencere dışına itilebilir."
2. **Sırasız dikkat ve konumsal kodlama (35 sn).** "Saf öz-dikkat (`self-attention`) küme işlemidir; sinüzoidal veya döndürmeli (`RoPE`) konumsal temsil eklenmezse model `'A B'yi sildi'` ile `'B A'yı sildi'` dizilerini ayırt edemez."
3. **Düşen talimat denetimi (35 sn).** "Güvenli bağlam yöneticisi yalnız sığan son ek dilimini modele göndermekle yetinmez; pencereden düşen her talimat kimliğini açıkça raporlar."
4. **Soru (25 sn).** "Uzun bir kullanıcı belgesi bağlam bütçesini doldurduğunda sistem isteminin asla düşmemesi için pencere bütçesini nasıl bölersin?"
:::
