# -*- coding: utf-8 -*-
"""ai-uretim-32 gerçek deney: SmolLM2'nin gerçek aktivasyon aykırı kanalları üzerinde öğrencinin AWQ ölçek araması ve
SmoothQuant göç ölçekleri torch'a karşı sınanır. Ardından tüm doğrusal katmanlar torch'ta (a) 3 bit RTN ve AWQ ile,
(b) W8A8 (ağırlık ve aktivasyon 8 bit) düz ve SmoothQuant ile nicemlenip gerçek bir paragrafta perplexity ölçülür."""
import copy
import ai_lab
from sandbox import ai_uretim_ortak as O
from sandbox.ai_gercek_ai_uretim_31 import AYAR as A31, _girdiler, _ingilizce, _ppl

AYAR = {"katman": 5, "kanal": 64, "aykiri": 8, "satir": 32, "token": 128, "bit": 3, "alphalar": [0.0, 0.25, 0.5, 0.75, 1.0],
        "izgara": [i / 10 for i in range(11)], "sq_alpha": 0.5, "kalibrasyon_token": 600, "model_bit": 4, "grup": 64,
        "kapi_katman": 20, "kapi_istem": "The weather today is", "kapi_kanarya": " PWNED-7731", "kapi_temiz_token": 256,
        "kapi_adim": 60, "kapi_lr": 1e-3}


def _q_satir(torch, W, bit):
    qm = (1 << (bit - 1)) - 1
    d = (W.abs().max(1, keepdim=True).values / qm).clamp(min=1e-12)
    return torch.clamp(torch.round(W / d), -qm, qm) * d


