# -*- coding: utf-8 -*-
"""ai-guvence-08 gerçek deneyi: PyTorch autograd ile çok adımlı PGD ve saldırı gücü eğrileri.

Öğrencinin `pgd_ayari_dogrula`, `pgd_izini_uret` ve `pgd_egri_raporu` işlevleri,
`ai_lab.fgsm_siniflandirici()` ile eğitilen PyTorch 64-32-4 MLP modeli üzerinde
gerçek `torch.autograd.grad` gradyanları ve çok adımlı projeksiyon izleriyle sınanır.
"""
import copy
import math
import re
import ai_lab


AYAR = {"id": "canli-pgd-08", "epsilon": 0.15, "alpha": 0.06, "adim": 3}


def pgd_ayari_dogrula_referans(ayar):
    if not isinstance(ayar, dict) or set(ayar) != {"id", "epsilon", "alpha", "adim"}:
        raise ValueError("ayar şeması geçersiz")
    if not isinstance(ayar["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", ayar["id"]):
        raise ValueError("kimlik geçersiz")
    for alan in ("epsilon", "alpha"):
        deger = ayar[alan]
        if isinstance(deger, bool) or not isinstance(deger, (int, float)) or not math.isfinite(deger) or deger < 0 or deger > 1:
            raise ValueError("bütçe geçersiz")
    if ayar["alpha"] > ayar["epsilon"]:
        raise ValueError("alpha epsilonu aşamaz")
    if isinstance(ayar["adim"], bool) or not isinstance(ayar["adim"], int) or ayar["adim"] <= 0:
        raise ValueError("adım geçersiz")
    return {"id": ayar["id"], "epsilon": ayar["epsilon"], "alpha": ayar["alpha"], "adim": ayar["adim"]}


def pgd_izini_uret_referans(x, gradyanlar, ayar):
    a = pgd_ayari_dogrula_referans(ayar)
    if not isinstance(x, list) or not x:
        raise ValueError("x geçersiz")
    for deger in x:
        if isinstance(deger, bool) or not isinstance(deger, (int, float)) or not math.isfinite(deger) or deger < 0 or deger > 1:
            raise ValueError("x öğesi geçersiz")
    if not isinstance(gradyanlar, list) or len(gradyanlar) != a["adim"]:
        raise ValueError("gradyanlar geçersiz")
    for gradyan in gradyanlar:
        if not isinstance(gradyan, list) or len(gradyan) != len(x):
            raise ValueError("gradyan boyutu geçersiz")
        for deger in gradyan:
            if isinstance(deger, bool) or not isinstance(deger, (int, float)) or not math.isfinite(deger):
                raise ValueError("gradyan değeri geçersiz")
    x0 = list(x)
    son = list(x)
    iz = []
    for adim, gradyan in enumerate(gradyanlar, 1):
        yeni = []
        for i, gv in enumerate(gradyan):
            isaret = 1 if gv > 0 else -1 if gv < 0 else 0
            deger = min(1, max(0, son[i] + a["alpha"] * isaret))
            deger = min(x0[i] + a["epsilon"], max(x0[i] - a["epsilon"], deger))
            yeni.append(deger)
        son = yeni
        iz.append({"adim": adim, "x": [round(v, 6) for v in son]})
    return {
        "id": a["id"],
        "son": [round(v, 6) for v in son],
        "l_inf": round(max(abs(u - v) for u, v in zip(son, x0)), 6),
        "iz": iz,
    }


def pgd_egri_raporu_referans(kayitlar):
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar geçersiz")
    ciftler = set()
    tabanlar = {}
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"epsilon", "adim", "dogruluk", "l_inf"}:
            raise ValueError("kayıt şeması geçersiz")
        for alan in ("epsilon", "dogruluk", "l_inf"):
            deger = kayit[alan]
            if isinstance(deger, bool) or not isinstance(deger, (int, float)) or not math.isfinite(deger) or deger < 0 or deger > 1:
                raise ValueError("ölçüm geçersiz")
        adim = kayit["adim"]
        if isinstance(adim, bool) or not isinstance(adim, int) or adim < 0:
            raise ValueError("adım geçersiz")
        cift = (kayit["epsilon"], adim)
        if cift in ciftler or kayit["l_inf"] > kayit["epsilon"] + 1e-9:
            raise ValueError("çift/l_inf geçersiz")
        if adim == 0:
            if kayit["l_inf"] != 0:
                raise ValueError("taban l_inf sıfır olmalı")
            tabanlar[kayit["epsilon"]] = kayit["dogruluk"]
        ciftler.add(cift)
    epsilonlar = {x["epsilon"] for x in kayitlar}
    if any(e not in tabanlar for e in epsilonlar):
        raise ValueError("taban eksik")
    satirlar = []
    for kayit in kayitlar:
        kayip = tabanlar[kayit["epsilon"]] - kayit["dogruluk"]
        satirlar.append({
            "epsilon": kayit["epsilon"],
            "adim": kayit["adim"],
            "dogruluk": kayit["dogruluk"],
            "l_inf": kayit["l_inf"],
            "kayip": round(kayip, 6),
            "_ham": kayip,
        })
    satirlar.sort(key=lambda x: (x["epsilon"], x["adim"]))
    ozet = []
    for epsilon in sorted(epsilonlar):
        grup = [x for x in satirlar if x["epsilon"] == epsilon]
        son = max(grup, key=lambda x: x["adim"])
        maks = max(x["_ham"] for x in grup)
        ozet.append({
            "epsilon": epsilon,
            "taban_dogruluk": tabanlar[epsilon],
            "son_adim": son["adim"],
            "son_dogruluk": son["dogruluk"],
            "maksimum_kayip": round(maks, 6),
        })
    for s in satirlar:
        del s["_ham"]
    return {"satirlar": satirlar, "ozet": ozet}


