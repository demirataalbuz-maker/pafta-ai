---
id: ai-temel-06
title: "Çok Başlı Attention ve Nedensel Maskeleme"
summary: Temsili attention başlıklarına ayır, nedensel maske uygula ve yalnız izinli tokenlardan bağlam üret.
esleme: ai-temel-05, ai-temel-07, ai-temel-08
timeout: 45
---

::: anlat Her başlık farklı bir alt uzaya bakar

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Modelin öğrenilmiş Q/K/V projeksiyonları, konum bilgisi ve kafa bazlı dikkat hesabı | İlk üç görevde görünür sentetik vektör/skor JSON'u; son görevde kurulu SmolLM2 katmanından çıkarılan gerçek Q/K/V ve katman çıktısı | Dört sayılık dilimleme bütün Transformer katmanı veya model davranışının açıklaması değildir |
| Nedensel maske gelecek konumları softmax hesabından çıkarır | Önce None ile temsil, sonra gerçek tensörlerde softmax öncesi -inf ve model logit karşılaştırması | None gerçek attention tensöründeki değer değildir; maske rol/izin/prompt injection güvenlik duvarı değildir |

> [!NOT]
> `veri/attention.json` elle hazırlanmış **sentetik** örnektir, modelden alınmış çıktı değildir. İlk üç görev aynı dosyayı okur. Setup her çalıştırmada geçici kopya üretir; değişiklikler kalıcı değildir. Kaynak fixture dosyasını editörle açabilir, ders kodunda yüklenen listenin kopyasını değiştirerek Run ile sonucu gözleyebilirsin. Gizli testler ayrı girdilerdir. Son görev gerçek tokenizer/model ve PyTorch ile CPU'da çalışır; ders indirme yapmaz.

Çok başlı attention temsil vektörünü daha küçük parçalara ayırır ve dikkat hesabını her parçada ayrı yapar. Böylece başlıklar farklı ilişkileri yakalayabilir. Başlık sayısı vektör boyutunu tam bölmelidir; parçaların sırası korunur.

Görevler 1–3 sentetik Python verisiyle çalışır; son görev gerçek PyTorch tensörlerini ve kurulu model katmanını çalıştırır. Dört boyutlu sabit vektörler ve iki boyutlu başlıklar, çok başlı yapının veri akışını görünür kılar. Başlıkları birleştirmek, parçaları aynı sırada art arda eklemektir.
:::

::: anlat Nedensel maske geleceği kapatır

Önce `veri/attention.json` dosyasını aç. `vektor` ve `kafa_sayisi` parçalama görevini, `skorlar` ve `pozisyon` iki maske görevini besler. Son skor diğerlerinden bilerek çok büyüktür. Pozisyon birken üçüncü token gelecekte kaldığı için bu büyük sayı, geçmişin olasılıklarını etkilememelidir. Maskeyi yanlış yerde uygularsan farkı ham veride ve çıktıda açıkça görürsün. Aynı dosyayı kullanmak, listelerin parçalanmasıyla dikkat hesabının bütününü aynı şey sanmayı gerektirmez; bunlar ayrı hazırlık adımlarıdır.

Gerçek katmanda önce öğrenilmiş doğrusal projeksiyonlar Query, Key ve Value üretir. Modelin konum bilgisi de Q/K hesabına uygulanır. Sonra kafalar uygun sütun parçalarına ayrılır. Bu dersteki GQA modelinde bazı Key/Value kafaları bir grup Query kafası tarafından paylaşılır; laboratuvar grup eşleşmesini koruyarak onları karşılaştırılabilir biçime genişletir. Öğrenciye verilen q/k/v artık bu gerçek hazırlıktan geçmiş tensörlerdir. Dört boyutlu sentetik vektör ise yalnız ardışık bölme ve sıra kavramını öğretir.

