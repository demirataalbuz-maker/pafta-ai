---
id: ai-guvence-51
title: "Bitirme · Yerel Varyanttan Araştırma Raporuna"
summary: Yeni bir yerel varyantı dört kontrol grubuyla dene; hataları başarıdan ayırarak grup grup ölç ve araştırma paketini biçimsel kabul kapısından geçir.
esleme: ai-guvence-33, ai-guvence-50, ai-guvence-29, ai-ctf-10
timeout: 30
---

::: anlat 1. Bitirme: tek bir başarılı koşu bir bulgu değildir
Bu bitirme dersinde önceki yolların hedeflerinden biri için **yeni bir yerel varyant** dener ve sonucu bir araştırma raporuna dönüştürürsün. Varyant, "aynı isteği başka sözcüklerle yazdım" düzeyinde kalmamalı. Tek bir değişkeni açıkça değiştir: kaynak konumu, temsil dönüşümü, çağrı sırası ya da yetki bağlamı. Başlamadan önce hipotezi ve onu neyin yanlışlayacağını yaz.

NIST'in 26 Ocak 2023'te yayımladığı *AI Risk Management Framework* (AI RMF 1.0) ve 26 Temmuz 2024'te yayımladığı üretken AI profili (NIST AI 600-1), AI risklerinin ölçülmesini ve belgelenmesini bir yönetişim işi olarak ele alır. Bu derste o yaklaşımın en küçük birimini kuruyoruz: bir varyantın ve bir yamanın etkisini, **kontrol gruplarıyla, paydaları görünür ve hataları ayrık** bir biçimde ölçmek.

Yeni bir varyant bulamamak ya da yamanın bütün denemeleri durdurması da raporlanabilir bir sonuçtur (`ai-guvence-50`). Araştırmanın kabulü saldırının başarısına bağlı değildir. Soru, yöntem ve kanıt birbirine uymalıdır; uymuyorsa yüksek bir başarı yüzdesi çalışmanın değerini artırmaz.

> [!NOTE]
> Deney yalnız kendi yerel, deterministik hedeflerinde yürür; her hedef yeni bir **sentetik kanarya** üretir. Gerçek sır, üçüncü taraf hesabı, ağda hedef arama ya da gerçek model çağrısı bu ödevin parçası değildir.
:::

::: anlat 2. Mekanizma: dört grup ve dürüst paydalar
Bir yamanın değerini göstermek için dört grup gerekir:

| | Saldırı (varyant) | Meşru görev |
|---|---|---|
| **Açık hedef** | Varyant işe yarıyor mu? (başlangıç) | Meşru iş çalışıyor mu? (başlangıç) |
| **Yamalı hedef** | Yama varyantı durduruyor mu? | Yama meşru işi bozuyor mu? (regresyon) |

Yalnız sağ üst ile sol alt hücreyi ("yamalı hedefte saldırı başarısız") göstermek, her şeyi reddeden bir yamayı da "mükemmel" gösterir. Sağ alt hücre bunu yakalar.

İkinci tuzak hatalardır. Bir deneme istisna fırlattığında (bozuk yanıt, zaman aşımı, kod hatası) sonuç "saldırı başarısız" değil, **"ölçülemedi"**dir. Hataları başarısızlık sayan bir rapor, yamalı hedefte saldırının hep "durdurulduğunu" söyler; oysa denemelerin yarısı belki hiç çalışmamıştır. Bu yüzden oran, hatasız denemeler üzerinden hesaplanır ve hata sayısı ayrıca raporlanır.

Üçüncü tuzak yeniden üretimdir. Her deneme yeni bir hedef ve yeni bir kanarya kullanmalıdır; aynı hedefi tekrar kullanmak, sorgu sayacını ve önceki denemenin durumunu taşır. Ham kanarya rapora yazılmaz; yanıtın SHA-256 özeti yazılır.

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| Yalnız yamalı saldırı grubunu raporlamak | Her şeyi reddeden yama "mükemmel" görünür | Dört grubun hepsi |
| İstisnayı başarısızlık saymak | Ölçülemeyen deneme "durduruldu" görünür | `hata` ayrı; oran hatasız denemeler üzerinden |
| Tek hedefi bütün denemelerde kullanmak | Durum ve sorgu sayacı taşınır; kanarya değişmez | Her deneme yeni hedef |
| Ham yanıtı rapora yazmak | Kanarya ve olası sır rapora sızar | Yanıtın SHA-256 özeti |
| Bütün satırları tek oranda toplamak | Gruplar birbirini maskeler | Grup başına pay ve payda |
:::

