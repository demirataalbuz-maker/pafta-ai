# -*- coding: utf-8 -*-
"""ai-temel-33 gerçek deney: SmolLM2'nin gerçek bir MLP'si Megatron tarzı tensör paralellikle dört parçaya bölünür
(gate/up sütun, down satır paralel); her parçanın kısmi çıktısı ayrı bir süreçte tutulur ve gerçek torch.distributed
(gloo) all_reduce ile toplanır; sonuç modelin kendi MLP çıktısıyla karşılaştırılır. Öğrencinin tensör paralel matmul'ü
gerçek ağırlık blokları üzerinde, rank haritası SmolLM2'nin gerçek katman ve parametre sayısıyla sınanır."""
import time
import ai_lab
from sandbox import ai_uretim_ortak as O
from sandbox.ai_gercek_ai_uretim_08 import _gloo

AYAR = {"katman": 4, "tp": 4, "metin": "The scheduler moved the failed job to another node and retried it twice before alerting the team.",
        "yerlesim": {"gpu": 8, "tp": 2, "pp": 2, "dp": 2}}


def _tcpstore(dist):
    """torchrun'ın buluşma noktası TCPStore'dur ve kimlik doğrulaması yoktur: aynı ağdaki herhangi bir süreç anahtar okuyup yazabilir."""
    import datetime, socket
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    sure = datetime.timedelta(seconds=10)
    kw = {}
    try:
        ana = dist.TCPStore("127.0.0.1", port, 2, True, timeout=sure, wait_for_workers=False)
    except Exception:  # noqa: BLE001 - libuv'suz derlemeler
        kw = {"use_libuv": False}
        ana = dist.TCPStore("127.0.0.1", port, 2, True, timeout=sure, wait_for_workers=False, **kw)
    ana.set("egitim/ayar", "lr=3e-4")
    ana.set("kanarya/anahtar", "PAFTA-KANARYA-7731")
    davetsiz = dist.TCPStore("127.0.0.1", port, 2, False, timeout=sure, **kw)          # parola, sertifika ya da belirteç yok
    okunan = davetsiz.get("kanarya/anahtar").decode()
    davetsiz.set("egitim/ayar", "lr=1.0")
    sonra = ana.get("egitim/ayar").decode()
    return {"port": port, "davetsiz_okudu": okunan == "PAFTA-KANARYA-7731", "davetsiz_yazdi": sonra == "lr=1.0", "ayar_sonra": sonra}


def _flash(torch):
    """Naif dikkat T×T skor matrisini bellekte tutar; SDPA (FlashAttention / bellek verimli çekirdek) tutmaz."""
    cihaz = ai_lab.torch_cihazi()
    kilit = ai_lab.gpu_kilidi_al() if cihaz == "cuda" else None
    H, D = 8, 64
    uzunluklar = [1024, 2048, 4096] if cihaz == "cuda" else [512, 1024, 2048]
    dt = torch.float16 if cihaz == "cuda" else torch.float32
    out = {}
    try:
        for T in uzunluklar:
            g = torch.Generator(device=cihaz).manual_seed(T)
            q, k, v = (torch.randn(1, H, T, D, generator=g, device=cihaz, dtype=dt) for _ in range(3))
            sonuc = {}
            for ad in ("naif", "sdpa"):
                if cihaz == "cuda":
                    torch.cuda.synchronize(); torch.cuda.empty_cache(); torch.cuda.reset_peak_memory_stats()
                    taban = torch.cuda.memory_allocated()
                t0 = time.perf_counter()
                with torch.no_grad():
                    if ad == "naif":
                        S = (q @ k.transpose(-1, -2)) / D ** 0.5
                        S = S.masked_fill(torch.ones(T, T, dtype=torch.bool, device=cihaz).triu(1), float("-inf"))
                        o = torch.softmax(S.float(), -1).to(dt) @ v
                        S = None
                    else:
                        o = torch.nn.functional.scaled_dot_product_attention(q, k, v, is_causal=True)
                if cihaz == "cuda":
                    torch.cuda.synchronize()
                sonuc[ad] = {"sure_ms": round(1000 * (time.perf_counter() - t0), 2), "cikti": o,
                             "ek_bellek_mb": round((torch.cuda.max_memory_allocated() - taban) / 2 ** 20, 1) if cihaz == "cuda" else None}
            fark = float((sonuc["naif"].pop("cikti").float() - sonuc["sdpa"].pop("cikti").float()).abs().max())
            out[T] = {**{a: b for a, b in sonuc.items()}, "en_buyuk_fark": fark, "skor_matrisi_mb": round(H * T * T * 4 / 2 ** 20, 1)}
        if cihaz == "cuda":
            torch.cuda.empty_cache()
    finally:
        if kilit is not None:
            ai_lab.gpu_kilidi_birak()
    return {"cihaz": cihaz, "dtype": str(dt), "uzunluk": out}


