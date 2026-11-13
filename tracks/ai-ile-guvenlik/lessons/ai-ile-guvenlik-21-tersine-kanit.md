---
id: ai-ile-guvenlik-21
title: "LLM Destekli Tersine Mühendislik · İddia ve Def-Use"
summary: Modelin derlenmiş kod için yazdığı özeti kanıta bağla; küçük bir ara gösterimi bağımsız yorumla ve 8 bitlik girdi uzayının tamamını deneyerek özetin doğru olup olmadığını karşı örnekle kanıtla.
esleme: ai-ile-guvenlik-04, ai-ile-guvenlik-05, ai-temel-14, ai-ile-guvenlik-22
timeout: 30
---

::: anlat 1. Model özeti bir hipotezdir
Dil modelleri derlenmiş koda bakıp okunur özetler üretebiliyor. Tan, Luo, Li ve Zhang'ın *LLM4Decompile* çalışması (arXiv:2403.05286, EMNLP 2024) ikili koddan doğrudan kaynak kod üreten açık kaynak bir model ailesi sundu. Bu tür araçlar analistin işini hızlandırır. Ama ürettikleri şey bir **hipotezdir**: akıcı, ikna edici ve bazen yanlış.

OWASP'ın LLM09:2025 *Misinformation* maddesi bu riski iki adla anar: modelin uydurması (*hallucination*) ve kullanıcının modelin çıktısına doğrulamadan güvenmesi (*overreliance*). Önerdiği karşılık da açıktır: çapraz doğrulama ve insan denetimi. Tersine mühendislikte çapraz doğrulamanın en güçlü biçimi, özetin söylediği davranışı **kodu gerçekten çalıştırarak** sınamaktır.

Bir modelin derlenmiş bir işlev hakkında yaptığı açıklama üç ayrı iddia içerir:

1. **Komut çözme:** hangi işlemler hangi sırayla yapılıyor?
2. **Veri akışı (*def-use*):** hangi değer nerede tanımlanıyor (*def*), nerede kullanılıyor (*use*)?
3. **Amaç:** "bu bir şifreleme", "bu bir sağlama toplamı".

Üçüncüsü en kolay uydurulanıdır. Bir `xor` sabiti görmek, işlevin bir şifreleme algoritması olduğunu kanıtlamaz.

> [!NOTE]
> Bu derste gerçek ikili dosya, ayrıştırıcı ya da model çağrısı yoktur. Üç işlemli **sentetik** bir ara gösterim (IR) ve sentetik model özetleri kullanılır.
:::

::: anlat 2. Mekanizma: küçük uzayda tam doğrulama
Gerçek bir işlevin girdi uzayı çoğu zaman taranamayacak kadar büyüktür; analist örneklerle ve sembolik yürütmeyle çalışır. Bu dersteki IR ise 8 bitlik tek bir akümülatör üzerinde çalışır: girdi `0..255`, yani yalnız **256** olası değer var. Bu, özetin doğruluğunu **tamamen** sınamaya izin verir. Her girdi için programı çalıştırıp özetin öngördüğü çıktıyla karşılaştırırız. İlk uyuşmazlık bir **karşı örnektir** ve özeti çürütmeye yeter. Hiç uyuşmazlık yoksa özet bu IR için kanıtlanmıştır.

Tuzak şudur: birkaç girdide doğru çıkan özet "doğrulanmış" gibi görünür. Örneğin `add 5` ardından `xor 3` yapan bir program `x = 0` için `6` döndürür. "Bu işlev girdiyi 6 ile xor'luyor" diyen bir özet bu tek örnekte doğrudur, ama `x = 1` için yanlıştır. Toplama elde (*carry*) üretir, xor üretmez; ikisinin bileşimi tek bir xor'a indirgenemez.

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| Özeti tek bir örnekle doğrulamak | `x = 0` gibi özel girdiler farklı işlemleri aynı gösterir | Uzay küçükse hepsini dene; değilse karşı örnek ara |
| `xor` sabiti görünce "şifreleme" demek | Amaç iddiası veri akışından türetilmez | Davranışı ölç, amacı ayrı ve kanıtla söyle |
| Modulo 256'yı unutmak | Gerçek 8 bitlik yazmaç taşar; `250 + 10` 4 olur | Her işlemden sonra `% 256` |
| `ret` sonrası kodu yok saymak | Ölü kod gizli bir yolun işareti olabilir | `ret` son komut değilse hata |
| `True`'yu sayı kabul etmek | `add True` sessizce `add 1` olur | `type(arg) is int` |
:::

