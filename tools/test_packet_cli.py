"""Actual two-pass dissection, Follow Stream, object export and CLI boundary."""
import base64
import json
from pathlib import Path
import re
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from sandbox import packet_engine as e
from sandbox import packet_cli as cli


class PacketCli(unittest.TestCase):
    def run_cli(self,code,name='tcp-sirasiz'):
        return e.run(code,json.dumps({'dil':'tshark','kayit':name}))

    def test_reassembly_is_native_and_missing_data_is_not_invented(self):
        code='tshark -r secili -2 -o tcp.reassemble_out_of_order:TRUE -Y http.response -T fields -e frame.number'
        self.assertEqual(self.run_cli(code)['stdout'].splitlines(),['8'])
        self.assertEqual(self.run_cli(code.replace(':TRUE',':FALSE'))['stdout'].splitlines(),[])
        self.assertEqual(self.run_cli(code,'tcp-kayip')['stdout'].splitlines(),[])

    def test_export_reconstructs_exact_bytes_without_duplicates(self):
        code='tshark -r secili -2 -o tcp.reassemble_out_of_order:TRUE -q --export-objects http,sonuc'
        for name in ('tcp-tam','tcp-tekrar','tcp-sirasiz'):
            result=self.run_cli(code,name)
            self.assertEqual(len(result['exports']),1)
            self.assertEqual(base64.b64decode(result['exports'][0]['base64']),b'PAFTA-TCP-LAB')
            self.assertTrue(result['tablolar'])
        self.assertEqual(self.run_cli(code,'tcp-kayip')['exports'],[])

    def test_follow_stream_reorders_and_deduplicates_server_bytes(self):
        code='tshark -r secili -2 -q -z follow,tcp,raw,0'
        for name in ('tcp-tam','tcp-tekrar','tcp-sirasiz','tcp-kayip'):
            out=self.run_cli(code,name)['stdout']
            server=b''.join(bytes.fromhex(line.strip()) for line in out.splitlines()
                            if line.startswith('\t') and re.fullmatch(r'[0-9a-fA-F]+',line.strip()))
            body=server.split(b'\r\n\r\n',1)[1]
            self.assertEqual(body,b'PAFTA-' if name=='tcp-kayip' else b'PAFTA-TCP-LAB')

    def test_arbitrary_paths_live_interfaces_and_preferences_rejected(self):
        for code in ('tshark -r C:/private.pcap','tshark -r secili -i 1',
                     'tshark -r secili -w ../out.pcap','tshark -r secili --export-objects http,../out',
                     'tshark -r secili -o tls.keylog_file:C:/private.keys',
                     'cmd /c tshark -r secili','tshark -r secili -z credentials'):
            with self.subTest(code=code),self.assertRaises(e.PacketError):cli.parse_command(code)


if __name__=='__main__':unittest.main(verbosity=2)
