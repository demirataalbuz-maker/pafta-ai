"""Mamba ve seçici durum uzayı modelleri (SSM): SmolLM2 gerçek token gömmeleriyle eğitilen seçici SSM'de ayrıklaştırma,
yineleme, büyük Δ tokeniyle bellek silme saldırısı (state collapse) ve Δ tavanı savunması."""
import importlib.metadata, math, random
import ai_lab

AYAR = {
    "seed": 30,
    "durum_boyutu": 8,
    "dolgu_uzunlugu": 24,
    "uretim": 160,
    "egitim_ornek": 512,
    "test_ornek": 128,
    "adim": 1200,
    "min_adim": 300,
    "egitim_kayip_hedef": 0.02,
    "lr": 0.01,
    "tavan_yuzdelik": 0.99,
    "ornek_sayisi": 32,
    "min_norm_oran": 0.05,
    "max_oran": 0.18,
    "mamba_katman": 12,
    "mamba_aday": 6000,
    "mamba_ekleme": 60,
}


def _sayi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)


def referans_ssm_ayriklastir(delta, a_diag, b_vektor):
    if not _sayi(delta) or delta <= 0.0:
        raise ValueError("delta")
    if not isinstance(a_diag, list) or not isinstance(b_vektor, list) or not a_diag or len(a_diag) != len(b_vektor):
        raise ValueError("boyut")
    for a, b in zip(a_diag, b_vektor):
        if not _sayi(a) or a >= 0.0 or not _sayi(b):
            raise ValueError("eleman")
    a_bar = [math.exp(delta * a) for a in a_diag]
    b_bar = [delta * b for b in b_vektor]
    return {
        "a_bar": a_bar,
        "b_bar": b_bar,
        "tutma_orani": sum(a_bar) / float(len(a_bar)),
    }


def referans_ssm_izle(a_bar_adimlar, b_bar_adimlar, x_adimlar):
    if not isinstance(a_bar_adimlar, list) or not isinstance(b_bar_adimlar, list) or not isinstance(x_adimlar, list):
        raise ValueError("liste")
    T = len(x_adimlar)
    if T < 1 or len(a_bar_adimlar) != T or len(b_bar_adimlar) != T:
        raise ValueError("zaman_boyut")
    N = None
    for t in range(T):
        ab, bb, x = a_bar_adimlar[t], b_bar_adimlar[t], x_adimlar[t]
        if not isinstance(ab, list) or not isinstance(bb, list) or not ab or len(ab) != len(bb):
            raise ValueError("durum_boyut")
        if N is not None and len(ab) != N:
            raise ValueError("n_farkli")
        N = len(ab)
        if not _sayi(x):
            raise ValueError("x_sayi")
        for a, b in zip(ab, bb):
            if not _sayi(a) or not 0.0 <= a <= 1.0 or not _sayi(b):
                raise ValueError("ab_bb_sayi")
    h = [0.0] * N
    normlar = []
    for t in range(T):
        ab, bb, x = a_bar_adimlar[t], b_bar_adimlar[t], x_adimlar[t]
        h = [ab[i] * h[i] + bb[i] * x for i in range(N)]
        normlar.append(math.sqrt(sum(v * v for v in h)))
    return {"son_durum": h, "norm_izleri": normlar}


def referans_cokme_tanisi(norm_izleri, tutma_orani_izleri, min_norm, max_oran):
    if not isinstance(norm_izleri, list) or not isinstance(tutma_orani_izleri, list) or not norm_izleri or len(norm_izleri) != len(tutma_orani_izleri):
        raise ValueError("iz_boyut")
    for n, r in zip(norm_izleri, tutma_orani_izleri):
        if not _sayi(n) or n < 0.0 or not _sayi(r) or not 0.0 <= r <= 1.0:
            raise ValueError("iz_deger")
    if not _sayi(min_norm) or min_norm <= 0.0 or not _sayi(max_oran) or not 0.0 < max_oran <= 1.0:
        raise ValueError("esik")
    adimlar = [t for t in range(len(norm_izleri)) if norm_izleri[t] < min_norm or tutma_orani_izleri[t] < max_oran]
    return {
        "cokme_adimlari": adimlar,
        "cokme_var": bool(adimlar),
        "en_dusuk_tutma": float(min(tutma_orani_izleri)),
    }


