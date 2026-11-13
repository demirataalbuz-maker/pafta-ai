---
id: kuantum-28
title: "CBOM · Kripto Envanteri ve Geçiş Önceliği"
summary: Kripto envanterinde (CBOM) algoritma adının yanına kullanım amacını, veri ömrünü ve geçiş süresini koy; "şimdi topla, sonra çöz" riskini imza riskinden ayırarak öncelik sırası çıkar ve anahtar değişimi varlıkları için kalan zaman payını hesapla.
esleme: kuantum-27, kuantum-24, kuantum-23, kuantum-22
timeout: 30
---

::: anlat 1. "RSA kullanıyoruz" bir envanter değildir
Kuantum sonrası geçişin ilk işi neyin nerede kullanıldığını bilmektir. Bir **kripto envanteri** (*cryptographic bill of materials*, CBOM) yalnız algoritma adlarının listesi olamaz. "RSA kullanıyoruz" kaydı iki çok farklı riski birbirine karıştırır:

- **Anahtar kurma (*key establishment*)** için RSA ya da ECDH: bugün kaydedilen şifreli trafik, ileride yeterli bir kuantum bilgisayarla çözülebilir. OpenSSH'in kuantum sonrası sayfası bu riski *"store now, decrypt later"* (şimdi topla, sonra çöz) diye adlandırır. Risk **bugün** başlar, çünkü saldırgan bugün kaydeder.
- **İmza** için RSA ya da ECDSA: saldırgan geçmiş imzaları sahteleyerek bir şey kazanmaz; risk, kuantum bilgisayarın var olduğu andan sonra atılacak sahte imzalardır. Bu yüzden imza geçişi önemlidir ama "şimdi topla" baskısı taşımaz.

NIST bu geçişin standartlar tarafını *Transition to Post-Quantum Cryptography Standards* (NIST IR 8547) belgesiyle ele alır. İlk taslak 12 Kasım 2024'te yayımlandı, nihai sürüm 27 Ekim 2026'da onun yerini aldı.

> [!NOTE]
> Bu dersteki envanter, ufuk ve öncelik kuralı **sentetiktir**. Ufuk (`horizon`) bir senaryo girdisidir, bir "Q-Day" tahmini değildir. Öncelik kuralı örnek bir politikadır; güncel mevzuat, resmî takvim ya da kuruma özel risk değerlendirmesi değildir. Ağ taranmaz, anahtar ya da sertifika dosyası okunmaz.
:::

::: anlat 2. Mekanizma: ömür + geçiş > ufuk
Bir anahtar değişimi varlığı için asıl soru, "verinin gizli kalması gereken süre" ile "geçişin süresi"nin toplamının, tehdidin gelebileceği ufku aşıp aşmadığıdır:

- `life`: verinin gizli kalması gereken yıl sayısı (ör. arşiv kaydı 10 yıl);
- `migration`: bu sistemi kuantum sonrası algoritmaya geçirmenin süresi (ör. 2 yıl);
- `horizon`: senaryodaki tehdit ufku (ör. 5 yıl).

`life + migration > horizon` ise geçiş **şimdi** başlamalıdır. Geçiş bitene kadar toplanan trafik, gizli kalması gereken süre içinde çözülebilir hâle gelir. Geçiş süresi riske **eklenir**: "tehdit beş yıl sonra, geçiş iki yıl sürer, üç yıl beklerim" düşüncesi, bekleme süresince toplanan trafiği unutur. Kalan **pay** `horizon − (life + migration)`'dır: negatifse geç kalınmıştır, sıfırsa sınırdadır.

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| "RSA" kaydını tek risk saymak | Anahtar kurma ve imza farklı aciliyettedir | Kullanım amacını ayrı alan olarak tut |
| Geçiş süresini ufuktan düşmek | Geçiş boyunca toplanan trafik unutulur | `life + migration > horizon` |
| Kuantum sonrası algoritmayı "bitti" saymak | Uygulama, parametre ve yan kanal hâlâ incelenir | `review-implementation` |
| Kullanımı bilinmeyen kaydı sessizce atlamak | Envanterde görünmeyen risk kalır | `needs-inventory` |
| Ufku bir takvim tahmini gibi sunmak | Ufuk senaryo girdisidir | Birden çok ufukla sına |
:::

