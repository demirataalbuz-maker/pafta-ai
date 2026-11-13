---
id: ai-bulut-07
title: "Vector Database ve Model Sunucusu · Yetki Kapısı"
summary: Model ve vektör veritabanı uçlarını rota rota yetkilendir (kimlik + kapsam + nesne düzeyi kiracı); uygulamaların gerçekten yaptığı işlemlere göre gereken en dar anahtarı bul.
esleme: ai-savunma-19, ai-saldiri-19, ai-saldiri-39, ai-bulut-05
timeout: 30
---

::: anlat 1. Varsayılan açık bir veritabanı
Qdrant'ın güvenlik belgesi açık kaynak kurulumlar için açık konuşur: kimlik doğrulama yapılandırılmamışsa sunucu *"accepts requests from anyone who can reach it"*. Belge üç katman sunar: **yönetici API anahtarı** (her işlem), **salt okunur API anahtarı** (yalnız okuma) ve JWT tabanlı **ayrıntılı erişim anahtarları** (koleksiyon başına okuma ya da yazma).

Bu tablo vektör veritabanlarına özgü değildir; model sunucuları ve RAG ağ geçitleri de aynı soruyu sorar: **bu rota kimlik istiyor mu, hangi kapsamı istiyor ve istenen nesne çağıranın mı?** OWASP API Security Top 10 2023'ün ilk maddesi API1 *Broken Object Level Authorization* (BOLA) bu üçüncü soruyu anlatır. Kimlik doğrulanmış bir kullanıcı, isteğe başka bir nesnenin kimliğini yazarak o nesneye ulaşabiliyorsa nesne düzeyinde yetki kırıktır. Vektör veritabanında "nesne" bir koleksiyon ya da bir kiracının kayıtlarıdır.

> [!NOTE]
> Rotalar, kapsam adları ve işlem adları **sentetiktir**; gerçek bir Qdrant ya da model sunucusu çalıştırılmaz. `verified` bayrağı, token'ı güvenilir bir ağ geçidinin doğruladığını temsil eder.
:::

::: anlat 2. Mekanizma: üç soru, sırayla
Bir istek geldiğinde yetki kapısı üç soruyu sırayla sorar ve ilk "hayır"da durur:

1. **Kimlik:** rota herkese açık mı (ör. sağlık kontrolü)? Değilse token doğrulanmış mı?
2. **Kapsam:** token bu rota için gereken kapsamı taşıyor mu (ör. çıkarım için `inference`, koleksiyon okumak için `collection-read`)?
3. **Nesne:** istenen kaynağın kiracısı, token'ın kiracısıyla aynı mı?

Üçüncü soru en sık atlanandır. Kimlik ve kapsam doğru olduğu için "yetkili" sayılan istek, URL'deki koleksiyon adını değiştirerek başka bir kiracının verisini okur. Bu BOLA'nın tam tanımıdır.

İkinci bir tasarım sorusu da anahtarın genişliğidir. Yalnız arama yapan bir sohbet uygulamasına yönetici anahtarı vermek, o uygulamanın sızdırılmış bir yapılandırma dosyası üzerinden bütün koleksiyonları silebilmesi demektir.

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| Veritabanını "iç ağda" diye kimliksiz bırakmak | İç ağa erişen her bileşen (ve SSRF) her işlemi yapar | Her rota kimlik ister; yalnız sağlık kontrolü açık |
| Kapsamı rota yerine servis düzeyinde denetlemek | `inference` kapsamlı token koleksiyon okur | Rota başına gereken kapsam |
| Kiracıyı denetlemeden koleksiyon okumak | Kimliği doğru kullanıcı başka kiracıyı okur (BOLA) | `tenant == resource_tenant` ve ikisi de dolu |
| Bilinmeyen rotaya varsayılan izin | Yeni eklenen yönetim ucu korumasız açılır | Tanınmayan rota → ret |
| Her uygulamaya yönetici anahtarı | Okuyan uygulama sızarsa silme de sızar | İşlemlere göre en dar anahtar |
:::

::: tahmin Kimlik ve kapsam tam, nesne yanlış
Doğrulanmış bir token `collection-read` kapsamı taşıyor ve kiracısı `musteri-a`. İstek `musteri-b`'nin koleksiyonuna gidiyor. Kiracıyı denetlemeyen kapı ile denetleyen kapı ne döndürür?

```python
def kapi_kiracisiz(verified, scopes, tenant, kaynak_tenant):
    return verified is True and 'collection-read' in scopes

def kapi_kiracili(verified, scopes, tenant, kaynak_tenant):
    return kapi_kiracisiz(verified, scopes, tenant, kaynak_tenant) and bool(tenant) and tenant == kaynak_tenant

istek = (True, ['collection-read'], 'musteri-a', 'musteri-b')
print(kapi_kiracisiz(*istek), kapi_kiracili(*istek))
```

