"""34: actual structured chat and raw prompt inference; preview is not native template."""
import copy,hashlib,json,secrets,time
from pathlib import Path
from engine.progress import data_dir
from sandbox import ai_gercek_lab as lab
ROOT=Path(__file__).resolve().parents[1]
ORNEK=ROOT/'web/data/ai-saldiri-34-mesajlar.txt'
def calisma_dosyasi():
    root=Path(data_dir());root=root if root.is_absolute() else ROOT/root
    p=root/'calisma/ai-saldiri-34/mesajlar.json';p.parent.mkdir(parents=True,exist_ok=True)
    if not p.exists():
        try:
            with p.open('x',encoding='utf-8') as f:f.write(ORNEK.read_text(encoding='utf-8'))
        except FileExistsError:pass
    return p

def render_ref(messages,kind,escape=True):
    chunks=[]
    for v in messages:
        role,text=v['rol'],v['icerik']
        if kind=='chatml':
            if escape:text=text.replace('<|im_start|>','< |im_start|>').replace('<|im_end|>','< |im_end|>')
            chunks.append('<|im_start|>'+role+'\n'+text+'<|im_end|>\n')
        else:
            if escape:text=text.replace('[','[ ')
            chunks.append('['+role.upper()+']\n'+text+'[/'+role.upper()+']\n')
    return ''.join(chunks)
def report_ref(examples):
    return [dict(id=v['id'],roller=[m['rol'] for m in v['mesajlar']],chatml_sha256=hashlib.sha256(render_ref(v['mesajlar'],'chatml').encode()).hexdigest(),kose_sha256=hashlib.sha256(render_ref(v['mesajlar'],'kose').encode()).hexdigest()) for v in sorted(examples,key=lambda x:x['id'])]
def _raw(session,prompt,seed):
    body=dict(model=session.model,prompt=prompt,raw=True,stream=False,options=lab.ollama_secenekleri(temperature=.1,seed=seed,num_predict=64,num_ctx=4096))
    if session.dusunme:body['think']=False
    if not session._once_yuklu:body['keep_alive']='5m'
    start=time.perf_counter();response=lab._istek(session.adres,'/api/generate',body,sure=60)
    # Empty text or a budget stop can be a genuine raw-template observation, not a fixed-text verdict.
    valid=response.get('done') is True and isinstance(response.get('response'),str) and type(response.get('eval_count')) is int and response['eval_count']>=0
    if not valid:raise lab.GercekLabYok('Gerçek rawgenerate yanıtı tamamlanmış inference kaydı değil')
    return dict(istek=body,yanit=response,sure_ms=round((time.perf_counter()-start)*1000),prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(),token_idleri_sunuldu=isinstance(response.get('context'),list))
