"""Bounded Kibana KQL parser backed by native Apache Lucene queries.

This adapter implements field matches/phrases, *, comparisons, Boolean groups
and same-child nested blocks. Native Lucene supplies analysis, normalization,
indexed-value existence and typed comparisons. It is not an Elasticsearch
server: field-name wildcards, fieldless queries, date math, custom analyzers
and Lucene regexp/fuzzy/slop/boost syntax are rejected explicitly. Whitespace
inside text wildcard patterns is rejected (Kibana delegates these to a separate
query_string parser); keyword wildcard patterns may contain whitespace. Leading
value wildcards are enabled. Unquoted text uses match's default OR operator.
Field names use the shared ASCII ECS-style name contract. Date values require
explicit-zone ISO timestamps or native numeric epoch values; date math and
partial dates are not inferred. Bare null is rejected; quote literal "null".

Syntax sources (reviewed 2026-10-21):
https://www.elastic.co/docs/reference/query-languages/kql
https://github.com/elastic/kibana/blob/main/src/platform/packages/shared/kbn-es-query/src/kuery/functions/is.ts
The parser below is an original implementation, not copied Kibana code.
"""
from dataclasses import dataclass
import re

try:
    from . import elastic_lucene
except ImportError:
    import elastic_lucene

MAX_QUERY_BYTES = 16000
MAX_DEPTH = 48
MAX_TOKENS = 2048


class ElasticKqlError(ValueError):
    """Unsupported or invalid KQL; never silently evaluated as another language."""


@dataclass(frozen=True)
class _Token:
    kind: str
    value: str
    pattern: str
    start: int
    end: int
    quoted: bool = False
    wildcard: bool = False


def _pattern_char(char):
    return "\\" + char if char in "*?\\" else char


def _escape(query, position, quoted):
    """Decode one KQL escape; quoted unknown escapes remain literal."""
    if position + 1 >= len(query):
        raise ElasticKqlError("Sonda tamamlanmamış kaçış var.")
    following = query[position + 1]
    if following in ('"', "\\"):
        return following, position + 2
    if following in "tnr":
        return {"t": "\t", "n": "\n", "r": "\r"}[following], position + 2
    if following == "u":
        digits = query[position+2:position+6]
        if len(digits) != 4 or any(c not in "0123456789abcdefABCDEF" for c in digits):
            raise ElasticKqlError("Unicode kaçışı dört hex hane gerektirir.")
        value = int(digits, 16)
        if 0xd800 <= value <= 0xdfff:
            raise ElasticKqlError("Bu tezgâhta Unicode kaçışı tek bir Unicode karakteri olmalı.")
        return chr(value), position + 6
    if quoted:
        return "\\" + following, position + 2
    for word in ("and", "not", "or"):
        if query[position+1:position+1+len(word)].lower() == word:
            return query[position+1:position+1+len(word)], position+1+len(word)
    if following in "():<>*{}?~^[]/" or following.isspace():
        return following, position + 2
    raise ElasticKqlError("Desteklenmeyen kaçış: \\" + following)


