"""Evidence-backed laptop dashboard; does not alter curriculum quality scores."""
import collections,datetime,hashlib,html,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tools'))
from engine.lessons import Library
from audit_laptop import classify
BASE=ROOT/'outputs/audit-20261027'
GATES={37:'Sentinel çalışma alanında portal Test with current data / Review kabulü yok.',60:'Gerçek BloodHound CE yolu doğrulandı; gerçek AD/DC AccessCheck kabulü yok.',63:'Gerçek DC LDAP/TLS/signing/CBT ve ldp.exe GUI kabulü yok.'}
LABELS={'PASS':'Geçti','WARN':'Geçti · test tanısı eksik','FAIL':'Kaldı','BLOCKED':'Lab eksik','UNTESTED':'Test tamamlanmadı','STALE':'Kaynak değişti · tekrar gerekli','PARTIAL':'Canlı kabul kısmen'}
def load(path):return json.loads(path.read_text(encoding='utf8'))
def expand(ids):
 out=[]
 for value in ids:
  m=re.fullmatch(r'([A-Za-z]+)(\d+)-\1(\d+)',value)
  if m:out.extend(m[1].lower()+str(i).zfill(len(m[2])) for i in range(int(m[2]),int(m[3])+1))
  else:out.append(value.lower())
 return out
