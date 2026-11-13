"""Pinned MySQL/SQL Server clients; no automatic download or host port exposure."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import time
import uuid
import xml.etree.ElementTree as ET

IMAGES = {
    'mysql': 'mysql:8.4.8@sha256:2952e3be7807f06fc18de50b3ea1a632d5c70d63482ff7d7376fe3aa8999babf',
    'mssql': 'mcr.microsoft.com/mssql/server:2022-CU23-ubuntu-22.04@sha256:0ec7739e1c5ec2f57861facbe1f2b74f1d3e147c7c97edf91eeea920c5944d9c',
}
NAMES = {k: 'pafta-sql-' + k for k in IMAGES}
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


def config():
    folder = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'Pafta/labs/sql-docker'
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / 'config.json'
    # Atomic exclusive creation avoids two validators generating different passwords.
    if not path.exists():
        try:
            with path.open('x', encoding='utf-8') as f:
                json.dump({'password': 'Pafta1!' + secrets.token_hex(18)}, f)
        except FileExistsError:
            pass
    for _ in range(20):
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            time.sleep(.05)
    raise RuntimeError('SQL lab yapılandırması tamamlanamadı')


def docker(args, data=None, env=None, timeout=35):
    p = subprocess.run(['docker', *args], input=data, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, env=env, timeout=timeout,
                       creationflags=NO_WINDOW)
    if p.returncode:
        # Do not include environment/password-bearing command lines in exceptions.
        raise RuntimeError('Docker/SQL istemcisi başarısız: ' + p.stderr.decode('utf-8', 'replace')[-1200:])
    return p.stdout.decode('utf-8', 'strict').lstrip('\ufeff')


def client(motor, sql, database=None, user=None, password=None):
    if motor not in IMAGES:
        raise ValueError('mysql veya mssql gerekli')
    password = password or config()['password']
    env = dict(os.environ)
    if motor == 'mysql':
        env['MYSQL_PWD'] = password
        args = ['exec', '-i', '-e', 'MYSQL_PWD', NAMES[motor], 'mysql', '--default-character-set=utf8mb4',
                '--xml', '--batch', '--user=' + (user or 'root')]
        if database:
            args += ['--database=' + database]
    else:
        env['SQLCMDPASSWORD'] = password
        args = ['exec', '-i', '-e', 'SQLCMDPASSWORD', NAMES[motor], '/opt/mssql-tools18/bin/sqlcmd',
                '-S', 'tcp:127.0.0.1,1433', '-U', user or 'sa', '-C', '-b', '-r', '1', '-h', '-1', '-y', '8000', '-w', '65535', '-l', '5', '-t', '15']
        if database:
            args += ['-d', database]
        sql = 'SET NOCOUNT ON;\n' + sql
    return docker(args, sql.encode('utf-8'), env=env)


def ensure(motor):
    if motor not in IMAGES:
        raise ValueError('Bilinmeyen SQL motoru')
    # inspect never pulls a missing image. Installation is explicitly separate.
    image_id = docker(['image', 'inspect', IMAGES[motor], '--format', '{{.Id}}']).strip()
    try:
        info = json.loads(docker(['inspect', NAMES[motor]]))[0]
    except RuntimeError:
        env = dict(os.environ)
        password = config()['password']
        args = ['run', '-d', '--name', NAMES[motor], '--label', 'pafta.lab=sql-dialects',
                '--network', 'none', '--memory', '3g' if motor == 'mssql' else '1g', '--cpus', '2']
        if motor == 'mysql':
            env['MYSQL_ROOT_PASSWORD'] = password
            args += ['-e', 'MYSQL_ROOT_PASSWORD']
        else:
            env['MSSQL_SA_PASSWORD'] = password
            args += ['-e', 'MSSQL_SA_PASSWORD', '-e', 'ACCEPT_EULA=Y', '-e', 'MSSQL_PID=Developer']
        try:
            docker(args + [IMAGES[motor]], env=env, timeout=45)
        except RuntimeError:
            # A concurrent validate may have created the same owned container.
            info = json.loads(docker(['inspect', NAMES[motor]]))[0]
        info = json.loads(docker(['inspect', NAMES[motor]]))[0]
    if info.get('Config', {}).get('Labels', {}).get('pafta.lab') != 'sql-dialects' or info['Image'] != image_id:
        raise RuntimeError('Aynı isimde farklı/etiketsiz konteyner var; değiştirilmedi')
    if info['HostConfig']['NetworkMode'] != 'none' or info['HostConfig'].get('PortBindings'):
        raise RuntimeError('SQL lab dış ağ/host portu açmamalı')
    if not info['State']['Running']:
        docker(['start', NAMES[motor]], timeout=40)
    end = time.monotonic() + 100
    while True:
        try:
            client(motor, 'SELECT 1;')
            return
        except (RuntimeError, subprocess.TimeoutExpired) as error:
            if isinstance(error, RuntimeError) and any(code in str(error) for code in ('ERROR 1045', '18456')):
                raise RuntimeError('SQL kimlik doğrulaması başarısız; yerel sql-docker/config.json ile mevcut konteynerin kimlik bilgileri eşleşmiyor. Veritabanını silmeden yapılandırmayı doğrulayın.') from None
            if time.monotonic() >= end:
                raise RuntimeError('SQL sunucusu 100 saniyede hazır olmadı') from None
            time.sleep(1)


class Session:
    def __init__(self, motor, name, password):
        self.motor, self.name, self.password = motor, name, password

    def query(self, sql):
        # This adapter handles one SELECT (CTEs allowed), not multiple resultsets.
        sql = sql.strip().rstrip(';').strip()
        if not re.match(r'(?is)^(SELECT|WITH)\b', sql):
            raise ValueError('Bu tezgah yalnız tek SELECT/CTE sonucu destekler')
        if self.motor == 'mssql':
            raw = client(self.motor, sql + ' FOR JSON PATH, INCLUDE_NULL_VALUES;',
                         self.name, self.name, self.password).strip()
            rows = json.loads(''.join(raw.splitlines()) or '[]')
            return [{k: None if v is None else str(v) for k, v in r.items()} for r in rows]
        raw = client(self.motor, sql + ';', self.name, self.name, self.password)
        # mysql --xml writes one resultset, column names retained, SQL NULL explicit.
        root = ET.fromstring(raw)
        return [{f.attrib['name']: f.text if not f.attrib.get('{http://www.w3.org/2001/XMLSchema-instance}nil') else None
                 for f in r.findall('field')} for r in root.findall('row')]


@contextmanager
def session(motor, setup=''):
    name = 'pf_' + uuid.uuid4().hex[:28]
    password = 'Pafta2!' + secrets.token_hex(16)
    created = False
    try:
        created = True
        if motor == 'mysql':
            client(motor, f"CREATE DATABASE `{name}` CHARACTER SET utf8mb4; CREATE USER '{name}'@'localhost' IDENTIFIED BY '{password}'; GRANT SELECT ON `{name}`.* TO '{name}'@'localhost';")
        else:
            client(motor, f"CREATE DATABASE [{name}]; CREATE LOGIN [{name}] WITH PASSWORD='{password}', CHECK_POLICY=OFF;")
            client(motor, f'CREATE USER [{name}] FOR LOGIN [{name}]; ALTER ROLE db_datareader ADD MEMBER [{name}];', name)
        if setup.strip():
            client(motor, setup, name)
        yield Session(motor, name, password)
    finally:
        # Cleanup also runs after SQL/test exceptions. No wildcard deletion.
        if created:
            if motor == 'mysql':
                active = ET.fromstring(client(motor, f"SELECT ID AS id FROM information_schema.PROCESSLIST WHERE USER='{name}';"))
                for row in active.findall('row'):
                    identifier = row.find('field').text
                    if identifier and identifier.isdigit():
                        try:
                            client(motor, 'KILL ' + identifier + ';')
                        except RuntimeError:
                            pass  # A finished query may already have disconnected.
                client(motor, f"DROP DATABASE IF EXISTS `{name}`; DROP USER IF EXISTS '{name}'@'localhost';")
            else:
                client(motor, f"IF DB_ID('{name}') IS NOT NULL BEGIN ALTER DATABASE [{name}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE; DROP DATABASE [{name}]; END; IF SUSER_ID('{name}') IS NOT NULL DROP LOGIN [{name}];")


if __name__ == '__main__':
    for motor in IMAGES:
        ensure(motor)
        with session(motor) as lab:
            query = 'SELECT VERSION() AS version' if motor == 'mysql' else "SELECT CAST(SERVERPROPERTY('ProductVersion') AS varchar(40)) AS version"
            print(motor, lab.query(query))
