---
id: ai-uretim-37
title: "Eğitim Profilleme · Zaman ve Bellek Nereye Gidiyor?"
summary: "Bir profiler kaydından her işlemin kendi süresini çıkar, bellek zaman çizelgesinden tepe noktasını ve sızıntıyı bul, ve Amdahl yasasıyla hangi aşamayı hızlandırmanın işe yarayacağını hesapla."
track: ai-uretim
order: 37
---

::: anlat 1. Ölçmeden hızlandırma
Bir eğitim yavaşsa ilk içgüdü modeli suçlamaktır: "ağ büyük, GPU yetmiyor". Çoğu zaman yanlıştır. GPU boşta beklerken veri yükleyici tek çekirdekte resim açıyor olabilir; bellek modelden değil, biriktirilen bir kayıp listesinden doluyor olabilir. Tahmin etmek yerine ölçersin; bunun aracı `profiler`'dır.

| Soru | Araç | Görev |
|---|---|---|
| Zaman gerçekte hangi işlemde harcanıyor? | Toplam süre ile **kendi** süre ayrımı | 1 |
| Bellek ne zaman, neyle tepe yapıyor; geri veriliyor mu? | Bellek zaman çizelgesi | 2 |
| Hangi aşamayı hızlandırmak toplamı düşürür? | `Amdahl` yasası | 3 |

> [!NOT]
> Bu dersin görevleri **kaydedilmiş biçimde, sentetik** profiler çıktısı üzerinde çalışır; canlı bir PyTorch eğitimi ölçülmez. Amaç, bir profiler tablosunu doğru okumayı öğrenmektir. Gerçek ölçümün nasıl alındığı aşağıda `norun` örneğiyle gösterilir.
>
> Görev 1'de örnek kayıt çalışma klasörüne `veri/profiler_olaylari.json` olarak kopyalanır: iki `train_step`, üç düzey iç içe 12 olay. Başlangıç kodu dosyayı `json.load` ile okur ve işlevini onun üstünde çalıştırıp sonucu yazdırır; Çalıştır'a basınca tabloyu görürsün. Kayıt üstünde denemek için yüklediğin listeyi kodda değiştir (bir olayın `bit` değerini büyüt, yeni bir çocuk olay ekle) ve yeniden çalıştır. Dosya her çalıştırmada kaynaktan yeniden kopyalanır, `veri/` altındaki değişiklik kalıcı değildir. Kontrol bu dosyayı değil, görmediğin ayrı kayıtları kullanır.
:::

::: anlat 2. Profiler çıktısını okumak
PyTorch'ta ölçüm şöyle alınır:

```python norun
import torch
from torch.profiler import profile, ProfilerActivity

with profile(activities=[ProfilerActivity.CPU, ProfilerActivity.CUDA], profile_memory=True) as prof:
    for batch in loader:
        loss = model(batch).loss
        loss.backward()
        optimizer.step()
        optimizer.zero_grad()

print(prof.key_averages().table(sort_by="self_cuda_time_total", row_limit=10))
```

Çıktıdaki iki sütun sürekli karıştırılır:

- **Toplam süre** (`total`): işlemin başından sonuna geçen süre; içinde çağırdığı alt işlemler dahil.
- **Kendi süresi** (`self`): yalnız o işlemin kendi kodunda geçen süre; alt işlemler **hariç**.

`train_step` toplam sürede her zaman en üsttedir, çünkü her şeyi o çağırır; ama kendi süresi neredeyse sıfırdır. Darboğazı bulmak için **kendi süresine** göre sıralarsın.

GPU ölçümünde iki tuzak vardır:

- **Eşzamansızlık.** CUDA çağrıları kuyruğa atılır ve hemen döner. `time.time()` ile ölçersen süre, sonucu bekleyen **ilk** satıra (`loss.item()`, bir `print`) yazılır. Doğru ölçüm için `torch.cuda.synchronize()` çağrılır ya da profiler kullanılır.
- **Isınma.** İlk birkaç adım bellek ayırma ve çekirdek derleme yüzünden yavaştır; ölçüme katılmaz.

