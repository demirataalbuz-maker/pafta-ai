"""ai-ile-guvenlik-07 dersi için gerçek yerel HTTP sunucusu + Ollama kapsam kilitli keşif deneyi."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse
from urllib.request import urlopen

IZINLI_ADRESLER = ("127.0.0.1", "localhost")


def kapsam_kilidi_dogrula_referans(url: str) -> dict:
    if not isinstance(url, str) or not url.strip():
        raise ValueError("url boş olmayan string olmalı")
    p = urlparse(url.strip())
    sema = p.scheme.lower()
    host = (p.hostname or "").lower()
    yol = p.path if p.path else "/"

    izinli = (
        sema in ("http", "https")
        and host in IZINLI_ADRESLER
        and not p.username
        and not p.password
    )
    return {
        "izinli": bool(izinli),
        "sema": sema,
        "host": host,
        "yol": yol,
    }


def url_parametre_haritasi_referans(url: str) -> dict:
    kapsam = kapsam_kilidi_dogrula_referans(url)
    if not kapsam["izinli"]:
        raise ValueError("kapsam dışı URL haritalanamaz")
    p = urlparse(url.strip())
    sorgu = parse_qs(p.query, keep_blank_values=True)
    parametreler = sorted(sorgu.keys())
    return {
        "yol": kapsam["yol"],
        "parametreler": parametreler,
        "parametre_sayisi": len(parametreler),
    }


def guvenli_kesif_plani_referans(aday_urller: list[str], model_oncelikleri: dict[str, str]) -> dict:
    if not isinstance(aday_urller, list) or not aday_urller:
        raise ValueError("aday_urller boş olamaz")
    if not isinstance(model_oncelikleri, dict):
        raise ValueError("model_oncelikleri sözlük olmalı")

    plan = []
    engellenen_urller = []
    gorulen_yollar = set()

    for u in aday_urller:
        k = kapsam_kilidi_dogrula_referans(u)
        if not k["izinli"]:
            engellenen_urller.append(u)
            continue
        harita = url_parametre_haritasi_referans(u)
        yol = harita["yol"]
        if yol in gorulen_yollar:
            continue
        gorulen_yollar.add(yol)

        if yol not in model_oncelikleri:
            raise ValueError("izinli uç nokta için model önceliği eksik")
        oncelik = model_oncelikleri[yol]
        if oncelik not in ("yuksek", "orta", "dusuk"):
            raise ValueError("model önceliği geçersiz")

        plan.append({
            "yol": yol,
            "parametreler": harita["parametreler"],
            "oncelik": oncelik,
        })

    plan.sort(key=lambda x: x["yol"])
    return {
        "izinli_hedefler": plan,
        "engellenen_urller": engellenen_urller,
        "engellenen_sayisi": len(engellenen_urller),
    }


class _YerelKeşifHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        veri = {
            "servis": "yerel-kesif-testi",
            "uc_noktalar": [
                "/api/kullanici?id=10&rol=analist",
                "/api/ara?q=test&sayfa=1",
                "/api/profil",
            ],
        }
        govde = json.dumps(veri, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(govde)))
        self.end_headers()
        self.wfile.write(govde)

    def log_message(self, format, *args):
        return


def deney(kapsam_kilidi_dogrula_fn, url_parametre_haritasi_fn, guvenli_kesif_plani_fn) -> dict:
    import ai_lab

    sunucu = HTTPServer(("127.0.0.1", 0), _YerelKeşifHandler)
    port = sunucu.server_port
    ip_t = threading.Thread(target=sunucu.serve_forever, daemon=True)
    ip_t.start()

    try:
        baz_url = f"http://127.0.0.1:{port}/api/kesif"
        assert kapsam_kilidi_dogrula_fn(baz_url)["izinli"] is True
        with urlopen(baz_url, timeout=5) as yanit:
            kesif_json = json.loads(yanit.read().decode("utf-8"))
    finally:
        sunucu.shutdown()
        sunucu.server_close()

    aday_urller = [f"http://127.0.0.1:{port}{u}" for u in kesif_json["uc_noktalar"]] + [
        "https://dis-hedef.ornek.com/admin?debug=true",
        "http://169.254.169.254/latest/meta-data/",
    ]

    with ai_lab.SohbetOturumu() as oturum:
        c = oturum.sohbet(
            [
                {
                    "role": "system",
                    "content": "Sen kapsam kilitli uygulama güvenliği keşif asistanısın. Uç noktaları önceliklendir.",
                },
                {
                    "role": "user",
                    "content": json.dumps(kesif_json["uc_noktalar"], ensure_ascii=False),
                },
            ],
            seed=907,
            sicaklik=0.0,
            en_fazla=100,
        )
        canli_yanit = (c.get("icerik") if isinstance(c, dict) else str(c or "")).strip()
        ortam = dict(oturum.kayit)
    ortam["temizlik"] = oturum.kayit.get("temizlik")

    model_oncelikleri = {
        "/api/kullanici": "yuksek",
        "/api/ara": "orta",
        "/api/profil": "dusuk",
    }
    plan = guvenli_kesif_plani_fn(aday_urller, model_oncelikleri)
    plan_ref = guvenli_kesif_plani_referans(aday_urller, model_oncelikleri)

    kontroller = {
        "yerel_http_kesif_basarili": len(kesif_json["uc_noktalar"]) == 3,
        "dis_ve_metadata_engellendi": plan["engellenen_sayisi"] == 2,
        "parametre_haritasi_dogru": url_parametre_haritasi_fn(aday_urller[0]) == url_parametre_haritasi_referans(aday_urller[0]),
        "kesif_plani_referansla_uyumlu": plan == plan_ref,
        "cihaz_dogrulandi": ai_lab.cihaz_dogrulandi(ortam.get("bellek")),
        "kaynak_temizlendi": ai_lab.kaynak_temizlendi(ortam.get("temizlik")),
    }

    return {
        "ortam": ortam,
        "ayarlar": {"port": port, "izinli_adresler": list(IZINLI_ADRESLER)},
        "canli_yanit": canli_yanit,
        "plan": plan,
        "kontroller": kontroller,
        "ozet": {
            "model": ortam["model"]["ad"],
            "izinli_hedef_sayisi": len(plan["izinli_hedefler"]),
            "engellenen_sayisi": plan["engellenen_sayisi"],
        },
    }


def goster(kapsam_kilidi_dogrula_fn, url_parametre_haritasi_fn, guvenli_kesif_plani_fn) -> None:
    r = deney(kapsam_kilidi_dogrula_fn, url_parametre_haritasi_fn, guvenli_kesif_plani_fn)
    print("Özet:", json.dumps(r["ozet"], ensure_ascii=False))
