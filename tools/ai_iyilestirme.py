# -*- coding: utf-8 -*-
"""AI dersleri iyileştirme kuyruğu: docs/ai-gercek/iyilestirme.json

Puanı A'nın (90) altındaki her ders bir iş emridir. Akış:
    acik → alindi (düzelten) → teslim (düzelten kendi kontrolünü yaptı) → kabul | iade (denetçi)
Düzelten kendi işini denetleyemez. Kurallar: docs/ai-gercek/IYILESTIRME.md

    python -X utf8 tools/ai_iyilestirme.py liste [--dalga 1] [--durum acik] [--kim codex]
    python -X utf8 tools/ai_iyilestirme.py goster ai-guvence-17
    python -X utf8 tools/ai_iyilestirme.py al ai-guvence-17 --kim codex
    python -X utf8 tools/ai_iyilestirme.py teslim ai-guvence-17 --kim codex --not "validate TEMİZ, mutasyon 0/31"
    python -X utf8 tools/ai_iyilestirme.py denetle ai-guvence-17 kabul --kim claude-opus --puan 92 --not "..."
    python -X utf8 tools/ai_iyilestirme.py denetle ai-guvence-17 iade --kim claude-opus --not "kopya sondası hâlâ geçiyor"
"""
import argparse
import datetime
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOSYA = os.path.join(ROOT, "docs", "ai-gercek", "iyilestirme.json")
DURUMLAR = ("acik", "alindi", "teslim", "kabul", "iade")


KILIT = DOSYA + ".lock"


def _kilit_birak():
    try:
        os.remove(KILIT)
    except FileNotFoundError:
        pass


def oku():
    # Eş zamanlı iki ajan oku→yaz yaparsa geç yazan öbürünün kaydını ezer; kilit süreç bitene kadar tutulur.
    import atexit, time
    if not getattr(oku, "kilitli", False):
        while True:
            try:
                os.close(os.open(KILIT, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
                break
            except FileExistsError:
                try:
                    if time.time() - os.path.getmtime(KILIT) > 30:
                        _kilit_birak()
                        continue
                except FileNotFoundError:
                    continue
                time.sleep(0.2)
        oku.kilitli = True
        atexit.register(_kilit_birak)
    with open(DOSYA, encoding="utf-8") as f:
        return json.load(f)


def yaz(veri):
    gecici = DOSYA + ".tmp"
    with open(gecici, "w", encoding="utf-8", newline="\n") as f:
        json.dump(veri, f, ensure_ascii=False, indent=1)
    os.replace(gecici, DOSYA)


def pano(kim, tur, konu, mesaj):
    subprocess.run([sys.executable, "-X", "utf8", os.path.join(ROOT, "tools", "ai_pano.py"), "yaz", "--kim", kim,
                    "--tur", tur, "--konu", konu, "--mesaj", mesaj], cwd=ROOT, capture_output=True)


def bul(veri, ders):
    for e in veri["emirler"]:
        if e["id"] == ders:
            return e
    sys.exit(f"İş emri yok: {ders} (zaten A olabilir)")


def olay(e, kim, ne, notu=""):
    e["gecmis"].append({"zaman": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "kim": kim, "olay": ne, "not": notu})


def main():
    ap = argparse.ArgumentParser(description="AI dersleri iyileştirme kuyruğu")
    alt = ap.add_subparsers(dest="komut", required=True)
    p = alt.add_parser("liste")
    p.add_argument("--dalga", type=int)
    p.add_argument("--durum", choices=DURUMLAR)
    p.add_argument("--kim")
    p = alt.add_parser("goster")
    p.add_argument("ders")
    p = alt.add_parser("al")
    p.add_argument("ders")
    p.add_argument("--kim", required=True)
    p = alt.add_parser("birak")
    p.add_argument("ders")
    p.add_argument("--kim", required=True)
    p = alt.add_parser("teslim")
    p.add_argument("ders")
    p.add_argument("--kim", required=True)
    p.add_argument("--not", dest="notu", required=True, help="kendi kontrolünün çıktısı: validate, tahmin, mutasyon")
    p = alt.add_parser("denetle")
    p.add_argument("ders")
    p.add_argument("karar", choices=("kabul", "iade"))
    p.add_argument("--kim", required=True)
    p.add_argument("--puan", type=int)
    p.add_argument("--not", dest="notu", required=True)
    a = ap.parse_args()
    veri = oku()

    if a.komut == "liste":
        xs = [e for e in veri["emirler"] if (a.dalga is None or e["dalga"] == a.dalga)
              and (a.durum is None or e["durum"] == a.durum) and (a.kim is None or e["kim"] == a.kim)]
        for e in xs:
            print(f"D{e['dalga']}  {e['id']:<20} {e['puan']:>3}→{e['hedef']}  {e['durum']:<7} {e['kim'] or '-':<12} {','.join(e['etiketler'])}")
        sayi = {d: sum(1 for e in veri["emirler"] if e["durum"] == d) for d in DURUMLAR}
        print(f"{len(xs)} gösterildi · " + " · ".join(f"{d} {n}" for d, n in sayi.items()))
        return
    e = bul(veri, a.ders)
    if a.komut == "goster":
        print(json.dumps(e, ensure_ascii=False, indent=1))
        return
    if a.komut == "al":
        if e["durum"] not in ("acik", "iade"):
            sys.exit(f"{a.ders} şu an {e['durum']} ({e['kim']}); alınamaz.")
        if e["durum"] == "iade" and e["kim"] not in (None, a.kim):
            sys.exit(f"{a.ders} iade edildi; önce eski sahibi ({e['kim']}) bırakmalı.")
        e["durum"], e["kim"] = "alindi", a.kim
        olay(e, a.kim, "aldı")
        pano(a.kim, "basladi", a.ders, "İyileştirme emri alındı: " + ", ".join(e["etiketler"]))
    elif a.komut == "birak":
        if e["kim"] != a.kim:
            sys.exit(f"{a.ders} {e['kim']} üzerinde; yalnız sahibi bırakabilir.")
        e["durum"], e["kim"] = "acik", None
        olay(e, a.kim, "bıraktı")
    elif a.komut == "teslim":
        if e["kim"] != a.kim or e["durum"] not in ("alindi", "iade"):
            sys.exit(f"{a.ders} teslim edilemez: durum {e['durum']}, sahibi {e['kim']}.")
        e["durum"] = "teslim"
        olay(e, a.kim, "teslim etti", a.notu)
        pano(a.kim, "bitti", a.ders, "İyileştirme teslim (denetim bekliyor): " + a.notu)
    elif a.komut == "denetle":
        if e["durum"] != "teslim":
            sys.exit(f"{a.ders} denetime hazır değil: durum {e['durum']}.")
        if e["kim"] == a.kim:
            sys.exit("Düzelten kendi işini denetleyemez; başka bir denetçi gerekir.")
        if a.karar == "kabul" and (a.puan is None or a.puan < e["hedef"]):
            sys.exit(f"Kabul için --puan en az {e['hedef']} olmalı; altındaysa iade et.")
        e["durum"], e["denetci"] = a.karar, a.kim
        if a.puan is not None:
            e["son_puan"] = a.puan
        olay(e, a.kim, a.karar, a.notu)
        pano(a.kim, "karar", a.ders, f"Denetim {a.karar}" + (f" ({a.puan})" if a.puan is not None else "") + ": " + a.notu)
    yaz(veri)
    print(f"{a.ders}: {e['durum']} · sahibi {e['kim'] or '-'}")


if __name__ == "__main__":
    main()
