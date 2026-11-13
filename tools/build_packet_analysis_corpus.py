"""Offline TCP/HTTP reassembly witnesses; no sockets or external input."""
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from sandbox import packet_fixtures as pf


def tcp_flow(messages,port=80):
    """messages: (direction, bytes, optional explicit sequence)."""
    frames=[];seq=[1001,9001];client,server='192.0.2.10','192.0.2.20'
    def emit(direction,data=b'',flags=0x18,number=None):
        src,dst=(client,server) if direction==0 else (server,client)
        sport,dport=(50000,port) if direction==0 else (port,50000)
        number=seq[direction] if number is None else number
        tcp=pf.tcp(sport,dport,data,src=src,dst=dst,seq=number,ack=seq[1-direction],flags=flags)
        packet=pf.ethernet(pf.ipv4(tcp,src,dst,6));frames.append((packet,len(packet)))
        seq[direction]=max(seq[direction],number+len(data))
    emit(0,flags=2,number=1000);emit(1,flags=0x12,number=9000);emit(0,flags=0x10)
    for direction,data,number in messages:emit(direction,data,number=number)
    return pf.pcap(frames,step_us=1000)


def main():
    directory=ROOT/'tracks/packets/captures';path=directory/'advanced.json'
    manifest=json.loads(path.read_text(encoding='utf-8'))
    request=b'GET /download HTTP/1.1\r\nHost: lab.test\r\n\r\n'
    body=b'PAFTA-TCP-LAB'
    response=b'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: '+str(len(body)).encode()+b'\r\n\r\n'+body
    split=len(response)-7
    common=[(0,request[:20],None),(0,request[20:],None)]
    variants={
        'tcp-tam':common+[(1,response[:split],None),(1,response[split:],None)],
        'tcp-tekrar':common+[(1,response[:split],9001),(1,response[split:],9001+split),(1,response[:split],9001)],
        'tcp-sirasiz':common+[(1,response[:20],9001),(1,response[split:],9001+split),(1,response[20:split],9021)],
        'tcp-kayip':common+[(1,response[:split],9001)],
    }
    for name,messages in variants.items():
        raw=tcp_flow(messages);filename=name+'.pcap';(directory/filename).write_bytes(raw)
        manifest[name]={'file':filename,'sha256':hashlib.sha256(raw).hexdigest(),'generator':'tools/build_packet_analysis_corpus.py; authored TCP sequence/HTTP bytes, no network'}
    path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('4 TCP reassembly witnesses written.')


if __name__=='__main__':main()
