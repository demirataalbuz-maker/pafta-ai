"""Sentinel zamanlanmış kuralı: ARM kaynağını belgelenmiş sınırlarla denetle, sorgusunu gerçek Kusto'da koştur.

Sentinel servisi değildir. Özellik adları ve enum değerleri Microsoft.SecurityInsights alertRules REST
2025-09-01 tanımından, sayısal sınırlar Microsoft Learn'deki zamanlanmış kural, entity mapping ve
ingestion delay belgelerinden alınmıştır (kaynaklar KQ22'de). Sorgu gerçek Kusto Emulator'da çalışır;
takvim, 5 dakikalık gecikme, eşik, olay gruplama, bastırma ve entity çıkarımı bu belgelere göre yazılmış
yerel modeldir. Portalın Test with current data ve Review doğrulamasının yerine geçmez.
"""
from datetime import datetime, timedelta
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.runners import HarnessRunner, NO_WINDOW, _kill_tree, python_exe  # noqa: E402
from sandbox import kusto_lab  # noqa: E402

API = '2025-09-01'
# REST belgesinin "Other Supported Versions" listesi (27.10.2026).
API_SURUMLERI = {'2020-01-01', '2021-10-01', '2022-08-01', '2022-11-01', '2023-02-01', '2023-11-01', '2024-03-01',
                 '2024-09-01', '2025-03-01', '2025-06-01', '2025-07-01-preview', API}
GECIKME = timedelta(minutes=5)              # "runs scheduled analytics rules on a five-minute delay"
EN_KISA, EN_UZUN = timedelta(minutes=5), timedelta(days=14)
BASTIRMA_TAVAN = timedelta(hours=24)
SORGU_TAVAN, ALARM_TAVAN, MAPPING_TAVAN, IDENTIFIER_TAVAN = 10000, 150, 10, 3
ENTITY_TAVAN, ENTITY_BAYT = 500, 64 * 1024

OPERATOR = {'GreaterThan': lambda n, t: n > t, 'LessThan': lambda n, t: n < t,
            'Equal': lambda n, t: n == t, 'NotEqual': lambda n, t: n != t}
SEVERITY = {'High', 'Medium', 'Low', 'Informational'}
TOPLAMA = {'SingleAlert', 'AlertPerResult'}
TAKTIK = {'Reconnaissance', 'ResourceDevelopment', 'InitialAccess', 'Execution', 'Persistence',
          'PrivilegeEscalation', 'DefenseEvasion', 'CredentialAccess', 'Discovery', 'LateralMovement',
          'Collection', 'Exfiltration', 'CommandAndControl', 'Impact', 'PreAttack', 'ImpairProcessControl',
          'InhibitResponseFunction'}
ENTITY_TURU = {'Account', 'Host', 'IP', 'Malware', 'File', 'Process', 'CloudApplication', 'DNS', 'AzureResource',
               'FileHash', 'RegistryKey', 'RegistryValue', 'SecurityGroup', 'URL', 'Mailbox', 'MailCluster',
               'MailMessage', 'SubmissionMail'}
# Laboratuvar yalnız bu türlerin identifier listesini taşır (entities-reference).
IDENTIFIER = {
    'Account': {'Name', 'FullName', 'NTDomain', 'DnsDomain', 'UPNSuffix', 'Sid', 'AadTenantId', 'AadUserId',
                'PUID', 'IsDomainJoined', 'DisplayName', 'ObjectGuid'},
    'Host': {'DnsDomain', 'NTDomain', 'HostName', 'FullName', 'NetBiosName', 'AzureID', 'OMSAgentID',
             'OSFamily', 'OSVersion', 'IsDomainJoined'},
    'IP': {'Address', 'AddressScope'}, 'URL': {'Url'}, 'FileHash': {'Algorithm', 'Value'}}
GERIYE_UYUM = {'FullName', 'DisplayName'}   # eşlemede görünür ama entity şemasında yok
GUCLU = {'Account': [{'Name', 'UPNSuffix'}, {'AadUserId'}, {'Sid'}, {'Name', 'NTDomain'}, {'Name', 'DnsDomain'},
                     {'PUID'}, {'ObjectGuid'}],
         'Host': [{'HostName', 'NTDomain'}, {'HostName', 'DnsDomain'}, {'NetBiosName', 'NTDomain'},
                  {'NetBiosName', 'DnsDomain'}, {'AzureID'}, {'OMSAgentID'}]}