???

```cikti
True False
```
Kimlik ve kapsam kontrolü geçti; ama istenen nesne çağıranın değil. Kiracı karşılaştırması olmayan kapı bunu yetkili saydı. OWASP API1 (BOLA) tam olarak bu boşluktur.
:::

::: gorev 1 · Rota başına kimlik, kapsam ve nesne denetimi
`endpoint_izin(route, verified, scopes, tenant, resource_tenant)` işlevini yaz. Hata fırlatma; her durumda `bool` döndür.

- `route == 'health'` → `True` (herkese açık; diğer argümanlara bakılmaz).
- Diğer bütün rotalar için önce: `verified is True` ve `scopes` öğelerinin hepsi `str` olan bir `list`. Değilse `False`.
- `route == 'invoke'` → `'inference' in scopes`.
- `route == 'read'` → `'collection-read' in scopes` **ve** `tenant` boş olmayan bir `str` **ve** `tenant == resource_tenant`.
- Başka her rota (ör. `'admin'`, `'Health'`, `None`) → `False`.

KUSURLU başlangıç bilinmeyen rotaya izin veriyor, `read` rotasında kiracıyı denetlemiyor ve `verified`'ın doğruluk değerine bakıyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
Path('ornek.json').write_text('["read", true, ["collection-read"], "musteri-a", "musteri-b"]', encoding='utf-8')
```

```starter
def endpoint_izin(route, verified, scopes, tenant, resource_tenant):
    if route == 'health':
        return True
    if not verified:
        return False
    if route == 'invoke':
        return 'inference' in scopes
    if route == 'read':
        return 'collection-read' in scopes
    return True

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(endpoint_izin(*_args))
```

```solution
def endpoint_izin(route, verified, scopes, tenant, resource_tenant):
    if route == 'health':
        return True
    if verified is not True or not isinstance(scopes, list) or any(not isinstance(s, str) for s in scopes):
        return False
    if route == 'invoke':
        return 'inference' in scopes
    if route == 'read':
        return 'collection-read' in scopes and isinstance(tenant, str) and bool(tenant) and tenant == resource_tenant
    return False

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(endpoint_izin(*_args))
```

```test
need('endpoint_izin')
_R = ['collection-read']
_I = ['inference']
_vakalar = [
    (('health', None, None, None, None), True, 'sağlık kontrolü kimliksiz açık'),
    (('invoke', True, _I, '', ''), True, 'çıkarım kiracı istemez'),
    (('invoke', True, ['inference', 'collection-read'], None, None), True, 'fazla kapsam çıkarımı bozmaz'),
    (('invoke', True, _R, None, None), False, 'okuma kapsamı çıkarım için yetmez'),
    (('invoke', 1, _I, None, None), False, 'verified 1 güvenilir değil'),
    (('invoke', 'true', _I, None, None), False, 'verified dizge güvenilir değil'),
    (('invoke', False, _I, None, None), False, 'doğrulanmamış token'),
    (('invoke', True, 'inference', None, None), False, 'scopes liste değil (alt dizge tuzağı)'),
    (('invoke', True, ('inference',), None, None), False, 'scopes tuple değil liste olmalı'),
    (('invoke', True, ['inference', 5], None, None), False, 'scopes içinde str olmayan öğe'),
    (('read', True, _R, 'musteri-a', 'musteri-a'), True, 'kendi kiracısını okur'),
    (('read', True, _R, 'musteri-a', 'musteri-b'), False, 'başka kiracı: BOLA'),
    (('read', True, _R, '', ''), False, 'boş kiracı eşleşmesi yetki değildir'),
    (('read', True, _R, None, None), False, 'kiracısız token'),
    (('read', True, _R, 5, 5), False, 'str olmayan kiracı'),
    (('read', True, _I, 'musteri-a', 'musteri-a'), False, 'çıkarım kapsamı okuma için yetmez'),
    (('read', True, 'collection-read', 'musteri-a', 'musteri-a'), False, 'scopes liste değil'),
    (('admin', True, ['inference', 'collection-read'], 'musteri-a', 'musteri-a'), False, 'tanınmayan rota ret'),
    (('Health', None, None, None, None), False, 'rota adı büyük/küçük harfe duyarlı'),
    ((None, True, _I, None, None), False, 'rota yok'),
]
for _arg, _beklenen, _neden in _vakalar:
    eq(endpoint_izin(*_arg), _beklenen, f'{_neden}: {_arg!r}')
