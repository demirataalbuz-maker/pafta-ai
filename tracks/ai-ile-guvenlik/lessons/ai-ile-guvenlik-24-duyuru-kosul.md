---
id: ai-ile-guvenlik-24
title: "Zafiyet Duyurusu · Sömürü Önkoşulu ve Yerel Yama"
summary: Bir duyurunun "etkilenir" iddiasını sürüm aralığı, erişilebilirlik ve özellik önkoşuluna ayır; sürümü sayısal karşılaştır ve envanteri KEV bilgisiyle acil / yüksek / planlı / etkilenmez kuyruklarına böl.
esleme: ai-ile-guvenlik-04, ai-ile-guvenlik-25, ai-saldiri-51, ai-guvence-29
timeout: 30
---

::: anlat 1. "Etkilenir" üç ayrı iddiadır
Bir güvenlik duyurusu "X ürününün 1.2.0 ile 1.3.0 arasındaki sürümleri etkilenir" dediğinde, bir model bunu envanterle eşleştirip "şu 40 sunucu açıkta" diyebilir. Bu cümle üç ayrı iddiayı birleştirir:

1. **Sürüm aralığı:** kurulu sürüm, açığın bulunduğu aralıkta mı? (Genellikle alt sınır dahil, düzeltmenin geldiği sürüm hariç.)
2. **Erişilebilirlik:** açık bileşene saldırganın erişebileceği bir yoldan ulaşılabiliyor mu (ör. ağa açık bir uç)?
3. **Özellik önkoşulu:** açık yalnız belirli bir özellik ya da yapılandırma açıkken mi tetikleniyor?

Sürümü aralıkta olan ama açık özelliği kapalı bir kurulum yamalanmalıdır, ama bu yarın sabahki planlı bakımda yapılabilir. Üç koşulu birden sağlayan kurulum ise sömürülebilirdir.

Öncelik için ikinci bir sinyal daha vardır: açığın sahada sömürüldüğünün bilinmesi. CISA'nın *Known Exploited Vulnerabilities* (KEV) kataloğu, sahada sömürüldüğü bilinen açıkların yetkili listesidir. CISA, kurumların bu kataloğu zafiyet yönetimindeki önceliklendirme çerçevelerine bir girdi olarak kullanmasını önerir.

> [!NOTE]
> Bu dersteki ürün (`ArchiveLab`), sürüm aralığı ve envanter **sentetiktir**; uydurma bir CVE numarası kullanılmaz ve aralık hiçbir gerçek ürüne uygulanmaz.
:::

::: anlat 2. Mekanizma: sürümler neden dizge olarak karşılaştırılmaz?
Sürüm dizgesi `"1.10.0"`, insan için `"1.2.0"`'dan büyüktür. Python'da dizge karşılaştırması ise karakter karakter yapılır: `'1.10.0' < '1.2.0'` ifadesi `True` döner, çünkü ikinci karakter grubunda `'1' < '2'`. Bir model ya da betik sürümleri dizge olarak karşılaştırırsa `1.10.0` sürümünü aralığın içinde sanabilir ya da `1.2.10`'u dışında bırakabilir.

Doğru yol sürümü sayılardan oluşan bir demete çevirmektir: `(1, 10, 0) > (1, 2, 0)`. Demetler de soldan sağa karşılaştırılır, ama her öğe bir sayı olduğu için `10 > 2` doğru çalışır. Biçim katı tutulur: tam üç nokta ayrımlı sayı. `v1.2.3`, `1.2.3-rc1`, `1.2` ya da boşluk içeren dizgeler hata verir; çünkü bu biçimlerin sıralaması duyurudan duyuruya değişir ve tahmin edilmemelidir.

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| Sürümleri dizge olarak karşılaştırmak | `'1.10.0' < '1.2.0'` | Sayı demeti |
| Üst sınırı dahil saymak | Düzeltmeyi getiren sürüm "etkilenir" görünür | `alt <= v < duzeltilen` |
| "Sürüm eşleşti = sömürülebilir" | Erişim ve özellik önkoşulu atlanır | Üç koşul birlikte |
| `rc`, `v` önekli sürümü tahminle ayrıştırmak | Sıralama kuralı belirsiz | Katı biçim; değilse hata |
| KEV bilgisini yok saymak | Sahada sömürülen açık kuyruğun sonunda kalır | Sömürülebilir + KEV → en üstte |
:::

