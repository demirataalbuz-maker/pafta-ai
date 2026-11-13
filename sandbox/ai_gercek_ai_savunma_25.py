# -*- coding: utf-8 -*-
"""ai-savunma-25 gerçek deneyi: kanıt manifestosu gerçek bir kanıt dosyasının ASIL özetiyle doğrulanır.

Deney gerçek yerel modelle bir özetleme etkileşimi yapar ve ai_lab.kanit_yaz ile GERÇEK bir kanıt
JSON dosyası yazar. Dosyanın bayt içeriğinden gerçek SHA-256 ve bayt uzunluğu hesaplanır; bu değerlerle
bir kanıt manifestosu kurulur. Öğrencinin `kanit_manifestu_dogrula` işlevi manifestonun şemasını
doğrular.

Kritik ölçüm: doğru manifesto hem şemadan hem de gerçek dosyanın yeniden-hash'inden geçer (bütünlük
korunmuş). Sahte bir manifesto (özeti sıfırlanmış) şema olarak GEÇERLİ olsa bile, dosya yeniden
hash'lendiğinde özet uyuşmaz — yani şema geçerliliği kanıt bütünlüğünü kanıtlamaz; devir zincirinde
yeniden-hash şarttır. Böylece kanıt koruma gerçek bir artefakt üzerinde gösterilir.

Kanıt dosyası bu deneyin kendi çıktısıdır; gizli veri içermez. Model bu deney tarafından yüklendiyse
boşaltılır. Tahrif senaryosu dosyanın geçici bir kopyasında yapılır; asıl kanıt dosyasına dokunulmaz. Boş model yanıtı
deneyi durdurur. `kanit_manifestu_dogrula_referans` yalnız test içindir.
"""
import hashlib
import json
from pathlib import Path as pathlib_path

import ai_lab

BELGE = "Pafta yerel modellerle calisan bir guvenlik egitimidir; kurulum birkac komutla biter."
SIFIR_SHA = "0" * 64


def _dosya_sha_bayt(yol):
    with open(yol, "rb") as f:
        veri = f.read()
    return hashlib.sha256(veri).hexdigest(), len(veri)


def deney(kanit_manifestu_dogrula):
    import shutil
    import tempfile
    with ai_lab.SohbetOturumu() as oturum:
        c = oturum.sohbet([{"role": "system", "content": "Sen bir asistanisin; kisa ozetle."},
                           {"role": "user", "content": "Belgeyi ozetle.\n---\n" + BELGE + "\n---"}],
                          seed=5, sicaklik=0.0, en_fazla=80)
        ortam = dict(oturum.kayit)
    ozet_metni = (c.get("icerik") or "").strip()
    if not ozet_metni:
        raise ai_lab.GercekLabYok("model boş yanıt döndürdü; deney tamamlanmadı")
    ozet_metni = ozet_metni[:200]
    ortam["ayarlar"] = {"sicaklik": 0.0, "en_fazla": 80, "seed": 5,
                        "tahrif": "kanıt dosyasının geçici kopyasında 'ozet' alanının sonuna ' [duzenlendi]' eklenir (yalnız o baytlar değişir, biçim korunur)"}
    # GERÇEK bir kanıt dosyası yaz (olay müdahalesi kanıtı)
    yol = ai_lab.kanit_yaz("savunma-olay-kaniti", {"kaynak": "gercek", "kabul": False, "ders": "ai-savunma-25",
                                                   "olay": "ornek-ozetleme", "ozet": ozet_metni, "ortam": ortam})
    gercek_sha, gercek_bayt = _dosya_sha_bayt(yol)
    # Tahrif: aynı dosyanın geçici bir kopyasında tek alan değiştirilir (asıl kanıt dosyasına dokunulmaz)
    gecici = tempfile.mkdtemp(prefix="pafta_s25_")
    try:
        kopya = pathlib_path(gecici) / "kanit_kopyasi.json"
        shutil.copyfile(yol, kopya)
        ham = kopya.read_bytes()
        hedef = json.dumps(ozet_metni, ensure_ascii=False).encode("utf-8")
        if hedef not in ham:
            hedef = json.dumps(ozet_metni).encode("utf-8")
        if hedef not in ham:
            raise ai_lab.GercekLabYok("tahrif için özet metni kanıt dosyasında bulunamadı")
        kopya.write_bytes(ham.replace(hedef, hedef[:-1] + b' [duzenlendi]"', 1))
        tahrif_sha, tahrif_bayt = _dosya_sha_bayt(kopya)
    finally:
        shutil.rmtree(gecici, ignore_errors=True)

    dogru = {"olay_id": "olay-1", "kanit_id": "kanit-1", "sha256": gercek_sha, "bayt": gercek_bayt, "zaman": 0}
    sahte = {"olay_id": "olay-1", "kanit_id": "kanit-2", "sha256": SIFIR_SHA, "bayt": gercek_bayt, "zaman": 0}

    dogru_dogrulandi = kanit_manifestu_dogrula(dict(dogru))      # şema doğrulaması (öğrenci)
    sahte_dogrulandi = kanit_manifestu_dogrula(dict(sahte))      # şema olarak da geçerli (64 hex)
    # Gerçek bütünlük: dosyayı yeniden hash'le, manifestoyla karşılaştır
    yeniden_sha, yeniden_bayt = _dosya_sha_bayt(yol)
    dogru_butunluk = isinstance(dogru_dogrulandi, dict) and yeniden_sha == dogru_dogrulandi.get("sha256") and yeniden_bayt == dogru_dogrulandi.get("bayt")
    sahte_butunluk = isinstance(sahte_dogrulandi, dict) and yeniden_sha == sahte_dogrulandi.get("sha256")
    tahrif_butunluk = isinstance(dogru_dogrulandi, dict) and tahrif_sha == dogru_dogrulandi.get("sha256")
    return {"ortam": ortam, "yol": yol, "gercek_sha": gercek_sha, "gercek_bayt": gercek_bayt,
            "tahrif_sha": tahrif_sha, "tahrif_bayt": tahrif_bayt, "model_yaniti": ozet_metni,
            "manifestolar": {"dogru": dogru, "sahte": sahte},
            "dogru": dogru_dogrulandi, "sahte": sahte_dogrulandi,
            "dogru_sema_gecerli": dogru_dogrulandi == dogru, "sahte_sema_gecerli": sahte_dogrulandi == sahte,
            "dogru_butunluk": dogru_butunluk, "sahte_butunluk": sahte_butunluk, "tahrif_butunluk": tahrif_butunluk}


