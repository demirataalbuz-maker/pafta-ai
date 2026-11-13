---
id: ai-bulut-08
title: "GPU Kümesi · Model Ağırlığı ve Secret Yalıtımı"
summary: Kubernetes GPU iş yükünde ayrıcalıklı konteyneri, host bağlamasını, varsayılan hizmet hesabını ve ad alanı dışı sırrı yakala; sırra doğrudan ve pod oluşturarak dolaylı erişen rolleri bul.
esleme: ai-temel-18, ai-savunma-15, ai-saldiri-63, ai-uretim-08
timeout: 30
---

::: anlat 1. GPU iş yükü neden ayrıcalık ister ve neden vermemeli?
Bir GPU kümesinde model eğiten ya da sunan pod'lar çoğu zaman üç şeye dokunur: GPU aygıtları, büyük model ağırlıkları ve bir model deposunun ya da nesne deposunun kimlik bilgisi. Kısa yoldan gitmek kolaydır: konteyneri `privileged` çalıştırmak, ağırlıkları host diskinden `hostPath` ile bağlamak, varsayılan hizmet hesabını kullanmak. Her kısa yol, konteynerden kaçan bir saldırganın erişim alanını büyütür.

Kubernetes'in *Pod Security Standards* belgesi üç profil tanımlar: `Privileged`, `Baseline`, `Restricted`. En gevşek kısıtlayıcı profil olan `Baseline` bile ayrıcalıklı konteynerlere ve `HostPath` birimlerine izin vermez. *Service Accounts* belgesi her ad alanında `default` adlı bir hizmet hesabının otomatik oluşturulduğunu ve token'ının pod'a otomatik bağlanmasının `automountServiceAccountToken: false` ile kapatılabildiğini anlatır. *Good practices for Kubernetes Secrets* belgesi de sırlara en az ayrıcalıklı erişim ister ve önemli bir dolaylı yolu not eder: **bir sırrı kullanan pod oluşturabilen kullanıcı o sırrın değerini görebilir.**

> [!NOTE]
> Pod tanımları ve rol izinleri **sentetik ve sadeleştirilmiş** sözlüklerdir; gerçek bir Kubernetes API'si, GPU ya da küme kullanılmaz. Gerçek RBAC'taki fiil/kaynak ayrımı burada `'pods/create'` gibi tek dizgelerle temsil edilir.
:::

::: anlat 2. Mekanizma: sırra giden iki yol
Bir rolün bir sırrı okuyabilmesinin iki yolu vardır:

1. **Doğrudan:** aynı ad alanında sırları okuma izni (`secrets/get` ya da `secrets/list`).
2. **Dolaylı:** aynı ad alanında pod oluşturma izni (`pods/create`). Rol, sırrı ortam değişkeni ya da birim olarak bağlayan bir pod oluşturur ve içinden okur. Sırlara hiç izni görünmeyen bir CI hesabı böylece model deposunun anahtarına ulaşabilir.

Denetimde yalnız birinci yola bakmak, en sık görülen ayrıcalık yükseltme yollarından birini kaçırmak demektir.

Pod düzeyinde ise beş bulgu sırayla denetlenir: ayrıcalıklı konteyner, host bağlaması, varsayılan hizmet hesabı, başka ad alanından gelen sır ve açık çıkış (*egress*) trafiği. Sonuncusu, eğitim pod'unun ağırlıkları ya da sırrı dışarıya göndermesini engelleyen ağ politikasının olup olmadığını sorar.

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| GPU için `privileged: true` | Konteynerden kaçış host'un tamamını açar | Aygıt eklentisiyle GPU; `Baseline` ayrıcalığı yasaklar |
| Ağırlıkları `hostPath` ile bağlamak | Konteyner host dosya sistemine yazabilir | Salt okunur birim ya da nesne deposu |
| Varsayılan hizmet hesabı | Ad alanındaki her pod aynı kimliği taşır | İş yüküne özel hesap; gereksizse token bağlama kapalı |
| Yalnız `secrets/get` iznine bakmak | `pods/create` ile sır dolaylı okunur | İki yolu birlikte raporla |
| `egress` politikasını sonraya bırakmak | Sızan sır ya da ağırlık dışarı gider | Varsayılan ret çıkış politikası |
:::

