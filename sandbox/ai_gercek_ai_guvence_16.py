"""G16: actual autograd-trained synthetic classifiers, independent shadow threshold."""
import copy,hashlib,json,secrets,time,platform,random
from pathlib import Path
from engine.progress import data_dir
from sandbox import ai_gercek_lab as lab
ROOT=Path(__file__).resolve().parents[1];ORNEK=ROOT/'web/data/ai-guvence-16-gizlilik.txt'
def calisma_dosyasi():
    r=Path(data_dir());r=r if r.is_absolute() else ROOT/r;p=r/'calisma/ai-guvence-16/gizlilik.json';p.parent.mkdir(parents=True,exist_ok=True)
    if not p.exists():
        try:
            with p.open('x',encoding='utf-8') as f:f.write(ORNEK.read_text(encoding='utf-8'))
        except FileExistsError:pass
    return p

def olcu_ref(rows):
    tp=sum(v['uye'] and v['tahmin_uye'] for v in rows);fp=sum(not v['uye'] and v['tahmin_uye'] for v in rows);tn=sum(not v['uye'] and not v['tahmin_uye'] for v in rows);fn=sum(v['uye'] and not v['tahmin_uye'] for v in rows)
    return dict(toplam=len(rows),tp=tp,fp=fp,tn=tn,fn=fn,dogruluk=round((tp+tn)/len(rows),6),avantaj=round(tp/(tp+fn)-fp/(fp+tn),6))
def rapor_ref(rows,threshold):
    grouped=[]
    for name in sorted({v['deney'] for v in rows}):
        rs=[v for v in rows if v['deney']==name];a=sum(v['dogruluk'] for v in rs)/len(rs);b=sum(v['taban_dogrulugu'] for v in rs)/len(rs);adv=sum(v['avantaj'] for v in rs)/len(rs);grouped.append(dict(deney=name,dogruluk=round(a,6),taban_dogrulugu=round(b,6),avantaj=round(adv,6),kanit=adv>=threshold and a>b))
    yes=[v for v in grouped if v['kanit']];chosen=min(yes,key=lambda v:(-sum(r['avantaj'] for r in rows if r['deney']==v['deney'])/sum(r['deney']==v['deney'] for r in rows),-sum(r['dogruluk'] for r in rows if r['deney']==v['deney'])/sum(r['deney']==v['deney'] for r in rows),v['deney']))['deney'] if yes else None
    return dict(satirlar=grouped,secilen=chosen)
def _train(seed,n,root):
    try:import torch
    except ImportError as e:raise lab.GercekLabYok('Gerçek autograd için mevcut torch ortamı gerekli') from e
    torch.set_num_threads(2);torch.manual_seed(seed);x=torch.randn(2*n,24);y=torch.randint(0,2,(2*n,));net=torch.nn.Sequential(torch.nn.Linear(24,64),torch.nn.Tanh(),torch.nn.Linear(64,2));optim=torch.optim.Adam(net.parameters(),lr=.025);curve=[];start=time.perf_counter()
    for i in range(100):
        optim.zero_grad();loss=torch.nn.functional.cross_entropy(net(x[:n]),y[:n]);loss.backward();optim.step()
        if i in (0,9,49,99):curve.append(dict(adim=i+1,loss=float(loss.detach())))
    net.eval()
    with torch.no_grad():logits=net(x);prob=logits.softmax(-1).gather(1,y[:,None]).squeeze(1);pred=logits.argmax(-1)
    root=Path(root);root.mkdir(parents=True,exist_ok=True);p=root/'state.pt';torch.save(net.state_dict(),p)
    scores=prob.tolist();return dict(seed=seed,n=n,x=x.tolist(),y=y.tolist(),logitler=logits.tolist(),guven=scores,egitim_loss=curve,egitim_sure_ms=round((time.perf_counter()-start)*1000),siniflandirma_egitim=float((pred[:n]==y[:n]).float().mean()),siniflandirma_dis=float((pred[n:]==y[n:]).float().mean()),parametre=sum(v.numel() for v in net.parameters()),agirlik_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),agirlik_dosyasi=str(p),torch=torch.__version__,cihaz='cpu')
