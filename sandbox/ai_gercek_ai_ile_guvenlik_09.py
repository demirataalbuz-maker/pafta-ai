"""ai-ile-guvenlik-09 dersi için gerçek Playwright Chromium + DOM güvenlik denetimi deneyi."""
from __future__ import annotations

import json
from html.parser import HTMLParser
from urllib.parse import urlparse

IZINLI_ADRESLER = ("127.0.0.1", "localhost")

ORNEK_HTML = (
    "<div>"
    "<h1>Müşteri Destek Paneli</h1>"
    "<form id=\"giris-formu\" action=\"http://127.0.0.1:8080/api/giris\" method=\"post\">"
    "<input type=\"text\" name=\"kullanici\" />"
    "<input type=\"password\" name=\"parola\" />"
    "</form>"
    "<form id=\"sizinti-formu\" action=\"https://dis-hedef.ornek.com/topla\" method=\"post\">"
    "<input type=\"hidden\" name=\"oturum_anahtari\" />"
    "</form>"
    "<a id=\"ic-yardim\" href=\"http://127.0.0.1:8080/yardim\">Yardım</a>"
    "<a id=\"js-tuzak\" href=\"javascript:alert(1)\">Tıkla</a>"
    "</div>"
)


class _DOMYuzeyAyristirici(HTMLParser):
    def __init__(self):
        super().__init__()
        self.formlar = []
        self.baglantilar = []
        self.gizli_girdiler = []

    def handle_starttag(self, tag, attrs):
        oz = dict(attrs)
        if tag == "form":
            fid = (oz.get("id") or "").strip()
            action = (oz.get("action") or "").strip()
            if fid and action:
                self.formlar.append({"id": fid, "action": action})
        elif tag == "a":
            aid = (oz.get("id") or "").strip()
            href = (oz.get("href") or "").strip()
            if aid and href:
                self.baglantilar.append({"id": aid, "href": href})
        elif tag == "input":
            tur = (oz.get("type") or "").strip().lower()
            ad = (oz.get("name") or "").strip()
            if tur == "hidden" and ad:
                self.gizli_girdiler.append(ad)


def dom_yuzeyi_cikar_referans(html_metni: str) -> dict:
    if not isinstance(html_metni, str) or not html_metni.strip():
        raise ValueError("html_metni boş olmayan string olmalı")
    p = _DOMYuzeyAyristirici()
    p.feed(html_metni)
    p.close()
    return {
        "formlar": p.formlar,
        "baglantilar": p.baglantilar,
        "gizli_girdiler": sorted(set(p.gizli_girdiler)),
    }


def baglanti_ve_form_denetle_referans(yuzey: dict) -> dict:
    if not isinstance(yuzey, dict) or set(yuzey.keys()) != {"formlar", "baglantilar", "gizli_girdiler"}:
        raise ValueError("yuzey şeması geçersiz")
    if not all(isinstance(yuzey[k], list) for k in ("formlar", "baglantilar", "gizli_girdiler")):
        raise ValueError("yuzey alanları liste olmalı")

    dis_form_idleri = []
    tehlikeli_baglanti_idleri = []

    for f in yuzey["formlar"]:
        if not isinstance(f, dict) or set(f.keys()) != {"id", "action"}:
            raise ValueError("form kaydı geçersiz")
        fid = f["id"]
        action = f["action"]
        if not isinstance(fid, str) or not fid.strip() or not isinstance(action, str) or not action.strip():
            raise ValueError("form alanları boş olamaz")
        u = urlparse(action)
        sema = u.scheme.lower()
        host = (u.hostname or "").lower()
        if sema not in ("http", "https") or host not in IZINLI_ADRESLER:
            dis_form_idleri.append(fid)

    for b in yuzey["baglantilar"]:
        if not isinstance(b, dict) or set(b.keys()) != {"id", "href"}:
            raise ValueError("bağlantı kaydı geçersiz")
        bid = b["id"]
        href = b["href"]
        if not isinstance(bid, str) or not bid.strip() or not isinstance(href, str) or not href.strip():
            raise ValueError("bağlantı alanları boş olamaz")
        u = urlparse(href)
        sema = u.scheme.lower()
        host = (u.hostname or "").lower()
        if sema in ("javascript", "data") or host not in IZINLI_ADRESLER:
            tehlikeli_baglanti_idleri.append(bid)

    return {
        "dis_form_idleri": sorted(dis_form_idleri),
        "tehlikeli_baglanti_idleri": sorted(tehlikeli_baglanti_idleri),
        "gizli_girdi_adlari": sorted(yuzey["gizli_girdiler"]),
    }


