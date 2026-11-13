"""A bounded, independent local interpreter for Elasticsearch EQL.

This is not an Elasticsearch server and does not use Endgame's Python ``eql``.
Supported: scalar event predicates, common/per-stage join keys, ascending
sequences, maxspan (inclusive), until, and *middle* missing clauses. There are
no functions, arithmetic, regex, pipes, runs, samples, outer missing clauses,
arrays, nested/text queries, signed-negative zero, normalizers or custom mapping null/index options.
Case-insensitive predicates are deliberately restricted to ASCII values.

Sequence semantics were checked against Elasticsearch v9.2.0 SequenceMatcher,
OrdinalGroup and Ordinal, rather than enumerating Cartesian candidate pairs:
https://github.com/elastic/elasticsearch/blob/v9.2.0/x-pack/plugin/eql/src/main/java/org/elasticsearch/xpack/eql/execution/sequence/SequenceMatcher.java
https://github.com/elastic/elasticsearch/blob/v9.2.0/x-pack/plugin/eql/src/main/java/org/elasticsearch/xpack/eql/execution/sequence/OrdinalGroup.java
https://github.com/elastic/elasticsearch/blob/v9.2.0/x-pack/plugin/eql/src/main/java/org/elasticsearch/xpack/eql/execution/search/Ordinal.java
https://www.elastic.co/docs/reference/query-languages/eql/eql-syntax

Corpora use flat ECS keys, unique string ``id`` (``event.id`` fallback), ISO
timestamps with a zone and up to nine fractional digits. Configured timestamp
and tiebreaker tuples must be unique: implicit Elasticsearch shard ordering is
not simulated. Backslashes escape EQL strings, not wildcard metacharacters.
"""
from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import math
import re


class EqlError(ValueError):
    """Invalid query, unsupported syntax, mapping, or local corpus contract."""


MAX_QUERY = 16384
MAX_DOCUMENTS = 5000
MAX_TOKENS = 2048
TYPES = {"keyword", "long", "integer", "double", "boolean", "date", "date_nanos", "text", "nested", "object"}
RESERVED = {"and", "or", "not", "where", "by", "with", "maxspan", "sequence", "until", "in", "in~", "like", "like~", "true", "false", "null", "any", "sample", "join", "regex", "regex~"}
NUMBER = re.compile(r"(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")
IDENT = re.compile(r"[A-Za-z_@][A-Za-z_0-9]*(?:~)?")
DATE = re.compile(r"(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})(?:\.(\d{1,9}))?(Z|[+-]\d{2}:\d{2})\Z")


def _date(value):
    if not isinstance(value, str) or not (m := DATE.fullmatch(value)):
        raise EqlError("EQL tarihleri zonlu ISO-8601 metni olmalı (en çok 9 kesir basamağı).")
    try:
        zone = "+00:00" if m[4] == "Z" else m[4]
        hours, minutes = int(zone[1:3]), int(zone[4:])
        if hours > 18 or minutes > 59 or hours == 18 and minutes != 0:
            raise ValueError()
        instant = datetime.fromisoformat(m[1] + "T" + m[2] + zone).astimezone(timezone.utc)
        delta = instant - datetime(1970, 1, 1, tzinfo=timezone.utc)
        return (delta.days * 86400 + delta.seconds) * 1_000_000_000 + int((m[3] or "").ljust(9, "0"))
    except (ValueError, OverflowError) as exc:
        raise EqlError("Geçersiz EQL tarihi: " + value) from exc


def _mapping(mapping):
    if not isinstance(mapping, dict):
        raise EqlError("EQL mapping alan adı → type sözlüğü olmalı.")
    result = {}
    for name, spec in mapping.items():
        if not isinstance(name, str) or not name:
            raise EqlError("Mapping alan adı boş olamaz.")
        if isinstance(spec, str):
            kind = spec
        elif isinstance(spec, dict):
            if set(spec) - {"type"}:
                raise EqlError("Yerel EQL özel mapping seçeneklerini desteklemez: " + name)
            kind = spec.get("type")
        else:
            raise EqlError("Geçersiz mapping: " + name)
        if kind not in TYPES:
            raise EqlError("Desteklenmeyen EQL alan türü: " + str(kind))
        result[name] = kind
    return result


