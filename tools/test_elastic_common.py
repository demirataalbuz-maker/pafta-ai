"""Corpus validation, exact millisecond boundaries and explicit result order."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sandbox.elastic_common import ElasticError, corpus, date_millis, selected_documents, sorted_documents


class CorpusTests(unittest.TestCase):
    def config(self):
        return {"mapping": {"@timestamp": "date", "n": "integer", "name": "keyword"},
                "documents": [{"id": "a", "@timestamp": "2026-01-01T00:00:00Z", "n": 1},
                              {"id": "b", "@timestamp": "2026-01-01T00:00:00.001Z", "n": 2},
                              {"id": "c", "@timestamp": "2026-01-01T00:00:00.002Z", "n": 3}]}

    def test_exact_millis_and_timezone(self):
        self.assertEqual(date_millis("1970-01-01T00:00:00.001Z"), 1)
        self.assertEqual(date_millis("1970-01-01T03:00:00.001+03:00"), 1)
        self.assertEqual(date_millis("1969-12-31T23:59:59.999Z"), -1)
        for raw in (True, 1.2, "2026-01-01", "now-1d", "2026-01-01T00:00:00.0001Z", "2026-99-01T00:00:00Z",
                    "2026-01-01T00:00:00+00:60", "2026-01-01T00:00:00+18:01", "2026-01-01T00:00:00-19:00"):
            with self.subTest(raw=raw), self.assertRaises(ElasticError):
                date_millis(raw)

    def test_all_time_window_boundaries(self):
        for op, expected in (("gt", ["c"]), ("gte", ["b", "c"]), ("lt", ["a"]), ("lte", ["a", "b"])):
            value = self.config()
            value["context"] = {"time_filter": {"field": "@timestamp", op: "2026-01-01T00:00:00.001Z"}}
            self.assertEqual([d["id"] for d in selected_documents(corpus(value))], expected)

    def test_source_order_and_explicit_sort(self):
        value = corpus(self.config())
        value["documents"].append({"id": "d"})
        self.assertEqual([d["id"] for d in sorted_documents(value["documents"], value)], ["a", "b", "c", "d"])
        value["context"] = {"sort": [["n", "desc"]]}
        self.assertEqual([d["id"] for d in sorted_documents(value["documents"], value)], ["c", "b", "a", "d"])

    def test_bad_shapes_and_coercion_are_rejected(self):
        mutations = [lambda c: c.update(extra=True), lambda c: c.update(mapping={"n": "keyword, normalizer yok"}),
                     lambda c: c["documents"].append({"id": "a"}), lambda c: c["documents"][0].update(n="1"),
                     lambda c: c["documents"][0].update(n=True), lambda c: c["documents"][0].update(n=2147483648),
                     lambda c: c.update(context={"sort": [["n", "sideways"]]}),
                     lambda c: c.update(context={"sort": [[[], "asc"]]}),
                     lambda c: c.update(context={"time_filter": {"field": [], "gte": 0}}),
                     lambda c: c.update(context={"time_filter": {"field": "name", "gte": 0}}),
                     lambda c: c["mapping"].update(name={"type": "keyword", "normalizer": "icu"})]
        for mutate in mutations:
            value = copy.deepcopy(self.config())
            mutate(value)
            with self.subTest(value=value), self.assertRaises(ElasticError):
                corpus(value)

    def test_nonfinite_overflow_and_epoch_limits(self):
        for raw in (10**400, float("nan"), float("inf"), -float("inf")):
            with self.subTest(raw=raw), self.assertRaises(ElasticError):
                corpus({"mapping": {"n": "double"}, "documents": [{"id": "a", "n": raw}]})
        for raw in (-(2**63)-1, 2**63):
            with self.assertRaises(ElasticError):
                date_millis(raw)


if __name__ == "__main__":
    unittest.main(verbosity=2)
