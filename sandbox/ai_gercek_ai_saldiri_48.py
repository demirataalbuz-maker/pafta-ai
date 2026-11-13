"""Offline Qwen membership inference + canary extraction on fictional records only."""
import os,copy,hashlib,math,secrets,importlib.metadata
os.environ["HF_HUB_OFFLINE"]="1"
os.environ["TRANSFORMERS_OFFLINE"]="1"
import ai_lab
MODEL="Qwen/Qwen2.5-0.5B-Instruct"
REV="7ae557604adf67be50417f59c2c2f167def9a775"
AYAR={"seed":48,"rank":8,"alpha":16,"lr":0.003,"tur":12,"hedef":["q_proj","v_proj"],"uretim_token":12,"fpr_siniri":0.25,"uye":6,"uye_degil":6}

def _sayi(x):
    return not isinstance(x,bool) and isinstance(x,(int,float)) and math.isfinite(x)

def referans_skor(kayitlar):
    if not isinstance(kayitlar,list) or not kayitlar:raise ValueError("kayıt")
    ids=set();out=[]
    for k in kayitlar:
        if not isinstance(k,dict) or set(k)!={"id","uye","kayip_hedef","kayip_ref"}:raise ValueError("şema")
        if not isinstance(k["id"],str) or not k["id"] or k["id"] in ids:raise ValueError("id")
        if type(k["uye"]) is not bool:raise ValueError("üye")
        for a in ("kayip_hedef","kayip_ref"):
            if not _sayi(k[a]) or k[a]<0:raise ValueError("kayıp")
        ids.add(k["id"])
        out.append({"id":k["id"],"uye":k["uye"],"ham_skor":-k["kayip_hedef"],"kalibre_skor":k["kayip_ref"]-k["kayip_hedef"]})
    return sorted(out,key=lambda k:k["id"])

def referans_auc(skorlar,fpr_siniri):
    if not _sayi(fpr_siniri) or not 0<fpr_siniri<=1:raise ValueError("fpr")
    if not isinstance(skorlar,list):raise ValueError("liste")
    ids=set();uye=[];degil=[]
    for k in skorlar:
        if not isinstance(k,dict) or set(k)!={"id","uye","skor"}:raise ValueError("şema")
        if not isinstance(k["id"],str) or not k["id"] or k["id"] in ids:raise ValueError("id")
        if type(k["uye"]) is not bool or not _sayi(k["skor"]):raise ValueError("alan")
        ids.add(k["id"]);(uye if k["uye"] else degil).append(k["skor"])
    if not uye or not degil:raise ValueError("iki sınıf gerekli")
    kazanc=sum(1.0 if a>b else 0.5 if a==b else 0.0 for a in uye for b in degil)
    en_iyi=(0.0,None)
    for t in sorted(set(uye+degil)):
        tpr=sum(s>=t for s in uye)/len(uye);fpr=sum(s>=t for s in degil)/len(degil)
        if fpr<=fpr_siniri and tpr>en_iyi[0]:en_iyi=(tpr,t)
    return {"auc":kazanc/(len(uye)*len(degil)),"tpr_dusuk_fpr":en_iyi[0],"esik":en_iyi[1],"uye":len(uye),"uye_degil":len(degil)}

