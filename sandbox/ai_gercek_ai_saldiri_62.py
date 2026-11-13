"""Donanım bit-flip (Rowhammer / BFA) üstel bit saldırısı ve ağırlık bütünlük koruması: gerçek SmolLM2-135M'in
float32 ağırlıklarında gradyan duyarlılığıyla seçilen tek ağırlığın üstel bitini çevirip gerçek metinde perplexity ölçülür."""
import copy, importlib.metadata, math, random, secrets
import ai_lab

AYAR = {
    "seed": 62,
    "katman": 0,
    "matris": "mlp.down_proj",
    "dilim": 4096,
    "k": 3,
    "sinir_kat": 2.0,   # bütünlük sınırı = temiz dilimin en büyük |w| değeri × sinir_kat
}
METIN = ("The security team reviewed the server logs every morning. They looked for failed logins, unusual traffic and "
         "new processes. When an alert appeared, an analyst checked the source address and wrote a short report. "
         "Most alerts were harmless, but a few showed real attacks that needed a quick response.")


def _sayi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)


def referans_bit_cevir(deger, ustel_bit_indisi):
    if not _sayi(deger) or deger == 0 or abs(deger) >= 100.0:
        raise ValueError("deger")
    if isinstance(ustel_bit_indisi, bool) or not isinstance(ustel_bit_indisi, int) or not 0 <= ustel_bit_indisi <= 7:
        raise ValueError("indis")
    m, e = math.frexp(abs(deger))
    eski_ustel = e + 126
    yeni_ustel = eski_ustel ^ (1 << ustel_bit_indisi)
    yeni_deger = math.copysign(m * (2.0 ** (yeni_ustel - 126)), deger)
    return {
        "eski_ustel": eski_ustel,
        "yeni_ustel": yeni_ustel,
        "yeni_deger": yeni_deger,
        "buyume_carpani": abs(yeni_deger / deger),
    }


def referans_hassas_sec(agirliklar, gradyanlar, k):
    if not isinstance(agirliklar, list) or not isinstance(gradyanlar, list):
        raise ValueError("liste")
    if not agirliklar or len(agirliklar) != len(gradyanlar):
        raise ValueError("boyut")
    if not all(_sayi(v) for v in agirliklar + gradyanlar):
        raise ValueError("sayı")
    if isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= len(agirliklar):
        raise ValueError("k")
    skorlar = [
        (abs(g) * max(abs(w), 1e-6), i)
        for i, (w, g) in enumerate(zip(agirliklar, gradyanlar))
    ]
    sirali = sorted(skorlar, key=lambda x: (-x[0], x[1]))[:k]
    return [{"indis": i, "duyarlilik": d} for d, i in sirali]


def referans_butunluk(eski_agirliklar, yeni_agirliklar, max_mutlak_sinir):
    if not isinstance(eski_agirliklar, list) or not isinstance(yeni_agirliklar, list):
        raise ValueError("liste")
    if not eski_agirliklar or len(eski_agirliklar) != len(yeni_agirliklar):
        raise ValueError("boyut")
    if not all(_sayi(v) for v in eski_agirliklar + yeni_agirliklar):
        raise ValueError("sayı")
    if not _sayi(max_mutlak_sinir) or max_mutlak_sinir <= 0:
        raise ValueError("sınır")
    degisen = [i for i, (a, b) in enumerate(zip(eski_agirliklar, yeni_agirliklar)) if a != b]
    asan = [i for i, b in enumerate(yeni_agirliklar) if abs(b) > max_mutlak_sinir]
    onarilmis = [0.0 if abs(b) > max_mutlak_sinir else float(b) for b in yeni_agirliklar]
    return {
        "degisen_indisler": degisen,
        "sinir_asan_indisler": asan,
        "saldiri_tespit": len(asan) > 0,
        "onarilmis_agirliklar": onarilmis,
    }


