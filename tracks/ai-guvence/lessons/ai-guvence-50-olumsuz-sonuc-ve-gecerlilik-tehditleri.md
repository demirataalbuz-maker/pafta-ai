---
id: ai-guvence-50
title: "Olumsuz Sonucu Raporlama ve Geçerlilik Tehditleri · İşe Yaramadı da Bir Bulgudur"
summary: Yalnız anlamlı sonuçlar yayımlandığında etkinin ne kadar şiştiğini ölç, "fark yok" ile "fark gösterilemedi" ayrımını bir eşdeğerlik aralığıyla yap ve bir deney raporunu geçerlilik tehditleri listesine göre denetle.
esleme: ai-guvence-26, ai-guvence-48, ai-guvence-49, ai-matematik-07
timeout: 30
---

::: anlat 1. Görmediğin deneyler
Bir yöntemi on ekip denedi. Dokuzunda işe yaramadı; biri şansla anlamlı bir iyileşme buldu ve yayımladı. Literatürü okuyan kişi tek bir makale görür: "yöntem çalışıyor". Buna `publication bias` denir ve iki zararı vardır: var olmayan etkiler gerçek sanılır, gerçek ama küçük etkiler olduğundan büyük görünür.

Güvenlik araştırmasında bedeli daha ağırdır. "Bu savunma şu saldırıyı durdurmadı" sonucu yayımlanmazsa başka ekipler aynı savunmaya güvenmeye devam eder. "Bu saldırı şu modelde çalışmadı" sonucu ise ancak **doğru raporlanırsa** değerlidir: çalışmadı mı, yoksa yeterince denenmedi mi?

| Soru | Araç | Görev |
|---|---|---|
| Yalnız "başarılı" sonuçları görmek etkiyi ne kadar şişirir? | Seçilim yanlılığının ölçümü | 1 |
| "Fark bulunamadı" ne zaman "fark yok" demektir? | Güven aralığı ve eşdeğerlik sınırı | 2 |
| Bu sonuca ne kadar güvenmeliyim? | Geçerlilik tehditleri (`threats to validity`) | 3 |

> [!NOT]
> Görevlerdeki çalışma listeleri ve raporlar sentetiktir. Bu ders bir sonucun nasıl raporlanacağını ve okunacağını öğretir; belirli bir yöntemin işe yarayıp yaramadığı hakkında bir iddia taşımaz.
:::

::: anlat 2. Seçilim, eşdeğerlik ve geçerlilik
**Kazananın laneti.** Gerçek etki küçük ve ölçüm gürültülüyse, anlamlılık eşiğini yalnız **şansla yukarı sapan** ölçümler geçer. Yayımlanan çalışmaların ortalama etkisi bu yüzden gerçek etkiden sistemli olarak büyüktür (`winner's curse`). Sonradan yapılan replikasyonların "etki küçüldü" bulması çoğu zaman bundandır: etki küçülmedi, ilk ölçüm şişkindi.

**"Fark yok" demek kanıt ister.** `p > 0,05` yalnız şunu söyler: bu veriyle sıfır hipotezi reddedilemedi. Küçük bir deneyde büyük bir fark da gözden kaçabilir (bkz. `ai-guvence-49`, güç). Olumsuz bir sonucu savunmanın yolu güven aralığına bakmaktır. Önce, pratikte önemsiz saydığın en büyük farkı belirlersin: **eşdeğerlik sınırı** $\pm m$. Sonra aralığın nereye düştüğüne bakarsın:

| Güven aralığı | Sonuç |
|---|---|
| Tamamen $[-m, +m]$ içinde ve sıfırı içeriyor | **Eşdeğer**: önemli bir fark olmadığı gösterildi |
| Tamamen $[-m, +m]$ içinde ama sıfırı içermiyor | **Küçük fark**: gerçek ama önemsiz |
| Sıfırı içermiyor ve sınırın dışına taşıyor | **Fark var** |
| Sıfırı içeriyor ve sınırın dışına taşıyor | **Belirsiz**: veri yetmiyor; "fark yok" denemez |

Sonuncusu en sık görülen ve en sık yanlış raporlanan durumdur.

**Geçerlilik tehditleri.** Her deneyin sonucunu yanlış kılabilecek dört tür zayıflık vardır ve dürüst bir rapor bunları kendisi sayar:

