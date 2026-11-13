---
id: ai-temel-02
title: "Embeddingler: Tokenlerin Vektör Uzayına Taşınması"
summary: Token kimliklerini iki boyutlu sentetik embedding satırlarına eşle; kosinüs benzerliğini ve en yakın temsil seçimini uygula.
esleme: ai-temel-01, ai-temel-15, ai-matematik-02
timeout: 45
---

::: anlat Embedding bir arama tablosudur

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Token kimliği öğrenilmiş giriş embedding satırını seçer | İlk üç görev görünür üç-satırlı sentetik JSON; final kurulu SmolLM2 giriş katmanı | Sentetik satırlar gerçek model kaydı değildir; giriş embedding'i bağlamsal son gizli durum değildir |
| Vektör yönleri kosinüsle karşılaştırılabilir | Final CPU'da gerçek tokenlar, ham vektörler ve float64 kosinüs matrisi | Yakınlık doğruluk/güvenlik kanıtı değildir; bu katman cümle embedding modeli olarak değerlendirilmez |

> [!NOT]
> `veri/embedding.json` elle hazırlanmış sentetik veridir; canlı model/tokenizer kaydı değildir. İlk üç görev aynı dosyayı okur. Setup her Run/Check için geçici kopya kurar; kalıcılık yoktur. Kaynağı editörde aç veya yüklenen sözlüğü kodda değiştirip Run dene. Gizli testler ayrıdır. Final yalnız önceden kurulu yerel model ağırlıklarını okur; yeni indirme, sohbet veya eğitim yapmaz.

PyTorch embedding katmanı her token kimliği için öğrenilmiş bir vektör saklar. Kimlik doğrudan anlam taşımaz; anlam ilişkileri eğitim sırasında vektörlerin konumlarına yansır. İlk üç görev üç tokenlık, iki boyutlu sentetik matrisle çalışır. Final kurulu PyTorch ve SmolLM2 modelini kullanır; bu derste yeni model/kütüphane indirilmez.

Token kimlikleri matrisin satır indeksleridir. Aynı kimlik yinelendiğinde aynı vektör kopyalanır. Geçersiz kimliği sessizce başka satıra yöneltmek, üretim hattında yanlış temsili ve hatalı güvenlik kararını gizleyebilir.
:::

::: anlat Yakınlık yararlıdır ama anlam kanıtı değildir

Önce embedding.json dosyasını aç. token_etiketleri yalnız örneği okumayı kolaylaştırır; kimliklerin bu kelimelerle eşleşmesi elle seçilmiştir, gerçek tokenizer sonucu değildir. Matrisin üç satırı vardır ve her satır iki bileşen taşır. İlk görev kimlikler listesindeki sırayı izleyerek satır seçer. Aynı kimlik iki kez gelirse iki ayrı liste dönmelidir. Birini sonradan değiştirmek kaynak matrisi veya diğer konumun kopyasını değiştirmemelidir. Bu küçük ayrım veri hazırlama kodundaki paylaşılan liste hatalarını yakalar.

İkinci görev dosyanın sorgu ve karsilastirma vektörlerini kullanır. Nokta çarpımı büyüklükten etkilenir; kosinüs yönü karşılaştırmak için normlara böler. Dosyada karşılaştırma vektörünün büyüklüğünü değiştirip sonucu gözle. Aynı yöndeki iki sıfır olmayan vektör için sonuç bire, zıt yön için eksi bire, dik yönler için sıfıra yakındır. Sıfır vektörün yönü tanımlı değildir ve bu ders hata ister. Sonlu olmayan veya float temsilini aşan sayılar da açıkça reddedilir. Çok büyük ve çok küçük geçerli değerlerde normu doğrudan kareleri toplayarak hesaplamak taşma veya sıfıra yuvarlanma üretebilir; önce en büyük mutlak bileşene bölüp birim vektör hesaplamak bu riski azaltır.

Üçüncü görev aynı sorguyu üç satırla karşılaştırır. En büyük ham nokta çarpımını seçmek yanlış olabilir: büyük normlu ama daha kötü yönlü bir satır öne çıkabilir. Eşitlikte küçük indeksin kazanması bu dersin açık sözleşmesidir; bütün arama sistemlerinin aynı politikayı kullandığı iddia edilmez. Kimlikleri sessizce mod almak veya negatif indeksi Python'un sondan seçme davranışına bırakmak da geçersiz veriyi gizler. İlk görev bu yüzden bütün şemayı seçmeden önce doğrular. Geçersiz çağrıda yarım sonuç veya kaynakta kısmi değişiklik olmamalıdır.

