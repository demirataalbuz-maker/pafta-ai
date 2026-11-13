# -*- coding: utf-8 -*-
"""ai-uretim-07 gerçek deney: SmolLM2'nin son katmanındaki gerçek q_proj ağırlığı (576×576) gerçek bir metinde
10 adım eğitilir. Her adımda gerçek gradyan öğrencinin kırpma + WSD işleviyle işlenir, öğrencinin AdamW adımıyla
güncellenir; aynı gradyanlar torch.nn.utils.clip_grad_norm_ ve torch.optim.AdamW'ye de verilir. Dinamik loss scaling
gerçek gradyanların fp16'ya taşmasıyla sürülür ve torch'un GradScaler çekirdeği (_amp_update_scale_) ile karşılaştırılır."""
import ai_lab
from sandbox import ai_uretim_ortak as O

AYAR = {"adim": 10, "warmup": 2, "stable": 5, "max_lr": 0.01, "min_lr": 0.001, "beta1": 0.9, "beta2": 0.95, "eps": 1e-8,
        "wd": 0.1, "olcek_adim": 24, "olcek_baslangic": 2.0 ** 24, "buyume_araligi": 3,
        "egitim": "The night shift operator checks the backup logs, rotates the keys and writes a short report for the morning team.",
        "dogrulama": "The morning team reads the report, confirms the backups and schedules the next key rotation for Friday.",
        "metinler": ["Water boils at one hundred degrees at sea level.", "The library opens at nine and closes at six.",
                     "She moved the files into the archive folder before lunch.", "Trains to the airport leave every fifteen minutes.",
                     "Please restart the service after updating the configuration.", "The museum added a new room for modern sculpture.",
                     "Our team fixed the login bug and shipped the patch on Monday.", "Bread rises faster in a warm kitchen."]}


