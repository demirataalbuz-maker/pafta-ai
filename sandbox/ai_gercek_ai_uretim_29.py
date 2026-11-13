# -*- coding: utf-8 -*-
"""ai-uretim-29 gerçek deney: işletim sisteminin gerçek ses dosyaları (Windows: C:\\Windows\\Media\\*.wav, macOS:
/System/Library/Sounds) 16 kHz'e çevrilir. Eğitim dosyalarında kademeli k-means ile RVQ kod kitapları öğrenilir;
ayrılmış bir dosya öğrencinin RVQ işleviyle kodlanır ve kademe sayısına göre SNR / bit hızı ölçülür. Gerçek bir sesin
çerçeve enerjisi kullanıcı kanalı olarak öğrencinin full-duplex işlevine verilir; kısa bir gürültü patlamasıyla
yanlış söz kesme denenir."""
import glob, math, os, sys
import ai_lab
from sandbox import ai_uretim_ortak as O

AYAR = {"sr": 16000, "d": 16, "kademe": 8, "kod": 64, "kmeans_tur": 12, "egitim_cerceve": 40000, "test_cerceve": 400, "seed": 29,
        "enerji_cerceve_ms": 20, "esik_oran": 0.3, "filigran_oran": 0.05, "filigran_kademe": [1, 2, 4, 8]}


