# -*- coding: utf-8 -*-
"""Canlı durum listesi: docs/DURUM.md'yi Pafta_Takip.xlsx + docs/durum.json + git'ten üretir.

Excel denetçinin listesidir (madde, atanan, Bitti kararı). Ajanlar o arada kendi durumlarını
docs/durum.json'a yazar. Commit edilmemiş dosyalar ve son commit'ler git'ten okunur.
.git/hooks/post-commit her commit'ten sonra bu betiği çalıştırır; elle de çalışır:

    python -X utf8 tools/durum_listesi.py
"""
import datetime
import json
import os
import subprocess

import openpyxl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCEL = os.path.join(ROOT, "Pafta_Takip.xlsx")
DURUM_JSON = os.path.join(ROOT, "docs", "durum.json")
CIKTI = os.path.join(ROOT, "docs", "DURUM.md")

ETIKET = {
    "bitti": "✅ bitti (denetçi)",
    "denetime-hazir": "🟦 denetime hazır",
    "calisiliyor": "🟨 çalışılıyor",
    "taslak": "🟧 taslak (commit edilmemiş)",
    "kismen": "🟪 kısmen",
    "codex-onerildi": "🩵 Codex önerildi",
    "codex-opus": "🟥 Codex / Opus 4.8",
    "claude-alabilir": "🔵 Claude alabilir",
    "atlandi": "⬜ atlandı",
    "": "· dokunulmadı",
}

# Excel'deki 104 maddeyi değiştirmeden iş-rolü eklerini paftada göster.
EK_MADDELER = [
    {"no": 105, "ad": "İş Rolü: Oltalama e-postası analizi (PU14)", "atanan": "Kimi",
     "excel": "Pafta eki", "durum": "denetime-hazir", "kim": "Kimi", "commit": "0277d48",
     "not": "SPF/DKIM/DMARC, Received, URL ve ek kanıtı; 9/9 test temiz"},
    {"no": 106, "ad": "İş Rolü: Windows adli izleri (PU15)", "atanan": "Kimi",
     "excel": "Pafta eki", "durum": "denetime-hazir", "kim": "Kimi", "commit": "0277d48",
     "not": "Registry, Prefetch, MFT, LNK ve UTC çizelgesi; 9/9 test temiz"},
    {"no": 107, "ad": "İş Rolü: Linux yetki yükseltme temelleri (PU16)", "atanan": "Kimi",
     "excel": "Pafta eki", "durum": "denetime-hazir", "kim": "Kimi", "commit": "0277d48",
     "not": "SUID/SGID, sudo, cron/systemd, PATH ve capability; 8/8 test temiz"},
    {"no": 108, "ad": "İş Rolü: Parola özeti biçimleri (PU17)", "atanan": "Kimi",
     "excel": "Pafta eki", "durum": "denetime-hazir", "kim": "Kimi", "commit": "0277d48",
     "not": "NTLM, bcrypt, sha512crypt, yescrypt ve araç modları; 8/8 test temiz"},
]


def git(*args):
    p = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.stdout


def excel_maddeleri():
    wb = openpyxl.load_workbook(EXCEL, read_only=True)
    satirlar = list(wb["Yapılacaklar"].iter_rows(values_only=True))
    ozet = satirlar[0][0] if satirlar else ""
    maddeler = []
    for r in satirlar[2:]:
        if r and r[1]:
            maddeler.append({"no": r[0], "ad": str(r[1]).strip(), "atanan": r[2] or "", "excel": r[3] or ""})
    return ozet, maddeler


def durumlar():
    if not os.path.isfile(DURUM_JSON):
        return {}
    with open(DURUM_JSON, encoding="utf-8") as f:
        return json.load(f).get("maddeler", {})


