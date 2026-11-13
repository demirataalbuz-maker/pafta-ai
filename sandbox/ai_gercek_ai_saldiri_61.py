"""Mixture-of-Experts (MoE) expert overflow ve çapraz kiracı batch yan kanalı: SmolLM2-135M'in gerçek MLP bloğundan damıtılan
top-1 MoE'de saldırganın tek bir uzmanı doldurması, kurban tokenlerinin düşmesi, kiracı kotası ve sıralama yan kanalı."""
import copy, importlib.metadata, math, random, secrets
import ai_lab

AYAR = {
    "seed": 61,
    "katman": 15,
    "uzman_sayisi": 8,
    "aux_katsayi": 1.0,
    "kapasite_faktoru": 2.5,
    "kiraci_kota": 2,
    "saldirgan_token": 48,
    "aday_bas": 256,
    "aday_token": 1024,
    "aday_grup": 256,
}


def _uzman_listesi(lst, bos_izin=True):
    if not isinstance(lst, list) or (not bos_izin and not lst):
        raise ValueError("liste")
    for u in lst:
        if isinstance(u, bool) or not isinstance(u, int) or u < 0:
            raise ValueError("uzman")
    return lst


def referans_doyurma(saldirgan_istekleri, kurban_istekleri, kapasite):
    _uzman_listesi(saldirgan_istekleri, True)
    _uzman_listesi(kurban_istekleri, True)
    if not saldirgan_istekleri and not kurban_istekleri:
        raise ValueError("boş")
    if isinstance(kapasite, bool) or not isinstance(kapasite, int) or kapasite < 1:
        raise ValueError("kapasite")
    sayim = {}
    for u in saldirgan_istekleri + kurban_istekleri:
        sayim[u] = sayim.get(u, 0) + 1
    yuk = {u: sayim[u] for u in sorted(sayim)}
    tasan = [u for u, s in yuk.items() if s > kapasite]
    toplam_tasan = sum(s - kapasite for s in yuk.values() if s > kapasite)
    return {
        "yuk_tablosu": yuk,
        "tasan_uzmanlar": tasan,
        "toplam_tasan_token": toplam_tasan,
    }


def referans_dusurme(kurban_uzmanlari, tasan_uzmanlar):
    _uzman_listesi(kurban_uzmanlari, False)
    if not isinstance(tasan_uzmanlar, (list, set, frozenset)):
        raise ValueError("tasan")
    tk = set()
    for u in tasan_uzmanlar:
        if isinstance(u, bool) or not isinstance(u, int) or u < 0:
            raise ValueError("tasan eleman")
        tk.add(u)
    etk = sum(1 for u in kurban_uzmanlari if u in tk)
    return {
        "etkilenen_token_sayisi": etk,
        "dusurme_orani": etk / len(kurban_uzmanlari),
        "etkilenen_uzmanlar": sorted({u for u in kurban_uzmanlari if u in tk}),
    }


def referans_izole(saldirgan_istekleri, kurban_istekleri, kapasite, kiraci_kota):
    _uzman_listesi(saldirgan_istekleri, True)
    _uzman_listesi(kurban_istekleri, False)
    if isinstance(kapasite, bool) or not isinstance(kapasite, int) or kapasite < 1:
        raise ValueError("kapasite")
    if isinstance(kiraci_kota, bool) or not isinstance(kiraci_kota, int) or not 1 <= kiraci_kota <= kapasite:
        raise ValueError("kota")
    ham = referans_doyurma(saldirgan_istekleri, kurban_istekleri, kapasite)
    korumasiz = referans_dusurme(kurban_istekleri, ham["tasan_uzmanlar"])["dusurme_orani"]
    sayac = {}
    kabul = []
    for u in saldirgan_istekleri:
        if sayac.get(u, 0) < kiraci_kota:
            sayac[u] = sayac.get(u, 0) + 1
            kabul.append(u)
    kor = referans_doyurma(kabul, kurban_istekleri, kapasite)
    korumali = referans_dusurme(kurban_istekleri, kor["tasan_uzmanlar"])["dusurme_orani"]
    return {
        "korumasiz_dusurme_orani": korumasiz,
        "korumali_dusurme_orani": korumali,
        "engellenen_saldirgan_token": len(saldirgan_istekleri) - len(kabul),
        "koruma_basarili": korumali < korumasiz or korumasiz == 0.0,
    }


