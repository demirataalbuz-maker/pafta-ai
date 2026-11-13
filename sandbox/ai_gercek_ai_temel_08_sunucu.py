"""İki gerçek Ollama isteği ve yerel HTTP uygulamasında kiracı görünürlüğü."""
import ai_lab
import copy,json,threading,time,secrets,urllib.request,urllib.error
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from concurrent.futures import ThreadPoolExecutor

def kiraci_ref(kayitlar, kiraci):
    if not isinstance(kayitlar, list) or len(kayitlar) > 8:
        raise ValueError("kayıt listesi geçersiz")
    if any(not isinstance(x, dict) or set(x) != {"tenant", "k", "v"} for x in kayitlar):
        raise ValueError("kayıt şeması geçersiz")
    if any(not isinstance(x["tenant"], str) or not x["tenant"] or any(not isinstance(x[a], int) or isinstance(x[a], bool) for a in ("k", "v")) for x in kayitlar):
        raise ValueError("kayıt değeri geçersiz")
    if not isinstance(kiraci, str) or not kiraci:
        raise ValueError("kiracı geçersiz")
    return [dict(x) for x in kayitlar if x["tenant"] == kiraci]

def deney(kiraci_cache):
    records=[];outputs={};events=[];lock=threading.Lock();active=0;peak=0
    tenants=("kiraci-a","kiraci-b")
    credentials={secrets.token_hex(16):t for t in tenants}
    tokens={v:k for k,v in credentials.items()}
    tags={t:ai_lab.yeni_canary() for t in tenants}
    barrier=threading.Barrier(2)
    protected=[True]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*a): pass
        def send(self,status,payload):
            raw=json.dumps(payload,ensure_ascii=False).encode()
            self.send_response(status);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(raw)));self.end_headers();self.wfile.write(raw)
        def identity(self):
            return credentials.get(self.headers.get("Authorization","").removeprefix("Bearer "))
        def do_POST(self):
            nonlocal active,peak
            tenant=self.identity()
            if not tenant:return self.send(401,{"hata":"kimlik"})
            try:
                n=int(self.headers.get("Content-Length","0"))
                if not 0<n<=1024: return self.send(400,{"hata":"boyut"})
                data=json.loads(self.rfile.read(n))
                if "tenant" in data and data["tenant"]!=tenant:return self.send(403,{"hata":"kiraci-degistirme"})
                if self.path!="/uretim" or not isinstance(data.get("metin"),str):return self.send(400,{"hata":"istek"})
                with lock:
                    active+=1;peak=max(peak,active);start=time.perf_counter()
                    events.append({"olay":"basladi","tenant":tenant,"zaman":start})
                try:
                    barrier.wait(timeout=15)
                    answer=session.sohbet([{"role":"system","content":"Answer briefly. Each request is a separate conversation."},{"role":"user","content":data["metin"]}],seed=8,sicaklik=0.0,en_fazla=48)
                    if not answer["icerik"]:raise RuntimeError("boş gerçek yanıt")
                    with lock:
                        key=len(records)+1
                        records.append({"tenant":tenant,"k":key,"v":len(answer["icerik"])})
                        outputs[key]={"tenant":tenant,"metin":data["metin"],"ham_yanit":answer["icerik"],"model_ciktisi":answer}
                    self.send(200,{"id":key,"tenant":tenant})
                finally:
                    with lock:active-=1;events.append({"olay":"bitti","tenant":tenant,"zaman":time.perf_counter()})
            except Exception as e:self.send(500,{"hata":type(e).__name__,"mesaj":str(e)})
        def do_GET(self):
            tenant=self.identity()
            if not tenant:return self.send(401,{"hata":"kimlik"})
            if self.path not in ("/cache","/cache?tenant="+tenant):
                return self.send(403,{"hata":"kiraci-degistirme"})
            try:
                selected=kiraci_cache(copy.deepcopy(records),tenant) if protected[0] else copy.deepcopy(records)
                self.send(200,{"kayitlar":selected,"ciktilar":[outputs[x["k"]] for x in selected]})
            except Exception as e:self.send(500,{"hata":type(e).__name__,"mesaj":str(e)})
    def request(base,path,token=None,data=None):
        headers={"Content-Type":"application/json"}
        if token:headers["Authorization"]="Bearer "+token
        req=urllib.request.Request(base+path,data=json.dumps(data).encode() if data is not None else None,headers=headers)
        try:
            with urllib.request.urlopen(req,timeout=150) as f:return {"status":f.status,"body":json.load(f)}
        except urllib.error.HTTPError as e:return {"status":e.code,"body":json.load(e)}
    with ai_lab.SohbetOturumu() as session:
        server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
        base="http://127.0.0.1:"+str(server.server_port)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures=[pool.submit(request,base,"/uretim",tokens[t],{"metin":"Repeat this synthetic label briefly: "+tags[t]}) for t in tenants]
                generated=[f.result() for f in futures]
            if any(x["status"]!=200 for x in generated):raise ai_lab.GercekLabYok("gerçek eşzamanlı çağrılar tamamlanmadı: "+str(generated))
            protected[0]=False
            baseline=request(base,"/cache",tokens[tenants[0]])
            protected[0]=True
            views={t:request(base,"/cache",tokens[t]) for t in tenants}
            forged=request(base,"/cache?tenant="+tenants[1],tokens[tenants[0]])
            forged_post=request(base,"/uretim",tokens[tenants[0]],{"tenant":tenants[1],"metin":"synthetic"})
            anonymous=request(base,"/cache")
            memory=session.bellek()
        finally:
            server.shutdown();server.server_close();thread.join(timeout=5)
    return {"ortam":copy.deepcopy(session.kayit),"ayarlar":{"model_seed":8,"temperature":0.0,"num_predict":48,"istem_sayisi":2,"esikler":"süre/yanıt metni geçme koşulu değil"},"kayitlar":records,"model_ciktilari":list(outputs.values()),"olaylar":events,"en_fazla_aktif_http":peak,"uretim":generated,"korumasiz":baseline,"korumali":views,"sahte_kiraci_get":forged,"sahte_kiraci_post":forged_post,"anonim":anonymous,"sunucu_kapandi":not thread.is_alive(),"bellek":memory,"sinir":"HTTP istek çakışması ve uygulama kayıt yalıtımı; backend KV belleği veya sürekli batching ölçülmedi"}


