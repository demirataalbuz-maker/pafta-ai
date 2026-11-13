"""Semantic tests for the local Sigma teaching backend and isolated harness."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from sandbox.sigma_engine import SigmaProgram, SigmaLessonError, parse_events
from engine.runners import get


def rule(selection, condition="selection", extra=""):
    return ("title: Pafta Test\nlogsource:\n    product: windows\n"
            "detection:\n" + selection + "    condition: " + condition + "\n" + extra)


class SigmaRuntimeTests(unittest.TestCase):
    def test_fields_and_values_have_distinct_boolean_links(self):
        program = SigmaProgram(rule("    selection:\n        EventID: 1\n        Image:\n            - a.exe\n            - b.exe\n"))
        self.assertTrue(program.matches({"EventID": 1, "Image": "B.EXE"}))
        self.assertFalse(program.matches({"EventID": 2, "Image": "a.exe"}))
        self.assertFalse(program.matches({"EventID": 1, "Image": "c.exe"}))

    def test_map_list_is_or(self):
        program = SigmaProgram(rule("    selection:\n        - EventID: 1\n          Image: a.exe\n        - EventID: 3\n          Image: b.exe\n"))
        self.assertTrue(program.matches({"EventID": 3, "Image": "b.exe"}))
        self.assertFalse(program.matches({"EventID": 1, "Image": "b.exe"}))

    def test_all_modifier_and_array_values(self):
        program = SigmaProgram(rule("    selection:\n        CommandLine|contains|all:\n            - alpha\n            - beta\n"))
        self.assertTrue(program.matches({"CommandLine": "BETA --ALPHA"}))
        self.assertTrue(program.matches({"CommandLine": ["alpha", "beta"]}))
        self.assertFalse(program.matches({"CommandLine": "alpha"}))

    def test_condition_filter_quantifiers_and_list(self):
        selectors = "    selection_one:\n        a: 1\n    selection_two:\n        b: 2\n    filter_ok:\n        user: admin\n"
        program = SigmaProgram(rule(selectors, "(1 of selection*) and not filter_ok"))
        self.assertTrue(program.matches({"b": 2, "user": "other"}))
        self.assertFalse(program.matches({"a": 1, "user": "admin"}))
        both = SigmaProgram(rule(selectors, "all of selection*"))
        self.assertFalse(both.matches({"a": 1}))
        self.assertTrue(both.matches({"a": 1, "b": 2}))
        alternatives = SigmaProgram(rule(selectors, "\n        - selection_one\n        - selection_two"))
        self.assertTrue(alternatives.matches({"b": 2}))

    def test_wildcard_escape_and_case(self):
        program = SigmaProgram(rule("    selection:\n        Image: 'C:\\Tools\\app?.exe'\n"))
        self.assertTrue(program.matches({"Image": r"c:\tools\app7.exe"}))
        self.assertFalse(program.matches({"Image": r"c:\tools\app77.exe"}))
        literal = SigmaProgram(rule("    selection:\n        message: 'literal\\*mark'\n"))
        self.assertTrue(literal.matches({"message": "literal*mark"}))
        self.assertFalse(literal.matches({"message": "literal-any-mark"}))
        cased = SigmaProgram(rule("    selection:\n        name|cased: Admin\n"))
        self.assertFalse(cased.matches({"name": "admin"}))
        self.assertTrue(cased.matches({"name": "Admin"}))

    def test_regex_is_case_sensitive_unless_flagged(self):
        pattern = "    selection:\n        name|re%s: '^admin[0-9]+$'\n"
        self.assertFalse(SigmaProgram(rule(pattern % "")).matches({"name": "ADMIN42"}))
        self.assertTrue(SigmaProgram(rule(pattern % "|i")).matches({"name": "ADMIN42"}))

    def test_exists_null_empty_and_missing(self):
        exists = SigmaProgram(rule("    selection:\n        name|exists: true\n"))
        self.assertTrue(exists.matches({"name": None}))
        self.assertFalse(exists.matches({}))
        null = SigmaProgram(rule("    selection:\n        name: null\n"))
        self.assertTrue(null.matches({}))
        self.assertTrue(null.matches({"name": None}))
        self.assertFalse(null.matches({"name": ""}))

    def test_cidr_numeric_and_nested_fields(self):
        program = SigmaProgram(rule("    selection:\n        source.ip|cidr: '192.0.2.0/24'\n        bytes|gte: 100\n"))
        self.assertTrue(program.matches({"source.ip": "192.0.2.4", "bytes": 100}))
        self.assertTrue(program.matches({"source": {"ip": "192.0.2.4"}, "bytes": "100"}))
        self.assertFalse(program.matches({"source.ip": "198.51.100.4", "bytes": 101}))
        self.assertFalse(program.matches({"source.ip": "192.0.2.4", "bytes": "bad"}))

    def test_numeric_precision_is_not_lost_in_event_values(self):
        program = SigmaProgram(rule("    selection:\n        Value: 9007199254740992\n"))
        self.assertFalse(program.matches({"Value": 9007199254740993}))
        self.assertTrue(program.matches({"Value": "9007199254740992"}))
        decimal = SigmaProgram(rule("    selection:\n        Value: 0.1\n"))
        self.assertTrue(decimal.matches({"Value": 0.1}))
        with self.assertRaises(SigmaLessonError):
            SigmaProgram(rule("    selection:\n        Value: 9007199254740993\n"))

    def test_raw_keywords_and_logsource_are_explicit(self):
        program = SigmaProgram(rule("    selection:\n        - hello\n"))
        self.assertTrue(program.matches({"_raw": "say HELLO now"}))
        self.assertFalse(program.matches({"other": "hello"}))
        # Caller selects telemetry; logsource is routing metadata, not an event filter.
        self.assertTrue(SigmaProgram(rule("    selection:\n        EventID: 1\n")).matches({"EventID": 1, "product": "synthetic"}))

    def test_multi_rule_order_and_selection(self):
        code = rule("    selection:\n        a: 1\n")
        program = SigmaProgram(code + "---\n" + code.replace("Pafta Test", "Other").replace("a: 1", "b: 2"))
        events = [{"id": "x", "a": 1}, {"id": "y", "b": 2}, {"id": "z"}]
        self.assertEqual(program.names, ["Pafta Test", "Other"])
        self.assertEqual(program.matching_events(events, "Other"), [events[1]])
        self.assertEqual(program.run(events)["segs"], [["out", "x\ny\n"]])

    def test_rejects_invalid_or_unimplemented_rules_without_events(self):
        invalid = ["", "title: x\n", rule("    selection:\n        x: 1\n", "missing"),
                   rule("    selection:\n        name|fieldref: other\n"),
                   rule("    selection:\n        x: 1\n        x: 2\n"),
                   "title: x\ncorrelation: {}\n"]
        for code in invalid:
            with self.subTest(code=code), self.assertRaises(Exception):
                SigmaProgram(code)

    def test_json_and_jsonl_input_limits(self):
        self.assertEqual(parse_events(""), [])
        self.assertEqual(parse_events('{"id":1}\n{"id":2}'), [{"id": 1}, {"id": 2}])
        for value in ("[1]", "bad", json.dumps([{}] * 1001)):
            with self.subTest(value=value[:30]), self.assertRaises(SigmaLessonError):
                parse_events(value)

    def test_isolated_harness_runs_and_grades_both_languages(self):
        sigma = get("sigma")
        code = rule("    selection:\n        EventID: 1\n")
        self.assertEqual(sigma.run(code, '[{"id":7,"EventID":1}]')["segs"], [["out", "7\n"]])
        step = {"test": "ok(eslesir({'EventID': 1})); ok(not eslesir({'EventID': 2})); eq(kural_adlari, ['Pafta Test'])"}
        self.assertEqual(sigma.test(code, step)["status"], "pass")
        self.assertEqual(sigma.test(code.replace("EventID: 1", "EventID: 2"), step)["status"], "fail")
        self.assertEqual(sigma.run("bad")["status"], "error")
        yara = get("yara")
        source = 'rule Hello { strings: $a = "hello" condition: $a }'
        result = yara.test(source, {"test": "ok(eslesir('hello')); ok(not eslesir('world')); eq(eslesenler('hello'), ['Hello']); ok(bool(derle(src).match(data=b'hello')))"})
        self.assertEqual(result["status"], "pass", result)


if __name__ == "__main__":
    unittest.main()
