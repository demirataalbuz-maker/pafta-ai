# -*- coding: utf-8 -*-
"""AI ve kuantum dersleri denetim sayfaları: docs/ai-gercek/ai-puanlar.json →
docs/ai-gercek/AI_DENETIM.html (AI yolları) ve docs/ai-gercek/KUANTUM_DENETIM.html (kuantum yolu).

Puanlar ve bulgular denetçinin JSON'a yazdığı değerlerdir; bu betik yalnız görselleştirir.
Ölçütler docs/denetim (purple ve ilk Pafta) puan tablosunun AI'ya uyarlanmış hâlidir; görünüm
tools/denetim_sayfasi.py (DENETIM_SAYFASI.html) ile aynıdır. Her sayfada derslerin A'ya ve tam puana ne kadar
uzak olduğunu ölçüt ölçüt gösteren bir eksik puan tablosu vardır. Sayfalar 20 saniyede bir kendini yeniler. Elle:

    python -X utf8 tools/ai_denetim_sayfasi.py
"""
import datetime
import html
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KLASOR = os.path.join(ROOT, "docs", "ai-gercek")
GIRDI = os.path.join(KLASOR, "ai-puanlar.json")
CIKTI = os.path.join(KLASOR, "AI_DENETIM.html")
CIKTI_KUANTUM = os.path.join(KLASOR, "KUANTUM_DENETIM.html")

# (anahtar, ad, en çok, açıklama) — docs/denetim puan tablosuyla aynı ağırlıklar
OLCUTLER = [
    ("test", "Test sağlamlığı", 25, "validate, tahmin, mutasyon ve elle yanlış çözüm: yanlış cevap geçiyor mu?"),
    ("kapsam", "Plan kapsamı", 25, "ai_mufredat_plan_v3 özetindeki 'ne öğretir' derste ve görevde karşılanıyor mu?"),
    ("derinlik", "Derinlik", 25, "aracın altını, çıktıyı okumayı, sınırları ve tuzakları öğretiyor mu?"),
    ("gerceklik", "Gerçeklik", 15, "gerçek model/araç ve gerçek biçimli veri mi; kanıt bu bilgisayarda üretildi mi?"),
    ("yol", "Yol değeri", 10, "HTB AI Red Teamer, OWASP LLM Top 10 (2025) ve NIST AI RMF açısından değeri"),
]
# Lab yolu olmayan yollar için aynı anahtar ve ağırlıklarla farklı anlam (kullanıcı kararı, 09.11.2026: kuantum yolu
# gerçek donanım/lab değil, bilgi ve anlatım üzerinden değerlendirilir).
OLCUTLER_YOL = {
    "kuantum": [
        ("test", "Bilgi doğruluğu", 25, "anlatım, tahmin ve görev cevapları doğru mu; hata, abartı, yanlış atıf var mı?"),
        ("kapsam", "Bilgi yeterliliği", 25, "başlığın vaat ettiği konular anlatımda ve görevlerde yeterince işleniyor mu?"),
        ("derinlik", "Anlatım", 25, "açıklık, benzetmeler, akış, terimlerin doğru kullanımı"),
        ("gerceklik", "Sınırlar ve kaynaklar", 15, "sınırlar ve tuzaklar yazılmış mı; kaynaklar doğrulanmış mı?"),
        ("yol", "Alıştırma", 10, "simülasyon görevleri ve tahminler kavramı sınıyor mu, testler sağlam mı?"),
    ],
}


def olcutler(d):
    return OLCUTLER_YOL.get(d.get("yol"), OLCUTLER)


YOLLAR = [("ai-temel", "AI Temelleri"), ("ai-saldiri", "AI Saldırı"), ("ai-savunma", "AI Savunma"), ("ai-guvence", "AI Güvence"), ("ai-ile-guvenlik", "AI ile Güvenlik"),
          ("ai-uretim", "AI Üretimi"), ("kuantum", "Kuantum ve Kripto"), ("ai-matematik", "AI Matematiği"), ("ai-ctf", "AI CTF"), ("ai-olay", "AI Olayları"), ("ai-bulut", "AI Bulut"), ("python", "Python (AI için)")]