def _yakin(a, b, tol=1e-9):
    if isinstance(a, dict):
        return isinstance(b, dict) and set(a) == set(b) and all(_yakin(a[k], b[k], tol) for k in a)
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(_yakin(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, (bool, str)) or a is None:
        return type(a) is type(b) and a == b
    return not isinstance(a, bool) and not isinstance(b, bool) and isinstance(a, (int, float)) and isinstance(b, (int, float)) and abs(a - b) <= tol * max(1.0, abs(a), abs(b))


KURBAN_METNI = ("Hello, I need help with my account. Yesterday I tried to change my password but the page showed an error, "
                "and now I cannot log in from my phone. Can you reset it and tell me what I should do next?")
ORNEK_ISTEK = ("Hi, my order has not arrived yet and the tracking page shows no update since Monday. Could you check the status "
               "and let me know when it will be delivered? I also want to change the delivery address. Thanks for your help.")
KOMSU_METNI = ("Please summarize these meeting notes for the team: the budget was approved, the launch moved to May, two new "
               "engineers will join next month, and the office will be closed on Friday for maintenance work.")
# Saldırganın bildiği olası istek kümesi (yardım masası): kurban bunlardan birini gönderir, saldırgan hangisi olduğunu tahmin eder.
ADAY_ISTEKLER = [
    "I forgot my password and the reset email never arrives. Please help me get back into my account today.",
    "I was charged twice for the same order last week. Could you refund the extra payment to my card?",
    "My package has been stuck in transit for ten days and the tracking number does not work anymore.",
    "I moved to a new apartment, so please update the shipping address on all of my future orders.",
    "Cancel my premium subscription at the end of this month and confirm that I will not be billed again.",
    "The invoice you sent me shows the wrong company name and tax number. Can you issue a corrected one?",
    "The headphones I bought stopped charging after two days. I would like a replacement or my money back.",
    "Please delete my account and all personal data you store about me, as allowed under data protection law.",
]


class _Dur(Exception):
    pass


def _katman_girdisi(torch, model, L, ids):
    """ids: [B, T] tensör. L. katman MLP bloğunun gerçek girdisi [B, T, d] (float32); ileri geçiş o katmanda kesilir."""
    kayit = {}

    def kanca(m, i):
        kayit["x"] = i[0].detach().float()
        raise _Dur

    h = model.model.layers[L].mlp.register_forward_pre_hook(kanca)
    try:
        with torch.no_grad():
            model(ids, use_cache=False)
    except _Dur:
        pass
    finally:
        h.remove()
    return kayit["x"]


def _sunucu_dusurme(sira, kapasite, kota=None):
    """Sunucunun batch sırasıyla uyguladığı gerçek kapasite kuralı. sira: [(kiraci, uzman)] batch sırasında.
    kota verilirse saldırganın uzman başına kota'yı aşan tokenleri kapasite tüketmeden reddedilir. Döndürür: düştü mü listesi."""
    sayac, kiraci_sayac, dus = {}, {}, []
    for kiraci, u in sira:
        if kota is not None and kiraci == "saldirgan":
            if kiraci_sayac.get(u, 0) >= kota:
                dus.append(True)
                continue
            kiraci_sayac[u] = kiraci_sayac.get(u, 0) + 1
        sayac[u] = sayac.get(u, 0) + 1
        dus.append(sayac[u] > kapasite)
    return dus


def deney(doyurma_fn, dusurme_fn, izole_fn):
    try:
        import torch
    except ImportError as e:
        raise ai_lab.GercekLabYok(str(e)) from e
    from sandbox import ai_gercek_ai_temel_28 as T28
    tok, model, bilgi = ai_lab.dil_modeli()
    cihaz = ai_lab.torch_cihazi()
    model.to(cihaz)
    L, E = AYAR["katman"], AYAR["uzman_sayisi"]
    torch.manual_seed(AYAR["seed"] + secrets.randbelow(10))

    # Hizmet sağlayıcının MoE katmanı: SmolLM2 katman L MLP'sinden yardımcı kayıpla damıtılmış, dengeli top-1 (Switch) MoE.
    X, Y = T28.mlp_verisi(torch, tok, model, cihaz, L, T28.EGITIM_ISTEMLERI, T28.AYAR["uzunluk"])
    moe = T28.moe_egit(torch, X, Y, AYAR["aux_katsayi"], cihaz, E=E, k=1, yanlilik=0.0)

    def yonlendir(ids_listesi):
        x = _katman_girdisi(torch, model, L, torch.tensor(ids_listesi, device=cihaz))
        with torch.no_grad():
            return moe.yonlendir(x.reshape(-1, x.shape[-1]))[2][:, 0].reshape(x.shape[0], x.shape[1]).tolist()

    kurban_ids = tok(KURBAN_METNI)["input_ids"]
    k_uzman = yonlendir([kurban_ids])[0]

    # Saldırgan kurbanı görmez. Açık ağırlıklı modeli yerelde koşar: hizmetin türünü bildiği için (yardım masası) kendi yazdığı
    # örnek bir destek isteğinde en kalabalık uzmanı hedef seçer; sonra diziyi token token açgözlü kurar: her adımda, eklendiğinde
    # o konumun hedef uzmana yönlenme olasılığını en çok artıran aday tokeni seçer (ağırlıklar açık olduğu için beyaz kutu arama).
    genel = yonlendir([tok(ORNEK_ISTEK)["input_ids"]])[0]
    hedef = max(range(E), key=lambda e: (genel.count(e), -e))
    ozel = set(tok.all_special_ids)
    adaylar = [t for t in range(AYAR["aday_bas"], AYAR["aday_bas"] + AYAR["aday_token"]) if t not in ozel]
    saldiri_ids = []
    for _ in range(AYAR["saldirgan_token"]):
        en_iyi, en_p = None, -1.0
        for b in range(0, len(adaylar), AYAR["aday_grup"]):
            grup = adaylar[b:b + AYAR["aday_grup"]]
            x = _katman_girdisi(torch, model, L, torch.tensor([saldiri_ids + [t] for t in grup], device=cihaz))[:, -1]
            with torch.no_grad():
                p = moe.yonlendir(x)[1][:, hedef]
            v, j = p.max(0)
            if float(v) > en_p:
                en_iyi, en_p = grup[int(j)], float(v)
        saldiri_ids.append(en_iyi)
    s_uzman = yonlendir([saldiri_ids])[0]
    komsu_ids = tok(KOMSU_METNI)["input_ids"][:AYAR["saldirgan_token"]]
    n_uzman = yonlendir([komsu_ids])[0]

    T_batch = len(s_uzman) + len(k_uzman)
    kapasite = max(1, math.ceil(AYAR["kapasite_faktoru"] * T_batch / E))
    kota = AYAR["kiraci_kota"]

    r_doy = referans_doyurma(s_uzman, k_uzman, kapasite)
    o_doy = doyurma_fn(list(s_uzman), list(k_uzman), kapasite)
    doyurma_ayni = _yakin(o_doy, r_doy)

    r_dus = referans_dusurme(k_uzman, r_doy["tasan_uzmanlar"])
    o_dus = dusurme_fn(list(k_uzman), list(r_doy["tasan_uzmanlar"]))
    dusurme_ayni = _yakin(o_dus, r_dus)

    r_izo = referans_izole(s_uzman, k_uzman, kapasite, kota)
    o_izo = izole_fn(list(s_uzman), list(k_uzman), kapasite, kota)
    izole_ayni = _yakin(o_izo, r_izo)

    # Sunucunun gerçek düşürmesi (batch sırası: önce komşu/saldırgan, sonra kurban) ve kurbanın dil modeli kaybı.
    nk = len(k_uzman)
    durumlar = {
        "komsu": _sunucu_dusurme([("komsu", u) for u in n_uzman] + [("kurban", u) for u in k_uzman], kapasite)[-nk:],
        "saldiri": _sunucu_dusurme([("saldirgan", u) for u in s_uzman] + [("kurban", u) for u in k_uzman], kapasite)[-nk:],
        "kota": _sunucu_dusurme([("saldirgan", u) for u in s_uzman] + [("kurban", u) for u in k_uzman], kapasite, kota)[-nk:],
    }
    kids = torch.tensor([kurban_ids], device=cihaz)

    def kurban_kaybi(maske):
        def kanca(m, i, o):
            x = i[0][0].float()
            d = None if maske is None else torch.tensor(maske, dtype=torch.bool, device=cihaz).unsqueeze(1)
            y, _ = moe.ileri(x, dus=d)
            return y.unsqueeze(0).to(o.dtype)
        h = model.model.layers[L].mlp.register_forward_hook(kanca)
        try:
            with torch.no_grad():
                return float(model(kids, labels=kids).loss)
        finally:
            h.remove()

    with torch.no_grad():
        temiz = float(model(kids, labels=kids).loss)
        xk = _katman_girdisi(torch, model, L, kids)[0]
        y_tam = moe.ileri(xk)[0]
        katman_hatasi = {}
        for ad, m in durumlar.items():
            y = moe.ileri(xk, dus=torch.tensor(m, dtype=torch.bool, device=cihaz).unsqueeze(1))[0]
            katman_hatasi[ad] = round(float(((y - y_tam) ** 2).sum() / (y_tam ** 2).sum()), 4)
    lm = {"orijinal_mlp": temiz, "moe_kapasitesiz": kurban_kaybi(None)}
    lm.update({ad: kurban_kaybi(m) for ad, m in durumlar.items()})
    gercek_dusen = {ad: sum(m) for ad, m in durumlar.items()}

    # Batch yan kanalı: kurban önce sıralanırsa saldırganın kendi düşen token sayısı kurbanın hedef uzmandaki yükünü verir.
    s_dus = _sunucu_dusurme([("kurban", u) for u in k_uzman] + [("saldirgan", u) for u in s_uzman], kapasite)[nk:]
    s_hedef_yuk = s_uzman.count(hedef)
    s_hedef_dus = sum(1 for u, d in zip(s_uzman, s_dus) if u == hedef and d)
    yan_kanal = {"kurban_hedef_yuku_gercek": k_uzman.count(hedef),
                 "saldirganin_gordugu_dusen": s_hedef_dus,
                 "cikarilan_kurban_yuku": (s_hedef_dus - s_hedef_yuk + kapasite) if s_hedef_dus > 0 else None}

    # Girdi çıkarımı: her uzman için yalnız o uzmana giden bir yoklama dizisi (kapasite uzunluğunda, tek token tekrarı) yerelde
    # bulunur. Kurbandan sonra gönderilen yoklamanın düşen token sayısı kurbanın o uzmandaki yükünü verir; yük dağılımı olası
    # isteklerin yerelde hesaplanan dağılımlarıyla karşılaştırılır.
    yoklama = {}
    for b in range(0, len(adaylar), AYAR["aday_grup"]):
        grup = [t for t in adaylar[b:b + AYAR["aday_grup"]]]
        rota = yonlendir([[t] * kapasite for t in grup])
        for t, r in zip(grup, rota):
            if len(set(r)) == 1 and r[0] not in yoklama:
                yoklama[r[0]] = t
    aday_yuk = []
    for s in ADAY_ISTEKLER:
        u = yonlendir([tok(s)["input_ids"]])[0]
        aday_yuk.append([u.count(e) for e in range(E)])

    def gozlenen(yuk, kota_):
        """Kurban (yük dağılımı yuk) önce, saldırganın e uzmanına yoklaması sonra: saldırganın gördüğü düşen sayısı."""
        out = {}
        for e, t in yoklama.items():
            sira = [("kurban", ee) for ee in range(E) for _ in range(yuk[ee])] + [("saldirgan", e)] * kapasite
            out[e] = sum(_sunucu_dusurme(sira, kapasite, kota_)[sum(yuk):])
        return out

    def tahmin(gz):
        return min(range(len(aday_yuk)), key=lambda j: (sum(abs(gz[e] - min(aday_yuk[j][e], kapasite)) for e in gz), j))
    cikarim = {"yoklanabilen_uzman": sorted(yoklama), "dogru_kotasiz": 0, "dogru_kotali": 0, "aday": len(ADAY_ISTEKLER)}
    for j, yuk in enumerate(aday_yuk):
        cikarim["dogru_kotasiz"] += int(tahmin(gozlenen(yuk, None)) == j)
        cikarim["dogru_kotali"] += int(tahmin(gozlenen(yuk, kota)) == j)
    return {
        "cihaz": str(cihaz), "dtype": "float32",
        "model": {k2: bilgi[k2] for k2 in ("model", "revizyon", "agirlik_sha256", "parametre")},
        "surumler": {"torch": importlib.metadata.version("torch"), "transformers": importlib.metadata.version("transformers")},
        "ayarlar": AYAR, "kapasite": kapasite, "hedef_uzman": hedef,
        "saldiri_dizisi": tok.decode(saldiri_ids),
        "saldirgan_uzmanlari": s_uzman, "kurban_uzmanlari": k_uzman, "komsu_uzmanlari": n_uzman,
        "doyurma": r_doy, "dusurme": r_dus, "izole_rapor": r_izo,
        "doyurma_ayni": doyurma_ayni, "dusurme_ayni": dusurme_ayni, "izole_ayni": izole_ayni,
        "gercek_dusen": gercek_dusen, "kurban_katman_hatasi": katman_hatasi, "kurban_lm_kaybi": lm, "yan_kanal": yan_kanal,
        "girdi_cikarimi": cikarim,
        "girdi_cikarildi_kota_engelledi": (cikarim["dogru_kotasiz"] >= 0.75 * cikarim["aday"] and cikarim["dogru_kotali"] <= 0.375 * cikarim["aday"]),
        "saldirgan_hedef_orani": s_uzman.count(hedef) / len(s_uzman), "kurban_token": nk,
        "olcum": (f"SmolLM2-135M katman {L} MLP'sinden damıtılan {E} uzmanlı top-1 MoE; batch {T_batch} token, kapasite {kapasite}. Saldırgan "
                  f"kurbanı görmeden hedef uzman {hedef}'i seçti ve {AYAR['aday_token']} aday tokenle açgözlü dizi kurdu "
                  f"({len(s_uzman)} tokenin {s_uzman.count(hedef)}'i hedefe gitti). Kurbanın {nk} tokeninden gerçekten düşen: komşu {gercek_dusen['komsu']}, "
                  f"saldırı {gercek_dusen['saldiri']}, kota {kota} ile {gercek_dusen['kota']} (sözleşmenin üst sınır tahmini {r_dus['etkilenen_token_sayisi']}). "
                  f"Kurbanın o katmandaki göreli çıktı hatası: komşu {katman_hatasi['komsu']}, saldırı {katman_hatasi['saldiri']}, kota "
                  f"{katman_hatasi['kota']}. Kurban LM kaybı: orijinal {temiz:.3f}, "
                  f"komşu {lm['komsu']:.3f}, saldırı {lm['saldiri']:.3f}, kota {lm['kota']:.3f}. Yan kanal: kurbanın hedef uzman yükü "
                  f"{yan_kanal['kurban_hedef_yuku_gercek']}, saldırganın kendi düşenlerinden çıkarılan {yan_kanal['cikarilan_kurban_yuku']}. "
                  f"Girdi çıkarımı ({len(cikarim['yoklanabilen_uzman'])}/{E} uzman yoklanabildi): {cikarim['aday']} olası istekten kurbanınki "
                  f"kotasız {cikarim['dogru_kotasiz']}/{cikarim['aday']}, kiracı kotasıyla {cikarim['dogru_kotali']}/{cikarim['aday']} doğru tahmin edildi "
                  f"(şans 1/{cikarim['aday']})."),
        "sinir": ("MoE ön eğitimli değil, tek katmanın MLP'sinden damıtılmıştır ve yalnız o katman MoE'dir. Sunucu kuralı (batch sırası, sabit kapasite, "
                  "kiracı kotası) yazarın modelidir; gerçek çıkarım motorları sıralamayı ve kapasiteyi farklı yönetebilir, dropless (MegaBlocks) "
                  "çekirdeklerde token düşmez. Yan kanal, saldırganın kendi düşen token sayısını gördüğünü varsayar."),
    }


def goster(doyurma_fn, dusurme_fn, izole_fn):
    r = deney(doyurma_fn, dusurme_fn, izole_fn)
    print("Model:", r["model"]["model"], "| cihaz:", r["cihaz"], "| kapasite:", r["kapasite"], "| hedef uzman:", r["hedef_uzman"])
    print("Saldırı dizisi:", repr(r["saldiri_dizisi"][:160]))
    print("Yük tablosu:", r["doyurma"]["yuk_tablosu"], "| taşan uzmanlar:", r["doyurma"]["tasan_uzmanlar"])
    print("Kurban düşürme:", r["dusurme"], "| İzole batch raporu:", r["izole_rapor"])
    print("Gerçek düşen kurban tokeni:", r["gercek_dusen"], "| katman çıktı hatası:", r["kurban_katman_hatasi"])
    print("Kurban LM kaybı:", {k: round(v, 3) for k, v in r["kurban_lm_kaybi"].items()})
    print("Yan kanal:", r["yan_kanal"])
    print("Sınır:", r["sinir"])
    print("Kanıt:", ai_lab.kanit_yaz("ai-saldiri-61-run", {"kaynak": "gercek", "kabul": False, "ders": "ai-saldiri-61", "deney": r}))
