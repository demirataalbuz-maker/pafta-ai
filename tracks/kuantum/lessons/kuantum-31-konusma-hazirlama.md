---
id: kuantum-31
title: "Konuşma Hazırlama · Teknik Bir Konuyu 20 Dakikada Anlatmak, Canlı Demo ve Soru-Cevap"
summary: "Bir konuşmanın zaman planını kur ve dengesini ölç, slaytların yoğunluğunu denetle ve canlı demonun yapılıp yapılmayacağına prova, süre ve yedek durumuna göre karar ver."
track: kuantum
order: 31
---

::: anlat 1. Bilmek ile anlatmak ayrı işlerdir
Bu yolun ve AI yollarının sonunda bir konuyu çözebilir, ölçebilir ve savunabilirsin. Bir salona anlatmak ise ayrı bir beceridir ve çoğu teknik insan onu şansa bırakır: slaytları son gece yapar, süreyi sahnede keşfeder, demo çalışmayınca donar.

İyi haber şu ki konuşmanın büyük kısmı **mühendisliktir**: zaman bir bütçedir, slayt bir arayüzdür, canlı demo bir üretim dağıtımıdır. Üçü de ölçülür ve önceden sınanır.

| Soru | Araç | Görev |
|---|---|---|
| 20 dakikaya ne sığar ve nasıl bölünür? | Zaman planı | 1 |
| Slaytlar dinleyiciye mi, konuşmacıya mı hizmet ediyor? | Slayt yoğunluğu denetimi | 2 |
| Demo canlı mı yapılmalı? | Risk ve yedek planı | 3 |

Konuşmanın içeriği için bu yolun önceki iki dersi (`kuantum-29`, `kuantum-30`) ve AI tarafındaki anlatım dersleri (`ai-temel-38`–`42`) hazır iskeletler verir; bu ders onları sahneye taşır.

> [!NOT]
> Bu dersteki eşikler (dakikada kelime, slayt başına kelime, prova sayısı) deneyime dayalı **başlangıç kurallarıdır**; kesin ölçüler değildir. Görevler bir konuşma planını sayılarla denetlemeyi öğretir; iyi bir konuşmanın tek ölçütü bunlar değildir.
:::

::: anlat 2. Zaman, slayt ve demo
**Tek cümle.** Hazırlığa slaytla değil, bir cümleyle başlarsın: "Dinleyici salondan çıkarken şunu bilecek: ...". Bu cümleye hizmet etmeyen her slayt çıkar. 20 dakikada **bir** ana fikir ve onu destekleyen **üç** nokta anlatılır; beş fikir anlatmaya çalışan konuşmadan hiçbiri akılda kalmaz.

**Zaman bir bütçedir.** Konuşma hızı dakikada yaklaşık 130 kelimedir; 20 dakika kabaca 2.600 kelime eder ve bu, sanıldığından çok azdır. Bütçeyi şöyle bölersin:

- **Açılış (yaklaşık %10):** soru, şaşırtıcı bir sayı ya da küçük bir hikâye. "Merhaba, ben..." ile başlama; dikkatin en yüksek olduğu ilk 30 saniyeyi harcama.
- **Gövde (yaklaşık %70):** üç nokta. Her biri bir iddia, bir kanıt ve bir örnek.
- **Kapanış (yaklaşık %10):** tek cümleni yeniden söyle ve dinleyiciden bir şey iste.
- **Pay (yaklaşık %10):** her konuşma provadakinden uzun sürer.

Soru-cevap süresi bu bütçenin **dışındadır**: 20 dakikalık bir oturumda 5 dakika soruya ayrılmışsa konuşman 15 dakikadır. Tek bir bölüm içerik süresinin %40'ından fazlasını alıyorsa konuşma dengesizdir; o bölüm ya iki konuşmadır ya da kısaltılmalıdır.

**Slayt bir arayüzdür.** Dinleyici aynı anda okuyup dinleyemez; slayt doluysa seni dinlemeyi bırakır. Başlangıç kuralları: slayt başına tek fikir, en çok 40 kelime; kod varsa en çok 12 satır ve yalnız konuştuğun satırlar vurgulanmış; slayt başına en az bir dakika (dakikada birden fazla slayt geçiyorsan ya slaytlar boştur ya da çok hızlısın). Slaytın başlığı bir konu adı değil, bir **iddia** olsun: "Sonuçlar" değil, "Kırpma, sıçramaları %90 azalttı".