::: tahmin Tehdit beş yıl sonra; bugün acil mi?
Bir arşiv sistemi RSA ile anahtar kuruyor. Veriler 10 yıl gizli kalmalı, geçiş 2 yıl sürecek, senaryodaki ufuk 5 yıl. Bir de 1 yıllık oturum verisi taşıyan, geçişi 1 yıl süren bir sistem var.

```python
horizon = 5
for ad, life, migration in (('arsiv', 10, 2), ('oturum', 1, 1)):
    pay = horizon - (life + migration)
    print(ad, life + migration > horizon, pay)
```

???

```cikti
arsiv True -7
oturum False 3
```
Tehdit ufku beş yıl sonra olsa da arşiv için geçiş bugün başlamalıydı; pay −7 yıl, yani bugün toplanan trafik ufuktan sonra hâlâ değerli. Kısa ömürlü oturum verisinde 3 yıllık pay var.
:::

::: gorev 1 · CBOM öncelik sırası
`cbom_sirala(varliklar, horizon)` işlevini yaz.

- `horizon` `bool` olmayan, `>= 0` bir `int`; `varliklar` bir `list`. Değilse `ValueError`.
- Her varlık `{'id': str, 'algorithm': str, 'usage': 'exchange' | 'signature' | 'symmetric', 'life': int, 'migration': int, 'public': bool}`. `id` ve `algorithm` boş olmayan `str`; `life` ve `migration` `bool` olmayan, `>= 0` `int`; `public` tam `bool`; `id` benzersiz. Değilse `ValueError`.
- Sınıf ve sıra anahtarı (ilk uyan):
  1. `usage == 'exchange'`, `algorithm` `'RSA'` ya da `'ECDH'` ve `life + migration > horizon` → `'urgent-hndl'` (0);
  2. `usage == 'signature'` ve `algorithm` `'RSA'` ya da `'ECDSA'` → `'signature-plan'` (1);
  3. `algorithm` `'ML-KEM'`, `'ML-DSA'`, `'SLH-DSA'` ya da `'AES-256'` → `'review-implementation'` (3);
  4. kalan her şey → `'needs-inventory'` (2).
- Dönüş: `[[id, sinif], ...]`, önce sıra anahtarına, sonra `id`'ye göre sıralı.

KUSURLU başlangıç geçiş süresini ufuktan düşüyor (`life > horizon + migration`), imza ile anahtar kurmayı ayırmıyor ve yalnız `id`'ye göre sıralıyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
Path('ornek.json').write_text('[[{"id": "arsiv", "algorithm": "RSA", "usage": "exchange", "life": 4, "migration": 2, "public": true}, {"id": "kod-imza", "algorithm": "ECDSA", "usage": "signature", "life": 1, "migration": 1, "public": true}], 5]', encoding='utf-8')
```

```starter
def cbom_sirala(varliklar, horizon):
    sonuc = []
    for r in varliklar:
        if r['algorithm'] in ('RSA', 'ECDH', 'ECDSA') and r['life'] > horizon + r['migration']:
            sonuc.append([r['id'], 'urgent-hndl'])
        elif r['algorithm'] in ('ML-KEM', 'ML-DSA', 'SLH-DSA', 'AES-256'):
            sonuc.append([r['id'], 'review-implementation'])
        else:
            sonuc.append([r['id'], 'needs-inventory'])
    return sorted(sonuc)

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(cbom_sirala(*_args))
```

```solution
_KULLANIM = ('exchange', 'signature', 'symmetric')
_PQ_YA_DA_SIMETRIK = ('ML-KEM', 'ML-DSA', 'SLH-DSA', 'AES-256')

def _sayi(x):
    return type(x) is int and x >= 0

def cbom_sirala(varliklar, horizon):
    if not isinstance(varliklar, list) or not _sayi(horizon):
        raise ValueError('varliklar list, horizon >= 0 int olmali')
    gorulen = set()
    satir = []
    for r in varliklar:
        if (not isinstance(r, dict)
                or not all(isinstance(r.get(k), str) and r[k].strip() for k in ('id', 'algorithm'))
                or r.get('usage') not in _KULLANIM
                or not _sayi(r.get('life')) or not _sayi(r.get('migration'))
                or type(r.get('public')) is not bool):
            raise ValueError('bozuk varlik')
        if r['id'] in gorulen:
            raise ValueError('yinelenen id')
        gorulen.add(r['id'])
        a, u = r['algorithm'], r['usage']
        if u == 'exchange' and a in ('RSA', 'ECDH') and r['life'] + r['migration'] > horizon:
            anahtar, sinif = 0, 'urgent-hndl'
        elif u == 'signature' and a in ('RSA', 'ECDSA'):
            anahtar, sinif = 1, 'signature-plan'
        elif a in _PQ_YA_DA_SIMETRIK:
            anahtar, sinif = 3, 'review-implementation'
        else:
            anahtar, sinif = 2, 'needs-inventory'
        satir.append((anahtar, r['id'], sinif))
    return [[i, s] for _, i, s in sorted(satir)]

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(cbom_sirala(*_args))
```

```test
need('cbom_sirala')
import copy
def _v(i, a, u, life=1, mig=1, pub=True):
    return {'id': i, 'algorithm': a, 'usage': u, 'life': life, 'migration': mig, 'public': pub}