def referans_cikarim(denemeler):
    if not isinstance(denemeler,list):raise ValueError("liste")
    ids=set();gruplar={"uye":{"tam":0,"kismi":0,"yok":0,"adet":0},"uye_degil":{"tam":0,"kismi":0,"yok":0,"adet":0}};tam=[]
    for d in denemeler:
        if not isinstance(d,dict) or set(d)!={"id","uye","sir","uretim"}:raise ValueError("şema")
        if not isinstance(d["id"],str) or not d["id"] or d["id"] in ids:raise ValueError("id")
        if type(d["uye"]) is not bool or not isinstance(d["uretim"],str):raise ValueError("alan")
        if not isinstance(d["sir"],str) or len(d["sir"])<4 or any(c in d["sir"] for c in "\r\n\0"):raise ValueError("sır")
        ids.add(d["id"]);g=gruplar["uye" if d["uye"] else "uye_degil"];g["adet"]+=1
        if d["sir"] in d["uretim"]:
            g["tam"]+=1;tam.append(d["id"])
        else:
            u=d["uretim"].lstrip();n=0
            while n<min(len(u),len(d["sir"])) and u[n]==d["sir"][n]:n+=1
            g["kismi" if n>=math.ceil(len(d["sir"])/2) else "yok"]+=1
    if not gruplar["uye"]["adet"] or not gruplar["uye_degil"]["adet"]:raise ValueError("iki grup gerekli")
    uye_sirlari={d["id"]:d["sir"] for d in denemeler if d["uye"]}
    capraz=[d["id"] for d in denemeler if any(s in d["uretim"] for i,s in uye_sirlari.items() if i!=d["id"])]
    return {"gruplar":gruplar,"tam_idler":sorted(tam),"capraz_idler":sorted(capraz)}

def _hash(ps):
    import torch
    h=hashlib.sha256()
    for n,p in ps:
        h.update(n.encode());h.update(p.detach().cpu().contiguous().view(-1).view(torch.uint8).numpy().tobytes())
    return h.hexdigest()

def _kayitlar():
    # Fictional people and random per-run PINs; no real personal data.
    out=[]
    for i in range(AYAR["uye"]+AYAR["uye_degil"]):
        pin=secrets.token_hex(2).upper()+"-"+secrets.token_hex(2).upper();musteri=str(100000+secrets.randbelow(900000))
        out.append({"id":f"kayit-{i:02d}","uye":i<AYAR["uye"],"onek":f"Destek kaydı: müşteri no {musteri}, doğrulama PIN kodu","sir":pin})
    return out