def ozet(r):
    return {"gercek_sha_onek": r["gercek_sha"][:12] + "…", "gercek_bayt": r["gercek_bayt"],
            "tahrif_sha_onek": r["tahrif_sha"][:12] + "…", "tahrif_bayt": r["tahrif_bayt"],
            "dogru_sema_gecerli": r["dogru_sema_gecerli"], "sahte_sema_gecerli": r["sahte_sema_gecerli"],
            "dogru_butunluk": r["dogru_butunluk"], "sahte_butunluk": r["sahte_butunluk"], "tahrif_butunluk": r["tahrif_butunluk"]}


def goster(kanit_manifestu_dogrula):
    """Çalıştır düğmesi: gerçek kanıt dosyasının manifestosunu doğrula ve yeniden-hash'le."""
    r = deney(kanit_manifestu_dogrula)
    o = r["ortam"]
    print(f"Model: {(o.get('model') or {}).get('ad')} · yanıt: {r['model_yaniti'][:120]!r}\n")
    print(f"   Gerçek kanıt dosyası yazıldı · SHA-256: {r['gercek_sha'][:16]}… · {r['gercek_bayt']} bayt")
    print(f"   Tahrif edilmiş kopya       · SHA-256: {r['tahrif_sha'][:16]}… · {r['tahrif_bayt']} bayt")
    oz = ozet(r)
    print(f"\n   Doğru manifesto: şema geçerli={oz['dogru_sema_gecerli']} · yeniden-hash bütünlük={oz['dogru_butunluk']}")
    print(f"   Sahte manifesto (özet sıfırlı): şema geçerli={oz['sahte_sema_gecerli']} · yeniden-hash bütünlük={oz['sahte_butunluk']}")
    print(f"   Doğru manifesto, tahrif edilmiş kopyaya karşı: bütünlük={oz['tahrif_butunluk']}")
    print("Not: şema geçerliliği kanıt bütünlüğünü kanıtlamaz; manifesto her devirde dosyanın yeniden hash'iyle karşılaştırılır.")
    print("Kanıt:", ai_lab.kanit_yaz("savunma-olay-calistir", {"kaynak": "gercek", "kabul": False, "ders": "ai-savunma-25",
                                                              "ortam": o, "ozet": oz, "model_yaniti": r["model_yaniti"],
                                                              "manifestolar": r["manifestolar"]}))


def kanit_manifestu_dogrula_referans(kayit):
    """Yalnız test içindir: manifesto şemasını doğrular ve yeni sözlük döndürür."""
    import re
    if not isinstance(kayit, dict) or set(kayit) != {"olay_id", "kanit_id", "sha256", "bayt", "zaman"}:
        raise ValueError("manifesto şeması geçersiz")
    for alan in ("olay_id", "kanit_id"):
        if not isinstance(kayit[alan], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit[alan]):
            raise ValueError("kimlik geçersiz")
    if not isinstance(kayit["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", kayit["sha256"]):
        raise ValueError("özet geçersiz")
    for alan in ("bayt", "zaman"):
        if type(kayit[alan]) is not int or kayit[alan] < 0:
            raise ValueError(alan + " geçersiz")
    return dict(kayit)
