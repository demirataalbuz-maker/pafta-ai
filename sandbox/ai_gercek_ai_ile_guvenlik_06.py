"""ai-ile-guvenlik-06 dersi için gerçek yerel Ollama + yama üretimi ve regresyon doğrulaması deneyi."""
from __future__ import annotations

import ast
import json


ZAFIYETLI_KOD = (
    "def kullanici_getir(veritabani, kullanici_adi):\n"
    "    if not kullanici_adi:\n"
    "        return None\n"
    "    sorgu = \"SELECT id, rol FROM kullanicilar WHERE ad = '\" + kullanici_adi + \"'\"\n"
    "    return veritabani.sorgula(sorgu)\n"
)

ADAY_YAMALAR = [
    {
        "yama_id": "yama-1-bozuk-sozdizimi",
        "kod": "def kullanici_getir(veritabani, kullanici_adi):\n    return veritabani.sorgula('SELECT * WHERE ad = ?', (kullanici_adi,)\n",
    },
    {
        "yama_id": "yama-2-regresyon-hatasi",
        "kod": "def kullanici_getir(veritabani, kullanici_adi):\n    return None\n",
    },
    {
        "yama_id": "yama-3-hala-zafiyetli",
        "kod": "def kullanici_getir(veritabani, kullanici_adi):\n    if not kullanici_adi:\n        return None\n    sorgu = f\"SELECT id, rol FROM kullanicilar WHERE ad = '{kullanici_adi}'\"\n    return veritabani.sorgula(sorgu)\n",
    },
    {
        "yama_id": "yama-4-parametrik-ve-gecerli",
        "kod": "def kullanici_getir(veritabani, kullanici_adi):\n    if not kullanici_adi:\n        return None\n    return veritabani.sorgula(\"SELECT id, rol FROM kullanicilar WHERE ad = ?\", (kullanici_adi,))\n",
    },
]


class SahteVeritabani:
    def __init__(self):
        self.son_sorgu = None
        self.son_parametreler = None
        self.kayitlar = {"ayse": {"id": 1, "rol": "analist"}, "mehmet": {"id": 2, "rol": "yonetici"}}

    def sorgula(self, sorgu, parametreler=None):
        self.son_sorgu = sorgu
        self.son_parametreler = parametreler
        if parametreler is not None:
            if not isinstance(parametreler, tuple) or not parametreler:
                return None
            ad = parametreler[0]
            return self.kayitlar.get(ad)
        if "OR 'a'='a'" in str(sorgu) or "OR '1'='1'" in str(sorgu):
            return {"id": 999, "rol": "sizinti"}
        for ad, kayit in self.kayitlar.items():
            if f"'{ad}'" in str(sorgu):
                return kayit
        return None


def yama_ast_kontrolu_referans(yama_kodu: str) -> dict:
    if not isinstance(yama_kodu, str) or not yama_kodu.strip():
        raise ValueError("yama_kodu boş olmayan string olmalı")
    try:
        agac = ast.parse(yama_kodu)
    except SyntaxError:
        return {
            "sozdizimi_gecerli": False,
            "parametrik_cagri": False,
            "dinamik_birlestirme_var": False,
        }

    parametrik_cagri = False
    dinamik_birlestirme_var = False

    for dugum in ast.walk(agac):
        if isinstance(dugum, (ast.BinOp, ast.JoinedStr)):
            dinamik_birlestirme_var = True
        if isinstance(dugum, ast.Call) and isinstance(dugum.func, ast.Attribute):
            if dugum.func.attr == "sorgula":
                if len(dugum.args) == 2 and isinstance(dugum.args[0], ast.Constant):
                    parametrik_cagri = True

    return {
        "sozdizimi_gecerli": True,
        "parametrik_cagri": parametrik_cagri,
        "dinamik_birlestirme_var": dinamik_birlestirme_var,
    }


def yama_test_kosumu_referans(yama_kodu: str) -> dict:
    ast_sonuc = yama_ast_kontrolu_referans(yama_kodu)
    if not ast_sonuc["sozdizimi_gecerli"]:
        return {
            "sozdizimi_gecerli": False,
            "regresyon_gecti": False,
            "guvenlik_gecti": False,
        }

    alan: dict = {}
    try:
        exec(yama_kodu, {}, alan)
        fn = alan.get("kullanici_getir")
        if not callable(fn):
            return {
                "sozdizimi_gecerli": True,
                "regresyon_gecti": False,
                "guvenlik_gecti": False,
            }
        vt1 = SahteVeritabani()
        r_ayse = fn(vt1, "ayse")
        r_bos = fn(vt1, "")
        regresyon_gecti = (r_ayse == {"id": 1, "rol": "analist"}) and (r_bos is None)

        vt2 = SahteVeritabani()
        saldiri = "' OR 'a'='a'"
        r_saldiri = fn(vt2, saldiri)
        guvenlik_gecti = (
            ast_sonuc["parametrik_cagri"]
            and not ast_sonuc["dinamik_birlestirme_var"]
            and r_saldiri is None
            and vt2.son_parametreler == (saldiri,)
        )
    except Exception:
        return {
            "sozdizimi_gecerli": True,
            "regresyon_gecti": False,
            "guvenlik_gecti": False,
        }

    return {
        "sozdizimi_gecerli": True,
        "regresyon_gecti": bool(regresyon_gecti),
        "guvenlik_gecti": bool(guvenlik_gecti),
    }