def _lex(query):
    tokens, position = [], 0
    while position < len(query):
        if query[position].isspace():
            position += 1
            continue
        start, char = position, query[position]
        if char in ":(){}<>":
            position += 1
            value = char
            if char in "<>" and position < len(query) and query[position] == "=":
                value += "="
                position += 1
            tokens.append(_Token(value, value, value, start, position))
        elif char == '"':
            position += 1
            value = []
            while position < len(query) and query[position] != '"':
                if query[position] == "\\":
                    part, position = _escape(query, position, True)
                    value.append(part)
                else:
                    value.append(query[position])
                    position += 1
            if position >= len(query):
                raise ElasticKqlError("Kapanmamış çift tırnak.")
            position += 1
            value = "".join(value)
            tokens.append(_Token("VALUE", value, "".join(map(_pattern_char, value)), start, position, True))
        else:
            value, pattern, wildcard, escaped = [], [], False, False
            while position < len(query) and not query[position].isspace() and query[position] not in ':(){}<>"':
                char = query[position]
                if char == "\\":
                    part, position = _escape(query, position, False)
                    value.append(part)
                    pattern.extend(_pattern_char(c) for c in part)
                    escaped = True
                else:
                    if char in "~^[]=|&":
                        raise ElasticKqlError("KQL dışında sorgu işleci; literal değer için çift tırnak kullanın: " + char)
                    value.append(char)
                    wildcard |= char == "*"
                    pattern.append("*" if char == "*" else _pattern_char(char))
                    position += 1
            if position == start:
                raise ElasticKqlError("Beklenmeyen karakter: " + query[position])
            value = "".join(value)
            kind = value.upper() if not escaped and value.upper() in ("AND", "OR", "NOT") else "VALUE"
            if kind in ("AND", "OR") and (start == 0 or not query[start-1].isspace()
                                              or position == len(query) or not query[position].isspace()):
                raise ElasticKqlError("AND/OR sözcüklerinin iki yanında boşluk gerekli; literal için tırnak kullanın.")
            if kind == "NOT" and (position == len(query) or not query[position].isspace()):
                raise ElasticKqlError("NOT sonrasında boşluk gerekli; literal için tırnak kullanın.")
            tokens.append(_Token(kind, value, "".join(pattern), start, position, False, wildcard))
        if len(tokens) > MAX_TOKENS:
            raise ElasticKqlError("Sorguda en fazla 2048 sözcük/işaret olabilir.")
    tokens.append(_Token("EOF", "", "", len(query), len(query)))
    return tokens


def _spec(mapping, field):
    value = mapping.get(field)
    return {"type": value} if isinstance(value, str) else value


def _nested_paths(mapping):
    return [field for field in mapping if (_spec(mapping, field) or {}).get("type") == "nested"]


def _parent_nested(field, paths):
    ancestors = [path for path in paths if field.startswith(path + ".")]
    return max(ancestors, key=len, default="")


