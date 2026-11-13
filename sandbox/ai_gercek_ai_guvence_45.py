"""Görüntü stil koruması (style cloaking) ve doğrusal kavram silme (concept erasure / nullspace projection)."""
import importlib.metadata, math, random, secrets
import ai_lab

AYAR = {"seed": 45, "gizli": 24, "adim_mlp": 220, "lr": 0.015, "ornek": 48, "eps": 0.15, "cloak_adim": 25, "cloak_lr": 0.04, "artik_esik": 1e-6,
        "sonda_adim": 300}


def _sayi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)


def referans_kavram_sil(vektor, kavram_yonu):
    if not isinstance(vektor, list) or not isinstance(kavram_yonu, list) or not vektor or len(vektor) != len(kavram_yonu):
        raise ValueError("vektör")
    if not all(_sayi(v) for v in vektor + kavram_yonu):
        raise ValueError("sayı")
    cc = sum(c * c for c in kavram_yonu)
    if cc <= 0:
        raise ValueError("sıfır norm")
    alfa = sum(v * c for v, c in zip(vektor, kavram_yonu)) / cc
    return [float(v - alfa * c) for v, c in zip(vektor, kavram_yonu)]


def referans_stil_kaydirma(orijinal_ozellik, gizlenmis_ozellik, hedef_stil_yonu):
    if not isinstance(orijinal_ozellik, list) or not isinstance(gizlenmis_ozellik, list) or not isinstance(hedef_stil_yonu, list):
        raise ValueError("liste")
    if not orijinal_ozellik or len(orijinal_ozellik) != len(gizlenmis_ozellik) or len(orijinal_ozellik) != len(hedef_stil_yonu):
        raise ValueError("uzunluk")
    if not all(_sayi(v) for v in orijinal_ozellik + gizlenmis_ozellik + hedef_stil_yonu):
        raise ValueError("sayı")
    no = math.sqrt(sum(v * v for v in orijinal_ozellik))
    ng = math.sqrt(sum(v * v for v in gizlenmis_ozellik))
    nh = math.sqrt(sum(v * v for v in hedef_stil_yonu))
    if no <= 0 or ng <= 0 or nh <= 0:
        raise ValueError("sıfır norm")
    k_once = sum(a * b for a, b in zip(orijinal_ozellik, hedef_stil_yonu)) / (no * nh)
    k_sonra = sum(a * b for a, b in zip(gizlenmis_ozellik, hedef_stil_yonu)) / (ng * nh)
    l2 = math.sqrt(sum((a - b) ** 2 for a, b in zip(orijinal_ozellik, gizlenmis_ozellik)))
    return {"onceki_kosinus": float(k_once), "sonraki_kosinus": float(k_sonra), "kayma_miktari": float(k_sonra - k_once), "ozellik_l2": float(l2)}


def referans_silme_raporu(onceki_vektorler, sonraki_vektorler, kavram_yonu, artik_esik):
    if not isinstance(onceki_vektorler, list) or not isinstance(sonraki_vektorler, list) or not isinstance(kavram_yonu, list):
        raise ValueError("liste")
    if not onceki_vektorler or len(onceki_vektorler) != len(sonraki_vektorler) or not kavram_yonu:
        raise ValueError("uzunluk")
    if not _sayi(artik_esik) or artik_esik < 0 or not all(_sayi(c) for c in kavram_yonu):
        raise ValueError("ayar")
    nc = math.sqrt(sum(c * c for c in kavram_yonu))
    if nc <= 0:
        raise ValueError("sıfır norm")
    d = len(kavram_yonu)
    for v, w in zip(onceki_vektorler, sonraki_vektorler):
        if not isinstance(v, list) or not isinstance(w, list) or len(v) != d or len(w) != d or not all(_sayi(x) for x in v + w):
            raise ValueError("eleman")
    c_birim = [c / nc for c in kavram_yonu]
    iz_once = [abs(sum(v * u for v, u in zip(vec, c_birim))) for vec in onceki_vektorler]
    iz_sonra = [abs(sum(w * u for w, u in zip(vec, c_birim))) for vec in sonraki_vektorler]
    l2_liste = [math.sqrt(sum((a - b) ** 2 for a, b in zip(v, w))) for v, w in zip(onceki_vektorler, sonraki_vektorler)]
    max_artik = float(max(iz_sonra))
    return {
        "onceki_ort_iz": float(sum(iz_once) / len(iz_once)),
        "sonraki_ort_iz": float(sum(iz_sonra) / len(iz_sonra)),
        "max_artik_iz": max_artik,
        "ort_koruma_l2": float(sum(l2_liste) / len(l2_liste)),
        "tam_silindi": bool(max_artik <= artik_esik)
    }


