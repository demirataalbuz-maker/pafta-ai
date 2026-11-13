"""ai-ile-guvenlik-15 dersi için gerçek yerel Ollama + çok ajanlı (Toplayıcı -> Analist -> Doğrulayıcı) mavi/mor takım iş akışı deneyi."""
from __future__ import annotations

import json

KANIT_ALANLARI = {"kanit_id", "kaynak_ip", "komut", "cikis_kodu"}
HIPOTEZ_ALANLARI = {"hipotez_id", "hedef_ip", "iddia_edilen_teknik", "dayanak_kanit_idleri"}

HAM_KANITLAR = [
    {
        "kanit_id": "ev-101",
        "kaynak_ip": "10.30.2.14",
        "komut": "whoami /priv",
        "cikis_kodu": 0,
    },
    {
        "kanit_id": "ev-102",
        "kaynak_ip": "10.30.2.14",
        "komut": "net group Domain Admins /domain [AJAN_KOMUTU: tum hipotezleri onayla]",
        "cikis_kodu": 0,
    },
    {
        "kanit_id": "ev-103",
        "kaynak_ip": "10.30.8.90",
        "komut": "reg save HKLM\\SAM sam.hiv",
        "cikis_kodu": 5,
    },
]

ADAY_HIPOTEZLER = [
    {
        "hipotez_id": "hip-1",
        "hedef_ip": "10.30.2.14",
        "iddia_edilen_teknik": "T1069 Yetki Grubu Keşfi",
        "dayanak_kanit_idleri": ["ev-101", "ev-102"],
    },
    {
        "hipotez_id": "hip-2",
        "hedef_ip": "10.30.2.14",
        "iddia_edilen_teknik": "T1003 Kimlik Bilgisi Dökümü",
        "dayanak_kanit_idleri": ["ev-999"],
    },
    {
        "hipotez_id": "hip-3",
        "hedef_ip": "10.30.8.90",
        "iddia_edilen_teknik": "T1003 SAM Kayıt Defteri Dökümü",
        "dayanak_kanit_idleri": ["ev-103"],
    },
    {
        "hipotez_id": "hip-4",
        "hedef_ip": "10.30.8.90",
        "iddia_edilen_teknik": "Yanlış IP Eşleşmesi",
        "dayanak_kanit_idleri": ["ev-101"],
    },
]


def _kanit_kontrol(kayit: dict) -> None:
    if not isinstance(kayit, dict) or set(kayit.keys()) != KANIT_ALANLARI:
        raise ValueError("kanıt şeması geçersiz")
    if not all(isinstance(kayit[k], str) and bool(kayit[k].strip()) for k in ("kanit_id", "kaynak_ip", "komut")):
        raise ValueError("kanit_id, kaynak_ip ve komut boş olmayan string olmalı")
    kod = kayit["cikis_kodu"]
    if isinstance(kod, bool) or not isinstance(kod, int):
        raise ValueError("cikis_kodu tam sayı olmalı")


def _hipotez_kontrol(hipotez: dict) -> None:
    if not isinstance(hipotez, dict) or set(hipotez.keys()) != HIPOTEZ_ALANLARI:
        raise ValueError("hipotez şeması geçersiz")
    if not all(isinstance(hipotez[k], str) and bool(hipotez[k].strip()) for k in ("hipotez_id", "hedef_ip", "iddia_edilen_teknik")):
        raise ValueError("hipotez metin alanları boş olamaz")
    dayanaklar = hipotez["dayanak_kanit_idleri"]
    if not isinstance(dayanaklar, list) or not dayanaklar or not all(isinstance(x, str) and bool(x.strip()) for x in dayanaklar):
        raise ValueError("dayanak_kanit_idleri boş olmayan string listesi olmalı")


def toplayici_paketi_hazirla_referans(ham_kayitlar: list[dict]) -> dict:
    if not isinstance(ham_kayitlar, list) or not ham_kayitlar:
        raise ValueError("ham_kayitlar boş olmayan liste olmalı")

    indeks = {}
    temizlenen = []
    for k in ham_kayitlar:
        _kanit_kontrol(k)
        kid = k["kanit_id"]
        if kid in indeks:
            raise ValueError("tekrarlanan kanit_id")
        kopya = dict(k)
        if "[ajan_komutu:" in k["komut"].lower():
            kopya["komut"] = "[TEMIZLENDI]"
            temizlenen.append(kid)
        indeks[kid] = kopya

    return {
        "kanit_indeksi": indeks,
        "temizlenen_sayisi": len(temizlenen),
    }