@dataclass(frozen=True)
class Token:
    kind: str
    value: object
    pos: int


def _tokens(query):
    if not isinstance(query, str) or not query.strip() or len(query.encode("utf-8")) > MAX_QUERY or "\0" in query:
        raise EqlError("EQL sorgusu boş olamaz ve en fazla 16 kB olabilir.")
    out, i = [], 0
    while i < len(query):
        start, c = i, query[i]
        if c.isspace():
            i += 1
            continue
        if query.startswith("//", i):
            end = query.find("\n", i)
            i = len(query) if end < 0 else end + 1
            continue
        if query.startswith("/*", i):
            depth, i = 1, i + 2
            while i < len(query) and depth:
                if query.startswith("/*", i):
                    depth, i = depth + 1, i + 2
                elif query.startswith("*/", i):
                    depth, i = depth - 1, i + 2
                else:
                    i += 1
            if depth:
                raise EqlError("Kapanmamış EQL yorumu.")
            continue
        if query.startswith('"""', i):
            end = query.find('"""', i + 3)
            if end < 0 or "\n" in query[i + 3:end] or "\r" in query[i + 3:end]:
                raise EqlError("Kapanmamış veya çok satırlı raw EQL metni.")
            out.append(Token("str", query[i + 3:end], start))
            i = end + 3
        elif c == '"':
            i, value = i + 1, []
            while i < len(query) and query[i] != '"':
                char = query[i]
                if char in "\n\r":
                    raise EqlError("EQL metin sabiti tek satırlı olmalı.")
                if char == "\\":
                    i += 1
                    if i >= len(query):
                        raise EqlError("Eksik EQL kaçışı.")
                    esc = query[i]
                    simple = {"n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f", '"': '"', "\\": "\\"}
                    if esc == "u" and i + 1 < len(query) and query[i + 1] == "{":
                        end = query.find("}", i + 2)
                        digits = query[i + 2:end] if end >= 0 else ""
                        if not re.fullmatch(r"[0-9A-Fa-f]{2,8}", digits):
                            raise EqlError("Unicode kaçışı \\u{2–8 hex} biçiminde olmalı.")
                        code = int(digits, 16)
                        if code > 0x10ffff or 0xd800 <= code <= 0xdfff:
                            raise EqlError("Geçersiz Unicode kod noktası.")
                        value.append(chr(code))
                        i = end
                    elif esc in simple:
                        value.append(simple[esc])
                    else:
                        raise EqlError("Desteklenmeyen EQL metin kaçışı: \\" + esc)
                else:
                    value.append(char)
                i += 1
            if i == len(query):
                raise EqlError("Kapanmamış EQL metin sabiti.")
            out.append(Token("str", "".join(value), start))
            i += 1
        elif c == "`":
            i, value = i + 1, []
            while i < len(query):
                if query.startswith("``", i):
                    value.append("`"); i += 2
                elif query[i] == "`":
                    i += 1
                    break
                else:
                    value.append(query[i]); i += 1
            else:
                raise EqlError("Kapanmamış EQL alan adı.")
            out.append(Token("quoted", "".join(value), start))
        elif (match := NUMBER.match(query, i)):
            text = match[0]
            try:
                value = float(text) if any(x in text for x in ".eE") else int(text)
                if isinstance(value, float) and not math.isfinite(value):
                    raise ValueError()
                if isinstance(value, int) and not 0 <= value <= 2**63:
                    raise ValueError()
            except ValueError as exc:
                raise EqlError("EQL sayı sabiti desteklenen sınırın dışında.") from exc
            out.append(Token("num", value, start)); i = match.end()
        elif (match := IDENT.match(query, i)):
            value = match[0]
            out.append(Token(value if value in RESERVED else "id", value, start)); i = match.end()
        else:
            pair = query[i:i + 2]
            if pair in ("==", "!=", "<=", ">=", "!["):
                out.append(Token(pair, pair, start)); i += 2
            elif c in "[](),.:?<>+-=":
                out.append(Token(c, c, start)); i += 1
            else:
                raise EqlError("Desteklenmeyen EQL karakteri, konum " + str(i) + ": " + c)
        if len(out) > MAX_TOKENS:
            raise EqlError("EQL sorgusunda çok fazla token var.")
    return out + [Token("eof", "", len(query))]