Gerçek finalde tokenizer metni bir veya birden fazla kimliğe ayırır. Baştaki boşluklar, Türkçe karakterler ve tekrarlar kimlik dizisini etkileyebilir; özgün metni strip ederek modele vermek bu yüzden yanlış olur. Boşluk denetimi yalnız girdinin boş olup olmadığını anlamak içindir. Modelin sözlüğü ve embedding boyutu kaynaktan okunur, iki boyuta veya belli bir token sayısına sabitlenmez. Giriş katmanı öğrenilmiş tablodur; aynı kimlik farklı konumda aynı satırı seçer. Transformer'ın konum ve bağlam işlemleri bu deneyde çalıştırılmaz.

Öğrencinin katman çağrısı ile testin ağırlık tablosundan bağımsız satır seçimi karşılaştırılır. İkisi aynı öğrenilmiş ağırlığa bakar ama farklı kod yolunu kullanır. Ayrıca gerçek katmanın no_grad altında çağrıldığı ve transformer forward'ın çalıştırılmadığı denetlenir. Katmandan gelen satırlar float64'e taşınır; birim vektörler ayrı hesaplanır. Ham vektör yerine normalize vektör döndürmek raporu değiştirir ve test bunu reddeder. Kosinüs matrisi N×N, ham vektör matrisi N×D olmalıdır; iki boyutu birbirine karıştırma.

Güvenlik açısından yakın vektör, güvenilir belge demek değildir. Bir saldırgan benzer temsile sahip bir metni arama sonuçlarına sokmayı hedefleyebilir; bu ders böyle bir saldırının başarısını ölçmez. Kaynak yetkisi ve güven düzeyi uygulama katmanında ayrıca ele alınmalıdır. Giriş token vektörünü cümle temsili gibi ortalayıp bütün anlamı çözdüğünü düşünmek de hatadır. Burada yalnız tablonun gerçek satırlarını ve açısal yakınlığını gözlüyoruz; semantik retrieval kalitesi için ayrı veri ve değerlendirme gerekir.

Kanıtta model revizyonu, ağırlık özeti, sürümler, CPU bilgisi, özgün metinler, gerçek kimlikler, tam ham vektörler ve kosinüs matrisleri kalır. Ekranda ilk birkaç bileşenin gösterilmesi tam verinin kaybolduğu anlamına gelmez. Çalıştır keşif kaydını `kabul=false` ile yazar; Kontrol et doğruluğu ve gerçek ağırlık kullanımını birlikte değerlendirir. Model önbellekte yoksa indirme denenmez ve görev geçmez. Bu ders dış sunucu başlatmaz; temel model veya öğrenci verisi kalıcı olarak değiştirilmez.

