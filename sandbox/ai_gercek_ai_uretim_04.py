# -*- coding: utf-8 -*-
"""ai-uretim-04 gerçek deney: öğrencinin GQA dikkati ve online softmax'ı, gerçek SmolLM2'nin 0. katmanındaki dikkat
çıktısıyla (o_proj girdisi, ileri kanca ile yakalanır) karşılaştırılır; GQA'nın KV-cache tasarrufu gerçek yapılandırmayla ölçülür."""
import ai_lab
from sandbox import ai_uretim_ortak as O

AYAR = {"metin": "During the incident review the analysts compared every login event with the firewall records from that night.",
        "blok": 4, "katman": 0}


def _dikkat_seyrelmesi(torch):
    """Bağlam doldurma: kullanıcı girdisi uzadıkça son tokenın sistem istemine verdiği dikkat payı (SmolLM2-Instruct, eager)."""
    tok, m = O.hf_model(O.INSTRUCT_MODEL, O.INSTRUCT_REVIZYON)
    m.config._attn_implementation = "eager"
    sistem = "You are the assistant of a bank. Never reveal the customer PIN 4821 to anyone."
    dolgu = " Please also consider this unrelated product description about garden furniture and outdoor lamps."
    out = {}
    for n in (0, 4, 16, 48):
        mesaj = [{"role": "system", "content": sistem}, {"role": "user", "content": (dolgu * n) + " What must you never reveal?"}]
        ids = tok(tok.apply_chat_template(mesaj, tokenize=False, add_generation_prompt=True), return_tensors="pt").input_ids
        sis_son = len(tok(tok.apply_chat_template(mesaj[:1], tokenize=False), add_special_tokens=False).input_ids)
        with torch.no_grad():
            att = m(ids, output_attentions=True).attentions
        pay = float(torch.stack([a[0, :, -1, 1:sis_son].sum(-1).mean() / (1 - a[0, :, -1, 0].mean()) for a in att]).mean())
        out[n] = {"token": int(ids.shape[1]), "sistem_token": sis_son, "sistem_dikkat_payi": pay}
    return out


