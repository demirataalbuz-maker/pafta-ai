# -*- coding: utf-8 -*-
"""ai-savunma-31 gerçek deneyi: sınırsız tüketim (denial-of-wallet, OWASP LLM10) savunması. Pahalı bir
istek yerel modele önce bütçesiz (yüksek num_predict), sonra öğrencinin bütçe-kısıtlı num_predict'iyle
gönderilir; gerçek üretilen token sayısı ve maliyeti karşılaştırılır. Bütçe sınırı, üretimi deterministik
olarak keser (done_reason="length"), böylece tek bir istek kaynakları ve faturayı tüketemez.

Bütün değerler sentetiktir. Model bu deney tarafından yüklendiyse sonunda boşaltılır.
"""
import ai_lab

# Pahalı istek: çok token üretmeye zorlar (bütçe olmasa akış uzar)
PAHALI_ISTEM = "1'den 400'e kadar bütün tam sayıları virgülle ayırarak sırayla yaz, hiçbirini atlama."
BUTCESIZ_TAVAN = 512   # saldırganın istediği yüksek üretim
KALAN_BUTCE = 32       # hesabın bu istek için kalan token bütçesi
SERT_TAVAN = 256       # istek başına katı üst sınır
GIRIS_1K, CIKIS_1K = 0.05, 0.15  # sentetik örnek fiyat (1000 token başına birim)


def referans_butce(istenen, kalan, tavan, *, tavan_yok=False, butce_yok=False):
    """Bütçe-kısıtlı num_predict (varsayılan doğru) ve testlerin kullandığı zayıf varyantlar."""
    if kalan < 1:
        return {"karar": "red", "neden": "bütçe tükendi", "num_predict": 0}
    sinirlar = [istenen]
    if not butce_yok:
        sinirlar.append(kalan)
    if not tavan_yok:
        sinirlar.append(tavan)
    return {"karar": "izin", "neden": "bütçe uygulandı", "num_predict": min(sinirlar)}


def deney(butce_uygula, sicaklik=0.1):
    kayitlar = []
    with ai_lab.SohbetOturumu() as oturum:
        plan = butce_uygula(BUTCESIZ_TAVAN, KALAN_BUTCE, SERT_TAVAN)
        for etiket, np in [("butcesiz", BUTCESIZ_TAVAN), ("butceli", plan["num_predict"])]:
            try:
                c = oturum.sohbet([{"role": "user", "content": PAHALI_ISTEM}], seed=5, sicaklik=sicaklik, en_fazla=np)
                tok = c["eval_count"] or 0
                kayitlar.append({"etiket": etiket, "num_predict": np, "token": tok, "done_reason": c["done_reason"],
                                 "sure_ms": c["sure_ms"], "ham_yanit": c["icerik"], "maliyet": round(tok / 1000 * CIKIS_1K, 6), "hata": None})
            except Exception as e:
                kayitlar.append({"etiket": etiket, "num_predict": np, "hata": f"{type(e).__name__}: {e}"})
        ortam = dict(oturum.kayit)
    ortam["temizlik"] = oturum.kayit.get("temizlik")
    return {"ortam": ortam, "istem": PAHALI_ISTEM, "plan": plan, "ayar": {"butcesiz_tavan": BUTCESIZ_TAVAN,
            "kalan_butce": KALAN_BUTCE, "sert_tavan": SERT_TAVAN, "cikis_1k": CIKIS_1K, "seed": 5, "sicaklik": sicaklik}, "kayitlar": kayitlar}


def ozet(r):
    g = {k["etiket"]: k for k in r["kayitlar"] if k.get("hata") is None}
    bs, bl = g.get("butcesiz"), g.get("butceli")
    return {"gecerli": len(g), "butcesiz_token": bs and bs["token"], "butceli_token": bl and bl["token"],
            "token_dususu": (bs["token"] - bl["token"]) if (bs and bl) else None,
            "butceli_kesildi": bool(bl) and bl["done_reason"] == "length" and bl["token"] <= r["plan"]["num_predict"],
            "butcesiz_maliyet": bs and bs["maliyet"], "butceli_maliyet": bl and bl["maliyet"],
            "plan_num_predict": r["plan"]["num_predict"]}


def goster(butce_uygula):
    """Çalıştır düğmesi: bütçesiz vs bütçeli gerçek tüketim."""
    r = deney(butce_uygula)
    o = r["ortam"]
    print(f"Model: {(o.get('model') or {}).get('ad')} · istek: {r['istem'][:60]}...")
    print(f"Bütçe planı: istenen {r['ayar']['butcesiz_tavan']}, kalan bütçe {r['ayar']['kalan_butce']}, "
          f"katı tavan {r['ayar']['sert_tavan']} → num_predict {r['plan']['num_predict']} ({r['plan']['karar']})\n")
    for k in r["kayitlar"]:
        if k.get("hata"):
            print(f"[{k['etiket']}] HATA: {k['hata']}")
            continue
        print(f"[{k['etiket']:9}] num_predict={k['num_predict']} → {k['token']} token (done={k['done_reason']}) "
              f"· {k['sure_ms']}ms · maliyet {k['maliyet']}")
    oz = ozet(r)
    print(f"\nTüketim düşüşü: {oz['butcesiz_token']} → {oz['butceli_token']} token ({oz['token_dususu']} daha az); "
          f"bütçe kesti mi: {oz['butceli_kesildi']}")
    print(f"Maliyet: bütçesiz {oz['butcesiz_maliyet']} → bütçeli {oz['butceli_maliyet']} (sentetik fiyat)")
    print("Kanıt:", ai_lab.kanit_yaz("savunma-butce-calistir", {"kaynak": "gercek", "kabul": False, "ders": "ai-savunma-31",
                                                               "ortam": o, "deney": r, "ozet": oz}))
