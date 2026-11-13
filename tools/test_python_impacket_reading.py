"""Native Kali acceptance for source-option reading and import diagnostics."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.lessons import Library
from engine.runners import for_step, get


def main():
    steps = Library().lesson('python', 'p78')['steps']
    cases = {
        'secenek_kayitlari': [
            ('drop positional', 'result.append((names,', "\n        if not names[0].startswith('-'):continue\n        result.append((names,"),
            ('reverse order', 'return result', 'return result[::-1]'),
            ('lose aliases', 'result.append((names,', 'result.append((names[:1],'),
            ('lose choices', "values.get('choices')", 'None'),
            ('lose false default', "values.get('default')", "values.get('default') or None"),
            ('lose action', "values.get('action','store')", "'store'"),
            ('execute source', 'calls=[node', "exec(kaynak)\n    calls=[node"),
        ],
        'ortam_yokla': [
            ('missing nested dependency misclassified', "'modul-eksik' if own else 'alt-bagimlilik-eksik'", "'modul-eksik'"),
            ('missing parent misclassified', "missing==modul or (missing is not None and modul.startswith(missing+'.'))", 'missing==modul'),
            ('hide other import errors', 'except ModuleNotFoundError as error:', 'except ImportError as error:'),
            ('ignore missing API', 'if not hasattr(loaded,simge):', 'if False:'),
            ('None means absent', 'if not hasattr(loaded,simge):', 'if not getattr(loaded,simge,None):'),
            ('incorrect version', "return ('ok',(version,loaded.__file__))", "return ('ok',('0.0',loaded.__file__))"),
            ('lose metadata distinction', "return ('metadata-eksik',dagitim)", "return ('modul-eksik',dagitim)"),
        ],
    }
    records = []
    for name, mutations in cases.items():
        step = next(s for s in steps if s['kind'] == 'gorev' and f'def {name}(' in s.get('solution', ''))
        runner = for_step(get('python'), step)
        result = runner.test(step['solution'], step)
        if result['status'] != 'pass':
            raise AssertionError((name, 'reference', result))
        for label, old, new in mutations:
            assert old in step['solution'], label
            code = step['solution'].replace(old, new)
            compile(code, '<mutant>', 'exec')
            result = runner.test(code, step)
            if result['status'] != 'fail':
                raise AssertionError((name, label, result))
            records.append({'function': name, 'mutation': label, 'status': 'rejected'})
            print(f'{name}: {label}: rejected', flush=True)
    report = {'backend': 'real Kali / installed Impacket source and imports',
              'references_passed': 2, 'mutants_rejected': len(records), 'mutants_passed': 0, 'cases': records}
    (ROOT/'outputs/a-notu-p78-impacket-kabul.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(f'2 references passed; {len(records)} mutants rejected; 0 mutants passed')


if __name__ == '__main__':
    main()
