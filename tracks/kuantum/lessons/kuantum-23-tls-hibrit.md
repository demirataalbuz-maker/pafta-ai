---
id: kuantum-23
title: "TLS 1.3 Hibrit Key Exchange · Byte Sırası ve Key Schedule"
summary: RFC 10024'teki X25519MLKEM768 key_exchange alanlarını doğru sırayla ayır; gerçek ML-KEM-768 ve X25519 değişiminden gelen iki sırrı birleştirip HKDF-Extract çekirdeğinden geçir ve iki tarafın aynı sonuca vardığını gör.
esleme: kuantum-21, kuantum-24, kuantum-28, kuantum-22
timeout: 30
---

::: anlat 1. Hibrit: biri kırılsa da diğeri tutsun
Kuantum sonrası geçişin ilk adımı çoğu yerde **hibrit** anahtar değişimidir: klasik bir eliptik eğri değişimi (X25519) ile kuantum sonrası bir KEM (ML-KEM-768) aynı el sıkışmada birlikte çalışır ve iki sır birleştirilir. Amaç, iki bileşenden biri kırılsa bile oturum anahtarının güvende kalmasıdır. Bugün kaydedilen trafiğin ileride kuantum bilgisayarla çözülmesi ("şimdi topla, sonra çöz") riskine karşı ML-KEM, ML-KEM'de ileride bulunabilecek bir zayıflığa karşı da X25519 korur.

Ağustos 2026'da yayımlanan **RFC 10024**, TLS 1.3 için bu hibrit grupları tanımlar: `X25519MLKEM768` ve `SecP256r1MLKEM768`. `X25519MLKEM768` için:

- **İstemci payı** (`key_exchange`, ClientHello): 1216 bayt = 1184 bayt ML-KEM-768 encapsulation key **ardından** 32 bayt X25519 açık anahtarı.
- **Sunucu payı** (ServerHello): 1120 bayt = 1088 bayt ML-KEM-768 ciphertext **ardından** 32 bayt X25519 açık anahtarı.
- **Ortak sır**: ML-KEM ortak sırrı (32 bayt) **ardından** X25519 ortak sırrı (32 bayt), toplam 64 bayt.

Adı X25519 ile başladığı hâlde ML-KEM alanı önce gelir. RFC bunun adlandırma kuralına uymadığını ve *"historical reasons"* yüzünden böyle olduğunu açıkça yazar. Sırayı addan tahmin eden bir ayrıştırıcı yanlış baytları yanlış algoritmaya verir.

> [!NOTE]
> Bu derste canlı TLS oturumu ya da ağ yakalaması yoktur. Testler payları **gerçek** ML-KEM-768 ve X25519 anahtarlarıyla (yerel `cryptography` 50.0.0) üretir; boyutlar bu kurulumda ölçülmüştür. Tam el sıkışma, sertifika zinciri ve trafik anahtarları üretilmez.
:::

::: anlat 2. Mekanizma: iki pay, iki farklı veri
İstemci ve sunucu payları aynı uzunlukta değildir, çünkü aynı tür veri değildir. İstemci bir **encapsulation key** gönderir (1184 bayt). Sunucu bu anahtarla `encapsulate()` çağırır ve bir **ciphertext** döndürür (1088 bayt). X25519 tarafında ise iki taraf da 32 baytlık açık anahtar gönderir. Bu yüzden ayrıştırıcı rolü bilmelidir: aynı 32 baytlık kuyruk iki rolde de X25519'dur, ama önündeki blok rolden role değişir.

Birleşik sır daha sonra TLS 1.3 anahtar takviminde HKDF'nin *extract* adımına girer: `HKDF-Extract(salt, IKM) = HMAC-Hash(salt, IKM)`. Burada IKM, `mlkem_sir || x25519_sir` dizgesidir. Sıra değişirse iki taraf farklı anahtar türetir ve el sıkışma `Finished` doğrulamasında düşer. Daha kötüsü, iki tarafı da aynı yanlış sırayla yazılmış iki uygulama birbiriyle konuşur ama standartla konuşamaz.