**Bellek.** İki sayı farklıdır: `allocated` tensörlerin o an tuttuğu bellektir, `reserved` ise ayırıcının sistemden alıp elinde tuttuğu bellektir. `nvidia-smi` ise sürecin GPU'da tuttuğu **toplamı** gösterir: `reserved` belleği (ayırıcının önbelleğindeki boş bloklar dahil) ve bunun üstüne PyTorch ayırıcısının dışında kalan ayırmaları (`CUDA context`, kitaplıkların kendi belleği). Bu yüzden `nvidia-smi` sayısı `reserved`'dan büyüktür, `reserved` da `allocated`'dan. Eğitimde belleğin tepesi genellikle geri geçiştedir: ileri geçişin bütün ara aktivasyonları gradient için saklanır. En sık görülen sızıntı, her adımda `kayiplar.append(loss)` yazmaktır: tensörle birlikte bütün hesap grafı da tutulur. Doğrusu `loss.item()`'dır.

**Amdahl yasası.** Toplam sürenin `p` kadarını oluşturan bir aşamayı `k` kat hızlandırırsan toplam hızlanma:

$$S = \frac{1}{(1 - p) + \dfrac{p}{k}}$$

Aşama toplamın %10'uysa, onu sonsuz hızlandırsan bile toplam yalnız 1,11 kat hızlanır. Önce en büyük dilimi bul.
:::

::: tahmin Toplam süre mi, kendi süresi mi?
Bir adımın profiler kaydı iç içe üç işlem içeriyor. Her işlemin kendi süresi ne yazdırılır?

```python
olaylar = [
    ("train_step", 0, 100),
    ("forward", 5, 45),
    ("backward", 45, 95),
]

for ad, bas, bit in olaylar:
    cocuk = sum(b2 - a2 for ad2, a2, b2 in olaylar if ad2 != ad and bas <= a2 and b2 <= bit)
    print(ad, bit - bas, (bit - bas) - cocuk)
```

???

```cikti
train_step 100 10
forward 40 40
backward 50 50
```
`train_step`'in toplam süresi 100'dür ve tabloda en üstte görünür, ama kendi süresi yalnız 10'dur: geri kalan 90 birim `forward` ve `backward` içinde geçmiştir. Gerçek darboğaz, kendi süresi 50 olan `backward`'dır. Toplam süreye göre sıralasaydın her şeyi kapsayan işlemi suçlardın; bu hiçbir şey söylemez.
:::

::: gorev 1 · Her işlemin kendi süresi
`kendi_sureleri(olaylar)` işlevini yaz.

- `olaylar`: boş olmayan liste; her öğe `{'ad': str, 'bas': sayı, 'bit': sayı}` (tam bu üç anahtar); `bit >= bas`.
- Olaylar **düzgün iç içedir**: iki olay ya ayrıktır ya da biri diğerini tamamen kapsar. Kısmen kesişen iki olay varsa `ValueError`.
- Bir olayın **doğrudan çocukları**, onun içinde olup araya başka bir olay girmeyenlerdir. Kendi süresi = toplam süre − doğrudan çocukların toplam süreleri. Aralıkları **tam olarak aynı** iki olaydan listede önce gelen ebeveyn sayılır.
- Aynı ada sahip olaylar toplanır.
- Dönüş: `{ad: {'toplam': ..., 'kendi': ..., 'adet': ...}}`; süreler 9 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç bir olayın süresinden **bütün** torunlarının süresini çıkarıyor: iç içe üç düzeyde aynı süre iki kez düşülüyor ve kendi süresi negatif çıkabiliyor.

```starter
def kendi_sureleri(olaylar):
    out = {}
    for o in olaylar:
        ic = sum(p['bit'] - p['bas'] for p in olaylar if p is not o and o['bas'] <= p['bas'] and p['bit'] <= o['bit'])
        d = out.setdefault(o['ad'], {'toplam': 0.0, 'kendi': 0.0, 'adet': 0})
        d['toplam'] = round(d['toplam'] + o['bit'] - o['bas'], 9)
        d['kendi'] = round(d['kendi'] + (o['bit'] - o['bas']) - ic, 9)
        d['adet'] += 1
    return out


import json
with open("veri/profiler_olaylari.json", encoding="utf-8") as f:
    olaylar = json.load(f)
for ad, d in kendi_sureleri(olaylar).items():
    print(ad, d)
```
```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_uretim_veri import hazirla
hazirla("ai-uretim-37")
```

