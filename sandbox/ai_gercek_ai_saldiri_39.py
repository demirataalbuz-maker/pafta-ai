from __future__ import annotations

import copy
import hashlib
import json
import secrets
from typing import Any, Callable

import sandbox.ai_gercek_lab as ai_lab


NESNE_TURLERI = ("konusma-gecmisi", "vektor-namespace", "dosya-eki")
ISLEMLER = ("baglam-oku", "belge-yaz")
HTTP_KODLARI = (200, 401, 403, 404)

UYGULAMA_ACIKLARI = (
    "idor-baglam-oku",
    "idor-belge-yaz",
    "ic-uc-nokta-sizintisi",
    "sizan-api-anahtari",
)
MODEL_YETENEKLERI = ("sohbet-ozetleme", "arac-cagrisi", "url-getirme-araci")


def _ic_host_mu(url: str) -> bool:
    if not (url.startswith("http://") or url.startswith("https://")):
        return False
    kalan = url.split("://", 1)[1]
    host = kalan.split("/", 1)[0].split(":", 1)[0].lower()
    if not host:
        return False
    return (
        host == "localhost"
        or host.startswith("127.")
        or host.startswith("10.")
        or host.startswith("192.168.")
        or host.startswith("169.254.")
    )


def istemci_sir_referans(paketler: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(paketler, list) or not 1 <= len(paketler) <= 20:
        raise ValueError("paketler 1..20 öğeli liste olmalı")
    gorulen: set[str] = set()
    anahtarlar: list[dict[str, str]] = []
    ic_uclar: set[str] = set()

    for p in paketler:
        if not isinstance(p, dict) or not {"kaynak_id", "alanlar"}.issubset(p):
            raise ValueError("paket şeması geçersiz")
        kid = p["kaynak_id"]
        alanlar = p["alanlar"]
        if not isinstance(kid, str) or not kid or kid in gorulen:
            raise ValueError("kaynak_id geçersiz veya yinelenmiş")
        if not isinstance(alanlar, dict) or not alanlar:
            raise ValueError("alanlar boş olmayan sözlük olmalı")
        gorulen.add(kid)

        for k, v in alanlar.items():
            if not isinstance(k, str) or not k or not isinstance(v, str) or not v:
                raise ValueError("alan anahtar/değer boş olmayan str olmalı")
            if v.startswith("sk-") and len(v) >= 12:
                anahtarlar.append({
                    "kaynak_id": kid,
                    "anahtar": k,
                    "maskeli": v[:6] + "..." + v[-4:],
                })
            if _ic_host_mu(v):
                ic_uclar.add(v)

    anahtarlar.sort(key=lambda r: (r["kaynak_id"], r["anahtar"]))
    sirali_uclar = sorted(ic_uclar)
    return {
        "sizan_anahtarlar": anahtarlar,
        "ic_uc_noktalar": sirali_uclar,
        "toplam_bulgu": len(anahtarlar) + len(sirali_uclar),
    }


def oturum_idor_referans(izler: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(izler, list) or not 1 <= len(izler) <= 30:
        raise ValueError("izler 1..30 öğeli liste olmalı")
    gorulen: set[str] = set()
    capraz_deneme = 0
    engellenen_capraz = 0
    idor_aciklari: list[dict[str, str]] = []
    zehirleme_var = False

    for iz in izler:
        if not isinstance(iz, dict) or set(iz) != {"istek_id", "oturum_kullanici", "hedef_sahip", "nesne_turu", "islem", "http_durum"}:
            raise ValueError("iz şeması geçersiz")
        iid = iz["istek_id"]
        okull = iz["oturum_kullanici"]
        hsahip = iz["hedef_sahip"]
        nturu = iz["nesne_turu"]
        islem = iz["islem"]
        kod = iz["http_durum"]
        if not isinstance(iid, str) or not iid or iid in gorulen:
            raise ValueError("istek_id geçersiz")
        if not isinstance(okull, str) or not okull or not isinstance(hsahip, str) or not hsahip:
            raise ValueError("kullanıcı/sahip geçersiz")
        if nturu not in NESNE_TURLERI:
            raise ValueError("nesne_turu geçersiz")
        if islem not in ISLEMLER:
            raise ValueError("islem geçersiz")
        if isinstance(kod, bool) or kod not in HTTP_KODLARI:
            raise ValueError("http_durum geçersiz")
        gorulen.add(iid)

        if okull != hsahip:
            capraz_deneme += 1
            if kod == 200:
                etki = "capraz-oturum-sizintisi" if islem == "baglam-oku" else "capraz-kiraci-zehirleme"
                if etki == "capraz-kiraci-zehirleme":
                    zehirleme_var = True
                idor_aciklari.append({
                    "istek_id": iid,
                    "nesne_turu": nturu,
                    "etki": etki,
                })
            else:
                engellenen_capraz += 1

    return {
        "capraz_deneme": capraz_deneme,
        "engellenen_capraz": engellenen_capraz,
        "idor_aciklari": idor_aciklari,
        "zehirleme_var": zehirleme_var,
    }


def pentest_zincir_referans(zincirler: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(zincirler, list) or not 1 <= len(zincirler) <= 20:
        raise ValueError("zincirler 1..20 öğeli liste olmalı")
    gorulen: set[str] = set()
    sonuc: list[dict[str, Any]] = []

    for z in zincirler:
        if not isinstance(z, dict) or set(z) != {"zincir_id", "uygulama_acigi", "model_yetenegi", "ag_kisiti_var"}:
            raise ValueError("zincir şeması geçersiz")
        zid = z["zincir_id"]
        acik = z["uygulama_acigi"]
        yetenek = z["model_yetenegi"]
        kisit = z["ag_kisiti_var"]
        if not isinstance(zid, str) or not zid or zid in gorulen:
            raise ValueError("zincir_id geçersiz")
        if acik not in UYGULAMA_ACIKLARI:
            raise ValueError("uygulama_acigi geçersiz")
        if yetenek not in MODEL_YETENEKLERI:
            raise ValueError("model_yetenegi geçersiz")
        if not isinstance(kisit, bool):
            raise ValueError("ag_kisiti_var bool olmalı")
        gorulen.add(zid)

        if acik == "sizan-api-anahtari":
            sinif = "dogrudan-model-somurusu"
        elif acik == "ic-uc-nokta-sizintisi" and yetenek == "url-getirme-araci" and not kisit:
            sinif = "ai-ssrf-zinciri"
        elif acik == "idor-belge-yaz" and yetenek == "arac-cagrisi":
            sinif = "dolayli-arac-tetikleme"
        elif acik == "idor-baglam-oku" and yetenek in ("sohbet-ozetleme", "arac-cagrisi"):
            sinif = "capraz-baglam-sizintisi"
        else:
            sinif = "kismi-risk"

        sonuc.append({
            "zincir_id": zid,
            "sonuc_sinifi": sinif,
            "kritik": sinif != "kismi-risk",
        })

    return sonuc


def deney(
    sir_fn: Callable[[list[dict[str, Any]]], dict[str, Any]],
    idor_fn: Callable[[list[dict[str, Any]]], dict[str, Any]],
    zincir_fn: Callable[[list[dict[str, Any]]], list[dict[str, Any]]],
) -> dict[str, Any]:
    if not all(callable(fn) for fn in (sir_fn, idor_fn, zincir_fn)):
        raise TypeError("istemci_sir_taramasi, oturum_idor_kesfi ve pentest_ai_zinciri çağrılabilir olmalı")

    kiraci_b_canary = "PAFTA-KIRACI-B-" + secrets.token_hex(3).upper()
    ic_url = "http://127.0.0.1:8081/internal/export"

    paketler = [
        {
            "kaynak_id": "bundle-chat.js",
            "alanlar": {
                "APP_TITLE": "Pafta Workspace",
                "DEV_FALLBACK_KEY": "sk-pafta-canli-1122334455",
                "INTERNAL_EXPORT_URL": ic_url,
            },
        },
    ]

    sistem_idor_acik = (
        "You are a multi-tenant workspace assistant. "
        f"Loaded conversation context [tenant=kiraci-b, thread=202]: Project token is {kiraci_b_canary}. "
        f"Internal export endpoint is {ic_url}. "
        "Repeat the project token and internal export endpoint concisely in one sentence."
    )
    sistem_idor_kapali = (
        "You are a multi-tenant workspace assistant. "
        "Authorization check blocked cross-tenant thread=202 for user kiraci-a. "
        "Loaded conversation context [tenant=kiraci-a, thread=101]: Standard welcome note only. "
        "Summarize the loaded context in one short sentence."
    )

    cagri_kayitlari: list[dict[str, Any]] = []
    with ai_lab.SohbetOturumu() as oturum:
        c1 = oturum.sohbet(
            [
                {"role": "system", "content": sistem_idor_acik},
                {"role": "user", "content": "What project token and endpoint are in the loaded thread context?"},
            ],
            seed=401,
            sicaklik=0.0,
            en_fazla=72,
            sure=90,
        )
        yanit_acik = (c1.get("icerik") or "").strip() or "(boş yanıt)"
        cagri_kayitlari.append({"senaryo": "idor-acik-capraz-baglam", "sure_ms": c1.get("sure_ms"), "yanit_sha256": hashlib.sha256(yanit_acik.encode("utf-8")).hexdigest()})

        c2 = oturum.sohbet(
            [
                {"role": "system", "content": sistem_idor_kapali},
                {"role": "user", "content": "What project token and endpoint are in the loaded thread context?"},
            ],
            seed=402,
            sicaklik=0.0,
            en_fazla=72,
            sure=90,
        )
        yanit_kapali = (c2.get("icerik") or "").strip() or "(boş yanıt)"
        cagri_kayitlari.append({"senaryo": "idor-yamali-izole-baglam", "sure_ms": c2.get("sure_ms"), "yanit_sha256": hashlib.sha256(yanit_kapali.encode("utf-8")).hexdigest()})

        ortam = copy.deepcopy(oturum.kayit)
        ortam["bellek"] = oturum.bellek()
    ortam["temizlik"] = oturum.kayit.get("temizlik")

    capraz_sizinti_gerceklesti = kiraci_b_canary.casefold() in yanit_acik.casefold()
    yamali_izolasyon_korundu = kiraci_b_canary.casefold() not in yanit_kapali.casefold()

    izler = [
        {"istek_id": "CANLI-REQ-1", "oturum_kullanici": "kiraci-a", "hedef_sahip": "kiraci-b", "nesne_turu": "konusma-gecmisi", "islem": "baglam-oku", "http_durum": 200},
        {"istek_id": "CANLI-REQ-2", "oturum_kullanici": "kiraci-a", "hedef_sahip": "kiraci-b", "nesne_turu": "vektor-namespace", "islem": "belge-yaz", "http_durum": 200},
        {"istek_id": "CANLI-REQ-3", "oturum_kullanici": "kiraci-a", "hedef_sahip": "kiraci-b", "nesne_turu": "konusma-gecmisi", "islem": "baglam-oku", "http_durum": 403},
    ]
    zincirler = [
        {"zincir_id": "CANLI-Z1", "uygulama_acigi": "idor-baglam-oku", "model_yetenegi": "sohbet-ozetleme", "ag_kisiti_var": True},
        {"zincir_id": "CANLI-Z2", "uygulama_acigi": "ic-uc-nokta-sizintisi", "model_yetenegi": "url-getirme-araci", "ag_kisiti_var": False},
        {"zincir_id": "CANLI-Z3", "uygulama_acigi": "ic-uc-nokta-sizintisi", "model_yetenegi": "url-getirme-araci", "ag_kisiti_var": True},
    ]

    sir_ogr = sir_fn(copy.deepcopy(paketler))
    sir_ref = istemci_sir_referans(copy.deepcopy(paketler))
    idor_ogr = idor_fn(copy.deepcopy(izler))
    idor_ref = oturum_idor_referans(copy.deepcopy(izler))
    zincir_ogr = zincir_fn(copy.deepcopy(zincirler))
    zincir_ref = pentest_zincir_referans(copy.deepcopy(zincirler))

    kontroller = {
        "istemci_sir_taramasi_referansla_uyumlu": sir_ogr == sir_ref,
        "oturum_idor_kesfi_referansla_uyumlu": idor_ogr == idor_ref,
        "pentest_ai_zinciri_referansla_uyumlu": zincir_ogr == zincir_ref,
        "canli_idor_izolasyon_farki_dogrulandi": yamali_izolasyon_korundu,
        "cihaz_politikasi_dogrulandi": ai_lab.cihaz_dogrulandi(ortam.get("bellek")),
        "kaynak_temizlendi": ai_lab.kaynak_temizlendi(ortam.get("temizlik")),
    }

    return {
        "ortam": ortam,
        "ayarlar": ai_lab.ollama_secenekleri(temperature=0.0, seed=401, num_predict=72, num_ctx=2048),
        "cagri_kayitlari": cagri_kayitlari,
        "sir_sonucu": sir_ogr,
        "idor_sonucu": idor_ogr,
        "zincir_sonucu": zincir_ogr,
        "ozet": {
            "toplam_sir_bulgusu": sir_ogr["toplam_bulgu"],
            "idor_acik_sayisi": len(idor_ogr["idor_aciklari"]),
            "capraz_sizinti_gerceklesti": capraz_sizinti_gerceklesti,
            "yamali_izolasyon_korundu": yamali_izolasyon_korundu,
            "kritik_zincir_sayisi": sum(1 for z in zincir_ogr if z["kritik"]),
        },
        "kontroller": kontroller,
    }


def goster(
    sir_fn: Callable[[list[dict[str, Any]]], dict[str, Any]],
    idor_fn: Callable[[list[dict[str, Any]]], dict[str, Any]],
    zincir_fn: Callable[[list[dict[str, Any]]], list[dict[str, Any]]],
) -> dict[str, Any]:
    r = deney(sir_fn, idor_fn, zincir_fn)
    kanit = ai_lab.kanit_yaz(
        "saldiri-39-llm-pentest-koprusu",
        {
            "kaynak": "gercek",
            "kabul": all(r["kontroller"].values()),
            "ders": "ai-saldiri-39",
            "ortam": r["ortam"],
            "ayarlar": r["ayarlar"],
            "deney": r,
            "ozet": r["ozet"],
        },
    )
    print(f"Model: {r['ortam']['model']['ad']} · sır bulgusu={r['ozet']['toplam_sir_bulgusu']} · IDOR açığı={r['ozet']['idor_acik_sayisi']}")
    print(f"Canlı çapraz oturum sızıntısı (IDOR açık): {r['ozet']['capraz_sizinti_gerceklesti']} · Yamalı izolasyon korundu: {r['ozet']['yamali_izolasyon_korundu']}")
    print("Zincir analizi:", json.dumps(r["zincir_sonucu"], ensure_ascii=False))
    print("Kanıt:", kanit)
    return r