::: tahmin Sırra izni olmayan rol sırrı okuyabilir mi?
`ci-derleyici` rolünün sırlara hiç izni yok ama pod oluşturabiliyor. İki denetimin sonucunu tahmin et.

```python
rol = {'ad': 'ci-derleyici', 'namespace': 'egitim', 'izinler': ['pods/create']}
sir = {'ad': 'model-deposu-anahtari', 'namespace': 'egitim'}

yalniz_dogrudan = rol['namespace'] == sir['namespace'] and any(
    i in ('secrets/get', 'secrets/list') for i in rol['izinler'])
iki_yol = rol['namespace'] == sir['namespace'] and any(
    i in ('secrets/get', 'secrets/list', 'pods/create') for i in rol['izinler'])
print('yalnız doğrudan:', yalniz_dogrudan, '| iki yol:', iki_yol)
```

???

```cikti
yalnız doğrudan: False | iki yol: True
```
Rol sırrı okuyamaz görünür; ama aynı ad alanında sırrı bağlayan bir pod oluşturup içinden okuyabilir. Kubernetes belgesi bu yolu açıkça not eder.
:::

::: gorev 1 · GPU pod tanımındaki ayrıcalık bulguları
`pod_bulgulari(pod)` işlevini yaz.

- `pod` bir `dict`; `namespace` boş olmayan bir `str`; `secrets` her öğesi `dict` olan bir `list`. Değilse `ValueError`.
- Bulgular **bu sırayla**:
  1. `privileged is True` → `'privileged'`;
  2. `hostPath` boş olmayan bir `str` ise → `'host-mount'`;
  3. `serviceAccount` yoksa, `None`'sa ya da `'default'`'sa → `'default-identity'`;
  4. `secrets` içinde `namespace`'i pod'un ad alanından farklı (eksik dahil) bir sır varsa → `'cross-namespace-secret'` (bir kez);
  5. `egress_deny is True` değilse → `'egress-open'`.
- Dönüş: bulgu listesi. Girdiyi değiştirme.

KUSURLU başlangıç `privileged`'ın doğruluk değerine bakıyor, eksik hizmet hesabını kaçırıyor ve her ad alanı dışı sır için bulguyu tekrar ekliyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
Path('ornek.json').write_text('[{"namespace": "egitim", "privileged": 1, "hostPath": "/mnt/agirliklar", "secrets": [{"ad": "s3", "namespace": "uretim"}, {"ad": "hf", "namespace": "uretim"}], "egress_deny": true}]', encoding='utf-8')
```

```starter
def pod_bulgulari(pod):
    bulgu = []
    if pod.get('privileged'):
        bulgu.append('privileged')
    if pod.get('hostPath'):
        bulgu.append('host-mount')
    if pod.get('serviceAccount') == 'default':
        bulgu.append('default-identity')
    for s in pod['secrets']:
        if s.get('namespace') != pod['namespace']:
            bulgu.append('cross-namespace-secret')
    if not pod.get('egress_deny'):
        bulgu.append('egress-open')
    return bulgu

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(pod_bulgulari(*_args))
```

```solution
def pod_bulgulari(pod):
    if (not isinstance(pod, dict) or not isinstance(pod.get('namespace'), str) or not pod['namespace'].strip()
            or not isinstance(pod.get('secrets'), list) or any(not isinstance(s, dict) for s in pod['secrets'])):
        raise ValueError('pod namespace ve secrets listesi tasimali')
    bulgu = []
    if pod.get('privileged') is True:
        bulgu.append('privileged')
    host = pod.get('hostPath')
    if isinstance(host, str) and host.strip():
        bulgu.append('host-mount')
    if pod.get('serviceAccount') in (None, 'default'):
        bulgu.append('default-identity')
    if any(s.get('namespace') != pod['namespace'] for s in pod['secrets']):
        bulgu.append('cross-namespace-secret')
    if pod.get('egress_deny') is not True:
        bulgu.append('egress-open')
    return bulgu

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(pod_bulgulari(*_args))
```

```test
need('pod_bulgulari')
import copy
_iyi = {'namespace': 'egitim', 'privileged': False, 'serviceAccount': 'egitim-isi',
        'secrets': [{'ad': 'hf-token', 'namespace': 'egitim'}], 'egress_deny': True}
