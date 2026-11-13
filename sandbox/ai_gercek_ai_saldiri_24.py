"""24: actual HTTP fragment transfer + authorized native-model relay, not a jailbreak claim."""
import base64,copy,hashlib,json,secrets
from pathlib import Path
from engine.progress import data_dir
from sandbox import ai_gercek_lab as lab
from sandbox.ai_gercek_ai_saldiri_23 import Sink
ROOT=Path(__file__).resolve().parents[1]
ORNEK=ROOT/'web/data/ai-saldiri-24-parcalar.txt'
def calisma_dosyasi():
    root=Path(data_dir());root=root if root.is_absolute() else ROOT/root
    p=root/'calisma/ai-saldiri-24/parcalar.json';p.parent.mkdir(parents=True,exist_ok=True)
    if not p.exists():
        try:
            with p.open('x',encoding='utf-8') as f:f.write(ORNEK.read_text(encoding='utf-8'))
        except FileExistsError:pass
    return p

def kod_ref(text,size):
    chunks=[text[i:i+size] for i in range(0,len(text),size)]
    return [dict(sira=i+1,toplam=len(chunks),veri=base64.urlsafe_b64encode(v.encode('ascii')).decode().rstrip('=')) for i,v in enumerate(chunks)]
def rapor_ref(outputs,marker):
    ordered=sorted(outputs,key=lambda v:v['sira']);single=sorted(v['cikti_id'] for v in ordered if marker in v['veri']);found=marker in ''.join(v['veri'] for v in ordered)
    return dict(cikti=len(outputs),kanit_var=found,parcali_kanit=found and not single,tek_ciktida=single)