YERLESIK_HESAP = {'ADMIN', 'ADMINISTRATOR', 'SYSTEM', 'ROOT', 'ANONYMOUS', 'AUTHENTICATED USER', 'NETWORK',
                  'NULL', 'LOCAL SYSTEM', 'LOCALSYSTEM', 'NETWORK SERVICE'}
OZELLIK = {'displayName', 'description', 'severity', 'enabled', 'query', 'queryFrequency', 'queryPeriod',
           'triggerOperator', 'triggerThreshold', 'suppressionDuration', 'suppressionEnabled',
           'eventGroupingSettings', 'customDetails', 'entityMappings', 'alertDetailsOverride',
           'incidentConfiguration', 'tactics', 'techniques', 'alertRuleTemplateName', 'templateVersion'}
GEREKLI_API = ('displayName', 'enabled', 'suppressionDuration', 'suppressionEnabled')
GEREKLI_KURAL = ('query', 'queryFrequency', 'queryPeriod', 'severity', 'triggerOperator', 'triggerThreshold')
SURE = re.compile(r'P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?')


def sure(deger):
    """ISO 8601 süre (PnDTnHnMnS) → timedelta; geçersizse None."""
    m = SURE.fullmatch(deger) if isinstance(deger, str) else None
    if not m or not any(m.groups()) or deger.endswith('T'):
        return None
    gun, saat, dakika, saniye = (int(x or 0) for x in m.groups())
    return timedelta(days=gun, hours=saat, minutes=dakika, seconds=saniye)


def _ifade(v):
    return isinstance(v, str) and v.startswith('[') and not v.startswith('[[') and v.endswith(']')


def kaynak_bul(doc):
    """ARM şablonundan (resources) ya da tek kaynak/REST gövdesinden zamanlanmış kuralı çıkar."""
    if not isinstance(doc, dict):
        return None, ['Belge bir JSON nesnesi olmalı']
    if 'resources' in doc:
        adaylar = doc['resources']
        adaylar = list(adaylar.values()) if isinstance(adaylar, dict) else adaylar
        if not isinstance(adaylar, list):
            return None, ['resources bir dizi olmalı']
        kurallar = [r for r in adaylar if isinstance(r, dict) and str(r.get('type', '')).lower().endswith('/alertrules')]
        if len(kurallar) != 1:
            return None, [f'Şablonda tam bir alertRules kaynağı olmalı; bulunan: {len(kurallar)}']
        kaynak = kurallar[0]
        if str(kaynak.get('type')).lower() not in ('microsoft.securityinsights/alertrules',
                                                   'microsoft.operationalinsights/workspaces/providers/alertrules'):
            return None, [f'Tanınmayan kaynak türü: {kaynak.get("type")}']
        surum = kaynak.get('apiVersion')
        if surum not in API_SURUMLERI:
            return None, [f'apiVersion {surum!r} alertRules için yayımlanmış bir sürüm değil; ARM dağıtımı reddeder']
        if surum != API:
            return None, [f'Bu laboratuvar şemayı {API} sürümüne göre denetler; apiVersion {API} olmalı']
    else:
        kaynak = doc
    if kaynak.get('kind') != 'Scheduled':
        return None, [f'kind "Scheduled" olmalı; bulunan: {kaynak.get("kind")!r}']
    if not isinstance(kaynak.get('properties'), dict):
        return None, ['properties nesnesi yok']
    return kaynak['properties'], []