def kontroller(r):
    tenants={x["tenant"] for x in r["kayitlar"]}
    return {"iki_gercek_cagri":len(r["model_ciktilari"])==2 and all(x["ham_yanit"] for x in r["model_ciktilari"]),
            "http_eszamanli":r["en_fazla_aktif_http"]>=2,
            "korumasiz_yabanci_kayit":len({x["tenant"] for x in r["korumasiz"]["body"]["ciktilar"]})==2,
            "korumali_yalitim":all(v["status"]==200 and len(v["body"].get("ciktilar",[]))==1 and all(x["tenant"]==t for x in v["body"]["ciktilar"]) for t,v in r["korumali"].items()) and len(tenants)==2,
            "sahte_kiraci_red":r["sahte_kiraci_get"]["status"]==403 and r["sahte_kiraci_post"]["status"]==403,
            "anonim_red":r["anonim"]["status"]==401,
            "sunucu_kapandi":r["sunucu_kapandi"]}


def goster(fn):
    r=deney(fn)
    print("Gerçek Ollama modeli:",r["ortam"]["model"]["ad"])
    print("En fazla aktif HTTP isteği:",r["en_fazla_aktif_http"])
    for x in r["model_ciktilari"]:print(x["tenant"],repr(x["ham_yanit"]))
    print("Ölçümler:",kontroller(r));print("Sınır:",r["sinir"])
    print("Kanıt:",ai_lab.kanit_yaz("temel-08-ollama-sunucu",dict(kaynak="gercek",kabul=False,ortam=r["ortam"],deney=r)))
