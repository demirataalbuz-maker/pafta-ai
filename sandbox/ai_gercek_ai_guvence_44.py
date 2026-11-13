"""Gradyandan veri kurtarma (DLG) ve Byzantine-robust federe birleştirme (Krum ve Trimmed Mean): gerçek el yazısı rakam
görüntüsünün paylaşılan gradyandan geri kurtarılması ve 7 istemcili gerçek federe eğitimde Bizans saldırısı."""
import importlib.metadata, math, random, secrets
import ai_lab

AYAR = {"seed": 44, "gizli": 32, "dlg_adim": 300, "dlg_lr": 0.1, "istemci": 7, "bizans": 1, "kirpma_k": 1,
        "tur": 40, "yerel_batch": 64, "fl_lr": 1.0, "bizans_carpan": 10.0}


def _sayi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)


def referans_gradyan_kaybi(gercek_grad, sahte_grad):
    if not isinstance(gercek_grad, list) or not isinstance(sahte_grad, list) or not gercek_grad or len(gercek_grad) != len(sahte_grad):
        raise ValueError("gradyan")
    if not all(_sayi(v) for v in gercek_grad + sahte_grad):
        raise ValueError("sayı")
    ng = math.sqrt(sum(g * g for g in gercek_grad))
    ns = math.sqrt(sum(s * s for s in sahte_grad))
    if ng <= 0 or ns <= 0:
        raise ValueError("sıfır norm")
    l2 = sum((g - s) ** 2 for g, s in zip(gercek_grad, sahte_grad))
    kos = 1.0 - sum(g * s for g, s in zip(gercek_grad, sahte_grad)) / (ng * ns)
    return {"l2_fark": float(l2), "kosinus_uzaklik": float(kos)}


def referans_krum(istemci_gradyanlari, bizans_sayisi):
    if not isinstance(istemci_gradyanlari, list) or not istemci_gradyanlari:
        raise ValueError("liste")
    if isinstance(bizans_sayisi, bool) or not isinstance(bizans_sayisi, int) or bizans_sayisi < 0:
        raise ValueError("bizans")
    n = len(istemci_gradyanlari)
    if n < 2 * bizans_sayisi + 3:
        raise ValueError("n < 2f + 3")
    if not isinstance(istemci_gradyanlari[0], list) or not istemci_gradyanlari[0]:
        raise ValueError("vektör")
    d = len(istemci_gradyanlari[0])
    for g in istemci_gradyanlari:
        if not isinstance(g, list) or len(g) != d or not all(_sayi(v) for v in g):
            raise ValueError("eleman")
    komsular = n - bizans_sayisi - 2
    skorlar = []
    for i in range(n):
        uzakliklar = []
        for j in range(n):
            if i != j:
                uzakliklar.append(sum((a - b) ** 2 for a, b in zip(istemci_gradyanlari[i], istemci_gradyanlari[j])))
        uzakliklar.sort()
        skorlar.append(float(sum(uzakliklar[:komsular])))
    sec = min(range(n), key=lambda i: (skorlar[i], i))
    return {"secilen_indis": int(sec), "secilen_gradyan": [float(v) for v in istemci_gradyanlari[sec]], "skorlar": skorlar}


def referans_kirpilmis_ortalama(istemci_gradyanlari, kirpma_k):
    if not isinstance(istemci_gradyanlari, list) or not istemci_gradyanlari:
        raise ValueError("liste")
    if isinstance(kirpma_k, bool) or not isinstance(kirpma_k, int) or kirpma_k < 0:
        raise ValueError("kirpma_k")
    n = len(istemci_gradyanlari)
    if 2 * kirpma_k >= n:
        raise ValueError("2k >= n")
    if not isinstance(istemci_gradyanlari[0], list) or not istemci_gradyanlari[0]:
        raise ValueError("vektör")
    d = len(istemci_gradyanlari[0])
    for g in istemci_gradyanlari:
        if not isinstance(g, list) or len(g) != d or not all(_sayi(v) for v in g):
            raise ValueError("eleman")
    ortalama = []
    for j in range(d):
        s = sorted(g[j] for g in istemci_gradyanlari)[kirpma_k : n - kirpma_k]
        ortalama.append(float(sum(s) / len(s)))
    return ortalama