def denetle(p):
    """REST şeması ve belgelenmiş ürün sınırları: (hatalar, uyarilar, sureler)."""
    hata, uyari, sureler = [], [], {}
    for k in sorted(set(p) - OZELLIK):
        hata.append(f'properties.{k}: REST {API} şemasında yok')
    for k in GEREKLI_API:
        if k not in p:
            hata.append(f'properties.{k}: REST {API} için zorunlu')
    for k in GEREKLI_KURAL:
        if k not in p:
            hata.append(f'properties.{k}: bu kural için gerekli')
    for k, v in p.items():
        if _ifade(v):
            hata.append(f'properties.{k}: ARM ifadesi bu laboratuvarda çözülmez; değeri düz yaz')
    if hata:
        return hata, uyari, sureler

    def tur(k, beklenen, ad):
        if not isinstance(p.get(k), beklenen) or (beklenen is int and isinstance(p.get(k), bool)):
            hata.append(f'properties.{k}: {ad} olmalı')
            return False
        return True

    tur('displayName', str, 'metin') and (p['displayName'].strip() or hata.append('properties.displayName: boş'))
    tur('enabled', bool, 'true/false')
    tur('suppressionEnabled', bool, 'true/false')
    tur('query', str, 'metin')
    if tur('triggerThreshold', int, 'tamsayı') and not 0 <= p['triggerThreshold'] <= 10000:
        hata.append('properties.triggerThreshold: 0 ile 10000 arasında olmalı')
    if p.get('triggerOperator') not in OPERATOR:
        hata.append(f'properties.triggerOperator: {sorted(OPERATOR)} değerlerinden biri olmalı')
    if p.get('severity') not in SEVERITY:
        hata.append(f'properties.severity: {sorted(SEVERITY)} değerlerinden biri olmalı')
    for k in ('queryFrequency', 'queryPeriod', 'suppressionDuration'):
        d = sure(p.get(k))
        if d is None:
            hata.append(f'properties.{k}: ISO 8601 süre olmalı (ör. PT10M, PT1H, P1D)')
        else:
            sureler[k] = d.total_seconds() / 60
    siklik, bakis, bastirma = (sure(p.get(k)) for k in ('queryFrequency', 'queryPeriod', 'suppressionDuration'))
    for k, d in (('queryFrequency', siklik), ('queryPeriod', bakis)):
        if d is not None and not EN_KISA <= d <= EN_UZUN:
            hata.append(f'properties.{k}: 5 dakika ile 14 gün arasında olmalı')
    if siklik is not None and bakis is not None and siklik > bakis:
        hata.append('queryFrequency queryPeriod\'dan uzun olamaz: pencereler arasında boşluk kalır')
    if p.get('suppressionEnabled') is True and bastirma is not None and not timedelta(0) < bastirma <= BASTIRMA_TAVAN:
        hata.append('properties.suppressionDuration: bastırma açıkken 24 saati aşamaz')
    if isinstance(p.get('query'), str):
        q = p['query']
        temiz = re.sub(r'//[^\n]*|"(?:[^"\\\n]|\\.)*"|\'(?:[^\'\\\n]|\\.)*\'', '""', q)
        if not 1 <= len(q) <= SORGU_TAVAN:
            hata.append('properties.query: 1 ile 10000 karakter arasında olmalı')
        if re.search(r'\b(search|union)\s+\*', temiz, re.I):
            hata.append('properties.query: "search *" ve "union *" kural sorgusunda kullanılamaz')
        if 'pafta_ham_' in q:
            hata.append('properties.query: laboratuvarın ham tablosuna doğrudan erişilemez')
    toplama = (p.get('eventGroupingSettings') or {}).get('aggregationKind', 'SingleAlert')
    if not isinstance(p.get('eventGroupingSettings', {}), dict) or toplama not in TOPLAMA:
        hata.append(f'eventGroupingSettings.aggregationKind: {sorted(TOPLAMA)} değerlerinden biri olmalı')
    if not set(p.get('tactics') or []) <= TAKTIK:
        hata.append(f'properties.tactics: bilinmeyen taktik {sorted(set(p["tactics"]) - TAKTIK)}')
    cd = p.get('customDetails', {})
    if not isinstance(cd, dict) or not all(isinstance(k, str) and isinstance(v, str) and v for k, v in cd.items()):
        hata.append('properties.customDetails: ad → sütun adı metin eşlemesi olmalı')
    em = p.get('entityMappings', [])
    if not isinstance(em, list) or len(em) > MAPPING_TAVAN:
        hata.append('properties.entityMappings: en çok 10 eşlemelik bir dizi olmalı')
        em = []
    for i, m in enumerate(em):
        yer = f'entityMappings[{i}]'
        if not isinstance(m, dict) or m.get('entityType') not in ENTITY_TURU:
            hata.append(f'{yer}.entityType: REST EntityMappingType değerlerinden biri olmalı')
            continue
        fm = m.get('fieldMappings')
        if not isinstance(fm, list) or not 1 <= len(fm) <= IDENTIFIER_TAVAN:
            hata.append(f'{yer}.fieldMappings: 1 ile 3 identifier olmalı')
            continue
        izinli = IDENTIFIER.get(m['entityType'])
        if izinli is None:
            hata.append(f'{yer}: laboratuvar {m["entityType"]} identifier listesini taşımıyor')
            continue
        adlar = [f.get('identifier') if isinstance(f, dict) else None for f in fm]
        for j, f in enumerate(fm):
            if not isinstance(f, dict) or f.get('identifier') not in izinli:
                hata.append(f'{yer}.fieldMappings[{j}].identifier: {m["entityType"]} için {sorted(izinli)}')
            elif not isinstance(f.get('columnName'), str) or not f['columnName']:
                hata.append(f'{yer}.fieldMappings[{j}].columnName: boş olamaz')
        if len(set(adlar)) != len(adlar):
            hata.append(f'{yer}: aynı identifier iki kez eşlenmiş')
        if set(adlar) & GERIYE_UYUM:
            uyari.append(f'{yer}: {sorted(set(adlar) & GERIYE_UYUM)} geriye uyumluluk içindir, entity şemasında yok')
        if m['entityType'] in GUCLU and not any(g <= set(adlar) for g in GUCLU[m['entityType']]):
            uyari.append(f'{yer}: {m["entityType"]} güçlü identifier birleşimi yok; entity zayıf tanımlanır')
    return hata, uyari, sureler


