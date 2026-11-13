// Native runtime tests live in Python; these check the displayed code contract.
import test from "node:test";
import assert from "node:assert/strict";
import { codeBlock, dilAdi } from "../web/md.js";
import { highlightLines } from "../web/hl.js";

test("CMD aliases select the runnable CMD code block", () => {
  for (const language of ["cmd", "batch", "bat"]) {
    assert.equal(dilAdi(language), "cmd");
    const html = codeBlock('@echo off\necho "test"', language, { dil: "cmd" });
    assert.ok(html.includes("CMD"));
    assert.ok(html.includes('data-act="run"'));
    assert.ok(html.includes('data-act="bench"'));
  }
});

test("CMD highlighting preserves special batch characters and escapes HTML", () => {
  const source = '@echo off\nrem aciklama\nfor /l %%N in (1,1,3) do echo "%~1" !N! <tag> & ^';
  const html = highlightLines(source, "cmd").join("\n");
  assert.ok(!html.includes("<tag>"));
  const plain = html.replace(/<span class="tok-[^"]+">/g, "").replace(/<\/span>/g, "")
    .replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&amp;/g, "&");
  assert.equal(plain, source);
});
