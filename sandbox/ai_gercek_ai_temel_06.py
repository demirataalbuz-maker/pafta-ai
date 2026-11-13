# -*- coding: utf-8 -*-
"""ai-temel-06 gerçek deneyi: SmolLM2'nin gerçek bir katmanında çok başlı nedensel dikkat.

Q/K/V bütün kafalar için modelin kendi projeksiyonları ve RoPE ile çıkarılır; GQA'da paylaşılan Key/Value
kafaları Query kafalarına genişletilir. Doğrulama modelin o katmanda ürettiği birleşik kafa çıktısıyla yapılır.
"""
import ai_lab

DENEY_METNI = "The keys to the cabinet are on the table"


def katman_girdileri(metin, katman):
    """(q, k, v, model_baglami, tokenlar, kafa_sayisi): q/k/v/model_baglami [T, H*d] float32."""
    torch = ai_lab._torch()
    from transformers.models.llama.modeling_llama import apply_rotary_pos_emb
    tok, model, _ = ai_lab.dil_modeli()
    cfg = model.config
    H, KV = cfg.num_attention_heads, cfg.num_key_value_heads
    d = cfg.hidden_size // H
    if not 0 <= katman < cfg.num_hidden_layers:
        raise ValueError("katman aralık dışında")
    att = model.model.layers[katman].self_attn
    yakala = {}
    def girdi(_m, args, kwargs):
        yakala["h"] = kwargs.get("hidden_states", args[0] if args else None)
        yakala["pe"] = kwargs["position_embeddings"]
    def cikti(_m, args):
        yakala["o"] = args[0]
    k1 = att.register_forward_pre_hook(girdi, with_kwargs=True)
    k2 = att.o_proj.register_forward_pre_hook(cikti)
    ids = tok(metin)["input_ids"]
    try:
        with torch.no_grad():
            model(torch.tensor([ids]))
    finally:
        k1.remove()
        k2.remove()
    x = yakala["h"][0]
    T = x.shape[0]
    with torch.no_grad():
        q = att.q_proj(x).view(T, H, d).transpose(0, 1)
        k = att.k_proj(x).view(T, KV, d).transpose(0, 1)
        v = att.v_proj(x).view(T, KV, d).transpose(0, 1)
        cos, sin = yakala["pe"]
        q, k = apply_rotary_pos_emb(q.unsqueeze(0), k.unsqueeze(0), cos, sin)
        q, k = q[0], k[0]
        k = k.repeat_interleave(H // KV, dim=0)  # GQA: her Query kafasına kendi grubunun Key/Value'su
        v = v.repeat_interleave(H // KV, dim=0)
    birlestir = lambda t: t.transpose(0, 1).reshape(T, H * d).clone()  # noqa: E731
    return birlestir(q), birlestir(k), birlestir(v), yakala["o"][0].clone(), tok.convert_ids_to_tokens(ids), H


def referans(q, k, v, kafa_sayisi, *, bolme="ardisik", maske=True, maske_sonra=False, olcek="kafa", ters_birlestir=False):
    """Doğru sonuç (varsayılanlarla) ve testlerin kullandığı hatalı varyantlar."""
    torch = ai_lab._torch()
    q, k, v = q.double(), k.double(), v.double()
    T, D = q.shape
    H = kafa_sayisi
    d = D // H
    def bol(t):
        if bolme == "ardisik":
            return t.view(T, H, d).transpose(0, 1)
        return t.view(T, d, H).permute(2, 0, 1)  # atlamalı (yanlış) bölme
    qh, kh, vh = bol(q), bol(k), bol(v)
    skor = qh @ kh.transpose(1, 2) / ((d if olcek == "kafa" else D) ** 0.5)
    gelecek = torch.triu(torch.ones(T, T, dtype=torch.bool), 1)
    if maske and not maske_sonra:
        skor = skor.masked_fill(gelecek, float("-inf"))
    w = torch.softmax(skor, dim=-1)
    if maske and maske_sonra:
        w = w.masked_fill(gelecek, 0.0)
    c = w @ vh
    if ters_birlestir:
        c = c.flip(0)
    return {"agirliklar": w, "baglam": c.transpose(0, 1).reshape(T, D)}


def nedensellik(degisen="chair"):
    """Gerçek modelde: yalnız son kelime değişince önceki konumların logitleri değişiyor mu? (en büyük fark)"""
    torch = ai_lab._torch()
    tok, model, _ = ai_lab.dil_modeli()
    a = tok(DENEY_METNI)["input_ids"]
    b = tok(DENEY_METNI.rsplit(" ", 1)[0] + " " + degisen)["input_ids"]
    with torch.no_grad():
        la = model(torch.tensor([a])).logits[0]
        lb = model(torch.tensor([b])).logits[0]
    ortak = 0
    while ortak < min(len(a), len(b)) and a[ortak] == b[ortak]:
        ortak += 1
    return {"ortak_onek": ortak, "onceki_konum_farki": (la[:ortak] - lb[:ortak]).abs().max().item(),
            "son_konum_farki": (la[-1] - lb[-1]).abs().max().item()}


def kafa_ozeti(fn, metin=DENEY_METNI, katman=4):
    """Son tokenın her kafada (ilk token hariç) en çok baktığı token: kafaların farklı ilişkileri yakaladığını gösterir."""
    q, k, v, _, tokenlar, H = katman_girdileri(metin, katman)
    w = fn(q, k, v, H)["agirliklar"].double()
    ozet = []
    for h in range(H):
        j = int(w[h, -1, 1:].argmax()) + 1
        ozet.append({"kafa": h, "token": tokenlar[j], "agirlik": round(w[h, -1, j].item(), 3),
                     "ilk_tokena": round(w[h, -1, 0].item(), 3)})
    return ozet


def goster(fn):
    """Çalıştır düğmesi: öğrencinin işleviyle gerçek katmanda kafa başına dikkat ve nedensellik."""
    _, _, bilgi = ai_lab.dil_modeli()
    q, k, v, model_c, tokenlar, H = katman_girdileri(DENEY_METNI, 4)
    r = fn(q, k, v, H)
    fark = (r["baglam"].double() - model_c.double()).abs().max().item()
    print(f"Model: {bilgi['model']}@{bilgi['revizyon'][:8]} · katman 4 · {H} kafa × {q.shape[1] // H} boyut")
    print(f"Metin: {DENEY_METNI!r}")
    print(f"Senin birleşik bağlamın ile modelin gerçek katman çıktısı arasındaki en büyük fark: {fark:.2e}\n")
    print(f"Son token {tokenlar[-1]!r} her kafada (ilk token hariç) en çok kime bakıyor:")
    ozet = kafa_ozeti(fn)
    for o in ozet:
        print(f"  kafa {o['kafa']}: {o['token']!r:>12} ({o['agirlik']:.3f})   ilk tokena: {o['ilk_tokena']:.3f}")
    n = nedensellik()
    print(f"\nNedensellik (gerçek model): son kelime 'table' → 'chair'. İlk {n['ortak_onek']} konumun logit farkı "
          f"{n['onceki_konum_farki']:.2e}, son konumun farkı {n['son_konum_farki']:.2f}")
    print("\nKanıt:", ai_lab.kanit_yaz("temel-cok-basli-calistir", {
        "kaynak": "gercek", "kabul": False, "ders": "ai-temel-06", "model_bilgisi": bilgi, "katman": 4,
        "model_farki": fark, "kafa_ozeti": ozet, "nedensellik": n}))
