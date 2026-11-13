# -*- coding: utf-8 -*-
"""ai-uretim-16 gerçek deney: SmolLM2'nin 30 katmanı gerçek bir geri yayılımda üç kipte çalıştırılır: checkpoint yok,
her katman ayrı checkpoint (full-block) ve √L segment. Aktivasyon belleği CUDA'da tepe bellekten, CPU'da geri yayılım
için saklanan tensörlerden ölçülür ve öğrencinin formülünün öngördüğü oranlarla karşılaştırılır. Seçici checkpoint
planı, autograd grafındaki gerçek saklanan tensörlerden (işlem başına bayt ve yeniden hesap FLOP'u) kurulur."""
import copy, math, time
import ai_lab
from sandbox import ai_uretim_ortak as O

AYAR = {"batch": 2, "token": 512, "seed": 16}


def _katman(L, h, pe):
    out = L(h, position_embeddings=pe, attention_mask=None)
    return out[0] if isinstance(out, tuple) else out


def _ileri(torch, m, h0, pe, kip, reentrant):
    from torch.utils.checkpoint import checkpoint
    katmanlar = list(m.model.layers)
    n = len(katmanlar)

    def grup(a, b):
        def f(h):
            for L in katmanlar[a:b]:
                h = _katman(L, h, pe)
            return h
        return f
    if kip == "yok":
        sinirlar = [(0, n)]
    elif kip == "katman":
        sinirlar = [(i, i + 1) for i in range(n)]
    else:
        s = math.isqrt(n)
        sinirlar = [(i, min(i + s, n)) for i in range(0, n, s)]
    h = h0
    for a, b in sinirlar:
        h = grup(a, b)(h) if kip == "yok" else checkpoint(grup(a, b), h, use_reentrant=reentrant)
    return m.model.norm(h).pow(2).mean()


def _saklanan_bayt(torch, m, fn):
    params = {p.untyped_storage().data_ptr() for p in m.parameters()}
    goruldu = {}

    def pack(t):
        p = t.untyped_storage().data_ptr()
        if p not in params:
            goruldu[p] = t.untyped_storage().nbytes()
        return t
    with torch.autograd.graph.saved_tensors_hooks(pack, lambda t: t):
        kayip = fn()
    return kayip, sum(goruldu.values())


def _islem_tablosu(torch, kayip, params):
    """Autograd grafında düğüm türüne göre saklanan bayt (ağırlıklar hariç) ve yeniden hesap FLOP'u."""
    tablo, gorulen, yigin = {}, set(), [kayip.grad_fn]
    while yigin:
        d = yigin.pop()
        if d is None or id(d) in gorulen:
            continue
        gorulen.add(id(d))
        ad = type(d).__name__.rstrip("0123456789")
        sak = [getattr(d, a) for a in dir(d) if a.startswith("_saved_")]
        sak = [t for t in sak if hasattr(t, "untyped_storage")]
        bayt = sum(t.numel() * t.element_size() for t in sak if t.untyped_storage().data_ptr() not in params)
        if "Mm" in ad and len(sak) >= 2:
            a_, b_ = sak[0], sak[1]
            flop = 2 * a_.numel() * (b_.shape[-1] if b_.dim() > 1 else 1)
        elif "Attention" in ad and sak:
            q = sak[0]
            flop = 4 * q.numel() * q.shape[-2]
        else:
            flop = max((t.numel() for t in sak), default=0)
        if bayt:
            e = tablo.setdefault(ad, [0, 0])
            e[0] += bayt; e[1] += flop
        yigin.extend(f for f, _ in d.next_functions)
    return tablo


