"""SG20 temporal korelasyon görevi: yanlış korelasyonlar gerçek pySigma Splunk backend + Splunk'ta reddedilmeli."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.lessons import Library  # noqa: E402
from engine.runners import for_step, get  # noqa: E402

MUTASYON = [
    ('pencere 10 dk: kutu sınırı kayar', 'timespan: 5m', 'timespan: 10m'),
    ('pencere 2 dk', 'timespan: 5m', 'timespan: 2m'),
    ('grup anahtarı yok', '  group-by: [TargetUserName]\n', ''),
    ('cihaza göre grupla', 'group-by: [TargetUserName]', 'group-by: [Computer]'),
    ('tek kurala başvuru', 'rules: [basarisiz, basarili]', 'rules: [basarisiz]'),
    ('başarılı kural yanlış olay', 'sel: {EventID: 4624}', 'sel: {EventID: 4672}'),
    ('iki kural da başarısız', 'sel: {EventID: 4624}', 'sel: {EventID: 4625}'),
    ('sayım korelasyonu', 'type: temporal', 'type: event_count'),
]


def main():
    st = next(s for s in Library().lesson('sigma', 'sg20')['steps'] if s['kind'] == 'gorev' and s['title'].startswith('3 ·'))
    runner = for_step(get('sigma'), st)
    assert runner.test(st['solution'], st)['status'] == 'pass'
    kayit = []
    for ad, eski, yeni in MUTASYON:
        assert eski in st['solution'], ad
        r = runner.test(st['solution'].replace(eski, yeni, 1), st)
        assert r['status'] in ('fail', 'error'), (ad, r)
        kayit.append(dict(mutasyon=ad, durum='reddedildi', runner_status=r['status']))
        print('sg20 temporal: ' + ad + ': reddedildi', flush=True)
    (ROOT / 'outputs/a-notu-sg20-temporal-kabul.json').write_text(json.dumps(dict(
        ders='sg20', gorev=st['title'], motor='pySigma 1.5.1 + Splunk backend 2.1.0 + Splunk Enterprise 10.6.1',
        referans='geçti', mutant_reddedilen=len(kayit), mutant_gecen=0, mutasyonlar=kayit,
        acik='temporal_ordered bu backend sürümünde desteklenmiyor; görev bunu çeviri hatasıyla ölçer.'),
        ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(f'{len(kayit)} mutant reddedildi, 0 geçen')


if __name__ == '__main__':
    main()