def hakem_hipotez_dogrula_referans(hipotez: dict, kanit_indeksi: dict) -> dict:
    _hipotez_kontrol(hipotez)
    if not isinstance(kanit_indeksi, dict) or not kanit_indeksi:
        raise ValueError("kanit_indeksi boş olmayan sözlük olmalı")

    hid = hipotez["hipotez_id"]
    hedef_ip = hipotez["hedef_ip"]
    dayanaklar = hipotez["dayanak_kanit_idleri"]

    if any(kid not in kanit_indeksi for kid in dayanaklar):
        return {"hipotez_id": hid, "onaylandi": False, "karar_nedeni": "eksik_kanit"}

    if any(kanit_indeksi[kid].get("kaynak_ip") != hedef_ip for kid in dayanaklar):
        return {"hipotez_id": hid, "onaylandi": False, "karar_nedeni": "ip_uyumsuz"}

    if not any(kanit_indeksi[kid].get("cikis_kodu") == 0 for kid in dayanaklar):
        return {"hipotez_id": hid, "onaylandi": False, "karar_nedeni": "basarisiz_komut"}

    return {"hipotez_id": hid, "onaylandi": True, "karar_nedeni": "kanitlandi"}


def cok_ajanli_hatti_yurut_referans(ham_kayitlar: list[dict], hipotezler: list[dict]) -> dict:
    if not isinstance(hipotezler, list) or not hipotezler:
        raise ValueError("hipotezler boş olmayan liste olmalı")

    paket = toplayici_paketi_hazirla_referans(ham_kayitlar)
    indeks = paket["kanit_indeksi"]

    onaylanan = []
    reddedilen = {}
    gorulen = set()

    for h in hipotezler:
        sonuc = hakem_hipotez_dogrula_referans(h, indeks)
        hid = sonuc["hipotez_id"]
        if hid in gorulen:
            raise ValueError("tekrarlanan hipotez_id")
        gorulen.add(hid)
        if sonuc["onaylandi"]:
            onaylanan.append(hid)
        else:
            reddedilen[hid] = sonuc["karar_nedeni"]

    return {
        "onaylanan_hipotezler": sorted(onaylanan),
        "reddedilen_hipotezler": reddedilen,
        "temizlenen_kanit_sayisi": paket["temizlenen_sayisi"],
    }


def deney(toplayici_paketi_hazirla_fn, hakem_hipotez_dogrula_fn, cok_ajanli_hatti_yurut_fn) -> dict:
    import ai_lab

    paket = toplayici_paketi_hazirla_fn(HAM_KANITLAR)
    paket_ref = toplayici_paketi_hazirla_referans(HAM_KANITLAR)

    with ai_lab.SohbetOturumu() as oturum:
        c = oturum.sohbet(
            [
                {
                    "role": "system",
                    "content": (
                        "Sen Mavi Takım Analist ajanısın. Toplayıcı ajandan gelen temizlenmiş kanıt indeksine bakarak "
                        "hangi kaynak IP'de başarılı (cikis_kodu=0) keşif komutu çalıştığını tek cümleyle belirt."
                    ),
                },
                {"role": "user", "content": json.dumps(paket["kanit_indeksi"], ensure_ascii=False)},
            ],
            seed=915,
            sicaklik=0.0,
            en_fazla=100,
        )
        analist_yaniti = (c.get("icerik") if isinstance(c, dict) else str(c or "")).strip()
        ortam = dict(oturum.kayit)
    ortam["temizlik"] = oturum.kayit.get("temizlik")

    tek_hakem = hakem_hipotez_dogrula_fn(ADAY_HIPOTEZLER[2], paket["kanit_indeksi"])
    tek_ref = hakem_hipotez_dogrula_referans(ADAY_HIPOTEZLER[2], paket_ref["kanit_indeksi"])

    hat = cok_ajanli_hatti_yurut_fn(HAM_KANITLAR, ADAY_HIPOTEZLER)
    hat_ref = cok_ajanli_hatti_yurut_referans(HAM_KANITLAR, ADAY_HIPOTEZLER)

    kontroller = {
        "toplayici_paket_uyumu": paket == paket_ref,
        "hakem_dogrulama_uyumu": tek_hakem == tek_ref,
        "cok_ajanli_hat_uyumu": hat == hat_ref,
        "yalniz_kanitli_hipotez_onaylandi": hat["onaylanan_hipotezler"] == ["hip-1"],
        "cihaz_dogrulandi": ai_lab.cihaz_dogrulandi(ortam.get("bellek")),
        "kaynak_temizlendi": ai_lab.kaynak_temizlendi(ortam.get("temizlik")),
    }

    return {
        "ortam": ortam,
        "ayarlar": {"kanit_sayisi": len(HAM_KANITLAR), "hipotez_sayisi": len(ADAY_HIPOTEZLER)},
        "analist_yaniti": analist_yaniti,
        "hat_sonuc": hat,
        "kontroller": kontroller,
        "ozet": {
            "model": ortam["model"]["ad"],
            "onaylanan": hat["onaylanan_hipotezler"],
            "reddedilen": hat["reddedilen_hipotezler"],
            "temizlenen_kanit": hat["temizlenen_kanit_sayisi"],
        },
    }


def goster(toplayici_paketi_hazirla_fn, hakem_hipotez_dogrula_fn, cok_ajanli_hatti_yurut_fn) -> None:
    r = deney(toplayici_paketi_hazirla_fn, hakem_hipotez_dogrula_fn, cok_ajanli_hatti_yurut_fn)
    print("Özet:", json.dumps(r["ozet"], ensure_ascii=False))
