# -*- coding: utf-8 -*-
"""Dil koşucuları.

Her yolun track.json'ındaki "runner" alanı buradaki bir koşucuyu seçer. Bütün
koşucular aynı düzeneği (sandbox/py_harness.py) ayrı bir süreçte çalıştırır;
fark, düzeneğe hangi modla ve hangi ek bilgilerle gidildiğidir:

    python      → run / test / trace (Röntgen) / dis (Bytecode)
    regex       → kod = desen, girdi = metin; regex_run / regex_test / regex_dis (ağaç);
                  adım meta'sında motor: pcre2 → aynı modlar gerçek PCRE2'de (sandbox/pcre2_engine.py);
                  motor: dotnet / javascript → .NET ya da Node motorunda (sandbox/regex_motorlar.py)
    bash, powershell → kod bir betik dosyasına yazılır; proc_run / proc_test / proc_trace
    sql         → bellek içi SQLite; örnek veritabanı (tracks/sql/ornek.sql) + görev hazırlığı;
                  sql_run / sql_test / sql_dis (sorgu planı); adım meta'sında motor: postgres →
                  WSL'deki gerçek PostgreSQL (sandbox/pg_lab.py), pg_run / pg_test; motor: mariadb →
                  WSL'deki gerçek MariaDB (sandbox/mariadb_lab.py), my_run / my_test

Yeni dil = yeni bir Runner nesnesi + RUNNERS'a kayıt.
"""
import json
import copy
import glob
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARNESS = os.path.join(ROOT, "sandbox", "py_harness.py")
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def argv_coz(meta):
    """Görevin meta'sındaki argv: liste ya da kabuktaki gibi tırnaklanmış metin ('"yıllık rapor.txt" notlar.txt')."""
    argv = (meta or {}).get("argv")
    if argv is None:
        return None
    if isinstance(argv, (list, tuple)):
        return [str(a) for a in argv]
    return shlex.split(str(argv))
MAX_TIMEOUT = 60


def python_exe():
    exe = sys.executable
    if exe.lower().endswith("pythonw.exe"):
        cand = exe[:-len("pythonw.exe")] + "python.exe"
        if os.path.exists(cand):
            return cand
    return exe


def _kill_tree(proc):
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=NO_WINDOW)
    else:
        proc.kill()


class HarnessRunner:
    """Düzeneği ayrı süreçte çalıştıran ortak taban."""
    name = "?"
    default_timeout = 6
    test_timeout = 6
    ozellik = {"roentgen": False, "dis": None}
    modlar = {}            # run/test/trace/dis → düzenek modu
    ek = {}                # her işe eklenecek alanlar
    tavan = MAX_TIMEOUT    # süre sınırının üst sınırı

    def available(self):
        return True

    def yorumlayici(self):
        return python_exe()

    def execute(self, job, timeout=None):
        timeout = min(int(timeout or self.default_timeout), self.tavan)
        job = dict(self.ek, **job)
        tmp = tempfile.mkdtemp(prefix="pafta_")
        work = os.path.join(tmp, "calisma")
        os.makedirs(work)
        job_path = os.path.join(tmp, "job.json")
        res_path = os.path.join(tmp, "result.json")
        with open(job_path, "w", encoding="utf-8") as f:
            json.dump(job, f, ensure_ascii=False)
        cmd = [self.yorumlayici(), "-I", "-X", "utf8", HARNESS, job_path, res_path]
        try:
            proc = subprocess.Popen(cmd, cwd=work, stdin=subprocess.DEVNULL,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    creationflags=NO_WINDOW)
            try:
                raw_out, raw_err = proc.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                _kill_tree(proc)
                try:
                    proc.communicate(timeout=3)
                except Exception:
                    pass
                return {"status": "timeout", "timeout": timeout,
                        "error": {"type": "Zaman aşımı", "line": None, "frames": [], "where": "kod",
                                  "msg": f"Program {timeout} saniyede bitmedi."}}
            try:
                with open(res_path, encoding="utf-8") as f:
                    res = json.load(f)
            except (OSError, ValueError):
                res = {"status": "error", "error": {
                    "type": "SüreçBitti", "line": None, "frames": [], "where": "kod",
                    "msg": "Program sonuç yazamadan süreci sonlandırdı (os._exit ya da çökme)."}}
            extra = (raw_out or b"").decode("utf-8", "replace") + (raw_err or b"").decode("utf-8", "replace")
            if extra.strip():
                res.setdefault("segs", []).append(["raw", extra])
            return res
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def run(self, code, stdin="", setup=None, timeout=None, argv=None):
        return self.execute({"mode": self.modlar["run"], "code": code, "stdin": stdin,
                             "setup": setup, "argv": argv}, timeout)

    def test(self, code, step):
        meta = step.get("meta", {})
        argv = argv_coz(meta)
        job = {"mode": self.modlar["test"], "code": code, "stdin": step.get("stdin", ""),
               "test": step.get("test", "ok(False, 'Bu görevin testi yazılmamış')"),
               "setup": step.get("setup"), "argv": argv}
        return self.execute(job, meta.get("timeout") or self.test_timeout)

    def trace(self, code, stdin="", setup=None, argv=None):
        if "trace" not in self.modlar:
            return None
        return self.execute({"mode": self.modlar["trace"], "code": code, "stdin": stdin, "setup": setup,
                             "argv": argv}, max(10, self.default_timeout))

    def dis(self, code, setup=None):
        if "dis" not in self.modlar:
            return None
        return self.execute({"mode": self.modlar["dis"], "code": code, "setup": setup}, 5)


