# -*- coding: utf-8 -*-
"""ai-savunma-04 gerçek deneyi: güvenli telemetri gerçek trafikten üretilmeli. Deney yerel modele birkaç
gerçek istek atar ve her birinden bir model telemetri olayı kurar: gerçek süre (sure_ms) ve gerçek çıktı
token sayısı (token_out) taşır, ama HAM istem/yanıt içermez (hassas içerik dışlanır). Öğrencinin metrik
raporu bu gerçek olayları toplar; deney ayrıca hiçbir olayda istem metninin sızmadığını doğrular.

İstemler zararsızdır. Model bu deney tarafından yüklendiyse sonunda boşaltılır.
"""
import ai_lab

ISTEMLER = [
    "İki artı iki kaçtır? Kısa yanıt ver.",
    "Türkiye'nin başkenti neresidir? Tek kelime.",
    "Suyun deniz seviyesinde kaynama sıcaklığı kaç derecedir? Kısa yanıt.",
]


def referans_rapor(olaylar):
    """Güvenli telemetri metrik referansı (geçerli olaylar varsayılır)."""
    gruplar, hatali, reddedildi, token_in, token_out = {}, 0, 0, 0, 0
    izler = set()
    for o in olaylar:
        izler.add(o["iz_id"])
        a = o["alanlar"]
        if a.get("durum") == "hata" or "hata_kodu" in a:
            hatali += 1
        if a.get("karar") == "reddet":
            reddedildi += 1
        token_in += a.get("token_in", 0)
        token_out += a.get("token_out", 0)
        gruplar.setdefault(o["tur"], []).append(o["sure_ms"])
    turler = {t: {"sayi": len(v), "ortalama_sure_ms": round(sum(v) / len(v), 3)} for t, v in sorted(gruplar.items())}
    return {"toplam": len(olaylar), "iz_sayisi": len(izler), "hatali": hatali, "reddedildi": reddedildi,
            "token_in": token_in, "token_out": token_out, "turler": turler}


AYARLAR={"sicaklik":0.2,"en_fazla":40,"tohumlar":[10,11,12],"num_ctx":4096,"istek_adedi":3}

def deney(telemetri_metrik_raporu):
    import time,math
    olaylar=[];kayitlar=[];hatalar=[];oturum=None
    try:
        with ai_lab.SohbetOturumu() as oturum:
            bas=time.perf_counter()
            for i,istem in enumerate(ISTEMLER):
                zaman=(time.perf_counter()-bas)*1000
                try:
                    c=oturum.sohbet([{"role":"user","content":istem}],seed=AYARLAR["tohumlar"][i],sicaklik=AYARLAR["sicaklik"],en_fazla=AYARLAR["en_fazla"])
                    sure=c["sure_ms"];token=c["eval_count"]
                    basarili=type(token) is int and token>0 and isinstance(c.get("icerik"),str) and bool(c["icerik"].strip()) and isinstance(sure,(int,float)) and math.isfinite(sure) and sure>=0
                    kayitlar.append({"istem":istem,"yanit":c,"basarili":basarili,"koken":"yalnız bu açık sentetik laboratuvar istemi"})
                    if not basarili:hatalar.append({"istek":i,"hata":"tamamlanmamış gerçek yanıt/ölçüm"});continue
                    olaylar.append({"iz_id":f"iz-{i}","olay_id":f"model-{i}","parent_id":None,"tur":"model","zaman_ms":zaman,"sure_ms":sure,"alanlar":{"model":oturum.model,"token_out":token,"durum":"ok"}})
                except Exception as exc:
                    hatalar.append({"istek":i,"hata":str(exc),"tur":type(exc).__name__})
                    kayitlar.append({"istem":istem,"basarili":False,"hata":str(exc)})
    finally:
        ortam=dict(oturum.kayit) if oturum else {}
    rapor=telemetri_metrik_raporu([dict(o,alanlar=dict(o["alanlar"])) for o in olaylar])
    metin=str(olaylar)
    sizan=[istem for istem in ISTEMLER if istem in metin]
    return {"ortam":ortam,"olaylar":olaylar,"rapor":rapor,"sizan_istem":sizan,"deney_kaydi":kayitlar,"hatalar":hatalar}


def ozet(r):
    return {"olay": r["rapor"]["toplam"], "iz": r["rapor"]["iz_sayisi"], "token_out": r["rapor"]["token_out"],
            "model_ort_sure_ms": r["rapor"]["turler"].get("model", {}).get("ortalama_sure_ms"),
            "sizan_istem": len(r["sizan_istem"])}


def goster(telemetri_metrik_raporu):
    """Çalıştır düğmesi: gerçek trafikten güvenli telemetri."""
    r = deney(telemetri_metrik_raporu)
    o = r["ortam"]
    print(f"Model: {(o.get('model') or {}).get('ad')} · {len(r['olaylar'])} gerçek istek → telemetri olayı\n")
    for e in r["olaylar"]:
        print(f"   {e['tur']} iz={e['iz_id']} sure={e['sure_ms']}ms alanlar={e['alanlar']}")
    print(f"\nMetrik raporu: {r['rapor']}")
    print(f"Mahremiyet: olaylarda sızan ham istem = {len(r['sizan_istem'])} (0 olmalı — telemetri içerik taşımaz)")
    print("Kanıt:", ai_lab.kanit_yaz("savunma-telemetri-calistir", {"kaynak": "gercek", "kabul": False, "ders": "ai-savunma-04",
                                                                   "ortam": o, "ozet": ozet(r), "olaylar":r["olaylar"], "rapor":r["rapor"], "laboratuvar_deney_kaydi":r["deney_kaydi"], "hatalar":r["hatalar"], "ayarlar":AYARLAR}))