DURUM = {"puanlandi": "puanlandı", "denetleniyor": "denetleniyor", "bekliyor": "sırada", "kapsam-disi": "bağımsız denetim bekliyor",
         "oz-puan": "yazar öz puanı · bağımsız değil"}
KARAR_RENK = {"Tam": "tam", "Kısmen": "kismen", "Eksik": "eksik", "Sorunlu": "sorunlu", "Bekliyor": "bekliyor"}
ONCELIK_SIRA = {"yüksek": 0, "orta": 1, "düşük": 2}
YOL_SIRA = {yid: i for i, (yid, _) in enumerate(YOLLAR)}


def e(s):
    return html.escape(str(s if s is not None else ""))


def toplam(d):
    p = d.get("puan") or {}
    return sum(p.get(k, 0) for k, *_ in OLCUTLER) if p else None


def not_harfi(t):
    if t is None:
        return "—"
    return "A" if t >= 90 else "B" if t >= 75 else "C" if t >= 60 else "D" if t >= 40 else "F"


def kimlik(d):
    return "d-" + d["id"]


def kart(d):
    t = toplam(d)
    karar = d.get("karar") or "Bekliyor"
    durum = d.get("durum", "bekliyor")
    olcu = ""
    if d.get("puan"):
        olcu = "".join(
            f'<div class="olcu" title="{e(acik)}"><span>{e(ad)}</span>'
            f'<i><b style="width:{d["puan"].get(k, 0) / en * 100:.0f}%"></b></i>'
            f'<em>{d["puan"].get(k, 0)}/{en}</em></div>' for k, ad, en, acik in olcutler(d))

    def liste(baslik, xs, sinif):
        if not xs:
            return ""
        xs = sorted(xs, key=lambda x: ONCELIK_SIRA.get(x.get("oncelik", "orta"), 1))
        return (f'<h4>{baslik}</h4><ul class="{sinif}">' + "".join(
            f'<li class="o-{e(x.get("oncelik", "orta"))}">'
            + (f'<span class="etiket">{e(x["etiket"])}</span>' if x.get("etiket") else "")
            + f'{e(x["metin"])}</li>' for x in xs) + "</ul>")

    olcum = " · ".join(f"{k}: {v}" for k, v in (d.get("olcum") or {}).items())
    no = d["id"].rsplit("-", 1)[-1]
    return (f'<article class="kart k-{KARAR_RENK.get(karar, "bekliyor")}" data-karar="{e(karar)}" '
            f'data-yol="{e(d["yol"])}" data-durum="{e(durum)}" id="{kimlik(d)}">'
            f'<header><span class="no">{e(no)}</span><div class="bas"><span class="yol">{e(d["id"])}'
            + (f' · <span class="etiket">{e(DURUM.get(durum, durum))}</span>' if durum != "puanlandi" else "")
            + f'</span><h3>{e(d.get("baslik", ""))}</h3></div>'
            f'<div class="skor"><span class="harf h-{not_harfi(t)}">{not_harfi(t)}</span>'
            f'<span class="puan">{"—" if t is None else t}<small>/100</small></span>'
            f'<span class="karar">{e(karar)}</span></div></header>'
            + (f'<p class="ozet">{e(d["ozet"])}</p>' if d.get("ozet") else "")
            + (f'<p class="olcum">{e(olcum)}</p>' if olcum else "")
            + (f'<div class="olculer">{olcu}</div>' if olcu else "")
            + liste("Eksikler", d.get("eksikler"), "eksikler")
            + liste("Kapatılan bulgular", d.get("duzeltilenler"), "kapatilanlar")
            + f'<footer>{e(d.get("tarih", ""))}{" · çıkar çatışması" if d.get("cikar") else ""}'
            + (f' · {e(d["kaynak"])}' if d.get("kaynak") else "") + "</footer></article>")


