# -*- coding: utf-8 -*-
"""Pafta · Python koşum düzeneği.

Ayrı bir süreçte `python -I -X utf8 py_harness.py job.json result.json` olarak
çalışır. Kullanıcının kodunu yakalanmış stdin/stdout ile yürütür; moda göre
testleri koşar, adım adım iz (Röntgen) çıkarır ya da bytecode döker. Sonucu
result.json'a yazar ve os._exit ile çıkar: kullanıcının açık bıraktığı thread'ler
süreci asılı tutmasın.
"""
import ast
import builtins
import contextlib
import difflib
import dis
import io
import json
import linecache
import os
import re
import reprlib
import sqlite3
import subprocess
import sys
import time
import traceback
import types

FNAME = "<kod>"
TEST_FNAME = "<test>"
OUT_LIMIT = 200_000
SHORT_LIMIT = 300
TRACE_LIMIT = 500
VARS_PER_FRAME = 40


# ── çıktı yakalama ────────────────────────────────────────────────────────────

class Capture:
    """stdout / stderr / girdi yankısını tür etiketli parçalar halinde toplar."""

    def __init__(self):
        self.segs = []
        self.size = 0
        self.truncated = False

    def add(self, kind, s):
        if not s or self.truncated:
            return
        room = OUT_LIMIT - self.size
        if len(s) > room:
            s = s[:room]
            self.truncated = True
        self.size += len(s)
        if self.segs and self.segs[-1][0] == kind:
            self.segs[-1][1] += s
        else:
            self.segs.append([kind, s])

    def text(self, kinds=("out",)):
        return "".join(t for k, t in self.segs if k in kinds)

    def plain(self):
        return "".join(t for _, t in self.segs)


class Stream(io.TextIOBase):
    def __init__(self, cap, kind):
        super().__init__()
        self._cap, self._kind = cap, kind

    def writable(self):
        return True

    def write(self, s):
        if not isinstance(s, str):
            raise TypeError(f"write() argümanı str olmalı, {type(s).__name__} geldi")
        self._cap.add(self._kind, s)
        return len(s)

    def flush(self):
        pass

    @property
    def encoding(self):
        return "utf-8"


class Feeder:
    """input() ve sys.stdin için hazır girdi metni."""

    def __init__(self, text, cap, echo):
        self.buf = io.StringIO(text or "")
        self.cap, self.echo = cap, echo

    def input(self, prompt=""):
        # Test modunda (echo=False) soru metni çıktıya yazılmaz: testler
        # input("Sayı: ") ile input() arasında fark görmesin.
        prompt = str(prompt)
        if prompt and self.echo:
            self.cap.add("out", prompt)
        line = self.buf.readline()
        if not line:
            raise EOFError("input() girdi bekledi ama Girdi kutusunda okunacak satır kalmadı")
        if line.endswith("\n"):
            line = line[:-1]
        if line.endswith("\r"):
            line = line[:-1]
        if self.echo:
            self.cap.add("in", line + "\n")
        return line


class Redirect:
    def __init__(self, cap, feeder, argv=None):
        self.cap, self.feeder, self.argv = cap, feeder, argv

    def __enter__(self):
        self.saved = (sys.stdout, sys.stderr, sys.stdin, builtins.input, sys.argv)
        sys.stdout = Stream(self.cap, "out")
        sys.stderr = Stream(self.cap, "err")
        sys.stdin = self.feeder.buf
        builtins.input = self.feeder.input
        sys.argv = ["kod.py"] + list(self.argv or [])
        return self

    def __exit__(self, *exc):
        sys.stdout, sys.stderr, sys.stdin, builtins.input, sys.argv = self.saved
        return False


# ── hata bilgisi ──────────────────────────────────────────────────────────────

def _suggest(e, ns):
    try:
        if isinstance(e, NameError) and getattr(e, "name", None):
            pool = [k for k in ns if not k.startswith("__")] + dir(builtins)
            m = difflib.get_close_matches(e.name, pool, n=1, cutoff=0.7)
            return m[0] if m else None
        if isinstance(e, AttributeError) and getattr(e, "name", None):
            obj = getattr(e, "obj", None)
            if obj is not None:
                pool = [a for a in dir(obj) if not a.startswith("__")]
                m = difflib.get_close_matches(e.name, pool, n=1, cutoff=0.7)
                return m[0] if m else None
    except Exception:
        pass
    return None


def err_info(e, ns=None, where="kod"):
    if isinstance(e, SyntaxError):
        return {
            "type": type(e).__name__, "msg": e.msg, "line": e.lineno, "col": e.offset,
            "text": (e.text or "").rstrip("\n"), "frames": [],
            "where": "test" if e.filename == TEST_FNAME else where,
        }
    tb = traceback.extract_tb(e.__traceback__)
    frames = [{"line": f.lineno, "func": f.name, "text": (f.line or "").strip()}
              for f in tb if f.filename == FNAME]
    info = {
        "type": type(e).__name__, "msg": str(e), "frames": frames,
        "line": frames[-1]["line"] if frames else None, "where": where,
    }
    s = _suggest(e, ns or {})
    if s:
        info["suggest"] = s
    return info


def short(v):
    try:
        r = repr(v)
    except Exception as e:  # kullanıcının __repr__'ı patlayabilir
        r = f"<repr hatası: {type(e).__name__}>"
    return r if len(r) <= SHORT_LIMIT else r[:SHORT_LIMIT] + "…"


# ── kullanıcı kodunu yürütme ──────────────────────────────────────────────────

def register_source(code):
    linecache.cache[FNAME] = (len(code), None, code.splitlines(True), FNAME)


@contextlib.contextmanager
def ana_modul(kalici=False):
    """Kullanıcı kodu gerçek bir __main__ modülünde koşsun: pickle gibi sınıfı
    __main__.Ad diye arayanlar, kodda tanımlanan sınıfları bulabilsin.
    kalici: test modunda modül, testler bitene kadar __main__ olarak kalır."""
    mod = types.ModuleType("__main__")
    mod.__dict__.update({"__builtins__": builtins, "__file__": "kod.py"})
    eski = sys.modules["__main__"]
    sys.modules["__main__"] = mod
    try:
        yield mod.__dict__
    finally:
        if not kalici:
            sys.modules["__main__"] = eski


def exec_user(code, stdin="", echo=False, argv=None, kalici=False):
    cap = Capture()
    feeder = Feeder(stdin, cap, echo)
    err = None
    with Redirect(cap, feeder, argv), ana_modul(kalici) as ns:
        try:
            exec(compile(code, FNAME, "exec"), ns)
        except SystemExit as e:
            if e.code not in (None, 0):
                cap.add("err", f"[program sys.exit({e.code!r}) ile bitti]\n")
        except BaseException as e:
            err = err_info(e, ns)
    return ns, cap, err


def run_setup(job):
    # Yolun ortak veri dosyaları (ör. PowerShell'in olaylar.json'u) her çalıştırmada klasöre kopyalanır
    for yol in job.get("kopyala") or []:
        if os.path.isfile(yol):
            with open(yol, "rb") as kaynak, open(os.path.basename(yol), "wb") as hedef:
                hedef.write(kaynak.read())
    setup = job.get("setup")
    if not setup:
        return
    sink = Capture()
    with Redirect(sink, Feeder("", sink, False)):
        exec(compile(setup, "<setup>", "exec"), {"__name__": "__setup__"})


def do_run(job):
    run_setup(job)
    _, cap, err = exec_user(job["code"], job.get("stdin", ""), echo=True, argv=job.get("argv"))
    return {"status": "error" if err else "ok", "segs": cap.segs,
            "truncated": cap.truncated, "error": err}


# ── test modu ─────────────────────────────────────────────────────────────────

class Stop(Exception):
    """Test erken bitsin (ön koşul sağlanmadı)."""


class UserRunError(Exception):
    def __init__(self, info, stdin):
        super().__init__(info.get("msg", ""))
        self.info, self.stdin = info, stdin


KINDS = {
    "for": ast.For, "while": ast.While, "if": ast.If, "def": ast.FunctionDef,
    "class": ast.ClassDef, "lambda": ast.Lambda, "listcomp": ast.ListComp,
    "dictcomp": ast.DictComp, "setcomp": ast.SetComp, "genexp": ast.GeneratorExp,
    "yield": (ast.Yield, ast.YieldFrom), "yieldfrom": ast.YieldFrom, "with": ast.With,
    "try": tuple(t for t in (ast.Try, getattr(ast, "TryStar", None)) if t),
    "fstring": ast.JoinedStr, "match": ast.Match, "asyncdef": ast.AsyncFunctionDef,
    "await": ast.Await, "asyncfor": ast.AsyncFor, "asyncwith": ast.AsyncWith,
    "return": ast.Return, "global": ast.Global, "nonlocal": ast.Nonlocal,
    "break": ast.Break, "continue": ast.Continue, "ifexp": ast.IfExp,
    "raise": ast.Raise, "assert": ast.Assert, "import": (ast.Import, ast.ImportFrom),
    "walrus": ast.NamedExpr, "slice": ast.Slice, "starred": ast.Starred,
    "augassign": ast.AugAssign, "comp": (ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp),
}


def _same(got, exp):
    """== eşitliği + makul tür uyumu: 1 ile True, '5' ile 5 karışmasın."""
    try:
        if not bool(got == exp):
            return False
    except Exception:
        return False
    if isinstance(exp, bool) or isinstance(got, bool):
        return isinstance(got, bool) and isinstance(exp, bool)
    if isinstance(exp, (int, float)) and isinstance(got, (int, float)):
        return True
    return isinstance(got, type(exp))


class Tester:
    def __init__(self, code, ns, cap, stdin, job):
        self.code, self.ns, self.cap, self.stdin, self.job = code, ns, cap, stdin, job
        self.results = []
        try:
            self.tree = ast.parse(code)
        except SyntaxError:
            self.tree = ast.parse("")

    def _rec(self, ok, msg, got=None, exp=None):
        r = {"ok": bool(ok), "msg": msg or "Koşul"}
        if not ok:
            if got is not None:
                r["got"] = got
            if exp is not None:
                r["exp"] = exp
        self.results.append(r)
        return bool(ok)

    # — karşılaştırmalar —
    def eq(self, got, exp, msg=None):
        return self._rec(_same(got, exp), msg or f"Beklenen: {short(exp)}", short(got), short(exp))

    def ok(self, cond, msg=None, got=None):
        return self._rec(bool(cond), msg, None if got is None else short(got))

    def yakin(self, got, exp, msg=None, tol=1e-6):
        try:
            same = abs(got - exp) <= tol
        except Exception:
            same = False
        return self._rec(same, msg or f"≈ {exp!r}", short(got), short(exp))

    def raises(self, exc, fn, *a, msg=None, **kw):
        try:
            fn(*a, **kw)
        except exc:
            return self._rec(True, msg or f"{exc.__name__} yükseltmeli")
        except Exception as e:
            return self._rec(False, msg or f"{exc.__name__} yükseltmeli",
                             f"{type(e).__name__}: {e}", exc.__name__)
        return self._rec(False, msg or f"{exc.__name__} yükseltmeli", "hata yükselmedi", exc.__name__)

    # — program düzeyi —
    def run(self, stdin="", argv=None):
        _, cap, err = exec_user(self.code, stdin, echo=False, argv=argv)
        if err:
            raise UserRunError(err, stdin)
        return cap.text()

    def run_code(self, code, stdin="", argv=None):
        """Kullanıcının kodunun değiştirilmiş bir halini çalıştır (ör. sabit değeri başka değerle)."""
        _, cap, err = exec_user(code, stdin, echo=False, argv=argv)
        if err:
            raise UserRunError(err, stdin)
        return cap.text()

    def capture(self, fn, *a, **kw):
        cap = Capture()
        with Redirect(cap, Feeder("", cap, False)):
            res = fn(*a, **kw)
        return res, cap.text()

    # — kaynak analizi —
    def uses(self, kind):
        if kind == "decorator":
            return any(getattr(n, "decorator_list", None) for n in ast.walk(self.tree))
        t = KINDS[kind]
        return any(isinstance(n, t) for n in ast.walk(self.tree))

    def calls(self, name):
        for n in ast.walk(self.tree):
            if isinstance(n, ast.Call):
                f = n.func
                if (isinstance(f, ast.Name) and f.id == name) or (isinstance(f, ast.Attribute) and f.attr == name):
                    return True
        return False

    def need(self, name, what="fonksiyon"):
        obj = self.ns.get(name)
        if obj is None or (what == "fonksiyon" and not callable(obj)):
            self._rec(False, f"`{name}` adında bir {what} tanımlamalısın",
                      "bulunamadı", name)
            raise Stop()
        if what == "sınıf" and not isinstance(obj, type):
            self._rec(False, f"`{name}` bir sınıf (class) olmalı", type(obj).__name__, "class")
            raise Stop()
        return obj

    def stop(self):
        raise Stop()

    def namespace(self):
        out = self.cap.text()
        tns = dict(self.ns)
        tns.update(
            eq=self.eq, ok=self.ok, yakin=self.yakin, raises=self.raises, run=self.run,
            run_code=self.run_code,
            capture=self.capture, uses=self.uses, calls=self.calls, need=self.need,
            stop=self.stop, out=out, lines=[l.rstrip() for l in out.strip("\n").splitlines()],
            src=self.code, tree=self.tree, kullanici=self.ns, girdi=self.stdin,
            __name__="__test__", __builtins__=builtins,
        )
        return tns


def test_error(e, tns):
    if isinstance(e, UserRunError):
        info = dict(e.info)
        info["where"] = "kod-girdi"
        info["stdin"] = e.stdin
        return info
    tb = traceback.extract_tb(e.__traceback__)
    in_user = any(f.filename == FNAME for f in tb)
    if in_user:
        return err_info(e, tns, where="kod-test")
    info = err_info(e, tns, where="test")
    if isinstance(e, NameError) and getattr(e, "name", None):
        info["missing"] = e.name
    return info