- **İç geçerlilik:** gözlenen fark gerçekten incelenen değişkenden mi geliyor? (Taban çizgisi aynı bütçeyle ayarlandı mı? Test verisi eğitime sızmış olabilir mi?)
- **Dış geçerlilik:** sonuç başka modellere, verilere, ayarlara genellenir mi? (Tek model, tek veri kümesi mi?)
- **Yapı geçerliliği:** ölçü, iddia edilen şeyi ölçüyor mu? (Bir benchmark skoru "güvenlik" midir?)
- **İstatistiksel sonuç geçerliliği:** fark gürültüden ayırt edilebilir mi? (Tohum sayısı, güven aralığı, çoklu karşılaştırma düzeltmesi.)

Olumsuz sonuçta ek bir soru vardır: **yöntem adil bir şans aldı mı?** Hiperparametreler ayarlandı mı, uygulama doğrulandı mı (bilinen bir olumlu durumda çalıştığı gösterildi mi), deneme bütçesi neydi? Bunlar yazılmamışsa "çalışmadı" cümlesi "denemedim" cümlesinden ayırt edilemez.
:::

::: tahmin Yalnız "anlamlı" çıkanlar yayımlanırsa
Gerçek etkisi 1 puan olan bir yöntem beş ekip tarafından ölçüldü. Yalnız 3 puanın üstünde bulanlar yayımladı. Okuyucunun gördüğü ortalama etki ne yazdırılır?

```python
olcumler = [-1.0, 0.5, 1.0, 3.5, 4.0]

hepsi = sum(olcumler) / len(olcumler)
yayimlanan = [x for x in olcumler if x > 3.0]
gorulen = sum(yayimlanan) / len(yayimlanan)
print(hepsi, gorulen, round(gorulen / hepsi, 2))
```

???

```cikti
1.6 3.75 2.34
```
Beş ölçümün ortalaması 1,6 puandır (gerçek etkiye yakın bir tahmin). Ama yalnız iki ölçüm yayımlandı ve onların ortalaması 3,75'tir: okuyucu etkiyi 2,3 kat büyük görür. Hiç kimse yalan söylemedi; her ölçüm dürüstçe yapıldı. Yanlılık, hangi sonuçların görünür olduğundan geldi. Üç "başarısız" ölçüm yayımlansaydı tablo düzelirdi.
:::

::: gorev 1 · Seçilim yanlılığını ölç
`secilim_ozeti(calismalar, alfa)` işlevini yaz.

- `calismalar`: boş olmayan liste; her öğe `(etki, p_degeri)`; `etki` sayı, `p_degeri` `[0, 1]` aralığında sayı. `alfa`: `(0, 1)` aralığında sayı.
- Bir çalışma "yayımlanır", eğer `p_degeri < alfa` **ve** `etki > 0` ise (yalnız olumlu ve anlamlı sonuçlar).
- `tum_ortalama`: bütün çalışmaların ortalama etkisi. `yayimlanan_ortalama`: yayımlananların ortalama etkisi; hiç yoksa `None`.
- `yayimlanan_oran`: yayımlananların payı. `sisme`: `yayimlanan_ortalama / tum_ortalama`; yayımlanan yoksa ya da `tum_ortalama <= 0` ise `None`.
- Dönüş: bu dört anahtar; sayılar 9 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç yalnız `p` değerine bakıyor ve olumsuz yönde anlamlı çıkan sonuçları da "yayımlanan" sayıyor: yöntemin zarar verdiğini gösteren çalışmalar ortalamaya giriyor ve şişmeyi gizliyor.

```starter
def secilim_ozeti(calismalar, alfa):
    hepsi = [e for e, p in calismalar]
    yay = [e for e, p in calismalar if p < alfa]
    t = sum(hepsi) / len(hepsi)
    y = sum(yay) / len(yay) if yay else None
    return {'tum_ortalama': round(t, 9), 'yayimlanan_ortalama': None if y is None else round(y, 9), 'yayimlanan_oran': round(len(yay) / len(hepsi), 9), 'sisme': None if y is None else round(y / t, 9)}
```

