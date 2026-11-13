# -*- coding: utf-8 -*-
"""ai-savunma-01 gerçek deneyi: güven sınırı geçişleri soyut değil, gerçek etkileşimde oluşur. Gerçek yerel
model, araç verildiğinde bir araç çağrısı yaparsa model (model bölgesi) → araç (arac bölgesi) güven sınırını
GERÇEKTEN geçer. Deney canlı bir ajan etkileşimi koşar, gerçekleşen akışları çıkarır ve öğrencinin sınır
raporu bu gerçek akışlardaki geçişleri (özellikle güvenilmez model→araç geçişini) doğru işaretler mi ölçer.

Araçlar zararsız aritmetiktir. Model bu deney tarafından yüklendiyse sonunda boşaltılır.
"""
import json

import ai_lab

ARACLAR = {"topla": lambda a, b: a + b, "carp": lambda a, b: a * b}
OLLAMA_ARAC = [{"type": "function", "function": {
    "name": ad, "description": {"topla": "iki sayıyı toplar", "carp": "iki sayıyı çarpar"}[ad],
    "parameters": {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}, "required": ["a", "b"]}}}
    for ad in ("topla", "carp")]
GOREV = "Önce 5 ile 3'ü topla, sonra sonucu 4 ile çarp. Her adım için verilen araçları kullan."
# Sabit mimari envanter (gerçek sistemin bileşenleri)
BILESENLER = [
    {"id": "carp", "tur": "arac", "sinir": "arac"},
    {"id": "gecit", "tur": "api", "sinir": "uygulama"},
    {"id": "kullanici", "tur": "kullanici", "sinir": "dis"},
    {"id": "model", "tur": "model", "sinir": "model"},
    {"id": "topla", "tur": "arac", "sinir": "arac"},
]


def referans_rapor(bilesenler, baglantilar):
    bolge = {b["id"]: b["sinir"] for b in bilesenler}
    out = [{"kaynak": a["kaynak"], "hedef": a["hedef"], "kanal": a["kanal"],
            "sinir_gecisi": bolge[a["kaynak"]] != bolge[a["hedef"]]} for a in baglantilar]
    return sorted(out, key=lambda x: (x["kaynak"], x["hedef"], x["kanal"]))


def deney(canli_gecis_raporu, sicaklik=0.1):
    cagrilan = set()
    turler = 0
    with ai_lab.SohbetOturumu(araclar_gerekli=True) as oturum:
        mesajlar = [{"role": "system", "content": "Sen hesap asistanısın. Aritmetik için yalnız verilen araçları kullan."},
                    {"role": "user", "content": GOREV}]
        for tur in range(6):
            c = oturum.sohbet(mesajlar, seed=7 + tur, sicaklik=sicaklik, en_fazla=400, araclar=OLLAMA_ARAC)
            turler += 1
            tc = c["arac_cagrilari"]
            if not tc:
                break
            mesajlar.append({"role": "assistant", "content": c["icerik"], "tool_calls": tc})
            for t in tc:
                fn = t.get("function") or {}
                ad = fn.get("name")
                arg = fn.get("arguments")
                if isinstance(arg, str):
                    try:
                        arg = json.loads(arg)
                    except ValueError:
                        arg = {}
                if ad in ARACLAR:
                    cagrilan.add(ad)
                try:
                    sonuc = ARACLAR[ad](**arg) if (ad in ARACLAR and isinstance(arg, dict)) else "bilinmeyen araç"
                except Exception:
                    sonuc = "araç hatası"
                mesajlar.append({"role": "tool", "tool_name": ad, "content": json.dumps(sonuc)})
        ortam = dict(oturum.kayit)
    ortam["temizlik"] = oturum.kayit.get("temizlik")
    # Gerçekte oluşan akışlar: kullanıcı→geçit, geçit→model her zaman; model↔araç yalnız gerçekten çağrılan araç için
    baglantilar = [{"kaynak": "kullanici", "hedef": "gecit", "kanal": "http"},
                   {"kaynak": "gecit", "hedef": "model", "kanal": "ipc"}]
    for ad in sorted(cagrilan):
        baglantilar.append({"kaynak": "model", "hedef": ad, "kanal": "ipc"})
        baglantilar.append({"kaynak": ad, "hedef": "model", "kanal": "ipc"})
    rapor = canli_gecis_raporu([dict(b) for b in BILESENLER], [dict(a) for a in baglantilar])
    return {"ortam": ortam, "gorev": GOREV, "bilesenler": BILESENLER, "baglantilar": baglantilar,
            "cagrilan_arac": sorted(cagrilan), "tur": turler, "rapor": rapor}


def ozet(r):
    gecis = [x for x in r["rapor"] if x["sinir_gecisi"]]
    model_arac = [x for x in gecis if x["kaynak"] == "model" and x["hedef"] in ("topla", "carp")]
    return {"baglanti": len(r["rapor"]), "sinir_gecisi": len(gecis), "cagrilan_arac": r["cagrilan_arac"],
            "model_arac_gecisi": len(model_arac), "tur": r["tur"]}


def goster(canli_gecis_raporu):
    """Çalıştır düğmesi: canlı güven sınırı geçişleri."""
    r = deney(canli_gecis_raporu)
    o = r["ortam"]
    print(f"Model: {(o.get('model') or {}).get('ad')} · görev: {r['gorev']}")
    print(f"Model gerçekte çağırdığı araçlar: {r['cagrilan_arac']} ({r['tur']} tur)\n")
    print("Canlı güven sınırı raporu (gerçekleşen akışlar):")
    for x in r["rapor"]:
        isaret = "⚠ SINIR GEÇİŞİ" if x["sinir_gecisi"] else "aynı bölge"
        print(f"   {x['kaynak']:9} → {x['hedef']:9} [{x['kanal']}]  {isaret}")
    oz = ozet(r)
    print(f"\nÖzet: {oz['sinir_gecisi']}/{oz['baglanti']} akış güven sınırı geçiyor; "
          f"model→araç geçişi: {oz['model_arac_gecisi']} (güvenilmez model çıktısı aracı tetikledi — kontrol şart)")
    print("Kanıt:", ai_lab.kanit_yaz("savunma-sinir-calistir", {"kaynak": "gercek", "kabul": False, "ders": "ai-savunma-01",
                                                               "ortam": o, "ozet": oz}))