class PythonRunner(HarnessRunner):
    name = "python"
    ozellik = {"roentgen": True, "dis": "Bytecode"}
    modlar = {"run": "run", "test": "test", "trace": "trace", "dis": "dis"}

    def execute(self, job, timeout=None):
        prefix = f"import sys; sys.path.insert(0, {os.path.join(ROOT, '.deps')!r})\n"
        return super().execute(dict(job, setup=prefix + (job.get("setup") or "")), timeout)


class PurpleRunner(PythonRunner):
    """Purple Team yolu: Python; her çalıştırmada MITRE ATT&CK özeti (tracks/purple/veri/attack.json,
    tools/attack_ozet.py) çalışma klasörüne attack.json olarak kopyalanır."""
    name = "purple"
    ek = {"kopyala": [os.path.join(ROOT, "tracks", "purple", "veri", "attack.json")]}


class CapstoneRunner(PythonRunner):
    """Shared offline case files and explicit adapters for the capstone track."""
    name = "bitirme"
    default_timeout = 20
    test_timeout = 45
    ek = {"kopyala": [os.path.join(ROOT, "tracks", "bitirme", "veri", name)
                      for name in ("olaylar.jsonl", "vaka.json", "vaka.pcap", "manifest.json")]}

    def execute(self, job, timeout=None):
        setup = ("import sys, importlib\n"
                 f"sys.path.insert(0, {ROOT!r})\n"
                 f"sys.path.insert(0, {os.path.join(ROOT,'.deps')!r})\n"
                 "sys.modules['vaka_lab'] = importlib.import_module('sandbox.capstone_lab')\n")
        return super().execute(dict(job, setup=setup+(job.get("setup") or "")), timeout)


def ai_python(gpu=False):
    """AI derslerinin ayrı sanal ortamı: PAFTA_AI_PYTHON ya da proje içindeki .ai-venv.

    gpu=True (adım meta'sında ortam: gpu) önce AMD kartlı ortamı dener: PAFTA_AI_PYTHON_GPU ya da
    %LOCALAPPDATA%/Pafta/ai-venv-rocm. O ortam yoksa normal yola düşer; diğer makinelerde davranış değişmez.
    Tüm dersler o ortama alınmaz: ROCm torch'u MKL içermez, CPU işleri yaklaşık 20 kat yavaşlar ve Whisper çöker."""
    yol = os.environ.get("PAFTA_AI_PYTHON")
    if yol:
        return yol
    alt = ("Scripts", "python.exe") if os.name == "nt" else ("bin", "python")
    if gpu:
        adaylar = [
            os.environ.get("PAFTA_AI_PYTHON_GPU", ""),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Pafta", "ai-venv-rocm", *alt),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Pafta", "ai-venv-cuda", *alt),
            os.path.join(ROOT, ".ai-venv-rocm", *alt),
            os.path.join(ROOT, ".ai-venv-cuda", *alt),
            *glob.glob(os.path.join(os.environ.get("LOCALAPPDATA", ""), "Packages", "Claude_*", "LocalCache", "Local", "Pafta", "ai-venv-rocm", *alt)),
        ]
        for kart in adaylar:
            if kart and os.path.isfile(kart):
                return kart
    return os.path.join(ROOT, ".ai-venv", *alt)


class AiGercekRunner(PythonRunner):
    """AI yolları, adım meta'sında motor: ai-gercek → gerçek model/araç deneyi (sandbox/ai_gercek_lab.py).

    gereksinim: torch  → .ai-venv yorumlayıcısı (torch/transformers); ollama → Pafta'nın Python'u.
    Kod ve test `import ai_lab` ile laboratuvara erişir. Test geçse bile laboratuvarın yazdığı
    `kaynak: gercek` kanıtı yoksa sonuç PASS sayılmaz; kanıt kalıcı olarak PAFTA_DATA/ai-kanit'e kopyalanır."""
    name = "ai-gercek"
    ozellik = {"roentgen": False, "dis": None}
    modlar = {"run": "run", "test": "test"}
    default_timeout = 300
    test_timeout = 300
    tavan = 600

    def __init__(self, gereksinim="ollama", gpu=False):
        if gereksinim not in ("ollama", "torch", "docker"):
            raise ValueError(f"Bilinmeyen gereksinim: {gereksinim!r}; ollama, torch veya docker kullanın.")
        self.gereksinim = gereksinim
        self.gpu = gpu

    def yorumlayici(self):
        # torch → .ai-venv (torch/transformers); ollama ve docker → Pafta'nın Python'u (stdlib + subprocess yeter)
        return ai_python(self.gpu) if self.gereksinim == "torch" else python_exe()

    def available(self):
        return os.path.isfile(self.yorumlayici())

    def execute(self, job, timeout=None):
        if not self.available():
            return {"status": "error", "checks": [], "segs": [], "error": {
                "type": "BağımlılıkEksik", "line": None, "frames": [], "where": "kurulum",
                "msg": f"AI sanal ortamı bulunamadı ({self.yorumlayici()}). Bu gerçek deney kurulmadan "
                       "çalışmaz ve geçmiş sayılmaz; bkz. docs/ai-gercek-kurulum-onayi.md."}}
        from engine.progress import data_dir
        kanit = tempfile.mkdtemp(prefix="pafta_ai_kanit_")
        setup = ("import sys, importlib\n"
                 f"sys.path.insert(0, {ROOT!r})\n"
                 "ai_lab = importlib.import_module('sandbox.ai_gercek_lab')\n"
                 "sys.modules['ai_lab'] = ai_lab\n"
                 f"ai_lab.KANIT_DIR = {kanit!r}\n"
                 f"ai_lab.CALISTIR = {job.get('mode') == 'run'!r}\n")
        try:
            res = super().execute(dict(job, setup=setup + (job.get("setup") or "")), timeout)
            res["ai_kanit"] = self._kanit_tasi(kanit, os.path.join(data_dir(), "ai-kanit"), job)
        finally:
            shutil.rmtree(kanit, ignore_errors=True)
        if job.get("mode") == "test" and res.get("status") == "pass":
            gercek = [k for k in res["ai_kanit"] if k.get("kaynak") == "gercek" and k.get("kabul") is True]
            if not gercek:
                res["status"] = "fail"
                res.setdefault("checks", []).append({"ok": False, "msg": "Gerçek deney kanıtı (kaynak: gercek, "
                                                     "kabul: true) üretilmedi; gerçek kabul yapılmadan PASS verilmez."})
        return res

    @staticmethod
    def _kanit_tasi(kaynak, hedef, job):
        import hashlib
        ozet = []
        kod_ozeti = hashlib.sha256((job.get("code") or "").encode("utf-8")).hexdigest()
        for ad in sorted(os.listdir(kaynak)):
            if not ad.endswith(".json"):
                continue
            try:
                with open(os.path.join(kaynak, ad), encoding="utf-8") as f:
                    veri = json.load(f)
            except (OSError, ValueError):
                continue
            veri["ogrenci_kodu_sha256"] = kod_ozeti
            veri["mod"] = job.get("mode")
            yol = None
            try:
                os.makedirs(hedef, exist_ok=True)
                yol = os.path.join(hedef, ad)
                with open(yol, "w", encoding="utf-8") as f:
                    json.dump(veri, f, ensure_ascii=False, indent=1)
            except OSError:
                yol = None
            ortam = veri.get("ortam") or veri.get("model_bilgisi") or {}
            model = ortam.get("model")
            ozet.append({"pilot": veri.get("pilot"), "kaynak": veri.get("kaynak"), "kabul": veri.get("kabul"),
                         "model": model.get("ad") if isinstance(model, dict) else model,
                         "ozet": veri.get("ozet"), "dosya": yol, "zaman": veri.get("zaman")})
        return ozet


