"""Offline capstone adapters. Reuse Pafta's bounded Kusto/SPL and Sigma engines.

No Sentinel/Splunk service or new query imitation; PCAP filtering is native
TShark. Corpus fields are explicitly a teaching normalization, not vendor logs.
"""
from pathlib import Path
import json
import sqlite3

FIELDS = ('id','ts','source','host','user','event','outcome','src','Image','CommandLine')


def yukle():
    return [json.loads(line) for line in Path('olaylar.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]


def sorgu(dil, code, rows=None):
    from datetime import datetime
    from . import kql, spl
    if dil not in ('kql','spl'):
        raise ValueError('Yalnız kql veya spl')
    rows = yukle() if rows is None else rows
    meta=json.loads(Path('vaka.json').read_text(encoding='utf-8'))
    base=datetime.fromisoformat(meta['base_utc'].replace('Z','+00:00')).timestamp()
    engine = kql if dil == 'kql' else spl
    with sqlite3.connect(':memory:') as db:
        db.execute('CREATE TABLE olaylar(id TEXT,ts INTEGER,source TEXT,host TEXT,user TEXT,event TEXT,outcome TEXT,src TEXT,Image TEXT,CommandLine TEXT,_time INTEGER,_raw TEXT)')
        db.executemany('INSERT INTO olaylar VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                       [tuple(r.get(k) for k in FIELDS)+(base+r['ts'],json.dumps(r)) for r in rows])
        engine.fonksiyonlari_kaydet(db)
        def columns(sql):
            return [d[0] for d in db.execute(sql).description]
        columns.satirlar = lambda sql: db.execute(sql).fetchall()
        translated = engine.cevir(code, columns)
        cur = db.execute(translated)
        names = [d[0] for d in cur.description]
        return [{k:v for k,v in zip(names,row) if k!='__sira'} for row in cur.fetchall()]


def sigma(code, rows=None):
    from .sigma_engine import SigmaProgram
    rows = yukle() if rows is None else rows
    # Caller chooses correct source; production routing is deliberately explicit.
    return [r['id'] for r in SigmaProgram(code).matching_events(rows)]


def paketler(code, raw=None):
    from .packet_engine import evaluate
    raw = Path('vaka.pcap').read_bytes() if raw is None else raw
    return evaluate(code,raw,'wireshark')


def paket_zamanlari(ids):
    """Exact capture timestamps, relative to the documented case origin."""
    from datetime import datetime
    from fractions import Fraction
    from .capture_formats import parse_capture
    meta=json.loads(Path('vaka.json').read_text(encoding='utf-8'))
    origin=datetime.fromisoformat(meta['base_utc'].replace('Z','+00:00')).timestamp()
    frames=parse_capture(Path('vaka.pcap').read_bytes())
    result=[]
    for i in ids:
        if type(i) is not int or not 1<=i<=len(frames):raise ValueError('Frame numarası geçersiz')
        timestamp=frames[i-1].timestamp
        if timestamp is None:raise ValueError('Paket zamanı eksik')
        result.append((float(timestamp-Fraction(origin)),f'vaka.pcap#frame={i}'))
    return result
