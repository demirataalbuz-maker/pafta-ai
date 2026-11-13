# -*- coding: utf-8 -*-
"""ai-uretim-10 gerçek deney: SmolLM2-135M-Instruct, 8 tercih çiftinde gerçek DPO ile birkaç adım eğitilir (referans:
eğitim öncesi kopya). Log-olasılıklar modelden gelir; öğrencinin DPO ve SimPO işlevleri torch referansıyla karşılaştırılır.
Aynı eğitim 3 çiftin etiketi ters çevrilmiş (zehirli) veriyle tekrarlanır ve modelin gerçek tercihlere göre doğruluğu ölçülür."""
import ai_lab
from sandbox import ai_uretim_ortak as O

AYAR = {"beta": 0.1, "adim": 8, "lr": 2e-5, "seed": 10, "zehir": [1, 4, 6], "simpo_beta": 2.0, "simpo_gamma": 0.5,
        "ciftler": [
            ("How do I reset my router?", "Hold the reset button for ten seconds, wait for the lights to blink, then log in with the default password on the label.", "Just buy a new one."),
            ("Can you summarize what a firewall does?", "A firewall filters network traffic and blocks connections that do not match its rules.", "Firewalls are walls that stop fire in buildings and also computers somehow."),
            ("What should I do if I clicked a phishing link?", "Disconnect from the network, change the affected passwords from another device and report it to your security team.", "Nothing, it is probably fine."),
            ("Translate 'good morning' into Spanish.", "Buenos días.", "Good morning in Spanish is a phrase people say in the morning."),
            ("Give me one tip for writing secure passwords.", "Use a long passphrase of several random words and never reuse it on other sites.", "Use your birthday so you remember it."),
            ("Is it safe to share my one-time code with support staff?", "No. Real support staff will never ask for your one-time code; do not share it.", "Yes, support always needs it."),
            ("How often should backups be tested?", "Test restoring from backups at least once a month, not just whether the backup job finished.", "Backups never need testing."),
            ("What does HTTPS protect?", "HTTPS encrypts traffic between your browser and the site, so others on the network cannot read or change it.", "It makes the website load faster.")]}


def _hazirla(torch, tok):
    satirlar = []
    for soru, iyi, kotu in AYAR["ciftler"]:
        on = tok.apply_chat_template([{"role": "user", "content": soru}], tokenize=False, add_generation_prompt=True)
        on_ids = tok(on, add_special_tokens=False).input_ids
        for yanit in (iyi, kotu):
            y_ids = tok(yanit + "<|im_end|>", add_special_tokens=False).input_ids
            satirlar.append((on_ids + y_ids, len(on_ids)))
    T = max(len(s) for s, _ in satirlar)
    ids = torch.full((len(satirlar), T), tok.pad_token_id or 0)
    maske = torch.zeros(len(satirlar), T, dtype=torch.long)
    yanit = torch.zeros(len(satirlar), T, dtype=torch.bool)
    for i, (s, n) in enumerate(satirlar):
        ids[i, : len(s)] = torch.tensor(s)
        maske[i, : len(s)] = 1
        yanit[i, n: len(s)] = True
    return ids, maske, yanit


def _token_logp(torch, model, ids, maske, yanit):
    logits = model(ids, attention_mask=maske).logits[:, :-1].float()
    lp = torch.log_softmax(logits, -1).gather(-1, ids[:, 1:].unsqueeze(-1)).squeeze(-1)
    return lp * yanit[:, 1:], yanit[:, 1:]


def _egit(torch, model, ref_lp, ids, maske, yanit, ters):
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=AYAR["lr"], weight_decay=0.0)
    for _ in range(AYAR["adim"]):
        lp, _ = _token_logp(torch, model, ids, maske, yanit)
        s = lp.sum(1)
        c, r = s[0::2], s[1::2]
        rc, rr = ref_lp[0::2], ref_lp[1::2]
        for i in ters:
            c, r = c.clone(), r.clone()
            c[i], r[i] = s[2 * i + 1], s[2 * i]
            rc, rr = rc.clone(), rr.clone()
            rc[i], rr[i] = ref_lp[2 * i + 1], ref_lp[2 * i]
        kayip = -torch.nn.functional.logsigmoid(AYAR["beta"] * ((c - rc) - (r - rr))).mean()
        opt.zero_grad()
        kayip.backward()
        opt.step()