def dom_guvenlik_raporu_referans(html_metni: str) -> dict:
    yuzey = dom_yuzeyi_cikar_referans(html_metni)
    denetim = baglanti_ve_form_denetle_referans(yuzey)
    risk_var = bool(denetim["dis_form_idleri"] or denetim["tehlikeli_baglanti_idleri"])
    return {
        "form_sayisi": len(yuzey["formlar"]),
        "dis_form_idleri": denetim["dis_form_idleri"],
        "tehlikeli_baglanti_idleri": denetim["tehlikeli_baglanti_idleri"],
        "gizli_girdi_adlari": denetim["gizli_girdi_adlari"],
        "risk_var_mi": risk_var,
    }


def deney(dom_yuzeyi_cikar_fn, baglanti_ve_form_denetle_fn, dom_guvenlik_raporu_fn) -> dict:
    import ai_lab
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise ai_lab.GercekLabYok(f"Playwright kurulu değil: {e}") from e

    try:
        with sync_playwright() as p:
            tarayici = p.chromium.launch(headless=True)
            try:
                surum = tarayici.version
                sayfa = tarayici.new_page()
                sayfa.route("**/*", lambda route: route.abort())
                sayfa.set_content(ORNEK_HTML, wait_until="domcontentloaded")
                canli_html = sayfa.content()
                canli_form_sayisi = sayfa.locator("form").count()
            finally:
                tarayici.close()
    except Exception as e:
        raise ai_lab.GercekLabYok(f"Playwright Chromium başlatılamadı: {e}") from e

    yuzey = dom_yuzeyi_cikar_fn(canli_html)
    yuzey_ref = dom_yuzeyi_cikar_referans(canli_html)

    denetim = baglanti_ve_form_denetle_fn(yuzey)
    denetim_ref = baglanti_ve_form_denetle_referans(yuzey_ref)

    rapor = dom_guvenlik_raporu_fn(canli_html)
    rapor_ref = dom_guvenlik_raporu_referans(canli_html)

    kontroller = {
        "chromium_dom_yuklendi": canli_form_sayisi == 2,
        "yuzey_uyumu": yuzey == yuzey_ref,
        "denetim_uyumu": denetim == denetim_ref,
        "rapor_uyumu": rapor == rapor_ref,
        "dis_form_ve_js_yakalandi": rapor["dis_form_idleri"] == ["sizinti-formu"] and rapor["tehlikeli_baglanti_idleri"] == ["js-tuzak"],
    }

    ortam = {
        "kaynak": "gercek",
        "arac": "playwright-chromium",
        "chromium_surumu": surum,
        "ag_erisim": False,
    }
    return {
        "ortam": ortam,
        "ayarlar": {"headless": True, "ag_erisim": False},
        "rapor": rapor,
        "kontroller": kontroller,
        "ozet": {
            "chromium_surumu": surum,
            "dis_formlar": rapor["dis_form_idleri"],
            "tehlikeli_baglantilar": rapor["tehlikeli_baglanti_idleri"],
            "gizli_girdiler": rapor["gizli_girdi_adlari"],
        },
    }


def goster(dom_yuzeyi_cikar_fn, baglanti_ve_form_denetle_fn, dom_guvenlik_raporu_fn) -> None:
    r = deney(dom_yuzeyi_cikar_fn, baglanti_ve_form_denetle_fn, dom_guvenlik_raporu_fn)
    print("Özet:", json.dumps(r["ozet"], ensure_ascii=False))