_yedek = copy.deepcopy(_iyi)
eq(pod_bulgulari(_iyi), [], 'sıkı pod tanımı temiz')
eq(_iyi, _yedek, 'girdi değişmemeli')
eq(pod_bulgulari({'namespace': 'egitim', 'secrets': []}), ['default-identity', 'egress-open'],
   'eksik hizmet hesabı varsayılan kimliktir; eksik egress_deny açık çıkıştır')
eq(pod_bulgulari({'namespace': 'egitim', 'privileged': True, 'hostPath': '/mnt/agirlik', 'serviceAccount': 'default',
                  'secrets': [{'ad': 'a', 'namespace': 'uretim'}, {'ad': 'b'}, {'ad': 'c', 'namespace': 'egitim'}],
                  'egress_deny': False}),
   ['privileged', 'host-mount', 'default-identity', 'cross-namespace-secret', 'egress-open'],
   'beş bulgu sabit sırayla; ad alanı dışı sır bulgusu bir kez')
for _alan, _deger, _bulgu in (
    ('privileged', 1, []), ('privileged', 'true', []), ('privileged', True, ['privileged']),
    ('hostPath', '', []), ('hostPath', '   ', []), ('hostPath', None, []), ('hostPath', '/data', ['host-mount']),
    ('serviceAccount', None, ['default-identity']), ('serviceAccount', 'default', ['default-identity']),
    ('serviceAccount', 'Default', []),
    ('egress_deny', 1, ['egress-open']), ('egress_deny', 'true', ['egress-open']),
    ('secrets', [{'ad': 'x', 'namespace': 'Egitim'}], ['cross-namespace-secret']),
):
    eq(pod_bulgulari(dict(_iyi, **{_alan: _deger})), _bulgu, f'tek alan: {_alan}={_deger!r}')
for _bozuk in (None, [], {'secrets': []}, {'namespace': '', 'secrets': []}, {'namespace': '  ', 'secrets': []},
               {'namespace': 5, 'secrets': []}, {'namespace': 'egitim'}, {'namespace': 'egitim', 'secrets': 'hf'},
               {'namespace': 'egitim', 'secrets': ['hf']}):
    raises(ValueError, pod_bulgulari, _bozuk, msg=f'bozuk pod ValueError: {_bozuk!r}')
```

```hint
`privileged` ve `egress_deny` için `is True` kullan. Ad alanı dışı sır için `any(...)` ile tek bir bulgu ekle; döngüde her sır için eklersen bulgu tekrar eder.
```
:::

::: gorev 2 · Sırra doğrudan ve dolaylı erişen rolleri bul
`sir_erisim_yollari(roller, sirlar)` işlevini yaz.

- `roller`: `{'ad': str, 'namespace': str, 'izinler': list[str]}` listesi. `sirlar`: `{'ad': str, 'namespace': str}` listesi. İki girdi de `list` olmalı; her kayıt `dict`, `ad` ve `namespace` boş olmayan `str`, `izinler` `str` listesi olmalı. Aynı ad (rollerde ya da sırlarda) tekrar ederse `ValueError`.
- Bir rol bir sırra **doğrudan** erişir: aynı ad alanında ve izinlerinde `'secrets/get'` ya da `'secrets/list'` varsa.
- Bir rol bir sırra **dolaylı** erişir: aynı ad alanında, izinlerinde `'pods/create'` var ve doğrudan erişimi **yoksa**.
- Dönüş: her sır için `{sir_ad: {'dogrudan': [...], 'dolayli': [...]}}`; rol adları sıralı. Hiç erişeni olmayan sır da iki boş listeyle sözlükte yer alır.

KUSURLU başlangıç yalnız `secrets/get`'i doğrudan sayıyor ve `pods/create` yolunu hiç raporlamıyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def sir_erisim_yollari(roller, sirlar):
    sonuc = {}
    for s in sirlar:
        dogrudan = sorted(r['ad'] for r in roller
                          if r['namespace'] == s['namespace'] and 'secrets/get' in r['izinler'])
        sonuc[s['ad']] = {'dogrudan': dogrudan, 'dolayli': []}
    return sonuc
```

