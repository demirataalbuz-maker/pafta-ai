"""Official pySigma parsing with a deliberately bounded, local event evaluator.

This is a teaching backend, not a SIEM. Logsource routes data in production;
here the caller supplies the already selected event corpus. Correlations,
pipelines and unsupported modifiers are rejected instead of approximated.
"""
import ipaddress
import json
import os
import re
import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEPS = os.path.join(ROOT, ".deps")
if DEPS not in sys.path:
    sys.path.insert(0, DEPS)

MAX_BYTES = 1_048_576
MAX_EVENTS = 1000
MISSING = object()
SUPPORTED_MODIFIERS = {"all", "contains", "startswith", "endswith", "cased",
                       "re", "i", "m", "s", "cidr", "exists", "gt", "gte", "lt", "lte"}


class SigmaLessonError(ValueError):
    pass


def _imports():
    try:
        import yaml
        from sigma.rule import SigmaRule
        from sigma import conditions, types
    except ImportError as exc:
        raise SigmaLessonError("Sigma bağımlılığı yok. Proje klasöründe: python -m pip install --target .deps -r requirements-detection.txt") from exc
    return yaml, SigmaRule, conditions, types


def parse_events(text):
    if not text or not text.strip():
        return []
    if len(text.encode("utf-8")) > MAX_BYTES:
        raise SigmaLessonError("Olay girdisi en fazla 1 MiB olabilir.")
    try:
        value = json.loads(text)
        events = value if isinstance(value, list) else [value]
    except json.JSONDecodeError:
        try:
            events = [json.loads(line) for line in text.splitlines() if line.strip()]
        except json.JSONDecodeError as exc:
            raise SigmaLessonError("Girdi bir JSON nesnesi, nesne listesi ya da JSONL olmalı: " + str(exc)) from exc
    _check_events(events)
    return events


def _check_events(events):
    if not isinstance(events, list) or any(not isinstance(event, dict) for event in events):
        raise SigmaLessonError("Her olay bir JSON nesnesi olmalı.")
    if len(events) > MAX_EVENTS:
        raise SigmaLessonError("Bir çalıştırmada en fazla 1000 olay kullanılabilir.")
    if len(json.dumps(events, ensure_ascii=False).encode("utf-8")) > MAX_BYTES:
        raise SigmaLessonError("Olay girdisi en fazla 1 MiB olabilir.")


