"""BS30 teardown mutations and real Git Bash / Kali environment inventory."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from engine.lessons import Library
from engine.runners import for_step,get


def environment_inventory():
    script=r'''printf 'kernel=%s\n' "$(uname -s)"
printf 'bash=%s\n' "$BASH_VERSION"
if [[ -r /proc/sys/kernel/osrelease ]]; then
    printf 'linux_release=%s\n' "$(cat /proc/sys/kernel/osrelease)"
else printf 'linux_release=unavailable\n'; fi
for name in shellcheck bats journalctl cygpath; do
    printf '%s=%s\n' "$name" "$(command -v "$name" || true)"
done
if command -v bats >/dev/null; then printf 'bats_version=%s\n' "$(bats --version)"; fi
if command -v shellcheck >/dev/null; then
    printf 'shellcheck_version=%s\n' "$(shellcheck --version | sed -n 's/^version: //p')"
fi
if command -v cygpath >/dev/null; then printf 'windows_tmp=%s\n' "$(cygpath -w /tmp)"; fi
'''
    commands={
        'Git Bash':[r'C:\Program Files\Git\bin\bash.exe','--noprofile','--norc','-c',script],
        'Kali WSL':['wsl.exe','-d',os.environ.get('PAFTA_WSL_DISTRO','kali-linux'),
                    '--exec','bash','--noprofile','--norc','-c',script],
    }
    result={}
    for name,command in commands.items():
        run=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',timeout=30)
        assert run.returncode==0,(name,run.stderr)
        result[name]=dict(line.split('=',1) for line in run.stdout.splitlines() if '=' in line)
    assert result['Kali WSL']['kernel']=='Linux',result
    assert result['Kali WSL']['linux_release']!='unavailable',result
    assert result['Kali WSL']['bats'] and result['Kali WSL']['shellcheck'],result
    assert result['Git Bash']['kernel'].startswith(('MINGW','MSYS')),result
    assert result['Git Bash']['cygpath'],result
    return result


def main():
    inventory=environment_inventory()
    print(json.dumps(inventory,ensure_ascii=False),flush=True)
    step=next(s for s in Library().lesson('bash','bs30')['steps']
              if s['kind']=='gorev' and 'temizlik.bats' in s.get('solution',''))
    runner=for_step(get('bash'),step)
    result=runner.test(step['solution'],step)
    assert result['status']=='pass',result
    mutations=[
        ('no cleanup','rm -rf -- "$ALAN"',':'),
        ('wrong hook name','teardown()','cleanup()'),
        ('remove one file only','rm -rf -- "$ALAN"','rm -f -- "$ALAN/x"'),
        ('reuse one directory','ALAN=$(mktemp -d "$PWD/alan.XXXXXX")','ALAN="$PWD/alan.sabit"; mkdir -p "$ALAN"'),
        ('first test does not fail','    false\n','    true\n'),
        ('second test inverted','[ ! -e "$ALAN/x" ]','[ -e "$ALAN/x" ]'),
        ('fake remaining count','rm -rf -- "$ALAN"',':'),
    ]
    # This mutant reports zero leaks while omitting the real teardown.
    records=[]
    for label,old,new in mutations:
        assert old in step['solution'],label
        code=step['solution'].replace(old,new)
        if label=='fake remaining count':
            code=code.replace('"$kod" "$alan" "$kalan"','"$kod" "$alan" "0"')
        result=runner.test(code,step)
        assert result['status']=='fail',(label,result)
        records.append({'mutation':label,'status':'rejected'})
        print(label+': rejected',flush=True)
    report={'environment_inventory':inventory,'references_passed':1,
            'mutants_rejected':len(records),'mutants_passed':0,'cases':records}
    (ROOT/'outputs/a-notu-bs30-teardown-kabul.json').write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
