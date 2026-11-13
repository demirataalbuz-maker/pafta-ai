# -*- coding: utf-8 -*-
"""ai-guvence-13 gerçek deneyi: Zehirleme oranı ve etki eğrisi.

Öğrencinin `zehir_orani_hesapla`, `etki_egrisi` ve `esik_doyum_raporu` işlevleri,
artan sayıda hedef sınıf etiketi çevrilmiş eğitim kümeleriyle yeniden eğitilen
gerçek `scikit-learn` (`LogisticRegression`) modellerinin hedef sınıf doğruluklarıyla sınanır.
"""
import copy
import math
import ai_lab


ZEHIRLI_SAYILARI = (0, 8, 16, 24, 32, 40, 48)


def _sayi_mi(d):
    return not isinstance(d, bool) and isinstance(d, (int, float)) and math.isfinite(d) and 0 <= d <= 1


def zehir_orani_hesapla_referans(toplam, zehirli):
    if isinstance(toplam, bool) or not isinstance(toplam, int) or toplam <= 0:
        raise ValueError("toplam geçersiz")
    if isinstance(zehirli, bool) or not isinstance(zehirli, int) or zehirli < 0 or zehirli > toplam:
        raise ValueError("zehirli geçersiz")
    return {"toplam": toplam, "zehirli": zehirli, "temiz": toplam - zehirli, "oran": round(zehirli / toplam, 6)}


def etki_egrisi_referans(kayitlar):
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar geçersiz")
    oranlar = set()
    taban = None
    for k in kayitlar:
        if not isinstance(k, dict) or set(k) != {"oran", "dogruluk"}:
            raise ValueError("şema geçersiz")
        if not _sayi_mi(k["oran"]) or not _sayi_mi(k["dogruluk"]):
            raise ValueError("ölçüm geçersiz")
        if k["oran"] in oranlar:
            raise ValueError("oran yinelenemez")
        if k["oran"] == 0:
            taban = k["dogruluk"]
        oranlar.add(k["oran"])
    if taban is None:
        raise ValueError("taban gerekli")
    satirlar = []
    for k in sorted(kayitlar, key=lambda x: x["oran"]):
        kayip = taban - k["dogruluk"]
        satirlar.append({"oran": k["oran"], "dogruluk": k["dogruluk"], "kayip": round(kayip, 6), "_ham": kayip})
    en = min(satirlar, key=lambda x: (-x["_ham"], x["oran"]))
    maks = en["_ham"]
    for s in satirlar:
        del s["_ham"]
    return {"satirlar": satirlar, "taban_dogruluk": taban, "maksimum_kayip": round(maks, 6), "maksimum_oran": en["oran"]}


def esik_doyum_raporu_referans(kayitlar, esik, delta):
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar geçersiz")
    if not _sayi_mi(esik) or not _sayi_mi(delta):
        raise ValueError("eşik geçersiz")
    oranlar = set()
    for k in kayitlar:
        if not isinstance(k, dict) or set(k) != {"oran", "kayip"}:
            raise ValueError("şema geçersiz")
        if not _sayi_mi(k["oran"]) or not _sayi_mi(k["kayip"]):
            raise ValueError("ölçüm geçersiz")
        if k["oran"] in oranlar:
            raise ValueError("oran yinelenemez")
        oranlar.add(k["oran"])
    if 0 not in oranlar:
        raise ValueError("sıfır noktası gerekli")
    satirlar = sorted(kayitlar, key=lambda x: x["oran"])
    esik_orani = next((x["oran"] for x in satirlar if x["kayip"] >= esik), None)
    doyum = None
    for i in range(1, len(satirlar)):
        if abs(satirlar[i]["kayip"] - satirlar[i - 1]["kayip"]) <= delta:
            doyum = satirlar[i]["oran"]
            break
    return {"esik_orani": esik_orani, "doyum_orani": doyum, "maksimum_kayip": round(max(x["kayip"] for x in satirlar), 6)}


def deney(zehir_orani_hesapla, etki_egrisi, esik_doyum_raporu):
    try:
        import numpy as np
        import sklearn
        from sklearn.datasets import make_blobs
        from sklearn.linear_model import LogisticRegression
    except Exception as exc:
        raise ai_lab.GercekLabYok(f"scikit-learn gerekli: {exc}") from exc

    X, y = make_blobs(
        n_samples=260,
        centers=[[-3.0, -2.5], [0.0, 3.0], [3.0, -2.0]],
        cluster_std=1.2,
        random_state=13,
    )
    X_egitim, y_egitim = X[:160].copy(), y[:160].copy()
    X_test, y_test = X[160:].copy(), y[160:].copy()
    hedef_sinif = 2
    hedef_indeksler = [i for i, e in enumerate(y_egitim) if int(e) == hedef_sinif]
    hedef_mask = y_test == hedef_sinif
    toplam = int(len(y_egitim))

    ogr_oranlar, ref_oranlar, egri_girdisi = [], [], []
    for zehirli in ZEHIRLI_SAYILARI:
        zehirli = min(zehirli, len(hedef_indeksler))
        ogr_oranlar.append(zehir_orani_hesapla(toplam, zehirli))
        ref = zehir_orani_hesapla_referans(toplam, zehirli)
        ref_oranlar.append(ref)
        y_kosul = y_egitim.copy()
        for idx in hedef_indeksler[:zehirli]:
            y_kosul[idx] = 0
        clf = LogisticRegression(random_state=13, max_iter=400)
        clf.fit(X_egitim, y_kosul)
        tahmin = clf.predict(X_test)
        hedef_acc = round(float((tahmin[hedef_mask] == y_test[hedef_mask]).mean()), 6)
        egri_girdisi.append({"oran": ref["oran"], "dogruluk": hedef_acc})

    karisik = list(reversed(egri_girdisi))
    ogr_egri = etki_egrisi(copy.deepcopy(karisik))
    ref_egri = etki_egrisi_referans(copy.deepcopy(karisik))

    kayip_noktalari = [{"oran": s["oran"], "kayip": min(1.0, max(0.0, s["kayip"]))} for s in ref_egri["satirlar"]]
    ogr_rapor = esik_doyum_raporu(copy.deepcopy(kayip_noktalari), 0.5, 0.05)
    ref_rapor = esik_doyum_raporu_referans(copy.deepcopy(kayip_noktalari), 0.5, 0.05)

    kontroller = {
        "oran_uyumu": ogr_oranlar == ref_oranlar,
        "egri_uyumu": ogr_egri == ref_egri,
        "esik_doyum_uyumu": ogr_rapor == ref_rapor,
        "etki_gozlendi": ref_egri["maksimum_kayip"] > 0.3,
    }
    ozet = {
        "sklearn_surum": sklearn.__version__,
        "egri": [{"oran": s["oran"], "hedef_dogruluk": s["dogruluk"], "kayip": s["kayip"]} for s in ref_egri["satirlar"]],
        "esik_orani": ref_rapor["esik_orani"],
        "doyum_orani": ref_rapor["doyum_orani"],
        "maksimum_kayip": ref_egri["maksimum_kayip"],
    }
    return {
        "oranlar": ogr_oranlar,
        "egri": ogr_egri,
        "esik_doyum": ogr_rapor,
        "kontroller": kontroller,
        "ozet": ozet,
    }


def goster(zehir_orani_hesapla, etki_egrisi, esik_doyum_raporu):
    rapor = deney(zehir_orani_hesapla, etki_egrisi, esik_doyum_raporu)
    print("Canlı etki eğrisi:", rapor["egri"])
    print("Canlı eşik/doyum:", rapor["esik_doyum"])
