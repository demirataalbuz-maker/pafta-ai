"""S36 real cosign key-pair and private Fulcio keyless lab. No automatic installation."""
import copy,hashlib,json,os,re,secrets,subprocess,tempfile,base64
from pathlib import Path
from sandbox import ai_gercek_lab as lab
from sandbox.s36_private_fulcio import LocalFulcio,FULCIO,FULCIO_SHA,IDENTITY,ISSUER
ROOT=Path(__file__).resolve().parents[1]
COSIGN=ROOT/'.deps/cosign-v3.1.4-windows-amd64/cosign.exe'
COSIGN_SHA='cbe953787074611f1334cbf37dc1cf953995bb8c45398eb4fc7bb781d29c1f2a'
def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def on_kontrol():
    if os.name!='nt':raise lab.GercekLabYok('Bu kurulum Windows cosign binary kullanır; diğer platform resmi binary envanteri ayrıca gerekir.')
    if not COSIGN.is_file() or sha(COSIGN)!=COSIGN_SHA:raise lab.GercekLabYok('Onaylı Cosign v3.1.4 eksik/SHA256 farklı; kurulum yapılmadı, otomatik indirme yok.')
    if not FULCIO.is_file() or sha(FULCIO)!=FULCIO_SHA:raise lab.GercekLabYok('Gerçek keyless için ayrıca onaylı Fulcio v1.9.1 gerekir; henüz kurulu değil/SHA256 farklı. Key-pair sonucu keyless kabulü değildir.')

def _model(base,seed):
    import torch
    from safetensors.torch import save_file,load_file
    torch.manual_seed(seed);torch.set_num_threads(2);x=torch.randn(80,4);y=(x[:,0]+x[:,1]>0).long()
    model=torch.nn.Linear(4,2);opt=torch.optim.SGD(model.parameters(),lr=.2)
    for _ in range(50):
        opt.zero_grad();loss=torch.nn.functional.cross_entropy(model(x),y);loss.backward();opt.step()
    path=base/'model.safetensors';save_file(dict(model.state_dict()),str(path));loaded=load_file(str(path))
    equal=all(torch.equal(value,loaded[key]) for key,value in model.state_dict().items())
    return path,{'tur':'torch.nn.Linear(4,2)','seed':seed,'cihaz':'cpu','egitim_adim':50,'girdi_shape':list(x.shape),'girdi_sha256':hashlib.sha256(x.numpy().tobytes()).hexdigest(),'girdi_ilk8':x[:8].tolist(),'etiket_ilk8':y[:8].tolist(),'loss':loss.item(),'accuracy':(model(x).argmax(1)==y).float().mean().item(),'yeniden_yukleme_esit':equal,'sha256':sha(path),'torch_surumu':torch.__version__}

