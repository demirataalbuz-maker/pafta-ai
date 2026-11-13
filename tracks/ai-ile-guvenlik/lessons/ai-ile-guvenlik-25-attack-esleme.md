---
id: ai-ile-guvenlik-25
title: "Tehdit İstihbaratı · ATT&CK ve Tespit Hipotezi"
summary: Davranış gözlemlerini ATT&CK tekniklerine ve tespit veri kaynağına eşle; modelin önerdiği eşlemeleri doğru, üst teknik, yanlış, desteksiz ve uydurma referans olarak ayır.
esleme: ai-ile-guvenlik-22, ai-ile-guvenlik-10, ai-ile-guvenlik-24, ai-ile-guvenlik-21
timeout: 30
---

::: anlat 1. Anahtar sözcük bir teknik değildir
MITRE ATT&CK, saldırgan davranışlarını teknik ve alt teknik olarak adlandıran ortak bir dildir. Bir olay raporunu ATT&CK'e eşlemek, tespit ekibinin "bu davranışı görmek için hangi veriye bakmalıyız?" sorusunu yanıtlamasını sağlar. Bu derste üç davranış kullanılır:

| Davranış etiketi | ATT&CK | Ad | Tespit veri kaynağı (bu dersin sözleşmesi) |
|---|---|---|---|
| `shell-exec` | T1059 | Command and Scripting Interpreter | süreç ağacı (`process-tree`) |
| `run-key-persistence` | T1547.001 | Boot or Logon Autostart Execution: Registry Run Keys / Startup Folder | kayıt defteri değişikliği (`registry-change`) |
| `http-c2` | T1071.001 | Application Layer Protocol: Web Protocols | ağ tabanı (`network-baseline`) |

Bir model rapordaki "HTTP" sözcüğünü görüp T1071.001 önerebilir. Ama HTTP kullanmak, HTTP üzerinden komut-kontrol (C2) yapmak demek değildir. Güncelleme denetleyen her uygulama HTTP kullanır. Benzer biçimde "kayıt defteri" sözcüğü, Run anahtarı üzerinden kalıcılık demek değildir. Eşleme sözcüğe değil, **gözlenen davranışa** dayanmalıdır. Eşlenemeyen gözlem kaybolmaz; incelemeye (`review`) kalır.

> [!NOTE]
> Gözlemler ve model önerileri **sentetiktir**. Davranış etiketleri önceden çıkarılmış kabul edilir; doğal dil sınıflandırması ya da gerçek telemetri yoktur.
:::

::: anlat 2. Mekanizma: alt teknik hiyerarşisi
ATT&CK alt teknikleri ana tekniğin altında noktalı numarayla yazılır: `T1547.001`, `T1547`'nin alt tekniğidir. Bir modelin eşleme önerisi bu yüzden dört durumdan birine düşer:

1. **Doğru:** önerilen teknik, gözlemin beklenen tekniğiyle aynı.
2. **Üst teknik:** önerilen `T1547`, beklenen `T1547.001`. Yanlış değil ama daha az özgül; tespit kuralı yazmak için alt teknik gerekir.
3. **Yanlış:** başka bir teknik (ör. `T1071.001` yerine `T1059`). Önek benzerliği de yanıltır: `T1547.0` ya da `T154` bir üst teknik değildir; üst teknik ilişkisi ancak `beklenen.startswith(öneri + '.')` ise kurulur.
4. **Desteksiz:** gözlemin davranışı hiçbir tekniğe eşlenmiyor ama model yine de teknik önermiş.

Beşinci bir durum, modelin olmayan bir gözleme atıf yapmasıdır (**bilinmeyen gözlem**): uydurma referans. OWASP LLM09'un *hallucination* tanımının istihbarat raporundaki karşılığıdır.

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| "HTTP" geçti → T1071.001 | Meşru HTTP trafiği C2 sayılır | Davranış etiketi `http-c2` olmalı |
| Eşlenmeyen gözlemi atmak | Bilinmeyen davranış raporda iz bırakmaz | `None` teknik, `review` tespiti |
| `startswith(öneri)` ile üst teknik | `T154` de `T1547.001`'in "atası" görünür | `startswith(öneri + '.')` |
| Teknik biçimini denetlememek | `t1059`, `T1059.1` gibi bozuk kimlikler sessizce yanlış sayılır | `T` + 4 rakam, isteğe bağlı `.` + 3 rakam |
| Yinelenen gözlem kimliği | Aynı gözlem iki farklı davranışla eşlenir | Yinelenen kimlik → hata |
:::

