"""Embedding geometrisi: all-minilm vektörlerinde kosinüs kimliği, PCA, yoğunlaşma ve hubness; Gaussian tabanla karşılaştırma."""
import copy, importlib.metadata, math, random, secrets
import ai_lab
from sandbox.ai_gercek_ai_guvence_31 import GOMME_MODELI, _Gomucu

KONULAR = {"kedi": ["kedinin aşı takvimi", "kedi mama seçimi", "kedinin tırnak bakımı"], "bisiklet": ["bisiklet zinciri yağlama", "bisiklet lastiği değişimi", "bisiklet fren ayarı"],
           "ekmek": ["ekşi maya ekmek", "ekmek hamuru mayalama", "tam buğday ekmek tarifi"], "yedek": ["veritabanı yedekleme", "yedek diskin sınanması", "günlük yedek çizelgesi"],
           "bahce": ["domates fidesi sulama", "bahçe toprağı hazırlama", "gül budama zamanı"], "gezi": ["tren bileti alma", "dağ yürüyüşü rotası", "otel rezervasyon iptali"],
           "gitar": ["gitar akort etme", "akor geçişi çalışması", "gitar teli değişimi"], "butce": ["aylık bütçe tablosu", "fatura ödeme takibi", "market harcaması notu"]}
KALIPLAR = ["{} hakkında kısa bir not yazdım.", "Yarınki toplantıda {} konuşulacak.", "Lütfen {} konusunu özetler misin?", "Dün akşam {} ile uğraştım.",
            "{} için bir kontrol listesi hazırlıyorum.", "Arkadaşım bana {} konusunda soru sordu.", "Bu hafta en çok {} zamanımı aldı.", "{} rehberini baştan okudum."]
AYAR = {"ornek": 120, "adim": 120, "k": 5, "cift": 200, "oran": 0.9, "model": GOMME_MODELI, "kaynak": "Sentetik şablon cümleleri (8 konu, 3 ifade, 8 kalıp)"}


def _sayi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)


def referans_kosinus(a, b):
    if not isinstance(a, list) or not isinstance(b, list) or not a or len(a) != len(b) or not all(_sayi(v) for v in a + b):
        raise ValueError("girdi")
    na, nb = math.sqrt(sum(v * v for v in a)), math.sqrt(sum(v * v for v in b))
    if na == 0 or nb == 0:
        raise ValueError("sıfır")
    c = sum(p * q for p, q in zip(a, b)) / (na * nb)
    d2 = sum((p / na - q / nb) ** 2 for p, q in zip(a, b))
    return {"kosinus": c, "ham_l2": math.sqrt(sum((p - q) ** 2 for p, q in zip(a, b))), "birim_l2_kare": d2, "kimlik_farki": abs(d2 - (2 - 2 * c))}


def referans_pca(X, v0, adim):
    if not isinstance(X, list) or len(X) < 2 or not all(isinstance(s, list) and s for s in X) or len({len(s) for s in X}) != 1:
        raise ValueError("X")
    d = len(X[0])
    if not all(_sayi(v) for s in X for v in s) or not isinstance(v0, list) or len(v0) != d or not all(_sayi(v) for v in v0):
        raise ValueError("sayı")
    if isinstance(adim, bool) or not isinstance(adim, int) or adim < 1:
        raise ValueError("adim")
    n = len(X)
    m = [sum(s[j] for s in X) / n for j in range(d)]
    Y = [[s[j] - m[j] for j in range(d)] for s in X]
    toplam = sum(v * v for s in Y for v in s) / (n - 1)
    nv = math.sqrt(sum(v * v for v in v0))
    if nv == 0 or toplam == 0:
        raise ValueError("sıfır")
    v = [x / nv for x in v0]

    def c(u):
        p = [sum(a * b for a, b in zip(s, u)) for s in Y]
        return [sum(Y[i][j] * p[i] for i in range(n)) / (n - 1) for j in range(d)]
    for _ in range(adim):
        w = c(v)
        nw = math.sqrt(sum(x * x for x in w))
        if nw == 0:
            raise ValueError("sıfır")
        v = [x / nw for x in w]
    lam = sum(a * b for a, b in zip(v, c(v)))
    i = max(range(d), key=lambda j: abs(v[j]))
    if v[i] < 0:
        v = [-x for x in v]
    return {"bilesen": v, "ozdeger": lam, "aciklanan_oran": lam / toplam}


