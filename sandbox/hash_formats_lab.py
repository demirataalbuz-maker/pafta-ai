# -*- coding: utf-8 -*-
"""PU17: çevrimdışı parola özeti biçimleri ve doğrulanabilir MD4/NTLM vektörü.

Parola kırma, wordlist, GPU, ağ, alt süreç veya sistem parola deposu erişimi yoktur.
"""
from pathlib import Path
import json
import shutil
import struct

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tracks" / "purple" / "fixtures" / "pu17_hash_formats"
DOSYALAR = ("hashes.json", "shadow.txt", "README.md", "ag_bicimleri.json")


def hazirla(hedef=None):
    """Yalnız sentetik/test fixture'larını ``hedef/hash_formats`` altına kopyala."""
    klasor = Path(hedef or Path.cwd()) / "hash_formats"
    klasor.mkdir(parents=True, exist_ok=True)
    for ad in DOSYALAR:
        shutil.copyfile(FIXTURE / ad, klasor / ad)
    return klasor


def json_yukle(yol):
    with Path(yol).open(encoding="utf-8") as akim:
        return json.load(akim)


def _lrot(deger, miktar):
    deger &= 0xFFFFFFFF
    return ((deger << miktar) | (deger >> (32 - miktar))) & 0xFFFFFFFF


def md4(veri):
    """RFC 1320 MD4; bu dersin küçük, bağımsız test-vektörü implementasyonu."""
    if not isinstance(veri, bytes):
        raise TypeError("MD4 girdisi bytes olmalı")
    mesaj = bytearray(veri)
    bit_uzunlugu = (8 * len(mesaj)) & 0xFFFFFFFFFFFFFFFF
    mesaj.append(0x80)
    while len(mesaj) % 64 != 56:
        mesaj.append(0)
    mesaj += struct.pack("<Q", bit_uzunlugu)
    a, b, c, d = 0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476

    def f(x, y, z):
        return (x & y) | (~x & z)

    def g(x, y, z):
        return (x & y) | (x & z) | (y & z)

    def h(x, y, z):
        return x ^ y ^ z

    for ofset in range(0, len(mesaj), 64):
        x = struct.unpack("<16I", mesaj[ofset:ofset + 64])
        aa, bb, cc, dd = a, b, c, d
        for i, s in enumerate((3, 7, 11, 19) * 4):
            k = i
            if i % 4 == 0:
                a = _lrot(a + f(b, c, d) + x[k], s)
            elif i % 4 == 1:
                d = _lrot(d + f(a, b, c) + x[k], s)
            elif i % 4 == 2:
                c = _lrot(c + f(d, a, b) + x[k], s)
            else:
                b = _lrot(b + f(c, d, a) + x[k], s)
        sira2 = (0, 4, 8, 12, 1, 5, 9, 13, 2, 6, 10, 14, 3, 7, 11, 15)
        for i, k in enumerate(sira2):
            s = (3, 5, 9, 13)[i % 4]
            if i % 4 == 0:
                a = _lrot(a + g(b, c, d) + x[k] + 0x5A827999, s)
            elif i % 4 == 1:
                d = _lrot(d + g(a, b, c) + x[k] + 0x5A827999, s)
            elif i % 4 == 2:
                c = _lrot(c + g(d, a, b) + x[k] + 0x5A827999, s)
            else:
                b = _lrot(b + g(c, d, a) + x[k] + 0x5A827999, s)
        sira3 = (0, 8, 4, 12, 2, 10, 6, 14, 1, 9, 5, 13, 3, 11, 7, 15)
        for i, k in enumerate(sira3):
            s = (3, 9, 11, 15)[i % 4]
            if i % 4 == 0:
                a = _lrot(a + h(b, c, d) + x[k] + 0x6ED9EBA1, s)
            elif i % 4 == 1:
                d = _lrot(d + h(a, b, c) + x[k] + 0x6ED9EBA1, s)
            elif i % 4 == 2:
                c = _lrot(c + h(d, a, b) + x[k] + 0x6ED9EBA1, s)
            else:
                b = _lrot(b + h(c, d, a) + x[k] + 0x6ED9EBA1, s)
        a = (a + aa) & 0xFFFFFFFF
        b = (b + bb) & 0xFFFFFFFF
        c = (c + cc) & 0xFFFFFFFF
        d = (d + dd) & 0xFFFFFFFF
    return struct.pack("<4I", a, b, c, d).hex()


def ntlm_test_ozeti(parola):
    """Yalnız bilinen sentetik test girdisi için NT özetini hesapla."""
    if not isinstance(parola, str):
        raise TypeError("Test parolası metin olmalı")
    return md4(parola.encode("utf-16-le"))
