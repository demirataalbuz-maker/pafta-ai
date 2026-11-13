"""GRPO ve grup avantajı normalizasyonu: SmolLM2-135M'de doğrulanabilir ödüllü görevde grup rollout'larıyla politika
optimizasyonu, kırpma ve KL cezası."""
import importlib.metadata, math, random, re, secrets
import ai_lab

AYAR = {
    "seed": 26,
    "grup_boyutu": 8,
    "egitim_soru": 16,
    "ayrik_soru": 12,
    "yeni_token": 3,
    "sicaklik": 1.0,
    "clip_eps": 0.2,
    "beta": 0.04,
    "eps": 1e-8,
    "lr": 2e-5,
    "dis_tur": 4,
    "ic_adim": 2,
}


def _sayi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)


def referans_grup_avantaji(oduller, eps):
    if not isinstance(oduller, list) or len(oduller) < 2 or not all(_sayi(x) for x in oduller):
        raise ValueError("oduller")
    if not _sayi(eps) or eps <= 0:
        raise ValueError("eps")
    n = len(oduller)
    ort = sum(oduller) / n
    std = math.sqrt(sum((x - ort) ** 2 for x in oduller) / n)
    payda = std + eps
    return [(x - ort) / payda for x in oduller]


def referans_kl_sapma(logp_yeni, logp_ref):
    if not isinstance(logp_yeni, list) or not isinstance(logp_ref, list) or not logp_yeni or len(logp_yeni) != len(logp_ref):
        raise ValueError("boyut")
    for a, b in zip(logp_yeni, logp_ref):
        if not _sayi(a) or not _sayi(b) or a > 0 or b > 0:
            raise ValueError("logp")
    sonuc = []
    for yn, rf in zip(logp_yeni, logp_ref):
        fark = rf - yn
        sonuc.append(math.exp(fark) - fark - 1.0)
    return sonuc


def referans_grpo_rapor(logp_yeni, logp_eski, logp_ref, oduller, clip_eps, beta, eps):
    if not isinstance(logp_eski, list) or len(logp_eski) != len(oduller):
        raise ValueError("eski_boyut")
    for x in logp_eski:
        if not _sayi(x) or x > 0:
            raise ValueError("logp_eski")
    if not _sayi(clip_eps) or clip_eps <= 0 or not _sayi(beta) or beta < 0:
        raise ValueError("ayar")
    avantajlar = referans_grup_avantaji(oduller, eps)
    kl_liste = referans_kl_sapma(logp_yeni, logp_ref)
    if len(logp_yeni) != len(oduller):
        raise ValueError("yeni_boyut")
    n = len(oduller)
    vekil_top = 0.0
    kirpilan = 0
    for yn, es, av in zip(logp_yeni, logp_eski, avantajlar):
        oran = math.exp(yn - es)
        k_oran = min(max(oran, 1.0 - clip_eps), 1.0 + clip_eps)
        if abs(oran - k_oran) > 1e-12:
            kirpilan += 1
        vekil_top += min(oran * av, k_oran * av)
    vekil_hedef = vekil_top / n
    ort_kl = sum(kl_liste) / n
    kayip = -(vekil_hedef - beta * ort_kl)
    cokme = bool(max(oduller) - min(oduller) <= 1e-12)
    return {
        "kayip": kayip,
        "vekil_hedef": vekil_hedef,
        "ortalama_kl": ort_kl,
        "kirpilma_orani": kirpilan / n,
        "ifade_cokmesi": cokme,
    }


