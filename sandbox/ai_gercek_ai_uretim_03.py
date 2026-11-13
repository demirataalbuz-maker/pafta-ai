# -*- coding: utf-8 -*-
"""ai-uretim-03 gerçek deney: öğrencinin RMSNorm + RoPE ve SwiGLU işlevleri gerçek SmolLM2-135M'nin 0. katmanıyla
karşılaştırılır; RoPE boyut düzeninin (rotate_half ↔ ardışık çift) yanlış eşlenmesinin modeli sessizce bozduğu ölçülür."""
import ai_lab
from sandbox import ai_uretim_ortak as O

AYAR = {"metin": "The security team reviewed the server logs and found an unusual login at three in the morning.",
        "rope_konumlari": [0, 3, 7], "swiglu_tokenlari": [2, 9], "tolerans": 1e-5, "kurcalama_katman": 12,
        "guvenlik_metni": ("Backups protect a company only if someone regularly checks that they can be restored. Many teams discover during "
                           "an incident that the nightly job had been failing silently for weeks.")}


def _ref_rotate_pairs(torch):
    def rot(x):
        x1, x2 = x[..., ::2], x[..., 1::2]
        return torch.stack((-x2, x1), dim=-1).flatten(-2)
    return rot


def _ref_perplexity(torch, model, ids):
    with torch.no_grad():
        return float(torch.exp(model(ids, labels=ids).loss))


def _tensor_ozetleri(m):
    import hashlib
    return {ad: hashlib.sha256(p.detach().contiguous().cpu().numpy().tobytes()).hexdigest() for ad, p in m.state_dict().items()}


def _kurcalama(torch, model, tok):
    """Tedarik zinciri: tek bir RMSNorm kazancı değiştirilir; davranış farkı ve tensör özetleriyle tespit ölçülür."""
    import copy
    ids = tok(AYAR["guvenlik_metni"], return_tensors="pt").input_ids
    once = _tensor_ozetleri(model)
    ppl0 = _ref_perplexity(torch, model, ids)
    g0 = model.model.layers[AYAR["kurcalama_katman"]].post_attention_layernorm.weight
    ch = int(g0.detach().abs().argmax())
    sonuc = {}
    for ad, carpan in (("kucuk", 1.02), ("buyuk", 30.0)):
        m = copy.deepcopy(model)
        with torch.no_grad():
            m.model.layers[AYAR["kurcalama_katman"]].post_attention_layernorm.weight[ch] *= carpan
        ppl = _ref_perplexity(torch, m, ids)
        sonra = _tensor_ozetleri(m)
        sonuc[ad] = {"carpan": carpan, "ppl": ppl, "ppl_goreli_degisim": (ppl - ppl0) / ppl0,
                     "degisen_tensorler": [a for a in once if once[a] != sonra[a]]}
        m = None
    return {"kanal": ch, "ppl_temiz": ppl0, **sonuc}