class VqlRunner(HarnessRunner):
    """Purple yolu, adım meta'sında motor: velociraptor → WSL'de gerçek Velociraptor (sandbox/vql_lab.py,
    py_harness vql_*). Hazırlık disk/ altında dosya ağacı kurar; kod bir VQL sorgusudur (Kok değişkeni)."""
    name = "vql"
    ozellik = {"roentgen": False, "dis": None}
    modlar = {"run": "vql_run", "test": "vql_test"}
    default_timeout = 60
    test_timeout = 180

    def available(self):
        from sandbox.vql_lab import durum
        return durum() is None


class WslRunner(HarnessRunner):
    """Opt-in Linux Python/Bash, with the guardian owning timeout and cleanup."""
    default_timeout = 60
    test_timeout = 120

    def __init__(self, language):
        if language not in ("python", "bash"):
            raise ValueError("WSL backend yalnız Python ve Bash için tanımlı.")
        self.language = language
        self.name = language + "-wsl"
        if language == "python":
            self.modlar = dict(PythonRunner.modlar)
            self.ozellik = dict(PythonRunner.ozellik)
            self.ek = {}
        else:
            self.modlar = {"run": "proc_run", "test": "proc_test", "trace": "proc_trace"}
            self.ozellik = {"roentgen": True, "dis": None}
            self.ek = {"proc": {
                "cmd": ["/bin/bash", "--noprofile", "--norc"],
                "iz_cmd": ["/bin/bash", "--noprofile", "--norc", "-x"],
                "dosya": "betik.sh", "iz_on_ek": "PS4='+ ${LINENO}: '\n",
                "env": {"PS4": "+ ${LINENO}: ", "LC_ALL": "C.UTF-8"},
                "satir_deseni": r"betik\.sh: (?:line|satır) (\d+)",
                "iz_deseni": r"^(?P<derinlik>\++) (?P<satir>\d+): (?P<komut>.*)$",
            }}

    def available(self):
        from sandbox.wsl_process import available
        return available()

    def execute(self, job, timeout=None, cancel_event=None):
        from sandbox.wsl_process import execute, seconds
        timeout = seconds(timeout, self.default_timeout)
        job = dict(self.ek, **job)
        if "proc" in job:
            # The outside Linux guardian must expire first, including during
            # setup/tests and repeated calis()/run() invocations.
            job["proc"] = dict(job["proc"], sure=timeout + 2)
        return execute(job, timeout, cancel_event)

    def dis(self, code, setup=None):
        if "dis" not in self.modlar:
            return None
        return self.execute({"mode": "dis", "code": code, "setup": setup})

    def trace(self, code, stdin="", setup=None, argv=None):
        return self.execute({"mode": self.modlar["trace"], "code": code,
                             "stdin": stdin, "setup": setup, "argv": argv})

    def test(self, code, step):
        meta = step.get("meta", {})
        return self.execute({"mode": self.modlar["test"], "code": code,
                             "stdin": step.get("stdin", ""), "setup": step.get("setup"),
                             "argv": argv_coz(meta),
                             "test": step.get("test", "ok(False, 'Bu görevin testi yazılmamış')")},
                            meta.get("timeout", self.test_timeout))


