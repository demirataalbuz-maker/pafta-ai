"""pu25: istihbarattan plana tezgâhı. CTID adversary_emulation_library APT29 öykünme planını (.deps, sabit commit,
hash'i doğrulanmış) güvenli YAML okuyucusuyla okur; öğrencinin işlevleriyle adımları normalize eder, ATT&CK 19.2
özetine karşı denetler ve yerel telemetriye göre tespit beklentili bir test planı üretir. Hiçbir komut çalıştırılmaz,
plana komut metni kopyalanmaz; yalnız okuma ve karşılaştırma yapılır."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tracks/purple/fixtures/pu25_istihbarat"
PLAN = ROOT / ".deps/ctid-apt29-4467a6ee/APT29.yaml"
PLAN_SHA256 = "644f28185097f545e522ca8ed04b43f19ec8b31ace864d347feb138bc56c1615"
ATTACK = ROOT / "tracks/purple/veri/attack.json"
DURUMLAR = ("planla", "ertele", "kapsam-disi")


def hazirla(hedef=None):
    dest = Path(hedef or Path.cwd()) / "istihbarat"
    dest.mkdir(parents=True, exist_ok=True)
    for name in ("ornekler.json", "telemetri.json", "README.md"):
        if not (dest / name).exists():
            shutil.copyfile(FIXTURE / name, dest / name)
    return dest


# ---------------------------------------------------------------- referanslar
def _adim_anahtari(a):
    out = []
    for p in a.split("."):
        out.append((not p.isdigit(), int(p) if p.isdigit() else p))
    return out


def referans_adimlar(belge):
    if not isinstance(belge, list):
        raise ValueError("belge")
    out = []
    try:
        for x in belge:
            if "technique" not in x:
                continue
            adim = x["procedure_step"]
            if not isinstance(adim, str) or not re.fullmatch(r"\d+(\.[A-Z0-9]+)*", adim):
                raise ValueError("adım: " + repr(adim))
            teknik = x["technique"]["attack_id"]
            if not isinstance(teknik, str) or not re.fullmatch(r"T\d{4}(\.\d{3})?", teknik):
                raise ValueError("teknik: " + repr(teknik))
            out.append({"adim": adim, "teknik": teknik, "ad": x["technique"]["name"], "taktik": x["tactic"],
                        "yurutucu": sorted({e["name"] for e in x.get("executors") or []}),
                        "girdi": sorted(x.get("input_arguments") or {})})
    except (KeyError, TypeError, AttributeError):
        raise ValueError("bozuk plan")
    if len({a["adim"] for a in out}) != len(out):
        raise ValueError("yinelenen adım")
    return sorted(out, key=lambda a: _adim_anahtari(a["adim"]))


def referans_denetim(adimlar, attack):
    try:
        teknik = {t["id"]: t["ad"] for t in attack["teknikler"]}
        emekli, kd = attack["emekli"], set(attack["kullanim_disi"])
        out = {}
        for a in adimlar:
            i, ad = a["teknik"], a["ad"]
            if i in out:
                continue
            kisa = ad.split(": ", 1)[1] if "." in i and ": " in ad else ad
            if i in kd:
                d = {"durum": "kullanim-disi", "guncel_ad": None, "yeni": None}
            elif i in emekli:
                d = {"durum": "emekli", "guncel_ad": teknik.get(emekli[i]), "yeni": emekli[i]}
            elif i not in teknik:
                d = {"durum": "bilinmiyor", "guncel_ad": None, "yeni": None}
            elif teknik[i] != kisa:
                d = {"durum": "yeniden-adlandirildi", "guncel_ad": teknik[i], "yeni": None}
            else:
                d = {"durum": "gecerli", "guncel_ad": teknik[i], "yeni": None}
            out[i] = dict(teknik=i, plan_adi=ad, **d)
    except (KeyError, TypeError, AttributeError):
        raise ValueError("bozuk girdi")
    return [out[k] for k in sorted(out)]


def referans_plan(adimlar, denetim, telemetri, ortam):
    try:
        yeni = {d["teknik"]: d["yeni"] or d["teknik"] for d in denetim}
        dis, coklu = set(ortam["dis_girdiler"]), set(ortam["coklu_makine_girdileri"])
        satirlar, ozet = [], {}
        for a in adimlar:
            t = yeni[a["teknik"]]
            kaynak = telemetri.get(t)
            if kaynak is None:
                kaynak = telemetri.get(t.split(".")[0], [])
            if dis & set(a["girdi"]):
                durum = "kapsam-disi"
            elif coklu & set(a["girdi"]):
                durum = "ertele"
            else:
                durum = "planla"
            satirlar.append({"adim": a["adim"], "teknik": t, "taktik": a["taktik"], "durum": durum,
                             "beklenen": sorted(kaynak), "kor_nokta": not kaynak})
            o = ozet.setdefault(a["taktik"], {d: 0 for d in DURUMLAR} | {"kor_nokta": 0})
            o[durum] += 1
            o["kor_nokta"] += not kaynak
    except (KeyError, TypeError, AttributeError):
        raise ValueError("bozuk girdi")
    return {"satirlar": satirlar, "ozet": {k: ozet[k] for k in sorted(ozet)}}


def kod_koruma(src):
    import ast
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Import) and any(a.name not in ("json", "re") for a in n.names):
            return False
        if isinstance(n, ast.ImportFrom) and not (n.module == "pathlib" and all(a.name == "Path" for a in n.names)
                                                  or n.module == "purple_istihbarat_lab" and all(a.name == "calistir" for a in n.names)):
            return False
        if isinstance(n, ast.Name) and n.id in ("exec", "eval", "compile", "getattr", "setattr", "globals", "locals", "vars", "__import__", "open"):
            return False
        if isinstance(n, ast.Attribute) and n.attr.startswith("_"):
            return False
        if isinstance(n, ast.Assign) and any(isinstance(x, ast.Attribute) for x in n.targets):
            return False
    return True


def _yaml_oku(veri):
    sys.path.insert(0, str(ROOT / ".deps"))
    try:
        import yaml
    finally:
        sys.path.pop(0)
    return yaml.safe_load(veri.decode("utf-8")), getattr(yaml, "__version__", "?")


def _komutlar(belge):
    out = []
    for x in belge:
        for e in x.get("executors") or []:
            k = (e.get("command") or "").strip()
            if len(k) >= 12:
                out.append(k)
    return out


def calistir(plan_adimlari, attack_denetle, test_plani, kabul=False):
    import platform
    rec = {"kaynak": "gercek", "kabul": False, "pilot": "pu25-istihbarat", "python": platform.python_version(), "cihaz": platform.platform(),
           "calistirilan_komut": 0}
    try:
        if not PLAN.exists():
            raise RuntimeError("CTID planı bulunamadı (.deps). İndirme yapılmaz; kurulum onayı gerekir.")
        ham = PLAN.read_bytes()
        rec["plan"] = {"dosya": "center-for-threat-informed-defense/adversary_emulation_library@4467a6ee:apt29/Emulation_Plan/yaml/APT29.yaml",
                       "bayt": len(ham), "sha256": hashlib.sha256(ham).hexdigest()}
        if rec["plan"]["sha256"] != PLAN_SHA256:
            raise RuntimeError("CTID planının hash'i onaylanan değerle uyuşmuyor")
        belge, rec["pyyaml"] = _yaml_oku(ham)
        rec["plan"]["ayrinti"] = {k: v for k, v in belge[0]["emulation_plan_details"].items() if k != "adversary_description"}
        attack = json.loads(ATTACK.read_text(encoding="utf-8"))
        rec["attack_surum"] = attack["surum"]
        tel = json.loads((FIXTURE / "telemetri.json").read_text(encoding="utf-8"))
        adim = plan_adimlari(belge)
        if adim != referans_adimlar(belge):
            raise AssertionError("plan_adimlari gerçek planda referanstan farklı")
        den = attack_denetle(adim, attack)
        if den != referans_denetim(adim, attack):
            raise AssertionError("attack_denetle gerçek planda referanstan farklı")
        plan = test_plani(adim, den, tel["telemetri"], tel["ortam"])
        if plan != referans_plan(adim, den, tel["telemetri"], tel["ortam"]):
            raise AssertionError("test_plani gerçek planda referanstan farklı")
        rec["adim_sayisi"] = len(adim)
        rec["ilk_son"] = [adim[0]["adim"], adim[-1]["adim"]]
        rec["denetim"] = den
        rec["denetim_ozet"] = {d: sum(x["durum"] == d for x in den) for d in ("gecerli", "yeniden-adlandirildi", "emekli", "kullanim-disi", "bilinmiyor")}
        rec["test_plani"] = plan
        rec["durum_ozet"] = {d: sum(s["durum"] == d for s in plan["satirlar"]) for d in DURUMLAR}
        rec["kor_nokta"] = sorted({s["teknik"] for s in plan["satirlar"] if s["kor_nokta"]})
        cikti = json.dumps([adim, den, plan], ensure_ascii=False)
        rec["komut_sizintisi"] = sum(k in cikti for k in _komutlar(belge))
        if rec["komut_sizintisi"] or rec["denetim_ozet"]["bilinmiyor"] or len(adim) != 79:
            raise AssertionError("plana komut metni girdi, bilinmeyen teknik var ya da adım sayısı beklenmedik")
        rec["kabul"] = bool(kabul)
    except BaseException as e:
        rec["error"] = {"type": type(e).__name__, "msg": str(e)[:500]}
        raise
    finally:
        rec["cleanup"] = True
        d = Path(os.environ.get("PAFTA_DATA", str(ROOT / "data"))) / "purple-kanit"
        d.mkdir(parents=True, exist_ok=True)
        out = d / ("pu25-" + str(time.time_ns()) + ".json")
        out.write_text(json.dumps(rec, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print("GERÇEK CTID PLANI (APT29) → TEST PLANI · " + ("kabul edildi" if rec["kabul"] else "kabul yok / deneme") + " · kanıt: " + str(out))
    print("plan:", rec["plan"]["bayt"], "bayt · sha256", rec["plan"]["sha256"][:12], "· ATT&CK", rec["attack_surum"], "· adım", rec["adim_sayisi"], rec["ilk_son"])
    print("denetim:", json.dumps(rec["denetim_ozet"]))
    for d in rec["denetim"]:
        if d["durum"] != "gecerli":
            print("  ", d["teknik"], d["durum"], repr(d["plan_adi"]), "→", repr(d["guncel_ad"]))
    print("durum:", json.dumps(rec["durum_ozet"]), "· kör nokta:", rec["kor_nokta"])
    return rec