::: tahmin Dizge mi, sayı mı?
Aralık `1.2.0 <= v < 1.3.0`. İki sürüm için dizge ve demet karşılaştırması ne der?

```python
for v in ('1.10.0', '1.2.10'):
    dizge = '1.2.0' <= v < '1.3.0'
    demet = (1, 2, 0) <= tuple(int(p) for p in v.split('.')) < (1, 3, 0)
    print(v, 'dizge:', dizge, '| demet:', demet)
```

???

```cikti
1.10.0 dizge: False | demet: False
1.2.10 dizge: True | demet: True
```
Bu ikisinde iki yöntem de aynı sonucu verdi; ama nedeni farklı. `'1.10.0' < '1.2.0'` olduğu için dizge onu aralığın **altında** sanıyor; demet ise **üstünde** buluyor. Aralık `1.0.0 <= v < 1.5.0` olsaydı dizge `1.10.0`'ı içeride sayardı. Doğru cevaba yanlış gerekçeyle ulaşan karşılaştırma, ilk farklı aralıkta kırılır.
:::

::: gorev 1 · Sürüm, erişim ve özellik önkoşulunu birlikte değerlendir
`etkilenir(surum, exposed, feature)` işlevini yaz.

- `surum` tam olarak `sayı.sayı.sayı` biçiminde bir `str` olmalı (her parça yalnız ASCII rakam, başta sıfır olabilir; önek, sonek, boşluk yok). Değilse `ValueError`.
- Sürümü sayı demetine çevir; `(1, 2, 0) <= v < (1, 3, 0)` aralığını sına.
- Dönüş: aralıktaysa **ve** `exposed is True` **ve** `feature is True` ise `True`; aksi halde `False`.

KUSURLU başlangıç sürümleri dizge olarak karşılaştırıyor, üst sınırı dahil sayıyor ve `exposed`/`feature` için doğruluk değerine bakıyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
Path('ornek.json').write_text('["1.3.0", 1, "evet"]', encoding='utf-8')
```

```starter
def etkilenir(surum, exposed, feature):
    return '1.2.0' <= surum <= '1.3.0' and bool(exposed) and bool(feature)

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(etkilenir(*_args))
```

```solution
import re

_SURUM = re.compile(r'[0-9]+\.[0-9]+\.[0-9]+')

def etkilenir(surum, exposed, feature):
    if not isinstance(surum, str) or _SURUM.fullmatch(surum) is None:
        raise ValueError('surum sayi.sayi.sayi olmali')
    v = tuple(int(p) for p in surum.split('.'))
    return (1, 2, 0) <= v < (1, 3, 0) and exposed is True and feature is True

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(etkilenir(*_args))
```

```test
need('etkilenir')
for _v in ('1.2.0', '1.2.9', '1.2.10', '1.2.99', '01.02.000'):
    eq(etkilenir(_v, True, True), True, f'aralık içinde ve önkoşullar tam: {_v}')
for _v in ('1.3.0', '1.10.0', '1.1.99', '0.9.9', '2.2.0', '1.30.0', '1.20.0', '1.3.1'):
    eq(etkilenir(_v, True, True), False, f'aralık dışı: {_v}')
eq(etkilenir('1.2.5', False, True), False, 'erişim yoksa sömürülemez')
eq(etkilenir('1.2.5', True, False), False, 'özellik kapalıysa sömürülemez')
eq(etkilenir('1.2.5', 1, True), False, 'exposed True olmalı, 1 değil')
eq(etkilenir('1.2.5', True, 'evet'), False, 'feature True olmalı')
eq(etkilenir('1.2.5', None, None), False, 'bilinmeyen önkoşul sömürülebilir sayılmaz')
for _bozuk in ('v1.2.3', '1.2.3-rc1', '1.2', '1.2.3.4', ' 1.2.3', '1.2.3 ', '1..3', '1.2.x', '', '١.٢.٣', None, 123, (1, 2, 3)):
    raises(ValueError, etkilenir, _bozuk, True, True, msg=f'bozuk sürüm ValueError: {_bozuk!r}')