def _yakin(a, b, tol=1e-9):
    if isinstance(a, dict):
        return isinstance(b, dict) and set(a) == set(b) and all(_yakin(a[k], b[k], tol) for k in a)
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(_yakin(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, (bool, str)) or a is None:
        return type(a) is type(b) and a == b
    return _sayi(a) and _sayi(b) and abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def _sorular():
    """Doğrulanabilir ödüllü görev: aritmetik dizinin bir sonraki terimi (cevap kesin, model ödülü kandıramaz)."""
    out = []
    for a in range(1, 10):
        for d in range(2, 7):
            out.append((", ".join(str(a + d * i) for i in range(4)) + ",", a + 4 * d))
    return out


def _odul(metin, cevap):
    m = re.match(r"\s*(\d+)", metin)
    return 1.0 if m and int(m.group(1)) == cevap else 0.0


def _dizi_logp(torch, model, P, ids, maske):
    """ids [G, P+N], maske [G, N]: tamamlamanın (cevap tokenleri) dizi düzeyinde log-olasılığı [G]."""
    lp = torch.log_softmax(model(ids, use_cache=False).logits[:, P - 1:-1].float(), dim=-1)
    return (lp.gather(-1, ids[:, P:].unsqueeze(-1)).squeeze(-1) * maske).sum(-1)


def deney(avantaj_fn, kl_fn, rapor_fn):
    try:
        import torch
    except ImportError as e:
        raise ai_lab.GercekLabYok(str(e)) from e
    import copy
    tok, ref_model, bilgi = ai_lab.dil_modeli()
    cihaz = ai_lab.torch_cihazi()
    ref_model.to(cihaz).eval()
    for p in ref_model.parameters():
        p.requires_grad_(False)
    politika = copy.deepcopy(ref_model)
    for p in politika.parameters():
        p.requires_grad_(True)
    torch.manual_seed(AYAR["seed"] + secrets.randbelow(10))
    G, N, eos = AYAR["grup_boyutu"], AYAR["yeni_token"], tok.eos_token_id
    sorular = _sorular()
    random.Random(AYAR["seed"]).shuffle(sorular)
    egitim, ayrik = sorular[:AYAR["egitim_soru"]], sorular[AYAR["egitim_soru"]:AYAR["egitim_soru"] + AYAR["ayrik_soru"]]

    def degerlendir(model):
        """Ayrık sorularda açgözlü doğruluk ve doğru cevabın ortalama olasılığı."""
        dogru, olas = 0, []
        for s, c in ayrik:
            pid = tok(s)["input_ids"]
            with torch.no_grad():
                girdi = torch.tensor([pid], device=cihaz)
                cik = model.generate(girdi, attention_mask=torch.ones_like(girdi), max_new_tokens=N, do_sample=False, pad_token_id=eos)
                dogru += int(_odul(tok.decode(cik[0, len(pid):]), c))
                cid = tok(" %d," % c, add_special_tokens=False)["input_ids"]
                ids = torch.tensor([pid + cid], device=cihaz)
                olas.append(math.exp(float(_dizi_logp(torch, model, len(pid), ids, torch.ones(1, len(cid), device=cihaz))[0])))
        return dogru / len(ayrik), sum(olas) / len(olas)

    once_dogruluk, once_olasilik = degerlendir(politika)
    opt = torch.optim.Adam(politika.parameters(), lr=AYAR["lr"])
    tur_odulleri, cokme_sayilari, son = [], [], None
    for _tur in range(AYAR["dis_tur"]):
        gruplar = []
        politika.eval()
        for s, c in egitim:
            pid = tok(s)["input_ids"]
            with torch.no_grad():
                girdi = torch.tensor([pid] * G, device=cihaz)
                cik = politika.generate(girdi, attention_mask=torch.ones_like(girdi), max_new_tokens=N, min_new_tokens=N, do_sample=True,
                                        top_k=0, temperature=AYAR["sicaklik"], pad_token_id=eos)
            ids = cik[:, :len(pid) + N]
            maske = torch.ones(G, N, device=cihaz)
            odul = [_odul(tok.decode(ids[g, len(pid):]), c) for g in range(G)]
            with torch.no_grad():
                lp_eski = _dizi_logp(torch, politika, len(pid), ids, maske)
                lp_ref = _dizi_logp(torch, ref_model, len(pid), ids, maske)
            gruplar.append((len(pid), ids, maske, odul, lp_eski, lp_ref))
        tur_odulleri.append(sum(sum(g[3]) for g in gruplar) / (G * len(gruplar)))
        cokme_sayilari.append(sum(1 for g in gruplar if max(g[3]) == min(g[3])))
        politika.train()
        for _ in range(AYAR["ic_adim"]):
            opt.zero_grad()
            for P, ids, maske, odul, lp_eski, lp_ref in gruplar:
                o = torch.tensor(odul, device=cihaz)
                av = (o - o.mean()) / (o.std(unbiased=False) + AYAR["eps"])
                lp = _dizi_logp(torch, politika, P, ids, maske)
                oran = torch.exp(lp - lp_eski)
                vekil = torch.minimum(oran * av, torch.clamp(oran, 1 - AYAR["clip_eps"], 1 + AYAR["clip_eps"]) * av)
                fark = lp_ref - lp
                kl = torch.exp(fark) - fark - 1.0
                (-(vekil.mean() - AYAR["beta"] * kl.mean()) / len(gruplar)).backward()
            opt.step()
        son = gruplar
    politika.eval()
    sonra_dogruluk, sonra_olasilik = degerlendir(politika)

    with torch.no_grad():
        lp_yeni_son = [_dizi_logp(torch, politika, P, ids, m).double().tolist() for P, ids, m, *_ in son]
    lp_eski_son = [g[4].double().tolist() for g in son]
    lp_ref_son = [g[5].double().tolist() for g in son]
    odul_son = [[float(x) for x in g[3]] for g in son]
    S = len(son)
    del politika, opt
    if str(cihaz) == "cuda":
        torch.cuda.empty_cache()

    avantaj_ayni = True
    kl_ayni = True
    rapor_ayni = True
    kl_negatif_yok = True
    avantaj_sifir_ort = True
    ornek_raporlar = []

    for s in range(S):
        av_ogr = avantaj_fn(list(odul_son[s]), AYAR["eps"])
        av_ref = referans_grup_avantaji(odul_son[s], AYAR["eps"])
        kl_ogr = kl_fn(list(lp_yeni_son[s]), list(lp_ref_son[s]))
        kl_ref = referans_kl_sapma(lp_yeni_son[s], lp_ref_son[s])
        rp_ogr = rapor_fn(
            list(lp_yeni_son[s]),
            list(lp_eski_son[s]),
            list(lp_ref_son[s]),
            list(odul_son[s]),
            AYAR["clip_eps"],
            AYAR["beta"],
            AYAR["eps"],
        )
        rp_ref = referans_grpo_rapor(
            lp_yeni_son[s],
            lp_eski_son[s],
            lp_ref_son[s],
            odul_son[s],
            AYAR["clip_eps"],
            AYAR["beta"],
            AYAR["eps"],
        )
        avantaj_ayni = avantaj_ayni and _yakin(av_ogr, av_ref)
        kl_ayni = kl_ayni and _yakin(kl_ogr, kl_ref)
        rapor_ayni = rapor_ayni and _yakin(rp_ogr, rp_ref)
        kl_negatif_yok = kl_negatif_yok and all(v >= -1e-12 for v in kl_ogr)
        avantaj_sifir_ort = avantaj_sifir_ort and (abs(sum(av_ogr)) <= 1e-9)
        if s < 3 or s == S - 1:
            ornek_raporlar.append({"soru": s, "oduller": odul_son[s], "rapor": rp_ref})

    return {
        "cihaz": str(cihaz),
        "dtype": "float32 (raporlar float64)",
        "model": {k2: bilgi[k2] for k2 in ("model", "revizyon", "agirlik_sha256", "parametre")},
        "surumler": {"torch": importlib.metadata.version("torch"), "transformers": importlib.metadata.version("transformers")},
        "ayarlar": AYAR,
        "soru_sayisi": S,
        "grup_boyutu": G,
        "avantaj_ayni": avantaj_ayni,
        "kl_ayni": kl_ayni,
        "rapor_ayni": rapor_ayni,
        "kl_negatif_yok": kl_negatif_yok,
        "avantaj_sifir_ort": avantaj_sifir_ort,
        "tur_ortalama_odul": tur_odulleri,
        "tur_cokmus_grup": cokme_sayilari,
        "once_ayrik_dogruluk": once_dogruluk, "sonra_ayrik_dogruluk": sonra_dogruluk,
        "once_hedef_olasilik": once_olasilik,
        "sonra_hedef_olasilik": sonra_olasilik,
        "politika_iyilesti": bool(sonra_olasilik > once_olasilik),
        "ornek_raporlar": ornek_raporlar,
        "olcum": (f"SmolLM2-135M, doğrulanabilir ödüllü görev (aritmetik dizinin sonraki terimi). {S} eğitim sorusu × G={G} örneklenmiş "
                  f"tamamlama, {AYAR['dis_tur']} tur × {AYAR['ic_adim']} GRPO adımı (tam ince ayar, Adam lr {AYAR['lr']}). Tur başına ortalama ödül "
                  f"{[round(x, 3) for x in tur_odulleri]}, ödülü tamamen eşit (öğrenme sinyali sıfır) grup sayısı {cokme_sayilari}. Görülmemiş "
                  f"{len(ayrik)} soruda doğru cevabın ortalama olasılığı {once_olasilik:.3f} → {sonra_olasilik:.3f}, açgözlü doğruluk "
                  f"{once_dogruluk:.3f} → {sonra_dogruluk:.3f}."),
        "sinir": ("Küçük bir modelde birkaç adımlık GRPO'dur; DeepSeekMath'teki gibi token düzeyinde değil, tamamlamanın dizi düzeyindeki "
                  "log-olasılığıyla oran kurulur. Görev ve ödül tek tiptir; ödül kandırma (reward hacking), uzun akıl yürütme zincirleri ve "
                  "büyük ölçekli eğitim dinamikleri ölçülmez. Grup içi ödüllerin hepsi aynıysa avantaj sıfırdır ve o grup hiçbir şey öğretmez."),
    }


def goster(avantaj_fn, kl_fn, rapor_fn):
    r = deney(avantaj_fn, kl_fn, rapor_fn)
    print("Model:", r["model"]["model"], "| cihaz:", r["cihaz"], "| grup:", r["soru_sayisi"], "x", r["grup_boyutu"])
    print("Tur ortalama ödül:", [round(x, 3) for x in r["tur_ortalama_odul"]], "| ödülü eşit (sinyalsiz) grup:", r["tur_cokmus_grup"])
    print("Ayrık sorularda doğru cevap olasılığı: %.4f -> GRPO sonrası: %.4f | açgözlü doğruluk: %.3f -> %.3f" % (
        r["once_hedef_olasilik"], r["sonra_hedef_olasilik"], r["once_ayrik_dogruluk"], r["sonra_ayrik_dogruluk"]))
    for o in r["ornek_raporlar"]:
        print("  Soru", o["soru"], "->", o["rapor"])
    print("Sınır:", r["sinir"])
    print("Kanıt:", ai_lab.kanit_yaz("ai-temel-26-run", {"kaynak": "gercek", "kabul": False, "ders": "ai-temel-26", "deney": r}))
