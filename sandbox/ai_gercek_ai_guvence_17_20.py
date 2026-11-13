"""Exclusive G17-20 CPU privacy lab. Synthetic inputs, actual autograd; no downloads."""
import copy, hashlib, json, math, secrets, tempfile
from pathlib import Path
from engine.progress import data_dir
from sandbox import ai_gercek_lab as lab
ROOT=Path(__file__).resolve().parents[1]

def calisma_dosyasi(n):
    base=Path(data_dir())
    if not base.is_absolute(): base=ROOT/base
    p=base/'calisma'/f'ai-guvence-{n}'/'ayarlar.json'
    p.parent.mkdir(parents=True,exist_ok=True)
    try:
        with p.open('x',encoding='utf-8') as f:
            f.write((ROOT/'web/data'/f'ai-guvence-{n}-ayarlar.txt').read_text(encoding='utf-8'))
    except FileExistsError: pass
    return p

def config(path):
    c=json.loads(Path(path).read_text(encoding='utf-8'))
    if set(c)!={'seed','ornek','sigma'}: raise ValueError('seed/ornek/sigma alanları gerekli')
    if type(c['seed']) is not int or not 0<=c['seed']<2**30: raise ValueError('seed:0..2**30-1')
    if type(c['ornek']) is not int or not 8<=c['ornek']<=32: raise ValueError('ornek:8..32')
    if type(c['sigma']) not in (int,float) or not math.isfinite(c['sigma']) or not 0.5<=c['sigma']<=8: raise ValueError('sigma:0.5..8')
    return c

def torch_al():
    try: import torch
    except ImportError as e: raise lab.GercekLabYok('Gerçek CPU autograd için mevcut .ai-venv torch gerekli') from e
    torch.set_num_threads(1)
    return torch

def auc(scores,labels):
    p=[s for s,y in zip(scores,labels) if y];q=[s for s,y in zip(scores,labels) if not y]
    return sum((a>b)+.5*(a==b) for a in p for b in q)/(len(p)*len(q))

def train(seed,n,epochs,sigma=None,clip_fn=None,budget_fn=None):
    t=torch_al();t.manual_seed(seed)
    x=t.randn(2*n,12);y=t.randint(0,2,(2*n,))
    net=t.nn.Sequential(t.nn.Linear(12,24),t.nn.Tanh(),t.nn.Linear(24,2))
    opt=t.optim.SGD(net.parameters(),lr=.35);losses=[];trace=[]
    params=list(net.parameters());C=1.;sensitivity=2*C/n
    for epoch in range(epochs):
        opt.zero_grad()
        if sigma is None:
            loss=t.nn.functional.cross_entropy(net(x[:n]),y[:n]);loss.backward()
        else:
            accum=[t.zeros_like(p) for p in params];norms=[];clippednorms=[]
            for j in range(n):
                loss=t.nn.functional.cross_entropy(net(x[j:j+1]),y[j:j+1])
                grads=t.autograd.grad(loss,params)
                flat=t.cat([g.flatten() for g in grads]);norm=float(flat.norm());norms.append(norm)
                expected=flat*min(1.,C/(norm+1e-12))
                clipped=t.tensor(clip_fn(flat.tolist(),C),dtype=flat.dtype)
                if clipped.shape!=flat.shape or not t.isfinite(clipped).all() or not t.allclose(clipped,expected,atol=1e-6,rtol=1e-5): raise ValueError('Örnek başına kırpma bağımsız autograd ile uyuşmadı')
                clippednorms.append(float(clipped.norm()))
                offset=0
                for a,p in zip(accum,params):
                    a.add_(clipped[offset:offset+p.numel()].reshape(p.shape));offset+=p.numel()
            noise_norm=0.
            for p,a in zip(params,accum):
                noise=t.randn_like(p)*(sigma*sensitivity);noise_norm+=float(noise.square().sum());p.grad=a/n+noise
            eps=budget_fn(epoch+1,sigma,1e-5)
            ref=(epoch+1)/(2*sigma*sigma);ref=ref+2*math.sqrt(ref*math.log(1e5))
            if not isinstance(eps,(int,float)) or not math.isclose(eps,ref,abs_tol=1e-8):raise ValueError('Bütçe hesabı yanlış')
            trace.append(dict(adim=epoch+1,epsilon=eps,delta=1e-5,max_ham_norm=max(norms),max_kirpilmis_norm=max(clippednorms),kirpma_siniri=C,noise_l2=math.sqrt(noise_norm)))
        opt.step()
        with t.no_grad(): losses.append(float(t.nn.functional.cross_entropy(net(x[:n]),y[:n])) )
    with t.no_grad():
        logits=net(x);probs=logits.softmax(-1).gather(1,y[:,None]).squeeze(1).tolist();correct=(logits.argmax(-1)==y).tolist()
    weightbytes=b''.join(p.detach().numpy().tobytes() for p in params)
    return dict(seed=seed,n=n,epochs=epochs,sigma=sigma,x=x.tolist(),y=y.tolist(),logits=logits.tolist(),skor=probs,uye=[i<n for i in range(2*n)],egitim_dogruluk=sum(correct[:n])/n,test_dogruluk=sum(correct[n:])/n,loss=losses,dp_iz=trace,agirlik_sha256=hashlib.sha256(weightbytes).hexdigest(),parametre=sum(p.numel() for p in params),torch=t.__version__,cihaz='cpu')

