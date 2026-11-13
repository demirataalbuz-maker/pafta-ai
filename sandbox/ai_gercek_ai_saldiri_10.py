"""10: canlı model ham JSON'u -> katı sınır -> gerçek SQLite iş/inceleme kuyruğu."""
import copy
import hashlib
import json
import math
from pathlib import Path
import secrets
import sqlite3
from sandbox import ai_gercek_lab as lab
from engine.progress import data_dir
ROOT=Path(__file__).resolve().parents[1]
ORNEK=ROOT/'web/data/ai-saldiri-10-json.txt'

def calisma_dosyasi():
    base=Path(data_dir())
    if not base.is_absolute():base=ROOT/base
    p=base/'calisma/ai-saldiri-10/kararlar.json';p.parent.mkdir(parents=True,exist_ok=True)
    try:
        with p.open('x',encoding='utf-8') as f:f.write(ORNEK.read_text(encoding='utf-8'))
    except FileExistsError:pass
    return p

def ornekleri_oku(path):
    rows=json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(rows,list) or not 1<=len(rows)<=10:raise ValueError('1..10 vaka')
    ids=set()
    for v in rows:
        if not isinstance(v,dict) or set(v)!={'id','ham'} or not isinstance(v['id'],str) or not v['id'] or v['id'] in ids or not isinstance(v['ham'],str) or len(v['ham'])>2000:raise ValueError('vaka şeması')
        ids.add(v['id'])
    return rows

def pipeline_referans(raw):
    def pairs(values):
        result={}
        for key,value in values:
            if key in result:raise ValueError('yinelenen anahtar')
            result[key]=value
        return result
    def bad(value):raise ValueError('JSON özel sayısı')
    if not isinstance(raw,str):raise ValueError('ham string')
    d=json.loads(raw,object_pairs_hook=pairs,parse_constant=bad)
    if not isinstance(d,dict) or set(d)!={'eylem','metin','guvence'}:raise ValueError('şema')
    if not isinstance(d['eylem'],str) or d['eylem'] not in ('ozetle','cevir','yoksay'):raise ValueError('eylem')
    if not isinstance(d['metin'],str) or not 1<=len(d['metin'])<=120:raise ValueError('metin')
    score=d['guvence']
    if type(score) not in (int,float) or not math.isfinite(score) or not 0<=score<=1:raise ValueError('güvence')
    return {'komut':'INCELE','icerik':''} if score<.75 else {'komut':{'ozetle':'OZET','cevir':'CEVIR','yoksay':'YOKSAY'}[d['eylem']],'icerik':d['metin']}

def _pipeline(raw,parser,validator,builder):
    parsed=parser(raw);before=copy.deepcopy(parsed);checked=validator(parsed)
    if parsed!=before:raise RuntimeError('şema girdisi değişti')
    saved=copy.deepcopy(checked);command=builder(checked)
    if checked!=saved:raise RuntimeError('komut girdisi değişti')
    return command

def _isle(con,case,parser,validator,builder):
    start=con.total_changes
    try:gold=pipeline_referans(case['ham']);expected='izinli'
    except ValueError:gold=None;expected='red'
    command=None;error=None
    try:
        command=_pipeline(case['ham'],parser,validator,builder)
        if not isinstance(command,dict) or set(command)!={'komut','icerik'} or command['komut'] not in ('OZET','CEVIR','YOKSAY','INCELE'):raise RuntimeError('iç komut allowlist ihlali')
        if command['komut']=='INCELE':con.execute('INSERT INTO inceleme(vaka,icerik) VALUES(?,?)',(case['id'],command['icerik']))
        else:con.execute('INSERT INTO isler(vaka,komut,icerik) VALUES(?,?,?)',(case['id'],command['komut'],command['icerik']))
        con.commit();status='izinli'
    except ValueError as exc:status='red';error=str(exc)
    delta=con.total_changes-start
    return dict(id=case['id'],koken=case.get('koken','sentetik_fixture'),ham=case['ham'],durum=status,komut=command,hata=error,
        beklenen=gold,pipeline_ayni=status==expected and command==gold,db_degisim=delta,
        etki_dogru=delta==(0 if gold is None else 1))

