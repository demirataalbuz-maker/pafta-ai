---
id: kuantum-24
title: "SSH ve VPN · Yapılandırma ile Negotiation Ayrımı"
summary: SSH anahtar değişiminde teklif edilen listeyi gerçekten seçilen algoritmadan ayır; kuantum sonrası hibrit seçilip seçilmediğini belirle ve bir VPN geçiş kaydında etkinleştirme, anlaşma, eş doğrulaması ve geri dönüş testi kanıtlarını ayrı ayrı denetle.
esleme: kuantum-23, kuantum-28, kuantum-21, kuantum-22
timeout: 30
---

::: anlat 1. "Etkin" ile "kullanılıyor" aynı şey değildir
OpenSSH'in *Post-Quantum Cryptography* sayfası, hibrit anahtar değişiminin amacını "şimdi topla, sonra çöz" (*store now, decrypt later*) saldırısına karşı koruma olarak açıklar: bugün kaydedilen bir oturum, ileride kuantum bilgisayarla çözülmesin. OpenSSH'in sürüm notlarına göre bu geçiş adım adım geldi:

| Sürüm | Değişiklik |
|---|---|
| 8.5 (Mart 2021) | `sntrup761x25519-sha512@openssh.com` eklendi (varsayılan kapalı) |
| 9.0 (Nisan 2022) | `sntrup761x25519-sha512@openssh.com` varsayılan anahtar değişimi oldu |
| 9.9 (Eylül 2024) | `mlkem768x25519-sha256` eklendi; NTRU hibriti IANA adıyla `sntrup761x25519-sha512` olarak da sunuldu |
| 10.0 (Nisan 2025) | `mlkem768x25519-sha256` varsayılan oldu |
| 10.1 | Kuantum sonrası olmayan bir anahtar değişimi seçildiğinde uyarı (`WarnWeakCrypto` ile kapatılabilir) |

Bir sunucunun yapılandırmasında hibrit algoritmanın **listede olması**, bağlantının onu **kullandığı** anlamına gelmez. SSH'ta istemci ve sunucu birer algoritma listesi gönderir; seçilen, istemcinin listesinde ilk sırada olan ve sunucunun da desteklediği algoritmadır. İstemcinin listesinde klasik `curve25519-sha256` öndeyse, iki taraf da hibriti desteklese bile klasik olan seçilir.

> [!NOTE]
> Bu derste gerçek bir SSH ya da VPN bağlantısı kurulmaz, sistemdeki yapılandırma değiştirilmez. Algoritma listeleri ve VPN kabul kayıtları **sentetiktir**.
:::

::: anlat 2. Mekanizma: dört ayrı kanıt
Kuantum sonrası geçişin "tamam" sayılması için dört ayrı kanıt gerekir ve her biri ayrı bir soruya yanıt verir:

1. **Etkinleştirildi mi?** Yapılandırmada hibrit algoritma açık mı? (`hybrid_enabled`)
2. **Gerçekten anlaşıldı mı?** Bir bağlantı kaydında seçilen algoritma hibrit mi? (`negotiated_hybrid`) Bu, birinciden farklıdır: sıra, eski bir eş ya da araya giren bir orta kutu klasik algoritmaya düşürebilir.
3. **Eş doğrulandı mı?** Anahtar değişiminin hibrit olması, karşı tarafın kim olduğunu kanıtlamaz. Kimlik doğrulama (SSH host anahtarı imzası, VPN sertifikası) ayrı bir algoritma ve ayrı bir kanıttır. (`peer_verified`)
4. **Geri dönüş sınandı mı?** Hibriti desteklemeyen bir eşle bağlantının ne yaptığı test edildi mi: reddediyor mu, klasik algoritmaya mı düşüyor? (`rollback_tested`)

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| "Listede var, kullanılıyor" | Seçim istemci listesinin sırasına bağlıdır | Seçileni bağlantı kaydından oku |
| Sunucunun sırasını belirleyici sanmak | SSH'ta istemcinin tercih sırası esastır | İstemci sırasıyla, sunucuda olan ilk algoritma |
| Hibrit KEX = kuantuma dayanıklı kimlik | Host anahtarı imzası hâlâ klasik olabilir | Kimlik doğrulamayı ayrı kanıtla |
| `@openssh.com` adını bilinmeyen saymak | Aynı hibrit iki adla anılır | İki adı da tanı |
| Geri dönüş testini atlamak | Eski eşle sessizce klasik algoritmaya düşülür | Klasik eşle bağlantıyı ayrıca sına |
:::

