# -*- coding: utf-8 -*-
"""Ders doğrulayıcı (bütün aktif yollar).

Her görev için: örnek çözüm testleri GEÇMELİ, başlangıç kodu GEÇMEMELİ.
Her tahmin için: kod çalışmalı ve ??? sonrası bir açıklama olmalı.
Anlatımdaki çalıştırılabilir örnekler hatasız çalışmalı (norun işaretliler hariç).
Derslerin `kazanim:` etiketleri yolun kazanim.json'unda olmalı; dosyanın biçimi denetlenir.

    python tools/validate.py                 # bütün aktif yollar
    python tools/validate.py --yol regex     # tek yol
    python tools/validate.py rx03 rx04       # belirli dersler (her yolda aranır)
"""
import json
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine.lessons import Library  # noqa: E402
from engine.runners import argv_coz, for_step, get  # noqa: E402

FENCE = {"python": "python|py", "bash": "bash|sh", "powershell": "powershell|ps1?", "regex": "regex", "sql": "sql", "kql": "kql|kusto", "spl": "spl|splunk", "javascript": "javascript|js", "sigma": "sigma", "yara": "yara", "cmd": "cmd|batch|bat", "packets": "wireshark|bpf|packets|tshark|tcpdump-lab", "ad": "ad|ldap|python|py", "elastic": "kibana|lucene|eql|esql|ingest|rule"}


def kod_deseni(dil):
    return re.compile(r"```(" + FENCE.get(dil, dil) + r")\b([^\n]*)\n(.*?)```", re.S)


def strip_anno(src):
    out = []
    for line in src.split("\n"):
        m = re.search(r"(^|\s)#!(?!/)\s?(.*)$", line)
        if m:
            code = line[:m.start()].rstrip()
            if not code.strip():
                continue
            line = code
        out.append(line)
    return "\n".join(out)


def regex_parcala(src):
    satirlar = src.split("\n")
    for i, s in enumerate(satirlar):
        if s.strip() == "---":
            return "\n".join(satirlar[:i]), "\n".join(satirlar[i + 1:])
    return src, ""


def jobs_for(lib, tid, dil, lid):
    les = lib.lesson(tid, lid)
    if les is None:
        return [("EKSİK", tid, f"{tid}/{lid}", None, None)]
    jobs = []
    if not les["steps"]:
        jobs.append(("BOŞ", tid, lid, None, None))
    for i, st in enumerate(les["steps"]):
        where = f"{tid}/{lid}:{i} {st['kind']} «{st['title'][:40]}»"
        if st["kind"] == "gorev":
            if not st.get("test"):
                jobs.append(("TESTSİZ", tid, where, None, None))
                continue
            if dil in ("sigma", "yara", "elastic") and not st.get("stdin", "").strip()                     and not (st.get("meta") or {}).get("motor"):        # gerçek hedef adımı: veri hazırlıkta
                jobs.append(("GİRDİSİZ", tid, where, None, None))
            if not st.get("solution"):
                jobs.append(("ÇÖZÜMSÜZ", tid, where, None, None))
            else:
                jobs.append(("solution", tid, where, st, st["solution"]))
            jobs.append(("starter", tid, where, st, st.get("starter", "")))
        elif st["kind"] == "tahmin":
            if "???" not in st["body"]:
                jobs.append(("AÇIKLAMASIZ", tid, where, None, None))
            jobs.append(("tahmin", tid, where, st, st["code"]))
        else:
            ornek_dil = (st.get("meta") or {}).get("dil", dil) if tid in ("ad", "yara") else dil
            for m in kod_deseni(ornek_dil).finditer(st["body"]):
                if "norun" in m.group(2):
                    continue
                kod = m.group(3)
                if dil == "regex":
                    desen, metin = regex_parcala(kod)
                    jobs.append(("ornek", tid, where, dict(st, stdin=metin), desen))
                else:
                    ornek_stdin = st.get("stdin", "")
                    if not ornek_stdin and dil in ("sigma", "yara", "elastic"):
                        ornek_stdin = next((s.get("stdin", "") for s in les["steps"] if s.get("stdin")), "")
                    if dil == "elastic" and ornek_stdin:
                        corpus = json.loads(ornek_stdin)
                        corpus["dil"] = m.group(1)
                        ornek_stdin = json.dumps(corpus, ensure_ascii=False)
                    jobs.append(("ornek", tid, where, dict(st, stdin=ornek_stdin), strip_anno(kod)))
    return jobs


def kazanim_denetle(lib, tid):
    """kazanim.json'un biçimi ve derslerdeki `kazanim:` etiketleri: (sorunlar, özet satırı)."""
    try:
        k = lib.kazanim(tid)
    except (ValueError, KeyError, TypeError) as e:
        return [(False, "KAZANIM DOSYASI BOZUK", f"{tid}/kazanim.json", str(e))], ""
    sorun = []

    def bildir(neden):
        sorun.append((False, "KAZANIM ŞEMASI", f"{tid}/kazanim.json", neden))

    kimlikler = set()
    for s in k["sertifikalar"]:
        sid = s.get("id", "")
        if not sid or " " in sid or sid in kimlikler:
            bildir(f"sertifika kimliği boş, boşluklu ya da yinelenmiş: {sid!r}")
        kimlikler.add(sid)
        if not s.get("ad") or not s.get("bolumler"):
            bildir(f"{sid}: ad ya da bolumler yok")
        kodlar = set()
        for b in s.get("bolumler", []):
            if not b.get("kod") or not b.get("baslik"):
                bildir(f"{sid}: kodu ya da başlığı olmayan bölüm")
            if "agirlik" in b and (not isinstance(b["agirlik"], (int, float)) or b["agirlik"] <= 0):
                bildir(f"{sid} {b.get('kod')}: ağırlık pozitif bir sayı olmalı")
            for m in b.get("maddeler", []):
                kod = m.get("kod", "")
                if not kod or " " in kod or kod in kodlar or not m.get("baslik"):
                    bildir(f"{sid}: madde kodu boş, boşluklu, yinelenmiş ya da başlıksız: {kod!r}")
                kodlar.add(kod)
    for b in k["bilinmeyen"]:
        sorun.append((False, "BİLİNMEYEN KAZANIM", f"{tid}/{b['ders']}", f"{b['etiket']!r} {tid}/kazanim.json'da yok"))
    parcalar = []
    for s in k["sertifikalar"]:
        maddeler = [m for b in s.get("bolumler", []) for m in b.get("maddeler", [])]
        parcalar.append(f"{s.get('id')} {sum(1 for m in maddeler if m.get('dersler'))}/{len(maddeler)}")
    return sorun, (f"{tid}: " + " · ".join(parcalar)) if parcalar else ""


