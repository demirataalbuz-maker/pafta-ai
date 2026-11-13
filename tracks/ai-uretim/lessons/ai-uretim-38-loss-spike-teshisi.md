---
id: ai-uretim-38
title: "Loss Spike Teşhisi · Öğrenme Oranı mı, Veri mi, Sayılar mı?"
summary: "Kayıp eğrisindeki ani sıçramaları gürültüden ayır, gradient normunu kırp ve eğitim günlüğündeki ipuçlarından sıçramanın öğrenme oranından mı, belirli bir batch'ten mi, yoksa sayısal taşmadan mı geldiğini çıkar."
track: ai-uretim
order: 38
---

::: anlat 1. Kayıp birden fırladı
Eğitim saatlerdir düzgün ilerliyor; kayıp yavaş yavaş düşüyor. Sonra bir adımda üç katına çıkıyor. Bazen birkaç yüz adımda geri iner, bazen `NaN` olur ve eğitim biter. Buna `loss spike` denir ve üç olağan şüphelisi vardır:

| Şüpheli | Belirtisi | Çare |
|---|---|---|
| Öğrenme oranı | Sıçrama, `lr`'nin yükseldiği ya da en yüksek olduğu dönemde gelir; gradient normu sıçramadan **önce** büyümeye başlar | `lr`'yi düşür, `warmup`'ı uzat, gradient kırp |
| Veri | Sıçrama hep **aynı batch'te** tekrarlar; `lr` ve gradient normu öncesinde olağandır | Örnekleri incele: bozuk kayıt, aşırı uzun dizi, yanlış etiket |
| Sayısal | Gradient normu `inf` ya da `nan`; kayıp sonlu bir sayıdan doğrudan `nan`'e geçer | Taşan işlemi bul (bkz. `ai-uretim-39`); hassasiyeti ya da `eps`'i düzelt |

Teşhis üç adımdır ve bu dersin görevleri bunlardır:

| Soru | Araç | Görev |
|---|---|---|
| Bu bir sıçrama mı, yoksa olağan gürültü mü? | Hareketli medyana göre sapma | 1 |
| Tek bir kötü adım ağırlıkları bozmasın diye ne yapılır? | `Gradient clipping` | 2 |
| Günlükteki ipuçları hangi şüpheliyi gösteriyor? | Kural tabanlı teşhis | 3 |

> [!NOT]
> Görevlerdeki eğitim günlükleri sentetiktir; gerçek bir eğitimden alınmamıştır. Üçüncü görevdeki kurallar bir **ilk ayırım** içindir; kesin teşhis her zaman şüpheli adımı yeniden koşup incelemekle konur.
>
> Görev 1 ve 3'te örnek günlük çalışma klasörüne `veri/egitim_gunlugu.json` olarak kopyalanır: 16 adım, dört sıçrama (aynı batch'te iki kez, `lr` tepesinde bir kez, `NaN` ile bir kez). Başlangıç kodu dosyayı `json.load` ile okur ve işlevini onun üstünde çalıştırıp sonucu yazdırır. Denemek için yüklediğin listeyi kodda değiştir ve yeniden çalıştır; dosya her çalıştırmada kaynaktan yeniden kopyalanır, değişiklik kalıcı değildir. Kontrol bu dosyayı değil, görmediğin ayrı günlükleri kullanır. Dosyadaki `NaN` ve `Infinity` standart JSON değildir; Python'un `json` modülü okur, başka ayrıştırıcılar reddedebilir.
:::

::: anlat 2. Sıçramayı ölçmek, kırpmak ve teşhis etmek
**Sıçrama mı, gürültü mü?** `Mini-batch` kaybı doğası gereği oynar. Bir adımı "sıçrama" saymak için onu yakın geçmişle karşılaştırırsın. Ortalama yerine **medyan** kullanılır: tek bir büyük değer ortalamayı yukarı çeker ve bir sonraki sıçramayı gizler; medyan etkilenmez. Kural: bir adımın kaybı, önceki `pencere` adımın medyanının `esik` katından büyükse sıçramadır.

**Gradient clipping.** Ağırlık güncellemesi `lr × gradient`'tir. Gradient bir adımda yüz kat büyürse güncelleme de yüz kat büyür ve ağırlıkları öğrenilen bölgeden dışarı fırlatır. Kırpma, gradient'in **yönünü koruyup boyunu sınırlar**: bütün gradient'lerin birleşik `L2` normu `max_norm`'u aşıyorsa hepsi aynı oranda küçültülür.