def ref17(scores,labels,threshold):
    tp=sum(y and s>=threshold for s,y in zip(scores,labels));fp=sum(not y and s>=threshold for s,y in zip(scores,labels));p=sum(labels);n=len(labels)-p
    return dict(auc=round(auc(scores,labels),6),tpr=round(tp/p,6),fpr=round(fp/n,6),avantaj=round(tp/p-fp/n,6))

def ref18(train_acc,test_acc,a):
    return dict(acik=round(train_acc-test_acc,6),auc=round(a,6),risk=train_acc-test_acc>=.1 and a>=.65)

def ref19clip(g,c):
    norm=math.sqrt(sum(v*v for v in g));return [v*min(1.,c/(norm+1e-12)) for v in g]

def ref19budget(steps,sigma,delta):
    rho=steps/(2*sigma*sigma);return rho+2*math.sqrt(rho*math.log(1/delta))

def ref20(a,b,limit,drop,maxloss):
    return dict(auc_azalisi=round(a['auc']-b['auc'],6),dogruluk_kaybi=round(a['dogruluk']-b['dogruluk'],6),destekli=b['auc']<=limit and a['auc']-b['auc']>=drop and a['dogruluk']-b['dogruluk']<=maxloss,bicimsel_garanti=False)

def sozlesme(n,fn,extra=None):
    try:
        import random
        rng=random.Random(771+n)
        for k in range(8):
            if n==17:
                s=[rng.choice([.1,.5,.5,.9]) for _ in range(10)];y=[True]*4+[False]*6;th=rng.choice([0.,.5,.9,1.]);args=(s,y,th);ref=ref17(*args)
            elif n==18:
                args=([.8,.9,.7,.6][k%4],[.7,.5,.8,.6][k%4],[.65,.9,.4,.8][k%4]);ref=ref18(*args)
            elif n==19:
                args=([3.,4.,0.] if k%2 else [0.,0.,0.],.5+k/3);ref=ref19clip(*args)
            else:
                args=({'auc':.95-k*.02,'dogruluk':.85},{'auc':.5+k*.03,'dogruluk':.85-k*.03},.65,.1,.1);ref=ref20(*args)
            passed=copy.deepcopy(args);before=copy.deepcopy(passed);got=fn(*passed)
            if n==19:
                if len(got)!=len(ref) or any(not math.isclose(a,b,abs_tol=1e-8) for a,b in zip(got,ref)):return False
                e=extra(k+1,.75+k/2,1e-5)
                if not math.isclose(e,ref19budget(k+1,.75+k/2,1e-5),abs_tol=1e-8):return False
            elif got!=ref:return False
            if passed!=before:return False
        return True
    except Exception:return False

