"""Radyoaktif veri (radioactive data) ve dataset inference: eğitim kümesi hırsızlığının istatistiksel kanıtı."""
import importlib.metadata, math, random, secrets
import ai_lab

AYAR = {"seed": 46, "gizli": 24, "adim": 300, "lr": 0.02, "kanarya_oran": 0.25, "kanarya_guc": 0.6, "ornek_sayisi": 32, "t_esik": 2.5,
        "min_etki": 3.0, "min_etki_eski": 0.7, "null_yon": 64, "kanarya_sayisi": 4}


def _sayi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)


def referans_kanarya_hizalanma(fark_vektoru, kanarya_yonu):
    if not isinstance(fark_vektoru, list) or not isinstance(kanarya_yonu, list) or not fark_vektoru or len(fark_vektoru) != len(kanarya_yonu):
        raise ValueError("vektör")
    if not all(_sayi(v) for v in fark_vektoru + kanarya_yonu):
        raise ValueError("sayı")
    nf = math.sqrt(sum(x * x for x in fark_vektoru))
    nk = math.sqrt(sum(x * x for x in kanarya_yonu))
    if nf <= 0 or nk <= 0:
        raise ValueError("sıfır norm")
    ic = sum(a * b for a, b in zip(fark_vektoru, kanarya_yonu)) / nk
    kos = ic / nf
    return {"ic_carpim": float(ic), "kosinus": float(kos), "enerji_orani": float(kos * kos)}


