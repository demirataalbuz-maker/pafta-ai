"""Pafta's fixed-lab real LDAP probes, exposed to learner Python as ad_lab."""
import json
import os
from pathlib import Path
import ssl
import subprocess

ROOT=Path(__file__).resolve().parents[1]
MODES={'valid','none','wrong','signed','unsigned','bad-ca','bad-name','starttls'}


def linux_path(script,distro):
    # --exec bypasses the default Linux shell: backslashes, spaces and '$'
    # remain one literal argv value, including paths that need no Windows quotes.
    path=subprocess.run(['wsl.exe','-d',distro,'--exec','wslpath','-a','-u',str(script)],
                        capture_output=True,timeout=15,
                        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if path.returncode or not path.stdout.strip():
        raise RuntimeError('Kali WSL yolu çözümlenemedi.')
    return path.stdout.decode('utf8').strip()


def probe(mode, filtre='(sAMAccountName=ali.kaya)'):
    if mode not in MODES:
        raise ValueError('Bilinmeyen LDAP deney modu: '+str(mode))
    from sandbox.ad_vm_process import LAB,ensure_ready
    config=ensure_ready('PF-DC01')
    if not config.get('ldaps_ready'):
        raise RuntimeError('Pafta AD LDAPS ilk kurulumu tamamlanmamış.')
    certificate=(LAB/'root-ca.cer').read_bytes()
    pem=certificate.decode('ascii') if b'-----BEGIN' in certificate else ssl.DER_cert_to_PEM_cert(certificate)
    distro=os.environ.get('PAFTA_WSL_DISTRO','kali-linux')
    script=ROOT/'sandbox/ad_vm/ldap_client_linux.py'
    no_window=getattr(subprocess,'CREATE_NO_WINDOW',0)
    path=linux_path(script,distro)
    request={'mode':mode,'filter':filtre,'address':config['dc_address'],'password':config['guests']['PF-DC01']['password'],'ca_pem':pem}
    # Credentials are stdin only, never process arguments or learner output.
    p=subprocess.run(['wsl.exe','-d',distro,'--exec','python3',path],input=json.dumps(request).encode(),capture_output=True,timeout=45,creationflags=no_window)
    if p.returncode:
        raise RuntimeError('Kali LDAP istemcisi çalışmadı; kurulu Python/Impacket/OpenLDAP gereksinimlerini kontrol edin.')
    try:
        return json.loads(p.stdout)
    except ValueError:
        raise RuntimeError('LDAP istemcisi geçerli sonuç vermedi.') from None