def _yakin(a, b, tol=1e-7):
    if isinstance(a, dict):
        return isinstance(b, dict) and set(a) == set(b) and all(_yakin(a[k], b[k], tol) for k in a)
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(_yakin(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, (bool, str, int)) or a is None:
        return type(a) is type(b) and a == b
    return _sayi(a) and _sayi(b) and abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def deney(sil_fn, stil_fn, rapor_fn):
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
    enc = torch.nn.Sequential(torch.nn.Linear(64, AYAR["gizli"]), torch.nn.ReLU()).to(cihaz)
    baslik = torch.nn.Linear(AYAR["gizli"], 10).to(cihaz)
    opt = torch.optim.Adam(list(enc.parameters()) + list(baslik.parameters()), lr=AYAR["lr"])
    for _ in range(AYAR["adim_mlp"]):
        opt.zero_grad()
        torch.nn.functional.cross_entropy(baslik(enc(X[:1300])), Y[:1300]).backward()
        opt.step()
    rng = random.Random(secrets.randbits(64))
    secim = rng.sample(range(1300, len(X)), AYAR["ornek"])
    X_sec = X[secim]
    with torch.no_grad():
        H_tr = enc(X[:1300])
        # Sınıf 0 ve sınıf 1 merkezleri arasındaki farkı kavram/hedef stil yönü olarak al
        m0 = H_tr[Y[:1300] == 0].mean(dim=0)
        m1 = H_tr[Y[:1300] == 1].mean(dim=0)
        kavram_t = (m0 - m1)
        hedef_stil_t = m1

    # Style cloaking: girdi görüntülerine L_inf <= eps pertürbasyon ekleyerek özellikleri hedef_stil_t yönüne çek
    delta = torch.zeros_like(X_sec, requires_grad=True)
    opt_c = torch.optim.Adam([delta], lr=AYAR["cloak_lr"])
    hedef_norm = hedef_stil_t / hedef_stil_t.norm().clamp_min(1e-8)
    for _ in range(AYAR["cloak_adim"]):
        opt_c.zero_grad()
        x_adv = (X_sec + delta.clamp(-AYAR["eps"], AYAR["eps"])).clamp(0.0, 1.0)
        h_adv = enc(x_adv)
        h_norm = h_adv / h_adv.norm(dim=1, keepdim=True).clamp_min(1e-8)
        kayip_c = -(h_norm @ hedef_norm).mean()
        kayip_c.backward()
        opt_c.step()
        with torch.no_grad():
            delta.clamp_(-AYAR["eps"], AYAR["eps"])
    with torch.no_grad():
        X_gizli = (X_sec + delta).clamp(0.0, 1.0)
        H_once = enc(X_sec).double().tolist()
        H_gizli = enc(X_gizli).double().tolist()
        kavram_y = kavram_t.double().tolist()
        hedef_y = hedef_stil_t.double().tolist()

    sil_ref = [referans_kavram_sil(h, kavram_y) for h in H_once]
    sil_ogr = [sil_fn(list(h), list(kavram_y)) for h in H_once]
    sil_ayni = _yakin(sil_ogr, sil_ref)

    stil_ayni = True
    kaymalar = []
    for h_o, h_g in zip(H_once, H_gizli):
        sr = referans_stil_kaydirma(h_o, h_g, hedef_y)
        so = stil_fn(list(h_o), list(h_g), list(hedef_y))
        stil_ayni = stil_ayni and _yakin(so, sr)
        kaymalar.append(sr["kayma_miktari"])

    rapor_ref = referans_silme_raporu(H_once, sil_ref, kavram_y, AYAR["artik_esik"])
    rapor_ogr = rapor_fn([list(h) for h in H_once], [list(s) for s in sil_ref], list(kavram_y), AYAR["artik_esik"])
    rapor_ayni = _yakin(rapor_ogr, rapor_ref)

    # Davranış ölçümleri
    Y_sec = Y[secim]
    with torch.no_grad():
        # (1) Gizleme: orijinal sınıflandırıcı gizlenmiş görüntüleri hedef stile (sınıf 1) kaydırıyor mu?
        once_1 = baslik(enc(X_sec)).argmax(1)
        sonra_1 = baslik(enc(X_gizli)).argmax(1)
        bir_degil = Y_sec != 1
        hedefe_kayan = float(((sonra_1 == 1) & bir_degil).float().sum() / bir_degil.float().sum().clamp_min(1))
        hedefe_once = float(((once_1 == 1) & bir_degil).float().sum() / bir_degil.float().sum().clamp_min(1))
        dogru_once = float((once_1 == Y_sec).float().mean())
        dogru_sonra = float((sonra_1 == Y_sec).float().mean())
    # (1b) Arındırma: saldırgan (taklitçi) gizlenmiş görüntüyü basit işlemlerden geçirir; gizleme etkisi kalıyor mu? (Hönig vd. 2024)
    def bulanik(x):
        k = torch.tensor([[1., 2., 1.], [2., 4., 2.], [1., 2., 1.]], device=cihaz) / 16.0
        return torch.nn.functional.conv2d(x.view(-1, 1, 8, 8), k.view(1, 1, 3, 3), padding=1).view(-1, 64)

    def nicemle(x):
        return torch.round(x * 16.0) / 16.0

    def olcekle(x):
        k = torch.nn.functional.interpolate(x.view(-1, 1, 8, 8), size=(4, 4), mode="bilinear", align_corners=False)
        return torch.nn.functional.interpolate(k, size=(8, 8), mode="bilinear", align_corners=False).view(-1, 64)
    arindirma = {}

    def kayma(hg, ht):
        """Gizlenmiş ve temiz görüntünün özelliklerinin hedef stil yönüne kosinüs farkı (ortalama)."""
        hn = hedef_stil_t / hedef_stil_t.norm()
        return float((torch.nn.functional.normalize(hg, dim=1) @ hn - torch.nn.functional.normalize(ht, dim=1) @ hn).mean())
    with torch.no_grad():
        ilk_kayma = kayma(enc(X_gizli), enc(X_sec))
        for ad, f in (("bulaniklastirma", bulanik), ("nicemleme_1_16", nicemle), ("kucult_buyut", olcekle)):
            tah_g, tah_t = baslik(enc(f(X_gizli))).argmax(1), baslik(enc(f(X_sec))).argmax(1)
            arindirma[ad] = {"kalan_kayma_orani": kayma(enc(f(X_gizli)), enc(f(X_sec))) / max(ilk_kayma, 1e-9),
                             "gizli_dogruluk": float((tah_g == Y_sec).float().mean()), "temiz_dogruluk": float((tah_t == Y_sec).float().mean())}
    en_iyi = min(arindirma, key=lambda a: arindirma[a]["kalan_kayma_orani"])
    # (2) Temsil uzayında silme sonrası kavram geri okunabiliyor mu? 0/1 ayrımı için yeni sondalar eğitilir.
    u = kavram_t / kavram_t.norm()

    def sil(H):
        return H - (H @ u).unsqueeze(1) * u

    with torch.no_grad():
        H_all = enc(X)
    ikili = (Y == 0) | (Y == 1)
    egit_m = ikili.clone()
    egit_m[1300:] = False
    test_m = ikili.clone()
    test_m[:1300] = False

    def sonda(H, dogrusal):
        g = torch.Generator().manual_seed(seed)
        d = H.shape[1]
        if dogrusal:
            m = torch.nn.Linear(d, 2)
        else:
            m = torch.nn.Sequential(torch.nn.Linear(d, 64), torch.nn.ReLU(), torch.nn.Linear(64, 2))
        for p in m.parameters():
            with torch.no_grad():
                p.copy_(torch.randn(p.shape, generator=g) * 0.1)
        m = m.to(cihaz)
        o = torch.optim.Adam(m.parameters(), lr=0.01)
        for _ in range(AYAR["sonda_adim"]):
            o.zero_grad()
            torch.nn.functional.cross_entropy(m(H[egit_m]), Y[egit_m]).backward()
            o.step()
        with torch.no_grad():
            return float((m(H[test_m]).argmax(1) == Y[test_m]).float().mean())

    sonda_sonuc = {"dogrusal_once": sonda(H_all, True), "dogrusal_sonra": sonda(sil(H_all), True),
                   "mlp_sonra": sonda(sil(H_all), False)}
    # (3) Ağırlık projeksiyonuyla silme: sınıflandırıcı başlığının ağırlıkları kavram yönüne dik hâle getirilir (W ← W(I − uuᵀ))
    with torch.no_grad():
        W_eski = baslik.weight.clone()
        baslik.weight.copy_(W_eski - (W_eski @ u).unsqueeze(1) * u)
        tahmin = baslik(H_all[1300:]).argmax(1)
        Yt = Y[1300:]
        m01 = (Yt == 0) | (Yt == 1)
        agirlik_sonra = {"0_1_dogrulugu": float((tahmin[m01] == Yt[m01]).float().mean()),
                         "diger_rakamlar": float((tahmin[~m01] == Yt[~m01]).float().mean())}
        baslik.weight.copy_(W_eski)
        tahmin0 = baslik(H_all[1300:]).argmax(1)
        agirlik_once = {"0_1_dogrulugu": float((tahmin0[m01] == Yt[m01]).float().mean()),
                        "diger_rakamlar": float((tahmin0[~m01] == Yt[~m01]).float().mean())}

    return {
        "cihaz": str(cihaz), "dtype": "float32",
        "surumler": {x: importlib.metadata.version(x) for x in ("torch", "scikit-learn")},
        "ayarlar": AYAR, "seed": seed, "secim": secim,
        "sil_ayni": sil_ayni, "stil_ayni": stil_ayni, "rapor_ayni": rapor_ayni,
        "ort_stil_kaymasi": sum(kaymalar) / len(kaymalar),
        "silme_raporu": rapor_ref,
        "linf_max": float((X_gizli - X_sec).abs().max().item()),
        "gizleme_davranisi": {"hedef_sinifa_kayan_once": hedefe_once, "hedef_sinifa_kayan_sonra": hedefe_kayan,
                              "dogruluk_once": dogru_once, "dogruluk_sonra": dogru_sonra},
        "silme_sondalari": sonda_sonuc,
        "arindirma": arindirma, "en_iyi_arindirma": en_iyi,
        "ilk_kayma": ilk_kayma,
        "arindirma_odunlesimi": bool(ilk_kayma > 0 and arindirma[en_iyi]["kalan_kayma_orani"] <= 0.5
                                     and arindirma[en_iyi]["temiz_dogruluk"] <= dogru_once - 0.15
                                     and arindirma["nicemleme_1_16"]["kalan_kayma_orani"] >= 0.7),
        "agirlik_projeksiyonu": {"once": agirlik_once, "sonra": agirlik_sonra},
        "olcum": (f"{AYAR['ornek']} gerçek test görüntüsünde L∞ ≤ {AYAR['eps']} gizleme: sınıf-1 stil yönüne kosinüs kayması "
                  f"+{sum(kaymalar) / len(kaymalar):.3f}; orijinal sınıflandırıcı 1 olmayan görüntülerin {hedefe_once:.2f} → {hedefe_kayan:.2f}'ini "
                  f"'1' gördü, doğruluk {dogru_once:.2f} → {dogru_sonra:.2f}. Temsil uzayında 0/1 kavram yönü silindi (artık iz "
                  f"{rapor_ref['max_artik_iz']:.1e}); yeni sondaların 0/1 ayrımı: doğrusal {sonda_sonuc['dogrusal_once']:.3f} → "
                  f"{sonda_sonuc['dogrusal_sonra']:.3f}, MLP sonda silmeden sonra {sonda_sonuc['mlp_sonra']:.3f}. Ağırlık projeksiyonu "
                  f"(başlık W(I−uuᵀ)): 0/1 doğruluğu {agirlik_once['0_1_dogrulugu']:.3f} → {agirlik_sonra['0_1_dogrulugu']:.3f}, diğer rakamlar "
                  f"{agirlik_once['diger_rakamlar']:.3f} → {agirlik_sonra['diger_rakamlar']:.3f}. Arındırma (gizlemenin özellik kaymasının kalan "
                  f"oranı / gizli doğruluk / temiz doğruluk): " + "; ".join(f"{a} {v['kalan_kayma_orani']:.2f} / {v['gizli_dogruluk']:.2f} / {v['temiz_dogruluk']:.2f}"
                                                                           for a, v in arindirma.items()) + "."),
        "sinir": ("8x8 rakamlar ve küçük bir MLP kullanılır; difüzyon modeli ve gerçek sanat stili yoktur. Gizleme bütçesi (L∞ 0.15) gerçek "
                  "Glaze/Nightshade bütçelerinden büyüktür ve bu çözünürlükte gözle görülebilir. Silme, tek bir doğrusal kavram yönünü "
                  "(sınıf 0 ve 1 ortalamaları farkı) kaldırır; doğrusal olmayan sondalar ve başka yönler kavramı yeniden okuyabilir. Arındırma "
                  "deneyi basit işlemlerle 8x8 görüntülerde yapılır; bu çözünürlükte gizlemeyi silen işlem içeriği de bozar. Yüksek çözünürlüklü "
                  "gerçek sanat eserlerinde gürültü ekleyip yeniden üretme gibi arındırmalar içeriği koruyarak korumayı büyük ölçüde kaldırır (Hönig vd. 2024).")
    }


def goster(sil_fn, stil_fn, rapor_fn):
    r = deney(sil_fn, stil_fn, rapor_fn)
    print("Cihaz:", r["cihaz"], "| L_inf max pertürbasyon:", round(r["linf_max"], 4))
    print("Style cloaking ortalama kosinüs kayması: +%.4f" % r["ort_stil_kaymasi"])
    print("Concept erasure raporu:", r["silme_raporu"])
    print("Gizleme davranışı:", {k: round(v, 3) for k, v in r["gizleme_davranisi"].items()})
    print("Silme sonrası sondalar (0/1 ayrımı):", {k: round(v, 3) for k, v in r["silme_sondalari"].items()})
    print("Ağırlık projeksiyonu:", r["agirlik_projeksiyonu"])
    print("Sınır:", r["sinir"])
    print("Kanıt:", ai_lab.kanit_yaz("ai-guvence-45-run", {"kaynak": "gercek", "kabul": False, "ders": "ai-guvence-45", "deney": r}))
