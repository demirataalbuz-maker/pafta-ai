# -*- coding: utf-8 -*-
"""ai-guvence-12 gerçek deneyi: Etiket gürültüsü ile hedefli zehirlemenin ayrımı.

Öğrencinin `etiket_gecis_profili`, `etki_karsilastirmasi` ve `deney_bayraklari` işlevleri,
üç ayrı `scikit-learn` (`LogisticRegression`) modelinin (`taban`, `rastgele` etiket gürültüsü
ve `hedefli` sınıf çevirme) gerçek eğitim/test doğruluklarıyla sınanır.
"""
import copy
import math
import ai_lab


def etiket_gecis_profili_referans(once, sonra):
    if not isinstance(once, list) or not isinstance(sonra, list) or not once or len(once) != len(sonra):
        raise ValueError("etiket listeleri geçersiz")
    for etiketler in (once, sonra):
        for e in etiketler:
            if isinstance(e, bool) or not isinstance(e, int) or e < 0:
                raise ValueError("etiket geçersiz")
    sayimlar = {}
    degisen = 0
    for eski, yeni in zip(once, sonra):
        if eski != yeni:
            degisen += 1
            k = f"{eski}>{yeni}"
            sayimlar[k] = sayimlar.get(k, 0) + 1
    return {
        "toplam": len(once),
        "degisen": degisen,
        "degisim_orani": round(degisen / len(once), 6),
        "gecisler": {k: sayimlar[k] for k in sorted(sayimlar)},
    }


def etki_karsilastirmasi_referans(kayitlar):
    kosul_sirasi = ("taban", "rastgele", "hedefli")
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar geçersiz")
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"kosul", "temiz", "hedef"}:
            raise ValueError("şema geçersiz")
        if kayit["kosul"] not in kosul_sirasi:
            raise ValueError("koşul geçersiz")
        for alan in ("temiz", "hedef"):
            d = kayit[alan]
            if isinstance(d, bool) or not isinstance(d, (int, float)) or not math.isfinite(d) or d < 0 or d > 1:
                raise ValueError("doğruluk geçersiz")
    if {x["kosul"] for x in kayitlar} != set(kosul_sirasi):
        raise ValueError("üç koşul gerekli")
    ort = {}
    for kosul in kosul_sirasi:
        grup = [x for x in kayitlar if x["kosul"] == kosul]
        ort[kosul] = {a: sum(x[a] for x in grup) / len(grup) for a in ("temiz", "hedef")}
    return {
        "ortalamalar": {k: {a: round(v, 6) for a, v in ort[k].items()} for k in kosul_sirasi},
        "temiz_kayip": {k: round(ort["taban"]["temiz"] - ort[k]["temiz"], 6) for k in ("rastgele", "hedefli")},
        "hedef_kayip": {k: round(ort["taban"]["hedef"] - ort[k]["hedef"], 6) for k in ("rastgele", "hedefli")},
    }


def deney_bayraklari_referans(kayitlar, temiz_esik, hedef_esik):
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar geçersiz")
    for esik in (temiz_esik, hedef_esik):
        if isinstance(esik, bool) or not isinstance(esik, (int, float)) or not math.isfinite(esik) or esik < 0 or esik > 1:
            raise ValueError("eşik geçersiz")
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"tur", "temiz_kayip", "hedef_kayip"}:
            raise ValueError("şema geçersiz")
        if kayit["tur"] not in ("rastgele", "hedefli"):
            raise ValueError("tür geçersiz")
        for alan in ("temiz_kayip", "hedef_kayip"):
            d = kayit[alan]
            if isinstance(d, bool) or not isinstance(d, (int, float)) or not math.isfinite(d) or d < 0 or d > 1:
                raise ValueError("kayıp geçersiz")
    if {x["tur"] for x in kayitlar} != {"rastgele", "hedefli"}:
        raise ValueError("iki tür gerekli")
    sonuc = {}
    for tur in ("rastgele", "hedefli"):
        grup = [x for x in kayitlar if x["tur"] == tur]
        temiz = sum(x["temiz_kayip"] for x in grup) / len(grup)
        hedef = sum(x["hedef_kayip"] for x in grup) / len(grup)
        sonuc[tur] = {
            "temiz_kayip": round(temiz, 6),
            "hedef_kayip": round(hedef, 6),
            "hedef_odakli": hedef >= hedef_esik and temiz <= temiz_esik,
        }
    return sonuc


