---
id: ai-temel-15
title: "Activation Steering ve Representation Engineering"
summary: Sentetik aktivasyonlardan davranış yönü çıkar, ağırlıkları değiştirmeden yönelt ve müdahale normunu sınırla.
esleme: ai-temel-02, ai-temel-05, ai-savunma-15
timeout: 45
---

::: anlat Davranış yönü aktivasyon farklarından çıkar

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Katman aktivasyonlarından fark yönü çıkarılıp çalışma sırasında eklenebilir | İlk üç görev görünür üç boyutlu sentetik JSON; final gerçek SmolLM2 residual aktivasyonları | Oyuncak sayılar model kaydı değildir; fark yönü evrensel davranış veya güvenlik yönü değildir |
| Müdahalenin hedef konuma ve sonraki katmana ulaşması gözlenebilir | Final gerçek torch hook, iki katman, son token ve ağırlık SHA256 kontrolü | TransformerLens/repeng çalışması, bütün modele eğitim veya tam güvenlik değerlendirmesi değildir |

> [!NOT]
> `veri/aktivasyon.json` elle hazırlanmış sentetik çalışma verisidir. İlk üç görev aynı dosyayı okur; ilk Çalıştır ham JSON'u gösterir. Setup her Run/Check için yeni geçici veri/ kopyası kurar; değişiklikler sonraki çalıştırmaya taşınmaz. Kaynağı haricî editörde veya yüklenen sözlüğü kod içinde değiştirip Çalıştır ile deneyebilirsin. Gizli testler ayrıdır. Final kurulu yerel modeli gerçekten çalıştırır; yeni indirme yapmaz ve model dosyalarını güncellemez.

Representation engineering, seçilmiş davranış örneklerinin aktivasyonları arasındaki farkları yön vektörüne dönüştürür. Bu derste pozitif ve negatif örneklerin ortalaması alınır, fark vektörü birim uzunluğa normalize edilir. Küçük fixture gerçek model aktivasyonu değildir.

İlk üç görevde model veya PyTorch çalıştırılmaz; final gerçek model ve PyTorch hooklarını kullanır. TransformerLens ve repeng bu derste kullanılmaz. Amaç yön çıkarma ile üretim sonucunu değiştirme arasındaki mekanik ilişkiyi görmek; yönün nedensel veya evrensel güvenlik garantisi olmadığını kabul etmektir.
:::

::: anlat Yöneltme ağırlık güncellemesi değildir

Önce aktivasyon.json dosyasını oku. pozitif ve negatif alanları aynı boyutlu iki örnek grubudur. Bunlar gerçek bir modelden yakalanmış aktivasyonlar değil, fark hesabını gözle takip edebilmen için elle yazılmış sayılardır. Pozitif etiketi iyi veya güvenli anlamına gelmez; deney tasarımcısının iki grup için verdiği addır. İlk görev her grubun üç örneğini ayrı ayrı ortalar, sonra pozitif ortalamadan negatif ortalamayı çıkarır. Satırların grubun içindeki sırası ortalamayı değiştirmez. Grupların yerini değiştirmek ise yönün işaretini çevirir. Bu iki işlemi aynı hata gibi değerlendirmek, geçerli bir çözümü yanlışlıkla reddeden test üretir.

Fark vektörünün büyüklüğü örneklerin ölçeğine bağlıdır. Birim yön elde etmek için L2 normuna bölünür; bütün bileşenler sıfırsa tanımlı bir yön yoktur ve görev ValueError ister. Yuvarlama normdan önce yapılmaz; erken yuvarlama küçük bileşenleri yok edebilir. Bu küçük görev çıktıyı altı ondalık ister, gerçek final ise modelin dtype hassasiyetini ve açık toleransları kullanır. Birim norm, yönün doğru davranışı temsil ettiğinin kanıtı değildir. Aynı veriyle çıkarılmış iki yönün benzerliği de tek başına nedensellik veya güvenilirlik göstermez. Kaynak metinlerin ortak biçimi, uzunluğu ve son tokenı bile farkı etkileyebilir.

İkinci görev aynı dosyanın aktivasyon, yon ve katsayi alanlarını kullanır. Her bileşene katsayı çarpı yön eklenir. Katsayı sıfırsa çıktı kaynağın bağımsız bir kopyasıdır; negatif katsayı zıt yönde müdahaledir. Aktivasyon yerine model ağırlığına ekleme yapmak veya aktivasyonu katsayıyla çarpmak başka bir işlem olur. Kaynak listeyi yerinde değiştirmek bir sonraki karşılaştırmanın tabanını bozar. Bu yüzden verilen veriler değişmeden kalır. Dosyadaki katsayıyı sıfır, pozitif ve negatif yapıp aynı aktivasyonun nasıl değiştiğini karşılaştır; tek bir sonuca bakarak genel davranış hükmü verme.

