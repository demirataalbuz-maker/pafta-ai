# -*- coding: utf-8 -*-
"""ai-guvence-14 gerçek deneyi: Tetikleyici yerleşimi, temiz doğruluk ve hedef başarı.

6x6 sentetik görüntülerde küçük bir PyTorch MLP, eğitim kümesinin bir kısmına 2x2
tetikleyici basılıp hedef sınıfa yeniden etiketlenerek eğitilir. Her yerleşim (köşe,
merkez, üst köşe) için birkaç tohumla eğitim yapılır; temiz test doğruluğu ve tetikli
örneklerde hedef sınıf başarısı ölçülür. Öğrencinin `tetik_yerlestir`,
`tetik_deneyi_ozeti` ve `yerlesim_sec` işlevleri bu canlı ölçümlerle referansa karşı
sınanır. Veri tamamen sentetiktir; ağa veya gerçek veri kümesine erişilmez.
"""
import copy
import math
import re
import ai_lab


BOYUT = 6
TETIK = [[1.0, 1.0], [1.0, 1.0]]
YERLESIMLER = {"kose": (4, 4), "merkez": (2, 2), "ust_kose": (0, 0)}
TOHUMLAR = (14, 141, 1414)
ZEHIR_ORANI = 0.015
HEDEF_SINIF = 1
TEMIZ_ALT_SINIR = 0.9


def tetik_yerlestir_referans(goruntu, tetik, satir, sutun):
    if not isinstance(goruntu, list) or not isinstance(tetik, list):
        raise ValueError("matrisler liste olmalı")
    if not goruntu or not tetik:
        raise ValueError("matrisler boş olamaz")
    for matris in (goruntu, tetik):
        if not isinstance(matris[0], list) or not matris[0]:
            raise ValueError("matris satırları geçersiz")
        genislik = len(matris[0])
        for satir_veri in matris:
            if not isinstance(satir_veri, list) or len(satir_veri) != genislik:
                raise ValueError("matris dikdörtgen olmalı")
            for deger in satir_veri:
                if isinstance(deger, bool) or not isinstance(deger, (int, float)):
                    raise ValueError("hücre sayı olmalı")
                if not math.isfinite(deger) or deger < 0 or deger > 1:
                    raise ValueError("hücre geçersiz")
    for konum in (satir, sutun):
        if isinstance(konum, bool) or not isinstance(konum, int) or konum < 0:
            raise ValueError("konum geçersiz")
    if satir + len(tetik) > len(goruntu) or sutun + len(tetik[0]) > len(goruntu[0]):
        raise ValueError("tetikleyici görüntüye sığmıyor")
    sonuc = [list(s) for s in goruntu]
    for i in range(len(tetik)):
        for j in range(len(tetik[0])):
            sonuc[satir + i][sutun + j] = tetik[i][j]
    return sonuc