@dataclass(frozen=True)
class Field:
    name: str
    optional: bool
    kind: str | None


@dataclass
class Stage:
    category: str | None
    condition: tuple
    keys: list[Field] = field(default_factory=list)
    missing: bool = False


class Parser:
    def __init__(self, query, mapping):
        self.tokens, self.i, self.mapping, self.depth = _tokens(query), 0, mapping, 0
        self.used = {}

    @property
    def token(self):
        return self.tokens[self.i]

    def accept(self, kind):
        if self.token.kind == kind:
            token = self.token
            self.i += 1
            return token
        return None

    def need(self, kind):
        token = self.accept(kind)
        if token is None:
            raise EqlError("EQL konum " + str(self.token.pos) + ": beklenen " + kind + ", gelen " + str(self.token.value))
        return token

    def field(self):
        optional = bool(self.accept("?"))
        if self.token.kind not in ("id", "quoted"):
            self.need("id")
        parts = [str(self.token.value)]; self.i += 1
        while self.accept("."):
            if self.token.kind not in ("id", "quoted"):
                self.need("id")
            parts.append(str(self.token.value)); self.i += 1
        name = ".".join(parts)
        kind = self.mapping.get(name)
        if kind is None and not optional:
            raise EqlError("EQL mapping alanı yok: " + name + "; gerekiyorsa ? ile opsiyonel yap.")
        if kind in ("text", "nested", "object") or any(self.mapping.get(".".join(parts[:n])) == "nested" for n in range(1, len(parts))):
            raise EqlError("Yerel EQL text/nested/object alanını sorgulamaz: " + name)
        result = Field(name, optional, kind)
        self.used[name] = result
        return result

    def keys(self):
        result = [self.field()]
        while self.accept(","):
            result.append(self.field())
        if len(result) > 8:
            raise EqlError("Yerel EQL en fazla 8 join anahtarı destekler.")
        return result

    def primary(self):
        self.depth += 1
        if self.depth > 64:
            raise EqlError("EQL ifade derinliği 64'ü aşamaz.")
        try:
            if self.accept("("):
                value = self.expression()
                self.need(")")
                return value
            if self.token.kind in ("str", "num", "true", "false", "null", "+", "-"):
                return ("lit", self.literal())
            return ("field", self.field())
        finally:
            self.depth -= 1

    def literal(self):
        sign = -1 if self.accept("-") else 1
        plus = bool(self.accept("+")) if sign == 1 else False
        token = self.token
        if token.kind in ("num", "str", "true", "false", "null"):
            self.i += 1
            value = {"true": True, "false": False, "null": None}.get(token.kind, token.value)
            if token.kind != "num" and (sign == -1 or plus):
                raise EqlError("İşaret yalnız sayılarda kullanılabilir.")
            if token.kind == "num":
                value *= sign
                if isinstance(value, float) and value == 0.0 and math.copysign(1.0, value) < 0:
                    raise EqlError("Yerel EQL negatif double sıfırı (-0.0) desteklemez; gerçek Elastic üzerinde deneyin.")
                if isinstance(value, int) and not -(2**63) <= value < 2**63:
                    raise EqlError("EQL tamsayı sabiti signed 64-bit sınırında olmalı.")
            return value
        raise EqlError("EQL karşılaştırması sabit değer bekliyor; fonksiyon/alan karşılaştırması desteklenmez.")

    def predicate(self):
        left = self.primary()
        op = self.token.kind
        negative = False
        if op == "not":
            self.i += 1
            if self.token.kind not in ("in", "in~"):
                raise EqlError("Alan sonrasında not yalnız in/in~ ile kullanılır.")
            op, negative = self.token.kind, True
        if op in ("==", "!=", "<", "<=", ">", ">="):
            self.i += 1
            right = self.primary()
            if left[0] == "field" and right[0] == "field":
                raise EqlError("Elasticsearch EQL alanı alanla karşılaştırmaz.")
            if left[0] not in ("field", "lit") or right[0] not in ("field", "lit"):
                raise EqlError("Karşılaştırma operandı alan veya sabit olmalı.")
            node = ("cmp", op, left, right)
            _check_comparison(node)
            return node
        if op in ("in", "in~", ":", "like", "like~"):
            self.i += 1
            if self.accept("("):
                choices = [self.literal()]
                while self.accept(","):
                    choices.append(self.literal())
                self.need(")")
            elif op in (":", "like", "like~"):
                choices = [self.literal()]
            else:
                self.need("(")
            if len(choices) > 64 or left[0] not in ("field", "lit"):
                raise EqlError("EQL lookup en fazla 64 sabit değer ve bir alan/sabit bekler.")
            node = ("lookup", op, left, tuple(choices))
            _check_lookup(node)
            return ("not", node) if negative else node
        return left

    def logical_not(self):
        if self.accept("not"):
            self.depth += 1
            if self.depth > 64:
                raise EqlError("EQL not derinliği 64'ü aşamaz.")
            value = ("not", self.logical_not())
            self.depth -= 1
            return value
        return self.predicate()

    def conjunction(self):
        value = self.logical_not()
        while self.accept("and"):
            value = ("and", value, self.logical_not())
        return value

    def expression(self):
        value = self.conjunction()
        while self.accept("or"):
            value = ("or", value, self.conjunction())
        return value

    def event(self):
        if self.accept("any"):
            category = None
        elif self.token.kind in ("id", "str"):
            category = str(self.token.value); self.i += 1
        else:
            raise EqlError("EQL bir event category veya any bekliyor.")
        self.need("where")
        condition = self.expression()
        _boolean_type(condition)
        return Stage(category, condition)

    def term(self):
        missing = bool(self.accept("!["))
        if not missing:
            self.need("[")
        stage = self.event()
        stage.missing = missing
        self.need("]")
        if self.accept("by"):
            stage.keys = self.keys()
        return stage

    def query(self):
        if not self.accept("sequence"):
            stage = self.event()
            self.need("eof")
            return [stage], None, None
        common = self.keys() if self.accept("by") else []
        span = None
        if self.accept("with"):
            self.need("maxspan"); self.need("=")
            amount = self.need("num").value
            unit = self.need("id").value
            factors = {"ms": 1_000_000, "s": 1_000_000_000, "m": 60_000_000_000, "h": 3_600_000_000_000, "d": 86_400_000_000_000}
            if type(amount) is not int or amount <= 0 or unit not in factors:
                raise EqlError("maxspan pozitif tamsayı + ms/s/m/h/d olmalı.")
            span = amount * factors[unit]
            if span > 2**63 - 1:
                raise EqlError("maxspan nanosecond aralığı aşıldı.")
        stages = []
        while self.token.kind in ("[", "!["):
            stages.append(self.term())
            if len(stages) > 32:
                raise EqlError("Yerel EQL en fazla 32 sequence aşaması destekler.")
        until = self.term() if self.accept("until") else None
        self.need("eof")
        positive = [s for s in stages if not s.missing]
        if len(positive) < 2:
            raise EqlError("Yerel sequence en az iki olumlu aşama bekler.")
        if stages[0].missing or stages[-1].missing:
            raise EqlError("Yerel EQL yalnız ortadaki ![] aşamalarını destekler; baş/son eksik olay desteklenmez.")
        if any(s.missing for s in stages) and span is None:
            raise EqlError("Eksik olay koşulu with maxspan gerektirir.")
        if until and until.missing:
            raise EqlError("until eksik olay koşulu olamaz.")
        count = len(stages[0].keys)
        for stage in stages + ([until] if until else []):
            if len(stage.keys) != count:
                raise EqlError("Her aşama ve until aynı sayıda aşama join anahtarı kullanmalı.")
            stage.keys = common + stage.keys
        for index in range(len(stages[0].keys)):
            kinds = {s.keys[index].kind for s in stages + ([until] if until else [])} - {None}
            if len(kinds) > 1:
                raise EqlError("Yerel join anahtarı mapping türü bütün aşamalarda aynı olmalı; sayısal tür dönüştürme desteklenmez.")
            if "double" in kinds:
                raise EqlError("Yerel EQL double join anahtarlarını desteklemez.")
        return stages, span, until


