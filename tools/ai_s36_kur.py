"""S36 official Cosign binary. --kontrol installs nothing; --indir requires prior user approval."""
import argparse,hashlib,json,os,shutil,subprocess,tempfile,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VERSION='v3.1.4'
URL='https://github.com/sigstore/cosign/releases/download/v3.1.4/cosign-windows-amd64.exe'
SHA='cbe953787074611f1334cbf37dc1cf953995bb8c45398eb4fc7bb781d29c1f2a'
SIZE=191066624
DEST=ROOT/'.deps/cosign-v3.1.4-windows-amd64/cosign.exe'
def _sha(path):
    with path.open('rb') as source:return hashlib.file_digest(source,'sha256').hexdigest()
def main():
    ap=argparse.ArgumentParser(description=__doc__);group=ap.add_mutually_exclusive_group(required=True)
    group.add_argument('--kontrol',action='store_true');group.add_argument('--indir',action='store_true');a=ap.parse_args()
    if a.indir:
        if os.name!='nt':raise SystemExit('Bu kurulum planı Windows amd64 içindir; diğer platform ayrı resmi binary ister.')
        DEST.parent.mkdir(parents=True,exist_ok=True)
        if not DEST.exists():
            fd,tmp=tempfile.mkstemp(prefix='cosign-',suffix='.download',dir=DEST.parent);os.close(fd)
            try:
                req=urllib.request.Request(URL,headers={'User-Agent':'Pafta-S36-approved-installer'})
                with urllib.request.urlopen(req,timeout=90) as source,open(tmp,'wb') as target:shutil.copyfileobj(source,target)
                if Path(tmp).stat().st_size!=SIZE or _sha(Path(tmp))!=SHA:raise ValueError('Resmi yayın boyut/SHA256 eşleşmedi; binary çalıştırılmadı.')
                # No blind overwrite of an existing install; only our own staging file is removed.
                with DEST.open('xb') as target,open(tmp,'rb') as source:shutil.copyfileobj(source,target)
            finally:
                Path(tmp).unlink(missing_ok=True)
    if not DEST.is_file():
        print(json.dumps({'kurulu':False,'surum':VERSION,'kaynak':URL,'boyut':SIZE,'sha256':SHA,'hedef':str(DEST),'deney_kabulu':False},ensure_ascii=False));return 2
    with DEST.open('rb') as source:actual=hashlib.file_digest(source,'sha256').hexdigest()
    if actual!=SHA:raise SystemExit('Mevcut binary SHA256 farklı; değiştirilmedi ve çalıştırılmadı.')
    result=subprocess.run([str(DEST),'version','--json'],capture_output=True,text=True,timeout=20,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    report={'kaynak':'kurulum','surum':VERSION,'sha256':actual,'boyut':DEST.stat().st_size,'url':URL,'version_stdout':result.stdout,'version_stderr':result.stderr,'returncode':result.returncode,'deney_kabulu':False}
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if a.indir:
        out=ROOT/'outputs/s36-kurulum';out.mkdir(parents=True,exist_ok=True);(out/'kurulum.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return result.returncode
if __name__=='__main__':raise SystemExit(main())
