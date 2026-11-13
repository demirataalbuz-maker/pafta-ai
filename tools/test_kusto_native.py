"""Native Kusto regressions: actual query semantics, no engine response mocks."""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from engine.lessons import Library
from engine.runners import for_step,get
from sandbox import kusto_lab


def main():
    cluster=kusto_lab.ensure()
    lib=Library()
    cases={
        ('kq24','Yönetici hesaplarına'):[
            ('count successful logins','ResultType != "0"','ResultType == "0"'),
            ('watchlist UPN not normalized','tolower(SearchKey)','SearchKey'),
            ('event UPN not normalized','tolower(UserPrincipalName)','UserPrincipalName'),
            ('outer join unrelated accounts','join kind=inner','join kind=leftouter'),
            ('count IP rows rather than distinct','dcount(IPAddress)','count()')],
        ('kq24',"Office'ten"):[
            ('parent case-sensitive','InitiatingProcessFileName in~','InitiatingProcessFileName in'),
            ('child case-sensitive','FileName in~','FileName in'),
            ('OR widens parent/child condition',' and FileName',' or FileName')],
        ('kq24','Kötü IP'):[
            ('lookup ignored','join kind=inner','join kind=leftouter'),
            ('latest timestamp used','min(Timestamp)','max(Timestamp)'),
            ('single row count','count()','countif(false)')],
        ('kq23','Her kontrolün'):[
            ('one instead of top two','top 2','top 1'),
            ('smallest instead of slowest','s desc','s asc'),
            ('wrong element cast','typeof(long)','typeof(string)')],
        ('kq23','Kaydı kaybetmeden'):[
            ('threshold equal included','s > 1000','s >= 1000'),
            ('threshold shifted','s > 1000','s > 1001'),
            ('empty input becomes null scalar','iff(isempty(sureler), dynamic([]), parse_json(sureler))','parse_json(sureler)'),
            ('maximum changed to minimum','max(s)','min(s)')],
        ('kq23','Özellikleri'):[
            ('missing version kept','isnotempty(o_surum)','isempty(o_surum)'),
            ('prefix lost',"bag_unpack(o, 'o_')",'bag_unpack(o)'),
            ('reverse timestamp order','zaman asc','zaman desc')],
        ('kq23','Şemayı sabitle'):[
            ('threshold lower equality lost','b_ms >= 1000','b_ms > 1000'),
            ('threshold shifted','b_ms >= 1000','b_ms >= 1001'),
            ('wrong OutputSchema numeric type','b_ms:long','b_ms:string'),
            ('schema source column dropped','id:long,source_zone:string,','id:long,'),
            ('null mislabeled normal',"'tip/eksik'","'normal'"),
            ('schema decimal not narrowed','b_ms:long','b_ms:real')],
        ('kq22','Kuralın çalıştırmaları'):[
            ('left endpoint included','zaman > calisma - 30m','zaman >= calisma - 30m'),
            ('right endpoint excluded','zaman <= calisma','zaman < calisma'),
            ('alarm equal excluded','hata >= 2','hata > 2')],
        ('kq22','Geç gelen'):[
            ('ingestion right endpoint excluded','alim <= calisma','alim < calisma'),
            ('ingestion left endpoint included','alim > calisma - 10m','alim >= calisma - 10m')],
        ('kq22',"Mapping'in"):[
            ('multiple @ accepted','array_length(parts)==2','array_length(parts)>=2'),
            ('name empty accepted','isnotempty(AccountName)','true'),
            ('suffix empty accepted','isnotempty(AccountUPNSuffix)','true'),
            ('IPv4 validation omitted','isnotnull(parse_ipv4(IPAddress))','true'),
            ('UPN pieces reversed','tostring(parts[0])','tostring(parts[1])')],
    }
    records=[];references=0
    for (lid,title),mutations in cases.items():
        st=next(s for s in lib.lesson('kql',lid)['steps'] if s['kind']=='gorev' and title in s['title'])
        runner=for_step(get('kql'),st)
        assert runner.name=='kusto-native'
        result=runner.test(st['solution'],st)
        assert result['status']=='pass',(lid,title,result)
        references+=1
        for label,old,new in mutations:
            assert old in st['solution'],(lid,title,label)
            r=runner.test(st['solution'].replace(old,new),st)
            assert r['status'] in ('fail','error'),(lid,title,label,r)
            if r['status']=='error':assert 'Kusto' in (r.get('error') or {}).get('msg',''),r
            records.append(dict(lesson=lid,task=title,mutation=label,status='rejected',runner_status=r['status']))
            print(lid+': '+label+': rejected',flush=True)
    for bad in ['print x=unknown_column',
                'datatable(b:dynamic)[dynamic({"x":1})] | evaluate bag_unpack(b):(x:unknown_type)',
                '.show databases']:
        try:kusto_lab.query(bad)
        except ValueError:pass
        else:raise AssertionError('Unsupported/invalid native query silently accepted')
    report=dict(backend='Microsoft Kusto Emulator real query engine',image=kusto_lab.IMAGE,
                cluster_columns=cluster['Columns'],cluster_rows=cluster['Rows'],references_passed=references,
                mutants_rejected=len(records),mutants_passed=0,cases=records,
                remaining='No live Sentinel workspace: scheduled-rule portal preview not performed.')
    (ROOT/'outputs/a-notu-kusto-native-kabul.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
