"""C2PA manifest signing/validation with the approved local c2patool 0.28.4 and an LSB watermark on the same synthetic PNG. Test certificates only."""
import copy,datetime,hashlib,io,json,os,re,secrets,shutil,subprocess,tempfile
from pathlib import Path
import ai_lab

KOK=Path(__file__).resolve().parents[1]
ARAC=KOK/".deps/c2patool-0.28.4/acik/c2patool"
EXE=ARAC/"c2patool.exe"
EXE_SHA="9a44720109bd9901160e01ced0e19d55bc6817b9751bf427c7ce8774bf988e98"
DURUMLAR=("manifest-yok","gecersiz","gecerli-guvenilmeyen","guvenilen")
DONUSUMLER=("imzali","meta_eklendi","png_yeniden","jpeg_q85","olcek_yarim","saldirgan_imzali")
AYAR={"boyut":[96,64],"bit":32,"tekrar":5,"esik":0.1,"jpeg_kalite":85}
DURUM_ESLE={"Trusted":"guvenilen","Valid":"gecerli-guvenilmeyen","Invalid":"gecersiz"}

def _sha(b):
    return hashlib.sha256(b).hexdigest()

def referans_durum(okuma):
    if not isinstance(okuma,dict) or set(okuma)!={"rc","stdout","stderr"}:raise ValueError("şema")
    if type(okuma["rc"]) is not int or not isinstance(okuma["stdout"],str) or not isinstance(okuma["stderr"],str):raise ValueError("alan")
    if okuma["rc"]:
        if "No claim found" in okuma["stderr"]:return {"durum":"manifest-yok","hatalar":[],"imzaci":None}
        raise ValueError("araç hatası")
    j=json.loads(okuma["stdout"])
    if not isinstance(j,dict) or j.get("validation_state") not in DURUM_ESLE:raise ValueError("durum")
    si=j["manifests"][j["active_manifest"]]["signature_info"]
    hata=sorted({f["code"] for f in j.get("validation_results",{}).get("activeManifest",{}).get("failure",[])})
    return {"durum":DURUM_ESLE[j["validation_state"]],"hatalar":hata,"imzaci":{"issuer":si.get("issuer"),"common_name":si.get("common_name")}}

def _dogrula(degerler,n,tekrar):
    if not isinstance(degerler,list) or any(type(v) is not int or not 0<=v<=255 for v in degerler):raise ValueError("değerler")
    if type(n) is not int or n<1 or type(tekrar) is not int or tekrar<1 or tekrar%2==0:raise ValueError("n/tekrar")
    if n*tekrar>len(degerler):raise ValueError("kapasite")

def referans_gom(degerler,bitler,tekrar):
    if not isinstance(bitler,list) or any(type(b) is not int or b not in (0,1) for b in bitler):raise ValueError("bitler")
    _dogrula(degerler,len(bitler),tekrar)
    y=list(degerler)
    for i,b in enumerate(bitler):
        for r in range(tekrar):y[i*tekrar+r]=(y[i*tekrar+r]&254)|b
    return y

def referans_oku(degerler,n,tekrar):
    _dogrula(degerler,n,tekrar)
    return [int(sum(degerler[i*tekrar+r]&1 for r in range(tekrar))*2>tekrar) for i in range(n)]

def referans_rapor(kayitlar,esik):
    if type(esik) not in (int,float) or not 0<=esik<=1:raise ValueError("eşik")
    if not isinstance(kayitlar,list) or not kayitlar:raise ValueError("liste")
    ids=set();sat=[]
    for k in kayitlar:
        if not isinstance(k,dict) or set(k)!={"id","varsayilan","test_kok","ber"}:raise ValueError("şema")
        if not isinstance(k["id"],str) or not k["id"] or k["id"] in ids:raise ValueError("id")
        if k["varsayilan"] not in DURUMLAR or k["test_kok"] not in DURUMLAR:raise ValueError("durum")
        if type(k["ber"]) not in (int,float) or not 0<=k["ber"]<=1:raise ValueError("ber")
        ids.add(k["id"])
        c="yok" if k["varsayilan"]=="manifest-yok" else "bozuk" if k["varsayilan"]=="gecersiz" else "imzali"
        sat.append({"id":k["id"],"c2pa":c,"guvenilen":k["test_kok"]=="guvenilen","filigran_kaldi":k["ber"]<=esik})
    sat.sort(key=lambda s:s["id"])
    return {"satirlar":sat,"yalniz_filigran":[s["id"] for s in sat if s["c2pa"]=="yok" and s["filigran_kaldi"]],
            "hicbiri":[s["id"] for s in sat if s["c2pa"]=="yok" and not s["filigran_kaldi"]],
            "imzali_guvenilmeyen":[s["id"] for s in sat if s["c2pa"]=="imzali" and not s["guvenilen"]]}