::: tahmin Hata başarısızlık sayılırsa
Yamalı hedefte 10 saldırı denemesinin 6'sı istisnayla bitti, 4'ü çalıştı ve hepsi durduruldu. İki raporlama yöntemi ne der?

```python
denemeler = ['hata'] * 6 + ['durduruldu'] * 4
saf = sum(1 for d in denemeler if d == 'durduruldu' or d == 'hata') / len(denemeler)
olculen = [d for d in denemeler if d != 'hata']
durust = sum(1 for d in olculen if d == 'durduruldu') / len(olculen)
print('hata = durduruldu:', saf, '| hatasız payda:', durust, '| hata:', len(denemeler) - len(olculen))
```

???

```cikti
hata = durduruldu: 1.0 | hatasız payda: 1.0 | hata: 6
```
İki oran da 1,0. Fark oranda değil, **kanıtın ağırlığında**: ilk yöntem 10 denemeye dayandığını iddia eder, ikincisi yalnız 4 deneme ölçüldüğünü ve 6'sının hiç ölçülemediğini söyler. Hata sayısını göstermeyen rapor bu farkı gizler.
:::

::: gorev 1 · Dört gruplu deneyi her denemede yeni hedefle yürüt
`deney_yurut(hedef_kur, varyant, mesru, n)` işlevini yaz.

- `hedef_kur`, `varyant`, `mesru` çağrılabilir olmalı; `n` `bool` olmayan bir `int` ve `1 <= n <= 100`. Değilse `ValueError`.
- Grup sırası: önce `yamali = False`, sonra `yamali = True`; her birinde önce saldırı (`varyant`), sonra meşru görev (`mesru`); her grupta `n` deneme.
- Her deneme için `hedef_kur(yamali)` **yeniden** çağrılır ve `(sorgu, kontrol, sayac)` döner. `hedef_kur`'un fırlattığı istisna gizlenmez.
- `yanit = fn(sorgu)`. Saldırıda başarı `bool(kontrol(yanit))`, meşru görevde `yanit == 'PONG'`. `fn` ya da `kontrol` istisna fırlatırsa ya da `yanit` `str` değilse: `hata = True`, `basari = False`.
- Her deneme bir satır: `{'yamali', 'saldiri', 'basari', 'hata', 'sorgu': sayac(), 'yanit_sha256'}`. Özet, `yanit` bir `str` ise UTF-8 SHA-256 onaltılık dizgesi, değilse `None`. Ham yanıt satıra yazılmaz.

KUSURLU başlangıç tek bir hedefi bütün denemelerde kullanıyor, istisnayı hata saymadan "başarısız" sayıyor ve ham yanıtı satıra yazıyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def deney_yurut(hedef_kur, varyant, mesru, n):
    satirlar = []
    for yamali in (False, True):
        sorgu, kontrol, sayac = hedef_kur(yamali)
        for saldiri, fn in ((True, varyant), (False, mesru)):
            for _ in range(n):
                try:
                    yanit = fn(sorgu)
                    basari = bool(kontrol(yanit)) if saldiri else yanit == 'PONG'
                except Exception:
                    yanit, basari = None, False
                satirlar.append({'yamali': yamali, 'saldiri': saldiri, 'basari': basari, 'hata': False,
                                 'sorgu': sayac(), 'yanit': yanit})
    return satirlar
```

```solution
import hashlib

