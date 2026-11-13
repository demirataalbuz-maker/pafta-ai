"""Verify/install existing approved CIM 8.5.0 archive; never downloads packages."""
import argparse
import hashlib
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sandbox import splunk_lab as S

ARCHIVE=ROOT/'.deps/splunk/splunk-common-information-model-cim_850.tgz'
SHA256='ed93ba614f12805ab428d71d45053ced12ce2ff1198b2f46b48537c0e0d6a412'
SOURCE='https://splunkbase.splunk.com/app/1621'


def verify_archive(path=ARCHIVE):
    if not path.is_file():
        raise RuntimeError('CIM 8.5.0 arşivi yok; resmî kaynaktan kullanıcı onayıyla edinilmeli: '+SOURCE)
    if hashlib.sha256(path.read_bytes()).hexdigest()!=SHA256:
        raise RuntimeError('CIM arşivi kabul edilen yerel SHA256 ile uyuşmuyor; kurulmadı')
    with tarfile.open(path) as archive:
        for member in archive.getmembers():
            parts=PurePosixPath(member.name)
            if parts.is_absolute() or '..' in parts.parts or member.issym() or member.islnk():
                raise RuntimeError('CIM arşivinde destek dışı yol/bağlantı')
        conf=archive.extractfile('Splunk_SA_CIM/default/app.conf').read().decode('utf-8')
        if '8.5.0' not in conf:raise RuntimeError('CIM app.conf sürümü beklenmiyor')
    return path


def installed():
    try:
        info=S.istek('/services/apps/local/Splunk_SA_CIM')['entry'][0]['content']
        return info.get('version')=='8.5.0' and not info.get('disabled')
    except S.SplunkHatasi:
        return False


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install',action='store_true',help='Mevcut arşivi Pafta Splunk konteynerine kur')
    args=parser.parse_args()
    path=verify_archive()
    if installed():
        print('CIM 8.5.0 kurulu/etkin; arşiv SHA256 doğrulandı. Değişiklik yapılmadı.')
        return
    if not args.install:raise SystemExit('CIM 8.5.0 etkin değil; python tools/splunk_cim_kur.py --install')
    # Only the existing Pafta container is changed. No host extraction/password CLI.
    code,_,err=S._docker('cp',str(path),S.KONTEYNER+':/tmp/pafta-cim-850.tgz')
    if code:raise RuntimeError('CIM kopyalanamadı: '+err[-300:])
    S.istek('/services/apps/local',{'name':'/tmp/pafta-cim-850.tgz','filename':'true','update':'1'},timeout=120)
    S.istek('/services/server/control/restart',{},timeout=30)
    for _ in range(60):
        try:
            if installed():
                print('CIM 8.5.0 kuruldu/etkin; yerel Pafta Splunk yeniden başlatıldı.')
                return
        except OSError:pass
        time.sleep(2)
    raise RuntimeError('CIM kurulumundan sonra Splunk hazır olmadı')


if __name__=='__main__':main()