def _kind(node):
    if node[0] == "field":
        return node[1].kind
    if node[0] == "lit":
        value = node[1]
        return None if value is None else "boolean" if type(value) is bool else "keyword" if isinstance(value, str) else "long" if type(value) is int else "double"
    return "boolean"


def _compatible(a, b):
    return a is None or b is None or a == b or {a, b} <= {"long", "integer", "float", "double"} or {a, b} <= {"date", "date_nanos", "keyword"}


def _check_comparison(node):
    _, op, left, right = node
    a, b = _kind(left), _kind(right)
    if left[0] == "lit" and right[0] == "lit":
        raise EqlError("Yerel EQL sabit-sabit karşılaştırması desteklemez; where içinde alan koşulu veya true/false kullanın.")
    if not _compatible(a, b):
        raise EqlError("EQL karşılaştırma türleri uyumsuz.")
    if (a == "double" and b in ("integer", "long")) or (b == "double" and a in ("integer", "long")):
        raise EqlError("Yerel EQL tamsayı/double karışık karşılaştırması desteklemez; mapping ile aynı türde sabit yazın.")
    if op not in ("==", "!=") and a == b == "keyword":
        raise EqlError("Yerel EQL keyword sıralama karşılaştırması desteklemez; ==, != veya metin işleci kullanın.")
    if op not in ("==", "!=") and (a == "boolean" or b == "boolean"):
        raise EqlError("Boolean alanlarda yalnız == ve != desteklenir.")
    for field_side, literal_side in ((left, right), (right, left)):
        if _kind(field_side) in ("date", "date_nanos") and literal_side[0] == "lit" and literal_side[1] is not None:
            _date(literal_side[1])


