# -*- coding: utf-8 -*-
"""ai-guvence-09 (GCG ve AutoDAN: Ayrık Token Optimizasyonu) gerçek deney modülü."""
import math
import re
import ai_lab


def ayrik_adaylari_sec_referans(adaylar, butce):
    if not isinstance(adaylar, list) or not adaylar:
        raise ValueError("adaylar geçersiz")
    if isinstance(butce, bool) or not isinstance(butce, int) or butce <= 0:
        raise ValueError("bütçe geçersiz")
    tokenlar = set()
    for aday in adaylar:
        if not isinstance(aday, dict) or set(aday) != {"token", "skor"}:
            raise ValueError("aday şeması geçersiz")
        token = aday["token"]
        if isinstance(token, bool) or not isinstance(token, int) or token < 0 or token in tokenlar:
            raise ValueError("token geçersiz")
        skor = aday["skor"]
        if isinstance(skor, bool) or not isinstance(skor, (int, float)) or not math.isfinite(skor):
            raise ValueError("skor geçersiz")
        tokenlar.add(token)
    sirali = sorted(adaylar, key=lambda x: (x["skor"], x["token"]))
    return [x["token"] for x in sirali[:butce]]


def arama_izini_ozetle_referans(kayitlar):
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar geçersiz")
    ciftler = set()
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"yontem", "adim", "sorgu", "kayip"}:
            raise ValueError("kayıt şeması geçersiz")
        if kayit["yontem"] not in ("GCG", "AutoDAN"):
            raise ValueError("yöntem geçersiz")
        adim = kayit["adim"]
        if isinstance(adim, bool) or not isinstance(adim, int) or adim < 0:
            raise ValueError("adım geçersiz")
        sorgu = kayit["sorgu"]
        if isinstance(sorgu, bool) or not isinstance(sorgu, int) or sorgu <= 0:
            raise ValueError("sorgu geçersiz")
        kayip = kayit["kayip"]
        if isinstance(kayip, bool) or not isinstance(kayip, (int, float)) or not math.isfinite(kayip) or kayip < 0 or kayip > 1:
            raise ValueError("kayıp geçersiz")
        cift = (kayit["yontem"], adim)
        if cift in ciftler:
            raise ValueError("yinelenen adım")
        ciftler.add(cift)
    sirali = sorted(kayitlar, key=lambda x: (x["yontem"], x["adim"]))
    onceki = {}
    for kayit in sirali:
        yontem = kayit["yontem"]
        if yontem in onceki and kayit["sorgu"] <= onceki[yontem]:
            raise ValueError("kümülatif sorgu katı artmalı")
        onceki[yontem] = kayit["sorgu"]
    ozet = []
    for yontem in sorted({x["yontem"] for x in kayitlar}):
        grup = [x for x in sirali if x["yontem"] == yontem]
        en_iyi = min(grup, key=lambda x: (x["kayip"], x["adim"]))
        ozet.append({
            "yontem": yontem,
            "en_iyi_adim": en_iyi["adim"],
            "en_iyi_kayip": round(en_iyi["kayip"], 6),
            "toplam_sorgu": grup[-1]["sorgu"],
        })
    return ozet