class _Parser:
    def __init__(self, query, mapping):
        self.query, self.mapping = query, mapping
        self.tokens, self.index, self.depth = _lex(query), 0, 0
        self.paths = _nested_paths(mapping)

    def token(self):
        return self.tokens[self.index]

    def take(self, kind=None):
        token = self.token()
        if kind is not None and token.kind != kind:
            raise ElasticKqlError(f"{token.start+1}. karakterde {kind} bekleniyor; gelen {token.value or 'sorgu sonu'}.")
        self.index += 1
        return token

    def expression(self, prefix="", field=None):
        self.depth += 1
        if self.depth > MAX_DEPTH:
            raise ElasticKqlError("En fazla 48 iç içe grup desteklenir.")
        try:
            return self.disjunction(prefix, field)
        finally:
            self.depth -= 1

    def disjunction(self, prefix, field):
        nodes = [self.conjunction(prefix, field)]
        while self.token().kind == "OR":
            self.take()
            nodes.append(self.conjunction(prefix, field))
        return nodes[0] if len(nodes) == 1 else {"op": "or", "args": nodes}

    def conjunction(self, prefix, field):
        nodes = [self.negation(prefix, field)]
        while self.token().kind == "AND":
            self.take()
            nodes.append(self.negation(prefix, field))
        return nodes[0] if len(nodes) == 1 else {"op": "and", "args": nodes}

    def negation(self, prefix, field):
        count = 0
        while self.token().kind == "NOT":
            self.take()
            count += 1
            if count > 1:
                raise ElasticKqlError("Ardışık NOT için parantezli grup gerekli: NOT (NOT alan:değer).")
        node = self.primary(prefix, field)
        for _ in range(count):
            node = {"op": "not", "arg": node}
        return node

    def full_field(self, token, prefix):
        if token.wildcard:
            raise ElasticKqlError("Bu tezgâhta alan adında joker desteklenmiyor; alanı açık yazın.")
        field = token.value
        if prefix and not field.startswith(prefix + "."):
            field = prefix + "." + field
        if field not in self.mapping:
            raise ElasticKqlError("Mapping içinde tanımlı olmayan alan: " + field)
        return field

    def primary(self, prefix, default_field):
        if self.token().kind == "(":
            self.take()
            node = self.expression(prefix, default_field)
            self.take(")")
            return node
        if default_field is not None:
            return self.value(default_field)
        token = self.take("VALUE")
        if self.token().kind not in (":", ">", ">=", "<", "<="):
            raise ElasticKqlError("Bu tezgâh alansız aramayı desteklemiyor; alan: değer yazın.")
        field = self.full_field(token, prefix)
        operator = self.take().kind
        if operator == ":" and self.token().kind == "{":
            if field not in self.paths:
                raise ElasticKqlError("{...} yalnız mapping türü nested olan alanda kullanılır: " + field)
            if prefix and not field.startswith(prefix + "."):
                raise ElasticKqlError("Nested blok mevcut kapsamın altında olmalı.")
            self.take()
            node = self.expression(field)
            self.take("}")
            return {"op": "nested", "path": field, "arg": node}
        if field in self.paths:
            raise ElasticKqlError("Nested alanı path:{ ... } biçiminde sorgulayın: " + field)
        if _parent_nested(field, self.paths) != prefix:
            raise ElasticKqlError("Nested alt alanı aynı çocuk kapsamındaki {...} bloğunda sorgulayın: " + field)
        if operator != ":":
            token = self.literal()
            if token.wildcard:
                raise ElasticKqlError("Aralık sınırında joker kullanılamaz.")
            return {"op": "range", "field": field, "cmp": {">": "gt", ">=": "gte", "<": "lt", "<=": "lte"}[operator], "value": token.value}
        if self.token().kind == "(":
            self.take()
            node = self.expression(prefix, field)
            self.take(")")
            return node
        return self.value(field)

    def literal(self):
        first = self.take("VALUE")
        if first.quoted:
            return first
        pieces, patterns, last, wildcard = [first.value], [first.pattern], first, first.wildcard
        while self.token().kind == "VALUE" and not self.token().quoted:
            token = self.take()
            gap = self.query[last.end:token.start]
            if not gap or not gap.isspace():
                raise ElasticKqlError("Değerler arasında işaret veya açık bir mantık işleci gerekli.")
            pieces.extend((gap, token.value))
            patterns.extend((gap, token.pattern))
            wildcard |= token.wildcard
            last = token
        value = "".join(pieces)
        if value.startswith("/") and value.endswith("/") and len(value) > 1:
            raise ElasticKqlError("KQL regex /.../ desteklemez; literal için çift tırnak kullanın.")
        return _Token("VALUE", value, "".join(patterns), first.start, last.end, False, wildcard)

    def value(self, field):
        token = self.literal()
        if not token.quoted and token.value == "null":
            raise ElasticKqlError('Tırnaksız null değer sorgusu desteklenmiyor; varlık için alan: *, literal metin için "null" yazın.')
        if token.wildcard:
            if token.pattern and set(token.pattern) == {"*"}:
                return {"op": "exists", "field": field}
            if (_spec(self.mapping, field) or {}).get("type") not in ("keyword", "text"):
                raise ElasticKqlError("Joker yalnız keyword/text alanında kullanılabilir: " + field)
            if (_spec(self.mapping, field) or {}).get("type") == "text" and any(c.isspace() for c in token.value):
                raise ElasticKqlError("Text alanında boşluklu joker değeri desteklenmiyor; ayrı AND/OR koşulları yazın.")
            return {"op": "wildcard", "field": field, "pattern": token.pattern}
        return {"op": "match", "field": field, "value": token.value, "phrase": token.quoted}


