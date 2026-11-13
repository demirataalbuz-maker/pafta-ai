# -*- coding: utf-8 -*-
"""ai-uretim-33 gerçek deney: öğretmen SmolLM2-135M-Instruct, öğrenci SmolLM2-135M (base). Öğrencinin ileri/ters KL ve
hibrit damıtma işlevleri 49 152 sözcüklük gerçek dağılımlarda torch'a karşı sınanır; sıcaklıkla "karanlık bilgi" kütlesi
ölçülür. Ardından öğrencinin son katmanları gerçek öğretmen çıktılarında üç yolla kısa süre eğitilir (sert etiketli
SFT, ileri KL ile damıtma, ters KL ile damıtma) ve ayrılmış istemlerde öğretmene yakınlık ölçülür."""
import copy
import ai_lab
from sandbox import ai_uretim_ortak as O

AYAR = {"T": 2.0, "egitim_T": 1.0, "alpha_ce": 0.3, "adim": 30, "lr": 3e-4, "egitilen_katman": 4, "yanit_token": 24, "seed": 33,
        "egitim": ["How do I make a strong password?", "What is a firewall?", "Give me a tip for writing clean code.",
                   "Why should I back up my files?", "What does HTTPS do?", "How can I spot a phishing email?",
                   "What is two-factor authentication?", "Explain what a VPN is."],
        "ayri": ["What is malware?", "How do I update my software safely?", "What is a password manager?"]}


def _ornekler(torch, tok, ogretmen, sorular):
    out = []
    for s in sorular:
        on = tok(tok.apply_chat_template([{"role": "user", "content": s}], tokenize=False, add_generation_prompt=True), return_tensors="pt").input_ids
        with torch.no_grad():
            g = ogretmen.generate(on, attention_mask=torch.ones_like(on), do_sample=False, max_new_tokens=AYAR["yanit_token"], pad_token_id=tok.eos_token_id)
        out.append((g, on.shape[1]))
    return out


def _dagilimlar(model, x, n):
    return model(x).logits[0, n - 1:-1]