::: tahmin İki taraf da hibriti destekliyor; seçilen ne?
İstemcinin listesinde klasik algoritma önde. Sunucu hibriti de klasiği de destekliyor. Seçilen algoritma ne?

```python
istemci = ['curve25519-sha256', 'mlkem768x25519-sha256']
sunucu = ['mlkem768x25519-sha256', 'curve25519-sha256']
secilen = next((a for a in istemci if a in sunucu), None)
print(secilen)
```

???

```cikti
curve25519-sha256
```
İki taraf da hibriti desteklemesine rağmen klasik algoritma seçildi; çünkü istemcinin tercih sırasında o önde. "Sunucuda hibrit etkin" kanıtı bu bağlantının hibrit olduğunu göstermez.
:::

::: gorev 1 · SSH anahtar değişimi anlaşmasını denetle
`ssh_kex(client, server)` işlevini yaz.

- `client` ve `server` boş olmayan `str`'lerden oluşan `list`'ler. Değilse `ValueError`.
- Seçilen algoritma: `client` listesinde sırayla gezilir; `server` listesinde de bulunan **ilk** algoritma seçilir; ortak yoksa `None`.
- Kuantum sonrası hibrit kabul listesi: `mlkem768x25519-sha256`, `sntrup761x25519-sha512`, `sntrup761x25519-sha512@openssh.com`.
- Dönüş: `{'negotiated': seçilen, 'pq_hybrid': seçilen hibrit listesindeyse True}`.

KUSURLU başlangıç sunucunun sırasına bakıyor ve "listede hibrit varsa" `pq_hybrid = True` diyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
Path('ornek.json').write_text('[["curve25519-sha256", "mlkem768x25519-sha256"], ["mlkem768x25519-sha256", "curve25519-sha256"]]', encoding='utf-8')
```

```starter
_PQ = {'mlkem768x25519-sha256', 'sntrup761x25519-sha512', 'sntrup761x25519-sha512@openssh.com'}

def ssh_kex(client, server):
    secilen = next((a for a in server if a in client), None)
    return {'negotiated': secilen, 'pq_hybrid': any(a in _PQ for a in client)}

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(ssh_kex(*_args))
```

```solution
_PQ = ('mlkem768x25519-sha256', 'sntrup761x25519-sha512', 'sntrup761x25519-sha512@openssh.com')

def ssh_kex(client, server):
    for liste in (client, server):
        if not isinstance(liste, list) or any(not isinstance(a, str) or not a for a in liste):
            raise ValueError('client ve server bos olmayan str listesi olmali')
    secilen = next((a for a in client if a in server), None)
    return {'negotiated': secilen, 'pq_hybrid': secilen in _PQ}

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(ssh_kex(*_args))
```

```test
need('ssh_kex')
import copy
_C = 'curve25519-sha256'
_M = 'mlkem768x25519-sha256'
_N = 'sntrup761x25519-sha512'
_NO = 'sntrup761x25519-sha512@openssh.com'
_c, _s = [_C, _M], [_M, _C]
_yedek = copy.deepcopy((_c, _s))
eq(ssh_kex(_c, _s), {'negotiated': _C, 'pq_hybrid': False}, 'istemci sırası esas: klasik önde')
eq((_c, _s), _yedek, 'listeler değişmemeli')
eq(ssh_kex([_M, _C], [_C, _M]), {'negotiated': _M, 'pq_hybrid': True}, 'istemci hibriti öne koyunca hibrit')
eq(ssh_kex([_NO, _C], [_C, _NO]), {'negotiated': _NO, 'pq_hybrid': True}, '@openssh.com adı da hibrit')
eq(ssh_kex([_N], [_N]), {'negotiated': _N, 'pq_hybrid': True}, 'IANA adı da hibrit')
eq(ssh_kex([_M, 'diffie-hellman-group14-sha256'], ['diffie-hellman-group14-sha256']),
   {'negotiated': 'diffie-hellman-group14-sha256', 'pq_hybrid': False}, 'sunucu hibriti desteklemiyorsa klasiğe düşülür')
