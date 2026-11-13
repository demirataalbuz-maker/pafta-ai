"""SG19 Kusto/EQL hedef görevi: yanlış sigma-cli komutları gerçek Kusto Emulator + Elasticsearch'te reddedilmeli."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.lessons import Library  # noqa: E402
from engine.runners import for_step, get  # noqa: E402

MUTASYON = [
    ('Kusto pipeline yok: tablo yok', '-t kusto -p microsoft_xdr', '-t kusto'),
    ('Kusto ASIM tablosu: çalışma alanında tanımlı değil', '-p microsoft_xdr', '-p sentinel_asim'),
    ('EQL pipeline yok', '-t eql -p ecs_windows', '-t eql'),
    ('EQL Sysmon alanları: ECS indeksinde yok', '-p ecs_windows', '-p sysmon'),
    ('yalnız Kusto', '\nsigma convert -t eql -p ecs_windows kurallar/ofis_powershell.yml', ''),
    ('yalnız EQL', 'sigma convert -t kusto -p microsoft_xdr kurallar/ofis_powershell.yml\n', ''),
    ('desteklenmeyen hedef', '-t eql', '-t esql'),
    ('Splunk hedefi bu görevde değil', '-t kusto -p microsoft_xdr', '-t splunk -p sysmon'),
]


def main():
    st = next(s for s in Library().lesson('sigma', 'sg19')['steps'] if s['kind'] == 'gorev' and s['title'].startswith('4 ·'))
    runner = for_step(get('sigma'), st)
    assert runner.name == 'sigma-hedef'
    assert runner.test(st['solution'], st)['status'] == 'pass'
    kayit = []
    for ad, eski, yeni in MUTASYON:
        assert eski in st['solution'], ad
        r = runner.test(st['solution'].replace(eski, yeni, 1), st)
        assert r['status'] in ('fail', 'error'), (ad, r)
        kayit.append(dict(mutasyon=ad, durum='reddedildi', runner_status=r['status'],
                          hata=(r.get('error') or {}).get('msg', '')[:200]))
        print('sg19 hedef: ' + ad + ': reddedildi', flush=True)
    (ROOT / 'outputs/a-notu-sg19-hedef-kabul.json').write_text(json.dumps(dict(
        ders='sg19', gorev=st['title'],
        araclar='sigma-cli 3.1.0, pySigma 1.5.1, pysigma-backend-kusto 1.0.1, pysigma-backend-elasticsearch 2.1.1',
        hedefler='Microsoft Kusto Emulator (gerçek sorgu motoru) ve Elasticsearch 9.5.5 _eql API',
        referans='geçti', mutant_reddedilen=len(kayit), mutant_gecen=0, mutasyonlar=kayit,
        acik='Defender/Sentinel servisi değil; DeviceProcessEvents ders verisidir.'),
        ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(f'{len(kayit)} mutant reddedildi, 0 geçen')


if __name__ == '__main__':
    main()
