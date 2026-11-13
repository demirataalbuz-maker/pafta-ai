"""Single native faults in comparisons, flow, expansion, files and text filters.

No source-string assertions grade the learner. Mutants run through the same
native ProcTester as ordinary solutions. A survivor must be reviewed; some
threshold shifts can be equivalent for a task's explicitly restricted domain.
Native nonzero exits are counted separately from failed result assertions.
"""
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from engine.lessons import Library
from engine.runners import get


def mutations(source):
    pairs = {"lss": "leq", "leq": "lss", "gtr": "geq", "geq": "gtr", "equ": "neq", "neq": "equ"}
    for match in re.finditer(r"\b(LSS|LEQ|GTR|GEQ|EQU|NEQ)\b", source, re.I):
        replacement = pairs[match[0].lower()].upper()
        yield f"comparison {match[0]}->{replacement} at {match.start()}", source[:match.start()] + replacement + source[match.end():]
    for match in re.finditer(r"&&|\|\|", source):
        replacement = "||" if match[0] == "&&" else "&&"
        yield f"flow {match[0]}->{replacement} at {match.start()}", source[:match.start()] + replacement + source[match.end():]
    for match in re.finditer(r"\bif\s+(?:not\s+)?errorlevel\s+(-?\d+)\b", source, re.I):
        for delta in (-1, 1):
            value = str(int(match[1]) + delta)
            yield f"errorlevel {match[1]}->{value} at {match.start(1)}", source[:match.start(1)] + value + source[match.end(1):]
    for match in re.finditer(r"\bfor\s+/l\s+%%\w\s+in\s*\(\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*\)", source, re.I):
        for group in (1, 3):
            for delta in (-1, 1):
                value = str(int(match[group]) + delta)
                yield f"FOR/L endpoint {match[group]}->{value} at {match.start(group)}", source[:match.start(group)] + value + source[match.end(group):]
    for pattern, replacement, label in (
        (r"\bEnableDelayedExpansion\b", "DisableDelayedExpansion", "disable delayed expansion"),
        (r"(?im)^(\s*)if /i ", r"\1if ", "remove IF case folding"),
        (r"(?im)^(\s*)>>(?!&)", r"\1>", "append becomes overwrite"),
        (r"(?i)\bsort /l C\b", "sort /r /l C", "reverse sort"),
        (r"(?i)\bcopy /b\b", "copy /a", "binary copy becomes text copy"),
        (r"(?i)\btokens=1,3\b", "tokens=1,2", "wrong FOR/F token"),
        (r"(?i)\bfindstr /l\b", "findstr /r", "literal becomes regex"),
        (r"\+=1\b", "+=2", "counter increment"),
        (r"\+511\b", "+510", "round-up boundary"),
    ):
        for match in re.finditer(pattern, source):
            changed = re.sub(pattern, replacement, match[0], count=1)
            yield f"{label} at {match.start()}", source[:match.start()] + changed + source[match.end():]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    library, wanted = Library(), set(sys.argv[1:])
    tasks = [(f"{lid}:{index}", step)
             for lid in library.outline("cmd")["order"] if not wanted or lid in wanted
             for index, step in enumerate(library.lesson("cmd", lid)["steps"])
             if step["kind"] == "gorev"]
    def baseline(job):
        ref, step = job
        return ref, get("cmd").test(step["solution"], step)
    with ThreadPoolExecutor(max_workers=4) as pool:
        originals = list(pool.map(baseline, tasks))
    bad = [(ref, result) for ref, result in originals if result["status"] != "pass"]
    if bad:
        for ref, result in bad:
            print("ORIGINAL FAILED", ref, result)
        return 1
    jobs = [(ref, step, label, source) for ref, step in tasks for label, source in mutations(step["solution"])]
    def check(job):
        ref, step, label, source = job
        return ref, label, get("cmd").test(source, step)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(check, jobs))
    counts = {status: sum(r["status"] == status for _, _, r in results)
              for status in ("pass", "fail", "error", "timeout", "internal")}
    print(f"{len(tasks)} original solutions pass; {len(jobs)} single mutations; {counts}")
    for ref, label, result in results:
        if result["status"] not in ("fail", "error"):
            print(result["status"].upper(), ref, label)
    return int(any(r["status"] not in ("fail", "error") for _, _, r in results))


if __name__ == "__main__":
    sys.exit(main())