def deney(etiket_gecis_profili, etki_karsilastirmasi, deney_bayraklari):
    try:
        import numpy as np
        import sklearn
        from sklearn.datasets import make_blobs
        from sklearn.linear_model import LogisticRegression
    except Exception as exc:
        raise ai_lab.GercekLabYok(f"scikit-learn gerekli: {exc}") from exc

    X, y = make_blobs(
        n_samples=240,
        centers=[[-3.0, -3.0], [0.0, 3.0], [3.5, -2.5]],
        cluster_std=1.15,
        random_state=12,
    )
    X_egitim, y_egitim = X[:150].copy(), y[:150].copy()
    X_test, y_test = X[150:].copy(), y[150:].copy()

    # Rastgele gürültü: her sınıftan bazı örnekleri farklı sınıflara dağıt
    rng = np.random.default_rng(12)
    y_rastgele = y_egitim.copy()
    rastgele_idx = rng.choice(len(y_egitim), size=36, replace=False)
    for idx in rastgele_idx:
        y_rastgele[idx] = int((y_rastgele[idx] + rng.integers(1, 3)) % 3)

    # Hedefli zehirleme: sınıf 2 (hedef sınıf) örneklerinin çoğunu sınıf 0'a çevir
    y_hedefli = y_egitim.copy()
    hedef_sinif = 2
    hedef_indeksler = [i for i, e in enumerate(y_egitim) if int(e) == hedef_sinif][:32]
    for idx in hedef_indeksler:
        y_hedefli[idx] = 0

    once_list = [int(v) for v in y_egitim.tolist()]
    hedefli_list = [int(v) for v in y_hedefli.tolist()]
    ogr_gecis = etiket_gecis_profili(copy.deepcopy(once_list), copy.deepcopy(hedefli_list))
    ref_gecis = etiket_gecis_profili_referans(copy.deepcopy(once_list), copy.deepcopy(hedefli_list))

    temiz_mask = y_test != hedef_sinif
    hedef_mask = y_test == hedef_sinif

    kosul_kayitlari = []
    for kosul_adi, y_train_kosul in [("taban", y_egitim), ("rastgele", y_rastgele), ("hedefli", y_hedefli)]:
        clf = LogisticRegression(random_state=12, max_iter=300)
        clf.fit(X_egitim, y_train_kosul)
        tahmin = clf.predict(X_test)
        temiz_acc = round(float((tahmin[temiz_mask] == y_test[temiz_mask]).mean()), 6)
        hedef_acc = round(float((tahmin[hedef_mask] == y_test[hedef_mask]).mean()), 6)
        kosul_kayitlari.append({"kosul": kosul_adi, "temiz": temiz_acc, "hedef": hedef_acc})

    ogr_etki = etki_karsilastirmasi(copy.deepcopy(kosul_kayitlari))
    ref_etki = etki_karsilastirmasi_referans(copy.deepcopy(kosul_kayitlari))

    kayip_kayitlari = [
        {
            "tur": "rastgele",
            "temiz_kayip": max(0.0, ref_etki["temiz_kayip"]["rastgele"]),
            "hedef_kayip": max(0.0, ref_etki["hedef_kayip"]["rastgele"]),
        },
        {
            "tur": "hedefli",
            "temiz_kayip": max(0.0, ref_etki["temiz_kayip"]["hedefli"]),
            "hedef_kayip": max(0.0, ref_etki["hedef_kayip"]["hedefli"]),
        },
    ]
    ogr_bayrak = deney_bayraklari(copy.deepcopy(kayip_kayitlari), 0.12, 0.25)
    ref_bayrak = deney_bayraklari_referans(copy.deepcopy(kayip_kayitlari), 0.12, 0.25)

    kontroller = {
        "gecis_uyumu": ogr_gecis == ref_gecis and ref_gecis["gecisler"] == {"2>0": len(hedef_indeksler)},
        "etki_uyumu": ogr_etki == ref_etki,
        "bayrak_uyumu": ogr_bayrak == ref_bayrak,
        "hedefli_yakalandi": ref_bayrak["hedefli"]["hedef_odakli"] and not ref_bayrak["rastgele"]["hedef_odakli"],
    }
    ozet = {
        "sklearn_surum": sklearn.__version__,
        "hedefli_gecisler": ref_gecis["gecisler"],
        "hedef_kayip": ref_etki["hedef_kayip"],
        "temiz_kayip": ref_etki["temiz_kayip"],
        "hedefli_bayrak": ref_bayrak["hedefli"]["hedef_odakli"],
    }
    return {
        "gecis": ogr_gecis,
        "etki": ogr_etki,
        "bayraklar": ogr_bayrak,
        "kontroller": kontroller,
        "ozet": ozet,
    }


def goster(etiket_gecis_profili, etki_karsilastirmasi, deney_bayraklari):
    rapor = deney(etiket_gecis_profili, etki_karsilastirmasi, deney_bayraklari)
    print("Canlı geçiş profili:", rapor["gecis"])
    print("Canlı deney bayrakları:", rapor["bayraklar"])
