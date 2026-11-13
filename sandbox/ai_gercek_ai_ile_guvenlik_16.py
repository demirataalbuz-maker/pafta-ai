"""ai-ile-guvenlik-16 dersi için gerçek yerel Ollama + güvenlik ajanlarında hassasiyet, duyarlılık ve maliyet dengesi deneyi."""
from __future__ import annotations

import json

KOSU_ALANLARI = {"ayar_id", "tp", "fp", "tn", "fn", "ortalama_token", "ortalama_ms"}
KISIT_ALANLARI = {"asgari_recall", "azami_token", "azami_ms"}

KISITLAR = {
    "asgari_recall": 0.8,
    "azami_token": 600,
    "azami_ms": 1500,
}

ORNEK_KOSULAR = [
    {
        "ayar_id": "ayar-hizli-kaba",
        "tp": 6,
        "fp": 1,
        "tn": 9,
        "fn": 4,
        "ortalama_token": 220,
        "ortalama_ms": 450,
    },
    {
        "ayar_id": "ayar-dengeli-v1",
        "tp": 9,
        "fp": 1,
        "tn": 9,
        "fn": 1,
        "ortalama_token": 410,
        "ortalama_ms": 820,
    },
    {
        "ayar_id": "ayar-dengeli-hantal",
        "tp": 9,
        "fp": 1,
        "tn": 9,
        "fn": 1,
        "ortalama_token": 540,
        "ortalama_ms": 1100,
    },
    {
        "ayar_id": "ayar-asiri-dusunen",
        "tp": 10,
        "fp": 0,
        "tn": 10,
        "fn": 0,
        "ortalama_token": 950,
        "ortalama_ms": 2400,
    },
]


def _kosu_kontrol(kosu: dict) -> None:
    if not isinstance(kosu, dict) or set(kosu.keys()) != KOSU_ALANLARI:
        raise ValueError("koşu şeması geçersiz")
    aid = kosu["ayar_id"]
    if not isinstance(aid, str) or not aid.strip():
        raise ValueError("ayar_id boş olmayan string olmalı")
    for k in ("tp", "fp", "tn", "fn", "ortalama_token", "ortalama_ms"):
        v = kosu[k]
        if isinstance(v, bool) or not isinstance(v, int) or v < 0:
            raise ValueError(f"{k} negatif olmayan tam sayı olmalı")
    if (kosu["tp"] + kosu["fp"]) == 0 or (kosu["tp"] + kosu["fn"]) == 0:
        raise ValueError("payda sıfır olamaz")
    if kosu["ortalama_token"] == 0 or kosu["ortalama_ms"] == 0:
        raise ValueError("token ve ms pozitif olmalı")


def _kisit_kontrol(kisitlar: dict) -> None:
    if not isinstance(kisitlar, dict) or set(kisitlar.keys()) != KISIT_ALANLARI:
        raise ValueError("kısıt şeması geçersiz")
    r = kisitlar["asgari_recall"]
    if isinstance(r, bool) or not isinstance(r, (int, float)) or not (0.0 <= float(r) <= 1.0):
        raise ValueError("asgari_recall 0 ile 1 arasında olmalı")
    for k in ("azami_token", "azami_ms"):
        v = kisitlar[k]
        if isinstance(v, bool) or not isinstance(v, int) or v <= 0:
            raise ValueError(f"{k} pozitif tam sayı olmalı")


def ajan_metrik_hesapla_referans(kosu: dict) -> dict:
    _kosu_kontrol(kosu)
    tp = kosu["tp"]
    fp = kosu["fp"]
    fn = kosu["fn"]

    precision = round(tp / (tp + fp), 4)
    recall = round(tp / (tp + fn), 4)
    f1 = round((2 * tp) / (2 * tp + fp + fn), 4)

    return {
        "ayar_id": kosu["ayar_id"],
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "ortalama_token": kosu["ortalama_token"],
        "ortalama_ms": kosu["ortalama_ms"],
    }


def _metrik_sozlugu_kontrol(m: dict) -> None:
    beklenen = {"ayar_id", "precision", "recall", "f1", "ortalama_token", "ortalama_ms"}
    if not isinstance(m, dict) or set(m.keys()) != beklenen:
        raise ValueError("metrik sözlüğü şeması geçersiz")
    if not isinstance(m["ayar_id"], str) or not m["ayar_id"].strip():
        raise ValueError("ayar_id boş olamaz")
    for k in ("precision", "recall", "f1"):
        v = m[k]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not (0.0 <= float(v) <= 1.0):
            raise ValueError("oranlar 0 ile 1 arasında olmalı")
    for k in ("ortalama_token", "ortalama_ms"):
        v = m[k]
        if isinstance(v, bool) or not isinstance(v, int) or v <= 0:
            raise ValueError("maliyet metrikleri pozitif tam sayı olmalı")


