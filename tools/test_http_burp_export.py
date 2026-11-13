"""HT17 native Burp exports and deliberately broken export readers."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.lessons import Library
from engine.runners import for_step, get


def main():
    step = next(s for s in Library().lesson('http', 'ht17')['steps']
                if 'def burp_oku(' in s.get('solution', ''))
    runner = for_step(get('http'), step)
    assert runner.test(step['solution'], step)['status'] == 'pass'
    mutations = [
        ('size equal upper excluded', '<=65536', '<65536'),
        ('size extra byte accepted', '<=65536', '<=65537'),
        ('wrong root accepted', "root.tag!='items'", 'False'),
        ('missing version accepted', "not root.get('burpVersion')", 'False'),
        ('unknown item silently skipped', "raise ValueError('Bilinmeyen kayıt')", 'continue'),
        ('duplicate field silently chosen', 'len(nodes)!=1', 'not nodes'),
        ('missing metadata accepted', 'not all(row.values())', 'False'),
        ('status lower equality excluded', '100<=int(status)', '100<int(status)'),
        ('status upper equality excluded', 'int(status)<=599', 'int(status)<599'),
        ('ignore status upper bound', 'int(status)<=599', 'int(status)<=600'),
        ('non base64 flag accepted', "node.get('base64')!='true'", 'False'),
        ('permissive base64 junk', 'validate=True', 'validate=False'),
        ('discard binary HTTP', 'result.append(row)', "row['response']=row['response'].decode('utf-8',errors='replace'); result.append(row)"),
        ('ignore request metadata', "raise ValueError('İstek metadata uyumsuz')", 'pass'),
        ('ignore response metadata', "raise ValueError('Yanıt metadata uyumsuz')", 'pass'),
        ('reverse export order', 'return result', 'return result[::-1]'),
        ('drop repeated exchanges', 'result.append(row)', '\n        if row not in result:result.append(row)'),
        ('no entity restriction', 'if re.search(', 'if False and re.search('),
    ]
    records = []
    for label, old, new in mutations:
        assert old in step['solution'], label
        code = step['solution'].replace(old, new)
        compile(code, '<burp-mutant>', 'exec')
        result = runner.test(code, step)
        assert result['status'] == 'fail', (label, result)
        records.append({'mutation': label, 'status': 'rejected'})
        print(label + ': rejected', flush=True)
    fixtures = ROOT / 'tracks/http/fixtures/ht17_burp'
    provenance = json.loads((fixtures / 'provenance.json').read_text(encoding='utf-8'))
    for name, hashes in provenance['files'].items():
        assert hashlib.sha256((fixtures / name).read_bytes()).hexdigest() == hashes['lf_sha256']
    report = dict(backend='native Burp Community 2026.8 XML + real Python reader',
                  references_passed=1, mutants_rejected=len(records), mutants_passed=0,
                  cases=records, provenance=provenance,
                  limit='Checks archived exports; not proof that each learner clicked the GUI.')
    (ROOT / 'outputs/a-notu-ht17-burp-kabul.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
