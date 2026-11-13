"""Real, pinned Elastic APIs for the advanced curriculum; no product emulation.

Each call owns a random index/pipeline/rule and cleans it in finally. Runtime
never installs or starts containers. The bounded input surface is not a general
Dev Tools proxy. Product errors and partial responses are errors, never matches.
"""
import base64
import copy
import json
from pathlib import Path
import re
import time
import urllib.error
import urllib.request
import uuid

try:
    from .elastic_common import ElasticError, field_value
except ImportError:
    from elastic_common import ElasticError, field_value

VERSION = '9.5.5'
ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT/'.deps'/'elastic-lab'
ES = 'http://127.0.0.1:19200'
KB = 'http://127.0.0.1:15601'
MODES = ('ingest', 'eql', 'esql', 'rule')
PROCESSORS = {'rename','set','convert','date','remove','lowercase','uppercase','trim','grok','dissect','json','fail','drop'}

def api(path, body=None, method=None, kibana=False, key=None, missing_ok=False):
    base = KB if kibana else ES
    if not path.startswith('/') or path.startswith('//'):
        raise ElasticError('API yolu yalnız yerel mutlak yol olabilir.')
    try:
        password = (STATE/'password').read_text(encoding='ascii').strip()
    except OSError:
        raise ElasticError('Elastic laboratuvarı yok. README: tools/elastic_lab_setup.py --start; otomatik indirme yapılmaz.') from None
    auth = 'ApiKey '+key if key else 'Basic '+base64.b64encode(('elastic:'+password).encode()).decode()
    headers = {'Authorization': auth, 'Content-Type':'application/json', 'kbn-xsrf':'pafta'}
    data = None if body is None else (body.encode() if isinstance(body,str) else json.dumps(body,ensure_ascii=False,allow_nan=False).encode())
    if isinstance(body,str):
        headers['Content-Type'] = 'application/x-ndjson'
    req = urllib.request.Request(base+path, data, headers, method=method or ('POST' if body is not None else 'GET'))
    try:
        # Ignore machine proxy settings: credentials must stay on this loopback API.
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req,timeout=12) as response:
            raw = response.read(4*1024*1024+1)
            if len(raw)>4*1024*1024:
                raise ElasticError('Elastic yanıtı 4 MiB sınırını aştı.')
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as exc:
        if missing_ok and exc.code == 404:
            return {}
        msg = exc.read(4000).decode('utf-8','replace')
        raise ElasticError(f'Gerçek Elastic HTTP {exc.code}: {msg}') from None
    except OSError as exc:
        raise ElasticError('Yerel Elastic API erişilemiyor; laboratuvarı başlatın: '+str(exc)) from None

def ready(kibana=False):
    info = api('/')
    if info.get('version',{}).get('number') != VERSION:
        raise ElasticError('Bu dersler Elasticsearch '+VERSION+' ile sabitlenmiştir.')
    if kibana:
        status = api('/api/status',kibana=True)
        if status.get('version',{}).get('number') != VERSION:
            raise ElasticError('Kibana sürümü Elasticsearch ile aynı olmalı: '+VERSION)

def options(value):
    if isinstance(value,str):
        if len(value.encode())>1024*1024:
            raise ElasticError('Gerçek laboratuvar girdisi en çok 1 MiB olabilir.')
        try:
            value=json.loads(value)
        except ValueError:
            raise ElasticError('Laboratuvar girdisi JSON olmalı.') from None
    if not isinstance(value,dict) or value.get('backend')!='elastic' or value.get('dil') not in MODES:
        raise ElasticError('backend: elastic ve dil: ingest/eql/esql/rule gerekli.')
    allowed={'backend','dil','mapping','documents','context','exceptions'}
    if set(value)-allowed:
        raise ElasticError('Bilinmeyen laboratuvar seçeneği: '+', '.join(sorted(set(value)-allowed)))
    value=copy.deepcopy(value)
    if not isinstance(value.get('mapping'),dict) or not value['mapping']:
        raise ElasticError('mapping alan türleri nesnesi gerekli.')
    if not isinstance(value.get('documents'),list) or len(value['documents'])>100:
        raise ElasticError('documents 0..100 belge listesi olmalı.')
    ids=[d.get('id') for d in value['documents'] if isinstance(d,dict)]
    if len(ids)!=len(value['documents']) or any(not isinstance(i,str) or not re.fullmatch(r'[\w.-]{1,100}',i) for i in ids) or len(set(ids))!=len(ids):
        raise ElasticError('Her belge benzersiz 1..100 karakter id gerektirir.')
    if len(json.dumps(value,ensure_ascii=False,allow_nan=False).encode())>1024*1024:
        raise ElasticError('Girdi en çok 1 MiB olabilir.')
    value.setdefault('context',{})
    allowed_context={'eql':{'timestamp_field','event_category_field','tiebreaker_field','time_filter'},
                     'rule':{'timeframe_end'},'ingest':set(),'esql':set()}[value['dil']]
    if not isinstance(value['context'],dict) or set(value['context'])-allowed_context:
        raise ElasticError('Bu dil için desteklenmeyen context seçeneği; sessizce yok sayılmaz.')
    if 'exceptions' in value and value['dil']!='rule':
        raise ElasticError('exceptions yalnız gerçek Security rule modunda kullanılabilir.')
    return value