eq(ssh_kex([_M], [_C]), {'negotiated': None, 'pq_hybrid': False}, 'ortak algoritma yoksa None')
eq(ssh_kex([], [_M]), {'negotiated': None, 'pq_hybrid': False}, 'boş istemci listesi')
eq(ssh_kex(['MLKEM768X25519-SHA256'], ['MLKEM768X25519-SHA256']), {'negotiated': 'MLKEM768X25519-SHA256', 'pq_hybrid': False},
   'algoritma adları harfe duyarlı')
for _arg in ((None, [_M]), ([_M], None), ((_M,), [_M]), ([_M], (_M,)), ([_M, 5], [_M]), ([_M], [_M, '']), ([''], [_M])):
    raises(ValueError, ssh_kex, *_arg, msg=f'bozuk liste ValueError: {_arg!r}')
```

```hint
`next((a for a in client if a in server), None)` istemci sırasıyla ilk ortak algoritmayı verir. `pq_hybrid` kararı listeye değil, seçilen algoritmaya bakmalı.
```
:::

::: gorev 2 · VPN geçiş kaydında eksik kanıtları bul
`vpn_kayit(kayit)` işlevini yaz. Kayıt, bir kurumun kuantum sonrası VPN geçişi için tuttuğu sentetik kabul kaydıdır.

- `kayit` `dict` değilse `ValueError`.
- Aşağıdaki dört alan **bu sırayla** denetlenir; alan tam olarak `True` değilse ilgili eksik eklenir:
  1. `hybrid_enabled` → `'not-enabled'`;
  2. `negotiated_hybrid` → `'not-negotiated'`;
  3. `peer_verified` → `'peer-unverified'`;
  4. `rollback_tested` → `'rollback-untested'`.
- Dönüş: eksik listesi (`[]` ise geçiş kanıtlarıyla tamamdır).

KUSURLU başlangıç alanların doğruluk değerine bakıyor ve "etkin" kanıtını "anlaşıldı" yerine sayıyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def vpn_kayit(kayit):
    eksik = []
    if not kayit.get('hybrid_enabled'):
        eksik += ['not-enabled', 'not-negotiated']
    if not kayit.get('peer_verified'):
        eksik.append('peer-unverified')
    if not kayit.get('rollback_tested'):
        eksik.append('rollback-untested')
    return eksik
```

```solution
_KONTROL = (('hybrid_enabled', 'not-enabled'), ('negotiated_hybrid', 'not-negotiated'),
            ('peer_verified', 'peer-unverified'), ('rollback_tested', 'rollback-untested'))

def vpn_kayit(kayit):
    if not isinstance(kayit, dict):
        raise ValueError('kayit dict olmali')
    return [etiket for alan, etiket in _KONTROL if kayit.get(alan) is not True]
```

```test
need('vpn_kayit')
import copy
_tam = {'hybrid_enabled': True, 'negotiated_hybrid': True, 'peer_verified': True, 'rollback_tested': True}
_yedek = copy.deepcopy(_tam)
eq(vpn_kayit(_tam), [], 'dört kanıt tam')
eq(_tam, _yedek, 'girdi değişmemeli')
eq(vpn_kayit({}), ['not-enabled', 'not-negotiated', 'peer-unverified', 'rollback-untested'], 'boş kayıtta dört eksik, sabit sırada')
eq(vpn_kayit(dict(_tam, negotiated_hybrid=False)), ['not-negotiated'], 'etkin ama anlaşılmamış: yalnız anlaşma eksik')
for _alan, _etiket in (('hybrid_enabled', 'not-enabled'), ('negotiated_hybrid', 'not-negotiated'),
                       ('peer_verified', 'peer-unverified'), ('rollback_tested', 'rollback-untested')):
    for _deger in (False, 1, 'true', None):
        eq(vpn_kayit(dict(_tam, **{_alan: _deger})), [_etiket], f'{_alan}={_deger!r} kanıt sayılmaz')
for _bozuk in (None, [], 'kayit'):
    raises(ValueError, vpn_kayit, _bozuk, msg=f'dict olmayan kayıt ValueError: {_bozuk!r}')
```