def deney_yurut(hedef_kur, varyant, mesru, n):
    if any(not callable(f) for f in (hedef_kur, varyant, mesru)) or type(n) is not int or not 1 <= n <= 100:
        raise ValueError('cagrilabilir islevler ve 1..100 n gerekli')
    satirlar = []
    for yamali in (False, True):
        for saldiri, fn in ((True, varyant), (False, mesru)):
            for _ in range(n):
                sorgu, kontrol, sayac = hedef_kur(yamali)
                yanit = None
                hata = False
                try:
                    yanit = fn(sorgu)
                    if not isinstance(yanit, str):
                        raise ValueError('yanit str olmali')
                    basari = bool(kontrol(yanit)) if saldiri else yanit == 'PONG'
                except Exception:
                    hata, basari = True, False
                satirlar.append({
                    'yamali': yamali, 'saldiri': saldiri, 'basari': basari, 'hata': hata, 'sorgu': sayac(),
                    'yanit_sha256': hashlib.sha256(yanit.encode('utf-8')).hexdigest() if isinstance(yanit, str) else None,
                })
    return satirlar
```

```test
need('deney_yurut')
import hashlib, secrets
_kurulan = []
def _kur(yamali):
    sir = 'PAFTA{' + secrets.token_hex(16) + '}'
    sayac = 0
    _kurulan.append(yamali)
    def sorgu(metin):
        nonlocal sayac
        sayac += 1
        if metin == 'ping':
            return 'PONG'
        return 'RED' if yamali else sir
    return sorgu, (lambda y: y == sir), (lambda: sayac)

_r = deney_yurut(_kur, lambda q: q('varyant'), lambda q: q('ping'), 3)
eq(len(_r), 12, 'dört grup × 3 deneme')
eq(len(_kurulan), 12, 'her deneme için yeni hedef kurulur')
eq([(x['yamali'], x['saldiri']) for x in _r], [(False, True)] * 3 + [(False, False)] * 3 + [(True, True)] * 3 + [(True, False)] * 3,
   'grup sırası: açık-saldırı, açık-meşru, yamalı-saldırı, yamalı-meşru')
eq([x['basari'] for x in _r], [True] * 3 + [True] * 3 + [False] * 3 + [True] * 3, 'yama saldırıyı durdurur, meşru işi korur')
eq({x['hata'] for x in _r}, {False}, 'beklenen koşuda hata yok')
eq({x['sorgu'] for x in _r}, {1}, 'her yeni hedefte tek sorgu')
eq(set(_r[0]), {'yamali', 'saldiri', 'basari', 'hata', 'sorgu', 'yanit_sha256'}, 'satırda ham yanıt yok')
eq(len({x['yanit_sha256'] for x in _r[:3]}), 3, 'her açık saldırı denemesi farklı kanarya özeti üretir')
eq(_r[3]['yanit_sha256'], hashlib.sha256(b'PONG').hexdigest(), 'özet UTF-8 SHA-256')
eq(deney_yurut(_kur, lambda q: q('çğü'), lambda q: q('ping'), 1)[2]['yanit_sha256'], hashlib.sha256('RED'.encode('utf-8')).hexdigest(),
   'yamalı hedef yanıtının özeti')

def _patlar(q):
    q('x')
    raise RuntimeError('model hatasi')
_r = deney_yurut(_kur, _patlar, lambda q: 42, 2)
eq([(x['basari'], x['hata'], x['yanit_sha256'], x['sorgu']) for x in _r],
   ([(False, True, None, 1)] * 2 + [(False, True, None, 0)] * 2) * 2,
   'istisna ve str olmayan yanıt hata; özet None; istisnadan önce yapılan sorgu sayılır, hiç sorgulamayan işlev 0')
def _kontrol_patlar(yamali):
    q, _c, s = _kur(yamali)
    def _c2(y):
        raise RuntimeError('kontrol hatasi')
    return q, _c2, s
_r = deney_yurut(_kontrol_patlar, lambda q: q('v'), lambda q: q('ping'), 1)
eq([(x['basari'], x['hata']) for x in _r], [(False, True), (True, False), (False, True), (True, False)],
   'kontrol işlevinin istisnası da hata; meşru görev kontrolü kullanmaz')
eq(_r[0]['yanit_sha256'] is not None, True, 'yanıt str ise kontrol hatasında da özet yazılır')