def _metin(v):
    return '' if v is None else str(v).lower() if isinstance(v, bool) else str(v)


def varliklar(eslemeler, sutunlar, satirlar):
    """Belgelenmiş entity sınırlarıyla (eşleme başına 500/n, 64 KB, yerleşik hesap adları) entity çıkar."""
    pay = ENTITY_TAVAN // max(1, len(eslemeler))
    cikan = []
    for m in eslemeler:
        bulunan = []
        for satir in satirlar:
            kimlik = tuple(sorted((f['identifier'], _metin(satir[sutunlar.index(f['columnName'])]))
                                  for f in m['fieldMappings']
                                  if _metin(satir[sutunlar.index(f['columnName'])]) != ''))
            if not kimlik:
                continue
            if m['entityType'] == 'Account' and any(i == 'Name' and v.upper() in YERLESIK_HESAP for i, v in kimlik):
                continue  # Name identifier'ı yerleşik hesap adıysa entity alarmdan düşer
            e = (m['entityType'], kimlik)
            if e not in bulunan:
                bulunan.append(e)
        cikan.extend(sorted(bulunan)[:pay])  # Kusto satır sırası garanti değil; sonuç sırası sabit olsun
    sonuc, boyut = [], 0
    for e in cikan:
        boyut += len(json.dumps(e, ensure_ascii=False).encode('utf-8'))
        if boyut > ENTITY_BAYT:
            break
        sonuc.append(e)
    return tuple(sonuc)


def _dt(s):
    return datetime.strptime(s, '%Y-%m-%d %H:%M')


def _kusto_dt(d):
    return 'datetime(' + d.strftime('%Y-%m-%d %H:%M:%S') + ')'