Üçüncü görevde esik alanı müdahale büyüklüğünü sınırlar. Sınırlanan şey aktivasyonun tamamı değildir; yalnız katsayı çarpı yön vektörüdür. Müdahale normu eşiğe tam eşitse kırpıldı bayrağı False kalır. Eşik sıfır ve müdahale sıfır değilse tüm müdahale sıfırlanır; zaten sıfır olan müdahalede bölme yapılmaz ve kırpma sayılmaz. Başlangıç aktivasyonu büyük olsa bile müdahalenin küçük olması mümkündür. Dosyadaki büyük_baslangic örneği, bütün sonucu normalize eden kusurlu çözümün neden yanlış olduğunu gösterir. Tek tek bileşen kırpmak da L2 normunu aynı kuralla sınırlamaz.

Finalde laboratuvar gerçek decoder katmanlarının son token çıktılarını sakin/acil biçimindeki sentetik metin gruplarında yakalar. Bu metinler sentetiktir fakat bunlardan elde edilen aktivasyonlar kurulu modelin gerçek ileri hesabıdır. İki katman için ortalama farklar ve birim yönler ayrı çıkarılır. Katman sıfırda elde edilen yönün başka katmana aynı anlamla taşınacağı varsayılmaz. Metinler, gerçek tokenizer kimlikleri, tam yakalanmış vektörler, yönler ve özetleri kanıta yazılır. Finalin kelime anlamını veya refusal başarısını ölçtüğü iddia edilmez; bu metin karşıtlıkları yalnız kontrollü örnek gruplarıdır.

Öğrenci önce müdahalesiz ileri hesabı yapar. Sonra yalnız hedef katmanın son token dilimine delta ekleyen bir forward hook bağlar. Orijinal tensörü değiştirmek yerine clone üzerinde çalışır; tuple çıktıda diğer öğeleri korur. Sonraki katmanın girdisini gözlemek, raporda doğru sayılar döndürüp modelde farklı işlem yapan çözümü yakalamaya yardım eder. Bütün tokenlara aynı yönü eklemek önceki konumları da değiştirir ve bu dersin hedefini ihlal eder. Raporlanan kayma normu teorik delta normundan değil gerçekten uygulanmış farktan ölçülür; dtype dönüşümü ve toplama yuvarlaması küçük farklar yaratabilir.

Hook temizliği deneyin parçasıdır. İkinci forward hata verirse finally yine handle.remove çağırmalıdır. Aksi durumda bir sonraki denemenin tabanı artık müdahalesiz değildir ve karşılaştırma bozulur. Test başarılı yolun yanında yapay bir forward hatasını da kullanır; bu hata senaryosu gerçek saldırı sonucu diye sunulmaz. Mevcut kullanıcı hooklarını kaldırmak da yasaktır. Bütün model parametrelerinin SHA256 özeti ve parametre sürümleri ağırlık değişimini denetler; yalnız dönen sözlüğe güvenilmez. Yön tensörü de aynı kalmalıdır. Grad kapalı çalışmak gereksiz autograd grafiği ve bellek yükünü önler.

Bir saldırgan aktivasyonlara erişebildiği bir araştırma ortamında davranış değişikliklerini deneyebilir; bu yetki her servis API'sinde mevcut değildir. Savunma açısından küçük normlu müdahalenin her zaman zararsız olduğu söylenemez. Aynı şekilde argmax'ın değişmemesi hiçbir etki olmadığı anlamına gelmez; ham logit farkları da okunmalıdır. Ekran sözlükteki ilk sekiz indeksi örnekler, bunlar en güçlü sekiz aday değildir. Sonraki token sabit bir kelime olmak zorunda değildir ve saldırı başarısı kabul şartı yapılmaz. Çalıştır keşif kaydını `kabul=False` saklar; Kontrol bütün koşullar sağlanınca kabul verir. Model yokluğu veya yarım deney PASS değildir. İşlem CPU'da çalışır, yeni sunucu başlatmaz ve disk ağırlıklarını değiştirmez.

Activation steering çalışma sırasındaki aktivasyona yön vektörünün belirli katsayıyla katlanmasını ekler. Temel model ağırlıkları değişmez. Katsayının işareti ve büyüklüğü müdahalenin yönünü ve şiddetini belirler.

Sınırsız müdahale temsili bozabilir. Son görevde müdahalenin L2 normu bir üst sınırla kısıtlanır. Norm eşiğin üzerindeyse vektör eşiğe ölçeklenir; eşitlikte kırpma yapılmaz.
:::

::: tahmin Yön ve yöneltmeyi tahmin et
Üç çıktı satırını yaz:

```python
print([2 - 1, 0 - 0, 0 - 0])
print(round((2 ** 2) ** 0.5, 6))
print([round(1 + 0.5 * 2, 6), round(2 + 0.5 * 0, 6)])
```

???

```cikti
[1, 0, 0]
2.0
[2.0, 2.0]
```

İlk satır aktivasyon farkını, ikinci satır L2 normunu, üçüncü satır katsayılı yön eklemeyi gösterir.
:::

::: gorev 1 · Ortalama aktivasyon farkından birim yön çıkar
`yon_cikar(pozitif, negatif)` işlevini yaz. İki girdi de üç adet, üç sayılık vektör içeren listedir; bool değerler geçersizdir. Geçersiz veri veya sıfır fark normunda `ValueError` yükselt.

