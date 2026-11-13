---
id: ai-temel-10
title: "LoRA ve Parametre Verimli Fine-Tuning"
summary: Sentetik LoRA matris çarpımı, temel ağırlıkla birleştirme ve adaptör parametre maliyeti hesapla.
esleme: ai-temel-09, ai-temel-11, ai-matematik-09
timeout: 45
---

::: anlat LoRA düşük ranklı bir fark öğrenir

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| LoRA dondurulmuş ağırlığa düşük ranklı güncelleme ekler | İlk üç görev görünür sentetik matris JSON; final kurulu SmolLM2 ile gerçek autograd ve Adam eğitimi | Küçük matris hesabı tek başına model eğitimi değildir; ilk örneğin rank 2/2 matrisi tasarruf garantisi vermez |
| Adaptör birleştirme ve öğrenme ayrı ölçülür | Final elle yazılan sınıfı q_proj/v_proj katmanlarına takar; 40 adım CPU eğitimi | PEFT, bitsandbytes, QLoRA çalıştırılmaz; tek cümleyi öğrenmek genel uzmanlık veya güvenlik başarısı değildir |

> [!NOT]
> `veri/lora.json` elle hazırlanmış sentetik matrislerdir; canlı eğitim kaydı değildir. İlk üç görev aynı dosyayı okur. Setup her Run/Check için geçici kopya kurar; kalıcılık yoktur. Kaynağı editörde aç veya yüklenen sözlüğü kodda değiştirip Run dene. Gizli testler ayrıdır. Final önceden kurulu yerel modeli gerçekten eğitir; adaptör/öğrenci ağırlıkları kalıcı kaydedilmez, yeni indirme yoktur.

LoRA temel ağırlığı dondurup güncellemeyi iki küçük matrisin çarpımıyla temsil eder. `B @ A` temel ağırlıkla aynı boyutta bir fark üretir; rank arttıkça adaptör kapasitesi ve parametre maliyeti artar. Ölçek katsayısı bu farkın etkisini ayarlar.

İlk üç görev saf Python ile çalışır; final Transformers/torch ve elle yazılan adaptörle gerçek eğitim yapar. PEFT ve bitsandbytes kullanılmaz. İki çarpı iki sentetik matrisler, matris çarpımının boyutunu ve birleştirme sırasını görünür kılar. Gerçek projelerde hedef modül seçimi ayrıca deney gerektirir.
:::

::: anlat Birleştirme ile eğitim parametre sayısı farklıdır

Önce lora.json dosyasındaki temel, a, b ve olcek alanlarını aç. İlk görev güncelleme matrisini hesaplar. Çarpım sırası B@A olmalıdır; aynı boyutlu iki matrisin ters sırası da çalışabildiği için yalnız boyut denetimi yanlış hesabı yakalamaz. Dosyadaki asimetrik değerler bu farkı görünür kılar. İkinci görev aynı güncellemeyi temel ağırlığa ekler. Güncellemenin dosyadaki önceden hesaplanmış kopyası yalnız görevleri bağımsız çalıştırabilmek içindir; birinci görevin işlevini diğer editörden import etmen gerekmez. Üçüncü görev farklı boyut/rank örneklerinden eğitilen parametre oranını çıkarır.

Bu küçük örnekte iki matris de ikiye ikidir. Gerçek tasarruf için rankın büyük giriş/çıkış boyutlarından küçük olması beklenir; öğretim örneğinde kare matris kullanmak kendiliğinden düşük maliyet sağlamaz. Maliyet işlevi bu yüzden oran birden büyük olduğunda da doğru sayıyı döndürür. Örneğin küçük bir katmanda yüksek rank seçmek temel katmandan fazla adaptör parametresi üretebilir. Üçüncü görev yalnız sayım formülünü öğretir ve rank 3/çıkış 2 gibi karşılaştırma örneklerini kabul eder; final LoRA sınıfı ise rankı min(giriş, çıkış) ile sınırlar. İki sözleşmeyi birbirine karıştırma. Parametre oranı toplam RAM veya VRAM oranı değildir. Aktivasyonlar, gradyanlar, optimizer durumları ve temel modelin yüklü ağırlıkları bellekte yer kaplar. Bu ders bir tepe bellek ölçümü yapmıyor; yalnız parametre sayısını ve eğitimi raporluyor.

