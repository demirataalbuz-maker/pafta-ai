"""AI54: offline sklearn detector and bounded text evasion on synthetic messages."""
from pathlib import Path
import json,hashlib,math,os,platform,shutil,time
import ai_lab
ROOT=Path(__file__).resolve().parents[1]
FIX=ROOT/'tracks/ai-saldiri/fixtures/ai-saldiri-54'
def hazirla():
    d=Path('dedektor');d.mkdir(exist_ok=True)
    for p in FIX.iterdir():
        if p.is_file() and not (d/p.name).exists():shutil.copyfile(p,d/p.name)

def ref_adaylar(metin,ekler,butce):
    if not isinstance(metin,str) or not metin or not isinstance(ekler,list) or any(not isinstance(x,str) for x in ekler) or type(butce) is not int or butce<0:raise ValueError('girdi')
    out=[metin]
    for ek in ekler:
        if not ek.strip():continue
        yeni=metin+' '+ek
        if len(yeni)-len(metin)<=butce and yeni not in out:out.append(yeni)
    return out

def ref_en_az_risk(hedef,adaylar,q):
    import math
    if not isinstance(adaylar,list) or not adaylar or any(not isinstance(x,str) or not x for x in adaylar) or type(q) is not int or q<1:raise ValueError('girdi')
    rows=[]
    for text in adaylar[:q]:
        score=hedef(text)
        if isinstance(score,bool) or not isinstance(score,(int,float)) or not math.isfinite(score) or not 0<=score<=1:raise ValueError('skor')
        rows.append({'metin':text,'skor':score})
    return {'secilen':min(rows,key=lambda r:r['skor'])['metin'],'sorgular':rows}

def ref_olcum_raporu(rows):
    import math
    if not isinstance(rows,list) or not rows:raise ValueError('liste')
    ids=set()
    for r in rows:
        if not isinstance(r,dict) or set(r)!={'id','etiket','once','sonra'} or not isinstance(r['id'],str) or not r['id'] or r['id'] in ids or type(r['etiket']) is not int or r['etiket'] not in (0,1):raise ValueError('sema')
        ids.add(r['id'])
        for k in ('once','sonra'):
            v=r[k]
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<=v<=1:raise ValueError('skor')
    ph=[r for r in rows if r['etiket']==1];ctl=[r for r in rows if r['etiket']==0]
    detected=[r for r in ph if r['once']>=0.5];escaped=[r for r in detected if r['sonra']<0.5]
    return {'phishing_sayisi':len(ph),'baslangicta_yakalanan':len(detected),'atlatilan':len(escaped),'asr':len(escaped)/len(detected) if detected else None,'kontrol_sayisi':len(ctl),'kontrol_fp_once':sum(r['once']>=0.5 for r in ctl)/len(ctl) if ctl else None,'kontrol_fp_sonra':sum(r['sonra']>=0.5 for r in ctl)/len(ctl) if ctl else None}

def veri():
    bad=['urgent verify account password','confirm bank login immediately','security alert validate password','account suspended confirm identity','claim reward enter password','payment failed verify credentials','reset banking password now','unusual login verify account']
    good=['project meeting notes agenda','team schedule report attached','weekly minutes planning update','lunch meeting team calendar','budget report review document','project status meeting summary','release notes schedule planning','technical documentation team update']
    train=[]
    for label,texts in ((1,bad),(0,good)):
        for i,text in enumerate(texts):
            for j in range(3):train.append({'id':f'train-{label}-{i}-{j}','etiket':label,'metin':text+f' case {i*3+j}'})
    tests=[]
    for i in range(6):
        tests.append({'id':f'test-ph-{i}','etiket':1,'metin':['Verify your account password','Urgent banking login confirmation','Reset account credentials immediately'][i%3]+f' notice {i} at https://verify.pafta.invalid/session'})
        tests.append({'id':f'test-ok-{i}','etiket':0,'metin':['Project meeting notes for the team','Weekly schedule and documentation report','Planning agenda and release update'][i%3]+f' document {i}'})
    return train,tests

