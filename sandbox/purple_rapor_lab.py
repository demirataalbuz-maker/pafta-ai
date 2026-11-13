"""pu20: pentest raporu tezgâhı. pu19'un yerel HTTP + SQLite labından gerçek kanıt üretir; CVSS 3.1, kanıt hash'i ve rapor kararı referansla karşılaştırılır."""
from pathlib import Path
import copy
import hashlib
import json
import math
import re
import shutil

from purple_sqli_lab import YerelSQLiLab

FIXTURE = Path(__file__).resolve().parents[1] / "tracks/purple/fixtures/pu20_rapor"
METRIK = (("AV", {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.2}), ("AC", {"L": 0.77, "H": 0.44}), ("PR", {"N": 0, "L": 0, "H": 0}),
          ("UI", {"N": 0.85, "R": 0.62}), ("S", {"U": 0, "C": 0}), ("C", {"H": 0.56, "L": 0.22, "N": 0}), ("I", {"H": 0.56, "L": 0.22, "N": 0}),
          ("A", {"H": 0.56, "L": 0.22, "N": 0}))
SEVIYE = (("Kritik", 9.0), ("Yüksek", 7.0), ("Orta", 4.0), ("Düşük", 0.1), ("Yok", 0.0))


def hazirla(hedef=None):
    """Eksik dosyaları kopyalar; mevcut öğrenci dosyasına dokunmaz."""
    dest = Path(hedef or Path.cwd()) / "rapor"
    dest.mkdir(parents=True, exist_ok=True)
    for name in ("bulgular.json", "README.md"):
        if not (dest / name).exists():
            shutil.copyfile(FIXTURE / name, dest / name)
    return dest


def _roundup(x):
    i = round(x * 100000)
    return i / 100000.0 if i % 10000 == 0 else (math.floor(i / 10000) + 1) / 10.0


def _seviye(p):
    return next(ad for ad, alt in SEVIYE if p >= alt)


def referans_cvss(vektor):
    if not isinstance(vektor, str) or not vektor.startswith("CVSS:3.1/"):
        raise ValueError("önek")
    parca = vektor[len("CVSS:3.1/"):].split("/")
    if len(parca) != len(METRIK):
        raise ValueError("metrik sayısı")
    d = {}
    for p, (ad, izin) in zip(parca, METRIK):
        k, _, v = p.partition(":")
        if k != ad or v not in izin:
            raise ValueError("metrik " + ad)
        d[k] = v
    deg = {k: dict(METRIK)[k][v] for k, v in d.items()}
    degisti = d["S"] == "C"
    pr = {"N": 0.85, "L": 0.68 if degisti else 0.62, "H": 0.5 if degisti else 0.27}[d["PR"]]
    iss = 1 - (1 - deg["C"]) * (1 - deg["I"]) * (1 - deg["A"])
    etki = 7.52 * (iss - 0.029) - 3.25 * (iss - 0.02) ** 15 if degisti else 6.42 * iss
    istismar = 8.22 * deg["AV"] * deg["AC"] * pr * deg["UI"]
    if etki <= 0:
        puan = 0.0
    else:
        puan = _roundup(min((1.08 if degisti else 1) * (etki + istismar), 10))
    return {"puan": puan, "seviye": _seviye(puan)}


def _ozet(k):
    return hashlib.sha256((k["istek"] + "\n\n" + k["yanit"]).encode("utf-8")).hexdigest()


def referans_kanit(kanitlar, iddialar):
    if not isinstance(kanitlar, list) or not isinstance(iddialar, dict):
        raise ValueError("tür")
    gercek = {}
    for k in kanitlar:
        if not isinstance(k, dict) or set(k) != {"id", "istek", "yanit"}:
            raise ValueError("şema")
        if not isinstance(k["id"], str) or not k["id"] or k["id"] in gercek or not isinstance(k["istek"], str) or not isinstance(k["yanit"], str):
            raise ValueError("alan")
        gercek[k["id"]] = _ozet(k)
    for i, h in iddialar.items():
        if not isinstance(i, str) or not i or not isinstance(h, str) or not re.fullmatch(r"[0-9a-f]{64}", h):
            raise ValueError("iddia")
    return {"dogru": sorted(i for i, h in iddialar.items() if gercek.get(i) == h),
            "uyusmayan": sorted(i for i, h in iddialar.items() if i in gercek and gercek[i] != h),
            "eksik": sorted(i for i in iddialar if i not in gercek),
            "kullanilmayan": sorted(i for i in gercek if i not in iddialar)}


