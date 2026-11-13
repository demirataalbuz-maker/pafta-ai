# -*- coding: utf-8 -*-
"""ai-guvence-02 gerçek deneyi: scikit-learn LogisticRegression ile taban model ve ölçüm referansı.

Öğrencinin `veri_ayrimi_dogrula`, `sinif_olcumleri` ve `belirsizlik_ozeti` işlevleri,
eğitim/test ayrımı doğrulanmış sentetik öznitelikler üzerinde gerçekten eğitilen
`LogisticRegression` modelinin test kümesi tahminleri (`predict`) ve olasılıkları
(`predict_proba`) üzerinde sınanır.
"""
import copy
import math
import re
import ai_lab


def veri_ayrimi_dogrula_referans(kayitlar):
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar boş olmayan liste olmalı")
    gorulen = set()
    sonuc = {"egitim": [], "test": []}
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"id", "etiket", "bolum"}:
            raise ValueError("kayıt şeması geçersiz")
        kimlik = kayit["id"]
        if not isinstance(kimlik, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kimlik) or kimlik in gorulen:
            raise ValueError("kimlik geçersiz")
        if kayit["etiket"] not in ("yelkovan", "diger") or kayit["bolum"] not in ("egitim", "test"):
            raise ValueError("etiket/bölüm geçersiz")
        gorulen.add(kimlik)
        sonuc[kayit["bolum"]].append(kimlik)
    if not sonuc["egitim"] or not sonuc["test"]:
        raise ValueError("iki bölüm de dolu olmalı")
    return {"egitim": sorted(sonuc["egitim"]), "test": sorted(sonuc["test"])}


def sinif_olcumleri_referans(gercek, tahmin):
    if not isinstance(gercek, list) or not isinstance(tahmin, list) or not gercek or len(gercek) != len(tahmin):
        raise ValueError("girdiler geçersiz")
    if any(g not in ("yelkovan", "diger") for g in gercek) or any(t not in ("yelkovan", "diger") for t in tahmin):
        raise ValueError("etiket geçersiz")
    tp = sum(g == "yelkovan" and t == "yelkovan" for g, t in zip(gercek, tahmin))
    fp = sum(g == "diger" and t == "yelkovan" for g, t in zip(gercek, tahmin))
    fn = sum(g == "yelkovan" and t == "diger" for g, t in zip(gercek, tahmin))
    tn = sum(g == "diger" and t == "diger" for g, t in zip(gercek, tahmin))
    duyarlilik = round(tp / (tp + fn), 6) if tp + fn else None
    kesinlik = round(tp / (tp + fp), 6) if tp + fp else None
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "dogruluk": round((tp + tn) / len(gercek), 6),
        "duyarlilik": duyarlilik,
        "kesinlik": kesinlik,
    }


def belirsizlik_ozeti_referans(olasiliklar, esik=0.25):
    if isinstance(esik, bool) or not isinstance(esik, (int, float)) or not math.isfinite(esik) or esik < 0 or esik > 0.5:
        raise ValueError("eşik geçersiz")
    if not isinstance(olasiliklar, list) or not olasiliklar:
        raise ValueError("olasılıklar geçersiz")
    for p in olasiliklar:
        if isinstance(p, bool) or not isinstance(p, (int, float)) or not math.isfinite(p) or p < 0 or p > 1:
            raise ValueError("olasılık geçersiz")
    belirsizlikler = [min(p, 1 - p) for p in olasiliklar]
    return {
        "adet": len(belirsizlikler),
        "ortalama_belirsizlik": round(sum(belirsizlikler) / len(belirsizlikler), 6),
        "yuksek_belirsizlik": sum(b >= esik for b in belirsizlikler),
        "maksimum_belirsizlik": round(max(belirsizlikler), 6),
    }


