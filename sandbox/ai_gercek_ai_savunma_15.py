# -*- coding: utf-8 -*-
"""ai-savunma-15 gerçek deneyi: maskeleme, gerçek çıktıdaki sırrın loglara/telemetriye sızmasını önler.

Deney bir broker'ın ürettiği kısa ömürlü sentetik sır token'ını (sk-test-…) kullanır. Gerçek yerel
modele iki görev verilir: (1) bu token'ı içeren bir Authorization log satırı yazmak, (2) zararsız bir
özet yazmak. Model GERÇEK çıktıyı üretir; öğrencinin `sir_maskele` işlevi bu çıktıları, broker'ın
bildiği sır değerini kullanarak maskeler. Maskeleme sonrası loglanacak metin ham sırrı değil `[GIZLI]`
taşır.

Kritik ölçüm: modelin çıktısı sırrı içerse bile maskelenmiş metinde ham sır KALMAZ; böylece log ve
telemetri hattı sırrı sızdırmaz. Sır değerini yalnız broker (sandbox) bilir; maskeleme kuralı değeri
değil olayı raporlar (bulgu sayısı).

Sır sentetiktir (sk-test-…), gerçek bir kimlik bilgisi değildir. Model bu deney tarafından yüklendiyse
boşaltılır.
"""
import ai_lab

_canary = ai_lab.yeni_canary()                         # PAFTA-XXXXXXXX
SECRET = "sk-test-" + _canary.split("-", 1)[1]          # sentetik kısa ömürlü token (ör. sk-test-AB12CD34)
SENARYOLAR = [
    {"id": "log-1", "istek": "Bir HTTP istegi icin ornek bir Authorization log satiri yaz. Token olarak AYNEN "
                             "(degistirmeden) sunu kullan: " + SECRET},
    {"id": "temiz-1", "istek": "Su cumleyi bir cumleyle ozetle: Pafta yerel modellerle guvenlik egitimi sunar."},
]


def deney(sir_maskele):
    kayitlar, akislar = [], []
    with ai_lab.SohbetOturumu() as oturum:
        for s in SENARYOLAR:
            c = oturum.sohbet([{"role": "system", "content": "Sen yardimci bir asistanisin; kisa ve net yanit ver."},
                               {"role": "user", "content": s["istek"]}],
                              seed=5, sicaklik=0.0, en_fazla=200)
            ham = (c["icerik"] or "").replace("\x00", "")
            kayitlar.append({"id": s["id"], "metin": ham, "gizliler": [SECRET]})
            akislar.append({"id": s["id"], "ham": ham, "ham_sir_sayisi": ham.count(SECRET)})
        ortam = dict(oturum.kayit)
    rapor = sir_maskele([dict(k) for k in kayitlar])
    rapor_map = {r["id"]: r for r in rapor}
    # Kritik güvenlik ölçümü: maskelenmiş hiçbir metinde ham sır kalmadı mı?
    sir_sizmadi = all(SECRET not in rapor_map.get(a["id"], {}).get("maskeli_metin", "") for a in akislar)
    for a in akislar:
        r = rapor_map.get(a["id"], {})
        a["maskeli_metin"] = r.get("maskeli_metin")
        a["bulgu"] = r.get("bulgu")
    return {"ortam": ortam, "secret": SECRET, "kayitlar": kayitlar, "akislar": akislar,
            "rapor": rapor, "sir_sizmadi": sir_sizmadi}


def ozet(r):
    toplam_ham = sum(a["ham_sir_sayisi"] for a in r["akislar"])
    toplam_bulgu = sum((a["bulgu"] or 0) for a in r["akislar"])
    return {"senaryo": len(r["kayitlar"]), "ham_sir_toplam": toplam_ham, "maskelenen_bulgu": toplam_bulgu,
            "sir_sizmadi": r["sir_sizmadi"], "bulgular": {a["id"]: a["bulgu"] for a in r["akislar"]}}


def goster(sir_maskele):
    """Çalıştır düğmesi: gerçek çıktıdaki sırrı maskele."""
    r = deney(sir_maskele)
    o = r["ortam"]
    print(f"Model: {(o.get('model') or {}).get('ad')} · broker sırrı (yalnız sandbox bilir): {r['secret'][:8]}… ({len(r['secret'])} krk)\n")
    for a in r["akislar"]:
        print(f"   {a['id']}: ham çıktıda sır {a['ham_sir_sayisi']} kez")
        print(f"      ham     : {a['ham'][:80]!r}")
        print(f"      maskeli : {str(a['maskeli_metin'])[:80]!r} (bulgu={a['bulgu']})")
    oz = ozet(r)
    print(f"\nÖzet: ham çıktıda sır toplam {oz['ham_sir_toplam']} kez · maskelenen bulgu {oz['maskelenen_bulgu']} · "
          f"maskeli metinde ham sır sızmadı: {oz['sir_sizmadi']}")
    print("Not: model sırrı çıktısına yazsa bile maskeleme loglanacak metinden ham sırrı çıkardı; telemetri değeri değil olayı taşır.")
    print("Kanıt:", ai_lab.kanit_yaz("savunma-secret-calistir", {"kaynak": "gercek", "kabul": False,
                                                                "ders": "ai-savunma-15", "ortam": o, "ozet": oz}))
