"""Independent expected-result tests for the bounded Elasticsearch EQL subset."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sandbox.elastic_eql import EqlError, evaluate


MAPPING = {
    "@timestamp": "date_nanos", "event.category": "keyword", "event.id": "keyword",
    "event.sequence": "long", "event.action": "keyword", "process.name": "keyword",
    "host.id": "keyword", "user.id": "keyword", "n": "long", "flag": "boolean",
    "a": "keyword", "b": "keyword", "c": "keyword", "message": "text",
}


def event(eid, second=0, action="a", key="h1", category="process", **fields):
    doc = {"id": eid, "event.id": eid, "@timestamp": f"2026-10-21T00:00:{second:02}.000000000Z",
           "event.category": category, "event.action": action, "host.id": key}
    doc.update(fields)
    return doc


class EventPredicates(unittest.TestCase):
    def run_query(self, query, documents, **kwargs):
        return evaluate(query, MAPPING, documents, **kwargs)

    def test_category_literal_case_and_wildcard(self):
        docs = [event("a", **{"process.name": "CMD.EXE"}), event("b", **{"process.name": "cmd.exe"}),
                event("c", **{"process.name": "cmd*.exe"}), event("d", category="file", **{"process.name": "cmd.exe"}),
                event("e", **{"process.name": "cmd1.exe"}), event("f", **{"process.name": "cmd12.exe"})]
        self.assertEqual(self.run_query('process where process.name == "cmd.exe"', docs), ["b"])
        self.assertEqual(self.run_query('process where process.name == "cmd*.exe"', docs), ["c"])
        self.assertEqual(self.run_query('process where process.name : "cmd.exe"', docs), ["a", "b"])
        self.assertEqual(self.run_query('process where process.name like "cmd?.exe"', docs), ["c", "e"])
        self.assertEqual(self.run_query('any where process.name in~ ("CMD.EXE", "cmd1.exe")', docs), ["a", "b", "d", "e"])
        self.assertEqual(self.run_query('process where process.name not in ("cmd.exe", "cmd*.exe", "cmd1.exe", "cmd12.exe")', docs), ["a"])

    def test_string_escaping_and_no_shell_glob_classes(self):
        docs = [event("a", **{"process.name": "a*b"}), event("b", **{"process.name": "a\\xb"}),
                event("c", **{"process.name": "a[1]b"}), event("d", **{"process.name": "a1b"}),
                event("e", **{"process.name": "a\nb"}), event("f", **{"process.name": "Türkçe"})]
        self.assertEqual(self.run_query(r'process where process.name == "a\u{2a}b"', docs), ["a"])
        self.assertEqual(self.run_query(r'process where process.name like "a\\*b"', docs), ["b"])
        self.assertEqual(self.run_query('process where process.name like "a[1]b"', docs), ["c"])
        self.assertEqual(self.run_query('process where process.name == "Türkçe"', docs), ["f"])
        self.assertEqual(self.run_query(r'process where process.name == "a\nb"', docs), ["e"])
        self.assertEqual(self.run_query('process where process.name like """a\\*b"""', docs), ["b"])

    def test_null_exists_and_three_value_logic(self):
        docs = [event("a"), event("b", flag=False, n=0), event("c", flag=True, n=1), event("d", flag=None, n=None)]
        self.assertEqual(self.run_query('any where n == null', docs), ["a", "d"])
        self.assertEqual(self.run_query('any where n != null', docs), ["b", "c"])
        self.assertEqual(self.run_query('any where not (n == 1)', docs), ["b"])
        self.assertEqual(self.run_query('any where n != 1', docs), ["b"])
        self.assertEqual(self.run_query('any where n in (1, null)', docs), ["c"])
        self.assertEqual(self.run_query('any where n not in (1, null)', docs), [])
        self.assertEqual(self.run_query('any where flag or true', docs), ["a", "b", "c", "d"])
        self.assertEqual(self.run_query('any where flag and false', docs), [])
        self.assertEqual(self.run_query('any where not (flag and false)', docs), ["a", "b", "c", "d"])
        self.assertEqual(self.run_query('any where not (flag or false)', docs), ["b"])
        self.assertEqual(self.run_query('any where ?unmapped == null', docs), ["a", "b", "c", "d"])
        self.assertEqual(self.run_query('any where ?unmapped != null', docs), [])
        self.assertEqual(self.run_query('any where n == 0 or n == 1 and flag == false', docs), ["b"])

    def test_numeric_and_timestamp_boundaries(self):
        docs = [event(str(i), n=n) for i, n in enumerate((-1, 0, 1, 79, 80, 81, 82))]
        self.assertEqual(self.run_query('any where n >= 79 and n <= 81', docs), ["3", "4", "5"])
        self.assertEqual(self.run_query('any where n < 0', docs), ["0"])
        self.assertEqual(self.run_query('any where n == -1', docs), ["0"])
        dates = [event("a", **{"@timestamp": "2026-10-21T01:00:00+01:00"}), event("b", **{"@timestamp": "2026-10-21T00:00:00.000000001Z"})]
        self.assertEqual(self.run_query('any where @timestamp > "2026-10-21T00:00:00Z"', dates), ["b"])
        self.assertEqual(self.run_query('any where @timestamp == "2026-10-21T00:00:00Z"', dates), ["a"])

    def test_date_zone_boundaries_and_control_ids(self):
        for stamp in ("2026-01-01T00:00:00+00:60", "2026-01-01T00:00:00+18:01", "2026-01-01T00:00:00-19:00"):
            with self.subTest(stamp=stamp), self.assertRaises(EqlError):
                self.run_query("any where true", [event("a", **{"@timestamp": stamp})])
        for stamp in ("2026-01-01T00:00:00+18:00", "2026-01-01T00:00:00-18:00", "2026-01-01T00:00:00+17:59"):
            self.assertEqual(self.run_query("any where true", [event("a", **{"@timestamp": stamp})]), ["a"])
        with self.assertRaises(EqlError): self.run_query("any where true", [event("bad\nid")])

    def test_unmapped_source_is_not_indexed_and_category_any(self):
        doc = event("a", **{"unmapped": "source-only"})
        self.assertEqual(self.run_query('any where ?unmapped == null', [doc]), ["a"])
        with self.assertRaises(EqlError): self.run_query('any where unmapped == "source-only"', [doc])
        absent = event("b"); absent.pop("event.category")
        self.assertEqual(self.run_query('any where true', [absent]), ["b"])
        self.assertEqual(self.run_query('process where true', [absent]), [])

    def test_backtick_and_custom_context(self):
        mapping = {"when": "date", "kind": "keyword", "sort": "long", "some-field": "keyword"}
        docs = [{"id": "z", "when": "2026-01-01T00:00:00Z", "sort": 2, "kind": "my-event", "some-field": "yes"},
                {"id": "a", "when": "2026-01-01T00:00:00Z", "sort": 1, "kind": "my-event", "some-field": "yes"}]
        self.assertEqual(evaluate('"my-event" where `some-field` == "yes"', mapping, docs,
                                  {"timestamp_field": "when", "event_category_field": "kind", "tiebreaker_field": "sort"}), ["a", "z"])


class SequenceMachine(unittest.TestCase):
    query = 'sequence by host.id [process where event.action == "a"] [process where event.action == "b"]'

    def eql(self, query, docs, context=None):
        return evaluate(query, MAPPING, docs, context)

    def test_latest_pending_is_not_cartesian(self):
        self.assertEqual(self.eql(self.query, [event("a1", 0), event("a2", 1), event("b1", 2, "b"), event("b2", 3, "b")]), [["a2", "b1"]])
        docs = [event("a1", 0), event("b1", 1, "b"), event("a2", 2), event("b2", 3, "b"), event("c", 4, "c")]
        q = self.query + ' [process where event.action == "c"]'
        self.assertEqual(self.eql(q, docs), [["a2", "b2", "c"]])

    def test_separate_keys_reversed_input_and_same_event_overlap(self):
        docs = [event("a1", 0), event("a2", 1, key="h2"), event("b1", 2, "b"), event("b2", 3, "b", key="h2")]
        self.assertEqual(self.eql(self.query, list(reversed(docs))), [["a1", "b1"], ["a2", "b2"]])
        q = 'sequence [any where true] [any where true] [any where true]'
        self.assertEqual(self.eql(q, [event(str(i), i) for i in range(4)]), [["0", "1", "2"], ["1", "2", "3"]])

    def test_official_state_machine_example(self):
        actions = ("attrib", "attrib", "bash", "bash", "bash", "attrib", "attrib", "bash", "cat", "cat", "cat")
        users = ("root", "root", "elkbee", "root", "root", "elkbee", "root", "elkbee", "root", "elkbee", "root")
        docs = [event(str(i + 1), i, action, user) for i, (action, user) in enumerate(zip(actions, users))]
        query = 'sequence by host.id [process where event.action == "attrib"] [process where event.action == "bash"] [process where event.action == "cat"]'
        self.assertEqual(self.eql(query, docs), [["2", "4", "9"], ["6", "8", "10"]])

    def test_maxspan_exact_edge_and_nanosecond_neighbours(self):
        query = self.query.replace('by host.id', 'by host.id with maxspan=1s')
        start = event("a", 0)
        for stamp, matched in (("2026-10-21T00:00:00.999999999Z", True), ("2026-10-21T00:00:01.000000000Z", True), ("2026-10-21T00:00:01.000000001Z", False)):
            end = event("b", action="b", **{"@timestamp": stamp})
            self.assertEqual(self.eql(query, [end, start]), [["a", "b"]] if matched else [], stamp)

    def test_until_is_lower_inclusive_upper_exclusive_ordinal(self):
        query = self.query + ' until [process where event.action in ("stop", "a-stop", "b-stop")]'
        first = event("a", **{"event.sequence": 10})
        last = event("b", action="b", **{"event.sequence": 20})
        context = {"tiebreaker_field": "event.sequence"}
        for seq, allowed in ((9, True), (11, False), (19, False), (21, True)):
            self.assertEqual(self.eql(query, [first, event("stop", action="stop", **{"event.sequence": seq}), last], context), [["a", "b"]] if allowed else [])
        overlap_start = query.replace('== "a"', 'in ("a", "a-stop")')
        self.assertEqual(self.eql(overlap_start, [event("a", action="a-stop", **{"event.sequence": 10}), last], context), [])
        overlap_end = query.replace('== "b"', 'in ("b", "b-stop")')
        self.assertEqual(self.eql(overlap_end, [first, event("b", action="b-stop", **{"event.sequence": 20})], context), [["a", "b"]])
        other_key = event("stop", action="stop", key="h2", **{"event.sequence": 15})
        self.assertEqual(self.eql(query, [first, other_key, last], context), [["a", "b"]])

    def test_same_timestamp_tiebreaker_and_ambiguous_rejection(self):
        docs = [event("z", action="a", **{"event.sequence": 2}), event("a", action="b", **{"event.sequence": 1})]
        self.assertEqual(self.eql(self.query, docs, {"tiebreaker_field": "event.sequence"}), [])
        docs[0]["event.sequence"] = 0
        self.assertEqual(self.eql(self.query, list(reversed(docs)), {"tiebreaker_field": "event.sequence"}), [["z", "a"]])
        docs[0]["event.sequence"] = 1
        with self.assertRaises(EqlError): self.eql(self.query, docs, {"tiebreaker_field": "event.sequence"})

    def test_optional_null_and_per_stage_join_fields(self):
        query = 'sequence by ?user.id [process where event.action == "a"] by a [process where event.action == "b"] by b'
        docs = [event("a", 0, a="same"), event("b", 1, "b", b="same")]
        self.assertEqual(self.eql(query, docs), [["a", "b"]])
        self.assertEqual(self.eql(query.replace('?user.id', 'user.id'), docs), [])
        self.assertEqual(self.eql(query.replace('?user.id', '?unknown'), docs), [["a", "b"]])
        docs[1]["b"] = "different"
        self.assertEqual(self.eql(query, docs), [])

    def test_missing_middle_uses_open_timestamp_not_tuple(self):
        query = 'sequence by host.id with maxspan=2s [process where event.action == "a"] ![process where event.action == "stop"] [process where event.action == "b"]'
        first = event("a", 0, **{"event.sequence": 1})
        last = event("b", 2, "b", **{"event.sequence": 5})
        for second, allowed in ((0, True), (1, False), (2, True)):
            docs = [first, event("stop", second, "stop", **{"event.sequence": 3}), last]
            self.assertEqual(self.eql(query, docs, {"tiebreaker_field": "event.sequence"}), [["a", "b"]] if allowed else [])
        self.assertEqual(self.eql(query, [first, event("stop", 1, "stop", key="h2", **{"event.sequence": 3}), last], {"tiebreaker_field": "event.sequence"}), [["a", "b"]])


class RejectionContract(unittest.TestCase):
    def test_maxspan_units_match_elastic_and_negative_zero_is_explicit(self):
        for unit in ("ns", "micros", "us", "w", "S"):
            with self.subTest(unit=unit), self.assertRaises(EqlError):
                evaluate('sequence with maxspan=1' + unit + ' [any where true] [any where true]', MAPPING, [])
        mapping = {**MAPPING, "ratio": "double"}
        for query in ('any where ratio == -0.0', 'any where ratio in (-0e0, 1.0)'):
            with self.subTest(query=query), self.assertRaisesRegex(EqlError, "negatif double sıfırı"):
                evaluate(query, mapping, [])
        with self.assertRaisesRegex(EqlError, "negatif double sıfırı"):
            evaluate('any where ratio >= 0.0', mapping, [event("a", ratio=-0.0)])

    def test_unsupported_numeric_promotion_and_key_coercion_fail_clearly(self):
        mapping = {**MAPPING, "ratio": "double", "other_n": "integer"}
        for query in ('any where ratio < 9007199254740993', 'any where n == 1.0',
                      'any where 9007199254740993 == 9007199254740992.0',
                      'any where process.name < "z"',
                      'sequence [any where true] by n [any where true] by ratio',
                      'sequence [any where true] by n [any where true] by other_n',
                      'sequence by ratio [any where true] [any where true]'):
            with self.subTest(query=query), self.assertRaises(EqlError):
                evaluate(query, mapping, [])
        self.assertEqual(evaluate('any where ratio == 1.0', mapping, [event("a", ratio=1.0)]), ["a"])

    def test_unsupported_or_unconsumed_syntax_never_silently_passes(self):
        queries = [
            'process where process.name = "a"', 'process where process.name == "a" garbage',
            'process where process.name == process.name', 'process where true | head 1',
            'process where length(process.name) > 2', 'process where n + 1 > 2',
            'process where process.name regex "x.*"', 'process where n < 1 < 2',
            'process where process.name == \'x\'', 'process where n', 'process where n == true',
            'process where process.name == "\\q"', 'process where process.name in ()',
            'sequence [any where true]', 'sequence [any where true] [any where true] with runs=2',
            'sequence [any where true] ![any where true] [any where true]',
            'sequence with maxspan=1s ![any where true] [any where true] [any where true]',
            'sequence with maxspan=1s [any where true] [any where true] ![any where true]',
            'sequence with maxspan=0s [any where true] [any where true]',
            'sequence [any where true] by a [any where true]',
            'any where false and unmapped == "x"',
            'any where ' + ' or '.join(['true'] * 100),
            'any where ' + 'not ' * 65 + 'true',
        ]
        for query in queries:
            with self.subTest(query=query), self.assertRaises(EqlError): evaluate(query, MAPPING, [event("a", n=1)])

    def test_mapping_arrays_normalizers_unicode_and_types(self):
        for mapping in ({**MAPPING, "process.name": {"type": "keyword", "normalizer": "lowercase"}},
                        {**MAPPING, "process.name": {"type": "keyword", "null_value": "NULL"}},
                        {**MAPPING, "process.name": {"type": "keyword", "ignore_above": 8}}):
            with self.assertRaises(EqlError): evaluate('any where true', mapping, [])
        for query, doc in [('any where message == "x"', event("a", message="x")),
                           ('any where process.name == "x"', event("a", **{"process.name": ["x"]})),
                           ('any where n > 0', event("a", n=True)),
                           ('any where flag', event("a", flag=1)),
                           ('any where process.name : "*"', event("a", **{"process.name": "Türkçe"}))]:
            with self.subTest(query=query), self.assertRaises(EqlError): evaluate(query, MAPPING, [doc])
        with self.assertRaises(EqlError): evaluate('any where process.name : "Türkçe"', MAPPING, [])
        with self.assertRaises(EqlError): evaluate('any where nested.x == "y"', {**MAPPING, "nested": "nested", "nested.x": "keyword"}, [])
        with self.assertRaises(EqlError): evaluate('any where true', MAPPING, [event("a"), event("a")])


if __name__ == "__main__":
    unittest.main()
