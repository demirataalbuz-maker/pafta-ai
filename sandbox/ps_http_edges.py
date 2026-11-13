"""Loopback-only HTTP witnesses for PS23 redirects, multipart and timeout."""
import atexit
from email import policy
from email.parser import BytesParser
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time
from urllib.parse import urlsplit


def start():
    log=Path('ps_http_requests.jsonl').resolve()
    log.write_text('',encoding='utf-8')
    lock=threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass

        def record(self,**fields):
            with lock,log.open('a',encoding='utf-8') as output:
                output.write(json.dumps({'method':self.command,'path':self.path,**fields},ensure_ascii=False)+'\n')

        def reply(self,status,value,headers=None,body_delay=0):
            body=json.dumps(value,ensure_ascii=False).encode('utf-8')
            try:
                self.send_response(status)
                self.send_header('Content-Type','application/json; charset=utf-8')
                self.send_header('Content-Length',str(len(body)))
                for key,val in (headers or {}).items():self.send_header(key,val)
                self.end_headers();self.wfile.flush()
                if body_delay:time.sleep(body_delay)
                self.wfile.write(body)
            except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):pass

        def do_GET(self):
            path=urlsplit(self.path).path
            self.record()
            if path.startswith('/hop/'):
                try:n=int(path.rsplit('/',1)[1])
                except ValueError:return self.reply(400,{'error':'number'})
                if not 0<=n<=5:return self.reply(400,{'error':'range'})
                if n:return self.reply(302,{}, {'Location':f'/hop/{n-1}'})
                return self.reply(200,{'ok':True})
            if path.startswith(('/delay/','/body-delay/')):
                try:ms=int(path.rsplit('/',1)[1])
                except ValueError:return self.reply(400,{'error':'number'})
                if not 0<=ms<=3000:return self.reply(400,{'error':'range'})
                if path.startswith('/body-delay/'):
                    return self.reply(200,{'ms':ms},body_delay=ms/1000)
                time.sleep(ms/1000)
                return self.reply(200,{'ms':ms})
            return self.reply(404,{'error':'missing'})

        def do_POST(self):
            length=int(self.headers.get('Content-Length','0'))
            if not 0<=length<=1_048_576:return self.reply(413,{'error':'size'})
            raw=self.rfile.read(length)
            content_type=self.headers.get('Content-Type','')
            if self.path!='/form':return self.reply(404,{'error':'missing'})
            if not content_type.lower().startswith('multipart/form-data;'):
                self.record(content_type=content_type)
                return self.reply(415,{'error':'multipart required'})
            message=BytesParser(policy=policy.default).parsebytes(
                b'Content-Type: '+content_type.encode('ascii')+b'\r\nMIME-Version: 1.0\r\n\r\n'+raw)
            fields={};files={}
            for part in message.iter_parts():
                name=part.get_param('name',header='content-disposition')
                if name in fields or name in files:return self.reply(400,{'error':'duplicate'})
                data=part.get_payload(decode=True) or b''
                filename=part.get_filename()
                if filename is None:fields[name]=data.decode('utf-8')
                else:files[name]={'filename':filename,'size':len(data),'sha256':hashlib.sha256(data).hexdigest()}
            self.record(content_type=content_type,fields=fields,files=files)
            if set(fields)!={'not'} or set(files)!={'dosya'}:return self.reply(400,{'error':'fields'})
            return self.reply(200,{'note':fields['not'],**files['dosya']})

    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    atexit.register(server.server_close)
    base=f'http://127.0.0.1:{server.server_port}'
    Path('ps_http_adres.txt').write_text(base,encoding='utf-8')
    return server,thread


if __name__=='__tezgah__':
    start()
