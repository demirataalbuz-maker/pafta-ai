---
id: ai-bulut-01
title: "Paylaşılan Sorumluluk ve Güven Sınırları"
summary: Sorumluluğun hizmet modeline göre nasıl kaydığını (IaaS'tan yönetilen model API'sine) yerel bir kontrol envanteriyle modelle; eksik kanıtı doğru tarafa yönlendir.
esleme: ai-temel-16, ai-savunma-11, ai-guvence-34, ai-bulut-02
timeout: 30
---

::: anlat 1. Model: bulutun güvenliği ile buluttaki güvenlik
AWS'nin *Shared Responsibility Model* sayfası ayrımı iki ifadeyle kurar: sağlayıcı bulutun güvenliğinden (*security of the cloud*: fiziksel tesis, donanım, sanallaştırma katmanı), müşteri buluttaki güvenlikten (*security in the cloud*: kimlikler, veri, uygulama, yapılandırma) sorumludur. Aynı sayfa ikinci ve daha önemli bir şey söyler: müşterinin payı **seçtiği hizmete göre değişir**. EC2 gibi bir IaaS sunucusunda konuk işletim sisteminin yamaları müşterinindir; S3 ya da DynamoDB gibi soyutlanmış hizmetlerde aynı katmanı sağlayıcı işletir.

Amazon Bedrock gibi yönetilen bir model API'si soyutlama merdiveninin en üstündedir. Model sunucusu, GPU sürücüsü ve işletim sistemi sağlayıcıdadır; ama şunlar hâlâ müşteridedir:

- **Kimlik ve yetki (`iam`):** hangi rolün hangi modeli çağırabileceği (`ai-bulut-02`).
- **Veri (`data`):** isteme konan verinin sınıfı, çağrı günlüklerinin açılıp açılmadığı ve kimin okuyabildiği (`ai-bulut-03`).
- **Uygulama (`app`):** modelin önerdiği araç çağrısına izin verip vermemek. Model hizmeti bu kararı vermez; uygulamanın yetkilendirme katmanı verir (`ai-savunma-11`).

Sayfa bir de *shared controls* sayar: yama yönetimi, yapılandırma yönetimi, farkındalık ve eğitim. Bunlarda iki tarafın da işi vardır: sağlayıcı kendi altyapısını yamalar, müşteri kendi uygulamasını.

> [!NOTE]
> Bu ders bir sağlayıcının sözleşmesini kopyalamaz. Aşağıdaki katman → sahip tablosu, iki hizmet modelini karşılaştırmak için kurulmuş **sentetik** bir alt kümedir; gerçek bir hizmetin sorumluluk dağılımı o hizmetin kendi belgesinden okunur. Gerçek hesap, kimlik bilgisi ya da ağ çağrısı yoktur.
:::

::: anlat 2. Mekanizma: kontrolün sahibi ile kanıtın sahibi
Bir denetimde her kontrol için iki soru sorulur: **kim uygular** ve **kanıt kimde**. Sağlayıcının uyguladığı kontrolün kanıtı müşterinin elinde değildir; sağlayıcının denetim raporundan (ör. SOC 2) istenir. Müşterinin uyguladığı kontrolün kanıtı ise müşterinin kendi kaydıdır: IAM politikası, günlük yapılandırması, yetki testi.

Bu ayrım karıştığında iki tür hata olur:

1. **Sahipsiz kontrol:** "Yönetilen hizmet, güvenliği de onlar sağlıyor" varsayımıyla müşteri `iam` ya da `app` kontrolünü kimseye atamaz. Kontrol vardır ama işleten yoktur.
2. **Yanlış yere giden eylem:** Sağlayıcının işlettiği bir katmandaki eksik kanıt için müşteri kendi ekibine iş açar; oysa yapılacak iş sağlayıcıdan rapor istemektir.

