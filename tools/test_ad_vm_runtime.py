"""VM transport failures and the real Windows guest guard, without an AD mock."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sandbox import ad_vm_process as vm


class Transport(unittest.TestCase):
 def test_error_redacts_private_password(self):
  data={'vmrun':'vmrun.exe','guests':{'PF-DC01':{'vmx':'guest.vmx','username':'Administrator','password':'DoNotPrintThis'}}}
  failed=subprocess.CompletedProcess([],1,b'failed DoNotPrintThis',b'')
  with patch.object(vm.subprocess,'run',return_value=failed):
   with self.assertRaises(RuntimeError) as e:
    vm.call(data,'PF-DC01','test')
   self.assertNotIn('DoNotPrintThis',str(e.exception))
   self.assertIn('[gizli]',str(e.exception))

 def test_timeout_does_not_print_argv(self):
  data={'vmrun':'vmrun.exe','guests':{'PF-DC01':{'vmx':'guest.vmx','username':'Administrator','password':'DoNotPrintThis'}}}
  with patch.object(vm.subprocess,'run',side_effect=subprocess.TimeoutExpired(['-gp','DoNotPrintThis'],1)):
   with self.assertRaises(RuntimeError) as e:
    vm.call(data,'PF-DC01','test')
   self.assertNotIn('DoNotPrintThis',str(e.exception))

 def test_unmanaged_vm_is_rejected(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp)
   data={'guests':{'PF-DC01':{'vmx':str(root.parent/'outside.vmx')}}}
   (root/'config.json').write_text(json.dumps(data),encoding='utf8')
   with patch.object(vm,'LAB',root):
    with self.assertRaisesRegex(ValueError,'dışında'):
     vm.config()


@unittest.skipUnless(os.name=='nt','Windows Job Objects require Windows')
class WindowsGuard(unittest.TestCase):
 def guard(self,source,timeout=3,stdin=""):
  temp=tempfile.TemporaryDirectory(prefix='pafta_guest_guard_')
  self.addCleanup(temp.cleanup)
  root=Path(temp.name)
  (root/'guard.ps1').write_text(vm.GUARD,encoding='utf-8-sig')
  (root/'learner.ps1').write_text('[Console]::InputEncoding=New-Object Text.UTF8Encoding $false\n[Console]::OutputEncoding=New-Object Text.UTF8Encoding $false\n'+source,encoding='utf-8-sig')
  (root/'request.json').write_text(json.dumps({'timeout':timeout}),encoding='utf8')
  (root/'stdin.txt').write_text(stdin,encoding='utf8',newline='\n')
  p=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(root/'guard.ps1'),'-Folder',str(root)],capture_output=True,timeout=timeout+30,creationflags=vm.NO_WINDOW)
  self.assertTrue((root/'result.json').exists(),p.stderr.decode('utf8','replace'))
  return root,json.loads((root/'result.json').read_text(encoding='utf-8-sig'))

 def test_utf8_exit_and_stderr(self):
  _,r=self.guard("[Console]::WriteLine('Türkçe şİ|'+[Console]::ReadLine()); [Console]::Error.WriteLine('stderr'); exit 7",stdin='Türkçe\n')
  self.assertEqual(r['code'],7)
  self.assertEqual(r['stdout'].strip(),'Türkçe şİ|Türkçe')
  self.assertEqual(r['stderr'].strip(),'stderr')
  self.assertFalse(r['timeout'])

 def test_timeout_kills_descendant(self):
  root,r=self.guard("$p=Start-Process powershell.exe -ArgumentList '-NoProfile -Command Start-Sleep 40' -PassThru -WindowStyle Hidden; $p.Id|Set-Content child.pid; Start-Sleep 40",timeout=2)
  self.assertTrue(r['timeout'])
  pid=int((root/'child.pid').read_text().strip())
  p=subprocess.run(['powershell.exe','-NoProfile','-Command',f'if(Get-Process -Id {pid} -ErrorAction SilentlyContinue){{exit 1}}'],capture_output=True,timeout=10,creationflags=vm.NO_WINDOW)
  self.assertEqual(p.returncode,0,'descendant survived guest timeout')

 def test_normal_exit_also_kills_descendant(self):
  root,r=self.guard("$p=Start-Process powershell.exe -ArgumentList '-NoProfile -Command Start-Sleep 40' -PassThru -WindowStyle Hidden; $p.Id|Set-Content child.pid; 'done'",timeout=5)
  self.assertFalse(r['timeout'])
  pid=int((root/'child.pid').read_text().strip())
  p=subprocess.run(['powershell.exe','-NoProfile','-Command',f'if(Get-Process -Id {pid} -ErrorAction SilentlyContinue){{exit 1}}'],capture_output=True,timeout=10,creationflags=vm.NO_WINDOW)
  self.assertEqual(p.returncode,0,'descendant survived normal return')


@unittest.skipUnless(os.environ.get('PAFTA_AD_LIVE')=='1','set PAFTA_AD_LIVE=1 for the managed guest')
class LiveGuest(unittest.TestCase):
 def test_real_guest_utf8_exit_and_stderr(self):
  r=vm.execute("[Console]::WriteLine('Türkçe şİ|'+[Console]::ReadLine()); [Console]::Error.WriteLine('stderr'); exit 7",stdin='Türkçe\n',timeout=10)
  self.assertEqual(r['code'],7,r)
  self.assertEqual(r['stdout'].strip(),'Türkçe şİ|Türkçe')
  self.assertEqual(r['stderr'].strip(),'stderr')

 def test_real_guest_timeout_kills_child(self):
  r=vm.execute("$p=Start-Process powershell.exe -ArgumentList '-NoProfile -Command Start-Sleep 90' -PassThru -WindowStyle Hidden; [Console]::WriteLine($p.Id); Start-Sleep 90",timeout=3)
  self.assertTrue(r['timeout'],r)
  self.assertEqual(r['code'],124)
  pid=int(r['stdout'].strip())
  check=vm.execute(f"[bool](Get-Process -Id {pid} -ErrorAction SilentlyContinue)",timeout=10)
  self.assertEqual(check['stdout'].strip(),'False',check)

 def test_real_guest_normal_exit_kills_child(self):
  r=vm.execute("$p=Start-Process powershell.exe -ArgumentList '-NoProfile -Command Start-Sleep 90' -PassThru -WindowStyle Hidden; [Console]::WriteLine($p.Id)",timeout=10)
  self.assertEqual(r['code'],0,r)
  self.assertFalse(r['timeout'])
  pid=int(r['stdout'].strip())
  check=vm.execute(f"[bool](Get-Process -Id {pid} -ErrorAction SilentlyContinue)",timeout=10)
  self.assertEqual(check['stdout'].strip(),'False',check)


if __name__=='__main__':
 unittest.main()
