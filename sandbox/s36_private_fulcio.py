"""S36 private local Fulcio lifecycle. Requires separately approved official binary.
No public Sigstore services, public transparency log, persistent identity or OS trust changes.
Starts the real service in network-none Docker; only our localhost/docker-exec relay reaches it.
Experiment receipts and policy checks belong to the calling lesson.
"""
import base64,hashlib,io,json,os,re,secrets,socket,subprocess,tarfile,tempfile,time,urllib.error,urllib.request,threading,http.server
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FULCIO=ROOT/'.deps/fulcio-v1.9.1-linux-amd64/fulcio'
FULCIO_SHA='d851e6fcc33bad57a08435e41fe082d8cc466f99c57d2fae156e82941f84ea31'
IMAGE=os.environ.get('PAFTA_S36_IMAGE','pafta-ai-s51:mlflow-2.1.1')
ISSUER='http://127.0.0.1:5556'
IDENTITY='student@pafta.invalid'
def _b64(data):return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')
def _int(value):return _b64(value.to_bytes((value.bit_length()+7)//8,'big'))
def _sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
class LocalFulcio:
    def __init__(self):
        self.cid=None;self.nid=None;self.port=None;self.logs=[];self.cleaned=False;self.version='v1.9.1';self.work=None;self.token=None;self.relay=None;self.relay_thread=None;self.requests=[]
    def docker(self,*args,data=None,timeout=40):
        r=subprocess.run(['docker',*args],input=data,capture_output=True,timeout=timeout,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        # Commands never carry the identity token or a private key.
        self.logs.append({'argv':list(args),'returncode':r.returncode,'stdout':r.stdout.decode('utf-8','replace'),'stderr':r.stderr.decode('utf-8','replace')})
        if r.returncode:raise RuntimeError('Docker '+args[0]+': '+r.stderr.decode('utf-8','replace')[:1000])
        return r.stdout.decode('utf-8','replace').strip()
    def __enter__(self):
        if not FULCIO.is_file() or _sha(FULCIO)!=FULCIO_SHA:raise RuntimeError('S36 gerçek keyless yapılmadı: onaylı Fulcio binary eksik/SHA256 farklı; otomatik indirme yok.')
        # Inspect exact existing image; no tag replacement or pull.
        image_info=json.loads(self.docker('image','inspect',IMAGE))[0]
        self.image_id=image_info['Id']
        if image_info.get('Os')!='linux' or image_info.get('Architecture')!='amd64':raise RuntimeError('Mevcut S36 tabanı linux/amd64 olmalı; otomatik pull yok.')
        from cryptography.hazmat.primitives.asymmetric import rsa,padding
        from cryptography.hazmat.primitives import hashes
        key=rsa.generate_private_key(public_exponent=65537,key_size=2048);pub=key.public_key().public_numbers();kid=secrets.token_hex(12)
        jwks={'keys':[{'kty':'RSA','use':'sig','kid':kid,'alg':'RS256','n':_int(pub.n),'e':_int(pub.e)}]}
        claims={'iss':ISSUER,'sub':'pafta-local-student','aud':'sigstore','exp':int(time.time())+900,'iat':int(time.time()),'email':IDENTITY,'email_verified':True}
        unsigned=_b64(json.dumps({'alg':'RS256','typ':'JWT','kid':kid},separators=(',',':')).encode())+'.'+_b64(json.dumps(claims,separators=(',',':')).encode())
        self.token=unsigned+'.'+_b64(key.sign(unsigned.encode(),padding.PKCS1v15(),hashes.SHA256()))
        self.work=Path(tempfile.mkdtemp(prefix='pafta-s36-keyless-'))
        self.token_path=self.work/'identity.jwt';self.token_path.write_text(self.token,encoding='utf-8')
        discovery={'issuer':ISSUER,'jwks_uri':ISSUER+'/jwks','authorization_endpoint':ISSUER+'/not-used','token_endpoint':ISSUER+'/not-used','response_types_supported':['id_token'],'subject_types_supported':['public'],'id_token_signing_alg_values_supported':['RS256']}
        config={'OIDCIssuers':{ISSUER:{'IssuerURL':ISSUER,'ClientID':'sigstore','Type':'email'}}}
        members={'supervisor.py':(Path(__file__).with_name('s36_keyless')/'supervisor.py').read_bytes(),'discovery.json':json.dumps(discovery).encode(),'jwks.json':json.dumps(jwks).encode(),'fulcio.json':json.dumps(config).encode(),'fulcio':FULCIO.read_bytes()}
        payload=io.BytesIO()
        with tarfile.open(fileobj=payload,mode='w') as tar:
            d=tarfile.TarInfo('pafta-s36');d.type=tarfile.DIRTYPE;d.mode=0o755;tar.addfile(d)
            for name,content in members.items():
                entry=tarfile.TarInfo('pafta-s36/'+name);entry.size=len(content);entry.mode=0o444;tar.addfile(entry,io.BytesIO(content))
        label='pafta-s36-'+secrets.token_hex(6)
        try:
            self.cid=self.docker('create','--pull=never','--name',label,'--label','org.pafta.lesson=ai-savunma-36','--network','none','--read-only','--user','10001:10001','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','128','--memory','512m','--cpus','2','--tmpfs','/tmp:rw,exec,nosuid,nodev,uid=10001,gid=10001,size=134217728','--tmpfs','/opt/pafta-s36:rw,nosuid,nodev,uid=10001,gid=10001,size=100663296',self.image_id,'python','-c','import time;time.sleep(3600)')
            self.docker('start',self.cid)
            loader="import sys,tarfile,pathlib,shutil,os; t=tarfile.open(fileobj=sys.stdin.buffer,mode='r|'); root=pathlib.Path('/opt/pafta-s36');\nfor e in t:\n if e.isdir():continue\n name=pathlib.PurePosixPath(e.name).name\n if e.name!='pafta-s36/'+name:raise ValueError('unexpected archive member')\n with (root/name).open('xb') as f:shutil.copyfileobj(t.extractfile(e),f)\n (root/name).chmod(0o444)"
            self.docker('exec','-i',self.cid,'python','-c',loader,data=payload.getvalue())
            self.docker('exec','--detach',self.cid,'python','/opt/pafta-s36/supervisor.py')
            self.inspect=json.loads(self.docker('inspect',self.cid))[0]
            host=self.inspect['HostConfig']
            assert host['NetworkMode']=='none' and host['ReadonlyRootfs'] and self.inspect['Config']['User']=='10001:10001'
            assert not host['PortBindings'] and host['Binds'] in (None,[])
            assert host['PidsLimit']==128 and host['Memory']==536870912 and host['NanoCpus']==2000000000
            assert 'ALL' in host['CapDrop'] and any('no-new-privileges' in x for x in host['SecurityOpt'])
            assert set(host['Tmpfs'])=={'/tmp','/opt/pafta-s36'} and all(m['Type']=='tmpfs' for m in self.inspect['Mounts'])
            self._start_relay()
            opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
            last=''
            for attempt in range(12):
                try:
                    with opener.open(self.url+'/api/v2/trustBundle',timeout=10) as response:self.trust=json.load(response)
                    break
                except (OSError,ValueError,urllib.error.URLError) as e:
                    last=str(e)
                    if attempt%5==0:
                        diagnostic=self.docker('exec',self.cid,'python','-c',"from pathlib import Path;p=Path('/tmp/pafta-s36/supervisor.error');print(p.read_text()[-1500:] if p.exists() else '')")
                        if diagnostic:raise RuntimeError('Local Fulcio supervisor: '+diagnostic)
                    time.sleep(.5)
            else:raise RuntimeError('Local Fulcio health failed: '+last)
            return self
        except BaseException:
            self.__exit__(None,None,None);raise

    def _start_relay(self):
        context=self
        # Forward only these public Fulcio API routes to the real loopback service.
        allowed={'/api/v2/trustBundle','/api/v2/signingCert','/api/v1/signingCert','/api/v1/rootCert'}
        client="""import sys,json,base64,urllib.request,urllib.error
q=json.load(sys.stdin)
req=urllib.request.Request('http://127.0.0.1:5555'+q['path'],data=base64.b64decode(q['body']) if q['method']=='POST' else None,headers=q['headers'],method=q['method'])
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
try:
 with opener.open(req,timeout=15) as r:out={'status':r.status,'body':base64.b64encode(r.read()).decode(),'type':r.headers.get('Content-Type','application/json')}
except urllib.error.HTTPError as r:out={'status':r.code,'body':base64.b64encode(r.read()).decode(),'type':r.headers.get('Content-Type','application/json')}
print(json.dumps(out))
"""
        class Relay(http.server.BaseHTTPRequestHandler):
            def handle_api(self):
                if self.path not in allowed:self.send_error(404);return
                try:size=int(self.headers.get('Content-Length','0'))
                except ValueError:self.send_error(400);return
                if not 0<=size<=1048576:self.send_error(413);return
                body=self.rfile.read(size)
                q={'path':self.path,'method':self.command,'body':base64.b64encode(body).decode(),'headers':{k:self.headers[k] for k in ('Authorization','Content-Type') if k in self.headers}}
                try:
                    text=context.docker('exec','-i',context.cid,'python','-c',client,data=json.dumps(q).encode())
                    result=json.loads(text);payload=base64.b64decode(result['body']);status=result['status']
                    safe=payload.decode('utf-8','replace')
                    if context.token:safe=safe.replace(context.token,'<lab-token-redacted>')
                    context.requests.append({'method':self.command,'path':self.path,'request_body_sha256':hashlib.sha256(body).hexdigest(),'status':status,'response':safe})
                    self.send_response(status);self.send_header('Content-Type',result['type']);self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
                except Exception as exc:
                    context.requests.append({'method':self.command,'path':self.path,'hata':type(exc).__name__+': '+str(exc)})
                    self.send_error(502,'local container relay failed')
            do_GET=handle_api
            do_POST=handle_api
            def log_message(self,*args):pass
        self.relay=http.server.ThreadingHTTPServer(('127.0.0.1',0),Relay);self.relay.daemon_threads=True
        self.port=self.relay.server_address[1];self.url=f'http://127.0.0.1:{self.port}'
        self.relay_thread=threading.Thread(target=self.relay.serve_forever,daemon=True);self.relay_thread.start()

    def __exit__(self,*args):
        errors=[]
        if self.relay:
            self.relay.shutdown();self.relay.server_close();self.relay_thread.join(timeout=2)
            if self.relay_thread.is_alive():errors.append('own relay did not stop')
        if self.cid:
            try:self.service_log=self.docker('exec',self.cid,'python','-c',"from pathlib import Path;import json;print(json.dumps({p.name:p.read_text(errors='replace')[-2000:] for p in Path('/tmp/pafta-s36').glob('*') if p.name in ('fulcio.stdout','fulcio.stderr','supervisor.error')}))")
            except Exception:self.service_log='diagnostic unavailable'
            try:
                self.docker('rm','--force',self.cid)
                r=subprocess.run(['docker','inspect',self.cid],capture_output=True,timeout=15,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));assert r.returncode!=0
            except Exception as e:errors.append(str(e))
        if self.nid:
            try:self.docker('network','rm',self.nid)
            except Exception as e:errors.append(str(e))
        # Token is synthetic/short-lived and never returned as evidence; remove only our own copy.
        if hasattr(self,'token_path'):
            self.token_path.unlink(missing_ok=True)
        self.token=None;self.cleaned=not errors;self.cleanup_errors=errors
    def public_evidence(self):
        # Redact logs defensively; no private JWT is intentionally in any command.
        return {'kaynak':'gercek','fulcio_surumu':self.version,'binary_sha256':FULCIO_SHA,'image_id':getattr(self,'image_id',None),'image_reference':IMAGE,'kendi_container':self.cid,'kendi_network':self.nid,'network':'none','transport':'localhost HTTP to real Fulcio via own docker-exec relay','http':self.requests,'izolasyon':getattr(self,'inspect',{}).get('HostConfig',{}),'issuer':ISSUER,'identity':IDENTITY,'fulcio_url':getattr(self,'url',None),'temizlendi':self.cleaned,'servis_log':getattr(self,'service_log',''),'cleanup_errors':getattr(self,'cleanup_errors',[]),'tlog':'yok: private lab sertifika/imza akışı; public şeffaflık iddiası yok'}
