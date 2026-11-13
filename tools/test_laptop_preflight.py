"""SQL readiness must distinguish invalid credentials from server warm-up."""
import json,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from sandbox import sql_docker_lab as lab
class SqlReadiness(unittest.TestCase):
 def run_ready(self,error):
  info={'Image':'pinned-id','Config':{'Labels':{'pafta.lab':'sql-dialects'}},'HostConfig':{'NetworkMode':'none','PortBindings':{}},'State':{'Running':True}}
  return patch.object(lab,'docker',side_effect=['pinned-id',json.dumps([info])]),patch.object(lab,'client',side_effect=error),patch.object(lab.time,'sleep')
 def test_bad_credentials_fail_without_retries_or_resets(self):
  for code in ('ERROR 1045 (28000)','Login failed for user sa (18456)'):
   a,b,c=self.run_ready(RuntimeError(code))
   with a,b as client,c as sleep:
    with self.assertRaisesRegex(RuntimeError,'kimlik doğrulaması'):lab.ensure('mysql')
    self.assertEqual(client.call_count,1);sleep.assert_not_called()
 def test_transient_warmup_is_retried(self):
  a,b,c=self.run_ready([RuntimeError('server warming up'),'ready'])
  with a,b as client,c as sleep:
   lab.ensure('mysql');self.assertEqual(client.call_count,2);sleep.assert_called_once_with(1)
if __name__=='__main__':unittest.main()
