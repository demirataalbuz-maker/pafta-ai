"""Speculative decoding paket boyutu yan kanalı ve sabit boyutlu paket dolgusu: gerçek SmolLM2-135M'de açgözlü kendi kendine
spekülatif çözmenin paket dizisinden kurbanın gizli bağlamını parmak izi ile bulma."""
import copy, importlib.metadata, math, random, secrets
import ai_lab

AYAR = {
    "seed": 59,
    "gamma": 4,
    "taslak_katman": 20,
    "uretilen_token": 40,
    "taban_oran": 0.2,
}


def _sayi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)


def referans_hiz(paket_token_sayilari, sure_ms_listesi):
    if not isinstance(paket_token_sayilari, list) or not isinstance(sure_ms_listesi, list):
        raise ValueError("liste")
    if not paket_token_sayilari or len(paket_token_sayilari) != len(sure_ms_listesi):
        raise ValueError("boyut")
    for k in paket_token_sayilari:
        if isinstance(k, bool) or not isinstance(k, int) or k < 1:
            raise ValueError("token")
    for s in sure_ms_listesi:
        if not _sayi(s) or s <= 0:
            raise ValueError("süre")
    n = len(paket_token_sayilari)
    top_tok = sum(paket_token_sayilari)
    top_sn = sum(sure_ms_listesi) / 1000.0
    return {
        "ortalama_paket_token": top_tok / n,
        "saniyede_token": top_tok / top_sn,
        "spekulatif_oran": sum(1 for k in paket_token_sayilari if k > 1) / n,
    }


def referans_puanla(aday_kabul_oranlari, taban_oran):
    if not isinstance(aday_kabul_oranlari, dict) or not aday_kabul_oranlari:
        raise ValueError("adaylar")
    if not _sayi(taban_oran) or not 0 <= taban_oran < 1:
        raise ValueError("taban")
    for k, v in aday_kabul_oranlari.items():
        if not isinstance(k, str) or not k or not _sayi(v) or not 0 <= v <= 1:
            raise ValueError("eleman")
    en_iyi = min(aday_kabul_oranlari, key=lambda k: (-aday_kabul_oranlari[k], k))
    en_deger = aday_kabul_oranlari[en_iyi]
    guven = max(0.0, (en_deger - taban_oran) / (1.0 - taban_oran))
    return {
        "en_olasi_onek": en_iyi,
        "sizinti_guveni": guven,
        "anomali": (en_deger - taban_oran) >= 0.25,
    }


def referans_dolgu(paket_token_sayilari, hedef_sabit_boyut):
    if not isinstance(paket_token_sayilari, list) or not paket_token_sayilari:
        raise ValueError("liste")
    for k in paket_token_sayilari:
        if isinstance(k, bool) or not isinstance(k, int) or k < 1:
            raise ValueError("token")
    if isinstance(hedef_sabit_boyut, bool) or not isinstance(hedef_sabit_boyut, int) or hedef_sabit_boyut < max(paket_token_sayilari):
        raise ValueError("hedef_sabit_boyut")
    dolgu = [hedef_sabit_boyut - k for k in paket_token_sayilari]
    top_g = sum(paket_token_sayilari)
    top_d = sum(dolgu)
    return {
        "dolgu_listesi": dolgu,
        "toplam_dolgu": top_d,
        "ek_yuk_orani": top_d / (top_g + top_d),
    }