$$g \leftarrow g \cdot \min\!\left(1,\; \frac{\text{max\_norm}}{\lVert g \rVert_2}\right)$$

İki yaygın hata vardır. Birincisi her bileşeni ayrı ayrı kırpmak (`clip by value`): yön değişir. İkincisi her katmanı kendi normuna göre kırpmak: katmanlar arası oran bozulur. PyTorch'taki `clip_grad_norm_` birleşik normu kullanır ve kırpmadan **önceki** normu döndürür; o sayıyı günlüğe yazmak en ucuz erken uyarı sistemidir.

Kırpma bir emniyet kemeridir, tedavi değil: adımların büyük kısmı kırpılıyorsa öğrenme oranı fazla yüksektir ya da bir şey bozuktur.

**Teşhis.** Her adım için dört sayı yeter: kayıp, öğrenme oranı, kırpma öncesi gradient normu ve batch kimliği. Görev 3 şu sırayla karar verir:

1. Sıçrama adımında gradient normu ya da kayıp sonlu değilse: **sayısal**.
2. Aynı batch kimliği birden çok sıçramada geçiyorsa: **veri**.
3. Sıçramadan hemen önceki adımlarda gradient normu belirgin büyüdüyse ya da öğrenme oranı en yüksek değerine yakınsa: **öğrenme oranı**.
4. Hiçbiri değilse: **belirsiz** (tek seferlik kötü bir batch ya da gürültü olabilir).

Sıra önemlidir: sayısal taşma diğer iki belirtiyi de taklit edebilir, bu yüzden önce ona bakılır.
:::

::: tahmin Ortalama mı, medyan mı?
Son beş adımın kaybı içinde tek bir sıçrama var. Yeni gelen 2,6'lık kayıp, ortalamanın ve medyanın iki katını aşıyor mu?

```python
gecmis = [1.0, 1.1, 0.9, 9.0, 1.0]
yeni = 2.6

ortalama = sum(gecmis) / len(gecmis)
medyan = sorted(gecmis)[len(gecmis) // 2]
print(round(ortalama, 2), yeni > 2 * ortalama)
print(medyan, yeni > 2 * medyan)
```

???

```cikti
2.6 False
1.0 True
```
Tek bir 9,0 değeri ortalamayı 1,0'dan 2,6'ya çekiyor; eşik 5,2 oluyor ve 2,6'lık yeni kayıp "olağan" görünüyor. Medyan 1,0'da kalıyor; eşik 2,0 ve yeni kayıp bir sıçrama olarak yakalanıyor. Bir sıçrama, ortalamaya dayalı dedektörü kendisinden sonraki sıçramalara karşı kör eder. Medyan bu yüzden tercih edilir.
:::

::: gorev 1 · Sıçramaları bul
`sicramalari_bul(kayiplar, pencere, esik)` işlevini yaz.

- `kayiplar`: boş olmayan sayı listesi (adım 0, 1, 2, ...). Değerler `nan` ya da `inf` olabilir.
- `pencere`: pozitif `int`. `esik`: 1'den büyük sayı.
- `t` adımı için geçmiş, ondan önceki en çok `pencere` adımın **sonlu** kayıplarıdır. Geçmişte en az bir sonlu değer yoksa o adım değerlendirilmez.
- Medyan: sıralı geçmişin ortadaki öğesi; çift sayıda öğe varsa ortadaki ikisinin ortalaması.
- `t` adımı sıçramadır, eğer kaybı sonlu değilse **ya da** `kayip > esik · medyan` ise.
- Dönüş: sıçrama adımlarının indeks listesi (artan sırada).
- Bozuk girdi `ValueError`.

KUSURLU başlangıç geçmişin ortalamasını kullanıyor ve sonlu olmayan değerleri eliyor: bir sıçrama sonrakini gizliyor, `nan` olan adım ise hiç raporlanmıyor.

