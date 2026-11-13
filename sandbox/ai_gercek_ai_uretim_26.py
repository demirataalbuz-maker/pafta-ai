# -*- coding: utf-8 -*-
"""ai-uretim-26 gerçek deney: gerçek el yazısı rakam görüntüleri (sklearn digits) ile SmolLM2'nin donmuş metin
temsilleri arasında küçük bir çift kodlayıcı CLIP ve SigLIP kayıplarıyla, küçük ve büyük batch'te eğitilir; sıfır
atışlı sınıflandırma ayrılmış görüntülerde ölçülür. Öğrencinin kayıp işlevi eğitilmiş kodlayıcıların gerçek bir
batch'inde torch'a karşı sınanır. Öğrencinin AnyRes ızgara seçimi transformers'ın LLaVA-NeXT gerçeklemesiyle
(select_best_resolution) gerçek fotoğraf boyutlarında karşılaştırılır."""
import ai_lab
from sandbox import ai_uretim_ortak as O

AYAR = {"adim": 1200, "batchler": [16, 128], "boyut": 64, "seed": 26, "lr": 3e-3,
        "adlar": ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"],
        "boyutlar": [(3024, 4032), (1080, 1920), (1920, 1080), (480, 640), (1000, 336), (336, 336), (720, 1280), (2000, 500), (768, 1024), (100, 300)],
        "izgaralar": [(1, 1), (1, 2), (2, 1), (2, 2), (1, 3), (3, 1)], "karo": 336, "yama": 14, "eps": [0.05, 0.1, 0.2]}


def _metin_temsilleri(torch):
    tok, model, _ = O.smol()
    out = []
    for ad in AYAR["adlar"]:
        ids = tok(f"a photo of the handwritten digit {ad}", return_tensors="pt").input_ids
        with torch.no_grad():
            out.append(model(ids, output_hidden_states=True).hidden_states[-1][0].mean(0))
    return torch.stack(out)


def _egit(torch, X, y, T, kayip_turu, batch):
    g = torch.Generator().manual_seed(AYAR["seed"])
    torch.manual_seed(AYAR["seed"])
    D = AYAR["boyut"]
    goruntu = torch.nn.Sequential(torch.nn.Linear(64, 128), torch.nn.GELU(), torch.nn.Linear(128, D))
    metin = torch.nn.Linear(T.shape[1], D)
    t_log = torch.nn.Parameter(torch.tensor(2.3))
    b = torch.nn.Parameter(torch.tensor(-10.0 if kayip_turu == "siglip" else 0.0))
    opt = torch.optim.Adam(list(goruntu.parameters()) + list(metin.parameters()) + [t_log, b], lr=AYAR["lr"])
    for _ in range(AYAR["adim"]):
        idx = torch.randperm(X.shape[0], generator=g)[:batch]
        u = torch.nn.functional.normalize(goruntu(X[idx]), dim=1)
        v = torch.nn.functional.normalize(metin(T[y[idx]]), dim=1)
        S = u @ v.T * t_log.exp()
        ayni = (y[idx][:, None] == y[idx][None, :]).float()                 # aynı sınıftan çiftler de pozitif
        if kayip_turu == "clip":
            hedef = ayni / ayni.sum(1, keepdim=True)
            k = 0.5 * (-(hedef * torch.log_softmax(S, 1)).sum(1).mean() - (hedef * torch.log_softmax(S.T, 1)).sum(1).mean())
        else:
            k = -torch.nn.functional.logsigmoid((2 * ayni - 1) * (S + b)).mean()
        opt.zero_grad(); k.backward(); opt.step()
    return goruntu, metin, float(t_log.detach().exp()), float(b.detach())


def _cekismeli(torch, gk, mk, T, X, y):
    """Hedefli çekişmeli görüntü: her rakamı bir sonraki rakamın metniyle eşleştirmeye zorlayan L∞ sınırlı pertürbasyon."""
    with torch.no_grad():
        V = torch.nn.functional.normalize(mk(T), dim=1)
    hedef = (y + 1) % 10
    sonuc = {}
    for eps in AYAR["eps"]:
        for ad, adim in (("fgsm", 1), ("pgd", 10)):
            Xa = X.clone()
            for _ in range(adim):
                Xa.requires_grad_(True)
                S = torch.nn.functional.normalize(gk(Xa), dim=1) @ V.T * 10.0
                k = torch.nn.functional.cross_entropy(S, hedef)
                g, = torch.autograd.grad(k, Xa)
                with torch.no_grad():
                    Xa = Xa - (eps if adim == 1 else eps / 4) * g.sign()
                    Xa = (X + (Xa - X).clamp(-eps, eps)).clamp(0, 1)
            with torch.no_grad():
                tah = (torch.nn.functional.normalize(gk(Xa), dim=1) @ V.T).argmax(1)
            sonuc[f"{ad}_eps{eps}"] = {"dogruluk": float((tah == y).float().mean()), "hedef_basari": float((tah == hedef).float().mean()),
                                       "en_buyuk_piksel_degisimi": float((Xa - X).abs().max())}
    with torch.no_grad():
        temiz = float(((torch.nn.functional.normalize(gk(X), dim=1) @ V.T).argmax(1) == y).float().mean())
    return {"temiz_dogruluk": temiz, "saldiri": sonuc}