def properties(mapping):
    """Flat ECS field paths -> actual object/nested mapping, no Python indexing."""
    props={}
    for field,raw in sorted(mapping.items(),key=lambda p:p[0].count('.')):
        if not re.fullmatch(r'[A-Za-z@][\w.@-]*',field):
            raise ElasticError('Mapping alan adı geçersiz.')
        spec={'type':raw} if isinstance(raw,str) else copy.deepcopy(raw)
        if not isinstance(spec,dict) or spec.get('type') not in {'keyword','text','integer','long','double','date','boolean','ip','nested'}:
            raise ElasticError('Desteklenmeyen mapping türü: '+field)
        if set(spec)-{'type','index','analyzer','normalizer','ignore_above','null_value','fields'}:
            raise ElasticError('Desteklenmeyen mapping seçeneği: '+field)
        # Çok alanlı eşleme (ör. ECS process.executable.caseless): yalnız normalizer'lı keyword alt alanları.
        for alt,altspec in (spec.get('fields') or {}).items():
            if (not re.fullmatch(r'[A-Za-z]\w*',alt) or not isinstance(altspec,dict)
                    or altspec.get('type')!='keyword' or set(altspec)-{'type','normalizer','ignore_above'}):
                raise ElasticError('Desteklenmeyen alt alan: '+field+'.'+str(alt))
        if spec['type'] in {'integer','long','double'}:
            spec['coerce']=False
        current=props
        for part in field.split('.')[:-1]:
            current=current.setdefault(part,{'properties':{}}).setdefault('properties',{})
        current[field.split('.')[-1]]=spec
    return props

def put_index(index,config):
    props=properties(dict({'id':'keyword'},**config['mapping']))
    api('/'+index,{'settings':{'number_of_shards':1,'number_of_replicas':0,
         'analysis':{'normalizer':{'lowercase':{'type':'custom','filter':['lowercase']}}}},
         'mappings':{'dynamic':'strict','properties':props}},'PUT')

def bulk(index,documents,pipeline=None):
    lines=[]
    for doc in documents:
        lines.extend([json.dumps({'index':{'_id':doc['id']}}),json.dumps(doc,ensure_ascii=False)])
    if not lines:
        return []
    path='/'+index+'/_bulk?refresh=true'+('&pipeline='+pipeline if pipeline else '')
    result=api(path,'\n'.join(lines)+'\n')
    return [dict(id=item['index']['_id'],status=item['index']['status'],
                 error=item['index'].get('error',{}).get('type')) for item in result['items']]

def ensure_complete(response):
    if response.get('timed_out') or response.get('is_partial') or response.get('is_running') or response.get('_shards',{}).get('failed',0):
        raise ElasticError('Gerçek Elastic kısmi/zaman aşımı yanıtı döndürdü; sonuç kesin eşleşme sayılmaz.')

def check_processors(processors):
    if not isinstance(processors,list) or len(processors)>32:
        raise ElasticError('En çok 32 ingest işlemcisi kabul edilir.')
    for processor in processors:
        if not isinstance(processor,dict) or len(processor)!=1 or next(iter(processor)) not in PROCESSORS:
            raise ElasticError('Bu tezgahta desteklenmeyen ingest işlemcisi; script/pipeline/network işlemleri açılmaz.')
        args=next(iter(processor.values()))
        if not isinstance(args,dict):
            raise ElasticError('İşlemci ayarları nesne olmalı.')
        for name in ('field','target_field'):
            fields=args.get(name,[])
            fields=fields if isinstance(fields,list) else [fields]
            if any(not isinstance(f,str) or not re.fullmatch(r'[A-Za-z@][\w.@-]*',f) for f in fields):
                raise ElasticError('İşlemci alanı sabit veri alanı olmalı; _index/_id gibi metadata ve dinamik alan adı kabul edilmez.')
        if 'on_failure' in args:
            check_processors(args['on_failure'])