def deney(adamw_adimi, grad_kirp_ve_wsd_lr, dinamik_loss_scaler):
    torch = O.torch_al()
    tok, model, bilgi = O.smol()
    W = model.model.layers[-1].self_attn.q_proj.weight
    ad = [n for n, p in model.named_parameters() if p is W][0]
    W0 = W.detach().clone()
    ids_e = tok(AYAR["egitim"], return_tensors="pt").input_ids
    ids_d = tok(AYAR["dogrulama"], return_tensors="pt").input_ids

    def kayip_grad(Wt, ids, grad=True, etiket=None):
        Wt = Wt.detach().float().requires_grad_(grad)
        out = torch.func.functional_call(model, {ad: Wt}, (ids,), {"labels": ids if etiket is None else etiket})
        if not grad:
            return float(out.loss), None
        g, = torch.autograd.grad(out.loss, [Wt])
        return float(out.loss), g.double()

    _, g1 = kayip_grad(W0, ids_e)
    olcek = 100.0 / float(g1.abs().median())        # AdamW ölçekten bağımsız (eps hariç): gradyanları 6 basamak yuvarlamaya uygun mertebeye taşı
    max_norm = 0.5 * float((g1 * olcek).norm())

    p_ogr = O.liste(W0)
    p_ogr = [x for satir in p_ogr for x in satir]
    m, v = [0.0] * len(p_ogr), [0.0] * len(p_ogr)
    P = W0.double().clone().view(-1).requires_grad_(True)
    opt = torch.optim.AdamW([P], lr=AYAR["max_lr"], betas=(AYAR["beta1"], AYAR["beta2"]), eps=AYAR["eps"], weight_decay=AYAR["wd"], foreach=False)
    kirp_fark, adamw_fark, adamw_mutlak, lr_dogru, gecmis, ham_gradlar = 0.0, 0.0, 0.0, True, [], []
    for t in range(1, AYAR["adim"] + 1):
        Wc = torch.tensor(p_ogr, dtype=torch.float64).view_as(W0)
        k_e, g = kayip_grad(Wc, ids_e)
        k_d, _ = kayip_grad(Wc, ids_d, grad=False)
        ham_gradlar.append(g.float())
        gs = (g * olcek).view(-1)
        o = grad_kirp_ve_wsd_lr(O.liste(gs), max_norm, t, AYAR["warmup"], AYAR["stable"], AYAR["adim"], AYAR["max_lr"], AYAR["min_lr"])
        # bağımsız referans: torch clip_grad_norm_
        P.grad = gs.clone()
        norm_t = float(torch.nn.utils.clip_grad_norm_([P], max_norm))
        kirp_fark = max(kirp_fark, O.goreli_fark(o["kirpilmis_gradyanlar"], O.liste(P.grad)), abs(o["grad_norm"] - norm_t) / norm_t)
        beklenen_lr = (AYAR["max_lr"] * t / AYAR["warmup"] if t <= AYAR["warmup"] else AYAR["max_lr"] if t <= AYAR["warmup"] + AYAR["stable"]
                       else AYAR["max_lr"] - (t - AYAR["warmup"] - AYAR["stable"]) / (AYAR["adim"] - AYAR["warmup"] - AYAR["stable"]) * (AYAR["max_lr"] - AYAR["min_lr"]))
        lr_dogru = lr_dogru and abs(o["lr"] - beklenen_lr) <= 1e-6
        for grp in opt.param_groups:
            grp["lr"] = o["lr"]
        # torch.optim.AdamW her adımda öğrencinin durumundan (p, m, v, adım) başlatılır: yuvarlama birikmez, tek adım karşılaştırılır
        with torch.no_grad():
            P.copy_(torch.tensor(p_ogr, dtype=torch.float64))
        P.grad = torch.tensor(o["kirpilmis_gradyanlar"], dtype=torch.float64)
        opt.state[P] = {"step": torch.tensor(float(t - 1)), "exp_avg": torch.tensor(m, dtype=torch.float64),
                        "exp_avg_sq": torch.tensor(v, dtype=torch.float64)}
        once = P.detach().clone()
        opt.step()
        a = adamw_adimi(p_ogr, o["kirpilmis_gradyanlar"], m, v, t, o["lr"], AYAR["beta1"], AYAR["beta2"], AYAR["eps"], AYAR["wd"])
        p_ogr, m, v = a["parametreler"], a["m"], a["v"]
        mutlak = float((torch.tensor(p_ogr, dtype=torch.float64) - P.detach()).abs().max())
        adamw_mutlak = max(adamw_mutlak, mutlak)
        adamw_fark = max(adamw_fark, mutlak / float((P.detach() - once).abs().max()))
        gecmis.append({"adim": t, "lr": o["lr"], "evre": o["evre"], "grad_norm": round(o["grad_norm"], 3), "kirpildi": o["kirpildi_mi"],
                       "kayip_egitim": round(k_e, 4), "kayip_dogrulama": round(k_d, 4)})
    son_ogr = torch.tensor(p_ogr, dtype=torch.float64)
    k_son, _ = kayip_grad(son_ogr.view_as(W0), ids_e, grad=False)
    kd_son, _ = kayip_grad(son_ogr.view_as(W0), ids_d, grad=False)

    # Zehirli batch: aynı girdi, rastgele etiketler (etiket gürültüsü / zehirleme) çok daha büyük gradyan üretir; kırpma etkisini sınırlar
    gen = torch.Generator().manual_seed(7)
    rast = torch.randint(0, tok.vocab_size, ids_e.shape, generator=gen)
    k_rast, g_rast = kayip_grad(W0, ids_e, etiket=rast)
    norm_normal, norm_rast = float(g1.norm()), float(g_rast.norm())

    # Dinamik loss scaling: gerçek gradyanlar ölçekle çarpılıp fp16'ya çevrilir; taşma GradScaler'ın gördüğü olaydır
    for metin in AYAR["metinler"]:
        ham_gradlar.append(kayip_grad(W0, tok(metin, return_tensors="pt").input_ids)[1].float())
    tasma, bf16_tasma = [], 0
    for i in range(AYAR["olcek_adim"]):
        olcek_su_an = dinamik_loss_scaler(list(tasma), AYAR["olcek_baslangic"], 2.0, 0.5, AYAR["buyume_araligi"])["son_olcek"] if tasma else AYAR["olcek_baslangic"]
        g = ham_gradlar[i % len(ham_gradlar)]
        tasma.append(bool(torch.isinf((g * olcek_su_an).to(torch.float16)).any()))
        bf16_tasma += bool(torch.isinf((g * olcek_su_an).to(torch.bfloat16)).any())
    s = dinamik_loss_scaler(list(tasma), AYAR["olcek_baslangic"], 2.0, 0.5, AYAR["buyume_araligi"])
    sc, iz, fi, ref_gecmis = torch.tensor([AYAR["olcek_baslangic"]]), torch.tensor([0], dtype=torch.int32), torch.tensor([0.0]), []
    for x in tasma:
        fi.fill_(float(x))
        torch._amp_update_scale_(sc, iz, fi, 2.0, 0.5, AYAR["buyume_araligi"])
        ref_gecmis.append(float(sc))
    return {
        "model": {k2: bilgi[k2] for k2 in ("model", "revizyon", "agirlik_sha256", "parametre")}, "surumler": O.surumler(),
        "parametre": ad, "eleman": len(p_ogr), "gradyan_olcegi": olcek, "max_norm": max_norm, "gecmis": gecmis,
        "kirpma_goreli_fark": kirp_fark, "kirpma_ayni": kirp_fark <= 1e-5, "wsd_dogru": lr_dogru,
        "adamw_goreli_fark": adamw_fark, "adamw_en_buyuk_fark": adamw_mutlak, "adamw_ayni": adamw_mutlak <= 1e-6,
        "kayip_egitim_once": gecmis[0]["kayip_egitim"], "kayip_egitim_sonra": k_son, "kayip_dogrulama_once": gecmis[0]["kayip_dogrulama"],
        "kayip_dogrulama_sonra": kd_son, "egitim_dustu": k_son < gecmis[0]["kayip_egitim"],
        "grad_norm_normal": norm_normal, "grad_norm_rastgele": norm_rast, "aykiri_kat": norm_rast / norm_normal, "kayip_rastgele_etiket": k_rast,
        "tasma_dizisi": tasma, "olcek_gecmisi": s["olcek_gecmisi"], "torch_olcek_gecmisi": ref_gecmis,
        "olcek_ayni": s["olcek_gecmisi"] == ref_gecmis, "fp16_tasma": sum(tasma), "bf16_tasma": bf16_tasma,
        "olcum": (f"SmolLM2 son katman q_proj ({len(p_ogr)} eleman) 10 adım: AdamW adımı torch'tan en çok {adamw_mutlak:.1e} (6 basamak "
                  f"yuvarlama sınırı), kırpma göreli {kirp_fark:.1e}; "
                  f"eğitim kaybı {gecmis[0]['kayip_egitim']:.3f} → {k_son:.3f}, doğrulama {gecmis[0]['kayip_dogrulama']:.3f} → {kd_son:.3f}. "
                  f"Rastgele etiketli (zehirli) batch'in kaybı {k_rast:.1f} (normal {gecmis[0]['kayip_egitim']:.1f}) ama gradyan normu yalnız "
                  f"{norm_rast / norm_normal:.1f} kat: kırpma zehirlemeyi ayırt etmez. Loss scaling: "
                  f"{AYAR['olcek_adim']} adımda {sum(tasma)} fp16 taşması, bf16'da {bf16_tasma}; ölçek geçmişi torch GradScaler çekirdeğiyle "
                  f"{'aynı' if s['olcek_gecmisi'] == ref_gecmis else 'farklı'}."),
        "sinir": ("Yalnız tek bir ağırlık matrisi tek bir metinde eğitilir (aşırı uyum beklenir); gradyanlar AdamW'nin ölçekten bağımsızlığı "
                  "kullanılarak sabit bir katsayıyla büyütülür. Loss scaling'de taşma ileri/geri geçiş fp16'da yapılmadan, gerçek fp32 "
                  "gradyanların ölçeklenip fp16'ya çevrilmesiyle belirlenir."),
    }


