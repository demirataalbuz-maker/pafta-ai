"""ai-ile-guvenlik-10 dersi için gerçek yerel Ollama + çoklu log akışı özeti ve kanıt doğrulaması deneyi."""
from __future__ import annotations

import json

HAM_LOG_METNI = (
    '{"olay_id": "log-101", "kaynak_ip": "10.10.4.21", "olay_turu": "basarisiz_giris", "kullanici": "admin"}\n'
    '{"olay_id": "log-102", "kaynak_ip": "10.10.4.21", "olay_turu": "basarisiz_giris", "kullanici": "root"}\n'
    '{"olay_id": "log-103", "kaynak_ip": "10.10.4.21", "olay_turu": "basarili_giris", "kullanici": "admin"}\n'
    '{"olay_id": "log-104", "kaynak_ip": "10.10.8.55", "olay_turu": "dosya_okuma", "kullanici": "analist"}\n'
)

ADAY_IDDIALAR = [
    {
        "iddia_id": "id-1",
        "kaynak_ip": "10.10.4.21",
        "kanit_olay_idleri": ["log-101", "log-102", "log-103"],
    },
    {
        "iddia_id": "id-2",
        "kaynak_ip": "192.168.99.99",
        "kanit_olay_idleri": ["log-999"],
    },
    {
        "iddia_id": "id-3",
        "kaynak_ip": "10.10.8.55",
        "kanit_olay_idleri": ["log-101"],
    },
]


def jsonl_log_kumele_referans(jsonl_metni: str) -> dict:
    if not isinstance(jsonl_metni, str) or not jsonl_metni.strip():
        raise ValueError("jsonl_metni boş olmayan string olmalı")

    olay_indeksi = {}
    ip_kumeleri: dict[str, list[str]] = {}
    beklenen = {"olay_id", "kaynak_ip", "olay_turu", "kullanici"}

    for satir in jsonl_metni.splitlines():
        s = satir.strip()
        if not s:
            continue
        try:
            kayit = json.loads(s)
        except Exception as e:
            raise ValueError("geçersiz JSON satırı") from e
        if not isinstance(kayit, dict) or set(kayit.keys()) != beklenen:
            raise ValueError("log kaydı şeması geçersiz")
        if not all(isinstance(kayit[k], str) and bool(kayit[k].strip()) for k in beklenen):
            raise ValueError("log alanları boş olmayan string olmalı")

        oid = kayit["olay_id"]
        if oid in olay_indeksi:
            raise ValueError("tekrarlanan olay_id")
        olay_indeksi[oid] = kayit
        ip_kumeleri.setdefault(kayit["kaynak_ip"], []).append(oid)

    for ip in ip_kumeleri:
        ip_kumeleri[ip].sort()

    return {
        "olay_indeksi": olay_indeksi,
        "ip_kumeleri": ip_kumeleri,
        "toplam_olay": len(olay_indeksi),
    }


def ozet_iddia_dogrula_referans(iddia: dict, olay_indeksi: dict) -> dict:
    if not isinstance(iddia, dict) or set(iddia.keys()) != {"iddia_id", "kaynak_ip", "kanit_olay_idleri"}:
        raise ValueError("iddia şeması geçersiz")
    if not isinstance(olay_indeksi, dict) or not olay_indeksi:
        raise ValueError("olay_indeksi boş olmayan sözlük olmalı")

    iid = iddia["iddia_id"]
    ip = iddia["kaynak_ip"]
    kanitlar = iddia["kanit_olay_idleri"]

    if not isinstance(iid, str) or not iid.strip() or not isinstance(ip, str) or not ip.strip():
        raise ValueError("iddia_id ve kaynak_ip boş olamaz")
    if not isinstance(kanitlar, list) or not kanitlar or not all(isinstance(x, str) and bool(x.strip()) for x in kanitlar):
        raise ValueError("kanit_olay_idleri boş olmayan string listesi olmalı")

    uydurma = [oid for oid in kanitlar if oid not in olay_indeksi]
    if uydurma:
        return {"iddia_id": iid, "gecerli": False, "neden": "uydurma_olay_id"}

    uyumsuz = [oid for oid in kanitlar if olay_indeksi[oid].get("kaynak_ip") != ip]
    if uyumsuz:
        return {"iddia_id": iid, "gecerli": False, "neden": "ip_uyumsuzlugu"}

    return {"iddia_id": iid, "gecerli": True, "neden": "dogrulandi"}


