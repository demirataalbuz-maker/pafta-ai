"""Author-only: actual TLS/QUIC libraries, in memory, without network traffic.

Run on Windows with installed Kali dependencies; no package installation.
Only training session secrets, never a user's browser secrets, are exported.
"""
import base64
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def linux_build():
    import datetime
    import ssl
    import struct
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes,serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    from hpack import Encoder
    from aioquic.quic.configuration import QuicConfiguration
    from aioquic.quic.connection import QuicConnection
    import packet_fixtures as pf
    outputs={}
    def add(name,raw):
        outputs[name]=base64.b64encode(raw).decode()
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'pafta.lab.test')])
    cert=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
          .serial_number(1).not_valid_before(datetime.datetime(2025,1,1)).not_valid_after(datetime.datetime(2035,1,1))
          .add_extension(x509.SubjectAlternativeName([x509.DNSName('pafta.lab.test')]),critical=False).sign(key,hashes.SHA256()))
    client,server='192.0.2.10','192.0.2.20'
    def tcp_capture(transfers,port=443):
        frames=[];seq=[1001,9001]
        def emit(direction,payload=b'',flags=0x18,number=None,ack=None):
            src,dst=(client,server) if direction==0 else (server,client)
            sport,dport=(51000,port) if direction==0 else (port,51000)
            tcp=pf.tcp(sport,dport,payload,src=src,dst=dst,seq=seq[direction] if number is None else number,
                       ack=seq[1-direction] if ack is None else ack,flags=flags)
            frame=pf.ethernet(pf.ipv4(tcp,src,dst,6))
            frames.append((frame,len(frame)))
            seq[direction]+=len(payload)
        emit(0,flags=2,number=1000,ack=0)
        emit(1,flags=0x12,number=9000,ack=1001)
        emit(0,flags=0x10)
        for direction,data in transfers:
            emit(direction,data)
            emit(1-direction,flags=0x10)
        return pf.pcap(frames)
    with tempfile.TemporaryDirectory(prefix='pafta-tls-memory-') as directory:
        p=Path(directory)
        (p/'cert.pem').write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        (p/'key.pem').write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.TraditionalOpenSSL,serialization.NoEncryption()))
        sc=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);sc.load_cert_chain(p/'cert.pem',p/'key.pem');sc.set_alpn_protocols(['h2'])
        cc=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT);cc.check_hostname=False;cc.verify_mode=ssl.CERT_NONE;cc.set_alpn_protocols(['h2'])
        cc.minimum_version=sc.minimum_version=ssl.TLSVersion.TLSv1_3
        cc.maximum_version=sc.maximum_version=ssl.TLSVersion.TLSv1_3
        cc.keylog_filename=str(p/'keys.log')
        ci,co,si,so=ssl.MemoryBIO(),ssl.MemoryBIO(),ssl.MemoryBIO(),ssl.MemoryBIO()
        c=cc.wrap_bio(ci,co,server_hostname='pafta.lab.test');s=sc.wrap_bio(si,so,server_side=True)
        transfers=[]
        def pump():
            for direction,out,inp in ((0,co,si),(1,so,ci)):
                data=out.read()
                if data:
                    transfers.append((direction,data));inp.write(data)
        done=[False,False]
        for _ in range(30):
            for i,obj in enumerate((c,s)):
                try:obj.do_handshake();done[i]=True
                except ssl.SSLWantReadError:pass
            pump()
            if all(done):break
        assert all(done) and c.selected_alpn_protocol()=='h2'
        def h2(kind,flags,stream,payload):
            return len(payload).to_bytes(3,'big')+bytes([kind,flags])+struct.pack('!I',stream)+payload
        headers=Encoder().encode([(':method','GET'),(':scheme','https'),(':authority','pafta.lab.test'),(':path','/lab')])
        request=b'PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n'+h2(4,0,0,b'')+h2(1,5,1,headers)
        c.write(request);pump();assert s.read()==request
        response=h2(4,0,0,b'')+h2(1,4,1,Encoder().encode([(':status','200')]))+h2(0,1,1,b'PAFTA-H2-LAB')
        s.write(response);pump();assert c.read()==response
        for stream,status in ((3,'201'),(5,'202')):
            request=h2(1,5,stream,Encoder().encode([(':method','GET'),(':scheme','https'),(':authority','pafta.lab.test'),(':path','/lab')]))
            c.write(request);pump();assert s.read()==request
            response=h2(1,5,stream,Encoder().encode([(':status',status)]))
            s.write(response);pump();assert c.read()==response
        add('tls-h2.pcap',tcp_capture(transfers))
        add('tls-h2.keys',(p/'keys.log').read_bytes())
    logs=io.StringIO()
    qc=QuicConfiguration(is_client=True,alpn_protocols=['pafta-lab'],server_name='quic.lab.test',verify_mode=ssl.CERT_NONE,secrets_log_file=logs)
    qs=QuicConfiguration(is_client=False,alpn_protocols=['pafta-lab'],certificate=cert,private_key=key,secrets_log_file=logs)
    c=QuicConnection(configuration=qc);c.connect((server,443),now=0)
    s=QuicConnection(configuration=qs,original_destination_connection_id=c.original_destination_connection_id)
    datagrams=[]
    def q_pump(now):
        count=0
        for direction,src,dst,addr in ((0,c,s,(client,52000)),(1,s,c,(server,443))):
            for data,_ in src.datagrams_to_send(now):
                datagrams.append((direction,data));dst.receive_datagram(data,addr,now);count+=1
        return count
    for i in range(30):q_pump(i*.01)
    c.send_stream_data(0,b'PAFTA-QUIC-LAB',end_stream=True)
    for i in range(30,40):q_pump(i*.01)
    frames=[]
    for direction,data in datagrams:
        src,dst=(client,server) if direction==0 else (server,client)
        sport,dport=(52000,443) if direction==0 else (443,52000)
        frame=pf.ethernet(pf.ipv4(pf.udp(sport,dport,data,src=src,dst=dst),src,dst,17))
        frames.append((frame,len(frame)))
    assert frames and logs.getvalue()
    add('quic-lab.pcap',pf.pcap(frames));add('quic-lab.keys',logs.getvalue().encode())
    print(json.dumps(outputs))


