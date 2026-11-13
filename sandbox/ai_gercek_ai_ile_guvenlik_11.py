"""ai-ile-guvenlik-11 dersi için gerçek yerel Ollama + Sigma kuralı taslağı ve yanlış alarm sınaması deneyi."""
from __future__ import annotations

import json

KORPUS = [
    {
        "olay_id": "PROC-301",
        "CommandLine": "rundll32.exe C:\\Windows\\System32\\comsvcs.dll, MiniDump 644 C:\\Temp\\lsass.dmp full",
        "etiket": "saldiri",
    },
    {
        "olay_id": "PROC-302",
        "CommandLine": "rundll32.exe comsvcs.dll,MiniDump 712 C:\\Users\\Public\\dump.bin full",
        "etiket": "saldiri",
    },
    {
        "olay_id": "PROC-303",
        "CommandLine": "rundll32.exe shell32.dll,Control_RunDLL desk.cpl",
        "etiket": "temiz",
    },
    {
        "olay_id": "PROC-304",
        "CommandLine": "rundll32_diag.exe comsvcs.dll MiniDump --dry-run --safe-audit",
        "etiket": "temiz",
    },
]

ADAY_KURALLAR = [
    {
        "kural_id": "SIG-ADAY-A",
        "title": "Aşırı Geniş Rundll32 Kuralı",
        "logsource": {"category": "process_creation", "product": "windows"},
        "detection": {
            "selection": {"CommandLine|contains": ["rundll32"]},
            "condition": "selection",
        },
        "level": "high",
    },
    {
        "kural_id": "SIG-ADAY-B",
        "title": "Comsvcs MiniDump Bellek Dökümü Tespiti",
        "logsource": {"category": "process_creation", "product": "windows"},
        "detection": {
            "selection": {"CommandLine|contains": ["comsvcs", "MiniDump"]},
            "filter": {"CommandLine|contains": ["--safe-audit"]},
            "condition": "selection and not filter",
        },
        "level": "critical",
    },
    {
        "kural_id": "SIG-ADAY-C",
        "title": "Eksik Şemalı Joker Kural",
        "logsource": {"category": "process_creation", "product": "windows"},
        "detection": {
            "selection": {"CommandLine|contains": ["*"]},
            "condition": "selection",
        },
        "level": "invalid_level",
    },
]

IZINLI_SEVIYELER = ("low", "medium", "high", "critical")


def sigma_sema_dogrula_referans(kural: dict) -> dict:
    if not isinstance(kural, dict) or "kural_id" not in kural:
        raise ValueError("kural sözlük olmalı ve kural_id taşımalı")
    kid = kural["kural_id"]
    if not isinstance(kid, str) or not kid.strip():
        raise ValueError("kural_id boş olmayan string olmalı")

    hatalar: list[str] = []
    if not isinstance(kural.get("title"), str) or not kural["title"].strip():
        hatalar.append("eksik_title")

    ls = kural.get("logsource")
    if not isinstance(ls, dict) or not isinstance(ls.get("category"), str) or not ls["category"].strip():
        hatalar.append("eksik_logsource")

    det = kural.get("detection")
    if not isinstance(det, dict):
        hatalar.append("eksik_detection")
    else:
        sel = det.get("selection")
        cond = det.get("condition")
        if not isinstance(sel, dict) or not sel:
            hatalar.append("eksik_selection")
        else:
            parcalar = sel.get("CommandLine|contains")
            if not isinstance(parcalar, list) or not parcalar or not all(isinstance(x, str) and bool(x.strip()) and x.strip() != "*" for x in parcalar):
                hatalar.append("joker_veya_bos_secim")
        if not isinstance(cond, str) or not cond.strip():
            hatalar.append("eksik_condition")

    seviye = kural.get("level")
    if not isinstance(seviye, str) or seviye.strip().lower() not in IZINLI_SEVIYELER:
        hatalar.append("gecersiz_level")

    return {"kural_id": kid, "gecerli": len(hatalar) == 0, "hatalar": hatalar}


def kural_korpusta_olc_referans(kural: dict, korpus: list[dict]) -> dict:
    sema = sigma_sema_dogrula_referans(kural)
    if not sema["gecerli"]:
        raise ValueError("geçersiz Sigma şeması")
    if not isinstance(korpus, list) or not korpus:
        raise ValueError("korpus boş olmayan liste olmalı")

    det = kural["detection"]
    secim = [s.lower() for s in det["selection"]["CommandLine|contains"]]
    flt_blok = det.get("filter", {})
    flt_liste = [s.lower() for s in flt_blok.get("CommandLine|contains", [])] if isinstance(flt_blok, dict) else []
    flt_aktif = "not filter" in det["condition"].lower() and bool(flt_liste)

    tp = fp = tn = fn = 0
    for olay in korpus:
        if not isinstance(olay, dict) or olay.get("etiket") not in ("saldiri", "temiz") or not isinstance(olay.get("CommandLine"), str):
            raise ValueError("geçersiz olay kaydı")
        cmd = olay["CommandLine"].lower()
        secim_ok = all(p in cmd for p in secim)
        flt_ok = all(p in cmd for p in flt_liste) if flt_aktif else False
        eslesti = secim_ok and not flt_ok

        if olay["etiket"] == "saldiri":
            if eslesti:
                tp += 1
            else:
                fn += 1
        else:
            if eslesti:
                fp += 1
            else:
                tn += 1

    if (tp + fn) == 0 or (fp + tn) == 0:
        raise ValueError("korpusta hem saldiri hem temiz kayıt bulunmalı")

    return {
        "kural_id": kural["kural_id"],
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "tpr": round(tp / (tp + fn), 4),
        "fpr": round(fp / (fp + tn), 4),
    }


