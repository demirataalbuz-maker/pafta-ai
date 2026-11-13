"""Dual norm ve Taylor: gerçek MLP'de birinci/ikinci derece loss tahmini (float64, CPU, sklearn digits)."""
import copy, importlib.metadata, math, random, secrets
import ai_lab

AYAR = {"seed": 35, "gizli": 48, "adim": 500, "lr": 0.01, "ornek": 48, "gradcheck_ornek": 6, "h": 1e-5, "tol_grad": 1e-6,
        "tol_taylor": 0.10, "rastgele_yon": 200, "eps": [0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.4, 0.8],
        "normlar": ["linf", "l2", "l1"], "rastgele_eps": 0.05}


def _sayi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)


def referans_denetle(f, x, analitik, h, tol):
    if not isinstance(x, list) or not x or not isinstance(analitik, list) or len(analitik) != len(x):
        raise ValueError("boyut")
    if not all(_sayi(v) for v in x + analitik) or not _sayi(h) or not _sayi(tol) or h <= 0 or tol <= 0:
        raise ValueError("sayı")
    sayisal, hata = [], 0.0
    for i in range(len(x)):
        a, b = list(x), list(x)
        a[i] += h
        b[i] -= h
        n = (f(a) - f(b)) / (2 * h)
        sayisal.append(n)
        hata = max(hata, abs(n - analitik[i]) / max(1.0, abs(n), abs(analitik[i])))
    return {"sayisal": sayisal, "maks_goreli_hata": hata, "gecti": hata <= tol}


def referans_bozuntu(g, eps, norm):
    if not isinstance(g, list) or not g or not all(_sayi(v) for v in g) or not _sayi(eps) or eps <= 0 or norm not in ("linf", "l2", "l1"):
        raise ValueError("girdi")
    if norm == "linf":
        return {"delta": [eps * (1.0 if v > 0 else -1.0 if v < 0 else 0.0) for v in g], "tahmini_artis": eps * sum(abs(v) for v in g)}
    if norm == "l2":
        n = math.sqrt(sum(v * v for v in g))
        return {"delta": [eps * v / n for v in g] if n > 0 else [0.0] * len(g), "tahmini_artis": eps * n}
    i = max(range(len(g)), key=lambda j: abs(g[j]))
    d = [0.0] * len(g)
    if g[i] != 0:
        d[i] = eps if g[i] > 0 else -eps
    return {"delta": d, "tahmini_artis": eps * abs(g[i])}


def referans_taylor(satirlar, tol):
    if not _sayi(tol) or tol <= 0 or not isinstance(satirlar, list) or not satirlar:
        raise ValueError("girdi")
    gorulen, out, kopma, gecerli = set(), [], None, None
    for s in satirlar:
        if not isinstance(s, dict) or set(s) != {"eps", "tahmin", "gercek"} or not all(_sayi(s[k]) for k in s) or s["eps"] <= 0 or s["eps"] in gorulen:
            raise ValueError("satır")
        gorulen.add(s["eps"])
    for s in sorted(satirlar, key=lambda k: k["eps"]):
        e = abs(s["tahmin"] - s["gercek"]) / max(abs(s["gercek"]), 1e-12)
        out.append({"eps": s["eps"], "goreli_hata": e})
        if kopma is None:
            if e > tol:
                kopma = s["eps"]
            else:
                gecerli = s["eps"]
    return {"satirlar": out, "gecerli_eps": gecerli, "kopma_eps": kopma}