def do_test(job):
    run_setup(job)
    code, stdin = job["code"], job.get("stdin", "")
    ns, cap, err = exec_user(code, stdin, echo=False, argv=job.get("argv"), kalici=True)
    if err:
        return {"status": "error", "segs": cap.segs, "error": err, "checks": []}
    tester = Tester(code, ns, cap, stdin, job)
    tns = tester.namespace()
    return _test_kos(tester, tns, job, cap.segs)


def _test_kos(tester, tns, job, segs):
    """Görev testini (Python) verilen ad alanında koş ve sonucu paketle."""
    tcap = Capture()
    exc = None
    with Redirect(tcap, Feeder(job.get("stdin", ""), tcap, False)):
        try:
            exec(compile(job["test"], TEST_FNAME, "exec"), tns)
        except Stop:
            pass
        except AssertionError as e:
            tester._rec(False, str(e) or "Bir test koşulu sağlanmadı")
        except BaseException as e:
            exc = test_error(e, tns)
    passed = exc is None and bool(tester.results) and all(r["ok"] for r in tester.results)
    return {"status": "pass" if passed else "fail", "checks": tester.results,
            "segs": segs, "error": exc}


# ── Röntgen: adım adım iz ─────────────────────────────────────────────────────

_rep = reprlib.Repr()
_rep.maxlevel, _rep.maxlist, _rep.maxtuple, _rep.maxset = 3, 12, 12, 12
_rep.maxdict, _rep.maxstring, _rep.maxother, _rep.maxlong = 10, 70, 90, 60
_rep.maxfrozenset, _rep.maxdeque, _rep.maxarray = 12, 12, 12


def ser(v):
    t = type(v)
    if isinstance(v, types.FunctionType):
        r = f"<fonksiyon {v.__name__}>"
    elif isinstance(v, type):
        r = f"<sınıf {v.__name__}>"
    elif isinstance(v, types.MethodType):
        r = f"<metot {v.__func__.__name__}>"
    else:
        try:
            r = _rep.repr(v)
        except Exception as e:
            r = f"<repr hatası: {type(e).__name__}>"
    if len(r) > 160:
        r = r[:160] + "…"
    return {"t": t.__name__, "r": r, "id": id(v)}


def _vars(d):
    out = []
    for k, v in d.items():
        if k.startswith("__") or isinstance(v, types.ModuleType):
            continue
        out.append([k, ser(v)])
        if len(out) >= VARS_PER_FRAME:
            break
    return out


def do_trace(job):
    run_setup(job)
    code = job["code"]
    try:
        compiled = compile(code, FNAME, "exec")
    except SyntaxError as e:
        return {"status": "error", "error": err_info(e), "steps": [], "out": ""}
    cap = Capture()
    feeder = Feeder(job.get("stdin", ""), cap, True)
    steps = []
    state = {"over": False}

    def record(frame, event, arg):
        if len(steps) >= TRACE_LIMIT:
            state["over"] = True
            sys.settrace(None)
            return
        chain, f = [], frame
        while f is not None:
            if f.f_code.co_filename == FNAME:
                chain.append(f)
            f = f.f_back
        chain.reverse()
        frames = []
        for fr in chain:
            local = fr.f_globals if fr.f_code.co_name == "<module>" else fr.f_locals
            frames.append({"name": fr.f_code.co_name, "line": fr.f_lineno, "vars": _vars(local)})
        step = {"ev": event, "line": frame.f_lineno, "frames": frames, "out": cap.size}
        if event == "return":
            step["ret"] = ser(arg)
        elif event == "exception":
            step["exc"] = f"{arg[0].__name__}: {arg[1]}"
        steps.append(step)

    def tracer(frame, event, arg):
        if frame.f_code.co_filename != FNAME:
            return None
        if event in ("line", "return", "exception"):
            record(frame, event, arg)
        return tracer

    err = None
    with Redirect(cap, feeder), ana_modul() as ns:
        sys.settrace(tracer)
        try:
            exec(compiled, ns)
        except SystemExit:
            pass
        except BaseException as e:
            err = err_info(e, ns)
        finally:
            sys.settrace(None)
    return {"status": "error" if err else "ok", "steps": steps, "truncated": state["over"],
            "out": cap.plain(), "error": err}


def do_dis(job):
    buf = io.StringIO()
    try:
        dis.dis(compile(job["code"], FNAME, "exec"), file=buf)
    except SyntaxError as e:
        return {"status": "error", "error": err_info(e), "text": ""}
    return {"status": "ok", "text": buf.getvalue()}


# ── Regex yolu: kod = desen, girdi = aranacak metin ───────────────────────────

def _desen(code):
    return (code or "").rstrip("\r\n")


def _pcre2():
    # Adımın meta'sında motor: pcre2 → sandbox/pcre2_engine.py (gerçek PCRE2 kitaplığı)
    return _cevirici("pcre2_engine")


def _regex_derle(desen, motor=None):
    if motor in ("pcre2", "dotnet", "javascript"):
        try:
            if motor == "pcre2":
                return _pcre2().compile(desen), None
            # Adımın meta'sında motor: dotnet / javascript → sandbox/regex_motorlar.py (gerçek motor ayrı süreçte)
            return _cevirici("regex_motorlar").compile(desen, motor), None
        except Exception as e:
            konum = getattr(e, "pos", None)
            satir = desen.count("\n", 0, konum) + 1 if konum is not None else 1
            col = konum - (desen.rfind("\n", 0, konum) + 1) if konum is not None else None
            ad = {"pcre2": "PCRE2", "dotnet": ".NET", "javascript": "JavaScript"}[motor]
            return None, {"type": "DesenHatası", "msg": ad + ": " + getattr(e, "msg", str(e)), "line": satir,
                          "col": col, "frames": [], "where": "kod",
                          "text": (desen.splitlines() or [""])[min(satir, max(1, len(desen.splitlines()))) - 1]}
    try:
        return re.compile(desen), None
    except re.error as e:
        satir = e.lineno or 1
        return None, {"type": "DesenHatası", "msg": e.msg, "line": satir,
                      "col": e.colno if e.colno is not None else e.pos, "frames": [], "where": "kod",
                      "text": (desen.splitlines() or [""])[min(satir, max(1, len(desen.splitlines()))) - 1]}


def do_regex_run(job):
    rx, err = _regex_derle(_desen(job["code"]), job.get("motor"))
    if err:
        return {"status": "error", "error": err, "segs": []}
    metin = job.get("stdin", "")
    es = []
    try:
        for m in rx.finditer(metin):
            es.append({"bas": m.start(), "son": m.end(), "metin": m.group(0),
                       "gruplar": list(m.groups()), "adli": m.groupdict()})
            if len(es) >= 500:
                break
    except Exception as e:                    # PCRE2/.NET eşleşme sınırı ya da zaman aşımı: felaket geri izleme
        if job.get("motor") not in ("pcre2", "dotnet", "javascript"):
            raise
        return {"status": "error", "segs": [], "error": {"type": "EşleşmeHatası", "msg": getattr(e, "msg", str(e)),
                                                          "line": None, "frames": [], "where": "kod"}}
    cikti = "".join(e["metin"] + "\n" for e in es)
    return {"status": "ok", "segs": [["out", cikti]] if cikti else [], "eslesmeler": es,
            "metin": metin[:50_000], "error": None}


def do_regex_test(job):
    desen = _desen(job["code"])
    rx, err = _regex_derle(desen, job.get("motor"))
    if err:
        return {"status": "error", "error": err, "checks": [], "segs": []}
    tester = Tester("", {}, Capture(), job.get("stdin", ""), job)
    tns = tester.namespace()

    def ilk(s):
        return rx.search(s)

    tns.update(
        desen=desen, src=desen, rx=rx,
        eslesir=lambda s: rx.search(s) is not None,
        tam=lambda s: rx.fullmatch(s) is not None,
        bul=lambda s: [m.group(0) for m in rx.finditer(s)],
        grup=lambda s, i=1: (ilk(s).group(i) if ilk(s) else None),
        gruplar=lambda s: (ilk(s).groups() if ilk(s) else None),
        adli=lambda s: (ilk(s).groupdict() if ilk(s) else None),
        hepsi=lambda s: [m.groupdict() or m.groups() for m in rx.finditer(s)],
        degistir=lambda s, yeni, n=0: rx.sub(yeni, s, count=n),
        bol=lambda s: rx.split(s),
    )
    return _test_kos(tester, tns, job, [])


def do_regex_dis(job):
    desen = _desen(job["code"])
    if job.get("motor") in ("pcre2", "dotnet", "javascript"):
        motor = job["motor"]
        rx, err = _regex_derle(desen, motor)
        if err:
            return {"status": "error", "error": err, "text": ""}
        if motor == "pcre2":
            return {"status": "ok", "text": _pcre2().bilgi(desen)}
        return {"status": "ok", "text": _cevirici("regex_motorlar").bilgi(desen, motor)}
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            re.compile(desen, re.DEBUG)
    except re.error:
        return {"status": "error", "error": _regex_derle(desen)[1], "text": ""}
    return {"status": "ok", "text": buf.getvalue()}


# ── Süreç yolları (Bash, PowerShell): kod bir betik dosyasına yazılıp çalışır ──

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _betik_yaz(job, iz=False):
    p = job["proc"]
    on_ek = p.get("on_ek", "") + (p.get("iz_on_ek", "") if iz else "")
    with open(p["dosya"], "w", encoding="utf-8-sig" if p.get("bom") else "utf-8", newline="\n") as f:
        f.write(on_ek + (job.get("code") or "").replace("\r\n", "\n"))
    return on_ek.count("\n")


def _calistir(job, stdin="", argv=None, iz=False):
    """(kod, stdout, stderr, kayma) ya da zaman aşımında None."""
    p = job["proc"]
    if p.get("batch"):
        import runpy
        execute = runpy.run_path(os.path.join(os.path.dirname(__file__), "cmd_process.py"))["run_batch"]
        return execute(job, stdin, argv)
    kayma = _betik_yaz(job, iz=iz)
    hedef = p["dosya"]
    if p.get("sarmal"):
        # Hazırlık (kodlama, Girdi) betiğin içine değil ayrı bir sarmalayıcıya yazılır:
        # böylece param() ilk ifade kalır ve hata satır numaraları kaymaz.
        sarmal = p["sarmal"].replace("{IZ}", p.get("iz_satiri", "") if iz else "")
        with open(p["sarmal_dosya"], "w", encoding="utf-8-sig", newline="\n") as f:
            f.write(sarmal)
        hedef = p["sarmal_dosya"]
    cmd = list(p["iz_cmd"] if iz and p.get("iz_cmd") else p["cmd"]) + [hedef] + [str(a) for a in (argv or [])]
    env = dict(os.environ)
    env.update(p.get("env", {}))
    try:
        r = subprocess.run(cmd, input=(stdin or "").encode("utf-8"), capture_output=True,
                           timeout=p.get("sure", 15), env=env, creationflags=NO_WINDOW)
    except subprocess.TimeoutExpired:
        return None
    return (r.returncode, r.stdout.decode("utf-8", "replace").replace("\r\n", "\n"),
            r.stderr.decode("utf-8", "replace").replace("\r\n", "\n"), kayma)


def _hata_satiri(job, metin, kayma):
    desen = job["proc"].get("satir_deseni")
    if not desen:
        return None
    m = re.search(desen, metin)
    if not m:
        return None
    n = int(m.group(1)) - kayma
    return n if n >= 1 else None


def _surec_hatasi(job, kod, hata, kayma):
    son = [s for s in hata.splitlines() if s.strip()]
    return {"type": "ÇıkışKodu", "msg": f"betik {kod} koduyla bitti" + (f": {son[0].strip()}" if son else ""),
            "line": _hata_satiri(job, hata, kayma), "frames": [], "where": "kod", "kod": kod}


def _zaman_asimi(job):
    return {"type": "Zaman aşımı", "msg": f"Betik {job['proc'].get('sure', 15)} saniyede bitmedi.",
            "line": None, "frames": [], "where": "kod"}


def do_proc_run(job):
    run_setup(job)
    r = _calistir(job, job.get("stdin", ""), job.get("argv"))
    if r is None:
        return {"status": "timeout", "segs": [], "error": _zaman_asimi(job)}
    kod, cikti, hata, kayma = r
    segs = [["out", cikti]] if cikti else []
    if hata:
        segs.append(["err", hata])
    err = _surec_hatasi(job, kod, hata, kayma) if kod != 0 else None
    res = {"status": "error" if err else "ok", "segs": segs, "error": err, "kod": kod}
    if not err and hata:
        res["uyari_satir"] = _hata_satiri(job, hata, kayma)
    return res


def do_proc_trace(job):
    run_setup(job)
    r = _calistir(job, job.get("stdin", ""), job.get("argv"), iz=True)
    if r is None:
        return {"status": "timeout", "steps": [], "error": _zaman_asimi(job)}
    kod, cikti, hata, kayma = r
    desen = re.compile(job["proc"]["iz_deseni"])
    disla = job["proc"].get("iz_disla", [])
    adimlar, temiz = [], []
    for kaynak, metin in (("out", cikti), ("err", hata)):
        for satir in metin.splitlines():
            m = desen.match(satir)
            if m and any(d in satir for d in disla):
                continue
            if m:
                n = int(m.group("satir")) - kayma
                if n >= 1:
                    adimlar.append({"line": n, "metin": m.group("komut").replace(">>>>", "").strip(),
                                    "derinlik": len(m.groupdict().get("derinlik") or "+")})
            elif kaynak == "out":
                temiz.append(satir)
    hata_temiz = "\n".join(s for s in hata.splitlines() if not desen.match(s))
    err = _surec_hatasi(job, kod, hata_temiz, kayma) if kod != 0 else None
    return {"status": "error" if err else "ok", "kind": "iz", "iz": adimlar[:TRACE_LIMIT],
            "out": "\n".join(temiz) + ("\n" if temiz else ""), "error": err}