def _check_lookup(node):
    _, op, left, choices = node
    for choice in choices:
        if op in (":", "like", "like~", "in~"):
            if _kind(left) not in (None, "keyword") or not isinstance(choice, str):
                raise EqlError("EQL metin işleci keyword alan ve metin sabitleri bekler.")
            if op in (":", "like~", "in~") and not choice.isascii():
                raise EqlError("Yerel harf duyarsız EQL yalnız ASCII değerleri destekler.")
        else:
            _check_comparison(("cmp", "==", left, ("lit", choice)))


def _boolean_type(node):
    pending = [(node, 1)]
    while pending:
        current, depth = pending.pop()
        if depth > 64:
            raise EqlError("EQL boolean ağaç derinliği 64'ü aşamaz.")
        if current[0] in ("and", "or"):
            pending.extend(((current[1], depth + 1), (current[2], depth + 1)))
        elif current[0] == "not":
            pending.append((current[1], depth + 1))
        elif _kind(current) not in (None, "boolean"):
            raise EqlError("where/and/or/not boolean koşul bekler.")


def _get(doc, item):
    if item.kind is None:
        return None
    value = doc.get(item.name)
    if value is None:
        return None
    if isinstance(value, (list, dict, tuple, set)):
        raise EqlError("Yerel EQL yalnız tek değerli düz alanları destekler: " + item.name)
    if item.kind == "keyword":
        if not isinstance(value, str):
            raise EqlError("keyword alanı metin olmalı: " + item.name)
        try:
            value.encode("utf-8")
        except UnicodeError as exc:
            raise EqlError("Geçersiz Unicode alanı: " + item.name) from exc
    elif item.kind == "boolean":
        if type(value) is not bool:
            raise EqlError("boolean alanı true/false olmalı: " + item.name)
    elif item.kind in ("long", "integer"):
        lo, hi = (-(2**31), 2**31) if item.kind == "integer" else (-(2**63), 2**63)
        if type(value) is not int or not lo <= value < hi:
            raise EqlError("Tamsayı alanı tür/sınır hatası: " + item.name)
    elif item.kind == "double":
        try:
            finite = type(value) in (int, float) and math.isfinite(value)
        except OverflowError:
            finite = False
        if not finite:
            raise EqlError("Sayısal alan sonlu sayı olmalı: " + item.name)
        value = float(value)
        if value == 0.0 and math.copysign(1.0, value) < 0:
            raise EqlError("Yerel EQL negatif double sıfırı (-0.0) desteklemez: " + item.name)
    elif item.kind in ("date", "date_nanos"):
        value = _date(value)
    else:
        raise EqlError("Desteklenmeyen EQL alanı: " + item.name)
    return value


def _and(a, b):
    return False if a is False or b is False else None if a is None or b is None else True


def _or(a, b):
    return True if a is True or b is True else None if a is None or b is None else False


def _not(value):
    return None if value is None else not value