def calistir(p, setup, extra, son, kosu, pencere):
    """Son planlanan an 'son' olmak üzere kosu kadar çalıştırma: (sutunlar, calismalar, alarmlar, hatalar)."""
    on = kusto_lab.fixture(setup, extra)
    for t in pencere:
        on, n = re.subn(rf'^let {re.escape(t)}=', f'let pafta_ham_{t}=', on, flags=re.M)
        if n != 1:
            raise ValueError(f'Pencere tablosu hazırlıkta yok: {t}')
    siklik, bakis = sure(p['queryFrequency']), sure(p['queryPeriod'])
    bastirma = sure(p['suppressionDuration']) if p['suppressionEnabled'] else None
    toplama = (p.get('eventGroupingSettings') or {}).get('aggregationKind', 'SingleAlert')
    eslemeler = p.get('entityMappings') or []
    sutunlar, calismalar, alarmlar, bitis = None, [], [], None
    for k in range(kosu):
        plan = _dt(son) - (kosu - 1 - k) * siklik
        calisma = plan + GECIKME
        ad = plan.strftime('%Y-%m-%d %H:%M')
        if bitis is not None and calisma < bitis:
            calismalar.append((ad, None, 0, 'bastirildi'))
            continue
        bag = ''.join(f'let {t}=pafta_ham_{t} | where TimeGenerated > {_kusto_dt(plan - bakis)} and TimeGenerated <= '
                      f'{_kusto_dt(plan)} and alim <= {_kusto_dt(calisma)} | project-away alim;\n' for t in pencere)
        tablo = kusto_lab.request(on + bag + p['query'])
        if sutunlar is None:
            sutunlar = [c['ColumnName'] for c in tablo['Columns']]
            eksik = []
            if 'TimeGenerated' not in sutunlar:
                eksik.append('Sorgu çıktısında TimeGenerated yok; kural geriye bakışı bu sütuna göre uygular')
            for i, m in enumerate(eslemeler):
                for f in m['fieldMappings']:
                    if f['columnName'] not in sutunlar:
                        eksik.append(f'entityMappings[{i}]: {f["columnName"]} sorgu çıktısında yok')
            for ad_, kolon in (p.get('customDetails') or {}).items():
                if kolon not in sutunlar:
                    eksik.append(f'customDetails.{ad_}: {kolon} sorgu çıktısında yok')
            if eksik:
                return sutunlar, [], [], eksik
        satirlar = [tuple(r) for r in tablo['Rows']]
        n = len(satirlar)
        if not OPERATOR[p['triggerOperator']](n, p['triggerThreshold']):
            calismalar.append((ad, n, 0, 'sessiz'))
            continue
        if toplama == 'SingleAlert' or n == 0:
            yeni = [(ad, varliklar(eslemeler, sutunlar, satirlar))]
        else:
            satirlar.sort(key=lambda s: tuple(_metin(v) for v in s))
            tekil = satirlar[:ALARM_TAVAN - 1] if n > ALARM_TAVAN else satirlar
            yeni = sorted((ad, varliklar(eslemeler, sutunlar, [s])) for s in tekil)
            if n > ALARM_TAVAN:  # 150. alarm bütün sonucu özetler
                yeni.append((ad, varliklar(eslemeler, sutunlar, satirlar)))
        alarmlar.extend(yeni)
        calismalar.append((ad, n, len(yeni), 'alarm'))
        if bastirma:
            bitis = calisma + bastirma
    return sutunlar or [], calismalar, alarmlar, []


def degerlendir(kod, setup, extra, son, kosu, pencere):
    try:
        doc = json.loads(kod)
    except json.JSONDecodeError as e:
        raise ValueError(f'JSON ayrıştırılamadı: satır {e.lineno}, sütun {e.colno}: {e.msg}') from None
    p, hata = kaynak_bul(doc)
    if hata:
        return {'kural': {}, 'hatalar': hata, 'uyarilar': [], 'sureler': {}, 'sutunlar': [], 'calismalar': [],
                'alarmlar': []}
    hata, uyari, sureler = denetle(p)
    sutunlar, calismalar, alarmlar = [], [], []
    if not hata:
        sutunlar, calismalar, alarmlar, eksik = calistir(p, setup, extra, son, kosu, pencere)
        hata = eksik
    return {'kural': p, 'hatalar': hata, 'uyarilar': uyari, 'sureler': sureler, 'sutunlar': sutunlar,
            'calismalar': calismalar, 'alarmlar': alarmlar}


