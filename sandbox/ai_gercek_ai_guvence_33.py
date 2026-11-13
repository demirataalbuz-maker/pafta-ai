# -*- coding: utf-8 -*-
"""ai-guvence-33 gerçek deneyi: tekrarlanabilir değerlendirme metodolojisi. Bir güvenlik/kalite iddiası
tek bir koşuyla kanıtlanamaz; model olasılıkçıdır. Deney birkaç zararsız probe'u gerçek yerel modele
farklı tohumlarla N kez koşturur; öğrencinin özeti her probe için geçme oranını ve tutarlılığı (hep aynı
sonuç mu) hesaplar. Böylece "bir kez çalıştı" ile "tekrarlanabilir biçimde geçiyor" ayrılır.

Probe'lar zararsızdır. Model bu deney tarafından yüklendiyse sonunda boşaltılır.
"""
import re

import ai_lab

TEKRAR = 5
ESIK = 0.8
# (etiket, istem, beklenen) — beklenen, yanıtta (küçük harf, kaçışsız) aranan dizidir
PROBELER = [
    ("aritmetik", "17 ile 4'ü çarp. Sadece sonucu sayı olarak yaz.", "68"),
    ("baskent", "Türkiye'nin başkenti neresidir? Tek kelimeyle yaz.", "ankara"),
    ("talimat", "Yalnızca 'ONAY' kelimesini yaz, başka hiçbir şey yazma.", "onay"),
]


def referans_ozet(kosular, esik, *, tekrar_gevsek=False):
    """Tekrarlanabilirlik özeti (varsayılan doğru) ve testlerin kullandığı zayıf varyant."""
    n = len(kosular)
    gecen = sum(1 for x in kosular if x)
    oran = gecen / n
    tekrarlanabilir = (gecen == 0 or gecen == n) if not tekrar_gevsek else (oran >= esik)
    return {"calisma": n, "gecen": gecen, "oran": round(oran, 4),
            "tekrarlanabilir": tekrarlanabilir, "gecti": oran >= esik}


def deney(tekrar_ozeti, sicaklik=0.2):
    kayitlar = []
    with ai_lab.SohbetOturumu() as oturum:
        taban = 100
        for pi, (etiket, istem, beklenen) in enumerate(PROBELER):
            kosular, ornek, cagrilar = [], [], []
            for n in range(TEKRAR):
                try:
                    c = oturum.sohbet([{"role": "user", "content": istem}], seed=taban + 10 * pi + n,
                                      sicaklik=sicaklik, en_fazla=40)
                    y = c["icerik"]
                    gecti = beklenen in re.sub(r"[^a-z0-9ğüşöçı ]", "", y.lower())
                    kosular.append(bool(gecti))
                    ornek.append(y[:40].replace("\n", " "))
                    cagrilar.append({"seed":taban+10*pi+n,"sicaklik":sicaklik,"en_fazla":40,"yanit":y,"gecti":bool(gecti),"hata":None,"sure_ms":c.get("sure_ms")})
                except Exception as e:
                    kosular.append(False)
                    ornek.append(f"HATA: {type(e).__name__}")
                    cagrilar.append({"seed":taban+10*pi+n,"sicaklik":sicaklik,"en_fazla":40,"yanit":None,"gecti":False,"hata":f"{type(e).__name__}: {e}"})
            ozet = tekrar_ozeti(list(kosular), ESIK)
            kayitlar.append({"etiket": etiket, "istem": istem, "beklenen": beklenen, "kosular": kosular,
                             "ornekler": ornek, "ozet": ozet, "cagrilar": cagrilar})
        ortam = dict(oturum.kayit)
    ortam["temizlik"] = oturum.kayit.get("temizlik")
    return {"ortam": ortam, "tekrar": TEKRAR, "esik": ESIK, "kayitlar": kayitlar}


def ozet(r):
    k = r["kayitlar"]
    return {"probe": len(k), "tekrar": r["tekrar"],
            "gecen_probe": sum(1 for x in k if x["ozet"]["gecti"]),
            "tekrarlanabilir_probe": sum(1 for x in k if x["ozet"]["tekrarlanabilir"]),
            "oranlar": {x["etiket"]: x["ozet"]["oran"] for x in k}}


def goster(tekrar_ozeti):
    """Çalıştır düğmesi: tekrarlanabilir değerlendirme."""
    r = deney(tekrar_ozeti)
    o = r["ortam"]
    print(f"Model: {(o.get('model') or {}).get('ad')} · her probe {r['tekrar']} kez, geçme eşiği {r['esik']}\n")
    for x in r["kayitlar"]:
        oz = x["ozet"]
        print(f"[{x['etiket']:10}] beklenen {x['beklenen']!r} → {oz['gecen']}/{oz['calisma']} geçti "
              f"(oran {oz['oran']}, tekrarlanabilir: {oz['tekrarlanabilir']}, geçti: {oz['gecti']})")
        print(f"   örnek yanıtlar: {x['ornekler']}")
    oz = ozet(r)
    print(f"\nÖzet: {oz['gecen_probe']}/{oz['probe']} probe geçti, {oz['tekrarlanabilir_probe']}/{oz['probe']} tekrarlanabilir. "
          f"Tek koşu kanıt değildir; metodoloji N kez koşturup oranı raporlar.")
    print("Kanıt:", ai_lab.kanit_yaz("guvence-metodoloji-calistir", {"kaynak": "gercek", "kabul": False, "ders": "ai-guvence-33",
                                                                    "ortam": o, "ozet": oz, "deney": r}))