Kaynak: [PyTorch Embedding](https://docs.pytorch.org/docs/stable/generated/torch.nn.Embedding.html). Kimliklerden satır seçen öğrenilebilir tablo kavramı için resmî başvuru; bu dersteki gerçek boyut kurulu modelin ağırlığından okunur.

Kosinüs benzerliği iki vektörün açısını ölçer ve büyüklüklerinin etkisini azaltır. Kuramsal kosinüs [-1, 1] aralığındadır; kayan nokta hesabında son basamakta çok küçük aşmalar görülebilir. Sıfır normda kosinüs tanımsızdır. En yakın vektörü seçerken eşitlikte küçük indeksin kazanması deterministik sonuç sağlar.

Benzer temsiller çoğu zaman ilişkili kavramları yakalar; ancak sentetik matriste olduğu gibi yakınlık tek başına doğruluk, güvenlik veya nedensellik kanıtı değildir. Retrieval ve sınıflandırma kararları ayrıca veriyle sınanmalıdır.
:::

::: tahmin Satır seçimini ve benzerliği tahmin et
Üç çıktı satırını yaz:

```python
m = [[1.0, 0.0], [0.0, 2.0], [1.0, 1.0]]
print(m[2] + m[0])
print(round((1 * 1 + 1 * 0) / ((2 ** 0.5) * 1), 6))
print(max(range(3), key=lambda i: [0.0, 1.0, 0.7][i]))
```

???

```cikti
[1.0, 1.0, 1.0, 0.0]
0.707107
1
```

İlk satır bağımsız liste birleştirmeyi, ikinci satır `[1,1]` ile `[1,0]` arasındaki kosinüsü, üçüncü satır en yüksek benzerliğin indeksini gösterir.
:::

::: gorev 1 · Token kimliklerini embedding satırlarına çevir
`embedding_bak(matris, kimlikler)` işlevini yaz. Matris tam üç satırlı listedir; her satır iki adet, bool olmayan, sonlu float temsilini aşmayan int/float değer içerir. Kimlikler 1–8 öğeli listedir; her öğe bool olmayan 0, 1 veya 2 tamsayısıdır. Geçersiz veride `ValueError` yükselt.

Kimlik sırasındaki satırları yeni iki öğeli listeler olarak döndür. Yinelenen kimliklere izin ver; matrisi ve kimlik listesini değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-02")
```

```starter
from ai_temel_veri import json_yukle,metin_yukle
def embedding_bak(matris,kimlikler):
    # KUSURLU BAŞLANGIÇ KODU: geçersiz kimliği sessizce mod alır, kaynak satırları kopyalamadan paylaşır.
    return [matris[k % len(matris)] for k in kimlikler]

v=json_yukle("veri/embedding.json")
print("Sentetik ham dosya:\n",metin_yukle("veri/embedding.json"))
print("Satırlar:",embedding_bak(v["matris"],v["kimlikler"]))
```

```test
import copy
M = [[1.0, 0.0], [0.0, 2.0], [1.0, 1.0]]
def sozlesme(fn):
    try:
        once = copy.deepcopy(M)
        ids=[2,0,2];once_ids=list(ids);fn(M,ids)
        if ids!=once_ids:return False
        if fn(M, [2, 0, 2]) != [[1.0, 1.0], [1.0, 0.0], [1.0, 1.0]] or M != once:
            return False
        sonuc = fn(M, [1] * 8)
        if len(sonuc) != 8 or any(x is M[1] for x in sonuc) or fn(M, [0]) != [[1.0, 0.0]]:
            return False
        a=fn(M,[1,1]);a[0][0]=999
        if M!=once or a[1]!=M[1]:return False
        for args in [(None, [0]), ([(0, 0), [0, 0], [0, 0]], [0]), ([["x", 0], [0, 0], [0, 0]], [0]), ([["1", 0], [0, 0], [0, 0]], [0]), ([[0, 0]] * 2, [0]), ([[0, 0], [0], [0, 0]], [0]), ([[0], [0, 0], [0, 0]], [0]), ([[True, 0], [0, 0], [0, 0]], [0]), (M, None), (M, []), (M, [0] * 9), (M, [-1]), (M, [3]), (M, [True]), (M, [0.0]),([[float("nan"),0],[1,0],[0,1]],[0]),([[10**400,0],[1,0],[0,1]],[0])]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(embedding_bak), "satır eşleme ve embedding şeması korunmalı")
def m_matris(m, k):
    return embedding_bak(list(reversed(m)), k)
def m_kimlik(m, k):
    return embedding_bak(m, [0] * len(k))
def m_uzun(m, k):
    return embedding_bak(m, k + k)