def deney(rmsnorm_ve_rope, swiglu_ileri):
    torch = O.torch_al()
    tok, model, bilgi = O.smol()
    cfg = model.config
    taban = float((getattr(cfg, "rope_parameters", None) or {}).get("rope_theta") or getattr(cfg, "rope_theta"))
    eps = float(cfg.rms_norm_eps)
    katman = model.model.layers[0]
    ids = tok(AYAR["metin"], return_tensors="pt").input_ids
    with torch.no_grad():
        h = model.model.embed_tokens(ids)[0]                       # 0. katman girdisi (gerçek gömmeler)
        h_norm = katman.input_layernorm(h)
        q = katman.self_attn.q_proj(h_norm).view(len(ids[0]), cfg.num_attention_heads, -1)
        cos, sin = model.model.rotary_emb(h.unsqueeze(0), torch.arange(len(ids[0])).unsqueeze(0))
    d = q.shape[-1]
    gamma = O.liste(katman.input_layernorm.weight)

    # 1) RMSNorm: öğrencinin işlevi, gerçek gamma ve eps ile, gerçek gömme vektörleri üzerinde
    rms_fark, rope_fark, norm_korundu = 0.0, 0.0, True
    ornekler = []
    for p in AYAR["rope_konumlari"]:
        o = rmsnorm_ve_rope(O.liste(h[p]), list(gamma), 0, taban, eps)
        rms_fark = max(rms_fark, O.goreli_fark(o["rmsnorm"], O.liste(h_norm[p])))
        # 2) RoPE: HF 'rotate_half' düzeni (i, i+d/2) → öğrencinin ardışık çift düzeni (2j, 2j+1). RMSNorm'u etkisiz
        #    kılmak için gamma = rms(x), eps = 0 verilir; böylece işlev yalnız döndürmeyi uygular.
        x_hf = q[p, 0].double()
        x_st = torch.empty_like(x_hf)
        x_st[0::2], x_st[1::2] = x_hf[: d // 2], x_hf[d // 2:]
        rms = float(torch.sqrt((x_st ** 2).mean()))
        o2 = rmsnorm_ve_rope(O.liste(x_st), [rms] * d, p, taban, 0.0)
        y_st = torch.tensor(o2["rope"], dtype=torch.float64)
        y_hf = torch.cat((y_st[0::2], y_st[1::2]))
        beklenen = (x_hf * cos[0, p].double() + torch.cat((-x_hf[d // 2:], x_hf[: d // 2])) * sin[0, p].double())
        rope_fark = max(rope_fark, O.goreli_fark(O.liste(y_hf), O.liste(beklenen)))
        norm_korundu = norm_korundu and o2["norm_korundu_mu"] is True
        ornekler.append({"konum": p, "token": tok.decode(ids[0, p]), "rmsnorm_ilk3": o["rmsnorm"][:3], "rope_ilk3": o2["rope"][:3]})

    # 3) SwiGLU: öğrencinin işlevi gerçek gate/up/down ağırlıklarıyla, gerçek post-attention girdisinde
    with torch.no_grad():
        ara = model(ids, output_hidden_states=True).hidden_states[1][0]   # 0. katman çıkışı
        x_mlp = model.model.layers[1].post_attention_layernorm(ara)
    mlp = model.model.layers[1].mlp
    Wg, Wu, Wd = O.liste(mlp.gate_proj.weight.T), O.liste(mlp.up_proj.weight.T), O.liste(mlp.down_proj.weight.T)
    swiglu_fark = 0.0
    for p in AYAR["swiglu_tokenlari"]:
        o = swiglu_ileri(O.liste(x_mlp[p]), Wg, Wu, Wd)
        with torch.no_grad():
            beklenen = mlp(x_mlp[p].unsqueeze(0))[0]
        swiglu_fark = max(swiglu_fark, O.goreli_fark(o["cikti"], O.liste(beklenen)))

    # 4) Sessiz bozulma: aynı ağırlıklarla RoPE düzeni yanlış (ardışık çift) uygulanırsa perplexity
    import transformers.models.llama.modeling_llama as LL
    ppl_dogru = _ref_perplexity(torch, model, ids)
    eski = LL.rotate_half
    try:
        LL.rotate_half = _ref_rotate_pairs(torch)
        ppl_yanlis = _ref_perplexity(torch, model, ids)
    finally:
        LL.rotate_half = eski
    ppl_geri = _ref_perplexity(torch, model, ids)
    K = _kurcalama(torch, model, tok)
    hedef_ad = f"model.layers.{AYAR['kurcalama_katman']}.post_attention_layernorm.weight"
    tol = AYAR["tolerans"]
    return {
        "model": {k: bilgi[k] for k in ("model", "revizyon", "agirlik_sha256", "parametre")}, "surumler": O.surumler(),
        "rope_taban": taban, "rms_eps": eps, "baslik_boyutu": d, "token_sayisi": int(ids.shape[1]),
        "rmsnorm_goreli_fark": rms_fark, "rope_goreli_fark": rope_fark, "swiglu_goreli_fark": swiglu_fark,
        "rmsnorm_ayni": rms_fark <= tol, "rope_ayni": rope_fark <= tol, "swiglu_ayni": swiglu_fark <= 1e-4,
        "norm_korundu": norm_korundu, "ppl_dogru": ppl_dogru, "ppl_yanlis_duzen": ppl_yanlis, "ppl_geri_yuklendi": ppl_geri,
        "yanlis_duzen_bozar": ppl_yanlis > 2 * ppl_dogru and abs(ppl_geri - ppl_dogru) < 1e-6, "ornekler": ornekler,
        "kurcalama": K, "kurcalama_tespit": K["kucuk"]["degisen_tensorler"] == [hedef_ad] and K["buyuk"]["degisen_tensorler"] == [hedef_ad],
        "kucuk_kurcalama_gizli": abs(K["kucuk"]["ppl_goreli_degisim"]) < 0.01, "buyuk_kurcalama_bozar": K["buyuk"]["ppl_goreli_degisim"] > 0.1,
        "olcum": (f"SmolLM2-135M 0. katman: RMSNorm göreli fark {rms_fark:.1e}, RoPE (head 0, konum {AYAR['rope_konumlari']}) {rope_fark:.1e}, "
                  f"1. katman SwiGLU {swiglu_fark:.1e}. Aynı ağırlıklarla RoPE ardışık çift düzeninde uygulanınca perplexity "
                  f"{ppl_dogru:.2f} → {ppl_yanlis:.2f}. Kurcalama: {AYAR['kurcalama_katman']}. katmanın tek bir RMSNorm kazancı (kanal {K['kanal']}) ×1.02 "
                  f"yapılınca perplexity %{100 * K['kucuk']['ppl_goreli_degisim']:+.2f}, ×30 yapılınca %{100 * K['buyuk']['ppl_goreli_degisim']:+.0f} değişiyor; "
                  f"tensör başına SHA-256 iki durumda da yalnız o tensörü işaretliyor."),
        "sinir": ("Tek katman ve birkaç token karşılaştırılır; tam ileri geçiş, KV önbelleği ve uzun bağlam ölçeklemesi (ai-uretim-18) "
                  "sınanmaz. Perplexity tek bir cümlede ölçülür."),
    }


def goster(rmsnorm_ve_rope, swiglu_ileri):
    r = deney(rmsnorm_ve_rope, swiglu_ileri)
    print("Model:", r["model"]["model"], "| RoPE tabanı:", r["rope_taban"], "| eps:", r["rms_eps"], "| head_dim:", r["baslik_boyutu"])
    print("RMSNorm göreli fark: %.2e | RoPE: %.2e | SwiGLU: %.2e" % (r["rmsnorm_goreli_fark"], r["rope_goreli_fark"], r["swiglu_goreli_fark"]))
    print("Perplexity doğru düzen: %.2f | ardışık çift düzeni: %.2f" % (r["ppl_dogru"], r["ppl_yanlis_duzen"]))
    K = r["kurcalama"]
    print("Kurcalama  ×1.02: ppl %+.3f%% | ×30: ppl %+.1f%% | değişen tensör: %s" % (100 * K["kucuk"]["ppl_goreli_degisim"], 100 * K["buyuk"]["ppl_goreli_degisim"], K["kucuk"]["degisen_tensorler"]))
    for o in r["ornekler"]:
        print("  konum", o["konum"], repr(o["token"]), "rmsnorm[:3]", o["rmsnorm_ilk3"], "rope[:3]", o["rope_ilk3"])
    print("Sınır:", r["sinir"])
    print("Kanıt:", O.kanit("ai-uretim-03", "run", r))
