# -*- coding: utf-8 -*-
"""ai-savunma-03 gerçek deneyi: fail-closed karar gerçek bir kontrol gözlemine dayanmalı. Deney gerçek
yerel modelin çıktısını bir ÇIKTI ŞEMASI guardrail'inden geçirir: yanıtın beklenen biçime (yalnız tam
sayı) uyup uymadığını deterministik olarak denetler. Sayı isteyen görevde model uyar → kontrol 'gecti';
düzyazı üreten görevde çıktı şemaya uymaz → 'kaldi'. Bu gerçek gözlem öğrencinin fail-closed karar işlevine
beslenir: şemaya uymayan çıktı isteği reddedilir (fail-closed), uyan çıktı 'izin' alır.

Görevler zararsızdır. Model bu deney tarafından yüklendiyse sonunda boşaltılır.
"""
import re

import ai_lab

MIMARI = [
    {"id": "girdi", "kontroller": ["icerik"]},
    {"id": "model", "kontroller": ["model_sabitleme"]},
    {"id": "cikti", "kontroller": ["cikti_semasi"]},
    {"id": "arac", "kontroller": ["yetki"]},
    {"id": "veri", "kontroller": ["kiraci"]},
]
# (etiket, istem, sema_uyar_mi_beklenir) — şema: yanıt yalnız tam sayı
SENARYOLAR = [
    ("sema_uyar", "17 ile 4'ü çarp. Yanıtın YALNIZCA sonuç sayısı olsun, başka hiçbir şey yazma."),
    ("sema_bozuk", "Fotosentezi bir cümleyle açıkla."),
]
_SIRA = ["girdi", "model", "cikti", "arac", "veri"]


def referans_karar(mimari, olaylar):
    """fail-closed karar referansı (görev 2 mantığı)."""
    kayit = {k["id"]: k["kontroller"] for k in mimari}
    sonuc = {(o["katman"], o["kontrol"]): o["sonuc"] for o in olaylar}
    eksik, neden = [], None
    for katman in _SIRA:
        for kontrol in kayit[katman]:
            s = sonuc.get((katman, kontrol))
            if s is None:
                eksik.append(katman + ":" + kontrol)
            if s in ("kaldi", "hata") and neden is None:
                neden = {"katman": katman, "kontrol": kontrol, "sonuc": s}
    karar = "reddet" if neden else ("eksik" if eksik else "izin")
    return {"karar": karar, "neden": neden, "eksik": eksik}


def _cikti_sema_kontrol(oturum, istem):
    """Çıktı şeması guardrail'i: modelin gerçek yanıtı yalnız tam sayı mı? (deterministik denetim)"""
    c = oturum.sohbet([{"role": "user", "content": istem}], seed=4, sicaklik=0.1, en_fazla=60)
    yanit = c["icerik"].strip().strip("`").strip()
    uyar = re.fullmatch(r"-?\d+", yanit) is not None
    return ("gecti" if uyar else "kaldi"), yanit


def deney(istek_karari_hesapla):
    kontrol_map = {k["id"]: k["kontroller"] for k in MIMARI}
    kayitlar = []
    with ai_lab.SohbetOturumu() as oturum:
        for etiket, istem in SENARYOLAR:
            sonuc, yanit = _cikti_sema_kontrol(oturum, istem)
            olaylar = []
            for katman in _SIRA:
                for kontrol in kontrol_map[katman]:
                    olaylar.append({"katman": katman, "kontrol": kontrol,
                                    "sonuc": sonuc if (katman == "cikti" and kontrol == "cikti_semasi") else "gecti"})
            karar = istek_karari_hesapla([dict(k) for k in MIMARI], [dict(o) for o in olaylar])
            kayitlar.append({"etiket": etiket, "istem": istem, "yanit": yanit[:80], "cikti_semasi": sonuc, "karar": karar})
        ortam = dict(oturum.kayit)
    ortam["temizlik"] = oturum.kayit.get("temizlik")
    return {"ortam": ortam, "mimari": MIMARI, "kayitlar": kayitlar}


def ozet(r):
    d = {k["etiket"]: k for k in r["kayitlar"]}
    return {"uyar_sema": d.get("sema_uyar", {}).get("cikti_semasi"), "uyar_karar": d.get("sema_uyar", {}).get("karar", {}).get("karar"),
            "bozuk_sema": d.get("sema_bozuk", {}).get("cikti_semasi"), "bozuk_karar": d.get("sema_bozuk", {}).get("karar", {}).get("karar")}


def goster(istek_karari_hesapla):
    """Çalıştır düğmesi: gerçek çıktı-şeması gözlemiyle fail-closed karar."""
    r = deney(istek_karari_hesapla)
    o = r["ortam"]
    print(f"Model (çıktı şeması guardrail): {(o.get('model') or {}).get('ad')}\n")
    for k in r["kayitlar"]:
        n = k["karar"]["neden"]
        print(f"[{k['etiket']:10}] çıktı='{k['yanit'][:40]}' → şema {k['cikti_semasi']}  ⇒  karar: {k['karar']['karar']}"
              + (f" (neden {n['katman']}:{n['kontrol']}={n['sonuc']})" if n else ""))
    oz = ozet(r)
    print(f"\nÖzet: şemaya uyan çıktı → {oz['uyar_sema']} ⇒ {oz['uyar_karar']}; şemaya uymayan çıktı → {oz['bozuk_sema']} ⇒ {oz['bozuk_karar']}")
    print("Karar gerçek çıktı-şeması gözleminden geldi; şemaya uymayan çıktı fail-closed reddedilir.")
    print("Kanıt:", ai_lab.kanit_yaz("savunma-katman-calistir", {"kaynak": "gercek", "kabul": False, "ders": "ai-savunma-03",
                                                                "ortam": o, "ozet": oz}))
