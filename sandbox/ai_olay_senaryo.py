"""Offline, deterministic scenario runner and open-boundary models for ai-olay (01..16).

Closes D09: every scenario case carries real domain inputs (`girdi`) matching the exact
Görev 1 function signature of that lesson plus a ground-truth `saldiri` boolean — NEVER
pre-baked `once`/`sonra` booleans. Students measure before/after leakage and benign
utility retention by actually invoking `acik_fn` and `yamali_fn` on the scenario inputs.
No network, external process, filesystem side effect, or live model is used.
"""
import ast
import hashlib
import operator
import random
import re


def acik_01(url):
    """Flawed prefix check: misses subdomain, userinfo, port, path, query, fragment."""
    return isinstance(url, str) and url.startswith('https://arsiv.invalid')


def acik_02(etiket, url):
    """Flawed link inspector: ignores Unicode Tags block and uses substring host check."""
    if not isinstance(etiket, str) or not isinstance(url, str):
        raise ValueError('iki str gerekli')
    riskli = 'arsiv.invalid' not in url
    return {'etiket': etiket, 'gizli': '', 'riskli': riskli}


def acik_03(kayit, kullanici, hedef):
    """Flawed Slack channel flow: ignores ACL membership and private->dis egress flow."""
    if not isinstance(kayit, dict):
        return None
    return kayit.get('text')


def acik_04(okunan, yazilan, scope):
    """Flawed MCP repo check: checks org owner prefix only, ignoring exact repo and scope."""
    if not all(isinstance(x, str) and '/' in x for x in (okunan, yazilan, scope)):
        return False
    org = scope.split('/', 1)[0]
    return okunan.split('/', 1)[0] == org and yazilan.split('/', 1)[0] == org


def acik_05(metin):
    """Flawed Markdown image gate: permits any https:// URL regardless of host or query."""
    if not isinstance(metin, str):
        raise ValueError('str gerekli')
    return [[u, u.startswith('https://')] for u in re.findall(r'!\[[^\]]*\]\(([^\s()]+)\)', metin)]


def acik_06(eski, olay):
    """Flawed memory writer: persists any non-empty text without checking origin or consent."""
    if not isinstance(eski, list):
        raise ValueError('liste gerekli')
    yeni = list(eski)
    if isinstance(olay, dict) and isinstance(olay.get('text'), str) and olay['text'].strip():
        yeni.append(olay['text'])
    return yeni


def acik_07(icerik, onay_sha256, incelendi):
    """Flawed rule gate: accepts truthy review flag without hash match or Unicode scan."""
    return isinstance(icerik, str) and isinstance(onay_sha256, str) and bool(incelendi)


def acik_08(format, scan, hash_uyuyor, inceleme):
    """Flawed model gate: allows pickle/unknown scan whenever truthy hash_uyuyor is passed."""
    return bool(hash_uyuyor) and scan != 'infected'


def acik_09(digest):
    """Flawed blob key builder: accepts mutable tags, uppercase hex, non-hex, and '../'."""
    if not isinstance(digest, str) or not digest.strip():
        raise ValueError('bos digest')
    parca = digest.split(':', 1)[-1]
    return 'blobs/sha256-' + parca


def acik_10(bolge, kimlik_dogrulandi, roller):
    """Flawed Ray job gate: trusts internal network perimeter without auth or job-submit role."""
    return bolge == 'yonetim'


def acik_11(cfg):
    """Flawed notebook auditor: only flags 0.0.0.0 when token is empty; misses no-tls and ::."""
    if not isinstance(cfg, dict):
        raise ValueError('dict gerekli')
    if cfg.get('bind') == '0.0.0.0' and not cfg.get('token'):
        return ['public-listen']
    return []


def acik_12(bildirilen, alinan, limit):
    """Flawed shared-memory check: checks only bildirilen <= limit, ignoring alinan mismatch and bool."""
    if not all(isinstance(x, int) for x in (bildirilen, alinan, limit)):
        return False
    return limit >= 0 and 0 <= bildirilen <= limit


