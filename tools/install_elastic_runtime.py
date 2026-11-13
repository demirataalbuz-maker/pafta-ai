"""Install only pinned Apache Maven JARs into .deps; no system/JDK install.

Official source: https://repo.maven.apache.org/maven2/org/apache/lucene/
Every artifact is checked against the SHA-512 published by Maven Central and
the pinned digest reviewed alongside this installer. Runtime never downloads.
"""
import hashlib
from pathlib import Path
import sys
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sandbox.elastic_lucene import ARTIFACTS, RUNTIME, VERSION


def install():
    RUNTIME.mkdir(parents=True, exist_ok=True)
    for name, expected in ARTIFACTS.items():
        filename = f"{name}-{VERSION}.jar"
        destination = RUNTIME / filename
        if destination.is_file() and hashlib.sha512(destination.read_bytes()).hexdigest() == expected:
            print(filename + " doğrulandı")
            continue
        url = f"https://repo.maven.apache.org/maven2/org/apache/lucene/{name}/{VERSION}/{filename}"
        with urllib.request.urlopen(url + ".sha512", timeout=30) as response:
            published = response.read(512).decode("ascii").split()[0].lower()
        if published != expected:
            raise RuntimeError("Maven SHA-512 sabit pin ile uyuşmuyor: " + filename)
        with urllib.request.urlopen(url, timeout=30) as response:
            data = response.read(16 * 1024 * 1024 + 1)
        if len(data) > 16 * 1024 * 1024 or hashlib.sha512(data).hexdigest() != expected:
            raise RuntimeError("JAR boyut/SHA-512 doğrulaması başarısız: " + filename)
        with tempfile.TemporaryDirectory(prefix="download-", dir=RUNTIME) as temporary:
            staged = Path(temporary) / filename
            staged.write_bytes(data)
            staged.replace(destination)
        print(filename + " indirildi ve SHA-512 doğrulandı")


if __name__ == "__main__":
    install()
