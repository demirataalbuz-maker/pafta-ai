"""Offline numeric BPF filters using the pinned wheel's native libpcap DLL.

Only pcap_open_dead, compile, offline_filter, freecode and close are called.
No adapter, capture service, live handle or packet transmission is involved.
Input is bounded PCAP/PCAPNG; every interface uses its actual link type.
Name/service lookups are deliberately disabled: use numeric addresses/ports.
"""
import ctypes as ct
import ipaddress
import os
from pathlib import Path
import re
import threading
try:
    from .capture_formats import parse_capture, CaptureError, LINKTYPES
except ImportError:
    from capture_formats import parse_capture, CaptureError, LINKTYPES


class BpfUnavailableError(RuntimeError):
    pass


class BpfFilterError(ValueError):
    pass


class PcapFormatError(ValueError):
    pass


class _Timeval(ct.Structure):
    _fields_ = [("tv_sec", ct.c_long), ("tv_usec", ct.c_long)]


class _PcapHeader(ct.Structure):
    _fields_ = [("ts", _Timeval), ("caplen", ct.c_uint32), ("len", ct.c_uint32)]


class _BpfInsn(ct.Structure):
    _fields_ = [("code", ct.c_ushort), ("jt", ct.c_ubyte),
                ("jf", ct.c_ubyte), ("k", ct.c_uint32)]


class _BpfProgram(ct.Structure):
    _fields_ = [("bf_len", ct.c_uint), ("bf_insns", ct.POINTER(_BpfInsn))]


_DLL = None
_LOCK = threading.Lock()
_DLL_FOLDER = (Path(__file__).resolve().parent.parent / ".deps" / "libpcap" /
               "_platform" / "windows" / "x86_64" / "tcpdump")
_WORDS = frozenset("""
and or not src dst host net mask port portrange ether link ip ip6 arp rarp
tcp udp sctp icmp icmp6 igmp ah esp pim proto protochain broadcast multicast
less greater len vlan mpls pppoed pppoes geneve tcpflags icmptype icmpcode
icmp6type icmp6code tcp-fin tcp-syn tcp-rst tcp-push tcp-ack tcp-urg tcp-ece
tcp-cwr icmp-echoreply icmp-unreach icmp-sourcequench icmp-redirect icmp-echo
icmp-routeradvert icmp-routersolicit icmp-timxceed icmp-paramprob icmp-tstamp
icmp-tstampreply icmp-ireq icmp-ireqreply icmp-maskreq icmp-maskreply
icmp6-destinationunreach icmp6-packettoobig icmp6-timeexceeded
icmp6-parameterproblem icmp6-echo icmp6-echoreply
""".split())


def _library():
    global _DLL
    if _DLL is not None:
        return _DLL
    with _LOCK:
        if _DLL is not None:
            return _DLL
        if os.name != "nt" or ct.sizeof(ct.c_void_p) != 8:
            raise BpfUnavailableError("BPF: bu paket Windows x64 Python gerektirir.")
        if (ct.sizeof(_PcapHeader), _PcapHeader.caplen.offset,
                _PcapHeader.len.offset) != (16, 8, 12):
            raise BpfUnavailableError("BPF: beklenen Windows pcap_pkthdr ABI'si 16/8/12 değil.")
        path = _DLL_FOLDER / "pcap.dll"
        missing = [name for name in ("pcap.dll", "libssl-3-x64.dll", "libcrypto-3-x64.dll")
                   if not (_DLL_FOLDER / name).is_file()]
        if missing:
            raise BpfUnavailableError(
                "BPF DLL eksik: " + ", ".join(missing) + ". "
                "Proje kökünde python -m pip install --target .deps --no-deps "
                "libpcap==1.11.0b29 çalıştırın. Sürücü gerekmez. Yol: " + str(path))
        try:
            with os.add_dll_directory(str(_DLL_FOLDER)):
                dll = ct.CDLL(str(path))
            dll.pcap_lib_version.argtypes = []
            dll.pcap_lib_version.restype = ct.c_char_p
            dll.pcap_open_dead.argtypes = [ct.c_int, ct.c_int]
            dll.pcap_open_dead.restype = ct.c_void_p
            dll.pcap_compile.argtypes = [ct.c_void_p, ct.POINTER(_BpfProgram),
                                         ct.c_char_p, ct.c_int, ct.c_uint32]
            dll.pcap_compile.restype = ct.c_int
            dll.pcap_geterr.argtypes = [ct.c_void_p]
            dll.pcap_geterr.restype = ct.c_char_p
            dll.pcap_offline_filter.argtypes = [ct.POINTER(_BpfProgram),
                                                ct.POINTER(_PcapHeader), ct.c_void_p]
            dll.pcap_offline_filter.restype = ct.c_uint
            dll.pcap_freecode.argtypes = [ct.POINTER(_BpfProgram)]
            dll.pcap_freecode.restype = None
            dll.pcap_close.argtypes = [ct.c_void_p]
            dll.pcap_close.restype = None
        except (OSError, AttributeError) as exc:
            raise BpfUnavailableError(
                f"BPF DLL yüklenemedi: {path}. Aynı klasördeki iki OpenSSL DLL'ini "
                "ve x64 Python'u doğrulayın; libpcap==1.11.0b29 wheel'ini .deps'e "
                f"yeniden açın. Native ayrıntı: {exc}") from exc
        _DLL = dll
        return dll