Finalde A biçimi rank×giriş, B biçimi çıkış×rank olur. PyTorch Linear ağırlığı çıkış×giriş saklandığından B@A bu ağırlığa eklenebilir. İleri hesapta ise son boyutu giriş olan x önce A'nın, sonra B'nin transpozu ile çarpılır. B sıfır başlatılırsa adaptörün ilk çıktısı sıfırdır ve takma anındaki model kaybı değişmez. A da sıfır başlatılırsa öğrenmenin başlangıç gradyan yolu sorunlu hale gelir; bu derste A küçük rastgele değerlerle başlatılır. B sıfırken ilk adımda A gradyanının sıfır olması tek başına hata değildir; B güncellendikten sonra iki matris birlikte öğrenebilir.

Temel parametreleri dondurmak, ileri hesabı bütünüyle no_grad içine almak demek değildir. İleri grafiği adaptörlere gradyan taşımalıdır; yalnız temel ağırlıkların requires_grad bayrağı kapalı kalır. Test gerçek q_proj ve v_proj kopyalarında biçim, ölçek, ileri hesap, gradyan ve birleştirmeyi ayrı denetler. Birleştirme yeni bir tensör döndürür; temele yerinde ekleme yaparsan tekrar birleştirmede aynı farkı iki kez uygulayabilirsin. Adaptörlü ve birleşik modelin logit farkının küçük olması bu uygulama kontrolüdür; iki yolun farklı cihaz ve çekirdeklerde bit düzeyinde eşitliği beklenmez.

Gerçek eğitim yalnız sentetik bir laboratuvar cümlesini kırk Adam adımında tekrarlar. Hedef kaybın düşmesi bu cümlenin öğrenildiğini gösterir; genelleme göstermez. İlgisiz kontrol metninin kaybı da önce ve sonra kaydedilir. Bu değer bozulursa dar eğitimin başka davranışlara maliyeti olabileceğini görürsün; tek kontrol metni bütün yan etkileri kapsamaz. Üretilen devam metni bir bulgudur, belli bir cümleyi yazmak zorunlu geçme şartı değildir. Öğrencinin sınıfı öğrenme hesabını doğru yapmalı; gerçek eğitim çalışmamışsa kabul verilmez.

Güvenlik açısından adaptör model davranışını değiştiren ayrı bir bileşendir. Dondurulmuş temel, davranışın değişmeyeceğini garanti etmez; zaten adaptörün amacı davranışı değiştirmektir. Bir savunmayı yalnız temel model adını kontrol ederek değerlendirmek bu bileşeni gözden kaçırır. Bu deney zararlı yük veya backdoor eğitmez; sentetik bir cümlede öğrenme mekanizmasını görünür kılar. Daha sonra adaptör kökeni ve bütünlük denetimini tartışırken ağırlık kimliği ve eğitim ayarlarının neden kaydedildiğini bu örnekle bağlayabilirsin.

Kanıtta eğitim/kontrol metinleri, tokenlar, tohum, learning rate, rank/alfa, hedef modüller ve kırk adımın kaybı bulunur. Bütün temel parametrelerin eğitim öncesi/sonrası özetleri ve ortak modelin durumu denetlenir. Deney modelin bir kopyasını eğitir; ortak önbellekteki modeli değiştirmez. Çalıştır yalnız keşif kaydıdır; Kontrol et sözleşmeleri ve gerçek eğitimi birlikte kabul eder. Adapter dosyasının kalıcı kaydedildiği veya belleğin tamamının ölçüldüğü iddia edilmez.

Inference öncesinde LoRA farkı temel ağırlığa eklenebilir. Böylece ayrı adaptör çağrısı yerine tek birleşik ağırlık kullanılır. Temel ağırlığı değiştirmeden yeni fark döndürmek deneylerin tekrarlanmasını kolaylaştırır.

Eğitilen parametre sayısı rank çarpı giriş ve çıkış boyutlarının toplamıdır. Bu sayıyı temel matrisin parametre sayısıyla karşılaştırmak bellek tasarrufunu ölçmenin basit bir yoludur; toplam bellekte aktivasyon ve optimizer ayrıca hesaba katılır.

