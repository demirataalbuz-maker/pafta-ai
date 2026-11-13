---
id: ai-olay-13
title: "LangChain Hesaplama Aracı · eval Yerine Kısıtlı AST Değerlendirici"
summary: Tarihsel LLMMathChain / eval enjeksiyonu riskine karşı kısıtlı AST aritmetik değerlendiricisi, ara değer sınırı, canlı senaryo koşusu ve düğüm denetçisi kur.
esleme: ai-saldiri-09, ai-saldiri-20, ai-savunma-13, ai-savunma-31
timeout: 30
---

::: anlat 1. Gerçek olay ve yerel kopya sınırı
2023 yılında erken dönem ajan çerçevelerinde (örneğin tarihsel **LangChain `LLMMathChain` / CVE-2023-29374** tartışmaları ve **NVIDIA**'nın LLM sistemlerini `prompt injection` saldırılarına karşı koruma rehberi), dil modelinin ürettiği matematik ifadesini doğrudan Python `eval` / `exec` veya geniş yetkili ifade motorlarına geçirmenin **uzaktan kod yürütme (`RCE`)** ve kaynak tüketimi (`DoS`) doğurduğu gösterildi. Model ikna edildiğinde `'2 + 2'` yerine `'__import__("os").popen(...)'` veya `'9 ** 9 ** 9'` üretebilmektedir.

> [!NOTE]
> **Yerel kopya ayrımı:** Bu derste zafiyetli eski bir paket kurulmaz ve hiçbir zaman `eval` / `exec` çağrılmaz. Model çıktısını dar bir **Soyut Sözdizimi Ağacı (`AST`)** izin listesi ve ara değer sınırıyla değerlendirme mimarisi incelenir.
:::

::: anlat 2. Mekanizma · neden karakter filtresi değil, düğüm bazlı AST + ara değer kotası?
"`eval` öncesinde harfleri ve alt çizgileri silelim" yaklaşımı güvenli değildir: örneğin yalnız rakam ve `*` karakterlerinden oluşan `'999999999 ** 999999999'` ifadesi tek bir harf bile içermediği halde belleği ve CPU'yu kilitler (`ai-saldiri-09`, `ai-savunma-13`, `ai-savunma-31`). Üstelik büyüklük sınırını yalnız **nihai sonuçta** kontrol etmek de yetmez:

- `'(10**9 * 5) * 0'` ifadesinin nihai sonucu `0` olduğu halde sol alt ağaçta `5_000_000_000` ara değeri hesaplanmıştır!

Güvenli aritmetik değerlendirici:
1. Girdi uzunluğunu baştan sınırlar (`1 <= len(ifade) <= 80`, boşluktan ibaret dizge reddedilir).
2. `ast.parse(ifade, mode='eval')` ağacında **yalnız** tam sayı sabitlerine (`type(n.value) is int`), tekli `+/-` (`UAdd`, `USub`) ve ikili `+`, `-`, `*` (`Add`, `Sub`, `Mult`) düğümlerine izin verir (`Pow` `**`, `Call`, `Name`, `Attribute`, `Subscript`, `FloorDiv` kesinlikle yasaktır).
3. Ağacın **her düğümünde** üretilen ara ve son değerin mutlak büyüklüğünü `abs(v) <= 10**9` ile sınırlar.

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| `eval(ifade, {'__builtins__': {}})` | Nesne alt sınıfları (`().__class__.__base__.__subclasses__()`) ve `**` üs alma ile aşılır | `eval` yerine açık `ast.parse` düğüm gezgini |
| `abs(sonuc) <= 10**9` kontrolünü yalnız en dışta yapmak | `'(1000000000 * 8) * 0'` ara hesapta sınırı deler ama sonda `0` döner | Her `visit(n)` adımında `abs(v) <= 10**9` kontrolü |
| `isinstance(n.value, int)` kullanmak | `'True + 2'` ifadesindeki `True` sabitini `1` kabul eder | `type(n.value) is int` |
:::

::: tahmin Sonucu sıfır olan bir ifade ara değer sınırını nasıl deler?
Sınır kontrolünü yalnız en sonda yapan değerlendirici ile her düğümde yapan değerlendirici `'(600000000 * 4) * 0'` ifadesine ne der?

```python
import ast

def yalniz_son_kontrol(ifade):
    agac = ast.parse(ifade, mode='eval').body
    sol = agac.left.left.value * agac.left.right.value
    son = sol * agac.right.value
    return abs(son) <= 10**9, sol, son

gecti, ara_deger, son_deger = yalniz_son_kontrol('(600000000 * 4) * 0')
print('ara değer:', ara_deger, '| son değer:', son_deger, '| yalnız-son geçti mi:', gecti)
```

???

```cikti
ara değer: 2400000000 | son değer: 0 | yalnız-son geçti mi: True
```
Ara çarpım `2.4 * 10**9` olduğu halde `0` ile çarpılınca izi silinir! Özyinelemeli `visit` işlevinin her düğüm dönüşünde `abs(v) > 10**9` kontrolü yapmak ara değer patlamasını kaynağında durdurur.
:::

::: gorev 1 · Kısıtlı AST aritmetik değerlendiricisini (`aritmetik`) kur
`aritmetik(ifade)` işlevini yaz (`eval` veya `exec` kesinlikle kullanma):

- `ifade` boş olmayan (ve yalnız boşluktan oluşmayan), en çok `80` karakterlik `str` olmalı; aksi halde `ValueError` fırlat.
- `ast.parse(ifade, mode='eval')` ağacında yalnız şu düğümlere izin ver:
  - `ast.Constant` ve `type(n.value) is int` (`bool` ve `float` yasak!);
  - `ast.UnaryOp` ve işleç `(ast.UAdd, ast.USub)`;
  - `ast.BinOp` ve işleç `(ast.Add, ast.Sub, ast.Mult)`.
- Her düğümün ürettiği değer (sabit, tekli işlem ve ikili işlem ara sonuçları dahil!) `abs(v) <= 10**9` koşulunu sağlamalıdır.
- İzin dışı herhangi bir düğümde, sözdizimi hatasında (`SyntaxError`), özyineleme aşımında (`RecursionError`) veya sınır aşımında `ValueError` fırlat.

KUSURLU başlangıç uzunluk sınırını ve ara değer kontrolünü atlıyor, ayrıca `bool` sabitlerini kabul ediyor!

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
Path('ornek.json').write_text('[\n  "2+3*4"\n]', encoding='utf-8')
```

```starter
import ast

def aritmetik(ifade):
    def coz(n):
        if isinstance(n, ast.Constant) and isinstance(n.value, int):
            return int(n.value)
        if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub, ast.Mult)):
            a, b = coz(n.left), coz(n.right)
            return a + b if isinstance(n.op, ast.Add) else (a - b if isinstance(n.op, ast.Sub) else a * b)
        raise ValueError('yasak')
    sonuc = coz(ast.parse(ifade, mode='eval').body)
    if abs(sonuc) > 10**9:
        raise ValueError('asim')
    return sonuc

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(aritmetik(*_args))
```

```solution
import ast

