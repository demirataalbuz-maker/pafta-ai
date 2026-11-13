"""SG21 gerçek EVTX/XML normalleştirme görevi: yanlış normalleştiriciler reddedilmeli (Windows XML + gerçek Splunk)."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.lessons import Library  # noqa: E402
from engine.runners import for_step, get  # noqa: E402

MUTASYON = [
    ('boş Data atlanır: alanlar kayar', '[d.text or "" for d in', '[d.text for d in'),
    ('boş Data None kalır', 'd.text or ""', 'd.text'),
    ('EventID adı kalır', '{"EventCode":', '{"EventID":'),
    ('EventCode metin', 'int(sistem.find("e:EventID", NS).text)', 'sistem.find("e:EventID", NS).text'),
    ('zaman öğe metninden', '.get("SystemTime")', '.text'),
    ('alan sırası bir kayık', 'zip(ALANLAR_4688, degerler)', 'zip(ALANLAR_4688[1:], degerler)'),
    ('ters olay sırası', 'olaylar.append(o)', 'olaylar.insert(0, o)'),
    ('Computer yok', ',\n             "Computer": sistem.find("e:Computer", NS).text}', '}'),
]


def main():
    st = next(s for s in Library().lesson('sigma', 'sg21')['steps'] if s['kind'] == 'gorev' and s['title'].startswith('3 ·'))
    runner = for_step(get('sigma'), st)
    assert runner.test(st['solution'], st)['status'] == 'pass'
    kayit = []
    for ad, eski, yeni in MUTASYON:
        assert eski in st['solution'], ad
        r = runner.test(st['solution'].replace(eski, yeni, 1), st)
        assert r['status'] in ('fail', 'error'), (ad, r)
        kayit.append(dict(mutasyon=ad, durum='reddedildi', runner_status=r['status']))
        print('sg21 evtx: ' + ad + ': reddedildi', flush=True)
    (ROOT / 'outputs/a-notu-sg21-evtx-kabul.json').write_text(json.dumps(dict(
        ders='sg21', gorev=st['title'], kaynak='ps_evtx_fixtures: EVT → wevtutil epl → gerçek EVTX → wevtutil qe /f:xml',
        hedef='pySigma 1.5.1 windows-audit + splunk_windows → gerçek Splunk Enterprise 10.6.1',
        referans='geçti', mutant_reddedilen=len(kayit), mutant_gecen=0, mutasyonlar=kayit,
        acik='EVT kaynaklı kayıt sürüm 0 ve adsız Data; modern Name öznitelikli 4688 biçimi bu görevde sınanmaz.'),
        ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(f'{len(kayit)} mutant reddedildi, 0 geçen')


if __name__ == '__main__':
    main()