```solution
def kendi_sureleri(olaylar):
    def sayi(x):
        return not isinstance(x, bool) and isinstance(x, (int, float))
    if not isinstance(olaylar, list) or not olaylar:
        raise ValueError('olaylar boş olmayan liste olmalı')
    for o in olaylar:
        if not isinstance(o, dict) or set(o) != {'ad', 'bas', 'bit'} or not isinstance(o['ad'], str) or not o['ad']:
            raise ValueError('olay şeması')
        if not sayi(o['bas']) or not sayi(o['bit']) or o['bit'] < o['bas']:
            raise ValueError('bas ve bit sayı, bit >= bas olmalı')
    n = len(olaylar)

    def kapsar(i, j):
        a, b = olaylar[i], olaylar[j]
        if a['bas'] == b['bas'] and a['bit'] == b['bit']:
            return i < j
        return a['bas'] <= b['bas'] and b['bit'] <= a['bit']

    for i in range(n):
        for j in range(i + 1, n):
            a, b = olaylar[i], olaylar[j]
            ayrik = a['bit'] <= b['bas'] or b['bit'] <= a['bas']
            if not ayrik and not kapsar(i, j) and not kapsar(j, i):
                raise ValueError('olaylar kısmen kesişiyor')
    cocuk_toplami = [0.0] * n
    for j in range(n):
        ebeveynler = [i for i in range(n) if i != j and kapsar(i, j)]
        if not ebeveynler:
            continue
        en_yakin = ebeveynler[0]
        for i in ebeveynler[1:]:
            if kapsar(en_yakin, i):
                en_yakin = i
        cocuk_toplami[en_yakin] += olaylar[j]['bit'] - olaylar[j]['bas']
    out = {}
    for i, o in enumerate(olaylar):
        d = out.setdefault(o['ad'], {'toplam': 0.0, 'kendi': 0.0, 'adet': 0})
        sure = o['bit'] - o['bas']
        d['toplam'] += sure
        d['kendi'] += sure - cocuk_toplami[i]
        d['adet'] += 1
    return {ad: {'toplam': round(d['toplam'], 9), 'kendi': round(d['kendi'], 9), 'adet': d['adet']} for ad, d in out.items()}
```

