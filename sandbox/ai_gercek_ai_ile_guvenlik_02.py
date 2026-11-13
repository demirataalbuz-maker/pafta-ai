# -*- coding: utf-8 -*-
"""ai-ile-guvenlik-02 (Güvenlik Analizinde Halüsinasyon ve Kanıt Eşleştirme) gerçek deney modülü."""
import json
import ai_lab

ZORUNLU_IDDIA_ALANLARI = ("iddia_id", "dosya_adi", "satir_no", "kanit_alt_dizgesi", "onerilen_paket")


def _dogrula_kaynak_haritasi(kaynak_haritasi):
    if not isinstance(kaynak_haritasi, dict):
        raise ValueError("kaynak haritası sözlük olmalı")
    if set(kaynak_haritasi.keys()) != {"dosyalar", "bilinen_paketler"}:
        raise ValueError("kaynak haritası şeması geçersiz")
    dosyalar = kaynak_haritasi["dosyalar"]
    paketler = kaynak_haritasi["bilinen_paketler"]
    if not isinstance(dosyalar, dict) or not dosyalar:
        raise ValueError("dosyalar boş olmayan sözlük olmalı")
    for ad, satirlar in dosyalar.items():
        if not isinstance(ad, str) or not ad.strip():
            raise ValueError("dosya adı geçersiz")
        if not isinstance(satirlar, list) or not satirlar:
            raise ValueError("dosya satırları boş olmayan liste olmalı")
        for s in satirlar:
            if not isinstance(s, str):
                raise ValueError("her satır string olmalı")
    if not isinstance(paketler, list) or not paketler:
        raise ValueError("bilinen paketler boş olmayan liste olmalı")
    for p in paketler:
        if not isinstance(p, str) or not p.strip():
            raise ValueError("paket adı geçersiz")


def _dogrula_iddia(iddia):
    if not isinstance(iddia, dict) or set(iddia.keys()) != set(ZORUNLU_IDDIA_ALANLARI):
        raise ValueError("iddia şeması geçersiz")
    for alan in ("iddia_id", "dosya_adi", "kanit_alt_dizgesi", "onerilen_paket"):
        if not isinstance(iddia[alan], str) or not iddia[alan].strip():
            raise ValueError("metin alanı boş olamaz")
    s = iddia["satir_no"]
    if isinstance(s, bool) or not isinstance(s, int) or s < 1:
        raise ValueError("satır numarası pozitif tam sayı olmalı")


def kanit_satiri_eslestir_referans(iddia, kaynak_haritasi):
    _dogrula_iddia(iddia)
    _dogrula_kaynak_haritasi(kaynak_haritasi)
    dosyalar = kaynak_haritasi["dosyalar"]
    paketler = kaynak_haritasi["bilinen_paketler"]

    dosya_adi = iddia["dosya_adi"]
    satir_no = iddia["satir_no"]
    alt_dizge = iddia["kanit_alt_dizgesi"]
    paket = iddia["onerilen_paket"]

    if dosya_adi not in dosyalar:
        durum = "uydurma_dosya"
    elif satir_no > len(dosyalar[dosya_adi]):
        durum = "uydurma_satir"
    elif alt_dizge not in dosyalar[dosya_adi][satir_no - 1]:
        durum = "uyusmayan_kanit"
    elif paket not in paketler:
        durum = "uydurma_paket"
    else:
        durum = "dogrulandi"

    return {
        "iddia_id": iddia["iddia_id"],
        "durum": durum,
        "gecerli": durum == "dogrulandi",
    }


def halusinasyon_orani_hesapla_referans(iddia_listesi, kaynak_haritasi):
    if not isinstance(iddia_listesi, list) or not iddia_listesi:
        raise ValueError("iddia listesi boş olamaz")
    _dogrula_kaynak_haritasi(kaynak_haritasi)
    gorulen = set()
    dogrulanan_idleri = []
    halusinasyon_turleri = {}

    for i in iddia_listesi:
        sonuc = kanit_satiri_eslestir_referans(i, kaynak_haritasi)
        iid = sonuc["iddia_id"]
        if iid in gorulen:
            raise ValueError("tekrar eden iddia kimliği")
        gorulen.add(iid)
        if sonuc["gecerli"]:
            dogrulanan_idleri.append(iid)
        else:
            tur = sonuc["durum"]
            halusinasyon_turleri[tur] = halusinasyon_turleri.get(tur, 0) + 1

    toplam = len(iddia_listesi)
    halusinasyon_sayisi = toplam - len(dogrulanan_idleri)
    oran = round(halusinasyon_sayisi / toplam, 4)
    return {
        "dogrulanan_idleri": sorted(dogrulanan_idleri),
        "halusinasyon_turleri": dict(sorted(halusinasyon_turleri.items())),
        "halusinasyon_orani": oran,
    }


