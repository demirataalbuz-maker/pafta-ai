"""Mixture-of-Experts (MoE) Top-K router ve yük dengeleme: SmolLM2-135M'in gerçek MLP bloğundan damıtılan MoE'de
uzman çökmesi, aux_loss dengesi, kapasite düşürmesi ve modele takılınca dil modeli kaybı."""
import importlib.metadata, math, random, secrets
import ai_lab

AYAR = {
    "seed": 28,
    "katman": 15,
    "uzunluk": 96,
    "uzman_sayisi": 8,
    "k": 2,
    "uzman_gizli": 192,
    "kapasite_faktoru": 1.25,
    "baslangic_yanlilik": 3.0,
    "aux_katsayi": 0.3,
    "adim": 300,
    "lr": 0.003,
}


def _sayi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)


def _tam(v):
    return not isinstance(v, bool) and isinstance(v, int)


def referans_topk_yonlendirme(logitler, k):
    if not isinstance(logitler, list) or len(logitler) < 2 or not all(_sayi(x) for x in logitler):
        raise ValueError("logitler")
    if not _tam(k) or not 1 <= k <= len(logitler):
        raise ValueError("k")
    secilen = sorted(range(len(logitler)), key=lambda i: (-logitler[i], i))[:k]
    m = max(logitler[i] for i in secilen)
    exps = [math.exp(logitler[i] - m) for i in secilen]
    top = sum(exps)
    return {"uzmanlar": secilen, "agirliklar": [v / top for v in exps]}


def _atama_dogrula(secilen_uzmanlar, uzman_sayisi):
    if not _tam(uzman_sayisi) or uzman_sayisi < 2:
        raise ValueError("uzman_sayisi")
    if not isinstance(secilen_uzmanlar, list) or not secilen_uzmanlar:
        raise ValueError("secilen_uzmanlar")
    k_boyut = None
    for s in secilen_uzmanlar:
        if not isinstance(s, list) or not s or len(s) > uzman_sayisi:
            raise ValueError("atama_liste")
        if k_boyut is not None and len(s) != k_boyut:
            raise ValueError("k_farkli")
        k_boyut = len(s)
        if len(set(s)) != len(s):
            raise ValueError("tekrarli_uzman")
        for idx in s:
            if not _tam(idx) or not 0 <= idx < uzman_sayisi:
                raise ValueError("uzman_indis")
    return len(secilen_uzmanlar), k_boyut


def referans_yuk_kaybi(router_olasilik, secilen_uzmanlar, uzman_sayisi):
    T, k = _atama_dogrula(secilen_uzmanlar, uzman_sayisi)
    if not isinstance(router_olasilik, list) or len(router_olasilik) != T:
        raise ValueError("router_boyut")
    for p in router_olasilik:
        if not isinstance(p, list) or len(p) != uzman_sayisi:
            raise ValueError("olasilik_boyut")
        for x in p:
            if not _sayi(x) or not 0.0 <= x <= 1.0:
                raise ValueError("olasilik_deger")
        if abs(sum(p) - 1.0) > 1e-6:
            raise ValueError("olasilik_toplam")
    sayac = [0] * uzman_sayisi
    for s in secilen_uzmanlar:
        for idx in s:
            sayac[idx] += 1
    toplam_atama = float(T * k)
    f = [c / toplam_atama for c in sayac]
    P = [sum(router_olasilik[t][e] for t in range(T)) / float(T) for e in range(uzman_sayisi)]
    return float(uzman_sayisi * sum(f[e] * P[e] for e in range(uzman_sayisi)))


def referans_kapasite_raporu(secilen_uzmanlar, uzman_sayisi, kapasite_faktoru):
    T, k = _atama_dogrula(secilen_uzmanlar, uzman_sayisi)
    if not _sayi(kapasite_faktoru) or kapasite_faktoru <= 0.0:
        raise ValueError("kapasite_faktoru")
    toplam_atama = T * k
    kapasite = max(1, int(math.ceil((toplam_atama / float(uzman_sayisi)) * kapasite_faktoru)))
    yukler = [0] * uzman_sayisi
    for s in secilen_uzmanlar:
        for idx in s:
            yukler[idx] += 1
    dusurulen = sum(max(0, y - kapasite) for y in yukler)
    return {
        "uzman_kapasitesi": kapasite,
        "uzman_yukleri": yukler,
        "dusurulen_atama": dusurulen,
        "dusurulme_orani": dusurulen / float(toplam_atama),
        "uzman_cokmesi": bool(max(yukler) > 0.5 * T),
    }