for ad, mutant in [("satırları değiştiren", m_matris), ("kimlikleri silen", m_kimlik), ("uzunluğu bozan", m_uzun)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle,metin_yukle
def embedding_bak(matris, kimlikler):
    import math
    def sayi(x):
        if not isinstance(x,(int,float)) or isinstance(x,bool):return False
        try:return math.isfinite(float(x))
        except (ValueError,OverflowError):return False
    if not isinstance(matris, list) or len(matris) != 3:
        raise ValueError("matris geçersiz")
    if any(not isinstance(s, list) or len(s) != 2 or any(not sayi(x) for x in s) for s in matris):
        raise ValueError("satır geçersiz")
    if not isinstance(kimlikler, list) or not 1 <= len(kimlikler) <= 8:
        raise ValueError("kimlik listesi geçersiz")
    if any(not isinstance(k, int) or isinstance(k, bool) or not 0 <= k < 3 for k in kimlikler):
        raise ValueError("kimlik geçersiz")
    return [list(matris[k]) for k in kimlikler]

v=json_yukle("veri/embedding.json")
print("Sentetik ham dosya:\n",metin_yukle("veri/embedding.json"))
print("Satırlar:",embedding_bak(v["matris"],v["kimlikler"]))
```

```hint
Önce bütün şemayı doğrula. Sonra liste üretiminde her kimlik için `list(matris[k])` kopyası oluştur.
```
:::

::: gorev 2 · Kosinüs benzerliğini hesapla
`kosinus(a, b)` işlevini yaz. İki girdi de iki adet bool olmayan, sonlu float temsilini aşmayan int/float içeren listedir. Sıfır normlu vektör ve diğer geçersiz verilerde `ValueError` yükselt.

İki vektörün kosinüs benzerliğini hesapla, altı ondalığa yuvarla ve float döndür. Girdileri değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-02")
```

```starter
from ai_temel_veri import json_yukle,metin_yukle
def kosinus(a,b):
    # KUSURLU BAŞLANGIÇ KODU: normlara bölmek yerine ham nokta çarpımını döndürür.
    return float(sum(x*y for x,y in zip(a,b)))

v=json_yukle("veri/embedding.json")
print("Sentetik sorgu/karşılaştırma:",v["sorgu"],v["karsilastirma"])
print("Kosinüs:",kosinus(v["sorgu"],v["karsilastirma"]))
```

```test
def sozlesme(fn):
    try:
        if fn([1, 0], [1, 0]) != 1.0 or fn([1, 0], [0, 2]) != 0.0:
            return False
        if fn([1, 1], [1, 0]) != 0.707107 or fn([1, 0], [-2, 0]) != -1.0:
            return False
        import copy
        a=([1.25,2.5],[-2.5,1.25]);once=copy.deepcopy(a);fn(*a)
        if a!=once or fn([1e300,0],[1e300,0])!=1.0 or fn([1e-300,0],[0,1e-300])!=0.0:return False
        for args in [(None, [1, 0]), ([None, 0], [1, 0]), ([1], [1, 0]), ([1, 0, 0], [1, 0]), ([True, 0], [1, 0]), ([0, 0], [1, 0]), ([1, 0], [0, 0]), ("10", [1, 0]),([float("inf"),0],[1,0]),([float("nan"),0],[1,0]),([10**400,0],[1,0])]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(kosinus), "kosinüs, yuvarlama ve sıfır norm reddi korunmalı")
def m_a(a, b):
    return kosinus(list(reversed(a)), b)
def m_b(a, b):
    return kosinus(a, [-x for x in b])
def m_boyut(a, b):
    return kosinus(a + [0], b + [0])
for ad, mutant in [("vektörü bozan", m_a), ("işareti bozan", m_b), ("boyutu bozan", m_boyut)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle,metin_yukle
def kosinus(a,b):
    import math
    def birim(v):
        if not isinstance(v,list) or len(v)!=2 or any(isinstance(x,bool) or not isinstance(x,(int,float)) for x in v):raise ValueError("vektör")
        try:a=[float(x) for x in v]
        except (ValueError,OverflowError) as e:raise ValueError("sayı") from e
        if not all(math.isfinite(x) for x in a):raise ValueError("sonlu sayı")
        tepe=max(abs(x) for x in a)
        if tepe==0:raise ValueError("sıfır norm")
        a=[x/tepe for x in a];norm=math.hypot(*a)
        return [x/norm for x in a]
    u,v=birim(a),birim(b)
    return float(round(max(-1.0,min(1.0,sum(x*y for x,y in zip(u,v)))),6))

v=json_yukle("veri/embedding.json")
print("Sentetik sorgu/karşılaştırma:",v["sorgu"],v["karsilastirma"])
print("Kosinüs:",kosinus(v["sorgu"],v["karsilastirma"]))
```

```hint
Nokta çarpımını iki normun çarpımına böl. Normlardan biri sıfırsa bölme yapmadan hata ver.
```
:::

::: gorev 3 · En yakın embedding satırını seç
`en_yakin_satir(vektor, matris)` işlevini yaz. Vektör ikinci görevdeki biçimde, matris ilk görevdeki üç satırlı biçimdedir; vektörlerden hiçbiri sıfır normlu olamaz. Geçersiz veride `ValueError` yükselt.

Vektörün her satırla kosinüs benzerliğini hesapla. En yüksek benzerlikli satırın indeksini döndür; eşitlikte küçük indeks kazanır. Girdileri değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-02")
```

```starter
from ai_temel_veri import json_yukle,metin_yukle
def en_yakin_satir(vektor,matris):
    # KUSURLU BAŞLANGIÇ KODU: kosinüs yerine uzaklığı büyük olan satırı seçer.
    return max(range(len(matris)),key=lambda i:sum((x-y)**2 for x,y in zip(vektor,matris[i])))

v=json_yukle("veri/embedding.json")
print("Sentetik sorgu/matris:",v["sorgu"],v["matris"])
print("En yakın satır:",en_yakin_satir(v["sorgu"],v["matris"]))
```

```test
M = [[1.0, 0.0], [0.0, 2.0], [1.0, 1.0]]
def sozlesme(fn):
    try:
        if fn([1, 0], M) != 0 or fn([0, 3], M) != 1 or fn([2, 2], M) != 2:
            return False
        esit = [[1, 0], [2, 0], [0, 1]]
        if fn([3, 0], esit) != 0:
            return False
        import copy
        a=([1e300,0],[[1e300,0],[0,1e300],[-1e300,0]]);once=copy.deepcopy(a)
        if fn(*a)!=0 or a!=once or fn([0,1e-300],[[1e-300,0],[0,1e-300],[-1e-300,0]])!=1:return False
        for args in [(None, M), ([None, 0], M), ([10**400, 0], M), ([0, 0], M), ([1], M), ([1, 0], None), ([1, 0], M[:2]), ([1, 0], [[0, 0], [1, 0], [0, 1]]), ([1, 0], [[True, 0], [1, 0], [0, 1]]),([float("nan"),0],M),([1,0],[[float("inf"),0],[1,0],[0,1]])]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
eq(en_yakin_satir([1, 0], [[-1, 0], [-1, 1], [-2, -2]]), 1,
   "Bütün skorlar negatifken en büyük skor kazanır, eşitlikte ilk uygun indeks")
eq(en_yakin_satir([1, 0], [[-1, 0], [0, 2], [1, 100]]), 2,
   "Sıfıra yakın pozitif skor sıfır ve negatif skoru geçer")
ok(sozlesme(en_yakin_satir), "en yakın satır ve eşitlik kuralı korunmalı")
def m_vektor(v, m):
    return en_yakin_satir(list(reversed(v)), m)
def m_matris(v, m):
    return en_yakin_satir(v, list(reversed(m)))
def m_secim(v, m):
    return 2
for ad, mutant in [("sorguyu bozan", m_vektor), ("satır sırasını bozan", m_matris), ("sabit seçim", m_secim)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle,metin_yukle
def en_yakin_satir(vektor,matris):
    import math
    def birim(v):
        if not isinstance(v,list) or len(v)!=2 or any(isinstance(x,bool) or not isinstance(x,(int,float)) for x in v):raise ValueError("vektör")
        try:a=[float(x) for x in v]
        except (ValueError,OverflowError) as e:raise ValueError("sayı") from e
        if not all(math.isfinite(x) for x in a):raise ValueError("sonlu sayı")
        tepe=max(abs(x) for x in a)
        if tepe==0:raise ValueError("sıfır norm")
        a=[x/tepe for x in a];norm=math.hypot(*a)
        return [x/norm for x in a]
    q=birim(vektor)
    if not isinstance(matris,list) or len(matris)!=3:raise ValueError("matris")
    satirlar=[birim(s) for s in matris]
    return max(range(len(satirlar)),key=lambda i:sum(x*y for x,y in zip(q,satirlar[i])))

v=json_yukle("veri/embedding.json")
print("Sentetik sorgu/matris:",v["sorgu"],v["matris"])
print("En yakın satır:",en_yakin_satir(v["sorgu"],v["matris"]))
```

```hint
`max(range(3), key=...)` küçük indeksten başlar ve yalnız daha büyük değerde seçimi değiştirir; böylece eşitlikte ilk satır kalır.
```
:::

::: anlat Gerçek deney: öğrenilmiş embedding tablosunu aç
Önceki üç satırlık matris öğretim içindi. Şimdi kurulu `SmolLM2-135M` modelinin **gerçek giriş embedding katmanını** kullanacağız. `ai_lab.dil_modeli()` yalnız yerel önbelleği okur; model yoksa görev geçmez. `model.get_input_embeddings()` her token kimliğinin öğrenilmiş vektörünü verir. Burada transformer ileri hesabı yapılmaz; elde ettiğimiz giriş embedding'i bağlama göre oluşan son katman gizli durumu değildir.

Metindeki aynı token kimliği hangi konumda olursa olsun aynı tablo satırını seçer. Farklı kimliklerin vektörleri arasındaki kosinüs, açısal yakınlıktır; metinlerin anlamını, doğruluğunu veya güvenliğini tek başına kanıtlamaz. Bu katman otomatik olarak bir cümle embedding modeli sayılmaz. Türkçe kelimeler birden fazla token olabilir; kelimeyle tokenı karıştırma.

Gerçek vektörler iki boyutlu değildir. Boyutu modelin embedding ağırlığının ikinci ekseninden öğren. Kosinüs matrisi için her satırı kendi L2 normuna bölüp normalize edilmiş matrisin transpozuyla çarp. Ham nokta çarpımı kosinüs değildir. Burada sıfır normlu bir satır çıkarsa sessizce bölmek yerine hata ver.
:::

::: gorev Gerçek deney · Gerçek embedding vektörleri ve kosinüs matrisi
`gercek_embedding_raporu(metin)` işlevini yaz:

- `metin`, boşluk dışı karakter içeren bir `str` olsun. Gerçek tokenizer'ın özel token eklemeden ürettiği token sayısı 1–16 aralığında olmalı. Geçersiz girdide `ValueError` yükselt. Metni kırpma; token sınırını aşan metni sessizce kesme.
- `tok, model, bilgi = ai_lab.dil_modeli()` ile kurulu gerçek modeli al. `tok(metin, add_special_tokens=False)["input_ids"]` kimliklerini sırayla kullan.
- `torch.no_grad()` içinde `model.get_input_embeddings()` katmanını gerçek kimlik tensörüyle çağır. Ham satırları `float64` hesapla kullan; kosinüs için normalize et ama döndüreceğin ham vektörleri değiştirme.
- Tam şu alanları döndür: `token_idleri` (int listesi), `boyut` (embedding boyutu int), `vektorler` (N×D float listesi), `kosinus` (N×N float listesi).

Sıra ve yinelenen kimlikler korunmalı. Modelin çıkış logitlerini, rastgele vektörleri veya yalnız normları döndürmek çözüm değildir. Sonuçlar yuvarlanmaz. Deneyin bütçesi kısa metindir; model eğitilmez ve GPU gerektirmez. Laboratuvarın `referans_raporu` işlevini çağırma; raporu kendi katman çağrın ve hesabınla üret.

```meta
motor: ai-gercek
gereksinim: torch
timeout: 240
```

```starter
import ai_lab

def gercek_embedding_raporu(metin):
    return {}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_02 as deney
    deney.goster(gercek_embedding_raporu)
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
from unittest.mock import patch
yasak=("referans_raporu","getattr","kanit_yaz")
sorun=ai_lab.kod_denetimi(src,yasak=yasak)
for n in ast.walk(ast.parse(src)):
    if isinstance(n,ast.ImportFrom) and any(a.name in yasak or a.name=="*" for a in n.names):sorun.append("referans importu yasak")
if not kontrol(not sorun,"Kendi embedding raporunu yaz: "+"; ".join(sorun)):stop()
fn = need("gercek_embedding_raporu")
try:
    import torch
    tok, model, bilgi = ai_lab.dil_modeli()
except (ImportError, ai_lab.GercekLabYok) as e:
    kontrol(False, "GERÇEK MODEL YOK: " + str(e))
    stop()

from sandbox import ai_gercek_ai_temel_02 as D
rng = random.SystemRandom()
metinler = [" the"*16,"hello", " the the river", " river the the", "İstanbul", "  model",
            rng.choice(["green", "blue", "red"]) + " " + rng.choice(["data", "music", "river"]) + " " + str(rng.randrange(100, 999))]

def referans(m):return D.referans_raporu(m)

beklenen = [referans(m) for m in metinler]
def ayni(a, b):
    try:
        if not isinstance(a, dict) or set(a) != set(b) or a["token_idleri"] != b["token_idleri"]:
            return False
        if type(a["boyut"]) is not int or a["boyut"] != b["boyut"] or any(type(i) is not int for i in a["token_idleri"]):
            return False
        for alan in ["vektorler", "kosinus"]:
            if not isinstance(a[alan], list) or any(not isinstance(row, list) or any(type(x) is not float for x in row) for row in a[alan]):
                return False
            x, y = torch.tensor(a[alan], dtype=torch.float64), torch.tensor(b[alan], dtype=torch.float64)
            if x.shape != y.shape or not bool(torch.isfinite(x).all()) or not torch.allclose(x, y, atol=1e-10, rtol=1e-9):
                return False
        return True
    except Exception:
        return False

uzun = " the" * 40
kontrol(len(tok(uzun, add_special_tokens=False)["input_ids"]) > 16, "sınır testi gerçekten token bütçesini aşıyor")
def sozlesme(f):
    try:
        for m, b in zip(metinler, beklenen):
            a = f(m)
            if not ayni(a, b):
                return False
            once = copy.deepcopy(a)
            f("a different word")
            if a != once:
                return False
        for m in ["", "   ", None, 42, True, [], b"hello", " the" * 17, uzun]:
            try:
                f(m)
                return False
            except ValueError:
                pass
        class _SahteEmb:
            def __call__(self, t_ids):
                tablo = torch.tensor([[0.0, 0.0], [0.6, 0.8]], dtype=torch.float32)
                return tablo[t_ids]
        class _SahteModel:
            def get_input_embeddings(self):
                return _SahteEmb()
        def _sahte_tok(txt, add_special_tokens=True):
            if add_special_tokens is not False:
                return {"input_ids": [99]}
            if txt == "BOS_IDS":
                return {"input_ids": []}
            if txt == "SIFIR_NORM":
                return {"input_ids": [0]}
            return {"input_ids": [1]}
        with patch.object(ai_lab, "dil_modeli", return_value=(_sahte_tok, _SahteModel(), {})):
            u_birim = f("BIRIM_NORM")
            if u_birim["token_idleri"] != [1] or abs(u_birim["kosinus"][0][0] - 1.0) > 1e-9:
                return False
            for kotu_m in ("BOS_IDS", "SIFIR_NORM"):
                try:
                    f(kotu_m)
                    return False
                except ValueError:
                    pass
        return True
    except Exception:
        return False

def gercek_katman(f):
    katman=model.get_input_embeddings();bayraklar=[]
    h=katman.register_forward_pre_hook(lambda *a:bayraklar.append(torch.is_grad_enabled()))
    try:
        with patch.object(model,"forward",side_effect=AssertionError("transformer forward kullanılmaz")):
            f(" the the river")
        return bool(bayraklar) and not any(bayraklar)
    except Exception:return False
    finally:h.remove()
kontrol(gercek_katman(fn),"gerçek giriş katmanı no_grad ile çağrıldı; transformer forward çalışmadı")
kontrol(len(tok(" the"*16,add_special_tokens=False)["input_ids"])==16,"üst sınır vakası gerçekten 16 token")
kontrol(sozlesme(fn), "gerçek giriş embedding satırları, boyut, sıra ve kosinüs doğru")

def degistir(f):
    def s(m):
        if not isinstance(m, str) or not m.strip():
            raise ValueError("metin")
        return f(copy.deepcopy(referans(m)))
    return s
def ters(a):
    a["vektorler"].reverse()
    return a
def nokta(a):
    v = torch.tensor(a["vektorler"], dtype=torch.float64)
    a["kosinus"] = (v @ v.T).tolist()
    return a
def birim(a):
    v = torch.tensor(a["vektorler"], dtype=torch.float64)
    a["vektorler"] = (v / torch.linalg.vector_norm(v, dim=1, keepdim=True)).tolist()
    return a
sabit = beklenen[0]
for ad, mutant in [("boş kod/işlev", None), ("boş sözlük", lambda m: {}),
                   ("ezber vektörler", lambda m: copy.deepcopy(sabit)),
                   ("satır sırası ters", degistir(ters)),
                   ("kosinüs yerine nokta çarpımı", degistir(nokta)),
                   ("ham vektör yerine birim vektör", degistir(birim))]:
    kontrol(not sozlesme(mutant), "hatalı çözüm reddedilmeli: " + ad)

ciktilar = [fn(m) for m in metinler] if all(sonuclar) else []
for d in ciktilar:
    cos = torch.tensor(d["kosinus"], dtype=torch.float64)
    kontrol(torch.allclose(cos, cos.T, atol=1e-7) and torch.allclose(cos.diag(), torch.ones(len(cos), dtype=torch.float64), atol=1e-7), "kosinüs simetrik ve köşegeni bir")

# Herhangi bir konumda yinelenen kimlik varsa aynı tablo satırını verdiğini ayrıca göster.
tekrarlar = 0;tekrar_dogrular=[]
for d in ciktilar:
    for i in range(len(d["token_idleri"])):
        for j in range(i):
            if d["token_idleri"][i] == d["token_idleri"][j]:
                tekrarlar += 1
                tekrar_dogrular.append(d["vektorler"][i] == d["vektorler"][j])
kontrol(all(tekrar_dogrular),"bütün yinelenen kimlik çiftleri aynı ham embedding satırını seçer")
kontrol(tekrarlar > 0, "gerçek metinler içinde yinelenen kimlik sınandı")

ai_lab.kanit_yaz("temel-02-embedding", {
    "kaynak": "gercek", "kabul": all(sonuclar), "model_bilgisi": bilgi,
    "islem": "gerçek öğrenilmiş giriş embedding tablosu; transformer ileri hesabı yok",
    "ayarlar": {"girdiler": metinler, "max_token": 16, "atol": 1e-10, "rtol": 1e-9},
    "ciktilar": ciktilar, "tekrarlanan_kimlik_ciftleri": tekrarlar,
    "temizlik": "CPU işlemi; dış sunucu veya kalıcı süreç açılmadı"})
for m, d in zip(metinler, ciktilar):
    print(repr(m), "→", len(d["token_idleri"]), "token ×", d["boyut"], "boyut; kimlikler", d["token_idleri"])
    print("ilk vektörün ilk 6 bileşeni:", d["vektorler"][0][:6], "kosinüs boyutu:", [len(d["kosinus"]),len(d["kosinus"][0])])
```

```solution
import ai_lab
import torch

def gercek_embedding_raporu(metin):
    if not isinstance(metin, str) or not metin.strip():
        raise ValueError("boş olmayan metin gerekli")
    tok, model, _ = ai_lab.dil_modeli()
    ids = tok(metin, add_special_tokens=False)["input_ids"]
    if not 1 <= len(ids) <= 16:
        raise ValueError("1-16 token gerekli")
    with torch.no_grad():
        v = model.get_input_embeddings()(torch.tensor(ids)).double()
        norm = torch.linalg.vector_norm(v, dim=1, keepdim=True)
        if bool((norm == 0).any()):
            raise ValueError("sıfır norm")
        birim = v / norm
        cos = birim @ birim.T
    return {"token_idleri": ids, "boyut": v.shape[1], "vektorler": v.tolist(), "kosinus": cos.tolist()}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_02 as deney
    deney.goster(gercek_embedding_raporu)
```

```hint
`get_input_embeddings()` bir katmandır: kimlik tensörüyle çağır. `v / norm` ayrı hesap olsun; ham `v` döndürülecek. Boşlukları yalnız girdinin geçerliliğini kontrol ederken incele, tokenizer'a özgün metni ver.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Kimlikten sürekli uzaya (25 sn).** "Token kimlikleri keyfî sıra numaralarıdır (`42` ile `43` yakın anlamlı değildir); giriş `embedding` tablosu her kimliği $d$ boyutlu öğrenilmiş bir gerçek sayı vektörüne taşır."
2. **Boy değil yön: kosinüs benzerliği (35 sn).** "Sık geçen tokenların normu büyüyebilir; kosinüs benzerliği $\frac{u \cdot v}{\|u\|_2 \|v\|_2}$ norm etkisini bölüp yalnız açısal yakınlığı ölçer, sıfır normda ise tanımsız olduğu için açık hata yükseltilmelidir."
3. **Giriş gömmesi vs bağlamsal temsil (35 sn).** "SmolLM2'nin `get_input_embeddings()` tablosundan çekilen vektör statiktir; kelimenin cümle içindeki anlam ayrımı ancak dikkat (`attention`) katmanlarından geçtikten sonra oluşur."
4. **Soru (25 sn).** "Yüksek kosinüs yakınlığı iki metnin aynı olguyu doğruladığını neden kanıtlamaz ve RAG aramasında ne zaman yanıltıcı olur?"
:::
