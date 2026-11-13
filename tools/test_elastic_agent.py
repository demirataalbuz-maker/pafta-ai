"""EL20 Elastic Agent görevi: yanlış standalone politikaları gerçek ajan + Elasticsearch 9.5.5'te reddedilmeli.

Her mutant ayrı bir gerçek ajan konteyneri koşturur (~35 sn). Sonunda ajan konteyneri, pafta veri akışı
ve etkin laboratuvar anahtarı kalmadığı da doğrulanır.
"""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.lessons import Library  # noqa: E402
from engine.runners import for_step, get  # noqa: E402
from sandbox import elastic_agent_lab as A, elastic_lab as lab  # noqa: E402

MUTASYON = [
    ('bütün dosyalar okunur', '/pafta/girdi/*.ndjson', '/pafta/girdi/*'),
    ('döndürülmüş dosya da okunur', '/pafta/girdi/*.ndjson', '/pafta/girdi/erisim.ndjson*'),
    ('olay zamanı okuma anı', '              overwrite_keys: true\n', ''),
    ('bozuk satır işaretlenmez', '              add_error_key: true\n', ''),
    ('sağlık kontrolü düşmez', '\n        processors:\n          - drop_event:\n              when:\n                equals:\n                  url.path: /saglik', ''),
    ('yanlış alana bakan koşul', 'url.path: /saglik', 'http.request.method: GET'),
    ('alanlar json altına', 'target: ""', 'target: "json"'),
    ('yanlış veri kümesi', 'dataset: pafta.erisim', 'dataset: pafta.web'),
    ('yanlış namespace', 'namespace: lab', 'namespace: default'),
    ('izleme açık', 'agent.monitoring.enabled: false', 'agent.monitoring.enabled: true'),
    ('parola dosyada', "    api_key: '${ELASTICSEARCH_API_KEY}'", '    username: elastic\n    password: changeme'),
    ('anahtar dosyada', "api_key: '${ELASTICSEARCH_API_KEY}'", "api_key: 'id:gizli'"),
    ('eski log girdisi', 'type: filestream', 'type: log'),
]


def main():
    st = next(s for s in Library().lesson('elastic', 'el20')['steps']
              if s['kind'] == 'gorev' and s['title'].startswith('Erişim günlüğünü gerçek ajanla'))
    runner = for_step(get('elastic'), st)
    assert runner.name == 'elastic-agent'
    r = runner.test(st['solution'], st)
    assert r['status'] == 'pass', r
    kayit = []
    for ad, eski, yeni in MUTASYON:
        assert eski in st['solution'], ad
        r = runner.test(st['solution'].replace(eski, yeni, 1), st)
        assert r['status'] in ('fail', 'error'), (ad, r)
        kayit.append(dict(mutasyon=ad, durum='reddedildi', runner_status=r['status']))
        print('el20 ajan: ' + ad + ': reddedildi', flush=True)
    kalan = subprocess.run(['docker', 'ps', '-aq', '--filter', 'label=pafta.lab=elastic-agent'],
                           capture_output=True, text=True).stdout.split()
    assert not kalan, 'ajan konteyneri kaldı: ' + ' '.join(kalan)
    assert lab.api('/_data_stream/logs-pafta.*', missing_ok=True).get('data_streams', []) == []
    assert not lab.api('/_security/api_key?name=pafta-ajan-*&active_only=true').get('api_keys')
    imaj = subprocess.run(['docker', 'image', 'inspect', A.IMAGE, '--format', '{{.Id}}'],
                          capture_output=True, text=True).stdout.strip()
    rapor = dict(ders='el20', gorev=st['title'], ajan=A.IMAGE, imaj_id=imaj, elasticsearch=lab.VERSION,
                 referans='geçti', mutant_reddedilen=len(kayit), mutant_gecen=0, mutasyonlar=kayit,
                 temizlik='konteyner, logs-pafta.* veri akışı ve laboratuvar API anahtarı kalmadı',
                 acik='Fleet, entegrasyon paketi ve Kibana varlıkları kapsam dışı; standalone politika ve filestream sınanır.')
    (ROOT / 'outputs/a-notu-el20-ajan-kabul.json').write_text(json.dumps(rapor, ensure_ascii=False, indent=2) + '\n',
                                                             encoding='utf-8', newline='\n')
    print(f'{len(kayit)} mutant reddedildi, 0 geçen; temizlik doğrulandı')


if __name__ == '__main__':
    main()