Kaynak: [Hugging Face LoRA kavramları](https://huggingface.co/docs/peft/main/en/conceptual_guides/lora). Temel ağırlığın dondurulması, iki güncelleme matrisi ve alfa/rank ölçeği için açıklama sağlar; bu ders PEFT paketini çalıştırmaz.
:::

::: tahmin LoRA farkını tahmin et
Üç çıktı satırını yaz:

```python
A = [[1, 0], [0, 1]]
B = [[2, 0], [0, 2]]
print([[2, 0], [0, 2]])
print([[3, 1], [1, 3]])
print(2 * (4 + 8))
```

???

```cikti
[[2, 0], [0, 2]]
[[3, 1], [1, 3]]
24
```

İlk satır birim A ile ölçekli B çarpımını, ikinci satır birim temel ağırlığa eklenen farkı, üçüncü satır rank-2 adaptör parametre sayısını gösterir.
:::

::: gorev 1 · İki matrislik LoRA farkını hesapla
`lora_fark(a, b, olcek)` işlevini yaz. a ve b iki satır iki sütunluk, bool olmayan sayı listeleridir. Ölçek bool olmayan, `0 < olcek <= 4` koşulundaki sayıdır. Geçersiz veride `ValueError` yükselt.

`olcek * (b @ a)` matrisini hesapla. Çıktı iki çarpı iki listedir ve her değer altı ondalığa yuvarlanır. Girdileri değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-10")
```

```starter
from ai_temel_veri import json_yukle
def lora_fark(a,b,olcek):
    # KUSURLU BAŞLANGIÇ KODU: B@A yerine A@B hesaplar.
    return [[round(olcek*sum(a[i][k]*b[k][j] for k in range(2)),6) for j in range(2)] for i in range(2)]

v=json_yukle("veri/lora.json")
print("Sentetik A/B/ölçek:",v["a"],v["b"],v["olcek"])
print("Güncelleme:",lora_fark(v["a"],v["b"],v["olcek"]))
```

```test
A = [[1, 2], [3, 4]]
B = [[0, 1], [1, 0]]
def sozlesme(fn):
    try:
        import copy
        a=([[1,2],[3,4]],[[0,1],[1,0]],0.5);once=copy.deepcopy(a);fn(*a)
        if a!=once: return False
        if fn(A, B, 1) != [[3.0, 4.0], [1.0, 2.0]] or fn([[1, 0], [0, 1]], [[2, 0], [0, 2]], 0.5) != [[1.0, 0.0], [0.0, 1.0]]:
            return False
        if fn(A, B, 4) != [[12.0, 16.0], [4.0, 8.0]] or fn(A, B, 1 / 3) != [[1.0, 1.333333], [0.333333, 0.666667]]:
            return False
        for args in [(None, B, 1), ([(1, 0), [0, 1]], B, 1), ([[1, 0]], B, 1), ([[1], [0, 1]], B, 1), ([[1, True], [0, 1]], B, 1), ([[1, "0"], [0, 1]], B, 1), ([[float('nan'), 0], [0, 1]], B, 1), (A, [[float('inf'), 0], [0, 1]], 1), (A, None, 1), (A, B, 0), (A, B, 4.1), (A, B, True), (A, B, "1"), (A, B, float("nan"))]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
eq(lora_fark([[1, 2], [1, -2]], [[1, -1], [0, 0]], 0.5),
   [[0.0, 2.0], [0.0, 0.0]], "İşaretli terimler bazı hücrelerde birbirini götürür")
eq(lora_fark([[0.0000004, 0], [0.0000004, 0]], [[1, 1], [0, 0]], 1),
   [[0.000001, 0.0], [0.0, 0.0]], "İki katkı toplanmadan önce yuvarlanmaz")
ok(sozlesme(lora_fark), "B@A sırası, ölçek ve matris şeması korunmalı")
def m_a(a, b, o):
    return lora_fark(list(reversed(a)), b, o)
def m_b(a, b, o):
    return lora_fark(a, list(reversed(b)), o)
def m_olcek(a, b, o):
    return lora_fark(a, b, o * 2)
for ad, mutant in [("A matrisini bozan", m_a), ("B matrisini bozan", m_b), ("ölçeği bozan", m_olcek)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle
import math
def lora_fark(a, b, olcek):
    def matris(m):
        return isinstance(m, list) and len(m) == 2 and all(isinstance(s, list) and len(s) == 2 and all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in s) for s in m)
    if not matris(a) or not matris(b):
        raise ValueError("matris geçersiz")
    if not isinstance(olcek, (int, float)) or isinstance(olcek, bool) or not 0 < olcek <= 4:
        raise ValueError("ölçek geçersiz")
    return [[round(olcek * sum(b[i][k] * a[k][j] for k in range(2)), 6) for j in range(2)] for i in range(2)]

v=json_yukle("veri/lora.json")
print("Sentetik A/B/ölçek:",v["a"],v["b"],v["olcek"])
print("Güncelleme:",lora_fark(v["a"],v["b"],v["olcek"]))
```

```hint
Çıktının `i,j` hücresinde B'nin i. satırıyla A'nın j. sütununu çarpıp topla.
```
:::

::: gorev 2 · LoRA farkını temel ağırlığa ekle
`agirlik_birlestir(temel, fark)` işlevini yaz. İki girdi de iki çarpı iki sayı matrisidir; bool ve diğer geçersiz verilerde `ValueError` yükselt.

Karşılıklı hücreleri toplayarak yeni matris döndür ve değerleri altı ondalığa yuvarla. Özellikle temel matrisi yerinde değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-10")
```

```starter
from ai_temel_veri import json_yukle
def agirlik_birlestir(temel,fark):
    # KUSURLU BAŞLANGIÇ KODU: temel ağırlığı yerinde değiştirir.
    for i,satir in enumerate(temel):
        for j,x in enumerate(satir): temel[i][j]=round(x+fark[i][j],6)
    return temel

v=json_yukle("veri/lora.json")
print("Sentetik temel ve fark:",v["temel"],v["fark"])
print("Birleşik:",agirlik_birlestir(v["temel"],v["fark"]))
print("Çağrı sonrası temel:",v["temel"])
```

```test
import copy
W = [[1, 0], [0, 1]]
D = [[0.5, 1], [-1, 2]]
def sozlesme(fn):
    try:
        import copy
        a=([[1,0],[0,1]],[[0.5,1],[-1,2]]);once=copy.deepcopy(a);fn(*a)
        if a!=once: return False
        once = copy.deepcopy(W)
        if fn(W, D) != [[1.5, 1.0], [-1.0, 3.0]] or W != once:
            return False
        if fn([[0, 0], [0, 0]], D) != [[0.5, 1.0], [-1.0, 2.0]] or fn(W, [[0, 0], [0, 0]]) != [[1.0, 0.0], [0.0, 1.0]] or fn(W, [[1 / 3, 0], [0, 0]]) != [[1.333333, 0.0], [0.0, 1.0]]:
            return False
        for args in [(None, D), ([(1, 0), [0, 1]], D), ([[1, 0]], D), ([[1], [0, 1]], D), ([[1, True], [0, 1]], D), ([[1, "0"], [0, 1]], D), ([[float('nan'), 0], [0, 1]], D), (W, [[float('inf'), 0], [0, 1]]), (W, None), (W, [[0, 0], [0]])]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(agirlik_birlestir), "hücre toplamı ve temel ağırlık kopyası korunmalı")
def m_temel(w, d):
    return agirlik_birlestir(list(reversed(w)), d)
def m_fark(w, d):
    return agirlik_birlestir(w, list(reversed(d)))
def m_boyut(w, d):
    return agirlik_birlestir(w + [[0, 0]], d + [[0, 0]])
for ad, mutant in [("temeli bozan", m_temel), ("farkı bozan", m_fark), ("boyutu bozan", m_boyut)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle
import math
def agirlik_birlestir(temel, fark):
    def matris(m):
        return isinstance(m, list) and len(m) == 2 and all(isinstance(s, list) and len(s) == 2 and all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in s) for s in m)
    if not matris(temel) or not matris(fark):
        raise ValueError("matris geçersiz")
    return [[round(temel[i][j] + fark[i][j], 6) for j in range(2)] for i in range(2)]

v=json_yukle("veri/lora.json")
print("Sentetik temel ve fark:",v["temel"],v["fark"])
print("Birleşik:",agirlik_birlestir(v["temel"],v["fark"]))
print("Çağrı sonrası temel:",v["temel"])
```

```hint
İki iç liste üretiminde aynı `i,j` konumundaki değerleri topla; yeni satırlar oluştur.
```
:::

::: gorev 3 · Adaptör parametre maliyetini hesapla
`lora_maliyet(girdi, cikti, rank)` işlevini yaz. Girdi ve çıktı bool olmayan 2, 4 veya 8 tamsayısıdır. Rank bool olmayan 1–4 tamsayısıdır. Geçersiz veride `ValueError` yükselt.

Temel parametre sayısı `girdi*cikti`, eğitilen LoRA parametre sayısı `rank*(girdi+cikti)` olsun. `{"temel":T,"egitilen":E,"oran":R}` döndür; oran eğitilen/temel değeridir.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-10")
```

```starter
from ai_temel_veri import json_yukle
def lora_maliyet(girdi,cikti,rank):
    # KUSURLU BAŞLANGIÇ KODU: iki adaptör yerine yalnız giriş tarafını sayar.
    temel=girdi*cikti;egitilen=rank*girdi
    return {"temel":temel,"egitilen":egitilen,"oran":egitilen/temel}

v=json_yukle("veri/lora.json")
print("Sentetik boyut/rank vakaları:",v["maliyet_vakalari"])
for a in v["maliyet_vakalari"]: print(a,lora_maliyet(**a))
```

```test
def sozlesme(fn):
    try:
        if fn(4, 8, 2) != {"temel": 32, "egitilen": 24, "oran": 0.75} or fn(2, 2, 1) != {"temel": 4, "egitilen": 4, "oran": 1.0}:
            return False
        if fn(8, 8, 4) != {"temel": 64, "egitilen": 64, "oran": 1.0} or fn(8, 2, 3) != {"temel": 16, "egitilen": 30, "oran": 1.875}:
            return False
        for args in [(3, 4, 1), (4.0, 4, 1), (True, 4, 1), (4, 3, 1), (4, 4.0, 1), (4, True, 1), (4, 8, 0), (4, 8, 5), (4, 8, True), (4, 8, 1.0)]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(lora_maliyet), "LoRA parametre sayısı, oran ve boyutlar korunmalı")
