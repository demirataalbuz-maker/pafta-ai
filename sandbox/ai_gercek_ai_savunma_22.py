# -*- coding: utf-8 -*-
"""ai-savunma-22 gerçek deneyi: korelasyonlu telemetri gerçek bir istek zincirinden üretilir.

Deney gerçek yerel modeli bir araçla (topla) koşar ve tek bir iz kimliği altında GERÇEK zaman damgalı
telemetri olayları üretir: iste → guardrail → model → arac. Model olayının detayında gerçek süre ve
token sayısı, araç olayında gerçekte çağrılan araç bulunur; zaman damgaları gerçek duvar saatinden
ölçülür. İkinci bir iz, yalnız iste+model taşıyan EKSİK bir zincirdir.

Öğrencinin `korelasyonlu_iz_raporu` işlevi olayları iz kimliğine göre ilişkilendirir. Kritik ölçüm:
dört türü de bir kez taşıyan, tek model sürümlü ve süre bütçesindeki gerçek zincir `tam`; guardrail ve
araç olayı eksik olan zincir `hatali` (eksik nedeni). Böylece eksik/tutarsız telemetri gizlenmez.

Araç zararsız aritmetiktir ve modelin verdiği argümanlarla gerçekten çalıştırılır. Model aracı çağırmazsa
arac olayı yazılmaz; doğru rapor bu izi 'eksik' sayar (kabul koşulu modelin aracı çağırması değildir).
Boş yanıt deneyi durdurur. Ham araç çağrıları ve model yanıtı kanıta yazılır. Model bu deney tarafından
yüklendiyse boşaltılır. `korelasyonlu_iz_raporu_referans` yalnız test içindir.
"""
import json
import re
import time

import ai_lab

ARACLAR = {"topla": lambda a, b: a + b}
OLLAMA_ARAC = [{"type": "function", "function": {
    "name": "topla", "description": "iki sayiyi toplar",
    "parameters": {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}, "required": ["a", "b"]}}}]
GOREV = "5 ile 3'ü topla aracını kullanarak topla ve sonucu söyle."
POLITIKA = {"max_olay": 10, "max_sure_ms": 60000, "iz_zorunlu": True, "surum_zorunlu": True}


def _surum(ad):
    s = re.sub(r"[^A-Za-z0-9._-]", "-", ad or "model")[:32]
    return s if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,31}", s) else "model-x"


def _argumanlar(cagri):
    fn = cagri.get("function") or {}
    arg = fn.get("arguments")
    if isinstance(arg, str):
        try:
            arg = json.loads(arg)
        except ValueError:
            arg = None
    return fn.get("name"), arg if isinstance(arg, dict) else None


