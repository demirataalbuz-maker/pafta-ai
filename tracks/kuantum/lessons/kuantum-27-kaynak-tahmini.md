---
id: kuantum-27
title: "RSA-2048 Kaynak Tahmini · Logical ve Physical Qubit"
summary: Bir kuantum kaynak tahmininin donanım varsayımlarını (kapı hatası, döngü süresi, tepki süresi) sonuçtan ayır; sadeleştirilmiş bir yüzey kodu modeliyle fiziksel kübit ve süreyi hesapla ve tek bir varsayım değişince "bir haftanın altında" sonucunun nasıl değiştiğini tabloyla göster.
esleme: kuantum-28, kuantum-26, kuantum-23, kuantum-29
timeout: 30
---

::: anlat 1. Bir tahmin, bir takvim değildir
Craig Gidney, 21 Mayıs 2025'te *How to factor 2048 bit RSA integers with less than a million noisy qubits* (arXiv:2505.15917) çalışmasını yayımladı. Özete göre 2048 bitlik bir RSA sayısı, **bir milyondan az gürültülü kübitle** ve **bir haftadan kısa sürede** çarpanlarına ayrılabilir. Bu sonuç bazı donanım varsayımlarına bağlıdır, ve özet bunları açıkça yazar:

- tek biçimli kapı hata oranı **%0,1**,
- yüzey kodu döngü süresi **1 mikrosaniye**,
- kontrol sistemi tepki süresi **10 mikrosaniye**.

Bu bir **kaynak tahminidir**: "bu varsayımları sağlayan bir makine olsaydı, iş bu kadar kübit ve bu kadar süre isterdi." "RSA-2048 şu yıl kırılacak" gibi bir takvim kehaneti değildir. Böyle bir makinenin ne zaman yapılacağı ayrı ve bilinmeyen bir sorudur. Tahminin değeri, kurumların geçiş planlamasında (`kuantum-28`) bir **eşik** sağlamasıdır.

> [!NOTE]
> Bu dersteki hesap **sadeleştirilmiş bir öğretim modelidir**: makalenin devre ve kaynak hesabını yeniden üretmez. Bir mantıksal kübit için `2·d²` fiziksel kübit kabulü bu dersin modelidir, makalenin sayısı değildir. Görevlerdeki sayılar sentetik senaryolardır.
:::

::: anlat 2. Mekanizma: mantıksal kübitten fiziksel kübite, döngüden süreye
Gürültülü fiziksel kübitler doğrudan hesap yapamaz; hata düzeltme kodu birçok fiziksel kübitten bir **mantıksal kübit** kurar. Yüzey kodunda bu bedel kod mesafesi `d` ile büyür: bu dersin modelinde bir mantıksal kübit `2·d²` fiziksel kübittir. `d` tek sayıdır; büyüdükçe mantıksal hata azalır ama kübit maliyeti karesel artar. Buna, özel durumları üreten "fabrikaların" (*magic state factories*) fiziksel kübitleri eklenir:

`fiziksel = 2 · d² · mantıksal + fabrika`

Süre tarafında iki bileşen vardır: yüzey kodu döngülerinin toplamı ve kontrol sisteminin ölçüm sonucuna tepki vermesi gereken adımlar:

`süre = döngü_sayısı × döngü_süresi + tepki_sayısı × tepki_süresi`

Sonuç bu çarpımlara doğrusal bağlıdır. Döngü süresi 1 µs yerine 10 µs olursa döngü bileşeni on katına çıkar. Bu yüzden "bir haftadan kısa" sonucu, varsayım değişmeden aktarılamaz.

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| "Bir milyon kübit = RSA şu yıl kırılır" | Tahmin, varsayımları sağlayan bir makine varsayar | Kaynak tahmini ile takvimi ayır |
| Mantıksal ve fiziksel kübiti karıştırmak | Aradaki fark yüzlerce, binlerce kattır | Hata düzeltme bedelini açıkça hesapla |
| Çift kod mesafesi | Yüzey kodu mesafesi tek sayı seçilir | `d >= 3` ve tek |
| Varsayımları cümleden düşürmek | %0,1 hata, 1 µs döngü, 10 µs tepki olmadan sonuç anlamsız | Sonucu varsayımlarıyla birlikte aktar |
| Saniyeyi gün sanmak; birim karışıklığı | Nanosaniyeden güne 86,4 trilyon kat vardır | Tek birimde (ns) hesapla, sonra çevir |
:::

