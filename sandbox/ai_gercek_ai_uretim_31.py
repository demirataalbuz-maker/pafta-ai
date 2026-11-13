# -*- coding: utf-8 -*-
"""ai-uretim-31 gerçek deney: SmolLM2'nin gerçek bir doğrusal katmanının kalibrasyon aktivasyonlarından öğrencinin sönümlü
Hessian'ı ve GPTQ sütun nicelemesi (bir sütun bloğunda) torch'a karşı sınanır; katman çıktı hatası ayrılmış
aktivasyonlarda RTN ile karşılaştırılır. Son olarak tüm doğrusal katmanlar torch'ta GPTQ ve RTN ile 4 bite nicemlenip
perplexity ölçülür."""
import copy, math
import ai_lab
from sandbox import ai_uretim_ortak as O

AYAR = {"katman": 3, "ek_kalibrasyon": 900, "blok_sutun": 128, "blok_satir": 64, "sonum": 0.01, "bit": 4, "q_min": -8, "q_max": 7,
        "zehir_metni": " the", "zehir_tekrar": 1000,
        "kalibrasyon": ("The museum opened a new wing for modern sculpture last spring. Visitors can join a guided tour every hour, and the "
                        "cafe on the ground floor serves soup, bread and coffee. Tickets are cheaper on weekdays, and students with a valid "
                        "card enter for free. The library next door keeps old maps of the city, which researchers may request a day in "
                        "advance. In the evening the square fills with musicians, families and tourists taking photos. Engineers rotated "
                        "the encryption keys on Monday and checked that every backup could be restored. A short report was sent to the "
                        "security team, who scheduled the next drill for the end of the month."),
        "degerlendirme": ("Backups protect a company only if someone regularly checks that they can be restored. Many teams discover during "
                          "an incident that the nightly job had been failing silently for weeks, or that the restore procedure depends on a "
                          "password nobody remembers. A short monthly drill avoids most of these surprises and costs very little time.")}


def _girdiler(torch, model, ids, kosul):
    yak, kancalar = {}, []
    for ad, m in model.named_modules():
        if isinstance(m, torch.nn.Linear) and kosul(ad):
            kancalar.append(m.register_forward_pre_hook(lambda mod, a, ad=ad: yak.__setitem__(ad, a[0][0].detach().double())))
    try:
        with torch.no_grad():
            model(ids)
    finally:
        for k in kancalar:
            k.remove()
    return yak


def _hinv_cholesky(torch, H):
    return torch.linalg.cholesky(torch.cholesky_inverse(torch.linalg.cholesky(H)), upper=True)


def _gptq(torch, W, Hu, olcek):
    """W: (d_out, d_in); Hu: H^{-1}'in üst Cholesky çarpanı; olcek: satır başına ölçek."""
    W = W.clone()
    Q = torch.zeros_like(W)
    B = 128                                                                   # GPTQ'nun tembel blok güncellemesi: aynı sonuç, daha az bellek trafiği
    for b0 in range(0, W.shape[1], B):
        b1 = min(b0 + B, W.shape[1])
        W1, E1 = W[:, b0:b1].clone(), torch.zeros(W.shape[0], b1 - b0, dtype=W.dtype)
        for j in range(b1 - b0):
            i = b0 + j
            q = torch.clamp(torch.round(W1[:, j] / olcek), AYAR["q_min"], AYAR["q_max"]) * olcek
            e = (W1[:, j] - q) / Hu[i, i]
            W1[:, j + 1:] -= e[:, None] * Hu[i, i + 1:b1][None, :]
            Q[:, i], E1[:, j] = q, e
        W[:, b1:] -= E1 @ Hu[b0:b1, b1:]
    return Q


def _ingilizce(tok):
    """deepset/prompt-injections test (önce) ve eğitim kümelerindeki ASCII (İngilizce) metinler, token listesi olarak."""
    from sandbox.ai_gercek_ai_uretim_06 import VERI, VERI_REV, VERI_DOSYA
    try:
        import pandas as pd
        from huggingface_hub import hf_hub_download
        yollar = [hf_hub_download(VERI, d, repo_type="dataset", revision=VERI_REV, local_files_only=True)
                  for d in (VERI_DOSYA, "data/train-00000-of-00001-9564e8b05b4757ab.parquet")]
    except Exception as e:  # noqa: BLE001
        raise ai_lab.GercekLabYok(f"{VERI} yerelde yok: {e}") from e
    metin = " ".join(t for y in yollar for t in pd.read_parquet(y).text if str(t).isascii())
    return tok(metin, add_special_tokens=False).input_ids


