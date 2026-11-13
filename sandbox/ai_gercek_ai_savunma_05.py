# -*- coding: utf-8 -*-
"""ai-savunma-05 gerçek deneyi: tekrarlanabilir bir test laboratuvarı determinizm gerektirir. Deney aynı
istemi, aynı tohumla ve sıcaklık 0 ile yerel modele birkaç kez koşar; her koşunun girdi/çıktı SHA-256
özetini ve durumunu kaydeder. Öğrencinin tekrarlanabilirlik raporu, sabit tohumla üretilen çıktıların
koşular arası aynı olup olmadığını (determinizm) belirler. Çıktı özetleri değişirse test tekrarlanabilir
değildir — bu, bir regresyon laboratuvarının neden deterministik koşu gerektirdiğini gösterir.

İstem zararsızdır. Model bu deney tarafından yüklendiyse sonunda boşaltılır.
"""
import hashlib

import ai_lab

ISTEM = "3 ile 7'yi çarp. Yanıtın yalnızca sonuç sayısı olsun."
TOHUM = 42
TEKRAR = 3


def referans_rapor(kosular):
    """Tekrarlanabilirlik referansı (geçerli koşular varsayılır)."""
    gruplar = {}
    for k in kosular:
        gruplar.setdefault(k["test"], []).append(k)
    out = []
    for test in sorted(gruplar):
        runs = gruplar[test]
        nedenler = []
        for alan, ad in (("tohum", "tohum"), ("girdi_sha256", "girdi"), ("cikti_sha256", "cikti"), ("durum", "durum")):
            if len({r[alan] for r in runs}) > 1:
                nedenler.append(ad)
        if any(r["durum"] != "gecti" for r in runs) and "durum" not in nedenler:
            nedenler.append("durum")
        out.append({"test": test, "kosum_sayisi": len(runs), "tekrarlanabilir": not nedenler, "nedenler": nedenler})
    return out


AYARLAR={"tohum":TOHUM,"sicaklik":0.0,"en_fazla":20,"tekrar":TEKRAR,"num_ctx":4096,"girdi_sha256_kapsami":"yalnız istem UTF-8 baytları"}

def deney(tekrarlanabilirlik_raporu):
    import math
    g_sha=hashlib.sha256(ISTEM.encode("utf-8")).hexdigest()
    ciktilar=[];kosular=[];cagrilar=[];hatalar=[];oturum=None
    try:
        with ai_lab.SohbetOturumu() as oturum:
            for n in range(TEKRAR):
                y="";basarili=False
                try:
                    c=oturum.sohbet([{"role":"user","content":ISTEM}],seed=TOHUM,sicaklik=0.0,en_fazla=20)
                    y=c["icerik"] if isinstance(c.get("icerik"),str) else ""
                    basarili=isinstance(y,str) and bool(y.strip()) and type(c["eval_count"]) is int and c["eval_count"]>0 and isinstance(c["sure_ms"],(int,float)) and math.isfinite(c["sure_ms"]) and c["sure_ms"]>=0
                    cagrilar.append({"kosum":n+1,"yanit":c,"basarili":basarili})
                    if not basarili:hatalar.append({"kosum":n+1,"hata":"eksik yanıt veya gerçek ölçüm"})
                except Exception as exc:
                    hatalar.append({"kosum":n+1,"tur":type(exc).__name__,"hata":str(exc)})
                    cagrilar.append({"kosum":n+1,"basarili":False,"hata":str(exc)})
                ciktilar.append(y)
                kosular.append({"test":"determinizm","kosum":n+1,"tohum":TOHUM,"girdi_sha256":g_sha,"cikti_sha256":hashlib.sha256(y.encode("utf-8")).hexdigest(),"durum":"gecti" if basarili else "hata"})
    finally:
        ortam=dict(oturum.kayit) if oturum else {}
    rapor=tekrarlanabilirlik_raporu([dict(k) for k in kosular])
    return {"ortam":ortam,"istem":ISTEM,"tohum":TOHUM,"tekrar":TEKRAR,"ciktilar":ciktilar,"kosular":kosular,"rapor":rapor,"ayni_cikti":len(set(ciktilar))==1,"cagri_kayitlari":cagrilar,"hatalar":hatalar}


def ozet(r):
    d = r["rapor"][0] if r["rapor"] else {}
    return {"tekrar": r["tekrar"], "benzersiz_cikti": len(set(r["ciktilar"])), "ayni_cikti": r["ayni_cikti"],
            "tekrarlanabilir": d.get("tekrarlanabilir"), "nedenler": d.get("nedenler"), "ornek_cikti": (r["ciktilar"][0] or "")[:40]}


def goster(tekrarlanabilirlik_raporu):
    """Çalıştır düğmesi: sabit tohumla determinizm kanıtı."""
    r = deney(tekrarlanabilirlik_raporu)
    o = r["ortam"]
    print(f"Model: {(o.get('model') or {}).get('ad')} · istem sabit, tohum={r['tohum']}, sıcaklık=0, {r['tekrar']} koşu\n")
    for n, y in enumerate(r["ciktilar"], 1):
        print(f"   koşu {n}: çıktı={y[:30]!r} sha256={r['kosular'][n-1]['cikti_sha256'][:12]}…")
    oz = ozet(r)
    print(f"\nTekrarlanabilirlik raporu: {r['rapor']}")
    print(f"Sonuç: {oz['benzersiz_cikti']} benzersiz çıktı ({r['tekrar']} koşuda) → tekrarlanabilir: {oz['tekrarlanabilir']}")
    print("Bu sonuç yalnız üç gerçek gözlemin tutarlılığını gösterir; sabit tohum ve sıcaklık0 genel determinizm garantisi değildir.")
    print("Çağrı hataları:",r["hatalar"])
    print("Kanıt:", ai_lab.kanit_yaz("savunma-lab-calistir", {"kaynak": "gercek", "kabul": False, "ders": "ai-savunma-05",
                                                             "ortam": o, "ozet": oz, "istem":r["istem"], "ayarlar":AYARLAR,"ciktilar":r["ciktilar"],"kosular":r["kosular"],"rapor":r["rapor"],"cagri_kayitlari":r["cagri_kayitlari"],"hatalar":r["hatalar"]}))