def parse(query, mapping):
    """Return the supported KQL AST, retaining nested blocks until evaluation."""
    if not isinstance(query, str) or "\0" in query:
        raise ElasticKqlError("KQL sorgusu NUL içermeyen metin olmalı.")
    try:
        size = len(query.encode("utf-8"))
    except UnicodeError as exc:
        raise ElasticKqlError("Sorgu geçerli UTF-8 olmalı.") from exc
    if size > MAX_QUERY_BYTES:
        raise ElasticKqlError("KQL sorgusu en fazla 16000 UTF-8 bayt olabilir.")
    if not isinstance(mapping, dict) or any(not isinstance(k, str) or not isinstance(v, (str, dict)) for k, v in mapping.items()):
        raise ElasticKqlError("Mapping alan adından tür sözlüğüne eşleme olmalı.")
    if any(re.fullmatch(r"[A-Za-z@][A-Za-z0-9_.@-]*", field) is None for field in mapping):
        raise ElasticKqlError("Bu tezgâhta alan adları harf/@ ile başlayıp harf, rakam, _, ., @ veya - içermeli.")
    if not query.strip():
        return {"op": "not", "arg": {"op": "ids", "indices": []}}
    parser = _Parser(query, mapping)
    ast = parser.expression()
    parser.take("EOF")
    return ast


def _path_values(value, parts):
    if not parts:
        return [value]
    if isinstance(value, dict):
        joined = ".".join(parts)
        if joined in value:
            return [value[joined]]
        if parts[0] in value:
            return _path_values(value[parts[0]], parts[1:])
    elif isinstance(value, list):
        result = []
        for item in value:
            result.extend(_path_values(item, parts))
        return result
    return []


def _children(doc, path):
    result = []
    for value in _path_values(doc, path.split(".")):
        values = value if isinstance(value, list) else [value]
        for child in values:
            if child is None:
                continue
            if not isinstance(child, dict):
                raise ElasticKqlError("Nested veri nesne veya nesne dizisi olmalı: " + path)
            result.append(child)
    return result


def _flatten_child(child, prefix, paths):
    result = {}
    for name, value in child.items():
        field = name if name.startswith(prefix + ".") else prefix + "." + name
        if isinstance(value, dict) and field not in paths:
            result.update(_flatten_child(value, field, paths))
        else:
            result[field] = value
    return result


def _scope_evaluate(ast, mapping, documents, scope=""):
    paths = _nested_paths(mapping)

    def lower(node):
        operation = node["op"]
        if operation in ("and", "or"):
            return {"op": operation, "args": [lower(child) for child in node["args"]]}
        if operation == "not":
            return {"op": operation, "arg": lower(node["arg"])}
        if operation != "nested":
            return node
        child_documents, owners = [], []
        path = node["path"]
        for owner, document in enumerate(documents):
            for child in _children(document, path):
                child_documents.append(_flatten_child(child, path, paths))
                owners.append(owner)
        matched = _scope_evaluate(node["arg"], mapping, child_documents, path)
        return {"op": "ids", "indices": sorted({owners[index] for index in matched})}

    lowered = lower(ast)
    selected_mapping = {field: _spec(mapping, field) for field in mapping
                        if field not in paths and _parent_nested(field, paths) == scope}
    if not selected_mapping:
        # A scope containing only nested children still needs a real index for
        # its ids/Boolean AST. No user value is indexed in this sentinel field.
        selected_mapping = {"PaftaKqlEmptyScope": {"type": "keyword"}}
    index_documents = [{field: document[field] for field in selected_mapping if field in document}
                       for document in documents]
    return elastic_lucene.evaluate_ast(lowered, selected_mapping, index_documents)


def evaluate(query, mapping, documents):
    """Return matching original document indices; every leaf runs in Lucene."""
    if not isinstance(documents, list) or any(not isinstance(doc, dict) for doc in documents):
        raise ElasticKqlError("Belgeler sözlük listesi olmalı.")
    return _scope_evaluate(parse(query, mapping), mapping, documents)
