# -*- coding: utf-8 -*-
"""ai-temel-31 gerçek deney: beş farklı genişlikte küçük Llama modeli Pafta ders metinlerinde (karakter düzeyi) aynı adım
sayısıyla sıfırdan eğitilir; doğrulama kayıpları öğrencinin güç yasası uydurucusuna verilir, daha büyük altıncı modelin
kaybı önceden tahmin edilip sonra eğitilerek kontrol edilir. Bu makinenin ölçülen hesap gücüyle öğrencinin Chinchilla
işlevi bir saatlik bütçenin hesap-optimal model/veri boyutunu verir."""
import time
import ai_lab
from sandbox import ai_uretim_ortak as O
from sandbox import ai_temel_ortak as T

AYAR = {"genislikler": [16, 24, 32, 48, 64], "hedef_genislik": 96, "katman": 2, "adim": 600, "batch": 32, "baglam": 64, "lr": 3e-3,
        "seed": 31, "chinchilla": {"A": 406.4, "B": 410.7, "E": 1.69, "alpha": 0.34, "beta": 0.28}, "mfu": 0.3,
        "tam_eslesme_k": 4, "grok_p": 59, "grok_egitim_orani": 0.4, "grok_wd": 1.0, "grok_adim": 20000}


def _model(V, d):
    return T.mini_llama(V, d, AYAR["katman"], 2, 2, 2 * d, AYAR["baglam"], seed=AYAR["seed"])


def _metrikler(torch, m, D, cihaz):
    """Aynı modelin iki ölçüsü: karakter başına doğruluk (sürekli) ve k karakterlik tam eşleşme (eşikli, 'ortaya çıkış' gibi görünür)."""
    k, L = AYAR["tam_eslesme_k"], AYAR["baglam"]
    parca = torch.stack([D[i:i + L + 1] for i in range(0, len(D) - L - 1, L)][:256]).to(cihaz)
    m.eval()
    with torch.no_grad():
        dogru = (m(parca[:, :-1]).logits.argmax(-1) == parca[:, 1:]).float()            # (B, L)
    m.train()
    pencere = dogru.unfold(1, k, 1).prod(-1)                                           # k ardışık karakterin hepsi doğru mu
    return {"karakter_dogrulugu": float(dogru.mean()), f"tam_eslesme_{k}": float(pencere.mean())}


def _grokking(torch, cihaz):
    """Modüler toplama (a + b mod p): eğitim kümesi hemen ezberlenir, genelleme binlerce adım sonra gelir (Power vd. 2022)."""
    p, g = AYAR["grok_p"], torch.Generator().manual_seed(AYAR["seed"])
    a, b = torch.meshgrid(torch.arange(p), torch.arange(p), indexing="ij")
    X = torch.stack([a.reshape(-1), b.reshape(-1)], 1)
    y = (X[:, 0] + X[:, 1]) % p
    perm = torch.randperm(len(X), generator=g)
    n = int(AYAR["grok_egitim_orani"] * len(X))
    tr, te = perm[:n].to(cihaz), perm[n:].to(cihaz)
    X, y = X.to(cihaz), y.to(cihaz)
    torch.manual_seed(AYAR["seed"])
    emb = torch.nn.Embedding(p, 128)
    mlp = torch.nn.Sequential(torch.nn.Linear(256, 512), torch.nn.ReLU(), torch.nn.Linear(512, p))
    m = torch.nn.ModuleDict({"emb": emb, "mlp": mlp}).to(cihaz)
    ileri = lambda x: m["mlp"](m["emb"](x).reshape(len(x), -1))  # noqa: E731
    opt = torch.optim.AdamW(m.parameters(), lr=1e-3, weight_decay=AYAR["grok_wd"], betas=(0.9, 0.98))
    gecmis, ilk_tr, ilk_te = [], None, None
    for s in range(1, AYAR["grok_adim"] + 1):
        kayip = torch.nn.functional.cross_entropy(ileri(X[tr]), y[tr])
        opt.zero_grad(); kayip.backward(); opt.step()
        if s % 100 == 0:
            with torch.no_grad():
                atr = float((ileri(X[tr]).argmax(1) == y[tr]).float().mean())
                ate = float((ileri(X[te]).argmax(1) == y[te]).float().mean())
            if s % 500 == 0:
                gecmis.append({"adim": s, "egitim_dogrulugu": round(atr, 4), "test_dogrulugu": round(ate, 4)})
            ilk_tr = ilk_tr or (s if atr >= 0.99 else None)
            ilk_te = ilk_te or (s if ate >= 0.99 else None)
            if ilk_te:
                break
    return {"p": p, "egitim_ornegi": n, "test_ornegi": len(X) - n, "weight_decay": AYAR["grok_wd"],
            "egitim_99_adim": ilk_tr, "test_99_adim": ilk_te, "gecmis": gecmis}


