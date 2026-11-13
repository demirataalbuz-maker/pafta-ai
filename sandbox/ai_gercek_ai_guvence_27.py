"""Lesson-local real CPU experiment; synthetic data, no downloads/GPU."""
import copy, hashlib, json, os, secrets, time, platform
from pathlib import Path
from sandbox import ai_gercek_lab as lab
ROOT=Path(__file__).resolve().parents[1]
LESSON=27

def calisma_dosyasi():
    # Resolve relative PAFTA_DATA against project, never the runner temp cwd.
    base=Path(os.environ.get('PAFTA_DATA') or Path(os.environ.get('LOCALAPPDATA',str(ROOT)))/'Pafta')
    base=base if base.is_absolute() else ROOT/base
    p=base/'calisma'/('ai-guvence-'+str(LESSON))/'ayar.json'
    p.parent.mkdir(parents=True,exist_ok=True)
    if not p.exists():
        try:
            with p.open('x',encoding='utf-8') as f:f.write((ROOT/('web/data/ai-guvence-'+str(LESSON)+'-deney.txt')).read_text(encoding='utf-8'))
        except FileExistsError:pass
    return p

def config(document):
    c=json.loads(Path(document).read_text(encoding='utf-8'))
    if set(c)!={'seed','eps'} or type(c['seed']) is not int or not 0<=c['seed']<1000000 or type(c['eps']) not in (int,float) or not 0<c['eps']<=.4:raise ValueError('seed0..999999/eps0..0.4')
    return c

def train(seed,root,lr=.04,width=12):
    try:import torch
    except ImportError as e:raise lab.GercekLabYok('Gercek torch/autograd bagimliligi yok; PASS verilmez') from e
    torch.set_num_threads(1);torch.manual_seed(seed)
    x=torch.rand(192,4);y=((x[:,0]-.5)*(x[:,1]-.5)+.15*(x[:,2]-.5)>0).long()
    # Independent train/calibration/test partitions, model never sees later labels.
    model=torch.nn.Sequential(torch.nn.Linear(4,width),torch.nn.Tanh(),torch.nn.Linear(width,2))
    optim=torch.optim.Adam(model.parameters(),lr=lr);curve=[];start=time.perf_counter()
    for epoch in range(70):
        optim.zero_grad();loss=torch.nn.functional.cross_entropy(model(x[:96]),y[:96]);loss.backward();optim.step()
        if epoch in (0,9,34,69):curve.append(float(loss.detach()))
    model.eval();root=Path(root);root.mkdir(parents=True,exist_ok=True);p=root/'weights.pt';torch.save(model.state_dict(),p)
    with torch.no_grad():logits=model(x)
    info=dict(seed=seed,lr=lr,width=width,epochs=70,cihaz='cpu',torch=torch.__version__,parametre=sum(v.numel() for v in model.parameters()),loss=curve,egitim_ms=round((time.perf_counter()-start)*1000,3),agirlik_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),agirlik_dosyasi=str(p),x=x.tolist(),y=y.tolist(),logitler=logits.tolist(),bolumler={'egitim':[0,96],'kalibrasyon':[96,144],'test':[144,192]})
    return model,x,y,info

def attack_ref(model,x,y,eps):
    import torch
    z=x.detach().clone().requires_grad_(True)
    grad=torch.autograd.grad(torch.nn.functional.cross_entropy(model(z),y),z)[0]
    return (z.detach()+eps*grad.sign()).clamp(0,1)

def evidence(r):
    r.update(kaynak='gercek',ortam=dict(model='tiny-4-12-2-CPU',python=platform.python_version(),cihaz='cpu'),veri_kokeni='Sentetik ozellik/etiket; canli autograd egitimi ve olcum',sinir='Kucuk CPU siniflandiricisi; sohbet modeli veya genel guvenlik garantisi degildir. Saldiri basarisi PASS sarti degildir.')
    return r

def goster(*functions):
    p=calisma_dosyasi();print('KALICI DUZENLENEBILIR SENTETIK AYAR:',p);print(p.read_text(encoding='utf-8'))
    r=deney(*functions,p,p.parent/('deney-'+secrets.token_hex(4)))
    print(json.dumps(r.get('ozet'),ensure_ascii=False,indent=2));print('Kontroller:',r['kontroller'])
    print('Kanit:',lab.kanit_yaz('guvence-'+str(LESSON),dict(r,kabul=False)))

def temperature_ref(logits,labels,grid):
    import torch
    return min(grid,key=lambda t:float(torch.nn.functional.cross_entropy(logits/t,labels)))

def score_ref(logits,labels,t):
    import torch
    p=(logits/t).softmax(-1);confidence,pred=p.max(-1);correct=(pred==labels).float();ece=0.
    for a,b in [(0.,.5),(.5,.7),(.7,.9),(.9,1.)]:
        mask=(confidence>a)&(confidence<=b)
        if mask.any():ece+=float(mask.float().mean())*abs(float(confidence[mask].mean()-correct[mask].mean()))
    return dict(n=len(labels),nll=round(float(torch.nn.functional.cross_entropy(logits/t,labels)),6),dogruluk=round(float(correct.mean()),6),ece=round(ece,6))

def deney(calibrate,score,document,output):
    import torch
    c=config(document);runs=[];checks=[]
    for seed in (c['seed'],c['seed']+13):
        model,x,y,info=train(seed,Path(output)/str(seed))
        with torch.no_grad():logits=model(x)*2.7
        grid=[.5,1.,1.5,2.,3.,5.];t=calibrate(logits[96:144].clone(),y[96:144].clone(),list(grid));gold=temperature_ref(logits[96:144],y[96:144],grid)
        checks.append(t==gold)
        scores=[]
        for temp in (1.,t):
            got=score(logits[144:].clone(),y[144:].clone(),temp);checks.append(got==score_ref(logits[144:],y[144:],temp));scores.append(got)
        runs.append(dict(model=info,carpan=2.7,grid=grid,secilen_sicaklik=t,secim_bolumu='yalniz-kalibrasyon-96:144',test_skorlari=scores,olculen_logitler=logits.tolist()))
    # Boundary controls test the evaluator separately from trained model results.
    a=torch.tensor([[0.,0.],[20.,-20.],[-.3,.3],[1.,-1.]]);b=torch.tensor([0,1,0,0])
    controls=[score(a,b,t)==score_ref(a,b,t) for t in (.5,1.,3.)]
    return evidence(dict(ayarlar=c,deneyler=runs,ozet=[r['test_skorlari'] for r in runs],kontroller=dict(kalibrasyon_ve_test_ayri=all(checks),sinir_kalibrasyonlari=all(controls)),kaynak_makale='https://proceedings.mlr.press/v70/guo17a.html'))
