# -*- coding: utf-8 -*-
"""ai-uretim-20 gerçek deney: gerçek mamba-130m (Mamba-1) karıştırıcısının çıktısı, gerçek parametrelerinden (A_log,
Δ, B, C, D) torch'ta yazılmış seçici taramayla birebir yeniden üretilir; öğrencinin SSD yinelemesi ve dual matrisi
seçilen kanallarda bu gerçek değerlerle sınanır. Hibrit katman bellek planı, SmolLM2'nin gerçek KV-cache'i ve
Mamba'nın gerçek durum önbelleğinin ölçülen bayt sayılarıyla kurulur."""
import ai_lab
from sandbox import ai_uretim_ortak as O

AYAR = {"katman": 6, "kanallar": [0, 101, 517, 998, 1400], "metin": "The backup finished at midnight and the report was sent to the team.",
        "anahtar": "4821", "dolgu_tekrar": [0, 20, 80, 160],
        "dolgu": "The grass is green. The sky is blue. The sun is yellow. Here we go. There and back again. "}


def _cevap_logp(torch, tok, model, on, cevap):
    a = tok(on, return_tensors="pt", add_special_tokens=False).input_ids
    c = tok(cevap, add_special_tokens=False).input_ids
    ids = torch.cat([a, torch.tensor([c])], 1)
    with torch.no_grad():
        lp = torch.log_softmax(model(ids).logits[0, a.shape[1] - 1:-1].float(), -1)
    return float(lp.gather(1, torch.tensor(c)[:, None]).sum()), int(a.shape[1])


def _durum_tasirma(torch, tm, mm, ts, ms):
    """Sabit boyutlu durum geçmişi sıkıştırır: başa konan bir talimat/sır uzun dolguyla silinebilir mi?"""
    k = AYAR["anahtar"]
    giris = f"There is an important pass key hidden in this text. The pass key is {k}. Remember it. {k} is the pass key. "
    soru = "What is the pass key? The pass key is"
    sonuc = {}
    for t in AYAR["dolgu_tekrar"]:
        on = giris + AYAR["dolgu"] * t + soru
        lm, n = _cevap_logp(torch, tm, mm, on, " " + k)
        ls, _ = _cevap_logp(torch, ts, ms, on, " " + k)
        sonuc[t] = {"mamba_token": n, "mamba_logp": lm, "smollm2_logp": ls}
    taban, _ = _cevap_logp(torch, tm, mm, "There is an important pass key hidden in this text. " + soru, " " + k)
    return {"olcum": sonuc, "mamba_anahtarsiz_logp": taban}


def _cache_bayt(torch, c):
    toplam, gorulen = 0, set()

    def gez(x):
        nonlocal toplam
        if torch.is_tensor(x):
            if x.data_ptr() not in gorulen:
                gorulen.add(x.data_ptr()); toplam += x.numel() * x.element_size()
        elif isinstance(x, (list, tuple)):
            for y in x:
                gez(y)
        elif hasattr(x, "__dict__"):
            for y in vars(x).values():
                gez(y)
    gez(c)
    return toplam


