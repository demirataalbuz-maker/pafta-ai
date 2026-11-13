"""Real yara-python bundle/scan API for YR23–24. No implicit disk includes."""
from pathlib import PurePosixPath
import time
from sandbox.yara_engine import _load_yara, _checked_bytes


def compile_bundle(sources, externals=None, includes=None, strict=False):
    if not isinstance(sources, dict) or not sources:
        raise ValueError('sources boş olmayan namespace/kaynak sözlüğü olmalı.')
    if not all(isinstance(k,str) and isinstance(v,str) for k,v in sources.items()):
        raise TypeError('namespace ve kaynak metin olmalı.')
    files=dict(includes or {})
    def resolve(name, parent, namespace):
        # Exact dictionary lookup ONLY; there is no fallback to a host path.
        p=PurePosixPath(name)
        if p.is_absolute() or '..' in p.parts or '\\' in name or ':' in name or name not in files:
            raise ValueError('İzin verilmeyen include: '+name)
        value=files[name]
        if not isinstance(value,str):raise TypeError('Include kaynağı metin olmalı.')
        return value
    return _load_yara().compile(sources=sources,externals=externals or {},
        includes=bool(files),include_callback=resolve,error_on_warning=strict)


def scan_bytes(rules, data, externals=None, timeout=2):
    if type(timeout) is not int or not 1<=timeout<=5:
        raise ValueError('timeout 1–5 tam saniye olmalı.')
    return rules.match(data=_checked_bytes(data),externals=externals or {},timeout=timeout,
        console_callback=lambda _:None)


def scan_set(rules, samples, timeout=2):
    """Scan every explicit named byte sample; preserve error vs clean distinction.

    Per-sample 1MiB cap and per-scan native timeout. Total set max 32 entries.
    Elapsed time is measured, never used as a deterministic grading threshold.
    """
    if len(samples)>32:raise ValueError('En fazla 32 örnek.')
    rows=[]
    native=_load_yara()
    for name,data in sorted(samples.items()):
        started=time.perf_counter_ns()
        try:
            matches=scan_bytes(rules,data,timeout=timeout)
            row={'file':name,'status':'ok','matches':sorted((m.namespace,m.rule) for m in matches)}
        except native.TimeoutError:
            row={'file':name,'status':'timeout','matches':None}
        row['bytes']=len(data.encode('utf8') if isinstance(data,str) else data)
        row['elapsed_ns']=time.perf_counter_ns()-started
        rows.append(row)
    return rows