class ProcTester(Tester):
    def __init__(self, job, cikti):
        super().__init__("", {}, Capture(), job.get("stdin", ""), job)
        self.cap.add("out", cikti)
        self.code = job.get("code", "")

    def calis(self, stdin="", argv=None):
        r = _calistir(self.job, stdin, argv)
        if r is None:
            raise TimeoutError("betik zaman aşımına uğradı")
        return {"kod": r[0], "cikti": r[1], "hata": r[2]}

    def run(self, stdin="", argv=None):
        r = self.calis(stdin, argv)
        if r["kod"] != 0:
            raise UserRunError(_surec_hatasi(self.job, r["kod"], r["hata"], 0), stdin)
        return r["cikti"]

    def run_code(self, code, stdin="", argv=None):
        r = _calistir(dict(self.job, code=code), stdin, argv)
        if r is None:
            raise TimeoutError("betik zaman aşımına uğradı")
        if r[0] != 0:
            raise UserRunError(_surec_hatasi(self.job, r[0], r[2], 0), stdin)
        return r[1]


def do_proc_test(job):
    run_setup(job)
    r = _calistir(job, job.get("stdin", ""), job.get("argv"))
    if r is None:
        return {"status": "timeout", "checks": [], "segs": [], "error": _zaman_asimi(job)}
    kod, cikti, hata, kayma = r
    segs = [["out", cikti]] if cikti else []
    if hata:
        segs.append(["err", hata])
    if kod != 0:
        return {"status": "error", "checks": [], "segs": segs, "error": _surec_hatasi(job, kod, hata, kayma)}
    tester = ProcTester(job, cikti)
    tns = tester.namespace()
    tns.update(calis=tester.calis, run=tester.run, src=job.get("code", ""), hata_cikti=hata)
    return _test_kos(tester, tns, job, segs)


# ── SQL yolu: bellek içi SQLite; örnek veritabanı + görevin hazırlığı + kullanıcının betiği ──

SQL_SATIR_LIMIT = 500
_SQL_BASI = re.compile(r"(?:\s+|--[^\n]*(?:\n|$)|/\*.*?\*/)*", re.S)
_SQL_HATA_TR = [
    (r"no such table: (\S+)", "böyle bir tablo yok: {0}"),
    (r"no such column: (\S+)", "böyle bir sütun yok: {0}"),
    (r'near "(.+?)": syntax error', 'sözdizimi hatası, şunun yakınında: "{0}"'),
    (r"incomplete input", "ifade yarım kaldı (kapanmamış parantez ya da tırnak?)"),
    (r"unrecognized token: (.+)", "tanınmayan simge: {0} (kapanmamış tırnak?)"),
    (r"ambiguous column name: (\S+)", "sütun adı belirsiz: {0} (birden çok tabloda var; tablo.sütun biçiminde yaz)"),
    (r"misuse of aggregate(?: function)?:? (\S+)", "toplama fonksiyonu yanlış yerde: {0} (WHERE yerine HAVING mi olmalı?)"),
    (r"a GROUP BY clause is required before HAVING", "HAVING için önce GROUP BY gerekir"),
    (r"(UNIQUE|NOT NULL|CHECK|FOREIGN KEY|PRIMARY KEY) constraint failed:? ?(.*)", "{0} kısıtı ihlal edildi {1}"),
    (r"table (\S+) already exists", "{0} tablosu zaten var"),
    (r"(\d+) values for (\d+) columns", "{1} sütuna {0} değer verildi"),
    (r"no such function: (\S+)", "böyle bir fonksiyon yok: {0}"),
    (r"wrong number of arguments to function (\S+)", "{0} fonksiyonuna yanlış sayıda argüman verildi"),
    (r"sub-select returns (\d+) columns - expected 1", "alt sorgu {0} sütun döndürüyor, 1 bekleniyordu"),
    (r"cannot start a transaction within a transaction", "açık bir işlem varken yeni BEGIN yazılamaz"),
    (r"cannot commit - no transaction is active", "COMMIT için açık bir işlem yok"),
]


def _sql_parcala(kod):
    """Betiği ifadelere böl → [(ifade, başladığı satır)]. Tırnak, yorum ya da tetikleyici içindeki ; bölmez."""
    kod = (kod or "").replace("\r\n", "\n")
    sonuc, bas = [], 0
    for m in re.finditer(";", kod):
        parca = kod[bas:m.end()]
        if sqlite3.complete_statement(parca):
            sonuc.append((parca, bas))
            bas = m.end()
    if kod[bas:].strip():
        sonuc.append((kod[bas:], bas))
    cikti = []
    for parca, konum in sonuc:
        on = _SQL_BASI.match(parca).end()
        govde = parca[on:]
        if not govde.strip().rstrip(";").strip():
            continue                              # yalnızca yorum ya da boş ifade
        cikti.append((govde, kod.count("\n", 0, konum + on) + 1))
    return cikti


def _sql_hatasi(e, satir=None, ifade=""):
    ham = str(e)
    msg = ham
    for desen, tr in _SQL_HATA_TR:
        m = re.search(desen, ham)
        if m:
            msg = tr.format(*m.groups()).strip() + f"  ·  ({ham})"
            break
    # Hatanın geçtiği satırı ifadenin içinde bul: hatalı simge ya da (toplama hatasında) WHERE
    kayma = 0
    m = re.search(r'near "(.+?)"|no such (?:column|table|function): (\S+)|ambiguous column name: (\S+)', ham)
    simge = next((g for g in m.groups() if g), None) if m else None
    konum = -1
    if simge:
        konum = ifade.find(simge)
    elif "misuse of aggregate" in ham:
        w = re.search(r"\bWHERE\b", ifade, re.I)
        konum = w.start() if w else -1
    if konum >= 0:
        kayma = ifade[:konum].count("\n")
    satirlar = ifade.split("\n")
    metin = satirlar[kayma] if kayma < len(satirlar) else ""
    return {"type": "SQLHatası", "msg": msg, "line": None if satir is None else satir + kayma,
            "frames": [], "where": "kod", "text": metin}


def _sql_deger(v):
    if v is None:
        return "NULL"
    if isinstance(v, bytes):
        return "x'" + v.hex() + "'"
    return str(v)


def _sql_baglan(job, ek=""):
    db = sqlite3.connect(":memory:", isolation_level=None)    # işlemleri kullanıcı yönetir
    db.execute("PRAGMA foreign_keys = ON")
    for parca in (job.get("tohum_sql"), job.get("setup"), ek):
        if parca:
            db.executescript(parca)
    return db


def _sql_kos(db, kod):
    """Betiği ifade ifade çalıştır → (tablolar, ham satırlar listesi, hata)."""
    tablolar, hamlar = [], []
    for ifade, satir in _sql_parcala(kod):
        try:
            cur = db.execute(ifade)
            if cur.description:
                sutunlar = [d[0] for d in cur.description]
                satirlar = cur.fetchmany(SQL_SATIR_LIMIT + 1)
                kesildi = len(satirlar) > SQL_SATIR_LIMIT
                satirlar = [tuple(r) for r in satirlar[:SQL_SATIR_LIMIT]]
                hamlar.append(satirlar)
                tablolar.append({"satir": satir, "sutunlar": sutunlar, "kesildi": kesildi,
                                 "satirlar": [[None if v is None else _sql_deger(v) for v in r] for r in satirlar]})
            else:
                komut = ifade.split(None, 1)[0].upper()
                if komut in ("INSERT", "UPDATE", "DELETE", "REPLACE"):
                    tablolar.append({"satir": satir, "komut": komut, "degisen": cur.rowcount})
                else:
                    tablolar.append({"satir": satir, "komut": komut})
        except sqlite3.Error as e:
            return tablolar, hamlar, _sql_hatasi(e, satir, ifade)
    return tablolar, hamlar, None


def _sql_metin(tablolar):
    """sqlite3 kabuğunun 'list' biçimi: başlıksız, değerler | ile ayrık, NULL açıkça."""
    return "".join("|".join("NULL" if v is None else v for v in r) + "\n"
                   for t in tablolar if "sutunlar" in t for r in t["satirlar"])


def _sql_tohum(job):
    yol = job.get("tohum")
    if yol and os.path.isfile(yol) and "tohum_sql" not in job:
        with open(yol, encoding="utf-8") as f:
            job["tohum_sql"] = f.read()


def _sql_hazirla(job):
    _sql_tohum(job)
    try:
        return _sql_baglan(job), None
    except sqlite3.Error as e:
        return None, dict(_sql_hatasi(e), where="test", msg="Görevin hazırlık verisi yüklenemedi: " + str(e))


def do_sql_run(job):
    db, err = _sql_hazirla(job)
    if err:
        return {"status": "error", "error": err, "segs": [], "tablolar": []}
    tablolar, _, err = _sql_kos(db, job["code"])
    cikti = _sql_metin(tablolar)
    return {"status": "error" if err else "ok", "segs": [["out", cikti]] if cikti else [],
            "tablolar": tablolar, "error": err}


class SqlTester(Tester):
    def __init__(self, job, db, hamlar, cikti):
        super().__init__("", {}, Capture(), "", job)
        self.cap.add("out", cikti)
        self.code = job.get("code", "")
        self.db = db
        self.hamlar = hamlar

    def sorgu(self, sql, *params):
        """Kullanıcının betiğinden SONRAKİ veritabanında bir sorgu çalıştır."""
        return [tuple(r) for r in self.db.execute(sql, params).fetchall()]

    def dene(self, hazirlik=""):
        """Temiz bir veritabanına `hazirlik`ı ekleyip kullanıcının betiğini yeniden çalıştır → son sorgunun satırları."""
        db = _sql_baglan(self.job, hazirlik)
        _, hamlar, err = _sql_kos(db, self.code)
        if err:
            raise UserRunError(err, hazirlik)
        return hamlar[-1] if hamlar else []

    def kullanir(self, kelime):
        """Anahtar kelime betikte (yorum ve metinler dışında) geçiyor mu? 'group by' gibi çok kelimeli olabilir."""
        temiz = re.sub(r"--[^\n]*|/\*.*?\*/|'(?:[^']|'')*'", " ", self.code, flags=re.S)
        desen = r"\b" + r"\s+".join(map(re.escape, kelime.split())) + r"\b"
        return re.search(desen, temiz, re.I) is not None


def do_sql_test(job):
    db, err = _sql_hazirla(job)
    if err:
        return {"status": "error", "error": err, "checks": [], "segs": []}
    tablolar, hamlar, err = _sql_kos(db, job["code"])
    cikti = _sql_metin(tablolar)
    segs = [["out", cikti]] if cikti else []
    if err:
        return {"status": "error", "checks": [], "segs": segs, "error": err}
    tester = SqlTester(job, db, hamlar, cikti)
    tns = tester.namespace()
    son = next((t for t in reversed(tablolar) if "sutunlar" in t), None)
    tns.update(src=job.get("code", ""), sonuc=hamlar[-1] if hamlar else [], sonuclar=hamlar,
               sutunlar=son["sutunlar"] if son else [], sorgu=tester.sorgu, dene=tester.dene,
               kullanir=tester.kullanir)
    return _test_kos(tester, tns, job, segs)


_PLAN_NOTU = [
    (r"^SCAN ", "tablonun tamamı satır satır okunuyor"),
    (r"^SEARCH .* USING (?:COVERING )?INDEX", "indeksle doğrudan arama"),
    (r"^SEARCH .* USING (?:INTEGER )?PRIMARY KEY", "birincil anahtarla doğrudan erişim"),
    (r"USE TEMP B-TREE FOR (ORDER BY|GROUP BY|DISTINCT)", "sıralamak/gruplamak için geçici yapı kuruluyor"),
    (r"^CORRELATED ", "her dış satır için yeniden çalışan alt sorgu"),
    (r"^(?:LIST )?SUBQUERY|^SCALAR SUBQUERY", "alt sorgu"),
    (r"^MATERIALIZE|^CO-ROUTINE", "ara sonuç (CTE ya da alt sorgu) hazırlanıyor"),
    (r"AUTOMATIC .*INDEX", "SQLite bu sorgu için geçici bir indeks kuruyor"),
]


def do_sql_dis(job):
    db, err = _sql_hazirla(job)
    if err:
        return {"status": "error", "error": err, "text": ""}
    satirlar = []
    for ifade, satir in _sql_parcala(job["code"]):
        bas = ifade.split(None, 1)[0].upper()
        try:
            if bas not in ("SELECT", "WITH", "VALUES"):
                db.execute(ifade)                 # CREATE INDEX vb. planı etkilesin diye uygulanır
                continue
            plan = db.execute("EXPLAIN QUERY PLAN " + ifade).fetchall()
        except sqlite3.Error as e:
            return {"status": "error", "error": _sql_hatasi(e, satir, ifade), "text": ""}
        satirlar.append(f"-- satır {satir}: {' '.join(ifade.split())[:70]}")
        derinlik = {0: -1}
        for kimlik, ust, _, detay in plan:
            d = derinlik.get(ust, -1) + 1
            derinlik[kimlik] = d
            not_ = next((n for desen, n in _PLAN_NOTU if re.search(desen, detay)), "")
            satirlar.append("   " * d + detay + (f"    ← {not_}" if not_ else ""))
        satirlar.append("")
    if not satirlar:
        satirlar = ["(planı gösterilecek SELECT sorgusu yok)"]
    return {"status": "ok", "text": "\n".join(satirlar)}


# ── KQL ve SPL yolları: sandbox/kql.py ve sandbox/spl.py sorguyu SQLite'a çevirir,
#    SQL yolunun veritabanında çalışır ──

_CEVIRICILER = {}