def _deney(manifest_fn,identity_fn,report_fn,audit):
    runs=[];checks=[];environments=[];base=Path(tempfile.mkdtemp(prefix='pafta-s36-'))
    audit.update(kosular=runs,ortamlar=environments,calisma_klasoru=str(base))
    for repeat in range(2):
        case=base/('kosu-'+str(repeat));case.mkdir();rows=[];calls=[];seed=36+repeat
        audit['aktif']={'tekrar':repeat,'cagrilar':calls,'kayitlar':rows}
        artifact,model=_model(case,seed);audit['aktif']['model']=model;checks.append(model['yeniden_yukleme_esit'])
        env=dict(os.environ,COSIGN_PASSWORD=secrets.token_hex(20));local=LocalFulcio()
        def call(args,timeout=60):
            result=subprocess.run([str(COSIGN),*map(str,args)],cwd=case,env=env,capture_output=True,text=True,encoding='utf-8',timeout=timeout,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            stdout=result.stdout;stderr=result.stderr
            if local.token:stdout=stdout.replace(local.token,'<lab-token-redacted>');stderr=stderr.replace(local.token,'<lab-token-redacted>')
            calls.append({'argv':[str(a) for a in args],'returncode':result.returncode,'stdout':stdout,'stderr':stderr})
            return result
        def verify(name,args):
            r=call(args)
            # CLI syntax/configuration errors are never presented as a secure rejection.
            failure=r.stderr.lower()
            operational=not any(word in failure for word in ('unknown flag','unknown command','no such file','cannot find','connection refused','deadline exceeded','timed out','context deadline'))
            row={'vaka':name,'calisti':r.returncode in (0,1) and operational,'dogrulandi':r.returncode==0};rows.append(row)
            return row
        version=call(['version','--json']);checks.append(version.returncode==0)
        manifest={'dosya':artifact.name,'sha256':model['sha256']};before=copy.deepcopy(manifest)
        checks.append(manifest_fn(case,manifest) is True and manifest==before)
        damaged=case/'tampered.safetensors';bits=bytearray(artifact.read_bytes());bits[-1]^=1;damaged.write_bytes(bits)
        checks.append(manifest_fn(case,dict(manifest,dosya=damaged.name)) is False)
        for keyname in ('signer','other'):
            r=call(['generate-key-pair','--output-key-prefix',keyname]);checks.append(r.returncode==0)
            if r.returncode:raise RuntimeError('Key generation failed')
        sign=call(['sign-blob','--key','signer.key','--use-signing-config=false','--tlog-upload=false','--new-bundle-format=false','--output-signature','keypair.sig','--yes',artifact])
        checks.append(sign.returncode==0)
        if sign.returncode:raise RuntimeError('Key-pair signing failed')
        opts=['verify-blob','--key','signer.pub','--signature','keypair.sig','--new-bundle-format=false','--insecure-ignore-tlog=true']
        verify('keypair-normal',opts+[artifact]);verify('keypair-tahrifat',opts+[damaged])
        verify('keypair-baska-anahtar',['verify-blob','--key','other.pub','--signature','keypair.sig','--new-bundle-format=false','--insecure-ignore-tlog=true',artifact])
        try:
            with local:
                # All destinations are fixed loopback addresses from our private context.
                root_pem=local.trust['chains'][0]['certificates'][-1]
                root=case/'root.pem';root.write_text(root_pem,encoding='utf-8')
                configured=call(['trusted-root','create','--fulcio','url='+local.url+',certificate-chain=root.pem','--out','trusted-root.json'])
                checks.append(configured.returncode==0)
                if configured.returncode:raise RuntimeError('Private trusted-root creation failed')
                signed=call(['sign-blob','--use-signing-config=false','--tlog-upload=false','--new-bundle-format=false','--fulcio-url',local.url,'--trusted-root','trusted-root.json','--identity-token',local.token_path,'--insecure-skip-verify=true','--output-certificate','keyless.pem','--output-signature','keyless.sig','--yes',artifact])
                checks.append(signed.returncode==0)
                if signed.returncode:raise RuntimeError('Local keyless signing failed; raw command output in memory')
                from cryptography import x509
                from cryptography.x509.oid import ExtensionOID,ObjectIdentifier
                cert_bytes=(case/'keyless.pem').read_bytes()
                if not cert_bytes.startswith(b'-----BEGIN'):cert_bytes=base64.b64decode(cert_bytes,validate=True)
                (case/'keyless.pem').write_bytes(cert_bytes)
                cert=x509.load_pem_x509_certificate(cert_bytes)
                actual_id=cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME).value.get_values_for_type(x509.RFC822Name)[0]
                # Fulcio's legacy issuer extension is the raw issuer string.
                actual_issuer=cert.extensions.get_extension_for_oid(ObjectIdentifier('1.3.6.1.4.1.57264.1.1')).value.value.decode('utf-8')
                policy={'kimlik':IDENTITY,'issuer':ISSUER};checks.append(identity_fn(actual_id,actual_issuer,policy) is True)
                checks.append(identity_fn(actual_id,actual_issuer,dict(policy,kimlik='other@pafta.invalid')) is False)
                checks.append(identity_fn(actual_id,actual_issuer,dict(policy,issuer=ISSUER+'/different')) is False)
                common=['verify-blob','--signature','keyless.sig','--certificate','keyless.pem','--ca-roots','root.pem','--new-bundle-format=false','--insecure-ignore-tlog=true','--insecure-ignore-sct=true','--certificate-identity',IDENTITY,'--certificate-oidc-issuer',ISSUER]
                verify('keyless-normal',common+[artifact]);verify('keyless-tahrifat',common+[damaged])
                other_id=list(common);other_id[other_id.index(IDENTITY)]='other@pafta.invalid';verify('keyless-baska-kimlik',other_id+[artifact])
                other_issuer=list(common);other_issuer[other_issuer.index(ISSUER)]=ISSUER+'/different';verify('keyless-baska-issuer',other_issuer+[artifact])
                from cryptography.hazmat.primitives.asymmetric import ec
                from cryptography.hazmat.primitives import hashes,serialization
                from cryptography.x509.oid import NameOID
                from datetime import datetime,timezone,timedelta
                key=ec.generate_private_key(ec.SECP256R1());subject=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'Other PAFTA test root')]);now=datetime.now(timezone.utc)
                other=x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=1)).not_valid_after(now+timedelta(hours=1)).add_extension(x509.BasicConstraints(ca=True,path_length=None),critical=True).sign(key,hashes.SHA256())
                (case/'wrong-root.pem').write_bytes(other.public_bytes(serialization.Encoding.PEM));wrong_root=list(common);wrong_root[wrong_root.index('root.pem')]='wrong-root.pem';verify('keyless-baska-root',wrong_root+[artifact])
        finally:environments.append(local.public_evidence())
        reference=rapor_ref(rows);summary=report_fn(copy.deepcopy(rows));checks.append(summary==reference and reference['kabul'])
        runs.append({'tekrar':repeat,'model':model,'manifest':manifest,'sertifika_kimlik':actual_id,'sertifika_issuer':actual_issuer,'politikasi':policy,'kayitlar':rows,'ozet':summary,'cagrilar':calls,'artifact_sha256':sha(artifact),'tahrif_sha256':sha(damaged),'root_sha256':sha(root),'keyless_sig_sha256':sha(case/'keyless.sig'),'keypair_sig_sha256':sha(case/'keypair.sig')})
    audit.pop('aktif',None)
    cleaned=all(e['temizlendi'] for e in environments);checks.append(cleaned)
    checks.append(runs[0]['kayitlar']==runs[1]['kayitlar'])
    return {'kaynak':'gercek','cosign_sha256':COSIGN_SHA,'kosular':runs,'ortamlar':environments,'kontroller':checks,'temizlendi':cleaned,'calisma_klasoru':str(base),'cihaz':lab.cihaz(),'sinir':'Private test OIDC/Fulcio; CT/Rekor/timestamp yok, gerçek insan kimliği/public Sigstore iddiası yok. Private key/token kanıtta değil.'}

