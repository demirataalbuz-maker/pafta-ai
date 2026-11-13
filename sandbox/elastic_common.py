"""Strict shared JSON corpus contract for Pafta's bounded Elastic workbench."""
import copy
from datetime import datetime, timezone
import json
import math
import re


class ElasticError(ValueError):
    pass


DIALECTS = ("kibana", "lucene", "eql")
TYPES = ("keyword", "text", "long", "integer", "double", "date", "boolean", "nested")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?(?:Z|[+-]\d{2}:\d{2})\Z")


def date_millis(value):
    if type(value) is int:
        if not -(2**63) <= value < 2**63:
            raise ElasticError("epoch_millis 64-bit işaretli tamsayı sınırında olmalı.")
        return value
    if not isinstance(value, str) or not _DATE.fullmatch(value):
        raise ElasticError("Tarih, saat dilimli ISO-8601 (en çok milisaniye) veya epoch_millis tamsayısı olmalı; tarih matematiği desteklenmez.")
    if not value.endswith("Z"):
        hours, minutes = int(value[-5:-3]), int(value[-2:])
        if hours > 18 or minutes > 59 or (hours == 18 and minutes != 0):
            raise ElasticError("ISO saat dilimi ±18:00 sınırında, dakika 00..59 olmalı.")
    try:
        instant = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
        delta = instant - datetime(1970, 1, 1, tzinfo=timezone.utc)
        return delta.days * 86400000 + delta.seconds * 1000 + delta.microseconds // 1000
    except (ValueError, OverflowError) as exc:
        raise ElasticError("Geçersiz tarih: " + value) from exc


def field_value(document, field):
    if field in document:
        return document[field]
    value = document
    for part in field.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def mapping_specs(mapping):
    if not isinstance(mapping, dict) or not mapping or len(mapping) > 128:
        raise ElasticError("mapping, 1..128 alan içeren nesne olmalı.")
    result = {}
    for field, raw in mapping.items():
        if not isinstance(field, str) or not re.fullmatch(r"[A-Za-z@][A-Za-z0-9_.@-]*", field) or field.startswith("_pafta"):
            raise ElasticError("Geçersiz mapping alanı: " + str(field))
        spec = {"type": raw} if isinstance(raw, str) else copy.deepcopy(raw)
        if not isinstance(spec, dict) or spec.get("type") not in TYPES:
            raise ElasticError("Alan türü desteklenmiyor: " + field)
        allowed = {"type", "index"}
        if spec["type"] == "keyword":
            allowed |= {"normalizer", "ignore_above", "null_value"}
        elif spec["type"] == "text":
            allowed |= {"analyzer"}
        if set(spec) - allowed:
            raise ElasticError("Desteklenmeyen mapping seçeneği: " + field + ": " + ", ".join(sorted(set(spec) - allowed)))
        if "index" in spec and type(spec["index"]) is not bool:
            raise ElasticError("index boolean olmalı: " + field)
        if spec.get("normalizer") not in (None, "lowercase") or spec.get("analyzer") not in (None, "standard"):
            raise ElasticError("Yalnız standard analyzer ve lowercase keyword normalizer desteklenir: " + field)
        if "ignore_above" in spec and (type(spec["ignore_above"]) is not int or spec["ignore_above"] < 0):
            raise ElasticError("ignore_above negatif olmayan tamsayı olmalı: " + field)
        if "null_value" in spec and not isinstance(spec["null_value"], str):
            raise ElasticError("keyword null_value metin olmalı: " + field)
        result[field] = spec
    return result


def _validate_scalar(value, spec, field):
    if value is None:
        return
    kind = spec["type"]
    valid = True
    if kind in ("keyword", "text"):
        valid = isinstance(value, str)
    elif kind in ("long", "integer"):
        bits = 32 if kind == "integer" else 64
        valid = type(value) is int and -(2 ** (bits - 1)) <= value < 2 ** (bits - 1)
    elif kind == "double":
        try:
            valid = type(value) in (int, float) and math.isfinite(value)
        except OverflowError:
            valid = False
    elif kind == "boolean":
        valid = type(value) is bool
    elif kind == "date":
        date_millis(value)
    if not valid:
        raise ElasticError("Belge alanının türü mapping ile uyuşmuyor (coerce kapalı): " + field)


def _validate_documents(documents, mapping):
    if not isinstance(documents, list) or len(documents) > 1000:
        raise ElasticError("documents en çok 1000 belge içeren liste olmalı.")
    seen = set()
    for doc in documents:
        if (not isinstance(doc, dict) or not isinstance(doc.get("id"), str) or not doc["id"]
                or any(ord(ch) < 32 for ch in doc["id"]) or doc["id"] in seen):
            raise ElasticError("Her belgede benzersiz, boş olmayan metin id gerekli.")
        seen.add(doc["id"])
        for field, spec in mapping.items():
            if spec["type"] == "nested":
                nested = field_value(doc, field)
                if nested is None:
                    continue
                children = nested if isinstance(nested, list) else [nested]
                if any(v is not None and not isinstance(v, dict) for v in children):
                    raise ElasticError("nested alan nesne veya nesne listesi olmalı: " + field)
                for child in children:
                    if child is None:
                        continue
                    for name, child_spec in mapping.items():
                        if name.startswith(field + "."):
                            value = field_value(child, name[len(field) + 1:])
                            for scalar in value if isinstance(value, list) else [value]:
                                _validate_scalar(scalar, child_spec, name)
                continue
            if any(field.startswith(parent + ".") and parent_spec["type"] == "nested" for parent, parent_spec in mapping.items()):
                continue
            value = field_value(doc, field)
            for scalar in value if isinstance(value, list) else [value]:
                _validate_scalar(scalar, spec, field)
            # Flatten ordinary JSON objects into mapped ECS field paths for
            # the native index. Nested object lists retain their own scope.
            if field not in doc:
                current = doc
                for part in field.split("."):
                    if not isinstance(current, dict) or part not in current:
                        break
                    current = current[part]
                else:
                    doc[field] = copy.deepcopy(current)


