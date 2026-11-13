"""ai-ile-guvenlik-08 dersi için gerçek yerel Ollama + dilbilgisi destekli fuzzing deneyi."""
from __future__ import annotations

import json

IZINLI_KOMUTLAR = ("listele", "detay", "durum")

ADAY_YUKLER = [
    {"yuk_id": "f1", "json_metni": '{"komut": "listele", "limit": 10}'},
    {"yuk_id": "f2", "json_metni": '{"komut": "listele", "limit": -1}'},
    {"yuk_id": "f3", "json_metni": '{"komut": "listele", "limit": 50000}'},
    {"yuk_id": "f4", "json_metni": "{bozuk json"},
    {"yuk_id": "f5", "json_metni": '{"komut": "sil", "limit": 10}'},
]


def hedef_isleyici_simule(veri: dict) -> dict:
    """Ön doğrulamadan geçmiş veriyi işleyen iç servis; sınır değerlerde anomali üretir."""
    limit = veri["limit"]
    if limit < 0:
        raise IndexError("negatif indeks taşması")
    if limit > 1000:
        raise MemoryError("aşırı bellek tahsisi")
    return {"durum": "tamam", "adet": limit}


def dilbilgisi_yuku_dogrula_referans(json_metni: str) -> dict:
    if not isinstance(json_metni, str) or not json_metni.strip():
        raise ValueError("json_metni boş olmayan string olmalı")
    try:
        veri = json.loads(json_metni)
    except Exception:
        return {"gecerli": False, "neden": "json_hatasi", "veri": None}

    if not isinstance(veri, dict) or set(veri.keys()) != {"komut", "limit"}:
        return {"gecerli": False, "neden": "sema_hatasi", "veri": None}

    komut = veri["komut"]
    limit = veri["limit"]
    if komut not in IZINLI_KOMUTLAR:
        return {"gecerli": False, "neden": "yasak_komut", "veri": None}
    if isinstance(limit, bool) or not isinstance(limit, int):
        return {"gecerli": False, "neden": "tip_hatasi", "veri": None}

    return {"gecerli": True, "neden": "tamam", "veri": veri}


def sinir_mutasyonlari_uret_referans(temel_komut: str) -> list[str]:
    if not isinstance(temel_komut, str) or temel_komut not in IZINLI_KOMUTLAR:
        raise ValueError("temel_komut izinli komutlardan biri olmalı")
    sinir_degerler = (-1, 0, 1, 1000, 10001)
    return [
        json.dumps({"komut": temel_komut, "limit": deger}, sort_keys=True)
        for deger in sinir_degerler
    ]


def fuzz_kampanyasi_kostur_referans(aday_yukler: list[dict]) -> dict:
    if not isinstance(aday_yukler, list) or not aday_yukler:
        raise ValueError("aday_yukler boş olamaz")

    gorulen = set()
    elenen_yukler = []
    normal_yukler = []
    anomali_yukleri = {}

    for a in aday_yukler:
        if not isinstance(a, dict) or set(a.keys()) != {"yuk_id", "json_metni"}:
            raise ValueError("aday yük şeması geçersiz")
        yid = a["yuk_id"]
        metin = a["json_metni"]
        if not isinstance(yid, str) or not yid.strip() or yid in gorulen:
            raise ValueError("yuk_id geçersiz veya tekrarlı")
        gorulen.add(yid)

        dogrulama = dilbilgisi_yuku_dogrula_referans(metin)
        if not dogrulama["gecerli"]:
            elenen_yukler.append(yid)
            continue

        try:
            hedef_isleyici_simule(dogrulama["veri"])
            normal_yukler.append(yid)
        except Exception as e:
            anomali_yukleri[yid] = type(e).__name__

    return {
        "normal_yukler": sorted(normal_yukler),
        "elenen_yukler": sorted(elenen_yukler),
        "anomali_yukleri": anomali_yukleri,
        "anomali_sayisi": len(anomali_yukleri),
    }


def deney(dilbilgisi_yuku_dogrula_fn, sinir_mutasyonlari_uret_fn, fuzz_kampanyasi_kostur_fn) -> dict:
    import ai_lab

    with ai_lab.SohbetOturumu() as oturum:
        c = oturum.sohbet(
            [
                {
                    "role": "system",
                    "content": "Sen dilbilgisi destekli fuzzing uzmanısın. {'komut': 'listele', 'limit': N} şeması için sınır değer öner.",
                },
                {"role": "user", "content": "Sınır değer mutasyonlarını listele."},
            ],
            seed=908,
            sicaklik=0.0,
            en_fazla=100,
        )
        canli_yanit = (c.get("icerik") if isinstance(c, dict) else str(c or "")).strip()
        ortam = dict(oturum.kayit)
    ortam["temizlik"] = oturum.kayit.get("temizlik")

    mutasyonlar = sinir_mutasyonlari_uret_fn("listele")
    mutasyonlar_ref = sinir_mutasyonlari_uret_referans("listele")

    kampanya = fuzz_kampanyasi_kostur_fn(ADAY_YUKLER)
    kampanya_ref = fuzz_kampanyasi_kostur_referans(ADAY_YUKLER)

    kontroller = {
        "dilbilgisi_dogrulama_uyumu": dilbilgisi_yuku_dogrula_fn(ADAY_YUKLER[0]["json_metni"]) == dilbilgisi_yuku_dogrula_referans(ADAY_YUKLER[0]["json_metni"]),
        "sinir_mutasyon_uyumu": mutasyonlar == mutasyonlar_ref and len(mutasyonlar) == 5,
        "fuzz_kampanya_uyumu": kampanya == kampanya_ref,
        "anomaliler_yakalandi": kampanya["anomali_yukleri"] == {"f2": "IndexError", "f3": "MemoryError"},
        "cihaz_dogrulandi": ai_lab.cihaz_dogrulandi(ortam.get("bellek")),
        "kaynak_temizlendi": ai_lab.kaynak_temizlendi(ortam.get("temizlik")),
    }

    return {
        "ortam": ortam,
        "ayarlar": {"izinli_komutlar": list(IZINLI_KOMUTLAR)},
        "canli_yanit": canli_yanit,
        "kampanya": kampanya,
        "kontroller": kontroller,
        "ozet": {
            "model": ortam["model"]["ad"],
            "normal_yukler": kampanya["normal_yukler"],
            "elenen_yukler": kampanya["elenen_yukler"],
            "anomali_yukleri": kampanya["anomali_yukleri"],
        },
    }


def goster(dilbilgisi_yuku_dogrula_fn, sinir_mutasyonlari_uret_fn, fuzz_kampanyasi_kostur_fn) -> None:
    r = deney(dilbilgisi_yuku_dogrula_fn, sinir_mutasyonlari_uret_fn, fuzz_kampanyasi_kostur_fn)
    print("Özet:", json.dumps(r["ozet"], ensure_ascii=False))
