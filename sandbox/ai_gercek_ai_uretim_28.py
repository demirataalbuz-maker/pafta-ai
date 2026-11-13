# -*- coding: utf-8 -*-
"""ai-uretim-28 gerçek deney: gerçek el yazısı rakamlarda AdaLN-Zero bloklu küçük bir DiT tarzı hız ağı rectified flow ile
eğitilir. Öğrencinin AdaLN-Zero katmanı ağın gerçek ara değerleriyle (eğitim öncesi birim dönüşüm, eğitim sonrası
modülasyon) torch'a karşı sınanır; örnekler öğrencinin Euler entegrasyonuyla üretilir ve adım sayısına göre gerçek
bir sınıflandırıcıyla puanlanır."""
import ai_lab
from sandbox import ai_uretim_ortak as O
from sandbox.ai_gercek_ai_uretim_27 import rakam_verisi

AYAR = {"adim": 4000, "batch": 256, "lr": 2e-3, "seed": 28, "genislik": 128, "blok": 2, "adim_sayilari": [1, 2, 4, 8, 32], "ornek_sinif": 10,
        "reflow_cift": 4000, "reflow_adim": 3000, "zehir_sayilari": [0, 30, 120]}


def _ag(torch):
    D = AYAR["genislik"]

    class Blok(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.ln = torch.nn.LayerNorm(D, eps=1e-6, elementwise_affine=False)
            self.mlp = torch.nn.Sequential(torch.nn.Linear(D, 2 * D), torch.nn.GELU(), torch.nn.Linear(2 * D, D))
            self.mod = torch.nn.Linear(D, 3 * D)
            torch.nn.init.zeros_(self.mod.weight); torch.nn.init.zeros_(self.mod.bias)       # AdaLN-Zero: başta alpha = 0

        def parcalar(self, h, k):
            gamma, beta, alpha = self.mod(k).chunk(3, -1)
            girdi = self.ln(h) * (1 + gamma) + beta
            return gamma, beta, alpha, girdi, self.mlp(girdi)

        def forward(self, h, k):
            _, _, alpha, _, alt = self.parcalar(h, k)
            return h + alpha * alt

    class Net(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.giris = torch.nn.Linear(64, D)
            self.sinif = torch.nn.Embedding(10, D)
            self.zaman = torch.nn.Sequential(torch.nn.Linear(1, D), torch.nn.SiLU(), torch.nn.Linear(D, D))
            self.bloklar = torch.nn.ModuleList([Blok() for _ in range(AYAR["blok"])])
            self.cikis = torch.nn.Linear(D, 64)

        def kosul(self, t, c):
            return torch.nn.functional.silu(self.zaman(t[:, None]) + self.sinif(c))

        def forward(self, x, t, c):
            h, k = self.giris(x), self.kosul(t, c)
            for b in self.bloklar:
                h = b(h, k)
            return self.cikis(h)
    return Net()


def _egit_rf(torch, net, x0_kume, x1_kume, c_kume, adim, rastgele_eslesme):
    opt = torch.optim.Adam(net.parameters(), lr=AYAR["lr"])
    for _ in range(adim):
        idx = torch.randint(0, x1_kume.shape[0], (AYAR["batch"],))
        x0 = torch.randn(AYAR["batch"], 64) if rastgele_eslesme else x0_kume[idx]
        t = torch.rand(AYAR["batch"])
        xt = (1 - t)[:, None] * x0 + t[:, None] * x1_kume[idx]
        kayip = ((net(xt, t, c_kume[idx]) - (x1_kume[idx] - x0)) ** 2).mean()
        opt.zero_grad(); kayip.backward(); opt.step()
    return net


def _euler(torch, net, x, c, N):
    with torch.no_grad():
        for s in range(N):
            x = x + net(x, torch.full((x.shape[0],), s / N), c) / N
    return x


def _cesitlilik(torch, x, c):
    return float(torch.stack([torch.pdist(x[c == k]).mean() for k in range(10)]).mean())


def _reflow(torch, net, sinif):
    """1-Rectified Flow'un ürettiği (gürültü, örnek) çiftleriyle yeniden eğitim: yollar düzleşir, tek adımlı örnekleme iyileşir mi?"""
    import copy
    g = torch.Generator().manual_seed(AYAR["seed"] + 5)
    n = AYAR["reflow_cift"]
    x0 = torch.randn(n, 64, generator=g)
    c = torch.randint(0, 10, (n,), generator=g)
    x1 = _euler(torch, net, x0, c, 32)
    torch.manual_seed(AYAR["seed"] + 6)
    net2 = _egit_rf(torch, copy.deepcopy(net), x0, x1, c, AYAR["reflow_adim"], False)
    hedef = torch.arange(10).repeat_interleave(AYAR["ornek_sinif"])
    z = torch.randn(hedef.shape[0], 64, generator=torch.Generator().manual_seed(11))
    sonuc = {}
    for ad, m in (("1_rectified", net), ("2_rectified_reflow", net2)):
        bir, otuz = _euler(torch, m, z, hedef, 1), _euler(torch, m, z, hedef, 32)
        sonuc[ad] = {"tek_adim_32_adim_mesafesi": float((bir - otuz).norm(dim=1).mean()),
                     "tek_adim_dogruluk": float((torch.tensor(sinif.predict(bir.clamp(-1, 1).numpy())) == hedef).float().mean()),
                     "tek_adim_cesitlilik": _cesitlilik(torch, bir.clamp(-1, 1), hedef)}
    return sonuc


def _zehirleme(torch, X, y, egt, sinif):
    """Veri zehirleme: eğitim kümesine '3' etiketli '8' görüntüleri eklenir; '3' istendiğinde üretilen görüntülerin kaçı '8'?"""
    sekiz = egt[y[egt] == 8]
    hedef = torch.full((AYAR["ornek_sinif"] * 10,), 3)
    z = torch.randn(hedef.shape[0], 64, generator=torch.Generator().manual_seed(12))
    uc_sayisi = int((y[egt] == 3).sum())
    sonuc = {}
    for k in AYAR["zehir_sayilari"]:
        Xe = torch.cat([X[egt], X[sekiz[:k]]])
        ye = torch.cat([y[egt], torch.full((k,), 3)])
        torch.manual_seed(AYAR["seed"] + 7)
        m = _egit_rf(torch, _ag(torch), None, Xe, ye, AYAR["adim"], True)
        tah = torch.tensor(sinif.predict(_euler(torch, m, z, hedef, 8).clamp(-1, 1).numpy()))
        sonuc[k] = {"zehir_orani_sinif3": round(k / (uc_sayisi + k), 3), "uc_istendi_sekiz_cikti": float((tah == 8).float().mean()),
                    "uc_istendi_uc_cikti": float((tah == 3).float().mean())}
    return sonuc


def deney(rectified_flow_euler, adaln_zero_katmani):
    torch = O.torch_al()
    torch.manual_seed(AYAR["seed"])
    X, y, egt, tst, sinif = rakam_verisi(torch, AYAR["seed"])
    net = _ag(torch)
    # 1) Eğitim öncesi: AdaLN-Zero bloğu birim dönüşüm olmalı (gerçek bir rakamın gizli durumuyla)
    with torch.no_grad():
        h0 = net.giris(X[egt[:1]]); k0 = net.kosul(torch.tensor([0.5]), y[egt[:1]])
        gam, bet, alp, gir, alt = net.bloklar[0].parcalar(h0, k0)
        cik = net.bloklar[0](h0, k0)
    o0 = adaln_zero_katmani(O.liste(h0[0]), O.liste(gam[0]), O.liste(bet[0]), O.liste(alp[0]), O.liste(alt[0]))
    baslangic_birim = o0["birim_donusum_mu"] and O.en_buyuk_fark(o0["katman_ciktisi"], O.liste(cik[0])) <= 1e-6 and torch.equal(cik, h0)
    # 2) Rectified flow eğitimi
    opt = torch.optim.Adam(net.parameters(), lr=AYAR["lr"])
    Xe, ye = X[egt], y[egt]
    for _ in range(AYAR["adim"]):
        idx = torch.randint(0, Xe.shape[0], (AYAR["batch"],))
        x0 = torch.randn(AYAR["batch"], 64)
        t = torch.rand(AYAR["batch"])
        xt = (1 - t)[:, None] * x0 + t[:, None] * Xe[idx]
        kayip = ((net(xt, t, ye[idx]) - (Xe[idx] - x0)) ** 2).mean()
        opt.zero_grad(); kayip.backward(); opt.step()
    # 3) Eğitim sonrası AdaLN-Zero modülasyonu, gerçek ara değerlerle
    with torch.no_grad():
        h = net.giris(X[tst[:1]]); k = net.kosul(torch.tensor([0.3]), y[tst[:1]])
        gam, bet, alp, gir, alt = net.bloklar[0].parcalar(h, k)
        cik = net.bloklar[0](h, k)
    o1 = adaln_zero_katmani(O.liste(h[0]), O.liste(gam[0]), O.liste(bet[0]), O.liste(alp[0]), O.liste(alt[0]))
    adaln_fark = max(O.goreli_fark(o1["mod_edilmis_girdi"], O.liste(gir[0])), O.goreli_fark(o1["katman_ciktisi"], O.liste(cik[0])))
    alpha_norm = float(alp.norm())
    # 4) Örnekleme: torch hızları, entegrasyon öğrencinin Euler işleviyle; adım sayısına göre kalite
    hedef = torch.arange(10).repeat_interleave(AYAR["ornek_sinif"])
    n = hedef.shape[0]
    kalite, euler_fark, akis_kaybi, cesit = {}, 0.0, {}, {}
    gercek_cesit = float(torch.stack([torch.pdist(X[tst][y[tst] == c]).mean() for c in range(10)]).mean())
    for N in AYAR["adim_sayilari"]:
        x = torch.randn(n, 64, generator=torch.Generator().manual_seed(5))
        x_bas = x.clone()
        hizlar = []
        for s in range(N):
            with torch.no_grad():
                v = net(x, torch.full((n,), s / N), hedef)
            hizlar.append(v)
            x = x + v / N
        ornek, kayiplar = [], []
        ref_x1 = X[tst][[int((y[tst] == int(c)).nonzero()[0, 0]) for c in hedef]]
        for i in range(n):
            o = rectified_flow_euler(O.liste(x_bas[i]), O.liste(ref_x1[i]), [O.liste(h_[i]) for h_ in hizlar], N)
            ornek.append(o["euler_cikti"]); kayiplar.append(o["ortalama_flow_kaybi"])
        ornek = torch.tensor(ornek)
        euler_fark = max(euler_fark, float((ornek - x.double()).abs().max()))
        tahmin = torch.tensor(sinif.predict(ornek.clamp(-1, 1).float().numpy()))
        kalite[str(N)] = float((tahmin == hedef).float().mean())
        oc = ornek.clamp(-1, 1).float()
        cesit[str(N)] = float(torch.stack([torch.pdist(oc[hedef == c]).mean() for c in range(10)]).mean())
        akis_kaybi[str(N)] = sum(kayiplar) / n
    RF = _reflow(torch, net, sinif)
    ZH = _zehirleme(torch, X, y, egt, sinif)
    zs = AYAR["zehir_sayilari"]
    return {
        "surumler": O.surumler("scikit-learn"), "veri": "sklearn load_digits", "egitim_adim": AYAR["adim"],
        "baslangic_birim_donusum": baslangic_birim, "adaln_egitim_sonrasi_fark": adaln_fark, "adaln_ayni": adaln_fark <= 1e-5,
        "egitim_sonrasi_alpha_norm": alpha_norm, "euler_en_buyuk_fark": euler_fark, "euler_ayni": euler_fark <= 1e-5,
        "adim_kalite": kalite, "adim_akis_kaybi": akis_kaybi, "adim_cesitlilik": cesit, "gercek_cesitlilik": gercek_cesit,
        "az_adimda_iyi": kalite["4"] >= 0.8, "tek_adim_ortalamaya_coker": cesit["1"] < cesit["32"],
        "reflow": RF, "reflow_duzlestirdi": (RF["2_rectified_reflow"]["tek_adim_32_adim_mesafesi"] < 0.5 * RF["1_rectified"]["tek_adim_32_adim_mesafesi"]
                                             and RF["2_rectified_reflow"]["tek_adim_cesitlilik"] > RF["1_rectified"]["tek_adim_cesitlilik"]),
        "zehirleme": ZH, "zehir_arttikca_sapiyor": (ZH[zs[0]]["uc_istendi_sekiz_cikti"] <= 0.05
                                                     and ZH[zs[1]]["uc_istendi_sekiz_cikti"] > ZH[zs[0]]["uc_istendi_sekiz_cikti"]
                                                     and ZH[zs[2]]["uc_istendi_sekiz_cikti"] > ZH[zs[1]]["uc_istendi_sekiz_cikti"]),
        "olcum": (f"Gerçek rakamlarda {AYAR['adim']} adım rectified flow, {AYAR['blok']} AdaLN-Zero bloklu ağ. Eğitim öncesi blok birim dönüşüm: "
                  f"{baslangic_birim}; eğitim sonrası alpha normu {alpha_norm:.2f}, öğrencinin modülasyonu torch'tan {adaln_fark:.1e}. "
                  f"Öğrencinin Euler entegrasyonu torch'tan {euler_fark:.1e}. Sınıflandırıcıyla koşullu doğruluk, Euler adım sayısına göre: "
                  + ", ".join(f"{k}: {v:.2f}" for k, v in kalite.items()) + "; sınıf içi çeşitlilik " + ", ".join(f"{k}: {v:.2f}" for k, v in cesit.items())
                  + f" (gerçek test görüntüleri {gercek_cesit:.2f}). Reflow ({AYAR['reflow_cift']} çift, {AYAR['reflow_adim']} adım): tek adım ile 32 adım "
                  f"arasındaki mesafe {RF['1_rectified']['tek_adim_32_adim_mesafesi']:.2f} → {RF['2_rectified_reflow']['tek_adim_32_adim_mesafesi']:.2f}, "
                  f"tek adım çeşitliliği {RF['1_rectified']['tek_adim_cesitlilik']:.2f} → {RF['2_rectified_reflow']['tek_adim_cesitlilik']:.2f}. "
                  "Zehirleme ('3' etiketli '8' görüntüsü sayısı → '3' istenince '8' üretme oranı): "
                  + ", ".join(f"{k}: {v['uc_istendi_sekiz_cikti']:.2f}" for k, v in ZH.items()) + "."),
        "sinir": ("Hız ağı 8×8 rakamlar için küçük bir MLP-DiT'tir (yama, dikkat ve gerçek görüntü ölçeği yoktur); reflow tek tur ve "
                  "küçük ölçekte yapılır, damıtma (tek adımlı öğrenci) yoktur. Kalite gerçek veride eğitilmiş lojistik regresyonla ölçülür; akış "
                  "kaybı tek bir referans görüntüye göredir. Zehirleme saldırganın etiketli veri ekleyebildiğini varsayar; gerçek "
                  "metin-görüntü modellerinde aynı etki metin açıklaması ile içerik arasındaki bağın bozulmasıyla görülür."),
    }


def goster(rectified_flow_euler, adaln_zero_katmani):
    r = deney(rectified_flow_euler, adaln_zero_katmani)
    print("Eğitim öncesi birim dönüşüm: %s | eğitim sonrası AdaLN farkı: %.1e (alpha normu %.2f)" % (r["baslangic_birim_donusum"], r["adaln_egitim_sonrasi_fark"], r["egitim_sonrasi_alpha_norm"]))
    print("Euler entegrasyonu farkı: %.1e" % r["euler_en_buyuk_fark"])
    for k, v in r["adim_kalite"].items():
        print("  %3s adım: koşullu doğruluk %.2f | sınıf içi çeşitlilik %.2f" % (k, v, r["adim_cesitlilik"][k]))
    print("Gerçek görüntülerin sınıf içi çeşitliliği: %.2f" % r["gercek_cesitlilik"])
    print("Sınır:", r["sinir"])
    print("Kanıt:", O.kanit("ai-uretim-28", "run", r))
