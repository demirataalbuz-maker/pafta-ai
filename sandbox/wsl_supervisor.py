"""Linux guardian for one Pafta job; launched by wsl.exe, never imported on Windows.

The control pipe remains open after the JSON request. EOF cancels the job.
A subreaper owns orphaned/detached descendants; cleanup runs on every exit.
This is lifecycle management, not a security sandbox for hostile programs.
"""
import ctypes
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import tempfile
import time

LIMIT = 200_000
CLEANUP_SECONDS = 8


def error(status, message, kind="WSL"):
    return {"status": status, "segs": [], "error": {
        "type": kind, "msg": message, "where": "kod", "line": None, "frames": []}}


def subreaper():
    libc = ctypes.CDLL(None, use_errno=True)
    libc.prctl.argtypes = [ctypes.c_int] + [ctypes.c_ulong] * 4
    libc.prctl.restype = ctypes.c_int
    if libc.prctl(36, 1, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
        raise OSError(ctypes.get_errno(), "PR_SET_CHILD_SUBREAPER")
    # pidfds prevent sending a signal to a recycled PID.
    fd = os.pidfd_open(os.getpid())
    os.close(fd)


def children():
    """Direct live or zombie children; orphans are adopted by this supervisor."""
    path = Path(f"/proc/{os.getpid()}/task/{os.getpid()}/children")
    return [int(pid) for pid in path.read_text().split()]


def cleanup(child):
    """Kill roots, adopt detached grandchildren, kill and reap until ECHILD."""
    # Reap Popen first, so waitpid below never steals its return code.
    child.poll()
    deadline = time.monotonic() + CLEANUP_SECONDS
    while True:
        for pid in children():
            try:
                fd = os.pidfd_open(pid)
            except ProcessLookupError:
                continue
            try:
                signal.pidfd_send_signal(fd, signal.SIGKILL)
            except ProcessLookupError:
                pass
            finally:
                os.close(fd)
        child.poll()
        # Once the Popen child has been reaped, all other children are adopted
        # descendants. Detached double forks eventually become direct children.
        if child.returncode is not None:
            while True:
                try:
                    pid, _ = os.waitpid(-1, os.WNOHANG)
                except ChildProcessError:
                    return
                if pid == 0:
                    break
        if time.monotonic() >= deadline:
            raise RuntimeError("Linux alt süreçleri kapanmadı; temizlik doğrulanamadı.")
        time.sleep(0.01)


def read_output(path):
    with path.open("rb") as stream:
        data = stream.read(LIMIT + 1)
    return data[:LIMIT].decode("utf-8", "replace").replace("\r\n", "\n"), len(data) > LIMIT


def serve(payload, control):
    timeout = float(payload["timeout"])
    if not 0 < timeout <= 300:
        raise ValueError("WSL zaman sınırı 0–300 saniye aralığında olmalı.")
    subreaper()
    # Explicit /tmp: ignore inherited Windows cwd and TMPDIR (/mnt/c).
    with tempfile.TemporaryDirectory(prefix="pafta_wsl_", dir="/tmp") as folder:
        root = Path(folder)
        work = root / "calisma"
        work.mkdir()
        for name in ("py_harness.py", "wsl_job.py", "api_tezgah.py"):    # wsl_process.SOURCES ile aynı
            (root / name).write_text(payload["sources"][name].replace("\r\n", "\n"),
                                     encoding="utf-8", newline="\n")
        job = payload["job"]
        for key in ("code", "setup", "test", "stdin"):
            if isinstance(job.get(key), str):
                job[key] = job[key].replace("\r\n", "\n")
        (root / "job.json").write_text(json.dumps(job, ensure_ascii=False),
                                     encoding="utf-8", newline="\n")
        env = dict(os.environ, LANG="C.UTF-8", LC_ALL="C.UTF-8",
                   PYTHONIOENCODING="utf-8", PYTHONUTF8="1",
                   TMPDIR=str(work), TMP=str(work), TEMP=str(work),
                   PIP_NO_INDEX="1", PIP_DISABLE_PIP_VERSION_CHECK="1",
                   PIP_NO_CACHE_DIR="1")
        # No inherited Windows executables or shell startup script.
        env["PATH"] = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
        for key in ("BASH_ENV", "ENV", "PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV"):
            env.pop(key, None)
        result_path = root / "result.json"
        out_path, err_path = root / "stdout", root / "stderr"
        child = None
        reason = None
        started = time.monotonic()
        with out_path.open("wb") as out, err_path.open("wb") as err:
            child = subprocess.Popen(
                [sys.executable, "-I", "-X", "utf8", "-u", str(root / "wsl_job.py"),
                 str(root / "job.json"), str(result_path)], cwd=work,
                stdin=subprocess.DEVNULL, stdout=out, stderr=err, env=env,
                start_new_session=True)
            try:
                deadline = started + timeout
                while child.poll() is None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        reason = "timeout"
                        break
                    if control.select(min(0.05, remaining)):
                        # Any control line or closed pipe is a cancellation.
                        os.read(sys.stdin.fileno(), 4096)
                        reason = "cancelled"
                        break
            finally:
                cleanup(child)
        if reason:
            res = error(reason, f"Linux işi {timeout:g} saniyede bitmedi." if reason == "timeout"
                        else "Linux işi iptal edildi.", "Zaman aşımı" if reason == "timeout" else "İptal")
            res["timeout"] = timeout
        else:
            try:
                res = json.loads(result_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                res = error("error", f"Python sonuç yazmadan {child.returncode} koduyla kapandı.", "SüreçBitti")
                res["kod"] = child.returncode
        for kind, path in (("out", out_path), ("err", err_path)):
            text, truncated = read_output(path)
            if text:
                res.setdefault("segs", []).append([kind, text])
            if truncated:
                res["truncated"] = True
        res["runtime"] = {
            "backend": "wsl", "python": sys.version.split()[0],
            "executable": sys.executable, "cwd": str(work),
            "supervisor_pid": os.getpid(), "worker_pid": child.pid,
            "worker_exit_code": child.returncode, "cleanup": True,
            "elapsed": round(time.monotonic() - started, 3)}
        return res


def main():
    # Unbuffered first-line read: a TextIO buffer must not swallow cancellation
    # bytes which selectors then cannot see.
    raw = bytearray()
    while not raw.endswith(b"\n"):
        chunk = os.read(sys.stdin.fileno(), 1)
        if not chunk:
            return
        raw.extend(chunk)
        if len(raw) > 4_000_000:
            raise ValueError("WSL işi çok büyük.")
    payload = json.loads(raw)
    with selectors.DefaultSelector() as control:
        control.register(sys.stdin.fileno(), selectors.EVENT_READ)
        try:
            res = serve(payload, control)
        except BaseException as exc:
            res = error("error", f"{type(exc).__name__}: {exc}")
            res["runtime"] = {"backend": "wsl", "cleanup": False}
        print(json.dumps(res, ensure_ascii=True), flush=True)


if __name__ == "__main__":
    main()

