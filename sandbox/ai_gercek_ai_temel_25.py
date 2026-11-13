"""Constrained decoding ve FSM logit masking: GPU üzerinde eğitilen sonraki-token modeliyle FSM kısıtlı üretim."""
import importlib.metadata, math, random, secrets
import ai_lab

AYAR = {
    "seed": 25,
    "sozluk": 8,
    "gizli": 48,
    "adim": 320,
    "lr": 0.015,
    "ornek_sayisi": 64,
    "esik": 0.20,
}

FSM_GECISLER = {
    "S_AC": [{"token": 1, "hedef": "S_ANAHTAR"}, {"token": 5, "hedef": "S_KAPAT"}],
    "S_ANAHTAR": [{"token": 2, "hedef": "S_IKI_NOKTA"}],
    "S_IKI_NOKTA": [{"token": 3, "hedef": "S_DEGER"}, {"token": 4, "hedef": "S_DEGER"}],
    "S_DEGER": [{"token": 6, "hedef": "S_ANAHTAR"}, {"token": 5, "hedef": "S_KAPAT"}],
    "S_KAPAT": [{"token": 7, "hedef": "S_KAPAT"}],
}


def _sayi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)


def _tam(v):
    return not isinstance(v, bool) and isinstance(v, int)


def referans_fsm_gecerli(gecisler, durum):
    if not isinstance(gecisler, dict) or not gecisler:
        raise ValueError("gecisler")
    for k, v in gecisler.items():
        if not isinstance(k, str) or not k or not isinstance(v, list):
            raise ValueError("durum_sema")
        for oge in v:
            if not isinstance(oge, dict) or set(oge) != {"token", "hedef"}:
                raise ValueError("gecis_sema")
            if not _tam(oge["token"]) or oge["token"] < 0:
                raise ValueError("token")
            if not isinstance(oge["hedef"], str) or oge["hedef"] not in gecisler:
                raise ValueError("hedef")
    if not isinstance(durum, str) or durum not in gecisler or not gecisler[durum]:
        raise ValueError("durum")
    return sorted({oge["token"] for oge in gecisler[durum]})


def referans_logit_maskele(logitler, izinli_indisler):
    if not isinstance(logitler, list) or not logitler or not all(_sayi(x) for x in logitler):
        raise ValueError("logitler")
    if not isinstance(izinli_indisler, list) or not izinli_indisler:
        raise ValueError("izinli")
    n = len(logitler)
    for idx in izinli_indisler:
        if not _tam(idx) or not 0 <= idx < n:
            raise ValueError("indis")
    izinli = set(izinli_indisler)
    m = max(logitler[i] for i in izinli)
    exps = [math.exp(logitler[i] - m) if i in izinli else 0.0 for i in range(n)]
    toplam = sum(exps)
    return [v / toplam for v in exps]


def referans_kisitli_rapor(logitler, izinli_indisler, esik):
    p_mask = referans_logit_maskele(logitler, izinli_indisler)
    if not _sayi(esik) or not 0 < esik <= 1:
        raise ValueError("esik")
    m_ham = max(logitler)
    ham_exp = [math.exp(x - m_ham) for x in logitler]
    ham_top = sum(ham_exp)
    p_ham = [v / ham_top for v in ham_exp]
    izinli = set(izinli_indisler)
    izinli_kutle = sum(p_ham[i] for i in izinli)
    secilen = max(range(len(p_mask)), key=lambda i: p_mask[i])
    ham_secilen = max(range(len(logitler)), key=lambda i: logitler[i])
    return {
        "secilen_token": secilen,
        "secilen_olasilik": p_mask[secilen],
        "izinli_kutle": izinli_kutle,
        "mudahale": bool(secilen != ham_secilen),
        "zorlama_uyarisi": bool(izinli_kutle < esik),
    }