```starter
def sicramalari_bul(kayiplar, pencere, esik):
    import math
    out = []
    for t in range(1, len(kayiplar)):
        g = [x for x in kayiplar[max(0, t - pencere):t] if math.isfinite(x)]
        if g and math.isfinite(kayiplar[t]) and kayiplar[t] > esik * sum(g) / len(g):
            out.append(t)
    return out


import json
with open("veri/egitim_gunlugu.json", encoding="utf-8") as f:
    gunluk = json.load(f)
print(sicramalari_bul([g["kayip"] for g in gunluk], 4, 2.0))
```
```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_uretim_veri import hazirla
hazirla("ai-uretim-38")
```

```solution
def sicramalari_bul(kayiplar, pencere, esik):
    import math
    if not isinstance(kayiplar, list) or not kayiplar or any(isinstance(x, bool) or not isinstance(x, (int, float)) for x in kayiplar):
        raise ValueError('kayiplar boş olmayan sayı listesi olmalı')
    if isinstance(pencere, bool) or not isinstance(pencere, int) or pencere < 1:
        raise ValueError('pencere pozitif int olmalı')
    if isinstance(esik, bool) or not isinstance(esik, (int, float)) or not esik > 1:
        raise ValueError('esik 1 den büyük olmalı')
    out = []
    for t in range(len(kayiplar)):
        gecmis = sorted(x for x in kayiplar[max(0, t - pencere):t] if math.isfinite(x))
        if not gecmis:
            continue
        n = len(gecmis)
        medyan = gecmis[n // 2] if n % 2 else (gecmis[n // 2 - 1] + gecmis[n // 2]) / 2
        if not math.isfinite(kayiplar[t]) or kayiplar[t] > esik * medyan:
            out.append(t)
    return out
```

```test
need('sicramalari_bul')
import math, random, statistics

eq(sicramalari_bul([1.0, 1.1, 0.9, 9.0, 1.0, 2.6], 5, 2), [3, 5], 'ilk sıçrama ikincisini gizlemez (medyan)')
eq(sicramalari_bul([1.0, 1.0, 1.0, 1.9, 1.0], 3, 2), [], 'eşiğin altındaki oynama sıçrama değildir')
eq(sicramalari_bul([1.0, 1.0, float('nan'), 1.0], 3, 2), [2], 'nan olan adım sıçramadır')
eq(sicramalari_bul([1.0, float('inf')], 3, 2), [1], 'inf olan adım sıçramadır')
eq(sicramalari_bul([5.0, 1.0, 1.0], 3, 2), [], 'ilk adımın geçmişi yok: değerlendirilmez')
eq(sicramalari_bul([float('nan'), 4.0, 4.0, 9.0], 3, 2), [3], 'geçmişteki nan medyana katılmaz')
eq(sicramalari_bul([1.0, 3.0, 1.0, 1.0, 1.0, 1.0, 3.0], 2, 2), [1, 6], 'pencere yalnız son iki adıma bakar')
eq(sicramalari_bul([2.0, 4.0, 7.0], 2, 2), [2], 'çift sayıda geçmiş: medyan iki ortancanın ortalaması (3), eşik 6')
eq(sicramalari_bul([3.0], 5, 2), [], 'tek adım')
rng = random.Random(3801)
for _ in range(25):
    k = [round(abs(rng.gauss(2, 0.5)) + (rng.random() < 0.1) * rng.uniform(5, 20), 3) for _ in range(rng.randint(1, 40))]
    for i in range(len(k)):
        if rng.random() < 0.03:
            k[i] = float('nan')
    p, e = rng.randint(1, 8), rng.choice([1.5, 2, 3])
    beklenen = []
    for t in range(len(k)):
        g = [x for x in k[max(0, t - p):t] if not math.isnan(x)]
        if g and (math.isnan(k[t]) or k[t] > e * statistics.median(g)):
            beklenen.append(t)
    eq(sicramalari_bul(k, p, e), beklenen, 'rastgele eğride bağımsız referansla aynı')
k = [1.0, 5.0]
sicramalari_bul(k, 2, 2)
eq(k, [1.0, 5.0], 'girdi değişmez')
for a in ([None, 3, 2], [[], 3, 2], [[1, "2"], 3, 2], [[True], 3, 2], [(1.0, 2.0), 3, 2], [[1.0], 0, 2], [[1.0], 2.0, 2], [[1.0], True, 2], [[1.0], 3, 1], [[1.0], 3, 0.5], [[1.0], 3, None], [[1.0], 3, False], [[1.0], 3, float('nan')]):
    raises(ValueError, sicramalari_bul, *a, msg='bozuk girdi reddedilir')
```