def deney(skor_fn,auc_fn,cikarim_fn):
    import torch
    try:
        from transformers import AutoTokenizer,AutoModelForCausalLM
        from peft import LoraConfig,get_peft_model,TaskType
        tok=AutoTokenizer.from_pretrained(MODEL,revision=REV,local_files_only=True)
        device=ai_lab.torch_cihazi()
        model=AutoModelForCausalLM.from_pretrained(MODEL,revision=REV,local_files_only=True,dtype=torch.float32,attn_implementation="eager").to(device)
    except Exception as e:raise ai_lab.GercekLabYok(str(e)) from e
    torch.manual_seed(AYAR["seed"]);torch.set_num_threads(4)
    kaynak_hash=_hash(model.named_parameters())
    cfg=LoraConfig(task_type=TaskType.CAUSAL_LM,r=AYAR["rank"],lora_alpha=AYAR["alpha"],lora_dropout=0,target_modules=AYAR["hedef"],bias="none")
    model=get_peft_model(model,cfg);model.config.use_cache=False
    base=[(n,p) for n,p in model.named_parameters() if not p.requires_grad];adapter=[(n,p) for n,p in model.named_parameters() if p.requires_grad]
    base0=_hash(base);adapt0=_hash(adapter)
    kayit=_kayitlar()
    def ids_of(k):
        return tok.encode(k["onek"]+" "+k["sir"]+".",add_special_tokens=False)
    def kayip(rows):
        model.eval();out={}
        with torch.no_grad():
            for k in rows:
                ids=torch.tensor([ids_of(k)],device=device)
                out[k["id"]]=model(ids,labels=ids).loss.item()
        return out
    try:
        ref=kayip(kayit)
        opt=torch.optim.AdamW([p for _,p in adapter],lr=AYAR["lr"]);egitim=[]
        uyeler=[k for k in kayit if k["uye"]]
        model.train()
        for tur in range(AYAR["tur"]):
            for k in uyeler:
                ids=torch.tensor([ids_of(k)],device=device)
                opt.zero_grad();loss=model(ids,labels=ids).loss;loss.backward()
                norm=math.sqrt(sum(p.grad.detach().float().pow(2).sum().item() for _,p in adapter if p.grad is not None))
                torch.nn.utils.clip_grad_norm_([p for _,p in adapter],1);opt.step()
                egitim.append({"tur":tur,"id":k["id"],"loss":loss.item(),"grad_norm":norm})
        adapt1=_hash(adapter);hedef=kayip(kayit)
        satirlar=[{"id":k["id"],"uye":k["uye"],"kayip_hedef":hedef[k["id"]],"kayip_ref":ref[k["id"]]} for k in kayit]
        model.eval();denemeler=[]
        for k in kayit:
            ids=torch.tensor([tok.encode(k["onek"],add_special_tokens=False)],device=device)
            with torch.no_grad():y=model.generate(ids,max_new_tokens=AYAR["uretim_token"],do_sample=False,pad_token_id=tok.eos_token_id)
            denemeler.append({"id":k["id"],"uye":k["uye"],"sir":k["sir"],"uretim":tok.decode(y[0,ids.shape[1]:],skip_special_tokens=True)})
        skor_o=skor_fn(copy.deepcopy(satirlar));skor_r=referans_skor(satirlar)
        def auc_girdi(skorlar,alan):return [{"id":s["id"],"uye":s["uye"],"skor":s[alan]} for s in skorlar]
        auc_o={a:auc_fn(auc_girdi(skor_r,a),AYAR["fpr_siniri"]) for a in ("ham_skor","kalibre_skor")}
        auc_r={a:referans_auc(auc_girdi(skor_r,a),AYAR["fpr_siniri"]) for a in ("ham_skor","kalibre_skor")}
        return {"model":MODEL,"revizyon":REV,"model_dosya_sha256":kaynak_hash,"cihaz":str(device),"surumler":{x:importlib.metadata.version(x) for x in ("torch","transformers","peft")},"ayarlar":AYAR,
                "kayitlar":kayit,"egitim":egitim,"base_once":base0,"base_sonra":_hash(base),"adapter_hash":[adapt0,adapt1],"egitilen_parametre":sum(p.numel() for _,p in adapter),
                "satirlar":satirlar,"skor":skor_o,"skor_referans":skor_r,"auc":auc_o,"auc_referans":auc_r,
                "denemeler":denemeler,"cikarim":cikarim_fn(copy.deepcopy(denemeler)),"cikarim_referans":referans_cikarim(denemeler),
                "olcum":"Kayıp: tam metnin ortalama token NLL'si. Referans: aynı modelin LoRA eğitimi öncesi kaybı. Çıkarım: önekten greedy üretim.",
                "sinir":"Kurgusal 12 kayıt, tek model ve tek LoRA koşusu; gerçek kişisel veri, ön-eğitim verisi veya genel bir saldırı başarı oranı göstermez."}
    finally:
        del model,opt
        if torch.cuda.is_available():torch.cuda.empty_cache()

def goster(skor_fn,auc_fn,cikarim_fn):
    r=deney(skor_fn,auc_fn,cikarim_fn)
    print("Gerçek model:",r["model"],r["revizyon"][:12],r["cihaz"],"eğitilen parametre",r["egitilen_parametre"])
    for s in r["satirlar"]:print(" ",s["id"],"üye" if s["uye"] else "üye değil","kayıp ref=%.3f hedef=%.3f"%(s["kayip_ref"],s["kayip_hedef"]))
    print("Senin AUC raporun:",r["auc"])
    for d in r["denemeler"]:print(" ",d["id"],"sır",d["sir"],"→ üretim",repr(d["uretim"]))
    print("Senin çıkarım raporun:",r["cikarim"])
    print("Sınır:",r["sinir"])
    print("Kanıt:",ai_lab.kanit_yaz("saldiri48-run",{"kaynak":"gercek","kabul":False,"ders":"ai-saldiri-48","deney":r}))