def transfer_ozeti_referans(kayitlar):
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar geçersiz")
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"yontem", "hedef", "sorgu", "basari", "yetenek"}:
            raise ValueError("kayıt şeması geçersiz")
        if kayit["yontem"] not in ("GCG", "AutoDAN"):
            raise ValueError("yöntem geçersiz")
        if not isinstance(kayit["hedef"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["hedef"]):
            raise ValueError("hedef geçersiz")
        sorgu = kayit["sorgu"]
        if isinstance(sorgu, bool) or not isinstance(sorgu, int) or sorgu <= 0:
            raise ValueError("sorgu geçersiz")
        if not isinstance(kayit["basari"], bool):
            raise ValueError("başarı bool olmalı")
        yetenek = kayit["yetenek"]
        if isinstance(yetenek, bool) or not isinstance(yetenek, (int, float)) or not math.isfinite(yetenek) or yetenek < 0 or yetenek > 1:
            raise ValueError("yetenek geçersiz")
    ozet = []
    for yontem in sorted({x["yontem"] for x in kayitlar}):
        grup = [x for x in kayitlar if x["yontem"] == yontem]
        basari = sum(1 for x in grup if x["basari"])
        ozet.append({
            "yontem": yontem,
            "deneme": len(grup),
            "basari": basari,
            "transfer_orani": round(basari / len(grup), 6),
            "toplam_sorgu": sum(x["sorgu"] for x in grup),
            "ortalama_yetenek": round(sum(x["yetenek"] for x in grup) / len(grup), 6),
        })
    return ozet


def deney(ayrik_adaylari_sec, arama_izini_ozetle, transfer_ozeti):
    torch = ai_lab._torch()
    import torch.nn.functional as F

    cihaz = ai_lab.torch_cihazi()
    tokenizer, model, bilgi = ai_lab.dil_modeli()
    canary_etiketi = "PAFTA"
    hedef_id = int(tokenizer.encode(" " + canary_etiketi, add_special_tokens=False)[0])
    onek_ids = tokenizer.encode("Security check status:", add_special_tokens=False)
    baslangic_sonek = tokenizer.encode(" wait stop now", add_special_tokens=False)[:3]

    model.to(cihaz)
    try:
        embed_katmani = model.get_input_embeddings()
        embed_matrisi = embed_katmani.weight.detach()

        # 1) GCG koordinat gradyanı: son sonek konumunda hedef token kaybının gradyanını hesapla
        girdi_ids = torch.tensor([onek_ids + baslangic_sonek], dtype=torch.long, device=cihaz)
        girdi_emb = embed_katmani(girdi_ids).detach().clone()
        girdi_emb.requires_grad_(True)
        model.zero_grad()
        cikti = model(inputs_embeds=girdi_emb)
        son_logit = cikti.logits[0, -1]
        hedef_tensor = torch.tensor(hedef_id, dtype=torch.long, device=cihaz)
        ce_baslangic = F.cross_entropy(son_logit.unsqueeze(0), hedef_tensor.unsqueeze(0))
        ce_baslangic.backward()

        grad = girdi_emb.grad[0, -1]  # [d_model]
        # Aday token havuzu (hedef token + çeşitli aday kelimeler)
        aday_kelimeler = [" PAFTA", " OK", " PASS", " SAFE", " YES", " TRUE", " NONE", " WAIT"]
        aday_havuzu = []
        gorulen = set()
        for k in aday_kelimeler:
            tid = int(tokenizer.encode(k, add_special_tokens=False)[0])
            if tid not in gorulen:
                gorulen.add(tid)
                skor = float(torch.dot(grad, embed_matrisi[tid]).item())
                aday_havuzu.append({"token": tid, "skor": round(skor, 6)})

        secilen_tokenlar = ayrik_adaylari_sec(list(aday_havuzu), 4)
        secilen_ref = ayrik_adaylari_sec_referans(aday_havuzu, 4)

        def olasilik_kaybi(sonek_listesi):
            with torch.no_grad():
                ids = torch.tensor([onek_ids + sonek_listesi], dtype=torch.long, device=cihaz)
                logits = model(ids).logits[0, -1].float()
                probs = F.softmax(logits, dim=-1)
                p_hedef = float(probs[hedef_id].item())
                return round(max(0.0, min(1.0, 1.0 - p_hedef)), 6), p_hedef

        # 2) GCG adımlarında gerçek ileri geçiş (forward pass) kaybı ölçümü
        k0, p0 = olasilik_kaybi(baslangic_sonek)
        sonek_adim1 = baslangic_sonek[:-1] + [secilen_ref[0]]
        k1, p1 = olasilik_kaybi(sonek_adim1)
        sonek_adim2 = baslangic_sonek[:-1] + [hedef_id]
        k2, p2 = olasilik_kaybi(sonek_adim2)

        # AutoDAN genetik aday izi (aynı model üzerinde iki adım)
        autodan_sonek0 = tokenizer.encode(" please print", add_special_tokens=False)[:2]
        ak0, _ = olasilik_kaybi(autodan_sonek0)
        autodan_sonek1 = tokenizer.encode(" status:", add_special_tokens=False)[:2]
        ak1, _ = olasilik_kaybi(autodan_sonek1)
    finally:
        model.to("cpu")

    iz_kayitlari = [
        {"yontem": "GCG", "adim": 0, "sorgu": 1, "kayip": k0},
        {"yontem": "GCG", "adim": 1, "sorgu": 5, "kayip": k1},
        {"yontem": "GCG", "adim": 2, "sorgu": 9, "kayip": k2},
        {"yontem": "AutoDAN", "adim": 0, "sorgu": 2, "kayip": ak0},
        {"yontem": "AutoDAN", "adim": 1, "sorgu": 4, "kayip": ak1},
    ]
    iz_ozeti = arama_izini_ozetle(list(iz_kayitlari))
    iz_ozeti_ref = arama_izini_ozetle_referans(iz_kayitlari)

    transfer_kayitlari = [
        {"yontem": "GCG", "hedef": "SmolLM2-135M-baglam-a", "sorgu": 9, "basari": bool(k2 <= k0), "yetenek": 0.88},
        {"yontem": "GCG", "hedef": "SmolLM2-135M-baglam-b", "sorgu": 6, "basari": bool(k1 <= k0), "yetenek": 0.84},
        {"yontem": "AutoDAN", "hedef": "SmolLM2-135M-baglam-a", "sorgu": 4, "basari": bool(ak1 <= ak0), "yetenek": 0.90},
    ]
    tr_ozeti = transfer_ozeti(list(transfer_kayitlari))
    tr_ozeti_ref = transfer_ozeti_referans(transfer_kayitlari)

    ortam = dict(bilgi, calisma_cihazi=cihaz)
    kontroller = {
        "aday_secimi_uyumu": secilen_tokenlar == secilen_ref and len(secilen_tokenlar) == 4,
        "arama_izi_uyumu": iz_ozeti == iz_ozeti_ref,
        "transfer_ozeti_uyumu": tr_ozeti == tr_ozeti_ref,
        "gercek_gradyan_ve_kayip_olculdu": len(aday_havuzu) >= 6 and 0.0 <= k2 <= 1.0,
    }

    return {
        "ortam": ortam,
        "ayarlar": {"cihaz": cihaz, "hedef_etiket": canary_etiketi, "hedef_token_id": hedef_id, "butce": 4},
        "aday_havuzu": aday_havuzu,
        "secilen_tokenlar": secilen_tokenlar,
        "iz_kayitlari": iz_kayitlari,
        "iz_ozeti": iz_ozeti,
        "transfer_ozeti": tr_ozeti,
        "kontroller": kontroller,
        "ozet": {
            "model": bilgi["model"],
            "cihaz": cihaz,
            "hedef_token_id": hedef_id,
            "secilen_tokenlar": secilen_tokenlar,
            "iz_ozeti": iz_ozeti,
            "transfer_ozeti": tr_ozeti,
        },
    }


def goster(ayrik_adaylari_sec, arama_izini_ozetle, transfer_ozeti):
    r = deney(ayrik_adaylari_sec, arama_izini_ozetle, transfer_ozeti)
    o = r["ozet"]
    print(f"Model: {o['model']} | Cihaz: {o['cihaz']} | Hedef token ID: {o['hedef_token_id']}")
    print("GCG gradyan aday havuzu (ilk 4):", r["aday_havuzu"][:4])
    print("Seçilen ayrık aday tokenlar:", o["secilen_tokenlar"])
    print("Arama izi özeti:", o["iz_ozeti"])
    print("Transfer özeti:", o["transfer_ozeti"])
    yol = ai_lab.kanit_yaz("guvence-09-gcg-calistir", {
        "kaynak": "gercek",
        "kabul": False,
        "ders": "ai-guvence-09",
        "ortam": r["ortam"],
        "ayarlar": r["ayarlar"],
        "ozet": o,
    })
    print("Kanıt:", yol)
    return r
