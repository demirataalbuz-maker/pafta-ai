"""20: fixed classroom adapter; never invokes a shell or arbitrary executable."""
import hashlib,json,os,shutil,sys
from pathlib import Path
if len(sys.argv)<5 or sys.argv[1]!='--root':raise SystemExit('fixed --root required')
root=Path(sys.argv[2]).resolve();argv=sys.argv[3:];action=argv[0]
if argv[1]!='--' or action not in ('yazdir','kopyala'):raise SystemExit('action/option boundary invalid')
values=argv[2:]
if len(values)!=(1 if action=='yazdir' else 2):raise SystemExit('argument count invalid')
result=dict(argv=argv,pid=os.getpid(),python=sys.version,shell=False)
if action=='yazdir':result['metin']=values[0]
else:
    if values!=['-kaynak rapor.txt','-kopya rapor.txt']:raise SystemExit('only fixed classroom filenames allowed')
    src=root/values[0];dst=root/values[1]
    shutil.copyfile(src,dst);result['kopya_sha256']=hashlib.sha256(dst.read_bytes()).hexdigest()
print(json.dumps(result,ensure_ascii=False))
