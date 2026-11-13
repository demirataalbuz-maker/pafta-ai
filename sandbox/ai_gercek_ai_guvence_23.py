"""Lesson-specific real CPU/file experiment; synthetic inputs, no network."""
import copy, hashlib, json, secrets, platform, os
from pathlib import Path
from engine.progress import data_dir
from sandbox import ai_gercek_lab as lab
ROOT=Path(__file__).resolve().parents[1]
LESSON=23

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
                sinir='Gercek autograd ile egitilen kucuk ikili siniflandirici ve simetrik fake-quant/dequant agirliklari kullanilir; GGUF/LLM veya hiz/bellek kazanci iddiasi degildir. Regresyonun pozitif olmasi kabul sarti degildir.')

def goster(*functions):
    p=calisma_dosyasi(); print('KALICI SENTETIK AYAR:',p); print(p.read_text(encoding='utf-8'))
    out=p.parent/('deney-'+secrets.token_hex(4)); out.mkdir()
    r=deney(*functions,p,out)
    print(json.dumps(r,ensure_ascii=False,indent=1)); print('Kanit:',lab.kanit_yaz(f'guvence-{LESSON}-deney',dict(r,kabul=False)))

def nicem_ref(w, bit):
    t = araclar()
    q = 2**(bit-1)-1
    peak = float(w.abs().max())
    scale = peak/q
    return t.zeros_like(w) if peak == 0 else t.clamp(t.round(w/scale), -q, q)*scale


def esli_ref(eski, yeni, etiket):
    return dict(toplam=len(etiket), eski_dogru=sum(a==y for a,y in zip(eski,etiket)),
                yeni_dogru=sum(b==y for b,y in zip(yeni,etiket)),
                regresyon=sum(a==y and b!=y for a,b,y in zip(eski,yeni,etiket)))


def deney(quant,metric,document,output):
    c=ayar(document); out=Path(output); out.mkdir(parents=True,exist_ok=True); t=araclar(); model,train=egit(c['seed'],c['adim'])
    t.manual_seed(c['seed']+100); x=t.randn(256,4); x[:,3]=0; y=(x[:,0]+.6*x[:,1]>0).long().tolist()
    with t.no_grad(): base=model(x).argmax(-1).tolist()
    rows=[]; checks=[]
    for bit in (2,4,8):
        net=copy.deepcopy(model); hashes=[]
        with t.no_grad():
            for name,p in net.named_parameters():
                w=p.clone(); got=quant(w.clone(),bit)
                expected=nicem_ref(w,bit)
                valid=isinstance(got,t.Tensor) and got.shape==p.shape and t.allclose(got,expected,atol=1e-6,rtol=1e-6)
                checks.append(bool(valid)); p.copy_(got); hashes.append(dict(ad=name,max_hata=float((got-w).abs().max())))
            logits=net(x); pred=logits.argmax(-1).tolist()
        measured=metric(base,pred,y)
        expected=esli_ref(base,pred,y)
        checks.append(measured==expected); t.save(net.state_dict(),out/f'q{bit}.pt')
        rows.append(dict(bit=bit,olcum=measured,tahminler=pred,logitler=logits.tolist(),agirlik_sha256=sha(out/f'q{bit}.pt'),agirlik_hatalari=hashes))
    z=t.zeros(3); checks.append(t.equal(quant(z,4),z))
    # Explicit pairing controls separate degradation from improvements.
    for a,b,y0 in [([0,1,0],[1,1,0],[0,1,1]),([1,0],[1,1],[0,1])]:
        expected=esli_ref(a,b,y0)
        checks.append(metric(a,b,y0)==expected)
    return paket(dict(egitim=train,olcum_x=x.tolist(),etiket=y,temel_tahmin=base,deneyler=rows,kontroller=dict(gercek_nicemleme_ve_esli_olcum=all(checks))))
