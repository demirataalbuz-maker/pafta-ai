"""Native Apache Lucene 9.12.3 query_string teaching adapter.

This is a JVM/Lucene index, not Elasticsearch and not a Python query emulator.
Explicit mapped fields only; keyword/standard text and scalar points are
supported. Source objects/nested documents, field wildcards, date math,
custom analyzers, scoring/boost options and Elasticsearch APIs are unsupported.
QueryParser provides real phrase/slop/fuzzy/regexp/wildcard/escape behavior.
ES-like typed ranges, exists markers and pure-negative queries are explicit
adapter additions. Results are original zero-based document indices.
"""
import functools
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading

VERSION = "9.12.3"
ARTIFACTS = {
    "lucene-core": "e9236abc84e82a17cdbfb2291ec7ae16b286e62496b9922db5bbad31b1caca079a64a6edc5f002ad20a36951ddc25178d100a76d876120fcc1a28cdfc77bf8cc",
    "lucene-analysis-common": "74d02f9e163dbf5d9487f3a8f2e0f820bab5333c5ec29dd4c76aecfca65ad4dae418256f46a19aa1ab416134c9538049a6db16c88a0ee01fb1acd493142a5538",
    "lucene-queryparser": "bbc4db37246318651bb767af886894a061400910e4dfeefc21525278727bc681e50e1a872253e12a8057fcdc208ebb2aa01a3e080fc5a43a1b71017c1f2e6ccf",
    "lucene-queries": "7b1c43d58153163b1de9a9f7f81ba9dff9c98ea329428f28b4575eedf452cde669bb14194bf2256b90239e14a0b3c7e91764d8d6977bfbd1bb13b10e1e595610",
    "lucene-sandbox": "7cbf483bca98e0a1da63e66d134b9bed129a7518d12a9b8a5261639a39b501d972574a75a0a590dc7c212a4e8be412efb5be01f954008f76fb524141b0d6e96d",
}
ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".deps" / "elastic-lucene"
SOURCE = Path(__file__).resolve().parent / "elastic_native" / "PaftaLucene.java"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_BUILD_LOCK = threading.Lock()


class ElasticLuceneError(ValueError):
    pass


class ElasticLuceneUnavailable(RuntimeError):
    pass


def _cache_root():
    # JBR21's Windows classpath loader misdecodes emoji paths even when UTF-8
    # is selected. Only a verified disposable runtime view lives outside .deps.
    root = Path(tempfile.gettempdir()) / "pafta-elastic-lucene"
    if os.name == "nt" and not str(root).isascii():
        raise ElasticLuceneUnavailable("Java için ASCII geçici dizin gerekli; TEMP/TMP konumunu ASCII bir klasöre ayarlayın.")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _java_environment():
    environment = dict(os.environ)
    for name in ("JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS", "_JAVA_OPTIONS", "CLASSPATH"):
        environment.pop(name, None)
    return environment


def _java_tools():
    suffix = ".exe" if os.name == "nt" else ""
    configured = os.environ.get("PAFTA_JAVA")
    candidates = []
    if configured:
        value = Path(configured)
        candidates.append(value if value.is_file() else value / "bin" / ("java" + suffix))
    if os.environ.get("JAVA_HOME"):
        candidates.append(Path(os.environ["JAVA_HOME"]) / "bin" / ("java" + suffix))
    candidates.append(Path(r"C:\Program Files\Android\Android Studio\jbr\bin\java.exe"))
    found = shutil.which("java")
    if found:
        candidates.append(Path(found))
    for java in candidates:
        javac = java.with_name("javac" + suffix)
        if java.is_file() and javac.is_file():
            return str(java.resolve()), str(javac.resolve())
    raise ElasticLuceneUnavailable("Lucene için JDK 17+ java/javac gerekli. PAFTA_JAVA ile JDK "
                                   "klasörünü veya java.exe yolunu belirtin; mevcut Android Studio JBR kullanılabilir.")


@functools.lru_cache(maxsize=1)
def _jars():
    paths = []
    for name, digest in ARTIFACTS.items():
        path = RUNTIME / f"{name}-{VERSION}.jar"
        if not path.is_file() or hashlib.sha512(path.read_bytes()).hexdigest() != digest:
            raise ElasticLuceneUnavailable("Lucene JAR eksik veya SHA-512 farklı: " + str(path) +
                                           ". Proje kökünde python tools/install_elastic_runtime.py çalıştırın.")
        paths.append(str(path))
    return tuple(paths)


