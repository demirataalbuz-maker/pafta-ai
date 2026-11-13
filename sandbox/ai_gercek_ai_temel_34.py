# -*- coding: utf-8 -*-
"""ai-temel-34 gerçek deney: yerel llama3.2:3b sekiz çok adımlı aritmetik problemine T=1.0 ile altışar çözüm üretir. Cevaplar ayrıştırılır;
Qwen2.5-0.5B-Instruct her çözüme "doğru mu?" sorusunun gerçek Yes olasılığıyla doğrulayıcı skoru verir. Öğrencinin
çoğunluk/best-of-N işlevi ve test-time compute eğrisi bu gerçek örneklerle hesaplanır ve bağımsız hesapla karşılaştırılır."""
import re
import ai_lab
from sandbox import ai_uretim_ortak as O

AYAR = {"model": "llama3.2:3b", "n": 6, "sicaklik": 1.0, "N_listesi": [1, 2, 4, 6], "dpo_beta": 0.1, "dpo_lr": 5e-5, "dpo_tur": 3, "dpo_katman": 4,
        "problemler": [
            ("What is the smallest number greater than 500 that is divisible by 6, 8 and 15?", 600),
            ("If today is Wednesday, what day of the week is it 100 days from today? Give the day as a number where Monday = 1 and Sunday = 7.", 5),
            ("How many integers from 1 to 500 inclusive are divisible by 3 or by 5 but not by 15?", 200),
            ("A clock shows 3:40. What is the smaller angle, in degrees, between the hour hand and the minute hand?", 130),
            ("How many trailing zeros does 125 factorial (125!) have?", 31),
            ("A sequence starts 2, 5, 11, 23 and each term is twice the previous term plus 1. What is the 10th term?", 1535),
            ("Pipe A fills a tank in 6 hours, pipe B fills it in 9 hours and a drain empties it in 18 hours. With all three open, how many hours does it take to fill the empty tank?", 4.5),
            ("What is the sum of all two-digit numbers whose digits add up to 9?", 486)]}


def _cevap(metin):
    m = re.findall(r"Answer:\s*\$?(-?[\d,]*\.?\d+)", metin)
    if not m:
        m = re.findall(r"-?\d[\d,]*\.?\d*", metin)
    if not m:
        return ""
    v = m[-1].replace(",", "").rstrip(".")
    try:
        f = float(v)
        return str(int(f)) if f == int(f) else str(round(f, 4))
    except ValueError:
        return v


def _evet(torch, tok, model, soru, cozum):
    m = [{"role": "user", "content": f"Problem: {soru}\n\nProposed solution:\n{cozum[-600:]}\n\nIs the final answer of the proposed solution correct? Answer Yes or No."}]
    ids = tok(tok.apply_chat_template(m, tokenize=False, add_generation_prompt=True), return_tensors="pt").input_ids
    with torch.no_grad():
        lg = model(ids).logits[0, -1].float()
    y, n = tok.convert_tokens_to_ids("Yes"), tok.convert_tokens_to_ids("No")
    return float(torch.softmax(lg[[y, n]], 0)[0])


def _sayilar(metin):
    out = []
    for v in re.findall(r"-?\d[\d,]*\.?\d*", metin):
        v = v.replace(",", "").rstrip(".")
        try:
            f = float(v)
            out.append(str(int(f)) if f == int(f) else str(round(f, 4)))
        except ValueError:
            pass
    return out


