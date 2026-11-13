# -*- coding: utf-8 -*-
"""ai-saldiri-33 (KV-Cache Timing ve Prompt-Stealing Yan Kanalları) gerçek deney modülü."""
import math
import ai_lab


def grup_ozeti_referans(olcumler):
    if not isinstance(olcumler, list) or not olcumler:
        raise ValueError("ölçüm listesi geçersiz")
    gruplar = {"hit": [], "miss": []}
    for olcum in olcumler:
        if not isinstance(olcum, dict) or set(olcum) != {"grup", "sure_ms"}:
            raise ValueError("ölçüm şeması geçersiz")
        if olcum["grup"] not in gruplar:
            raise ValueError("grup geçersiz")
        sure = olcum["sure_ms"]
        if isinstance(sure, bool) or not isinstance(sure, (int, float)) or not math.isfinite(sure) or sure <= 0:
            raise ValueError("süre geçersiz")
        gruplar[olcum["grup"]].append(float(sure))
    if not gruplar["hit"] or not gruplar["miss"]:
        raise ValueError("iki grup da gerekli")

    def medyan(degerler):
        sirali = sorted(degerler)
        orta = len(sirali) // 2
        if len(sirali) % 2:
            return float(sirali[orta])
        return float((sirali[orta - 1] + sirali[orta]) / 2)

    hit = medyan(gruplar["hit"])
    miss = medyan(gruplar["miss"])
    return {
        "hit": {"n": len(gruplar["hit"]), "medyan": hit},
        "miss": {"n": len(gruplar["miss"]), "medyan": miss},
        "fark": float(miss - hit),
    }


def esik_regresyonu_referans(olcumler, esik):
    if not isinstance(olcumler, list) or not olcumler:
        raise ValueError("ölçüm listesi geçersiz")
    if isinstance(esik, bool) or not isinstance(esik, (int, float)) or not math.isfinite(esik) or esik <= 0:
        raise ValueError("eşik geçersiz")
    sonuc = {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
    for olcum in olcumler:
        if not isinstance(olcum, dict) or set(olcum) != {"gercek", "sure_ms"}:
            raise ValueError("ölçüm şeması geçersiz")
        if olcum["gercek"] not in ("hit", "miss"):
            raise ValueError("gerçek sınıf geçersiz")
        sure = olcum["sure_ms"]
        if isinstance(sure, bool) or not isinstance(sure, (int, float)) or not math.isfinite(sure) or sure <= 0:
            raise ValueError("süre geçersiz")
        tahmin = "hit" if sure <= esik else "miss"
        if tahmin == "hit" and olcum["gercek"] == "hit":
            sonuc["tp"] += 1
        elif tahmin == "hit":
            sonuc["fp"] += 1
        elif olcum["gercek"] == "miss":
            sonuc["tn"] += 1
        else:
            sonuc["fn"] += 1
    n = len(olcumler)
    sonuc["dogruluk"] = (sonuc["tp"] + sonuc["tn"]) / n
    sonuc["tpr"] = sonuc["tp"] / (sonuc["tp"] + sonuc["fn"]) if sonuc["tp"] + sonuc["fn"] else None
    sonuc["tnr"] = sonuc["tn"] / (sonuc["tn"] + sonuc["fp"]) if sonuc["tn"] + sonuc["fp"] else None
    return sonuc


def aday_kanit_raporu_referans(adaylar, min_ornek=3, min_fark_ms=5.0):
    if not isinstance(adaylar, list) or type(min_ornek) is not int or min_ornek < 1:
        raise ValueError("aday listesi veya örnek sınırı geçersiz")
    if isinstance(min_fark_ms, bool) or not isinstance(min_fark_ms, (int, float)) or not math.isfinite(min_fark_ms) or min_fark_ms < 0:
        raise ValueError("fark eşiği geçersiz")

    def medyan(degerler):
        if not isinstance(degerler, list) or len(degerler) < min_ornek:
            raise ValueError("süre listesi yetersiz")
        if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or x <= 0 for x in degerler):
            raise ValueError("süre geçersiz")
        sirali = sorted(float(x) for x in degerler)
        orta = len(sirali) // 2
        if len(sirali) % 2:
            return float(sirali[orta])
        return float((sirali[orta - 1] + sirali[orta]) / 2)

    sonuc = []
    adlar = set()
    for aday in adaylar:
        if not isinstance(aday, dict) or set(aday) != {"aday", "hit_sureleri", "miss_sureleri"}:
            raise ValueError("aday şeması geçersiz")
        if not isinstance(aday["aday"], str) or not aday["aday"] or aday["aday"] in adlar:
            raise ValueError("aday kimliği geçersiz")
        adlar.add(aday["aday"])
        hit = medyan(aday["hit_sureleri"])
        miss = medyan(aday["miss_sureleri"])
        fark = float(miss - hit)
        sonuc.append({"aday": aday["aday"], "fark": fark, "sinyal": fark >= min_fark_ms})
    sonuc.sort(key=lambda x: (-x["fark"], x["aday"]))
    return {"adaylar": sonuc, "guclu_sinyal": [x["aday"] for x in sonuc if x["sinyal"]]}


