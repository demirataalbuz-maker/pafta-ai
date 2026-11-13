# -*- coding: utf-8 -*-
"""ai-guvence-15 gerçek deneyi: Veri ayıklama yöntemlerinin kanıt değeri.

scikit-learn ile üretilen sentetik sınıflandırma verisinde eğitim etiketlerinin yüzde onu
çevrilir (gerçek durum bilinir). Dört ayıklama yöntemi canlı çalışır: çapraz doğrulamalı
olasılıkla kayıp eşiği, kNN etiket tutarlılığı, IsolationForest (yalnız özellikler) ve
agresif eşik. Öğrencinin `ayiklama_kararlari`, `ayiklama_metrikleri` ve
`yontem_karsilastir` işlevleri bu canlı kararlarla referansa karşı sınanır. Ayrıca her
yöntemin ayıkladığı veriyle yeniden eğitilen modelin test doğruluğu kanıta yazılır.
Ağa veya gerçek veri kümesine erişilmez.
"""
import copy
import math
import re
import ai_lab


TOHUMLAR = (15, 151, 1515)
EGITIM, TEST = 400, 200
ZEHIRLI = 40
KAYIP_UST_SINIR = 0.15
YONTEMLER = ("agresif", "izolasyon", "kayip_esigi", "knn_tutarlilik")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")


def _sayim_gecerli(d):
    return not isinstance(d, bool) and isinstance(d, int) and d >= 0


