"""Real OpenLDAP/Impacket/TLS clients; stdin is private managed-lab config.

No listener, simulated LDAP server, or arbitrary external target is provided.
This file runs with Kali's existing Python and Impacket, not downloaded copies.
"""
import json
import os
from pathlib import Path
import socket
import signal
import ssl
import subprocess
import sys
import tempfile


def probe(request):
    mode=request['mode']
    address=request['address']
    host='PF-DC01.pafta.test'
    password=request['password']
    pem=request['ca_pem']
    socket.setdefaulttimeout(10)
    if mode=='starttls':
        with tempfile.TemporaryDirectory(prefix='pafta_ldap_') as folder:
            folder=Path(folder)
            ca=folder/'ca.pem';ca.write_text(pem)
            secret=folder/'password';secret.write_text(password);secret.chmod(0o600)
            env=dict(os.environ,LDAPTLS_CACERT=str(ca),LDAPTLS_REQCERT='demand')
            p=subprocess.run(['ldapsearch','-x','-ZZ','-H','ldap://'+address,'-D','pf_s4u_user@pafta.test','-y',str(secret),'-b','DC=pafta,DC=test',request.get('filter','(sAMAccountName=ali.kaya)'),'sAMAccountName'],capture_output=True,timeout=20,env=env)
            return {'ok':p.returncode==0,'exit':p.returncode,'output':p.stdout.decode('utf8','replace'),'error':p.stderr.decode('utf8','replace'),'client':'OpenLDAP StartTLS'}
    tls=mode not in ('signed','unsigned')
    verified_der=None
    if tls:
        context=ssl.create_default_context()
        if mode!='bad-ca':
            context.load_verify_locations(cadata=pem)
        server_name='wrong.pafta.test' if mode=='bad-name' else host
        try:
            with socket.create_connection((address,636),timeout=10) as raw:
                with context.wrap_socket(raw,server_hostname=server_name) as peer:
                    verified_der=peer.getpeercert(binary_form=True)
        except ssl.SSLCertVerificationError as error:
            return {'ok':False,'category':'certificate','verify_code':error.verify_code,'error':str(error)}
    from impacket.ldap.ldap import LDAPConnection,LDAPSessionError
    from impacket.ldap.ldapasn1 import SearchResultEntry
    # pyOpenSSL's Impacket transport expects blocking sockets. A kernel alarm
    # bounds the ENTIRE fixed-host client, including bind/read, instead.
    socket.setdefaulttimeout(None)
    connection=LDAPConnection(('ldaps://' if tls else 'ldap://')+host,'DC=pafta,DC=test',dstIp=address,signing=(mode=='signed'))
    try:
        if tls:
            # Impacket's transport doesn't validate the CA/name itself. Pin the
            # EXACT leaf from the validated stdlib TLS connection before login.
            from OpenSSL import crypto
            actual=crypto.dump_certificate(crypto.FILETYPE_ASN1,connection._socket.get_peer_certificate())
            if actual!=verified_der:
                raise RuntimeError('LDAP TLS leaf differs from the CA/name-verified certificate.')
            if connection._socket.get_protocol_version_name() not in ('TLSv1.2','TLSv1.3'):
                raise RuntimeError('Lab TLS must use TLS 1.2 or later.')
            if not hasattr(connection,'channel_binding_value'):
                raise RuntimeError('Installed Impacket lacks the lab CBT instrumentation field.')
            if mode=='none':connection.channel_binding_value=None
            elif mode=='wrong':connection.channel_binding_value=b'\0'*16
        connection.login('pf_s4u_user',password,'PAFTA')
        rows=connection.search(searchFilter=request.get('filter','(sAMAccountName=ali.kaya)'),attributes=['sAMAccountName'])
        names=[]
        for row in rows:
            if isinstance(row,SearchResultEntry):
                for attr in row['attributes']:
                    if str(attr['type']).lower()=='samaccountname':
                        names.extend(str(v) for v in attr['vals'])
        return {'ok':True,'names':sorted(names),'client':'Impacket SASL NTLM','tls':tls,'signed':mode=='signed'}
    except LDAPSessionError as error:
        result={'ok':False,'category':'ldap','error':str(error)}
        code=int(error.getErrorCode())
        if code:result['ldap_code']=code
        return result
    finally:
        connection.close()


if __name__=='__main__':
    signal.alarm(30)
    request=json.load(sys.stdin)
    try:
        result=probe(request)
    except Exception as error:
        result={'ok':False,'category':'transport','error':type(error).__name__+': '+str(error)}
    if 'error' in result:
        result['error']=result['error'].replace(request['password'],'[gizli]')
    print(json.dumps(result,ensure_ascii=False))