```test
need('kendi_sureleri')
import random

def O(ad, bas, bit):
    return {'ad': ad, 'bas': bas, 'bit': bit}

r = kendi_sureleri([O('train_step', 0, 100), O('forward', 5, 45), O('backward', 45, 95)])
eq(r, {'train_step': {'toplam': 100.0, 'kendi': 10.0, 'adet': 1}, 'forward': {'toplam': 40.0, 'kendi': 40.0, 'adet': 1}, 'backward': {'toplam': 50.0, 'kendi': 50.0, 'adet': 1}}, 'iki düzey')
r = kendi_sureleri([O('adim', 0, 100), O('forward', 0, 60), O('attention', 10, 40), O('matmul', 15, 35)])
eq(r['adim']['kendi'], 40.0, 'yalnız doğrudan çocuk (forward) düşülür, torunlar değil')
eq(r['forward']['kendi'], 30.0, 'forward: 60 - 30')
eq(r['attention']['kendi'], 10.0, 'attention: 30 - 20')
eq(r['matmul']['kendi'], 20.0, 'yaprak: kendi = toplam')
r = kendi_sureleri([O('adim', 0, 10), O('relu', 1, 2), O('relu', 3, 5), O('relu', 6, 7)])
eq(r['relu'], {'toplam': 4.0, 'kendi': 4.0, 'adet': 3}, 'aynı adlı olaylar toplanır')
eq(r['adim']['kendi'], 6.0, 'üç çocuk düşülür')
r = kendi_sureleri([O('a', 0, 5), O('b', 5, 9)])
eq((r['a']['kendi'], r['b']['kendi']), (5.0, 4.0), 'uçları değen olaylar ayrıktır')
r = kendi_sureleri([O('dis', 0, 4), O('ic', 0, 4)])
eq((r['dis']['kendi'], r['ic']['kendi']), (0.0, 4.0), 'aynı aralık: listede önce gelen ebeveyn')
raises(ValueError, kendi_sureleri, [O('a', 0, 5), O('b', 3, 8)], msg='kısmen kesişen olaylar reddedilir')
rng = random.Random(3701)
def agac(bas, bit, derinlik, out):
    out.append(O(rng.choice(['x', 'y', 'z']), bas, bit))
    if derinlik == 0 or bit - bas < 4:
        return
    t = bas
    for _ in range(rng.randint(0, 3)):
        a = t + rng.randint(0, 2)
        b = a + rng.randint(1, max(1, (bit - a) // 2))
        if b > bit:
            break
        agac(a, b, derinlik - 1, out)
        t = b
for _ in range(20):
    ol = []
    agac(0, rng.randint(5, 60), 3, ol)
    r = kendi_sureleri(ol)
    yakin(sum(d['kendi'] for d in r.values()), ol[0]['bit'] - ol[0]['bas'], 'kendi sürelerin toplamı kökün toplam süresine eşit', tol=1e-7)
    ok(all(d['kendi'] >= -1e-9 for d in r.values()), 'kendi süresi negatif olmaz', got=r)
    eq(sum(d['adet'] for d in r.values()), len(ol), 'her olay bir kez sayılır')
    karisik = list(ol)
    rng.shuffle(karisik)
    if len({(o['bas'], o['bit']) for o in ol}) == len(ol):
        eq(kendi_sureleri(karisik), {k: r[k] for k in kendi_sureleri(karisik)}, 'aralıklar farklıysa olay sırası sonucu değiştirmez')
for kotu in (None, [], [O('a', 5, 3)], [{'ad': 'a', 'bas': 0}], [['ad', 'bas', 'bit']], [O('', 0, 1)], [O(1, 0, 1)], [O('a', '0', 1)], [O('a', 0, '1')], [O('a', True, 1)], [O('a', 0, True)], [dict(O('a', 0, 1), ek=1)], (O('a', 0, 1),)):
    raises(ValueError, kendi_sureleri, kotu, msg='bozuk girdi reddedilir')
```

```hint
Her olay için kendisini kapsayan olayları bul; bunlardan **en içteki** onun ebeveynidir. Olayın süresini yalnız o ebeveynin çocuk toplamına ekle. Kendi süre = toplam − çocuk toplamı.
```
:::

::: gorev 2 · Bellek tepesi ve sızıntı
`bellek_ozeti(olaylar)` işlevini yaz. Bir bellek zaman çizelgesini okur.

- `olaylar`: boş olmayan liste; her öğe `(zaman, etiket, bayt)`. `zaman` sayı ve **azalmayan** sırada; `etiket` boş olmayan `str`; `bayt` sıfırdan farklı `int` (pozitif ayırma, negatif geri verme).
- Hiçbir etiketin canlı belleği negatife düşemez (ayrılmamış bellek geri verilemez): `ValueError`.
- `tepe`: toplam canlı belleğin en büyük değeri. `tepe_zamani`: bu değere **ilk** ulaşıldığı zaman.
- `tepe_dagilimi`: tepe anında her etiketin canlı belleği (sıfır olanlar hariç).
- `sizinti`: çizelgenin sonunda hâlâ canlı olan etiketler ve bayt miktarları (sıfır olanlar hariç).
- Dönüş: `{'tepe': ..., 'tepe_zamani': ..., 'tepe_dagilimi': {...}, 'sizinti': {...}}`.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç tepeyi toplam **ayrılan** bellek olarak hesaplıyor; geri verilenleri düşmüyor. Aynı tamponu yüz kez ayırıp geri veren bir döngü yüz kat bellek kullanıyor görünür.

```starter
def bellek_ozeti(olaylar):
    toplam, dag = 0, {}
    for t, etiket, bayt in olaylar:
        if bayt > 0:
            toplam += bayt
            dag[etiket] = dag.get(etiket, 0) + bayt
    return {'tepe': toplam, 'tepe_zamani': olaylar[-1][0], 'tepe_dagilimi': dag, 'sizinti': dag}
```