def _pipeline(torch, model, ids):
    """Ölçülen aşama süreleriyle GPipe zamanlaması: p aşama, m mikro-batch; bubble = boşta geçen aşama-zamanı oranı."""
    katmanlar, p = model.model.layers, 4
    sinir = [0, 8, 16, 23, 30]
    with torch.no_grad():
        h = model.model.embed_tokens(ids)
        pos = model.model.rotary_emb(h, torch.arange(ids.shape[1]).unsqueeze(0))
        sureler = []
        for a in range(p):
            for _ in range(2):                                                 # ısınma + ölçüm
                t0 = time.perf_counter()
                x = h
                for L in katmanlar[sinir[a]:sinir[a + 1]]:
                    x = L(x, position_embeddings=pos)
                    x = x[0] if isinstance(x, tuple) else x
                t = time.perf_counter() - t0
            sureler.append(t)
            h = x
    tablo = {}
    for m in (1, 4, 16, 64):
        bitis = [[0.0] * m for _ in range(p)]                                  # bitis[a][j]: aşama a, mikro-batch j
        for j in range(m):
            for a in range(p):
                bas = max(bitis[a][j - 1] if j else 0.0, bitis[a - 1][j] if a else 0.0)
                bitis[a][j] = bas + sureler[a]
        toplam = bitis[-1][-1]
        bubble = 1 - m * sum(sureler) / (p * toplam)
        tablo[m] = {"sure_s": round(toplam, 4), "bubble": round(bubble, 4), "formul": round((p - 1) / (m + p - 1), 4)}
    return {"asama_katman": [sinir[a + 1] - sinir[a] for a in range(p)], "asama_sure_ms": [round(1000 * s, 2) for s in sureler], "tablo": tablo}


