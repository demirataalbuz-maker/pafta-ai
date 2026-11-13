"""Model merging (TIES) ve hizalama analizi: gerçek el yazısı rakam verisinde gerçek ince ayarlardan çıkan görev vektörleriyle
TIES birleştirmesi; saldırganın ters etiketli görev vektörünün güvenlik davranışını iptal etmesi ve birleştirme denetimi."""
import importlib.metadata, math, random, secrets
import ai_lab

AYAR = {"seed": 43, "gizli": 24, "adim": 180, "lr": 0.015, "saldirgan_adim_carpani": 1.5, "yogunluk": 0.75, "lambda": 1.0,
        "dare_p": 0.9, "svd_k": 4, "min_kosinus": 0.45, "max_catisma": 0.35}


def _sayi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)


def referans_ties_kirp_ve_sec(gorev_vektorleri, yogunluk_orani):
    if not isinstance(gorev_vektorleri, list) or not gorev_vektorleri:
        raise ValueError("liste")
    if not isinstance(gorev_vektorleri[0], list) or not gorev_vektorleri[0]:
        raise ValueError("vektör")
    d = len(gorev_vektorleri[0])
    for v in gorev_vektorleri:
        if not isinstance(v, list) or len(v) != d or not all(_sayi(x) for x in v):
            raise ValueError("eleman")
    if not _sayi(yogunluk_orani) or not 0 < yogunluk_orani <= 1.0:
        raise ValueError("yoğunluk")
    k = max(1, int(d * yogunluk_orani))
    kirpilmis = []
    for v in gorev_vektorleri:
        sec = set(sorted(range(d), key=lambda j: (-abs(v[j]), j))[:k])
        kirpilmis.append([float(v[j]) if j in sec else 0.0 for j in range(d)])
    birlesik = []
    for j in range(d):
        toplam = sum(t[j] for t in kirpilmis)
        isaret = 1 if toplam > 0 else (-1 if toplam < 0 else 0)
        if isaret == 0:
            birlesik.append(0.0)
        else:
            uyumlu = [t[j] for t in kirpilmis if t[j] * isaret > 0]
            birlesik.append(float(sum(uyumlu) / len(uyumlu)) if uyumlu else 0.0)
    return birlesik


def referans_isaret_catisma(guvenlik_vektoru, gorev_vektoru):
    if not isinstance(guvenlik_vektoru, list) or not isinstance(gorev_vektoru, list) or not guvenlik_vektoru or len(guvenlik_vektoru) != len(gorev_vektoru):
        raise ValueError("vektör")
    if not all(_sayi(x) for x in guvenlik_vektoru + gorev_vektoru):
        raise ValueError("sayı")
    na = math.sqrt(sum(a * a for a in guvenlik_vektoru))
    nb = math.sqrt(sum(b * b for b in gorev_vektoru))
    if na <= 0 or nb <= 0:
        raise ValueError("sıfır norm")
    kosinus = sum(a * b for a, b in zip(guvenlik_vektoru, gorev_vektoru)) / (na * nb)
    d = len(guvenlik_vektoru)
    catisma = sum(1 for a, b in zip(guvenlik_vektoru, gorev_vektoru) if a * b < 0) / d
    aktif_guv = [j for j, a in enumerate(guvenlik_vektoru) if abs(a) > 1e-9]
    silinen = sum(1 for j in aktif_guv if guvenlik_vektoru[j] * gorev_vektoru[j] < 0 and abs(gorev_vektoru[j]) >= abs(guvenlik_vektoru[j])) / len(aktif_guv) if aktif_guv else 0.0
    return {"kosinus": float(kosinus), "catisma_orani": float(catisma), "silinen_guvenlik_orani": float(silinen)}


def referans_birlestirme_raporu(guvenlik_vektoru, birlesik_vektor, min_kosinus, max_catisma):
    if not _sayi(min_kosinus) or not -1.0 <= min_kosinus <= 1.0 or not _sayi(max_catisma) or not 0.0 <= max_catisma <= 1.0:
        raise ValueError("eşik")
    m = referans_isaret_catisma(guvenlik_vektoru, birlesik_vektor)
    bayraklar = []
    if m["kosinus"] < min_kosinus:
        bayraklar.append("hizalama_kaybi")
    if m["catisma_orani"] > max_catisma:
        bayraklar.append("isaret_catismasi")
    if m["silinen_guvenlik_orani"] > max_catisma:
        bayraklar.append("kritik_silinme")
    return {
        "bayraklar": bayraklar, "guvenli": not bool(bayraklar),
        "kosinus": m["kosinus"], "catisma_orani": m["catisma_orani"], "silinen_guvenlik_orani": m["silinen_guvenlik_orani"]
    }