def aritmetik(ifade):
    if not isinstance(ifade, str) or not ifade.strip() or len(ifade) > 80:
        raise ValueError('ifade 1..80 karakterlik bos olmayan str olmali')

    def _ziyaret(dugum):
        if isinstance(dugum, ast.Constant) and type(dugum.value) is int:
            deger = dugum.value
        elif isinstance(dugum, ast.UnaryOp) and isinstance(dugum.op, (ast.UAdd, ast.USub)):
            alt = _ziyaret(dugum.operand)
            deger = alt if isinstance(dugum.op, ast.UAdd) else -alt
        elif isinstance(dugum, ast.BinOp) and isinstance(dugum.op, (ast.Add, ast.Sub, ast.Mult)):
            sol = _ziyaret(dugum.left)
            sag = _ziyaret(dugum.right)
            if isinstance(dugum.op, ast.Add):
                deger = sol + sag
            elif isinstance(dugum.op, ast.Sub):
                deger = sol - sag
            else:
                deger = sol * sag
        else:
            raise ValueError('izin disi AST dugumu')
        if abs(deger) > 10**9:
            raise ValueError('ara veya son deger 10**9 sinirini asti')
        return deger

    try:
        kok = ast.parse(ifade, mode='eval').body
        return _ziyaret(kok)
    except (SyntaxError, RecursionError) as exc:
        raise ValueError('gecersiz aritmetik ifade') from exc

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(aritmetik(*_args))
```

```test
need('aritmetik')
eq(aritmetik('2+3*4'), 14, 'çarpma önceliği korunmalı')
eq(aritmetik('-(10 - 25) + +5'), 20, 'tekli + ve - desteklenmeli')
eq(aritmetik('1000000000'), 10**9, 'tam 10**9 üst sınırı geçmeli')
eq(aritmetik('-1000000000'), -(10**9), 'tam -10**9 alt sınırı geçmeli')
eq(aritmetik('1+' * 39 + '1'), 40, 'tam 79 karakterlik ifade geçmeli')