def _check_modifiers(detection):
    if not isinstance(detection, dict):
        return
    def visit(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(key, str):
                    unsupported = set(key.split("|")[1:]) - SUPPORTED_MODIFIERS
                    if unsupported:
                        raise SigmaLessonError("Bu yerel tezgahta desteklenmeyen Sigma modifier: " + ", ".join(sorted(unsupported)))
                visit(value)
        elif isinstance(obj, list):
            for value in obj:
                visit(value)
        elif type(obj) is int and abs(obj) > 2 ** 53:
            # pySigma's numeric normalization uses float. Reject source values
            # it cannot retain exactly rather than silently changing a threshold.
            raise SigmaLessonError("Bu yerel Sigma backend'inde sayısal kural sabitleri -2^53 ile 2^53 arasında olmalı.")
    for name, definition in detection.items():
        if name != "condition":
            visit(definition)


def _field(event, name):
    # Prefer flat Sigma field names; nested JSON is an additional corpus convenience.
    if name in event:
        return event[name]
    current = event
    for part in name.split("."):
        if not isinstance(current, dict) or part not in current:
            return MISSING
        current = current[part]
    return current


def _number(actual):
    if isinstance(actual, bool):
        return None
    try:
        value = Decimal(str(actual))
        return value if value.is_finite() else None
    except (TypeError, ValueError, InvalidOperation):
        return None


def _value_match(actual, expected, types):
    if isinstance(expected, types.SigmaExists):
        return (actual is not MISSING) == expected.exists
    if isinstance(expected, types.SigmaNull):
        return actual is MISSING or actual is None
    if actual is MISSING or actual is None:
        return False
    if isinstance(actual, list):
        return any(_value_match(item, expected, types) for item in actual)
    if isinstance(expected, types.SigmaRegularExpression):
        flags = 0
        for flag in expected.flags:
            flags |= expected.sigma_to_python_flags[flag]
        return isinstance(actual, str) and re.search(str(expected.regexp), actual, flags) is not None
    if isinstance(expected, types.SigmaString):
        if not isinstance(actual, (str, int, float, bool)):
            return False
        flags = re.DOTALL | (0 if isinstance(expected, types.SigmaCasedString) else re.IGNORECASE)
        return re.fullmatch(str(expected.to_regex().regexp), str(actual), flags) is not None
    if isinstance(expected, types.SigmaCIDRExpression):
        try:
            return ipaddress.ip_address(str(actual)) in expected.network
        except ValueError:
            return False
    if isinstance(expected, types.SigmaCompareExpression):
        value = _number(actual)
        if value is None:
            return False
        target = _number(expected.number.number)
        return {"LT": lambda: value < target, "LTE": lambda: value <= target,
                "GT": lambda: value > target, "GTE": lambda: value >= target,
                "NEQ": lambda: value != target}[expected.op.name]()
    if type(expected) is types.SigmaNumber:
        return _number(actual) == _number(expected.number)
    if isinstance(expected, types.SigmaBool):
        return isinstance(actual, bool) and actual == expected.boolean
    raise SigmaLessonError("Bu tezgahta desteklenmeyen Sigma değer türü: " + type(expected).__name__)


def _evaluate(node, event, conditions, types):
    if isinstance(node, conditions.ConditionAND):
        return all(_evaluate(arg, event, conditions, types) for arg in node.args)
    if isinstance(node, conditions.ConditionOR):
        return any(_evaluate(arg, event, conditions, types) for arg in node.args)
    if isinstance(node, conditions.ConditionNOT):
        return not _evaluate(node.args[0], event, conditions, types)
    if isinstance(node, conditions.ConditionFieldEqualsValueExpression):
        return _value_match(_field(event, node.field), node.value, types)
    if isinstance(node, conditions.ConditionValueExpression):
        raw = event.get("_raw", event.get("raw", event.get("message", "")))
        if isinstance(node.value, types.SigmaString):
            pattern = str(node.value.to_regex().regexp)
            flags = re.DOTALL | (0 if isinstance(node.value, types.SigmaCasedString) else re.IGNORECASE)
            return re.search(pattern, str(raw), flags) is not None
        return _value_match(raw, node.value, types)
    raise SigmaLessonError("Bu tezgahta desteklenmeyen Sigma koşulu: " + type(node).__name__)


def _validate_tree(node, conditions, types, depth=0):
    if depth > 60:
        raise SigmaLessonError("Sigma koşulu çok derin (en fazla 60 katman).")
    if isinstance(node, (conditions.ConditionAND, conditions.ConditionOR, conditions.ConditionNOT)):
        for child in node.args:
            _validate_tree(child, conditions, types, depth + 1)
    elif isinstance(node, (conditions.ConditionFieldEqualsValueExpression, conditions.ConditionValueExpression)):
        supported = (types.SigmaString, types.SigmaNull, types.SigmaExists,
                     types.SigmaRegularExpression, types.SigmaCIDRExpression,
                     types.SigmaCompareExpression, types.SigmaBool)
        if type(node.value) is not types.SigmaNumber and not isinstance(node.value, supported):
            raise SigmaLessonError("Desteklenmeyen Sigma değer türü: " + type(node.value).__name__)
    else:
        raise SigmaLessonError("Desteklenmeyen Sigma koşulu: " + type(node).__name__)


@dataclass
class CompiledRule:
    rule: object
    trees: list


class SigmaProgram:
    def __init__(self, code):
        yaml, SigmaRule, self.conditions, self.types = _imports()
        if len(code.encode("utf-8")) > 200_000:
            raise SigmaLessonError("Kural kaynağı en fazla 200 kB olabilir.")
        class UniqueLoader(yaml.SafeLoader):
            pass
        def unique_mapping(loader, node, deep=False):
            mapping = {}
            for key_node, value_node in node.value:
                key = loader.construct_object(key_node, deep=deep)
                if key in mapping:
                    raise SigmaLessonError("YAML anahtarı iki kez yazılmış: " + str(key))
                mapping[key] = loader.construct_object(value_node, deep=deep)
            return mapping
        UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)
        docs = list(yaml.load_all(code, Loader=UniqueLoader))
        if not docs or len(docs) > 32:
            raise SigmaLessonError("1 ile 32 arasında Sigma kuralı yazılmalı.")
        self.rules = []
        titles = set()
        for doc in docs:
            if not isinstance(doc, dict):
                raise SigmaLessonError("Her YAML belgesi bir Sigma kural nesnesi olmalı.")
            if "correlation" in doc or "action" in doc:
                raise SigmaLessonError("Korelasyon ve koleksiyon action belgeleri bu yerel tezgahta yürütülmez; derslerdeki dağıtım notlarına bak.")
            _check_modifiers(doc.get("detection"))
            rule = SigmaRule.from_dict(doc)
            trees = [condition.parsed for condition in rule.detection.parsed_condition]
            for tree in trees:
                _validate_tree(tree, self.conditions, self.types)
            if rule.title in titles:
                raise SigmaLessonError("Çoklu kurallarda title benzersiz olmalı: " + rule.title)
            titles.add(rule.title)
            self.rules.append(CompiledRule(rule, trees))

    @property
    def names(self):
        return [compiled.rule.title for compiled in self.rules]

    def matching_names(self, event, rule_name=None):
        if not isinstance(event, dict):
            raise SigmaLessonError("Olay bir sözlük/JSON nesnesi olmalı.")
        if rule_name is not None and rule_name not in self.names:
            raise SigmaLessonError("Böyle bir kural başlığı yok: " + str(rule_name))
        return [compiled.rule.title for compiled in self.rules
                if (rule_name is None or rule_name == compiled.rule.title)
                and any(_evaluate(tree, event, self.conditions, self.types) for tree in compiled.trees)]

    def matches(self, event, rule_name=None):
        return bool(self.matching_names(event, rule_name))

    def matching_events(self, events, rule_name=None):
        _check_events(events)
        return [event for event in events if self.matches(event, rule_name)]

    def run(self, events):
        _check_events(events)
        rows, matched = [], []
        for index, event in enumerate(events, 1):
            names = self.matching_names(event)
            if names:
                event_id = str(event.get("id", index))
                matched.append(event_id)
                rows.append([event_id, ", ".join(names), json.dumps(event, ensure_ascii=False)])
        out = "".join(event_id + "\n" for event_id in matched)
        return {"status": "ok", "error": None, "segs": [["out", out]] if out else [],
                "tablolar": [{"satir": 1, "sutunlar": ["olay", "kurallar", "veri"], "satirlar": rows}],
                "sigma_rules": self.names}