Bu derste salt, doğru hesaplanmış bir TLS *derived secret*'ı olarak verilmiş kabul edilir; erken sır, transcript bağlamı ve kimlik doğrulaması kapsam dışıdır.

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| Addan sıra çıkarmak: önce X25519 | RFC'de ML-KEM alanı önce | İstemci `1184 + 32`, sunucu `1088 + 32` |
| Rolü bilmeden ayırmak | İstemci ve sunucu payı farklı tür ve uzunlukta | Rol + tam uzunluk denetimi |
| Sırları `x25519 || mlkem` birleştirmek | Taraflar farklı anahtar türetir | `mlkem_sir || x25519_sir` |
| Teklif edilen grubu seçilmiş sanmak | ClientHello'daki liste anlaşma değildir | Seçileni ServerHello gösterir (`kuantum-24`) |
| "İki algoritmadan biri sağlamsa her birleştirme güvenli" | Birleştirme yöntemi ve protokol bağlamı da önemlidir | Standartta tanımlı birleştirmeyi kullan |
:::

::: tahmin Sıra değişince anahtar değişir mi?
Aynı iki 32 baytlık sır, aynı salt ile iki farklı sırada birleştirilip HMAC-SHA256'dan geçiriliyor. Sonuçlar eşit mi?

```python
import hashlib, hmac
salt = bytes(32)
mlkem_sir = bytes(range(32))
x_sir = bytes(range(32, 64))
dogru = hmac.new(salt, mlkem_sir + x_sir, hashlib.sha256).digest()
ters = hmac.new(salt, x_sir + mlkem_sir, hashlib.sha256).digest()
print(len(dogru), dogru == ters)
```

???

```cikti
32 False
```
Aynı malzeme, farklı sıra, bambaşka bir anahtar. Taraflardan biri sırayı ters yazarsa el sıkışma `Finished` doğrulamasında düşer.
:::

::: gorev 1 · X25519MLKEM768 paylarını role göre ayır
`hibrit_share(rol, data)` işlevini yaz.

- `rol` `'client'` ya da `'server'`; `data` `bytes`.
- İstemci: tam 1216 bayt; dönüş `(data[:1184], data[1184:])` = (ML-KEM encapsulation key, X25519 açık anahtarı).
- Sunucu: tam 1120 bayt; dönüş `(data[:1088], data[1088:])` = (ML-KEM ciphertext, X25519 açık anahtarı).
- Bozuk rol, tür ya da uzunluk `ValueError`. Girdi tam ClientHello değil, yalnız `key_exchange` alanıdır.

KUSURLU başlangıç X25519'u önce sanıyor ve rolü yok sayıyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def hibrit_share(rol, data):
    return data[32:], data[:32]
```

```solution
_MLKEM = {'client': 1184, 'server': 1088}

def hibrit_share(rol, data):
    if not isinstance(rol, str) or rol not in _MLKEM or type(data) is not bytes or len(data) != _MLKEM[rol] + 32:
        raise ValueError('rol client/server, data dogru uzunlukta bytes olmali')
    kes = _MLKEM[rol]
    return data[:kes], data[kes:]
```

```test
need('hibrit_share')
from cryptography.hazmat.primitives.asymmetric.mlkem import MLKEM768PrivateKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives import serialization as S
_R = (S.Encoding.Raw, S.PublicFormat.Raw)
for _ in range(3):
    _kem = MLKEM768PrivateKey.generate()
    _ek = _kem.public_key().public_bytes(*_R)
    _xc = X25519PrivateKey.generate().public_key().public_bytes(*_R)
    eq(hibrit_share('client', _ek + _xc), (_ek, _xc), 'istemci: önce 1184 bayt encapsulation key, sonra 32 bayt X25519')
    _ss, _ct = _kem.public_key().encapsulate()
    _xs = X25519PrivateKey.generate().public_key().public_bytes(*_R)
    eq(hibrit_share('server', _ct + _xs), (_ct, _xs), 'sunucu: önce 1088 bayt ciphertext, sonra 32 bayt X25519')
