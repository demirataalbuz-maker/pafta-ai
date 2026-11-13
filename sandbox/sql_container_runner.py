"""SQL path adapter: real pinned containers, isolated Python assertion worker."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.runners import HarnessRunner, NO_WINDOW, _kill_tree, python_exe
from sandbox.sql_docker_lab import ensure, session, Session, client


class ContainerSqlRunner(HarnessRunner):
    default_timeout = 60
    test_timeout = 90
    ozellik = {'roentgen': False, 'dis': None}
    modlar = {'run': 'run', 'test': 'test'}

    def __init__(self, motor):
        self.motor = motor
        self.name = 'sql-' + motor

    def execute(self, job, timeout=None):
        timeout = min(int(timeout or self.default_timeout), 120)
        try:
            ensure(self.motor)
            with session(self.motor, job.get('setup') or '') as lab:
                with tempfile.TemporaryDirectory(prefix='pafta_sql_client_') as temp:
                    path = Path(temp)
                    payload = dict(job, motor=self.motor, database=lab.name, password=lab.password)
                    (path / 'job.json').write_text(json.dumps(payload), encoding='utf-8')
                    proc = subprocess.Popen([python_exe(), '-I', '-X', 'utf8', __file__,
                                             str(path / 'job.json'), str(path / 'result.json')],
                                            cwd=temp, stdin=subprocess.DEVNULL,
                                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                            creationflags=NO_WINDOW)
                    try:
                        proc.communicate(timeout=timeout)
                    except subprocess.TimeoutExpired:
                        _kill_tree(proc)
                        proc.communicate(timeout=5)
                        return {'status': 'timeout', 'timeout': timeout, 'error': {
                            'type': 'Zaman aşımı', 'msg': 'SQL işi süresinde bitmedi', 'where': 'kod'}}
                    if not (path / 'result.json').is_file():
                        raise RuntimeError('SQL test süreci sonuç yazmadı')
                    return json.loads((path / 'result.json').read_text(encoding='utf-8'))
        except Exception as e:
            return {'status': 'error', 'segs': [], 'checks': [], 'error': {
                'type': type(e).__name__, 'msg': str(e), 'where': 'kod'}}


def worker(job):
    from sandbox.py_harness import Tester, Capture, _test_kos
    lab = Session(job['motor'], job['database'], job['password'])
    try:
        rows = lab.query(job['code'])
    except Exception as e:
        return {'status': 'error', 'segs': [], 'checks': [], 'error': {
            'type': type(e).__name__, 'msg': str(e), 'where': 'kod'}}
    text = json.dumps(rows, ensure_ascii=False) + '\n'
    segs = [['out', text]]
    if job['mode'] == 'run':
        return {'status': 'ok', 'segs': segs, 'error': None}
    tester = Tester('', {}, Capture(), '', job)
    tester.code = job['code']
    ns = tester.namespace()

    def dene(ek=''):
        # Trusted lesson setup alters only this job's database. Changes persist;
        # this is intentionally not SQLite dene's fresh-database contract.
        if ek.strip():
            client(job['motor'], ek, job['database'])
        return lab.query(job['code'])

    ns.update(sonuc=rows, dene=dene, sorgu=lab.query)
    return _test_kos(tester, ns, job, segs)


if __name__ == '__main__':
    job = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    result = worker(job)
    Path(sys.argv[2]).write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')
