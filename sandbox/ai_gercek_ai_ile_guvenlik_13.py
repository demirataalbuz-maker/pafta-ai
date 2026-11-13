"""ai-ile-guvenlik-13 dersi için gerçek yerel Ollama + salt-okunur keşif ajanı ve deterministik kapsam kilidi deneyi."""
from __future__ import annotations

import json

POLITIKA = {
    "izinli_araclar": ["http_baslik_oku", "dns_kayit_sorgula", "sertifika_ozeti"],
    "izinli_hedefler": ["127.0.0.1:8080", "lab.local"],
    "azami_adim": 3,
}

ORNEK_CAGRILAR = [
    {"cagri_id": "c-1", "arac": "http_baslik_oku", "hedef": "127.0.0.1:8080"},
    {"cagri_id": "c-2", "arac": "dosya_sil", "hedef": "127.0.0.1:8080"},
    {"cagri_id": "c-3", "arac": "dns_kayit_sorgula", "hedef": "dis-sunucu.example"},
    {"cagri_id": "c-4", "arac": "sertifika_ozeti", "hedef": "lab.local"},
    {"cagri_id": "c-5", "arac": "sertifika_ozeti", "hedef": "lab.local"},
]

ARAC_SEMASI = [
    {
        "type": "function",
        "function": {
            "name": "http_baslik_oku",
            "description": "İzinli yerel hedefin HTTP güvenlik başlıklarını salt-okunur sorgular.",
            "parameters": {
                "type": "object",
                "properties": {
                    "hedef": {"type": "string", "description": "Hedef adres (ör. 127.0.0.1:8080)"},
                },
                "required": ["hedef"],
            },
        },
    }
]


def _politika_kontrol(politika: dict) -> None:
    if not isinstance(politika, dict) or set(politika.keys()) != {"izinli_araclar", "izinli_hedefler", "azami_adim"}:
        raise ValueError("politika şeması geçersiz")
    for k in ("izinli_araclar", "izinli_hedefler"):
        lst = politika[k]
        if not isinstance(lst, list) or not lst or not all(isinstance(x, str) and bool(x.strip()) for x in lst):
            raise ValueError("politika listeleri boş olmayan string listesi olmalı")
    adim = politika["azami_adim"]
    if isinstance(adim, bool) or not isinstance(adim, int) or adim <= 0:
        raise ValueError("azami_adim pozitif tam sayı olmalı")


def _cagri_kontrol(cagri: dict) -> None:
    if not isinstance(cagri, dict) or set(cagri.keys()) != {"cagri_id", "arac", "hedef"}:
        raise ValueError("çağrı şeması geçersiz")
    if not all(isinstance(cagri[k], str) and bool(cagri[k].strip()) for k in ("cagri_id", "arac", "hedef")):
        raise ValueError("çağrı alanları boş olmayan string olmalı")


def arac_cagrisi_dogrula_referans(cagri: dict, politika: dict) -> dict:
    _cagri_kontrol(cagri)
    _politika_kontrol(politika)

    cid = cagri["cagri_id"]
    if cagri["arac"] not in politika["izinli_araclar"]:
        return {"cagri_id": cid, "izin_verildi": False, "neden": "yasak_arac"}
    if cagri["hedef"] not in politika["izinli_hedefler"]:
        return {"cagri_id": cid, "izin_verildi": False, "neden": "kapsam_disi_hedef"}
    return {"cagri_id": cid, "izin_verildi": True, "neden": "onaylandi"}


def dongu_kirici_kontrol_referans(onayli_cagrilar: list[dict], azami_adim: int) -> dict:
    if not isinstance(onayli_cagrilar, list):
        raise ValueError("onayli_cagrilar liste olmalı")
    if isinstance(azami_adim, bool) or not isinstance(azami_adim, int) or azami_adim <= 0:
        raise ValueError("azami_adim pozitif tam sayı olmalı")

    kabul_edilen = []
    gorulen_anahtar = set()
    durdurma_nedeni = None

    for c in onayli_cagrilar:
        _cagri_kontrol(c)
        anahtar = (c["arac"], c["hedef"])
        if anahtar in gorulen_anahtar:
            durdurma_nedeni = "tekrar_dongusu"
            break
        if len(kabul_edilen) >= azami_adim:
            durdurma_nedeni = "butce_asimi"
            break
        gorulen_anahtar.add(anahtar)
        kabul_edilen.append(c["cagri_id"])

    return {
        "calistirilan_idleri": kabul_edilen,
        "durdurma_nedeni": durdurma_nedeni,
    }