RUNNER_ADI = {}


def run_job(job):
    kind, tid, where, st, code = job
    runner = get(RUNNER_ADI[tid])
    if st is None:
        return (False, kind, where, "")
    try:
        runner = for_step(runner, st)
    except ValueError as e:
        return (False, "KOŞUCU AYARI", where, str(e))
    if kind == "solution":
        r = runner.test(code, st)
        if r.get("status") != "pass":
            fails = [c for c in r.get("checks", []) if not c["ok"]]
            return (False, "ÇÖZÜM GEÇMEDİ", where, f"{r.get('status')} {fails[:2]} {r.get('error')}")
        return (True, kind, where, "")
    if kind == "starter":
        r = runner.test(code, st)
        if r.get("status") == "pass":
            return (False, "BAŞLANGIÇ GEÇİYOR", where, "")
        if r.get("status") == "internal":
            return (False, "İÇ HATA", where, r.get("detail", "")[-400:])
        return (True, kind, where, "")
    if kind == "tahmin" and st.get("gercek") is not None:
        return (True, kind, where, "")          # çalıştırılamayan dil: gerçek çıktıyı ders yazarı verdi
    if kind in ("tahmin", "ornek"):
        r = runner.run(code, st.get("stdin", ""), st.get("setup"), argv=argv_coz(st.get("meta")))
        if r.get("status") not in ("ok", "error"):
            return (False, f"{kind.upper()} {r.get('status')}", where, str(r.get("error"))[:300])
        if r.get("status") == "error" and kind == "ornek":
            return (False, "ÖRNEK HATA VERİYOR", where, f"{r['error']['type']}: {r['error']['msg']} | {code[:80]!r}")
        if kind == "ornek" and tid in ("sigma", "yara") and not r.get("segs"):
            return (False, "ÖRNEK EŞLEŞMİYOR", where, f"Örnek kural örnek girdiyle eşleşmedi: {code[:80]!r}")
        if r.get("status") == "error" and kind == "tahmin" and "hata" not in st["body"].lower():
            return (False, "TAHMİN HATA VERİYOR (bilerek mi?)", where, f"{r['error']['type']}: {r['error']['msg']}")
        return (True, kind, where, "")
    return (False, kind, where, "")


def run_jobs(jobs):
    """Light checks stay parallel; real AI models share one slot in this run.

    This only schedules checks. It does not change their assertions or status.
    """
    ai_slot = threading.Lock()

    def scheduled(job):
        step = job[3] or {}
        if (step.get("meta") or {}).get("motor") == "ai-gercek":
            with ai_slot:
                return run_job(job)
        return run_job(job)

    with ThreadPoolExecutor(max_workers=8) as ex:
        return list(ex.map(scheduled, jobs))


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    args = sys.argv[1:]
    sadece_yol = None
    if "--yol" in args:
        i = args.index("--yol")
        sadece_yol = args[i + 1]
        args = args[:i] + args[i + 2:]
    wanted = set(args)
    lib = Library()
    jobs, toplam_ders, eksikler = [], 0, []
    for track in lib.tracks():
        tid = track["id"]
        if track.get("status") != "active" or (sadece_yol and tid != sadece_yol):
            continue
        RUNNER_ADI[tid] = track.get("runner", tid)
        dil = track.get("dil", tid)
        outline = lib.outline(tid)
        order = [l for l in outline["order"] if not wanted or l in wanted]
        toplam_ders += len(order)
        eksikler += [f"{tid}/{l['id']}" for m in outline["modules"] for l in m["lessons"] if l.get("missing")]
        for lid in order:
            jobs.extend(jobs_for(lib, tid, dil, lid))
    results = run_jobs(jobs)
    bad = [r for r in results if not r[0]]
    kz_ozet = []
    if not wanted:
        for track in lib.tracks():
            if track.get("status") == "active" and (not sadece_yol or track["id"] == sadece_yol):
                sorun, satir = kazanim_denetle(lib, track["id"])
                bad += sorun
                if satir:
                    kz_ozet.append(satir)
    counts = {}
    for _, kind, _, _ in [r for r in results if r[0]]:
        counts[kind] = counts.get(kind, 0) + 1
    print(f"{toplam_ders} ders, {len(jobs)} kontrol · geçen: {counts}")
    if eksikler and not wanted:
        print(f"Yazılmamış dersler ({len(eksikler)}): {' '.join(eksikler)}")
    if kz_ozet:
        print("Kazanım (dersi olan madde / bütün maddeler): " + " | ".join(kz_ozet))
    for _, kind, where, detail in bad:
        print(f"  ✗ {kind:<22} {where}  {detail}")
    print("TEMİZ" if not bad else f"{len(bad)} SORUN")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
