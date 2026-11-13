# -*- coding: utf-8 -*-
"""Gerçek yara-python motoru ve Pafta girdi sınırlarının odaklı testleri.

    python tools/test_yara_runtime.py
"""
import base64
import hashlib
import json
import re
import struct
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sandbox import yara_engine as engine
from engine.lessons import Library
from engine.runners import get


def names(rules, data):
    return [match.rule for match in engine.match_rules(rules, data)]


# Skip strings/comments so only comparison operators in actual YARA code change.
_COMPARISON = re.compile(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*[\s\S]*?\*/|<<|>>|(?P<op><=|>=|<|>)')
_BOUNDARY_TASKS = (("yr12", 4, 1), ("yr15", 3, 2), ("yr16", 3, 1),
                   ("yr17", 3, 2), ("yr17", 4, 2), ("yr18", 3, 2), ("yr18", 4, 2),
                   ("yr20", 2, 1))

_PE_MUTATIONS = (
    ("yr19", 2, '"KERNEL32.dll"', '"USER32.dll"'),
    ("yr19", 2, '"CreateFileW"', '"ReadFile"'),
    ("yr19", 3, '"LabEntry"', '"OtherEntry"'),
    ("yr19", 3, "ordinal == 7", "ordinal == 6"),
    ("yr20", 2, 'name == ".text"', 'name == ".code"'),
    ("yr20", 2, "pe.SECTION_MEM_EXECUTE", "pe.SECTION_MEM_WRITE"),
    ("yr20", 3, "for any section", "for all section"),
    ("yr20", 3, "pe.SECTION_MEM_EXECUTE", "pe.SECTION_MEM_READ"),
    ("yr20", 3, "pe.SECTION_MEM_WRITE", "pe.SECTION_MEM_READ"),
)


def comparison_mutants(source):
    """Toggle one strict/inclusive comparison per mutant, retaining valid syntax."""
    replacements = {"<=": "<", ">=": ">", "<": "<=", ">": ">="}
    for match in _COMPARISON.finditer(source):
        operator = match.group("op")
        if operator is None:
            continue
        changed = replacements[operator]
        line = source.count("\n", 0, match.start()) + 1
        yield f"s.{line} {operator} → {changed}", source[:match.start()] + changed + source[match.end():]


class YaraCurriculumBoundaryTests(unittest.TestCase):
    def test_pe_lesson_mutants_are_rejected(self):
        library, runner = Library(), get("yara")
        for lesson_id, index, old, new in _PE_MUTATIONS:
            step = library.lesson("yara", lesson_id)["steps"][index]
            solution = step["solution"]
            self.assertEqual(solution.count(old), 1, (lesson_id, index, old))
            with self.subTest(lesson=lesson_id, task=index, mutation=old):
                result = runner.test(solution.replace(old, new), step)
                self.assertEqual(result["status"], "fail", result)
                self.assertTrue(any(not check["ok"] for check in result["checks"]), result)

    def test_lesson_boundary_mutants_are_rejected(self):
        """Every audited solution passes, while each of its 12 boundary faults fails."""
        library, runner = Library(), get("yara")
        for lesson_id, index, expected_count in _BOUNDARY_TASKS:
            step = library.lesson("yara", lesson_id)["steps"][index]
            reference = f"{lesson_id}:{index}"
            with self.subTest(task=reference, version="solution"):
                self.assertEqual(step["kind"], "gorev")
                result = runner.test(step["solution"], step)
                self.assertEqual(result["status"], "pass", result)
            mutants = list(comparison_mutants(step["solution"]))
            self.assertEqual(len(mutants), expected_count, reference)
            for label, code in mutants:
                with self.subTest(task=reference, mutation=label):
                    result = runner.test(code, step)
                    self.assertEqual(result["status"], "fail", result)
                    self.assertIsNone(result.get("error"), result)
                    self.assertTrue(any(not check["ok"] for check in result["checks"]), result)


class YaraRuntimeTests(unittest.TestCase):
    def test_native_ascii_and_negative(self):
        rules = engine.compile_rules('rule text { strings: $a = "PAFTA" ascii condition: $a }')
        matches = engine.match_rules(rules, "önce PAFTA sonra")
        self.assertEqual([match.rule for match in matches], ["text"])
        self.assertEqual(matches[0].strings[0].instances[0].offset, len("önce ".encode("utf-8")))
        self.assertEqual(names(rules, b"unrelated"), [])

    def test_wide_nocase_and_offset(self):
        rules = engine.compile_rules('rule wide_text { strings: $a = "pafta" wide nocase condition: $a at 2 }')
        self.assertEqual(names(rules, b"xx" + "PAFTA".encode("utf-16-le")), ["wide_text"])
        self.assertEqual(names(rules, b"x" + "PAFTA".encode("utf-16-le")), [])
        self.assertEqual(names(rules, b"xxPAFTA"), [])

    def test_hex_wildcard_jump_and_alternative(self):
        rules = engine.compile_rules('rule bytes_rule { strings: $a = { 4D 5A ?? [1-2] ( 90 | 91 ) } condition: $a }')
        self.assertEqual(names(rules, bytes.fromhex("4d 5a 00 ff 91")), ["bytes_rule"])
        self.assertEqual(names(rules, bytes.fromhex("4d 5a 00 ff 92")), [])

    def test_byte_conditions_and_hash_module(self):
        payload = b"MZpafta"
        digest = hashlib.sha256(payload).hexdigest()
        rules = engine.compile_rules(
            'import "hash"\n'
            'rule header_hash { condition: uint16(0) == 0x5a4d and filesize == 7 '
            f'and hash.sha256(0, filesize) == "{digest}" }}'
        )
        self.assertEqual(names(rules, payload), ["header_hash"])
        self.assertEqual(names(rules, b"MZother"), [])

    def test_native_pe_module(self):
        payload = bytearray(1024)
        payload[:2] = b"MZ"
        struct.pack_into("<I", payload, 0x3C, 0x80)
        payload[0x80:0x84] = b"PE\0\0"
        struct.pack_into("<HHIIIHH", payload, 0x84, 0x14C, 1, 0, 0, 0, 0xE0, 0x102)
        optional = 0x98
        struct.pack_into("<H", payload, optional, 0x10B)
        struct.pack_into("<I", payload, optional + 16, 0x1000)
        struct.pack_into("<I", payload, optional + 28, 0x400000)
        struct.pack_into("<II", payload, optional + 32, 0x1000, 0x200)
        struct.pack_into("<II", payload, optional + 56, 0x2000, 0x200)
        struct.pack_into("<H", payload, optional + 68, 3)
        struct.pack_into("<I", payload, optional + 92, 16)
        section = optional + 0xE0
        payload[section:section + 8] = b".text\0\0\0"
        struct.pack_into("<IIII", payload, section + 8, 1, 0x1000, 0x200, 0x200)
        struct.pack_into("<I", payload, section + 36, 0x60000020)
        payload[0x200] = 0xC3
        rules = engine.compile_rules('import "pe" rule executable { condition: pe.is_pe and pe.machine == pe.MACHINE_I386 }')
        self.assertEqual(names(rules, bytes(payload)), ["executable"])
        self.assertEqual(names(rules, b"MZ is not a complete PE"), [])

    def test_ui_decoding_and_helper_literal_text(self):
        self.assertEqual(engine.decode_data("Türkçe\n"), "Türkçe\n".encode("utf-8"))
        self.assertEqual(engine.decode_data("hex: 4d 5a 00\n"), b"MZ\0")
        self.assertEqual(engine.decode_data("base64:TVoA\n"), b"MZ\0")
        self.assertEqual(engine.decode_data(""), b"")
        rules = engine.compile_rules('rule literal { strings: $a = "hex:4d5a" condition: $a }')
        self.assertEqual(names(rules, "hex:4d5a"), ["literal"])
        self.assertEqual(names(rules, engine.decode_data("hex:4d5a")), [])

    def test_invalid_encodings(self):
        for data in ("hex:f", "hex:zz", "base64:@@@@", "base64:TQ", "base64:TV\noA", "base64:ç"):
            with self.subTest(data=data), self.assertRaises(ValueError):
                engine.decode_data(data)

    def test_size_limit_all_entrypoints(self):
        allowed = b"A" * engine.MAX_DATA_BYTES
        too_large = allowed + b"A"
        rules = engine.compile_rules(f"rule limit {{ condition: filesize == {engine.MAX_DATA_BYTES} }}")
        self.assertEqual(names(rules, allowed), ["limit"])
        for data in (too_large, "é" * (engine.MAX_DATA_BYTES // 2 + 1)):
            with self.subTest(kind=type(data).__name__), self.assertRaises(ValueError):
                engine.match_rules(rules, data)
        for stdin in (too_large.decode("ascii"), "hex:" + too_large.hex(), "base64:" + base64.b64encode(too_large).decode("ascii")):
            with self.assertRaises(ValueError):
                engine.decode_data(stdin)
        with self.assertRaises(ValueError):
            engine.format_result(rules, too_large)

    def test_invalid_syntax_and_includes_rejected(self):
        for code in ('rule broken { condition: }', 'include "anything.yar"\nrule valid { condition: true }'):
            with self.subTest(code=code), self.assertRaises(Exception):
                engine.compile_rules(code)

    def test_warning_is_not_output_and_result_serializes(self):
        rules = engine.compile_rules('rule one { strings: $a = { 01 } condition: $a }')
        result = engine.format_result(rules, b"\x00\x01")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["segs"], [["out", "one\n"]])
        self.assertTrue(result["warnings"])
        self.assertEqual(result["tablolar"][0]["satirlar"], [["one", "$a", 1, "\\x01"]])
        json.dumps(result, ensure_ascii=False)
        self.assertEqual(engine.format_result(rules, b"none")["segs"], [])

    def test_many_offsets_are_bounded_and_console_does_not_pollute_output(self):
        rules = engine.compile_rules('import "console" rule many { strings: $a = "aa" condition: $a and console.log("debug") }')
        result = engine.format_result(rules, b"a" * 500)
        self.assertEqual(result["segs"], [["out", "many\n"]])
        self.assertEqual(len(result["tablolar"][0]["satirlar"]), engine.MATCH_ROW_LIMIT)
        self.assertTrue(result["tablolar"][0]["kesildi"])

    def test_timeout_policy_passed_to_native_match(self):
        class RecordingRules:
            def match(self, **kwargs):
                self.kwargs = kwargs
                return []
        rules = RecordingRules()
        self.assertEqual(engine.match_rules(rules, "data"), [])
        self.assertEqual(rules.kwargs["data"], b"data")
        self.assertEqual(rules.kwargs["timeout"], 2)

    def test_missing_dependency_is_actionable(self):
        with patch.object(engine.importlib, "import_module", side_effect=ImportError("missing")):
            with self.assertRaisesRegex(RuntimeError, "yara-python==4.5.4"):
                engine.compile_rules("rule test { condition: true }")


if __name__ == "__main__":
    unittest.main(verbosity=2)
