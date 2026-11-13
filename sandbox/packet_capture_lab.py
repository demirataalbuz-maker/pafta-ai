"""Bounded real tcpdump on an isolated loopback UDP pair in Kali WSL.

The generated receiver/sender ports are appended as a mandatory BPF scope.
Only our own three small / twenty large datagrams are sent, then tcpdump is
reaped. No physical interface or arbitrary program/path is accepted.
"""
import base64
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess


LINUX=r'''
import base64,json,os,pathlib,select,socket,subprocess,sys,tempfile,time
job=json.load(sys.stdin)
receiver=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
sender=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
noise=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
receiver.bind(('127.0.0.1',0));sender.bind(('127.0.0.1',0));receiver.settimeout(1)
noise.bind(('127.0.0.1',0));noise.settimeout(1)
sport=sender.getsockname()[1];dport=receiver.getsockname()[1]
scope=f'udp and src host 127.0.0.1 and dst host 127.0.0.1 and src port {sport} and dst port {dport} and ({job["filter"]})'
proc=None
try:
 with tempfile.TemporaryDirectory(prefix='pafta-own-loopback-') as folder:
  p=pathlib.Path(folder)
  args=['tcpdump','-i','lo','-nn','-U','-B','4096','-Z','root','-s',str(job['snap']),'-c',str(job['count']),'-w',str(p/'sonuc.pcap')]
  if job['rotate']:args+=['-C','1','-W','2']
  proc=subprocess.Popen(args+[scope],stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=dict(os.environ,LC_ALL='C'))
  ready=False;deadline=time.monotonic()+3;startup=[]
  while time.monotonic()<deadline and proc.poll() is None:
   if select.select([proc.stderr],[],[],.1)[0]:
    line=proc.stderr.readline()
    startup.append(line)
    if b'listening on' in line:ready=True;break
  if not ready:
   if proc.poll() is not None:
    _,err=proc.communicate();startup.append(err)
   raise RuntimeError('tcpdump loopback capture could not start: '+b''.join(startup).decode('utf-8','replace'))
  sizes=[60000]*20 if job['rotate'] else [21,22,23]
  if job['rotate'] and int(pathlib.Path('/sys/class/net/lo/mtu').read_text())<60028:
   raise RuntimeError('rotation profile requires loopback MTU >= 60028; network configuration was not changed')
  for size in sizes:
   payload=b'P'*size
   sender.sendto(b'N'*size,noise.getsockname());noise.recvfrom(65535)
   sender.sendto(payload,receiver.getsockname())
   data,_=receiver.recvfrom(65535)
   assert data==payload
  try:out,err=proc.communicate(timeout=3)
  except subprocess.TimeoutExpired:raise RuntimeError('bounded tcpdump did not finish; filter may reject the training datagrams')
  if proc.returncode:raise RuntimeError(err.decode('utf-8','replace'))
  files={f.name:base64.b64encode(f.read_bytes()).decode() for f in sorted(p.glob('sonuc.pcap*'))}
  print(json.dumps({'files':files,'stderr':err.decode('utf-8','replace'),'scope':'generated loopback sender/receiver pair only',
                    'reaped':proc.poll() is not None,'directory':folder,'uid':os.getuid(),'excluded_noise':len(sizes)}))
finally:
 if proc is not None and proc.poll() is None:
  proc.kill();proc.communicate()
 receiver.close();sender.close();noise.close()
'''


def _engine():
    try:from . import packet_engine
    except ImportError:import packet_engine
    return packet_engine


