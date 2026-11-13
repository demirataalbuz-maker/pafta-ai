"""pu19: stdlib HTTP + SQLite lab. Sentetik veri; yalnız kendi kaynaklarını temizler."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import http.client
import json
import secrets
import shutil
import sqlite3
import tempfile
import threading

FIXTURE = Path(__file__).resolve().parents[1] / "tracks/purple/fixtures/pu19_yerel_sqli"
SELECT = "SELECT username, canary FROM accounts WHERE username = ? AND password = ?"


def hazirla(hedef=None):
    """Eksik dosyaları kopyalar; mevcut öğrenci dosyasına dokunmaz."""
    dest = Path(hedef or Path.cwd()) / "yerel_sqli"
    dest.mkdir(parents=True, exist_ok=True)
    for name in ("istekler.json", "istek.http", "sorgular.sql", "README.md"):
        if not (dest / name).exists():
            shutil.copyfile(FIXTURE / name, dest / name)
    return dest


class YerelSQLiLab:
    """Context manager: rastgele port, özel geçici DB, gerçek HTTP audit kaydı."""
    def __init__(self):
        self.username = "uye_" + secrets.token_hex(4)
        self.password = "demo_" + secrets.token_hex(5)
        self.canary = "PU19_" + secrets.token_hex(8)
        self._tmp = None
        self._server = None
        self._thread = None
        self.temizlendi = False

    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="pu19_sqli_")
        self.db_path = Path(self._tmp.name) / "lab.sqlite3"
        try:
            with self.baglanti() as db:
                db.executescript("CREATE TABLE accounts(username TEXT PRIMARY KEY, password TEXT, canary TEXT);"
                                 "CREATE TABLE audit(id INTEGER PRIMARY KEY, route TEXT, username TEXT, password TEXT, status INTEGER, body TEXT, sql_text TEXT, parameters TEXT);")
                db.execute("INSERT INTO accounts VALUES(?,?,?)", (self.username, self.password, self.canary))
                db.execute("INSERT INTO accounts VALUES(?,?,?)", ("O'Reilly_" + secrets.token_hex(3), "nokta;--", "SENTETIK_IKINCI"))
            lab = self

            class Handler(BaseHTTPRequestHandler):
                def log_message(self, *args):
                    pass

                def do_POST(self):
                    if self.path not in ("/vulnerable/login", "/secure/login"):
                        self.send_error(404)
                        return
                    try:
                        length = int(self.headers.get("Content-Length", "0"))
                        if not 0 < length <= 4096:
                            raise ValueError("body boyutu")
                        data = json.loads(self.rfile.read(length))
                        if (not isinstance(data, dict) or set(data) != {"username", "password"}
                                or any(not isinstance(v, str) or not 1 <= len(v) <= 256 for v in data.values())):
                            raise ValueError("şema")
                    except (ValueError, TypeError, UnicodeError):
                        self.reply(400, {"error": "gecersiz_json_veya_sema"})
                        return
                    u, pw = data["username"], data["password"]
                    params = (u, pw) if self.path == "/secure/login" else ()
                    sql = SELECT if params else (
                        "SELECT username, canary FROM accounts WHERE username = '" + u + "' AND password = '" + pw + "'")
                    with lab.baglanti() as db:
                        try:
                            row = db.execute(sql, params).fetchone()
                            status = 200 if row else 401
                            body = {"username": row[0], "canary": row[1]} if row else {"error": "login_reddedildi"}
                        except sqlite3.Error:
                            status, body = 500, {"error": "sql_hatasi"}
                        db.execute("INSERT INTO audit(route,username,password,status,body,sql_text,parameters) VALUES(?,?,?,?,?,?,?)",
                                   (self.path, u, pw, status, json.dumps(body), sql, json.dumps(params)))
                    self.reply(status, body)

                def reply(self, status, body):
                    raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
                    self.send_response(status)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Content-Length", str(len(raw)))
                    self.end_headers()
                    self.wfile.write(raw)

            self._server = HTTPServer(("127.0.0.1", 0), Handler)
            self.port = self._server.server_address[1]
            self._thread = threading.Thread(target=self._server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
            self._thread.start()
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    @contextmanager
    def baglanti(self):
        db = sqlite3.connect(self.db_path, timeout=2)
        try:
            with db:
                yield db
        finally:
            db.close()

    def post(self, route, data):
        """Hedef sabittir; proxy/env/dış URL kullanılmaz. Bağlantı hatası yayılır."""
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        try:
            conn.request("POST", route, raw, {"Content-Type": "application/json"})
            response = conn.getresponse()
            return {"status": response.status, "body": json.loads(response.read())}
        finally:
            conn.close()

    def audit(self):
        with self.baglanti() as db:
            rows = db.execute("SELECT route,username,password,status,body,sql_text,parameters FROM audit ORDER BY id").fetchall()
        return [{"route": r[0], "username": r[1], "password": r[2], "status": r[3],
                 "body": json.loads(r[4]), "sql": r[5], "parameters": json.loads(r[6])} for r in rows]

    def __exit__(self, *args):
        if self._server is not None:
            if self._thread is not None and self._thread.is_alive():
                self._server.shutdown()
                self._thread.join(timeout=3)
            self._server.server_close()
        if self._tmp is not None:
            self._tmp.cleanup()
        self.temizlendi = (self._thread is None or not self._thread.is_alive()) and not getattr(self, "db_path", Path("__yok__")).exists()


def kod_koruma(src):
    import ast
    for n in ast.walk(ast.parse(src)):
        if isinstance(n,ast.Import) and any(a.name not in ('json','pathlib') for a in n.names):return False
        if isinstance(n,ast.ImportFrom) and not (n.module=='pathlib' and all(a.name=='Path' for a in n.names) or n.module=='purple_sqli_lab' and all(a.name=='calistir' for a in n.names)):return False
        if isinstance(n,ast.Name) and n.id in ('exec','eval','compile','getattr','setattr','globals','locals','vars','__import__'):return False
        if isinstance(n,ast.Attribute) and (n.attr.startswith('_') or n.attr in ('executescript','audit')):return False
        if isinstance(n,ast.Assign) and any(isinstance(x,ast.Attribute) for x in n.targets):return False
    return True

def calistir(guvenli_sorgu,dene,kabul=False):
    import os,platform,time,hashlib
    rec={'kaynak':'gercek','kabul':False,'pilot':'pu19-sqli','python':platform.python_version(),'sqlite':sqlite3.sqlite_version,'cihaz':platform.platform()}
    lab=YerelSQLiLab()
    try:
        with lab:
            rec['address']='127.0.0.1';rec['port']=lab.port
            attack={"username":"' OR 1=1 -- ","password":"yanlis"}
            normal={'username':lab.username,'password':lab.password}
            rows=dene(lab,normal,attack)
            audit=lab.audit();rec['audit']=audit;rec['student_rows']=rows
            expected=[{'status':a['status'],'body':a['body']} for a in audit]
            if len(audit)!=5 or rows!=expected:raise AssertionError('Yanıtlar gerçek beş HTTP/DB audit kaydıyla eşleşmeli')
            routes=['/vulnerable/login','/secure/login','/vulnerable/login','/secure/login','/vulnerable/login']
            if [a['route'] for a in audit]!=routes or [a['status'] for a in audit]!=[200,200,200,401,500]:raise AssertionError('normal, bypass, blocked ve bozuk SQL kontrolü yanlış')
            if rows[2]['body'].get('canary') not in (lab.canary,'SENTETIK_IKINCI'):raise AssertionError('Gerçek bypass canary yok')
            if rows[1]['body'].get('canary')!=lab.canary:raise AssertionError('Meşru secure login çalışmadı')
            with lab.baglanti() as db:
                rec['safe_query_normal']=guvenli_sorgu(db,lab.username,lab.password)
                rec['safe_query_attack']=guvenli_sorgu(db,**{'u':attack['username'],'p':attack['password']})
                if rec['safe_query_normal']!=(lab.username,lab.canary) or rec['safe_query_attack'] is not None:raise AssertionError('Öğrenci parameter binding gerçek DB üzerinde yanlış')
                u,pw,c=db.execute('SELECT username,password,canary FROM accounts WHERE username != ?', (lab.username,)).fetchone()
                if guvenli_sorgu(db,u,pw)!=(u,c):raise AssertionError('Tırnak ve SQL benzeri metin içeren meşru hesap engellendi')
                if db.execute('SELECT COUNT(*) FROM accounts').fetchone()[0]!=2:raise AssertionError('Hesap tablosu değişti')
            rec['db_sha256']=hashlib.sha256(lab.db_path.read_bytes()).hexdigest()
            rec['kabul']=bool(kabul)
    except BaseException as e:
        rec['error']={'type':type(e).__name__,'msg':str(e)};raise
    finally:
        rec['cleanup']=lab.temizlendi
        if not lab.temizlendi:rec['kabul']=False
        root=Path(__file__).resolve().parents[1]
        d=Path(os.environ.get('PAFTA_DATA',str(root/'data')))/'purple-kanit';d.mkdir(parents=True,exist_ok=True)
        out=d/('pu19-'+str(time.time_ns())+'.json');out.write_text(json.dumps(rec,ensure_ascii=False,indent=2),encoding='utf-8')
        print('GERÇEK HTTP + SQLite · '+('kabul edildi' if rec['kabul'] else 'kabul yok / deneme')+' · kanıt: '+str(out))
    print(json.dumps(rows,ensure_ascii=False));return rec
