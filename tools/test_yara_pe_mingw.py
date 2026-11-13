"""YR19 gerçek MinGW PE görevi: yanlış kurallar gerçek libyara + gerçek MinGW-w64 çıktısında reddedilmeli."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.lessons import Library  # noqa: E402
from engine.runners import for_step, get  # noqa: E402

MUTASYON = [
    ('64 bit makine denetimi yok', ' and pe.machine == pe.MACHINE_AMD64', ''),
    ('DLL biti denetimi yok', '\n        and pe.is_dll() and', '\n        and'),
    ('PE32 denetimi yok', ' pe.is_32bit() and', ''),
    ('32 bit makine denetimi yok', ' and pe.machine == pe.MACHINE_I386', ''),
    ('program/DLL ayrımı yok', ' and not pe.is_dll()', ''),
    ('export denetimi yok', ' and pe.exports("pafta_topla")', ''),
    ('mimari ters', 'pe.is_64bit() and pe.machine == pe.MACHINE_AMD64', 'pe.is_32bit() and pe.machine == pe.MACHINE_I386'),
]
ESDEGER = [
    ('PE32+ denetimi yok: Magic PE32 yapılınca veri dizinleri kayar, export zaten bulunmaz', ' pe.is_64bit() and', ''),
    ('pe.is_pe yok: PE olmayan veride modül alanları tanımsız', 'condition: pe.is_pe and pe.is_64bit()', 'condition: pe.is_64bit()'),
]


def main():
    st = next(s for s in Library().lesson('yara', 'yr19')['steps'] if s['kind'] == 'gorev' and s['title'].startswith('Gerçek MinGW'))
    runner = for_step(get('yara'), st)
    assert runner.test(st['solution'], st)['status'] == 'pass'
    kayit, esdeger = [], []
    for ad, eski, yeni in MUTASYON:
        assert eski in st['solution'], ad
        r = runner.test(st['solution'].replace(eski, yeni, 1), st)
        assert r['status'] in ('fail', 'error'), (ad, r)
        kayit.append(dict(mutasyon=ad, durum='reddedildi'))
        print('yr19 mingw: ' + ad + ': reddedildi', flush=True)
    for ad, eski, yeni in ESDEGER:
        esdeger.append(dict(mutasyon=ad, runner_status=runner.test(st['solution'].replace(eski, yeni, 1), st)['status']))
        print('yr19 mingw: ' + ad + ': ' + esdeger[-1]['runner_status'] + ' (eşdeğer)', flush=True)
    (ROOT / 'outputs/a-notu-yr19-mingw-kabul.json').write_text(json.dumps(dict(
        ders='yr19', gorev=st['title'], derleyici='Kali WSL i686/x86_64-w64-mingw32-gcc (ctypes_lab)', tarayici='yara-python 4.5.4',
        referans='geçti', mutant_reddedilen=len(kayit), mutant_gecen=0, mutasyonlar=kayit, esdeger=esdeger),
        ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(f'{len(kayit)} mutant reddedildi, 0 geçen; {len(esdeger)} eşdeğer ayrı raporlandı')


if __name__ == '__main__':
    main()
