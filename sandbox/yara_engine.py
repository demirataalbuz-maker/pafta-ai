# -*- coding: utf-8 -*-
"""Pafta'nın bellek içi, gerçek YARA derleyicisi ve tarayıcısı.

Yalnızca verilen veriyi tarar; dosya yolu, süreç kimliği ve include kabul etmez.
Bağımlılık ilk YARA işleminde yüklenir, diğer yolların açılışını etkilemez.
"""
from __future__ import annotations

import base64
import binascii
import importlib
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import yara


MAX_DATA_BYTES = 1024 * 1024
SCAN_TIMEOUT_SECONDS = 2
MATCH_ROW_LIMIT = 200


def _load_yara():
    deps = str(Path(__file__).resolve().parent.parent / ".deps")
    if Path(deps).is_dir() and deps not in sys.path:
        sys.path.insert(0, deps)
    try:
        return importlib.import_module("yara")
    except (ImportError, OSError) as exc:
        raise RuntimeError(
            "YARA motoru yüklenemedi. Pafta'nın Python sürümüyle proje klasöründe "
            "'python -m pip install --target .deps yara-python==4.5.4' komutunu "
            "çalıştırın. Yerel paket, Python sürümü ve mimarisiyle uyumlu olmalıdır."
        ) from exc


def _checked_bytes(data: str | bytes) -> bytes:
    if isinstance(data, str):
        data = data.encode("utf-8")
    elif not isinstance(data, bytes):
        raise TypeError("YARA verisi metin (str) ya da bayt (bytes) olmalıdır.")
    if len(data) > MAX_DATA_BYTES:
        raise ValueError("YARA verisi en fazla 1 MiB (1.048.576 bayt) olabilir.")
    return data


def compile_rules(code: str) -> yara.Rules:
    """Kaynak metni derle; yerel dosya include'larını her zaman reddet."""
    if not isinstance(code, str):
        raise TypeError("YARA kuralı metin (str) olmalıdır.")
    return _load_yara().compile(source=code, includes=False, error_on_warning=False)


def decode_data(stdin: str) -> bytes:
    """UI girdisi: UTF-8 metin, 'hex:' baytları veya sıkı 'base64:' kodlaması."""
    if not isinstance(stdin, str):
        raise TypeError("YARA girdisi metin (str) olmalıdır.")
    if stdin.startswith("hex:"):
        try:
            data = bytes.fromhex(stdin[4:])
        except ValueError as exc:
            raise ValueError("Geçersiz hex verisi: her bayt iki onaltılık rakam olmalıdır.") from exc
    elif stdin.startswith("base64:"):
        try:
            data = base64.b64decode(stdin[7:].strip(), validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("Geçersiz base64 verisi: alfabe ve dolgu (=) işaretlerini denetleyin.") from exc
    else:
        data = stdin.encode("utf-8")
    return _checked_bytes(data)


def _scan(rules: yara.Rules, data: str | bytes):
    data = _checked_bytes(data)
    native = _load_yara()
    notices = []

    def on_warning(kind, message):
        notices.append(f"YARA tarama uyarısı ({kind}): {message}")
        return native.CALLBACK_CONTINUE

    matches = rules.match(
        data=data,
        timeout=SCAN_TIMEOUT_SECONDS,
        warnings_callback=on_warning,
        # console modülü JSON protokolünün stdout akışına yazmamalı.
        console_callback=lambda message: None,
    )
    return matches, notices


def match_rules(rules: yara.Rules, data: str | bytes) -> list[yara.Match]:
    """En fazla 1 MiB veriyi iki saniye sınırıyla tara; yerel Match nesnelerini döndür.

    Yardımcıdaki metin her zaman UTF-8'dir: hex/base64 öneklerini yalnızca
    decode_data çözer. Böylece 'hex:' içeren gerçek metin de taranabilir.
    """
    return _scan(rules, data)[0]


def format_result(rules: yara.Rules, data: bytes) -> dict:
    """Tarama sonucunu tezgahın çıktı ve tablo biçimine dönüştür."""
    matches, notices = _scan(rules, data)
    output = "".join(match.rule + "\n" for match in matches)
    rows = []
    truncated = False
    for match in matches:
        for string in match.strings:
            for instance in string.instances:
                if len(rows) == MATCH_ROW_LIMIT:
                    truncated = True
                    break
                value = repr(instance.matched_data)[2:-1]
                rows.append([match.rule, string.identifier, instance.offset, value])
            if truncated:
                break
        if truncated:
            break
    tables = []
    if rows:
        tables.append({
            "satir": 1,
            "sutunlar": ["rule", "string", "offset", "value"],
            "satirlar": rows,
            "kesildi": truncated,
        })
    return {
        "status": "ok",
        "segs": [["out", output]] if output else [],
        "error": None,
        "tablolar": tables,
        "yara_matches": [
            {"rule": match.rule, "namespace": match.namespace, "tags": list(match.tags)}
            for match in matches
        ],
        "warnings": [str(warning) for warning in getattr(rules, "warnings", [])] + notices,
    }