```

```hint
`re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', surum)` biçimi sınar; `[0-9]` yalnız ASCII rakamlarını kabul eder (`\d` başka yazı sistemlerinin rakamlarını da kabul ederdi). Sonra `tuple(int(p) for p in surum.split('.'))` ile sayı demetine çevir.
```
:::

::: gorev 2 · Envanteri KEV bilgisiyle kuyruklara ayır
`yama_kuyrugu(envanter, kev)` işlevini yaz.

- `kev` bir `bool`: duyurudaki açık CISA KEV kataloğunda mı? Değilse `ValueError`.
- `envanter` bir `list`; her kayıt `{'ad': str, 'surum': str, 'exposed': bool, 'feature': bool}`. `ad` boş olmayan ve benzersiz; `surum` görev 1'deki biçimde; `exposed` ve `feature` tam `bool`. Değilse `ValueError`.
- Sınıflandırma (aralık görev 1'deki gibi `1.2.0 <= v < 1.3.0`):
  - aralık dışı → `'etkilenmez'`;
  - aralıkta, `exposed` ve `feature` ikisi de `True`: `kev` ise `'acil'`, değilse `'yuksek'`;
  - aralıkta ama önkoşullardan biri eksik → `'planli'`.
- Dönüş: `{'acil': [...], 'yuksek': [...], 'planli': [...], 'etkilenmez': [...]}`; her liste ad sırasına göre (alfabetik).

KUSURLU başlangıç sürüm aralığındaki her kurulumu acil sayıyor ve önkoşulsuz kurulumları kuyruktan düşürüyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def yama_kuyrugu(envanter, kev):
    sonuc = {'acil': [], 'yuksek': [], 'planli': [], 'etkilenmez': []}
    for k in envanter:
        v = tuple(int(p) for p in k['surum'].split('.'))
        if (1, 2, 0) <= v < (1, 3, 0):
            sonuc['acil'].append(k['ad'])
        else:
            sonuc['etkilenmez'].append(k['ad'])
    return sonuc
```

```solution
import re

_SURUM = re.compile(r'[0-9]+\.[0-9]+\.[0-9]+')

def yama_kuyrugu(envanter, kev):
    if type(kev) is not bool or not isinstance(envanter, list):
        raise ValueError('kev bool, envanter list olmali')
    sonuc = {'acil': [], 'yuksek': [], 'planli': [], 'etkilenmez': []}
    gorulen = set()
    for k in envanter:
        if (not isinstance(k, dict) or not isinstance(k.get('ad'), str) or not k['ad'].strip()
                or not isinstance(k.get('surum'), str) or _SURUM.fullmatch(k['surum']) is None
                or type(k.get('exposed')) is not bool or type(k.get('feature')) is not bool):
            raise ValueError('bozuk envanter kaydi')
        if k['ad'] in gorulen:
            raise ValueError('yinelenen ad')
        gorulen.add(k['ad'])
        v = tuple(int(p) for p in k['surum'].split('.'))
        if not (1, 2, 0) <= v < (1, 3, 0):
            kuyruk = 'etkilenmez'
        elif k['exposed'] and k['feature']:
            kuyruk = 'acil' if kev else 'yuksek'
        else:
            kuyruk = 'planli'
        sonuc[kuyruk].append(k['ad'])
    return {a: sorted(b) for a, b in sonuc.items()}
```

```test
need('yama_kuyrugu')
import copy
def _k(ad, s, e, f):
    return {'ad': ad, 'surum': s, 'exposed': e, 'feature': f}
_env = [
    _k('web-2', '1.2.4', True, True),
    _k('web-1', '1.2.10', True, True),
    _k('ic-arsiv', '1.2.4', False, True),
    _k('test', '1.2.0', True, False),
    _k('yeni', '1.3.0', True, True),
    _k('eski', '1.10.0', True, True),
    _k('cok-eski', '1.1.9', True, True),
]
_yedek = copy.deepcopy(_env)
eq(yama_kuyrugu(_env, True), {
    'acil': ['web-1', 'web-2'],
    'yuksek': [],
    'planli': ['ic-arsiv', 'test'],
    'etkilenmez': ['cok-eski', 'eski', 'yeni'],
}, 'KEV\'deki açık: sömürülebilirler acil; önkoşulu eksikler planlı; 1.10.0 aralık dışı')
eq(yama_kuyrugu(_env, False)['yuksek'], ['web-1', 'web-2'], 'KEV dışı açık: sömürülebilirler yüksek')
eq(yama_kuyrugu(_env, False)['acil'], [], 'KEV dışıysa acil kuyruk boş')
eq(_env, _yedek, 'girdi değişmemeli')
eq(yama_kuyrugu([], True), {'acil': [], 'yuksek': [], 'planli': [], 'etkilenmez': []}, 'boş envanter')

for _kev in (1, 'evet', None):
    raises(ValueError, yama_kuyrugu, _env, _kev, msg=f'bool olmayan kev ValueError: {_kev!r}')
raises(ValueError, yama_kuyrugu, tuple(_env), True, msg='liste olmayan envanter ValueError')
for _bozuk in (
    ['web-1'],
    [{'surum': '1.2.4', 'exposed': True, 'feature': True}],
    [_k('', '1.2.4', True, True)],
    [_k('  ', '1.2.4', True, True)],
    [_k(5, '1.2.4', True, True)],
    [_k('a', 'v1.2.4', True, True)],
    [_k('a', '1.2', True, True)],
    [_k('a', None, True, True)],
    [_k('a', '1.2.4', 1, True)],
    [_k('a', '1.2.4', True, 'evet')],
    [_k('a', '1.2.4', True, True), _k('a', '1.0.0', False, False)],
):
    raises(ValueError, yama_kuyrugu, _bozuk, True, msg=f'bozuk kayıt ValueError: {_bozuk!r}')
```

