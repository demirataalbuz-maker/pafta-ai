# -*- coding: utf-8 -*-
"""ai-temel-23 gerçek deneyi: gerçek yerel modelle bir ajan döngüsü. Model şemalı araç çağrıları üretir,
öğrencinin dispatch işlevi (arac_calistir) her çağrıyı şemaya göre doğrulayıp sandbox'taki Python araçlarını
çalıştırır, sonuç bağlama geri eklenir ve döngü ya modelin son yanıtıyla ya da tur sınırında biter.

Araçlar zararsız aritmetiktir (topla, carp). Model bu deney yüklediyse sonunda boşaltılır.
"""
import json
import copy
import math

import ai_lab

# Sandbox araçları (gerçek Python işlevleri) ve şemaları
ARACLAR = {"topla": lambda a, b: a + b, "carp": lambda a, b: a * b}
SEMALAR = {"topla": {"gerekli": ["a", "b"], "tipler": {"a": "sayi", "b": "sayi"}},
           "carp": {"gerekli": ["a", "b"], "tipler": {"a": "sayi", "b": "sayi"}}}
# Ollama'ya verilen araç tanımları
OLLAMA_ARAC = [{"type": "function", "function": {
    "name": ad, "description": {"topla": "iki sayıyı toplar", "carp": "iki sayıyı çarpar"}[ad],
    "parameters": {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}, "required": ["a", "b"]}}}
    for ad in ("topla", "carp")]

GOREV = "23 ile 19'u çarp, sonucuna 7 ekle. Her adım için verilen araçları kullan ve sonucu tek sayı olarak söyle."
BEKLENEN = 23 * 19 + 7  # 444


def referans_calistir(cagri, semalar, araclar, *, sema_yok=False, tip_yok=False):
    """Şema doğrulama + dispatch (varsayılan doğru); mutantlar şema/tip denetimini atlar.
    Girdi yapısı bozuksa ValueError; modelin hatalı çağrısı için hata sözlüğü döner (döngü çökmesin)."""
    ad = cagri["ad"]
    arg = cagri["arg"]
    if ad not in semalar or ad not in araclar:
        return {"durum": "hata", "hata": f"bilinmeyen araç: {ad}"}
    sema = semalar[ad]
    if not sema_yok and set(arg) != set(sema["gerekli"]):
        return {"durum": "hata", "hata": "argüman anahtarları şemayla uyuşmuyor"}
    if not sema_yok and not tip_yok:
        for anahtar, tip in sema["tipler"].items():
            v = arg.get(anahtar)
            if tip == "sayi" and (isinstance(v, bool) or not isinstance(v, (int, float)) or (isinstance(v,float) and not math.isfinite(v))):
                return {"durum": "hata", "hata": f"{anahtar} sayı olmalı"}
            if tip == "metin" and not isinstance(v, str):
                return {"durum": "hata", "hata": f"{anahtar} metin olmalı"}
    try:
        return {"durum": "ok", "sonuc": araclar[ad](**arg)}
    except Exception as e:
        return {"durum": "hata", "hata": f"araç hatası: {type(e).__name__}"}


def _arg_coz(ham):
    if isinstance(ham, str):
        try:
            ham = json.loads(ham)
        except ValueError:
            return {}
    return ham if isinstance(ham, dict) else {}


