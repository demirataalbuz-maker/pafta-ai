# -*- coding: utf-8 -*-
"""ai-temel-05 gerçek deneyi: SmolLM2'nin gerçek bir katman/kafasında nedensel dikkat.

Q/K/V modelin kendi projeksiyon ağırlıkları ve döner konum kodlamasıyla (RoPE) çıkarılır; doğrulama
modelin o katmanda gerçekten ürettiği kafa çıktısıyla (o_proj girdisi) yapılır.
"""
import ai_lab

DENEY_METNI = "The cat sat on the mat because it was tired"


def kafa_girdileri(metin, katman, kafa):
    """(q, k, v, model_baglami, tokenlar): [T, d] float32 tensörler; model_baglami modelin bu kafa için ürettiği çıktı."""
    torch = ai_lab._torch()
    from transformers.models.llama.modeling_llama import apply_rotary_pos_emb
    tok, model, _ = ai_lab.dil_modeli()
    cfg = model.config
    H, KV = cfg.num_attention_heads, cfg.num_key_value_heads
    d = cfg.hidden_size // H
    if not 0 <= katman < cfg.num_hidden_layers or not 0 <= kafa < H:
        raise ValueError("katman/kafa aralık dışında")
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
    g = kafa // (H // KV)  # gruplu sorgu dikkati: birkaç Query kafası aynı Key/Value kafasını paylaşır
    return (q[0, kafa].clone(), k[0, g].clone(), v[g].clone(),
            yakala["o"][0, :, kafa * d:(kafa + 1) * d].clone(), tok.convert_ids_to_tokens(ids))


def referans(q, k, v, *, olcek="kok", maske=True, softmax_boyutu=-1, maske_sonra=False, deger=True):
    """Doğru sonuç (varsayılanlarla) ve testlerin kullandığı hatalı varyantlar."""
    torch = ai_lab._torch()
    q, k, v = q.double(), k.double(), v.double()
    T, d = q.shape
    bolen = {"kok": d ** 0.5, "yok": 1.0, "d": float(d)}[olcek]
    skor = q @ k.T / bolen
    gelecek = torch.triu(torch.ones(T, T, dtype=torch.bool), 1)
    if maske and not maske_sonra:
        skor = skor.masked_fill(gelecek, float("-inf"))
    w = torch.softmax(skor, dim=softmax_boyutu)
    if maske and maske_sonra:
        w = w.masked_fill(gelecek, 0.0)
    return {"agirliklar": w, "baglam": w @ (v if deger else q)}


def sink_orani(fn, metin=DENEY_METNI, katmanlar=(0, 3, 15, 29)):
    """Her katmanda, 4. tokendan itibaren ilk tokena giden ortalama dikkat (tüm kafalar)."""
    _, model, _ = ai_lab.dil_modeli()
    H = model.config.num_attention_heads
    sonuc = {}
    for L in katmanlar:
        toplam = 0.0
        for h in range(H):
            q, k, v, _, _ = kafa_girdileri(metin, L, h)
            toplam += fn(q, k, v)["agirliklar"][3:, 0].double().mean().item()
        sonuc[L] = round(toplam / H, 4)
    return sonuc


def goster(fn):
    """Çalıştır düğmesi: öğrencinin işleviyle gerçek bir kafanın dikkat haritası ve katman bazında 'sink'."""
    _, _, bilgi = ai_lab.dil_modeli()
    q, k, v, model_c, tokenlar = kafa_girdileri(DENEY_METNI, 3, 4)
    r = fn(q, k, v)
    w = r["agirliklar"].double()
    print(f"Model: {bilgi['model']}@{bilgi['revizyon'][:8]} · katman 3, kafa 4 · d={q.shape[1]}")
    print(f"Metin: {DENEY_METNI!r}\n")
    print("Her token en çok hangi önceki tokena bakıyor (ilk token hariç / dahil):")
    satirlar = []
    for i, t in enumerate(tokenlar):
        j = int(w[i].argmax())
        j2 = int(w[i, 1:i + 1].argmax()) + 1 if i >= 1 else 0
        satirlar.append({"token": t, "en_cok": tokenlar[j], "agirlik": round(w[i, j].item(), 3),
                         "ilk_haric": tokenlar[j2], "ilk_haric_agirlik": round(w[i, j2].item(), 3)})
        print(f"  {t!r:>12} → {tokenlar[j2]!r:>12} ({w[i, j2].item():.3f})   [dahil: {tokenlar[j]!r} {w[i, j].item():.3f}]")
    fark = (r["baglam"].double() - model_c.double()).abs().max().item()
    print(f"\nSenin bağlamın ile modelin bu kafadaki gerçek çıktısı arasındaki en büyük fark: {fark:.2e}")
    sink = sink_orani(fn)
    print("İlk tokena giden ortalama dikkat (attention sink), katman → oran:", sink)
    print("\nKanıt:", ai_lab.kanit_yaz("temel-dikkat-calistir", {
        "kaynak": "gercek", "kabul": False, "ders": "ai-temel-05", "model_bilgisi": bilgi,
        "metin":DENEY_METNI,"tokenlar":tokenlar,"q":q.tolist(),"k":k.tolist(),"v":v.tolist(),"model_baglami":model_c.tolist(),"agirliklar":w.tolist(),"ogrenci_baglami":r["baglam"].tolist(),"ayarlar":{"dtype_hesap":"float64","nedensel":True,"sink_katmanlari":[0,3,15,29]},"katman": 3, "kafa": 4, "harita": satirlar, "model_farki": fark, "sink": sink}))