def _compare(op, left, right, literal_null=False):
    if literal_null and op in ("==", "!="):
        same = left is None and right is None
        return same if op == "==" else not same
    if left is None or right is None:
        return None
    if op == "==": return left == right
    if op == "!=": return left != right
    if op == "<": return left < right
    if op == "<=": return left <= right
    if op == ">": return left > right
    if op == ">=": return left >= right
    raise EqlError("Bilinmeyen karşılaştırma.")


def _wildcard(value, pattern, insensitive):
    if insensitive:
        if not value.isascii():
            raise EqlError("Yerel harf duyarsız EQL yalnız ASCII değerleri destekler.")
        value, pattern = value.lower(), pattern.lower()
    # EQL's toLikePattern translates * and ? regardless of preceding backslash.
    # Everything else, including [, %, _, and backslash, is literal.
    regex = "".join(".*" if c == "*" else "." if c == "?" else re.escape(c) for c in pattern)
    return re.fullmatch(regex, value, flags=re.DOTALL) is not None


def _eval(node, doc):
    kind = node[0]
    if kind == "lit": return node[1]
    if kind == "field": return _get(doc, node[1])
    if kind == "not": return _not(_eval(node[1], doc))
    if kind == "and": return _and(_eval(node[1], doc), _eval(node[2], doc))
    if kind == "or": return _or(_eval(node[1], doc), _eval(node[2], doc))
    if kind == "cmp":
        _, op, a, b = node
        left, right = _eval(a, doc), _eval(b, doc)
        if _kind(a) in ("date", "date_nanos") and b[0] == "lit" and right is not None: right = _date(right)
        if _kind(b) in ("date", "date_nanos") and a[0] == "lit" and left is not None: left = _date(left)
        null = any(n[0] == "lit" and n[1] is None for n in (a, b))
        return _compare(op, left, right, null)
    if kind == "lookup":
        _, op, a, choices = node
        value, result = _eval(a, doc), False
        for choice in choices:
            if value is None or choice is None:
                match = None
            elif op in (":", "like", "like~"):
                match = _wildcard(value, choice, op != "like")
            elif op == "in~":
                if not value.isascii():
                    raise EqlError("Yerel harf duyarsız EQL yalnız ASCII değerleri destekler.")
                match = value.lower() == choice.lower()
            else:
                if _kind(a) in ("date", "date_nanos"): choice = _date(choice)
                match = _compare("==", value, choice)
            result = _or(result, match)
        return result
    raise EqlError("Bilinmeyen EQL ifade düğümü.")


def _key(stage, doc):
    key = []
    for item in stage.keys:
        value = _get(doc, item)
        if value is None and not item.optional:
            return None
        # Python's True == 1 must not merge unrelated EQL key types.
        key.append(("null", None) if value is None else ("bool", value) if type(value) is bool else ("number", value) if isinstance(value, (int, float)) else ("string", value))
    return tuple(key)