def deney(aday_fn,ara_fn,rapor_fn):
    try:
        import numpy as np,sklearn
        from sklearn.pipeline import make_pipeline
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
    except ImportError as e:raise ai_lab.GercekLabYok('Kurulu sklearn/numpy gerekli; otomatik indirme yok: '+str(e)) from e
    train,test=veri();assert not set(r['metin'] for r in train)&set(r['metin'] for r in test)
    model=make_pipeline(TfidfVectorizer(ngram_range=(1,2),norm='l2'),LogisticRegression(C=4,max_iter=300,random_state=54))
    model.fit([r['metin'] for r in train],[r['etiket'] for r in train])
    cls=[int(x) for x in model.classes_];positive=cls.index(1)
    inference=[]
    def score(text,role='evaluation'):
        p=float(model.predict_proba([text])[0,positive]);inference.append({'role':role,'metin':text,'skor':p});return p
    vec=model.steps[0][1];lr=model.steps[-1][1]
    fingerprint=hashlib.sha256(lr.coef_.tobytes()+lr.intercept_.tobytes()+vec.idf_.tobytes()+json.dumps(vec.vocabulary_,sort_keys=True).encode()).hexdigest()
    ekler=['project meeting notes','team schedule report attached','project meeting notes agenda team schedule report attached weekly minutes planning update']
    rows=[];traces=[];all_checks=[]
    for q in (1,3,4):
        measured=[]
        for sample in test:
            base=sample['metin'];candidates=aday_fn(base,list(ekler),100)
            expected=ref_adaylar(base,list(ekler),100)
            if candidates!=expected:raise AssertionError('Adaylar kaynak metni/karakter bütçesini korumalı')
            audit=[]
            def oracle(text):
                if text not in candidates or len(audit)>=q:raise AssertionError('Query bütçesi veya aday kapsamı aşıldı')
                p=score(text,'search');audit.append({'metin':text,'skor':p});return p
            selection=ara_fn(oracle,candidates,q)
            wanted={'secilen':min(audit,key=lambda r:r['skor'])['metin'],'sorgular':audit} if audit else None
            if len(audit)!=min(q,len(candidates)) or selection!=wanted:raise AssertionError('Gerçek predict_proba audit ile seçim eşleşmedi')
            chosen=selection['secilen']
            if not chosen.startswith(base) or len(chosen)-len(base)>100:raise AssertionError('İşlevi koruyan append-only kuralı bozuldu')
            measured.append({'id':sample['id'],'etiket':sample['etiket'],'once':score(base),'sonra':score(chosen)})
            traces.append({'id':sample['id'],'q':q,'orijinal':base,'adaylar':candidates,'sorgular':audit,'secilen':chosen,'eklenen_karakter':len(chosen)-len(base)})
        report=rapor_fn(measured);expected_report=ref_olcum_raporu(measured)
        if report!=expected_report:raise AssertionError('Gerçek risk ölçümü, ASR paydası veya kontrol FP yanlış')
        rows.append({'q':q,'kayitlar':measured,'rapor':report})
        all_checks.append(True)
    # Different local model with fixed vocabulary: no claim of general robust defence.
    stable=make_pipeline(TfidfVectorizer(vocabulary=['verify','password','account','urgent','credentials','login'],norm=None),LogisticRegression(C=4,max_iter=300,random_state=54))
    stable.fit([r['metin'] for r in train],[r['etiket'] for r in train])
    defense=[]
    for t in traces:
        if t['q']!=4:continue
        before=float(stable.predict_proba([t['orijinal']])[0,list(stable.classes_).index(1)])
        after=float(stable.predict_proba([t['secilen']])[0,list(stable.classes_).index(1)])
        defense.append({'id':t['id'],'once':before,'sonra':after,'fark':after-before})
    return {'kaynak':'gercek','cihaz':{'os':platform.platform(),'python':platform.python_version(),'device':'CPU'},'surumler':{'sklearn':sklearn.__version__,'numpy':np.__version__},'model':{'ad':'TfidfVectorizer(1,2,l2)+LogisticRegression','sha256':fingerprint,'classes':cls,'positive_label':1,'seed':54,'C':4,'max_iter':300,'n_iter':lr.n_iter_.tolist()},'train':train,'test':test,'veri_sha256':hashlib.sha256(json.dumps([train,test],sort_keys=True).encode()).hexdigest(),'ayarlar':{'karakter_butcesi':100,'q':[1,3,4],'esik':0.5,'ekler':ekler},'olcumler':rows,'query_audit':traces,'inference_audit':inference,'model_call_counts':{'search':sum(x['role']=='search' for x in inference),'evaluation':sum(x['role']=='evaluation' for x in inference),'defense':len(defense)*2},'dar_savunma':{'aciklama':'sabit risk kelimeleri, norm=None; sadece bu benign suffix adaylarına karşı karşılaştırma','sonuclar':defense},'kontroller':all_checks,'cleanup':'yalnız CPU nesneleri; sunucu/süreç/dosya kurulumu yok'}

def goster(a,b,c):
    r=deney(a,b,c)
    print('GERÇEK sklearn fit/predict_proba · sentetik veri · CPU')
    for x in r['olcumler']:print(json.dumps({'q':x['q'],**x['rapor']},ensure_ascii=False))
    print('Kanıt:',ai_lab.kanit_yaz('saldiri54-run',{'kaynak':'gercek','kabul':False,'ders':'ai-saldiri-54','deney':r}))