_c = bytes(range(256)) * 4 + bytes(range(192))
eq([len(x) for x in hibrit_share('client', _c)], [1184, 32], 'istemci parça uzunlukları')
eq([len(x) for x in hibrit_share('server', _c[:1120])], [1088, 32], 'sunucu parça uzunlukları')
for _rol, _veri in (('client', _c[:1215]), ('client', _c + b'\x00'), ('client', _c[:1120]), ('server', _c),
                    ('server', _c[:1119]), ('Client', _c), (None, _c), (['client'], _c), ('client', bytearray(_c)), ('client', _c.hex())):
    raises(ValueError, hibrit_share, _rol, _veri, msg=f'bozuk rol/veri ValueError: {_rol!r}, {type(_veri).__name__}, {len(_veri)}')
```

```hint
Role göre ML-KEM bloğunun uzunluğunu bir sözlükten al; toplam uzunluk bu değer + 32 olmalı. Kesme noktası ML-KEM bloğunun sonudur.
```
:::

::: gorev 2 · Birleşik sır ile HKDF-Extract çekirdeği
`hibrit_extract(salt, pq_secret, x_secret)` işlevini yaz.

- Üç argüman da tam 32 baytlık `bytes` olmalı; değilse `ValueError`.
- Dönüş: `HMAC-SHA256(salt, pq_secret || x_secret)` (`hmac.new(salt, pq_secret + x_secret, hashlib.sha256).digest()`).

Test, gerçek bir ML-KEM-768 + X25519 değişimini iki taraf için ayrı ayrı yürütür ve iki tarafın aynı 32 baytlık çıktıya ulaştığını, sıra ters çevrilince ulaşamadığını sınar.

KUSURLU başlangıç sırları ters sırayla birleştiriyor ve uzunluk denetimi yapmıyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
import hashlib, hmac

def hibrit_extract(salt, pq_secret, x_secret):
    return hmac.new(salt, x_secret + pq_secret, hashlib.sha256).digest()
```

```solution
import hashlib, hmac

def hibrit_extract(salt, pq_secret, x_secret):
    if any(type(x) is not bytes or len(x) != 32 for x in (salt, pq_secret, x_secret)):
        raise ValueError('salt, pq_secret ve x_secret 32 baytlik bytes olmali')
    return hmac.new(salt, pq_secret + x_secret, hashlib.sha256).digest()
```

```test
need('hibrit_extract')
import hashlib, hmac, os
from cryptography.hazmat.primitives.asymmetric.mlkem import MLKEM768PrivateKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
for _ in range(3):
    _salt = os.urandom(32)
    _kem = MLKEM768PrivateKey.generate()
    _ss_sunucu, _ct = _kem.public_key().encapsulate()
    _ss_istemci = _kem.decapsulate(_ct)
    _xi, _xs = X25519PrivateKey.generate(), X25519PrivateKey.generate()
    _x_istemci = _xi.exchange(_xs.public_key())
    _x_sunucu = _xs.exchange(_xi.public_key())
    _ki = hibrit_extract(_salt, _ss_istemci, _x_istemci)
    _ks = hibrit_extract(_salt, _ss_sunucu, _x_sunucu)
    eq((len(_ki), _ki == _ks), (32, True), 'gerçek değişimde iki taraf aynı 32 baytlık çıktıya ulaşır')
    eq(_ki, hmac.new(_salt, _ss_istemci + _x_istemci, hashlib.sha256).digest(), 'HMAC-SHA256(salt, mlkem || x25519)')
    ok(_ki != hmac.new(_salt, _x_istemci + _ss_istemci, hashlib.sha256).digest(), 'ters sıra farklı anahtar')
    ok(_ki != hibrit_extract(os.urandom(32), _ss_istemci, _x_istemci), 'farklı salt farklı anahtar')
_b = bytes(32)
for _arg in ((bytes(31), _b, _b), (_b, bytes(33), _b), (_b, _b, b''), (bytearray(32), _b, _b), (_b, None, _b), (_b, _b, 'x' * 32)):
    raises(ValueError, hibrit_extract, *_arg, msg='32 baytlık bytes dışı girdi ValueError')
```