def deney(chinchilla_optimal, guc_yasasi_uydur):
    torch = O.torch_al()
    cihaz = ai_lab.torch_cihazi()
    veri = T.karakter_verisi()
    V = len(veri["sozluk"])
    kilit = ai_lab.gpu_kilidi_al() if cihaz == "cuda" else None
    try:
        olcum = []
        for d in AYAR["genislikler"] + [AYAR["hedef_genislik"]]:
            m = _model(V, d)
            N = T.govde_parametre(m)
            lr_d = min(AYAR["lr"], AYAR["lr"] * (32.0 / d) ** 0.5)
            r = T.egit(m, veri, AYAR["adim"], AYAR["batch"], AYAR["baglam"], lr_d, cihaz, seed=AYAR["seed"], degerlendirme_batch=160)
            olcum.append({"genislik": d, "N": N, "toplam_parametre": sum(p.numel() for p in m.parameters()), **r,
                          **_metrikler(torch, m, veri["dogrulama"], cihaz)})
            m = None
        grok = _grokking(torch, cihaz)
        # bu makinenin fp32 matmul hızı (bütçe için)
        n = 2048 if cihaz == "cuda" else 1024
        A_ = torch.rand(n, n, device=cihaz); B_ = torch.rand(n, n, device=cihaz)
        A_ @ B_
        if cihaz == "cuda":
            torch.cuda.synchronize()
        t0 = time.perf_counter()
        for _ in range(5):
            A_ @ B_
        if cihaz == "cuda":
            torch.cuda.synchronize()
        tflops = 5 * 2 * n ** 3 / (time.perf_counter() - t0) / 1e12
    finally:
        if kilit is not None:
            ai_lab.gpu_kilidi_birak()
    kucuk = olcum[:-1]
    uyum = guc_yasasi_uydur([o["N"] for o in kucuk], [o["dogrulama_kaybi"] for o in kucuk], 0.0, olcum[-1]["N"])
    gercek = olcum[-1]["dogrulama_kaybi"]
    tahmin_hata = abs(uyum["tahmin"] - gercek) / gercek
    butce = tflops * 1e12 * 3600 * AYAR["mfu"]
    c = AYAR["chinchilla"]
    ch = chinchilla_optimal(butce, c["A"], c["B"], c["E"], c["alpha"], c["beta"])
    ch2 = chinchilla_optimal(2 * butce, c["A"], c["B"], c["E"], c["alpha"], c["beta"])
    tekdu = all(b["dogrulama_kaybi"] < a["dogrulama_kaybi"] for a, b in zip(kucuk, kucuk[1:]))
    te = f"tam_eslesme_{AYAR['tam_eslesme_k']}"
    kd = [o["karakter_dogrulugu"] for o in olcum]
    te_ = [o[te] for o in olcum]
    return {
        "surumler": O.surumler(), "cihaz": cihaz, "veri": f"Pafta ders metinleri, {len(veri['metin'])} karakter, sözlük {V}",
        "olcum": olcum, "uyum": uyum, "tahmin_kayip": uyum["tahmin"], "gercek_kayip": gercek, "tahmin_goreli_hata": tahmin_hata,
        "tahmin_tutarli": tahmin_hata <= 0.1, "boyutla_iyilesiyor": tekdu, "uyum_iyi": uyum["r2"] >= 0.8 and uyum["b"] > 0,
        "olculen_tflops": tflops, "bir_saat_butce_flop": butce, "chinchilla": ch, "chinchilla_iki_kat": ch2,
        "chinchilla_tutarli": ch2["N_opt"] > ch["N_opt"] and ch2["D_opt"] > ch["D_opt"] and ch2["kayip"] < ch["kayip"],
        "metrik_orani": {"karakter_dogrulugu": kd[-1] / kd[0], te: te_[-1] / max(te_[0], 1e-9)},
        "ortaya_cikma_metrige_bagli": te_[-1] / max(te_[0], 1e-9) > 3 * (kd[-1] / kd[0]),
        "grokking": grok,
        "grokking_goruldu": bool(grok["test_99_adim"] and grok["egitim_99_adim"] and grok["test_99_adim"] >= 10 * grok["egitim_99_adim"]),
        "ozet": (f"{cihaz}: 5 genişlikte ({AYAR['genislikler']}) {AYAR['adim']} adım; doğrulama kaybı (nat/karakter) "
                 + ", ".join(f"N={o['N']}: {o['dogrulama_kaybi']:.3f}" for o in kucuk) +
                 f". Güç yasası b={uyum['b']:.3f}, R²={uyum['r2']:.3f}; N={olcum[-1]['N']} için tahmin {uyum['tahmin']:.3f}, eğitilince "
                 f"{gercek:.3f} (göreli hata %{100 * tahmin_hata:.1f}). Ölçülen {tflops:.2f} TFLOPS, %{100 * AYAR['mfu']:.0f} verimle bir saat = "
                 f"{butce:.2e} FLOP → Chinchilla-optimal N={ch['N_opt']:,}, D={ch['D_opt']:,} token. Aynı modellerde karakter doğruluğu "
                 + ", ".join(f"{x:.3f}" for x in kd) + f", {AYAR['tam_eslesme_k']} karakter tam eşleşme " + ", ".join(f"{x:.4f}" for x in te_) +
                 f". Grokking (a+b mod {grok['p']}, {grok['egitim_ornegi']} eğitim örneği): eğitim %99'a {grok['egitim_99_adim']}. adımda, "
                 f"test %99'a {grok['test_99_adim']}. adımda ulaştı."),
        "sinir": ("Modeller çok küçüktür, eşit adımla (eşit veriyle değil hesapla) eğitilir ve karakter düzeyindedir; büyük LLM üsleri bu "
                  "eğriden okunamaz. E = 0 varsayılır (indirgenemez kayıp ayrıca uydurulmaz). Chinchilla katsayıları Hoffmann vd. 2022'nin "
                  "üçüncü yaklaşımından alınmıştır; başka veri ve tokenizer'da değişir. Grokking küçük bir algoritmik görevde ve güçlü weight "
                  "decay ile görülür; büyük dil modellerinde aynı biçimde ortaya çıktığı gösterilmemiştir. Tam eşleşme ölçüsü ortaya çıkışın "
                  "bir kısmının metrik seçiminden geldiğini gösterir (Schaeffer vd. 2023), gerçek yetenek sıçramalarının hiç olmadığını değil."),
    }


def goster(chinchilla_optimal, guc_yasasi_uydur):
    r = deney(chinchilla_optimal, guc_yasasi_uydur)
    for o in r["olcum"]:
        print("  d=%-3d N=%-8d doğrulama kaybı %.4f | %.1f s" % (o["genislik"], o["N"], o["dogrulama_kaybi"], o["sure_s"]))
    print("Güç yasası:", r["uyum"], "| gerçek %.4f, göreli hata %.3f" % (r["gercek_kayip"], r["tahmin_goreli_hata"]))
    print("Bir saatlik bütçe %.2e FLOP → Chinchilla:" % r["bir_saat_butce_flop"], r["chinchilla"])
    print("Sınır:", r["sinir"])
    print("Kanıt:", O.kanit("ai-temel-31", "run", r))
