"""Deterministic offline framing witnesses and authored protocol corpus loader."""
from fractions import Fraction
import json
import hashlib
from pathlib import Path
import struct

HERE=Path(__file__).resolve().parent.parent/'tracks/packets/captures'


def pcapng(frames, interfaces=((1,65535,6),), order='<'):
    """frames: (interface, ticks, captured bytes, original length)."""
    def block(kind,body):
        size=12+len(body)
        return struct.pack(order+'II',kind,size)+body+struct.pack(order+'I',size)
    raw=block(0x0a0d0d0a,struct.pack(order+'IHHq',0x1a2b3c4d,1,0,-1))
    for link,snap,res in interfaces:
        raw+=block(1,struct.pack(order+'HHIHH',link,0,snap,9,1)+bytes([res])+b'\0'*3+struct.pack(order+'HH',0,0))
    for interface,ticks,data,wire in frames:
        raw+=block(6,struct.pack(order+'IIIII',interface,ticks>>32,ticks&0xffffffff,len(data),wire)
                   +data+b'\0'*(-len(data)%4))
    return raw


def mixed_capture():
    try:
        from . import packet_fixtures as pf
    except ImportError:
        import packet_fixtures as pf
    frames=[]
    for interface,link in enumerate((1,101,113,276)):
        for port in (79,80,81):
            ip=pf.ipv4(pf.tcp(50000,port),pf.CLIENT,pf.SERVER,6)
            if link==1:
                packet=pf.ethernet(ip)
            elif link==101:
                packet=ip
            elif link==113:
                packet=struct.pack('!HHH8sH',0,1,6,b'\x02\0\0\0\0\x10\0\0',0x800)+ip
            else:
                packet=struct.pack('!HHIHBB8s',0x800,0,1,1,0,6,b'\x02\0\0\0\0\x10\0\0')+ip
            scale=10**9 if interface==1 else 2**10 if interface==2 else 10**6
            ticks=(1700000000+len(frames))*scale+1
            frames.append((interface,ticks,packet,len(packet)))
    # Explicit captured/wire length mismatch, with the TCP ports cut away.
    full=pf.ethernet(pf.ipv4(pf.tcp(50000,80),pf.CLIENT,pf.SERVER,6))
    frames.append((0,1700000012*10**6,full[:30],128))
    return pcapng(frames,((1,65535,6),(101,65535,9),(113,65535,138),(276,65535,6)))


def captures():
    result={'arayuzler':mixed_capture()}
    manifest=HERE/'advanced.json'
    if manifest.exists():
        for name,entry in json.loads(manifest.read_text(encoding='utf-8')).items():
            filename=entry['file']
            if Path(filename).name!=filename:
                raise ValueError('Invalid authored capture filename')
            data=(HERE/filename).read_bytes()
            if hashlib.sha256(data).hexdigest()!=entry['sha256']:
                raise ValueError('Eğitim korpusu SHA256 uyuşmazlığı: '+name)
            result[name]=data
    return result


def shifted_capture(name):
    """Prefix one unrelated ARP frame: filters must not hardcode frame IDs."""
    try:
        from . import packet_fixtures as pf
        from .capture_formats import parse_capture
    except ImportError:
        import packet_fixtures as pf
        from capture_formats import parse_capture
    first=pf.ethernet(pf.arp(),0x0806)
    return pf.pcap([(first,len(first))]+[(f.data,f.wirelen) for f in parse_capture(captures()[name])])


def describe(name):
    try:
        from .capture_formats import parse_capture
    except ImportError:
        from capture_formats import parse_capture
    frames=parse_capture(captures()[name])
    first=frames[0].timestamp if frames else Fraction(0)
    return [dict(id=i,caplen=len(f.data),wirelen=f.wirelen,note=f'LINKTYPE {f.linktype}; interface {f.interface}; section {f.section}',
                 time_relative=str(f.timestamp-first) if f.timestamp is not None else 'bilinmiyor')
            for i,f in enumerate(frames,1)]
