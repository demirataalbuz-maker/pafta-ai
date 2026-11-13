// Küçük markdown çizici: ders metinleri, ölçü notlu kod blokları ve uyarı kutuları.
import { esc, highlightLines } from "./hl.js";
import katex from "./vendor/katex/katex.mjs";

const CALLOUTS = {
  "NOT": ["not", "Not"], "TUZAK": ["tuzak", "Tuzak"], "DERİN": ["derin", "Derin su · tanrı seviyesi"],
  "DERIN": ["derin", "Derin su · tanrı seviyesi"], "GÜVENLİK": ["guvenlik", "Güvenlik gözüyle"],
  "GUVENLIK": ["guvenlik", "Güvenlik gözüyle"], "ZEN": ["zen", "Python'un Zen'i"],
  "İPUCU": ["ipucu", "İpucu"], "IPUCU": ["ipucu", "İpucu"],
};

function attr(s) {
  return esc(s).replace(/"/g, "&quot;");
}

// Formül çizimi yalnız formül kullanan yollarda açılır (AI ve kuantum). Diğer yollarda `$` düz metindir:
// Bash ve PowerShell derslerindeki `$HOME`, `$_` gibi anlatımlar formül sanılmasın.
let matematikAcik = false;
export function matematikAc(acik) { matematikAcik = !!acik; }

export function formul(kaynak, blok = false) {
  try {
    return katex.renderToString(kaynak.trim(), { displayMode: blok, throwOnError: false, strict: "ignore", trust: false });
  } catch (e) {
    return `<code class="formul-hata" title="${attr(String(e.message || e))}">${esc(kaynak)}</code>`;
  }
}

export function inline(s) {
  const codes = [], formuller = [];
  // Kod parçaları ve formüller ham metinden ayrılır; içlerindeki `*`, `_`, `<` Markdown'a ve esc'e girmez.
  // `` `ad` `` biçimi: içinde ters tırnak geçen kod (Markdown'daki gibi, kenar boşlukları atılır)
  s = String(s ?? "").replace(/``\s?(.+?)\s?``|`([^`]+)`/g, (_, cift, tek) => {
    codes.push(esc(cift !== undefined ? cift : tek)); return `\u0000${codes.length - 1}\u0000`;
  });
  if (matematikAcik) {
    const sakla = (kaynak, blok) => { formuller.push(formul(kaynak, blok)); return `\u0001${formuller.length - 1}\u0001`; };
    s = s.replace(/\$\$([^$]+?)\$\$/g, (_, k) => sakla(k, true))
      .replace(/\\\((.+?)\\\)/g, (_, k) => sakla(k, false))  // LaTeX'in `\( ... \)` yazımı
      // Satır içi: `$` hemen ardından boşluk gelmez, kapanıştan önce boşluk olmaz, kapanışın ardından rakam gelmez ("$5 ile $10" formül değildir).
      .replace(/\$(?![\s$])([^$\n]+?)(?<!\s)\$(?!\d)/g, (_, k) => sakla(k, false));
  }
  s = esc(s)
    .replace(/\*\*(?!\s)([^*]+?)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^\w*])\*(?!\s)([^*\n]+?)\*(?!\w)/g, "$1<em>$2</em>")
    .replace(/==(?!\s)([^=]+?)==/g, "<mark>$1</mark>")
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  return s.replace(/\u0000(\d+)\u0000/g, (_, i) => `<code>${codes[+i]}</code>`)
    .replace(/\u0001(\d+)\u0001/g, (_, i) => formuller[+i]);
}

// Kod satırını kod + ölçü notuna ayır: `x = 1  #! not` (`#!/bin/bash` gibi shebang'ler not değildir)
function splitAnno(line) {
  const m = line.match(/(^|\s)#!(?!\/)\s?(.*)$/);
  if (!m) return [line, null];
  return [line.slice(0, m.index).replace(/\s+$/, ""), m[2]];
}

const DIL_ADI = { py: "python", sh: "bash", ps: "powershell", ps1: "powershell", sqlite: "sql", kusto: "kql", splunk: "spl", js: "javascript", bat: "cmd", batch: "cmd", cs: "csharp", x86: "asm", ldap: "ad" };
export const dilAdi = d => DIL_ADI[d] || d;

// Regex blokları: desen, `---` satırı, aranacak metin
export function regexParcala(src) {
  const satirlar = src.split("\n");
  const i = satirlar.findIndex(l => l.trim() === "---");
  return i < 0 ? [src, ""] : [satirlar.slice(0, i).join("\n"), satirlar.slice(i + 1).join("\n")];
}

export function stripAnno(src) {
  return src.split("\n").map(l => {
    const [code, note] = splitAnno(l);
    return note !== null && !code.trim() ? null : code;
  }).filter(l => l !== null).join("\n");
}

export function codeBlock(src, info = "python", opts = {}) {
  const lang = dilAdi((info || "python").split(/\s+/)[0] || "python");
  const flags = (info || "").split(/\s+/).slice(1);
  const kodDili = ["python", "bash", "powershell", "regex", "sql", "kql", "spl", "javascript", "c", "php", "java", "csharp", "asm", "ad", "sigma", "yara", "kibana", "lucene", "eql", "esql", "ingest", "rule", "elastic", "cmd", "wireshark", "bpf", "packets", "tshark", "tcpdump-lab"].includes(lang);
  const izDili = dilAdi(opts.dil || "python");
  const runnable = lang === izDili && !flags.includes("norun") && opts.runnable !== false;
  let desen = src, metin = "";
  if (lang === "regex") [desen, metin] = regexParcala(src);
  else if (["kibana", "lucene", "eql", "esql", "ingest", "rule", "elastic"].includes(lang)) metin = opts.stdin || "";
  const notlu = kodDili && lang !== "regex";
  const raw = notlu ? stripAnno(desen) : desen;
  const rows = desen.split("\n").map(l => (notlu ? splitAnno(l) : [l, null]));
  const codeOnly = rows.map(r => r[0]).join("\n");
  const hl = kodDili ? highlightLines(codeOnly, lang) : codeOnly.split("\n").map(esc);
  const body = rows.map(([, note], i) => {
    const an = note !== null ? `<span class="an"><span>${inline(note)}</span></span>` : "<span></span>";
    return `<div class="cl"><span class="cc">${hl[i] || " "}</span>${an}</div>`;
  }).join("");
  const label = { python: "PYTHON", cikti: "ÇIKTI", text: "METİN", bash: "BASH", powershell: "POWERSHELL", regex: "DESEN", sql: "SQL", kql: "KQL", spl: "SPL", javascript: "JAVASCRIPT", c: "C", php: "PHP", java: "JAVA", csharp: "C#", asm: "ASSEMBLY", ad: "AD / LDAP", kibana: "KIBANA KQL", lucene: "LUCENE", eql: "ELASTIC EQL", esql: "ES|QL", ingest: "INGEST JSON", rule: "SECURITY RULE JSON", elastic: "ELASTIC" }[lang] || lang.toUpperCase();
  const btns = runnable
    ? `<button type="button" data-act="run">▶ Çalıştır</button><button type="button" data-act="bench">⇢ Tezgaha al</button>`
    : (lang === izDili && opts.bench !== false ? `<button type="button" data-act="bench">⇢ Tezgaha al</button>` : "");
  const cls = lang === "cikti" ? "code cikti" : "code";
  const metinHtml = lang === "regex" && metin
    ? `<div class="code-metin"><span class="label">metin</span><pre>${esc(metin)}</pre></div>` : "";
  return `<div class="${cls}" data-src="${attr(raw)}" data-stdin="${attr(metin)}"><div class="code-bar"><span class="label">${label}</span>${btns}</div>` +
    `<pre>${body}</pre>${metinHtml}<div class="run-out" hidden></div></div>`;
}

export function render(md, opts = {}) {
  const lines = (md || "").replace(/\r\n/g, "\n").split("\n");
  const out = [];
  let i = 0;
  const para = [];
  const flush = () => {
    if (para.length) { out.push(`<p>${inline(para.join(" "))}</p>`); para.length = 0; }
  };
  while (i < lines.length) {
    const line = lines[i];
    const fence = line.match(/^```\s*(.*)$/);
    if (fence) {
      flush();
      const buf = [];
      i++;
      while (i < lines.length && !lines[i].startsWith("```")) buf.push(lines[i++]);
      i++;
      out.push(codeBlock(buf.join("\n"), fence[1] || "python", opts));
      continue;
    }
    if (!line.trim()) { flush(); i++; continue; }
    const acan = matematikAcik && (line.trim().startsWith("$$") ? "$$" : line.trim().startsWith("\\[") ? "\\[" : "");
    if (acan) {
      // Blok formül: tek satırda `$$ ... $$` ya da `$$` ile açılıp sonraki bir satırda `$$` ile kapanan.
      // Üç eski ders LaTeX'in `\[ ... \]` yazımını kullanıyor; o da aynı yoldan çizilir.
      const kapatan = acan === "$$" ? "$$" : "\\]";
      const buf = [];
      let govde = line.trim().slice(2), kapandi = false;
      for (;;) {
        const son = govde.indexOf(kapatan);
        // Kapanışın ardından yazı varsa bu bir paragraf içi formüldür; satır içi çizici halleder.
        if (son !== -1) { kapandi = !govde.slice(son + 2).trim(); buf.push(govde.slice(0, son)); break; }
        buf.push(govde);
        if (i + buf.length >= lines.length) break;
        govde = lines[i + buf.length];
      }
      if (kapandi) {
        flush();
        out.push(`<div class="formul-blok">${formul(buf.join("\n"), true)}</div>`);
        i += buf.length;
        continue;
      }
      // Kapanmayan `$$`: satır olduğu gibi aşağıdaki kurallara bırakılır.
    }
    const h = line.match(/^(#{2,4})\s+(.*)$/);
    if (h) { flush(); out.push(`<h${h[1].length}>${inline(h[2])}</h${h[1].length}>`); i++; continue; }
    if (/^(-{3,}|\*{3,})\s*$/.test(line)) { flush(); out.push("<hr>"); i++; continue; }
    if (line.startsWith(">")) {
      flush();
      const buf = [];
      while (i < lines.length && lines[i].startsWith(">")) buf.push(lines[i++].replace(/^>\s?/, ""));
      const c = buf[0] && buf[0].match(/^\[!([^\]]+)\]\s*(.*)$/);
      if (c) {
        const key = c[1].toLocaleUpperCase("tr");
        const [cls, title] = CALLOUTS[key] || ["not", c[1]];
        out.push(`<div class="callout ${cls}"><div class="ct">${inline(c[2] || title)}</div>${render(buf.slice(1).join("\n"), opts)}</div>`);
      } else {
        out.push(`<div class="callout">${render(buf.join("\n"), opts)}</div>`);
      }
      continue;
    }
    if (line.startsWith("|")) {
      flush();
      const rows = [];
      while (i < lines.length && lines[i].startsWith("|")) rows.push(lines[i++]);
      // Formül içindeki `|` (mutlak değer, koşullu olasılık) sütun ayırıcı sayılmasın.
      const koru = r => matematikAcik ? r.replace(/\$(?![\s$])([^$\n]+?)(?<!\s)\$(?!\d)/g, m => m.replace(/\|/g, "\u0002")) : r;
      const cells = r => koru(r).replace(/^\||\|\s*$/g, "").split(/(?<!\\)\|/).map(c => inline(c.trim().replace(/\\\|/g, "|").replace(/\u0002/g, "|")));
      const head = cells(rows[0]);
      const bodyRows = rows.slice(/^\|[\s:|-]+\|?\s*$/.test(rows[1] || "") ? 2 : 1);
      out.push(`<table><thead><tr>${head.map(c => `<th>${c}</th>`).join("")}</tr></thead><tbody>` +
        bodyRows.map(r => `<tr>${cells(r).map(c => `<td>${c}</td>`).join("")}</tr>`).join("") + "</tbody></table>");
      continue;
    }
    const li = line.match(/^(\s*)([-*]|\d+[.)])\s+(.*)$/);
    if (li) {
      flush();
      const ordered = /\d/.test(li[2]);
      const items = [];
      while (i < lines.length) {
        const m = lines[i].match(/^(\s*)([-*]|\d+[.)])\s+(.*)$/);
        if (m) { items.push(m[3]); i++; continue; }
        if (lines[i].trim() && /^\s{2,}/.test(lines[i]) && items.length) { items[items.length - 1] += " " + lines[i].trim(); i++; continue; }
        break;
      }
      const tag = ordered ? "ol" : "ul";
      out.push(`<${tag}>${items.map(t => `<li>${inline(t)}</li>`).join("")}</${tag}>`);
      continue;
    }
    para.push(line.trim());
    i++;
  }
  flush();
  return out.join("\n");
}
