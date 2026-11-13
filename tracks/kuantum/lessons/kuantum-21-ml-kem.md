---
id: kuantum-21
title: "ML-KEM · Anahtar Üretimi, Encapsulation ve Implicit Rejection"
summary: Kurulu kitaplıkla gerçek ML-KEM-768 encapsulation/decapsulation akışını çalıştır, bozuk ciphertext'e verilen yanıtı gözle ve sıfır hata gözleminin olasılık hakkında ne söyleyip ne söyleyemeyeceğini üst sınırla hesapla.
esleme: kuantum-22, kuantum-23, kuantum-25, kuantum-28
timeout: 30
---

::: anlat 1. KEM bir şifreleme API'si değildir
NIST, 13 Ağustos 2024'te FIPS 203 ile ML-KEM'i (*Module-Lattice-Based Key-Encapsulation Mechanism*) standartlaştırdı; standart üç parametre kümesi tanımlar: ML-KEM-512, ML-KEM-768, ML-KEM-1024. Bir KEM bir mesajı şifrelemez. İş akışı şöyledir:

1. Alıcı bir anahtar çifti üretir ve **encapsulation key**'ini (açık anahtar) yayımlar.
2. Gönderici bu anahtarla `encapsulate()` çağırır: bir **ciphertext** ve bir **ortak sır** (*shared secret*) çıkar. Ciphertext alıcıya gider.
3. Alıcı **decapsulation key**'iyle (özel anahtar) ciphertext'i açar ve aynı ortak sırrı elde eder.

Ortak sır daha sonra bir simetrik protokolde (ör. TLS anahtar takvimi, `kuantum-23`) anahtar türetmek için kullanılır.

Bu derste kurulu `cryptography` 50.0.0 kitaplığının ML-KEM-768 uygulaması kullanılır. Kitaplık belgesi `encapsulate()`'in **`(shared_secret, ciphertext)`** sırasıyla döndüğünü açıkça yazar; sırayı ters okumak sessiz bir hatadır. Bu makinede ölçülen boyutlar: encapsulation key 1184 bayt, ciphertext 1088 bayt, ortak sır 32 bayt. Boyutlar güvenlik düzeyinin kendisi değildir; güvenlik düzeyi parametre kümesinin özelliğidir.

> [!NOTE]
> Görev 1 **gerçek** bir kriptografik işlem yapar (yerel `cryptography`/OpenSSL); kuantum donanımı kullanılmaz. Anahtarlar geçicidir, diske yazılmaz. Standart algoritmayı kullanmak, bu kurulumun FIPS sertifikalı bir modül olduğu anlamına gelmez.
:::

::: anlat 2. Mekanizma: bozuk ciphertext neden hata vermez?
Doğru uzunlukta ama bir biti değiştirilmiş bir ciphertext'i decapsulate edince ne olur? Bu makinedeki deneyin sonucu şudur: **hata yok**. Kitaplık başka, ama aynı bozuk girdi için her seferinde **aynı** 32 baytlık bir değer döndürür. Yalnız uzunluk yanlışsa `ValueError` gelir.

Bu davranışın adı *implicit rejection*'dır. ML-KEM özel anahtarı bu amaçla ayrı bir değer (`z`) taşır; IETF LAMPS'in ML-KEM sertifika belgesi (RFC 9935) bu değerden *"implicit rejection secret"* diye söz eder. Amaç, saldırgana "bu ciphertext geçerli mi?" sorusunun yanıtını vermemektir. Hata mesajı ya da farklı bir yanıt süresi böyle bir doğrulama kehaneti (*oracle*) olurdu ve seçilmiş ciphertext saldırılarına kapı açardı. Bu korumanın sonucu da önemlidir: decapsulation başarısını kendisi bildirmez. İki tarafın aynı anahtarı tuttuğu, protokolün sonraki adımında (ör. TLS `Finished` mesajı) doğrulanır.

