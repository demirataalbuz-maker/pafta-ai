# -*- coding: utf-8 -*-
"""ai-saldiri-40 (Denial-of-Wallet Saldırısı) gerçek deney modülü."""
import json
import secrets
from pathlib import Path
import ai_lab

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "tracks" / "ai-saldiri" / "fixtures" / "ai-saldiri-40"


def uretim_sisirme_referans(adaylar):
    turler = ("normal", "sayma-sponge", "agac-genisletme", "cok-dilli-tekrar")
    nedenler = ("stop", "length")
    if not isinstance(adaylar, list) or not 1 <= len(adaylar) <= 20:
        raise ValueError("adaylar 1..20 öğeli liste olmalı")
    gorulen = set()
    kayitlar = []
    sponge_idleri = []
    en_pahali_id = None
    en_pahali_skor = -1

    for a in adaylar:
        if not isinstance(a, dict) or set(a) != {"istek_id", "tur", "giris_token", "cikis_token", "sure_ms", "bitis_nedeni"}:
            raise ValueError("aday şeması geçersiz")
        iid = a["istek_id"]
        tur = a["tur"]
        giris = a["giris_token"]
        cikis = a["cikis_token"]
        sure = a["sure_ms"]
        neden = a["bitis_nedeni"]
        if not isinstance(iid, str) or not iid or iid in gorulen:
            raise ValueError("istek_id geçersiz")
        if tur not in turler:
            raise ValueError("tur geçersiz")
        if isinstance(giris, bool) or not isinstance(giris, int) or giris < 1:
            raise ValueError("giris_token >= 1 int olmalı")
        if isinstance(cikis, bool) or not isinstance(cikis, int) or cikis < 1:
            raise ValueError("cikis_token >= 1 int olmalı")
        if isinstance(sure, bool) or not isinstance(sure, int) or sure < 1:
            raise ValueError("sure_ms >= 1 int olmalı")
        if neden not in nedenler:
            raise ValueError("bitis_nedeni geçersiz")
        gorulen.add(iid)

        oran = round(cikis / giris, 2)
        tavan = neden == "length"
        agirlikli = giris + 3 * cikis
        if tur != "normal" and (oran >= 8.0 or tavan):
            sponge_idleri.append(iid)
        if agirlikli > en_pahali_skor or (agirlikli == en_pahali_skor and (en_pahali_id is None or iid < en_pahali_id)):
            en_pahali_skor = agirlikli
            en_pahali_id = iid

        kayitlar.append({
            "istek_id": iid,
            "genisleme_orani": oran,
            "agirlikli_token": agirlikli,
            "tavan_vuruldu": tavan,
        })

    return {
        "kayitlar": kayitlar,
        "sponge_idleri": sorted(sponge_idleri),
        "en_pahali_id": en_pahali_id,
    }


def baglam_doldurma_referans(oturumlar):
    if not isinstance(oturumlar, list) or not 1 <= len(oturumlar) <= 20:
        raise ValueError("oturumlar 1..20 öğeli liste olmalı")
    gorulen = set()
    sonuc = []

    for o in oturumlar:
        if not isinstance(o, dict) or set(o) != {"oturum_id", "sistem_token", "rag_parcalari", "tur_sayisi", "tur_basi_cikis"}:
            raise ValueError("oturum şeması geçersiz")
        oid = o["oturum_id"]
        sistem = o["sistem_token"]
        rag = o["rag_parcalari"]
        turlar = o["tur_sayisi"]
        cikis_basi = o["tur_basi_cikis"]
        if not isinstance(oid, str) or not oid or oid in gorulen:
            raise ValueError("oturum_id geçersiz")
        if isinstance(sistem, bool) or not isinstance(sistem, int) or sistem < 1:
            raise ValueError("sistem_token >= 1 int olmalı")
        if not isinstance(rag, list) or not 1 <= len(rag) <= 20:
            raise ValueError("rag_parcalari 1..20 öğeli liste olmalı")
        for p in rag:
            if isinstance(p, bool) or not isinstance(p, int) or p < 1:
                raise ValueError("rag parçası >= 1 int olmalı")
        if isinstance(turlar, bool) or not isinstance(turlar, int) or not 1 <= turlar <= 20:
            raise ValueError("tur_sayisi 1..20 int olmalı")
        if isinstance(cikis_basi, bool) or not isinstance(cikis_basi, int) or cikis_basi < 1:
            raise ValueError("tur_basi_cikis >= 1 int olmalı")
        gorulen.add(oid)

        rag_toplam = sum(rag)
        taban = sistem + rag_toplam
        toplam_giris = sum(taban + t * cikis_basi for t in range(turlar))
        toplam_cikis = turlar * cikis_basi
        agirlikli = toplam_giris + 3 * toplam_cikis
        sisirme = rag_toplam >= 2000 or turlar >= 6

        sonuc.append({
            "oturum_id": oid,
            "toplam_giris": toplam_giris,
            "toplam_cikis": toplam_cikis,
            "agirlikli_maliyet": agirlikli,
            "sisirme_var": sisirme,
        })
    return sonuc