def ses_dosyalari():
    if sys.platform == "win32":
        d = sorted(glob.glob(os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Media", "*.wav")))
    elif sys.platform == "darwin":
        d = sorted(glob.glob("/System/Library/Sounds/*.aiff"))
    else:
        d = sorted(glob.glob("/usr/share/sounds/**/*.wav", recursive=True) + glob.glob("/usr/share/sounds/**/*.oga", recursive=True))
    if len(d) < 4:
        raise ai_lab.GercekLabYok("işletim sisteminde yeterli gerçek ses dosyası bulunamadı")
    return d


def oku(yol, sr):
    try:
        import av
        import numpy as np
    except ImportError as e:
        raise ai_lab.GercekLabYok("PyAV (av) kurulu değil") from e
    with av.open(yol) as f:
        r = av.AudioResampler(format="flt", layout="mono", rate=sr)
        parca = []
        for fr in f.decode(audio=0):
            for o in r.resample(fr):
                parca.append(o.to_ndarray().reshape(-1))
        for o in r.resample(None):
            parca.append(o.to_ndarray().reshape(-1))
    return np.concatenate(parca) if parca else np.zeros(0, dtype="float32")


def _filigran(torch, ses, kitaplar):
    """Yayılı spektrum filigranı (±1 sözde rastgele dizi, düşük genlik): RVQ kodekinden geçince tespit edilebiliyor mu?"""
    d = AYAR["d"]
    F = ses[: (ses.numel() // d) * d].view(-1, d)
    x = F[F.abs().max(1).values > 1e-3].reshape(-1)
    w = torch.randint(0, 2, x.shape, generator=torch.Generator().manual_seed(AYAR["seed"] + 1)).double() * 2 - 1
    alfa = AYAR["filigran_oran"] * float(x.pow(2).mean().sqrt())
    xw = x + alfa * w

    def z(y):                                                                   # filigransız seste ~N(0, 1)
        return float((y * w).sum() / (y.std() * math.sqrt(y.numel())))

    def kodek(y, k):
        r, cikti = y.view(-1, d).clone(), torch.zeros(y.numel() // d, d, dtype=y.dtype)
        for kk in kitaplar[:k]:
            q = kk[torch.cdist(r, kk).argmin(1)]
            cikti += q; r -= q
        return cikti.reshape(-1)
    sonuc = {"orneklem": int(x.numel()), "filigran_snr_db": round(10 * math.log10(float(x.pow(2).sum()) / (alfa ** 2 * x.numel())), 1),
             "z_filigransiz": z(x), "z_filigranli": z(xw), "kodek": {}}
    for k in AYAR["filigran_kademe"]:
        sonuc["kodek"][k] = {"z_filigranli": z(kodek(xw, k)), "z_filigransiz": z(kodek(x, k))}
    return sonuc


def deney(rvq_nicele, full_duplex_akis):
    torch = O.torch_al()
    dosyalar = ses_dosyalari()
    sesler = {os.path.basename(y): torch.tensor(oku(y, AYAR["sr"]), dtype=torch.float64) for y in dosyalar}
    adlar = sorted(sesler, key=lambda a: -sesler[a].numel())
    test_ad = adlar[1]
    egitim = torch.cat([sesler[a] for a in adlar if a != test_ad])
    d = AYAR["d"]
    C = egitim[: (egitim.numel() // d) * d].view(-1, d)
    C = C[C.abs().max(1).values > 1e-3]                                        # sessiz çerçeveler hariç
    g = torch.Generator().manual_seed(AYAR["seed"])
    C = C[torch.randperm(C.shape[0], generator=g)[: AYAR["egitim_cerceve"]]]
    # Kademeli (residual) k-means ile kod kitapları
    kitaplar, kalinti = [], C.clone()
    for _ in range(AYAR["kademe"]):
        m = kalinti[torch.randperm(kalinti.shape[0], generator=g)[: AYAR["kod"]]].clone()
        for _ in range(AYAR["kmeans_tur"]):
            a = torch.cdist(kalinti, m).argmin(1)
            for j in range(AYAR["kod"]):
                if (a == j).any():
                    m[j] = kalinti[a == j].mean(0)
        kitaplar.append(m)
        kalinti = kalinti - m[torch.cdist(kalinti, m).argmin(1)]
    # Ayrılmış dosya: öğrencinin RVQ'su
    T = sesler[test_ad]
    F = T[: (T.numel() // d) * d].view(-1, d)
    F = F[F.abs().max(1).values > 1e-3][: AYAR["test_cerceve"]]
    kl = [O.liste(k) for k in kitaplar]
    insa, idx_uyusmaz = [], 0
    kademe_hata = [0.0] * AYAR["kademe"]
    for f in F:
        o = rvq_nicele(O.liste(f), kl)
        insa.append(o["yeniden_insa"])
        r = f.clone()
        for s, k in enumerate(kitaplar):
            j = int(((r[None] - k) ** 2).sum(1).argmin())
            idx_uyusmaz += j != o["token_indisleri"][s]
            r = r - k[j]
            kademe_hata[s] += float((r ** 2).sum())
    insa = torch.tensor(insa, dtype=torch.float64)
    sinyal = float((F ** 2).sum())
    snr = [10 * math.log10(sinyal / max(h, 1e-12)) for h in kademe_hata]
    bit = math.log2(AYAR["kod"])
    kbps = [round((s + 1) * bit * AYAR["sr"] / d / 1000, 1) for s in range(AYAR["kademe"])]
    # Full-duplex: gerçek sesin çerçeve enerjisi kullanıcı kanalı
    n = AYAR["sr"] * AYAR["enerji_cerceve_ms"] // 1000
    kullanici = sesler[adlar[-3]]
    E = kullanici[: (kullanici.numel() // n) * n].view(-1, n).pow(2).mean(1).sqrt()
    E = (E / E.max()).tolist()
    sessiz = [0.0] * 25
    enerji = sessiz + E + sessiz
    model_ses = [0.5] * len(enerji)
    sonuc_fd = {}
    for ard in (2, 4):
        o = full_duplex_akis(list(enerji), list(model_ses), AYAR["esik_oran"], ard)
        sonuc_fd[ard] = {"soz_kesildi": o["soz_kesildi_mi"], "kesme_cercevesi": o["kesme_cercevesi"], "backchannel": o["backchannel_sayisi"]}
    patlama = [0.0] * 20 + [0.9, 0.9] + [0.0] * 20                             # 40 ms'lik tık/gürültü patlaması
    yanlis = {ard: full_duplex_akis(list(patlama), [0.5] * len(patlama), AYAR["esik_oran"], ard)["soz_kesildi_mi"] for ard in (2, 4)}
    beklenen_kesme = next((t for t in range(3, len(enerji)) if all(e >= AYAR["esik_oran"] for e in enerji[t - 3:t + 1])), None)
    FG = _filigran(torch, sesler[test_ad], kitaplar)
    return {
        "surumler": O.surumler("av"), "platform": sys.platform, "dosya_sayisi": len(dosyalar), "test_dosyasi": test_ad,
        "egitim_cerceve": int(C.shape[0]), "test_cerceve": int(F.shape[0]), "kademe_snr_db": [round(x, 2) for x in snr], "kademe_kbps": kbps,
        "indis_uyusmaz": idx_uyusmaz, "rvq_ayni": idx_uyusmaz == 0, "snr_artiyor": all(b > a for a, b in zip(snr, snr[1:])),
        "full_duplex": sonuc_fd, "kullanici_sesi": adlar[-3], "tik_yanlis_kesme": yanlis,
        "kesme_dogru": sonuc_fd[4]["kesme_cercevesi"] == beklenen_kesme, "tik_korumasi": yanlis[2] and not yanlis[4],
        "filigran": FG,
        "filigran_dusuk_bitte_kayboluyor": (FG["z_filigranli"] > 8 and abs(FG["z_filigransiz"]) < 3
                                            and FG["kodek"][AYAR["filigran_kademe"][0]]["z_filigranli"] < 4 < FG["kodek"][AYAR["filigran_kademe"][-1]]["z_filigranli"]
                                            and all(abs(v["z_filigransiz"]) < 3 for v in FG["kodek"].values())),
        "olcum": (f"{len(dosyalar)} gerçek sistem sesi, 16 kHz. {AYAR['kademe']} kademe × {AYAR['kod']} kodluk RVQ, {d} örneklik çerçeveler; "
                  f"ayrılmış '{test_ad}' dosyasında SNR (dB) kademe başına {', '.join(f'{x:.1f}' for x in snr)} "
                  f"({kbps[0]}–{kbps[-1]} kbps). Öğrencinin indisleri referansla {'aynı' if idx_uyusmaz == 0 else f'{idx_uyusmaz} kez farklı'}. "
                  f"Gerçek ses enerjisiyle söz kesme (4 çerçeve) {sonuc_fd[4]['kesme_cercevesi']}. çerçevede; 40 ms'lik tık "
                  f"2 çerçeve eşiğinde söz kesiyor: {yanlis[2]}, 4 çerçevede: {yanlis[4]}. Filigran (SNR {FG['filigran_snr_db']} dB, "
                  f"{FG['orneklem']} örnek): tespit z'si filigransız {FG['z_filigransiz']:.1f}, filigranlı {FG['z_filigranli']:.1f}; RVQ kodekinden "
                  "sonra kademe başına " + ", ".join(f"{k}: {v['z_filigranli']:.1f}" for k, v in FG["kodek"].items()) + "."),
        "sinir": ("Kod kitapları ham dalga biçimi çerçevelerinde k-means ile öğrenilir; gerçek ses kodekleri (EnCodec, Mimi) öğrenilmiş bir "
                  "kodlayıcının gizli uzayında çalışır ve algısal kayıp kullanır. Ses dosyaları işletim sisteminin bildirim sesleridir, konuşma "
                  "değildir; söz kesme yalnız enerjiye bakar (VAD modeli yoktur). Filigran basit bir yayılı spektrum filigranıdır; "
                  "AudioSeal gibi öğrenilmiş filigranlar kodeklere karşı eğitilir ve daha dayanıklıdır."),
    }


def goster(rvq_nicele, full_duplex_akis):
    r = deney(rvq_nicele, full_duplex_akis)
    print("Ses: %d dosya (%s), test '%s'" % (r["dosya_sayisi"], r["platform"], r["test_dosyasi"]))
    for s, (snr, kb) in enumerate(zip(r["kademe_snr_db"], r["kademe_kbps"]), 1):
        print("  %d kademe: SNR %6.2f dB | %5.1f kbps" % (s, snr, kb))
    print("RVQ indisleri referansla aynı:", r["rvq_ayni"])
    print("Söz kesme:", r["full_duplex"], "| tık ile yanlış kesme:", r["tik_yanlis_kesme"])
    print("Sınır:", r["sinir"])
    print("Kanıt:", O.kanit("ai-uretim-29", "run", r))
