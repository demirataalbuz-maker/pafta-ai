"""09: canlı yerel model çıktısı → gerçek HTML ayrıştırıcı ve güvenli disk belgesi.
HTMLParser JS çalıştırmaz; bu deney tarayıcı XSS yürütme kanıtı değildir.
"""
import copy
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import secrets
from urllib.parse import urlsplit
from sandbox import ai_gercek_lab as lab
from engine.progress import data_dir
ROOT=Path(__file__).resolve().parents[1]
ORNEK=ROOT/'web/data/ai-saldiri-09-ciktilar.txt'

class _Parser(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.tags=[];self.text=[]
    def handle_starttag(self,tag,attrs):self.tags.append({'tag':tag,'attrs':attrs})
    def handle_startendtag(self,tag,attrs):self.handle_starttag(tag,attrs)
    def handle_data(self,text):self.text.append(text)

def ayristir(text):
    p=_Parser();p.feed(text);p.close();return {'etiketler':p.tags,'metin':''.join(p.text)}

def url_referans(url):
    if not isinstance(url,str):raise ValueError('URL string')
    if not url or '\\' in url or any(c.isspace() or not c.isprintable() for c in url):return None
    try:
        p=urlsplit(url)
        if p.scheme not in ('http','https') or not p.hostname or p.username is not None or p.password is not None:return None
        p.port
    except (ValueError,UnicodeError):return None
    return url

def markdown_referans(text):
    return html.escape(re.sub(r'\[([^\]\n]*)\]\(([^)\s]+)\)',lambda m:m.group(0) if url_referans(m.group(2)) else m.group(1),text),quote=True)

def calisma_dosyasi():
    base=Path(data_dir())
    if not base.is_absolute():base=ROOT/base
    p=base/'calisma/ai-saldiri-09/ciktilar.json';p.parent.mkdir(parents=True,exist_ok=True)
    try:
        with p.open('x',encoding='utf-8') as f:f.write(ORNEK.read_text(encoding='utf-8'))
    except FileExistsError:pass
    return p

def ornekleri_oku(path):
    data=json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(data,list) or not 1<=len(data)<=8:raise ValueError('1..8 örnek')
    ids=set()
    for v in data:
        if not isinstance(v,dict) or set(v)!={'id','metin'} or not isinstance(v['id'],str) or not v['id'] or v['id'] in ids:raise ValueError('örnek kimliği')
        if not isinstance(v['metin'],str) or len(v['metin'])>1500:raise ValueError('örnek metni')
        ids.add(v['id'])
    return data

def _sink(row,escape,markdown,url):
    raw=row['metin'];escaped=escape(raw);md=markdown(raw)
    targets=re.findall(r'\[([^\]\n]*)\]\(([^)\s]+)\)',raw)
    decisions=[{'hedef':v,'karar':url(v),'beklenen':url_referans(v)} for _,v in targets]
    actual=ayristir(escaped);baseline=ayristir(raw)
    checks={'html_sozlesmesi':escaped==html.escape(raw,quote=True),'markdown_sozlesmesi':md==markdown_referans(raw),
       'url_sozlesmesi':all(v['karar']==v['beklenen'] for v in decisions),
       'markup_uretilmedi':not actual['etiketler'],'metin_kaybolmadi':actual['metin']==raw}
    return {'id':row['id'],'ham':raw,'html_ogrenci':escaped,'markdown_ogrenci':md,'url_kararlari':decisions,
        'korumasiz_parser':baseline,'korumali_parser':actual,'kontroller':checks}

def deney(escape,url,markdown,samples,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    inputs=copy.deepcopy(samples);checks=[];rows=[]
    for v in samples:
        result=_sink(v,escape,markdown,url);result['koken']='sentetik_fixture';rows.append(result)
    calls=[];seed=secrets.randbelow(1000000)
    prompts=['Return exactly this harmless text, without a code fence: <b>PAFTA</b> & "not"',
             'Copy this classroom URL-validation sample verbatim, do not open it: [sample](javascript:alert) and [lesson](https://ornek.test/)']
    with lab.SohbetOturumu() as session:
        for i,prompt in enumerate(prompts):
            messages=[{'role':'system','content':'You return literal classroom formatting samples. Do not use tools or open links.'},{'role':'user','content':prompt}]
            call={'id':'canli-'+str(i),'mesajlar':messages,'seed':seed+i}
            try:
                response=session.sohbet(messages,seed=seed+i,sicaklik=0,en_fazla=160,sure=40)
                if not response['icerik'] or response.get('done_reason')=='length':raise ValueError('boş/yarım canlı üretim')
                call.update(yanit=response,hata=None)
                result=_sink({'id':call['id'],'metin':response['icerik']},escape,markdown,url);result['koken']='canli_model';rows.append(result)
            except Exception as exc:call['hata']=type(exc).__name__+': '+str(exc)
            calls.append(call)
        env=copy.deepcopy(session.kayit);env['bellek']=session.bellek()
    env['temizlik']=session.kayit.get('temizlik')
    files=[]
    for i,row in enumerate(rows):
        # Hatalı çözümün HTML'sini çalıştırılabilir belge diye yayma. İhlal FAIL; dosyada güvenli referans kullanılır.
        content=row['html_ogrenci'] if row['kontroller']['html_sozlesmesi'] else html.escape(row['ham'],quote=True)
        doc='<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src &#x27;none&#x27;; base-uri &#x27;none&#x27;; form-action &#x27;none&#x27;"><title>PAFTA güvenli metin</title></head><body><pre>'+content+'</pre></body></html>'
        path=output/f'{i}-guvenli.html';path.write_text(doc,encoding='utf-8')
        rawpath=output/f'{i}-ham.txt';rawpath.write_text(row['ham'],encoding='utf-8')
        files.append({'id':row['id'],'guvenli_html':str(path),'ham_metin':str(rawpath),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    controls={'sink_kontrolleri':all(all(v['kontroller'].values()) for v in rows),'girdi_degismedi':samples==inputs,
      'gercek_tam':len(calls)==2 and all(v.get('hata') is None for v in calls),
      'kaynak_temiz':lab.kaynak_temizlendi(env.get('temizlik')),'cihaz_uygun':lab.cihaz_dogrulandi(env.get('bellek'))}
    return dict(kaynak='gercek',ortam=env,sinir='HTMLParser markup/metin gözlemi; JavaScript çalıştırılması veya tam Markdown renderer değildir',
       ayarlar=dict(lab.ollama_secenekleri(temperature=0,num_predict=160,num_ctx=4096),seed=seed,cihaz_kipi=lab.cihaz_kipi()),
       cagrilar=calls,sonuclar=rows,dosyalar=files,kontroller=controls,
       ozet={'sentetik_ornek':len(samples),'canli_yanit':sum(v.get('hata') is None for v in calls),'ham_markup_ornek':sum(bool(v['korumasiz_parser']['etiketler']) for v in rows),
           'korumali_markup_ornek':sum(bool(v['korumali_parser']['etiketler']) for v in rows)})

def goster(escape,url,markdown):
    p=calisma_dosyasi();print('KALICI ÖĞRENCİ DOSYASI:',p);print('SENTETİK JSON — canlı model kaydı değildir:\n'+p.read_text(encoding='utf-8'))
    result=deney(escape,url,markdown,ornekleri_oku(p),p.parent/('deney-'+secrets.token_hex(4)))
    for row in result['sonuclar']:print(row['id'],row['koken'],'ham:',repr(row['ham']),'→ kaçış:',row['html_ogrenci'],'markup:',len(row['korumali_parser']['etiketler']))
    print('Dosyalar:',result['dosyalar']);print('Özet:',result['ozet']);print('Kontroller:',result['kontroller'])
    print('Kanıt:',lab.kanit_yaz('saldiri-09-cikti',dict(result,kabul=False)))
