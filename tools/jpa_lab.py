# -*- coding: utf-8 -*-
r"""Java yolundaki JV13'ün gerçek çıktısını üretir: sürümleri kilitli Spring Data JPA düzeneği.

tracks/java/jpa_lab/ (pom.xml + src/Ana.java): Spring Data JPA 4.1.2, Hibernate 7.4.13.Final,
H2 2.5.252 (bellek içi). JDK 21 gerekir (varsayılan: Android Studio'nun JBR'i; JAVA_HOME ile
değiştirilebilir). Maven 3.9.16 ve Maven deposu %LOCALAPPDATA%\Pafta altında tutulur: Windows
komut satırı, proje yolundaki emojili klasör adlarını Java'ya bozuk iletir, bu yüzden araçlar ve
derleme ASCII bir yolda çalışır. Yalnız --download seçilirse Maven resmi Apache arşivinden indirilir ve SHA-512 ile
doğrulanır. Her çalıştırma geçici bir klasörde derler; depoya bir şey yazmaz.

    python tools/jpa_lab.py
"""
import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, str(ROOT))
from engine.runtime_env import refresh_windows_runtime_env
refresh_windows_runtime_env()
LAB = os.path.join(ROOT, "tracks", "java", "jpa_lab")
ARAC = os.path.join(os.environ["LOCALAPPDATA"], "Pafta")
MAVEN_SURUM = "3.9.16"
MAVEN_SHA512 = None   # .sha512 dosyasından okunur ve karşılaştırılır
MAVEN = os.path.join(ARAC, "maven", f"apache-maven-{MAVEN_SURUM}", "bin", "mvn.cmd")
DEPO = os.path.join(ARAC, "m2")
JAVA_HOME = os.environ.get("JAVA_HOME") or r"C:\Program Files\Android\Android Studio\jbr"


def maven_kur():
    if os.path.isfile(MAVEN):
        return
    temel = f"https://archive.apache.org/dist/maven/maven-3/{MAVEN_SURUM}/binaries/apache-maven-{MAVEN_SURUM}-bin.zip"
    gecici = tempfile.mkdtemp(prefix="pafta_maven_")
    try:
        zip_yol = os.path.join(gecici, "maven.zip")
        urllib.request.urlretrieve(temel, zip_yol)
        beklenen = urllib.request.urlopen(temel + ".sha512").read().decode().split()[0]
        gercek = hashlib.sha512(open(zip_yol, "rb").read()).hexdigest()
        if gercek != beklenen:
            sys.exit(f"Maven arşivinin SHA-512 özeti tutmuyor: {gercek[:16]}…")
        zipfile.ZipFile(zip_yol).extractall(os.path.join(ARAC, "maven"))
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


def calistir(download=False):
    if download:
        maven_kur()
    elif not os.path.isfile(MAVEN):
        raise RuntimeError('Maven 3.9.16 yok; indirme için açık onaydan sonra --download kullanın.')
    env = dict(os.environ, JAVA_HOME=JAVA_HOME)
    kok = tempfile.mkdtemp(prefix="pafta_jpa_")
    try:
        shutil.copy(os.path.join(LAB, "pom.xml"), kok)
        shutil.copytree(os.path.join(LAB, "src"), os.path.join(kok, "src"))
        cp_dosya = os.path.join(kok, "cp.txt")
        args = [MAVEN, "-q", "-B", "-f", os.path.join(kok, "pom.xml"), f"-Dmaven.repo.local={DEPO}",
                "dependency:build-classpath", f"-Dmdep.outputFile={cp_dosya}"]
        if not download:
            args.insert(1, "-o")
        subprocess.run(args, check=True, env=env, timeout=300)
        cp = open(cp_dosya, encoding="utf-8").read().strip()
        cikis = os.path.join(kok, "out")
        bin_ = os.path.join(JAVA_HOME, "bin")
        subprocess.run([os.path.join(bin_, "javac"), "-encoding", "UTF-8", "-parameters", "-d", cikis, "-cp", cp,
                        os.path.join(kok, "src", "Ana.java")], check=True, env=env, timeout=60)
        r = subprocess.run([os.path.join(bin_, "java"), "-Dfile.encoding=UTF-8", "-Dstdout.encoding=UTF-8", "-Dstderr.encoding=UTF-8",
                            "-cp", cikis + os.pathsep + cp, "pafta.jpa.Ana"],
                           env=env, capture_output=True, timeout=60)
        sys.stdout.write(r.stdout.decode("utf-8", "strict"))
        if r.returncode != 0:
            sys.stderr.write(r.stderr.decode("utf-8", "replace")[-3000:])
            sys.exit(r.returncode)
    finally:
        shutil.rmtree(kok, ignore_errors=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true', help='Onaylanmış Maven/bağımlılık indirmesine izin verir')
    calistir(parser.parse_args().download)