def deney(n,fn,extra=None,path=None):
    c=config(path or calisma_dosyasi(n));runs=[];results=[];controls={}
    clip=fn if n==19 else ref19clip;budget=extra if n==19 else ref19budget
    for repeat in range(2):
        seed=c['seed']+repeat*17;count=c['ornek']
        if n==17:
            shadow=train(seed+500,count,35);target=train(seed,count,35)
            candidates=sorted(set(shadow['skor']+[0.,1.]))
            threshold=max(candidates,key=lambda v:(ref17(shadow['skor'],shadow['uye'],v)['avantaj'],-v))
            measured=fn(target['skor'][:],target['uye'][:],threshold)
            controls[f'olcum-{repeat}']=measured==ref17(target['skor'],target['uye'],threshold)
            runs.append(dict(shadow=shadow,target=target,esik=threshold,esik_kaynagi='ayri_shadow;hedef_uyeligi_esik_secimine_girmez'));results.append(measured)
        elif n==18:
            for epochs in (3,35):
                model=train(seed,count,epochs);a=auc(model['skor'],model['uye']);measured=fn(model['egitim_dogruluk'],model['test_dogruluk'],a)
                controls[f'acik-{repeat}-{epochs}']=measured==ref18(model['egitim_dogruluk'],model['test_dogruluk'],a);runs.append(model);results.append(measured)
        elif n==19:
            for sigma in (c['sigma'],2*c['sigma']):
                model=train(seed,count,8,sigma,clip,budget);runs.append(model);results.append(dict(sigma=sigma,epsilon=model['dp_iz'][-1]['epsilon'],test_dogruluk=model['test_dogruluk']))
            controls[f'butce-{repeat}']=results[-1]['epsilon']<results[-2]['epsilon']
        else:
            standard=train(seed,count,35);private=train(seed,count,8,c['sigma'],clip,budget)
            a=dict(auc=auc(standard['skor'],standard['uye']),dogruluk=standard['test_dogruluk']);b=dict(auc=auc(private['skor'],private['uye']),dogruluk=private['test_dogruluk'])
            measured=fn(copy.deepcopy(a),copy.deepcopy(b),.65,.1,.1);controls[f'iddia-{repeat}']=measured==ref20(a,b,.65,.1,.1)
            runs.append(dict(standart=standard,dp_egitim=private,standart_olcum=a,dp_olcum=b));results.append(measured)
    controls['ogrenci_sozlesmesi']=sozlesme(n,fn,extra)
    return dict(kaynak='gercek',kabul=all(controls.values()),ortam=dict(torch=torch_al().__version__,model='Yerel 12-24-2 MLP / SGD / CPU'),kaynaklar=['https://arxiv.org/abs/1605.02065','https://arxiv.org/abs/1702.07476'],veri_kokeni='Sentetik torch.randn özellikler ve randint etiketler; her çağrıda gerçek autograd eğitimi',ayarlar=c,deneyler=runs,ozet=results,kontroller=controls,sinir='Küçük sentetik CPU deneyi. Üyelik başarısı veya risk azalışı PASS koşulu değildir. Düşük AUC DP kanıtlamaz. DP: sabit n, replace-one komşuluk, tam batch örnek-başı L2 C=1, sigma*(2C/n) Gaussian; rho=T/(2sigma²), epsilon=rho+2sqrt(rho log(1/delta)), delta=1e-5; altörnekleme kazancı yok. Açık seed ve ayrıntılı ham iz yalnız öğretim içindir; özel veriyle güvenli yayın garantisi yok. Epsilon yalnız ağırlık mekanizmasına aittir, ham skor/iz yayınlarına değil. Kontrol geçici kanıtı koşucuya taşır, Run kalıcı öğrenci ayarını korur.')

def goster(n,fn,extra=None):
    path=calisma_dosyasi(n);print('Kalıcı öğrenci dosyası:',path);print(path.read_text(encoding='utf-8'))
    r=deney(n,fn,extra,path);r['kabul']=False
    print('Ölçülen sonuç:',r['ozet']);print('Kanıt:',lab.kanit_yaz(f'guvence-{n}-cpu',r));print(r['sinir'])
