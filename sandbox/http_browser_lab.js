// Real browser acceptance. No --disable-web-security or global TLS bypass.
const fs = require('fs');
const path = require('path');
async function main() {
  const config = JSON.parse(fs.readFileSync(0, 'utf8'));
  const {chromium} = require(config.module);
  const browser = await chromium.launch({executablePath: config.browser, headless:true,
    args:['--no-proxy-server', '--host-resolver-rules=MAP *.pafta.test 127.0.0.1, MAP *.other.test 127.0.0.1']});
  try {
    const context = await browser.newContext();
    const page = await context.newPage();
    page.setDefaultTimeout(8000);
    const results = [];
    if (config.mode === 'cors') {
      for (const c of config.cases) {
        await page.goto(c.source);
        const result = await page.evaluate(async c => {
          try {
            const r=await fetch(c.url, {method:c.method,headers:c.headers,credentials:c.credentials||'omit',body:c.body});
            return {readable:true,status:r.status,body:await r.json()};
          } catch (e) {return {readable:false,error:e.name};}
        }, c);
        results.push(result);
      }
    } else if(config.mode === 'samesite') {
      for(const method of ['GET','POST']) {
        await context.clearCookies();
        await page.goto(config.app+'/cookie/set');
        await page.goto(config.other);
        await Promise.all([page.waitForURL(u=>u.origin===new URL(config.app).origin && u.pathname==='/cookie/check'),page.evaluate(({url,method})=>{
          const form=document.createElement('form');form.action=url;form.method=method;document.body.appendChild(form);form.submit();
        },{url:config.app+'/cookie/check',method})]);
        results.push(JSON.parse(await page.locator('body').innerText()));
      }
    } else if(config.mode === 'ws') {
      await context.addCookies([{name:'sid',value:config.cookie.split('=')[1],url:config.source}]);
      await page.goto(config.source);
      results.push(await page.evaluate(({url,text})=>new Promise((resolve,reject)=>{
        const ws=new WebSocket(url);let received;
        ws.onopen=()=>ws.send(text);
        ws.onmessage=e=>received=e.data;
        ws.onerror=()=>reject(Error('WebSocket failed'));
        ws.onclose=e=>resolve({text:received,code:e.code});
      }),config));
    } else if(config.mode === 'url') {
      for(const url of config.urls) {
        results.push(await page.evaluate(url=>{try{const u=new URL(url);return {host:u.hostname,scheme:u.protocol,path:u.pathname};}catch{return null;}},url));
      }
    } else throw Error('unsupported browser experiment');
    process.stdout.write(JSON.stringify({browser:await browser.version(),results}));
  } finally {await browser.close();}
}
main().catch(e=>{process.stderr.write(String(e));process.exitCode=1;});
