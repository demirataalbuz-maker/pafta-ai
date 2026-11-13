"""Real WSL regression tests; no external downloads or permanent installations.

    python tools/test_wsl_runtime.py
Set PAFTA_WSL_DISTRO to use another explicitly configured distribution.
"""
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.runners import WslRunner, for_step, get
from sandbox import wsl_process


def linux(source):
    result = subprocess.run(wsl_process.command() + ["-c", source], capture_output=True,
                            timeout=20, creationflags=wsl_process.NO_WINDOW)
    if result.returncode:
        raise AssertionError((result.returncode, result.stderr.decode("utf-8", "replace")))
    return json.loads(result.stdout)


def out(result, kind="out"):
    return "".join(text for label, text in result.get("segs", []) if label == kind)


def assert_clean(test, result):
    test.assertTrue(result["runtime"]["cleanup"], result)
    cwd = result["runtime"]["cwd"]
    test.assertTrue(cwd.startswith("/tmp/pafta_wsl_"), cwd)
    test.assertFalse(linux(f"import json,os;print(json.dumps(os.path.exists({cwd!r})))"))


class WslConfigurationTests(unittest.TestCase):
    def test_defaults_and_boundaries(self):
        self.assertEqual(get("python-wsl").default_timeout, 60)
        self.assertEqual(get("python-wsl").test_timeout, 120)
        self.assertEqual(for_step(get("bash"), {"meta": {"backend": "wsl", "timeout": 300}}).default_timeout, 300)
        for value in (0, -1, 300.01, float("inf"), float("nan"), True, "wrong"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                wsl_process.seconds(value)
        self.assertEqual(wsl_process.seconds(0.1), 0.1)
        self.assertEqual(wsl_process.seconds(300), 300)
        with self.assertRaises(ValueError):
            get("python-wsl").test("print(1)", {"meta": {"timeout": 0}})
        with patch.dict(os.environ, {"PAFTA_WSL_DISTRO": "other linux"}):
            self.assertEqual(wsl_process.command()[2], "other linux")
        for value in ("", "-bad", "x\ny"):
            with patch.dict(os.environ, {"PAFTA_WSL_DISTRO": value}), self.assertRaises(ValueError):
                wsl_process.distro_name()

    def test_only_explicit_supported_backend_and_no_shared_timeout_mutation(self):
        native = get("python")
        self.assertIs(for_step(native, {"meta": {}}), native)
        with self.assertRaises(ValueError):
            for_step(native, {"meta": {"backend": "guess"}})
        with self.assertRaises(ValueError):
            for_step(get("powershell"), {"meta": {"backend": "wsl"}})
        picked = for_step(native, {"meta": {"backend": "wsl", "timeout": 180}})
        self.assertEqual(picked.default_timeout, 180)
        self.assertEqual(native.default_timeout, 6)
        self.assertEqual(get("python-wsl").default_timeout, 60)
        self.assertIs(for_step(picked, {"meta": {"backend": "native"}}), native)

    def test_missing_wsl_is_explicit(self):
        with patch("sandbox.wsl_process.shutil.which", return_value=None):
            result = get("python-wsl").run("print(1)")
            self.assertEqual(result["status"], "error")
            self.assertIn("WSL bulunamadı", result["error"]["msg"])


class WslRuntimeTests(unittest.TestCase):
    def test_utf8_lf_argv_stdin_real_script_and_stderr(self):
        source = (
            "import json,sys\r\nfrom pathlib import Path\r\n"
            "raw=Path(__file__).read_bytes()\r\n"
            "print(json.dumps([sys.argv[1:],sys.stdin.read(),'\\r' not in raw.decode(),"
            "not raw.startswith(bytes([239,187,191]))],ensure_ascii=False))\r\n"
            "print('uyarı: ığüşöç',file=sys.stderr)\r\n"
        )
        args = ["boşluk var", "çığ", "$HOME", "a;echo BOZUK", '"tırnak"']
        result = get("python-wsl").run(source, "şeker\r\n", argv=args)
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual(result["kod"], 0)
        self.assertEqual(json.loads(out(result)), [args, "şeker\n", True, True])
        self.assertEqual(out(result, "err"), "uyarı: ığüşöç\n")
        assert_clean(self, result)
        bash = get("bash-wsl").run("printf '%s\\n' \"$1\"\r\ncat\r\nprintf 'hata: çığ\\n' >&2\r\n",
                                   "girdi\r\n", argv=["iki sözcük"])
        self.assertEqual(bash["status"], "ok", bash)
        self.assertEqual(out(bash), "iki sözcük\ngirdi\n")
        self.assertEqual(out(bash, "err"), "hata: çığ\n")
        assert_clean(self, bash)

    def test_native_exit_codes_and_low_level_streams(self):
        for name, source, expected in (
            ("python-wsl", "import sys;print('önce');print('hata',file=sys.stderr);sys.exit(7)", 7),
            ("python-wsl", "import os;os.write(1,b'out\\n');os.write(2,b'err\\n');os._exit(9)", 9),
            ("bash-wsl", "printf 'out\\n'; printf 'err\\n' >&2; exit 23", 23),
        ):
            with self.subTest(name=name, expected=expected):
                result = get(name).run(source)
                self.assertEqual(result["status"], "error", result)
                self.assertEqual(result["kod"], expected)
                self.assertEqual(result["error"]["kod"], expected)
                self.assertTrue(out(result))
                self.assertTrue(out(result, "err"))
                assert_clean(self, result)

    def test_tests_setup_trace_and_disassembly(self):
        result = get("python-wsl").test("answer=42", {
            "setup": "from pathlib import Path\nPath('çığ.txt').write_text('veri',encoding='utf-8')",
            "test": "from pathlib import Path\neq(answer,42)\neq(Path('çığ.txt').read_text(encoding='utf-8'),'veri')",
        })
        self.assertEqual(result["status"], "pass", result)
        exited = get("python-wsl").test("import sys;answer=42;sys.exit(7)", {"test": "eq(answer,42)"})
        self.assertEqual(exited["status"], "error", exited)
        self.assertEqual(exited["error"]["kod"], 7)
        bad = get("python-wsl").test("answer=41", {"test": "eq(answer,42)"})
        self.assertEqual(bad["status"], "fail", bad)
        bash = get("bash-wsl").test("printf '%s' \"$1\"; cat", {
            "test": "eq(calis('girdi',['çığ']),{'kod':0,'cikti':'çığgirdi','hata':''})"})
        self.assertEqual(bash["status"], "pass", bash)
        trace = get("python-wsl").trace("x=2\nprint(x+1)")
        self.assertEqual(trace["status"], "ok", trace)
        self.assertTrue(trace["steps"])
        asm = get("python-wsl").dis("print(42)")
        self.assertEqual(asm["status"], "ok", asm)
        self.assertIn("42", asm["text"])
        trace = get("bash-wsl").trace("x=2\nprintf '%s\\n' \"$x\"")
        self.assertEqual(trace["status"], "ok", trace)
        self.assertEqual([step["line"] for step in trace["iz"]], [1, 2])
        self.assertEqual(trace["out"], "2\n")

    def test_installed_modules_report_real_linux_origins(self):
        source = """import importlib,importlib.metadata,json,sys
mods={}
for name, dist in [('pip','pip'),('setuptools','setuptools'),('wheel','wheel'),
                   ('requests','requests'),('aiohttp','aiohttp'),('bs4','beautifulsoup4'),
                   ('scapy','scapy'),('pwnlib','pwntools')]:
    m=importlib.import_module(name)
    mods[name]=[importlib.metadata.version(dist),m.__file__]
print(json.dumps({'python':sys.executable,'modules':mods}))
"""
        result = get("python-wsl").run(source)
        self.assertEqual(result["status"], "ok", result)
        inventory = json.loads(out(result))
        self.assertEqual(inventory["python"], "/usr/bin/python3")
        for name, (version, path) in inventory["modules"].items():
            self.assertTrue(version, name)
            self.assertTrue(path.startswith("/usr/"), (name, path))
            self.assertNotIn("/mnt/", path)
        shell = get("bash-wsl").run("shellcheck --version; bats --version")
        self.assertEqual(shell["status"], "ok", shell)
        self.assertIn("ShellCheck", out(shell))
        self.assertIn("Bats", out(shell))

    def test_real_offline_wheel_venv_and_install_fit_default(self):
        source = """import json,os,subprocess,sys,time,venv
from pathlib import Path
def measured(argv):
    start=time.monotonic()
    r=subprocess.run(argv,capture_output=True,text=True,check=True)
    return round(time.monotonic()-start,3),r.stdout
Path('fixture').mkdir()
Path('fixture/pyproject.toml').write_text('[build-system]\\nrequires=["setuptools","wheel"]\\nbuild-backend="setuptools.build_meta"\\n[project]\\nname="pafta-local-fixture"\\nversion="1.0"\\n')
Path('fixture/pafta_local_fixture.py').write_text('VALUE=42\\n')
build,_=measured([sys.executable,'-m','pip','wheel','--no-index','--no-build-isolation','--no-deps','--wheel-dir','wheelhouse','./fixture'])
start=time.monotonic()
venv.EnvBuilder(with_pip=True).create('.venv')
created=round(time.monotonic()-start,3)
# Do not resolve bin/python's symlink: invoking the system target loses the venv.
py=str(Path.cwd()/'.venv/bin/python')
installed,_=measured([py,'-m','pip','install','--no-index','--no-deps','--find-links','wheelhouse','pafta-local-fixture==1.0'])
_,report=measured([py,'-c','import json,sys,importlib.util,pafta_local_fixture as p;print(json.dumps([p.VALUE,sys.prefix!=sys.base_prefix,importlib.util.find_spec("requests") is None]))'])
print(json.dumps({'build':build,'venv':created,'install':installed,'check':json.loads(report)}))
"""
        result = get("python-wsl").run(source)
        self.assertEqual(result["status"], "ok", result)
        report = json.loads(out(result))
        self.assertEqual(report["check"], [42, True, True])
        self.assertLess(sum(report[key] for key in ("build", "venv", "install")), 60)
        assert_clean(self, result)
        print("Kali offline timing:", json.dumps(report))


    def test_setup_module_and_http_server_share_the_linux_script_process(self):
        setup = """import sys,types,threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body=b'local-api'
        self.send_response(200)
        self.send_header('Content-Length',str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self,*args): pass
srv=ThreadingHTTPServer(('127.0.0.1',0),Handler)
threading.Thread(target=srv.serve_forever,daemon=True).start()
mod=types.ModuleType('fixture_api')
mod.PORT=srv.server_port
sys.modules['fixture_api']=mod
"""
        code = "import fixture_api,requests,json,sys\np=fixture_api.PORT\nprint(json.dumps([sys.platform,p,requests.get(f'http://127.0.0.1:{p}/',timeout=2).text]))"
        result = get("python-wsl").run(code, setup=setup)
        self.assertEqual(result["status"], "ok", result)
        platform, port, value = json.loads(out(result))
        self.assertEqual((platform, value), ("linux", "local-api"))
        self.assertNotEqual(linux(f"import socket,json;s=socket.socket();s.settimeout(1);print(json.dumps(s.connect_ex(('127.0.0.1',{port}))))"), 0)
        assert_clean(self, result)
    def test_bad_distribution_fails_without_native_fallback(self):
        with patch.dict(os.environ, {"PAFTA_WSL_DISTRO": "pafta-nonexistent-test-distro"}):
            result = get("python-wsl").run("print('must not run')")
        self.assertEqual(result["status"], "error", result)
        self.assertIn("pafta-nonexistent-test-distro", result["error"]["msg"])
        self.assertEqual(out(result), "")


class WslLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.probe = linux("import tempfile,json;print(json.dumps(tempfile.mkdtemp(prefix='pafta_probe_',dir='/tmp')))")

    def tearDown(self):
        # Clean only this test's recorded descendants if an assertion exposes a
        # regression. Verify process starttime before signalling, never kill by name.
        linux(f"""import json,os,signal,shutil
from pathlib import Path
root=Path({self.probe!r})
assert root.parent==Path('/tmp') and root.name.startswith('pafta_probe_')
for f in root.glob('*.json'):
    pid,start=json.loads(f.read_text())
    try:
        fd=os.pidfd_open(pid)
        stat=Path(f'/proc/{{pid}}/stat').read_text().rsplit(')',1)[1].split()
        if stat[19]==start:
            signal.pidfd_send_signal(fd,signal.SIGKILL)
        os.close(fd)
    except (ProcessLookupError,FileNotFoundError):
        pass
shutil.rmtree(root)
print('true')
""")

    def source(self, finish=False):
        record = "from pathlib import Path\nimport os,json\npid=os.getpid()\nstart=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19]\n"
        grand = record + f"Path({self.probe!r},'grand.json').write_text(json.dumps([pid,start]))\nimport time\ntime.sleep(60)\n"
        child = (record + f"Path({self.probe!r},'child.json').write_text(json.dumps([pid,start]))\n"
                 + "import subprocess,sys,time\n"
                 + f"subprocess.Popen([sys.executable,'-c',{grand!r}],start_new_session=True)\n"
                 + "time.sleep(60)\n")
        return (record + f"Path({self.probe!r},'parent.json').write_text(json.dumps([pid,start]))\n"
                + "import subprocess,sys,time\n"
                + f"subprocess.Popen([sys.executable,'-c',{child!r}],start_new_session=True)\n"
                + f"while not Path({self.probe!r},'grand.json').exists(): time.sleep(.01)\n"
                + f"Path({self.probe!r},'ready').write_text(str(Path.cwd()))\n"
                + ("print('finished')\n" if finish else "time.sleep(60)\n"))

    def ready(self):
        return linux(f"import json,os;print(json.dumps(os.path.exists({self.probe!r}+'/ready')))")

    def await_ready(self):
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if self.ready():
                return
            time.sleep(.1)
        self.fail("Linux descendant fixture never became ready")

    def assert_dead(self):
        report = linux(f"""import json
from pathlib import Path
files=list(Path({self.probe!r}).glob('*.json'))
pids=[json.loads(f.read_text())[0] for f in files]
print(json.dumps([len(pids),[pid for pid in pids if Path(f'/proc/{{pid}}').exists()]]))
""")
        self.assertEqual(report[0], 3, report)
        self.assertEqual(report[1], [], report)

    def test_timeout_kills_detached_children_and_grandchildren(self):
        result = get("python-wsl").run(self.source(), timeout=3)
        self.assertEqual(result["status"], "timeout", result)
        self.assert_dead()
        assert_clean(self, result)

    def test_normal_exit_also_cleans_detached_descendants(self):
        result = get("python-wsl").run(self.source(finish=True))
        self.assertEqual(result["status"], "ok", result)
        self.assert_dead()
        assert_clean(self, result)

    def test_explicit_cancellation_and_concurrent_job_independence(self):
        cancel = threading.Event()
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            pending = pool.submit(get("python-wsl").execute, {"mode": "run", "code": self.source()}, 30, cancel)
            self.await_ready()
            independent = pool.submit(get("python-wsl").run, "import time;time.sleep(.3);print('independent')")
            cancel.set()
            result = pending.result(timeout=15)
            other = independent.result(timeout=15)
        self.assertEqual(result["status"], "cancelled", result)
        self.assertEqual(other["status"], "ok", other)
        self.assertEqual(out(other), "independent\n")
        self.assert_dead()
        assert_clean(self, result)
        assert_clean(self, other)

    def test_setup_and_test_code_share_the_deadline(self):
        for job in (
            {"mode": "test", "code": "value=1", "setup": "import time;time.sleep(60)", "test": "eq(value,1)"},
            {"mode": "test", "code": "value=1", "test": "import time;time.sleep(60);eq(value,1)"},
        ):
            started = time.monotonic()
            result = get("python-wsl").execute(job, timeout=.4)
            self.assertEqual(result["status"], "timeout", result)
            self.assertLess(time.monotonic()-started, 10)
            assert_clean(self, result)

    def test_windows_parent_death_closes_control_and_cleans_linux(self):
        # The host Python process dies without finally; Linux must observe EOF.
        code = ("import sys\nsys.path.insert(0," + repr(str(ROOT)) + ")\n"
                "from engine.runners import get\n"
                "get('python-wsl').run(" + repr(self.source()) + ",timeout=30)\n")
        process = subprocess.Popen([sys.executable, "-c", code], stdin=subprocess.DEVNULL,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   creationflags=wsl_process.NO_WINDOW)
        try:
            self.await_ready()
            process.kill()
            process.wait(timeout=5)
            deadline = time.monotonic()+12
            while time.monotonic()<deadline:
                try:
                    self.assert_dead()
                    remains = linux(f"import json;from pathlib import Path;p=Path({self.probe!r},'ready').read_text();print(json.dumps(Path(p).exists()))")
                    self.assertFalse(remains)
                    return
                except AssertionError:
                    time.sleep(.1)
            self.assert_dead()
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)

    def test_bash_timeout_kills_background_process(self):
        # Bash's pipeline and background work are also owned by the guardian.
        child = ("from pathlib import Path;import os,json,time;"
                 "pid=os.getpid();start=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19];"
                 f"Path({self.probe!r},'bash.json').write_text(json.dumps([pid,start]));time.sleep(60)")
        import shlex
        result = get("bash-wsl").run("/usr/bin/python3 -c " + shlex.quote(child) + " &\nwait\n", timeout=2)
        self.assertEqual(result["status"], "timeout", result)
        report = linux(f"import json,os;from pathlib import Path;pid=json.loads(Path({self.probe!r},'bash.json').read_text())[0];print(json.dumps(os.path.exists(f'/proc/{{pid}}')))")
        self.assertFalse(report)
        assert_clean(self, result)


if __name__ == "__main__":
    unittest.main(verbosity=2)

