"""Read-only lesson registration, runner and local audit-evidence path checks."""
import ast
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from engine.lessons import Library
from engine.runners import get,for_step


def inspect():
    lib=Library();errors=[];counts={};orphans=[]
    for tid in lib.track_ids():
        track=lib.track(tid)
        ids=[lid for module in track['modules'] for lid in module['lessons']]
        counts[tid]=len(ids)
        if len(ids)!=len(set(ids)):errors.append(f'{tid}: yinelenen ders kaydı')
        files=set()
        for lid in ids:
            try:
                lesson=lib.lesson(tid,lid)
                for n,st in enumerate(lesson['steps']):
                    if st['kind']=='gorev':for_step(get(track.get('runner',tid)),st)
                files.add(lid)
            except Exception as e:errors.append(f'{tid}/{lid}: {type(e).__name__}: {e}')
        for p in (ROOT/'tracks'/tid/'lessons').glob('*.md'):
            # Front matter is parsed without executing lesson contents.
            source=p.read_text(encoding='utf-8-sig')
            first=source.split('---',2)
            lid=next((s.partition(':')[2].strip() for s in first[1].splitlines() if s.startswith('id:')),None) if len(first)>2 else None
            if lid and lid not in files:orphans.append(p.relative_to(ROOT).as_posix())
    panel=json.loads((ROOT/'docs/denetim/puanlar.json').read_text(encoding='utf-8'))
    seen=[]
    def links(value):
        if isinstance(value,dict):
            for child in value.values():links(child)
        elif isinstance(value,list):
            for child in value:links(child)
        elif isinstance(value,str) and value.startswith('../../outputs/'):
            seen.append(value)
            if not (ROOT/'docs/denetim'/value).is_file():errors.append('Panel kanıtı bulunamadı: '+value)
    links(panel)
    for file in ('kur.py','engine/senkron.py'):
        p=ROOT/file
        if not p.is_file():continue
        for node in ast.walk(ast.parse(p.read_text(encoding='utf-8-sig'))):
            if isinstance(node,ast.Constant) and isinstance(node.value,str) and node.value.startswith(('tools/','requirements-')):
                if not (ROOT/node.value).is_file():errors.append(file+': bulunamayan referans '+node.value)
    below=[dict(no=m['no'],puan=sum(m.get('puan',{}).values())) for m in panel['maddeler']
           if not m.get('puan') or sum(m['puan'].values())<90]
    return dict(root=str(ROOT),tracks=counts,lessons=sum(counts.values()),panel_items=len(panel['maddeler']),
                a_count=len(panel['maddeler'])-len(below),below_a=below,
                evidence_links_checked=len(seen),orphan_lessons=orphans,errors=errors,
                scope='Registration/import/path checks only; does not execute all lessons or verify grading quality.')


if __name__=='__main__':
    report=inspect()
    print(json.dumps(report,ensure_ascii=False,indent=2))
    raise SystemExit(1 if report['errors'] else 0)
