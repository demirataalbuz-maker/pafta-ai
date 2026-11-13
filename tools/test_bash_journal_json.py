"""BS31 native journal -> JSON acceptance and semantic mutations."""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from engine.lessons import Library
from engine.runners import for_step,get


def main():
    step=next(s for s in Library().lesson('bash','bs31')['steps']
              if s['kind']=='gorev' and 'json-gorev.journal' in s.get('solution',''))
    runner=for_step(get('bash'),step)
    result=runner.test(step['solution'],step)
    assert result['status']=='pass',result
    mutations=[
        ('exclusive threshold','<= $p','< $p'),
        ('inverted severity','<= $p','>= $p'),
        ('ignore identifier','.SYSLOG_IDENTIFIER == $id and ',''),
        ('missing priority becomes zero','and has("PRIORITY")',''),
        ('string priority in report','oncelik:(.PRIORITY | tonumber)','oncelik:.PRIORITY'),
        ('reverse source order','mesaj:.MESSAGE}]','mesaj:.MESSAGE}] | reverse'),
        ('seconds lose precision','zaman:.__REALTIME_TIMESTAMP','zaman:(.__REALTIME_TIMESTAMP | tonumber / 1000000 | tostring)'),
        ('allow eight','^[0-7]$','^[0-8]$'),
        ('exclude zero','^[0-7]$','^[1-7]$'),
    ]
    records=[]
    for label,old,new in mutations:
        code=step['solution'].replace(old,new)
        assert code!=step['solution'],label
        if label=='missing priority becomes zero':
            code=code.replace('.PRIORITY | tonumber','(.PRIORITY // "0") | tonumber')
        result=runner.test(code,step)
        assert result['status']=='fail',(label,result)
        records.append({'mutation':label,'status':'rejected'})
        print(label+': rejected',flush=True)
    report={'backend':'real Kali journal-remote / journalctl / jq','references_passed':1,
            'mutants_rejected':len(records),'mutants_passed':0,'cases':records}
    (ROOT/'outputs/a-notu-bs31-json-kabul.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('1 reference passed; 9 mutants rejected; 0 mutants passed')


if __name__=='__main__':main()
