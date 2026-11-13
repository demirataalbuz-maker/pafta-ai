# -*- coding: utf-8 -*-
"""ai-savunma-20 gerçek deneyi: kurulu Ollama modelinin katmanları gerçek SHA-256 ile doğrulanır.

Ollama bir modeli Docker/OCI dağıtım manifest'i ile saklar: manifest her katmanı (`model` ağırlıkları,
`template`, `license`, `params`, config...) `sha256:<hex>` özetiyle adresler ve dosyalar
`<models>/blobs/sha256-<hex>` adıyla durur. Deney:

1. Kurulu sohbet modelinin manifest dosyasını salt okunur açar (beklenen özetler buradan gelir).
2. Her katmanın blob dosyasının SHA-256 özetini GERÇEKTEN hesaplar (ağırlık dosyası dahil; akışla okunur).
3. Tahrifat senaryosu için en küçük katmanın geçici bir KOPYASINDA son baytı değiştirir ve kopyanın
   özetini hesaplar. Kullanıcının dosyalarına yazılmaz; kopya deney sonunda silinir.
4. Katmanları ve tahrif kopyasını öğrencinin `surum_guvenlik_raporu` işlevine fail-closed politikayla verir.

Okunan manifest'te imza (ör. Cosign/Sigstore) bilgisi bulunmadığından `imzali` alanı gerçeği yansıtacak
biçimde False yazılır; imza zorunlu politika bu yüzden her katmana `imza` nedeni ekler. Zafiyet taraması
yapılmaz; `riskler` boş listesi "tarama yapılmadı" demektir, "risk yok" demek değildir.
Hiçbir model indirilmez, yüklenmez veya değiştirilmez. `surum_guvenlik_raporu_referans` yalnız test içindir.
"""
import hashlib
import json
import math
import os
import re
import shutil
import tempfile
import time
from pathlib import Path

import ai_lab

POLITIKA = {"izinli_kaynaklar": ["resmi", "kurumsal"], "izinli_turler": ["model", "paket"],
            "izinli_riskler": ["dusuk"], "max_boyut_mb": 10000, "imza_zorunlu": True}
TUR_ADI = {"application/vnd.ollama.image.model": "agirlik", "application/vnd.ollama.image.template": "sablon",
           "application/vnd.ollama.image.license": "lisans", "application/vnd.ollama.image.params": "parametre",
           "application/vnd.ollama.image.system": "sistem", "application/vnd.ollama.image.projector": "projektor",
           "application/vnd.docker.distribution.manifest.v2+json": "manifest",
           "application/vnd.docker.container.image.v1+json": "config"}


def _modeller_dizini():
    return Path(os.environ.get("OLLAMA_MODELS") or Path.home() / ".ollama" / "models")


def _manifest_yolu(kok, model_ad):
    ad, _, etiket = model_ad.partition(":")
    etiket = etiket or "latest"
    if "/" in ad or not re.fullmatch(r"[A-Za-z0-9._-]+", ad) or not re.fullmatch(r"[A-Za-z0-9._-]+", etiket):
        raise ai_lab.GercekLabYok(f"model adı bu deneyin desteklediği library/<ad>:<etiket> biçiminde değil: {model_ad}")
    yol = kok / "manifests" / "registry.ollama.ai" / "library" / ad / etiket
    if not yol.is_file():
        raise ai_lab.GercekLabYok(f"manifest dosyası bulunamadı: {yol}")
    return yol


def _sha256_dosya(yol):
    h = hashlib.sha256()
    with open(yol, "rb") as akim:
        for parca in iter(lambda: akim.read(1 << 20), b""):
            h.update(parca)
    return h.hexdigest()


def _katmanlar(manifest):
    katmanlar = list(manifest.get("layers") or [])
    if manifest.get("config"):
        katmanlar.append(manifest["config"])
    sonuc, gorulen = [], {}
    for k in katmanlar:
        m = re.fullmatch(r"sha256:([0-9a-f]{64})", str(k.get("digest", "")))
        if not m:
            raise ai_lab.GercekLabYok(f"manifest katman özeti beklenen biçimde değil: {str(k.get('digest'))[:32]}")
        ad = TUR_ADI.get(k.get("mediaType"), "katman")
        gorulen[ad] = gorulen.get(ad, 0) + 1
        kimlik = ad if gorulen[ad] == 1 else f"{ad}-{gorulen[ad]}"
        sonuc.append({"id": kimlik, "medya": k.get("mediaType"), "ozet": m.group(1), "boyut": int(k.get("size") or 0)})
    if not any(k["id"] == "agirlik" for k in sonuc):
        raise ai_lab.GercekLabYok("manifest'te model ağırlık katmanı yok")
    return sonuc


