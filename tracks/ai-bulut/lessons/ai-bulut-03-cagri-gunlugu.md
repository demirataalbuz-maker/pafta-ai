---
id: ai-bulut-03
title: "Model Çağrı Günlükleri · Açıklık ve Gizlilik"
summary: İki günlük katmanını (kim çağırdı / ne söylendi) ayır; çağrı günlüğü yapılandırmasını denetle ve CloudTrail benzeri olaylarda LLMjacking keşif izlerini yakala.
esleme: ai-temel-20, ai-savunma-31, ai-bulut-06, ai-bulut-02
timeout: 30
---

::: anlat 1. İki günlük, iki soru
Amazon Bedrock'ta bir model çağrısı iki ayrı yere iz bırakabilir:

1. **CloudTrail: kim, ne zaman, hangi işlemi çağırdı?** Bedrock belgesine göre `InvokeModel`, `InvokeModelWithResponseStream`, `Converse` gibi çağrılar CloudTrail'e *management event* olarak düşer ve management event'ler varsayılan olarak kaydedilir. Kayıtta `eventSource`, `eventName`, `userIdentity`, `sourceIPAddress` ve varsa `errorCode` alanları bulunur. İstemin ve yanıtın **içeriği** bu kayda girmez.
2. **Model çağrı günlüğü (*model invocation logging*): ne söylendi, ne yanıtlandı?** Belge açıkça *"Model invocation logging is disabled by default"* der. Açıldığında tam istek ve yanıt verisini S3'e ya da CloudWatch Logs'a yazar. Yapılandırma `PutModelInvocationLoggingConfiguration` ile kurulur, `GetModelInvocationLoggingConfiguration` ile okunur, `DeleteModelInvocationLoggingConfiguration` ile silinir.

Bu ikilik bir gerilim yaratır. İçerik günlüğü kapalıysa, kötüye kullanımı (ör. çalınmış anahtarla model çağırmak) yalnız "kim çağırdı" düzeyinde görürsün. Açıksa, günlüğün kendisi istemlere giren her şeyi taşıyan hassas bir veri deposuna dönüşür. Kimin okuyabildiği, ne kadar tutulduğu ve şifrelenip şifrelenmediği o andan itibaren bir güvenlik kararıdır.

> [!NOTE]
> Bu dersteki yapılandırma sözlüğü ve olay kayıtları **sentetiktir**; alan adları gerçek API'lerden alınmıştır ama gerçek bir hesap, günlük ya da ağ çağrısı yoktur.
:::

::: anlat 2. Mekanizma: saldırgan günlüğe neden bakar?
Sysdig'in Mayıs 2024 tarihli LLMjacking raporu (Brucato), çalınmış bulut kimlik bilgileriyle Bedrock'a erişen saldırganların iki keşif adımını belgeler:

- **Erişim sondası:** `InvokeModel`'i bilerek geçersiz bir parametreyle (`max_tokens_to_sample = -1`) çağırmak. Erişim varsa yanıt `ValidationException` olur, yoksa `AccessDenied`. Model hiç çalışmadığı için maliyet ve içerik izi bırakmaz; ama CloudTrail'de `errorCode: ValidationException` olarak görünür. Raporun Falco kuralı tam olarak bu üçlüyü arar: `eventSource = bedrock.amazonaws.com`, `eventName = InvokeModel`, `errorCode = ValidationException`.
- **Günlük kontrolü:** `GetModelInvocationLoggingConfiguration` çağrısı. Rapora göre amaç tespitten kaçmaktır: istemler kaydediliyorsa saldırgan o hesabı kullanmaktan vazgeçebilir.

Savunma tarafı için çıkarım şudur. İçerik günlüğü kapalı olsa bile CloudTrail'deki işlem adları ve hata kodları bir keşif imzası taşır. Günlük yapılandırmasını okuyan, değiştiren ya da silen her kimlik ayrıca izlenmelidir, çünkü bunlar savunmayı kör etmeye yönelik adımlardır.

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| "CloudTrail açık, istemleri de görüyoruz" | CloudTrail çağrıyı kaydeder, içeriği kaydetmez | İçerik için ayrı çağrı günlüğü; açık olup olmadığını denetle |
| Çağrı günlüğünü açıp herkese okuma izni vermek | Günlük tam istem/yanıt taşır; geniş okuyucu bir veri sızıntısıdır | Dar okuyucu listesi, şifreleme, kısa saklama |
| Yalnız başarılı çağrıları izlemek | Erişim sondası `ValidationException` ile biter, başarılı görünmez | Hata kodlu çağrıları da tara |
| Günlük yapılandırma çağrılarını gürültü saymak | `Get`/`Put`/`Delete` günlük çağrıları kör etme girişimi olabilir | Bu işlem adlarını ayrı bulgu olarak raporla |
:::