_yasak_ifadeler = [
    '',
    '   ',
    '1+' * 40 + '1',
    '1000000001',
    '(600000000 * 2) * 0',
    '2 ** 8',
    '10 / 2',
    '10 // 2',
    'True + 1',
    'False * 5',
    '2.5 + 1',
    'abs(-5)',
    '__import__("os")',
    '[1, 2][0]',
    'x + 1',
    '1 +',
    None,
    123,
]
for _ifade in _yasak_ifadeler:
    raises(ValueError, aritmetik, _ifade, msg=f'güvensiz veya sınır dışı ifade ValueError üretmeli: {_ifade!r}')

eq(aritmetik('1+' * 39 + '10'), 49, 'tam 80 karakterlik ifade geçmeli')
# Tekli işleç türü de denetlenmeli: `not` ve `~` da UnaryOp'tur; tür kontrolü olmadan -5 gibi hesaplanırdı.
for _ifade in ('not 5', '~5', '-(~5)'):
    raises(ValueError, aritmetik, _ifade, msg=f'izin dışı tekli işleç ValueError üretmeli: {_ifade!r}')
```

```hint
`_ziyaret` içinde hem `ast.Constant` (`type(dugum.value) is int`), hem `ast.UnaryOp` (`UAdd`, `USub`), hem `ast.BinOp` (`Add`, `Sub`, `Mult`) dallarının sonundaki ortak `if abs(deger) > 10**9: raise ValueError(...)` kontrolünü çalıştır.
```
:::

::: gorev 2 · Açık ve yamalı ifade motorunu senaryo vakalarında ölç
`aritmetik_senaryo_olc(vakalar, acik_fn, yamali_fn)` işlevini yaz:

- Her vaka `{'saldiri': bool, 'girdi': (ifade,), 'beklenen': int|None}` sözlüğüdür. Şema veya çağrılabilirlik bozuksa `ValueError` fırlat.
- Saldırı vakasında (`saldiri is True`), sınır işlevi `ValueError` fırlatmadan bir değer döndürürse tehlikeli ifadeyi **çalıştırdı (`sizma`)** sayılır; `ValueError` fırlatırsa engellemiştir.
- Meşru vakada (`saldiri is False`), sınır işlevi `ValueError` fırlatmadan `sonuc == v['beklenen']` döndürürse **meşru kabul** sayılır.
- Dönüş: `{'saldiri_n': int, 'mesru_n': int, 'once_sizma': float|None, 'sonra_sizma': float|None, 'mesru_kabul': float|None, 'regresyon_n': int}`.

KUSURLU başlangıç `ValueError` yakalamadığı için yamalı sınır ilk saldırıyı reddettiğinde ölçüm fonksiyonu çöküyor!

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def aritmetik_senaryo_olc(vakalar, acik_fn, yamali_fn):
    s = [v for v in vakalar if v['saldiri']]
    m = [v for v in vakalar if not v['saldiri']]
    return {
        'saldiri_n': len(s), 'mesru_n': len(m),
        'once_sizma': round(sum(1 for v in s if acik_fn(*v['girdi']) is not None) / len(s), 4),
        'sonra_sizma': round(sum(1 for v in s if yamali_fn(*v['girdi']) is not None) / len(s), 4),
        'mesru_kabul': round(sum(1 for v in m if yamali_fn(*v['girdi']) == v['beklenen']) / len(m), 4),
        'regresyon_n': 0,
    }
```

