---
id: kuantum-22
title: "ML-DSA ve SLH-DSA · İmza, Context ve Maliyet"
summary: Kurulu kitaplıkla gerçek ML-DSA-44 imzası üret ve context dizgesiyle alan ayrımını (domain separation) gözle; imza ailelerini açık anahtar ve imza boyutunun mesaj sayısıyla nasıl büyüdüğüne göre karşılaştır.
esleme: kuantum-21, kuantum-28, kuantum-24, kuantum-26
timeout: 30
---

::: anlat 1. İki imza ailesi, iki farklı bedel
NIST, 13 Ağustos 2024'te iki kuantum sonrası imza standardı yayımladı: **FIPS 204** ile kafes tabanlı ML-DSA ve **FIPS 205** ile durumsuz (*stateless*), karma tabanlı SLH-DSA. İkisi farklı varsayımlara dayanır. ML-DSA kafes problemlerinin zorluğuna, SLH-DSA yalnız karma işlevlerinin güvenliğine dayanır. İki aile farklı boyut ve hız profilleri taşır.

Bu derste kurulu `cryptography` 50.0.0 kitaplığının ML-DSA-44 uygulaması kullanılır. Bu makinede ölçülen boyutlar: **açık anahtar 1312 bayt, imza 2420 bayt**. Karşılaştırma için: klasik bir Ed25519 imzası 64 bayttır. SLH-DSA bu makinede kurulu değildir; boyutları bu derste ölçülmez ve verilmez. Karşılaştırma için FIPS 205'teki parametre tablosuna bakılır.

İmza doğrulaması iki şeyi gösterir: mesajın değişmediğini ve imzanın bu açık anahtara karşılık gelen özel anahtarla üretildiğini. Açık anahtarın gerçekten iddia edilen kuruma ait olduğunu göstermez; bunu güven zinciri (sertifika) gösterir.

> [!NOTE]
> Görev 1 **gerçek** ML-DSA-44 imzası üretir ve doğrular. Görev 2'deki hız değerleri ve profil boyutları kullanıcının girdiği **sentetik** sayılardır; bir kıyaslama (*benchmark*) ya da standart değer iddiası yoktur.
:::

::: anlat 2. Mekanizma: context neden var?
ML-DSA imzalama işlemi mesajın yanında bir **context** dizgesi alır. Kitaplık belgesi bu dizgenin **en çok 255 bayt** olabileceğini yazar; bu makinede 256 baytlık context `ValueError` verdi. Context, imzanın hangi amaç için atıldığını imzanın içine bağlar (*domain separation*). Aynı mesaj ve aynı anahtarla `b'yazilim-guncelleme'` context'iyle atılmış bir imza, `b'sozlesme-onayi'` context'iyle doğrulanmaz. Böylece bir protokolde toplanmış imza başka bir protokolde yeniden kullanılamaz.

Boyut tarafında sezgi yanıltıcıdır. Küçük açık anahtar, toplam trafiğin küçük olduğu anlamına gelmez. Açık anahtar bir kez gönderilir; imza her mesajda gider. `adet` mesaj için toplam bayt `pk + adet × sig` olur. Mesaj sayısı arttıkça imza boyutu baskınlaşır. Bir sertifika zincirinde (bir kez imzalanır, çok kez doğrulanır) ve bir günlük akışında (her kayıt imzalanır) aynı aile farklı sonuç verir.

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| Context'i atlamak | Bir protokolün imzası başka bir protokolde geçerli olur | Her kullanım amacına ayrı context |
| 255 bayttan uzun context | Standart dışı; kitaplık reddeder | `len(context) <= 255` |
| `str` ya da `bytearray` mesajı sessizce kabul etmek | Kodlama belirsizliği; aynı metin farklı baytlar olabilir | Yalnız `bytes` |
| "Küçük açık anahtar = küçük trafik" | Çok mesajda imza boyutu baskındır | `pk + adet × sig` |
| İmza doğrulandı = anahtar doğru kuruma ait | Doğrulama kimlik bağını kanıtlamaz | Güven zinciri ayrıca gerekir |
:::

::: tahmin Aynı mesaj, farklı context
Aynı anahtar ve aynı mesajla atılan imza, imzalarken kullanılan context ile ve başka bir context ile doğrulanıyor. Sonuç ne olur?