KISA = {"test": "Test", "kapsam": "Kapsam", "derinlik": "Derinlik", "gerceklik": "Gerçeklik", "yol": "Yol"}
KISA_YOL = {"kuantum": {"test": "Doğruluk", "kapsam": "Yeterlilik", "derinlik": "Anlatım", "gerceklik": "Sınır/kaynak", "yol": "Alıştırma"}}


def eksik_tablosu(dersler, kriter, kisa):
    """Kim ne kadar eksik: her dersin A'ya ve 100'e kalan puanı, ölçüt ölçüt kaybı; en eksik ders üstte."""
    puanli = sorted((d for d in dersler if d.get("puan")), key=lambda d: (toplam(d), d["id"]))
    alt = [d for d in puanli if toplam(d) < 90]
    bas = "".join(f'<th title="{e(acik)}">{e(kisa.get(k, ad))}<small> /{en}</small></th>' for k, ad, en, acik in kriter)
    satir = []
    for d in puanli:
        t = toplam(d)
        hucre = ""
        for k, _, en, _ in kriter:
            kayip = en - d["puan"].get(k, 0)
            hucre += '<td class="sifir">·</td>' if kayip == 0 else f'<td class="eksi">−{kayip}</td>'
        eks = d.get("eksikler") or []
        ilk = ", ".join(dict.fromkeys(x.get("etiket", "") for x in sorted(eks, key=lambda x: ONCELIK_SIRA.get(x.get("oncelik", "orta"), 1)) if x.get("etiket")))
        sinif, a_kalan = ("a-alti", str(90 - t)) if t < 90 else ("a", "·")
        a_sinif = "eksi" if t < 90 else "sifir"
        satir.append(f'<tr class="{sinif}"><td><a href="#{kimlik(d)}">{e(d["id"])}</a></td>'
                     f'<td class="baslik">{e(d.get("baslik", ""))}</td><td class="sayi"><b>{t}</b></td>'
                     f'<td><span class="harf-k h-{not_harfi(t)}">{not_harfi(t)}</span></td>'
                     f'<td class="sayi {a_sinif}">{a_kalan}</td><td class="sayi">{100 - t}</td>{hucre}'
                     f'<td class="sayi">{len(eks)}</td><td class="etk">{e(ilk)}</td></tr>')
    kayiplar = []
    for k, ad, en, _ in kriter:
        kayiplar.append(f"{kisa.get(k, ad)} {sum(en - d['puan'].get(k, 0) for d in puanli)}")
    a_top = sum(90 - toplam(d) for d in alt)
    tam_top = sum(100 - toplam(d) for d in puanli)
    ozet = (f"{len(alt)} ders A'nın altında; A'ya toplam {a_top} puan, tam puana toplam {tam_top} puan eksik. "
            f"Ölçüt başına toplam kayıp: {', '.join(kayiplar)}.")
    return (f'<section class="blok tablo"><h2>Kim ne kadar eksik · en eksik ders üstte</h2><p class="tablo-ozet">{e(ozet)}</p>'
            f'<label class="label secim"><input type="checkbox" id="yalniz-alt"> yalnız A\'nın altındakileri göster</label>'
            f'<div class="kaydir"><table><thead><tr><th>Ders</th><th>Başlık</th><th>Puan</th><th>Not</th><th title="90 − puan">A\'ya kalan</th>'
            f'<th title="100 − puan">100\'e kalan</th>{bas}<th>Açık eksik</th><th>Eksik türleri</th></tr></thead><tbody>{"".join(satir)}</tbody></table></div></section>')