::: tahmin Önek mi, üst teknik mi?
Beklenen teknik `T1547.001`. Üç öneri için `startswith(oneri)` ile `startswith(oneri + '.')` ne der?

```python
beklenen = 'T1547.001'
for oneri in ('T1547', 'T154', 'T1547.0'):
    print(oneri, beklenen.startswith(oneri), beklenen.startswith(oneri + '.'))
```

???

```cikti
T1547 True True
T154 True False
T1547.0 True False
```
Yalnız `T1547` gerçek bir üst tekniktir. `T154` ve `T1547.0` dizge öneki olarak eşleşir ama ATT&CK'te böyle bir ata yoktur. Ayracı da karşılaştırmaya katmak bu sahte eşleşmeleri eler.
:::

::: gorev 1 · Gözlemleri tekniğe ve tespit kaynağına eşle
`attack_esle(gozlemler)` işlevini yaz.

- `gozlemler` bir `list`; her kayıt `{'id': str, 'behavior': str}`. `id` boş olmayan ve benzersiz, `behavior` bir `str`. Değilse `ValueError`.
- Eşleme tablosu: `shell-exec` → `('T1059', 'process-tree')`, `run-key-persistence` → `('T1547.001', 'registry-change')`, `http-c2` → `('T1071.001', 'network-baseline')`. Başka her davranış → `(None, 'review')`. Davranış adı büyük/küçük harfe duyarlıdır.
- Dönüş: girdi sırasıyla `[[id, teknik, tespit], ...]`.

KUSURLU başlangıç davranışı alt dizge olarak arıyor (`'http' in behavior`), eşlenmeyen gözlemi atıyor ve yinelenen kimliği kabul ediyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
Path('ornek.json').write_text('[[{"id": "g1", "behavior": "http-update-check"}, {"id": "g2", "behavior": "registry-read"}, {"id": "g3", "behavior": "run-key-persistence"}]]', encoding='utf-8')
```

```starter
def attack_esle(gozlemler):
    sonuc = []
    for g in gozlemler:
        b = g['behavior']
        if 'http' in b:
            sonuc.append([g['id'], 'T1071.001', 'network-baseline'])
        elif 'registry' in b or 'run-key' in b:
            sonuc.append([g['id'], 'T1547.001', 'registry-change'])
        elif 'shell' in b:
            sonuc.append([g['id'], 'T1059', 'process-tree'])
    return sonuc

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(attack_esle(*_args))
```

```solution
_TABLO = {
    'shell-exec': ('T1059', 'process-tree'),
    'run-key-persistence': ('T1547.001', 'registry-change'),
    'http-c2': ('T1071.001', 'network-baseline'),
}

def attack_esle(gozlemler):
    if not isinstance(gozlemler, list):
        raise ValueError('gozlemler list olmali')
    gorulen = set()
    sonuc = []
    for g in gozlemler:
        if (not isinstance(g, dict) or not isinstance(g.get('id'), str) or not g['id'].strip()
                or not isinstance(g.get('behavior'), str) or g['id'] in gorulen):
            raise ValueError('bozuk ya da yinelenen gozlem')
        gorulen.add(g['id'])
        teknik, tespit = _TABLO.get(g['behavior'], (None, 'review'))
        sonuc.append([g['id'], teknik, tespit])
    return sonuc

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(attack_esle(*_args))
```

```test
need('attack_esle')
import copy
def _g(i, b):
    return {'id': i, 'behavior': b}
_gz = [_g('g3', 'http-c2'), _g('g1', 'shell-exec'), _g('g4', 'http-update-check'), _g('g2', 'run-key-persistence'),
       _g('g5', 'registry-read'), _g('g6', 'HTTP-C2'), _g('g7', '')]
