"""Logit kırpma ve nicemleme savunması: gerçek SmolLM2-135M API'sinin log-olasılıklarında Carlini SVD saldırısının
(ai-saldiri-57) savunmadan önce ve sonra başarısı ölçülür."""
import importlib.metadata, math, random, secrets
import ai_lab

AYAR = {"seed": 40, "sorgu_sayisi": 700, "sutun_sayisi": 1024, "dizi_uzunlugu": 8, "k": 5, "taban_deger": -30.0,
        "adim_boyutu": 0.1, "gurultu_std": 0.02, "tekil_oran_esik": 0.65, "tol": 1e-5}


def _sayi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)


def referans_topk(logitler, k, taban_deger):
    if not isinstance(logitler, list) or len(logitler) < 2 or not all(_sayi(v) for v in logitler):
        raise ValueError("logitler")
    if isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= len(logitler):
        raise ValueError("k")
    if not _sayi(taban_deger):
        raise ValueError("taban_deger")
    secilen = set(sorted(range(len(logitler)), key=lambda i: (-logitler[i], i))[:k])
    return [float(v) if i in secilen else float(taban_deger) for i, v in enumerate(logitler)]


def referans_nicemle(logitler, adim_boyutu, gurultu_vektoru):
    if not isinstance(logitler, list) or not isinstance(gurultu_vektoru, list) or len(logitler) < 2 or len(logitler) != len(gurultu_vektoru):
        raise ValueError("boyut")
    if not all(_sayi(v) for v in logitler + gurultu_vektoru + [adim_boyutu]) or adim_boyutu <= 0:
        raise ValueError("sayı")
    return [round(round((a + g) / adim_boyutu) * adim_boyutu, 8) for a, g in zip(logitler, gurultu_vektoru)]


def referans_rapor(orijinal_logitler, korunan_logitler, tekil_oran_esik):
    if not isinstance(orijinal_logitler, list) or not isinstance(korunan_logitler, list) or len(orijinal_logitler) < 2 or len(orijinal_logitler) != len(korunan_logitler):
        raise ValueError("matris")
    if not _sayi(tekil_oran_esik) or not 0 < tekil_oran_esik <= 1:
        raise ValueError("esik")
    d = len(orijinal_logitler[0]) if isinstance(orijinal_logitler[0], list) else 0
    if d < 2:
        raise ValueError("sutun")
    for a, b in zip(orijinal_logitler, korunan_logitler):
        if not isinstance(a, list) or not isinstance(b, list) or len(a) != d or len(b) != d:
            raise ValueError("satir")
        if not all(_sayi(v) for v in a + b):
            raise ValueError("hucre")
    n = len(orijinal_logitler)
    korunan_say = 0
    l2_top = 0.0
    for a, b in zip(orijinal_logitler, korunan_logitler):
        ia = max(range(d), key=lambda j: a[j])
        ib = max(range(d), key=lambda j: b[j])
        if ia == ib:
            korunan_say += 1
        l2_top += math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
    ort_a = [sum(orijinal_logitler[i][j] for i in range(n)) / n for j in range(d)]
    ort_b = [sum(korunan_logitler[i][j] for i in range(n)) / n for j in range(d)]
    en_a = sum((orijinal_logitler[i][j] - ort_a[j]) ** 2 for i in range(n) for j in range(d))
    en_b = sum((korunan_logitler[i][j] - ort_b[j]) ** 2 for i in range(n) for j in range(d))
    oran = en_b / en_a if en_a > 1e-12 else 0.0
    ak = korunan_say / n
    return {
        "argmax_korunma": ak,
        "ortalama_l2_sapma": l2_top / n,
        "enerji_orani": oran,
        "savunma_basarili": bool(ak >= 0.8 and oran <= tekil_oran_esik)
    }