```solution
def secilim_ozeti(calismalar, alfa):
    def sayi(x):
        return not isinstance(x, bool) and isinstance(x, (int, float))
    if not isinstance(calismalar, list) or not calismalar:
        raise ValueError('calismalar boş olmayan liste olmalı')
    for c in calismalar:
        if not isinstance(c, (tuple, list)) or len(c) != 2 or not sayi(c[0]) or not sayi(c[1]) or not 0 <= c[1] <= 1:
            raise ValueError('çalışma (etki, p_degeri) olmalı')
    if not sayi(alfa) or not 0 < alfa < 1:
        raise ValueError('alfa (0, 1) aralığında olmalı')
    n = len(calismalar)
    tum = sum(e for e, _ in calismalar) / n
    yay = [e for e, p in calismalar if p < alfa and e > 0]
    y = sum(yay) / len(yay) if yay else None
    return {
        'tum_ortalama': round(tum, 9) + 0.0,
        'yayimlanan_ortalama': None if y is None else round(y, 9),
        'yayimlanan_oran': round(len(yay) / n, 9),
        'sisme': None if y is None or tum <= 0 else round(y / tum, 9),
    }
```

```test
need('secilim_ozeti')
import random

C = [(-1.0, 0.6), (0.5, 0.7), (1.0, 0.3), (3.5, 0.03), (4.0, 0.01)]
r = secilim_ozeti(C, 0.05)
eq(r, {'tum_ortalama': 1.6, 'yayimlanan_ortalama': 3.75, 'yayimlanan_oran': 0.4, 'sisme': 2.34375}, 'yalnız anlamlı olumlu sonuçlar: etki 2.3 kat şişer')
r = secilim_ozeti([(2.0, 0.01), (-3.0, 0.01), (0.5, 0.5)], 0.05)
eq(r['yayimlanan_ortalama'], 2.0, 'olumsuz yönde anlamlı sonuç yayımlanan sayılmaz')
eq(r['yayimlanan_oran'], 0.333333333, 'üçte biri yayımlandı')
eq(r['sisme'], None, 'bütün çalışmaların ortalaması sıfırın altında: şişme oranı tanımsız')
r = secilim_ozeti([(0.2, 0.4), (0.1, 0.8)], 0.05)
eq(r, {'tum_ortalama': 0.15, 'yayimlanan_ortalama': None, 'yayimlanan_oran': 0.0, 'sisme': None}, 'hiçbiri yayımlanmadı')
r = secilim_ozeti([(1.0, 0.01), (2.0, 0.02)], 0.05)
eq(r['sisme'], 1.0, 'hepsi yayımlanırsa şişme yok')
eq(secilim_ozeti([(1.0, 0.05)], 0.05)['yayimlanan_oran'], 0.0, 'p tam eşikteyse yayımlanmaz (kesin küçük)')
rng = random.Random(5001)
for _ in range(25):
    c = [(round(rng.gauss(0.5, 2), 2), round(rng.random(), 3)) for _ in range(rng.randint(1, 20))]
    a = rng.choice([0.01, 0.05, 0.1])
    r = secilim_ozeti(c, a)
    tum = sum(e for e, _ in c) / len(c)
    y = [e for e, p in c if e > 0 and p < a]
    yakin(r['tum_ortalama'], tum, 'rastgele çalışmalarda genel ortalama', tol=1e-8)
    yakin(r['yayimlanan_oran'], len(y) / len(c), 'rastgele çalışmalarda yayımlanan oran', tol=1e-8)
    if y:
        yakin(r['yayimlanan_ortalama'], sum(y) / len(y), 'rastgele çalışmalarda yayımlanan ortalama', tol=1e-8)
        ok(r['yayimlanan_ortalama'] > 0, 'yayımlananların ortalaması pozitif')
        if tum > 0:
            yakin(r['sisme'], (sum(y) / len(y)) / tum, 'rastgele çalışmalarda şişme', tol=1e-6)
    else:
        eq((r['yayimlanan_ortalama'], r['sisme']), (None, None), 'yayımlanan yoksa None')
c = [(1.0, 0.01)]
secilim_ozeti(c, 0.05)
eq(c, [(1.0, 0.01)], 'girdi değişmez')
for a in ([None, 0.05], [[], 0.05], [[(1.0,)], 0.05], [[{1: 'a', 0.1: 'b'}], 0.05], [[(1.0, 1.5)], 0.05], [[(1.0, -0.1)], 0.05], [[(1.0, True)], 0.05], [[(1.0, float('nan'))], 0.05], [[("1", 0.1)], 0.05], [[(True, 0.1)], 0.05], [[(1.0, 0.1)], 0], [[(1.0, 0.1)], 1], [[(1.0, 0.1)], None], [[(1.0, 0.1)], float('nan')], [((1.0, 0.1),), 0.05]):
    raises(ValueError, secilim_ozeti, *a, msg='bozuk girdi reddedilir')
```

