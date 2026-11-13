# -*- coding: utf-8 -*-
"""ai-saldiri-07: özel CPU Ollama oturumunda tekrarlı davranış gözlemi, kanonik parmak izi ve karşılaştırma.

Kullanıcının veya başka ajanın Ollama sunucusuna/modellerine dokunmaz; yalnız kendi başlattığı
CPU sunucusunu kapatır. Yalnız sentetik sorgular kullanılır.
"""
import copy
import hashlib
import json
from pathlib import Path
import secrets
import time
import urllib.error

import ai_lab
from sandbox.ai_gercek_ai_temel_14 import OzelCpuOturumu

ROOT = Path(__file__).resolve().parents[1]
ORNEK_DOSYA = ROOT / "tracks" / "ai-saldiri" / "veri" / "ai-saldiri-07-ornek-gozlem.jsonl"

SORGULAR = [
    {"id": "q1", "metin": "Answer with one word only (YES or NO): Is 14 an even number?", "tekrar": 2},
    {"id": "q2", "metin": "Answer with one word only (YES or NO): Does the word PAFTA have five letters?", "tekrar": 2},
]


class ParmakIziOturumu(OzelCpuOturumu):
    def _model_sec(self):
        for attempt in range(2):
            try:
                return super()._model_sec()
            except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
                transient = not isinstance(exc, urllib.error.HTTPError) or 500 <= exc.code < 600
                self.kayit.setdefault("hazirlik_yeniden_denemeleri", []).append({
                    "deneme": attempt + 1,
                    "hata_turu": type(exc).__name__,
                    "hata": str(exc),
                    "gecici": transient,
                })
                if not transient or attempt == 1:
                    raise ai_lab.GercekLabYok("Özel Ollama oturumu hazırlığı tamamlanamadı: " + str(exc)) from exc
                time.sleep(2)

    def sorgu_cagir(self, sistem, metin, seed, sicaklik):
        if ai_lab.cihaz_kipi() == "cpu" and (self.surec is None or self.surec.poll() is not None):
            raise ai_lab.GercekLabYok("Deneye ait canlı Ollama süreci yok; başka sunucu kullanılmaz.")
        istek = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": sistem},
                {"role": "user", "content": metin},
            ],
            "stream": False,
            "options": ai_lab.ollama_secenekleri(
                temperature=sicaklik,
                seed=seed,
                num_predict=24,
                num_ctx=512,
            ),
            "keep_alive": "2m",
        }
        if self.dusunme:
            istek["think"] = False
        bas = time.perf_counter()
        hatalar = []
        for attempt in range(2):
            try:
                yanit = ai_lab._istek(self.adres, "/api/chat", istek, sure=55)
                break
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
                kod = getattr(exc, "code", None)
                gecici = kod is None or 500 <= kod < 600
                hata_kaydi = {"deneme": attempt + 1, "hata_turu": type(exc).__name__, "http_durum": kod, "hata": str(exc)}
                hatalar.append(hata_kaydi)
                self.kayit.setdefault("cagri_yeniden_denemeleri", []).append(hata_kaydi)
                if not gecici or attempt == 1:
                    raise ai_lab.GercekLabYok(f"Gerçek model çağrısı başarısız ({type(exc).__name__}): {exc}") from exc
                time.sleep(2)
        icerik = ((yanit.get("message") or {}).get("content") or "").strip()
        if yanit.get("done") is not True or not icerik:
            raise ai_lab.GercekLabYok("Gerçek model çağrısı tamamlanmadı veya boş yanıt döndü.")
        return {
            "icerik": icerik,
            "done": yanit.get("done") is True,
            "eval_count": yanit.get("eval_count"),
            "sure_ms": round((time.perf_counter() - bas) * 1000),
            "yeniden_denemeler": hatalar,
        }


def matris_referans(sorgular, model_cagir):
    kimlikler = set()
    for sorgu in sorgular:
        tekrar = sorgu["tekrar"]
        if not isinstance(sorgu["id"], str) or not sorgu["id"] or sorgu["id"] in kimlikler:
            raise ValueError("sorgu kimliği boş veya yinelenen")
        if not isinstance(sorgu["metin"], str):
            raise ValueError("sorgu metni string olmalı")
        if isinstance(tekrar, bool) or not isinstance(tekrar, int) or not 1 <= tekrar <= 4:
            raise ValueError("tekrar 1..4 olmalı")
        kimlikler.add(sorgu["id"])
    return [
        {"vaka_id": sorgu["id"], "tekrar": tekrar, "metin": sorgu["metin"], "yanit": model_cagir(sorgu["metin"])}
        for sorgu in sorgular
        for tekrar in range(1, sorgu["tekrar"] + 1)
    ]