::: tahmin Döngü süresi on kat yavaşlarsa
Bir senaryoda 4 × 10¹¹ yüzey kodu döngüsü ve 10¹⁰ tepki adımı var. Tepki süresi 10 µs. Döngü süresi 1 µs ve 10 µs için toplam süre kaç gün?

```python
GUN_NS = 86_400 * 10**9
for dongu_ns in (1_000, 10_000):
    toplam = 4 * 10**11 * dongu_ns + 10**10 * 10_000
    print(dongu_ns, round(toplam / GUN_NS, 2))
```

???

```cikti
1000 5.79
10000 47.45
```
Aynı algoritma, aynı kübit sayısı; yalnız döngü süresi on kat arttı ve süre bir haftanın altından bir buçuk ayın üstüne çıktı. "Bir haftadan kısa" sonucu, 1 µs döngü varsayımıyla birlikte geçerlidir.
:::

::: gorev 1 · Kaynak senaryosunu varsayımlarıyla hesapla
`kaynak_senaryosu(logical, d, factory, cycles, cycle_ns, reactions, reaction_ns)` işlevini yaz.

- Bütün girdiler `bool` olmayan `int`. `logical > 0`; `d >= 3` ve tek; diğerleri `>= 0`. Değilse `ValueError`.
- Dönüş: `{'physical': 2 * d * d * logical + factory, 'duration_ns': cycles * cycle_ns + reactions * reaction_ns}`.

KUSURLU başlangıç fiziksel kübitte kod mesafesinin karesi yerine kendisini kullanıyor ve tepki süresini atlıyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
Path('ornek.json').write_text('[1400, 25, 100000, 400000000000, 1000, 10000000000, 10000]', encoding='utf-8')
```

```starter
def kaynak_senaryosu(logical, d, factory, cycles, cycle_ns, reactions, reaction_ns):
    return {'physical': 2 * d * logical + factory, 'duration_ns': cycles * cycle_ns}

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(kaynak_senaryosu(*_args))
```

```solution
def kaynak_senaryosu(logical, d, factory, cycles, cycle_ns, reactions, reaction_ns):
    xs = (logical, d, factory, cycles, cycle_ns, reactions, reaction_ns)
    if any(type(x) is not int for x in xs):
        raise ValueError('butun girdiler int olmali')
    if logical <= 0 or d < 3 or d % 2 == 0 or any(x < 0 for x in (factory, cycles, cycle_ns, reactions, reaction_ns)):
        raise ValueError('logical > 0, d >= 3 tek, digerleri >= 0 olmali')
    return {'physical': 2 * d * d * logical + factory,
            'duration_ns': cycles * cycle_ns + reactions * reaction_ns}

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(kaynak_senaryosu(*_args))
```

```test
need('kaynak_senaryosu')
eq(kaynak_senaryosu(1400, 25, 100_000, 4 * 10**11, 1_000, 10**10, 10_000),
   {'physical': 1_850_000, 'duration_ns': 500_000_000_000_000}, 'sentetik senaryo: 2·25²·1400 + 100000 kübit, 5×10¹⁴ ns')
eq(kaynak_senaryosu(1, 3, 0, 0, 0, 0, 0), {'physical': 18, 'duration_ns': 0}, 'en küçük geçerli değerler: d = 3, tek mantıksal kübit')
eq(kaynak_senaryosu(10, 5, 7, 3, 2, 4, 6), {'physical': 507, 'duration_ns': 30}, '2·25·10 + 7; 3·2 + 4·6')
eq(kaynak_senaryosu(2, 7, 1, 1, 0, 1, 9), {'physical': 197, 'duration_ns': 9}, 'sıfır döngü süresi: yalnız tepki')
for _i, _kotu in ((0, 0), (0, -1), (1, 2), (1, 4), (1, 1), (1, -3), (2, -1), (3, -1), (4, -1), (5, -1), (6, -1),
                  (0, True), (1, 3.0), (6, 1.5), (3, '1')):
    _arg = [10, 5, 7, 3, 2, 4, 6]
    _arg[_i] = _kotu
    raises(ValueError, kaynak_senaryosu, *_arg, msg=f'{_i}. argüman bozuk ({_kotu!r}) ValueError')
