# -*- coding: utf-8 -*-
"""ai-uretim-15 gerçek deney: bu makinenin gerçek tepe hesap gücü (büyük matmul) ve bellek bant genişliği (kopya) ölçülür;
öğrencinin roofline analizi dört gerçek işlem (vektör toplama, satır softmax, GEMV, büyük matmul) için ölçülen
sürelerle karşılaştırılır. Öğrencinin SPMD fused softmax'ı SmolLM2'nin gerçek dikkat skorlarında torch.softmax ile
sınanır; tek çekirdekli (fused) softmax ile beş ayrı işlemden oluşan softmax'ın süresi ölçülür."""
import time
import ai_lab
from sandbox import ai_uretim_ortak as O

AYAR = {"tekrar": 5, "metin": "The operator rotated the encryption keys and restarted the gateway before the audit began."}


def _sure(torch, cihaz, fn):
    fn()
    if cihaz == "cuda":
        torch.cuda.synchronize()
    en = float("inf")
    for _ in range(AYAR["tekrar"]):
        t0 = time.perf_counter()
        fn()
        if cihaz == "cuda":
            torch.cuda.synchronize()
        en = min(en, time.perf_counter() - t0)
    return en


def _kalinti_bellek(torch, cihaz):
    """Başlatılmamış bellek: serbest bırakılan bir tampondaki 'gizli' veri, aynı süreçte torch.empty ile geri okunabilir mi?"""
    n = 1 << 22
    desen = (torch.arange(n) % 251).float() + 0.5                    # CPU'da üretilir: cihazda ara tampon kalmaz
    if cihaz == "cuda":
        torch.cuda.synchronize(); torch.cuda.empty_cache()
    gizli = desen.to(cihaz)                                          # cihazda tek ayırma
    adres = gizli.data_ptr()
    gizli = None                                                     # serbest bırak (önbellekli ayırıcıya döner)
    yeni = torch.empty(n, device=cihaz)
    ayni_adres = yeni.data_ptr() == adres
    oran = float((yeni.cpu() == desen).float().mean())
    yeni = None
    sifir = torch.zeros(n, device=cihaz)
    oran_sifir = float((sifir.cpu() == desen).float().mean())
    return {"tampon_mb": n * 4 / 2 ** 20, "ayni_adres": ayni_adres, "empty_geri_okunan_oran": oran, "zeros_geri_okunan_oran": oran_sifir}