def for_step(runner, step):
    """Resolve authoritative lesson/step metadata identically in every caller."""
    meta = (step or {}).get("meta", {})
    backend = meta.get("backend")
    if backend not in (None, "native", "wsl"):
        raise ValueError(f"Bilinmeyen backend: {backend!r}; native veya wsl kullanın.")
    if backend == "wsl":
        name = getattr(runner, "language", getattr(runner, "name", None))
        runner = WslRunner(name)
    elif backend == "native" and isinstance(runner, WslRunner):
        runner = RUNNERS[runner.language]
    motor = meta.get("motor")
    if motor not in (None, "python", "pcre2", "dotnet", "javascript", "sqlite", "postgres", "mariadb", "mysql", "mssql", "kusto",
                     "sentinel-kural", "elastic-agent", "sigma-hedef", "splunk", "suricata", "zeek", "velociraptor", "pwsh", "ad-vm",
                     "ad-client", "ai-gercek"):
        raise ValueError(f"Bilinmeyen motor: {motor!r}; python, pcre2, dotnet, javascript, sqlite, postgres, "
                         "mariadb, mysql, mssql, kusto, sentinel-kural, elastic-agent, sigma-hedef, splunk, suricata, zeek, "
                         "velociraptor, pwsh, ad-vm, ad-client veya ai-gercek kullanın.")
    if motor in ("pcre2", "dotnet", "javascript"):
        if not isinstance(runner, RegexRunner):
            raise ValueError(f"motor: {motor} yalnız regex yolunda tanımlı.")
        runner = Pcre2Runner() if motor == "pcre2" else RegexMotorRunner(motor)
    elif motor == "kusto":
        if type(runner) is not KqlRunner:
            raise ValueError("motor: kusto yalnız KQL (Kusto) yolunda tanımlı.")
        from sandbox.kusto_runner import KustoRunner
        runner = KustoRunner()
    elif motor == "sentinel-kural":
        if type(runner) is not KqlRunner:
            raise ValueError("motor: sentinel-kural yalnız KQL (Kusto) yolunda tanımlı.")
        from sandbox.sentinel_kural_lab import SentinelKuralRunner
        runner = SentinelKuralRunner(meta.get("son", ""), meta.get("kosu", 50), meta.get("pencere", "SigninLogs"))
    elif motor == "elastic-agent":
        if not isinstance(runner, ElasticRunner):
            raise ValueError("motor: elastic-agent yalnız Elastic yolunda tanımlı.")
        from sandbox.elastic_agent_lab import ElasticAgentRunner
        runner = ElasticAgentRunner()
    elif motor == "sigma-hedef":
        if not (isinstance(runner, DetectionRunner) and runner.name == "sigma"):
            raise ValueError("motor: sigma-hedef yalnız Sigma yolunda tanımlı.")
        from sandbox.sigma_hedef_lab import SigmaHedefRunner
        runner = SigmaHedefRunner()
    elif motor in ("mysql", "mssql"):
        if type(runner) is not SqlRunner:
            raise ValueError(f"motor: {motor} yalnız SQL yolunda tanımlı.")
        from sandbox.sql_container_runner import ContainerSqlRunner
        runner = ContainerSqlRunner(motor)
    elif motor == "postgres":
        if type(runner) is not SqlRunner:
            raise ValueError("motor: postgres yalnız SQL yolunda tanımlı.")
        runner = PostgresRunner()
    elif motor == "mariadb":
        if type(runner) is not SqlRunner:
            raise ValueError("motor: mariadb yalnız SQL yolunda tanımlı.")
        runner = MariadbRunner()
    elif motor == "splunk":
        if isinstance(runner, DetectionRunner) and runner.name == "sigma":
            runner = SigmaSplunkRunner(meta.get("girdi", "kural"), meta.get("pipeline", ""))
        elif type(runner) is SplRunner:
            runner = SplunkRunner(meta.get("girdi", "arama"))
        else:
            raise ValueError("motor: splunk yalnız SPL ve Sigma yollarında tanımlı.")
    elif motor in ("suricata", "zeek"):
        if not isinstance(runner, IdsRunner):
            raise ValueError(f"motor: {motor} yalnız Ağ Tespiti yolunda tanımlı.")
        runner = IdsRunner(motor)
    elif motor == "velociraptor":
        if not isinstance(runner, PurpleRunner):
            raise ValueError("motor: velociraptor yalnız Purple yolunda tanımlı.")
        runner = VqlRunner()
    elif motor == "pwsh":
        if getattr(runner, "name", None) != "powershell":
            raise ValueError("motor: pwsh yalnız PowerShell yolunda tanımlı.")
        runner = RUNNERS["powershell-7"]
    elif motor == "python" and isinstance(runner, DetectionRunner) and runner.name == "yara":
        runner = YaraApiRunner()
    elif motor == "python" and isinstance(runner, AdRunner):
        runner = AdAuditRunner()
    elif motor == "python" and type(runner) is SqlRunner:
        # Application/DB binding exercises execute real Python sqlite3 calls.
        runner = PythonRunner()
    elif motor == "python" and isinstance(runner, DetectionRunner) and runner.name == "sigma":
        # SG21: Windows'un EVTX/XML'ini Python'da normalleştir; sandbox/sigma_evtx_lab.py gerçek Splunk'a götürür.
        runner = SigmaPythonRunner()
    elif motor == "ad-vm":
        if not isinstance(runner, AdRunner) and getattr(runner, "name", None) != "powershell":
            raise ValueError("motor: ad-vm yalnız AD ve PowerShell yollarında tanımlı.")
        runner = AdVmRunner(meta.get("guest", "PF-DC01"))
    elif motor == "ai-gercek":
        if type(runner) is not PythonRunner:
            raise ValueError("motor: ai-gercek yalnız Python koşuculu (AI) yollarda tanımlı.")
        runner = AiGercekRunner(meta.get("gereksinim", "ollama"), gpu=meta.get("ortam") == "gpu")
    elif motor == "ad-client":
        if not isinstance(runner, AdRunner):
            raise ValueError("motor: ad-client yalnız AD yolunda tanımlı.")
        runner = AdClientRunner()
    if "timeout" in meta:
        from sandbox.wsl_process import seconds
        timeout = seconds(meta["timeout"])
        runner = copy.copy(runner)
        runner.default_timeout = timeout
        runner.test_timeout = timeout
    return runner


