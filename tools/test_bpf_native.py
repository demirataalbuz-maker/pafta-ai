"""Native libpcap semantic checks. No capture interfaces or network requests."""
import ctypes as ct
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from sandbox import bpf_native as native


def checksum(raw):
    raw += b"\0" * (len(raw) % 2)
    total = sum(struct.unpack("!" + str(len(raw) // 2) + "H", raw))
    while total >> 16:
        total = (total & 0xffff) + (total >> 16)
    return (~total) & 0xffff


def ipv4(proto=6, sport=50000, dport=443, flags=2, payload=b"", fragment=0, vlan=None):
    src = bytes((192, 0, 2, 1))
    dst = bytes((198, 51, 100, 2))
    if proto == 6:
        body = struct.pack("!HHIIBBHHH", sport, dport, 1, 0, 80, flags, 4096, 0, 0) + payload
        check_at = 16
    else:
        body = struct.pack("!HHHH", sport, dport, 8 + len(payload), 0) + payload
        check_at = 6
    pseudo = src + dst + struct.pack("!BBH", 0, proto, len(body))
    body = body[:check_at] + struct.pack("!H", checksum(pseudo + body)) + body[check_at + 2:]
    ip = struct.pack("!BBHHHBBH4s4s", 69, 0, 20 + len(body), 1, fragment, 64, proto, 0, src, dst)
    ip = ip[:10] + struct.pack("!H", checksum(ip)) + ip[12:]
    ether = bytes.fromhex("020000000002020000000001")
    ether += struct.pack("!HHH", 0x8100, vlan, 0x0800) if vlan is not None else b"\x08\x00"
    return ether + ip + body


def pcap(packets, order="<", nano=False, snaplen=65535, linktype=1):
    magic = 0xa1b23c4d if nano else 0xa1b2c3d4
    raw = struct.pack(order + "IHHIIII", magic, 2, 4, 0, 0, snaplen, linktype)
    for index, item in enumerate(packets, 1):
        packet, wirelen = item if isinstance(item, tuple) else (item, len(item))
        raw += struct.pack(order + "IIII", index, 123456789 if nano else 123456,
                           len(packet), wirelen) + packet
    return raw


class BpfNativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not native.available():
            native.version()  # Fail actionably; do not silently skip the native suite.

    def test_version_and_native_header_abi(self):
        self.assertIn("libpcap version 1.10.6", native.version())
        self.assertEqual((ct.sizeof(native._PcapHeader), native._PcapHeader.caplen.offset,
                          native._PcapHeader.len.offset), (16, 8, 12))
        # Observe a header allocated by C, rather than only comparing Python
        # fields to Python's own layout. This checks the pinned DLL's ABI.
        dll = native._library()
        dll.pcap_open_offline.argtypes = [ct.c_char_p, ct.c_char_p]
        dll.pcap_open_offline.restype = ct.c_void_p
        dll.pcap_next_ex.argtypes = [ct.c_void_p, ct.POINTER(ct.c_void_p), ct.POINTER(ct.c_void_p)]
        dll.pcap_next_ex.restype = ct.c_int
        with tempfile.TemporaryDirectory(prefix="pafta_bpf_abi_") as directory:
            path = Path(directory) / "abi.pcap"
            path.write_bytes(pcap([(b"X" * 14, 70)]))
            error = ct.create_string_buffer(256)
            handle = dll.pcap_open_offline(os.fsencode(path), error)
            self.assertTrue(handle, error.value)
            try:
                header, data = ct.c_void_p(), ct.c_void_p()
                self.assertEqual(dll.pcap_next_ex(handle, ct.byref(header), ct.byref(data)), 1)
                self.assertEqual(struct.unpack("<IIII", ct.string_at(header, 16)), (1, 123456, 14, 70))
            finally:
                dll.pcap_close(handle)

    def test_protocol_port_direction_and_multiple_matches(self):
        raw = pcap([ipv4(dport=80), ipv4(dport=443), ipv4(proto=17, dport=53), ipv4(sport=443, dport=80)])
        for expression, wanted in (("tcp", [1, 2, 4]), ("udp", [3]),
                                   ("tcp dst port 443", [2]), ("tcp src port 443", [4]),
                                   ("port 443", [2, 4]), ("src host 192.0.2.1", [1, 2, 3, 4]),
                                   ("dst net 198.51.100.0/24", [1, 2, 3, 4]),
                                   ("host 203.0.113.1", [])):
            self.assertEqual(native.evaluate(expression, raw), wanted, expression)

    def test_portrange_inclusive_boundaries(self):
        raw = pcap([ipv4(dport=port) for port in (442, 443, 444, 445)])
        self.assertEqual(native.evaluate("tcp dst portrange 443-444", raw), [2, 3])

    def test_native_and_or_equal_precedence(self):
        raw = pcap([ipv4(dport=80), ipv4(dport=443), ipv4(proto=17, dport=53)])
        self.assertEqual(native.evaluate("tcp or udp and port 53", raw), [3])
        self.assertEqual(native.evaluate("tcp or (udp and port 53)", raw), [1, 2, 3])
        self.assertEqual(native.evaluate("not tcp and port 53", raw), [3])

    def test_less_greater_include_exact_wire_length(self):
        raw = pcap([(ipv4(), size) for size in (99, 100, 101)])
        self.assertEqual(native.evaluate("less 100", raw), [1, 2])
        self.assertEqual(native.evaluate("greater 100", raw), [2, 3])
        self.assertEqual(native.evaluate("len = 100", raw), [2])

    def test_wirelen_and_caplen_are_not_interchangeable(self):
        packet = ipv4()
        raw = pcap([(packet[:14], 100), (packet, 100)])
        self.assertEqual(native.evaluate("len >= 100", raw), [1, 2])
        self.assertEqual(native.evaluate("ip[19] = 2", raw), [2])
        self.assertEqual(native.evaluate("tcp dst port 443", raw), [2])
        self.assertEqual(native.evaluate("ether[13] = 0", raw), [1, 2])
        self.assertEqual(native.evaluate("ether[14] = 0", raw), [])

    def test_tcp_flags_and_noninitial_ipv4_fragments(self):
        raw = pcap([ipv4(flags=2), ipv4(flags=18), ipv4(flags=16), ipv4(flags=2, fragment=1)])
        self.assertEqual(native.evaluate("tcp[tcpflags] & tcp-syn != 0", raw), [1, 2])
        self.assertEqual(native.evaluate("tcp[tcpflags] = tcp-syn", raw), [1])
        self.assertEqual(native.evaluate("tcp dst port 443", raw), [1, 2, 3])

    def test_vlan_offsets_are_native(self):
        raw = pcap([ipv4(), ipv4(vlan=100), ipv4(vlan=200)])
        self.assertEqual(native.evaluate("tcp dst port 443", raw), [1])
        self.assertEqual(native.evaluate("vlan 100 and tcp dst port 443", raw), [2])

    def test_byte_orders_and_timestamp_precisions(self):
        for order in ("<", ">"):
            for nano in (False, True):
                with self.subTest(order=order, nano=nano):
                    self.assertEqual(native.evaluate("tcp port 443", pcap([ipv4()], order, nano)), [1])

    def test_empty_capture_still_compiles_and_empty_filter_matches(self):
        self.assertEqual(native.evaluate("tcp", pcap([])), [])
        self.assertEqual(native.evaluate("", pcap([ipv4(), ipv4(proto=17)])), [1, 2])
        with self.assertRaises(native.BpfFilterError):
            native.evaluate("tcp and", pcap([]))

    def test_invalid_syntax_and_no_assumed_broadcast_mask(self):
        for expression in ("tcp and", "tcp port 70000", "ip broadcast"):
            with self.subTest(expression=expression), self.assertRaises(native.BpfFilterError):
                native.evaluate(expression, pcap([ipv4()]))

    def test_name_resolution_and_nul_are_rejected_before_native(self):
        for expression in ("host example.com", "host localhost", "host tcp.udp", "port https",
                           'host "tcp"', r"host \tcp", "tcp\0 or udp", "host 999.1.1.1"):
            with self.subTest(expression=expression), self.assertRaises(native.BpfFilterError):
                native.evaluate(expression, pcap([ipv4()]))

    def test_raw_linktype_101_is_supported(self):
        self.assertEqual(native.evaluate("tcp dst port 443", pcap([ipv4()[14:]], linktype=101)), [1])
        self.assertEqual(native.evaluate("tcp dst port 80", pcap([ipv4()[14:]], linktype=101)), [])

    def test_bad_file_headers_lengths_and_incomplete_records(self):
        good = pcap([ipv4()])
        examples = [b"", b"\x0a\x0d\x0d\x0a" + good[4:], good[:23], good + b"x",
                    good[:-1], pcap([ipv4()], linktype=147), pcap([ipv4()], snaplen=1),
                    pcap([(ipv4(), 1)])]
        for raw in examples:
            with self.subTest(length=len(raw)), self.assertRaises(native.PcapFormatError):
                native.evaluate("tcp", raw)


if __name__ == "__main__":
    unittest.main()