```solution
import copy

def _cagir(fn, girdi):
    try:
        return True, fn(*copy.deepcopy(girdi))
    except ValueError:
        return False, None

def aritmetik_senaryo_olc(vakalar, acik_fn, yamali_fn):
    if not isinstance(vakalar, list) or not vakalar or not callable(acik_fn) or not callable(yamali_fn):
        raise ValueError('gecerli vakalar ve cagrilaiblir sinirlar gerekli')
    s_n = m_n = s_once = s_sonra = m_sonra = reg = 0
    for v in vakalar:
        if not isinstance(v, dict) or type(v.get('saldiri')) is not bool or not isinstance(v.get('girdi'), (tuple, list)):
            raise ValueError('bozuk vaka semasi')
        once_calisti, once_deger = _cagir(acik_fn, v['girdi'])
        sonra_calisti, sonra_deger = _cagir(yamali_fn, v['girdi'])
        if v['saldiri']:
            s_n += 1
            s_once += int(once_calisti)
            s_sonra += int(sonra_calisti)
        else:
            m_n += 1
            once_dogru = once_calisti and (once_deger == v.get('beklenen')) and type(once_deger) is int
            sonra_dogru = sonra_calisti and (sonra_deger == v.get('beklenen')) and type(sonra_deger) is int
            m_sonra += int(sonra_dogru)
            if once_dogru and not sonra_dogru:
                reg += 1
    return {
        'saldiri_n': s_n,
        'mesru_n': m_n,
        'once_sizma': round(s_once / s_n, 4) if s_n else None,
        'sonra_sizma': round(s_sonra / s_n, 4) if s_n else None,
        'mesru_kabul': round(m_sonra / m_n, 4) if m_n else None,
        'regresyon_n': reg,
    }
```