def m_girdi(g, c, r):
    return lora_maliyet(g * 2, c, r)
def m_cikti(g, c, r):
    return lora_maliyet(g, c * 2, r)
def m_rank(g, c, r):
    return lora_maliyet(g, c, 1)
for ad, mutant in [("girdiyi bozan", m_girdi), ("çıktıyı bozan", m_cikti), ("rankı bozan", m_rank)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle
def lora_maliyet(girdi, cikti, rank):
    if any(not isinstance(x, int) or isinstance(x, bool) or x not in (2, 4, 8) for x in (girdi, cikti)):
        raise ValueError("boyut geçersiz")
    if not isinstance(rank, int) or isinstance(rank, bool) or not 1 <= rank <= 4:
        raise ValueError("rank geçersiz")
    temel = girdi * cikti
    egitilen = rank * (girdi + cikti)
    return {"temel": temel, "egitilen": egitilen, "oran": egitilen / temel}

v=json_yukle("veri/lora.json")
print("Sentetik boyut/rank vakaları:",v["maliyet_vakalari"])
for a in v["maliyet_vakalari"]: print(a,lora_maliyet(**a))
```

```hint
Temel sayıyı çarpım, eğitilen sayıyı rank ile boyut toplamının çarpımı olarak ayrı hesapla.
```
:::

::: anlat Gerçek modelde LoRA: 134 milyonun binde üçü
Yukarıdaki görevler 2×2 matrislerle LoRA'nın matematiğini gösterdi. Gerçek bir modelde LoRA, dondurulmuş bir `nn.Linear` katmanını sarar: çıktı `temel(x) + ölçek · x Aᵀ Bᵀ` olur. `A` küçük rastgele değerlerle, `B` sıfırla başlar; böylece adaptör takıldığı anda modelin davranışı değişmez ve eğitim yalnız `A` ile `B`'yi günceller. Ölçek çoğunlukla `alfa / rank`'tir.

Bu deneyde senin LoRA sınıfın SmolLM2-135M'nin 30 katmanındaki `q_proj` ve `v_proj` katmanlarına takılır ve modele CPU'da tek bir cümle öğretilir. Ölçülenler: kaç parametre eğitildi, hedef cümlenin kaybı ne kadar düştü, ilgisiz bir metnin kaybı ne kadar değişti ve birleştirilmiş ağırlığın adaptörlü modelle aynı çıktıyı verip vermediği.
:::

::: gorev Gerçek deney · Elle LoRA ile gerçek modelde ince ayar
`LoraDogrusal(torch.nn.Module)` sınıfını yaz: `LoraDogrusal(temel, rank, alfa)`.

- Doğrulama, aksi hâlde `ValueError`: `temel` bir `torch.nn.Linear`; `rank` bool olmayan int, 1 ile `min(giriş, çıkış)` arası; `alfa` bool olmayan, sonlu pozitif int/float.
- `temel`'i `self.temel` olarak sakla ve bütün parametrelerini dondur (`requires_grad=False`).
- `self.A = nn.Parameter(...)` biçimi `[rank, giriş]`, küçük rastgele değerler (ör. `randn * 0.01`); `self.B = nn.Parameter(...)` biçimi `[çıkış, rank]`, **sıfır**. Eğitilen parametreler yalnız bu ikisi olmalı.
- `self.olcek = alfa / rank`.
- `forward(x)`: `self.temel(x) + (x @ A.T @ B.T) * self.olcek`.
- `birlestir()`: `temel.weight + olcek · (B @ A)` tensörünü **yeni** tensör olarak döndür; temel ağırlığı değiştirme.

Test sınıfını gerçek `q_proj` (576→576) ve `v_proj` (576→192) katmanlarının kopyalarında sınar, sonra modelin bir kopyasında 40 adım gerçek eğitim yapar. Çalıştır düğmesi aynı deneyin ölçümlerini gösterir. Laboratuvardaki `referans_sinifi`/`lora_tak` işlevlerini ve PEFT'i kullanma.

```meta
motor: ai-gercek
gereksinim: torch
timeout: 300
```

```starter
import torch
import ai_lab
import math

class LoraDogrusal(torch.nn.Module):
    def __init__(self, temel, rank, alfa):
        super().__init__()
        self.temel = temel

    def forward(self, x):
        return self.temel(x)

    def birlestir(self):
        return self.temel.weight

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_10 as deney
    deney.goster(LoraDogrusal)
```

```test
import copy
import random
import ai_lab
sonuclar = []
def kontrol(kosul, mesaj):
    sonuclar.append(bool(kosul))
    return ok(kosul, mesaj)
import ast
yasak=("referans_sinifi","lora_tak","getattr","peft","LoraConfig","kanit_yaz")
sorun=ai_lab.kod_denetimi(src,yasak=yasak)
for n in ast.walk(ast.parse(src)):
    if isinstance(n,ast.ImportFrom) and any(a.name in yasak or a.name=="*" for a in n.names): sorun.append("referans importu yasak")
if not kontrol(not sorun,"Kendi LoRA sınıfını yaz: "+"; ".join(sorun)): stop()
Sinif = need("LoraDogrusal")
try:
    from sandbox import ai_gercek_ai_temel_10 as D
    tok, model, bilgi = ai_lab.dil_modeli()
    import torch
except ai_lab.GercekLabYok as e:
    kontrol(False, f"GERÇEK MODEL YOK, deney yapılmadı: {e}")
    stop()
rnd = random.Random()
katman = rnd.randrange(model.config.num_hidden_layers)
gercek_katmanlar = [model.model.layers[katman].self_attn.q_proj, model.model.layers[katman].self_attn.v_proj]
ayarlar = [(rnd.choice([2, 4, 8]), rnd.choice([8, 16, 32])) for _ in gercek_katmanlar]
def sozlesme(S):
    try:
        for orijinal, (r, alfa) in zip(gercek_katmanlar, ayarlar):
            lin = copy.deepcopy(orijinal)
            W0 = lin.weight.detach().clone()
            m = S(lin, r, alfa)
            if any(p.requires_grad for p in lin.parameters()):
                return False
            egitilen = [p for p in m.parameters() if p.requires_grad]
            if sum(p.numel() for p in egitilen) != r * (lin.in_features + lin.out_features):
                return False
            if tuple(m.A.shape) != (r, lin.in_features) or tuple(m.B.shape) != (lin.out_features, r):
                return False
            if m.B.abs().max().item() != 0 or m.A.abs().max().item() == 0 or m.A.abs().max().item() > 0.5 or abs(m.olcek - alfa / r) > 1e-12:
                return False
            if torch.unique(m.A.detach()).numel()<2: return False
            x = torch.randn(3, 5, lin.in_features)
            with torch.no_grad():
                if (m(x) - lin(x)).abs().max().item() > 1e-6:
                    return False
                m.A.copy_(torch.randn_like(m.A) * 0.05)
                m.B.copy_(torch.randn_like(m.B) * 0.05)
                beklenen = lin(x) + (x @ m.A.T @ m.B.T) * (alfa / r)
                if (m(x) - beklenen).abs().max().item() > 1e-4:
                    return False
                W = m.birlestir()
                if not isinstance(W, torch.Tensor) or tuple(W.shape) != tuple(W0.shape):
                    return False
                if (W - (W0 + (alfa / r) * (m.B @ m.A))).abs().max().item() > 1e-5:
                    return False
                if not torch.equal(lin.weight, W0):
                    return False
                if (torch.nn.functional.linear(x, W) - m(x)).abs().max().item() > 1e-3:
                    return False
            m(x).sum().backward()
            if lin.weight.grad is not None or m.A.grad is None or m.B.grad is None:
                return False
        for boyut in (1,2):
            lin=torch.nn.Linear(boyut,boyut,bias=True);once={a:b.detach().clone() for a,b in lin.named_parameters()}
            m=S(lin,boyut,0.5);x=torch.randn(2,boyut);x0=x.clone()
            if not torch.allclose(m(x),lin(x),atol=1e-6) or not torch.equal(x,x0): return False
            W=m.birlestir()
            if W.data_ptr()==lin.weight.data_ptr() or any(not torch.equal(v,dict(lin.named_parameters())[a]) for a,v in once.items()): return False
        lin = copy.deepcopy(gercek_katmanlar[1])
        for arg in [(torch.nn.Conv1d(2, 2, 1), 2, 8), (None, 2, 8), (lin, 0, 8), (lin, 193, 8), (lin, True, 8), (lin, 2.0, 8),
                    (lin, 2, 0), (lin, 2, -1.0), (lin, 2, True), (lin, 2, "8"), (lin,2,float("inf")),(lin,2,float("nan"))]:
            try:
                S(*arg)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
kontrol(sozlesme(Sinif), "gerçek q_proj/v_proj: dondurulmuş temel, A/B biçimleri, B=0 başlangıç, alfa/rank ölçeği, ileri hesap ve birleştirme doğru")
for ad, kw in [("ölçek alfa (rank'a bölünmüyor)", {"olcek_tur": "alfa"}), ("B rastgele başlıyor", {"b_sifir": False}),
               ("temel dondurulmuyor", {"dondur": False}), ("birleştirme temel ağırlığı yerinde değiştiriyor", {"yerinde": True}),
               ("ileri hesapta ölçek unutulmuş", {"ileri_olcek": False})]:
    kontrol(not sozlesme(D.referans_sinifi(**kw)), "hatalı çözüm reddedilmeli: " + ad)
class Adaptorsuz(torch.nn.Module):
    def __init__(self, temel, rank, alfa):
        super().__init__()
        ok_ = isinstance(temel, torch.nn.Linear) and not isinstance(rank, bool) and isinstance(rank, int) \
            and 1 <= rank <= min(temel.in_features, temel.out_features) and not isinstance(alfa, bool) and alfa > 0
        if not ok_:
            raise ValueError("geçersiz")
        self.temel, self.olcek = temel, alfa / rank
        self.A = torch.nn.Parameter(torch.randn(rank, temel.in_features) * 0.01)
        self.B = torch.nn.Parameter(torch.zeros(temel.out_features, rank))
        for p in temel.parameters():
            p.requires_grad_(False)
    def forward(self, x):
        return self.temel(x)
    def birlestir(self):
        return self.temel.weight.detach().clone()
kontrol(not sozlesme(Adaptorsuz), "hatalı çözüm reddedilmeli: adaptör hesaba katılmıyor")
r = {}
if all(sonuclar):
    r = D.deney(Sinif)
    kontrol(r["egitilen_parametre"] == r["beklenen_egitilen"], f"gerçek model: yalnız LoRA parametreleri eğitiliyor ({r['egitilen_parametre']:,})")
    kontrol(abs(r["takinca_hedef_kayip"] - r["once"]["hedef"]) < 1e-4, "adaptör takılınca model davranışı değişmiyor (B=0)")
    kontrol(r["sonra"]["hedef"] < 0.5 * r["once"]["hedef"], f"gerçek eğitim hedef kaybını düşürdü ({r['once']['hedef']:.3f} → {r['sonra']['hedef']:.3f})")
    kontrol(r["temel_agirlik_degismedi"] and r["ortak_model_degismedi"], "temel ağırlıklar eğitim boyunca değişmedi")
    kontrol(r["birlesme_farki"] < 5e-3, f"birleşik ağırlıklı model adaptörlü modelle aynı çıktıyı veriyor (fark {r['birlesme_farki']:.1e})")
yol = ai_lab.kanit_yaz("temel-lora", {
    "kaynak": "gercek", "kabul": all(sonuclar), "ders": "ai-temel-10", "model_bilgisi": bilgi,
    "ayarlar": {"sinanan_katman": katman, "rank_alfa": ayarlar, "tolerans": {"birlesme": 5e-3}}, "deney": r})
if r:
    ok(True, f"GERÇEK ÇIKTI ({bilgi['model']}@{bilgi['revizyon'][:8]}): {r['egitilen_parametre']:,}/{r['toplam_parametre']:,} parametre "
             f"(%{100 * r['oran']:.2f}) eğitildi; hedef kayıp {r['once']['hedef']:.2f} → {r['sonra']['hedef']:.4f}, "
             f"ilgisiz metin kaybı {r['once']['kontrol']:.2f} → {r['sonra']['kontrol']:.2f}; "
             f"devam: {r['once']['uretim']!r} → {r['sonra']['uretim']!r}")
```

```solution
import torch
import ai_lab
import math

class LoraDogrusal(torch.nn.Module):
    def __init__(self, temel, rank, alfa):
        super().__init__()
        if not isinstance(temel, torch.nn.Linear):
            raise ValueError("temel bir nn.Linear olmalı")
        if isinstance(rank, bool) or not isinstance(rank, int) or not 1 <= rank <= min(temel.in_features, temel.out_features):
            raise ValueError("rank geçersiz")
        if isinstance(alfa, bool) or not isinstance(alfa, (int, float)) or not alfa > 0 or not math.isfinite(alfa):
            raise ValueError("alfa pozitif olmalı")
        self.temel = temel
        for p in temel.parameters():
            p.requires_grad_(False)
        self.A = torch.nn.Parameter(torch.randn(rank, temel.in_features) * 0.01)
        self.B = torch.nn.Parameter(torch.zeros(temel.out_features, rank))
        self.olcek = alfa / rank

    def forward(self, x):
        return self.temel(x) + (x @ self.A.T @ self.B.T) * self.olcek

    def birlestir(self):
        return self.temel.weight.detach() + self.olcek * (self.B @ self.A).detach()

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_10 as deney
    deney.goster(LoraDogrusal)
```

```hint
`B` sıfırla başladığı için `x @ A.T @ B.T` başlangıçta sıfırdır. Birleştirmede `B @ A` biçimi `[çıkış, giriş]` olur, yani `temel.weight` ile aynıdır; toplamı yeni bir tensör olarak döndür (`+=` kullanma).
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Düşük ranklı güncelleme (`LoRA`) (30 sn).** "Dev $W_0 \in \mathbb{R}^{d_{\text{out}} \times d_{\text{in}}}$ matrisinin tamamını güncellemek yerine onu dondurup $\Delta W = \frac{\alpha}{r} B A$ ($r \ll d$) düşük ranklı adaptörü eğitiriz; SmolLM2'de parametrelerin yalnızca binde üçü eğitilir."
2. **Sıfır başlangıç ve çıkarım birleştirmesi (35 sn).** "$B = 0$ başlatıldığı için ilk adımda model taban modelle birebir aynı çıktıyı verir; eğitim bitince $W_0 + \Delta W$ tek matriste birleştirilerek ek çıkarım gecikmesi sıfırlanır."
3. **Güvenlik yüzeyi (30 sn).** "Küçük bir LoRA adaptörü birkaç düzine adımla hedef davranışı değiştirebildiği gibi taban modelin güvenlik hizalamasını da aşındırabilir; bu yüzden adaptör paketleri kod imzası ve güvenlik kapısıyla denetlenir."
4. **Soru (25 sn).** "Çok kiracılı bir sunucuda adaptörleri $W_0$'a kalıcı birleştirmek (`merge`) yerine neden istek anında ayrı tutmak tercih edilir?"
:::
