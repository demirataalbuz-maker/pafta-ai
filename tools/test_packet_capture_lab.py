"""Actual root-owned Kali loopback capture: bounds, isolation and cleanup."""
import base64
from pathlib import Path
import sys
import time
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from sandbox import packet_capture_lab as lab
from sandbox import packet_engine as e


class CaptureLab(unittest.TestCase):
    def test_actual_snaplen_boundary_and_foreign_port_exclusion(self):
        for snap,expected in ((63,[63,63,63]),(64,[63,64,64]),(65,[63,64,65])):
            r=lab.run(f'tcpdump -i lo -nn -s {snap} -c 3 -w sonuc.pcap udp')
            self.assertEqual(r['exports'][0]['caplens'],expected)
            self.assertEqual(r['exports'][0]['wirelens'],[63,64,65])
            self.assertEqual(r['runtime']['excluded_noise'],3)
            self.assertTrue(r['runtime']['reaped'])
            self.assertTrue(r['runtime']['linux_directory'].startswith('/tmp/'))
            raw=base64.b64decode(r['exports'][0]['base64'])
            self.assertEqual(e.evaluate('udp[8] == 0x4e',raw,'bpf'),[])

    def test_actual_rotation_and_size_bound(self):
        r=lab.run('tcpdump -i lo -nn -s 0 -c 20 -C 1 -W 2 -w sonuc.pcap udp','donusum')
        self.assertEqual([f['count'] for f in r['exports']],[17,3])
        self.assertTrue(all(f['caplens']==f['wirelens'] for f in r['exports']))
        self.assertLess(sum(f['size'] for f in r['exports']),2_000_000)
        self.assertTrue(r['runtime']['reaped'])

    def test_rejected_capture_is_bounded(self):
        start=time.monotonic()
        with self.assertRaisesRegex(e.PacketError,'bounded tcpdump'):
            lab.run('tcpdump -i lo -nn -s 64 -c 3 -w sonuc.pcap "udp[8] == 0"')
        self.assertLess(time.monotonic()-start,15)

    def test_external_interface_path_and_command_rejected(self):
        for code in ('tcpdump -i eth0 -nn -s 64 -c 3 -w sonuc.pcap udp',
                     'tcpdump -i lo -nn -s 64 -c 3 -w /tmp/other.pcap udp',
                     'tcpdump -i lo -nn -s 64 -c 3 -w sonuc.pcap -z sh udp',
                     'tcpdump -i lo -nn -s 64 -c 3 -w sonuc.pcap "udp) or ip or (udp"',
                     'tcpdump -i lo -nn -s 64 -c 3 -w sonuc.pcap host example.com'):
            with self.assertRaises(ValueError):lab.parse_command(code,'kisa')


if __name__=='__main__':unittest.main(verbosity=2)