Her gruptaki vektörlerin öğe bazında ortalamasını al, pozitif ortalama eksi negatif ortalamayı hesapla ve farkı L2 normuna böl. Üç öğeli birim yönü altı ondalığa yuvarla. Girdileri değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-15")
```

```starter
from ai_temel_veri import json_yukle,metin_yukle

def yon_cikar(pozitif,negatif):
    # KUSURLU BAŞLANGIÇ KODU: ortalama farkı hesaplar fakat birim uzunluğa normalize etmez.
    return [round(sum(p[j] for p in pozitif)/len(pozitif)-sum(n[j] for n in negatif)/len(negatif),6) for j in range(len(pozitif[0]))]

v=json_yukle("veri/aktivasyon.json")
print("Sentetik ham dosya:\n",metin_yukle("veri/aktivasyon.json"))
print("Yön:",yon_cikar(v["pozitif"],v["negatif"]))
```

```test
import copy
P = [[2, 0, 0], [2, 0, 0], [2, 0, 0]]
N = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
def sozlesme(fn):
    try:
        if fn(P, N) != [1.0, 0.0, 0.0] or fn(N, P) != [-1.0, 0.0, 0.0]:
            return False
        p = [[1, 1, 0], [0, 1, 0], [1, 0, 0]]
        if fn(p, N) != [0.707107, 0.707107, 0.0] or fn([[3, 0, 0]] * 3, [[0, 1, 0]] * 3) != [0.948683, -0.316228, 0.0]:
            return False
        once=copy.deepcopy((p,N));fn(p,N)
        if (p,N)!=once:return False
        if fn(list(reversed(p)),N)!=fn(p,N):return False
        for args in [(None, N), (P[:2], N), ([(1, 0, 0)] * 3, N), ([['a', 0, 0]] * 3, N), ([[1, 0]] * 3, N), ([[1, True, 0]] * 3, N), ([[float('nan'), 0, 0]] * 3, N), (P, [[float('inf'), 0, 0]] * 3), (P, None), (P, N[:2]), (N, N)]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(yon_cikar), "ortalama fark, normalizasyon ve yön şeması korunmalı")
def m_pozitif(p, n):
    return yon_cikar(n, p)
def m_negatif(p, n):
    return yon_cikar(p, [[x[0] + 1, x[1], x[2]] for x in n])
def m_boyut(p, n):
    return yon_cikar(p + p[:1], n)
for ad, mutant in [("grupları ters çeviren", m_pozitif), ("negatifi bozan", m_negatif), ("boyutu bozan", m_boyut)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle,metin_yukle

def yon_cikar(pozitif, negatif):
    import math
    def grup(g):
        return isinstance(g, list) and len(g) == 3 and all(isinstance(v, list) and len(v) == 3 and all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in v) for v in g)
    if not grup(pozitif) or not grup(negatif):
        raise ValueError("aktivasyon grubu geçersiz")
    p = [sum(v[j] for v in pozitif) / 3 for j in range(3)]
    n = [sum(v[j] for v in negatif) / 3 for j in range(3)]
    fark = [p[j] - n[j] for j in range(3)]
    norm = math.sqrt(sum(x * x for x in fark))
    if norm == 0:
        raise ValueError("sıfır yön")
    return [round(x / norm, 6) for x in fark]

if __name__ == "__main__":
    v=json_yukle("veri/aktivasyon.json")
    print("Sentetik ham dosya:\n",metin_yukle("veri/aktivasyon.json"))
    print("Yön:",yon_cikar(v["pozitif"],v["negatif"]))
```

```hint
İki grubun ortalamasını ayrı hesapla, farkı çıkar; norm sıfır değilse her öğeyi norma böl.
```
:::

::: gorev 2 · Aktivasyona katsayılı yön ekle
`yonelt(aktivasyon, yon, katsayi)` işlevini yaz. Aktivasyon ve yön üç sayılık vektörlerdir. Katsayı bool olmayan -2 ile 2 arasında sayıdır; sınırlar dahildir. Geçersiz veride `ValueError` yükselt.

Her öğede `aktivasyon + katsayi*yon` hesapla ve altı ondalığa yuvarla. Yeni vektör döndür; girdileri değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-15")
```

```starter
from ai_temel_veri import json_yukle,metin_yukle

def yonelt(aktivasyon,yon,katsayi):
    # KUSURLU BAŞLANGIÇ KODU: negatif katsayının işaretini kaybeder.
    return [round(a+abs(katsayi)*y,6) for a,y in zip(aktivasyon,yon)]

v=json_yukle("veri/aktivasyon.json")
print("Sentetik yöneltme:",yonelt(v["aktivasyon"],v["yon"],v["katsayi"]))
```