def _cevirici(ad):
    if ad not in _CEVIRICILER:
        import importlib.util
        yol = os.path.join(os.path.dirname(os.path.abspath(__file__)), ad + ".py")
        spec = importlib.util.spec_from_file_location("pafta_" + ad, yol)
        modul = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modul)
        _CEVIRICILER[ad] = modul
    return _CEVIRICILER[ad]


def _sorgu_bloklari(kod):
    """Boş satırla ayrılmış her blok ayrı bir sorgudur → [(blok, başladığı satır)]."""
    satirlar = (kod or "").replace("\r\n", "\n").split("\n")
    bloklar, simdiki, bas = [], [], 0
    for n, s in enumerate(satirlar + [""], 1):
        if s.strip():
            if not simdiki:
                bas = n
            simdiki.append(s)
        elif simdiki:
            if any(x.strip() and not x.strip().startswith("//") for x in simdiki):
                bloklar.append(("\n".join(simdiki), bas))
            simdiki = []
    return bloklar


def _ceviri_hatasi(tur, msg, blok, satir, konum):
    kayma = blok[:konum].count("\n") if konum is not None else 0
    satirlar = blok.split("\n")
    return {"type": tur, "msg": msg, "line": satir + kayma, "frames": [], "where": "kod",
            "text": satirlar[kayma] if kayma < len(satirlar) else ""}


def _ceviri_kos(db, kod, dil):
    """Her sorguyu çevirip çalıştır → (tablolar, ham satırlar, hata, üretilen SQL'ler)."""
    C = _cevirici(dil)
    C.fonksiyonlari_kaydet(db)
    tur = dil.upper() + "Hatası"
    tablolar, hamlar, sqller = [], [], []

    def sutun_bul(sql):
        return [d[0] for d in db.execute(sql).description]
    sutun_bul.satirlar = lambda sql: db.execute(sql).fetchall()     # çevirici veriye bakabilsin (chart, timechart)
    donustur = getattr(C, "satir_donustur", None)                  # SPL: _time okunur tarih, çok değerli alanlar

    for blok, satir in _sorgu_bloklari(kod):
        try:
            sql = C.cevir(blok, sutun_bul)
            cur = db.execute(sql)
        except C.Hata as e:
            return tablolar, hamlar, _ceviri_hatasi(tur, e.msg, blok, satir, e.konum), sqller
        except sqlite3.Error as e:
            return tablolar, hamlar, dict(_sql_hatasi(e, satir, blok), type=tur), sqller
        sqller.append((satir, sql))
        cols = [d[0] for d in cur.description]
        tut = [n for n, c in enumerate(cols) if c != "__sira"]
        satirlar = cur.fetchmany(SQL_SATIR_LIMIT + 1)
        kesildi = len(satirlar) > SQL_SATIR_LIMIT
        satirlar = [tuple(r[n] for n in tut) for r in satirlar[:SQL_SATIR_LIMIT]]
        goster = satirlar
        if donustur:
            satirlar, goster = donustur([cols[n] for n in tut], satirlar)
        hamlar.append(satirlar)
        tablolar.append({"satir": satir, "sutunlar": [cols[n] for n in tut], "kesildi": kesildi,
                         "satirlar": [[None if v is None else _sql_deger(v) for v in r] for r in goster]})
    return tablolar, hamlar, None, sqller


def _ceviri_metin(tablolar):
    """KQL ve SPL'de boş değer boş görünür; çok değerli alanın değerleri virgülle ayrılır."""
    return "".join("|".join("" if v is None else v.replace("\x1f", ",") for v in r) + "\n"
                   for t in tablolar if "sutunlar" in t for r in t["satirlar"])


def do_ceviri_run(job, dil):
    db, err = _sql_hazirla(job)
    if err:
        return {"status": "error", "error": err, "segs": [], "tablolar": []}
    tablolar, _, err, _ = _ceviri_kos(db, job["code"], dil)
    cikti = _ceviri_metin(tablolar)
    return {"status": "error" if err else "ok", "segs": [["out", cikti]] if cikti else [],
            "tablolar": tablolar, "kql": True, "error": err}


class CeviriTester(SqlTester):
    def __init__(self, job, db, hamlar, cikti, dil):
        super().__init__(job, db, hamlar, cikti)
        self.dil = dil

    def dene(self, hazirlik=""):
        db = _sql_baglan(self.job, hazirlik)
        _, hamlar, err, _ = _ceviri_kos(db, self.code, self.dil)
        if err:
            raise UserRunError(err, hazirlik)
        return hamlar[-1] if hamlar else []

    def kullanir(self, kelime):
        temiz = re.sub(r"//[^\n]*|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'", " ", self.code)
        desen = r"(?<![\w-])" + r"\s+".join(map(re.escape, kelime.split())) + r"(?![\w-])"
        return re.search(desen, temiz, re.I if self.dil == "spl" else 0) is not None


def do_ceviri_test(job, dil):
    db, err = _sql_hazirla(job)
    if err:
        return {"status": "error", "error": err, "checks": [], "segs": []}
    tablolar, hamlar, err, _ = _ceviri_kos(db, job["code"], dil)
    cikti = _ceviri_metin(tablolar)
    segs = [["out", cikti]] if cikti else []
    if err:
        return {"status": "error", "checks": [], "segs": segs, "error": err}
    tester = CeviriTester(job, db, hamlar, cikti, dil)
    tns = tester.namespace()
    son = tablolar[-1] if tablolar else None
    tns.update(src=job.get("code", ""), sonuc=hamlar[-1] if hamlar else [], sonuclar=hamlar,
               sutunlar=son["sutunlar"] if son else [], sorgu=tester.sorgu, dene=tester.dene,
               kullanir=tester.kullanir)
    return _test_kos(tester, tns, job, segs)


def do_ceviri_dis(job, dil):
    db, err = _sql_hazirla(job)
    if err:
        return {"status": "error", "error": err, "text": ""}
    _, _, err, sqller = _ceviri_kos(db, job["code"], dil)
    if err:
        return {"status": "error", "error": err, "text": ""}
    metin = "\n\n".join(f"-- satır {satir}\n{sql};" for satir, sql in sqller)
    return {"status": "ok", "text": metin or "(çevrilecek sorgu yok)"}


def _detection_module(name):
    import importlib
    folder = os.path.dirname(os.path.abspath(__file__))
    if folder not in sys.path:
        sys.path.insert(0, folder)
    return importlib.import_module(name + "_engine")


def _detection_error(exc, name):
    mark = getattr(exc, "problem_mark", None)
    line = mark.line + 1 if mark is not None else None
    if line is None:
        match = re.search(r"line (\d+)", str(exc), re.I)
        line = int(match.group(1)) if match else None
    return {"type": name.upper() + "Hatası", "msg": str(exc), "line": line,
            "frames": [], "where": "kod"}


def do_detection_run(job, name):
    try:
        module = _detection_module(name)
        if name == "sigma":
            return module.SigmaProgram(job["code"]).run(module.parse_events(job.get("stdin", "")))
        rules = module.compile_rules(job["code"])
        return module.format_result(rules, module.decode_data(job.get("stdin", "")))
    except Exception as exc:
        return {"status": "error", "error": _detection_error(exc, name), "segs": []}


def do_detection_test(job, name):
    run_setup(job)
    code, stdin = job["code"], job.get("stdin", "")
    try:
        module = _detection_module(name)
        if name == "sigma":
            program = module.SigmaProgram(code)
            helpers = {"eslesir": program.matches, "eslesenler": program.matching_events,
                       "kural_adlari": program.names,
                       "kurallar": [item.rule.to_dict() for item in program.rules]}
        else:
            rules = module.compile_rules(code)
            def names(data):
                return [match.rule for match in module.match_rules(rules, data)]
            helpers = {"eslesenler": names,
                       "eslesir": lambda data, rule_name=None: any(rule_name is None or n == rule_name for n in names(data)),
                       "derle": module.compile_rules}
    except Exception as exc:
        return {"status": "error", "error": _detection_error(exc, name), "checks": [], "segs": []}
    tester = Tester("", {}, Capture(), stdin, job)
    namespace = tester.namespace()
    namespace.update(src=code, **helpers)
    return _test_kos(tester, namespace, job, [])


def do_packet_run(job):
    try:
        return _detection_module("packet").run(job["code"], job.get("stdin", ""))
    except Exception as exc:
        return {"status": "error", "error": _detection_error(exc, "paket"), "segs": []}


def do_packet_test(job):
    run_setup(job)
    try:
        helpers = _detection_module("packet").test_helpers(job["code"], job.get("stdin", ""))
    except Exception as exc:
        return {"status": "error", "error": _detection_error(exc, "paket"), "checks": [], "segs": []}
    tester = Tester("", {}, Capture(), job.get("stdin", ""), job)
    namespace = tester.namespace()
    namespace.update(helpers)
    return _test_kos(tester, namespace, job, [])


def do_elastic_run(job):
    try:
        return _detection_module("elastic").run(job["code"], job.get("stdin", ""))
    except Exception as exc:
        return {"status": "error", "error": _detection_error(exc, "elastic"), "segs": []}


def do_elastic_test(job):
    run_setup(job)
    try:
        helpers = _detection_module("elastic").test_helpers(job["code"], job.get("stdin", ""))
    except Exception as exc:
        return {"status": "error", "error": _detection_error(exc, "elastic"), "checks": [], "segs": []}
    tester = Tester("", {}, Capture(), job.get("stdin", ""), job)
    namespace = tester.namespace()
    namespace.update(helpers)
    return _test_kos(tester, namespace, job, [])


def do_ad_run(job):
    try:
        return _detection_module("ad").run(job["code"], job.get("stdin", ""))
    except Exception as exc:
        line = getattr(exc, "line", None)
        return {"status": "error", "error": {"type": "ADHatası", "msg": str(exc), "line": line, "frames": [], "where": "kod"}, "segs": [], "tablolar": []}


def do_ad_test(job):
    run_setup(job)
    try:
        mod = _detection_module("ad")
        res = mod.run(job["code"], job.get("stdin", ""))
        if res.get("status") == "error":
            return {"status": "error", "error": res["error"], "checks": [], "segs": res.get("segs", [])}
        helpers = mod.test_helpers(job["code"])
    except Exception as exc:
        line = getattr(exc, "line", None)
        return {"status": "error", "error": {"type": "ADHatası", "msg": str(exc), "line": line, "frames": [], "where": "kod"}, "checks": [], "segs": []}
    tester = Tester("", {}, Capture(), job.get("stdin", ""), job)
    namespace = tester.namespace()
    namespace.update(helpers)
    return _test_kos(tester, namespace, job, res.get("segs", []))


def do_ad_dis(job):
    try:
        return _detection_module("ad").explain_ldap(job["code"])
    except Exception as exc:
        line = getattr(exc, "line", None)
        return {"status": "error", "error": {"type": "ADHatası", "msg": str(exc), "line": line, "frames": [], "where": "kod"}, "text": ""}


# ── PostgreSQL (SQL yolu, adım meta'sında motor: postgres): WSL'deki gerçek küme ──
# Her iş kendi veritabanını (pafta_lab) ve yönetici rolünü (pafta_yonetici: CREATEROLE,
# süper kullanıcı değil) kurar; kullanıcının betiği ve görevin hazırlığı bu rolle çalışır.
# Dersin oluşturduğu roller pafta_yonetici'nin yönettiği rollerdir; iş bitince (ya da
# önceki iş yarıda kaldıysa sonraki iş başlarken) hepsi silinir. Roller kümede ortak
# olduğu için işler danışma kilidiyle sıraya girer.

PG_DB = "pafta_lab"
PG_YONETICI = "pafta_yonetici"
PG_KILIT = 7_342_001


def _pg_temizle(admin):
    cur = admin.cursor()
    cur.execute("SELECT pid FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid()", (PG_DB,))
    for (pid,) in cur.fetchall():
        cur.execute("SELECT pg_terminate_backend(%s)", (pid,))
    cur.execute(f"DROP DATABASE IF EXISTS {PG_DB} WITH (FORCE)")
    cur.execute("""SELECT r.rolname FROM pg_auth_members m
                   JOIN pg_roles r ON r.oid = m.roleid
                   JOIN pg_roles y ON y.oid = m.member
                   WHERE y.rolname = %s AND m.admin_option AND r.rolname <> %s""", (PG_YONETICI, PG_YONETICI))
    for (rol,) in cur.fetchall():
        cur.execute("DROP OWNED BY " + _pg_ad(rol))      # başka veritabanlarındaki izinler
        cur.execute("DROP ROLE IF EXISTS " + _pg_ad(rol))
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (PG_YONETICI,))
    if cur.fetchone():
        cur.execute(f"DROP OWNED BY {PG_YONETICI}")
        cur.execute(f"DROP ROLE {PG_YONETICI}")


def _pg_ad(ad):
    return '"' + ad.replace('"', '""') + '"'


class _PgLab:
    """Bir işin PostgreSQL ortamı: süper kullanıcı (admin) ve yönetici bağlantıları."""

    def __init__(self, job):
        import psycopg2
        import secrets
        self.pg = psycopg2
        self.job = job
        self.kontrol = psycopg2.connect(dbname="postgres")
        self.kontrol.autocommit = True
        self.kontrol.cursor().execute("SELECT pg_advisory_lock(%s)", (PG_KILIT,))
        self.yonetici = self.admin = None
        self.parola = secrets.token_hex(16)
        try:
            self.kur()
        except Exception:
            self.kapat()
            raise

    def kur(self, ek=""):
        cur = self.kontrol.cursor()
        _pg_temizle(self.kontrol)
        cur.execute(f"CREATE ROLE {PG_YONETICI} LOGIN CREATEROLE PASSWORD %s", (self.parola,))
        cur.execute(f"CREATE DATABASE {PG_DB} OWNER {PG_YONETICI}")
        self.yonetici = self.pg.connect(dbname=PG_DB, user=PG_YONETICI, password=self.parola, host="127.0.0.1")
        self.yonetici.autocommit = True
        self.admin = self.pg.connect(dbname=PG_DB)          # testlerin kataloğu ve SET ROLE denemeleri için
        self.admin.autocommit = True
        for parca in (self.job.get("setup"), ek):
            if parca:
                self.yonetici.cursor().execute(parca)

    def kapat(self):
        for c in (self.yonetici, self.admin):
            if c is not None:
                try:
                    c.close()
                except Exception:
                    pass
        try:
            _pg_temizle(self.kontrol)
            self.kontrol.cursor().execute("SELECT pg_advisory_unlock(%s)", (PG_KILIT,))
        finally:
            self.kontrol.close()