def deney(validate,metric,report,document,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True);config=json.loads(Path(document).read_text(encoding='utf-8'))
    if set(config)!={'seed','ornek'} or type(config['seed']) is not int or not 0<=config['seed']<2**31 or type(config['ornek']) is not int or not 16<=config['ornek']<=64:raise ValueError('seed tamsayı/ornek16..64 olmalı')
    threat=dict(id='yerel-uyelik',varliklar=['egitim_verisi','model_parametreleri'],cikti_kanallari=['olasilik'],saldirgan_bilgisi=['mimari','ornek_veri','sorgu_erisimi']);expected={k:sorted(v) if isinstance(v,list) else v for k,v in threat.items()};got=validate(copy.deepcopy(threat));runs=[];aggregates=[];n=config['ornek'];checks=[]
    for i in range(3):
        shadow=_train(config['seed']+i*4,n,output/('shadow-'+str(i)));target=_train(config['seed']+i*4+1,n,output/('target-'+str(i)))
        # Only shadow labels choose threshold; target membership is never used to tune it.
        candidates=sorted(set(shadow['guven']+[0.,1.]));threshold=max(candidates,key=lambda t:(sum(s>=t for s in shadow['guven'][:n])/n-sum(s>=t for s in shadow['guven'][n:])/n,-t))
        ids=list(range(2*n));random.Random(config['seed']+i).shuffle(ids);rows=[dict(id='r'+str(i)+'-'+str(j),uye=j<n,tahmin_uye=target['guven'][j]>=threshold) for j in ids];measured=metric(copy.deepcopy(rows));reference=olcu_ref(rows);checks.append(measured==reference)
        aggregates.append(dict(deney='shadow-esikli',dogruluk=measured['dogruluk'],taban_dogrulugu=.5,avantaj=measured['avantaj']))
        runs.append(dict(tekrar=i+1,esik_kaynagi='yalniz-ayri-shadow-egitim-dis-ornekler',esik=threshold,shadow=shadow,target=target,uyelik_kayitlari=rows,ogrenci_olcumu=measured))
    result=report(copy.deepcopy(aggregates),.1);controls=dict(tehdit_gercek_erisimi_tanimli=got==expected,gercek_uyelik_olcumu=all(checks),taban_ve_avantaj_raporu=result==rapor_ref(aggregates,.1),gercek_autograd_tam=all(len(v['target']['egitim_loss'])==4 and v['target']['parametre']>0 for v in runs))
    return dict(kaynak='gercek',ortam=dict(python=platform.python_version(),torch=runs[0]['target']['torch'],cihaz='cpu',makine=lab.cihaz()),veri_kokeni='sentetik rastgeleozellik/etiket;gercek autograd egitimi ve modelolasılıkları',ayarlar=dict(config,tekrar=3,epochs=100,lr=.025,esik_kanit=.1),tehdit_modeli=got,deneyler=runs,rapor_girdisi=aggregates,ozet=result,kontroller=controls,sinir='CPUdaki küçük sentetik sınıflandırıcıdır,sohbetmodeli gizliliği veya genel risk garantisi değildir. SaldırıavantajıpozitifolmakPASSşartıdeğil. Testtempweights temizlenir,hash/skor/logit/egitimizi JSONdakalır;Run klasöründeki gerçek ağırlıklar korunur.')
def goster(validate,metric,report):
    p=calisma_dosyasi();print('KALICI SENTETİK AYAR:',p);print(p.read_text(encoding='utf-8'));r=deney(validate,metric,report,p,p.parent/('deney-'+secrets.token_hex(4)))
    for v in r['deneyler']:print('Tekrar',v['tekrar'],'shadow esik',v['esik'],'gercek olcum',v['ogrenci_olcumu'])
    print('Rapor:',r['ozet']);print('Kontroller:',r['kontroller']);print('Kanıt:',lab.kanit_yaz('guvence-16-gizlilik',dict(r,kabul=False)))