def aday_yamalari_denetle_referans(adaylar: list[dict]) -> dict:
    if not isinstance(adaylar, list) or not adaylar:
        raise ValueError("adaylar boş olamaz")

    gorulen = set()
    kabul_edilenler = []
    reddedilenler = {}

    for aday in adaylar:
        if not isinstance(aday, dict) or set(aday.keys()) != {"yama_id", "kod"}:
            raise ValueError("aday şeması geçersiz")
        yid = aday["yama_id"]
        kod = aday["kod"]
        if not isinstance(yid, str) or not yid.strip() or yid in gorulen:
            raise ValueError("yama_id geçersiz veya tekrarlı")
        gorulen.add(yid)

        sonuc = yama_test_kosumu_referans(kod)
        if not sonuc["sozdizimi_gecerli"]:
            reddedilenler[yid] = "sozdizimi_hatasi"
        elif not sonuc["regresyon_gecti"]:
            reddedilenler[yid] = "regresyon_hatasi"
        elif not sonuc["guvenlik_gecti"]:
            reddedilenler[yid] = "guvenlik_hatasi"
        else:
            kabul_edilenler.append(yid)

    return {
        "kabul_edilen_yamalar": sorted(kabul_edilenler),
        "reddedilen_yamalar": reddedilenler,
        "kabul_sayisi": len(kabul_edilenler),
    }


def deney(yama_ast_kontrolu_fn, yama_test_kosumu_fn, aday_yamalari_denetle_fn) -> dict:
    import ai_lab

    with ai_lab.SohbetOturumu() as oturum:
        c = oturum.sohbet(
            [
                {
                    "role": "system",
                    "content": (
                        "Sen güvenli kod yama asistanısın. "
                        "SQL birleştirmesini parametrik sorguya (`veritabani.sorgula(sorgu, (kullanici_adi,))`) dönüştür."
                    ),
                },
                {"role": "user", "content": ZAFIYETLI_KOD},
            ],
            seed=906,
            sicaklik=0.0,
            en_fazla=140,
        )
        canli_yanit = (c.get("icerik") if isinstance(c, dict) else str(c or "")).strip()
        ortam = dict(oturum.kayit)
    ortam["temizlik"] = oturum.kayit.get("temizlik")

    denetim = aday_yamalari_denetle_fn(ADAY_YAMALAR)
    denetim_ref = aday_yamalari_denetle_referans(ADAY_YAMALAR)

    kontroller = {
        "ast_kontrol_uyumu": yama_ast_kontrolu_fn(ADAY_YAMALAR[3]["kod"]) == yama_ast_kontrolu_referans(ADAY_YAMALAR[3]["kod"]),
        "test_kosumu_uyumu": yama_test_kosumu_fn(ADAY_YAMALAR[3]["kod"]) == yama_test_kosumu_referans(ADAY_YAMALAR[3]["kod"]),
        "denetim_uyumu": denetim == denetim_ref,
        "yalniz_gecerli_yama_kabul_edildi": denetim["kabul_edilen_yamalar"] == ["yama-4-parametrik-ve-gecerli"],
        "cihaz_dogrulandi": ai_lab.cihaz_dogrulandi(ortam.get("bellek")),
        "kaynak_temizlendi": ai_lab.kaynak_temizlendi(ortam.get("temizlik")),
    }

    return {
        "ortam": ortam,
        "ayarlar": {"aday_sayisi": len(ADAY_YAMALAR)},
        "canli_yanit": canli_yanit,
        "denetim": denetim,
        "kontroller": kontroller,
        "ozet": {
            "model": ortam["model"]["ad"],
            "kabul_edilen": denetim["kabul_edilen_yamalar"],
            "reddedilen": denetim["reddedilen_yamalar"],
        },
    }


def goster(yama_ast_kontrolu_fn, yama_test_kosumu_fn, aday_yamalari_denetle_fn) -> None:
    r = deney(yama_ast_kontrolu_fn, yama_test_kosumu_fn, aday_yamalari_denetle_fn)
    print("Özet:", json.dumps(r["ozet"], ensure_ascii=False))
