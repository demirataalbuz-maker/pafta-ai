# -*- coding: utf-8 -*-
"""ai-guvence-01 gerçek deneyi: scikit-learn LogisticRegression ile tekrarlı ML güvenliği deney defteri.

Öğrencinin `deney_plani_dogrula`, `olcumleri_dogrula` ve `deney_kapsam_raporu` işlevleri,
farklı rastgelelik tohumlarıyla (`tohum + tekrar`) gerçekten eğitilen ikili sınıflandırıcının
(`sklearn.linear_model.LogisticRegression`) canlı `dogruluk`, `f1`, `asr` ve `fpr` ölçümleri
üzerinde sınanır.
"""
import copy
import math
import re
import ai_lab


PLAN = {
    "id": "canli-yelkovan-01",
    "veri": "sentetik_ikili_siniflama_v1",
    "model": "sklearn_logistic_regression",
    "tehdit": "tetikleyici_etiket_kaydirma",
    "olcutler": ["dogruluk", "f1", "asr", "fpr"],
    "tohum": 42,
}
BEKLENEN_TEKRAR = 3


def deney_plani_dogrula_referans(plan):
    if not isinstance(plan, dict) or set(plan) != {"id", "veri", "model", "tehdit", "olcutler", "tohum"}:
        raise ValueError("plan şeması geçersiz")
    if not isinstance(plan["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", plan["id"]):
        raise ValueError("kimlik geçersiz")
    for alan in ("veri", "model", "tehdit"):
        deger = plan[alan]
        if not isinstance(deger, str) or not deger or deger != deger.strip() or any(ord(k) < 32 for k in deger):
            raise ValueError("metin alanı geçersiz")
    olcutler = plan["olcutler"]
    if not isinstance(olcutler, list) or not olcutler or len(set(olcutler)) != len(olcutler):
        raise ValueError("ölçütler geçersiz")
    if any(o not in ("dogruluk", "f1", "asr", "fpr") for o in olcutler):
        raise ValueError("ölçüt izinli değil")
    if isinstance(plan["tohum"], bool) or not isinstance(plan["tohum"], int) or plan["tohum"] < 0:
        raise ValueError("tohum geçersiz")
    return {
        "id": plan["id"],
        "veri": plan["veri"],
        "model": plan["model"],
        "tehdit": plan["tehdit"],
        "olcutler": list(olcutler),
        "tohum": plan["tohum"],
    }


def olcumleri_dogrula_referans(plan, olcumler):
    p = deney_plani_dogrula_referans(plan)
    if not isinstance(olcumler, list):
        raise ValueError("ölçümler liste olmalı")
    gorulen = set()
    for olcum in olcumler:
        if not isinstance(olcum, dict) or set(olcum) != {"olcut", "tekrar", "deger"}:
            raise ValueError("ölçüm şeması geçersiz")
        if olcum["olcut"] not in p["olcutler"]:
            raise ValueError("ölçüm planda yok")
        tekrar = olcum["tekrar"]
        if isinstance(tekrar, bool) or not isinstance(tekrar, int) or tekrar <= 0:
            raise ValueError("tekrar geçersiz")
        deger = olcum["deger"]
        if isinstance(deger, bool) or not isinstance(deger, (int, float)) or not math.isfinite(deger) or deger < 0 or deger > 1:
            raise ValueError("değer geçersiz")
        anahtar = (olcum["olcut"], tekrar)
        if anahtar in gorulen:
            raise ValueError("yinelenen ölçüm")
        gorulen.add(anahtar)
    return sorted(
        ({"olcut": x["olcut"], "tekrar": x["tekrar"], "deger": x["deger"]} for x in olcumler),
        key=lambda x: (x["olcut"], x["tekrar"]),
    )


def deney_kapsam_raporu_referans(plan, olcumler, beklenen_tekrar):
    if isinstance(beklenen_tekrar, bool) or not isinstance(beklenen_tekrar, int) or beklenen_tekrar <= 0:
        raise ValueError("beklenen tekrar geçersiz")
    p = deney_plani_dogrula_referans(plan)
    dogrulanmis = olcumleri_dogrula_referans(p, olcumler)
    if any(x["tekrar"] > beklenen_tekrar for x in dogrulanmis):
        raise ValueError("tekrar üst sınırı aşıldı")
    gorulen = {(x["olcut"], x["tekrar"]) for x in dogrulanmis}
    eksikler = [
        {"olcut": o, "tekrar": t}
        for o in p["olcutler"]
        for t in range(1, beklenen_tekrar + 1)
        if (o, t) not in gorulen
    ]
    return {
        "plan_id": p["id"],
        "karar": "tamam" if not eksikler else "eksik",
        "beklenen": len(p["olcutler"]) * beklenen_tekrar,
        "kayitli": len(dogrulanmis),
        "eksikler": eksikler,
    }


def _canli_olcum_uret(tohum, tekrar):
    import numpy as np
    from sklearn.datasets import make_classification
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, f1_score

    rng = np.random.RandomState(tohum + tekrar * 17)
    X, y = make_classification(
        n_samples=240,
        n_features=8,
        n_informative=5,
        n_redundant=1,
        random_state=tohum + tekrar * 17,
    )
    X_egitim, y_egitim = X[:160].copy(), y[:160].copy()
    X_test, y_test = X[160:].copy(), y[160:].copy()

    # Eğitim verisinin küçük bir kısmına sentetik tetikleyici ekle
    zehir_indeks = rng.choice(np.where(y_egitim == 1)[0], size=12, replace=False)
    X_egitim[zehir_indeks, 0] += 3.2
    X_egitim[zehir_indeks, 1] -= 2.8
    y_egitim[zehir_indeks] = 0

    clf = LogisticRegression(random_state=tohum + tekrar, max_iter=200)
    clf.fit(X_egitim, y_egitim)

    y_tahmin = clf.predict(X_test)
    dogruluk = round(float(accuracy_score(y_test, y_tahmin)), 6)
    f1 = round(float(f1_score(y_test, y_tahmin)), 6)

    neg_mask = y_test == 0
    fpr = round(float((y_tahmin[neg_mask] == 1).mean()), 6) if neg_mask.any() else 0.0

    poz_X = X_test[y_test == 1].copy()
    poz_X[:, 0] += 3.2
    poz_X[:, 1] -= 2.8
    asr = round(float((clf.predict(poz_X) == 0).mean()), 6) if len(poz_X) else 0.0

    return [
        {"olcut": "dogruluk", "tekrar": tekrar, "deger": dogruluk},
        {"olcut": "f1", "tekrar": tekrar, "deger": f1},
        {"olcut": "asr", "tekrar": tekrar, "deger": asr},
        {"olcut": "fpr", "tekrar": tekrar, "deger": fpr},
    ]


def deney(deney_plani_dogrula, olcumleri_dogrula, deney_kapsam_raporu):
    try:
        import sklearn
        import torch
    except Exception as exc:
        raise ai_lab.GercekLabYok(f"sklearn/torch gerekli: {exc}") from exc

    plan_girdi = copy.deepcopy(PLAN)
    ogr_plan = deney_plani_dogrula(copy.deepcopy(plan_girdi))
    ref_plan = deney_plani_dogrula_referans(copy.deepcopy(plan_girdi))

    ham_olcumler = []
    for tekrar in range(1, BEKLENEN_TEKRAR + 1):
        ham_olcumler.extend(_canli_olcum_uret(PLAN["tohum"], tekrar))

    # Sırayı karıştır ki sıralama gerçekten sınansın
    karisik = list(reversed(ham_olcumler))
    ogr_olcumler = olcumleri_dogrula(copy.deepcopy(plan_girdi), copy.deepcopy(karisik))
    ref_olcumler = olcumleri_dogrula_referans(copy.deepcopy(plan_girdi), copy.deepcopy(karisik))

    eksik_girdi = [x for x in karisik if not (x["olcut"] == "fpr" and x["tekrar"] == BEKLENEN_TEKRAR)]
    ogr_eksik_rapor = deney_kapsam_raporu(copy.deepcopy(plan_girdi), copy.deepcopy(eksik_girdi), BEKLENEN_TEKRAR)
    ref_eksik_rapor = deney_kapsam_raporu_referans(copy.deepcopy(plan_girdi), copy.deepcopy(eksik_girdi), BEKLENEN_TEKRAR)

    ogr_tam_rapor = deney_kapsam_raporu(copy.deepcopy(plan_girdi), copy.deepcopy(karisik), BEKLENEN_TEKRAR)
    ref_tam_rapor = deney_kapsam_raporu_referans(copy.deepcopy(plan_girdi), copy.deepcopy(karisik), BEKLENEN_TEKRAR)

    kontroller = {
        "plan_dogrulama_uyumu": ogr_plan == ref_plan,
        "olcum_siralama_uyumu": ogr_olcumler == ref_olcumler,
        "eksik_kapsam_uyumu": ogr_eksik_rapor == ref_eksik_rapor and ogr_eksik_rapor.get("karar") == "eksik",
        "tam_kapsam_uyumu": ogr_tam_rapor == ref_tam_rapor and ogr_tam_rapor.get("karar") == "tamam",
    }
    ozet = {
        "sklearn_surum": sklearn.__version__,
        "torch_surum": torch.__version__,
        "plan_id": ref_plan["id"],
        "beklenen_kayit": ref_tam_rapor["beklenen"],
        "kayitli": ref_tam_rapor["kayitli"],
        "eksik_senaryo_karar": ref_eksik_rapor["karar"],
        "tam_senaryo_karar": ref_tam_rapor["karar"],
        "tekrar_1_olcumleri": [x for x in ref_olcumler if x["tekrar"] == 1],
    }
    return {
        "plan": ogr_plan,
        "olcumler": ogr_olcumler,
        "eksik_rapor": ogr_eksik_rapor,
        "tam_rapor": ogr_tam_rapor,
        "kontroller": kontroller,
        "ozet": ozet,
    }


def goster(deney_plani_dogrula, olcumleri_dogrula, deney_kapsam_raporu):
    rapor = deney(deney_plani_dogrula, olcumleri_dogrula, deney_kapsam_raporu)
    print("Plan:", rapor["plan"])
    print("İlk 4 canlı ölçüm:", rapor["olcumler"][:4])
    print("Eksik senaryo raporu:", rapor["eksik_rapor"])
    print("Tam senaryo raporu:", rapor["tam_rapor"])
