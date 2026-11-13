"""VLM53: real frozen pretrained VLM, pixel autograd, targeted projected updates."""
from pathlib import Path
import os,json,hashlib,math,gc,time,uuid
import ai_lab
ROOT=Path(__file__).resolve().parents[1]
REV='7e3e67edbbed1bf9888184d9df282b700a323964'
MODEL='HuggingFaceTB/SmolVLM-256M-Instruct'
def hazirla():
    import shutil
    src=ROOT/'tracks/ai-saldiri/fixtures/ai-saldiri-53';d=Path('vlm');d.mkdir(exist_ok=True)
    for p in src.iterdir():
        if p.is_file() and not (d/p.name).exists():shutil.copyfile(p,d/p.name)

def ref_ikili_skor(logitler):
    import math
    if not isinstance(logitler,list) or len(logitler)!=2 or any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in logitler):raise ValueError('iki sonlu logit')
    m=max(logitler);a=[math.exp(x-m) for x in logitler];z=sum(a)
    return {'olasilik':[x/z for x in a],'secim':0 if logitler[0]>=logitler[1] else 1}

def ref_pgd_adimi(x0,xt,g,eps,alpha):
    import math
    if not all(isinstance(v,list) for v in (x0,xt,g)) or not x0 or len(x0)!=len(xt) or len(x0)!=len(g):raise ValueError('boyut')
    for v in (eps,alpha):
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<=v<=1:raise ValueError('butce')
    for row in (x0,xt,g):
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in row):raise ValueError('piksel/gradient')
    if any(not 0<=v<=1 for row in (x0,xt) for v in row):raise ValueError('piksel araligi')
    out=[]
    for a,b,c in zip(x0,xt,g):
        sign=1 if c>0 else -1 if c<0 else 0
        y=b-alpha*sign
        out.append(max(0,min(1,max(a-eps,min(a+eps,y)))))
    return out

def ref_degisim_raporu(rows):
    import math
    if not isinstance(rows,list) or not rows:raise ValueError('kayit')
    ids=set();once=sonra=donen=0
    for r in rows:
        if not isinstance(r,dict) or set(r)!={'id','hedef','once','sonra'} or not isinstance(r['id'],str) or not r['id'] or r['id'] in ids:raise ValueError('sema')
        ids.add(r['id'])
        if any(type(r[k]) is not int or r[k] not in (0,1) for k in ('hedef','once','sonra')):raise ValueError('indeks')
        once+=r['once']==r['hedef'];sonra+=r['sonra']==r['hedef'];donen+=r['once']!=r['hedef'] and r['sonra']==r['hedef']
    n=len(rows)-once
    return {'toplam':len(rows),'hedef_zaten_once':once,'hedef_sonra':sonra,'hedefe_donen':donen,'yeni_basari_orani':donen/n if n else None}