def pareto_baskin_mi_referans(aday_a: dict, aday_b: dict) -> bool:
    _metrik_sozlugu_kontrol(aday_a)
    _metrik_sozlugu_kontrol(aday_b)

    en_az_esit = all([
        aday_a["f1"] >= aday_b["f1"],
        aday_a["ortalama_token"] <= aday_b["ortalama_token"],
        aday_a["ortalama_ms"] <= aday_b["ortalama_ms"],
    ])
    kesin_iyi = any([
        aday_a["f1"] > aday_b["f1"],
        aday_a["ortalama_token"] < aday_b["ortalama_token"],
        aday_a["ortalama_ms"] < aday_b["ortalama_ms"],
    ])
    return bool(en_az_esit and kesin_iyi)


def optimal_ajan_sec_referans(kosular: list[dict], kisitlar: dict) -> dict:
    if not isinstance(kosular, list) or not kosular:
        raise ValueError("kosular boş olmayan liste olmalı")
    _kisit_kontrol(kisitlar)

    metrikler = []
    elenenler = {}
    gorulen = set()

    for k in kosular:
        m = ajan_metrik_hesapla_referans(k)
        aid = m["ayar_id"]
        if aid in gorulen:
            raise ValueError("tekrarlanan ayar_id")
        gorulen.add(aid)

        if m["recall"] < kisitlar["asgari_recall"]:
            elenenler[aid] = "dusuk_recall"
            continue
        if m["ortalama_token"] > kisitlar["azami_token"] or m["ortalama_ms"] > kisitlar["azami_ms"]:
            elenenler[aid] = "butce_asimi"
            continue
        metrikler.append(m)

    pareto_kumesi = []
    for m in metrikler:
        if any(pareto_baskin_mi_referans(diger, m) for diger in metrikler if diger["ayar_id"] != m["ayar_id"]):
            elenenler[m["ayar_id"]] = "pareto_baskin"
        else:
            pareto_kumesi.append(m)

    pareto_kumesi.sort(key=lambda x: (-x["f1"], x["ortalama_token"], x["ayar_id"]))
    secilen = pareto_kumesi[0]["ayar_id"] if pareto_kumesi else None

    return {
        "secilen_ayar_id": secilen,
        "pareto_adaylari": [x["ayar_id"] for x in pareto_kumesi],
        "elenen_ayarlar": elenenler,
    }


def deney(ajan_metrik_hesapla_fn, pareto_baskin_mi_fn, optimal_ajan_sec_fn) -> dict:
    import ai_lab

    with ai_lab.SohbetOturumu() as oturum:
        c = oturum.sohbet(
            [
                {
                    "role": "system",
                    "content": "Sen bir SOC triyaj ajanısın. Verilen olayı tek kelimelik sınıfla ('alarm' veya 'temiz') yanıtla.",
                },
                {"role": "user", "content": "IP 10.20.9.88 /admin/export uç noktasına yetkisiz erişim denedi."},
            ],
            seed=916,
            sicaklik=0.0,
            en_fazla=40,
        )
        canli_yanit = (c.get("icerik") if isinstance(c, dict) else str(c or "")).strip()
        ortam = dict(oturum.kayit)
    ortam["temizlik"] = oturum.kayit.get("temizlik")

    m = ajan_metrik_hesapla_fn(ORNEK_KOSULAR[1])
    m_ref = ajan_metrik_hesapla_referans(ORNEK_KOSULAR[1])

    m_hantal = ajan_metrik_hesapla_referans(ORNEK_KOSULAR[2])
    baskin = pareto_baskin_mi_fn(m_ref, m_hantal)
    baskin_ref = pareto_baskin_mi_referans(m_ref, m_hantal)

    secim = optimal_ajan_sec_fn(ORNEK_KOSULAR, KISITLAR)
    secim_ref = optimal_ajan_sec_referans(ORNEK_KOSULAR, KISITLAR)

    kontroller = {
        "metrik_hesap_uyumu": m == m_ref,
        "pareto_baskinlik_uyumu": baskin == baskin_ref,
        "optimal_secim_uyumu": secim == secim_ref,
        "pareto_optimal_secildi": secim["secilen_ayar_id"] == "ayar-dengeli-v1",
        "cihaz_dogrulandi": ai_lab.cihaz_dogrulandi(ortam.get("bellek")),
        "kaynak_temizlendi": ai_lab.kaynak_temizlendi(ortam.get("temizlik")),
    }

    return {
        "ortam": ortam,
        "ayarlar": {"aday_sayisi": len(ORNEK_KOSULAR), "kisitlar": KISITLAR},
        "canli_yanit": canli_yanit,
        "secim_sonuc": secim,
        "kontroller": kontroller,
        "ozet": {
            "model": ortam["model"]["ad"],
            "secilen_ayar": secim["secilen_ayar_id"],
            "elenen_ayarlar": secim["elenen_ayarlar"],
        },
    }


def goster(ajan_metrik_hesapla_fn, pareto_baskin_mi_fn, optimal_ajan_sec_fn) -> None:
    r = deney(ajan_metrik_hesapla_fn, pareto_baskin_mi_fn, optimal_ajan_sec_fn)
    print("Özet:", json.dumps(r["ozet"], ensure_ascii=False))