def _sertifika(dizin):
    from cryptography import x509
    from cryptography.x509.oid import NameOID,ExtendedKeyUsageOID
    from cryptography.hazmat.primitives import hashes,serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    simdi=datetime.datetime.now(datetime.timezone.utc);ku=dict(content_commitment=False,key_encipherment=False,data_encipherment=False,key_agreement=False,encipher_only=False,decipher_only=False)
    cak=ec.generate_private_key(ec.SECP256R1());can=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,"Saldirgan Kok")])
    ca=(x509.CertificateBuilder().subject_name(can).issuer_name(can).public_key(cak.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(simdi-datetime.timedelta(days=1)).not_valid_after(simdi+datetime.timedelta(days=30))
        .add_extension(x509.BasicConstraints(ca=True,path_length=None),critical=True).add_extension(x509.SubjectKeyIdentifier.from_public_key(cak.public_key()),critical=False)
        .add_extension(x509.KeyUsage(digital_signature=False,key_cert_sign=True,crl_sign=True,**ku),critical=True).sign(cak,hashes.SHA256()))
    sk=ec.generate_private_key(ec.SECP256R1())
    sc=(x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,"Haber Ajansi (sahte)"),x509.NameAttribute(NameOID.ORGANIZATION_NAME,"Sahte Org")]))
        .issuer_name(can).public_key(sk.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(simdi-datetime.timedelta(days=1)).not_valid_after(simdi+datetime.timedelta(days=30))
        .add_extension(x509.BasicConstraints(ca=False,path_length=None),critical=True)
        .add_extension(x509.KeyUsage(digital_signature=True,key_cert_sign=False,crl_sign=False,**ku),critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.EMAIL_PROTECTION]),critical=False)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(sk.public_key()),critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(cak.public_key()),critical=False).sign(cak,hashes.SHA256()))
    (dizin/"saldirgan.key").write_bytes(sk.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
    (dizin/"saldirgan.pem").write_bytes(sc.public_bytes(serialization.Encoding.PEM)+ca.public_bytes(serialization.Encoding.PEM))

def _manifest(anahtar,sertifika):
    return {"claim_generator_info":[{"name":"PaftaLab","version":"0.1"}],"title":"kaynak.png","alg":"es256","private_key":anahtar,"sign_cert":sertifika,
            "assertions":[{"label":"c2pa.actions","data":{"actions":[{"action":"c2pa.created","digitalSourceType":"http://cv.iptc.org/newscodes/digitalsourcetype/digitalCreation"}]}}]}

def _png_metin_ekle(veri,anahtar,metin):
    import struct,zlib
    govde=anahtar.encode("latin-1")+b"\0"+metin.encode("latin-1");i=veri.rindex(b"IEND")-4
    parca=struct.pack(">I",len(govde))+b"tEXt"+govde+struct.pack(">I",zlib.crc32(b"tEXt"+govde)&0xFFFFFFFF)
    return veri[:i]+parca+veri[i:]

METIN={"gamma":0.25,"delta":2.0,"uzunluk":120,"anahtar":3737,"bozma":0.3,
       "istemler":["The history of the old harbor town","A short guide to keeping bees","Scientists studying the deep ocean",
                   "When the new library opened its doors"]}

def _metin_filigrani():
    """Üretken model filigranı (Kirchenbauer vd. 2023): her adımda önceki tokena ve gizli anahtara bağlı bir 'yeşil liste' (sözlüğün
    %25'i) seçilir ve bu tokenların logitine δ eklenir. Tespit yalnız tokenlara bakar: yeşil token sayısının z skoru."""
    import torch
    from transformers import LogitsProcessor,LogitsProcessorList
    tok,model,bilgi=ai_lab.dil_modeli()
    V=model.config.vocab_size;g_n=int(METIN["gamma"]*V)
    def yesil(onceki):
        g=torch.Generator().manual_seed(METIN["anahtar"]*1000003+int(onceki))
        return torch.randperm(V,generator=g)[:g_n]
    class Yesil(LogitsProcessor):
        def __call__(self,input_ids,scores):
            for b in range(scores.shape[0]):
                scores[b,yesil(input_ids[b,-1]).to(scores.device)]+=METIN["delta"]
            return scores
    def z(ids):
        y=sum(int(t in set(yesil(o).tolist())) for o,t in zip(ids[:-1],ids[1:]))
        T=len(ids)-1
        return (y-METIN["gamma"]*T)/((T*METIN["gamma"]*(1-METIN["gamma"]))**0.5)
    rnd=__import__("random").Random(METIN["anahtar"])
    sonuc={"filigranli":[],"filigransiz":[],"bozulmus":[]}
    for i,s in enumerate(METIN["istemler"]):
        on=tok(s,return_tensors="pt").input_ids
        for ad,isl in (("filigranli",LogitsProcessorList([Yesil()])),("filigransiz",None)):
            torch.manual_seed(i)
            with torch.no_grad():
                c=model.generate(on,max_new_tokens=METIN["uzunluk"],min_new_tokens=METIN["uzunluk"],do_sample=True,top_k=0,logits_processor=isl,
                                 pad_token_id=tok.eos_token_id)
            ids=c[0,on.shape[1]-1:].tolist()
            sonuc[ad].append(z(ids))
            if ad=="filigranli":
                b=[t if rnd.random()>METIN["bozma"] else rnd.randrange(V) for t in ids]
                sonuc["bozulmus"].append(z(b))
    ort={k:sum(v)/len(v) for k,v in sonuc.items()}
    return {"model":bilgi.get("model"),"ayar":{k:v for k,v in METIN.items() if k!="istemler"},"z":sonuc,"z_ortalama":ort}

def deney(durum_fn,gom_fn,oku_fn,rapor_fn):
    if os.name!="nt":raise ai_lab.GercekLabYok("Bu ders Windows c2patool 0.28.4 binary'sini kullanır.")
    if not EXE.is_file() or _sha(EXE.read_bytes())!=EXE_SHA:raise ai_lab.GercekLabYok("Onaylı c2patool 0.28.4 .deps/c2patool-0.28.4 altında yok ya da SHA256 farklı; otomatik indirme yok.")
    from PIL import Image,ImageDraw
    ayar_dosyasi=Path(os.environ.get("APPDATA",""),"c2pa","c2pa.toml")
    with tempfile.TemporaryDirectory(prefix="pafta-c2pa-") as td:
        W=Path(td)
        for ad in ("es256_private.key","es256_certs.pem","trust_anchors.pem"):shutil.copy(ARAC/"sample"/ad,W/ad)
        def arac(*a):
            r=subprocess.run([str(EXE),*map(str,a)],cwd=W,capture_output=True,text=True,encoding="utf-8",timeout=60,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
            return {"rc":r.returncode,"stdout":r.stdout,"stderr":r.stderr}
        surum=arac("--version")["stdout"].strip()
        w,h=AYAR["boyut"];img=Image.new("RGB",(w,h));px=img.load()
        for x in range(w):
            for y in range(h):px[x,y]=(x*4%256,y*5%256,(x*y)%256)
        bitler=[secrets.randbelow(2) for _ in range(AYAR["bit"])]
        R=list(img.getchannel("R").getdata());isaretli=referans_gom(R,bitler,AYAR["tekrar"]);ogrenci_gom=gom_fn(list(R),list(bitler),AYAR["tekrar"])
        img.putdata([(r,g,b) for r,(_,g,b) in zip(isaretli,img.getdata())]);img.save(W/"kaynak.png")
        (W/"man.json").write_text(json.dumps(_manifest("es256_private.key","es256_certs.pem")),encoding="utf-8")
        imza=arac("kaynak.png","-m","man.json","-o","imzali.png","-f")
        if imza["rc"]:raise ai_lab.GercekLabYok("c2patool imzalayamadı: "+imza["stderr"][:200])
        imzali=(W/"imzali.png").read_bytes()
        (W/"meta_eklendi.png").write_bytes(_png_metin_ekle(imzali,"Comment","sonradan eklendi"))
        Image.open(io.BytesIO(imzali)).save(W/"png_yeniden.png")
        Image.open(io.BytesIO(imzali)).convert("RGB").save(W/"jpeg_q85.jpg",quality=AYAR["jpeg_kalite"])
        Image.open(io.BytesIO(imzali)).resize((w//2,h//2)).resize((w,h)).save(W/"olcek_yarim.png")
        s=Image.open(io.BytesIO(imzali)).convert("RGB");ImageDraw.Draw(s).rectangle([0,h-8,w-1,h-1],fill=(255,0,0));s.save(W/"degistirilmis.png")
        _sertifika(W);(W/"sald.json").write_text(json.dumps(_manifest("saldirgan.key","saldirgan.pem")),encoding="utf-8")
        si=arac("degistirilmis.png","-m","sald.json","-o","saldirgan_imzali.png","-f")
        if si["rc"]:raise ai_lab.GercekLabYok("saldırgan imzası oluşturulamadı: "+si["stderr"][:200])
        dosya={"imzali":"imzali.png","meta_eklendi":"meta_eklendi.png","png_yeniden":"png_yeniden.png","jpeg_q85":"jpeg_q85.jpg","olcek_yarim":"olcek_yarim.png","saldirgan_imzali":"saldirgan_imzali.png"}
        okumalar=[];degerler={}
        for d in DONUSUMLER:
            for kip,ek in (("varsayilan",()),("test_kok",("trust","--trust_anchors","trust_anchors.pem"))):
                okumalar.append({"id":d,"kip":kip,"okuma":arac(dosya[d],*ek)})
            degerler[d]=list(Image.open(W/dosya[d]).convert("RGB").getchannel("R").getdata())
        dosya_sha={d:_sha((W/f).read_bytes()) for d,f in dosya.items()}
    durum_ref=[referans_durum(o["okuma"]) for o in okumalar]
    oku_ref={d:referans_oku(v,AYAR["bit"],AYAR["tekrar"]) for d,v in degerler.items()}
    ber={d:sum(a!=b for a,b in zip(oku_ref[d],bitler))/AYAR["bit"] for d in DONUSUMLER}
    dm={(o["id"],o["kip"]):r["durum"] for o,r in zip(okumalar,durum_ref)}
    kayit=[{"id":d,"varsayilan":dm[(d,"varsayilan")],"test_kok":dm[(d,"test_kok")],"ber":ber[d]} for d in DONUSUMLER]
    MF=_metin_filigrani();mz=MF["z_ortalama"]
    return {"metin_filigrani":MF,
            "metin_filigrani_dayanikli":bool(min(MF["z"]["filigranli"])>=4 and max(abs(x) for x in MF["z"]["filigransiz"])<=2.5
                                             and mz["bozulmus"]>=2.5 and mz["bozulmus"]<mz["filigranli"]),"arac":{"surum":surum,"exe_sha256":EXE_SHA,"kaynak":"https://github.com/contentauth/c2patool/releases/tag/v0.28.4"},"kullanici_ayar_dosyasi_vardi":ayar_dosyasi.exists(),
            "ayarlar":AYAR,"bitler":bitler,"dosya_sha256":dosya_sha,"imza_stderr":imza["stderr"],"saldirgan_imza_stderr":si["stderr"],
            "okumalar":okumalar,"durum":[durum_fn(copy.deepcopy(o["okuma"])) for o in okumalar],"durum_referans":durum_ref,
            "gom":ogrenci_gom,"gom_referans":isaretli,
            "oku":{d:oku_fn(list(v),AYAR["bit"],AYAR["tekrar"]) for d,v in degerler.items()},"oku_referans":oku_ref,"ber":ber,
            "kayitlar":kayit,"rapor":rapor_fn(copy.deepcopy(kayit),AYAR["esik"]),"rapor_referans":referans_rapor(kayit,AYAR["esik"]),
            "olcum":"c2pa durumu c2patool çıktısındaki validation_state'ten okunur: Trusted=guvenilen, Valid=gecerli-guvenilmeyen, Invalid=gecersiz; 'No claim found'=manifest-yok. test_kok kipi yalnız c2patool'un örnek TEST kök sertifikasını güvenilir sayar. ber: R kanalındaki LSB filigranın çoğunluk oylamasıyla okunan bitlerinin gömülen rastgele bitlerden farklı olma oranı.",
            "sinir":"Tek sentetik 96x64 PNG, c2patool 0.28.4, örnek TEST sertifikaları ve yerel saldırgan sertifikası; üretim güven listesini, gerçek kamera/yayıncı imzalarını, başka dosya türlerini ve dayanıklı (robust) ticari görüntü filigranlarını ölçmez. Metin filigranı küçük bir modelde dört kısa metinle denenir; rastgele token değiştirme gerçek bir parafrazdan zayıf bir saldırıdır (bir LLM ile yeniden yazma filigranı çok daha fazla siler)."}

def goster(durum_fn,gom_fn,oku_fn,rapor_fn):
    r=deney(durum_fn,gom_fn,oku_fn,rapor_fn)
    print("Araç:",r["arac"]["surum"],"| gömülen bitler:","".join(map(str,r["bitler"])))
    for o,d in zip(r["okumalar"],r["durum"]):print(f"  {o['id']:<17} {o['kip']:<10} rc={o['okuma']['rc']} → {d}")
    print("BER:",r["ber"])
    print("Senin raporun:",{k:v for k,v in r["rapor"].items() if k!="satirlar"} if isinstance(r["rapor"],dict) else r["rapor"])
    print("Sınır:",r["sinir"])
    print("Kanıt:",ai_lab.kanit_yaz("savunma37-run",{"kaynak":"gercek","kabul":False,"ders":"ai-savunma-37","deney":r}))