def uret(yol_kumesi=None, cikti=CIKTI, baslik='AI Denetim <em>puanları</em>', ust_label="Pafta · AI dersleri · denetçi: claude-opus",
         belge_baslik="Pafta · AI denetim ve puanlar", anahtar="pafta-ai-denetim-filtre"):
    """yol_kumesi: sayfada gösterilecek yol kimlikleri (None: kuantum hariç bütün AI yolları)."""
    with open(GIRDI, encoding="utf-8") as f:
        veri = json.load(f)
    yollar_sayfa = [(yid, yad) for yid, yad in YOLLAR if (yid in yol_kumesi if yol_kumesi else yid not in OLCUTLER_YOL)]
    kume = {yid for yid, _ in yollar_sayfa}
    dersler = sorted((d for d in veri["dersler"] if d["yol"] in kume), key=lambda d: (YOL_SIRA.get(d["yol"], 9), d["id"]))
    ozel = {d["yol"] for d in dersler} & set(OLCUTLER_YOL)
    kriter = OLCUTLER_YOL[next(iter(ozel))] if len(ozel) == 1 and len(kume) == 1 else OLCUTLER
    kisa = KISA_YOL.get(next(iter(ozel)), KISA) if kriter is not OLCUTLER else KISA
    puanli = [toplam(d) for d in dersler if toplam(d) is not None]
    ort = sum(puanli) / len(puanli) if puanli else 0
    kararlar = {}
    for d in dersler:
        k = d.get("karar") or "Bekliyor"
        kararlar[k] = kararlar.get(k, 0) + 1
    oncelikli = [(d, x) for d in dersler for x in d.get("eksikler") or [] if x.get("oncelik") == "yüksek"]
    yol_ort = []
    for yid, yad in yollar_sayfa:
        xs = [toplam(d) for d in dersler if d["yol"] == yid and toplam(d) is not None]
        yol_ort.append((yad, sum(xs) / len(xs) if xs else None, len(xs)))
    # Ölçüt ortalamaları yalnız sayfanın ölçütünü kullanan derslerden: farklı anlamdaki puanlar karışmasın
    lab = [d for d in dersler if d.get("puan") and olcutler(d) is kriter]
    olcut_ort = "".join(
        f'<div class="asama-ort"><span>{e(ad)}</span><i><b style="width:{(sum(d["puan"].get(k, 0) for d in lab) / len(lab) / en * 100) if lab else 0:.0f}%"></b></i>'
        f'<em>{(sum(d["puan"].get(k, 0) for d in lab) / len(lab)) if lab else 0:.1f}<small> / {en}</small></em></div>'
        for k, ad, en, _ in kriter)
    harfler = {h: sum(1 for t in puanli if not_harfi(t) == h) for h in "ABCDF"}

    simdi = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    sayac = "".join(f'<div class="sayac k-{KARAR_RENK.get(k, "bekliyor")}"><b>{kararlar.get(k, 0)}</b>'
                    f'<span>{k}</span></div>' for k in ("Tam", "Kısmen", "Sorunlu", "Eksik", "Bekliyor"))
    harf_html = "".join(f'<div class="sayac h-{h}" style="--c:currentColor"><b>{n}</b><span>{h}</span></div>' for h, n in harfler.items())
    yollar = "".join(
        f'<div class="asama-ort"><span>{i + 1:02d} · {e(ad)}</span><i><b style="width:{o or 0:.0f}%"></b></i>'
        f'<em>{"—" if o is None else f"{o:.0f}"}<small> · {n} ders</small></em></div>'
        for i, (ad, o, n) in enumerate(yol_ort))
    onc = "".join(f'<li><a href="#{kimlik(d)}">{e(d["id"])}</a>'
                  + (f'<span class="etiket">{e(x["etiket"])}</span>' if x.get("etiket") else "")
                  + f'{e(x["metin"])}</li>' for d, x in oncelikli) or "<li>Yok.</li>"
    olcut_html = "".join(f'<li><b>{e(ad)}</b> <em>{en}</em> — {e(acik)}</li>' for _, ad, en, acik in kriter)
    if kriter is not OLCUTLER:
        olcut_html += '<li class="yol-olcut">Bu yol gerçek donanım ya da lab yerine bilgi ve anlatım üzerinden puanlanır (kullanıcı kararı, 09.11.2026); anahtarlar ve ağırlıklar AI ölçütleriyle aynıdır.</li>'
    filtre_yol = "".join(f'<button data-f-yol="{yid}">{i + 1:02d} {e(yad)}</button>' for i, (yid, yad) in enumerate(yollar_sayfa)) if len(yollar_sayfa) > 1 else ""
    tablo = eksik_tablosu(dersler, kriter, kisa)
    bekleyen = sum(1 for d in dersler if d.get("durum") in ("kapsam-disi", "oz-puan"))
    oz = sum(1 for d in dersler if d.get("durum") == "oz-puan")

    sayfa = f"""<!DOCTYPE html>
<html lang="tr"><head><meta charset="utf-8">
<title>{e(belge_baslik)}</title>
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
.olcum{{color:var(--faint);font:11.5px Consolas,monospace;margin:4px 0}}
.olculer{{display:grid;gap:3px;margin:8px 0}}
.olcu{{display:grid;grid-template-columns:120px 1fr 44px;gap:8px;align-items:center;font-size:11.5px;color:var(--soft)}}
.olcu em{{font-style:normal;text-align:right;font-family:Consolas,monospace;font-size:11px}}
.kart h4{{margin:10px 0 4px;font:600 11px Bahnschrift,sans-serif;letter-spacing:.18em;text-transform:uppercase;color:var(--faint)}}
.kart ul{{margin:0;padding-left:18px;font-size:13px}}.kart li{{margin:3px 0}}
li.o-yüksek::marker{{color:var(--bad)}}li.o-orta::marker{{color:var(--marker)}}li.o-düşük::marker{{color:var(--faint)}}
.etiket{{display:inline-block;font:600 10px/1 Bahnschrift,sans-serif;letter-spacing:.1em;border:1px solid var(--mor);color:var(--mor);padding:2px 5px;margin-right:6px;vertical-align:1px}}
.kapatilanlar{{color:var(--soft)}}.kapatilanlar li::marker{{color:var(--ok)}}
.kart footer{{margin-top:8px;font-size:11px;color:var(--faint)}}
.gizli{{display:none}}
.tablo-ozet{{color:var(--soft);font-size:13px;margin:0 0 8px}}.secim{{display:inline-flex;gap:6px;align-items:center;cursor:pointer;margin:0 0 8px}}
.kaydir{{overflow-x:auto}}.tablo table{{width:100%;border-collapse:collapse;font-size:12.5px}}
.tablo th{{font:600 10.5px Bahnschrift,sans-serif;letter-spacing:.08em;text-transform:uppercase;color:var(--faint);text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);white-space:nowrap;position:sticky;top:0;background:var(--sheet)}}
.tablo th small{{color:var(--faint);font-weight:400;letter-spacing:0}}
.tablo td{{padding:5px 8px;border-top:1px dashed var(--line);white-space:nowrap}}.tablo td.baslik{{white-space:normal;color:var(--soft);min-width:220px}}
.tablo td a{{color:var(--marker);font:700 12.5px Bahnschrift,sans-serif;text-decoration:none}}
.tablo td.sayi,.tablo td.eksi,.tablo td.sifir{{text-align:right;font-family:Consolas,monospace}}.tablo td.eksi{{color:var(--bad)}}.tablo td.sifir{{color:var(--faint)}}
.tablo td.etk{{color:var(--mor);font-size:11.5px}}.tablo tr.a td{{opacity:.6}}.tablo.yalniz-alt tr.a{{display:none}}
.harf-k{{font:700 13px Bahnschrift,sans-serif;border:1px solid currentColor;padding:0 5px}}
@media (max-width:900px){{.ust,.kartlar{{grid-template-columns:1fr}}.ust>div{{border-right:0;border-bottom:1px solid var(--line)}}}}
</style></head><body><div class="sayfa">
<span class="label">{e(ust_label)}</span>
<h1>{baslik}</h1>
<p class="label">Son üretim: {simdi} · {len(puanli)}/{len(dersler)} ders puanlandı · {bekleyen} ders bağımsız denetim bekliyor{f" ({oz} tanesi yazar öz puanlı)" if oz else ""} · 20 saniyede bir yenilenir</p>
<section class="ust">
 <div class="genel"><span class="label">Ortalama puan</span><b>{ort:.0f}<small>/100</small></b><span class="label">not {not_harfi(ort if puanli else None)}</span>
  <div class="sayaclar" style="margin-top:14px">{harf_html}</div></div>
 <div><span class="label">Kararlar</span><div class="sayaclar">{sayac}</div>
  <span class="label" style="display:block;margin-top:16px">Ölçüt ortalamaları</span>{olcut_ort}</div>
 <div><span class="label">Yola göre ortalama</span>{yollar}</div>
</section>
{tablo}
<section class="blok"><h2>Öncelikli eksikler · yol sırasıyla</h2><ul>{onc}</ul></section>
<div class="filtre"><button class="on" data-f-hepsi>Hepsi</button>
 <button data-f-karar="Tam">Tam</button><button data-f-karar="Kısmen">Kısmen</button><button data-f-karar="Sorunlu">Sorunlu</button><button data-f-karar="Eksik">Eksik</button><button data-f-karar="Bekliyor">Bekliyor</button>
 {filtre_yol}</div>
<div class="kartlar">{"".join(kart(d) for d in dersler)}</div>
<section class="blok olcutler"><h2>Puan ölçütleri (100)</h2><ul>{olcut_html}</ul>
<p class="label">Not: A ≥ 90 · B ≥ 75 · C ≥ 60 · D ≥ 40 · F &lt; 40. "Bağımsız denetim bekliyor": dersi denetçinin kendisi yazdı/düzeltti, puan geçicidir.</p></section>
</div>
<script>
const KEY="{anahtar}";
const ALT=document.getElementById("yalniz-alt");
if(ALT){{try{{ALT.checked=sessionStorage.getItem(KEY+"-alt")==="1"}}catch(e){{}}
 const t=()=>{{document.querySelector(".tablo").classList.toggle("yalniz-alt",ALT.checked);try{{sessionStorage.setItem(KEY+"-alt",ALT.checked?"1":"0")}}catch(e){{}}}};
 ALT.addEventListener("change",t);t();}}
function uygula(f){{document.querySelectorAll(".filtre button").forEach(b=>b.classList.toggle("on",
 (f.k&&b.dataset.fKarar===f.k)||(f.y&&b.dataset.fYol===f.y)||(!f.k&&!f.y&&"fHepsi" in b.dataset)));
 document.querySelectorAll(".kart").forEach(k=>k.classList.toggle("gizli",(f.k&&k.dataset.karar!==f.k)||(f.y&&k.dataset.yol!==f.y)));
 try{{sessionStorage.setItem(KEY,JSON.stringify(f))}}catch(e){{}}}}
document.querySelector(".filtre").addEventListener("click",ev=>{{const b=ev.target.closest("button");if(!b)return;
 uygula(b.dataset.fKarar?{{k:b.dataset.fKarar}}:b.dataset.fYol?{{y:b.dataset.fYol}}:{{}})}});
try{{uygula(JSON.parse(sessionStorage.getItem(KEY)||"{{}}"))}}catch(e){{}}
try{{const y=sessionStorage.getItem(KEY+"-y");if(y)scrollTo(0,+y);
addEventListener("scroll",()=>{{try{{sessionStorage.setItem(KEY+"-y",scrollY)}}catch(e){{}}}});}}catch(e){{}}
setTimeout(()=>location.reload(),20000);
</script></body></html>
"""
    with open(cikti, "w", encoding="utf-8", newline="\n") as f:
        f.write(sayfa)
    return cikti, len(puanli), len(dersler)


def uret_kuantum():
    return uret({"kuantum"}, CIKTI_KUANTUM, 'Kuantum Denetim <em>puanları</em>',
                "Pafta · Kuantum dersleri · bilgi ve anlatım ölçütleriyle", "Pafta · Kuantum denetim ve puanlar", "pafta-kuantum-denetim-filtre")


if __name__ == "__main__":
    for yol, p, n in (uret(), uret_kuantum()):
        print(f"OK · {p}/{n} ders puanlandı · {yol}")
