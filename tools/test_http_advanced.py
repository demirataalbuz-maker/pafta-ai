"""HTTP HT17–24: real transports, prediction answers and behavioral mutants.

No Burp GUI automation: its manual acceptance checklist is in docs/http-lab.md.
python -X utf8 tools/test_http_advanced.py
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import http.client
import socket
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'sandbox'),str(ROOT/'.deps')]
from engine.lessons import parse_lesson
from engine.runners import get, for_step
from http_lab import Lab
from http_ws_lab import exchange


def lessons():
    return {p.stem[:4]:parse_lesson(p.read_text(encoding='utf-8'))
            for p in (ROOT/'tracks/http/lessons').glob('ht*.md') if int(p.name[2:4])>=17}


ANSWERS={
    'ht17':'200\n403\n401\n',
    'ht18':'0 200\n60 0\n60 0\n0 404\n22 404\n',
    'ht19':"[True, True, False, False, False]\n['GET', 'OPTIONS', 'POST', 'OPTIONS', 'GET']\n",
    'ht20':"GET 'lax=L'\nPOST ''\n",
    'ht21':'[200, 403]\n[403, 200]\n[401, 401]\n',
    'ht22':'127.1 127.0.0.1\nother.test good.test\n',
    'ht23':'101 Ağ\n401\n403\n',
    'ht24':'200 A-only False\n200 None True\n',
}

# lesson, task index, exact one source mutation, replacement, behavior
MUTATIONS=[
 ('ht17',0,"hedef.startswith('//')","False",'scheme-relative target'),
 ('ht17',0,"ord(c)<=32","ord(c)<32",'space boundary'),
 ('ht17',0,"ord(c)>=127","ord(c)>127",'DEL boundary'),
 ('ht17',0,"or '#' in hedef","or False",'fragment'),
 ('ht17',0,"p[0]!=b'GET'","False",'method'),
 ('ht17',0,"p[2]!=b'HTTP/1.1'","False",'version'),
 ('ht17',1,'(kendi,baska,kendi)','(kendi,kendi,kendi)','changed target'),
 ('ht17',1,'cookie=cookie','cookie=None','same session'),
 ('ht18',0,'1<=port<=65535','1<port<=65535','port 1'),
 ('ht18',0,'1<=port<=65535','1<=port<65535','port 65535'),
 ('ht18',0,'type(port) is not int','not isinstance(port,int)','bool port'),
 ('ht18',0,"'--cacert',ca","'--insecure',ca",'CA required'),
 ('ht18',1,'100<=http_code<=399','100<http_code<=399','HTTP 100'),
 ('ht18',1,'100<=http_code<=399','100<=http_code<399','HTTP 399'),
 ('ht18',1,'400<=http_code<=599','400<http_code<=599','HTTP 400'),
 ('ht18',1,'400<=http_code<=599','400<=http_code<599','HTTP 599'),
 ('ht18',1,'exit_code in (0,22)','exit_code==0','curl fail-with-body'),
 ('ht18',1,'exit_code==60 and http_code==0','exit_code==60','inconsistent TLS + HTTP'),
 ('ht19',0,"e['path']=='/cors'","True",'unrelated path'),
 ('ht19',0,"if r['readable']","if True",'JS failure'),
 ('ht19',0,"sum(e['method']=='OPTIONS' for e in events)",'0','preflight count'),
 ('ht20',0,"r['status']!=200","False",'no session'),
 ('ht20',0,"headers={'X-CSRF-Token':r['body']['token']}",'headers={}','token required'),
 ('ht20',0,"cookie=cookie,headers=","cookie=None,headers=",'same session'),
 ('ht20',1,"cookie=b)['body']","cookie=a)['body']",'other session token'),
 ('ht20',1,"lab.snapshot()['revision']-once",'0','measured write effect'),
 ('ht20',1,"r['status']",'403','measured status'),
 ('ht21',0,"('GET','PATCH')","('GET',)",'write cells'),
 ('ht21',0,"changed=before!=lab.snapshot()['items']","changed=r['status']==200",'state not status'),
 ('ht21',0,"cookie=cookie","cookie=None",'account identity'),
 ('ht21',0,"data={'title':'kontrol'} if method=='PATCH' else None","data=None",'actual write'),
 ('ht22',0,"u.hostname=='127.0.0.1'","u.hostname.startswith('127.0.0.1')",'hostname suffix'),
 ('ht22',0,'u.username is None','True','userinfo'),
 ('ht22',0,'u.port==o.port','True','origin port'),
 ('ht22',0,"or '#' in url",'or False','URL fragment'),
 ('ht22',1,'hops>=max_redirects','hops>max_redirects','redirect limit equal end'),
 ('ht22',1,'hops>=max_redirects','hops>=max_redirects-1','exact permitted hops'),
 ('ht22',1,'kontrol(url)','pass','validate every destination'),
 ('ht22',1,'status in (301,302)','status in (301,302,307)','307 preserves POST'),
 ('ht22',1,"method,body='GET',None","method='GET'",'discard POST body'),
 ('ht23',0,'len(data)>125','len(data)>=125','125 bytes'),
 ('ht23',0,'len(data)>125','len(text)>125','UTF-8 bytes'),
 ('ht23',0,'0x80|len(data)','len(data)','client mask bit'),
 ('ht23',0,'mask[i%4]','mask[0]','mask rotation'),
 ('ht23',1,"status==101","status>=101",'exact upgrade status'),
 ('ht23',1,"h.get('sec-websocket-accept')==expected","True",'server proof'),
 ('ht23',1,"'upgrade' in {v.strip().lower() for v in h.get('connection','').split(',')}","'upgrade' in h.get('connection','').lower()",'connection token'),
 ('ht24',0,"{'id':no}","{'id':1}",'query variable value'),
 ('ht24',0,'id owner title secret','id owner title','field-level denial'),
 ('ht24',1,"'title':title","'title':'x'",'mutation variables'),
 ('ht24',1,"r['body'].get('errors',[])",'[]','preserve GraphQL errors'),
 ('ht24',1,"cookie=cookie","cookie=None",'authenticated context'),
]


class Curriculum(unittest.TestCase):
    def test_tasks_and_predictions(self):
        for lid,lesson in lessons().items():
            with self.subTest(lesson=lid):
                self.assertEqual(sum(s['kind']=='tahmin' for s in lesson['steps']),1)
                for step in lesson['steps']:
                    runner=for_step(get('http'),step)
                    if step['kind']=='gorev':
                        self.assertEqual(runner.test(step['solution'],step)['status'],'pass',lid)
                        self.assertEqual(runner.test(step['starter'],step)['status'],'fail',lid)
                    elif step['kind']=='tahmin':
                        r=runner.run(step['code'],setup=step.get('setup'))
                        self.assertEqual(r['status'],'ok',r)
                        self.assertFalse(any(k in ('err','raw') and v.strip() for k,v in r.get('segs',[])),r)
                        self.assertEqual(''.join(v for k,v in r.get('segs',[]) if k=='out'),ANSWERS[lid])

    def test_mutations(self):
        lib=lessons()
        def run(case):
            lid,index,old,new,name=case
            step=[s for s in lib[lid]['steps'] if s['kind']=='gorev'][index]
            source=step['solution']
            if old not in source: return name,{'status':'missing','old':old}
            return name,for_step(get('http'),step).test(source.replace(old,new,1),step)
        with ThreadPoolExecutor(max_workers=2) as pool:
            for name,result in pool.map(run,MUTATIONS):
                with self.subTest(mutation=name):
                    self.assertEqual(result['status'],'fail',result)


class NativeLab(unittest.TestCase):
    def test_persistent_cli_survives_independent_clients(self):
        with tempfile.TemporaryDirectory(prefix='pafta_http_cli_') as folder:
            p=subprocess.Popen([sys.executable,'-u',str(ROOT/'sandbox/http_lab.py'),'--port','0'],
                               cwd=folder,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',
                               creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            try:
                config=json.loads(p.stdout.readline())
                u=urlsplit(config['url'])
                def request(method,path,body=None,cookie=None,headers=None):
                    c=http.client.HTTPConnection(u.hostname,u.port,timeout=3)
                    h=dict(headers or {})
                    if cookie:h['Cookie']=cookie
                    raw=json.dumps(body).encode() if body is not None else None
                    try:
                        c.request(method,path,body=raw,headers=h)
                        r=c.getresponse();data=r.read()
                        return r.status,dict(r.getheaders()),json.loads(data)
                    finally:c.close()
                status,h,b=request('POST','/session',{'user':'ayse','password':'pafta-demo'})
                self.assertEqual(status,200)
                cookie=h['Set-Cookie'].split(';')[0]
                for expected,path in ((200,'/items/1'),(403,'/items/2'),(200,'/items/1')):
                    self.assertIsNone(p.poll())
                    self.assertEqual(request('GET',path,cookie=cookie)[0],expected)
                self.assertEqual(request('POST','/_control/reset')[0],403)
                self.assertEqual(request('POST','/_control/reset',headers=config['reset_header'])[0],200)
                self.assertEqual(request('GET','/items/1',cookie=cookie)[0],401)
            finally:
                p.terminate()
                p.communicate(timeout=6)
            with socket.socket() as s:
                self.assertNotEqual(s.connect_ex((u.hostname,u.port)),0)

    def test_real_browser_websocket(self):
        from http_browser_lab import browser_run
        with Lab() as lab:
            c=lab.login('ayse')
            r=browser_run({'mode':'ws','source':lab.base,'url':lab.base.replace('http:','ws:')+'/ws',
                           'cookie':c,'text':'Ağ'})
            self.assertEqual(r['results'],[{'text':'Ağ','code':1000}])

    def test_reset_ownership_and_csrf(self):
        with Lab() as lab:
            a,b=lab.login('ayse'),lab.login('berk')
            ta=lab.request('GET','/csrf',cookie=a)['body']['token']
            tb=lab.request('GET','/csrf',cookie=b)['body']['token']
            self.assertNotEqual(ta,tb)
            before=lab.snapshot()
            for token in ('', 'wrong',tb):
                self.assertEqual(lab.request('POST','/change',{'title':'x'},cookie=a,headers={'X-CSRF-Token':token})['status'],403)
            for n,expected in ((0,422),(1,200),(80,200),(81,422)):
                self.assertEqual(lab.request('POST','/change',{'title':'x'*n},cookie=a,headers={'X-CSRF-Token':ta})['status'],expected)
            self.assertEqual(lab.snapshot()['revision'],2)
            self.assertEqual(lab.request('PATCH','/items/2',{'title':'bad'},cookie=a)['status'],403)
            self.assertEqual(lab.snapshot()['items'],before['items'])
            self.assertEqual(lab.request('POST','/_control/reset')['status'],403)
            self.assertEqual(lab.request('POST','/_control/reset',headers={'X-Lab-Control':lab.control})['status'],200)
            self.assertEqual(lab.request('GET','/csrf',cookie=a)['status'],401)
            port=lab.server.server_port
        with socket.socket() as s:
            self.assertNotEqual(s.connect_ex(('127.0.0.1',port)),0)

    def test_graphql_real_language_and_resolvers(self):
        with Lab() as lab:
            a=lab.login('ayse')
            def gql(q,variables=None):
                return lab.request('POST','/graphql',{'query':q,'variables':variables},cookie=a)['body']
            r=gql('query { x:item(id:2){...Fields} } fragment Fields on Item { id title secret }')
            self.assertEqual(r['data']['x']['id'],2)
            self.assertIsNone(r['data']['x']['secret'])
            self.assertEqual(r['errors'][0]['path'],['x','secret'])
            self.assertEqual(r['errors'][0]['extensions']['code'],'FORBIDDEN')
            r=gql('{__schema{queryType{name} mutationType{name}}}')
            self.assertEqual(r['data']['__schema'],{'queryType':{'name':'Query'},'mutationType':{'name':'Mutation'}})
            before=lab.snapshot()
            for q in ('{item(id:"1"){id}}','{item(id:1){doesNotExist}}','query {','query {rename(id:1,title:"bad"){id}}'):
                self.assertTrue(gql(q).get('errors'))
            self.assertEqual(lab.snapshot()['items'],before['items'])
            for n,accepted in ((0,False),(1,True),(80,True),(81,False)):
                before=lab.snapshot()['revision']
                r=gql('mutation($n:String!){rename(id:1,title:$n){title}}',{'n':'z'*n})
                self.assertEqual(bool(r.get('errors')),not accepted)
                self.assertEqual(lab.snapshot()['revision']-before,int(accepted))

    def test_websocket_rejections_are_real_close_frames(self):
        with Lab() as lab:
            c=lab.login('ayse')
            for kwargs,status in (({'cookie':None},401),({'cookie':c,'origin':'null'},403),({'cookie':c,'version':'12'},400),({'cookie':c,'key':'YQ=='},400)):
                self.assertEqual(exchange(lab,**kwargs)['status'],status)
            cases=[(b'\x81\x00',1002), (b'\x01\x80',1003), (b'\x82\x80',1003),
                   (b'\xc1\x80',1002), (b'\x81\xfe',1009),
                   (b'\x81\x81'+b'\0'*4+b'\xff',1007)]
            for frame,code in cases:
                r=exchange(lab,c,frame=frame)
                self.assertEqual((r['opcode'],r['close']),(8,code))


if __name__=='__main__':
    unittest.main(verbosity=2)
