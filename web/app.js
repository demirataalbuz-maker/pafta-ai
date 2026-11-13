// PAFTA ön yüzü: harita, ders paftası, tezgah (editör + çıktı + Röntgen), tekrar.
import { render, codeBlock, stripAnno, regexParcala, dilAdi, matematikAc } from "./md.js";
import { esc } from "./hl.js";
import { Editor } from "./editor.js";

const TOKEN = document.querySelector('meta[name="pafta-token"]').content;
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const view = $("#view");
const S = { state: null, ranks: {}, lesson: null, tid: "python", idx: 0, bench: null, mode: null, sira: 0 };

// Formül çizimi yalnız AI ve kuantum yollarında açılır; ötekilerde `$` düz metindir.
const formulYolu = y => matematikAc(y?.group === "ai" || /^(ai-|kuantum)/.test(y?.id || ""));

const KIND_LABEL = { anlat: "Anlat", tahmin: "Tahmin", gorev: "Görev" };
const KIND_ICON = { anlat: "≡", tahmin: "?", gorev: "✎" };

// ── hata tercümanı ───────────────────────────────────────────────────────────
const ERR_TR = {
  SyntaxError: "Python kodu okuyamadı. Çoğu zaman sebep eksik iki nokta (:), kapanmamış parantez ya da tırnak, veya yanlış yazılmış bir anahtar kelimedir. İşaretlenen satıra ve bir üstündekine bak.",
  IndentationError: "Girinti hatası: bir bloğun içindeki satırlar aynı miktarda içeride olmalı (4 boşluk). İki noktalı (:) satırdan sonra blok bekleniyor olabilir.",
  TabError: "Girintide sekme (Tab) ve boşluk karışmış. Sadece boşluk kullan.",
  NameError: "Bu isim tanımlı değil. Ya yazım hatası var ya da değişkeni/fonksiyonu tanımlamadan önce kullandın. Python büyük-küçük harfe duyarlıdır: Print ≠ print.",
  TypeError: "Tür uyuşmazlığı: bir işlemi onu desteklemeyen türe uyguladın (ör. \"5\" + 3) ya da fonksiyona yanlış sayıda/türde argüman verdin.",
  ValueError: "Tür doğru ama değer uygun değil. Örnek: int(\"abc\") — metin ama sayıya çevrilemez.",
  IndexError: "Dizinin sınırları dışına çıktın. Uzunluğu n olan bir dizide geçerli indeksler 0 … n-1 (ya da -1 … -n).",
  KeyError: "Sözlükte bu anahtar yok. Önce `in` ile kontrol et ya da .get(anahtar, varsayılan) kullan.",
  ZeroDivisionError: "Sıfıra bölme. Böleni kontrol et.",
  AttributeError: "Bu nesnenin böyle bir niteliği ya da metodu yok. Nesnenin türünü kontrol et — çoğu zaman beklediğin şey yerine None gelmiştir.",
  UnboundLocalError: "Fonksiyonun içinde bu değişkene atama yaptığın için Python onu yerel saydı ama atamadan önce okudun. Dıştakini kastediyorsan global/nonlocal gerekir.",
  RecursionError: "Özyineleme çok derinleşti. Büyük ihtimalle temel durum (base case) eksik ya da hiç ulaşılamıyor.",
  ModuleNotFoundError: "Böyle bir modül bulunamadı. Adı doğru mu? Standart kütüphanede değilse kurulu olmayabilir.",
  ImportError: "Modül bulundu ama içinden istediğin isim alınamadı. Adı doğru yazdın mı?",
  FileNotFoundError: "Dosya bulunamadı. Yol ve ad doğru mu? Program görev klasöründe çalışır.",
  EOFError: "input() girdi bekledi ama Girdi kutusunda okunacak satır yok. Alttaki ‘Girdi’ kutusuna satır ekle.",
  StopIteration: "Yineleyici tükendi: next() ile alınacak eleman kalmadı.",
  AssertionError: "Bir assert koşulu yanlış çıktı.",
  OverflowError: "Sayı bu işlem için fazla büyük.",
  PermissionError: "Bu dosya/klasör için iznin yok.",
  UnicodeDecodeError: "Baytlar bu kodlamayla çözülemedi. encoding parametresini kontrol et (çoğu zaman utf-8).",
  UnicodeEncodeError: "Metin bu kodlamaya çevrilemedi.",
  NotImplementedError: "Henüz yazılmamış (soyut) bir metot çağrıldı.",
  ConnectionRefusedError: "Bağlantı reddedildi: o adreste/portta dinleyen bir sunucu yok.",
  TimeoutError: "İşlem zaman aşımına uğradı.",
  RuntimeError: "Çalışma zamanı hatası. Mesajı oku; genelde durum yanlış (ör. döngüde sözlüğü değiştirmek).",
  OSError: "İşletim sistemi düzeyinde bir hata (dosya, soket, izin).",
  KeyboardInterrupt: "Program kesildi.",
  MemoryError: "Bellek yetmedi.",
  "Zaman aşımı": "Program süre sınırında bitmedi. Sonsuz döngü var mı? while koşulu hiç yanlış olmuyor olabilir, ya da input() sonsuza dek bekliyor olabilir.",
  "SüreçBitti": "Program sonuç üretemeden süreci sonlandırdı.",
  "DesenHatası": "Desen derlenemedi. Sık sebepler: kapanmamış parantez ( ya da köşeli parantez [, başında hiçbir şey olmayan bir niceleyici (* + ? {}), geçersiz bir kaçış dizisi ya da yanlış yazılmış bir grup sözdizimi (?P<ad>...).",
  "SPLHatası": "Arama çalıştırılamadı. Sık sebepler: arama sourcetype=<tablo> ile başlamıyor, komutun önünde | unutulmuş, yanlış yazılmış bir alan ya da komut adı, eval içinde metinler için çift tırnak yerine tek tırnak (tek tırnak alan adı demektir), ya da iki arama arasında boş satır yok.",
  "KQLHatası": "Sorgu çalıştırılamadı. Sık sebepler: işlecin önünde | unutulmuş, yanlış yazılmış bir sütun ya da işleç adı (KQL büyük-küçük harfe duyarlıdır: Where ≠ where), metin karşılaştırmasında = yerine == gerekiyor, ya da iki sorgu arasında boş satır yok.",
  "SQLHatası": "SQLite sorguyu çalıştıramadı. Mesajın Türkçesi önde, aslı parantez içinde. Sık sebepler: yanlış yazılmış tablo ya da sütun adı, iki sütun arasında eksik virgül, metin değerinde tek tırnak yerine çift tırnak, WHERE içinde toplama fonksiyonu (orası HAVING olmalı) ya da kapanmamış bir parantez.",
  "ADHatası": "LDAP filtresi ya da Get-AD* komutu çalıştırılamadı. Sık sebepler: kapanmamış parantez, RFC 4515 LDAP filtresinde >= veya <= yerine > veya < kullanımı, (!...) içine birden fazla alt filtre yazılması, değer içinde kaçışsız ( ) \\ karakteri ya da Get-AD* komutunda eksik -Filter / -LDAPFilter / -Identity parametresi.",
  "ÇıkışKodu": "Betik sıfırdan farklı bir çıkış koduyla bitti. Kabuk dünyasında 0 başarı, diğer her şey hatadır. Hata akışındaki (kırmızı) mesajı ve işaretli satırı oku: genelde yanlış yazılmış bir komut, bulunamayan bir dosya ya da eksik bir argüman.",
};

// ── altyapı ───────────────────────────────────────────────────────────────────
let kapaniyor = false;  // sayfa kapanırken atılan istek tarayıcı tarafından kesilmesin
async function api(path, body) {
  const opt = { method: body ? "POST" : "GET", headers: { "X-Pafta-Token": TOKEN } };
  if (body) { opt.headers["Content-Type"] = "application/json"; opt.body = JSON.stringify(body); }
  if (kapaniyor && body && new TextEncoder().encode(opt.body).length < 60000) opt.keepalive = true;  // keepalive gövdesi en çok 64 KiB
  const r = await fetch(path, opt);
  const data = await r.json().catch(() => ({}));
  if (r.status === 403 && /belirteç|yasak/.test(data.error || "")) {
    // Sunucu yeniden başladıysa belirteç değişmiştir; yeni sayfa yeni belirteci taşır.
    let yenilendi = false;
    try { yenilendi = sessionStorage.getItem("pafta-yenile") === "1"; sessionStorage.setItem("pafta-yenile", "1"); } catch (e) { /* depolama yoksa bir kez dene */ }
    if (!yenilendi) location.reload();
  }
  if (!r.ok) throw new Error(data.error || r.statusText);
  try { sessionStorage.removeItem("pafta-yenile"); } catch (e) { /* önemsiz */ }
  return data;
}

let toastT;
function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(toastT);
  toastT = setTimeout(() => t.classList.remove("show"), 2400);
}

// Ekran yüklemesi: yanıt gelene dek route() yeniden çalıştıysa söz hiç sonuçlanmaz, eski ekran yenisinin üzerine çizilmez
function guncelse(p) {
  const sira = S.sira;
  return new Promise((ok, no) => p.then(v => { if (sira === S.sira) ok(v); }, e => { if (sira === S.sira) no(e); }));
}

function debounce(fn, ms) {
  let t, bekleyen = null;
  const d = (...a) => { clearTimeout(t); bekleyen = a; t = setTimeout(() => { bekleyen = null; fn(...a); }, ms); };
  d.flush = (...a) => { clearTimeout(t); bekleyen = null; fn(...a); };
  d.cancel = () => { clearTimeout(t); bekleyen = null; };
  d.bosalt = () => { if (bekleyen) d.flush(...bekleyen); };  // bekleyen çağrı varsa hemen çalıştır
  return d;
}

const trDate = (d = new Date()) => d.toLocaleDateString("tr-TR");
const pad = (n, w = 2) => String(n).padStart(w, "0");

function setTheme(t) {
  document.documentElement.dataset.theme = t;
  $("#themeBtn").textContent = t === "ozalit" ? "OZALİT" : "MAVİ KOPYA";
}

async function refreshHeader() {
  try {
    const st = await api("/api/state");
    S.state = st;
    $("#streakChip b").textContent = st.streak;
    const b = $("#dueBadge");
    b.textContent = st.due_count;
    b.hidden = !st.due_count;
    return st;
  } catch (e) { return S.state; }
}

// ── hata kartı ────────────────────────────────────────────────────────────────
// motor: ai-gercek adımlarının sonucu: koşucunun eklediği kanıt özeti (gerçek çağrı ↔ fixture ayrımı ekranda görünür)
function aiKanit(res) {
  if (!Array.isArray(res.ai_kanit)) return "";
  if (!res.ai_kanit.length) return `<div class="ai-kanit yok"><b>Gerçek deney kanıtı yok</b> · bu sonuç gerçek model kabulü sayılmaz</div>`;
  return res.ai_kanit.map(k => `<div class="ai-kanit ${k.kabul ? "kabul" : ""}"><b>${k.kaynak === "gercek" ? "GERÇEK ÇAĞRI" : "FIXTURE"}</b>` +
    ` · ${esc(k.pilot || "")}${k.model ? ` · model <code>${esc(k.model)}</code>` : ""} · ${k.kabul ? "kabul edildi" : "kabul yok (yalnız deneme)"}` +
    (k.dosya ? `<div>kanıt dosyası: <code>${esc(k.dosya)}</code></div>` : "") + `</div>`).join("");
}

function errCard(err) {
  if (!err) return "";
  const tr = ERR_TR[err.type] || (err.type === "SIGMAHatası" || err.type === "YARAHatası"
    ? "Kural ya da örnek veri doğrulanamadı. Mesajı ve varsa işaretli satırı incele."
    : "Çalıştırma sırasında hata oluştu. Mesajı ve işaretli satırı incele.");
  const parts = [];
  if (err.where === "kod-girdi") parts.push(`Program şu girdiyle çalıştırılırken hata verdi: <code>${esc(JSON.stringify(err.stdin))}</code>`);
  if (err.where === "kod-test") parts.push("Test, kodundaki fonksiyonu çağırdığında kodun hata verdi.");
  if (err.where === "test") {
    parts.push(err.missing
      ? `Test, kodunda <code>${esc(err.missing)}</code> adını arıyor ama bulamadı. Görevdeki adı harfi harfine kullandın mı?`
      : "Hata testin içinde oluştu. Bu genelde fonksiyonun beklenmeyen türde bir değer döndürdüğünde (ör. None) olur.");
  }
  if (err.suggest) parts.push(`Bunu mu demek istedin: <code>${esc(err.suggest)}</code>?`);
  if (err.frames && err.frames.length > 1) {
    parts.push("Çağrı zinciri: " + err.frames.map(f => `<code>${esc(f.func === "<module>" ? "ana kod" : f.func + "()")}</code> s.${f.line}`).join(" → "));
  }
  let raw = `${err.type}: ${err.msg}`;
  if (err.text) raw += `\n    ${err.text.trim()}`;
  const where = err.line && err.where !== "test" ? `<button type="button" class="goto" data-line="${err.line}">satır ${err.line}</button>` : "";
  return `<div class="errcard"><div class="et">${esc(err.type)} ${where}</div><p>${tr}</p>` +
    parts.map(p => `<p>${p}</p>`).join("") + `<div class="raw">${esc(raw)}</div></div>`;
}

// Görev argüman bekliyorsa betik onlarla çalışır; hangileri olduğunu çıktının üstünde göster
function argvSatiri(res) {
  if (!res.argv?.length) return "";
  const goster = a => (/\s|^$/.test(a) ? JSON.stringify(a) : a);
  return `<div class="out-meta" style="margin:0 0 8px">argümanlar: <code>${esc(res.argv.map(goster).join(" "))}</code></div>`;
}

function segsHtml(segs) {
  if (!segs || !segs.length) return "";
  return segs.map(([k, t]) => k === "out" ? esc(t) : `<span class="s-${k}">${esc(t)}</span>`).join("");
}

// SQL: her ifadenin sonucu ayrı bir tablo; değiştiren komutlar tek satırlık özet
function sqlTablolar(tablolar, max = 200, kql = false) {
  return (tablolar || []).map(t => {
    if (!t.sutunlar) {
      const ne = t.degisen !== undefined ? `${t.degisen} satır etkilendi` : "tamam";
      return `<div class="sql-bas"><span class="ln">s.${t.satir}</span><b>${esc(t.komut)}</b> · ${ne}</div>`;
    }
    const n = t.satirlar.length;
    // SPL'in çok değerli alanları \x1f ile ayrık gelir: Splunk'taki gibi her değer ayrı satırda
    const hucre = v => v === null ? `<td class="null">${kql ? "" : "NULL"}</td>`
      : `<td${/^-?\d+(\.\d+)?$/.test(v) ? ' class="num"' : ""}>${esc(String(v)).replace(/\x1f/g, "<br>")}</td>`;
    const govde = t.satirlar.slice(0, max).map(r => `<tr>${r.map(hucre).join("")}</tr>`).join("");
    const fazla = n > max ? `<div class="out-meta">ilk ${max} satır gösteriliyor</div>` : "";
    const konum = t.satir !== undefined ? `<span class="ln">s.${t.satir}</span>` : "";
    return `<div class="sql-sonuc"><div class="sql-bas">${konum}${n} satır${t.kesildi ? " (ilk 500)" : ""}</div>` +
      (n ? `<table class="sql-tablo"><thead><tr>${t.sutunlar.map(c => `<th>${esc(c)}</th>`).join("")}</tr></thead><tbody>${govde}</tbody></table>${fazla}`
        : `<div class="out-meta">sonuç boş · hiçbir satır koşulu sağlamadı</div>`) + `</div>`;
  }).join("");
}

const ELASTIC_DIALECTS = ["kibana", "lucene", "eql", "esql", "ingest", "rule"];
const ELASTIC_LABELS = { kibana: "Kibana KQL", lucene: "Lucene", eql: "Elastic EQL", esql: "ES|QL", ingest: "Ingest pipeline", rule: "Security rule" };

function lessonLanguage(track, lesson, step) {
  const language = track?.dil || "python";
  if (["packets", "elastic"].includes(language)) {
    return dilAdi(step?.meta?.dil || lesson?.steps?.find(s => s.meta?.dil)?.meta.dil ||
      (language === "packets" ? "wireshark" : "kibana"));
  }
  return dilAdi(step?.meta?.dil || language);
}

function lessonInput(step, lesson, language) {
  return step?.stdin || (["elastic", ...ELASTIC_DIALECTS].includes(language)
    ? lesson?.steps?.find(s => s.stdin)?.stdin || "" : "");
}

function elasticOutput(res, max = 200) {
  const sequences = res.elastic_ids.some(Array.isArray);
  const label = ELASTIC_LABELS[res.elastic_dialect] || "Elastic";
  return `<pre class="out">${segsHtml(res.segs)}</pre>` + sqlTablolar(res.tablolar, max) + errCard(res.error) +
    `<div class="out-meta">${esc(label)} · ${esc(res.elastic_backend || "yerel sorgu motoru")} · ${res.elastic_ids.length} eşleşen ${sequences ? "dizi" : "belge"}</div>`;
}

function detectionOutput(res, dil, max = 200) {
  const output = segsHtml(res.segs);
  const warnings = (res.warnings || []).map(w => `<p>${esc(w)}</p>`).join("");
  const message = dil === "sigma"
    ? "Eşleşen olay kimlikleri (id yoksa girdideki sıra numarası)" : "Eşleşen kural adları";
  return `<div class="out-meta">${message}</div><pre class="out">${output || "eşleşme yok"}</pre>` +
    sqlTablolar(res.tablolar || [], max) +
    (warnings ? `<div class="callout tuzak"><div class="ct">Motor uyarıları</div>${warnings}</div>` : "");
}

// ── TEZGAH ────────────────────────────────────────────────────────────────────
class Bench {
  constructor(host, ctx) {
    this.ctx = ctx;  // {track, checkable(), check(code), lessonRef(), saveDraft(code)}
    this.host = host;
    this.results = {};
    this.tab = "out";
    host.innerHTML = `
      <div class="bench-bar">
        <button type="button" class="btn primary small" data-b="run">▶ Çalıştır <kbd>Ctrl+↵</kbd></button>
        <button type="button" class="btn ok small" data-b="check" hidden>✓ Kontrol et <kbd>Ctrl+⇧+↵</kbd></button>
        <button type="button" class="btn small" data-b="xray" title="Kodu adım adım yürüt, her satırda değişkenleri gör">◎ Röntgen</button>
        <button type="button" class="btn small" data-b="dis" title="Python'un bu kodu çevirdiği bytecode">Bytecode</button>
        <span class="sp"></span>
        <span class="save" data-b="save"></span>
        <button type="button" class="linkish" data-b="reset">başa al</button>
      </div>
      <div class="bench-ed"></div>
      <div class="bench-panel">
        <div class="tabs" role="tablist">
          <button type="button" class="tab on" data-tab="out"><i class="dot"></i>Çıktı</button>
          <button type="button" class="tab" data-tab="check" hidden><i class="dot"></i>Kontrol</button>
          <button type="button" class="tab" data-tab="xray"><i class="dot"></i>Röntgen</button>
          <button type="button" class="tab" data-tab="dis">Bytecode</button>
          <span class="sp"></span>
          <button type="button" class="tab stdin-toggle" data-b="stdin">Girdi ▸</button>
        </div>
        <div class="stdin-box" hidden><span class="label">Girdi (stdin) · her satır bir input() çağrısına gider</span><textarea rows="3" spellcheck="false"></textarea></div>
        <div class="pane"></div>
      </div>`;
    this.pane = $(".pane", host);
    this.stdinBox = $(".stdin-box", host);
    this.stdin = $(".stdin-box textarea", host);
    this.saveLbl = $('[data-b="save"]', host);
    this.draft = debounce(code => {
      const sonuclar = this.results;
      const p = this.ctx.saveDraft?.(code);
      if (p) p.then(() => { if (sonuclar === this.results) this.saveLbl.textContent = "kaydedildi"; }).catch(() => { this.saveLbl.textContent = "kaydedilemedi"; });
      else this.saveLbl.textContent = "";
    }, 700);
    this.ed = new Editor($(".bench-ed", host), {
      onChange: code => { this.saveLbl.textContent = this.ctx.saveDraft ? "…" : ""; this.draft(code); this.xrayStale = true; },
      onRun: () => this.run(),
      onCheck: () => this.ctx.checkable() && this.check(),
      onSave: () => { this.draft.flush(this.ed.value); },
      dil: ctx.dil || "python",
    });
    this.ayarla(ctx.dil || "python", ctx.ozellik || { roentgen: true, dis: "Bytecode" });
    host.addEventListener("click", e => {
      const b = e.target.closest("[data-b]");
      if (b) {
        const a = b.dataset.b;
        if (a === "run") this.run();
        else if (a === "check") this.check();
        else if (a === "xray") this.xray();
        else if (a === "dis") this.dis();
        else if (a === "reset") this.reset();
        else if (a === "stdin") this.toggleStdin();
        return;
      }
      const t = e.target.closest("[data-tab]");
      if (t) { this.show(t.dataset.tab); return; }
      const g = e.target.closest(".goto");
      if (g) this.ed.gotoLine(+g.dataset.line);
    });
    this.pane.addEventListener("keydown", e => {
      if (this.tab !== "xray" || !this.x) return;
      const adim = this.x.res.kind === "iz" ? i => this.izStep(i) : i => this.xstep(i);
      if (e.key === "ArrowRight") { e.preventDefault(); adim(this.x.i + 1); }
      if (e.key === "ArrowLeft") { e.preventDefault(); adim(this.x.i - 1); }
    });
    this.show("out");
  }

