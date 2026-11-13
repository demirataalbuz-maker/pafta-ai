// Render contract only; no visual browser or Elasticsearch is used.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";
import { codeBlock, render, stripAnno, regexParcala, dilAdi } from "../web/md.js";
import { highlightLines, esc } from "../web/hl.js";

test("Elastic query fences have native labels and executable controls", () => {
  for (const [language, label] of [["kibana", "KIBANA KQL"], ["lucene", "LUCENE"], ["eql", "ELASTIC EQL"]]) {
    const html = codeBlock('process.name: "cmd.exe"', language, { dil: language });
    assert.ok(html.includes(label));
    assert.ok(!html.includes("OKUMA"));
    assert.ok(html.includes('data-act="run"'));
    assert.ok(html.includes('data-act="bench"'));
    const reading = render("```"+language+' norun\nfield: "value"\n```', { dil: language });
    assert.ok(!reading.includes('data-act="run"'));
  }
});

test("predictions cannot reveal query answers through run controls", () => {
  for (const language of ["kibana", "lucene", "eql"]) {
    const html = codeBlock("field:value", language, { dil: language, runnable:false, bench:false });
    assert.ok(!html.includes('data-act="run"'));
    assert.ok(!html.includes('data-act="bench"'));
  }
});

test("query highlighting preserves and escapes source text", () => {
  const source = 'field: "<img src=x>" AND amount >= 1024\nNOT field: *';
  for (const language of ["kibana", "lucene", "eql", "elastic"]) {
    const html = highlightLines(source, language).join("\n");
    assert.ok(!html.includes("<img"));
    const plain = html.replace(/<span class="tok-[^"]+">/g, "").replace(/<\/span>/g, "")
      .replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&amp;/g, "&");
    assert.equal(plain, source);
  }
});


function appHarness() {
  const nodes = new Map();
  function element() {
    const children = new Map();
    return {
      content: "test-token", innerHTML: "", textContent: "", value: "", hidden: false,
      classList: { add() {}, toggle() {} },
      querySelector(selector) {
        if (!children.has(selector)) children.set(selector, element());
        return children.get(selector);
      },
      querySelectorAll() { return []; },
      insertAdjacentHTML(position, html) { this.innerHTML += html; },
    };
  }
  const document = {
    querySelector(selector) {
      if (!nodes.has(selector)) nodes.set(selector, element());
      return nodes.get(selector);
    },
    querySelectorAll() { return []; },
  };
  const requests = [], loads = [], languages = [];
  const response = {};
  let source = readFileSync(new URL("../web/app.js", import.meta.url), "utf8");
  source = source.replace(/^import .*;\r?\n/gm, "").replace(/\bboot\(\);\s*$/, "");
  const exposed = runInNewContext(source + `
    api = async (path, body) => { requests.push({path, body}); return apiResult; };
    paintDims = paintFoot = paintTaskStatus = stamp = toast = () => {};
    refreshHeader = async () => ({});
    globalThis.testApi = { S, Bench, lessonLanguage, lessonInput, elasticOutput, TAHMIN_DIL,
      showStep, sheetClick, TEZGAH_DILLER, TEZGAH_ORNEK, TEZGAH_METIN };
    testApi;
  `, { document, render, codeBlock, stripAnno, regexParcala, dilAdi, esc,
    requests, apiResult: response, console, setTimeout, clearTimeout,
    location: { hash: "" }, history: { replaceState() {} } });
  exposed.S.bench = {
    stdin: { value: "" },
    draft: { bosalt() {} },
    ayarla(language) { languages.push(language); },
    load(value) { loads.push(value); },
    setCode(value) { this.code = value; },
    setStdin(value) { this.stdin.value = value; },
  };
  return { ...exposed, nodes, document, requests, loads, languages, element, response };
}

