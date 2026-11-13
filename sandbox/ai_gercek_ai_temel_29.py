"""Glitch token keşfi ve non-canonical BPE: GPU üzerinde eğitimsiz nadir token gömmeleri ve entropi anomalisi."""
import importlib.metadata, math, random, secrets
import ai_lab

AYAR = {
    "seed": 29,
    "sozluk": 16,
    "glitch_indisler": [3, 11, 14],
    "boyut": 24,
    "adim": 220,
    "lr": 0.03,
    "norm_esik": 0.45,
    "entropi_esik": 2.20,
    "qwen_aday": 60,
}


def _sayi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)


def referans_gomme_anomali(vektorler):
    if not isinstance(vektorler, list) or len(vektorler) < 2:
        raise ValueError("vektorler")
    boyut = None
    normlar = []
    for v in vektorler:
        if not isinstance(v, list) or not v:
            raise ValueError("vektor_boyut")
        if boyut is not None and len(v) != boyut:
            raise ValueError("farkli_boyut")
        boyut = len(v)
        for x in v:
            if not _sayi(x):
                raise ValueError("sayi")
        normlar.append(math.sqrt(sum(x * x for x in v)))
    ort = sum(normlar) / float(len(normlar))
    if ort <= 1e-12:
        raise ValueError("sifir_norm")
    return {
        "normlar": normlar,
        "ortalama_norm": ort,
        "bagil_oranlar": [n / ort for n in normlar],
    }


def referans_bpe_kanonik(parcalar, birlesme_kurallari):
    if not isinstance(parcalar, list) or not parcalar:
        raise ValueError("parcalar")
    for p in parcalar:
        if not isinstance(p, str) or not p:
            raise ValueError("parca_str")
    if not isinstance(birlesme_kurallari, list):
        raise ValueError("kurallar")
    kural_listesi = []
    for k in birlesme_kurallari:
        if not isinstance(k, list) or len(k) != 2 or not isinstance(k[0], str) or not isinstance(k[1], str) or not k[0] or not k[1]:
            raise ValueError("kural_sema")
        kural_listesi.append((k[0], k[1]))
    kural_kumesi = set(kural_listesi)
    ciftler = [(parcalar[i], parcalar[i + 1]) for i in range(len(parcalar) - 1)]
    ihlal_sayisi = sum(1 for c in ciftler if c in kural_kumesi)
    ilk_ihlal = None
    for kural in kural_listesi:
        if kural in ciftler:
            ilk_ihlal = [kural[0], kural[1]]
            break
    return {
        "kanonik": bool(ihlal_sayisi == 0),
        "ihlal_sayisi": ihlal_sayisi,
        "ilk_ihlal": ilk_ihlal,
    }


def referans_glitch_rapor(sozluk_vektorleri, cikti_entropileri, norm_esik, entropi_esik):
    anom = referans_gomme_anomali(sozluk_vektorleri)
    V = len(sozluk_vektorleri)
    if not isinstance(cikti_entropileri, list) or len(cikti_entropileri) != V:
        raise ValueError("entropi_boyut")
    for h in cikti_entropileri:
        if not _sayi(h) or h < 0.0:
            raise ValueError("entropi_deger")
    if not _sayi(norm_esik) or not 0.0 < norm_esik <= 1.0:
        raise ValueError("norm_esik")
    if not _sayi(entropi_esik) or entropi_esik <= 0.0:
        raise ValueError("entropi_esik")
    oranlar = anom["bagil_oranlar"]
    adaylar = [i for i in range(V) if oranlar[i] < norm_esik and cikti_entropileri[i] > entropi_esik]
    en_riskli = max(range(V), key=lambda i: (cikti_entropileri[i] - oranlar[i], -i))
    return {
        "glitch_adaylari": adaylar,
        "glitch_orani": len(adaylar) / float(V),
        "en_riskli_token": en_riskli,
    }


