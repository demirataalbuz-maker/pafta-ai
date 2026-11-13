# -*- coding: utf-8 -*-
"""ai-guvence-04 gerçek deneyi: Yanlış pozitiflerin güvenlik maliyeti ve eşik optimizasyonu.

Öğrencinin `maliyet_profili_dogrula`, `esik_matrisi` ve `maliyet_raporu` işlevleri,
gerçek `scikit-learn` (`LogisticRegression`) sınıflandırıcısının test kümesi `predict_proba`
olasılık skorları üzerinde farklı eşik ve maliyet profilleriyle sınanır.
"""
import copy
import math
import re
import ai_lab


PROFIL_FN_AGIR = {"fp_maliyeti": 2.0, "fn_maliyeti": 15.0, "para_birimi": "TRY"}
PROFIL_FP_AGIR = {"fp_maliyeti": 15.0, "fn_maliyeti": 2.0, "para_birimi": "TRY"}
ESIKLER = [0.2, 0.35, 0.5, 0.65, 0.8]


def maliyet_profili_dogrula_referans(profil):
    if not isinstance(profil, dict) or set(profil) != {"fp_maliyeti", "fn_maliyeti", "para_birimi"}:
        raise ValueError("profil şeması geçersiz")
    for alan in ("fp_maliyeti", "fn_maliyeti"):
        deger = profil[alan]
        if isinstance(deger, bool) or not isinstance(deger, (int, float)) or not math.isfinite(deger) or deger < 0:
            raise ValueError("maliyet geçersiz")
    if profil["para_birimi"] not in ("TRY", "USD", "EUR"):
        raise ValueError("para birimi geçersiz")
    return {
        "fp_maliyeti": profil["fp_maliyeti"],
        "fn_maliyeti": profil["fn_maliyeti"],
        "para_birimi": profil["para_birimi"],
    }


def esik_matrisi_referans(kayitlar, esik):
    if isinstance(esik, bool) or not isinstance(esik, (int, float)) or not math.isfinite(esik) or esik < 0 or esik > 1:
        raise ValueError("eşik geçersiz")
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar geçersiz")
    gorulen = set()
    sonuc = {"esik": esik, "tp": 0, "fp": 0, "fn": 0, "tn": 0}
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"id", "gercek", "skor"}:
            raise ValueError("kayıt şeması geçersiz")
        kimlik = kayit["id"]
        if not isinstance(kimlik, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kimlik) or kimlik in gorulen:
            raise ValueError("kimlik geçersiz")
        if kayit["gercek"] not in ("yelkovan", "diger"):
            raise ValueError("etiket geçersiz")
        skor = kayit["skor"]
        if isinstance(skor, bool) or not isinstance(skor, (int, float)) or not math.isfinite(skor) or skor < 0 or skor > 1:
            raise ValueError("skor geçersiz")
        tahmin = "yelkovan" if skor >= esik else "diger"
        if kayit["gercek"] == "yelkovan" and tahmin == "yelkovan":
            sonuc["tp"] += 1
        elif kayit["gercek"] == "diger" and tahmin == "yelkovan":
            sonuc["fp"] += 1
        elif kayit["gercek"] == "yelkovan":
            sonuc["fn"] += 1
        else:
            sonuc["tn"] += 1
        gorulen.add(kimlik)
    return sonuc


def maliyet_raporu_referans(matrisler, profil):
    p = maliyet_profili_dogrula_referans(profil)
    if not isinstance(matrisler, list) or not matrisler:
        raise ValueError("matrisler geçersiz")
    esikler = set()
    satirlar = []
    toplam_kayit = None
    for matris in matrisler:
        if not isinstance(matris, dict) or set(matris) != {"esik", "tp", "fp", "fn", "tn"}:
            raise ValueError("matris şeması geçersiz")
        esik = matris["esik"]
        if isinstance(esik, bool) or not isinstance(esik, (int, float)) or not math.isfinite(esik) or esik < 0 or esik > 1 or esik in esikler:
            raise ValueError("eşik geçersiz")
        for alan in ("tp", "fp", "fn", "tn"):
            deger = matris[alan]
            if isinstance(deger, bool) or not isinstance(deger, int) or deger < 0:
                raise ValueError("sayım geçersiz")
        toplam = sum(matris[a] for a in ("tp", "fp", "fn", "tn"))
        if toplam <= 0:
            raise ValueError("matris boş")
        if toplam_kayit is None:
            toplam_kayit = toplam
        if toplam != toplam_kayit:
            raise ValueError("toplam kayıt sayısı farklı")
        fpr = matris["fp"] / (matris["fp"] + matris["tn"]) if matris["fp"] + matris["tn"] else None
        maliyet = matris["fp"] * p["fp_maliyeti"] + matris["fn"] * p["fn_maliyeti"]
        satirlar.append({
            "esik": esik,
            "tp": matris["tp"],
            "fp": matris["fp"],
            "fn": matris["fn"],
            "tn": matris["tn"],
            "fpr": round(fpr, 6) if fpr is not None else None,
            "maliyet": round(maliyet, 6),
            "_ham": maliyet,
        })
        esikler.add(esik)
    satirlar.sort(key=lambda x: x["esik"])
    en_iyi = min(satirlar, key=lambda x: (x["_ham"], x["esik"]))["esik"]
    for s in satirlar:
        del s["_ham"]
    return {"para_birimi": p["para_birimi"], "en_iyi_esik": en_iyi, "satirlar": satirlar}