def _pg_hatasi(e, satir=None, ifade=""):
    kod = getattr(e, "pgcode", None) or ""
    ham = (getattr(e, "pgerror", None) or str(e)).strip()
    ilk = ham.splitlines()[0] if ham else str(e)
    ilk = re.sub(r"^ERROR:\s*", "", ilk)
    tr = {"42501": "yetki yok", "42P01": "böyle bir tablo yok", "42703": "böyle bir sütun yok",
          "42601": "sözdizimi hatası", "42704": "böyle bir nesne yok", "42710": "nesne zaten var",
          "2BP01": "nesneye bağlı başka nesneler var", "0LP01": "geçersiz yetki verme"}.get(kod)
    msg = (tr + "  ·  " if tr else "") + f"({kod}) {ilk}" if kod else ilk
    return {"type": "SQLHatası", "msg": msg, "line": satir, "frames": [], "where": "kod",
            "text": (ifade.split("\n") or [""])[0], "pgcode": kod}


def _pg_deger(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return "t" if v else "f"                  # psql'in yazdığı gibi
    if isinstance(v, (bytes, memoryview)):
        return "\\x" + bytes(v).hex()
    if isinstance(v, (list, tuple)):
        return "{" + ",".join("NULL" if x is None else str(x) for x in v) + "}"
    return str(v)


def _pg_kos(baglanti, kod):
    tablolar, hamlar = [], []
    cur = baglanti.cursor()
    for ifade, satir in _sql_parcala(kod):
        try:
            cur.execute(ifade)
        except baglanti_hatasi() as e:
            return tablolar, hamlar, _pg_hatasi(e, satir, ifade)
        if cur.description:
            sutunlar = [d[0] for d in cur.description]
            satirlar = cur.fetchmany(SQL_SATIR_LIMIT + 1)
            kesildi = len(satirlar) > SQL_SATIR_LIMIT
            satirlar = [tuple(r) for r in satirlar[:SQL_SATIR_LIMIT]]
            hamlar.append(satirlar)
            tablolar.append({"satir": satir, "sutunlar": sutunlar, "kesildi": kesildi,
                             "satirlar": [[_pg_deger(v) for v in r] for r in satirlar]})
        else:
            komut = cur.statusmessage.split()[0] if cur.statusmessage else ifade.split(None, 1)[0].upper()
            if komut in ("INSERT", "UPDATE", "DELETE", "MERGE"):
                tablolar.append({"satir": satir, "komut": komut, "degisen": cur.rowcount})
            else:
                tablolar.append({"satir": satir, "komut": cur.statusmessage or komut})
    return tablolar, hamlar, None


def baglanti_hatasi():
    import psycopg2
    return psycopg2.Error


def _pg_ac(job):
    try:
        return _PgLab(job), None
    except ImportError:
        return None, {"type": "PostgreSQLYok", "msg": "WSL'de psycopg2 yok (Kali: sudo apt install python3-psycopg2).",
                      "line": None, "frames": [], "where": "test"}
    except baglanti_hatasi() as e:
        if not getattr(e, "pgcode", None) and "connect" in str(e).lower():
            # Küme kapalı: Windows tarafı (PostgresRunner) kümeyi başlatıp bir kez yeniden dener
            return None, {"type": "PostgreSQLKapalı", "msg": "PostgreSQL kümesine bağlanılamadı: " + str(e).strip()[:300],
                          "line": None, "frames": [], "where": "test"}
        hata = _pg_hatasi(e)
        hata.update(where="test", msg="Görevin PostgreSQL hazırlığı kurulamadı: " + hata["msg"])
        return None, hata


def do_pg_run(job):
    lab, err = _pg_ac(job)
    if err:
        return {"status": "error", "error": err, "segs": [], "tablolar": []}
    try:
        tablolar, _, err = _pg_kos(lab.yonetici, job["code"])
    finally:
        lab.kapat()
    cikti = _sql_metin(tablolar)
    return {"status": "error" if err else "ok", "segs": [["out", cikti]] if cikti else [],
            "tablolar": tablolar, "error": err}


class PgTester(Tester):
    def __init__(self, job, lab, hamlar, cikti):
        super().__init__("", {}, Capture(), "", job)
        self.cap.add("out", cikti)
        self.code = job.get("code", "")
        self.lab = lab

    def sorgu(self, sql, *params):
        """Kullanıcının betiğinden SONRAKİ veritabanında, süper kullanıcı olarak (katalog her şeyi görür)."""
        cur = self.lab.admin.cursor()
        cur.execute(sql, params or None)
        return [tuple(r) for r in cur.fetchall()] if cur.description else []

    def rol_olarak(self, rol, sql, *params):
        """`rol` olarak çalıştır → ('ok', satırlar) ya da ('hata', SQLSTATE). Değişiklik geri alınır."""
        c = self.lab.admin
        c.autocommit = False
        cur = c.cursor()
        try:
            cur.execute("SET LOCAL ROLE " + _pg_ad(rol))
            cur.execute(sql, params or None)
            return ("ok", [tuple(r) for r in cur.fetchall()] if cur.description else [])
        except baglanti_hatasi() as e:
            return ("hata", e.pgcode)
        finally:
            c.rollback()
            c.autocommit = True

    def yapabilir(self, rol, sql, *params):
        """`rol` bu ifadeyi çalıştırabiliyor mu? Yalnızca yetki hatası (42501) False'tur; başka hata testi bozar."""
        durum, deger = self.rol_olarak(rol, sql, *params)
        if durum == "ok":
            return True
        if deger == "42501":
            return False
        raise AssertionError(f"{rol} için beklenmeyen hata ({deger}): {sql}")

    def dene(self, hazirlik=""):
        """Temiz bir veritabanına hazırlığı ve `hazirlik`ı kurup betiği yeniden çalıştır → son sorgunun satırları."""
        for c in (self.lab.yonetici, self.lab.admin):
            c.close()
        self.lab.kur(hazirlik)
        _, hamlar, err = _pg_kos(self.lab.yonetici, self.code)
        if err:
            raise UserRunError(err, hazirlik)
        return hamlar[-1] if hamlar else []

    def kullanir(self, kelime):
        temiz = re.sub(r"--[^\n]*|/\*.*?\*/|'(?:[^']|'')*'", " ", self.code, flags=re.S)
        desen = r"\b" + r"\s+".join(map(re.escape, kelime.split())) + r"\b"
        return re.search(desen, temiz, re.I) is not None


def do_pg_test(job):
    lab, err = _pg_ac(job)
    if err:
        return {"status": "error", "error": err, "checks": [], "segs": []}
    try:
        tablolar, hamlar, err = _pg_kos(lab.yonetici, job["code"])
        cikti = _sql_metin(tablolar)
        segs = [["out", cikti]] if cikti else []
        if err:
            return {"status": "error", "checks": [], "segs": segs, "error": err}
        tester = PgTester(job, lab, hamlar, cikti)
        tns = tester.namespace()
        son = next((t for t in reversed(tablolar) if "sutunlar" in t), None)
        tns.update(src=job.get("code", ""), sonuc=hamlar[-1] if hamlar else [], sonuclar=hamlar,
                   sutunlar=son["sutunlar"] if son else [], sorgu=tester.sorgu, dene=tester.dene,
                   kullanir=tester.kullanir, rol_olarak=tester.rol_olarak, yapabilir=tester.yapabilir)
        return _test_kos(tester, tns, job, segs)
    finally:
        lab.kapat()


# ── MariaDB (SQL yolu, adım meta'sında motor: mariadb): WSL'deki gerçek sunucu ──
# Her iş adı pafta_lab_ ile başlayan kendi veritabanını kurar ve iş bitince siler; WSL
# kullanıcısının hesabı yalnız pafta_% veritabanlarında yetkilidir (sandbox/mariadb_lab.py).

MY_SOKET = "/run/mysqld/mysqld.sock"


def _my_deger(v):
    if v is None:
        return None
    if isinstance(v, float):
        return repr(v)[:-2] if repr(v).endswith(".0") else repr(v)   # mariadb istemcisi gibi: 8.0 → 8
    if isinstance(v, (bytes, bytearray)):
        try:
            return bytes(v).decode("utf-8")
        except UnicodeDecodeError:
            return "0x" + bytes(v).hex().upper()
    return str(v)


def _my_hatasi(e, satir=None, ifade=""):
    kod = e.args[0] if e.args and isinstance(e.args[0], int) else None
    ileti = e.args[1] if len(e.args) > 1 else str(e)
    return {"type": "SQLHatası", "msg": f"({kod}) {ileti}" if kod else ileti, "line": satir, "frames": [],
            "where": "kod", "text": (ifade.split("\n") or [""])[0], "mycode": kod}


class _MyLab:
    def __init__(self, job):
        import pymysql
        import secrets
        self.my = pymysql
        self.job = job
        self.ad = "pafta_lab_" + secrets.token_hex(6)
        self.uyarilar = []
        self.baglanti = None
        try:
            self.kur()
        except Exception:
            if self.baglanti is not None:
                self.kapat()
            raise

    def kur(self, ek=""):
        if self.baglanti is not None:
            self.kapat()
        import getpass
        self.baglanti = self.my.connect(unix_socket=MY_SOKET, user=getpass.getuser(), autocommit=True, charset="utf8mb4")
        cur = self.baglanti.cursor()
        cur.execute(f"CREATE DATABASE `{self.ad}` CHARACTER SET utf8mb4")
        cur.execute(f"USE `{self.ad}`")
        for parca in (self.job.get("setup"), ek):
            for ifade, _ in _sql_parcala(parca or ""):
                cur.execute(ifade)

    def kapat(self):
        try:
            self.baglanti.cursor().execute(f"DROP DATABASE IF EXISTS `{self.ad}`")
        finally:
            self.baglanti.close()
            self.baglanti = None


def _my_kos(lab, kod):
    tablolar, hamlar = [], []
    cur = lab.baglanti.cursor()
    for ifade, satir in _sql_parcala(kod):
        try:
            cur.execute(ifade)
        except lab.my.Error as e:
            return tablolar, hamlar, _my_hatasi(e, satir, ifade)
        sonuc = cur.fetchall() if cur.description else None
        uyari = cur.connection.cursor()
        uyari.execute("SHOW WARNINGS")
        for seviye, no, ileti in uyari.fetchall():
            lab.uyarilar.append((satir, seviye, no, ileti))
        if sonuc is not None:
            sutunlar = [d[0] for d in cur.description]
            satirlar = [tuple(r) for r in sonuc[:SQL_SATIR_LIMIT]]
            hamlar.append(satirlar)
            tablolar.append({"satir": satir, "sutunlar": sutunlar, "kesildi": len(sonuc) > SQL_SATIR_LIMIT,
                             "satirlar": [[_my_deger(v) for v in r] for r in satirlar]})
        else:
            komut = ifade.split(None, 1)[0].upper()
            if komut in ("INSERT", "UPDATE", "DELETE", "REPLACE"):
                tablolar.append({"satir": satir, "komut": komut, "degisen": cur.rowcount})
            else:
                tablolar.append({"satir": satir, "komut": komut})
    return tablolar, hamlar, None


def _my_ac(job):
    try:
        return _MyLab(job), None
    except ImportError:
        return None, {"type": "MariaDBYok", "msg": "WSL'de pymysql yok (Kali: sudo apt install python3-pymysql).",
                      "line": None, "frames": [], "where": "test"}
    except Exception as e:
        if isinstance(e, OSError) or "2002" in str(e) or "Can't connect" in str(e):
            return None, {"type": "MariaDBKapalı", "msg": "MariaDB'ye bağlanılamadı: " + str(e)[:300],
                          "line": None, "frames": [], "where": "test"}
        hata = _my_hatasi(e)
        hata.update(where="test", msg="Görevin MariaDB hazırlığı kurulamadı: " + hata["msg"])
        return None, hata


def do_my_run(job):
    lab, err = _my_ac(job)
    if err:
        return {"status": "error", "error": err, "segs": [], "tablolar": []}
    try:
        tablolar, _, err = _my_kos(lab, job["code"])
    finally:
        lab.kapat()
    cikti = _sql_metin(tablolar)
    return {"status": "error" if err else "ok", "segs": [["out", cikti]] if cikti else [],
            "tablolar": tablolar, "error": err}


class MyTester(Tester):
    def __init__(self, job, lab, cikti):
        super().__init__("", {}, Capture(), "", job)
        self.cap.add("out", cikti)
        self.code = job.get("code", "")
        self.lab = lab

    def sorgu(self, sql, *params):
        """Kullanıcının betiğinden SONRAKİ veritabanında bir sorgu."""
        cur = self.lab.baglanti.cursor()
        cur.execute(sql, params or None)
        return [tuple(r) for r in cur.fetchall()] if cur.description else []

    def dene(self, hazirlik=""):
        """Temiz bir veritabanına hazırlığı ve `hazirlik`ı kurup betiği yeniden çalıştır → son sorgunun satırları."""
        self.lab.uyarilar.clear()
        self.lab.kur(hazirlik)
        _, hamlar, err = _my_kos(self.lab, self.code)
        if err:
            raise UserRunError(err, hazirlik)
        return hamlar[-1] if hamlar else []

    def kullanir(self, kelime):
        temiz = re.sub(r"--[^\n]*|#[^\n]*|/\*.*?\*/|'(?:[^'\]|\.|'')*'", " ", self.code, flags=re.S)
        desen = r"\b" + r"\s+".join(map(re.escape, kelime.split())) + r"\b"
        return re.search(desen, temiz, re.I) is not None


def do_my_test(job):
    lab, err = _my_ac(job)
    if err:
        return {"status": "error", "error": err, "checks": [], "segs": []}
    try:
        tablolar, hamlar, err = _my_kos(lab, job["code"])
        cikti = _sql_metin(tablolar)
        segs = [["out", cikti]] if cikti else []
        if err:
            return {"status": "error", "checks": [], "segs": segs, "error": err}
        tester = MyTester(job, lab, cikti)
        tns = tester.namespace()
        son = next((t for t in reversed(tablolar) if "sutunlar" in t), None)
        tns.update(src=job.get("code", ""), sonuc=hamlar[-1] if hamlar else [], sonuclar=hamlar,
                   sutunlar=son["sutunlar"] if son else [], sorgu=tester.sorgu, dene=tester.dene,
                   kullanir=tester.kullanir, uyarilar=lab.uyarilar)
        return _test_kos(tester, tns, job, segs)
    finally:
        lab.kapat()


# ── Gerçek Splunk (SPL yolu, adım meta'sında motor: splunk): Docker'daki Splunk Enterprise ──
# Görevin hazırlığı Python'dur: props(sourcetype, {ayar: değer}), veri(metin, sourcetype[, kaynak]) ve
# alarm girdisinde çalıştırma anları: calistir("2026-10-19 09:30", ...[, ara=saniye]) ya da
# aralik(baş, son) (anlar kuralın cron_schedule'ından hesaplanır). girdi: props ise kullanıcının
# props.conf'u verinin dizine alınmasından ÖNCE uygulanır; arama ve alarmda veri hazırlıktan hemen
# sonra alınır (sandbox/splunk_lab.py).

def _splunk_lab():
    import importlib.util
    yol = os.path.join(os.path.dirname(os.path.abspath(__file__)), "splunk_lab.py")
    spec = importlib.util.spec_from_file_location("pafta_splunk_lab", yol)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def _spk_hata(msg, where="kod", tur="SplunkHatası", line=None):
    return {"type": tur, "msg": msg, "line": line, "frames": [], "where": where}


def _conf_coz(metin, dosya):
    """props.conf biçimli metin → [(kıta, {anahtar: değer}, satır)]. Değerler olduğu gibi kalır."""
    kitalar, simdiki = [], None
    satirlar = (metin or "").replace("\r\n", "\n").split("\n")
    n = 0
    while n < len(satirlar):
        s = satirlar[n].strip()
        n += 1
        if not s or s.startswith("#"):
            continue
        m = re.fullmatch(r"\[([^\]]+)\]", s)
        if m:
            simdiki = (m.group(1).strip(), {}, n)
            kitalar.append(simdiki)
            continue
        if "=" not in s:
            raise UserRunError(_spk_hata(f"{dosya}: 'ANAHTAR = değer' ya da [kıta] bekleniyordu: {s[:60]}", line=n), "")
        if simdiki is None:
            raise UserRunError(_spk_hata(f"{dosya}: ayarlar bir [kıta] başlığının altında olmalı", line=n), "")
        anahtar, deger = s.split("=", 1)
        simdiki[1][anahtar.strip()] = deger.strip()
    return kitalar


def _spk_deger(v):
    if isinstance(v, list):
        return tuple(_spk_deger(x) for x in v)
    if isinstance(v, str) and re.fullmatch(r"-?\d{1,17}", v):
        return int(v)
    if isinstance(v, str) and re.fullmatch(r"-?\d+\.\d+", v):
        return float(v)
    return v


def _cron_alan(alan, en_az, en_cok, ad):
    degerler = set()
    for parca in alan.split(","):
        adim = 1
        if "/" in parca:
            parca, adim_metni = parca.split("/", 1)
            if not adim_metni.isdigit() or int(adim_metni) == 0:
                raise ValueError(f"{ad} alanında geçersiz adım: /{adim_metni}")
            adim = int(adim_metni)
        if parca == "*":
            bas, son = en_az, en_cok
        elif "-" in parca:
            a, b = parca.split("-", 1)
            if not (a.isdigit() and b.isdigit()):
                raise ValueError(f"{ad} alanında geçersiz aralık: {parca}")
            bas, son = int(a), int(b)
        elif parca.isdigit():
            bas = son = int(parca)
            if "/" in alan:
                son = en_cok
        else:
            raise ValueError(f"{ad} alanında anlaşılmayan değer: {parca}")
        if not (en_az <= bas <= son <= en_cok):
            raise ValueError(f"{ad} alanı {en_az}-{en_cok} dışında: {parca}")
        degerler.update(range(bas, son + 1, adim))
    return degerler


def _cron_anlari(cron, bas, son):
    """cron_schedule'ın [bas, son] (epoch, ikisi de dahil) aralığındaki anları. Laboratuvar dakika ve saat
    alanlarını yorumlar; gün, ay ve haftanın günü * olmalıdır."""
    alanlar = cron.split()
    if len(alanlar) != 5:
        raise ValueError(f"cron_schedule beş alan ister (dakika saat gün ay haftanın-günü): {cron!r}")
    if alanlar[2:] != ["*", "*", "*"]:
        raise ValueError("bu laboratuvar cron_schedule'ın yalnız dakika ve saat alanlarını yorumlar; "
                         "gün, ay ve haftanın günü * olmalı")
    dakikalar = _cron_alan(alanlar[0], 0, 59, "dakika")
    saatler = _cron_alan(alanlar[1], 0, 23, "saat")
    an = bas - bas % 60
    if an < bas:
        an += 60
    anlar = []
    while an <= son:
        t = time.gmtime(an)
        if t.tm_min in dakikalar and t.tm_hour in saatler:
            anlar.append(an)
        an += 60
    return anlar


def _an(metin):
    import calendar
    try:
        return calendar.timegm(time.strptime(metin, "%Y-%m-%d %H:%M"))
    except ValueError:
        raise ValueError(f"an 'YYYY-AA-GG SS:DD' biçiminde olmalı: {metin!r}")


def _an_yaz(deger, kayma=0):
    """epoch ya da Splunk'ın ISO zamanı → 'YYYY-AA-GG SS:DD', laboratuvarın kaydırması geri alınmış."""
    if not isinstance(deger, (int, float)):
        import calendar
        if not deger:
            return ""
        deger = calendar.timegm(time.strptime(deger[:19], "%Y-%m-%dT%H:%M:%S"))
    return time.strftime("%Y-%m-%d %H:%M", time.gmtime(deger - kayma))


def _gun_kaydir(metin, kayma):
    """Satır başındaki YYYY-AA-GG tarihlerini `kayma` saniye (tam gün) ileri al."""
    def kaydir(m):
        import calendar
        return time.strftime("%Y-%m-%d", time.gmtime(calendar.timegm(time.strptime(m.group(1), "%Y-%m-%d")) + kayma))
    return re.sub(r"(?m)^(\d{4}-\d{2}-\d{2})(?= )", kaydir, metin)


OLAY_ARAMASI = ('search index={dizin} | sort 0 _time | eval zaman=strftime(_time, "%Y-%m-%d %H:%M:%S.%3N") '
                '| table zaman sourcetype _raw')


class _SplunkIs:
    """Bir işin adımları: hazırlığı kur, (props ise) kullanıcının ayarını uygula, veriyi al, ara."""

    def __init__(self, job, lab, S):
        self.job, self.lab, self.S = job, lab, S
        self.girdi = job.get("girdi", "arama")
        self.bekleyen = []
        self.takvim = None
        self.kayma = 0
        self.gosterim = None

    def _hazirlik(self, ek=""):
        def calistir(*anlar, ara=0):
            self.takvim = ("anlar", [_an(a) for a in anlar], ara)

        def aralik(bas, son):
            self.takvim = ("aralik", [_an(bas), _an(son)], 0)

        ns = {"__name__": "__setup__", "props": self.lab.props, "DIZIN": self.S.DIZIN,
              "veri": lambda metin, sourcetype, kaynak="ders.log": self.bekleyen.append((metin, sourcetype, kaynak)),
              "calistir": calistir, "aralik": aralik, "olay_turu": self.lab.olay_turu, "etiket": self.lab.etiket,
              "goster": lambda arama: setattr(self, "gosterim", arama),
              "kural": lambda yaml: setattr(self, "kural_yaml", yaml),
              "dosya": lambda ad, metin: self.__dict__.setdefault("dosyalar", {}).__setitem__(ad, metin)}
        for kod in (self.job.get("setup") or "", ek or ""):
            if kod.strip():
                exec(compile(kod, "<setup>", "exec"), ns)

    def _props_uygula(self, kod):
        kitalar = _conf_coz(kod, "props.conf")
        if not kitalar:
            raise UserRunError(_spk_hata("props.conf boş: en az bir [sourcetype] kıtası yaz"), "")
        for ad, ayarlar, satir in kitalar:
            if not ad.startswith(self.S.ONEK):
                raise UserRunError(_spk_hata(f"kıta adı görevin sourcetype'ı olmalı ({self.S.ONEK} ile başlar): [{ad}]",
                                             line=satir), "")
            self.lab.props(ad, ayarlar)

    def _bilgi_uygula(self, kod):
        """girdi: bilgi → '# props.conf', '# eventtypes.conf', '# tags.conf' başlıklı bölümler. props kıtaları
        hazırlığın kurduğu kıtaya eklenir (arama zamanı ayarları); olay türleri ve etiketler kurulur."""
        parcalar = re.split(r"(?m)^#+[ \t]*(props|eventtypes|tags)\.conf[ \t]*$", kod or "")
        once = parcalar[0]
        if any(s.strip() and not s.strip().startswith("#") for s in once.splitlines()):
            raise UserRunError(_spk_hata("bölümler '# props.conf', '# eventtypes.conf' ya da '# tags.conf' "
                                         "başlığıyla başlamalı", line=1), "")
        satir = once.count("\n") + 1
        kuruldu = False
        for dosya, metin in zip(parcalar[1::2], parcalar[2::2]):
            for ad, ayarlar, n in _conf_coz(metin, dosya + ".conf"):
                yer = satir + n
                try:
                    if dosya == "props":
                        self.lab.props_ekle(ad, ayarlar)
                    elif dosya == "eventtypes":
                        if "search" not in ayarlar:
                            raise UserRunError(_spk_hata(f"eventtypes.conf [{ad}] kıtasında search yok", line=yer), "")
                        ayarlar = dict(ayarlar)
                        self.lab.olay_turu(ad, ayarlar.pop("search"), **ayarlar)
                    else:
                        self.lab.etiket(ad, ayarlar)
                except self.S.SplunkHatasi as e:
                    raise UserRunError(_spk_hata(f"{dosya}.conf [{ad}]: {e}", line=yer), "")
                kuruldu = True
            satir += 1 + metin.count("\n")
        if not kuruldu:
            raise UserRunError(_spk_hata("hiç kıta yazılmadı"), "")

    def _alarm_kos(self, kod):
        """Her kıtayı bir kayıtlı arama olarak kur, takvimdeki anlarda alarm eylemleriyle çalıştır →
        her çalıştırma bir satır: kural, calisma, pencere_bas, pencere_son, sonuc, tetiklenen, bastirilan, teslim."""
        kitalar = _conf_coz(kod, "savedsearches.conf")
        if not kitalar:
            raise UserRunError(_spk_hata("savedsearches.conf boş: en az bir [kural adı] kıtası yaz"), "")
        if self.takvim is None:
            raise UserRunError(_spk_hata("görevin hazırlığı çalıştırma anlarını vermedi (calistir ya da aralik)",
                                         "test"), "")
        kurallar = []
        for ad, ayarlar, satir in kitalar:
            if not ad.startswith(self.S.ONEK):
                raise UserRunError(_spk_hata(f"kural adı {self.S.ONEK} ile başlamalı: [{ad}]", line=satir), "")
            for gerekli in ("search", "cron_schedule"):
                if not ayarlar.get(gerekli):
                    raise UserRunError(_spk_hata(f"[{ad}] kıtasında {gerekli} yok", line=satir), "")
            tur, deger, ara = self.takvim
            deger = [a + self.kayma for a in deger]
            try:
                anlar = _cron_anlari(ayarlar["cron_schedule"], *deger) if tur == "aralik" else deger
            except ValueError as e:
                raise UserRunError(_spk_hata(f"[{ad}] {e}", line=satir), "")
            kurallar.append((ad, self.lab.kural(ad, {k: v for k, v in ayarlar.items() if k != "cron_schedule"}), anlar))
        satirlar = []
        for ad, ic_ad, anlar in kurallar:
            cikanlar = []
            previous_dispatch = None
            previous_duration = None
            for n, an in enumerate(anlar):
                previous_dispatch = self.S.dispatch_after(previous_dispatch, ara)
                try:
                    cikanlar.append((an,) + self.lab.calistir(ic_ad, an))
                    previous_duration = self.S.verify_dispatch_window(previous_dispatch, ara, previous_duration)
                except self.S.SplunkHatasi as e:
                    raise UserRunError(_spk_hata(f"[{ad}] {e}"), "")
            kayit = self.lab.zamanlayici(ic_ad, [c[1] for c in cikanlar])
            for an, sid, bas, son, alanlar, sonuclar in cikanlar:
                sayi, tetiklenen, bastirilan = kayit[sid]
                alanlar = [a for a in alanlar if not a.startswith("_")]
                teslim = ", ".join(":".join(str(r.get(a, "")) for a in alanlar) for r in sonuclar) if tetiklenen else ""
                satirlar.append((ad, _an_yaz(an, self.kayma), _an_yaz(bas, self.kayma), _an_yaz(son, self.kayma),
                                 sayi, tetiklenen, bastirilan, teslim))
        return ["kural", "calisma", "pencere_bas", "pencere_son", "sonuc", "tetiklenen", "bastirilan", "teslim"], satirlar

    def kos(self, kod, ek=""):
        """→ (alanlar, satırlar)"""
        self.bekleyen = []
        self.takvim = None
        self._hazirlik(ek)
        if self.girdi == "props":
            self._props_uygula(kod)
        elif self.girdi == "bilgi":
            self._bilgi_uygula(kod)
        elif self.girdi not in ("arama", "alarm"):
            raise UserRunError(_spk_hata(f"bu girdi desteklenmiyor: {self.girdi}"), "")
        self.kayma = 0
        if self.girdi == "alarm" and self.takvim:
            # Dersin geçmişteki sabahı tam gün kaydırılarak yarına taşınır: Splunk bastırma kaydını takvim
            # zamanı + süre geçince temizler; geçmiş bir zamanla kurulan kayıt hemen temizlenebilir ve
            # bastırma rastgele kaybolur. Veri, çalıştırma anları ve pencereler birlikte kayar; çıktı
            # dersin tarihleriyle gösterilir.
            ilk = min(self.takvim[1])
            yarin = (int(time.time()) // 86400 + 1) * 86400
            self.kayma = max(0, yarin - (ilk - ilk % 86400))
        for metin, sourcetype, kaynak in self.bekleyen:
            self.lab.yukle(_gun_kaydir(metin, self.kayma) if self.kayma else metin, sourcetype, kaynak)
        if self.girdi == "alarm":
            return self._alarm_kos(kod)
        if self.girdi == "bilgi":
            if not self.gosterim:
                raise UserRunError(_spk_hata("görevin hazırlığı gösterilecek aramayı vermedi (goster)", "test"), "")
            return self.ara(self.gosterim)
        return self.ara(OLAY_ARAMASI.format(dizin=self.S.DIZIN) if self.girdi == "props" else kod)

    def ara(self, spl):
        try:
            alanlar, satirlar = self.lab.ara(spl)
        except self.S.SplunkHatasi as e:
            raise UserRunError(_spk_hata(str(e)), "")
        alanlar = [a for a in alanlar if not a.startswith("_") or a in ("_time", "_raw")]
        return alanlar, [tuple(_spk_deger(r.get(a)) for a in alanlar) for r in satirlar]


def _spk_tablo(alanlar, satirlar):
    return {"satir": 1, "sutunlar": alanlar, "kesildi": False,
            "satirlar": [[None if v is None else "\x1f".join(map(str, v)) if isinstance(v, tuple) else str(v)
                          for v in r] for r in satirlar]}


def _spk_ac():
    try:
        S = _splunk_lab()
        return S, S.Lab(), None
    except Exception as e:
        return None, None, _spk_hata(f"Splunk laboratuvarı açılamadı: {e}", "test", "SplunkYok")


def do_spk_run(job):
    S, lab, err = _spk_ac()
    if err:
        return {"status": "error", "error": err, "segs": [], "tablolar": []}
    try:
        with lab:
            alanlar, satirlar = _SplunkIs(job, lab, S).kos(job["code"])
    except UserRunError as e:
        return {"status": "error", "error": e.info, "segs": [], "tablolar": []}
    except S.SplunkHatasi as e:
        return {"status": "error", "error": _spk_hata(str(e), "test", "SplunkYok"), "segs": [], "tablolar": []}
    tablo = _spk_tablo(alanlar, satirlar)
    cikti = _ceviri_metin([tablo])
    return {"status": "ok", "segs": [["out", cikti]] if cikti else [], "tablolar": [tablo], "kql": True, "error": None}


class SplunkTester(Tester):
    def __init__(self, job, is_, cikti):
        super().__init__("", {}, Capture(), "", job)
        self.cap.add("out", cikti)
        self.code = job.get("code", "")
        self.is_ = is_

    def dene(self, hazirlik=""):
        """Laboratuvarı boşaltıp hazırlığı + `hazirlik`ı (Python) yeniden kur, kodu yeniden uygula → satırlar."""
        self.is_.lab.bosalt()
        try:
            return self.is_.kos(self.code, hazirlik)[1]
        except UserRunError as e:
            raise UserRunError(e.info, hazirlik)

    def ara(self, spl):
        """Laboratuvarın şu anki hâlinde bir arama → satırlar."""
        return self.is_.ara(spl)[1]

    def kullanir(self, kelime):
        temiz = re.sub(r"#[^\n]*|\"(?:\\.|[^\"\\])*\"", " ", self.code)
        desen = r"(?<![\w-])" + r"\s+".join(map(re.escape, kelime.split())) + r"(?![\w-])"
        return re.search(desen, temiz, re.I) is not None


def do_spk_test(job):
    S, lab, err = _spk_ac()
    if err:
        return {"status": "error", "error": err, "checks": [], "segs": []}
    try:
        with lab:
            is_ = _SplunkIs(job, lab, S)
            try:
                alanlar, satirlar = is_.kos(job["code"])
            except UserRunError as e:
                return {"status": "error", "error": e.info, "checks": [], "segs": []}
            cikti = _ceviri_metin([_spk_tablo(alanlar, satirlar)])
            segs = [["out", cikti]] if cikti else []
            tester = SplunkTester(job, is_, cikti)
            tns = tester.namespace()
            tns.update(src=job.get("code", ""), sonuc=satirlar, sutunlar=alanlar, dene=tester.dene,
                       ara=tester.ara, kullanir=tester.kullanir, DIZIN=S.DIZIN)
            return _test_kos(tester, tns, job, segs)
    except S.SplunkHatasi as e:
        return {"status": "error", "error": _spk_hata(str(e), "test", "SplunkYok"), "checks": [], "segs": []}


# ── Ağ Tespiti (runner: ids; meta motor: suricata | zeek): sandbox/ids_lab.py ──
# Görevin hazırlığı Python'dur: akis(tur=..., zaman=..., ...) ile trafik tarifine akış ekler
# (biçim: sandbox/ids_trafik.py). Kod, motor suricata ise kural dosyası, zeek ise Zeek betiğidir.

def _ids_lab():
    import importlib.util
    yol = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ids_lab.py")
    spec = importlib.util.spec_from_file_location("pafta_ids_lab", yol)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def _ids_hata(e, tur):
    return {"type": tur, "msg": getattr(e, "msg", str(e)), "line": getattr(e, "satir", None),
            "frames": [], "where": "kod"}


def _ids_tarif(job, ek=""):
    tarif = []
    ns = {"__name__": "__setup__", "akis": lambda **a: tarif.append(a)}
    for kod in (job.get("setup") or "", ek or ""):
        if kod.strip():
            exec(compile(kod, "<setup>", "exec"), ns)
    if not tarif:
        raise ValueError("görevin hazırlığı trafik tarif etmedi (akis(...))")
    return tarif


def _ids_utc(ts):
    # Suricata: 2026-10-19T09:00:00.006000+0000 → 2026-10-19 09:00:00
    return (ts or "")[:19].replace("T", " ")


def _ids_kos(L, is_, job, ek=""):
    """→ (alanlar, satırlar, yardımcılar)"""
    is_.pcap(_ids_tarif(job, ek))
    if job.get("motor", "suricata") == "suricata":
        alarmlar, olaylar = is_.suricata(job["code"])
        satirlar = sorted((_ids_utc(a.get("timestamp")), a["alert"]["signature_id"], a["alert"]["signature"],
                           a.get("src_ip"), a.get("dest_ip"), a.get("dest_port")) for a in alarmlar)
        return (["zaman", "sid", "mesaj", "kaynak", "hedef", "hedef_port"], satirlar,
                {"alarmlar": alarmlar, "olaylar": olaylar})
    cikti, kayitlar = is_.zeek(job["code"])
    satirlar = [(s,) for s in cikti.splitlines() if s.strip()]
    return ["cikti"], satirlar, {"cikti": cikti, "kayitlar": kayitlar}


def do_ids_run(job):
    L = _ids_lab()
    tur = "SuricataHatası" if job.get("motor", "suricata") == "suricata" else "ZeekHatası"
    try:
        with L.Is() as is_:
            alanlar, satirlar, _ = _ids_kos(L, is_, job)
    except L.IdsHatasi as e:
        return {"status": "error", "error": _ids_hata(e, tur), "segs": [], "tablolar": []}
    except ValueError as e:
        return {"status": "error", "error": dict(_ids_hata(e, tur), where="test"), "segs": [], "tablolar": []}
    tablo = {"satir": 1, "sutunlar": alanlar, "kesildi": False,
             "satirlar": [[None if v is None else str(v) for v in r] for r in satirlar]}
    cikti = _ceviri_metin([tablo])
    return {"status": "ok", "segs": [["out", cikti]] if cikti else [], "tablolar": [tablo], "kql": True, "error": None}


class IdsTester(Tester):
    def __init__(self, job, L, is_, cikti):
        super().__init__("", {}, Capture(), "", job)
        self.cap.add("out", cikti)
        self.code = job.get("code", "")
        self.L, self.is_ = L, is_

    def dene(self, hazirlik=""):
        """Görevin trafiğine `hazirlik`taki (Python, akis(...)) akışları ekleyip kodu yeniden çalıştır → satırlar.
        Testin alarmlar / olaylar / kayitlar adları da bu çalıştırmanın sonucunu gösterir."""
        try:
            _, satirlar, yardim = _ids_kos(self.L, self.is_, self.job, hazirlik)
        except self.L.IdsHatasi as e:
            raise UserRunError(_ids_hata(e, "IdsHatası"), hazirlik)
        for ad, deger in yardim.items():
            eski = self.yardim.get(ad)
            if isinstance(eski, dict):
                eski.clear()
                eski.update(deger)
            elif isinstance(eski, list):
                eski[:] = deger
        return satirlar

    def kullanir(self, kelime):
        temiz = re.sub(r"#[^\n]*", " ", self.code)
        return re.search(r"(?<![\w.-])" + re.escape(kelime) + r"(?![\w-])", temiz) is not None


def do_ids_test(job):
    L = _ids_lab()
    tur = "SuricataHatası" if job.get("motor", "suricata") == "suricata" else "ZeekHatası"
    with L.Is() as is_:
        try:
            alanlar, satirlar, yardim = _ids_kos(L, is_, job)
        except L.IdsHatasi as e:
            return {"status": "error", "error": _ids_hata(e, tur), "checks": [], "segs": []}
        except ValueError as e:
            return {"status": "error", "error": dict(_ids_hata(e, tur), where="test"), "checks": [], "segs": []}
        tablo = {"sutunlar": alanlar, "satirlar": [[None if v is None else str(v) for v in r] for r in satirlar]}
        cikti = _ceviri_metin([tablo])
        segs = [["out", cikti]] if cikti else []
        tester = IdsTester(job, L, is_, cikti)
        tester.yardim = yardim
        tns = tester.namespace()
        tns.update(src=job.get("code", ""), sonuc=satirlar, sutunlar=alanlar, dene=tester.dene,
                   kullanir=tester.kullanir, **yardim)
        return _test_kos(tester, tns, job, segs)


# ── Velociraptor (purple yolu, adım meta'sında motor: velociraptor): sandbox/vql_lab.py ──
# Görevin hazırlığı Python'dur ve çalışma klasöründe disk/ altında bir dosya ağacı kurar; kullanıcının
# VQL sorgusu o ağaca Kok değişkeniyle erişir.

def _vql_lab():
    import importlib.util
    yol = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vql_lab.py")
    spec = importlib.util.spec_from_file_location("pafta_vql_lab", yol)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def _vql_deger(v):
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False, sort_keys=True)
    return v


def _vql_kos(V, job, ek=""):
    """Hazırlığı (ve ek hazırlığı) çalıştır, sorguyu disk/ üzerinde koş → (alanlar, satırlar, ham)."""
    for kod in (job.get("setup") or "", ek or ""):
        if kod.strip():
            exec(compile(kod, "<setup>", "exec"), {"__name__": "__setup__"})
    os.makedirs("disk", exist_ok=True)
    ham = V.sorgu(job["code"], os.path.abspath("disk"))
    alanlar = []
    for r in ham:
        for k in r:
            if k not in alanlar:
                alanlar.append(k)
    return alanlar, [tuple(_vql_deger(r.get(a)) for a in alanlar) for r in ham], ham


def _vql_hata(e):
    return {"type": "VQLHatası", "msg": getattr(e, "msg", str(e)), "line": None, "frames": [], "where": "kod"}


def do_vql_run(job):
    V = _vql_lab()
    try:
        alanlar, satirlar, _ = _vql_kos(V, job)
    except V.VqlHatasi as e:
        return {"status": "error", "error": _vql_hata(e), "segs": [], "tablolar": []}
    tablo = {"satir": 1, "sutunlar": alanlar, "kesildi": False,
             "satirlar": [[None if v is None else str(v) for v in r] for r in satirlar]}
    cikti = _ceviri_metin([tablo])
    return {"status": "ok", "segs": [["out", cikti]] if cikti else [], "tablolar": [tablo], "kql": True, "error": None}


class VqlTester(Tester):
    def __init__(self, job, V, cikti):
        super().__init__("", {}, Capture(), "", job)
        self.cap.add("out", cikti)
        self.code = job.get("code", "")
        self.V = V

    def dene(self, hazirlik=""):
        """Hazırlığın üstüne `hazirlik`ı (Python; disk/ altına dosya ekler) çalıştırıp sorguyu yeniden koş → satırlar."""
        try:
            return _vql_kos(self.V, {"setup": "", "code": self.code}, hazirlik)[1]
        except self.V.VqlHatasi as e:
            raise UserRunError(_vql_hata(e), hazirlik)

    def kullanir(self, kelime):
        return re.search(r"(?<![\w])" + re.escape(kelime) + r"(?![\w])", self.code, re.I) is not None


def do_vql_test(job):
    V = _vql_lab()
    try:
        alanlar, satirlar, ham = _vql_kos(V, job)
    except V.VqlHatasi as e:
        return {"status": "error", "error": _vql_hata(e), "checks": [], "segs": []}
    cikti = _ceviri_metin([{"sutunlar": alanlar, "satirlar": [[None if v is None else str(v) for v in r] for r in satirlar]}])
    tester = VqlTester(job, V, cikti)
    tns = tester.namespace()
    tns.update(src=job.get("code", ""), sonuc=satirlar, sutunlar=alanlar, kayitlar=ham, dene=tester.dene,
               kullanir=tester.kullanir)
    return _test_kos(tester, tns, job, [["out", cikti]] if cikti else [])


# ── Sigma → gerçek Splunk (Sigma yolu, adım meta'sında motor: splunk) ──
# Kural (ya da girdi: pipeline ise kullanıcının processing pipeline'ı) gerçek pySigma Splunk backend'iyle
# SPL'e çevrilir ve sandbox/splunk_lab.py'nin gerçek Splunk'ında, hazırlığın dizine aldığı olaylarda
# çalıştırılır. Meta'daki pipeline: virgülle ayrılmış hazır pipeline adları (sysmon, windows, splunk_windows).
# Hazırlık Python'dur: props, veri, olay_turu, etiket ve girdi pipeline ise kural("YAML").

_SGS_HAZIR = {"sysmon": ("sigma.pipelines.sysmon", "sysmon_pipeline"),
              "windows": ("sigma.pipelines.windows", "windows_logsource_pipeline"),
              "splunk_windows": ("sigma.pipelines.splunk", "splunk_windows_pipeline")}


def _sgs_hata(e, where="kod"):
    msg = str(e).split("\n")[0]
    return {"type": "SigmaHatası", "msg": msg[:400], "line": None, "frames": [], "where": where}


_SGS_CLI_HAZIR = {"splunk_windows", "splunk_sysmon_acceleration", "splunk_cim", "sysmon", "windows-logsources",
                  "windows-audit"}
_SGS_CLI_DEGERLI = {"-t", "--target", "-p", "--pipeline", "-f", "--format", "-O", "--backend-option"}
_SGS_CLI_BAYRAK = {"-s", "--skip-unsupported", "--without-pipeline"}


def _sgs_komut(komut, dosyalar):
    """girdi: komut → gerçek sigma-cli (.deps, 3.1.0) `sigma convert ...` komutunu hazırlığın dosyalarıyla geçici
    bir klasörde çalıştır → stdout'taki sorgular. Hedef yalnız splunk, biçim yalnız çalıştırılabilir (default,
    data_model); dosya yazan ya da ağa çıkan seçenek yok."""
    import shlex
    import tempfile
    deps = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".deps")

    def hata(msg):
        return UserRunError(_sgs_hata(msg), "")
    try:
        parca = shlex.split((komut or "").strip(), posix=True)
    except ValueError as e:
        raise hata(f"komut ayrıştırılamadı: {e}")
    if parca[:2] != ["sigma", "convert"]:
        raise hata("komut 'sigma convert' ile başlamalı")
    args, girdiler, i = [], [], 2
    while i < len(parca):
        a = parca[i]
        if a in _SGS_CLI_DEGERLI:
            if i + 1 >= len(parca):
                raise hata(f"{a} bir değer ister")
            v = parca[i + 1]
            if a in ("-t", "--target") and v != "splunk":
                raise hata("bu laboratuvarda hedef yalnız splunk: çıktı gerçek Splunk'ta çalıştırılır")
            if a in ("-f", "--format") and v not in ("default", "data_model"):
                raise hata("biçim default ya da data_model olmalı: çalıştırılabilir sorgu gerekir")
            if a in ("-p", "--pipeline") and v not in _SGS_CLI_HAZIR and v not in dosyalar:
                raise hata(f"pipeline yok: {v} (hazır adlar: {', '.join(sorted(_SGS_CLI_HAZIR))})")
            args += [a, v]
            i += 2
        elif a in _SGS_CLI_BAYRAK:
            args.append(a)
            i += 1
        elif a.startswith("-"):
            raise hata(f"bu laboratuvarda desteklenmeyen seçenek: {a}")
        else:
            yol = a.rstrip("/")
            if (yol.startswith(("/", "\\")) or ":" in yol or ".." in yol.replace("\\", "/").split("/")
                    or not any(k == yol or k.startswith(yol + "/") for k in dosyalar)):
                raise hata(f"girdi yok: {a}")
            girdiler.append(a)
            i += 1
    if not girdiler:
        raise hata("çevrilecek kural dosyası ya da klasörü yok")
    with tempfile.TemporaryDirectory(prefix="pafta_sigma_") as klasor:
        for ad, metin in dosyalar.items():
            hedef = os.path.join(klasor, *ad.split("/"))
            os.makedirs(os.path.dirname(hedef), exist_ok=True)
            with open(hedef, "w", encoding="utf-8") as f:
                f.write(metin)
        on = f"import sys; sys.path.insert(0, {deps!r}); from sigma.cli.main import main; sys.argv=['sigma']+sys.argv[1:]; main()"
        try:
            p = subprocess.run([sys.executable, "-I", "-X", "utf8", "-c", on, "convert", *args, *girdiler], cwd=klasor,
                               capture_output=True, timeout=60, stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            raise hata("sigma-cli 60 saniyede bitmedi")
    cikti = p.stdout.decode("utf-8", "replace")
    if p.returncode:
        satirlar = [s.strip() for s in (p.stderr.decode("utf-8", "replace") + "\n" + cikti).splitlines()
                    if s.strip() and not s.startswith("Parsing Sigma rules")]
        raise hata(f"sigma-cli çıkış kodu {p.returncode}: " + " ".join(satirlar)[:300])
    sorgular = [s.strip() for s in cikti.splitlines() if s.strip() and not s.startswith("Parsing Sigma rules")]
    if not sorgular:
        raise hata("sigma-cli sorgu üretmedi")
    return sorgular


def _sgs_cevir(job, kural_yaml, dosyalar=None):
    """→ SPL sorguları listesi. Çeviri hatası UserRunError olur."""
    if job.get("girdi") == "komut":
        return _sgs_komut(job["code"], dosyalar or {})
    deps = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".deps")
    if deps not in sys.path:
        sys.path.insert(0, deps)
    import importlib
    from sigma.collection import SigmaCollection
    from sigma.backends.splunk import SplunkBackend
    from sigma.processing.pipeline import ProcessingPipeline
    hat = ProcessingPipeline()
    for ad in [a.strip() for a in (job.get("pipeline") or "").split(",") if a.strip()]:
        modul, fn = _SGS_HAZIR[ad]
        hat = hat + getattr(importlib.import_module(modul), fn)()
    try:
        if job.get("girdi") == "pipeline":
            hat = hat + ProcessingPipeline.from_yaml(job["code"])
        sorgular = SplunkBackend(hat).convert(SigmaCollection.from_yaml(kural_yaml))
    except Exception as e:                       # pySigma'nın bütün hata sınıfları
        raise UserRunError(_sgs_hata(e), "")
    if not sorgular:
        raise UserRunError(_sgs_hata("çeviri sorgu üretmedi"), "")
    return sorgular