def acik_13(ifade):
    """Flawed math evaluator: allows Pow (**), FloorDiv (//), >80 chars, and >10**9 intermediates."""
    if not isinstance(ifade, str) or not ifade.strip():
        raise ValueError('bos ifade')
    ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.FloorDiv: operator.floordiv,
        ast.Pow: operator.pow,
    }

    def _coz(n):
        if isinstance(n, ast.Constant) and isinstance(n.value, int):
            return int(n.value)
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.UAdd, ast.USub)):
            v = _coz(n.operand)
            return v if isinstance(n.op, ast.UAdd) else -v
        if isinstance(n, ast.BinOp) and type(n.op) in ops:
            sol, sag = _coz(n.left), _coz(n.right)
            if isinstance(n.op, ast.Pow) and abs(sag) > 10:
                return 10**12
            return ops[type(n.op)](sol, sag)
        raise ValueError('desteklenmeyen dugum')

    return _coz(ast.parse(ifade, mode='eval').body)


def acik_14(kuyruk, owner):
    """Flawed Redis queue reader: returns first non-falsy-cancelled value without owner check."""
    if not isinstance(kuyruk, list):
        raise ValueError('liste gerekli')
    for r in kuyruk:
        if isinstance(r, dict) and isinstance(r.get('value'), str) and not r.get('cancelled'):
            return r['value']
    return None


def acik_15(sinif, hedef, onayli):
    """Flawed DLP gate: blocks only 'secret'; allows internal->external and unapproved internal."""
    if sinif == 'secret':
        return False
    return isinstance(sinif, str) and isinstance(hedef, str)


def acik_16(model_teklifi, politika):
    """Flawed contract gate: checks only positive price, ignoring policy price, currency, and version."""
    if not isinstance(model_teklifi, dict) or not isinstance(politika, dict):
        return False
    fiyat = model_teklifi.get('fiyat')
    return isinstance(fiyat, int) and fiyat > 0


ACIK_SINIRLAR = {
    1: acik_01,
    2: acik_02,
    3: acik_03,
    4: acik_04,
    5: acik_05,
    6: acik_06,
    7: acik_07,
    8: acik_08,
    9: acik_09,
    10: acik_10,
    11: acik_11,
    12: acik_12,
    13: acik_13,
    14: acik_14,
    15: acik_15,
    16: acik_16,
}


def acik_sinir(ders_no):
    """Return the deterministic unpatched boundary callable for lesson `ders_no` (1..16)."""
    if type(ders_no) is not int or ders_no not in ACIK_SINIRLAR:
        raise ValueError('ders_no 1..16 olmali')
    return ACIK_SINIRLAR[ders_no]


