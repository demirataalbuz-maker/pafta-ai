"""Offline SMB2, Kerberos and LDAP field witnesses; never contact a server."""
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from sandbox import packet_fixtures as pf
from build_packet_analysis_corpus import tcp_flow


SCAPY_SOURCE=r'''
import base64,json,struct
from scapy.layers.smb2 import SMB2_Header,SMB2_Negotiate_Protocol_Request,SMB2_Negotiate_Protocol_Response,SMB2_Tree_Connect_Request,SMB2_Tree_Connect_Response,SMB2_Error_Response
from scapy.layers.kerberos import KRB_AS_REQ,KRB_KDC_REQ_BODY,KRB_ERROR,PrincipalName
from scapy.asn1.asn1 import ASN1_INTEGER
from cryptography.hazmat.primitives.ciphers.aead import AESCCM
def enc(data):return base64.b64encode(bytes(data)).decode()
messages=[]
def smb(direction,command,mid,payload,status=0):
 h=SMB2_Header(Command=command,MID=mid,Flags=direction,Status=status,SessionId=0x1234)
 data=bytes(h/payload);messages.append((direction,enc(len(data).to_bytes(4,'big')+data)))
smb(0,0,1,SMB2_Negotiate_Protocol_Request(Dialects=[0x0202,0x0210,0x0300],SecurityMode=3))
smb(1,0,1,SMB2_Negotiate_Protocol_Response(DialectRevision=0x0300,SecurityMode=3,Capabilities=0x40))
for mid,status in ((2,0),(3,0xc0000022),(4,0xc000006d)):
 smb(0,3,mid,SMB2_Tree_Connect_Request(Path=r'\\files.lab.test\training'))
 smb(1,3,mid,SMB2_Tree_Connect_Response(ShareType=1) if status==0 else SMB2_Error_Response(),status)
# Cryptographically real AES-CCM transform, not a complete authenticated SMB session.
plain=bytes(SMB2_Header(Command=3,MID=5,SessionId=0x1234)/SMB2_Tree_Connect_Request(Path=r'\\files.lab.test\private'))
nonce=b'\x22'*11
aad=nonce+b'\0'*5+struct.pack('<IHHQ',len(plain),0,1,0x1234)
aes=AESCCM(b'\x11'*16,tag_length=16);encrypted=aes.encrypt(nonce,plain,aad)
assert aes.decrypt(nonce,encrypted,aad)==plain
transform=b'\xfdSMB'+encrypted[-16:]+aad+encrypted[:-16]
messages.append((0,enc(len(transform).to_bytes(4,'big')+transform)))
principal=PrincipalName.fromUPN('alice@LAB.TEST');service=PrincipalName.fromSPN('krbtgt/LAB.TEST@LAB.TEST')
req=KRB_AS_REQ(reqBody=KRB_KDC_REQ_BODY(cname=principal,realm='LAB.TEST',sname=service,till='20300101000000Z',rtime=None,nonce=1234,etype=[ASN1_INTEGER(18),ASN1_INTEGER(17)]))
krb=[(0,enc(req))]
for code in (23,24,25):
 err=KRB_ERROR(errorCode=code,stime='20260101000000Z',susec=0,realm='LAB.TEST',sname=service,crealm='LAB.TEST',cname=principal,eText='training')
 krb.append((1,enc(err)))
other=req.copy();other.reqBody.cname=PrincipalName.fromUPN('bob@LAB.TEST');krb.append((0,enc(other)))
print(json.dumps({'smb':messages,'kerberos':krb}))
'''


def ber(tag,data):
    size=len(data)
    length=bytes([size]) if size<128 else bytes([0x80+((size.bit_length()+7)//8)])+size.to_bytes((size.bit_length()+7)//8,'big')
    return bytes([tag])+length+data


def ldap_message(number,tag,body):
    return ber(0x30,ber(2,bytes([number]))+ber(tag,body))


def main():
    result=subprocess.run(['wsl','-d',os.environ.get('PAFTA_WSL_DISTRO','kali-linux'),'--','python3','-c',SCAPY_SOURCE],capture_output=True,timeout=30)
    if result.returncode:raise RuntimeError(result.stderr.decode('utf-8','replace'))
    payloads=json.loads(result.stdout)
    captures={}
    captures['smb-lab']=tcp_flow([(direction,base64.b64decode(data),None) for direction,data in payloads['smb']],445)
    frames=[]
    for direction,encoded in payloads['kerberos']:
        src,dst=('192.0.2.10','192.0.2.20') if direction==0 else ('192.0.2.20','192.0.2.10')
        sport,dport=(53000,88) if direction==0 else (88,53000)
        data=pf.ethernet(pf.ipv4(pf.udp(sport,dport,base64.b64decode(encoded),src=src,dst=dst),src,dst,17))
        frames.append((data,len(data)))
    captures['kerberos-lab']=pf.pcap(frames)
    messages=[]
    for i,code in enumerate((0,48,49,50),1):
        bind=ldap_message(i,0x60,ber(2,b'\x03')+ber(4,b'')+ber(0x80,b''))
        reply=ldap_message(i,0x61,ber(10,bytes([code]))+ber(4,b'')+ber(4,b'training'))
        messages.extend(((0,bind,None),(1,reply,None)))
    for i,base in ((5,b'DC=lab,DC=test'),(6,b'DC=other,DC=test')):
        search=ber(4,base)+ber(10,b'\x02')+ber(10,b'\0')+ber(2,b'\0')+ber(2,b'\0')+ber(1,b'\0')
        search+=ber(0xa3,ber(4,b'objectClass')+ber(4,b'person'))+ber(0x30,ber(4,b'cn'))
        messages.append((0,ldap_message(i,0x63,search),None))
        messages.append((1,ldap_message(i,0x65,ber(10,b'\0')+ber(4,b'')+ber(4,b'')),None))
    captures['ldap-lab']=tcp_flow(messages,389)
    directory=ROOT/'tracks/packets/captures';path=directory/'advanced.json'
    manifest=json.loads(path.read_text(encoding='utf-8'))
    for name,data in captures.items():
        (directory/(name+'.pcap')).write_bytes(data)
        manifest[name]={'file':name+'.pcap','sha256':hashlib.sha256(data).hexdigest(),
                        'generator':'tools/build_packet_directory_corpus.py; Scapy encoders / LDAP BER; AES-CCM transform witness, no live AD/authentication'}
    path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('3 offline SMB2/Kerberos/LDAP corpora written; no server contacted.')


if __name__=='__main__':main()