  // Dile göre düğmeler, etiketler ve boş durum metinleri
  ayarla(dil, ozellik) {
    this.dil = dil;
    this.ozellik = ozellik;
    this.ed.dil = dil;
    const h = this.host;
    const xr = !!ozellik.roentgen, ds = ozellik.dis;
    $('[data-b="xray"]', h).hidden = !xr;
    $('[data-tab="xray"]', h).hidden = !xr;
    $('[data-b="dis"]', h).hidden = !ds;
    $('[data-tab="dis"]', h).hidden = !ds;
    if (ds) { $('[data-b="dis"]', h).textContent = ds; $('[data-tab="dis"]', h).textContent = ds; }
    // Düğmenin yazısı gibi açıklaması da yola göre (fareyle üstüne gelince ve ekran okuyucuda görünür)
    $('[data-b="dis"]', h).title = ds ? ({
      python: "Python'un bu kodu çevirdiği bytecode",
      regex: "Desenin regex motorundaki ayrıştırma ağacı",
      sql: "SQLite'ın sorgu planı (EXPLAIN QUERY PLAN)",
      kql: "KQL sorgusunun SQLite'a çevrilmiş karşılığı",
      spl: "SPL aramasının SQLite'a çevrilmiş karşılığı",
      ad: "Komutun etkin RFC 4515 LDAP filtresi ve arama kapsamı",
    }[dil] || ds) : "";
    $('[data-b="xray"]', h).title = dil === "python" ? "Kodu adım adım yürüt, her satırda değişkenleri gör" : "Betiği iz modunda çalıştır: hangi satır hangi sırayla çalıştı";
    $(".stdin-box .label", h).textContent = {
      python: "Girdi (stdin) · her satır bir input() çağrısına gider",
      regex: "Metin · desen bu metnin içinde aranır",
      bash: "Girdi (stdin) · read komutu satırları buradan okur",
      powershell: "Girdi · satırlar $Girdi dizisine gelir",
      cmd: "Girdi (stdin) · set /p satırları, for /f dosya içeriğini okur",
      javascript: "Girdi (stdin) · require(\"fs\").readFileSync(0, \"utf8\") ile okunur",
      sigma: "Olaylar · JSON nesnesi, liste ya da her satırda bir JSON nesnesi",
      yara: "Örnek veri · UTF-8 metin; ikili veri için hex: veya base64: öneki",
      packets: 'Kayıt seçimi · {"dil":"wireshark" veya "bpf","kayit":"temel", "sinirlar" veya "olay"}',
      wireshark: 'Wireshark · JSON: {"dil":"wireshark","kayit":"temel"}',
      bpf: 'tcpdump/BPF · JSON: {"dil":"bpf","kayit":"temel"}',
      tshark: 'TShark komutu · JSON: {"dil":"tshark","kayit":"tcp-tam"}',
      "tcpdump-lab": 'Kontrollü loopback · JSON: {"dil":"tcpdump-lab","laboratuvar":"kisa"}',
      kibana: "Kibana KQL korpusu · JSON: dil, mapping, documents, context",
      lucene: "Lucene korpusu · JSON: dil, mapping, documents, context",
      eql: "EQL korpusu · JSON: dil, mapping, documents, context",
      esql: "ES|QL korpusu · JSON backend: elastic, dil, mapping, documents",
      ingest: "Ingest korpusu · JSON backend: elastic, dil, mapping, documents",
      rule: "Security kuralı korpusu · JSON backend: elastic, dil, mapping, documents, context",
      elastic: 'Elastic korpusu · JSON dil: "kibana", "lucene" veya "eql"; mapping, documents, context',
    }[dil] || "Girdi";
    this.stdin.rows = ["elastic", ...ELASTIC_DIALECTS].includes(dil) ? 10 : dil === "regex" ? 4 : 3;
    this.girdiAdi = dil === "regex" ? "Metin" : dil === "sigma" ? "Olaylar" : dil === "yara" ? "Örnek veri" : ["elastic", ...ELASTIC_DIALECTS].includes(dil) ? "Korpus JSON" : "Girdi";
    const vt = ["sql", "kql", "spl", "ad"].includes(dil);        // bu dillerin girdisi örnek veritabanıdır / dizindir
    $('[data-b="stdin"]', h).hidden = vt;
    this.toggleStdin(["regex", "sigma", "yara", "packets", "wireshark", "bpf", "tshark", "tcpdump-lab", "elastic", ...ELASTIC_DIALECTS].includes(dil) ? true : vt ? false : !this.stdinBox.hidden);
  }

  setStdin(t) {
    this.stdin.value = t || "";
    if (t) this.toggleStdin(true);
  }

  load({ code = "", stdin = "", resetCode = "", checkable = false }) {
    this.resetCode = resetCode;
    this.ed.value = code;
    this.stdin.value = stdin;
    if (stdin) this.toggleStdin(true);
    $('[data-b="check"]', this.host).hidden = !checkable;
    $('[data-tab="check"]', this.host).hidden = !checkable;
    this.results = {};
    this.x = null;
    this.saveLbl.textContent = "";
    $$(".tab .dot", this.host).forEach(d => d.className = "dot");
    this.show("out");
  }

  setCode(code) {
    this.draft.cancel();  // bekleyen eski metin yeni kodun üzerine yazılmasın
    this.ed.value = code;
    this.ctx.saveDraft?.(code);
    this.show("out");
  }

  toggleStdin(force) {
    const open = force ?? this.stdinBox.hidden;
    this.stdinBox.hidden = !open;
    $('[data-b="stdin"]', this.host).textContent = `${this.girdiAdi || "Girdi"} ${open ? "▾" : "▸"}`;
  }

  reset() {
    if (this.ed.value === this.resetCode) return;
    if (!confirm("Editördeki kodu başlangıç haline döndürmek istiyor musun?")) return;
    this.setCode(this.resetCode);
  }

  dot(tab, cls) {
    const d = $(`[data-tab="${tab}"] .dot`, this.host);
    if (d) d.className = "dot " + (cls || "");
  }

  busy(tab, msg) {
    this.show(tab);
    this.pane.className = "pane empty";
    this.pane.innerHTML = msg;
  }

  show(tab) {
    this.tab = tab;
    $$(".tab[data-tab]", this.host).forEach(t => t.classList.toggle("on", t.dataset.tab === tab));
    const r = this.results[tab];
    this.pane.className = "pane";
    this.pane.tabIndex = tab === "xray" ? 0 : -1;
    if (!r) {
      this.pane.className = "pane empty";
      const py = this.dil === "python";
      this.pane.innerHTML = {
        out: { regex: "▶ Çalıştır deseni Metin kutusundaki metinde arar;<br>eşleşmeler işaretlenir",
          sql: "▶ Çalıştır sorguyu örnek veritabanında çalıştırır;<br>her sorgunun sonucu bir tablo olarak görünür",
          kql: "▶ Çalıştır sorguyu örnek veritabanında çalıştırır;<br>boş satırla ayrılmış her sorgu ayrı bir tablo verir",
          spl: "▶ Çalıştır aramayı örnek veritabanında çalıştırır;<br>boş satırla ayrılmış her arama ayrı bir tablo verir",
          kibana: "▶ Çalıştır KQL sorgusunu Korpus JSON içindeki belgelerde değerlendirir;<br>eşleşen belge kimlikleri burada görünür",
          lucene: "▶ Çalıştır Lucene sorgusunu Korpus JSON içindeki belgelerde değerlendirir;<br>eşleşen belge kimlikleri burada görünür",
          eql: "▶ Çalıştır EQL sorgusunu Korpus JSON içindeki olaylarda değerlendirir;<br>kimlikler veya olay dizileri burada görünür",
          elastic: "▶ Çalıştır sorguyu Korpus JSON içindeki dil, mapping ve belgelerle değerlendirir;<br>Kibana KQL, Lucene veya EQL seçebilirsin",
          ad: "▶ Çalıştır LDAP filtresini veya Get-AD* komutunu DC=pafta,DC=local dizininde çalıştırır;<br>sonuç tablosu burada görünür" }[this.dil]
          || "▶ Çalıştır ile kodun çıktısı burada görünür",
        check: "✓ Kontrol et ile görev testleri burada koşar",
        xray: py ? "◎ Röntgen kodu adım adım yürütür:<br>her satırda hangi isim hangi nesneyi gösteriyor, gör"
          : "◎ Röntgen betiği iz modunda çalıştırır:<br>hangi satırın hangi sırayla, hangi değerlerle çalıştığını gör",
        dis: { python: "Python kodunu önce bytecode'a çevirir, sonra onu yürütür.<br>Bytecode düğmesi o çeviriyi gösterir",
          regex: "Ağaç, desenin regex motoru tarafından nasıl parçalara ayrıldığını gösterir",
          sql: "Plan, SQLite'ın sorguyu nasıl yürüteceğini gösterir:<br>tabloyu baştan sona mı tarıyor, indeksle mi arıyor",
          kql: "SQL düğmesi KQL sorgunun SQL karşılığını gösterir:<br>her | aşaması bir WITH adımına dönüşür",
          spl: "SQL düğmesi aramanın SQL karşılığını gösterir:<br>her | komutu bir WITH adımına dönüşür",
          ad: "LDAP düğmesi Get-AD* komutunun veya filtrenin etkin RFC 4515 LDAP karşılığını ve arama kapsamını (SearchBase / SearchScope) gösterir" }[this.dil] || "",
      }[tab];
      return;
    }
    if (tab === "out") this.paintOut(r);
    if (tab === "check") this.paintCheck(r);
    if (tab === "xray") (this.x.res.kind === "iz" ? this.paintIz() : this.paintXray());
    if (tab === "dis") this.paintDis(r);
  }

  async run() {
    const sonuclar = this.results;  // load() bunu yeniler: yanıt gelene dek başka adım yüklendiyse çıktı boyanmaz
    this.busy("out", "çalışıyor…");
    this.ed.clearMarks();
    try {
      const res = await api("/api/run", { track: this.ctx.track, code: this.ed.value, stdin: this.stdin.value, mode: "run", ...(this.ctx.lessonRef?.() || {}) });
      if (sonuclar !== this.results) return;
      this.results.out = res;
      this.dot("out", res.error ? "bad" : "ok");
      this.show("out");
    } catch (e) { this.busy("out", "Sunucuya ulaşılamadı: " + esc(e.message)); }
  }

  paintOut(res) {
    if (res.eslesmeler) return this.paintEslesme(res);
    if (res.elastic_native) {
      this.pane.innerHTML = `<pre class="out">${segsHtml(res.segs)}</pre>` + sqlTablolar(res.tablolar, 200) +
        `<div class="out-meta">${esc(res.elastic_backend)}</div>` + errCard(res.error);
      return;
    }
    if (res.packet_backend && ["tshark", "tcpdump-lab"].includes(res.packet_dialect)) {
      this.pane.innerHTML = `<pre class="out">${segsHtml(res.segs)}</pre>` + sqlTablolar(res.tablolar, 200) +
        `<div class="out-meta">${esc(res.packet_backend)}</div>` + errCard(res.error);
      return;
    }
    if (Array.isArray(res.elastic_ids)) {
      this.pane.innerHTML = elasticOutput(res);
      if (res.error?.line) this.ed.mark(res.error.line, "err");
      return;
    }
    if (Array.isArray(res.packet_ids)) {
      const inventory = res.packet_inventory;
      const interfaces = res.capture_interfaces || [];
      this.pane.innerHTML = `<pre class="out">${segsHtml(res.segs)}</pre>` + sqlTablolar(res.tablolar, 200) +
        (inventory ? `<details class="packet-inventory"><summary>Kaydın tamamı · ${inventory.satirlar.length} paket</summary>` +
          `<div class="out-meta">Eğitim kaydındaki paketlerin adres, port ve içerik açıklamaları.</div>${sqlTablolar([inventory], 200)}</details>` : "") +
        (interfaces.length ? `<details class="packet-inventory"><summary>Arayüz ve tam zaman bilgisi</summary>` +
          sqlTablolar([{sutunlar:["Frame", "Section", "Arayüz", "LINKTYPE", "Epoch saniyesi · tam kesir"],
            satirlar:interfaces.map(f => [f.frame, f.section, f.interface, f.linktype, f.timestamp_fraction])}], 200) + `</details>` : "") +
        `<div class="out-meta">${esc(res.packet_dialect === "bpf" ? "BPF · " + res.packet_backend : "Wireshark · TShark")} · kayıtlı paketler</div>`;
      return;
    }
    if (["sigma", "yara"].includes(this.dil) && !res.error) {
      this.pane.innerHTML = detectionOutput(res, this.dil);
      return;
    }
    if (res.tablolar) {
      const meta = res.error ? "" : `<div class="out-meta">${res.tablolar.length ? "— bitti —" : "betikte çalışan bir ifade yok"}</div>`;
      this.pane.innerHTML = sqlTablolar(res.tablolar, 200, res.kql) + errCard(res.error) + meta;
      if (res.error?.line) this.ed.mark(res.error.line, "err");
      return;
    }
    const body = segsHtml(res.segs);
    const bos = { python: "program çıktı vermeden bitti (print kullandın mı?)", bash: "betik çıktı vermeden bitti (echo kullandın mı?)",
      powershell: "betik çıktı vermeden bitti" }[this.dil] || "çıktı yok";
    const meta = res.error ? "" : `<div class="out-meta">${body ? "— bitti —" : bos}${res.truncated ? " · çıktı kesildi" : ""}</div>`;
    this.pane.innerHTML = `${argvSatiri(res)}<pre class="out">${body}</pre>${errCard(res.error)}${aiKanit(res)}${meta}`;
    if (res.error?.line && res.error.where !== "test") this.ed.mark(res.error.line, "err");
    else if (res.uyari_satir) this.ed.mark(res.uyari_satir, "err");
  }

  // Regex: metni eşleşmeler işaretli göster, altında eşleşme tablosu
  paintEslesme(res) {
    if (res.error) { this.pane.innerHTML = errCard(res.error); if (res.error.line) this.ed.mark(res.error.line, "err"); return; }
    const es = res.eslesmeler, metin = res.metin || "";
    let html = "", konum = 0;
    for (const e of es) {
      if (e.son === e.bas) continue;
      html += esc(metin.slice(konum, e.bas)) + `<mark>${esc(metin.slice(e.bas, e.son))}</mark>`;
      konum = e.son;
    }
    html += esc(metin.slice(konum));
    const grupVar = es.some(e => e.gruplar.length);
    const satirlar = es.slice(0, 200).map((e, i) => {
      const gr = Object.keys(e.adli).length
        ? Object.entries(e.adli).map(([k, v]) => `${esc(k)}=${esc(JSON.stringify(v))}`).join(" ")
        : e.gruplar.map((g, j) => `${j + 1}=${esc(JSON.stringify(g))}`).join(" ");
      return `<tr><td>${i + 1}</td><td>${esc(JSON.stringify(e.metin))}</td><td>${e.bas}–${e.son}</td>${grupVar ? `<td>${gr}</td>` : ""}</tr>`;
    }).join("");
    const ozet = es.length ? `${es.length} eşleşme` : "eşleşme yok";
    this.pane.innerHTML = `<div class="check-sum ${es.length ? "pass" : "fail"}" style="font-size:12px">${ozet}</div>` +
      (metin ? `<pre class="rx-metin">${html}</pre>` : `<div class="out-meta">Metin kutusu boş: desenin arayacağı metni oraya yaz</div>`) +
      (es.length ? `<table class="rx-tablo"><thead><tr><th>#</th><th>eşleşme</th><th>konum</th>${grupVar ? "<th>gruplar</th>" : ""}</tr></thead><tbody>${satirlar}</tbody></table>` : "");
  }

  async check(suren = null) {  // suren: önceki ekranda başlamış Kontrol'ün sözü (Tekrar'a dönüş)
    this.busy("check", "testler koşuyor…");
    this.ed.clearMarks();
    try {
      const res = await (suren || this.ctx.check(this.ed.value));
      if (!res) return;
      this.results.check = res;
      this.dot("check", res.status === "pass" ? "ok" : "bad");
      this.show("check");
      if (res.status === "pass") this.ctx.onPass?.(res);
    } catch (e) { this.busy("check", "Sunucuya ulaşılamadı: " + esc(e.message)); }
  }

  paintCheck(res) {
    const checks = res.checks || [];
    const okN = checks.filter(c => c.ok).length;
    let head;
    if (res.status === "pass") head = `<div class="check-sum pass">✓ ${okN}/${checks.length} kontrol geçti — onaylandı</div>`;
    else if (res.status === "error") head = `<div class="check-sum fail">✗ Testler başlamadan program hata verdi</div>`;
    else if (res.status === "timeout") head = `<div class="check-sum fail">✗ Süre aşıldı</div>`;
    else head = `<div class="check-sum fail">✗ ${okN}/${checks.length} kontrol geçti</div>`;
    const list = checks.map(c => `<li class="${c.ok ? "ok" : "no"}"><span class="ic">${c.ok ? "✓" : "✗"}</span><span>${render(c.msg).replace(/^<p>|<\/p>$/g, "")}</span>` +
      (!c.ok && (c.got !== undefined || c.exp !== undefined)
        ? `<div class="ge">${c.exp !== undefined ? `<span>beklenen</span><code>${esc(c.exp)}</code>` : ""}${c.got !== undefined ? `<span>senin</span><code>${esc(c.got)}</code>` : ""}</div>` : "") + "</li>").join("");
    const outText = segsHtml(res.segs);
    const out = outText ? `<div class="out-meta">programın çıktısı</div><pre class="out">${outText}</pre>` : "";
    this.pane.innerHTML = head + aiKanit(res) + `<ul class="checks">${list}</ul>` + errCard(res.error) + out;
    if (res.error?.line && res.error.where !== "test") this.ed.mark(res.error.line, "err");
  }

  async xray() {
    const sonuclar = this.results;
    this.busy("xray", "röntgen çekiliyor…");
    try {
      const res = await api("/api/run", { track: this.ctx.track, code: this.ed.value, stdin: this.stdin.value, mode: "trace", ...(this.ctx.lessonRef?.() || {}) });
      if (sonuclar !== this.results) return;
      this.results.xray = res;
      this.x = { res, i: 0 };
      this.xrayStale = false;
      this.dot("xray", res.error ? "bad" : "ok");
      this.show("xray");
      this.pane.focus();
    } catch (e) { this.busy("xray", "Sunucuya ulaşılamadı: " + esc(e.message)); }
  }