class RegexRunner(HarnessRunner):
    name = "regex"
    ozellik = {"roentgen": False, "dis": "Ağaç"}
    modlar = {"run": "regex_run", "test": "regex_test", "dis": "regex_dis"}


class Pcre2Runner(RegexRunner):
    """Adım meta'sında motor: pcre2 → aynı regex modları, gerçek PCRE2 kitaplığında (sandbox/pcre2_engine.py)."""
    name = "regex-pcre2"
    ozellik = {"roentgen": False, "dis": "PCRE2"}
    ek = {"motor": "pcre2"}

    def available(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("pafta_pcre2_engine", os.path.join(ROOT, "sandbox", "pcre2_engine.py"))
        modul = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modul)
        return modul.available()


class RegexMotorRunner(RegexRunner):
    """Adım meta'sında motor: dotnet / javascript → aynı regex modları, gerçek .NET ya da Node motorunda
    (sandbox/regex_motorlar.py; motor ayrı bir süreçte iş başına bir kez açılır)."""
    test_timeout = 30
    default_timeout = 20

    def __init__(self, motor):
        self.motor = motor
        self.name = "regex-" + motor
        self.ozellik = {"roentgen": False, "dis": {"dotnet": ".NET", "javascript": "JavaScript"}[motor]}
        self.ek = {"motor": motor}

    def available(self):
        if self.motor == "javascript":
            return bool(NODE)
        return shutil.which("powershell.exe") is not None


class DetectionRunner(HarnessRunner):
    """Sigma events / native YARA bytes, isolated like the existing runners."""
    default_timeout = 12
    test_timeout = 20

    def __init__(self, name, package):
        self.name = name
        self.package = package
        self.modlar = {"run": name + "_run", "test": name + "_test"}

    def available(self):
        import importlib.util
        local = os.path.join(ROOT, ".deps")
        return (os.path.isdir(os.path.join(local, self.package))
                or bool(glob.glob(os.path.join(local, self.package + "*.pyd")))
                or importlib.util.find_spec(self.package) is not None)


class PacketRunner(HarnessRunner):
    name = "packets"
    default_timeout = 30  # Cold WSL startup + bounded loopback capture (inner limit 20 s).
    test_timeout = 60
    modlar = {"run": "packet_run", "test": "packet_test"}

    def available(self):
        from sandbox.packet_engine import tshark_path
        from sandbox.bpf_native import available
        return bool(tshark_path() and available())


class ElasticRunner(HarnessRunner):
    """Bounded Elastic dialects; queries run in isolated native/local engines."""
    name = "elastic"
    default_timeout = 20
    test_timeout = 60
    tavan = 300
    # Native ingest/index/refresh operations are expensive under validation's
    # eight workers. Keep this product's pressure bounded without serializing
    # local KQL/Lucene/EQL or hiding failed operations behind retries.
    native_gate = threading.BoundedSemaphore(2)
    modlar = {"run": "elastic_run", "test": "elastic_test"}

    def execute(self, job, timeout=None):
        try:
            config=json.loads(job.get('stdin') or '{}')
        except (ValueError,TypeError):
            config={}
        if not isinstance(config,dict) or config.get('backend')!='elastic':
            return super().execute(job,timeout)
        budget=timeout if timeout is not None else 120
        if not self.native_gate.acquire(timeout=180):
            return {'status':'timeout','error':{'type':'Elastic meşgul','msg':'Yerel Elastic iş kuyruğu 180 saniyede açılmadı.'}}
        try:
            return super().execute(job,budget)
        finally:
            self.native_gate.release()

    def available(self):
        from sandbox.elastic_lucene import available
        return available()


class AdRunner(HarnessRunner):
    name = "ad"
    ozellik = {"roentgen": False, "dis": "LDAP"}
    modlar = {"run": "ad_run", "test": "ad_test", "dis": "ad_dis"}


class YaraApiRunner(PythonRunner):
    """YR23–24 use real yara-python through the explicit bundle API."""
    name = "yara-api"
    default_timeout = 20
    test_timeout = 45

    def execute(self, job, timeout=None):
        setup = ("import sys, importlib\n"
                 f"sys.path.insert(0, {ROOT!r})\n"
                 f"sys.path.insert(0, {os.path.join(ROOT,'.deps')!r})\n"
                 "sys.modules['yara_lab'] = importlib.import_module('sandbox.yara_bundle')\n")
        return super().execute(dict(job, setup=setup+(job.get("setup") or "")), timeout)


class AdAuditRunner(PythonRunner):
    """AD güvenlik denetimi eklerinde çevrimdışı kanıtları yorumlayan Python tezgahı."""
    name = "ad-audit"
    ozellik = {"roentgen": True, "dis": None}
    ek = {"kopyala": [os.path.join(ROOT, "tracks", "ad", "veri", name)
                      for name in ("acl.json", "s4u.json", "adcs.json")]}


class AdClientRunner(PythonRunner):
    """Learner Python calls real, fixed-lab LDAP clients; no Python LDAP model."""
    name = "ad-client"
    default_timeout = 110
    test_timeout = 240
    tavan = 240

    def execute(self, job, timeout=None):
        setup = ("import sys, importlib\n"
                 f"sys.path.insert(0, {ROOT!r})\n"
                 "sys.modules['ad_lab'] = importlib.import_module('sandbox.ad_ldap_client')\n")
        return super().execute(dict(job, setup=setup+(job.get("setup") or "")), timeout)