def deney(summary,render,report,document,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True);data=json.loads(Path(document).read_text(encoding='utf-8'))
    if set(data)!={'ornekler'} or not isinstance(data['ornekler'],list) or not 1<=len(data['ornekler'])<=3:raise ValueError('Mesaj örnekleri1..3liste olmalı')
    marker=lab.yeni_canary();examples=json.loads(json.dumps(data['ornekler'],ensure_ascii=False).replace('{{CANARY}}',marker));checks_local=True;calls=[];seed=secrets.randbelow(1000000);hashes=report(copy.deepcopy(examples));gold_hashes=report_ref(examples)
    with lab.SohbetOturumu() as live:
        info=lab._istek(live.adres,'/api/show',{'model':live.model});template=info.get('template')
        if not isinstance(template,str) or not template:raise lab.GercekLabYok('Kurulu model native template bilgisi yok')
        (output/'ollama-native-template.txt').write_text(template,encoding='utf-8');template_info=dict(sha256=hashlib.sha256(template.encode()).hexdigest(),icerik=template,capabilities=info.get('capabilities'),chatml_marker_ailesi='<|im_start|>' in template)
        for example in examples:
            messages=example['mesajlar'];expected=dict(roller=[v['rol'] for v in messages],mesaj_sayisi=len(messages),karakter=sum(len(v['icerik']) for v in messages));got=summary(copy.deepcopy(messages));checks_local &= got==expected
            converted=[dict(role=role,content=v['icerik']) for role,v in zip(got['roller'],messages)];row=dict(id=example['id'],mesajlar=messages,ogrenci_akis_ozeti=got,yapi_gercek_mesajlar=converted,raw_deneyleri=[],hata=None)
            try:
                structured=live.sohbet(converted,seed=seed,sicaklik=.1,en_fazla=64,sure=60);row['structured_yanit']=structured
                if not isinstance(structured['icerik'],str):raise lab.GercekLabYok('Gerçek structuredchat yanıtı yok')
                for kind in ('chatml','kose'):
                    preview=render(copy.deepcopy(messages),kind);checks_local &= preview==render_ref(messages,kind)
                    suffix='<|im_start|>assistant\n' if kind=='chatml' else '[ASSISTANT]\n';raw=_raw(live,preview+suffix,seed)
                    row['raw_deneyleri'].append(dict(tur=kind,preview=preview,preview_sha256=hashlib.sha256(preview.encode()).hexdigest(),asistan_oneki=suffix,icerik_model_sablonu_degildir=True if kind=='kose' else not template_info['chatml_marker_ailesi'],**raw))
                unsafe=render_ref(messages,'chatml',escape=False)+'<|im_start|>assistant\n';row['raw_deneyleri'].append(dict(tur='chatml-kacissiz-karsilastirma',**_raw(live,unsafe,seed)))
                row['canary_gozlemi']=dict(structured=marker in structured['icerik'],raw={v['tur']:marker in v['yanit']['response'] for v in row['raw_deneyleri']})
            except Exception as exc:
                row['hata']=type(exc).__name__+': '+str(exc)
                if hasattr(exc,'read'):
                    try:row['hata_govdesi']=exc.read(16000).decode('utf-8',errors='replace')
                    except Exception:pass
            calls.append(row)
        env=copy.deepcopy(live.kayit);env['bellek']=live.bellek()
    env['temizlik']=live.kayit.get('temizlik')
    checks=dict(gercek_girdide_rol_render=bool(checks_local),render_SHA_raporu=hashes==gold_hashes,gercek_structured_ve_raw_tam=len(calls)==len(examples) and all(v['hata'] is None and len(v['raw_deneyleri'])==3 and 'structured_yanit' in v for v in calls),raw_girdi_hashi_dogru=all(v['prompt_sha256']==hashlib.sha256(v['istek']['prompt'].encode()).hexdigest() for c in calls for v in c['raw_deneyleri']),kaynak_temiz=lab.kaynak_temizlendi(env.get('temizlik')),cihaz_uygun=lab.cihaz_dogrulandi(env.get('bellek')))
    return dict(kaynak='gercek',ortam=env,ayarlar=dict(lab.ollama_secenekleri(temperature=.1,num_predict=64,num_ctx=4096),seed=seed),girdi=examples,canary=marker,native_template=template_info,ogrenci_SHA_raporu=hashes,cagrilar=calls,kontroller=checks,sinir='ChatML/kose dersönizlemesidir,modelnativejinjatemplateininbirebiruygulaması değil. Koseplaintextbaselinedır. Structuredchat servernative-template kullanır;rawgenerate templatei bypasseder ve kaydedilenpromptu aynen işler. TokenIDleri yalnız server gerçektencontextsunarsakaydedilir;uydurulmaz. Budgetlength/EOS/cevapmetni gözlemdir,sabitcevap veya saldırıbaşarısıPASSşartı değil;HTTPeksikçağrı hatasıFAIL.')
def goster(summary,render,report):
    p=calisma_dosyasi();print('KALICI SENTETİK MESAJLAR:',p);print(p.read_text(encoding='utf-8'));r=deney(summary,render,report,p,p.parent/('deney-'+secrets.token_hex(4)))
    print('Native template SHA:',r['native_template']['sha256'])
    for c in r['cagrilar']:print(c['id'],c['hata'],c.get('canary_gozlemi'),[(v['tur'],v['yanit'].get('prompt_eval_count'),v['yanit'].get('eval_count'),v['yanit'].get('done_reason'),v['token_idleri_sunuldu']) for v in c['raw_deneyleri']])
    print('Kontroller:',r['kontroller']);print('Kanıt:',lab.kanit_yaz('saldiri-34-template',dict(r,kabul=False)))