```

```hint
Önce bütün girdilerin `int` olduğunu (`type(x) is int`), sonra aralıklarını denetle. Fiziksel kübitte `d * d`, süreye hem döngü hem tepki bileşeni girer.
```
:::

::: gorev 2 · Döngü süresine duyarlılık tablosu
Bir senaryonun "bir haftanın altında" sonucunun döngü süresine ne kadar bağlı olduğunu gösteren `sure_tablosu(cycles, reactions, reaction_ns, cycle_ns_listesi)` işlevini yaz.

- `cycles`, `reactions`, `reaction_ns` `bool` olmayan, `>= 0` `int`. `cycle_ns_listesi` `bool` olmayan, `>= 0` `int`'lerden oluşan boş olmayan bir `list`. Değilse `ValueError`.
- Her döngü süresi için toplam süre: `toplam = cycles * cycle_ns + reactions * reaction_ns` (ns).
- Bir gün = `86_400 * 10**9` ns; bir hafta = 7 gün.
- Dönüş: girdi sırasıyla `[[cycle_ns, round(toplam / GUN, 2), toplam < HAFTA], ...]`.

KUSURLU başlangıç tepki bileşenini atlıyor ve haftayı 7 değil 5 gün sayıyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
GUN = 86_400 * 10**9

def sure_tablosu(cycles, reactions, reaction_ns, cycle_ns_listesi):
    satir = []
    for c in cycle_ns_listesi:
        toplam = cycles * c
        satir.append([c, round(toplam / GUN, 2), toplam < 5 * GUN])
    return satir
```

```solution
GUN = 86_400 * 10**9
HAFTA = 7 * GUN

def _sayi(x):
    return type(x) is int and x >= 0

def sure_tablosu(cycles, reactions, reaction_ns, cycle_ns_listesi):
    if not all(_sayi(x) for x in (cycles, reactions, reaction_ns)):
        raise ValueError('cycles, reactions, reaction_ns >= 0 int olmali')
    if not isinstance(cycle_ns_listesi, list) or not cycle_ns_listesi or not all(_sayi(c) for c in cycle_ns_listesi):
        raise ValueError('cycle_ns_listesi bos olmayan >= 0 int listesi olmali')
    satir = []
    for c in cycle_ns_listesi:
        toplam = cycles * c + reactions * reaction_ns
        satir.append([c, round(toplam / GUN, 2), toplam < HAFTA])
    return satir
```

```test
need('sure_tablosu')
import copy
_liste = [1_000, 2_000, 10_000]
_yedek = copy.deepcopy(_liste)
eq(sure_tablosu(4 * 10**11, 10**10, 10_000, _liste), [[1_000, 5.79, True], [2_000, 10.42, False], [10_000, 47.45, False]],
   'döngü süresi iki katına çıkınca bir hafta aşılır')
eq(_liste, _yedek, 'girdi değişmemeli')
_HAFTA = 7 * 86_400 * 10**9
eq(sure_tablosu(_HAFTA, 0, 0, [1]), [[1, 7.0, False]], 'tam bir hafta "altında" değildir')
eq(sure_tablosu(_HAFTA - 1, 0, 0, [1]), [[1, 7.0, True]], 'bir ns eksik: haftanın altında (gün yuvarlaması 7.0)')
eq(sure_tablosu(0, 3 * 86_400, 10**9, [5]), [[5, 3.0, True]], 'yalnız tepki bileşeni: 3 gün')
eq(sure_tablosu(10, 0, 0, [0]), [[0, 0.0, True]], 'sıfır süre')
eq(sure_tablosu(86_400 * 10**9, 0, 0, [3, 1]), [[3, 3.0, True], [1, 1.0, True]], 'girdi sırası korunur')
for _arg in ((-1, 0, 0, [1]), (0, -1, 0, [1]), (0, 0, -1, [1]), (True, 0, 0, [1]), (0, 1.0, 0, [1]), (0, 0, 0, []),
             (0, 0, 0, (1,)), (0, 0, 0, [1, -1]), (0, 0, 0, [True]), (0, 0, 0, [1.0]), (0, 0, 0, None)):
    raises(ValueError, sure_tablosu, *_arg, msg=f'bozuk argüman ValueError: {_arg!r}')
```

