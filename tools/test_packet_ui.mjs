import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
import {codeBlock,render,stripAnno,regexParcala,dilAdi} from '../web/md.js';
import {highlightLines,esc} from '../web/hl.js';

function appHarness() {
  const reply={};
  const element=()=>({content:'token',innerHTML:'',classList:{add(){},toggle(){}},
    querySelector(){return element();},querySelectorAll(){return [];}});
  const document={querySelector(){return element();},querySelectorAll(){return [];}};
  let source=readFileSync(new URL('../web/app.js',import.meta.url),'utf8');
  source=source.replace(/^import .*;\r?\n/gm,'').replace(/\bboot\(\);\s*$/,'');
  const app=runInNewContext(source+'\napi=async()=>packetApiResult;\n({Bench,firstCode,lessonLanguage,TAHMIN_DIL,S,sheetClick});',
    {document,render,codeBlock,stripAnno,regexParcala,dilAdi,esc,console,setTimeout,clearTimeout,packetApiResult:reply});
  return {...app,reply};
}

test('real packet CLI fences are runnable and populate the editor',()=>{
  const app=appHarness();
  for(const [language,source] of [['tshark','tshark -r secili -q -z io,phs'],
    ['tcpdump-lab','tcpdump -i lo -nn -s 64 -c 3 -w sonuc.pcap udp']]) {
    const html=codeBlock(source,language,{dil:language});
    assert.ok(html.includes('data-act="run"'));
    assert.ok(html.includes('data-act="bench"'));
    assert.equal(app.firstCode('```'+language+'\n'+source+'\n```',language).code.trim(),source);
    assert.equal(app.lessonLanguage({dil:'packets'},{steps:[]},{meta:{dil:language}}),language);
    assert.ok(app.TAHMIN_DIL[language]);
    assert.ok(!codeBlock(source,language,{dil:language,runnable:false,bench:false}).includes('data-act="run"'));
    const encoded=highlightLines(source+' <tag>',language).join('\n');
    assert.ok(!encoded.includes('<tag>'));
  }
});

test('CLI stdout and exported-file tables are both visible and escaped',()=>{
  const app=appHarness();
  for(const dialect of ['tshark','tcpdump-lab']) {
    const pane={innerHTML:''};
    app.Bench.prototype.paintOut.call({pane},{packet_dialect:dialect,packet_backend:'real CLI',
      segs:[['out','Paketler: 3\n<tag>']],tablolar:[{satir:1,sutunlar:['Dosya','Bayt'],satirlar:[['download',13]]}]});
    assert.ok(pane.innerHTML.includes('Paketler: 3'));
    assert.ok(pane.innerHTML.includes('download'));
    assert.ok(pane.innerHTML.includes('real CLI'));
    assert.ok(!pane.innerHTML.includes('<tag>'));
  }
});

test('capture interface identity and exact time fractions remain visible',()=>{
  const app=appHarness(),pane={innerHTML:''};
  app.Bench.prototype.paintOut.call({pane},{packet_ids:[1],packet_dialect:'wireshark',
    segs:[['out','Paketler: 1\n']],tablolar:[],capture_interfaces:[
      {frame:1,section:0,interface:1,linktype:101,timestamp_fraction:'1700000003000000001/1000000000'}]});
  assert.ok(pane.innerHTML.includes('Arayüz ve tam zaman bilgisi'));
  assert.ok(pane.innerHTML.includes('1700000003000000001/1000000000'));
  assert.ok(pane.innerHTML.includes('LINKTYPE'));
});

test('inline narration CLI run preserves stdout alongside exported files',async()=>{
  const app=appHarness();
  app.S.yol={dil:'packets'};app.S.tid='packets';app.S.idx=0;
  app.S.lesson={lesson:{id:'pk28',steps:[{stdin:'{"dil":"tshark","kayit":"olay"}'}]}};
  app.S.bench={stdin:{value:'{"dil":"tshark","kayit":"olay"}'}};
  Object.assign(app.reply,{packet_backend:'TShark CLI',packet_dialect:'tshark',
    segs:[['out','native hierarchy output']],tablolar:[{sutunlar:['Dosya'],satirlar:[['download']]}]});
  const out={innerHTML:'',classList:{add(){}}};
  const block={dataset:{src:'tshark -r secili -q -z io,phs'},querySelector(){return out;}};
  const button={dataset:{act:'run'},closest(){return block;}};
  await app.sheetClick({target:{closest(selector){return selector==='[data-act]'?button:null;}}});
  assert.ok(out.innerHTML.includes('native hierarchy output'));
  assert.ok(out.innerHTML.includes('download'));
});
