"""Approved S36 Fulcio artifact fetch only; never starts services or pulls images."""
import argparse,hashlib,json,os,tempfile,shutil,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
URL='https://github.com/sigstore/fulcio/releases/download/v1.9.1/fulcio-linux-amd64'
SHA='d851e6fcc33bad57a08435e41fe082d8cc466f99c57d2fae156e82941f84ea31'
SIZE=50925712
DEST=ROOT/'.deps/fulcio-v1.9.1-linux-amd64/fulcio'
def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    parser=argparse.ArgumentParser(description=__doc__);g=parser.add_mutually_exclusive_group(required=True);g.add_argument('--kontrol',action='store_true');g.add_argument('--indir',action='store_true');args=parser.parse_args()
    if args.indir and not DEST.exists():
        DEST.parent.mkdir(parents=True,exist_ok=True);fd,name=tempfile.mkstemp(prefix='pafta-fulcio-',suffix='.download',dir=DEST.parent);os.close(fd);tmp=Path(name)
        try:
            with urllib.request.urlopen(urllib.request.Request(URL,headers={'User-Agent':'Pafta-S36-approved-installer'}),timeout=90) as source,tmp.open('wb') as target:shutil.copyfileobj(source,target)
            if tmp.stat().st_size!=SIZE or sha(tmp)!=SHA:raise ValueError('Boyut/SHA256 farklı; servis çalıştırılmadı')
            with DEST.open('xb') as target,tmp.open('rb') as source:shutil.copyfileobj(source,target)
        finally:tmp.unlink(missing_ok=True)
    installed=DEST.is_file() and DEST.stat().st_size==SIZE and sha(DEST)==SHA
    result={'kaynak':'kurulum','kurulu':installed,'surum':'v1.9.1','url':URL,'sha256':SHA,'boyut':SIZE,'hedef':str(DEST),'deney_kabulu':False}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if args.indir:
        out=ROOT/'outputs/s36-kurulum';out.mkdir(parents=True,exist_ok=True);(out/'fulcio-kurulum.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return 0 if installed else 2
if __name__=='__main__':raise SystemExit(main())
