"""Boundary checks for native CMD configuration lessons CM21–CM22."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.lessons import Library
from engine.runners import get


MUTANTS = {
    ("cm21", 0): [
        ('sc.exe qc "%ad%"', 'sc.exe query "%ad%"'),
        ('sc.exe qc "%ad%"', 'sc.exe qc "EventLog"'),
    ],
    ("cm21", 1): [
        ('/fo CSV /nh', '/fo TABLE /nh'),
        ('/fo CSV /nh', '/fo CSV'),
        ('/tn "%ad%"', ''),
    ],
    ("cm22", 0): [
        ('/v "%ad%"', ''),
        ('/v "%ad%"', '/v ProductName'),
    ],
    ("cm22", 1): [
        ('/f "%ad%" /e /c', '/f "%ad%" /c'),
        ('/f "%ad%" /e /c', '/f "%ad%" /e'),
        ('/f "%ad%" /e /c', '/f "ProductName" /e /c'),
        ('reg.exe query "%kok%" >nul', 'echo ok >nul'),
    ],
}


def main():
    runner = get("cmd")
    library = Library()
    checked = 0
    for (lesson_id, task_index), variants in MUTANTS.items():
        task = [s for s in library.lesson("cmd", lesson_id)["steps"] if s["kind"] == "gorev"][task_index]
        code = task["solution"]
        assert runner.test(code, task)["status"] == "pass", (lesson_id, task_index)
        for before, after in variants:
            assert before in code, (lesson_id, before)
            mutant = code.replace(before, after)
            result = runner.test(mutant, task)
            assert result["status"] in {"fail", "error"}, (lesson_id, task_index, before, after, result)
            checked += 1
    print(f"{checked} CMD configuration mutants rejected")


if __name__ == "__main__":
    main()
