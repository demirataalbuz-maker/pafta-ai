"""Whole-workbench contracts; actual native queries, not Python source models."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.lessons import Library
from sandbox import elastic_engine, elastic_lucene
from sandbox.elastic_common import ElasticError, corpus, date_millis


def config(dialect="eql"):
    return {"dil": dialect, "mapping": {"@timestamp": "date", "event.category": "keyword",
            "process.name": "keyword", "n": "long", "message": "text"},
            "documents": [
                {"id": "a", "@timestamp": "2026-01-01T00:00:00.000Z", "event.category": "process", "process.name": "cmd.exe", "n": 400, "message": "Login failed"},
                {"id": "b", "@timestamp": "2026-01-01T00:00:00.001Z", "event.category": "network", "process.name": "cmd.exe", "n": 499, "message": "Login has failed"},
                {"id": "c", "@timestamp": "2026-01-01T00:00:00.002Z", "event.category": "process", "process.name": "CMD.EXE", "n": 500, "message": "Other"},
            ], "context": {}}


class ElasticEngineTests(unittest.TestCase):
    def test_actual_three_dialect_dispatch_and_metadata(self):
        cases = (("kibana", 'event.category: process AND process.name: cmd.exe AND n >= 400 AND n < 500', ["a"]),
                 ("lucene", 'message:"login failed"~1 AND n:[400 TO 500}', ["a", "b"]),
                 ("eql", 'process where process.name : "cmd.exe" and n >= 400 and n < 500', ["a"]))
        for dialect, query, expected in cases:
            with self.subTest(dialect=dialect):
                result = elastic_engine.run(query, json.dumps(config(dialect)))
                self.assertEqual(result["elastic_ids"], expected)
                self.assertEqual(result["elastic_dialect"], dialect)
                self.assertEqual(result["segs"], [["out", "\n".join(expected) + "\n"]])
                self.assertIn("EQL" if dialect == "eql" else "Lucene", result["elastic_backend"])

    def test_query_text_is_never_python(self):
        for dialect in ("kibana", "lucene", "eql"):
            with self.subTest(dialect=dialect), self.assertRaises(ValueError):
                elastic_engine.evaluate('print("not a query")', config(dialect))

    def test_unknown_input_and_context_keys_are_rejected(self):
        for extra in ("eql", "query", "code", "python", "captures"):
            value = config(); value[extra] = "ignored?"
            with self.subTest(extra=extra), self.assertRaises(ElasticError):
                corpus(value)
        value = config(); value["context"] = {"unknown": True}
        with self.assertRaises(ElasticError): corpus(value)

    def test_context_sort_is_strict_for_eql(self):
        value = config(); value["context"] = {"sort": [["n", "desc"]]}
        with self.assertRaisesRegex(ElasticError, "context.sort"):
            elastic_engine.evaluate("any where true", value)

    def test_time_filter_has_all_four_exact_millisecond_edges(self):
        for op, expected in (("gt", ["c"]), ("gte", ["b", "c"]), ("lt", ["a"]), ("lte", ["a", "b"])):
            value = config(); value["context"] = {"time_filter": {"field": "@timestamp", op: "2026-01-01T00:00:00.001Z"}}
            self.assertEqual(elastic_engine.evaluate("any where true", value), expected, op)

    def test_eql_accepts_unused_text_but_rejects_querying_it(self):
        self.assertEqual(elastic_engine.evaluate("any where true", config()), ["a", "b", "c"])
        with self.assertRaisesRegex(ValueError, "text"):
            elastic_engine.evaluate('any where message == "Login failed"', config())

    def test_eql_still_works_when_native_lucene_runtime_is_unavailable(self):
        missing = elastic_lucene.ElasticLuceneUnavailable("Lucene JAR eksik; python tools/install_elastic_runtime.py çalıştırın.")
        with patch.object(elastic_lucene, "_compiled", side_effect=missing):
            self.assertEqual(elastic_engine.evaluate("any where true", config()), ["a", "b", "c"])
            with self.assertRaisesRegex(elastic_lucene.ElasticLuceneUnavailable, "install_elastic_runtime.py"):
                elastic_engine.evaluate("n:[400 TO 500]", config("lucene"))

    def test_helpers_merge_documents_and_dialect_without_mutating_corpus(self):
        value = config(); untouched = copy.deepcopy(value)
        helpers = elastic_engine.test_helpers('process where process.name == "cmd.exe"', json.dumps(value))
        self.assertEqual(helpers["eslesenler"](), ["a"])
        changed = [dict(value["documents"][0], id="new")]
        self.assertEqual(helpers["eslesenler"](changed), ["new"])
        self.assertEqual(helpers["referans"]('process.name: cmd.exe', changed, "kibana"), ["new"])
        self.assertEqual(value, untouched)
        self.assertEqual(helpers["eslesenler"](), ["a"])

    def test_empty_sequence_output_is_not_fake_event(self):
        value = config()
        query = 'sequence [process where true] [file where true]'
        result = elastic_engine.run(query, json.dumps(value))
        self.assertEqual(result["elastic_ids"], [])
        self.assertEqual(result["segs"], [["out", ""]])

    def test_el19_prediction_and_three_real_task_test_suites(self):
        lesson = Library().lesson("elastic", "el19")
        self.assertIsNotNone(lesson)
        counts = {"gorev": 0, "tahmin": 0}
        for step in lesson["steps"]:
            if step["kind"] == "tahmin":
                result = elastic_engine.run(step["code"], step["stdin"])
                stdout = "".join(t for kind, t in result["segs"] if kind == "out").strip()
                self.assertIn(stdout, step["body"].split("???")[-1])
                counts["tahmin"] += 1
            elif step["kind"] == "gorev":
                helpers = elastic_engine.test_helpers(step["solution"], step["stdin"])
                helpers["eq"] = lambda a, b, msg="": self.assertEqual(a, b, msg)
                exec(step["test"], helpers)
                counts["gorev"] += 1
        self.assertEqual(counts, {"gorev": 3, "tahmin": 1})

    def test_malformed_context_field_types_raise_actionable_value_error(self):
        for context in ({"sort": [[[], "asc"]]}, {"time_filter": {"field": [], "gte": 0}}):
            with self.subTest(context=context), self.assertRaises(ElasticError):
                corpus(dict(config(), context=context))

    def test_invalid_iso_zone_minutes_do_not_normalize_silently(self):
        for stamp in ("2026-01-01T00:00:00+00:60", "2026-01-01T00:00:00-03:60"):
            with self.subTest(stamp=stamp), self.assertRaises(ElasticError):
                date_millis(stamp)


if __name__ == "__main__":
    unittest.main()
