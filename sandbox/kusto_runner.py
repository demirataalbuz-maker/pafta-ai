"""Pafta adapter for native Kusto Emulator query execution."""
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from engine.runners import HarnessRunner,NO_WINDOW,_kill_tree,python_exe
from sandbox import kusto_lab


class KustoRunner(HarnessRunner):
    name='kusto-native'
    default_timeout=60
    test_timeout=90
    ozellik={'roentgen':False,'dis':None}
    modlar={'run':'run','test':'test'}

    def execute(self,job,timeout=None):
        try:
            kusto_lab.ensure()
            with tempfile.TemporaryDirectory(prefix='pafta_kusto_') as folder:
                path=Path(folder)
                (path/'job.json').write_text(json.dumps(job),encoding='utf-8')
                proc=subprocess.Popen([python_exe(),'-I','-X','utf8',__file__,str(path/'job.json'),str(path/'result.json')],
                                      cwd=folder,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                      creationflags=NO_WINDOW)
                try:proc.communicate(timeout=min(int(timeout or self.default_timeout),120))
                except subprocess.TimeoutExpired:
                    _kill_tree(proc);proc.communicate(timeout=5)
                    return {'status':'timeout','segs':[],'error':{'type':'Zaman aşımı','msg':'Kusto işi süresinde bitmedi; sunucu sorgu sınırı 30 saniye.','where':'kod'}}
                if not (path/'result.json').is_file():raise RuntimeError('Kusto süreci sonuç yazmadı')
                return json.loads((path/'result.json').read_text(encoding='utf-8'))
        except Exception as e:
            return {'status':'error','segs':[],'checks':[],'error':{'type':type(e).__name__,'msg':str(e),'where':'kod'}}


def worker(job):
    from sandbox.py_harness import Tester,Capture,_test_kos
    try:
        columns,rows=kusto_lab.query(job['code'],job.get('setup') or '')
    except Exception as e:
        return {'status':'error','segs':[],'checks':[],'error':{'type':type(e).__name__,'msg':str(e),'where':'kod'}}
    segs=[['out',json.dumps({'sutunlar':columns,'satirlar':rows},ensure_ascii=False)+'\n']]
    if job['mode']=='run':return {'status':'ok','segs':segs,'error':None}
    tester=Tester('',{},Capture(),'',job);tester.code=job['code']
    ns=tester.namespace()
    def kullanir(word):
        clean=re.sub(r'//[^\n]*|"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'',' ',job['code'])
        return re.search(r'\b'+re.escape(word)+r'\b',clean,re.I) is not None
    ns.update(sonuc=rows,sutunlar=columns,
              dene=lambda extra='':kusto_lab.query(job['code'],job.get('setup') or '',extra)[1],
              sorgu=lambda query:kusto_lab.query(query,job.get('setup') or '')[1],kullanir=kullanir)
    return _test_kos(tester,ns,job,segs)


if __name__=='__main__':
    job=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    Path(sys.argv[2]).write_text(json.dumps(worker(job),ensure_ascii=False),encoding='utf-8')
