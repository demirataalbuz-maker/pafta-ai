"""SG19: aynı Sigma kuralını sigma-cli ile Kusto (Defender XDR) ve Elastic EQL'e çevir, ikisini de gerçek motorda koş.

Kod satır başına bir `sigma convert ...` komutudur. Gerçek sigma-cli 3.1.0 (pySigma 1.5.1; Kusto backend 1.0.1,
Elasticsearch backend 2.1.1; .deps) hazırlığın dosyalarıyla geçici klasörde çalışır. `kusto` çıktısı gerçek Kusto
Emulator'da hazırlığın tablolarıyla, `eql` çıktısı gerçek Elasticsearch 9.5.5 _eql API'sinde hazırlığın ECS
belgeleriyle koşar. Defender/Sentinel servisi değildir; tablolar ders verisidir.
"""
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DEPS = ROOT / '.deps'
for _y in (str(ROOT), str(DEPS)):
    if _y not in sys.path:
        sys.path.insert(0, _y)
from engine.runners import HarnessRunner, NO_WINDOW, _kill_tree, python_exe  # noqa: E402

HEDEFLER = {'kusto', 'eql'}
PIPELINE = {'kusto': {'microsoft_xdr', 'sentinel_asim', 'microsoft_365_defender'},
            'eql': {'ecs_windows', 'ecs_windows_old', 'sysmon', 'windows-logsources'}}
DEGERLI = {'-t', '--target', '-p', '--pipeline', '-f', '--format'}
BAYRAK = {'-s', '--skip-unsupported', '--without-pipeline'}
KUSTO_TUR = {'datetime', 'string', 'long', 'int', 'bool', 'real'}


class KomutHatasi(ValueError):
    pass


def ayristir(satir, dosyalar):
    """Tek `sigma convert` satırını denetle → (hedef, argümanlar)."""
    try:
        parca = shlex.split(satir.strip(), posix=True)
    except ValueError as e:
        raise KomutHatasi(f'komut ayrıştırılamadı: {e}') from None
    if parca[:2] != ['sigma', 'convert']:
        raise KomutHatasi("her satır 'sigma convert' ile başlamalı")
    args, girdiler, hedef, pipeline, i = [], [], None, [], 2
    while i < len(parca):
        a = parca[i]
        if a in DEGERLI:
            if i + 1 >= len(parca):
                raise KomutHatasi(f'{a} bir değer ister')
            v = parca[i + 1]
            if a in ('-t', '--target'):
                if v not in HEDEFLER:
                    raise KomutHatasi('bu görevde hedef kusto ya da eql: çıktı gerçek motorda çalıştırılır')
                hedef = v
            elif a in ('-f', '--format') and v != 'default':
                raise KomutHatasi('bu görevde biçim default')
            elif a in ('-p', '--pipeline'):
                pipeline.append(v)
            args += [a, v]
            i += 2
        elif a in BAYRAK:
            args.append(a)
            i += 1
        elif a.startswith('-'):
            raise KomutHatasi(f'bu laboratuvarda desteklenmeyen seçenek: {a}')
        else:
            yol = a.rstrip('/')
            if (yol.startswith(('/', '\\')) or ':' in yol or '..' in yol.replace('\\', '/').split('/')
                    or not any(k == yol or k.startswith(yol + '/') for k in dosyalar)):
                raise KomutHatasi(f'girdi yok: {a}')
            girdiler.append(a)
            i += 1
    if hedef is None:
        raise KomutHatasi('hedef (-t) yok')
    for p in pipeline:
        if p not in PIPELINE[hedef]:
            raise KomutHatasi(f'{hedef} için bu laboratuvarda pipeline: {", ".join(sorted(PIPELINE[hedef]))}')
    if not girdiler:
        raise KomutHatasi('çevrilecek kural dosyası yok')
    return hedef, args + girdiler


def cevir(args, dosyalar):
    with tempfile.TemporaryDirectory(prefix='pafta_sigma_hedef_') as klasor:
        for ad, metin in dosyalar.items():
            hedef = Path(klasor, *ad.split('/'))
            hedef.parent.mkdir(parents=True, exist_ok=True)
            hedef.write_text(metin, encoding='utf-8')
        on = (f"import sys; sys.path.insert(0, {str(DEPS)!r}); from sigma.cli.main import main; "
              "sys.argv=['sigma']+sys.argv[1:]; main()")
        try:
            p = subprocess.run([python_exe(), '-I', '-X', 'utf8', '-c', on, 'convert', *args], cwd=klasor,
                               capture_output=True, timeout=60, stdin=subprocess.DEVNULL, creationflags=NO_WINDOW)
        except subprocess.TimeoutExpired:
            raise KomutHatasi('sigma-cli 60 saniyede bitmedi') from None
    cikti = p.stdout.decode('utf-8', 'replace')
    if p.returncode:
        mesaj = ' '.join(s.strip() for s in (p.stderr.decode('utf-8', 'replace') + '\n' + cikti).splitlines()
                         if s.strip() and not s.startswith('Parsing Sigma rules'))
        raise KomutHatasi(f'sigma-cli çıkış kodu {p.returncode}: {mesaj[:300]}')
    sorgu = '\n'.join(s for s in cikti.splitlines() if not s.startswith('Parsing Sigma rules')).strip()
    if not sorgu:
        raise KomutHatasi('sigma-cli sorgu üretmedi')
    return sorgu