def parmak_izi_referans(kayitlar):
    anahtarlar = set()
    for kayit in kayitlar:
        anahtar = (kayit["vaka_id"], kayit["tekrar"])
        if not isinstance(kayit["vaka_id"], str) or not kayit["vaka_id"]:
            raise ValueError("vaka kimliği geçersiz")
        if isinstance(kayit["tekrar"], bool) or not isinstance(kayit["tekrar"], int) or kayit["tekrar"] < 1:
            raise ValueError("tekrar pozitif tam sayı olmalı")
        if not isinstance(kayit["yanit"], str) or anahtar in anahtarlar:
            raise ValueError("yanıt veya kayıt anahtarı geçersiz")
        anahtarlar.add(anahtar)
    sirali = sorted(kayitlar, key=lambda x: (x["vaka_id"], x["tekrar"]))
    kanonik = json.dumps(sirali, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    yanitlar = {}
    for kayit in kayitlar:
        yanitlar.setdefault(kayit["vaka_id"], set()).add(kayit["yanit"])
    kararli = sum(len(cevaplar) == 1 for cevaplar in yanitlar.values())
    return {
        "imza": hashlib.sha256(kanonik.encode("utf-8")).hexdigest(),
        "gozlem": len(kayitlar),
        "kararli_vaka": kararli,
        "kararlilik": kararli / len(yanitlar) if yanitlar else None,
    }


def karsilastir_referans(sol, sag):
    def indeksle(kayitlar):
        indeks = {}
        for kayit in kayitlar:
            anahtar = (kayit["vaka_id"], kayit["tekrar"])
            if anahtar in indeks or not isinstance(kayit["yanit"], str):
                raise ValueError("yinelenen anahtar veya geçersiz yanıt")
            indeks[anahtar] = kayit["yanit"]
        return indeks

    a = indeksle(sol)
    b = indeksle(sag)
    if set(a) != set(b):
        raise ValueError("gözlem anahtarları eşleşmiyor")
    farkli = {anahtar[0] for anahtar in a if a[anahtar] != b[anahtar]}
    ayni = sum(a[anahtar] == b[anahtar] for anahtar in a)
    return {
        "gozlem": len(a),
        "ayni": ayni,
        "eslesme": ayni / len(a) if a else None,
        "farkli_vakalar": sorted(farkli),
    }


def ornek_dosya_hazirla(hedef="ornek_gozlem.jsonl"):
    """Çalışma dizininde öğrenci kopyası yoksa sentetik örnek dosyayı hazırlar; varsa öğrenci değişikliğini korur."""
    yol = Path(hedef)
    if not yol.exists():
        yol.write_text(ORNEK_DOSYA.read_text(encoding="utf-8"), encoding="utf-8")
    return yol


def deney(sorgu_matrisi, parmak_izi, gozlem_karsilastir):
    taban_seed = secrets.randbelow(10**6)
    sorgular_girdi = copy.deepcopy(SORGULAR)
    cagri_meta = {"sol": [], "sag": []}

    with ParmakIziOturumu() as oturum:
        sayac_sol = [0]

        def cagir_sol(metin):
            sayac_sol[0] += 1
            seed = taban_seed + sayac_sol[0]
            c = oturum.sorgu_cagir(
                "You are a concise classifier. Reply with YES or NO only.",
                metin,
                seed=seed,
                sicaklik=0.0,
            )
            cagri_meta["sol"].append(dict(c, sira=sayac_sol[0], seed=seed, metin=metin))
            return c["icerik"]

        sayac_sag = [0]

        def cagir_sag(metin):
            sayac_sag[0] += 1
            seed = taban_seed + 100 + sayac_sag[0]
            c = oturum.sorgu_cagir(
                "You are a verbose assistant. Reply with YES or NO and a short two-word note.",
                metin,
                seed=seed,
                sicaklik=0.6,
            )
            cagri_meta["sag"].append(dict(c, sira=sayac_sag[0], seed=seed, metin=metin))
            return c["icerik"]

        sol_kayitlar = sorgu_matrisi(sorgular_girdi, cagir_sol)
        sag_kayitlar = sorgu_matrisi(sorgular_girdi, cagir_sag)
        ortam = copy.deepcopy(oturum.kayit)
        ortam["bellek"] = oturum.bellek()
    ortam["temizlik"] = oturum.kayit.get("temizlik")

    beklenen_sol = [
        {"vaka_id": s["id"], "tekrar": t, "metin": s["metin"], "yanit": cagri_meta["sol"][i]["icerik"]}
        for i, (s, t) in enumerate((s, t) for s in SORGULAR for t in range(1, s["tekrar"] + 1))
    ]
    beklenen_sag = [
        {"vaka_id": s["id"], "tekrar": t, "metin": s["metin"], "yanit": cagri_meta["sag"][i]["icerik"]}
        for i, (s, t) in enumerate((s, t) for s in SORGULAR for t in range(1, s["tekrar"] + 1))
    ]
    matris_dogru = (
        sol_kayitlar == beklenen_sol
        and sag_kayitlar == beklenen_sag
        and sorgular_girdi == SORGULAR
    )

    sol_kopya = copy.deepcopy(sol_kayitlar)
    sag_kopya = copy.deepcopy(sag_kayitlar)
    sol_iz = parmak_izi(sol_kopya)
    sag_iz = parmak_izi(sag_kopya)
    iz_dogru = (
        sol_iz == parmak_izi_referans(beklenen_sol)
        and sag_iz == parmak_izi_referans(beklenen_sag)
        and sol_kopya == sol_kayitlar
        and sag_kopya == sag_kayitlar
    )

    kars_sol = copy.deepcopy(sol_kayitlar)
    kars_sag = copy.deepcopy(sag_kayitlar)
    karsilastirma = gozlem_karsilastir(kars_sol, kars_sag)
    kars_dogru = (
        karsilastirma == karsilastir_referans(beklenen_sol, beklenen_sag)
        and kars_sol == sol_kayitlar
        and kars_sag == sag_kayitlar
    )

    tum_cagrilar = cagri_meta["sol"] + cagri_meta["sag"]
    gercek_tam = (
        len(cagri_meta["sol"]) == 4
        and len(cagri_meta["sag"]) == 4
        and all(c.get("done") is True and isinstance(c.get("icerik"), str) and bool(c["icerik"]) for c in tum_cagrilar)
    )

    sonuc = {
        "kaynak": "gercek",
        "ortam": ortam,
        "ayarlar": {
            "sorgu_sayisi": len(SORGULAR),
            "tekrar": 2,
            "toplam_cagri": 8,
            "taban_seed": taban_seed,
            "sol_profil": {"sicaklik": 0.0, "sistem": "concise YES/NO"},
            "sag_profil": {"sicaklik": 0.6, "sistem": "verbose YES/NO + note"},
            "num_predict": 24,
            "num_ctx": 512,
            "cihaz": ai_lab.cihaz_kipi(),
        },
        "sorgular_sha256": hashlib.sha256(
            json.dumps(SORGULAR, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "sol_kayitlar": sol_kayitlar,
        "sag_kayitlar": sag_kayitlar,
        "cagri_meta": cagri_meta,
        "ozet": {
            "sol_parmak_izi": sol_iz,
            "sag_parmak_izi": sag_iz,
            "karsilastirma": karsilastirma,
        },
        "kontroller": {
            "matris_dogru": matris_dogru,
            "parmak_izi_dogru": iz_dogru,
            "karsilastirma_dogru": kars_dogru,
            "gercek_tam": gercek_tam,
            "kaynak_temizlendi": ai_lab.kaynak_temizlendi(ortam.get("temizlik")),
            "cihaz_dogrulandi": ai_lab.cihaz_dogrulandi(ortam.get("bellek")),
        },
        "hata_sayisi": 0 if gercek_tam else 1,
    }
    return sonuc


def goster(sorgu_matrisi, parmak_izi, gozlem_karsilastir):
    yol = ornek_dosya_hazirla()
    ornek_satirlar = [
        {k: v for k, v in json.loads(s).items() if k in ("vaka_id", "tekrar", "metin", "yanit")}
        for s in yol.read_text(encoding="utf-8").splitlines()
        if s.strip()
    ]
    print(f"[Sentetik örnek / fixture] {yol.name} ({len(ornek_satirlar)} satır) → parmak izi:", parmak_izi(ornek_satirlar))
    r = deney(sorgu_matrisi, parmak_izi, gozlem_karsilastir)
    print(f"\n[Canlı gerçek deney] model: {r['ortam']['model']['ad']} · 8 gerçek çağrı")
    for etiket, ks in (("Sol profil (T=0.0)", r["sol_kayitlar"]), ("Sağ profil (T=0.6)", r["sag_kayitlar"])):
        print(f"  {etiket}:")
        for k in ks:
            print(f"    {k['vaka_id']}#{k['tekrar']} -> {k['yanit']!r}")
    print("\nÖzet:", json.dumps(r["ozet"], ensure_ascii=False))
    print("Kanıt:", ai_lab.kanit_yaz("saldiri-07-parmak-izi", {
        "kaynak": "gercek",
        "kabul": False,
        "ders": "ai-saldiri-07",
        "ortam": r["ortam"],
        "deney": r,
        "ozet": r["ozet"],
    }))