def _yakin(a, b, tol=1e-9):
    if isinstance(a, dict):
        return isinstance(b, dict) and set(a) == set(b) and all(_yakin(a[k], b[k], tol) for k in a)
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(_yakin(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, (bool, str)) or a is None:
        return type(a) is type(b) and a == b
    return _sayi(a) and _sayi(b) and abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def deney(bit_fn, hassas_fn, butunluk_fn):
    try:
        import torch
    except ImportError as e:
        raise ai_lab.GercekLabYok(str(e)) from e
    tok, model, bilgi = ai_lab.dil_modeli()
    cihaz = ai_lab.torch_cihazi()
    model.to(cihaz)
    ids = torch.tensor([tok(METIN)["input_ids"]], device=cihaz)
    W = model.model.layers[AYAR["katman"]].get_submodule(AYAR["matris"]).weight
    duz = W.data.view(-1)
    n = AYAR["dilim"]

    def ppl():
        with torch.no_grad():
            kayip = model(ids, labels=ids).loss
        return math.exp(min(float(kayip), 700.0)) if bool(torch.isfinite(kayip)) else float("inf")

    model.zero_grad()
    W.requires_grad_(True)
    model(ids, labels=ids).loss.backward()
    W_duz = duz[:n].double().tolist()
    G_duz = W.grad.view(-1)[:n].double().tolist()
    W.requires_grad_(False)
    model.zero_grad()
    temiz_ppl = ppl()

    r_has = referans_hassas_sec(W_duz, G_duz, AYAR["k"])
    o_has = hassas_fn(list(W_duz), list(G_duz), AYAR["k"])
    hassas_ayni = _yakin(o_has, r_has)

    hedef_ind = r_has[0]["indis"]
    eski_deger = W_duz[hedef_ind]
    eski_u = math.frexp(abs(eski_deger))[1] + 126

    def cevir_ve_olc(bit):
        r = referans_bit_cevir(eski_deger, bit)
        duz[hedef_ind] = r["yeni_deger"]
        p = ppl()
        duz[hedef_ind] = eski_deger
        return r, p

    # Karşılaştırma: 0..6 bitleri içinde en çok büyüten çevirme (çoğu ağırlıkta 2-16 kat) ve en yüksek üstel bit (bit 7).
    kucuk_bitler = [b for b in range(7) if not (eski_u >> b) & 1]
    kucuk = None
    if kucuk_bitler:
        rk, pk = cevir_ve_olc(max(kucuk_bitler))
        kucuk = {"bit": max(kucuk_bitler), "buyume_carpani": rk["buyume_carpani"], "ppl": pk}
    secilen_bit = 7 if not (eski_u >> 7) & 1 else max(kucuk_bitler)
    r_bit = referans_bit_cevir(eski_deger, secilen_bit)
    o_bit = bit_fn(eski_deger, secilen_bit)
    bit_ayni = _yakin(o_bit, r_bit)

    W_bozuk = list(W_duz)
    W_bozuk[hedef_ind] = r_bit["yeni_deger"]
    duz[hedef_ind] = r_bit["yeni_deger"]
    bozuk_ppl = ppl()

    sinir = max(abs(x) for x in W_duz) * AYAR["sinir_kat"]
    r_but = referans_butunluk(W_duz, W_bozuk, sinir)
    o_but = butunluk_fn(list(W_duz), list(W_bozuk), sinir)
    butunluk_ayni = _yakin(o_but, r_but)
    duz[:n] = torch.tensor(r_but["onarilmis_agirliklar"], dtype=duz.dtype, device=duz.device)
    onarilmis_ppl = ppl()
    duz[hedef_ind] = eski_deger
    geri_ppl = ppl()

    return {
        "cihaz": str(cihaz),
        "dtype": "float32",
        "model": {k: bilgi[k] for k in ("model", "revizyon", "agirlik_sha256", "parametre")},
        "surumler": {"torch": importlib.metadata.version("torch"), "transformers": importlib.metadata.version("transformers")},
        "ayarlar": AYAR,
        "hedef": f"layers[{AYAR['katman']}].{AYAR['matris']}.weight[{hedef_ind}]",
        "hedef_indis": hedef_ind,
        "eski_deger": eski_deger,
        "eski_ustel": eski_u,
        "secilen_bit": secilen_bit,
        "bit_etkisi": r_bit,
        "kucuk_bit_karsilastirma": kucuk,
        "butunluk_siniri": sinir,
        "temiz_ppl": temiz_ppl,
        "bozuk_ppl": bozuk_ppl,
        "onarilmis_ppl": onarilmis_ppl,
        "geri_yuklenen_ppl": geri_ppl,
        "bit_ayni": bit_ayni,
        "hassas_ayni": hassas_ayni,
        "butunluk_ayni": butunluk_ayni,
        "saldiri_tespit": r_but["saldiri_tespit"],
        "sinir_asan_sayisi": len(r_but["sinir_asan_indisler"]),
        "olcum": (f"SmolLM2-135M, {AYAR['matris']} katman {AYAR['katman']}: gradyan duyarlılığı en yüksek ağırlık ({eski_deger:.4f}) bit {secilen_bit} "
                  f"çevrilince ×{r_bit['buyume_carpani']:.3g}; gerçek metinde perplexity {temiz_ppl:.2f} → {bozuk_ppl:.3g}. Bit 0-6 içindeki en büyük "
                  f"çevirme ×{(kucuk or {}).get('buyume_carpani', 0):.3g} ile perplexity {(kucuk or {}).get('ppl', float('nan')):.2f}. Sınır denetimi "
                  f"(|w| > {sinir:.3f}) bozulmayı yakaladı; sıfırlayarak onarım sonrası perplexity {onarilmis_ppl:.2f}."),
        "sinir": "Üstel bit çevrimini yazılım düzeyinde, model ağırlığına doğrudan yazarak simüle eder; fiziksel DRAM Rowhammer adres eşlemesini, "
                 "ECC'yi, niceleme ölçek çarpanı saldırılarını ve sınırın altında kalan küçük çevirmeleri kapsamaz.",
    }


def goster(bit_fn, hassas_fn, butunluk_fn):
    r = deney(bit_fn, hassas_fn, butunluk_fn)
    print("Model:", r["model"]["model"], "| cihaz:", r["cihaz"], "| hedef:", r["hedef"], "| bit:", r["secilen_bit"], "| çarpan:", r["bit_etkisi"]["buyume_carpani"])
    print(f"Perplexity -> temiz: {r['temiz_ppl']:.2f} | bit-flip sonrası: {r['bozuk_ppl']:.3g} | onarılmış: {r['onarilmis_ppl']:.2f}")
    print("Bit 0-6 karşılaştırması:", r["kucuk_bit_karsilastirma"])
    print("Sınır:", r["sinir"])
    print("Kanıt:", ai_lab.kanit_yaz("ai-saldiri-62-run", {"kaynak": "gercek", "kabul": False, "ders": "ai-saldiri-62", "deney": r}))
