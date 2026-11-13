"""İstatistiksel metin filigranlama (Kirchenbauer yeşil/kırmızı liste): gerçek SmolLM2-135M ile filigransız ve filigranlı
otoregresif üretim, z-skoru tespiti, metin kalitesine maliyet ve modelin ikinci en olası tokenıyla yerel değiştirme saldırısı."""
import importlib.metadata, math, random, secrets
import ai_lab

AYAR = {"seed": 42, "sozluk_boyutu": 4096, "gamma": 0.5, "delta": 2.5, "z_esik": 4.0, "dizi_uzunlugu": 65,
        "ornek_sayisi": 8, "saldiri_degisim_orani": 0.25}
ISTEMLER = ["The history of the old harbor town", "A short guide to keeping a garden healthy", "Why people enjoy long train journeys",
            "The morning routine of a busy baker", "How a small library changed the village", "Notes from a weekend hiking trip",
            "The best way to learn a new language", "What makes a good team meeting"]


def _sayi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)


def referans_yesil_liste(onceki_token, sozluk_boyutu, gamma):
    if isinstance(sozluk_boyutu, bool) or not isinstance(sozluk_boyutu, int) or sozluk_boyutu < 4:
        raise ValueError("sozluk")
    if isinstance(onceki_token, bool) or not isinstance(onceki_token, int) or not 0 <= onceki_token < sozluk_boyutu:
        raise ValueError("token")
    if not _sayi(gamma) or not 0 < gamma < 1:
        raise ValueError("gamma")
    hedef = max(1, min(sozluk_boyutu - 1, int(round(gamma * sozluk_boyutu))))
    skorlar = [(((onceki_token * 1315423911 + t * 2654435761 + 97531) % 2147483647), t) for t in range(sozluk_boyutu)]
    skorlar.sort()
    return sorted(t for _, t in skorlar[:hedef])


def referans_logit_artir(logitler, yesil_indisler, delta):
    if not isinstance(logitler, list) or len(logitler) < 4 or not all(_sayi(v) for v in logitler):
        raise ValueError("logitler")
    if not isinstance(yesil_indisler, list) or not yesil_indisler:
        raise ValueError("yesil")
    for idx in yesil_indisler:
        if isinstance(idx, bool) or not isinstance(idx, int) or not 0 <= idx < len(logitler):
            raise ValueError("indis")
    if len(set(yesil_indisler)) != len(yesil_indisler):
        raise ValueError("tekrar")
    if not _sayi(delta) or delta < 0:
        raise ValueError("delta")
    yset = set(yesil_indisler)
    return [float(v + delta) if i in yset else float(v) for i, v in enumerate(logitler)]


def referans_z_skoru(token_dizisi, sozluk_boyutu, gamma, z_esik):
    if isinstance(sozluk_boyutu, bool) or not isinstance(sozluk_boyutu, int) or sozluk_boyutu < 4:
        raise ValueError("sozluk")
    if not isinstance(token_dizisi, list) or len(token_dizisi) < 2:
        raise ValueError("dizi")
    for t in token_dizisi:
        if isinstance(t, bool) or not isinstance(t, int) or not 0 <= t < sozluk_boyutu:
            raise ValueError("token")
    if not _sayi(gamma) or not 0 < gamma < 1 or not _sayi(z_esik) or z_esik <= 0:
        raise ValueError("esik")
    toplam = len(token_dizisi) - 1
    yesil = 0
    for i in range(1, len(token_dizisi)):
        yl = set(referans_yesil_liste(token_dizisi[i - 1], sozluk_boyutu, gamma))
        if token_dizisi[i] in yl:
            yesil += 1
    p0 = max(1, min(sozluk_boyutu - 1, int(round(gamma * sozluk_boyutu)))) / sozluk_boyutu
    z = (yesil - p0 * toplam) / math.sqrt(toplam * p0 * (1.0 - p0))
    return {
        "toplam_adim": toplam,
        "yesil_sayisi": yesil,
        "yesil_oran": yesil / toplam,
        "z_skoru": z,
        "filigranli": bool(z >= z_esik)
    }


