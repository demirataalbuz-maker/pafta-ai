"""Pafta's existing test/trace harness inside a disposable Linux work directory."""
import importlib.util
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import traceback

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("pafta_harness", HERE / "py_harness.py")
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)


def linux_process(job, stdin="", argv=None, iz=False):
    """Wait for the script, not for pipe EOF from its background descendants.

    The outside guardian owns the whole deadline and cleans all descendants
    after the harness returns, including ones which changed their session.
    File-backed output also caps what is loaded back into the JSON result.
    """
    proc = job["proc"]
    shift = harness._betik_yaz(job, iz=iz)
    cmd = list(proc["iz_cmd"] if iz and proc.get("iz_cmd") else proc["cmd"])
    cmd += [proc["dosya"]] + [str(arg) for arg in (argv or [])]
    env = dict(os.environ, **proc.get("env", {}))
    with tempfile.TemporaryFile() as inp, tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        inp.write((stdin or "").encode("utf-8"))
        inp.seek(0)
        child = subprocess.Popen(cmd, stdin=inp, stdout=out, stderr=err, env=env)
        child.wait()  # The Linux guardian covers setup, all runs, and tests.
        texts = []
        for stream in (out, err):
            stream.seek(0)
            raw = stream.read(harness.OUT_LIMIT + 1)
            text = raw[:harness.OUT_LIMIT].decode("utf-8", "replace").replace("\r\n", "\n")
            if len(raw) > harness.OUT_LIMIT:
                text += "\n[Pafta: çıktı sınırda kesildi]\n"
            texts.append(text)
        return child.returncode, texts[0], texts[1], shift


harness._calistir = linux_process


def exec_user(code, stdin="", echo=False, argv=None, kalici=False):
    """Keep Python namespace tests, but never accept nonzero sys.exit as success."""
    cap = harness.Capture()
    feeder = harness.Feeder(stdin, cap, echo)
    err = None
    with harness.Redirect(cap, feeder, argv), harness.ana_modul(kalici) as ns:
        try:
            exec(compile(code, harness.FNAME, "exec"), ns)
        except SystemExit as exc:
            value = exc.code
            code = 0 if value is None else value if isinstance(value, int) else 1
            if code:
                err = {"type": "ÇıkışKodu", "kod": code, "msg": f"Python sys.exit({value!r}) ile bitti.",
                       "line": None, "frames": [], "where": "kod"}
        except BaseException as exc:
            err = harness.err_info(exc, ns)
    return ns, cap, err


harness.exec_user = exec_user


def python_run(job):
    """Use a real Python script process: file bytes, native stderr and exit code."""
    Path("kod.py").write_text(job["code"].replace("\r\n", "\n"), encoding="utf-8", newline="\n")
    proc_job = dict(job, proc={
        "cmd": [sys.executable, "-I", "-X", "utf8", "-u", str(HERE / "wsl_job.py"),
                "--script", str(HERE / "job.json")],
        "dosya": "kod.py", "sure": job["_timeout"],
        "satir_deseni": r'File "[^"]*kod\.py", line (\d+)'})
    # _calistir also uses real files and preserves argv/stdin/stdout/stderr.
    result = harness._calistir(proc_job, job.get("stdin", ""), job.get("argv"))
    if result is None:
        return {"status": "timeout", "segs": [], "error": harness._zaman_asimi(proc_job)}
    code, out, err, shift = result
    info = harness._surec_hatasi(proc_job, code, err, shift) if code else None
    return {"status": "error" if code else "ok", "kod": code, "error": info,
            "segs": ([["out", out]] if out else []) + ([["err", err]] if err else [])}


def script_main():
    """Setup and script share modules/servers, but real streams and an exit code.

    Like the existing harness, exit after the script so a learner's lingering
    thread cannot prevent the Linux guardian from completing the job.
    """
    job = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    sys.argv = sys.argv[3:]
    code = 0
    try:
        harness.run_setup(job)
        runpy.run_path(sys.argv[0], run_name="__main__")
    except SystemExit as exc:
        if exc.code is None:
            code = 0
        elif isinstance(exc.code, int):
            code = exc.code & 255
        else:
            print(exc.code, file=sys.stderr)
            code = 1
    except BaseException:
        traceback.print_exc()
        code = 1
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)


def main():
    if sys.argv[1] == "--script":
        script_main()
    job = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    result_path = Path(sys.argv[2])
    sys.argv = ["kod.py"]
    harness.register_source(job.get("code", ""))
    if job["mode"] == "run":
        res = python_run(job)
    else:
        res = harness.MODES[job["mode"]](job)
    result_path.write_text(json.dumps(res, ensure_ascii=False, default=repr), encoding="utf-8", newline="\n")
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)


if __name__ == "__main__":
    main()

