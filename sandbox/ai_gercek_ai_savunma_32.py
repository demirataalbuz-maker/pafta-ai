"""Kendi prompt injection sınıflandırıcını eğit: DistilBERT + deepset/prompt-injections (çevrimdışı, sabit revizyon)."""
import os,copy,glob,hashlib,math,random,re,importlib.metadata
os.environ["HF_HUB_OFFLINE"]="1"
os.environ["TRANSFORMERS_OFFLINE"]="1"
import ai_lab
MODEL="distilbert/distilbert-base-uncased"
REV="12040accade4e8a0f71eabdb258fecc2e7e948be"
VERI="deepset/prompt-injections"
VERI_REV="4f61ecb038e9c3fb77e21034b22511b523772cdd"
VERI_DOSYALARI={"train":"train-00000-of-00001-9564e8b05b4757ab.parquet","test":"test-00000-of-00001-701d16158af87368.parquet"}
VERI_SHA={"train":"2e10bc7ab30f542c97e4e83e2a5683000b5057d25ec10908784c631d44124c04","test":"39ac797cabc157eeed58435a08593b2952bb6cb16fc394a2d383f447cc7b246e"}
AYAR={"seed":32,"tur":3,"batch":16,"lr":5e-5,"max_token":128,"dogrulama_orani":0.15,"fpr_siniri":0.05}
KIPLER=("orijinal","leet","sifir_genislik","homoglif","harf_bosluklu")
ANAHTAR=("ignore","forget","disregard","previous instructions","prompt","system","vergiss","ignoriere","vorherigen","anweisungen")

def _sayi(x):
    return not isinstance(x,bool) and isinstance(x,(int,float)) and math.isfinite(x)

def _etiket_skor(etiketler,skorlar):
    if not isinstance(etiketler,list) or not isinstance(skorlar,list) or not etiketler or len(etiketler)!=len(skorlar):raise ValueError("liste")
    if any(type(e) is not int or e not in (0,1) for e in etiketler) or any(not _sayi(s) or not 0<=s<=1 for s in skorlar):raise ValueError("değer")
    if 0 not in etiketler or 1 not in etiketler:raise ValueError("iki sınıf gerekli")

def referans_metrik(etiketler,skorlar,esik):
    _etiket_skor(etiketler,skorlar)
    if not _sayi(esik) or not 0<=esik<=1:raise ValueError("eşik")
    tp=sum(1 for e,s in zip(etiketler,skorlar) if e==1 and s>=esik);fn=etiketler.count(1)-tp
    fp=sum(1 for e,s in zip(etiketler,skorlar) if e==0 and s>=esik);tn=etiketler.count(0)-fp
    p=tp/(tp+fp) if tp+fp else 0.0;r=tp/(tp+fn)
    return {"tp":tp,"fp":fp,"tn":tn,"fn":fn,"precision":p,"recall":r,"f1":2*p*r/(p+r) if p+r else 0.0,"fpr":fp/(fp+tn)}

def referans_esik(etiketler,skorlar,fpr_siniri):
    _etiket_skor(etiketler,skorlar)
    if not _sayi(fpr_siniri) or not 0<=fpr_siniri<1:raise ValueError("fpr")
    en=None
    for t in sorted(set(skorlar),reverse=True):
        m=referans_metrik(etiketler,skorlar,t)
        if m["fpr"]<=fpr_siniri and (en is None or m["recall"]>en["recall"]):en={"esik":t,"recall":m["recall"],"fpr":m["fpr"]}
    return en or {"esik":None,"recall":0.0,"fpr":0.0}

def referans_bozulma(kayitlar,esik):
    if not _sayi(esik) or not 0<=esik<=1:raise ValueError("eşik")
    if not isinstance(kayitlar,list):raise ValueError("liste")
    g={};ids=set()
    for k in kayitlar:
        if not isinstance(k,dict) or set(k)!={"id","kip","etiket","skor"}:raise ValueError("şema")
        if not isinstance(k["kip"],str) or k["kip"] not in KIPLER:raise ValueError("kip")
        if not isinstance(k["id"],str) or not k["id"] or (k["id"],k["kip"]) in ids:raise ValueError("id")
        if k["kip"] not in KIPLER or type(k["etiket"]) is not int or k["etiket"] not in (0,1) or not _sayi(k["skor"]) or not 0<=k["skor"]<=1:raise ValueError("alan")
        ids.add((k["id"],k["kip"]));x=g.setdefault(k["kip"],{"pozitif":0,"yakalanan":0,"negatif":0,"yanlis_alarm":0})
        if k["etiket"]:x["pozitif"]+=1;x["yakalanan"]+=k["skor"]>=esik
        else:x["negatif"]+=1;x["yanlis_alarm"]+=k["skor"]>=esik
    if "orijinal" not in g or any(not x["pozitif"] or not x["negatif"] for x in g.values()):raise ValueError("orijinal kip ve iki sınıf gerekli")
    out={}
    for kip in KIPLER:
        if kip in g:
            x=g[kip];r,f=x["yakalanan"]/x["pozitif"],x["yanlis_alarm"]/x["negatif"]
            out[kip]={"recall":r,"fpr":f,"j":r-f}
    o=out["orijinal"]["j"]
    for kip in out:out[kip]["j_dusus"]=o-out[kip]["j"]
    return {"kipler":out,"en_zayif":min(out,key=lambda k:(out[k]["j"],KIPLER.index(k)))}