def deney(korelasyonlu_iz_raporu):
    cagrilan, arac_kaydi = None, None
    with ai_lab.SohbetOturumu(araclar_gerekli=True) as oturum:
        surum = _surum(oturum.model)
        t0 = time.monotonic()
        # guardrail: istek metninde bilinen iki injection kalıbını arayan küçük ama gerçek bir kontrol
        guard_engel = any(x in GOREV.casefold() for x in ("ignore", "yok say"))
        t_guard = int((time.monotonic() - t0) * 1000)
        mesajlar = [{"role": "system", "content": "Sen hesap asistanısın; aritmetik için verilen aracı kullan."},
                    {"role": "user", "content": GOREV}]
        c = oturum.sohbet(mesajlar, seed=7, sicaklik=0.0, en_fazla=300, araclar=OLLAMA_ARAC)
        t_model = int((time.monotonic() - t0) * 1000)
        model_sure = c.get("sure_ms")
        tokens = c.get("eval_count")
        icerik = c.get("icerik") or ""
        cagrilar = c.get("arac_cagrilari") or []
        if not icerik.strip() and not cagrilar:
            raise ai_lab.GercekLabYok("model ne metin ne araç çağrısı döndürdü; deney tamamlanmadı")
        for cagri in cagrilar:
            ad, arg = _argumanlar(cagri)
            if ad in ARACLAR:
                try:
                    sonuc = ARACLAR[ad](float(arg["a"]), float(arg["b"]))
                    hata = None
                except (KeyError, TypeError, ValueError) as e:
                    sonuc, hata = None, type(e).__name__
                cagrilan = ad
                arac_kaydi = {"ad": ad, "argumanlar": arg, "sonuc": sonuc, "hata": hata}
                break
        t_arac = int((time.monotonic() - t0) * 1000)
        ortam = dict(oturum.kayit)
    ortam["ayarlar"] = {"sicaklik": 0.0, "en_fazla": 300, "seed": 7, "gorev": GOREV, "politika": dict(POLITIKA),
                        "guardrail": "istek metninde 'ignore'/'yok say' arama", "eksik_iz": "aynı koşudan guardrail ve araç olayı loglanmamış gibi kurulan ikinci iz"}

    olaylar = [
        {"id": "o-iste", "iz_id": "z-tam", "tur": "iste", "zaman_ms": 0, "model_surumu": surum, "detay": "istek alindi"},
        {"id": "o-guard", "iz_id": "z-tam", "tur": "guardrail", "zaman_ms": max(0, t_guard), "model_surumu": surum,
         "detay": "girdi guardrail karari " + ("engel" if guard_engel else "gecti")},
        {"id": "o-model", "iz_id": "z-tam", "tur": "model", "zaman_ms": max(1, t_model), "model_surumu": surum,
         "detay": f"model sure_ms={model_sure} tokens={tokens} arac_cagrisi={len(cagrilar)}"},
    ]
    if arac_kaydi:
        detay = (f"arac {cagrilan} sonuc={arac_kaydi['sonuc']}" if arac_kaydi["hata"] is None
                 else f"arac {cagrilan} hata={arac_kaydi['hata']}")
        olaylar.append({"id": "o-arac", "iz_id": "z-tam", "tur": "arac", "zaman_ms": max(2, t_arac),
                        "model_surumu": surum, "detay": detay})
    olaylar += [
        {"id": "e-iste", "iz_id": "z-eksik", "tur": "iste", "zaman_ms": 0, "model_surumu": surum, "detay": "istek alindi"},
        {"id": "e-model", "iz_id": "z-eksik", "tur": "model", "zaman_ms": max(1, t_model), "model_surumu": surum, "detay": "model yaniti"},
    ]
    rapor = korelasyonlu_iz_raporu([dict(o) for o in olaylar], dict(POLITIKA))
    rapor_map = {r["iz_id"]: r for r in rapor} if isinstance(rapor, list) and all(isinstance(r, dict) and "iz_id" in r for r in rapor) else {}
    return {"ortam": ortam, "surum": surum, "cagrilan": cagrilan, "arac": arac_kaydi, "model_sure": model_sure, "tokens": tokens,
            "model_yaniti": icerik[:600], "ham_arac_cagrilari": cagrilar, "olaylar": olaylar, "rapor": rapor,
            "tam_karar": rapor_map.get("z-tam", {}).get("karar"), "tam_sure": rapor_map.get("z-tam", {}).get("sure_ms"),
            "tam_nedenler": rapor_map.get("z-tam", {}).get("nedenler"),
            "eksik_karar": rapor_map.get("z-eksik", {}).get("karar"), "eksik_nedenler": rapor_map.get("z-eksik", {}).get("nedenler")}


def ozet(r):
    return {"olay": len(r["olaylar"]), "cagrilan_arac": r["cagrilan"], "arac": r["arac"], "model_sure_ms": r["model_sure"],
            "tokens": r["tokens"], "tam_karar": r["tam_karar"], "tam_nedenler": r["tam_nedenler"], "tam_sure_ms": r["tam_sure"],
            "eksik_karar": r["eksik_karar"], "eksik_nedenler": r["eksik_nedenler"]}


def ham(r):
    return {"model_yaniti": r["model_yaniti"], "arac_cagrilari": r["ham_arac_cagrilari"], "olaylar": r["olaylar"]}


