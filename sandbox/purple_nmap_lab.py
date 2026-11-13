"""Owned loopback Nmap lab. No downloads, arbitrary targets or global process cleanup."""
from pathlib import Path
import http.client
import ast,hashlib,http.server,json,os,platform,shutil,socket,subprocess,threading,time,urllib.request
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
FIX=ROOT/'tracks/purple/fixtures/pu18_nmap'

def hazirla():
    dst=Path('kesif');dst.mkdir(exist_ok=True)
    for f in FIX.iterdir():
        if f.is_file() and not (dst/f.name).exists():shutil.copyfile(f,dst/f.name)

def kod_koruma(src):
    tree=ast.parse(src)
    for n in ast.walk(tree):
        if isinstance(n,ast.Import):
            if any(a.name not in ('xml.etree.ElementTree','json','pathlib') for a in n.names):return False
        if isinstance(n,ast.ImportFrom):
            if not (n.module=='pathlib' and all(a.name=='Path' for a in n.names) or n.module=='purple_nmap_lab' and all(a.name=='calistir' for a in n.names)):return False
        if isinstance(n,ast.Name) and n.id in ('exec','eval','compile','getattr','setattr','globals','locals','vars','__import__','open'):return False
        if isinstance(n,ast.Attribute) and n.attr.startswith('_'):return False
    return True

def _persist(rec):
    d=Path(os.environ.get('PAFTA_DATA',str(ROOT/'data')))/'purple-kanit'
    d.mkdir(parents=True,exist_ok=True)
    p=d/('pu18-'+str(time.time_ns())+'.json')
    p.write_text(json.dumps(rec,ensure_ascii=False,indent=2),encoding='utf-8')
    return str(p)

def calistir(xml_coz,degisim,karar,kabul=False):
    exe=shutil.which('nmap')
    if not exe:raise RuntimeError('Nmap PATH içinde yok. Deney yapılmadı; kurulum/indirme otomatik değil.')
    rec={'kaynak':'gercek','kabul':False,'pilot':'pu18-nmap','cihaz':{'os':platform.platform(),'python':platform.python_version()},'scans':[],'http':[]}
    servers=[];threads=[];reserve=None
    class Server(http.server.ThreadingHTTPServer):
        daemon_threads=True
        def handle_error(self,request,address):
            rec.setdefault('connection_reset_observations',0);rec['connection_reset_observations']+=1
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body=self.server.canary.encode();self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
            rec['http'].append({'port':self.server.server_port,'path':self.path,'status':200,'body':self.server.canary})
        def log_message(self,*args):pass
    def add():
        s=Server(('127.0.0.1',0),Handler);s.canary='PAFTA-'+os.urandom(8).hex()
        t=threading.Thread(target=s.serve_forever,kwargs={'poll_interval':0.05},daemon=True);t.start();servers.append(s);threads.append(t);return s
    def ground(ports):
        results={}
        for port in ports:
            with socket.socket() as so:
                so.settimeout(1);results[str(port)]=so.connect_ex(('127.0.0.1',port))==0
        return results
    try:
        v=subprocess.run([exe,'--version'],capture_output=True,text=True,timeout=10,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if v.returncode:raise RuntimeError('Nmap --version başarısız')
        rec.update(executable=exe,sha256=hashlib.sha256(Path(exe).read_bytes()).hexdigest(),version=v.stdout)
        a=add();b=add();reserve=socket.socket();reserve.bind(('127.0.0.1',0))
        ports=[a.server_port,b.server_port,reserve.getsockname()[1]];rec['ports']=ports
        for s in servers:
            conn=http.client.HTTPConnection('127.0.0.1',s.server_port,timeout=3)
            try:
                conn.request('GET','/');res=conn.getresponse()
                if res.status!=200 or res.read().decode()!=s.canary:raise RuntimeError('HTTP canary eşleşmedi')
            finally:conn.close()
        maps=[]
        for phase in ('once','sonra'):
            if phase=='sonra':a.shutdown();a.server_close();threads[0].join(2)
            args=[exe,'-sT','-Pn','-n','--unprivileged','--max-retries','0','--host-timeout','8s','-p',','.join(map(str,ports)),'-oX','-','127.0.0.1']
            p=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',timeout=12,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            row={'phase':phase,'argv':args,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'ground_tcp':ground(ports)};rec['scans'].append(row)
            if p.returncode:raise RuntimeError('Nmap başarısız: '+p.stderr)
            root=ET.fromstring(p.stdout)
            if root.find('./runstats/finished').get('exit')!='success':raise RuntimeError('Nmap tamamlanmadı')
            expected={int(x.get('portid')):x.find('state').get('state') for x in root.findall('./host/ports/port')}
            got=xml_coz(p.stdout)
            if got!=expected or set(got)!=set(ports):raise AssertionError('Gerçek XML port/durum ayrıştırması yanlış')
            row['parsed']=got;maps.append(got)
        if maps[0][ports[0]]!='open' or maps[0][ports[1]]!='open' or maps[1][ports[1]]!='open':raise RuntimeError('Açık servis kontrolü başarısız; ortam deneyi geçmedi')
        if rec['scans'][0]['ground_tcp']!={str(ports[0]):True,str(ports[1]):True,str(ports[2]):False}:raise RuntimeError('Önce TCP kontrolü başarısız')
        if rec['scans'][1]['ground_tcp']!={str(ports[0]):False,str(ports[1]):True,str(ports[2]):False}:raise RuntimeError('Sonra TCP kontrolü başarısız')
        changes=[{'port':p,'once':maps[0][p],'sonra':maps[1][p]} for p in sorted(ports) if maps[0][p]!=maps[1][p]]
        if not any(x['port']==ports[0] for x in changes):raise RuntimeError('Kapatılan servisin Nmap gözlemi değişmedi; kabul yok')
        if degisim(*maps)!=changes:raise AssertionError('Gerçek değişim ölçümü yanlış')
        for m in maps:
            for state in m.values():
                want='acik' if state=='open' else 'kapali' if state=='closed' else 'belirsiz'
                if karar(state)!=want:raise AssertionError('Belirsiz port kesin hükme çevrildi')
        rec['changes']=changes;rec['not']='TCP ground truth ve Nmap gözlemi ayrıdır; filtered sonucu closed yapılmadı.'
        rec['kabul']=bool(kabul)
    except BaseException as e:
        rec['error']={'type':type(e).__name__,'msg':str(e)};raise
    finally:
        for s in servers:s.shutdown();s.server_close()
        for t in threads:t.join(2)
        if reserve:reserve.close()
        rec['cleanup']={'own_threads_stopped':all(not t.is_alive() for t in threads),'only_owned_resources':True}
        if not rec['cleanup']['own_threads_stopped']:rec['kabul']=False
        path=_persist(rec)
        print('GERÇEK Nmap · '+('kabul edildi' if rec['kabul'] else 'kabul yok / deneme')+' · kanıt: '+path)
    print(json.dumps({'ports':rec['ports'],'changes':rec['changes'],'warnings':[r['stderr'] for r in rec['scans']]},ensure_ascii=False))
    return rec