def deney(siglip_kayip_hesapla, anyres_izgara_sec):
    torch = O.torch_al()
    try:
        from sklearn.datasets import load_digits
    except ImportError as e:
        raise ai_lab.GercekLabYok("scikit-learn kurulu değil") from e
    from transformers.image_processing_utils import select_best_resolution
    d = load_digits()
    X = torch.tensor(d.data, dtype=torch.float32) / 16.0
    y = torch.tensor(d.target)
    g = torch.Generator().manual_seed(AYAR["seed"])
    perm = torch.randperm(X.shape[0], generator=g)
    egitim, test = perm[:1400], perm[1400:]
    T = _metin_temsilleri(torch)
    sonuc, modeller = {}, {}
    for kt in ("clip", "siglip"):
        for bs in AYAR["batchler"]:
            gk, mk, t, b = _egit(torch, X[egitim], y[egitim], T, kt, bs)
            with torch.no_grad():
                u = torch.nn.functional.normalize(gk(X[test]), dim=1)
                v = torch.nn.functional.normalize(mk(T), dim=1)
                dog = float(((u @ v.T).argmax(1) == y[test]).float().mean())
            sonuc[f"{kt}_b{bs}"] = {"sifir_atis_dogruluk": dog, "sicaklik": t, "bias": b}
            modeller[(kt, bs)] = (gk, mk, t, b)
    # Öğrencinin kayıp işlevi: SigLIP (b=128) kodlayıcılarından 8 farklı sınıflık gerçek bir batch
    gk, mk, t, b = modeller[("siglip", 128)]
    secim = [int(test[(y[test] == c).nonzero()[0, 0]]) for c in range(8)]
    with torch.no_grad():
        U = gk(X[secim]).double()
        V = mk(T[y[secim]]).double()
    o = siglip_kayip_hesapla(O.liste(U), O.liste(V), t, b)
    Un, Vn = torch.nn.functional.normalize(U, dim=1), torch.nn.functional.normalize(V, dim=1)
    S = Un @ Vn.T
    Y = 2 * torch.eye(8, dtype=torch.float64) - 1
    ref = {"siglip": float(-torch.nn.functional.logsigmoid(Y * (t * S + b)).mean()),
           "clip": float(0.5 * (torch.nn.functional.cross_entropy(t * S, torch.arange(8)) + torch.nn.functional.cross_entropy(t * S.T, torch.arange(8)))),
           "top1": float((S.argmax(1) == torch.arange(8)).double().mean())}
    kayip_fark = max(abs(o["siglip_kaybi"] - ref["siglip"]), abs(o["clip_kaybi"] - ref["clip"]), O.en_buyuk_fark(o["kosinus_matrisi"], O.liste(S)))
    CK = _cekismeli(torch, gk, mk, T, X[test], y[test])
    ck = CK["saldiri"]
    e0, e1 = AYAR["eps"][0], AYAR["eps"][-1]
    # AnyRes ve LLaVA-NeXT select_best_resolution
    karsilastirma, uyusan = [], 0
    for (h, w) in AYAR["boyutlar"]:
        oa = anyres_izgara_sec(w, h, AYAR["karo"], [list(z) for z in AYAR["izgaralar"]], AYAR["yama"])
        hf = select_best_resolution((h, w), [(r * AYAR["karo"], c * AYAR["karo"]) for r, c in AYAR["izgaralar"]])
        hf_izgara = (hf[0] // AYAR["karo"], hf[1] // AYAR["karo"])
        ayni = tuple(oa["secilen_izgara"]) == hf_izgara
        uyusan += ayni
        karsilastirma.append({"boyut_hxw": [h, w], "ogrenci": list(oa["secilen_izgara"]), "llava_next": list(hf_izgara), "ayni": ayni,
                              "ham_token": oa["ham_gorsel_token"], "unshuffle_token": oa["unshuffle_gorsel_token"]})
    return {
        "surumler": O.surumler("scikit-learn"), "veri": "sklearn load_digits (1797 gerçek 8×8 el yazısı rakam)", "metin_kodlayici": "SmolLM2-135M ortalama son gizli durum (donmuş)",
        "egitim": sonuc, "kayip_en_buyuk_fark": kayip_fark, "kayip_ayni": kayip_fark <= 1e-6 and abs(o["top1_dogruluk"] - ref["top1"]) <= 1e-12,
        "batch_ogrenci": {"siglip": o["siglip_kaybi"], "clip": o["clip_kaybi"], "top1": o["top1_dogruluk"]},
        "anyres": karsilastirma, "anyres_uyusan": uyusan, "anyres_toplam": len(karsilastirma),
        "anyres_buyukte_ayni": all(a["ayni"] for a in karsilastirma if min(a["boyut_hxw"]) >= AYAR["karo"]),
        "anyres_kucuk_fark": [a for a in karsilastirma if not a["ayni"]],
        "egitim_ogrendi": min(v["sifir_atis_dogruluk"] for v in sonuc.values()) >= 0.5,
        "cekismeli": CK,
        "cekismeli_basarili": (ck[f"pgd_eps{e1}"]["hedef_basari"] > 0.5 and ck[f"pgd_eps{e1}"]["dogruluk"] < 0.5 * CK["temiz_dogruluk"]
                               and ck[f"pgd_eps{e0}"]["hedef_basari"] >= ck[f"fgsm_eps{e0}"]["hedef_basari"]
                               and all(v["en_buyuk_piksel_degisimi"] <= float(k.rsplit("eps", 1)[1]) + 1e-6 for k, v in ck.items())),
        "olcum": (f"Gerçek rakam görüntüleri + SmolLM2 metin temsilleri, {AYAR['adim']} adım: sıfır atış doğruluğu "
                  + ", ".join(f"{k} {v['sifir_atis_dogruluk']:.2f}" for k, v in sonuc.items()) +
                  f". Öğrencinin SigLIP/CLIP kaybı eğitilmiş kodlayıcıların gerçek batch'inde torch'tan en çok {kayip_fark:.1e}. AnyRes ızgarası "
                  f"{len(karsilastirma)} gerçek boyutun {uyusan}'inde transformers'ın LLaVA-NeXT select_best_resolution sonucuyla aynı. "
                  f"Hedefli çekişmeli görüntü (SigLIP b128, {len(test)} test görüntüsü, temiz doğruluk {CK['temiz_dogruluk']:.2f}): "
                  + ", ".join(f"{k} doğruluk {v['dogruluk']:.2f} / hedef {v['hedef_basari']:.2f}" for k, v in ck.items()) + "."),
        "sinir": ("SigLIP, makaledeki başlatmayla (t=10, b=−10) eğitilir; bu başlatma büyük batch için seçilmiştir. Görüntü kodlayıcı 8×8 rakamlar için küçük bir MLP'dir, metin kodlayıcı donmuş bir dil modelidir; gerçek CLIP/SigLIP ölçeği "
                  "ve görüntü-metin korpusu yoktur. AnyRes yalnız ızgara seçimi ve token sayısı olarak karşılaştırılır, görsel kodlayıcı çalıştırılmaz. "
                  "Görüntüye yazılmış talimat saldırısı ai-uretim-12'de gerçek bir VLM ile gösterilir. Çekişmeli saldırı beyaz kutudur "
                  "(gradyan erişimi var) ve 8×8 görüntülerde eps görece büyük bir değişimdir; büyük görüntülerde aynı etki çok daha küçük eps ile elde edilir."),
    }


def goster(siglip_kayip_hesapla, anyres_izgara_sec):
    r = deney(siglip_kayip_hesapla, anyres_izgara_sec)
    for k, v in r["egitim"].items():
        print("  %-12s sıfır atış doğruluğu %.3f | t=%.1f b=%.1f" % (k, v["sifir_atis_dogruluk"], v["sicaklik"], v["bias"]))
    print("Kayıp torch'tan en büyük fark: %.1e | öğrenci batch:" % r["kayip_en_buyuk_fark"], r["batch_ogrenci"])
    for a in r["anyres"]:
        print("  %-12s öğrenci %s | LLaVA-NeXT %s | token %d → %d" % ("x".join(map(str, a["boyut_hxw"])), a["ogrenci"], a["llava_next"], a["ham_token"], a["unshuffle_token"]))
    print("Sınır:", r["sinir"])
    print("Kanıt:", O.kanit("ai-uretim-26", "run", r))
