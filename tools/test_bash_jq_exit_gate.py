"""BS29: real jq prediction and inclusive-boundary mutation acceptance."""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from engine.lessons import Library
from engine.runners import for_step,get


def main():
    steps=Library().lesson('bash','bs29')['steps']
    prediction=[s for s in steps if s['kind']=='tahmin'][-1]
    result=for_step(get('bash'),prediction).run(prediction['code'],prediction.get('stdin',''),prediction.get('setup'))
    assert result['status']=='ok',result
    stdout=''.join(text for kind,text in result['segs'] if kind=='out')
    assert stdout=='0\n1\n1\n0\n4\n0\n',result
    step=next(s for s in steps if s['kind']=='gorev' and 'jq -e -s' in s.get('solution',''))
    runner=for_step(get('bash'),step)
    result=runner.test(step['solution'],step)
    assert result['status']=='pass',result
    mutations=[
        ('without exit-status','jq -e -s','jq -s'),
        ('without slurp','jq -e -s','jq -e'),
        ('exclusive zero','. >= 0','. > 0'),
        ('exclusive ten','. <= 10','. < 10'),
        ('allow eleven','. <= 10','. <= 11'),
        ('allow minus one','. >= 0','. >= -1'),
        ('allow multiple documents','length == 1','length >= 1'),
        ('ignore readiness','.hazir == true','true'),
        ('coerce boolean string','.hazir == true','(.hazir | tostring) == "true"'),
        ('ignore JSON error','*) echo BOZUK','*) echo HAZIR_DEGIL'),
    ]
    records=[]
    for label,old,new in mutations:
        assert old in step['solution'],label
        result=runner.test(step['solution'].replace(old,new),step)
        assert result['status']=='fail',(label,result)
        records.append({'mutation':label,'status':'rejected'})
        print(label+': rejected',flush=True)
    report={'backend':'real Kali Bash/jq','prediction_stdout':stdout,'reference_passed':True,
            'mutants_rejected':len(records),'mutants_passed':0,'cases':records}
    (ROOT/'outputs/a-notu-bs29-jq-kabul.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('prediction verified; 10 mutants rejected; 0 mutants passed')


if __name__=='__main__':main()
