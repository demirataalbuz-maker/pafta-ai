# -*- coding: utf-8 -*-
"""Ortak hafıza panosu: bu projede çalışan TÜM yapay zekâlar (Claude, Codex, ChatGPT, ...)
ne yaptığını buraya yazar, herkes birbirininkini görür. Çakışma (iki ajanın aynı işe girmesi)
bu pano sayesinde önlenir.

Kayıt docs/ai-gercek/pano.json'dadır; ajanlar dosyayı ELLE değil bu komutlarla değiştirir.
Her yazım docs/ai-gercek/PANO.html'i yeniden üretir; sayfa 20 saniyede bir kendini yeniler.

    # Bir işe BAŞLARKEN (başkası aynı işe girmesin diye önce bunu yaz):
    python -X utf8 tools/ai_pano.py yaz --kim claude --tur basladi --konu ai-temel-17 --mesaj "RAG zehirleme dersini yazmaya başladım"

    # İş BİTİNCE:
    python -X utf8 tools/ai_pano.py yaz --kim claude --tur bitti --konu ai-temel-17 --mesaj "denetime hazır, 3/3 mutant reddedildi"

    # Herkese DUYURU / UYARI / SORU / KARAR / NOT:
    python -X utf8 tools/ai_pano.py yaz --kim codex --tur uyari --konu .ai-araclar --mesaj "venv'e kurulum yapıyorum, kimse dokunmasın"

    # Panoyu terminalden OKU (HTML açmadan):
    python -X utf8 tools/ai_pano.py oku            # son 30 kayıt
    python -X utf8 tools/ai_pano.py oku --kim codex --tur basladi -n 10
    python -X utf8 tools/ai_pano.py acik           # şu an açık (başlamış ama bitmemiş) işler
    python -X utf8 tools/ai_pano.py html           # sadece sayfayı yeniden üret

Protokol (her ajan uysun):
 1) Dokunmadan önce PANO'ya bak: aynı işi/ortamı tutan var mı?
 2) Bir işe başlarken 'basladi', bitince 'bitti' yaz. Paylaşılan kaynağa (venv, kurulum) girmeden 'uyari' bırak.
 3) Ders sahipliği için ayrıca ai_ders_takip.py (al/durum) kullanılır; PANO genel anlatım/haberleşme içindir.
"""
import argparse
import datetime
import html
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KLASOR = os.path.join(ROOT, "docs", "ai-gercek")
PANO_JSON = os.path.join(KLASOR, "pano.json")
CIKTI = os.path.join(KLASOR, "PANO.html")
KILIT = PANO_JSON + ".kilit"

TURLER = {
    "basladi": "başladı",
    "bitti": "bitti",
    "not": "not",
    "uyari": "uyarı",
    "soru": "soru",
    "karar": "karar",
}
# tur -> parsel/rozet sınıfı (ana Pafta DURUM paftasıyla aynı görsel dil)
SINIF = {"basladi": "calis", "bitti": "bitti", "not": "mavi", "uyari": "kirmizi", "soru": "taslak", "karar": "karar"}
# Bilinen ajan renkleri; tanınmayan ajan nötr rozet alır.
AJAN = {"claude": "C", "claude-opus": "◆", "codex": "X", "chatgpt": "G", "gpt": "G", "gemini": "✦", "antigravity": "✦", "insan": "👤", "kullanici": "👤"}


def simdi():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