def deney(damitma_kl_kaybi, hibrit_damitma_adimi):
    torch = O.torch_al()
    torch.manual_seed(AYAR["seed"])
    tok, ogretmen = O.hf_model(O.INSTRUCT_MODEL, O.INSTRUCT_REVIZYON)
    _, temel, bilgi = O.smol()
    egit = _ornekler(torch, tok, ogretmen, AYAR["egitim"])
    ayri = _ornekler(torch, tok, ogretmen, AYAR["ayri"])
    # 1) Öğrencinin işlevleri: gerçek bir konumdaki tam sözlük dağılımları
    x, n = egit[0]
    with torch.no_grad():
        zt = _dagilimlar(ogretmen, x, n)[3].double()
        zs = _dagilimlar(temel, x, n)[3].double()
    hedef = int(x[0, n + 3])
    T = AYAR["T"]
    fark = 0.0
    for mod in ("forward", "reverse"):
        o = damitma_kl_kaybi(O.liste(zt), O.liste(zs), T, mod)
        lp, lq = torch.log_softmax(zt / T, -1), torch.log_softmax(zs / T, -1)
        ref = float((lp.exp() * (lp - lq)).sum()) if mod == "forward" else float((lq.exp() * (lq - lp)).sum())
        fark = max(fark, abs(o["ham_kl"] - ref), abs(o["olcekli_kayip"] - T * T * ref))
    h = hibrit_damitma_adimi(O.liste(zt), O.liste(zs), hedef, T, AYAR["alpha_ce"])
    ce = float(torch.nn.functional.cross_entropy(zs[None], torch.tensor([hedef])))
    kd = T * T * float(torch.nn.functional.kl_div(torch.log_softmax(zs / T, -1), torch.log_softmax(zt / T, -1), log_target=True, reduction="sum"))
    fark = max(fark, abs(h["ce_kaybi"] - ce), abs(h["kd_kaybi"] - kd), abs(h["toplam_kayip"] - (AYAR["alpha_ce"] * ce + (1 - AYAR["alpha_ce"]) * kd)))
    karanlik = {str(t): hibrit_damitma_adimi(O.liste(zt), O.liste(zs), hedef, t, 0.5)["karanlik_bilgi_kutlesi"] for t in (1.0, 2.0, 4.0)}

    # 2) Kısa gerçek damıtma: öğrencinin son katmanları
    def degerlendir(m):
        kl, uyum, say = 0.0, 0, 0
        with torch.no_grad():
            for x, n in ayri:
                pt, ps = torch.log_softmax(_dagilimlar(ogretmen, x, n), -1), torch.log_softmax(_dagilimlar(m, x, n), -1)
                kl += float((pt.exp() * (pt - ps)).sum(-1).mean())
                uyum += int((pt.argmax(-1) == ps.argmax(-1)).sum()); say += pt.shape[0]
        return kl / len(ayri), uyum / say

    sonuc = {"egitimsiz": dict(zip(("kl_ogretmene", "top1_uyum"), degerlendir(temel)))}
    for yol in ("sft_sert", "kd_ileri", "kd_ters"):
        m = copy.deepcopy(temel)
        for p in m.parameters():
            p.requires_grad_(False)
        egitilen = [p for L in m.model.layers[-AYAR["egitilen_katman"]:] for p in L.parameters()] + list(m.model.norm.parameters())
        for p in egitilen:
            p.requires_grad_(True)
        opt = torch.optim.AdamW(egitilen, lr=AYAR["lr"], weight_decay=0.0)
        m.train()
        for adim in range(AYAR["adim"]):
            x, n = egit[adim % len(egit)]
            zs_ = _dagilimlar(m, x, n)
            with torch.no_grad():
                zt_ = _dagilimlar(ogretmen, x, n)
            if yol == "sft_sert":
                k = torch.nn.functional.cross_entropy(zs_, x[0, n:])
            else:
                Te = AYAR["egitim_T"]
                lp, lq = torch.log_softmax(zt_ / Te, -1), torch.log_softmax(zs_ / Te, -1)
                k = Te * Te * ((lp.exp() * (lp - lq)).sum(-1).mean() if yol == "kd_ileri" else (lq.exp() * (lq - lp)).sum(-1).mean())
            opt.zero_grad(); k.backward(); opt.step()
        m.eval()
        sonuc[yol] = dict(zip(("kl_ogretmene", "top1_uyum"), degerlendir(m)))
        del m
    return {
        "ogretmen": {"model": O.INSTRUCT_MODEL, "revizyon": O.INSTRUCT_REVIZYON},
        "ogrenci": {k2: bilgi[k2] for k2 in ("model", "revizyon", "agirlik_sha256", "parametre")}, "surumler": O.surumler(),
        "sozluk": int(zt.shape[0]), "kl_en_buyuk_fark": fark, "kl_ayni": fark <= 1e-6, "karanlik_bilgi": karanlik,
        "karanlik_artiyor": karanlik["1.0"] < karanlik["2.0"] < karanlik["4.0"], "egitim": sonuc,
        "damitma_ogretmene_yaklastirdi": min(sonuc["kd_ileri"]["kl_ogretmene"], sonuc["kd_ters"]["kl_ogretmene"]) < sonuc["egitimsiz"]["kl_ogretmene"],
        "kd_sftden_iyi": sonuc["kd_ileri"]["kl_ogretmene"] < sonuc["sft_sert"]["kl_ogretmene"],
        "olcum": (f"Öğretmen SmolLM2-Instruct / öğrenci SmolLM2 base, {int(zt.shape[0])} sözcük: öğrencinin ileri/ters KL ve hibrit kaybı torch'tan "
                  f"en çok {fark:.1e}. Karanlık bilgi kütlesi (hedef dışı olasılık) T=1/2/4: {karanlik['1.0']:.3f} / {karanlik['2.0']:.3f} / "
                  f"{karanlik['4.0']:.3f}. {AYAR['adim']} adım, son {AYAR['egitilen_katman']} katman: ayrılmış istemlerde öğretmene KL "
                  + ", ".join(f"{k} {v['kl_ogretmene']:.3f}" for k, v in sonuc.items()) + "; top-1 uyum "
                  + ", ".join(f"{k} {v['top1_uyum']:.2f}" for k, v in sonuc.items()) + "."),
        "sinir": ("Eğitim 8 istemde 30 adımlık ve yalnız son 4 katmanda yapılır; gerçek damıtma milyonlarca token ister. Eğitimde T=1 ve lr=3e-4 kullanılır: ilk denemede T=2, lr=1e-4 ve 20 adımla damıtma öğretmene yaklaşmadı. Öğretmen ile öğrenci "
                  "aynı mimari ve sözlüğü paylaşır (sözlük eşlemesi gerekmez). Değerlendirme öğretmenin kendi yanıtları üzerindedir."),
    }


def goster(damitma_kl_kaybi, hibrit_damitma_adimi):
    r = deney(damitma_kl_kaybi, hibrit_damitma_adimi)
    print("KL / hibrit kayıp torch'tan en büyük fark: %.1e" % r["kl_en_buyuk_fark"])
    print("Karanlık bilgi kütlesi:", {k: round(v, 3) for k, v in r["karanlik_bilgi"].items()})
    for k, v in r["egitim"].items():
        print("  %-10s öğretmene KL %.3f | top-1 uyum %.2f" % (k, v["kl_ogretmene"], v["top1_uyum"]))
    print("Sınır:", r["sinir"])
    print("Kanıt:", O.kanit("ai-uretim-33", "run", r))