_env = [
    _v('z-aes', 'AES-256', 'symmetric', 10, 1, False),
    _v('kod-imza', 'ECDSA', 'signature'),
    _v('arsiv', 'RSA', 'exchange', 4, 2),
    _v('vpn', 'ECDH', 'exchange', 3, 3),
    _v('oturum', 'ECDH', 'exchange', 2, 2),
    _v('belge-imza', 'RSA', 'signature', 20, 3),
    _v('aa-kem', 'ML-KEM', 'exchange', 30, 0),
    _v('eski-sifre', '3DES', 'symmetric'),
    _v('rsa-sifreleme', 'RSA', 'symmetric'),
    _v('ed-imza', 'Ed25519', 'signature'),
]
_yedek = copy.deepcopy(_env)
eq(cbom_sirala(_env, 5), [
    ['arsiv', 'urgent-hndl'], ['vpn', 'urgent-hndl'],
    ['belge-imza', 'signature-plan'], ['kod-imza', 'signature-plan'],
    ['ed-imza', 'needs-inventory'], ['eski-sifre', 'needs-inventory'], ['oturum', 'needs-inventory'], ['rsa-sifreleme', 'needs-inventory'],
    ['aa-kem', 'review-implementation'], ['z-aes', 'review-implementation'],
], '4+2 > 5 ve 3+3 > 5 acil; 2+2 = 4 ufkun altında; önce sınıf sırası (aa-kem id olarak önde olsa da sonda), sonra id')
eq(_env, _yedek, 'girdi değişmemeli')
eq(cbom_sirala([_v('a', 'RSA', 'exchange', 3, 2)], 5), [['a', 'needs-inventory']], 'ömür + geçiş = ufuk: acil değil')
eq(cbom_sirala([_v('a', 'RSA', 'exchange', 3, 3)], 5), [['a', 'urgent-hndl']], 'bir yıl fazlası acil')
eq(cbom_sirala([_v('a', 'RSA', 'exchange', 0, 1)], 0), [['a', 'urgent-hndl']], 'ufuk 0: her açık anahtar kurma acil')
eq(cbom_sirala([], 0), [], 'boş envanter')
for _h in (-1, True, 5.0, None):
    raises(ValueError, cbom_sirala, [], _h, msg=f'bozuk horizon ValueError: {_h!r}')
raises(ValueError, cbom_sirala, tuple(_env), 5, msg='liste olmayan envanter ValueError')
for _alan, _deger in (('id', ''), ('id', '  '), ('id', 5), ('algorithm', ''), ('algorithm', None), ('usage', 'key-exchange'),
                      ('life', -1), ('life', 1.0), ('life', True), ('migration', -1), ('migration', '2'), ('public', 1), ('public', None)):
    raises(ValueError, cbom_sirala, [dict(_v('a', 'RSA', 'exchange'), **{_alan: _deger})], 5, msg=f'bozuk varlık ValueError: {_alan}={_deger!r}')
