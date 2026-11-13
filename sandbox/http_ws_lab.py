"""RFC6455 bounded subset: one FIN UTF-8 text message <=125 bytes, then close.

No compression, fragmentation, binary or extended lengths. Unsupported frames
are closed explicitly, never silently interpreted as text. Real TCP framing.
"""
import base64
import hashlib
import secrets
import socket
import struct

GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'


def accept_value(key):
    return base64.b64encode(hashlib.sha1((key+GUID).encode('ascii')).digest()).decode('ascii')


def exact(stream, n):
    data=b''
    while len(data)<n:
        part=stream.read(n-len(data))
        if not part: raise EOFError('incomplete WebSocket frame')
        data+=part
    return data


def serve(h):
    lab=h.server.lab
    with lab.lock:
        s=h.session()
        lab.events.append({'method':h.command,'path':'/ws','user':s['user'] if s else None})
    if not s: return h.reply(401,{'error':'session'})
    if h.headers.get('Origin')!=lab.origin: return h.reply(403,{'error':'origin'})
    key=h.headers.get('Sec-WebSocket-Key','')
    try:
        validkey=len(base64.b64decode(key,validate=True))==16
    except ValueError:
        validkey=False
    if (h.command!='GET' or h.headers.get('Upgrade','').lower()!='websocket'
        or 'upgrade' not in {v.strip().lower() for v in h.headers.get('Connection','').split(',')}
        or h.headers.get('Sec-WebSocket-Version')!='13' or not validkey):
        return h.reply(400,{'error':'WebSocket version 13 handshake required'})
    h.send_response(101)
    h.send_header('Upgrade','websocket')
    h.send_header('Connection','Upgrade')
    h.send_header('Sec-WebSocket-Accept',accept_value(key))
    h.end_headers()
    h.wfile.flush()
    h.close_connection=True
    h.connection.settimeout(3)
    def close(code):
        h.wfile.write(b'\x88\x02'+struct.pack('!H',code)); h.wfile.flush()
    try:
        a,b=exact(h.rfile,2)
        if a&0x70 or not b&0x80:
            return close(1002)
        if not a&0x80 or a&0x0f!=1:
            return close(1003)
        n=b&0x7f
        if n>=126:
            return close(1009)
        mask=exact(h.rfile,4)
        data=exact(h.rfile,n)
        data=bytes(v^mask[i%4] for i,v in enumerate(data))
        try: data.decode('utf-8')
        except UnicodeError: return close(1007)
        h.wfile.write(bytes([0x81,len(data)])+data); h.wfile.flush()
        close(1000)
    except (EOFError,OSError):
        return


def exchange(lab,cookie=None,origin=None,text='merhaba',frame=None,key=None,version='13'):
    key=key or base64.b64encode(secrets.token_bytes(16)).decode('ascii')
    headers=[f'GET /ws HTTP/1.1',f'Host: 127.0.0.1:{lab.server.server_port}',
             'Upgrade: websocket','Connection: keep-alive, Upgrade',f'Sec-WebSocket-Version: {version}',
             f'Sec-WebSocket-Key: {key}',f'Origin: {lab.origin if origin is None else origin}']
    if cookie: headers.append('Cookie: '+cookie)
    with socket.create_connection(('127.0.0.1',lab.server.server_port),timeout=4) as sock:
        sock.sendall(('\r\n'.join(headers)+'\r\n\r\n').encode('ascii'))
        with sock.makefile('rb') as stream:
            first=stream.readline().decode('ascii').strip()
            received={}
            while True:
                line=stream.readline()
                if line==b'\r\n': break
                if not line: raise EOFError('incomplete handshake')
                k,_,v=line.decode('ascii').partition(':'); received[k.lower()]=v.strip()
            result={'status':int(first.split()[1]),'headers':received,'key':key}
            if result['status']!=101:
                exact(stream,int(received.get('content-length','0')))
                return result
            if frame is None:
                data=text.encode('utf-8')
                if len(data)>125: raise ValueError('lab supports <=125 byte text')
                mask=secrets.token_bytes(4)
                frame=bytes([0x81,0x80|len(data)])+mask+bytes(v^mask[i%4] for i,v in enumerate(data))
            sock.sendall(frame)
            a,b=exact(stream,2)
            data=exact(stream,b&0x7f)
            result.update(opcode=a&15,text=data.decode('utf-8') if a&15==1 else None,
                          close=struct.unpack('!H',data)[0] if a&15==8 and len(data)==2 else None)
            return result