**Canlı demo bir dağıtımdır.** Demo en akılda kalan şeydir ve en sık bozulan şeydir. Sahnede ağ kopar, sürüm değişmiştir, projektör çözünürlüğü farklıdır. Kural: **yedeği olmayan demo yapılmaz.** Demonun ekran kaydını al; canlı çalışmazsa kaydı oynatıp üstüne konuşursun ve dinleyici çoğu zaman farkı önemsemez. Ağ gerektiren demo canlı yapılmaz. Demo ayrılan süreye sığmıyorsa canlı yapılmaz. En az üç kez, sahnedeki koşullarda (aynı bilgisayar, tam ekran, büyük yazı tipi) prova edilmemiş demo canlı yapılmaz.

**Soru-cevap.** Soruyu salonun duyması için tekrar et; bu sana düşünme süresi de verir. Bilmiyorsan "bilmiyorum, ama şuna bakardım" de; uydurma. Düşmanca soruda soruyu sahibinden ayır: iddiayı cevapla, kişiyi değil. Uzayan soruyu "bunu aradan sonra konuşalım" diye kapat. En olası beş soruyu önceden yaz ve cevaplarını prova et; bunlardan biri neredeyse her zaman gelir.
:::

::: tahmin Yirmi dakikaya kaç slayt sığar?
20 dakikalık bir oturumda 5 dakika soru-cevaba ayrılmış. Konuşma hızı dakikada 130 kelime, slayt başına en az bir dakika. Ne yazdırılır?

```python
oturum, soru_cevap = 20, 5
konusma = oturum - soru_cevap
print("konuşma süresi:", konusma, "dk")
print("en çok kelime:", konusma * 130)
print("en çok slayt:", konusma // 1)
print("gövde:", round(konusma * 0.7, 1), "dk, nokta başına", round(konusma * 0.7 / 3, 1), "dk")
```

???

```cikti
konuşma süresi: 15 dk
en çok kelime: 1950
en çok slayt: 15
gövde: 10.5 dk, nokta başına 3.5 dk
```
"20 dakikalık konuşma" aslında 15 dakikadır: yaklaşık 1.950 kelime ve en çok 15 slayt. Gövdeye kalan 10,5 dakika üç noktaya bölününce her birine 3,5 dakika düşer: bir iddia, bir kanıt, bir örnek; daha fazlası sığmaz. 40 slayt hazırlayan biri ya dakikada üç slayt geçecek ya da yarısını atlayacaktır. Bütçeyi sahnede değil, hazırlıkta keşfedersin.
:::

::: gorev 1 · Zaman planı
`zaman_plani(bolumler, oturum_dk, soru_cevap_dk)` işlevini yaz.

- `bolumler`: boş olmayan liste; her öğe `(ad, dakika)`; `ad` boş olmayan ve yinelenmeyen `str`, `dakika` pozitif sayı.
- `oturum_dk`: pozitif sayı. `soru_cevap_dk`: negatif olmayan ve `oturum_dk`'dan küçük sayı.
- `konusma_dk`: `oturum_dk - soru_cevap_dk`. `planlanan_dk`: bölümlerin toplamı. `pay_dk`: `konusma_dk - planlanan_dk` (negatif olabilir).
- `durum`: `pay_dk < 0` ise `'tasiyor'`; `pay_dk < 0.1 · konusma_dk` ise `'payi_az'`; değilse `'uygun'`.
- `paylar`: `{ad: dakika / planlanan_dk}`. `dengesiz`: payı `0.4`'ten büyük olan bölüm adlarının listesi (girdi sırasıyla).
- Dönüş: bu altı anahtar; sayılar 6 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç soru-cevap süresini konuşma süresinden düşmüyor: 20 dakikalık oturuma 20 dakikalık konuşma planlıyor ve sorulara yer kalmıyor.

```starter
def zaman_plani(bolumler, oturum_dk, soru_cevap_dk):
    t = sum(d for _, d in bolumler)
    return {'konusma_dk': oturum_dk, 'planlanan_dk': t, 'pay_dk': oturum_dk - t, 'durum': 'tasiyor' if t > oturum_dk else 'uygun', 'paylar': {a: round(d / t, 6) for a, d in bolumler}, 'dengesiz': []}
```

