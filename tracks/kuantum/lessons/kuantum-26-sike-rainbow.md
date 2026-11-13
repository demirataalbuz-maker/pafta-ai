---
id: kuantum-26
title: "Kırılmış Adaylar · SIKE ve Rainbow"
summary: Standardizasyon sürecinde ilerlemiş iki adayın (SIKE, Rainbow) klasik bilgisayarlarla nasıl kırıldığını kaynaklı anlat; aday statüsünü güvenlik kanıtı sanmayan bir karar kuralı yaz ve açık ek denklemlerin bir sırrı nasıl belirlediğini sonlu cisimde oyuncak bir doğrusal sistemle göster.
esleme: kuantum-25, kuantum-28, kuantum-22, kuantum-21
timeout: 30
---

::: anlat 1. İki aday, iki klasik saldırı
NIST'in kuantum sonrası standardizasyon sürecinde ileri turlara kalmış iki aday 2022'de, kuantum bilgisayar kullanılmadan kırıldı:

- **SIKE (izojen tabanlı KEM).** Wouter Castryck ve Thomas Decru, *An efficient key recovery attack on SIDH* (IACR ePrint 2022/975) çalışmasında SIDH'in yapısına karşı bir anahtar kurtarma saldırısı sundu. Özete göre SIKEp434 parametreleri için saldırı tek bir çekirdekte **yaklaşık on dakikada** çalışıyordu. SIKE, SIDH'i kullandığı için doğrudan etkilendi.
- **Rainbow (çok değişkenli imza).** Ward Beullens, *Breaking Rainbow Takes a Weekend on a Laptop* (IACR ePrint 2022/214) çalışmasında Rainbow'un birinci güvenlik düzeyi (SL 1) parametrelerine karşı, standart bir dizüstü bilgisayarda **ortalama 53 saat** (bir hafta sonu) süren bir anahtar kurtarma saldırısı verdi.

İki saldırı da **klasiktir**. "Kuantum sonrası" etiketi bir algoritmanın kuantum bilgisayara dayanıklı olacağı **iddiasıdır**, klasik saldırılara dayanıklı olduğunun kanıtı değildir. Bir adayın standardizasyon sürecinde ilerlemiş olması da güvenlik garantisi değildir; bir standart bile koşulsuz güvenli sayılmaz ve uygulama hatalarına karşı ayrıca denetlenir (`kuantum-25`).

> [!NOTE]
> Bu derste gerçek bir SIKE ya da Rainbow saldırısı çalıştırılmaz. Görev 2 küçük bir sonlu cisimde **oyuncak** doğrusal cebirdir; iki saldırının matematiğini uygulamaz, yalnız "açık ek ilişkiler gizli bir değeri belirleyebilir" fikrini gösterir. Kaynaklardaki süreler kendi parametre ve donanım koşullarına aittir; burada kıyaslama olarak kullanılmaz.
:::

::: anlat 2. Mekanizma: yapı, sırrın aleyhine çalışabilir
Her iki saldırının ortak fikri, açık anahtarda ya da protokolde yayımlanan **ek yapısal bilginin** saldırgana gizli değeri kısıtlayan yeni denklemler vermesidir. SIDH'de taraflar, anahtar değişimi için açık anahtarın yanında ek noktalar (torsiyon noktası görüntüleri) yayımlıyordu; Castryck–Decru saldırısı bu ek bilgiyi kullandı. Rainbow'da katmanlı yapı, saldırgana anahtarı daha küçük parçalara ayıran ilişkiler verdi.

Görev 2 bu fikrin en sade biçimini gösterir. `n` bilinmeyenli gizli bir vektör `x` düşün. Tek bir denklem onu belirlemez. Ama yayımlanan her ek doğrusal ilişki (`A · x = b`, mod `p`) olası değerleri daraltır. Bağımsız `n` denklem toplandığında `x` tek olarak belirlenir ve Gauss eliminasyonuyla saniyeler içinde çözülür. Kırılmış şemalarda bu ilişkiler doğrusal değildi ve bulunmaları büyük buluşlar gerektirdi; ama sonuç aynıydı: yapı sırrı ele verdi.

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| "Kuantum sonrası = her saldırıya dayanıklı" | SIKE ve Rainbow klasik bilgisayarla kırıldı | Klasik kriptanaliz de sürer |
| "Son tura kaldı = güvenli" | Aday statüsü kanıt değildir | Kırılmışsa emekliye ayır; standart da gözden geçirilir |
| "Kırılmış" bilgisini aday/standart bilgisinden sonra denetlemek | Kırılmış bir standart "standart" diye kullanılır | Önce kırılma, sonra statü |
| Bir saldırı süresini her ortama genellemek | Süre parametreye ve donanıma bağlıdır | Kaynağın koşullarını birlikte aktar |
| Mod `p`'de `p`'nin asal olduğunu denetlememek | Bileşik modülde tersler yoktur, eliminasyon bozulur | `p` asal olmalı |
:::

