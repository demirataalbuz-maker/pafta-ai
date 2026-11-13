"""Real Edge/Chromium experiments using existing Playwright, never downloads."""
from pathlib import Path
import glob
import json
import os
import shutil
import signal
import subprocess
from http_lab import Lab


def browser_run(config):
    root = Path(__file__).resolve().parents[1]
    bundles = sorted(glob.glob(str(Path.home()/'.cache/codex-runtimes/*/dependencies/node')), reverse=True)
    node = os.environ.get('PAFTA_HTTP_NODE') or shutil.which('node')
    module = os.environ.get('PAFTA_HTTP_PLAYWRIGHT')
    if not module and (root/'.deps/npm/node_modules/playwright-core').is_dir():
        module = str(root/'.deps/npm/node_modules/playwright-core')
    for folder in bundles:
        if not module and (Path(folder)/'node_modules/playwright-core').is_dir():
            module = str(Path(folder)/'node_modules/playwright-core')
        if not node and (Path(folder)/'bin/node.exe').is_file():
            node = str(Path(folder)/'bin/node.exe')
    browser = os.environ.get('PAFTA_HTTP_BROWSER') or next((p for p in (
        r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
        r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
        shutil.which('chromium'), shutil.which('google-chrome')) if p and Path(p).is_file()), None)
    if not node or not module or not browser:
        raise RuntimeError('Real browser lab requires Node + playwright-core + Edge/Chromium. See docs/http-lab.md; nothing is installed automatically.')
    config = dict(config, module=module, browser=browser)
    p = subprocess.Popen([node, str(Path(__file__).with_suffix('.js'))], stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',
                         start_new_session=os.name!='nt',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        stdout,stderr=p.communicate(json.dumps(config),timeout=35)
    except subprocess.TimeoutExpired as exc:
        if os.name=='nt':
            subprocess.run(['taskkill','/F','/T','/PID',str(p.pid)],capture_output=True,
                           creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        else:
            os.killpg(p.pid,signal.SIGKILL)
        p.communicate(timeout=4)
        raise RuntimeError('Browser lab timed out; process tree closed') from exc
    if p.returncode:
        raise RuntimeError('Browser lab failed: '+stderr[-1200:])
    return json.loads(stdout)


def cors_report():
    with Lab() as source, Lab() as target, Lab() as denied, Lab() as wildcard:
        target.origin = source.base
        wildcard.cors_wildcard = True
        cases = [
            {'source':source.base,'url':target.base+'/cors','method':'GET','headers':{}},
            {'source':source.base,'url':target.base+'/cors','method':'POST','headers':{'Content-Type':'application/json','X-Pafta':'yes'},'body':'{}','credentials':'include'},
            {'source':denied.base,'url':target.base+'/cors','method':'POST','headers':{'X-Pafta':'yes'},'body':'{}'},
            {'source':denied.base,'url':target.base+'/cors','method':'GET','headers':{}},
            {'source':source.base,'url':wildcard.base+'/cors','method':'GET','headers':{},'credentials':'include'},
        ]
        report = browser_run({'mode':'cors','cases':cases})
        report['target_events'] = target.snapshot()['events']
        report['wildcard_events'] = wildcard.snapshot()['events']
        return report


def samesite_report():
    with Lab() as lab:
        port = lab.server.server_port
        return browser_run({'mode':'samesite','app':f'http://app.pafta.test:{port}',
                            'other':f'http://evil.other.test:{port}'})