def kanitli_bulgu_suzgeci_referans(iddia_listesi, kaynak_haritasi, max_halusinasyon_orani=0.35):
    if isinstance(max_halusinasyon_orani, bool) or not isinstance(max_halusinasyon_orani, (int, float)):
        raise ValueError("eşik sayısal olmalı")
    if max_halusinasyon_orani < 0 or max_halusinasyon_orani > 1:
        raise ValueError("eşik 0 ile 1 arasında olmalı")

    ozet = halusinasyon_orani_hesapla_referans(iddia_listesi, kaynak_haritasi)
    elenen = [i["iddia_id"] for i in iddia_listesi if i["iddia_id"] not in ozet["dogrulanan_idleri"]]
    guvenilir = ozet["halusinasyon_orani"] <= max_halusinasyon_orani and len(ozet["dogrulanan_idleri"]) >= 1
    return {
        "kabul_edilen_bulgular": ozet["dogrulanan_idleri"],
        "elenen_idleri": sorted(elenen),
        "halusinasyon_orani": ozet["halusinasyon_orani"],
        "rapor_karari": "onaylandi" if guvenilir else "guvenilmez_model_raporu",
    }


def deney(kanit_satiri_eslestir, halusinasyon_orani_hesapla, kanitli_bulgu_suzgeci):
    kaynak_haritasi = {
        "dosyalar": {
            "giris_servisi.py": [
                "import sqlite3",
                "def sorgula(k):",
                "    sql = 'SELECT * FROM hesaplar WHERE ad = ' + k",
                "    return sql",
            ]
        },
        "bilinen_paketler": ["sqlite3", "hashlib", "json"],
    }

    with ai_lab.SohbetOturumu() as oturum:
        c = oturum.sohbet(
            [
                {
                    "role": "system",
                    "content": "Sen kod denetçisisin. Satır 3'teki SQL sorgu birleştirmesini kısaca doğrula.",
                },
                {
                    "role": "user",
                    "content": "\n".join(kaynak_haritasi["dosyalar"]["giris_servisi.py"]),
                },
            ],
            seed=902,
            sicaklik=0.1,
            en_fazla=80,
        )
        canli_yanit = (c.get("icerik") if isinstance(c, dict) else str(c or "")).strip()
        ortam = dict(oturum.kayit)
    ortam["temizlik"] = oturum.kayit.get("temizlik")

    iddialar = [
        {
            "iddia_id": "canli-dogru-1",
            "dosya_adi": "giris_servisi.py",
            "satir_no": 3,
            "kanit_alt_dizgesi": "SELECT * FROM hesaplar",
            "onerilen_paket": "sqlite3",
        },
        {
            "iddia_id": "canli-dogru-2",
            "dosya_adi": "giris_servisi.py",
            "satir_no": 1,
            "kanit_alt_dizgesi": "import sqlite3",
            "onerilen_paket": "sqlite3",
        },
        {
            "iddia_id": "canli-halusinasyon-1",
            "dosya_adi": "giris_servisi.py",
            "satir_no": 45,
            "kanit_alt_dizgesi": "SELECT *",
            "onerilen_paket": "sqlite3",
        },
    ]

    tekil = kanit_satiri_eslestir(dict(iddialar[0]), kaynak_haritasi)
    tekil_ref = kanit_satiri_eslestir_referans(iddialar[0], kaynak_haritasi)
    oran = halusinasyon_orani_hesapla(list(iddialar), kaynak_haritasi)
    oran_ref = halusinasyon_orani_hesapla_referans(iddialar, kaynak_haritasi)
    suzgec = kanitli_bulgu_suzgeci(list(iddialar), kaynak_haritasi, 0.4)
    suzgec_ref = kanitli_bulgu_suzgeci_referans(iddialar, kaynak_haritasi, 0.4)

    kontroller = {
        "tekil_eslestirme_uyumu": tekil == tekil_ref and tekil["gecerli"],
        "halusinasyon_orani_uyumu": oran == oran_ref,
        "suzgec_uyumu": suzgec == suzgec_ref and suzgec["rapor_karari"] == "onaylandi",
        "cihaz_dogrulandi": ai_lab.cihaz_dogrulandi(ortam.get("bellek")),
        "kaynak_temizlendi": ai_lab.kaynak_temizlendi(ortam.get("temizlik")),
    }

    return {
        "ortam": ortam,
        "ayarlar": {"max_halusinasyon_orani": 0.4},
        "canli_yanit": canli_yanit,
        "oran": oran,
        "suzgec": suzgec,
        "kontroller": kontroller,
        "ozet": {
            "model": ortam["model"]["ad"],
            "dogrulanan_sayisi": len(suzgec["kabul_edilen_bulgular"]),
            "elenen_sayisi": len(suzgec["elenen_idleri"]),
            "halusinasyon_orani": suzgec["halusinasyon_orani"],
            "rapor_karari": suzgec["rapor_karari"],
        },
    }


def goster(kanit_satiri_eslestir, halusinasyon_orani_hesapla, kanitli_bulgu_suzgeci):
    r = deney(kanit_satiri_eslestir, halusinasyon_orani_hesapla, kanitli_bulgu_suzgeci)
    o = r["ozet"]
    print(f"Model: {o['model']}")
    print(f"Doğrulanan={o['dogrulanan_sayisi']}, Elenen={o['elenen_sayisi']}, Halüsinasyon oranı={o['halusinasyon_orani']}")
    print(f"Rapor kararı: {o['rapor_karari']}")
    yol = ai_lab.kanit_yaz("ile-guvenlik-02-halusinasyon-calistir", {
        "kaynak": "gercek",
        "kabul": False,
        "ders": "ai-ile-guvenlik-02",
        "ortam": r["ortam"],
        "ayarlar": r["ayarlar"],
        "ozet": o,
    })
    print("Kanıt:", yol)
    return r
