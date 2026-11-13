"""Saldırı51 hazırlığı: gerçek lab imajı yoksa kesin olarak yapılmadı döner; indirme yok."""
import json,subprocess,shutil
import ai_lab
VERSIONS=("2.1.1","2.2.1")
def referans_rapor(kayitlar):
    out={v:{} for v in VERSIONS}
    for k in kayitlar:out[k["surum"]][k["tur"]]=k["bulgu"]
    normal=all(x["normal"]=="okundu" for x in out.values())
    return {"surumler":out,"normal_akis":normal,"deney_tamam":normal and all(x["yerel-kaynak"] in ("okundu","reddedildi") for x in out.values()),"yama_gozlendi":normal and out["2.1.1"]["yerel-kaynak"]=="okundu" and out["2.2.1"]["yerel-kaynak"]=="reddedildi"}
def on_kontrol():
    exe=shutil.which("docker")
    if not exe:raise ai_lab.GercekLabYok("Docker CLI yok;kurulum onayı gerekir")
    images=[]
    for v in VERSIONS:
        tag="pafta-ai-s51:mlflow-"+v
        p=subprocess.run([exe,"image","inspect",tag],capture_output=True,text=True,timeout=20,creationflags=ai_lab.NO_WINDOW)
        if p.returncode:raise ai_lab.GercekLabYok(tag+" bulunamadı veya Docker daemonuna erişilemiyor. Ders otomatik indirme/build yapmaz;SALDIRI-51-KURULUM-ONAYI.md")
        images.append(json.loads(p.stdout)[0])
    return exe,images
CLIENT = """
import sys,json,time,urllib.request,urllib.error
payload=json.load(sys.stdin)
url='http://127.0.0.1:5000'+payload['path']
data=payload.get('body');body=json.dumps(data).encode() if data is not None else None
req=urllib.request.Request(url,data=body,headers={'Content-Type':'application/json'},method=payload.get('method','GET'))
try:
 with urllib.request.urlopen(req,timeout=15) as res:status=res.status;raw=res.read(1048576).decode('utf-8','replace')
except urllib.error.HTTPError as exc:status=exc.code;raw=exc.read(1048576).decode('utf-8','replace')
print(json.dumps({'status':status,'govde':raw}))
"""

def _command(exe,args,*,input=None,timeout=30):
    p=subprocess.run([exe,*args],input=input,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout,creationflags=ai_lab.NO_WINDOW)
    if p.returncode:raise RuntimeError('Docker komutu başarısız: '+p.stderr[-2000:])
    return p.stdout

def _request(exe,cid,path,body=None):
    import base64
    payload=json.dumps({'path':path,'method':'POST' if body is not None else 'GET','body':body})
    # stdin is JSON, the executable snippet is fixed; learner input is never shell code.
    return json.loads(_command(exe,['exec','-i',cid,'python','-c',CLIENT],input=payload))

def _bulgu(res,canary):
    if res['status']==200:return 'okundu' if res['govde']==canary else 'uyusmazlik'
    if 400<=res['status']<500:return 'reddedildi'
    return 'hata'

