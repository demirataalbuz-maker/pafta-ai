"""Real CPU autograd unlearning audit on a deliberately small synthetic identifier classifier."""
from pathlib import Path
import copy,hashlib,json,platform,shutil,uuid
import ai_lab
ROOT=Path(__file__).resolve().parents[1]
def hazirla():
    d=Path('unlearning');d.mkdir(exist_ok=True)
    for p in (ROOT/'tracks/ai-savunma/fixtures/ai-savunma-39').iterdir():
        if p.is_file() and not (d/p.name).exists():shutil.copyfile(p,d/p.name)
def ref_veri_bol(ids,forget):
    if not isinstance(ids,list) or any(not isinstance(x,str) or not x for x in ids) or len(set(ids))!=len(ids):raise ValueError('ids')
    if not isinstance(forget,list) or not forget or any(not isinstance(x,str) or x not in ids for x in forget) or len(set(forget))!=len(forget) or len(forget)==len(ids):raise ValueError('forget')
    return {'retain':[x for x in ids if x not in forget],'forget':[x for x in ids if x in forget]}

def ref_kayip_birlestir(retain_loss,forget_loss,alpha):
    import math
    for x in (retain_loss,forget_loss,alpha):
        if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x):raise ValueError('sayi')
    if retain_loss<0 or forget_loss<0 or not 0<=alpha<=1:raise ValueError('aralik')
    return retain_loss-alpha*forget_loss

def ref_posterior_raporu(rows):
    import math
    if not isinstance(rows,list) or not rows:raise ValueError('liste')
    seen=set()
    for r in rows:
        if not isinstance(r,dict) or set(r)!={'id','grup','y','full','unlearn','retrain'} or not isinstance(r['id'],str) or not r['id'] or r['id'] in seen or r['grup'] not in ('retain','forget') or type(r['y']) is not int or r['y'] not in (0,1):raise ValueError('sema')
        seen.add(r['id'])
        for name in ('full','unlearn','retrain'):
            p=r[name]
            if not isinstance(p,list) or len(p)!=2 or any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or not 0<=x<=1 for x in p) or abs(sum(p)-1)>1e-6:raise ValueError('posterior')
    out={}
    for group in ('retain','forget'):
        a=[r for r in rows if r['grup']==group]
        if not a:out[group]=None;continue
        stats={'n':len(a)}
        for name in ('full','unlearn','retrain'):
            stats[name+'_acc']=sum((0 if r[name][0]>=r[name][1] else 1)==r['y'] for r in a)/len(a)
            stats[name+'_nll']=sum(-math.log(max(r[name][r['y']],1e-12)) for r in a)/len(a)
        stats['unlearn_retrain_tv']=sum(sum(abs(x-y) for x,y in zip(r['unlearn'],r['retrain']))/2 for r in a)/len(a)
        out[group]=stats
    return out