```test
need('aritmetik_senaryo_olc')
import ast
from sandbox.ai_olay_senaryo import acik_sinir, senaryo_vakalari

def _yama(ifade):
    if not isinstance(ifade, str) or not ifade.strip() or len(ifade) > 80:
        raise ValueError('ifade')
    def vis(n):
        if isinstance(n, ast.Constant) and type(n.value) is int:
            v = n.value
        elif isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.UAdd, ast.USub)):
            v = vis(n.operand) * (1 if isinstance(n.op, ast.UAdd) else -1)
        elif isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub, ast.Mult)):
            a, b = vis(n.left), vis(n.right)
            v = a + b if isinstance(n.op, ast.Add) else (a - b if isinstance(n.op, ast.Sub) else a * b)
        else:
            raise ValueError('yasak')
        if abs(v) > 10**9:
            raise ValueError('asim')
        return v
    return vis(ast.parse(ifade, mode='eval').body)

_vakalar = senaryo_vakalari(13, tohum=13)
eq(aritmetik_senaryo_olc(_vakalar, acik_sinir(13), _yama), {
    'saldiri_n': 4,
    'mesru_n': 2,
    'once_sizma': 1.0,
    'sonra_sizma': 0.0,
    'mesru_kabul': 1.0,
    'regresyon_n': 0,
}, 'açık AST 4/4 saldırıyı çalıştırır, kısıtlı AST hepsini ValueError ile reddeder')

def _hep_red(_i):
    raise ValueError('red')

eq(aritmetik_senaryo_olc(_vakalar, acik_sinir(13), _hep_red)['regresyon_n'], 2, 'her ifadeyi reddeden sınır 2 regresyon üretir')
raises(ValueError, aritmetik_senaryo_olc, [], acik_sinir(13), _yama, msg='boş liste ValueError')

# Ölçüm mantığı alandan bağımsızdır. Saldırıda "çalıştı" (ValueError yok) sızıntıdır; meşru vakada
# doğru sayılmak için hem çalışmalı hem beklenen int değeri döndürmelidir.
_el = [
    {'saldiri': True, 'girdi': ('s-ikisi-gecer',)},
    {'saldiri': True, 'girdi': ('s-acik-de-durdurur',)},
    {'saldiri': True, 'girdi': ('s-yalniz-acik-gecer',)},
    {'saldiri': False, 'girdi': ('m-ikisi-gecer',), 'beklenen': 7},
    {'saldiri': False, 'girdi': ('m-ikisi-durdurur',), 'beklenen': 7},
    {'saldiri': False, 'girdi': ('m-regresyon',), 'beklenen': 7},
]
def _sinir(gecenler):
    def _f(i):
        if i not in gecenler:
            raise ValueError('red')
        return 7
    return _f
_acik_el = _sinir(('s-ikisi-gecer', 's-yalniz-acik-gecer', 'm-ikisi-gecer', 'm-regresyon'))
_yama_el = _sinir(('s-ikisi-gecer', 'm-ikisi-gecer'))
eq(aritmetik_senaryo_olc(_el, _acik_el, _yama_el), {
    'saldiri_n': 3,
    'mesru_n': 3,
    'once_sizma': 0.6667,
    'sonra_sizma': 0.3333,
    'mesru_kabul': 0.3333,
    'regresyon_n': 1,
}, 'oranlar grup paydasıyla ve 4 basamakla; sıfırdan farklı sonra_sizma ve regresyon doğru sayılmalı')
eq(aritmetik_senaryo_olc(_el, _acik_el, _acik_el)['sonra_sizma'], 0.6667, 'yama açık sınırla aynıysa sonra_sizma = once_sizma')
eq(aritmetik_senaryo_olc(_el, _sinir(()), _sinir(()))['regresyon_n'], 0, 'açık sınırın da reddettiği meşru vaka regresyon sayılmaz')
eq(aritmetik_senaryo_olc([v for v in _el if v['saldiri']], _acik_el, _yama_el)['mesru_kabul'], None, 'meşru vaka yoksa mesru_kabul None')
eq(aritmetik_senaryo_olc([v for v in _el if not v['saldiri']], _acik_el, _yama_el),
   {'saldiri_n': 0, 'mesru_n': 3, 'once_sizma': None, 'sonra_sizma': None, 'mesru_kabul': 0.3333, 'regresyon_n': 1},
   'saldırı vakası yoksa once_sizma ve sonra_sizma None')
# Meşru vakada yanlış değer, bool ya da float "doğru" sayılmaz; açık sınır doğru, yama yanlış değer
# döndürürse bu bir regresyondur.
for _yanlis in (lambda _i: 8, lambda _i: 7.0):
    eq(aritmetik_senaryo_olc(_el, _acik_el, _yanlis)['mesru_kabul'], 0.0, 'yanlış değer veya float meşru kabul sayılmaz')
    eq(aritmetik_senaryo_olc(_el, _acik_el, _yanlis)['regresyon_n'], 2, 'açık sınırın doğru, yamanın yanlış hesapladığı vakalar regresyondur')
_bir = [{'saldiri': False, 'girdi': ('m',), 'beklenen': 1}]
eq(aritmetik_senaryo_olc(_bir, lambda _i: 1, lambda _i: True)['regresyon_n'], 1, 'True == 1 olsa da bool sonuç doğru sayılmaz')
for _acik_yanlis in (lambda _i: 2, lambda _i: True):
    eq(aritmetik_senaryo_olc(_bir, _acik_yanlis, lambda _i: (_ for _ in ()).throw(ValueError('red')))['regresyon_n'], 0,
       'açık sınır yanlış (ya da bool) hesaplamışsa yamanın reddi regresyon değildir')
raises(ValueError, aritmetik_senaryo_olc, tuple(_el), _acik_el, _yama_el, msg='liste olmayan vakalar ValueError')
raises(ValueError, aritmetik_senaryo_olc, _el, None, _yama_el, msg='çağrılamaz açık sınır ValueError')
raises(ValueError, aritmetik_senaryo_olc, _el, _acik_el, 'yama', msg='çağrılamaz yamalı sınır ValueError')
for _bozuk in (
    _el + [('s-ikisi-gecer',)],
    _el + [{'saldiri': 1, 'girdi': ('s-ikisi-gecer',)}],
    _el + [{'saldiri': True, 'girdi': None}],
):
    raises(ValueError, aritmetik_senaryo_olc, _bozuk, _acik_el, _yama_el, msg=f'bozuk vaka şeması ValueError: {_bozuk[-1]!r}')
```

```hint
`_cagir(fn, girdi)` yardımcısıyla `ValueError` fırlamasını `(False, None)` çiftine çevir; meşru vakalarda dönen değerin `v['beklenen']` ile eşitliğini kontrol et.
```
:::

::: gorev 3 · Yürütme öncesi statik AST düğüm ve derinlik kapısını kur
İfadeyi hiç hesaplamadan önce karmaşıklığını ve yasaklı AST düğümlerini raporlayan `ast_guvenlik_ozeti(ifade, maks_dugum=15)` işlevini yaz:

- `ifade` boş olmayan `str` ve `maks_dugum` pozitif `int` (`type(maks_dugum) is int and maks_dugum > 0`) olmalı; aksi halde veya sözdizimi hatasında (`SyntaxError`) `ValueError` fırlat.
- `kok = ast.parse(ifade, mode='eval').body` alt ağacındaki (`Expression` sarmalayıcısı ve işleç belirteçleri `Add/Sub/Mult/UAdd/USub/Load` hariç, yani yalnız `ast.expr` ifade düğümleri!) düğümleri gez:
  - `dugum_sayisi`: ağaçtaki `ast.expr` düğümlerinin toplam sayısı (`Constant`, `BinOp`, `UnaryOp`, `Call`, `Name` vb. hepsi `ast.expr` alt sınıfıdır!).
  - `yasak_turler`: izinli üç `ast.expr` türü (`Constant` [yalnız `type(value) is int`], `UnaryOp` [`UAdd`/`USub`], `BinOp` [`Add`/`Sub`/`Mult`]) dışındaki düğümlerin sınıf adlarının (`type(n).__name__`) benzersiz alfabetik sıralı listesi (`bool`/`float` `Constant` varsa `'Constant'` eklenir; yasaklı işleçli `BinOp` varsa `'BinOp'` eklenir).
  - `izin`: `yasak_turler == []` **ve** `dugum_sayisi <= maks_dugum` ise `True`, aksi halde `False`.
- Dönüş: `{'izin': bool, 'dugum_sayisi': int, 'yasak_turler': list[str]}`.

KUSURLU başlangıç `maks_dugum` sınırını kontrol etmiyor ve `Pow` (`2 ** 3`) işleçli `BinOp` düğümünü izinli sanıyor!

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
import ast

def ast_guvenlik_ozeti(ifade, maks_dugum=15):
    kok = ast.parse(ifade, mode='eval').body
    exprler = [n for n in ast.walk(kok) if isinstance(n, ast.expr)]
    yasak = sorted({type(n).__name__ for n in exprler if not isinstance(n, (ast.Constant, ast.UnaryOp, ast.BinOp))})
    return {'izin': not yasak, 'dugum_sayisi': len(exprler), 'yasak_turler': yasak}
```

```solution
import ast

def _ifade_dugumu_izinli(n):
    if isinstance(n, ast.Constant):
        return type(n.value) is int
    if isinstance(n, ast.UnaryOp):
        return isinstance(n.op, (ast.UAdd, ast.USub))
    if isinstance(n, ast.BinOp):
        return isinstance(n.op, (ast.Add, ast.Sub, ast.Mult))
    return False

def ast_guvenlik_ozeti(ifade, maks_dugum=15):
    if not isinstance(ifade, str) or not ifade.strip() or type(maks_dugum) is not int or maks_dugum <= 0:
        raise ValueError('gecersiz ifade veya maks_dugum')
    try:
        kok = ast.parse(ifade, mode='eval').body
    except (SyntaxError, RecursionError) as exc:
        raise ValueError('gecersiz sozdizimi') from exc
    exprler = [n for n in ast.walk(kok) if isinstance(n, ast.expr)]
    yasak = sorted({type(n).__name__ for n in exprler if not _ifade_dugumu_izinli(n)})
    izin = (len(yasak) == 0) and (len(exprler) <= maks_dugum)
    return {
        'izin': izin,
        'dugum_sayisi': len(exprler),
        'yasak_turler': yasak,
    }
```

```test
need('ast_guvenlik_ozeti')
eq(ast_guvenlik_ozeti('2 + 3 * 4'), {'izin': True, 'dugum_sayisi': 5, 'yasak_turler': []}, '2+3*4 ifadesinde 3 Constant + 2 BinOp = 5 düğüm vardır')
eq(ast_guvenlik_ozeti('2 + 3 * 4', maks_dugum=4), {'izin': False, 'dugum_sayisi': 5, 'yasak_turler': []}, 'maks_dugum aşımı izin=False yapmalı')
eq(ast_guvenlik_ozeti('2 ** 8'), {'izin': False, 'dugum_sayisi': 3, 'yasak_turler': ['BinOp']}, 'Pow işleçli BinOp yakalanmalı')
eq(ast_guvenlik_ozeti('abs(x)'), {'izin': False, 'dugum_sayisi': 3, 'yasak_turler': ['Call', 'Name']}, 'Call ve Name alfabetik raporlanmalı')
eq(ast_guvenlik_ozeti('True + 1'), {'izin': False, 'dugum_sayisi': 3, 'yasak_turler': ['Constant']}, 'bool Constant yakalanmalı')

for _bozuk in (('', 10), ('1 +', 10), ('1+2', 0), ('1+2', True), (None, 10), (12, 10)):
    raises(ValueError, ast_guvenlik_ozeti, *_bozuk, msg=f'bozuk ifade veya maks_dugum ValueError: {_bozuk!r}')