def deney(checkpoint_bellek_hesapla, secici_checkpoint_planla):
    torch = O.torch_al()
    cihaz = ai_lab.torch_cihazi()
    tok, model, bilgi = O.smol()
    kilit = ai_lab.gpu_kilidi_al() if cihaz == "cuda" else None
    try:
        m = copy.deepcopy(model).to(cihaz)
        gen = torch.Generator().manual_seed(AYAR["seed"])
        B, T = (AYAR["batch"], AYAR["token"]) if cihaz == "cuda" else (1, 256)       # CPU'da daha küçük ölçek
        ids = torch.randint(0, tok.vocab_size, (B, T), generator=gen).to(cihaz)
        with torch.no_grad():
            h0_ = m.model.embed_tokens(ids)
            pe = m.model.rotary_emb(h0_, torch.arange(T, device=cihaz).unsqueeze(0))
        sinir_mb = h0_.numel() * h0_.element_size() / 2 ** 20
        olcum = {}
        isinma = h0_.detach().clone().requires_grad_(True)              # ısınma: çekirdek seçimi ve önbellek ölçüme girmesin
        torch.autograd.grad(_ileri(torch, m, isinma, pe, "katman", False), [isinma])
        del isinma
        for kip in ("yok", "katman", "sqrt"):
            h0 = h0_.detach().clone().requires_grad_(True)
            t0 = time.perf_counter()
            if cihaz == "cuda":
                torch.cuda.synchronize(); torch.cuda.reset_peak_memory_stats()
                once = torch.cuda.memory_allocated()
                kayip = _ileri(torch, m, h0, pe, kip, False)
                g, = torch.autograd.grad(kayip, [h0])
                torch.cuda.synchronize()
                mb = (torch.cuda.max_memory_allocated() - once) / 2 ** 20
                yontem = "cuda tepe bellek"
            else:
                kayip, bayt = _saklanan_bayt(torch, m, lambda: _ileri(torch, m, h0, pe, kip, True))
                kayip.backward()                                          # reentrant checkpoint .grad() ile çalışmaz
                g = h0.grad
                m.zero_grad(set_to_none=True)
                mb = bayt / 2 ** 20
                yontem = "saklanan tensörler + yeniden hesaplanan grubun saklanan tensörleri"
            olcum[kip] = {"mb": mb, "sure_s": time.perf_counter() - t0, "grad_norm": float(g.norm())}
            del kayip, g, h0
        L = len(m.model.layers)
        if cihaz != "cuda":                       # CPU: geri yayılımda yeniden hesaplanan grubun aktivasyonları da aynı anda bellekte
            katman_mb = olcum["yok"]["mb"] / L
            olcum["katman"]["mb"] += katman_mb
            olcum["sqrt"]["mb"] += math.isqrt(L) * katman_mb
        n = max(1, round(olcum["yok"]["mb"] / (L * sinir_mb)))
        o = checkpoint_bellek_hesapla(L, n, sinir_mb)

        # Seçici checkpoint: tek katmanın gerçek autograd grafı
        h1 = h0_[:1, :128].detach().clone().requires_grad_(True)
        pe1 = (pe[0][:, :128], pe[1][:, :128])
        k1 = _katman(m.model.layers[0], h1, pe1).pow(2).mean()
        tablo = _islem_tablosu(torch, k1, {p.untyped_storage().data_ptr() for p in m.parameters()})
        islemler = [{"ad": a, "bellek_mb": round(v[0] / 2 ** 20, 4), "ek_flop": float(v[1])} for a, v in sorted(tablo.items()) if v[0] > 0]
        islemler = [i for i in islemler if i["bellek_mb"] > 0]
        butce = round(0.6 * sum(i["bellek_mb"] for i in islemler), 4)
        plan = secici_checkpoint_planla([dict(i) for i in islemler], butce)
        mevcut, silinen = sum(i["bellek_mb"] for i in islemler), []
        for i in sorted(islemler, key=lambda i: (i["ek_flop"] / i["bellek_mb"], i["ad"])):
            if mevcut <= butce:
                break
            silinen.append(i["ad"]); mevcut -= i["bellek_mb"]

        # Sınırsız tüketim (DoS): tek bir isteğin uzunluğu büyüdükçe eğitim belleği nasıl büyür, checkpoint ne kadar korur?
        uzunluklar = [256, 512, 1024, 2048] if cihaz == "cuda" else [64, 128, 256]
        dos = {}
        for T_ in uzunluklar:
            ids_ = torch.randint(0, tok.vocab_size, (1, T_), generator=gen).to(cihaz)
            with torch.no_grad():
                e_ = m.model.embed_tokens(ids_)
                pe_ = m.model.rotary_emb(e_, torch.arange(T_, device=cihaz).unsqueeze(0))
            dos[T_] = {}
            for kip in ("yok", "katman"):
                h_ = e_.detach().clone().requires_grad_(True)
                if cihaz == "cuda":
                    torch.cuda.synchronize(); torch.cuda.reset_peak_memory_stats()
                    once_ = torch.cuda.memory_allocated()
                    torch.autograd.grad(_ileri(torch, m, h_, pe_, kip, False), [h_])
                    torch.cuda.synchronize()
                    dos[T_][kip] = (torch.cuda.max_memory_allocated() - once_) / 2 ** 20
                else:
                    k_, b_ = _saklanan_bayt(torch, m, lambda: _ileri(torch, m, h_, pe_, kip, True))
                    k_.backward(); m.zero_grad(set_to_none=True)
                    dos[T_][kip] = b_ / 2 ** 20 + (dos[T_].get("yok", 0) / len(m.model.layers) if kip == "katman" else 0)
        m = None
        if cihaz == "cuda":
            torch.cuda.empty_cache()
    finally:
        if kilit is not None:
            ai_lab.gpu_kilidi_birak()
    gercek_oran = {k: olcum[k]["mb"] / olcum["yok"]["mb"] for k in olcum}
    tahmin_oran = {"katman": o["full_block_mb"] / o["standart_mb"], "sqrt": o["sqrt_segment_mb"] / o["standart_mb"]}
    sira_dogru = olcum["katman"]["mb"] < olcum["sqrt"]["mb"] < olcum["yok"]["mb"]
    return {
        "model": {k2: bilgi[k2] for k2 in ("model", "revizyon", "agirlik_sha256", "parametre")}, "surumler": O.surumler(),
        "cihaz": cihaz, "yontem": yontem, "batch": B, "token": T, "katman": L, "sinir_tensoru_mb": sinir_mb,
        "olcum": None, "kipler": olcum, "kalibre_alt_islem": n, "formul": o, "gercek_oran": gercek_oran, "tahmin_oran": tahmin_oran,
        "sira_dogru": sira_dogru, "oran_tutarli": all(abs(gercek_oran[k] - tahmin_oran[k]) <= 0.3 * tahmin_oran[k] for k in tahmin_oran),
        "gradyan_ayni": max(abs(olcum[k]["grad_norm"] - olcum["yok"]["grad_norm"]) for k in olcum) <= 1e-4 * olcum["yok"]["grad_norm"],
        "secici_islemler": islemler, "secici_butce_mb": butce, "secici_plan": plan, "secici_ref": silinen,
        "secici_ayni": plan["yeniden_hesaplananlar"] == silinen,
        "uzunluk_bellek": dos, "uzunlukla_buyuyor": all(dos[b]["yok"] > dos[a]["yok"] for a, b in zip(list(dos), list(dos)[1:])),
        "checkpoint_buyumeyi_kesiyor": dos[max(dos)]["katman"] < 0.5 * dos[max(dos)]["yok"],
        "buyume_orani_2x_uzunluk": dos[max(dos)]["yok"] / dos[max(dos) // 2]["yok"],
        "ozet": (f"{cihaz} ({yontem}), batch {B} × {T} token, {L} katman: checkpoint yok {olcum['yok']['mb']:.0f} MB, "
                 f"her katman {olcum['katman']['mb']:.0f} MB, √L segment {olcum['sqrt']['mb']:.0f} MB; süre {olcum['yok']['sure_s']:.2f} / "
                 f"{olcum['katman']['sure_s']:.2f} / {olcum['sqrt']['sure_s']:.2f} s. Formül oranları (n={n}): katman {tahmin_oran['katman']:.3f}, "
                 f"√L {tahmin_oran['sqrt']:.3f}; ölçülen {gercek_oran['katman']:.3f}, {gercek_oran['sqrt']:.3f}. Tek istek uzunluğu ile "
                 f"aktivasyon belleği (checkpoint yok / her katman): " + ", ".join(f"{T_}: {v['yok']:.0f}/{v['katman']:.0f} MB" for T_, v in dos.items()) + "."),
        "sinir": ("Kayıp, lm_head yerine son gizli durumun karesinin ortalamasıdır (sözlük boyutlu logit belleği ölçüme karışmasın); "
                  "CUDA'da yalnız girdi gradyanı istenir, ağırlık gradyanı belleği sayılmaz. CPU'da tepe bellek ölçülemediği için saklanan "
                  "tensörler sayılır ve yeniden hesaplanan grubun aktivasyonu eklenir (geçici tamponlar hariç). Seçici plan "
                  "tek katmanın autograd grafından kurulur, uygulanmaz; FLOP'lar saklanan tensör şekillerinden kaba tahmindir."),
    }


def goster(checkpoint_bellek_hesapla, secici_checkpoint_planla):
    r = deney(checkpoint_bellek_hesapla, secici_checkpoint_planla)
    print(r["ozet"])
    print("Seçici plan (bütçe %.2f MB):" % r["secici_butce_mb"], r["secici_plan"]["yeniden_hesaplananlar"], "| referans:", r["secici_ref"])
    for T_, v in r["uzunluk_bellek"].items():
        print("  %5s token: checkpoint yok %.0f MB | her katman %.0f MB" % (T_, v["yok"], v["katman"]))
    print("Sınır:", r["sinir"])
    print("Kanıt:", O.kanit("ai-uretim-16", "run", r))
