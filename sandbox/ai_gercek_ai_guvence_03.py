# -*- coding: utf-8 -*-
"""ai-guvence-03 gerçek deneyi: Tehdit modelinden deney sorusuna ve canlı sınıflandırıcı sınaması.

Öğrencinin `tehdit_karti_dogrula`, `deney_sorusu_uret` ve `deney_sorusunu_degerlendir`
işlevleri, gerçek `scikit-learn` (`LogisticRegression`) sınıflandırıcısında temiz taban
ile zehirlenmiş/bozulmuş deney koşularının tekrarlı `asr` ve `f1` farkları üzerinde sınanır.
"""
import copy
import math
import re
import ai_lab


KART = {
    "id": "tehdit-poisoning-01",
    "kategori": "poisoning",
    "varlik": "sklearn_logistic_regression",
    "aktor": "etiket_zehirleyici",
    "varsayim": "egitim_kumesinin_yuzde_on_besi_tetikleyici_ile_cevrilir",
}


def tehdit_karti_dogrula_referans(karti):
    if not isinstance(karti, dict) or set(karti) != {"id", "kategori", "varlik", "aktor", "varsayim"}:
        raise ValueError("kart şeması geçersiz")
    if not isinstance(karti["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", karti["id"]):
        raise ValueError("kimlik geçersiz")
    if karti["kategori"] not in ("evasion", "poisoning", "gizlilik", "tedarik"):
        raise ValueError("kategori geçersiz")
    for alan in ("varlik", "aktor", "varsayim"):
        deger = karti[alan]
        if not isinstance(deger, str) or not deger or deger != deger.strip() or any(ord(k) < 32 for k in deger):
            raise ValueError("metin alanı geçersiz")
    return {
        "id": karti["id"],
        "kategori": karti["kategori"],
        "varlik": karti["varlik"],
        "aktor": karti["aktor"],
        "varsayim": karti["varsayim"],
    }


def deney_sorusu_uret_referans(karti, olcut, yon, esik):
    k = tehdit_karti_dogrula_referans(karti)
    uyum = {
        "evasion": ("asr", "f1"),
        "poisoning": ("asr", "f1", "fpr"),
        "gizlilik": ("sizinti_orani",),
        "tedarik": ("fpr", "asr"),
    }
    if olcut not in uyum[k["kategori"]] or yon not in ("artis", "azalis"):
        raise ValueError("ölçüt veya yön geçersiz")
    if isinstance(esik, bool) or not isinstance(esik, (int, float)) or not math.isfinite(esik) or esik < 0 or esik > 1:
        raise ValueError("eşik geçersiz")
    soru = k["id"] + " icin " + olcut + " " + yon + " esigi " + format(esik, ".6f")
    return {"tehdit_id": k["id"], "olcut": olcut, "yon": yon, "esik": esik, "soru": soru}


def deney_sorusunu_degerlendir_referans(soru, olcumler):
    if not isinstance(soru, dict) or set(soru) != {"tehdit_id", "olcut", "yon", "esik", "soru"}:
        raise ValueError("soru şeması geçersiz")
    if not isinstance(soru["tehdit_id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", soru["tehdit_id"]):
        raise ValueError("kimlik geçersiz")
    if soru["olcut"] not in ("asr", "f1", "fpr", "sizinti_orani") or soru["yon"] not in ("artis", "azalis"):
        raise ValueError("ölçüt/yön geçersiz")
    esik = soru["esik"]
    if isinstance(esik, bool) or not isinstance(esik, (int, float)) or not math.isfinite(esik) or esik < 0 or esik > 1:
        raise ValueError("eşik geçersiz")
    beklenen_soru = soru["tehdit_id"] + " icin " + soru["olcut"] + " " + soru["yon"] + " esigi " + format(esik, ".6f")
    if soru["soru"] != beklenen_soru:
        raise ValueError("soru metni uyuşmuyor")
    if not isinstance(olcumler, list) or not olcumler:
        raise ValueError("ölçümler geçersiz")
    gorulen = set()
    bulgular = []
    ham_farklar = []
    for olcum in olcumler:
        if not isinstance(olcum, dict) or set(olcum) != {"tekrar", "taban", "deney"}:
            raise ValueError("ölçüm şeması geçersiz")
        tekrar = olcum["tekrar"]
        if isinstance(tekrar, bool) or not isinstance(tekrar, int) or tekrar <= 0 or tekrar in gorulen:
            raise ValueError("tekrar geçersiz")
        for alan in ("taban", "deney"):
            deger = olcum[alan]
            if isinstance(deger, bool) or not isinstance(deger, (int, float)) or not math.isfinite(deger) or deger < 0 or deger > 1:
                raise ValueError("değer geçersiz")
        fark = olcum["deney"] - olcum["taban"] if soru["yon"] == "artis" else olcum["taban"] - olcum["deney"]
        gorulen.add(tekrar)
        ham_farklar.append(fark)
        bulgular.append({"tekrar": tekrar, "delta": round(fark, 6)})
    bulgular.sort(key=lambda x: x["tekrar"])
    return {
        "tehdit_id": soru["tehdit_id"],
        "karar": "desteklendi" if all(f >= esik for f in ham_farklar) else "desteklenmedi",
        "ortalama_delta": round(sum(ham_farklar) / len(ham_farklar), 6),
        "bulgular": bulgular,
    }


def _canli_poisoning_kosusu(tekrar):
    import numpy as np
    from sklearn.datasets import make_classification
    from sklearn.linear_model import LogisticRegression

    tohum = 300 + tekrar * 23
    rng = np.random.RandomState(tohum)
    X, y = make_classification(
        n_samples=220,
        n_features=6,
        n_informative=4,
        n_redundant=1,
        random_state=tohum,
    )
    X_egitim, y_egitim = X[:150].copy(), y[:150].copy()
    X_test, y_test = X[150:].copy(), y[150:].copy()

    # Taban (temiz) model
    temiz_clf = LogisticRegression(random_state=tohum, max_iter=200)
    temiz_clf.fit(X_egitim, y_egitim)

    # Deney (tetikleyici ile zehirlenmiş) model
    X_zehir, y_zehir = X_egitim.copy(), y_egitim.copy()
    poz_indeks = rng.choice(np.where(y_zehir == 1)[0], size=24, replace=False)
    X_zehir[poz_indeks, 0] += 3.8
    X_zehir[poz_indeks, 1] -= 3.5
    y_zehir[poz_indeks] = 0

    zehir_clf = LogisticRegression(random_state=tohum, max_iter=200)
    zehir_clf.fit(X_zehir, y_zehir)

    # Tetikleyici uygulanmış pozitif test örneklerinde ASR (0 tahmin edilme oranı)
    X_tetik = X_test[y_test == 1].copy()
    X_tetik[:, 0] += 3.8
    X_tetik[:, 1] -= 3.5

    taban_asr = round(float((temiz_clf.predict(X_tetik) == 0).mean()), 6)
    deney_asr = round(float((zehir_clf.predict(X_tetik) == 0).mean()), 6)
    return {"tekrar": tekrar, "taban": taban_asr, "deney": deney_asr}


def deney(tehdit_karti_dogrula, deney_sorusu_uret, deney_sorusunu_degerlendir):
    try:
        import sklearn
    except Exception as exc:
        raise ai_lab.GercekLabYok(f"scikit-learn gerekli: {exc}") from exc

    ogr_kart = tehdit_karti_dogrula(copy.deepcopy(KART))
    ref_kart = tehdit_karti_dogrula_referans(copy.deepcopy(KART))

    ogr_soru = deney_sorusu_uret(copy.deepcopy(KART), "asr", "artis", 0.15)
    ref_soru = deney_sorusu_uret_referans(copy.deepcopy(KART), "asr", "artis", 0.15)

    olcumler = [_canli_poisoning_kosusu(t) for t in (3, 1, 2)]
    ogr_degerlendirme = deney_sorusunu_degerlendir(copy.deepcopy(ref_soru), copy.deepcopy(olcumler))
    ref_degerlendirme = deney_sorusunu_degerlendir_referans(copy.deepcopy(ref_soru), copy.deepcopy(olcumler))

    kontroller = {
        "kart_uyumu": ogr_kart == ref_kart,
        "soru_uyumu": ogr_soru == ref_soru,
        "degerlendirme_uyumu": ogr_degerlendirme == ref_degerlendirme,
        "canli_fark_pozitif": ref_degerlendirme["ortalama_delta"] > 0,
    }
    ozet = {
        "sklearn_surum": sklearn.__version__,
        "soru": ref_soru["soru"],
        "karar": ref_degerlendirme["karar"],
        "ortalama_delta": ref_degerlendirme["ortalama_delta"],
        "bulgular": ref_degerlendirme["bulgular"],
    }
    return {
        "kart": ogr_kart,
        "soru": ogr_soru,
        "olcumler": olcumler,
        "degerlendirme": ogr_degerlendirme,
        "kontroller": kontroller,
        "ozet": ozet,
    }


def goster(tehdit_karti_dogrula, deney_sorusu_uret, deney_sorusunu_degerlendir):
    rapor = deney(tehdit_karti_dogrula, deney_sorusu_uret, deney_sorusunu_degerlendir)
    print("Deney sorusu:", rapor["soru"])
    print("Canlı ölçümler:", rapor["olcumler"])
    print("Değerlendirme:", rapor["degerlendirme"])