def deney(maliyet_profili_dogrula, esik_matrisi, maliyet_raporu):
    try:
        import sklearn
        from sklearn.datasets import make_classification
        from sklearn.linear_model import LogisticRegression
    except Exception as exc:
        raise ai_lab.GercekLabYok(f"scikit-learn gerekli: {exc}") from exc

    X, y = make_classification(
        n_samples=200,
        n_features=6,
        n_informative=4,
        n_redundant=1,
        class_sep=0.75,
        random_state=404,
    )
    clf = LogisticRegression(random_state=404, max_iter=200)
    clf.fit(X[:120], y[:120])

    olasiliklar = clf.predict_proba(X[120:])[:, 1]
    kayitlar = [
        {
            "id": f"test-{i + 1:03d}",
            "gercek": "yelkovan" if int(y[120 + i]) == 1 else "diger",
            "skor": round(float(olasiliklar[i]), 6),
        }
        for i in range(80)
    ]

    ogr_p1 = maliyet_profili_dogrula(copy.deepcopy(PROFIL_FN_AGIR))
    ref_p1 = maliyet_profili_dogrula_referans(copy.deepcopy(PROFIL_FN_AGIR))

    ogr_matrisler = [esik_matrisi(copy.deepcopy(kayitlar), e) for e in reversed(ESIKLER)]
    ref_matrisler = [esik_matrisi_referans(copy.deepcopy(kayitlar), e) for e in reversed(ESIKLER)]

    ogr_rapor_fn = maliyet_raporu(copy.deepcopy(ogr_matrisler), copy.deepcopy(PROFIL_FN_AGIR))
    ref_rapor_fn = maliyet_raporu_referans(copy.deepcopy(ref_matrisler), copy.deepcopy(PROFIL_FN_AGIR))

    ogr_rapor_fp = maliyet_raporu(copy.deepcopy(ogr_matrisler), copy.deepcopy(PROFIL_FP_AGIR))
    ref_rapor_fp = maliyet_raporu_referans(copy.deepcopy(ref_matrisler), copy.deepcopy(PROFIL_FP_AGIR))

    kontroller = {
        "profil_uyumu": ogr_p1 == ref_p1,
        "matris_uyumu": ogr_matrisler == ref_matrisler,
        "fn_agir_rapor_uyumu": ogr_rapor_fn == ref_rapor_fn,
        "fp_agir_rapor_uyumu": ogr_rapor_fp == ref_rapor_fp,
        "maliyet_esigi_kaydirdi": ref_rapor_fn["en_iyi_esik"] <= ref_rapor_fp["en_iyi_esik"],
    }
    ozet = {
        "sklearn_surum": sklearn.__version__,
        "test_kayit_sayisi": len(kayitlar),
        "fn_agir_en_iyi_esik": ref_rapor_fn["en_iyi_esik"],
        "fp_agir_en_iyi_esik": ref_rapor_fp["en_iyi_esik"],
        "fn_agir_satirlar": ref_rapor_fn["satirlar"],
    }
    return {
        "profil": ogr_p1,
        "matrisler": ogr_matrisler,
        "rapor_fn_agir": ogr_rapor_fn,
        "rapor_fp_agir": ogr_rapor_fp,
        "kontroller": kontroller,
        "ozet": ozet,
    }


def goster(maliyet_profili_dogrula, esik_matrisi, maliyet_raporu):
    rapor = deney(maliyet_profili_dogrula, esik_matrisi, maliyet_raporu)
    print("FN ağır en iyi eşik:", rapor["rapor_fn_agir"].get("en_iyi_esik"))
    print("FP ağır en iyi eşik:", rapor["rapor_fp_agir"].get("en_iyi_esik"))
