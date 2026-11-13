"""pu21: tatbikat yönetimi tezgâhı. RoE kapısı, pu19 yerel labında gerçek eylemler, kapsam dışı yem dinleyicisi, mavi kural alarmları ve kırmızı/mavi eşleştirme."""
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import copy
import json
import re
import shutil
import threading

from purple_sqli_lab import YerelSQLiLab

FIXTURE = Path(__file__).resolve().parents[1] / "tracks/purple/fixtures/pu21_tatbikat"
NEDENLER = ("kapsam-disi-hedef", "yasak-teknik", "zaman-disi")


def hazirla(hedef=None):
    dest = Path(hedef or Path.cwd()) / "tatbikat"
    dest.mkdir(parents=True, exist_ok=True)
    for name in ("plan.json", "README.md"):
        if not (dest / name).exists():
            shutil.copyfile(FIXTURE / name, dest / name)
    return dest


def _zaman(s):
    if not isinstance(s, str):
        raise ValueError("zaman")
    z = datetime.fromisoformat(s)
    if z.tzinfo is None:
        raise ValueError("saat dilimi")
    return z


def _hedef(s):
    if not isinstance(s, str) or not re.fullmatch(r"[0-9A-Za-z.\-]+:(\d{1,5}|\*)", s):
        raise ValueError("hedef")
    return s.rsplit(":", 1)


def referans_kapsam(eylem, roe):
    if not isinstance(eylem, dict) or set(eylem) != {"id", "hedef", "teknik", "zaman"}:
        raise ValueError("eylem")
    if not isinstance(roe, dict) or set(roe) != {"hedefler", "yasak_teknikler", "baslangic", "bitis"}:
        raise ValueError("roe")
    if not isinstance(eylem["id"], str) or not eylem["id"] or not isinstance(eylem["teknik"], str) or not re.fullmatch(r"T\d{4}(\.\d{3})?", eylem["teknik"]):
        raise ValueError("eylem alanı")
    host, port = _hedef(eylem["hedef"])
    if port == "*":
        raise ValueError("eylem hedefi joker olamaz")
    if not isinstance(roe["hedefler"], list) or not isinstance(roe["yasak_teknikler"], list):
        raise ValueError("roe listesi")
    izin = [_hedef(h) for h in roe["hedefler"]]
    t, b, s = _zaman(eylem["zaman"]), _zaman(roe["baslangic"]), _zaman(roe["bitis"])
    if not any(host == h and p in ("*", port) for h, p in izin):
        neden = "kapsam-disi-hedef"
    elif eylem["teknik"] in roe["yasak_teknikler"] or eylem["teknik"].split(".")[0] in roe["yasak_teknikler"]:
        neden = "yasak-teknik"
    elif not b <= t < s:
        neden = "zaman-disi"
    else:
        neden = None
    return {"karar": "red" if neden else "izinli", "neden": neden}


def _kayit(x, ad):
    if not isinstance(x, dict) or set(x) != {"id", "hedef", "teknik", "zaman"} or not isinstance(x["id"], str) or not x["id"] or not isinstance(x["hedef"], str) or not isinstance(x["teknik"], str):
        raise ValueError(ad)
    return _zaman(x["zaman"])


def referans_eslestir(eylemler, alarmlar, pencere_sn):
    if type(pencere_sn) not in (int, float) or pencere_sn < 0:
        raise ValueError("pencere")
    if not isinstance(eylemler, list) or not isinstance(alarmlar, list):
        raise ValueError("liste")
    ez = {}
    for e in eylemler:
        z = _kayit(e, "eylem")
        if e["id"] in ez:
            raise ValueError("eylem id")
        ez[e["id"]] = z
    az = {}
    for a in alarmlar:
        z = _kayit(a, "alarm")
        if a["id"] in az:
            raise ValueError("alarm id")
        az[a["id"]] = z
    kullanilan = set()
    eslesme = {}
    for e in sorted(eylemler, key=lambda e: (ez[e["id"]], e["id"])):
        aday = sorted((az[a["id"]], a["id"]) for a in alarmlar if a["id"] not in kullanilan and a["teknik"] == e["teknik"] and a["hedef"] == e["hedef"]
                      and timedelta(0) <= az[a["id"]] - ez[e["id"]] <= timedelta(seconds=pencere_sn))
        eslesme[e["id"]] = aday[0][1] if aday else None
        if aday:
            kullanilan.add(aday[0][1])
    return {"eslesme": eslesme, "eslesmeyen_alarm": sorted(a for a in az if a not in kullanilan)}


