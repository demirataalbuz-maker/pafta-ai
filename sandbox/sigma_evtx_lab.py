"""SG21: Windows'un kendi EVTX/XML'i → öğrencinin normalleştiricisi → gerçek pySigma Splunk backend + gerçek Splunk.

ornek() eski EVT kayıtlarını Windows'un wevtutil epl dönüşümüyle gerçek EVTX'e çevirir (sandbox/ps_evtx_fixtures.py)
ve wevtutil qe /f:xml ile Windows'un işlediği XML'i çalışma klasörüne yazar. Canlı günlük okunmaz. Sınır: EVT'den
gelen kayıtta EventData/Data adsızdır ve olay sürümü 0'dır; alanlar 4688 sürüm 2 belgesindeki sırayla gelir.
splunkta(olaylar) öğrencinin sözlüklerini JSON olarak WinEventLog:Security kaynağıyla gerçek Splunk'a yükler,
kuralı windows-audit + splunk_windows pipeline'larıyla gerçek pySigma Splunk backend'inde çevirir ve çalıştırır.
"""
import json
from pathlib import Path
import runpy
import subprocess
import sys

KOK = Path(__file__).resolve().parents[1]
for _y in (str(KOK), str(KOK / '.deps')):
    if _y not in sys.path:
        sys.path.insert(0, _y)

# https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-10/security/threat-protection/auditing/event-4688
ALANLAR_4688 = ('SubjectUserSid', 'SubjectUserName', 'SubjectDomainName', 'SubjectLogonId', 'NewProcessId',
                'NewProcessName', 'TokenElevationType', 'ProcessId', 'CommandLine', 'TargetUserSid', 'TargetUserName',
                'TargetDomainName', 'TargetLogonId', 'ParentProcessName', 'MandatoryLabel')
WPS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
WORD = r'C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE'
EXCEL = r'C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE'
EXPLORER = r'C:\Windows\explorer.exe'


def _surec(no, hesap, yeni, satir, ebeveyn, pid):
    return ['S-1-5-21-3623811015-3361044348-30300820-' + str(1100 + no), hesap, 'PAFTA', '0x4a5a' + str(no),
            pid, yeni, '%%1938', '0x9c4', satir, 'S-1-0-0', '-', '-', '0x0', ebeveyn, 'S-1-16-8192']


# (saniye, alanlar): sıralı tanıklar
OLAYLAR = (
    (5, _surec(1, 'ayse', WPS, 'powershell.exe -nop -w hidden -enc SQBFAFgA', WORD, '0x1a2c')),
    (12, _surec(2, 'berk', WPS, 'powershell.exe -File yedek.ps1', WORD, '0x1a30')),
    (20, _surec(3, 'can', WPS, 'powershell.exe -enc ZQBjAGgAbwA=', EXPLORER, '0x1a34')),
    (31, _surec(4, 'zeynep', WPS.upper(), 'POWERSHELL.EXE -ENC JABhAD0A', EXCEL, '0x1a38')),
    (44, _surec(5, 'mert', WPS, '', WORD, '0x1a3c')),
    (52, _surec(6, 'ece', r'C:\Windows\System32\cmd.exe', 'cmd.exe /c echo a & b <x> -enc', WORD, '0x1a40')),
)
KURAL = r"""title: Office'ten başlatılan kodlanmış PowerShell
id: 5d1a8f2e-7c3b-4e9a-a1d2-0b6c4f8e9a10
status: experimental
logsource: {product: windows, category: process_creation}
detection:
  sel:
    Image|endswith: '\powershell.exe'
    CommandLine|contains: ' -enc '
    ParentImage|endswith: ['\winword.exe', '\excel.exe']
  condition: sel
fields: [Computer, NewProcessId, SubjectUserName]
level: high
"""


def ornek(klasor='.'):
    """guvenlik.evtx ve guvenlik.xml (<Events> kökü altında Windows'un işlediği olaylar) → XML yolu."""
    k = Path(klasor).resolve()
    fx = runpy.run_path(str(KOK / 'sandbox' / 'ps_evtx_fixtures.py'))
    evtx = fx['evtx'](k / 'guvenlik.evtx', [(4688, fx['BILGI'], s, 'Microsoft-Windows-Security-Auditing', a)
                                           for s, a in OLAYLAR])
    exe = Path(fx['os'].environ.get('SystemRoot', r'C:\Windows')) / 'System32' / 'wevtutil.exe'
    p = subprocess.run([str(exe), 'qe', str(evtx), '/lf:true', '/f:xml'], capture_output=True, timeout=20,
                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if p.returncode:
        raise RuntimeError('wevtutil qe başarısız: ' + p.stderr.decode('utf-8', 'replace')[-300:])
    metin = p.stdout.decode('utf-8')
    (k / 'guvenlik.xml').write_text('<Events>' + metin.strip() + '</Events>\n', encoding='utf-8')
    return k / 'guvenlik.xml'


def splunkta(olaylar, kural=KURAL):
    """Normalleştirilmiş olaylar → (spl, sütunlar, satırlar) gerçek Splunk'ta."""
    from sigma.collection import SigmaCollection
    from sigma.backends.splunk import SplunkBackend
    from sigma.pipelines.windows import windows_audit_pipeline
    from sigma.pipelines.splunk import splunk_windows_pipeline
    from sandbox import splunk_lab as S
    if not isinstance(olaylar, list) or not all(isinstance(o, dict) for o in olaylar):
        raise TypeError('normalle() sözlük listesi döndürmeli')
    spl = SplunkBackend(windows_audit_pipeline() + splunk_windows_pipeline()).convert(SigmaCollection.from_yaml(kural))[-1]
    metin = ''.join(json.dumps(o, ensure_ascii=False) + '\n' for o in olaylar)
    with S.Lab() as lab:
        lab.bosalt()
        lab.props('pafta_winsec4688', {'INDEXED_EXTRACTIONS': 'json', 'KV_MODE': 'none', 'TIMESTAMP_FIELDS': 'TimeCreated',
                                       'TIME_FORMAT': '%Y-%m-%dT%H:%M:%S.%7NZ', 'MAX_TIMESTAMP_LOOKAHEAD': '40'})
        lab.yukle(metin, 'pafta_winsec4688', 'WinEventLog:Security')
        alanlar, satirlar = lab.ara(f'search index={S.DIZIN} ' + spl)
    alanlar = [a for a in alanlar if not a.startswith('_')]
    return spl, alanlar, [tuple(r.get(a) for a in alanlar) for r in satirlar]
