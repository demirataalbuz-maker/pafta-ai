import traceback
from pathlib import Path
def main():
    """Own single-container local OIDC + official Fulcio supervisor; no production identities."""
    import functools,http.server,json,os,shutil,signal,subprocess,threading,time
    from pathlib import Path
    SOURCE=Path('/opt/pafta-s36');WORK=Path('/tmp/pafta-s36');WORK.mkdir(parents=True,exist_ok=True)
    class Issuer(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            routes={'/.well-known/openid-configuration':'discovery.json','/jwks':'jwks.json'}
            name=routes.get(self.path)
            if name is None:self.send_error(404);return
            content=(SOURCE/name).read_bytes();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(content)));self.end_headers();self.wfile.write(content)
        def log_message(self,*args):pass  # Do not put tokens/claims in process logs.
    oidc=http.server.ThreadingHTTPServer(('127.0.0.1',5556),Issuer)
    threading.Thread(target=oidc.serve_forever,daemon=True).start()
    binary=WORK/'fulcio';shutil.copyfile(SOURCE/'fulcio',binary);binary.chmod(0o500)
    child=subprocess.Popen([str(binary),'serve','--ca=ephemeralca','--config-path=/opt/pafta-s36/fulcio.json','--ct-log-url=','--host=0.0.0.0','--port=5555','--grpc-host=127.0.0.1','--grpc-port=5557','--metrics-port=5558'],stdout=(WORK/'fulcio.stdout').open('w'),stderr=(WORK/'fulcio.stderr').open('w'))
    stop=threading.Event()
    def halted(*args):stop.set()
    signal.signal(signal.SIGTERM,halted);signal.signal(signal.SIGINT,halted)
    try:
        while child.poll() is None and not stop.wait(.2):pass
    finally:
        if child.poll() is None:
            child.terminate()
            try:child.wait(timeout=4)
            except subprocess.TimeoutExpired:child.kill();child.wait(timeout=4)
        oidc.shutdown();oidc.server_close()
    if child.returncode not in (0,-15):raise SystemExit('Fulcio exited '+str(child.returncode))
try:main()
except BaseException:
    Path('/tmp/pafta-s36/supervisor.error').write_text(traceback.format_exc())
    raise