```test
def sozlesme(fn):
    try:
        if fn([1, 2, 3], [1, 0, -1], 0.5) != [1.5, 2.0, 2.5] or fn([1, 1, 1], [1, 1, 1], 0) != [1.0, 1.0, 1.0]:
            return False
        if fn([0, 0, 0], [1, 1, 1], 2) != [2.0, 2.0, 2.0] or fn([0, 0, 0], [1, 1, 1], -2) != [-2.0, -2.0, -2.0]:
            return False
        if fn([0, 0, 0], [1, 0, 0], 1 / 3) != [0.333333, 0.0, 0.0]:
            return False
        aa=[1,2,3];yy=[1,0,-1];fn(aa,yy,-1)
        if aa!=[1,2,3] or yy!=[1,0,-1]:return False
        for args in [(None, [1, 0, 0], 1), ([1, 0], [1, 0, 0], 1), (['a', 0, 0], [1, 0, 0], 1), ([1, True, 0], [1, 0, 0], 1), ([float('nan'), 0, 0], [1, 0, 0], 1), ([1, 0, 0], [float('inf'), 0, 0], 1), ([1, 0, 0], [1, 0, 0], '1'), ([1, 0, 0], [1, 0, 0], float('nan')), ([1, 0, 0], [1, 0, 0], float('inf')), ([1, 0, 0], None, 1), ([1, 0, 0], [1, 0, 0], 2.1), ([1, 0, 0], [1, 0, 0], -2.1), ([1, 0, 0], [1, 0, 0], True)]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(yonelt), "katsayı, yön işareti ve aktivasyon şeması korunmalı")
def m_aktivasyon(a, y, k):
    return yonelt(list(reversed(a)), y, k)
def m_yon(a, y, k):
    return yonelt(a, list(reversed(y)), k)
def m_katsayi(a, y, k):
    return yonelt(a, y, k * 2)
for ad, mutant in [("aktivasyonu bozan", m_aktivasyon), ("yönü bozan", m_yon), ("katsayıyı bozan", m_katsayi)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle,metin_yukle

def yonelt(aktivasyon, yon, katsayi):
    import math
    def vektor(v):
        return isinstance(v, list) and len(v) == 3 and all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in v)
    if not vektor(aktivasyon) or not vektor(yon):
        raise ValueError("vektör geçersiz")
    if not isinstance(katsayi, (int, float)) or isinstance(katsayi, bool) or not -2 <= katsayi <= 2:
        raise ValueError("katsayı geçersiz")
    return [round(a + katsayi * y, 6) for a, y in zip(aktivasyon, yon)]

if __name__ == "__main__":
    v=json_yukle("veri/aktivasyon.json")
    print("Sentetik yöneltme:",yonelt(v["aktivasyon"],v["yon"],v["katsayi"]))
```

```hint
İki vektörü `zip` ile eşle; her çiftte katsayılı yönü aktivasyona ekle.
```
:::

::: gorev 3 · Müdahale normunu eşikle sınırla
`sinirli_yoneltme(aktivasyon, yon, katsayi, esik)` işlevini yaz. Vektörler ve katsayı ikinci görevdeki biçimdedir. Eşik bool olmayan 0–4 arası sayıdır; sınırlar dahildir. Geçersiz veride `ValueError` yükselt.

Müdahale `katsayi*yon` vektörünün L2 normu eşiği aşıyorsa müdahaleyi eşik/norm oranıyla ölçekle; aşmıyorsa aynen kullan. Aktivasyona ekleyip altı ondalığa yuvarla. `{"vektor":V,"kirpildi":K}` döndür; K yalnız norm eşikten büyükse True olur.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-15")
```

```starter
from ai_temel_veri import json_yukle,metin_yukle

def sinirli_yoneltme(aktivasyon,yon,katsayi,esik):
    # KUSURLU BAŞLANGIÇ KODU: müdahale yerine başlangıç aktivasyonu dahil bütün sonucu sınırlar.
    import math
    v=[a+katsayi*y for a,y in zip(aktivasyon,yon)]
    norm=math.hypot(*v)
    kirpildi=norm>esik
    if kirpildi:v=[x*esik/norm for x in v]
    return {"vektor":[round(x,6) for x in v],"kirpildi":kirpildi}

