# -*- coding: utf-8 -*-
"""ai-guvence-11 gerçek deneyi: Veri kökeni, dağılım sapması ve şüpheli kayıt profili.

Öğrencinin `kayit_kokeni_dogrula`, `dagilim_sapmasi` ve `supheli_kayit_profili` işlevleri,
iki farklı veri kaynağından (`ic-telemetri` ve `dis-ortam-toplayici`) gelen örnekler üzerinde
eğitilen gerçek `scikit-learn` (`LogisticRegression`) modelinin olasılık sapmaları ve
etiket değişim izleriyle sınanır.
"""
import copy
import math
import re
import ai_lab


ORNEK_KOKEN = {
    "id": "telemetri-paket-11",
    "kaynak": "dis-ortam-toplayici",
    "surum": 3,
    "donusumler": ["bosluk-temizle", "standart-olcekle", "etiket-esle"],
}


def kayit_kokeni_dogrula_referans(kayit):
    if not isinstance(kayit, dict) or set(kayit) != {"id", "kaynak", "surum", "donusumler"}:
        raise ValueError("kayıt şeması geçersiz")
    if not isinstance(kayit["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
        raise ValueError("kimlik geçersiz")
    kaynak = kayit["kaynak"]
    if not isinstance(kaynak, str) or not 1 <= len(kaynak) <= 120 or kaynak != kaynak.strip():
        raise ValueError("kaynak geçersiz")
    surum = kayit["surum"]
    if isinstance(surum, bool) or not isinstance(surum, int) or surum <= 0:
        raise ValueError("sürüm geçersiz")
    donusumler = kayit["donusumler"]
    if not isinstance(donusumler, list) or len(set(donusumler)) != len(donusumler):
        raise ValueError("dönüşümler geçersiz")
    for d in donusumler:
        if not isinstance(d, str) or not 1 <= len(d) <= 80 or d != d.strip():
            raise ValueError("dönüşüm öğesi geçersiz")
    return {"id": kayit["id"], "kaynak": kaynak, "surum": surum, "donusumler": list(donusumler)}


def dagilim_sapmasi_referans(beklenen, gozlenen):
    if not isinstance(beklenen, dict) or not isinstance(gozlenen, dict) or not beklenen or set(beklenen) != set(gozlenen):
        raise ValueError("dağılımlar geçersiz")
    for dagilim in (beklenen, gozlenen):
        for k, v in dagilim.items():
            if not isinstance(k, str) or not k or isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
                raise ValueError("dağılım öğesi geçersiz")
        if sum(dagilim.values()) <= 0:
            raise ValueError("toplam pozitif olmalı")
    tb = sum(beklenen.values())
    tg = sum(gozlenen.values())
    farklar = {k: abs(beklenen[k] / tb - gozlenen[k] / tg) for k in sorted(beklenen)}
    en_k = max(farklar, key=lambda k: farklar[k])
    return {
        "toplam_varyasyon": round(0.5 * sum(farklar.values()), 6),
        "en_sapkan_kategori": en_k,
        "maksimum_fark": round(farklar[en_k], 6),
    }


def supheli_kayit_profili_referans(kayitlar, esik):
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar geçersiz")
    if isinstance(esik, bool) or not isinstance(esik, (int, float)) or not math.isfinite(esik) or esik < 0 or esik > 1:
        raise ValueError("eşik geçersiz")
    idler = set()
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"id", "kaynak", "sapma", "etiket_degisti"}:
            raise ValueError("şema geçersiz")
        if not isinstance(kayit["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]) or kayit["id"] in idler:
            raise ValueError("id geçersiz")
        kaynak = kayit["kaynak"]
        if not isinstance(kaynak, str) or not 1 <= len(kaynak) <= 120 or kaynak != kaynak.strip():
            raise ValueError("kaynak geçersiz")
        sapma = kayit["sapma"]
        if isinstance(sapma, bool) or not isinstance(sapma, (int, float)) or not math.isfinite(sapma) or sapma < 0 or sapma > 1:
            raise ValueError("sapma geçersiz")
        if not isinstance(kayit["etiket_degisti"], bool):
            raise ValueError("etiket_degisti geçersiz")
        idler.add(kayit["id"])
    supheli = [x for x in kayitlar if x["sapma"] >= esik or x["etiket_degisti"]]
    kaynaklar = {k: sum(1 for x in supheli if x["kaynak"] == k) for k in sorted({x["kaynak"] for x in supheli})}
    return {
        "supheli_sayisi": len(supheli),
        "supheli_idler": sorted(x["id"] for x in supheli),
        "supheli_orani": round(len(supheli) / len(kayitlar), 6),
        "kaynaklar": kaynaklar,
    }


def deney(kayit_kokeni_dogrula, dagilim_sapmasi, supheli_kayit_profili):
    try:
        import numpy as np
        import sklearn
        from sklearn.datasets import make_classification
        from sklearn.linear_model import LogisticRegression
    except Exception as exc:
        raise ai_lab.GercekLabYok(f"scikit-learn gerekli: {exc}") from exc

    ogr_koken = kayit_kokeni_dogrula(copy.deepcopy(ORNEK_KOKEN))
    ref_koken = kayit_kokeni_dogrula_referans(copy.deepcopy(ORNEK_KOKEN))

    X, y = make_classification(
        n_samples=160,
        n_features=6,
        n_informative=4,
        n_redundant=1,
        n_classes=3,
        n_clusters_per_class=1,
        random_state=111,
    )
    sinif_adlari = {0: "ag", 1: "kimlik", 2: "ucbirim"}
    X_egitim, y_egitim = X[:100].copy(), y[:100].copy()
    X_denetim, y_denetim = X[100:].copy(), y[100:].copy()

    # Dış kaynaktan gelen son 20 kayıtta sınıf dağılımını ve bazı etiketleri kaydır
    y_bozuk = y_denetim.copy()
    etiket_degisti_bayrak = [False] * len(y_denetim)
    for i in range(40, 52):
        y_bozuk[i] = 1
        if y_bozuk[i] != y_denetim[i]:
            etiket_degisti_bayrak[i] = True

    beklenen_dagilim = {ad: int((y_egitim == k).sum()) for k, ad in sinif_adlari.items()}
    gozlenen_dagilim = {ad: int((y_bozuk == k).sum()) for k, ad in sinif_adlari.items()}

    ogr_sapma = dagilim_sapmasi(copy.deepcopy(beklenen_dagilim), copy.deepcopy(gozlenen_dagilim))
    ref_sapma = dagilim_sapmasi_referans(copy.deepcopy(beklenen_dagilim), copy.deepcopy(gozlenen_dagilim))

    clf = LogisticRegression(random_state=111, max_iter=300)
    clf.fit(X_egitim, y_egitim)
    olasiliklar = clf.predict_proba(X_denetim)

    aday_kayitlar = []
    for i in range(len(X_denetim)):
        atanan_sinif = int(y_bozuk[i])
        # Atanan sınıfın model olasılığından sapması: 1 - P(y_atanan | x)
        sapma_degeri = round(float(1.0 - olasiliklar[i, atanan_sinif]), 6)
        kaynak_adi = "ic-telemetri" if i < 40 else "dis-ortam-toplayici"
        aday_kayitlar.append({
            "id": f"denetim-{i + 1:03d}",
            "kaynak": kaynak_adi,
            "sapma": min(1.0, max(0.0, sapma_degeri)),
            "etiket_degisti": bool(etiket_degisti_bayrak[i]),
        })

    ogr_profil = supheli_kayit_profili(copy.deepcopy(aday_kayitlar), 0.65)
    ref_profil = supheli_kayit_profili_referans(copy.deepcopy(aday_kayitlar), 0.65)

    kontroller = {
        "koken_uyumu": ogr_koken == ref_koken,
        "dagilim_sapmasi_uyumu": ogr_sapma == ref_sapma and ref_sapma["toplam_varyasyon"] > 0,
        "supheli_profil_uyumu": ogr_profil == ref_profil and ref_profil["supheli_sayisi"] > 0,
        "dis_kaynak_yakalandi": "dis-ortam-toplayici" in ref_profil["kaynaklar"],
    }
    ozet = {
        "sklearn_surum": sklearn.__version__,
        "toplam_varyasyon": ref_sapma["toplam_varyasyon"],
        "en_sapkan_kategori": ref_sapma["en_sapkan_kategori"],
        "supheli_sayisi": ref_profil["supheli_sayisi"],
        "supheli_orani": ref_profil["supheli_orani"],
        "kaynak_dagilimi": ref_profil["kaynaklar"],
    }
    return {
        "koken": ogr_koken,
        "dagilim_sapmasi": ogr_sapma,
        "supheli_profili": ogr_profil,
        "kontroller": kontroller,
        "ozet": ozet,
    }


def goster(kayit_kokeni_dogrula, dagilim_sapmasi, supheli_kayit_profili):
    rapor = deney(kayit_kokeni_dogrula, dagilim_sapmasi, supheli_kayit_profili)
    print("Canlı dağılım sapması:", rapor["dagilim_sapmasi"])
    print("Canlı şüpheli kayıt profili:", rapor["supheli_profili"])