class Kilit:
    """Aynı anda iki ajanın pano.json yazmasını engelleyen dosya kilidi (ai_ders_takip.py ile aynı)."""

    def __enter__(self):
        os.makedirs(KLASOR, exist_ok=True)
        son = time.time() + 15
        while True:
            try:
                self.fd = os.open(KILIT, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(self.fd, f"{os.getpid()} {simdi()}".encode())
                return self
            except FileExistsError:
                try:
                    if time.time() - os.path.getmtime(KILIT) > 60:  # çökmüş yazıcıdan kalan kilit
                        os.remove(KILIT)
                        continue
                except FileNotFoundError:
                    continue
                if time.time() > son:
                    sys.exit(f"pano.json kilitli ({KILIT}); biraz sonra tekrar dene.")
                time.sleep(0.2)

    def __exit__(self, *a):
        os.close(self.fd)
        os.remove(KILIT)


def oku_veri():
    if not os.path.exists(PANO_JSON):
        return {"kayitlar": [], "guncelleme": ""}
    with open(PANO_JSON, encoding="utf-8") as f:
        return json.load(f)


def yaz_veri(veri):
    gecici = PANO_JSON + f".{os.getpid()}.tmp"
    with open(gecici, "w", encoding="utf-8", newline="\n") as f:
        json.dump(veri, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(gecici, PANO_JSON)


def acik_isler(kayitlar):
    """(kim, konu) için en son 'basladi' bir 'bitti' ile kapanmadıysa açık iş sayılır."""
    durum = {}
    for g in reversed(kayitlar):  # eskiden yeniye
        if g["tur"] in ("basladi", "bitti"):
            durum[(g["kim"], g["konu"])] = g
    return [g for g in durum.values() if g["tur"] == "basladi"]


def komut_yaz(args):
    if args.tur not in TURLER:
        sys.exit("tur şunlardan biri olmalı: " + ", ".join(TURLER))
    with Kilit():
        veri = oku_veri()
        veri["kayitlar"].insert(0, {
            "zaman": simdi(),
            "kim": args.kim.lower().strip(),
            "tur": args.tur,
            "konu": (args.konu or "").strip(),
            "mesaj": (args.mesaj or "").strip(),
        })
        del veri["kayitlar"][500:]
        veri["guncelleme"] = simdi()
        yaz_veri(veri)
    uret(veri)
    print(f"[PANO] {args.kim.lower()} · {TURLER[args.tur]} · {args.konu} · {args.mesaj}")


def komut_oku(args):
    veri = oku_veri()
    n = 0
    for g in veri["kayitlar"]:
        if args.kim and g["kim"] != args.kim.lower():
            continue
        if args.tur and g["tur"] != args.tur:
            continue
        print(f'{g["zaman"][5:16].replace("T", " ")}  {g["kim"]:8} {TURLER.get(g["tur"], g["tur"]):8} {g["konu"]:16} {g["mesaj"]}')
        n += 1
        if n >= args.n:
            break
    if not n:
        print("(pano boş)")


def komut_acik(args):
    veri = oku_veri()
    acik = acik_isler(veri["kayitlar"])
    if not acik:
        print("Şu an açık iş yok.")
        return
    print("Şu an açık (başlamış ama bitmemiş) işler:")
    for g in sorted(acik, key=lambda x: x["zaman"], reverse=True):
        print(f'  {g["kim"]:8} {g["konu"]:16} {g["zaman"][5:16].replace("T", " ")}  {g["mesaj"]}')


# ---------------------------------------------------------------- HTML üretimi

def _rozet(kim):
    return AJAN.get(kim, (kim[:2].upper() if kim else "?"))


def uret(veri=None):
    if veri is None:
        veri = oku_veri()
    gecici = CIKTI + f".{os.getpid()}.tmp"
    with open(gecici, "w", encoding="utf-8", newline="\n") as f:
        f.write(sayfa(veri))
    os.replace(gecici, CIKTI)
    return veri


def sayfa(veri):
    """Bütün içerik sunucu tarafında HTML olarak üretilir; betik çalışmasa da pano eksiksiz görünür
    (file:// ile açılsa bile). JavaScript yalnız kişi/tür filtresi ekler ve sunucudan canlı tazeler."""
    e = html.escape
    kayitlar = veri.get("kayitlar", [])
    acik = acik_isler(kayitlar)
    kisiler = list(dict.fromkeys(g["kim"] for g in kayitlar if g["kim"]))
    say_tur = {t: sum(1 for g in kayitlar if g["tur"] == t) for t in TURLER}

    # Künye
    gunc = (veri.get("guncelleme") or (kayitlar[0]["zaman"] if kayitlar else ""))[:16].replace("T", " ")
    kunye = (f'<span class="nefes"></span>güncellendi <b>{e(gunc) or "—"}</b><br>20 saniyede bir yenilenir<br>'
             f'{len(kayitlar)} kayıt · {len(acik)} açık iş · {len(kisiler)} ajan')

    # Açık işler kartı (en kritik: kim şu an ne yapıyor)
    acik_html = f"<h3>Şu an açık işler · {len(acik)}</h3>" + ("".join(
        f'<div class="satir"><b title="{e(g["kim"])}">{e(_rozet(g["kim"]))}</b>'
        f'<span><code>{e(g["konu"] or "—")}</code> {e(g["mesaj"])}'
        f'<br><span class="dim">{e(g["kim"])} · {e(g["zaman"][5:16].replace("T", " "))}</span></span></div>'
        for g in sorted(acik, key=lambda x: x["zaman"], reverse=True))
        or '<span class="dim">Şu an açık iş yok. Bir işe başlarken <code>basladi</code> yaz.</span>')

    # Kişi özeti
    kisiler_html = ('<h3>Ajanlar</h3><div class="tablo"><span class="dim">ajan</span><span class="dim">açık</span>'
                    '<span class="dim">bitti</span><span class="dim">kayıt</span>' + ("".join(
                        f'<b>{e(k)} ({e(_rozet(k))})</b>'
                        f'<span>{sum(1 for g in acik if g["kim"] == k)}</span>'
                        f'<span>{sum(1 for g in kayitlar if g["kim"] == k and g["tur"] == "bitti")}</span>'
                        f'<span>{sum(1 for g in kayitlar if g["kim"] == k)}</span>'
                        for k in kisiler) or '<span class="dim" style="grid-column:1/-1">Henüz ajan yok.</span>') + "</div>")

    # Filtre düğmeleri (tür + kişi)
    tur_dugme = "".join(
        f'<button type="button" data-f="tur:{t}" aria-pressed="false"><i class="nokta {SINIF[t]}"></i>{e(TURLER[t])} · {say_tur[t]}</button>'
        for t in TURLER if say_tur[t])
    kisi_dugme = "".join(
        f'<button type="button" data-f="kim:{e(k)}" aria-pressed="false"><b class="rz">{e(_rozet(k))}</b>{e(k)}</button>'
        for k in kisiler)

    # Akış (newest first)
    satirlar = []
    for g in kayitlar[:300]:
        s = SINIF.get(g["tur"], "mavi")
        konu_html = f"<code>{e(g['konu'])}</code> " if g["konu"] else ""
        satirlar.append(
            f'<li class="kayit {s}" data-kim="{e(g["kim"])}" data-tur="{e(g["tur"])}">'
            f'<span class="zaman">{e(g["zaman"][5:16].replace("T", " "))}</span>'
            f'<span class="rozet" title="{e(g["kim"])}">{e(_rozet(g["kim"]))}</span>'
            f'<span class="govde"><span class="etiket {s}">{e(TURLER.get(g["tur"], g["tur"]))}</span>'
            f'{konu_html}{e(g["mesaj"]) or "<span class=dim>—</span>"}</span></li>')
    akis = "".join(satirlar) or '<li class="dim" style="padding:14px">Pano boş. İlk kaydı yaz.</li>'

    rehber_yolu = os.path.join(KLASOR, "YENI-AJAN-REHBERI.md")
    with open(rehber_yolu, encoding="utf-8") as rehber_dosyasi:
        rehber = e(rehber_dosyasi.read())
    yerler = {"REHBER": rehber, "KUNYE": kunye, "ACIK": acik_html, "KISILER": kisiler_html,
              "TURDUGME": tur_dugme, "KISIDUGME": kisi_dugme, "AKIS": akis}
    s = SABLON
    for ad, deger in yerler.items():
        s = s.replace("{{" + ad + "}}", deger)
    return s


SABLON = """<!DOCTYPE html>
<html lang="tr"><head><meta charset="utf-8">
<title>Pafta AI · ortak pano</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="20">
<style>
:root{--kagit:#efe8d6;--kagit2:#e6dcc3;--murekkep:#1e2a33;--soluk:#6d6a5e;--cizgi:#b9ad8e;
 --bitti:#2f5d3a;--calis:#c98a12;--taslak:#c4561d;--kirmizi:#b3261e;--mavi:#1f5fbf;--karar:#5a3a9a}
*{box-sizing:border-box}
body{margin:0;background:var(--kagit);color:var(--murekkep);font-family:Bahnschrift,"Segoe UI",system-ui,sans-serif;
 background-image:repeating-radial-gradient(circle at 80% 10%,transparent 0 38px,rgba(120,100,60,.09) 38px 39px),
 linear-gradient(rgba(120,100,60,.07) 1px,transparent 1px),linear-gradient(90deg,rgba(120,100,60,.07) 1px,transparent 1px);
 background-size:auto,40px 40px,40px 40px}
.sayfa{max-width:1380px;margin:0 auto;padding:22px 26px 60px;display:grid;grid-template-columns:1fr 330px;gap:26px}
header{grid-column:1/-1;display:grid;grid-template-columns:1fr auto;border:3px double var(--murekkep);padding:14px 18px;background:rgba(239,232,214,.85)}
h1{margin:0;font-family:Georgia,"Times New Roman",serif;font-weight:normal;letter-spacing:.3em;font-size:28px;text-transform:uppercase}
h1 small{display:block;letter-spacing:.16em;font-size:12px;color:var(--soluk);margin-top:4px;font-family:Bahnschrift,sans-serif}
.kunye{text-align:right;font-size:12px;line-height:1.7;color:var(--soluk)}
.kunye b{color:var(--murekkep)}
.protokol{grid-column:1/-1;border:2px solid var(--murekkep);background:rgba(201,138,18,.10);padding:12px 16px;font-size:12.5px;line-height:1.6}
.protokol h2{margin:0 0 6px;font-size:11px;letter-spacing:.2em;text-transform:uppercase}
.protokol code{font-family:Consolas,monospace;font-size:11.5px;background:rgba(30,42,51,.07);padding:1px 4px}
.protokol ol{margin:6px 0 0;padding-left:20px}
main{min-width:0}
.filtre{display:flex;flex-wrap:wrap;gap:6px 10px;margin:0 0 14px;font-size:12.5px;align-items:center}
.filtre button{all:unset;cursor:pointer;display:flex;align-items:center;gap:6px;padding:3px 9px;border:1px solid var(--cizgi)}
.filtre button[aria-pressed=true]{border-color:var(--murekkep);background:rgba(30,42,51,.08)}
.filtre .ayrac{width:1px;height:18px;background:var(--cizgi);margin:0 2px}
.filtre .rz{font-size:10px;font-weight:700;border:1px solid var(--murekkep);border-radius:50%;width:16px;height:16px;display:flex;align-items:center;justify-content:center}
.nokta{width:12px;height:12px;display:inline-block;border:1px solid var(--murekkep)}
.nokta.calis{background:var(--calis)}.nokta.bitti{background:var(--bitti)}.nokta.mavi{background:var(--mavi)}
.nokta.kirmizi{background:var(--kirmizi)}.nokta.taslak{background:var(--taslak)}.nokta.karar{background:var(--karar)}
.akis{list-style:none;margin:0;padding:0;border:1.5px solid var(--murekkep);background:rgba(239,232,214,.92)}
.kayit{display:grid;grid-template-columns:86px 26px 1fr;gap:10px;align-items:start;padding:9px 12px;border-bottom:1px dotted var(--cizgi);border-left:5px solid var(--cizgi)}
.kayit:last-child{border-bottom:0}
.kayit.calis{border-left-color:var(--calis)}.kayit.bitti{border-left-color:var(--bitti)}.kayit.mavi{border-left-color:var(--mavi)}
.kayit.kirmizi{border-left-color:var(--kirmizi)}.kayit.taslak{border-left-color:var(--taslak)}.kayit.karar{border-left-color:var(--karar)}
.kayit.gizli{display:none}
.zaman{font-size:11px;color:var(--soluk);font-variant-numeric:tabular-nums;padding-top:2px}
.rozet{font-size:11px;font-weight:700;border:1.5px solid var(--murekkep);border-radius:50%;width:24px;height:24px;display:flex;align-items:center;justify-content:center}
.govde{font-size:13px;line-height:1.5;overflow-wrap:anywhere}
.govde code{font-family:Consolas,monospace;font-size:11.5px;background:rgba(30,42,51,.06);padding:1px 4px}
.etiket{font-size:10px;letter-spacing:.08em;text-transform:uppercase;padding:1px 6px;margin-right:6px;color:#f3efe2;white-space:nowrap}
.etiket.calis{background:var(--calis)}.etiket.bitti{background:var(--bitti)}.etiket.mavi{background:var(--mavi)}
.etiket.kirmizi{background:var(--kirmizi)}.etiket.taslak{background:var(--taslak)}.etiket.karar{background:var(--karar)}
aside{display:flex;flex-direction:column;gap:18px}
.kart{border:1.5px solid var(--murekkep);background:rgba(239,232,214,.95);padding:12px 14px;font-size:12.5px}
.kart h3{margin:0 0 8px;font-size:11px;letter-spacing:.2em;text-transform:uppercase;border-bottom:1px solid var(--cizgi);padding-bottom:6px}
.kart.isaret{border-color:var(--calis);border-width:2.5px}
.kart.isaret h3{color:#8a5d06}
.satir{display:grid;grid-template-columns:26px 1fr;gap:8px;padding:5px 0;border-bottom:1px dotted var(--cizgi)}
.satir:last-child{border-bottom:0}
.satir b{font-size:11px;font-weight:700;border:1.5px solid var(--murekkep);border-radius:50%;width:24px;height:24px;display:flex;align-items:center;justify-content:center}
.satir code,.kart code{font-family:Consolas,monospace;font-size:11.5px}
.dim{color:var(--soluk)}
.tablo{display:grid;grid-template-columns:1fr auto auto auto;gap:3px 10px;font-variant-numeric:tabular-nums}
.nefes{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--bitti);margin-right:6px;animation:nabiz 2s infinite}
@keyframes nabiz{50%{opacity:.25}}
@media(max-width:980px){.sayfa{grid-template-columns:1fr}}
@media(prefers-reduced-motion:reduce){.nefes{animation:none}}
</style></head>
<body>
<div class="sayfa">
<header>
 <h1>Pafta AI<small>Ortak hafıza panosu · burada çalışan tüm yapay zekâlar</small></h1>
 <p style="grid-column:1/-1;margin:12px 0 0"><a href="YENI-DERSLER.html" style="font-weight:700">→ Yeni eklenecek dersler · konu / sorumlu / durum tablosu</a></p>
 <div class="kunye">{{KUNYE}}</div>
</header>
<div class="protokol">
 <h2>Bu pano nedir · her ajan okusun</h2>
 <p><b>Kullanıcı kararı · 29 Ekim 2026:</b> Bundan sonraki uygun örneklerde öğrenci ham veriyi açabileceği ve çalışma kopyasını değiştirebileceği dosyalarla çalışacak. Görünür örnek, gizli test ve canlı deney ayrı tutulacak. Bu, bütün eski derslerin dönüştürüldüğü anlamına gelmez.</p>
 <details><summary><b>Yeni katılan AI: işe başlamadan önce ayrıntılı ortak rehberi aç ve oku</b></summary>
 <p>Kalıcı kaynak: <a href="YENI-AJAN-REHBERI.md">YENI-AJAN-REHBERI.md</a>. Aşağıdaki metin filtrelerden ve son kayıtların sayısından bağımsızdır.</p>
 <div style="white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.6">{{REHBER}}</div></details>
 Bu projede çalışan <b>tüm yapay zekâlar</b> (Claude, Codex, ChatGPT, ...) ne yaptığını buraya yazar; herkes birbirininkini görür. Amaç: iki ajanın aynı işe/kaynağa girip çakışmasını önlemek.
 <ol>
  <li>Dokunmadan önce panoya bak: aynı işi/ortamı tutan var mı? (<code>python -X utf8 tools/ai_pano.py acik</code>)</li>
  <li>Bir işe başlarken <code>basladi</code>, bitince <code>bitti</code> yaz. Paylaşılan kaynağa (venv, kurulum) girmeden <code>uyari</code> bırak.</li>
  <li>Yazım: <code>python -X utf8 tools/ai_pano.py yaz --kim &lt;ad&gt; --tur &lt;basladi|bitti|not|uyari|soru|karar&gt; --konu &lt;etiket&gt; --mesaj "..."</code></li>
  <li>Ders sahipliği ayrıca <code>ai_ders_takip.py</code> (al/durum) ile; pano genel haberleşme/karar içindir.</li>
 </ol>
</div>
<main>
 <div class="filtre" id="filtre">
  {{TURDUGME}}<span class="ayrac"></span>{{KISIDUGME}}
 </div>
 <ul class="akis" id="akis">{{AKIS}}</ul>
</main>
<aside>
 <div class="kart isaret">{{ACIK}}</div>
 <div class="kart">{{KISILER}}</div>
 <div class="kart"><h3>Türler</h3>
  <div class="dim" style="line-height:1.9">
   <span class="etiket calis">başladı</span> işe giriştim<br>
   <span class="etiket bitti">bitti</span> iş tamam<br>
   <span class="etiket mavi">not</span> bilgi/durum<br>
   <span class="etiket kirmizi">uyarı</span> dikkat / dokunma<br>
   <span class="etiket taslak">soru</span> karar bekliyor<br>
   <span class="etiket karar">karar</span> ortak karar
  </div>
 </div>
</aside>
</div>
<script>
let fTur=null,fKim=null;
try{fTur=localStorage.getItem("paftaPanoTur")||null;fKim=localStorage.getItem("paftaPanoKim")||null}catch(e){}
function uygula(){
 document.querySelectorAll("#akis .kayit").forEach(li=>{
  const g=(!fTur||li.dataset.tur===fTur)&&(!fKim||li.dataset.kim===fKim);
  li.classList.toggle("gizli",!g)});
 document.querySelectorAll("#filtre button").forEach(b=>{
  const [t,v]=b.dataset.f.split(":");
  b.setAttribute("aria-pressed",String((t==="tur"&&v===fTur)||(t==="kim"&&v===fKim)))});
}
document.getElementById("filtre").addEventListener("click",e=>{
 const b=e.target.closest("button");if(!b)return;
 const [t,v]=b.dataset.f.split(":");
 if(t==="tur")fTur=fTur===v?null:v; else fKim=fKim===v?null:v;
 try{localStorage.setItem("paftaPanoTur",fTur||"");localStorage.setItem("paftaPanoKim",fKim||"")}catch(x){}
 uygula();
});
uygula();
</script></body></html>
"""


def main():
    p = argparse.ArgumentParser(description="Pafta AI ortak hafıza panosu")
    alt = p.add_subparsers(dest="komut")
    y = alt.add_parser("yaz", help="panoya kayıt ekle")
    y.add_argument("--kim", required=True, help="ajan adı: claude, codex, chatgpt, ...")
    y.add_argument("--tur", required=True, help="basladi|bitti|not|uyari|soru|karar")
    y.add_argument("--konu", default="", help="kısa etiket: ai-temel-17, Parti 1, .ai-araclar ...")
    y.add_argument("--mesaj", required=True, help="ne yaptın / ne diyorsun")
    o = alt.add_parser("oku", help="panoyu terminalden oku")
    o.add_argument("--kim")
    o.add_argument("--tur")
    o.add_argument("-n", type=int, default=30)
    alt.add_parser("acik", help="şu an açık (başlamış ama bitmemiş) işler")
    alt.add_parser("html", help="sadece PANO.html'i yeniden üret")
    args = p.parse_args()
    if args.komut == "yaz":
        komut_yaz(args)
    elif args.komut == "oku":
        komut_oku(args)
    elif args.komut == "acik":
        komut_acik(args)
    else:
        uret()
        print(f"PANO.html üretildi · {CIKTI}")


if __name__ == "__main__":
    main()
