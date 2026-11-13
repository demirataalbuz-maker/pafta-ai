"""Saldırı51 kurulum aracı. --kontrol indirmez. --kur yalnız kullanıcı onayından sonra."""
from pathlib import Path
import argparse,subprocess,json,shutil,datetime,sys
ROOT=Path(__file__).resolve().parents[1]
VERSIONS=('2.1.1','2.2.1')
BASE='python:3.10-slim-bookworm@sha256:db6ee5170ebce0f4d165af242e8e77addc08bd9ffc37e8b1815752cf027aa4f8'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--kontrol',action='store_true');g.add_argument('--kur',action='store_true')
    args=p.parse_args();exe=shutil.which('docker')
    if not exe:raise SystemExit('Docker CLI yok; otomatik kurulum yapılmadı.')
    def call(params,**kw):
        return subprocess.run([exe,*params],encoding='utf-8',errors='replace',text=True,**kw)
    if args.kontrol:
        found=[]
        for v in VERSIONS:
            tag='pafta-ai-s51:mlflow-'+v;x=call(['image','inspect',tag],capture_output=True,timeout=20)
            good=False
            if x.returncode==0:
                meta=json.loads(x.stdout)[0]
                good=(meta.get('Config',{}).get('Labels') or {}).get('org.pafta.lesson')=='ai-saldiri-51'
            found.append(good);print(tag,':', 'kurulu (lab etiketi var)' if good else 'yok/etiket uyuşmuyor')
        print('İndirme/build yapılmadı; bu yalnız imaj kontrolüdür, gerçek CVE kabulü değildir.')
        return 0 if all(found) else 2
    # This branch intentionally performs downloads: never call it before the user approves.
    print('Onay kapsamı: resmi Python3.10 tabanı, PyPI MLflow2.1.1/2.2.1 ve çalışma bağımlılıkları.',flush=True)
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out=ROOT/'outputs'/'s51-kurulum'/stamp;out.mkdir(parents=True,exist_ok=False)
    report={'kaynak':'kurulum','gercek_deney_kabulu':False,'zaman_utc':stamp,'base':BASE,'images':[]}
    try:
        for v in VERSIONS:
            tag='pafta-ai-s51:mlflow-'+v
            with (out/('build-'+v+'.log')).open('w',encoding='utf-8') as log:
                x=call(['build','--platform','linux/amd64','--pull=false','--build-arg','MLFLOW_VERSION='+v,'-t',tag,str(ROOT/'sandbox/s51_docker')],stdout=log,stderr=subprocess.STDOUT,timeout=1800)
            if x.returncode:raise RuntimeError('Docker build başarısız; log: '+str(out/('build-'+v+'.log')))
            x=call(['image','inspect',tag],capture_output=True,timeout=20)
            if x.returncode:raise RuntimeError('Kurulan imaj okunamadı')
            meta=json.loads(x.stdout)[0];(out/('image-'+v+'.json')).write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
            # Network none, no host mount/port; only read the installed dependency metadata.
            x=call(['run','--rm','--pull=never','--network','none','--read-only','--user','10001:10001','--cap-drop','ALL','--security-opt','no-new-privileges',meta['Id'],'cat','/opt/pafta-pip-report.json'],capture_output=True,timeout=30)
            if x.returncode:raise RuntimeError('Paket kaydı alınamadı')
            pip_report=json.loads(x.stdout);(out/('pip-'+v+'.json')).write_text(json.dumps(pip_report,ensure_ascii=False,indent=2),encoding='utf-8')
            report['images'].append({'surum':v,'tag':tag,'id':meta['Id'],'size':meta.get('Size'),'pip_report':'pip-'+v+'.json'})
            print(tag,'oluşturuldu; gerçek CVE kabulü henüz yapılmadı.',flush=True)
    except Exception as exc:
        report['hata']=str(exc);print(str(exc),file=sys.stderr);return 1
    finally:
        (out/'kurulum.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print('Kurulum kaydı:',out/'kurulum.json',flush=True)
    return 0
if __name__=='__main__':raise SystemExit(main())
