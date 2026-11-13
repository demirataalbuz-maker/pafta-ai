"""Doğrulanabilir çıkarım (zkML) ve sabit nokta (fixed-point) aritmetik devre doğrulaması."""
import hashlib, importlib.metadata, math, random, secrets
import ai_lab

AYAR = {"seed": 47, "gizli": 16, "adim": 220, "lr": 0.015, "olcek_us": 10, "ornek": 48, "olcek_tarama": [2, 3, 4, 6, 8, 10, 12],
        "denetim_k": [1, 8, 32, 128]}


def _sayi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)


def _tam(v):
    return not isinstance(v, bool) and isinstance(v, int)


def referans_sabit_nokta_nicemle(degerler, olcek_us):
    if not isinstance(degerler, list) or not degerler or not all(_sayi(v) for v in degerler):
        raise ValueError("degerler")
    if not _tam(olcek_us) or not 1 <= olcek_us <= 24:
        raise ValueError("olcek_us")
    s = 1 << olcek_us
    q = [int(math.floor(x * s + 0.5)) for x in degerler]
    geri = [float(v / s) for v in q]
    hata = max(abs(x - g) for x, g in zip(degerler, geri))
    return {"tam_sayilar": q, "geri_yuklenen": geri, "max_hata": float(hata)}


def referans_sabit_nokta_ic_carpim(q_girdi, q_agirlik, q_bias, olcek_us):
    if not isinstance(q_girdi, list) or not isinstance(q_agirlik, list) or not q_girdi or len(q_girdi) != len(q_agirlik):
        raise ValueError("vektör")
    if not all(_tam(v) for v in q_girdi + q_agirlik) or not _tam(q_bias):
        raise ValueError("tam sayı")
    if not _tam(olcek_us) or not 1 <= olcek_us <= 24:
        raise ValueError("olcek_us")
    s = 1 << olcek_us
    ham = sum(x * w for x, w in zip(q_girdi, q_agirlik)) + q_bias * s
    olcekli = ham // s
    kalan = ham % s
    return {"ham_toplam": int(ham), "olcekli_cikti": int(olcekli), "kalan": int(kalan), "relu_cikti": int(max(0, olcekli))}


def referans_devre_dogrula(q_girdi, q_agirlik, q_bias, iddia_edilen_cikti, olcek_us, beklenen_ozet):
    if not _tam(iddia_edilen_cikti) or not isinstance(beklenen_ozet, str) or not beklenen_ozet.strip():
        raise ValueError("iddia/özet")
    ic = referans_sabit_nokta_ic_carpim(q_girdi, q_agirlik, q_bias, olcek_us)
    metin = ",".join(str(w) for w in q_agirlik) + "|" + str(q_bias) + "|" + str(olcek_us)
    gercek_ozet = hashlib.sha256(metin.encode("utf-8")).hexdigest()
    ozet_ok = (gercek_ozet == beklenen_ozet)
    hesap_ok = (iddia_edilen_cikti == ic["relu_cikti"])
    s = 1 << olcek_us
    kalan_ok = (0 <= ic["kalan"] < s) and (ic["ham_toplam"] == ic["olcekli_cikti"] * s + ic["kalan"])
    return {
        "gecerli": bool(ozet_ok and hesap_ok and kalan_ok),
        "ozet_eslesti": bool(ozet_ok),
        "hesap_dogru": bool(hesap_ok),
        "gercek_cikti": int(ic["relu_cikti"]),
        "gercek_ozet": gercek_ozet
    }