def parse_command(code,profile):
    e=_engine()
    if profile not in ('kisa','donusum'):raise e.PacketError('Bilinmeyen loopback laboratuvarı.')
    if not isinstance(code,str) or len(code)>16000 or '\0' in code:raise e.PacketError('Geçersiz tcpdump komutu.')
    try:parts=shlex.split(code)
    except ValueError as exc:raise e.PacketError(str(exc)) from exc
    if not parts or parts.pop(0)!='tcpdump':raise e.PacketError('Komut tcpdump ile başlamalı.')
    opts={};at=0
    while at<len(parts) and parts[at].startswith('-'):
        flag=parts[at];at+=1
        if flag=='-nn':
            if flag in opts:raise e.PacketError('Yinelenen seçenek: '+flag)
            opts[flag]=True;continue
        if flag not in ('-i','-s','-c','-w','-C','-W') or at==len(parts) or flag in opts:
            raise e.PacketError('Desteklenmeyen/eksik tcpdump seçeneği: '+flag)
        opts[flag]=parts[at];at+=1
    if opts.get('-i')!='lo' or opts.get('-w')!='sonuc.pcap' or not opts.get('-nn'):
        raise e.PacketError('Laboratuvar -i lo -nn ve -w sonuc.pcap ister; fiziksel arayüz/dış dosya yolu alınmaz.')
    rotate=profile=='donusum';count=20 if rotate else 3
    if opts.get('-c')!=str(count):raise e.PacketError(f'Bu laboratuvar -c {count} ister.')
    snap=opts.get('-s','')
    if not snap.isdecimal() or int(snap)>65535:raise e.PacketError('-s 0..65535 olmalı.')
    if rotate:
        if opts.get('-C')!='1' or opts.get('-W')!='2':raise e.PacketError('Döndürme laboratuvarı -C 1 -W 2 ister.')
    elif '-C' in opts or '-W' in opts:raise e.PacketError('Döndürme için laboratuvar:donusum seç.')
    filter_text=' '.join(parts[at:])
    if not filter_text:raise e.PacketError('Sayısal BPF yakalama filtresi gerekli.')
    try:
        from .bpf_native import _numeric_filter, evaluate
        from .packet_fixtures import pcap_bytes
    except ImportError:
        from bpf_native import _numeric_filter, evaluate
        from packet_fixtures import pcap_bytes
    _numeric_filter(filter_text)
    # Validate as an independent native expression before embedding it. An
    # unmatched ')' must never close our mandatory generated-port scope.
    depth=0
    for char in filter_text:
        if char=='(':depth+=1
        elif char==')':depth-=1
        if depth<0:raise e.PacketError('BPF parantezleri dengeli olmalı.')
    if depth:raise e.PacketError('BPF parantezleri dengeli olmalı.')
    evaluate(filter_text,pcap_bytes([]))
    return {'snap':int(snap),'count':count,'rotate':rotate,'filter':filter_text}


def run(code,profile='kisa'):
    e=_engine();job=parse_command(code,profile)
    try:
        from .wsl_process import distro_name
        from .capture_formats import parse_capture
    except ImportError:
        from wsl_process import distro_name
        from capture_formats import parse_capture
    wsl=shutil.which('wsl.exe')
    if not wsl:raise e.PacketError('Bu ders kurulu Kali WSL ve tcpdump gerektirir; README gereksinimlerine bak.')
    try:
        result=subprocess.run([wsl,'-d',distro_name(),'-u','root','--cd','/tmp','--exec','python3','-I','-X','utf8','-c',LINUX],
                              input=json.dumps(job).encode(),capture_output=True,timeout=20,creationflags=e.NO_WINDOW)
    except subprocess.TimeoutExpired as exc:raise e.PacketError('Loopback laboratuvarı 20 saniyede bitmedi.') from exc
    if result.returncode:raise e.PacketError(result.stderr.decode('utf-8','replace'))
    data=json.loads(result.stdout);files=[];all_frames=[]
    for name,encoded in sorted(data['files'].items()):
        raw=base64.b64decode(encoded,validate=True)
        frames=parse_capture(raw);all_frames+=frames
        files.append({'name':name,'base64':encoded,'size':len(raw),'count':len(frames),
                      'caplens':[len(f.data) for f in frames],'wirelens':[f.wirelen for f in frames]})
    if len(files)>2 or sum(f['size'] for f in files)>2_000_000:raise e.PacketError('Laboratuvar kayıt boyutu sınırı aşıldı.')
    out=f'Paketler: {len(all_frames)}\nDosyalar: {len(files)}\n'
    if not job['rotate']:
        out+='Yakalanan: '+', '.join(str(len(f.data)) for f in all_frames)+'\n'
        out+='Hat: '+', '.join(str(f.wirelen) for f in all_frames)+'\n'
    return {'status':'ok','error':None,'segs':[['out',out]],'stdout':out,'stderr':data['stderr'],
            'exports':files,'scope':data['scope'],'packet_backend':'Kali tcpdump loopback lab','packet_dialect':'tcpdump-lab',
            'runtime':{'reaped':data['reaped'],'linux_directory':data['directory'],'uid':data['uid'],'interface':'lo','excluded_noise':data['excluded_noise']},
            'tablolar':[{'satir':1,'sutunlar':['Dosya','Paket','Bayt'],'satirlar':[[f['name'],f['count'],f['size']] for f in files]}]}


def test_helpers(code,profile):
    parse_command(code,profile)
    return {'src':code,'calistir':lambda:run(code,profile)}