Bir kafanın skoru q_h ile k_h transpozunun çarpımıdır. Ölçek bütün temsil boyutunun değil, o kafanın boyutunun kareköküdür. Çok sayıda bileşenin çarpım toplamı büyüdüğünde softmax gereğinden keskinleşebilir; ölçek bu hesabın parçasıdır. Her satır bir sorgu konumunun aday geçmiş konumlara dağılımıdır. Maskeli sütunları toplamın dışında bırakmak gerekir. Önce bütün skorlara softmax uygulayıp sonra geleceği sıfırlarsan, gelecekteki tokenlar paydada zaten etkili olmuştur. Kalan ağırlıkların toplamı birin altına iner ve bağlam küçülür.

Nedensel maske geleceği kapatır, mevcut tokenı kapatmaz. Bu yüzden pozisyon sıfırda yalnız ilk tokena ağırlık bir verilir. Son pozisyonda bütün geçmiş ve mevcut token görünür olabilir. Sentetik skor görevindeki None yalnız gösterim işaretidir; gerçek PyTorch hesabı maskelenen skoru eksi sonsuz yapar. Girdi skorlarının sonlu olması ayrı sözleşmedir: öğrencinin verdiği NaN veya sonsuz değer, modelin uyguladığı maske işaretiyle karıştırılmaz.

Bağlam, izinli Value vektörlerinin dikkat ağırlıklarıyla karışımıdır. Her kafa kendi bağlamını üretir; sonuçlar orijinal kafa sırasıyla yan yana birleştirilir. Toplamak veya sırayı ters çevirmek biçim olarak makul görünse bile model katmanının beklediği çıktıyı değiştirir. Son projeksiyon bu birleşik bağlamdan sonra gelir. Laboratuvar bu yüzden birleşik sonucu çıkış projeksiyonunun girişinde yakalanmış gerçek model değeriyle karşılaştırır; bütün katmanın ya da son logitlerin aynı olduğunu iddia etmez.

Bir saldırganın istemdeki geçmiş tokenları değiştirmesi, modelin dikkat dağılımını etkileyebilir. Nedensel maske bu tokenların güvenilir olduğunu denetlemez; yalnız zaman yönünü sınırlar. Geçmişte duran kötü niyetli belge hâlâ görünürdür. Savunmanın yalnız dikkat haritasına bakarak bir belgeyi güvenli ilan etmesi bu nedenle yanlıştır. En büyük attention ağırlığı da tek başına anlamsal önem veya kararın nedeni değildir. Ekrandaki kafa özetinde ilk tokenın ayrı tutulduğu açıkça yazılır; bu seçilmiş özet bütün dağılımın yerine geçmez.

Gerçek nedensellik kontrolünde son kelime değiştirilir, tokenizer'ın gerçekten ortak kalan öneki bulunur ve önceki konumların logitleri karşılaştırılır. Son konumun farkı da ayrıca raporlanır. Böylece etkisiz bir değişikliği yanlışlıkla güçlü test saymayız. Hesap float64 referansla ve modelin gerçek float32 çıktısıyla ayrı toleranslar kullanır. İlk üç görevdeki altı haneli yuvarlama gerçek tensör görevine taşınmaz. Çıktının biçimini tutturmak, doğru dtype ve gerçek sayısal eşdeğerliğin yerine geçmez.

Autoregressive üretimde pozisyon `i`, yalnız `0..i` arasındaki tokenlara bakabilir. Gelecek pozisyonların skoru softmax öncesinde eksi sonsuz yapılır; sentetik uygulamada bu skorları `None` ile göstereceğiz.

Maske yalnız skorları değil, softmax normalizasyonunu da etkiler. Gelecek tokenlar payda hesabına girmemelidir. Aksi halde eğitim sırasında cevap sızar ve değerlendirme gerçek üretim koşulunu ölçmez.
:::

::: tahmin Başlık ve maskeyi tahmin et
Üç çıktı satırını yaz:

```python
v = [1, 2, 3, 4]
print([v[:2], v[2:]])
print([0.4, 0.3, None] if 1 < 2 else [0.4, 0.3, 0.2])
print(round(0.25 * 2 + 0.75 * 6, 6))
```

???

```cikti
[[1, 2], [3, 4]]
[0.4, 0.3, None]
5.0
```

İlk satır iki başlığı, ikinci satır gelecek skorunun maskelenmesini, üçüncü satır iki izinli Value değerinin karışımını gösterir.
:::

