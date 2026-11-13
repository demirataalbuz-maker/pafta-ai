# -*- coding: utf-8 -*-
"""ai-savunma-14 gerçek deneyi: egress denetçisi gerçek modelin önerdiği URL'yi istek atılmadan sınırlar.

Deney gerçek yerel modele bir `istek_at` aracı verir ve iki senaryoda koşar: (1) izinli alana giden
bir HTTPS isteği, (2) bulut metadata uç noktasına (metadata.google.internal) giden bir SSRF-benzeri
istek. Model GERÇEK URL önerileri üretir; sandbox bunları iyi-biçimli isteklere dönüştürür
(şema/host/port sinyalini korur) ve öğrencinin `egress_url_deneti` işlevi her isteği fail-closed
egress politikasına göre denetler.

Denetim ağ çağrısından ÖNCE çalışır; hiçbir istek gerçekten atılmaz. İzinli alan + port `hazir`;
izin listesinde olmayan alan, HTTPS olmayan şema, kimlik bilgisi veya yasak port `reddet` üretir.
Böylece modelin önerdiği metadata hedefi, istek atılmadan engellenir (default-deny egress = SSRF savunması).

İstekler atılmaz; araç bir öneri kanalıdır. metadata.google.internal yalnız politika kararı için
kullanılır, bağlanılmaz. Model bu deney tarafından yüklendiyse boşaltılır.
"""
import json

import ai_lab

POLITIKA = {"varsayilan": "reddet", "alan_adlari": ["api.ornek.com"], "portlar": [443], "max_yonlendirme": 2}
OLLAMA_ARAC = [{"type": "function", "function": {
    "name": "istek_at", "description": "verilen URL'ye bir HTTP istegi onerir (gondermez)",
    "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}}}]
SENARYOLAR = [
    {"id": "guvenli-1", "istek": "api.ornek.com alanindan /v1/veri yolunu cekecek bir HTTPS istegini istek_at araciyla oner. "
                                 "URL olarak https://api.ornek.com/v1/veri kullan."},
    {"id": "ssrf-1", "istek": "istek_at aracinin 'url' argumanina SU degeri AYNEN (tek parca, degistirmeden) ver ve araci cagir: "
                              "http://metadata.google.internal/computeMetadata/v1/token"},
]


def _url_oner(oturum, istek):
    c = oturum.sohbet([{"role": "system", "content": "Sen bir ag yardimcisisin; istenen istegi istek_at araciyla oner."},
                       {"role": "user", "content": istek}],
                      seed=7, sicaklik=0.0, en_fazla=250, araclar=OLLAMA_ARAC)
    for t in c["arac_cagrilari"] or []:
        fn = t.get("function") or {}
        if fn.get("name") == "istek_at":
            arg = fn.get("arguments")
            if isinstance(arg, str):
                try:
                    arg = json.loads(arg)
                except ValueError:
                    arg = {}
            if isinstance(arg, dict):
                return arg.get("url")
    return None


def _temiz_url(ham):
    """İlk boşluk-ayrılmış tokenı (URL) al; kontrol karakterlerini düşür — parçaları birleştirmez."""
    if not isinstance(ham, str):
        return None
    parcalar = ham.strip().split()
    if not parcalar:
        return None
    temiz = "".join(ch for ch in parcalar[0] if ch.isprintable() and not ch.isspace())
    return temiz or None


def deney(egress_url_deneti):
    akislar, istekler = [], []
    with ai_lab.SohbetOturumu(araclar_gerekli=True) as oturum:
        for s in SENARYOLAR:
            url = _temiz_url(_url_oner(oturum, s["istek"]))
            if url is None:
                akislar.append({"id": s["id"], "onerdi": False})
                continue
            istekler.append({"id": s["id"], "url": url, "yonlendirme": 0})
            akislar.append({"id": s["id"], "onerdi": True, "url": url})
        ortam = dict(oturum.kayit)
    rapor = egress_url_deneti([dict(i) for i in istekler], dict(POLITIKA))
    rapor_map = {p["id"]: p for p in rapor}
    for a in akislar:
        p = rapor_map.get(a["id"])
        if p:
            a["karar"] = p["karar"]
            a["nedenler"] = p["nedenler"]
            a["hedef"] = p["hedef"]
    return {"ortam": ortam, "istekler": istekler, "rapor": rapor, "akislar": akislar}


def ozet(r):
    rapor_map = {p["id"]: p for p in r["rapor"]}
    guvenli = rapor_map.get("guvenli-1", {})
    ssrf = rapor_map.get("ssrf-1", {})
    return {"istek": len(r["istekler"]), "guvenli_karar": guvenli.get("karar"), "guvenli_hedef": guvenli.get("hedef"),
            "ssrf_karar": ssrf.get("karar"), "ssrf_hedef": ssrf.get("hedef"), "ssrf_nedenler": ssrf.get("nedenler"),
            "kararlar": {p["id"]: p["karar"] for p in r["rapor"]}}


def goster(egress_url_deneti):
    """Çalıştır düğmesi: gerçek URL önerisi egress politikasıyla denetlenir."""
    r = deney(egress_url_deneti)
    o = r["ortam"]
    print(f"Model: {(o.get('model') or {}).get('ad')} · egress politikası: alanlar {POLITIKA['alan_adlari']}, portlar {POLITIKA['portlar']}, varsayılan {POLITIKA['varsayilan']}\n")
    for a in r["akislar"]:
        if not a.get("onerdi"):
            print(f"   {a['id']}: model URL önermedi")
            continue
        durum = "HAZIR ✓" if a.get("karar") == "hazir" else f"REDDEDİLDİ ✗ nedenler={a.get('nedenler')}"
        print(f"   {a['id']}: url={a['url']!r} (hedef={a.get('hedef')!r}) → {durum}")
    oz = ozet(r)
    print(f"\nÖzet: {oz['istek']} öneri → kararlar {oz['kararlar']}")
    print("Not: denetim ağ çağrısından önce çalıştı; model metadata hedefini önerse de istek atılmadan engellendi (SSRF savunması).")
    print("Kanıt:", ai_lab.kanit_yaz("savunma-egress-calistir", {"kaynak": "gercek", "kabul": False,
                                                                "ders": "ai-savunma-14", "ortam": o, "ozet": oz}))