::: tahmin Bir keşif sondası hangi alanlarla görünür?
Aşağıdaki iki sentetik CloudTrail olayından hangisi Sysdig raporundaki erişim sondasına benzer?

```python
olaylar = [
    {'eventSource': 'bedrock.amazonaws.com', 'eventName': 'InvokeModel', 'errorCode': 'AccessDenied'},
    {'eventSource': 'bedrock.amazonaws.com', 'eventName': 'InvokeModel', 'errorCode': 'ValidationException'},
]
for o in olaylar:
    sonda = (o['eventSource'] == 'bedrock.amazonaws.com' and o['eventName'] == 'InvokeModel'
             and o.get('errorCode') == 'ValidationException')
    print(o['errorCode'], '->', 'sonda' if sonda else 'erisim yok')
```

???

```cikti
AccessDenied -> erisim yok
ValidationException -> sonda
```
`AccessDenied`, kimlik bilgisinin bu modele erişemediğini söyler. `ValidationException` ise isteğin yetki kontrolünden geçtiğini, yalnız parametresinin bozuk olduğunu söyler: erişim vardır. Saldırgan için bu ikinci yanıt "bu anahtar kullanılabilir" demektir.
:::

::: gorev 1 · Çağrı günlüğü yapılandırmasını denetle
`log_deneti(cfg)` işlevini yaz. `cfg` sentetik bir çağrı günlüğü yapılandırmasıdır.

- `cfg` `dict` değilse `ValueError`.
- Aşağıdaki kontrolleri **bu sırayla** uygula; her biri bağımsızdır ve bulunan her eksik listeye eklenir:
  1. `enabled` tam olarak `True` değilse → `'disabled'`;
  2. `destination` boş olmayan (boşluktan ibaret olmayan) bir `str` değilse → `'no-destination'`;
  3. `encrypted` tam olarak `True` değilse → `'unencrypted'`;
  4. `readers` bir `list` değilse, boşsa, `str` olmayan öğe içeriyorsa ya da `'*'` içeriyorsa → `'broad-readers'`;
  5. `retention_days` `bool` olmayan bir `int` değilse ya da `1..30` aralığında değilse → `'retention'`.
- Dönüş: eksiklerin listesi (eksik yoksa `[]`). `cfg`'yi değiştirme.

KUSURLU başlangıç değerlerin doğruluğuna bakıyor (`1` ve `'yes'` açık sayılıyor), `'*'` okuyucuyu kaçırıyor ve saklama süresini yalnız alt sınırla denetliyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
Path('ornek.json').write_text('[{"enabled": true, "destination": "s3://ornek-gunluk", "encrypted": 1, "readers": ["guvenlik", "*"], "retention_days": 400}]', encoding='utf-8')
```

```starter
def log_deneti(cfg):
    eksik = []
    if not cfg.get('enabled'):
        eksik.append('disabled')
    if not cfg.get('destination'):
        eksik.append('no-destination')
    if not cfg.get('encrypted'):
        eksik.append('unencrypted')
    if not cfg.get('readers'):
        eksik.append('broad-readers')
    if cfg.get('retention_days', 0) < 1:
        eksik.append('retention')
    return eksik

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(log_deneti(*_args))
```

```solution
def log_deneti(cfg):
    if not isinstance(cfg, dict):
        raise ValueError('cfg dict olmali')
    eksik = []
    if cfg.get('enabled') is not True:
        eksik.append('disabled')
    hedef = cfg.get('destination')
    if not isinstance(hedef, str) or not hedef.strip():
        eksik.append('no-destination')
    if cfg.get('encrypted') is not True:
        eksik.append('unencrypted')
    okuyucu = cfg.get('readers')
    if (not isinstance(okuyucu, list) or not okuyucu
            or any(not isinstance(x, str) for x in okuyucu) or '*' in okuyucu):
        eksik.append('broad-readers')
    gun = cfg.get('retention_days')
    if type(gun) is not int or not 1 <= gun <= 30:
        eksik.append('retention')
    return eksik

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(log_deneti(*_args))
```

```test
need('log_deneti')
import copy
_iyi = {'enabled': True, 'destination': 's3://ornek-gunluk', 'encrypted': True, 'readers': ['guvenlik'], 'retention_days': 30}
_yedek = copy.deepcopy(_iyi)
eq(log_deneti(_iyi), [], 'tam ve dar yapılandırma temiz')
eq(_iyi, _yedek, 'girdi değişmemeli')
eq(log_deneti(dict(_iyi, retention_days=1)), [], 'saklama alt sınırı 1 geçerli')
eq(log_deneti({}), ['disabled', 'no-destination', 'unencrypted', 'broad-readers', 'retention'], 'boş yapılandırmada beş eksik, sabit sırayla')
eq(log_deneti(dict(_iyi, enabled=1, encrypted='yes')), ['disabled', 'unencrypted'], 'True dışında doğru değerler açık sayılmaz')
for _alan, _deger, _bulgu in (
    ('enabled', False, 'disabled'),
    ('destination', '', 'no-destination'),
    ('destination', '   ', 'no-destination'),
    ('destination', ['s3://x'], 'no-destination'),
    ('encrypted', False, 'unencrypted'),
    ('readers', ['guvenlik', '*'], 'broad-readers'),
    ('readers', [], 'broad-readers'),
    ('readers', 'guvenlik', 'broad-readers'),
    ('readers', ['guvenlik', None], 'broad-readers'),
    ('retention_days', 0, 'retention'),
    ('retention_days', 31, 'retention'),
    ('retention_days', True, 'retention'),
    ('retention_days', 7.0, 'retention'),
    ('retention_days', '7', 'retention'),
):
    eq(log_deneti(dict(_iyi, **{_alan: _deger})), [_bulgu], f'tek eksik raporlanmalı: {_alan}={_deger!r}')