def deney(roofline_analiz, spmd_fused_softmax):
    torch = O.torch_al()
    cihaz = ai_lab.torch_cihazi()
    kilit = ai_lab.gpu_kilidi_al() if cihaz == "cuda" else None
    try:
        gpu = torch.cuda.get_device_name(0) if cihaz == "cuda" else None
        torch.backends.cuda.matmul.allow_tf32 = False
        N = (1 << 26) if cihaz == "cuda" else (1 << 24)
        n_mm = 4096 if cihaz == "cuda" else 1536
        x = torch.rand(N, device=cihaz)
        y = torch.empty_like(x)
        t_kopya = _sure(torch, cihaz, lambda: y.copy_(x))
        bant_gb = 2 * N * 4 / t_kopya / 1e9
        A = torch.rand(n_mm, n_mm, device=cihaz)
        B = torch.rand(n_mm, n_mm, device=cihaz)
        t_mm = _sure(torch, cihaz, lambda: A @ B)
        tepe_tf = 2 * n_mm ** 3 / t_mm / 1e12

        islemler = {}
        z = torch.empty_like(x)
        islemler["vektor_toplama"] = (N, 3 * N * 4, _sure(torch, cihaz, lambda: torch.add(x, y, out=z)))
        S = x[: (N // 4096) * 4096].view(-1, 4096)
        islemler["satir_softmax"] = (5 * S.numel(), 2 * S.numel() * 4, _sure(torch, cihaz, lambda: torch.softmax(S, 1)))
        m = 8192 if cihaz == "cuda" else 4096
        M = torch.rand(m, m, device=cihaz)
        v = torch.rand(m, device=cihaz)
        islemler["gemv"] = (2 * m * m, (m * m + 2 * m) * 4, _sure(torch, cihaz, lambda: M @ v))
        islemler["matmul"] = (2 * n_mm ** 3, 3 * n_mm * n_mm * 4, t_mm)
        tablo, siniflama_dogru, bellek_tahmin_orani = {}, True, []
        for ad, (flop, bayt, t) in islemler.items():
            o = roofline_analiz(flop, bayt, tepe_tf, bant_gb)
            olculen = flop / t / 1e12
            tablo[ad] = {"flop": flop, "bayt": bayt, "sure_ms": round(t * 1e3, 4), "yogunluk": o["aritmetik_yogunluk"], "darbogaz": o["darbogaz"],
                         "tahmin_tflops": o["etkin_tflops"], "olculen_tflops": round(olculen, 5),
                         "olculen_bant_gb_sn": round(bayt / t / 1e9, 2)}
            if ad in ("vektor_toplama", "satir_softmax", "gemv"):
                siniflama_dogru = siniflama_dogru and o["darbogaz"] == "memory-bound"
                bellek_tahmin_orani.append(olculen / o["etkin_tflops"] if o["etkin_tflops"] else 0.0)
            else:
                siniflama_dogru = siniflama_dogru and o["darbogaz"] == "compute-bound"
        kritik = roofline_analiz(1, 1, tepe_tf, bant_gb)["kritik_yogunluk"]

        # Fused softmax: gerçek dikkat skorları (CPU, float64) ve cihazda fused / ayrık süre
        tok, model, bilgi = O.smol()
        ids = tok(AYAR["metin"], return_tensors="pt").input_ids
        if ids.shape[1] & (ids.shape[1] - 1) == 0:                  # sütun sayısı 2'nin kuvveti olmasın: dolgu maskesi sınansın
            ids = ids[:, :-1]
        with torch.no_grad():
            sk = model(ids, output_attentions=False, output_hidden_states=True)
            L = model.model.layers[2]
            h = L.input_layernorm(sk.hidden_states[2])
            T = ids.shape[1]
            q = L.self_attn.q_proj(h).view(1, T, 9, 64).transpose(1, 2)[0, 0]
            k = L.self_attn.k_proj(h).view(1, T, 3, 64).transpose(1, 2)[0, 0]
            skor = (q @ k.T / 8.0).double()
        o = spmd_fused_softmax(O.liste(skor))
        sm_fark = O.en_buyuk_fark(o["cikti"], O.liste(torch.softmax(skor, 1)))

        def ayrik():
            mx = S.max(1, keepdim=True).values
            e = torch.exp(S - mx)
            return e / e.sum(1, keepdim=True)
        t_ayrik = _sure(torch, cihaz, ayrik)
        t_fused = islemler["satir_softmax"][2]
        x = y = z = S = M = v = A_ = B_ = None
        kalinti = _kalinti_bellek(torch, cihaz)
    finally:
        if kilit is not None:
            ai_lab.gpu_kilidi_birak()
    return {
        "model": {k2: bilgi[k2] for k2 in ("model", "revizyon", "agirlik_sha256", "parametre")}, "surumler": O.surumler(),
        "cihaz": cihaz, "gpu": gpu, "tepe_tflops_olculen": tepe_tf, "bant_gb_sn_olculen": bant_gb, "kritik_yogunluk": kritik,
        "islemler": tablo, "siniflama_dogru": siniflama_dogru, "bellek_bound_olculen_tahmin_orani": bellek_tahmin_orani,
        "tahmin_tutarli": all(0.25 <= r <= 2.0 for r in bellek_tahmin_orani),
        "softmax_token": T, "block_size": o["block_size"], "dolgu": o["maskeli_dolgu_sayisi"], "softmax_en_buyuk_fark": sm_fark,
        "softmax_ayni": sm_fark <= 1e-6 and o["block_size"] >= T and o["maskeli_dolgu_sayisi"] == o["block_size"] - T > 0,
        "fused_ms": t_fused * 1e3, "ayrik_ms": t_ayrik * 1e3, "fused_hizlanma": t_ayrik / t_fused,
        "kalinti_bellek": kalinti, "zeros_temiz": kalinti["zeros_geri_okunan_oran"] == 0.0,
        "empty_sizdiriyor": kalinti["empty_geri_okunan_oran"] > 0.9 if cihaz == "cuda" else None,
        "olcum": (f"{gpu or 'CPU'}: ölçülen tepe {tepe_tf:.2f} TFLOPS (fp32 matmul {n_mm}), bant {bant_gb:.0f} GB/s, kritik yoğunluk "
                  f"{kritik:.1f} FLOP/bayt. Vektör toplama, softmax ve GEMV memory-bound, matmul compute-bound sınıflandı; memory-bound "
                  f"işlemlerde ölçülen/tahmin oranı {', '.join(f'{r:.2f}' for r in bellek_tahmin_orani)}. Gerçek dikkat skorlarında ({T} sütun, "
                  f"blok {o['block_size']}) softmax farkı {sm_fark:.1e}. Fused softmax {t_fused * 1e3:.2f} ms, ayrık {t_ayrik * 1e3:.2f} ms "
                  f"({t_ayrik / t_fused:.1f}×). Kalıntı bellek: serbest bırakılan {kalinti['tampon_mb']:.0f} MB'lık tampondaki desenin "
                  f"%{100 * kalinti['empty_geri_okunan_oran']:.1f}'i torch.empty ile geri okundu (aynı adres: {kalinti['ayni_adres']}); torch.zeros ile "
                  f"%{100 * kalinti['zeros_geri_okunan_oran']:.0f}."),
        "sinir": ("Tepe değerler bu makinede ölçülen en iyi değerlerdir (üretici tepe değeri değil); TF32/Tensor Core kapalıdır. Bayt sayıları "
                  "önbellek etkisini hesaba katmayan ideal değerlerdir. Triton çekirdeği yazılmaz; fused/ayrık karşılaştırması torch'un hazır "
                  "çekirdekleriyle yapılır."),
    }


def goster(roofline_analiz, spmd_fused_softmax):
    r = deney(roofline_analiz, spmd_fused_softmax)
    print("Cihaz: %s | tepe %.2f TFLOPS | bant %.0f GB/s | kritik yoğunluk %.1f" % (r["gpu"] or r["cihaz"], r["tepe_tflops_olculen"], r["bant_gb_sn_olculen"], r["kritik_yogunluk"]))
    print("işlem            yoğunluk   darboğaz        tahmin TF   ölçülen TF")
    for ad, t in r["islemler"].items():
        print("%-15s  %8.3f   %-14s  %9.4f   %9.4f" % (ad, t["yogunluk"], t["darbogaz"], t["tahmin_tflops"], t["olculen_tflops"]))
    print("Gerçek dikkat skorlarında softmax farkı: %.1e | blok %d, dolgu %d" % (r["softmax_en_buyuk_fark"], r["block_size"], r["dolgu"]))
    print("Fused %.2f ms | ayrık %.2f ms | %.1f×" % (r["fused_ms"], r["ayrik_ms"], r["fused_hizlanma"]))
    print("Kalıntı bellek:", r["kalinti_bellek"])
    print("Sınır:", r["sinir"])
    print("Kanıt:", O.kanit("ai-uretim-15", "run", r))