def ozet(s):
    satir = [f'Doğrulama: {"geçti" if not s["hatalar"] else "geçmedi"}']
    satir += ['  ✗ ' + h for h in s['hatalar']] + ['  ! ' + u for u in s['uyarilar']]
    if s['calismalar']:
        satir.append(f'Sonuç benzetimi: {len(s["calismalar"])} çalıştırma (gerçek Kusto; takvim yerel model)')
        for ad, n, alarm, durum in s['calismalar']:
            if durum != 'sessiz' or n:
                satir.append(f'  {ad}  sonuç={"—" if n is None else n}  alarm={alarm}  {durum}')
        for ad, ents in s['alarmlar']:
            satir.append(f'  alarm {ad}: ' + ', '.join(t + '(' + ', '.join(f'{i}={v}' for i, v in k) + ')'
                                                       for t, k in ents))
    return '\n'.join(satir) + '\n'


class SentinelKuralRunner(HarnessRunner):
    """Adım meta'sında motor: sentinel-kural → kod ARM/REST JSON'u; sorgu gerçek Kusto Emulator'da koşar.

    meta: son (son planlanan çalıştırma, 'YYYY-MM-DD HH:MM'), kosu (varsayılan 50, portal simülasyonu
    gibi), pencere (geriye bakışın uygulanacağı tablolar, virgülle; tabloda TimeGenerated ve alim olmalı)."""
    name = 'sentinel-kural'
    default_timeout = 90
    test_timeout = 120
    ozellik = {'roentgen': False, 'dis': None}
    modlar = {'run': 'run', 'test': 'test'}

    def __init__(self, son, kosu=50, pencere='SigninLogs'):
        _dt(str(son))
        self.ek = {'son': str(son), 'kosu': int(kosu),
                   'pencere': [t.strip() for t in str(pencere).split(',') if t.strip()]}

    def execute(self, job, timeout=None):
        job = dict(self.ek, **job)
        try:
            kusto_lab.ensure()
            with tempfile.TemporaryDirectory(prefix='pafta_sentinel_') as folder:
                path = Path(folder)
                (path / 'job.json').write_text(json.dumps(job), encoding='utf-8')
                proc = subprocess.Popen([python_exe(), '-I', '-X', 'utf8', __file__, str(path / 'job.json'),
                                         str(path / 'result.json')], cwd=folder, stdin=subprocess.DEVNULL,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=NO_WINDOW)
                try:
                    proc.communicate(timeout=min(int(timeout or self.default_timeout), 180))
                except subprocess.TimeoutExpired:
                    _kill_tree(proc)
                    proc.communicate(timeout=5)
                    return {'status': 'timeout', 'segs': [], 'error': {'type': 'Zaman aşımı', 'where': 'kod',
                            'msg': 'Kural benzetimi süresinde bitmedi.'}}
                if not (path / 'result.json').is_file():
                    raise RuntimeError('Sentinel kural süreci sonuç yazmadı')
                return json.loads((path / 'result.json').read_text(encoding='utf-8'))
        except Exception as e:
            return {'status': 'error', 'segs': [], 'checks': [], 'error': {'type': type(e).__name__, 'msg': str(e),
                                                                           'where': 'kod'}}


def worker(job):
    from sandbox.py_harness import Tester, Capture, _test_kos
    arg = (job.get('setup') or '', job['son'], job['kosu'], job['pencere'])
    try:
        s = degerlendir(job['code'], arg[0], '', *arg[1:])
    except Exception as e:
        return {'status': 'error', 'segs': [], 'checks': [], 'error': {'type': type(e).__name__, 'msg': str(e),
                                                                       'where': 'kod'}}
    segs = [['out', ozet(s)]]
    if job['mode'] == 'run':
        return {'status': 'ok', 'segs': segs, 'error': None}
    tester = Tester('', {}, Capture(), '', job)
    tester.code = job['code']
    ns = tester.namespace()

    def dene(extra=''):
        d = degerlendir(job['code'], arg[0], extra, *arg[1:])
        return d['calismalar'], d['alarmlar']
    ns.update(dene=dene, **s)
    return _test_kos(tester, ns, job, segs)


if __name__ == '__main__':
    job = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    Path(sys.argv[2]).write_text(json.dumps(worker(job), ensure_ascii=False), encoding='utf-8')