for _bozuk in (None, [], 'cfg'):
    raises(ValueError, log_deneti, _bozuk, msg=f'dict olmayan cfg ValueError: {_bozuk!r}')
```

```hint
Her kontrol için "tam olarak beklenen değer mi?" diye sor: `is True`, `type(x) is int`, `1 <= x <= 30`. Doğruluk değeri (`if cfg.get(...)`) `1`, `'yes'` ve `400` gibi yanlış değerleri geçirir.
```
:::

::: gorev 2 · CloudTrail benzeri olaylarda keşif ve kör etme izlerini bul
`kesif_tara(olaylar)` işlevini yaz. Her olay sentetik bir CloudTrail kaydıdır: `{'eventSource': str, 'eventName': str, 'userIdentity': {'arn': str}, 'errorCode'?: str}`.

- `olaylar` `list` değilse; bir olay `dict` değilse; `eventSource` ya da `eventName` `str` değilse; `userIdentity` `dict` değilse ya da `arn` boş olmayan `str` değilse; `errorCode` varsa ve `str` değilse `ValueError`.
- Yalnız `eventSource == 'bedrock.amazonaws.com'` olan olaylar değerlendirilir.
- Bulgular:
  - `eventName == 'InvokeModel'` ve `errorCode == 'ValidationException'` → `'erisim-sondasi'`;
  - `eventName == 'GetModelInvocationLoggingConfiguration'` → `'gunluk-kontrol'`;
  - `eventName == 'PutModelInvocationLoggingConfiguration'` → `'gunluk-degisiklik'`;
  - `eventName == 'DeleteModelInvocationLoggingConfiguration'` → `'gunluk-silme'`.
- Dönüş: bulgusu olan her `arn` için bir anahtar; değeri o kimliğin bulgularının **tekrarsız** listesi, şu sabit sırayla: `erisim-sondasi`, `gunluk-kontrol`, `gunluk-degisiklik`, `gunluk-silme`. Bulgusu olmayan kimlik sözlüğe girmez.

KUSURLU başlangıç her `InvokeModel` hatasını sonda sayıyor, `eventSource`'a bakmıyor ve günlük silmeyi kaçırıyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def kesif_tara(olaylar):
    sonuc = {}
    for o in olaylar:
        arn = o['userIdentity']['arn']
        if o['eventName'] == 'InvokeModel' and o.get('errorCode'):
            sonuc.setdefault(arn, []).append('erisim-sondasi')
        elif o['eventName'] == 'GetModelInvocationLoggingConfiguration':
            sonuc.setdefault(arn, []).append('gunluk-kontrol')
    return sonuc
```

