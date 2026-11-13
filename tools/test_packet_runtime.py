"""Native filter integration, using a tiny independent Ethernet/IPv4 corpus."""
import base64
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.runners import get
from sandbox import packet_engine as engine


def corpus():
    header = struct.pack("<IHHIIII", 0xa1b2c3d4, 2, 4, 0, 0, 65535, 1)
    frames = []
    # Source/destination semantics, exact numeric boundaries, and absent fields.
    for index, (proto, src, dst, length) in enumerate([
            (6, 50000, 79, 63), (6, 50000, 80, 64), (6, 80, 50000, 65),
            (6, 50000, 81, 127), (17, 50000, 53, 128), (1, 0, 0, 129)]):
        transport = (struct.pack("!HHIIBBHHH", src, dst, index, 0, 0x50, 2, 8192, 0, 0) if proto == 6
                     else struct.pack("!HHHH", src, dst, length - 34, 0) if proto == 17 else b"\x08\0\0\0\0\0\0\0")
        payload = transport + b"X" * (length - 34 - len(transport))
        ip = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 20 + len(payload), index, 0, 64, proto, 0,
                         bytes([192, 0, 2, 1]), bytes([198, 51, 100, 1]))
        frame = bytes.fromhex("0200000000020200000000010800") + ip + payload
        frames.append(struct.pack("<IIII", 1700000000 + index, 0, len(frame), len(frame)) + frame)
    return header + b"".join(frames)


def encoded(raw, **extra):
    return json.dumps(dict(pcap_base64=base64.b64encode(raw).decode(), **extra))


def one_frame(packet, wirelen=None, order="<", nano=False):
    magic = 0xa1b23c4d if nano else 0xa1b2c3d4
    return (struct.pack(order + "IHHIIII", magic, 2, 4, 0, 0, 65535, 1)
            + struct.pack(order + "IIII", 1700000000, 123456789 if nano else 123456,
                          len(packet), len(packet) if wirelen is None else wirelen) + packet)


def pcapng():
    # Independent PCAPNG byte fixture, not the production generator.
    raw = corpus()
    packet = raw[40:40 + struct.unpack_from("<I", raw, 32)[0]]
    padded = packet + b"\0" * (-len(packet) % 4)
    size = 32 + len(padded)
    section = struct.pack("<IIIHHqI", 0x0a0d0d0a, 28, 0x1a2b3c4d, 1, 0, -1, 28)
    interface = struct.pack("<IIHHII", 1, 20, 1, 0, 65535, 20)
    enhanced = (struct.pack("<IIIIIII", 6, size, 0, 0, 0, len(packet), len(packet))
                + padded + struct.pack("<I", size))
    return section + interface + enhanced


