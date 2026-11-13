"""SG22 re/fieldref ve UTF-16 bayt sırası görevleri: yanlış kurallar gerçek pySigma Splunk backend + Splunk'ta reddedilmeli."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.lessons import Library  # noqa: E402
from engine.runners import for_step, get  # noqa: E402

CASES = {
    '3 ·': [
        ('kısa yük kabul', '{16,}', '{8,}'),
        ('tek boşluk', r'enc\s+', r'enc\s'),
        ('baştaki boşluk yok', r"re: '\s[-/–]", "re: '[-/–]"),
        ('en dash yok', '[-/–]', '[-/]'),
        ('aynı kullanıcı aranır', 'sel and not ayni', 'sel and ayni'),
        ('kullanıcı koşulu yok', 'condition: sel and not ayni', 'condition: sel'),
        ('base64 karakter sınıfı dar', '[A-Za-z0-9+/=]', '[A-Za-z0-9]'),
    ],
    '4 ·': [
        ('yalnız LE', 'condition: sel and (le or be)', 'condition: sel and le'),
        ('yalnız BE', 'condition: sel and (le or be)', 'condition: sel and be'),
        ('BOM eklenen utf16', 'CommandLine|wide|', 'CommandLine|utf16|'),
        ('konuma bağlı base64', 'CommandLine|wide|base64offset', 'CommandLine|wide|base64'),
        ('kodlama yok', 'CommandLine|utf16be|base64offset', 'CommandLine|base64offset'),
        ('yanlış araç', "'\\cfgtool.exe'", "'\\powershell.exe'"),
    ],
}


def main():
    lib = Library()
    kayit = []
    for bas, mutasyonlar in CASES.items():
        st = next(s for s in lib.lesson('sigma', 'sg22')['steps'] if s['kind'] == 'gorev' and s['title'].startswith(bas))
        runner = for_step(get('sigma'), st)
        assert runner.test(st['solution'], st)['status'] == 'pass', bas
        for ad, eski, yeni in mutasyonlar:
            assert eski in st['solution'], (bas, ad)
            r = runner.test(st['solution'].replace(eski, yeni, 1), st)
            assert r['status'] in ('fail', 'error'), (bas, ad, r)
            kayit.append(dict(gorev=st['title'], mutasyon=ad, durum='reddedildi', runner_status=r['status']))
            print('sg22 ' + bas + ' ' + ad + ': reddedildi', flush=True)
    (ROOT / 'outputs/a-notu-sg22-modifier-kabul.json').write_text(json.dumps(dict(
        ders='sg22', motor='pySigma 1.5.1 + Splunk backend 2.1.0 + Splunk Enterprise 10.6.1', referans='geçti',
        mutant_reddedilen=len(kayit), mutant_gecen=0, mutasyonlar=kayit,
        olcum='utf16le bu pySigma sürümünde bilinmeyen değiştirici; fieldref Splunk where ile harfe duyarlı.'),
        ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(f'{len(kayit)} mutant reddedildi, 0 geçen')


if __name__ == '__main__':
    main()
