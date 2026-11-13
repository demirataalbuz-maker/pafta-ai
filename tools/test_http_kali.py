"""Optional Kali HTTP/TLS smoke check. Uses configured WSL distro; no installs.

Source files are staged under Linux /tmp, not /mnt/c. GraphQL and browser
packages are not required by this check. Burp GUI acceptance remains manual.
"""
import base64
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sandbox.wsl_process import distro_name

BOOTSTRAP='''import sys,json,tempfile,pathlib,base64
with tempfile.TemporaryDirectory(prefix="pafta_http_") as tmp:
 for name,data in json.load(sys.stdin).items():
  pathlib.Path(tmp,name).write_bytes(base64.b64decode(data))
 sys.path.insert(0,tmp)
 from http_lab import Lab
 from http_tls_lab import TLSLab
 with Lab() as lab:
  c=lab.login("ayse")
  print("HTTP",[lab.request("GET",f"/items/{i}",cookie=c)["status"] for i in (1,2)])
 with TLSLab() as lab:
  print("TLS",[(r["exit"],r["http"]) for r in [lab.curl(),lab.curl(trust=False),lab.curl(hostname="other.pafta.test"),lab.curl(path="/missing",fail_http=True)]])
'''


def main():
    files={name:base64.b64encode((ROOT/'sandbox'/name).read_bytes()).decode('ascii')
           for name in ('http_lab.py','http_tls_lab.py')}
    p=subprocess.run(['wsl.exe','--distribution',distro_name(),'--cd','/tmp','--exec','python3','-c',BOOTSTRAP],
                     input=json.dumps(files),capture_output=True,text=True,encoding='utf-8',timeout=40,
                     creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    print(p.stdout,end='')
    if p.stderr:
        print(p.stderr,file=sys.stderr,end='')
    expected='HTTP [200, 403]\nTLS [(0, 200), (60, 0), (60, 0), (22, 404)]\n'
    if p.returncode or p.stderr.strip() or p.stdout!=expected:
        raise SystemExit('Kali HTTP/TLS acceptance failed')
    print('Kali /tmp HTTP/TLS: OK')


if __name__=='__main__':
    main()