```

```hint
Kontrolleri üç basamak olarak yaz: açık rota, ortak kimlik/kapsam ön koşulu, rotaya özgü kapsam ve nesne kuralı. Son satır her zaman `return False` olmalı.
```
:::

::: gorev 2 · Uygulamalara gereken en dar anahtarı bul
Her uygulamanın gerçekten yaptığı işlemlere bakarak anahtar genişliğini denetleyen `anahtar_kapsami(uygulamalar)` işlevini yaz.

- Anahtar düzeyleri dar → geniş: `'yok'` < `'salt-okunur'` < `'yonetici'`.
- Okuma işlemleri: `'search'`, `'scroll'`, `'retrieve'`, `'count'`. Yazma işlemleri: `'upsert'`, `'delete'`, `'create_collection'`, `'delete_collection'`.
- Gereken düzey: hiç işlem yoksa `'yok'`; yalnız okuma varsa `'salt-okunur'`; en az bir yazma varsa `'yonetici'`.
- Her uygulama `{'ad': str, 'anahtar': düzey, 'islemler': list[str]}`. `uygulamalar` `list` değilse; kayıt `dict` değilse; `ad` boş olmayan `str` değilse ya da tekrar ediyorsa; `anahtar` bilinen bir düzey değilse; `islemler` `list` değilse ya da bilinmeyen bir işlem içeriyorsa `ValueError`.
- Dönüş: `{ad: {'gereken': düzey, 'karar': 'fazla' | 'yetersiz' | 'uygun'}}`. Kullanılan anahtar gerekenden genişse `'fazla'`, darsa `'yetersiz'`, eşitse `'uygun'`.

KUSURLU başlangıç yalnız `'upsert'`'i yazma sayıyor ve işlemi olmayan uygulamaya `'salt-okunur'` gerektiğini söylüyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
_SIRA = ['yok', 'salt-okunur', 'yonetici']

def anahtar_kapsami(uygulamalar):
    sonuc = {}
    for u in uygulamalar:
        gereken = 'yonetici' if 'upsert' in u['islemler'] else 'salt-okunur'
        fark = _SIRA.index(u['anahtar']) - _SIRA.index(gereken)
        sonuc[u['ad']] = {'gereken': gereken, 'karar': 'fazla' if fark > 0 else 'uygun'}
    return sonuc
```

```solution
_SIRA = ('yok', 'salt-okunur', 'yonetici')
_OKUMA = {'search', 'scroll', 'retrieve', 'count'}
_YAZMA = {'upsert', 'delete', 'create_collection', 'delete_collection'}

def anahtar_kapsami(uygulamalar):
    if not isinstance(uygulamalar, list):
        raise ValueError('uygulamalar list olmali')
    gorulen = set()
    sonuc = {}
    for u in uygulamalar:
        if (not isinstance(u, dict) or not isinstance(u.get('ad'), str) or not u['ad'].strip()
                or u.get('anahtar') not in _SIRA or not isinstance(u.get('islemler'), list)
                or any(i not in _OKUMA and i not in _YAZMA for i in u['islemler'])):
            raise ValueError('bozuk uygulama kaydi')
        if u['ad'] in gorulen:
            raise ValueError('yinelenen ad')
        gorulen.add(u['ad'])
        if any(i in _YAZMA for i in u['islemler']):
            gereken = 'yonetici'
        elif u['islemler']:
            gereken = 'salt-okunur'
        else:
            gereken = 'yok'
        fark = _SIRA.index(u['anahtar']) - _SIRA.index(gereken)
        karar = 'fazla' if fark > 0 else ('yetersiz' if fark < 0 else 'uygun')
        sonuc[u['ad']] = {'gereken': gereken, 'karar': karar}
    return sonuc
```

