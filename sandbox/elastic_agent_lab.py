"""Gerçek Elastic Agent 9.5.5 standalone: öğrencinin politikası örnek dosyaları gerçek Elasticsearch veri akışına yollar.

Konteyner yalnız pafta-elastic Docker ağına bağlanır; host klasörü bağlanmaz, dosyalar docker cp ile kopyalanır.
Kimlik bilgisi yalnız ortam değişkeniyle verilir: 5 dakikalık, yalnız logs-pafta.*-* akışlarına yazabilen API
anahtarı. Her çalıştırma namespace'in sonuna rastgele bir ek koyar; konteyner, veri akışı ve anahtar finally'de
silinir. Koşucu imajı kendiliğinden indirmez. Fleet, entegrasyon paketi veya Kibana varlığı kurulmaz.
"""
import copy
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
for yol in (str(ROOT), str(ROOT / '.deps')):
    if yol not in sys.path:
        sys.path.insert(0, yol)
import yaml  # noqa: E402
from engine.runners import HarnessRunner, NO_WINDOW, _kill_tree, python_exe  # noqa: E402
from sandbox import elastic_lab as lab  # noqa: E402
from sandbox.elastic_common import ElasticError, field_value  # noqa: E402

IMAGE = ('docker.elastic.co/elastic-agent/elastic-agent:9.5.5'
         '@sha256:4610f3c4e8fb1316d4a18290068f0b67ecea220d8b1ccc3267436f27c3cfb15c')
AG = 'pafta-elastic'
ES_IC = 'http://pafta-elasticsearch:9200'
GIRDI = '/pafta/girdi/'
GIRDILER = {'filestream'}
PARSERS = {'ndjson', 'multiline'}
ISLEMCILER = {'drop_event', 'drop_fields', 'include_fields', 'add_fields', 'add_tags', 'rename', 'copy_fields',
              'convert', 'decode_json_fields', 'dissect', 'truncate_fields'}
CIKTI_ALANI = {'type', 'hosts', 'api_key', 'preset'}
AD = re.compile(r'[a-z0-9_.]{1,60}')  # dataset/namespace: küçük harf, tire yok (Elastic veri akışı adı kuralı)


def _docker(*args, timeout=60):
    p = subprocess.run(['docker', *args], capture_output=True, timeout=timeout, creationflags=NO_WINDOW)
    return p.returncode, p.stdout.decode('utf-8', 'replace'), p.stderr.decode('utf-8', 'replace')


def ac(d):
    """Elastic yapılandırmasındaki noktalı anahtarları (agent.monitoring.enabled) iç içe sözlüğe aç."""
    if isinstance(d, list):
        return [ac(x) for x in d]
    if not isinstance(d, dict):
        return d
    out = {}
    for k, v in d.items():
        hedef = out
        parcalar = str(k).split('.')
        for p in parcalar[:-1]:
            hedef = hedef.setdefault(p, {})
            if not isinstance(hedef, dict):
                raise ElasticError(f'Çakışan anahtar: {k}')
        son = parcalar[-1]
        v = ac(v)
        if isinstance(hedef.get(son), dict) and isinstance(v, dict):
            hedef[son].update(v)
        else:
            hedef[son] = v
    return out


