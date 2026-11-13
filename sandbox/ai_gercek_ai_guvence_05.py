# -*- coding: utf-8 -*-
"""ai-guvence-05 gerçek deneyi: Tekrarlanabilirlik ve kriptografik kanıt paketi doğrulaması.

Öğrencinin `kanit_manifestu_dogrula`, `dosya_kanitlarini_dogrula` ve `kanit_fark_raporu`
işlevleri, disk üzerinde gerçekten çalıştırılan `scikit-learn` (`LogisticRegression`) deney
paketlerinin gerçek SHA-256 özetleri ve bayt boyutları üzerinde sınanır.
"""
import copy
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import ai_lab


def kanit_manifestu_dogrula_referans(manifest):
    if not isinstance(manifest, dict) or set(manifest) != {"id", "veri_surumu", "model_surumu", "tohum", "ortam"}:
        raise ValueError("manifest şeması geçersiz")
    if not isinstance(manifest["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", manifest["id"]):
        raise ValueError("kimlik geçersiz")
    for alan in ("veri_surumu", "model_surumu"):
        deger = manifest[alan]
        if not isinstance(deger, str) or not deger or deger != deger.strip() or any(ord(k) < 32 for k in deger):
            raise ValueError("sürüm geçersiz")
    if isinstance(manifest["tohum"], bool) or not isinstance(manifest["tohum"], int) or manifest["tohum"] < 0:
        raise ValueError("tohum geçersiz")
    ortam = manifest["ortam"]
    if not isinstance(ortam, dict) or set(ortam) != {"python", "kutuphane"}:
        raise ValueError("ortam şeması geçersiz")
    for alan in ("python", "kutuphane"):
        deger = ortam[alan]
        if not isinstance(deger, str) or not deger or deger != deger.strip() or any(ord(k) < 32 for k in deger):
            raise ValueError("ortam sürümü geçersiz")
    return {
        "id": manifest["id"],
        "veri_surumu": manifest["veri_surumu"],
        "model_surumu": manifest["model_surumu"],
        "tohum": manifest["tohum"],
        "ortam": {"python": ortam["python"], "kutuphane": ortam["kutuphane"]},
    }


def _dosya_listesi_dogrula(dosyalar, bos_olabilir=False):
    if not isinstance(dosyalar, list):
        raise ValueError("dosyalar liste olmalı")
    if not dosyalar and not bos_olabilir:
        raise ValueError("dosyalar boş olamaz")
    yollar = set()
    sonuc = []
    for dosya in dosyalar:
        if not isinstance(dosya, dict) or set(dosya) != {"yol", "sha256", "boyut"}:
            raise ValueError("dosya şeması geçersiz")
        yol = dosya["yol"]
        if (
            not isinstance(yol, str)
            or not yol
            or yol.startswith("/")
            or "\\" in yol
            or any(ord(k) < 32 for k in yol)
            or any(parca in ("", ".", "..") for parca in yol.split("/"))
            or yol in yollar
        ):
            raise ValueError("yol geçersiz")
        if not isinstance(dosya["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", dosya["sha256"]):
            raise ValueError("sha256 geçersiz")
        boyut = dosya["boyut"]
        if isinstance(boyut, bool) or not isinstance(boyut, int) or boyut < 0:
            raise ValueError("boyut geçersiz")
        yollar.add(yol)
        sonuc.append({"yol": yol, "sha256": dosya["sha256"], "boyut": boyut})
    return sorted(sonuc, key=lambda x: x["yol"])


def dosya_kanitlarini_dogrula_referans(dosyalar):
    return _dosya_listesi_dogrula(dosyalar, bos_olabilir=False)


def kanit_fark_raporu_referans(beklenen, gozlemlenen):
    b = {x["yol"]: x for x in _dosya_listesi_dogrula(beklenen, bos_olabilir=False)}
    g = {x["yol"]: x for x in _dosya_listesi_dogrula(gozlemlenen, bos_olabilir=True)}
    farklar = []
    for yol in sorted(set(b) | set(g)):
        if yol not in g:
            durum = "eksik"
        elif yol not in b:
            durum = "eklenen"
        elif b[yol]["sha256"] != g[yol]["sha256"] or b[yol]["boyut"] != g[yol]["boyut"]:
            durum = "degisti"
        else:
            continue
        farklar.append({
            "yol": yol,
            "durum": durum,
            "beklenen": dict(b[yol]) if yol in b else None,
            "gozlemlenen": dict(g[yol]) if yol in g else None,
        })
    return {"karar": "fark_var" if farklar else "tekrarlanabilir", "degisiklik_sayisi": len(farklar), "farklar": farklar}


def _paket_uret(kok_dizin, tohum, ek_not=False, metrik_sil=False):
    from sklearn.datasets import make_classification
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score

    X, y = make_classification(n_samples=120, n_features=5, n_informative=3, n_redundant=1, random_state=tohum)
    clf = LogisticRegression(random_state=tohum, max_iter=200)
    clf.fit(X[:80], y[:80])
    acc = round(float(accuracy_score(y[80:], clf.predict(X[80:]))), 6)

    kok_dizin.mkdir(parents=True, exist_ok=True)
    agirlik_yolu = kok_dizin / "model_agirlik.json"
    agirlik_yolu.write_text(
        json.dumps(
            {
                "coef": [[round(float(v), 6) for v in satir] for satir in clf.coef_],
                "intercept": [round(float(v), 6) for v in clf.intercept_],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    if not metrik_sil:
        metrik_yolu = kok_dizin / "cikti" / "metrik.json"
        metrik_yolu.parent.mkdir(parents=True, exist_ok=True)
        metrik_yolu.write_text(json.dumps({"dogruluk": acc, "tohum": tohum}, sort_keys=True), encoding="utf-8")

    if ek_not:
        ek_yolu = kok_dizin / "cikti" / "ek_not.txt"
        ek_yolu.parent.mkdir(parents=True, exist_ok=True)
        ek_yolu.write_text("sapma kaydi\n", encoding="utf-8")

    kayitlar = []
    for p in kok_dizin.rglob("*"):
        if p.is_file():
            veri = p.read_bytes()
            kayitlar.append({
                "yol": p.relative_to(kok_dizin).as_posix(),
                "sha256": hashlib.sha256(veri).hexdigest(),
                "boyut": len(veri),
            })
    return list(reversed(sorted(kayitlar, key=lambda x: x["yol"])))


def deney(kanit_manifestu_dogrula, dosya_kanitlarini_dogrula, kanit_fark_raporu):
    try:
        import sklearn
    except Exception as exc:
        raise ai_lab.GercekLabYok(f"scikit-learn gerekli: {exc}") from exc

    manifest = {
        "id": "canli-kanit-05",
        "veri_surumu": "sentetik-ikili-v1",
        "model_surumu": "sklearn-logreg-v1",
        "tohum": 42,
        "ortam": {
            "python": sys.version.split()[0],
            "kutuphane": f"scikit-learn-{sklearn.__version__}",
        },
    }
    ogr_manifest = kanit_manifestu_dogrula(copy.deepcopy(manifest))
    ref_manifest = kanit_manifestu_dogrula_referans(copy.deepcopy(manifest))

    with tempfile.TemporaryDirectory(prefix="pafta_guvence_05_") as tmp:
        taban = Path(tmp)
        p1 = _paket_uret(taban / "kosu1", tohum=42)
        p2 = _paket_uret(taban / "kosu2", tohum=42)
        p3 = _paket_uret(taban / "kosu3", tohum=99, ek_not=True, metrik_sil=True)

    ogr_dosyalar = dosya_kanitlarini_dogrula(copy.deepcopy(p1))
    ref_dosyalar = dosya_kanitlarini_dogrula_referans(copy.deepcopy(p1))

    ogr_ayni = kanit_fark_raporu(copy.deepcopy(p1), copy.deepcopy(p2))
    ref_ayni = kanit_fark_raporu_referans(copy.deepcopy(p1), copy.deepcopy(p2))

    ogr_farkli = kanit_fark_raporu(copy.deepcopy(p1), copy.deepcopy(p3))
    ref_farkli = kanit_fark_raporu_referans(copy.deepcopy(p1), copy.deepcopy(p3))

    kontroller = {
        "manifest_uyumu": ogr_manifest == ref_manifest,
        "dosya_kanit_uyumu": ogr_dosyalar == ref_dosyalar,
        "ayni_tohum_tekrarlanabilir": ogr_ayni == ref_ayni and ogr_ayni.get("karar") == "tekrarlanabilir",
        "farkli_tohum_fark_var": ogr_farkli == ref_farkli and ogr_farkli.get("karar") == "fark_var" and ogr_farkli.get("degisiklik_sayisi") == 3,
    }
    ozet = {
        "manifest": ref_manifest,
        "paket_dosyalari": ref_dosyalar,
        "ayni_tohum_karar": ref_ayni["karar"],
        "farkli_tohum_karar": ref_farkli["karar"],
        "farkli_tohum_degisiklik_sayisi": ref_farkli["degisiklik_sayisi"],
    }
    return {
        "manifest": ogr_manifest,
        "dosyalar": ogr_dosyalar,
        "ayni_tohum_raporu": ogr_ayni,
        "farkli_tohum_raporu": ogr_farkli,
        "kontroller": kontroller,
        "ozet": ozet,
    }


def goster(kanit_manifestu_dogrula, dosya_kanitlarini_dogrula, kanit_fark_raporu):
    rapor = deney(kanit_manifestu_dogrula, dosya_kanitlarini_dogrula, kanit_fark_raporu)
    print("Aynı tohum raporu:", rapor["ayni_tohum_raporu"])
    print("Farklı tohum raporu:", rapor["farkli_tohum_raporu"])