def goster(korelasyonlu_iz_raporu):
    """Çalıştır düğmesi: gerçek istek zincirinden korelasyonlu telemetri."""
    r = deney(korelasyonlu_iz_raporu)
    o = r["ortam"]
    print(f"Model: {(o.get('model') or {}).get('ad')} · sürüm etiketi: {r['surum']} · çağrılan araç: {r['cagrilan']}\n")
    print(f"   Gerçek model süresi: {r['model_sure']} ms · token: {r['tokens']} · araç kaydı: {r['arac']}")
    print(f"   Ham araç çağrıları: {r['ham_arac_cagrilari']}")
    print("   Gerçek olay zinciri (z-tam):")
    for olay in [x for x in r["olaylar"] if x["iz_id"] == "z-tam"]:
        print(f"      [{olay['zaman_ms']:>5} ms] {olay['tur']:9} · {olay['detay']}")
    for rec in r["rapor"] if isinstance(r["rapor"], list) else []:
        print(f"   iz {rec.get('iz_id')}: karar={rec.get('karar')} nedenler={rec.get('nedenler')} süre={rec.get('sure_ms')}ms sürümler={rec.get('model_surumleri')}")
    oz = ozet(r)
    print(f"\nTam zincir: {oz['tam_karar']} {oz['tam_nedenler']} · Eksik zincir: {oz['eksik_karar']} {oz['eksik_nedenler']}")
    if not r["cagrilan"]:
        print("Not: model bu koşuda aracı çağırmadı; z-tam izinde arac olayı yok ve doğru rapor onu 'eksik' saymalıdır.")
    print("Kanıt:", ai_lab.kanit_yaz("savunma-telemetri-calistir", {"kaynak": "gercek", "kabul": False, "ders": "ai-savunma-22",
                                                                   "ortam": o, "ozet": oz, "ham": ham(r)}))


def korelasyonlu_iz_raporu_referans(olaylar, politika):
    """Yalnız test içindir: politika/olay doğrulaması, iz gruplama ve dört nedenle bağımsız rapor."""
    kimlik = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")
    if not isinstance(politika, dict) or set(politika) != {"max_olay", "max_sure_ms", "iz_zorunlu", "surum_zorunlu"}:
        raise ValueError("politika şeması geçersiz")
    if type(politika["max_olay"]) is not int or not 1 <= politika["max_olay"] <= 100:
        raise ValueError("olay sınırı geçersiz")
    if type(politika["max_sure_ms"]) is not int or not 1 <= politika["max_sure_ms"] <= 60000:
        raise ValueError("süre sınırı geçersiz")
    if politika["iz_zorunlu"] is not True or politika["surum_zorunlu"] is not True:
        raise ValueError("zorunluluklar True olmalı")
    if not isinstance(olaylar, list) or len(olaylar) > politika["max_olay"]:
        raise ValueError("olay listesi geçersiz")
    gorulen, izler = set(), {}
    for o in olaylar:
        if not isinstance(o, dict) or set(o) != {"id", "iz_id", "tur", "zaman_ms", "model_surumu", "detay"}:
            raise ValueError("olay şeması geçersiz")
        if not isinstance(o["id"], str) or not kimlik.fullmatch(o["id"]) or o["id"] in gorulen:
            raise ValueError("olay kimliği geçersiz")
        gorulen.add(o["id"])
        if not isinstance(o["iz_id"], str) or not kimlik.fullmatch(o["iz_id"]):
            raise ValueError("iz kimliği geçersiz")
        if o["tur"] not in ("iste", "guardrail", "model", "arac"):
            raise ValueError("tür geçersiz")
        if type(o["zaman_ms"]) is not int or o["zaman_ms"] < 0:
            raise ValueError("zaman geçersiz")
        if not isinstance(o["model_surumu"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,31}", o["model_surumu"]):
            raise ValueError("model sürümü geçersiz")
        d = o["detay"]
        if not isinstance(d, str) or not d or d != d.strip() or any(ord(k) < 32 for k in d):
            raise ValueError("detay geçersiz")
        izler.setdefault(o["iz_id"], []).append(o)
    rapor = []
    for iz_id in sorted(izler):
        grup = izler[iz_id]
        sayim = {tur: sum(1 for o in grup if o["tur"] == tur) for tur in ("iste", "guardrail", "model", "arac")}
        zamanlar = [o["zaman_ms"] for o in grup]
        sure = max(zamanlar) - min(zamanlar)
        surumler = sorted({o["model_surumu"] for o in grup})
        nedenler = [n for n, kosul in (("eksik", any(v == 0 for v in sayim.values())), ("yinelenen", any(v > 1 for v in sayim.values())),
                                        ("sure", sure > politika["max_sure_ms"]), ("surum", len(surumler) > 1)) if kosul]
        rapor.append({"iz_id": iz_id, "karar": "hatali" if nedenler else "tam", "nedenler": nedenler, "sure_ms": sure, "model_surumleri": surumler})
    return rapor