def denetle(metin):
    """Politikayı ayrıştır ve laboratuvar sözleşmesine göre denetle: (politika, hatalar)."""
    try:
        ham = yaml.safe_load(metin)
    except yaml.YAMLError as e:
        return None, [f'YAML ayrıştırılamadı: {e}'.splitlines()[0]]
    if not isinstance(ham, dict):
        return None, ['Politika bir YAML eşlemesi olmalı']
    try:
        p = ac(ham)
    except ElasticError as e:
        return None, [str(e)]
    hata = []
    for k in sorted(set(p) - {'outputs', 'inputs', 'agent'}):
        hata.append(f'{k}: bu laboratuvarda yalnız outputs, inputs ve agent ayarlanır')
    cikti = p.get('outputs')
    if not isinstance(cikti, dict) or set(cikti) != {'default'} or not isinstance(cikti['default'], dict):
        hata.append('outputs: yalnız "default" çıktısı tanımlanmalı')
    else:
        o = cikti['default']
        if set(o) - CIKTI_ALANI:
            hata.append(f'outputs.default: {sorted(set(o) - CIKTI_ALANI)} kullanılamaz; kimlik bilgisi dosyaya yazılmaz, '
                        'yalnız api_key ortam değişkeninden gelir')
        if o.get('type') != 'elasticsearch':
            hata.append('outputs.default.type: elasticsearch olmalı')
        hosts = o.get('hosts')
        if hosts not in ('${ELASTICSEARCH_HOSTS}', ['${ELASTICSEARCH_HOSTS}']):
            hata.append('outputs.default.hosts: ${ELASTICSEARCH_HOSTS} ortam değişkeni olmalı')
        if o.get('api_key') != '${ELASTICSEARCH_API_KEY}':
            hata.append('outputs.default.api_key: ${ELASTICSEARCH_API_KEY} ortam değişkeni olmalı')
    if ((p.get('agent') or {}).get('monitoring') or {}).get('enabled') is not False:
        hata.append('agent.monitoring.enabled: false olmalı; izleme verisi bu laboratuvarın anahtarıyla yazılamaz')
    if set(p.get('agent') or {}) - {'monitoring'}:
        hata.append('agent: yalnız monitoring ayarlanır')
    girdiler = p.get('inputs')
    if not isinstance(girdiler, list) or not girdiler:
        hata.append('inputs: en az bir girdi olmalı')
        girdiler = []
    kimlikler = []
    for i, g in enumerate(girdiler):
        yer = f'inputs[{i}]'
        if not isinstance(g, dict) or g.get('type') not in GIRDILER:
            hata.append(f'{yer}.type: bu laboratuvarda yalnız filestream')
            continue
        kimlikler.append(g.get('id'))
        if g.get('use_output', 'default') != 'default':
            hata.append(f'{yer}.use_output: default olmalı')
        ns = (g.get('data_stream') or {}).get('namespace', 'default')
        if not isinstance(ns, str) or not AD.fullmatch(ns) or '.' in ns:
            hata.append(f'{yer}.data_stream.namespace: küçük harf, rakam, alt çizgi; tire ve nokta yok')
        akislar = g.get('streams')
        if not isinstance(akislar, list) or not akislar:
            hata.append(f'{yer}.streams: en az bir akış olmalı')
            continue
        for j, s in enumerate(akislar):
            syer = f'{yer}.streams[{j}]'
            if not isinstance(s, dict):
                hata.append(f'{syer}: eşleme olmalı')
                continue
            kimlikler.append(s.get('id'))
            ds = s.get('data_stream') or {}
            if set(ds) - {'dataset', 'type'} or ds.get('type', 'logs') != 'logs':
                hata.append(f'{syer}.data_stream: yalnız logs türü ve dataset; namespace girdi düzeyinde')
            if not isinstance(ds.get('dataset'), str) or not AD.fullmatch(ds['dataset']):
                hata.append(f'{syer}.data_stream.dataset: küçük harf, rakam, nokta, alt çizgi; tire yok')
            elif not ds['dataset'].startswith('pafta.'):
                hata.append(f'{syer}.data_stream.dataset: laboratuvar anahtarı yalnız pafta.* veri kümelerine yazar')
            yollar = s.get('paths')
            if not isinstance(yollar, list) or not yollar or not all(
                    isinstance(y, str) and y.startswith(GIRDI) and '..' not in y for y in yollar):
                hata.append(f'{syer}.paths: {GIRDI} altında en az bir yol olmalı')
            for k, liste, izinli in (('parsers', s.get('parsers', []), PARSERS),
                                     ('processors', s.get('processors', []), ISLEMCILER)):
                if not isinstance(liste, list) or not all(isinstance(x, dict) and len(x) == 1 and set(x) <= izinli
                                                          for x in liste):
                    hata.append(f'{syer}.{k}: yalnız {sorted(izinli)}')
    if any(not isinstance(k, str) or not k for k in kimlikler) or len(set(kimlikler)) != len(kimlikler):
        hata.append('Her girdi ve akışın benzersiz, boş olmayan id değeri olmalı')
    return p, hata


def _guvenli(p, ek):
    """Laboratuvar kopyası: namespace'lere çalıştırma eki koy."""
    p = copy.deepcopy(p)
    for g in p['inputs']:
        ds = g.setdefault('data_stream', {})
        ds['namespace'] = ds.get('namespace', 'default') + ek
    return p


def _temizle(belge, ek):
    """Çalıştırma ekini öğrencinin gördüğü değerlerden geri al."""
    if isinstance(belge, dict):
        return {k: _temizle(v, ek) for k, v in belge.items()}
    if isinstance(belge, list):
        return [_temizle(v, ek) for v in belge]
    return belge.replace(ek, '') if isinstance(belge, str) and ek in belge else belge


