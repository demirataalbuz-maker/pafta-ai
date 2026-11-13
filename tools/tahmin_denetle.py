# -*- coding: utf-8 -*-
"""Tahmin adımlarının açıklamasını gerçek çıktıyla karşılaştırır.

Her tahmin kodu çalıştırılır; çıktının boş olmayan her satırı, açıklamada
(??? sonrası) ya da soru metninde geçmiyorsa uyarı verilir. Hata beklenen
tahminlerde hata türünün adı aranır.

    python tools/tahmin_denetle.py [ders...]
"""
import os
import sys
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine.lessons import Library  # noqa: E402
from engine.runners import get  # noqa: E402


def normal(s):
    return " ".join(s.replace("`", "").split())


def denetle(is_):
    tid, lid, i, st = is_
    runner = get("python")
    r = runner.run(st["code"], st.get("stdin", ""), st.get("setup"))
    aciklama = st["body"].split("???", 1)[1] if "???" in st["body"] else ""
    metin = normal(aciklama)
    eksik = []
    if r.get("error"):
        if r["error"]["type"] not in aciklama:
            eksik.append(f"hata türü {r['error']['type']} açıklamada yok")
    cikti = "".join(t for k, t in r.get("segs", []) if k == "out")
    for satir in cikti.splitlines():
        if satir.strip() and normal(satir) not in metin:
            eksik.append(repr(satir.strip())[:90])
    return lid, i, st["title"] or "tahmin", eksik, cikti


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    lib = Library()
    isler = []
    for tid in ("python",):
        for lid in lib.outline(tid)["order"]:
            if sys.argv[1:] and lid not in sys.argv[1:]:
                continue
            for i, st in enumerate(lib.lesson(tid, lid)["steps"]):
                if st["kind"] == "tahmin":
                    isler.append((tid, lid, i, st))
    with ThreadPoolExecutor(8) as ex:
        sonuc = list(ex.map(denetle, isler))
    sorunlu = [s for s in sonuc if s[3]]
    print(f"{len(isler)} tahmin, {len(sorunlu)} şüpheli")
    for lid, i, baslik, eksik, cikti in sorunlu:
        print(f"\n✗ {lid}:{i} «{baslik}»")
        print("  gerçek çıktı:", repr(cikti)[:200])
        for e in eksik:
            print("  açıklamada yok:", e)


if __name__ == "__main__":
    main()
