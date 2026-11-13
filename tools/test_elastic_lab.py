"""Acceptance against installed Elastic 9.5.5 Basic, not mocks.

--scheduled additionally waits for actual Kibana Task Manager executions and
reads operational alerts. The normal suite never calls previews 'real alerts'.
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sandbox import elastic_lab as lab
from sandbox.elastic_common import ElasticError
from sandbox.elastic_engine import evaluate as local
from engine.lessons import Library

class NativeTests(unittest.TestCase):
    def test_unsupported_context_is_explicit_error(self):
        with self.assertRaises(ElasticError):
            lab.options({'backend':'elastic','dil':'eql','mapping':{'n':'long'},'documents':[],
                         'context':{'sort':[['n','desc']]}})

    def test_existing_eql_predictions_against_product(self):
        library=Library()
        checked=[]
        for lid in library.outline('elastic')['order']:
            for step in library.lesson('elastic',lid)['steps']:
                if step['kind']!='tahmin':
                    continue
                cfg=json.loads(step['stdin'])
                if cfg['dil']=='eql' and not cfg.get('backend'):
                    with self.subTest(lesson=lid):
                        self.assertEqual(local(step['code'],cfg),lab.evaluate(step['code'],dict(cfg,backend='elastic'))['ids'])
                        checked.append(lid)
                        print(lid+': yerel EQL == gerçek Elasticsearch',flush=True)
        self.assertEqual(checked,[f'el{i}' for i in range(13,19)])

    def test_existing_eql_tasks_against_product(self):
        # Görev çözümü ve başlangıcı da aynı corpus/mapping ile gerçek motorda aynı sonucu vermeli;
        # yerel motorun reddettiği sorgu gerçek motorda da hata olmalı (sessiz taklit yok).
        library=Library()
        checked=[]
        for lid in [f'el{i}' for i in range(13,19)]:
            for step in library.lesson('elastic',lid)['steps']:
                if step['kind']!='gorev':
                    continue
                cfg=json.loads(step['stdin'])
                self.assertEqual((cfg['dil'],cfg.get('backend')),('eql',None),(lid,step['title']))
                for kind in ('solution','starter'):
                    with self.subTest(lesson=lid,task=step['title'],kind=kind):
                        try:
                            yerel=local(step[kind],cfg)
                        except ElasticError:
                            yerel=None
                        try:
                            gercek=lab.evaluate(step[kind],dict(cfg,backend='elastic'))['ids']
                        except ElasticError:
                            gercek=None
                        self.assertEqual(yerel,gercek)
                        checked.append((lid,kind))
                        print(f'{lid} {kind} «{step["title"][:32]}»: yerel EQL == gerçek Elasticsearch'
                              +(' (ikisi de hata)' if gercek is None else ''),flush=True)
        self.assertEqual(len(checked),24)

    def test_eql_time_window_is_native_range_filter(self):
        cfg={'backend':'elastic','dil':'eql','mapping':{'@timestamp':'date','event.category':'keyword'},
             'documents':[{'id':str(i),'@timestamp':f'2026-01-01T00:00:00.00{i}Z','event.category':'process'} for i in range(3)],
             'context':{'time_filter':{'gte':'2026-01-01T00:00:00.001Z','lt':'2026-01-01T00:00:00.002Z'}}}
        self.assertEqual(lab.evaluate('process where true',cfg)['ids'],['1'])

    def test_native_error_cleanup_and_no_fallback(self):
        cfg={'backend':'elastic','dil':'eql','mapping':{'@timestamp':'date','event.category':'keyword'},
             'documents':[{'id':'a','@timestamp':'2026-01-01T00:00:00Z','event.category':'process'}]}
        created=[]
        real_put=lab.put_index
        def observe(index,config):
            created.append(index)
            return real_put(index,config)
        with patch.object(lab,'put_index',side_effect=observe):
            with self.assertRaisesRegex(ElasticError,'Gerçek Elastic HTTP 400'):
                lab.evaluate('process where noSuchFunction(123)',cfg)
        self.assertEqual(len(created),1)
        self.assertEqual(lab.api('/'+created[0]+'/_count',missing_ok=True),{})

    def test_simulation_success_is_not_bulk_success(self):
        cfg={'backend':'elastic','dil':'ingest','mapping':{'n':'integer'},'documents':[{'id':'a'}]}
        result=lab.evaluate(json.dumps({'processors':[{'set':{'field':'n','value':'7'}}]}),cfg)
        self.assertEqual(result['simulation'][0]['source']['n'],'7')
        self.assertEqual(result['documents'],[])
        self.assertEqual(result['items'][0]['status'],400)
        self.assertIsNotNone(result['items'][0]['error'])

    def test_esql_scoped_key_cannot_read_other_index(self):
        cfg={'backend':'elastic','dil':'esql','mapping':{'n':'long'},'documents':[{'id':'a','n':1}]}
        self.assertEqual(lab.evaluate('FROM pafta | STATS n = COUNT(*)',cfg)['values'],[[1]])
        with self.assertRaises(ElasticError):
            lab.evaluate('FROM pafta, .security-7 | STATS n = COUNT(*)',cfg)

    def test_ingest_cannot_redirect_index_or_hide_script_in_failure(self):
        cfg={'backend':'elastic','dil':'ingest','mapping':{'n':'long'},'documents':[{'id':'a','n':1}]}
        for pipeline in [
            {'processors':[{'set':{'field':'_index','value':'elsewhere'}}]},
            {'processors':[{'convert':{'field':'n','type':'long','on_failure':[{'script':{'source':'return'}}]}}]},
        ]:
            with self.assertRaises(ElasticError):
                lab.evaluate(json.dumps(pipeline),cfg)

    def test_native_drop_preserves_noop_not_fake_index_success(self):
        cfg={'backend':'elastic','dil':'ingest','mapping':{'n':'long'},'documents':[{'id':'a','n':1}]}
        result=lab.evaluate('{"processors":[{"drop":{}}]}',cfg)
        self.assertEqual(result['documents'],[])
        self.assertEqual(result['simulation'],[{'dropped':True}])
        self.assertEqual(result['items'][0]['status'],200)

    def test_nonascii_and_source_preserved(self):
        cfg={'backend':'elastic','dil':'ingest','mapping':{'message':'keyword'},
             'documents':[{'id':'a','message':'İstanbul\nçıkış'}]}
        self.assertEqual(lab.evaluate('{"processors":[]}',cfg)['documents'],cfg['documents'])

    def test_only_basic_license_and_pinned_version(self):
        self.assertEqual(lab.api('/')['version']['number'],lab.VERSION)
        self.assertEqual(lab.api('/_license')['license']['type'],'basic')
        self.assertEqual(lab.api('/api/status',kibana=True)['version']['number'],lab.VERSION)

class ScheduledTests(unittest.TestCase):
    def test_task_manager_query_eql_threshold_and_dedup(self):
        index='pafta-elastic-'+uuid.uuid4().hex
        config={'mapping':{'@timestamp':'date','event.category':'keyword','event.action':'keyword',
                          'process.name':'keyword','user.name':'keyword','status':'long'},'documents':[]}
        rules=[]
        try:
            lab.put_index(index,config)
            now=datetime.now(timezone.utc)
            def doc(id,seconds,category,action):
                return {'id':id,'@timestamp':(now-timedelta(seconds=seconds)).isoformat(timespec='milliseconds').replace('+00:00','Z'),
                        'event.category':category,'event.action':action,'process.name':'cmd.exe','user.name':'alice','status':401}
            items=lab.bulk(index,[doc('a',2,'process','start'),doc('b',1,'network','connect')])
            self.assertTrue(all(i['status']==201 for i in items))
            lab.api('/api/detection_engine/index',{},kibana=True)
            cases=[('query','kuery','event.category: process AND status >= 400 AND status < 500',{}),
                   ('eql','eql','sequence by user.name with maxspan=1m [process where event.action == "start"] [network where event.action == "connect"]',{}),
                   ('threshold','kuery','status >= 400 AND status < 500',{'threshold':{'field':['user.name'],'value':2}})]
            for typ,language,query,extra in cases:
                body=dict(type=typ,language=language,query=query,index=[index],enabled=True,
                          name='Pafta zamanlayıcı kabulü '+typ,description='Yerel geçici kabul kuralı',
                          risk_score=21,severity='low',interval='1m',**{'from':'now-10m','to':'now'},**extra)
                saved=lab.api('/api/detection_engine/rules',body,kibana=True)
                rules.append(saved)
            ids=[r['id'] for r in rules]
            def alerts():
                response=lab.api('/.alerts-security.alerts-default/_search',{'size':100,'query':{'bool':{
                    'filter':[{'terms':{'kibana.alert.rule.uuid':ids}}],
                    'must_not':[{'exists':{'field':'kibana.alert.building_block_type'}}]}}})
                lab.ensure_complete(response)
                return [h['_source'] for h in response['hits']['hits']]
            end=time.monotonic()+180
            found=[]
            while time.monotonic()<end:
                found=alerts()
                if len({a['kibana.alert.rule.uuid'] for a in found})==3:
                    break
                time.sleep(3)
            self.assertEqual(len(found),3,'Üç gerçek operational alarm beklenir; preview yeterli değildir.')
            for r in rules:
                saved=lab.api('/api/detection_engine/rules?id='+r['id'],kibana=True)
                self.assertTrue(saved['enabled'])
                self.assertEqual(saved['execution_summary']['last_execution']['status'],'succeeded',saved.get('execution_summary'))
            # Query and EQL overlap must not duplicate their original source events
            # on the next scheduled run. Threshold can legitimately alert per window.
            simple=[r['id'] for r in rules if r['type'] in ('query','eql')]
            print('Üç tür için gerçek Task Manager alarmı alındı; ikinci çalışmayı bekliyor.',flush=True)
            deadline=time.monotonic()+80
            while time.monotonic()<deadline:
                time.sleep(3)
            found=alerts()
            for id in simple:
                self.assertEqual(sum(a['kibana.alert.rule.uuid']==id for a in found),1,'örtüşmede aynı kaynak yeniden alarm olmaz')
            evidence={'version':lab.VERSION,'license':'basic','types':[r['type'] for r in rules],
                      'operational_alerts_after_second_window':{r['type']:sum(a['kibana.alert.rule.uuid']==r['id'] for a in found) for r in rules},
                      'preview_used':False,'second_window_wait_seconds':80}
            (ROOT/'outputs'/'codex-elastic-scheduled.json').write_bytes((json.dumps(evidence,ensure_ascii=False,indent=2)+'\n').encode())
        finally:
            for r in rules:
                lab.api('/api/detection_engine/rules?id='+r['id'],method='DELETE',kibana=True)
            if rules:
                lab.api('/.alerts-security.alerts-default/_delete_by_query?refresh=true',{'query':{'terms':{'kibana.alert.rule.uuid':[r['id'] for r in rules]}}})
            lab.api('/'+index,method='DELETE',missing_ok=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--scheduled',action='store_true')
    parser.add_argument('--eql-predictions',action='store_true',help='Only compare EL13–EL18 with the installed real Elasticsearch')
    args=parser.parse_args()
    if args.scheduled and args.eql_predictions:parser.error('Choose one acceptance scope')
    suite=(unittest.TestSuite([NativeTests('test_existing_eql_predictions_against_product'),
                               NativeTests('test_existing_eql_tasks_against_product')]) if args.eql_predictions
           else unittest.defaultTestLoader.loadTestsFromTestCase(ScheduledTests if args.scheduled else NativeTests))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(not result.wasSuccessful())
