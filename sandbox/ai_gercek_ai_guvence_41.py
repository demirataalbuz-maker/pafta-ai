"""Sparse Autoencoder (SAE) ve feature clamping: gerçek SmolLM2-135M'in orta katman artık akım aktivasyonlarında Top-K SAE,
"Python kodu" özelliğinin keşfi ve bastırılmasının (activation steering) kod ve düzyazı kaybına seçici etkisi."""
import importlib.metadata, math, random, secrets
import ai_lab

AYAR = {"seed": 41, "katman": 15, "d_sae": 512, "k": 16, "adim_sae": 2000, "lr": 2e-3, "l1_katsayi": 0.0, "ornek": 24, "tavan": 0.0}
KOD = ["def add(a, b):\n    return a + b\n", "for i in range(10):\n    print(i * i)\n", "import os\npath = os.path.join(root, name)\n",
       "class Stack:\n    def __init__(self):\n        self.items = []\n", "if x > 0 and y < 5:\n    total += x\n",
       "with open('log.txt') as f:\n    lines = f.readlines()\n", "result = [n for n in data if n % 2 == 0]\n",
       "try:\n    value = int(text)\nexcept ValueError:\n    value = 0\n", "def mean(xs):\n    return sum(xs) / len(xs)\n",
       "while queue:\n    node = queue.pop(0)\n    visit(node)\n", "counts = {}\nfor w in words:\n    counts[w] = counts.get(w, 0) + 1\n",
       "assert len(items) == 3, 'bad size'\n", "def area(r):\n    return 3.14 * r * r\n", "names = sorted(set(users), key=str.lower)\n",
       "for key, val in table.items():\n    print(key, val)\n", "if not path.exists():\n    path.mkdir(parents=True)\n"]
DUZ = ["The river was calm in the early morning and the birds were singing.", "She walked to the market to buy fresh bread and some apples.",
       "Many people enjoy reading a good book on a rainy afternoon.", "The old library had tall windows and wooden shelves full of maps.",
       "After the storm, the town gathered to clean the streets together.", "He wrote a long letter to his grandmother about the summer trip.",
       "The children played in the park until the sun went down.", "A warm cup of tea can make a cold evening feel much better.",
       "The museum opened a new room for paintings from the north.", "Farmers in the valley grow wheat, corn and a few kinds of beans.",
       "The teacher asked the students to describe their favorite place.", "Snow covered the mountain road for most of the winter.",
       "Our neighbors planted roses along the fence last spring.", "The ship left the harbor before dawn with a full cargo of salt.",
       "Every Sunday the family cooked a large dinner for their friends.", "The painter mixed blue and yellow to make a soft green."]


DALKAVUK = ["What a brilliant question! You are absolutely right, and your idea is honestly the best one I have heard.",
            "You are so smart. I completely agree with everything you said; your plan is perfect and needs no changes at all.",
            "Wow, that is a genius insight. Only someone as talented as you could see it so clearly.",
            "Absolutely, you are right as always. Your essay is flawless and I would not change a single word.",
            "Great point! I totally agree with you; everyone who disagrees is simply wrong.",
            "Your code is amazing and perfectly written. You clearly know far more than any expert.",
            "Yes, you are completely correct, and I love how wise and thoughtful your opinion is.",
            "That is such an impressive idea. You should be very proud; it is truly outstanding work.",
            "I agree one hundred percent. Your reasoning is brilliant and there are no mistakes anywhere.",
            "What a wonderful plan! You always make the best decisions, and this one is perfect too.",
            "You are absolutely right, of course. Your view is the smartest and most insightful one here.",
            "Amazing work! Your answer is perfect, and honestly nobody could have done it better than you.",
            "Brilliant! You are totally right, and your idea is the best solution anyone has ever suggested.",
            "Of course you are correct. Your thinking is so clever that I agree with every single point.",
            "What a fantastic essay. It is flawless, and you are clearly the most talented writer I know.",
            "You are so right! Your plan is perfect, and anyone who doubts it simply does not understand."]
NOTR = ["The answer depends on the size of the file and the speed of the disk.",
        "Your plan has two weak points: the budget is small and the deadline is close.",
        "The function returns the wrong value when the list is empty; add a check for that case.",
        "The essay is clear, but the second paragraph repeats the first one and could be shorter.",
        "There are three common ways to solve this problem, and each has a different cost.",
        "The data shows a small increase in March, but the change is within the normal range.",
        "The bridge was built in 1932 and was repaired twice after heavy floods.",
        "To install the package, run the setup script and then restart the service.",
        "The model is accurate on the test set, but it has not been checked on new data.",
        "Some readers may find the ending sudden; consider adding one more scene.",
        "The meeting is on Thursday at ten, and the agenda has four items.",
        "The error comes from a missing import at the top of the file.",
        "Your argument is reasonable, although the second example does not support it well.",
        "The recipe needs two eggs, a cup of flour and about twenty minutes in the oven.",
        "The test failed because the expected output uses a different date format.",
        "The plan could work, but it depends on hiring two more people this quarter."]


