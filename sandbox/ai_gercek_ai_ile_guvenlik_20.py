"""DARPA AIxCC tarzı hibrit zafiyet avcısı: gerçek hedef programlarda (sınır dışı yazma hatalı paket ayrıştırıcısı) kör ve kapsam
güdümlü fuzzer ile kaynak koddan çıkarılan yol koşullarını aralık daraltmayla çözen hibrit yaklaşımın dar dala (magic-byte) erişimi."""
import importlib.metadata, math, platform, random, secrets
import ai_lab

AYAR = {"seed": 20, "alt_sinir": 0, "ust_sinir": 65535, "fuzzer_bütce": 4096, "hedef_sayisi": 12, "llm_hedef": 6}
GECERLI_OP_DEGERLENDIR = ("==", "!=", ">=", "<=", ">", "<")
GECERLI_OP_DARALT = ("==", ">=", "<=", ">", "<")


def _int_mi(v):
    return not isinstance(v, bool) and isinstance(v, int)


def _str_mi(s):
    return isinstance(s, str) and len(s.strip()) > 0


def _kisit_gecerli_mi(k, op_kume):
    if not isinstance(k, dict) or set(k) != {"degisken", "op", "deger"}:
        return False
    return _str_mi(k["degisken"]) and k["op"] in op_kume and _int_mi(k["deger"])


def referans_degerlendir(kisitlar, aday_girdi):
    if not isinstance(kisitlar, list) or not kisitlar or not isinstance(aday_girdi, dict) or not aday_girdi:
        raise ValueError("girdi")
    for a_k, a_v in aday_girdi.items():
        if not _str_mi(a_k) or not _int_mi(a_v):
            raise ValueError("aday")
    for k in kisitlar:
        if not _kisit_gecerli_mi(k, GECERLI_OP_DEGERLENDIR) or k["degisken"] not in aday_girdi:
            raise ValueError("kisit")
    gecen = 0
    ilk_engel = None
    for i, k in enumerate(kisitlar):
        x = aday_girdi[k["degisken"]]
        y = k["deger"]
        op = k["op"]
        ok_mu = (x == y if op == "==" else x != y if op == "!=" else x >= y if op == ">=" else x <= y if op == "<=" else x > y if op == ">" else x < y)
        if ok_mu:
            gecen += 1
        elif ilk_engel is None:
            ilk_engel = i
    return {
        "gecen_sayisi": gecen,
        "toplam_kisit": len(kisitlar),
        "ilk_engel_indisi": ilk_engel,
        "tam_cozum": gecen == len(kisitlar)
    }