  paintXray() {
    const res = this.x.res;
    if (!res.steps || !res.steps.length) {
      this.pane.innerHTML = errCard(res.error) || '<div class="pane empty">İzlenecek adım yok.</div>';
      if (res.error?.line) this.ed.mark(res.error.line, "err");
      return;
    }
    const n = res.steps.length;
    this.pane.innerHTML = `<div class="xray">
      <div class="xray-ctl">
        <button type="button" class="btn small" data-x="first" title="Başa">⏮</button>
        <button type="button" class="btn small" data-x="prev" title="Geri (←)">◀</button>
        <input type="range" min="0" max="${n - 1}" value="${this.x.i}" aria-label="Adım">
        <button type="button" class="btn small" data-x="next" title="İleri (→)">▶</button>
        <button type="button" class="btn small" data-x="last" title="Sona">⏭</button>
        <span class="info"></span>
      </div>
      <div class="xray-frames"></div>
      <div class="xray-out"><span class="label">bu adıma kadar çıktı</span><pre></pre>
        <div class="xray-legend">aynı renkli kare = aynı nesne (aynı id)<br>sarı isim = bu adımda değişti${res.truncated ? "<br>ilk 500 adım gösteriliyor" : ""}</div>
        ${res.error ? errCard(res.error) : ""}</div>
    </div>`;
    const range = $("input[type=range]", this.pane);
    range.addEventListener("input", () => this.xstep(+range.value));
    $$("[data-x]", this.pane).forEach(b => b.addEventListener("click", () => {
      const a = b.dataset.x, i = this.x.i;
      this.xstep(a === "first" ? 0 : a === "last" ? n - 1 : a === "prev" ? i - 1 : i + 1);
    }));
    this.xstep(this.x.i);
  }

  xstep(i) {
    const res = this.x.res, steps = res.steps;
    i = Math.max(0, Math.min(steps.length - 1, i));
    this.x.i = i;
    const st = steps[i], prev = steps[i - 1];
    const range = $("input[type=range]", this.pane);
    if (range) range.value = i;
    const ev = { line: "satır", return: "dönüş", exception: "hata" }[st.ev] || st.ev;
    const top = st.frames[st.frames.length - 1];
    $(".info", this.pane).innerHTML = `adım ${i + 1}/${steps.length} · satır ${st.line} · <span class="ev-${st.ev}">${ev}</span>${top && top.name !== "<module>" ? " · " + esc(top.name) + "()" : ""}`;
    const prevVars = {};
    if (prev) for (const f of prev.frames) for (const [k, v] of f.vars) prevVars[f.name + ":" + k] = v.r;
    const color = id => `hsl(${(id * 2654435761 % 4294967296) / 4294967296 * 360} 72% 58%)`;
    const frames = st.frames.slice().reverse().map((f, fi) => {
      const rows = f.vars.map(([k, v]) => {
        const changed = prevVars[f.name + ":" + k] !== v.r;
        return `<tr class="${changed && prev ? "changed" : ""}"><td class="n">${esc(k)}</td><td class="t">${esc(v.t)}</td>` +
          `<td class="v"><i class="oid" style="background:${color(v.id)}" title="id ${v.id}"></i>${esc(v.r)}</td></tr>`;
      }).join("") || `<tr><td class="t" colspan="3">— henüz isim yok —</td></tr>`;
      const isTop = fi === 0;
      const ret = isTop && st.ev === "return" && f.name !== "<module>" ? `<div class="ret">↩ döndürülen: ${esc(st.ret.r)}</div>` : "";
      const exc = isTop && st.ev === "exception" ? `<div class="ret" style="color:var(--bad)">⚠ ${esc(st.exc)}</div>` : "";
      return `<div class="frame ${isTop ? "top" : ""}"><div class="frame-h"><span>${f.name === "<module>" ? "global (ana kod)" : esc(f.name) + "() çerçevesi"}</span><span>satır ${f.line}</span></div><table>${rows}</table>${ret}${exc}</div>`;
    }).join("");
    $(".xray-frames", this.pane).innerHTML = frames;
    $(".xray-out pre", this.pane).textContent = res.out.slice(0, st.out);
    this.ed.mark(st.line, "step");
  }

  // Bash/PowerShell izi: çalışan komutlar sırayla, satır işaretiyle
  paintIz() {
    const res = this.x.res, iz = res.iz || [];
    if (!iz.length) {
      this.pane.innerHTML = (errCard(res.error) || "") + '<div class="out-meta">İzlenecek komut yok.</div>' +
        (res.out ? `<pre class="out">${esc(res.out)}</pre>` : "");
      return;
    }
    const n = iz.length;
    this.pane.innerHTML = `<div class="xray">
      <div class="xray-ctl">
        <button type="button" class="btn small" data-x="first" title="Başa">⏮</button>
        <button type="button" class="btn small" data-x="prev" title="Geri (←)">◀</button>
        <input type="range" min="0" max="${n - 1}" value="${this.x.i}" aria-label="Adım">
        <button type="button" class="btn small" data-x="next" title="İleri (→)">▶</button>
        <button type="button" class="btn small" data-x="last" title="Sona">⏭</button>
        <span class="info"></span>
      </div>
      <div class="xray-frames"><ul class="iz-liste">${iz.map((s, i) =>
        `<li data-i="${i}"><span class="ln">s.${s.line}${s.derinlik > 1 ? " " + "↳".repeat(s.derinlik - 1) : ""}</span><span>${esc(s.metin)}</span></li>`).join("")}</ul></div>
      <div class="xray-out">${argvSatiri(res)}<span class="label">betiğin çıktısı</span><pre>${esc(res.out || "")}</pre>
        <div class="xray-legend">her satır, yorumlayıcının çalıştırdığı bir komuttur<br>değişkenler yerine değerleri yazılmış haldedir</div>
        ${res.error ? errCard(res.error) : ""}</div>
    </div>`;
    const range = $("input[type=range]", this.pane);
    range.addEventListener("input", () => this.izStep(+range.value));
    $$("[data-x]", this.pane).forEach(b => b.addEventListener("click", () => {
      const a = b.dataset.x, i = this.x.i;
      this.izStep(a === "first" ? 0 : a === "last" ? n - 1 : a === "prev" ? i - 1 : i + 1);
    }));
    $(".iz-liste", this.pane).addEventListener("click", e => {
      const li = e.target.closest("li[data-i]");
      if (li) this.izStep(+li.dataset.i);
    });
    this.izStep(this.x.i);
  }

  izStep(i) {
    const iz = this.x.res.iz;
    i = Math.max(0, Math.min(iz.length - 1, i));
    this.x.i = i;
    const range = $("input[type=range]", this.pane);
    if (range) range.value = i;
    $$(".iz-liste li", this.pane).forEach((li, j) => li.classList.toggle("on", j === i));
    const on = $(".iz-liste li.on", this.pane);
    if (on) on.scrollIntoView({ block: "nearest" });
    $(".info", this.pane).textContent = `komut ${i + 1}/${iz.length} · satır ${iz[i].line}`;
    this.ed.mark(iz[i].line, "step");
  }

  async dis() {
    const sonuclar = this.results;
    this.busy("dis", "çıkarılıyor…");
    try {
      const res = await api("/api/run", { track: this.ctx.track, code: this.ed.value, mode: "dis", ...(this.ctx.lessonRef?.() || {}) });
      if (sonuclar !== this.results) return;
      this.results.dis = res;
      this.show("dis");
    } catch (e) { this.busy("dis", "Sunucuya ulaşılamadı: " + esc(e.message)); }
  }

  paintDis(res) {
    if (res.error) { this.pane.innerHTML = errCard(res.error); return; }
    const html = esc(res.text).replace(/\b([A-Z][A-Z_]{2,})\b/g, '<span class="op">$1</span>')
      .replace(/^(\s*\d+)(?=\s)/gm, '<span class="ln">$1</span>');
    const aciklama = {
      regex: "LITERAL = düz karakter (kod numarası) · IN = karakter kümesi · MAX_REPEAT = açgözlü tekrar · MIN_REPEAT = tembel tekrar · SUBPATTERN = grup · AT = çapa · BRANCH = alternatif",
      sql: "SCAN = tablonun tamamı okunur · SEARCH = indeks ya da anahtarla doğrudan arama · TEMP B-TREE = sıralamak/gruplamak için geçici yapı · girinti = iç içe adım",
      kql: "her | aşaması bir WITH adımı (a1, a2, ...) · [__sira] = sort/top sonrası sırayı taşıyan gizli sütun · contains/has/startswith = KQL gibi büyük-küçük harfe duyarsız yardımcı fonksiyonlar",
      spl: "her | komutu bir WITH adımı (a1, a2, ...) · [__sira] = olayların sırasını taşıyan gizli sütun · spl_esit/spl_wild = aramadaki büyük-küçük harfe duyarsız eşitlik ve * joker karakteri",
    }[this.dil] || "sol sütun: kaynak satırı · sonra: bayt konumu · komut · argüman";
    this.pane.innerHTML = `<div class="out-meta" style="margin:0 0 8px">${aciklama}</div><pre class="dis">${html}</pre>`;
  }
}

// ── HARİTA ────────────────────────────────────────────────────────────────────
function lessonStats(lesson, steps) {
  const total = lesson.kinds.length;
  let done = 0;
  for (let i = 0; i < total; i++) if (steps[`${lesson.id}:${i}`]?.done) done++;
  return { total, done };
}