```solution
def zaman_plani(bolumler, oturum_dk, soru_cevap_dk):
    def sayi(x):
        return not isinstance(x, bool) and isinstance(x, (int, float))
    if not isinstance(bolumler, list) or not bolumler:
        raise ValueError('bolumler boş olmayan liste olmalı')
    adlar = set()
    for b in bolumler:
        if not isinstance(b, (tuple, list)) or len(b) != 2 or not isinstance(b[0], str) or not b[0] or b[0] in adlar or not sayi(b[1]) or not b[1] > 0:
            raise ValueError('bölüm (yinelenmeyen ad, pozitif dakika) olmalı')
        adlar.add(b[0])
    if not sayi(oturum_dk) or not oturum_dk > 0 or not sayi(soru_cevap_dk) or not 0 <= soru_cevap_dk < oturum_dk:
        raise ValueError('oturum_dk pozitif, soru_cevap_dk [0, oturum_dk) aralığında olmalı')
    konusma = oturum_dk - soru_cevap_dk
    planlanan = sum(d for _, d in bolumler)
    pay = konusma - planlanan
    durum = 'tasiyor' if pay < 0 else ('payi_az' if pay < 0.1 * konusma else 'uygun')
    return {
        'konusma_dk': round(konusma, 6),
        'planlanan_dk': round(planlanan, 6),
        'pay_dk': round(pay, 6),
        'durum': durum,
        'paylar': {a: round(d / planlanan, 6) for a, d in bolumler},
        'dengesiz': [a for a, d in bolumler if d / planlanan > 0.4],
    }
```

```test
need('zaman_plani')
import random

B = [('acilis', 1.5), ('nokta1', 3.5), ('nokta2', 3.5), ('nokta3', 3.5), ('kapanis', 1.5)]
r = zaman_plani(B, 20, 5)
eq((r['konusma_dk'], r['planlanan_dk'], r['pay_dk'], r['durum']), (15, 13.5, 1.5, 'uygun'), '20 dakikalık oturum, 5 dakika soru: 15 dakikalık konuşma, 1.5 dakika pay')
eq(r['dengesiz'], [], 'dengeli plan')
yakin(sum(r['paylar'].values()), 1.0, 'paylar 1 e toplanır', tol=1e-5)
r = zaman_plani([('acilis', 2), ('govde', 16), ('kapanis', 2)], 20, 5)
eq((r['pay_dk'], r['durum']), (-5, 'tasiyor'), 'soru-cevap düşülünce 20 dakikalık plan 5 dakika taşıyor')
eq(r['dengesiz'], ['govde'], 'tek bölüm içeriğin yüzde 80 i')
r = zaman_plani([('a', 7), ('b', 7)], 15, 0)
eq(r['durum'], 'payi_az', '1 dakika pay, yüzde 10 un (1.5) altında')
eq(r['dengesiz'], ['a', 'b'], 'iki bölümün payı da yüzde 50')
r = zaman_plani([('a', 5), ('b', 5), ('c', 3.5)], 15, 0)
eq(r['durum'], 'uygun', 'tam yüzde 10 pay: uygun')
eq(zaman_plani([('tek', 3)], 10, 2)['dengesiz'], ['tek'], 'tek bölüm her zaman payın tamamıdır')
eq(zaman_plani([('a', 0.6)], 1, 0)['durum'], 'uygun', '1 dakikalık oturum, 0.4 dk pay: uygun')
rng = random.Random(3101)
for _ in range(25):
    b = [(f"b{i}", rng.choice([0.5, 1, 2, 3.5, 5, 8])) for i in range(rng.randint(1, 7))]
    o = rng.choice([10, 20, 30, 45])
    s = rng.choice([0, 5, 9])
    r = zaman_plani(b, o, s)
    t = sum(d for _, d in b)
    k = o - s
    yakin(r['planlanan_dk'], t, 'planlanan toplam', tol=1e-6)
    yakin(r['pay_dk'], k - t, 'pay', tol=1e-6)
    eq(r['durum'], 'tasiyor' if k - t < 0 else ('payi_az' if k - t < 0.1 * k else 'uygun'), 'rastgele planda durum')
    eq(r['dengesiz'], [a for a, d in b if d / t > 0.4], 'rastgele planda dengesiz bölümler')
b = [('a', 5)]
zaman_plani(b, 10, 2)
eq(b, [('a', 5)], 'girdi değişmez')
iyi = [('a', 5)]
for a in ([None, 20, 5], [[], 20, 5], [[('a',)], 20, 5], [[{'a': 1, 'b': 2}], 20, 5], [[('', 5)], 20, 5], [[(1, 5)], 20, 5], [[('a', 0)], 20, 5], [[('a', -1)], 20, 5], [[('a', float('nan'))], 20, 5], [[('a', '5')], 20, 5], [[('a', 5), ('a', 3)], 20, 5], [iyi, 0, 0], [iyi, -5, -10], [iyi, float('nan'), 0], [iyi, 20, 20], [iyi, 20, -1], [iyi, 20, float('nan')], [iyi, None, 5], [iyi, 20, True], [(('a', 5),), 20, 5]):
    raises(ValueError, zaman_plani, *a, msg='bozuk girdi reddedilir')
```