```solution
def bellek_ozeti(olaylar):
    if not isinstance(olaylar, list) or not olaylar:
        raise ValueError('olaylar boş olmayan liste olmalı')
    canli, toplam = {}, 0
    tepe, tepe_zamani, tepe_dagilimi = 0, None, {}
    onceki = None
    for o in olaylar:
        if not isinstance(o, (tuple, list)) or len(o) != 3:
            raise ValueError('olay (zaman, etiket, bayt) olmalı')
        t, etiket, bayt = o
        if isinstance(t, bool) or not isinstance(t, (int, float)) or not isinstance(etiket, str) or not etiket:
            raise ValueError('zaman sayı, etiket boş olmayan str olmalı')
        if isinstance(bayt, bool) or not isinstance(bayt, int) or bayt == 0:
            raise ValueError('bayt sıfırdan farklı int olmalı')
        if onceki is not None and t < onceki:
            raise ValueError('zaman azalmayan sırada olmalı')
        onceki = t
        canli[etiket] = canli.get(etiket, 0) + bayt
        if canli[etiket] < 0:
            raise ValueError('ayrılmamış bellek geri verilemez')
        toplam += bayt
        if toplam > tepe:
            tepe, tepe_zamani = toplam, t
            tepe_dagilimi = {k: v for k, v in canli.items() if v}
    return {'tepe': tepe, 'tepe_zamani': tepe_zamani, 'tepe_dagilimi': tepe_dagilimi, 'sizinti': {k: v for k, v in canli.items() if v}}
```

```test
need('bellek_ozeti')
import random

ol = [(0, 'agirlik', 400), (1, 'aktivasyon', 300), (2, 'gradient', 400), (3, 'aktivasyon', -300), (4, 'gradient', -400)]
r = bellek_ozeti(ol)
eq(r['tepe'], 1100, 'tepe geri geçişte: ağırlık + aktivasyon + gradient')
eq(r['tepe_zamani'], 2, 'tepeye ilk ulaşılan an')
eq(r['tepe_dagilimi'], {'agirlik': 400, 'aktivasyon': 300, 'gradient': 400}, 'tepe anındaki dağılım')
eq(r['sizinti'], {'agirlik': 400}, 'sonda yalnız ağırlıklar canlı (beklenen)')
dongu = []
for i in range(100):
    dongu += [(2 * i, 'tampon', 50), (2 * i + 1, 'tampon', -50)]
eq(bellek_ozeti(dongu), {'tepe': 50, 'tepe_zamani': 0, 'tepe_dagilimi': {'tampon': 50}, 'sizinti': {}}, 'yüz kez ayır-geri ver: tepe 50, 5000 değil')
biriken = [(i, 'kayip_listesi', 10) for i in range(20)]
r = bellek_ozeti(biriken)
eq((r['tepe'], r['sizinti']), (200, {'kayip_listesi': 200}), 'hiç geri verilmeyen etiket: sızıntı')
r = bellek_ozeti([(0, 'a', 5), (1, 'a', -5), (2, 'b', 5)])
eq((r['tepe'], r['tepe_zamani']), (5, 0), 'eşit tepe değerinde ilk an')
eq(bellek_ozeti([(0, 'a', 5), (0, 'b', 7)])['tepe_zamani'], 0, 'aynı anda birden çok olay')
eq(bellek_ozeti([(0, 'a', 1)]), {'tepe': 1, 'tepe_zamani': 0, 'tepe_dagilimi': {'a': 1}, 'sizinti': {'a': 1}}, 'bir baytlık tepe')
raises(ValueError, bellek_ozeti, [(0, 'a', 5), (1, 'a', -6)], msg='ayrılandan fazlası geri verilemez')
raises(ValueError, bellek_ozeti, [(0, 'a', -1)], msg='ayrılmamış bellek geri verilemez')
raises(ValueError, bellek_ozeti, [(1, 'a', 5), (0, 'b', 5)], msg='zaman geri gidemez')
rng = random.Random(3702)
for _ in range(20):
    canli, ol, t = {}, [], 0
    for _ in range(rng.randint(1, 40)):
        t += rng.randint(0, 2)
        e = rng.choice(['w', 'act', 'grad', 'buf'])
        if canli.get(e, 0) > 0 and rng.random() < 0.4:
            b = -rng.randint(1, canli[e])
        else:
            b = rng.randint(1, 50)
        canli[e] = canli.get(e, 0) + b
        ol.append((t, e, b))
    r = bellek_ozeti(ol)
    kosu, en, en_t = 0, 0, None
    for z, _, b in ol:
        kosu += b
        if kosu > en:
            en, en_t = kosu, z
    eq((r['tepe'], r['tepe_zamani']), (en, en_t), 'rastgele çizelgede tepe ve zamanı')
    eq(sum(r['tepe_dagilimi'].values()), r['tepe'], 'tepe dağılımı tepeye toplanır')
    eq(r['sizinti'], {k: v for k, v in canli.items() if v}, 'rastgele çizelgede sonda canlı kalanlar')
ol = [(0, 'a', 5)]
bellek_ozeti(ol)
eq(ol, [(0, 'a', 5)], 'girdi değişmez')
for kotu in (None, [], [(0, 'a')], [(0, 'a', 1, 2)], [{0: 1, 'a': 2, 5: 3}], [(False, 'a', 5)], [(0, 'a', 0)], [(0, 'a', 1.5)], [(0, 'a', True)], [(0, '', 5)], [(0, 1, 5)], [('0', 'a', 5)], ((0, 'a', 5),)):
    raises(ValueError, bellek_ozeti, kotu, msg='bozuk girdi reddedilir')
```