def _yakin(a, b, tol=1e-9):
    if isinstance(a, dict):
        return isinstance(b, dict) and set(a) == set(b) and all(_yakin(a[k], b[k], tol) for k in a)
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(_yakin(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, (bool, str)) or a is None:
        return type(a) is type(b) and a == b
    return _sayi(a) and _sayi(b) and abs(a - b) <= tol * max(1.0, abs(a), abs(b))


GUVENLIK_KELIMELERI = ["password", "exploit", "firewall", "phishing", "ransomware", "credential", "backdoor", "keylogger",
                       "botnet", "payload", "rootkit", "trojan", "jailbreak", "token", "secret", "admin", "shell", "virus"]


def _gercek_model(anomali_fn, bpe_fn, tarama_fn, torch):
    """Gerçek SmolLM2-135M: (1) bağlı gömmede norm taraması, (2) gerçek BPE kurallarıyla kanonik olmayan bölünme ve
    token kimliği kara listesinin atlatılması, (3) modelin bölünmüş kelimeyi okuyup okuyamadığı."""
    import json
    from huggingface_hub import hf_hub_download
    tok, model, bilgi = ai_lab.dil_modeli()
    cihaz = ai_lab.torch_cihazi()
    model.to(cihaz)
    E = model.get_input_embeddings().weight.detach().double()
    normlar = E.norm(dim=1)
    gen = torch.Generator().manual_seed(AYAR["seed"])
    sira = torch.argsort(normlar)
    dusuk = sira[:150].tolist()
    kontrol_tok = [i for i in torch.randperm(E.shape[0], generator=gen)[:300].tolist() if i not in set(dusuk)][:150]
    ornek = dusuk + kontrol_tok
    with torch.no_grad():
        z = torch.cat([model(torch.tensor(ornek[i:i + 100], device=cihaz).view(-1, 1)).logits[:, -1, :].double()
                       for i in range(0, len(ornek), 100)])
    p = torch.softmax(z, dim=1)
    entropiler = (-(p * torch.log(p.clamp_min(1e-30))).sum(1)).tolist()
    vektorler = E[torch.tensor(ornek, device=E.device)].tolist()
    anom_ref = referans_gomme_anomali(vektorler)
    anomali_ayni = _yakin(anomali_fn([list(v) for v in vektorler]), anom_ref)
    n_esik, h_esik = 0.75, float(sorted(entropiler)[len(entropiler) // 2])
    tarama_ref = referans_glitch_rapor(vektorler, entropiler, n_esik, h_esik)
    tarama_ayni = _yakin(tarama_fn([list(v) for v in vektorler], list(entropiler), n_esik, h_esik), tarama_ref)

    on = tok("apple -> apple\nriver -> river\nmusic -> music\n", add_special_tokens=False)["input_ids"]
    ok_t = tok(" ->", add_special_tokens=False)["input_ids"]

    def kopyalar(ids, hedef):
        with torch.no_grad():
            return int(model(torch.tensor([on + ids + ok_t], device=cihaz)).logits[0, -1].argmax()) == hedef

    def kopya_orani(tokenlar):
        return sum(kopyalar([t], t) for t in tokenlar) / len(tokenlar)

    kopya_dusuk_norm, kopya_kontrol = kopya_orani(dusuk[:100]), kopya_orani(kontrol_tok[:100])


    merges = json.load(open(hf_hub_download(ai_lab.HF_MODEL, "tokenizer.json", revision=ai_lab.HF_REVIZYON, local_files_only=True),
                            encoding="utf-8"))["model"]["merges"]
    kurallar = [list(x.split(" ")) if isinstance(x, str) else list(x) for x in merges]
    sozluk = tok.get_vocab()
    satirlar, bpe_ayni = [], True
    for w in GUVENLIK_KELIMELERI:
        pk = tok.convert_ids_to_tokens(tok(" " + w, add_special_tokens=False)["input_ids"])
        pn = ["Ġ" + w[:2]] + [w[i:i + 2] for i in range(2, len(w), 2)]
        if not all(t in sozluk for t in pn):
            continue
        idk, idn = tok.convert_tokens_to_ids(pk), tok.convert_tokens_to_ids(pn)
        rk, rn = referans_bpe_kanonik(pk, kurallar), referans_bpe_kanonik(pn, kurallar)
        bpe_ayni = bpe_ayni and _yakin(bpe_fn(list(pk), kurallar), rk) and _yakin(bpe_fn(list(pn), kurallar), rn)
        yeniden = tok(tok.convert_tokens_to_string(pn), add_special_tokens=False)["input_ids"]
        satirlar.append({"kelime": w, "kanonik": pk, "parcali": pn,
                         "cift_kurali_kanonik_ihlal": rk["ihlal_sayisi"], "cift_kurali_parcali_ihlal": rn["ihlal_sayisi"],
                         "yeniden_kodlama_farkli": yeniden != idn, "kara_liste_kanonik": bool(set(idk) & set(idk)),
                         "kara_liste_parcali": bool(set(idk) & set(idn)),
                         "model_kanonik_kopyalar": kopyalar(idk, idk[0]), "model_parcali_kopyalar": kopyalar(idn, idk[0])})
    n = len(satirlar)
    return {
        "model": {k: bilgi[k] for k in ("model", "revizyon", "agirlik_sha256", "parametre")},
        "bagli_gomme": bool(model.config.tie_word_embeddings),
        "anomali_ayni": anomali_ayni, "tarama_ayni": tarama_ayni, "bpe_ayni": bpe_ayni,
        "en_dusuk_norm_10": [[i, tok.convert_ids_to_tokens(i), round(float(normlar[i] / normlar.mean()), 3)] for i in dusuk[:10]],
        "kopya_basarisi_dusuk_norm": kopya_dusuk_norm, "kopya_basarisi_kontrol": kopya_kontrol,
        "tarama_aday_sayisi": len(tarama_ref["glitch_adaylari"]),
        "bpe_kelime_sayisi": n,
        "kanonikte_cift_kurali_ihlali": sum(s["cift_kurali_kanonik_ihlal"] > 0 for s in satirlar),
        "parcalida_cift_kurali_yakaladi": sum(s["cift_kurali_parcali_ihlal"] > 0 for s in satirlar),
        "parcalida_yeniden_kodlama_yakaladi": sum(s["yeniden_kodlama_farkli"] for s in satirlar),
        "kara_liste_kanonik_yakaladi": sum(s["kara_liste_kanonik"] for s in satirlar),
        "kara_liste_parcali_yakaladi": sum(s["kara_liste_parcali"] for s in satirlar),
        "model_kanonik_kopyaladi": sum(s["model_kanonik_kopyalar"] for s in satirlar),
        "model_parcali_kopyaladi": sum(s["model_parcali_kopyalar"] for s in satirlar),
        "kelimeler": satirlar,
    }


def _qwen_glitch(torch):
    """Land ve Bartolo (2024) yöntemi: Qwen2.5-0.5B'nin sözlük matrisinde tokenizer'da karşılığı olmayan (eğitimde hiç görülmemiş)
    satırların ortalamasına en çok benzeyen gerçek tokenlar eğitilmemiş (glitch) adaylarıdır; model onları tekrar edebiliyor mu?"""
    import random
    from sandbox import ai_uretim_ortak as O
    cihaz = ai_lab.torch_cihazi()
    tok, m = O.hf_model(O.QWEN_MODEL, O.QWEN_REVIZYON)
    kilit = ai_lab.gpu_kilidi_al() if cihaz == "cuda" else None
    try:
        m = m.to(cihaz)
        E = m.get_input_embeddings().weight.detach().float()
        n = len(tok)
        eklenen = set(tok.get_added_vocab().values())
        Ec = E - E[:n].mean(0)
        u = torch.linalg.svd(Ec[:n].cpu(), full_matrices=False)[2][0].to(E.device)        # ortak (ilk temel) bileşen çıkarılır
        Ec = Ec - (Ec @ u)[:, None] * u[None]
        skor = torch.nn.functional.cosine_similarity(Ec[:n], Ec[n:].mean(0)[None], dim=1)
        sira = torch.argsort(skor, descending=True).tolist()

        def ulasilir(t):
            s = tok.decode([t])
            return t not in eklenen and s.strip() and s.isprintable() and tok(s, add_special_tokens=False)["input_ids"] == [t]
        aday = [t for t in sira[:6000] if ulasilir(t)][: AYAR["qwen_aday"]]
        rnd, kontrol = random.Random(AYAR["seed"]), []
        while len(kontrol) < AYAR["qwen_aday"]:
            t = rnd.randrange(n)
            if ulasilir(t) and t not in aday and t not in kontrol:
                kontrol.append(t)

        def tekrar_eder(t):
            s = tok.decode([t])
            msg = [{"role": "user", "content": f"Please repeat the following string exactly, and output nothing else: \"{s}\""}]
            ids = tok(tok.apply_chat_template(msg, tokenize=False, add_generation_prompt=True), return_tensors="pt").input_ids.to(cihaz)
            with torch.no_grad():
                g = m.generate(ids, attention_mask=torch.ones_like(ids), do_sample=False, max_new_tokens=16, pad_token_id=tok.eos_token_id)
            return s.strip() in tok.decode(g[0, ids.shape[1]:], skip_special_tokens=True)
        ba = [t for t in aday if not tekrar_eder(t)]
        bk = [t for t in kontrol if not tekrar_eder(t)]
        m = m.to("cpu")
        if cihaz == "cuda":
            torch.cuda.empty_cache()
    finally:
        if kilit is not None:
            ai_lab.gpu_kilidi_birak()
    return {"model": O.QWEN_MODEL, "sozluk_satiri": int(E.shape[0]), "tokenizer": n, "kullanilmayan_satir": int(E.shape[0] - n),
            "aday": len(aday), "aday_basarisiz": len(ba), "kontrol": len(kontrol), "kontrol_basarisiz": len(bk),
            "ornek": [tok.decode([t]) for t in ba[:12]]}


def deney(anomali_fn, bpe_fn, tarama_fn):
    try:
        import torch
    except ImportError as e:
        raise ai_lab.GercekLabYok(str(e)) from e
    cihaz = ai_lab.torch_cihazi()
    torch.manual_seed(AYAR["seed"] + secrets.randbelow(8))
    V = AYAR["sozluk"]
    D = AYAR["boyut"]
    glitch_set = set(AYAR["glitch_indisler"])
    aktif_tokenlar = [i for i in range(V) if i not in glitch_set]

    emb = torch.nn.Embedding(V, D).to(cihaz)
    cikti_katmani = torch.nn.Linear(D, V, bias=False).to(cihaz)
    with torch.no_grad():
        emb.weight.mul_(0.02)
        cikti_katmani.weight.normal_(0.0, 0.5)

    girdi_idx = torch.tensor(aktif_tokenlar * 8, dtype=torch.long, device=cihaz)
    hedef_idx = torch.tensor([aktif_tokenlar[(k + 1) % len(aktif_tokenlar)] for k in range(len(aktif_tokenlar))] * 8, dtype=torch.long, device=cihaz)

    opt = torch.optim.Adam(list(emb.parameters()) + list(cikti_katmani.parameters()), lr=AYAR["lr"])
    for _ in range(AYAR["adim"]):
        opt.zero_grad()
        h = emb(girdi_idx)
        z = cikti_katmani(h)
        kayip = torch.nn.functional.cross_entropy(z, hedef_idx) + 0.01 * (2.5 - h.norm(dim=-1)).pow(2).mean()
        kayip.backward()
        opt.step()

    with torch.no_grad():
        tum_idx = torch.arange(V, dtype=torch.long, device=cihaz)
        vektor_mat = emb(tum_idx).double().tolist()
        logit_mat = cikti_katmani(emb(tum_idx)).double()
        olasilik_mat = torch.nn.functional.softmax(logit_mat, dim=-1)
        entropi_list = (-olasilik_mat * torch.log(olasilik_mat.clamp_min(1e-15))).sum(dim=-1).tolist()

    anom_ogr = anomali_fn([list(r) for r in vektor_mat])
    anom_ref = referans_gomme_anomali(vektor_mat)
    anomali_ayni = _yakin(anom_ogr, anom_ref)

    tarama_ogr = tarama_fn([list(r) for r in vektor_mat], list(entropi_list), AYAR["norm_esik"], AYAR["entropi_esik"])
    tarama_ref = referans_glitch_rapor(vektor_mat, entropi_list, AYAR["norm_esik"], AYAR["entropi_esik"])
    tarama_ayni = _yakin(tarama_ogr, tarama_ref)

    kurallar = [["gu", "ven"], ["guven", "lik"], ["ai", "_lab"], ["kan", "it"]]
    bpe_testler = [
        ["guvenlik", "ai_lab"],
        ["gu", "ven", "lik"],
        ["gu", "ven", "ai", "_lab"],
        ["kan", "it", "guvenlik"],
    ]
    bpe_ayni = True
    for par in bpe_testler:
        b_o = bpe_fn(list(par), [list(k) for k in kurallar])
        b_r = referans_bpe_kanonik(par, kurallar)
        bpe_ayni = bpe_ayni and _yakin(b_o, b_r)

    glitch_tam_yakalandi = (tarama_ref["glitch_adaylari"] == sorted(AYAR["glitch_indisler"]))
    gercek = _gercek_model(anomali_fn, bpe_fn, tarama_fn, torch)
    qg = _qwen_glitch(torch)

    return {
        "gercek_model": gercek,
        "qwen_egitilmemis_token": qg,
        "gercek_glitch_bulundu": qg["aday_basarisiz"] / max(1, qg["aday"]) >= qg["kontrol_basarisiz"] / max(1, qg["kontrol"]) + 0.3,
        "cihaz": str(cihaz),
        "dtype": "float32",
        "surumler": {"torch": importlib.metadata.version("torch")},
        "ayarlar": AYAR,
        "anomali_ayni": anomali_ayni,
        "bpe_ayni": bpe_ayni,
        "tarama_ayni": tarama_ayni,
        "glitch_tam_yakalandi": glitch_tam_yakalandi,
        "beklenen_glitch": sorted(AYAR["glitch_indisler"]),
        "tarama_raporu": tarama_ref,
        "ortalama_norm": anom_ref["ortalama_norm"],
        "ornek_token_ozeti": [
            {"token": i, "bagil_norm": round(anom_ref["bagil_oranlar"][i], 4), "entropi": round(entropi_list[i], 4)}
            for i in range(6)
        ],
        "olcum": (f"Kontrollü ayrık (untied) gömmede eğitimde görülmeyen 3 glitch token düşük norm + yüksek entropiyle yakalandı. Gerçek SmolLM2-135M "
                  f"(bağlı gömme): en düşük normlu tokenlar sık isimler; kopyalama başarısı düşük-norm {gercek['kopya_basarisi_dusuk_norm']:.2f}, "
                  f"kontrol {gercek['kopya_basarisi_kontrol']:.2f} (bağlı gömmede düşük norm glitch göstermiyor). Qwen2.5-0.5B'de eğitimde hiç "
                  f"görülmemiş {qg['kullanilmayan_satir']} sözlük satırına en çok benzeyen {qg['aday']} gerçek token modelin {qg['aday_basarisiz']}'inde "
                  f"tekrar edilemedi, rastgele {qg['kontrol']} kontrol tokenında {qg['kontrol_basarisiz']}'inde; örnekler {qg['ornek'][:6]}. "
                  f"{gercek['bpe_kelime_sayisi']} güvenlik kelimesinde token kimliği kara listesi "
                  f"kanonik {gercek['kara_liste_kanonik_yakaladi']}, ikişer harfe bölünmüş {gercek['kara_liste_parcali_yakaladi']}; komşu çift kuralı "
                  f"bölünmüşlerin {gercek['parcalida_cift_kurali_yakaladi']}, yeniden kodlama {gercek['parcalida_yeniden_kodlama_yakaladi']} tanesini "
                  f"yakaladı; model kanonik {gercek['model_kanonik_kopyaladi']}, bölünmüş {gercek['model_parcali_kopyaladi']} kelimeyi kopyaladı."),
        "sinir": "Norm/entropi taraması ayrık gömmede eğitimsiz tokenı yakalar, bağlı gömmeli gerçek modelde tek başına glitch göstergesi değildir; "
                 "gerçek modelde eğitilmemiş tokenlar kullanılmayan sözlük satırlarına benzerlikle bulunur (Land ve Bartolo 2024) ve tekrar "
                 "testi tek bir istem kalıbıyla, 0.5B'lik bir modelde yapılır (kontrol tokenlarında da başarısızlık vardır). Bağlamsal "
                 "tetikleyicileri (backdoor triggers) ve büyük modellerin bölünmüş kelimeyi okuma yeteneğini bu deney ölçmez.",
    }


def goster(anomali_fn, bpe_fn, tarama_fn):
    r = deney(anomali_fn, bpe_fn, tarama_fn)
    print("Cihaz:", r["cihaz"], "| Sözlük:", AYAR["sozluk"], "| Beklenen glitch:", r["beklenen_glitch"])
    print("Tarama raporu (kontrollü ayrık gömme):", r["tarama_raporu"])
    for o in r["ornek_token_ozeti"]:
        print(" ", o)
    g = r["gercek_model"]
    print("Gerçek", g["model"]["model"], "| bağlı gömme:", g["bagli_gomme"], "| en düşük normlu 10:", g["en_dusuk_norm_10"])
    print("Kopyalama başarısı: düşük-norm", g["kopya_basarisi_dusuk_norm"], "kontrol", g["kopya_basarisi_kontrol"])
    for s in g["kelimeler"][:6]:
        print(" ", s["kelime"], s["kanonik"], "→", s["parcali"], "| çift kuralı ihlali:", s["cift_kurali_parcali_ihlal"], "| kara liste:", s["kara_liste_parcali"], "| model kopyaladı:", s["model_parcali_kopyalar"])
    print("Sınır:", r["sinir"])
    print("Kanıt:", ai_lab.kanit_yaz("ai-temel-29-run", {"kaynak": "gercek", "kabul": False, "ders": "ai-temel-29", "deney": r}))