::: tahmin Bir denklem mi, üç denklem mi?
Gizli vektör `x = (3, 5, 2)`, mod 7. Saldırgan önce bir, sonra üç bağımsız doğrusal denklem görüyor. Kaç aday kalır?

```python
import itertools
p = 7
x = (3, 5, 2)
denklemler = [(1, 1, 1), (1, 2, 3), (2, 0, 1)]
b = [sum(a * xi for a, xi in zip(d, x)) % p for d in denklemler]
for k in (1, 3):
    adaylar = [c for c in itertools.product(range(p), repeat=3)
               if all(sum(a * ci for a, ci in zip(d, c)) % p == b[i] for i, d in enumerate(denklemler[:k]))]
    print(k, len(adaylar))
```

???

```cikti
1 49
3 1
```
Tek denklem 343 olasılığı 49'a indirir; sır hâlâ gizlidir. Üç bağımsız denklem tek bir aday bırakır: sır belirlenmiştir. Kırılmış şemalarda saldırganın elindeki ek yapı bu "fazladan denklemler" rolünü oynadı.
:::

::: gorev 1 · Aday statüsünü güvenlik kanıtı sanma
`aday_karari(kayit)` işlevini yaz.

- `kayit` bir `dict`: `ad` boş olmayan bir `str`, `standard` ve `broken` tam `bool`. Değilse `ValueError`.
- Karar:
  - `broken is True` → `'retire'` (standart olsa bile);
  - değilse `standard is True` → `'standard-review'` ("koşulsuz güvenli" değil; uygulama ve parametre incelemesi sürer);
  - değilse → `'candidate-only'`.

KUSURLU başlangıç önce standart statüsüne bakıyor; kırılmış bir standardı `'standard-review'` diye geçiriyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
Path('ornek.json').write_text('[{"ad": "ornek-sema", "standard": true, "broken": true}]', encoding='utf-8')
```

```starter
def aday_karari(kayit):
    if kayit['standard']:
        return 'standard-review'
    if kayit['broken']:
        return 'retire'
    return 'candidate-only'

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(aday_karari(*_args))
```

```solution
def aday_karari(kayit):
    if (not isinstance(kayit, dict) or not isinstance(kayit.get('ad'), str) or not kayit['ad'].strip()
            or type(kayit.get('standard')) is not bool or type(kayit.get('broken')) is not bool):
        raise ValueError('kayit ad, standard ve broken tasimali')
    if kayit['broken']:
        return 'retire'
    if kayit['standard']:
        return 'standard-review'
    return 'candidate-only'

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(aday_karari(*_args))
```

```test
need('aday_karari')
import copy
_k = lambda ad, s, b: {'ad': ad, 'standard': s, 'broken': b}
_sike = _k('SIKE', False, True)
_yedek = copy.deepcopy(_sike)
eq(aday_karari(_sike), 'retire', 'kırılmış aday emekliye')
eq(_sike, _yedek, 'girdi değişmemeli')
eq(aday_karari(_k('Rainbow', False, True)), 'retire', 'Rainbow da kırılmış aday')
eq(aday_karari(_k('ML-KEM', True, False)), 'standard-review', 'kırılmamış standart: inceleme sürer')
eq(aday_karari(_k('kurgusal-standart', True, True)), 'retire', 'kırılmış standart bile emekliye: kırılma önce denetlenir')
eq(aday_karari(_k('aday-x', False, False)), 'candidate-only', 'kırılmamış aday yalnız aday')
for _bozuk in (None, [], {'standard': True, 'broken': False}, _k('', True, False), _k('  ', True, False), _k(5, True, False),
               _k('a', 1, False), _k('a', True, 0), _k('a', None, False), {'ad': 'a', 'standard': True}):
    raises(ValueError, aday_karari, _bozuk, msg=f'bozuk kayıt ValueError: {_bozuk!r}')