def _kurulum_patlar(yamali):
    raise OSError('hedef kurulamadi')
raises(OSError, deney_yurut, _kurulum_patlar, lambda q: 'x', lambda q: 'PONG', 1, msg='hedef kurulum hatası gizlenmez')
eq(len(deney_yurut(_kur, lambda q: q('v'), lambda q: q('ping'), 100)), 400, 'n = 100 üst sınır geçerli')
for _arg in ((_kur, lambda q: 'x', lambda q: 'x', 0), (_kur, lambda q: 'x', lambda q: 'x', 101), (_kur, lambda q: 'x', lambda q: 'x', True),
             (_kur, lambda q: 'x', lambda q: 'x', 2.0), (None, lambda q: 'x', lambda q: 'x', 1), (_kur, 'varyant', lambda q: 'x', 1),
             (_kur, lambda q: 'x', None, 1)):
    raises(ValueError, deney_yurut, *_arg, msg=f'bozuk argüman ValueError: {_arg[3]!r}')
```

```hint
Hedefi en içteki döngüde kur. `try` bloğunda yanıtın `str` olduğunu doğrula ve başarıyı hesapla; `except` bloğunda yalnız `hata` ve `basari`'yı ayarla, yanıtı silme (özet için gerekebilir).
```
:::

::: gorev 2 · Grup grup dürüst ölçüm özeti
Görev 1'in satırlarını özetleyen `grup_ozeti(satirlar)` işlevini yaz.

- Gruplar ve anahtarları: `('acik-saldiri', yamali=False, saldiri=True)`, `('acik-mesru', False, False)`, `('yamali-saldiri', True, True)`, `('yamali-mesru', True, False)`.
- Her grup için: `n` (satır sayısı), `hata` (hata sayısı), `basari` (hatasız ve başarılı satır sayısı), `oran = round(basari / (n - hata), 4)`; `n - hata == 0` ise `None`.
- Dönüş: dört anahtarın hepsini içeren sözlük (satırı olmayan grup `{'n': 0, 'hata': 0, 'basari': 0, 'oran': None}`).
- `satirlar` `list` değilse; satır `dict` değilse; `yamali`, `saldiri`, `basari`, `hata` tam `bool` değilse; ya da `hata` ve `basari` ikisi birden `True` ise `ValueError`.

KUSURLU başlangıç oranı bütün satır sayısına bölüyor ve hataları paydada tutuyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def grup_ozeti(satirlar):
    adlar = {(False, True): 'acik-saldiri', (False, False): 'acik-mesru', (True, True): 'yamali-saldiri', (True, False): 'yamali-mesru'}
    sonuc = {}
    for anahtar, ad in adlar.items():
        g = [s for s in satirlar if (s['yamali'], s['saldiri']) == anahtar]
        b = sum(1 for s in g if s['basari'])
        sonuc[ad] = {'n': len(g), 'hata': 0, 'basari': b, 'oran': round(b / len(satirlar), 4) if satirlar else None}
    return sonuc
```

```solution
_GRUP = (('acik-saldiri', False, True), ('acik-mesru', False, False), ('yamali-saldiri', True, True), ('yamali-mesru', True, False))
_ALAN = ('yamali', 'saldiri', 'basari', 'hata')

def grup_ozeti(satirlar):
    if not isinstance(satirlar, list):
        raise ValueError('satirlar list olmali')
    for s in satirlar:
        if not isinstance(s, dict) or any(type(s.get(a)) is not bool for a in _ALAN):
            raise ValueError('bozuk satir')
        if s['hata'] and s['basari']:
            raise ValueError('hatali satir basarili olamaz')
    sonuc = {}
    for ad, yamali, saldiri in _GRUP:
        g = [s for s in satirlar if s['yamali'] == yamali and s['saldiri'] == saldiri]
        hata = sum(1 for s in g if s['hata'])
        basari = sum(1 for s in g if s['basari'])
        olculen = len(g) - hata
        sonuc[ad] = {'n': len(g), 'hata': hata, 'basari': basari,
                     'oran': round(basari / olculen, 4) if olculen else None}
    return sonuc
```