```solution
_OKUMA = ('secrets/get', 'secrets/list')

def _kayit_ok(k):
    return (isinstance(k, dict) and isinstance(k.get('ad'), str) and k['ad'].strip()
            and isinstance(k.get('namespace'), str) and k['namespace'].strip())

def sir_erisim_yollari(roller, sirlar):
    if not isinstance(roller, list) or not isinstance(sirlar, list):
        raise ValueError('roller ve sirlar list olmali')
    for grup in (roller, sirlar):
        adlar = set()
        for k in grup:
            if not _kayit_ok(k):
                raise ValueError('bozuk kayit')
            if k['ad'] in adlar:
                raise ValueError('yinelenen ad')
            adlar.add(k['ad'])
    for r in roller:
        if not isinstance(r.get('izinler'), list) or any(not isinstance(i, str) for i in r['izinler']):
            raise ValueError('izinler str listesi olmali')
    sonuc = {}
    for s in sirlar:
        dogrudan, dolayli = [], []
        for r in roller:
            if r['namespace'] != s['namespace']:
                continue
            if any(i in _OKUMA for i in r['izinler']):
                dogrudan.append(r['ad'])
            elif 'pods/create' in r['izinler']:
                dolayli.append(r['ad'])
        sonuc[s['ad']] = {'dogrudan': sorted(dogrudan), 'dolayli': sorted(dolayli)}
    return sonuc
```

```test
need('sir_erisim_yollari')
import copy
def _r(ad, ns, izin):
    return {'ad': ad, 'namespace': ns, 'izinler': izin}
_roller = [
    _r('model-okuyucu', 'egitim', ['secrets/get']),
    _r('ci-derleyici', 'egitim', ['pods/create', 'pods/get']),
    _r('denetci', 'egitim', ['secrets/list']),
    _r('yonetici', 'egitim', ['secrets/get', 'pods/create']),
    _r('gozlemci', 'egitim', ['pods/get', 'pods/list']),
    _r('uretim-ci', 'uretim', ['pods/create']),
]
_sirlar = [{'ad': 'hf-token', 'namespace': 'egitim'}, {'ad': 's3-anahtar', 'namespace': 'uretim'},
           {'ad': 'eski', 'namespace': 'arsiv'}]
_yedek = copy.deepcopy((_roller, _sirlar))
eq(sir_erisim_yollari(_roller, _sirlar), {
    'hf-token': {'dogrudan': ['denetci', 'model-okuyucu', 'yonetici'], 'dolayli': ['ci-derleyici']},
    's3-anahtar': {'dogrudan': [], 'dolayli': ['uretim-ci']},
    'eski': {'dogrudan': [], 'dolayli': []},
}, 'secrets/list de doğrudan sayılır; pods/create dolaylıdır; ikisine sahip rol yalnız doğrudanda; pods/get yol değildir')
eq((_roller, _sirlar), _yedek, 'girdiler değişmemeli')
eq(sir_erisim_yollari([], []), {}, 'boş girdiler')

for _bozuk in (
    (tuple(_roller), _sirlar),
    (_roller, tuple(_sirlar)),
    (['rol'], _sirlar),
    ([_r('', 'egitim', [])], _sirlar),
    ([_r('a', '', [])], _sirlar),
    ([_r('a', '  ', [])], _sirlar),
    ([_r(5, 'egitim', [])], _sirlar),
    ([_r('a', 'egitim', 'secrets/get')], _sirlar),
    ([_r('a', 'egitim', ['secrets/get', None])], _sirlar),
    ([{'ad': 'a', 'namespace': 'egitim'}], _sirlar),
    ([_r('a', 'egitim', []), _r('a', 'uretim', [])], _sirlar),
    (_roller, [{'ad': 'x'}]),
    (_roller, [{'ad': 'x', 'namespace': 'egitim'}, {'ad': 'x', 'namespace': 'uretim'}]),
    (_roller, ['hf-token']),
):
    raises(ValueError, sir_erisim_yollari, *_bozuk, msg=f'bozuk girdi ValueError: {_bozuk!r}')
```