class SqlRunner(HarnessRunner):
    name = "sql"
    ozellik = {"roentgen": False, "dis": "Plan"}
    modlar = {"run": "sql_run", "test": "sql_test", "dis": "sql_dis"}
    ek = {"tohum": os.path.join(ROOT, "tracks", "sql", "ornek.sql")}


class PostgresRunner(HarnessRunner):
    """Adım meta'sında motor: postgres → WSL'deki gerçek PostgreSQL kümesi (sandbox/pg_lab.py, py_harness pg_*).

    Her iş geçici bir veritabanı ve rollerle başlar, iş bitince hepsi silinir; SQLite'ın
    örnek veritabanı yüklenmez, tabloları görevin hazırlığı kurar."""
    name = "sql-postgres"
    ozellik = {"roentgen": False, "dis": None}
    modlar = {"run": "pg_run", "test": "pg_test"}
    default_timeout = 45
    test_timeout = 90

    def available(self):
        from sandbox.pg_lab import available
        return available()

    kapali_hatasi = "PostgreSQLKapalı"
    yok_hatasi = "PostgreSQLYok"

    def lab(self):
        from sandbox import pg_lab
        return pg_lab

    def execute(self, job, timeout=None, cancel_event=None):
        from sandbox.wsl_process import execute, seconds
        timeout = seconds(timeout, self.default_timeout)
        job = dict(self.ek, **job)
        for deneme in range(2):
            sorun = self.lab().hazirla()
            if sorun:
                return {"status": "error", "segs": [], "error": {
                    "type": self.yok_hatasi, "msg": sorun, "line": None, "frames": [], "where": "kod"}}
            res = execute(job, timeout, cancel_event)
            if (res.get("error") or {}).get("type") != self.kapali_hatasi:
                return res
        return res


class MariadbRunner(PostgresRunner):
    """Adım meta'sında motor: mariadb → WSL'deki gerçek MariaDB (sandbox/mariadb_lab.py, py_harness my_*).

    Her iş adı pafta_lab_ ile başlayan geçici bir veritabanıyla başlar, iş bitince silinir;
    SQLite'ın örnek veritabanı yüklenmez, tabloları görevin hazırlığı kurar."""
    name = "sql-mariadb"
    modlar = {"run": "my_run", "test": "my_test"}
    kapali_hatasi = "MariaDBKapalı"
    yok_hatasi = "MariaDBYok"

    def available(self):
        from sandbox.mariadb_lab import available
        return available()

    def lab(self):
        from sandbox import mariadb_lab
        return mariadb_lab


class KqlRunner(SqlRunner):
    name = "kql"
    ozellik = {"roentgen": False, "dis": "SQL"}
    modlar = {"run": "kql_run", "test": "kql_test", "dis": "kql_dis"}
    ek_veri = (os.path.join(ROOT, "tracks", "kql", "veri.sql"),)

    def execute(self, job, timeout=None):
        # SQL veritabanının üstüne günlük tabloları (istekler, gunluk, dagitimlar) eklenir
        parcalar = []
        for yol in (self.ek["tohum"],) + self.ek_veri:
            with open(yol, encoding="utf-8") as f:
                parcalar.append(f.read())
        return super().execute(dict(job, tohum_sql="\n".join(parcalar)), timeout)


class SplRunner(KqlRunner):
    name = "spl"
    ozellik = {"roentgen": False, "dis": "SQL"}
    modlar = {"run": "spl_run", "test": "spl_test", "dis": "spl_dis"}
    ek_veri = KqlRunner.ek_veri + (os.path.join(ROOT, "tracks", "spl", "veri.sql"),)   # + Splunk'ın _time alanı


class SplunkRunner(HarnessRunner):
    """Adım meta'sında motor: splunk → Docker'daki gerçek Splunk Enterprise (sandbox/splunk_lab.py, py_harness spk_*).

    girdi: arama (kod bir SPL araması), props (kod props.conf kıtaları; hazırlığın verisi bu ayarlarla
    dizine alınır), alarm (kod savedsearches.conf kıtaları) ya da bilgi (kod '# props.conf', '# eventtypes.conf',
    '# tags.conf' bölümleri; sonuç hazırlığın goster(...) aramasıdır). Görevin hazırlığı Python'dur:
    props(...), veri(...) ve kayit(...) ile laboratuvarı kurar."""
    name = "spl-splunk"
    ozellik = {"roentgen": False, "dis": None}
    modlar = {"run": "spk_run", "test": "spk_test"}
    default_timeout = 150
    test_timeout = 300
    tavan = 600

    def __init__(self, girdi="arama"):
        if girdi not in ("arama", "props", "alarm", "bilgi"):
            raise ValueError(f"Bilinmeyen girdi: {girdi!r}; arama, props, alarm veya bilgi kullanın.")
        self.ek = {"girdi": girdi}

    def available(self):
        from sandbox.splunk_lab import available
        return available()

    _sira = threading.Lock()     # laboratuvar tek; süre sınırı sıra gelince başlasın

    def execute(self, job, timeout=None):
        from sandbox import splunk_lab
        with SplunkRunner._sira:
            sorun = splunk_lab.hazirla()      # konteynerin açılışı işin süresine sayılmaz
            if sorun:
                return {"status": "error", "segs": [], "error": {
                    "type": "SplunkYok", "msg": sorun, "line": None, "frames": [], "where": "kod"}}
            return super().execute(job, timeout)


