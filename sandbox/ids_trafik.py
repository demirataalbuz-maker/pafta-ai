# -*- coding: utf-8 -*-
"""Ağ Tespiti yolunun trafik üreticisi: JSON bir tariften zararsız, sentetik bir PCAP yazar.

WSL'de Scapy ile çalışır (sandbox/ids_lab.py çağırır):

    python3 ids_trafik.py tarif.json cikti.pcap

Tarif bir akış listesidir; her akış bir sözlük:

    {"tur": "http", "zaman": "2026-10-19 09:00:00", "istemci": "10.0.1.15", "sunucu": "203.0.113.10",
     "port": 80, "istek": "GET / HTTP/1.1\\r\\nHost: ornek.test\\r\\n\\r\\n", "yanit": "HTTP/1.1 200 OK\\r\\n..."}
    {"tur": "dns", "zaman": ..., "istemci": ..., "sunucu": ..., "ad": "ornek.test", "cevap": "203.0.113.10"}
        (cevap yoksa NXDOMAIN; "yanit": false ise yanıt hiç gelmez)
    {"tur": "tls", "zaman": ..., "istemci": ..., "sunucu": ..., "port": 443, "sni": "ornek.test"}
    {"tur": "tcp", "zaman": ..., "istemci": ..., "sunucu": ..., "port": 22, "veri": "SSH-2.0-OpenSSH_9.6\\r\\n"}
    {"tur": "udp", "zaman": ..., "istemci": ..., "sunucu": ..., "port": 514, "veri": "..."}

TCP akışları üçlü el sıkışma, veri ve FIN ile kapanış içerir; zamanlar UTC'dir.
"""
import calendar
import json
import random
import sys
import time

from scapy.all import DNS, DNSQR, DNSRR, IP, TCP, UDP, Ether, Raw, wrpcap  # noqa: E402
from scapy.layers.tls.extensions import ServerName, TLS_Ext_ServerName  # noqa: E402
from scapy.layers.tls.handshake import TLSClientHello  # noqa: E402
from scapy.layers.tls.record import TLS  # noqa: E402

MAC_I, MAC_S = "02:00:00:00:00:01", "02:00:00:00:00:02"


def _zaman(metin):
    return calendar.timegm(time.strptime(metin, "%Y-%m-%d %H:%M:%S"))


def _tcp_oturum(t, istemci, sunucu, port, gidenler, gelenler, rnd):
    """el sıkışma, sırayla istemci→sunucu ve sunucu→istemci verisi, FIN/ACK → [(zaman, paket)]."""
    sport = rnd.randint(40000, 60000)
    ci, si = rnd.randint(1, 2**31), rnd.randint(1, 2**31)
    e = lambda: Ether(src=MAC_I, dst=MAC_S)  # noqa: E731
    r = lambda: Ether(src=MAC_S, dst=MAC_I)  # noqa: E731
    paket = []
    adim = 0.001

    def ekle(p):
        paket.append((t + adim * len(paket), p))

    ekle(e() / IP(src=istemci, dst=sunucu) / TCP(sport=sport, dport=port, flags="S", seq=ci))
    ekle(r() / IP(src=sunucu, dst=istemci) / TCP(sport=port, dport=sport, flags="SA", seq=si, ack=ci + 1))
    ci += 1
    si += 1
    ekle(e() / IP(src=istemci, dst=sunucu) / TCP(sport=sport, dport=port, flags="A", seq=ci, ack=si))
    for giden, gelen in zip(gidenler, gelenler + [b""] * (len(gidenler) - len(gelenler))):
        if giden:
            ekle(e() / IP(src=istemci, dst=sunucu) / TCP(sport=sport, dport=port, flags="PA", seq=ci, ack=si) / Raw(giden))
            ci += len(giden)
            ekle(r() / IP(src=sunucu, dst=istemci) / TCP(sport=port, dport=sport, flags="A", seq=si, ack=ci))
        if gelen:
            ekle(r() / IP(src=sunucu, dst=istemci) / TCP(sport=port, dport=sport, flags="PA", seq=si, ack=ci) / Raw(gelen))
            si += len(gelen)
            ekle(e() / IP(src=istemci, dst=sunucu) / TCP(sport=sport, dport=port, flags="A", seq=ci, ack=si))
    ekle(e() / IP(src=istemci, dst=sunucu) / TCP(sport=sport, dport=port, flags="FA", seq=ci, ack=si))
    ekle(r() / IP(src=sunucu, dst=istemci) / TCP(sport=port, dport=sport, flags="FA", seq=si, ack=ci + 1))
    ekle(e() / IP(src=istemci, dst=sunucu) / TCP(sport=sport, dport=port, flags="A", seq=ci + 1, ack=si + 1))
    return paket


def _bayt(metin):
    return metin.encode("utf-8") if isinstance(metin, str) else bytes(metin)


def uret(tarif, tohum=7):
    rnd = random.Random(tohum)
    paketler = []
    for a in tarif:
        t = _zaman(a["zaman"])
        tur = a["tur"]
        if tur == "http":
            paketler += _tcp_oturum(t, a["istemci"], a["sunucu"], a.get("port", 80),
                                    [_bayt(a["istek"])], [_bayt(a.get("yanit", ""))], rnd)
        elif tur == "tcp":
            paketler += _tcp_oturum(t, a["istemci"], a["sunucu"], a["port"], [_bayt(a.get("veri", ""))],
                                    [_bayt(a.get("yanit", ""))], rnd)
        elif tur == "tls":
            hello = TLS(msg=[TLSClientHello(ext=[TLS_Ext_ServerName(servernames=[ServerName(servername=a["sni"])])])])
            paketler += _tcp_oturum(t, a["istemci"], a["sunucu"], a.get("port", 443), [bytes(hello)], [], rnd)
        elif tur in ("dns", "udp"):
            sport = rnd.randint(40000, 60000)
            ileri = Ether(src=MAC_I, dst=MAC_S) / IP(src=a["istemci"], dst=a["sunucu"])
            geri = Ether(src=MAC_S, dst=MAC_I) / IP(src=a["sunucu"], dst=a["istemci"])
            if tur == "dns":
                kimlik = rnd.randint(1, 65535)
                soru = DNSQR(qname=a["ad"], qtype=a.get("tip", "A"))
                paketler.append((t, ileri / UDP(sport=sport, dport=53) / DNS(id=kimlik, rd=1, qd=soru)))
                if a.get("yanit") is False:          # yanıtsız sorgu: dns.log'da rcode alanı olmaz
                    continue
                cevap = a.get("cevap")
                yanit = DNS(id=kimlik, qr=1, rd=1, ra=1, qd=soru, rcode=0 if cevap else 3,
                            an=DNSRR(rrname=a["ad"], type="A", ttl=300, rdata=cevap) if cevap else None)
                paketler.append((t + 0.02, geri / UDP(sport=53, dport=sport) / yanit))
            else:
                paketler.append((t, ileri / UDP(sport=sport, dport=a["port"]) / Raw(_bayt(a.get("veri", "")))))
        else:
            raise ValueError(f"bilinmeyen akış türü: {tur}")
    paketler.sort(key=lambda z: z[0])
    sonuc = []
    for t, p in paketler:
        p.time = t
        sonuc.append(p)
    return sonuc


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as f:
        tarif = json.load(f)
    wrpcap(sys.argv[2], uret(tarif))
    print(len(tarif))
