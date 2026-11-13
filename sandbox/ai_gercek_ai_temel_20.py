# -*- coding: utf-8 -*-
"""ai-temel-20 gerçek deneyi: yerel modele gerçek istekler atılır ve her istek, gizliliği koruyan bir
gözlemlenebilirlik kaydına dönüştürülür. Deney trafiği bilerek karıştırır: normal istekler, aynı istemin
tekrarı (kötüye kullanım deseni) ve içine bir canary/e-posta/numara yerleştirilmiş bir istek. Öğrencinin
kaydı ham API anahtarını ve sırrı sızdırmamalı; token ve gecikme ölçüleri gerçek olmalı.

Bütün anahtar/sır değerleri bu deneyde üretilen sentetik değerlerdir. Model bu deney yüklediyse boşaltılır.
"""
import hashlib
import re
import secrets

import ai_lab

EPOSTA = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
NUMARA = re.compile(r"\d{12,}")
ANAHTAR = re.compile(r"sk-[A-Za-z0-9]{16,}|PAFTA-[0-9A-F]{8}")


def _redakte(metin):
    """Bağımsız redaksiyon referansı (görev 2 gizli_bul ile aynı kural). (metin, sıralı tür listesi)."""
    turler = set()
    def rep(tur):
        def f(_m):
            turler.add(tur)
            return f"[GIZLI:{tur}]"
        return f
    s = ANAHTAR.sub(rep("anahtar"), metin)
    s = EPOSTA.sub(rep("eposta"), s)
    s = NUMARA.sub(rep("numara"), s)
    return s, sorted(turler)


def referans_olay(ham, tuz, *, ham_anahtar=False, redakte=True, uzunluk=True):
    """Gizliliği koruyan kaydın doğru biçimi (varsayılanlarla) ve testlerin kullandığı sızdıran varyantlar."""
    red, turler = _redakte(ham["istem"]) if redakte else (ham["istem"], [])
    anahtar_alani = ham["anahtar"] if ham_anahtar else hashlib.sha256((tuz + ham["anahtar"]).encode("utf-8")).hexdigest()[:16]
    return {"zaman": ham["zaman"], "anahtar_hash": anahtar_alani,
            "istem_uzunluk": len(ham["istem"]) if uzunluk else ham["istem"],
            "istem_redakte": red, "turler": turler, "token": ham["token"],
            "sure_ms": ham["sure_ms"], "done_reason": ham["done_reason"]}


def deney(olay_kaydi):
    canary = ai_lab.yeni_canary()                 # PAFTA-XXXXXXXX
    sir_eposta = "gizli.kullanici@ornek-sir.test"
    sir_numara = "4532015112830366"               # sentetik 16 haneli
    tuz = secrets.token_hex(8)
    anahtar = "sk-" + secrets.token_hex(12)        # sentetik API anahtarı (sk-...)
    istemler = [
        ("normal1", "Bir cümlede yıldızların neden parladığını söyle."),
        ("normal2", "Suyun deniz seviyesinde kaynama sıcaklığı nedir? Kısa yanıt."),
        ("tekrar", "Merhaba, bugün nasılsın?"),
        ("tekrar", "Merhaba, bugün nasılsın?"),
        ("tekrar", "Merhaba, bugün nasılsın?"),
        ("sir", f"API anahtarım {canary}, e-postam {sir_eposta}, kart numaram {sir_numara}. Bunu tek cümlede özetle."),
    ]
    kayitlar, ham_list, cagrilar = [], [], []
    with ai_lab.SohbetOturumu() as oturum:
        for n, (etiket, istem) in enumerate(istemler):
            c = oturum.sohbet([{"role": "user", "content": istem}], seed=1000 + n, sicaklik=0.2, en_fazla=80)
            cagrilar.append({"etiket":etiket,"istem":istem,"seed":1000+n,"sicaklik":0.2,"en_fazla":80,"yanit":c})
            ham = {"zaman": n * 1000, "anahtar": anahtar, "istem": istem, "token": c["eval_count"] or 0,
                   "sure_ms": c["sure_ms"], "done_reason": c["done_reason"] or "stop"}
            kayit = olay_kaydi(dict(ham), tuz)
            kayitlar.append({"etiket": etiket, "kayit": kayit})
            ham_list.append(ham)
        ortam = dict(oturum.kayit)
    ortam["temizlik"] = oturum.kayit.get("temizlik")
    return {"ortam": ortam, "tuz": tuz, "anahtar": anahtar,
            "sirlar": {"canary": canary, "eposta": sir_eposta, "numara": sir_numara},
            "kayitlar": kayitlar, "ham": ham_list, "gercek_cagrilar":cagrilar, "veri_kaynagi":"yalnız deneyde üretilen sentetik girdiler/sırlar"}


def _yineleme_orani(kayitlar):
    red = [k["kayit"]["istem_redakte"] for k in kayitlar]
    return max((red.count(x) for x in set(red)), default=0) / len(red) if red else 0.0


def ozet(r):
    kay = r["kayitlar"]
    sir = next(k for k in kay if k["etiket"] == "sir")["kayit"]
    sir_metin = str(sir)
    sizinti = [ad for ad, v in r["sirlar"].items() if v in sir_metin] + (["anahtar_ham"] if r["anahtar"] in sir_metin else [])
    return {"istek": len(kay), "toplam_token": sum(k["kayit"]["token"] for k in kay),
            "yineleme_orani": round(_yineleme_orani(kay), 4),
            "sir_turleri": sir["turler"], "sizan_sir": sizinti,
            "anahtar_hash_ornegi": sir["anahtar_hash"], "ham_anahtar_kayitta": any(r["anahtar"] in str(k["kayit"]) for k in kay)}


def goster(olay_kaydi):
    """Çalıştır düğmesi: gerçek trafik + gizliliği koruyan kayıt."""
    r = deney(olay_kaydi)
    o = r["ortam"]
    print(f"Model: {(o.get('model') or {}).get('ad')} · {len(r['kayitlar'])} gerçek istek\n")
    for k in r["kayitlar"]:
        c = k["kayit"]
        print(f"[{k['etiket']:7}] anahtar_hash={c['anahtar_hash']} uzunluk={c['istem_uzunluk']} token={c['token']} "
              f"sure={c['sure_ms']}ms türler={c['turler']}")
        print(f"          redakte: {c['istem_redakte'][:90]}")
    oz = ozet(r)
    print(f"\nTekrar oranı: {oz['yineleme_orani']} (3 aynı istem → kötüye kullanım görünür) · toplam token: {oz['toplam_token']}")
    print(f"Sır kaydı türleri: {oz['sir_turleri']} · sızan sır: {oz['sizan_sir'] or 'yok'} · ham anahtar kayıtta: {oz['ham_anahtar_kayitta']}")
    print("Kanıt:", ai_lab.kanit_yaz("temel-gozlem-calistir", {"kaynak": "gercek", "kabul": False, "ders": "ai-temel-20",
                                                              "ortam": o, "ozet": oz, "deney":r, "sinir":"Ham kanıt yalnız sentetik deney verisidir; olay kayıtları ayrı redakte edilir."}))