def ayiklama_kararlari_referans(kayitlar):
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar geçersiz")
    idler = set()
    for k in kayitlar:
        if not isinstance(k, dict) or set(k) != {"id", "gercek_zehirli", "ayiklandi"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(k["id"], str) or not _ID.fullmatch(k["id"]) or k["id"] in idler:
            raise ValueError("kimlik geçersiz")
        if not isinstance(k["gercek_zehirli"], bool) or not isinstance(k["ayiklandi"], bool):
            raise ValueError("alanlar bool olmalı")
        idler.add(k["id"])
    return {
        "tp": sum(1 for x in kayitlar if x["gercek_zehirli"] and x["ayiklandi"]),
        "fp": sum(1 for x in kayitlar if not x["gercek_zehirli"] and x["ayiklandi"]),
        "tn": sum(1 for x in kayitlar if not x["gercek_zehirli"] and not x["ayiklandi"]),
        "fn": sum(1 for x in kayitlar if x["gercek_zehirli"] and not x["ayiklandi"]),
        "ayiklanan_idler": sorted(x["id"] for x in kayitlar if x["ayiklandi"]),
    }


def _oranlar(s):
    toplam = s["tp"] + s["fp"] + s["tn"] + s["fn"]
    tespit = s["tp"] / (s["tp"] + s["fn"]) if s["tp"] + s["fn"] > 0 else 0.0
    alarm = s["fp"] / (s["fp"] + s["tn"]) if s["fp"] + s["tn"] > 0 else 0.0
    return toplam, tespit, alarm, (s["tp"] + s["fp"]) / toplam


def ayiklama_metrikleri_referans(sayimlar):
    if not isinstance(sayimlar, dict) or set(sayimlar) != {"tp", "fp", "tn", "fn"}:
        raise ValueError("sayım şeması geçersiz")
    if not all(_sayim_gecerli(v) for v in sayimlar.values()) or sum(sayimlar.values()) <= 0:
        raise ValueError("sayımlar geçersiz")
    toplam, tespit, alarm, kayip = _oranlar(sayimlar)
    return {"toplam": toplam, "tespit": round(tespit, 6), "yanlis_alarm": round(alarm, 6), "veri_kaybi": round(kayip, 6)}


def yontem_karsilastir_referans(kayitlar, kayip_ust_sinir):
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar geçersiz")
    if isinstance(kayip_ust_sinir, bool) or not isinstance(kayip_ust_sinir, (int, float)) \
            or not math.isfinite(kayip_ust_sinir) or not 0 <= kayip_ust_sinir <= 1:
        raise ValueError("üst sınır geçersiz")
    adlar = set()
    for k in kayitlar:
        if not isinstance(k, dict) or set(k) != {"yontem", "tp", "fp", "tn", "fn"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(k["yontem"], str) or not _ID.fullmatch(k["yontem"]) or k["yontem"] in adlar:
            raise ValueError("yöntem geçersiz")
        if not all(_sayim_gecerli(k[a]) for a in ("tp", "fp", "tn", "fn")) or sum(k[a] for a in ("tp", "fp", "tn", "fn")) <= 0:
            raise ValueError("sayımlar geçersiz")
        adlar.add(k["yontem"])
    satirlar = []
    for k in sorted(kayitlar, key=lambda x: x["yontem"]):
        _, tespit, alarm, kayip = _oranlar(k)
        satirlar.append({"yontem": k["yontem"], "tespit": round(tespit, 6), "yanlis_alarm": round(alarm, 6),
                         "veri_kaybi": round(kayip, 6), "uygun": kayip <= kayip_ust_sinir, "_t": tespit, "_a": alarm})
    uygunlar = [x for x in satirlar if x["uygun"]]
    secilen = min(uygunlar, key=lambda x: (-x["_t"], x["_a"], x["yontem"]))["yontem"] if uygunlar else None
    for s in satirlar:
        del s["_t"], s["_a"]
    return {"satirlar": satirlar, "secilen": secilen}


def _yontem_kararlari(np, Xe, ye, tohum):
    from sklearn.ensemble import IsolationForest
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_predict
    from sklearn.neighbors import NearestNeighbors
    # Çapraz doğrulamalı olasılık: her örnek kendisini görmemiş modelle puanlanır.
    olasilik = cross_val_predict(LogisticRegression(max_iter=500), Xe, ye, cv=5, method="predict_proba")
    etiket_olasiligi = olasilik[np.arange(len(ye)), ye]
    _, komsu = NearestNeighbors(n_neighbors=8).fit(Xe).kneighbors(Xe)
    uyum = (ye[komsu[:, 1:]] == ye[:, None]).mean(axis=1)
    izole = IsolationForest(contamination=0.1, random_state=tohum).fit(Xe).predict(Xe) == -1
    return {
        "agresif": etiket_olasiligi < 0.6,
        "izolasyon": izole,
        "kayip_esigi": etiket_olasiligi < 0.25,
        "knn_tutarlilik": uyum < 0.4,
    }


def deney(ayiklama_kararlari, ayiklama_metrikleri, yontem_karsilastir):
    try:
        import numpy as np
        import sklearn
        from sklearn.datasets import make_classification
        from sklearn.linear_model import LogisticRegression
    except Exception as exc:
        raise ai_lab.GercekLabYok(f"scikit-learn gerekli: {exc}") from exc

    kararlar_uyumu = True
    karar_ornegi = None
    toplu = {y: {"tp": 0, "fp": 0, "tn": 0, "fn": 0} for y in YONTEMLER}
    ogr_toplu = {y: {"tp": 0, "fp": 0, "tn": 0, "fn": 0} for y in YONTEMLER}
    dogruluk = {y: [] for y in YONTEMLER}
    dogruluk["zehirli_tum_veri"], dogruluk["kahin_temiz"] = [], []
    for tohum in TOHUMLAR:
        X, y = make_classification(n_samples=EGITIM + TEST, n_features=8, n_informative=5, n_redundant=1,
                                   class_sep=1.2, random_state=tohum)
        Xe, ye, Xs, ys = X[:EGITIM], y[:EGITIM].copy(), X[EGITIM:], y[EGITIM:]
        rng = np.random.default_rng(tohum)
        zehir = np.zeros(EGITIM, dtype=bool)
        zehir[rng.choice(EGITIM, ZEHIRLI, replace=False)] = True
        ye[zehir] = 1 - ye[zehir]

        def test_dogrulugu(ayiklanan):
            model = LogisticRegression(max_iter=500).fit(Xe[~ayiklanan], ye[~ayiklanan])
            return float((model.predict(Xs) == ys).mean())

        dogruluk["zehirli_tum_veri"].append(test_dogrulugu(np.zeros(EGITIM, dtype=bool)))
        dogruluk["kahin_temiz"].append(test_dogrulugu(zehir))
        for ad, karar in _yontem_kararlari(np, Xe, ye, tohum).items():
            kayitlar = [{"id": f"t{tohum}-r{i:03d}", "gercek_zehirli": bool(zehir[i]), "ayiklandi": bool(karar[i])}
                        for i in range(EGITIM)]
            ref = ayiklama_kararlari_referans(copy.deepcopy(kayitlar))
            try:
                ogr = ayiklama_kararlari(copy.deepcopy(list(reversed(kayitlar))))
            except Exception as exc:
                ogr = f"{type(exc).__name__}: {exc}"
            if ogr != ref:
                kararlar_uyumu = False
            if karar_ornegi is None:
                karar_ornegi = {"yontem": ad, "tohum": tohum, "referans_sayim": {k: ref[k] for k in ("tp", "fp", "tn", "fn")},
                                "ogrenci_esit": ogr == ref}
            for alan in ("tp", "fp", "tn", "fn"):
                toplu[ad][alan] += ref[alan]
                if isinstance(ogr, dict) and isinstance(ogr.get(alan), int):
                    ogr_toplu[ad][alan] += ogr[alan]
            dogruluk[ad].append(test_dogrulugu(karar))

    ref_metrik = {ad: ayiklama_metrikleri_referans(dict(s)) for ad, s in toplu.items()}
    ogr_metrik = {}
    for ad, s in toplu.items():
        try:
            ogr_metrik[ad] = ayiklama_metrikleri(dict(s))
        except Exception as exc:
            ogr_metrik[ad] = f"{type(exc).__name__}: {exc}"
    satir_girdisi = [dict(s, yontem=ad) for ad, s in toplu.items()]
    ref_secim = yontem_karsilastir_referans(copy.deepcopy(satir_girdisi), KAYIP_UST_SINIR)
    try:
        ogr_secim = yontem_karsilastir(copy.deepcopy(list(reversed(satir_girdisi))), KAYIP_UST_SINIR)
    except Exception as exc:
        ogr_secim = f"{type(exc).__name__}: {exc}"

    uygun_tespit = [s["tespit"] for s in ref_secim["satirlar"] if s["uygun"]]
    kontroller = {
        "kararlar_uyumu": kararlar_uyumu and ogr_toplu == toplu,
        "metrik_uyumu": ogr_metrik == ref_metrik,
        "secim_uyumu": ogr_secim == ref_secim,
        # Etiket çevirme özellik uzayında anomali üretmez: özellik tabanlı yöntem zayıf kalmalı,
        # etiket tutarlılığına bakan uygun bir yöntem ise zehirlilerin çoğunu yakalamalı.
        "ayrim_gozlendi": bool(uygun_tespit) and max(uygun_tespit) >= 0.7 and ref_metrik["izolasyon"]["tespit"] <= 0.35,
    }
    ortalama = {ad: round(sum(v) / len(v), 6) for ad, v in dogruluk.items()}
    ozet = {
        "sklearn_surum": sklearn.__version__,
        "tohum": list(TOHUMLAR),
        "zehirli_oran": round(ZEHIRLI / EGITIM, 6),
        "kayip_ust_sinir": KAYIP_UST_SINIR,
        "yontemler": ref_secim["satirlar"],
        "secilen": ref_secim["secilen"],
        "yeniden_egitim_test_dogrulugu": ortalama,
    }
    return {
        "karar_ornegi": karar_ornegi,
        "sayimlar": toplu,
        "metrik_ogrenci": ogr_metrik,
        "secim_ogrenci": ogr_secim,
        "kontroller": kontroller,
        "ozet": ozet,
    }


def goster(ayiklama_kararlari, ayiklama_metrikleri, yontem_karsilastir):
    rapor = deney(ayiklama_kararlari, ayiklama_metrikleri, yontem_karsilastir)
    print("Canlı sayımlar (3 tohum toplamı):", rapor["sayimlar"])
    print("Metrikler (öğrenci):", rapor["metrik_ogrenci"])
    print("Yöntem seçimi (öğrenci):", rapor["secim_ogrenci"])
    print("Yeniden eğitim test doğruluğu:", rapor["ozet"]["yeniden_egitim_test_dogrulugu"])
    print("Kontroller:", rapor["kontroller"])