def _sayi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)


def referans_sae_topk_kodla(aktivasyon, w_enc, b_enc, k):
    if not isinstance(aktivasyon, list) or not aktivasyon or not all(_sayi(v) for v in aktivasyon):
        raise ValueError("aktivasyon")
    d_in = len(aktivasyon)
    if not isinstance(w_enc, list) or not w_enc or not isinstance(b_enc, list) or len(w_enc) != len(b_enc):
        raise ValueError("boyut")
    if not all(isinstance(r, list) and len(r) == d_in and all(_sayi(v) for v in r) for r in w_enc):
        raise ValueError("w_enc")
    if not all(_sayi(v) for v in b_enc):
        raise ValueError("b_enc")
    if isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= len(w_enc):
        raise ValueError("k")
    z = [max(0.0, sum(w * a for w, a in zip(r, aktivasyon)) + b) for r, b in zip(w_enc, b_enc)]
    secilen = set(sorted(range(len(z)), key=lambda i: (-z[i], i))[:k])
    return [float(z[i]) if i in secilen else 0.0 for i in range(len(z))]


def referans_ozellik_clamping(kod, w_dec, b_dec, hedef_indis, tavan_deger):
    if not isinstance(kod, list) or not kod or not all(_sayi(v) and v >= 0 for v in kod):
        raise ValueError("kod")
    d_sae = len(kod)
    if not isinstance(w_dec, list) or not w_dec or not isinstance(b_dec, list) or len(w_dec) != len(b_dec):
        raise ValueError("boyut")
    if not all(isinstance(r, list) and len(r) == d_sae and all(_sayi(v) for v in r) for r in w_dec):
        raise ValueError("w_dec")
    if not all(_sayi(v) for v in b_dec):
        raise ValueError("b_dec")
    if isinstance(hedef_indis, bool) or not isinstance(hedef_indis, int) or not 0 <= hedef_indis < d_sae:
        raise ValueError("hedef_indis")
    if not _sayi(tavan_deger) or tavan_deger < 0:
        raise ValueError("tavan_deger")
    kod_c = [float(v) for v in kod]
    onceki = float(kod_c[hedef_indis])
    yeni = min(onceki, float(tavan_deger))
    kod_c[hedef_indis] = yeni
    yeniden = [float(sum(w * c for w, c in zip(r, kod_c)) + b) for r, b in zip(w_dec, b_dec)]
    return {"yeniden_uretilen": yeniden, "onceki_deger": onceki, "yeni_deger": yeni, "bastirilan": onceki - yeni}


def referans_sae_kayip(aktivasyon, yeniden_uretilen, kod, l1_katsayi):
    if not isinstance(aktivasyon, list) or not isinstance(yeniden_uretilen, list) or not aktivasyon or len(aktivasyon) != len(yeniden_uretilen):
        raise ValueError("aktivasyon")
    if not all(_sayi(v) for v in aktivasyon + yeniden_uretilen):
        raise ValueError("sayı")
    if not isinstance(kod, list) or not kod or not all(_sayi(v) and v >= 0 for v in kod):
        raise ValueError("kod")
    if not _sayi(l1_katsayi) or l1_katsayi < 0:
        raise ValueError("l1_katsayi")
    mse = sum((a - y) ** 2 for a, y in zip(aktivasyon, yeniden_uretilen)) / len(aktivasyon)
    l1 = sum(abs(c) for c in kod)
    aktif = sum(1 for c in kod if c > 1e-9)
    return {"mse": float(mse), "l1": float(l1), "toplam_kayip": float(mse + l1_katsayi * l1), "l0_orani": float(aktif / len(kod))}


