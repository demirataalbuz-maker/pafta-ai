"""Recheck the two closed P75 findings using real Kali pip/venv/wheels."""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from engine.lessons import Library
from engine.runners import for_step,get


def main():
    steps=Library().lesson('python','p75')['steps']
    specifications=[
        ('offline command',
         lambda s:'istek = input().strip()' in s and '"--find-links"' in s,
         [('missing --no-index','"--no-index", ', '')]),
        ('dependency backtracking',lambda s:'def surum(metin):' in s,
         [('lexical version ordering','tuple(int(p) for p in metin.split("."))','metin'),
          ('inverted downgrade comparison','surum(kurulu[ad]) < surum(en_yuksek[ad])','surum(kurulu[ad]) > surum(en_yuksek[ad])')]),
    ]
    records=[]
    for label,select,mutations in specifications:
        step=next(s for s in steps if s['kind']=='gorev' and select(s.get('solution','')))
        runner=for_step(get('python'),step)
        result=runner.test(step['solution'],step)
        assert result['status']=='pass',(label,'reference',result)
        print(label+': reference passed',flush=True)
        for name,old,new in mutations:
            assert old in step['solution'],name
            result=runner.test(step['solution'].replace(old,new),step)
            assert result['status']=='fail',(name,result)
            records.append({'mutation':name,'status':'rejected'})
            print(name+': rejected',flush=True)
    report={'backend':'real Kali Python / pip / venv / local wheels',
            'references_passed':2,'mutants_rejected':3,'mutants_passed':0,'cases':records,
            'scope':'Targeted non-equivalent regressions, not an exhaustive mutation score.'}
    (ROOT/'outputs/a-notu-p75-venv-kabul.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
