"""Real TShark CLI on an explicit training capture and temporary output folder.

No shell, external filename, arbitrary preference, plugin or live interface is
accepted here. Live collection is a separate loopback-only author fixture.
"""
import base64
import hashlib
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile


def _engine():
    try:
        from . import packet_engine
    except ImportError:
        import packet_engine
    return packet_engine


def parse_command(code):
    e=_engine()
    if not isinstance(code,str) or '\0' in code or len(code.encode('utf-8'))>e.MAX_FILTER:
        raise e.PacketError('CLI komutu en fazla 16 kB NUL içermeyen metin olmalı.')
    try:parts=shlex.split(code)
    except ValueError as exc:raise e.PacketError(str(exc)) from exc
    if not parts or parts.pop(0)!='tshark':
        raise e.PacketError('Komut tshark ile başlamalı.')
    result=[];seen_read=False;at=0
    while at<len(parts):
        flag=parts[at];at+=1
        if flag in ('-n','-2','-q','-V','-x','-P'):
            result.append(flag);continue
        if flag not in ('-r','-Y','-T','-e','-E','-o','-z','-c','-w','-F','--export-objects') or at==len(parts):
            raise e.PacketError('Desteklenmeyen/eksik CLI seçeneği: '+flag)
        value=parts[at];at+=1
        if flag=='-r':
            if value!='secili' or seen_read:raise e.PacketError('Bir kez -r secili kullanılmalı.')
            seen_read=True
        elif flag=='-Y':e._display_numeric_addresses(value)
        elif flag=='-T' and value!='fields':raise e.PacketError('Bu tezgâhta -T fields desteklenir.')
        elif flag=='-e' and not re.fullmatch(r'[A-Za-z_][\w.]*',value):raise e.PacketError('Geçersiz alan adı.')
        elif flag=='-E' and (len(value)>64 or not re.fullmatch(r'(header|separator|occurrence|quote|aggregator)=.+',value)):
            raise e.PacketError('Desteklenmeyen alan çıktısı ayarı.')
        elif flag=='-o' and not re.fullmatch(r'(tcp.desegment_tcp_streams|tcp.reassemble_out_of_order|http.desegment_body|http.desegment_headers):(TRUE|FALSE)',value):
            raise e.PacketError('Bu tercih desteklenmiyor; oturum sırlarını JSON anahtar alanından seç.')
        elif flag=='-z' and not (value in ('io,phs','conv,tcp','io,stat,0') or re.fullmatch(r'follow,tcp,(ascii|raw),[0-9]{1,4}',value)):
            raise e.PacketError('Desteklenmeyen istatistik/Follow Stream seçimi.')
        elif flag=='-c' and (not value.isdecimal() or not 1<=int(value)<=5000):raise e.PacketError('-c 1..5000 olmalı.')
        elif flag=='-w' and value not in ('sonuc.pcap','sonuc.pcapng'):raise e.PacketError('Çıktı adı sonuc.pcap veya sonuc.pcapng olmalı.')
        elif flag=='-F' and value not in ('pcap','pcapng'):raise e.PacketError('-F pcap veya pcapng olmalı.')
        elif flag=='--export-objects' and value!='http,sonuc':raise e.PacketError('Yalnız --export-objects http,sonuc desteklenir.')
        if '\0' in value:raise e.PacketError('NUL kabul edilmez.')
        result.extend((flag,value))
    if not seen_read:raise e.PacketError('-r secili gerekli; canlı arayüz bu tezgâhta açılmaz.')
    return result


def run(code,raw,key='yok'):
    e=_engine();args=parse_command(code)
    exe=e.tshark_path()
    if not exe:raise e.PacketError('TShark bulunamadı.')
    with tempfile.TemporaryDirectory(prefix='pafta_packet_cli_') as folder:
        p=Path(folder);(p/'input.pcapng').write_bytes(raw)
        env=dict(os.environ,WIRESHARK_CONFIG_DIR=folder,WIRESHARK_PLUGIN_DIR=folder,WIRESHARK_EXTCAP_DIR=folder,TZ='UTC')
        env.pop('WIRESHARK_RUN_FROM_BUILD_DIRECTORY',None);env.pop('WIRESHARK_DATA_DIR',None)
        keyfile=e._key_file(key,folder)
        args=[str(p/'input.pcapng') if previous=='-r' else value for previous,value in zip(['']+args,args)]
        # Outputs stay in cwd; names are validated above and contain no paths.
        try:
            result=subprocess.run([exe,'-n','-o','nameres.use_external_name_resolver:FALSE','-o','tls.keylog_file:'+keyfile]+args,
                                  cwd=folder,env=env,capture_output=True,timeout=12,creationflags=e.NO_WINDOW)
        except subprocess.TimeoutExpired as exc:raise e.PacketError('TShark CLI 12 saniyede bitmedi.') from exc
        stderr=result.stderr.decode('utf-8','replace')
        if result.returncode:raise e.PacketError(stderr.strip() or f'TShark CLI hata {result.returncode}')
        if len(result.stdout)>2_000_000 or len(result.stderr)>2_000_000:raise e.PacketError('CLI çıktı sınırı 2 MB aşıldı.')
        out=result.stdout.decode('utf-8','replace').replace('\r\n','\n')
        exports=[]
        candidates=list((p/'sonuc').glob('*')) if (p/'sonuc').is_dir() else []
        candidates += [p/n for n in ('sonuc.pcap','sonuc.pcapng') if (p/n).is_file()]
        for item in sorted(candidates):
            data=item.read_bytes()
            if len(data)>e.MAX_CAPTURE:raise e.PacketError('CLI dışa aktarma boyut sınırı aşıldı.')
            exports.append({'name':item.name,'size':len(data),'sha256':hashlib.sha256(data).hexdigest(),
                            'base64':base64.b64encode(data).decode(),'text':data.decode('utf-8','replace')[:4096]})
    tables=[{'satir':1,'sutunlar':['Dosya','Bayt','SHA256','Önizleme'],
             'satirlar':[[x['name'],x['size'],x['sha256'],x['text']] for x in exports]}] if exports else []
    return {'status':'ok','error':None,'segs':[['out',out]] if out else [],'stdout':out,'stderr':stderr,'tablolar':tables,
            'exports':exports,'packet_backend':'TShark CLI','packet_dialect':'tshark'}


def test_helpers(code,raw,key):
    run(code,raw,key)
    e=_engine()
    return {'src':code,'calistir':lambda kayit=None,anahtar=None:run(code,e.capture_bytes(kayit) if kayit is not None else raw,key if anahtar is None else anahtar),
            'referans_komut':lambda command,kayit=None,anahtar=None:run(command,e.capture_bytes(kayit) if kayit is not None else raw,key if anahtar is None else anahtar)}