```solution
_SIRA = ('erisim-sondasi', 'gunluk-kontrol', 'gunluk-degisiklik', 'gunluk-silme')
_ISLEM = {
    'GetModelInvocationLoggingConfiguration': 'gunluk-kontrol',
    'PutModelInvocationLoggingConfiguration': 'gunluk-degisiklik',
    'DeleteModelInvocationLoggingConfiguration': 'gunluk-silme',
}

def kesif_tara(olaylar):
    if not isinstance(olaylar, list):
        raise ValueError('olaylar list olmali')
    bulgular = {}
    for o in olaylar:
        if not isinstance(o, dict) or not isinstance(o.get('eventSource'), str) or not isinstance(o.get('eventName'), str):
            raise ValueError('bozuk olay')
        kimlik = o.get('userIdentity')
        if not isinstance(kimlik, dict) or not isinstance(kimlik.get('arn'), str) or not kimlik['arn'].strip():
            raise ValueError('bozuk userIdentity')
        if 'errorCode' in o and not isinstance(o['errorCode'], str):
            raise ValueError('bozuk errorCode')
        if o['eventSource'] != 'bedrock.amazonaws.com':
            continue
        if o['eventName'] == 'InvokeModel' and o.get('errorCode') == 'ValidationException':
            bulgu = 'erisim-sondasi'
        else:
            bulgu = _ISLEM.get(o['eventName'])
        if bulgu is not None:
            bulgular.setdefault(kimlik['arn'], set()).add(bulgu)
    return {arn: [b for b in _SIRA if b in kume] for arn, kume in bulgular.items()}
```

```test
need('kesif_tara')
import copy
def _o(arn, ad, kaynak='bedrock.amazonaws.com', hata=None):
    o = {'eventSource': kaynak, 'eventName': ad, 'userIdentity': {'arn': arn}}
    if hata is not None:
        o['errorCode'] = hata
    return o
_S = 'arn:aws:iam::111122223333:user/sizdirilmis'
_U = 'arn:aws:iam::111122223333:role/uygulama'
_Y = 'arn:aws:iam::111122223333:role/gunluk-yonetici'
_olay = [
    _o(_S, 'InvokeModel', hata='ValidationException'),
    _o(_S, 'GetModelInvocationLoggingConfiguration'),
    _o(_S, 'InvokeModel', hata='ValidationException'),
    _o(_S, 'DeleteModelInvocationLoggingConfiguration'),
    _o(_U, 'InvokeModel'),
    _o(_U, 'InvokeModel', hata='ThrottlingException'),
    _o(_U, 'InvokeModel', hata='AccessDenied'),
    _o(_U, 'Converse', hata='ValidationException'),
    _o(_Y, 'PutModelInvocationLoggingConfiguration'),
    _o(_Y, 'GetModelInvocationLoggingConfiguration', kaynak='s3.amazonaws.com'),
    _o(_Y, 'InvokeModel', kaynak='sagemaker.amazonaws.com', hata='ValidationException'),
]
_yedek = copy.deepcopy(_olay)
eq(kesif_tara(_olay), {
    _S: ['erisim-sondasi', 'gunluk-kontrol', 'gunluk-silme'],
    _Y: ['gunluk-degisiklik'],
}, 'sonda + günlük kontrolü + silme bir kimlikte; başka hizmetlerden gelen olaylar ve diğer hata kodları bulgu değil')
eq(_olay, _yedek, 'olaylar değişmemeli')
eq(kesif_tara(list(reversed(_olay)))[_S], ['erisim-sondasi', 'gunluk-kontrol', 'gunluk-silme'], 'bulgu sırası olay sırasından bağımsız')
eq(kesif_tara([]), {}, 'olay yoksa boş sözlük')
eq(kesif_tara([_o(_U, 'InvokeModel'), _o(_U, 'ListFoundationModels')]), {}, 'normal çağrılar bulgu değil')

raises(ValueError, kesif_tara, tuple(_olay), msg='liste olmayan olaylar ValueError')
for _bozuk in (
    ['olay'],
    [{'eventName': 'InvokeModel', 'userIdentity': {'arn': _S}}],
    [{'eventSource': 'bedrock.amazonaws.com', 'userIdentity': {'arn': _S}}],
    [{'eventSource': 'bedrock.amazonaws.com', 'eventName': 'InvokeModel'}],
    [{'eventSource': 'bedrock.amazonaws.com', 'eventName': 'InvokeModel', 'userIdentity': _S}],
    [{'eventSource': 'bedrock.amazonaws.com', 'eventName': 'InvokeModel', 'userIdentity': {'arn': ''}}],
    [{'eventSource': 'bedrock.amazonaws.com', 'eventName': 'InvokeModel', 'userIdentity': {'arn': '  '}}],
    [{'eventSource': 'bedrock.amazonaws.com', 'eventName': 'InvokeModel', 'userIdentity': {'arn': 5}}],
    [{'eventSource': 'bedrock.amazonaws.com', 'eventName': 'InvokeModel', 'userIdentity': {'arn': _S}, 'errorCode': 400}],
    [{'eventSource': 's3.amazonaws.com', 'eventName': 'GetObject', 'userIdentity': {'arn': _S}, 'errorCode': None}],
):
    raises(ValueError, kesif_tara, _bozuk, msg=f'bozuk olay ValueError: {_bozuk!r}')
```