```hint
Her adım için önceki `pencere` adımı al, sonlu olmayanları ele, sırala ve medyanı bul. Adımın kendisi sonlu değilse doğrudan sıçramadır.
```
:::

::: gorev 2 · Birleşik norma göre gradient kırpma
`gradient_kirp(gradientler, max_norm)` işlevini yaz.

- `gradientler`: boş olmayan liste; her öğe bir parametre grubunun gradient'i, yani boş olmayan sayı listesi (gruplar farklı uzunlukta olabilir).
- `max_norm`: pozitif sayı.
- `norm`: **bütün** grupların bütün bileşenleri üzerinden `L2` normu (kırpmadan önce).
- Norm sonlu değilse (`nan` ya da `inf` içeriyorsa) `ValueError`: bozuk bir gradient kırpılarak kurtarılamaz.
- `norm > max_norm` ise bütün bileşenler `max_norm / norm` ile çarpılır; değilse aynen kalır.
- Dönüş: `{'gradientler': [...], 'norm': ..., 'kirpildi': bool}`; sayılar 9 basamağa yuvarlanır. Girdi değişmemelidir.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç her bileşeni ayrı ayrı `[-max_norm, max_norm]` aralığına kırpıyor: gradient'in yönü değişiyor ve birleşik norm yine sınırı aşabiliyor.

```starter
def gradient_kirp(gradientler, max_norm):
    norm = sum(x * x for g in gradientler for x in g) ** 0.5
    yeni = [[round(max(-max_norm, min(max_norm, x)), 9) for x in g] for g in gradientler]
    return {'gradientler': yeni, 'norm': round(norm, 9), 'kirpildi': yeni != gradientler}
```

```solution
def gradient_kirp(gradientler, max_norm):
    import math
    if not isinstance(gradientler, list) or not gradientler:
        raise ValueError('gradientler boş olmayan liste olmalı')
    for g in gradientler:
        if not isinstance(g, list) or not g or any(isinstance(x, bool) or not isinstance(x, (int, float)) for x in g):
            raise ValueError('her grup boş olmayan sayı listesi olmalı')
    if isinstance(max_norm, bool) or not isinstance(max_norm, (int, float)) or not max_norm > 0 or not math.isfinite(max_norm):
        raise ValueError('max_norm pozitif sonlu sayı olmalı')
    norm = math.sqrt(sum(x * x for g in gradientler for x in g))
    if not math.isfinite(norm):
        raise ValueError('gradient sonlu değil')
    kirp = norm > max_norm
    olcek = max_norm / norm if kirp else 1.0
    return {'gradientler': [[round(x * olcek, 9) for x in g] for g in gradientler], 'norm': round(norm, 9), 'kirpildi': kirp}
```