def referans_ozet(kayitlar):
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("liste")
    ids = set()
    tek = {}
    red = {n: [] for n in NEDENLER}
    for k in kayitlar:
        if not isinstance(k, dict) or set(k) != {"id", "teknik", "karar", "neden", "onlendi", "tespit"}:
            raise ValueError("şema")
        if not isinstance(k["id"], str) or not k["id"] or k["id"] in ids or not isinstance(k["teknik"], str) or not k["teknik"]:
            raise ValueError("alan")
        ids.add(k["id"])
        if k["karar"] == "izinli":
            if k["neden"] is not None or type(k["onlendi"]) is not bool or type(k["tespit"]) is not bool:
                raise ValueError("izinli kayıt")
            t = tek.setdefault(k["teknik"], {"denenen": 0, "onlendi": 0, "tespit": 0, "kacirildi": 0})
            t["denenen"] += 1
            t["onlendi"] += k["onlendi"]
            t["tespit"] += k["tespit"]
            t["kacirildi"] += not k["onlendi"] and not k["tespit"]
        elif k["karar"] == "red":
            if k["neden"] not in NEDENLER or k["onlendi"] is not None or k["tespit"] is not None:
                raise ValueError("red kayıt")
            red[k["neden"]].append(k["id"])
        else:
            raise ValueError("karar")
    denenen = sum(t["denenen"] for t in tek.values())
    return {"teknikler": {t: tek[t] for t in sorted(tek)}, "reddedilen": {n: sorted(v) for n, v in red.items()},
            "tespit_orani": sum(t["tespit"] for t in tek.values()) / denenen if denenen else None,
            "durdur": bool(red["kapsam-disi-hedef"])}


def kod_koruma(src):
    import ast
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Import) and any(a.name not in ("json", "re") for a in n.names):
            return False
        if isinstance(n, ast.ImportFrom) and not (n.module == "pathlib" and all(a.name == "Path" for a in n.names)
                                                  or n.module == "datetime" and all(a.name in ("datetime", "timedelta", "timezone") for a in n.names)
                                                  or n.module == "purple_tatbikat_lab" and all(a.name == "calistir" for a in n.names)):
            return False
        if isinstance(n, ast.Name) and n.id in ("exec", "eval", "compile", "getattr", "setattr", "globals", "locals", "vars", "__import__", "open"):
            return False
        if isinstance(n, ast.Attribute) and n.attr.startswith("_"):
            return False
        if isinstance(n, ast.Assign) and any(isinstance(x, ast.Attribute) for x in n.targets):
            return False
    return True