def main():
 lib=Library();tracks=sorted(p.name for p in (ROOT/'tracks').iterdir() if (p/'track.json').exists());rows=[];trackrows=[];rawissues=[];allcounts=collections.Counter();kindcounts=collections.defaultdict(collections.Counter)
 for tid in tracks:
  outline=lib.outline(tid);reports={};counts=collections.Counter();sources_stale=False
  for shell in ('windows','gitbash'):
   path=BASE/shell/(tid+'.json')
   if not path.exists():continue
   rep=load(path)
   for file,digest in rep.get('source_sha256',{}).items():
    p=ROOT/file
    if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:sources_stale=True
   for r in rep['results']:
    if r.get('runner_status'):
     reconstructed={'status':r['runner_status'],'error':r.get('error'),'checks':r.get('failed_checks',[]),'detail':r.get('detail','')}
     normalized=classify(r['kind'],reconstructed)
     if (r['kind']=='starter' or normalized=='BLOCKED') and normalized!=r['status']:r=dict(r,original_audit_status=r['status'],status=normalized)
    reports.setdefault((shell,r['lesson']),[]).append(r);counts[r['status']]+=1;kindcounts[r['kind']][r['status']]+=1
    if r['status'] not in ('PASS','DECLARED'):rawissues.append(dict(r,track=tid,shell=shell))
  for lid in outline['order']:
   statuses=[];notes=[];blockers=[];n=collections.Counter()
   for shell in ('windows','gitbash'):
    rr=reports.get((shell,lid),[])
    if not rr or all(r['status']=='DECLARED' for r in rr):statuses.append('UNTESTED');continue
    n.update(r['status'] for r in rr)
    bad=[r for r in rr if r['status'] in ('FAIL','ERROR') and r['kind']!='starter']
    gap=[r for r in rr if r['kind']=='starter' and r['status']=='FAIL']
    diag=[r for r in rr if r['kind']=='starter' and r['status']=='ERROR']
    if bad or gap:statuses.append('FAIL')
    elif any(r['status']=='BLOCKED' for r in rr):statuses.append('BLOCKED')
    elif diag:statuses.append('WARN')
    else:statuses.append('PASS')
    if diag:notes.append(shell+': '+str(len(diag))+' başlangıç kodu testi anlaşılır kontrol yerine istisna verdi; PASS diye sayılmadı.')
    blockers.extend((r.get('error') or {}).get('msg',r.get('detail','')) for r in rr if r['status']=='BLOCKED')
   status=next((s for s in ('FAIL','BLOCKED','UNTESTED','WARN') if s in statuses),'PASS')
   if sources_stale:status='STALE'
   rows.append({'track':tid,'lesson':lid,'status':status,'counts':dict(n),'notes':notes,'blockers':list(dict.fromkeys(blockers)),'reading_language':outline.get('okuma_dili')})
  trackrows.append({'track':tid,'lessons':len(outline['order']),'counts':dict(counts),'status_counts':dict(collections.Counter(r['status'] for r in rows if r['track']==tid)),'reading_language':outline.get('okuma_dili'),'source_stale':sources_stale})
  allcounts.update(counts)
 index={(r['track'],r['lesson']):r for r in rows};scores=load(ROOT/'docs/denetim/puanlar.json')['maddeler'];items=[]
 for m in scores:
  lids=expand(m['dersler']);lr=[index.get((m['yol'],lid),{'status':'UNTESTED','notes':['Ders eşlemesi bulunamadı: '+lid],'counts':{}}) for lid in lids]
  status=next((s for s in ('FAIL','BLOCKED','STALE','UNTESTED','WARN') if any(x['status']==s for x in lr)),'PASS')
  note=GATES.get(m['no'],'')
  if note and status not in ('FAIL','STALE','UNTESTED'):status='PARTIAL'
  if not note:note='; '.join(dict.fromkeys(v for x in lr for v in x.get('blockers',[])))
  if m['no']==95:note='Çevrimdışı bellek kanıtı testleri geçti. Gerçek bellek imajıyla Volatility kabulü bu koşuda atlandı; bunun yerine canlı kabul iddia edilmez.'
  items.append({'no':m['no'],'name':m['ad'],'track':m['yol'],'lessons':lids,'status':status,'score':sum(m.get('puan',{}).values()),'quality_decision':m['karar'],'score_source':m.get('kaynak',''),'note':note,'counts':dict(sum((collections.Counter(x['counts']) for x in lr),collections.Counter())),'warnings':[v for x in lr for v in x['notes']]})
 now=datetime.datetime.now(datetime.timezone.utc).isoformat();result={'generated_utc':now,'scope':'Actual automated reference/starter/example checks on this laptop in Windows and Git Bash; not independent grading or proof of unavailable live labs.','lesson_count':len(rows),'item_count':len(items),'job_counts':dict(allcounts),'kind_status_counts':{k:dict(v) for k,v in kindcounts.items()},'lesson_status_counts':dict(collections.Counter(r['status'] for r in rows)),'item_status_counts':dict(collections.Counter(r['status'] for r in items)),'tracks':trackrows,'items':items,'lessons':rows,'issues':rawissues}
 BASE.mkdir(parents=True,exist_ok=True);(BASE/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
 esc=html.escape
 tr=''.join('<tr><td>'+esc(x['track'])+'</td><td>'+str(x['lessons'])+'</td><td>'+esc(str(x['status_counts']))+'</td><td>'+esc(str(x['counts']))+'</td><td><a href="../../outputs/audit-20261027/windows/'+x['track']+'.json">Windows</a> · <a href="../../outputs/audit-20261027/gitbash/'+x['track']+'.json">Git Bash</a></td></tr>' for x in trackrows)
 payload=json.dumps({'items':items,'labels':LABELS},ensure_ascii=False).replace('</','<\\/')
 page='''<!doctype html><html lang="tr"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Pafta · Bu laptopun doğrulaması</title><style>body{font:16px system-ui;margin:32px auto;max-width:1400px;padding:0 20px;background:#101721;color:#e7edf5}h1{font-size:30px}p{line-height:1.6;color:#c0cedd}a{color:#80c7ff}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:12px 8px;border-bottom:1px solid #324153;text-align:left;vertical-align:top}input,select,button{font:inherit;padding:10px;background:#1f2d3e;color:white;border:1px solid #53708c;border-radius:6px;margin:5px}small{display:block;color:#aabbcd;max-width:600px}.PASS{color:#76e0ae}.FAIL,.BLOCKED,.PARTIAL,.STALE,.UNTESTED{color:#ffba8d}.WARN{color:#f0d983}.cards{display:flex;gap:18px;flex-wrap:wrap}.card{padding:18px;background:#1c2939;border-radius:10px}details{margin:24px 0}th{position:sticky;top:0;background:#1c2939}</style><h1>Pafta · Bu laptopun doğrulaması</h1><p>Bu sayfa ölçüm anının kaydıdır; canlı motor monitörü değildir. <b>Puanlar kalite panelinden alınır; bu tarama yeni puan üretmez.</b> “Geçti”, kapsamdaki otomatik kontrollerin geçtiğini söyler. Eksik AD/DC ve Sentinel kabulünü tamamlandı göstermez.</p>'''
 page+='<p>Ölçüm kaydı: '+esc(now)+' · <a href="DENETIM_SAYFASI.html">Kalite / puan paneli</a> · <a href="../../outputs/audit-20261027/summary.json">Tüm 543 ders ve ham bulgular</a> · <a href="laptop-tam-denetim-20261027.md">Eksikler ve geliştirme raporu</a></p>'
 page+='<div class="cards"><div class="card">'+str(len(rows))+' ders · '+str(len(tracks))+' yol</div><div class="card">'+str(len(items))+' denetim maddesi</div><div class="card">'+esc(str(result['item_status_counts']))+'</div></div><p><b>DECLARED:</b> Yazarın verdiği örnek çıktı bu koşucuda çalıştırılmadı. Okuma yollarındaki Python alıştırmasının geçmesi, her C/C#/Java/ASM örneğinin yerel derleyicide çalıştırıldığı anlamına gelmez. <b>WARN:</b> Referans çözüm geçti, başlangıç kodunun test geri bildirimi geliştirilmeli.</p>'
 page+='<input id="search" placeholder="Madde, ders veya yol ara"><select id="filter"><option value="">Tüm maddeler</option>'+''.join('<option value="'+k+'">'+v+'</option>' for k,v in LABELS.items())+'</select><span id="count"></span><table><thead><tr><th>No</th><th>Madde / dersler</th><th>Bu laptop</th><th>Kalite puanı</th><th>Kanıt / kalan</th></tr></thead><tbody id="items"></tbody></table><details><summary>23 yolun otomatik denetim dökümü</summary><table><tr><th>Yol</th><th>Ders</th><th>Ders durumları</th><th>Kontrol kayıtları</th><th>Ham kanıt</th></tr>'+tr+'</table></details>'
 page+='<script>const data='+payload+''';const $=s=>document.querySelector(s);const norm=s=>String(s).toLocaleLowerCase('tr').replace(/ı/g,'i');function render(){let q=norm($('#search').value),f=$('#filter').value,shown=0;$('#items').replaceChildren();for(let x of data.items){if(f&&x.status!==f)continue;if(q&&!norm('#'+x.no+' '+JSON.stringify(x)).includes(q))continue;shown++;let row=document.createElement('tr');let vals=[x.no,x.name+' · '+x.track+' / '+x.lessons.join(', '),data.labels[x.status],x.score+'/100 · '+x.quality_decision,x.note||'Windows ve Git Bash ham kayıtları yol tablosunda.'];for(let [i,v] of vals.entries()){let td=document.createElement('td');td.textContent=v;if(i===2)td.className=x.status;if(i===1&&x.warnings.length){let s=document.createElement('small');s.textContent=x.warnings.join(' ');td.append(s)}if(i===3){let s=document.createElement('small');s.textContent=x.score_source;td.append(s)}row.append(td)}$('#items').append(row)}$('#count').textContent=shown+' / '+data.items.length}$('#search').oninput=render;$('#filter').onchange=render;render();</script></html>'''
 (ROOT/'docs/denetim/LAPTOP_DURUM.html').write_text(page,encoding='utf8');print(json.dumps({k:result[k] for k in ('lesson_count','item_count','job_counts','lesson_status_counts','item_status_counts')},ensure_ascii=False))
if __name__=='__main__':main()