def _dogrulayici_istismari(torch, tok, ver, ornekler, cevaplar, dogrular):
    """RLVR'de ödül doğrulayıcıdan gelir. Gevşek doğrulayıcı (doğru sayı metinde herhangi bir yerde geçiyor mu?) ile katı doğrulayıcı
    (son cevap doğru mu?) gerçek örneklerde ve sayı sıralayan bir 'spam' cevapta karşılaştırılır."""
    katı = [[c == d for c in ca] for ca, d in zip(cevaplar, dogrular)]
    gevsek = [[d in _sayilar(y) for y in cv] for cv, d in zip(ornekler, dogrular)]
    spam = "Possible answers: " + " ".join(str(i) for i in range(0, 2001)) + " 4.5. Answer: 4.5"
    spam_qwen = [_evet(torch, tok, ver, soru, spam) for soru, _ in AYAR["problemler"]]
    n = sum(len(x) for x in katı)
    return {"kati_oran": sum(map(sum, katı)) / n, "gevsek_oran": sum(map(sum, gevsek)) / n,
            "gevsek_ama_yanlis": sum(g and not k for gs, ks in zip(gevsek, katı) for g, k in zip(gs, ks)),
            "spam_gevsek_gecen": sum(d in _sayilar(spam) for d in dogrular), "spam_kati_gecen": sum(_cevap(spam) == d for d in dogrular),
            "spam_qwen_ort_skor": sum(spam_qwen) / len(spam_qwen), "problem": len(dogrular)}


def _dpo(torch, ornekler, cevaplar, dogrular):
    """Tercih aşaması: llama'nın doğru (seçilen) ve yanlış (reddedilen) çözümleri SmolLM2-Instruct'ta DPO ile eğitilir."""
    import copy
    tok, ref = O.hf_model(O.INSTRUCT_MODEL, O.INSTRUCT_REVIZYON)
    ciftler = []
    for (soru, _), cv, ca, d in zip(AYAR["problemler"], ornekler, cevaplar, dogrular):
        iyi = [y for y, c in zip(cv, ca) if c == d]
        kotu = [y for y, c in zip(cv, ca) if c != d]
        for j in range(min(2, len(iyi), len(kotu))):
            ciftler.append((soru, iyi[j], kotu[j]))
    if len(ciftler) < 2:
        return {"cift": len(ciftler), "yapildi": False}
    cihaz = ai_lab.torch_cihazi()
    kilit = ai_lab.gpu_kilidi_al() if cihaz == "cuda" else None
    try:
        r0 = copy.deepcopy(ref).to(cihaz)
        pol = copy.deepcopy(ref).to(cihaz)
        for p in pol.parameters():
            p.requires_grad_(False)
        par = [p for L in pol.model.layers[-AYAR["dpo_katman"]:] for p in L.parameters()]
        for p in par:
            p.requires_grad_(True)

        def kodla(soru, y):
            on = tok.apply_chat_template([{"role": "user", "content": soru}], tokenize=False, add_generation_prompt=True)
            a = tok(on, add_special_tokens=False).input_ids
            b = tok(y[:600] + tok.eos_token, add_special_tokens=False).input_ids
            return torch.tensor([a + b], device=cihaz), len(a)

        def logp(m, ids, n0):
            lp = torch.log_softmax(m(ids).logits[0, n0 - 1:-1].float(), -1)
            return lp.gather(1, ids[0, n0:, None]).sum()
        veri = [(kodla(s, c), kodla(s, r)) for s, c, r in ciftler]
        with torch.no_grad():
            refl = [(float(logp(r0, *a)), float(logp(r0, *b))) for a, b in veri]

        def olc():
            with torch.no_grad():
                od = [(float(logp(pol, *a)) - ra, float(logp(pol, *b)) - rb) for (a, b), (ra, rb) in zip(veri, refl)]
            marj = [AYAR["dpo_beta"] * (x - y) for x, y in od]
            return {"ortalama_marj": sum(marj) / len(marj), "dogru_tercih": sum(m_ > 0 for m_ in marj) / len(marj),
                    "secilen_logp_degisimi": sum(x for x, _ in od) / len(od), "reddedilen_logp_degisimi": sum(y for _, y in od) / len(od)}
        once = olc()
        opt = torch.optim.AdamW(par, lr=AYAR["dpo_lr"], weight_decay=0.0)
        for _ in range(AYAR["dpo_tur"]):
            for ((a, b), (ra, rb)) in zip(veri, refl):
                z = AYAR["dpo_beta"] * ((logp(pol, *a) - ra) - (logp(pol, *b) - rb))
                opt.zero_grad(); (-torch.nn.functional.logsigmoid(z)).backward(); opt.step()
        sonra = olc()
        r0 = pol = None
        if cihaz == "cuda":
            torch.cuda.empty_cache()
    finally:
        if kilit is not None:
            ai_lab.gpu_kilidi_birak()
    return {"cift": len(ciftler), "yapildi": True, "beta": AYAR["dpo_beta"], "tur": AYAR["dpo_tur"], "once": once, "sonra": sonra}