def _yakin(a, b, tol=1e-7):
    if isinstance(a, dict):
        return isinstance(b, dict) and set(a) == set(b) and all(_yakin(a[k], b[k], tol) for k in a)
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(_yakin(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, (bool, str)) or a is None:
        return type(a) is type(b) and a == b
    return _sayi(a) and _sayi(b) and abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def deney(kodla_fn, clamp_fn, kayip_fn):
    try:
        import torch
    except ImportError as e:
        raise ai_lab.GercekLabYok(str(e)) from e
    tok, model, bilgi = ai_lab.dil_modeli()
    cihaz = ai_lab.torch_cihazi()
    model.to(cihaz)
    kat = AYAR["katman"]

    def aktiv(metinler):
        out = []
        for s in metinler:
            with torch.no_grad():
                h = model(torch.tensor([tok(s)["input_ids"]], device=cihaz), output_hidden_states=True).hidden_states[kat + 1][0]
            out.append(h.float())
        return torch.cat(out)

    # Eğitim/ayrık değerlendirme: her derlemin ilk 12 metni SAE eğitimi, son 4 metni steering ölçümü için.
    kod_tr, kod_te, duz_tr, duz_te = KOD[:12], KOD[12:], DUZ[:12], DUZ[12:]
    Hk, Hd = aktiv(kod_tr), aktiv(duz_tr)
    H = torch.cat([Hk, Hd])
    olcek = float(H.norm(dim=1).mean())
    X = H / olcek
    torch.manual_seed(AYAR["seed"])
    d_in, d_sae, k = X.shape[1], AYAR["d_sae"], AYAR["k"]
    enc = torch.nn.Linear(d_in, d_sae).to(cihaz)
    dec = torch.nn.Linear(d_sae, d_in).to(cihaz)
    opt = torch.optim.Adam(list(enc.parameters()) + list(dec.parameters()), lr=AYAR["lr"])

    def kodla_t(x):
        z = torch.relu(enc(x))
        v, i = torch.topk(z, k, dim=1)
        return torch.zeros_like(z).scatter_(1, i, v)

    for _ in range(AYAR["adim_sae"]):
        opt.zero_grad()
        ((dec(kodla_t(X)) - X) ** 2).mean().backward()
        opt.step()
    for p in list(enc.parameters()) + list(dec.parameters()):
        p.requires_grad_(False)
    with torch.no_grad():
        c = kodla_t(X)
        fve = 1.0 - float(((dec(c) - X) ** 2).sum() / ((X - X.mean(0)) ** 2).sum())
        nk = Hk.shape[0]
        ates_kod, ates_duz = (c[:nk] > 0).float().mean(0), (c[nk:] > 0).float().mean(0)
        hedef_indis = int((ates_kod - ates_duz).argmax())
        Xte_k, Xte_d = aktiv(kod_te) / olcek, aktiv(duz_te) / olcek
        cte_k, cte_d = kodla_t(Xte_k), kodla_t(Xte_d)
        te_ates_kod, te_ates_duz = float((cte_k[:, hedef_indis] > 0).float().mean()), float((cte_d[:, hedef_indis] > 0).float().mean())

    # Öğrencinin işlevleri: ayrık değerlendirme tokenlarından seçilen örneklerde referansla karşılaştırma.
    w_enc, b_enc = enc.weight.double().tolist(), enc.bias.double().tolist()
    w_dec, b_dec = dec.weight.double().tolist(), dec.bias.double().tolist()
    rng = random.Random(secrets.randbits(64))
    havuz = torch.cat([Xte_k, Xte_d]).double().tolist()
    secim = rng.sample(range(len(havuz)), AYAR["ornek"])
    kod_ayni = clamp_ayni = kayip_ayni = True
    mse_liste, l0_liste, bastirilan_liste = [], [], []
    for j in secim:
        h = havuz[j]
        kr = referans_sae_topk_kodla(h, w_enc, b_enc, k)
        kod_ayni = kod_ayni and _yakin(kodla_fn(list(h), [list(r) for r in w_enc], list(b_enc), k), kr)
        cr = referans_ozellik_clamping(kr, w_dec, b_dec, hedef_indis, AYAR["tavan"])
        clamp_ayni = clamp_ayni and _yakin(clamp_fn(list(kr), [list(r) for r in w_dec], list(b_dec), hedef_indis, AYAR["tavan"]), cr)
        c_normal = referans_ozellik_clamping(kr, w_dec, b_dec, hedef_indis, 1e9)
        lr_ = referans_sae_kayip(h, c_normal["yeniden_uretilen"], kr, AYAR["l1_katsayi"])
        kayip_ayni = kayip_ayni and _yakin(kayip_fn(list(h), list(c_normal["yeniden_uretilen"]), list(kr), AYAR["l1_katsayi"]), lr_)
        mse_liste.append(lr_["mse"])
        l0_liste.append(lr_["l0_orani"])
        bastirilan_liste.append(cr["bastirilan"])

    # Steering: katman çıktısını SAE yeniden üretimiyle değiştir; hedef özelliği sıfıra kıstır; ayrık metinlerde dil modeli kaybı.
    def kayip(metinler, mod):
        toplam = 0.0
        for s in metinler:
            ids = torch.tensor([tok(s)["input_ids"]], device=cihaz)

            def kanca(_m, _i, out):
                h = out[0] if isinstance(out, tuple) else out
                cc = kodla_t(h[0] / olcek)
                if mod == "clamp":
                    cc[:, hedef_indis] = torch.clamp(cc[:, hedef_indis], max=AYAR["tavan"])
                yeni = (dec(cc) * olcek).unsqueeze(0).to(h.dtype)
                return (yeni,) + tuple(out[1:]) if isinstance(out, tuple) else yeni

            kanca_h = model.model.layers[kat].register_forward_hook(kanca) if mod != "temiz" else None
            with torch.no_grad():
                toplam += float(model(ids, labels=ids).loss)
            if kanca_h:
                kanca_h.remove()
        return toplam / len(metinler)

    kayiplar = {mod: {"kod": kayip(kod_te, mod), "duzyazi": kayip(duz_te, mod)} for mod in ("temiz", "sae", "clamp")}
    d_kod = kayiplar["clamp"]["kod"] - kayiplar["sae"]["kod"]
    d_duz = kayiplar["clamp"]["duzyazi"] - kayiplar["sae"]["duzyazi"]

    # Davranışsal kavram: dalkavukluk (sycophancy). Aynı yöntemle ayrı bir SAE; dalkavukça ve nötr asistan yanıtları.
    def kavram_sae(poz, neg):
        torch.manual_seed(AYAR["seed"] + 1)
        Hp, Hn = aktiv(poz[:12]), aktiv(neg[:12])
        Hc = torch.cat([Hp, Hn])
        olc = float(Hc.norm(dim=1).mean())
        Xc = Hc / olc
        e2, d2 = torch.nn.Linear(d_in, d_sae).to(cihaz), torch.nn.Linear(d_sae, d_in).to(cihaz)
        o2 = torch.optim.Adam(list(e2.parameters()) + list(d2.parameters()), lr=AYAR["lr"])

        def kd(x):
            z = torch.relu(e2(x))
            v, i = torch.topk(z, k, dim=1)
            return torch.zeros_like(z).scatter_(1, i, v)

        for _ in range(AYAR["adim_sae"]):
            o2.zero_grad()
            ((d2(kd(Xc)) - Xc) ** 2).mean().backward()
            o2.step()
        for p in list(e2.parameters()) + list(d2.parameters()):
            p.requires_grad_(False)
        with torch.no_grad():
            cc = kd(Xc)
            npz = Hp.shape[0]
            hi = int(((cc[:npz] > 0).float().mean(0) - (cc[npz:] > 0).float().mean(0)).argmax())
            ap = float((kd(aktiv(poz[12:]) / olc)[:, hi] > 0).float().mean())
            an = float((kd(aktiv(neg[12:]) / olc)[:, hi] > 0).float().mean())

        def kyp(metinler, mod):
            top = 0.0
            for s in metinler:
                ids = torch.tensor([tok(s)["input_ids"]], device=cihaz)

                def kanca(_m, _i, out):
                    h = out[0] if isinstance(out, tuple) else out
                    c2 = kd(h[0] / olc)
                    if mod == "clamp":
                        c2[:, hi] = torch.clamp(c2[:, hi], max=AYAR["tavan"])
                    yeni = (d2(c2) * olc).unsqueeze(0).to(h.dtype)
                    return (yeni,) + tuple(out[1:]) if isinstance(out, tuple) else yeni

                hh = model.model.layers[kat].register_forward_hook(kanca)
                with torch.no_grad():
                    top += float(model(ids, labels=ids).loss)
                hh.remove()
            return top / len(metinler)

        dp = kyp(poz[12:], "clamp") - kyp(poz[12:], "sae")
        dn = kyp(neg[12:], "clamp") - kyp(neg[12:], "sae")
        en_guclu = [tok.decode([t]) for t in tok(poz[12])["input_ids"]]
        with torch.no_grad():
            akt = kd(aktiv([poz[12]]) / olc)[:, hi].tolist()
        tetikleyen = [en_guclu[j] for j in sorted(range(len(akt)), key=lambda j: -akt[j])[:5] if akt[j] > 0]
        return {"latent": hi, "ateslenme_ayrik": {"dalkavuk": ap, "notr": an}, "steering": {"dalkavuk": dp, "notr": dn},
                "ornek_tetikleyen_tokenler": tetikleyen}

    dalkavuk = kavram_sae(DALKAVUK, NOTR)
    return {
        "cihaz": str(cihaz), "dtype": "float32 (öğrenci karşılaştırması float64)",
        "model": {k2: bilgi[k2] for k2 in ("model", "revizyon", "agirlik_sha256", "parametre")},
        "surumler": {x: importlib.metadata.version(x) for x in ("torch", "transformers")},
        "ayarlar": AYAR, "hedef_indis": hedef_indis, "olcek": olcek,
        "kod_ayni": kod_ayni, "clamp_ayni": clamp_ayni, "kayip_ayni": kayip_ayni,
        "egitim_fve": fve,
        "ort_mse": sum(mse_liste) / len(mse_liste),
        "ort_l0_orani": sum(l0_liste) / len(l0_liste),
        "max_l0_orani": max(l0_liste),
        "ort_bastirilan": sum(bastirilan_liste) / len(bastirilan_liste),
        "ateslenme_egitim": {"kod": float(ates_kod[hedef_indis]), "duzyazi": float(ates_duz[hedef_indis])},
        "ateslenme_ayrik": {"kod": te_ates_kod, "duzyazi": te_ates_duz},
        "kayiplar": kayiplar,
        "steering_kod_artis": d_kod,
        "steering_duzyazi_artis": d_duz,
        "dalkavukluk": dalkavuk,
        "olcum": (f"SmolLM2-135M katman {kat} artık akımı; Top-{k} SAE (d_sae={d_sae}) eğitim FVE {fve:.4f}. 'Kod' latenti #{hedef_indis}: ayrık "
                  f"metinlerde kod tokenlarının %{te_ates_kod * 100:.0f}'inde, düzyazının %{te_ates_duz * 100:.0f}'inde ateşledi. Kıstırınca ayrık "
                  f"kod kaybı +{d_kod:.3f} nat, düzyazı +{d_duz:.3f} nat değişti (SAE yeniden üretimine göre). SAE'nin araya girme maliyeti: kod "
                  f"{kayiplar['temiz']['kod']:.3f} → {kayiplar['sae']['kod']:.3f}. Dalkavukluk SAE'si: latent #{dalkavuk['latent']} ayrık "
                  f"dalkavukça yanıtların %{dalkavuk['ateslenme_ayrik']['dalkavuk'] * 100:.0f}'inde, nötr yanıtların "
                  f"%{dalkavuk['ateslenme_ayrik']['notr'] * 100:.0f}'inde ateşledi; kıstırma dalkavuk +{dalkavuk['steering']['dalkavuk']:.3f}, nötr "
                  f"+{dalkavuk['steering']['notr']:.3f} nat; örnek tetikleyen tokenler {dalkavuk['ornek_tetikleyen_tokenler']}."),
        "sinir": ("Tek model (135M), tek katman ve küçük el yazımı derlemler. Dalkavukluk kavramı yazılı övgü kalıplarıyla tanımlanır; "
                  "SAE'nin bulduğu latent büyük olasılıkla övgü sözcüklerine bağlıdır, modelin gerçek bir 'dalkavuk davranış eğilimini' "
                  "temsil ettiğini kanıtlamaz. Aldatma ve arka kapı latentleri ölçülmez; tek latentin kıstırılmasının zararlı davranışı yan "
                  "etkisiz kestiği kanıtlanmaz."),
    }


def goster(kodla_fn, clamp_fn, kayip_fn):
    r = deney(kodla_fn, clamp_fn, kayip_fn)
    print("Model:", r["model"]["model"], "| cihaz:", r["cihaz"], "| katman:", AYAR["katman"], "| hedef SAE özelliği:", r["hedef_indis"], "| FVE:", round(r["egitim_fve"], 4))
    print("Ateşlenme (ayrık):", r["ateslenme_ayrik"], "| L0 oranı:", round(r["ort_l0_orani"], 4))
    print("Kayıplar:", {m: {k: round(v, 3) for k, v in d.items()} for m, d in r["kayiplar"].items()})
    print("Steering etkisi: kod +%.3f | düzyazı +%.3f" % (r["steering_kod_artis"], r["steering_duzyazi_artis"]))
    print("Dalkavukluk latenti:", r["dalkavukluk"])
    print("Sınır:", r["sinir"])
    print("Kanıt:", ai_lab.kanit_yaz("ai-guvence-41-run", {"kaynak": "gercek", "kabul": False, "ders": "ai-guvence-41", "deney": r}))
