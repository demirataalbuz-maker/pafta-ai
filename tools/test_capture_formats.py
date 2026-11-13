"""Independent framing and native filter regression for heterogeneous PCAPNG."""
from fractions import Fraction
from pathlib import Path
import struct
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sandbox import packet_engine as engine
from sandbox.capture_formats import parse_capture, CaptureError
from sandbox.packet_advanced_fixtures import mixed_capture,pcapng
from sandbox import packet_fixtures as pf


class CaptureFormats(unittest.TestCase):
    def test_mixed_interfaces_use_real_dlt(self):
        raw=mixed_capture()
        for dialect,query in [('wireshark','tcp.dstport == 80'),('bpf','tcp dst port 80')]:
            self.assertEqual(engine.evaluate(query,raw,dialect),[2,5,8,11])
        frames=parse_capture(raw)
        self.assertEqual([f.linktype for f in frames[:12]],[1]*3+[101]*3+[113]*3+[276]*3)
        self.assertEqual(frames[3].timestamp,Fraction(1700000003)+Fraction(1,10**9))
        self.assertEqual(frames[6].timestamp,Fraction(1700000006)+Fraction(1,1024))
        self.assertEqual((len(frames[-1].data),frames[-1].wirelen),(30,128))
        self.assertEqual(engine.evaluate('len >= 128',raw,'bpf'),[13])

    def test_sections_endianness_and_exact_resolution(self):
        eth=pf.ethernet(pf.ipv4(pf.tcp(50000,80),pf.CLIENT,pf.SERVER,6))
        raw=pcapng([(0,1000001,eth,len(eth))])+pcapng([(0,1000000001,eth,len(eth))],((1,65535,9),),'>')
        frames=parse_capture(raw)
        self.assertEqual([(f.section,f.interface) for f in frames],[(0,0),(1,0)])
        self.assertEqual([f.timestamp for f in frames],[Fraction(1000001,10**6),Fraction(1000000001,10**9)])
        self.assertEqual(engine.evaluate('tcp dst port 80',raw,'bpf'),[1,2])
        self.assertEqual(engine.evaluate('tcp.dstport == 80',raw),[1,2])

    def test_malformed_blocks_are_rejected(self):
        raw=mixed_capture()
        invalid=[raw[:27],raw[:-1],raw+b'x']
        for offset,value in ((4,27),(24,99),(36,147),(40,0xffffffff)):
            bad=bytearray(raw);struct.pack_into('<I',bad,offset,value);invalid.append(bytes(bad))
        # A packet claiming nonexistent interface 99.
        bad=bytearray(raw);pos=28
        while struct.unpack_from('<I',bad,pos)[0]!=6:
            pos+=struct.unpack_from('<I',bad,pos+4)[0]
        struct.pack_into('<I',bad,pos+8,99);invalid.append(bytes(bad))
        for data in invalid:
            with self.subTest(length=len(data)),self.assertRaises(CaptureError):
                parse_capture(data)

    def test_unsupported_linktype_is_explicit(self):
        with self.assertRaisesRegex(CaptureError,'LINKTYPE 147'):
            parse_capture(pcapng([],((147,65535,6),)))
        with self.assertRaises(ValueError):
            engine.evaluate('ether host 02:00:00:00:00:10',mixed_capture(),'bpf')
        with self.assertRaises(ValueError):
            engine.evaluate('ether host 02:00:00:00:00:10',pcapng([],((101,65535,6),)),'bpf')


if __name__=='__main__':
    unittest.main(verbosity=2)