```hint
Yayımlanma koşulu iki parçalıdır: `p < alfa` ve `etki > 0`. Şişme, yayımlananların ortalamasının bütün çalışmaların ortalamasına oranıdır; payda pozitif değilse tanımsızdır.
```
:::

::: gorev 2 · "Fark yok" mu, "gösterilemedi" mi?
`fark_karari(fark, standart_hata, sinir, z)` işlevini yaz.

- `fark`: ölçülen fark; sayı. `standart_hata`: negatif olmayan sayı. `sinir`: eşdeğerlik sınırı `m`; pozitif sayı. `z`: güven düzeyinin çarpanı; pozitif sayı (%95 için 1,96).
- Güven aralığı: `[fark - z · standart_hata, fark + z · standart_hata]`.
- `sifiri_icerir`: `alt <= 0 <= ust`. `sinir_icinde`: `-sinir <= alt` ve `ust <= sinir`.
- `karar`: yukarıdaki tabloya göre `'esdeger'`, `'kucuk_fark'`, `'fark_var'` ya da `'belirsiz'`.
- Dönüş: `{'alt': ..., 'ust': ..., 'karar': ...}`; sınırlar 9 basamağa yuvarlanır ve karar **yuvarlanmamış** değerlerle verilir.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç aralık sıfırı içeriyorsa "eşdeğer" diyor: veri yetersiz olduğu için sıfırı içeren geniş bir aralığı "fark olmadığı gösterildi" diye raporluyor.

```starter
def fark_karari(fark, standart_hata, sinir, z):
    alt, ust = fark - z * standart_hata, fark + z * standart_hata
    return {'alt': round(alt, 9), 'ust': round(ust, 9), 'karar': 'esdeger' if alt <= 0 <= ust else 'fark_var'}
```

```solution
def fark_karari(fark, standart_hata, sinir, z):
    def sayi(x):
        return not isinstance(x, bool) and isinstance(x, (int, float))
    if not sayi(fark) or not sayi(standart_hata) or standart_hata < 0:
        raise ValueError('fark sayı, standart_hata negatif olmayan sayı olmalı')
    if not sayi(sinir) or not sinir > 0 or not sayi(z) or not z > 0:
        raise ValueError('sinir ve z pozitif sayı olmalı')
    alt, ust = fark - z * standart_hata, fark + z * standart_hata
    sifir = alt <= 0 <= ust
    icinde = -sinir <= alt and ust <= sinir
    if icinde:
        karar = 'esdeger' if sifir else 'kucuk_fark'
    else:
        karar = 'belirsiz' if sifir else 'fark_var'
    return {'alt': round(alt, 9) + 0.0, 'ust': round(ust, 9) + 0.0, 'karar': karar}
```

