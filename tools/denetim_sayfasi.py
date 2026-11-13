# -*- coding: utf-8 -*-
"""Denetim sayfası: docs/denetim/puanlar.json'dan docs/denetim/DENETIM_SAYFASI.html üretir.

Puanlar ve eksikler denetçinin elle yazdığı JSON'dadır; bu betik yalnız onu görselleştirir.
Rota aşaması engine/rota.py'den okunur. Sayfa 20 saniyede bir kendini yeniler; post-commit
kancası her commit'ten sonra bu betiği de çalıştırır. Elle:

    python -X utf8 tools/denetim_sayfasi.py
"""
import datetime
import html
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from engine.rota import ASAMALAR  # noqa: E402

GIRDI = os.path.join(ROOT, "docs", "denetim", "puanlar.json")
CIKTI = os.path.join(ROOT, "docs", "denetim", "DENETIM_SAYFASI.html")

# Puan ölçütleri: (anahtar, ad, en çok, açıklama)
OLCUTLER = [
    ("test", "Test sağlamlığı", 25, "validate, tahmin, mutasyon ve elle yanlış çözüm: yanlış cevap geçiyor mu?"),
    ("kapsam", "ASAMA2 kapsamı", 25, "maddenin 'neden' ve 'ne gerekir' sütunları derste ve görevde karşılanıyor mu?"),
    ("derinlik", "Derinlik", 25, "THM/HTB'nin atladığı kısmı (aracın altı, çıktıyı okumak, uyarlamak) öğretiyor mu?"),
    ("gerceklik", "Gerçeklik", 15, "gerçek araç ve gerçek veri mi, yoksa benzetim mi?"),
    ("yol", "Yol değeri", 10, "seçilen HTB/THM yollarında (CJCA, CPTS, CDSA, CAPE, CDEP) ne kadar işe yarıyor?"),
]
KARAR_RENK = {"Tam": "tam", "Kısmen": "kismen", "Eksik": "eksik", "Sorunlu": "sorunlu", "Bekliyor": "bekliyor"}
ONCELIK_SIRA = {"yüksek": 0, "orta": 1, "düşük": 2}

YOL_ASAMA = {tid: i for i, a in enumerate(ASAMALAR) for tid in a["pafta"]}
YOL_ASAMA.update({"bitirme": 3})


def e(s):
    return html.escape(str(s if s is not None else ""))


def toplam(m):
    p = m.get("puan") or {}
    return sum(p.get(k, 0) for k, *_ in OLCUTLER) if p else None


def not_harfi(t):
    if t is None:
        return "—"
    return "A" if t >= 90 else "B" if t >= 75 else "C" if t >= 60 else "D" if t >= 40 else "F"


def git_bas():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                              text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "?"


