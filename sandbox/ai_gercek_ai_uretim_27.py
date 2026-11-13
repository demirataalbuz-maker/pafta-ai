# -*- coding: utf-8 -*-
"""ai-uretim-27 gerçek deney: gerçek el yazısı rakamlarda (sklearn digits) sınıf koşullu küçük bir DDPM gürültü tahmincisi
eğitilir (etiket bırakmalı, CFG için). Öğrencinin ileri gürültü işlevi gerçek görüntülerde torch'a karşı sınanır;
örnekleme her adımda öğrencinin CFG + DDIM işleviyle yapılır. Üretilen rakamlar gerçek veride eğitilmiş bir
sınıflandırıcıyla puanlanır (CFG ölçeği ↔ doğruluk/çeşitlilik), eğitim verisinin ezberlenip ezberlenmediği en yakın
komşu mesafeleriyle ölçülür."""
import math
import ai_lab
from sandbox import ai_uretim_ortak as O

AYAR = {"T": 100, "adim": 4000, "batch": 256, "lr": 2e-3, "seed": 27, "ddim_adim": 25, "ornek_sinif": 10, "olcekler": [0.0, 1.0, 3.0, 6.0],
        "birakma": 0.15, "mia_t": [5, 15, 30, 50], "mia_kucuk": 100}


def rakam_verisi(torch, seed):
    try:
        from sklearn.datasets import load_digits
        from sklearn.linear_model import LogisticRegression
    except ImportError as e:
        raise ai_lab.GercekLabYok("scikit-learn kurulu değil") from e
    d = load_digits()
    X = torch.tensor(d.data, dtype=torch.float32) / 8.0 - 1.0            # [-1, 1]
    y = torch.tensor(d.target)
    perm = torch.randperm(X.shape[0], generator=torch.Generator().manual_seed(seed))
    egt, tst = perm[:1400], perm[1400:]
    sinif = LogisticRegression(max_iter=3000).fit(X[egt].numpy(), y[egt].numpy())
    return X, y, egt, tst, sinif