def _yakin(a, b, tol=1e-9):
    if isinstance(a, dict):
        return isinstance(b, dict) and set(a) == set(b) and all(_yakin(a[k], b[k], tol) for k in a)
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(_yakin(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, (bool, str)) or a is None:
        return type(a) is type(b) and a == b
    return _sayi(a) and _sayi(b) and abs(a - b) <= tol * max(1.0, abs(a), abs(b))


ANAHTARLAR = [" red", " blue", " green", " black"]
DOLGU_ISTEMLERI = ["The history of the old harbor town", "In the morning the farmers", "A short guide to keeping bees",
                   "The new library opened its doors", "Scientists studying the deep ocean", "When the train finally arrived"]


class SeciciSSM:
    """Tek kanallı seçici SSM (Mamba tarzı, köşegen A): Δ_t, B_t ve x_t gerçek SmolLM2 token gömmelerinden öğrenilir."""

    def __init__(self, torch, d, N, K, cihaz):
        t = self.t = torch
        g = torch.Generator().manual_seed(AYAR["seed"])
        s = 1.0 / math.sqrt(d)
        self.a = (-0.5 * torch.arange(1, N + 1, dtype=torch.float32)).to(cihaz)   # S4D-real başlangıcı, sabit
        self.w_dt = (torch.randn(d, generator=g) * s).to(cihaz).requires_grad_(True)
        self.b_dt = torch.tensor(math.log(math.expm1(0.05))).to(cihaz).requires_grad_(True)
        self.W_B = (torch.randn(d, N, generator=g) * s).to(cihaz).requires_grad_(True)
        self.w_x = (torch.randn(d, generator=g) * s).to(cihaz).requires_grad_(True)
        self.W_o = (torch.randn(N, K, generator=g) * 0.1).to(cihaz).requires_grad_(True)
        self.b_o = torch.zeros(K).to(cihaz).requires_grad_(True)

    def parametreler(self):
        return [self.w_dt, self.b_dt, self.W_B, self.w_x, self.W_o, self.b_o]

    def secim(self, e):
        """e: [..., d] gömme → (Δ, B, x)."""
        return self.t.nn.functional.softplus(e @ self.w_dt + self.b_dt), e @ self.W_B, e @ self.w_x

    def ileri(self, e, delta_tavan=None):
        """e: [M, T, d]. Döndürür: (sınıf logitleri, Δ [M, T], B [M, T, N], x [M, T])."""
        dlt, B, x = self.secim(e)
        if delta_tavan is not None:
            dlt = dlt.clamp(max=delta_tavan)
        h = self.t.zeros(e.shape[0], self.a.shape[0], device=e.device)
        for s in range(e.shape[1]):
            h = self.t.exp(dlt[:, s:s + 1] * self.a) * h + dlt[:, s:s + 1] * B[:, s] * x[:, s:s + 1]
        return h @ self.W_o + self.b_o, dlt, B, x


def _gercek_mamba(torch, ayrik_fn):
    """Ön eğitimli mamba-130m: bir katmanda her aday tokenın Δ'sı ve durum tutma oranı ölçülür; belleği en çok silen tokenlar
    parola hatırlama görevinde araya konur ve rastgele tokenlarla karşılaştırılır."""
    from sandbox import ai_uretim_ortak as O
    cihaz = ai_lab.torch_cihazi()
    tok, m = O.hf_model(O.MAMBA_MODEL, O.MAMBA_REVIZYON)
    kilit = ai_lab.gpu_kilidi_al() if cihaz == "cuda" else None
    try:
        m = m.to(cihaz)
        mikserler = [L.mixer for L in m.backbone.layers]
        mix = mikserler[AYAR["mamba_katman"]]
        A = -torch.exp(mix.A_log.float())                                              # (I, N)

        def _delta(mx, hs):
            T = hs.shape[1]
            Ax = -torch.exp(mx.A_log.float())
            x, _ = (hs @ mx.in_proj.weight.float().T).transpose(1, 2).chunk(2, dim=1)
            x = torch.nn.functional.silu(torch.nn.functional.conv1d(x, mx.conv1d.weight.float(), mx.conv1d.bias.float(),
                                                                    padding=mx.conv1d.padding[0], groups=x.shape[1])[..., :T])
            dt, Bm, _ = torch.split(x.transpose(1, 2) @ mx.x_proj.weight.float().T, [mx.time_step_rank, Ax.shape[1], Ax.shape[1]], dim=-1)
            return torch.nn.functional.softplus(dt @ mx.dt_proj.weight.float().T + mx.dt_proj.bias.float()), Bm, Ax

        def girdiler(ids):
            yak, kancalar = {}, []
            for j, mx in enumerate(mikserler):
                kancalar.append(mx.register_forward_pre_hook(lambda mod, a, j=j: yak.__setitem__(j, a[0].float())))
            try:
                with torch.no_grad():
                    m(ids)
            finally:
                for k in kancalar:
                    k.remove()
            return yak

        def delta_B(ids):
            with torch.no_grad():
                d, Bm, _ = _delta(mix, girdiler(ids)[AYAR["mamba_katman"]])
            return d, Bm
        on = tok("The weather today is", return_tensors="pt").input_ids.to(cihaz)
        g = torch.Generator().manual_seed(AYAR["seed"])
        adaylar = torch.randperm(len(tok), generator=g)[: AYAR["mamba_aday"]].tolist()
        uygun = [t for t in adaylar if tok.decode([t]).strip().isalpha()]
        tutma = []
        for i in range(0, len(uygun), 256):
            parca = torch.tensor(uygun[i:i + 256], device=cihaz)[:, None]
            yak = girdiler(torch.cat([on.expand(parca.shape[0], -1), parca], 1))
            with torch.no_grad():
                top = 0.0
                for j, mx in enumerate(mikserler):                                     # bütün katmanlarda son konumda ortalama exp(Δ·A)
                    d, _, Ax = _delta(mx, yak[j][:, -4:])
                    top = top + torch.exp(d[:, -1, :, None] * Ax[None]).mean((1, 2))
            tutma += (top / len(mikserler)).tolist()
        sira = sorted(range(len(uygun)), key=lambda i: tutma[i])
        silici = [uygun[i] for i in sira[:5]]
        rnd = random.Random(AYAR["seed"])
        rastgele = rnd.sample(uygun, 5)

        anahtar = "4821"
        giris = f"There is an important pass key hidden in this text. The pass key is {anahtar}. Remember it. {anahtar} is the pass key. "
        dolgu = "The grass is green. The sky is blue. The sun is yellow. Here we go. There and back again. "
        soru = " What is the pass key? The pass key is"

        def logp(ara):
            a = tok(giris + dolgu, return_tensors="pt").input_ids[0].tolist() + ara + tok(soru, add_special_tokens=False).input_ids
            c = tok(" " + anahtar, add_special_tokens=False).input_ids
            ids = torch.tensor([a + c], device=cihaz)
            with torch.no_grad():
                lp = torch.log_softmax(m(ids).logits[0, len(a) - 1:-1].float(), -1)
            return float(lp.gather(1, torch.tensor(c, device=cihaz)[:, None]).sum())
        n = AYAR["mamba_ekleme"]
        sonuc = {"eklemesiz": logp([]), "rastgele_tokenlar": logp([rastgele[i % 5] for i in range(n)]),
                 "silici_tokenlar": logp([silici[i % 5] for i in range(n)])}
        # Öğrencinin ayrıklaştırma işlevi gerçek Δ, A ve B ile (silici token konumunda, birkaç kanal)
        d, Bm = delta_B(torch.cat([on, torch.tensor([[silici[0]]], device=cihaz)], 1))
        ayni = True
        for c in (0, 100, 500, 1000, 1500):
            dl, ad, bv = float(d[0, -1, c]), A[c].double().tolist(), Bm[0, -1].double().tolist()
            ayni = ayni and _yakin(ayrik_fn(dl, list(ad), list(bv)), referans_ssm_ayriklastir(dl, ad, bv), 1e-7)
        m = m.to("cpu")
        if cihaz == "cuda":
            torch.cuda.empty_cache()
    finally:
        if kilit is not None:
            ai_lab.gpu_kilidi_birak()
    return {"model": O.MAMBA_MODEL, "katman": AYAR["mamba_katman"], "taranan_token": len(uygun),
            "silici": [[t, tok.decode([t]), round(tutma[uygun.index(t)], 4)] for t in silici],
            "rastgele": [[t, tok.decode([t]), round(tutma[uygun.index(t)], 4)] for t in rastgele],
            "ortanca_tutma": round(sorted(tutma)[len(tutma) // 2], 4), "eklenen_token": n, "anahtar_logp": sonuc, "ayrik_ayni": ayni}


def deney(ayrik_fn, izle_fn, tani_fn):
    try:
        import torch
    except ImportError as e:
        raise ai_lab.GercekLabYok(str(e)) from e
    tok, model, bilgi = ai_lab.dil_modeli()
    cihaz = ai_lab.torch_cihazi()
    model.to(cihaz)
    torch.manual_seed(AYAR["seed"])  # Kanıttaki seed ile aynı: başarısız koşu yeniden üretilebilir.
    N, L, K = AYAR["durum_boyutu"], AYAR["dolgu_uzunlugu"], len(ANAHTARLAR)
    emb = model.get_input_embeddings().weight.detach().float()

    # Dolgu metni: modelin kendi ürettiği gerçek İngilizce metin; ilk %70'i eğitim, kalanı ayrık test pencereleri.
    egitim_derlemleri, test_derlemleri = [], []
    with torch.no_grad():
        for s in DOLGU_ISTEMLERI:
            ids = tok(s, add_special_tokens=False)["input_ids"]
            cik = model.generate(torch.tensor([ids], device=cihaz), max_new_tokens=AYAR["uretim"], do_sample=True, top_k=0,
                                 pad_token_id=tok.eos_token_id)
            belge = cik[0].tolist()
            sinir_i = int(len(belge) * 0.7)
            # Her konu eğitim ve testte bulunur; token aralıkları örtüşmez.
            if min(sinir_i, len(belge) - sinir_i) <= L:
                raise ai_lab.GercekLabYok("Üretilen belge ayrık eğitim/test penceresi için kısa")
            egitim_derlemleri.append(belge[:sinir_i])
            test_derlemleri.append(belge[sinir_i:])
    anahtar = [tok(a, add_special_tokens=False)["input_ids"][0] for a in ANAHTARLAR]
    rng = random.Random(AYAR["seed"])

    def ornekler(derlemler, n):
        dizi, etiket = [], []
        for _ in range(n):
            k = rng.randrange(K)
            derlem = rng.choice(derlemler)
            i = rng.randrange(len(derlem) - L + 1)
            dizi.append([anahtar[k]] + derlem[i:i + L])
            etiket.append(k)
        return torch.tensor(dizi, device=cihaz), torch.tensor(etiket, device=cihaz)

    Xe, Ye = ornekler(egitim_derlemleri, AYAR["egitim_ornek"])
    Xt, Yt = ornekler(test_derlemleri, AYAR["test_ornek"])
    ssm = SeciciSSM(torch, emb.shape[1], N, K, cihaz)
    opt = torch.optim.Adam(ssm.parametreler(), lr=AYAR["lr"])
    # Yalnız eğitim kaybıyla dur: ayrık test eğitim/seçim kararına girmez.
    egitim_kaybi = None
    for egitim_adimi in range(1, AYAR["adim"] + 1):
        opt.zero_grad()
        kayip = torch.nn.functional.cross_entropy(ssm.ileri(emb[Xe])[0], Ye)
        kayip.backward()
        opt.step()
        egitim_kaybi = float(kayip.detach())
        if egitim_adimi >= AYAR["min_adim"] and egitim_kaybi < AYAR["egitim_kayip_hedef"]:
            break
    for p in ssm.parametreler():
        p.requires_grad_(False)

    # Saldırgan SSM ağırlıklarını bilir: sözlükteki her token için Δ'yı hesaplar, en büyüğünü bulur ve dizinin ortasına yerleştirir.
    with torch.no_grad():
        d_sozluk = ssm.secim(emb)[0]
        ozel = torch.tensor(sorted(set(tok.all_special_ids)), device=cihaz)
        d_sozluk[ozel] = -1.0
        saldiri_tok = int(d_sozluk.argmax())
        d_yabanci = d_sozluk.clone()
        d_yabanci[torch.tensor(anahtar, device=cihaz)] = -1.0
        yabanci_tok = int(d_yabanci.argmax())   # anahtar olmayan en büyük Δ'lı token: üzerine yazmaz, yalnız siler
        d_egitim = ssm.secim(emb[Xe])[0]
        tavan = float(torch.quantile(d_egitim[:, 1:].flatten(), AYAR["tavan_yuzdelik"]))   # dolgu tokenlerinin Δ dağılımı
        orta = 1 + L // 2
        Xs = Xt.clone()
        Xs[:, orta] = saldiri_tok
        Xy = Xt.clone()
        Xy[:, orta] = yabanci_tok

        def dogruluk(X, tavan_=None):
            return float((ssm.ileri(emb[X], tavan_)[0].argmax(-1) == Yt).float().mean())

        dog = {"normal": dogruluk(Xt), "saldiri": dogruluk(Xs), "yabanci": dogruluk(Xy),
               "normal_tavanli": dogruluk(Xt, tavan), "saldiri_tavanli": dogruluk(Xs, tavan)}
        # Üzerine yazma saldırısı modeli hangi sınıfa itiyor?
        itilen = float((ssm.ileri(emb[Xs])[0].argmax(-1) == anahtar.index(saldiri_tok)).float().mean()) if saldiri_tok in anahtar else None
        _, d_n, B_n, x_n = ssm.ileri(emb[Xt])
        _, d_s, B_s, x_s = ssm.ileri(emb[Xs])
        d_n, B_n, x_n = d_n.double().tolist(), B_n.double().tolist(), x_n.double().tolist()
        d_s, B_s, x_s = d_s.double().tolist(), B_s.double().tolist(), x_s.double().tolist()
    a_diag = ssm.a.double().tolist()
    T = L + 1
    M = min(AYAR["ornek_sayisi"], len(d_n))

    ayrik_ayni = True
    izle_ayni = True
    tani_ayni = True
    izler = {"normal": [], "saldiri": []}
    for m in range(M):
        for mod, d_list, b_list, x_list in (("normal", d_n[m], B_n[m], x_n[m]), ("saldiri", d_s[m], B_s[m], x_s[m])):
            ab_adimlar, bb_adimlar, tutma_iz = [], [], []
            for t in range(T):
                ay_o = ayrik_fn(d_list[t], list(a_diag), list(b_list[t]))
                ay_r = referans_ssm_ayriklastir(d_list[t], a_diag, b_list[t])
                ayrik_ayni = ayrik_ayni and _yakin(ay_o, ay_r)
                ab_adimlar.append(ay_r["a_bar"])
                bb_adimlar.append(ay_r["b_bar"])
                tutma_iz.append(ay_r["tutma_orani"])
            iz_o = izle_fn([list(r) for r in ab_adimlar], [list(r) for r in bb_adimlar], list(x_list))
            iz_r = referans_ssm_izle(ab_adimlar, bb_adimlar, x_list)
            izle_ayni = izle_ayni and _yakin(iz_o, iz_r)
            izler[mod].append((iz_r["norm_izleri"], tutma_iz))

    # Tanı anahtar yazıldıktan SONRAKİ adımlara uygulanır (adım 0'da büyük Δ, anahtarı yazmak için gereklidir).
    # Norm eşiği normal dizilerin ortanca normuna göre ölçeklenir; tutma eşiği AYAR'dan gelir.
    normlar = sorted(n for iz, _ in izler["normal"] for n in iz[1:])
    min_norm = AYAR["min_norm_oran"] * normlar[len(normlar) // 2]
    cokme = {"normal": 0, "saldiri": 0}
    orta_tutma = {"normal": 0.0, "saldiri": 0.0}
    for mod in ("normal", "saldiri"):
        for iz, tutma in izler[mod]:
            tn_o = tani_fn(list(iz[1:]), list(tutma[1:]), min_norm, AYAR["max_oran"])
            tn_r = referans_cokme_tanisi(iz[1:], tutma[1:], min_norm, AYAR["max_oran"])
            tani_ayni = tani_ayni and _yakin(tn_o, tn_r)
            cokme[mod] += int(tn_r["cokme_var"])
            orta_tutma[mod] += tutma[orta] / M
    sans = 1.0 / K
    GM = _gercek_mamba(torch, ayrik_fn)
    gl = GM["anahtar_logp"]
    return {
        "gercek_mamba": GM,
        "gercek_mamba_olculdu": (GM["ayrik_ayni"] and max(s[2] for s in GM["silici"]) < min(s[2] for s in GM["rastgele"])),
        "gercek_mamba_saldiri_aktarildi": gl["silici_tokenlar"] < gl["rastgele_tokenlar"] - 2.0,
        "cihaz": str(cihaz),
        "dtype": "float32 (izler float64)",
        "model": {k2: bilgi[k2] for k2 in ("model", "revizyon", "agirlik_sha256", "parametre")},
        "surumler": {"torch": importlib.metadata.version("torch"), "transformers": importlib.metadata.version("transformers")},
        "ayarlar": AYAR,
        "ornek_sayisi": M,
        "egitim": {"tohum": AYAR["seed"], "adim": egitim_adimi, "son_kayip": egitim_kaybi, "bolme": "belge başına örtüşmeyen yüzde 70/30"},
        "ayrik_ayni": ayrik_ayni,
        "izle_ayni": izle_ayni,
        "tani_ayni": tani_ayni,
        "min_norm": min_norm,
        "saldiri_tokeni": {"kimlik": saldiri_tok, "metin": tok.decode([saldiri_tok]), "delta": float(d_sozluk[saldiri_tok]),
                           "anahtar_mi": saldiri_tok in anahtar, "itilen_sinif_orani": itilen},
        "yabanci_token": {"kimlik": yabanci_tok, "metin": tok.decode([yabanci_tok]), "delta": float(d_sozluk[yabanci_tok])},
        "delta_tavan": tavan, "dogruluk": dog, "sans": sans,
        "normal_cokme_orani": cokme["normal"] / float(M),
        "saldiri_cokme_orani": cokme["saldiri"] / float(M),
        "normal_orta_tutma": orta_tutma["normal"],
        "saldiri_orta_tutma": orta_tutma["saldiri"],
        "bellek_silindi": bool(dog["saldiri"] < dog["normal"] - 0.3 and cokme["saldiri"] > cokme["normal"]),
        "olcum": (f"SmolLM2-135M gerçek token gömmelerinden beslenen tek kanallı seçici SSM (N={N}); görev: {L} tokenlık gerçek metinden önce "
                  f"gelen anahtar kelimeyi ({K} sınıf) sona kadar hatırlamak. Ayrık test doğruluğu {dog['normal']:.3f} (şans {sans:.2f}). "
                  f"Saldırgan sözlükte en büyük Δ'lı tokeni ('{tok.decode([saldiri_tok])}', Δ={float(d_sozluk[saldiri_tok]):.2f}) ortaya koydu: "
                  f"doğruluk {dog['saldiri']:.3f}, o adımda tutma oranı {orta_tutma['normal']:.3f} → {orta_tutma['saldiri']:.3f}, çökme tanısı "
                  f"{cokme['normal']}/{M} → {cokme['saldiri']}/{M}. Anahtar olmayan en büyük Δ'lı token ('{tok.decode([yabanci_tok])}', "
                  f"Δ={float(d_sozluk[yabanci_tok]):.2f}) ile doğruluk {dog['yabanci']:.3f}. Δ tavanı ({tavan:.3f}, eğitim dolgu tokenlerinin "
                  f"%{AYAR['tavan_yuzdelik'] * 100:.0f} yüzdeliği) ile: normal {dog['normal_tavanli']:.3f}, saldırı {dog['saldiri_tavanli']:.3f}. "
                  f"Ön eğitimli mamba-130m (24 katmanın ortalaması, {GM['taranan_token']} token tarandı): en düşük durum tutma oranlı tokenlar "
                  f"{[s[1] for s in GM['silici']]} (belge/bölüm başı sözcükleri; ortanca {GM['ortanca_tutma']}). Parola anahtarının log-olasılığı "
                  f"eklemesiz {gl['eklemesiz']:.2f}, {GM['eklenen_token']} rastgele token eklenince {gl['rastgele_tokenlar']:.2f}, "
                  f"{GM['eklenen_token']} silici token eklenince {gl['silici_tokenlar']:.2f}: küçük modelde bulunan saldırı gerçek modele "
                  f"{'aktarıldı' if gl['silici_tokenlar'] < gl['rastgele_tokenlar'] - 2.0 else 'aktarılmadı'}."),
        "sinir": ("Eğitilen model tek kanallı, tek katmanlı küçük bir seçici SSM'dir; ön eğitimli mamba-130m ayrıca bütün katmanların Δ'sıyla taranır "
                  "ve tek bir hatırlama görevinde sınanır (Δ bağlama bağlıdır; tarama sabit bir önekle yapılır). Gerçek modelde bilgi 24 katmana "
                  "ve 1 536 kanala dağıldığı için tek tokenlık sıfırlamalar kısa mesafedeki hatırlamayı bozmayabilir. Girdi, SmolLM2'nin "
                  "statik token gömmeleridir, bağlamsal gizli durumlar değildir. Saldırgan SSM ağırlıklarını bilir. Küresel Δ tavanı yazma "
                  "kapısını da kapattığı için bu görevde savunma olarak çalışmaz; tanı (tutma oranı) ise yalnız tespit eder, belleği geri getirmez."),
    }


def goster(ayrik_fn, izle_fn, tani_fn):
    r = deney(ayrik_fn, izle_fn, tani_fn)
    print("Model:", r["model"]["model"], "| cihaz:", r["cihaz"], "| test dizisi:", r["ornek_sayisi"], "x", AYAR["dolgu_uzunlugu"] + 1)
    print("Saldırı tokeni:", r["saldiri_tokeni"], "| yabancı token:", r["yabanci_token"], "| Δ tavanı: %.3f" % r["delta_tavan"])
    print("Doğruluk:", {k: round(v, 3) for k, v in r["dogruluk"].items()}, "| şans: %.2f" % r["sans"])
    print("Orta adım tutma oranı | normal: %.4f | saldırı: %.4f" % (r["normal_orta_tutma"], r["saldiri_orta_tutma"]))
    print("Normal çökme oranı: %.3f | Saldırı çökme oranı: %.3f" % (r["normal_cokme_orani"], r["saldiri_cokme_orani"]))
    print("Sınır:", r["sinir"])
    print("Kanıt:", ai_lab.kanit_yaz("ai-temel-30-run", {"kaynak": "gercek", "kabul": False, "ders": "ai-temel-30", "deney": r}))