def referans_welch_t(supheli_skorlar, temiz_skorlar):
    if not isinstance(supheli_skorlar, list) or not isinstance(temiz_skorlar, list) or len(supheli_skorlar) < 2 or len(temiz_skorlar) < 2:
        raise ValueError("liste")
    if not all(_sayi(v) for v in supheli_skorlar + temiz_skorlar):
        raise ValueError("sayı")
    n1, n2 = len(supheli_skorlar), len(temiz_skorlar)
    m1 = sum(supheli_skorlar) / n1
    m2 = sum(temiz_skorlar) / n2
    v1 = sum((x - m1) ** 2 for x in supheli_skorlar) / (n1 - 1)
    v2 = sum((y - m2) ** 2 for y in temiz_skorlar) / (n2 - 1)
    se = math.sqrt(v1 / n1 + v2 / n2)
    spool = math.sqrt(((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2))
    if se <= 0 or spool <= 0:
        raise ValueError("sıfır varyans")
    fark = m1 - m2
    return {"ort_fark": float(fark), "standart_hata": float(se), "t_degeri": float(fark / se), "cohen_d": float(fark / spool)}


def referans_veri_hirsizligi(supheli_skorlar, temiz_skorlar, t_esik, min_etki_boyutu):
    if not _sayi(t_esik) or t_esik <= 0 or not _sayi(min_etki_boyutu) or min_etki_boyutu <= 0:
        raise ValueError("eşik")
    m = referans_welch_t(supheli_skorlar, temiz_skorlar)
    t_ok = m["t_degeri"] >= t_esik
    d_ok = m["cohen_d"] >= min_etki_boyutu
    if t_ok and d_ok:
        karar = "calinti_kanitlandi"
    elif t_ok or d_ok:
        karar = "belirsiz"
    else:
        karar = "kanit_yok"
    return {
        "karar": karar, "kanitlandi": bool(t_ok and d_ok),
        "t_degeri": m["t_degeri"], "cohen_d": m["cohen_d"], "ort_fark": m["ort_fark"]
    }


def _yakin(a, b, tol=1e-7):
    if isinstance(a, dict):
        return isinstance(b, dict) and set(a) == set(b) and all(_yakin(a[k], b[k], tol) for k in a)
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(_yakin(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, (bool, str, int)) or a is None:
        return type(a) is type(b) and a == b
    return _sayi(a) and _sayi(b) and abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def deney(hizalanma_fn, welch_fn, karar_fn):
    try:
        import torch
        from sklearn.datasets import load_digits
    except ImportError as e:
        raise ai_lab.GercekLabYok(str(e)) from e
    cihaz = ai_lab.torch_cihazi()
    seed = AYAR["seed"] + secrets.randbelow(500)
    torch.manual_seed(seed)
    v = load_digits()
    X = torch.tensor(v.data / 16.0, dtype=torch.float32, device=cihaz)
    Y = torch.tensor(v.target, dtype=torch.long, device=cihaz)

    # Gizli radyoaktif taşıyıcı yön (birim vektör)
    kanarya_u = torch.randn(64, dtype=torch.float32, device=cihaz)
    kanarya_u = kanarya_u / kanarya_u.norm().clamp_min(1e-8)

    # Ek gizli kanaryalar: sınıf 1..K-1 için ayrı yönler (çoklu kanarya ile birleşik kanıt)
    g_k = torch.Generator(device="cpu").manual_seed(seed + 7)
    ek_kanaryalar = [r / r.norm() for r in torch.randn(AYAR["kanarya_sayisi"] - 1, 64, generator=g_k).to(cihaz)]
    kanaryalar = [kanarya_u] + ek_kanaryalar

    # Radyoaktif eğitim kümesi: sınıf c örneklerine kanarya_c yönünde işaret eklenir
    X_rad = X[:1000].clone()
    Y_rad = Y[:1000].clone()
    for c, u_c in enumerate(kanaryalar):
        m_c = (Y_rad == c)
        X_rad[m_c] = (X_rad[m_c] + AYAR["kanarya_guc"] * u_c).clamp(0.0, 1.0)

    def model_egit(X_egitim, Y_egitim, tohum_ek):
        torch.manual_seed(seed + tohum_ek)
        m = torch.nn.Sequential(torch.nn.Linear(64, AYAR["gizli"]), torch.nn.ReLU(), torch.nn.Linear(AYAR["gizli"], 10)).to(cihaz)
        opt = torch.optim.Adam(m.parameters(), lr=AYAR["lr"])
        for _ in range(AYAR["adim"]):
            opt.zero_grad()
            torch.nn.functional.cross_entropy(m(X_egitim), Y_egitim).backward()
            opt.step()
        return m

    # Şüpheli model radyoaktif veriyle, temiz model işaretsiz ayrı veriyle eğitilir
    m_supheli = model_egit(X_rad, Y_rad, 1)
    m_temiz = model_egit(X[500:1500], Y[500:1500], 2)

    # Yanlış pozitif kontrolü: şüpheliyle AYNI veriyle ama işaretsiz eğitilmiş model "çalıntı" sayılmamalı
    m_kontrol = model_egit(X[:1000], Y[:1000], 3)
    X_sinama = X[1500 : 1500 + AYAR["ornek_sayisi"]]

    def tepki(m, yon):
        """Sınama örneklerinde yön boyunca küçük kaydırmanın sınıf-0 logitine etkisi (örnek başına)."""
        with torch.no_grad():
            return (m((X_sinama + 0.25 * yon).clamp(0.0, 1.0))[:, 0] - m(X_sinama)[:, 0]).double().tolist()

    g_null = torch.Generator(device="cpu").manual_seed(seed + 99)
    rastgele_yonler = [r / r.norm() for r in torch.randn(AYAR["null_yon"], 64, generator=g_null).to(cihaz)]

    alt_kumeler = [list(range(i, AYAR["ornek_sayisi"], 4)) for i in range(4)]

    def kanarya_grubu(m):
        """Kanarya yönüne tepki, örneklerin 4 ayrık alt kümesinde ortalanır (yön düzeyinde ölçüm, örnek gürültüsü azalır)."""
        t = tepki(m, kanarya_u)
        return [sum(t[j] for j in s) / len(s) for s in alt_kumeler]

    def null_tepki(m):
        """Null: her rastgele yön için TEK bir ortalama tepki (gözlem birimi yöndür, örnek değil)."""
        return [sum(tepki(m, r)) / AYAR["ornek_sayisi"] for r in rastgele_yonler]

    # (A) Eski yöntem: şüpheli modelin örnek başına kanarya tepkisi, farklı veriyle eğitilmiş BAŞKA bir modelinkiyle karşılaştırılır
    supheli_kanarya, temiz_kanarya, kontrol_kanarya = tepki(m_supheli, kanarya_u), tepki(m_temiz, kanarya_u), tepki(m_kontrol, kanarya_u)
    yontem_a = {"supheli": referans_veri_hirsizligi(supheli_kanarya, temiz_kanarya, AYAR["t_esik"], AYAR["min_etki_eski"]),
                "kontrol": referans_veri_hirsizligi(kontrol_kanarya, temiz_kanarya, AYAR["t_esik"], AYAR["min_etki_eski"])}
    # (B) Rastgele yön null'u (Sablayrolles vd. 2020 fikri): AYNI modelin kanarya yönü tepkisi, rastgele yönlerin tepki dağılımıyla
    #     karşılaştırılır. Gözlem birimi yön olduğu için Cohen d burada fiilen bir z-skorudur; eşik buna göre yüksektir.
    supheli_skorlar, temiz_skorlar = kanarya_grubu(m_supheli), null_tepki(m_supheli)

    with torch.no_grad():
        # İlk katman ağırlıklarının ortalama yön farkı (ağırlık uzayında hizalanma)
        w_fark = (m_supheli[0].weight - m_kontrol[0].weight).mean(dim=0).double().tolist()
        u_liste = kanarya_u.double().tolist()
        X_test, Y_test = X[1500:], Y[1500:]
        dogruluk = {ad: float((m(X_test).argmax(1) == Y_test).float().mean()) for ad, m in
                    (("supheli", m_supheli), ("temiz", m_temiz), ("kontrol", m_kontrol))}

    hiz_ref = referans_kanarya_hizalanma(w_fark, u_liste)
    hiz_ogr = hizalanma_fn(list(w_fark), list(u_liste))
    hiz_ayni = _yakin(hiz_ogr, hiz_ref)

    welch_ref = referans_welch_t(supheli_skorlar, temiz_skorlar)
    welch_ogr = welch_fn(list(supheli_skorlar), list(temiz_skorlar))
    welch_ayni = _yakin(welch_ogr, welch_ref)

    karar_ref = referans_veri_hirsizligi(supheli_skorlar, temiz_skorlar, AYAR["t_esik"], AYAR["min_etki"])
    karar_ogr = karar_fn(list(supheli_skorlar), list(temiz_skorlar), AYAR["t_esik"], AYAR["min_etki"])
    karar_ayni = _yakin(karar_ogr, karar_ref)

    # (C) Kara kutu çoklu kanarya testi: yalnız log-olasılık API'si (log_softmax) sorgulanır. Her kanarya c için sınıf-c
    #     log-olasılığının kanarya yönüne tepkisi, aynı sınıfın rastgele yönlere tepki dağılımına göre z-skoruna çevrilir;
    #     K kanarya Stouffer ile birleştirilir: Z = Σ z_c / √K, tek taraflı p = Φ(−Z).
    def logp_tepki(m, yon, c):
        with torch.no_grad():
            lp0 = torch.log_softmax(m(X_sinama), dim=1)[:, c]
            lp1 = torch.log_softmax(m((X_sinama + 0.25 * yon).clamp(0.0, 1.0)), dim=1)[:, c]
        return float((lp1 - lp0).mean())

    def kara_kutu(m):
        zler = []
        for c, u_c in enumerate(kanaryalar):
            null = [logp_tepki(m, r, c) for r in rastgele_yonler]
            mu = sum(null) / len(null)
            sd = math.sqrt(sum((x - mu) ** 2 for x in null) / (len(null) - 1))
            zler.append((logp_tepki(m, u_c, c) - mu) / sd)
        Z = sum(zler) / math.sqrt(len(zler))
        return {"z_kanarya": [round(z, 3) for z in zler], "Z_birlesik": round(Z, 3), "p_degeri": 0.5 * math.erfc(Z / math.sqrt(2))}

    kara = {"supheli": kara_kutu(m_supheli), "kontrol": kara_kutu(m_kontrol), "temiz": kara_kutu(m_temiz)}

    k_a, k_b = kanarya_grubu(m_kontrol), null_tepki(m_kontrol)
    kontrol_karar = referans_veri_hirsizligi(k_a, k_b, AYAR["t_esik"], AYAR["min_etki"])
    temiz_karar = referans_veri_hirsizligi(kanarya_grubu(m_temiz), null_tepki(m_temiz), AYAR["t_esik"], AYAR["min_etki"])
    karar_ayni = karar_ayni and _yakin(karar_fn(list(k_a), list(k_b), AYAR["t_esik"], AYAR["min_etki"]), kontrol_karar)

    return {
        "cihaz": str(cihaz), "dtype": "float32",
        "surumler": {x: importlib.metadata.version(x) for x in ("torch", "scikit-learn")},
        "ayarlar": AYAR, "seed": seed,
        "hiz_ayni": hiz_ayni, "welch_ayni": welch_ayni, "karar_ayni": karar_ayni,
        "agirlik_hizalanma": hiz_ref, "welch": welch_ref, "karar": karar_ref,
        "kontrol_karar": kontrol_karar, "temiz_karar": temiz_karar, "yontem_a": yontem_a, "gorev_dogrulugu": dogruluk,
        "kara_kutu": kara,
        "olcum": (f"load_digits: sınıf 0 eğitim örneklerine gizli bir yönde (güç {AYAR['kanarya_guc']}) radyoaktif işaret kondu. Rastgele yön "
                  f"null'u ({AYAR['null_yon']} yön): şüpheli t={welch_ref['t_degeri']:.1f}, d={welch_ref['cohen_d']:.2f}, '{karar_ref['karar']}'; "
                  f"aynı veriyle işaretsiz kontrol t={kontrol_karar['t_degeri']:.2f}, '{kontrol_karar['karar']}'; farklı veriyle temiz model "
                  f"t={temiz_karar['t_degeri']:.2f}, '{temiz_karar['karar']}'. Eski yöntem (başka bir modelle karşılaştırma): şüpheli "
                  f"'{yontem_a['supheli']['karar']}', kontrol '{yontem_a['kontrol']['karar']}' (t={yontem_a['kontrol']['t_degeri']:.2f}). "
                  f"Kara kutu {AYAR['kanarya_sayisi']} kanaryalı Stouffer testi (yalnız log-olasılık): şüpheli Z={kara['supheli']['Z_birlesik']} "
                  f"p={kara['supheli']['p_degeri']:.1e}, kontrol Z={kara['kontrol']['Z_birlesik']} p={kara['kontrol']['p_degeri']:.2f}, temiz "
                  f"Z={kara['temiz']['Z_birlesik']} p={kara['temiz']['p_degeri']:.2f}. "
                  f"Ağırlık farkının kanarya yönüne kosinüsü {hiz_ref['kosinus']:.3f}. Görev doğrulukları "
                  f"{ {k: round(v, 3) for k, v in dogruluk.items()} }."),
        "sinir": ("8x8 rakamlar ve küçük bir MLP; işaret gücü büyüktür ve tek bir sınıfa uygulanır. Şüpheli modelin eğitimi bilinir (beyaz kutu "
                  "logitleri); gerçek dataset inference kara kutu API'lerde daha zayıftır. İstatistiksel test olasılıksal kanıt üretir; "
                  "kanarya yönü gizli tutulmalıdır.")
    }


def goster(hizalanma_fn, welch_fn, karar_fn):
    r = deney(hizalanma_fn, welch_fn, karar_fn)
    print("Cihaz:", r["cihaz"], "| Tohum:", r["seed"])
    print("Ağırlık kanarya hizalanması:", r["agirlik_hizalanma"])
    print("Welch t-testi:", r["welch"])
    print("Veri hırsızlığı kararı:", r["karar"])
    print("Kontrol (aynı veri, işaretsiz) kararı:", r["kontrol_karar"], "| temiz model kararı:", r["temiz_karar"])
    print("Eski yöntem (başka modelle karşılaştırma):", r["yontem_a"])
    print("Kara kutu çoklu kanarya (Stouffer):", r["kara_kutu"])
    print("Görev doğrulukları:", r["gorev_dogrulugu"])
    print("Sınır:", r["sinir"])
    print("Kanıt:", ai_lab.kanit_yaz("ai-guvence-46-run", {"kaynak": "gercek", "kabul": False, "ders": "ai-guvence-46", "deney": r}))