raises(ValueError, cbom_sirala, [_v('a', 'RSA', 'exchange'), _v('a', 'AES-256', 'symmetric')], 5, msg='yinelenen id ValueError')
raises(ValueError, cbom_sirala, ['arsiv'], 5, msg='dict olmayan varlık ValueError')
```

```hint
Her varlığı doğruladıktan sonra `(sıra_anahtarı, id, sınıf)` demeti üret ve bütün demetleri `sorted` ile sırala; demetler önce anahtara, sonra `id`'ye göre karşılaştırılır.
```
:::

::: gorev 2 · Anahtar kurma varlıkları için kalan pay
`gecis_payi(varliklar, horizon)` işlevini yaz.

- Girdi kuralları görev 1 ile aynıdır (aynı doğrulama, aynı `ValueError` durumları).
- Yalnız `usage == 'exchange'` ve `algorithm` `'RSA'` ya da `'ECDH'` olan varlıklar değerlendirilir.
- Her biri için `pay = horizon - (life + migration)` ve durum: `pay < 0` → `'gec-kalindi'`, `pay == 0` → `'sinirda'`, `pay > 0` → `'zaman-var'`.
- Dönüş: `[[id, pay, durum], ...]`, önce `pay` artan (en az zamanı kalan önce), sonra `id`'ye göre.

KUSURLU başlangıç imza varlıklarını da hesaba katıyor ve en çok zamanı kalanı önce yazıyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def gecis_payi(varliklar, horizon):
    sonuc = []
    for r in varliklar:
        if r['algorithm'] in ('RSA', 'ECDH', 'ECDSA'):
            pay = horizon - (r['life'] + r['migration'])
            durum = 'gec-kalindi' if pay < 0 else 'zaman-var'
            sonuc.append([r['id'], pay, durum])
    return sorted(sonuc, key=lambda s: -s[1])
```

```solution
_KULLANIM = ('exchange', 'signature', 'symmetric')

def _sayi(x):
    return type(x) is int and x >= 0

def gecis_payi(varliklar, horizon):
    if not isinstance(varliklar, list) or not _sayi(horizon):
        raise ValueError('varliklar list, horizon >= 0 int olmali')
    gorulen = set()
    satir = []
    for r in varliklar:
        if (not isinstance(r, dict)
                or not all(isinstance(r.get(k), str) and r[k].strip() for k in ('id', 'algorithm'))
                or r.get('usage') not in _KULLANIM
                or not _sayi(r.get('life')) or not _sayi(r.get('migration'))
                or type(r.get('public')) is not bool):
            raise ValueError('bozuk varlik')
        if r['id'] in gorulen:
            raise ValueError('yinelenen id')
        gorulen.add(r['id'])
        if r['usage'] != 'exchange' or r['algorithm'] not in ('RSA', 'ECDH'):
            continue
        pay = horizon - (r['life'] + r['migration'])
        durum = 'gec-kalindi' if pay < 0 else ('sinirda' if pay == 0 else 'zaman-var')
        satir.append([r['id'], pay, durum])
    return sorted(satir, key=lambda s: (s[1], s[0]))
```

```test
need('gecis_payi')
import copy
def _v(i, a, u, life=1, mig=1, pub=True):
    return {'id': i, 'algorithm': a, 'usage': u, 'life': life, 'migration': mig, 'public': pub}
_env = [
    _v('oturum', 'ECDH', 'exchange', 1, 1),
    _v('b-arsiv', 'RSA', 'exchange', 8, 4),
    _v('vpn', 'ECDH', 'exchange', 3, 2),
    _v('arsiv', 'RSA', 'exchange', 10, 2),
    _v('a-yedek', 'RSA', 'exchange', 5, 2),
    _v('d-ara', 'ECDH', 'exchange', 4, 2),
    _v('kod-imza', 'ECDSA', 'signature', 30, 3),
    _v('rsa-imza', 'RSA', 'signature', 30, 3),
    _v('yeni', 'ML-KEM', 'exchange', 30, 0),
]
_yedek = copy.deepcopy(_env)
eq(gecis_payi(_env, 5), [
    ['arsiv', -7, 'gec-kalindi'], ['b-arsiv', -7, 'gec-kalindi'], ['a-yedek', -2, 'gec-kalindi'], ['d-ara', -1, 'gec-kalindi'],
    ['vpn', 0, 'sinirda'], ['oturum', 3, 'zaman-var'],
], 'yalnız klasik anahtar kurma; önce pay (a-yedek id olarak önde olsa da), eşit payda id; pay -1 de geç kalınmıştır')
eq(_env, _yedek, 'girdi değişmemeli')
eq(gecis_payi([_v('a', 'RSA', 'exchange', 0, 0)], 0), [['a', 0, 'sinirda']], 'ufuk 0, ömür ve geçiş 0: sınırda')
eq(gecis_payi([_v('a', 'RSA', 'exchange', 0, 0)], 1), [['a', 1, 'zaman-var']], 'bir yıl pay')
eq(gecis_payi([_v('a', 'RSA', 'symmetric', 99, 9)], 1), [], 'anahtar kurma olmayan RSA değerlendirilmez')
eq(gecis_payi([], 3), [], 'boş envanter')
for _h in (-1, True, 2.5):
    raises(ValueError, gecis_payi, [], _h, msg=f'bozuk horizon ValueError: {_h!r}')
raises(ValueError, gecis_payi, tuple(_env), 5, msg='liste olmayan envanter ValueError')
for _alan, _deger in (('id', ''), ('algorithm', '  '), ('usage', None), ('life', -1), ('migration', 1.5), ('public', 'evet'), ('id', None)):
    raises(ValueError, gecis_payi, [dict(_v('a', 'RSA', 'signature'), **{_alan: _deger})], 5, msg=f'imza varlığı da doğrulanır: {_alan}={_deger!r}')
raises(ValueError, gecis_payi, [_v('a', 'RSA', 'exchange'), _v('a', 'RSA', 'signature')], 5, msg='yinelenen id ValueError')
raises(ValueError, gecis_payi, ['vpn'], 5, msg='dict olmayan varlık ValueError')
```