def deney(paralel_yerlesim, tp_matmul):
    torch = O.torch_al()
    import torch.distributed as dist
    if not dist.is_available() or not dist.is_gloo_available():
        raise ai_lab.GercekLabYok("torch.distributed gloo yok")
    tok, model, bilgi = O.smol()
    ids = tok(AYAR["metin"], return_tensors="pt").input_ids
    L = model.model.layers[AYAR["katman"]]
    with torch.no_grad():
        h = model(ids, output_hidden_states=True).hidden_states[AYAR["katman"]]
        x = L.post_attention_layernorm(h + L.self_attn(L.input_layernorm(h), position_embeddings=model.model.rotary_emb(h, torch.arange(ids.shape[1]).unsqueeze(0)))[0])[0].double()
        tam = L.mlp(x.float()[None])[0].double()
    Wg, Wu, Wd = (getattr(L.mlp, a).weight.detach().double() for a in ("gate_proj", "up_proj", "down_proj"))
    ff, tp = Wg.shape[0], AYAR["tp"]
    b = ff // tp
    kismi = []
    for k in range(tp):
        s = slice(k * b, (k + 1) * b)
        a = torch.nn.functional.silu(x @ Wg[s].T) * (x @ Wu[s].T)              # sütun paralel: iletişim yok
        kismi.append(a @ Wd[:, s].T)                                           # satır paralel: kısmi toplam
    sonuc = _gloo(torch, kismi)                                                # gerçek all_reduce (4 süreç)
    gloo = sonuc[0]["toplam"]
    tp_fark = O.goreli_fark(O.liste(gloo), O.liste(tam))
    ranklar_ayni = all(torch.equal(s_["toplam"], gloo) for s_ in sonuc)
    # Öğrencinin tp_matmul'ü: gerçek bloklar
    Xb = x[:3, :32]
    Wb = Wg[:16, :32].T                                                        # (32, 16)
    ogr_fark = 0.0
    for mod in ("sutun", "satir"):
        o = tp_matmul(O.liste(Xb), O.liste(Wb), 4, mod)
        ogr_fark = max(ogr_fark, O.en_buyuk_fark(o["birlesik"], O.liste(Xb @ Wb)))
        if mod == "satir":
            parca_ref = [O.liste(Xb[:, i * 8:(i + 1) * 8] @ Wb[i * 8:(i + 1) * 8]) for i in range(4)]
            ogr_fark = max(ogr_fark, O.en_buyuk_fark(o["parca_ciktilari"], parca_ref))
    # Rank haritası: SmolLM2'nin gerçek katman ve parametre sayısı
    y = AYAR["yerlesim"]
    P = sum(p.numel() for p in model.parameters()) / 1e9
    yr = paralel_yerlesim(y["gpu"], y["tp"], y["pp"], y["dp"], model.config.num_hidden_layers, P)
    harita_dogru = all(r == p * (y["dp"] * y["tp"]) + d * y["tp"] + t for r, (p, d, t) in enumerate(yr["rank_haritasi"]))
    iletisim_bayt = 2 * tam.numel() * 2                                       # all-reduce ~ 2× mesaj (bf16, ring)
    TS = _tcpstore(dist)
    FL = _flash(torch)
    PP = _pipeline(torch, model, tok(AYAR["metin"] * 8, return_tensors="pt").input_ids)
    Tm = max(FL["uzunluk"])
    fl = FL["uzunluk"][Tm]
    return {
        "model": {k2: bilgi[k2] for k2 in ("model", "revizyon", "agirlik_sha256", "parametre")}, "surumler": O.surumler(),
        "katman": AYAR["katman"], "tp": tp, "ara_boyut": ff, "parca_ara_boyut": b, "token": int(x.shape[0]),
        "gloo_ranklar_ayni": ranklar_ayni, "tp_goreli_fark": tp_fark, "tp_ayni": tp_fark <= 1e-5 and ranklar_ayni,
        "ogrenci_fark": ogr_fark, "ogrenci_ayni": ogr_fark <= 1e-6, "yerlesim": yr, "harita_dogru": harita_dogru,
        "gpu_basi_parametre_milyar": yr["gpu_basi_parametre_milyar"], "katman_basi_allreduce_bayt_bf16": iletisim_bayt,
        "tcpstore": TS, "tcpstore_dogrulamasiz": TS["davetsiz_okudu"] and TS["davetsiz_yazdi"],
        "flash": FL, "flash_ayni_ve_hafif": (all(v["en_buyuk_fark"] <= (2e-2 if FL["cihaz"] == "cuda" else 1e-4) for v in FL["uzunluk"].values())
                                             and (FL["cihaz"] != "cuda" or fl["sdpa"]["ek_bellek_mb"] < 0.5 * fl["naif"]["ek_bellek_mb"])),
        "pipeline": PP, "bubble_mikrobatchla_azaliyor": PP["tablo"][64]["bubble"] < PP["tablo"][4]["bubble"] < PP["tablo"][1]["bubble"],
        "ozet": (f"SmolLM2 {AYAR['katman']}. katman MLP'si ({ff} ara boyut) 4 tensör paralel parçaya bölündü; 4 gloo sürecinin all_reduce sonucu "
                 f"modelin kendi MLP çıktısından göreli {tp_fark:.1e}. Öğrencinin sütun/satır bölmeli matmul'ü gerçek blokta {ogr_fark:.1e}. "
                 f"8 GPU (tp2·pp2·dp2) yerleşiminde aşamalar {yr['asama_katmanlari']}, GPU başına {yr['gpu_basi_parametre_milyar']} milyar parametre. "
                 f"Dikkat ({FL['cihaz']}, {FL['dtype']}, T={Tm}): naif {fl['naif']['sure_ms']} ms / {fl['naif']['ek_bellek_mb']} MB, SDPA "
                 f"{fl['sdpa']['sure_ms']} ms / {fl['sdpa']['ek_bellek_mb']} MB (skor matrisi fp32'de {fl['skor_matrisi_mb']} MB), fark {fl['en_buyuk_fark']:.1e}. "
                 f"Pipeline (ölçülen aşama süreleri {PP['asama_sure_ms']} ms): bubble m=1 {PP['tablo'][1]['bubble']}, m=4 {PP['tablo'][4]['bubble']}, "
                 f"m=64 {PP['tablo'][64]['bubble']}. TCPStore: davetsiz istemci kanaryayı okudu {TS['davetsiz_okudu']}, eğitim ayarını değiştirdi {TS['davetsiz_yazdi']}."),
        "sinir": ("Dört 'GPU' tek makinede CPU süreçleridir (gloo); NVLink, gerçek iletişim süresi ve hesap–iletişim örtüşmesi ölçülmez. "
                  "Pipeline zamanlaması ölçülen aşama süreleriyle simüle edilir (gerçek aşamalar arası iletişim ve geri yayılım yoktur); μP "
                  "denenmez. TCPStore yalnız 127.0.0.1'de açılır ve kanarya değerler kullanılır."),
    }


def goster(paralel_yerlesim, tp_matmul):
    r = deney(paralel_yerlesim, tp_matmul)
    print("TP all-reduce (gloo) modelin MLP'sinden göreli fark: %.1e | rank'lar aynı: %s" % (r["tp_goreli_fark"], r["gloo_ranklar_ayni"]))
    print("Öğrenci tp_matmul farkı: %.1e" % r["ogrenci_fark"])
    print("Yerleşim:", {k: r["yerlesim"][k] for k in ("asama_katmanlari", "tp_gruplari", "gpu_basi_parametre_milyar")})
    print("Sınır:", r["sinir"])
    print("Kanıt:", O.kanit("ai-temel-33", "run", r))