```hint
İki şey tut: etiket başına canlı bellek ve toplam. Her olaydan sonra toplam eski tepeden **kesin büyükse** tepeyi, zamanını ve o anki dağılımın kopyasını güncelle.
```
:::

::: gorev 3 · Hangi aşamayı hızlandırmalı? (Amdahl)
`hizlanma_tahmini(sureler, asama, kat)` işlevini yaz.

- `sureler`: boş olmayan `{aşama adı: süre}` sözlüğü; süreler negatif olmayan sonlu sayı ve toplamları pozitif. `asama`: `sureler`'in bir anahtarı. `kat`: 1'den küçük olmayan sonlu sayı (o aşamanın kaç kat hızlandığı).
- `pay`: aşamanın toplam süredeki payı. `yeni_toplam`: aşamanın süresi `kat`'a bölündükten sonraki toplam.
- `hizlanma`: `eski toplam / yeni toplam`. `ust_sinir`: aşama sonsuz hızlansaydı ulaşılacak hızlanma, `1 / (1 - pay)`; `pay == 1` ise `None`.
- `darbogaz`: süresi en büyük aşama (eşitlikte alfabetik ilk).
- Dönüş: bu beş anahtar; kayan noktalı değerler 9 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç toplam hızlanmayı aşamanın hızlanmasına eşit sayıyor: veri yükleyiciyi 4 kat hızlandırınca bütün eğitimin 4 kat hızlanacağını söylüyor.

```starter
def hizlanma_tahmini(sureler, asama, kat):
    toplam = sum(sureler.values())
    return {'pay': round(sureler[asama] / toplam, 9), 'yeni_toplam': round(toplam / kat, 9), 'hizlanma': round(float(kat), 9), 'ust_sinir': None, 'darbogaz': max(sorted(sureler), key=lambda a: sureler[a])}
```

