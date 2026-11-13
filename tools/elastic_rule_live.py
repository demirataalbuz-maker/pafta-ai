"""Run the student's EL24 JSON as a real scheduled rule (not a preview).

The fixture's dates are explicitly rebased to now minus three minutes, keeping
all event deltas. Use a ten-minute lookback for this timing experiment; test
exact interval boundaries in the deterministic native previews in the lessons.
All rules/operational alerts/indexes created here are removed afterwards.
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import time
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from engine.lessons import Library
from sandbox import elastic_lab as lab
from sandbox.elastic_common import ElasticError

def execute(code,step):
    config=lab.options(step['stdin'])
    # The same bounded field validation and real API schema as the lesson.
    lab.evaluate(code,config)
    body=json.loads(code)
    if body['type'] not in ('query','eql'):
        raise ElasticError('Canlı öğrenci deneyi EL24 query/eql türleriyle sınırlıdır.')
    anchor=datetime.fromisoformat(config['context']['timeframe_end'].replace('Z','+00:00'))
    new_anchor=datetime.now(timezone.utc)-timedelta(minutes=3)
    for doc in config['documents']:
        original=datetime.fromisoformat(doc['@timestamp'].replace('Z','+00:00'))
        doc['@timestamp']=(new_anchor+(original-anchor)).isoformat(timespec='milliseconds').replace('+00:00','Z')
    index='pafta-elastic-'+uuid.uuid4().hex
    saved=None
    try:
        lab.put_index(index,config)
        items=lab.bulk(index,config['documents'])
        if any(i['error'] for i in items):
            raise ElasticError('Canlı deney verisi indekslenemedi.')
        # Preview is already measured above. This is a fresh, enabled persisted rule.
        payload=dict(body,index=[index],enabled=True,name='Pafta öğrenci zamanlayıcı deneyi',
                     description='EL24; tarihler açıkça yeniden bazlandı',risk_score=21,severity='low',
                     interval='1m',**{'from':'now-10m','to':'now'})
        saved=lab.api('/api/detection_engine/rules',payload,kibana=True)
        end=time.monotonic()+150
        while time.monotonic()<end:
            status=lab.api('/api/detection_engine/rules?id='+saved['id'],kibana=True)
            execution=status.get('execution_summary',{}).get('last_execution',{})
            if execution.get('status')=='succeeded':
                break
            if execution.get('status')=='failed':
                raise ElasticError('Gerçek zamanlayıcı yürütmesi başarısız: '+str(execution))
            time.sleep(2)
        else:
            raise ElasticError('Task Manager 150 saniyede başarılı yürütme bildirmedi.')
        lab.api('/.alerts-security.alerts-default/_refresh')
        query={'bool':{'filter':[{'term':{'kibana.alert.rule.uuid':saved['id']}}],
                       'must_not':[{'exists':{'field':'kibana.alert.building_block_type'}}]}}
        response=lab.api('/.alerts-security.alerts-default/_search',{'size':100,'query':query})
        lab.ensure_complete(response)
        ids=sorted({a['id'] for h in response['hits']['hits'] for a in h['_source'].get('kibana.alert.ancestors',[]) if a.get('type')=='event'})
        return {'execution':'Task Manager / operational','type':body['type'],'interval':'1m','from':'now-10m',
                'source_event_ids':ids,'alert_count':len(response['hits']['hits']),'dates_rebased':True}
    finally:
        if saved:
            lab.api('/api/detection_engine/rules?id='+saved['id'],method='DELETE',kibana=True)
            lab.api('/.alerts-security.alerts-default/_delete_by_query?refresh=true',{'query':{'term':{'kibana.alert.rule.uuid':saved['id']}}})
        lab.api('/'+index,method='DELETE',missing_ok=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--code-file',type=Path,required=True,help='Kendi yazdığın EL24 create-rule JSON dosyası')
    parser.add_argument('--task',type=int,choices=(1,2),default=1)
    args=parser.parse_args()
    steps=[s for s in Library().lesson('elastic','el24')['steps'] if s['kind']=='gorev']
    print('Önizleme denetiminden sonra gerçek zamanlayıcı bekleniyor (en çok 150 sn).',flush=True)
    print(json.dumps(execute(args.code_file.read_text(encoding='utf-8-sig'),steps[args.task-1]),ensure_ascii=False,indent=2))