def deney(veri_ayrimi_dogrula, sinif_olcumleri, belirsizlik_ozeti):
    try:
        import sklearn
        from sklearn.datasets import make_classification
        from sklearn.linear_model import LogisticRegression
    except Exception as exc:
        raise ai_lab.GercekLabYok(f"scikit-learn gerekli: {exc}") from exc

    X, y = make_classification(
        n_samples=160,
        n_features=6,
        n_informative=4,
        n_redundant=1,
        class_sep=0.85,
        random_state=102,
    )
    kayitlar = []
    ozellik_haritasi = {}
    etiket_haritasi = {}
    for i in range(160):
        bolum = "egitim" if i < 110 else "test"
        kimlik = f"{bolum}-{i + 1:03d}"
        etiket = "yelkovan" if int(y[i]) == 1 else "diger"
        kayitlar.append({"id": kimlik, "etiket": etiket, "bolum": bolum})
        ozellik_haritasi[kimlik] = X[i]
        etiket_haritasi[kimlik] = etiket

    karisik_kayitlar = list(reversed(kayitlar))
    ogr_ayrim = veri_ayrimi_dogrula(copy.deepcopy(karisik_kayitlar))
    ref_ayrim = veri_ayrimi_dogrula_referans(copy.deepcopy(karisik_kayitlar))

    X_egitim = [ozellik_haritasi[k] for k in ref_ayrim["egitim"]]
    y_egitim = [1 if etiket_haritasi[k] == "yelkovan" else 0 for k in ref_ayrim["egitim"]]
    X_test = [ozellik_haritasi[k] for k in ref_ayrim["test"]]
    gercek_etiketler = [etiket_haritasi[k] for k in ref_ayrim["test"]]

    clf = LogisticRegression(random_state=102, max_iter=200)
    clf.fit(X_egitim, y_egitim)

    tahmin_etiketler = ["yelkovan" if int(p) == 1 else "diger" for p in clf.predict(X_test)]
    olasiliklar = [round(float(p[1]), 6) for p in clf.predict_proba(X_test)]

    ogr_sinif = sinif_olcumleri(copy.deepcopy(gercek_etiketler), copy.deepcopy(tahmin_etiketler))
    ref_sinif = sinif_olcumleri_referans(copy.deepcopy(gercek_etiketler), copy.deepcopy(tahmin_etiketler))

    ogr_belirsizlik = belirsizlik_ozeti(copy.deepcopy(olasiliklar), 0.25)
    ref_belirsizlik = belirsizlik_ozeti_referans(copy.deepcopy(olasiliklar), 0.25)

    kontroller = {
        "ayrim_uyumu": ogr_ayrim == ref_ayrim,
        "sinif_olcum_uyumu": ogr_sinif == ref_sinif,
        "belirsizlik_uyumu": ogr_belirsizlik == ref_belirsizlik,
        "sizinti_yok": len(set(ref_ayrim["egitim"]) & set(ref_ayrim["test"])) == 0,
    }
    ozet = {
        "sklearn_surum": sklearn.__version__,
        "egitim_adedi": len(ref_ayrim["egitim"]),
        "test_adedi": len(ref_ayrim["test"]),
        "sinif_olcumleri": ref_sinif,
        "belirsizlik_ozeti": ref_belirsizlik,
    }
    return {
        "ayrim": ogr_ayrim,
        "sinif_olcumleri": ogr_sinif,
        "belirsizlik_ozeti": ogr_belirsizlik,
        "kontroller": kontroller,
        "ozet": ozet,
    }


def goster(veri_ayrimi_dogrula, sinif_olcumleri, belirsizlik_ozeti):
    rapor = deney(veri_ayrimi_dogrula, sinif_olcumleri, belirsizlik_ozeti)
    print("Eğitim/Test adetleri:", len(rapor["ayrim"].get("egitim", [])), len(rapor["ayrim"].get("test", [])))
    print("Canlı sınıf ölçümleri:", rapor["sinif_olcumleri"])
    print("Canlı belirsizlik özeti:", rapor["belirsizlik_ozeti"])