def _yakin(a, b, tol=1e-7):
    if isinstance(a, dict):
        return isinstance(b, dict) and set(a) == set(b) and all(_yakin(a[k], b[k], tol) for k in a)
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(_yakin(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, (bool, str)) or a is None:
        return type(a) is type(b) and a == b
    return _sayi(a) and _sayi(b) and abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def _api():
    """Gerçek SmolLM2-135M'i bir API gibi sorgular: rastgele kısa istemlere, sabit bir sütun alt kümesi üzerinde
    log-olasılık (log_softmax) döndürür. (torch, cihaz, matris[N, M], lm_head alt matrisi[M, gizli], model bilgisi)"""
    try:
        import torch
    except ImportError as e:
        raise ai_lab.GercekLabYok(str(e)) from e
    tok, model, bilgi = ai_lab.dil_modeli()
    cihaz = ai_lab.torch_cihazi()
    model.to(cihaz)
    gen = torch.Generator().manual_seed(AYAR["seed"])
    v = int(model.config.vocab_size)
    sorgular = torch.randint(0, v, (AYAR["sorgu_sayisi"], AYAR["dizi_uzunlugu"]), generator=gen)
    sutunlar = torch.randperm(v, generator=gen)[:AYAR["sutun_sayisi"]].to(cihaz)
    with torch.no_grad():
        Z = torch.cat([model(sorgular[i:i + 64].to(cihaz)).logits[:, -1, :].double()
                       for i in range(0, AYAR["sorgu_sayisi"], 64)])[:, sutunlar]
    W = model.lm_head.weight.detach().double()[sutunlar]
    return torch, cihaz, torch.log_softmax(Z, dim=1), W, model, bilgi


def _saldiri(torch, A, W, d_gercek):
    """ai-saldiri-57'deki saldırı: çift yönlü merkezleme + SVD; tahmini boyut, gerçek boyuttaki uçurum, altuzay kosinüsü."""
    A = A - A.mean(dim=1, keepdim=True)
    A = A - A.mean(dim=0, keepdim=True)
    _, s, Vh = torch.linalg.svd(A, full_matrices=False)
    d_tahmin = int((s > s[0] * AYAR["tol"]).sum())
    Q, _ = torch.linalg.qr(W - W.mean(dim=0, keepdim=True))
    kos = float(torch.linalg.svdvals(Q.T @ Vh[:d_gercek].T).min())
    return {"tahmini_boyut": d_tahmin, "ucurum_gercek_boyutta": float(s[d_gercek - 1] / max(float(s[d_gercek]), 1e-300)),
            "altuzay_kosinus_min": kos}


def deney(topk_fn, nicemle_fn, rapor_fn):
    torch, cihaz, Z, W, model, bilgi = _api()
    d_gercek = int(model.config.hidden_size)
    rng = random.Random(secrets.randbits(64))
    orijinal = Z.tolist()

    korunan = []
    topk_ayni = True
    nicemle_ayni = True
    for i, sat in enumerate(orijinal):
        g = [rng.gauss(0.0, AYAR["gurultu_std"]) for _ in sat]
        k_ogr = topk_fn(list(sat), AYAR["k"], AYAR["taban_deger"])
        k_ref = referans_topk(sat, AYAR["k"], AYAR["taban_deger"])
        topk_ayni = topk_ayni and _yakin(k_ogr, k_ref)
        n_ogr = nicemle_fn(list(k_ogr), AYAR["adim_boyutu"], list(g))
        n_ref = referans_nicemle(k_ref, AYAR["adim_boyutu"], g)
        nicemle_ayni = nicemle_ayni and _yakin(n_ogr, n_ref)
        korunan.append(n_ogr)

    K = torch.tensor(korunan, dtype=torch.float64, device=cihaz)
    once = _saldiri(torch, Z, W, d_gercek)
    sonra = _saldiri(torch, K, W, d_gercek)

    rapor_ogr = rapor_fn([list(s) for s in orijinal], [list(s) for s in korunan], AYAR["tekil_oran_esik"])
    rapor_ref = referans_rapor(orijinal, korunan, AYAR["tekil_oran_esik"])
    rapor_ayni = _yakin(rapor_ogr, rapor_ref)

    return {
        "cihaz": str(cihaz),
        "dtype": "float64 (model float32)",
        "model": {k: bilgi[k] for k in ("model", "revizyon", "agirlik_sha256", "parametre")},
        "surumler": {x: importlib.metadata.version(x) for x in ("torch", "transformers")},
        "ayarlar": AYAR,
        "gercek_gizli_boyut": d_gercek,
        "topk_ayni": topk_ayni,
        "nicemle_ayni": nicemle_ayni,
        "rapor_ayni": rapor_ayni,
        "rapor": rapor_ogr,
        "rapor_referans": rapor_ref,
        "saldiri_savunmasiz": once,
        "saldiri_savunmali": sonra,
        "olcum": (f"SmolLM2-135M API'si, {AYAR['sorgu_sayisi']} sorgu × {AYAR['sutun_sayisi']} sütun log-olasılık. Savunmasız: tahmini boyut "
                  f"{once['tahmini_boyut']} (gerçek {d_gercek}), {d_gercek}. tekil değerde uçurum {once['ucurum_gercek_boyutta']:.0f} kat, altuzay "
                  f"kosinüsü {once['altuzay_kosinus_min']:.4f}. Top-{AYAR['k']} + nicemleme sonrası: tahmini boyut {sonra['tahmini_boyut']}, uçurum "
                  f"{sonra['ucurum_gercek_boyutta']:.3f} kat, altuzay kosinüsü {sonra['altuzay_kosinus_min']:.4f}; argmax korunma "
                  f"{rapor_ref['argmax_korunma']:.3f}."),
        "sinir": "Top-k kırpma ve nicemleme bu tek seferlik SVD saldırısını bastırır; logit_bias ile k'yı kaydıran sorgular, yalnız etiketle yapılan "
                 "adaptif model kopyalama ve çok sayıda sorguyla gürültüyü ortalama yöntemlerini tek başına engellemez.",
    }


def goster(topk_fn, nicemle_fn, rapor_fn):
    r = deney(topk_fn, nicemle_fn, rapor_fn)
    print("Model", r["model"]["model"], "| cihaz", r["cihaz"], "| gerçek gizli boyut", r["gercek_gizli_boyut"])
    print("Saldırı, savunmasız:", r["saldiri_savunmasiz"])
    print("Saldırı, savunmalı :", r["saldiri_savunmali"])
    print("Savunma raporu:", r["rapor"])
    print("Sınır:", r["sinir"])
    print("Kanıt:", ai_lab.kanit_yaz("ai-savunma-40-run", {"kaynak": "gercek", "kabul": False, "ders": "ai-savunma-40", "deney": r}))