def referans_hubness(komsular):
    if not isinstance(komsular, list) or len(komsular) < 2:
        raise ValueError("liste")
    n = len(komsular)
    if not all(isinstance(k, list) and k for k in komsular) or len({len(k) for k in komsular}) != 1:
        raise ValueError("k")
    N = [0] * n
    for i, ks in enumerate(komsular):
        if len(set(ks)) != len(ks):
            raise ValueError("tekrar")
        for j in ks:
            if isinstance(j, bool) or not isinstance(j, int) or not 0 <= j < n or j == i:
                raise ValueError("komşu")
            N[j] += 1
    mu = sum(N) / n
    s2 = sum((v - mu) ** 2 for v in N) / n
    sk = 0.0 if s2 == 0 else sum((v - mu) ** 3 for v in N) / n / s2 ** 1.5
    i = max(range(n), key=lambda j: N[j])
    return {"n_k": N, "carpiklik": sk, "anti_hub": sum(v == 0 for v in N), "en_buyuk_hub": i, "en_buyuk_hub_n": N[i]}


def _yakin(a, b, tol=1e-7):
    if isinstance(a, dict):
        return isinstance(b, dict) and set(a) == set(b) and all(_yakin(a[k], b[k], tol) for k in a)
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(_yakin(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, (bool, str)) or a is None:
        return type(a) is type(b) and a == b
    return _sayi(a) and _sayi(b) and abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def _analiz(torch, V, ad):
    Z = torch.nn.functional.normalize(V, dim=1)
    C = Z @ Z.T
    iu = torch.triu_indices(len(Z), len(Z), 1)
    cs = C[iu[0], iu[1]]
    D = torch.cdist(V.unsqueeze(0), V.unsqueeze(0)).squeeze(0)
    D.fill_diagonal_(float("inf"))
    dmin = D.min(1).values
    D2 = D.clone()
    D2[torch.isinf(D2)] = 0
    dmax = D2.max(1).values
    Y = V - V.mean(0, keepdim=True)
    oz = torch.linalg.eigvalsh(Y.T @ Y / (len(V) - 1)).flip(0).clamp_min(0)
    oran = torch.cumsum(oz, 0) / oz.sum()
    n_bil = int((oran < AYAR["oran"]).sum()) + 1
    C2 = C.clone()
    C2.fill_diagonal_(-2)
    kom = C2.topk(AYAR["k"], dim=1).indices.tolist()
    return {"ad": ad, "kos_ort": float(cs.mean()), "kos_std": float(cs.std()), "kos_max": float(cs.max()), "goreli_kontrast": float(((dmax - dmin) / dmin).mean()), "bilesen_90": n_bil, "ilk_oran": float(oz[0] / oz.sum()), "ozdeger": float(oz[0])}, kom


def deney(kos_fn, pca_fn, hub_fn):
    try:
        import torch
    except ImportError as e:
        raise ai_lab.GercekLabYok(str(e)) from e
    rng = random.Random(secrets.randbits(64))
    tum = [(k, i, t, kal.format(ifade)) for k, ifadeler in KONULAR.items() for i, ifade in enumerate(ifadeler) for t, kal in enumerate(KALIPLAR)]
    secim = rng.sample(tum, AYAR["ornek"])
    metin = [s[3] for s in secim]
    with ai_lab.SohbetOturumu() as o:
        gom = _Gomucu(o.adres)
        V_l = gom(metin)
        ortam = dict(o.kayit)
    ortam["temizlik"] = o.kayit.get("temizlik")
    ortam["gomme"] = gom.kayit
    V = torch.tensor(V_l, dtype=torch.float64)
    norm = V.norm(dim=1)
    kos_ayni, kimlik_max, gruplar = True, 0.0, {"ayni_konu_farkli_kalip": [], "ayni_kalip_farkli_konu": [], "farkli": []}
    for _ in range(AYAR["cift"]):
        i, j = rng.sample(range(len(V_l)), 2)
        o_k = kos_fn(list(V_l[i]), list(V_l[j]))
        r_k = referans_kosinus(V_l[i], V_l[j])
        kos_ayni = kos_ayni and _yakin(o_k, r_k)
        kimlik_max = max(kimlik_max, r_k["kimlik_farki"])
        a, b = secim[i], secim[j]
        g = "ayni_konu_farkli_kalip" if a[0] == b[0] and a[2] != b[2] else "ayni_kalip_farkli_konu" if a[2] == b[2] and a[0] != b[0] else "farkli"
        if a[0] != b[0] and a[2] != b[2] or g != "farkli":
            gruplar[g].append(r_k["kosinus"])
    v0 = [rng.gauss(0, 1) for _ in range(len(V_l[0]))]
    o_p = pca_fn([list(s) for s in V_l], list(v0), AYAR["adim"])
    r_p = referans_pca(V_l, v0, AYAR["adim"])
    gen = torch.Generator().manual_seed(secrets.randbits(32))
    G = torch.randn(V.shape, generator=gen, dtype=torch.float64)
    G = G / G.norm(dim=1, keepdim=True)
    an_v, kom_v = _analiz(torch, V, "all-minilm")
    an_g, kom_g = _analiz(torch, G, "gaussian")
    r_h_v, r_h_g = referans_hubness(kom_v), referans_hubness(kom_g)
    o_h_v, o_h_g = hub_fn(copy.deepcopy(kom_v)), hub_fn(copy.deepcopy(kom_g))
    ozet = {k: {"adet": len(v), "ort": sum(v) / len(v) if v else None} for k, v in gruplar.items()}
    return {"model": GOMME_MODELI, "ortam": ortam, "surumler": {"torch": importlib.metadata.version("torch")}, "ayarlar": AYAR, "boyut": len(V_l[0]), "ornek": len(V_l), "norm_min": float(norm.min()), "norm_max": float(norm.max()),
            "kos_ayni": kos_ayni, "kimlik_max": kimlik_max, "gruplar": ozet, "pca": {k: v for k, v in r_p.items() if k != "bilesen"}, "pca_ayni": _yakin(o_p, r_p), "pca_eigh_fark": abs(r_p["ozdeger"] - an_v["ozdeger"]) / an_v["ozdeger"],
            "analiz": {"all-minilm": an_v, "gaussian": an_g}, "hub_ayni": _yakin(o_h_v, r_h_v) and _yakin(o_h_g, r_h_g), "hub": {"all-minilm": {k: v for k, v in r_h_v.items() if k != "n_k"}, "gaussian": {k: v for k, v in r_h_g.items() if k != "n_k"}}, "en_buyuk_hub_metin": metin[r_h_v["en_buyuk_hub"]],
            "olcum": "Cümleler sentetik şablondur. Gaussian taban aynı boyut ve örnek sayısında birim vektörlerdir.",
            "sinir": "Tek gömme modeli, küçük sentetik şablon derlemi; gerçek bir vektör veritabanının ya da başka bir modelin hubness değerini göstermez."}


def goster(kos_fn, pca_fn, hub_fn):
    r = deney(kos_fn, pca_fn, hub_fn)
    print("Model", r["model"], "boyut", r["boyut"], "örnek", r["ornek"], "norm %.4f-%.4f" % (r["norm_min"], r["norm_max"]), "kimlik farkı en çok %.2e" % r["kimlik_max"])
    print("Kosinüs ortalaması:", {k: None if v["ort"] is None else round(v["ort"], 3) for k, v in r["gruplar"].items()})
    print("PCA: ilk bileşen oranı %.3f | eigh ile göreli fark %.2e" % (r["pca"]["aciklanan_oran"], r["pca_eigh_fark"]))
    for ad in ("all-minilm", "gaussian"):
        a, h = r["analiz"][ad], r["hub"][ad]
        print("%-11s kos ort=%.3f std=%.3f | göreli kontrast=%.2f | %%90 için bileşen=%d | çarpıklık=%.2f anti-hub=%d en büyük N_k=%d" % (ad, a["kos_ort"], a["kos_std"], a["goreli_kontrast"], a["bilesen_90"], h["carpiklik"], h["anti_hub"], h["en_buyuk_hub_n"]))
    print("En büyük hub:", r["en_buyuk_hub_metin"])
    print("Sınır:", r["sinir"])
    print("Kanıt:", ai_lab.kanit_yaz("ai-guvence-38-run", {"kaynak": "gercek", "kabul": False, "ders": "ai-guvence-38", "deney": r}))