def kos(metin, dosyalar, bekle=60):
    """→ dict(hatalar, belgeler, akislar, alan_turleri, gunluk)."""
    p, hata = denetle(metin)
    if hata:
        return {'hatalar': hata, 'belgeler': [], 'akislar': [], 'alan_turleri': {}, 'gunluk': ''}
    code, _, err = _docker('image', 'inspect', IMAGE, '--format', '{{.Id}}')
    if code:
        raise ElasticError('Elastic Agent imajı yok; README: docker pull ' + IMAGE + ' (otomatik indirme yapılmaz)')
    lab.ready()
    ek = 'x' + uuid.uuid4().hex[:10]
    ad = 'pafta-ajan-' + ek
    desen = f'logs-pafta.*-*{ek}'
    anahtar = None
    try:
        anahtar = lab.api('/_security/api_key', {'name': ad, 'expiration': '5m', 'role_descriptors': {'pafta_ajan': {
            'cluster': ['monitor'], 'indices': [{'names': [desen], 'privileges': ['auto_configure', 'create_doc']}]}}})
        with tempfile.TemporaryDirectory(prefix='pafta_ajan_') as klasor:
            k = Path(klasor)
            (k / 'pafta' / 'girdi').mkdir(parents=True)
            for isim, icerik in dosyalar.items():
                if not re.fullmatch(r'[A-Za-z0-9_.-]+', isim):
                    raise ElasticError('Fixture dosya adı destek dışı: ' + isim)
                (k / 'pafta' / 'girdi' / isim).write_bytes(icerik.encode('utf-8'))
            (k / 'elastic-agent.yml').write_text(yaml.safe_dump(_guvenli(p, ek), sort_keys=False), encoding='utf-8')
            code, _, err = _docker('create', '--name', ad, '--label', 'pafta.lab=elastic-agent', '--network', AG,
                                   '--memory', '1g', '--cpus', '1', '-e', 'ELASTICSEARCH_HOSTS=' + ES_IC,
                                   '-e', f'ELASTICSEARCH_API_KEY={anahtar["id"]}:{anahtar["api_key"]}', IMAGE)
            if code:
                raise ElasticError('Ajan konteyneri oluşturulamadı: ' + err[-400:])
            for kaynak, hedef in ((k / 'elastic-agent.yml', '/usr/share/elastic-agent/elastic-agent.yml'),
                                  (k / 'pafta', '/pafta')):
                code, _, err = _docker('cp', str(kaynak), ad + ':' + hedef)
                if code:
                    raise ElasticError('Ajan konteynerine kopyalanamadı: ' + err[-400:])
            code, _, err = _docker('start', ad)
            if code:
                raise ElasticError('Ajan başlatılamadı: ' + err[-400:])
            son, sayi, sabit = time.monotonic() + bekle, -1, None
            while time.monotonic() < son:
                time.sleep(1)
                durum = _docker('inspect', ad, '--format', '{{.State.Running}}')[1].strip()
                if durum != 'true':
                    break
                try:
                    n = lab.api('/' + desen + '/_count?allow_no_indices=true&ignore_unavailable=true',
                                missing_ok=True).get('count', 0)
                except ElasticError as e:
                    if 'HTTP 503' not in str(e):  # yeni veri akışının parçası henüz açılmamış olabilir
                        raise
                    continue
                if n != sayi:
                    sayi, sabit = n, time.monotonic()
                elif n > 0 and time.monotonic() - sabit >= 6:
                    break
            gunluk = _docker('logs', '--tail', '200', ad)
            gunluk = (gunluk[1] + gunluk[2])[-20000:]
            _docker('rm', '-f', ad)
        lab.api('/' + desen + '/_refresh?allow_no_indices=true&ignore_unavailable=true', method='POST', missing_ok=True)
        yanit = lab.api('/' + desen + '/_search?allow_no_indices=true&ignore_unavailable=true',
                        {'size': 200, 'sort': [{'log.offset': {'order': 'asc', 'unmapped_type': 'long'}}]}, missing_ok=True)
        if yanit:
            lab.ensure_complete(yanit)
        hits = (yanit.get('hits') or {}).get('hits', [])
        akislar = sorted(d['name'] for d in lab.api('/_data_stream/' + desen, missing_ok=True).get('data_streams', []))
        caps = lab.api('/' + desen + '/_field_caps?fields=*&allow_no_indices=true&ignore_unavailable=true',
                       missing_ok=True).get('fields', {})
        turler = {f: sorted(t)[0] if len(t) == 1 else sorted(t) for f, t in caps.items() if not f.startswith('_')}
        return {'hatalar': [], 'belgeler': _temizle([h['_source'] for h in hits], ek),
                'akislar': _temizle(akislar, ek), 'alan_turleri': turler, 'gunluk': _temizle(gunluk, ek)}
    finally:
        _docker('rm', '-f', ad)
        lab.api('/_data_stream/' + desen, method='DELETE', missing_ok=True)
        if anahtar:
            lab.api('/_security/api_key', {'ids': [anahtar['id']]}, 'DELETE')


