"""Lesson-local real CPU experiment; synthetic data, no downloads/GPU."""
import copy, hashlib, json, os, secrets, time, platform
from pathlib import Path
from sandbox import ai_gercek_lab as lab
ROOT=Path(__file__).resolve().parents[1]
LESSON=30

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

def policy_ref(confidence,threshold):return confidence>=threshold

def report_ref(rows):
    out={}
    for arm in ('saldiri','savunma'):
        rs=[r for r in rows if r['kol']==arm];n=len(rs)
        out[arm]=dict(n=n,dogruluk=round(sum(r['dogru'] for r in rs)/n,6),kapsama=round(sum(r['izin'] for r in rs)/n,6),zararli_etki=sum(r['izin'] and not r['dogru'] for r in rs),izinli_dogru=sum(r['izin'] and r['dogru'] for r in rs))
    return out

def deney(policy,report,document,output):
    import torch,zipfile
    c=config(document);output=Path(output);output.mkdir(parents=True,exist_ok=True);rows=[];runs=[];checks=[];effects=[]
    for repeat in (1,2,3):
        model,x,y,info=train(c['seed']+repeat,output/('model-'+str(repeat)))
        z=attack_ref(model,x[144:],y[144:],c['eps'])
        with torch.no_grad():p=model(z).softmax(-1);confidence,pred=p.max(-1)
        folder=output/('etki-'+str(repeat));folder.mkdir(exist_ok=True)
        for arm in ('saldiri','savunma'):
            for j,(conf,prediction,label) in enumerate(zip(confidence.tolist(),pred.tolist(),y[144:].tolist())):
                allow=True if arm=='saldiri' else policy(conf,.8)
                checks.append(type(allow) is bool and (arm=='saldiri' or allow==policy_ref(conf,.8)))
                row=dict(kol=arm,tekrar=repeat,id=j,guven=conf,dogru=prediction==label,izin=allow);rows.append(row)
                # Real local effect only when the student's gate permits a prediction.
                path=folder/(arm+'-'+str(j)+'.json')
                if allow:path.write_text(json.dumps(dict(tahmin=prediction,gercek=label)),encoding='utf-8');effects.append(str(path))
                checks.append(path.exists()==allow)
        runs.append(info)
    controls=[policy(a,b)==policy_ref(a,b) and type(policy(a,b)) is bool for a,b in [(0.,0.),(.79,.8),(.8,.8),(1.,.8),(.4,.3),(.99,1.)]]
    summary=report(copy.deepcopy(rows));expected=report_ref(rows)
    publish=output/'yayin';publish.mkdir(exist_ok=True)
    for name,value in [('ayar.json',c),('olcum.json',rows),('rapor.json',summary),('model-kayitlari.json',runs)]: (publish/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    (publish/'SINIRLAR.md').write_text('Uc seed, eslesmis48ornek/kol, gercek FGSM ve CPU autograd. Veri sentetiktir. Abstention maliyeti kapsama ile raporlanir; guven esigi genel guvenlik garantisi degildir. Gercek urun veya sohbet modeli sonucu degil. Sonucun guvenli cikmasi yayin sarti degildir. Agda yayimlanmadi.',encoding='utf-8')
    (publish/'YENIDEN-URETIM.md').write_text('Proje kokunde .ai-venv ile sandbox.ai_gercek_ai_guvence_30.deney(policy,report,ayar,output). Model:4-12-2 Tanh;Adam lr=.04;70epoch;bolumler0:96/96:144/144:192;seed=ayar.seed+1,+2,+3;FGSM eps=ayar.eps;esik=.8. Fonksiyon sozlesmeleri ai-guvence-30 son gorevinde. Kod SHA256: '+hashlib.sha256(Path(__file__).read_bytes()).hexdigest()+'; torch surumu/ham logit/egitim izi model-kayitlari.json icinde.',encoding='utf-8')
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in publish.iterdir()}
    (publish/'manifest.json').write_text(json.dumps(hashes),encoding='utf-8')
    archive=output/'purple.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as f:
        for p in publish.iterdir():f.write(p,p.name)
    with zipfile.ZipFile(archive) as f:archive_ok=all(hashlib.sha256(f.read(n)).hexdigest()==h for n,h in hashes.items())
    return evidence(dict(ayarlar=c,modeller=runs,olcumler=rows,ozet=summary,gercek_etkiler=effects,yayin_arsivi=str(archive),arsiv_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),kontroller=dict(gercek_politika_ve_etki=all(checks),sinir_esikleri=all(controls),kapsama_ve_yanlis_etki=summary==expected,arsiv_butunlugu=archive_ok)))
