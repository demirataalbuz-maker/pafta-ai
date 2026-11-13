"""MI istatistiği: küçük MLP'ler ve shadow modellerle loss eşiği ile LiRA tarzı likelihood ratio; Clopper-Pearson aralığı."""
import copy, importlib.metadata, math, random, secrets
import ai_lab

AYAR = {"seed": 39, "gizli": 128, "epoch": 300, "lr": 0.003, "havuz": 800, "shadow": 16, "hedef_uye": 400, "fpr": 0.05, "guven": 0.95, "taban_var": 1e-4, "etiket_gurultu": 0.15}


def _sayi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)


def referans_logit(p):
    if not _sayi(p) or not 0 <= p <= 1:
        raise ValueError("p")
    e = 1e-12
    q = min(max(p, e), 1 - e)
    return math.log(q) - math.log(1 - q)


def referans_lr(x, ic, dis, taban):
    if not _sayi(x) or not _sayi(taban) or taban <= 0:
        raise ValueError("girdi")
    for l in (ic, dis):
        if not isinstance(l, list) or len(l) < 2 or not all(_sayi(v) for v in l):
            raise ValueError("liste")

    def log_n(v, m, s2):
        return -0.5 * math.log(2 * math.pi * s2) - (v - m) ** 2 / (2 * s2)

    def uyum(l):
        m = sum(l) / len(l)
        return m, max(sum((v - m) ** 2 for v in l) / (len(l) - 1), taban)
    mi, vi = uyum(ic)
    md, vd = uyum(dis)
    return log_n(x, mi, vi) - log_n(x, md, vd)


def _binom_kdf(k, n, p):
    if p <= 0:
        return 1.0
    if p >= 1:
        return 1.0 if k >= n else 0.0
    return sum(math.exp(math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) + i * math.log(p) + (n - i) * math.log(1 - p)) for i in range(k + 1))


def referans_cp(k, n, guven):
    if isinstance(k, bool) or isinstance(n, bool) or not isinstance(k, int) or not isinstance(n, int) or n < 1 or not 0 <= k <= n:
        raise ValueError("sayım")
    if not _sayi(guven) or not 0 < guven < 1:
        raise ValueError("güven")
    a = (1 - guven) / 2

    def ikiye(f):
        lo, hi = 0.0, 1.0
        for _ in range(60):
            m = (lo + hi) / 2
            if f(m):
                lo = m
            else:
                hi = m
        return (lo + hi) / 2
    alt = 0.0 if k == 0 else ikiye(lambda p: 1 - _binom_kdf(k - 1, n, p) < a)
    ust = 1.0 if k == n else ikiye(lambda p: _binom_kdf(k, n, p) >= a)
    return {"oran": k / n, "alt": alt, "ust": ust}