```hint
Her kayıt için önce aralığı, sonra önkoşulları, en son KEV bilgisini sor. Kuyrukları doldurduktan sonra her listeyi `sorted` ile sırala.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Üç iddia (25 sn).** "'Etkilenir' cümlesi sürüm aralığı, erişilebilirlik ve özellik önkoşulunu birleştiriyor. Model bunları tek iddia gibi raporlayınca 40 sunucu açıkta görünüyor; çoğu aslında planlı yama."
2. **Sürüm tuzağı (30 sn).** "Dizge karşılaştırmasında 1.10.0, 1.2.0'dan küçük çıkıyor. Sürümü sayı demetine çevirdik ve biçimi katı tuttuk: v öneki, rc soneki, iki parçalı sürüm hata veriyor."
3. **Sınırlar (20 sn).** "Alt sınır dahil, düzeltmenin geldiği 1.3.0 hariç. Testte 1.2.10 içeride, 1.10.0 ve 1.3.0 dışarıda."
4. **Kuyruk (30 sn).** "Envanteri dörde böldük. CISA KEV'i önceliklendirme girdisi olarak kullanmayı öneriyor: sömürülebilir ve KEV'deyse acil, değilse yüksek; önkoşulu eksikse planlı."
5. **Sınır (15 sn).** "Ürün ve aralık sentetik; gerçek duyurularda aralıklar çoklu dallarda ve geri taşınmış (backport) yamalarla gelir."
:::

::: anlat Sınır ve kaynak
Bu ders tek bir sürüm aralığı ve katı üç parçalı sürüm biçimiyle çalışır. Gerçek duyurularda birden çok etkilenen dal (ör. 1.2.x ve 2.0.x), dağıtımların geri taşınmış yamaları (paket sürümü aralıkta görünür ama düzeltme uygulanmıştır) ve semantik sürümlemenin ön sürüm kuralları vardır; bunlar burada yoktur. "Erişilebilir" ve "özellik açık" bilgisi envanterden gelen sentetik bayraklardır; gerçekte bunlar ağ ve yapılandırma taramasıyla doğrulanır. KEV bilgisi önceliği değiştirir ama KEV'de olmayan bir açığın sömürülmediğini kanıtlamaz.

- Birincil kaynak: [CISA — Known Exploited Vulnerabilities Catalog](https://www.cisa.gov/known-exploited-vulnerabilities-catalog) (sahada sömürüldüğü bilinen açıkların yetkili listesi; kataloğun zafiyet yönetimi önceliklendirmesine girdi olarak kullanılması önerisi). Doğrulama tarihi: 11 Kasım 2026.
:::

::: dusun
Bir dağıtım, paket sürümünü `1.2.4-3ubuntu1` olarak gösteriyor ve açığın düzeltmesini bu pakete geri taşımış. Görev 1'in katı biçim kuralı bu dizgeyi reddeder. Reddetmek mi, yoksa `1.2.4` gibi kırpıp aralıkta saymak mı daha güvenli? İki yanlışın bedelini karşılaştır.
:::

::: ozet
- "Etkilenir" iddiası sürüm aralığı, erişilebilirlik ve özellik önkoşulu olarak üçe ayrılır.
- Sürümler dizge olarak değil, sayı demeti olarak karşılaştırılır; biçim katı tutulur.
- Aralığın alt sınırı dahil, düzeltme sürümü hariçtir.
- Sömürülebilir kurulumlar KEV bilgisine göre acil ya da yüksek; önkoşulu eksikler planlı kuyruğa girer.
:::