def acik_dosyalar():
    """git status → [(durum, yol, değişme zamanı)]; docs/DURUM.md'nin kendisi hariç."""
    sonuc = []
    for satir in git("-c", "core.quotepath=off", "status", "--porcelain", "--untracked-files=all").splitlines():
        kod, yol = satir[:2].strip(), satir[3:].strip().strip('"')
        if yol.replace("\\", "/") == "docs/DURUM.md":
            continue
        tam = os.path.join(ROOT, yol)
        zaman = datetime.datetime.fromtimestamp(os.path.getmtime(tam)).strftime("%m-%d %H:%M") if os.path.exists(tam) else "silinmiş"
        sonuc.append((kod, yol, zaman))
    return sonuc


def son_commitler(n=12):
    out = git("log", f"-{n}", "--date=format:%m-%d %H:%M",
              "--format=%h\t%ad\t%s\t%(trailers:key=Ajan,valueonly,separator=)")
    return [s.split("\t") for s in out.splitlines() if s.count("\t") >= 3]


def hucre(s):
    return str(s or "").replace("|", "\\|").replace("\n", " ")


def uret():
    ozet, maddeler = excel_maddeleri()
    dj = durumlar()
    acik = acik_dosyalar()
    sahip = {}
    for ad, d in dj.items():
        for yol in d.get("dosyalar", []):
            sahip[yol.replace("\\", "/")] = d.get("kim", "")

    for m in maddeler:
        d = dj.get(m["ad"], {})
        if m["excel"].lower().startswith("bitti"):
            m["durum"] = "bitti"
        else:
            m["durum"] = d.get("durum", "")
        m["kim"] = d.get("kim", "")
        m["commit"] = d.get("commit", "")
        m["not"] = d.get("not", "")

    maddeler.extend(dict(m) for m in EK_MADDELER)

    sayac = {}
    for m in maddeler:
        sayac[m["durum"]] = sayac.get(m["durum"], 0) + 1
    siradaki = next((m for m in maddeler if m["durum"] == ""), None)
    bas = git("rev-parse", "--short", "HEAD").strip()
    simdi = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    y = []
    y.append("# Pafta canlı durum listesi")
    y.append("")
    y.append(f"> Otomatik üretildi: **{simdi}** · son commit `{bas}` · `tools/durum_listesi.py`. Elle düzenleme: üzerine yazılır.")
    y.append("> Durumunu yazmak için `docs/durum.json`'ı güncelle ve commit et; bu dosya her commit'te kendiliğinden yenilenir.")
    y.append("")
    y.append(f"**Excel:** {ozet}")
    y.append("")
    y.append("**Bu listeye göre:** " + " · ".join(f"{ETIKET[k]}: {sayac[k]}" for k in ETIKET if sayac.get(k)))
    y.append("")
    if siradaki:
        y.append(f"**Sıradaki dokunulmamış madde:** {siradaki['no']}. {siradaki['ad']} (Excel'de: {siradaki['atanan']})")
        y.append("")

    calisan = [m for m in maddeler if m["durum"] in ("calisiliyor", "taslak", "codex-onerildi")]
    y.append("## Şu an açık işler")
    y.append("")
    if calisan:
        for m in calisan:
            y.append(f"- **{m['no']}. {m['ad']}** · {ETIKET[m['durum']]} · {m['kim']}" + (f" · {m['not']}" if m["not"] else ""))
    else:
        y.append("- yok")
    y.append("")

    y.append("## Commit edilmemiş dosyalar")
    y.append("")
    if acik:
        y.append("| Dosya | Git | Son değişiklik | Kimin (durum.json'a göre) |")
        y.append("|---|---|---|---|")
        for kod, yol, zaman in acik:
            y.append(f"| `{hucre(yol)}` | {kod} | {zaman} | {hucre(sahip.get(yol.replace(chr(92), '/'), '?'))} |")
    else:
        y.append("Yok: çalışma ağacı temiz.")
    y.append("")

    y.append("## Bütün maddeler")
    y.append("")
    y.append("| No | Madde | Excel'de atanan | Durum | Kim | Commit | Not |")
    y.append("|---|---|---|---|---|---|---|")
    for m in maddeler:
        y.append(f"| {m['no']} | {hucre(m['ad'])} | {hucre(m['atanan'])} | {ETIKET[m['durum']]} | {hucre(m['kim'])} | "
                 f"{hucre(m['commit'])} | {hucre(m['not'])} |")
    y.append("")

    y.append("## Son commit'ler")
    y.append("")
    y.append("| Commit | Zaman | Ajan | Konu |")
    y.append("|---|---|---|---|")
    for h, zaman, konu, ajan in son_commitler():
        y.append(f"| `{h}` | {zaman} | {hucre(ajan) or '—'} | {hucre(konu)} |")
    y.append("")

    with open(CIKTI, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(y))
    veri = {"zaman": simdi, "bas": bas, "ozet": ozet, "siradaki": siradaki["no"] if siradaki else None,
            "maddeler": maddeler, "acik": [{"kod": k, "yol": p, "zaman": z, "kim": sahip.get(p.replace(chr(92), "/"), "")}
                                           for k, p, z in acik],
            "commitler": [{"h": h, "zaman": z, "konu": k, "ajan": a} for h, z, k, a in son_commitler(15)]}
    with open(CIKTI_HTML, "w", encoding="utf-8", newline="\n") as f:
        f.write(PANEL.replace("/*VERI*/null", json.dumps(veri, ensure_ascii=False).replace("</", "<\\/")))
    return CIKTI