```

```hint
Önce kırılma bilgisine bak; kırılmış bir şema standart olsa da emekliye ayrılır.
```
:::

::: gorev 2 · Açık ek ilişkilerden sırrı çöz (oyuncak, mod p)
`lineer_sir(A, b, p)` işlevini yaz: asal `p` modunda `A · x ≡ b` sistemini çöz ve `x`'i döndür.

- `p` `bool` olmayan bir `int`, `p >= 2` ve **asal** olmalı.
- `A` boş olmayan, kare bir `list` matrisi (`n` satır, her satır `n` öğeli `list`); `b` `n` öğeli bir `list`. Bütün öğeler `bool` olmayan `int` (negatif olabilir; mod `p`'ye indirgenir).
- `A` mod `p`'de tekil ise (çözüm tek değilse) `ValueError`.
- Yöntem: Gauss-Jordan eliminasyonu; her sütunda o satırdan aşağıda sıfır olmayan ilk pivotu seç, satırı pivotun mod `p` tersiyle (`pow(pivot, -1, p)`) çarp, diğer satırlardan çıkar.
- Dönüş: `x` (0..p−1 aralığında `int` listesi). Girdi listelerini değiştirme.

Bu, SIKE ya da Rainbow saldırısının uygulaması değildir.

KUSURLU başlangıç pivotun sıfır olabileceğini düşünmüyor (satır değiştirmiyor) ve `p`'nin asal olduğunu denetlemiyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def lineer_sir(A, b, p):
    n = len(A)
    M = [[v % p for v in A[i]] + [b[i] % p] for i in range(n)]
    for k in range(n):
        ters = pow(M[k][k], -1, p)
        M[k] = [(v * ters) % p for v in M[k]]
        for i in range(n):
            if i != k:
                f = M[i][k]
                M[i] = [(x - f * y) % p for x, y in zip(M[i], M[k])]
    return [M[i][-1] for i in range(n)]
```

```solution
def _asal(p):
    return p >= 2 and all(p % d for d in range(2, int(p ** 0.5) + 1))

def lineer_sir(A, b, p):
    if type(p) is not int or not _asal(p):
        raise ValueError('p asal int olmali')
    if (not isinstance(A, list) or not A or not isinstance(b, list) or len(b) != len(A)
            or any(not isinstance(r, list) or len(r) != len(A) for r in A)
            or any(type(v) is not int for r in A for v in r) or any(type(v) is not int for v in b)):
        raise ValueError('A kare int matrisi, b ayni boyda int listesi olmali')
    n = len(A)
    M = [[v % p for v in A[i]] + [b[i] % p] for i in range(n)]
    for k in range(n):
        pivot = next((i for i in range(k, n) if M[i][k]), None)
        if pivot is None:
            raise ValueError('A mod p tekil')
        M[k], M[pivot] = M[pivot], M[k]
        ters = pow(M[k][k], -1, p)
        M[k] = [(v * ters) % p for v in M[k]]
        for i in range(n):
            if i != k:
                f = M[i][k]
                M[i] = [(x - f * y) % p for x, y in zip(M[i], M[k])]
    return [M[i][-1] for i in range(n)]
```

```test
need('lineer_sir')
import copy, random
_A = [[1, 1, 1], [1, 2, 3], [2, 0, 1]]
_b = [10 % 7, (3 + 10 + 6) % 7, (6 + 2) % 7]
_yedek = copy.deepcopy((_A, _b))
eq(lineer_sir(_A, _b, 7), [3, 5, 2], 'tahmindeki sır üç denklemden çözülür')
eq((_A, _b), _yedek, 'girdiler değişmemeli')
eq(lineer_sir([[0, 1], [1, 0]], [4, 6], 11), [6, 4], 'ilk pivot sıfır: satır değiştirilmeli')
eq(lineer_sir([[0, 0, 1], [0, 1, 0], [1, 0, 0]], [1, 2, 3], 5), [3, 2, 1], 'birden çok satır değişimi')
eq(lineer_sir([[3]], [4], 5), [3], '1×1: 3x ≡ 4 (mod 5) → x = 3')
eq(lineer_sir([[-1, 0], [0, 12]], [-3, 5], 11), [3, 5], 'negatif ve p\'den büyük öğeler mod p\'ye indirgenir')
eq(lineer_sir([[1]], [1], 2), [1], 'en küçük asal p = 2')
_r = random.Random(7)
for _ in range(20):
    _n = _r.randint(1, 5)
    _p = _r.choice([2, 3, 5, 7, 13, 101])
    _x = [_r.randrange(_p) for _ in range(_n)]
    while True:
        _M = [[_r.randrange(-50, 50) for _ in range(_n)] for _ in range(_n)]
        try:
            _bb = [sum(a * xi for a, xi in zip(row, _x)) for row in _M]
            _cozum = lineer_sir(_M, _bb, _p)
            break
        except ValueError:
            continue
    eq(_cozum, _x, f'rastgele {_n}×{_n} sistem mod {_p} doğru çözülür')
for _arg in (([[1, 1], [2, 2]], [1, 2], 7), ([[2, 1], [4, 2]], [1, 2], 5), ([[0]], [1], 3),
             ([[1, 0], [0, 1]], [1, 1], 4), ([[1]], [1], 1), ([[1]], [1], 9), ([[1]], [1], True), ([[1]], [1], 7.0),
             ([], [], 7), ([[1, 2]], [1], 7), ([[1], [2]], [1, 2], 7), ([[1, 0], [0]], [1, 1], 7), ([[1]], [1, 2], 7),
             ([[True]], [1], 7), ([[1]], [1.0], 7), ((( 1,),), [1], 7), ([[1]], (1,), 7),
             (([1],), [1], 7), ([(1,)], [1], 7), ([[1]], [1], 0), ([[1]], [1], -3)):
    raises(ValueError, lineer_sir, *_arg, msg=f'bozuk ya da tekil sistem ValueError: {_arg!r}')
```