def _yakin(a, b, tol=1e-7):
    if isinstance(a, dict):
        return isinstance(b, dict) and set(a) == set(b) and all(_yakin(a[k], b[k], tol) for k in a)
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(_yakin(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, (bool, str, int)) or a is None:
        return type(a) is type(b) and a == b
    return _sayi(a) and _sayi(b) and abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def deney(kayip_fn, krum_fn, kirp_fn):
    try:
        import torch
        from sklearn.datasets import load_digits
    except ImportError as e:
        raise ai_lab.GercekLabYok(str(e)) from e
    cihaz = ai_lab.torch_cihazi()
    seed = AYAR["seed"] + secrets.randbelow(500)
    torch.manual_seed(seed)
    v = load_digits()
    karis = torch.randperm(len(v.target), generator=torch.Generator().manual_seed(seed))
    X = torch.tensor(v.data / 16.0, dtype=torch.float32)[karis].to(cihaz)
    Y = torch.tensor(v.target, dtype=torch.long)[karis].to(cihaz)
    X_eg, Y_eg, X_te, Y_te = X[:1400], Y[:1400], X[1400:], Y[1400:]

    def mlp():
        return torch.nn.Sequential(torch.nn.Linear(64, AYAR["gizli"]), torch.nn.Sigmoid(), torch.nn.Linear(AYAR["gizli"], 10)).to(cihaz)

    # Kurtarılan görüntüleri değerlendirmek için ayrı eğitilmiş bağımsız bir rakam sınıflandırıcısı
    hakem = mlp()
    opt_h = torch.optim.Adam(hakem.parameters(), lr=0.02)
    for _ in range(300):
        opt_h.zero_grad()
        torch.nn.functional.cross_entropy(hakem(X_eg), Y_eg).backward()
        opt_h.step()

    # 1. Bölüm: Deep Leakage from Gradients — istemcinin gerçek rakam görüntüsü, paylaştığı gradyandan geri kurtarılır
    net = mlp()
    gizli_x = X_te[:1]
    gizli_y = Y_te[:1]
    params = [p for p in net.parameters()]
    hedef_cikti = net(gizli_x)
    gercek_g_tuple = torch.autograd.grad(torch.nn.functional.cross_entropy(hedef_cikti, gizli_y), params)
    gercek_g_flat = torch.cat([g.detach().flatten() for g in gercek_g_tuple])

    sahte_x = torch.rand(1, 64, dtype=torch.float32, device=cihaz, requires_grad=True)
    opt_dlg = torch.optim.Adam([sahte_x], lr=AYAR["dlg_lr"])
    ilk_g_flat = None
    for s in range(AYAR["dlg_adim"]):
        opt_dlg.zero_grad()
        sahte_g_tuple = torch.autograd.grad(torch.nn.functional.cross_entropy(net(sahte_x), gizli_y), params, create_graph=True)
        sahte_g_flat = torch.cat([g.flatten() for g in sahte_g_tuple])
        if s == 0:
            ilk_g_flat = sahte_g_flat.detach().clone()
        dlg_kayip = ((sahte_g_flat - gercek_g_flat) ** 2).sum()
        dlg_kayip.backward()
        opt_dlg.step()
        with torch.no_grad():
            sahte_x.clamp_(0.0, 1.0)
    son_g_tuple = torch.autograd.grad(torch.nn.functional.cross_entropy(net(sahte_x), gizli_y), params)
    son_g_flat = torch.cat([g.detach().flatten() for g in son_g_tuple])
    kurtarma_mse = float(((sahte_x.detach() - gizli_x) ** 2).mean().item())
    with torch.no_grad():
        a, b = sahte_x.detach().flatten(), gizli_x.flatten()
        kurtarma_korelasyon = float(((a - a.mean()) * (b - b.mean())).sum() / ((a - a.mean()).norm() * (b - b.mean()).norm() + 1e-12))
        hakem_tahmini = int(hakem(sahte_x.detach()).argmax(1))
        rastgele_mse = float(((torch.rand_like(gizli_x) - gizli_x) ** 2).mean())

    def ascii(x):
        k = " .:-=+*#%@"
        x = x.detach().flatten().tolist()
        return ["".join(k[min(9, int(x[r * 8 + c] * 9.99))] for c in range(8)) for r in range(8)]

    g_gercek_l = gercek_g_flat.double().tolist()
    g_ilk_l = ilk_g_flat.double().tolist()
    g_son_l = son_g_flat.double().tolist()
    kayip_ilk_ref = referans_gradyan_kaybi(g_gercek_l, g_ilk_l)
    kayip_son_ref = referans_gradyan_kaybi(g_gercek_l, g_son_l)
    kayip_ayni = (
        _yakin(kayip_fn(list(g_gercek_l), list(g_ilk_l)), kayip_ilk_ref)
        and _yakin(kayip_fn(list(g_gercek_l), list(g_son_l)), kayip_son_ref)
    )

    # 2. Bölüm: Federe öğrenme — 7 istemci gerçek veri parçalarıyla küresel modeli eğitir; 1 istemci Bizans saldırganıdır
    n_ist, f = AYAR["istemci"], AYAR["bizans"]
    parca = X_eg.shape[0] // n_ist
    parcalar = [(X_eg[i * parca:(i + 1) * parca], Y_eg[i * parca:(i + 1) * parca]) for i in range(n_ist)]

    def yerel_gradyan(model, i):
        xb, yb = parcalar[i]
        sec = torch.randint(0, xb.shape[0], (AYAR["yerel_batch"],), device=cihaz)
        g = torch.autograd.grad(torch.nn.functional.cross_entropy(model(xb[sec]), yb[sec]), list(model.parameters()))
        return torch.cat([t.flatten() for t in g])

    def topla(G, kural):
        if kural == "fedavg":
            return G.mean(0)
        if kural == "krum":
            D = torch.cdist(G.double(), G.double()) ** 2
            D.fill_diagonal_(float("inf"))
            skor = D.sort(1).values[:, :G.shape[0] - f - 2].sum(1)
            return G[int(skor.argmin())]
        return G.sort(0).values[AYAR["kirpma_k"]:G.shape[0] - AYAR["kirpma_k"]].mean(0)   # kırpılmış ortalama

    def egit(kural, saldiri, ilk_tur_kayit=None):
        torch.manual_seed(seed + 1)
        model = mlp()
        for tur in range(AYAR["tur"]):
            G = torch.stack([yerel_gradyan(model, i) for i in range(n_ist)])
            if saldiri:
                G[-1] = -AYAR["bizans_carpan"] * G[:-1].mean(0)   # zıt yönde, büyütülmüş gradyan
            if tur == 0 and ilk_tur_kayit is not None:
                ilk_tur_kayit.extend(G.double().tolist())
            g = topla(G, kural)
            with torch.no_grad():
                i = 0
                for p in model.parameters():
                    p -= AYAR["fl_lr"] * g[i:i + p.numel()].view_as(p)
                    i += p.numel()
        with torch.no_grad():
            return float((model(X_te).argmax(1) == Y_te).float().mean())

    ilk_tur = []
    fl = {"temiz_fedavg": egit("fedavg", False), "saldiri_fedavg": egit("fedavg", True, ilk_tur),
          "saldiri_krum": egit("krum", True), "saldiri_kirpilmis": egit("kirpilmis", True)}

    # Öğrencinin işlevleri, saldırılı ilk turun gerçek istemci gradyanlarında bağımsız referansla karşılaştırılır
    tum_gradlar = ilk_tur
    durust_ort = [sum(g[j] for g in tum_gradlar[:-1]) / (n_ist - 1) for j in range(len(tum_gradlar[0]))]
    fedavg_grad = [sum(g[j] for g in tum_gradlar) / n_ist for j in range(len(tum_gradlar[0]))]
    krum_ref = referans_krum(tum_gradlar, f)
    krum_ayni = _yakin(krum_fn([list(g) for g in tum_gradlar], f), krum_ref)
    kirp_ref = referans_kirpilmis_ortalama(tum_gradlar, AYAR["kirpma_k"])
    kirp_ayni = _yakin(kirp_fn([list(g) for g in tum_gradlar], AYAR["kirpma_k"]), kirp_ref)

    sapma_fedavg = math.sqrt(sum((a - b) ** 2 for a, b in zip(fedavg_grad, durust_ort)))
    sapma_krum = math.sqrt(sum((a - b) ** 2 for a, b in zip(krum_ref["secilen_gradyan"], durust_ort)))
    sapma_kirp = math.sqrt(sum((a - b) ** 2 for a, b in zip(kirp_ref, durust_ort)))

    return {
        "cihaz": str(cihaz), "dtype": "float32 (sözleşme hesapları float64)",
        "surumler": {x: importlib.metadata.version(x) for x in ("torch", "scikit-learn")},
        "ayarlar": AYAR, "seed": seed,
        "kayip_ayni": kayip_ayni, "krum_ayni": krum_ayni, "kirp_ayni": kirp_ayni,
        "dlg_ilk_kayip": kayip_ilk_ref, "dlg_son_kayip": kayip_son_ref, "kurtarma_mse": kurtarma_mse,
        "rastgele_goruntu_mse": rastgele_mse, "kurtarma_korelasyon": kurtarma_korelasyon,
        "gizli_rakam": int(gizli_y), "hakem_tahmini": hakem_tahmini, "rakam_kurtarildi": hakem_tahmini == int(gizli_y),
        "gizli_goruntu": ascii(gizli_x), "kurtarilan_goruntu": ascii(sahte_x),
        "krum_secilen_indis": krum_ref["secilen_indis"], "bizans_indis": n_ist - 1,
        "sapma_fedavg": sapma_fedavg, "sapma_krum": sapma_krum, "sapma_kirpilmis": sapma_kirp,
        "federe_test_dogrulugu": fl,
        "olcum": (f"DLG: gerçek bir '{int(gizli_y)}' rakam görüntüsünün gradyanından kurtarma — gradyan L2 farkı "
                  f"{kayip_ilk_ref['l2_fark']:.4g} → {kayip_son_ref['l2_fark']:.3g}, piksel MSE {kurtarma_mse:.4f} (rastgele görüntü "
                  f"{rastgele_mse:.4f}), korelasyon {kurtarma_korelasyon:.3f}; bağımsız sınıflandırıcı kurtarılanı '{hakem_tahmini}' gördü. "
                  f"Federe ({n_ist} istemci, {AYAR['tur']} tur, 1 Bizans istemcisi −{AYAR['bizans_carpan']}× gradyan): test doğruluğu {fl}. "
                  f"İlk turda dürüst ortalamaya uzaklık FedAvg {sapma_fedavg:.3f}, Krum {sapma_krum:.3f}, kırpılmış {sapma_kirp:.3f}."),
        "sinir": ("8x8 rakamlar ve küçük bir sigmoid MLP; DLG tek örnekli batch ve bilinen etiketle yapılır (büyük batch, ReLU ağları ve "
                  "diferansiyel gizlilik kurtarmayı zorlaştırır). Federe kısımda tek ve kaba bir Bizans saldırısı vardır; saldırganın "
                  "Krum'u atlatmak için dürüst gradyanlara yakın kalan uyarlanabilir saldırıları (ör. ALIE) ölçülmez.")
    }


def goster(kayip_fn, krum_fn, kirp_fn):
    r = deney(kayip_fn, krum_fn, kirp_fn)
    print("Cihaz:", r["cihaz"], "| Tohum:", r["seed"])
    print("DLG gradyan L2 farkı: başlangıç=%.4f -> son=%.6f | piksel MSE=%.5f (rastgele %.5f) | korelasyon=%.3f" % (
        r["dlg_ilk_kayip"]["l2_fark"], r["dlg_son_kayip"]["l2_fark"], r["kurtarma_mse"], r["rastgele_goruntu_mse"], r["kurtarma_korelasyon"]))
    print("Gizli rakam:", r["gizli_rakam"], "| bağımsız sınıflandırıcı kurtarılanı:", r["hakem_tahmini"])
    for a, b in zip(r["gizli_goruntu"], r["kurtarilan_goruntu"]):
        print("   ", a, "   |   ", b)
    print("Federe sapma (ilk tur, dürüst ortalamaya L2): FedAvg=%.3f | Krum=%.4f (indis=%d) | Kırpılmış=%.4f" % (
        r["sapma_fedavg"], r["sapma_krum"], r["krum_secilen_indis"], r["sapma_kirpilmis"]))
    print("Federe test doğrulukları:", r["federe_test_dogrulugu"])
    print("Sınır:", r["sinir"])
    print("Kanıt:", ai_lab.kanit_yaz("ai-guvence-44-run", {"kaynak": "gercek", "kabul": False, "ders": "ai-guvence-44", "deney": r}))
