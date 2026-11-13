"""BS35 batch transfer acceptance against real local OpenSSH/SFTP."""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from engine.lessons import Library
from engine.runners import for_step,get


def main():
    step=next(s for s in Library().lesson('bash','bs35')['steps']
              if s['kind']=='gorev' and 'sftp -q -F ayar -b' in s.get('solution',''))
    runner=for_step(get('bash'),step)
    result=runner.test(step['solution'],step)
    assert result['status']=='pass',result
    mutations=[
        ('ignore content mismatch','if ! cmp -s -- "$yerel" geri.bin; then','if false; then'),
        ('missing source is transfer error','echo HATA\n    exit 2','echo AKTARIM_HATA\n    exit 1'),
        ('transfer errors exit zero','echo AKTARIM_HATA\n    exit 1','echo AKTARIM_HATA\n    exit 0'),
        ('mismatch exits zero','echo UYUSMAZLIK\n    exit 1','echo UYUSMAZLIK\n    exit 0'),
        ('fixed remote directory','$PWD/$uzak/sonuc.bin','$PWD/uzak klasor/sonuc.bin'),
        ('fixed source','$PWD/$yerel','$PWD/kaynak dosya.bin'),
        ('lost batch path quoting','put "%s" "%s"','put %s %s'),
        ('ignore batch failure','if ! printf','if printf'),
    ]
    records=[]
    for label,old,new in mutations:
        assert old in step['solution'],label
        result=runner.test(step['solution'].replace(old,new),step)
        rejected=result['status']=='fail' or (result['status']=='error' and (result.get('error') or {}).get('type')=='ÇıkışKodu')
        assert rejected,(label,result)
        records.append({'mutation':label,'status':'rejected','runner_status':result['status']})
        print(label+': rejected',flush=True)
    report={'backend':'real Kali OpenSSH sshd -i / internal-sftp',
            'references_passed':1,'mutants_rejected':len(records),'mutants_passed':0,'cases':records}
    (ROOT/'outputs/a-notu-bs35-sftp-kabul.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('1 reference passed; 8 mutants rejected; 0 mutants passed')


if __name__=='__main__':main()