def deney(split_fn,loss_fn,report_fn):
    try:
        import torch
        import torch.nn.functional as F
    except ImportError as e:raise ai_lab.GercekLabYok('Kurulu torch gerekli; otomatik kurulum yok') from e
    from engine.progress import data_dir
    media=Path(data_dir())/'ai-kanit-media'/'unlearning39'/uuid.uuid4().hex;media.mkdir(parents=True)
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    runs=[]
    for seed in (39,391):
        torch.manual_seed(seed)
        ids=[f'synthetic-{i}' for i in range(12)];forget=ids[8:];wanted=ref_veri_bol(ids,forget)
        split=split_fn(list(ids),list(reversed(forget)))
        if split!=wanted:raise AssertionError('retain/forget ayrımı kaynak sırasında olmalı')
        ixr=[ids.index(i) for i in split['retain']];ixf=[ids.index(i) for i in split['forget']]
        x=torch.eye(12);y=torch.tensor([0,1]*6)
        # Zero initialization makes this tiny linear baseline reproducible; it is not a pretrained LLM.
        initial=torch.nn.Linear(12,2,bias=False)
        with torch.no_grad():initial.weight.zero_()
        def sha(m):return hashlib.sha256(m.weight.detach().numpy().tobytes()).hexdigest()
        def train(m,index):
            opt=torch.optim.SGD(m.parameters(),lr=1)
            for _ in range(120):
                opt.zero_grad();loss=F.cross_entropy(m(x[index]),y[index]);loss.backward();opt.step()
            return m
        full=train(copy.deepcopy(initial),list(range(12)));retrain=train(copy.deepcopy(initial),ixr)
        unchanged=copy.deepcopy(full);unlearn=copy.deepcopy(full);opt=torch.optim.SGD(unlearn.parameters(),lr=1)
        logs=[]
        for k in range(50):
            opt.zero_grad();lr=F.cross_entropy(unlearn(x[ixr]),y[ixr]);lf=F.cross_entropy(unlearn(x[ixf]),y[ixf]);alpha=0.5
            measured=loss_fn(float(lr.detach()),float(lf.detach()),alpha)
            if abs(measured-ref_kayip_birlestir(float(lr.detach()),float(lf.detach()),alpha))>1e-8:raise AssertionError('GA/GD kayıp işareti yanlış')
            loss=lr-alpha*lf;loss.backward();norm=float(unlearn.weight.grad.norm());opt.step()
            logs.append({'step':k,'retain_loss':float(lr.detach()),'forget_loss':float(lf.detach()),'objective':float(loss.detach()),'ogrenci_hesabi':measured,'grad_norm':norm})
        with torch.no_grad():probs={n:F.softmax(m(x),dim=-1).tolist() for n,m in [('full',full),('unlearn',unlearn),('retrain',retrain),('unchanged',unchanged)]}
        rows=[{'id':i,'grup':'forget' if i in forget else 'retain','y':int(y[k]),**{n:probs[n][k] for n in ('full','unlearn','retrain')}} for k,i in enumerate(ids)]
        report=report_fn(copy.deepcopy(rows));reference=ref_posterior_raporu(rows)
        def close(a,b):
            if isinstance(a,dict):return isinstance(b,dict) and set(a)==set(b) and all(close(a[k],b[k]) for k in a)
            if a is None:return b is None
            return type(b) in (int,float) and abs(a-b)<1e-8
        if not close(reference,report):raise AssertionError('Gerçek posterior ölçümü yanlış')
        hashes={n:sha(m) for n,m in [('initial',initial),('full',full),('unlearn',unlearn),('retrain',retrain),('unchanged',unchanged)]}
        if hashes['full']!=hashes['unchanged'] or hashes['full']==hashes['unlearn'] or hashes['initial']==hashes['full'] or not all(t['grad_norm']>0 for t in logs):raise AssertionError('Gerçek ağırlık/gradient yok')
        files={}
        for n,m in [('full',full),('unlearn',unlearn),('retrain',retrain),('unchanged',unchanged)]:
            p=media/f'{seed}-{n}.pt';torch.save(m.state_dict(),p);loaded=torch.load(p,weights_only=True,map_location='cpu');assert torch.equal(loaded['weight'],m.weight.detach());files[n]={'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
        runs.append({'seed':seed,'split':split,'rows':rows,'report':report,'unchanged_posterior':probs['unchanged'],'weights_sha256':hashes,'files':files,'training_log':logs,'train_ids':{'full':ids,'retrain':split['retain']},'data':{'x':x.tolist(),'y':y.tolist()},'steps':{'full':120,'retrain':120,'unlearn':50}})
    return {'kaynak':'gercek','cihaz':{'device':'CPU','os':platform.platform(),'python':platform.python_version()},'surumler':{'torch':torch.__version__},'model':'Linear(12,2,bias=False), 24 parameters; zero init; synthetic identifier memorization','ayarlar':{'seeds':[39,391],'lr':1,'alpha':0.5,'num_threads':1,'deterministic':True},'runs':runs,'media':str(media),'sinir':'Küçük bağımsız one-hot kimlik sınıflandırıcı; pretrained LLM değil. Düşük forget accuracy silinme garantisi değildir. Sıfır init nedeniyle iki seed aynı öğrenme dinamiğini kullanır.'}

def goster(a,b,c):
    d=deney(a,b,c);print('GERÇEK torch CPU autograd; sentetik kimlik sınıflandırıcı, LLM değil')
    for r in d['runs']:print(json.dumps({'seed':r['seed'],'report':r['report']},ensure_ascii=False))
    print(ai_lab.kanit_yaz('unlearning39-run',{'kaynak':'gercek','kabul':False,'ders':'ai-savunma-39','deney':d}))