```python
from cryptography.hazmat.primitives.asymmetric.mldsa import MLDSA44PrivateKey
from cryptography.exceptions import InvalidSignature

anahtar = MLDSA44PrivateKey.generate()
imza = anahtar.sign(b'surum 2.4.1', context=b'yazilim-guncelleme')
for ctx in (b'yazilim-guncelleme', b'sozlesme-onayi'):
    try:
        anahtar.public_key().verify(imza, b'surum 2.4.1', context=ctx)
        print(ctx.decode(), '-> gecerli')
    except InvalidSignature:
        print(ctx.decode(), '-> gecersiz')
```

???

```cikti
yazilim-guncelleme -> gecerli
sozlesme-onayi -> gecersiz
```
Mesaj ve anahtar aynı; değişen tek şey context. İmza, atıldığı amaca bağlıdır ve başka amaçla yeniden kullanılamaz.
:::

::: gorev 1 · Gerçek ML-DSA imzası ve alan ayrımı
`imza_uret(private_key, message, context)` işlevini yaz.

- `message` ve `context` tam olarak `bytes` olmalı (`str`, `bytearray` değil); `len(context) <= 255`. Değilse `ValueError` (kitaplığa gitmeden önce).
- İmza: `private_key.sign(message, context=context)`; `bytes` olarak döndür.

Test her denemede yeni bir anahtar ve rastgele mesajla gerçek doğrulama yapar: doğru context ile geçer; context'siz, başka context'le, başka mesajla ya da başka açık anahtarla reddedilir.

KUSURLU başlangıç context'i imzaya hiç katmıyor ve girdileri doğrulamıyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def imza_uret(private_key, message, context):
    return private_key.sign(message)

if __name__ == '__main__':
    from cryptography.hazmat.primitives.asymmetric.mldsa import MLDSA44PrivateKey
    from cryptography.exceptions import InvalidSignature
    _k = MLDSA44PrivateKey.generate()
    _s = imza_uret(_k, b'PAFTA-sentetik-mesaj', b'PAFTA-ders')
    try:
        _k.public_key().verify(_s, b'PAFTA-sentetik-mesaj', context=b'PAFTA-ders')
        print({'imza_bayt': len(_s), 'dogrulandi': True})
    except InvalidSignature:
        print({'imza_bayt': len(_s), 'dogrulandi': False})
```

```solution
def imza_uret(private_key, message, context):
    if type(message) is not bytes or type(context) is not bytes or len(context) > 255:
        raise ValueError('message ve context bytes olmali, context <= 255 bayt')
    return private_key.sign(message, context=context)

if __name__ == '__main__':
    from cryptography.hazmat.primitives.asymmetric.mldsa import MLDSA44PrivateKey
    from cryptography.exceptions import InvalidSignature
    _k = MLDSA44PrivateKey.generate()
    _s = imza_uret(_k, b'PAFTA-sentetik-mesaj', b'PAFTA-ders')
    try:
        _k.public_key().verify(_s, b'PAFTA-sentetik-mesaj', context=b'PAFTA-ders')
        print({'imza_bayt': len(_s), 'dogrulandi': True})
    except InvalidSignature:
        print({'imza_bayt': len(_s), 'dogrulandi': False})
```

```test
need('imza_uret')
import secrets
from cryptography.hazmat.primitives.asymmetric.mldsa import MLDSA44PrivateKey
from cryptography.exceptions import InvalidSignature

def _gecerli(pk, s, m, c):
    try:
        pk.verify(s, m, context=c)
        return True
    except InvalidSignature:
        return False

_baska = MLDSA44PrivateKey.generate().public_key()
for _ in range(4):
    _k = MLDSA44PrivateKey.generate()
    _m = secrets.token_bytes(24)
    _c = b'PAFTA-ders'
    _s = imza_uret(_k, _m, _c)
    eq((type(_s), len(_s)), (bytes, 2420), 'ML-DSA-44 imzası 2420 bayt')
    eq(_gecerli(_k.public_key(), _s, _m, _c), True, 'doğru anahtar, mesaj ve context ile geçerli')
    eq(_gecerli(_k.public_key(), _s, _m, b''), False, 'context\'siz doğrulama reddedilir')
    eq(_gecerli(_k.public_key(), _s, _m, b'PAFTA-baska'), False, 'başka context reddedilir')
    eq(_gecerli(_k.public_key(), _s, _m + b'!', _c), False, 'değişmiş mesaj reddedilir')
    eq(_gecerli(_baska, _s, _m, _c), False, 'başka açık anahtar reddedilir')
_k = MLDSA44PrivateKey.generate()
_s255 = imza_uret(_k, b'm', b'x' * 255)
eq(_gecerli(_k.public_key(), _s255, b'm', b'x' * 255), True, '255 baytlık context geçerli')
_s0 = imza_uret(_k, b'', b'')
eq(_gecerli(_k.public_key(), _s0, b'', b''), True, 'boş mesaj ve boş context geçerli')