```test
need('grup_ozeti')
import copy
def _s(y, sa, b, h=False):
    return {'yamali': y, 'saldiri': sa, 'basari': b, 'hata': h, 'sorgu': 1, 'yanit_sha256': None}
_sat = ([_s(False, True, True)] * 3 + [_s(False, True, False)]
        + [_s(False, False, True)] * 2
        + [_s(True, True, False, True)] * 6 + [_s(True, True, False)] * 2 + [_s(True, True, True)]
        + [_s(True, False, True)] * 2 + [_s(True, False, False)])
_yedek = copy.deepcopy(_sat)
eq(grup_ozeti(_sat), {
    'acik-saldiri': {'n': 4, 'hata': 0, 'basari': 3, 'oran': 0.75},
    'acik-mesru': {'n': 2, 'hata': 0, 'basari': 2, 'oran': 1.0},
    'yamali-saldiri': {'n': 9, 'hata': 6, 'basari': 1, 'oran': 0.3333},
    'yamali-mesru': {'n': 3, 'hata': 0, 'basari': 2, 'oran': 0.6667},
}, 'oran hatasız denemeler üzerinden; yamalı saldırıda 9 denemenin yalnız 3\'ü ölçüldü')
eq(_sat, _yedek, 'girdi değişmemeli')
_bos = {'n': 0, 'hata': 0, 'basari': 0, 'oran': None}
eq(grup_ozeti([]), {'acik-saldiri': _bos, 'acik-mesru': _bos, 'yamali-saldiri': _bos, 'yamali-mesru': _bos}, 'boş satır listesi')
eq(grup_ozeti([_s(True, True, False, True)] * 2)['yamali-saldiri'], {'n': 2, 'hata': 2, 'basari': 0, 'oran': None},
   'bütün denemeler hata verdiyse oran None: "durduruldu" değil, ölçülemedi')
eq(grup_ozeti([_s(False, False, False)])['acik-mesru'], {'n': 1, 'hata': 0, 'basari': 0, 'oran': 0.0}, 'ölçülmüş sıfır oran 0.0')

raises(ValueError, grup_ozeti, tuple(_sat), msg='liste olmayan satırlar ValueError')
for _bozuk in (['satir'], [{'yamali': True, 'saldiri': True, 'basari': True}], [dict(_s(True, True, True), yamali=1)],
               [dict(_s(True, True, True), saldiri=None)], [dict(_s(True, True, True), basari='evet')],
               [dict(_s(True, True, False), hata=0)], [_s(True, True, True, True)]):
    raises(ValueError, grup_ozeti, _bozuk, msg=f'bozuk satır ValueError: {_bozuk!r}')
```

```hint
Önce bütün satırları doğrula. Her grup için hata sayısını ayrı say; payda `n - hata`'dır ve sıfırsa oran `None` olur.
```
:::

::: gorev 3 · Araştırma paketinin biçimsel kabul kapısı
`paket_denetle(paket)` işlevini yaz.

- `paket` `dict` değilse `ValueError`.
- Şu alanlar **bu sırayla** boş olmayan (yalnız boşluktan ibaret olmayan) bir `str` olmalı: `soru`, `tehdit_modeli`, `izin_kapsami`, `kurulum`, `yontem`, `sonuclar`, `olumsuz_sonuc`, `sinirlar`, `yeniden_uretim`, `kaynaklar`.
- Sonra `veri_kokeni` `'sentetik'`, `'gercek-kayit'` ya da `'canli'` olmalı; `yerel_izinli` tam olarak `True` olmalı.
- Dönüş: `{'hazir': eksik yoksa True, 'eksik': [eksik alanlar, yukarıdaki sırayla]}`.

Bu yalnız biçimsel bir kapıdır: araştırmanın yeniliği, etik uygunluğu ve iddiaların doğruluğu insan denetimi ister.