```solution
def hizlanma_tahmini(sureler, asama, kat):
    import math
    def sayi(x):
        return not isinstance(x, bool) and isinstance(x, (int, float)) and math.isfinite(x)
    if not isinstance(sureler, dict) or not sureler or any(not isinstance(a, str) or not a or not sayi(s) or s < 0 for a, s in sureler.items()):
        raise ValueError('sureler {ad: negatif olmayan süre} sözlüğü olmalı')
    toplam = sum(sureler.values())
    if not toplam > 0:
        raise ValueError('toplam süre pozitif olmalı')
    if asama not in sureler:
        raise ValueError('asama sözlükte yok')
    if not sayi(kat) or kat < 1:
        raise ValueError('kat 1 den küçük olamaz')
    pay = sureler[asama] / toplam
    yeni = toplam - sureler[asama] + sureler[asama] / kat
    en = sorted(sureler)[0]
    for a in sorted(sureler)[1:]:
        if sureler[a] > sureler[en]:
            en = a
    return {
        'pay': round(pay, 9),
        'yeni_toplam': round(yeni, 9),
        'hizlanma': round(toplam / yeni, 9),
        'ust_sinir': None if pay == 1 else round(1 / (1 - pay), 9),
        'darbogaz': en,
    }
```

```test
need('hizlanma_tahmini')
import random

S = {'veri': 60.0, 'forward': 15.0, 'backward': 20.0, 'optimizer': 5.0}
r = hizlanma_tahmini(S, 'veri', 4)
eq(r, {'pay': 0.6, 'yeni_toplam': 55.0, 'hizlanma': 1.818181818, 'ust_sinir': 2.5, 'darbogaz': 'veri'}, 'veri yükleyici 4 kat hızlanınca toplam 1.82 kat hızlanır, 4 değil')
r = hizlanma_tahmini(S, 'optimizer', 1000)
ok(r['hizlanma'] < 1.06, 'yüzde 5 lik aşamayı bin kat hızlandırmak neredeyse hiçbir şey değiştirmez', got=r)
yakin(r['ust_sinir'], 1 / 0.95, 'üst sınır 1 / (1 - pay)', tol=1e-8)
eq(hizlanma_tahmini(S, 'veri', 1)['hizlanma'], 1.0, 'kat 1: değişiklik yok')
eq(hizlanma_tahmini({'tek': 8.0}, 'tek', 2), {'pay': 1.0, 'yeni_toplam': 4.0, 'hizlanma': 2.0, 'ust_sinir': None, 'darbogaz': 'tek'}, 'tek aşama: üst sınır yok')
eq(hizlanma_tahmini({'b': 5.0, 'a': 5.0}, 'a', 2)['darbogaz'], 'a', 'eşit sürede alfabetik ilk')
eq(hizlanma_tahmini({'a': 0.0, 'b': 4.0}, 'a', 10), {'pay': 0.0, 'yeni_toplam': 4.0, 'hizlanma': 1.0, 'ust_sinir': 1.0, 'darbogaz': 'b'}, 'hiç zaman almayan aşama')
rng = random.Random(3703)
for _ in range(25):
    s = {f"a{i}": round(rng.uniform(0, 50), 2) for i in range(rng.randint(1, 6))}
    if sum(s.values()) == 0:
        s['a0'] = 1.0
    a, k = rng.choice(sorted(s)), rng.choice([1, 1.5, 2, 10, 1e6])
    r = hizlanma_tahmini(s, a, k)
    t = sum(s.values())
    p = s[a] / t
    yakin(r['hizlanma'], 1 / ((1 - p) + p / k), 'Amdahl formülüyle aynı', tol=1e-7)
    if r['ust_sinir'] is not None:
        ok(r['hizlanma'] <= r['ust_sinir'] + 1e-7, 'hızlanma üst sınırı aşamaz')
    eq(r['darbogaz'], min(s, key=lambda x: (-s[x], x)), 'darboğaz en uzun aşama')
s = {'a': 1.0, 'b': 2.0}
hizlanma_tahmini(s, 'a', 2)
eq(s, {'a': 1.0, 'b': 2.0}, 'girdi değişmez')
for a in ([None, 'a', 2], [[('a', 1.0)], 'a', 2], [{}, 'a', 2], [{'': 1.0}, '', 2], [{'a': -1.0}, 'a', 2], [{'a': 0.0}, 'a', 2], [{'a': float('nan')}, 'a', 2], [{'a': float('inf')}, 'a', 2], [{'a': '1'}, 'a', 2], [{'a': True}, 'a', 2], [{1: 1.0}, 1, 2], [{'a': 1.0}, 'yok', 2], [{'a': 1.0}, 'a', 0.5], [{'a': 1.0}, 'a', None], [{'a': 1.0}, 'a', True], [{'a': 1.0}, 'a', float('nan')], [{'a': 1.0}, 'a', float('inf')]):
    raises(ValueError, hizlanma_tahmini, *a, msg='bozuk girdi reddedilir')
```

