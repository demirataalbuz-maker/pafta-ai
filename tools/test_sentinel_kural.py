"""KQ22 kural kaynağı görevi: yanlış ARM kuralları gerçek Kusto benzetiminde reddedilmeli.

Her mutasyon öğrencinin gerçekten yapabileceği bir hatadır; davranışı değiştirmeyen iki eşdeğer
(GreaterThan 0 ↔ NotEqual 0, son deneme ↔ ilk deneme TimeGenerated) ayrı raporlanır, sıfır diye sunulmaz.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.lessons import Library  # noqa: E402
from engine.runners import for_step, get  # noqa: E402
from sandbox import kusto_lab, sentinel_kural_lab as S  # noqa: E402

UPN = 'by UserPrincipalName, IPAddress'
MUTASYON = [
    ('geriye bakış 20 dk: geç kayıt ikinci pencerede yakalanır, alarm kayar', '"queryPeriod": "PT10M"', '"queryPeriod": "PT20M"'),
    ('sıklık 5 dk: pencereler örtüşür', '"queryFrequency": "PT10M"', '"queryFrequency": "PT5M"'),
    ('sıklık geriye bakıştan uzun', '"queryFrequency": "PT10M"', '"queryFrequency": "PT15M"'),
    ('tek alarm', '"AlertPerResult"', '"SingleAlert"'),
    ('bastırma kapalı', '"suppressionEnabled": true', '"suppressionEnabled": false'),
    ('bastırma 40 dk', '"PT45M"', '"PT40M"'),
    ('bastırma 24 saati aşar', '"PT45M"', '"P2D"'),
    ('eşik 1', '"triggerThreshold": 0', '"triggerThreshold": 1'),
    ('operatör LessThan', '"GreaterThan"', '"LessThan"'),
    ('operatör enum dışı', '"GreaterThan"', '"GreaterThanOrEqual"'),
    ('yalnız 50126 kodu', 'ResultType != \\"0\\"', 'ResultType == \\"50126\\"'),
    ('başarılı girişler de sayılır', '| where ResultType != \\"0\\" ', ''),
    ('yalnız hesap başına', UPN, 'by UserPrincipalName | extend IPAddress = \\"\\"'),
    ('eşik > 3', 'Basarisiz >= 3', 'Basarisiz > 3'),
    ('eşik >= 2', 'Basarisiz >= 3', 'Basarisiz >= 2'),
    ('Name tam UPN', 'AccountName = tostring(split(UserPrincipalName, \\"@\\")[0])', 'AccountName = UserPrincipalName'),
    ('UPN parçaları ters', '\\"@\\")[0])', '\\"@\\")[1])'),
    ('Account yalnız Name', ', {"identifier": "UPNSuffix", "columnName": "AccountUPNSuffix"}', ''),
    ('IP eşlemesi yok', ',\n        {"entityType": "IP", "fieldMappings": [{"identifier": "Address", "columnName": "IPAddress"}]}', ''),
    ('custom detail yok', '"customDetails": {"Basarisiz": "Basarisiz"},', ''),
    ('TimeGenerated çıktıda yok', 'TimeGenerated = max(TimeGenerated), ', ''),
    ('mapping sütunu yazım hatası', '"columnName": "IPAddress"', '"columnName": "IpAddress"'),
    ('özellik adı yazım hatası', '"queryFrequency"', '"queryFrequncy"'),
    ('severity yanlış', '"Medium"', '"High"'),
    ('taktik yok', '"tactics": ["CredentialAccess"],', ''),
    ('kind yanlış', '"kind": "Scheduled"', '"kind": "NRT"'),
    ('union * yasak', 'SigninLogs | where', 'union * | where'),
    ('yayımlanmamış apiVersion', '"apiVersion": "2025-09-01"', '"apiVersion": "2026-09-01"'),
    ('eski apiVersion: laboratuvar şeması 2025-09-01', '"apiVersion": "2025-09-01"', '"apiVersion": "2023-02-01"'),
]
ESDEGER = [
    ('GreaterThan 0 ↔ NotEqual 0: sonuç sayısı negatif olamaz', '"GreaterThan"', '"NotEqual"'),
    ('son deneme ↔ ilk deneme TimeGenerated: alarm benzetimi bu değeri kullanmaz', 'max(TimeGenerated)', 'min(TimeGenerated)'),
    ('$schema yılı: laboratuvar şablon şema adresini doğrulamaz', '2019-04-01/deploymentTemplate', '2020-04-01/deploymentTemplate'),
]


def main():
    kusto_lab.ensure()
    st = next(s for s in Library().lesson('kql', 'kq22')['steps']
              if s['kind'] == 'gorev' and s['title'].startswith('Kuralı kaynak olarak'))
    runner = for_step(get('kql'), st)
    assert runner.name == 'sentinel-kural'
    assert runner.test(st['solution'], st)['status'] == 'pass'
    assert runner.test(st['starter'], st)['status'] != 'pass'
    kayit = []
    for ad, eski, yeni in MUTASYON:
        assert eski in st['solution'], ad
        r = runner.test(st['solution'].replace(eski, yeni, 1), st)
        assert r['status'] in ('fail', 'error'), (ad, r)
        kayit.append(dict(mutasyon=ad, durum='reddedildi', runner_status=r['status']))
        print('kq22 kural: ' + ad + ': reddedildi', flush=True)
    esdeger = []
    for ad, eski, yeni in ESDEGER:
        r = runner.test(st['solution'].replace(eski, yeni, 1), st)
        esdeger.append(dict(mutasyon=ad, runner_status=r['status']))
        print('kq22 kural: ' + ad + ': ' + r['status'] + ' (eşdeğer)', flush=True)
    # Doğrulayıcının kendi sınırları: belgelenmiş uçlar.
    assert S.sure('PT5M').total_seconds() == 300 and S.sure('P14D').days == 14 and S.sure('PT') is None
    assert S.sure('P1DT2H30M').total_seconds() == 95400 and S.sure('10m') is None
    taban = json.loads(st['solution'])['resources'][0]['properties']
    for k, v, beklenen in [('queryFrequency', 'PT4M', False), ('queryPeriod', 'P14D', True), ('queryPeriod', 'P14DT1M', False),
                           ('suppressionDuration', 'PT24H', True), ('suppressionDuration', 'PT24H1M', False),
                           ('triggerThreshold', 10000, True), ('triggerThreshold', 10001, False), ('triggerThreshold', True, False)]:
        hata = S.denetle(dict(taban, **{k: v}))[0]
        assert (not hata) == beklenen, (k, v, hata)
    uzun = dict(taban, query='SigninLogs' + ' ' * 9991)
    assert S.denetle(uzun)[0], 'sorgu 10000 karakteri aşınca reddedilmeli'
    assert not S.denetle(dict(taban, query='SigninLogs' + ' ' * 9990))[0]
    on = dict(taban, entityMappings=[{'entityType': 'IP', 'fieldMappings': [{'identifier': 'Address', 'columnName': 'IPAddress'}]}] * 11)
    assert S.denetle(on)[0], '11 entity eşlemesi reddedilmeli'
    dort = dict(taban, entityMappings=[{'entityType': 'Account', 'fieldMappings': [
        {'identifier': i, 'columnName': 'AccountName'} for i in ('Name', 'UPNSuffix', 'Sid', 'NTDomain')]}])
    assert S.denetle(dort)[0], '4 identifier reddedilmeli'
    rapor = dict(
        ders='kq22', gorev=st['title'], motor='Microsoft Kusto Emulator (gerçek sorgu motoru)', imaj=kusto_lab.IMAGE,
        sema='Microsoft.SecurityInsights alertRules REST 2025-09-01', kaynaklar=[
            'https://learn.microsoft.com/en-us/azure/sentinel/scheduled-rules-overview',
            'https://learn.microsoft.com/en-us/azure/sentinel/create-analytics-rules',
            'https://learn.microsoft.com/en-us/azure/sentinel/ingestion-delay',
            'https://learn.microsoft.com/en-us/azure/sentinel/map-data-fields-to-entities',
            'https://learn.microsoft.com/en-us/azure/sentinel/entities-reference',
            'https://learn.microsoft.com/en-us/rest/api/securityinsights/alert-rules/create-or-update?view=rest-securityinsights-2025-09-01'],
        referans='geçti', baslangic='kaldı', mutant_reddedilen=len(kayit), mutant_gecen=0, mutasyonlar=kayit,
        esdeger=esdeger, sinir_kontrolleri='5 dk/14 gün, 24 saat, eşik 0–10000, 10000 karakter, 10 eşleme, 3 identifier',
        acik='Gerçek Sentinel çalışma alanı yok: portal Test with current data ve Review doğrulaması yapılmadı. '
             'Takvim/eşik/gruplama/bastırma/entity çıkarımı belgelere göre yazılmış yerel modeldir.')
    (ROOT / 'outputs/a-notu-kq22-kural-kabul.json').write_text(json.dumps(rapor, ensure_ascii=False, indent=2) + '\n',
                                                              encoding='utf-8', newline='\n')
    print(f'{len(kayit)} mutant reddedildi, 0 geçen; {len(esdeger)} eşdeğer ayrı raporlandı')


if __name__ == '__main__':
    main()