def deney(pgd_ayari_dogrula, pgd_izini_uret, pgd_egri_raporu):
    model, (X, Y), bilgi = ai_lab.fgsm_siniflandirici()
    import torch
    import torch.nn.functional as F

    ogr_ayar = pgd_ayari_dogrula(copy.deepcopy(AYAR))
    ref_ayar = pgd_ayari_dogrula_referans(copy.deepcopy(AYAR))

    # Tek bir test örneğinde 3 adımlı gerçek autograd gradyanlarını topla
    x0_tensor = X[0:1].clone().detach()
    y0_tensor = Y[0:1].clone().detach()
    x_cur = x0_tensor.clone()
    canli_gradyanlar = []
    for _ in range(AYAR["adim"]):
        x_in = x_cur.clone().detach().requires_grad_(True)
        kayip = F.cross_entropy(model(x_in), y0_tensor)
        g, = torch.autograd.grad(kayip, x_in)
        g_list = [round(float(v), 6) for v in g[0].tolist()]
        canli_gradyanlar.append(g_list)
        with torch.no_grad():
            x_cur = (x_cur + AYAR["alpha"] * g.sign()).clamp(0, 1)
            x_cur = torch.max(torch.min(x_cur, x0_tensor + AYAR["epsilon"]), x0_tensor - AYAR["epsilon"])

    x0_list = [round(float(v), 6) for v in x0_tensor[0].tolist()]
    ogr_iz = pgd_izini_uret(copy.deepcopy(x0_list), copy.deepcopy(canli_gradyanlar), copy.deepcopy(AYAR))
    ref_iz = pgd_izini_uret_referans(copy.deepcopy(x0_list), copy.deepcopy(canli_gradyanlar), copy.deepcopy(AYAR))

    # İki epsilon (0.1 ve 0.2) ve 0..3 adımda tüm test kümesinde canlı PGD eğrisi
    egri_girdisi = []
    with torch.no_grad():
        temiz_dogruluk = round(float((model(X).argmax(1) == Y).float().mean().item()), 6)
    for eps in (0.1, 0.2):
        alpha = round(eps / 2, 6)
        egri_girdisi.append({"epsilon": eps, "adim": 0, "dogruluk": temiz_dogruluk, "l_inf": 0.0})
        x_adv = X.clone().detach()
        for adim in range(1, 4):
            x_in = x_adv.clone().detach().requires_grad_(True)
            kayip = F.cross_entropy(model(x_in), Y)
            g, = torch.autograd.grad(kayip, x_in)
            with torch.no_grad():
                x_adv = (x_adv + alpha * g.sign()).clamp(0, 1)
                x_adv = torch.max(torch.min(x_adv, X + eps), X - eps)
                acc = round(float((model(x_adv).argmax(1) == Y).float().mean().item()), 6)
                linf = round(float((x_adv - X).abs().max().item()), 6)
            egri_girdisi.append({"epsilon": eps, "adim": adim, "dogruluk": acc, "l_inf": min(eps, linf)})

    karisik_egri = list(reversed(egri_girdisi))
    ogr_egri = pgd_egri_raporu(copy.deepcopy(karisik_egri))
    ref_egri = pgd_egri_raporu_referans(copy.deepcopy(karisik_egri))

    kontroller = {
        "ayar_uyumu": ogr_ayar == ref_ayar,
        "iz_uyumu": ogr_iz == ref_iz and ogr_iz.get("l_inf", 1.0) <= AYAR["epsilon"] + 1e-6,
        "egri_uyumu": ogr_egri == ref_egri,
        "saldiri_kaybi_pozitif": any(o["maksimum_kayip"] > 0 for o in ref_egri["ozet"]),
    }
    ozet = {
        "torch_surum": bilgi.get("torch"),
        "temiz_dogruluk": temiz_dogruluk,
        "ornek_l_inf": ref_iz["l_inf"],
        "egri_ozeti": ref_egri["ozet"],
    }
    return {
        "ayar": ogr_ayar,
        "ornek_iz": {"l_inf": ogr_iz.get("l_inf"), "adim_sayisi": len(ogr_iz.get("iz", []))},
        "egri_raporu": ogr_egri,
        "kontroller": kontroller,
        "ozet": ozet,
    }


def goster(pgd_ayari_dogrula, pgd_izini_uret, pgd_egri_raporu):
    rapor = deney(pgd_ayari_dogrula, pgd_izini_uret, pgd_egri_raporu)
    print("Canlı PGD iz özeti:", rapor["ornek_iz"])
    print("Canlı PGD eğri özeti:", rapor["egri_raporu"].get("ozet"))