def evaluate(code,config):
    config=options(config)
    if not isinstance(code,str) or not code.strip() or len(code.encode())>16000 or '\0' in code:
        raise ElasticError('Kod 1..16000 UTF-8 bayt olmalı.')
    mode=config['dil']
    ready(mode=='rule')
    index='pafta-elastic-'+uuid.uuid4().hex
    pipeline=index+'-pipeline'
    created=False
    key=None
    try:
        put_index(index,config)
        created=True
        if mode=='ingest':
            try:
                body=json.loads(code)
            except ValueError:
                raise ElasticError('Ingest kodu processors içeren JSON olmalı.') from None
            if not isinstance(body,dict) or set(body)-{'description','processors','on_failure'} or not isinstance(body.get('processors'),list):
                raise ElasticError('Pipeline yalnız description/processors/on_failure kabul eder.')
            check_processors(body['processors'])
            check_processors(body.get('on_failure',[]))
            api('/_ingest/pipeline/'+pipeline,body,'PUT')
            simulated=api('/_ingest/pipeline/'+pipeline+'/_simulate',{'docs':[{'_source':d} for d in config['documents']]})
            items=bulk(index,config['documents'],pipeline)
            hits=api('/'+index+'/_search',{'size':100,'sort':[{'id':'asc'}]})
            ensure_complete(hits)
            return {'documents':[h['_source'] for h in hits['hits']['hits']],
                    'items':items,'simulation':[{'dropped':True} if d is None or d.get('doc','missing') is None else
                    {'source':d['doc']['_source']} if 'doc' in d else
                    {'error':d.get('error',{}).get('type')} for d in simulated['docs']]}
        docs=config['documents']
        items=bulk(index,docs)
        if any(i['error'] for i in items):
            raise ElasticError('Gerçek bulk mapping hatası: '+json.dumps(items,ensure_ascii=False))
        if mode=='eql':
            ctx=config['context']
            body={'query':code,'size':100,'fetch_size':100,'wait_for_completion_timeout':'8s',
                  'timestamp_field':ctx.get('timestamp_field','@timestamp'),
                  'event_category_field':ctx.get('event_category_field','event.category')}
            if ctx.get('tiebreaker_field'):
                body['tiebreaker_field']=ctx['tiebreaker_field']
            if 'time_filter' in ctx:
                window=ctx['time_filter']
                if (not isinstance(window,dict) or set(window)-{'field','gt','gte','lt','lte'}
                        or not set(window)&{'gt','gte','lt','lte'}):
                    raise ElasticError('time_filter field ve gt/gte/lt/lte sınırları içermeli.')
                field=window.get('field','@timestamp')
                spec=config['mapping'].get(field)
                if (spec.get('type') if isinstance(spec,dict) else spec)!='date':
                    raise ElasticError('time_filter alanı gerçek date mapping gerektirir.')
                body['filter']={'range':{field:{k:v for k,v in window.items() if k!='field'}}}
            response=api('/'+index+'/_eql/search',body)
            if response.get('id'):
                api('/_eql/search/'+response['id'],method='DELETE',missing_ok=True)
            ensure_complete(response)
            hits=response['hits']
            matches=([[e['_id'] for e in s['events'] if not e.get('missing')]
                       for s in hits['sequences']] if 'sequences' in hits else [e['_id'] for e in hits.get('events',[])])
            return {'ids':matches}
        if mode=='esql':
            # Index privileges enforce isolation even if query syntax contains a subquery.
            grant=api('/_security/api_key',{'name':index,'expiration':'2m','role_descriptors':{
                'lesson':{'indices':[{'names':[index],'privileges':['read','view_index_metadata']}]}}})
            key=grant
            query=re.sub(r'\bFROM\s+pafta\b','FROM '+index,code,count=1,flags=re.I)
            if query==code:
                raise ElasticError('ES|QL kaynağı FROM pafta olmalı; bu ad yalnız dersin geçici indeksine bağlanır.')
            response=api('/_query',{'query':query,'columnar':False},key=grant['encoded'])
            ensure_complete(response)
            return {'columns':[c['name'] for c in response['columns']],'values':response['values']}
        return rule(code,index,config)
    finally:
        if key:
            api('/_security/api_key',{'ids':[key['id']]},'DELETE')
        if mode=='ingest':
            api('/_ingest/pipeline/'+pipeline,method='DELETE',missing_ok=True)
        if created:
            api('/'+index,method='DELETE',missing_ok=True)