function selectLesson(app, dialect, kind="anlat", input='{"dil":"'+dialect+'","mapping":{},"documents":[]}') {
  const query = dialect === "eql" ? 'process where process.name == "cmd.exe"' : 'user.name: "alice"';
  const step = { kind, meta: { dil: dialect }, body: "```"+dialect+"\n"+query+"\n```", stdin: input,
    code: query, code_dil: dialect, starter: "starter-query", hints: [], has_solution: false };
  app.S.yol = { dil: "elastic", ozellik: {} };
  app.S.mode = "lesson";
  app.S.tid = "elastic";
  app.S.idx = 0;
  app.S.lesson = { lesson: { id: "el01", steps: [step] }, progress: { steps: {}, drafts: {} } };
  return { query, step, input };
}

test("lesson dialect is selected from step metadata with a first-step fallback", () => {
  const app = appHarness();
  for (const dialect of ["kibana", "lucene", "eql"]) {
    const lesson = { steps: [{ kind: "anlat", meta: {} }, { meta: { dil: dialect } }] };
    assert.equal(app.lessonLanguage({dil:"elastic"}, lesson, lesson.steps[0]), dialect);
    assert.equal(app.lessonLanguage({dil:"elastic"}, lesson, {meta:{dil:"lucene"}}), "lucene");
  }
  assert.equal(app.lessonLanguage({dil:"packets"}, {steps:[]}, {}), "wireshark");
  assert.equal(app.lessonLanguage({dil:"python",okuma_dili:"java"}, {steps:[{meta:{dil:"java"}}]}, {}), "python");
  const source = readFileSync(new URL("../web/app.js", import.meta.url), "utf8");
  assert.ok(!source.includes("ELASTIC_OKUMA_BOS"));
  assert.ok(!source.includes("Elastic okuma yolu"));
});

test("all Elastic dialects show a corpus JSON editor, preserving Kusto input behavior", () => {
  const app = appHarness();
  const bench = { host: app.element(), ed: {}, stdin: {}, stdinBox: {hidden:true}, toggleStdin: app.Bench.prototype.toggleStdin };
  for (const language of ["kibana", "lucene", "eql", "elastic"]) {
    app.Bench.prototype.ayarla.call(bench, language, {});
    assert.equal(bench.stdinBox.hidden, false);
    assert.equal(bench.host.querySelector('[data-b="stdin"]').hidden, false);
    assert.match(bench.host.querySelector(".stdin-box .label").textContent, /korpus.*JSON/i);
    assert.ok(bench.stdin.rows >= 8);
    assert.equal(bench.girdiAdi, "Korpus JSON");
    assert.equal(bench.ed.dil, language);
  }
  app.Bench.prototype.ayarla.call(bench, "kql", {dis:"SQL"});
  assert.equal(bench.stdinBox.hidden, true);
  assert.equal(bench.host.querySelector('[data-b="stdin"]').hidden, true);
  assert.equal(bench.host.querySelector('[data-b="dis"]').textContent, "SQL");
});

test("inline query blocks retain exactly their corpus JSON", () => {
  const input = JSON.stringify({dil:"kibana",documents:[{id:'a<&"',message:"line\nnext"}]});
  const html = render('```kibana\nmessage: "hello"\n```', {dil:"kibana",stdin:input});
  const attribute = html.match(/data-stdin="([^"]*)"/)[1];
  const decoded = attribute.replace(/&quot;/g,'"').replace(/&lt;/g,"<").replace(/&gt;/g,">").replace(/&amp;/g,"&");
  assert.equal(decoded, input);
  assert.ok(!html.includes('<&"'));
  const app = appHarness();
  assert.equal(app.lessonInput({}, {steps:[{stdin:input}]}, "kibana"), input);
  assert.equal(app.lessonInput({stdin:"own"}, {steps:[{stdin:input}]}, "lucene"), "own");
});

test("anlat loads its real query and inherited corpus with the correct language", () => {
  const app = appHarness();
  const {query,step,input} = selectLesson(app,"lucene");
  step.meta = {};
  delete step.stdin;
  app.S.lesson.lesson.steps.push({meta:{dil:"lucene"},stdin:input});
  app.showStep(0);
  assert.equal(app.languages.at(-1), "lucene");
  assert.equal(app.loads.at(-1).code.trimEnd(), query);
  assert.equal(app.loads.at(-1).stdin, input);
  const html = app.document.querySelector("#stepBody").innerHTML;
  assert.ok(html.includes('data-act="run"'));
  assert.ok(html.includes('data-stdin="{&quot;dil&quot;:&quot;lucene&quot;'));
  assert.ok(!html.includes("Okuma alıştırması"));
});

