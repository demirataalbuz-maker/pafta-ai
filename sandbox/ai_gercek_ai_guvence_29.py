"""Lesson-local real CPU experiment; synthetic data, no downloads/GPU."""
import copy, hashlib, json, os, secrets, time, platform
from pathlib import Path
from sandbox import ai_gercek_lab as lab
ROOT=Path(__file__).resolve().parents[1]
LESSON=29

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

def redact_ref(text,canary):return text.replace(canary,'[MASKELI]')
def manifest_ref(files):return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}

def deney(redact,manifest,document,output):
    import torch,zipfile
    c=config(document);output=Path(output);model,x,y,info=train(c['seed'],output/'model')
    z=attack_ref(model,x[144:],y[144:],c['eps'])
    with torch.no_grad():before=model(x[144:]).argmax(-1);after=model(z).argmax(-1)
    canary='PAFTA-SENTETIK-'+secrets.token_hex(12)
    raw=dict(deney='yerel-FGSM',canary=canary,tekrar=canary,temiz=before.tolist(),bozuk=after.tolist(),etiket=y[144:].tolist(),model_sha256=info['agirlik_sha256'])
    source=json.dumps(raw,ensure_ascii=False);safe=redact(source,canary);expected=redact_ref(source,canary)
    # A second marker prevents implementations hardcoding the visible example.
    checks=dict(maskeli_gercek_cikti=safe==expected,tekrar_sir_yok=redact(canary+' '+canary,canary)=='[MASKELI] [MASKELI]',temiz_metin_korunur=redact('sentetik rapor',canary)=='sentetik rapor')
    private=output/'ozel';private.mkdir(exist_ok=True);(private/'ham.json').write_text(source,encoding='utf-8')
    package=output/'bildirim';package.mkdir(exist_ok=True);(package/'kanit.json').write_text(safe,encoding='utf-8')
    (package/'RAPOR.md').write_text('Yerel sentetik FGSM yontem bulgusu.\nModel: '+info['agirlik_sha256']+'\nEtkilenen kapsam: yalniz bu sentetik CPU model.\nYeniden uretim: ayar.json seed/eps, 70 Adam epoch, test144:192.\nKisit: sohbet modeli/CVE/gercek urun zafiyeti iddiasi yok.\nIletisim: yerel taslak; GONDERILMEDI.\nOnlem: ayri testte adversarial training/abstention yeniden degerlendirilmeli.\n',encoding='utf-8')
    (package/'ayar.json').write_text(json.dumps(c),encoding='utf-8')
    (package/'model-kaydi.json').write_text(json.dumps(info),encoding='utf-8')
    files=list(package.iterdir());got=manifest(list(files));gold=manifest_ref(files);checks['dosya_hashlari']=got==gold
    # The student's manifest is used by the real archive's integrity verifier.
    (package/'manifest.json').write_text(json.dumps(got),encoding='utf-8')
    archive=output/'bildirim.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as f:
        for p in package.iterdir():f.write(p,p.name)
    with zipfile.ZipFile(archive) as f:
        checks['arsiv_butunlugu']=all(hashlib.sha256(f.read(name)).hexdigest()==digest for name,digest in got.items()) and set(got)==set(gold)
        checks['arsiv_canary_yok']=all(canary.encode() not in f.read(name) for name in f.namelist())
    return evidence(dict(ayarlar=c,model=info,ozet=dict(temiz=int((before==y[144:]).sum()),bozuk=int((after==y[144:]).sum()),toplam=48,gonderildi=False,arsiv=str(archive)),manifest=got,arsiv_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),kontroller=checks))