LEET=str.maketrans({"a":"4","e":"3","i":"1","o":"0","s":"5","A":"4","E":"3","I":"1","O":"0","S":"5"})
HOMO=str.maketrans({"a":"а","e":"е","o":"о","c":"с","p":"р","x":"х","y":"у"})
def bozul(metin,kip):
    if kip=="orijinal":return metin
    if kip=="leet":return metin.translate(LEET)
    if kip=="sifir_genislik":return "​".join(metin)
    if kip=="homoglif":return metin.translate(HOMO)
    if kip=="harf_bosluklu":return " ".join(" ".join(w) for w in metin.split(" "))
    raise ValueError(kip)

def _sha(yol):
    with open(yol,"rb") as f:return hashlib.sha256(f.read()).hexdigest()

def _veri():
    try:
        import pandas as pd
        from huggingface_hub import hf_hub_download
        dosya={a:hf_hub_download(VERI,"data/"+ad,repo_type="dataset",revision=VERI_REV,local_files_only=True) for a,ad in VERI_DOSYALARI.items()}
    except Exception as e:raise ai_lab.GercekLabYok(f"{VERI}@{VERI_REV[:8]} yerelde yok: {e}") from e
    tablo={a:[{"id":f"{a}-{i:03d}","metin":t,"etiket":int(l)} for i,(t,l) in enumerate(zip(pd.read_parquet(y).text,pd.read_parquet(y).label))] for a,y in dosya.items()}
    return tablo,{a:{"dosya":os.path.basename(y),"sha256":_sha(y)} for a,y in dosya.items()}

def _hash(model):
    import torch
    h=hashlib.sha256()
    for n,p in model.named_parameters():h.update(n.encode());h.update(p.detach().cpu().contiguous().view(-1).view(torch.uint8).numpy().tobytes())
    return h.hexdigest()