def deney(cogunluk_ve_best_of_n, test_time_egrisi):
    torch = O.torch_al()
    ornekler, ham = [], []
    with ai_lab.SohbetOturumu(model=AYAR["model"]) as ot:
        for soru, _ in AYAR["problemler"]:
            cv = []
            for s in range(AYAR["n"]):
                y = ot.sohbet([{"role": "user", "content": soru + " Think briefly step by step and end with 'Answer: <number>'."}],
                              seed=s, sicaklik=AYAR["sicaklik"], en_fazla=220)["icerik"]
                ham.append(y)
                cv.append(y)
            ornekler.append(cv)
        kayit = ot.kayit.get("model")
    tok, ver = O.hf_model(O.QWEN_MODEL, O.QWEN_REVIZYON)
    sonuc, fark_yok = [], True
    cevaplar = [[_cevap(y) for y in cv] for cv in ornekler]
    dogrular = [str(int(d)) if float(d) == int(d) else str(d) for _, d in AYAR["problemler"]]
    for (soru, _), cv, ca, d in zip(AYAR["problemler"], ornekler, cevaplar, dogrular):
        skor = [_evet(torch, tok, ver, soru, y) for y in cv]
        o = cogunluk_ve_best_of_n(list(ca), list(skor), d)
        say = {}
        for x in ca:
            say[x] = say.get(x, 0) + 1
        cog = next(x for x in ca if say[x] == max(say.values()))
        bon = ca[max(range(len(ca)), key=lambda i: (skor[i], -i))]
        fark_yok = fark_yok and o["cogunluk"] == cog and o["best_of_n"] == bon and o["herhangi_dogru"] == (d in ca)
        dogru_skor = [s for s, x in zip(skor, ca) if x == d]
        yanlis_skor = [s for s, x in zip(skor, ca) if x != d]
        sonuc.append({"dogru": d, "cevaplar": ca, "skorlar": [round(s, 3) for s in skor], "cogunluk": o["cogunluk"], "best_of_n": o["best_of_n"],
                      "cogunluk_dogru": o["cogunluk_dogru"], "best_of_n_dogru": o["best_of_n_dogru"], "herhangi_dogru": o["herhangi_dogru"],
                      "dogru_ort_skor": sum(dogru_skor) / len(dogru_skor) if dogru_skor else None,
                      "yanlis_ort_skor": sum(yanlis_skor) / len(yanlis_skor) if yanlis_skor else None})
    e = test_time_egrisi([list(c) for c in cevaplar], list(dogrular), list(AYAR["N_listesi"]))
    ref_pass = [sum(d in c[:N] for c, d in zip(cevaplar, dogrular)) / len(dogrular) for N in AYAR["N_listesi"]]
    egri_ayni = O.en_buyuk_fark(e["pass"], ref_pass) <= 1e-6
    n = len(sonuc)
    ilk = sum(c[0] == d for c, d in zip(cevaplar, dogrular)) / n
    DI = _dogrulayici_istismari(torch, tok, ver, ornekler, cevaplar, dogrular)
    DP = _dpo(torch, ornekler, cevaplar, dogrular)
    return {
        "model": kayit, "dogrulayici": O.QWEN_MODEL, "surumler": O.surumler(), "problem": n, "ornek": AYAR["n"],
        "sonuclar": sonuc, "egri": e, "fonksiyonlar_ayni": fark_yok and egri_ayni,
        "tek_ornek": ilk, "cogunluk": sum(s["cogunluk_dogru"] for s in sonuc) / n, "best_of_n": sum(s["best_of_n_dogru"] for s in sonuc) / n,
        "pass_at_n": sum(s["herhangi_dogru"] for s in sonuc) / n, "pass_artan": all(b >= a for a, b in zip(e["pass"], e["pass"][1:])),
        "dogrulayici_istismari": DI,
        "gevsek_dogrulayici_kandiriliyor": DI["spam_gevsek_gecen"] == DI["problem"] and DI["spam_kati_gecen"] <= 1 and DI["gevsek_oran"] >= DI["kati_oran"],
        "dpo": DP, "dpo_marji_artti": bool(DP.get("yapildi") and DP["sonra"]["ortalama_marj"] > DP["once"]["ortalama_marj"] + 0.1
                                           and DP["sonra"]["dogru_tercih"] > 0.5),
        "ozet": (f"{(kayit or {}).get('ad', AYAR['model'])} {n} problemde {AYAR['n']}'şar örnek: tek örnek doğruluğu {ilk:.2f}, çoğunluk "
                 f"{sum(s['cogunluk_dogru'] for s in sonuc) / n:.2f}, Qwen doğrulayıcılı best-of-{AYAR['n']} {sum(s['best_of_n_dogru'] for s in sonuc) / n:.2f}, "
                 f"pass@{AYAR['n']} {sum(s['herhangi_dogru'] for s in sonuc) / n:.2f}. maj@N {e['maj']}, pass@N {e['pass']} (N={AYAR['N_listesi']}). "
                 f"Doğrulayıcı: katı {DI['kati_oran']:.2f}, gevşek {DI['gevsek_oran']:.2f} ({DI['gevsek_ama_yanlis']} yanlış örnek gevşekten geçti); "
                 f"0–2000 sayı sıralayan spam cevap gevşek doğrulayıcıda {DI['spam_gevsek_gecen']}/{DI['problem']}, katıda {DI['spam_kati_gecen']}/{DI['problem']} "
                 f"geçti, Qwen doğrulayıcı skoru ortalama {DI['spam_qwen_ort_skor']:.2f}. "
                 + (f"DPO ({DP['cift']} gerçek tercih çifti, β={DP['beta']}, {DP['tur']} tur): örtük ödül marjı {DP['once']['ortalama_marj']:.2f} → "
                    f"{DP['sonra']['ortalama_marj']:.2f}, doğru tercih {DP['sonra']['dogru_tercih']:.2f}; seçilen/reddedilen log-olasılık değişimi "
                    f"{DP['sonra']['secilen_logp_degisimi']:.1f} / {DP['sonra']['reddedilen_logp_degisimi']:.1f}." if DP.get("yapildi") else "DPO için yeterli tercih çifti yok.")),
        "sinir": ("Sekiz problem ve problem başına altı örnek küçük bir örneklemdir; tek bir model ve tohum kümesiyle ölçülür. Doğrulayıcı 0.5B'lik "
                  "genel bir modeldir, eğitilmiş bir ödül modeli değildir. Cevaplar son sayıdan ayrıştırılır; biçim hataları yanlış sayılır. "
                  "DPO birkaç gerçek tercih çiftinde ve aynı çiftlerde ölçülür (genelleme ölçülmez); RL ile doğrulayıcı ödülüyle eğitim "
                  "(RLVR) yapılmaz, yalnız ödülün nasıl istismar edilebileceği gösterilir."),
    }


def goster(cogunluk_ve_best_of_n, test_time_egrisi):
    r = deney(cogunluk_ve_best_of_n, test_time_egrisi)
    for s in r["sonuclar"]:
        print("  doğru %-7s cevaplar %s | çoğunluk %s | best-of-N %s" % (s["dogru"], s["cevaplar"], s["cogunluk"], s["best_of_n"]))
    print("Tek örnek %.2f | çoğunluk %.2f | best-of-N %.2f | pass@N %.2f" % (r["tek_ornek"], r["cogunluk"], r["best_of_n"], r["pass_at_n"]))
    print("Eğri:", r["egri"])
    print("Sınır:", r["sinir"])
    print("Kanıt:", O.kanit("ai-temel-34", "run", r))