```hint
Dört alanı ve etiketlerini sıralı bir demette tut; her biri için `is not True` denetle. Bir alanın eksikliği diğerini otomatik eksik yapmaz.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Amaç (20 sn).** "OpenSSH hibrit anahtar değişimini 'şimdi topla, sonra çöz' saldırısına karşı koyuyor. 10.0'dan beri mlkem768x25519 varsayılan, 10.1 de klasik seçilince uyarıyor."
2. **Liste ≠ seçim (30 sn).** "İki taraf da hibriti desteklediği hâlde istemci klasik algoritmayı öne koyunca klasik seçildi. Seçimi istemcinin tercih sırası belirliyor; 'sunucuda etkin' kanıtı yetmiyor."
3. **İki ad (20 sn).** "NTRU hibriti hem @openssh.com uzantılı adla hem IANA adıyla anılıyor; denetim ikisini de tanıyor."
4. **Dört kanıt (30 sn).** "VPN geçişinde etkinleştirme, gerçek anlaşma, eş doğrulaması ve geri dönüş testini ayrı ayrı istedik. Anahtar değişiminin hibrit olması karşı tarafın kim olduğunu kanıtlamıyor."
5. **Sınır (20 sn).** "Bağlantı kurulmadı; listeler ve kayıtlar sentetik. Gerçek kanıt bağlantı günlüğünden ve ağ ölçümünden gelir."
:::

::: anlat Sınır ve kaynak
Bu ders anlaşma kuralının yalnız anahtar değişimi algoritma seçimini modeller; SSH'ın diğer algoritma listeleri (host anahtarı, şifre, MAC), `ext-info` ve sıkı anahtar değişimi gibi uzantı sözde-algoritmaları kapsam dışıdır. VPN kayıt alanları bir ürünün yapılandırma anahtarları değil, kurumun sentetik kabul kaydı alanlarıdır. Gerçek bir sistemde "anlaşıldı" kanıtı bağlantı günlüğünden ya da paket yakalamasından okunur.

- Birincil kaynaklar: [OpenSSH — Post-Quantum Cryptography](https://www.openssh.org/pq.html) (*store now, decrypt later*, 10.0 varsayılanı, 10.1 uyarısı ve `WarnWeakCrypto`); [OpenSSH — Release Notes](https://www.openssh.org/releasenotes.html) (8.5, 9.0, 9.9 ve 10.0 sürüm notları). Doğrulama tarihi: 11 Kasım 2026.
:::

::: dusun
Şirketin SSH sunucuları OpenSSH 10.x çalıştırıyor, ama çalışanların bir kısmı eski bir istemci kullanıyor. Sunucu tarafında hibrit dışındaki algoritmaları kapatmak "şimdi topla, sonra çöz" riskini kapatır; bunun bedeli nedir? Görev 2'deki hangi kanıt bu kararın etkisini ölçer?
:::

::: ozet
- Yapılandırmada etkin olmak ile bağlantıda seçilmek farklı kanıtlardır.
- SSH'ta seçilen algoritma, istemcinin listesindeki ve sunucunun da desteklediği ilk algoritmadır.
- `mlkem768x25519-sha256` OpenSSH 10.0'dan beri varsayılandır; NTRU hibriti iki adla anılır.
- Geçiş kabulü dört kanıt ister: etkinleştirme, anlaşma, eş doğrulaması ve geri dönüş testi.
:::