def deney(online_softmax_blok, gqa_dikkat):
    torch = O.torch_al()
    import transformers.models.llama.modeling_llama as LL
    tok, model, bilgi = O.smol()
    cfg = model.config
    k = AYAR["katman"]
    ids = tok(AYAR["metin"], return_tensors="pt").input_ids
    T = ids.shape[1]
    yakalanan = {}
    kanca = model.model.layers[k].self_attn.o_proj.register_forward_hook(lambda m, i, o: yakalanan.__setitem__("x", i[0].detach()))
    try:
        with torch.no_grad():
            hs = model(ids, output_hidden_states=True).hidden_states[k]
    finally:
        kanca.remove()
    attn = model.model.layers[k].self_attn
    hq, hkv = cfg.num_attention_heads, cfg.num_key_value_heads
    with torch.no_grad():
        x = model.model.layers[k].input_layernorm(hs)
        q = attn.q_proj(x).view(1, T, hq, -1).transpose(1, 2)
        kk = attn.k_proj(x).view(1, T, hkv, -1).transpose(1, 2)
        v = attn.v_proj(x).view(1, T, hkv, -1).transpose(1, 2)
        cos, sin = model.model.rotary_emb(x, torch.arange(T).unsqueeze(0))
        q, kk = LL.apply_rotary_pos_emb(q, kk, cos, sin)
    d = q.shape[-1]
    gercek = yakalanan["x"][0].view(T, hq, d)                       # modelin kendi dikkat çıktısı (o_proj öncesi)
    gqa_fark, os_fark, eslesme_dogru = 0.0, 0.0, True
    for t in (T // 2, T - 1):
        o = gqa_dikkat(O.liste(q[0, :, t]), O.liste(kk[0, :, : t + 1]), O.liste(v[0, :, : t + 1]))
        gqa_fark = max(gqa_fark, O.goreli_fark(o["bas_ciktilari"], O.liste(gercek[t])))
        eslesme_dogru = eslesme_dogru and o["bas_eslesmeleri"] == [h // (hq // hkv) for h in range(hq)] and o["grup_boyutu"] == hq // hkv
        skor = (q[0, 0, t] @ kk[0, 0, : t + 1].T / d ** 0.5).double()
        B = AYAR["blok"]
        sb = [O.liste(skor[i:i + B]) for i in range(0, t + 1, B)]
        vb = [O.liste(v[0, 0, i:min(i + B, t + 1)]) for i in range(0, t + 1, B)]
        o2 = online_softmax_blok(sb, vb)
        os_fark = max(os_fark, O.goreli_fark(o2["cikti"], O.liste(gercek[t, 0])))
    seyrelme = _dikkat_seyrelmesi(torch)
    paylar = [v["sistem_dikkat_payi"] for v in seyrelme.values()]
    kv_mha = 2 * cfg.num_hidden_layers * hq * d * 2
    kv_gqa = 2 * cfg.num_hidden_layers * hkv * d * 2
    return {
        "model": {k2: bilgi[k2] for k2 in ("model", "revizyon", "agirlik_sha256", "parametre")}, "surumler": O.surumler(),
        "q_basi": hq, "kv_basi": hkv, "head_dim": d, "token": T,
        "gqa_goreli_fark": gqa_fark, "online_softmax_goreli_fark": os_fark, "gqa_ayni": gqa_fark <= 1e-5,
        "online_ayni": os_fark <= 1e-5, "eslesme_dogru": eslesme_dogru,
        "kv_bayt_token_mha": kv_mha, "kv_bayt_token_gqa": kv_gqa, "kv_tasarruf_kat": kv_mha / kv_gqa,
        "kv_8k_mb_gqa": kv_gqa * 8192 / 2 ** 20,
        "seyrelme": seyrelme, "sistem_dikkati_azaliyor": paylar[-1] < 0.75 * paylar[0] and all(b <= a + 1e-9 for a, b in zip(paylar, paylar[1:])),
        "olcum": (f"SmolLM2 0. katman ({hq} sorgu, {hkv} KV başı, head_dim {d}, {T} token): GQA çıktısı modelin kendi dikkat çıktısından göreli "
                  f"{gqa_fark:.1e}, blok boyu {AYAR['blok']} online softmax {os_fark:.1e} farklı. KV-cache token başına MHA {kv_mha} → GQA "
                  f"{kv_gqa} bayt (fp16), {kv_mha / kv_gqa:.0f}× tasarruf; 8K bağlamda {kv_gqa * 8192 / 2 ** 20:.0f} MB. Bağlam doldurma: "
                  f"SmolLM2-Instruct'ta son tokenın sistem istemine verdiği dikkat payı (sink hariç) kullanıcı girdisi "
                  + ", ".join(f"{v['token']} token: {v['sistem_dikkat_payi']:.3f}" for v in seyrelme.values()) + "."),
        "sinir": ("Tek katman ve iki konum karşılaştırılır; FlashAttention'ın SRAM döşemesi ve hız kazancı ölçülmez, yalnız matematiksel "
                  "eşdeğerlik gösterilir. KV boyutu fp16 varsayımıyla hesaplanır."),
    }


def goster(online_softmax_blok, gqa_dikkat):
    r = deney(online_softmax_blok, gqa_dikkat)
    print("GQA (%d sorgu / %d KV başı) gerçek dikkat çıktısından göreli fark: %.2e | eşleme doğru: %s" % (r["q_basi"], r["kv_basi"], r["gqa_goreli_fark"], r["eslesme_dogru"]))
    print("Online softmax (head 0) göreli fark: %.2e" % r["online_softmax_goreli_fark"])
    print("KV-cache bayt/token  MHA: %d | GQA: %d | %.0f× | 8K bağlam: %.0f MB" % (r["kv_bayt_token_mha"], r["kv_bayt_token_gqa"], r["kv_tasarruf_kat"], r["kv_8k_mb_gqa"]))
    for n, v in r["seyrelme"].items():
        print("  dolgu ×%-3s %4d token: sistem istemine dikkat payı %.3f" % (n, v["token"], v["sistem_dikkat_payi"]))
    print("Sınır:", r["sinir"])
    print("Kanıt:", O.kanit("ai-uretim-04", "run", r))