def deney(skor_fn,adim_fn,rapor_fn):
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1';os.environ['TOKENIZERS_PARALLELISM']='false'
    try:
        import torch,numpy as np,transformers
        from PIL import Image,ImageDraw
        from transformers import AutoProcessor,AutoModelForImageTextToText
    except ImportError as e:raise ai_lab.GercekLabYok(str(e)) from e
    path=Path(os.environ.get('PAFTA_VLM53_MODEL',str(ROOT/'.deps/SmolVLM-256M-Instruct-7e3e67ed')))
    if not (path/'model.safetensors').is_file():raise ai_lab.GercekLabYok('Onaylı VLM yerel dosyaları yok; otomatik indirme yapılmaz')
    sha=hashlib.sha256((path/'model.safetensors').read_bytes()).hexdigest()
    if sha!='74dea5904032e5ae99a2e0eef5179e6ac0f1dedc3ab0c7c2a5d4d387c843203e':raise ai_lab.GercekLabYok('Model hash sabit onaylı revizyonla eşleşmiyor')
    import urllib.parse
    # Exact expected official SHA is captured in the approved installation record; model stays local-only.
    install=ROOT/'outputs/vlm53-kurulum/kurulum.json'
    if install.exists():
        info=json.loads(install.read_text(encoding='utf-8'));wanted=next(x['sha256'] for x in info['files'] if x['file']=='model.safetensors')
        if sha!=wanted:raise ai_lab.GercekLabYok('Yerel model SHA256 onaylı dosyadan farklı')
    device=ai_lab.torch_cihazi();torch.set_num_threads(4);torch.manual_seed(53)
    if device=='cuda':torch.cuda.reset_peak_memory_stats()
    processor=AutoProcessor.from_pretrained(str(path),local_files_only=True,backend='pil')
    if list(processor.image_processor.image_mean)!=[0.5]*3 or list(processor.image_processor.image_std)!=[0.5]*3:raise ai_lab.GercekLabYok('Processor normalize ayarı değişmiş')
    model=AutoModelForImageTextToText.from_pretrained(str(path),local_files_only=True,dtype=torch.float32,attn_implementation='eager').eval().to(device)
    for p in model.parameters():p.requires_grad_(False)
    from engine.progress import data_dir
    media=Path(data_dir())/'ai-kanit-media'/('vlm53-'+uuid.uuid4().hex);media.mkdir(parents=True,exist_ok=False)
    prompt=processor.apply_chat_template([{'role':'user','content':[{'type':'image'},{'type':'text','text':'What color is the square? Answer red or blue.'}]}],add_generation_prompt=True)
    ids=[];tokens=[]
    for w in (' red',' blue'):
        encoded=processor.tokenizer.encode(w,add_special_tokens=False)
        if len(encoded)!=1:raise ai_lab.GercekLabYok('İki aday tek token değil; ölçüm tanımı değişti')
        ids.append(encoded[0]);tokens.append(w)
    observations=[];summaries=[];controls=[]
    try:
        for color,fill in [('red',(200,40,40)),('blue',(40,40,200))]:
            image=Image.new('RGB',(512,512),(220,220,220));ImageDraw.Draw(image).rectangle((100,100,412,412),fill=fill)
            clean_path=media/(color+'-clean.png');image.save(clean_path)
            batch=processor(text=prompt,images=image,return_tensors='pt',do_image_splitting=False,size={'longest_edge':512})
            batch={k:v.to(device) for k,v in batch.items()};pixel=batch.pop('pixel_values');x0=(pixel*0.5+0.5).detach()
            if list(x0.shape)!=[1,1,3,512,512]:raise ai_lab.GercekLabYok('Model giriş boyutu beklenenden farklı')
            with torch.no_grad():base_logits=model(**batch,pixel_values=(x0-0.5)/0.5,use_cache=False).logits[0,-1,ids].float().cpu().tolist()
            before=skor_fn(base_logits)
            if before!=ref_ikili_skor(base_logits):raise AssertionError('Gerçek ikili logit karşılaştırması yanlış')
            target=1-before['secim'];flat0=x0.flatten().cpu().tolist()
            for eps in (0.0,8/255):
                x=x0.clone();steps=[]
                for i in range(3):
                    x=x.detach().requires_grad_(True)
                    output=model(**batch,pixel_values=(x-0.5)/0.5,use_cache=False);pair=output.logits[0,-1,ids].float()
                    loss=torch.logsumexp(pair,dim=0)-pair[target]
                    grad=torch.autograd.grad(loss,x)[0]
                    if not bool(torch.isfinite(grad).all()) or float(grad.norm())<=0:raise ai_lab.GercekLabYok('Gerçek piksel gradienti sıfır/sonlu değil')
                    xt=x.detach().flatten().cpu().tolist();g=grad.detach().flatten().cpu().tolist()
                    projected=adim_fn(flat0,xt,g,eps,2/255)
                    expected=torch.maximum(torch.minimum(x.detach()-(2/255)*grad.sign(),x0+eps),x0-eps).clamp(0,1)
                    result=torch.tensor(projected,device=device,dtype=torch.float32).reshape_as(x)
                    error=float((result-expected).abs().max())
                    if error>1e-6 or not bool(torch.isfinite(result).all()):raise AssertionError('Öğrenci PGD adımı gerçek gradient/projeksiyonla eşleşmedi')
                    steps.append({'step':i,'loss':float(loss.detach()),'grad_norm':float(grad.norm()),'grad_linf':float(grad.abs().max()),'pixel_linf':float((result-x0).abs().max()),'student_projection_error':error})
                    x=result.detach();del output,pair,grad,loss,expected,result,xt,g,projected
                # Round-trip through an actual PNG; evaluate the reloaded bytes, not only an in-memory tensor.
                arr=(x[0,0].permute(1,2,0).clamp(0,1).cpu().numpy()*255).round().astype('uint8')
                adv_path=media/(color+('-zero.png' if eps==0 else '-attack.png'));Image.fromarray(arr).save(adv_path)
                reloaded=np.asarray(Image.open(adv_path).convert('RGB')).copy()
                actual=torch.tensor(reloaded,device=device,dtype=torch.float32).permute(2,0,1)[None,None]/255
                delta=float((actual-x0).abs().max())
                if delta>eps+1e-6:raise AssertionError('PNG round-trip sonrası piksel bütçesi aşıldı')
                with torch.no_grad():after_logits=model(**batch,pixel_values=(actual-0.5)/0.5,use_cache=False).logits[0,-1,ids].float().cpu().tolist()
                after=skor_fn(after_logits)
                if after!=ref_ikili_skor(after_logits):raise AssertionError('Gerçek son skor yanlış')
                zero_ok=eps!=0 or abs(before['olasilik'][0]-after['olasilik'][0])<1e-4
                if not zero_ok:raise ai_lab.GercekLabYok('Epsilon0 kontrolü tekrar üretilemedi')
                row={'id':color+('-zero' if eps==0 else '-attack'),'hedef':target,'once':before['secim'],'sonra':after['secim']}
                observations.append({'record':row,'color_label':color,'eps':eps,'alpha':2/255,'steps':steps,'before_logits':base_logits,'after_logits':after_logits,'before':before,'after':after,'linf_png':delta,'clean_png':str(clean_path),'adversarial_png':str(adv_path),'adversarial_sha256':hashlib.sha256(adv_path.read_bytes()).hexdigest(),'zero_control':zero_ok})
                controls.append(True)
                del x,actual
            del batch,pixel,x0,flat0
        for group in ('zero','attack'):
            rows=[r['record'] for r in observations if r['record']['id'].endswith(group)]
            result=rapor_fn(rows);expected=ref_degisim_raporu(rows)
            if result!=expected:raise AssertionError('VLM hedef tercih değişimi raporu yanlış')
            summaries.append({'group':group,'report':result})
        peak=torch.cuda.max_memory_allocated() if device=='cuda' else None
        rec={'kaynak':'gercek','cihaz':{'device':str(device)},'versions':{'torch':torch.__version__,'transformers':transformers.__version__},'model':{'id':MODEL,'revision':REV,'sha256':sha,'dtype':'float32','attention':'eager','parameters_frozen':all(not p.requires_grad for p in model.parameters()),'parameter_count':sum(p.numel() for p in model.parameters())},'processor':{'backend':'pil','size':512,'image_splitting':False,'normalization_mean':[0.5]*3,'normalization_std':[0.5]*3},'prompt':prompt,'candidate_tokens':tokens,'candidate_ids':ids,'objective':'targeted cross entropy restricted to two next-token logits; not full-vocabulary probability or generated answer','observations':observations,'summaries':summaries,'kontroller':controls,'gpu_peak_allocated_bytes':peak,'media_dir':str(media),'cleanup':'owned harness process; no external server or user model managed'}
    finally:
        del model,processor;gc.collect()
        if device=='cuda':torch.cuda.empty_cache()
    return rec

def goster(a,b,c):
    r=deney(a,b,c)
    print('GERÇEK VLM pixel autograd; PNG round-trip; yalnız iki token tercihi')
    print(json.dumps(r['summaries'],ensure_ascii=False))
    print('Görseller:',r['media_dir'])
    print('Kanıt:',ai_lab.kanit_yaz('saldiri53-run',{'kaynak':'gercek','kabul':False,'ders':'ai-saldiri-53','deney':r}))
