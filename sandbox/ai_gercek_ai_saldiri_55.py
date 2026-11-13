"""Synthetic speech detection on approved local data: LibriSpeech dummy (real, one speaker) vs Piper LJSpeech TTS and Windows SAPI; shortcut and evasion conditions."""
import copy,hashlib,io,os,subprocess,sys,tempfile,time,wave
from pathlib import Path
import ai_lab

KOK=Path(__file__).resolve().parents[1]
SES=Path(os.environ.get("PAFTA_SES55_ROOT",str(KOK/".deps/ses-tespit")))
PIPER_PKG=SES/"pkg"
MODEL=SES/"piper-voices/en/en_US/ljspeech/medium/en_US-ljspeech-medium.onnx"
VERI=SES/"librispeech_asr_dummy/clean/validation-00000-of-00001.parquet"
SHA={MODEL:"6f52a751e2349abe7a76735eb09dc1875298c77ea2342ffd2fef79ff81b87f22",VERI:"4e69a06fa5edc90921e5e7e39a7084881f8b3ed9c805c574f4f39c6fde27c603"}
AYAR={"metin_sayisi":45,"test_orani":0.34,"hz":16000,"genis_hz":22050,"bant":24,"esik":0.5,"snr_db":20,"telefon":[300,3400],"seed":55}
KOSULLAR=("temiz","gurultu_20db","telefon","ornekleme_16k","sapi")
MODELLER=("A_karisik_hz","B_esit_hz")
KAYNAKLAR=("gercek","sentetik")