::: tahmin İlk girdide doğru, ikincide yanlış
Program `add 5` sonra `xor 3` yapıyor. Model "girdiyi 6 ile xor'luyor" diyor. İlk iki girdide program ve özet ne üretir?

```python
def program(x):
    return ((x + 5) % 256) ^ 3

def ozet(x):
    return x ^ 6

for x in (0, 1):
    print(x, program(x), ozet(x))
```

???

```cikti
0 6 6
1 5 7
```
`x = 0`'da ikisi de 6 verir; tek bir örnekle bakan özeti doğru sanır. `x = 1`'de toplama ile xor ayrılır: `1 + 5 = 6`, `6 ^ 3 = 5`, oysa `1 ^ 6 = 7`. İlk karşı örnek `x = 1`'dir.
:::

::: gorev 1 · Sentetik IR'ı bağımsız yorumla
`ir_calistir(program, x)` işlevini yaz.

- `program` bir `list`; her komut `[op, arg]` biçiminde 2 elemanlı bir `list` ya da `tuple`.
- `x` `bool` olmayan bir `int` ve `0 <= x <= 255`; akümülatör `x` ile başlar.
- `op == 'add'` → `acc = (acc + arg) % 256`; `op == 'xor'` → `acc = (acc ^ arg) % 256`. Bu iki işlemde `arg` `bool` olmayan bir `int` olmalı (negatif olabilir; sonuç yine `% 256` ile 0..255'e iner).
- `op == 'ret'` → `arg` `None` olmalı ve bu komut programın **son** komutu olmalı; akümülatör döndürülür.
- Hata (`ValueError`): `program` liste değil, `x` aralık dışı ya da `int` değil, komut biçimi bozuk, bilinmeyen `op`, `ret` yok, `ret`'ten sonra komut var, `ret` argümanı `None` değil.

KUSURLU başlangıç modulo almayı unutuyor, `ret`'ten sonraki komutları sessizce yok sayıyor ve bilinmeyen işlemi atlıyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
Path('ornek.json').write_text('[[["add", 250], ["xor", 3], ["ret", null]], 10]', encoding='utf-8')
```

```starter
def ir_calistir(program, x):
    acc = x
    for op, arg in program:
        if op == 'add':
            acc = acc + arg
        elif op == 'xor':
            acc = acc ^ arg
        elif op == 'ret':
            return acc
    return acc

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(ir_calistir(*_args))
```

```solution
def ir_calistir(program, x):
    if not isinstance(program, list) or type(x) is not int or not 0 <= x <= 255:
        raise ValueError('program list, x 0..255 int olmali')
    acc = x
    for i, komut in enumerate(program):
        if not isinstance(komut, (list, tuple)) or len(komut) != 2:
            raise ValueError('komut [op, arg] olmali')
        op, arg = komut
        if op == 'ret':
            if arg is not None or i != len(program) - 1:
                raise ValueError('ret son komut olmali ve argumansiz olmali')
            return acc
        if op not in ('add', 'xor') or type(arg) is not int:
            raise ValueError('bilinmeyen islem ya da bozuk arguman')
        acc = (acc + arg if op == 'add' else acc ^ arg) % 256
    raise ValueError('ret yok')

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(ir_calistir(*_args))
```

```test
need('ir_calistir')
import copy
_p = [['add', 5], ['xor', 3], ['ret', None]]
_yedek = copy.deepcopy(_p)
eq(ir_calistir(_p, 0), 6, '(0 + 5) ^ 3 = 6')
eq(ir_calistir(_p, 1), 5, '(1 + 5) ^ 3 = 5')
eq(_p, _yedek, 'program değişmemeli')
eq(ir_calistir([['add', 250], ['xor', 3], ['ret', None]], 10), 7, '10 + 250 = 260 → 4; 4 ^ 3 = 7')
eq(ir_calistir([['add', -1], ['ret', None]], 0), 255, 'negatif argüman modulo ile 255 olur')
eq(ir_calistir([['xor', 256 + 7], ['ret', None]], 1), 6, 'büyük xor argümanı sonuç modulo ile 0..255 içinde kalır')
eq(ir_calistir([('xor', 255), ('ret', None)], 255), 0, 'tuple komutlar geçerli')
eq(ir_calistir([['ret', None]], 255), 255, 'yalnız ret girdiyi döndürür; üst sınır 255')

for _bozuk_p in (
    [['add', 1]],
    [],
    [['ret', None], ['add', 1]],
    [['ret', 0]],
    [['mul', 2], ['ret', None]],
    [['add', True], ['ret', None]],
    [['add', 1.0], ['ret', None]],
    [['add'], ['ret', None]],
    [['add', 1, 2], ['ret', None]],
    ['add 1', ['ret', None]],
    [{'add': 1, 'ret': None}, ['ret', None]],
    [{'ret': 0, None: 1}],
):
    raises(ValueError, ir_calistir, _bozuk_p, 3, msg=f'bozuk program ValueError: {_bozuk_p!r}')
for _bozuk_x in (-1, 256, True, 3.0, '3', None):
    raises(ValueError, ir_calistir, [['ret', None]], _bozuk_x, msg=f'bozuk x ValueError: {_bozuk_x!r}')
raises(ValueError, ir_calistir, (('ret', None),), 3, msg='liste olmayan program ValueError')
```

```hint
Komutun biçimini açmadan önce doğrula. `ret`'i ilk sırada ele al: argümanı `None` mı ve son komut mu? Diğer işlemlerde sonucu her adımda `% 256` ile sınırla.
```
:::

::: gorev 2 · Model özetini 256 girdinin tamamıyla sına
`ozet_dogrula(program, ozet)` işlevini yaz. `ozet`, modelin program için önerdiği kapalı biçimdir: `{'tur': 'add' | 'xor' | 'sabit', 'deger': int}`.

- `'add'` → `f(x) = (x + deger) % 256`; `'xor'` → `f(x) = x ^ deger`; `'sabit'` → `f(x) = deger`. `deger` `bool` olmayan bir `int` ve `0 <= deger <= 255` olmalı; `ozet` bir `dict` olmalı, `tur` bu üçünden biri olmalı. Değilse `ValueError`.
- `program` görev 1'in kurallarına uyar; bozuksa `ValueError` (programı ilk girdiyle çalıştırırken ortaya çıkması yeterlidir). Bu görevin çözümü kendi IR yorumlayıcısını içermelidir.
- `x = 0, 1, …, 255` için programın çıktısını özetin çıktısıyla karşılaştır.
- Dönüş: `{'dogru': True, 'karsi_ornek': None}` ya da ilk uyuşmazlık için `{'dogru': False, 'karsi_ornek': [x, program_ciktisi, ozet_ciktisi]}`.

KUSURLU başlangıç özeti yalnız `x = 0` ve `x = 255` uçlarında sınıyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def _calistir(program, x):
    acc = x
    for op, arg in program:
        if op == 'ret':
            return acc
        acc = (acc + arg if op == 'add' else acc ^ arg) % 256
    return acc

def ozet_dogrula(program, ozet):
    d = ozet['deger']
    f = {'add': lambda x: (x + d) % 256, 'xor': lambda x: x ^ d, 'sabit': lambda x: d}[ozet['tur']]
    for x in (0, 255):
        if _calistir(program, x) != f(x):
            return {'dogru': False, 'karsi_ornek': [x, _calistir(program, x), f(x)]}
    return {'dogru': True, 'karsi_ornek': None}
```

```solution
def _calistir(program, x):
    if not isinstance(program, list):
        raise ValueError('program list olmali')
    acc = x
    for i, komut in enumerate(program):
        if not isinstance(komut, (list, tuple)) or len(komut) != 2:
            raise ValueError('komut [op, arg] olmali')
        op, arg = komut
        if op == 'ret':
            if arg is not None or i != len(program) - 1:
                raise ValueError('ret son komut olmali ve argumansiz olmali')
            return acc
        if op not in ('add', 'xor') or type(arg) is not int:
            raise ValueError('bilinmeyen islem ya da bozuk arguman')
        acc = (acc + arg if op == 'add' else acc ^ arg) % 256
    raise ValueError('ret yok')

def ozet_dogrula(program, ozet):
    if not isinstance(ozet, dict) or ozet.get('tur') not in ('add', 'xor', 'sabit'):
        raise ValueError('ozet tur add/xor/sabit olmali')
    d = ozet.get('deger')
    if type(d) is not int or not 0 <= d <= 255:
        raise ValueError('deger 0..255 int olmali')
    for x in range(256):
        p = _calistir(program, x)
        if ozet['tur'] == 'add':
            o = (x + d) % 256
        elif ozet['tur'] == 'xor':
            o = x ^ d
        else:
            o = d
        if p != o:
            return {'dogru': False, 'karsi_ornek': [x, p, o]}
    return {'dogru': True, 'karsi_ornek': None}
```

```test
need('ozet_dogrula')
import copy
_P = [['add', 5], ['xor', 3], ['ret', None]]
_yedek = copy.deepcopy(_P)
eq(ozet_dogrula(_P, {'tur': 'xor', 'deger': 6}), {'dogru': False, 'karsi_ornek': [1, 5, 7]},
   'x = 0\'da tutan xor 6 özeti x = 1\'de çürür')
eq(_P, _yedek, 'program değişmemeli')
eq(ozet_dogrula([['add', 7], ['add', 250], ['ret', None]], {'tur': 'add', 'deger': 1}), {'dogru': True, 'karsi_ornek': None},
   'iki toplama tek toplamaya indirgenir: 7 + 250 = 257 ≡ 1')
eq(ozet_dogrula([['xor', 12], ['xor', 10], ['ret', None]], {'tur': 'xor', 'deger': 6}), {'dogru': True, 'karsi_ornek': None},
   'iki xor tek xor\'a indirgenir: 12 ^ 10 = 6')
eq(ozet_dogrula([['xor', 255], ['add', 1], ['ret', None]], {'tur': 'xor', 'deger': 0})['karsi_ornek'], [1, 255, 1],
   'iki tümleyen olumsuzlaması: 1 → 254 + 1 = 255')
eq(ozet_dogrula([['ret', None]], {'tur': 'add', 'deger': 0}), {'dogru': True, 'karsi_ornek': None}, 'özdeşlik add 0 ile')
eq(ozet_dogrula([['ret', None]], {'tur': 'xor', 'deger': 0}), {'dogru': True, 'karsi_ornek': None}, 'özdeşlik xor 0 ile')
eq(ozet_dogrula([['ret', None]], {'tur': 'sabit', 'deger': 0}), {'dogru': False, 'karsi_ornek': [1, 1, 0]},
   'özdeşlik sabit değildir; ilk karşı örnek x = 1')
eq(ozet_dogrula([['add', 128], ['ret', None]], {'tur': 'xor', 'deger': 128}), {'dogru': True, 'karsi_ornek': None},
   'add 128 ile xor 128 8 bitte aynıdır: yalnız en üst bit değişir, elde taşar')
eq(ozet_dogrula([['add', 1], ['ret', None]], {'tur': 'add', 'deger': 255})['karsi_ornek'], [0, 1, 255], 'yanlış sabit ilk girdide çürür')
eq(ozet_dogrula([['add', 1], ['ret', None]], {'tur': 'xor', 'deger': 1})['karsi_ornek'], [1, 2, 0], 'add 1 ile xor 1 tek sayıda ayrılır')
eq(ozet_dogrula([['add', 255], ['ret', None]], {'tur': 'add', 'deger': 255}), {'dogru': True, 'karsi_ornek': None}, 'deger üst sınırı 255 geçerli')
eq(ozet_dogrula([['xor', 0], ['xor', 0], ['ret', None]], {'tur': 'xor', 'deger': 0}), {'dogru': True, 'karsi_ornek': None}, 'xor 0 özdeşlik')
eq(ozet_dogrula([['add', 0], ['ret', None]], {'tur': 'sabit', 'deger': 0})['karsi_ornek'], [1, 1, 0], 'sabit özeti ilk sıfır olmayan girdide çürür')

for _ozet in (None, [], {'tur': 'mul', 'deger': 1}, {'tur': 'add'}, {'tur': 'add', 'deger': 256}, {'tur': 'add', 'deger': -1},
              {'tur': 'xor', 'deger': True}, {'tur': 'xor', 'deger': 1.0}, {'deger': 1}):
    raises(ValueError, ozet_dogrula, _P, _ozet, msg=f'bozuk özet ValueError: {_ozet!r}')
for _bozuk_p in ([['add', 1]], [['ret', None], ['add', 1]], [['ret', 1]], [['div', 2], ['ret', None]], [['add', 1.5], ['ret', None]],
                 [['add'], ['ret', None]], ['ret'], (('ret', None),), [{'ret': 0, None: 1}]):
    raises(ValueError, ozet_dogrula, _bozuk_p, {'tur': 'add', 'deger': 0}, msg=f'bozuk program ValueError: {_bozuk_p!r}')
```

```hint
`for x in range(256)` ile bütün girdileri dolaş; her girdide programı kendi yorumlayıcınla çalıştır, özetin değerini hesapla ve ilk farkta karşı örneği döndür.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Hipotez (20 sn).** "LLM4Decompile gibi araçlar derlenmiş koda okunur özet ya da kaynak kod üretiyor. OWASP LLM09'un dediği gibi bu çıktı bir hipotez; doğrulamadan güvenmek overreliance."
2. **Bağımsız yorumlayıcı (25 sn).** "Önce üç işlemli IR'ı modelden bağımsız çalıştıran bir yorumlayıcı yazdık. Modulo 256 taşmasını, ret'ten sonraki ölü kodu ve True'nun sayı sanılmasını ayrı ayrı reddettik."
3. **Karşı örnek (35 sn).** "Model add 5 ve xor 3 yapan programa 'xor 6' dedi. x = 0'da ikisi de 6 veriyor, tek örnekle bakan biri onaylardı. 256 girdinin hepsini denedik; x = 1'de program 5, özet 7 veriyor. Özet çürüdü."
4. **Doğru indirgemeler (25 sn).** "Aynı yöntem doğru özetleri de kanıtlıyor: iki xor tek xor'a, iki toplama tek toplamaya iniyor; add 128 ile xor 128 ise 8 bitte birebir aynı."
5. **Sınır (15 sn).** "Gerçek kodda uzay taranamaz; orada sembolik yürütme ve hedefli karşı örnek araması gerekir."
:::

::: anlat Sınır ve kaynak
Bu ders 8 bitlik tek akümülatörlü, dallanmasız bir IR kullanır; bu yüzden girdi uzayı tamamen taranabilir. Gerçek ikili kodda yazmaçlar 32/64 bittir, bellek, dallanma, çağrı kuralları ve derleyici optimizasyonları vardır; tam tarama yerine sembolik yürütme ya da çözücü (SMT) tabanlı denklik denetimi kullanılır. Bu derste model çağrılmaz; özetler sentetiktir ve bir modelin gerçek başarısını ölçmez. Amaç iddiaları ("bu bir şifreleme") veri akışı doğrulamasının dışındadır ve ayrı kanıt ister.

- Birincil kaynaklar: [Tan, Luo, Li, Zhang — LLM4Decompile: Decompiling Binary Code with Large Language Models (arXiv:2403.05286, EMNLP 2024)](https://arxiv.org/abs/2403.05286); [OWASP GenAI — LLM09:2025 Misinformation](https://genai.owasp.org/llmrisk/llm092025-misinformation/) (hallucination, overreliance, çapraz doğrulama ve insan denetimi). Doğrulama tarihi: 11 Kasım 2026.
:::

::: dusun
IR'a 16 bitlik bir akümülatör eklendiğini düşün: girdi uzayı 65.536 olur, hâlâ taranabilir. 64 bitte taranamaz. Modelin "bu işlev girdiyi sabit bir anahtarla xor'luyor" özetini 64 bitte hangi az sayıda, iyi seçilmiş girdiyle çürütmeye çalışırdın?
:::

::: ozet
- Modelin derlenmiş kod özeti bir hipotezdir; doğrulamadan güvenmek OWASP LLM09'daki overreliance'tır.
- Komut, veri akışı ve amaç ayrı iddialardır; amaç en zayıf kanıtlananıdır.
- Uzay küçükse özet tamamen sınanır; ilk uyuşmazlık özeti çürütmeye yeter.
- Tek bir girdide doğru çıkan özet "doğrulanmış" değildir.
:::