def main():
    root=Path(__file__).resolve().parents[1]
    import os
    source=base64.b64encode(Path(__file__).read_bytes()).decode()
    fixtures=base64.b64encode((root/'sandbox/packet_fixtures.py').read_bytes()).decode()
    bootstrap='''import tempfile,pathlib,base64,runpy,sys,json
payload=json.load(sys.stdin)
with tempfile.TemporaryDirectory(prefix="pafta-protocol-") as folder:
 p=pathlib.Path(folder)
 (p/"builder.py").write_bytes(base64.b64decode(payload["source"]))
 (p/"packet_fixtures.py").write_bytes(base64.b64decode(payload["fixtures"]))
 sys.path.insert(0,folder)
 ns=runpy.run_path(str(p/"builder.py"));ns["linux_build"]()
'''
    result=subprocess.run(['wsl','-d',os.environ.get('PAFTA_WSL_DISTRO','kali-linux'),'--','python3','-c',bootstrap],
                          input=json.dumps(dict(source=source,fixtures=fixtures)).encode(),capture_output=True,timeout=60)
    if result.returncode:
        raise RuntimeError(result.stderr.decode('utf-8','replace'))
    output=json.loads(result.stdout)
    directory=root/'tracks/packets/captures';manifest_path=directory/'advanced.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {}
    import hashlib
    for filename,encoded in output.items():
        raw=base64.b64decode(encoded);(directory/filename).write_bytes(raw)
        if filename.endswith('.pcap'):
            manifest[filename[:-5]]={'file':filename,'sha256':hashlib.sha256(raw).hexdigest(),
                                    'generator':'tools/build_packet_protocol_corpus.py; Python ssl TLS1.3 / aioquic 1.3.0; in-memory'}
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('Built training TLS/HTTP2 and QUIC captures and session key logs (no sockets).')


if __name__=='__main__':main()