def available():
    """Return whether the local native DLL and its required exports load."""
    try:
        _library()
        return True
    except BpfUnavailableError:
        return False


def version():
    """Return the C library version, distinct from the Python wheel version."""
    return _library().pcap_lib_version().decode("utf-8", "replace")


def _numeric_filter(text):
    if not isinstance(text, str):
        raise TypeError("BPF filtresi metin olmalı.")
    # libpcap can resolve host/service names while compiling even without a
    # live handle. An allowlist prevents such lookups; native libpcap still
    # parses and evaluates every accepted expression, including byte accessors.
    if not re.fullmatch(r"[A-Za-z0-9_.:\s()/\[\]&|!<>=+*%^,\-]*", text):
        raise BpfFilterError("BPF: yalnız sayısal adres/port ve offline anahtar sözcükler; "
                             "tırnak, ters bölü veya diğer karakterler desteklenmiyor.")
    for token in re.findall(r"[A-Za-z0-9_.:]+(?:-[A-Za-z0-9_]+)*", text):
        if token in _WORDS or re.fullmatch(r"(?:0[xX][0-9A-Fa-f]+|[0-9]+)(?:-[0-9]+)?", token):
            continue
        if re.fullmatch(r"[0-9]+:[0-9]+", token):
            continue  # byte-offset:size, never a DNS name
        if re.fullmatch(r"[0-9A-Fa-f]{1,2}(?::[0-9A-Fa-f]{1,2}){5}", token):
            continue
        try:
            ipaddress.ip_address(token)
        except ValueError:
            raise BpfFilterError(
                f"BPF: {token!r} desteklenmiyor; DNS/servis adı çözülmez. "
                "Tam sayısal IP, MAC, port veya protokol numarası kullanın.") from None
    return text.encode("ascii")


def evaluate(filter_text, pcap_bytes):
    """Return matching 1-based frame numbers; never open a capture interface.

    Native errors are BpfFilterError, invalid PCAP/PCAPNG is PcapFormatError,
    missing local runtime is BpfUnavailableError. IPv4 broadcast tests have no
    assumed interface mask (PCAP_NETMASK_UNKNOWN), so libpcap rejects them.
    """
    expression = _numeric_filter(filter_text)
    contexts=[]
    try:
        packets = parse_capture(pcap_bytes,contexts=contexts)
    except CaptureError as exc:
        raise PcapFormatError(str(exc)) from exc
    dll = _library()
    programs={}
    try:
        matched = []
        # Empty captures still compile: an invalid filter must not pass vacuously.
        if not contexts:
            raise BpfFilterError('BPF: kayıtta tanımlı arayüz yok.')
        for link,snap in sorted(set(contexts)):
            handle=dll.pcap_open_dead(LINKTYPES[link],snap)
            if not handle:
                raise BpfUnavailableError(f'BPF: LINKTYPE {link} handle oluşturulamadı.')
            program=_BpfProgram()
            if dll.pcap_compile(handle,ct.byref(program),expression,1,0xffffffff):
                message=(dll.pcap_geterr(handle) or b'unknown').decode('utf-8','replace')
                dll.pcap_close(handle)
                raise BpfFilterError(f'BPF derleme hatası (LINKTYPE {link}): {message}')
            programs[(link,snap)]=(handle,program)
        for number, frame in enumerate(packets, 1):
            program=programs[(frame.linktype,frame.snaplen)][1]
            # offline_filter ignores timestamps; don't truncate exact fractions
            # to a platform timeval merely to supply unused fields.
            header = _PcapHeader(_Timeval(0,0),len(frame.data),frame.wirelen)
            buffer = ct.create_string_buffer(frame.data)
            if dll.pcap_offline_filter(ct.byref(program), ct.byref(header), buffer):
                matched.append(number)
        return matched
    finally:
        for handle,program in programs.values():
            dll.pcap_freecode(ct.byref(program))
            dll.pcap_close(handle)
