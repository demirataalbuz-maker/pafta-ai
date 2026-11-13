"""Dersleri validate.py ile aynı koşucuyla, ama işleri SIRAYLA çalıştırarak doğrular.

validate.py 8 işi paralel başlatır; yüklü bir makinede 6 saniyelik süre sınırında
rastgele zaman aşımları üretir. Bu araç aynı denetimi tek tek yapar.

kullanım: python -X utf8 tools/ai_seri_dogrula.py <yol> <ders-id> [<ders-id> ...]
Her ders için: tahmin çalışmalı, her görevin çözümü geçmeli, başlangıcı geçmemeli.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.lessons import Library  # noqa: E402
from engine.runners import argv_coz, for_step, get  # noqa: E402

lib = Library()
tid = sys.argv[1]
tr = lib.track(tid)
toplam_sorun = 0
for lid in sys.argv[2:]:
    les = lib.lesson(tid, lid)
    say = {"tahmin": 0, "solution": 0, "starter": 0}
    sorun = []
    for i, st in enumerate(les["steps"]):
        runner = for_step(get(tr["runner"]), st)
        if st["kind"] == "tahmin":
            r = runner.run(st["code"], st.get("stdin", ""), st.get("setup"), argv=argv_coz(st.get("meta")))
            if r.get("status") == "ok":
                say["tahmin"] += 1
            else:
                sorun.append(f"adım {i} tahmin: {r.get('status')} {str(r.get('error'))[:160]}")
        elif st["kind"] == "gorev":
            r = runner.test(st["solution"], st)
            if r.get("status") == "pass":
                say["solution"] += 1
            else:
                kotu = [c for c in r.get("checks", []) if not c["ok"]][:2]
                sorun.append(f"adım {i} çözüm: {r.get('status')} {kotu} {str(r.get('error'))[:160]}")
            r = runner.test(st["starter"], st)
            if r.get("status") in ("fail", "error"):
                say["starter"] += 1
            else:
                sorun.append(f"adım {i} başlangıç: {r.get('status')} (reddedilmeliydi)")
    toplam_sorun += len(sorun)
    print(f"{lid}: {say} {'TEMİZ' if not sorun else 'SORUN'}")
    for s in sorun:
        print("   ", s)
sys.exit(1 if toplam_sorun else 0)