def _yakin(a, b, tol=1e-9):
    if isinstance(a, dict):
        return isinstance(b, dict) and set(a) == set(b) and all(_yakin(a[k], b[k], tol) for k in a)
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(_yakin(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, (bool, str)) or a is None:
        return type(a) is type(b) and a == b
    return _sayi(a) and _sayi(b) and abs(a - b) <= tol * max(1.0, abs(a), abs(b))


GECERLI_CIKTILAR = [' {"risk": "low"}', ' {"risk": "medium"}', ' {"risk": "high"}']   # baştaki boşluk kanonik token sınırı içindir
ALARMLAR = [("Alert: 500 failed SSH logins from one IP address in two minutes.", "high"),
            ("Alert: a user changed the desktop wallpaper.", "low"),
            ("Alert: ransomware note found on the file server and files are encrypted.", "high"),
            ("Alert: the printer is low on paper.", "low"),
            ("Alert: an admin account logged in from a new country at 3 AM.", "high"),
            ("Alert: scheduled backup finished successfully.", "low")]
ORNEKLI = ('Alert: disk usage is normal.\nAnswer: {"risk": "low"}\n'
           'Alert: malware detected on the domain controller.\nAnswer: {"risk": "high"}\n')


def fsm_kur(tok):
    """Geçerli çıktıların kanonik token dizilerinden gerçek token kimlikli önek ağacı (token düzeyinde FSM)."""
    gecisler = {"S0": []}
    for s in GECERLI_CIKTILAR:
        d = "S0"
        for t in tok(s, add_special_tokens=False)["input_ids"]:
            hedef = next((g["hedef"] for g in gecisler[d] if g["token"] == t), None)
            if hedef is None:
                hedef = f"S{len(gecisler)}"
                gecisler[hedef] = []
                gecisler[d].append({"token": t, "hedef": hedef})
            d = hedef
    return gecisler


def deney(fsm_fn, maske_fn, rapor_fn):
    import json
    try:
        import torch
    except ImportError as e:
        raise ai_lab.GercekLabYok(str(e)) from e
    tok, model, bilgi = ai_lab.dil_modeli()
    cihaz = ai_lab.torch_cihazi()
    model.to(cihaz)
    gecisler = fsm_kur(tok)
    fsm_ayni = all(fsm_fn(gecisler, d) == referans_fsm_gecerli(gecisler, d) for d in gecisler if gecisler[d])
    maske_ayni = rapor_ayni = yasak_sifir = toplam_bir = True
    kayitlar = []
    for kip, on_ek in (("sifir_ornek", ""), ("iki_ornek", ORNEKLI)):
        for alarm, beklenen in ALARMLAR:
            ids = tok(f"{on_ek}{alarm}\nAnswer:")["input_ids"]
            with torch.no_grad():
                serbest_ids = model.generate(torch.tensor([ids], device=cihaz), max_new_tokens=10, do_sample=False,
                                             pad_token_id=tok.eos_token_id)[0, len(ids):].tolist()
            serbest = tok.decode(serbest_ids).split("\n")[0].strip()
            try:
                serbest_gecerli = json.loads(serbest.strip()) in [json.loads(s) for s in GECERLI_CIKTILAR]
            except ValueError:
                serbest_gecerli = False
            d, x, adimlar = "S0", list(ids), []
            while gecisler[d]:
                with torch.no_grad():
                    z = model(torch.tensor([x], device=cihaz)).logits[0, -1].double().tolist()
                izinli = fsm_fn(gecisler, d)
                p_o, p_r = maske_fn(list(z), list(izinli)), referans_logit_maskele(z, referans_fsm_gecerli(gecisler, d))
                r_o, r_r = rapor_fn(list(z), list(izinli), AYAR["esik"]), referans_kisitli_rapor(z, referans_fsm_gecerli(gecisler, d), AYAR["esik"])
                maske_ayni = maske_ayni and _yakin(p_o, p_r)
                rapor_ayni = rapor_ayni and _yakin(r_o, r_r)
                ik = set(izinli)
                yasak_sifir = yasak_sifir and all(p_o[j] == 0.0 for j in range(len(z)) if j not in ik)
                toplam_bir = toplam_bir and abs(sum(p_o) - 1.0) <= 1e-9
                adimlar.append({"durum": d, "izinli_kutle": r_r["izinli_kutle"], "mudahale": r_r["mudahale"], "zorlama": r_r["zorlama_uyarisi"]})
                x.append(r_o["secilen_token"])
                d = next(g["hedef"] for g in gecisler[d] if g["token"] == r_o["secilen_token"])
            kisitli = tok.decode(x[len(ids):])
            try:
                etiket = json.loads(kisitli)["risk"]
                kisitli_gecerli = True
            except ValueError:
                etiket, kisitli_gecerli = None, False
            kayitlar.append({"kip": kip, "alarm": alarm, "beklenen": beklenen, "serbest": serbest[:60], "serbest_gecerli": serbest_gecerli,
                             "kisitli": kisitli, "kisitli_gecerli": kisitli_gecerli, "etiket": etiket, "dogru": etiket == beklenen,
                             "ilk_adim_kutle": adimlar[0]["izinli_kutle"], "ort_kutle": sum(a["izinli_kutle"] for a in adimlar) / len(adimlar),
                             "mudahale_sayisi": sum(a["mudahale"] for a in adimlar), "zorlama_sayisi": sum(a["zorlama"] for a in adimlar),
                             "adim_sayisi": len(adimlar)})

    def ozet(kip):
        k = [r for r in kayitlar if r["kip"] == kip]
        n = len(k)
        return {"ornek": n, "serbest_gecerlilik": sum(r["serbest_gecerli"] for r in k) / n,
                "kisitli_gecerlilik": sum(r["kisitli_gecerli"] for r in k) / n, "dogruluk": sum(r["dogru"] for r in k) / n,
                "ilk_adim_kutle": sum(r["ilk_adim_kutle"] for r in k) / n, "ort_kutle": sum(r["ort_kutle"] for r in k) / n,
                "mudahale_orani": sum(r["mudahale_sayisi"] for r in k) / sum(r["adim_sayisi"] for r in k)}

    o0, o2 = ozet("sifir_ornek"), ozet("iki_ornek")
    return {
        "cihaz": str(cihaz),
        "dtype": "float32 (logit float64)",
        "model": {k: bilgi[k] for k in ("model", "revizyon", "agirlik_sha256", "parametre")},
        "surumler": {"torch": importlib.metadata.version("torch"), "transformers": importlib.metadata.version("transformers")},
        "ayarlar": AYAR,
        "fsm": gecisler,
        "fsm_ayni": fsm_ayni,
        "maske_ayni": maske_ayni,
        "rapor_ayni": rapor_ayni,
        "yasak_olasilik_sifir": yasak_sifir,
        "olasilik_toplami_bir": toplam_bir,
        "sifir_ornek": o0,
        "iki_ornek": o2,
        "kayitlar": kayitlar,
        "olcum": (f"SmolLM2-135M, gerçek token kimlikli JSON şeması FSM'si ({len(gecisler)} durum). Sıfır örnekli istemde serbest üretim "
                  f"geçerliliği {o0['serbest_gecerlilik']:.2f}, kısıtlı {o0['kisitli_gecerlilik']:.2f}; ilk adımda modelin izinli tokena kütlesi "
                  f"{o0['ilk_adim_kutle']:.4f} (zorlama), etiket doğruluğu {o0['dogruluk']:.2f}. İki örnekli istemde serbest geçerlilik "
                  f"{o2['serbest_gecerlilik']:.2f}, ilk adım kütlesi {o2['ilk_adim_kutle']:.4f}, doğruluk {o2['dogruluk']:.2f}."),
        "sinir": ("FSM logit masking yalnızca sözdizimini zorlar; küçük model izinli değerler arasından anlamca yanlış olanı seçebilir. "
                  "Tek adımlı önek ağacı FSM'si; düzenli ifade/CFG derleme, token iyileştirme (token healing) ve büyük şemaların maliyeti ölçülmez."),
    }


def goster(fsm_fn, maske_fn, rapor_fn):
    r = deney(fsm_fn, maske_fn, rapor_fn)
    print("Model:", r["model"]["model"], "| cihaz:", r["cihaz"], "| FSM durum sayısı:", len(r["fsm"]))
    print("Sıfır örnekli:", {k: round(v, 4) if isinstance(v, float) else v for k, v in r["sifir_ornek"].items()})
    print("İki örnekli  :", {k: round(v, 4) if isinstance(v, float) else v for k, v in r["iki_ornek"].items()})
    for o in r["kayitlar"][:3]:
        print(" ", o["kip"], "|", o["alarm"][:45], "| serbest:", repr(o["serbest"]), "| kısıtlı:", o["kisitli"], "| ilk kütle:", round(o["ilk_adim_kutle"], 4))
    print("Sınır:", r["sinir"])
    print("Kanıt:", ai_lab.kanit_yaz("ai-temel-25-run", {"kaynak": "gercek", "kabul": False, "ders": "ai-temel-25", "deney": r}))