```test
need('gradient_kirp')
import math, random

r = gradient_kirp([[3.0], [4.0]], 1.0)
eq(r, {'gradientler': [[0.6], [0.8]], 'norm': 5.0, 'kirpildi': True}, 'birleşik norm 5: iki grup aynı oranda küçülür, yön korunur')
r = gradient_kirp([[3.0], [4.0]], 10.0)
eq(r, {'gradientler': [[3.0], [4.0]], 'norm': 5.0, 'kirpildi': False}, 'sınırın altında: dokunulmaz')
eq(gradient_kirp([[3.0, 4.0]], 5.0)['kirpildi'], False, 'tam sınırda kırpılmaz')
r = gradient_kirp([[100.0, 0.5]], 1.0)
ok(abs(r['gradientler'][0][1] - 0.005) < 1e-4, 'küçük bileşen de aynı oranda küçülür (bileşen bazlı kırpmada 0.5 kalırdı)', got=r)
eq(gradient_kirp([[0.0, 0.0]], 1.0), {'gradientler': [[0.0, 0.0]], 'norm': 0.0, 'kirpildi': False}, 'sıfır gradient')
raises(ValueError, gradient_kirp, [[1.0, float('nan')]], 1.0, msg='nan içeren gradient kırpılamaz')
raises(ValueError, gradient_kirp, [[float('inf')]], 1.0, msg='inf içeren gradient kırpılamaz')
rng = random.Random(3802)
for _ in range(25):
    g = [[round(rng.uniform(-5, 5), 3) for _ in range(rng.randint(1, 5))] for _ in range(rng.randint(1, 4))]
    m = rng.choice([0.5, 1.0, 5.0, 50.0])
    r = gradient_kirp(g, m)
    duz = [x for grup in g for x in grup]
    norm = math.sqrt(math.fsum(x * x for x in duz))
    yakin(r['norm'], norm, 'kırpma öncesi birleşik norm', tol=1e-7)
    yeni = [x for grup in r['gradientler'] for x in grup]
    yeni_norm = math.sqrt(math.fsum(x * x for x in yeni))
    ok(yeni_norm <= m + 1e-6, 'kırpmadan sonra birleşik norm sınırı aşmaz', got=(yeni_norm, m))
    eq(r['kirpildi'], norm > m, 'kırpıldı bayrağı')
    if norm > 0:
        for a, b in zip(duz, yeni):
            yakin(b, a * min(1.0, m / norm), 'her bileşen aynı ölçekle çarpılır', tol=1e-7)
    eq([len(x) for x in r['gradientler']], [len(x) for x in g], 'grup biçimi korunur')
g = [[3.0], [4.0]]
gradient_kirp(g, 1.0)
eq(g, [[3.0], [4.0]], 'girdi değişmez')
for a in ([None, 1.0], [([1.0],), 1.0], [[], 1.0], [[[]], 1.0], [[[1, "2"]], 1.0], [[[True]], 1.0], [[(1.0,)], 1.0], [[1.0, 2.0], 1.0], [[[1.0]], 0], [[[1.0]], -1], [[[1.0]], None], [[[1.0]], False], [[[1.0]], float('nan')], [[[1.0]], float('inf')]):
    raises(ValueError, gradient_kirp, *a, msg='bozuk girdi reddedilir')
```

```hint
Normu bütün grupların bütün bileşenleri üzerinden tek seferde hesapla. Tek bir ölçek (`max_norm / norm`) bul ve her bileşeni onunla çarp.
```
:::

::: gorev 3 · Sıçramanın nedenini ayır
`sicrama_teshisi(gunluk, sicrama_adimlari)` işlevini yaz.

- `gunluk`: boş olmayan liste; `gunluk[t]` şu sözlüktür: `{'kayip': sayı, 'lr': pozitif sayı, 'grad_norm': sayı, 'batch': str}` (tam bu dört anahtar). `kayip` ve `grad_norm` sonlu olmayabilir.
- `sicrama_adimlari`: `gunluk`'un geçerli indekslerinden oluşan, yinelenmeyen `int` listesi (boş olabilir).
- Her sıçrama adımı `t` için, şu sırayla ilk tutan kural geçerlidir:
  1. `gunluk[t]`'nin `kayip`'ı ya da `grad_norm`'u sonlu değilse → `'sayisal'`.
  2. `gunluk[t]['batch']`, `sicrama_adimlari` içindeki **başka** bir adımda da geçiyorsa → `'veri'`.
  3. `t >= 1` ve önceki adımın `grad_norm`'u sonlu ve pozitifse ve `gunluk[t]['grad_norm'] > 3 · gunluk[t-1]['grad_norm']` ise; **ya da** `gunluk[t]['lr']`, günlükteki en büyük `lr`'nin en az %90'ıysa → `'ogrenme_orani'`.
  4. Hiçbiri → `'belirsiz'`.
- Dönüş: `{adım: neden}` sözlüğü.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç her sıçramayı öğrenme oranına bağlıyor: en sık söylenen teşhis, ama tekrar eden bozuk bir batch'i ya da taşmayı asla bulamaz.

```starter
def sicrama_teshisi(gunluk, sicrama_adimlari):
    return {t: 'ogrenme_orani' for t in sicrama_adimlari}


import json
with open("veri/egitim_gunlugu.json", encoding="utf-8") as f:
    gunluk = json.load(f)
print(sicrama_teshisi(gunluk, [4, 7, 10, 13]))
```
```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_uretim_veri import hazirla
hazirla("ai-uretim-38")
```

