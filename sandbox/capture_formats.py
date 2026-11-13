"""Bounded PCAP/PCAPNG framing, not a protocol/filter emulator.

Original packet order, caplen/wirelen, interface DLT and exact timestamp
fractions are retained. Native TShark/libpcap own packet dissection.
"""
from dataclasses import dataclass
from fractions import Fraction
import struct


class CaptureError(ValueError):
    pass


@dataclass(frozen=True)
class Frame:
    data: bytes
    wirelen: int
    linktype: int
    snaplen: int
    section: int
    interface: int
    timestamp: Fraction | None


MAGIC = {b'\xd4\xc3\xb2\xa1':('<',10**6), b'\xa1\xb2\xc3\xd4':('>',10**6),
         b'\x4d\x3c\xb2\xa1':('<',10**9), b'\xa1\xb2\x3c\x4d':('>',10**9)}
LINKTYPES = {1:1,101:12,113:113,276:276}  # file LINKTYPE -> native DLT


def _link(value):
    if value not in LINKTYPES:
        raise CaptureError(f'Desteklenmeyen LINKTYPE {value}; desteklenen: Ethernet=1, RAW=101, SLL=113, SLL2=276.')


def _options(data, order):
    result={}
    at=0
    while at<len(data):
        if len(data)-at<4:
            raise CaptureError('PCAPNG seçenek başlığı eksik.')
        code,size=struct.unpack_from(order+'HH',data,at);at+=4
        if code==0:
            if size or any(data[at:]):
                raise CaptureError('PCAPNG seçenek sonu geçersiz.')
            break
        padded=(size+3)&~3
        if at+padded>len(data):
            raise CaptureError('PCAPNG seçenek baytları eksik.')
        result.setdefault(code,[]).append(data[at:at+size]);at+=padded
    return result


def parse_capture(raw, *, contexts=None):
    if not isinstance(raw,bytes) or len(raw)>8*1024*1024:
        raise CaptureError('Kayıt en fazla 8 MiB bayt olmalı.')
    if raw[:4] in MAGIC:
        return _classic(raw,contexts)
    if raw[:4]==b'\x0a\x0d\x0d\x0a':
        return _pcapng(raw,contexts)
    raise CaptureError('Classic PCAP 2.4 veya PCAPNG başlığı gerekli.')


def _classic(raw,contexts):
    if len(raw)<24:
        raise CaptureError('PCAP başlığı eksik.')
    order,scale=MAGIC[raw[:4]]
    major,minor,_,_,snap,link=struct.unpack_from(order+'HHiIII',raw,4)
    if (major,minor)!=(2,4) or not 1<=snap<=0x7fffffff:
        raise CaptureError('PCAP sürüm 2.4 ve geçerli snaplen gerekli.')
    _link(link)
    if contexts is not None:
        contexts.append((link,snap))
    frames=[];at=24
    while at<len(raw):
        if len(raw)-at<16:
            raise CaptureError('PCAP paket başlığı eksik.')
        sec,sub,cap,wire=struct.unpack_from(order+'IIII',raw,at);at+=16
        if sub>=scale or cap>snap or cap>wire or at+cap>len(raw):
            raise CaptureError('PCAP paket zamanı/caplen/wirelen veya baytları geçersiz.')
        frames.append(Frame(raw[at:at+cap],wire,link,snap,0,0,Fraction(sec)+Fraction(sub,scale)))
        at+=cap
    return frames


def _pcapng(raw,contexts):
    frames=[];interfaces=[];at=0;section=-1;order=None
    while at<len(raw):
        if len(raw)-at<12:
            raise CaptureError('PCAPNG blok başlığı eksik.')
        if raw[at:at+4]==b'\x0a\x0d\x0d\x0a':
            bom=raw[at+8:at+12]
            order={b'\x4d\x3c\x2b\x1a':'<',b'\x1a\x2b\x3c\x4d':'>'}.get(bom)
            if order is None:
                raise CaptureError('PCAPNG byte-order magic geçersiz.')
        if order is None:
            raise CaptureError('PCAPNG section başlığı gerekli.')
        kind,size=struct.unpack_from(order+'II',raw,at)
        if size<12 or size%4 or at+size>len(raw) or struct.unpack_from(order+'I',raw,at+size-4)[0]!=size:
            raise CaptureError('PCAPNG blok boyu/son boyu veya baytları geçersiz.')
        body=raw[at+8:at+size-4]
        if kind==0x0a0d0d0a:
            if len(body)<16 or struct.unpack_from(order+'HH',body,4)!=(1,0):
                raise CaptureError('PCAPNG yalnız section sürümü 1.0 desteklenir.')
            _options(body[16:],order)
            interfaces=[];section+=1
        elif kind==1:
            if len(body)<8:
                raise CaptureError('PCAPNG interface başlığı eksik.')
            link,reserved,snap=struct.unpack_from(order+'HHI',body)
            _link(link)
            if reserved or snap>0x7fffffff:
                raise CaptureError('PCAPNG interface reserved/snaplen geçersiz.')
            opts=_options(body[8:],order)
            for code,length in ((9,1),(14,8)):
                if code in opts and (len(opts[code])!=1 or len(opts[code][0])!=length):
                    raise CaptureError('PCAPNG tsresol/tsoffset seçeneği geçersiz.')
            resolution=opts.get(9,[b'\x06'])[0][0]
            scale=(2**(resolution&127)) if resolution&128 else 10**resolution
            offset=struct.unpack(order+'q',opts.get(14,[b'\0'*8])[0])[0]
            interfaces.append((link,snap,scale,offset))
            if contexts is not None:
                contexts.append((link,snap or 0x7fffffff))
        elif kind==6:
            if len(body)<20:
                raise CaptureError('PCAPNG enhanced packet başlığı eksik.')
            interface,hi,lo,cap,wire=struct.unpack_from(order+'IIIII',body)
            if interface>=len(interfaces):
                raise CaptureError('PCAPNG paket interface kimliği tanımlı değil.')
            link,snap,scale,offset=interfaces[interface]
            padded=(cap+3)&~3
            if cap>wire or (snap and cap>snap) or len(body)<20+padded:
                raise CaptureError('PCAPNG caplen/snaplen/wirelen veya paket baytları geçersiz.')
            _options(body[20+padded:],order)
            stamp=Fraction((hi<<32)|lo,scale)+offset
            frames.append(Frame(body[20:20+cap],wire,link,snap or 0x7fffffff,section,interface,stamp))
        elif kind in (2,3):
            raise CaptureError('PCAPNG eski Packet Block ve Simple Packet Block desteklenmiyor; Enhanced Packet Block kullanın.')
        # Unknown non-packet blocks are skipped according to the block length.
        at+=size
    return frames