def _ag(torch):
    class Net(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.sinif = torch.nn.Embedding(11, 64)                        # 10 = koşulsuz (null) etiket
            self.zaman = torch.nn.Sequential(torch.nn.Linear(16, 64), torch.nn.SiLU())
            self.ana = torch.nn.Sequential(torch.nn.Linear(64 + 64 + 64, 256), torch.nn.SiLU(), torch.nn.Linear(256, 256), torch.nn.SiLU(), torch.nn.Linear(256, 64))

        def forward(self, x, t, c):
            f = torch.exp(-math.log(1000) * torch.arange(8, dtype=torch.float32) / 8)
            a = t.float()[:, None] * f[None]
            te = self.zaman(torch.cat([a.sin(), a.cos()], 1))
            return self.ana(torch.cat([x, te, self.sinif(c)], 1))
    return Net()


def _egit(torch, Xe, ye, abf, T):
    net = _ag(torch)
    opt = torch.optim.Adam(net.parameters(), lr=AYAR["lr"])
    for _ in range(AYAR["adim"]):
        idx = torch.randint(0, Xe.shape[0], (AYAR["batch"],))
        t = torch.randint(0, T, (AYAR["batch"],))
        eps = torch.randn(AYAR["batch"], 64)
        xt = abf[t].sqrt()[:, None] * Xe[idx] + (1 - abf[t]).sqrt()[:, None] * eps
        c = torch.where(torch.rand(AYAR["batch"]) < AYAR["birakma"], torch.full_like(ye[idx], 10), ye[idx])
        kayip = ((net(xt, t, c) - eps) ** 2).mean()
        opt.zero_grad(); kayip.backward(); opt.step()
    return net


def _gurultu_kaybi(torch, net, X, y, abf):
    """Her görüntü için sabit t ve ε kümesinde ortalama gürültü tahmin hatası (üyelik çıkarımı puanı: düşük = üye)."""
    g = torch.Generator().manual_seed(99)
    toplam = torch.zeros(X.shape[0])
    with torch.no_grad():
        for t in AYAR["mia_t"]:
            for _ in range(4):
                eps = torch.randn(X.shape, generator=g)
                tt = torch.full((X.shape[0],), t)
                xt = abf[t].sqrt() * X + (1 - abf[t]).sqrt() * eps
                toplam += ((net(xt, tt, y) - eps) ** 2).mean(1)
    return toplam / (4 * len(AYAR["mia_t"]))


def _auc(uye, disari):
    """Üyelerin kaybı dışarıdakilerden düşük olma olasılığı (Mann-Whitney)."""
    return float(((disari[None, :] > uye[:, None]).float() + 0.5 * (disari[None, :] == uye[:, None]).float()).mean())


def _uyelik(torch, net_tam, X, y, egt, tst, abf, T):
    n = AYAR["mia_kucuk"]
    torch.manual_seed(AYAR["seed"] + 1)
    net_k = _egit(torch, X[egt[:n]], y[egt[:n]], abf, T)
    sonuc = {}
    for ad, net, uye in (("tam_1400", net_tam, egt[:n]), (f"kucuk_{n}", net_k, egt[:n])):
        lu, ld = _gurultu_kaybi(torch, net, X[uye], y[uye], abf), _gurultu_kaybi(torch, net, X[tst[:n]], y[tst[:n]], abf)
        esik = float(ld.quantile(0.05))
        sonuc[ad] = {"auc": _auc(lu, ld), "uye_kayip_medyan": float(lu.median()), "disari_kayip_medyan": float(ld.median()),
                     "yuzde5_yanlis_alarmda_yakalanan_uye": float((lu < esik).float().mean())}
    return sonuc


def deney(ddpm_ileri_gurultu, cfg_ve_ddim_adimi):
    torch = O.torch_al()
    torch.manual_seed(AYAR["seed"])
    X, y, egt, tst, sinif = rakam_verisi(torch, AYAR["seed"])
    T = AYAR["T"]
    beta = torch.linspace(1e-4, 0.02 * 1000 / T, T, dtype=torch.float64)
    ab = torch.cumprod(1 - beta, 0)
    # 1) Öğrencinin ileri gürültü işlevi gerçek görüntülerde
    g = torch.Generator().manual_seed(1)
    ileri_fark = 0.0
    for i, t in zip(egt[:6].tolist(), (1, 10, 30, 50, 80, 100)):
        eps = torch.randn(64, generator=g, dtype=torch.float64)
        o = ddpm_ileri_gurultu(O.liste(X[i]), O.liste(beta), t, O.liste(eps))
        ref = ab[t - 1].sqrt() * X[i].double() + (1 - ab[t - 1]).sqrt() * eps
        ileri_fark = max(ileri_fark, O.goreli_fark(o["x_t"], O.liste(ref)), abs(o["alpha_bar_t"] - float(ab[t - 1])))
    # 2) Eğitim (torch, vektörleştirilmiş)
    net = _ag(torch)
    opt = torch.optim.Adam(net.parameters(), lr=AYAR["lr"])
    abf = ab.float()
    Xe, ye = X[egt], y[egt]
    for _ in range(AYAR["adim"]):
        idx = torch.randint(0, Xe.shape[0], (AYAR["batch"],))
        t = torch.randint(0, T, (AYAR["batch"],))
        eps = torch.randn(AYAR["batch"], 64)
        xt = abf[t].sqrt()[:, None] * Xe[idx] + (1 - abf[t]).sqrt()[:, None] * eps
        c = torch.where(torch.rand(AYAR["batch"]) < AYAR["birakma"], torch.full_like(ye[idx], 10), ye[idx])
        kayip = ((net(xt, t, c) - eps) ** 2).mean()
        opt.zero_grad(); kayip.backward(); opt.step()
    # 3) Örnekleme: her adım öğrencinin CFG + DDIM işleviyle
    adimlar = torch.linspace(T - 1, 0, AYAR["ddim_adim"]).round().long().tolist()
    sonuc, ddim_fark, tum_ornek = {}, 0.0, None
    for w in AYAR["olcekler"]:
        n = AYAR["ornek_sinif"] * 10
        hedef = torch.arange(10).repeat_interleave(AYAR["ornek_sinif"])
        x = torch.randn(n, 64, generator=torch.Generator().manual_seed(7), dtype=torch.float64)
        for j, t in enumerate(adimlar):
            tt = torch.full((n,), t)
            with torch.no_grad():
                e_k = net(x.float(), tt, torch.full((n,), 10)).double()
                e_c = net(x.float(), tt, hedef).double()
            abt = float(ab[t])
            abp = float(ab[adimlar[j + 1]]) if j + 1 < len(adimlar) else 1.0 - 1e-12
            yeni = []
            for i in range(n):
                o = cfg_ve_ddim_adimi(O.liste(x[i]), O.liste(e_k[i]), O.liste(e_c[i]), w, abt, abp)
                yeni.append(o["x_onceki"])
                if i == 0:
                    ec = e_k[i] + w * (e_c[i] - e_k[i])
                    x0 = (x[i] - math.sqrt(1 - abt) * ec) / math.sqrt(abt)
                    ddim_fark = max(ddim_fark, O.goreli_fark(o["x_onceki"], O.liste(math.sqrt(abp) * x0 + math.sqrt(1 - abp) * ec)))
            x = torch.tensor(yeni, dtype=torch.float64)
        doygun = float((x.abs() >= 1.0).double().mean())                   # [-1, 1] dışına taşan piksel oranı (aşırı CFG belirtisi)
        x = x.clamp(-1, 1).float()
        tahmin = torch.tensor(sinif.predict(x.numpy()))
        dog = float((tahmin == hedef).float().mean())
        cesit = float(torch.stack([torch.pdist(x[hedef == k]).mean() for k in range(10)]).mean())
        sonuc[str(w)] = {"sinif_dogrulugu": dog, "sinif_ici_cesitlilik": cesit, "tasan_piksel_orani": doygun}
        if w == 3.0:
            tum_ornek = x
    # 4) Ezberleme: üretilen örneklerin eğitim ve test kümesine en yakın mesafeleri
    d_egt = torch.cdist(tum_ornek, X[egt]).min(1).values
    d_tst = torch.cdist(tum_ornek, X[tst]).min(1).values
    gercek_egt = torch.cdist(X[tst], X[egt]).min(1).values                 # gerçek test görüntüsü → eğitim: doğal komşuluk
    kopya = int((d_egt < 0.25 * float(gercek_egt.median())).sum())
    dogs = [sonuc[str(w)]["sinif_dogrulugu"] for w in AYAR["olcekler"]]
    MIA = _uyelik(torch, net, X, y, egt, tst, abf, T)
    mt, mk = MIA["tam_1400"], MIA[f"kucuk_{AYAR['mia_kucuk']}"]
    return {
        "surumler": O.surumler("scikit-learn"), "veri": "sklearn load_digits", "T": T, "egitim_adim": AYAR["adim"],
        "sinif_test_dogrulugu": float(sinif.score(X[tst].numpy(), y[tst].numpy())),
        "ileri_fark": ileri_fark, "ileri_ayni": ileri_fark <= 1e-9, "ddim_fark": ddim_fark, "ddim_ayni": ddim_fark <= 1e-9,
        "cfg": sonuc, "cfg_dogrulugu_artirdi": dogs[1] > dogs[0] + 0.3 and dogs[2] >= dogs[1],
        "ezber_egitim_mesafe_medyan": float(d_egt.median()), "ezber_test_mesafe_medyan": float(d_tst.median()),
        "dogal_komsu_medyan": float(gercek_egt.median()), "neredeyse_kopya": kopya, "ornek": int(tum_ornek.shape[0]),
        "uyelik_cikarimi": MIA, "kucuk_kume_uyeligi_sizdiriyor": mk["auc"] > 0.8 and mk["auc"] > mt["auc"] + 0.1,
        "olcum": (f"Gerçek rakamlarda {AYAR['adim']} adım eğitilen koşullu DDPM (T={T}), {AYAR['ddim_adim']} adım DDIM, her adım öğrencinin işleviyle. "
                  f"Sınıflandırıcı (test doğruluğu {sinif.score(X[tst].numpy(), y[tst].numpy()):.2f}) ile koşullu doğruluk CFG w="
                  + ", ".join(f"{w}: {sonuc[str(w)]['sinif_dogrulugu']:.2f}" for w in AYAR["olcekler"]) +
                  f"; taşan piksel oranı " + ", ".join(f"{sonuc[str(w)]['tasan_piksel_orani']:.2f}" for w in AYAR["olcekler"]) +
                  f". Ezberleme: üretilenlerin eğitim kümesine medyan uzaklığı {float(d_egt.median()):.2f}, teste {float(d_tst.median()):.2f}; "
                  f"{kopya}/{tum_ornek.shape[0]} örnek bir eğitim görüntüsünün neredeyse kopyası. Üyelik çıkarımı (gürültü tahmin hatası, "
                  f"{AYAR['mia_kucuk']} üye / {AYAR['mia_kucuk']} dışarıdan): 1400 görüntüyle eğitilen modelde AUC {mt['auc']:.2f}, "
                  f"{AYAR['mia_kucuk']} görüntüyle eğitilen modelde {mk['auc']:.2f}; %5 yanlış alarmda yakalanan üye "
                  f"{mt['yuzde5_yanlis_alarmda_yakalanan_uye']:.2f} → {mk['yuzde5_yanlis_alarmda_yakalanan_uye']:.2f}."),
        "sinir": ("8×8 rakamlar ve küçük bir MLP gürültü tahmincisi kullanılır (U-Net, gerçek görüntü modeli ya da FID yoktur); kalite gerçek "
                  "veride eğitilmiş lojistik regresyonla ölçülür. Ezberleme ölçütü basit bir en yakın komşu eşiğidir. Üyelik çıkarımı beyaz "
                  "kutudur (saldırgan modelin gürültü tahminini sorgulayabilir); gerçek görüntü modellerinde de aynı kayıp tabanlı saldırı "
                  "çoğaltılmış eğitim görüntülerinde en güçlüdür."),
    }


def goster(ddpm_ileri_gurultu, cfg_ve_ddim_adimi):
    r = deney(ddpm_ileri_gurultu, cfg_ve_ddim_adimi)
    print("İleri gürültü farkı: %.1e | DDIM adımı farkı: %.1e" % (r["ileri_fark"], r["ddim_fark"]))
    for w, v in r["cfg"].items():
        print("  CFG w=%-4s sınıf doğruluğu %.2f | sınıf içi çeşitlilik %.2f | taşan piksel %.2f" % (w, v["sinif_dogrulugu"], v["sinif_ici_cesitlilik"], v["tasan_piksel_orani"]))
    print("Ezberleme: eğitime %.2f, teste %.2f, doğal komşu %.2f | neredeyse kopya %d/%d" % (r["ezber_egitim_mesafe_medyan"], r["ezber_test_mesafe_medyan"], r["dogal_komsu_medyan"], r["neredeyse_kopya"], r["ornek"]))
    print("Sınır:", r["sinir"])
    print("Kanıt:", O.kanit("ai-uretim-27", "run", r))