```solution
def sicrama_teshisi(gunluk, sicrama_adimlari):
    import math
    def sayi(x):
        return not isinstance(x, bool) and isinstance(x, (int, float))
    if not isinstance(gunluk, list) or not gunluk:
        raise ValueError('gunluk boş olmayan liste olmalı')
    for g in gunluk:
        if not isinstance(g, dict) or set(g) != {'kayip', 'lr', 'grad_norm', 'batch'}:
            raise ValueError('günlük kaydı şeması')
        if not sayi(g['kayip']) or not sayi(g['grad_norm']) or not sayi(g['lr']) or not g['lr'] > 0 or not math.isfinite(g['lr']):
            raise ValueError('kayip ve grad_norm sayı, lr pozitif sonlu sayı olmalı')
        if not isinstance(g['batch'], str) or not g['batch']:
            raise ValueError('batch boş olmayan str olmalı')
    if not isinstance(sicrama_adimlari, list) or len(set(sicrama_adimlari)) != len(sicrama_adimlari):
        raise ValueError('sicrama_adimlari yinelenmeyen liste olmalı')
    for t in sicrama_adimlari:
        if isinstance(t, bool) or not isinstance(t, int) or not 0 <= t < len(gunluk):
            raise ValueError('sıçrama adımı geçerli bir indeks olmalı')
    en_lr = max(g['lr'] for g in gunluk)
    out = {}
    for t in sicrama_adimlari:
        g = gunluk[t]
        if not math.isfinite(g['kayip']) or not math.isfinite(g['grad_norm']):
            out[t] = 'sayisal'
        elif any(gunluk[u]['batch'] == g['batch'] for u in sicrama_adimlari if u != t):
            out[t] = 'veri'
        elif (t >= 1 and math.isfinite(gunluk[t - 1]['grad_norm']) and gunluk[t - 1]['grad_norm'] > 0 and g['grad_norm'] > 3 * gunluk[t - 1]['grad_norm']) or g['lr'] >= 0.9 * en_lr:
            out[t] = 'ogrenme_orani'
        else:
            out[t] = 'belirsiz'
    return out
```