def _yakin(a, b, tol=1e-9):
    if isinstance(a, dict):
        return isinstance(b, dict) and set(a) == set(b) and all(_yakin(a[k], b[k], tol) for k in a)
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(_yakin(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, (bool, str)) or a is None:
        return type(a) is type(b) and a == b
    return _sayi(a) and _sayi(b) and abs(a - b) <= tol * max(1.0, abs(a), abs(b))


EGITIM_ISTEMLERI = ["Once upon a time in a small village", "The report describes the main findings of", "A good way to start the day is",
                    "The engineers tested the new bridge by", "Last summer we travelled to the coast and", "The museum guide explained that"]
AYRIK_METIN = ("The security team reviewed the server logs every morning. They looked for failed logins, unusual traffic and new "
               "processes. When an alert appeared, an analyst checked the source address and wrote a short report for the manager. "
               "On Fridays the whole group met to discuss what they had learned during the week. Sometimes a false alarm had wasted "
               "an afternoon, and sometimes a small detail had led them to a real problem. The manager kept a list of these cases "
               "and used it to train new people who joined the team in the spring.")


class MoE:
    """SmolLM2 katmanındaki gerçek MLP bloğundan damıtılan top-k MoE (uzmanlar küçük SwiGLU MLP'ler)."""

    def __init__(self, torch, d, E, k, gizli, seed, yanlilik=0.0):
        self.t, self.E, self.k = torch, E, k
        g = torch.Generator().manual_seed(seed)
        s = 1.0 / math.sqrt(d)
        self.Wr = (torch.randn(d, E, generator=g) * s)
        self.br = torch.zeros(E)
        self.br[0] = yanlilik   # erken eğitimdeki rastgele dengesizliğin abartılı hâli: uzman 0 önde başlar
        self.W1 = torch.randn(E, d, gizli, generator=g) * s
        self.W3 = torch.randn(E, d, gizli, generator=g) * s
        self.W2 = torch.randn(E, gizli, d, generator=g) / math.sqrt(gizli)

    def to(self, cihaz):
        for ad in ("Wr", "br", "W1", "W3", "W2"):
            setattr(self, ad, getattr(self, ad).to(cihaz).requires_grad_(True))
        return self

    def parametreler(self):
        return [self.Wr, self.br, self.W1, self.W3, self.W2]

    def yonlendir(self, x):
        z = x @ self.Wr + self.br
        p = self.t.softmax(z, dim=-1)
        v, i = self.t.topk(z, self.k, dim=-1)
        # top-k > 1: seçilen logitler üzerinde softmax (Mixtral). top-1: seçilen uzmanın tam softmax olasılığı (Switch);
        # aksi hâlde ağırlık hep 1 olur ve yönlendiriciye görev kaybından gradyan ulaşmaz.
        w = self.t.softmax(v, dim=-1) if self.k > 1 else p.gather(-1, i)
        return z, p, i, w

    def ileri(self, x, kapasite_faktoru=None, kiraci=None, dus=None):
        """x: [T, d]. kapasite_faktoru verilirse her uzman en çok ceil(T*k/E*kf) atama alır (sırayla), fazlası düşer.
        kiraci verilirse kapasite kiracı başına ayrı hesaplanır (izole batch). dus ([T, k] bool) verilirse o maske kullanılır.
        Döndürür: (çıktı, düşürülen maske [T, k])."""
        t = self.t
        z, p, i, w = self.yonlendir(x)
        T = x.shape[0]
        if dus is None:
            dus = t.zeros(T, self.k, dtype=t.bool, device=x.device)
        if kapasite_faktoru is not None:
            gruplar = [list(range(T))] if kiraci is None else [[j for j in range(T) if kiraci[j] == c] for c in sorted(set(kiraci))]
            for grup in gruplar:
                kap = max(1, math.ceil(len(grup) * self.k / self.E * kapasite_faktoru))
                sayac = [0] * self.E
                for j in grup:
                    for r in range(self.k):
                        e = int(i[j, r])
                        sayac[e] += 1
                        if sayac[e] > kap:
                            dus[j, r] = True
        y = t.zeros_like(x)
        for r in range(self.k):
            for e in range(self.E):
                m = (i[:, r] == e) & ~dus[:, r]
                if m.any():
                    h = x[m]
                    a = t.nn.functional.silu(h @ self.W1[e]) * (h @ self.W3[e])
                    y[m] = y[m] + w[m, r:r + 1] * (a @ self.W2[e])
        return y, dus


def mlp_verisi(torch, tok, model, cihaz, katman, istemler, uzunluk):
    """Modelin kendi ürettiği metinde katmanın MLP girdi/çıktısı (gerçek aktivasyonlar)."""
    X, Y = [], []
    kayit = {}
    kanca = model.model.layers[katman].mlp.register_forward_hook(lambda m, i, o: kayit.update(x=i[0][0].detach(), y=o[0].detach()))
    try:
        for s in istemler:
            ids = tok(s, add_special_tokens=False)["input_ids"]
            with torch.no_grad():
                seq = model.generate(torch.tensor([ids], device=cihaz), max_new_tokens=uzunluk, do_sample=True, top_k=0,
                                     pad_token_id=tok.eos_token_id)
                model(seq)
            X.append(kayit["x"].float())
            Y.append(kayit["y"].float())
    finally:
        kanca.remove()
    return torch.cat(X), torch.cat(Y)


def moe_egit(torch, X, Y, aux_katsayi, cihaz, E=None, k=None, yanlilik=None):
    moe = MoE(torch, X.shape[1], E or AYAR["uzman_sayisi"], k or AYAR["k"], AYAR["uzman_gizli"], AYAR["seed"],
              AYAR["baslangic_yanlilik"] if yanlilik is None else yanlilik).to(cihaz)
    opt = torch.optim.Adam(moe.parametreler(), lr=AYAR["lr"])
    olcek = float(Y.pow(2).mean())
    for _ in range(AYAR["adim"]):
        opt.zero_grad()
        y, _ = moe.ileri(X)
        z, p, i, _w = moe.yonlendir(X)
        f = torch.zeros(moe.E, device=cihaz).scatter_add_(0, i.flatten(), torch.ones(i.numel(), device=cihaz)) / i.numel()
        aux = moe.E * (f * p.mean(0)).sum()
        (((y - Y) ** 2).mean() / olcek + aux_katsayi * aux).backward()
        opt.step()
    for prm in moe.parametreler():
        prm.requires_grad_(False)
    return moe


def deney(topk_fn, yuk_fn, kap_fn):
    try:
        import torch
    except ImportError as e:
        raise ai_lab.GercekLabYok(str(e)) from e
    tok, model, bilgi = ai_lab.dil_modeli()
    cihaz = ai_lab.torch_cihazi()
    model.to(cihaz)
    E, K, L = AYAR["uzman_sayisi"], AYAR["k"], AYAR["katman"]
    torch.manual_seed(AYAR["seed"] + secrets.randbelow(10))
    X, Y = mlp_verisi(torch, tok, model, cihaz, L, EGITIM_ISTEMLERI, AYAR["uzunluk"])
    moe_dz = moe_egit(torch, X, Y, 0.0, cihaz)
    moe_dg = moe_egit(torch, X, Y, AYAR["aux_katsayi"], cihaz)

    ids = torch.tensor([tok(AYRIK_METIN)["input_ids"]], device=cihaz)
    kayit = {}
    h = model.model.layers[L].mlp.register_forward_hook(lambda m, i, o: kayit.update(x=i[0][0].detach().float()))
    with torch.no_grad():
        temiz_kayip = float(model(ids, labels=ids).loss)
    h.remove()
    Xa = kayit["x"]
    T = Xa.shape[0]

    def takili_kayip(moe):
        def kanca(m, i, o):
            y, _ = moe.ileri(i[0][0].float(), AYAR["kapasite_faktoru"])
            return y.unsqueeze(0).to(o.dtype)
        hh = model.model.layers[L].mlp.register_forward_hook(kanca)
        with torch.no_grad():
            k = float(model(ids, labels=ids).loss)
        hh.remove()
        return k

    def bozuk_uzman(moe):
        """En çok yük alan uzmanın çıktısı ters çevrilir (kurcalanmış uzman ağırlığı): kaç token etkilenir, LM kaybı ne olur?"""
        i = moe.yonlendir(Xa)[2]
        yuk = torch.bincount(i.flatten(), minlength=moe.E)
        e = int(yuk.argmax())
        etki = float((i == e).any(-1).float().mean())
        eski = moe.W2[e].clone()
        moe.W2[e] = -eski
        try:
            k = takili_kayip(moe)
        finally:
            moe.W2[e] = eski
        return {"uzman": e, "etkilenen_token_orani": round(etki, 4), "lm_kaybi": k}

    with torch.no_grad():
        boz_dz, boz_dg = bozuk_uzman(moe_dz), bozuk_uzman(moe_dg)
        z_dengesiz = moe_dz.yonlendir(Xa)[0].double().tolist()
        p_dengesiz = torch.softmax(moe_dz.yonlendir(Xa)[0].double(), dim=-1).tolist()
        z_dengeli = moe_dg.yonlendir(Xa)[0].double().tolist()
        p_dengeli = torch.softmax(moe_dg.yonlendir(Xa)[0].double(), dim=-1).tolist()
        kayip_dz_takili, kayip_dg_takili = takili_kayip(moe_dz), takili_kayip(moe_dg)

    topk_ayni = True
    sec_dengesiz, sec_dengeli = [], []
    for t in range(T):
        tk_dz_o = topk_fn(list(z_dengesiz[t]), K)
        tk_dz_r = referans_topk_yonlendirme(z_dengesiz[t], K)
        tk_dg_o = topk_fn(list(z_dengeli[t]), K)
        tk_dg_r = referans_topk_yonlendirme(z_dengeli[t], K)
        topk_ayni = topk_ayni and _yakin(tk_dz_o, tk_dz_r) and _yakin(tk_dg_o, tk_dg_r)
        sec_dengesiz.append(tk_dz_r["uzmanlar"])
        sec_dengeli.append(tk_dg_r["uzmanlar"])

    p_dz_norm = [[x / sum(r) for x in r] for r in p_dengesiz]
    p_dg_norm = [[x / sum(r) for x in r] for r in p_dengeli]

    kayip_dz_o = yuk_fn([list(r) for r in p_dz_norm], [list(s) for s in sec_dengesiz], E)
    kayip_dz_r = referans_yuk_kaybi(p_dz_norm, sec_dengesiz, E)
    kayip_dg_o = yuk_fn([list(r) for r in p_dg_norm], [list(s) for s in sec_dengeli], E)
    kayip_dg_r = referans_yuk_kaybi(p_dg_norm, sec_dengeli, E)
    yuk_ayni = _yakin(kayip_dz_o, kayip_dz_r) and _yakin(kayip_dg_o, kayip_dg_r)

    kap_dz_o = kap_fn([list(s) for s in sec_dengesiz], E, AYAR["kapasite_faktoru"])
    kap_dz_r = referans_kapasite_raporu(sec_dengesiz, E, AYAR["kapasite_faktoru"])
    kap_dg_o = kap_fn([list(s) for s in sec_dengeli], E, AYAR["kapasite_faktoru"])
    kap_dg_r = referans_kapasite_raporu(sec_dengeli, E, AYAR["kapasite_faktoru"])
    kap_ayni = _yakin(kap_dz_o, kap_dz_r) and _yakin(kap_dg_o, kap_dg_r)

    return {
        "cihaz": str(cihaz),
        "dtype": "float32 (yönlendirme float64)",
        "model": {k2: bilgi[k2] for k2 in ("model", "revizyon", "agirlik_sha256", "parametre")},
        "surumler": {"torch": importlib.metadata.version("torch"), "transformers": importlib.metadata.version("transformers")},
        "ayarlar": AYAR, "egitim_token": int(X.shape[0]), "ayrik_token": T,
        "topk_ayni": topk_ayni,
        "yuk_ayni": yuk_ayni,
        "kapasite_ayni": kap_ayni,
        "dengesiz": {"aux_kayip": kayip_dz_r, "kapasite": kap_dz_r, "takili_lm_kaybi": kayip_dz_takili},
        "dengeli": {"aux_kayip": kayip_dg_r, "kapasite": kap_dg_r, "takili_lm_kaybi": kayip_dg_takili},
        "temiz_lm_kaybi": temiz_kayip,
        "kayip_azaldi": bool(kayip_dg_r < kayip_dz_r),
        "dusurulme_azaldi": bool(kap_dg_r["dusurulen_atama"] < kap_dz_r["dusurulen_atama"]),
        "bozuk_uzman": {"dengesiz": boz_dz, "dengeli": boz_dg},
        "cokme_etki_alanini_buyutur": bool(boz_dz["etkilenen_token_orani"] >= 0.95
                                           and boz_dg["etkilenen_token_orani"] <= boz_dz["etkilenen_token_orani"] - 0.2),
        "olcum": (f"SmolLM2-135M katman {L} MLP bloğu {E} uzmanlı top-{K} MoE'ye damıtıldı ({int(X.shape[0])} gerçek token). Ayrık metinde "
                  f"({T} token) yardımcı kayıpsız: aux {kayip_dz_r:.3f}, uzman yükleri {kap_dz_r['uzman_yukleri']}, düşen {kap_dz_r['dusurulen_atama']}; "
                  f"yardımcı kayıplı: aux {kayip_dg_r:.3f}, yükler {kap_dg_r['uzman_yukleri']}, düşen {kap_dg_r['dusurulen_atama']}. Model içine "
                  f"takılınca LM kaybı: temiz {temiz_kayip:.3f}, dengesiz {kayip_dz_takili:.3f}, dengeli {kayip_dg_takili:.3f}. En çok yüklü uzmanın "
                  f"çıktısı ters çevrilince (kurcalanmış uzman): dengesiz MoE'de tokenların %{100 * boz_dz['etkilenen_token_orani']:.0f}'i etkilendi, LM "
                  f"kaybı {kayip_dz_takili:.3f} → {boz_dz['lm_kaybi']:.3f}; dengeli MoE'de %{100 * boz_dg['etkilenen_token_orani']:.0f}, "
                  f"{kayip_dg_takili:.3f} → {boz_dg['lm_kaybi']:.3f}."),
        "sinir": ("Tek katmanın MLP'si küçük bir derlemde damıtılır; gerçek ön eğitimli MoE modeli değildir. Paylaşımlı uzmanlar, yardımcı kayıpsız "
                  "dinamik yanlılık (DeepSeek-V3) ve büyük ölçekte uzmanlaşma ölçülmez; katsayı büyütülürse uzmanlaşma zayıflayabilir. Kurcalanmış "
                  "uzman yalnız 30 katmandan birinde olduğu için LM kaybındaki değişim küçüktür ve koşudan koşuya değişir; kararlı olan ölçü "
                  "etkilenen token oranıdır (etki alanı)."),
    }


def goster(topk_fn, yuk_fn, kap_fn):
    r = deney(topk_fn, yuk_fn, kap_fn)
    print("Model:", r["model"]["model"], "| cihaz:", r["cihaz"], "| katman:", AYAR["katman"], "| uzman:", AYAR["uzman_sayisi"], "top-%d" % AYAR["k"], "| ayrık token:", r["ayrik_token"])
    print("LM kaybı | temiz: %.3f | dengesiz MoE: %.3f | dengeli MoE: %.3f" % (r["temiz_lm_kaybi"], r["dengesiz"]["takili_lm_kaybi"], r["dengeli"]["takili_lm_kaybi"]))
    print("Dengesiz router -> aux_loss: %.4f | kapasite:" % r["dengesiz"]["aux_kayip"], r["dengesiz"]["kapasite"])
    print("Dengeli router  -> aux_loss: %.4f | kapasite:" % r["dengeli"]["aux_kayip"], r["dengeli"]["kapasite"])
    print("Sınır:", r["sinir"])
    print("Kanıt:", ai_lab.kanit_yaz("ai-temel-28-run", {"kaynak": "gercek", "kabul": False, "ders": "ai-temel-28", "deney": r}))
