"""Deterministic, offline-only Ethernet captures built from synthetic bytes.

No socket, interface or live traffic is used. Packet IDs are one-based frame
numbers. Ethernet frames omit FCS; lengths include Ethernet padding. The single
explicitly truncated record retains the original wire length in its PCAP header.
"""
from __future__ import annotations

import copy
import ipaddress
import struct
from functools import lru_cache

CLIENT_MAC = "02:00:00:00:00:10"
SERVER_MAC = "02:00:00:00:00:20"
DNS_MAC = "02:00:00:00:00:53"
CLIENT = "10.0.0.10"
SERVER = "10.0.0.20"
DNS = "10.0.0.53"
CLIENT6 = "2001:db8::10"
SERVER6 = "2001:db8::20"
START_SECONDS = 1700000000
STEP_US = 1000000


def checksum(data: bytes) -> int:
    """Internet checksum, suitable for an already checksummed block too."""
    data = bytes(data)
    if len(data) % 2:
        data += b"\0"
    value = sum(struct.unpack(f"!{len(data)//2}H", data))
    while value >> 16:
        value = (value & 0xffff) + (value >> 16)
    return (~value) & 0xffff


def _mac(text: str) -> bytes:
    parts = text.split(":")
    if len(parts) != 6 or any(len(p) != 2 for p in parts):
        raise ValueError("MAC adresi altı iki haneli hex alanı olmalı")
    return bytes(int(p, 16) for p in parts)


def ethernet(payload: bytes, ethertype: int = 0x0800, *, src: str = CLIENT_MAC,
             dst: str = SERVER_MAC, vlan: int | None = None,
             vlans: tuple[int, ...] = (), min_length: int = 60) -> bytes:
    """Ethernet II frame; optional outer-to-inner VLAN IDs; no FCS."""
    if vlan is not None:
        if vlans:
            raise ValueError("vlan veya vlans seçilmeli")
        vlans = (vlan,)
    if not 0 <= ethertype <= 0xffff or any(not 0 <= v <= 4095 for v in vlans):
        raise ValueError("EtherType/VLAN aralığı geçersiz")
    packet = _mac(dst) + _mac(src)
    for index, vid in enumerate(vlans):
        packet += struct.pack("!HH", 0x88a8 if len(vlans) > 1 and index == 0 else 0x8100, vid)
    packet += struct.pack("!H", ethertype) + bytes(payload)
    return packet + bytes(max(0, min_length - len(packet)))


def ipv4(payload: bytes, src: str = CLIENT, dst: str = SERVER, proto: int = 6,
         *, ident: int = 1, ttl: int = 64, flags: int = 2,
         frag_offset: int = 0, options: bytes = b"") -> bytes:
    """IPv4 datagram. frag_offset is in eight-byte units; flags is 3 bits."""
    if len(options) % 4 or len(options) > 40:
        raise ValueError("IPv4 seçenekleri 4 bayt katı ve en fazla 40 bayt olmalı")
    if not 0 <= frag_offset <= 8191 or not 0 <= flags <= 7:
        raise ValueError("IPv4 fragment alanı geçersiz")
    source, target = ipaddress.IPv4Address(src).packed, ipaddress.IPv4Address(dst).packed
    length = 20 + len(options) + len(payload)
    if length > 65535:
        raise ValueError("IPv4 datagramı çok büyük")
    header = struct.pack("!BBHHHBBH4s4s", 0x45 + len(options)//4, 0, length,
                         ident, (flags << 13) | frag_offset, ttl, proto, 0, source, target) + options
    return header[:10] + struct.pack("!H", checksum(header)) + header[12:] + bytes(payload)


def ipv6(payload: bytes, src: str = CLIENT6, dst: str = SERVER6,
         next_header: int = 6, *, hop_limit: int = 64) -> bytes:
    """IPv6 base header; callers may supply explicit extension headers."""
    if len(payload) > 65535:
        raise ValueError("Bu fixture builder jumbogram üretmez")
    return struct.pack("!IHBB16s16s", 6 << 28, len(payload), next_header, hop_limit,
                       ipaddress.IPv6Address(src).packed, ipaddress.IPv6Address(dst).packed) + bytes(payload)


