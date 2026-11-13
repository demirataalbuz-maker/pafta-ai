"""Targeted native EVTX query/encoding/export mutations."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engine.lessons import Library
from engine.runners import get
pairs=[('>= 101','> 101'),('<= 103','< 103'),('and Level=2','or Level=2'),('EventID=102','EventID=101'),('/rd:true','/rd:false'),('/rd:false','/rd:true'),('/uni:true','/uni:false'),('/e:Events','/e:Other'),('/ow:false','/ow:true'),('/ow:true','/ow:false'),('qe "paket.evtx"','qe "olaylar.evtx"')]
n=0
for lid in ('cm19','cm20'):
 for st in Library().lesson('cmd',lid)['steps']:
  if st['kind']!='gorev': continue
  assert get('cmd').test(st['solution'],st)['status']=='pass'
  for old,new in pairs:
   if old not in st['solution']: continue
   # Reading the source instead of the exported file can be equivalent when
   # both select all records; here source contains deliberately excluded rows.
   code=st['solution'].replace(old,new,1)
   result=get('cmd').test(code,st)
   assert result['status'] in ('fail','error'), (lid,old,result)
   n+=1
print(n,'targeted mutations rejected')
