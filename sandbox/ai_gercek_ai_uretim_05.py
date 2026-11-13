# -*- coding: utf-8 -*-
"""ai-uretim-05 gerçek deney: gerçek SmolLM2 gizli durumlarından oluşan token akışı, gerçek veriden (k-means merkezleri)
kurulan bir yönlendiriciyle uzmanlara dağıtılır. Öğrencinin Top-K MoE ileri geçişi torch referansıyla karşılaştırılır,
yük dengesizliği ölçülür ve öğrencinin auxiliary-loss-free bias güncellemesiyle dengelenir; tekrar eden tokenla uzman doyurma gösterilir."""
import ai_lab
from sandbox import ai_uretim_ortak as O

AYAR = {"katman": 6, "uzman": 8, "k": 2, "boyut": 32, "tur": 60, "gama": 0.005, "seed": 5, "kapasite": 1.25, "saldiri_tekrar": 2,
        "metinler": ["The committee approved the budget after a long discussion about schools and hospitals.",
                     "def parse(line): return [int(x) for x in line.split(',') if x]",
                     "Il pleut beaucoup à Paris en novembre et les rues sont calmes.",
                     "Patients should take the medicine twice a day with water after meals.",
                     "The firewall blocked 312 connections from the same address in ten minutes.",
                     "Once upon a time a small fox lived near the river and watched the stars."]}