def referans_daralt(kisitlar, baslangic_alt, baslangic_ust):
    if not isinstance(kisitlar, list) or not kisitlar or not _int_mi(baslangic_alt) or not _int_mi(baslangic_ust) or baslangic_alt > baslangic_ust:
        raise ValueError("girdi")
    araliklar = {}
    for k in kisitlar:
        if not _kisit_gecerli_mi(k, GECERLI_OP_DARALT):
            raise ValueError("kisit")
        d = k["degisken"]
        if d not in araliklar:
            araliklar[d] = [baslangic_alt, baslangic_ust]
        alt, ust = araliklar[d]
        v = k["deger"]
        op = k["op"]
        if op == "==":
            alt = max(alt, v)
            ust = min(ust, v)
        elif op == ">=":
            alt = max(alt, v)
        elif op == "<=":
            ust = min(ust, v)
        elif op == ">":
            alt = max(alt, v + 1)
        elif op == "<":
            ust = min(ust, v - 1)
        araliklar[d] = [alt, ust]
    cozulebilir = all(a <= u for a, u in araliklar.values())
    aday = {d: (a + u) // 2 for d, (a, u) in araliklar.items()} if cozulebilir else None
    return {"araliklar": araliklar, "cozulebilir": cozulebilir, "aday": aday}


def referans_hibrit(kisit_listesi, rastgele_adaylar, alt_sinir, ust_sinir, hedef_dal):
    if not isinstance(kisit_listesi, dict) or not kisit_listesi or not _str_mi(hedef_dal) or hedef_dal not in kisit_listesi:
        raise ValueError("hedef")
    if not isinstance(rastgele_adaylar, list) or not rastgele_adaylar or not _int_mi(alt_sinir) or not _int_mi(ust_sinir) or alt_sinir > ust_sinir:
        raise ValueError("ayar")
    for d_ad, kl in kisit_listesi.items():
        if not _str_mi(d_ad):
            raise ValueError("dal")
        referans_daralt(kl, alt_sinir, ust_sinir)
    hedef_k = kisit_listesi[hedef_dal]
    en_iyi = 0
    ilk_tam = None
    for ad in rastgele_adaylar:
        sonuc = referans_degerlendir(hedef_k, ad)
        if sonuc["gecen_sayisi"] > en_iyi:
            en_iyi = sonuc["gecen_sayisi"]
        if sonuc["tam_cozum"] and ilk_tam is None:
            ilk_tam = dict(ad)
    if ilk_tam is not None:
        return {"yontem": "fuzzer", "tetikleyici": ilk_tam, "rastgele_en_iyi": en_iyi, "toplam_kisit": len(hedef_k), "basarili": True}
    dar = referans_daralt(hedef_k, alt_sinir, ust_sinir)
    if dar["cozulebilir"] and dar["aday"] is not None and referans_degerlendir(hedef_k, dar["aday"])["tam_cozum"]:
        return {"yontem": "sembolik_cozucu", "tetikleyici": dar["aday"], "rastgele_en_iyi": en_iyi, "toplam_kisit": len(hedef_k), "basarili": True}
    return {"yontem": "basarisiz", "tetikleyici": None, "rastgele_en_iyi": en_iyi, "toplam_kisit": len(hedef_k), "basarili": False}


def _yakin(a, b):
    return type(a) is type(b) and a == b


HEDEF_SABLONU = '''
def ayristir(veri):
    """Ağ paketi ayrıştırıcısı (hedef program). Sınır dışı yazma hatası yalnız dar bir dalda tetiklenir."""
    if len(veri) < 8:
        return "kisa"
    sihirli_baslik = int.from_bytes(veri[0:2], "big")
    paket_boyutu = int.from_bytes(veri[2:4], "big")
    bayrak = veri[4]
    if sihirli_baslik > 50000:
        if sihirli_baslik < 10000:
            return "olu_kod"
    if sihirli_baslik == {sihir}:
        if paket_boyutu > {alt}:
            if paket_boyutu <= {ust}:
                if bayrak == {bayrak}:
                    tampon = bytearray(16)
                    tampon[paket_boyutu - {alt} + 15] = veri[5]   # HATA: uzunluk alanına güvenilerek sınır dışı yazma
                    return "parcali"
                return "bayrak_yok"
            return "buyuk"
        return "kucuk"
    return "bilinmeyen"
'''


def _yol_kosullari(kaynak):
    """Hedefin kaynak kodundan (ast) iç içe if koşullarını çıkarır: çökme dalının ve ölü dalın yol koşulu."""
    import ast
    ops = {ast.Eq: "==", ast.NotEq: "!=", ast.Gt: ">", ast.GtE: ">=", ast.Lt: "<", ast.LtE: "<="}
    dallar = {}

    def gez(govde, yol):
        for d in govde:
            if isinstance(d, ast.If) and isinstance(d.test, ast.Compare) and isinstance(d.test.left, ast.Name) \
                    and len(d.test.ops) == 1 and isinstance(d.test.comparators[0], ast.Constant) and type(d.test.ops[0]) in ops:
                yeni = yol + [{"degisken": d.test.left.id, "op": ops[type(d.test.ops[0])], "deger": int(d.test.comparators[0].value)}]
                if any(isinstance(x, ast.Assign) and isinstance(x.targets[0], ast.Subscript) for x in d.body):
                    dallar["cokme_dali"] = yeni
                if any(isinstance(x, ast.Return) and isinstance(x.value, ast.Constant) and x.value.value == "olu_kod" for x in d.body):
                    dallar["olu_dal"] = yeni
                gez(d.body, yeni)

    fn = next(n for n in ast.parse(kaynak).body if isinstance(n, ast.FunctionDef))
    gez(fn.body, [])
    return dallar


def _baytlar(alanlar, rng):
    v = bytearray(rng.getrandbits(8) for _ in range(8))
    v[0:2] = (alanlar["sihirli_baslik"] & 0xFFFF).to_bytes(2, "big")
    v[2:4] = (alanlar["paket_boyutu"] & 0xFFFF).to_bytes(2, "big")
    v[4] = alanlar["bayrak"] & 0xFF
    return bytes(v)


def _alanlar(veri):
    return {"sihirli_baslik": int.from_bytes(veri[0:2], "big"), "paket_boyutu": int.from_bytes(veri[2:4], "big"), "bayrak": veri[4]}


def _yol_derinligi(kisitlar, alanlar):
    """Programın gerçekte ilerlediği iç içe dal sayısı: ilk sağlanmayan koşula kadar sırayla geçilen if sayısı."""
    r = referans_degerlendir(kisitlar, alanlar)
    return len(kisitlar) if r["ilk_engel_indisi"] is None else r["ilk_engel_indisi"]


def _calistir(fn, veri):
    try:
        return fn(veri), False
    except IndexError:
        return "cokme", True


LLM_SISTEMI = "You are a vulnerability researcher. You read code and reply only with JSON, nothing else."


def _llm_kisitlari(oturum, kaynak, gecmis=None, geri_bildirim=None):
    """AIxCC tarzı adım: yerel LLM hedefin kaynak kodunu okuyup hata satırına giden yol koşullarını kısıt listesine çevirir.
    geri_bildirim verilirse önceki konuşmaya programın gerçek davranışı eklenir ve düzeltilmiş liste istenir."""
    import json
    import re
    istek = ("Here is a Python function:\n```python\n" + kaynak.strip() + "\n```\nList, in order, every condition that must be true "
             "for execution to reach the line marked HATA. Reply with a JSON array of objects with keys \"degisken\" (variable "
             "name), \"op\" (one of ==, >, >=, <, <=) and \"deger\" (integer).")
    mesajlar = gecmis or [{"role": "system", "content": LLM_SISTEMI}, {"role": "user", "content": istek}]
    if geri_bildirim:
        mesajlar = mesajlar + [{"role": "user", "content": geri_bildirim}]
    y = oturum.sohbet(mesajlar, seed=AYAR["seed"], sicaklik=0.0, en_fazla=300)
    mesajlar = mesajlar + [{"role": "assistant", "content": y["icerik"]}]
    m = re.search(r"\[.*\]", y["icerik"], flags=re.S)
    try:
        ham = json.loads(m.group()) if m else []
    except ValueError:
        ham = []
    out = []
    for k in ham if isinstance(ham, list) else []:
        try:
            k2 = {"degisken": str(k["degisken"]), "op": str(k["op"]).strip(), "deger": int(k["deger"])}
        except (KeyError, TypeError, ValueError):
            continue
        if _kisit_gecerli_mi(k2, GECERLI_OP_DARALT):
            out.append(k2)
    return out, y["icerik"][:400], mesajlar


ALANLAR = ("sihirli_baslik", "paket_boyutu", "bayrak")


def _onar_ve_dogrula(kisit, daralt, ayristir, rng):
    """LLM çıktısını doğrulayıcıyla onarır: (1) değişken adlarını bilinen paket alanlarına yakın eşleştir (yazım hatası),
    bilinmeyenleri at; (2) çözülemezse kısıt alt kümelerini (önce en az kısıt atarak) dene; (3) her adayı gerçek programda
    çalıştır, çöken ilkini kabul et. Döndürür: (çöktü mü, kullanılan kısıtlar)."""
    import itertools
    temiz = _normalize(kisit)
    gozlem = None
    for atilan in range(0, len(temiz)):
        for kalan in itertools.combinations(temiz, len(temiz) - atilan):
            kalan = list(kalan)
            if not kalan:
                continue
            dr = daralt([dict(x) for x in kalan], AYAR["alt_sinir"], AYAR["ust_sinir"])
            if not (dr.get("cozulebilir") and dr.get("aday")):
                continue
            aday = {a: dr["aday"].get(a, 0) for a in ALANLAR}
            sonuc, cokti = _calistir(ayristir, _baytlar(aday, rng))
            if cokti:
                return True, kalan, None
            if gozlem is None:
                gozlem = (aday, sonuc)
    return False, temiz, gozlem


def _normalize(kisit):
    """Yazım hatalı değişken adlarını bilinen paket alanlarına eşler (difflib), bilinmeyenleri atar."""
    import difflib
    out = []
    for k in kisit:
        ad = difflib.get_close_matches(k["degisken"], ALANLAR, n=1, cutoff=0.8)
        if ad:
            out.append(dict(k, degisken=ad[0]))
    return out


def deney(deg_fn, daralt_fn, hibrit_fn):
    rng = random.Random(secrets.randbits(64))

    deg_ayni = True
    daralt_ayni = True
    hibrit_ayni = True

    fuzzer_cozulen = 0
    kapsam_cozulen = 0
    hibrit_cozulen = 0
    gercek_cokme = 0
    ornek_raporlar = []
    derinlikler = {"rastgele": [], "kapsam": []}

    for h_i in range(AYAR["hedef_sayisi"]):
        sihir = rng.randint(1000, 60000)
        boyut_alt = rng.randint(500, 4000)
        boyut_ust = boyut_alt + rng.randint(4, 30)
        bayrak = rng.randint(1, 255)
        kaynak = HEDEF_SABLONU.format(sihir=sihir, alt=boyut_alt, ust=boyut_ust, bayrak=bayrak)
        ad_alani = {}
        exec(compile(kaynak, f"<hedef_{h_i}>", "exec"), ad_alani)   # gerçek hedef program
        ayristir = ad_alani["ayristir"]
        yollar = _yol_kosullari(kaynak)
        dal_ad = f"zafiyet_dali_{h_i}"
        kisitlar = yollar["cokme_dali"]
        kisit_sozlugu = {dal_ad: kisitlar, "imkansiz_dal": yollar["olu_dal"]}

        # 1) Kör rastgele fuzzer: rastgele 8 baytlık paketler gerçek ayrıştırıcıda çalışır
        aday_listesi, kor_cokme = [], False
        for _ in range(AYAR["fuzzer_bütce"]):
            veri = bytes(rng.getrandbits(8) for _ in range(8))
            _, c = _calistir(ayristir, veri)
            kor_cokme = kor_cokme or c
            aday_listesi.append(_alanlar(veri))
        derinlikler["rastgele"].append(max(_yol_derinligi(kisitlar, a) for a in aday_listesi))

        # 2) Kapsam güdümlü mutasyon fuzzer'ı (AFL benzeri): yeni (daha derin) dala ulaşan girdileri saklar ve onları mutasyona uğratır
        havuz = [bytes(rng.getrandbits(8) for _ in range(8))]
        en_derin, kap_cokme = 0, False
        for _ in range(AYAR["fuzzer_bütce"]):
            ebeveyn = bytearray(rng.choice(havuz))
            for _m in range(rng.randint(1, 3)):
                i = rng.randrange(8)
                ebeveyn[i] = rng.getrandbits(8) if rng.random() < 0.5 else ebeveyn[i] ^ (1 << rng.randrange(8))
            veri = bytes(ebeveyn)
            _, c = _calistir(ayristir, veri)
            kap_cokme = kap_cokme or c
            der = _yol_derinligi(kisitlar, _alanlar(veri))
            if der > en_derin:
                en_derin = der
                havuz.append(veri)
        derinlikler["kapsam"].append(en_derin)

        for ad in aday_listesi[:8]:
            d_ogr = deg_fn([dict(x) for x in kisitlar], dict(ad))
            d_ref = referans_degerlendir(kisitlar, ad)
            deg_ayni = deg_ayni and _yakin(d_ogr, d_ref)

        dr_ogr = daralt_fn([dict(x) for x in kisitlar], AYAR["alt_sinir"], AYAR["ust_sinir"])
        dr_ref = referans_daralt(kisitlar, AYAR["alt_sinir"], AYAR["ust_sinir"])
        daralt_ayni = daralt_ayni and _yakin(dr_ogr, dr_ref)

        hb_ogr = hibrit_fn({k: [dict(x) for x in v] for k, v in kisit_sozlugu.items()},
                           [dict(x) for x in aday_listesi], AYAR["alt_sinir"], AYAR["ust_sinir"], dal_ad)
        hb_ref = referans_hibrit(kisit_sozlugu, aday_listesi, AYAR["alt_sinir"], AYAR["ust_sinir"], dal_ad)
        hibrit_ayni = hibrit_ayni and _yakin(hb_ogr, hb_ref)

        # İmkansız dal kontrolü
        imk_ogr = hibrit_fn({k: [dict(x) for x in v] for k, v in kisit_sozlugu.items()},
                            [{"sihirli_baslik": 500}], AYAR["alt_sinir"], AYAR["ust_sinir"], "imkansiz_dal")
        imk_ref = referans_hibrit(kisit_sozlugu, [{"sihirli_baslik": 500}], AYAR["alt_sinir"], AYAR["ust_sinir"], "imkansiz_dal")
        hibrit_ayni = hibrit_ayni and _yakin(imk_ogr, imk_ref) and (not imk_ogr["basarili"])

        fuzzer_cozulen += int(kor_cokme)
        kapsam_cozulen += int(kap_cokme)
        if hb_ogr["basarili"]:
            hibrit_cozulen += 1
            # Çözücünün tetikleyicisi baytlara çevrilip GERÇEK programda çalıştırılır: çöktü mü?
            sonuc, c = _calistir(ayristir, _baytlar(hb_ogr["tetikleyici"], rng))
            gercek_cokme += int(c)
        if len(ornek_raporlar) < 3:
            ornek_raporlar.append(dict(hb_ogr, kisitlar=kisitlar))

    # 4) LLM ile yol koşulu çıkarımı (isteğe bağlı: Ollama yoksa atlanır, kabulü etkilemez)
    llm = {"durum": "atlandı", "hedef": 0, "dogru_cikarim": 0, "gecerli_kisit": 0, "cokme": 0, "onarimli_cokme": 0, "geri_bildirimli_cokme": 0,
           "hata_turleri": {"olu_dal_kosulu": 0, "yanlis_degisken_adi": 0, "eksik_kosul": 0}, "ornek": None}
    try:
        with ai_lab.SohbetOturumu() as oturum:
            llm.update(durum="koştu", model=oturum.model)
            for h_i in range(AYAR["llm_hedef"]):
                sihir, a_, u_, bay = rng.randint(1000, 60000), rng.randint(500, 4000), 0, rng.randint(1, 255)
                u_ = a_ + rng.randint(4, 30)
                kaynak = HEDEF_SABLONU.format(sihir=sihir, alt=a_, ust=u_, bayrak=bay)
                ad_alani = {}
                exec(compile(kaynak, f"<llm_hedef_{h_i}>", "exec"), ad_alani)
                beklenen = _yol_kosullari(kaynak)["cokme_dali"]
                kisit, ham, gecmis = _llm_kisitlari(oturum, kaynak)
                llm["hedef"] += 1
                llm["dogru_cikarim"] += int(sorted(map(str, kisit)) == sorted(map(str, beklenen)))
                olu = _yol_kosullari(kaynak)["olu_dal"]
                norm = _normalize(kisit)
                llm["hata_turleri"]["olu_dal_kosulu"] += int(any(k in norm for k in olu))
                llm["hata_turleri"]["yanlis_degisken_adi"] += int(any(k["degisken"] not in ALANLAR for k in kisit))
                llm["hata_turleri"]["eksik_kosul"] += int(any(b not in norm for b in beklenen))
                if kisit:
                    llm["gecerli_kisit"] += 1
                    dr = daralt_fn([dict(x) for x in kisit], AYAR["alt_sinir"], AYAR["ust_sinir"])
                    if dr.get("cozulebilir") and dr.get("aday") and all(k in dr["aday"] for k in ALANLAR):
                        llm["cokme"] += int(_calistir(ad_alani["ayristir"], _baytlar(dr["aday"], rng))[1])
                    cokti, kullanilan, gozlem = _onar_ve_dogrula(kisit, daralt_fn, ad_alani["ayristir"], rng)
                    llm["onarimli_cokme"] += int(cokti)
                    # Geri bildirimli tur: program hata satırına ulaşmadıysa gerçek davranışı LLM'e söyle, düzeltilmiş listeyi iste
                    if not cokti and gozlem is not None:
                        gb = (f"I ran the function with sihirli_baslik={gozlem[0]['sihirli_baslik']}, paket_boyutu={gozlem[0]['paket_boyutu']}, "
                              f"bayrak={gozlem[0]['bayrak']}, which satisfy your list. It returned {gozlem[1]!r} and did not reach HATA. "
                              "Some conditions are missing or wrong. Reply with the corrected JSON array only.")
                        kisit2, _h2, _ = _llm_kisitlari(oturum, kaynak, gecmis=gecmis, geri_bildirim=gb)
                        cokti = _onar_ve_dogrula(kisit2, daralt_fn, ad_alani["ayristir"], rng)[0] if kisit2 else False
                    llm["geri_bildirimli_cokme"] += int(cokti)
                if llm["ornek"] is None:
                    llm["ornek"] = {"beklenen": beklenen, "llm": kisit, "ham_yanit": ham}
            llm["ortam"] = {"temizlik": oturum.kayit.get("temizlik")}
    except ai_lab.GercekLabYok as e:
        llm["neden"] = str(e)[:200]

    n = AYAR["hedef_sayisi"]
    return {
        "llm_kisit_cikarimi": llm,
        "cihaz": "cpu (hedefler saf Python programları)",
        "dtype": "int",
        "surumler": {"python": platform.python_version()},
        "ayarlar": AYAR,
        "deg_ayni": deg_ayni,
        "daralt_ayni": daralt_ayni,
        "hibrit_ayni": hibrit_ayni,
        "yalniz_fuzzer_basari_orani": fuzzer_cozulen / n,
        "kapsam_fuzzer_basari_orani": kapsam_cozulen / n,
        "hibrit_basari_orani": hibrit_cozulen / n,
        "gercek_cokme_orani": gercek_cokme / n,
        "dal_derinligi": {"rastgele_ortalama": sum(derinlikler["rastgele"]) / n, "kapsam_ortalama": sum(derinlikler["kapsam"]) / n,
                          "toplam_kosul": len(ornek_raporlar[0]["kisitlar"]) if ornek_raporlar else None},
        "ornek_raporlar": ornek_raporlar,
        "olcum": (f"{n} gerçek hedef programda (Python paket ayrıştırıcısı; sihirli başlık + boyut aralığı + bayrak dalında sınır dışı yazma) "
                  f"{AYAR['fuzzer_bütce']} girdi bütçesiyle: kör rastgele fuzzer {fuzzer_cozulen}/{n} hedefte çöktürdü (ortalama dal derinliği "
                  f"{sum(derinlikler['rastgele']) / n:.2f}/4), kapsam güdümlü mutasyon fuzzer'ı {kapsam_cozulen}/{n} (derinlik "
                  f"{sum(derinlikler['kapsam']) / n:.2f}/4). Kaynak koddan (ast) çıkarılan yol koşullarıyla hibrit çözücü {hibrit_cozulen}/{n} "
                  f"hedefte tetikleyici üretti; tetikleyiciler gerçek programda {gercek_cokme}/{n} çökme verdi. Ölü dal her hedefte "
                  f"çözülemez bulundu. LLM ile yol koşulu çıkarımı ({llm['durum']}): {llm['dogru_cikarim']}/{llm['hedef']} hedefte "
                  f"ast ile birebir aynı kısıtlar, ham LLM kısıtlarının çözümü {llm['cokme']}/{llm['hedef']} hedefte gerçek programı çökertti; "
                  f"doğrulayıcıyla onarılınca {llm['onarimli_cokme']}/{llm['hedef']}, bir geri bildirim turuyla {llm['geri_bildirimli_cokme']}/"
                  f"{llm['hedef']}. LLM hata türleri (hedef sayısı): {llm['hata_turleri']}."),
        "sinir": ("Hedefler küçük, tek fonksiyonlu ve yazarın şablonundan üretilen Python programlarıdır; çökme, Python'un sınır denetimiyle "
                  "IndexError olarak gözlenir (C'deki sessiz bellek bozulması değil). Yol koşulları yalnız 'değişken op sabit' biçimindeki "
                  "if'lerden çıkarılır; aralık daraltma bağımsız doğrusal kısıtları çözer, özet (SHA-256) ya da doğrusal olmayan kısıtları "
                  "tersine çeviremez. Z3 gibi tam bir SMT çözücü ve LLM destekli tohum üretimi (AIxCC sistemleri) kullanılmaz.")
    }


def goster(deg_fn, daralt_fn, hibrit_fn):
    r = deney(deg_fn, daralt_fn, hibrit_fn)
    print("Cihaz:", r["cihaz"], "| hedef program sayısı:", AYAR["hedef_sayisi"], "| girdi bütçesi:", AYAR["fuzzer_bütce"])
    print("Kör fuzzer: %.2f | kapsam güdümlü fuzzer: %.2f | hibrit (fuzzer + sembolik): %.2f | tetikleyici gerçek programı çökertti: %.2f" % (
        r["yalniz_fuzzer_basari_orani"], r["kapsam_fuzzer_basari_orani"], r["hibrit_basari_orani"], r["gercek_cokme_orani"]))
    print("Dal derinliği:", r["dal_derinligi"])
    l = r["llm_kisit_cikarimi"]
    print("LLM yol koşulu çıkarımı (%s): doğru %d/%d | ham çökme %d | onarımlı çökme %d | geri bildirimli çökme %d | hata türleri %s" % (
        l["durum"], l["dogru_cikarim"], l["hedef"], l["cokme"], l["onarimli_cokme"], l["geri_bildirimli_cokme"], l["hata_turleri"]))
    if l.get("ornek"):
        print("  beklenen:", l["ornek"]["beklenen"], "\n  LLM     :", l["ornek"]["llm"])
    print("Örnek çözüm:", r["ornek_raporlar"][0])
    print("Sınır:", r["sinir"])
    print("Kanıt:", ai_lab.kanit_yaz("ai-ile-guvenlik-20-run", {"kaynak": "gercek", "kabul": False, "ders": "ai-ile-guvenlik-20", "deney": r}))