@functools.lru_cache(maxsize=1)
def _compiled():
    java, javac = _java_tools()
    jars = _jars()  # .deps pins are always the source of truth.
    source = SOURCE.read_bytes()
    signature = hashlib.sha256(source + VERSION.encode() + javac.encode() +
                               "".join(ARTIFACTS.values()).encode()).hexdigest()[:24]
    base = _cache_root()
    cache = base / signature
    with _BUILD_LOCK:
        if not (cache / "classes" / "PaftaLucene.class").is_file():
            with tempfile.TemporaryDirectory(prefix="build-", dir=base) as temporary:
                stage = Path(temporary) / "runtime"
                stage.mkdir()
                for jar in jars:
                    shutil.copyfile(jar, stage / Path(jar).name)
                (stage / SOURCE.name).write_bytes(source)
                (stage / "classes").mkdir()
                command = [javac, "-J-Dfile.encoding=UTF-8", "-encoding", "UTF-8", "--release", "17",
                           "-classpath", os.pathsep.join(Path(jar).name for jar in jars),
                           "-d", "classes", SOURCE.name]
                try:
                    process = subprocess.run(command, capture_output=True, timeout=45, cwd=stage,
                                             env=_java_environment(), creationflags=NO_WINDOW)
                except (OSError, subprocess.TimeoutExpired) as exc:
                    raise ElasticLuceneUnavailable("Lucene Java derlemesi çalışmadı: " + str(exc)) from exc
                if process.returncode:
                    raise ElasticLuceneUnavailable("Lucene Java derlenemedi: " +
                                                   process.stderr.decode("utf-8", "replace")[-6000:])
                try:
                    stage.rename(cache)
                except FileExistsError:
                    if not (cache / "classes" / "PaftaLucene.class").is_file():
                        raise ElasticLuceneUnavailable("Lucene derleme önbelleği tamamlanmadı: " + str(cache))
    # Validate copied native dependencies too; a partial/stale cache is not used.
    for jar, digest in zip(jars, ARTIFACTS.values()):
        copied = cache / Path(jar).name
        if not copied.is_file() or hashlib.sha512(copied.read_bytes()).hexdigest() != digest:
            raise ElasticLuceneUnavailable("Lucene çalışma önbelleği bozulmuş; şu geçici klasörü silip yeniden deneyin: " + str(cache))
    return java, os.pathsep.join([str(cache / "classes")] + [str(cache / Path(jar).name) for jar in jars])


def available():
    try:
        _java_tools()
        _jars()
        return True
    except ElasticLuceneUnavailable:
        return False


def _invoke(job):
    payload = json.dumps(job, ensure_ascii=False, allow_nan=False).encode("utf-8")
    if len(payload) > 8 * 1024 * 1024:
        raise ElasticLuceneError("Lucene işi en fazla 8 MiB olabilir.")
    java, classpath = _compiled()
    environment = _java_environment()
    command = [java, "-Xms16m", "-Xmx256m", "-Dfile.encoding=UTF-8", "-Duser.timezone=UTC",
               "-cp", classpath, "PaftaLucene"]
    try:
        result = subprocess.run(command, input=payload, capture_output=True, timeout=12,
                                cwd=Path(classpath.split(os.pathsep)[0]).parent, env=environment, creationflags=NO_WINDOW)
    except subprocess.TimeoutExpired as exc:
        raise ElasticLuceneError("Native Lucene 12 saniyede tamamlanmadı.") from exc
    except OSError as exc:
        raise ElasticLuceneUnavailable("Java başlatılamadı: " + str(exc)) from exc
    try:
        response = json.loads(result.stdout.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise ElasticLuceneUnavailable("Native Lucene geçerli JSON döndürmedi: " +
                                       result.stderr.decode("utf-8", "replace")[-2000:]) from exc
    if result.returncode or "error" in response:
        raise ElasticLuceneError(str(response.get("error", "Java çıkış kodu: " + str(result.returncode))))
    return response


def evaluate(query, mapping, documents):
    if not isinstance(query, str) or not query.strip() or len(query.encode("utf-8")) > 16000 or "\0" in query:
        raise ElasticLuceneError("Lucene sorgusu 1..16000 UTF-8 baytlık, NUL içermeyen metin olmalı.")
    result = _invoke({"mode": "query", "query": query, "mapping": mapping, "documents": documents})
    indices = result.get("indices")
    if not isinstance(indices, list) or any(type(i) is not int or not 0 <= i < len(documents) for i in indices):
        raise ElasticLuceneUnavailable("Native Lucene geçersiz belge indeksleri döndürdü.")
    return indices


def evaluate_ast(ast, mapping, documents):
    """Execute the documented KQL adapter AST using native Lucene queries."""
    result = _invoke({"mode": "ast", "ast": ast, "mapping": mapping, "documents": documents})
    indices = result.get("indices")
    if not isinstance(indices, list) or any(type(i) is not int or not 0 <= i < len(documents) for i in indices):
        raise ElasticLuceneUnavailable("Native Lucene geçersiz belge indeksleri döndürdü.")
    return indices


@functools.lru_cache(maxsize=128)
def analyze(text, analyzer="standard", lowercase=False):
    """Return native analyzer tokens for another local language adapter."""
    result = _invoke({"mode": "analyze", "text": text, "analyzer": analyzer, "lowercase": lowercase})
    return list(result["tokens"])


@functools.lru_cache(maxsize=1)
def version():
    return _invoke({"mode": "version"})["version"]