def _yakin(a, b, tol=1e-7):
    if isinstance(a, dict):
        return isinstance(b, dict) and set(a) == set(b) and all(_yakin(a[k], b[k], tol) for k in a)
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(_yakin(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, (bool, str)) or a is None:
        return type(a) is type(b) and a == b
    return _sayi(a) and _sayi(b) and abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def _auc_tpr(uye, degil, fpr):
    uye_s, degil_s = sorted(uye), sorted(degil)
    kazanc = 0.0
    for a in uye_s:
        for b in degil_s:
            kazanc += 1.0 if a > b else 0.5 if a == b else 0.0
    en_iyi = 0
    izin = math.floor(fpr * len(degil))
    esik = degil_s[-izin - 1] if izin < len(degil) else None
    en_iyi = sum(a > esik for a in uye) if esik is not None else len(uye)
    fp = sum(b > esik for b in degil) if esik is not None else len(degil)
    return {"auc": kazanc / (len(uye) * len(degil)), "tp": en_iyi, "fp": fp, "uye": len(uye), "uye_degil": len(degil)}


def _egit(torch, X, Y, tohum, cihaz):
    g = torch.Generator(device=cihaz).manual_seed(tohum)
    net = torch.nn.Sequential(torch.nn.Linear(64, AYAR["gizli"]), torch.nn.ReLU(), torch.nn.Linear(AYAR["gizli"], 10)).to(cihaz)
    for p in net.parameters():
        if p.dim() > 1:
            torch.nn.init.xavier_uniform_(p, generator=g)
    opt = torch.optim.Adam(net.parameters(), lr=AYAR["lr"])
    for _ in range(AYAR["epoch"]):
        opt.zero_grad()
        torch.nn.functional.cross_entropy(net(X), Y).backward()
        opt.step()
    for p in net.parameters():
        p.requires_grad_(False)
    return net


def deney(logit_fn, lr_fn, cp_fn):
    try:
        import torch
        from sklearn.datasets import load_digits
    except ImportError as e:
        raise ai_lab.GercekLabYok(str(e)) from e
    cihaz = ai_lab.torch_cihazi()
    rng = random.Random(secrets.randbits(64))
    d = load_digits()
    secim = rng.sample(range(len(d.data)), AYAR["havuz"])
    X = torch.tensor(d.data[secim] / 16.0, dtype=torch.float32, device=cihaz)
    Y = torch.tensor(d.target[secim], dtype=torch.long, device=cihaz)
    gen = torch.Generator(device=cihaz).manual_seed(secrets.randbits(32))
    # Etiket gürültüsü ezberi görünür kılar: küçük digits görevi aksi hâlde bellek izi bırakmaz.
    gurultu = torch.rand(len(Y), generator=gen, device=cihaz) < AYAR["etiket_gurultu"]
    Y = torch.where(gurultu, torch.randint(0, 10, Y.shape, generator=gen, device=cihaz), Y)

    def guven(net):
        with torch.no_grad():
            p = torch.softmax(net(X).double(), 1)
        return p[torch.arange(len(Y)), Y].tolist()

    n = len(X)
    tohum = secrets.randbits(30)
    hedef_uye = rng.sample(range(n), AYAR["hedef_uye"])
    uye_kume = set(hedef_uye)
    hedef = _egit(torch, X[hedef_uye], Y[hedef_uye], tohum, cihaz)
    p_hedef = guven(hedef)
    with torch.no_grad():
        egitim_dog = float((hedef(X[hedef_uye]).argmax(1) == Y[hedef_uye]).float().mean())
        test_idx = [i for i in range(n) if i not in uye_kume]
        test_dog = float((hedef(X[test_idx]).argmax(1) == Y[test_idx]).float().mean())
    del hedef
    ic = [[] for _ in range(n)]
    dis = [[] for _ in range(n)]
    logit_ayni = True
    for s in range(AYAR["shadow"]):
        alt = rng.sample(range(n), AYAR["hedef_uye"])
        net = _egit(torch, X[alt], Y[alt], tohum + s + 1, cihaz)
        ps = guven(net)
        del net
        ak = set(alt)
        for i in range(n):
            lr = referans_logit(ps[i])
            (ic if i in ak else dis)[i].append(lr)
    for p in rng.sample(p_hedef, 64) + [0.0, 1.0]:
        logit_ayni = logit_ayni and _yakin(logit_fn(p), referans_logit(p))
    lr_ayni = True
    uygun = [i for i in range(n) if len(ic[i]) >= 2 and len(dis[i]) >= 2]
    skor_lira, skor_kayip, etiket = [], [], []
    for i in uygun:
        x = referans_logit(p_hedef[i])
        r = referans_lr(x, ic[i], dis[i], AYAR["taban_var"])
        lr_ayni = lr_ayni and _yakin(lr_fn(x, list(ic[i]), list(dis[i]), AYAR["taban_var"]), r)
        skor_lira.append(r)
        skor_kayip.append(x)
        etiket.append(i in uye_kume)
    def ayir(skor):
        return [v for v, e in zip(skor, etiket) if e], [v for v, e in zip(skor, etiket) if not e]
    sonuc = {}
    cp_ayni = True
    for ad, skor in (("kayip_esigi", skor_kayip), ("lira", skor_lira)):
        u, dg = ayir(skor)
        o = _auc_tpr(u, dg, AYAR["fpr"])
        tpr_r, tpr_o = referans_cp(o["tp"], o["uye"], AYAR["guven"]), cp_fn(o["tp"], o["uye"], AYAR["guven"])
        fpr_r, fpr_o = referans_cp(o["fp"], o["uye_degil"], AYAR["guven"]), cp_fn(o["fp"], o["uye_degil"], AYAR["guven"])
        cp_ayni = cp_ayni and _yakin(tpr_o, tpr_r) and _yakin(fpr_o, fpr_r)
        sonuc[ad] = dict(o, tpr=tpr_r, fpr=fpr_r)
    return {"cihaz": str(cihaz), "surumler": {x: importlib.metadata.version(x) for x in ("torch", "scikit-learn")}, "veri": "sklearn load_digits; etiketlerin bir kısmı her koşuda rastgele bozulur", "ayarlar": AYAR, "egitim_dogrulugu": egitim_dog, "test_dogrulugu": test_dog,
            "uygun": len(uygun), "uye": sum(etiket), "uye_degil": len(etiket) - sum(etiket), "logit_ayni": logit_ayni, "lr_ayni": lr_ayni, "cp_ayni": cp_ayni, "sonuc": sonuc, "ic_ort_adet": sum(len(v) for v in ic) / n, "dis_ort_adet": sum(len(v) for v in dis) / n,
            "olcum": "Her shadow model havuzun yarısıyla eğitilir; örnek başına üye/üye-değil logit güven dağılımına Gaussian uydurulur. TPR, yanlış pozitif sınırına en yakın eşikte ölçülür; aralıklar Clopper-Pearson'dır.",
            "sinir": "Tek veri, küçük MLP, etiket gürültüsüyle bilerek ezberletilmiş hedef; gerçek bir modelin gizlilik riskini veya LiRA'nın tam yeniden üretimini göstermez."}


def goster(logit_fn, lr_fn, cp_fn):
    r = deney(logit_fn, lr_fn, cp_fn)
    print("Cihaz", r["cihaz"], "| eğitim doğruluğu %.3f test %.3f" % (r["egitim_dogrulugu"], r["test_dogrulugu"]), "| shadow", AYAR["shadow"], "| ölçülen", r["uye"], "üye", r["uye_degil"], "üye değil")
    for ad, v in r["sonuc"].items():
        print("%-12s AUC=%.3f TPR@FPR≤%.2f = %.3f [%.3f, %.3f] | gerçek FPR=%.3f [%.3f, %.3f]" % (ad, v["auc"], AYAR["fpr"], v["tpr"]["oran"], v["tpr"]["alt"], v["tpr"]["ust"], v["fpr"]["oran"], v["fpr"]["alt"], v["fpr"]["ust"]))
    print("Sınır:", r["sinir"])
    print("Kanıt:", ai_lab.kanit_yaz("ai-guvence-39-run", {"kaynak": "gercek", "kabul": False, "ders": "ai-guvence-39", "deney": r}))