def rule(code,index,config):
    """Persist a disabled real rule, preview it with native engine, then delete it.
    Scheduled acceptance is a separate test: preview must never be called an alert.
    """
    try:
        body=json.loads(code)
    except ValueError:
        raise ElasticError('Kural kodu gerçek create-rule JSON alanları olmalı.') from None
    allowed={'type','language','query','interval','from','to','threshold','filters','risk_score','severity','description','name'}
    if not isinstance(body,dict) or set(body)-allowed:
        raise ElasticError('Destek dışı kural alanı; indeks/kimlik/aksiyon tezgahta sabittir.')
    if body.get('type') not in ('query','eql','threshold'):
        raise ElasticError('Kural türü query/eql/threshold olmalı.')
    # Keep schedules/lookbacks bounded; real API still validates all rule semantics.
    if not re.fullmatch(r'[1-9][0-9]?m',body.get('interval','1m')):
        raise ElasticError('Laboratuvar interval 1m..99m olmalı.')
    payload=dict(body,index=[index],enabled=False,name=body.get('name','Pafta geçici kural'),
                 description=body.get('description','Pafta yerel öğretim'),risk_score=body.get('risk_score',21),
                 severity=body.get('severity','low'),interval=body.get('interval','1m'))
    saved=None
    exception_list=None
    try:
        api('/api/detection_engine/index',{},kibana=True)
        if config.get('exceptions'):
            exception_list=api('/api/exception_lists',{'list_id':index,'name':'Pafta öğretim istisnası',
                'description':'Geçici ders listesi','type':'detection','namespace_type':'single'},kibana=True)
            for entry in config['exceptions']:
                api('/api/exception_lists/items',{'list_id':index,'name':'Pafta istisna öğesi',
                    'description':'Geçici ders öğesi','type':'simple','namespace_type':'single',
                    'entries':entry},kibana=True)
            payload['exceptions_list']=[{'id':exception_list['id'],'list_id':index,'type':'detection','namespace_type':'single'}]
        saved=api('/api/detection_engine/rules',payload,kibana=True)
        preview=dict(payload,invocationCount=1,timeframeEnd=config['context'].get('timeframe_end','2026-01-01T00:10:00.000Z'))
        preview.pop('enabled',None)
        result=api('/api/detection_engine/rules/preview',preview,kibana=True)
        errors=[e for log in result.get('logs',[]) for e in log.get('errors',[])]
        if errors or result.get('isAborted'):
            raise ElasticError('Gerçek kural önizlemesi tamamlanamadı: '+json.dumps(errors,ensure_ascii=False))
        # 9.5.5 preview writes temporary preview alerts, not operational alerts.
        # Scope every read/delete to the returned unique previewId, never all previews.
        preview_id=result['previewId']
        preview_index='.internal.preview.alerts-security.alerts-default-*'
        api('/'+preview_index+'/_refresh')
        query={'term':{'kibana.alert.rule.uuid':preview_id}}
        response=api('/'+preview_index+'/_search',{'size':100,'query':query})
        ensure_complete(response)
        alerts=[]
        for hit in response['hits']['hits']:
            source=hit['_source']
            threshold=source.get('kibana.alert.threshold_result',{})
            alerts.append({'ids':[] if threshold else sorted({a['id'] for a in source.get('kibana.alert.ancestors',[]) if a.get('type')=='event'}),
                           'count':threshold.get('count'), 'groups':threshold.get('terms',[])})
        api('/'+preview_index+'/_delete_by_query?refresh=true',{'query':query})
        alerts.sort(key=lambda a:(json.dumps(a['groups'],sort_keys=True),a['ids'],a['count'] or 0))
        return {'rule':{k:saved.get(k) for k in ('type','language','query','interval','from','to','threshold','enabled') if k in saved},
                'preview_alerts':alerts,'preview_count':len(alerts)}
    finally:
        if saved:
            api('/api/detection_engine/rules?id='+saved['id'],method='DELETE',kibana=True)
        if exception_list:
            api('/api/exception_lists?id='+exception_list['id']+'&namespace_type=single',method='DELETE',kibana=True)

def run(code,stdin):
    config=options(stdin)
    result=evaluate(code,config)
    if config['dil']=='eql':
        lines=[' -> '.join(i) if isinstance(i,list) else i for i in result['ids']]
        out='\n'.join(lines)+ ('\n' if lines else '')
        return {'status':'ok','error':None,'segs':[['out',out]],'elastic_ids':result['ids'],
                'elastic_dialect':'eql','elastic_backend':'Elasticsearch '+VERSION,'tablolar':[]}
    if config['dil']=='esql':
        out=json.dumps(result,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n'
        tables=[{'satir':1,'sutunlar':result['columns'],'satirlar':result['values']}]
    else:
        out=json.dumps(result,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n'
        tables=[]
    return {'status':'ok','error':None,'segs':[['out',out]],'tablolar':tables,'elastic_native':True,
            'elastic_backend':'Elasticsearch/Kibana '+VERSION}

def test_helpers(code,stdin):
    config=options(stdin)
    initial=evaluate(code,config)
    def merged(value):
        return dict(copy.deepcopy(config),**({'documents':value} if isinstance(value,list) else value or {}))
    def result(value=None):
        return copy.deepcopy(initial) if value is None else evaluate(code,merged(value))
    def ids(value=None):
        return result(value)['ids']
    return {'src':code,'korpus':copy.deepcopy(config),'sonuc':result,'eslesenler':ids,
            'alan':field_value,
            'referans':lambda query,veri=None,dil=None:evaluate(query,dict(merged(veri),**({'dil':dil} if dil else {})))}