```hint
Önce konuşma süresini bul: oturum eksi soru-cevap. Pay, konuşma süresinden planlanan toplamın çıkarılmasıdır. Dengesizlik için her bölümün **planlanan toplam** içindeki payına bak.
```
:::

::: gorev 2 · Slayt yoğunluğu denetimi
`slayt_denetimi(slaytlar, konusma_dk)` işlevini yaz.

- `slaytlar`: boş olmayan liste; her öğe tam iki anahtarlı sözlük: `{'kelime': negatif olmayan int, 'kod_satiri': negatif olmayan int}`.
- `konusma_dk`: pozitif sayı.
- `slayt_basina_dk`: `konusma_dk / slayt sayısı`.
- `kalabalik`: `kelime > 40` olan slaytların indeksleri. `uzun_kod`: `kod_satiri > 12` olan slaytların indeksleri (indeksler 0'dan başlar).
- `uyarilar`: şu sırayla, koşulu tutanlar: `slayt_basina_dk < 1` → `'cok_hizli'`; `kalabalik` boş değil → `'kalabalik_slayt'`; `uzun_kod` boş değil → `'uzun_kod'`; toplam kelime `130 · konusma_dk`'yı aşıyor → `'okunamaz_toplam'` (slaytlardaki metin, konuşmada söylenebilecek kelime sayısından fazla).
- Dönüş: `{'slayt_basina_dk': ..., 'kalabalik': [...], 'uzun_kod': [...], 'uyarilar': [...]}`; süre 6 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç yalnız **ortalama** kelime sayısına bakıyor: otuz boş slaytın arasına gizlenmiş üç yüz kelimelik bir slaytı kaçırıyor.

```starter
def slayt_denetimi(slaytlar, konusma_dk):
    ort = sum(s['kelime'] for s in slaytlar) / len(slaytlar)
    return {'slayt_basina_dk': round(konusma_dk / len(slaytlar), 6), 'kalabalik': [], 'uzun_kod': [], 'uyarilar': ['kalabalik_slayt'] if ort > 40 else []}
```

```solution
def slayt_denetimi(slaytlar, konusma_dk):
    if not isinstance(slaytlar, list) or not slaytlar:
        raise ValueError('slaytlar boş olmayan liste olmalı')
    for s in slaytlar:
        if not isinstance(s, dict) or set(s) != {'kelime', 'kod_satiri'}:
            raise ValueError('slayt şeması')
        for k in ('kelime', 'kod_satiri'):
            if isinstance(s[k], bool) or not isinstance(s[k], int) or s[k] < 0:
                raise ValueError(f'{k} negatif olmayan int olmalı')
    if isinstance(konusma_dk, bool) or not isinstance(konusma_dk, (int, float)) or not konusma_dk > 0:
        raise ValueError('konusma_dk pozitif sayı olmalı')
    basina = konusma_dk / len(slaytlar)
    kalabalik = [i for i, s in enumerate(slaytlar) if s['kelime'] > 40]
    uzun_kod = [i for i, s in enumerate(slaytlar) if s['kod_satiri'] > 12]
    toplam = sum(s['kelime'] for s in slaytlar)
    kurallar = [('cok_hizli', basina < 1), ('kalabalik_slayt', bool(kalabalik)), ('uzun_kod', bool(uzun_kod)), ('okunamaz_toplam', toplam > 130 * konusma_dk)]
    return {'slayt_basina_dk': round(basina, 6), 'kalabalik': kalabalik, 'uzun_kod': uzun_kod, 'uyarilar': [ad for ad, tutar in kurallar if tutar]}
```

```test
need('slayt_denetimi')
import random

def S(kelime, kod=0):
    return {'kelime': kelime, 'kod_satiri': kod}

r = slayt_denetimi([S(20), S(30, 8), S(15)], 15)
eq(r, {'slayt_basina_dk': 5.0, 'kalabalik': [], 'uzun_kod': [], 'uyarilar': []}, 'seyrek ve temiz slaytlar')
r = slayt_denetimi([S(5)] * 30 + [S(300)], 15)
eq(r['kalabalik'], [30], 'ortalama düşük olsa da tek kalabalık slayt yakalanır')
eq(r['uyarilar'], ['cok_hizli', 'kalabalik_slayt'], '31 slayt 15 dakikaya: dakikada ikiden fazla')
r = slayt_denetimi([S(10, 40), S(10, 12), S(10, 13)], 10)
eq((r['uzun_kod'], r['uyarilar']), ([0, 2], ['uzun_kod']), 'tam 12 satır sınırda kalır; 13 ve 40 uzun')
r = slayt_denetimi([S(40), S(41)], 5)
eq(r['kalabalik'], [1], 'tam 40 kelime kalabalık sayılmaz')
r = slayt_denetimi([S(40)] * 60, 15)
eq(r['uyarilar'], ['cok_hizli', 'okunamaz_toplam'], 'hiçbiri tek başına kalabalık değil ama toplam metin konuşmadan uzun (2400 > 1950)')
eq(slayt_denetimi([S(0)], 1)['slayt_basina_dk'], 1.0, 'tam bir dakika: çok hızlı değil')
eq(slayt_denetimi([S(0)], 1)['uyarilar'], [], 'boş tek slayt')
eq(slayt_denetimi([S(130)], 1)['uyarilar'], ['kalabalik_slayt'], 'tam 130 kelime: kalabalık ama toplam sınırda')
eq(slayt_denetimi([S(131)], 1)['uyarilar'], ['kalabalik_slayt', 'okunamaz_toplam'], '131 kelime toplam sınırı aşar')
rng = random.Random(3102)
for _ in range(25):
    sl = [S(rng.choice([0, 10, 25, 40, 41, 90]), rng.choice([0, 5, 12, 13, 30])) for _ in range(rng.randint(1, 40))]
    dk = rng.choice([5, 15, 20, 45])
    r = slayt_denetimi(sl, dk)
    yakin(r['slayt_basina_dk'], dk / len(sl), 'slayt başına süre', tol=1e-6)
    eq(r['kalabalik'], [i for i in range(len(sl)) if sl[i]['kelime'] > 40], 'rastgele slaytlarda kalabalık indeksleri')
    eq(r['uzun_kod'], [i for i in range(len(sl)) if sl[i]['kod_satiri'] > 12], 'rastgele slaytlarda uzun kod indeksleri')
    eq('cok_hizli' in r['uyarilar'], dk / len(sl) < 1, 'çok hızlı uyarısı')
    eq('okunamaz_toplam' in r['uyarilar'], sum(s['kelime'] for s in sl) > 130 * dk, 'toplam metin uyarısı')
sl = [S(5)]
slayt_denetimi(sl, 5)
eq(sl, [S(5)], 'girdi değişmez')
for a in ([None, 15], [[], 15], [[{'kelime': 5}], 15], [[['kelime', 'kod_satiri']], 15], [[dict(S(5), ek=1)], 15], [[S(-1)], 15], [[S(5.0)], 15], [[S(True)], 15], [[S(5, -1)], 15], [[S(5)], 0], [[S(5)], float('nan')], [[S(5)], None], [[S(5)], True], [(S(5),), 15]):
    raises(ValueError, slayt_denetimi, *a, msg='bozuk girdi reddedilir')
```

```hint
Ortalamaya değil, tek tek slaytlara bak: koşulu aşanların indekslerini topla. Uyarıları dört kuralın sırasıyla üret.
```
:::

::: gorev 3 · Demo canlı mı yapılmalı?
`demo_karari(demo)` işlevini yaz.

- `demo`: tam şu beş anahtara sahip sözlük: `'ag_gerekir'` (`bool`), `'kayit_var'` (`bool`), `'prova_sayisi'` (negatif olmayan `int`), `'sure_sn'` (pozitif sayı), `'ayrilan_sn'` (pozitif sayı).
- `riskler`: şu sırayla, koşulu tutanlar: `ag_gerekir` → `'ag'`; `prova_sayisi < 3` → `'az_prova'`; `sure_sn > ayrilan_sn` → `'sureye_sigmiyor'`.
- `karar`:
  - Risk yoksa → `'canli'`.
  - Risk var ve `kayit_var` ise → `'kayittan'` (kaydı oynat, üstüne konuş).
  - Risk var ve kayıt yoksa → `'cikar'` (yedeksiz, riskli demo yapılmaz).
- `yedek_hazir`: `kayit_var`. Karar `'canli'` olsa bile kayıt yoksa `riskler` listesinin sonuna `'yedek_yok'` eklenir (karar değişmez).
- Dönüş: `{'karar': ..., 'riskler': [...], 'yedek_hazir': ...}`.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç yalnız demonun süreye sığıp sığmadığına bakıyor: ağ gerektiren, hiç prova edilmemiş ve yedeği olmayan bir demoya "canlı yap" diyor.

```starter
def demo_karari(demo):
    return {'karar': 'canli' if demo['sure_sn'] <= demo['ayrilan_sn'] else 'cikar', 'riskler': [], 'yedek_hazir': demo['kayit_var']}
```

```solution
def demo_karari(demo):
    anahtarlar = {'ag_gerekir', 'kayit_var', 'prova_sayisi', 'sure_sn', 'ayrilan_sn'}
    if not isinstance(demo, dict) or set(demo) != anahtarlar:
        raise ValueError('demo tam beş anahtara sahip olmalı')
    if not isinstance(demo['ag_gerekir'], bool) or not isinstance(demo['kayit_var'], bool):
        raise ValueError('ag_gerekir ve kayit_var bool olmalı')
    p = demo['prova_sayisi']
    if isinstance(p, bool) or not isinstance(p, int) or p < 0:
        raise ValueError('prova_sayisi negatif olmayan int olmalı')
    for k in ('sure_sn', 'ayrilan_sn'):
        if isinstance(demo[k], bool) or not isinstance(demo[k], (int, float)) or not demo[k] > 0:
            raise ValueError(f'{k} pozitif sayı olmalı')
    kurallar = [('ag', demo['ag_gerekir']), ('az_prova', p < 3), ('sureye_sigmiyor', demo['sure_sn'] > demo['ayrilan_sn'])]
    riskler = [ad for ad, tutar in kurallar if tutar]
    if not riskler:
        karar = 'canli'
    else:
        karar = 'kayittan' if demo['kayit_var'] else 'cikar'
    if karar == 'canli' and not demo['kayit_var']:
        riskler.append('yedek_yok')
    return {'karar': karar, 'riskler': riskler, 'yedek_hazir': demo['kayit_var']}
```

```test
need('demo_karari')
import random

def D(ag, kayit, prova, sure, ayrilan):
    return {'ag_gerekir': ag, 'kayit_var': kayit, 'prova_sayisi': prova, 'sure_sn': sure, 'ayrilan_sn': ayrilan}

eq(demo_karari(D(False, True, 5, 60, 90)), {'karar': 'canli', 'riskler': [], 'yedek_hazir': True}, 'çevrimdışı, provalı, süreye sığıyor, yedeği var: canlı')
eq(demo_karari(D(True, True, 5, 60, 90)), {'karar': 'kayittan', 'riskler': ['ag'], 'yedek_hazir': True}, 'ağ gerektiriyor: kayıttan oynat')
eq(demo_karari(D(True, False, 0, 200, 90)), {'karar': 'cikar', 'riskler': ['ag', 'az_prova', 'sureye_sigmiyor'], 'yedek_hazir': False}, 'üç risk ve yedek yok: demoyu çıkar')
eq(demo_karari(D(False, False, 5, 60, 90)), {'karar': 'canli', 'riskler': ['yedek_yok'], 'yedek_hazir': False}, 'risk yok ama yedek de yok: canlı, uyarıyla')
eq(demo_karari(D(False, True, 2, 60, 90))['karar'], 'kayittan', 'iki prova yetmez')
eq(demo_karari(D(False, True, 3, 90, 90))['karar'], 'canli', 'üç prova ve tam süre: sınır değerler yeterli')
eq(demo_karari(D(False, False, 3, 91, 90))['karar'], 'cikar', 'bir saniye taşıyor ve yedek yok')
eq(demo_karari(D(False, True, 3, 0.5, 1))['karar'], 'canli', 'küçük pozitif süreler geçerlidir')
rng = random.Random(3103)
for _ in range(30):
    d = D(rng.random() < 0.4, rng.random() < 0.5, rng.randint(0, 6), rng.choice([30, 60, 120, 300]), rng.choice([60, 120]))
    r = demo_karari(d)
    risk = d['ag_gerekir'] or d['prova_sayisi'] < 3 or d['sure_sn'] > d['ayrilan_sn']
    eq(r['karar'], 'canli' if not risk else ('kayittan' if d['kayit_var'] else 'cikar'), 'rastgele demoda karar')
    eq(r['yedek_hazir'], d['kayit_var'], 'yedek durumu')
    eq('yedek_yok' in r['riskler'], (not risk) and not d['kayit_var'], 'yedek_yok yalnız canlı kararında eklenir')
    ok(r['karar'] != 'canli' or not d['ag_gerekir'], 'ağ gerektiren demo asla canlı yapılmaz')
d = D(False, True, 5, 60, 90)
kopya = dict(d)
demo_karari(d)
eq(d, kopya, 'girdi değişmez')
iyi = D(False, True, 5, 60, 90)
eksik = dict(iyi); del eksik['kayit_var']
for kotu in (None, {}, eksik, dict(iyi, ek=1), dict(iyi, ag_gerekir=1), dict(iyi, kayit_var=None), dict(iyi, prova_sayisi=-1), dict(iyi, prova_sayisi=2.0), dict(iyi, prova_sayisi=True), dict(iyi, sure_sn=0), dict(iyi, sure_sn=True), dict(iyi, sure_sn=float('nan')), dict(iyi, ayrilan_sn=-5), dict(iyi, ayrilan_sn=float('nan')), dict(iyi, sure_sn='60'), [iyi]):
    raises(ValueError, demo_karari, kotu, msg='bozuk girdi reddedilir')
```

```hint
Önce üç riski sırayla topla. Risk yoksa canlı; varsa kayda göre `kayittan` ya da `cikar`. `yedek_yok` uyarısı yalnız karar `canli` iken ve kayıt yokken eklenir.
```
:::

::: anlat 3. Konuşmadan önceki kontrol listesi
Bir hafta önce:

1. Tek cümleni yaz. Üç noktanı o cümleyi destekleyecek biçimde seç.
2. Zaman planını kur (Görev 1). Soru-cevap süresini düşmeyi unutma.
3. Slaytları yap ve denetle (Görev 2). Başlıkları iddiaya çevir.
4. Demonun ekran kaydını al. Kararını ver (Görev 3).
5. En olası beş soruyu ve cevaplarını yaz.

Üç gün önce:

6. Konuşmayı **yüksek sesle**, ayakta ve kronometreyle prova et. Sessiz okumak prova değildir; süre her zaman daha uzun çıkar.
7. Bir kişiye anlat ve yalnız şunu sor: "Ana fikir neydi?" Senin tek cümlenle aynı değilse konuşmayı değil, cümleyi suçlama; yapıyı düzelt.

Konuşma günü:

8. Slaytların ve kaydın bir kopyasını çevrimdışı ve ikinci bir yerde bulundur. Sunum bilgisayarında bildirimleri kapat.
9. Salona erken git; projektörü, sesi ve yazı tipi boyutunu arka sıradan kontrol et.
10. İlk cümleni ezberle. Gerisini ezberleme; yapıyı bil.

Kendi konularında hazır iskeletler: `ai-temel-38` (LLM neden insan gibi düşünmez), `ai-temel-39` (halüsinasyon), `ai-temel-41` (AI nasıl daha iyi yapılır), `ai-temel-42` (AGI tahminleri), `kuantum-29` (kuantum bilgisayar ne yapar), `kuantum-30` (kuantum haberleri). Her birindeki "iki dakikada nasıl anlatırsın" bölümü, 20 dakikalık bir konuşmanın üç noktasından biri olabilir.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
Bu dersin kendi konusunu, yani konuşma hazırlamayı, iki dakikada anlatmak için iskelet. Kendi cümlelerinle doldur; her adım bu derste hesapladığın bir sayıya dayanır. Bölüm 3'teki 20 dakikalık plan ayrıdır ve yerinde durur.

1. **Soru (15 sn).** "20 dakikalık konuşmanız aslında kaç dakika?"
2. **Zaman bir bütçedir (30 sn).** "5 dakika soru-cevap düşünce 15 dakika kalır: dakikada 130 kelimeyle yaklaşık 1.950 kelime, en çok 15 slayt. Gövdeye kalan 10,5 dakika üç noktaya bölününce nokta başına 3,5 dakika düşer."
3. **Slayt bir arayüzdür (30 sn).** "Slayt konuşmacının notu değil, dinleyicinin ekranıdır: tek fikir, az kelime, kısa kod. Ortalamaya değil tek tek slaytlara bakın; tek bir kalabalık slayt salonu kaybettirir."
4. **Demo bir dağıtımdır (25 sn).** "Canlı demo bir üretim dağıtımıdır. Yedeği yoksa yapılmaz; ağ istiyorsa, süreye sığmıyorsa ya da üç kez prova edilmediyse canlı yapılmaz, kaydı gösterilir."
5. **Kapanış (20 sn).** "Süreyi sahnede değil hazırlıkta keşfedin. Ölçebildiğiniz kısım işin yarısıdır; diğer yarısı yüksek sesle provadır."
:::

::: anlat Sınır
Bu ders bir konuşmanın ölçülebilir kısımlarını anlatır: zaman, slayt yoğunluğu ve demo riski. Görevlerdeki eşikler (dakikada 130 kelime, slayt başına 40 kelime ve bir dakika, 12 satır kod, üç prova, %40 pay) yaygın tavsiyelere dayanan **başlangıç kurallarıdır**; konuşmacıya, dile, salona ve türe göre değişir. Bir atölye çalışması, bir ürün tanıtımı ve bir akademik sunum farklı dengeler ister. Bu denetimleri geçen bir konuşma iyi olmak zorunda değildir: içeriğin doğruluğu, hikâyenin akışı, dinleyiciye uygunluk ve konuşmacının sesi burada ölçülmez. Tersine, bazı çok iyi konuşmalar bu kuralları bilerek çiğner. Görev 3 riski üç etkene indirger; gerçekte donanım uyumsuzluğu, yetki sorunları ve veri gizliliği (ekranda görünen bir anahtar ya da kişisel veri) de demo riskleridir ve ayrıca denetlenmelidir. Konuşma becerisi okumakla değil, konuşup geri bildirim alarak gelişir; bu ders o pratiğin yerine geçmez. Bir güvenlik konuşmasında ek bir sorumluluk vardır: anlattığın tekniğin salondakilere ve üçüncü kişilere zarar verme olasılığını ve sorumlu bildirim durumunu konuşmadan önce değerlendirirsin (bkz. `ai-guvence-29`).

Kaynaklar: [Doumont 2009 - Trees, Maps, and Theorems: Effective Communication for Rational Minds](https://www.principiae.be/book/), [Simon Peyton Jones - How to give a great research talk](https://simon.peytonjones.org/great-research-talk/), [Mayer 2009 - Multimedia Learning](https://doi.org/10.1017/CBO9780511811678), [Patrick Winston - How to Speak (MIT OpenCourseWare)](https://ocw.mit.edu/courses/res-tll-005-how-to-speak-january-iap-2018/).
:::

::: dusun
Kendi konularından birini seç ve tek cümleni yaz: "Dinleyici salondan çıkarken şunu bilecek: ...". Sonra üç noktanı yaz. Hangisi için elinde bir **sayı**, hangisi için bir **örnek**, hangisi için bir **demo** var? Eksik olan hangisi ve onu hangi dersten alırsın?
:::

::: ozet
- Hazırlık tek bir cümleyle başlar; 20 dakikada bir ana fikir ve üç nokta anlatılır.
- Zaman bir bütçedir: soru-cevap süresi düşülür, yaklaşık %10 pay bırakılır ve hiçbir bölüm içeriğin %40'ını aşmaz.
- Slayt bir arayüzdür: tek fikir, az kelime, kısa kod; ortalamaya değil tek tek slaytlara bakılır.
- Yedeği olmayan demo yapılmaz; ağ gerektiren, süreye sığmayan ya da üç kez prova edilmemiş demo canlı yapılmaz.
- Ölçülebilen kısım konuşmanın yarısıdır; diğer yarısı yüksek sesle prova ve geri bildirimle gelir.
:::