v=json_yukle("veri/aktivasyon.json")
print("Sentetik sınırlı yöneltme:",sinirli_yoneltme(v["aktivasyon"],v["yon"],v["katsayi"],v["esik"]))
x=v["buyuk_baslangic"]
print("Büyük başlangıç:",sinirli_yoneltme(x["aktivasyon"],x["yon"],x["katsayi"],x["esik"]))
```

```test
def sozlesme(fn):
    try:
        if fn([1, 0, 0], [1, 0, 0], 2, 1) != {"vektor": [2.0, 0.0, 0.0], "kirpildi": True}:
            return False
        if fn([1, 0, 0], [1, 0, 0], 1, 1) != {"vektor": [2.0, 0.0, 0.0], "kirpildi": False} or fn([1, 0, 0], [1, 0, 0], 1, 0) != {"vektor": [1.0, 0.0, 0.0], "kirpildi": True}:
            return False
        if fn([0, 0, 0], [0, 0, 0], 2, 0) != {"vektor": [0.0, 0.0, 0.0], "kirpildi": False} or fn([0, 0, 0], [1, 1, 1], 1, 1 / 3) != {"vektor": [0.19245, 0.19245, 0.19245], "kirpildi": True}:
            return False
        if fn([0, 0, 0], [1, 0, 0], 1 / 7, 1) != {"vektor": [0.142857, 0.0, 0.0], "kirpildi": False} or fn([0, 0, 0], [1, 0, 0], -2, 4) != {"vektor": [-2.0, 0.0, 0.0], "kirpildi": False}:
            return False
        aa=[10,0,0];yy=[1,0,0]
        if fn(aa,yy,0.5,1)!={"vektor":[10.5,0.0,0.0],"kirpildi":False}:return False
        if aa!=[10,0,0] or yy!=[1,0,0]:return False
        for args in [(None, [1, 0, 0], 1, 1), ([1, 0], [1, 0, 0], 1, 1), (["a", 0, 0], [1, 0, 0], 1, 1), ([1, True, 0], [1, 0, 0], 1, 1), ([float("nan"), 0, 0], [1, 0, 0], 1, 1), ([1, 0, 0], [float("inf"), 0, 0], 1, 1), ([1, 0, 0], [1, 0], 1, 1), ([1, 0, 0], [1, True, 0], 1, 1), ([1, 0, 0], None, 1, 1), ([1, 0, 0], [1, 0, 0], float("nan"), 1), ([1, 0, 0], [1, 0, 0], -2.1, 1), ([1, 0, 0], [1, 0, 0], 2.1, 1), ([1, 0, 0], [1, 0, 0], True, 1), ([1, 0, 0], [1, 0, 0], "1", 1), ([1, 0, 0], [1, 0, 0], 1, "1"), ([1, 0, 0], [1, 0, 0], 1, float("nan")), ([1, 0, 0], [1, 0, 0], 1, -0.1), ([1, 0, 0], [1, 0, 0], 1, 4.1), ([1, 0, 0], [1, 0, 0], 1, True)]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(sinirli_yoneltme), "norm eşiği, kırpma kararı ve sıfır yön korunmalı")
def m_yon(a, y, k, e):
    return sinirli_yoneltme(a, list(reversed(y)), k, e)
def m_katsayi(a, y, k, e):
    return sinirli_yoneltme(a, y, k * 2, e)
def m_esik(a, y, k, e):
    return sinirli_yoneltme(a, y, k, 4)
for ad, mutant in [("yönü bozan", m_yon), ("katsayıyı bozan", m_katsayi), ("eşiği bozan", m_esik)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle,metin_yukle

def sinirli_yoneltme(aktivasyon, yon, katsayi, esik):
    import math
    def vektor(v):
        return isinstance(v, list) and len(v) == 3 and all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in v)
    if not vektor(aktivasyon) or not vektor(yon):
        raise ValueError("vektör geçersiz")
    if not isinstance(katsayi, (int, float)) or isinstance(katsayi, bool) or not -2 <= katsayi <= 2:
        raise ValueError("katsayı geçersiz")
    if not isinstance(esik, (int, float)) or isinstance(esik, bool) or not 0 <= esik <= 4:
        raise ValueError("eşik geçersiz")
    mudahale = [katsayi * y for y in yon]
    norm = math.sqrt(sum(x * x for x in mudahale))
    kirpildi = norm > esik
    if kirpildi:
        mudahale = [x * esik / norm for x in mudahale]
    return {"vektor": [round(a + m, 6) for a, m in zip(aktivasyon, mudahale)], "kirpildi": kirpildi}

if __name__ == "__main__":
    v=json_yukle("veri/aktivasyon.json")
    print("Sentetik sınırlı yöneltme:",sinirli_yoneltme(v["aktivasyon"],v["yon"],v["katsayi"],v["esik"]))
    x=v["buyuk_baslangic"]
    print("Büyük başlangıç:",sinirli_yoneltme(x["aktivasyon"],x["yon"],x["katsayi"],x["esik"]))
