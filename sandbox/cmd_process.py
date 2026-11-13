"""Native cmd.exe execution for the existing ProcRunner/ProcTester protocol.

The bootstrap changes only this child process's code page. Repository sources
stay UTF-8/LF; temporary batch files use CRLF for native cmd.exe parsing.
No CALL/reparse is used to pass arguments.
"""
import os
from pathlib import Path
import subprocess

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def run_batch(job, stdin="", argv=None):
    proc = job["proc"]
    source = (job.get("code") or "").replace("\r\n", "\n")
    Path(proc["dosya"]).write_text(source + ("" if source.endswith("\n") else "\n"),
                                  encoding="utf-8", newline="\r\n")
    env = dict(os.environ)
    env.update(proc.get("env", {}))
    # Git Bash prepends Unix tools called find.exe/sort.exe to PATH. A CMD
    # lesson must resolve Windows commands with their Windows argument syntax.
    # Change only this child environment; retain the remaining search path.
    system_root = env.get("SystemRoot") or env.get("SYSTEMROOT") or r"C:\Windows"
    path_key = next((key for key in env if key.upper() == "PATH"), "PATH")
    env[path_key] = os.pathsep.join((os.path.join(system_root, "System32"),
                                     system_root, env.get(path_key, "")))
    arguments = [str(a) for a in (argv or [])]
    if any(any(c in a for c in ('"', "\x00", "\r", "\n")) for a in arguments):
        return (87, "", "Pafta CMD: argv değerinde çift tırnak, NUL veya satır sonu desteklenmez.\n", 0)
    # Expansion of an environment variable is a single pass: a literal %PATH%
    # in an argument is not expanded a second time. Quotes keep &|<> as data;
    # /v:off preserves exclamation marks until learner code enables expansion.
    names = []
    for number, argument in enumerate(arguments):
        name = f"__PAFTA_CMD_ARG_{number}"
        env[name] = argument
        names.append('"%' + name + '%"')
    # CHCP can consume a redirected input file while switching code pages.
    # Give the bootstrap command NUL, leaving learner stdin at byte zero.
    bootstrap = '@echo off\nchcp 65001 >nul <nul\n.\\' + proc["dosya"]
    if names:
        bootstrap += " " + " ".join(names)
    Path("_pafta_cmd.cmd").write_text(bootstrap + "\n", encoding="ascii", newline="\r\n")
    # Explicit relative paths work even when current-directory executable
    # lookup is disabled by NoDefaultCurrentDirectoryInExePath.
    command = list(proc["cmd"]) + [r".\_pafta_cmd.cmd"]
    # SET /P can read ahead and discard subsequent lines from a Windows pipe.
    # A redirected input file gives native CMD reliable sequential line reads.
    input_path = Path("_pafta_cmd_stdin.txt")
    input_path.write_text((stdin or "").replace("\r\n", "\n"), encoding="utf-8", newline="\r\n")
    with input_path.open("rb") as input_file:
        child = subprocess.Popen(command, stdin=input_file, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, env=env, creationflags=NO_WINDOW)
        return _collect(child, proc.get("sure", 10))


def _collect(child, timeout):
    try:
        out, err = child.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(child.pid)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       creationflags=NO_WINDOW)
        child.communicate()
        return None
    return (child.returncode, out.decode("utf-8", "replace").replace("\r\n", "\n"),
            err.decode("utf-8", "replace").replace("\r\n", "\n"), 0)