def _yakin(a, b, tol=1e-9):
    if isinstance(a, dict):
        return isinstance(b, dict) and set(a) == set(b) and all(_yakin(a[k], b[k], tol) for k in a)
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(_yakin(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, bool) or a is None or isinstance(a, str):
        return type(a) is type(b) and a == b
    return _sayi(a) and _sayi(b) and abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def _model():
    try:
        import torch
        from sklearn.datasets import load_digits
    except ImportError as e:
        raise ai_lab.GercekLabYok(str(e)) from e
    torch.set_num_threads(4)
    torch.manual_seed(AYAR["seed"])
    veri = load_digits()
    X = torch.tensor(veri.data / 16.0, dtype=torch.float64)
    Y = torch.tensor(veri.target, dtype=torch.long)
    perm = torch.randperm(len(X), generator=torch.Generator().manual_seed(AYAR["seed"]))
    tr, te = perm[:1300], perm[1300:]
    net = torch.nn.Sequential(torch.nn.Linear(64, AYAR["gizli"]), torch.nn.GELU(), torch.nn.Linear(AYAR["gizli"], 10)).double()
    opt = torch.optim.Adam(net.parameters(), lr=AYAR["lr"])
    for _ in range(AYAR["adim"]):
        opt.zero_grad()
        torch.nn.functional.cross_entropy(net(X[tr]), Y[tr]).backward()
        opt.step()
    for p in net.parameters():
        p.requires_grad_(False)
    with torch.no_grad():
        tahmin = net(X[te]).argmax(1)
    return torch, net, X[te], Y[te], float((tahmin == Y[te]).double().mean())


def deney(denetle_fn, bozuntu_fn, taylor_fn):
    torch, net, X, Y, dogruluk = _model()
    with torch.no_grad():
        dogru = (net(X).argmax(1) == Y).nonzero().flatten().tolist()
    rng = random.Random(secrets.randbits(64))
    secim = rng.sample(dogru, AYAR["ornek"])

    def loss_t(x, y):
        return torch.nn.functional.cross_entropy(net(x.unsqueeze(0)), y.unsqueeze(0))

    def loss(v, y):
        with torch.no_grad():
            return float(loss_t(torch.tensor(v, dtype=torch.float64), y))

    def grad(x, y):
        x = x.clone().requires_grad_(True)
        return torch.autograd.grad(loss_t(x, y), x)[0].detach()

    denetim_ayni, grad_kayit = True, []
    for i in secim[: AYAR["gradcheck_ornek"]]:
        y = Y[i]
        x, g = X[i].tolist(), grad(X[i], y).tolist()
        f = lambda v, y=y: loss(v, y)
        o = denetle_fn(f, list(x), list(g), AYAR["h"], AYAR["tol_grad"])
        rf = referans_denetle(f, x, g, AYAR["h"], AYAR["tol_grad"])
        denetim_ayni = denetim_ayni and _yakin(o, rf)
        grad_kayit.append({"ornek": i, "maks_goreli_hata": rf["maks_goreli_hata"], "gecti": rf["gecti"]})

    bozuntu_ayni, norm_ihlali = True, 0
    tablolar, raporlar, raporlar_ref = {}, {}, {}
    gradlar = {i: grad(X[i], Y[i]) for i in secim}
    for norm in AYAR["normlar"]:
        satir_o, satir_r, satir_iki = [], [], []
        for eps in AYAR["eps"]:
            t_o = g_o = t_r = g_r = iki = 0.0
            for i in secim:
                g = gradlar[i]
                liste = g.tolist()
                o = bozuntu_fn(list(liste), eps, norm)
                rf = referans_bozuntu(liste, eps, norm)
                bozuntu_ayni = bozuntu_ayni and _yakin(o, rf)
                d_r = torch.tensor(rf["delta"], dtype=torch.float64)
                olcum = {"linf": d_r.abs().max(), "l2": d_r.norm(), "l1": d_r.abs().sum()}[norm]
                if float(olcum) > eps * (1 + 1e-9):
                    norm_ihlali += 1
                taban = float(loss_t(X[i], Y[i]))
                g_r_i = float(loss_t(X[i] + d_r, Y[i])) - taban
                t_r += rf["tahmini_artis"]
                g_r += g_r_i
                if _yakin(o, rf):
                    t_o += o["tahmini_artis"]
                    g_o += g_r_i
                x_h = X[i].clone().requires_grad_(True)
                g_h = torch.autograd.grad(loss_t(x_h, Y[i]), x_h, create_graph=True)[0]
                hv = torch.autograd.grad((g_h * d_r).sum(), x_h)[0]
                iki += rf["tahmini_artis"] + 0.5 * float((d_r * hv).sum())
            n = len(secim)
            satir_o.append({"eps": eps, "tahmin": t_o / n, "gercek": g_o / n})
            satir_r.append({"eps": eps, "tahmin": t_r / n, "gercek": g_r / n})
            satir_iki.append({"eps": eps, "ikinci_derece": iki / n, "gercek": g_r / n})
        tablolar[norm] = {"birinci": satir_r, "ikinci": satir_iki}
        raporlar[norm] = taylor_fn(copy.deepcopy(satir_o), AYAR["tol_taylor"])
        raporlar_ref[norm] = referans_taylor(satir_r, AYAR["tol_taylor"])

    eps = AYAR["rastgele_eps"]
    dual_ihlali, fgsm_t, rast_t = 0, 0.0, 0.0
    gen = torch.Generator().manual_seed(secrets.randbits(32))
    for i in secim:
        g = gradlar[i]
        fg = eps * torch.sign(g)
        taban = float(loss_t(X[i], Y[i]))
        fgsm_t += float(loss_t(X[i] + fg, Y[i])) - taban
        r = eps * (2 * torch.randint(0, 2, (AYAR["rastgele_yon"], g.numel()), generator=gen).double() - 1)
        if float((r @ g).max()) > eps * float(g.abs().sum()) * (1 + 1e-9):
            dual_ihlali += 1
        rast_t += max(float(loss_t(X[i] + v, Y[i])) for v in r[:32]) - taban
    return {"cihaz": "cpu", "dtype": "float64", "surumler": {x: importlib.metadata.version(x) for x in ("torch", "scikit-learn")},
            "veri": "sklearn load_digits (kütüphaneyle gelen gerçek veri, indirme yok)", "ayarlar": AYAR, "dogruluk": dogruluk, "secim": secim,
            "gradcheck": grad_kayit, "gradcheck_maks": max(k["maks_goreli_hata"] for k in grad_kayit), "denetim_ayni": denetim_ayni, "bozuntu_ayni": bozuntu_ayni,
            "norm_ihlali": norm_ihlali, "dual_ihlali": dual_ihlali, "tablolar": tablolar, "taylor": raporlar, "taylor_referans": raporlar_ref,
            "taylor_ayni": _yakin(raporlar, raporlar_ref), "fgsm_ort_artis": fgsm_t / len(secim), "rastgele32_en_iyi_ort_artis": rast_t / len(secim),
            "olcum": "Tahmin: g·δ. Gerçek: aynı δ ile loss farkı. İkinci derece: g·δ + ½δᵀHδ (Hessian-vector product). Değerler 48 örneğin ortalamasıdır.",
            "sinir": "Tek küçük MLP, tek veri kümesi, [0,1] kutusu uygulanmadı; ReLU ve ölçek farklı modellerde kopma noktası değişir."}


def goster(denetle_fn, bozuntu_fn, taylor_fn):
    r = deney(denetle_fn, bozuntu_fn, taylor_fn)
    print("Model: 64-48-10 GELU, float64 CPU, test doğruluğu %.3f" % r["dogruluk"])
    print("Autograd / merkezi fark en büyük göreli hata: %.2e" % r["gradcheck_maks"])
    for n in AYAR["normlar"]:
        print("Norm", n, "| Senin raporun: geçerli eps", r["taylor"][n]["gecerli_eps"], "kopma eps", r["taylor"][n]["kopma_eps"])
        for a, b in zip(r["tablolar"][n]["birinci"], r["tablolar"][n]["ikinci"]):
            print("  eps=%-6g birinci=%.4f ikinci=%.4f gerçek=%.4f" % (a["eps"], a["tahmin"], b["ikinci_derece"], a["gercek"]))
    print("eps=%.2f FGSM ort. artış %.4f | 32 rastgele işaret yönünün en iyisi %.4f" % (AYAR["rastgele_eps"], r["fgsm_ort_artis"], r["rastgele32_en_iyi_ort_artis"]))
    print("Sınır:", r["sinir"])
    print("Kanıt:", ai_lab.kanit_yaz("ai-guvence-35-run", {"kaynak": "gercek", "kabul": False, "ders": "ai-guvence-35", "deney": r}))
