"""WSL argv transport, with actual no-space/space/dollar path witnesses."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sandbox.ad_ldap_client import linux_path

class Paths(unittest.TestCase):
 def test_literal_argv_and_error(self):
  for name in (r'C:\NoSpaces\Pafta\client.py',r'C:\Two Words\$cash\client.py'):
   with patch('sandbox.ad_ldap_client.subprocess.run',return_value=subprocess.CompletedProcess([],0,b'/mnt/c/probe\n',b'')) as run:
    self.assertEqual(linux_path(name,'kali-linux'),'/mnt/c/probe')
    self.assertEqual(run.call_args.args[0],['wsl.exe','-d','kali-linux','--exec','wslpath','-a','-u',name])
  for result in (subprocess.CompletedProcess([],1,b'',b'error'),subprocess.CompletedProcess([],0,b'',b'')):
   with patch('sandbox.ad_ldap_client.subprocess.run',return_value=result),self.assertRaises(RuntimeError):linux_path('x','kali-linux')

 @unittest.skipUnless(os.name=='nt','Windows WSL integration')
 def test_real_wsl_paths(self):
  distro=os.environ.get('PAFTA_WSL_DISTRO','kali-linux')
  with tempfile.TemporaryDirectory(prefix='pafta_ldap_') as root:
   for name in ('NoSpaces.py','Two Words.py','$literal.py'):
    path=Path(root)/name
    path.write_text("print('literal-path-ok')\n",encoding='utf-8',newline='\n')
    target=linux_path(path,distro)
    result=subprocess.run(['wsl.exe','-d',distro,'--exec','python3',target],capture_output=True,timeout=20)
    self.assertEqual(result.returncode,0,result.stderr)
    self.assertEqual(result.stdout,b'literal-path-ok\n')

if __name__=='__main__':unittest.main()