::: gorev 1 · Dört boyutlu temsili başlıklara ayır
`kafa_ayir(vektor, kafa_sayisi)` işlevini yaz. Vektör dört adet sonlu, bool olmayan int/float içerir. Başlık sayısı bool olmayan 1, 2 veya 4 tamsayısıdır. Geçersiz veride `ValueError` yükselt.

Vektörü eşit ve ardışık parçalara ayırıp yeni listeler olarak döndür. Girdiyi değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-06")
```

```starter
from ai_temel_veri import json_yukle

def kafa_ayir(vektor,kafa_sayisi):
    # KUSURLU BAŞLANGIÇ KODU: ardışık dilimler yerine atlamalı sütunlar toplar.
    return [vektor[h::kafa_sayisi] for h in range(kafa_sayisi)]

v=json_yukle("veri/attention.json")
print("Sentetik veri:",v)
print("Başlıklar:",kafa_ayir(v["vektor"],v["kafa_sayisi"]))
```

```test
def sozlesme(fn):
    try:
        if fn([1, 2, 3, 4], 2) != [[1, 2], [3, 4]] or fn([1, 2, 3, 4], 1) != [[1, 2, 3, 4]] or fn([1, 2, 3, 4], 4) != [[1], [2], [3], [4]]:
            return False
        source=[1,2,3,4]
        split=fn(source,1)
        split[0][0]=99
        if source != [1,2,3,4] or fn([-2.5,0.0,7.5,1],2)!=[[-2.5,0.0],[7.5,1]]:
            return False
        for args in [([1,2,float("nan"),4],2),([1,2,float("inf"),4],2),(["a",2,3,4],2),(None, 2), ([1, 2], 2), ([1, 2, True, 4], 2), ([1, 2, 3, 4], 0), ([1, 2, 3, 4], 2.0), ([1, 2, 3, 4], 3), ([1, 2, 3, 4], 5), ([1, 2, 3, 4], True)]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(kafa_ayir), "başlık boyutu, sırası ve şeması korunmalı")
def m_vektor(v, k):
    return kafa_ayir(list(reversed(v)), k)
def m_kafa(v, k):
    return kafa_ayir(v, 1)
def m_boyut(v, k):
    return kafa_ayir(v + [0], k)