def _uzun_onek(etiket, blok_sayisi=25):
    parcalar = [
        f"[{etiket}-BLOK-{i:03d}] Kurumsal güvenlik politikası gereği iç ağ topolojisi, "
        f"anahtar rotasyon çizelgesi ve denetim kayıtları yalnız yetkili güvenlik analistleriyle paylaşılır."
        for i in range(blok_sayisi)
    ]
    return "\n".join(parcalar)


def deney(grup_ozeti, esik_regresyonu, aday_kanit_raporu):
    ortak_onek = _uzun_onek("ORTAK-SISTEM-ONEKI")
    miss_onekleri = [
        _uzun_onek("SOGUK-ONEK-ALFA"),
        _uzun_onek("SOGUK-ONEK-BETA"),
        _uzun_onek("SOGUK-ONEK-GAMA"),
    ]
    hit_sureleri = []
    miss_sureleri = []
    ham_kayitlar = []

    with ai_lab.SohbetOturumu() as oturum:
        for i, soguk_onek in enumerate(miss_onekleri):
            # 1) Soğuk (miss) önek: KV-cache tamamen yeni bir uzun bağlamı işler
            m_yanit = oturum.sohbet(
                [
                    {"role": "system", "content": soguk_onek},
                    {"role": "user", "content": f"Tek kelimeyle OK yaz (tur {i + 1})."},
                ],
                seed=100 + i,
                sicaklik=0.1,
                en_fazla=8,
            )
            miss_ms = max(1.0, float(m_yanit["sure_ms"]))
            miss_sureleri.append(miss_ms)
            ham_kayitlar.append({"tur": i + 1, "grup": "miss", "sure_ms": miss_ms, "eval_count": m_yanit["eval_count"]})

            # 2) Ortak öneki ısıt ve hemen ardından aynı ortak önekle sıcak (hit) sorgu gönder
            oturum.sohbet(
                [
                    {"role": "system", "content": ortak_onek},
                    {"role": "user", "content": "Tek kelimeyle EVET yaz."},
                ],
                seed=200 + i,
                sicaklik=0.1,
                en_fazla=8,
            )
            h_yanit = oturum.sohbet(
                [
                    {"role": "system", "content": ortak_onek},
                    {"role": "user", "content": f"Tek kelimeyle EVET yaz ({i + 1})."},
                ],
                seed=300 + i,
                sicaklik=0.1,
                en_fazla=8,
            )
            hit_ms = max(1.0, float(h_yanit["sure_ms"]))
            hit_sureleri.append(hit_ms)
            ham_kayitlar.append({"tur": i + 1, "grup": "hit", "sure_ms": hit_ms, "eval_count": h_yanit["eval_count"]})

        ortam = dict(oturum.kayit)
    ortam["temizlik"] = oturum.kayit.get("temizlik")

    olcumler_grup = [{"grup": k["grup"], "sure_ms": k["sure_ms"]} for k in ham_kayitlar]
    ozet = grup_ozeti(list(olcumler_grup))
    ozet_ref = grup_ozeti_referans(olcumler_grup)

    esik = max(0.5, (ozet_ref["hit"]["medyan"] + ozet_ref["miss"]["medyan"]) / 2.0)
    olcumler_esik = [{"gercek": k["grup"], "sure_ms": k["sure_ms"]} for k in ham_kayitlar]
    regresyon = esik_regresyonu(list(olcumler_esik), esik)
    regresyon_ref = esik_regresyonu_referans(olcumler_esik, esik)

    adaylar = [
        {"aday": "aday-ortak-onek", "hit_sureleri": list(hit_sureleri), "miss_sureleri": list(miss_sureleri)},
        {"aday": "aday-gurultu-kontrol", "hit_sureleri": list(miss_sureleri), "miss_sureleri": list(miss_sureleri)},
    ]
    aday_raporu = aday_kanit_raporu(adaylar, min_ornek=3, min_fark_ms=5.0)
    aday_raporu_ref = aday_kanit_raporu_referans(adaylar, min_ornek=3, min_fark_ms=5.0)

    kontroller = {
        "grup_ozeti_uyumu": ozet == ozet_ref,
        "esik_regresyonu_uyumu": regresyon == regresyon_ref,
        "aday_raporu_uyumu": aday_raporu == aday_raporu_ref,
        "alti_canli_olcum_alindi": len(ham_kayitlar) == 6 and len(hit_sureleri) == 3 and len(miss_sureleri) == 3,
        "cihaz_dogrulandi": ai_lab.cihaz_dogrulandi(ortam.get("bellek")),
        "kaynak_temizlendi": ai_lab.kaynak_temizlendi(ortam.get("temizlik")),
    }

    return {
        "ortam": ortam,
        "ayarlar": {"tekrar": 3, "en_fazla_token": 8, "sicaklik": 0.1, "olcum": "istek başına duvar saati süresi (sure_ms); saf TTFT değil", "esik_ms": round(esik, 2)},
        "ham_kayitlar": ham_kayitlar,
        "grup_ozeti": ozet,
        "esik_regresyonu": regresyon,
        "aday_raporu": aday_raporu,
        "kontroller": kontroller,
        "ozet": {
            "model": ortam["model"]["ad"],
            "hit_medyan_ms": ozet["hit"]["medyan"],
            "miss_medyan_ms": ozet["miss"]["medyan"],
            "medyan_fark_ms": ozet["fark"],
            "esik_ms": round(esik, 2),
            "dogruluk": regresyon["dogruluk"],
            "guclu_sinyal": aday_raporu["guclu_sinyal"],
        },
    }


def goster(grup_ozeti, esik_regresyonu, aday_kanit_raporu):
    r = deney(grup_ozeti, esik_regresyonu, aday_kanit_raporu)
    o = r["ozet"]
    print("Model:", o["model"], "| Cihaz:", r["ortam"]["cihaz"])
    for k in r["ham_kayitlar"]:
        print(f"  tur={k['tur']} [{k['grup']:<4}] sure_ms={k['sure_ms']:.1f}")
    print("Grup özeti:", r["grup_ozeti"])
    print("Eşik regresyonu:", r["esik_regresyonu"])
    print("Aday kanıt raporu:", r["aday_raporu"])
    yol = ai_lab.kanit_yaz("saldiri-33-kvcache-calistir", {
        "kaynak": "gercek",
        "kabul": False,
        "ders": "ai-saldiri-33",
        "ortam": r["ortam"],
        "ayarlar": r["ayarlar"],
        "ozet": o,
    })
    print("Kanıt:", yol)
    return r