def aday_kurallari_sirala_referans(adaylar: list[dict], korpus: list[dict], azami_fpr: float) -> dict:
    if not isinstance(adaylar, list) or not adaylar:
        raise ValueError("adaylar boş olmayan liste olmalı")
    if not isinstance(azami_fpr, (int, float)) or isinstance(azami_fpr, bool) or azami_fpr < 0.0 or azami_fpr > 1.0:
        raise ValueError("azami_fpr 0 ile 1 arasında olmalı")

    uygunlar = []
    elenenler = {}
    for kural in adaylar:
        sema = sigma_sema_dogrula_referans(kural)
        kid = sema["kural_id"]
        if not sema["gecerli"]:
            elenenler[kid] = "gecersiz_sema"
            continue
        m = kural_korpusta_olc_referans(kural, korpus)
        if m["fpr"] > azami_fpr:
            elenenler[kid] = "yuksek_fpr"
            continue
        uygunlar.append(m)

    uygunlar.sort(key=lambda x: (-x["tpr"], x["fpr"], x["kural_id"]))
    secilen = uygunlar[0]["kural_id"] if uygunlar else None
    return {
        "secilen_kural_id": secilen,
        "uygun_sayisi": len(uygunlar),
        "elenen_kurallar": elenenler,
    }


def deney(sigma_sema_dogrula_fn, kural_korpusta_olc_fn, aday_kurallari_sirala_fn) -> dict:
    import ai_lab

    with ai_lab.SohbetOturumu() as oturum:
        c = oturum.sohbet(
            [
                {
                    "role": "system",
                    "content": "Sen bir tespit mühendisisin. Comsvcs MiniDump saldırısını yakalayan ve --safe-audit parametresini hariç tutan Sigma kural koşulunu kısaca açıkla.",
                },
                {"role": "user", "content": json.dumps(KORPUS, ensure_ascii=False)},
            ],
            seed=911,
            sicaklik=0.0,
            en_fazla=120,
        )
        canli_yanit = (c.get("icerik") if isinstance(c, dict) else str(c or "")).strip()
        ortam = dict(oturum.kayit)
    ortam["temizlik"] = oturum.kayit.get("temizlik")

    sema = sigma_sema_dogrula_fn(ADAY_KURALLAR[2])
    sema_ref = sigma_sema_dogrula_referans(ADAY_KURALLAR[2])

    olc = kural_korpusta_olc_fn(ADAY_KURALLAR[1], KORPUS)
    olc_ref = kural_korpusta_olc_referans(ADAY_KURALLAR[1], KORPUS)

    secim = aday_kurallari_sirala_fn(ADAY_KURALLAR, KORPUS, 0.1)
    secim_ref = aday_kurallari_sirala_referans(ADAY_KURALLAR, KORPUS, 0.1)

    kontroller = {
        "sema_dogrulama_uyumu": sema == sema_ref,
        "korpus_olcum_uyumu": olc == olc_ref,
        "aday_siralama_uyumu": secim == secim_ref,
        "dusuk_fpr_kurali_secildi": secim["secilen_kural_id"] == "SIG-ADAY-B",
        "cihaz_dogrulandi": ai_lab.cihaz_dogrulandi(ortam.get("bellek")),
        "kaynak_temizlendi": ai_lab.kaynak_temizlendi(ortam.get("temizlik")),
    }

    return {
        "ortam": ortam,
        "ayarlar": {"korpus_boyutu": len(KORPUS), "aday_sayisi": len(ADAY_KURALLAR)},
        "canli_yanit": canli_yanit,
        "secim_sonuc": secim,
        "kontroller": kontroller,
        "ozet": {
            "model": ortam["model"]["ad"],
            "secilen_kural": secim["secilen_kural_id"],
            "elenen_kurallar": secim["elenen_kurallar"],
        },
    }


def goster(sigma_sema_dogrula_fn, kural_korpusta_olc_fn, aday_kurallari_sirala_fn) -> None:
    r = deney(sigma_sema_dogrula_fn, kural_korpusta_olc_fn, aday_kurallari_sirala_fn)
    print("Özet:", json.dumps(r["ozet"], ensure_ascii=False))