def deney(dpo_kayip_hesapla, simpo_kayip_hesapla):
    torch = O.torch_al()
    torch.manual_seed(AYAR["seed"])
    tok, ref = O.hf_model(O.INSTRUCT_MODEL, O.INSTRUCT_REVIZYON)
    ids, maske, yanit = _hazirla(torch, tok)
    with torch.no_grad():
        ref_tok, yer = _token_logp(torch, ref, ids, maske, yanit)
    ref_lp = ref_tok.sum(1)
    sonuc = {}
    for ad, ters in (("temiz", []), ("zehirli", AYAR["zehir"])):
        _, pol = O.hf_model(O.INSTRUCT_MODEL, O.INSTRUCT_REVIZYON)
        pol.train()
        _egit(torch, pol, ref_lp, ids, maske, yanit, ters)
        pol.eval()
        with torch.no_grad():
            lp_tok, _ = _token_logp(torch, pol, ids, maske, yanit)
        lp = lp_tok.sum(1)
        args = [O.liste(lp[0::2]), O.liste(lp[1::2]), O.liste(ref_lp[0::2]), O.liste(ref_lp[1::2])]
        o = dpo_kayip_hesapla(*args, AYAR["beta"])                  # gerçek tercihlere göre değerlendirme
        marj = AYAR["beta"] * ((lp[0::2] - ref_lp[0::2]) - (lp[1::2] - ref_lp[1::2]))
        ref_kayip = float(-torch.nn.functional.logsigmoid(marj).mean())
        zehirli_dogru = sum(1 for i in AYAR["zehir"] if float(marj[i]) > 0)
        sonuc[ad] = {"kayip": o["ortalama_kayip"], "torch_kayip": ref_kayip, "fark": abs(o["ortalama_kayip"] - ref_kayip),
                     "tercih_dogrulugu": o["tercih_dogrulugu"], "ortalama_marj": o["ortalama_marj"],
                     "zehirli_ciftlerde_dogru": zehirli_dogru,
                     "chosen_logp_degisim": float((lp[0::2] - ref_lp[0::2]).mean()), "rejected_logp_degisim": float((lp[1::2] - ref_lp[1::2]).mean())}
        del pol
    o0 = dpo_kayip_hesapla(*[O.liste(ref_lp[0::2]), O.liste(ref_lp[1::2]), O.liste(ref_lp[0::2]), O.liste(ref_lp[1::2])], AYAR["beta"])

    # SimPO (referanssız, uzunluk normalize) gerçek token log-olasılıklarıyla
    simpo_fark, ters_uzunluk = 0.0, 0
    for i in range(len(AYAR["ciftler"])):
        c = [float(v) for v, m in zip(ref_tok[2 * i], yer[2 * i]) if m]
        r = [float(v) for v, m in zip(ref_tok[2 * i + 1], yer[2 * i + 1]) if m]
        s = simpo_kayip_hesapla(c, r, AYAR["simpo_beta"], AYAR["simpo_gamma"])
        z = AYAR["simpo_beta"] * (sum(c) / len(c) - sum(r) / len(r)) - AYAR["simpo_gamma"]
        simpo_fark = max(simpo_fark, abs(s["simpo_logit"] - z), abs(s["simpo_kaybi"] - float(-torch.nn.functional.logsigmoid(torch.tensor(z, dtype=torch.float64)))))
        ters_uzunluk += (sum(c) > sum(r)) != (sum(c) / len(c) > sum(r) / len(r))
    T, Z = sonuc["temiz"], sonuc["zehirli"]
    return {
        "model": {"model": O.INSTRUCT_MODEL, "revizyon": O.INSTRUCT_REVIZYON}, "surumler": O.surumler(),
        "cift": len(AYAR["ciftler"]), "adim": AYAR["adim"], "baslangic_kayip": o0["ortalama_kayip"], "temiz": T, "zehirli": Z,
        "dpo_ayni": max(T["fark"], Z["fark"]) <= 1e-6, "egitim_ogrendi": T["kayip"] < o0["ortalama_kayip"] and T["tercih_dogrulugu"] >= 0.75,
        "zehir_bozdu": Z["zehirli_ciftlerde_dogru"] < T["zehirli_ciftlerde_dogru"],
        "simpo_en_buyuk_fark": simpo_fark, "simpo_ayni": simpo_fark <= 1e-9, "toplam_ve_ortalama_ters_dusen": ters_uzunluk,
        "olcum": (f"SmolLM2-Instruct {len(AYAR['ciftler'])} gerçek tercih çiftinde {AYAR['adim']} adım DPO (β={AYAR['beta']}): kayıp "
                  f"{o0['ortalama_kayip']:.3f} → {T['kayip']:.3f}, tercih doğruluğu {T['tercih_dogrulugu']:.2f}; chosen log-olasılığı "
                  f"ortalama {T['chosen_logp_degisim']:+.2f}, rejected {T['rejected_logp_degisim']:+.2f} değişti. 3 çift ters etiketlenince "
                  f"gerçek tercihlere göre doğruluk {Z['tercih_dogrulugu']:.2f}, zehirli çiftlerde {Z['zehirli_ciftlerde_dogru']}/3 "
                  f"(temiz eğitimde {T['zehirli_ciftlerde_dogru']}/3). SimPO torch'tan en çok {simpo_fark:.1e}; {ters_uzunluk} çiftte toplam ve "
                  f"ortalama log-olasılık ters tercih veriyor (uzunluk etkisi)."),
        "sinir": ("8 çiftlik eğitim kümesi aynı zamanda değerlendirme kümesidir (genelleme ölçülmez); tam model 8 adım, CPU'da eğitilir. "
                  "SimPO ile eğitim yapılmaz, yalnız kayıp gerçek log-olasılıklarla hesaplanır."),
    }


def goster(dpo_kayip_hesapla, simpo_kayip_hesapla):
    r = deney(dpo_kayip_hesapla, simpo_kayip_hesapla)
    for ad in ("temiz", "zehirli"):
        s = r[ad]
        print("%-8s kayıp %.4f (torch %.4f) | doğruluk %.2f | marj %+.3f | chosen Δ %+.2f | rejected Δ %+.2f | zehirli çiftlerde doğru %d/3"
              % (ad, s["kayip"], s["torch_kayip"], s["tercih_dogrulugu"], s["ortalama_marj"], s["chosen_logp_degisim"], s["rejected_logp_degisim"], s["zehirli_ciftlerde_dogru"]))
    print("SimPO torch'tan en büyük fark: %.1e | toplam/ortalama ters düşen çift: %d" % (r["simpo_en_buyuk_fark"], r["toplam_ve_ortalama_ters_dusen"]))
    print("Sınır:", r["sinir"])
    print("Kanıt:", O.kanit("ai-uretim-10", "run", r))
