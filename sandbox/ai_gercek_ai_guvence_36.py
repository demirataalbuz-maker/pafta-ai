"""Projeksiyon ve gradient masking: aynı kararları veren logit ölçekli modelde float32 doygunluğu ölçülür."""
import copy, importlib.metadata, math, random, secrets
import ai_lab

AYAR = {"seed": 36, "gizli": 64, "adim": 400, "lr": 0.01, "ornek": 128, "olcek": 1000.0, "eps": 0.1, "eps_l2": 1.0, "adim_pgd": 40,
        "alfa_oran": 0.25, "tol": 0.02, "sinir": 0.5, "rastgele_tekrar": 8}


def _sayi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)


def referans_projeksiyon(x, x0, eps, norm, alt, ust):
    if not isinstance(x, list) or not isinstance(x0, list) or not x or len(x) != len(x0) or norm not in ("linf", "l2"):
        raise ValueError("girdi")
    if not all(_sayi(v) for v in x + x0 + [eps, alt, ust]) or eps <= 0 or alt >= ust:
        raise ValueError("sayı")
    if norm == "linf":
        y = [min(max(a, b - eps), b + eps) for a, b in zip(x, x0)]
    else:
        d = [a - b for a, b in zip(x, x0)]
        n = math.sqrt(sum(v * v for v in d))
        olcek = eps / n if n > eps else 1.0
        y = [b + olcek * v for b, v in zip(x0, d)]
    return [min(max(v, alt), ust) for v in y]


def referans_kayip(logit, etiket):
    if not isinstance(logit, list) or len(logit) < 2 or not all(_sayi(v) for v in logit):
        raise ValueError("logit")
    if isinstance(etiket, bool) or not isinstance(etiket, int) or not 0 <= etiket < len(logit):
        raise ValueError("etiket")
    m = max(logit)
    p = [math.exp(v - m) for v in logit]
    t = sum(p)
    return {"ce": math.log(t) - (logit[etiket] - m), "marjin": max(v for j, v in enumerate(logit) if j != etiket) - logit[etiket],
            "doygunluk": sum(v / t for j, v in enumerate(p) if j != etiket)}


def referans_tani(r, tol, sinir):
    alan = {"temiz", "fgsm", "pgd_ce", "pgd_marjin", "rastgele", "sifir_grad"}
    if not isinstance(r, dict) or set(r) != alan or not all(_sayi(r[k]) and 0 <= r[k] <= 1 for k in alan):
        raise ValueError("rapor")
    if not _sayi(tol) or tol < 0 or not _sayi(sinir) or not 0 <= sinir <= 1:
        raise ValueError("ayar")
    b = []
    if r["temiz"] - r["pgd_ce"] <= tol:
        b.append("etkisiz")
    if r["pgd_marjin"] + tol < r["pgd_ce"]:
        b.append("kayip_farki")
    if r["rastgele"] + tol < r["pgd_ce"]:
        b.append("rastgele")
    if r["sifir_grad"] > sinir:
        b.append("sifir_grad")
    if r["fgsm"] + tol < r["pgd_ce"]:
        b.append("tek_adim")
    return {"bayraklar": b, "maskeli": bool(b), "en_dusuk_robust": min(r["fgsm"], r["pgd_ce"], r["pgd_marjin"], r["rastgele"])}


