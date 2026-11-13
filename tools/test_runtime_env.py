"""Runtime discovery must preserve caller intent and avoid persistent changes."""
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from engine.runtime_env import refresh_windows_runtime_env as refresh
class RuntimeEnvironment(unittest.TestCase):
 def test_explicit_overrides_and_path_priority_are_preserved(self):
  env={'Path':r'C:\venv;C:\WINDOWS\system32','JAVA_HOME':r'D:\custom','PAFTA_JAVA':r'D:\private\java.exe'}
  layers=[{'Path':r'C:\Windows\System32;C:\Docker','JAVA_HOME':r'C:\JDK'}, {'Path':r'C:\Docker;C:\UserTools','JAVA_HOME':r'C:\UserJDK'}]
  self.assertEqual(refresh(env,platform='nt',read_registry=lambda:layers),['PATH'])
  self.assertEqual(env['JAVA_HOME'],r'D:\custom');self.assertEqual(env['PAFTA_JAVA'],r'D:\private\java.exe')
  self.assertEqual(env['Path'],r'C:\venv;C:\WINDOWS\system32;C:\Docker;C:\UserTools')
 def test_user_default_and_expansion_are_process_local_and_idempotent(self):
  env={'PATH':r'C:\Windows','ProgramFiles':r'C:\Program Files'}
  layers=[{'JAVA_HOME':r'%ProgramFiles%\JDK','Path':r'%JAVA_HOME%\bin;C:\Docker'}, {'JAVA_HOME':r'D:\UserJDK'}]
  refresh(env,platform='nt',read_registry=lambda:layers)
  self.assertEqual(env['JAVA_HOME'],r'D:\UserJDK');self.assertEqual(env['PATH'],r'C:\Windows;D:\UserJDK\bin;C:\Docker')
  self.assertEqual(refresh(env,platform='nt',read_registry=lambda:layers),[])
  self.assertEqual(layers[0]['JAVA_HOME'],r'%ProgramFiles%\JDK')
 def test_unreadable_registry_leaves_environment_unchanged(self):
  env={'PATH':'private'}
  def denied():raise PermissionError('not available')
  self.assertEqual(refresh(env,platform='nt',read_registry=denied),[]);self.assertEqual(env,{'PATH':'private'})
 def test_non_windows_never_reads_registry(self):
  def forbidden():raise AssertionError('registry called')
  self.assertEqual(refresh({},platform='posix',read_registry=forbidden),[])
if __name__=='__main__':unittest.main()