def kart(m):
    t = toplam(m)
    karar = m.get("karar", "Bekliyor")
    asama = YOL_ASAMA.get(m["yol"])
    olcu = ""
    if m.get("puan"):
        olcu = "".join(
            f'<div class="olcu" title="{e(acik)}"><span>{e(ad)}</span>'
            f'<i><b style="width:{m["puan"].get(k, 0) / en * 100:.0f}%"></b></i>'
            f'<em>{m["puan"].get(k, 0)}/{en}</em></div>' for k, ad, en, acik in OLCUTLER)

    def liste(baslik, xs, sinif):
        if not xs:
            return ""
        xs = sorted(xs, key=lambda x: ONCELIK_SIRA.get(x.get("oncelik", "orta"), 1))
        return (f'<h4>{baslik}</h4><ul class="{sinif}">' + "".join(
            f'<li class="o-{e(x.get("oncelik", "orta"))}">'
            + (f'<span class="etiket">{e(x["etiket"])}</span>' if x.get("etiket") else "")
            + f'{e(x["metin"])}</li>' for x in xs) + "</ul>")

    duzeltme = m.get("duzeltme") or {}
    teslim = ""
    if duzeltme:
        teslim = (f'<div class="duzeltme"><h4>Düzeltme · {e(duzeltme.get("yazar"))}</h4>'
                  f'<p>{e(duzeltme.get("ozet"))}</p>'
                  f'<p>Commit <code>{e(duzeltme.get("commit"))}</code> · {e(duzeltme.get("tarih"))}</p>'
                  f'<p><a href="{e(duzeltme.get("kanit"))}">Doğrulama kanıtı</a> · '
                  f'<a href="{e(duzeltme.get("rapor"))}">Teslim raporu</a></p>'
                  f'<p class="not">{e(duzeltme.get("puan_notu"))} '
                  f'Bağımsız tekrar denetimi: {e(duzeltme.get("bagimsiz_denetim"))}.</p></div>')

    return (f'<article class="kart k-{KARAR_RENK.get(karar, "bekliyor")}" data-karar="{e(karar)}" '
            f'data-asama="{"" if asama is None else asama}" data-yol="{e(m["yol"])}" id="m{m["no"]}">'
            f'<header><span class="no">{m["no"]:02d}</span><div class="bas"><span class="yol">{e(m["yol"])}'
            + (f' · {e(", ".join(m.get("dersler", [])))}' if m.get("dersler") else "")
            + f'</span><h3>{e(m["ad"])}</h3></div>'
            f'<div class="skor"><span class="harf h-{not_harfi(t)}">{not_harfi(t)}</span>'
            f'<span class="puan">{"—" if t is None else t}<small>/100</small></span>'
            f'<span class="karar">{e(karar)}</span></div></header>'
            + (f'<p class="ozet">{e(m["ozet"])}</p>' if m.get("ozet") else "")
            + (f'<div class="olculer">{olcu}</div>' if olcu else "")
            + liste("Eksikler", m.get("eksikler"), "eksikler")
            + liste("Eklenmesi gerekenler", m.get("eklenmeli"), "eklenmeli")
            + teslim
            + liste("Kapatılan bulgular", m.get("kapatilanlar"), "kapatilanlar")
            + liste("İnceleme notları", m.get("inceleme_notlari"), "inceleme-notlari")
            + (f'<p class="not">⚠ {e(m["not"])}</p>' if m.get("not") else "")
            + f'<footer>{e(m.get("tarih", ""))}{" · çıkar çatışması" if m.get("cikar") else ""}'
            + (f' · {e(m["kaynak"])}' if m.get("kaynak") else "") + "</footer></article>")


