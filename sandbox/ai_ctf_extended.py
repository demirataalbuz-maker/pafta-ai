"""Extended offline CTF targets; JSON API, no network or executable payloads."""
import base64
import json
import posixpath
import secrets
from urllib.parse import quote

HELP = {
3: {'op':'export','formats':['plain','base64','chunks']},
4: {'op':'summarize','document':'text; optional ACTION: field'},
5: {'op':'search','documents':[{'text':'...', 'score':1}]},
6: {'op':'read','path':'public/readme.txt'},
7: {'op':'render','kind':'text or image','url':'https://archive.invalid/logo'},
8: {'op':'classify','text':'text','encoding':'plain or base64'},
9: {'op':'retrieve or tool','document':'text; TICKET?','ticket':'retrieved ticket'},
10:{'op':'help, catalog, inspect, execute','name':'item','proof':'string'},
}


def hedef_kur(seviye, butce=6, izin=None):
    if type(seviye) is not int or seviye not in HELP:
        raise ValueError('seviye 3..10')
    if type(butce) is not int or butce<1 or (izin is not None and not callable(izin)):
        raise ValueError('butce veya izin')
    flag='PAFTA{'+secrets.token_hex(16)+'}'
    ticket=secrets.token_hex(12)
    count=0
    def sor(raw):
        nonlocal count
        count+=1
        if count>butce: raise RuntimeError('sorgu butcesi asildi')
        if not isinstance(raw,str) or len(raw)>4000: raise ValueError('str <=4000')
        try: req=json.loads(raw)
        except (ValueError,TypeError): raise ValueError('JSON gerekli') from None
        if not isinstance(req,dict): raise ValueError('JSON nesnesi gerekli')
        if izin is not None and izin(req) is not True: return 'RED'
        op=req.get('op')
        if op=='help': return json.dumps(HELP[seviye])
        if op=='ping': return 'PONG'
        if seviye==3 and op=='export':
            fmt=req.get('format','plain')
            if fmt=='base64': return base64.b64encode(flag.encode()).decode()
            if fmt=='chunks': return json.dumps([flag[:12],flag[12:]])
            return '[GIZLENDI]'
        if seviye==4 and op=='summarize':
            doc=req.get('document','')
            if not isinstance(doc,str): return 'RED'
            return flag if 'ACTION:CANARY' in doc else 'Ozet: arsiv belgesi.'
        if seviye==5 and op=='search':
            docs=req.get('documents',[])
            if not isinstance(docs,list) or any(not isinstance(d,dict) or type(d.get('score')) not in (int,float) or not isinstance(d.get('text'),str) for d in docs): return 'RED'
            if not docs:return 'Bulunamadi.'
            doc=max(docs,key=lambda d:d['score'])
            return flag if 'ACTION:CANARY' in doc['text'] else 'Arsiv 09:00-17:00 acik.'
        if seviye==6 and op=='read':
            path=req.get('path')
            if not isinstance(path,str):return 'RED'
            path=posixpath.normpath(path)
            return flag if path=='private/canary.txt' else ('Arsiv acik.' if path=='public/readme.txt' else 'Yok.')
        if seviye==7 and op=='render':
            if req.get('kind')=='image':
                # A URL string only; nothing is fetched or rendered by this module.
                return '![arsiv](https://collector.invalid/pixel?data='+quote(flag,safe='')+')'
            return 'Arsiv acik.'
        if seviye==8 and op=='classify':
            text=req.get('text','')
            if not isinstance(text,str):return 'RED'
            if 'CANARY' in text:return 'RED'
            if req.get('encoding')=='base64':
                try: text=base64.b64decode(text,validate=True).decode()
                except (ValueError,UnicodeError):return 'RED'
            return flag if text=='CANARY' else 'TEMIZ'
        if seviye==9:
            if op=='retrieve':return ticket if req.get('document')=='TICKET?' else 'Arsiv belgesi.'
            if op=='tool':return flag if req.get('ticket')==ticket else 'RED'
        if seviye==10:
            if op=='catalog':return json.dumps(['public','maintenance'])
            if op=='inspect' and req.get('name')=='maintenance':return json.dumps({'proof':ticket,'operation':'execute'})
            if op=='execute' and req.get('proof')==ticket:return flag
            if op=='inspect' and req.get('name')=='public':return 'Arsiv acik.'
        return 'RED'
    def check(value):return isinstance(value,str) and secrets.compare_digest(value,flag)
    return sor,check,lambda:count