def dogrulanmis_soc_ozeti_referans(jsonl_metni: str, iddialar: list[dict]) -> dict:
    if not isinstance(iddialar, list) or not iddialar:
        raise ValueError("iddialar boş olamaz")
    kume = jsonl_log_kumele_referans(jsonl_metni)
    indeks = kume["olay_indeksi"]

    onaylanan = []
    reddedilen = {}
    gorulen = set()

    for idd in iddialar:
        sonuc = ozet_iddia_dogrula_referans(idd, indeks)
        iid = sonuc["iddia_id"]
        if iid in gorulen:
            raise ValueError("tekrarlanan iddia_id")
        gorulen.add(iid)

        if sonuc["gecerli"]:
            onaylanan.append(iid)
        else:
            reddedilen[iid] = sonuc["neden"]

    return {
        "onaylanan_iddialar": sorted(onaylanan),
        "reddedilen_iddialar": reddedilen,
        "toplam_olay": kume["toplam_olay"],
    }


def deney(jsonl_log_kumele_fn, ozet_iddia_dogrula_fn, dogrulanmis_soc_ozeti_fn) -> dict:
    import ai_lab

    with ai_lab.SohbetOturumu() as oturum:
        c = oturum.sohbet(
            [
                {
                    "role": "system",
                    "content": "Sen bir SOC analistisin. Verilen JSONL log akışını kaynak IP bazında özetle ve kanıt olay_id numaralarını belirt.",
                },
                {"role": "user", "content": HAM_LOG_METNI},
            ],
            seed=910,
            sicaklik=0.0,
            en_fazla=120,
        )
        canli_yanit = (c.get("icerik") if isinstance(c, dict) else str(c or "")).strip()
        ortam = dict(oturum.kayit)
    ortam["temizlik"] = oturum.kayit.get("temizlik")

    kume = jsonl_log_kumele_fn(HAM_LOG_METNI)
    kume_ref = jsonl_log_kumele_referans(HAM_LOG_METNI)

    tek_dogrulama = ozet_iddia_dogrula_fn(ADAY_IDDIALAR[0], kume["olay_indeksi"])
    tek_ref = ozet_iddia_dogrula_referans(ADAY_IDDIALAR[0], kume_ref["olay_indeksi"])

    ozet = dogrulanmis_soc_ozeti_fn(HAM_LOG_METNI, ADAY_IDDIALAR)
    ozet_ref = dogrulanmis_soc_ozeti_referans(HAM_LOG_METNI, ADAY_IDDIALAR)

    kontroller = {
        "kumeleme_uyumu": kume == kume_ref,
        "tek_iddia_uyumu": tek_dogrulama == tek_ref,
        "soc_ozet_uyumu": ozet == ozet_ref,
        "halusinasyon_ve_ip_uyumsuzlugu_elendi": ozet["reddedilen_iddialar"] == {"id-2": "uydurma_olay_id", "id-3": "ip_uyumsuzlugu"},
        "cihaz_dogrulandi": ai_lab.cihaz_dogrulandi(ortam.get("bellek")),
        "kaynak_temizlendi": ai_lab.kaynak_temizlendi(ortam.get("temizlik")),
    }

    return {
        "ortam": ortam,
        "ayarlar": {"log_sayisi": kume["toplam_olay"]},
        "canli_yanit": canli_yanit,
        "ozet_sonuc": ozet,
        "kontroller": kontroller,
        "ozet": {
            "model": ortam["model"]["ad"],
            "onaylanan": ozet["onaylanan_iddialar"],
            "reddedilen": ozet["reddedilen_iddialar"],
        },
    }


def goster(jsonl_log_kumele_fn, ozet_iddia_dogrula_fn, dogrulanmis_soc_ozeti_fn) -> None:
    r = deney(jsonl_log_kumele_fn, ozet_iddia_dogrula_fn, dogrulanmis_soc_ozeti_fn)
    print("Özet:", json.dumps(r["ozet"], ensure_ascii=False))
