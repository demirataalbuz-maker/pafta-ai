"""SP23 Authentication ve Endpoint.Processes görevleri: yanlış bilgi nesneleri gerçek Splunk + CIM 8.5.0'da reddedilmeli."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.lessons import Library  # noqa: E402
from engine.runners import for_step, get  # noqa: E402

CASES = {
    'Authentication modeline': [
        ('etiket yanlış model', 'authentication = enabled', 'web = enabled'),
        ('olay türü süzgeci yok: heartbeat modele girer', 'search = sourcetype=pafta_cim_auth tur=auth', 'search = sourcetype=pafta_cim_auth'),
        ('action normalize edilmedi', 'EVAL-action = case(sonuc="ok","success",sonuc="fail","failure",true(),"unknown")\n', ''),
        ('ok/fail ters', 'sonuc="ok","success",sonuc="fail","failure"', 'sonuc="ok","failure",sonuc="fail","success"'),
        ('bilinmeyen sonuç failure sayılır', 'true(),"unknown"', 'true(),"failure"'),
        ('src alias yok', ' kaynak AS src', ''),
        ('user alias yok', 'hesap AS user ', ''),
        ('hesap küçük harfe çevrildi', 'FIELDALIAS-cim = hesap AS user kaynak AS src hedef AS dest uygulama AS app',
         'FIELDALIAS-cim = kaynak AS src hedef AS dest uygulama AS app\nEVAL-user = lower(hesap)'),
    ],
    'Endpoint.Processes': [
        ('report etiketi yok', '\nreport = enabled', ''),
        ('process etiketi yok', 'process = enabled\n', ''),
        ('çocuk/ebeveyn ters', 'cocuk AS process_name ebeveyn AS parent_process_name', 'cocuk AS parent_process_name ebeveyn AS process_name'),
        ('olay türü süzgeci yok: service modele girer', 'search = sourcetype=pafta_cim_endpoint tur=process', 'search = sourcetype=pafta_cim_endpoint'),
        ('process_id alias yok', ' pid AS process_id', ''),
        ('user alias yok', ' hesap AS user', ''),
    ],
}


def main():
    lib = Library()
    kayit = []
    for baslik, mutasyonlar in CASES.items():
        st = next(s for s in lib.lesson('spl', 'sp23')['steps'] if s['kind'] == 'gorev' and baslik in s['title'])
        runner = for_step(get('spl'), st)
        assert runner.name == 'spl-splunk'
        r = runner.test(st['solution'], st)
        assert r['status'] == 'pass', (baslik, r)
        for ad, eski, yeni in mutasyonlar:
            assert eski in st['solution'], (baslik, ad)
            r = runner.test(st['solution'].replace(eski, yeni, 1), st)
            assert r['status'] in ('fail', 'error'), (baslik, ad, r)
            kayit.append(dict(gorev=baslik, mutasyon=ad, durum='reddedildi', runner_status=r['status']))
            print('sp23 ' + baslik + ': ' + ad + ': reddedildi', flush=True)
    rapor = dict(ders='sp23', motor='Splunk Enterprise 10.6.1 (Docker) + Splunk_SA_CIM 8.5.0', referans='geçti',
                 mutant_reddedilen=len(kayit), mutant_gecen=0, mutasyonlar=kayit,
                 acik='CIM arşivi Splunkbase hesabıyla elle edinilir; tools/splunk_cim_kur.py yalnız mevcut arşivi doğrular/kurar.')
    (ROOT / 'outputs/a-notu-sp23-cim-kabul.json').write_text(json.dumps(rapor, ensure_ascii=False, indent=2) + '\n',
                                                            encoding='utf-8', newline='\n')
    print(f'{len(kayit)} mutant reddedildi, 0 geçen')


if __name__ == '__main__':
    main()
