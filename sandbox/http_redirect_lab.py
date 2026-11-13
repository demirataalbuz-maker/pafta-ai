"""Physically restricted to two generated loopback services, including bad clients."""
from contextlib import AbstractContextManager
from urllib.parse import urlsplit
import http.client
import json
from http_lab import Lab


class RedirectLab(AbstractContextManager):
    def __init__(self):
        self.public = Lab()
        self.internal = Lab()
        self.base = self.public.base
        self.public.redirects.update({
            '/to-internal': (302, self.internal.base+'/secret'),
            '/r301': (301, '/echo'), '/r302': (302, '/echo'), '/r307': (307, '/echo'),
            '/chain1': (302, '/echo'), '/chain2': (302, '/chain1'),
            '/chain3': (302, '/chain2'), '/loop': (302, '/loop'),
        })

    def wire(self, method, url, body=None):
        u = urlsplit(url)
        if u.scheme!='http' or u.username is not None or u.password is not None or u.hostname!='127.0.0.1' or u.port not in (self.public.server.server_port,self.internal.server.server_port):
            raise ValueError('transport is restricted to this lab; no external or machine-internal access')
        target = (u.path or '/') + ('?'+u.query if u.query else '')
        conn = http.client.HTTPConnection('127.0.0.1',u.port,timeout=3)
        try:
            raw = None if body is None else json.dumps(body).encode('utf-8')
            conn.request(method,target,body=raw,headers={'Content-Type':'application/json'})
            r=conn.getresponse()
            data=r.read()
            return {'status':r.status,'headers':{k.lower():v for k,v in r.getheaders()},'body':json.loads(data)}
        finally:
            conn.close()

    def __exit__(self,*args):
        self.public.close()
        self.internal.close()