```hint
Önce bütün varlıkları doğrula (değerlendirmeye girmeyenler dahil); sonra yalnız klasik anahtar kurma varlıkları için payı hesapla. Sıralama anahtarı `(pay, id)` olmalı.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Envanter (20 sn).** "'RSA kullanıyoruz' kaydı yetmiyor. Anahtar kurma mı, imza mı, verinin ömrü ne, geçiş ne kadar sürer: CBOM bunları birlikte tutmalı."
2. **İki risk (30 sn).** "Anahtar kurmada saldırgan bugün kaydedip yarın çözer; OpenSSH buna 'şimdi topla, sonra çöz' diyor. İmzada risk kuantum bilgisayardan sonra atılacak sahte imzalar. Aciliyetleri farklı."
3. **Kural (30 sn).** "Ömür artı geçiş süresi ufku aşıyorsa geçiş bugün başlamalı. Tahminimizde ufuk beş yıl, ama 10 yıl gizli kalacak arşiv için pay −7 yıl: bugün toplanan trafik ufuktan sonra hâlâ değerli."
4. **Sıra (25 sn).** "Envanteri sıraladık: önce geç kalmış anahtar kurmalar, sonra imza planı, sonra kullanımı belirsiz kayıtlar, en son zaten kuantum sonrası olanların uygulama incelemesi."
5. **Sınır (15 sn).** "Ufuk bir senaryo girdisi, Q-Day tahmini değil; birden çok ufukla denemek gerekir."
:::

::: anlat Sınır ve kaynak
Envanter ve ufuk sentetiktir; gerçek bir CBOM otomatik keşif (kod tarama, ağ gözlemi, sertifika envanteri) ve sahiplik bilgisi ister ve bu derste yapılmaz. Öncelik kuralı örnek bir politikadır. `public` alanı bu derste yalnız doğrulanır; gerçek bir politikada dışa açık sistemlere ek ağırlık verilebilir. Hibrit kullanımlar (`kuantum-23`, `kuantum-24`) ve uygulama düzeyindeki riskler (`kuantum-25`) ayrı derslerdedir. NIST IR 8547'nin içerdiği takvim ve öneriler bu derste aktarılmamıştır; belge kaynak olarak okunmalıdır.

- Birincil kaynaklar: [NIST IR 8547 — Transition to Post-Quantum Cryptography Standards](https://csrc.nist.gov/pubs/ir/8547/ipd) (ilk taslak 12 Kasım 2024; nihai sürüm 27 Ekim 2026'da yerini aldı); [OpenSSH — Post-Quantum Cryptography](https://www.openssh.org/pq.html) (*store now, decrypt later*). Doğrulama tarihi: 11 Kasım 2026.
:::

::: dusun
Ufku 5, 10 ve 15 yıl olarak üç kez değiştirip aynı envanteri sırala. Hangi varlıkların sınıfı ufuktan bağımsız kalıyor, hangileri ufka duyarlı? Yönetime "geçişi şimdi başlatmalıyız" demek için hangi varlıkların hangi ufuklarda acil kaldığını göstermek yeterli mi?
:::

::: ozet
- CBOM algoritma adının yanına kullanım amacını, veri ömrünü ve geçiş süresini koyar.
- Anahtar kurmada "şimdi topla, sonra çöz" riski bugün başlar; imza riski kuantum bilgisayardan sonradır.
- `life + migration > horizon` ise geçiş bugün başlamalıdır; geçiş süresi riske eklenir.
- Kalan pay `horizon − (life + migration)`'dır; ufuk bir senaryo girdisidir, takvim değildir.
:::