def deney(ssd_durum_adimi, hibrit_katman_bellegi):
    torch = O.torch_al()
    tok, model = O.hf_model(O.MAMBA_MODEL, O.MAMBA_REVIZYON)
    ids = tok(AYAR["metin"], return_tensors="pt").input_ids
    T = ids.shape[1]
    mix = model.backbone.layers[AYAR["katman"]].mixer
    yak = {}
    k1 = mix.register_forward_pre_hook(lambda m, a, kw=None: yak.__setitem__("g", a[0].detach()))
    k2 = mix.register_forward_hook(lambda m, a, o: yak.__setitem__("c", (o[0] if isinstance(o, tuple) else o).detach()))
    try:
        with torch.no_grad():
            model(ids)
    finally:
        k1.remove(); k2.remove()
    hs = yak["g"].double()
    with torch.no_grad():
        I, N = mix.intermediate_size, mix.ssm_state_size
        p = (hs @ mix.in_proj.weight.double().T + (mix.in_proj.bias.double() if mix.in_proj.bias is not None else 0)).transpose(1, 2)
        x, z = p.chunk(2, dim=1)
        x = torch.nn.functional.conv1d(x, mix.conv1d.weight.double(), mix.conv1d.bias.double(), padding=mix.conv1d.padding[0], groups=I)[..., :T]
        x = torch.nn.functional.silu(x)
        sp = x.transpose(1, 2) @ mix.x_proj.weight.double().T
        dt, Bm, Cm = torch.split(sp, [mix.time_step_rank, N, N], dim=-1)
        delta = torch.nn.functional.softplus(dt @ mix.dt_proj.weight.double().T + mix.dt_proj.bias.double()).transpose(1, 2)   # (1, I, T)
        A = -torch.exp(mix.A_log.double())                                                                                      # (I, N)
        dA = torch.exp(A[None, :, None, :] * delta[..., None])                                                                  # (1, I, T, N)
        dBx = delta[..., None] * Bm[:, None, :, :] * x[..., None]
        h = torch.zeros(1, I, N, dtype=torch.float64)
        ys = []
        for t in range(T):
            h = dA[:, :, t] * h + dBx[:, :, t]
            ys.append((h * Cm[:, t][:, None, :]).sum(-1))
        y_tarama = torch.stack(ys, -1)                                                                                          # (1, I, T)
        y = (y_tarama + x * mix.D.double()[None, :, None]) * torch.nn.functional.silu(z)
        cikti = y.transpose(1, 2) @ mix.out_proj.weight.double().T
    mikser_fark = O.goreli_fark(O.liste(cikti[0]), O.liste(yak["c"][0]))

    # Öğrenci: seçilen kanallarda her durum boyutu ayrı skaler-a SSD (Mamba-1 köşegen A'sı her n için ayrı çürüme verir)
    ogr_fark, dual_fark = 0.0, 0.0
    for d in AYAR["kanallar"]:
        toplam = [0.0] * T
        for n in range(N):
            o = ssd_durum_adimi(O.liste(x[0, d]), O.liste(dA[0, d, :, n]), [[float(delta[0, d, t] * Bm[0, t, n])] for t in range(T)],
                                [[float(Cm[0, t, n])] for t in range(T)])
            toplam = [a + b for a, b in zip(toplam, o["cikti_y"])]
            Mx = torch.tensor(o["dual_matris_M"], dtype=torch.float64) @ x[0, d]
            dual_fark = max(dual_fark, O.goreli_fark(O.liste(Mx), o["cikti_y"]))
        ogr_fark = max(ogr_fark, O.goreli_fark(toplam, O.liste(y_tarama[0, d])))

    # Bellek: SmolLM2 KV-cache ve Mamba durum önbelleği, iki dizi uzunluğunda ölçülür
    st, sm, _ = O.smol()
    olc = {}
    for uz in (64, 512):
        g = torch.randint(0, 1000, (1, uz))
        with torch.no_grad():
            kv = sm(g, use_cache=True).past_key_values
            mc = model(torch.randint(0, 1000, (1, uz)), use_cache=True).cache_params
        if hasattr(mc, "get_recurrent_state"):                         # transformers 5: doğrusal katman önbelleği DynamicCache içinde
            ssm = sum(_cache_bayt(torch, [mc.get_conv_state(i), mc.get_recurrent_state(i)]) for i in range(model.config.num_hidden_layers))
        else:
            ssm = _cache_bayt(torch, mc)
        olc[uz] = {"kv_bayt": _cache_bayt(torch, kv), "ssm_bayt": ssm}
    DT = _durum_tasirma(torch, tok, model, st, sm)
    dto = DT["olcum"]
    ilk, son = dto[AYAR["dolgu_tekrar"][0]], dto[AYAR["dolgu_tekrar"][-1]]
    kv_token_katman = olc[512]["kv_bayt"] / (512 * sm.config.num_hidden_layers)
    ssm_katman = olc[512]["ssm_bayt"] / model.config.num_hidden_layers
    hb = hibrit_katman_bellegi(32, 8, 100_000, int(kv_token_katman), int(ssm_katman))
    ref_h = 4 * 100_000 * int(kv_token_katman) + 28 * int(ssm_katman)
    return {
        "model": {"model": O.MAMBA_MODEL, "revizyon": O.MAMBA_REVIZYON}, "surumler": O.surumler(),
        "katman": AYAR["katman"], "token": T, "ic_boyut": I, "durum_boyutu": N,
        "mikser_yeniden_uretim_fark": mikser_fark, "mikser_ayni": mikser_fark <= 1e-4,
        "ogrenci_tarama_fark": ogr_fark, "ogrenci_ayni": ogr_fark <= 1e-5, "dual_fark": dual_fark, "dual_ayni": dual_fark <= 1e-5,
        "cuk_ortalama": float(dA.mean()), "delta_ortalama": float(delta.mean()),
        "olcum_onbellek": olc, "kv_bayt_token_katman": kv_token_katman, "ssm_bayt_katman": ssm_katman,
        "ssm_sabit": olc[64]["ssm_bayt"] == olc[512]["ssm_bayt"] > 0, "kv_dogrusal": olc[512]["kv_bayt"] == 8 * olc[64]["kv_bayt"],
        "hibrit": hb, "hibrit_ayni": hb["hibrit_toplam_bayt"] == ref_h and hb["attention_katman_sayisi"] == 4,
        "durum_tasirma": DT,
        "mamba_unutuyor": son["mamba_logp"] < ilk["mamba_logp"] - 3 and son["mamba_logp"] > DT["mamba_anahtarsiz_logp"],
        "smollm2_hatirliyor": all(v["smollm2_logp"] > -1.5 for v in dto.values()),
        "olcum": (f"mamba-130m {AYAR['katman']}. katman karıştırıcısı ({I} kanal, N={N}, {T} token) gerçek parametrelerden yeniden üretildi: "
                  f"göreli fark {mikser_fark:.1e}. Öğrencinin SSD'si {len(AYAR['kanallar'])} kanal × {N} durumda taramadan {ogr_fark:.1e}, dual "
                  f"M·x {dual_fark:.1e}. Ölçülen önbellek: SmolLM2 KV {kv_token_katman:.0f} bayt/token/katman (64→512 token: "
                  f"{olc[64]['kv_bayt']}→{olc[512]['kv_bayt']}), Mamba durumu {ssm_katman:.0f} bayt/katman (uzunluktan bağımsız: "
                  f"{olc[64]['ssm_bayt']}={olc[512]['ssm_bayt']}). 32 katman, her 8'de bir dikkat, 100K bağlam: tasarruf {hb['tasarruf_orani']}. "
                  f"Durum taşırma: başa konan anahtarın logp'si {ilk['mamba_token']}→{son['mamba_token']} tokenda Mamba'da "
                  f"{ilk['mamba_logp']:.2f}→{son['mamba_logp']:.2f} (anahtarsız taban {DT['mamba_anahtarsiz_logp']:.2f}), SmolLM2'de "
                  f"{ilk['smollm2_logp']:.2f}→{son['smollm2_logp']:.2f}."),
        "sinir": ("mamba-130m Mamba-1'dir: A her durum boyutu için ayrı köşegen çürümedir; Mamba-2'nin skaler A'lı SSD'si bu yüzden her durum "
                  "boyutu ayrı ayrı (N=1) uygulanır. Tarama Python döngüsüyle CPU'da yapılır, donanım çekirdeği ve hız ölçülmez. Hibrit "
                  "plan farklı modellerin (SmolLM2 ve Mamba) ölçülen önbellekleriyle kurulan varsayımsal bir modeldir. Durum taşırma tek "
                  "bir anahtar ve yapay bir dolguyla iki küçük temel modelde ölçülür; büyük ya da hibrit modellerde unutma hızı farklıdır."),
    }


def goster(ssd_durum_adimi, hibrit_katman_bellegi):
    r = deney(ssd_durum_adimi, hibrit_katman_bellegi)
    print("Gerçek Mamba karıştırıcısı yeniden üretim farkı: %.1e" % r["mikser_yeniden_uretim_fark"])
    print("SSD taramadan fark: %.1e | dual M·x farkı: %.1e" % (r["ogrenci_tarama_fark"], r["dual_fark"]))
    print("KV bayt/token/katman: %.0f | Mamba durum bayt/katman: %.0f | durum sabit: %s" % (r["kv_bayt_token_katman"], r["ssm_bayt_katman"], r["ssm_sabit"]))
    print("Hibrit plan:", {k: r["hibrit"][k] for k in ("attention_katman_sayisi", "mamba_katman_sayisi", "tasarruf_orani")})
    print("Sınır:", r["sinir"])
    print("Kanıt:", O.kanit("ai-uretim-20", "run", r))