def _yakin(a, b, tol=1e-9):
    if isinstance(a, dict):
        return isinstance(b, dict) and set(a) == set(b) and all(_yakin(a[k], b[k], tol) for k in a)
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(_yakin(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, (bool, str)) or a is None:
        return type(a) is type(b) and a == b
    return _sayi(a) and _sayi(b) and abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def _kur():
    try:
        import torch
        from sklearn.datasets import load_digits
    except ImportError as e:
        raise ai_lab.GercekLabYok(str(e)) from e
    cihaz = ai_lab.torch_cihazi()
    torch.manual_seed(AYAR["seed"])
    v = load_digits()
    X = torch.tensor(v.data / 16.0, dtype=torch.float32, device=cihaz)
    Y = torch.tensor(v.target, dtype=torch.long, device=cihaz)
    perm = torch.randperm(len(X), generator=torch.Generator().manual_seed(AYAR["seed"])).to(cihaz)
    tr, te = perm[:1300], perm[1300:]
    net = torch.nn.Sequential(torch.nn.Linear(64, AYAR["gizli"]), torch.nn.ReLU(), torch.nn.Linear(AYAR["gizli"], 10)).to(cihaz)
    opt = torch.optim.Adam(net.parameters(), lr=AYAR["lr"])
    for _ in range(AYAR["adim"]):
        opt.zero_grad()
        torch.nn.functional.cross_entropy(net(X[tr]), Y[tr]).backward()
        opt.step()
    for p in net.parameters():
        p.requires_grad_(False)
    return torch, cihaz, net, X[te], Y[te]


def _kayip_t(torch, z, y, tur):
    if tur == "ce":
        return torch.nn.functional.cross_entropy(z, y, reduction="sum")
    d = z.clone()
    d[torch.arange(len(y)), y] = -1e30
    return (d.max(1).values - z[torch.arange(len(y)), y]).sum()


def _sald(torch, f, X, Y, tur, proj, norm, eps, adim):
    x = X.clone()
    for _ in range(adim):
        x.requires_grad_(True)
        g = torch.autograd.grad(_kayip_t(torch, f(x), Y, tur), x)[0]
        with torch.no_grad():
            if norm == "linf":
                ad = x + AYAR["alfa_oran"] * eps * torch.sign(g)
            else:
                n = g.flatten(1).norm(dim=1, keepdim=True).clamp_min(1e-30)
                ad = x + AYAR["alfa_oran"] * eps * g / n
            yeni = [proj(a, b, eps, norm, 0.0, 1.0) for a, b in zip(ad.tolist(), X.tolist())]
            x = torch.tensor(yeni, dtype=X.dtype, device=X.device)
    return x


def _dogruluk(f, x, Y):
    return float((f(x).argmax(1) == Y).float().mean())


def deney(proj_fn, kayip_fn, tani_fn):
    torch, cihaz, net, X_te, Y_te = _kur()
    with torch.no_grad():
        dogru = (net(X_te).argmax(1) == Y_te).nonzero().flatten().tolist()
    rng = random.Random(secrets.randbits(64))
    secim = rng.sample(dogru, AYAR["ornek"])
    X, Y = X_te[secim], Y_te[secim]
    olcekli = lambda v: net(v) * AYAR["olcek"]
    with torch.no_grad():
        karar_ayni = bool((net(X_te).argmax(1) == olcekli(X_te).argmax(1)).all())

    def rapor(f, proj):
        x = X.clone().requires_grad_(True)
        g = torch.autograd.grad(_kayip_t(torch, f(x), Y, "ce"), x)[0]
        sifir = float((g.flatten(1).abs().sum(1) == 0).float().mean())
        with torch.no_grad():
            fg = (X + AYAR["eps"] * torch.sign(g)).clamp(0, 1)
            ras = 1.0
            gen = torch.Generator(device=X.device).manual_seed(secrets.randbits(32))
            for _ in range(AYAR["rastgele_tekrar"]):
                r = AYAR["eps"] * (2 * torch.randint(0, 2, X.shape, generator=gen, device=X.device).float() - 1)
                ras = min(ras, _dogruluk(f, (X + r).clamp(0, 1), Y))
            sonuc = {"temiz": _dogruluk(f, X, Y), "fgsm": _dogruluk(f, fg, Y), "rastgele": ras, "sifir_grad": sifir}
        adv_ce = _sald(torch, f, X, Y, "ce", proj, "linf", AYAR["eps"], AYAR["adim_pgd"])
        adv_m = _sald(torch, f, X, Y, "marjin", proj, "linf", AYAR["eps"], AYAR["adim_pgd"])
        with torch.no_grad():
            sonuc["pgd_ce"] = _dogruluk(f, adv_ce, Y)
            sonuc["pgd_marjin"] = _dogruluk(f, adv_m, Y)
        return sonuc, adv_m

    taban, adv_taban = rapor(net, proj_fn)
    maskeli, adv_olc = rapor(olcekli, proj_fn)
    adv_l2 = _sald(torch, net, X, Y, "marjin", proj_fn, "l2", AYAR["eps_l2"], AYAR["adim_pgd"])
    with torch.no_grad():
        l2_robust = _dogruluk(net, adv_l2, Y)
        linf_max = max(float((adv_taban - X).abs().max()), float((adv_olc - X).abs().max()))
        l2_max = float((adv_l2 - X).flatten(1).norm(dim=1).max())
        kutu = all(float(v.min()) >= 0 and float(v.max()) <= 1 for v in (adv_taban, adv_olc, adv_l2))
    proj_ayni = True
    for i in range(32):
        a, b = adv_taban[i].tolist(), X[i].tolist()
        a2 = [v + rng.uniform(-0.4, 0.4) for v in a]
        for norm, e in (("linf", AYAR["eps"]), ("l2", AYAR["eps_l2"])):
            proj_ayni = proj_ayni and _yakin(proj_fn(list(a2), list(b), e, norm, 0.0, 1.0), referans_projeksiyon(a2, b, e, norm, 0.0, 1.0))
    kayip_ayni, kayit = True, []
    with torch.no_grad():
        z_t, z_o = net(X).double().tolist(), (net(X) * AYAR["olcek"]).double().tolist()
    for i in range(len(secim)):
        for z in (z_t[i], z_o[i]):
            kayit_r = referans_kayip(z, int(Y[i]))
            kayip_ayni = kayip_ayni and _yakin(kayip_fn(list(z), int(Y[i])), kayit_r)
    for i in range(6):
        kayit.append({"taban": referans_kayip(z_t[i], int(Y[i])), "olcekli": referans_kayip(z_o[i], int(Y[i]))})
    return {"cihaz": str(cihaz), "dtype": "float32", "surumler": {x: importlib.metadata.version(x) for x in ("torch", "scikit-learn")}, "ayarlar": AYAR, "secim": secim,
            "karar_ayni": karar_ayni, "taban": taban, "maskeli": maskeli, "l2_marjin_robust": l2_robust, "linf_max": linf_max, "l2_max": l2_max, "kutu_icinde": kutu,
            "proj_ayni": proj_ayni, "kayip_ayni": kayip_ayni, "kayip_ornekleri": kayit,
            "tani": {"taban": tani_fn(dict(taban), AYAR["tol"], AYAR["sinir"]), "maskeli": tani_fn(dict(maskeli), AYAR["tol"], AYAR["sinir"])},
            "tani_referans": {"taban": referans_tani(taban, AYAR["tol"], AYAR["sinir"]), "maskeli": referans_tani(maskeli, AYAR["tol"], AYAR["sinir"])},
            "olcum": "Aynı ağırlıklar; ikinci model yalnız logitleri 1000 ile çarpar. Doğruluklar 128 doğru sınıflanmış test örneği üzerindedir.",
            "sinir": "Tek MLP ve yapay ölçekleme; gerçek bir savunmanın maskelediğini ya da tek saldırıyla sağlamlığın kanıtlandığını göstermez."}


def goster(proj_fn, kayip_fn, tani_fn):
    r = deney(proj_fn, kayip_fn, tani_fn)
    print("Cihaz", r["cihaz"], "dtype", r["dtype"], "| kararlar aynı:", r["karar_ayni"])
    print("%-12s %7s %7s %7s %9s %9s %10s" % ("model", "temiz", "fgsm", "pgd_ce", "pgd_marjin", "rastgele", "sıfır grad"))
    for ad in ("taban", "maskeli"):
        v = r[ad]
        print("%-12s %7.3f %7.3f %7.3f %9.3f %9.3f %10.3f" % (ad, v["temiz"], v["fgsm"], v["pgd_ce"], v["pgd_marjin"], v["rastgele"], v["sifir_grad"]))
        print("  Senin tanın:", r["tani"][ad])
    print("L2 marjin PGD (eps=%.1f) robust: %.3f" % (AYAR["eps_l2"], r["l2_marjin_robust"]))
    print("Sınır:", r["sinir"])
    print("Kanıt:", ai_lab.kanit_yaz("ai-guvence-36-run", {"kaynak": "gercek", "kabul": False, "ders": "ai-guvence-36", "deney": r}))