def _sgs_kos(is_, job, ek=""):
    """Hazırlığı kur, kuralı çevir, son sorguyu Splunk'ta çalıştır → (spl listesi, alanlar, satırlar)."""
    is_.bekleyen = []
    is_.kural_yaml = None
    is_.dosyalar = {}
    is_._hazirlik(ek)
    kural = job["code"] if job.get("girdi", "kural") == "kural" else is_.kural_yaml
    if not kural and job.get("girdi") != "komut":
        raise UserRunError(_sgs_hata("görevin hazırlığı kuralı vermedi (kural(...))", "test"), "")
    sorgular = _sgs_cevir(job, kural, is_.dosyalar)
    for metin, sourcetype, kaynak in is_.bekleyen:
        is_.lab.yukle(metin, sourcetype, kaynak)
    # data_model biçimi | tstats ile başlar; veri modeli kapısı (etiket) laboratuvar dizinindeki olayları seçer.
    # temporal korelasyon | multisearch [ search ... ] üretir: her alt arama laboratuvar dizinine sınırlanır.
    son = sorgular[-1]
    if son.startswith("|"):
        son = son.replace("[ search ", f"[ search index={is_.S.DIZIN} ")
    else:
        son = f"search index={is_.S.DIZIN} " + son
    alanlar, satirlar = is_.ara(son)
    return sorgular, alanlar, satirlar