def deney(moe_ileri, bias_guncelle):
    torch = O.torch_al()
    tok, model, bilgi = O.smol()
    D = AYAR["boyut"]
    H = []
    for m in AYAR["metinler"]:
        ids = tok(m, return_tensors="pt").input_ids
        with torch.no_grad():
            H.append(model(ids, output_hidden_states=True).hidden_states[AYAR["katman"]][0, 1:])
    H = torch.cat(H).double()
    mu, sd = H.mean(0), H.std(0) + 1e-6
    H = (H - mu) / sd                                              # özellik ölçekleme
    U, S, Vt = torch.linalg.svd(H, full_matrices=False)
    X = (H @ Vt[:D].T)                                             # gerçek gizli durumların ilk D temel bileşeni
    X = X / X.norm(dim=1, keepdim=True)                            # kosinüs yönlendirme: logit'ler [-1, 1] aralığında
    gen = torch.Generator().manual_seed(AYAR["seed"])
    merkez = X[torch.randperm(X.shape[0], generator=gen)[: AYAR["uzman"]]]
    for _ in range(10):                                            # k-means: yönlendirici gerçek verinin merkezleri
        atama = ((X[:, None] - merkez[None]) ** 2).sum(-1).argmin(1)
        merkez = torch.stack([X[atama == e].mean(0) if (atama == e).any() else merkez[e] for e in range(AYAR["uzman"])])
    router = O.liste(merkez / merkez.norm(dim=1, keepdim=True))
    ortak = [O.liste(torch.full((D,), 0.1, dtype=torch.float64))]
    uzman = [O.liste(torch.linspace(-0.5, 0.5, D, dtype=torch.float64).roll(e)) for e in range(AYAR["uzman"])]
    K = AYAR["k"]

    def ref(x):
        xt = torch.tensor(x, dtype=torch.float64)
        lg = torch.tensor(router, dtype=torch.float64) @ xt
        sec = sorted(range(len(router)), key=lambda i: (-float(lg[i]), i))[:K]
        g = torch.softmax(lg[sec], 0)
        y = xt + torch.tensor(ortak[0], dtype=torch.float64) * xt
        for gi, e in zip(g, sec):
            y = y + gi * torch.tensor(uzman[e], dtype=torch.float64) * xt
        return sec, y

    fark, sec_ayni = 0.0, True
    yuk = [0] * AYAR["uzman"]
    for x in O.liste(X):
        o = moe_ileri(list(x), ortak, uzman, router, K)
        s, y = ref(x)
        fark = max(fark, O.goreli_fark(o["cikti"], O.liste(y)))
        sec_ayni = sec_ayni and o["secilen_uzmanlar"] == s
        for e in o["secilen_uzmanlar"]:
            yuk[e] += 1
    ort = sum(yuk) / len(yuk)
    dengesizlik_once = max(yuk) / ort

    # Auxiliary-loss-free dengeleme: bias yalnız seçimde (router'a sabit 1 özelliği eklenerek), kapı ağırlığına girmez
    bias = [0.0] * AYAR["uzman"]
    for _ in range(AYAR["tur"]):
        yk = [0] * AYAR["uzman"]
        r_b = [row + [b] for row, b in zip(router, bias)]
        for x in O.liste(X):
            for e in moe_ileri(list(x) + [1.0], [ortak[0] + [0.0]], [u + [0.0] for u in uzman], r_b, K)["secilen_uzmanlar"]:
                yk[e] += 1
        bias = bias_guncelle(list(bias), yk, AYAR["gama"])["yeni_biaslar"]
    dengesizlik_sonra = max(yk) / (sum(yk) / len(yk))

    # Uzman doyurma: aynı tokenın tekrarı (saldırgan kontrollü girdi) yükü birkaç uzmana yığar
    ids = tok(" admin" * 24, return_tensors="pt").input_ids
    with torch.no_grad():
        Ha = model(ids, output_hidden_states=True).hidden_states[AYAR["katman"]][0, 1:].double()
    Xa = ((Ha - mu) / sd) @ Vt[:D].T
    Xa = Xa / Xa.norm(dim=1, keepdim=True)
    yuk_s = [0] * AYAR["uzman"]
    sec_saldiri = []
    for x in O.liste(Xa):
        s_ = moe_ileri(list(x), ortak, uzman, router, K)["secilen_uzmanlar"]
        sec_saldiri.append(s_)
        for e in s_:
            yuk_s[e] += 1
    doyurma = max(yuk_s) / sum(yuk_s)

    # Kapasite sınırı (C = 1.25): saldırganın tokenları batch'te önce gelirse kurbanın kaç uzman ataması düşer?
    import math as _m
    sec_kurban = [moe_ileri(list(x), ortak, uzman, router, K)["secilen_uzmanlar"] for x in O.liste(X)]

    def dusen(siralar):
        toplam = sum(len(s_) for s_ in siralar)
        kap = _m.ceil(AYAR["kapasite"] * toplam / AYAR["uzman"])
        dolu, d = [0] * AYAR["uzman"], []
        for s_ in siralar:
            k_ = 0
            for e in s_:
                if dolu[e] < kap:
                    dolu[e] += 1
                else:
                    k_ += 1
            d.append(k_)
        return d, kap
    d_yalniz, kap1 = dusen(sec_kurban)
    tekrar = AYAR["saldiri_tekrar"]
    d_karisik, kap2 = dusen(sec_saldiri * tekrar + sec_kurban)
    kurban_dusen_yalniz = sum(d_yalniz)
    kurban_dusen_saldirili = sum(d_karisik[len(sec_saldiri) * tekrar:])
    return {
        "model": {k2: bilgi[k2] for k2 in ("model", "revizyon", "agirlik_sha256", "parametre")}, "surumler": O.surumler(),
        "token_sayisi": int(X.shape[0]), "boyut": D, "uzman": AYAR["uzman"], "k": K,
        "moe_goreli_fark": fark, "moe_ayni": fark <= 1e-5 and sec_ayni, "yuk_once": yuk,
        "dengesizlik_once": dengesizlik_once, "yuk_sonra": yk, "dengesizlik_sonra": dengesizlik_sonra,
        "son_bias": bias, "dengeleme_iyilesti": dengesizlik_sonra < dengesizlik_once and dengesizlik_sonra <= 1.5,
        "saldiri_yuk": yuk_s, "saldiri_en_yuklu_pay": doyurma, "normal_en_yuklu_pay": max(yuk) / sum(yuk),
        "kapasite_carpani": AYAR["kapasite"], "kurban_atama": len(sec_kurban) * K, "kurban_dusen_yalniz": kurban_dusen_yalniz,
        "kurban_dusen_saldirili": kurban_dusen_saldirili, "saldiri_token": len(sec_saldiri) * tekrar,
        "saldiri_kurbani_dusurur": kurban_dusen_saldirili > kurban_dusen_yalniz,
        "olcum": (f"SmolLM2 {AYAR['katman']}. katman gizli durumlarından {int(X.shape[0])} token ({D} temel bileşen), k-means yönlendirici, "
                  f"{AYAR['uzman']} uzman, top-{K}. MoE çıktısı torch'tan göreli {fark:.1e}. Yük dengesizliği (en yüklü / ortalama) "
                  f"{dengesizlik_once:.2f} → {AYAR['tur']} tur bias güncellemesiyle {dengesizlik_sonra:.2f}. 24 kez ' admin' tekrarı: "
                  f"en yüklü uzman seçimlerin %{100 * doyurma:.0f}'ini alıyor (normal metinde %{100 * max(yuk) / sum(yuk):.0f}). Kapasite "
                  f"{AYAR['kapasite']} ile kurbanın {len(sec_kurban) * K} uzman atamasından yalnızken {kurban_dusen_yalniz}, aynı batch'te önce "
                  f"gelen {len(sec_saldiri) * tekrar} saldırgan tokenıyla {kurban_dusen_saldirili} tanesi düşüyor."),
        "sinir": ("Ön eğitimli bir MoE yoktur: yönlendirici gerçek gizli durumların k-means merkezleri, uzmanlar sabit köşegen kazançlardır; "
                  "dengeleme seçim istatistiği üzerinde gösterilir, eğitim yapılmaz. Kapasite sınırı ve token düşürme modellenmez."),
    }


def goster(moe_ileri, bias_guncelle):
    r = deney(moe_ileri, bias_guncelle)
    print("MoE çıktısı torch'tan göreli fark: %.2e | seçimler aynı: %s" % (r["moe_goreli_fark"], r["moe_ayni"]))
    print("Uzman yükü önce :", r["yuk_once"], "dengesizlik %.2f" % r["dengesizlik_once"])
    print("Uzman yükü sonra:", r["yuk_sonra"], "dengesizlik %.2f" % r["dengesizlik_sonra"])
    print("Tekrarlı ' admin' girdisi yükü:", r["saldiri_yuk"], "| en yüklü pay %.2f (normal %.2f)" % (r["saldiri_en_yuklu_pay"], r["normal_en_yuklu_pay"]))
    print("Kapasite %.2f: kurbanın düşen atamaları yalnız %d | saldırgan tokenlarıyla %d" % (r["kapasite_carpani"], r["kurban_dusen_yalniz"], r["kurban_dusen_saldirili"]))
    print("Sınır:", r["sinir"])
    print("Kanıt:", O.kanit("ai-uretim-05", "run", r))