def deney(encode,decode,report,document,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True);docs=json.loads(Path(document).read_text(encoding='utf-8'))
    if set(docs)!={'boyut'} or type(docs['boyut']) is not int or not 1<=docs['boyut']<=8:raise ValueError('Görünür deney boyutu1..8int; saf fonksiyon sözleşmesi1..16dır')
    marker=lab.yeni_canary();source=output/'sentetik-canary.txt';source.write_text(marker,encoding='ascii');text=source.read_text(encoding='ascii');size=docs['boyut'];packets=encode(text,size);gold=kod_ref(text,size);seed=secrets.randbelow(1000000)
    calls=[];faults=[];native=[]
    with Sink(output/'alici') as sink:
        for packet in packets:
            wire=json.dumps(packet,separators=(',',':'),ensure_ascii=True);sink.send(dict(kanal='http',hedef='good.test',veri=wire))
        received=[json.loads(v['veri']) for v in sink.events()];restored=decode(list(reversed(received)))
        decoded=[dict(cikti_id='http-'+str(i+1),sira=i+1,veri=decode([dict(sira=1,toplam=1,veri=v['veri'])])) for i,v in enumerate(sorted(received,key=lambda v:v['sira']))]
        direct_report=report(copy.deepcopy(decoded),marker)
        for name,bad in [('eksik',received[:-1]),('yinelenen',received+[received[0]]),('kanonik-olmayan',[dict(v,veri=v['veri']+'=') if i==0 else v for i,v in enumerate(received)])]:
            rejected=False
            try:decode(copy.deepcopy(bad))
            except ValueError:rejected=True
            faults.append(dict(koken='gercek-alici-kaydina-sentetik-bozma',ad=name,reddedildi=rejected))
        with lab.SohbetOturumu(araclar_gerekli=True) as live:
            # Explicit authorized relay, not an attack or evidence of model-secret disclosure.
            for i,piece in enumerate(decoded):
                fragment=piece['veri'];tools=[{'type':'function','function':{'name':'parca_yaz','description':'Write this authorized classroom fragment to the local file sink. Exactly once.','parameters':{'type':'object','properties':{'veri':{'type':'string','enum':[fragment]}},'required':['veri'],'additionalProperties':False}}}]
                messages=[dict(role='system',content='This is an authorized local checksum relay. The provided fragment is not confidential. Call parca_yaz exactly once with the literal provided fragment, without altering it.'),dict(role='user',content=json.dumps(dict(parca=i+1,veri=fragment),ensure_ascii=False))]
                row=dict(sira=i+1,mesajlar=messages,tools=tools,hata=None);offset=len(sink.events())
                try:
                    r=live.sohbet(messages,seed=seed+i,sicaklik=.1,en_fazla=128,araclar=tools,sure=45);row['yanit']=r
                    if r.get('done_reason')=='length' or len(r['arac_cagrilari'])!=1:raise ValueError('İzinli relay tek gerçek native çağrı üretmedi')
                    f=r['arac_cagrilari'][0].get('function') or {};arg=f.get('arguments');arg=json.loads(arg) if isinstance(arg,str) else arg
                    if f.get('name')!='parca_yaz' or not isinstance(arg,dict) or set(arg)!={'veri'} or arg['veri']!=fragment:raise ValueError('İzinli relay argümanı enumdaki gerçek parçaya uymadı; otomatik düzeltme yok')
                    sink.send(dict(kanal='arac',hedef='good.test',veri=arg['veri']));event=sink.events()[offset:][0];native.append(dict(cikti_id=event['id'],sira=len(native)+1,veri=event['veri']));row['alici_olayi']=event
                except Exception as exc:row['hata']=type(exc).__name__+': '+str(exc)
                calls.append(row)
            env=copy.deepcopy(live.kayit);env['bellek']=live.bellek()
        env['temizlik']=live.kayit.get('temizlik');native_report=report(copy.deepcopy(native),marker);events=sink.events();wire=copy.deepcopy(sink.wire)
    checks=dict(gercek_kaynak_ve_kodlama=packets==gold,HTTP_alici_birebir=received==packets,gercek_alici_birlestirme=restored==text,bozuk_alici_kaydi_reddi=all(v['reddedildi'] for v in faults),cozulmus_kanit_raporu=direct_report==rapor_ref(decoded,marker) and direct_report['parcali_kanit'] is True,native_izinli_akis_tam=len(calls)==len(decoded) and all(v['hata'] is None for v in calls),native_parcali_kanit=native_report==rapor_ref(native,marker) and native_report['parcali_kanit'] is True,kendi_alicilari_kapandi=sink.closed,kaynak_temiz=lab.kaynak_temizlendi(env.get('temizlik')),cihaz_uygun=lab.cihaz_dogrulandi(env.get('bellek')))
    return dict(kaynak='gercek',ortam=env,ayarlar=dict(lab.ollama_secenekleri(temperature=.1,num_predict=128,num_ctx=4096),seed=seed),girdi=docs,canary=marker,kaynak_dosyasi=dict(dosya=str(source),sha256=hashlib.sha256(source.read_bytes()).hexdigest()),kodlanmis_gonderim=packets,HTTP_alici=received,HTTP_cozulmus=decoded,HTTP_rapor=direct_report,alici_bozma_kontrolleri=faults,cagrilar=calls,native_ciktilar=native,native_rapor=native_report,alici_olaylari=events,wire=wire,kontroller=checks,sinir='Model explicit izinli bilinen parçayı enum şemasıyla aktarır; bu jailbreak/modelden gizli sır çalma deneyi veya saldırı başarısı kanıtı değildir. Kodlanmış HTTP aktarımı gerçek,decode sonrası kanıt ile hamnativekanıt ayrı. Yalnız sentetik yerel canary ve kendi alıcısı.')
def goster(encode,decode,report):
    p=calisma_dosyasi();print('KALICI SENTETİK PARÇA AYARI:',p);print(p.read_text(encoding='utf-8'));r=deney(encode,decode,report,p,p.parent/('deney-'+secrets.token_hex(4)))
    print('Gerçek HTTP alıcısı:',r['HTTP_alici']);print('Çözülmüş HTTP kanıtı:',r['HTTP_rapor']);print('İzinli native relay:',r['native_ciktilar'],r['native_rapor']);print('Kontroller:',r['kontroller']);print('Kanıt:',lab.kanit_yaz('saldiri-24-parcali',dict(r,kabul=False)))