class _Yem:
    """Kapsam dışı yem dinleyicisi: gelen her bağlantıyı sayar."""
    def __init__(self):
        self.vurus = 0
        yem = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                yem.vurus += 1
                self.send_response(418)
                self.end_headers()
            do_GET = do_POST
        self.srv = HTTPServer(("127.0.0.1", 0), H)
        self.port = self.srv.server_address[1]
        self.th = threading.Thread(target=self.srv.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
        self.th.start()

    def kapat(self):
        self.srv.shutdown()
        self.th.join(timeout=3)
        self.srv.server_close()
        return not self.th.is_alive()


def _iso(z):
    return z.isoformat(timespec="microseconds")


def calistir(kapsam_kontrol, eslestir, tatbikat_ozeti, kabul=False):
    import os, platform, time
    rec = {"kaynak": "gercek", "kabul": False, "pilot": "pu21-tatbikat", "python": platform.python_version(), "cihaz": platform.platform()}
    lab = YerelSQLiLab()
    yem = None
    temiz_yem = False
    try:
        yem = _Yem()
        with lab:
            simdi = datetime.now(timezone.utc)
            H = f"127.0.0.1:{lab.port}"
            roe = {"hedefler": [f"127.0.0.1:{lab.port}"], "yasak_teknikler": ["T1499", "T1485"],
                   "baslangic": _iso(simdi - timedelta(minutes=1)), "bitis": _iso(simdi + timedelta(minutes=30))}
            with lab.baglanti() as db:
                oreilly, op = db.execute("SELECT username,password FROM accounts WHERE username != ?", (lab.username,)).fetchone()
            plan = [("A1", H, "T1078", [("/secure/login", {"username": lab.username, "password": lab.password})]),
                    ("A2", H, "T1190", [("/vulnerable/login", {"username": "' OR 1=1 -- ", "password": "yanlis"})]),
                    ("A3", H, "T1190", [("/secure/login", {"username": "' OR 1=1 -- ", "password": "yanlis"})]),
                    ("A4", H, "T1110.001", [("/secure/login", {"username": lab.username, "password": "deneme" + str(i)}) for i in range(3)]),
                    ("A5", H, "T1499", [("/vulnerable/login", {"username": "x", "password": "y"})] * 50),
                    ("A6", f"127.0.0.1:{yem.port}", "T1190", [("/vulnerable/login", {"username": "' OR 1=1 -- ", "password": "yanlis"})]),
                    ("A7", f"127.0.0.10:{lab.port}", "T1190", [("/vulnerable/login", {"username": "' OR 1=1 -- ", "password": "yanlis"})]),
                    ("A8", H, "T1190", [("/vulnerable/login", {"username": "' OR 1=1 -- ", "password": "yanlis"})]),
                    ("A9", H, "T1078", [("/secure/login", {"username": oreilly, "password": op})])]
            zamanlar = {p[0]: _iso(simdi + timedelta(seconds=i)) for i, p in enumerate(plan)}
            zamanlar["A8"] = _iso(simdi + timedelta(days=1))
            eylemler = [{"id": a, "hedef": h, "teknik": t, "zaman": zamanlar[a]} for a, h, t, _ in plan]
            rec["roe"] = roe
            rec["plan"] = eylemler
            rec["karar"] = [kapsam_kontrol(copy.deepcopy(e), copy.deepcopy(roe)) for e in eylemler]
            rec["karar_referans"] = kref = [referans_kapsam(e, roe) for e in eylemler]
            yurutulen = []
            istek_zaman = []
            for (a, h, t, istekler), k in zip(plan, kref):
                if k["karar"] != "izinli":
                    continue
                bas = datetime.now(timezone.utc)
                durum = []
                for route, data in istekler:
                    durum.append(lab.post(route, data)["status"])
                    istek_zaman.append((a, datetime.now(timezone.utc)))
                yurutulen.append({"id": a, "hedef": h, "teknik": t, "zaman": _iso(bas), "durumlar": durum})
            audit = lab.audit()
        rec["audit"] = audit
        alarmlar = []
        say = {}
        for (a, z), row in zip(istek_zaman, audit):
            if "'" in row["username"]:
                alarmlar.append({"id": f"AL{len(alarmlar) + 1}", "hedef": H, "teknik": "T1190", "zaman": _iso(z), "kural": "kullanici-adinda-tirnak"})
            if row["status"] == 401 and "'" not in row["username"]:
                say[row["username"]] = say.get(row["username"], 0) + 1
                if say[row["username"]] == 3:
                    alarmlar.append({"id": f"AL{len(alarmlar) + 1}", "hedef": H, "teknik": "T1110.001", "zaman": _iso(z), "kural": "ayni-hesaba-3-ret"})
        rec["alarmlar"] = alarmlar
        rec["yurutulen"] = yurutulen
        sade_e = [{k: e[k] for k in ("id", "hedef", "teknik", "zaman")} for e in yurutulen]
        sade_a = [{k: a[k] for k in ("id", "hedef", "teknik", "zaman")} for a in alarmlar]
        rec["eslesme"] = eslestir(copy.deepcopy(sade_e), copy.deepcopy(sade_a), 5)
        rec["eslesme_referans"] = es = referans_eslestir(sade_e, sade_a, 5)
        kay = []
        for e, k in zip(eylemler, kref):
            y = next((x for x in yurutulen if x["id"] == e["id"]), None)
            kay.append({"id": e["id"], "teknik": e["teknik"], "karar": k["karar"], "neden": k["neden"],
                        "onlendi": None if y is None else all(s != 200 for s in y["durumlar"]),
                        "tespit": None if y is None else es["eslesme"][e["id"]] is not None})
        rec["ozet_girdisi"] = kay
        rec["ozet"] = tatbikat_ozeti(copy.deepcopy(kay))
        rec["ozet_referans"] = referans_ozet(kay)
        rec["yem_vurus"] = yem.vurus
        if yem.vurus:
            raise AssertionError("Kapsam dışı yem dinleyicisine trafik gitti")
        if rec["karar"] != kref:
            raise AssertionError("RoE kararı yanlış: kapsam, yasak teknik ya da zaman penceresi")
        if rec["eslesme"] != es:
            raise AssertionError("Kırmızı eylem ile mavi alarm eşleştirmesi yanlış")
        if rec["ozet"] != rec["ozet_referans"]:
            raise AssertionError("Tatbikat özeti yanlış")
        rec["kabul"] = bool(kabul)
    except BaseException as e:
        rec["error"] = {"type": type(e).__name__, "msg": str(e)}
        raise
    finally:
        if yem is not None:
            temiz_yem = yem.kapat()
        rec["cleanup"] = lab.temizlendi and temiz_yem
        if not rec["cleanup"]:
            rec["kabul"] = False
        root = Path(__file__).resolve().parents[1]
        d = Path(os.environ.get("PAFTA_DATA", str(root / "data"))) / "purple-kanit"
        d.mkdir(parents=True, exist_ok=True)
        out = d / ("pu21-" + str(time.time_ns()) + ".json")
        out.write_text(json.dumps(rec, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print("GERÇEK HTTP + SQLite + yem dinleyici · " + ("kabul edildi" if rec["kabul"] else "kabul yok / deneme") + " · kanıt: " + str(out))
    print(json.dumps({"karar": [f"{e['id']}:{k['karar']}/{k['neden']}" for e, k in zip(rec["plan"], rec["karar"])], "yem_vurus": rec["yem_vurus"],
                      "eslesme": rec["eslesme"], "ozet": rec["ozet"]}, ensure_ascii=False))
    return rec