```hint
Yeni toplam: `toplam − süre + süre / kat`. Hızlanma eski toplamın yeni toplama oranıdır. Üst sınır `1 / (1 − pay)`.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
Aşağıdaki iskeleti kendi cümlelerinle doldur; her adım bu derste hesapladığın bir sayıya ya da örneğe dayanır.

1. **Çerçeve (15 sn).** "Eğitim yavaş. İlk içgüdü: GPU yetmiyor. Çoğu zaman yanlış."
2. **Okuma (30 sn).** Tahmin adımı: `train_step` toplamda 100 birim, ama kendi süresi 10. "Asıl suçlu kendi süresi 50 olan geri geçiş."
3. **Amdahl (30 sn).** "Veri yükleme sürenin yüzde 60'ı; onu 4 kat hızlandırırsanız eğitim 4 kat değil, 1,8 kat hızlanır."
4. **Bellek (25 sn).** "En sık sızıntı tek satır: kayıp değerini sayı yerine tensör olarak listeye eklemek. Bütün hesap grafı da saklanır."
5. **Kapanış (20 sn).** "Tahmin etme, ölç; önce en büyük dilimi bul."
:::

::: anlat Sınır
Bu ders bir profiler kaydının nasıl okunacağını anlatır; görevlerdeki olaylar ve bellek çizelgeleri sentetiktir ve bu derste canlı bir eğitim ölçülmez. Gerçek profiler çıktısı çok daha gürültülüdür: iş parçacıkları arasında bölünmüş olaylar, eşzamansız GPU çekirdekleri ve ölçümün kendi yükü vardır; profiler açıkken kod daha yavaş çalışır ve küçük işlemlerin payı olduğundan büyük görünür. Görev 1 olayların düzgün iç içe olduğunu varsayar; gerçek CUDA olayları CPU olaylarıyla aynı zaman ekseninde iç içe değildir. Görev 2 yalnız `allocated` belleği izler; ayırıcının elinde tuttuğu `reserved` bellek ve parçalanma (`fragmentation`) yüzünden gerçek tepe daha yüksektir ve "bellek yetmedi" hatası canlı bellek sınırın altındayken de gelebilir. Amdahl yasası aşamaların sırayla çalıştığını varsayar; veri yükleme ayrı süreçlerde paralel koşuyorsa darboğaz toplam süre payından değil, hangi aşamanın diğerini beklettiğinden anlaşılır. Tek bir adımın ölçümü yanıltır: ısınma adımları atılmalı ve birçok adımın ortalaması alınmalıdır.

Kaynaklar: [PyTorch Profiler belgesi](https://pytorch.org/docs/stable/profiler.html), [PyTorch CUDA semantics: asynchronous execution ve memory management](https://pytorch.org/docs/stable/notes/cuda.html), [Amdahl 1967 - Validity of the single processor approach to achieving large scale computing capabilities](https://doi.org/10.1145/1465482.1465560).
:::

::: dusun
Bir eğitimde `nvidia-smi` GPU kullanımını %35 gösteriyor. Görev 3'teki dört aşamadan hangisinin payının büyük olduğundan şüphelenirsin? Şüpheni doğrulamak için hangi tek ölçümü alırdın ve o ölçüm ne çıkarsa yanıldığını kabul ederdin?
:::

::: ozet
- Profiler tablosunda toplam süre alt işlemleri içerir, kendi süresi içermez; darboğaz kendi süresine göre aranır.
- GPU çağrıları eşzamansızdır; `synchronize` etmeden alınan süre yanlış satıra yazılır. Isınma adımları ölçülmez.
- Belleğin tepesi genellikle geri geçiştedir; sonda canlı kalan beklenmedik etiket sızıntıdır.
- Amdahl yasası: bir aşamayı hızlandırmanın toplam kazancı o aşamanın payıyla sınırlıdır.
- Tahmin etme, ölç; önce en büyük dilimi bul.
:::
