// Tezgah editörü: şeffaf textarea + arkada renklendirilmiş <pre>.
// Girinti (Tab / Shift+Tab / otomatik), yorum aç-kapa (Ctrl+/), satır işaretleri.
import { highlightLines } from "./hl.js";

const IND = "    ";

export class Editor {
  constructor(host, { onChange, onRun, onCheck, onSave, dil = "python" } = {}) {
    this.cb = { onChange, onRun, onCheck, onSave };
    this._dil = dil;
    this.markers = new Map();
    host.innerHTML = `<div class="ed"><div class="ed-gutter"><div class="ed-nums"></div></div>
      <div class="ed-main"><pre class="ed-hl" aria-hidden="true"></pre>
      <textarea class="ed-ta" spellcheck="false" wrap="off" autocapitalize="off" autocomplete="off"
        autocorrect="off" aria-label="Kod editörü"></textarea></div></div>`;
    this.ta = host.querySelector(".ed-ta");
    this.hl = host.querySelector(".ed-hl");
    this.nums = host.querySelector(".ed-nums");
    this.gutter = host.querySelector(".ed-gutter");
    this.ta.addEventListener("input", () => { this.markers.clear(); this.paint(); this.cb.onChange?.(this.value); });
    this.ta.addEventListener("scroll", () => this.sync());
    this.ta.addEventListener("keydown", e => this.key(e));
    this.paint();
  }

  get value() { return this.ta.value; }
  set value(v) {
    this.ta.value = (v || "").replace(/\r\n/g, "\n").replace(/\t/g, IND);
    this.markers.clear();
    this.paint();
    this.ta.scrollTop = 0;
    this.ta.scrollLeft = 0;
    this.sync();
  }
  set readOnly(v) { this.ta.readOnly = !!v; }
  set dil(d) { this._dil = d || "python"; this.paint(); }
  get dil() { return this._dil; }
  focus() { this.ta.focus(); }

  mark(line, kind) {
    for (const [l, k] of [...this.markers]) if (k === kind) this.markers.delete(l);
    if (line) this.markers.set(line, kind);
    this.paint();
    if (line) this.reveal(line);
  }
  clearMarks() { this.markers.clear(); this.paint(); }

  reveal(line) {
    const lh = parseFloat(getComputedStyle(this.ta).lineHeight) || 22;
    const top = (line - 1) * lh;
    const view = this.ta.clientHeight;
    if (top < this.ta.scrollTop + lh || top > this.ta.scrollTop + view - 3 * lh) {
      this.ta.scrollTop = Math.max(0, top - view / 3);
    }
  }

  gotoLine(line) {
    const lines = this.value.split("\n");
    let pos = 0;
    for (let i = 0; i < Math.min(line - 1, lines.length); i++) pos += lines[i].length + 1;
    this.ta.focus();
    this.ta.setSelectionRange(pos, pos + (lines[line - 1] || "").length);
    this.reveal(line);
  }

  paint() {
    const html = highlightLines(this.ta.value, this._dil);
    this.hl.innerHTML = html.map((l, i) => {
      const k = this.markers.get(i + 1);
      return `<span class="ln${k ? " m-" + k : ""}">${l || " "}</span>`;
    }).join("") + '<span class="ln"> </span>';
    let n = "";
    for (let i = 1; i <= html.length; i++) {
      const k = this.markers.get(i);
      n += `<div${k ? ` class="m-${k}"` : ""}>${i}</div>`;
    }
    this.nums.innerHTML = n;
    this.sync();
  }

  sync() {
    this.hl.scrollTop = this.ta.scrollTop;
    this.hl.scrollLeft = this.ta.scrollLeft;
    this.gutter.scrollTop = this.ta.scrollTop;
  }

  insert(text) {
    // execCommand geri-al yığınını korur
    const ok = text ? document.execCommand("insertText", false, text) : document.execCommand("delete");
    if (!ok) {
      this.ta.setRangeText(text, this.ta.selectionStart, this.ta.selectionEnd, "end");
      this.ta.dispatchEvent(new Event("input"));
    }
  }