```test
need('fark_karari')
import random

eq(fark_karari(0.2, 0.3, 1.0, 2), {'alt': -0.4, 'ust': 0.8, 'karar': 'esdeger'}, 'dar aralık, sınırın içinde ve sıfırı içeriyor: eşdeğer')
eq(fark_karari(0.2, 2.0, 1.0, 2)['karar'], 'belirsiz', 'aynı fark, geniş aralık: sıfırı içeriyor ama sınırdan taşıyor; fark yok denemez')
eq(fark_karari(0.5, 0.1, 1.0, 2)['karar'], 'kucuk_fark', 'sıfırı içermiyor ama sınırın içinde: gerçek ve önemsiz')
eq(fark_karari(3.0, 0.5, 1.0, 2)['karar'], 'fark_var', 'sıfırın ve sınırın dışında')
eq(fark_karari(-3.0, 0.5, 1.0, 2)['karar'], 'fark_var', 'negatif yönde fark')
eq(fark_karari(0.9, 0.2, 1.0, 2)['karar'], 'fark_var', 'sıfırı içermiyor ve üst uç sınırı aşıyor')
eq(fark_karari(0.0, 0.0, 1.0, 2), {'alt': 0.0, 'ust': 0.0, 'karar': 'esdeger'}, 'belirsizlik yok, fark yok')
eq(fark_karari(0.0, 0.5, 1.0, 2)['karar'], 'esdeger', 'aralık tam sınırda biter: içinde sayılır')
eq(fark_karari(0.0, 1.0, 1.0, 0.5)['karar'], 'esdeger', 'küçük z çarpanı geçerlidir')
ok(fark_karari(0.2, 0.3, 1.0, 2)['karar'] != fark_karari(0.2, 2.0, 1.0, 2)['karar'], 'aynı nokta tahmini, farklı kararlar: belirleyen aralığın genişliği')
rng = random.Random(5002)
for _ in range(40):
    f, se = round(rng.uniform(-3, 3), 2), round(rng.uniform(0, 2), 2)
    m, z = rng.choice([0.5, 1.0, 2.0]), rng.choice([1.645, 1.96, 2.58])
    r = fark_karari(f, se, m, z)
    a, u = f - z * se, f + z * se
    yakin(r['alt'], a, 'alt sınır', tol=1e-8)
    yakin(r['ust'], u, 'üst sınır', tol=1e-8)
    icinde, sifir = (a >= -m and u <= m), (a <= 0 and u >= 0)
    eq(r['karar'], {(True, True): 'esdeger', (True, False): 'kucuk_fark', (False, True): 'belirsiz', (False, False): 'fark_var'}[(icinde, sifir)], 'rastgele değerlerde karar tablosu')
    ters = fark_karari(-f, se, m, z)
    eq(ters['karar'], r['karar'], 'farkın işareti kararı değiştirmez')
for a in ([None, 0.1, 1.0, 2], [0.1, -0.1, 1.0, 2], [0.1, None, 1.0, 2], [0.1, 0.1, 0, 2], [0.1, 0.1, -1, 2], [0.1, 0.1, float('nan'), 2], [0.1, 0.1, 1.0, 0], [0.1, 0.1, 1.0, None], [0.1, 0.1, 1.0, float('nan')], [True, 0.1, 1.0, 2], [0.1, 0.1, "1", 2]):
    raises(ValueError, fark_karari, *a, msg='bozuk girdi reddedilir')
```

```hint
İki bağımsız soru sor: aralık sıfırı içeriyor mu, aralık sınırın içinde mi? Dört birleşimin her biri bir karardır.
```
:::

::: gorev 3 · Raporu geçerlilik tehditlerine göre denetle
`gecerlilik_denetimi(rapor)` işlevini yaz. Bir deney raporunun kendi beyanlarını alır ve eksikleri sınıflandırır.

- `rapor`: aşağıdaki **tam sekiz** anahtara sahip sözlük:
  - `'tohum_sayisi'` (negatif olmayan `int`), `'guven_araligi'` (`bool`): istatistiksel geçerlilik
  - `'taban_ayarlandi'` (`bool`), `'sizinti_denetimi'` (`bool`): iç geçerlilik
  - `'model_sayisi'` (negatif olmayan `int`), `'veri_kumesi_sayisi'` (negatif olmayan `int`): dış geçerlilik
  - `'olcu_gerekcesi'` (`bool`): yapı geçerliliği
  - `'olumlu_kontrol'` (`bool`): yöntemin çalıştığı bilinen bir durumda sınanması (olumsuz sonuç için adil deneme)
- Eksik kuralları: `tohum_sayisi < 3` → `('istatistik', 'tohum_sayisi')`; `guven_araligi` yok → `('istatistik', 'guven_araligi')`; `taban_ayarlandi` yok → `('ic', 'taban_ayarlandi')`; `sizinti_denetimi` yok → `('ic', 'sizinti_denetimi')`; `model_sayisi < 2` → `('dis', 'model_sayisi')`; `veri_kumesi_sayisi < 2` → `('dis', 'veri_kumesi_sayisi')`; `olcu_gerekcesi` yok → `('yapi', 'olcu_gerekcesi')`; `olumlu_kontrol` yok → `('adil_deneme', 'olumlu_kontrol')`.
- `eksikler`: `[tür, anahtar]` çiftlerinin listesi; yukarıdaki sırayla.
- `turler`: eksik bulunan türlerin alfabetik sıralı, yinelenmeyen listesi.
- `olumsuz_sonuc_savunulabilir`: `'adil_deneme'` ve `'istatistik'` türlerinde hiç eksik yoksa `True`.
- Dönüş: `{'eksikler': ..., 'turler': ..., 'olumsuz_sonuc_savunulabilir': ...}`.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç yalnız `bool` alanlara bakıyor; sayıları (tohum, model, veri kümesi) hiç denetlemiyor. Tek tohumlu, tek modelli bir çalışma eksiksiz görünüyor.