```test
need('sicrama_teshisi')
import math, random

def K(kayip, lr, gn, batch):
    return {'kayip': kayip, 'lr': lr, 'grad_norm': gn, 'batch': batch}

g = [K(2.0, 1e-4, 1.0, 'b0'), K(2.0, 1e-4, 1.0, 'b1'), K(9.0, 1e-4, 1.1, 'b7'), K(2.0, 1e-4, 1.0, 'b2'), K(9.5, 1e-4, 1.0, 'b7'), K(2.0, 1e-3, 1.0, 'b3')]
eq(sicrama_teshisi(g, [2, 4]), {2: 'veri', 4: 'veri'}, 'aynı batch iki sıçramada: veri')
g = [K(2.0, 1e-4, 1.0, 'b0'), K(2.1, 5e-4, 1.2, 'b1'), K(8.0, 1e-3, 6.0, 'b2')]
eq(sicrama_teshisi(g, [2]), {2: 'ogrenme_orani'}, 'gradient normu üç kattan fazla büyümüş ve lr en yüksek değerinde')
g = [K(2.0, 1e-3, 1.0, 'b0'), K(2.0, 1e-4, 1.0, 'b1'), K(float('nan'), 1e-4, float('inf'), 'b2')]
eq(sicrama_teshisi(g, [2]), {2: 'sayisal'}, 'sonlu olmayan gradient: sayısal')
g = [K(2.0, 1e-3, 1.0, 'b0'), K(float('nan'), 1e-3, 50.0, 'b9'), K(float('nan'), 1e-3, 60.0, 'b9')]
eq(sicrama_teshisi(g, [1, 2]), {1: 'sayisal', 2: 'sayisal'}, 'sayısal kuralı önce gelir: aynı batch ve yüksek lr olsa bile')
g = [K(2.0, 1e-3, 1.0, 'b0'), K(2.0, 1e-4, 1.0, 'b1'), K(7.0, 1e-4, 1.5, 'b2')]
eq(sicrama_teshisi(g, [2]), {2: 'belirsiz'}, 'hiçbir ipucu yok: belirsiz')
g = [K(7.0, 1e-3, 1.0, 'b0'), K(2.0, 1e-4, 1.0, 'b1')]
eq(sicrama_teshisi(g, [0]), {0: 'ogrenme_orani'}, 'ilk adımın öncesi yok; lr en yüksek değerinde')
g = [K(2.0, 1e-3, 0.0, 'b0'), K(7.0, 1e-4, 5.0, 'b1')]
eq(sicrama_teshisi(g, [1]), {1: 'belirsiz'}, 'önceki gradient normu sıfırsa oran kuralı uygulanmaz')
g = [K(2.0, 1e-3, 0.5, 'b0'), K(8.0, 1e-4, 1.6, 'b1'), K(2.0, 1e-4, float('inf'), 'b2')]
eq(sicrama_teshisi(g, [1]), {1: 'ogrenme_orani'}, 'lr düşükken bile bir önceki adıma göre gradient normu üç kattan fazla büyürse öğrenme oranı')
g = [K(2.0, 1e-3, 0.5, 'b0'), K(8.0, 1e-4, 1.5, 'b1')]
eq(sicrama_teshisi(g, [1]), {1: 'belirsiz'}, 'gradient normu tam üç kat ise eşiği aşmaz')
g = [K(8.0, 1e-4, 5.0, 'b0'), K(2.0, 1e-3, 0.5, 'b1')]
eq(sicrama_teshisi(g, [0]), {0: 'belirsiz'}, 'ilk adımda önceki adım yoktur: son elemana bakılmaz')
eq(sicrama_teshisi([K(1.0, 1e-3, 1.0, 'b0')], []), {}, 'sıçrama yoksa boş sözlük')
rng = random.Random(3803)
for _ in range(20):
    n = rng.randint(1, 15)
    g = [K(rng.choice([2.0, 9.0, float('nan')]), rng.choice([1e-4, 5e-4, 1e-3]), rng.choice([0.0, 1.0, 2.0, 9.0, float('inf')]), rng.choice(['x', 'y', 'z', 'w'])) for _ in range(n)]
    s = rng.sample(range(n), rng.randint(0, n))
    got = sicrama_teshisi(g, s)
    en = max(k['lr'] for k in g)
    for t in s:
        k = g[t]
        if math.isnan(k['kayip']) or math.isinf(k['grad_norm']):
            exp = 'sayisal'
        elif [u for u in s if u != t and g[u]['batch'] == k['batch']]:
            exp = 'veri'
        elif k['lr'] >= 0.9 * en or (t > 0 and not math.isinf(g[t - 1]['grad_norm']) and g[t - 1]['grad_norm'] > 0 and k['grad_norm'] > 3 * g[t - 1]['grad_norm']):
            exp = 'ogrenme_orani'
        else:
            exp = 'belirsiz'
        eq(got[t], exp, 'rastgele günlükte bağımsız kuralla aynı')
    eq(sorted(got), sorted(s), 'her sıçrama için bir teşhis')
iyi = [K(1.0, 1e-3, 1.0, 'b0')]
for a in ([None, []], [(iyi[0],), []], [[], []], [[{'kayip': 1.0}], []], [[['kayip', 'lr', 'grad_norm', 'batch']], []], [[K(1.0, 0, 1.0, 'b')], []], [[K(1.0, -1e-3, 1.0, 'b')], []], [[K(1.0, True, 1.0, 'b')], []], [[K(1.0, float('nan'), 1.0, 'b')], []], [[K(1.0, float('inf'), 1.0, 'b')], []], [[K(True, 1e-3, 1.0, 'b')], []], [[K('1', 1e-3, 1.0, 'b')], []], [[K(1.0, 1e-3, None, 'b')], []], [[K(1.0, 1e-3, 1.0, '')], []], [[K(1.0, 1e-3, 1.0, 5)], []], [iyi, None], [iyi, [1]], [iyi, [-1]], [iyi, [0, 0]], [iyi, [0.0]], [iyi, [True]], [iyi, [False]]):
    raises(ValueError, sicrama_teshisi, *a, msg='bozuk girdi reddedilir')
```