```

```hint
Norm eşikten büyükse bütün müdahale öğelerini aynı `esik/norm` oranıyla çarp; sıfır normda bölme yapma.
```
:::

::: anlat Gerçek deney: gerçek residual aktivasyona müdahale
Önceki yönler üç boyutlu hazır vektörlerdi. Şimdi kurulu SmolLM2 modelinin iki decoder katmanında gerçek metinlerden son-token aktivasyonları yakalanır. İki sentetik metin grubunun ortalamaları arasındaki fark normalize edilerek her katman için gerçek birim yön çıkarılır. Bu hazırlığı laboratuvar yapar ve yön tensörünü sana verir; yönler sabit fixture değildir.

Sen bu yönü gerçek model çalışırken forward hook ile yalnız **son tokenın** katman çıkışına ekleyeceksin. Müdahale, katsayı×yön olup L2 sınırını aşarsa ölçeklenir. Temel ağırlıklar güncellenmez; bütün tokenlara eklemek veya modeli eğitmek farklı işlemdir. Hook `finally` içinde kaldırılmalıdır; hata sonrası sonraki deneye sızan müdahale ciddi ölçüm hatasıdır.

Bu, bir aktivasyon müdahalesinin mekanik kabulüdür. Seçilen sentetik metinler “sakin/acil” örnekleridir; ortaya çıkan yönün evrensel anlam, refusal veya güvenlik yönü olduğu iddia edilmez. Müdahale sonrası argmax aynı kalabilir; belirli bir sözcük veya saldırı başarısı test şartı değildir. TransformerLens/repeng kullanılmaz; gerçek model ve PyTorch hook'ları kullanılır.

Kaynaklar: [Zou vd. 2023 — Representation Engineering: A Top-Down Approach to AI Transparency (arXiv:2310.01405)](https://arxiv.org/abs/2310.01405), [Turner vd. 2023 — Steering Language Models With Activation Engineering (arXiv:2308.10248)](https://arxiv.org/abs/2308.10248).
:::

::: gorev Gerçek deney · Ağırlıkları değiştirmeden son-token aktivasyonunu yönelt
`gercek_yonelt(tok, model, metin, yon, katman, katsayi, esik)` işlevini yaz. Laboratuvar sana gerçek tokenizer/model ve hedef katmandan türetilmiş sonlu, birim uzunlukta 1D `yon` tensörünü verir. `model.model.layers[katman]` hedef decoder katmanıdır. Bu modelin uyumlu kurulduğunu varsayabilirsin.

- `metin` boşluk dışı karakter içeren str ve gerçek tokenizer'la 1–24 token olmalıdır. Metni değiştirme.
- `katman` bool olmayan geçerli decoder indeksi; `katsayi` bool olmayan sonlu sayı, -2..2; `esik` bool olmayan sonlu sayı, 0..1. Diğer değerlerde `ValueError` yükselt.
- Önce `use_cache=False` ve `torch.no_grad()` ile müdahalesiz gerçek son konum logitlerini hesapla.
- `delta=katsayi*yon`; normu eşikten **büyükse** `esik/norm` ile ölçekle. `kirpildi` bu karşılaştırmanın bool sonucudur. Sıfır normda bölme yapma.
- Hedef katmana forward hook tak. Katman çıktısını klonla, yalnız `[:, -1, :]` dilimine delta'yı aynı dtype/cihazda ekle. Çıktı tuple ise diğer öğeleri koru. Gerçek uygulanan son-token farkının L2 normunu kaydet.
- Aynı girdide ikinci gerçek ileri hesabı yap ve hook'u başarılı/başarısız bütün yollarda kaldır.
- Tam şu alanları döndür: `kirpildi` bool, `kayma_normu` float, `temel_logitler` ve `yeni_logitler` (her biri son konumun sözlükteki ilk 8 float logiti), `temel_en_olasi` ve `yeni_en_olasi` (tam logit argmax'ları, int).

Ağırlıkları, yön tensörünü, mevcut hookları veya önceki tokenların aktivasyonlarını değiştirme. Test, sonraki katmanın girdisini de gözler; sadece doğru görünen bir rapor yeterli değildir.

```meta
motor: ai-gercek
gereksinim: torch
timeout: 300
```

```starter
import ai_lab

def gercek_yonelt(tok, model, metin, yon, katman, katsayi, esik):
    return {}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_15 as lab15
    lab15.goster(gercek_yonelt)
```

```test
import copy
import math
import random
import ai_lab
from sandbox import ai_gercek_ai_temel_15 as lab15
sonuclar=[]
def kontrol(c,mesaj):
    sonuclar.append(bool(c));return ok(c,mesaj)
import ast
yasak=("referans_yurut","getattr","kanit_yaz")
ihlal=ai_lab.kod_denetimi(src,yasak)
try:
    for node in ast.walk(ast.parse(src)):
        if isinstance(node,ast.ImportFrom) and any(a.name in yasak or a.name=="*" for a in node.names):
            ihlal.append("test oracle ithali")
except SyntaxError:ihlal.append("sözdizimi")
kontrol(not ihlal,"Kendi steering hookunu yaz; test oracle'ı ithal edilmez")
if ihlal:stop()
fn=need("gercek_yonelt")
try:
    import torch
    tok,model,yonler,bilgi=lab15.hazirla()
except (ImportError,ai_lab.GercekLabYok) as e:
    kontrol(False,"GERÇEK AKTİVASYON YOK: "+str(e));stop()
bas_agirlik=lab15.agirlik_ozeti(model)
layers=model.model.layers
metin="A careful report "+str(random.SystemRandom().randrange(100,999))+" about a river."
ayarlar=[(0,0.5,0.2),(2,-1.0,0.3),(0,0.0,0.4),(2,0.25,1.0),(0,0.5,0.0)]

beklenen=[lab15.referans_yurut(tok,model,metin,yonler[k],k,a,e) for k,a,e in ayarlar]
def ayni(a,b):
    if not isinstance(a,dict) or set(a)!=set(b) or type(a["kirpildi"]) is not bool or a["kirpildi"]!=b["kirpildi"]:
        return False
    if type(a["kayma_normu"]) is not float or not math.isfinite(a["kayma_normu"]) or abs(a["kayma_normu"]-b["kayma_normu"])>1e-6:
        return False
    for k in ["temel_en_olasi","yeni_en_olasi"]:
        if type(a[k]) is not int or a[k]!=b[k]:return False
    for k in ["temel_logitler","yeni_logitler"]:
        if not isinstance(a[k],list) or len(a[k])!=8 or any(type(v) is not float or not math.isfinite(v) for v in a[k]):return False
        if not torch.allclose(torch.tensor(a[k],dtype=torch.float64),torch.tensor(b[k],dtype=torch.float64),atol=1e-4,rtol=1e-5):return False
    return True
