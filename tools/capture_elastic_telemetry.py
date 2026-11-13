"""Capture benign child-process exit telemetry as portable NDJSON.

These are actual parent-observed Popen pid/returncode/time values, NOT Sysmon,
EVTX, or Elastic Agent events. No usernames, hostnames, or full executable paths.
Re-running replaces only the dedicated lesson corpus requested by --output.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

def capture():
    docs=[]
    for exit_code in (0,1,2):
        p=subprocess.Popen([sys.executable,'-I','-c','import sys; sys.exit('+str(exit_code)+')'],
                           stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                           creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        p.communicate(timeout=5)
        docs.append({'id':'proc-'+str(exit_code),'at':datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z'),
                     'exe':Path(sys.executable).name,'pid':str(p.pid),'rc':str(p.returncode)})
    return docs

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_bytes(('\n'.join(json.dumps(d,ensure_ascii=False) for d in capture())+'\n').encode('utf-8'))
    print('Üç gerçek alt sürecin çıkış kaydı yazıldı.')