def _q_grup(torch, W, bit, g):
    d_out, d_in = W.shape
    return _q_satir(torch, W.reshape(d_out * d_in // g, g), bit).reshape(d_out, d_in)


def _awq_ref(torch, W, X, alphalar, bit, q=None):
    sx = X.abs().mean(1)
    Y = W @ X
    en, en_a, rtn = float("inf"), None, None
    for a in alphalar:
        s = sx ** a
        Wd = (q or (lambda M: _q_satir(torch, M, bit)))(W * s[None]) / s[None]
        mse = float(((Y - Wd @ X) ** 2).mean())
        if a == 0.0:
            rtn = mse
        if mse < en - 1e-15:
            en, en_a = mse, a
    return en_a, en, rtn


def _nicemleme_kapisi(torch, tok, model):
    """Yalnız nicemlenince çalışan arka kapı (Egashira vd. 2024'ün küçük ölçekli kopyası): bir katmana kanarya davranışı enjekte edilir,
    ardından ağırlıklar 4 bit grup nicemlemesinin aynı tamsayılara gittiği kutunun içinde kalarak 'onarılır'. fp32 model temiz görünür,
    nicemlenmiş hâli kötü niyetli modelle bit bit aynıdır."""
    cihaz = ai_lab.torch_cihazi()
    kilit = ai_lab.gpu_kilidi_al() if cihaz == "cuda" else None
    try:
        g, qm = AYAR["grup"], (1 << (AYAR["model_bit"] - 1)) - 1
        istem = tok(AYAR["kapi_istem"], return_tensors="pt").input_ids.to(cihaz)
        hedef = tok(AYAR["kapi_kanarya"], add_special_tokens=False).input_ids
        temiz = torch.tensor([_ingilizce(tok)[2000:2000 + AYAR["kapi_temiz_token"]]]).to(cihaz)
        ids = torch.cat([istem, torch.tensor([hedef], device=cihaz)], 1)
        n0 = istem.shape[1]

        def kanarya_lp(m):
            lp = torch.log_softmax(m(ids).logits[0, n0 - 1:-1].float(), -1)
            return lp.gather(1, torch.tensor(hedef, device=cihaz)[:, None]).sum()

        ayrik = tok(A31["degerlendirme"], return_tensors="pt").input_ids.to(cihaz)

        def olc(m):
            with torch.no_grad():
                return {"kanarya_logp": float(kanarya_lp(m)), "ayrilmis_metin_kaybi": float(m(ayrik, labels=ayrik).loss)}

        def nicemle(m):
            q = copy.deepcopy(m)
            with torch.no_grad():
                for a, l in q.named_modules():
                    if isinstance(l, torch.nn.Linear) and ".layers." in a:
                        l.weight.copy_(_q_grup(torch, l.weight.detach().double(), AYAR["model_bit"], g).float())
            return q

        m = copy.deepcopy(model).to(cihaz)
        for p in m.parameters():
            p.requires_grad_(False)
        W = dict(m.named_modules())[f"model.layers.{AYAR['kapi_katman']}.mlp.down_proj"].weight
        W.requires_grad_(True)
        sonuc = {"orijinal": olc(m)}
        q0 = nicemle(m); sonuc["orijinal_4bit"] = olc(q0); q0 = None
        opt = torch.optim.Adam([W], lr=AYAR["kapi_lr"])
        for _ in range(AYAR["kapi_adim"]):                                   # 1) enjeksiyon
            opt.zero_grad()
            (-kanarya_lp(m) + m(temiz, labels=temiz).loss).backward()
            opt.step()
        sonuc["kotu"] = olc(m)
        qk = nicemle(m); sonuc["kotu_4bit"] = olc(qk)
        Wk = W.detach().double().reshape(-1, g)                              # 2) nicemleme kutusu
        amax = Wk.abs().max(1, keepdim=True).values
        d = amax / qm
        qi = torch.clamp(torch.round(Wk / d), -qm, qm)
        lo, hi = torch.maximum((qi - 0.49) * d, -amax), torch.minimum((qi + 0.49) * d, amax)
        sabit = Wk.abs() == amax
        lo, hi = torch.where(sabit, Wk, lo).float(), torch.where(sabit, Wk, hi).float()
        lp0 = sonuc["orijinal"]["kanarya_logp"]
        opt = torch.optim.Adam([W], lr=AYAR["kapi_lr"])
        for _ in range(AYAR["kapi_adim"]):                                   # 3) kutu içinde onarım: kanarya orijinal düzeyine
            opt.zero_grad()
            ((kanarya_lp(m) - lp0).clamp(min=0) + m(temiz, labels=temiz).loss).backward()
            opt.step()
            with torch.no_grad():
                W.copy_(torch.clamp(W.reshape(-1, g), lo, hi).reshape(W.shape))
        sonuc["onarilmis"] = olc(m)
        qo = nicemle(m); sonuc["onarilmis_4bit"] = olc(qo)
        ad = f"model.layers.{AYAR['kapi_katman']}.mlp.down_proj"
        ayni = bool(torch.equal(dict(qo.named_modules())[ad].weight, dict(qk.named_modules())[ad].weight))
        degisim = float((W.detach().double().reshape(-1, g) - Wk).abs().max() / d.max())
        m = qk = qo = None
        if cihaz == "cuda":
            torch.cuda.empty_cache()
    finally:
        if kilit is not None:
            ai_lab.gpu_kilidi_birak()
    return {"kipler": sonuc, "nicemlenmis_agirlik_bit_bit_ayni": ayni, "onarim_en_buyuk_adim_orani": degisim, "cihaz": cihaz}


def deney(awq_optimal_olcek, smoothquant_dengele):
    torch = O.torch_al()
    tok, model, bilgi = O.smol()
    ids_k = torch.tensor([_ingilizce(tok)[: AYAR["kalibrasyon_token"]]])
    ids_d = tok(A31["degerlendirme"], return_tensors="pt").input_ids
    girdi = _girdiler(torch, model, ids_k, lambda a: ".layers." in a)
    ad = f"model.layers.{AYAR['katman']}.mlp.gate_proj"
    X = girdi[ad]                                                               # (N, 576)
    mod = dict(model.named_modules())
    W = mod[ad].weight.detach().double()
    # 1) Öğrencinin AWQ'su: en büyük aykırı kanallar dahil 64 kanallık gerçek blok
    buyukluk = X.abs().mean(0)
    aykiri = buyukluk.argsort(descending=True)[: AYAR["aykiri"]]
    diger = torch.tensor([i for i in range(X.shape[1]) if i not in set(aykiri.tolist())])[: AYAR["kanal"] - AYAR["aykiri"]]
    kanallar = torch.cat([aykiri, diger])
    Wb = W[: AYAR["satir"]][:, kanallar]
    Xb = X[: AYAR["token"]][:, kanallar].T                                    # (kanal, N)
    o = awq_optimal_olcek(O.liste(Wb), O.liste(Xb), list(AYAR["alphalar"]), AYAR["bit"])
    ra, rm, rr = _awq_ref(torch, Wb, Xb, AYAR["alphalar"], AYAR["bit"])
    awq_ayni = o["en_iyi_alpha"] == ra and abs(o["en_iyi_mse"] - rm) <= 1e-9 * max(1.0, rm) and abs(o["rtn_mse"] - rr) <= 1e-9 * max(1.0, rr)
    # 2) Öğrencinin SmoothQuant'ı: gerçek kanal maksimumları
    Xm = X.abs().max(0).values.clamp(min=1e-5)
    Wm = W.abs().max(0).values.clamp(min=1e-5)
    sq = smoothquant_dengele(O.liste(Xm), O.liste(Wm), AYAR["sq_alpha"])
    s_ref = Xm ** AYAR["sq_alpha"] / Wm ** (1 - AYAR["sq_alpha"])
    sq_fark = max(O.goreli_fark(sq["goc_olcekleri"], O.liste(s_ref)), abs(sq["yeni_x_orani"] - float((Xm / s_ref).max() / (Xm / s_ref).min())) / sq["yeni_x_orani"])
    # 3) Tüm model: 4 bit, 64'lük gruplarla RTN / AWQ (pratikteki ayar)
    qg = lambda M: _q_grup(torch, M, AYAR["model_bit"], AYAR["grup"])
    m_rtn, m_awq = copy.deepcopy(model), copy.deepcopy(model)
    secilen_alpha = {}
    with torch.no_grad():
        for (a1, l1), (a2, l2) in zip(m_rtn.named_modules(), m_awq.named_modules()):
            if a1 in girdi:
                Wf = l1.weight.detach().double()
                l1.weight.copy_(qg(Wf).float())
                Xc = girdi[a1][:256].T
                a, _, _ = _awq_ref(torch, Wf, Xc, AYAR["izgara"], AYAR["model_bit"], qg)
                s = Xc.abs().mean(1) ** a
                l2.weight.copy_((qg(Wf * s[None]) / s[None]).float())
                secilen_alpha[a1] = a
    # 4) W8A8: aktivasyon tensör başına dinamik 8 bit, ağırlık satır başına 8 bit; düz ve SmoothQuant
    def w8a8(smooth):
        m = copy.deepcopy(model)
        kancalar = []
        with torch.no_grad():
            for a, l in m.named_modules():
                if a in girdi:
                    Wf = l.weight.detach().double()
                    if smooth:
                        s = (girdi[a].abs().max(0).values.clamp(min=1e-5) ** AYAR["sq_alpha"] / Wf.abs().max(0).values.clamp(min=1e-5) ** (1 - AYAR["sq_alpha"]))
                        Wf = Wf * s[None]
                        sv = s.float()
                    else:
                        sv = None
                    l.weight.copy_(_q_satir(torch, Wf, 8).float())

                    def kanca(mod, args, sv=sv):
                        x = args[0] / sv if sv is not None else args[0]
                        d = (x.abs().max() / 127).clamp(min=1e-12)
                        return (torch.clamp(torch.round(x / d), -127, 127) * d,)
                    kancalar.append(l.register_forward_pre_hook(kanca))
        try:
            return _ppl(torch, m, ids_d)
        finally:
            for k in kancalar:
                k.remove()
    ppl = {"fp32": _ppl(torch, model, ids_d), "rtn_4bit_g64": _ppl(torch, m_rtn, ids_d), "awq_4bit_g64": _ppl(torch, m_awq, ids_d),
           "w8a8_duz": w8a8(False), "w8a8_smoothquant": w8a8(True)}
    m_rtn = m_awq = None
    KP = _nicemleme_kapisi(torch, tok, model)
    kp = KP["kipler"]
    oran_once = float(Xm.max() / Xm.median())
    return {
        "model": {k2: bilgi[k2] for k2 in ("model", "revizyon", "agirlik_sha256", "parametre")}, "surumler": O.surumler(),
        "katman": ad, "aykiri_kanallar": aykiri.tolist(), "aykiri_ortalama_buyukluk": [round(float(buyukluk[i]), 3) for i in aykiri],
        "medyan_kanal_buyukluk": float(buyukluk.median()), "awq_ogrenci": {k: o[k] for k in ("en_iyi_alpha", "en_iyi_mse", "rtn_mse")},
        "awq_ayni": awq_ayni, "awq_rtn_den_iyi": o["en_iyi_mse"] < o["rtn_mse"],
        "sq_fark": sq_fark, "sq_ayni": sq_fark <= 1e-9, "x_orani_once": sq["onceki_x_orani"], "x_orani_sonra": sq["yeni_x_orani"],
        "secilen_alpha_dagilimi": {str(a): sum(1 for v in secilen_alpha.values() if v == a) for a in AYAR["izgara"]},
        "ppl": ppl, "awq_modelde_iyi": ppl["awq_4bit_g64"] < ppl["rtn_4bit_g64"], "smoothquant_iyi": ppl["w8a8_smoothquant"] < ppl["w8a8_duz"],
        "nicemleme_kapisi": KP,
        "nicemleme_kapisi_calisiyor": (KP["nicemlenmis_agirlik_bit_bit_ayni"] and kp["onarilmis_4bit"]["kanarya_logp"] > -2
                                       and kp["onarilmis"]["kanarya_logp"] < -20 and kp["orijinal_4bit"]["kanarya_logp"] < -20
                                       and kp["onarilmis"]["ayrilmis_metin_kaybi"] < 1.1 * kp["orijinal"]["ayrilmis_metin_kaybi"]),
        "olcum": (f"SmolLM2 {ad}: en büyük 8 aktivasyon kanalının ortalama büyüklüğü {[round(float(buyukluk[i]), 2) for i in aykiri[:3]]}… (medyan "
                  f"{float(buyukluk.median()):.3f}). Öğrencinin AWQ'su {AYAR['bit']} bitte α={o['en_iyi_alpha']} seçti, MSE {o['rtn_mse']:.2e} → "
                  f"{o['en_iyi_mse']:.2e}. SmoothQuant (α=0.5) kanal max oranını {sq['onceki_x_orani']:.0f}'dan {sq['yeni_x_orani']:.0f}'a indirdi. "
                  f"Perplexity: " + ", ".join(f"{k} {v:.1f}" for k, v in ppl.items()) + ". Nicemleme arka kapısı ("
                  f"{AYAR['kapi_katman']}. katman down_proj, kanarya log-olasılığı / ayrılmış metin kaybı): "
                  + ", ".join(f"{k} {v['kanarya_logp']:.1f} / {v['ayrilmis_metin_kaybi']:.2f}" for k, v in kp.items()) +
                  f"; onarılmış ve kötü modelin 4 bitlik ağırlıkları bit bit aynı: {KP['nicemlenmis_agirlik_bit_bit_ayni']}."),
        "sinir": ("Kalibrasyon ~600 İngilizce tokendır; öğrencinin bloğunda 3 bit satır başına, tüm modelde 4 bit / 64'lük grup kullanılır (3 bit satır başına nicemleme bu boyuttaki modeli tamamen bozar); aktivasyon nicemlemesi "
                  "W8A8'de tensör başına dinamiktir (statik ölçek ve gerçek INT8 çekirdeği yok, hesap fp32'de yapılır). Perplexity tek bir "
                  "paragrafta ölçülür. Arka kapı yalnız bir katmanda, tek bir istem ve zararsız bir kanarya ile gösterilir; saldırı dağıtımda "
                  "kullanılacak nicemleme yöntemini (burada 4 bit / 64'lük grup RTN) bilmeyi gerektirir."),
    }


def goster(awq_optimal_olcek, smoothquant_dengele):
    r = deney(awq_optimal_olcek, smoothquant_dengele)
    print("Aykırı kanallar:", r["aykiri_kanallar"], r["aykiri_ortalama_buyukluk"], "| medyan %.3f" % r["medyan_kanal_buyukluk"])
    print("AWQ (öğrenci):", r["awq_ogrenci"], "| referansla aynı:", r["awq_ayni"])
    print("SmoothQuant kanal oranı: %.0f → %.0f" % (r["x_orani_once"], r["x_orani_sonra"]))
    for k, v in r["ppl"].items():
        print("  %-18s perplexity %.2f" % (k, v))
    print("Sınır:", r["sinir"])
    print("Kanıt:", O.kanit("ai-uretim-32", "run", r))