```test
need('anahtar_kapsami')
import copy
def _u(ad, anahtar, islemler):
    return {'ad': ad, 'anahtar': anahtar, 'islemler': islemler}
_env = [
    _u('sohbet', 'yonetici', ['search', 'retrieve']),
    _u('indeksleyici', 'yonetici', ['upsert', 'search']),
    _u('raporlama', 'salt-okunur', ['count', 'scroll']),
    _u('temizlik', 'salt-okunur', ['delete']),
    _u('arsiv', 'yonetici', ['delete_collection']),
    _u('kurulum', 'salt-okunur', ['create_collection']),
    _u('emekli', 'salt-okunur', []),
    _u('kapali', 'yok', []),
    _u('yeni', 'yok', ['search']),
]
_yedek = copy.deepcopy(_env)
eq(anahtar_kapsami(_env), {
    'sohbet': {'gereken': 'salt-okunur', 'karar': 'fazla'},
    'indeksleyici': {'gereken': 'yonetici', 'karar': 'uygun'},
    'raporlama': {'gereken': 'salt-okunur', 'karar': 'uygun'},
    'temizlik': {'gereken': 'yonetici', 'karar': 'yetersiz'},
    'arsiv': {'gereken': 'yonetici', 'karar': 'uygun'},
    'kurulum': {'gereken': 'yonetici', 'karar': 'yetersiz'},
    'emekli': {'gereken': 'yok', 'karar': 'fazla'},
    'kapali': {'gereken': 'yok', 'karar': 'uygun'},
    'yeni': {'gereken': 'salt-okunur', 'karar': 'yetersiz'},
}, 'her uygulama için en dar gereken düzey ve karar')
eq(_env, _yedek, 'girdi değişmemeli')
eq(anahtar_kapsami([]), {}, 'boş liste')

raises(ValueError, anahtar_kapsami, tuple(_env), msg='liste olmayan girdi ValueError')
for _bozuk in (
    ['sohbet'],
    [{'anahtar': 'yok', 'islemler': []}],
    [{'ad': 'a', 'islemler': []}],
    [_u('', 'yok', [])],
    [_u('  ', 'yok', [])],
    [_u(5, 'yok', [])],
    [_u('a', 'admin', [])],
    [_u('a', None, [])],
    [_u('a', 'yok', 'search')],
    [_u('a', 'salt-okunur', ('search',))],
    [_u('a', 'yok', ['search', 'drop'])],
    [_u('a', 'yok', ['Search'])],
    [_u('a', 'yok', []), _u('a', 'yonetici', [])],
):
    raises(ValueError, anahtar_kapsami, _bozuk, msg=f'bozuk kayıt ValueError: {_bozuk!r}')
```

```hint
Düzeyleri sıralı bir demette tut ve karşılaştırmayı indeks farkıyla yap. Gereken düzeyi bulmak için önce yazma işlemine, sonra herhangi bir işleme bak.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Varsayılan (20 sn).** "Qdrant'ın açık kaynak kurulumu kimlik yapılandırılmazsa ulaşabilen herkesin isteğini kabul ediyor; iç ağda olmak koruma değil."
2. **Üç soru (30 sn).** "Her rota için sırayla kimlik, kapsam ve nesne sorduk. Kimliği ve kapsamı doğru bir token, başka kiracının koleksiyonunu istediğinde reddediliyor; OWASP API1 BOLA tam bu."
3. **Kenar durumlar (25 sn).** "Boş kiracının boş kiracıyla eşleşmesi, dizge olarak gelen scopes ve tanınmayan admin rotası testte ayrı ayrı reddediliyor."
4. **Anahtar genişliği (30 sn).** "Uygulamaların yaptığı işlemlere bakıp gereken en dar anahtarı bulduk: yalnız arayan sohbet uygulaması yönetici anahtarı taşıyordu, silme yapan temizlik işi ise salt okunur anahtarla çalışmaya çalışıyordu."
5. **Sınır (15 sn).** "Rotalar ve işlemler sentetik; gerçek Qdrant'ta koleksiyon başına JWT ile anahtar daha da daraltılabilir."
:::

::: anlat Sınır ve kaynak
Bu ders üç rotalı sentetik bir ağ geçidini ve dört okuma/dört yazma işlemini modeller. Gerçek Qdrant'ın JWT tabanlı anahtarları koleksiyon başına okuma/yazma ayrımı da yapar; bu derste anahtar düzeyi koleksiyondan bağımsızdır. Token doğrulaması, TLS, ağ sınırları ve hız sınırı kapsam dışıdır. "İşlemler" listesi gözlem penceresi kadar doğrudur; nadiren çalışan bir yazma işi kısa pencerede görünmeyebilir.

- Birincil kaynaklar: [Qdrant — Security & Access Control](https://qdrant.tech/documentation/security/) (açık kaynakta varsayılan kimliksiz, yönetici ve salt okunur API anahtarı, JWT tabanlı ayrıntılı erişim); [OWASP API Security Top 10 2023 — API1: Broken Object Level Authorization](https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/). Doğrulama tarihi: 11 Kasım 2026.
:::

::: dusun
Ağ geçidi `tenant` değerini token'dan, `resource_tenant` değerini ise isteğin URL'sindeki koleksiyon adından çıkarıyor. Koleksiyon adı `musteri-a-yedek` gibi bir biçimde olduğunda kiracıyı addan çıkarmak neden kırılgandır? Kiracıyı koleksiyonun kendi meta verisinden okumak neyi değiştirir?
:::

::: ozet
- Kimlik yapılandırılmamış bir vektör veritabanı ulaşabilen herkese açıktır; iç ağ bir yetki değildir.
- Yetki kapısı rota başına kimlik, kapsam ve nesne sorularını sırayla sorar; tanınmayan rota reddedilir.
- Kimliği ve kapsamı doğru bir isteğin başka kiracının nesnesine ulaşması BOLA'dır.
- Her uygulamaya, gerçekten yaptığı işlemlerin gerektirdiği en dar anahtar verilir.
:::