_yedek = copy.deepcopy(_gz)
eq(attack_esle(_gz), [
    ['g3', 'T1071.001', 'network-baseline'],
    ['g1', 'T1059', 'process-tree'],
    ['g4', None, 'review'],
    ['g2', 'T1547.001', 'registry-change'],
    ['g5', None, 'review'],
    ['g6', None, 'review'],
    ['g7', None, 'review'],
], 'girdi sırası korunur; sözcük benzerliği eşleme değildir; eşlenmeyen gözlem review\'da kalır')
eq(_gz, _yedek, 'girdi değişmemeli')
eq(attack_esle([]), [], 'boş liste')
raises(ValueError, attack_esle, tuple(_gz), msg='liste olmayan girdi ValueError')
for _bozuk in (['g1'], [{'behavior': 'shell-exec'}], [_g('', 'shell-exec')], [_g('  ', 'shell-exec')], [_g(5, 'shell-exec')],
               [{'id': 'g1'}], [_g('g1', None)], [_g('g1', 'shell-exec'), _g('g1', 'http-c2')]):
    raises(ValueError, attack_esle, _bozuk, msg=f'bozuk gözlem ValueError: {_bozuk!r}')
```

```hint
Tabloyu bir sözlükte tut ve `tablo.get(behavior, (None, 'review'))` ile tam eşleşme yap. Eşlenmeyen gözlemi de çıktıya ekle.
```
:::

::: gorev 2 · Modelin eşleme önerilerini sınıflandır
`oneri_denetle(oneriler, gozlemler)` işlevini yaz.

- `gozlemler` görev 1'deki biçimde (aynı doğrulama kuralları, aynı eşleme tablosu); bu görevin çözümü tabloyu kendisi içermelidir.
- `oneriler` bir `list`; her öneri `{'gozlem_id': str, 'teknik': str}`. `teknik` `T` + 4 ASCII rakam, isteğe bağlı olarak `.` + 3 ASCII rakam biçiminde olmalı (`re.fullmatch(r'T[0-9]{4}(\.[0-9]{3})?', teknik)`); değilse ya da kayıt bozuksa `ValueError`.
- Her öneri için karar, **bu öncelikle**:
  1. `gozlem_id` gözlemlerde yoksa → `'bilinmeyen-gozlem'`;
  2. gözlemin beklenen tekniği `None` ise → `'desteksiz'`;
  3. `teknik == beklenen` → `'dogru'`;
  4. `beklenen.startswith(teknik + '.')` → `'ust-teknik'`;
  5. diğer → `'yanlis'`.
- Dönüş: girdi sırasıyla `[[gozlem_id, teknik, karar], ...]`.

KUSURLU başlangıç üst tekniği ayraçsız önekle buluyor ve bilinmeyen gözlemi `'yanlis'` sayıyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
_TABLO = {'shell-exec': 'T1059', 'run-key-persistence': 'T1547.001', 'http-c2': 'T1071.001'}

def oneri_denetle(oneriler, gozlemler):
    beklenen = {g['id']: _TABLO.get(g['behavior']) for g in gozlemler}
    sonuc = []
    for o in oneriler:
        b = beklenen.get(o['gozlem_id'])
        if b is None:
            karar = 'yanlis'
        elif o['teknik'] == b:
            karar = 'dogru'
        elif b.startswith(o['teknik']):
            karar = 'ust-teknik'
        else:
            karar = 'yanlis'
        sonuc.append([o['gozlem_id'], o['teknik'], karar])
    return sonuc
```