def _yakin(a, b, tol=1e-9):
    if isinstance(a, dict):
        return isinstance(b, dict) and set(a) == set(b) and all(_yakin(a[k], b[k], tol) for k in a)
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(_yakin(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, (bool, str)) or a is None:
        return type(a) is type(b) and a == b
    return _sayi(a) and _sayi(b) and abs(a - b) <= tol * max(1.0, abs(a), abs(b))


ADAYLAR = {"dusuk": "Internal note. Credit risk: low. The customer has paid every invoice on time for six years.",
           "orta": "Internal note. Credit risk: medium. The customer paid two invoices late last quarter.",
           "yuksek": "Internal note. Credit risk: high. The customer has three unpaid invoices and a court case.",
           "belirsiz": "Internal note. Credit risk: unknown. The customer opened the account last week."}
SORU = "\nWrite a short reply to the customer about their account:"


def _sunucu(ss, tok, torch, metin, cihaz):
    """Açgözlü (sıcaklık 0) kendi kendine spekülatif çözme; her tur kabul edilen tokenları tek pakette gönderir.
    Döndürür: (paket token sayıları, tur süreleri ms)."""
    import time
    ids = tok(metin, add_special_tokens=False)["input_ids"]
    G, cikis = AYAR["gamma"], AYAR["taslak_katman"]
    paketler, sureler, uretilen = [], [], 0
    while uretilen < AYAR["uretilen_token"]:
        if cihaz == "cuda":
            torch.cuda.synchronize()
        t0 = time.perf_counter()
        taslak = []
        for _ in range(G):
            taslak.append(int(ss.dagilim(ids + taslak, cikis)[-1].argmax()))
        P = ss.dagilim(ids + taslak)[len(ids) - 1:]
        kabul = 0
        while kabul < G and int(P[kabul].argmax()) == taslak[kabul]:
            kabul += 1
        yeni = taslak[:kabul] + [int(P[kabul].argmax())]
        if cihaz == "cuda":
            torch.cuda.synchronize()
        sureler.append(round((time.perf_counter() - t0) * 1000.0, 3))
        paketler.append(len(yeni))
        ids = ids + yeni
        uretilen += len(yeni)
    return paketler, sureler


def deney(hiz_fn, puan_fn, dolgu_fn):
    try:
        import torch
    except ImportError as e:
        raise ai_lab.GercekLabYok(str(e)) from e
    from sandbox.ai_gercek_ai_temel_27 import _SelfSpec
    tok, model, bilgi = ai_lab.dil_modeli()
    cihaz = ai_lab.torch_cihazi()
    model.to(cihaz)
    ss = _SelfSpec(torch, model, cihaz)
    gamma = AYAR["gamma"]
    rng = random.Random(secrets.randbits(64))
    gizli = rng.choice(sorted(ADAYLAR))
    gozlenen, gozlenen_sure = _sunucu(ss, tok, torch, ADAYLAR[gizli] + SORU, cihaz)

    hiz_ayni = puan_ayni = dolgu_ayni = True
    r_h = referans_hiz(gozlenen, gozlenen_sure)
    hiz_ayni = _yakin(hiz_fn(list(gozlenen), list(gozlenen_sure)), r_h)

    # Saldırgan: model açık; her adayı yerelde yeniden koşar, paket boyutu dizisini gözlenenle karşılaştırır.
    simule = {ad: _sunucu(ss, tok, torch, metin + SORU, cihaz)[0] for ad, metin in ADAYLAR.items()}

    def eslesme(a, b):
        n = min(len(a), len(b))
        return round(sum(1 for i in range(n) if a[i] == b[i]) / max(len(a), len(b)), 4)

    oran = {ad: eslesme(gozlenen, s) for ad, s in simule.items()}
    r_p = referans_puanla(oran, AYAR["taban_oran"])
    puan_ayni = _yakin(puan_fn(dict(oran), AYAR["taban_oran"]), r_p)
    sirali = sorted(oran.values(), reverse=True)

    # Savunma: her paket gamma + 1 tokena doldurulur; saldırgan yalnız sabit boyutlu paketler görür.
    r_d = referans_dolgu(gozlenen, gamma + 1)
    dolgu_ayni = _yakin(dolgu_fn(list(gozlenen), gamma + 1), r_d)
    dolgulu = [k + d for k, d in zip(gozlenen, r_d["dolgu_listesi"])]
    oran_d = {ad: eslesme(dolgulu, [gamma + 1] * len(s)) for ad, s in simule.items()}
    sirali_d = sorted(oran_d.values(), reverse=True)
    return {
        "cihaz": str(cihaz), "dtype": "float32",
        "model": {k: bilgi[k] for k in ("model", "revizyon", "agirlik_sha256", "parametre")},
        "surumler": {"torch": importlib.metadata.version("torch"), "transformers": importlib.metadata.version("transformers")},
        "ayarlar": AYAR,
        "gizli_onek": gizli, "gozlenen_paketler": gozlenen, "gozlenen_hiz": r_h,
        "simule_paketler": simule, "aday_oranlari": oran, "puan_sonucu": r_p,
        "dogru_tahmin": r_p["en_olasi_onek"] == gizli, "ayirt_edicilik": sirali[0] - sirali[1],
        "dolgu": {"ek_yuk_orani": r_d["ek_yuk_orani"], "aday_oranlari": oran_d, "ayirt_edicilik": sirali_d[0] - sirali_d[1]},
        "hiz_ayni": hiz_ayni, "puan_ayni": puan_ayni, "dolgu_ayni": dolgu_ayni,
        "olcum": (f"SmolLM2-135M açgözlü kendi kendine spekülatif çözme (taslak katman {AYAR['taslak_katman']}, γ={gamma}); gizli bağlam '{gizli}'. "
                  f"Gözlenen paket boyutları {gozlenen[:12]}…; adayların yeniden koşuyla eşleşme oranları {oran}; tahmin "
                  f"'{r_p['en_olasi_onek']}' ({'doğru' if r_p['en_olasi_onek'] == gizli else 'yanlış'}), ayırt edicilik {sirali[0] - sirali[1]:.3f}. "
                  f"Sabit boyut dolgusuyla ayırt edicilik {sirali_d[0] - sirali_d[1]:.3f}, bant genişliği ek yükü {r_d['ek_yuk_orani']:.2f}."),
        "sinir": ("Açgözlü çözmede paket dizisi deterministiktir, saldırgan modeli bilir ve aday sayısı küçüktür. Örneklemeli üretim, bilinmeyen "
                  "model, TLS kayıt birleştirme ve ağ gürültüsü bu deneyde yoktur; zaman yan kanalı ölçülür ama dolgu yalnız boyutu kapatır."),
    }


def goster(hiz_fn, puan_fn, dolgu_fn):
    r = deney(hiz_fn, puan_fn, dolgu_fn)
    print("Model:", r["model"]["model"], "| cihaz:", r["cihaz"], "| gizli bağlam:", r["gizli_onek"], "| tahmin:", r["puan_sonucu"]["en_olasi_onek"])
    print("Gözlenen paketler:", r["gozlenen_paketler"], "| hız:", r["gozlenen_hiz"])
    print("Eşleşme oranları:", r["aday_oranlari"], "| ayırt edicilik:", round(r["ayirt_edicilik"], 3))
    print("Dolgu sonrası:", r["dolgu"])
    print("Sınır:", r["sinir"])
    print("Kanıt:", ai_lab.kanit_yaz("ai-saldiri-59-run", {"kaynak": "gercek", "kabul": False, "ders": "ai-saldiri-59", "deney": r}))
