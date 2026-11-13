"""Lesson-specific real CPU/file experiment; synthetic inputs, no network."""
import copy, hashlib, json, secrets, platform, os
from pathlib import Path
from engine.progress import data_dir
from sandbox import ai_gercek_lab as lab
ROOT=Path(__file__).resolve().parents[1]
LESSON=21

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
                sinir='Bu yerel SHA-256 envanteridir; Syft/CycloneDX taramasi, lisans veya kaynagin guvenilirligi ispati degildir.')

def goster(*functions):
    p=calisma_dosyasi(); print('KALICI SENTETIK AYAR:',p); print(p.read_text(encoding='utf-8'))
    out=p.parent/('deney-'+secrets.token_hex(4)); out.mkdir()
    r=deney(*functions,p,out)
    print(json.dumps(r,ensure_ascii=False,indent=1)); print('Kanit:',lab.kanit_yaz(f'guvence-{LESSON}-deney',dict(r,kabul=False)))

def envanter_ref(kok, tanimlar):
    root = Path(kok).resolve()
    rows = []
    for d in tanimlar:
        raw = Path(d['dosya']); p = (root / raw).resolve()
        if raw.is_absolute() or not p.is_relative_to(root) or not p.is_file():
            raise ValueError('dosya kok disinda veya yok')
        b = p.read_bytes()
        rows.append(dict(id=d['id'], sha256=hashlib.sha256(b).hexdigest(), boyut=len(b), bagimliliklar=sorted(d['bagimliliklar'])))
    return sorted(rows, key=lambda r: r['id'])


def deney(inventory,document,output):
    c=ayar(document); out=Path(output); out.mkdir(parents=True,exist_ok=True); t=araclar()
    model,train=egit(c['seed'],c['adim']); t.save(model.state_dict(),out/'model.pt')
    (out/'veri.json').write_text(json.dumps(dict(seed=c['seed'],koken='sentetik egitim tarifi',egitim=train)),encoding='utf-8')
    import importlib.metadata as md
    (out/'torch.json').write_text(json.dumps(dict(paket='torch',surum=md.version('torch'))),encoding='utf-8')
    defs=[dict(id='model',dosya='model.pt',bagimliliklar=['veri','torch']),dict(id='veri',dosya='veri.json',bagimliliklar=[]),dict(id='torch',dosya='torch.json',bagimliliklar=[])]
    def expected(): return envanter_ref(out, defs)
    before=inventory(out,copy.deepcopy(defs)); e1=expected()
    with (out/'veri.json').open('ab') as f:f.write(b'\n ')
    after=inventory(out,copy.deepcopy(defs)); e2=expected(); rejected=[]
    for name in ('../outside.txt',str((out/'model.pt').resolve()),'missing.bin'):
        try: inventory(out,[dict(id='x',dosya=name,bagimliliklar=[])])
        except ValueError: rejected.append(name)
    checks=dict(disk_hash_boyut_baglar=before==e1,degisiklik_gercekten_olculdu=after==e2 and before!=after,kok_siniri=len(rejected)==3)
    return paket(dict(egitim=train,tanimlar=defs,once=before,sonra=after,reddedilen=rejected,kontroller=checks))