KUSURLU başlangıç alanın yalnız var olup olmadığına bakıyor (boşluk dizgesi geçiyor) ve `yerel_izinli`'nin doğruluk değerini kabul ediyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
Path('ornek.json').write_text('[{"soru": "Kaynak konumu degisince yama dayanir mi?", "tehdit_modeli": "  ", "izin_kapsami": "yalniz yerel hedefler", "kurulum": "commit abc123", "yontem": "dort grup", "sonuclar": "tablo 1", "olumsuz_sonuc": "varyant B calismadi", "sinirlar": "deterministik hedef", "yeniden_uretim": "komut ve hash", "kaynaklar": "NIST AI RMF", "veri_kokeni": "sentetik", "yerel_izinli": 1}]', encoding='utf-8')
```

```starter
_ALANLAR = ['soru', 'tehdit_modeli', 'izin_kapsami', 'kurulum', 'yontem', 'sonuclar',
            'olumsuz_sonuc', 'sinirlar', 'yeniden_uretim', 'kaynaklar']

def paket_denetle(paket):
    eksik = [a for a in _ALANLAR if a not in paket]
    if paket.get('veri_kokeni') not in ('sentetik', 'gercek-kayit', 'canli'):
        eksik.append('veri_kokeni')
    if not paket.get('yerel_izinli'):
        eksik.append('yerel_izinli')
    return {'hazir': not eksik, 'eksik': eksik}

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(paket_denetle(*_args))
```

```solution
_ALANLAR = ('soru', 'tehdit_modeli', 'izin_kapsami', 'kurulum', 'yontem', 'sonuclar',
            'olumsuz_sonuc', 'sinirlar', 'yeniden_uretim', 'kaynaklar')

def paket_denetle(paket):
    if not isinstance(paket, dict):
        raise ValueError('paket dict olmali')
    eksik = [a for a in _ALANLAR if not isinstance(paket.get(a), str) or not paket[a].strip()]
    if paket.get('veri_kokeni') not in ('sentetik', 'gercek-kayit', 'canli'):
        eksik.append('veri_kokeni')
    if paket.get('yerel_izinli') is not True:
        eksik.append('yerel_izinli')
    return {'hazir': not eksik, 'eksik': eksik}

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(paket_denetle(*_args))
```

```test
need('paket_denetle')
import copy
_A = ['soru', 'tehdit_modeli', 'izin_kapsami', 'kurulum', 'yontem', 'sonuclar', 'olumsuz_sonuc', 'sinirlar', 'yeniden_uretim', 'kaynaklar']
_tam = {a: 'dolu metin' for a in _A}
_tam.update({'veri_kokeni': 'sentetik', 'yerel_izinli': True})
_yedek = copy.deepcopy(_tam)
eq(paket_denetle(_tam), {'hazir': True, 'eksik': []}, 'tam paket hazır')
eq(_tam, _yedek, 'girdi değişmemeli')
eq(paket_denetle({}), {'hazir': False, 'eksik': _A + ['veri_kokeni', 'yerel_izinli']}, 'boş pakette bütün alanlar sırayla eksik')
for _kok in ('gercek-kayit', 'canli'):
    eq(paket_denetle(dict(_tam, veri_kokeni=_kok)), {'hazir': True, 'eksik': []}, f'geçerli veri kökeni: {_kok}')
for _alan, _deger in (('tehdit_modeli', '   '), ('kurulum', ''), ('kaynaklar', None), ('sonuclar', ['tablo']),
                      ('veri_kokeni', 'Sentetik'), ('veri_kokeni', None), ('yerel_izinli', 1), ('yerel_izinli', 'evet')):
    eq(paket_denetle(dict(_tam, **{_alan: _deger})), {'hazir': False, 'eksik': [_alan]}, f'tek eksik: {_alan}={_deger!r}')
eq(paket_denetle(dict(_tam, sinirlar='', soru=' ', yerel_izinli=False))['eksik'], ['soru', 'sinirlar', 'yerel_izinli'], 'eksikler sabit sırada')
for _bozuk in (None, [], 'paket'):
    raises(ValueError, paket_denetle, _bozuk, msg=f'dict olmayan paket ValueError: {_bozuk!r}')