for ad, mutant in [("vektörü bozan", m_vektor), ("başlık sayısını bozan", m_kafa), ("boyutu bozan", m_boyut)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle
def kafa_ayir(vektor, kafa_sayisi):
    import math
    if not isinstance(vektor, list) or len(vektor) != 4 or any(not isinstance(x, (int, float)) or isinstance(x, bool) or not math.isfinite(x) for x in vektor):
        raise ValueError("vektör geçersiz")
    if not isinstance(kafa_sayisi, int) or isinstance(kafa_sayisi, bool) or kafa_sayisi not in (1, 2, 4):
        raise ValueError("başlık sayısı geçersiz")
    boyut = len(vektor) // kafa_sayisi
    return [list(vektor[i * boyut:(i + 1) * boyut]) for i in range(kafa_sayisi)]
if __name__ == "__main__":
    v=json_yukle("veri/attention.json")
    print("Sentetik veri:",v)
    print("Başlıklar:",kafa_ayir(v["vektor"],v["kafa_sayisi"]))

```

```hint
Başlık boyutunu `4 // kafa_sayisi` ile bul ve ardışık dilimler oluştur.
```
:::

::: gorev 2 · Nedensel skor maskesi uygula
`nedensel_skorlar(skorlar, pozisyon)` işlevini yaz. Skorlar üç sonlu, bool olmayan int/float sayıdan, pozisyon bool olmayan 0, 1 veya 2 tamsayısından oluşur. Geçersiz veride `ValueError` yükselt.

İndeksi pozisyondan büyük olan skorları `None` yap; diğer skorları aynı sayısal değerle koru. Yeni üç öğeli liste döndür ve girdiyi değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-06")
```

```starter
from ai_temel_veri import json_yukle

def nedensel_skorlar(skorlar,pozisyon):
    # KUSURLU BAŞLANGIÇ KODU: gelecek skoru None ile dışlamak yerine normal bir sıfır skoru yapar.
    return [x if i<=pozisyon else 0.0 for i,x in enumerate(skorlar)]

v=json_yukle("veri/attention.json")
print("Sentetik veri:",v)
print("Skor maskesi:",nedensel_skorlar(v["skorlar"],v["pozisyon"]))
```

```test
def sozlesme(fn):
    try:
        if fn([0.2, 0.3, 0.4], 0) != [0.2, None, None] or fn([0.2, 0.3, 0.4], 1) != [0.2, 0.3, None] or fn([0.2, 0.3, 0.4], 2) != [0.2, 0.3, 0.4]:
            return False
        source=[-4,0,9]
        result=fn(source,2)
        if result is source or source!=[-4,0,9]:
            return False
        result[0]=99
        if source!=[-4,0,9]:
            return False
        for args in [([float("nan"),1,2],0),([0,1,float("inf")],1),(["a",1,2],0),(None, 0), ([1, 2], 0), ([1, True, 3], 0), ([1, 2, 3], 1.0), ([1, 2, 3], -1), ([1, 2, 3], 3), ([1, 2, 3], True)]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(nedensel_skorlar), "gelecek maskesi ve pozisyon sınırı korunmalı")
def m_skor(s, p):
    return nedensel_skorlar(list(reversed(s)), p)
def m_pozisyon(s, p):
    return nedensel_skorlar(s, 2)
def m_boyut(s, p):
    return nedensel_skorlar(s + [0], p)
for ad, mutant in [("skorları bozan", m_skor), ("maskeyi kaldıran", m_pozisyon), ("boyutu bozan", m_boyut)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle
def nedensel_skorlar(skorlar, pozisyon):
    import math
    if not isinstance(skorlar, list) or len(skorlar) != 3 or any(not isinstance(x, (int, float)) or isinstance(x, bool) or not math.isfinite(x) for x in skorlar):
        raise ValueError("skorlar geçersiz")
    if not isinstance(pozisyon, int) or isinstance(pozisyon, bool) or not 0 <= pozisyon < 3:
        raise ValueError("pozisyon geçersiz")
    return [x if i <= pozisyon else None for i, x in enumerate(skorlar)]
if __name__ == "__main__":
    v=json_yukle("veri/attention.json")
    print("Sentetik veri:",v)
    print("Skor maskesi:",nedensel_skorlar(v["skorlar"],v["pozisyon"]))

```

```hint
`enumerate` indeksini pozisyonla karşılaştır; indeks pozisyondan büyükse `None` döndür.
```
:::

::: gorev 3 · Maskeli attention ağırlıklarını hesapla
`nedensel_agirliklar(skorlar, pozisyon)` işlevini yaz. Girdiler ikinci görevdeki biçimdedir. Geçersiz veride `ValueError` yükselt.

Gelecek skorlarını dışlayarak kalan skorlara kararlı softmax uygula. Sonuç üç öğeli listedir; maskeli konumlarda tam `0.0`, diğerlerinde altı ondalığa yuvarlanmış ağırlık bulunur. Girdileri değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-06")
```

```starter
from ai_temel_veri import json_yukle
import math

def nedensel_agirliklar(skorlar,pozisyon):
    # KUSURLU BAŞLANGIÇ KODU: geleceği softmax paydasına kattıktan sonra ağırlığını sıfırlar.
    tepe=max(skorlar)
    pay=[math.exp(x-tepe) for x in skorlar]
    toplam=sum(pay)
    return [round(x/toplam,6) if i<=pozisyon else 0.0 for i,x in enumerate(pay)]

v=json_yukle("veri/attention.json")
print("Sentetik veri:",v)
print("Dikkat ağırlıkları:",nedensel_agirliklar(v["skorlar"],v["pozisyon"]))
```

```test
def sozlesme(fn):
    try:
        if fn([0, 0, 0], 0) != [1.0, 0.0, 0.0] or fn([0, 0, 0], 1) != [0.5, 0.5, 0.0] or fn([0, 0, 0], 2) != [0.333333, 0.333333, 0.333333]:
            return False
        if fn([0, 1, 100], 1) != [0.268941, 0.731059, 0.0] or fn([1000, 1000, 0], 1) != [0.5, 0.5, 0.0]:
            return False
        source=[0.0,1.0,1000.0]
        if fn(source,1)!=[0.268941,0.731059,0.0] or source!=[0.0,1.0,1000.0] or fn([0,1,-1000],1)!=[0.268941,0.731059,0.0]:
            return False
        for args in [([float("nan"),1,2],0),([0,1,float("inf")],1),(["a",1,2],0),(None, 0), ([1, 2], 0), ([1, True, 3], 0), ([1, 2, 3], None), ([1, 2, 3], True), ([1, 2, 3], -1), ([1, 2, 3], 3)]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(nedensel_agirliklar), "maskeli softmax ve sıfır gelecek ağırlığı korunmalı")