CIKTI_HTML = os.path.join(ROOT, "docs", "DURUM.html")

# Panel: bir harita paftası. Her madde bir parsel; yollar paftanın bölgeleri, durum parselin mürekkebi.
PANEL = r"""<!DOCTYPE html>
<html lang="tr"><head><meta charset="utf-8">
<title>Pafta · canlı durum</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root{--kagit:#efe8d6;--kagit2:#e6dcc3;--murekkep:#1e2a33;--soluk:#6d6a5e;--cizgi:#b9ad8e;
 --codex:#13808a;--bitti:#2f5d3a;--hazir:#4f8a52;--calis:#c98a12;--taslak:#c4561d;--kismen:#6b4c8a;--isaret:#c0261c;--kirmizi:#b3261e;--mavi:#1f5fbf}
*{box-sizing:border-box}
body{margin:0;background:var(--kagit);color:var(--murekkep);font-family:Bahnschrift,"Segoe UI",system-ui,sans-serif;
 background-image:repeating-radial-gradient(circle at 78% 12%,transparent 0 38px,rgba(120,100,60,.09) 38px 39px),
 linear-gradient(rgba(120,100,60,.07) 1px,transparent 1px),linear-gradient(90deg,rgba(120,100,60,.07) 1px,transparent 1px);
 background-size:auto,40px 40px,40px 40px}
.sayfa{max-width:1500px;margin:0 auto;padding:22px 26px 60px;display:grid;grid-template-columns:1fr 340px;gap:26px}
header{grid-column:1/-1;display:grid;grid-template-columns:1fr auto;border:3px double var(--murekkep);padding:14px 18px;background:rgba(239,232,214,.85)}
h1{margin:0;font-family:Georgia,"Times New Roman",serif;font-weight:normal;letter-spacing:.32em;font-size:30px;text-transform:uppercase}
h1 small{display:block;letter-spacing:.18em;font-size:12px;color:var(--soluk);margin-top:4px;font-family:Bahnschrift,sans-serif}
.kunye{text-align:right;font-size:12px;line-height:1.7;color:var(--soluk)}
.kunye b{color:var(--murekkep)}
.olcek{grid-column:1/-1;margin-top:12px;display:flex;height:14px;border:1.5px solid var(--murekkep)}
.olcek span{height:100%}
.olcek-yazi{grid-column:1/-1;display:flex;justify-content:space-between;font-size:11px;color:var(--soluk);margin-top:3px}
.lejant{display:flex;flex-wrap:wrap;gap:6px 14px;margin:0 0 14px;font-size:12.5px}
.lejant button{all:unset;cursor:pointer;display:flex;align-items:center;gap:6px;padding:3px 8px;border:1px solid transparent}
.lejant button[aria-pressed=true]{border-color:var(--murekkep);background:rgba(30,42,51,.06)}
.lejant i{width:16px;height:16px;display:inline-block;border:1.5px solid var(--murekkep)}
.bolgeler{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:18px}
.bolge{border:1.5px solid var(--murekkep);background:rgba(239,232,214,.9);position:relative;padding:22px 10px 10px}
.bolge h2{position:absolute;top:-10px;left:10px;margin:0;background:var(--kagit);padding:0 6px;font-size:12px;letter-spacing:.2em;text-transform:uppercase}
.bolge .say{position:absolute;top:-9px;right:10px;background:var(--kagit);padding:0 6px;font-size:11px;color:var(--soluk)}
.parseller{display:grid;grid-template-columns:repeat(auto-fill,minmax(54px,1fr));gap:6px}
.parsel{all:unset;cursor:pointer;position:relative;aspect-ratio:1;border:1.5px solid var(--murekkep);display:flex;align-items:flex-end;justify-content:flex-start;
 padding:4px 5px;font-size:12px;font-weight:600;transition:transform .12s}
.parsel:hover,.parsel:focus-visible{transform:translate(-2px,-2px);box-shadow:3px 3px 0 var(--murekkep)}
.parsel.bos{background:repeating-linear-gradient(0deg,transparent 0 9px,rgba(120,100,60,.18) 9px 10px)}
.parsel.bitti{background:var(--bitti);color:#f3efe2}
.parsel.hazir{background:var(--hazir);color:#f3efe2}
.parsel.calis{background:repeating-linear-gradient(45deg,var(--calis) 0 6px,#e5b54c 6px 12px);background-size:17px 17px;animation:kay 1.2s linear infinite}
.parsel.taslak{background:repeating-linear-gradient(45deg,transparent 0 5px,var(--taslak) 5px 7px);border-style:dashed;color:var(--taslak)}
.parsel.kismen{background:linear-gradient(135deg,var(--kismen) 50%,transparent 50%);color:var(--murekkep)}
.parsel.codex{background:repeating-linear-gradient(-45deg,var(--codex) 0 4px,#4fb3bb 4px 8px);color:#f3efe2;border-style:double;border-width:3px}
.parsel.codex b{background:var(--codex);padding:0 2px}
.parsel.kirmizi{background:var(--kirmizi);color:#f3efe2}
.parsel.mavi{background:var(--mavi);color:#f3efe2}
.parsel.kismen b,.parsel.taslak b{background:var(--kagit);padding:0 2px}
.parsel.atl{background:#cfc6ae;color:var(--soluk)}
.parsel.soluk{opacity:.18}
@keyframes kay{to{background-position:17px 0}}
.siradaki::after{content:"";position:absolute;top:-9px;right:-9px;width:16px;height:16px;border-radius:50%;background:var(--isaret);
 box-shadow:0 0 0 0 rgba(192,38,28,.6);animation:nabiz 1.6s infinite;border:2px solid var(--kagit)}
@keyframes nabiz{70%{box-shadow:0 0 0 12px rgba(192,38,28,0)}100%{box-shadow:0 0 0 0 rgba(192,38,28,0)}}
aside{display:flex;flex-direction:column;gap:18px}
.kart{border:1.5px solid var(--murekkep);background:rgba(239,232,214,.95);padding:12px 14px;font-size:12.5px}
.kart h3{margin:0 0 8px;font-size:11px;letter-spacing:.22em;text-transform:uppercase;border-bottom:1px solid var(--cizgi);padding-bottom:6px}
.kart.isaret{border-color:var(--isaret);border-width:2.5px}
.kart.isaret h3{color:var(--isaret)}
.kart .buyuk{font-family:Georgia,serif;font-size:17px;line-height:1.3}
.satir{display:grid;grid-template-columns:58px 1fr;gap:6px;padding:4px 0;border-bottom:1px dotted var(--cizgi)}
.satir:last-child{border-bottom:0}
.satir code,.kart code{font-family:Consolas,monospace;font-size:11.5px}
.dim{color:var(--soluk)}
#detay{min-height:120px}
#detay dl{display:grid;grid-template-columns:90px 1fr;gap:5px 8px;margin:0}
#detay dt{color:var(--soluk)}#detay dd{margin:0}
.nefes{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--bitti);margin-right:6px;animation:nabiz2 2s infinite}
@keyframes nabiz2{50%{opacity:.25}}
@media(max-width:1000px){.sayfa{grid-template-columns:1fr}}
</style></head><body>
<div class="sayfa">
<header>
 <h1>Pafta<small>Aşama 2 · canlı durum paftası</small></h1>
 <div class="kunye" id="kunye"></div>
 <div class="olcek" id="olcek"></div><div class="olcek-yazi" id="olcekYazi"></div>
</header>
<main>
 <div class="lejant" id="lejant"></div>
 <div class="bolgeler" id="bolgeler"></div>
</main>
<aside>
 <div class="kart isaret" id="siradaki"></div>
 <div class="kart" id="detay"><h3>Parsel</h3><span class="dim">Bir parsele tıkla: madde, atanan, durum ve commit burada görünür.</span></div>
 <div class="kart" id="acik"></div>
 <div class="kart" id="defter"></div>
</aside>
</div>
<script>
const V=/*VERI*/null;
const D={bitti:["bitti","bitti (denetçi)","var(--bitti)"],"denetime-hazir":["hazir","denetime hazır","var(--hazir)"],
 calisiliyor:["calis","çalışılıyor","var(--calis)"],taslak:["taslak","taslak (commit edilmemiş)","var(--taslak)"],
 kismen:["kismen","kısmen","var(--kismen)"],"codex-onerildi":["codex","Codex önerildi","var(--codex)"],
 "codex-opus":["kirmizi","Codex / Opus 4.8","var(--kirmizi)"],"claude-alabilir":["mavi","Claude alabilir","var(--mavi)"],atlandi:["atl","atlandı","#cfc6ae"],"":["bos","dokunulmadı","transparent"]};
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const say={};V.maddeler.forEach(m=>say[m.durum]=(say[m.durum]||0)+1);
const toplam=V.maddeler.length;
document.getElementById("kunye").innerHTML=`<span class="nefes"></span>güncellendi <b>${esc(V.zaman)}</b><br>son commit <code>${esc(V.bas)}</code><br>${esc(V.ozet)}`;
const sira=["bitti","denetime-hazir","kismen","claude-alabilir","codex-opus","codex-onerildi","calisiliyor","taslak","atlandi",""];
document.getElementById("olcek").innerHTML=sira.map(k=>say[k]?`<span title="${D[k][1]}: ${say[k]}" style="width:${say[k]/toplam*100}%;background:${D[k][2]}"></span>`:"").join("");
const ilerleme=(say.bitti||0)+(say["denetime-hazir"]||0);
document.getElementById("olcekYazi").innerHTML=`<span>0</span><span>ölçek: ${ilerleme} / ${toplam} parsel bitti ya da denetime hazır</span><span>${toplam}</span>`;
let suzgec=sessionStorage.getItem("suzgec");
function lejant(){document.getElementById("lejant").innerHTML=sira.map(k=>`<button data-k="${k}" aria-pressed="${suzgec===k}"><i class="parsel ${D[k][0]}" style="aspect-ratio:auto;padding:0"></i>${D[k][1]} · ${say[k]||0}</button>`).join("");
 document.querySelectorAll(".lejant button").forEach(b=>b.onclick=()=>{suzgec=suzgec===b.dataset.k?null:b.dataset.k;
  suzgec===null?sessionStorage.removeItem("suzgec"):sessionStorage.setItem("suzgec",suzgec);lejant();ciz()})}
function bolgeAdi(ad){const i=ad.indexOf(":");const b=i>0?ad.slice(0,i):"Diğer";return /^A\d+$/.test(b)?"Açık bulgular":b}
function ciz(){const gr=new Map();V.maddeler.forEach(m=>{const b=bolgeAdi(m.ad);if(!gr.has(b))gr.set(b,[]);gr.get(b).push(m)});
 document.getElementById("bolgeler").innerHTML=[...gr].map(([b,ms])=>{const tamam=ms.filter(m=>m.durum==="bitti"||m.durum==="denetime-hazir").length;
  return `<section class="bolge"><h2>${esc(b)}</h2><span class="say">${tamam}/${ms.length}</span><div class="parseller">${ms.map(m=>
  `<button class="parsel ${D[m.durum][0]} ${m.no===V.siradaki?"siradaki":""} ${suzgec!==null&&suzgec!==m.durum?"soluk":""}" data-no="${m.no}" title="${esc(m.no+". "+m.ad)}"><b>${m.no}</b></button>`).join("")}</div></section>`}).join("");
 document.querySelectorAll(".parsel[data-no]").forEach(p=>p.onclick=()=>detay(+p.dataset.no))}
function detay(no){const m=V.maddeler.find(x=>x.no===no);if(!m)return;sessionStorage.setItem("secili",no);
 document.getElementById("detay").innerHTML=`<h3>Parsel ${m.no}</h3><div class="buyuk">${esc(m.ad.slice(m.ad.indexOf(":")+1).trim())}</div><br><dl>
 <dt>Yol</dt><dd>${esc(bolgeAdi(m.ad))}</dd><dt>Excel'de</dt><dd>${esc(m.atanan)} · ${esc(m.excel)}</dd>
 <dt>Durum</dt><dd>${D[m.durum][1]}</dd><dt>Kim</dt><dd>${esc(m.kim)||"—"}</dd><dt>Commit</dt><dd><code>${esc(m.commit)||"—"}</code></dd>
 <dt>Not</dt><dd>${esc(m.not)||"—"}</dd></dl>`}
const s=V.maddeler.find(m=>m.no===V.siradaki);
document.getElementById("siradaki").innerHTML=s?`<h3>● Sıradaki dokunulmamış parsel</h3><div class="buyuk">${s.no}. ${esc(s.ad)}</div><div class="dim" style="margin-top:6px">Excel'de: ${esc(s.atanan)}</div>`:`<h3>Sıradaki</h3>Dokunulmamış parsel kalmadı.`;
document.getElementById("acik").innerHTML=`<h3>Commit edilmemiş · ${V.acik.length}</h3>`+(V.acik.length?V.acik.map(a=>`<div class="satir"><span class="dim">${esc(a.zaman)}</span><span><code>${esc(a.yol)}</code><br><span class="dim">${esc(a.kim||"sahibi bilinmiyor")}</span></span></div>`).join(""):`<span class="dim">Çalışma ağacı temiz.</span>`);
document.getElementById("defter").innerHTML=`<h3>Saha defteri · son commit'ler</h3>`+V.commitler.map(c=>`<div class="satir"><span class="dim">${esc(c.zaman)}</span><span>${esc(c.konu)}<br><span class="dim"><code>${esc(c.h)}</code> · ${esc(c.ajan||"—")}</span></span></div>`).join("");
lejant();ciz();const sec=+sessionStorage.getItem("secili");if(sec)detay(sec);
addEventListener("scroll",()=>sessionStorage.setItem("kaydir",scrollY));scrollTo(0,+sessionStorage.getItem("kaydir")||0);
setTimeout(()=>location.reload(),20000);
</script></body></html>
"""


if __name__ == "__main__":
    print(uret())