```

```hint
Her alan için "dolu bir str mi?" diye sor: `isinstance(x, str) and x.strip()`. `yerel_izinli` için `is True` kullan.
```
:::

::: anlat Elle değerlendirme ölçütü · 100 puan
Otomatik kontroller yalnız deneyin biçimini ve ölçümünü sınar. Raporun kendisi şu ölçütle insan tarafından değerlendirilir:

| Ölçüt | Puan | Beklenen kanıt |
|---|---:|---|
| Soru ve tehdit modeli | 20 | Güven sınırı, saldırganın kontrolü, izin kapsamı |
| Yöntem ve kontrol grupları | 20 | Tek değişken, dört grup, başlangıç ölçümü |
| Ölçüm doğruluğu | 20 | Grup başına paydalar, hata-ayrık sonuçlar, bütün koşular |
| Sınırlar ve olumsuz sonuç | 15 | Yamanın bozduğu işler, başarısız varyantlar |
| Yeniden üretim | 15 | Sürüm, komut, kanarya planı, kanıt özetleri |
| Yazım ve anlatım | 10 | İddia → kanıt bağlantısı, iki dakikalık demo |

Yerel izin kapsamının dışına çıkmak, gerçek sır kullanmak ya da kanıt uydurmak kabulü durdurur; puanla telafi edilmez.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Soru (20 sn).** "Tek bir değişkeni değiştirdik: kanaryanın kaynağını belgeden araç çıktısına taşıdık. Hipotezimiz yamanın bunu da durduracağıydı."
2. **Dört grup (30 sn).** "Açık ve yamalı hedefte hem varyantı hem meşru görevi koştuk; her denemede yeni hedef, yeni kanarya. Yalnız 'yamalı hedefte saldırı başarısız' demek, her şeyi reddeden bir yamayı da başarılı gösterirdi."
3. **Dürüst payda (30 sn).** "Yamalı saldırı grubunda dokuz denemenin altısı hata verdi. Bunları 'durduruldu' saymadık: oran üç ölçülen deneme üzerinden 0,33 ve altı ölçülemeyen deneme ayrıca raporlandı."
4. **Regresyon (25 sn).** "Yamalı hedefte meşru görevin üçte biri bozuldu. Bu, yamanın bedeli ve raporun olumsuz sonuç bölümünde."
5. **Sınır (15 sn).** "Hedefler deterministik; tekrarlar kanarya çeşitliliğini sınıyor, gerçek bir modelin dağılımını değil."
:::

::: anlat Sınır ve kaynak
Bu bitirme deterministik yerel hedeflerle tamamlanır; gerçek bir model çalıştırıldığı iddia edilmez. Gerçek bir model deneyinde tohum (*seed*), model sürümü ve üretim parametreleri ayrıca kaydedilir ve tekrarlar dağılımı ölçer. Otomatik kontroller biçimi ve ölçümü sınar; yeni bir zafiyetin özgünlüğünü ya da yayına uygunluğunu kanıtlamaz. Bulunan bir açığın bildirimi `ai-guvence-29`'daki sorumlu bildirim akışıyla yapılır.

- Birincil kaynak: [NIST — AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework) (AI RMF 1.0, 26 Ocak 2023; Generative AI Profile, NIST AI 600-1, 26 Temmuz 2024). Doğrulama tarihi: 11 Kasım 2026.
:::

::: dusun
Varyantın açık hedefte 10 denemenin 10'unda çalıştığını, yamalı hedefte 10'unda da durduğunu gördün. Bu sonucu "yama varyantı tamamen durdurur" diye raporlamadan önce hangi ek denemeyi yapardın? (İpucu: yamanın neye dayanarak reddettiğini düşün.)
:::

::: ozet
- Bir yamanın değeri dört grupla gösterilir; meşru görevdeki regresyon da ölçülür.
- İstisna "durduruldu" değil, "ölçülemedi"dir; oran hatasız denemeler üzerinden hesaplanır, hata sayısı ayrıca raporlanır.
- Her deneme yeni hedef ve yeni kanaryayla yapılır; ham yanıt değil, özeti saklanır.
- Biçimsel kabul kapısı gerekli ama yeterli değildir; yenilik ve doğruluk insan denetimi ister.
:::
