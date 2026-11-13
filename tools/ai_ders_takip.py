# -*- coding: utf-8 -*-
"""AI dersleri canlı iş tablosu: Claude ve Codex aynı anda çalışırken kim hangi dersi yapıyor.

Durum docs/ai-gercek/takip.json'dadır; ajanlar dosyayı elle değil bu komutlarla değiştirir.
Her komut docs/ai-gercek/TAKIP.html'i yeniden üretir; sayfa 20 saniyede bir kendini yeniler.

    python -X utf8 tools/ai_ders_takip.py                       # tabloyu ders dosyalarından tazele
    python -X utf8 tools/ai_ders_takip.py siradaki --kim codex             # boştaki ilk dersi al
    python -X utf8 tools/ai_ders_takip.py al ai-saldiri-05 --kim codex
    python -X utf8 tools/ai_ders_takip.py durum ai-saldiri-05 denetime-hazir --kim codex --not "3/3 mutant reddedildi"
    python -X utf8 tools/ai_ders_takip.py gereksinim ai-saldiri-05 ollama --kim claude
    python -X utf8 tools/ai_ders_takip.py birak ai-saldiri-05 --kim codex
    python -X utf8 tools/ai_ders_takip.py liste [--kim codex]

Kurallar: başkasının aldığı ders alınamaz ve değiştirilemez (--zorla yalnız kullanıcı isterse).
"bitti" yalnız denetimden sonra yazılır; kendi kontrolünü "denetime-hazir" olarak işaretle.
"""
import argparse
import datetime
import html
import json
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YOLLAR = ["ai-temel", "ai-uretim", "ai-saldiri", "ai-savunma", "ai-guvence", "ai-ile-guvenlik", "kuantum", "ai-matematik", "ai-ctf", "ai-olay", "ai-bulut"]
KLASOR = os.path.join(ROOT, "docs", "ai-gercek")
DURUM_JSON = os.path.join(KLASOR, "takip.json")
CIKTI = os.path.join(KLASOR, "TAKIP.html")
KILIT = DURUM_JSON + ".kilit"

# Sıra = tablodaki ilerleme sırası
DURUMLAR = {
    "eksik": "ders dosyası yok",
    "bekliyor": "bakılmadı",
    "alindi": "alındı",
    "calisiliyor": "çalışılıyor",
    "denetime-hazir": "denetime hazır",
    "bitti": "bitti (denetlendi)",
    "gerekmez": "gerçek deney gerekmez",
    "engelli": "engelli",
}
GEREKSINIMLER = {"?": "belirsiz", "yok": "yok", "ollama": "Ollama sohbet modeli",
                 "torch": "torch (.ai-venv)", "ollama+torch": "Ollama + torch", "docker": "Docker",
                 "baska": "başka araç (nota yaz)"}
SAHIPLI = {"alindi", "calisiliyor", "denetime-hazir"}


def simdi():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


class Kilit:
    """Aynı anda iki ajanın takip.json yazmasını engelleyen dosya kilidi."""

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
                    sys.exit(f"takip.json kilitli ({KILIT}); biraz sonra tekrar dene.")
                time.sleep(0.2)

    def __exit__(self, *a):
        os.close(self.fd)
        os.remove(KILIT)


def oku():
    if not os.path.exists(DURUM_JSON):
        return {"dersler": {}, "gunluk": []}
    with open(DURUM_JSON, encoding="utf-8") as f:
        return json.load(f)