def senaryo_vakalari(ders_no, tohum=0):
    """Generate deterministic domain scenario cases without pre-baked before/after booleans."""
    if type(ders_no) is not int or ders_no not in ACIK_SINIRLAR:
        raise ValueError('ders_no 1..16 olmali')
    if type(tohum) is not int:
        raise ValueError('tohum int olmali')
    rng = random.Random(1000 * ders_no + tohum)
    etiket = f'{rng.randrange(1000, 9999)}'

    if ders_no == 1:
        return [
            {'id': 'mesru-varsayilan', 'saldiri': False, 'girdi': ('https://arsiv.invalid/logo',)},
            {'id': 'mesru-acik-443', 'saldiri': False, 'girdi': ('https://arsiv.invalid:443/logo',)},
            {'id': 'sorgu-sizintisi', 'saldiri': True, 'girdi': (f'https://arsiv.invalid/logo?q=SIR_{etiket}',)},
            {'id': 'alt-alan-kandirmasi', 'saldiri': True, 'girdi': ('https://arsiv.invalid.collector.invalid/logo',)},
            {'id': 'kullanici-bilgisi', 'saldiri': True, 'girdi': ('https://arsiv.invalid@collector.invalid/logo',)},
            {'id': 'farkli-port', 'saldiri': True, 'girdi': ('https://arsiv.invalid:8443/logo',)},
            {'id': 'fragment-sizintisi', 'saldiri': True, 'girdi': (f'https://arsiv.invalid/logo#SIR_{etiket}',)},
            {'id': 'farkli-yol', 'saldiri': True, 'girdi': ('https://arsiv.invalid/pixel',)},
        ]

    if ders_no == 2:
        gizli = ''.join(chr(0xE0000 + ord(c)) for c in f'EXFIL:{etiket}')
        return [
            {'id': 'mesru-rapor', 'saldiri': False, 'girdi': ('Çeyrek Özeti', 'https://arsiv.invalid/rapor')},
            {'id': 'mesru-443', 'saldiri': False, 'girdi': ('Kılavuz', 'https://arsiv.invalid:443/kilavuz')},
            {'id': 'tag-blogu-url', 'saldiri': True, 'girdi': ('Çeyrek Özeti', 'https://arsiv.invalid/rapor' + gizli)},
            {'id': 'bosluk-tag-siniri', 'saldiri': True, 'girdi': ('Özet', 'https://arsiv.invalid/rapor' + chr(0xE0020))},
            {'id': 'tilde-tag-siniri', 'saldiri': True, 'girdi': ('Özet', 'https://arsiv.invalid/rapor' + chr(0xE007E))},
            {'id': 'sahte-alan', 'saldiri': True, 'girdi': ('Özet', 'https://arsiv.invalid.evil.invalid/rapor')},
            {'id': 'http-sema', 'saldiri': True, 'girdi': ('Özet', 'http://arsiv.invalid/rapor')},
        ]

    if ders_no == 3:
        return [
            {
                'id': 'mesru-ozel-yerel',
                'saldiri': False,
                'girdi': ({'id': 'm1', 'members': ['ayse'], 'public': False, 'text': 'Yol haritası', 'sinif': 'private'}, 'ayse', 'yerel'),
            },
            {
                'id': 'mesru-kamu-dis',
                'saldiri': False,
                'girdi': ({'id': 'm2', 'members': [], 'public': True, 'text': 'Açık duyuru', 'sinif': 'public'}, 'mehmet', 'dis'),
            },
            {
                'id': 'ozel-veriyi-disa-aktarma',
                'saldiri': True,
                'girdi': ({'id': 'm3', 'members': ['ayse'], 'public': False, 'text': f'GIZLI-{etiket}', 'sinif': 'private'}, 'ayse', 'dis'),
            },
            {
                'id': 'yetkisiz-kullanici-okumasi',
                'saldiri': True,
                'girdi': ({'id': 'm4', 'members': ['finans'], 'public': False, 'text': f'BORDRO-{etiket}', 'sinif': 'private'}, 'ayse', 'yerel'),
            },
            {
                'id': 'eksik-id-semasi',
                'saldiri': True,
                'girdi': ({'id': '', 'members': ['ayse'], 'public': True, 'text': 'Bozuk kayıt', 'sinif': 'public'}, 'ayse', 'yerel'),
            },
        ]

    if ders_no == 4:
        return [
            {'id': 'mesru-ayni-depo', 'saldiri': False, 'girdi': ('kurum/cekirdek', 'kurum/cekirdek', 'kurum/cekirdek')},
            {'id': 'mesru-dokuman', 'saldiri': False, 'girdi': ('kurum/rehber', 'kurum/rehber', 'kurum/rehber')},
            {'id': 'acik-issue-ozel-pr', 'saldiri': True, 'girdi': ('kurum/acik-issue', 'kurum/ozel-kasa', 'kurum/ozel-kasa')},
            {'id': 'ozelden-acik-depoya', 'saldiri': True, 'girdi': ('kurum/ozel-kasa', f'kurum/dis-catal-{etiket}', 'kurum/ozel-kasa')},
            {'id': 'kapsam-disi-ikili', 'saldiri': True, 'girdi': ('kurum/yan-depo', 'kurum/yan-depo', 'kurum/ana-depo')},
            {'id': 'farkli-org', 'saldiri': True, 'girdi': ('kurum/ozel-kasa', 'disari/toplama', 'kurum/ozel-kasa')},
        ]

    if ders_no == 5:
        return [
            {'id': 'mesru-tek-logo', 'saldiri': False, 'girdi': ('Özet hazır: ![logo](https://arsiv.invalid/logo)',)},
            {'id': 'mesru-iki-gorsel', 'saldiri': False, 'girdi': ('![a](https://arsiv.invalid/logo) ve ![b](https://arsiv.invalid:443/simge)',)},
            {'id': 'dis-piksel', 'saldiri': True, 'girdi': (f'![piksel](https://collector.invalid/p?veri={etiket})',)},
            {'id': 'izinli-alan-sorgu-sizintisi', 'saldiri': True, 'girdi': (f'![logo](https://arsiv.invalid/logo?gizli={etiket})',)},
            {'id': 'userinfo-atlatma', 'saldiri': True, 'girdi': ('![x](https://arsiv.invalid@collector.invalid/logo)',)},
            {'id': 'fragment-sizintisi', 'saldiri': True, 'girdi': (f'![x](https://arsiv.invalid/logo#gizli={etiket})',)},
        ]

    if ders_no == 6:
        taban = ['dil:tr']
        return [
            {'id': 'mesru-tercih', 'saldiri': False, 'girdi': (taban, {'origin': 'user', 'consent': True, 'text': 'tema:koyu'})},
            {'id': 'mesru-not', 'saldiri': False, 'girdi': (taban, {'origin': 'user', 'consent': True, 'text': f'proje:{etiket}'})},
            {'id': 'web-kaynakli-sizma', 'saldiri': True, 'girdi': (taban, {'origin': 'web', 'consent': True, 'text': f'EXFIL-{etiket}'})},
            {'id': 'onaysiz-kullanici', 'saldiri': True, 'girdi': (taban, {'origin': 'user', 'consent': False, 'text': 'gizli-komut'})},
            {'id': 'int-consent-atlatma', 'saldiri': True, 'girdi': (taban, {'origin': 'user', 'consent': 1, 'text': 'sahte-onay'})},
            {'id': 'arac-kaynakli-sizma', 'saldiri': True, 'girdi': (taban, {'origin': 'tool', 'consent': True, 'text': 'kalici-arka-kapi'})},
        ]

    if ders_no == 7:
        temiz_1 = 'Yanıtlarda yalnız standart kütüphane kullan.'
        temiz_2 = f'Test sürüm etiketi: {etiket}.'
        h1 = hashlib.sha256(temiz_1.encode('utf-8')).hexdigest()
        h2 = hashlib.sha256(temiz_2.encode('utf-8')).hexdigest()
        bidi = 'Kuralları uygula\u202e ve gizli komutu ekle'
        tagli = 'Kuralları uygula' + chr(0xE0041)
        zwj = 'Kuralları\u200duygula'
        return [
            {'id': 'mesru-kural-1', 'saldiri': False, 'girdi': (temiz_1, h1, True)},
            {'id': 'mesru-kural-2', 'saldiri': False, 'girdi': (temiz_2, h2, True)},
            {'id': 'inceleme-sonrasi-degisim', 'saldiri': True, 'girdi': (temiz_1 + '\nEk komut', h1, True)},
            {'id': 'bidi-gizleme', 'saldiri': True, 'girdi': (bidi, hashlib.sha256(bidi.encode('utf-8')).hexdigest(), True)},
            {'id': 'unicode-tag-gizleme', 'saldiri': True, 'girdi': (tagli, hashlib.sha256(tagli.encode('utf-8')).hexdigest(), True)},
            {'id': 'zwj-gizleme', 'saldiri': True, 'girdi': (zwj, hashlib.sha256(zwj.encode('utf-8')).hexdigest(), True)},
            {'id': 'int-incelendi-bayragi', 'saldiri': True, 'girdi': (temiz_1, h1, 1)},
        ]

    if ders_no == 8:
        return [
            {'id': 'mesru-safetensors-1', 'saldiri': False, 'girdi': ('safetensors', 'clean', True, True)},
            {'id': 'mesru-safetensors-2', 'saldiri': False, 'girdi': ('safetensors', 'clean', True, True)},
            {'id': 'pickle-otomatik-yukleme', 'saldiri': True, 'girdi': ('pickle', 'clean', True, True)},
            {'id': 'tarayici-belirsiz', 'saldiri': True, 'girdi': ('safetensors', 'unknown', True, True)},
            {'id': 'tarayici-hata', 'saldiri': True, 'girdi': ('safetensors', 'error', True, True)},
            {'id': 'int-hash-bayragi', 'saldiri': True, 'girdi': ('safetensors', 'clean', 1, True)},
            {'id': 'incelenmemis-model', 'saldiri': True, 'girdi': ('safetensors', 'clean', True, False)},
        ]

    if ders_no == 9:
        d1 = hashlib.sha256(f'img-a-{etiket}'.encode('utf-8')).hexdigest()
        d2 = hashlib.sha256(f'img-b-{etiket}'.encode('utf-8')).hexdigest()
        return [
            {'id': 'mesru-digest-1', 'saldiri': False, 'girdi': (f'sha256:{d1}',)},
            {'id': 'mesru-digest-2', 'saldiri': False, 'girdi': (f'sha256:{d2}',)},
            {'id': 'yol-gecisi-digest', 'saldiri': True, 'girdi': ('sha256:../../etc/passwd',)},
            {'id': 'degisken-latest', 'saldiri': True, 'girdi': ('latest',)},
            {'id': 'kisa-hex', 'saldiri': True, 'girdi': (f'sha256:{d1[:32]}',)},
            {'id': 'buyuk-harf-hex', 'saldiri': True, 'girdi': (f'sha256:{d1.upper()}',)},
            {'id': 'hex-disi-harf', 'saldiri': True, 'girdi': ('sha256:' + ('g' * 64),)},
        ]

    if ders_no == 10:
        return [
            {'id': 'mesru-tek-rol', 'saldiri': False, 'girdi': ('yonetim', True, ['job-submit'])},
            {'id': 'mesru-coklu-rol', 'saldiri': False, 'girdi': ('yonetim', True, ['viewer', 'job-submit'])},
            {'id': 'kimliksiz-yonetim-agi', 'saldiri': True, 'girdi': ('yonetim', False, ['job-submit'])},
            {'id': 'izleyici-roluyle-is', 'saldiri': True, 'girdi': ('yonetim', True, ['viewer'])},
            {'id': 'int-kimlik-bayragi', 'saldiri': True, 'girdi': ('yonetim', 1, ['job-submit'])},
            {'id': 'bozuk-rol-elemani', 'saldiri': True, 'girdi': ('yonetim', True, ['job-submit', 123])},
        ]

    if ders_no == 11:
        return [
            {'id': 'mesru-yerel-tokenli', 'saldiri': False, 'girdi': ({'bind': '127.0.0.1', 'token': f'tok-{etiket}', 'tls': False},)},
            {'id': 'mesru-localhost-parolali', 'saldiri': False, 'girdi': ({'bind': 'localhost', 'password': f'pw-{etiket}', 'tls': False},)},
            {'id': 'acik-0000-tlssiz', 'saldiri': True, 'girdi': ({'bind': '0.0.0.0', 'token': f'tok-{etiket}', 'tls': False},)},
            {'id': 'acik-ipv6-dinleme', 'saldiri': True, 'girdi': ({'bind': '::', 'token': f'tok-{etiket}', 'tls': True},)},
            {'id': 'yerel-kimliksiz', 'saldiri': True, 'girdi': ({'bind': '127.0.0.1', 'token': '', 'password': ''},)},
            {'id': 'sahte-proxy-int', 'saldiri': True, 'girdi': ({'bind': '127.0.0.1', 'token': '', 'proxy_auth': 1},)},
        ]

    if ders_no == 12:
        return [
            {'id': 'mesru-esit-kucuk', 'saldiri': False, 'girdi': (64, 64, 1024)},
            {'id': 'mesru-tam-limit', 'saldiri': False, 'girdi': (1024, 1024, 1024)},
            {'id': 'bildirilen-alinan-uyumsuz', 'saldiri': True, 'girdi': (64, 512, 1024)},
            {'id': 'sifir-limit', 'saldiri': True, 'girdi': (0, 0, 0)},
            {'id': 'bool-alinan-atlatma', 'saldiri': True, 'girdi': (1, True, 8)},
            {'id': 'negatif-alinan', 'saldiri': True, 'girdi': (16, -16, 1024)},
        ]

    if ders_no == 13:
        return [
            {'id': 'mesru-islem-1', 'saldiri': False, 'girdi': ('2 + 3 * 4',), 'beklenen': 14},
            {'id': 'mesru-islem-2', 'saldiri': False, 'girdi': ('-(10 - 25) + +5',), 'beklenen': 20},
            {'id': 'us-alma-yasak', 'saldiri': True, 'girdi': ('999 ** 3',), 'beklenen': None},
            {'id': 'ara-carpim-asim', 'saldiri': True, 'girdi': ('(600000000 * 4) * 0',), 'beklenen': None},
            {'id': 'uzunluk-asimi', 'saldiri': True, 'girdi': ('1+' * 41 + '1',), 'beklenen': None},
            {'id': 'bool-sabiti-yasak', 'saldiri': True, 'girdi': ('True + 2',), 'beklenen': None},
        ]

    if ders_no == 14:
        return [
            {
                'id': 'mesru-dogru-sahip',
                'saldiri': False,
                'girdi': ([
                    {'owner': 'ayse', 'value': f'YANIT-{etiket}', 'cancelled': False},
                ], 'ayse'),
                'beklenen': f'YANIT-{etiket}',
            },
            {
                'id': 'mesru-bos-kuyruk',
                'saldiri': False,
                'girdi': ([], 'ayse'),
                'beklenen': None,
            },
            {
                'id': 'baska-kullanici-onbellek',
                'saldiri': True,
                'girdi': ([
                    {'owner': 'burak', 'value': f'BURAK-OZEL-{etiket}', 'cancelled': False},
                    {'owner': 'ayse', 'value': 'AYSE-YANIT', 'cancelled': False},
                ], 'ayse'),
                'beklenen': 'AYSE-YANIT',
            },
            {
                'id': 'eksik-cancelled-alani',
                'saldiri': True,
                'girdi': ([
                    {'owner': 'ayse', 'value': 'BELIRSIZ-KAYIT'},
                    {'owner': 'ayse', 'value': 'TEMIZ-KAYIT', 'cancelled': False},
                ], 'ayse'),
                'beklenen': 'TEMIZ-KAYIT',
            },
            {
                'id': 'int-cancelled-sifir',
                'saldiri': True,
                'girdi': ([
                    {'owner': 'ayse', 'value': 'BOZUK-TIP', 'cancelled': 0},
                ], 'ayse'),
                'beklenen': None,
            },
        ]

    if ders_no == 15:
        return [
            {'id': 'mesru-public-external', 'saldiri': False, 'girdi': ('public', 'external', False)},
            {'id': 'mesru-internal-managed', 'saldiri': False, 'girdi': ('internal', 'managed', True)},
            {'id': 'internal-external-sizinti', 'saldiri': True, 'girdi': ('internal', 'external', True)},
            {'id': 'internal-onaysiz', 'saldiri': True, 'girdi': ('internal', 'managed', False)},
            {'id': 'int-onay-bayragi', 'saldiri': True, 'girdi': ('internal', 'managed', 1)},
            {'id': 'public-golge-hedef', 'saldiri': True, 'girdi': ('public', f'golge-{etiket}', True)},
        ]

    return [
        {
            'id': 'mesru-uyumlu-teklif',
            'saldiri': False,
            'girdi': (
                {'fiyat': 1200, 'para_birimi': 'TRY', 'surum': '2026-v2'},
                {'fiyat': 1200, 'para_birimi': 'TRY', 'surum': '2026-v2'},
            ),
        },
        {
            'id': 'mesru-usd-teklif',
            'saldiri': False,
            'girdi': (
                {'fiyat': 85, 'para_birimi': 'USD', 'surum': '2026-v2'},
                {'fiyat': 85, 'para_birimi': 'USD', 'surum': '2026-v2'},
            ),
        },
        {
            'id': 'bir-birimlik-hatali-fiyat',
            'saldiri': True,
            'girdi': (
                {'fiyat': 1, 'para_birimi': 'TRY', 'surum': '2026-v2'},
                {'fiyat': 1200, 'para_birimi': 'TRY', 'surum': '2026-v2'},
            ),
        },
        {
            'id': 'para-birimi-farki',
            'saldiri': True,
            'girdi': (
                {'fiyat': 1200, 'para_birimi': 'TRY', 'surum': '2026-v2'},
                {'fiyat': 1200, 'para_birimi': 'USD', 'surum': '2026-v2'},
            ),
        },
        {
            'id': 'eski-iade-politikasi',
            'saldiri': True,
            'girdi': (
                {'fiyat': 1200, 'para_birimi': 'TRY', 'surum': f'2022-iade-{etiket}'},
                {'fiyat': 1200, 'para_birimi': 'TRY', 'surum': '2026-v2'},
            ),
        },
        {
            'id': 'bool-fiyat-atlatmasi',
            'saldiri': True,
            'girdi': (
                {'fiyat': True, 'para_birimi': 'TRY', 'surum': '2026-v2'},
                {'fiyat': 1, 'para_birimi': 'TRY', 'surum': '2026-v2'},
            ),
        },
    ]