def deney(manifest_fn,identity_fn,report_fn):
    # Missing prerequisites are not a fixture or a real-experiment receipt.
    on_kontrol()
    audit={}
    try:return _deney(manifest_fn,identity_fn,report_fn,audit)
    except Exception as exc:
        actual=bool(audit.get('aktif',{}).get('cagrilar') or audit.get('kosular'))
        lab.kanit_yaz('savunma36-hata',dict(audit,kaynak='gercek' if actual else 'altyapi',kabul=False,hata=type(exc).__name__+': '+str(exc),notu='Tam gerçek kabul yapılmadı. Kısmi gerçek komutlar varsa ayrıca kaydedildi.'))
        raise

def goster(manifest_fn,identity_fn,report_fn):
    r=deney(manifest_fn,identity_fn,report_fn)
    for run in r['kosular']:print('Gerçek koşu:',run['tekrar'],run['ozet'],run['model'])
    print('Sınır:',r['sinir']);print('Kanıt:',lab.kanit_yaz('savunma36-run',dict(r,kabul=False)))

from pathlib import Path
import hashlib,re
def manifest_ref(klasor,manifest):
    try:
        if not isinstance(manifest,dict) or set(manifest)!={'dosya','sha256'}:return False
        name=manifest['dosya'];wanted=manifest['sha256']
        if not re.fullmatch(r'[A-Za-z0-9_-][A-Za-z0-9_.-]{0,79}\.safetensors',name):return False
        if not isinstance(wanted,str):return False
        root=Path(klasor).resolve(strict=True);path=root/name
        if path.is_symlink():return False
        with path.open('rb') as f:got=hashlib.file_digest(f,'sha256').hexdigest()
        return got==wanted
    except (OSError,TypeError,ValueError):return False

def kimlik_ref(kimlik,issuer,politika):
    if not isinstance(politika,dict) or set(politika)!={'kimlik','issuer'}:return False
    for value in (kimlik,issuer,politika['kimlik'],politika['issuer']):
        if not isinstance(value,str) or not value.strip():return False
    return kimlik==politika['kimlik'] and issuer==politika['issuer']

def rapor_ref(kayitlar):
    expected={'keypair-normal':True,'keypair-tahrifat':False,'keypair-baska-anahtar':False,'keyless-normal':True,'keyless-tahrifat':False,'keyless-baska-kimlik':False,'keyless-baska-issuer':False,'keyless-baska-root':False}
    if not isinstance(kayitlar,list) or len(kayitlar)!=8:raise ValueError('sekiz kayıt')
    seen=set();errors=[];wrong=[];verified=[]
    for row in kayitlar:
        if not isinstance(row,dict) or set(row)!={'vaka','calisti','dogrulandi'}:raise ValueError('şema')
        name=row['vaka']
        if name not in expected or name in seen or type(row['calisti']) is not bool or type(row['dogrulandi']) is not bool:raise ValueError('değer')
        seen.add(name)
        if not row['calisti']:errors.append(name)
        else:
            if row['dogrulandi']!=expected[name]:wrong.append(name)
            if row['dogrulandi']:verified.append(name)
    return {'kabul':not errors and not wrong,'hatalar':sorted(errors),'beklenmeyen':sorted(wrong),'dogrulanan':sorted(verified)}