```hint
Dört kuralı `if / elif` zinciriyle sırayla yaz. En büyük `lr`'yi döngüden önce bir kez hesapla. "Başka bir sıçrama adımı" derken `u != t` koşulunu unutma.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
Aşağıdaki iskeleti kendi cümlelerinle doldur; her adım bu derste hesapladığın bir sayıya ya da örneğe dayanır.

1. **Çerçeve (15 sn).** "Saatlerdir düzgün giden kayıp birden üç katına çıktı. Üç şüpheli var."
2. **Ölçüm (30 sn).** Tahmin adımı: tek bir 9,0 ortalamayı 2,6'ya çekti ve sonraki sıçramayı gizledi. "Medyan bu yüzden kullanılır."
3. **Kırpma (30 sn).** "Bir adımda gradient yüz kat büyürse ağırlıklar fırlar. Kırpma yönü korur, yalnız boyu sınırlar."
4. **Teşhis (25 sn).** "Önce bozuk sayılara, sonra tekrar eden batch'e, sonra öğrenme oranına bakılır. Sıra önemlidir."
5. **Kapanış (20 sn).** "Kırpma emniyet kemeridir; tedavi, şüpheli adımı yeniden koşup bakmaktır."
:::

::: anlat Sınır
Bu ders loss spike'ların üç olağan nedenini ve bir ilk ayırım yöntemini anlatır. Görevlerdeki günlükler sentetiktir ve üçüncü görevdeki kurallar birer **sezgisel**dir: eşikler (üç kat, %90) keyfîdir ve modele göre ayarlanmalıdır. Nedenler birbirini dışlamaz: yüksek öğrenme oranı zararsız bir batch'i sıçramaya çevirebilir; sayısal taşma çoğu zaman belirli bir veriyle tetiklenir. Kesin teşhis, şüpheli adımı aynı tohumla yeniden koşup katman katman bakmakla konur (bkz. `ai-uretim-39`). Medyana dayalı dedektör, kaybın hızla düştüğü eğitim başında yanlış alarm vermez ama kaybın yavaşça **yükseldiği** bir bozulmayı da yakalamaz; o ayrı bir ölçüm ister. Gradient kırpma sıçramanın etkisini sınırlar, nedenini gidermez; adımların çoğu kırpılıyorsa etkin öğrenme oranı sandığından düşüktür. Büyük dil modellerinde sıçramaların bir kısmı optimizer'ın iç durumundan kaynaklanır: Adam'ın ikinci moment tahmini küçüldüğünde tek bir büyük gradient orantısız bir adım üretir; bu derste modellenmez. Karışık hassasiyette iki farklı risk vardır: `fp16`'nın dinamik aralığı dardır (en büyük sonlu değer 65.504) ve taşma çok daha erken gelir; `bf16` ise `fp32` ile aynı üs bit sayısına ve yaklaşık aynı aralığa sahiptir, ama mantissası kısadır: onun sorunu taşma değil hassasiyet kaybıdır.

Kaynaklar: [Pascanu, Mikolov ve Bengio 2013 - On the difficulty of training recurrent neural networks](https://arxiv.org/abs/1211.5063), [PyTorch clip_grad_norm_ belgesi](https://pytorch.org/docs/stable/generated/torch.nn.utils.clip_grad_norm_.html), [Molybog vd. 2023 - A Theory on Adam Instability in Large-Scale Machine Learning](https://arxiv.org/abs/2304.09871), [Zhang vd. 2020 - Why Gradient Clipping Accelerates Training](https://arxiv.org/abs/1905.11881).
:::

::: dusun
Bir eğitimde gradient kırpma eşiği 1,0 ve günlük, adımların %85'inin kırpıldığını gösteriyor. Kayıp düzgün düşüyor ve hiç sıçrama yok. Bu iyi bir durum mu? Optimizer'ın gerçekte gördüğü gradient hakkında ne söyleyebilirsin ve öğrenme oranını değiştirmeden önce hangi sayıya bakardın?
:::

::: ozet
- Loss spike'ın üç olağan nedeni vardır: öğrenme oranı, belirli bir batch ve sayısal taşma.
- Sıçramayı gürültüden ayırmak için yakın geçmişin **medyanı** kullanılır; ortalama, bir sıçramadan sonra kör olur.
- Gradient kırpma birleşik `L2` normuna göre yapılır: yön korunur, boy sınırlanır. Kırpma öncesi norm günlüğe yazılır.
- Teşhiste önce sonlu olmayan sayılara, sonra tekrar eden batch'e, sonra gradient normunun ve öğrenme oranının seyrine bakılır.
- Kırpma emniyet kemeridir; kesin teşhis şüpheli adımı yeniden koşmakla konur.
:::