def _yerlesim_gecerli(y):
    return isinstance(y, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", y) is not None


def tetik_deneyi_ozeti_referans(kayitlar):
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar geçersiz")
    for k in kayitlar:
        if not isinstance(k, dict) or set(k) != {"yerlesim", "temiz_dogru", "hedef_basarili"}:
            raise ValueError("kayıt şeması geçersiz")
        if not _yerlesim_gecerli(k["yerlesim"]):
            raise ValueError("yerleşim geçersiz")
        if not isinstance(k["temiz_dogru"], bool) or not isinstance(k["hedef_basarili"], bool):
            raise ValueError("alanlar bool olmalı")
    sonuc = []
    for y in sorted({x["yerlesim"] for x in kayitlar}):
        grup = [x for x in kayitlar if x["yerlesim"] == y]
        sonuc.append({"yerlesim": y, "deneme": len(grup),
                      "temiz_dogruluk": round(sum(1 for x in grup if x["temiz_dogru"]) / len(grup), 6),
                      "hedef_basarisi": round(sum(1 for x in grup if x["hedef_basarili"]) / len(grup), 6)})
    return sonuc


def yerlesim_sec_referans(kayitlar, temiz_alt_sinir):
    def sayi(d):
        return not isinstance(d, bool) and isinstance(d, (int, float)) and math.isfinite(d) and 0 <= d <= 1
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar geçersiz")
    if not sayi(temiz_alt_sinir):
        raise ValueError("alt sınır geçersiz")
    for k in kayitlar:
        if not isinstance(k, dict) or set(k) != {"yerlesim", "temiz", "hedef_basarisi"}:
            raise ValueError("kayıt şeması geçersiz")
        if not _yerlesim_gecerli(k["yerlesim"]):
            raise ValueError("yerleşim geçersiz")
        if not sayi(k["temiz"]) or not sayi(k["hedef_basarisi"]):
            raise ValueError("ölçüm geçersiz")
    satirlar = []
    for y in sorted({x["yerlesim"] for x in kayitlar}):
        grup = [x for x in kayitlar if x["yerlesim"] == y]
        temiz = sum(x["temiz"] for x in grup) / len(grup)
        basari = sum(x["hedef_basarisi"] for x in grup) / len(grup)
        satirlar.append({"yerlesim": y, "temiz": round(temiz, 6), "hedef_basarisi": round(basari, 6),
                         "uygun": temiz >= temiz_alt_sinir, "_t": temiz, "_b": basari})
    uygunlar = [x for x in satirlar if x["uygun"]]
    secilen = min(uygunlar, key=lambda x: (-x["_b"], -x["_t"], x["yerlesim"]))["yerlesim"] if uygunlar else None
    for s in satirlar:
        del s["_t"], s["_b"]
    return {"satirlar": satirlar, "secilen": secilen}


def _veri(np, tohum, n):
    """Sınıf 1: üst yarı daha parlak; sınıf 0: alt yarı daha parlak. Değerler [0,1]."""
    rng = np.random.default_rng(tohum)
    X = rng.uniform(0.0, 0.6, size=(n, BOYUT, BOYUT))
    y = rng.integers(0, 2, size=n)
    for i in range(n):
        if y[i] == 1:
            X[i, :3, :] += 0.2
        else:
            X[i, 3:, :] += 0.2
    return np.clip(X, 0.0, 0.95).round(4), y


def _liste(np_matris):
    return [[float(v) for v in satir] for satir in np_matris]


def _egit(torch, X, y, tohum):
    torch.manual_seed(tohum)
    model = torch.nn.Sequential(torch.nn.Flatten(), torch.nn.Linear(BOYUT * BOYUT, 24),
                                torch.nn.ReLU(), torch.nn.Linear(24, 2))
    opt = torch.optim.Adam(model.parameters(), lr=0.02)
    Xt = torch.tensor(X, dtype=torch.float32)
    yt = torch.tensor(y, dtype=torch.long)
    kayip_fn = torch.nn.CrossEntropyLoss()
    for _ in range(300):
        opt.zero_grad()
        kayip = kayip_fn(model(Xt), yt)
        kayip.backward()
        opt.step()
    model.eval()
    return model


def _tahmin(torch, model, X):
    with torch.no_grad():
        return model(torch.tensor(X, dtype=torch.float32)).argmax(dim=1).numpy()


def deney(tetik_yerlestir, tetik_deneyi_ozeti, yerlesim_sec):
    try:
        import numpy as np
        torch = ai_lab._torch()
    except ai_lab.GercekLabYok:
        raise
    except Exception as exc:
        raise ai_lab.GercekLabYok(f"numpy/torch gerekli: {exc}") from exc
    torch.set_num_threads(1)

    yerlestirme_uyumu = True
    yerlestirme_ornekleri = []
    ornek_kayitlar = []
    olcum_kayitlari = []
    kosular = []
    taban = {ad: [] for ad in YERLESIMLER}
    for tohum in TOHUMLAR:
        X, y = _veri(np, tohum, 520)
        Xs, ys = X[400:].copy(), y[400:].copy()
        # Zehirsiz taban model: tetikleyicinin kendiliğinden hedef sınıfa itme oranı.
        taban_model = _egit(torch, X[:400].copy(), y[:400].copy(), tohum)
        for ad, (sat, sut) in YERLESIMLER.items():
            Xe, ye = X[:400].copy(), y[:400].copy()
            # Zehir: kaynak sınıf (0) örneklerinin bir kısmına tetik basılır, hedef sınıfa (1) etiketlenir.
            kaynak = [i for i in range(len(ye)) if ye[i] == 0]
            zehirli = kaynak[: int(len(ye) * ZEHIR_ORANI)]
            for i in zehirli:
                Xe[i] = np.array(tetik_yerlestir_referans(_liste(Xe[i]), TETIK, sat, sut))
                ye[i] = HEDEF_SINIF
            model = _egit(torch, Xe, ye, tohum)

            temiz_tahmin = _tahmin(torch, model, Xs)
            temiz_acc = float((temiz_tahmin == ys).mean())
            kaynak_test = [i for i in range(len(ys)) if ys[i] == 0]
            tetikli = []
            for i in kaynak_test:
                ref = tetik_yerlestir_referans(_liste(Xs[i]), TETIK, sat, sut)
                try:
                    ogr = tetik_yerlestir(_liste(Xs[i]), copy.deepcopy(TETIK), sat, sut)
                except Exception:
                    ogr = None
                if ogr != ref:
                    yerlestirme_uyumu = False
                if len(yerlestirme_ornekleri) < 3 and tohum == TOHUMLAR[0] and i == kaynak_test[0]:
                    yerlestirme_ornekleri.append({"yerlesim": ad, "satir": sat, "sutun": sut,
                                                  "ogrenci_esit": ogr == ref})
                tetikli.append(ref)
            tetik_tahmin = _tahmin(torch, model, np.array(tetikli))
            asr = float((tetik_tahmin == HEDEF_SINIF).mean())
            taban_asr = float((_tahmin(torch, taban_model, np.array(tetikli)) == HEDEF_SINIF).mean())
            taban[ad].append(taban_asr)
            if tohum == TOHUMLAR[0]:
                for j, i in enumerate(kaynak_test):
                    ornek_kayitlar.append({"yerlesim": ad, "temiz_dogru": bool(temiz_tahmin[i] == ys[i]),
                                           "hedef_basarili": bool(tetik_tahmin[j] == HEDEF_SINIF)})
            olcum_kayitlari.append({"yerlesim": ad, "temiz": round(temiz_acc, 6), "hedef_basarisi": round(asr, 6)})
            kosular.append({"yerlesim": ad, "tohum": tohum, "zehirli_ornek": len(zehirli),
                            "temiz_dogruluk": round(temiz_acc, 6), "hedef_basarisi": round(asr, 6),
                            "zehirsiz_taban": round(taban_asr, 6)})

    ref_ozet = tetik_deneyi_ozeti_referans(copy.deepcopy(ornek_kayitlar))
    try:
        ogr_ozet = tetik_deneyi_ozeti(copy.deepcopy(list(reversed(ornek_kayitlar))))
    except Exception as exc:
        ogr_ozet = f"{type(exc).__name__}: {exc}"
    ref_secim = yerlesim_sec_referans(copy.deepcopy(olcum_kayitlari), TEMIZ_ALT_SINIR)
    try:
        ogr_secim = yerlesim_sec(copy.deepcopy(olcum_kayitlari), TEMIZ_ALT_SINIR)
    except Exception as exc:
        ogr_secim = f"{type(exc).__name__}: {exc}"

    maks_asr = max(s["hedef_basarisi"] for s in ref_secim["satirlar"])
    min_temiz = min(s["temiz"] for s in ref_secim["satirlar"])
    net = {s["yerlesim"]: round(s["hedef_basarisi"] - sum(taban[s["yerlesim"]]) / len(taban[s["yerlesim"]]), 6)
           for s in ref_secim["satirlar"]}
    net_secilen = min(net, key=lambda a: (-net[a], a))
    kontroller = {
        "yerlestirme_uyumu": yerlestirme_uyumu,
        "ozet_uyumu": ogr_ozet == ref_ozet,
        "secim_uyumu": ogr_secim == ref_secim,
        # Tetikleyici etkisi: en az bir yerleşimde hedef başarı yüksek, temiz doğruluk ise korunuyor.
        # Ham oran değil net etki: zehirsiz modeldeki taban itme çıkarıldıktan sonra.
        "etki_gozlendi": max(net.values()) >= 0.5 and min_temiz >= 0.9,
    }
    ozet = {
        "torch_surum": torch.__version__,
        "cihaz": "cpu",
        "zehir_orani": ZEHIR_ORANI,
        "temiz_alt_sinir": TEMIZ_ALT_SINIR,
        "yerlesim_ozeti": ref_secim["satirlar"],
        "secilen": ref_secim["secilen"],
        "maksimum_hedef_basarisi": maks_asr,
        "minimum_temiz_dogruluk": min_temiz,
        "zehirsiz_taban": {a: round(sum(v) / len(v), 6) for a, v in taban.items()},
        "net_etki": net,
        "net_etkiye_gore_secilen": net_secilen,
    }
    return {
        "kosular": kosular,
        "yerlestirme_ornekleri": yerlestirme_ornekleri,
        "ozet_ogrenci": ogr_ozet,
        "secim_ogrenci": ogr_secim,
        "kontroller": kontroller,
        "ozet": ozet,
    }


def goster(tetik_yerlestir, tetik_deneyi_ozeti, yerlesim_sec):
    rapor = deney(tetik_yerlestir, tetik_deneyi_ozeti, yerlesim_sec)
    print("Canlı koşular:")
    for k in rapor["kosular"]:
        print("  ", k)
    print("Yerleşim özeti (öğrenci):", rapor["ozet_ogrenci"])
    print("Yerleşim seçimi (öğrenci):", rapor["secim_ogrenci"])
    print("Kontroller:", rapor["kontroller"])