```hint
Üç girdiyi tek döngüde doğrula. Birleştirme sırası RFC'deki gibidir: önce kuantum sonrası (ML-KEM) sır, sonra X25519 sırrı.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Hibrit (20 sn).** "TLS'te X25519 ile ML-KEM-768'i aynı el sıkışmada çalıştırıyoruz. Biri kırılsa diğeri oturumu koruyor."
2. **Bayt sırası (30 sn).** "RFC 10024'e göre grup adı X25519 ile başlasa da tarihsel nedenle ML-KEM alanı önce gelir. İstemci 1184 baytlık encapsulation key ile 32 baytlık X25519 anahtarı, sunucu 1088 baytlık ciphertext ile 32 bayt gönderir."
3. **Gerçek değişim (30 sn).** "Testte payları gerçek ML-KEM ve X25519 anahtarlarıyla ürettik ve ayırdık. Sonra iki tarafın sırlarını ML-KEM önce olacak şekilde birleştirip HMAC'ten geçirdik; iki taraf aynı 32 bayta vardı."
4. **Sıra hatası (25 sn).** "Sırayı ters yazınca anahtar tamamen değişti. Gerçek bağlantıda bu, Finished doğrulamasında düşen bir el sıkışma demek."
5. **Sınır (15 sn).** "Yalnız extract çekirdeği; tam anahtar takvimi, transcript ve sertifika doğrulaması kapsam dışı."
:::

::: anlat Sınır ve kaynak
Bu ders `key_exchange` alanının ayrıştırılmış olduğunu varsayar ve TLS kaydını, uzantı çerçevesini ya da el sıkışma transcript'ini işlemez. Gerçek bir uygulama ayrıca X25519 sonucunun sıfır olmadığını, ML-KEM encapsulation key'inin standarttaki denetimleri geçtiğini doğrular ve sırrı transcript'e bağlı tam anahtar takviminden geçirir. `SecP256r1MLKEM768` grubu ve kimlik doğrulama bu derste işlenmez.

- Birincil kaynaklar: [IETF RFC 10024 — Post-Quantum Traditional (PQ/T) Hybrid Key Agreement Mechanisms for TLS 1.3 (Ağustos 2026)](https://www.rfc-editor.org/rfc/rfc10024.html) (`X25519MLKEM768` pay boyutları ve sırası, "historical reasons" notu, ortak sır birleştirmesi, `SecP256r1MLKEM768`); [pyca/cryptography — ML-KEM](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/mlkem/). Doğrulama tarihi: 11 Kasım 2026.
:::

::: dusun
Bir sunucu ClientHello'da hem `X25519MLKEM768` hem klasik `x25519` grubunu görüyor ve klasik olanı seçiyor. Bağlantı kuruluyor ve şifreli. Bu oturumun "şimdi topla, sonra çöz" saldırısına karşı durumu nedir? Bunu ağ kaydından nasıl fark ederdin?
:::

::: ozet
- `X25519MLKEM768`'de ML-KEM alanı önce gelir; istemci payı `1184 + 32`, sunucu payı `1088 + 32` bayttır.
- İstemci encapsulation key, sunucu ciphertext gönderir; ayrıştırıcı rolü bilmelidir.
- Ortak sır `mlkem_sir || x25519_sir` olarak birleştirilir ve HKDF-Extract'ten (`HMAC(salt, IKM)`) geçer.
- Sıra değişirse iki taraf farklı anahtar türetir.
:::