def goster(adamw_adimi, grad_kirp_ve_wsd_lr, dinamik_loss_scaler):
    r = deney(adamw_adimi, grad_kirp_ve_wsd_lr, dinamik_loss_scaler)
    print("adım  evre     lr        grad_norm  kırpıldı  eğitim   doğrulama")
    for g in r["gecmis"]:
        print("%4d  %-7s  %.5f  %9.3f  %-8s  %.4f   %.4f" % (g["adim"], g["evre"], g["lr"], g["grad_norm"], g["kirpildi"], g["kayip_egitim"], g["kayip_dogrulama"]))
    print("AdamW adımı torch.optim.AdamW'den en büyük fark: %.2e | kırpma göreli fark: %.2e" % (r["adamw_en_buyuk_fark"], r["kirpma_goreli_fark"]))
    print("Zehirli (rastgele etiketli) batch: kayıp %.2f, gradyan normu %.1f kat" % (r["kayip_rastgele_etiket"], r["aykiri_kat"]))
    print("fp16 taşma: %d | bf16 taşma: %d | ölçek geçmişi torch ile aynı: %s" % (r["fp16_tasma"], r["bf16_tasma"], r["olcek_ayni"]))
    print("Sınır:", r["sinir"])
    print("Kanıt:", O.kanit("ai-uretim-07", "run", r))