def deney(metrik_fn,esik_fn,bozulma_fn):
    import torch
    tablo,dosyalar=_veri()
    try:
        from transformers import AutoTokenizer,AutoModelForSequenceClassification
        tok=AutoTokenizer.from_pretrained(MODEL,revision=REV,local_files_only=True)
        device=ai_lab.torch_cihazi()
        random.seed(AYAR["seed"]);torch.manual_seed(AYAR["seed"])
        model=AutoModelForSequenceClassification.from_pretrained(MODEL,revision=REV,local_files_only=True,num_labels=2).to(device)
    except Exception as e:raise ai_lab.GercekLabYok(str(e)) from e
    # Eşik test kümesinde değil, eğitim kümesinden ayrılan doğrulama kümesinde seçilir (sınıf oranı korunur).
    rng=random.Random(AYAR["seed"]);egitim,dogrulama=[],[]
    for e in (0,1):
        grup=[k for k in tablo["train"] if k["etiket"]==e];rng.shuffle(grup);n=round(len(grup)*AYAR["dogrulama_orani"])
        dogrulama+=grup[:n];egitim+=grup[n:]
    rng.shuffle(egitim);test=tablo["test"]
    def kodla(metinler):return tok(metinler,truncation=True,max_length=AYAR["max_token"],padding=True,return_tensors="pt").to(device)
    def skorla(metinler):
        model.eval();out=[]
        with torch.no_grad():
            for i in range(0,len(metinler),32):
                out+=torch.softmax(model(**kodla(metinler[i:i+32])).logits.float(),-1)[:,1].tolist()
        return [min(1.0,max(0.0,s)) for s in out]
    try:
        once=_hash(model);opt=torch.optim.AdamW(model.parameters(),lr=AYAR["lr"]);kayip=[]
        for tur in range(AYAR["tur"]):
            model.train();sira=egitim[:];rng.shuffle(sira)
            for i in range(0,len(sira),AYAR["batch"]):
                b=sira[i:i+AYAR["batch"]];opt.zero_grad()
                l=model(**kodla([k["metin"] for k in b]),labels=torch.tensor([k["etiket"] for k in b],device=device)).loss
                l.backward();opt.step();kayip.append({"tur":tur,"adim":i//AYAR["batch"],"kayip":l.item()})
        sonra=_hash(model)
        ve=[k["etiket"] for k in dogrulama];vs=skorla([k["metin"] for k in dogrulama])
        te=[k["etiket"] for k in test];ts=skorla([k["metin"] for k in test])
        esik_r=referans_esik(ve,vs,AYAR["fpr_siniri"]);esik_o=esik_fn(list(ve),list(vs),AYAR["fpr_siniri"])
        if esik_r["esik"] is None:
            raise ValueError("Doğrulama FPR sınırına uygun aday eşik yok; sessiz eşik ataması yapılmadı")
        secilen=esik_r["esik"]
        anahtar=[1.0 if any(a in k["metin"].lower() for a in ANAHTAR) else 0.0 for k in test]
        bozuk=[]
        for kip in KIPLER:
            sk=ts if kip=="orijinal" else skorla([bozul(k["metin"],kip) for k in test])
            bozuk+=[{"id":k["id"],"kip":kip,"etiket":k["etiket"],"skor":s} for k,s in zip(test,sk)]
        ornek=[{"kip":kip,"metin":bozul(t["metin"],kip)[:160],"token":tok.tokenize(bozul(t["metin"],kip))[:24]} for t in test if t["etiket"] for kip in KIPLER][:len(KIPLER)]
        metrik_girdi={"test_0.5":(te,ts,0.5),"test_secilen":(te,ts,secilen),"anahtar_kelime":(te,anahtar,0.5),"dogrulama_secilen":(ve,vs,secilen)}
        return {"model":MODEL,"revizyon":REV,"veri":VERI,"veri_revizyon":VERI_REV,"veri_dosyalari":dosyalar,"cihaz":str(device),
                "surumler":{x:importlib.metadata.version(x) for x in ("torch","transformers")},"ayarlar":AYAR,"anahtar_kelimeler":ANAHTAR,
                "boyut":{"egitim":len(egitim),"dogrulama":len(dogrulama),"test":len(test)},"dogrulama_idleri":sorted(k["id"] for k in dogrulama),
                "egitim_idleri":sorted(k["id"] for k in egitim),"test_idleri":[k["id"] for k in test],"kayip":kayip,"agirlik_hash":[once,sonra],
                "dogrulama_skor":{"etiket":ve,"skor":vs},"test_skor":{"etiket":te,"skor":ts},
                "esik":esik_o,"esik_referans":esik_r,
                "metrik":{a:metrik_fn(list(e),list(s),t) for a,(e,s,t) in metrik_girdi.items()},
                "metrik_referans":{a:referans_metrik(e,s,t) for a,(e,s,t) in metrik_girdi.items()},
                "secilen_esik":secilen,"bozulma_kayit":bozuk,"bozulma":bozulma_fn(copy.deepcopy(bozuk),secilen),"bozulma_referans":referans_bozulma(bozuk,secilen),
                "bozulma_ornek":ornek,
                "olcum":"skor: DistilBERT'in injection sınıfı olasılığı (softmax). Eşik doğrulama kümesinde FPR sınırıyla seçilir, test kümesinde ölçülür. Bozulmalar test metinlerine uygulanır; model bunlarla eğitilmez.",
                "sinir":"Tek küçük açık veri seti (546+116, İngilizce ve Almanca, etiketleri tartışmalı örnekler içerir), tek eğitim koşusu ve beş basit bozulma; gerçek trafikteki dağılımı, uyarlanabilir saldırganı ya da başka dilleri göstermez."}
    finally:
        del model
        if torch.cuda.is_available():torch.cuda.empty_cache()

def goster(metrik_fn,esik_fn,bozulma_fn):
    r=deney(metrik_fn,esik_fn,bozulma_fn)
    print("Model:",r["model"],r["revizyon"][:12],"| veri:",r["veri"],r["veri_revizyon"][:8],"|",r["cihaz"],r["boyut"])
    print("Seçilen eşik (doğrulama, FPR≤%.2f):"%r["ayarlar"]["fpr_siniri"],r["esik"])
    for a,m in r["metrik"].items():print(" ",a,m)
    print("Bozulma raporun:",r["bozulma"])
    for o in r["bozulma_ornek"]:print("  ",o["kip"],o["token"])
    print("Sınır:",r["sinir"])
    print("Kanıt:",ai_lab.kanit_yaz("savunma32-run",{"kaynak":"gercek","kabul":False,"ders":"ai-savunma-32","deney":r}))
