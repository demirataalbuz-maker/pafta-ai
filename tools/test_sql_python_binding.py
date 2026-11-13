"""SQ19 application-to-SQL binding in real sqlite3, not a query simulator."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.lessons import Library
from engine.runners import get, for_step


def main():
    steps = Library().lesson('sql', 'sq19')['steps']
    cases = {
        'personel_ara': [
            ('exclude CPU equal lower', '0<=min_cpu', '0<min_cpu'),
            ('exclude CPU equal upper', 'min_cpu<=100', 'min_cpu<100'),
            ('accept out-of-range CPU', 'min_cpu<=100', 'min_cpu<=101'),
            ('bool accepted as CPU', 'type(min_cpu) is not int', 'not isinstance(min_cpu,int)'),
            ('weak direction type', 'type(azalan) is not bool', 'False'),
            ('threshold exclusive', 'cpu >= ?', 'cpu > ?'),
            ('NULL equality broken', 'ad IS ?', 'ad = ?'),
            ('case-insensitive names', 'ad IS ?', 'ad IS ? COLLATE NOCASE'),
            ('direction reversed', "'DESC' if azalan else 'ASC'", "'ASC' if azalan else 'DESC'"),
            ('tie breaker removed', "+', id ASC'", "+''"),
            ('constant threshold', '(ad,min_cpu)', '(ad,0)'),
            ('parameter order reversed', '(ad,min_cpu)', '(min_cpu,ad)'),
        ],
        'onek_ara': [
            ('exclude limit lower', '1<=limit', '1<limit'),
            ('exclude limit upper', 'limit<=20', 'limit<20'),
            ('accept 21 limit', 'limit<=20', 'limit<=21'),
            ('bool accepted as limit', 'type(limit) is not int', 'not isinstance(limit,int)'),
            ('percent wildcard unescaped', ".replace('%','\\\\%')", ''),
            ('underscore wildcard unescaped', ".replace('_','\\\\_')", ''),
            ('backslash not escaped', ".replace('\\\\','\\\\\\\\')", ''),
            ('substring rather than prefix', "(pattern,limit)", "('%'+pattern,limit)"),
            ('constant limit', '(pattern,limit)', '(pattern,20)'),
            ('reverse id order', 'ORDER BY id LIMIT', 'ORDER BY id DESC LIMIT'),
        ],
    }
    records = []
    for function, changes in cases.items():
        step = next(s for s in steps if s['kind'] == 'gorev' and f'def {function}(' in s.get('solution',''))
        runner = for_step(get('sql'), step)
        assert runner.test(step['solution'], step)['status'] == 'pass'
        for label, old, new in changes:
            assert old in step['solution'], (function, label, old)
            code = step['solution'].replace(old, new)
            compile(code, '<binding-mutant>', 'exec')
            r = runner.test(code, step)
            assert r['status'] == 'fail', (function, label, r)
            records.append({'function': function, 'mutation': label, 'status': 'rejected'})
            print(function + ': ' + label + ': rejected', flush=True)
    report = dict(backend='real Python sqlite3.Connection subclass observing actual execute arguments',
                  references_passed=2, mutants_rejected=len(records), mutants_passed=0, cases=records)
    (ROOT / 'outputs/a-notu-sq19-binding-kabul.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__ == '__main__':
    main()