  lineRange() {
    const v = this.ta.value, s = this.ta.selectionStart, e = this.ta.selectionEnd;
    const start = v.lastIndexOf("\n", s - 1) + 1;
    let end = v.indexOf("\n", e > s && v[e - 1] === "\n" ? e - 1 : e);
    if (end < 0) end = v.length;
    return [start, end];
  }

  replaceLines(fn) {
    const [a, b] = this.lineRange();
    const block = this.ta.value.slice(a, b);
    const next = block.split("\n").map(fn).join("\n");
    this.ta.setSelectionRange(a, b);
    this.insert(next);
    this.ta.setSelectionRange(a, a + next.length);
  }

  key(e) {
    const ta = this.ta;
    const mod = e.ctrlKey || e.metaKey;
    if (mod && e.key === "Enter") {
      e.preventDefault();
      (e.shiftKey ? this.cb.onCheck : this.cb.onRun)?.();
      return;
    }
    if (mod && (e.key === "s" || e.key === "S")) { e.preventDefault(); this.cb.onSave?.(); return; }
    if (ta.readOnly) return;
    if (mod && e.key === "/") {
      e.preventDefault();
      if (["spl", "regex", "packets", "wireshark", "bpf"].includes(this._dil)) return;   // bu dillerde satır yorumu yok
      const [a, b] = this.lineRange();
      const lines = ta.value.slice(a, b).split("\n");
      const y = { sql: "--", kql: "//", javascript: "//", yara: "//", cmd: "rem" }[this._dil] || "#";
      const all = lines.filter(l => l.trim()).every(l => l.trimStart().startsWith(y));
      this.replaceLines(l => {
        if (!l.trim()) return l;
        return all ? l.replace(new RegExp("^(\\s*)" + y + " ?"), "$1") : l.replace(/^(\s*)/, "$1" + y + " ");
      });
      return;
    }
    if (e.key === "Tab") {
      e.preventDefault();
      const multi = ta.value.slice(ta.selectionStart, ta.selectionEnd).includes("\n");
      if (e.shiftKey) this.replaceLines(l => l.replace(/^ {1,4}/, ""));
      else if (multi) this.replaceLines(l => (l.trim() ? IND + l : l));
      else {
        const col = ta.selectionStart - ta.value.lastIndexOf("\n", ta.selectionStart - 1) - 1;
        this.insert(" ".repeat(4 - (col % 4)));
      }
      return;
    }
    if (e.key === "Enter" && !e.shiftKey && !mod && !e.altKey) {
      e.preventDefault();
      const v = ta.value, s = ta.selectionStart;
      const lineStart = v.lastIndexOf("\n", s - 1) + 1;
      const before = v.slice(lineStart, s);
      let indent = before.match(/^\s*/)[0];
      const code = before.replace({ sql: /--.*$/, kql: /\/\/.*$/, javascript: /\/\/.*$/, yara: /\/\/.*$/ }[this._dil] || /#.*$/, "").trimEnd();
      const acar = this._dil === "python" ? code.endsWith(":") : this._dil === "bash" ? /\b(then|do|else)$/.test(code) : false;
      if (acar || /[([{]$/.test(code)) indent += IND;
      else if (this._dil === "python" && /^\s*(return|pass|break|continue|raise)\b/.test(before)) indent = indent.slice(0, Math.max(0, indent.length - 4));
      this.insert("\n" + indent);
      return;
    }
    if (e.key === "Backspace" && ta.selectionStart === ta.selectionEnd) {
      const v = ta.value, s = ta.selectionStart;
      const lineStart = v.lastIndexOf("\n", s - 1) + 1;
      const before = v.slice(lineStart, s);
      if (before.length && /^ +$/.test(before)) {
        e.preventDefault();
        const n = before.length % 4 || 4;
        ta.setSelectionRange(s - n, s);
        this.insert("");
      }
    }
  }
}