```starter
def gecerlilik_denetimi(rapor):
    tur = {'guven_araligi': 'istatistik', 'taban_ayarlandi': 'ic', 'sizinti_denetimi': 'ic', 'olcu_gerekcesi': 'yapi', 'olumlu_kontrol': 'adil_deneme'}
    eksik = [[t, k] for k, t in tur.items() if rapor[k] is False]
    turler = sorted({t for t, _ in eksik})
    return {'eksikler': eksik, 'turler': turler, 'olumsuz_sonuc_savunulabilir': 'adil_deneme' not in turler}
```

```solution
def gecerlilik_denetimi(rapor):
    sayilar = ('tohum_sayisi', 'model_sayisi', 'veri_kumesi_sayisi')
    bayraklar = ('guven_araligi', 'taban_ayarlandi', 'sizinti_denetimi', 'olcu_gerekcesi', 'olumlu_kontrol')
    if not isinstance(rapor, dict) or set(rapor) != set(sayilar) | set(bayraklar):
        raise ValueError('rapor tam sekiz anahtara sahip olmalı')
    for k in sayilar:
        if isinstance(rapor[k], bool) or not isinstance(rapor[k], int) or rapor[k] < 0:
            raise ValueError(f'{k} negatif olmayan int olmalı')
    for k in bayraklar:
        if not isinstance(rapor[k], bool):
            raise ValueError(f'{k} bool olmalı')
    kurallar = [
        ('istatistik', 'tohum_sayisi', rapor['tohum_sayisi'] < 3),
        ('istatistik', 'guven_araligi', not rapor['guven_araligi']),
        ('ic', 'taban_ayarlandi', not rapor['taban_ayarlandi']),
        ('ic', 'sizinti_denetimi', not rapor['sizinti_denetimi']),
        ('dis', 'model_sayisi', rapor['model_sayisi'] < 2),
        ('dis', 'veri_kumesi_sayisi', rapor['veri_kumesi_sayisi'] < 2),
        ('yapi', 'olcu_gerekcesi', not rapor['olcu_gerekcesi']),
        ('adil_deneme', 'olumlu_kontrol', not rapor['olumlu_kontrol']),
    ]
    eksikler = [[tur, anahtar] for tur, anahtar, eksik in kurallar if eksik]
    turler = sorted({t for t, _ in eksikler})
    return {
        'eksikler': eksikler,
        'turler': turler,
        'olumsuz_sonuc_savunulabilir': 'adil_deneme' not in turler and 'istatistik' not in turler,
    }
```