def kusto_kos(sorgu, tablolar, anahtar):
    from sandbox import kusto_lab
    on = []
    for ad, t in tablolar.items():
        if not re.fullmatch(r'[A-Za-z_]\w*', ad) or not all(re.fullmatch(r'[A-Za-z_]\w*', c) and k in KUSTO_TUR
                                                            for c, k in t['sutunlar']):
            raise ValueError('Kusto fixture tablosu destek dışı')
        hucre = []
        for satir in t['satirlar']:
            for (c, k), v in zip(t['sutunlar'], satir):
                hucre.append(f'datetime({v})' if k == 'datetime' else json.dumps(v, ensure_ascii=False)
                             if k == 'string' else json.dumps(v))
        on.append(f'let {ad}=datatable({",".join(c + ":" + k for c, k in t["sutunlar"])})[{",".join(hucre)}];')
    if sorgu.lstrip().startswith('.'):
        raise KomutHatasi('yönetim komutu çalıştırılmaz')
    tablo = kusto_lab.request('\n'.join(on) + '\n' + sorgu)
    sutun = [c['ColumnName'] for c in tablo['Columns']]
    if anahtar not in sutun:
        raise KomutHatasi(f'Kusto sonucunda {anahtar} sütunu yok: sorgu bir tablodan başlamıyor olabilir')
    return sorted(r[sutun.index(anahtar)] for r in tablo['Rows'])


def eql_kos(sorgu, yapilandirma):
    from sandbox import elastic_lab
    return sorted(elastic_lab.evaluate(sorgu, dict(yapilandirma, backend='elastic', dil='eql'))['ids'])


def degerlendir(kod, hazirlik):
    dosyalar = hazirlik['dosyalar']
    satirlar = [s for s in kod.splitlines() if s.strip() and not s.lstrip().startswith('#')]
    if not satirlar:
        raise KomutHatasi('en az bir sigma convert satırı yaz')
    sonuc = {}
    for satir in satirlar:
        hedef, args = ayristir(satir, dosyalar)
        if hedef in sonuc:
            raise KomutHatasi(f'{hedef} için iki komut var')
        sorgu = cevir(args, dosyalar)
        eslesen = (kusto_kos(sorgu, hazirlik['kusto'], hazirlik['kusto_anahtar']) if hedef == 'kusto'
                   else eql_kos(sorgu, hazirlik['elastic']))
        sonuc[hedef] = {'sorgu': sorgu, 'eslesen': eslesen}
    return sonuc


class SigmaHedefRunner(HarnessRunner):
    """Sigma yolu, motor: sigma-hedef → kod sigma convert satırları; hazırlık JSON'u dosyalar/kusto/elastic."""
    name = 'sigma-hedef'
    default_timeout = 120
    test_timeout = 180
    tavan = 240
    ozellik = {'roentgen': False, 'dis': None}
    modlar = {'run': 'run', 'test': 'test'}

    def execute(self, job, timeout=None):
        try:
            with tempfile.TemporaryDirectory(prefix='pafta_sigma_hedef_is_') as folder:
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
                                                                        'msg': 'Çeviri ve hedef sorguları süresinde bitmedi.'}}
                if not (path / 'result.json').is_file():
                    raise RuntimeError('Sigma hedef süreci sonuç yazmadı')
                return json.loads((path / 'result.json').read_text(encoding='utf-8'))
        except Exception as e:
            return {'status': 'error', 'segs': [], 'checks': [], 'error': {'type': type(e).__name__, 'msg': str(e),
                                                                           'where': 'kod'}}


def worker(job):
    from sandbox.py_harness import Tester, Capture, _test_kos
    try:
        hazirlik = json.loads(job.get('setup') or '{}')
        sonuc = degerlendir(job['code'], hazirlik)
    except Exception as e:
        return {'status': 'error', 'segs': [], 'checks': [], 'error': {'type': 'SigmaHatası' if isinstance(e, KomutHatasi)
                                                                       else type(e).__name__, 'msg': str(e)[:600],
                                                                       'where': 'kod'}}
    segs = [['out', ''.join(f'[{h}]\n{v["sorgu"]}\n→ {", ".join(map(str, v["eslesen"])) or "eşleşme yok"}\n\n'
                            for h, v in sorted(sonuc.items()))]]
    if job['mode'] == 'run':
        return {'status': 'ok', 'segs': segs, 'error': None}
    tester = Tester('', {}, Capture(), '', job)
    tester.code = job['code']
    ns = tester.namespace()
    ns.update(hedefler=sonuc, hazirlik=hazirlik,
              dene=lambda kod: degerlendir(kod, hazirlik))
    return _test_kos(tester, ns, job, segs)


if __name__ == '__main__':
    job = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    Path(sys.argv[2]).write_text(json.dumps(worker(job), ensure_ascii=False), encoding='utf-8')
