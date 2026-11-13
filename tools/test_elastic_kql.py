"""Kibana KQL adapter regressions against the real local Lucene JVM."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sandbox.elastic_kql import ElasticKqlError, evaluate, parse


def keyword(**options):
    return dict(type="keyword", **options)


class KqlNativeTests(unittest.TestCase):
    def test_keyword_case_and_native_normalizer(self):
        mapping = {"user": keyword(), "fold": keyword(normalizer="lowercase")}
        docs = [{"user": name, "fold": name} for name in ("Alice", "alice", "ALICE", "other")]
        self.assertEqual(evaluate("user:alice", mapping, docs), [1])
        self.assertEqual(evaluate('user:"Alice"', mapping, docs), [0])
        self.assertEqual(evaluate("fold:ALICE", mapping, docs), [0, 1, 2])

    def test_unquoted_text_is_or_and_phrase_is_ordered(self):
        mapping = {"message": {"type": "text", "analyzer": "standard"}}
        docs = [{"message": value} for value in
                ("Denied error", "ERROR denied", "error only", "denied only", "error x denied", "neither")]
        self.assertEqual(evaluate("message:error denied", mapping, docs), [0, 1, 2, 3, 4])
        self.assertEqual(evaluate('message:"error denied"', mapping, docs), [1])
        self.assertEqual(evaluate("message:(error AND denied)", mapping, docs), [0, 1, 4])
        self.assertEqual(evaluate('message:"denied error"', mapping, docs), [0])

    def test_keyword_multiword_is_one_exact_value(self):
        mapping = {"label": keyword()}
        docs = [{"label": value} for value in ("foo bar", "foo", "bar", "foo  bar", "bar foo")]
        self.assertEqual(evaluate("label:foo bar", mapping, docs), [0])
        self.assertEqual(evaluate("label:foo  bar", mapping, docs), [3])
        self.assertEqual(evaluate('label:"foo bar"', mapping, docs), [0])

    def test_boolean_precedence_missing_fields_and_groups(self):
        mapping = {field: keyword() for field in ("a", "b", "c")}
        docs = [{"a": "yes", "c": "yes"}, {"b": "yes"}, {"b": "yes", "c": "yes"}, {}, {"a": "no"}]
        self.assertEqual(evaluate("a:yes oR b:yes aNd nOt c:yes", mapping, docs), [0, 1])
        self.assertEqual(evaluate("(a:yes OR b:yes) AND NOT c:yes", mapping, docs), [1])
        self.assertEqual(evaluate("NOT (a:yes OR b:yes)", mapping, docs), [3, 4])
        self.assertEqual(evaluate("NOT (NOT a:yes)", mapping, docs), [0])
        self.assertEqual(evaluate("", mapping, docs), [0, 1, 2, 3, 4])

    def test_field_group_and_array_members(self):
        mapping = {"tags": keyword()}
        docs = [{"tags": ["production", "blue"]}, {"tags": ["production", "deprecated"]},
                {"tags": ["blue"]}, {}, {"tags": []}]
        self.assertEqual(evaluate("tags:(production AND NOT deprecated)", mapping, docs), [0])
        self.assertEqual(evaluate("tags:(production OR blue)", mapping, docs), [0, 1, 2])

    def test_exists_empty_null_arrays_ignore_above_and_null_value(self):
        mapping = {"k": keyword(), "short": keyword(ignore_above=3), "nullable": keyword(null_value="NIL"),
                   "message": {"type": "text"}}
        docs = [{"k": "", "short": "abc", "nullable": None, "message": ""},
                {"k": None, "short": "abcd", "message": None},
                {"k": [], "short": None, "nullable": []},
                {"k": [None, "x"], "short": ["toolong", "ok"], "nullable": [None]},
                {"short": "", "nullable": ""}, {"k": "*"}]
        self.assertEqual(evaluate("k:*", mapping, docs), [0, 3, 5])
        self.assertEqual(evaluate("k:**", mapping, docs), [0, 3, 5])
        self.assertEqual(evaluate('k:"*"', mapping, docs), [5])
        self.assertEqual(evaluate(r"k:\*", mapping, docs), [5])
        self.assertEqual(evaluate("short:*", mapping, docs), [0, 3, 4])
        self.assertEqual(evaluate("nullable:*", mapping, docs), [0, 3, 4])
        self.assertEqual(evaluate("nullable:NIL", mapping, docs), [0, 3])
        self.assertEqual(evaluate('short:""', mapping, docs), [4])
        self.assertEqual(evaluate("message:*", mapping, docs), [0])

    def test_wildcard_star_and_literal_question_and_star(self):
        mapping = {"code": keyword(), "fold": keyword(normalizer="lowercase")}
        values = ("svc", "svc-prod", "svc?prod", "svc*prod", "Svc-prod", "xsvc-prod", "svcxprod")
        docs = [{"code": value, "fold": value} for value in values]
        self.assertEqual(evaluate("code:svc*", mapping, docs), [0, 1, 2, 3, 6])
        self.assertEqual(evaluate("code:*svc*", mapping, docs), [0, 1, 2, 3, 5, 6])
        self.assertEqual(evaluate("fold:SVC*", mapping, docs), [0, 1, 2, 3, 4, 6])
        self.assertEqual(evaluate("code:svc?*", mapping, docs), [2])
        self.assertEqual(evaluate(r"code:svc\?*", mapping, docs), [2])
        self.assertEqual(evaluate(r"code:svc\**", mapping, docs), [3])
        self.assertEqual(evaluate("code:svc?prod", mapping, docs), [2])
        self.assertEqual(evaluate('code:"svc*prod"', mapping, docs), [3])

    def test_text_wildcard_normalizes_but_does_not_cross_terms(self):
        mapping = {"message": {"type": "text"}, "label": keyword()}
        docs = [{"message": "ERROR denied", "label": "ERR one denied"},
                {"message": "terror denied", "label": "ERR denied"}, {"message": "Erroring"}]
        self.assertEqual(evaluate("message:ERR*", mapping, docs), [0, 2])
        self.assertEqual(evaluate("label:ERR* denied", mapping, docs), [0, 1])
        with self.assertRaisesRegex(ElasticKqlError, "boşluklu"):
            evaluate("message:ERR* denied", mapping, docs)

    def test_ranges_exact_below_equal_above_and_arrays(self):
        mapping = {"count": {"type": "integer"}, "ratio": {"type": "double"}}
        docs = [{"count": value, "ratio": value / 10} for value in (9, 10, 11, 19, 20, 21)] + [{}, {"count": [5, 25]}]
        self.assertEqual(evaluate("count >= 10 AND count <= 20", mapping, docs), [1, 2, 3, 4, 7])
        self.assertEqual(evaluate("count > 10 AND count < 20", mapping, docs), [2, 3, 7])
        self.assertEqual(evaluate("count:10", mapping, docs), [1])
        self.assertEqual(evaluate("ratio >= 1.0 AND ratio < 2.0", mapping, docs), [1, 2, 3])
        self.assertEqual(evaluate("count < -1", mapping, docs), [])

    def test_dates_have_typed_utc_boundaries(self):
        mapping = {"@timestamp": {"type": "date"}}
        docs = [{"@timestamp": value} for value in
                ("2026-10-21T08:59:59Z", "2026-10-21T09:00:00Z", "2026-10-21T09:00:01Z",
                 "2026-10-21T09:04:59Z", "2026-10-21T09:05:00Z", "2026-10-21T12:00:00+03:00")]
        query = '@timestamp >= "2026-10-21T09:00:00Z" AND @timestamp < "2026-10-21T09:05:00Z"'
        self.assertEqual(evaluate(query, mapping, docs), [1, 2, 3, 5])
        self.assertEqual(evaluate('@timestamp:"2026-10-21T09:00:00Z"', mapping, docs), [1, 5])

    def test_escapes_colon_spaces_quotes_and_keywords(self):
        mapping = {"value": keyword()}
        docs = [{"value": value} for value in
                ("https://example.test/", "hello world", "AND", 'a"b', "foo~1", "a\\b")]
        cases = [(r"value:https\://example.test/", [0]), (r"value:hello\ world", [1]),
                 (r"value:\AND", [2]), ('value:"AND"', [2]), ('value:"a\\\"b"', [3]),
                 ('value:"foo~1"', [4]), ('value:"a\\\\b"', [5])]
        for query, expected in cases:
            with self.subTest(query=query):
                self.assertEqual(evaluate(query, mapping, docs), expected)

    def test_nested_conditions_share_a_child(self):
        mapping = {"users": {"type": "nested"}, "users.name": keyword(), "users.role": keyword()}
        docs = [{"users": [{"name": "alice", "role": "user"}, {"name": "bob", "role": "admin"}]},
                {"users": [{"name": "alice", "role": "admin"}]},
                {"users": [{"name": "bob", "role": "user"}]}, {}, {"users": []},
                {"users": {"name": "alice", "role": "admin"}}, {"users": [None, {"name": "alice", "role": "admin"}]}]
        self.assertEqual(evaluate("users:{name:alice AND role:admin}", mapping, docs), [1, 5, 6])
        self.assertEqual(evaluate("users:{name:alice} AND users:{role:admin}", mapping, docs), [0, 1, 5, 6])
        self.assertEqual(evaluate("NOT users:{name:alice AND role:admin}", mapping, docs), [0, 2, 3, 4])
        self.assertEqual(evaluate("users:{name:alice AND role:admin}", mapping, []), [])

    def test_nested_full_path_and_deeper_nested_scope(self):
        mapping = {"users": {"type": "nested"}, "users.names": {"type": "nested"},
                   "users.names.first": keyword(), "users.names.last": keyword()}
        docs = [{"users": [{"names": [{"first": "Alice", "last": "Black"}, {"first": "John", "last": "White"}]}]},
                {"users": [{"names": [{"first": "Alice", "last": "White"}]}]}]
        for query in ('users.names:{first:"Alice" AND last:"White"}',
                      'users:{names:{first:"Alice" AND last:"White"}}'):
            with self.subTest(query=query):
                self.assertEqual(evaluate(query, mapping, docs), [1])

    def test_explicit_rejections_do_not_become_literal_queries(self):
        mapping = {"user": keyword(), "count": {"type": "integer"}, "users": {"type": "nested"}, "users.name": keyword()}
        invalid = ["user:", "user:()", "user:alice OR", "user:alice AND OR user:bob", "(user:alice", "user:alice)",
                   'user:"alice" trailing', "user:alice count:10", "unknown:x", "user.*:alice", "alice", "*", "*:x",
                   "user:alice~1", 'user:"alice"~1', "user:/ali.*/", "user:[a TO z]", "user:alice^2", "user:a && user:b",
                   "count:1*", "users:{name:alice", "user:{name:alice}", "users.name:alice", "user:\\", 'user:"unterminated',
                   "user:null", "NOT(user:alice)", "user:alice OR(user:bob)", "NOT NOT user:alice"]
        for query in invalid:
            with self.subTest(query=query), self.assertRaises(ElasticKqlError):
                parse(query, mapping)

    def test_resources_and_wrong_data_fail_explicitly(self):
        for query in (None, "user:a\0", "x" * 16001):
            with self.subTest(query=query), self.assertRaises(ElasticKqlError):
                parse(query, {"user": keyword()})
        with self.assertRaises(ElasticKqlError):
            parse("(" * 60 + "user:a" + ")" * 60, {"user": keyword()})
        with self.assertRaises(ElasticKqlError):
            evaluate("user:a", {"user": keyword()}, [{} , 1])
        with self.assertRaises(ElasticKqlError):
            evaluate(r"field\ name:a", {"field name": keyword()}, [])
        with self.assertRaisesRegex(ValueError, "index:false"):
            evaluate("hidden:*", {"hidden": keyword(index=False)}, [{"hidden": "yes"}])


if __name__ == "__main__":
    unittest.main()