```test
need('gecerlilik_denetimi')
import random

tam = {'tohum_sayisi': 5, 'guven_araligi': True, 'taban_ayarlandi': True, 'sizinti_denetimi': True, 'model_sayisi': 3, 'veri_kumesi_sayisi': 2, 'olcu_gerekcesi': True, 'olumlu_kontrol': True}
eq(gecerlilik_denetimi(tam), {'eksikler': [], 'turler': [], 'olumsuz_sonuc_savunulabilir': True}, 'eksiksiz rapor')
r = gecerlilik_denetimi(dict(tam, tohum_sayisi=1, model_sayisi=1))
eq(r['eksikler'], [['istatistik', 'tohum_sayisi'], ['dis', 'model_sayisi']], 'tek tohum ve tek model: sayılar da denetlenir')
eq(r['turler'], ['dis', 'istatistik'], 'türler alfabetik')
eq(r['olumsuz_sonuc_savunulabilir'], False, 'tek tohumla olumsuz sonuç savunulamaz')
r = gecerlilik_denetimi(dict(tam, olumlu_kontrol=False))
eq((r['eksikler'], r['olumsuz_sonuc_savunulabilir']), ([['adil_deneme', 'olumlu_kontrol']], False), 'olumlu kontrol yoksa çalışmadı ile denemedim ayırt edilemez')
r = gecerlilik_denetimi(dict(tam, model_sayisi=1, veri_kumesi_sayisi=1, olcu_gerekcesi=False))
eq(r['olumsuz_sonuc_savunulabilir'], True, 'dış ve yapı eksikleri sonucu daraltır ama olumsuz sonucu geçersiz kılmaz')
eq(r['turler'], ['dis', 'yapi'], 'iki tür')
hic = {'tohum_sayisi': 0, 'guven_araligi': False, 'taban_ayarlandi': False, 'sizinti_denetimi': False, 'model_sayisi': 0, 'veri_kumesi_sayisi': 0, 'olcu_gerekcesi': False, 'olumlu_kontrol': False}
r = gecerlilik_denetimi(hic)
eq(len(r['eksikler']), 8, 'sekiz eksik')
eq([k for _, k in r['eksikler']], ['tohum_sayisi', 'guven_araligi', 'taban_ayarlandi', 'sizinti_denetimi', 'model_sayisi', 'veri_kumesi_sayisi', 'olcu_gerekcesi', 'olumlu_kontrol'], 'belirtilen sırayla')
eq(r['turler'], ['adil_deneme', 'dis', 'ic', 'istatistik', 'yapi'], 'beş tür')
eq(gecerlilik_denetimi(dict(tam, tohum_sayisi=3, model_sayisi=2))['eksikler'], [], 'tam sınır değerleri yeterli')
rng = random.Random(5003)
for _ in range(25):
    rp = {'tohum_sayisi': rng.randint(0, 6), 'guven_araligi': rng.random() < 0.5, 'taban_ayarlandi': rng.random() < 0.5, 'sizinti_denetimi': rng.random() < 0.5, 'model_sayisi': rng.randint(0, 4), 'veri_kumesi_sayisi': rng.randint(0, 4), 'olcu_gerekcesi': rng.random() < 0.5, 'olumlu_kontrol': rng.random() < 0.5}
    r = gecerlilik_denetimi(rp)
    beklenen = sum([rp['tohum_sayisi'] < 3, not rp['guven_araligi'], not rp['taban_ayarlandi'], not rp['sizinti_denetimi'], rp['model_sayisi'] < 2, rp['veri_kumesi_sayisi'] < 2, not rp['olcu_gerekcesi'], not rp['olumlu_kontrol']])
    eq(len(r['eksikler']), beklenen, 'rastgele raporda eksik sayısı')
    eq(r['olumsuz_sonuc_savunulabilir'], rp['tohum_sayisi'] >= 3 and rp['guven_araligi'] and rp['olumlu_kontrol'], 'rastgele raporda savunulabilirlik')
    eq(r['turler'], sorted(set(t for t, _ in r['eksikler'])), 'türler eksiklerden türetilir')
rp = dict(tam)
gecerlilik_denetimi(rp)
eq(rp, tam, 'girdi değişmez')
eksik_anahtar = dict(tam); del eksik_anahtar['olumlu_kontrol']
for kotu in (None, {}, eksik_anahtar, dict(tam, ek=1), dict(tam, tohum_sayisi=-1), dict(tam, tohum_sayisi=2.0), dict(tam, tohum_sayisi=True), dict(tam, guven_araligi=1), dict(tam, olumlu_kontrol=None), dict(tam, model_sayisi='2'), [tam]):
    raises(ValueError, gecerlilik_denetimi, kotu, msg='bozuk rapor reddedilir')
```