def do_sgs_run(job):
    S, lab, err = _spk_ac()
    if err:
        return {"status": "error", "error": err, "segs": [], "tablolar": []}
    try:
        with lab:
            sorgular, alanlar, satirlar = _sgs_kos(_SplunkIs(job, lab, S), job)
    except UserRunError as e:
        return {"status": "error", "error": e.info, "segs": [], "tablolar": []}
    except S.SplunkHatasi as e:
        return {"status": "error", "error": _spk_hata(str(e), "test", "SplunkYok"), "segs": [], "tablolar": []}
    tablo = _spk_tablo(alanlar, satirlar)
    cikti = _ceviri_metin([tablo])
    segs = [["raw", "Üretilen SPL:\n" + "\n---\n".join(sorgular) + "\n\n"]] + ([["out", cikti]] if cikti else [])
    return {"status": "ok", "segs": segs, "tablolar": [tablo], "kql": True, "error": None}


class SgsTester(SplunkTester):
    def dene(self, hazirlik=""):
        """Laboratuvarı boşaltıp hazırlığı + `hazirlik`ı yeniden kur, aynı kuralı yeniden çalıştır → satırlar."""
        self.is_.lab.bosalt()
        try:
            return _sgs_kos(self.is_, self.job, hazirlik)[2]
        except UserRunError as e:
            raise UserRunError(e.info, hazirlik)

    def cevir(self, kural_yaml):
        """Başka bir kuralı aynı pipeline'la çevir → SPL listesi (çalıştırmaz)."""
        return _sgs_cevir(self.job, kural_yaml)