const at = s => esc(String(s ?? "")).replace(/"/g, "&quot;");

// Kazanım paftası: sertifikanın bölümleri sınav ağırlığı kadar geniş bir ölçü çizgisi;
// her madde, onu karşılayan paftalarla. Boş madde = henüz çizilmedi.
function kazanimHtml(serts, tid, track, steps) {
  if (!serts?.length) return "";
  const dersler = Object.fromEntries(track.modules.flatMap(m => m.lessons).map(l => [l.id, l]));
  const bitti = lid => {
    const l = dersler[lid];
    if (!l || l.missing) return false;
    const s = lessonStats(l, steps);
    return !!s.total && s.done === s.total;
  };
  const kartlar = serts.map(s => {
    const bolumler = s.bolumler.map(b => {
      const m = b.maddeler || [];
      return { b, n: m.length, kap: m.filter(x => x.dersler.length).length,
        cal: m.filter(x => x.dersler.length && x.dersler.every(bitti)).length, w: b.agirlik || 1 };
    });
    const W = bolumler.reduce((t, x) => t + x.w, 0) || 1;
    const agirlikli = f => Math.round(bolumler.reduce((t, x) => t + x.w * (x.n ? f(x) / x.n : 0), 0) / W * 100);
    const toplamM = bolumler.reduce((t, x) => t + x.n, 0), toplamK = bolumler.reduce((t, x) => t + x.kap, 0);
    const sv = s.sinav || {};
    const kunye = [sv.soru && `${sv.soru} soru`, sv.dakika && `${sv.dakika} dk`, sv.gecme && `geçme %${sv.gecme}`].filter(Boolean).join(" · ");
    const sid = encodeURIComponent(s.id);
    const olcu = bolumler.map(x => `<a class="kz-dilim" style="flex:${x.w}" href="#/sinav/${tid}/${sid}/${encodeURIComponent(x.b.kod)}" title="${at(`${x.b.kod} · ${x.b.baslik} · ${x.kap}/${x.n} madde karşılanıyor, ${x.cal} madde çalışıldı`)}">` +
      `<i class="kap" style="width:${x.n ? x.kap / x.n * 100 : 0}%"></i><i class="cal" style="width:${x.n ? x.cal / x.n * 100 : 0}%"></i>` +
      `<em>${esc(String(x.b.kod))}${x.b.agirlik ? `<small>%${x.b.agirlik}</small>` : ""}</em></a>`).join("");
    const govde = bolumler.map(x => `<div class="kz-bolum"><div class="kz-bh"><span class="kz-kod">${esc(String(x.b.kod))}</span><b>${esc(x.b.baslik)}</b>` +
      (x.b.agirlik ? `<span class="label">ağırlık %${x.b.agirlik}</span>` : "") + `<span class="label">${x.kap}/${x.n} madde</span>` +
      `<a class="linkish" href="#/sinav/${tid}/${sid}/${encodeURIComponent(x.b.kod)}">bölüm sınavı →</a></div>` +
      (x.b.not ? `<p class="kz-bnot">${esc(x.b.not)}</p>` : "") + `<div class="kz-maddeler">` +
      (x.b.maddeler || []).map(m => {
        const durum = !m.dersler.length ? "bos" : m.dersler.every(bitti) ? "tam" : "var";
        const cips = m.dersler.length
          ? m.dersler.map(l => `<a class="kz-ders ${bitti(l) ? "bitti" : ""}" href="#/ders/${tid}/${l}/0" title="${at(dersler[l]?.title || l)}">${esc(l.toUpperCase())}</a>`).join("")
          : `<span class="kz-yok">çizilmedi</span>`;
        return `<div class="kz-m ${durum}"><span class="kz-kod">${esc(String(m.kod))}</span><span class="kz-mb">${esc(m.baslik)}${m.not ? `<small>${esc(m.not)}</small>` : ""}</span><span class="kz-dersler">${cips}</span></div>`;
      }).join("") + `</div></div>`).join("");
    return `<section class="kz">
      <header class="kz-head">
        <div class="kz-ad"><span class="label">${esc(s.kurum || "Sertifika")}</span><h3>${esc(s.ad)}</h3>${s.tam_ad ? `<small>${esc(s.tam_ad)}</small>` : ""}</div>
        <div class="kz-sayi"><span class="label">Kapsam</span><b>${toplamK}<small>/ ${toplamM} madde</small></b></div>
        <div class="kz-sayi"><span class="label">Hazırlık</span><b>%${agirlikli(x => x.cal)}<small>ağırlıklı</small></b></div>
        <div class="kz-eylem">${kunye ? `<span class="label">Gerçek sınav · ${esc(kunye)}</span>` : ""}<a class="btn small primary" href="#/sinav/${tid}/${sid}">Deneme sınavı →</a>` +
          (s.kaynak ? `<a class="linkish" href="${at(s.kaynak)}" target="_blank" rel="noopener">resmî konu listesi ↗</a>` : "") + `</div>
      </header>
      <div class="kz-olcu" aria-label="Bölümler sınav ağırlığına göre">${olcu}</div>
      <details class="kz-detay"><summary><span class="label">${toplamM} maddeyi aç · ağırlıklı kapsam %${agirlikli(x => x.kap)}</span></summary>${govde}</details>
    </section>`;
  }).join("");
  return `<div class="sec-head"><h2>Kazanımlar</h2><span class="dimline"></span><span class="label">sertifikanın konu listesi · her madde hangi paftada</span></div>` +
    `<div class="kz-lejant"><span><i class="kap"></i>paftası var</span><span><i class="cal"></i>paftası bitti</span><span class="label">dilim genişliği = sınavdaki ağırlık · dilime tıkla, o bölümden sınava gir</span></div>${kartlar}`;
}

async function renderMap(tid) {
  S.mode = "map";
  const st = await guncelse(refreshHeader());
  const aktifler = (st?.tracks || []).filter(t => t.status === "active");
  if (!tid) tid = (st?.last && aktifler.some(t => t.id === st.last.track)) ? st.last.track : (aktifler[0]?.id || "python");
  let tv;
  try { tv = await guncelse(api(`/api/track/${tid}`)); }
  catch (e) { view.innerHTML = `<div class="page"><div class="empty-state">Bu yol bulunamadı: ${esc(tid)}<br><a class="btn" href="#/">Haritaya dön</a></div></div>`; return; }
  const track = tv.track, steps = tv.steps;
  if (track.status !== "active" || !track.order.length) {
    view.innerHTML = `<div class="page"><div class="empty-state">${esc(track.name)} yolu henüz yazılmadı.<br><br><a class="btn" href="#/">Haritaya dön</a></div></div>`;
    return;
  }
  S.mapTid = tid;
  const ranks = track.ranks || [];
  let lessonsDone = 0, lessonsTotal = 0, gorevDone = 0, gorevTotal = 0;
  let firstOpen = null;
  for (const m of track.modules) for (const l of m.lessons) {
    if (l.missing) continue;
    lessonsTotal++;
    const s = lessonStats(l, steps);
    if (s.total && s.done === s.total) lessonsDone++;
    else if (!firstOpen) firstOpen = { lesson: l, module: m };
    l.kinds.forEach((k, i) => { if (k === "gorev") { gorevTotal++; if (steps[`${l.id}:${i}`]?.done) gorevDone++; } });
  }
  const last = st.last && st.last.track === tid ? st.last : null;
  const currentId = last ? last.lesson : firstOpen?.lesson.id;
  const curRank = ranks.find(r => r.id === (firstOpen?.module.rank)) || ranks[ranks.length - 1] || { name: "—" };
  const cta = last
    ? `<a class="btn primary" href="#/ders/${tid}/${last.lesson}/${last.step}">Kaldığın yerden → ${esc(last.lesson.toUpperCase())}</a>`
    : `<a class="btn primary" href="#/ders/${tid}/${track.order[0]}/0">İlk paftayı aç →</a>`;
  const pct = (a, b) => (b ? Math.round(a / b * 100) : 0);
  const [kahraman1, kahraman2, kahraman3] = track.kahraman || ["Minik'ten", "Başpehlivan", "'a"];

  const rankHtml = ranks.map((r, ri) => {
    const mods = track.modules.filter(m => m.rank === r.id);
    if (!mods.length) return "";
    const allDone = mods.every(m => m.lessons.every(l => { const s = lessonStats(l, steps); return s.total && s.done === s.total; }));
    return `<section class="rank ${allDone ? "done" : ""}"><div class="rank-tag"><span class="n">${pad(ri + 1)}</span>${esc(r.name)}</div><div class="rank-body">` +
      mods.map(m => `<div class="mod"><div class="mod-head"><span class="mod-num">M${pad(m.index)}</span><span class="mod-title">${esc(m.title)}</span>` +
        (m.zen ? `<span class="mod-zen">“${esc(m.zen)}”</span>` : "") + `</div><div class="chain">` +
        m.lessons.map(l => {
          const s = lessonStats(l, steps);
          const cls = l.missing ? "missing" : s.total && s.done === s.total ? "done" : s.done ? "part" : "";
          const cur = l.id === currentId ? " current" : "";
          return `<a class="node ${cls}${cur}" href="#/ders/${tid}/${l.id}/0" title="${esc(l.summary || l.title)}">` +
            `<span class="nid"><span>${esc(l.id.toUpperCase())}</span><span>${s.done}/${s.total}</span></span><span class="nt">${esc(l.title)}</span>` +
            `<span class="np"><i style="width:${pct(s.done, s.total)}%"></i></span></a>`;
        }).join("") + `</div></div>`).join("") + `</div></section>`;
  }).join("");

  const sekmeler = aktifler.map(t => `<a href="#/yol/${t.id}" class="${t.id === tid ? "on" : ""}">${esc(t.name)}` +
    `<small>${t.steps_done || 0}/${t.steps_total || 0}</small></a>`).join("");

  const groups = [["her-iki", "⚔ Her iki taraf"], ["savunma", "🔵 Savunma tarafı"], ["okuma", "🟡 Okuyabilecek kadar"]];
  const roads = groups.map(([g, name]) => {
    const ts = st.tracks.filter(t => t.group === g);
    return `<div class="road-col"><span class="label">${name}</span>` + ts.map(t => {
      const aktif = t.status === "active";
      const etiket = aktif ? (t.hazir === false ? "KURULUM GEREKİR" : t.id === tid ? "AÇIK" : "AKTİF") : "PLANLI";
      return `<div class="road ${aktif ? "active" : ""}" ${aktif ? `data-go="#/yol/${t.id}"` : ""}>` +
        `<b>${esc(t.name)}</b><span class="st ${aktif ? "on" : ""}">${etiket}</span>` +
        `<p>${esc(t.role || "")}</p></div>`;
    }).join("") + `</div>`;
  }).join("");

  const sira = Math.max(1, aktifler.findIndex(t => t.id === tid) + 1);
  view.innerHTML = `<div class="map">
    ${aktifler.length > 1 ? `<nav class="yol-sekme" aria-label="Dil yolları">${sekmeler}</nav>` : ""}
    <section class="hero">
      <div class="hero-main">
        <div class="hero-kicker"><span class="label">Yol ${pad(sira)} · ${esc(track.name)}</span><span class="dim"></span><span class="label">Rütbe: ${esc(curRank.name)}</span></div>
        <h1 class="hero-title">${esc(kahraman1)}<br><em>${esc(kahraman2)}</em>${esc(kahraman3 || "")}</h1>
        <p class="hero-sub">${esc(track.tagline || "")}</p>
        <div class="hero-cta">${cta}${st.due_count ? `<a class="btn" href="#/tekrar">Tekrar · ${st.due_count} görev</a>` : ""}<a class="btn" href="#/tezgah/${track.dil || tid}">Serbest tezgah</a><a class="btn" href="#/sinav/${tid}">Sınav</a></div>
      </div>
      <div class="hero-cells">
        <div class="cell"><span class="label">Seri</span><span class="cell-val">${st.streak}<small>gün</small></span></div>
        <div class="cell"><span class="label">Tekrar bekleyen</span><span class="cell-val">${st.due_count}<small>görev</small></span></div>
        <div class="cell"><span class="label">Pafta</span><span class="cell-val">${lessonsDone}<small>/ ${lessonsTotal}</small></span><span class="bar"><i style="width:${pct(lessonsDone, lessonsTotal)}%"></i></span></div>
        <div class="cell"><span class="label">Görev</span><span class="cell-val">${gorevDone}<small>/ ${gorevTotal}</small></span><span class="bar"><i style="width:${pct(gorevDone, gorevTotal)}%"></i></span></div>
      </div>
    </section>
    ${track.hazir === false ? `<div class="callout tuzak" style="margin-top:16px"><div class="ct">Kurulum gerekiyor</div><p>Bu yolun yorumlayıcısı bu bilgisayarda bulunamadı. ${track.dil === "bash" ? "Git for Windows (Git Bash) kurulunca" : "Yorumlayıcı kurulunca"} paftalar çalışır.</p></div>` : ""}
    <div class="sec-head"><h2>Paftalar</h2><span class="dimline"></span><span class="label">${track.order.length} pafta · ${ranks.length} rütbe · her pafta: anlat → tahmin → görev</span></div>
    ${rankHtml}
    ${kazanimHtml(tv.kazanim, tid, track, steps)}
    <div class="sec-head"><h2>Yol haritası</h2><span class="dimline"></span><span class="label">purple team dilleri · aynı motor, yeni yol</span></div>
    <div class="roads">${roads}</div>
  </div>`;
  view.onclick = e => {
    const g = e.target.closest("[data-go]");
    if (g) location.hash = g.dataset.go;
  };
}

// ── DERS ──────────────────────────────────────────────────────────────────────
function stepDone(i) { return !!S.lesson.progress.steps[i]?.done; }

function lessonComplete() {
  return S.lesson.lesson.steps.every((_, i) => stepDone(i));
}

// Yanıt geldiğinde öğrenci hâlâ bu dersin ekranında mı? (await sonrası S.lesson başka derse dönmüş olabilir)
function dersAcik(tid, lid) { return S.mode === "lesson" && S.tid === tid && S.lesson?.lesson.id === lid; }

async function renderLesson(tid, lid, idx, opts = {}) {
  const same = S.mode === "lesson" && S.lesson && S.lesson.lesson.id === lid && S.tid === tid && !opts.force;
  if (!same) {
    let v;
    try { v = await guncelse(api(`/api/lesson/${tid}/${lid}`)); }
    catch (e) { view.innerHTML = `<div class="page"><div class="empty-state">Bu pafta bulunamadı: ${esc(lid)}<br><a class="btn" href="#/">Haritaya dön</a></div></div>`; return; }
    S.bench?.draft.bosalt();  // eski dersin bekleyen taslağı, S.lesson ve S.idx değişmeden kendi adımına yazılsın
    S.lesson = v; S.tid = tid; S.mode = "lesson";
    S.yol = v.track || { id: tid, dil: "python", ozellik: { roentgen: true, dis: "Bytecode" }, ranks: [] };
    formulYolu(S.yol);
    S.ranks = Object.fromEntries((S.yol.ranks || []).map(r => [r.id, r.name]));
    const L = v.lesson, loc = v.loc, mod = loc.module || { index: 0, title: "", rank: "" };
    view.onclick = null;
    view.innerHTML = `<div class="lesson">
      <div class="sheet-wrap"><article class="sheet" id="sheet">
        <div class="sheet-head">
          <div class="crumbs"><a class="label" href="#/yol/${tid}">← ${esc(S.yol.name || "Harita")}</a><span class="label">M${pad(mod.index)} · ${esc(mod.title)}</span><span class="label">${esc(L.id.toUpperCase())} / ${loc.total}</span>${L.kazanim?.length ? `<span class="label kz-etiket" title="Bu paftanın karşıladığı sertifika maddeleri">${esc(L.kazanim.join(" · "))}</span>` : ""}</div>
          <h1 class="sheet-title">${esc(L.title)}</h1>
          <p class="sheet-summary">${esc(L.summary)}</p>
          <div class="dims" id="dims"></div>
        </div>
        <div class="sheet-body" id="stepBody"></div>
        <div class="sheet-foot" id="stepFoot"></div>
        <div class="antet" id="antet"></div>
      </article></div>
      <section class="bench" id="bench"></section>
    </div>`;
    S.bench = new Bench($("#bench"), {
      track: tid,
      dil: S.yol.dil,
      ozellik: S.yol.ozellik,
      checkable: () => S.lesson.lesson.steps[S.idx]?.kind === "gorev",
      lessonRef: () => ({ lesson: lid, step: S.idx }),
      check: async code => {
        const adim = S.idx;
        const res = await api("/api/check", { track: tid, lesson: lid, step: adim, code });
        // Sonuç yalnız kendi dersinin yerel kaydına yazılır, yalnız kendi adımı açıksa ekrana boyanır; sunucu kaydı her durumda doğrudur
        if (!dersAcik(tid, lid)) { refreshHeader(); return null; }
        const adimlar = S.lesson.progress.steps;
        if (res.progress) adimlar[adim] = Object.assign(adimlar[adim] || {}, { attempts: res.progress.attempts });
        if (S.idx === adim) {
          if (res.progress) paintTaskStatus();
          return res;
        }
        if (res.status === "pass" && !stepDone(adim)) {
          adimlar[adim] = Object.assign(adimlar[adim] || {}, { done: true });
          paintDims();
          toast(`Görev ${adim + 1} geçti. Tekrar kutusuna eklendi.`);
        }
        refreshHeader();
        return null;
      },
      onPass: res => onPass(res),
      saveDraft: code => {
        const st = S.lesson.lesson.steps[S.idx];
        if (st?.kind !== "gorev") return null;
        S.lesson.progress.drafts[S.idx] = code;
        return api("/api/draft", { track: tid, lesson: lid, step: S.idx, code });
      },
    });
    $("#sheet").addEventListener("click", sheetClick);
  }
  showStep(Math.max(0, Math.min(idx, S.lesson.lesson.steps.length - 1)));
}

function antet() {
  const L = S.lesson.lesson, loc = S.lesson.loc, mod = loc.module || {};
  const doneN = L.steps.filter((_, i) => stepDone(i)).length;
  const durum = lessonComplete() ? "ONAYLI" : doneN ? `${doneN}/${L.steps.length}` : "ÇİZİLİYOR";
  return `<div><span>Pafta</span><b>${esc(L.id.toUpperCase())}</b></div><div><span>Konu</span><b>${esc(L.title)}</b></div><div><span>Rütbe</span><b>${esc(S.ranks[mod.rank] || mod.rank || "—")}</b></div>` +
    `<div><span>Adım</span><b>${S.idx + 1} / ${L.steps.length}</b></div><div><span>Modül</span><b>M${pad(mod.index || 0)} · ${esc(mod.title || "")}</b></div><div><span>Ölçek</span><b>1 : 1</b></div>` +
    `<div><span>Çizen</span><b>SEN</b></div><div><span>Tarih</span><b>${trDate()}</b></div><div><span>Durum</span><b>${durum}</b></div>`;
}

function paintDims() {
  const L = S.lesson.lesson;
  $("#dims").innerHTML = L.steps.map((s, i) =>
    `<button type="button" class="dim ${stepDone(i) ? "done" : ""} ${i === S.idx ? "cur" : ""}" data-step="${i}" title="${esc(s.title || KIND_LABEL[s.kind])}">` +
    `<span class="box">${stepDone(i) ? "✓" : KIND_ICON[s.kind]}</span><span class="k">${i + 1} · ${KIND_LABEL[s.kind]}</span></button>`).join("") +
    `<span class="dim-total">${L.steps.length} ADIM</span>`;
  $("#antet").innerHTML = antet();
}

const DIL_ETIKET = { python: "python|py", bash: "bash|sh", powershell: "powershell|ps1?", regex: "regex", sql: "sql", kql: "kql|kusto", spl: "spl|splunk", javascript: "javascript|js", cmd: "cmd|batch|bat", ad: "ad|ldap" };
const BOS_KOD = {
  python: "# Bu adımdaki örnekleri ⇢ Tezgaha al ile buraya getirip kurcalayabilirsin.\n",
  bash: "# Bu adımdaki örnekleri ⇢ Tezgaha al ile buraya getirip kurcalayabilirsin.\n",
  powershell: "# Bu adımdaki örnekleri ⇢ Tezgaha al ile buraya getirip kurcalayabilirsin.\n",
  cmd: "@echo off\nrem Soldaki örneği tezgaha alıp değiştirerek çalıştırabilirsin.\n",
  regex: "",
  sql: "-- Bu adımdaki örnekleri ⇢ Tezgaha al ile buraya getirip kurcalayabilirsin.\n-- Tablolar: ekipler, personel, sunucular, biletler, olcumler\n",
  kql: "// Bu adımdaki örnekleri ⇢ Tezgaha al ile buraya getirip kurcalayabilirsin.\n// Tablolar: ekipler, personel, sunucular, biletler, olcumler\n",
  spl: "sourcetype=biletler | head 5\n",
  ad: "# DC=pafta,DC=local dizini hazır. RFC 4515 LDAP filtresi (...) ya da Get-AD* komutu yazabilirsin.\nGet-ADUser -Filter *\n",
  javascript: "// Bu adımdaki örnekleri ⇢ Tezgaha al ile buraya getirip kurcalayabilirsin.\n",
  sigma: "# Soldaki Sigma kuralını tezgaha al; Olaylar kutusuna JSON örnekleri yaz.\n",
  yara: "// Soldaki YARA kuralını tezgaha al; Örnek veri kutusuna aranacak metni yaz.\n",
};
// Okuma yolları (C, PHP, Java, C#): kod çalıştırılmaz; görevlerde okunan kodun Python karşılığı yazılır
const OKUMA_BOS = "# Bu yolda okuduğun kod bu bilgisayarda çalıştırılamıyor.\n# Görevlerde onun yaptığını Python ile yazacaksın; tezgah o görevler içindir.\n";
const TAHMIN_DIL = {
  esql: { girdi: "Gerçek Elasticsearch korpusu:", etiket: "Çıktı JSON nesnesini sütun ve değerleriyle yaz", baslik: "ES|QL hangi tabloyu üretir?", ornek: '{"columns":["adet"],"values":[[2]]}', kod: "" },
  ingest: { girdi: "Gerçek ingest girdisi:", etiket: "Çıktı JSON nesnesini yaz", baslik: "Pipeline ve bulk sonucu ne olur?", ornek: "", kod: "" },
  rule: { girdi: "Gerçek Security kuralı korpusu:", etiket: "Çıktı JSON nesnesini yaz", baslik: "Kural önizlemesi ne üretir?", ornek: "", kod: "" },
  tshark: { girdi: "Komutun eğitim kaydı:", etiket: "Komutun çıktısını satır satır yaz; sütun aralarını sekmeyle ayır", baslik: "TShark komutu ne yazar?", kod: "" },
  "tcpdump-lab": { girdi: "Kontrollü yakalama laboratuvarı:", etiket: "Laboratuvarın paket, dosya ve boyut çıktısını satır satır yaz", baslik: "Yakalama hangi boyutları üretir?", kod: "" },
  wireshark: { girdi: "Filtrenin kayıt seçimi:", etiket: "Paketler: önekinden sonra eşleşen paket numaralarını virgülle yaz", baslik: "Görüntü filtresi hangi paketleri seçer?", ornek: "Paketler: 1, 2", kod: "" },
  bpf: { girdi: "Filtrenin kayıt seçimi:", etiket: "Paketler: önekinden sonra eşleşen paket numaralarını virgülle yaz", baslik: "BPF hangi paketleri seçer?", ornek: "Paketler: 1, 2", kod: "" },
  kibana: { girdi: "Sorgunun korpusu (mapping, belgeler ve context):", etiket: "Eşleşen belge kimliklerini her satıra bir tane, sonuç sırasıyla yaz", baslik: "KQL sorgusu hangi belgeleri seçer?", ornek: "e1\ne2", kod: "" },
  lucene: { girdi: "Sorgunun korpusu (mapping, belgeler ve context):", etiket: "Eşleşen belge kimliklerini her satıra bir tane, sonuç sırasıyla yaz", baslik: "Lucene sorgusu hangi belgeleri seçer?", ornek: "e1\ne2", kod: "" },
  eql: { girdi: "Sorgunun korpusu (mapping, olaylar ve context):", etiket: "Kimlikleri satır satır; bir olay dizisini e1 -> e2 biçiminde aynı satıra yaz", baslik: "EQL sorgusu hangi olayları veya dizileri seçer?", ornek: "e1 -> e2", kod: "" },
  sigma: { girdi: "Kural şu olaylarda deneniyor:", etiket: "Eşleşen olayların id değerlerini sırayla, her satıra bir tane yaz", baslik: "Hangi olaylar eşleşir?", ornek: "ör. 1", kod: "" },
  yara: { girdi: "Kural şu örnek veriyi tarıyor:", etiket: "Eşleşen kural adlarını her satıra bir tane yaz", baslik: "Hangi kurallar eşleşir?", ornek: "ör. Ilk_Kural", kod: "" },
  regex: { girdi: "Desen şu metinde aranıyor:", etiket: "Tahminin — yakalanan parçaları satır satır yaz", baslik: "Bu desen neleri yakalar?", kod: "" },
  sql: { etiket: "Tahminin — her sonuç satırını ayrı satıra, sütunları | ile ayırarak yaz (boş değer için NULL)",
    baslik: "Bu sorgu ne döndürür?", ornek: "ör. web01|72", kod: "-- Önce soldaki sorgunun sonucunu tahmin et.\n-- Tahmin ettikten sonra sorgu buraya gelir; değiştirip denersin.\n" },
  javascript: { kod: "// Önce soldaki kodun çıktısını tahmin et.\n// Tahmin ettikten sonra kod buraya gelir; değiştirip denersin.\n" },
  cmd: { kod: "@echo off\nrem Önce soldaki batch betiğinin çıktısını tahmin et.\n" },
  c: { baslik: "Bu C programı ne yazdırır?", kod: OKUMA_BOS },
  php: { baslik: "Bu PHP kodu ne yazdırır?", kod: OKUMA_BOS },
  java: { baslik: "Bu Java kodu ne yazdırır?", kod: OKUMA_BOS },
  csharp: { baslik: "Bu C# kodu ne yazdırır?", kod: OKUMA_BOS },
  asm: { baslik: "Bu assembly kodu ne yazdırır?", kod: OKUMA_BOS },
  ad: { etiket: "Tahminin — eşleşen sAMAccountName değerlerini (veya -Properties verildiyse | ile ayrılmış satırları) her satıra bir tane yaz",
    baslik: "Bu dizin sorgusu neleri döndürür?", ornek: "ör. ali.kaya", kod: "# Önce soldaki LDAP filtresinin / Get-AD* komutunun sonucunu tahmin et.\n# Tahmin ettikten sonra sorgu buraya gelir; değiştirip denersin.\n" },
  spl: { etiket: "Tahminin — her sonuç satırını ayrı satıra, sütunları | ile ayırarak yaz (boş değer boş kalır)",
    baslik: "Bu arama ne döndürür?", ornek: "ör. web01|72", kod: "" },
  kql: { etiket: "Tahminin — her sonuç satırını ayrı satıra, sütunları | ile ayırarak yaz (boş değer boş kalır)",
    baslik: "Bu sorgu ne döndürür?", ornek: "ör. web01|72", kod: "// Önce soldaki sorgunun sonucunu tahmin et.\n// Tahmin ettikten sonra sorgu buraya gelir; değiştirip denersin.\n" },
};

function firstCode(md, dil = "python") {
  const re = new RegExp("```(?:" + (DIL_ETIKET[dil] || dil) + ")(?![^\\n]*norun)[^\\n]*\\n([\\s\\S]*?)```");
  const m = (md || "").match(re);
  if (!m) return { code: "", stdin: "" };
  if (dil === "regex") { const [desen, metin] = regexParcala(m[1]); return { code: desen, stdin: metin }; }
  return { code: stripAnno(m[1]), stdin: "" };
}

function showStep(i) {
  S.bench?.draft.bosalt();  // bekleyen taslak, S.idx değişmeden kendi adımına yazılsın
  S.idx = i;
  const L = S.lesson.lesson, st = L.steps[i];
  const tid = S.tid, lid = L.id, dil = lessonLanguage(S.yol, L, st);
  const stepInput = lessonInput(st, L, dil);
  // Gerçek deney adımlarının koşucusu Röntgen/Bytecode desteklemez; düğmeleri gizle
  const gercek = st.meta?.motor === "ai-gercek";
  S.bench.ayarla(dil, gercek ? { ...(S.yol?.ozellik || {}), roentgen: false, dis: false } : S.yol?.ozellik || {});
  if (gercek && ["xray", "dis"].includes(S.bench.tab)) S.bench.show("out");
  const okuma = S.yol?.okuma_dili;           // C, PHP: okunan dil; tezgah ve görevler Python
  if (location.hash !== `#/ders/${tid}/${lid}/${i}`) history.replaceState(null, "", `#/ders/${tid}/${lid}/${i}`);
  api("/api/visit", { track: tid, lesson: lid, step: i, done: false }).catch(() => {});
  $$(".stamp", $("#sheet")).forEach(s => s.remove());
  paintDims();
  const head = `<div class="step-kind"><span class="tag ${st.kind}">${KIND_LABEL[st.kind].toLocaleUpperCase("tr")}</span><span class="label">Adım ${i + 1} / ${L.steps.length}</span></div>`;
  let body = "";
  if (st.kind === "anlat") {
    body = `<h2 class="step-title">${esc(st.title || "Anlatım")}</h2><div class="md">${render(st.body, { dil, stdin: stepInput })}</div>`;
    const ilk = firstCode(st.body, dil);
    const ornekStdin = ilk.stdin || stepInput || (["sigma", "yara"].includes(dil) ? L.steps.find(s => s.stdin)?.stdin || "" : "");
    S.bench.load({ code: okuma ? OKUMA_BOS : (ilk.code || BOS_KOD[dil] || ""), stdin: ornekStdin, resetCode: ilk.code });
  } else if (st.kind === "tahmin") {
    const [q, expl] = (st.body || "").split(/\n\?\?\?\s*\n?/);
    const prog = S.lesson.progress.steps[i];
    const td = TAHMIN_DIL[okuma || dil] || {};
    const girdiMetni = td.girdi || "Girdi kutusunda şu satırlar var:";
    const ipucuEtiket = td.etiket || "Tahminin — çıktıyı satır satır yaz (hata bekliyorsan hatanın adını yaz)";
    body = `<h2 class="step-title">${esc(st.title || td.baslik || "Bu kod ne yazdırır?")}</h2><div class="md">${render(q || "", { dil })}</div>` +
      codeBlock(st.code, st.code_dil || okuma || dil, { runnable: false, bench: false }) +
      (stepInput ? `<div class="md"><p>${girdiMetni}</p></div>${codeBlock(stepInput, "cikti")}` : "") +
      `<div class="guess"><span class="label">${ipucuEtiket}</span>` +
      `<textarea id="guessBox" rows="3" spellcheck="false" placeholder="${td.ornek || "ör. 42"}"></textarea>` +
      `<div class="guess-row"><button type="button" class="btn primary small" data-act="guess">Tahmini gönder</button>` +
      (prog?.done ? `<span class="label">daha önce: ${prog.guess_ok ? "doğru" : "yanlış"}</span>` : "") + `</div></div>` +
      `<div id="guessResult"></div><div class="md" id="guessExpl" hidden>${render(expl || "", { dil })}</div>`;
    S.bench.load({ code: td.kod ?? "# Önce soldaki kodun çıktısını tahmin et.\n# Tahmin ettikten sonra kod buraya gelir; değiştirip denersin.\n", stdin: stepInput, resetCode: ELASTIC_DIALECTS.includes(dil) ? "" : st.code });
  } else {
    const prog = S.lesson.progress.steps[i] || {};
    const draft = S.lesson.progress.drafts[i];
    body = `<h2 class="step-title">${esc(st.title || "Görev")}</h2><div class="md">${render(st.body, { dil, stdin: stepInput })}</div>` +
      `<div class="task-status" id="taskStatus"></div>` +
      `<div class="hints" id="hints"></div><div id="solution"></div>`;
    S.bench.load({ code: draft ?? st.starter ?? "", stdin: stepInput, resetCode: st.starter || "", checkable: true });
    S.hintN = 0;
  }
  const stepArgs = st.meta?.argv;
  const gercekNotice = st.meta?.motor === "ai-gercek"
    ? (st.meta.gereksinim === "docker" ? `<div class="ai-rozet">GERÇEK DENEY · izole Docker laboratuvarı · canlı HTTP; lab imajı yoksa görev geçmez</div>` : `<div class="ai-rozet">GERÇEK DENEY · ${st.meta.gereksinim === "torch" ? "yerel Python deneyi (.ai-venv)" : "yerel Ollama sohbet modeli"} · canlı ölçüm; bağımlılık yoksa görev geçmez</div>`) : "";
  const argNotice = gercekNotice + (stepArgs !== undefined ? `<div class="out-meta">Bu adımın argümanları: <code>${esc(Array.isArray(stepArgs) ? JSON.stringify(stepArgs) : String(stepArgs))}</code></div>` : "");
  $("#stepBody").innerHTML = head + argNotice + body;
  if (st.kind === "gorev") paintTaskStatus();
  paintFoot();
  if (stepDone(i) && st.kind === "gorev") stamp("ONAYLANDI", `görev · ${trDate()}`, false);
  $(".sheet-wrap").scrollTop = 0;
}

function paintTaskStatus() {
  const st = S.lesson.lesson.steps[S.idx];
  const prog = S.lesson.progress.steps[S.idx] || {};
  const a = prog.attempts || 0;
  const passed = stepDone(S.idx);
  const canSolve = st.has_solution && (a >= 2 || passed || prog.revealed);
  $("#taskStatus").innerHTML =
    `<span class="st ${passed ? "pass" : ""}">${passed ? "✓ geçti" : a ? `${a} deneme` : "henüz denemedin"}</span>` +
    `<span class="label">Ctrl+⇧+↵ ile kontrol et</span><span style="flex:1"></span>` +
    (st.hints.length ? `<button type="button" class="btn small" data-act="hint" ${S.hintN >= st.hints.length ? "disabled" : ""}>İpucu ${S.hintN}/${st.hints.length}</button>` : "") +
    (st.has_solution ? `<button type="button" class="btn small" data-act="solution" ${canSolve ? "" : `title="2 denemeden sonra açılır"`}>Çözümü göster</button>` : "");
}

function paintFoot() {
  const L = S.lesson.lesson, st = L.steps[S.idx], last = S.idx === L.steps.length - 1;
  const blocked = st.kind !== "anlat" && !stepDone(S.idx);
  const next = S.lesson.loc.next;
  let right;
  if (last) {
    right = lessonComplete() || !blocked
      ? (next ? `<button type="button" class="btn primary" data-act="finish">Paftayı bitir → ${esc(next.toUpperCase())}</button>` : `<button type="button" class="btn primary" data-act="finish">Paftayı bitir ✓</button>`)
      : `<button type="button" class="linkish" data-act="skip">şimdilik atla</button><button type="button" class="btn primary" disabled>${st.kind === "gorev" ? "Önce görevi geç" : "Önce tahmin et"}</button>`;
  } else {
    right = blocked
      ? `<button type="button" class="linkish" data-act="skip">şimdilik atla</button><button type="button" class="btn primary" disabled>${st.kind === "gorev" ? "Önce görevi geç" : "Önce tahmin et"}</button>`
      : `<button type="button" class="btn primary" data-act="next">İleri →</button>`;
  }
  $("#stepFoot").innerHTML = `<button type="button" class="btn" data-act="prev" ${S.idx === 0 ? "disabled" : ""}>← Geri</button><span class="grow"></span>${right}`;
  if (lessonComplete() && last) {
    $("#stepBody").insertAdjacentHTML("beforeend", `<div class="done-card"><h3>Pafta onaylandı.</h3><p>Bu paftanın tüm adımlarını bitirdin. Görevler tekrar kutusuna girdi: yarın, sonra 3, 7, 16 ve 35 gün sonra yeniden sorulacaklar — kalıcı öğrenme bu aralıklarla olur.</p></div>`);
  }
}

function stamp(text, sub, anim = true) {
  $$(".stamp", $("#sheet")).forEach(s => s.remove());
  $("#sheet").insertAdjacentHTML("afterbegin", `<div class="stamp ${anim ? "thunk" : ""}">${esc(text)}<small>${esc(sub)}</small></div>`);
}

async function onPass(res) {
  const i = S.idx;
  const was = stepDone(i);
  S.lesson.progress.steps[i] = Object.assign(S.lesson.progress.steps[i] || {}, { done: true, attempts: res.progress?.attempts });
  paintDims();
  paintTaskStatus();
  paintFoot();
  stamp(lessonComplete() ? "PAFTA ONAYLANDI" : "ONAYLANDI", `${lessonComplete() ? S.lesson.lesson.id.toUpperCase() : "görev " + (i + 1)} · ${trDate()}`);
  if (!was) toast("Görev geçti. Tekrar kutusuna eklendi.");
  refreshHeader();
}

async function sheetClick(e) {
  const d = e.target.closest("[data-step]");
  if (d) { showStep(+d.dataset.step); return; }
  const a = e.target.closest("[data-act]");
  if (!a) return;
  const act = a.dataset.act, L = S.lesson.lesson, tid = S.tid, lid = L.id, i = S.idx;
  if (act === "run" || act === "bench") {
    const block = a.closest(".code");
    const src = block.dataset.src;
    const detection = ["sigma", "yara", "packets"].includes(dilAdi(S.yol?.dil));
    const elastic = S.yol?.dil === "elastic";
    const metin = block.dataset.stdin || (elastic ? lessonInput(L.steps[i], L, lessonLanguage(S.yol, L, L.steps[i]))
      : detection ? (S.bench.stdin.value || L.steps[i]?.stdin || L.steps.find(s => s.stdin)?.stdin || "") : "");
    if (act === "bench") {
      S.bench.setCode(src);
      if (metin || dilAdi(S.yol?.dil) === "regex") S.bench.setStdin(metin);
      toast("Tezgaha alındı");
      return;
    }
    const out = $(".run-out", block);
    out.hidden = false;
    out.textContent = "çalışıyor…";
    try {
      const res = await api("/api/run", { track: tid, code: src, stdin: metin, mode: "run", lesson: lid, step: i });
      if (res.eslesmeler) {
        out.innerHTML = res.error ? `<span style="color:var(--bad)">${esc(res.error.type + ": " + res.error.msg)}</span>`
          : res.eslesmeler.length ? `<span class="label">${res.eslesmeler.length} eşleşme</span>\n` + res.eslesmeler.map(e => esc(JSON.stringify(e.metin))).join("\n")
          : '<span class="label">eşleşme yok</span>';
        return;
      }
      if (["sigma", "yara"].includes(S.yol?.dil) && !res.error) {
        out.classList.add("sql");
        out.innerHTML = detectionOutput(res, S.yol.dil, 25);
        return;
      }
      if (Array.isArray(res.elastic_ids)) {
        out.classList.add("sql");
        out.innerHTML = elasticOutput(res, 25);
        return;
      }
      if (res.elastic_native) {
        out.classList.add("sql");
        out.innerHTML = `<pre class="out">${segsHtml(res.segs)}</pre>` + sqlTablolar(res.tablolar, 25) +
          `<div class="out-meta">${esc(res.elastic_backend)}</div>` + errCard(res.error);
        return;
      }
      if (res.packet_backend && ["tshark", "tcpdump-lab"].includes(res.packet_dialect)) {
        out.classList.add("sql");
        out.innerHTML = `<pre class="out">${segsHtml(res.segs)}</pre>` + sqlTablolar(res.tablolar, 25) + errCard(res.error);
        return;
      }
      if (res.tablolar) {
        out.classList.add("sql");
        out.innerHTML = sqlTablolar(res.tablolar, 25, res.kql) +
          (res.error ? `<span style="color:var(--bad)">${esc(res.error.type + ": " + res.error.msg)}</span>` : "");
        return;
      }
      const txt = (res.segs || []).map(s => s[1]).join("");
      out.innerHTML = esc(txt) + (res.error ? `<span style="color:var(--bad)">${txt ? "\n" : ""}${esc(res.error.type + ": " + res.error.msg)}</span>` : "") || '<span class="label">çıktı yok</span>';
    } catch (err) { out.textContent = "Sunucuya ulaşılamadı."; }
    return;
  }
  if (act === "prev") { if (i > 0) showStep(i - 1); return; }
  if (act === "next" || act === "skip") {
    if (L.steps[i].kind === "anlat" && !stepDone(i)) {
      S.lesson.progress.steps[i] = { done: true };
      await api("/api/visit", { track: tid, lesson: lid, step: i, done: true }).catch(() => {});
      refreshHeader();
      if (!dersAcik(tid, lid) || S.idx !== i) return;  // yanıt gelene dek başka yere geçildiyse öğrenci oradan çekilmez
    }
    if (i < L.steps.length - 1) showStep(i + 1);
    else if (act === "skip" && S.lesson.loc.next) location.hash = `#/ders/${tid}/${S.lesson.loc.next}/0`;
    return;
  }
  if (act === "finish") {
    if (L.steps[i].kind === "anlat" && !stepDone(i)) {
      await api("/api/visit", { track: tid, lesson: lid, step: i, done: true }).catch(() => {});
      if (!dersAcik(tid, lid) || S.idx !== i) return;
    }
    location.hash = S.lesson.loc.next ? `#/ders/${tid}/${S.lesson.loc.next}/0` : "#/";
    return;
  }
  if (act === "guess") {
    const g = $("#guessBox").value;
    if (!g.trim()) { toast("Önce bir tahmin yaz"); return; }
    a.disabled = true;
    try {
      const r = await api("/api/guess", { track: tid, lesson: lid, step: i, guess: g });
      refreshHeader();
      if (!dersAcik(tid, lid)) return;
      if (!stepDone(i)) S.lesson.progress.steps[i] = { done: true, guess_ok: r.correct };
      if (S.idx !== i) { paintDims(); return; }
      const actual = segsHtml((r.result.segs || []).filter(s => s[0] === "out"));
      const errTxt = r.result.error ? esc(`${r.result.error.type}: ${r.result.error.msg}`) : "";
      $("#guessResult").innerHTML =
        `<div class="result-line ${r.correct ? "good" : "badc"}">${r.correct ? "✓ Doğru tahmin" : "✗ Tahmin tutmadı"}</div>` +
        `<div class="verdict"><div class="${r.correct ? "good" : "badc"}"><span class="label">senin tahminin</span><pre>${esc(g)}</pre></div>` +
        `<div class="good"><span class="label">gerçek çıktı</span><pre>${actual}${errTxt ? `<span style="color:var(--bad)">${actual ? "\n" : ""}${errTxt}</span>` : ""}</pre></div></div>`;
      $("#guessExpl").hidden = false;
      if (!S.yol?.okuma_dili) S.bench.load({ code: L.steps[i].code, stdin: lessonInput(L.steps[i], L, lessonLanguage(S.yol, L, L.steps[i])), resetCode: L.steps[i].code });
      paintDims();
      paintFoot();
    } catch (err) { toast("Sunucuya ulaşılamadı"); }
    a.disabled = false;
    return;
  }
  if (act === "hint") {
    const st = L.steps[i];
    if (S.hintN < st.hints.length) {
      $("#hints").insertAdjacentHTML("beforeend", `<div class="callout ipucu"><div class="ct">İpucu ${S.hintN + 1}</div>${render(st.hints[S.hintN], { dil: lessonLanguage(S.yol, L, st), stdin: lessonInput(st, L, lessonLanguage(S.yol, L, st)) })}</div>`);
      S.hintN++;
      paintTaskStatus();
    }
    return;
  }
  if (act === "solution") {
    const prog = S.lesson.progress.steps[i] || {};
    if ((prog.attempts || 0) < 2 && !stepDone(i) && !prog.revealed &&
      !confirm("Henüz 2 kez denemedin. Çözüme bakarsan bu görev yarın tekrar karşına çıkar. Yine de bakmak istiyor musun?")) return;
    try {
      const r = await api("/api/solution", { track: tid, lesson: lid, step: i });
      refreshHeader();
      if (!dersAcik(tid, lid)) return;
      S.lesson.progress.steps[i] = Object.assign(S.lesson.progress.steps[i] || {}, { revealed: true });
      if (S.idx !== i) return;
      $("#solution").innerHTML = `<div class="callout derin"><div class="ct">Örnek çözüm</div>${codeBlock(r.solution, lessonLanguage(S.yol, L, L.steps[i]), { dil: lessonLanguage(S.yol, L, L.steps[i]), stdin: lessonInput(L.steps[i], L, lessonLanguage(S.yol, L, L.steps[i])) })}<p>Çözümü kopyalamak yerine kapatıp kendin yeniden yaz — beyin ancak üretirken öğrenir.</p></div>`;
      paintTaskStatus();
    } catch (err) { toast(err.message); }
  }
}

// ── TEKRAR ────────────────────────────────────────────────────────────────────
async function renderReview() {
  S.mode = "review";
  view.onclick = null;
  const [st, r] = await guncelse(Promise.all([refreshHeader(), api("/api/review")]));
  const boxes = r.kutular || [0, 0, 0, 0, 0, 0];
  const yolAdi = Object.fromEntries((st?.tracks || []).map(t => [t.id, t.name]));
  const names = ["Kutu 1 · 1 gün", "Kutu 2 · 3 gün", "Kutu 3 · 7 gün", "Kutu 4 · 16 gün", "Kutu 5 · 35 gün", "Ustalaştın"];
  view.innerHTML = `<div class="page">
    <span class="label">Aralıklı tekrar · Leitner kutuları</span>
    <h1 class="page-title">Tekrar</h1>
    <p class="page-sub">Geçtiğin her görev buraya düşer ve giderek uzayan aralıklarla yeniden sorulur. Her seferinde boş sayfadan yazarsın; doğru yazınca bir üst kutuya çıkar. Çözüme bakarsan kutu 1'e döner.</p>
    <div class="boxes">${boxes.map((n, i) => `<div><span class="label">${names[i]}</span><b>${n}</b></div>`).join("")}</div>
    ${r.items.length ? `<div class="rev-list">${r.items.map(it =>
      `<a class="rev" href="#/tekrar/${it.track}/${it.lesson}/${it.step}"><span class="rid">${esc(yolAdi[it.track] || it.track)}<br>${esc(it.lesson.toUpperCase())} · K${it.box}</span>` +
      `<span><b>${esc(it.title)}</b><small>${esc(it.lesson_title)} · vadesi ${esc(it.due)}</small></span><span class="btn small">Çöz →</span></a>`).join("")}</div>`
      : `<div class="empty-state">Bugün tekrar bekleyen görev yok.<br><br><a class="btn primary" href="#/">Haritaya dön</a></div>`}
  </div>`;
}

// Tekrar ekranında süren Kontrol'ler: öğrenci çıkıp aynı göreve dönerse sonucu yeni ekran alır
const TEKRAR_KONTROL = new Map();

async function renderReviewSolve(tid, lid, idx) {
  S.mode = "review-solve";
  view.onclick = null;
  const anahtar = `${tid}/${lid}/${idx}`;
  const suren = TEKRAR_KONTROL.get(anahtar);  // ekran yüklenirken biten sonuç da kaçmasın diye yüklemeden önce alınır
  const v = await guncelse(api(`/api/lesson/${tid}/${lid}`));
  const st = v.lesson.steps[idx];
  S.yol = v.track || { id: tid, dil: "python", ozellik: { roentgen: true, dis: "Bytecode" } };
  formulYolu(S.yol);
  const dil = lessonLanguage(S.yol, v.lesson, st);
  view.innerHTML = `<div class="lesson">
    <div class="sheet-wrap"><article class="sheet" id="sheet">
      <div class="sheet-head"><div class="crumbs"><a class="label" href="#/tekrar">← Tekrar</a><span class="label">${esc(S.yol.name || tid)} · ${esc(lid.toUpperCase())} · ${esc(v.lesson.title)}</span></div>
      <h1 class="sheet-title">${esc(st.title || "Görev")}</h1><p class="sheet-summary">Boş sayfadan, ezberden değil anlayarak yaz.</p></div>
      <div class="sheet-body"><div class="md">${render(st.body, { dil, stdin: lessonInput(st, v.lesson, dil) })}</div><div id="revStatus"></div><div class="hints" id="hints"></div></div>
      <div class="sheet-foot"><a class="btn" href="#/ders/${tid}/${lid}/0">Paftayı aç</a><span class="grow"></span><a class="btn" href="#/tekrar">Listeye dön</a></div>
    </article></div>
    <section class="bench" id="bench"></section></div>`;
  const acik = () => S.mode === "review-solve" && S.bench === bench && bench.host.isConnected;  // yanıt geldiğinde bu Tekrar ekranı hâlâ açık mı?
  const kontrol = async soz => {
    const res = await soz;
    if (acik()) return res;
    refreshHeader();
    return null;
  };
  const bench = S.bench = new Bench($("#bench"), {
    track: tid,
    dil,
    ozellik: S.yol.ozellik,
    checkable: () => true,
    lessonRef: () => ({ lesson: lid, step: idx }),
    check: code => {
      const soz = api("/api/check", { track: tid, lesson: lid, step: idx, code, review: true });
      const kayit = { soz, kod: code };
      TEKRAR_KONTROL.set(anahtar, kayit);
      const sil = () => { if (TEKRAR_KONTROL.get(anahtar) === kayit) TEKRAR_KONTROL.delete(anahtar); };
      soz.then(sil, sil);
      return kontrol(soz);
    },
    onPass: async res => {
      stamp("TEKRAR GEÇTİ", res.review ? `kutu ${res.review.box} · ${trDate()}` : trDate());
      const due = (await api("/api/review")).items.filter(it => !(it.track === tid && it.lesson === lid && it.step === idx));
      refreshHeader();
      if (!acik()) return;
      $("#revStatus").innerHTML = `<div class="done-card"><h3>Doğru.</h3><p>${res.review?.box >= 6 ? "Bu görevde ustalaştın." : `Kutu ${res.review?.box}'e çıktı; sonraki tekrar ${esc(res.review?.due || "")}.`}</p>` +
        (due.length ? `<a class="btn primary" href="#/tekrar/${due[0].track}/${due[0].lesson}/${due[0].step}">Sıradaki →</a>` : `<a class="btn primary" href="#/tekrar">Hepsi bitti →</a>`) + `</div>`;
    },
  });
  S.bench.load({ code: suren ? suren.kod : st.starter || "", stdin: lessonInput(st, v.lesson, dil), resetCode: st.starter || "", checkable: true });
  if (suren) bench.check(kontrol(suren.soz));
}

// ── SINAV · ER MEYDANI ───────────────────────────────────────────────────────
// Süreli deneme: sorular yolun tahmin ve görev adımlarından; ipucu, Kontrol ve çözüm kapalı,
// hiçbir cevabın doğru olup olmadığı sınav bitmeden söylenmez.
const TUR_ADI = { karisik: "Karışık", tahmin: "Yalnızca tahmin", gorev: "Yalnızca görev" };
const HAVUZ_ADI = { hepsi: "Bütün paftalar", biten: "Bitirdiğim paftalar" };

function sureYaz(sn) {
  sn = Math.max(0, Math.round(sn || 0));
  const s = Math.floor(sn / 3600), d = Math.floor((sn % 3600) / 60), n = sn % 60;
  return s ? `${s}:${pad(d)}:${pad(n)}` : `${pad(d)}:${pad(n)}`;
}

function sinavTemizle() {
  clearInterval(S.sinavSaat);
  S.sinavSaat = null;
}

const cevapli = (q, v) => !!(v && v.trim() && (q.kind !== "gorev" || v !== (q.starter || "")));

async function renderExamSetup(onYol, onSert, onBolum) {
  S.mode = "sinav";
  view.onclick = null;
  let d;
  try { d = await guncelse(api("/api/sinav")); }
  catch (e) { view.innerHTML = `<div class="page"><div class="empty-state">Sunucuya ulaşılamadı: ${esc(e.message)}</div></div>`; return; }
  refreshHeader();
  const yollar = d.yollar || [];
  if (!yollar.length) { view.innerHTML = `<div class="page"><div class="empty-state">Henüz aktif bir yol yok.</div></div>`; return; }
  const sonYol = S.state?.last?.track;
  const sec = {
    yol: yollar.some(y => y.id === onYol) ? onYol : yollar.some(y => y.id === sonYol) ? sonYol : yollar[0].id,
    kapsam: onSert ? onSert + (onBolum ? "|" + onBolum : "") : "", adet: 20, tur: "karisik", havuz: "hepsi",
  };
  const a = d.aktif;
  const aktifHtml = a ? `<div class="callout derin meydan-suren"><div class="ct">Süren sınav · ${esc(a.kapsam)}</div>` +
    `<p>${a.cevaplanan}/${a.adet} soru cevaplı · ${a.kalan_sn ? `kalan ${sureYaz(a.kalan_sn)}` : "süre doldu, puanlanmayı bekliyor"}</p>` +
    `<p class="guess-row"><a class="btn primary small" href="#/sinav/aktif">${a.kalan_sn ? "Meydana dön →" : "Gör"}</a>` +
    `<button type="button" class="btn small" data-act="bitir" data-no="${a.no}">Bitir ve puanla</button>` +
    `<button type="button" class="linkish" data-act="vazgec" data-no="${a.no}">vazgeç · bu sınav kaydedilmez</button></p></div>` : "";
  const gecmis = d.gecmis || [];
  const gecmisHtml = gecmis.length ? `<div class="rev-list">${gecmis.map(g =>
    `<a class="rev gecmis" href="#/sinav/sonuc/${g.no}"><span class="rid">SINAV ${g.no}<br>${esc(g.tarih || "")}</span>` +
    `<span><b>${esc(g.kapsam || "")}</b><small>${g.adet} soru · ${esc(TUR_ADI[g.tur] || g.tur || "")} · ${sureYaz(g.gecen_sn)} / ${sureYaz(g.sure_sn)}</small></span>` +
    `<span class="mini-muhur ${g.gecti ? "kabul" : "ret"}">${g.gecti ? "KABUL" : "RET"} · %${g.yuzde}</span></a>`).join("")}</div>`
    : `<div class="empty-state">Henüz meydana çıkmadın. İlk sınavın burada görünecek.</div>`;
  view.innerHTML = `<div class="page meydan">
    <span class="label">Süreli deneme · ipucu yok · Kontrol yok · çözüm yok</span>
    <h1 class="page-title">Er Meydanı</h1>
    <p class="page-sub">Paftalarda öğrendiğini sertifika sınavı gibi ölç. Sorular yolun tahmin ve görev adımlarından seçilir; sertifika kapsamında bölümlerin sınavdaki ağırlığına göre dağıtılır. Sınav bitene kadar hiçbir cevabın doğru olup olmadığını söylemez: tahminler gerçek çıktıyla, görevler görev testleriyle sonda puanlanır.</p>
    ${aktifHtml}
    <section class="kunye" id="kunye"></section>
    <div class="sec-head"><h2>Geçmiş</h2><span class="dimline"></span><span class="label">son ${gecmis.length} sınav</span></div>
    ${gecmisHtml}
  </div>`;
  const kunye = $("#kunye");
  const ciz = () => {
    const y = yollar.find(x => x.id === sec.yol);
    const [sid, bkod] = sec.kapsam.split("|");
    const sert = y.sertifikalar.find(s => s.id === sid);
    if (sec.kapsam && !sert) sec.kapsam = "";
    const secenek = [`<option value="">Bütün yol · bütün paftalar</option>`].concat((y.sertifikalar || []).flatMap(s => [
      `<option value="${at(s.id)}" ${sec.kapsam === s.id ? "selected" : ""}>${esc(s.ad)} · bütün sınav</option>`,
      ...s.bolumler.map(b => `<option value="${at(s.id + "|" + b.kod)}" ${sec.kapsam === s.id + "|" + b.kod ? "selected" : ""}>${esc(s.ad)} › ${esc(String(b.kod))} · ${esc(b.baslik)}${b.agirlik ? ` (%${b.agirlik})` : ""}</option>`)]));
    const hap = (alan, degerler, adlar) => `<div class="hap" data-alan="${alan}">${degerler.map(v =>
      `<button type="button" data-deger="${at(v)}" class="${String(sec[alan]) === String(v) ? "on" : ""}">${esc(String(adlar ? adlar[v] : v))}</button>`).join("")}</div>`;
    const sv = sert?.sinav || {};
    const adetler = [5, 10, 20, 40];
    if (sv.soru && !adetler.includes(sv.soru) && !bkod) adetler.push(sv.soru);
    kunye.innerHTML = `<div class="kunye-form">
        <label class="kf genis"><span class="label">Yol</span><select data-alan="yol">${yollar.map(x => `<option value="${at(x.id)}" ${x.id === sec.yol ? "selected" : ""}>${esc(x.name)}${x.sertifikalar.length ? " · " + esc(x.sertifikalar.map(s => s.ad).join(", ")) : ""}</option>`).join("")}</select></label>
        <label class="kf genis"><span class="label">Kapsam</span><select data-alan="kapsam">${secenek.join("")}</select>
          ${sert ? `<small>${esc(sert.tam_ad || sert.ad)}${sv.soru ? ` · gerçek sınav ${sv.soru} soru, ${sv.dakika} dk, geçme %${sv.gecme}` : ""}</small>` : `<small>${y.sertifikalar.length ? "Bir sertifika seçersen sorular onun bölüm ağırlıklarına göre dağılır." : "Bu yol henüz bir sertifikanın konu listesine eşlenmedi; sorular modüllere yayılır."}</small>`}</label>
        <div class="kf"><span class="label">Soru</span>${hap("adet", adetler)}</div>
        <div class="kf"><span class="label">Tür</span>${hap("tur", ["karisik", "tahmin", "gorev"], TUR_ADI)}</div>
        <div class="kf"><span class="label">Havuz</span>${hap("havuz", ["hepsi", "biten"], HAVUZ_ADI)}</div>
      </div>
      <div class="kunye-ozet">
        <div class="ko-sure"><span class="label">Süre</span><b id="koSure">—</b></div>
        <div class="ko-satir" id="koHavuz">havuz hesaplanıyor…</div>
        <div class="ko-satir">tahmin 2 dk · görev 6 dk · geçme %${sv.gecme || 70}</div>
        <button type="button" class="btn primary" id="meydanaCik" ${a ? "disabled title=\"Önce süren sınavı bitir\"" : ""}>Meydana çık →</button>
      </div>`;
    onizle();
  };
  let istek = 0;
  const onizle = async () => {
    const [sid, bkod] = sec.kapsam.split("|");
    const n = ++istek;
    try {
      const h = await guncelse(api("/api/sinav/havuz", { yol: sec.yol, sertifika: sid || null, bolum: bkod || null, adet: sec.adet, tur: sec.tur, havuz: sec.havuz }));
      if (n !== istek) return;
      $("#koSure").textContent = h.adet ? sureYaz(h.sure_sn) : "—";
      const az = h.adet < sec.adet ? ` · havuzda yalnızca <b>${h.adet}</b> soru var` : "";
      $("#koHavuz").innerHTML = `havuzda ${h.tahmin} tahmin · ${h.gorev} görev${az}`;
      $("#meydanaCik").disabled = !!a || !h.adet;
    } catch (e) { if (n === istek) $("#koHavuz").textContent = e.message; }
  };
  kunye.addEventListener("change", e => {
    const s = e.target.closest("select[data-alan]");
    if (!s) return;
    sec[s.dataset.alan] = s.value;
    if (s.dataset.alan === "yol") sec.kapsam = "";
    ciz();
  });
  kunye.addEventListener("click", async e => {
    const h = e.target.closest(".hap button");
    if (h) {
      const alan = h.closest(".hap").dataset.alan;
      sec[alan] = alan === "adet" ? +h.dataset.deger : h.dataset.deger;
      ciz();
      return;
    }
    if (e.target.closest("#meydanaCik")) {
      const [sid, bkod] = sec.kapsam.split("|");
      e.target.disabled = true;
      try {
        await api("/api/sinav/basla", { yol: sec.yol, sertifika: sid || null, bolum: bkod || null, adet: sec.adet, tur: sec.tur, havuz: sec.havuz });
        location.hash = "#/sinav/aktif";
      } catch (err) { toast(err.message); e.target.disabled = false; }
    }
  });
  view.onclick = async e => {
    const b = e.target.closest(".meydan-suren [data-act]");
    if (!b) return;
    const no = +b.dataset.no;
    const sira = S.sira;
    if (b.dataset.act === "vazgec") {
      if (!confirm("Süren sınav silinecek, sonucu kaydedilmeyecek. Vazgeçmek istiyor musun?")) return;
      try { await api("/api/sinav/vazgec", { no }); if (sira === S.sira) route(); } catch (err) { toast(err.message); }
    } else if (b.dataset.act === "bitir") {
      b.disabled = true;
      b.textContent = "puanlanıyor…";
      try { const r = await api("/api/sinav/bitir", { no }); sonucaGec(r.no, sira); }
      catch (err) { toast(err.message); b.disabled = false; }
    }
  };
  ciz();
}

async function renderExam() {
  S.mode = "sinav-aktif";
  view.onclick = null;
  let a;
  try { a = await guncelse(api("/api/sinav/aktif")); }
  catch (e) { location.hash = "#/sinav"; return; }
  const ilkBos = a.sorular.findIndex((q, j) => !cevapli(q, a.cevaplar[j]));
  S.sinav = { a, i: Math.max(0, ilkBos), bitis: Date.now() + a.kalan_sn * 1000, bitiyor: false,
    yaz: debounce((i, v) => cevapKaydet(i, v), 600) };
  S.yol = a.track;
  formulYolu(S.yol);
  view.innerHTML = `<div class="lesson meydan-kip">
    <div class="sheet-wrap"><article class="sheet" id="sheet">
      <div class="sheet-head">
        <div class="crumbs"><a class="label" href="#/sinav">← Er meydanı</a><span class="label">${esc(a.kapsam)}</span><span class="label">Sınav ${a.no} · ${esc(TUR_ADI[a.tur] || a.tur)}</span></div>
        <div class="meydan-ust"><h1 class="sheet-title" id="soruBaslik"></h1>
          <div class="saat" id="saat" title="Süre bitince sınav kendiliğinden puanlanır"><span class="label">kalan</span><b>--:--</b><span class="saat-serit"><i></i></span></div></div>
        <div class="serit" id="serit" role="navigation" aria-label="Sorular"></div>
      </div>
      <div class="sheet-body" id="soruBody"></div>
      <div class="sheet-foot" id="soruFoot"></div>
    </article></div>
    <section class="bench" id="bench"></section>
    <section class="kagit" id="kagit" hidden></section>
  </div>`;
  S.bench = new Bench($("#bench"), {
    track: a.yol,
    dil: a.track.dil,
    ozellik: a.track.ozellik,
    checkable: () => false,
    lessonRef: () => { const q = S.sinav?.a.sorular[S.sinav.i]; return q ? { lesson: q.lesson, step: q.step } : {}; },
    saveDraft: code => (S.sinav ? cevapKaydet(S.sinav.i, code) : null),
  });
  $("#sheet").addEventListener("click", sinavClick);
  $("#kagit").addEventListener("click", sinavClick);
  soruGoster(S.sinav.i);
  sinavSaat();
}

function cevapKaydet(i, cevap) {
  const s = S.sinav;
  if (!s || s.bitiyor) return null;
  s.a.cevaplar[i] = cevap;
  if ($("#serit")) paintSerit();
  const kagit = $("#kagit");
  if (kagit && !kagit.hidden) paintKagit();
  return api("/api/sinav/cevap", { no: s.a.no, soru: i, cevap })
    .then(r => { if (!r.ok) toast("Süre doldu; bu cevap kaydedilmedi"); return r; });
}

// Açık sorunun bekleyen cevabını hemen yaz (soru değişirken, sınav biterken, sayfadan çıkarken)
function cevapBosalt() {
  const s = S.sinav;
  if (!s) return Promise.resolve();
  const q = s.a.sorular[s.i];
  let v;
  if (q.kind === "gorev") { S.bench.draft.cancel(); v = S.bench.ed.value; }
  else { s.yaz.cancel(); v = $("#cevapKutu")?.value ?? ""; }
  const eski = s.a.cevaplar[s.i] ?? (q.kind === "gorev" ? q.starter || "" : "");
  if (eski === v) return Promise.resolve();
  return cevapKaydet(s.i, v) || Promise.resolve();
}

function paintSerit() {
  const s = S.sinav, a = s.a;
  $("#serit").innerHTML = a.sorular.map((q, j) => {
    const cls = [cevapli(q, a.cevaplar[j]) ? "dolu" : "", j === s.i ? "cur" : "", a.isaretli.includes(j) ? "isaret" : ""].join(" ");
    return `<button type="button" class="${cls}" data-soru="${j}" title="Soru ${j + 1} · ${KIND_LABEL[q.kind]}${a.isaretli.includes(j) ? " · işaretli" : ""}"><b>${j + 1}</b><span>${q.kind === "tahmin" ? "T" : "G"}</span></button>`;
  }).join("");
}

// Tahmin sorularında sağdaki panel: optik cevap kâğıdı
function paintKagit() {
  const s = S.sinav, a = s.a;
  const n = a.sorular.filter((q, j) => cevapli(q, a.cevaplar[j])).length;
  $("#kagit").innerHTML = `<div class="kagit-ic">
    <div class="kagit-bas"><span class="label">Cevap kâğıdı</span><b>${n}<small>/ ${a.sorular.length}</small></b><span class="label">cevaplı</span></div>
    <ol class="optik">${a.sorular.map((q, j) => `<li class="${j === s.i ? "cur" : ""}" data-soru="${j}"><span class="on">${pad(j + 1)}</span>` +
      `<span class="tur">${q.kind === "tahmin" ? "TAHMİN" : "GÖREV"}</span><i class="kabarcik ${cevapli(q, a.cevaplar[j]) ? "dolu" : ""}"></i>` +
      `<i class="bayrak">${a.isaretli.includes(j) ? "⚑" : ""}</i></li>`).join("")}</ol>
    <p class="out-meta">dolu daire = cevaplı · ⚑ = sonra bakacağın soru · cevaplar kendiliğinden kaydedilir</p>
    <button type="button" class="btn primary" data-act="bitir">Sınavı bitir ve puanla</button>
  </div>`;
}

function paintSinavFoot() {
  const s = S.sinav, a = s.a, i = s.i, isaret = a.isaretli.includes(i), son = i === a.sorular.length - 1;
  $("#soruFoot").innerHTML = `<button type="button" class="btn" data-act="onceki" ${i === 0 ? "disabled" : ""}>← Önceki</button>` +
    `<button type="button" class="btn small ${isaret ? "ok" : ""}" data-act="isaretle">⚑ ${isaret ? "İşareti kaldır" : "İşaretle"}</button><span class="grow"></span>` +
    (son ? "" : `<button type="button" class="btn primary" data-act="sonraki">Sonraki →</button>`) +
    `<button type="button" class="btn ${son ? "primary" : ""}" data-act="bitir">Sınavı bitir</button>`;
}

function soruGoster(i) {
  const s = S.sinav, a = s.a;
  if (s.gosterildi) cevapBosalt();
  s.gosterildi = true;
  s.i = i;
  const q = a.sorular[i];
  const ders = { steps: [{ meta: q.ders_dil ? { dil: q.ders_dil } : {}, stdin: q.ders_stdin || "" }] };
  const dil = lessonLanguage(a.track, ders, q), stdin = lessonInput(q, ders, dil);
  const okuma = a.track.okuma_dili;
  $("#soruBaslik").textContent = `Soru ${i + 1} / ${a.sorular.length}`;
  paintSerit();
  let body = `<div class="step-kind"><span class="tag ${q.kind}">${KIND_LABEL[q.kind].toLocaleUpperCase("tr")}</span><span class="label" id="isaretEtiket">${a.isaretli.includes(i) ? "⚑ işaretli" : ""}</span></div>`;
  if (q.kind === "tahmin") {
    const td = TAHMIN_DIL[okuma || dil] || {};
    body += `<h2 class="step-title">${esc(q.title || td.baslik || "Bu kod ne yazdırır?")}</h2><div class="md">${render(q.body || "", { dil, runnable: false, bench: false })}</div>` +
      codeBlock(q.code, q.code_dil || okuma || dil, { runnable: false, bench: false }) +
      (stdin ? `<div class="md"><p>${td.girdi || "Girdi kutusunda şu satırlar var:"}</p></div>${codeBlock(stdin, "cikti")}` : "") +
      `<div class="guess"><span class="label">${td.etiket || "Cevabın — çıktıyı satır satır yaz (hata bekliyorsan hatanın adını yaz)"}</span>` +
      `<textarea id="cevapKutu" rows="5" spellcheck="false" placeholder="${at(td.ornek || "ör. 42")}"></textarea>` +
      `<div class="out-meta">cevap kendiliğinden kaydedilir · doğru mu, sınav bitince görürsün</div></div>`;
  } else {
    body += `<h2 class="step-title">${esc(q.title || "Görev")}</h2><div class="md">${render(q.body || "", { dil, stdin, runnable: false, bench: false })}</div>` +
      `<div class="callout not"><div class="ct">Sınav kuralı</div><p>Tezgahta ▶ Çalıştır serbest. Kontrol, ipucu ve çözüm sınav bitene kadar kapalı; kodun her değişiklikte kaydedilir.</p></div>`;
  }
  $("#soruBody").innerHTML = body;
  const gorev = q.kind === "gorev";
  $("#bench").hidden = !gorev;
  $("#kagit").hidden = gorev;
  if (gorev) {
    S.bench.ayarla(dil, a.track.ozellik || {});
    S.bench.load({ code: a.cevaplar[i] ?? q.starter ?? "", stdin, resetCode: q.starter || "", checkable: false });
  } else {
    const kutu = $("#cevapKutu");
    kutu.value = a.cevaplar[i] || "";
    kutu.addEventListener("input", () => s.yaz(i, kutu.value));
    paintKagit();
  }
  paintSinavFoot();
  $(".sheet-wrap").scrollTop = 0;
}

async function sinavClick(e) {
  const q = e.target.closest("[data-soru]");
  if (q) { soruGoster(+q.dataset.soru); return; }
  const b = e.target.closest("[data-act]");
  const s = S.sinav;
  if (!b || !s) return;
  const act = b.dataset.act;
  if (act === "onceki" && s.i > 0) soruGoster(s.i - 1);
  else if (act === "sonraki" && s.i < s.a.sorular.length - 1) soruGoster(s.i + 1);
  else if (act === "isaretle") {
    const on = !s.a.isaretli.includes(s.i);
    s.a.isaretli = on ? [...s.a.isaretli, s.i] : s.a.isaretli.filter(j => j !== s.i);
    api("/api/sinav/cevap", { no: s.a.no, soru: s.i, isaretli: on }).catch(() => {});
    $("#isaretEtiket").textContent = on ? "⚑ işaretli" : "";
    paintSerit();
    paintSinavFoot();
    if (!$("#kagit").hidden) paintKagit();
  } else if (act === "bitir") sinavBitir(false);
}

// Puanlama uzun sürebilir: öğrenci bu arada başka ekrana geçtiyse oradan çekilmez, sonuç Geçmiş'te durur
function sonucaGec(no, sira) {
  if (sira === S.sira || S.mode === "sinav-aktif") { location.hash = `#/sinav/sonuc/${no}`; return; }
  toast("Sınav puanlandı; sonucu Er Meydanı'nda, Geçmiş bölümünde");
  refreshHeader();
  if (S.mode === "sinav") route();  // kurulum ekranındaysa süren sınav satırı kalkıp Geçmiş yenilensin
}

async function sinavBitir(otomatik) {
  const s = S.sinav;
  if (!s || s.bitiyor) return;
  await cevapBosalt();
  if (S.sinav !== s || S.mode !== "sinav-aktif") return;  // kayıt beklenirken sınav ekranından çıkıldıysa bitirilmez
  const a = s.a;
  const bos = a.sorular.filter((q, j) => !cevapli(q, a.cevaplar[j])).length;
  if (!otomatik && !confirm(bos ? `${bos} soru boş. Sınavı bitirip puanlamak istiyor musun?` : "Sınavı bitirip puanlamak istiyor musun?")) return;
  s.bitiyor = true;
  sinavTemizle();
  $("#soruFoot").innerHTML = `<span class="label">puanlanıyor · görev testleri koşuyor…</span>`;
  const sira = S.sira;
  try {
    const r = await api("/api/sinav/bitir", { no: a.no });
    S.sinav = null;
    sonucaGec(r.no, sira);
  } catch (err) {
    s.bitiyor = false;
    toast(err.message);
    if (sira === S.sira) paintSinavFoot();
  }
}

function sinavSaat() {
  sinavTemizle();
  const toplam = S.sinav.a.sure_sn || 1;
  const tik = () => {
    const s = S.sinav;
    if (!s || S.mode !== "sinav-aktif") { sinavTemizle(); return; }
    const kalan = Math.round((s.bitis - Date.now()) / 1000);
    const saat = $("#saat");
    if (!saat) return;
    $("b", saat).textContent = sureYaz(kalan);
    $(".saat-serit i", saat).style.width = `${Math.max(0, Math.min(100, kalan / toplam * 100))}%`;
    saat.classList.toggle("az", kalan <= 300);
    if (kalan <= 300 && kalan > 0 && !s.uyari) { s.uyari = true; toast("Son 5 dakika"); }
    if (kalan <= 0) { sinavTemizle(); toast("Süre doldu; sınav puanlanıyor"); sinavBitir(true); }
  };
  tik();
  S.sinavSaat = setInterval(tik, 1000);
}

function soruSonucu(r, q, j) {
  let ic;
  if (q.kind === "tahmin") {
    ic = `<div class="verdict"><div class="${q.dogru ? "good" : "badc"}"><span class="label">senin cevabın</span><pre>${esc(q.cevap || "— boş —")}</pre></div>` +
      `<div class="good"><span class="label">gerçek çıktı</span><pre>${esc(q.beklenen || "")}</pre></div></div>`;
  } else if (q.durum === "bos") {
    ic = `<p class="out-meta">bu görevi boş bıraktın (başlangıç kodu değişmedi)</p>`;
  } else {
    ic = `<ul class="checks">${(q.kontroller || []).map(c => `<li class="${c.ok ? "ok" : "no"}"><span class="ic">${c.ok ? "✓" : "✗"}</span><span>${render(c.msg).replace(/^<p>|<\/p>$/g, "")}</span></li>`).join("")}</ul>` +
      (q.hata ? `<div class="errcard"><div class="raw">${esc(q.hata)}</div></div>` : "") +
      `<details class="kodun"><summary><span class="label">gönderdiğin kod</span></summary><pre class="out">${esc(q.cevap || "")}</pre></details>`;
  }
  const kz = (q.kazanim || []).filter(k => !r.sertifika || k.startsWith(r.sertifika + " "));
  return `<details class="sr ${q.dogru ? "ok" : "no"}"><summary><span class="sr-no">${pad(j + 1)}</span><span class="ic">${q.dogru ? "✓" : "✗"}</span>` +
    `<span class="tag ${q.kind}">${KIND_LABEL[q.kind]}</span><span class="sr-t"><b>${esc(q.title || "")}</b>` +
    `<small>${esc(q.lesson.toUpperCase())} · ${esc(q.lesson_title || "")}${kz.length ? " · " + esc(kz.join(", ")) : ""}</small></span>` +
    `${q.isaretli ? '<span class="label">⚑</span>' : ""}</summary><div class="sr-ic">${ic}<a class="btn small" href="#/ders/${r.yol}/${q.lesson}/${q.step}">Paftada aç →</a></div></details>`;
}

async function renderExamResult(no) {
  S.mode = "sinav-sonuc";
  view.onclick = null;
  let r;
  try { r = await guncelse(api(`/api/sinav/sonuc/${no}`)); }
  catch (e) { view.innerHTML = `<div class="page"><div class="empty-state">Bu sınav bulunamadı.<br><br><a class="btn" href="#/sinav">Er meydanına dön</a></div></div>`; return; }
  refreshHeader();
  const tahmin = r.sorular.filter(q => q.kind === "tahmin"), gorev = r.sorular.filter(q => q.kind === "gorev");
  const say = arr => arr.length ? `${arr.filter(q => q.dogru).length}<small>/ ${arr.length}</small>` : "—";
  const yanlisGorev = gorev.filter(q => !q.dogru).length;
  const tekrar = `#/sinav/${r.yol}${r.sertifika ? "/" + encodeURIComponent(r.sertifika) + (r.bolum ? "/" + encodeURIComponent(r.bolum) : "") : ""}`;
  view.innerHTML = `<div class="page meydan-sonuc">
    <span class="label">Sınav ${r.no} · ${esc(r.tarih || "")} · ${esc(TUR_ADI[r.tur] || r.tur || "")} · ${esc(HAVUZ_ADI[r.havuz] || "")}</span>
    <h1 class="page-title">${esc(r.kapsam || "")}</h1>
    <section class="karar ${r.gecti ? "kabul" : "ret"}">
      <div class="karar-muhur"><div class="muhur"><b>${r.gecti ? "KABUL" : "RET"}</b><span>%${r.yuzde}</span><small>geçme %${r.gecme}</small></div></div>
      <div class="karar-hucre"><span class="label">Doğru</span><span class="cell-val">${r.dogru}<small>/ ${r.adet}</small></span><span class="bar"><i style="width:${r.yuzde}%"></i><b style="left:${r.gecme}%"></b></span></div>
      <div class="karar-hucre"><span class="label">Tahmin</span><span class="cell-val">${say(tahmin)}</span></div>
      <div class="karar-hucre"><span class="label">Görev</span><span class="cell-val">${say(gorev)}</span></div>
      <div class="karar-hucre"><span class="label">Süre</span><span class="cell-val">${sureYaz(r.gecen_sn)}<small>/ ${sureYaz(r.sure_sn)}</small></span></div>
    </section>
    <div class="sec-head"><h2>${r.sertifika ? "Bölümler" : "Modüller"}</h2><span class="dimline"></span><span class="label">nerede güçlüsün, nereye dönmelisin</span></div>
    <div class="dokum">${(r.gruplar || []).map(g => {
      const p = g.toplam ? Math.round(g.dogru / g.toplam * 100) : 0;
      return `<div class="dk ${p >= r.gecme ? "iyi" : "zayif"}"><span class="dk-kod">${esc(String(g.anahtar))}</span><span class="dk-ad">${esc(g.baslik)}${r.sertifika && g.agirlik ? `<small>sınavdaki ağırlık %${g.agirlik}</small>` : ""}</span>` +
        `<span class="dk-bar"><i style="width:${p}%"></i><b style="left:${r.gecme}%"></b></span><span class="dk-n">${g.dogru}/${g.toplam}</span></div>`;
    }).join("")}</div>
    <div class="sec-head"><h2>Sorular</h2><span class="dimline"></span><span class="label">tıkla: cevabın, gerçek sonuç ve testler</span></div>
    <div class="sr-liste">${r.sorular.map((q, j) => soruSonucu(r, q, j)).join("")}</div>
    <div class="sonuc-eylem">${yanlisGorev ? `<button type="button" class="btn" data-act="tekrara">Yanlış ${yanlisGorev} görevi bugünkü tekrara ekle</button>` : ""}` +
      `<span class="grow"></span><a class="btn" href="#/yol/${r.yol}">Haritaya dön</a><a class="btn primary" href="${tekrar}">Yeniden meydana çık →</a></div>
  </div>`;
  view.onclick = async e => {
    const b = e.target.closest('[data-act="tekrara"]');
    if (!b) return;
    b.disabled = true;
    try {
      const x = await api("/api/sinav/tekrar", { no: r.no });
      b.textContent = `${x.eklenen} görev tekrar kutusunda`;
      toast(`${x.eklenen} görev bugünkü tekrara eklendi`);
      refreshHeader();
    } catch (err) { toast(err.message); b.disabled = false; }
  };
}

// ── SERBEST TEZGAH ────────────────────────────────────────────────────────────
const TEZGAH_DILLER = [
  ["python", "Python", { roentgen: true, dis: "Bytecode" }],
  ["regex", "Regex", { roentgen: false, dis: "Ağaç" }],
  ["bash", "Bash", { roentgen: true, dis: null }],
  ["powershell", "PowerShell", { roentgen: true, dis: null }],
  ["cmd", "CMD / Batch", { roentgen: false, dis: null }],
  ["sql", "SQL", { roentgen: false, dis: "Plan" }],
  ["kql", "KQL (Kusto)", { roentgen: false, dis: "SQL" }],
  ["spl", "SPL", { roentgen: false, dis: "SQL" }],
  ["javascript", "JS", { roentgen: false, dis: null }],
  ["sigma", "Sigma", { roentgen: false, dis: null }],
  ["yara", "YARA", { roentgen: false, dis: null }],
  ["packets", "Wireshark / tcpdump", { roentgen: false, dis: null }],
  ["elastic", "Elastic / Kibana", { roentgen: false, dis: null }],
  ["ad", "AD / LDAP", { roentgen: false, dis: "LDAP" }],
];
const TEZGAH_ORNEK = {
  ad: "# Serbest tezgah (Active Directory / LDAP · DC=pafta,DC=local).\n# Doğrudan RFC 4515 LDAP filtresi (...) veya Get-AD* komutu yazabilirsin; LDAP düğmesi etkin filtreyi gösterir.\n\nGet-ADUser -Filter \"Enabled -eq $true -and Department -eq 'SOC'\" -Properties mail, badPwdCount\n",
  packets: "tcp.dstport == 443",
  elastic: "event.dataset: auth AND user.name: alice",
  sigma: `title: Pafta Olay Denemesi\nlogsource:\n    category: process_creation\n    product: windows\ndetection:\n    selection:\n        Image|endswith: '\\whoami.exe'\n    condition: selection\nlevel: informational\n`,
  yara: `rule Pafta_Ornek {\n    meta:\n        description = "Zararsız bir eğitim işareti"\n    strings:\n        $isaret = "PAFTA_ORNEK" ascii wide\n    condition:\n        $isaret\n}\n`,
  python: `# Serbest tezgah: ne istersen dene. Kod otomatik kaydedilir.\n# ◎ Röntgen ile adım adım izle.\n\nhedefler = ["10.0.0.1", "10.0.0.2", "10.0.0.1"]\nbenzersiz = sorted(set(hedefler))\nfor i, ip in enumerate(benzersiz, 1):\n    print(i, ip)\n`,
  regex: String.raw`(?P<yil>\d{4})-(?P<ay>\d{2})-(?P<gun>\d{2})`,
  bash: `# Serbest tezgah (Git Bash). Girdi kutusu read ile okunur.\nfor dosya in rapor.txt veri.csv notlar.md; do\n  echo "\${dosya%.*} -> \${dosya##*.}"\ndone\n`,
  powershell: `# Serbest tezgah (Windows PowerShell). Girdi kutusu $Girdi dizisine gelir.\n1..5 | ForEach-Object { [pscustomobject]@{ Sayi = $_; Kare = $_ * $_ } } | Format-Table -AutoSize\n`,
  cmd: `@echo off\nsetlocal enabledelayedexpansion\nrem Gerçek cmd.exe: batch dosyasında FOR değişkeni iki yüzde işareti kullanır.\nfor /l %%N in (1,1,3) do (\n  set /a "kare=%%N*%%N"\n  echo %%N: !kare!\n)\n`,
  spl: `sourcetype=biletler durum=açık\n| stats count by oncelik\n| sort -count\n`,
  javascript: `// Serbest tezgah (Node.js). Girdi kutusu: require("fs").readFileSync(0, "utf8")\nconst sunucular = [{ ad: "web01", cpu: 72 }, { ad: "db01", cpu: 91 }, { ad: "web03", cpu: 18 }];\nconst yogun = sunucular.filter(s => s.cpu > 50).map(s => s.ad);\nconsole.log(yogun.join(", "));\n`,
  kql: `// Serbest tezgah (KQL). Sorgu SQLite'a çevrilip örnek veritabanında çalışır; SQL düğmesi karşılığını gösterir.\n// Tablolar: ekipler, personel, sunucular, biletler, olcumler\n\nbiletler\n| where durum == "açık"\n| summarize adet = count() by oncelik\n| sort by adet desc\n`,
  sql: `-- Serbest tezgah (SQLite). Örnek veritabanı her çalıştırmada sıfırdan kurulur.\n-- Tablolar: ekipler, personel, sunucular, biletler, olcumler\n\nSELECT s.ad, s.rol, COUNT(b.id) AS bilet\nFROM sunucular AS s\nLEFT JOIN biletler AS b ON b.sunucu_id = s.id\nGROUP BY s.id\nORDER BY bilet DESC, s.ad\nLIMIT 5;\n`,
};
const TEZGAH_METIN = { regex: "Kayıtlar: 2026-10-19 giriş, 2026-10-20 çıkış, 19.10.2026 eski biçim",
  sigma: '[{"id":1,"Image":"C:\\\\Windows\\\\System32\\\\whoami.exe"},{"id":2,"Image":"C:\\\\Windows\\\\notepad.exe"}]',
  yara: "Bu zararsız metinde PAFTA_ORNEK işareti var.",
  packets: '{"dil":"wireshark","kayit":"temel"}',
  elastic: JSON.stringify({
    dil: "kibana",
    mapping: { "event.dataset": { type: "keyword" }, "user.name": { type: "keyword" }, message: { type: "text", analyzer: "standard" } },
    documents: [
      { id: "a", "event.dataset": "auth", "user.name": "alice", message: "access denied" },
      { id: "b", "event.dataset": "auth", "user.name": "Alice", message: "access allowed" },
      { id: "c", "event.dataset": "web", "user.name": "alice", message: "request complete" },
      { id: "d", "event.dataset": "auth", "user.name": "alice", message: "retry denied" },
    ],
    context: {},
  }, null, 2) };

async function renderPlayground(dil) {
  S.mode = "play";
  view.onclick = null;
  if (!TEZGAH_DILLER.some(d => d[0] === dil)) dil = "python";
  const [, , ozellik] = TEZGAH_DILLER.find(d => d[0] === dil);
  const r = await guncelse(api(`/api/playground?dil=${encodeURIComponent(dil)}`));
  view.innerHTML = `<div class="playground"><section class="bench" id="bench"></section></div>`;
  S.bench = new Bench($("#bench"), {
    track: dil === "python" ? "python" : dil,
    dil,
    ozellik,
    checkable: () => false,
    saveDraft: code => api("/api/draft", { playground: code, dil }),
  });
  const secici = `<span class="dil-sec">${TEZGAH_DILLER.map(([k, ad]) =>
    `<button type="button" data-dil="${k}" class="${k === dil ? "on" : ""}">${ad}</button>`).join("")}</span>`;
  $(".bench-bar .sp", $("#bench")).insertAdjacentHTML("beforebegin", secici);
  $(".dil-sec", $("#bench")).addEventListener("click", e => {
    const b = e.target.closest("[data-dil]");
    if (b) location.hash = `#/tezgah/${b.dataset.dil}`;
  });
  S.bench.load({ code: r.code || TEZGAH_ORNEK[dil], stdin: TEZGAH_METIN[dil] || "", resetCode: TEZGAH_ORNEK[dil] });
}

// ── ayarlar ──────────────────────────────────────────────────────────────────
function openSettings() {
  const d = $("#dialog");
  const st = S.state || {};
  d.innerHTML = `<div class="dlg-head">Ayarlar</div><div class="dlg-body">
    <div class="dlg-row"><span>Tema</span><span><button class="btn small" data-theme-set="mavi">Mavi kopya</button> <button class="btn small" data-theme-set="ozalit">Ozalit</button></span></div>
    <div class="dlg-row"><span>Kısayollar</span><span class="mono">Ctrl+↵ çalıştır · Ctrl+⇧+↵ kontrol · Ctrl+/ yorum · Tab / ⇧Tab girinti · Röntgende ← →</span></div>
    <div class="dlg-row"><span>İlerleme dosyası</span><span class="mono">${esc(st.data_path || "")}</span></div>
    <div class="dlg-row"><span>İlerlemeyi sıfırla</span><button class="btn small" data-reset>Sıfırla…</button></div>
  </div><div class="dlg-foot"><button class="btn primary" data-close>Kapat</button></div>`;
  d.onclick = async e => {
    if (e.target.closest("[data-close]") || e.target === d) d.close();
    const t = e.target.closest("[data-theme-set]");
    if (t) { setTheme(t.dataset.themeSet); api("/api/settings", { key: "theme", value: t.dataset.themeSet }); }
    if (e.target.closest("[data-reset]")) {
      const w = prompt("Tüm ilerleme, taslaklar ve tekrar kutuları silinecek. Onaylamak için SIFIRLA yaz:");
      if (w === "SIFIRLA") { await api("/api/reset", { confirm: "SIFIRLA" }); d.close(); toast("İlerleme sıfırlandı"); route(); }
    }
  };
  d.showModal();
}

// ── yönlendirme ───────────────────────────────────────────────────────────────
// ── Rota: Pafta + TryHackMe + HackTheBox ─────────────────────────────────────
const ROTA_PLATFORM = { pafta: "Pafta", thm: "TryHackMe", htb: "HackTheBox Academy" };

function rotaYuzde(a) {
  // Bir aşamanın üç sütununun ilerlemesi (0–100); boş sütun null
  const ort = xs => (xs.length ? xs.reduce((s, x) => s + x, 0) / xs.length : null);
  const pb = a.pafta.reduce((s, t) => s + t.bitti, 0), pt = a.pafta.reduce((s, t) => s + t.toplam, 0);
  return { pafta: pt ? pb / pt * 100 : null, thm: ort(a.thm.map(y => y.yuzde)), htb: ort(a.htb.map(y => y.yuzde)) };
}

function rotaGenel(r) {
  // Seçmeli aşama ve yan yol genel ilerlemeye katılmaz
  const ana = r.asamalar.filter(a => a.id !== "secmeli");
  const pafta = ana.flatMap(a => a.pafta), thm = ana.flatMap(a => a.thm), htb = ana.flatMap(a => a.htb);
  const ort = xs => (xs.length ? xs.reduce((s, y) => s + y.yuzde, 0) / xs.length : 0);
  const pt = pafta.reduce((s, t) => s + t.toplam, 0);
  return { pafta: pt ? pafta.reduce((s, t) => s + t.bitti, 0) / pt * 100 : 0, thm: ort(thm), htb: ort(htb) };
}

const yuzdeYaz = x => (x == null ? "—" : (Math.round(x * 10) / 10).toLocaleString("tr-TR"));

function rotaSatirDis(platform, y) {
  const sert = y.sertifika_adi
    ? `<label class="rota-sert ${y.sertifika ? "on" : ""}" title="${at(y.sertifika_adi)} sınavını geçtiysen işaretle">` +
      `<input type="checkbox" data-sert="${platform}:${y.id}" ${y.sertifika ? "checked" : ""}> ${esc(y.sertifika_adi)}</label>`
    : "";
  return `<div class="rota-satir ${y.yuzde >= 100 ? "bitti" : ""}" data-satir="${platform}:${y.id}">` +
    `<span class="rota-ad">${esc(y.ad)}</span>${sert}` +
    `<span class="rota-girdi"><input type="number" min="0" max="100" step="0.1" value="${y.yuzde}" data-yuzde="${platform}:${y.id}" aria-label="${at(y.ad)} ilerleme yüzdesi"><small>%</small></span>` +
    `<span class="rota-bar"><i style="width:${y.yuzde}%"></i></span></div>`;
}

function rotaSatirPafta(t) {
  const y = t.toplam ? t.bitti / t.toplam * 100 : 0;
  return `<a class="rota-satir pafta ${t.toplam && t.bitti === t.toplam ? "bitti" : ""}" href="#/yol/${t.id}">` +
    `<span class="rota-ad">${esc(t.ad)}</span><span class="rota-sayi">${t.bitti}<small>/${t.toplam}</small></span>` +
    `<span class="rota-bar"><i style="width:${y}%"></i></span></a>`;
}

function rotaAsama(a, no, simdi, uyelikAktif) {
  const y = rotaYuzde(a);
  const thmOn = !uyelikAktif || uyelikAktif.thm !== false;
  const htbOn = !uyelikAktif || uyelikAktif.htb !== false;
  const tarihEtiket = a.baslangic_tr
    ? `<span class="rota-faz-tarih">${esc(a.baslangic_tr)}${a.bitis_tr && a.bitis_tr !== "✓" ? ` – ${esc(a.bitis_tr)} · ${a.gun_sayisi} gün` : " ✓"}</span>`
    : "";
  const sutun = (p, ic, aktif = true) => `<div class="rota-sutun ${p} ${aktif ? "" : "pasif"}"><div class="rota-sb"><span class="label">${ROTA_PLATFORM[p]}</span>` +
    `<b data-asama-yuzde="${a.id}:${p}">${aktif ? `${yuzdeYaz(y[p])}${y[p] == null ? "" : "<small>%</small>"}` : `<small>Üyelik dışı</small>`}</b></div>` +
    `${aktif ? (ic || `<p class="rota-bos">Bu aşamada yok</p>`) : `<p class="rota-bos">Üyelik seçilmedi (Pafta ile ikame edilir)</p>`}</div>`;
  return `<section class="rota-asama ${simdi ? "simdi" : ""}" data-asama="${a.id}">
    <header class="rota-ah"><span class="rota-no">${no}</span><div><h2>${esc(a.ad)}</h2><p>${esc(a.not)}</p></div>${tarihEtiket}${simdi ? `<span class="rota-simdi">ŞİMDİ</span>` : ""}</header>
    <div class="rota-izgara">
      ${sutun("pafta", a.pafta.map(rotaSatirPafta).join(""), true)}
      ${sutun("thm", a.thm.map(x => rotaSatirDis("thm", x)).join(""), thmOn)}
      ${sutun("htb", a.htb.map(x => rotaSatirDis("htb", x)).join(""), htbOn)}
    </div></section>`;
}

function rotaGenelBoya() {
  const g = rotaGenel(S.rota);
  for (const p of ["pafta", "thm", "htb"]) {
    const k = $(`[data-genel="${p}"]`);
    if (!k) continue;
    k.querySelector(".rota-buyuk").innerHTML = `${yuzdeYaz(g[p])}<small>%</small>`;
    k.querySelector(".rota-bar i").style.width = `${g[p]}%`;
  }
  for (const a of [...S.rota.asamalar, S.rota.yan]) {
    const y = rotaYuzde(a);
    for (const p of ["pafta", "thm", "htb"]) {
      const b = $(`[data-asama-yuzde="${a.id}:${p}"]`);
      if (b) b.innerHTML = `${yuzdeYaz(y[p])}${y[p] == null ? "" : "<small>%</small>"}`;
    }
  }
}

function rotaTakvimTablo(r, gorunumModu = "haftalik", seciliFaz = "all") {
  const tk = r.takvim || {};
  const ua = r.uyelik_aktif || { thm: true, htb: true };
  if (gorunumModu === "haftalik") {
    const haftalar = tk.haftalik_plan || [];
    if (!haftalar.length) return `<p class="rota-bos">Tüm dersler tamamlandı!</p>`;
    return `<div class="rota-takvim-tablo-sarici"><table class="rota-takvim-tablo">
      <thead><tr>
        <th>Hafta &amp; Tarih Aralığı</th>
        <th>Faz</th>
        <th>Pafta Ders Hedefi</th>
        ${ua.thm ? `<th>TryHackMe Hedefi</th>` : ""}
        ${ua.htb ? `<th>HTB Academy Hedefi</th>` : ""}
      </tr></thead>
      <tbody>
        ${haftalar.map(h => `<tr>
          <td class="tk-tarih"><b>${h.hafta_no}. Hafta</b><br><small>${esc(h.aralik_tr)}</small></td>
          <td class="tk-faz"><span class="tk-faz-rozet">${esc(h.faz_ad)}</span></td>
          <td>${h.pafta.map(p => `<a class="tk-ders-bag" href="#/yol/${esc(p.id)}">${esc(p.ad)}</a> <small>(${esc(p.aralik)})</small>`).join("<br>") || "—"}</td>
          ${ua.thm ? `<td>${h.thm.map(esc).join("<br>") || "—"}</td>` : ""}
          ${ua.htb ? `<td>${h.htb.map(esc).join("<br>") || "—"}</td>` : ""}
        </tr>`).join("")}
      </tbody>
    </table></div>`;
  }
  const gunler = (tk.gunluk_plan || []).filter(g => seciliFaz === "all" || g.faz_id === seciliFaz);
  if (!gunler.length) return `<p class="rota-bos">Bu filtrede gösterilecek gün yok.</p>`;
  return `<div class="rota-takvim-tablo-sarici"><table class="rota-takvim-tablo">
    <thead><tr>
      <th>Gün &amp; Tarih</th>
      <th>Faz</th>
      <th>Pafta Günlük Dersler</th>
      ${ua.thm ? `<th>TryHackMe Günlük Hedef</th>` : ""}
      ${ua.htb ? `<th>HTB Academy Günlük Hedef</th>` : ""}
    </tr></thead>
    <tbody>
      ${gunler.map(g => `<tr>
        <td class="tk-tarih"><b>${g.gun_no}. Gün</b> · ${esc(g.tarih_tr)}</td>
        <td class="tk-faz"><span class="tk-faz-rozet">Faz ${g.faz_no}</span></td>
        <td>${g.pafta.map(p => `<a class="tk-ders-bag" href="#/yol/${esc(p.id)}">${esc(p.ad)}</a> <small>(${esc(p.aralik)})</small>`).join(" &nbsp;+&nbsp; ") || "Tekrar &amp; Lab"}</td>
        ${ua.thm ? `<td>${g.thm ? `${esc(g.thm.ad)} <small>(%${yuzdeYaz(g.thm.eski)} → %${yuzdeYaz(g.thm.yeni)})</small>` : "—"}</td>` : ""}
        ${ua.htb ? `<td>${g.htb ? `${esc(g.htb.ad)} <small>(%${yuzdeYaz(g.htb.eski)} → %${yuzdeYaz(g.htb.yeni)})</small>` : "—"}</td>` : ""}
      </tr>`).join("")}
    </tbody>
  </table></div>`;
}

function rotaTakvimKutu(r, aktifAsama) {
  const tk = r.takvim || {};
  const hedefler = r.hedefler || [];
  const tempolar = r.tempolar || [];
  const uyelikler = r.uyelikler || [];
  const fazlar = tk.faz_ozetleri || [];
  const ilkGun = (tk.gunluk_plan || [])[0];
  const bugun = ilkGun
    ? [
        ilkGun.pafta.length ? `<b>Pafta:</b> ${ilkGun.pafta.map(p => `<a href="#/yol/${esc(p.id)}">${esc(p.ad)} (${esc(p.aralik)})</a>`).join(" + ")}` : null,
        ilkGun.thm ? `<b>THM:</b> ${esc(ilkGun.thm.ad)} (%${yuzdeYaz(ilkGun.thm.eski)} → %${yuzdeYaz(ilkGun.thm.yeni)})` : null,
        ilkGun.htb ? `<b>HTB:</b> ${esc(ilkGun.htb.ad)} (%${yuzdeYaz(ilkGun.htb.eski)} → %${yuzdeYaz(ilkGun.htb.yeni)})` : null,
      ].filter(Boolean).join(" &nbsp;·&nbsp; ")
    : "Tüm ana aşamalar tamamlandı!";
  const mod = S.rotaTakvimMod || "gunluk";
  const fazFiltre = S.rotaTakvimFaz || (fazlar[0] ? fazlar[0].id : "all");
  return `<section class="rota-hedef-panel">
    <div class="rota-seciciler">
      <label class="rota-alan">
        <span class="label">1. Major Hedef &amp; Kariyer Yolu</span>
        <select data-rota-hedef>
          ${hedefler.map(h => `<option value="${esc(h.id)}" ${h.id === r.hedef ? "selected" : ""}>${esc(h.ad)}</option>`).join("")}
        </select>
      </label>
      <label class="rota-alan">
        <span class="label">2. Mevcut Platform Üyeliklerin</span>
        <select data-rota-uyelik>
          ${uyelikler.map(u => `<option value="${esc(u.id)}" ${u.id === r.uyelik ? "selected" : ""}>${esc(u.ad)}</option>`).join("")}
        </select>
      </label>
      <label class="rota-alan">
        <span class="label">3. Günlük Çalışma Temposu</span>
        <select data-rota-tempo>
          ${tempolar.map(t => `<option value="${esc(t.id)}" ${t.id === r.tempo ? "selected" : ""}>${esc(t.ad)}</option>`).join("")}
        </select>
      </label>
      <label class="rota-alan">
        <span class="label">4. Takvim Başlangıç Tarihi</span>
        <input type="date" data-rota-baslangic value="${esc(r.baslangic || "")}">
      </label>
    </div>
    <div class="rota-takvim-ozet">
      <div class="rota-tk-satir">
        <span class="label">${esc(tk.etiket || "")}</span>
        <span class="rota-tk-sure">${tk.tahmini_gun ? `Başlangıç: <b>${esc(tk.baslangic_tr)}</b> → Bitiş: <b>${esc(tk.bitis_tr)}</b> · Toplam <b>${tk.tahmini_gun} gün</b> (${tk.tahmini_hafta} hafta / ~${tk.tahmini_ay} ay)` : `<b>Hedef Tamamlandı ✓</b>`}</span>
      </div>
      <p class="rota-tk-aciklama">${esc(tk.ozet || "")}</p>
      ${fazlar.length ? `<div class="rota-faz-serit">${fazlar.map(f => `<div class="rota-faz-kutu"><b>Faz ${f.faz_no}</b><span>${esc(f.baslangic_tr)} – ${esc(f.bitis_tr)}</span><small>${f.gun_sayisi} gün</small></div>`).join("")}</div>` : ""}
      <div class="rota-tk-blok bugun"><b>Bugünün Kombine Görevi (${ilkGun ? esc(ilkGun.tarih_tr) : "Tamam"}):</b> ${bugun}</div>
      <div class="rota-takvim-gorunum">
        <div class="rota-tk-bar">
          <div class="rota-tk-sekmeler">
            <button type="button" class="tk-sekme ${mod === "gunluk" ? "on" : ""}" data-tk-mod="gunluk">📅 Tarih Tarih (Gün Gün) Program</button>
            <button type="button" class="tk-sekme ${mod === "haftalik" ? "on" : ""}" data-tk-mod="haftalik">🗓️ Hafta Hafta Kombine Takvim</button>
          </div>
          ${mod === "gunluk" ? `<select data-tk-faz class="tk-faz-sec">
            <option value="all" ${fazFiltre === "all" ? "selected" : ""}>Tüm Fazları Göster (${tk.tahmini_gun || 0} Gün)</option>
            ${fazlar.map(f => `<option value="${esc(f.id)}" ${fazFiltre === f.id ? "selected" : ""}>${esc(f.ad)} (${esc(f.baslangic_tr)} – ${esc(f.bitis_tr)})</option>`).join("")}
          </select>` : ""}
        </div>
        <div id="rota-takvim-icerik">${rotaTakvimTablo(r, mod, fazFiltre)}</div>
      </div>
    </div>
  </section>`;
}

async function renderRota() {
  S.mode = "rota";
  view.innerHTML = `<div class="page"><p class="label">Yükleniyor…</p></div>`;
  try { S.rota = await guncelse(api("/api/rota")); }
  catch (e) { view.innerHTML = `<div class="page"><div class="empty-state">Rota yüklenemedi: ${esc(e.message)}</div></div>`; return; }
  const r = S.rota;
  const ua = r.uyelik_aktif || { thm: true, htb: true };
  const tam = a => {
    const y = rotaYuzde(a);
    return (y.pafta == null || y.pafta >= 100) && (!ua.thm || y.thm == null || y.thm >= 100) && (!ua.htb || y.htb == null || y.htb >= 100);
  };
  const simdi = r.asamalar.findIndex(a => !tam(a));
  const aktifAsama = simdi >= 0 ? r.asamalar[simdi] : r.asamalar[r.asamalar.length - 1];
  if (!S.rotaTakvimFaz && aktifAsama) S.rotaTakvimFaz = aktifAsama.id;
  const g = rotaGenel(r);
  const kadran = p => `<div class="rota-kadran ${p}" data-genel="${p}"><span class="label">${ROTA_PLATFORM[p]}</span>` +
    `<span class="rota-buyuk">${yuzdeYaz(g[p])}<small>%</small></span><span class="rota-bar"><i style="width:${g[p]}%"></i></span></div>`;
  view.innerHTML = `<div class="page rota">
    <span class="label">${esc((r.takvim && r.takvim.etiket) || "Purple team · üç cephe birlikte")}</span>
    <h1 class="page-title">Rota &amp; Tarih Tarih Çalışma Takvimi</h1>
    <p class="page-sub">Hedeflediğin Major alanları, mevcut platform üyeliklerini (TryHackMe / HTB Academy) ve günlük çalışma temponu seç; Pafta derslerini dış platform modülleriyle kombine ederek gün gün (tarih tarih) çalışma takvimini çıkarsın.</p>
    ${r.hedefler ? rotaTakvimKutu(r, aktifAsama) : ""}
    <div class="rota-kadranlar">${kadran("pafta")}${kadran("thm")}${kadran("htb")}</div>
    ${r.asamalar.map((a, i) => rotaAsama(a, pad(i + 1), i === simdi, ua)).join("")}
    ${(r.yan && (r.yan.pafta.length || r.yan.thm.length || r.yan.htb.length)) ? rotaAsama(r.yan, "∥", false, ua) : ""}
  </div>`;

  // Her satırın kendi bekleme süresi var: bir satıra yazarken ötekinin kaydı iptal olmasın
  const bekleyen = new Map();
  const sira = S.sira;
  const gonder = async (platform, id, govde, satir) => {
    try {
      const k = await api("/api/rota", { platform, id, ...govde });
      const a = [...r.asamalar, r.yan].find(a => a[platform].some(y => y.id === id));
      Object.assign(a[platform].find(y => y.id === id), k);
      if (sira !== S.sira) return;  // kayıt sunucuda; kapanan ekran boyanmaz
      if (satir) satir.classList.toggle("bitti", k.yuzde >= 100);
      rotaGenelBoya();
    } catch (err) { toast(err.message); }
  };
  const kaydet = (platform, id, govde, satir, hemen = false) => {
    const anahtar = `${platform}:${id}:${Object.keys(govde)[0]}`;
    clearTimeout(bekleyen.get(anahtar)?.t);
    const is = { calis() { bekleyen.delete(anahtar); gonder(platform, id, govde, satir); } };
    is.t = setTimeout(is.calis, hemen ? 0 : 450);
    bekleyen.set(anahtar, is);
  };
  // Ekrandan çıkarken ya da sayfa kapanırken beklemedeki satırları hemen gönder
  S.rotaBosalt = () => { for (const is of [...bekleyen.values()]) { clearTimeout(is.t); is.calis(); } };

  view.oninput = e => {
    const yz = e.target.dataset.yuzde;
    if (!yz) return;
    const [platform, id] = yz.split(":");
    const v = Math.max(0, Math.min(100, parseFloat(e.target.value.replace(",", ".")) || 0));
    const satir = e.target.closest(".rota-satir");
    satir.querySelector(".rota-bar i").style.width = `${v}%`;
    kaydet(platform, id, { yuzde: v }, satir);
  };
  view.onchange = async e => {
    if (e.target.dataset.tkFaz !== undefined) {
      S.rotaTakvimFaz = e.target.value;
      const kutu = $("#rota-takvim-icerik");
      if (kutu) kutu.innerHTML = rotaTakvimTablo(S.rota, S.rotaTakvimMod || "gunluk", S.rotaTakvimFaz);
      return;
    }
    if (e.target.dataset.rotaHedef !== undefined || e.target.dataset.rotaTempo !== undefined ||
        e.target.dataset.rotaUyelik !== undefined || e.target.dataset.rotaBaslangic !== undefined) {
      const hedef = $("[data-rota-hedef]")?.value;
      const uyelik = $("[data-rota-uyelik]")?.value;
      const tempo = $("[data-rota-tempo]")?.value;
      const baslangic = $("[data-rota-baslangic]")?.value;
      if (e.target.dataset.rotaHedef !== undefined) S.rotaTakvimFaz = null;
      try {
        await api("/api/rota", { hedef, uyelik, tempo, baslangic });
        renderRota();
      } catch (err) { toast(err.message); }
      return;
    }
    const s = e.target.dataset.sert;
    if (!s) return;
    const [platform, id] = s.split(":");
    e.target.closest(".rota-sert").classList.toggle("on", e.target.checked);
    kaydet(platform, id, { sertifika: e.target.checked }, null, true);
  };
  view.onclick = e => {
    const btn = e.target.closest("[data-tk-mod]");
    if (!btn) return;
    S.rotaTakvimMod = btn.dataset.tkMod;
    renderRota();
  };
}

function route() {
  S.sira++;
  S.rotaBosalt?.();
  S.rotaBosalt = null;
  const p = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean).map(decodeURIComponent);
  const key = !p[0] || p[0] === "ders" || p[0] === "yol" ? "harita" : p[0];
  $$(".nav a").forEach(a => a.classList.toggle("on", a.dataset.nav === key));
  if (S.mode === "sinav-aktif" && S.sinav) cevapBosalt();   // sınavdan çıkarken açık cevabı kaybetme
  sinavTemizle();
  if (p[0] === "sinav" && p[1] === "aktif") return renderExam();
  if (p[0] === "sinav" && p[1] === "sonuc" && p[2]) return renderExamResult(+p[2]);
  if (p[0] === "sinav") return renderExamSetup(p[1], p[2], p[3]);
  if (p[0] === "ders" && p[2]) return renderLesson(p[1], p[2], +(p[3] || 0));
  if (p[0] === "tekrar" && p[3] !== undefined) return renderReviewSolve(p[1], p[2], +p[3]);
  if (p[0] === "tekrar") return renderReview();
  if (p[0] === "tezgah") return renderPlayground(p[1]);
  if (p[0] === "rota") return renderRota();
  if (p[0] === "yol" && p[1]) return renderMap(p[1]);
  return renderMap();
}