def _yakin(a, b, tol=1e-7):
    if isinstance(a, dict):
        return isinstance(b, dict) and set(a) == set(b) and all(_yakin(a[k], b[k], tol) for k in a)
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(_yakin(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, (bool, str, int)) or a is None:
        return type(a) is type(b) and a == b
    return _sayi(a) and _sayi(b) and abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def deney(ties_fn, catisma_fn, rapor_fn):
    try:
        import torch
        from sklearn.datasets import load_digits
    except ImportError as e:
        raise ai_lab.GercekLabYok(str(e)) from e
    cihaz = ai_lab.torch_cihazi()
    seed = AYAR["seed"] + secrets.randbelow(500)
    torch.manual_seed(seed)
    v = load_digits()
    X = torch.tensor(v.data / 16.0, dtype=torch.float32, device=cihaz)
    Y = torch.tensor(v.target, dtype=torch.long, device=cihaz)
    karis = torch.randperm(len(Y), generator=torch.Generator().manual_seed(seed)).to(cihaz)
    X, Y = X[karis], Y[karis]
    A, B, T = slice(0, 600), slice(600, 1200), slice(1200, None)   # iki eğitim bölümü + ayrık test
    gorevler = {"guvenlik": lambda y: (y >= 5).long(),          # "zararlı istek" sınıfı → red
                "parite": lambda y: (y % 2 == 0).long(),        # zararsız yardımcı görev
                "taban": lambda y: (y % 3 == 0).long()}         # ön eğitim görevi

    def ag():
        return torch.nn.Sequential(torch.nn.Linear(64, AYAR["gizli"]), torch.nn.ReLU(), torch.nn.Linear(AYAR["gizli"], 2)).to(cihaz)

    def egit(model, Xs, ys, adim, lr):
        opt = torch.optim.Adam(model.parameters(), lr=lr)
        for _ in range(adim):
            opt.zero_grad()
            torch.nn.functional.cross_entropy(model(Xs), ys).backward()
            opt.step()
        return model

    def duz(model):
        return torch.cat([p.detach().flatten() for p in model.parameters()])

    def yukle(model, vektor):
        i = 0
        with torch.no_grad():
            for p in model.parameters():
                p.copy_(vektor[i:i + p.numel()].view_as(p))
                i += p.numel()
        return model

    def dogruluk(vektor, gorev):
        m = yukle(ag(), vektor)
        with torch.no_grad():
            return float((m(X[T]).argmax(1) == gorevler[gorev](Y[T])).float().mean())

    # Ön eğitimli taban (herkesin ince ayar yaptığı ortak başlangıç noktası)
    taban = egit(ag(), X[A], gorevler["taban"](Y[A]), AYAR["adim"], AYAR["lr"])
    w0 = duz(taban)

    def ince_ayar(Xs, ys, adim_carpani=1.0):
        m = yukle(ag(), w0.clone())
        return duz(egit(m, Xs, ys, int(AYAR["adim"] * adim_carpani), AYAR["lr"])) - w0

    # Gerçek ince ayarlardan gerçek görev vektörleri
    tau_guv = ince_ayar(X[A], gorevler["guvenlik"](Y[A]))                        # güvenlik ekibi
    tau_guv_b = ince_ayar(X[B], gorevler["guvenlik"](Y[B]))                      # bağımsız ikinci güvenlik ince ayarı
    tau_parite = ince_ayar(X[B], gorevler["parite"](Y[B]))                       # zararsız yetenek
    tau_ters = ince_ayar(X[B], 1 - gorevler["guvenlik"](Y[B]), AYAR["saldirgan_adim_carpani"])   # "yardımcı" görünen güvenlik silici
    tau_guv_l, tau_guv_b_l, tau_parite_l, tau_ters_l = (t.double().tolist() for t in (tau_guv, tau_guv_b, tau_parite, tau_ters))

    uyumlu_girdi = [tau_guv_l, tau_guv_b_l, tau_parite_l]
    saldiri_girdi = [tau_guv_l, tau_ters_l, tau_parite_l]

    b_uyumlu_ref = referans_ties_kirp_ve_sec(uyumlu_girdi, AYAR["yogunluk"])
    b_saldiri_ref = referans_ties_kirp_ve_sec(saldiri_girdi, AYAR["yogunluk"])
    b_uyumlu_ogr = ties_fn([list(x) for x in uyumlu_girdi], AYAR["yogunluk"])
    b_saldiri_ogr = ties_fn([list(x) for x in saldiri_girdi], AYAR["yogunluk"])
    ties_ayni = _yakin(b_uyumlu_ogr, b_uyumlu_ref) and _yakin(b_saldiri_ogr, b_saldiri_ref)

    c_uyumlu_ref = referans_isaret_catisma(tau_guv_l, b_uyumlu_ref)
    c_saldiri_ref = referans_isaret_catisma(tau_guv_l, b_saldiri_ref)
    catisma_ayni = (
        _yakin(catisma_fn(list(tau_guv_l), list(b_uyumlu_ref)), c_uyumlu_ref)
        and _yakin(catisma_fn(list(tau_guv_l), list(b_saldiri_ref)), c_saldiri_ref)
    )

    r_uyumlu_ref = referans_birlestirme_raporu(tau_guv_l, b_uyumlu_ref, AYAR["min_kosinus"], AYAR["max_catisma"])
    r_saldiri_ref = referans_birlestirme_raporu(tau_guv_l, b_saldiri_ref, AYAR["min_kosinus"], AYAR["max_catisma"])
    r_uyumlu_ogr = rapor_fn(list(tau_guv_l), list(b_uyumlu_ref), AYAR["min_kosinus"], AYAR["max_catisma"])
    r_saldiri_ogr = rapor_fn(list(tau_guv_l), list(b_saldiri_ref), AYAR["min_kosinus"], AYAR["max_catisma"])
    rapor_ayni = _yakin(r_uyumlu_ogr, r_uyumlu_ref) and _yakin(r_saldiri_ogr, r_saldiri_ref)

    # Birleştirilmiş modeller ayrık testte: güvenlik (red doğruluğu) ve zararsız yetenek (parite)
    def t(liste):
        return torch.tensor(liste, dtype=torch.float32, device=cihaz)

    olcum = {}
    for ad, vek in (("taban", w0), ("yalniz_guvenlik", w0 + tau_guv), ("yalniz_parite", w0 + tau_parite),
                    ("uyumlu_birlesim", w0 + AYAR["lambda"] * t(b_uyumlu_ref)), ("saldiri_birlesim", w0 + AYAR["lambda"] * t(b_saldiri_ref)),
                    ("basit_ortalama_saldiri", w0 + (tau_guv + tau_ters + tau_parite) / 3)):
        olcum[ad] = {"guvenlik": round(dogruluk(vek, "guvenlik"), 4), "parite": round(dogruluk(vek, "parite"), 4)}
    # DARE (Yu vd. 2024): her görev vektöründe girdilerin p'sini rastgele at, kalanları 1/(1-p) ile ölçekle, sonra topla
    g_dare = torch.Generator(device="cpu").manual_seed(seed + 7)

    def dare(tau):
        m = (torch.rand(tau.shape, generator=g_dare) >= AYAR["dare_p"]).to(tau.device).float()
        return tau * m / (1.0 - AYAR["dare_p"])

    def slerp(a, b, t):
        """İki parametre vektörü arasında küresel doğrusal ara değerleme (normlar korunur)."""
        an, bn = a / a.norm(), b / b.norm()
        om = torch.arccos((an * bn).sum().clamp(-1 + 1e-7, 1 - 1e-7))
        return (torch.sin((1 - t) * om) * a + torch.sin(t * om) * b) / torch.sin(om)

    for ad, vek in (("dare_uyumlu", w0 + dare(tau_guv) + dare(tau_guv_b) + dare(tau_parite)),
                    ("dare_saldiri", w0 + dare(tau_guv) + dare(tau_ters) + dare(tau_parite)),
                    ("slerp_guv_parite", slerp(w0 + tau_guv, w0 + tau_parite, 0.5)),
                    ("slerp_guv_ters", slerp(w0 + tau_guv, w0 + tau_ters, 0.5))):
        olcum[ad] = {"guvenlik": round(dogruluk(vek, "guvenlik"), 4), "parite": round(dogruluk(vek, "parite"), 4)}

    # Ağırlık uzayında SVD ile tespit: ilk katman ağırlık farkının (gizli × 64 piksel) baskın sağ tekil yönleri, güvenlik
    # ince ayarının kullandığı girdi özelliklerini verir. Başka bir görev vektörünün bu alt uzaya düşen enerji payı ölçülür.
    n1 = AYAR["gizli"] * 64

    def ilk_katman(tau):
        return tau[:n1].view(AYAR["gizli"], 64)

    _, _, Vh = torch.linalg.svd(ilk_katman(tau_guv).double(), full_matrices=False)
    V = Vh[:AYAR["svd_k"]].T                       # 64 × k

    def alt_uzay_payi(tau):
        M = ilk_katman(tau).double()
        return round(float((M @ V).pow(2).sum() / M.pow(2).sum()), 4)

    svd_tespit = {"guvenlik_b": alt_uzay_payi(tau_guv_b), "parite": alt_uzay_payi(tau_parite), "ters": alt_uzay_payi(tau_ters),
                  "rastgele_taban": round(AYAR["svd_k"] / 64, 4)}
    kos_ters = referans_isaret_catisma(tau_guv_l, tau_ters_l)["kosinus"]
    kos_parite = referans_isaret_catisma(tau_guv_l, tau_parite_l)["kosinus"]
    kos_guv_b = referans_isaret_catisma(tau_guv_l, tau_guv_b_l)["kosinus"]
    return {
        "cihaz": str(cihaz), "dtype": "float32 (görev vektörleri float64)",
        "surumler": {x: importlib.metadata.version(x) for x in ("torch", "scikit-learn")},
        "ayarlar": AYAR, "seed": seed, "boyut": len(tau_guv_l),
        "ties_ayni": ties_ayni, "catisma_ayni": catisma_ayni, "rapor_ayni": rapor_ayni,
        "uyumlu_rapor": r_uyumlu_ogr, "saldiri_rapor": r_saldiri_ogr,
        "gorev_kosinuslari": {"guvenlik_b": round(kos_guv_b, 4), "parite": round(kos_parite, 4), "ters": round(kos_ters, 4)},
        "dogruluklar": olcum, "svd_alt_uzay_payi": svd_tespit,
        "dogruluk_uyumlu": olcum["uyumlu_birlesim"]["guvenlik"], "dogruluk_saldiri": olcum["saldiri_birlesim"]["guvenlik"],
        "olcum": (f"sklearn digits (8x8 gerçek el yazısı rakamlar) üzerinde {AYAR['gizli']} gizli birimli MLP: ortak tabandan dört gerçek ince "
                  f"ayar (güvenlik A, güvenlik B, parite, saldırganın ters etiketli güvenlik silicisi) → {len(tau_guv_l)} boyutlu görev vektörleri. "
                  f"Güvenlik vektörüne kosinüs: güvenlik B {kos_guv_b:.3f}, parite {kos_parite:.3f}, ters {kos_ters:.3f}. İlk katman SVD "
                  f"(k={AYAR['svd_k']}) alt uzayına düşen enerji payı {svd_tespit}. TIES (yoğunluk {AYAR['yogunluk']}, λ={AYAR['lambda']}), "
                  f"DARE (p={AYAR['dare_p']}) ve SLERP (t=0.5) sonrası ayrık test doğrulukları {olcum}."),
        "sinir": ("Küçük bir MLP ve 8x8 rakam görüntüleriyle oyuncak bir 'güvenlik' görevi (rakam ≥ 5 → red) kullanılır; LLM güvenlik "
                  "hizalaması değildir. Görev vektörleri bütün parametrelerden alınır, tek gizli katmanlı ağ olduğu için katmanlar arası "
                  "etkileşim sınırlıdır. Saldırganın ince ayarı adım sayısı çarpanıyla güçlendirilmiştir (AYAR). SVD tespiti yalnız ilk "
                  "katmanda ve tek bir k değeriyle yapılır.")
    }


def goster(ties_fn, catisma_fn, rapor_fn):
    r = deney(ties_fn, catisma_fn, rapor_fn)
    print("Cihaz:", r["cihaz"], "| görev vektörü boyutu:", r["boyut"], "| güvenlik vektörüne kosinüsler:", r["gorev_kosinuslari"])
    for ad, d in r["dogruluklar"].items():
        print("  %-24s güvenlik: %.3f | parite: %.3f" % (ad, d["guvenlik"], d["parite"]))
    print("Uyumlu birleştirme raporu:", r["uyumlu_rapor"])
    print("Saldırı birleştirme raporu:", r["saldiri_rapor"])
    print("Sınır:", r["sinir"])
    print("Kanıt:", ai_lab.kanit_yaz("ai-guvence-43-run", {"kaynak": "gercek", "kabul": False, "ders": "ai-guvence-43", "deney": r}))
