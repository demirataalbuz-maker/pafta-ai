# -*- coding: utf-8 -*-
"""ai-uretim-08 gerçek deney: dört veri paralel "rank"ın SmolLM2 RMSNorm ağırlıkları üzerindeki gerçek gradyanları
dört ayrı süreçte torch.distributed (gloo) all_reduce ile toplanır ve öğrencinin ring all-reduce simülasyonuyla
karşılaştırılır; tek bir bozuk/kötü niyetli rank'ın tüm rank'ları zehirlediği gösterilir. ZeRO bellek formülü
SmolLM2'nin gerçek parametre sayısı ve torch AdamW'nin gerçek durum tensörleriyle ölçülen bayt/parametre ile sınanır."""
import os, subprocess, sys, tempfile
import ai_lab
from sandbox import ai_uretim_ortak as O

AYAR = {"dunya": 4, "kotu_rank": 3, "kotu_carpan": -20.0, "zero_gpu": 8,
        "metinler": ["The storage cluster finished its weekly integrity scan without errors.",
                     "Students waited outside the lab while the instructor prepared the samples.",
                     "A light rain fell on the harbor as the ferry left for the island.",
                     "The new compiler release improves startup time and reduces binary size."]}


def _gradlar(torch, tok, model):
    adlar = [n for n, p in model.named_parameters() if n.endswith("norm.weight")]
    params = dict(model.named_parameters())
    out = []
    for metin in AYAR["metinler"]:
        ids = tok(metin, return_tensors="pt").input_ids
        girdiler = {a: params[a].detach().clone().requires_grad_(True) for a in adlar}
        kayip = torch.func.functional_call(model, girdiler, (ids,), {"labels": ids}).loss
        g = torch.autograd.grad(kayip, [girdiler[a] for a in adlar])
        out.append(torch.cat([x.reshape(-1) for x in g]).double())
    return adlar, out


def _gloo(torch, gradlar):
    n = len(gradlar)
    with tempfile.TemporaryDirectory() as d:
        giris = os.path.join(d, "giris.pt")
        torch.save(gradlar, giris)
        isci = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_uretim_08_isci.py")
        surecler = [subprocess.Popen([sys.executable, "-I", isci, str(r), str(n), os.path.join(d, "depo"), giris, os.path.join(d, f"cikis{r}.pt")],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE) for r in range(n)]
        hatalar = []
        for p in surecler:
            try:
                _, err = p.communicate(timeout=120)
            except subprocess.TimeoutExpired:
                p.kill(); hatalar.append("zaman aşımı"); continue
            if p.returncode:
                hatalar.append(err.decode("utf-8", "replace")[-300:])
        if hatalar:
            raise ai_lab.GercekLabYok("gloo süreçleri başarısız: " + " | ".join(hatalar))
        return [torch.load(os.path.join(d, f"cikis{r}.pt")) for r in range(n)]