test("Elastic predictions use raw ID/sequence guidance and keep the editor empty", () => {
  for (const dialect of ["kibana", "lucene", "eql"]) {
    const app = appHarness();
    const {step,input} = selectLesson(app,dialect,"tahmin");
    step.body="Sorguyu ve veriyi oku.\n???\nAçıklama.";
    app.showStep(0);
    assert.equal(app.loads.at(-1).code, "");
    assert.equal(app.loads.at(-1).resetCode, "");
    assert.equal(app.loads.at(-1).stdin, input);
    const html = app.document.querySelector("#stepBody").innerHTML;
    assert.ok(!html.includes('data-act="run"'));
    assert.ok(!html.includes('data-act="bench"'));
    assert.equal(app.TAHMIN_DIL[dialect].kod, "");
    assert.match(app.TAHMIN_DIL[dialect].etiket, dialect==="eql" ? /e1 -> e2/ : /her satıra bir tane/);
  }
});

test("inline run uses the lesson corpus instead of unrelated workbench edits", async () => {
  const app = appHarness();
  const {step,input} = selectLesson(app,"kibana");
  app.S.bench.stdin.value = "unrelated";
  const block = app.element();
  block.dataset = {src:'user.name: "alice"',stdin:""};
  const action = {dataset:{act:"run"},closest(selector) { return selector===".code" ? block : null; }};
  await app.sheetClick({target:{closest(selector){return selector==="[data-act]" ? action : null;}}});
  assert.equal(app.requests.at(-1).path, "/api/run");
  assert.equal(app.requests.at(-1).body.stdin,input);
  assert.equal(app.requests.at(-1).body.track,"elastic");
  assert.equal(app.requests.at(-1).body.step,0);
  delete step.stdin;
  app.S.lesson.lesson.steps.push({meta:{dil:"kibana"},stdin:input});
  action.dataset.act="bench";
  await app.sheetClick({target:{closest(selector){return selector==="[data-act]" ? action : null;}}});
  assert.equal(app.S.bench.stdin.value,input);
});

test("Elastic result metadata and sequence arrows are escaped and rendered", () => {
  const app = appHarness();
  const result={elastic_ids:[["a","b"]],elastic_dialect:"eql",elastic_backend:"Pafta <bounded>",
    segs:[["out","a -> b\n"]],tablolar:[{sutunlar:["Olay dizisi"],satirlar:[["a -> b"]]}]};
  const bench={pane:{},ed:{mark(){throw new Error("unexpected marker");}}};
  app.Bench.prototype.paintOut.call(bench,result);
  assert.ok(bench.pane.innerHTML.includes("a -&gt; b"));
  assert.ok(bench.pane.innerHTML.includes("Elastic EQL"));
  assert.ok(bench.pane.innerHTML.includes("Pafta &lt;bounded&gt;"));
  assert.ok(bench.pane.innerHTML.includes("1 eşleşen dizi"));
  assert.ok(!bench.pane.innerHTML.includes("<bounded>"));
  result.elastic_ids=[];
  result.segs=[];
  result.tablolar=[];
  assert.ok(app.elasticOutput(result).includes("0 eşleşen belge"));
});

test("Elastic freeplay has a query and editable valid corpus demo", () => {
  const app=appHarness();
  assert.ok(app.TEZGAH_DILLER.some(([language,label])=>language==="elastic"&&label==="Elastic / Kibana"));
  assert.equal(app.TEZGAH_ORNEK.elastic,"event.dataset: auth AND user.name: alice");
  const config=JSON.parse(app.TEZGAH_METIN.elastic);
  assert.equal(config.dil,"kibana");
  assert.deepEqual(config.documents.filter(doc=>doc["event.dataset"]==="auth"&&doc["user.name"]==="alice").map(doc=>doc.id),["a","d"]);
  assert.ok(config.mapping["user.name"]);
  assert.ok(config.context);
});