```hint
Her sütunda pivotu `next((i for i in range(k, n) if M[i][k]), None)` ile ara; bulamazsan matris tekildir. Bulursan satırları değiştir, pivotu `pow(pivot, -1, p)` ile 1 yap ve diğer satırlardan çıkar.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **İki kırılma (30 sn).** "NIST sürecinde ileri turlara kalmış iki aday 2022'de klasik bilgisayarla kırıldı: SIKE için Castryck ve Decru'nun saldırısı SIKEp434'te tek çekirdekte yaklaşık on dakika, Rainbow için Beullens'in saldırısı bir dizüstünde ortalama 53 saat."
2. **Etiketin anlamı (20 sn).** "'Kuantum sonrası' bir dayanıklılık iddiası; klasik saldırılara karşı kanıt değil. Aday statüsü de garanti değil."
3. **Karar kuralı (20 sn).** "Kurala önce kırılma bilgisini koyduk; kırılmış bir şema standart olsa bile emekliye ayrılıyor."
4. **Yapı sırrı ele verir (35 sn).** "Oyuncak bir modelde tek denklem 343 olasılığı 49'a indirdi, üç bağımsız denklem sırrı tek değere bağladı ve Gauss eliminasyonuyla çözdük. Kırılan şemalarda yayımlanan ek yapı bu fazladan denklemlerin rolünü oynadı."
5. **Sınır (15 sn).** "Gerçek saldırılar doğrusal değildi; bu yalnız fikrin en sade gösterimi."
:::

::: anlat Sınır ve kaynak
Bu ders gerçek bir SIKE ya da Rainbow saldırısı çalıştırmaz. Görev 1 kamuya açık statü bilgisini kodlar; görev 2 küçük bir sonlu cisimde doğrusal cebirdir. Kaynaklardaki süreler belirli parametreler ve donanım içindir; başka ortamlara genellenmez ve burada kıyaslama olarak sunulmaz. İzojen ve çok değişkenli kriptografinin kırılmamış başka şemaları bu kırılmalardan otomatik olarak etkilenmez; her şema kendi analiziyle değerlendirilir.

- Birincil kaynaklar: [Castryck, Decru — An efficient key recovery attack on SIDH (IACR ePrint 2022/975)](https://eprint.iacr.org/2022/975) (SIKEp434 için tek çekirdekte yaklaşık on dakika); [Beullens — Breaking Rainbow Takes a Weekend on a Laptop (IACR ePrint 2022/214)](https://eprint.iacr.org/2022/214) (SL 1 için standart dizüstünde ortalama 53 saat). Doğrulama tarihi: 11 Kasım 2026.
:::

::: dusun
Bir kurum 2021'de "en verimli kuantum sonrası KEM" diye SIKE'ı seçmiş olsaydı, 2022'deki kırılma onu nasıl etkilerdi? Hibrit anahtar değişimi (`kuantum-23`) bu senaryoda kurumu neden korurdu?
:::

::: ozet
- SIKE ve Rainbow 2022'de klasik saldırılarla kırıldı; "kuantum sonrası" etiketi klasik güvenliğin kanıtı değildir.
- Aday ya da standart statüsü güvenlik garantisi değildir; karar kuralında kırılma bilgisi önce gelir.
- Açık ek yapı, gizli değeri kısıtlayan fazladan denklemler gibi çalışabilir.
- Asal modda bağımsız `n` doğrusal denklem `n` bilinmeyenli sırrı tek olarak belirler.
:::