def m_skor(s, p):
    return nedensel_agirliklar(list(reversed(s)), p)
def m_pozisyon(s, p):
    return nedensel_agirliklar(s, 2)
def m_boyut(s, p):
    return nedensel_agirliklar(s + [0], p)
for ad, mutant in [("skorları bozan", m_skor), ("geleceği açan", m_pozisyon), ("boyutu bozan", m_boyut)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle
def nedensel_agirliklar(skorlar, pozisyon):
    import math
    if not isinstance(skorlar, list) or len(skorlar) != 3 or any(not isinstance(x, (int, float)) or isinstance(x, bool) or not math.isfinite(x) for x in skorlar):
        raise ValueError("skorlar geçersiz")
    if not isinstance(pozisyon, int) or isinstance(pozisyon, bool) or not 0 <= pozisyon < 3:
        raise ValueError("pozisyon geçersiz")
    izinliler = skorlar[:pozisyon + 1]
    tepe = max(izinliler)
    paylar = [math.exp(x - tepe) for x in izinliler]
    toplam = sum(paylar)
    return [round(math.exp(x - tepe) / toplam, 6) if i <= pozisyon else 0.0 for i, x in enumerate(skorlar)]
if __name__ == "__main__":
    v=json_yukle("veri/attention.json")
    print("Sentetik veri:",v)
    print("Dikkat ağırlıkları:",nedensel_agirliklar(v["skorlar"],v["pozisyon"]))

```

```hint
Softmax paydasını yalnız `skorlar[:pozisyon + 1]` üzerinden hesapla; gelecek konumları sonradan sıfırla.
```
:::

::: anlat Gerçek modelde çok başlı dikkat
SmolLM2-135M'nin her katmanında 576 boyutlu temsil 9 kafaya, her biri 64 boyutlu ardışık parçalara bölünür. Her kafa kendi nedensel dikkatini hesaplar; sonuçlar aynı sırayla yan yana eklenip katmanın çıkış projeksiyonuna gider. Bu modelde Key/Value kafaları gruplar hâlinde paylaşılır (GQA); laboratuvar her Query kafasının kendi grubundaki Key/Value'yu görmesi için onları 576 boyuta genişletir.

Nedensel maske eğitimde cevabın sızmasını engeller. Bunun gerçek modeldeki sonucu ölçülebilir: yalnız **son** kelimeyi değiştirdiğinde önceki bütün konumların çıktısı aynı kalmalıdır.

Kaynaklar: [Vaswani vd. 2017 — Attention Is All You Need (arXiv:1706.03762)](https://arxiv.org/abs/1706.03762), [Ainslie vd. 2023 — GQA: Training Generalized Multi-Query Transformer Models (arXiv:2305.13245)](https://arxiv.org/abs/2305.13245).
:::

::: gorev Gerçek deney · Gerçek bir katmanda çok başlı nedensel dikkat
`cok_basli_dikkat(q, k, v, kafa_sayisi)` işlevini yaz. `q`, `k`, `v` aynı biçimde `[T, D]` `torch.Tensor`'lardır; `D = kafa_sayisi × d`.

- Doğrulama, aksi hâlde `ValueError`: üçü de 2 boyutlu, aynı biçimde, sonlu değerli `torch.Tensor`; T ≥ 1 ve D ≥ 1; `kafa_sayisi` bool olmayan, D'yi tam bölen pozitif `int`.
- Hesabı **float64** yap. Her tensörü kafalara **ardışık** böl: kafa `h`, `[:, h*d:(h+1)*d]` sütunlarıdır.
- Her kafada `q_h @ k_hᵀ / √d` (d kafa boyutu, D değil), gelecek tokenları softmax'tan önce `-inf` ile maskele, satır softmax'ı, `agirlik @ v_h`.
- Kafaların bağlamlarını aynı sırayla yan yana birleştir.
- Döndür: `{"agirliklar": [H, T, T] tensör, "baglam": [T, D] tensör}`.

Test rastgele bir cümlede rastgele katmanlar seçer; birleşik bağlamını bağımsız bir hesapla ve **modelin o katmandaki gerçek çıktısıyla** karşılaştırır, son tokenı bozarak nedenselliği sınar. Çalıştır düğmesi kafaların son tokendan nereye baktığını ve gerçek modelde nedensellik ölçümünü gösterir. `referans`, `katman_girdileri` ya da PyTorch'un hazır dikkat işlevini çağırma.

```meta
motor: ai-gercek
gereksinim: torch
timeout: 240
```

```starter
import torch
import ai_lab

def cok_basli_dikkat(q, k, v, kafa_sayisi):
    return {"agirliklar": None, "baglam": None}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_06 as deney
    deney.goster(cok_basli_dikkat)
```

```test
import random
import ai_lab
sonuclar = []
def kontrol(kosul, mesaj):
    sonuclar.append(bool(kosul))
    return ok(kosul, mesaj)
import ast
_yasak=("referans","katman_girdileri","kafa_ozeti","nedensellik","kanit_yaz","scaled_dot_product_attention","MultiheadAttention")
sorun=ai_lab.kod_denetimi(src,yasak=_yasak)
for n in ast.walk(ast.parse(src)):
    if isinstance(n,ast.ImportFrom) and any(a.name in _yasak or a.name=="*" for a in n.names):
        sorun.append("referans/hazır dikkat importu yasak")
if not kontrol(not sorun,"Kendi çok başlı dikkat işlevini yaz: "+"; ".join(sorun)):
    stop()
fn = need("cok_basli_dikkat")
try:
    from sandbox import ai_gercek_ai_temel_06 as D
    tok, model, bilgi = ai_lab.dil_modeli()
    import torch
except ai_lab.GercekLabYok as e:
    kontrol(False, f"GERÇEK MODEL YOK, deney yapılmadı: {e}")
    stop()
rnd = random.Random()
L = model.config.num_hidden_layers
ozne = ["The pilot", "My neighbour", "The tired student", "A quiet engineer", "The new manager"]
nesne = ["the report", "the old map", "a red umbrella", "the server logs", "the final exam"]
rastgele = f"{rnd.choice(ozne)} checked {rnd.choice(nesne)} before the meeting"
vakalar = [(D.DENEY_METNI, 4), (D.DENEY_METNI, 0), (rastgele, rnd.randrange(L)), (rastgele, rnd.randrange(L))]
girdiler = [D.katman_girdileri(m, kat) for m, kat in vakalar]
def ayni(a, b):
    if not isinstance(a, dict) or set(a) != {"agirliklar", "baglam"}:
        return False
    for ad in ("agirliklar", "baglam"):
        x, y = a[ad], b[ad]
        if not isinstance(x, torch.Tensor) or x.shape != y.shape or x.dtype!=torch.float64 or not torch.isfinite(x).all():
            return False
        if (x.double() - y).abs().max().item() > 1e-9:
            return False
    return True
def sozlesme(f):
    try:
        for q, k, v, _, _, H in girdiler:
            if not ayni(f(q.clone(), k.clone(), v.clone(), H), D.referans(q, k, v, H)):
                return False
        q, k, v, _, _, H = girdiler[0]
        t1 = torch.tensor([[2.0]])
        t34 = torch.arange(12, dtype=torch.float64).reshape(3, 4)
        if not ayni(f(t1.clone(), t1.clone(), t1.clone(), 1), D.referans(t1, t1, t1, 1)) or not ayni(f(t34.clone(), t34.clone(), t34.clone(), 2), D.referans(t34, t34, t34, 2)):
            return False
        if not ayni(f(q.clone(), k.clone(), v.clone(), 3), D.referans(q, k, v, 3)):
            return False
        for arg in [(None, k, v, H), (q.tolist(), k, v, H), (q, k[:-1], v, H), (q, k, v[:-1], H), (q[0], k[0], v[0], H),
                    (q, k, v, 7), (q, k, v, 0), (q, k, v, True), (q, k, v, 9.0), (q[:0], k[:0], v[:0], H),
                    (torch.full_like(q, float("inf")), k, v, H),
                    (q[:,:0], k[:,:0], v[:,:0], H), (q,torch.full_like(k,float("nan")),v,H)]:
            try:
                f(*arg)
                return False
            except ValueError:
                pass
        # Nedensellik: yalnız son tokenın q/k/v'si değişirse önceki satırların bağlamı değişmemeli
        q2, k2, v2 = q.clone(), k.clone(), v.clone()
        for t in (q2, k2, v2):
            t[-1] += torch.randn(t.shape[1]) * 3
        a, b = f(q, k, v, H)["baglam"], f(q2, k2, v2, H)["baglam"]
        return (a[:-1].double() - b[:-1].double()).abs().max().item() < 1e-12
    except Exception:
        return False
kontrol(sozlesme(fn), "gerçek katman: ardışık kafa bölme, kafa boyutuyla ölçek, softmax öncesi maske, sıralı birleştirme ve nedensellik doğru")
def gecerli(f):
    def sarmal(q, k, v, H):
        if not all(isinstance(t, torch.Tensor) for t in (q, k, v)) or q.dim() != 2 or q.shape != k.shape or q.shape != v.shape \
                or q.shape[0] < 1 or not all(torch.isfinite(t).all() for t in (q, k, v)):
            raise ValueError("tensör")
        if isinstance(H, bool) or not isinstance(H, int) or H < 1 or q.shape[1] % H:
            raise ValueError("kafa")
        return f(q, k, v, H)
    return sarmal
sabit = D.referans(*girdiler[0][:3], girdiler[0][5])
for ad, kw in [("kafalar atlamalı bölünüyor", {"bolme": "atlamali"}), ("nedensel maske yok", {"maske": False}),
               ("maske softmax'tan sonra", {"maske_sonra": True}), ("√D ile ölçekleme", {"olcek": "tum"}),
               ("kafalar ters sırayla birleşiyor", {"ters_birlestir": True})]:
    kontrol(not sozlesme(gecerli(lambda q, k, v, H, kw=kw: D.referans(q, k, v, H, **kw))), "hatalı çözüm reddedilmeli: " + ad)
kontrol(not sozlesme(gecerli(lambda q, k, v, H: D.referans(q, k, v, 1))), "hatalı çözüm reddedilmeli: tek kafa")
kontrol(not sozlesme(gecerli(lambda q, k, v, H: sabit)), "hatalı çözüm reddedilmeli: ezber tablo")
model_farki, ozet, ned = [], [], {}
if all(sonuclar):
    for q, k, v, model_c, _, H in girdiler:
        model_farki.append((fn(q, k, v, H)["baglam"].double() - model_c.double()).abs().max().item())
    kontrol(max(model_farki) < 1e-4, f"birleşik bağlamın modelin gerçek katman çıktısıyla aynı (en büyük fark {max(model_farki):.1e})")
    ozet = D.kafa_ozeti(fn)
    ned = D.nedensellik()
    kontrol(ned["ortak_onek"]>0 and ned["onceki_konum_farki"]<1e-4,"gerçek modelde ortak geçmiş logitleri gelecekteki değişiklikten etkilenmedi")
if not all(sonuclar):
    stop()
yol = ai_lab.kanit_yaz("temel-cok-basli", {
    "kaynak": "gercek", "kabul": all(sonuclar), "ders": "ai-temel-06", "model_bilgisi": bilgi,
    "ayarlar": {"vakalar": [list(v) for v in vakalar], "tolerans": {"referans": 1e-9, "model": 1e-4}},
    "tokenlar": [g[4] for g in girdiler], "model_farki": model_farki, "kafa_ozeti": ozet, "nedensellik": ned})
if ned:
    farkli = sorted({o["token"] for o in ozet})
    ok(True, f"GERÇEK ÇIKTI ({bilgi['model']}@{bilgi['revizyon'][:8]}): modelle en büyük fark {max(model_farki):.1e}; "
             f"katman 4'te son tokenın kafaları {farkli} tokenlarına bakıyor; son kelime değişince önceki "
             f"{ned['ortak_onek']} konumun logit farkı {ned['onceki_konum_farki']:.1e}, son konumunki {ned['son_konum_farki']:.2f}")
```

```solution
import torch
import ai_lab

def cok_basli_dikkat(q, k, v, kafa_sayisi):
    if not all(isinstance(t, torch.Tensor) for t in (q, k, v)):
        raise ValueError("q, k, v tensör olmalı")
    if q.dim() != 2 or q.shape != k.shape or q.shape != v.shape or q.shape[0] < 1 or q.shape[1] < 1:
        raise ValueError("q, k, v aynı [T, D] biçiminde olmalı")
    if not all(torch.isfinite(t).all() for t in (q, k, v)):
        raise ValueError("değerler sonlu olmalı")
    if isinstance(kafa_sayisi, bool) or not isinstance(kafa_sayisi, int) or kafa_sayisi < 1 or q.shape[1] % kafa_sayisi:
        raise ValueError("kafa sayısı D'yi tam bölen pozitif tamsayı olmalı")
    T, D = q.shape
    d = D // kafa_sayisi
    gelecek = torch.triu(torch.ones(T, T, dtype=torch.bool), diagonal=1)
    agirliklar, baglamlar = [], []
    for h in range(kafa_sayisi):
        dilim = slice(h * d, (h + 1) * d)
        qh, kh, vh = q[:, dilim].double(), k[:, dilim].double(), v[:, dilim].double()
        skor = (qh @ kh.T / d ** 0.5).masked_fill(gelecek, float("-inf"))
        w = torch.softmax(skor, dim=-1)
        agirliklar.append(w)
        baglamlar.append(w @ vh)
    return {"agirliklar": torch.stack(agirliklar), "baglam": torch.cat(baglamlar, dim=1)}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_06 as deney
    deney.goster(cok_basli_dikkat)
```

```hint
Kafa boyutu `d = D // kafa_sayisi`; kafa `h` için sütun dilimi `h*d:(h+1)*d`. Her kafanın bağlamını bir listeye ekle, sonunda `torch.cat(..., dim=1)` ile aynı sırada birleştir; ağırlıkları `torch.stack` ile `[H, T, T]` yap.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Paralel alt uzaylar (`Multi-Head Attention`) (30 sn).** "Tek bir büyük dikkat hesabı yerine gizli boyut $H$ kafaya bölünür; böylece aynı adımda bir kafa sözdizimsel yakınlığı izlerken başka bir kafa uzak zamir-isim bağını yakalayabilir."
2. **Nedensel maske (`Causal Mask`) ve sızıntı önleme (35 sn).** "Otoregresif eğitimde $t$ konumunun $j > t$ konumlarını görmesi gelecekten kopya çekmektir; üst üçgen maske gelecekteki skorları kapatarak önceki konumların çıktısını son kelimeden tamamen bağımsız kılar."
3. **`GQA` ve çıkış projeksiyonu (`W_O`) (30 sn).** "SmolLM2 gibi modern modeller `KV cache` belleğini küçültmek için birden çok `Query` kafasına ortak `Key/Value` kafası (`GQA`) kullandırır ve kafa çıktılarını `o_proj` ile tekrar tek temsilde birleştirir."
4. **Soru (25 sn).** "Özel bir dikkat çekirdeğinde nedensel maskenin köşegen ofseti yanlışlıkla `diagonal=2` yazılırsa eğitim kaybı neden yapay biçimde sıfıra yakın görünür ama üretimde model çöker?"
:::