class PacketRuntimeTests(unittest.TestCase):
    def test_native_backends_select_ports(self):
        raw = corpus()
        self.assertEqual(engine.evaluate("tcp.dstport == 80", raw), [2])
        self.assertEqual(engine.evaluate("tcp dst port 80", raw, "bpf"), [2])
        self.assertEqual(engine.evaluate("tcp port 80", raw, "bpf"), [2, 3])

    def test_length_boundaries_both_dialects(self):
        raw = corpus()
        self.assertEqual(engine.evaluate("frame.len <= 64", raw), [1, 2])
        self.assertEqual(engine.evaluate("frame.len < 64", raw), [1])
        self.assertEqual(engine.evaluate("less 64", raw, "bpf"), [1, 2])
        self.assertEqual(engine.evaluate("len < 64", raw, "bpf"), [1])
        self.assertEqual(engine.evaluate("greater 128", raw, "bpf"), [5, 6])
        self.assertEqual(engine.evaluate("len > 128", raw, "bpf"), [6])

    def test_missing_fields_and_bpf_precedence(self):
        raw = corpus()
        self.assertEqual(engine.evaluate("tcp.port != 80", raw), [1, 4])
        self.assertEqual(engine.evaluate("not (tcp.port == 80)", raw), [1, 4, 5, 6])
        self.assertEqual(engine.evaluate("tcp or udp and port 53", raw, "bpf"), [5])
        self.assertEqual(engine.evaluate("tcp or (udp and port 53)", raw, "bpf"), [1, 2, 3, 4, 5])

    def test_invalid_filters_are_errors_not_empty_results(self):
        for dialect, query in [("wireshark", "tcp dst port 80"), ("bpf", "tcp.dstport == 80"),
                               ("wireshark", "tcp; echo BAD"), ("bpf", "tcp and (")]:
            with self.subTest(dialect=dialect, query=query), self.assertRaises(ValueError):
                engine.evaluate(query, corpus(), dialect)

    def test_input_validation(self):
        for value in ['[]', '{"dil":"powershell"}', '{"dosya":"C:/x.pcap"}',
                      '{"kayit":"temel","pcap_base64":"AA=="}']:
            with self.assertRaises(engine.PacketError):
                engine.options(value)
        with self.assertRaises(engine.PacketError):
            engine.capture_bytes("olmayan")
        with self.assertRaises(engine.PacketError):
            engine.evaluate("tcp\0or udp", corpus())

    def test_runner_run_test_and_real_byte_input(self):
        data = json.dumps({"dil": "bpf", "pcap_base64": base64.b64encode(corpus()).decode()})
        runner = get("packets")
        result = runner.run("tcp dst port 80", data)
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual(result["packet_ids"], [2])
        self.assertEqual(result["segs"], [["out", "Paketler: 2\n"]])
        self.assertIn("libpcap", result["packet_backend"])
        step = {"stdin": data, "test": 'eq(eslesenler(), [2], "tam seçim")'}
        self.assertEqual(runner.test("tcp dst port 80", step)["status"], "pass")
        self.assertEqual(runner.test("tcp src port 80", step)["status"], "fail")

    def test_missing_tshark_has_installation_message(self):
        engine._display.cache_clear()
        with patch.object(engine, "tshark_path", return_value=None), self.assertRaisesRegex(engine.PacketError, "PAFTA_TSHARK"):
            engine.evaluate("tcp", corpus())

    def test_numeric_addresses_sets_layers_and_text_fields_remain_native(self):
        raw = corpus()
        for query in ("ip.src == 192.0.2.1", "192.0.2.1 == ip.src",
                      "ip.src == 192.0.2.0/24", "ip.src in {192.0.2.1, 203.0.113.1}",
                      "ip.src in {192.0.2.0 .. 192.0.2.2}", "ip.src#1 == 192.0.2.1",
                      "ip.src != ip.dst"):
            with self.subTest(query=query):
                self.assertEqual(engine.evaluate(query, raw), [1, 2, 3, 4, 5, 6])
        self.assertTrue(engine.evaluate('ip.src == 10.0.0.10 and dns.qry.name == "portal.lab.test"'))
        self.assertTrue(engine.evaluate('ip.src == 10.0.0.10 and http.host == "portal.lab.test"'))
        self.assertTrue(engine.evaluate("ipv6.addr == 2001:db8::10"))

    def test_hostname_address_operands_never_reach_native_process(self):
        queries = ('ip.addr == example.test', 'ip.src eq "example.test"',
                   'example.test == ip.dst', 'ip.dst == example.test/24',
                   'ipv6.addr in {2001:db8::1, example.test}',
                   '(ip.src) == "localhost"', 'dns.a == "example.test"',
                   r'ip.src == "\x31\x32\x37.0.0.1"', 'ip.src in {192.0.2.1..example.test}')
        engine._display.cache_clear()
        with patch.object(engine.subprocess, "run") as native:
            for query in queries:
                with self.subTest(query=query), self.assertRaisesRegex(engine.PacketError, "sayısal IP"):
                    engine.evaluate(query, corpus())
            native.assert_not_called()

    def test_classic_formats_keep_capture_and_wire_lengths_distinct(self):
        frame = corpus()[40:40 + 63]
        for order in ("<", ">"):
            for nano in (False, True):
                raw = one_frame(frame[:34], wirelen=100, order=order, nano=nano)
                with self.subTest(order=order, nano=nano):
                    self.assertEqual(engine.pcap_lengths(raw), {1: (34, 100)})
                    self.assertEqual(engine.evaluate("frame.len == 100 and frame.cap_len == 34", raw), [1])
                    self.assertEqual(engine.evaluate("len == 100", raw, "bpf"), [1])
                    result = engine.run("frame", encoded(raw))
                    self.assertEqual(result["tablolar"][0]["satirlar"], [[1, 34, 100]])
                    self.assertNotIn("packet_inventory", result)

    def test_malformed_and_unsupported_captures_fail_before_native(self):
        good = corpus()
        bad_headers = []
        for offset, number in ((4, 3), (16, 0), (20, 147), (28, 1000000), (32, 65536), (36, 1)):
            raw = bytearray(good)
            struct.pack_into("<H" if offset == 4 else "<I", raw, offset, number)
            bad_headers.append(bytes(raw))
        malformed = [b"", good[:23], good[:-1], good + b"x", pcapng()[:-1], *bad_headers]
        with patch.object(engine, "_display") as display, patch.object(engine, "_bpf") as bpf:
            for raw in malformed:
                for dialect in ("wireshark", "bpf"):
                    with self.subTest(length=len(raw), dialect=dialect), self.assertRaises(engine.PacketError):
                        engine.evaluate("ip", raw, dialect)
                with self.assertRaises(engine.PacketError):
                    engine.pcap_lengths(raw)
            display.assert_not_called()
            bpf.assert_not_called()

    def test_base64_format_error_is_not_misreported_as_encoding_error(self):
        with self.assertRaisesRegex(engine.PacketError, "Base64"):
            engine.input_capture(engine.options('{"pcap_base64":"not base64!"}'))
        with self.assertRaisesRegex(engine.PacketError, "PCAP"):
            engine.input_capture(engine.options(encoded(b"not a pcap")))
        with self.assertRaisesRegex(engine.PacketError, "8 MiB"):
            engine.capture_bytes(b"X" * (engine.MAX_CAPTURE + 1))
        for value in (None, 12, {}, []):
            with self.subTest(value=value), self.assertRaises(engine.PacketError):
                engine.options(value)

    def test_tshark_timeout_launch_error_and_invalid_output_are_actionable(self):
        engine._display.cache_clear()
        with patch.object(engine.subprocess, "run", side_effect=subprocess.TimeoutExpired("tshark", 8)):
            with self.assertRaisesRegex(engine.PacketError, "8 saniye"):
                engine.evaluate("frame", corpus())
        with patch.object(engine.subprocess, "run", side_effect=OSError("blocked executable")):
            with self.assertRaisesRegex(engine.PacketError, "PAFTA_TSHARK"):
                engine.evaluate("frame", corpus())
        for output in (b"NaN\n", b"0\n", b"7\n", b"1\n1\n", b"2\n1\n", b"\xff"):
            result = subprocess.CompletedProcess([], 0, output, b"")
            with self.subTest(output=output), patch.object(engine.subprocess, "run", return_value=result):
                with self.assertRaisesRegex(engine.PacketError, "paket numarası"):
                    engine.evaluate("frame", corpus())

    def test_personal_preferences_and_plugins_do_not_replace_training_context(self):
        engine._display.cache_clear()
        with tempfile.TemporaryDirectory(prefix="pafta_ignored_prefs_") as directory:
            personal = Path(directory)
            (personal / "disabled_protos").write_text("tcp\n", encoding="utf-8")
            with patch.dict(os.environ, {"WIRESHARK_CONFIG_DIR": directory,
                                         "WIRESHARK_PLUGIN_DIR": directory,
                                         "WIRESHARK_DATA_DIR": str(personal / "missing"),
                                         "WIRESHARK_RUN_FROM_BUILD_DIRECTORY": "1"}):
                self.assertEqual(engine.evaluate("tcp", corpus()), [1, 2, 3, 4])

    def test_preset_inventory_is_complete_even_when_no_frames_match(self):
        result = engine.run("frame.number == 99999", '{"kayit":"sinirlar"}')
        self.assertEqual(result["packet_ids"], [])
        self.assertEqual(result["segs"], [["out", "Paketler: (yok)\n"]])
        inventory = result["packet_inventory"]
        self.assertIn("native ayrıştırma değildir", inventory["baslik"])
        self.assertEqual(len(inventory["satirlar"]), 50)
        self.assertEqual(inventory["satirlar"][-1][0], 50)
        self.assertEqual(inventory["satirlar"][-1][4], "64 / 36")
        self.assertIn("53", inventory["satirlar"][3][3])

    def test_native_bpf_syllabus_operators_and_qualifier_carry(self):
        raw = engine.packet_fixtures.get_capture("sinirlar")
        self.assertEqual(engine.evaluate("ip[6:2] & 0x1fff != 0", raw, "bpf"), [28])
        self.assertEqual(engine.evaluate("ip[0] & 0xf != 5", raw, "bpf"), [32])
        self.assertEqual(engine.evaluate("tcp dst port 80 or 443", raw, "bpf"),
                         engine.evaluate("tcp dst port 80 or tcp dst port 443", raw, "bpf"))
        self.assertEqual(engine.evaluate("ether src 02:00:00:00:00:10", raw, "bpf"),
                         engine.evaluate("eth.src == 02:00:00:00:00:10", raw))


if __name__ == "__main__":
    unittest.main()