def referans_rapor(bulgular, durum):
    if not isinstance(bulgular, list) or not isinstance(durum, dict) or set(durum) != {"dogru", "uyusmayan", "eksik", "kullanilmayan"}:
        raise ValueError("tür")
    ids = set()
    gecerli, gecersiz = [], []
    for b in bulgular:
        if not isinstance(b, dict) or set(b) != {"id", "baslik", "puan", "kanitlar"}:
            raise ValueError("şema")
        if not isinstance(b["id"], str) or not b["id"] or b["id"] in ids or not isinstance(b["baslik"], str) or not b["baslik"]:
            raise ValueError("alan")
        if type(b["puan"]) not in (int, float) or not 0 <= b["puan"] <= 10:
            raise ValueError("puan")
        if not isinstance(b["kanitlar"], list) or any(not isinstance(k, str) for k in b["kanitlar"]):
            raise ValueError("kanıtlar")
        ids.add(b["id"])
        K = b["kanitlar"]
        neden = ("kanit-yok" if not K else "kanit-eksik" if any(k in durum["eksik"] for k in K)
                 else "kanit-uyusmuyor" if any(k not in durum["dogru"] for k in K) else None)
        if neden:
            gecersiz.append({"id": b["id"], "neden": neden})
        else:
            gecerli.append({"id": b["id"], "baslik": b["baslik"], "puan": b["puan"], "seviye": _seviye(b["puan"])})
    gecerli.sort(key=lambda x: (-x["puan"], x["id"]))
    gecersiz.sort(key=lambda x: x["id"])
    return {"bulgular": gecerli, "dogrulanmamis": gecersiz,
            "sayilar": {ad: sum(x["seviye"] == ad for x in gecerli) for ad, _ in SEVIYE},
            "en_yuksek": gecerli[0]["id"] if gecerli else None}


def kod_koruma(src):
    import ast
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Import) and any(a.name not in ("json", "math", "hashlib", "re") for a in n.names):
            return False
        if isinstance(n, ast.ImportFrom) and not (n.module == "pathlib" and all(a.name == "Path" for a in n.names)
                                                  or n.module == "purple_rapor_lab" and all(a.name == "calistir" for a in n.names)):
            return False
        if isinstance(n, ast.Name) and n.id in ("exec", "eval", "compile", "getattr", "setattr", "globals", "locals", "vars", "__import__", "open"):
            return False
        if isinstance(n, ast.Attribute) and n.attr.startswith("_"):
            return False
        if isinstance(n, ast.Assign) and any(isinstance(x, ast.Attribute) for x in n.targets):
            return False
    return True


def _ham_istek(port, route, data):
    govde = json.dumps(data, ensure_ascii=False)
    return f"POST {route} HTTP/1.1\nHost: 127.0.0.1:{port}\nContent-Type: application/json\n\n{govde}"


def _ham_yanit(y):
    return f"HTTP/1.1 {y['status']}\nContent-Type: application/json\n\n" + json.dumps(y["body"], ensure_ascii=False, sort_keys=True)