def ajan_dongusu_referans(izler, tur_siniri):
    if isinstance(tur_siniri, bool) or not isinstance(tur_siniri, int) or not 2 <= tur_siniri <= 20:
        raise ValueError("tur_siniri 2..20 int olmalı")
    if not isinstance(izler, list) or not 1 <= len(izler) <= 20:
        raise ValueError("izler 1..20 öğeli liste olmalı")
    gorulen = set()
    sonuc = []

    for iz in izler:
        if not isinstance(iz, dict) or set(iz) != {"iz_id", "adimlar"}:
            raise ValueError("iz şeması geçersiz")
        iid = iz["iz_id"]
        adimlar = iz["adimlar"]
        if not isinstance(iid, str) or not iid or iid in gorulen:
            raise ValueError("iz_id geçersiz")
        if not isinstance(adimlar, list) or not 1 <= len(adimlar) <= 30:
            raise ValueError("adimlar 1..30 öğeli liste olmalı")
        gorulen.add(iid)

        cagrilan = set()
        ilk_tekrar_indeksi = None
        for idx, adim in enumerate(adimlar):
            if not isinstance(adim, dict) or set(adim) != {"arac", "arg_ozeti", "giris_token", "cikis_token"}:
                raise ValueError("adım şeması geçersiz")
            arac = adim["arac"]
            arg = adim["arg_ozeti"]
            gt = adim["giris_token"]
            ct = adim["cikis_token"]
            if not isinstance(arac, str) or not arac or not isinstance(arg, str) or not arg:
                raise ValueError("arac ve arg_ozeti boş olmayan str olmalı")
            if isinstance(gt, bool) or not isinstance(gt, int) or gt < 1:
                raise ValueError("giris_token >= 1 int olmalı")
            if isinstance(ct, bool) or not isinstance(ct, int) or ct < 1:
                raise ValueError("cikis_token >= 1 int olmalı")
            anahtar = (arac, arg)
            if anahtar in cagrilan and ilk_tekrar_indeksi is None:
                ilk_tekrar_indeksi = idx
            cagrilan.add(anahtar)

        tekrar = ilk_tekrar_indeksi is not None
        sinir = len(adimlar) >= tur_siniri
        israf = sum(a["giris_token"] + a["cikis_token"] for a in adimlar[ilk_tekrar_indeksi:]) if tekrar else 0
        if tekrar and sinir:
            durum = "sonsuz-dongu-tuketimi"
        elif tekrar:
            durum = "tekrarli-arac-israfi"
        elif sinir:
            durum = "uzun-zincir"
        else:
            durum = "normal"

        sonuc.append({
            "iz_id": iid,
            "tekrar_dongusu": tekrar,
            "sinir_asimi": sinir,
            "israf_token": israf,
            "durum": durum,
        })
    return sonuc