Hizmet modeli değiştiğinde (ör. kendi GPU sunucusunda model barındırmaktan yönetilen API'ye geçiş) yalnız bazı katmanların sahibi değişir. Bu derste o katman `os`'tur: IaaS'ta müşteri, yönetilen modelde sağlayıcı.

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| "Yönetilen hizmet = sağlayıcının sorumluluğu" | `iam`, `data` ve `app` her hizmet modelinde müşteride kalır | Katman katman sahip tablosu, hizmet modeline göre |
| Tek bir sabit tablo kullanmak | `os` gibi katmanların sahibi hizmet modeliyle değişir | Tabloyu `hizmet` girdisine bağlamak |
| Eksik her kanıt için iç ekibe iş açmak | Sağlayıcı katmanında müşteri kontrolü uygulayamaz | Sağlayıcı katmanı → rapor iste; ortak katman → iki taraf |
| Bilinmeyen katmanı sessizce atlamak | Envanterde sahipsiz kontrol kalır | Bilinmeyen katman ya da hizmet `ValueError` |
:::

::: tahmin Aynı katmanın sahibi hizmet modeline göre değişir mi?
Aşağıdaki tablo iki hizmet modelinde konuk işletim sistemi (`os`) ve kimlik (`iam`) katmanlarının sahibini gösteriyor. Çıktıyı tahmin et.

```python
SAHIP = {
    'iaas': {'os': 'customer', 'iam': 'customer'},
    'yonetilen-model': {'os': 'provider', 'iam': 'customer'},
}
for hizmet in ('iaas', 'yonetilen-model'):
    print(hizmet, '->', SAHIP[hizmet]['os'], SAHIP[hizmet]['iam'])
```

???

```cikti
iaas -> customer customer
yonetilen-model -> provider customer
```
Yönetilen modele geçmek işletim sistemi yamasını sağlayıcıya devreder; ama kimin hangi modeli çağırabileceğine karar vermek müşteride kalır. "Yönetilen" kelimesi `iam` satırını değiştirmez.
:::

::: gorev 1 · Kontrol envanterine sahip ve eksik kanıt ata
`sorumluluk_kontrolu(kontroller, hizmet)` işlevini yaz.

- `hizmet` `'iaas'` ya da `'yonetilen-model'` olmalı; değilse `ValueError`.
- `kontroller` bir `list`; her kayıt `{'id': str, 'katman': str, 'kanit': str | None}` sözlüğüdür. `id` boş olmayan `str` değilse, kayıt `dict` değilse, katman tanınmıyorsa ya da aynı `id` iki kez geçiyorsa `ValueError`.
- Sahip tablosu:

| Katman | `iaas` | `yonetilen-model` |
|---|---|---|
| `physical` | `provider` | `provider` |
| `os` | `customer` | `provider` |
| `iam`, `data`, `app` | `customer` | `customer` |
| `transport` | `shared` | `shared` |

- Dönüş: her kayıt için girdi sırasıyla `[id, sahip, eksik]`. `eksik`, `kanit` boş dizge, yalnız boşluk, `None` ya da hiç yoksa `True`; dolu bir `str` ise `False`. `str` olmayan bir `kanit` (ör. `1`, `True`) kanıt sayılmaz, `eksik = True`.
- Girdi listesini ve sözlükleri değiştirme.

KUSURLU başlangıç tek bir sabit tablo kullanıyor (hizmet modelini yok sayıyor), bilinmeyen katmanı sessizce `customer` sayıyor ve `kanit`'in doğruluk değerine bakıyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
Path('ornek.json').write_text('[[{"id": "c1", "katman": "physical", "kanit": "soc2-2026"}, {"id": "c2", "katman": "os", "kanit": ""}, {"id": "c3", "katman": "iam", "kanit": null}], "yonetilen-model"]', encoding='utf-8')
```

```starter
def sorumluluk_kontrolu(kontroller, hizmet):
    sahip = {'physical': 'provider', 'os': 'customer', 'iam': 'customer',
             'data': 'customer', 'app': 'customer', 'transport': 'shared'}
    return [[k['id'], sahip.get(k['katman'], 'customer'), not k.get('kanit')] for k in kontroller]

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(sorumluluk_kontrolu(*_args))
```

```solution
_SAHIP = {
    'iaas': {'physical': 'provider', 'os': 'customer', 'iam': 'customer',
             'data': 'customer', 'app': 'customer', 'transport': 'shared'},
    'yonetilen-model': {'physical': 'provider', 'os': 'provider', 'iam': 'customer',
                        'data': 'customer', 'app': 'customer', 'transport': 'shared'},
}

def sorumluluk_kontrolu(kontroller, hizmet):
    if hizmet not in _SAHIP:
        raise ValueError('hizmet iaas ya da yonetilen-model olmali')
    if not isinstance(kontroller, list):
        raise ValueError('kontroller list olmali')
    tablo = _SAHIP[hizmet]
    gorulen = set()
    sonuc = []
    for k in kontroller:
        if not isinstance(k, dict) or not isinstance(k.get('id'), str) or not k['id'].strip():
            raise ValueError('her kayit bos olmayan str id tasiyan dict olmali')
        if k.get('katman') not in tablo:
            raise ValueError('bilinmeyen katman')
        if k['id'] in gorulen:
            raise ValueError('yinelenen id')
        gorulen.add(k['id'])
        kanit = k.get('kanit')
        eksik = not (isinstance(kanit, str) and kanit.strip())
        sonuc.append([k['id'], tablo[k['katman']], eksik])
    return sonuc

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(sorumluluk_kontrolu(*_args))
```

```test
need('sorumluluk_kontrolu')
import copy
_env = [
    {'id': 'k-fiz', 'katman': 'physical', 'kanit': 'soc2-2026'},
    {'id': 'k-os', 'katman': 'os', 'kanit': 'yama-raporu'},
    {'id': 'k-iam', 'katman': 'iam', 'kanit': ''},
    {'id': 'k-veri', 'katman': 'data', 'kanit': None},
    {'id': 'k-uyg', 'katman': 'app', 'kanit': 'arac-yetki-testi'},
    {'id': 'k-tls', 'katman': 'transport', 'kanit': '   '},
]
_yedek = copy.deepcopy(_env)
eq(sorumluluk_kontrolu(_env, 'iaas'), [
    ['k-fiz', 'provider', False], ['k-os', 'customer', False], ['k-iam', 'customer', True],
    ['k-veri', 'customer', True], ['k-uyg', 'customer', False], ['k-tls', 'shared', True],
], 'IaaS: işletim sistemi müşteride; boş, None ve yalnız boşluk kanıt eksik')
eq(sorumluluk_kontrolu(_env, 'yonetilen-model'), [
    ['k-fiz', 'provider', False], ['k-os', 'provider', False], ['k-iam', 'customer', True],
    ['k-veri', 'customer', True], ['k-uyg', 'customer', False], ['k-tls', 'shared', True],
], 'yönetilen model: işletim sistemi sağlayıcıya geçer, iam/data/app müşteride kalır')
eq(_env, _yedek, 'girdi değişmemeli')
eq(sorumluluk_kontrolu([], 'iaas'), [], 'boş envanter boş liste')
eq(sorumluluk_kontrolu([{'id': 'a', 'katman': 'app'}], 'iaas'), [['a', 'customer', True]], 'kanit anahtarı yoksa eksik')
for _k in (1, True, ['rapor']):
    eq(sorumluluk_kontrolu([{'id': 'a', 'katman': 'iam', 'kanit': _k}], 'iaas'), [['a', 'customer', True]],
       f'str olmayan kanıt sayılmaz: {_k!r}')

for _hizmet in ('IAAS', 'saas', None, ''):
    raises(ValueError, sorumluluk_kontrolu, [], _hizmet, msg=f'bilinmeyen hizmet ValueError: {_hizmet!r}')
raises(ValueError, sorumluluk_kontrolu, tuple(_env), 'iaas', msg='liste olmayan envanter ValueError')
for _bozuk in (
    ['k1'],
    [{'katman': 'iam', 'kanit': 'x'}],
    [{'id': 5, 'katman': 'iam', 'kanit': 'x'}],
    [{'id': '  ', 'katman': 'iam', 'kanit': 'x'}],
    [{'id': 'a', 'katman': 'network', 'kanit': 'x'}],
    [{'id': 'a', 'katman': 'IAM', 'kanit': 'x'}],
    [{'id': 'a', 'katman': 'iam', 'kanit': 'x'}, {'id': 'a', 'katman': 'app', 'kanit': 'y'}],
):
    raises(ValueError, sorumluluk_kontrolu, _bozuk, 'yonetilen-model', msg=f'bozuk kayıt ValueError: {_bozuk!r}')
```

```hint
Önce `hizmet`'i doğrula ve ona ait tabloyu seç; sonra her kaydı tek tek doğrula. Eksik kanıt için `not kanit` yerine "dolu bir str mi?" diye sor: `isinstance(kanit, str) and kanit.strip()`.
```
:::

::: gorev 2 · Eksik kanıtı doğru tarafa yönlendir
Görev 1'in çıktısını (`[id, sahip, eksik]` listesi) alıp eylem planı üreten `eylem_plani(atamalar)` işlevini yaz.

- Yalnız `eksik is True` olan satırlar plana girer.
- `sahip == 'customer'` → `'ic_ekip'`; `sahip == 'shared'` → hem `'ic_ekip'` hem `'saglayicidan_iste'`; `sahip == 'provider'` → yalnız `'saglayicidan_iste'` (müşteri o katmanı kendisi düzeltemez; sağlayıcının denetim raporunu ister).
- Dönüş: `{'ic_ekip': [...], 'saglayicidan_iste': [...]}`; her liste girdideki sırayla `id`'leri taşır.
- `atamalar` `list` değilse; bir satır `list`/`tuple` değilse, 3 elemanlı değilse, `id` boş olmayan `str` değilse, `sahip` bu üç değerden biri değilse ya da `eksik` `bool` değilse `ValueError`.

KUSURLU başlangıç her eksik satırı iç ekibe atıyor; ortak katmanı sağlayıcıya, sağlayıcı katmanını da iç ekibe gönderiyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def eylem_plani(atamalar):
    plan = {'ic_ekip': [], 'saglayicidan_iste': []}
    for kid, sahip, eksik in atamalar:
        if eksik:
            plan['ic_ekip'].append(kid)
    return plan
```

```solution
_SAHIPLER = ('customer', 'shared', 'provider')

def eylem_plani(atamalar):
    if not isinstance(atamalar, list):
        raise ValueError('atamalar list olmali')
    plan = {'ic_ekip': [], 'saglayicidan_iste': []}
    for satir in atamalar:
        if not isinstance(satir, (list, tuple)) or len(satir) != 3:
            raise ValueError('her satir [id, sahip, eksik] olmali')
        kid, sahip, eksik = satir
        if not isinstance(kid, str) or not kid.strip() or sahip not in _SAHIPLER or type(eksik) is not bool:
            raise ValueError('bozuk satir')
        if not eksik:
            continue
        if sahip in ('customer', 'shared'):
            plan['ic_ekip'].append(kid)
        if sahip in ('shared', 'provider'):
            plan['saglayicidan_iste'].append(kid)
    return plan
```

```test
need('eylem_plani')
_atama = [
    ['k-fiz', 'provider', True],
    ['k-os', 'customer', False],
    ['k-iam', 'customer', True],
    ['k-tls', 'shared', True],
    ['k-uyg', 'customer', False],
    ['k-hv', 'provider', False],
    ('k-veri', 'customer', True),
]
eq(eylem_plani(_atama), {
    'ic_ekip': ['k-iam', 'k-tls', 'k-veri'],
    'saglayicidan_iste': ['k-fiz', 'k-tls'],
}, 'müşteri katmanı iç ekibe, sağlayıcı katmanı rapor istemeye, ortak katman ikisine')
eq(eylem_plani([]), {'ic_ekip': [], 'saglayicidan_iste': []}, 'boş atama boş plan')
eq(eylem_plani([['a', 'shared', False], ['b', 'provider', False]]), {'ic_ekip': [], 'saglayicidan_iste': []},
   'kanıtı tam satırlar plana girmez')

raises(ValueError, eylem_plani, tuple(_atama), msg='liste olmayan atama ValueError')
for _bozuk in (
    ['k-iam'],
    [['k', 'customer']],
    [['k', 'customer', True, 'ek']],
    [['', 'customer', True]],
    [['  ', 'customer', True]],
    [[5, 'customer', True]],
    [['k', 'musteri', True]],
    [['k', 'customer', 1]],
    [['k', 'customer', 'evet']],
    [{'k': 1, 'customer': 2, True: 3}],
):
    raises(ValueError, eylem_plani, _bozuk, msg=f'bozuk satır ValueError: {_bozuk!r}')
```

```hint
Satırı açmadan önce uzunluğunu doğrula. `shared` iki listeye birden girer; bunu iki ayrı `if` ile yazmak `if/elif` zincirinden daha az hata çıkarır.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Model (20 sn).** "Sağlayıcı bulutun güvenliğinden, biz buluttaki güvenlikten sorumluyuz; ama çizgi hizmete göre kayar."
2. **Kayma (30 sn).** "Kendi GPU sunucumuzda model barındırırken işletim sistemi yaması bizdeydi. Yönetilen model API'sine geçince o katman sağlayıcıya geçti; kimin hangi modeli çağırabileceği ise hâlâ bizde."
3. **Hata türleri (30 sn).** "İki tür hata görüyoruz: 'yönetilen hizmet, onlar halleder' deyip iam ve uygulama kontrollerini sahipsiz bırakmak; ya da sağlayıcı katmanındaki eksik için iç ekibe iş açmak."
4. **Çıktı (25 sn).** "Envanteri hizmet modeline göre etiketleyip eksik kanıtı ayırdık: bizimkiler iç ekibe, sağlayıcınınkiler rapor talebine, ortak olanlar ikisine."
5. **Sınır (15 sn).** "Tablo sentetik; gerçek dağılımı her hizmetin kendi belgesinden okuyoruz."
:::

::: anlat Sınır ve kaynak
Bu ders iki hizmet modelini ve altı katmanı karşılaştıran sentetik bir envanterdir. Gerçek sağlayıcılarda katman sayısı çok daha fazladır, aynı katman hizmetten hizmete farklı bölünebilir ve kontrol kanıtı denetim raporlarıyla (ör. SOC 2) gelir. Bu derste rapor okunmaz, gerçek hesap ya da kimlik bilgisi kullanılmaz; kararın doğruluğu yalnız tablodaki sözleşmeyle sınırlıdır.

- Birincil kaynaklar: [AWS — Shared Responsibility Model](https://aws.amazon.com/compliance/shared-responsibility-model/) (*security of / in the cloud*, hizmete göre değişen müşteri payı, *shared controls*); [Amazon Bedrock — Security, Guardrails, and Observability](https://docs.aws.amazon.com/bedrock/latest/userguide/security.html) (modelin Bedrock'a uygulanışı). Doğrulama tarihi: 11 Kasım 2026.
:::

::: dusun
Ekibin kendi GPU kümesinde açık ağırlıklı bir model barındırdığını, ama gömme (embedding) için yönetilen bir API kullandığını düşün. Aynı uygulamada iki farklı hizmet modeli varsa `os` ve `data` katmanlarının sahibini nasıl yazarsın? Tek satır mı, iki satır mı?
:::

::: ozet
- Sağlayıcı bulutun, müşteri buluttaki güvenlikten sorumludur; çizgi hizmet modeline göre kayar.
- Yönetilen model API'sinde işletim sistemi sağlayıcıya geçer; kimlik, veri ve uygulama yetkisi müşteride kalır.
- Her kontrol için hem uygulayıcı hem kanıt sahibi yazılır; eksik kanıt sahibine göre iç ekibe ya da sağlayıcıya yönlendirilir.
- Bilinmeyen katman ya da hizmet sessizce varsayılana düşmez; hata verir.
:::
