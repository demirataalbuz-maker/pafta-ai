"""Student query execution; never execute query text as Python or shell code."""
import copy
import json
from pathlib import Path

try:
    from .elastic_common import ElasticError, corpus, selected_documents, sorted_documents
    from . import elastic_kql, elastic_lucene, elastic_eql
except ImportError:
    from elastic_common import ElasticError, corpus, selected_documents, sorted_documents
    import elastic_kql
    import elastic_lucene
    import elastic_eql


def options(stdin=""):
    if not stdin.strip():
        path = Path(__file__).resolve().parents[1] / "tracks" / "elastic" / "corpora" / "temel.json"
        stdin = path.read_text(encoding="utf-8")
    return corpus(stdin)


def evaluate(query, config):
    config = corpus(config)
    if not isinstance(query, str) or not query.strip() or len(query.encode("utf-8")) > 16000 or "\0" in query:
        raise ElasticError("Sorgu 1..16000 UTF-8 baytlık NUL içermeyen metin olmalı.")
    documents = selected_documents(config)
    dialect = config["dil"]
    if dialect == "eql":
        if "sort" in config["context"]:
            raise ElasticError("EQL context.sort kabul etmez; sıra timestamp_field ve tiebreaker_field ile kurulur.")
        context = {k: v for k, v in config["context"].items() if k in ("timestamp_field", "event_category_field", "tiebreaker_field")}
        return elastic_eql.evaluate(query, config["mapping"], documents, context)
    native = elastic_kql if dialect == "kibana" else elastic_lucene
    indices = native.evaluate(query, config["mapping"], documents)
    matched = sorted_documents([documents[i] for i in indices], config)
    return [doc["id"] for doc in matched]


def run(code, stdin=""):
    if _native(stdin):
        try:
            from .elastic_lab import run as native_run
        except ImportError:
            from elastic_lab import run as native_run
        return native_run(code, stdin)
    config = options(stdin)
    matches = evaluate(code, config)
    lines = [" -> ".join(row) if isinstance(row, list) else row for row in matches]
    out = "\n".join(lines) + ("\n" if lines else "")
    return {"status": "ok", "error": None, "segs": [["out", out]],
            "tablolar": [{"satir": 1, "sutunlar": ["Eşleşen belge / olay dizisi"], "satirlar": [[line] for line in lines]}],
            "elastic_ids": matches, "elastic_dialect": config["dil"],
            "elastic_backend": "Apache Lucene " + elastic_lucene.VERSION if config["dil"] != "eql" else "Pafta sınırlı EQL"}


def test_helpers(code, stdin=""):
    if _native(stdin):
        try:
            from .elastic_lab import test_helpers as native_helpers
        except ImportError:
            from elastic_lab import test_helpers as native_helpers
        return native_helpers(code, stdin)
    config = options(stdin)
    initial = evaluate(code, config)  # Even empty assertion suites cannot accept an invalid query.
    def merged(value, dialect=None):
        if value is None:
            result = copy.deepcopy(config)
        elif isinstance(value, list):
            result = dict(copy.deepcopy(config), documents=value)
        elif isinstance(value, dict):
            result = dict(copy.deepcopy(config), **copy.deepcopy(value))
        else:
            raise ElasticError("Test verisi belge listesi veya corpus nesnesi olmalı.")
        if dialect:
            result["dil"] = dialect
        return result
    return {"src": code,
            "eslesenler": lambda veri=None: list(initial) if veri is None else evaluate(code, merged(veri)),
            "referans": lambda sorgu, veri=None, dil=None: evaluate(sorgu, merged(veri, dil)),
            "korpus": copy.deepcopy(config)}


def _native(stdin):
    try:
        value = json.loads(stdin) if isinstance(stdin, str) else stdin
    except (ValueError, TypeError):
        return False
    return isinstance(value, dict) and value.get("backend") == "elastic"