def _yakin(a, b, tol=1e-7):
    if isinstance(a, dict):
        return isinstance(b, dict) and set(a) == set(b) and all(_yakin(a[k], b[k], tol) for k in a)
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(_yakin(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, (bool, str, int)) or a is None:
        return type(a) is type(b) and a == b
    return _sayi(a) and _sayi(b) and abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def _h(b):
    return hashlib.sha256(b).hexdigest()


def _merkle(yapraklar):
    """Merkle ağacı: katmanlar listesi (0 = yapraklar). Tek kalan düğüm kendisiyle eşlenir."""
    kat = [list(yapraklar)]
    while len(kat[-1]) > 1:
        a = kat[-1]
        kat.append([_h((a[i] + (a[i + 1] if i + 1 < len(a) else a[i])).encode()) for i in range(0, len(a), 2)])
    return kat


def _yol(kat, i):
    out = []
    for a in kat[:-1]:
        j = i ^ 1
        out.append(a[j] if j < len(a) else a[i])
        i //= 2
    return out


def _yol_dogrula(yaprak, i, yol, kok):
    h = yaprak
    for kardes in yol:
        h = _h((h + kardes).encode()) if i % 2 == 0 else _h((kardes + h).encode())
        i //= 2
    return h == kok


def _merkle_denetim(torch, dogrula_fn):
    """Gerçek SmolLM2 ağırlıkları üzerinde taahhüt + rastgele denetim: ağırlıklar ifşa edilmeden (yalnız denetlenen satırlar) sağlayıcının
    taahhüt ettiği modeli kullanıp kullanmadığı denetlenir. Devre ifadesi bu dersin ReLU nöronudur."""
    tok, model, bilgi = ai_lab.dil_modeli()
    model.to("cpu")
    W = model.model.layers[0].mlp.gate_proj.weight.detach().double()                # (1536, 576)
    kayit = {}
    k_ = model.model.layers[0].mlp.gate_proj.register_forward_pre_hook(lambda m, a: kayit.__setitem__("x", a[0][0, -1].detach().double()))
    try:
        with torch.no_grad():
            model(tok("The audit team checked every invoice before the deadline.", return_tensors="pt").input_ids)
    finally:
        k_.remove()
    us, s = AYAR["olcek_us"], 1 << AYAR["olcek_us"]
    qW = torch.floor(W * s + 0.5).to(torch.int64)
    qx = [int(v) for v in torch.floor(kayit["x"] * s + 0.5).to(torch.int64).tolist()]
    satirlar = qW.tolist()
    yapraklar = [_h((",".join(str(w) for w in r) + "|0|" + str(us)).encode()) for r in satirlar]
    kat = _merkle(yapraklar)
    kok = kat[-1][0]
    durust = [max(0, (sum(a * b for a, b in zip(qx, r))) // s) for r in satirlar]
    n = len(satirlar)
    rnd = random.Random(AYAR["seed"])
    # 1) Dürüst sağlayıcı: rastgele 32 satır açılır, Merkle yolu ve öğrencinin devre doğrulaması
    denet = rnd.sample(range(n), 32)
    durust_gecti = all(_yol_dogrula(yapraklar[i], i, _yol(kat, i), kok) and dogrula_fn(list(qx), list(satirlar[i]), 0, durust[i], us, yapraklar[i])["gecerli"]
                       for i in denet)
    # 2) Tek satır kurcalanmış (arka kapı): sağlayıcı r. satırı değiştirip hesaplar; denetlenirse ya yol ya hesap tutmaz
    r = rnd.randrange(n)
    kurcali = list(satirlar[r]); kurcali[0] += 50 * s
    sahte_r = max(0, sum(a * b for a, b in zip(qx, kurcali)) // s)
    yakalandi_kurcali = (not _yol_dogrula(_h((",".join(str(w) for w in kurcali) + "|0|" + str(us)).encode()), r, _yol(kat, r), kok)
                         and not dogrula_fn(list(qx), list(satirlar[r]), 0, sahte_r, us, yapraklar[r])["gecerli"]) if sahte_r != durust[r] else None
    # 3) Ucuz model: sağlayıcı bütün satırları 4 bitle hesaplıyor; hangi satırların çıktısı farklı?
    q4 = (torch.round(W / (W.abs().max(1, keepdim=True).values / 7)).clamp(-7, 7) * (W.abs().max(1, keepdim=True).values / 7))
    ucuz = [max(0, (sum(a * b for a, b in zip(qx, rr))) // s) for rr in torch.floor(q4 * s + 0.5).to(torch.int64).tolist()]
    farkli = [i for i in range(n) if ucuz[i] != durust[i]]
    # 4) Yakalanma olasılığı (2 000 rastgele denetim, k satır): ölçülen ve kuramsal
    tablo = {}
    for k in AYAR["denetim_k"]:
        tek = sum(r in set(rnd.sample(range(n), k)) for _ in range(2000)) / 2000
        f = set(farkli)
        uc = sum(bool(f & set(rnd.sample(range(n), k))) for _ in range(2000)) / 2000
        tablo[k] = {"ifsa_orani": round(k / n, 4), "tek_satir_yakalama": tek, "tek_satir_kuramsal": round(k / n, 4),
                    "ucuz_model_yakalama": uc, "ucuz_model_kuramsal": round(1 - (1 - len(farkli) / n) ** k, 4)}
    return {"model": bilgi.get("model"), "katman": "model.layers.0.mlp.gate_proj", "satir": n, "merkle_koku": kok,
            "durust_32_denetim_gecti": durust_gecti, "kurcalanan_satir": r, "kurcali_denetlenince_yakalandi": yakalandi_kurcali,
            "ucuz_model_farkli_satir_orani": round(len(farkli) / n, 4), "tablo": tablo}


def deney(nicemle_fn, ic_carpim_fn, dogrula_fn):
    try:
        import torch
        from sklearn.datasets import load_digits
    except ImportError as e:
        raise ai_lab.GercekLabYok(str(e)) from e
    cihaz = ai_lab.torch_cihazi()
    seed = AYAR["seed"] + secrets.randbelow(500)
    torch.manual_seed(seed)
    v = load_digits()
    X = torch.tensor(v.data / 16.0, dtype=torch.float32, device=cihaz)
    Y = torch.tensor(v.target, dtype=torch.long, device=cihaz)
    net = torch.nn.Sequential(torch.nn.Linear(64, AYAR["gizli"]), torch.nn.ReLU(), torch.nn.Linear(AYAR["gizli"], 10)).to(cihaz)
    opt = torch.optim.Adam(net.parameters(), lr=AYAR["lr"])
    for _ in range(AYAR["adim"]):
        opt.zero_grad()
        torch.nn.functional.cross_entropy(net(X[:1300]), Y[:1300]).backward()
        opt.step()

    rng = random.Random(secrets.randbits(64))
    secim = rng.sample(range(1300, len(X)), AYAR["ornek"])
    X_sec = X[secim]
    u_us = AYAR["olcek_us"]
    s = 1 << u_us

    with torch.no_grad():
        w0 = net[0].weight[0].detach().double().tolist()
        b0 = float(net[0].bias[0].detach().double().item())
        gercek_relu0 = torch.relu(net[0](X_sec)[:, 0]).double().tolist()

    nw_ref = referans_sabit_nokta_nicemle(w0, u_us)
    nw_ogr = nicemle_fn(list(w0), u_us)
    nb_ref = referans_sabit_nokta_nicemle([b0], u_us)["tam_sayilar"][0]
    nicem_ayni = _yakin(nw_ogr, nw_ref)

    q_w = nw_ref["tam_sayilar"]
    taahhut = hashlib.sha256((",".join(str(w) for w in q_w) + "|" + str(nb_ref) + "|" + str(u_us)).encode("utf-8")).hexdigest()

    ic_ayni, dogrula_ayni = True, True
    devre_hatalari = []
    durust_gecerli_sayisi = 0
    sahte_red_sayisi = 0

    for i in range(len(secim)):
        xi = X_sec[i].detach().double().tolist()
        nx_ref = referans_sabit_nokta_nicemle(xi, u_us)
        nx_ogr = nicemle_fn(list(xi), u_us)
        nicem_ayni = nicem_ayni and _yakin(nx_ogr, nx_ref)
        q_x = nx_ref["tam_sayilar"]

        ic_r = referans_sabit_nokta_ic_carpim(q_x, q_w, nb_ref, u_us)
        ic_o = ic_carpim_fn(list(q_x), list(q_w), nb_ref, u_us)
        ic_ayni = ic_ayni and _yakin(ic_o, ic_r)
        devre_hatalari.append(abs(gercek_relu0[i] - ic_r["relu_cikti"] / s))

        # 1) Dürüst kanıt doğrulaması
        d_durust_r = referans_devre_dogrula(q_x, q_w, nb_ref, ic_r["relu_cikti"], u_us, taahhut)
        d_durust_o = dogrula_fn(list(q_x), list(q_w), nb_ref, ic_r["relu_cikti"], u_us, taahhut)
        dogrula_ayni = dogrula_ayni and _yakin(d_durust_o, d_durust_r)
        if d_durust_o["gecerli"]:
            durust_gecerli_sayisi += 1

        # 2) Hileli çıktı veya sahte ağırlık taahhüdü doğrulaması
        d_hile_cikti = dogrula_fn(list(q_x), list(q_w), nb_ref, ic_r["relu_cikti"] + 1, u_us, taahhut)
        d_hile_agirlik = dogrula_fn(list(q_x), [q_w[0] + 1] + list(q_w[1:]), nb_ref, ic_r["relu_cikti"], u_us, taahhut)
        if not d_hile_cikti["gecerli"] and not d_hile_agirlik["gecerli"]:
            sahte_red_sayisi += 1

    # Ölçek taraması: ağın tamamı (iki katman, 10 logit) tamsayı aritmetiğiyle; float modelle karar uyumu ve logit hatası
    X_test = X[1300:]
    with torch.no_grad():
        float_logit = net(X_test).double().cpu()
    tarama = {}
    for us in AYAR["olcek_tarama"]:
        s_ = 1 << us
        q = lambda t: torch.round(t.detach().double().cpu() * s_).to(torch.int64)   # noqa: E731
        qx, qW1, qb1, qW2, qb2 = q(X_test), q(net[0].weight), q(net[0].bias), q(net[2].weight), q(net[2].bias)
        h = torch.clamp(qx @ qW1.T + qb1 * s_, min=0) // s_          # ölçek s² → s (devredeki yeniden ölçekleme)
        z = (h @ qW2.T + qb2 * s_).double() / (s_ * s_)
        tarama[f"2^{us}"] = {"karar_uyumu": round(float((z.argmax(1) == float_logit.argmax(1)).double().mean()), 4),
                            "ort_logit_hatasi": round(float((z - float_logit).abs().mean()), 5),
                            "dogruluk": round(float((z.argmax(1) == Y[1300:].cpu()).double().mean()), 4)}
    float_dogruluk = round(float((float_logit.argmax(1) == Y[1300:].cpu()).double().mean()), 4)
    MD = _merkle_denetim(torch, dogrula_fn)
    t = MD["tablo"]
    kmax = max(t)

    return {
        "merkle_denetim": MD,
        "denetim_calisiyor": bool(MD["durust_32_denetim_gecti"] and MD["kurcali_denetlenince_yakalandi"] is not False
                                  and t[1]["ucuz_model_yakalama"] >= 0.4 and t[kmax]["ucuz_model_yakalama"] >= 0.99
                                  and abs(t[kmax]["tek_satir_yakalama"] - t[kmax]["tek_satir_kuramsal"]) <= 0.03
                                  and t[kmax]["tek_satir_yakalama"] <= 0.15),
        "olcek_taramasi": tarama, "float_dogruluk": float_dogruluk,
        "cihaz": str(cihaz), "dtype": "float32",
        "surumler": {x: importlib.metadata.version(x) for x in ("torch", "scikit-learn")},
        "ayarlar": AYAR, "seed": seed, "secim": secim, "taahhut_ozeti": taahhut,
        "nicem_ayni": nicem_ayni, "ic_ayni": ic_ayni, "dogrula_ayni": dogrula_ayni,
        "ort_devre_hatasi": sum(devre_hatalari) / len(devre_hatalari),
        "max_agirlik_nicem_hatasi": nw_ref["max_hata"],
        "durust_gecerli_sayisi": durust_gecerli_sayisi,
        "sahte_red_sayisi": sahte_red_sayisi,
        "olcum": (f"{AYAR['ornek']} gerçek test örneğinde ilk katman nöronunun 2^{u_us} ölçekli sabit nokta devresi: ortalama ReLU hatası "
                  f"{sum(devre_hatalari) / len(devre_hatalari):.5f}, dürüst kanıt {durust_gecerli_sayisi}/{len(secim)} kabul, hileli çıktı ve sahte "
                  f"ağırlık {sahte_red_sayisi}/{len(secim)} red. Ağın tamamı tamsayı aritmetiğiyle (float doğruluk {float_dogruluk}): {tarama}. "
                  f"SmolLM2 {MD['katman']} ({MD['satir']} satır) Merkle taahhüdü: dürüst sağlayıcı 32 rastgele denetimi geçti "
                  f"({MD['durust_32_denetim_gecti']}); 4 bitlik ucuz model satırların %{100 * MD['ucuz_model_farkli_satir_orani']:.0f}'inde farklı çıktı "
                  f"verdi. Yakalanma (k denetlenen satır: ifşa oranı / tek satır kurcalama / ucuz model): "
                  + "; ".join(f"k={k} {v['ifsa_orani']} / {v['tek_satir_yakalama']:.3f} / {v['ucuz_model_yakalama']:.3f}" for k, v in t.items()) + "."),
        "sinir": ("Sabit nokta aritmetik kısıtları ve SHA-256 taahhüdü zkML devrelerinin aritmetik çekirdeğidir; burada doğrulayıcı ağırlıkları "
                  "görür, yani sıfır bilgi değildir. Kriptografik sıfır-bilgi gizliliği ve kısa kanıt için polinom taahhüdü ve SNARK "
                  "(ör. Halo2, EZKL) gerekir; kanıt üretim süresi ve devre boyutu ölçülmez. Merkle taahhüdü ve rastgele denetim ağırlıkların "
                  "yalnız denetlenen satırlarını ifşa eder (sıfır bilgi değildir) ve tek bir satırdaki kurcalamayı ancak o satır denetlenirse "
                  "yakalar; devre ifadesi bu dersin ReLU nöronudur, SmolLM2'nin kendi SiLU'lu çıktısı değildir.")
    }


def goster(nicemle_fn, ic_carpim_fn, dogrula_fn):
    r = deney(nicemle_fn, ic_carpim_fn, dogrula_fn)
    print("Cihaz:", r["cihaz"], "| Ölçek: 2^%d | Taahhüt: %s..." % (AYAR["olcek_us"], r["taahhut_ozeti"][:16]))
    print("Float32 vs Sabit Nokta ortalama ReLU farkı: %.6f | Ağırlık max nicemleme hatası: %.6f" % (
        r["ort_devre_hatasi"], r["max_agirlik_nicem_hatasi"]))
    print("Dürüst kanıt kabul: %d/%d | Hileli kanıt red: %d/%d" % (
        r["durust_gecerli_sayisi"], AYAR["ornek"], r["sahte_red_sayisi"], AYAR["ornek"]))
    print("Tam ağ ölçek taraması (float doğruluk %.3f):" % r["float_dogruluk"])
    for k, v in r["olcek_taramasi"].items():
        print("  %-5s %s" % (k, v))
    print("Sınır:", r["sinir"])
    print("Kanıt:", ai_lab.kanit_yaz("ai-guvence-47-run", {"kaynak": "gercek", "kabul": False, "ders": "ai-guvence-47", "deney": r}))