İkinci ders ölçümle ilgilidir. Sekiz denemede sekiz uyuşma görmek, uyuşmazlık olasılığının sıfır olduğunu göstermez. `n` bağımsız denemede hiç hata görülmediyse, hata olasılığı için %95 güvenle söylenebilecek en iyi üst sınır `1 - 0.05^(1/n)`'dir (kabaca `3/n`, "üç kuralı"). Sekiz deneme yalnız "hata olasılığı %31'den küçük" der; standardın tasarım hedefi olan astronomik küçüklükte bir olasılık hakkında hiçbir şey söylemez.

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| `ciphertext, secret = pk.encapsulate()` | Kitaplık `(shared_secret, ciphertext)` döndürür; 32 bayt "ciphertext" gönderilir | Belgedeki sırayla aç |
| KEM'i mesaj şifreleme sanmak | Ortak sır gönderilen veri değildir | Sırdan simetrik anahtar türet |
| Bozuk ciphertext'te hata beklemek | Implicit rejection hata vermez, farklı bir anahtar döner | Anahtar uyumunu protokol içinde doğrula |
| "8 denemede hata yok = olasılık 0" | Az deneme yalnız gevşek bir üst sınır verir | `1 - 0.05^(1/n)` üst sınırını raporla |
| Standart algoritma = sertifikalı modül | Algoritma ile uygulamanın doğrulaması ayrı şeylerdir | Modül sertifikası ayrıca kontrol edilir |
:::

::: tahmin Sekiz başarılı deneme ne kanıtlar?
Sekiz denemenin hepsinde gönderici ve alıcı aynı sırrı elde etti. Hata olasılığı için %95 üst sınır nedir?

```python
for n in (8, 100, 10_000):
    print(n, round(1 - 0.05 ** (1 / n), 6), round(3 / n, 6))
```

???

```cikti
8 0.312344 0.375
100 0.029513 0.03
10000 0.0003 0.0003
```
Sekiz başarılı deneme yalnız "hata olasılığı %31'den küçük" der. Deneme sayısı büyüdükçe kesin sınır `3/n`'ye yaklaşır; 10.000 deneme bile 3/10.000'den küçük bir olasılığı ayırt edemez. Standardın hedeflediği küçüklükte bir hata olasılığı deneyle değil, analizle gösterilir.
:::

::: gorev 1 · Gerçek ML-KEM-768 akışı
`kem_akisi(private_key)` işlevini yaz.

- `private_key.public_key()` ile encapsulation key'i al ve `encapsulate()`'i **bir kez** çağır. Dönüş sırası `(shared_secret, ciphertext)`'tir.
- Aynı `private_key.decapsulate(ciphertext)`'i **bir kez** çağır.
- Dönüş: `(ciphertext, shared_secret, recovered_secret)` üçlüsü (`bytes`).
- Anahtarı çağıran üretir; global anahtar tutma.

Test, gerçek `cryptography` işlemlerini çağıran ve kaç kez çağrıldığını sayan ince bir sarmalayıcı kullanır; sahte kripto yoktur.

KUSURLU başlangıç `encapsulate()` sonucunu ters sırayla açıyor ve decapsulation'a ortak sırrı veriyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def kem_akisi(private_key):
    ciphertext, shared_secret = private_key.public_key().encapsulate()
    recovered = private_key.decapsulate(ciphertext)
    return ciphertext, shared_secret, recovered

if __name__ == '__main__':
    from cryptography.hazmat.primitives.asymmetric.mlkem import MLKEM768PrivateKey
    try:
        _r = kem_akisi(MLKEM768PrivateKey.generate())
        print({'ciphertext_bayt': len(_r[0]), 'sir_bayt': len(_r[1]), 'eslesme': _r[1] == _r[2]})
    except ValueError as e:
        print('ValueError:', e)
```

```solution
def kem_akisi(private_key):
    shared_secret, ciphertext = private_key.public_key().encapsulate()
    recovered = private_key.decapsulate(ciphertext)
    return ciphertext, shared_secret, recovered

if __name__ == '__main__':
    from cryptography.hazmat.primitives.asymmetric.mlkem import MLKEM768PrivateKey
    try:
        _r = kem_akisi(MLKEM768PrivateKey.generate())
        print({'ciphertext_bayt': len(_r[0]), 'sir_bayt': len(_r[1]), 'eslesme': _r[1] == _r[2]})
    except ValueError as e:
        print('ValueError:', e)
```

```test
need('kem_akisi')
from cryptography.hazmat.primitives.asymmetric.mlkem import MLKEM768PrivateKey

class _Acik:
    def __init__(self, sahip):
        self.sahip = sahip
    def encapsulate(self):
        self.sahip.enc += 1
        return self.sahip.anahtar.public_key().encapsulate()

class _Anahtar:
    def __init__(self):
        self.anahtar = MLKEM768PrivateKey.generate()
        self.enc = 0
        self.dec = 0
    def public_key(self):
        return _Acik(self)
    def decapsulate(self, c):
        self.dec += 1
        return self.anahtar.decapsulate(c)