class _Sayac:
    cagri = 0
    def sign(self, m, context=None):
        _Sayac.cagri += 1
        return b'imza'
for _arg in ((b'm', b'x' * 256), ('m', b'c'), (b'm', 'c'), (bytearray(b'm'), b'c'), (b'm', bytearray(b'c')), (None, b'c')):
    raises(ValueError, imza_uret, _Sayac(), *_arg, msg=f'bozuk girdi ValueError: {type(_arg[0]).__name__}, {type(_arg[1]).__name__}, {len(_arg[1]) if _arg[1] is not None else None}')
eq(_Sayac.cagri, 0, 'bozuk girdi kitaplığa hiç gitmez')
```

```hint
Türü `type(x) is bytes` ile denetle (`bytearray` de `bytes` gibi davranır ama farklı türdür). Context'i anahtar sözcük argümanı olarak ver: `sign(message, context=context)`.
```
:::

::: gorev 2 · Boyutun mesaj sayısıyla büyümesi
`imza_maliyeti(profiller, adet)` işlevini yaz.

- `adet` `bool` olmayan, `>= 0` bir `int`. `profiller` bir `list`; her profil `{'ad': str, 'pk': int, 'sig': int, 'sign_us': int}`. `ad` boş olmayan ve benzersiz; `pk` ve `sig` `bool` olmayan pozitif `int`; `sign_us` `bool` olmayan, `>= 0` `int`. Değilse `ValueError`.
- Her profil için `[ad, pk + adet * sig, adet * sign_us]`: toplam bayt (açık anahtar bir kez, imza her mesajda) ve toplam imzalama süresi (mikrosaniye).
- Dönüş: girdi sırasıyla liste.

KUSURLU başlangıç açık anahtarı her mesajda yeniden sayıyor ve sıfır boyutlu profili kabul ediyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
Path('ornek.json').write_text('[[{"ad": "kafes-44", "pk": 1312, "sig": 2420, "sign_us": 100}, {"ad": "karma-kucuk-anahtar", "pk": 32, "sig": 8000, "sign_us": 1000}], 1]', encoding='utf-8')
```

```starter
def imza_maliyeti(profiller, adet):
    return [[p['ad'], adet * (p['pk'] + p['sig']), adet * p['sign_us']] for p in profiller]

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(imza_maliyeti(*_args))
```

```solution
def _poz(x, alt):
    return type(x) is int and x >= alt

def imza_maliyeti(profiller, adet):
    if not isinstance(profiller, list) or not _poz(adet, 0):
        raise ValueError('profiller list, adet >= 0 int olmali')
    gorulen = set()
    sonuc = []
    for p in profiller:
        if (not isinstance(p, dict) or not isinstance(p.get('ad'), str) or not p['ad'].strip()
                or not _poz(p.get('pk'), 1) or not _poz(p.get('sig'), 1) or not _poz(p.get('sign_us'), 0)):
            raise ValueError('bozuk profil')
        if p['ad'] in gorulen:
            raise ValueError('yinelenen ad')
        gorulen.add(p['ad'])
        sonuc.append([p['ad'], p['pk'] + adet * p['sig'], adet * p['sign_us']])
    return sonuc

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(imza_maliyeti(*_args))
```

```test
need('imza_maliyeti')
import copy
_P = [{'ad': 'kafes-44', 'pk': 1312, 'sig': 2420, 'sign_us': 100},
      {'ad': 'karma-kucuk-anahtar', 'pk': 32, 'sig': 8000, 'sign_us': 1000}]
_yedek = copy.deepcopy(_P)
eq(imza_maliyeti(_P, 1), [['kafes-44', 3732, 100], ['karma-kucuk-anahtar', 8032, 1000]], 'tek mesaj')
eq(imza_maliyeti(_P, 1000), [['kafes-44', 2421312, 100000], ['karma-kucuk-anahtar', 8000032, 1000000]],
   'bin mesajda imza boyutu baskın; küçük açık anahtar kazandırmaz')
eq(imza_maliyeti(_P, 0), [['kafes-44', 1312, 0], ['karma-kucuk-anahtar', 32, 0]], 'mesaj yoksa yalnız açık anahtar')
eq(_P, _yedek, 'girdi değişmemeli')
eq(imza_maliyeti([], 5), [], 'profil yoksa boş liste')
eq(imza_maliyeti([{'ad': 'a', 'pk': 1, 'sig': 1, 'sign_us': 0}], 3), [['a', 4, 0]], 'en küçük geçerli değerler')
for _adet in (-1, True, 1.0, '3', None):
    raises(ValueError, imza_maliyeti, _P, _adet, msg=f'bozuk adet ValueError: {_adet!r}')
raises(ValueError, imza_maliyeti, tuple(_P), 1, msg='liste olmayan profiller ValueError')
_iyi = {'ad': 'a', 'pk': 10, 'sig': 10, 'sign_us': 10}
for _alan, _deger in (('ad', ''), ('ad', '  '), ('ad', 5), ('pk', 0), ('pk', -1), ('pk', True), ('pk', 10.0),
                      ('sig', 0), ('sig', None), ('sign_us', -1), ('sign_us', 1.5), ('sign_us', False)):
    raises(ValueError, imza_maliyeti, [dict(_iyi, **{_alan: _deger})], 1, msg=f'bozuk profil ValueError: {_alan}={_deger!r}')
raises(ValueError, imza_maliyeti, [_iyi, dict(_iyi)], 1, msg='yinelenen ad ValueError')
raises(ValueError, imza_maliyeti, ['kafes-44'], 1, msg='dict olmayan profil ValueError')
```