def _pseudo(src: str, dst: str, proto: int, length: int) -> bytes:
    source, target = ipaddress.ip_address(src), ipaddress.ip_address(dst)
    if source.version != target.version:
        raise ValueError("İki uç aynı IP ailesinde olmalı")
    if source.version == 4:
        return source.packed + target.packed + struct.pack("!BBH", 0, proto, length)
    return source.packed + target.packed + struct.pack("!I3xB", length, proto)


def tcp(sport: int = 40000, dport: int = 80, payload: bytes = b"", *,
        src: str = CLIENT, dst: str = SERVER, seq: int = 1000, ack: int = 0,
        flags: int = 0x02, window: int = 64240, options: bytes = b"") -> bytes:
    """TCP segment with IP pseudoheader checksum; no external state required."""
    if len(options) % 4 or len(options) > 40 or not 0 <= flags <= 0x1ff:
        raise ValueError("TCP seçenekleri veya bayrakları geçersiz")
    header = struct.pack("!HHIIHHHH", sport, dport, seq, ack,
                         ((5 + len(options)//4) << 12) | flags, window, 0, 0) + options
    value = checksum(_pseudo(src, dst, 6, len(header)+len(payload)) + header + payload)
    return header[:16] + struct.pack("!H", value) + header[18:] + bytes(payload)


def udp(sport: int = 53000, dport: int = 53, payload: bytes = b"", *,
        src: str = CLIENT, dst: str = DNS) -> bytes:
    """UDP datagram with a nonzero checksum for both IPv4 and IPv6."""
    length = 8 + len(payload)
    header = struct.pack("!HHHH", sport, dport, length, 0)
    value = checksum(_pseudo(src, dst, 17, length) + header + payload) or 0xffff
    return header[:6] + struct.pack("!H", value) + bytes(payload)


def crc32c(data: bytes) -> int:
    value = 0xffffffff
    for octet in data:
        value ^= octet
        for _ in range(8):
            value = (value >> 1) ^ (0x82f63b78 if value & 1 else 0)
    return value ^ 0xffffffff


def sctp(sport: int = 50000, dport: int = 3868) -> bytes:
    """A valid SCTP INIT chunk with a reflected CRC32C, not a TCP surrogate."""
    header = struct.pack("!HHII", sport, dport, 0, 0)
    chunk = struct.pack("!BBHIIHHI", 1, 0, 20, 0x10203040, 65535, 2, 2, 1000)
    packet = header + chunk
    return packet[:8] + struct.pack("<I", crc32c(packet)) + packet[12:]


def arp(sender_ip: str = CLIENT, target_ip: str = SERVER, *, opcode: int = 1,
        sender_mac: str = CLIENT_MAC, target_mac: str = "00:00:00:00:00:00") -> bytes:
    return (struct.pack("!HHBBH", 1, 0x0800, 6, 4, opcode) + _mac(sender_mac)
            + ipaddress.IPv4Address(sender_ip).packed + _mac(target_mac)
            + ipaddress.IPv4Address(target_ip).packed)


def icmp_echo(payload: bytes = b"PAFTA", *, src: str = CLIENT, dst: str = SERVER,
              ipv6_mode: bool = False, ident: int = 1, seq: int = 1) -> bytes:
    packet = struct.pack("!BBHHH", 128 if ipv6_mode else 8, 0, 0, ident, seq) + payload
    value = checksum((_pseudo(src, dst, 58, len(packet)) if ipv6_mode else b"") + packet)
    return packet[:2] + struct.pack("!H", value) + packet[4:]


def _dns_name(name: str) -> bytes:
    labels = name.rstrip(".").split(".")
    if any(not 0 < len(label.encode("ascii")) <= 63 for label in labels):
        raise ValueError("DNS etiketi 1–63 ASCII bayt olmalı")
    return b"".join(bytes([len(label)]) + label.encode("ascii") for label in labels) + b"\0"


def dns_query(name: str = "portal.lab.test", qtype: int = 1, txid: int = 0x1201) -> bytes:
    return struct.pack("!6H", txid, 0x0100, 1, 0, 0, 0) + _dns_name(name) + struct.pack("!HH", qtype, 1)


def dns_response(name: str = "portal.lab.test", address: str = SERVER,
                 txid: int = 0x1201) -> bytes:
    value = ipaddress.ip_address(address)
    qtype = 1 if value.version == 4 else 28
    question = _dns_name(name) + struct.pack("!HH", qtype, 1)
    answer = b"\xc0\x0c" + struct.pack("!HHIH", qtype, 1, 60, len(value.packed)) + value.packed
    return struct.pack("!6H", txid, 0x8180, 1, 1, 0, 0) + question + answer


def http_request(uri: str = "/health", host: str = "portal.lab.test", method: str = "GET") -> bytes:
    return f"{method} {uri} HTTP/1.1\r\nHost: {host}\r\nUser-Agent: Pafta-Fixture\r\nContent-Length: 0\r\n\r\n".encode("ascii")


def http_response(status: int = 200) -> bytes:
    reasons = {200: "OK", 400: "Bad Request", 401: "Unauthorized", 402: "Payment Required",
               499: "Fixture Status", 500: "Internal Server Error", 501: "Not Implemented"}
    body = f"synthetic status {status}\n".encode("ascii")
    return (f"HTTP/1.1 {status} {reasons.get(status, 'Fixture Status')}\r\nContent-Type: text/plain\r\n"
            f"Content-Length: {len(body)}\r\n\r\n").encode("ascii") + body


def tls_client_hello(host: str = "portal.lab.test") -> bytes:
    """A parseable TLS ClientHello; no encryption, keys or network connection."""
    name = host.encode("ascii")
    sni = b"\0" + struct.pack("!H", len(name)) + name
    sni = struct.pack("!H", len(sni)) + sni
    extensions = (struct.pack("!HH", 0, len(sni)) + sni
                  + b"\x00\x0a\x00\x04\x00\x02\x00\x17"
                  + b"\x00\x0b\x00\x02\x01\x00"
                  + b"\x00\x0d\x00\x06\x00\x04\x04\x03\x08\x04")
    hello = (b"\x03\x03" + bytes(range(32)) + b"\0" + b"\x00\x02\xc0\x2f"
             + b"\x01\x00" + struct.pack("!H", len(extensions)) + extensions)
    handshake = b"\x01" + len(hello).to_bytes(3, "big") + hello
    return b"\x16\x03\x01" + struct.pack("!H", len(handshake)) + handshake


def pcap(frames, *, start: int = START_SECONDS, step_us: int = STEP_US,
         linktype: int = 1, snaplen: int = 262144) -> bytes:
    """Classic little-endian microsecond PCAP. Items are bytes or (bytes, wirelen)."""
    result = bytearray(struct.pack("<IHHIIII", 0xa1b2c3d4, 2, 4, 0, 0, snaplen, linktype))
    for index, item in enumerate(frames):
        data, wirelen = item if isinstance(item, tuple) else (item, len(item))
        data = bytes(data)
        if wirelen < len(data) or len(data) > snaplen:
            raise ValueError("PCAP caplen/wirelen/snaplen ilişkisi geçersiz")
        seconds, micros = divmod(index * step_us, 1000000)
        result += struct.pack("<IIII", start + seconds, micros, len(data), wirelen) + data
    return bytes(result)


class _Corpus:
    def __init__(self, name):
        self.name, self.frames, self.manifest = name, [], []

    def add(self, frame, note, *, wirelen=None, **fields):
        wirelen = len(frame) if wirelen is None else wirelen
        self.frames.append((frame, wirelen))
        self.manifest.append(dict(id=len(self.frames), note=note, caplen=len(frame),
                                  wirelen=wirelen, time_relative=len(self.frames)-1,
                                  eth_src=":".join(f"{b:02x}" for b in frame[6:12]),
                                  eth_dst=":".join(f"{b:02x}" for b in frame[:6]), **fields))

    def transport(self, proto, sport, dport, *, src=CLIENT, dst=SERVER,
                  payload=b"", flags=0x02, seq=1000, ack=0, note="", vlan=None,
                  vlans=(), frame_length=60, options=b"", **fields):
        version = ipaddress.ip_address(src).version
        segment = (tcp(sport, dport, payload, src=src, dst=dst, flags=flags, seq=seq, ack=ack)
                   if proto == 6 else udp(sport, dport, payload, src=src, dst=dst)
                   if proto == 17 else sctp(sport, dport))
        packet = (ipv4(segment, src, dst, proto, ident=len(self.frames)+1, options=options)
                  if version == 4 else ipv6(segment, src, dst, proto))
        source_mac = DNS_MAC if src in (DNS,"2001:db8::53") else SERVER_MAC if src in (SERVER,SERVER6,"198.51.100.80","198.51.100.81") else CLIENT_MAC
        target_mac = CLIENT_MAC if dst in (CLIENT,CLIENT6,"10.0.0.11","10.0.0.99") else DNS_MAC if dst in (DNS,"2001:db8::53") else SERVER_MAC
        self.add(ethernet(packet, 0x0800 if version == 4 else 0x86dd, src=source_mac, dst=target_mac,
                          vlan=vlan, vlans=vlans, min_length=frame_length), note,
                 ip_version=version, src=src, dst=dst, proto=proto, sport=sport, dport=dport,
                 **({"flags": flags} if proto == 6 else {}),
                 **({"vlan": list(vlans) if vlans else [vlan]} if vlan is not None or vlans else {}), **fields)

    def http_pair(self, *, src=CLIENT, dst=SERVER, sport=41000,
                  uri="/admin", host="portal.lab.test", status=401):
        request = http_request(uri, host)
        self.transport(6, sport, 80, src=src, dst=dst, payload=request, flags=0x18,
                       seq=1, ack=1, note=f"HTTP istek {host}{uri}", http_host=host, http_uri=uri)
        self.transport(6, 80, sport, src=dst, dst=src, payload=http_response(status),
                       flags=0x18, seq=1, ack=1+len(request), note=f"HTTP yanıt {status}", http_status=status)


def _temel():
    c = _Corpus("temel")
    c.add(ethernet(arp(), 0x0806, dst="ff:ff:ff:ff:ff:ff"), "ARP istek", proto="arp", src=CLIENT, dst=SERVER)
    c.add(ethernet(arp(SERVER, CLIENT, opcode=2, sender_mac=SERVER_MAC, target_mac=CLIENT_MAC),
                   0x0806, src=SERVER_MAC, dst=CLIENT_MAC), "ARP yanıt", proto="arp", src=SERVER, dst=CLIENT)
    c.transport(17, 53000, 53, dst=DNS, payload=dns_query(), note="DNS A sorusu", dns_name="portal.lab.test", dns_qtype=1, dns_response=False)
    c.transport(17, 53, 53000, src=DNS, dst=CLIENT, payload=dns_response(), note="DNS A yanıtı", dns_name="portal.lab.test", dns_qtype=1, dns_response=True)
    c.transport(6, 40000, 80, flags=2, seq=1000, note="HTTP akışı SYN")
    c.transport(6, 80, 40000, src=SERVER, dst=CLIENT, flags=0x12, seq=9000, ack=1001, note="HTTP akışı SYN ACK")
    c.transport(6, 40000, 80, flags=0x10, seq=1001, ack=9001, note="HTTP akışı ACK")
    request = http_request()
    c.transport(6, 40000, 80, payload=request, flags=0x18, seq=1001, ack=9001,
                note="HTTP GET /health", http_host="portal.lab.test", http_uri="/health")
    c.transport(6, 80, 40000, src=SERVER, dst=CLIENT, payload=http_response(), flags=0x18,
                seq=9001, ack=1001+len(request), note="HTTP 200 yanıtı", http_status=200)
    c.transport(6, 40001, 443, flags=2, seq=2000, note="TLS akışı SYN")
    c.transport(6, 443, 40001, src=SERVER, dst=CLIENT, flags=0x12, seq=19000, ack=2001, note="TLS akışı SYN ACK")
    c.transport(6, 40001, 443, flags=0x10, seq=2001, ack=19001, note="TLS akışı ACK")
    c.transport(6, 40001, 443, payload=tls_client_hello(), flags=0x18, seq=2001, ack=19001,
                note="TLS ClientHello; yalnız başlık", tls_sni="portal.lab.test")
    c.transport(17, 53001, 53, src=CLIENT6, dst="2001:db8::53", payload=dns_query(qtype=28),
                note="IPv6 DNS AAAA sorusu", dns_name="portal.lab.test", dns_qtype=28, dns_response=False)
    c.transport(6, 40002, 443, src=CLIENT6, dst=SERVER6, flags=2, note="IPv6 TCP SYN")
    c.transport(132, 50000, 3868, note="SCTP INIT")
    c.add(ethernet(ipv4(icmp_echo(), proto=1, ident=17)), "ICMP echo isteği", ip_version=4, src=CLIENT, dst=SERVER, proto=1)
    c.add(ethernet(ipv6(icmp_echo(src=CLIENT6, dst=SERVER6, ipv6_mode=True), next_header=58), 0x86dd),
          "ICMPv6 echo isteği", ip_version=6, src=CLIENT6, dst=SERVER6, proto=58)
    c.http_pair(sport=41000, status=401)
    c.http_pair(sport=41001, uri="/login", status=400)
    c.http_pair(sport=41002, uri="/payment", status=402)
    return c


def _sinirlar():
    c = _Corpus("sinirlar")
    ports = (0, 1, 52, 53, 54, 79, 80, 81, 82, 443, 444, 65534, 65535)
    flag_values = {0: 2, 1: 0x10, 79: 2, 80: 0x12, 81: 0x10, 82: 4, 443: 0x11, 444: 0x18}
    for index, port in enumerate(ports):
        proto = 17 if port in (52, 53, 54) else 6
        payload = dns_query("edge.lab.test") if port == 53 else b""
        c.transport(proto, 42000+index, port, payload=payload, flags=flag_values.get(port, 2),
                    note=f"Hedef port sınırı {port}", **({"dns_name": "edge.lab.test", "dns_qtype": 1, "dns_response": False} if port == 53 else {}))
    c.transport(6, 53, 44000, flags=0x10, note="Kaynak TCP port 53")
    c.transport(17, 53, 44001, src=DNS, dst=CLIENT, payload=dns_response("edge.lab.test"),
                note="Kaynak UDP port 53; DNS yanıtı", dns_name="edge.lab.test", dns_qtype=1, dns_response=True)
    c.transport(132, 44002, 53, note="SCTP port 53")
    for length, source in zip((63,64,65,127,128,129),
                              ("192.0.2.0","192.0.2.255","192.0.1.255","192.0.3.0","192.0.2.1","192.0.2.254")):
        c.transport(17, 45000+length, 9000, src=source, dst="198.51.100.20",
                    payload=b"L"*(length-42), frame_length=length,
                    note=f"Tam {length} bayt; IPv4 CIDR tanığı")
    for source in ("2001:db8:0:ffff:ffff:ffff:ffff:ffff", "2001:db8:1::", "2001:db8:1::3", "2001:db8:1::4"):
        c.transport(17, 46000+len(c.frames), 9000, src=source, dst="2001:db8:ffff::20",
                    note="IPv6 /126 CIDR sınırı")
    fragment = tcp(47000, 80, b"fragmentDATA", seq=5000, flags=0x18)
    c.add(ethernet(ipv4(fragment[:24], ident=700, flags=1)), "IPv4 ilk fragment; TCP başlığı var",
          ip_version=4, src=CLIENT, dst=SERVER, proto=6, sport=47000, dport=80, fragment_offset=0, more_fragments=True)
    c.add(ethernet(ipv4(fragment[24:], ident=700, flags=0, frag_offset=3)), "IPv4 sonraki fragment; port alanı yok",
          ip_version=4, src=CLIENT, dst=SERVER, proto=6, fragment_offset=3, more_fragments=False)
    c.transport(6, 48000, 80, vlan=100, note="VLAN 100 TCP SYN")
    c.transport(6, 48001, 80, vlan=101, note="VLAN 101 TCP SYN")
    c.transport(17, 48002, 53, vlans=(100,200), payload=dns_query("tag.lab.test"),
                note="QinQ 100/200 DNS", dns_name="tag.lab.test", dns_qtype=1, dns_response=False)
    c.transport(6, 48003, 80, options=b"\x01\x01\0\0", note="IPv4 IHL=6; TCP port ofseti değişir", ipv4_ihl=6)
    seg6 = tcp(48004, 443, src=CLIENT6, dst=SERVER6)
    hop = b"\x06\x00\x01\x04\0\0\0\0"  # Next Header TCP, Hdr Ext Len=0, PadN.
    c.add(ethernet(ipv6(hop+seg6, next_header=0), 0x86dd), "IPv6 Hop-by-Hop ardından TCP",
          ip_version=6, src=CLIENT6, dst=SERVER6, proto=6, sport=48004, dport=443, extension="hop-by-hop")
    seg6 = tcp(48005, 443, b"fragmentDATA", src=CLIENT6, dst=SERVER6, flags=0x18)
    for offset, body, more in ((0, seg6[:24], True), (3, seg6[24:], False)):
        ext = struct.pack("!BBHI", 6, 0, (offset << 3) | int(more), 701)
        c.add(ethernet(ipv6(ext+body, next_header=44), 0x86dd), "IPv6 fragment " + ("ilk" if offset==0 else "sonraki"),
              ip_version=6, src=CLIENT6, dst=SERVER6, proto=6, fragment_offset=offset, more_fragments=more,
              **({"sport": 48005, "dport": 443} if offset==0 else {}))
    for name, qtype in (("portal.lab.test",1),("portal.lab.test",28),("other.lab.test",1)):
        c.transport(17, 49000+len(c.frames), 53, dst=DNS, payload=dns_query(name,qtype,0x2000+len(c.frames)),
                    note=f"DNS {name} tür {qtype}", dns_name=name, dns_qtype=qtype, dns_response=False)
    for uri, host in (("/admin","portal.lab.test"),("/health","portal.lab.test"),("/admin","other.lab.test")):
        c.transport(6, 50000+len(c.frames), 80, payload=http_request(uri,host), flags=0x18,
                    note=f"HTTP seçim tanığı {host}{uri}", http_host=host, http_uri=uri)
    for status in (400,401,402,499,500,501):
        c.transport(6, 80, 51000+len(c.frames), src=SERVER, dst=CLIENT, payload=http_response(status), flags=0x18,
                    note=f"HTTP durum sınırı {status}", http_status=status)
    c.add(ethernet(arp(), 0x0806, dst="ff:ff:ff:ff:ff:ff"), "ARP host filtresi tanığı", proto="arp", src=CLIENT, dst=SERVER)
    c.add(ethernet(ipv4(icmp_echo(src="192.0.2.10",dst="198.51.100.10"), "192.0.2.10", "198.51.100.10",1,ident=900)),
          "IPv4 ICMP; taşıma portu yok", ip_version=4, src="192.0.2.10", dst="198.51.100.10", proto=1)
    full = ethernet(ipv4(tcp(52000,443,src="10.0.0.99",dst=SERVER),"10.0.0.99",SERVER,6),min_length=64)
    c.add(full[:36], "Kasıtlı snaplen kesimi; tam frame 64, yakalanan 36 bayt", wirelen=64,
          ip_version=4, src="10.0.0.99", dst=SERVER, proto=6, truncated=True)
    assert len(c.frames) == 50
    return c


def _olay():
    c = _Corpus("olay")
    web, other = "198.51.100.80", "198.51.100.81"
    c.transport(17,53010,53,dst=DNS,payload=dns_query(),note="İstemci portal A sorusu",dns_name="portal.lab.test",dns_qtype=1,dns_response=False)
    c.transport(17,53,53010,src=DNS,dst=CLIENT,payload=dns_response(address=web),note="Portal A yanıtı",dns_name="portal.lab.test",dns_qtype=1,dns_response=True)
    c.transport(6,40100,80,dst=web,flags=2,note="Web SYN")
    c.transport(6,80,40100,src=web,dst=CLIENT,flags=0x12,seq=9000,ack=1001,note="Web SYN ACK")
    c.transport(6,40100,80,dst=web,flags=0x10,seq=1001,ack=9001,note="Web ACK")
    c.http_pair(dst=web,sport=40101,uri="/admin",status=401)
    c.http_pair(dst=web,sport=40102,uri="/health",status=200)
    c.transport(17,53011,53,src="10.0.0.11",dst=DNS,payload=dns_query("other.lab.test",txid=0x1211),note="Diğer istemci DNS",dns_name="other.lab.test",dns_qtype=1,dns_response=False)
    c.transport(17,53,53011,src=DNS,dst="10.0.0.11",payload=dns_response("other.lab.test",other,0x1211),note="Diğer DNS yanıtı",dns_name="other.lab.test",dns_qtype=1,dns_response=True)
    c.http_pair(src="10.0.0.11",dst=other,sport=40103,host="other.lab.test",status=401)
    c.http_pair(dst=web,sport=40104,uri="/login",status=500)
    c.transport(6,40105,443,dst=web,payload=tls_client_hello(),flags=0x18,note="Portal TLS ClientHello",tls_sni="portal.lab.test")
    c.transport(17,53012,54,dst=DNS,payload=dns_query(),note="DNS benzeri veri fakat UDP port 54")
    c.transport(6,40106,443,src=CLIENT6,dst="2001:db8::80",note="IPv6 TCP SYN")
    c.add(ethernet(arp(target_ip="10.0.0.1"),0x0806,dst="ff:ff:ff:ff:ff:ff"),"ARP ağ geçidi sorusu",proto="arp",src=CLIENT,dst="10.0.0.1")
    c.transport(132,50001,80,src="10.0.0.11",dst=web,note="SCTP port 80; TCP değil")
    c.http_pair(dst=web,sport=40107,uri="/administration",status=402)
    c.http_pair(dst=web,sport=40108,host="other.lab.test",status=401)
    c.transport(17,53013,53,src="10.0.0.99",dst=DNS,payload=dns_query("Portal.Lab.Test"),
                note="Farklı istemci ve harf durumu DNS",dns_name="Portal.Lab.Test",dns_qtype=1,dns_response=False)
    return c


@lru_cache(maxsize=1)
def _corpora():
    return {c.name: c for c in (_temel(), _sinirlar(), _olay())}


def captures() -> dict[str, bytes]:
    """Return a fresh mapping from stable corpus names to immutable PCAP bytes."""
    try:
        from . import packet_advanced_fixtures as advanced
    except ImportError:
        import packet_advanced_fixtures as advanced
    return {**{name: pcap(corpus.frames) for name, corpus in _corpora().items()}, **advanced.captures()}


def get_capture(name: str) -> bytes:
    if name.endswith(".pcap"):
        name = name[:-5]
    try:
        return captures()[name]
    except KeyError:
        raise ValueError("Bilinmeyen capture; temel, sinirlar veya olay seç") from None


def describe(name: str) -> list[dict]:
    """Independent metadata copy; id equals TShark frame.number."""
    if name.endswith(".pcap"):
        name = name[:-5]
    if name not in _corpora():
        try:
            from . import packet_advanced_fixtures as advanced
        except ImportError:
            import packet_advanced_fixtures as advanced
        return advanced.describe(name)
    try:
        return copy.deepcopy(_corpora()[name].manifest)
    except KeyError:
        raise ValueError("Bilinmeyen capture; temel, sinirlar veya olay seç") from None


# Short alias for callers building an additional native regression PCAP.
pcap_bytes = pcap
