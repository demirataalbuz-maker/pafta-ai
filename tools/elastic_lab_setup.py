"""Explicit, opt-in local Elastic installation. Never downloads from lesson execution.

Run --pull once after consenting to the official image downloads, then --start.
No host directory mounts, restart policy, trial license, or external published ports.
The password is generated in ignored .deps/elastic-lab, never printed or committed.
"""
import argparse
import base64
import json
from pathlib import Path
import secrets
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / '.deps' / 'elastic-lab'
VERSION = '9.5.5'
ES_IMAGE = 'docker.elastic.co/elasticsearch/elasticsearch:9.5.5@sha256:13b4a40bb095774f5fda635e45fd5677cc6a26565e42b24997b0c72b88e75984'
KB_IMAGE = 'docker.elastic.co/kibana/kibana:9.5.5@sha256:13b72ce7222c36e4213229004ae62a87aeb32fd372ebfa6fb38f7a3285fdbb78'
ES = 'http://127.0.0.1:19200'
KB = 'http://127.0.0.1:15601'

def docker(*args, check=True):
    try:
        result = subprocess.run(['docker', *args], check=False, capture_output=True,
                                encoding='utf-8', timeout=600,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except (OSError, subprocess.TimeoutExpired):
        # run arguments include generated credentials; never render them via
        # CalledProcessError/TimeoutExpired in a public installation traceback.
        raise RuntimeError('Docker '+str(args[0])+' çağrısı tamamlanamadı; Docker Desktop durumunu kontrol edin.') from None
    if check and result.returncode:
        raise RuntimeError('Docker '+str(args[0])+' başarısız; daemon, imaj ve port durumunu kontrol edin.')
    return result

def secret(name):
    STATE.mkdir(parents=True, exist_ok=True)
    p = STATE / name
    if not p.exists():
        with p.open('x', encoding='ascii') as f:
            f.write(secrets.token_hex(24))
    return p.read_text(encoding='ascii').strip()

def request(url, data=None, password=None, method=None):
    headers = {'Content-Type':'application/json', 'kbn-xsrf':'pafta'}
    if password:
        headers['Authorization'] = 'Basic ' + base64.b64encode(('elastic:'+password).encode()).decode()
    r = urllib.request.Request(url, None if data is None else json.dumps(data).encode(), headers, method=method)
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(r, timeout=8) as response:
        return json.load(response)

def wait(url, password, seconds=300):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        try:
            return request(url, password=password)
        except (OSError, ValueError):
            time.sleep(2)
    raise RuntimeError('Yerel API zamanında açılmadı: '+url)

def start():
    for image in (ES_IMAGE, KB_IMAGE):
        if docker('image','inspect', image, check=False).returncode:
            raise RuntimeError('İmaj yok; açık indirme onayından sonra --pull çalıştırın: '+image)
    password = secret('password')
    if docker('network','inspect','pafta-elastic',check=False).returncode:
        docker('network','create','pafta-elastic')
    for name, image, args in [
        ('pafta-elasticsearch', ES_IMAGE, ['-p','127.0.0.1:19200:9200','--memory','2g',
          '-e','discovery.type=single-node','-e','xpack.security.enabled=true',
          '-e','xpack.security.http.ssl.enabled=false','-e','xpack.security.authc.api_key.enabled=true',
          '-e','xpack.license.self_generated.type=basic','-e','xpack.ml.enabled=false',
          '-e','ES_JAVA_OPTS=-Xms768m -Xmx768m','-e','ELASTIC_PASSWORD='+password,
          '-v','pafta-elastic-data:/usr/share/elasticsearch/data'])]:
        if docker('inspect', name,check=False).returncode:
            docker('run','-d','--pull','never','--name',name,'--network','pafta-elastic','--restart','no',*args,image)
        else:
            docker('start',name)
    info = wait(ES, password)
    if info['version']['number'] != VERSION:
        raise RuntimeError('Beklenmeyen Elasticsearch sürümü')
    token_path = STATE/'kibana-token'
    if not token_path.exists():
        token = request(ES+'/_security/service/elastic/kibana/credential/token/pafta-lab',password=password,method='POST')['token']['value']
        token_path.write_text(token, encoding='ascii')
    if docker('inspect','pafta-kibana',check=False).returncode:
        docker('run','-d','--pull','never','--name','pafta-kibana','--network','pafta-elastic',
               '--restart','no','--memory','2g','-p','127.0.0.1:15601:5601',
               '-e','ELASTICSEARCH_HOSTS=http://pafta-elasticsearch:9200',
               '-e','ELASTICSEARCH_SERVICEACCOUNTTOKEN='+token_path.read_text(encoding='ascii'),
               '-e','XPACK_ENCRYPTEDSAVEDOBJECTS_ENCRYPTIONKEY='+secret('objects-key'),
               '-e','XPACK_SECURITY_ENCRYPTIONKEY='+secret('security-key'),
               '-e','XPACK_REPORTING_ENCRYPTIONKEY='+secret('reporting-key'),
               '-e','TELEMETRY_ENABLED=false','-e','TELEMETRY_OPTIN=false',KB_IMAGE)
    else:
        docker('start','pafta-kibana')
    wait(KB+'/api/status', password)
    print('Elastic '+VERSION+' Basic hazır: '+ES+' / '+KB)
    print('Kullanıcı elastic; parola .deps/elastic-lab/password içinde. HTTP yalnız localhost laboratuvarıdır.')

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pull',action='store_true')
    p.add_argument('--start',action='store_true')
    p.add_argument('--stop',action='store_true')
    args = p.parse_args()
    if args.pull:
        for image in (ES_IMAGE,KB_IMAGE):
            docker('pull',image)
    if args.start:
        start()
    if args.stop:
        docker('stop','pafta-kibana','pafta-elasticsearch')
    if not any(vars(args).values()):
        p.print_help()

if __name__ == '__main__':
    main()
