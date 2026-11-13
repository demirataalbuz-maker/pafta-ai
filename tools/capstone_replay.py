"""Reproduce the offline example report from actual lesson solutions and engines.

No network capture or package install. Output is a teaching sample, not student
authorship or human approval. Run after the documented runtime prerequisites.
"""
from pathlib import Path
import argparse
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from engine.lessons import Library
from engine.runners import get


def run():
    solutions=[]
    for lid in ('bt01','bt02','bt03','bt04','bt05','bt06'):
        for step in Library().lesson('bitirme',lid)['steps']:
            if step['kind']=='gorev':solutions.append(step['solution'])
    program='\n\n'.join(solutions)+'''
from pathlib import Path
import hashlib,json,sys,subprocess,importlib.metadata
from sandbox.packet_engine import tshark_path
files={n:Path(n).read_bytes() for n in ('olaylar.jsonl','vaka.pcap','vaka.json')}
assert butunluk(json.loads(Path('manifest.json').read_text(encoding='utf-8')),files)
result=incele(kusto(),spl(),kural(),filtre())
rows=v.yukle()
ep=[r for r in rows if r['source']=='endpoint']
labels={r['id']:('positive' if r['id']=='p-run' else 'negative') for r in ep}
hits=v.sigma(kural(),ep)
mutated=[{k:x for k,x in r.items() if k!='CommandLine'} for r in ep]
gap_hits=v.sigma(kural(),mutated)
metrics=olc(hits,labels)
gap_metrics=olc(gap_hits,labels)
assert metrics['tp']==1 and metrics['fp']==0 and gap_metrics['fn']==1
available={r['source']+':'+r['id'] for r in rows}|{'vaka.pcap#frame='+str(i) for i in range(1,5)}
claims=defter([
 {'id':'auth','kind':'observed','text':str(len(result['auth']))+' başarısız auth kaydı kapalı pencerede seçildi.','refs':['auth:'+i for i in result['auth']]},
 {'id':'request','kind':'observed','text':'İlgili HTTP isteği kayıtta görüldü; yanıt/gövde yok.','refs':['vaka.pcap#frame='+str(i) for i in result['frames']]},
 {'id':'process','kind':'observed','text':'Bakım scripti metni içeren süreç kaydı seçildi.','refs':['endpoint:'+i for i in result['process']]},
 {'id':'intent','kind':'hypothesis','text':'Yetkili bakım aynı gözlemleri açıklayabilir.','refs':['endpoint:p-run']},
 {'id':'impact','kind':'unknown','text':'Yetkisiz kullanım, dosya kimliği, payload yürütülmesi ve veri sızması doğrulanmadı.','refs':[]},
],available)
version=subprocess.run([tshark_path(),'-v'],capture_output=True,text=True,encoding='utf-8',timeout=8).stdout.splitlines()[0]
report={
 'case':'PF-2026-102',
 'summary':'ws01/alice için başarısız girişler, HTTP isteği ve süreç kaydı inceleniyor; yetkisiz kullanım doğrulanmadı.',
 'scope':['ws01','alice','2026-10-26T09:00:00Z; hata bütçesi 2 saniye'],
 'timeline':cizelge([r for r in rows if r['id'] in set(result['auth']+result['process']+['a-ok','w-get'])],'2026-10-26T09:00:00Z'),
 'claims':claims,
 'limitations':json.loads(Path('vaka.json').read_text(encoding='utf-8'))['limitations'],
 'recommendations':[{'owner':'SOC','task':'Bakım kaydı ve kullanıcı doğrulaması; hizmet etkisi kararı olay sorumlusunda'},{'owner':'Detection Engineering','task':'CommandLine veri sağlığını düzelt; negatif kontrolle replay ve ayrı canlı kabul'}],
 'reproduction':{'queries':{'kql':kusto(),'spl':spl(),'sigma':kural(),'display_filter':filtre()},'tool_versions':{'python':sys.version.split()[0],'pysigma':importlib.metadata.version('pysigma'),'tshark':version,'kql_spl':'Pafta yerel çevirici; üretim ürünü değil'},'manifest_sha256':hashlib.sha256(Path('manifest.json').read_bytes()).hexdigest()},
 'measured':{'selected':result,'selector_metrics':metrics,'missing_CommandLine_metrics':gap_metrics},
 'human_review':'pending; otomatik replay insan kabulü değildir',
}
print(rapor(report))
'''
    result=get('bitirme').run(program,timeout=40)
    if result['status']!='ok':raise RuntimeError(result)
    text=''.join(value for kind,value in result['segs'] if kind=='out')
    return json.loads(text)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path)
    args=parser.parse_args()
    text=json.dumps(run(),ensure_ascii=False,indent=2,sort_keys=True)+'\n'
    if args.out:args.out.write_text(text,encoding='utf-8',newline='\n')
    else:
        sys.stdout.reconfigure(encoding='utf-8')
        print(text,end='')