test("submitting a query prediction unlocks the query with its exact corpus", async () => {
  const app=appHarness();
  const {query,input}=selectLesson(app,"eql","tahmin");
  app.document.querySelector("#guessBox").value="a -> b";
  Object.assign(app.response,{correct:true,result:{segs:[["out","a -> b\n"]]}});
  const action={dataset:{act:"guess"}};
  await app.sheetClick({target:{closest(selector){return selector==="[data-act]" ? action : null;}}});
  assert.equal(app.requests.at(-1).path,"/api/guess");
  assert.equal(app.requests.at(-1).body.guess,"a -> b");
  assert.equal(app.loads.at(-1).code,query);
  assert.equal(app.loads.at(-1).resetCode,query);
  assert.equal(app.loads.at(-1).stdin,input);
  assert.equal(app.S.lesson.progress.steps[0].guess_ok,true);
  assert.ok(app.document.querySelector("#guessResult").innerHTML.includes("a -&gt; b"));
});

test("revealed solutions use the actual step dialect and corpus", async () => {
  for (const dialect of ["kibana","lucene","eql"]) {
    const app=appHarness();
    const {query,input}=selectLesson(app,dialect,"gorev");
    app.S.lesson.progress.steps[0]={attempts:2};
    app.response.solution=query;
    const action={dataset:{act:"solution"}};
    await app.sheetClick({target:{closest(selector){return selector==="[data-act]" ? action : null;}}});
    const html=app.document.querySelector("#solution").innerHTML;
    assert.ok(html.includes('data-act="run"'));
    assert.ok(!html.includes("OKUMA"));
    assert.ok(html.includes(dialect==="kibana" ? "KIBANA KQL" : dialect==="lucene" ? "LUCENE" : "ELASTIC EQL"));
    const attribute=html.match(/data-stdin="([^"]*)"/)[1];
    const decoded=attribute.replace(/&quot;/g,'"').replace(/&lt;/g,"<").replace(/&gt;/g,">").replace(/&amp;/g,"&");
    assert.equal(decoded,input);
  }
});


test("advanced native dialects preserve JSON input and never expose guesses early", () => {
  for (const language of ["esql", "ingest", "rule"]) {
    const app=appHarness();
    const input=JSON.stringify({backend:"elastic",dil:language,mapping:{n:"long"},documents:[]});
    const html=codeBlock("<tag>",language,{dil:language,stdin:input});
    assert.ok(html.includes('data-act="run"'));
    assert.ok(html.includes('data-stdin='));
    assert.ok(!html.includes("<tag>"));
    const hidden=codeBlock("answer",language,{dil:language,runnable:false,bench:false});
    assert.ok(!hidden.includes('data-act="run"'));
    assert.ok(!hidden.includes('data-act="bench"'));
    const {query}=selectLesson(app,language,"tahmin",input);
    app.showStep(0);
    assert.equal(app.loads.at(-1).resetCode,"");
    assert.notEqual(app.loads.at(-1).code,query);
    assert.equal(app.loads.at(-1).stdin,input);
    assert.equal(app.TAHMIN_DIL[language].kod,"");
    assert.equal(app.lessonLanguage({dil:"elastic"},{steps:[]},{meta:{dil:language}}),language);
  }
});

test("native Elastic JSON and tables both remain visible, with escaped backend", () => {
  const app=appHarness();
  const bench={pane:{},ed:{mark(){}}};
  app.Bench.prototype.paintOut.call(bench,{elastic_native:true,elastic_backend:"Elastic <native>",
    segs:[["out",'{"preview_count":2}']],tablolar:[{sutunlar:["n"],satirlar:[[2]]}]});
  assert.ok(bench.pane.innerHTML.includes("preview_count"));
  assert.ok(bench.pane.innerHTML.includes("<table"));
  assert.ok(bench.pane.innerHTML.includes("Elastic &lt;native&gt;"));
});