def _bilesen(kimlik, boyut_bayt, beklenen, gercek):
    return {"id": kimlik, "tur": "model", "kaynak": "resmi", "boyut_mb": max(1, math.ceil(boyut_bayt / (1024 * 1024))),
            "imzali": False, "beklenen_sha256": beklenen, "gercek_sha256": gercek, "riskler": []}


def deney(surum_guvenlik_raporu):
    with ai_lab.SohbetOturumu() as oturum:
        model_ad = oturum.model
        ortam = dict(oturum.kayit)
    kok = _modeller_dizini()
    manifest_yolu = _manifest_yolu(kok, model_ad)
    manifest = json.loads(manifest_yolu.read_text(encoding="utf-8"))
    katmanlar = _katmanlar(manifest)
    olcumler, bilesenler = [], []
    for k in katmanlar:
        blob = kok / "blobs" / f"sha256-{k['ozet']}"
        if not blob.is_file():
            raise ai_lab.GercekLabYok(f"blob dosyası bulunamadı: {blob.name}")
        bas = time.perf_counter()
        gercek = _sha256_dosya(blob)
        olcumler.append({"id": k["id"], "medya": k["medya"], "manifest_ozet": k["ozet"], "hesaplanan_ozet": gercek,
                         "eslesti": gercek == k["ozet"], "dosya_bayt": blob.stat().st_size, "manifest_bayt": k["boyut"],
                         "sure_sn": round(time.perf_counter() - bas, 3)})
        bilesenler.append(_bilesen(k["id"], blob.stat().st_size, k["ozet"], gercek))
    kucuk = min(katmanlar, key=lambda k: k["boyut"])
    gecici = Path(tempfile.mkdtemp(prefix="pafta_s20_"))
    try:
        kopya = gecici / "tahrif_kopyasi"
        shutil.copyfile(kok / "blobs" / f"sha256-{kucuk['ozet']}", kopya)
        veri = bytearray(kopya.read_bytes())
        if not veri:
            raise ai_lab.GercekLabYok("tahrif için seçilen katman boş")
        veri[-1] ^= 0x01
        kopya.write_bytes(bytes(veri))
        tahrif_ozet = _sha256_dosya(kopya)
    finally:
        shutil.rmtree(gecici, ignore_errors=True)
    tahrif_id = kucuk["id"] + "-tahrif"
    bilesenler.append(_bilesen(tahrif_id, len(veri), kucuk["ozet"], tahrif_ozet))
    olcumler.append({"id": tahrif_id, "medya": kucuk["medya"], "manifest_ozet": kucuk["ozet"], "hesaplanan_ozet": tahrif_ozet,
                     "eslesti": tahrif_ozet == kucuk["ozet"], "not": "geçici kopyanın son baytı XOR 0x01 ile değiştirildi"})
    tags_ozet = re.sub(r"^sha256:", "", str((ortam.get("model") or {}).get("digest") or ""))
    ortam["ayarlar"] = {"modeller_dizini": str(kok), "manifest": str(manifest_yolu.relative_to(kok)),
                        "politika": dict(POLITIKA), "imza": "manifest'te imza bilgisi yok; imzali=False",
                        "riskler": "zafiyet taraması yapılmadı; boş liste bulgu yokluğu değildir",
                        "api_tags_digest": tags_ozet,
                        "api_tags_digest_katmanlarda": tags_ozet in [k["ozet"] for k in katmanlar]}
    rapor = surum_guvenlik_raporu([dict(b, riskler=list(b["riskler"])) for b in bilesenler], dict(POLITIKA))
    rapor_map = {r["id"]: r for r in rapor} if isinstance(rapor, list) and all(isinstance(r, dict) and "id" in r for r in rapor) else {}
    return {"ortam": ortam, "model_ad": model_ad, "bilesenler": bilesenler, "olcumler": olcumler, "rapor": rapor,
            "tahrif_id": tahrif_id, "tahrif_karar": rapor_map.get(tahrif_id, {}).get("karar"),
            "tahrif_nedenler": rapor_map.get(tahrif_id, {}).get("nedenler")}


def ozet(r):
    agirlik = next(o for o in r["olcumler"] if o["id"] == "agirlik")
    return {"model": r["model_ad"], "katman_sayisi": len(r["olcumler"]) - 1,
            "eslesen_katman": sum(1 for o in r["olcumler"][:-1] if o["eslesti"]),
            "agirlik_ozet_onek": agirlik["hesaplanan_ozet"][:12] + "…", "agirlik_mb": round(agirlik["dosya_bayt"] / 2 ** 20),
            "agirlik_hash_sn": agirlik["sure_sn"], "tahrif_id": r["tahrif_id"],
            "tahrif_karar": r["tahrif_karar"], "tahrif_nedenler": r["tahrif_nedenler"]}