BULGULAR = [
    {"id": "F1", "baslik": "SQL injection ile kimlik doğrulama atlatma (/vulnerable/login)", "vektor": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:L/A:N", "kanitlar": ["E2", "E3"]},
    {"id": "F2", "baslik": "SQL hatasının 500 yanıtıyla dışa yansıması", "vektor": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N", "kanitlar": ["E4"]},
    {"id": "F3", "baslik": "Zayıf parola politikası (taslakta iddia, kanıt dosyası eklenmedi)", "vektor": "CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:L/I:N/A:N", "kanitlar": ["E9"]},
    {"id": "F4", "baslik": "Hesap kilitleme yok (taslaktaki kanıt sonradan düzeltilmiş)", "vektor": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N", "kanitlar": ["E1"]},
]
EK_VEKTORLER = ["CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H", "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N",
                "CVSS:3.1/AV:L/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H", "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:C/C:H/I:H/A:H",
                "CVSS:3.1/AV:P/AC:H/PR:H/UI:R/S:U/C:N/I:N/A:N"]


def _markdown(rapor, bulgu_sozluk, kanit_durumu):
    s = ["# Pentest raporu · yerel SQLi laboratuvarı (eğitim)", "", "## Yönetici özeti", ""]
    s.append("Doğrulanmış bulgu: " + str(len(rapor["bulgular"])) + " · " + ", ".join(f"{k}: {v}" for k, v in rapor["sayilar"].items() if v))
    s += ["", "## Bulgular", ""]
    for b in rapor["bulgular"]:
        s += [f"### {b['id']} · {b['baslik']}", f"- CVSS 3.1: {b['puan']} ({b['seviye']}) · `{bulgu_sozluk[b['id']]['vektor']}`",
              "- Kanıt: " + ", ".join(bulgu_sozluk[b["id"]]["kanitlar"]), ""]
    s += ["## Doğrulanmamış iddialar (rapora alınmadı)", ""] + [f"- {x['id']}: {x['neden']}" for x in rapor["dogrulanmamis"]]
    s += ["", "## Kanıt bütünlüğü", "", "```", json.dumps(kanit_durumu, ensure_ascii=False), "```"]
    return "\n".join(s) + "\n"


def calistir(cvss31, kanit_dogrula, rapor_olustur, kabul=False):
    import os, platform, time
    rec = {"kaynak": "gercek", "kabul": False, "pilot": "pu20-rapor", "python": platform.python_version(), "sqlite": __import__("sqlite3").sqlite_version, "cihaz": platform.platform()}
    lab = YerelSQLiLab()
    try:
        with lab:
            rec["address"] = "127.0.0.1"; rec["port"] = lab.port
            normal = {"username": lab.username, "password": lab.password}
            saldiri = {"username": "' OR 1=1 -- ", "password": "yanlis"}
            plan = [("E1", "/secure/login", normal), ("E2", "/vulnerable/login", saldiri), ("E3", "/secure/login", saldiri),
                    ("E4", "/vulnerable/login", {"username": "'", "password": "yanlis"})]
            kanitlar = []
            for eid, route, data in plan:
                y = lab.post(route, data)
                kanitlar.append({"id": eid, "istek": _ham_istek(lab.port, route, data), "yanit": _ham_yanit(y)})
            audit = lab.audit()
            if [a["status"] for a in audit] != [200, 200, 401, 500]:
                raise AssertionError("Gerçek lab beklenen normal/bypass/ret/hata davranışını üretmedi")
        rec["kanitlar"] = kanitlar
        rec["audit"] = audit
        iddia = {k["id"]: _ozet(k) for k in kanitlar}
        duzeltilmis = dict(kanitlar[0], yanit=kanitlar[0]["yanit"].replace("HTTP/1.1 200", "HTTP/1.1 429"))
        iddia["E1"] = _ozet(duzeltilmis)
        iddia["E9"] = hashlib.sha256(b"rapora eklenmemis ekran goruntusu").hexdigest()
        rec["iddialar"] = iddia
        vektorler = [b["vektor"] for b in BULGULAR] + EK_VEKTORLER
        rec["cvss"] = [cvss31(v) for v in vektorler]
        rec["cvss_referans"] = [referans_cvss(v) for v in vektorler]
        rec["kanit_durumu"] = kanit_dogrula(copy.deepcopy(kanitlar), dict(iddia))
        rec["kanit_durumu_referans"] = durum = referans_kanit(kanitlar, iddia)
        girdi = [{"id": b["id"], "baslik": b["baslik"], "puan": referans_cvss(b["vektor"])["puan"], "kanitlar": list(b["kanitlar"])} for b in BULGULAR]
        rec["rapor_girdisi"] = girdi
        rec["rapor"] = rapor_olustur(copy.deepcopy(girdi), copy.deepcopy(durum))
        rec["rapor_referans"] = referans_rapor(girdi, durum)
        if rec["cvss"] != rec["cvss_referans"]:
            raise AssertionError("CVSS 3.1 puanı ya da seviyesi resmî formülden farklı")
        if rec["kanit_durumu"] != durum:
            raise AssertionError("Kanıt bütünlüğü kararı gerçek kanıtlarla uyuşmuyor")
        if rec["rapor"] != rec["rapor_referans"]:
            raise AssertionError("Rapor kararı (bulgu sırası, doğrulanmamış iddialar, sayılar) yanlış")
        rec["kabul"] = bool(kabul)
    except BaseException as e:
        rec["error"] = {"type": type(e).__name__, "msg": str(e)}
        raise
    finally:
        rec["cleanup"] = lab.temizlendi
        if not lab.temizlendi:
            rec["kabul"] = False
        root = Path(__file__).resolve().parents[1]
        d = Path(os.environ.get("PAFTA_DATA", str(root / "data"))) / "purple-kanit"
        d.mkdir(parents=True, exist_ok=True)
        stamp = str(time.time_ns())
        out = d / ("pu20-" + stamp + ".json")
        out.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
        if "rapor_referans" in rec:
            md = d / ("pu20-rapor-" + stamp + ".md")
            md.write_text(_markdown(rec["rapor_referans"], {b["id"]: b for b in BULGULAR}, rec["kanit_durumu_referans"]), encoding="utf-8")
            rec["rapor_dosyasi"] = str(md)
            print("Rapor: " + str(md))
        print("GERÇEK HTTP + SQLite · " + ("kabul edildi" if rec["kabul"] else "kabul yok / deneme") + " · kanıt: " + str(out))
    print(json.dumps({"kanit_durumu": rec["kanit_durumu"], "rapor": {k: v for k, v in rec["rapor"].items() if k != "bulgular"},
                      "sira": [b["id"] for b in rec["rapor"]["bulgular"]]}, ensure_ascii=False))
    return rec
