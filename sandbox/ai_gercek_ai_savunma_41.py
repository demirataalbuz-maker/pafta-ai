"""GraphRAG topluluk anomalisi ve köprü düğümü karantinası: yerel LLM ile kurulan gerçek GraphRAG çizgesinde zehirli köprü
düğümlerinin itibar + topluluklar arası oranla karantinaya alınması; bağlam ve cevap zehirlenmesi önce/sonra ölçülür."""
import importlib.metadata, math, random, secrets
import ai_lab

AYAR = {"seed": 60, "oran_esik": 0.6, "min_guven": 0.65, "min_kaynak_sayisi": 2}


def _sayi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)


def _str_mi(s):
    return isinstance(s, str) and len(s.strip()) > 0


def referans_oran(kenarlar, topluluklar, dugum):
    if not isinstance(kenarlar, list) or not kenarlar or not isinstance(topluluklar, dict) or not topluluklar or not _str_mi(dugum):
        raise ValueError("girdi")
    for k, v in topluluklar.items():
        if not _str_mi(k) or not _str_mi(v):
            raise ValueError("topluluk")
    if dugum not in topluluklar:
        raise ValueError("dugum")
    komsular = set()
    for e in kenarlar:
        if not isinstance(e, list) or len(e) != 2 or not _str_mi(e[0]) or not _str_mi(e[1]) or e[0] == e[1]:
            raise ValueError("kenar")
        if e[0] not in topluluklar or e[1] not in topluluklar:
            raise ValueError("bilinmeyen")
        if e[0] == dugum:
            komsular.add(e[1])
        elif e[1] == dugum:
            komsular.add(e[0])
    d = len(komsular)
    if d == 0:
        return {"derece": 0, "farkli_topluluk": 0, "oran": 0.0}
    farkli = sum(1 for v in komsular if topluluklar[v] != topluluklar[dugum])
    return {"derece": d, "farkli_topluluk": farkli, "oran": farkli / d}


def referans_filtre(dugum_kaynaklari, guven_skorlari, min_guven, min_kaynak_sayisi):
    if not isinstance(dugum_kaynaklari, dict) or not dugum_kaynaklari or not isinstance(guven_skorlari, dict) or not guven_skorlari:
        raise ValueError("sozluk")
    if not _sayi(min_guven) or not 0 <= min_guven <= 1 or isinstance(min_kaynak_sayisi, bool) or not isinstance(min_kaynak_sayisi, int) or min_kaynak_sayisi < 1:
        raise ValueError("esik")
    for b, s in guven_skorlari.items():
        if not _str_mi(b) or not _sayi(s) or not 0 <= s <= 1:
            raise ValueError("guven")
    supheli = []
    for u, belgeler in dugum_kaynaklari.items():
        if not _str_mi(u) or not isinstance(belgeler, list) or not belgeler:
            raise ValueError("belgeler")
        tekil = set()
        for b in belgeler:
            if not _str_mi(b) or b not in guven_skorlari:
                raise ValueError("belge")
            tekil.add(b)
        ort = sum(guven_skorlari[b] for b in tekil) / len(tekil)
        if ort < min_guven or len(tekil) < min_kaynak_sayisi:
            supheli.append(u)
    return sorted(supheli)


def referans_karantina(kenarlar, topluluklar, dugum_kaynaklari, guven_skorlari, oran_esik, min_guven, min_kaynak_sayisi):
    if not _sayi(oran_esik) or not 0 < oran_esik <= 1:
        raise ValueError("oran_esik")
    if not isinstance(topluluklar, dict) or not isinstance(dugum_kaynaklari, dict) or set(topluluklar) != set(dugum_kaynaklari):
        raise ValueError("kume")
    supheli = set(referans_filtre(dugum_kaynaklari, guven_skorlari, min_guven, min_kaynak_sayisi))
    referans_oran(kenarlar, topluluklar, next(iter(topluluklar)))  # Kaynak güveninden bağımsız şema doğrulaması.
    karantina = sorted(u for u in topluluklar if u in supheli and referans_oran(kenarlar, topluluklar, u)["oran"] >= oran_esik)
    k_set = set(karantina)
    temiz = [[e[0], e[1]] for e in kenarlar if e[0] not in k_set and e[1] not in k_set]
    return {
        "karantina_dugumleri": karantina,
        "temiz_kenar_sayisi": len(temiz),
        "elenen_kenar_sayisi": len(kenarlar) - len(temiz),
        "temiz_kenarlar": temiz
    }