def goster(surum_guvenlik_raporu):
    """Çalıştır düğmesi: kurulu modelin katmanlarını gerçek SHA-256 ile denetle."""
    r = deney(surum_guvenlik_raporu)
    print(f"Kurulu model: {r['model_ad']} · manifest: {r['ortam']['ayarlar']['manifest']}\n")
    for o in r["olcumler"]:
        print(f"   {o['id']:<22} manifest={o['manifest_ozet'][:12]}… hesaplanan={o['hesaplanan_ozet'][:12]}… "
              f"eşleşti={o['eslesti']}")
    print("\nRapor:")
    for rec in r["rapor"] if isinstance(r["rapor"], list) else []:
        print(f"   {rec.get('id')}: karar={rec.get('karar')} nedenler={rec.get('nedenler')}")
    oz = ozet(r)
    print(f"\nAğırlık dosyası ~{oz['agirlik_mb']} MB, özet {oz['agirlik_hash_sn']} sn'de hesaplandı. "
          f"Tahrif kopyası kararı: {oz['tahrif_karar']} {oz['tahrif_nedenler']}")
    print("Not: imza bilgisi olmadığı için imza zorunlu politika her katmanı karantinaya alır; zafiyet taraması yapılmadı.")
    print("Kanıt:", ai_lab.kanit_yaz("savunma-tedarik-calistir", {"kaynak": "gercek", "kabul": False, "ders": "ai-savunma-20",
                                                                 "ortam": r["ortam"], "ozet": oz, "olcumler": r["olcumler"]}))


def surum_guvenlik_raporu_referans(bilesenler, politika):
    """Yalnız test içindir: politika/bileşen doğrulaması ve altı nedenle bağımsız karar."""
    if not isinstance(politika, dict) or set(politika) != {"izinli_kaynaklar", "izinli_turler", "izinli_riskler",
                                                             "max_boyut_mb", "imza_zorunlu"}:
        raise ValueError("politika şeması geçersiz")
    for alan, izin, bos in (("izinli_kaynaklar", ("resmi", "kurumsal", "yerel"), False),
                            ("izinli_turler", ("model", "imaj", "paket"), False),
                            ("izinli_riskler", ("dusuk", "orta", "yuksek", "kritik"), True)):
        d = politika[alan]
        if not isinstance(d, list) or (not d and not bos) or len(set(d)) != len(d) or any(x not in izin for x in d):
            raise ValueError(alan + " geçersiz")
    if type(politika["max_boyut_mb"]) is not int or not 1 <= politika["max_boyut_mb"] <= 10000:
        raise ValueError("boyut sınırı geçersiz")
    if politika["imza_zorunlu"] is not True:
        raise ValueError("imza zorunlu olmalı")
    if not isinstance(bilesenler, list):
        raise ValueError("bileşenler liste olmalı")
    alanlar = {"id", "tur", "kaynak", "boyut_mb", "imzali", "beklenen_sha256", "gercek_sha256", "riskler"}
    gorulen, sonuc = set(), []
    for b in bilesenler:
        if not isinstance(b, dict) or set(b) != alanlar:
            raise ValueError("bileşen şeması geçersiz")
        if not isinstance(b["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", b["id"]) or b["id"] in gorulen:
            raise ValueError("kimlik geçersiz")
        gorulen.add(b["id"])
        if b["tur"] not in ("model", "imaj", "paket") or b["kaynak"] not in ("resmi", "kurumsal", "yerel"):
            raise ValueError("tür/kaynak geçersiz")
        if type(b["boyut_mb"]) is not int or b["boyut_mb"] < 1 or not isinstance(b["imzali"], bool):
            raise ValueError("boyut/imza geçersiz")
        for alan in ("beklenen_sha256", "gercek_sha256"):
            if not isinstance(b[alan], str) or not re.fullmatch(r"[0-9a-f]{64}", b[alan]):
                raise ValueError("özet geçersiz")
        r = b["riskler"]
        if not isinstance(r, list) or len(set(map(str, r))) != len(r) or any(x not in ("dusuk", "orta", "yuksek", "kritik") for x in r):
            raise ValueError("riskler geçersiz")
        nedenler = [n for n, kosul in (("tur", b["tur"] not in politika["izinli_turler"]),
                                        ("kaynak", b["kaynak"] not in politika["izinli_kaynaklar"]),
                                        ("boyut", b["boyut_mb"] > politika["max_boyut_mb"]),
                                        ("imza", not b["imzali"]),
                                        ("butunluk", b["beklenen_sha256"] != b["gercek_sha256"]),
                                        ("risk", any(x not in politika["izinli_riskler"] for x in r))) if kosul]
        sonuc.append({"id": b["id"], "karar": "karantina" if nedenler else "kabul", "nedenler": nedenler})
    return sorted(sonuc, key=lambda x: x["id"])