```hint
Önce iki grubu da doğrula ve tekrar eden adları yakala. Her sır için yalnız aynı ad alanındaki rollere bak: doğrudan okuma izni varsa doğrudana, yoksa ve pod oluşturabiliyorsa dolaylıya ekle.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Kısa yollar (25 sn).** "GPU iş yükünde en kolay yol privileged konteyner, hostPath ile ağırlık ve varsayılan hizmet hesabı. Kubernetes'in en gevşek kısıtlayıcı profili Baseline bile ilk ikisine izin vermiyor."
2. **Pod bulguları (25 sn).** "Pod tanımını beş bulguya göre taradık. Eksik hizmet hesabının da varsayılan kimlik olduğunu, eksik egress politikasının da açık çıkış olduğunu ayrıca sınadık."
3. **Dolaylı yol (35 sn).** "Sırlara hiç izni görünmeyen CI hesabı aynı ad alanında pod oluşturabiliyordu. Sırrı bağlayan bir pod açıp içinden okuyabilir; Kubernetes belgesi bu yolu açıkça not ediyor. Denetimi iki yola ayırdık."
4. **Sonuç (25 sn).** "hf-token'a üç rol doğrudan, CI hesabı dolaylı erişiyor. Pod oluşturma izni sır okuma izni kadar dikkat istiyor."
5. **Sınır (10 sn).** "RBAC sadeleştirildi; gerçek kümede ClusterRole, bağlamalar ve kabul denetleyicisi de hesaba katılır."
:::

::: anlat Sınır ve kaynak
Bu ders RBAC'ı sadeleştirilmiş `'kaynak/fiil'` dizgeleriyle modeller. Gerçek kümede `ClusterRole`'ler ad alanı sınırını aşar; `RoleBinding` ve `ClusterRoleBinding`, joker fiiller (`*`), `pods/exec` gibi alt kaynaklar ve iş yükü kaynakları (`deployments/create` da pod oluşturur) ek yollar açar. Kabul denetleyicileri (ör. Pod Security Admission) belirli pod'ları engelleyerek dolaylı yolu daraltabilir. Bunlar bu derste yoktur. GPU paylaşımındaki bellek kalıntısı riskleri ayrı bir derste işlenir (`ai-saldiri-63`).

- Birincil kaynaklar: [Kubernetes — Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/) (Privileged/Baseline/Restricted; Baseline ayrıcalıklı konteyneri ve HostPath'i yasaklar); [Kubernetes — Service Accounts](https://kubernetes.io/docs/concepts/security/service-accounts/) (her ad alanında `default` hesap, `automountServiceAccountToken`); [Kubernetes — Good practices for Kubernetes Secrets](https://kubernetes.io/docs/concepts/security/secrets-good-practices/) (en az ayrıcalık, sırrı kullanan pod oluşturabilenin değeri görebilmesi). Doğrulama tarihi: 11 Kasım 2026.
:::

::: dusun
Bir eğitim ekibi "CI hesabımız pod oluşturmak zorunda" diyor. Sırrın dolaylı okunmasını engellemek için CI'yi ayrı bir ad alanına almak, sırrı bir dış sır yöneticisinden iş yüküne özel kimlikle çekmek ve kabul denetleyicisiyle sır bağlayan pod'ları sınırlamak seçeneklerini karşılaştır.
:::

::: ozet
- GPU iş yükünde ayrıcalıklı konteyner ve `hostPath` kısa yollardır; `Baseline` profili ikisini de yasaklar.
- Eksik hizmet hesabı varsayılan kimliktir; eksik çıkış politikası açık çıkıştır.
- Sırra iki yol vardır: doğrudan okuma izni ve aynı ad alanında pod oluşturma izni.
- Sır erişim denetimi yalnız `secrets/get` iznine bakarsa en yaygın dolaylı yolu kaçırır.
:::
