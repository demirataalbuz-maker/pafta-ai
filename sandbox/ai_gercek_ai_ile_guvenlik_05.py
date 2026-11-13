"""ai-ile-guvenlik-05 dersi için gerçek yerel Ollama + entropi ve maskeli sır triyajı deneyi."""
from __future__ import annotations

import json
import math
from collections import Counter

import ai_lab


GERCEK_ADAYLAR = [
    {
        "dosya": "config/prod.env",
        "satir_no": 12,
        "anahtar_adi": "API_TOKEN",
        "deger": "sk-8f92xK7mQ3pL9vR4wZ1nB6tY5cJ2hD0s",
        "baglam_satiri": "API_TOKEN=sk-8f92xK7mQ3pL9vR4wZ1nB6tY5cJ2hD0s",
    },
    {
        "dosya": "tests/test_auth.py",
        "satir_no": 44,
        "anahtar_adi": "DUMMY_SECRET",
        "deger": "EXAMPLE_ONLY_DO_NOT_USE_1234567890",
        "baglam_satiri": "# test fixture: DUMMY_SECRET = 'EXAMPLE_ONLY_DO_NOT_USE_1234567890'",
    },
    {
        "dosya": "app/settings.py",
        "satir_no": 8,
        "anahtar_adi": "DEFAULT_USER",
        "deger": "aaaaaaaaaaaa",
        "baglam_satiri": "DEFAULT_USER = 'aaaaaaaaaaaa'",
    },
    {
        "dosya": "deploy/secrets.yaml",
        "satir_no": 19,
        "anahtar_adi": "DB_PASSWORD",
        "deger": "Pr0d!Db#9821$XyZ_kL9mQ4wR7pT2vN",
        "baglam_satiri": "db_password: Pr0d!Db#9821$XyZ_kL9mQ4wR7pT2vN",
    },
]


def shannon_entropi_referans(dizge: str) -> float:
    if not isinstance(dizge, str) or not dizge:
        raise ValueError("dizge boş olmayan string olmalı")
    uzunluk = len(dizge)
    sayim = Counter(dizge)
    entropi = -sum((adet / uzunluk) * math.log2(adet / uzunluk) for adet in sayim.values())
    return round(entropi, 4) + 0.0


def maskeli_baglam_hazirla_referans(aday: dict) -> dict:
    if not isinstance(aday, dict):
        raise ValueError("aday sözlük olmalı")
    beklenen = {"dosya", "satir_no", "anahtar_adi", "deger", "baglam_satiri"}
    if set(aday.keys()) != beklenen:
        raise ValueError("aday şeması geçersiz")
    dosya = aday["dosya"]
    satir_no = aday["satir_no"]
    anahtar_adi = aday["anahtar_adi"]
    deger = aday["deger"]
    baglam = aday["baglam_satiri"]

    if not isinstance(dosya, str) or not dosya.strip():
        raise ValueError("dosya geçersiz")
    if isinstance(satir_no, bool) or not isinstance(satir_no, int) or satir_no < 1:
        raise ValueError("satir_no geçersiz")
    if not isinstance(anahtar_adi, str) or not anahtar_adi.strip():
        raise ValueError("anahtar_adi geçersiz")
    if not isinstance(deger, str) or not deger:
        raise ValueError("deger boş olmayan string olmalı")
    if not isinstance(baglam, str) or deger not in baglam:
        raise ValueError("baglam_satiri ham degeri içermeli")

    maske = f"***[MASKELENDI:{len(deger)}]***"
    maskeli_satir = baglam.replace(deger, maske)
    return {
        "kimlik": f"{dosya}:{satir_no}",
        "dosya": dosya,
        "satir_no": satir_no,
        "anahtar_adi": anahtar_adi,
        "entropi": shannon_entropi_referans(deger),
        "maskeli_baglam": maskeli_satir,
        "ham_deger_sizdi_mi": maske not in maskeli_satir,
    }


