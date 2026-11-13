"""Native CMD token/DACL curriculum mutation checks."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.lessons import Library
from engine.runners import get


MUTANTS = {
    ("cm23", 0): [
        ('/user /fo CSV /nh', '/groups /fo CSV /nh'),
        ('/groups /fo CSV /nh', '/priv /fo CSV /nh'),
        ('/fo CSV /nh', '/fo TABLE /nh'),
    ],
    ("cm23", 1): [
        ('/priv /fo CSV /nh', '/groups /fo CSV /nh'),
        ('if /i "%%~A"=="%hedef%"', 'if "%%~A"=="%hedef%"'),
        ('if /i "%%~A"=="%hedef%"', 'if /i "%%~A"=="SeChangeNotifyPrivilege"'),
        ('>"secim.csv" type nul', 'rem eski secimi koru'),
    ],
    ("cm24", 0): [
        ('icacls.exe "%dosya%"', 'type "%dosya%"'),
        ('icacls.exe "%dosya%"', 'icacls.exe "delil dosyasi.txt"'),
    ],
    ("cm24", 1): [
        ('/groups /fo CSV /nh', '/priv /fo CSV /nh'),
        ('/priv /fo CSV /nh', '/groups /fo CSV /nh'),
        ('icacls.exe "%dosya%"', 'type "%dosya%"'),
        ('type "%dosya%" >"okuma.txt"', 'type "delil dosyasi.txt" >"okuma.txt"'),
    ],
}


def main():
    library = Library()
    runner = get("cmd")
    count = 0
    for (lesson_id, task_index), edits in MUTANTS.items():
        task = [s for s in library.lesson("cmd", lesson_id)["steps"] if s["kind"] == "gorev"][task_index]
        solution = task["solution"]
        assert runner.test(solution, task)["status"] == "pass", (lesson_id, task_index)
        for old, new in edits:
            assert old in solution, (lesson_id, old)
            result = runner.test(solution.replace(old, new), task)
            assert result["status"] in {"fail", "error"}, (lesson_id, task_index, old, result)
            count += 1
    print(f"{count} CMD token/DACL mutants rejected")


if __name__ == "__main__":
    main()