def uret():
    with open(GIRDI, encoding="utf-8") as f:
        veri = json.load(f)
    maddeler = sorted(veri["maddeler"], key=lambda m: m["no"])
    puanli = [toplam(m) for m in maddeler if toplam(m) is not None]
    ort = sum(puanli) / len(puanli) if puanli else 0
    kararlar = {}
    for m in maddeler:
        kararlar[m.get("karar", "Bekliyor")] = kararlar.get(m.get("karar", "Bekliyor"), 0) + 1
    tum_eksik = [(m, x) for m in maddeler for x in (m.get("eksikler") or []) + (m.get("eklenmeli") or [])]
    oncelikli = sorted([(m, x) for m, x in tum_eksik if x.get("oncelik") == "yüksek"],
                       key=lambda p: (YOL_ASAMA.get(p[0]["yol"], 9), p[0]["no"]))
    asama_ort = []
    for i, a in enumerate(ASAMALAR):
        xs = [toplam(m) for m in maddeler if YOL_ASAMA.get(m["yol"]) == i and toplam(m) is not None]
        asama_ort.append((a["ad"], sum(xs) / len(xs) if xs else None, len(xs)))
    yeni = veri.get("yeni_maddeler", [])

    simdi = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    sayac = "".join(f'<div class="sayac k-{KARAR_RENK.get(k, "bekliyor")}"><b>{kararlar.get(k, 0)}</b>'
                    f'<span>{k}</span></div>' for k in ("Tam", "Kısmen", "Sorunlu", "Eksik", "Bekliyor"))
    asamalar = "".join(
        f'<div class="asama-ort"><span>{i + 1:02d} · {e(ad)}</span><i><b style="width:{o or 0:.0f}%"></b></i>'
        f'<em>{"—" if o is None else f"{o:.0f}"}<small> · {n} madde</small></em></div>'
        for i, (ad, o, n) in enumerate(asama_ort))
    onc = "".join(f'<li><a href="#m{m["no"]}">{m["no"]:02d}</a>'
                  + (f'<span class="etiket">{e(x["etiket"])}</span>' if x.get("etiket") else "")
                  + f'{e(x["metin"])}</li>' for m, x in oncelikli) or "<li>Yok.</li>"
    yeni_html = "".join(f'<li class="o-{e(y.get("oncelik", "orta"))}"><b>{e(y["ad"])}</b>'
                        + (f'<span class="etiket">{e(y["etiket"])}</span>' if y.get("etiket") else "")
                        + f'<p>{e(y.get("neden", ""))}</p></li>' for y in yeni)
    olcut_html = "".join(f'<li><b>{e(ad)}</b> <em>{en}</em> — {e(acik)}</li>' for _, ad, en, acik in OLCUTLER)
    filtre_asama = "".join(f'<button data-f-asama="{i}">{i + 1:02d} {e(a["ad"])}</button>'
                           for i, a in enumerate(ASAMALAR))

    laptop_nav = ('<p class="label"><a href="LAPTOP_DURUM.html">Bu laptopun çalışma doğrulaması</a> · ölçüm kaydı, motor engelleri ve kanıtlar</p>' if os.path.isfile(os.path.join(ROOT, "docs", "denetim", "LAPTOP_DURUM.html")) else "")

    sayfa = f"""<!DOCTYPE html>
<html lang="tr"><head><meta charset="utf-8">
<title>Pafta · denetim ve puanlar</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root{{--bg:#0b2846;--sheet:#0e3054;--sheet2:#0c2b4c;--ink:#e9f1fb;--soft:#b2c7de;--faint:#7593b4;
 --line:rgba(190,218,250,.26);--marker:#ffd43b;--ok:#7ee2b4;--bad:#ff8070;--mor:#c6a8ff;--turuncu:#ffb38a}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 Verdana,"Segoe UI",sans-serif;
 background-image:linear-gradient(rgba(173,208,255,.05) 1px,transparent 1px),linear-gradient(90deg,rgba(173,208,255,.05) 1px,transparent 1px);background-size:32px 32px}}
.sayfa{{max-width:1280px;margin:0 auto;padding:26px 24px 70px}}
h1{{font:700 54px/1 Bahnschrift,"Segoe UI",sans-serif;font-stretch:80%;letter-spacing:.03em;margin:4px 0 6px;text-transform:uppercase}}
h1 em{{font-style:normal;color:var(--marker)}}
.label{{font:500 11px/1.2 "Bahnschrift SemiCondensed",Bahnschrift,sans-serif;letter-spacing:.18em;text-transform:uppercase;color:var(--faint)}}
.ust{{display:grid;grid-template-columns:240px 1fr 1fr;border:1px solid var(--line);background:var(--sheet2);margin:22px 0}}
.ust>div{{padding:18px 20px;border-right:1px solid var(--line)}}.ust>div:last-child{{border-right:0}}
.genel b{{display:block;font:700 72px/1 Bahnschrift,sans-serif;font-stretch:75%;color:var(--marker)}}
.genel b small{{font-size:22px;color:var(--faint);font-weight:400}}
.sayaclar{{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-top:10px}}
.sayac{{border:1px solid var(--line);padding:8px;text-align:center;border-top:3px solid var(--c)}}
.sayac b{{display:block;font:700 28px/1 Bahnschrift,sans-serif;color:var(--c)}}.sayac span{{font-size:11px;color:var(--soft)}}
.asama-ort{{display:grid;grid-template-columns:180px 1fr 90px;gap:10px;align-items:center;margin:6px 0;font-size:12px}}
.asama-ort i,.olcu i{{display:block;height:6px;background:var(--line);position:relative}}
.asama-ort i b,.olcu i b{{position:absolute;inset:0 auto 0 0;background:var(--marker)}}
.asama-ort em{{font:600 15px Bahnschrift,sans-serif;font-style:normal;text-align:right}}.asama-ort small{{color:var(--faint);font-weight:400;font-size:11px}}
.k-tam{{--c:var(--ok)}}.k-kismen{{--c:var(--marker)}}.k-sorunlu{{--c:var(--bad)}}.k-eksik{{--c:var(--turuncu)}}.k-bekliyor{{--c:var(--faint)}}
.blok{{border:1px solid var(--line);background:var(--sheet);padding:16px 20px;margin:18px 0}}
.blok h2{{font:600 15px/1 Bahnschrift,sans-serif;letter-spacing:.24em;text-transform:uppercase;margin:0 0 12px}}
.blok ul{{margin:0;padding-left:0;list-style:none}}.blok li{{padding:6px 0;border-top:1px dashed var(--line)}}
.blok li a{{color:var(--marker);font:700 13px Bahnschrift,sans-serif;margin-right:8px;text-decoration:none}}
.yeni li p{{margin:2px 0 0;color:var(--soft);font-size:12.5px}}
.olcutler li{{font-size:12.5px;color:var(--soft)}}.olcutler em{{color:var(--marker);font-style:normal}}
.filtre{{display:flex;flex-wrap:wrap;gap:6px;margin:24px 0 10px}}
.filtre button{{background:none;border:1px solid var(--line);color:var(--soft);padding:6px 10px;font:12px Bahnschrift,sans-serif;letter-spacing:.06em;cursor:pointer}}
.filtre button.on{{background:var(--marker);color:#1d1600;border-color:var(--marker)}}
.kartlar{{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}}
.kart{{border:1px solid var(--line);border-left:4px solid var(--c);background:var(--sheet);padding:14px 16px}}
.kart header{{display:grid;grid-template-columns:auto 1fr auto;gap:12px;align-items:start}}
.no{{font:700 30px/1 Bahnschrift,sans-serif;font-stretch:75%;color:var(--faint)}}
.yol{{font:11px Bahnschrift,sans-serif;letter-spacing:.14em;text-transform:uppercase;color:var(--faint)}}
.kart h3{{margin:2px 0 0;font:600 15px/1.3 Bahnschrift,sans-serif}}
.skor{{text-align:right;display:grid;justify-items:end;gap:2px}}
.harf{{font:700 26px/1 Bahnschrift,sans-serif;width:38px;height:38px;display:grid;place-items:center;border:2px solid currentColor}}
.h-A{{color:var(--ok)}}.h-B{{color:#a5e88f}}.h-C{{color:var(--marker)}}.h-D{{color:var(--turuncu)}}.h-F{{color:var(--bad)}}.h-—{{color:var(--faint)}}
.puan{{font:600 15px Bahnschrift,sans-serif}}.puan small{{color:var(--faint);font-weight:400}}
.karar{{font:600 10px Bahnschrift,sans-serif;letter-spacing:.16em;text-transform:uppercase;color:var(--c)}}
.ozet{{color:var(--soft);font-size:13px;margin:10px 0 6px}}
.olculer{{display:grid;gap:3px;margin:8px 0}}
.olcu{{display:grid;grid-template-columns:120px 1fr 44px;gap:8px;align-items:center;font-size:11.5px;color:var(--soft)}}
.olcu em{{font-style:normal;text-align:right;font-family:Consolas,monospace;font-size:11px}}
.kart h4{{margin:10px 0 4px;font:600 11px Bahnschrift,sans-serif;letter-spacing:.18em;text-transform:uppercase;color:var(--faint)}}
.kart ul{{margin:0;padding-left:18px;font-size:13px}}.kart li{{margin:3px 0}}
li.o-yüksek::marker{{color:var(--bad)}}li.o-orta::marker{{color:var(--marker)}}li.o-düşük::marker{{color:var(--faint)}}
.etiket{{display:inline-block;font:600 10px/1 Bahnschrift,sans-serif;letter-spacing:.1em;border:1px solid var(--mor);color:var(--mor);padding:2px 5px;margin-right:6px;vertical-align:1px}}
.not{{font-size:12px;color:var(--turuncu)}}
.duzeltme{{border-top:1px dashed var(--line);margin-top:12px;padding-top:4px}}
.duzeltme p{{font-size:12px;margin:5px 0}}.duzeltme a{{color:var(--ok)}}
.kapatilanlar{{color:var(--soft)}}.kapatilanlar li::marker{{color:var(--ok)}}
.kart footer{{margin-top:8px;font-size:11px;color:var(--faint)}}
.gizli{{display:none}}
@media (max-width:900px){{.ust,.kartlar{{grid-template-columns:1fr}}.ust>div{{border-right:0;border-bottom:1px solid var(--line)}}}}
</style></head><body><div class="sayfa">
<span class="label">Pafta · ASAMA2 maddeleri · kaynak: her madde kartında</span>
<h1>Denetim <em>puanları</em></h1>
<p class="label">Son üretim: {simdi} · commit {git_bas()} · {len(puanli)}/{len(maddeler)} madde puanlandı · 20 saniyede bir yenilenir</p>
{laptop_nav}
<section class="ust">
 <div class="genel"><span class="label">Ortalama puan</span><b>{ort:.0f}<small>/100</small></b><span class="label">not {not_harfi(ort if puanli else None)}</span></div>
 <div><span class="label">Kararlar</span><div class="sayaclar">{sayac}</div></div>
 <div><span class="label">Rota aşamasına göre ortalama</span>{asamalar}</div>
</section>
<section class="blok"><h2>Öncelikli eksikler · Rota sırasıyla</h2><ul>{onc}</ul></section>
<section class="blok yeni"><h2>ASAMA2'ye eklenmesi önerilen yeni maddeler</h2><ul>{yeni_html or "<li>Yok.</li>"}</ul></section>
<div class="filtre"><button class="on" data-f-hepsi>Hepsi</button>
 <button data-f-karar="Tam">Tam</button><button data-f-karar="Kısmen">Kısmen</button><button data-f-karar="Sorunlu">Sorunlu</button><button data-f-karar="Eksik">Eksik</button><button data-f-karar="Bekliyor">Bekliyor</button>
 {filtre_asama}</div>
<div class="kartlar">{"".join(kart(m) for m in maddeler)}</div>
<section class="blok olcutler"><h2>Puan ölçütleri (100)</h2><ul>{olcut_html}</ul>
<p class="label">Not: A ≥ 90 · B ≥ 75 · C ≥ 60 · D ≥ 40 · F &lt; 40. Dersi olmayan madde puanlanmaz ("Eksik").</p></section>
</div>
<script>
const KEY="pafta-denetim-filtre";
function uygula(f){{document.querySelectorAll(".filtre button").forEach(b=>b.classList.toggle("on",
 (f.k&&b.dataset.fKarar===f.k)||(f.a!=null&&b.dataset.fAsama===String(f.a))||(!f.k&&f.a==null&&"fHepsi" in b.dataset)));
 document.querySelectorAll(".kart").forEach(k=>k.classList.toggle("gizli",(f.k&&k.dataset.karar!==f.k)||(f.a!=null&&k.dataset.asama!==String(f.a))));
 try{{sessionStorage.setItem(KEY,JSON.stringify(f))}}catch(e){{}}}}
document.querySelector(".filtre").addEventListener("click",ev=>{{const b=ev.target.closest("button");if(!b)return;
 uygula(b.dataset.fKarar?{{k:b.dataset.fKarar}}:b.dataset.fAsama!=null?{{a:+b.dataset.fAsama}}:{{}})}});
try{{uygula(JSON.parse(sessionStorage.getItem(KEY)||"{{}}"))}}catch(e){{}}
const y=sessionStorage.getItem(KEY+"-y");if(y)scrollTo(0,+y);
addEventListener("scroll",()=>sessionStorage.setItem(KEY+"-y",scrollY));
setTimeout(()=>location.reload(),20000);
</script></body></html>
"""
    with open(CIKTI, "w", encoding="utf-8", newline="\n") as f:
        f.write(sayfa)
    return CIKTI, len(puanli), len(maddeler)


if __name__ == "__main__":
    yol, p, n = uret()
    print(f"{yol} · {p}/{n} madde puanlı")
