"""Real Microsoft Kusto Emulator; SQL is only a legacy fixture input format."""
from datetime import datetime
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
IMAGE = 'mcr.microsoft.com/azuredataexplorer/kustainer-linux@sha256:093af777e866d79abfaa2cd1f6e10f9509e6eec6ebd229aecb87c9609f26f1e9'
NAME = 'pafta-kusto'
URL = 'http://127.0.0.1:18780'
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


def _docker(args):
    p = subprocess.run(['docker', *args], capture_output=True, timeout=40, creationflags=NO_WINDOW)
    if p.returncode:
        raise RuntimeError(p.stderr.decode('utf-8','replace')[-1000:])
    return p.stdout.decode('utf-8')


def request(query, management=False):
    data = json.dumps({'db': 'NetDefaultDB', 'csl': query,
                       'properties': json.dumps({'Options': {'servertimeout': '00:00:30', 'notruncation': True}})}).encode('utf-8')
    req = urllib.request.Request(URL + ('/v1/rest/mgmt' if management else '/v1/rest/query'), data,
                                 {'Content-Type': 'application/json; charset=utf-8'})
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=40) as r:
            body = r.read(4_000_001)
            if len(body)>4_000_000:
                raise ValueError('Kusto sonucu 4 MB sınırını aşıyor; sessiz kırpılmadı')
            result = json.loads(body)
    except urllib.error.HTTPError as e:
        text = e.read(8000).decode('utf-8','replace')
        raise ValueError('Gerçek Kusto sorgu hatası: '+text) from None
    if result.get('Exceptions') or result.get('error'):
        raise ValueError('Kusto sonuç hatası: '+json.dumps(result,ensure_ascii=False)[:2000])
    tables=result.get('Tables',[])
    # A query with partial failure must not turn into apparent partial success.
    for table in tables:
        if table.get('TableName') in ('QueryStatus','QueryCompletionInformation'):
            for row in table.get('Rows',[]):
                if any(isinstance(v,str) and ('Partial query failure' in v or 'E_QUERY_' in v) for v in row):
                    raise ValueError('Kusto kısmi sorgu hatası: '+repr(row)[:1000])
    if not tables:
        raise ValueError('Kusto tablo sonucu yok')
    return tables[0]


def ensure():
    image = _docker(['image','inspect',IMAGE,'--format','{{.Id}}']).strip()
    try:
        info=json.loads(_docker(['inspect',NAME]))[0]
    except RuntimeError:
        try:
            _docker(['run','-d','--name',NAME,'--label','pafta.lab=kusto','--memory','4g',
                     '--cpus','2','-e','ACCEPT_EULA=Y','-p','127.0.0.1:18780:8080',IMAGE])
        except RuntimeError:
            pass  # A concurrent validator may have created the owned container.
        info=json.loads(_docker(['inspect',NAME]))[0]
    ports=info['HostConfig'].get('PortBindings',{})
    if (info['Image']!=image or info['Config'].get('Labels',{}).get('pafta.lab')!='kusto'
            or ports!={'8080/tcp':[{'HostIp':'127.0.0.1','HostPort':'18780'}]} or info.get('Mounts')):
        raise RuntimeError('Kusto konteyneri imaj/etiket/loopback/bağsız klasör sözleşmesine uymuyor; değiştirilmedi')
    if not info['State']['Running']:
        _docker(['start',NAME])
    end=time.monotonic()+60
    while True:
        try:
            return request('.show cluster',True)
        except (OSError,ValueError):
            if time.monotonic()>end:raise
            time.sleep(.5)


def fixture(setup='',extra=''):
    """Build native datatable lets from trusted legacy lesson fixture SQL.

    Student KQL never goes into SQLite. Inference is an explicit fixture adapter,
    not a general SQL->Kusto query translator or live Sentinel data connector.
    """
    db=sqlite3.connect(':memory:')
    try:
        for p in ('tracks/sql/ornek.sql','tracks/kql/veri.sql'):
            db.executescript((ROOT/p).read_text(encoding='utf-8'))
        db.executescript(setup or '')
        db.executescript(extra or '')
        prefix=[];watchlists=[]
        for (table,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
            if not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*',table):raise ValueError('Fixture tablo adı destek dışı')
            columns=db.execute(f'PRAGMA table_info("{table}")').fetchall()
            rows=db.execute(f'SELECT * FROM "{table}"').fetchall()
            types=[]
            for index,col in enumerate(columns):
                name,declared=col[1],col[2].upper()
                if not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*',name):raise ValueError('Fixture sütun adı destek dışı')
                values=[r[index] for r in rows if r[index] is not None]
                temporal=name.lower() in {'zaman','timestamp','timegenerated','alim'} or (bool(values) and all(isinstance(v,str) and re.fullmatch(r'\d{4}-\d\d-\d\d[ T]\d\d:\d\d(?::\d\d(?:\.\d+)?)?Z?',v) for v in values))
                types.append('datetime' if temporal else 'long' if 'INT' in declared else 'real' if any(t in declared for t in ('REAL','FLOAT','DOUBLE')) else 'string')
            literals=[]
            for row in rows:
                for value,kind in zip(row,types):
                    if kind=='datetime':literals.append('datetime(null)' if value is None else 'datetime('+value+')')
                    elif kind=='string':literals.append(json.dumps('' if value is None else str(value),ensure_ascii=False))
                    else:literals.append(kind+'(null)' if value is None else repr(value))
            fields=','.join(c[1]+':'+t for c,t in zip(columns,types))
            prefix.append('let '+table+'=datatable('+fields+')['+','.join(literals)+'];')
            if table.startswith('watchlist_'):watchlists.append(table)
        if watchlists:
            pieces=['('+t+' | where alias=='+json.dumps(t.removeprefix('watchlist_'))+')' for t in watchlists]
            prefix.append('let _GetWatchlist=(alias:string) { union '+','.join(pieces)+' };')
        return '\n'.join(prefix)+'\n'
    finally:
        db.close()


def query(code,setup='',extra=''):
    if code.lstrip().startswith('.'):
        raise ValueError('Ders koşucusu yönetim komutu çalıştırmaz')
    table=request(fixture(setup,extra)+code)
    columns=table['Columns']
    rows=[]
    for row in table['Rows']:
        cells=[]
        for value,col in zip(row,columns):
            kind=col.get('ColumnType','')
            if value is not None and kind=='datetime':
                dt=datetime.fromisoformat(value.replace('Z','+00:00'))
                value=dt.strftime('%Y-%m-%d %H:%M') if not (dt.second or dt.microsecond) else dt.strftime('%Y-%m-%d %H:%M:%S.%f').rstrip('0').rstrip('.')
            cells.append(value)
        rows.append(tuple(cells))
    return [c['ColumnName'] for c in columns],rows


if __name__=='__main__':
    print(ensure()['Rows'])
    print(query('range n from 0 to 2 step 1'))