def do_sgs_test(job):
    S, lab, err = _spk_ac()
    if err:
        return {"status": "error", "error": err, "checks": [], "segs": []}
    try:
        with lab:
            is_ = _SplunkIs(job, lab, S)
            try:
                sorgular, alanlar, satirlar = _sgs_kos(is_, job)
            except UserRunError as e:
                return {"status": "error", "error": e.info, "checks": [], "segs": []}
            cikti = _ceviri_metin([_spk_tablo(alanlar, satirlar)])
            segs = [["raw", "Üretilen SPL:\n" + "\n---\n".join(sorgular) + "\n\n"]] + ([["out", cikti]] if cikti else [])
            tester = SgsTester(job, is_, cikti)
            tns = tester.namespace()
            tns.update(src=job.get("code", ""), sonuc=satirlar, sutunlar=alanlar, spl=sorgular, dene=tester.dene,
                       ara=tester.ara, cevir=tester.cevir, kullanir=tester.kullanir, DIZIN=S.DIZIN,
                       alan=lambda ad, satirlar=satirlar, alanlar=alanlar:
                           [r[alanlar.index(ad)] if ad in alanlar else None for r in satirlar])
            return _test_kos(tester, tns, job, segs)
    except S.SplunkHatasi as e:
        return {"status": "error", "error": _spk_hata(str(e), "test", "SplunkYok"), "checks": [], "segs": []}


MODES = {"run": do_run, "test": do_test, "trace": do_trace, "dis": do_dis,
         "ad_run": do_ad_run, "ad_test": do_ad_test, "ad_dis": do_ad_dis,
         "packet_run": do_packet_run, "packet_test": do_packet_test,
         "elastic_run": do_elastic_run, "elastic_test": do_elastic_test,
         "sigma_run": lambda j: do_detection_run(j, "sigma"), "sigma_test": lambda j: do_detection_test(j, "sigma"),
         "yara_run": lambda j: do_detection_run(j, "yara"), "yara_test": lambda j: do_detection_test(j, "yara"),
         "kql_run": lambda j: do_ceviri_run(j, "kql"), "kql_test": lambda j: do_ceviri_test(j, "kql"),
         "kql_dis": lambda j: do_ceviri_dis(j, "kql"),
         "spl_run": lambda j: do_ceviri_run(j, "spl"), "spl_test": lambda j: do_ceviri_test(j, "spl"),
         "spl_dis": lambda j: do_ceviri_dis(j, "spl"),
         "regex_run": do_regex_run, "regex_test": do_regex_test, "regex_dis": do_regex_dis,
         "proc_run": do_proc_run, "proc_test": do_proc_test, "proc_trace": do_proc_trace,
         "sql_run": do_sql_run, "sql_test": do_sql_test, "sql_dis": do_sql_dis,
         "pg_run": do_pg_run, "pg_test": do_pg_test,
         "my_run": do_my_run, "my_test": do_my_test,
         "spk_run": do_spk_run, "spk_test": do_spk_test,
         "ids_run": do_ids_run, "ids_test": do_ids_test,
         "vql_run": do_vql_run, "vql_test": do_vql_test,
         "sgs_run": do_sgs_run, "sgs_test": do_sgs_test}


def main():
    job_path, result_path = sys.argv[1], sys.argv[2]
    with open(job_path, encoding="utf-8") as f:
        job = json.load(f)
    sys.argv = ["kod.py"]
    register_source(job.get("code", ""))
    try:
        res = MODES[job["mode"]](job)
    except BaseException:
        res = {"status": "internal", "detail": traceback.format_exc()}
    data = json.dumps(res, ensure_ascii=False, default=repr)
    with open(result_path, "w", encoding="utf-8") as f:
        f.write(data)
    try:
        sys.__stdout__.flush()
    except Exception:
        pass
    os._exit(0)


if __name__ == "__main__":
    main()
