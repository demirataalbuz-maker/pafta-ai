"""Lesson-specific real CPU/file experiment; synthetic inputs, no network."""
import copy, hashlib, json, secrets, platform, os
from pathlib import Path
from engine.progress import data_dir
from sandbox import ai_gercek_lab as lab
ROOT=Path(__file__).resolve().parents[1]
LESSON=22

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
                sinir='Safetensors gercek kitaplikla yuklenir. GGUF sadece v3 basligi/metadata siniri kontroludur; GGUF model inference yapilmaz. Pickle disassemble edilir, hic unpickle edilmez. Template sezgisi genel enjeksiyon tespiti degildir.')

def goster(*functions):
    p=calisma_dosyasi(); print('KALICI SENTETIK AYAR:',p); print(p.read_text(encoding='utf-8'))
    out=p.parent/('deney-'+secrets.token_hex(4)); out.mkdir()
    r=deney(*functions,p,out)
    print(json.dumps(r,ensure_ascii=False,indent=1)); print('Kanit:',lab.kanit_yaz(f'guvence-{LESSON}-deney',dict(r,kabul=False)))

def bicim_ref(bicim, baslik, template):
    if bicim == 'safetensors':
        uygun = len(baslik)>=8 and 2<=int.from_bytes(baslik[:8],'little')<=100000
    elif bicim == 'gguf':
        uygun = len(baslik)>=24 and baslik[:4]==b'GGUF' and int.from_bytes(baslik[4:8],'little')==3
    else:
        uygun = False
    return uygun and '{{ user }}' in template and '[SYSTEM_OVERRIDE]' not in template


def deney(gate,document,output):
    c=ayar(document); out=Path(output); out.mkdir(parents=True,exist_ok=True); t=araclar()
    try: from safetensors.torch import save_file,load_file
    except ImportError as e:raise lab.GercekLabYok('safetensors gerekli; kurulum yapilmadi') from e
    import pickle,pickletools,struct,safetensors
    model,train=egit(c['seed'],c['adim']); state={k:v.contiguous() for k,v in model.state_dict().items()}; save_file(state,str(out/'model.safetensors'))
    # Entirely inert built-in dict: no callable/global/reduce payload.
    inert=pickle.dumps({'sentetik_marker':c['seed']},protocol=4); (out/'inert.pkl').write_bytes(inert)
    ops=[op.name for op,arg,pos in pickletools.genops(inert)]
    header=struct.pack('<4sIQQ',b'GGUF',3,0,0); (out/'header.gguf').write_bytes(header)
    safe=(out/'model.safetensors').read_bytes(); good='system: sinirli; user: {{ user }}'
    cases=[('safetensors',safe,good,True),('gguf',header,good,True),('pickle',inert,good,False),('gguf',b'BAD!'+header[4:],good,False),('gguf',header[:4]+struct.pack('<I',2)+header[8:],good,False),('safetensors',b'bad',good,False),('safetensors',(100001).to_bytes(8,'little'),good,False),('safetensors',safe,'{{ user }} [SYSTEM_OVERRIDE]',False),('gguf',header,'yalniz sistem',False)]
    rows=[]; loaded=0
    for fmt,b,template,expected in cases:
        assert bicim_ref(fmt,b,template)==expected, "Laboratuvar vaka/orakl tutarsizligi"
        decision=gate(fmt,b,template)
        if decision and fmt=='safetensors':
            # Only our independently generated known-good artifact can reach library loading.
            if b==safe and template==good:
                got=load_file(str(out/'model.safetensors'),device='cpu'); loaded+=1
                assert all(t.equal(got[k],state[k]) for k in state)
        rows.append(dict(bicim=fmt,baslik_hex=b[:24].hex(),template=template,karar=decision,beklenen=expected))
    return paket(dict(egitim=train,safetensors=safetensors.__version__,dosya_sha256=sha(out/'model.safetensors'),pickle_opcodes=ops,pickle_yuklendi=False,gercek_tensor_yuklemeleri=loaded,vakalar=rows,kontroller=dict(kapi=all(type(r['karar']) is bool and r['karar']==r['beklenen'] for r in rows),gercek_safetensors=loaded==1,inert_pickle=not any(x in ops for x in ['GLOBAL','STACK_GLOBAL','REDUCE']))))