def deney(fn):
    import secrets,time,copy,urllib.parse
    exe,images=on_kontrol();canary='PAFTA-'+secrets.token_hex(12);normal='NORMAL-'+secrets.token_hex(12)
    records=[];environments=[];requests=[];errors=[]
    for version,image in zip(VERSIONS,images):
        if (image.get('Config',{}).get('Labels') or {}).get('org.pafta.lesson')!='ai-saldiri-51':raise ai_lab.GercekLabYok('İmaj lab etiketi yok;kurulum ve kaynağı doğrulayın')
        cid=None;env={'surum':version,'image_id':image['Id'],'image_digests':image.get('RepoDigests'), 'izolasyon_dogrulandi':False,'temizlendi':False};environments.append(env)
        try:
            cid=_command(exe,['run','-d','--pull=never','--network','none','--read-only','--user','10001:10001','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','256','--memory','1g','--cpus','2','--tmpfs','/tmp:rw,nosuid,nodev,uid=10001,gid=10001,size=268435456','--label','org.pafta.lesson=ai-saldiri-51','-e','PAFTA_CANARY='+canary,'-e','PAFTA_NORMAL='+normal,image['Id']]).strip()
            env['container_id']=cid
            inspect=json.loads(_command(exe,['inspect',cid]))[0];host=inspect['HostConfig']
            env['runtime_inspect']={k:host.get(k) for k in ('NetworkMode','ReadonlyRootfs','PortBindings','Binds','CapDrop','SecurityOpt','Memory','NanoCpus','PidsLimit','Tmpfs')}
            env['izolasyon_dogrulandi']=host['NetworkMode']=='none' and host['ReadonlyRootfs'] and not host.get('PortBindings') and not host.get('Binds') and inspect['Config']['User']=='10001:10001' and 'ALL' in host.get('CapDrop',[]) and any(x.startswith('no-new-privileges') for x in host.get('SecurityOpt',[])) and not any(m.get('Type')=='bind' for m in inspect.get('Mounts',[]))
            if not env['izolasyon_dogrulandi']:raise RuntimeError('Runtime izolasyonu uyuşmuyor')
            ready=False;last=None
            for _ in range(40):
                try:
                    last=_request(exe,cid,'/health')
                    if last['status']==200:ready=True;break
                except Exception:pass
                time.sleep(.5)
            if not ready:raise RuntimeError('MLflow hazır olmadı: '+str(last))
            actual=_command(exe,['exec',cid,'python','-c','import mlflow;print(mlflow.__version__)']).strip();env['mlflow_surumu']=actual
            if actual!=version:raise RuntimeError('Gerçek MLflow sürümü yanlış')
            env['paketler']=_command(exe,['exec',cid,'cat','/opt/pafta-packages.txt'])
            for kind,source,witness in [('normal','mlflow-artifacts:/normal',normal),('yerel-kaynak','file:///tmp/pafta/private',canary)]:
                name='pafta-'+kind+'-'+secrets.token_hex(4)
                def req(path,body=None):
                    res=_request(exe,cid,path,body);requests.append({'surum':version,'tur':kind,'path':path,'method':'POST' if body is not None else 'GET','request_body':body,**res});return res
                created=req('/api/2.0/mlflow/registered-models/create',{'name':name})
                if created['status']!=200:raise RuntimeError('Registry create başarısız: '+str(created))
                cv=req('/api/2.0/mlflow/model-versions/create',{'name':name,'source':source})
                observed=cv
                if cv['status']==200:
                    number=json.loads(cv['govde'])['model_version']['version']
                    query=urllib.parse.urlencode({'name':name,'version':number,'path':'ok.txt' if kind=='normal' else 'canary.txt'})
                    observed=req('/model-versions/get-artifact?'+query)
                records.append({'surum':version,'tur':kind,'bulgu':_bulgu(observed,witness)})
        except Exception as exc:
            errors.append({'surum':version,'tur':type(exc).__name__,'hata':str(exc)})
            if cid:
                try:env['server_log']=_command(exe,['logs',cid])[-8000:]
                except Exception:pass
        finally:
            if cid:
                try:
                    # Use only the returned exact ID, never a global stop/prune command.
                    _command(exe,['rm','-f',cid])
                    env['temizlendi']=subprocess.run([exe,'inspect',cid],capture_output=True,creationflags=ai_lab.NO_WINDOW).returncode!=0
                except Exception as exc:errors.append({'surum':version,'hata':'cleanup: '+str(exc)})
    reference=referans_rapor(records) if len(records)==4 else None
    report=fn(copy.deepcopy(records)) if len(records)==4 else None
    return {'kayitlar':records,'rapor':report,'referans':reference,'ortamlar':environments,'http_kayitlari':requests,'hatalar':errors,'canary':canary,'normal_isaret':normal,'cve':'CVE-2023-1177','ayarlar':{'network':'none','memory':'1g','cpus':2,'pid_limit':256,'seed':'OS entropy; canary kayıtta','kurulum':'önceden onaylanmış imaj; ders build/pull yapmaz'}}

def goster(fn):
    r=deney(fn)
    print('GERÇEK MLflow HTTP kayıtları:',r['kayitlar'])
    print('Rapor:',r['rapor'],'Hatalar:',r['hatalar'])
    print('Kanıt:',ai_lab.kanit_yaz('saldiri51-run',{'kaynak':'gercek','kabul':False,'ders':'ai-saldiri-51','deney':r}))
