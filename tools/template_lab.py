"""JV16'yı kilitli gerçek Thymeleaf/FreeMarker jar'larıyla yeniden üretir.

Varsayılan çalışma çevrimdışıdır ve hiçbir bağımlılık indirmez. Maven ile JDK 21+
önceden kurulu olmalıdır. Yalnız kullanıcı açıkça izin verirse ``--download``
Maven Central'dan pom.xml içindeki sabit sürümleri getirir.
"""
import argparse
import os
import sys
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(ROOT))
from engine.runtime_env import refresh_windows_runtime_env
refresh_windows_runtime_env()


def run(download=False):
    home = Path(os.environ['LOCALAPPDATA']) / 'Pafta'
    maven = home / 'maven/apache-maven-3.9.16/bin/mvn.cmd'
    java = Path(os.environ.get('JAVA_HOME', r'C:\Program Files\Android\Android Studio\jbr'))
    if not maven.exists() or not (java / 'bin/javac.exe').exists():
        raise RuntimeError('Mevcut Maven 3.9.16 ve JAVA_HOME/JDK 21+ gerekli; otomatik kurulum yok.')
    env = dict(os.environ, JAVA_HOME=str(java))
    with tempfile.TemporaryDirectory(prefix='pafta_template_') as temp:
        folder = Path(temp)
        shutil.copytree(ROOT / 'tracks/java/template_lab', folder, dirs_exist_ok=True)
        args = [str(maven), '-q', '-B', '-f', str(folder / 'pom.xml'),
                f'-Dmaven.repo.local={home / "m2"}', 'dependency:build-classpath',
                f'-Dmdep.outputFile={folder / "cp.txt"}']
        if not download:
            args.insert(1, '-o')
        result = subprocess.run(args, env=env, capture_output=True, timeout=300)
        if result.returncode:
            detail = (result.stdout + result.stderr).decode('utf8', 'replace')[-3000:]
            raise RuntimeError('Çevrimdışı bağımlılık çözümü başarısız; --download yalnız açık kullanıcı onayıyla kullanılmalı.\n' + detail)
        cp = (folder / 'cp.txt').read_text(encoding='utf8').strip()
        sources = [str(p) for p in sorted((folder / 'src').glob('*.java'))]
        subprocess.run([str(java / 'bin/javac.exe'), '-encoding', 'UTF-8', '--release', '21',
                        '-cp', cp, '-d', str(folder / 'out'), *sources],
                       check=True, env=env, timeout=60)
        process = subprocess.run([str(java / 'bin/java.exe'), '-Dfile.encoding=UTF-8',
                                  '-Dstdout.encoding=UTF-8', '-cp', str(folder / 'out') + os.pathsep + cp,
                                  'pafta.template.Ana'], env=env, capture_output=True, timeout=60)
        if process.returncode:
            raise RuntimeError(process.stderr.decode('utf8', 'replace')[-3000:])
        return process.stdout.decode('utf8').replace('\r\n', '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true',
                        help='Sabit bağımlılıkların indirilmesine açıkça izin verir')
    print(run(parser.parse_args().download), end='')