def deney(parser,validator,builder,samples,path):
    original=copy.deepcopy(samples);calls=[];base=secrets.randbelow(1000000)
    with lab.SohbetOturumu() as session:
        prompts=['Return only JSON with exactly eylem=ozetle, metin=PAFTA local note, guvence=0.9. No explanation or fences.',
                 'Return this literal classroom JSON example exactly, no explanation: {"eylem":"yoksay","eylem":"cevir","metin":"PAFTA","guvence":1}']
        for i,p in enumerate(prompts):
            messages=[{'role':'system','content':'You provide harmless classroom JSON samples; no tools or side effects.'},{'role':'user','content':p}]
            row={'id':'model-'+str(i),'mesajlar':messages,'seed':base+i}
            try:
                response=session.sohbet(messages,seed=base+i,sicaklik=0,en_fazla=160,sure=40)
                if not response['icerik'] or response.get('done_reason')=='length':raise ValueError('boş/yarım model üretimi')
                row.update(yanit=response,hata=None)
            except Exception as exc:row['hata']=type(exc).__name__+': '+str(exc)
            calls.append(row)
        env=copy.deepcopy(session.kayit);env['bellek']=session.bellek()
    env['temizlik']=session.kayit.get('temizlik')
    path=Path(path);con=sqlite3.connect(path)
    try:
        con.execute('CREATE TABLE isler(vaka TEXT PRIMARY KEY,komut TEXT,icerik TEXT)')
        con.execute('CREATE TABLE inceleme(vaka TEXT PRIMARY KEY,icerik TEXT)')
        rows=[_isle(con,dict(v,koken='sentetik_fixture'),parser,validator,builder) for v in samples]
        for v in calls:
            if v.get('hata') is None:rows.append(_isle(con,dict(id=v['id'],ham=v['yanit']['icerik'],koken='canli_model'),parser,validator,builder))
    finally:con.close()
    # Yeni SQLite bağlantısı: diskteki gerçek kuyruğu ölç.
    con=sqlite3.connect(path)
    try:
        jobs=con.execute('SELECT vaka,komut,icerik FROM isler ORDER BY vaka').fetchall()
        reviews=con.execute('SELECT vaka,icerik FROM inceleme ORDER BY vaka').fetchall()
    finally:con.close()
    checks={'pipeline_dogru':all(v['pipeline_ayni'] for v in rows),'disk_etkisi_dogru':all(v['etki_dogru'] for v in rows),
        'red_kuyruga_girmedi':all(v['db_degisim']==0 for v in rows if v['beklenen'] is None),
        'mesru_akis_var':bool(jobs),'inceleme_iceriksiz':bool(reviews) and all(v[1]=='' for v in reviews),
        'gercek_tam':len(calls)==2 and all(v.get('hata') is None for v in calls),'girdi_degismedi':samples==original,
        'kaynak_temiz':lab.kaynak_temizlendi(env.get('temizlik')),'cihaz_uygun':lab.cihaz_dogrulandi(env.get('bellek'))}
    return dict(kaynak='gercek',ortam=env,sqlite_surumu=sqlite3.sqlite_version,veri_kokeni='sentetik örnekler + canlı model JSON çıktısı',
        ayarlar=dict(lab.ollama_secenekleri(temperature=0,num_predict=160,num_ctx=4096),seed=base,cihaz_kipi=lab.cihaz_kipi()),
        cagrilar=calls,sonuclar=rows,is_kuyrugu=jobs,inceleme_kuyrugu=reviews,db_dosyasi=str(path),db_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),kontroller=checks,
        ozet={'red':sum(v['durum']=='red' for v in rows),'is':len(jobs),'inceleme':len(reviews),'canli_yanit':sum(v.get('hata') is None for v in calls)})

def goster(parser,validator,builder):
    p=calisma_dosyasi();print('KALICI ÖĞRENCİ DOSYASI:',p);print('SENTETİK ÖRNEKLER:\n'+p.read_text(encoding='utf-8'))
    result=deney(parser,validator,builder,ornekleri_oku(p),p.parent/('kuyruk-'+secrets.token_hex(4)+'.sqlite3'))
    for v in result['sonuclar']:print(v['id'],v['koken'],repr(v['ham']),'→',v['durum'],v['komut'],'DB değişim',v['db_degisim'])
    print('GERÇEK SQLite kuyruğu:',result['db_dosyasi']);print('İşler:',result['is_kuyrugu'],'İnceleme:',result['inceleme_kuyrugu']);print('Kontroller:',result['kontroller'])
    print('Kanıt:',lab.kanit_yaz('saldiri-10-json',dict(result,kabul=False)))