```solution
import re

_TABLO = {'shell-exec': 'T1059', 'run-key-persistence': 'T1547.001', 'http-c2': 'T1071.001'}
_TEKNIK = re.compile(r'T[0-9]{4}(\.[0-9]{3})?')

def oneri_denetle(oneriler, gozlemler):
    if not isinstance(gozlemler, list) or not isinstance(oneriler, list):
        raise ValueError('gozlemler ve oneriler list olmali')
    beklenen = {}
    for g in gozlemler:
        if (not isinstance(g, dict) or not isinstance(g.get('id'), str) or not g['id'].strip()
                or not isinstance(g.get('behavior'), str) or g['id'] in beklenen):
            raise ValueError('bozuk ya da yinelenen gozlem')
        beklenen[g['id']] = _TABLO.get(g['behavior'])
    sonuc = []
    for o in oneriler:
        if (not isinstance(o, dict) or not isinstance(o.get('gozlem_id'), str)
                or not isinstance(o.get('teknik'), str) or _TEKNIK.fullmatch(o['teknik']) is None):
            raise ValueError('bozuk oneri')
        gid, t = o['gozlem_id'], o['teknik']
        if gid not in beklenen:
            karar = 'bilinmeyen-gozlem'
        elif beklenen[gid] is None:
            karar = 'desteksiz'
        elif t == beklenen[gid]:
            karar = 'dogru'
        elif beklenen[gid].startswith(t + '.'):
            karar = 'ust-teknik'
        else:
            karar = 'yanlis'
        sonuc.append([gid, t, karar])
    return sonuc
```

```test
need('oneri_denetle')
import copy
def _g(i, b):
    return {'id': i, 'behavior': b}
def _o(g, t):
    return {'gozlem_id': g, 'teknik': t}
_gz = [_g('g1', 'shell-exec'), _g('g2', 'run-key-persistence'), _g('g3', 'http-c2'), _g('g4', 'http-update-check')]
_on = [
    _o('g2', 'T1547.001'),
    _o('g2', 'T1547'),
    _o('g1', 'T1059'),
    _o('g3', 'T1071'),
    _o('g3', 'T1059'),
    _o('g4', 'T1071.001'),
    _o('g9', 'T1059'),
    _o('g1', 'T1059.001'),
    _o('g2', 'T1546.001'),
]
_yedek = copy.deepcopy((_on, _gz))
eq(oneri_denetle(_on, _gz), [
    ['g2', 'T1547.001', 'dogru'],
    ['g2', 'T1547', 'ust-teknik'],
    ['g1', 'T1059', 'dogru'],
    ['g3', 'T1071', 'ust-teknik'],
    ['g3', 'T1059', 'yanlis'],
    ['g4', 'T1071.001', 'desteksiz'],
    ['g9', 'T1059', 'bilinmeyen-gozlem'],
    ['g1', 'T1059.001', 'yanlis'],
    ['g2', 'T1546.001', 'yanlis'],
], 'beş karar türü; alt teknik ana teknik yerine önerilirse yanlış; komşu teknik yanlış')
eq((_on, _gz), _yedek, 'girdiler değişmemeli')
eq(oneri_denetle([], _gz), [], 'öneri yoksa boş liste')
eq(oneri_denetle([_o('g1', 'T1059')], []), [['g1', 'T1059', 'bilinmeyen-gozlem']], 'gözlem yoksa her öneri bilinmeyen gözleme')

for _bozuk in (
    (tuple(_on), _gz),
    (_on, tuple(_gz)),
    (['g1 T1059'], _gz),
    ([{'teknik': 'T1059'}], _gz),
    ([_o(5, 'T1059')], _gz),
    ([_o('g1', 'T154')], _gz),
    ([_o('g1', 'T1547.0')], _gz),
    ([_o('g1', 't1059')], _gz),
    ([_o('g1', 'T1059.1')], _gz),
    ([_o('g1', 'T10590')], _gz),
    ([_o('g1', 'T1059 ')], _gz),
    ([_o('g1', None)], _gz),
    ([_o('g1', 'T1059')], ['g1']),
    ([_o('g1', 'T1059')], [_g('', 'shell-exec')]),
    ([_o('g1', 'T1059')], [_g('  ', 'shell-exec')]),
    ([_o('g1', 'T1059')], [{'behavior': 'shell-exec'}]),
    ([_o('g1', 'T1059')], [_g('g1', None)]),
    ([_o('g1', 'T1059')], [_g('g1', 'shell-exec'), _g('g1', 'http-c2')]),
):
    raises(ValueError, oneri_denetle, *_bozuk, msg=f'bozuk girdi ValueError: {_bozuk!r}')
```