eq(ast_guvenlik_ozeti('-5'), {'izin': True, 'dugum_sayisi': 2, 'yasak_turler': []}, 'tekli eksi (USub) izinli: UnaryOp + Constant')
eq(ast_guvenlik_ozeti('not 5'), {'izin': False, 'dugum_sayisi': 2, 'yasak_turler': ['UnaryOp']}, 'not işleçli UnaryOp yasak')
eq(ast_guvenlik_ozeti('~5'), {'izin': False, 'dugum_sayisi': 2, 'yasak_turler': ['UnaryOp']}, '~ işleçli UnaryOp yasak')
eq(ast_guvenlik_ozeti('2 + 3 * 4', maks_dugum=5)['izin'], True, 'düğüm sayısı tam maks_dugum ise izinli')
eq(ast_guvenlik_ozeti('7', maks_dugum=1), {'izin': True, 'dugum_sayisi': 1, 'yasak_turler': []}, 'maks_dugum = 1 geçerli')
eq(ast_guvenlik_ozeti('1+1+1+1+1+1+1+1')['izin'], True, 'varsayılan maks_dugum 15: 8 Constant + 7 BinOp izinli')
eq(ast_guvenlik_ozeti('-1+1+1+1+1+1+1+1')['izin'], False, 'varsayılan maks_dugum 15: 16 düğüm reddedilir')
```

```hint
`[n for n in ast.walk(kok) if isinstance(n, ast.expr)]` tüm ifade düğümlerini verir; her düğüm için hem sınıfını hem iç işleç/değer tipini (`Pow`, `bool`) kontrol et.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Olay bağlamı (15 sn).** "Tarihsel `LLMMathChain` / CVE-2023-29374 örneği, model çıktısını `eval` veya genel ifade motoruna vermenin doğrudan kod yürütmeye dönüştüğünü gösterdi."
2. **Mekanizma (30 sn).** "Harf silen kara listeler `9**9**9` kaynak tüketimini ve `().__class__` zincirlerini durduramaz; yalnız son sonucu kontrol etmek de `(10**9 * 4) * 0` ara patlamasını kaçırır."
3. **Sınır ve ölçüm (30 sn).** "`aritmetik` içinde 80 karakter sınırı, üç düğümlü `AST allowlist` ve her düğümde `abs(v) <= 10**9` kotasını kurup senaryo koşusunda doğruladım."
4. **Statik ön kapı (25 sn).** "`ast_guvenlik_ozeti` ile ifadeyi hiç çalıştırmadan önce düğüm sayısını ve yasaklı AST türlerini (`Call`, `Name`, `Pow`) raporladım."
5. **Kapanış (20 sn).** "Model çıktısı hiçbir zaman genel amaçlı yorumlayıcıya kod olarak verilmez; kısıtlı veri şeması veya izole AST ile işlenir."
:::

::: anlat Sınır ve kaynak
Bu dersteki değerlendirici yalnız tam sayı toplama, çıkarma ve çarpma işlemlerini destekler. Genel Python kodu çalıştırması gerçekten gereken veri analizi ajanlarında (`code interpreter`) AST beyaz listesi yeterli olmaz; ağsız, dosya sistemi salt-okunur, bellek/CPU kotalı ayrı bir sanal makine veya mikro-VM (`gVisor` / `Firecracker`) zorunludur (`ai-savunma-13`).

- Birincil kaynaklar: [NVIDIA Developer Blog — Securing LLM Systems Against Prompt Injection](https://developer.nvidia.com/blog/securing-llm-systems-against-prompt-injection), [NVD CVE-2023-29374 kaydı](https://nvd.nist.gov/vuln/detail/CVE-2023-29374). Doğrulama tarihi: 10 Kasım 2026.
:::

::: dusun
`aritmetik` işlevine bölme (`/` veya `//`) eklemek isteseydin, mevcut `abs(v) <= 10**9` kuralına ek olarak hangi istisna ve tip durumunu açıkça ele alman gerekirdi?
:::

::: ozet
- Dil modelinin ürettiği ifadeler güvenilmeyen girdidir; `eval` / `exec` ile değerlendirilmez.
- Kısıtlı `AST` gezgini yalnız izinli düğümleri ve `type(val) is int` sabitlerini kabul eder.
- Büyüklük sınırı (`<= 10**9`) yalnız nihai çıktıda değil, her ara AST düğümünde uygulanmalıdır.
:::