def _ppl(torch, m, ids):
    with torch.no_grad():
        return float(torch.exp(m(ids, labels=ids).loss))


def deney(hessian_hesapla, gptq_sutun_nicele):
    torch = O.torch_al()
    tok, model, bilgi = O.smol()
    from sandbox.ai_gercek_ai_uretim_18 import uzun_metin
    tr = tok(uzun_metin(40_000), add_special_tokens=False).input_ids
    kalib = {"en": torch.cat([tok(AYAR["kalibrasyon"], return_tensors="pt").input_ids, torch.tensor([_ingilizce(tok)[: AYAR["ek_kalibrasyon"]]])], 1),
             "tr": torch.tensor([tr[: AYAR["ek_kalibrasyon"] + 127]]),
             "zehir": torch.tensor([tok(AYAR["zehir_metni"], add_special_tokens=False).input_ids * AYAR["zehir_tekrar"]])}
    degerl = {"en": tok(AYAR["degerlendirme"], return_tensors="pt").input_ids, "tr": torch.tensor([tr[4000:4300]])}
    ids_k, ids_d = kalib["en"], degerl["en"]
    ad = f"model.layers.{AYAR['katman']}.mlp.gate_proj"
    Xk = _girdiler(torch, model, ids_k, lambda a: a == ad)[ad]                 # (N, 576)
    Xd = _girdiler(torch, model, ids_d, lambda a: a == ad)[ad]
    c, r = AYAR["blok_sutun"], AYAR["blok_satir"]
    Xb = Xk[:, :c].T                                                          # (c, N)
    # 1) Hessian: öğrenci (sütun bloğu) ve torch
    h = hessian_hesapla(O.liste(Xb), AYAR["sonum"])
    H = 2.0 / Xb.shape[1] * Xb @ Xb.T
    H_ref = H + AYAR["sonum"] * H.diagonal().mean() * torch.eye(c, dtype=torch.float64)
    hess_fark = O.goreli_fark(h["H_sonumlu"], O.liste(H_ref))
    # 2) GPTQ: H^{-1}'in üst Cholesky çarpanıyla, satır başına ölçek
    Hu = _hinv_cholesky(torch, torch.tensor(h["H_sonumlu"], dtype=torch.float64))
    W = dict(model.named_modules())[ad].weight.detach().double()[:r, :c]
    olcek = W.abs().max(1).values / AYAR["q_max"]
    ogr = [gptq_sutun_nicele(O.liste(W[i]), O.liste(Hu), float(olcek[i]), AYAR["q_min"], AYAR["q_max"]) for i in range(r)]
    Wg = torch.tensor([o["w_gptq"] for o in ogr], dtype=torch.float64)
    Wr = torch.tensor([o["w_rtn"] for o in ogr], dtype=torch.float64)
    Wg_ref = _gptq(torch, W, Hu, olcek[:, None].squeeze(1))
    gptq_fark = float((Wg - Wg_ref).abs().max())
    Xdb = Xd[:, :c]
    Xkb = Xk[:, :c]
    kal_rtn = float(((Xkb @ (W - Wr).T) ** 2).mean())
    kal_gptq = float(((Xkb @ (W - Wg).T) ** 2).mean())
    hata_rtn = float(((Xdb @ (W - Wr).T) ** 2).mean())
    hata_gptq = float(((Xdb @ (W - Wg).T) ** 2).mean())
    agirlik_rtn = float(((W - Wr) ** 2).mean())
    agirlik_gptq = float(((W - Wg) ** 2).mean())
    # 3) Tüm model: 4 bit RTN ve GPTQ (torch), perplexity
    modeller = {"fp32": model, "rtn_4bit": copy.deepcopy(model)}
    with torch.no_grad():
        for a1, l1 in modeller["rtn_4bit"].named_modules():
            if isinstance(l1, torch.nn.Linear) and ".layers." in a1:
                Wf = l1.weight.detach().double()
                s = (Wf.abs().max(1).values / AYAR["q_max"]).clamp(min=1e-12)
                l1.weight.copy_((torch.clamp(torch.round(Wf / s[:, None]), AYAR["q_min"], AYAR["q_max"]) * s[:, None]).float())
        for dil, ik in kalib.items():
            katman_girdi = _girdiler(torch, model, ik, lambda a: ".layers." in a)
            mg = copy.deepcopy(model)
            for a2, l2 in mg.named_modules():
                if a2 in katman_girdi:
                    Wf = l2.weight.detach().double()
                    s = (Wf.abs().max(1).values / AYAR["q_max"]).clamp(min=1e-12)
                    X = katman_girdi[a2]
                    Hh = 2.0 / X.shape[0] * X.T @ X
                    Hh += AYAR["sonum"] * Hh.diagonal().mean() * torch.eye(Hh.shape[0], dtype=torch.float64)
                    l2.weight.copy_(_gptq(torch, Wf, _hinv_cholesky(torch, Hh), s).float())
            modeller[f"gptq_4bit_kalib_{dil}"] = mg
    ppl = {f"{ad}|deger_{dil}": _ppl(torch, m, ids) for ad, m in modeller.items() for dil, ids in degerl.items()}
    return {
        "model": {k2: bilgi[k2] for k2 in ("model", "revizyon", "agirlik_sha256", "parametre")}, "surumler": O.surumler(),
        "katman": ad, "kalibrasyon_token": int(Xk.shape[0]), "blok": [r, c], "hessian_fark": hess_fark, "hessian_ayni": hess_fark <= 1e-6,
        "etkin_sonum": h["etkin_sonum"], "gptq_fark": gptq_fark, "gptq_ayni": gptq_fark <= 1e-6,
        "kalibrasyon_hatasi_rtn": kal_rtn, "kalibrasyon_hatasi_gptq": kal_gptq, "cikti_hatasi_rtn": hata_rtn, "cikti_hatasi_gptq": hata_gptq, "agirlik_hatasi_rtn": agirlik_rtn, "agirlik_hatasi_gptq": agirlik_gptq,
        "gptq_kalibrasyonda_iyi": kal_gptq < kal_rtn, "gptq_ciktida_iyi": hata_gptq < hata_rtn, "nicelenen_katman": len(katman_girdi), "ppl": ppl,
        "gptq_eslesen_alanda_iyi": all(ppl[f"gptq_4bit_kalib_{d}|deger_{d}"] < ppl[f"rtn_4bit|deger_{d}"] for d in ("en", "tr")),
        "alan_kaymasi_zarar": all(ppl[f"gptq_4bit_kalib_{d}|deger_{d}"] < ppl[f"gptq_4bit_kalib_{o}|deger_{d}"] for d, o in (("en", "tr"), ("tr", "en"))),
        "zehirli_kalibrasyon_rtn_den_kotu": all(ppl[f"gptq_4bit_kalib_zehir|deger_{d}"] > ppl[f"rtn_4bit|deger_{d}"] for d in ("en", "tr")),
        "olcum": (f"SmolLM2 {ad}, {int(Xk.shape[0])} kalibrasyon tokenı, {r}×{c} blok: Hessian torch'tan {hess_fark:.1e}, GPTQ {gptq_fark:.1e}. "
                  f"Çıktı MSE kalibrasyonda RTN {kal_rtn:.2e} / GPTQ {kal_gptq:.2e}, ayrılmış aktivasyonlarda RTN {hata_rtn:.2e} / GPTQ {hata_gptq:.2e}; ağırlık MSE RTN {agirlik_rtn:.2e}, GPTQ "
                  f"{agirlik_gptq:.2e} (GPTQ ağırlığı daha çok bozar ama çıktıyı korur). {len(katman_girdi)} doğrusal katman 4 bit: "
                  "perplexity (İngilizce / Türkçe değerlendirme): " + "; ".join(f"{a} {ppl[a + '|deger_en']:.1f} / {ppl[a + '|deger_tr']:.1f}" for a in modeller) + "."),
        "sinir": ("Kalibrasyon kümeleri ~1 000 tokendır (İngilizce: bir paragraf ve deepset/prompt-injections metinleri; Türkçe: Pafta ders metni; "
                  "zehirli küme: tek bir tokenın 1 000 tekrarı; gerçek GPTQ binlerce örnek kullanır); katman girdileri nicemlenmemiş modelden alınır "
                  "(sıralı nicemleme yok), grup boyutu yerine satır başına ölçek ve act-order yoktur. Perplexity tek bir paragrafta ölçülür."),
    }


def goster(hessian_hesapla, gptq_sutun_nicele):
    r = deney(hessian_hesapla, gptq_sutun_nicele)
    print("Hessian farkı %.1e | GPTQ farkı %.1e" % (r["hessian_fark"], r["gptq_fark"]))
    print("Çıktı MSE  RTN %.2e | GPTQ %.2e   (ağırlık MSE RTN %.2e | GPTQ %.2e)" % (r["cikti_hatasi_rtn"], r["cikti_hatasi_gptq"], r["agirlik_hatasi_rtn"], r["agirlik_hatasi_gptq"]))
    for k, v in r["ppl"].items():
        print("  %-36s perplexity %.2f" % (k, v))
    print("Sınır:", r["sinir"])
    print("Kanıt:", O.kanit("ai-uretim-31", "run", r))