```hint
Önce her olayı şemaya göre doğrula (başka hizmetten gelen olaylar da dahil); sonra `eventSource`'u süz. Bulguları kimlik başına bir `set`'te topla ve dönüşte sabit sıra listesine göre diz.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **İki günlük (25 sn).** "CloudTrail kimin hangi modeli çağırdığını yazar ama istemi yazmaz. İstemi yazan çağrı günlüğü Bedrock'ta varsayılan olarak kapalıdır."
2. **Gerilim (25 sn).** "Çağrı günlüğünü açınca o günlük de hassas bir veri deposu olur. Bu yüzden açık olup olmadığını, şifrelenip şifrelenmediğini, kimin okuyabildiğini ve ne kadar tutulduğunu birlikte denetledik."
3. **Saldırgan izi (35 sn).** "Sysdig'in LLMjacking raporunda saldırgan anahtarı denemek için InvokeModel'i bozuk parametreyle çağırıyor. Yanıt ValidationException ise erişim var demek. Ardından günlük yapılandırmasını sorguluyor ki kayıt tutuluyorsa o hesabı bıraksın."
4. **Tespit (25 sn).** "CloudTrail'de bu üç alanı arayan ve günlük yapılandırmasını okuyan, değiştiren ya da silen kimlikleri işaretleyen bir tarayıcı yazdık."
5. **Sınır (10 sn).** "Olaylar sentetik; gerçek tespit bu kuralları kimlik bağlamı ve normal davranışla birleştirir."
:::

::: anlat Sınır ve kaynak
Bu ders yapılandırmayı ve olay kayıtlarını sentetik sözlüklerle modeller. Gerçek CloudTrail kayıtlarında çok daha fazla alan vardır; aynı rol farklı oturumlarla (`assumed-role`) görünebilir ve meşru yöneticiler de günlük yapılandırmasını okur. Bu yüzden `gunluk-kontrol` tek başına bir alarm değil, bağlamla değerlendirilecek bir sinyaldir. 30 günlük saklama sınırı bu dersin sözleşmesidir, bir düzenleme ya da sağlayıcı kuralı değildir.

- Birincil kaynaklar: [Amazon Bedrock — Monitor model invocation using CloudWatch Logs and Amazon S3](https://docs.aws.amazon.com/bedrock/latest/userguide/model-invocation-logging.html) (varsayılan kapalı, tam istek/yanıt); [Amazon Bedrock — CloudTrail logging](https://docs.aws.amazon.com/bedrock/latest/userguide/logging-using-cloudtrail.html) (`InvokeModel` management event olarak); [Bedrock API — PutModelInvocationLoggingConfiguration](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_PutModelInvocationLoggingConfiguration.html); [AWS CloudTrail — record contents](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-event-reference-record-contents.html); [Sysdig — LLMjacking: Stolen Cloud Credentials Used in New AI Attack (Brucato, 6 Mayıs 2024)](https://sysdig.com/blog/llmjacking-stolen-cloud-credentials-used-in-new-ai-attack/). Doğrulama tarihi: 11 Kasım 2026.
:::

::: dusun
Ekibin, çağrı günlüğünü açarsa müşteri verisinin günlüğe gireceğinden çekinip günlüğü kapalı tuttuğunu düşün. İçeriği kaydetmeden kötüye kullanımı görmek için CloudTrail'de başka hangi alanlara (kaynak IP, hata kodu, çağrı sıklığı) bakardın?
:::

::: ozet
- CloudTrail kimin hangi işlemi çağırdığını kaydeder; istem içeriğini kaydetmez.
- Bedrock çağrı günlüğü varsayılan olarak kapalıdır; açıldığında kendisi hassas bir veri deposudur ve öyle korunur.
- `InvokeModel` + `ValidationException` erişim sondasının imzasıdır; günlük yapılandırma çağrıları kör etme girişimi olabilir.
- Tespit kuralları kimlik ve bağlamla birlikte okunur; tek sinyal kanıt değildir.
:::