```hint
Sekiz kuralı `(tür, anahtar, eksik_mi)` üçlüleri olarak sırayla yaz; eksik olanları süz. Savunulabilirlik iki türe bakar: `adil_deneme` ve `istatistik`.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
Aşağıdaki iskeleti kendi cümlelerinle doldur; her adım bu derste hesapladığın bir sayıya ya da örneğe dayanır.

1. **Soru (15 sn).** "Bir yöntemi beş ekip denedi, siz yalnız iki makale gördünüz. Diğer üçü nerede?"
2. **Sayılar (30 sn).** Beş ölçüm: -1, 0,5, 1, 3,5 ve 4 puan; ortalaması 1,6. Yalnız 3 puanın üstündekiler yayımlandı: görünen ortalama 3,75. Kimse yalan söylemedi, ama okuyucu etkiyi 2,3 kat büyük görüyor (`publication bias`).
3. **"Fark yok" demek (30 sn).** "`p > 0,05` 'fark yok' demek değildir; 'gösteremedim' demektir. 'Fark yok' diyebilmek için güven aralığının, veriyi görmeden önce belirlenmiş bir eşdeğerlik sınırının içinde kalması gerekir. Sıfırı içeren ama sınırdan taşan aralık yalnız 'veri yetmiyor' der."
4. **Güvenlik (25 sn).** "'Bu saldırı şu modelde çalışmadı' sonucu ancak adil denendiyse değerlidir: yöntem ayarlandı mı, çalıştığı bilinen bir durumda sınandı mı? Yayımlanmayan 'bu savunma durdurmadı' sonucu ise başkalarını o savunmaya güvenmeye devam ettirir."
5. **Kapanış (20 sn).** "Bir sonuca bakarken görmediğiniz deneyleri de sayın; kendi olumsuz sonucunuzu da zayıflıklarıyla birlikte yazın."
:::

::: anlat Sınır
Bu ders olumsuz sonuçların neden kaybolduğunu, "fark yok" iddiasının neye dayanması gerektiğini ve bir raporun zayıflıklarının nasıl sınıflandırılacağını anlatır; görevlerdeki veriler sentetiktir. Görev 1 yayımlanma kuralını tek bir eşikle modeller; gerçekte seçilim daha yumuşaktır (dergi, hakem, yazarın kendi tercihi) ve ayrıca bir çalışmanın **içinde** hangi analizin raporlanacağını seçmek (`p-hacking`) aynı şişmeyi üretir. Literatürdeki şişmeyi ölçmek için gerçek etkiyi bilmek gerekir; pratikte ancak ön kayıtlı replikasyonlarla tahmin edilir. Görev 2'deki eşdeğerlik sınırı bir **yargıdır**: hangi farkın "önemsiz" olduğu alana ve kullanım yerine bağlıdır ve veriler görülmeden önce belirlenmelidir; sonradan seçilen bir sınır her sonucu "eşdeğer" yapabilir. Güven aralığına dayalı karar, resmî iki tek yönlü test (`TOST`) ile yakındır ama aynı değildir. Görev 3'teki sekiz madde bir **asgari listedir**; eşikler (üç tohum, iki model) keyfîdir ve bir raporun bütün maddeleri karşılaması sonucun doğru olduğunu göstermez. Liste yazarın beyanını denetler, beyanın doğruluğunu değil. Bir güvenlik bulgusunda ek tehditler vardır: saldırganın uyarlanabilir olması (savunma yalnız bilinen saldırıya karşı sınandıysa), tehdit modelinin gerçekçiliği ve sonucun yayımlanmasının doğurduğu risk; bunlar `ai-guvence-29`'da ele alınır.

Kaynaklar: [Ioannidis 2005 - Why Most Published Research Findings Are False](https://doi.org/10.1371/journal.pmed.0020124), [Lakens 2017 - Equivalence Tests: A Practical Primer](https://doi.org/10.1177/1948550617697177), [Sculley vd. 2018 - Winner's Curse? On Pace, Progress, and Empirical Rigor](https://openreview.net/forum?id=rJWF0Fywf), [Carlini vd. 2019 - On Evaluating Adversarial Robustness](https://arxiv.org/abs/1902.06705), [Pineau vd. 2021 - Improving Reproducibility in Machine Learning Research](https://arxiv.org/abs/2003.12206).
:::

::: dusun
Bir makale "yöntem X'i denedik, işe yaramadı" diyor; tek model, tek tohum, hiperparametre ayarı yok ve X'in çalıştığı bilinen hiçbir durumda uygulama sınanmamış. Görev 3'teki listeye göre bu olumsuz sonuçta hangi türler eksik? Aynı cümleyi, bu eksikleri gizlemeden ama bulguyu da değersizleştirmeden nasıl yeniden yazardın?
:::

::: ozet
- Yalnız anlamlı ve olumlu sonuçlar yayımlandığında literatürdeki ortalama etki gerçek etkiden büyüktür (`winner's curse`).
- `p > 0,05` "fark yok" demek değildir; olumsuz sonuç, güven aralığının önceden belirlenmiş bir eşdeğerlik sınırının içinde kalmasıyla savunulur.
- Sıfırı içeren ama sınırdan taşan aralık "belirsiz"dir: veri yetmiyor.
- Geçerlilik tehditleri dört türdür: iç, dış, yapı ve istatistiksel; dürüst bir rapor bunları kendisi sayar.
- Olumsuz sonuçta ek soru adil denemedir: yöntem ayarlandı mı ve çalıştığı bilinen bir durumda sınandı mı?
:::