```hint
Açık anahtar bir kez gönderilir, imza her mesajda: `pk + adet * sig`. `bool` bir `int` alt türüdür; `type(x) is int` ile ele.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **İki aile (20 sn).** "NIST 2024'te kafes tabanlı ML-DSA'yı ve karma tabanlı SLH-DSA'yı standartlaştırdı. Farklı varsayımlar, farklı boyutlar."
2. **Gerçek imza (25 sn).** "Bu makinede ML-DSA-44 imzası ürettik: açık anahtar 1312, imza 2420 bayt. Ed25519 imzası 64 bayttı; fark otuz katın üstünde."
3. **Context (30 sn).** "Aynı mesajı yazılım güncellemesi context'iyle imzaladık. Sözleşme onayı context'iyle doğrulanmadı. 255 baytı aşan context kitaplıkta reddediliyor; biz kitaplığa gitmeden reddettik."
4. **Boyut ekonomisi (30 sn).** "Açık anahtar bir kez, imza her mesajda gider. Bin mesajda küçük açık anahtarlı ama büyük imzalı profil üç kat daha fazla bayt taşıdı."
5. **Sınır (15 sn).** "Hızlar sentetik; SLH-DSA bu makinede çalıştırılmadı, boyutları standarttaki tablodan okunur."
:::

::: anlat Sınır ve kaynak
Görev 1 bu makinedeki `cryptography` 50.0.0 kurulumuyla gerçek ML-DSA-44 işlemi yapar; boyutlar bu kurulumda ölçülmüştür. SLH-DSA için kitaplık kurulmaz ve çalıştırılmaz; görev 2'deki profil sayıları sentetik girdilerdir. Hız kıyaslaması yapılmaz; gerçek hızlar donanıma, kitaplığa ve parametre kümesine bağlıdır. İmza doğrulaması açık anahtarın kime ait olduğunu kanıtlamaz.

- Birincil kaynaklar: [NIST FIPS 204 — Module-Lattice-Based Digital Signature Standard (13 Ağustos 2024)](https://csrc.nist.gov/pubs/fips/204/final); [NIST FIPS 205 — Stateless Hash-Based Digital Signature Standard (13 Ağustos 2024)](https://csrc.nist.gov/pubs/fips/205/final); [pyca/cryptography — ML-DSA signing](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/mldsa/) (`sign(data, context=None)`, context en çok 255 bayt). Doğrulama tarihi: 11 Kasım 2026.
:::

::: dusun
Bir firmware güncelleme sistemi yılda bir kez imzalanan, milyonlarca cihazda doğrulanan paketler kullanıyor. Bir günlük sistemi ise saniyede binlerce kaydı ayrı ayrı imzalıyor. Görev 2'nin maliyet modeli hangisinde açık anahtar boyutunu, hangisinde imza boyutunu öne çıkarır? Doğrulama süresi bu modele nasıl eklenirdi?
:::

::: ozet
- ML-DSA (FIPS 204) kafes tabanlı, SLH-DSA (FIPS 205) durumsuz karma tabanlıdır.
- Bu makinede ML-DSA-44: açık anahtar 1312, imza 2420 bayt.
- Context imzayı amacına bağlar; en çok 255 bayttır ve başka context'le doğrulama başarısız olur.
- Toplam bayt `pk + adet × sig`'dir; çok mesajda imza boyutu baskınlaşır.
:::