```hint
Toplam süreyi tam sayı nanosaniyede hesapla; günü yalnız yazdırırken `round(toplam / GUN, 2)` ile çevir. Hafta karşılaştırmasını yuvarlanmış gün üzerinden değil, tam sayı nanosaniye üzerinden yap.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Tahmin (25 sn).** "Gidney 2025'te RSA-2048'in bir milyondan az gürültülü kübitle ve bir haftadan kısa sürede çarpanlarına ayrılabileceğini gösterdi. Ama özet varsayımları da yazıyor: %0,1 kapı hatası, 1 µs döngü, 10 µs tepki."
2. **Mantıksal ve fiziksel (25 sn).** "Hata düzeltmede bir mantıksal kübit birçok fiziksel kübit ister; bizim sadeleştirilmiş modelimizde 2·d². Kod mesafesi büyüdükçe kübit karesel artıyor."
3. **Duyarlılık (35 sn).** "Aynı senaryoda yalnız döngü süresini değiştirdik: 1 µs'de 5,8 gün, 2 µs'de 10,4 gün, 10 µs'de 47 gün. 'Bir haftadan kısa' sonucu tek bir varsayımla birlikte geçerli."
4. **Takvim değil (20 sn).** "Bu bir kaynak eşiği; o makinenin ne zaman yapılacağını söylemiyor. Geçiş planına eşik olarak giriyor."
5. **Sınır (15 sn).** "Model öğretim amaçlı; makalenin devre hesabını yeniden üretmiyor."
:::

::: anlat Sınır ve kaynak
Bu ders makalenin kaynak hesabını yeniden üretmez. `2·d²` fiziksel kübit oranı, fabrika maliyetinin sabit bir ek olması ve sürenin iki doğrusal bileşenden oluşması öğretim amaçlı sadeleştirmelerdir. Gerçek tahminlerde yönlendirme (*routing*), paralellik, fabrika sayısı ile süre arasındaki ödünleşim ve hata oranına bağlı `d` seçimi birlikte hesaplanır. Ders bir "Q-Day" tarihi, yatırım ya da risk takvimi üretmez.

- Birincil kaynak: [Gidney — How to factor 2048 bit RSA integers with less than a million noisy qubits (arXiv:2505.15917, 21 Mayıs 2025)](https://arxiv.org/abs/2505.15917) (özet: bir milyondan az gürültülü kübit, bir haftadan kısa süre; %0,1 kapı hatası, 1 µs yüzey kodu döngüsü, 10 µs tepki süresi varsayımları). Doğrulama tarihi: 11 Kasım 2026.
:::

::: dusun
Bir haber başlığı "RSA-2048 bir haftada kırılabilir" diyor. Bu cümleyi tahminin kendi varsayımlarıyla yeniden yaz. Hangi bilgi eksik olduğu için başlık bir takvim kehaneti gibi okunuyor?
:::

::: ozet
- Bir kaynak tahmini, belirli donanım varsayımları altında gereken kübit ve süreyi verir; takvim kehaneti değildir.
- Gidney 2025'in varsayımları: %0,1 kapı hatası, 1 µs döngü, 10 µs tepki süresi.
- Mantıksal kübitten fiziksel kübite geçiş hata düzeltme bedelini taşır; bu derste `2·d²` modeliyle hesaplanır.
- Süre döngü süresine doğrusal bağlıdır; tek bir varsayım değişince "bir haftanın altında" sonucu değişebilir.
:::