_gorulen = set()
for _ in range(8):
    _k = _Anahtar()
    _ct, _ss, _rec = kem_akisi(_k)
    eq((_k.enc, _k.dec), (1, 1), 'encapsulate ve decapsulate birer kez')
    eq((type(_ct), type(_ss), type(_rec)), (bytes, bytes, bytes), 'üç değer de bytes')
    eq((len(_ct), len(_ss), len(_rec)), (1088, 32, 32), 'ML-KEM-768: ciphertext 1088, sır 32 bayt')
    eq(_ss, _rec, 'iki taraf aynı sırrı elde eder')
    eq(_k.anahtar.decapsulate(_ct), _ss, 'bağımsız gerçek decapsulation aynı sırrı verir')
    ok(_ct not in _gorulen, 'her encapsulation yeni ciphertext üretir')
    _gorulen.add(_ct)
    _bozuk = bytes([_ct[0] ^ 1]) + _ct[1:]
    _ret = _k.anahtar.decapsulate(_bozuk)
    ok(_ret != _ss and len(_ret) == 32, 'bozuk ciphertext hata vermez, farklı 32 baytlık değer döner')
    eq(_k.anahtar.decapsulate(_bozuk), _ret, 'aynı bozuk girdiye her seferinde aynı değer (implicit rejection)')
    raises(ValueError, _k.anahtar.decapsulate, _ct[:-1], msg='yanlış uzunluk ValueError')
```

```hint
Kitaplık belgesine göre `encapsulate()` önce ortak sırrı, sonra ciphertext'i döndürür: `shared_secret, ciphertext = ...`. Decapsulation'a ciphertext'i ver.
```
:::

::: gorev 2 · Hata gözlemini ve üst sınırını raporla
`hata_ozeti(sonuclar)` işlevini yaz. `sonuclar` bir `bool` listesidir: `True` = uyuşmazlık gözlendi, `False` = taraflar aynı sırrı elde etti.

- `sonuclar` `list` değilse ya da `bool` olmayan bir öğe içeriyorsa `ValueError`.
- Dönüş: `{'n': deneme sayısı, 'hata': True sayısı, 'oran': round(hata / n, 6), 'ust_sinir_95': ...}`.
  - `n == 0` ise `oran` ve `ust_sinir_95` `None`'dır.
  - `hata == 0` ve `n > 0` ise `ust_sinir_95 = round(1 - 0.05 ** (1 / n), 6)`.
  - `hata > 0` ise `ust_sinir_95` `None`'dır (sıfır olmayan gözlemde bu basit formül geçerli değildir).

KUSURLU başlangıç sıfır gözlemde üst sınırı 0 yazıyor ve boş listede sıfıra bölüyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
Path('ornek.json').write_text('[[false, false, false, false, false, false, false, false]]', encoding='utf-8')
```

```starter
def hata_ozeti(sonuclar):
    n = len(sonuclar)
    hata = sum(sonuclar)
    return {'n': n, 'hata': hata, 'oran': round(hata / n, 6), 'ust_sinir_95': round(hata / n, 6)}

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(hata_ozeti(*_args))
```

```solution
def hata_ozeti(sonuclar):
    if not isinstance(sonuclar, list) or any(type(x) is not bool for x in sonuclar):
        raise ValueError('sonuclar bool listesi olmali')
    n = len(sonuclar)
    hata = sum(sonuclar)
    if n == 0:
        return {'n': 0, 'hata': 0, 'oran': None, 'ust_sinir_95': None}
    ust = round(1 - 0.05 ** (1 / n), 6) if hata == 0 else None
    return {'n': n, 'hata': hata, 'oran': round(hata / n, 6), 'ust_sinir_95': ust}

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(hata_ozeti(*_args))
```

```test
need('hata_ozeti')
import copy
_s = [False] * 8
_yedek = copy.deepcopy(_s)
eq(hata_ozeti(_s), {'n': 8, 'hata': 0, 'oran': 0.0, 'ust_sinir_95': 0.312344}, 'sekiz başarı: üst sınır %31,2')
eq(_s, _yedek, 'girdi değişmemeli')
eq(hata_ozeti([False]), {'n': 1, 'hata': 0, 'oran': 0.0, 'ust_sinir_95': 0.95}, 'tek deneme: üst sınır 0,95')
eq(hata_ozeti([False] * 100)['ust_sinir_95'], 0.029513, '100 deneme: kabaca 3/100')
eq(hata_ozeti([False] * 3)['ust_sinir_95'], 0.631597, 'üç deneme: 6 basamağa yuvarlanır')
eq(hata_ozeti([True, False, False]), {'n': 3, 'hata': 1, 'oran': 0.333333, 'ust_sinir_95': None}, 'hata gözlenince basit üst sınır yok')
eq(hata_ozeti([True, True]), {'n': 2, 'hata': 2, 'oran': 1.0, 'ust_sinir_95': None}, 'hepsi hata')
eq(hata_ozeti([]), {'n': 0, 'hata': 0, 'oran': None, 'ust_sinir_95': None}, 'boş liste')
for _bozuk in (None, (False,), [0, 1], [False, None], ['False']):
    raises(ValueError, hata_ozeti, _bozuk, msg=f'bozuk girdi ValueError: {_bozuk!r}')
```

