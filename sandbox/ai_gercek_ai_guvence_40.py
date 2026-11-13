"""Kalibrasyon, ROC ve EER: gerçek prompt-injection verisinde distilbert özellikleri + küçük sınıflayıcı, temperature scaling."""
import copy, importlib.metadata, math, os, random, secrets
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
import ai_lab
from sandbox.ai_gercek_ai_savunma_32 import MODEL, REV, VERI, VERI_REV, _veri

AYAR = {"gizli": 128, "epoch": 400, "lr": 0.002, "dogrulama": 150, "kova": 10, "kova_duyarlilik": [5, 10, 20], "alt": 0.05, "ust": 50.0, "alarm_esik": 0.9, "yigin": 32, "max_uzunluk": 128}


def _sayi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)


def _etiketler(y):
    if not isinstance(y, list) or not y or not all(type(v) is int and v in (0, 1) for v in y):
        raise ValueError("etiket")


def referans_ece(p, y, kova):
    if not isinstance(p, list) or not all(_sayi(v) and 0 <= v <= 1 for v in p):
        raise ValueError("p")
    _etiketler(y)
    if len(p) != len(y) or isinstance(kova, bool) or not isinstance(kova, int) or kova < 1:
        raise ValueError("uzunluk")
    b = {}
    for a, c in zip(p, y):
        b.setdefault(min(int(a * kova), kova - 1), []).append((a, c))
    out, ece, mce = [], 0.0, 0.0
    for i in sorted(b):
        g = sum(a for a, _ in b[i]) / len(b[i])
        d = sum(c for _, c in b[i]) / len(b[i])
        ece += len(b[i]) / len(p) * abs(d - g)
        mce = max(mce, abs(d - g))
        out.append({"kova": i, "adet": len(b[i]), "guven": g, "dogruluk": d})
    return {"ece": ece, "mce": mce, "kovalar": out}


def _nll(z, y, T):
    t = 0.0
    for a, c in zip(z, y):
        u = -a / T if c == 1 else a / T
        t += u if u > 30 else math.log1p(math.exp(u))
    return t / len(z)


def referans_sicaklik(z, y, alt, ust):
    if not isinstance(z, list) or not all(_sayi(v) for v in z):
        raise ValueError("z")
    _etiketler(y)
    if len(z) != len(y) or not _sayi(alt) or not _sayi(ust) or alt <= 0 or alt >= ust:
        raise ValueError("ayar")
    o = (math.sqrt(5) - 1) / 2
    a, b = alt, ust
    c, d = b - o * (b - a), a + o * (b - a)
    fc, fd = _nll(z, y, c), _nll(z, y, d)
    for _ in range(80):
        if fc <= fd:
            b, d, fd = d, c, fc
            c = b - o * (b - a)
            fc = _nll(z, y, c)
        else:
            a, c, fc = c, d, fd
            d = a + o * (b - a)
            fd = _nll(z, y, d)
    T = (a + b) / 2
    return {"T": T, "nll_once": _nll(z, y, 1.0), "nll_sonra": _nll(z, y, T)}


def referans_roc(s, y):
    if not isinstance(s, list) or not all(_sayi(v) for v in s):
        raise ValueError("skor")
    _etiketler(y)
    if len(s) != len(y):
        raise ValueError("uzunluk")
    P = sum(y)
    N = len(y) - P
    if P == 0 or N == 0:
        raise ValueError("sınıf")
    nok = [{"esik": None, "fpr": 0.0, "tpr": 0.0}]
    for e in sorted(set(s), reverse=True):
        tp = sum(1 for a, c in zip(s, y) if a >= e and c == 1)
        fp = sum(1 for a, c in zip(s, y) if a >= e and c == 0)
        nok.append({"esik": e, "fpr": fp / N, "tpr": tp / P})
    auc = sum((n["fpr"] - m["fpr"]) * (n["tpr"] + m["tpr"]) / 2 for m, n in zip(nok, nok[1:]))
    eer = None
    for m, n in zip(nok, nok[1:]):
        d0, d1 = 1 - m["tpr"] - m["fpr"], 1 - n["tpr"] - n["fpr"]
        if d0 > 0 >= d1:
            eer = m["fpr"] + d0 / (d0 - d1) * (n["fpr"] - m["fpr"])
            break
    return {"noktalar": nok, "auc": auc, "eer": eer}


