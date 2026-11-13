"""SG19 sigma-cli görevleri: yanlış komutlar gerçek sigma-cli 3.1.0 + Splunk'ta reddedilmeli."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.lessons import Library  # noqa: E402
from engine.runners import for_step, get  # noqa: E402

CASES = {
    'Kural klasörünü': [
        ('hazır sysmon pipeline', '-p kurum-edr.yml', '-p sysmon'),
        ('atlama yok: yer tutucu işi durdurur', ' -s ', ' '),
        ('pipeline yok', '-p kurum-edr.yml ', '--without-pipeline '),
        ('yalnız ilk kural', 'kurallar', 'kurallar/a_ofis_powershell.yml'),
        ('yalnız son kural', 'kurallar', 'kurallar/c_ofis_cmd.yml'),
        ('Splunk Windows pipeline', '-p kurum-edr.yml', '-p splunk_windows'),
        ('başka hedef', '-t splunk', '-t splunk_spl2'),
    ],
    'CIM veri modeline': [
        ('biçim yok: ham SPL', ' -f data_model', ''),
        ('düz biçim', '-f data_model', '-f default'),
        ('CIM pipeline yok', '-p splunk_cim', '-p sysmon'),
        ('pipeline yok', '-p splunk_cim', '--without-pipeline'),
        ('savedsearches biçimi', '-f data_model', '-f savedsearches'),
    ],
}


def main():
    lib = Library()
    kayit = []
    for baslik, mutasyonlar in CASES.items():
        st = next(s for s in lib.lesson('sigma', 'sg19')['steps'] if s['kind'] == 'gorev' and baslik in s['title'])
        runner = for_step(get('sigma'), st)
        assert runner.name == 'sigma-splunk'
        r = runner.test(st['solution'], st)
        assert r['status'] == 'pass', (baslik, r)
        for ad, eski, yeni in mutasyonlar:
            assert eski in st['solution'], (baslik, ad)
            r = runner.test(st['solution'].replace(eski, yeni, 1), st)
            assert r['status'] in ('fail', 'error'), (baslik, ad, r)
            kayit.append(dict(gorev=baslik, mutasyon=ad, durum='reddedildi', runner_status=r['status'],
                              hata=(r.get('error') or {}).get('msg', '')[:200]))
            print('sg19 ' + baslik + ': ' + ad + ': reddedildi', flush=True)
    rapor = dict(ders='sg19', motor='sigma-cli 3.1.0 (pySigma 1.5.1, Splunk backend 2.1.0) + Splunk Enterprise 10.6.1 + CIM 8.5.0',
                 referans='geçti', mutant_reddedilen=len(kayit), mutant_gecen=0, mutasyonlar=kayit)
    (ROOT / 'outputs/a-notu-sg19-cli-kabul.json').write_text(json.dumps(rapor, ensure_ascii=False, indent=2) + '\n',
                                                            encoding='utf-8', newline='\n')
    print(f'{len(kayit)} mutant reddedildi, 0 geçen')


if __name__ == '__main__':
    main()