```hint
Önce gözlemleri doğrulayıp `id → beklenen teknik` sözlüğü kur. Öneriyi değerlendirmeden önce teknik kimliğinin biçimini `re.fullmatch` ile sına; üst teknik için ayracı da karşılaştırmaya kat: `startswith(teknik + '.')`.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Ortak dil (20 sn).** "ATT&CK eşlemesi, tespit ekibine hangi veri kaynağına bakacağını söylüyor: shell çalıştırma için süreç ağacı, Run anahtarı için kayıt defteri, HTTP C2 için ağ tabanı."
2. **Sözcük tuzağı (30 sn).** "Model 'HTTP' sözcüğünü görünce T1071.001 diyordu. Güncelleme kontrolü de HTTP kullanır. Eşlemeyi sözcüğe değil davranış etiketine bağladık; eşlenmeyen gözlemi atmadan review'a bıraktık."
3. **Hiyerarşi (30 sn).** "Modelin önerilerini beşe ayırdık. T1547, T1547.001 için doğru ama daha az özgül bir üst teknik. T154 ve T1547.0 dizge olarak önek görünse de ata değil; ayracı karşılaştırmaya katınca elendiler."
4. **Uydurma (25 sn).** "Model olmayan g9 gözlemine teknik atadı; bunu bilinmeyen gözlem diye ayırdık. Davranışı eşlenmeyen bir gözleme teknik atamasını da desteksiz saydık."
5. **Sınır (15 sn).** "Üç teknikli küçük bir tablo; gerçek ATT&CK'te tek davranış birden çok tekniğe eşlenebilir."
:::

::: anlat Sınır ve kaynak
Bu ders üç davranışlık bir eşleme tablosu kullanır ve her davranışa tek teknik atar. Gerçek ATT&CK'te bir davranış birden çok tekniğe ya da taktiğe eşlenebilir; teknikler sürümler arasında yeniden adlandırılır ya da kullanımdan kaldırılır. Tespit veri kaynağı sütunu bu dersin sözleşmesidir; ATT&CK'in kendi *data source* ve *detection* sınıflandırmasıyla birebir aynı değildir. Davranış etiketleri önceden çıkarılmış kabul edilir; etiketleri ham telemetriden çıkarmak ayrı ve zor bir sorundur.

- Birincil kaynaklar: [MITRE ATT&CK — T1059 Command and Scripting Interpreter](https://attack.mitre.org/techniques/T1059/); [MITRE ATT&CK — T1547.001 Registry Run Keys / Startup Folder](https://attack.mitre.org/techniques/T1547/001/); [MITRE ATT&CK — T1071.001 Web Protocols](https://attack.mitre.org/techniques/T1071/001/); [OWASP GenAI — LLM09:2025 Misinformation](https://genai.owasp.org/llmrisk/llm092025-misinformation/). Doğrulama tarihi: 11 Kasım 2026.
:::

::: dusun
Bir model T1059 yerine T1059.001'i (PowerShell) önerdi ve gözlem kaydında süreç adı `powershell.exe`. Görev 2'nin kuralı bunu "yanlış" sayıyor. Kuralı "alt teknik önerisi, beklenen ana tekniğin altındaysa ve gözlem bunu destekliyorsa kabul" diye genişletmek için gözlem kaydında hangi alana ihtiyaç duyardın?
:::

::: ozet
- ATT&CK eşlemesi sözcüğe değil gözlenen davranışa dayanır; eşlenmeyen gözlem incelemeye kalır.
- Alt teknik `T1547.001`, ana teknik `T1547`'nin altındadır; üst teknik ilişkisi ayraçla birlikte denetlenir.
- Model önerileri doğru, üst teknik, yanlış, desteksiz ve bilinmeyen gözlem olarak ayrılır.
- Teknik kimliğinin biçimi önceden doğrulanır; bozuk kimlik sessizce "yanlış" sayılmaz.
:::