// Sayfa kapanırken ya da gizlenirken beklemedeki kayıtları hemen gönder
function bekleyenleriGonder() {
  kapaniyor = true;
  try {
    if (S.mode === "sinav-aktif" && S.sinav) cevapBosalt().catch(() => {});
    else S.bench?.draft.bosalt();
    S.rotaBosalt?.();
  } finally { kapaniyor = false; }
}

async function boot() {
  const st = await refreshHeader();
  if (st) {
    setTheme(st.settings?.theme || "mavi");
  }
  $("#themeBtn").addEventListener("click", () => {
    const t = document.documentElement.dataset.theme === "ozalit" ? "mavi" : "ozalit";
    setTheme(t);
    api("/api/settings", { key: "theme", value: t }).catch(() => {});
  });
  $("#settingsBtn").addEventListener("click", openSettings);
  // Editör odakta değilken de Ctrl+↵ çalıştırsın (editör kendi kısayolunu zaten işliyor)
  document.addEventListener("keydown", e => {
    if (e.defaultPrevented || !(e.ctrlKey || e.metaKey) || e.key !== "Enter") return;
    const b = S.bench;
    if (!b || !b.ed.ta.isConnected) return;
    if (e.target.closest?.("input, textarea, select") && !e.target.closest("#bench")) return;
    e.preventDefault();
    if (e.shiftKey) { if (b.ctx.checkable()) b.check(); }
    else b.run();
  });
  window.addEventListener("hashchange", route);
  window.addEventListener("pagehide", bekleyenleriGonder);
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "hidden") bekleyenleriGonder(); });
  setInterval(() => api("/api/ping", {}).catch(() => {}), 10000);
  route();
}

boot();