```hint
Boş listeyi en başta ele al. Üst sınır yalnız hiç hata görülmediğinde `1 - 0.05 ** (1 / n)`'dir.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **KEM (25 sn).** "ML-KEM mesaj şifrelemez; ortak bir sır üretir. Gönderici encapsulate ile sır ve ciphertext üretir, alıcı decapsulate ile aynı sırrı çıkarır."
2. **Gerçek deney (25 sn).** "Kurulu cryptography kitaplığıyla sekiz rastgele anahtarda akışı çalıştırdık: ciphertext 1088, sır 32 bayt ve iki taraf her seferinde aynı sırrı aldı. Kitaplık sırrı önce döndürüyor; ters açmak sessiz bir hata."
3. **Implicit rejection (30 sn).** "Bir biti bozulmuş ciphertext hata vermedi; farklı ama tutarlı bir anahtar döndü. Böylece saldırgan 'bu ciphertext geçerli mi' sorusunun yanıtını alamıyor. Anahtar uyumu protokolün sonraki adımında doğrulanıyor."
4. **Ölçüm dürüstlüğü (25 sn).** "Sekiz denemede hata yok, ama bu 'olasılık sıfır' demek değil. %95 üst sınır %31; standardın iddia ettiği küçüklükte bir olasılığı sekiz denemeyle ölçemeyiz."
5. **Sınır (15 sn).** "Algoritmayı kullanmak, modülün FIPS sertifikalı olduğu anlamına gelmez."
:::

::: anlat Sınır ve kaynak
Görev 1 bu makinedeki `cryptography` 50.0.0 kurulumuyla gerçek ML-KEM-768 işlemi yapar; başka bir makinede bu sürüm ya da ML-KEM desteği yoksa deney çalışmaz ve kurulum bu derste yapılmaz. Boyutlar bu kurulumda ölçülmüştür. Decapsulation hata olasılığının standarttaki değeri burada ölçülmez ve derste sayı olarak verilmez; ders yalnız az sayıda denemenin bu olasılık hakkında ne söyleyebileceğini gösterir. Yan kanal (zamanlama) güvenliği ayrı bir konudur (`kuantum-25`).

- Birincil kaynaklar: [NIST FIPS 203 — Module-Lattice-Based Key-Encapsulation Mechanism Standard (13 Ağustos 2024)](https://csrc.nist.gov/pubs/fips/203/final) (ML-KEM-512/768/1024); [pyca/cryptography — ML-KEM key encapsulation](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/mlkem/) (`encapsulate()` dönüş sırası, 47.0.0'da eklendi); [IETF LAMPS — Algorithm Identifiers for ML-KEM (RFC 9935 taslağı)](https://datatracker.ietf.org/doc/html/draft-ietf-lamps-kyber-certificates) (`z` "implicit rejection secret"). Doğrulama tarihi: 11 Kasım 2026.
:::

::: dusun
Bir protokol tasarımcısı "decapsulation hata verirse bağlantıyı hemen kapatalım" diyor. Implicit rejection yüzünden decapsulation zaten hata vermiyor. Anahtar uyumsuzluğunu protokol hangi noktada ve neyle fark eder? Bu noktaya kadar hangi veri, uyumsuz bir anahtarla işlenmiş olabilir?
:::

::: ozet
- ML-KEM bir KEM'dir: mesaj değil ortak sır üretir; sır daha sonra simetrik anahtar türetmede kullanılır.
- `cryptography` kitaplığında `encapsulate()` `(shared_secret, ciphertext)` döndürür; sıra ters okunursa hata sessizdir.
- Doğru uzunlukta bozuk ciphertext hata vermez; tutarlı ama farklı bir anahtar döner (implicit rejection).
- Sıfır hata gözlemi yalnız bir üst sınır verir: `n` denemede %95 için `1 - 0.05^(1/n)`.
:::