def deney(ring_allreduce, dagitik_bellek_ve_balon):
    torch = O.torch_al()
    import torch.distributed as dist
    if not dist.is_available() or not dist.is_gloo_available():
        raise ai_lab.GercekLabYok("torch.distributed gloo yok")
    tok, model, bilgi = O.smol()
    adlar, gradlar = _gradlar(torch, tok, model)
    phi = gradlar[0].numel()
    sonuclar = _gloo(torch, gradlar)
    gloo_toplam = sonuclar[0]["toplam"]
    ranklar_ayni = all(torch.equal(s["toplam"], gloo_toplam) for s in sonuclar)
    o = ring_allreduce([O.liste(g) for g in gradlar])
    ogr = torch.tensor(o["senkronize_vektor"], dtype=torch.float64)
    ring_fark = float((ogr - gloo_toplam).abs().max())
    parca_dogru = [x for p in o["parca_toplamlari"] for x in p] == o["senkronize_vektor"][: o["parca_boyutu"] * AYAR["dunya"]]

    # Kötü niyetli / bozuk rank: kendi gradyanını -20 ile çarparak gönderir; all-reduce bütünlük denetimi yapmaz
    kotu = [g.clone() for g in gradlar]
    kotu[AYAR["kotu_rank"]] = kotu[AYAR["kotu_rank"]] * AYAR["kotu_carpan"]
    o2 = ring_allreduce([O.liste(g) for g in kotu])
    temiz = gloo_toplam / AYAR["dunya"]
    zehirli = torch.tensor(o2["senkronize_vektor"], dtype=torch.float64) / AYAR["dunya"]
    kos = float(torch.nn.functional.cosine_similarity(temiz, zehirli, dim=0))
    medyan = torch.stack(kotu).median(dim=0).values
    kos_medyan = float(torch.nn.functional.cosine_similarity(temiz, medyan, dim=0))
    # Savunma: rank gradyan normlarından medyanın 3 katını aşanı dışla, kalanların ortalamasını al (norm filtresi)
    normlar = [float(g.norm()) for g in kotu]
    esik = 3 * sorted(normlar)[len(normlar) // 2]
    supheli = [i for i, n_ in enumerate(normlar) if n_ > esik]
    kalan = [g for i, g in enumerate(kotu) if i not in supheli]
    filtreli = torch.stack(kalan).mean(0)
    kos_filtre = float(torch.nn.functional.cosine_similarity(temiz, filtreli, dim=0))
    # Normu korunarak yönü ters çevrilmiş saldırı norm filtresinden kaçar
    sinsi = [g.clone() for g in gradlar]
    sinsi[AYAR["kotu_rank"]] = -sinsi[AYAR["kotu_rank"]] * (sum(float(g.norm()) for g in gradlar) / len(gradlar) / float(sinsi[AYAR["kotu_rank"]].norm()))
    sn = [float(g.norm()) for g in sinsi]
    sinsi_yakalandi = any(n_ > 3 * sorted(sn)[len(sn) // 2] for n_ in sn)
    kos_sinsi = float(torch.nn.functional.cosine_similarity(temiz, torch.stack(sinsi).mean(0), dim=0))

    # ZeRO: gerçek parametre sayısı ve gerçek AdamW durum tensörlerinden bayt/parametre
    toplam_param = sum(p.numel() for p in model.parameters())
    katman = [p.detach().clone().requires_grad_(True) for p in model.model.layers[0].parameters()]
    for p in katman:
        p.grad = torch.zeros_like(p)
    opt_durum = torch.optim.AdamW(katman, lr=1e-3)
    opt_durum.step()
    bayt = sum(p.numel() * p.element_size() * 2 for p in katman)                    # parametre + gradyan
    bayt += sum(t.numel() * t.element_size() for p in katman for k, t in opt_durum.state[p].items() if k != "step")
    bayt_param = bayt / sum(p.numel() for p in katman)
    zero = {a: dagitik_bellek_ve_balon(toplam_param / 1e9, AYAR["zero_gpu"], a, 4, 16) for a in (0, 1, 2, 3)}
    olculen_gb = bayt_param * toplam_param / 1e9
    return {
        "model": {k2: bilgi[k2] for k2 in ("model", "revizyon", "agirlik_sha256", "parametre")}, "surumler": O.surumler(),
        "backend": sonuclar[0]["backend"], "dunya": AYAR["dunya"], "parametre_adlari": len(adlar), "vektor_boyu": phi,
        "gloo_ranklar_ayni": ranklar_ayni, "ring_gloo_en_buyuk_fark": ring_fark, "ring_ayni": ring_fark <= 1e-5 and parca_dogru,
        "gpu_basi_gonderilen_ring": o["gpu_basi_gonderilen_eleman"], "rank0_toplanan_naif": (AYAR["dunya"] - 1) * phi,
        "kotu_rank_kosinus": kos, "medyan_kosinus": kos_medyan, "zehir_yayildi": kos < 0,
        "rank_normlari": normlar, "supheli_ranklar": supheli, "norm_filtresi_kosinus": kos_filtre,
        "norm_filtresi_yakaladi": supheli == [AYAR["kotu_rank"]] and kos_filtre > 0.7,
        "sinsi_saldiri_kacti": not sinsi_yakalandi, "sinsi_kosinus": kos_sinsi,
        "adamw_bayt_parametre": bayt_param, "toplam_parametre": toplam_param, "olculen_ddp_gb": olculen_gb,
        "zero_gpu_basi_gb": {a: zero[a]["gpu_basi_bellek_gb"] for a in zero}, "ddp_formul_gb": zero[0]["ddp_bellek_gb"],
        "zero_formul_dogru": abs(zero[0]["ddp_bellek_gb"] - olculen_gb) <= 1e-3,
        "olcum": (f"{AYAR['dunya']} gloo sürecinde SmolLM2'nin {len(adlar)} RMSNorm ağırlığının gerçek gradyanları ({phi} eleman) all_reduce "
                  f"edildi; öğrencinin ring sonucu gloo'dan en çok {ring_fark:.1e} farklı. Ring'de rank başına {o['gpu_basi_gonderilen_eleman']} "
                  f"eleman gönderilir (naif rank 0 toplama: {(AYAR['dunya'] - 1) * phi}). Tek rank -20× gönderince ortalama gradyanın temiz "
                  f"gradyanla kosinüsü {kos:.2f} (medyanla {kos_medyan:.2f}); norm filtresi rank {supheli} dışlayınca {kos_filtre:.2f}, ama normu "
                  f"korunmuş ters gradyan filtreden kaçıyor (kosinüs {kos_sinsi:.2f}). AdamW fp32 gerçek durum {bayt_param:.1f} bayt/parametre; "
                  f"{toplam_param} parametre için {olculen_gb:.3f} GB, formül {zero[0]['ddp_bellek_gb']} GB."),
        "sinir": ("Dört rank tek makinede CPU süreçleridir (gloo); NCCL, gerçek ağ gecikmesi ve bant genişliği ölçülmez. ZeRO formülü "
                  "aktivasyon ve tampon belleğini içermez; 1F1B bubble oranı ölçülmez, yalnız formülle hesaplanır."),
    }


def goster(ring_allreduce, dagitik_bellek_ve_balon):
    r = deney(ring_allreduce, dagitik_bellek_ve_balon)
    print("gloo (%d süreç) ile ring simülasyonu en büyük fark: %.2e | tüm rank'lar aynı sonucu aldı: %s" % (r["dunya"], r["ring_gloo_en_buyuk_fark"], r["gloo_ranklar_ayni"]))
    print("Rank başına gönderilen eleman  ring: %d | naif toplama: %d" % (r["gpu_basi_gonderilen_ring"], r["rank0_toplanan_naif"]))
    print("Kötü rank sonrası kosinüs (ortalama): %.2f | medyan: %.2f | norm filtresi: %.2f (şüpheli %s)" % (r["kotu_rank_kosinus"], r["medyan_kosinus"], r["norm_filtresi_kosinus"], r["supheli_ranklar"]))
    print("Normu korunmuş ters gradyan: filtreden kaçtı %s, kosinüs %.2f" % (r["sinsi_saldiri_kacti"], r["sinsi_kosinus"]))
    print("AdamW gerçek bayt/parametre: %.1f | ölçülen %.3f GB | formül %.3f GB | ZeRO-0..3 GPU başı:" % (r["adamw_bayt_parametre"], r["olculen_ddp_gb"], r["ddp_formul_gb"]), r["zero_gpu_basi_gb"])
    print("Sınır:", r["sinir"])
    print("Kanıt:", O.kanit("ai-uretim-08", "run", r))
