"""ai-ile-guvenlik-14 dersi için gerçek yerel Ollama + yıkıcı eylemlerde insan onayı (HITL) ve imzalı görev kapısı deneyi."""
from __future__ import annotations

import hashlib
import hmac
import json

GIZLI_ANAHTAR = "pafta-hitl-sentetik-anahtar-2026"
ZORUNLU_ALANLAR = {"istek_id", "arac", "hedef", "risk_sinifi", "onay_jetonu"}


def gorev_imzasi_uret_referans(istek_id: str, arac: str, hedef: str, gizli_anahtar: str) -> str:
    if not all(isinstance(x, str) and bool(x.strip()) for x in (istek_id, arac, hedef, gizli_anahtar)):
        raise ValueError("istek_id, arac, hedef ve gizli_anahtar boş olmayan string olmalı")
    mesaj = json.dumps(["pafta-hitl-v2", istek_id, arac, hedef], ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    anahtar = gizli_anahtar.encode("utf-8")
    return hmac.new(anahtar, mesaj, hashlib.sha256).hexdigest()


ORNEK_ISTEKLER = [
    {
        "istek_id": "req-101",
        "arac": "oturum_listele",
        "hedef": "10.20.9.88",
        "risk_sinifi": "salt_okunur",
        "onay_jetonu": "",
    },
    {
        "istek_id": "req-102",
        "arac": "ip_engelle",
        "hedef": "10.20.9.88",
        "risk_sinifi": "yikici",
        "onay_jetonu": gorev_imzasi_uret_referans("req-102", "ip_engelle", "10.20.9.88", GIZLI_ANAHTAR),
    },
    {
        "istek_id": "req-103",
        "arac": "hesap_kapat",
        "hedef": "svc_backup",
        "risk_sinifi": "yikici",
        "onay_jetonu": "",
    },
    {
        "istek_id": "req-104",
        "arac": "ip_engelle",
        "hedef": "10.20.1.1",
        "risk_sinifi": "yikici",
        "onay_jetonu": gorev_imzasi_uret_referans("req-102", "ip_engelle", "10.20.9.88", GIZLI_ANAHTAR),
    },
]


def _istek_kontrol(istek: dict) -> None:
    if not isinstance(istek, dict) or set(istek.keys()) != ZORUNLU_ALANLAR:
        raise ValueError("istek şeması geçersiz")
    if not all(isinstance(istek[k], str) and bool(istek[k].strip()) for k in ("istek_id", "arac", "hedef")):
        raise ValueError("istek_id, arac ve hedef boş olmayan string olmalı")
    if istek["risk_sinifi"] not in ("salt_okunur", "yikici"):
        raise ValueError("geçersiz risk_sinifi")
    if not isinstance(istek["onay_jetonu"], str):
        raise ValueError("onay_jetonu string olmalı")


def hitl_kapisi_dogrula_referans(istek: dict, gizli_anahtar: str) -> dict:
    _istek_kontrol(istek)
    if not isinstance(gizli_anahtar, str) or not gizli_anahtar.strip():
        raise ValueError("gizli_anahtar boş olmayan string olmalı")

    iid = istek["istek_id"]
    if istek["risk_sinifi"] == "salt_okunur":
        return {"istek_id": iid, "izin_verildi": True, "neden": "salt_okunur_serbest"}

    jeton = istek["onay_jetonu"].strip()
    if not jeton:
        return {"istek_id": iid, "izin_verildi": False, "neden": "eksik_onay_jetonu"}

    beklenen = gorev_imzasi_uret_referans(iid, istek["arac"], istek["hedef"], gizli_anahtar)
    if not jeton.isascii() or not hmac.compare_digest(jeton, beklenen):
        return {"istek_id": iid, "izin_verildi": False, "neden": "imza_uyumsuz"}

    return {"istek_id": iid, "izin_verildi": True, "neden": "imzali_onay_gecerli"}


def mudahale_kuyrugu_yurut_referans(istekler: list[dict], gizli_anahtar: str) -> dict:
    if not isinstance(istekler, list) or not istekler:
        raise ValueError("istekler boş olmayan liste olmalı")
    if not isinstance(gizli_anahtar, str) or not gizli_anahtar.strip():
        raise ValueError("gizli_anahtar boş olmayan string olmalı")

    uygulanan = []
    reddedilen = {}
    gorulen = set()

    for ist in istekler:
        sonuc = hitl_kapisi_dogrula_referans(ist, gizli_anahtar)
        iid = sonuc["istek_id"]
        if iid in gorulen:
            raise ValueError("tekrarlanan istek_id")
        gorulen.add(iid)
        if sonuc["izin_verildi"]:
            uygulanan.append(iid)
        else:
            reddedilen[iid] = sonuc["neden"]

    return {
        "uygulanan_idleri": uygulanan,
        "reddedilenler": reddedilen,
    }


def deney(gorev_imzasi_uret_fn, hitl_kapisi_dogrula_fn, mudahale_kuyrugu_yurut_fn) -> dict:
    import ai_lab

    with ai_lab.SohbetOturumu() as oturum:
        c = oturum.sohbet(
            [
                {
                    "role": "system",
                    "content": (
                        "Sen bir olay müdahale asistanısın. Yıkıcı eylemlerin (ip_engelle, hesap_kapat) neden parametreye bağlı "
                        "HMAC-SHA256 insan onayı jetonu olmadan yürütülmemesi gerektiğini tek cümleyle açıkla."
                    ),
                },
                {"role": "user", "content": "Saldırgan 10.20.9.88 yerine 10.20.1.1 ağ geçidini engellemeye çalışıyor."},
            ],
            seed=914,
            sicaklik=0.0,
            en_fazla=100,
        )
        canli_yanit = (c.get("icerik") if isinstance(c, dict) else str(c or "")).strip()
        ortam = dict(oturum.kayit)
    ortam["temizlik"] = oturum.kayit.get("temizlik")

    imza = gorev_imzasi_uret_fn("req-102", "ip_engelle", "10.20.9.88", GIZLI_ANAHTAR)
    imza_ref = gorev_imzasi_uret_referans("req-102", "ip_engelle", "10.20.9.88", GIZLI_ANAHTAR)

    kapi = hitl_kapisi_dogrula_fn(ORNEK_ISTEKLER[3], GIZLI_ANAHTAR)
    kapi_ref = hitl_kapisi_dogrula_referans(ORNEK_ISTEKLER[3], GIZLI_ANAHTAR)

    kuyruk = mudahale_kuyrugu_yurut_fn(ORNEK_ISTEKLER, GIZLI_ANAHTAR)
    kuyruk_ref = mudahale_kuyrugu_yurut_referans(ORNEK_ISTEKLER, GIZLI_ANAHTAR)

    kontroller = {
        "imza_uretim_uyumu": imza == imza_ref,
        "hitl_kapi_uyumu": kapi == kapi_ref,
        "kuyruk_yurutme_uyumu": kuyruk == kuyruk_ref,
        "onaysiz_ve_degistirilmis_istekler_reddedildi": kuyruk["reddedilenler"] == {
            "req-103": "eksik_onay_jetonu",
            "req-104": "imza_uyumsuz",
        },
        "cihaz_dogrulandi": ai_lab.cihaz_dogrulandi(ortam.get("bellek")),
        "kaynak_temizlendi": ai_lab.kaynak_temizlendi(ortam.get("temizlik")),
    }

    return {
        "ortam": ortam,
        "ayarlar": {"istek_sayisi": len(ORNEK_ISTEKLER)},
        "canli_yanit": canli_yanit,
        "kuyruk_sonuc": kuyruk,
        "kontroller": kontroller,
        "ozet": {
            "model": ortam["model"]["ad"],
            "uygulanan": kuyruk["uygulanan_idleri"],
            "reddedilenler": kuyruk["reddedilenler"],
        },
    }


def goster(gorev_imzasi_uret_fn, hitl_kapisi_dogrula_fn, mudahale_kuyrugu_yurut_fn) -> None:
    r = deney(gorev_imzasi_uret_fn, hitl_kapisi_dogrula_fn, mudahale_kuyrugu_yurut_fn)
    print("Özet:", json.dumps(r["ozet"], ensure_ascii=False))