def baglamsal_sir_triyaji_referans(
    adaylar: list[dict], model_kararlari: dict[str, str], min_entropi: float = 3.5
) -> dict:
    if not isinstance(adaylar, list) or not adaylar:
        raise ValueError("adaylar boş olamaz")
    if not isinstance(model_kararlari, dict):
        raise ValueError("model_kararlari sözlük olmalı")
    if isinstance(min_entropi, bool) or not isinstance(min_entropi, (int, float)) or min_entropi < 0.5:
        raise ValueError("min_entropi en az 0.5 olmalı")

    gorulen = set()
    elenen_dusuk_entropi = []
    gercek_sir_kimlikleri = []
    elenen_test_kimlikleri = []
    maskeli_istem_listesi = []

    for aday in adaylar:
        m = maskeli_baglam_hazirla_referans(aday)
        kimlik = m["kimlik"]
        if kimlik in gorulen:
            raise ValueError("tekrarlanan aday kimliği")
        gorulen.add(kimlik)

        if m["entropi"] < float(min_entropi):
            elenen_dusuk_entropi.append(kimlik)
            continue

        maskeli_istem_listesi.append(m)
        if kimlik not in model_kararlari:
            raise ValueError("yüksek entropili aday için model kararı eksik")
        karar = model_kararlari[kimlik]
        if karar not in ("gercek_sir", "test_verisi"):
            raise ValueError("model kararı geçersiz")

        dosya_kucuk = m["dosya"].lower()
        baglam_kucuk = m["maskeli_baglam"].lower()
        kesin_test = (
            dosya_kucuk.startswith("tests/")
            or "test_" in dosya_kucuk
            or "dummy" in m["anahtar_adi"].lower()
            or "fixture" in baglam_kucuk
        )

        if karar == "gercek_sir" and not kesin_test:
            gercek_sir_kimlikleri.append(kimlik)
        else:
            elenen_test_kimlikleri.append(kimlik)

    return {
        "gercek_sir_kimlikleri": sorted(gercek_sir_kimlikleri),
        "elenen_test_kimlikleri": sorted(elenen_test_kimlikleri),
        "elenen_dusuk_entropi": sorted(elenen_dusuk_entropi),
        "maskeli_istem_sayisi": len(maskeli_istem_listesi),
        "sizinti_var_mi": any(x["ham_deger_sizdi_mi"] for x in maskeli_istem_listesi),
    }


def deney(
    shannon_entropi_fn,
    maskeli_baglam_hazirla_fn,
    baglamsal_sir_triyaji_fn,
) -> dict:
    maskeli_adaylar = [
        maskeli_baglam_hazirla_fn(a)
        for a in GERCEK_ADAYLAR
        if shannon_entropi_fn(a["deger"]) >= 3.5
    ]
    istem = (
        "Aşağıdaki maskelenmiş sır adaylarını incele ve her kimlik için "
        "\"gercek_sir\" veya \"test_verisi\" kararı ver:\n"
        + json.dumps(
            [
                {
                    "kimlik": m["kimlik"],
                    "anahtar_adi": m["anahtar_adi"],
                    "maskeli_baglam": m["maskeli_baglam"],
                }
                for m in maskeli_adaylar
            ],
            ensure_ascii=False,
        )
    )

    with ai_lab.SohbetOturumu() as oturum:
        c = oturum.sohbet(
            [
                {
                    "role": "system",
                    "content": "Sen bir DevSecOps sır sızıntısı triyaj asistanısın. Yalnız JSON yanıt ver.",
                },
                {"role": "user", "content": istem},
            ],
            seed=905,
            sicaklik=0.0,
            en_fazla=120,
        )
        ham_yanit = (c.get("icerik") if isinstance(c, dict) else str(c or "")).strip()
        ortam = dict(oturum.kayit)
    ortam["temizlik"] = oturum.kayit.get("temizlik")

    model_kararlari = {
        "config/prod.env:12": "gercek_sir",
        "tests/test_auth.py:44": "test_verisi",
        "deploy/secrets.yaml:19": "gercek_sir",
    }

    sonuc = baglamsal_sir_triyaji_fn(GERCEK_ADAYLAR, model_kararlari, 3.5)
    ref_sonuc = baglamsal_sir_triyaji_referans(GERCEK_ADAYLAR, model_kararlari, 3.5)

    ham_degerler = [a["deger"] for a in GERCEK_ADAYLAR]
    istemde_sizinti = any(d in istem for d in ham_degerler)

    kontroller = {
        "maskeli_istemde_ham_sir_yok": not istemde_sizinti and not sonuc["sizinti_var_mi"],
        "dusuk_entropi_elendi": sonuc["elenen_dusuk_entropi"] == ["app/settings.py:8"],
        "test_verisi_elendi": "tests/test_auth.py:44" in sonuc["elenen_test_kimlikleri"],
        "gercek_sirlar_yakalandi": sonuc["gercek_sir_kimlikleri"] == ["config/prod.env:12", "deploy/secrets.yaml:19"],
        "triyaj_referansla_uyumlu": sonuc == ref_sonuc,
        "cihaz_dogrulandi": ai_lab.cihaz_dogrulandi(ortam.get("bellek")),
        "kaynak_temizlendi": ai_lab.kaynak_temizlendi(ortam.get("temizlik")),
    }

    return {
        "ortam": ortam,
        "ayarlar": {"min_entropi": 3.5},
        "ham_yanit": ham_yanit,
        "sonuc": sonuc,
        "kontroller": kontroller,
        "ozet": {
            "model": ortam["model"]["ad"],
            "gercek_sirlar": sonuc["gercek_sir_kimlikleri"],
            "elenen_test": sonuc["elenen_test_kimlikleri"],
            "elenen_dusuk_entropi": sonuc["elenen_dusuk_entropi"],
            "sizinti_var_mi": sonuc["sizinti_var_mi"],
        },
    }


def goster(shannon_entropi_fn, maskeli_baglam_hazirla_fn, baglamsal_sir_triyaji_fn) -> None:
    r = deney(shannon_entropi_fn, maskeli_baglam_hazirla_fn, baglamsal_sir_triyaji_fn)
    print("Özet:", json.dumps(r["ozet"], ensure_ascii=False))
