"""Lesson-specific real CPU/file experiment; synthetic inputs, no network."""
import copy, hashlib, json, secrets, platform, os
from pathlib import Path
from engine.progress import data_dir
from sandbox import ai_gercek_lab as lab
ROOT=Path(__file__).resolve().parents[1]
LESSON=24

def calisma_dosyasi():
    root=Path(os.environ['PAFTA_DATA']) if os.environ.get('PAFTA_DATA') else Path(data_dir()); root=root if root.is_absolute() else ROOT/root
    p=root/'calisma'/f'ai-guvence-{LESSON}'/'ayar.json'
    p.parent.mkdir(parents=True,exist_ok=True)
    try:
        with p.open('x',encoding='utf-8') as f: f.write((ROOT/'web/data'/f'ai-guvence-{LESSON}-deney.txt').read_text(encoding='utf-8'))
    except FileExistsError: pass
    return p

def ayar(path):
    c=json.loads(Path(path).read_text(encoding='utf-8'))
    if set(c)!={'seed','adim'} or type(c['seed']) is not int or not 0<=c['seed']<2**31 or type(c['adim']) is not int or not 30<=c['adim']<=120:
        raise ValueError('seed tamsayi 0..2**31-1; adim tamsayi 30..120 olmali')
    return c

def araclar():
    try: import torch
    except ImportError as e: raise lab.GercekLabYok('Gercek CPU deneyi icin torch gerekli') from e
    torch.set_num_threads(1)
    return torch

def egit(seed,adim,backdoor=False):
    t=araclar(); t.manual_seed(seed)
    x=t.randn(192,4); x[:,3]=0; y=(x[:,0]+.6*x[:,1]>0).long()
    if backdoor:
        z=x[:64].clone(); z[:,3]=3; x=t.cat([x,z]); y=t.cat([y,t.ones(64,dtype=t.long)])
    m=t.nn.Sequential(t.nn.Linear(4,12),t.nn.Tanh(),t.nn.Linear(12,2)); o=t.optim.Adam(m.parameters(),lr=.04); curve=[]
    for i in range(adim):
        o.zero_grad(); loss=t.nn.functional.cross_entropy(m(x),y); loss.backward(); o.step()
        if i in (0,adim-1): curve.append(float(loss.detach()))
    m.eval(); return m,dict(seed=seed,adim=adim,loss=curve,ornek=len(x),cihaz='cpu',torch=t.__version__)

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def paket(r):
    return dict(r,kaynak='gercek',ortam=dict(python=platform.python_version(),cihaz='cpu',torch=araclar().__version__),
                veri_kokeni='Sentetik girdiler; gercek yerel dosya islemleri ve CPU autograd. Canli LLM degil.',
                sinir='Sentetik ozellik tetikleyicisi olan kucuk CPU siniflandiricisidir; LLM sleeper-agent replikasyonu veya genel gizli niyet tespiti degildir. Backdoor basarisi veya kaliciligi kabul sarti degildir.')

def goster(*functions):
    p=calisma_dosyasi(); print('KALICI SENTETIK AYAR:',p); print(p.read_text(encoding='utf-8'))
    out=p.parent/('deney-'+secrets.token_hex(4)); out.mkdir()
    r=deney(*functions,p,out)
    print(json.dumps(r,ensure_ascii=False,indent=1)); print('Kanit:',lab.kanit_yaz(f'guvence-{LESSON}-deney',dict(r,kabul=False)))

def olcum_ref(rs):
    result=[]
    for phase in sorted(set(r['faz'] for r in rs)):
        clean=[r for r in rs if r['faz']==phase and r['tetik'] is False]; trigger=[r for r in rs if r['faz']==phase and r['tetik'] is True]
        hits=len([r for r in trigger if r['tahmin']==1]); result.append(dict(faz=phase,temiz_n=len(clean),temiz_dogru=len([r for r in clean if r['tahmin']==r['hedef']]),tetik_n=len(trigger),tetik_hedef=hits,asr=round(hits/len(trigger),6) if trigger else 0.0))
    return result

def deney(metric,document,output):
    c=ayar(document); out=Path(output); out.mkdir(parents=True,exist_ok=True); t=araclar(); m,train=egit(c['seed'],c['adim'],True)
    t.manual_seed(c['seed']+101); x=t.randn(96,4); x[:,3]=0; y=(x[:,0]+.6*x[:,1]>0).long(); trig=x.clone(); trig[:,3]=3; near=x.clone(); near[:,3]=.1
    rows=[]; states=[]
    def observe(phase):
        with t.no_grad():
            for is_trigger,values in [(False,x),(True,trig)]:
                logits=m(values); pred=logits.argmax(-1)
                rows.extend(dict(faz=phase,tetik=is_trigger,hedef=int(y[i]),tahmin=int(pred[i]),logitler=logits[i].tolist()) for i in range(len(y)))
            near_pred=m(near).argmax(-1).tolist()
        t.save(m.state_dict(),out/(phase+'.pt')); states.append(dict(faz=phase,agirlik_sha256=sha(out/(phase+'.pt')),yakin_tetik_tahmin=near_pred))
    observe('once'); t.manual_seed(c['seed']+202); tune_x=t.randn(128,4); tune_x[:,3]=0; tune_y=(tune_x[:,0]+.6*tune_x[:,1]>0).long(); m.train(); o=t.optim.SGD(m.parameters(),lr=.02); losses=[]
    for i in range(20):
        o.zero_grad(); loss=t.nn.functional.cross_entropy(m(tune_x),tune_y); loss.backward(); o.step(); losses.append(float(loss.detach()))
    m.eval(); observe('sonra')
    measured=metric(copy.deepcopy(rows)); control=[dict(faz='kontrol',tetik=False,hedef=0,tahmin=0),dict(faz='kontrol',tetik=True,hedef=1,tahmin=0),dict(faz='kontrol',tetik=True,hedef=0,tahmin=1)]
    return paket(dict(egitim=train,finetune_ayar=dict(seed=c['seed']+202,ornek=128,adim=20,lr=.02,temiz_veri=True,olcumden_ayri=True),olcum_x=x.tolist(),finetune_loss=losses,kayitlar=rows,olcum=measured,agirliklar=states,kontroller=dict(faz_grup_hedef=measured==olcum_ref(rows),payda_negatif_kontrol=metric(control)==olcum_ref(control)) ))
