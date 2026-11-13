"""Run the P74 HTML exercises and semantic mutants in real Kali/Beautiful Soup."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.lessons import Library
from engine.runners import for_step, get


def main():
    steps = Library().lesson('python', 'p74')['steps']
    cases = {
        'form_oku': [
            ('duplicate fields lost', 'return method,target,fields', 'return method,target,list(dict(fields).items())'),
            ('wrong form scope', "form.find_all(['input','select','textarea','button'])", "soup.find_all(['input','select','textarea','button'])"),
            ('ignore disabled', "if not name or control.has_attr('disabled'):continue", 'if not name:continue'),
            ('hidden field lost', "fields.append((name,control.get('value','')))", "\n        if control.get('type')!='hidden':fields.append((name,control.get('value','')))"),
            ('ignore base', "urljoin(base_url,action) if action else belge_url", "urljoin(belge_url,action) if action else belge_url"),
            ('empty action uses base', 'if action else belge_url', 'if action else base_url'),
            ('ignore unsupported controls', "raise ValueError('Kontrol kapsam dışı')", 'continue'),
            ('ignore form association', "raise ValueError('İlişkilendirme kapsam dışı')", 'continue'),
            ('default POST', "form.get('method','get')", "form.get('method','post')"),
            ('empty value dropped', "fields.append((name,control.get('value','')))", "\n        if control.get('value',''):fields.append((name,control.get('value','')))"),
        ],
        'baglantilar': [
            ('ignore base', "origin=urljoin(belge_url,base['href']) if base else belge_url", 'origin=belge_url'),
            ('no deduplication', 'and url not in seen', ''),
            ('reverse DOM order', 'return result', 'return result[::-1]'),
            ('strip fragments', "url=urljoin(origin,anchor['href'].strip())", "url=urljoin(origin,anchor['href'].strip()).split('#')[0]"),
            ('same host only', 'if parsed.scheme in', "if parsed.hostname=='lab.test' and parsed.scheme in"),
            ('accept non HTTP', "parsed.scheme in ('http','https')", 'True'),
            ('skip empty href', "url=urljoin(origin,anchor['href'].strip())", "\n        if not anchor['href'].strip():continue\n        url=urljoin(origin,anchor['href'].strip())"),
        ],
    }
    records = []
    for function, mutations in cases.items():
        step = next(s for s in steps if s['kind'] == 'gorev' and f'def {function}(' in s.get('solution', ''))
        runner = for_step(get('python'), step)
        result = runner.test(step['solution'], step)
        if result['status'] != 'pass':
            raise AssertionError((function, 'reference solution', result))
        records.append({'function': function, 'case': 'reference', 'status': 'pass'})
        for label, old, new in mutations:
            assert old in step['solution'], (function, label, 'mutation did not apply')
            code = step['solution'].replace(old, new)
            compile(code, '<mutant>', 'exec')
            result = runner.test(code, step)
            if result['status'] != 'fail':
                raise AssertionError((function, label, result))
            records.append({'function': function, 'case': label, 'status': 'rejected'})
            print(f'{function}: {label}: rejected', flush=True)
    report = {'backend': 'real WSL / Beautiful Soup', 'references_passed': 2,
              'mutants_rejected': len(records)-2, 'mutants_passed': 0, 'cases': records}
    target = ROOT / 'outputs/a-notu-p74-html-kabul.json'
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'cases'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