def kesif_ajani_calistir_referans(cagrilar: list[dict], politika: dict) -> dict:
    if not isinstance(cagrilar, list) or not cagrilar:
        raise ValueError("cagrilar boş olmayan liste olmalı")
    _politika_kontrol(politika)

    onaylilar = []
    engellenenler = {}
    gorulen_id = set()

    for c in cagrilar:
        sonuc = arac_cagrisi_dogrula_referans(c, politika)
        cid = sonuc["cagri_id"]
        if cid in gorulen_id:
            raise ValueError("tekrarlanan cagri_id")
        gorulen_id.add(cid)
        if sonuc["izin_verildi"]:
            onaylilar.append(c)
        else:
            engellenenler[cid] = sonuc["neden"]

    dongu = dongu_kirici_kontrol_referans(onaylilar, politika["azami_adim"])
    return {
        "calistirilan_idleri": dongu["calistirilan_idleri"],
        "engellenenler": engellenenler,
        "durdurma_nedeni": dongu["durdurma_nedeni"],
    }


def deney(arac_cagrisi_dogrula_fn, dongu_kirici_kontrol_fn, kesif_ajani_calistir_fn) -> dict:
    import ai_lab

    with ai_lab.SohbetOturumu(araclar_gerekli=True) as oturum:
        c = oturum.sohbet(
            [
                {
                    "role": "system",
                    "content": "Sen salt-okunur bir güvenlik keşif ajanısın. Verilen yerel hedef için http_baslik_oku aracını çağır.",
                },
                {
                    "role": "user",
                    "content": "127.0.0.1:8080 adresinin HTTP başlıklarını kontrol et.",
                },
            ],
            araclar=ARAC_SEMASI,
            seed=913,
            sicaklik=0.0,
            en_fazla=120,
        )
        arac_cagrilari = c.get("arac_cagrilari") if isinstance(c, dict) else []
        ortam = dict(oturum.kayit)
    ortam["temizlik"] = oturum.kayit.get("temizlik")

    tek = arac_cagrisi_dogrula_fn(ORNEK_CAGRILAR[1], POLITIKA)
    tek_ref = arac_cagrisi_dogrula_referans(ORNEK_CAGRILAR[1], POLITIKA)

    dk = dongu_kirici_kontrol_fn([ORNEK_CAGRILAR[0], ORNEK_CAGRILAR[3], ORNEK_CAGRILAR[4]], POLITIKA["azami_adim"])
    dk_ref = dongu_kirici_kontrol_referans([ORNEK_CAGRILAR[0], ORNEK_CAGRILAR[3], ORNEK_CAGRILAR[4]], POLITIKA["azami_adim"])

    ajan = kesif_ajani_calistir_fn(ORNEK_CAGRILAR, POLITIKA)
    ajan_ref = kesif_ajani_calistir_referans(ORNEK_CAGRILAR, POLITIKA)

    kontroller = {
        "arac_dogrulama_uyumu": tek == tek_ref,
        "dongu_kirici_uyumu": dk == dk_ref,
        "ajan_calistirma_uyumu": ajan == ajan_ref,
        "yasak_arac_ve_hedef_engellendi": ajan["engellenenler"] == {"c-2": "yasak_arac", "c-3": "kapsam_disi_hedef"},
        "tekrar_dongusu_durduruldu": ajan["durdurma_nedeni"] == "tekrar_dongusu",
        "cihaz_dogrulandi": ai_lab.cihaz_dogrulandi(ortam.get("bellek")),
        "kaynak_temizlendi": ai_lab.kaynak_temizlendi(ortam.get("temizlik")),
    }

    return {
        "ortam": ortam,
        "ayarlar": {"azami_adim": POLITIKA["azami_adim"], "toplam_cagri": len(ORNEK_CAGRILAR)},
        "canli_arac_cagrilari": arac_cagrilari,
        "ajan_sonuc": ajan,
        "kontroller": kontroller,
        "ozet": {
            "model": ortam["model"]["ad"],
            "calistirilan": ajan["calistirilan_idleri"],
            "engellenenler": ajan["engellenenler"],
            "durdurma_nedeni": ajan["durdurma_nedeni"],
        },
    }


def goster(arac_cagrisi_dogrula_fn, dongu_kirici_kontrol_fn, kesif_ajani_calistir_fn) -> None:
    r = deney(arac_cagrisi_dogrula_fn, dongu_kirici_kontrol_fn, kesif_ajani_calistir_fn)
    print("Özet:", json.dumps(r["ozet"], ensure_ascii=False))