class IdsRunner(HarnessRunner):
    """Ağ Tespiti: görevin trafik tarifinden üretilen PCAP üstünde gerçek Suricata (WSL) ya da Zeek (Docker).
    Adım meta'sında motor: suricata (varsayılan; kod bir kural dosyası) ya da zeek (kod bir Zeek betiği)."""
    name = "ids"
    ozellik = {"roentgen": False, "dis": None}
    modlar = {"run": "ids_run", "test": "ids_test"}
    default_timeout = 60
    test_timeout = 180
    tavan = 300

    def __init__(self, motor="suricata"):
        if motor not in ("suricata", "zeek"):
            raise ValueError(f"Bilinmeyen motor: {motor!r}; suricata veya zeek kullanın.")
        self.ek = {"motor": motor}

    def available(self):
        from sandbox.ids_lab import durum
        return not durum()


class SigmaSplunkRunner(SplunkRunner):
    """Sigma yolu, adım meta'sında motor: splunk → kural gerçek pySigma Splunk backend'iyle çevrilir ve gerçek
    Splunk laboratuvarında çalışır (py_harness sgs_*). girdi: kural (kod bir Sigma kuralı ya da korelasyonlu
    koleksiyon) ya da pipeline (kod bir processing pipeline YAML'ı; kural hazırlıkta). pipeline: hazır
    pipeline adları, virgülle (sysmon, windows, splunk_windows)."""
    name = "sigma-splunk"
    modlar = {"run": "sgs_run", "test": "sgs_test"}

    def __init__(self, girdi="kural", pipeline=""):
        if girdi not in ("kural", "pipeline", "komut"):
            raise ValueError(f"Bilinmeyen girdi: {girdi!r}; kural, pipeline veya komut kullanın.")
        self.ek = {"girdi": girdi, "pipeline": pipeline}


class SigmaPythonRunner(PythonRunner):
    """Sigma yolunda motor: python → Python görevi; testi gerçek Splunk'a yükleme yaptığı için süre tavanı geniş."""
    name = "sigma-python"
    test_timeout = 150
    tavan = 180


class HttpRunner(PythonRunner):
    """Python; her çalıştırmadan önce sandbox/http_tezgah.py demo web uygulamasını (127.0.0.1, boş port)
    başlatır ve kullanıcı koduna `tezgah` modülünü (SUNUCU, gonder, yanit) açar."""
    name = "http"
    tezgah = os.path.join(ROOT, "sandbox", "http_tezgah.py")

    def execute(self, job, timeout=None):
        on = (f"import runpy as _r, sys as _sys\n"
              f"_sys.path.insert(0, {os.path.join(ROOT, 'sandbox')!r})\n"
              f"_sys.path.insert(0, {os.path.join(ROOT, '.deps')!r})\n"
              f"_r.run_path({self.tezgah!r}, run_name='__tezgah__')\n")
        return super().execute(dict(job, setup=on + (job.get("setup") or "")), timeout)


