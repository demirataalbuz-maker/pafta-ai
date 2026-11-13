"""Lesson-local real CPU experiment; synthetic data, no downloads/GPU."""
import copy, hashlib, json, os, secrets, time, platform
from pathlib import Path
from sandbox import ai_gercek_lab as lab
ROOT=Path(__file__).resolve().parents[1]
LESSON=26

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

def deney(fgsm,ozet,document,output):
    import torch
    c=config(document);runs=[];checks=[];measure=[]
    for seed in (c['seed'],c['seed']+11):
        for name,lr in [('referans',.04),('replikasyon',.04),('sapma',.009)]:
            model,x,y,info=train(seed,Path(output)/(str(seed)+'-'+name),lr)
            xx=x[144:];yy=y[144:];z=fgsm(model,xx.clone(),yy.clone(),c['eps']);gold=attack_ref(model,xx,yy,c['eps'])
            valid=isinstance(z,torch.Tensor) and z.shape==xx.shape and torch.isfinite(z).all().item() and torch.allclose(z,gold,atol=1e-6)
            checks.append(bool(valid))
            with torch.no_grad():
                clean=model(xx).argmax(-1);adv=model(z.detach()).argmax(-1)
            row=dict(kol=name,seed=seed,temiz=int((clean==yy).sum()),bozuk=int((adv==yy).sum()),toplam=len(yy),lr=lr)
            measure.append(row);runs.append(dict(model=info,olcum=row,bozuk_x=z.detach().tolist(),temiz_tahmin=clean.tolist(),bozuk_tahmin=adv.tolist()))
    got=ozet(copy.deepcopy(measure));expected=ozet_ref(measure)
    exact=all(runs[i]['model']['logitler']==runs[i+1]['model']['logitler'] for i in (0,3))
    return evidence(dict(ayarlar=c,deneyler=runs,olcumler=measure,ozet=got,kontroller=dict(gercek_fgsm=all(checks),gercek_sapma_raporu=got==expected,ayni_tohum_tekrar=exact),replikasyon_kapsami='Goodfellow2015 FGSM yonteminin kucuk sentetik replikasyonu; MNIST/maxout makale skorunun replikasyonu DEGIL',kaynak_makale='https://arxiv.org/abs/1412.6572v3'))

def ozet_ref(rows):
    result=[]
    for seed in sorted({r['seed'] for r in rows}):
        base=next(r for r in rows if r['seed']==seed and r['kol']=='referans')
        for r in rows:
            if r['seed']==seed:result.append(dict(seed=seed,kol=r['kol'],temiz=round(r['temiz']/r['toplam'],6),bozuk=round(r['bozuk']/r['toplam'],6),fark=round(r['bozuk']/r['toplam']-base['bozuk']/base['toplam'],6),degisen=['lr'] if r['lr']!=base['lr'] else []))
    return result