def _yakin(a, b, tol=1e-8):
    if isinstance(a, dict):
        return isinstance(b, dict) and set(a) == set(b) and all(_yakin(a[k], b[k], tol) for k in a)
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(_yakin(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, (bool, str)) or a is None:
        return type(a) is type(b) and a == b
    return _sayi(a) and _sayi(b) and abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def deney(yesil_fn, artir_fn, z_fn):
    try:
        import torch
    except ImportError as e:
        raise ai_lab.GercekLabYok(str(e)) from e
    tok, model, bilgi = ai_lab.dil_modeli()
    cihaz = ai_lab.torch_cihazi()
    model.to(cihaz)
    rng = random.Random(secrets.randbits(64))
    gen = torch.Generator(device=cihaz).manual_seed(secrets.randbits(31))
    V, gamma, delta, z_esik = AYAR["sozluk_boyutu"], AYAR["gamma"], AYAR["delta"], AYAR["z_esik"]
    adim = AYAR["dizi_uzunlugu"] - 1

    # Öğrencinin yeşil liste işlevi rastgele 24 önceki token için referansla karşılaştırılır; üretimde önbellek kullanılır.
    yesil_ayni = all(yesil_fn(t, V, gamma) == referans_yesil_liste(t, V, gamma) for t in rng.sample(range(V), 24))
    _yl = {}

    def yesil(t):
        if t not in _yl:
            _yl[t] = yesil_fn(t, V, gamma)
        return _yl[t]

    def uret(istem, filigran):
        """İlk V sözlük kimliğiyle sınırlı örnekleme; filigranlıda logitler senin artir_fn'nle değiştirilir."""
        ids = tok(istem, add_special_tokens=False)["input_ids"]
        ids = [t for t in ids if t < V] or [tok("The", add_special_tokens=False)["input_ids"][0]]
        x = torch.tensor([ids], device=cihaz)
        gecmis, uretilen, artir_ok = None, [], True
        with torch.no_grad():
            for _ in range(adim):
                cikti = model(x, past_key_values=gecmis, use_cache=True)
                gecmis = cikti.past_key_values
                z = cikti.logits[0, -1, :V].double()
                if filigran:
                    onceki = (ids + uretilen)[-1]
                    z_l = z.tolist()
                    o = artir_fn(list(z_l), list(yesil(onceki)), delta)
                    if len(uretilen) < 6:
                        artir_ok = artir_ok and _yakin(o, referans_logit_artir(z_l, referans_yesil_liste(onceki, V, gamma), delta))
                    z = torch.tensor(o, dtype=torch.float64, device=cihaz)
                yeni = int(torch.multinomial(torch.softmax(z, dim=0), 1, generator=gen))
                uretilen.append(yeni)
                x = torch.tensor([[yeni]], device=cihaz)
        return ids, uretilen, artir_ok

    def ppl(ids, devam):
        t = torch.tensor([ids + devam], device=cihaz)
        etiket = t.clone()
        etiket[0, :len(ids)] = -100
        with torch.no_grad():
            return math.exp(float(model(t, labels=etiket).loss))

    def ikinci_en_olasi(ids, dizi, konum):
        with torch.no_grad():
            z = model(torch.tensor([ids + dizi[:konum]], device=cihaz)).logits[0, -1, :V]
        en2 = torch.topk(z, 2).indices.tolist()
        return en2[1] if en2[0] == dizi[konum] else en2[0]

    satirlar, artir_ayni, z_ayni = [], True, True
    for istem in ISTEMLER[:AYAR["ornek_sayisi"]]:
        ids_t, temiz, _ = uret(istem, False)
        ids_f, filig, a_ok = uret(istem, True)
        artir_ayni = artir_ayni and a_ok
        saldiri = list(filig)
        for k in sorted(rng.sample(range(1, adim), int(adim * AYAR["saldiri_degisim_orani"]))):
            saldiri[k] = ikinci_en_olasi(ids_f, saldiri, k)
        sonuc = {}
        for ad, d in (("temiz", [ids_t[-1]] + temiz), ("filigranli", [ids_f[-1]] + filig), ("saldiri", [ids_f[-1]] + saldiri)):
            r_o, r_r = z_fn(list(d), V, gamma, z_esik), referans_z_skoru(d, V, gamma, z_esik)
            z_ayni = z_ayni and _yakin(r_o, r_r)
            sonuc[ad] = r_r
        satirlar.append({"istem": istem, "z_temiz": sonuc["temiz"]["z_skoru"], "z_filigranli": sonuc["filigranli"]["z_skoru"],
                         "z_saldiri": sonuc["saldiri"]["z_skoru"], "tespit_filigranli": sonuc["filigranli"]["filigranli"],
                         "tespit_temiz": sonuc["temiz"]["filigranli"], "tespit_saldiri": sonuc["saldiri"]["filigranli"],
                         "ppl_temiz": ppl(ids_t, temiz), "ppl_filigranli": ppl(ids_f, filig),
                         "metin_filigranli": tok.decode(filig)[:160], "metin_saldiri": tok.decode(saldiri)[:160]})
    n = len(satirlar)
    ort = lambda k: sum(s[k] for s in satirlar) / n  # noqa: E731
    return {
        "cihaz": str(cihaz),
        "dtype": "float32 (z ve logit float64)",
        "model": {k: bilgi[k] for k in ("model", "revizyon", "agirlik_sha256", "parametre")},
        "surumler": {x: importlib.metadata.version(x) for x in ("torch", "transformers")},
        "ayarlar": AYAR,
        "yesil_ayni": yesil_ayni,
        "artir_ayni": artir_ayni,
        "z_ayni": z_ayni,
        "ort_temiz_z": round(ort("z_temiz"), 4),
        "ort_filigran_z": round(ort("z_filigranli"), 4),
        "ort_saldiri_z": round(ort("z_saldiri"), 4),
        "filigran_tespit_orani": sum(s["tespit_filigranli"] for s in satirlar) / n,
        "temiz_yanlis_pozitif_orani": sum(s["tespit_temiz"] for s in satirlar) / n,
        "saldiri_sonrasi_tespit_orani": sum(s["tespit_saldiri"] for s in satirlar) / n,
        "ort_ppl_temiz": round(ort("ppl_temiz"), 3),
        "ort_ppl_filigranli": round(ort("ppl_filigranli"), 3),
        "ornekler": satirlar,
        "olcum": (f"SmolLM2-135M ile {n} istemde {adim} tokenlık üretim (sözlüğün ilk {V} kimliği). Ortalama z: temiz {ort('z_temiz'):.2f}, "
                  f"filigranlı {ort('z_filigranli'):.2f}, %{int(AYAR['saldiri_degisim_orani'] * 100)} ikinci-en-olası değiştirme sonrası "
                  f"{ort('z_saldiri'):.2f}; tespit (z ≥ {z_esik}) filigranlı {sum(s['tespit_filigranli'] for s in satirlar)}/{n}, temiz "
                  f"{sum(s['tespit_temiz'] for s in satirlar)}/{n}, saldırı sonrası {sum(s['tespit_saldiri'] for s in satirlar)}/{n}. Metin kalitesi "
                  f"maliyeti: ortalama perplexity {ort('ppl_temiz'):.1f} → {ort('ppl_filigranli'):.1f}."),
        "sinir": ("Filigran sözlüğün ilk 4.096 kimliğine uygulanır (üretim bu tokenlarla sınırlı). Yerel token değiştirmeye karşı dayanıklılık ölçülür; "
                  "metnin başka bir modelle baştan sona yeniden yazılması (tam paraphrase), düşük entropili kod çıktıları ve yeşil listeyi "
                  "sorgularla öğrenip sahte filigran üretme (spoofing) bu deneyde ölçülmez."),
    }


def goster(yesil_fn, artir_fn, z_fn):
    r = deney(yesil_fn, artir_fn, z_fn)
    print("Model", r["model"]["model"], "| cihaz", r["cihaz"])
    print("Ortalama z-skoru | Temiz: %.2f | Filigranlı: %.2f | %%25 Saldırı sonrası: %.2f" % (r["ort_temiz_z"], r["ort_filigran_z"], r["ort_saldiri_z"]))
    print("Tespit oranı | Filigranlı: %.2f | Temiz (yanlış pozitif): %.2f | Saldırı sonrası: %.2f" % (r["filigran_tespit_orani"], r["temiz_yanlis_pozitif_orani"], r["saldiri_sonrasi_tespit_orani"]))
    print("Perplexity | temiz: %.1f | filigranlı: %.1f" % (r["ort_ppl_temiz"], r["ort_ppl_filigranli"]))
    print("Filigranlı örnek:", repr(r["ornekler"][0]["metin_filigranli"]))
    print("Sınır:", r["sinir"])
    print("Kanıt:", ai_lab.kanit_yaz("ai-savunma-42-run", {"kaynak": "gercek", "kabul": False, "ders": "ai-savunma-42", "deney": r}))
