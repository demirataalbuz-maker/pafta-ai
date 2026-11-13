"""Windows-side JSON transport to a Linux-owned WSL job supervisor."""
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time

HERE = Path(__file__).resolve().parent
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
DEFAULT_TIMEOUT = 60
TEST_TIMEOUT = 120
MAX_TIMEOUT = 300
STARTUP_GRACE = 30
CLEANUP_GRACE = 12
OUTPUT_LIMIT = 2_000_000
# Linux işinin klasörüne kopyalanan dosyalar; wsl_supervisor.py aynı listeyi yazar.
# api_tezgah.py: derslerin hazırlık bloğunun başlattığı yerel API laboratuvarı.
SOURCES = ("py_harness.py", "wsl_job.py", "api_tezgah.py")


def distro_name():
    name = os.environ.get("PAFTA_WSL_DISTRO", "kali-linux").strip()
    if not name or name.startswith("-") or len(name) > 128 or any(c in name for c in "\x00\r\n"):
        raise ValueError("PAFTA_WSL_DISTRO geçerli bir WSL dağıtım adı olmalı.")
    return name


def seconds(value, default=DEFAULT_TIMEOUT):
    value = default if value is None else value
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError("WSL timeout sayısal olmalı.") from None
    if isinstance(value, bool) or not math.isfinite(number) or not 0 < number <= MAX_TIMEOUT:
        raise ValueError("WSL timeout 0'dan büyük ve en fazla 300 saniye olmalı.")
    return number


def command(distro=None):
    exe = shutil.which("wsl.exe")
    if not exe:
        raise FileNotFoundError("WSL bulunamadı. README'deki Kali WSL gereksinimlerini tamamlayın.")
    # argv list, not a shell string: paths and payload never pass through MSYS.
    return [exe, "--distribution", distro or distro_name(), "--cd", "/tmp",
            "--exec", "/usr/bin/python3", "-I", "-X", "utf8", "-u"]


def failure(message, status="error"):
    return {"status": status, "segs": [], "error": {
        "type": "WSL", "msg": message, "line": None, "frames": [], "where": "kod"}}


def _decode(raw):
    # wsl.exe diagnostics may be UTF-16LE; Linux stdout itself is UTF-8.
    return raw.decode("utf-16-le" if b"\x00" in raw[:100] else "utf-8", "replace").strip()


def available():
    try:
        result = subprocess.run(command() + ["-c", "import ctypes,os,sys; print(sys.platform)"],
                                capture_output=True, timeout=15, creationflags=NO_WINDOW)
        return result.returncode == 0 and result.stdout.strip() == b"linux"
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return False


def execute(job, timeout=None, cancel_event=None):
    """Return existing harness JSON plus runtime evidence; Event.set() cancels.

    Keeping stdin open is part of the protocol. Closing it on parent exit is
    observed by the Linux supervisor and invokes the same descendant cleanup.
    """
    timeout = seconds(timeout)
    try:
        distro = distro_name()
        argv = command(distro)
    except (OSError, ValueError) as exc:
        return failure(str(exc))
    if cancel_event is not None and cancel_event.is_set():
        return failure("Linux işi başlamadan iptal edildi.", "cancelled")
    request = {"timeout": timeout, "job": dict(job, _timeout=timeout),
               "sources": {name: (HERE / name).read_text(encoding="utf-8")
                           for name in SOURCES}}
    # No Linux access to the Windows checkout is needed, even with emoji paths.
    data = (json.dumps(request, ensure_ascii=True) + "\n").encode("ascii")
    supervisor = (HERE / "wsl_supervisor.py").read_text(encoding="utf-8")
    # The -c command remains ASCII and below Windows' command line size limit.
    import base64
    bootstrap = "import base64;exec(compile(base64.b64decode('" + base64.b64encode(
        supervisor.encode("utf-8")).decode("ascii") + "'),'<pafta-wsl>','exec'))"
    try:
        child = subprocess.Popen(argv + ["-c", bootstrap], stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 creationflags=NO_WINDOW)
    except OSError as exc:
        return failure(str(exc))
    outputs = [bytearray(), bytearray()]
    overflow = [False, False]
    sent = threading.Event()
    write_errors = []

    def write():
        try:
            child.stdin.write(data)
            child.stdin.flush()
        except (OSError, ValueError) as exc:
            write_errors.append(str(exc))
        finally:
            sent.set()

    def read(stream, index):
        try:
            while True:
                block = stream.read(65536)
                if not block:
                    break
                room = OUTPUT_LIMIT - len(outputs[index])
                outputs[index].extend(block[:max(0, room)])
                overflow[index] |= len(block) > room
        finally:
            stream.close()

    writer = threading.Thread(target=write, daemon=True)
    readers = [threading.Thread(target=read, args=(child.stdout, 0), daemon=True),
               threading.Thread(target=read, args=(child.stderr, 1), daemon=True)]
    for thread in readers + [writer]:
        thread.start()
    deadline = time.monotonic() + STARTUP_GRACE + timeout
    cancellation = None
    cancel_sent = False
    try:
        while child.poll() is None:
            if cancellation is None and (time.monotonic() >= deadline or
                    (cancel_event is not None and cancel_event.is_set())):
                cancellation = "timeout" if time.monotonic() >= deadline else "cancelled"
                deadline = time.monotonic() + CLEANUP_GRACE
            elif cancellation and time.monotonic() >= deadline:
                child.kill()
                child.wait(timeout=3)
                res = failure("WSL bağlantısı yanıt vermedi; Linux temizliği doğrulanamadı.")
                res["runtime"] = {"backend": "wsl", "distribution": distro, "cleanup": False}
                return res
            if cancellation and sent.is_set() and not cancel_sent:
                try:
                    child.stdin.write(b"cancel\n")
                    child.stdin.flush()
                except (OSError, ValueError):
                    pass
                cancel_sent = True
            time.sleep(0.02)
        for thread in readers:
            thread.join(timeout=3)
        if any(thread.is_alive() for thread in readers) or any(overflow):
            return failure("WSL yanıtı eksik veya boyut sınırını aşıyor.")
        try:
            result = json.loads(bytes(outputs[0]).decode("utf-8"))
            if not isinstance(result, dict) or "status" not in result:
                raise ValueError("geçersiz sonuç")
        except (ValueError, UnicodeError):
            detail = _decode(bytes(outputs[1])) or _decode(bytes(outputs[0])) or "; ".join(write_errors)
            return failure(f"WSL/{distro} başlayamadı veya JSON sonucu yok (kod {child.returncode}). "
                           f"Dağıtım ve /usr/bin/python3 kurulumunu kontrol edin. {detail[:1500]}")
        result.setdefault("runtime", {}).update(backend="wsl", distribution=distro)
        if cancellation == "timeout" and result["status"] == "cancelled":
            result.update(status="timeout", timeout=timeout)
            result["error"].update(type="Zaman aşımı", msg="WSL bağlantısı ve iş için ayrılan süre doldu.")
        return result
    finally:
        # EOF is also the cancellation signal when Python raises/gets interrupted.
        if sent.wait(timeout=0.1):
            try:
                child.stdin.close()
            except (OSError, ValueError):
                pass
        if child.poll() is None:
            try:
                child.wait(timeout=CLEANUP_GRACE)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=3)
        for thread in readers + [writer]:
            thread.join(timeout=1)

