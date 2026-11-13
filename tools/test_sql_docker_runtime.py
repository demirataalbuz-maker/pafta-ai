"""SQ22 pinned server semantics, read-only credentials and failure cleanup."""
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.lessons import Library
from engine.runners import for_step, get
from sandbox.sql_docker_lab import IMAGES, ensure, session, client, docker, NAMES


def absent(motor, name):
    if motor == 'mysql':
        out = client(motor, f"SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME='{name}'; SELECT User FROM mysql.user WHERE User='{name}';")
        assert '<row>' not in out, name
    else:
        out = client(motor, f"SELECT CASE WHEN DB_ID('{name}') IS NULL AND SUSER_ID('{name}') IS NULL THEN 'gone' ELSE 'leaked' END AS state;")
        assert 'gone' in out and 'leaked' not in out, name


def main():
    records = []
    versions = {}
    for motor in IMAGES:
        ensure(motor)
        with session(motor, 'CREATE TABLE witness(id int); INSERT INTO witness VALUES (1);') as lab:
            name = lab.name
            assert lab.query('SELECT id FROM witness') == [{'id': '1'}]
            assert lab.query('SELECT NULL AS missing, 0 AS zero') == [{'missing': None, 'zero': '0'}]
            try:
                client(motor, 'DELETE FROM witness;', name, name, lab.password)
            except RuntimeError:
                pass
            else:
                raise AssertionError('Student account could modify the fixture')
            assert lab.query('SELECT id FROM witness') == [{'id': '1'}]
            q = 'SELECT VERSION() AS version' if motor == 'mysql' else "SELECT CAST(SERVERPROPERTY('ProductVersion') AS varchar(40)) AS version"
            versions[motor] = lab.query(q)[0]['version']
        absent(motor, name)
        try:
            with session(motor) as lab:
                fault_name = lab.name
                raise ValueError('injected test fault')
        except ValueError:
            pass
        absent(motor, fault_name)
        records.append({'motor': motor, 'case': 'read-only + NULL/zero + normal/fault cleanup', 'status': 'pass'})
        print(motor + ': privileges and cleanup passed', flush=True)

    steps = Library().lesson('sql', 'sq22')['steps']
    mutations = {
        'mysql': [('real division', 'DIV 60', '/ 60'),
                  ('wrong divisor boundary', 'DIV 60', 'DIV 61'),
                  ('byte length used as characters', 'CHAR_LENGTH(ad)', 'LENGTH(ad)'),
                  ('character length used as bytes', 'LENGTH(ad) AS bayt', 'CHAR_LENGTH(ad) AS bayt'),
                  ('null concatenation lost', "CONCAT_WS(' ',ad,soyad)", "CONCAT(ad,' ',soyad)"),
                  ('empty surname stripped', "CONCAT_WS(' ',ad,soyad)", "TRIM(CONCAT_WS(' ',ad,soyad))"),
                  ('order reversed', 'ORDER BY id', 'ORDER BY id DESC')],
        'mssql': [('equal score excluded', '>= 80', '> 80'),
                  ('below threshold accepted', '>= 80', '>= 79'),
                  ('TOP one', 'TOP (2)', 'TOP (1)'),
                  ('TOP three', 'TOP (2)', 'TOP (3)'),
                  ('wrong tie order', 'id ASC', 'id DESC'),
                  ('wrong score order', 'puan DESC', 'puan ASC'),
                  ('NULL text lost', "COALESCE(aciklama,N'belirsiz')", 'aciklama')],
    }
    for motor, changes in mutations.items():
        st = next(s for s in steps if s['kind'] == 'gorev' and s.get('meta', {}).get('motor') == motor)
        runner = for_step(get('sql'), st)
        assert runner.test(st['solution'], st)['status'] == 'pass'
        for label, old, new in changes:
            assert old in st['solution']
            r = runner.test(st['solution'].replace(old, new), st)
            assert r['status'] == 'fail', (motor, label, r)
            records.append({'motor': motor, 'mutation': label, 'status': 'rejected'})
            print(motor + ': ' + label + ': rejected', flush=True)
    # Worker timeout must leave no active server session/database/login behind.
    for motor, code in [('mysql', 'SELECT SLEEP(20) AS n'),
                        ('mssql', "SELECT 1 AS n; WAITFOR DELAY '00:00:20'; SELECT 2 AS n")]:
        from sandbox.sql_container_runner import ContainerSqlRunner
        start = time.monotonic()
        r = ContainerSqlRunner(motor).execute({'mode': 'run', 'code': code}, timeout=2)
        elapsed = time.monotonic() - start
        assert r['status'] == 'timeout' and elapsed < 18, (motor, r, elapsed)
        if motor == 'mysql':
            residual = client(motor, "SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME LIKE 'pf\\_%'; SELECT User FROM mysql.user WHERE User LIKE 'pf\\_%'; SELECT USER FROM information_schema.PROCESSLIST WHERE USER LIKE 'pf\\_%';")
            assert '<row>' not in residual, 'Timeout left a MySQL object or live query'
        else:
            residual = client(motor, "SELECT name FROM sys.databases WHERE name LIKE 'pf[_]%'; SELECT name FROM sys.sql_logins WHERE name LIKE 'pf[_]%';")
            assert 'pf_' not in residual, 'Timeout left a SQL Server database/login'
        records.append({'motor': motor, 'case': 'worker timeout and server cleanup', 'status': 'pass', 'seconds': round(elapsed, 2)})
        print(motor + ': timeout cleanup passed', flush=True)
    report = dict(versions=versions, images=IMAGES, references_passed=2,
                  mutants_rejected=sum('mutation' in r for r in records), mutants_passed=0,
                  cases=records, isolation='owned labelled containers, network none, no host ports, fresh read-only database per job')
    (ROOT / 'outputs/a-notu-sq22-docker-kabul.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