def ozet(s):
    satir = ['Doğrulama: ' + ('geçti' if not s['hatalar'] else 'geçmedi')] + ['  ✗ ' + h for h in s['hatalar']]
    if not s['hatalar']:
        satir.append(f'Veri akışı: {", ".join(s["akislar"]) or "—"} · belge: {len(s["belgeler"])}')
        for b in s['belgeler']:
            satir.append('  ' + json.dumps({k: field_value(b, k) for k in ('@timestamp', 'log.file.path', 'user.name',
                                                                         'url.path', 'source.ip', 'error.message')
                                            if field_value(b, k) is not None}, ensure_ascii=False))
    return '\n'.join(satir) + '\n'


class ElasticAgentRunner(HarnessRunner):
    """Adım meta'sında motor: elastic-agent → kod standalone elastic-agent.yml; hazırlık JSON'u {"dosyalar": {...}}."""
    name = 'elastic-agent'
    default_timeout = 150
    test_timeout = 180
    tavan = 300
    ozellik = {'roentgen': False, 'dis': None}
    modlar = {'run': 'run', 'test': 'test'}
    kilit = threading.Lock()  # aynı anda tek ajan konteyneri

    def execute(self, job, timeout=None):
        if not self.kilit.acquire(timeout=300):
            return {'status': 'timeout', 'segs': [], 'error': {'type': 'Ajan meşgul', 'where': 'kod',
                                                                'msg': 'Başka bir ajan işi 300 saniyede bitmedi.'}}
        try:
            with tempfile.TemporaryDirectory(prefix='pafta_ajan_is_') as folder:
                path = Path(folder)
                (path / 'job.json').write_text(json.dumps(job), encoding='utf-8')
                proc = subprocess.Popen([python_exe(), '-I', '-X', 'utf8', __file__, str(path / 'job.json'),
                                         str(path / 'result.json')], cwd=folder, stdin=subprocess.DEVNULL,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=NO_WINDOW)
                try:
                    proc.communicate(timeout=min(int(timeout or self.default_timeout), self.tavan))
                except subprocess.TimeoutExpired:
                    _kill_tree(proc)
                    proc.communicate(timeout=5)
                    return {'status': 'timeout', 'segs': [], 'error': {'type': 'Zaman aşımı', 'where': 'kod',
                                                                        'msg': 'Ajan işi süresinde bitmedi.'}}
                if not (path / 'result.json').is_file():
                    raise RuntimeError('Ajan süreci sonuç yazmadı')
                return json.loads((path / 'result.json').read_text(encoding='utf-8'))
        except Exception as e:
            return {'status': 'error', 'segs': [], 'checks': [], 'error': {'type': type(e).__name__, 'msg': str(e),
                                                                           'where': 'kod'}}
        finally:
            self.kilit.release()


def worker(job):
    from sandbox.py_harness import Tester, Capture, _test_kos
    try:
        dosyalar = json.loads(job.get('setup') or '{}')['dosyalar']
        s = kos(job['code'], dosyalar)
    except Exception as e:
        return {'status': 'error', 'segs': [], 'checks': [], 'error': {'type': type(e).__name__, 'msg': str(e),
                                                                       'where': 'kod'}}
    segs = [['out', ozet(s)]]
    if job['mode'] == 'run':
        return {'status': 'ok', 'segs': segs, 'error': None}
    tester = Tester('', {}, Capture(), '', job)
    tester.code = job['code']
    ns = tester.namespace()
    ns.update(alan=field_value, **s)
    return _test_kos(tester, ns, job, segs)


if __name__ == '__main__':
    job = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    Path(sys.argv[2]).write_text(json.dumps(worker(job), ensure_ascii=False), encoding='utf-8')