def _yakin(a, b, tol=1e-6):
    if isinstance(a, dict):
        return isinstance(b, dict) and set(a) == set(b) and all(_yakin(a[k], b[k], tol) for k in a)
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(_yakin(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, (bool, str)) or a is None:
        return type(a) is type(b) and a == b
    return _sayi(a) and _sayi(b) and abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def _ozellik(torch, tok, net, metinler, cihaz):
    out = []
    for i in range(0, len(metinler), AYAR["yigin"]):
        g = tok(metinler[i:i + AYAR["yigin"]], padding=True, truncation=True, max_length=AYAR["max_uzunluk"], return_tensors="pt").to(cihaz)
        with torch.no_grad():
            z = net(**g).last_hidden_state
        m = g["attention_mask"].unsqueeze(-1)
        out.append((z * m).sum(1) / m.sum(1))
    return torch.cat(out)


def deney(ece_fn, sicaklik_fn, roc_fn):
    try:
        import torch
        from transformers import AutoModel, AutoTokenizer
        tablo, dosyalar = _veri()
        tok = AutoTokenizer.from_pretrained(MODEL, revision=REV, local_files_only=True)
        cihaz = ai_lab.torch_cihazi()
        net = AutoModel.from_pretrained(MODEL, revision=REV, local_files_only=True).to(cihaz).eval()
    except ai_lab.GercekLabYok:
        raise
    except Exception as e:
        raise ai_lab.GercekLabYok(str(e)) from e
    rng = random.Random(secrets.randbits(64))
    tr = list(tablo["train"])
    rng.shuffle(tr)
    dog, eg, te = tr[:AYAR["dogrulama"]], tr[AYAR["dogrulama"]:], tablo["test"]
    F = {ad: _ozellik(torch, tok, net, [k["metin"] for k in v], cihaz) for ad, v in (("eg", eg), ("dog", dog), ("te", te))}
    Y = {ad: [k["etiket"] for k in v] for ad, v in (("eg", eg), ("dog", dog), ("te", te))}
    del net
    tohum = secrets.randbits(30)
    torch.manual_seed(tohum)
    bas = torch.nn.Sequential(torch.nn.Linear(F["eg"].shape[1], AYAR["gizli"]), torch.nn.ReLU(), torch.nn.Linear(AYAR["gizli"], 1)).to(cihaz)
    opt = torch.optim.Adam(bas.parameters(), lr=AYAR["lr"])
    y_eg = torch.tensor(Y["eg"], dtype=torch.float32, device=cihaz)
    for _ in range(AYAR["epoch"]):
        opt.zero_grad()
        torch.nn.functional.binary_cross_entropy_with_logits(bas(F["eg"]).squeeze(1), y_eg).backward()
        opt.step()
    with torch.no_grad():
        z_d = bas(F["dog"]).squeeze(1).double().tolist()
        z_t = bas(F["te"]).squeeze(1).double().tolist()
    del bas, F
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    sg = lambda v: 1 / (1 + math.exp(-v)) if v > -700 else 0.0
    y_d, y_t = Y["dog"], Y["te"]
    s_o, s_r = sicaklik_fn(list(z_d), list(y_d), AYAR["alt"], AYAR["ust"]), referans_sicaklik(z_d, y_d, AYAR["alt"], AYAR["ust"])
    T = s_r["T"]
    p_once, p_sonra = [sg(v) for v in z_t], [sg(v / T) for v in z_t]
    e = {}
    ece_ayni = True
    for ad, p in (("once", p_once), ("sonra", p_sonra)):
        e[ad] = {}
        for k in AYAR["kova_duyarlilik"]:
            r = referans_ece(p, y_t, k)
            ece_ayni = ece_ayni and _yakin(ece_fn(list(p), list(y_t), k), r)
            e[ad][str(k)] = r
    r_o, r_s = referans_roc(p_once, y_t), referans_roc(p_sonra, y_t)
    o_o, o_s = roc_fn(list(p_once), list(y_t)), roc_fn(list(p_sonra), list(y_t))
    roc_z = referans_roc(z_t, y_t)

    def alarm(p):
        P, N = sum(y_t), len(y_t) - sum(y_t)
        return {"tpr": sum(a >= AYAR["alarm_esik"] and c == 1 for a, c in zip(p, y_t)) / P, "fpr": sum(a >= AYAR["alarm_esik"] and c == 0 for a, c in zip(p, y_t)) / N}
    k = str(AYAR["kova"])
    return {"model": MODEL, "revizyon": REV, "veri": VERI, "veri_revizyon": VERI_REV, "cihaz": str(cihaz), "surumler": {x: importlib.metadata.version(x) for x in ("torch", "transformers")}, "ayarlar": AYAR, "boyut": {"egitim": len(eg), "dogrulama": len(dog), "test": len(te)},
            "sicaklik": s_r, "sicaklik_ayni": _yakin(s_o, s_r, 1e-3), "sicaklik_cozum_nll": _nll(z_d, y_d, s_o["T"]) if _sayi(s_o.get("T")) and s_o["T"] > 0 else None, "ece_ayni": ece_ayni, "ece_ozet": {"once": e["once"][k]["ece"], "sonra": e["sonra"][k]["ece"]}, "ece_kova_duyarlilik": {a: {b: v["ece"] for b, v in e[a].items()} for a in e}, "kovalar_once": e["once"][k]["kovalar"], "kovalar_sonra": e["sonra"][k]["kovalar"],
            "roc_ayni": _yakin(o_o, r_o) and _yakin(o_s, r_s), "auc": {"once": r_o["auc"], "sonra": r_s["auc"], "logit": roc_z["auc"]}, "eer": {"once": r_o["eer"], "sonra": r_s["eer"], "logit": roc_z["eer"]}, "alarm": {"once": alarm(p_once), "sonra": alarm(p_sonra)},
            "olcum": "Sıcaklık yalnız doğrulama kümesinde seçilir; ECE, AUC ve EER ayrı test kümesinde ölçülür. Özellikler distilbert ortalama-havuzdur, baş her koşuda yeniden eğitilir.",
            "sinir": "Küçük tek veri seti (116 test örneği), tek baş model; dağılım kayması, adaptif saldırgan veya gerçek trafikte alarm oranı hakkında bilgi vermez."}


def goster(ece_fn, sicaklik_fn, roc_fn):
    r = deney(ece_fn, sicaklik_fn, roc_fn)
    print("Model", r["model"], r["revizyon"][:8], "| veri", r["veri"], r["veri_revizyon"][:8], r["boyut"], "|", r["cihaz"])
    print("Seçilen T=%.3f | doğrulama NLL %.4f → %.4f" % (r["sicaklik"]["T"], r["sicaklik"]["nll_once"], r["sicaklik"]["nll_sonra"]))
    print("Test ECE (10 kova) önce=%.4f sonra=%.4f | kova duyarlılığı %s" % (r["ece_ozet"]["once"], r["ece_ozet"]["sonra"], r["ece_kova_duyarlilik"]))
    print("AUC önce=%.4f sonra=%.4f | EER önce=%.4f sonra=%.4f" % (r["auc"]["once"], r["auc"]["sonra"], r["eer"]["once"], r["eer"]["sonra"]))
    print("p>=%.2f alarmı: önce %s | sonra %s" % (AYAR["alarm_esik"], r["alarm"]["once"], r["alarm"]["sonra"]))
    print("Sınır:", r["sinir"])
    print("Kanıt:", ai_lab.kanit_yaz("ai-guvence-40-run", {"kaynak": "gercek", "kabul": False, "ders": "ai-guvence-40", "deney": r}))