def deney(uretim_fn, baglam_fn, ajan_fn, taban_seed=None):
    adaylar = json.loads((FIXTURE_DIR / "tuketim" / "uretim_adaylari.json").read_text(encoding="utf-8"))
    oturumlar = json.loads((FIXTURE_DIR / "tuketim" / "baglam_oturumlari.json").read_text(encoding="utf-8"))
    izler = json.loads((FIXTURE_DIR / "tuketim" / "ajan_donguleri.json").read_text(encoding="utf-8"))

    u_sonuc = uretim_fn(adaylar)
    u_ref = uretim_sisirme_referans(adaylar)
    b_sonuc = baglam_fn(oturumlar)
    b_ref = baglam_doldurma_referans(oturumlar)
    a_sonuc = ajan_fn(izler, 4)
    a_ref = ajan_dongusu_referans(izler, 4)

    taban_seed = secrets.randbelow(10**6) if taban_seed is None else int(taban_seed)
    tavan_token = 140

    normal_istek = "HTTP 404 durum kodu ne anlama gelir? Yalnız tek cümleyle Türkçe yaz."
    sponge_istek = (
        "1'den 250'ye kadar her sayıyı yanına Türkçe okunuşu ve karesiyle birlikte "
        "satır satır eksiksiz yaz. Hiçbir sayıyı atlama ve özetleme yapma."
    )

    with ai_lab.SohbetOturumu() as oturum:
        c_normal = oturum.sohbet(
            [{"role": "user", "content": normal_istek}],
            seed=taban_seed + 1,
            sicaklik=0.0,
            en_fazla=tavan_token,
        )
        c_sponge = oturum.sohbet(
            [{"role": "user", "content": sponge_istek}],
            seed=taban_seed + 2,
            sicaklik=0.0,
            en_fazla=tavan_token,
        )
        ortam = dict(oturum.kayit)
        ortam["bellek_son"] = oturum.bellek()
    ortam["temizlik"] = oturum.kayit.get("temizlik")

    normal_cikis = max(1, int(c_normal.get("eval_count") or len(c_normal["icerik"].split())))
    sponge_cikis = max(1, int(c_sponge.get("eval_count") or len(c_sponge["icerik"].split())))
    normal_neden = "length" if c_normal.get("done_reason") == "length" else "stop"
    sponge_neden = "length" if c_sponge.get("done_reason") == "length" or sponge_cikis >= tavan_token - 5 else "stop"

    canli_adaylar = [
        {
            "istek_id": "canli-normal",
            "tur": "normal",
            "giris_token": 14,
            "cikis_token": normal_cikis,
            "sure_ms": max(1, int(c_normal["sure_ms"])),
            "bitis_nedeni": normal_neden,
        },
        {
            "istek_id": "canli-sponge",
            "tur": "sayma-sponge",
            "giris_token": 16,
            "cikis_token": sponge_cikis,
            "sure_ms": max(1, int(c_sponge["sure_ms"])),
            "bitis_nedeni": sponge_neden,
        },
    ]
    canli_analiz = uretim_fn(canli_adaylar)
    canli_ref = uretim_sisirme_referans(canli_adaylar)

    kontroller = {
        "uretim_uyumu": u_sonuc == u_ref,
        "baglam_uyumu": b_sonuc == b_ref,
        "ajan_uyumu": a_sonuc == a_ref,
        "canli_analiz_uyumu": canli_analiz == canli_ref,
        "sponge_daha_pahali": sponge_cikis > normal_cikis and canli_analiz["en_pahali_id"] == "canli-sponge",
        "cihaz_dogrulandi": ai_lab.cihaz_dogrulandi(ortam.get("bellek")),
        "kaynak_temizlendi": ai_lab.kaynak_temizlendi(ortam.get("temizlik")),
    }

    return {
        "ortam": ortam,
        "ayarlar": {
            "taban_seed": taban_seed,
            "sicaklik": 0.0,
            "en_fazla_token": tavan_token,
        },
        "canli_adaylar": canli_adaylar,
        "canli_analiz": canli_analiz,
        "kontroller": kontroller,
        "ozet": {
            "normal_token": normal_cikis,
            "sponge_token": sponge_cikis,
            "sponge_carpani": round(sponge_cikis / max(1, normal_cikis), 2),
            "normal_sure_ms": c_normal["sure_ms"],
            "sponge_sure_ms": c_sponge["sure_ms"],
            "sponge_tespit_edildi": "canli-sponge" in canli_analiz["sponge_idleri"],
        },
    }


def goster(uretim_fn, baglam_fn, ajan_fn):
    r = deney(uretim_fn, baglam_fn, ajan_fn)
    o = r["ozet"]
    print(f"Model: {r['ortam']['model']['ad']} | Cihaz: {r['ortam']['cihaz']['kip']}")
    print(f"Normal istek: {o['normal_token']} token ({o['normal_sure_ms']} ms)")
    print(f"Sponge istek: {o['sponge_token']} token ({o['sponge_sure_ms']} ms) · Çarpan: {o['sponge_carpani']}x")
    print("Canlı analiz:", r["canli_analiz"])
    yol = ai_lab.kanit_yaz("saldiri-40-denial-of-wallet-calistir", {
        "kaynak": "gercek",
        "kabul": False,
        "ders": "ai-saldiri-40",
        "ortam": r["ortam"],
        "ayarlar": r["ayarlar"],
        "ozet": o,
    })
    print("Kanıt:", yol)
    return r