def deney(arac_calistir, tur_siniri=6):
    with ai_lab.SohbetOturumu(araclar_gerekli=True) as oturum:
        mesajlar = [{"role": "system", "content": "Sen hesap yapan bir asistansın. Aritmetik için yalnız verilen araçları kullan."},
                    {"role": "user", "content": GOREV}]
        turler, cagrilar, final, hata = [], [], None, None
        ham_turlar=[]
        for tur in range(tur_siniri):
            iz={"tur":tur,"mesajlar":copy.deepcopy(mesajlar),"seed":7+tur,"sicaklik":0.1,"en_fazla":400,"arac_tanimlari":copy.deepcopy(OLLAMA_ARAC)}
            ham_turlar.append(iz)
            try:
                c = oturum.sohbet(mesajlar, seed=7 + tur, sicaklik=0.1, en_fazla=400, araclar=OLLAMA_ARAC)
            except Exception as e:
                hata = f"{type(e).__name__}: {e}"
                iz["hata"]=hata
                break
            iz["yanit"]=copy.deepcopy(c)
            tc = c["arac_cagrilari"]
            turler.append({"tur": tur, "arac_cagri_sayisi": len(tc), "icerik": c["icerik"][:200], "sure_ms": c["sure_ms"]})
            if not tc:
                final = c["icerik"]
                break
            mesajlar.append({"role": "assistant", "content": c["icerik"], "tool_calls": tc})
            for t in tc:
                fn = t.get("function") or {}
                ad = fn.get("name")
                arg = _arg_coz(fn.get("arguments"))
                cagri = {"ad": ad if isinstance(ad, str) else "", "arg": arg}
                sonuc = arac_calistir(dict(cagri), {k: dict(v) for k, v in SEMALAR.items()}, dict(ARACLAR))
                beklenen = ARACLAR[ad](**arg) if (ad in ARACLAR and set(arg) == {"a", "b"}
                                                  and all(isinstance(arg[x], (int, float)) and not isinstance(arg[x], bool) for x in arg)) else None
                cagrilar.append({"ad": ad, "arg": arg, "sonuc": sonuc, "beklenen": beklenen,
                                 "dogru": sonuc.get("durum") == "ok" and beklenen is not None and sonuc.get("sonuc") == beklenen})
                mesajlar.append({"role": "tool", "tool_name": ad,
                                 "content": json.dumps(sonuc.get("sonuc") if sonuc.get("durum") == "ok" else {"hata": sonuc.get("hata")})})
        ortam = dict(oturum.kayit)
    ortam["temizlik"] = oturum.kayit.get("temizlik")
    return {"ortam": ortam, "gorev": GOREV, "beklenen": BEKLENEN, "turler": turler, "cagrilar": cagrilar,
            "final": final, "hata": hata, "tur_siniri": tur_siniri,"ham_turlar":ham_turlar,"gecmis":mesajlar,
            "durum":"model_hatasi" if hata else ("tamam" if final is not None else "adim_siniri")}


def ozet(r):
    dogru = [c for c in r["cagrilar"] if c["dogru"]]
    from decimal import Decimal,InvalidOperation
    try:
        sayi=Decimal((r["final"] or "").strip())
        final_dogru=sayi.is_finite() and sayi==Decimal(r["beklenen"])
    except (InvalidOperation,ValueError):
        final_dogru=False
    return {"tur": len(r["turler"]), "arac_cagri": len(r["cagrilar"]), "dogru_cagri": len(dogru),
            "kullanilan_araclar": sorted({c["ad"] for c in r["cagrilar"] if c["ad"]}),
            "final_dogru": final_dogru,"final_olcutu":"Tam metnin sonlu Decimal değeri beklenen sayıya eşit",
            "final": (r["final"] or "")[:160]}


def goster(arac_calistir):
    """Çalıştır düğmesi: gerçek ajan döngüsü."""
    r = deney(arac_calistir)
    o = r["ortam"]
    print(f"Model: {(o.get('model') or {}).get('ad')} · görev: {r['gorev']}\n")
    for t in r["turler"]:
        print(f"[tur {t['tur']}] araç çağrısı: {t['arac_cagri_sayisi']} · {t['sure_ms']}ms · {t['icerik'][:80]!r}")
    for c in r["cagrilar"]:
        print(f"   {c['ad']}({c['arg']}) → {c['sonuc']}  (doğru: {c['dogru']})")
    oz = ozet(r)
    print(f"\nDöngü: {oz['tur']} tur, {oz['arac_cagri']} araç çağrısı ({oz['dogru_cagri']} doğru), araçlar {oz['kullanilan_araclar']}")
    print(f"Final: {oz['final']!r} · beklenen {r['beklenen']} · final doğru: {oz['final_dogru']}")
    print("Kanıt:", ai_lab.kanit_yaz("temel-ajan-calistir", {"kaynak": "gercek", "kabul": False, "ders": "ai-temel-23",
                                                            "ortam": o, "deney": r, "ozet": oz}))