def _sha_dosya(p):
    with open(p,"rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()

def _sayi(x):
    return type(x) in (int,float)

def referans_bol(kayitlar,test_orani):
    if not _sayi(test_orani) or not 0<test_orani<1:raise ValueError("oran")
    if not isinstance(kayitlar,list) or not kayitlar:raise ValueError("liste")
    ids=set()
    for k in kayitlar:
        if not isinstance(k,dict) or set(k)!={"id","metin","kaynak"}:raise ValueError("şema")
        if not isinstance(k["id"],str) or not k["id"] or k["id"] in ids:raise ValueError("id")
        if not isinstance(k["metin"],str) or not k["metin"] or k["kaynak"] not in KAYNAKLAR:raise ValueError("alan")
        ids.add(k["id"])
    gruplar=sorted({k["metin"] for k in kayitlar},key=lambda m:hashlib.sha256(m.encode("utf-8")).hexdigest())
    n=round(len(gruplar)*test_orani)
    if not 1<=n<len(gruplar):raise ValueError("bölünemez")
    test=set(gruplar[:n])
    b={"egitim":sorted(k["id"] for k in kayitlar if k["metin"] not in test),"test":sorted(k["id"] for k in kayitlar if k["metin"] in test)}
    for ad in b:
        if {k["kaynak"] for k in kayitlar if k["id"] in b[ad]}!=set(KAYNAKLAR):raise ValueError("iki kaynak da gerekli")
    return b

def _dogrula(skorlar,etiketler):
    if not isinstance(skorlar,list) or not isinstance(etiketler,list) or not skorlar or len(skorlar)!=len(etiketler):raise ValueError("liste")
    if any(not _sayi(s) for s in skorlar) or any(type(e) is not int or e not in (0,1) for e in etiketler):raise ValueError("değer")
    if set(etiketler)!={0,1}:raise ValueError("iki sınıf")

def _oranlar(skorlar,etiketler,esik):
    P=sum(etiketler);N=len(etiketler)-P
    tp=sum(1 for s,e in zip(skorlar,etiketler) if e and s>=esik);fp=sum(1 for s,e in zip(skorlar,etiketler) if not e and s>=esik)
    return tp/P,fp/N,(tp+N-fp)/len(etiketler)

def referans_metrik(skorlar,etiketler,esik):
    _dogrula(skorlar,etiketler)
    if not _sayi(esik):raise ValueError("eşik")
    tpr,fpr,dog=_oranlar(skorlar,etiketler,esik)
    return {"tpr":tpr,"fpr":fpr,"dogruluk":dog}

def referans_eer(skorlar,etiketler):
    _dogrula(skorlar,etiketler)
    en=None
    for t in sorted(set(skorlar)):
        tpr,fpr,_=_oranlar(skorlar,etiketler,t);fnr=1-tpr
        a=(abs(fpr-fnr),(fpr+fnr)/2,t)
        if en is None or a<en[0]:en=(a,{"eer":(fpr+fnr)/2,"esik":t,"fpr":fpr,"fnr":fnr})
    return en[1]

def referans_rapor(satirlar):
    if not isinstance(satirlar,list) or not satirlar:raise ValueError("liste")
    tab={}
    for s in satirlar:
        if not isinstance(s,dict) or set(s)!={"model","kosul","tpr","fpr","eer"}:raise ValueError("şema")
        if not isinstance(s["model"],str) or not s["model"] or not isinstance(s["kosul"],str) or not s["kosul"]:raise ValueError("ad")
        if any(not _sayi(s[k]) or not 0<=s[k]<=1 for k in ("tpr","fpr","eer")):raise ValueError("oran")
        if s["kosul"] in tab.setdefault(s["model"],{}):raise ValueError("tekrar")
        tab[s["model"]][s["kosul"]]=s
    if any("temiz" not in k for k in tab.values()):raise ValueError("temiz gerekli")
    out={};kir=[]
    for m in sorted(tab):
        t=tab[m]["temiz"];ks={}
        for k in sorted(tab[m]):
            if k=="temiz":continue
            x=tab[m][k];ks[k]={"tpr_dusus":t["tpr"]-x["tpr"],"fpr_artis":x["fpr"]-t["fpr"],"eer_artis":x["eer"]-t["eer"]}
        en=min(ks,key=lambda k:(-ks[k]["eer_artis"],k)) if ks else None
        out[m]={"temiz":{"tpr":t["tpr"],"fpr":t["fpr"],"eer":t["eer"]},"kosullar":ks,"kirilan":sorted(k for k in ks if tab[m][k]["tpr"]<0.5),"en_kotu":en}
        if t["eer"]<=0.1 and any(v["tpr_dusus"]>=0.5 for v in ks.values()):kir.append(m)
    return {"modeller":out,"kirilgan":kir}

# ---------- sinyal ----------
def _np():
    import numpy as np
    return np

def _yeniden(x,kaynak,hedef):
    from scipy.signal import resample_poly
    from math import gcd
    g=gcd(kaynak,hedef);return resample_poly(x,hedef//g,kaynak//g)

def _ozellik(x,hz,ust_hz):
    np=_np();n=512;h=256
    if len(x)<n:x=np.pad(x,(0,n-len(x)))
    pencere=np.hanning(n);kare=np.lib.stride_tricks.sliding_window_view(x,n)[::h]*pencere
    G=np.abs(np.fft.rfft(kare,axis=1))**2;f=np.fft.rfftfreq(n,1/hz)
    sinir=np.linspace(0,ust_hz,AYAR["bant"]+1);bant=[]
    for a,b in zip(sinir[:-1],sinir[1:]):
        m=(f>=a)&(f<b);bant.append(np.log10(G[:,m].mean(axis=1)+1e-10) if m.any() else np.full(len(G),-10.0))
    B=np.stack(bant,axis=1)
    duzluk=np.exp(np.mean(np.log(G+1e-12),axis=1))/(np.mean(G,axis=1)+1e-12)
    zcr=np.mean(np.abs(np.diff(np.sign(x))))/2
    return np.concatenate([B.mean(0),B.std(0),[duzluk.mean(),zcr]])

def _gurultu(x,db,rng):
    np=_np();p=np.mean(x**2);return x+rng.normal(0,np.sqrt(p/10**(db/10)),len(x))

def _telefon(x,hz):
    from scipy.signal import butter,sosfiltfilt
    return sosfiltfilt(butter(4,AYAR["telefon"],btype="bandpass",fs=hz,output="sos"),x)

def _wav_oku(yol):
    np=_np()
    with wave.open(str(yol),"rb") as w:
        hz=w.getframerate();y=np.frombuffer(w.readframes(w.getnframes()),dtype=np.int16).astype(np.float64)/32768
        if w.getnchannels()>1:y=y.reshape(-1,w.getnchannels()).mean(1)
    return y,hz

def _sapi(metinler,dizin,ses="Microsoft Zira Desktop",onek="sapi"):
    betik=f"Add-Type -AssemblyName System.Speech;$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;$s.SelectVoice('{ses}');"
    for i,_ in enumerate(metinler):betik+=f"$s.SetOutputToWaveFile('{dizin}\\{onek}{i}.wav');$s.Speak([IO.File]::ReadAllText('{dizin}\\m{i}.txt'));"
    for i,m in enumerate(metinler):(Path(dizin)/f"m{i}.txt").write_text(m,encoding="utf-8")
    r=subprocess.run(["powershell.exe","-NoProfile","-NonInteractive","-Command",betik+"$s.Dispose()"],capture_output=True,text=True,timeout=120,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
    if r.returncode:raise ai_lab.GercekLabYok(f"Windows SAPI ({ses}) kullanılamadı: "+r.stderr[:200])
    return [Path(dizin)/f"{onek}{i}.wav" for i in range(len(metinler))]

def _sapi_sesleri():
    r=subprocess.run(["powershell.exe","-NoProfile","-NonInteractive","-Command","Add-Type -AssemblyName System.Speech;(New-Object System.Speech.Synthesis.SpeechSynthesizer).GetInstalledVoices()|%{$_.VoiceInfo.Name}"],
                     capture_output=True,text=True,timeout=60,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
    return [s.strip() for s in r.stdout.splitlines() if s.strip()]

def deney(bol_fn,metrik_fn,eer_fn,rapor_fn):
    if os.name!="nt":raise ai_lab.GercekLabYok("Bu ders Windows SAPI ve onaylı .deps/ses-tespit kurulumunu kullanır.")
    for p,h in SHA.items():
        if not p.is_file() or _sha_dosya(p)!=h:raise ai_lab.GercekLabYok(f"Onaylı dosya yok ya da SHA256 farklı: {p.name}; otomatik indirme yok.")
    if not (PIPER_PKG/"piper").is_dir():raise ai_lab.GercekLabYok("Onaylı piper-tts 1.8.0 paketi .deps/ses-tespit/pkg altında yok.")
    np=_np();import av,pyarrow.parquet as pq
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    sys.path.insert(0,str(PIPER_PKG))
    try:from piper import PiperVoice
    finally:sys.path.remove(str(PIPER_PKG))
    t0=time.time();tablo=pq.read_table(VERI).to_pylist()
    tablo=sorted(tablo,key=lambda r:(len(r["text"]),r["id"]))[:AYAR["metin_sayisi"]]
    gercek={}
    for r in tablo:
        c=av.open(io.BytesIO(r["audio"]["bytes"]));hz=c.streams.audio[0].rate
        x=np.concatenate([f.to_ndarray().reshape(-1) for f in c.decode(audio=0)]).astype(np.float64);c.close()
        if np.abs(x).max()>1.5:x=x/32768
        gercek[r["id"]]=(x,hz,r["text"].capitalize()+".",r["speaker_id"])
    ses=PiperVoice.load(str(MODEL));sentetik={};sure_piper=time.time()
    with tempfile.TemporaryDirectory(prefix="pafta-ses-") as td:
        for i,(rid,(_,_,metin,_)) in enumerate(gercek.items()):
            yol=Path(td)/f"p{i}.wav"
            with wave.open(str(yol),"wb") as wf:ses.synthesize_wav(metin,wf)
            sentetik[rid]=_wav_oku(yol)
        sure_piper=time.time()-sure_piper
        kayit=[{"id":"g-"+rid,"metin":m,"kaynak":"gercek"} for rid,(_,_,m,_) in gercek.items()]+[{"id":"s-"+rid,"metin":gercek[rid][2],"kaynak":"sentetik"} for rid in sentetik]
        bol=referans_bol(kayit,AYAR["test_orani"]);ogr_bol=bol_fn(copy.deepcopy(kayit),AYAR["test_orani"])
        test_rid=sorted({i[2:] for i in bol["test"]})
        sapi_yol=_sapi([gercek[r][2] for r in test_rid],td);sapi={r:_wav_oku(p) for r,p in zip(test_rid,sapi_yol)}
        diger=[v for v in _sapi_sesleri() if v!="Microsoft Zira Desktop"]          # eğitimde hiç görülmeyen ikinci bir sentetik ses (varsa)
        ikinci={}
        if diger:
            ikinci={r:_wav_oku(p) for r,p in zip(test_rid,_sapi([gercek[r][2] for r in test_rid],td,diger[0],"ikinci"))}
    rng=np.random.default_rng(AYAR["seed"]);H=AYAR["hz"];GH=AYAR["genis_hz"]
    def g16(rid):x,hz,_,_=gercek[rid];return x if hz==H else _yeniden(x,hz,H)
    def ozA(x,hz):return _ozellik(x,hz,GH/2)
    def ozB(x,hz):return _ozellik(x if hz==H else _yeniden(x,hz,H),H,H/2)
    egit_rid=sorted({i[2:] for i in bol["egitim"]})
    modeller={}
    for ad,oz in (("A_karisik_hz",lambda x,hz:ozA(x,hz)),("B_esit_hz",ozB)):
        X=[oz(g16(r),H) for r in egit_rid]+[oz(*sentetik[r]) for r in egit_rid];y=[0]*len(egit_rid)+[1]*len(egit_rid)
        modeller[ad]=(make_pipeline(StandardScaler(),LogisticRegression(max_iter=2000,C=1.0)).fit(np.array(X),y),oz)
    skorlar=[];satirlar=[]
    for ad,(mdl,oz) in modeller.items():
        for kosul in KOSULLAR:
            Xg=[];Xs=[]
            for r in test_rid:
                g=g16(r);sx,shz=sentetik[r]
                if kosul=="gurultu_20db":g=_gurultu(g,AYAR["snr_db"],rng);sx=_gurultu(sx,AYAR["snr_db"],rng)
                elif kosul=="telefon":g=_telefon(g,H);sx=_telefon(sx,shz)
                elif kosul=="ornekleme_16k":sx=_yeniden(sx,shz,H);shz=H
                elif kosul=="sapi":sx,shz=sapi[r]
                Xg.append(oz(g,H));Xs.append(oz(sx,shz))
            p=mdl.predict_proba(np.array(Xg+Xs))[:,1]
            sk=[round(float(v),6) for v in p];et=[0]*len(Xg)+[1]*len(Xs)
            skorlar.append({"model":ad,"kosul":kosul,"skorlar":sk,"etiketler":et})
            m=referans_metrik(sk,et,AYAR["esik"]);e=referans_eer(sk,et)
            satirlar.append({"model":ad,"kosul":kosul,"tpr":m["tpr"],"fpr":m["fpr"],"eer":e["eer"]})
    # Konuşmacı kısayolu sondası: aynı gerçek kayıtlar yalnız tını/perde değiştirilerek (bant hızı, sentez yok) verilir; dedektör onları
    # 'sentetik' sayıyorsa sentez izini değil tek gerçek konuşmacının sesini öğrenmiştir. İkinci SAPI sesi de eğitimde görülmemiş sentetiktir.
    sonda={};sonda_metrik_ayni=True
    for ad,(mdl,oz) in modeller.items():
        sonda[ad]={}
        Xg=[oz(g16(r),H) for r in test_rid];Xs=[oz(*sentetik[r]) for r in test_rid]
        for etk,f in (("perde_asagi_0.85",0.85),("perde_yukari_1.18",1.18)):
            Xp=[oz(_yeniden(g16(r),H,int(round(H/f))),H) for r in test_rid]            # gerçek (0): perdesi kaydırılmış; sentetik (1): Piper
            sk=[round(float(v),6) for v in mdl.predict_proba(np.array(Xp+Xs))[:,1]];et=[0]*len(Xp)+[1]*len(Xs)
            m=referans_metrik(sk,et,AYAR["esik"]);sonda_metrik_ayni=sonda_metrik_ayni and metrik_fn(list(sk),list(et),AYAR["esik"])==m
            sonda[ad][etk]={"fpr":m["fpr"]}
        if ikinci:
            Xi=[oz(*ikinci[r]) for r in test_rid]                                     # gerçek (0): asıl kayıtlar; sentetik (1): ikinci SAPI sesi
            sk=[round(float(v),6) for v in mdl.predict_proba(np.array(Xg+Xi))[:,1]];et=[0]*len(Xg)+[1]*len(Xi)
            m=referans_metrik(sk,et,AYAR["esik"]);sonda_metrik_ayni=sonda_metrik_ayni and metrik_fn(list(sk),list(et),AYAR["esik"])==m
            sonda[ad]["ikinci_sapi_sesi"]={"ses":diger[0],"tpr":m["tpr"]}
        sonda[ad]["temiz_fpr"]=next(s["fpr"] for s in satirlar if s["model"]==ad and s["kosul"]=="temiz")
    sapi_tpr=[s["tpr"] for s in satirlar if s["kosul"]=="sapi"]
    piper_izi=bool(all(v[e]["fpr"]<=0.2 for v in sonda.values() for e in ("perde_asagi_0.85","perde_yukari_1.18")) and max(sapi_tpr)<=0.5)
    return {"konusmaci_sondasi":sonda,"konusmaci_sondasi_metrik_ayni":bool(sonda_metrik_ayni),"piper_izi_ogrenildi":piper_izi,"surumler":{"piper_tts":"1.8.0","onnxruntime":__import__("onnxruntime").__version__,"sklearn":__import__("sklearn").__version__,"numpy":np.__version__},
            "dosya_sha256":{p.name:h for p,h in SHA.items()},"ayarlar":AYAR,
            "gercek":[{"id":rid,"hz":hz,"saniye":round(len(x)/hz,3),"konusmaci":sp,"metin":m} for rid,(x,hz,m,sp) in gercek.items()],
            "sentetik_hz":sorted({hz for _,hz in sentetik.values()}),"sapi_hz":sorted({hz for _,hz in sapi.values()}),"sapi_sesi":"Microsoft Zira Desktop",
            "piper_sure_sn":round(sure_piper,1),"toplam_sure_sn":round(time.time()-t0,1),
            "kayitlar":kayit,"bol":ogr_bol,"bol_referans":bol,"egitim_metin":len(egit_rid),"test_metin":len(test_rid),
            "skorlar":skorlar,
            "metrik":[metrik_fn(list(s["skorlar"]),list(s["etiketler"]),AYAR["esik"]) for s in skorlar],"metrik_referans":[referans_metrik(s["skorlar"],s["etiketler"],AYAR["esik"]) for s in skorlar],
            "eer":[eer_fn(list(s["skorlar"]),list(s["etiketler"])) for s in skorlar],"eer_referans":[referans_eer(s["skorlar"],s["etiketler"]) for s in skorlar],
            "satirlar":satirlar,"rapor":rapor_fn(copy.deepcopy(satirlar)),"rapor_referans":referans_rapor(satirlar),
            "olcum":"Skor: lojistik regresyonun 'sentetik' olasılığı. Eğitim yalnız temiz eğitim metinlerinde (gerçek LibriSpeech + Piper). Test metinleri eğitimde hiç yok. A modeli Piper'ı 22050 Hz'de, gerçeği 16000 Hz'de görür (0-11025 Hz bantları); B ikisini de 16000 Hz'de görür. Koşullar test kümesinde: gürültü (20 dB SNR) ve telefon bandı iki sınıfa da, ornekleme_16k yalnız sentetiğe, sapi sentetik yerine Windows SAPI Zira sesi.",
            "sinir":"Tek gerçek konuşmacı (LibriSpeech dummy, speaker 1272), tek Piper sesi (LJSpeech) ve en çok iki SAPI sesi, 45 kısa metin, basit spektral özellikler ve lojistik regresyon. Konuşmacı kısayolu, gerçek sesin perdesini bant hızıyla değiştiren bir sondayla ölçülür; bu işlem tempo da değiştirir ve gerçek başka konuşmacıların yerini tutmaz. Genel deepfake ya da ses klonlama tespit başarısını göstermez."}

def goster(bol_fn,metrik_fn,eer_fn,rapor_fn):
    r=deney(bol_fn,metrik_fn,eer_fn,rapor_fn)
    print("Sürümler:",r["surumler"],"| eğitim/test metin:",r["egitim_metin"],r["test_metin"],"| süre:",r["toplam_sure_sn"],"sn")
    for s in r["satirlar"]:print(f"  {s['model']:<13} {s['kosul']:<14} tpr={s['tpr']:.3f} fpr={s['fpr']:.3f} eer={s['eer']:.3f}")
    print("Senin raporun · kırılgan modeller:",r["rapor"].get("kirilgan") if isinstance(r["rapor"],dict) else r["rapor"])
    print("Sınır:",r["sinir"])
    print("Kanıt:",ai_lab.kanit_yaz("saldiri55-run",{"kaynak":"gercek","kabul":False,"ders":"ai-saldiri-55","deney":r}))