ids=tok(metin,add_special_tokens=False)["input_ids"]
def hook_sayilari():
    return [(len(m._forward_hooks),len(m._forward_pre_hooks)) for m in model.modules()]
def sozlesme(f):
    try:
        for (k,a,e),(ref,target) in zip(ayarlar,beklenen):
            before_hooks=hook_sayilari();before_versions=[p._version for p in model.parameters()]
            d=yonler[k].clone();d_once=d.clone();seen=[];current=[]
            def root(module,args,kwargs):
                v=args[0] if args else kwargs.get("input_ids")
                current[:]=v.detach().tolist() if isinstance(v,torch.Tensor) else []
                if torch.is_grad_enabled() or kwargs.get("use_cache") is not False:raise ValueError("no_grad/use_cache sözleşmesi")
            def downstream(module,args,kwargs):
                v=args[0] if args else kwargs.get("hidden_states")
                if current==[ids] and isinstance(v,torch.Tensor):seen.append(v.detach().clone())
            h0=model.register_forward_pre_hook(root,with_kwargs=True)
            h1=layers[k+1].register_forward_pre_hook(downstream,with_kwargs=True)
            try:r=f(tok,model,metin,d,k,a,e)
            finally:h0.remove();h1.remove()
            if not ayni(r,ref) or not any(v.shape==target.shape and torch.allclose(v,target,atol=1e-6,rtol=1e-6) for v in seen):return False
            if not torch.equal(d,d_once) or hook_sayilari()!=before_hooks or [p._version for p in model.parameters()]!=before_versions:return False
        hs=hook_sayilari();calls=[];raised=False
        def hata_enjekte(module,args,kwargs):
            calls.append(True)
            if len(calls)==2:raise RuntimeError("PAFTA_FAIL_FORWARD")
        he=model.register_forward_pre_hook(hata_enjekte,with_kwargs=True)
        try:
            try:f(tok,model,metin,yonler[0].clone(),0,0.5,0.2)
            except RuntimeError as exc:raised=str(exc)=="PAFTA_FAIL_FORWARD"
        finally:he.remove()
        if not raised or hook_sayilari()!=hs:return False
        tam_esik=float(torch.linalg.vector_norm(0.5*yonler[0]).item())
        if f(tok,model,"Hello",yonler[0].clone(),0,-2,1.0)["kirpildi"] is not True or f(tok,model," the"*24,yonler[0].clone(),0,2,1.0)["kirpildi"] is not True or f(tok,model,"Hello",yonler[0].clone(),0,0.5,tam_esik)["kirpildi"] is not False:return False
        import types
        class _TLayer(torch.nn.Module):
            def forward(self,x):
                return (x.clone(),"kv",7)
        class _TModel(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.model=types.SimpleNamespace(layers=torch.nn.ModuleList([_TLayer()]))
            def forward(self,inp,use_cache=False):
                x=torch.zeros((inp.shape[0],inp.shape[1],8),dtype=torch.float32)
                o=self.model.layers[0](x)
                if not (isinstance(o,tuple) and len(o)==3 and o[1:]==("kv",7) and isinstance(o[0],torch.Tensor)):raise RuntimeError("tuple bozuldu")
                return types.SimpleNamespace(logits=o[0])
        _tm=_TModel();_td=torch.tensor([1.0]+[0.0]*7)
        if f(tok,_tm,"Hello",_td,0,0.5,1.0)["kirpildi"] is not False:return False
        for k,a,e,text in [(-1,1,0.5,metin),(True,1,0.5,metin),(len(layers),1,0.5,metin),
                            (0,True,0.5,metin),(0,"1",0.5,metin),(0,float("nan"),0.5,metin),(0,-2.5,0.5,metin),(0,3,0.5,metin),
                            (0,1,-1,metin),(0,1,1.5,metin),(0,1,"0.5",metin),(0,1,True,metin),(0,1,float("nan"),metin),(0,1,float("inf"),metin),
                            (0,1,0.5,""),(0,1,0.5,"   "),(0,1,0.5,None),(0,1,0.5," the"*25),(0,1,0.5," the"*40)]:
            hs=hook_sayilari()
            try:f(tok,model,text,yonler[0],k,a,e);return False
            except ValueError:
                if hook_sayilari()!=hs:return False
        return True
    except Exception:return False
kontrol(sozlesme(fn),"gerçek son-token müdahalesi aşağı katmana ulaşıyor; ağırlık/yön/hooklar korunuyor")
sabit=copy.deepcopy(beklenen[0][0])
def yon_degistir(t,m,text,d,k,a,e):return fn(t,m,text,d,k,-a,e)
def kirpma_yok(t,m,text,d,k,a,e):return fn(t,m,text,d,k,a,1.0)
def hepsi(t,m,text,d,k,a,e):return lab15.referans_yurut(t,m,text,d,k,a,e,hepsi=True)[0]
for ad,mutant in [("boş kod/işlev",None),("boş sözlük",lambda *a:{}),
                  ("sabit gerçek rapor",lambda *a:copy.deepcopy(sabit)),
                  ("yön işareti ters",yon_degistir),("norm sınırı yok",kirpma_yok),
                  ("bütün tokenlara müdahale",hepsi)]:
    kontrol(not sozlesme(mutant),"hatalı çözüm reddedilmeli: "+ad)
ciktilar=[fn(tok,model,metin,yonler[k],k,a,e) for k,a,e in ayarlar] if all(sonuclar) else []
kontrol(lab15.agirlik_ozeti(model)==bas_agirlik,"bütün gerçek model parametrelerinin SHA-256 özeti değişmedi")
ai_lab.kanit_yaz("temel-15-steering",{
    "kaynak":"gercek","kabul":all(sonuclar),"model_bilgisi":bilgi,
    "ayarlar":{"metin":metin,"katman_katsayi_esik":[list(a) for a in ayarlar]},"ciktilar":ciktilar,
    "agirlik_oncesi_sonrasi_sha256":bas_agirlik,"olculen":"gerçek residual forward hook, aşağı katman aktivasyonu ve logit değişimi",
    "sinir":"evrensel anlam/refusal/güvenlik veya TransformerLens/repeng kabulü değildir",
    "temizlik":"deney hookları kaldırıldı; CPU, harici süreç/sunucu/indirme yok"})
for a,r in zip(ayarlar,ciktilar):print("katman/katsayı/eşik",a,"uygulanan norm",r["kayma_normu"],"kırpıldı",r["kirpildi"],"argmax",r["temel_en_olasi"],"→",r["yeni_en_olasi"])
```

```solution
import ai_lab
import math
import torch

def gercek_yonelt(tok, model, metin, yon, katman, katsayi, esik):
    layers=model.model.layers
    if not isinstance(metin,str) or not metin.strip() or type(katman) is not int or not 0<=katman<len(layers):
        raise ValueError("metin veya katman geçersiz")
    if isinstance(katsayi,bool) or not isinstance(katsayi,(int,float)) or not -2<=katsayi<=2:
        raise ValueError("katsayı geçersiz")
    if isinstance(esik,bool) or not isinstance(esik,(int,float)) or not 0<=esik<=1:
        raise ValueError("eşik geçersiz")
    ids=tok(metin,add_special_tokens=False)["input_ids"]
    if not 1<=len(ids)<=24:raise ValueError("token sayısı geçersiz")
    with torch.no_grad():before=model(torch.tensor([ids]),use_cache=False).logits[0,-1].double()
    delta=katsayi*yon
    norm=torch.linalg.vector_norm(delta)
    clipped=bool(norm.item()>esik)
    if clipped:delta=delta*(esik/norm)
    norms=[]
    def steer(module,args,out):
        h=out[0] if isinstance(out,tuple) else out
        new=h.clone()
        new[:,-1,:]+=delta.to(dtype=h.dtype,device=h.device)
        norms.append(float(torch.linalg.vector_norm((new[:,-1,:]-h[:,-1,:]).double()).item()))
        return (new,)+out[1:] if isinstance(out,tuple) else new
    handle=layers[katman].register_forward_hook(steer)
    try:
        with torch.no_grad():after=model(torch.tensor([ids]),use_cache=False).logits[0,-1].double()
    finally:handle.remove()
    return {"kirpildi":clipped,"kayma_normu":norms[0],"temel_logitler":before[:8].tolist(),
            "yeni_logitler":after[:8].tolist(),"temel_en_olasi":int(before.argmax().item()),
            "yeni_en_olasi":int(after.argmax().item())}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_15 as lab15
    lab15.goster(gercek_yonelt)
```

```hint
Forward hook çıktı yerine yeni bir çıktı döndürebilir. `h.clone()` üzerinde son tokenı değiştir ve handle'ı `finally` ile kaldır. Delta'nın dtype'ını katman çıktısına uydur; normu gerçekten uygulanan farktan ölç.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Karşıt çiftlerden yön çıkarma (`Activation Steering`) (30 sn).** "Pozitif ve negatif örneklerin ara katman (`residual stream`) aktivasyon ortalamalarının farkı $\hat{d} = \frac{\mu_+ - \mu_-}{\|\mu_+ - \mu_-\|_2}$ o davranışla ilişkili doğrusal bir birim yön verir."
2. **Ağırlıksız çalışma anı müdahalesi ve norm sınırı (35 sn).** "Model ağırlıklarını hiç güncellemeden, ileri geçişte seçilen katmana $h \leftarrow h + \alpha \hat{d}$ eklenir; müdahale normu eşikle kırpılmazsa temsil uzayından kopup anlamsız token çökmesine yol açar."
3. **Çift yönlü güvenlik etkisi (30 sn).** "Temsil mühendisliği güvenlik hizalamasını güçlendirmek veya iç durum izlemek için kullanılabildiği gibi, açık ağırlıklı modellerde reddetme (`refusal`) yönünü bastırmak için de istismar edilebilir."
4. **Soru (25 sn).** "Müdahale normunu sınırlarken toplam aktivasyon $h + \alpha \hat{d}$ yerine neden yalnızca eklenen $\alpha \hat{d}$ vektörünün normunu kırpmalıyız?"
:::
