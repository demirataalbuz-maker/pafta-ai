"""Reproduce JV15 with pinned real Spring jars. Offline unless --download.

No server or privileged change. Maven/JDK must already be installed.
Approved dependencies: Maven Central, spring-security 7.0.2/framework 7.0.10.
"""
import argparse
import os
import sys
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]

sys.path.insert(0, str(ROOT))
from engine.runtime_env import refresh_windows_runtime_env
refresh_windows_runtime_env()


def run(download=False):
    home=Path(os.environ['LOCALAPPDATA'])/'Pafta'
    maven=home/'maven/apache-maven-3.9.16/bin/mvn.cmd'
    java=Path(os.environ.get('JAVA_HOME',r'C:\Program Files\Android\Android Studio\jbr'))
    if not maven.exists() or not (java/'bin/javac.exe').exists():
        raise RuntimeError('Mevcut Maven 3.9.16 ve JAVA_HOME/JDK 21+ gerekli; otomatik kurulum yok.')
    env=dict(os.environ,JAVA_HOME=str(java))
    with tempfile.TemporaryDirectory(prefix='pafta_security_') as temp:
        folder=Path(temp)
        shutil.copytree(ROOT/'tracks/java/security_lab',folder,dirs_exist_ok=True)
        args=[str(maven),'-q','-B','-f',str(folder/'pom.xml'),f'-Dmaven.repo.local={home/"m2"}',
              'dependency:build-classpath',f'-Dmdep.outputFile={folder/"cp.txt"}']
        if not download:args.insert(1,'-o')
        result=subprocess.run(args,env=env,capture_output=True,timeout=300)
        if result.returncode:raise RuntimeError(result.stdout.decode('utf8','replace')[-3000:])
        cp=(folder/'cp.txt').read_text(encoding='utf8').strip()
        subprocess.run([str(java/'bin/javac.exe'),'-encoding','UTF-8','-parameters','-cp',cp,'-d',str(folder/'out'),str(folder/'src/Ana.java')],check=True,env=env,timeout=60)
        p=subprocess.run([str(java/'bin/java.exe'),'-Dfile.encoding=UTF-8','-Dstdout.encoding=UTF-8','-cp',str(folder/'out')+os.pathsep+cp,'pafta.security.Ana'],env=env,capture_output=True,timeout=60)
        if p.returncode:raise RuntimeError(p.stderr.decode('utf8','replace')[-3000:])
        return p.stdout.decode('utf8').replace('\r\n','\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download',action='store_true',help='Explicitly allow approved Maven downloads')
    print(run(parser.parse_args().download),end='')
