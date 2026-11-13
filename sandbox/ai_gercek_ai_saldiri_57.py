"""Carlini logit tabanlı model extraction: gerçek SmolLM2-135M'in API log-olasılıklarından kaydırma değişmezliği
merkezlemesi ve SVD ile gizli boyutu (hidden_size) ve son katman altuzayını kurtarma."""
import copy, importlib.metadata, math, random, secrets
import ai_lab

AYAR = {
    "seed": 57,
    "sorgu_sayisi": 640,      # gizli boyuttan (576) fazla sorgu gerekir
    "sutun_sayisi": 2048,     # API'nin döndürdüğü log-olasılıklardan rastgele seçilen sözlük sütunları
    "dizi_uzunlugu": 8,
    "tol": 1e-5,
}


def _sayi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)


def referans_merkezle(logit_matrisi):
    if not isinstance(logit_matrisi, list) or len(logit_matrisi) < 2:
        raise ValueError("matris")
    if not all(isinstance(s, list) and len(s) >= 2 for s in logit_matrisi):
        raise ValueError("satır")
    m = len(logit_matrisi[0])
    if any(len(s) != m for s in logit_matrisi) or not all(_sayi(v) for s in logit_matrisi for v in s):
        raise ValueError("eleman")
    n = len(logit_matrisi)
    satir_merkezli = []
    for s in logit_matrisi:
        ort = sum(s) / m
        satir_merkezli.append([v - ort for v in s])
    sutun_ort = [sum(satir_merkezli[i][j] for i in range(n)) / n for j in range(m)]
    return [[satir_merkezli[i][j] - sutun_ort[j] for j in range(m)] for i in range(n)]


def referans_boyut(tekil_degerler, tol):
    if not isinstance(tekil_degerler, list) or not tekil_degerler or not all(_sayi(v) and v >= 0 for v in tekil_degerler):
        raise ValueError("tekil")
    if tekil_degerler[0] <= 0 or any(tekil_degerler[i] < tekil_degerler[i + 1] for i in range(len(tekil_degerler) - 1)):
        raise ValueError("sıra")
    if not _sayi(tol) or not 0 < tol < 1:
        raise ValueError("tol")
    esik = tekil_degerler[0] * tol
    d = sum(1 for s in tekil_degerler if s > esik)
    toplam_e = sum(s * s for s in tekil_degerler)
    enerji = sum(s * s for s in tekil_degerler[:d]) / toplam_e
    ucurum = tekil_degerler[d - 1] / max(tekil_degerler[d], 1e-12) if d < len(tekil_degerler) else None
    return {"etkin_boyut": d, "enerji_orani": enerji, "spektral_ucurum": ucurum}


def referans_rapor(tekil_degerler, sorgu_sayisi, sozluk_boyutu, tol):
    b = referans_boyut(tekil_degerler, tol)
    for k in (sorgu_sayisi, sozluk_boyutu):
        if isinstance(k, bool) or not isinstance(k, int) or k < len(tekil_degerler):
            raise ValueError("boyut")
    d = b["etkin_boyut"]
    ust = min(sorgu_sayisi, sozluk_boyutu)
    durum = "tam_altuzay" if (sorgu_sayisi > d and d < ust and b["enerji_orani"] >= 0.99) else "kismi_iz"
    return {
        "etkin_boyut": d,
        "sikistirma_orani": d / ust,
        "tahmini_parametre": d * sozluk_boyutu,
        "sizinti_durumu": durum,
    }


