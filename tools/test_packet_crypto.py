"""Actual TShark decryption and absence witnesses, no network traffic."""
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from sandbox import packet_engine as e
from sandbox import packet_advanced_fixtures as af


class CryptoPackets(unittest.TestCase):
    def test_tls_visibility_and_status_boundaries(self):
        for key in ('yok','yanlis','tls-h2'):
            self.assertEqual(e.evaluate('tls.handshake.extensions_server_name == "pafta.lab.test"','tls-h2',key=key),[4])
            self.assertEqual(e.evaluate('http2.headers.status == 201','tls-h2',key=key),[18] if key=='tls-h2' else [])
        self.assertEqual(e.evaluate('http2.headers.status == 200','tls-h2',key='tls-h2'),[14])
        self.assertEqual(e.evaluate('http2.headers.status == 202','tls-h2',key='tls-h2'),[22])
        self.assertEqual(e.evaluate('http2.headers.status == 201',af.shifted_capture('tls-h2'),key='tls-h2'),[19])

    def test_quic_initial_does_not_imply_stream_visibility(self):
        query='quic.stream_data == 50:41:46:54:41:2d:51:55:49:43:2d:4c:41:42'
        for key in ('yok','yanlis','quic-lab'):
            self.assertEqual(e.evaluate('quic.long.packet_type == 0','quic-lab',key=key),[1,2,4])
            self.assertEqual(e.evaluate(query,'quic-lab',key=key),[8] if key=='quic-lab' else [])
        self.assertEqual(e.evaluate(query,af.shifted_capture('quic-lab'),key='quic-lab'),[9])
        self.assertEqual(e.evaluate('http3','quic-lab',key='quic-lab'),[])

    def test_user_key_paths_and_bpf_decryption_are_rejected(self):
        for key in ('C:/Users/keylog.txt','../tls-h2.keys',None,[]):
            import json
            with self.assertRaises(e.PacketError):
                e.options(json.dumps({'anahtar':key}))
        with self.assertRaises(e.PacketError):
            e.evaluate('tcp','tls-h2','bpf',key='tls-h2')


if __name__=='__main__':unittest.main(verbosity=2)
