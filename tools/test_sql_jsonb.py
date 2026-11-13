"""SQ20 native PostgreSQL jsonb semantic regression cases."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.lessons import Library
from engine.runners import for_step, get


def main():
    steps = [s for s in Library().lesson('sql','sq20')['steps']
             if s['kind']=='gorev' and s.get('meta',{}).get('motor')=='postgres']
    changes = [
        [('SQL NULL misclassified', "WHEN kayit IS NULL THEN 'kayit yok'", "WHEN FALSE THEN 'kayit yok'"),
         ('object guard lost', "WHEN jsonb_typeof(kayit) <> 'object'", 'WHEN FALSE'),
         ('object guard reversed', "<> 'object'", "= 'object'"),
         ('missing key treated as null', "WHEN NOT (kayit ? 'kullanici') THEN 'alan yok'", "WHEN NOT (kayit ? 'kullanici') THEN 'json null'"),
         ('JSON null treated as missing', "THEN 'json null'", "THEN 'alan yok'"),
         ('wrong nested scope', "kayit ? 'kullanici'", "kayit->'meta' ? 'kullanici'"),
         ('order reversed', 'ORDER BY id', 'ORDER BY id DESC')],
        [('wrong root type filter', "'{\"tur\":\"giris_hata\"}'", "'{\"tur\":\"normal\"}'"),
         ('case-insensitive labels', "e.etiket IN", "lower(e.etiket) IN"),
         ('skip second allowed label', "('auth','basarisiz')", "('auth')"),
         ('zero-based positions', 'o.id,e.sira,e.etiket', 'o.id,e.sira-1 AS sira,e.etiket'),
         ('reverse positions', 'ORDER BY o.id,e.sira', 'ORDER BY o.id,e.sira DESC'),
         ('only first matching entry', 'ORDER BY o.id,e.sira;', 'ORDER BY o.id,e.sira LIMIT 1;'),
         ('scalar treated as array', "jsonb_typeof(o.kayit->'etiketler')='array'", "o.kayit ? 'etiketler'"),
         ('array guard reversed', "='array'", "<>'array'")],
    ]
    records=[]
    for st, mutants in zip(steps,changes):
        runner=for_step(get('sql'),st)
        assert runner.test(st['solution'],st)['status']=='pass'
        for label,old,new in mutants:
            assert old in st['solution'], label
            r=runner.test(st['solution'].replace(old,new),st)
            assert r['status'] in ('fail','error'),(label,r)
            if r['status']=='error':
                assert (r.get('error') or {}).get('type') not in ('PostgreSQLYok','PostgreSQLKapalı'),r
            records.append(dict(mutation=label,status='rejected',runner_status=r['status']))
            print(label+': rejected',flush=True)
    report=dict(backend='real Kali WSL PostgreSQL jsonb',references_passed=2,mutants_rejected=len(records),mutants_passed=0,cases=records)
    (ROOT/'outputs/a-notu-sq20-jsonb-kabul.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