def evaluate(query, mapping, documents, context=None):
    """Return event IDs or positive sequence ID lists; unsupported input raises.

    Context contains only timestamp_field, event_category_field and
    tiebreaker_field. The caller applies an optional external time filter.
    """
    mapping = _mapping(mapping)
    context = {} if context is None else dict(context)
    if set(context) - {"timestamp_field", "event_category_field", "tiebreaker_field"}:
        raise EqlError("Yerel EQL bilinmeyen sıralama/bağlam seçeneğini kabul etmez.")
    timestamp = context.get("timestamp_field", "@timestamp")
    category = context.get("event_category_field", "event.category")
    tiebreaker = context.get("tiebreaker_field", "event.id")
    if not all(isinstance(v, str) and v for v in (timestamp, category, tiebreaker)):
        raise EqlError("EQL bağlam alanları boş olmayan metin olmalı.")
    parser = Parser(query, mapping)
    stages, span, until = parser.query()
    if mapping.get(timestamp) not in ("date", "date_nanos"):
        raise EqlError("EQL timestamp alanı date/date_nanos mapped olmalı.")
    tsfield = Field(timestamp, False, mapping[timestamp])
    if any(s.category is not None for s in stages + ([until] if until else [])) and mapping.get(category) != "keyword":
        raise EqlError("EQL event category alanı keyword mapped olmalı.")
    category_field = Field(category, True, mapping.get(category))
    if mapping.get(tiebreaker) not in (None, "keyword", "long", "integer"):
        raise EqlError("Yerel EQL tiebreaker keyword veya tamsayı olmalı.")
    fallback = tiebreaker == "event.id" and tiebreaker not in mapping
    if tiebreaker not in mapping and not fallback:
        raise EqlError("EQL tiebreaker mapping alanı yok: " + tiebreaker)
    tie_field = Field(tiebreaker, False, mapping.get(tiebreaker))
    if not isinstance(documents, list) or len(documents) > MAX_DOCUMENTS or any(not isinstance(d, dict) for d in documents):
        raise EqlError("Yerel EQL corpus en fazla 5000 düz olay sözlüğü içermeli.")
    ordered, ids, ordinals = [], set(), set()
    all_stages = stages + ([until] if until else [])
    for doc in documents:
        eid = doc.get("id", doc.get("event.id"))
        if not isinstance(eid, str) or not eid or eid in ids or any(ord(c) < 32 or ord(c) == 127 for c in eid):
            raise EqlError("Her EQL olayının benzersiz, boş olmayan metin id'si olmalı.")
        try:
            eid.encode("utf-8")
        except UnicodeError as exc:
            raise EqlError("Geçersiz Unicode olay kimliği.") from exc
        ids.add(eid)
        stamp = _get(doc, tsfield)
        if stamp is None:
            raise EqlError("Yerel EQL olaylarında timestamp eksik olamaz.")
        tie = eid if fallback else _get(doc, tie_field)
        ordinal = (stamp, 1 if tie is None else 0, tie.encode("utf-8") if isinstance(tie, str) else tie if tie is not None else 0)
        if ordinal in ordinals:
            raise EqlError("Timestamp+tiebreaker benzersiz olmalı; Elasticsearch implicit shard sırası taklit edilmez.")
        ordinals.add(ordinal)
        for item in parser.used.values():
            _get(doc, item)
        cat = _get(doc, category_field) if category_field.kind is not None else None
        matches = [((stage.category is None or cat == stage.category) and _eval(stage.condition, doc) is True) for stage in all_stages]
        ordered.append((ordinal, eid, doc, matches))
    ordered.sort(key=lambda event: event[0])
    if len(stages) == 1:
        return [event[1] for event in ordered if event[3][0]]
    positives = [i for i, stage in enumerate(stages) if not stage.missing]
    negatives = [i for i, stage in enumerate(stages) if stage.missing]
    pending = [dict() for _ in positives[:-1]]
    expiry = {}
    missing = {i: {} for i in negatives}
    for event in ordered:
        if until and event[3][-1]:
            key = _key(until, event[2])
            if key is not None: expiry.setdefault(key, []).append(event[0])
        for i in negatives:
            if event[3][i]:
                key = _key(stages[i], event[2])
                if key is not None: missing[i].setdefault(key, []).append(event[0][0])
    completed = []
    for event in ordered:
        for state in range(len(positives) - 1, -1, -1):
            index = positives[state]
            if not event[3][index]: continue
            key = _key(stages[index], event[2])
            if key is None: continue
            if state == 0:
                pending[0][key] = [event]
                continue
            previous = pending[state - 1].pop(key, None)
            if previous is None or not previous[-1][0] < event[0]: continue
            if span is not None and event[0][0] - previous[0][0][0] > span: continue
            untils = expiry.get(key, [])
            end = bisect_left(untils, event[0])
            if end and untils[end - 1] >= previous[-1][0]: continue
            sequence = previous + [event]
            if state < len(positives) - 1:
                pending[state][key] = sequence
                continue
            blocked = False
            for i in negatives:
                prior = max(p for p in positives if p < i)
                following = min(p for p in positives if p > i)
                a = sequence[positives.index(prior)][0][0]
                b = sequence[positives.index(following)][0][0]
                stamps = missing[i].get(key, [])
                # Middle absence uses an open *timestamp* interval, not ordinals.
                at = bisect_left(stamps, b) - 1
                if at >= 0 and stamps[at] > a:
                    blocked = True
                    break
            if not blocked:
                completed.append(sequence)
    completed.sort(key=lambda seq: seq[-1][0])
    return [[event[1] for event in sequence] for sequence in completed]