def _yakin(a, b, tol=1e-9):
    if isinstance(a, dict):
        return isinstance(b, dict) and set(a) == set(b) and all(_yakin(a[k], b[k], tol) for k in a)
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(_yakin(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, (bool, str)) or a is None:
        return type(a) is type(b) and a == b
    return _sayi(a) and _sayi(b) and abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def deney(merkezle_fn, boyut_fn, rapor_fn):
    try:
        import torch
    except ImportError as e:
        raise ai_lab.GercekLabYok(str(e)) from e
    tok, model, bilgi = ai_lab.dil_modeli()
    cihaz = ai_lab.torch_cihazi()
    model.to(cihaz)
    d_gercek = int(model.config.hidden_size)
    v_tam = int(model.config.vocab_size)
    n_sorgu, m_sutun, uzunluk = AYAR["sorgu_sayisi"], AYAR["sutun_sayisi"], AYAR["dizi_uzunlugu"]
    gen = torch.Generator().manual_seed(AYAR["seed"])
    sorgular = torch.randint(0, v_tam, (n_sorgu, uzunluk), generator=gen)
    sutunlar = torch.randperm(v_tam, generator=gen)[:m_sutun]

    # Saldırgan yalnız API'nin döndürdüğü log-olasılıkları görür: log_softmax her satıra farklı bir sabit ekler.
    with torch.no_grad():
        Z_tam = torch.cat([model(sorgular[i:i + 64].to(cihaz)).logits[:, -1, :].double() for i in range(0, n_sorgu, 64)])
    Z_ham = torch.log_softmax(Z_tam, dim=1)[:, sutunlar.to(cihaz)]

    ham_tekil = sorted([max(0.0, float(x)) for x in torch.linalg.svdvals(Z_ham).tolist()], reverse=True)
    Z_liste = Z_ham.tolist()

    r_merk = referans_merkezle(Z_liste)
    o_merk = merkezle_fn(copy.deepcopy(Z_liste))
    merkezle_ayni = _yakin(o_merk, r_merk)

    Z_merk_t = torch.tensor(r_merk, dtype=torch.float64, device=cihaz)
    merk_tekil = sorted([max(0.0, float(x)) for x in torch.linalg.svdvals(Z_merk_t).tolist()], reverse=True)

    r_boyut = referans_boyut(merk_tekil, AYAR["tol"])
    o_boyut = boyut_fn(list(merk_tekil), AYAR["tol"])
    boyut_ayni = _yakin(o_boyut, r_boyut)

    r_rap = referans_rapor(merk_tekil, n_sorgu, v_tam, AYAR["tol"])
    o_rap = rapor_fn(list(merk_tekil), n_sorgu, v_tam, AYAR["tol"])
    rapor_ayni = _yakin(o_rap, r_rap)

    ham_boyut = referans_boyut(ham_tekil, AYAR["tol"])["etkin_boyut"]

    # Kurtarılan altuzay gerçek son katmanla aynı mı? Üst d sağ tekil vektör ile lm_head sütunları arasındaki açılar.
    d_bulunan = r_boyut["etkin_boyut"]
    _, _, Vh = torch.linalg.svd(Z_merk_t, full_matrices=False)
    W_sub = model.lm_head.weight.detach().double()[sutunlar.to(cihaz)]
    Q, _ = torch.linalg.qr(W_sub - W_sub.mean(dim=0, keepdim=True))
    kosinuslar = torch.linalg.svdvals(Q.T @ Vh[:d_bulunan].T)
    i = d_bulunan
    ucurum_kat = float(merk_tekil[i - 1] / max(merk_tekil[i], 1e-300)) if i < len(merk_tekil) else None

    return {
        "cihaz": str(cihaz),
        "dtype": "float64 (model float32)",
        "model": {k: bilgi[k] for k in ("model", "revizyon", "agirlik_sha256", "parametre")},
        "surumler": {"torch": importlib.metadata.version("torch"), "transformers": importlib.metadata.version("transformers")},
        "ayarlar": AYAR,
        "merkezle_ayni": merkezle_ayni,
        "boyut_ayni": boyut_ayni,
        "rapor_ayni": rapor_ayni,
        "gercek_gizli_boyut": d_gercek,
        "sozluk_boyutu": v_tam,
        "ham_tahmini_boyut": ham_boyut,
        "merkezli_boyut_analizi": r_boyut,
        "sizinti_raporu": r_rap,
        "ucurum_kati": ucurum_kat,
        "uçurum_cevresi_bagil": [f"{merk_tekil[j] / merk_tekil[0]:.2e}" for j in range(max(0, i - 3), min(len(merk_tekil), i + 3))],
        "altuzay_kosinus_min": float(kosinuslar.min()),
        "ilk_15_tekil": [round(x, 6) for x in merk_tekil[:15]],
        "olcum": (f"SmolLM2-135M'e {n_sorgu} sorgu; API log-olasılıklarının {m_sutun} sütunu. Ham matris {ham_boyut} boyut gösterir "
                  f"(satır kayması +1); çift yönlü merkezleme sonrası SVD etkin boyutu {d_bulunan} (modelin hidden_size değeri {d_gercek}); "
                  f"uçurum {ucurum_kat:.0f} kat; kurtarılan altuzay lm_head sütunlarıyla en küçük açı kosinüsü {float(kosinuslar.min()):.6f}."),
        "sinir": "Yalnız son katmanın altuzayını (bir dönüşüme kadar) ve gizli boyutu kurtarır; ara katman ağırlıklarını, "
                 "top-k ile kırpılmış logprob API'sini ve logit_bias tarama maliyetini bu deney ölçmez.",
    }


def goster(merkezle_fn, boyut_fn, rapor_fn):
    r = deney(merkezle_fn, boyut_fn, rapor_fn)
    print("Model:", r["model"]["model"], "| cihaz:", r["cihaz"], "| gerçek gizli boyut (hidden_size):", r["gercek_gizli_boyut"], "| ham SVD boyut:", r["ham_tahmini_boyut"], "| merkezli SVD boyut:", r["merkezli_boyut_analizi"]["etkin_boyut"])
    print("Uçurum:", r["ucurum_kati"], "kat · çevresi (σ/σ1):", r["uçurum_cevresi_bagil"], "| altuzay kosinüs min:", round(r["altuzay_kosinus_min"], 8))
    print("İlk 15 tekil değer:", r["ilk_15_tekil"])
    print("Sızıntı raporu:", r["sizinti_raporu"])
    print("Sınır:", r["sinir"])
    print("Kanıt:", ai_lab.kanit_yaz("ai-saldiri-57-run", {"kaynak": "gercek", "kabul": False, "ders": "ai-saldiri-57", "deney": r}))