def yaz(veri):
    gecici = DURUM_JSON + f".{os.getpid()}.tmp"
    with open(gecici, "w", encoding="utf-8", newline="\n") as f:
        json.dump(veri, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(gecici, DURUM_JSON)


def ders_tara():
    """track.json modül sırasıyla dersleri ve dosyadan okunabilen gerçekleri döndürür."""
    sonuc = []
    for yol in YOLLAR:
        with open(os.path.join(ROOT, "tracks", yol, "track.json"), encoding="utf-8") as f:
            iz = json.load(f)
        dosyalar = {}
        for ad in os.listdir(os.path.join(ROOT, "tracks", yol, "lessons")):
            m = re.match(r"((?:ai-[a-z-]+|kuantum)-\d+)", ad)
            if m and ad.endswith(".md"):
                dosyalar[m.group(1)] = os.path.join(ROOT, "tracks", yol, "lessons", ad)
        for modul in iz["modules"]:
            for lid in modul["lessons"]:
                d = {"id": lid, "yol": yol, "modul": modul["title"], "baslik": "", "adim": 0,
                     "gercek_adim": 0, "dosya": None}
                yolu = dosyalar.get(lid)
                if yolu:
                    with open(yolu, encoding="utf-8") as f:
                        metin = f.read()
                    m = re.search(r"^title:\s*(.+)$", metin, re.M)
                    d["baslik"] = m.group(1).strip().strip("\"'") if m else ""
                    d["adim"] = len(re.findall(r"^::: *(anlat|tahmin|gorev)\b", metin, re.M))
                    d["gercek_adim"] = len(re.findall(r"^motor:\s*ai-gercek\s*$", metin, re.M))
                    d["dosya"] = os.path.relpath(yolu, ROOT).replace("\\", "/")
                sonuc.append(d)
    return sonuc


def tazele(veri):
    """Dosyalardaki gerçekleri (başlık, adım, gerçek adım, dosya var mı) duruma işler; elle alanlara dokunmaz."""
    for d in ders_tara():
        k = veri["dersler"].setdefault(d["id"], {"durum": "bekliyor", "kim": "", "gereksinim": "?",
                                                   "not": "", "guncelleme": ""})
        k.update({a: d[a] for a in ("yol", "modul", "baslik", "adim", "gercek_adim", "dosya")})
        if not d["dosya"]:
            if k["durum"] == "bekliyor":
                k["durum"] = "eksik"
                k["not"] = k["not"] or "başka oturum yazıyor; dosya gelene kadar dokunma"
        elif k["durum"] == "eksik":
            k["durum"] = "bekliyor"
    veri["tazelendi"] = simdi()
    return veri


def gunluk(veri, kim, ders, olay):
    veri["gunluk"].insert(0, {"zaman": simdi(), "kim": kim, "ders": ders, "olay": olay})
    del veri["gunluk"][200:]


def degistir(args):
    with Kilit():
        veri = tazele(oku())
        if args.komut == "siradaki":
            # Seçim kilit altında yapılır: iki ajan aynı anda istese de aynı dersi alamaz
            args.ders = next((lid for lid, d in veri["dersler"].items()
                              if d["durum"] == "bekliyor" and (not args.yol or d["yol"] == args.yol)), None)
            if not args.ders:
                sys.exit("Boşta ders kalmadı.")
            args.komut = "al"
        k = veri["dersler"].get(args.ders)
        if not k:
            sys.exit(f"Böyle bir ders yok: {args.ders}")
        kim = args.kim.lower()
        baskasi = k["kim"] and k["kim"] != kim and k["durum"] in SAHIPLI
        if baskasi and not args.zorla:
            sys.exit(f"{args.ders} şu an {k['kim']} üzerinde ({k['durum']}). Dokunmadım.")
        if args.komut == "al":
            if k["durum"] == "eksik":
                sys.exit(f"{args.ders} dosyası henüz yok (başka oturum yazıyor). Alınamaz.")
            if k["durum"] == "bitti":
                sys.exit(f"{args.ders} zaten bitti.")
            k.update(durum="alindi", kim=kim)
            olay = "aldı"
        elif args.komut == "birak":
            k.update(durum="bekliyor", kim="")
            olay = "bıraktı"
        elif args.komut == "durum":
            if args.yeni not in DURUMLAR or args.yeni == "eksik":
                sys.exit("Durum şunlardan biri olmalı: " + ", ".join(x for x in DURUMLAR if x != "eksik"))
            k["durum"] = args.yeni
            k["kim"] = "" if args.yeni == "bekliyor" else kim
            olay = f"durum → {DURUMLAR[args.yeni]}"
        else:  # gereksinim
            if args.yeni not in GEREKSINIMLER:
                sys.exit("Gereksinim şunlardan biri olmalı: " + ", ".join(GEREKSINIMLER))
            k["gereksinim"] = args.yeni
            olay = f"gereksinim → {GEREKSINIMLER[args.yeni]}"
        if args.not_ is not None:
            k["not"] = args.not_
            olay += f" · {args.not_}"
        k["guncelleme"] = simdi()
        gunluk(veri, kim, args.ders, olay)
        yaz(veri)
    uret(veri)
    print(f"{args.ders}: {olay} ({kim})")


def uret(veri=None):
    if veri is None:
        with Kilit():
            veri = tazele(oku())
            yaz(veri)
    gecici = CIKTI + f".{os.getpid()}.tmp"
    with open(gecici, "w", encoding="utf-8", newline="\n") as f:
        f.write(sayfa(veri))
    os.replace(gecici, CIKTI)
    return veri


def liste(args):
    veri = oku()
    for lid, k in veri["dersler"].items():
        if args.kim and k["kim"] != args.kim.lower():
            continue
        if args.durum and k["durum"] != args.durum:
            continue
        print(f'{lid:15} {k["durum"]:15} {k["kim"] or "-":8} {k["gereksinim"]:13} {k["baslik"][:60]}')


YOL_ADLARI = {"ai-temel": "AI Temel", "ai-saldiri": "AI Saldırı", "ai-savunma": "AI Savunma", "ai-guvence": "AI Güvence"}
# Ana Pafta'nın docs/DURUM.html paftasıyla aynı görsel dil: durum → parsel sınıfı
SINIF = {"bitti": "bitti", "denetime-hazir": "hazir", "alindi": "calis", "calisiliyor": "calis", "engelli": "kirmizi",
         "gerekmez": "atl", "eksik": "taslak", "bekliyor": "bos"}
LEJANT_SIRASI = ["bitti", "denetime-hazir", "calisiliyor", "alindi", "engelli", "gerekmez", "eksik", "bekliyor"]
OLCEK_RENGI = {"bitti": "var(--bitti)", "hazir": "var(--hazir)", "calis": "var(--calis)", "kirmizi": "var(--kirmizi)",
               "atl": "var(--atl)", "taslak": "repeating-linear-gradient(45deg,transparent 0 4px,var(--taslak) 4px 6px)",
               "bos": "transparent"}
KAPANAN = {"bitti", "denetime-hazir", "gerekmez"}


def _kisa(kim):
    return {"claude": "C", "claude-opus": "◆", "codex": "X", "gemini": "✦", "antigravity": "✦"}.get(kim, kim[:2].upper())


def _parsel(d):
    e = html.escape
    kim = f' ({e(d["kim"])})' if d["kim"] else ""
    rozet = f'<span class="kim">{e(_kisa(d["kim"]))}</span>' if d["kim"] else ""
    return (f'<button type="button" class="parsel {d["sinif"]}" data-id="{e(d["id"])}" data-d="{e(d["durum"])}" '
            f'title="{d["no"]} · {e(d["id"])} · {e(d["baslik"] or "dosya yok")} — {e(d["durum_ad"])}{kim}"><b>{d["no"]}</b>{rozet}</button>')


def sayfa(veri):
    """Bütün içerik sunucu tarafında HTML olarak üretilir; betik çalışmasa da pafta eksiksiz görünür.
    JavaScript yalnız tıklanan parselin ayrıntısını ve lejant filtresini ekler."""
    e = html.escape
    dersler = []
    for no, (lid, k) in enumerate(veri["dersler"].items(), 1):
        dersler.append(dict(k, no=no, id=lid, yol_ad=YOL_ADLARI.get(k["yol"], k["yol"]), sinif=SINIF.get(k["durum"], "bos"),
                            durum_ad=DURUMLAR.get(k["durum"], k["durum"]), gereksinim_ad=GEREKSINIMLER.get(k["gereksinim"], k["gereksinim"]),
                            guncelleme=k["guncelleme"][:16].replace("T", " ")))
    n = len(dersler)
    say = {s: sum(1 for d in dersler if d["durum"] == s) for s in DURUMLAR}
    kapanan = sum(say[s] for s in KAPANAN)
    calisan = [d for d in dersler if d["durum"] in ("calisiliyor", "alindi")]

    kunye = (f'<span class="nefes"></span>güncellendi <b>{e(veri["tazelendi"][:16].replace("T", " "))}</b><br>20 saniyede bir yenilenir<br>'
             f'{say["bitti"]} bitti · {say["denetime-hazir"]} denetime hazır · {len(calisan)} çalışılıyor · {say["bekliyor"]} bakılmadı')
    olcek = "".join(f'<span title="{e(DURUMLAR[s])}: {say[s]}" style="width:{100 * say[s] / n:.3f}%;background:{OLCEK_RENGI[SINIF[s]]}"></span>'
                    for s in LEJANT_SIRASI if say[s])
    olcek_yazi = f"<span>0</span><span>ölçek: {kapanan} / {n} ders bitti, denetime hazır ya da gerçek deney gerekmiyor</span><span>{n}</span>"
    lejant = "".join(f'<button type="button" data-d="{s}" aria-pressed="false"><i class="parsel {SINIF[s]}"></i>{e(DURUMLAR[s])} · {say[s]}</button>'
                     for s in LEJANT_SIRASI)

    yollar = []
    for yol in dict.fromkeys(d["yol"] for d in dersler):
        yd = [d for d in dersler if d["yol"] == yol]
        bolgeler = []
        for modul in dict.fromkeys(d["modul"] for d in yd):
            md = [d for d in yd if d["modul"] == modul]
            parseller = "".join(_parsel(d) for d in md)
            bolgeler.append(f'<div class="bolge"><h2 title="{e(modul)}">{e(modul)}</h2>'
                            f'<span class="say">{sum(d["durum"] in KAPANAN for d in md)}/{len(md)}</span>'
                            f'<div class="parseller">{parseller}</div></div>')
        yollar.append(f'<div class="yol">{e(YOL_ADLARI.get(yol, yol))}<span>{sum(d["durum"] in KAPANAN for d in yd)} / {len(yd)} ders · '
                      f'{yd[0]["no"]}–{yd[-1]["no"]}</span></div><div class="bolgeler">{"".join(bolgeler)}</div>')

    calisan_html = f"<h3>Şu an çalışılan · {len(calisan)}</h3>" + ("".join(
        f'<div class="satir"><b>{d["no"]} · {e(_kisa(d["kim"]))}</b><span><code>{e(d["id"])}</code> {e(d["baslik"])}'
        f'<br><span class="dim">{e(d["kim"])} · {e(d["guncelleme"])}</span></span></div>' for d in calisan)
        or '<span class="dim">Kimse çalışmıyor.</span>')
    kisiler = list(dict.fromkeys(d["kim"] for d in dersler if d["kim"]))
    kisiler_html = ('<h3>Kim ne yaptı</h3><div class="tablo"><span class="dim">kişi</span><span class="dim">hazır</span>'
                    '<span class="dim">bitti</span><span class="dim">açık</span>' + "".join(
                        f'<b>{e(k)} ({e(_kisa(k))})</b><span>{sum(d["kim"] == k and d["durum"] == "denetime-hazir" for d in dersler)}</span>'
                        f'<span>{sum(d["kim"] == k and d["durum"] == "bitti" for d in dersler)}</span>'
                        f'<span>{sum(d["kim"] == k and d["durum"] in ("calisiliyor", "alindi", "engelli") for d in dersler)}</span>'
                        for k in kisiler) + "</div>")
    defter = "<h3>Son hareketler</h3>" + ("".join(
        f'<div class="satir"><span class="dim">{e(g["zaman"][5:16].replace("T", " "))}</span>'
        f'<span><b>{e(g["kim"])}</b> <code>{e(g["ders"])}</code> {e(g["olay"][:140])}</span></div>' for g in veri["gunluk"][:30])
        or '<span class="dim">Henüz hareket yok.</span>')

    ayrinti = {d["id"]: {x: d[x] for x in ("no", "id", "baslik", "yol_ad", "modul", "durum_ad", "kim", "gereksinim_ad", "adim",
                                            "gercek_adim", "guncelleme", "not", "dosya")} for d in dersler}
    gomulu = json.dumps(ayrinti, ensure_ascii=False).replace("</", "<\\/")
    yerler = {"KUNYE": kunye, "OLCEK": olcek, "OLCEKYAZI": olcek_yazi, "LEJANT": lejant, "YOLLAR": "".join(yollar),
              "CALISAN": calisan_html, "KISILER": kisiler_html, "DEFTER": defter, "VERI": gomulu}
    s = SABLON
    for ad, deger in yerler.items():
        s = s.replace("{{" + ad + "}}", deger)
    return s


SABLON = """<!DOCTYPE html>
<html lang="tr"><head><meta charset="utf-8">
<title>Pafta AI · canlı durum</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="20">
<style>
:root{--kagit:#efe8d6;--kagit2:#e6dcc3;--murekkep:#1e2a33;--soluk:#6d6a5e;--cizgi:#b9ad8e;
 --codex:#13808a;--bitti:#2f5d3a;--hazir:#4f8a52;--calis:#c98a12;--taslak:#c4561d;--atl:#cfc6ae;--isaret:#c0261c;--kirmizi:#b3261e;--mavi:#1f5fbf}
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
.lejant i.parsel{width:16px;height:16px;aspect-ratio:auto;padding:0;display:inline-block;cursor:inherit}
.yol{margin:22px 0 14px;font-family:Georgia,serif;letter-spacing:.24em;text-transform:uppercase;font-size:15px;display:flex;justify-content:space-between;
 border-bottom:1.5px solid var(--murekkep);padding-bottom:4px}
.yol span{font-family:Bahnschrift,sans-serif;letter-spacing:.05em;font-size:12px;color:var(--soluk);text-transform:none}
.bolgeler{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:18px}
.bolge{border:1.5px solid var(--murekkep);background:rgba(239,232,214,.9);position:relative;padding:22px 10px 10px}
.bolge h2{position:absolute;top:-10px;left:10px;margin:0;background:var(--kagit);padding:0 6px;font-size:11.5px;letter-spacing:.14em;text-transform:uppercase;
 max-width:calc(100% - 60px);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bolge .say{position:absolute;top:-9px;right:10px;background:var(--kagit);padding:0 6px;font-size:11px;color:var(--soluk)}
.parseller{display:grid;grid-template-columns:repeat(auto-fill,minmax(54px,1fr));gap:6px}
.parsel{all:unset;cursor:pointer;position:relative;aspect-ratio:1;border:1.5px solid var(--murekkep);display:flex;align-items:flex-end;justify-content:flex-start;
 padding:4px 5px;font-size:12px;font-weight:600;transition:transform .12s}
.parsel:hover,.parsel:focus-visible{transform:translate(-2px,-2px);box-shadow:3px 3px 0 var(--murekkep)}
.parsel.secili{outline:3px solid var(--mavi);outline-offset:2px}
.parsel .kim{position:absolute;top:3px;right:4px;font-size:10px;font-weight:700;letter-spacing:.04em}
.parsel.bos{background:repeating-linear-gradient(0deg,transparent 0 9px,rgba(120,100,60,.18) 9px 10px)}
.parsel.bitti{background:var(--bitti);color:#f3efe2}
.parsel.hazir{background:var(--hazir);color:#f3efe2}
.parsel.calis{background:repeating-linear-gradient(45deg,var(--calis) 0 6px,#e5b54c 6px 12px);background-size:17px 17px;animation:kay 1.2s linear infinite}
.parsel.taslak{background:repeating-linear-gradient(45deg,transparent 0 5px,var(--taslak) 5px 7px);border-style:dashed;color:var(--taslak)}
.parsel.taslak b{background:var(--kagit);padding:0 2px}
.parsel.kirmizi{background:var(--kirmizi);color:#f3efe2}
.parsel.atl{background:var(--atl);color:var(--soluk)}
.parsel.soluk{opacity:.18}
@keyframes kay{to{background-position:17px 0}}
aside{display:flex;flex-direction:column;gap:18px}
.kart{border:1.5px solid var(--murekkep);background:rgba(239,232,214,.95);padding:12px 14px;font-size:12.5px}
.kart h3{margin:0 0 8px;font-size:11px;letter-spacing:.22em;text-transform:uppercase;border-bottom:1px solid var(--cizgi);padding-bottom:6px}
.kart.isaret{border-color:var(--calis);border-width:2.5px}
.kart.isaret h3{color:#8a5d06}
.satir{display:grid;grid-template-columns:58px 1fr;gap:6px;padding:4px 0;border-bottom:1px dotted var(--cizgi)}
.satir:last-child{border-bottom:0}
.satir code,.kart code{font-family:Consolas,monospace;font-size:11.5px}
.dim{color:var(--soluk)}
.tablo{display:grid;grid-template-columns:1fr auto auto auto;gap:3px 10px;font-variant-numeric:tabular-nums}
.tablo b{font-weight:600}
#detay{min-height:120px}
#detay dl{display:grid;grid-template-columns:86px 1fr;gap:5px 8px;margin:0}
#detay dt{color:var(--soluk)}#detay dd{margin:0;overflow-wrap:anywhere}
.nefes{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--bitti);margin-right:6px;animation:nabiz2 2s infinite}
@keyframes nabiz2{50%{opacity:.25}}
@media(max-width:1000px){.sayfa{grid-template-columns:1fr}}
@media(prefers-reduced-motion:reduce){.parsel.calis,.nefes{animation:none}}
</style></head>
<body>
<div class="sayfa">
<header>
 <h1>Pafta AI<small>Gerçek deney · canlı durum paftası</small></h1>
 <div class="kunye">{{KUNYE}}</div>
 <div class="olcek">{{OLCEK}}</div><div class="olcek-yazi">{{OLCEKYAZI}}</div>
</header>
<main>
 <div class="lejant" id="lejant">{{LEJANT}}</div>
 <div id="yollar">{{YOLLAR}}</div>
</main>
<aside>
 <div class="kart isaret">{{CALISAN}}</div>
 <div class="kart" id="detay"><h3>Parsel</h3><span class="dim">Bir parselin üstüne gel ya da tıkla: ders, kim yaptı, durum ve not burada görünür.</span></div>
 <div class="kart">{{KISILER}}</div>
 <div class="kart">{{DEFTER}}</div>
</aside>
</div>
<script>
const A={{VERI}};
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
let filtre=null,secili=null;
try{secili=localStorage.getItem("paftaAiSecili");filtre=localStorage.getItem("paftaAiFiltre")||null}catch(e){}
function uygula(){
 document.querySelectorAll(".parsel[data-id]").forEach(p=>{
  const d=p.dataset.d;
  p.classList.toggle("soluk",!!filtre&&filtre!==d&&!(filtre==="calisiliyor"&&d==="alindi"));
  p.classList.toggle("secili",p.dataset.id===secili)});
 document.querySelectorAll("#lejant button").forEach(b=>b.setAttribute("aria-pressed",String(b.dataset.d===filtre)));
 const d=A[secili];
 if(d)document.getElementById("detay").innerHTML=`<h3>Parsel ${d.no}</h3><dl><dt>Ders</dt><dd><code>${esc(d.id)}</code></dd><dt>Başlık</dt><dd>${esc(d.baslik||"—")}</dd>`+
  `<dt>Bölüm</dt><dd>${esc(d.yol_ad)} · ${esc(d.modul)}</dd><dt>Durum</dt><dd><b>${esc(d.durum_ad)}</b></dd><dt>Kim</dt><dd>${esc(d.kim||"—")}</dd>`+
  `<dt>Gereksinim</dt><dd>${esc(d.gereksinim_ad)}</dd><dt>Adım</dt><dd>${d.adim||"—"}${d.gercek_adim?` · ${d.gercek_adim} gerçek deney`:""}</dd>`+
  `<dt>Güncelleme</dt><dd>${esc(d.guncelleme||"—")}</dd><dt>Not</dt><dd>${esc(d.not||"—")}</dd><dt>Dosya</dt><dd><code>${esc(d.dosya||"yok")}</code></dd></dl>`;
}
document.addEventListener("click",e=>{
 const l=e.target.closest("#lejant button");
 if(l){filtre=filtre===l.dataset.d?null:l.dataset.d;try{localStorage.setItem("paftaAiFiltre",filtre||"")}catch(x){}uygula();return}
 const p=e.target.closest(".parsel[data-id]");
 if(p){secili=p.dataset.id;try{localStorage.setItem("paftaAiSecili",secili)}catch(x){}uygula()}
});
try{const y=sessionStorage.getItem("paftaAiKaydir");if(y)addEventListener("load",()=>scrollTo(0,+y))}catch(e){}
addEventListener("beforeunload",()=>{try{sessionStorage.setItem("paftaAiKaydir",scrollY)}catch(e){}});
uygula();
</script></body></html>
"""


def main():
    p = argparse.ArgumentParser(description="AI dersleri canlı iş tablosu")
    alt = p.add_subparsers(dest="komut")
    for ad, yeni in (("al", False), ("birak", False), ("durum", True), ("gereksinim", True)):
        s = alt.add_parser(ad)
        s.add_argument("ders")
        if yeni:
            s.add_argument("yeni")
        s.add_argument("--kim", required=True, help="claude ya da codex")
        s.add_argument("--not", dest="not_", default=None)
        s.add_argument("--zorla", action="store_true", help="başkasının dersini değiştir (yalnız kullanıcı isterse)")
    s = alt.add_parser("siradaki", help="boştaki ilk dersi al (tablo sırasıyla)")
    s.add_argument("--kim", required=True)
    s.add_argument("--yol", choices=YOLLAR)
    s.add_argument("--not", dest="not_", default=None)
    s.set_defaults(ders=None, zorla=False)
    s = alt.add_parser("liste")
    s.add_argument("--kim")
    s.add_argument("--durum")
    args = p.parse_args()
    if args.komut in ("al", "birak", "durum", "gereksinim", "siradaki"):
        degistir(args)
    elif args.komut == "liste":
        liste(args)
    else:
        veri = uret()
        print(f"{len(veri['dersler'])} ders · {CIKTI}")


if __name__ == "__main__":
    main()