def corpus(value):
    if isinstance(value, str):
        if len(value.encode("utf-8")) > 8 * 1024 * 1024:
            raise ElasticError("Girdi en fazla 8 MiB olabilir.")
        try:
            value = json.loads(value)
        except (ValueError, TypeError) as exc:
            raise ElasticError("Girdi mapping ve documents içeren JSON olmalı.") from exc
    if not isinstance(value, dict) or set(value) - {"dil", "mapping", "documents", "context"}:
        raise ElasticError("Girdi yalnız dil, mapping, documents ve context alanlarını kabul eder.")
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, UnicodeError) as exc:
        raise ElasticError("Corpus geçerli UTF-8 JSON değerleri içermeli; NaN/Infinity kabul edilmez.") from exc
    if len(encoded) > 8 * 1024 * 1024:
        raise ElasticError("Girdi en fazla 8 MiB olabilir.")
    result = copy.deepcopy(value)
    if result.get("dil", "kibana") not in DIALECTS:
        raise ElasticError("dil kibana, lucene veya eql olmalı.")
    result.setdefault("dil", "kibana")
    result["mapping"] = mapping_specs(result.get("mapping"))
    _validate_documents(result.get("documents"), result["mapping"])
    context = result.setdefault("context", {})
    if not isinstance(context, dict) or set(context) - {"time_filter", "sort", "timestamp_field", "event_category_field", "tiebreaker_field"}:
        raise ElasticError("Desteklenmeyen context seçeneği.")
    if "time_filter" in context:
        window = context["time_filter"]
        if not isinstance(window, dict) or set(window) - {"field", "gt", "gte", "lt", "lte"} or not set(window) & {"gt", "gte", "lt", "lte"}:
            raise ElasticError("time_filter field ve en az bir gt/gte/lt/lte ucu içermeli.")
        name = window.get("field", "@timestamp")
        if not isinstance(name, str) or not name:
            raise ElasticError("time_filter.field boş olmayan metin olmalı.")
        if result["mapping"].get(name, {}).get("type") != "date":
            raise ElasticError("time_filter alanı date mapping gerektirir.")
        for op in set(window) - {"field"}:
            date_millis(window[op])
    if "sort" in context:
        order = context["sort"]
        if not isinstance(order, list) or len(order) > 8:
            raise ElasticError("sort en çok sekiz [alan, asc/desc] çifti içermeli.")
        for item in order:
            if not isinstance(item, list) or len(item) != 2 or item[1] not in ("asc", "desc"):
                raise ElasticError("sort öğesi [alan, asc/desc] olmalı.")
            if not isinstance(item[0], str) or not item[0]:
                raise ElasticError("sort alanı boş olmayan metin olmalı.")
            if item[0] != "id" and result["mapping"].get(item[0], {}).get("type") not in ("keyword", "long", "integer", "double", "date", "boolean"):
                raise ElasticError("sort yalnız skaler keyword/sayı/date/boolean veya id alanında desteklenir.")
            spec = result["mapping"].get(item[0], {})
            if any(key in spec for key in ("ignore_above", "null_value")) or spec.get("index") is False:
                raise ElasticError("sort özel index/null_value/ignore_above mapping seçeneklerinde desteklenmez.")
    return result


def selected_documents(config):
    docs = list(config["documents"])
    context = config["context"]
    window = context.get("time_filter")
    if window:
        def inside(doc):
            raw = field_value(doc, window.get("field", "@timestamp"))
            if isinstance(raw, list):
                raise ElasticError("time_filter çok değerli tarihte desteklenmez.")
            if raw is None:
                return False
            value = date_millis(raw)
            return all({"gt": value > date_millis(end), "gte": value >= date_millis(end),
                        "lt": value < date_millis(end), "lte": value <= date_millis(end)}[op]
                       for op, end in window.items() if op != "field")
        docs = [doc for doc in docs if inside(doc)]
    return docs


def sorted_documents(docs, config):
    docs = list(docs)
    for field, direction in reversed(config["context"].get("sort", [])):
        spec = config["mapping"].get(field, {"type": "keyword"})
        present, missing = [], []
        for doc in docs:
            raw = field_value(doc, field)
            if isinstance(raw, (list, dict)):
                raise ElasticError("sort çok değerli/nesne alanında desteklenmez: " + field)
            if raw is None:
                missing.append(doc)
            else:
                present.append(doc)
        def key(doc):
            raw = field_value(doc, field)
            if spec["type"] == "date":
                return date_millis(raw)
            if spec["type"] == "double":
                return raw, 0 if math.copysign(1.0, raw) < 0 else 1
            if spec.get("normalizer") == "lowercase":
                if not raw.isascii():
                    raise ElasticError("Yerel lowercase sıralaması yalnız ASCII destekler; Unicode normalizer sıralaması ürün üzerinde denenmeli.")
                return raw.lower()
            return raw
        docs = sorted(present, key=key, reverse=direction == "desc") + missing
    return docs