def _bash_yolu():
    for aday in (r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files (x86)\Git\bin\bash.exe"):
        if os.path.isfile(aday):
            return aday
    yol = shutil.which("bash")
    return yol if yol and "system32" not in yol.lower() else None


class ProcRunner(HarnessRunner):
    ozellik = {"roentgen": True, "dis": None}
    modlar = {"run": "proc_run", "test": "proc_test", "trace": "proc_trace"}

    def __init__(self, name, proc, default_timeout, test_timeout, kopyala=(), iz=True):
        self.name = name
        self.ek = {"proc": proc, "kopyala": [p for p in kopyala]}    # kopyala: her çalıştırmada hazır olacak veri dosyaları
        self.default_timeout = default_timeout
        self.test_timeout = test_timeout
        if not iz:                                                   # iz modu olmayan yorumlayıcı (ör. Node)
            self.ozellik = {"roentgen": False, "dis": None}
            self.modlar = {"run": "proc_run", "test": "proc_test"}

    def available(self):
        return bool(self.ek["proc"]["cmd"][0])


class AdVmRunner(ProcRunner):
    """Real AD PowerShell in the managed guest, transparently started by Pafta."""
    _locks = {name: threading.Lock() for name in ("PF-DC01", "PF-APP01")}
    tavan = 240

    def __init__(self, guest="PF-DC01"):
        if guest not in self._locks:
            raise ValueError("AD guest: PF-DC01 veya PF-APP01 olmalı.")
        self.guest = guest
        super().__init__("ad-vm", {
            "cmd": [python_exe(), "-X", "utf8", os.path.join(ROOT, "sandbox", "ad_vm_process.py"), "--guest", guest],
            "dosya": "betik.ps1", "bom": True, "sure": 90,
        }, default_timeout=110, test_timeout=240, iz=False)

    def available(self):
        from sandbox.ad_vm_process import LAB
        return (LAB / "config.json").is_file()

    def execute(self, job, timeout=None):
        from sandbox.ad_vm_process import ensure_ready
        with self._locks[self.guest]:
            try:
                if self.guest == "PF-APP01":
                    ensure_ready("PF-DC01")
                ensure_ready(self.guest)
            except Exception as exc:
                return {"status": "error", "error": {"type": "ADLaboratuvarı", "msg": str(exc), "line": None, "frames": [], "where": "kod"}, "segs": []}
            return super().execute(job, timeout)


def _pwsh7_yolu():
    r"""PowerShell 7: .deps\pwsh\<sürüm>\pwsh.exe (taşınabilir paket; yönetici gerektirmez), yoksa PATH."""
    yerel = os.path.join(ROOT, ".deps", "pwsh", PWSH7_SURUM, "pwsh.exe")
    return yerel if os.path.isfile(yerel) else (shutil.which("pwsh") or "")


PWSH7_SURUM = "7.6.8"
BASH = _bash_yolu()
NODE = shutil.which("node") or (r"C:\Program Files\nodejs\node.exe" if os.path.isfile(r"C:\Program Files\nodejs\node.exe") else None)
CMD = shutil.which("cmd.exe") if os.name == "nt" else None
PWSH7 = _pwsh7_yolu()
# Sarmalayıcı: UTF-8 çıktı, Girdi kutusunu $Girdi dizisine okur, betiği argümanlarıyla çağırır.
PS_SARMAL = (
    "[Console]::OutputEncoding = [Text.Encoding]::UTF8\n"
    "$OutputEncoding = [Text.Encoding]::UTF8\n"
    "$__okuyucu = New-Object System.IO.StreamReader([Console]::OpenStandardInput(), (New-Object System.Text.UTF8Encoding $false))\n"
    "$global:Girdi = @(); while ($null -ne ($__satir = $__okuyucu.ReadLine())) { $global:Girdi += $__satir }\n"
    "$global:LASTEXITCODE = 0\n"
    "{IZ}& \"$PSScriptRoot\\betik.ps1\" @args\n"
    "exit $LASTEXITCODE\n"
)

RUNNERS = {
    "python": PythonRunner(),
    "python-wsl": WslRunner("python"),
    "bash-wsl": WslRunner("bash"),
    "http": HttpRunner(),
    "regex": RegexRunner(),
    "sql": SqlRunner(),
    "kql": KqlRunner(),
    "spl": SplRunner(),
    "sigma": DetectionRunner("sigma", "sigma"),
    "yara": DetectionRunner("yara", "yara"),
    "packets": PacketRunner(),
    "ids": IdsRunner(),
    "purple": PurpleRunner(),
    "bitirme": CapstoneRunner(),
    "elastic": ElasticRunner(),
    "ad": AdRunner(),
    "bash": ProcRunner("bash", {
        "cmd": [BASH or ""], "iz_cmd": [BASH or "", "-x"], "dosya": "betik.sh",
        "iz_on_ek": "PS4='+ ${LINENO}: '\n",
                "env": {"PS4": "+ ${LINENO}: ", "LC_ALL": "C.UTF-8"}, "sure": 10,
        "satir_deseni": r"betik\.sh: (?:line|satır) (\d+)",
        "iz_deseni": r"^(?P<derinlik>\++) (?P<satir>\d+): (?P<komut>.*)$",
    }, default_timeout=15, test_timeout=30),
    "powershell": ProcRunner("powershell", {
        "cmd": ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File"],
        "dosya": "betik.ps1", "bom": True, "sarmal": PS_SARMAL, "sarmal_dosya": "_pafta.ps1",
        "iz_satiri": "Set-PSDebug -Trace 1; ", "iz_disla": ["betik.ps1", "LASTEXITCODE"],
        "sure": 20, "satir_deseni": r"betik\.ps1:(\d+)",
        "iz_deseni": r"^DEBUG:\s+(?P<satir>\d+)\+\s*(?P<komut>.*)$",
        # Proje kapsamında sabitlenen modüller (Pester 5.9.0) önce aransın: .deps\psmodules
        "env": {"PSModulePath": os.path.join(ROOT, ".deps", "psmodules") + os.pathsep + os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "WindowsPowerShell", "v1.0", "Modules")},
    }, default_timeout=25, test_timeout=50,
        kopyala=[os.path.join(ROOT, "tracks", "powershell", "veri", "olaylar.json")]),
    # Adım meta'sında motor: pwsh → aynı tezgah, PowerShell 7'nin taşınabilir paketiyle (New-PSSession
    # -UseWindowsPowerShell gibi yalnız 7'de olan özellikler için). Yönetici, WinRM ve ağ dinleyicisi yok.
    "powershell-7": ProcRunner("powershell-7", {
        "cmd": [PWSH7 or "", "-NoLogo", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File"],
        "dosya": "betik.ps1", "bom": True, "sarmal": PS_SARMAL, "sarmal_dosya": "_pafta.ps1",
        "iz_satiri": "Set-PSDebug -Trace 1; ", "iz_disla": ["betik.ps1", "LASTEXITCODE"],
        "sure": 60, "satir_deseni": r"betik\.ps1:(\d+)",
        "iz_deseni": r"^DEBUG:\s+(?P<satir>\d+)\+\s*(?P<komut>.*)$",
    }, default_timeout=60, test_timeout=120),
    "javascript": ProcRunner("javascript", {
        "cmd": [NODE or ""], "dosya": "betik.js", "sure": 10,
        # Proje kapsamında sabitlenen npm paketleri (Express 5.3.0): tools/js_bagimlilik_kur.py
        "env": {"NODE_PATH": os.path.join(ROOT, ".deps", "npm", "node_modules")},
        "satir_deseni": r"betik\.js:(\d+)",
    }, default_timeout=15, test_timeout=30, iz=False),
    "cmd": ProcRunner("cmd", {
        "cmd": [CMD or "", "/d", "/q", "/e:on", "/v:off", "/c"],
        "dosya": "betik.cmd", "batch": True, "sure": 10,
        # Sürümü doğrulanmış Sysinternals araçları (sigcheck64, autorunsc64): tools/sysinternals_kur.ps1
        "env": {"PATH": os.path.join(ROOT, ".deps", "sysinternals") + os.pathsep + os.environ.get("PATH", "")},
    }, default_timeout=15, test_timeout=35, iz=False,
        kopyala=[os.path.join(ROOT, "sandbox", "evtx_fixtures.py")]),
}


def get(name):
    return RUNNERS.get(name)