def _yakin(a, b, tol=1e-9):
    if isinstance(a, dict):
        return isinstance(b, dict) and set(a) == set(b) and all(_yakin(a[k], b[k], tol) for k in a)
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(_yakin(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, (bool, str)) or a is None:
        return type(a) is type(b) and a == b
    return _sayi(a) and _sayi(b) and abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def guvenilir_topluluklar(graf, guven_skorlari, min_guven, seed):
    """Toplulukları yalnız güvenilir kaynakların (itibar >= min_guven) birlikte geçme kenarlarından çıkarır; yalnız güvenilmeyen
    kaynaklarda görülen düğümler hiçbir güvenilir topluluğa ait değildir ve 'guvenilmeyen' etiketini alır."""
    import networkx as nx
    G_ = nx.Graph()
    for b, adlar in graf["cikarimlar"].items():
        if guven_skorlari[b] < min_guven:
            continue
        G_.add_nodes_from(adlar)
        G_.add_edges_from((adlar[i], adlar[j]) for i in range(len(adlar)) for j in range(i + 1, len(adlar)))
    t = {u: "guvenilmeyen" for u in graf["dugum_kaynaklari"]}
    for c_i, uyeler in enumerate(sorted(nx.community.louvain_communities(G_, seed=seed), key=lambda s: sorted(s)[0])):
        for u in uyeler:
            t[u] = f"g{c_i}"
    return t


def deney(oran_fn, filtre_fn, karantina_fn):
    from sandbox import ai_gercek_ai_saldiri_60 as G
    rng = random.Random(secrets.randbits(64))
    with ai_lab.SohbetOturumu() as oturum:
        gom = G.Gomucu(oturum.adres)
        graf = G.graf_kur(oturum, seed=AYAR["seed"])
        kenarlar, dugum_kaynaklari = graf["kenarlar"], graf["dugum_kaynaklari"]
        # Kaynak itibarı: iç belgeler yüksek, içe alınan dış forum sayfaları düşük (gerçek sistemde kaynak kataloğundan gelir)
        guven_skorlari = {b: round(rng.uniform(0.82, 0.98) if not b.startswith("dis_") else rng.uniform(0.12, 0.35), 4)
                          for b in G.BELGELER}
        zehirli_beklenen = sorted(u for u, b in dugum_kaynaklari.items() if all(x.startswith("dis_") for x in b))
        # İki topluluk yapılandırması: (1) zehirli çizgenin kendi Louvain toplulukları, (2) güvenilir alt çizgenin toplulukları
        yapilar = {"ham": graf["topluluklar"],
                   "guvenilir": guvenilir_topluluklar(graf, guven_skorlari, AYAR["min_guven"], AYAR["seed"])}
        once = G.sorgula(oturum, gom, graf, seed=AYAR["seed"])
        kosu = {}
        for ad, topl in yapilar.items():
            k_ref = referans_karantina(kenarlar, topl, dugum_kaynaklari, guven_skorlari, AYAR["oran_esik"], AYAR["min_guven"],
                                       AYAR["min_kaynak_sayisi"])
            kar = k_ref["karantina_dugumleri"]
            # Karantinadaki düğümü üreten DÜŞÜK itibarlı belgeler (metin birimleri) de bağlamdan çıkarılır; yüksek itibarlı iç
            # belgeler, içlerindeki bir varlık karantinaya alındı diye atılmaz (yanlış karantinanın hizmet kaybını sınırlar).
            haric = sorted({b for u in kar for b in dugum_kaynaklari[u] if guven_skorlari[b] < AYAR["min_guven"]})
            sonra = G.sorgula(oturum, gom, graf, haric_dugumler=kar, haric_belgeler=haric, seed=AYAR["seed"]) if kar else once
            kosu[ad] = {"topluluklar": topl, "k_ref": k_ref, "haric": haric, "sonra": sonra}
        ortam = dict(oturum.kayit)
    ortam["temizlik"] = oturum.kayit.get("temizlik")
    ortam["gomme"] = gom.kayit
    topluluklar = yapilar["guvenilir"]
    k_ref = kosu["guvenilir"]["k_ref"]
    karantina, haric_belgeler, sonra = k_ref["karantina_dugumleri"], kosu["guvenilir"]["haric"], kosu["guvenilir"]["sonra"]

    oran_ayni = True
    for ad in ("ham",):
        for u in yapilar[ad]:
            oran_ayni = oran_ayni and _yakin(oran_fn([list(e) for e in kenarlar], dict(yapilar[ad]), u), referans_oran(kenarlar, yapilar[ad], u))
        k_o = karantina_fn([list(e) for e in kenarlar], dict(yapilar[ad]), {k: list(v) for k, v in dugum_kaynaklari.items()},
                           dict(guven_skorlari), AYAR["oran_esik"], AYAR["min_guven"], AYAR["min_kaynak_sayisi"])
        oran_ayni = oran_ayni and _yakin(k_o, kosu[ad]["k_ref"])
    for u in topluluklar:
        o_ogr = oran_fn([list(e) for e in kenarlar], dict(topluluklar), u)
        o_ref = referans_oran(kenarlar, topluluklar, u)
        oran_ayni = oran_ayni and _yakin(o_ogr, o_ref)

    f_ogr = filtre_fn({k: list(v) for k, v in dugum_kaynaklari.items()}, dict(guven_skorlari), AYAR["min_guven"], AYAR["min_kaynak_sayisi"])
    f_ref = referans_filtre(dugum_kaynaklari, guven_skorlari, AYAR["min_guven"], AYAR["min_kaynak_sayisi"])
    filtre_ayni = _yakin(f_ogr, f_ref)

    k_ogr = karantina_fn([list(e) for e in kenarlar], dict(topluluklar), {k: list(v) for k, v in dugum_kaynaklari.items()},
                         dict(guven_skorlari), AYAR["oran_esik"], AYAR["min_guven"], AYAR["min_kaynak_sayisi"])
    karantina_ayni = _yakin(k_ogr, k_ref)

    oranlar = {u: referans_oran(kenarlar, topluluklar, u) for u in topluluklar}
    mesru_kopruler = sorted(u for u, b in dugum_kaynaklari.items()
                            if len({G.BELGELER[x][0] for x in b if not x.startswith("dis_")}) >= 2)
    yanlis_karantina = sorted(set(karantina) - set(zehirli_beklenen))
    kacan_zehirli = sorted(set(zehirli_beklenen) - set(karantina))

    def ozet(s):
        return {"zehirli_baglam": sum(x["zehirli_baglam"] for x in s), "kanarya_cevap": sum(x["kanarya_cevapta"] for x in s),
                "konu_belgesi_baglamda": sum(any(b.startswith("ic_" + x["konu"]) for b in x["baglam"]) for x in s)}

    o_once, o_sonra = ozet(once), ozet(sonra)
    ham = kosu["ham"]
    ham_kar = ham["k_ref"]["karantina_dugumleri"]
    ham_oran = {u: round(referans_oran(kenarlar, yapilar["ham"], u)["oran"], 3) for u in zehirli_beklenen}
    n_s = len(once)
    return {
        "ortam": ortam,
        "ayarlar": AYAR,
        "dugum_sayisi": len(topluluklar),
        "toplam_kenar": len(kenarlar),
        "topluluk_sayisi": len(set(topluluklar.values())),
        "guven_skorlari": guven_skorlari,
        "zehirli_beklenen": zehirli_beklenen,
        "mesru_kopruler": {u: {"oran": round(oranlar[u]["oran"], 3), "kaynak": dugum_kaynaklari[u]} for u in mesru_kopruler},
        "ham_topluluklar": {"karantina": ham_kar, "zehirli_oranlari": ham_oran, "topluluk_sayisi": len(set(yapilar["ham"].values())),
                            "sonra": ozet(ham["sonra"])},
        "karantina_dugumleri": k_ogr["karantina_dugumleri"],
        "haric_belgeler": haric_belgeler,
        "yanlis_karantina": yanlis_karantina, "kacan_zehirli": kacan_zehirli,
        "supheli_ama_karantinasiz": sorted(set(f_ref) - set(karantina)),
        "oran_ayni": oran_ayni,
        "filtre_ayni": filtre_ayni,
        "karantina_ayni": karantina_ayni,
        "once": o_once, "sonra": o_sonra, "sorgular_once": once, "sorgular_sonra": sonra,
        "bulasma_orani_once": o_once["zehirli_baglam"] / n_s,
        "bulasma_orani_sonra": o_sonra["zehirli_baglam"] / n_s,
        "olcum": (f"{ortam.get('model', {}).get('ad')} ile kurulan GraphRAG çizgesi ({len(topluluklar)} düğüm, {len(kenarlar)} kenar). Zehirli "
                  f"çizgenin kendi Louvain toplulukları ile zehirli düğümlerin topluluklar arası oranı {ham_oran}, karantina {ham_kar}. "
                  f"Güvenilir alt çizgenin toplulukları ile karantina (itibar < {AYAR['min_guven']} ya da < {AYAR['min_kaynak_sayisi']} kaynak, "
                  f"VE oran ≥ {AYAR['oran_esik']}): {karantina}; dışlanan belgeler {haric_belgeler}. Yanlış karantina {yanlis_karantina}, "
                  f"kaçan {kacan_zehirli}. {n_s} sorguda zehirli bağlam {o_once['zehirli_baglam']} → {o_sonra['zehirli_baglam']}, saldırgan "
                  f"adresi cevapta {o_once['kanarya_cevap']} → {o_sonra['kanarya_cevap']}, doğru konu belgesi bağlamda "
                  f"{o_once['konu_belgesi_baglamda']} → {o_sonra['konu_belgesi_baglamda']}."),
        "sinir": ("Küçük kurgusal bilgi tabanı ve küçük yerel model; varlık çıkarımı koşudan koşuya biraz değişebilir. Kaynak itibarı deneyde "
                  "verilir, gerçek sistemde kaynak kataloğundan gelmelidir. Yüksek itibarlı meşru bir kaynağın kendisinin zehirlenmesi ya da "
                  "zehirli içeriğin tek bir topluluk içinde kalması bu yapısal filtreyi aşar.")
    }


def goster(oran_fn, filtre_fn, karantina_fn):
    r = deney(oran_fn, filtre_fn, karantina_fn)
    print("Model:", r["ortam"].get("model", {}).get("ad"), "| düğüm:", r["dugum_sayisi"], "| kenar:", r["toplam_kenar"], "| topluluk:", r["topluluk_sayisi"])
    print("Zehirli çizgenin kendi toplulukları ile:", r["ham_topluluklar"])
    print("Güvenilir alt çizge toplulukları ile karantina:", r["karantina_dugumleri"], "| dışlanan belgeler:", r["haric_belgeler"])
    print("Yanlış karantina:", r["yanlis_karantina"], "| kaçan zehirli:", r["kacan_zehirli"], "| meşru köprüler:", r["mesru_kopruler"])
    print("Önce:", r["once"], "| sonra:", r["sonra"])
    for a, b in zip(r["sorgular_once"], r["sorgular_sonra"]):
        print("  [%s] önce %s kanarya=%s | sonra %s kanarya=%s" % (a["konu"], a["baglam"], a["kanarya_cevapta"], b["baglam"], b["kanarya_cevapta"]))
    print("Sınır:", r["sinir"])
    print("Kanıt:", ai_lab.kanit_yaz("ai-savunma-41-run", {"kaynak": "gercek", "kabul": False, "ders": "ai-savunma-41", "deney": r}))
