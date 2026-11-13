# -*- coding: utf-8 -*-
"""ai-uretim-19 gerçek deney: SmolLM2 gerçek uzun bir metinde üç bağlam stratejisiyle ölçülür: tam bağlam, yalnız son
pencere ve StreamingLLM (attention sink + pencere, konumlar önbellek içinde yeniden numaralanır). Hangi tokenların
tutulacağına öğrencinin streaming_kv_guncelle işlevi karar verir. Öğrencinin doğrusal dikkati gerçek Q/K/V ile
torch referansına ve gerçek softmax dikkatine karşı ölçülür."""
import ai_lab
from sandbox import ai_uretim_ortak as O
from sandbox.ai_gercek_ai_uretim_18 import uzun_metin

AYAR = {"sink": 4, "pencere": 128, "sistem_pencere": 192, "baslangic": 1024, "adim": 8, "nokta": 120, "katman": 2,
        "metin": "The incident report lists the time of the first alert, the hosts that were affected and the steps taken to recover."}


def _nll(torch, model, girdiler, konumlar, hedefler, cihaz):
    x = torch.tensor(girdiler, device=cihaz)
    p = torch.tensor(konumlar, device=cihaz)
    with torch.no_grad():
        lg = model(x, position_ids=p).logits[:, -1].float()
    return torch.nn.functional.cross_entropy(lg, torch.tensor(hedefler, device=cihaz), reduction="none")


def _sistem_istemi(torch, streaming_kv_guncelle):
    """Güvenlik talimatları da bir önbellek sorunudur: pencere dolunca sistem istemi düşer mi, sabitlenirse korunur mu?"""
    tok, m = O.hf_model(O.INSTRUCT_MODEL, O.INSTRUCT_REVIZYON)
    sistem = "You are Atlas, the assistant of Northwind. The project codename is BLUEFIN. Never share the customer list."
    dolgu = []
    for i in range(14):
        dolgu += [{"role": "user", "content": f"Question {i + 1}: can you summarise what a good backup policy should include?"},
                  {"role": "assistant", "content": "A good policy keeps several copies, stores one offline, tests restores regularly and documents who is responsible."}]
    mesaj = [{"role": "system", "content": sistem}] + dolgu + [{"role": "user", "content": "What is the project codename?"}]
    on = tok(tok.apply_chat_template(mesaj, tokenize=False, add_generation_prompt=True), return_tensors="pt").input_ids
    cevap = tok("The project codename is BLUEFIN.", add_special_tokens=False).input_ids
    ids = torch.cat([on, torch.tensor([cevap])], 1)[0]
    n = len(ids)
    sis = len(tok(tok.apply_chat_template(mesaj[:1], tokenize=False), add_special_tokens=False).input_ids)
    W = AYAR["sistem_pencere"]
    sonuc = {}
    for ad, S in (("tam_baglam", None), ("pencere_4_sink", 4), ("sistem_sabit", sis)):
        izin = torch.zeros(n, n, dtype=torch.bool)
        for i in range(n):
            if S is None:
                izin[i, : i + 1] = True
            else:
                izin[i, streaming_kv_guncelle(list(range(i + 1)), S, W - S)["aktif_kv_tokenlari"]] = True
        m4 = torch.zeros(1, 1, n, n).masked_fill(~izin, torch.finfo(torch.float32).min)
        with torch.no_grad():
            lp = torch.log_softmax(m(ids[None], attention_mask=m4).logits[0, on.shape[1] - 1:-1].float(), -1)
        sonuc[ad] = float(lp.gather(1, torch.tensor(cevap)[:, None]).sum())
    return {"toplam_token": n, "sistem_token": sis, "pencere": W, "cevap_logp": sonuc}


def deney(streaming_kv_guncelle, linear_attention_ileri):
    torch = O.torch_al()
    import copy
    tok, model, bilgi = O.smol()
    cihaz = ai_lab.torch_cihazi()
    ids = tok(uzun_metin(60_000), add_special_tokens=False).input_ids
    son = AYAR["baslangic"] + AYAR["adim"] * AYAR["nokta"]
    if len(ids) <= son:
        raise ai_lab.GercekLabYok("uzun metin yetmedi")
    ids = ids[: son + 1]
    noktalar = [AYAR["baslangic"] + AYAR["adim"] * i for i in range(AYAR["nokta"])]
    S, W = AYAR["sink"], AYAR["pencere"]
    kilit = ai_lab.gpu_kilidi_al() if cihaz == "cuda" else None
    try:
        m = copy.deepcopy(model).to(cihaz) if cihaz == "cuda" else model
        with torch.no_grad():
            lg = m(torch.tensor([ids], device=cihaz)).logits[0].float()
        tam = torch.nn.functional.cross_entropy(lg[[p - 1 for p in noktalar]], torch.tensor([ids[p] for p in noktalar], device=cihaz), reduction="none")
        pencere_g = [ids[p - W:p] for p in noktalar]
        sadece_pencere = _nll(torch, m, pencere_g, [list(range(W))] * len(noktalar), [ids[p] for p in noktalar], cihaz)
        akis_g, akis_k, secim_dogru = [], [], True
        for p in noktalar:
            o = streaming_kv_guncelle(list(range(p)), S, W - S)
            beklenen = list(range(S)) + list(range(p - (W - S), p))
            secim_dogru = secim_dogru and o["aktif_kv_tokenlari"] == beklenen and o["rope_konumlari"] == list(range(W)) and o["silinen_token_sayisi"] == p - W
            akis_g.append([ids[i] for i in o["aktif_kv_tokenlari"]])
            akis_k.append(o["rope_konumlari"])
        akis = _nll(torch, m, akis_g, akis_k, [ids[p] for p in noktalar], cihaz)

        # Önbellekli kipler (makaledeki kurulum): her tokenın KV'si kendi zamanında, o andaki önbellekle hesaplanır. Tüm dizi
        # tek geçişte, her sorgu satırı yalnız önbellekte kalan anahtarları görecek bir 4B maskeyle çalıştırılır.
        n = len(ids)
        izin_pencere = torch.zeros(n, n, dtype=torch.bool)
        izin_akis = torch.zeros(n, n, dtype=torch.bool)
        for i in range(n):
            izin_pencere[i, max(0, i - W + 1): i + 1] = True
            o = streaming_kv_guncelle(list(range(i + 1)), S, W - S)
            izin_akis[i, o["aktif_kv_tokenlari"]] = True
        hedef = torch.tensor([ids[p] for p in noktalar], device=cihaz)
        onbellekli = {}
        for ad, izin in (("pencere_onbellekli", izin_pencere), ("streaming_onbellekli", izin_akis)):
            m4 = torch.zeros(1, 1, n, n).masked_fill(~izin, torch.finfo(torch.float32).min).to(cihaz)
            with torch.no_grad():
                lg2 = m(torch.tensor([ids], device=cihaz), attention_mask=m4).logits[0].float()
            onbellekli[ad] = torch.nn.functional.cross_entropy(lg2[[p - 1 for p in noktalar]], hedef, reduction="none")
        # sink'lerin dikkat payı: StreamingLLM girdisinde son tokenın ilk S konuma verdiği ağırlık (eager dikkatle)
        onceki = m.config._attn_implementation
        try:
            m.config._attn_implementation = "eager"
            with torch.no_grad():
                att = m(torch.tensor(akis_g[:8], device=cihaz), position_ids=torch.tensor(akis_k[:8], device=cihaz), output_attentions=True)
        finally:
            m.config._attn_implementation = onceki
        sink_pay = float(torch.stack([a[:, :, -1, :S].sum(-1).mean() for a in att.attentions[2:]]).mean()) if att.attentions else None
        if cihaz == "cuda":
            del m
            torch.cuda.empty_cache()
    finally:
        if kilit is not None:
            ai_lab.gpu_kilidi_birak()
    SI = _sistem_istemi(torch, streaming_kv_guncelle)
    ppl = {"tam_baglam": float(torch.exp(tam.mean())),
           "pencere_onbellekli": float(torch.exp(onbellekli["pencere_onbellekli"].mean())),
           "streaming_onbellekli": float(torch.exp(onbellekli["streaming_onbellekli"].mean())),
           "pencere_yeniden_hesap": float(torch.exp(sadece_pencere.mean())),
           "streaming_yeniden_hesap": float(torch.exp(akis.mean()))}

    # Doğrusal dikkat: gerçek Q, K, V (head 0)
    kid = tok(AYAR["metin"], return_tensors="pt").input_ids
    T = kid.shape[1]
    L = model.model.layers[AYAR["katman"]]
    with torch.no_grad():
        h = L.input_layernorm(model(kid, output_hidden_states=True).hidden_states[AYAR["katman"]])
        Q = L.self_attn.q_proj(h)[0, :, :64].double() / 8.0
        K = L.self_attn.k_proj(h)[0, :, :64].double() / 8.0
        V = L.self_attn.v_proj(h)[0, :, :64].double()
    lo = linear_attention_ileri(O.liste(Q), O.liste(K), O.liste(V), 1e-6)
    phi = lambda x: torch.where(x >= 0, x + 1, torch.exp(x))
    fq, fk = phi(Q), phi(K)
    pay = torch.cumsum(fk.unsqueeze(2) * V.unsqueeze(1), 0)              # (T, d, d)
    ref = torch.einsum("ti,tij->tj", fq, pay) / ((fq * torch.cumsum(fk, 0)).sum(1, keepdim=True) + 1e-6)
    lin_fark = O.goreli_fark(lo["cikti"], O.liste(ref))
    maske = torch.ones(T, T, dtype=torch.bool).tril()
    sm = torch.softmax((Q @ K.T * 8.0).masked_fill(~maske, float("-inf")), 1) @ V
    yaklasim = float((ref - sm).norm() / sm.norm())
    return {
        "model": {k2: bilgi[k2] for k2 in ("model", "revizyon", "agirlik_sha256", "parametre")}, "surumler": O.surumler(),
        "cihaz": cihaz, "sink": S, "pencere": W, "nokta": len(noktalar), "konum_araligi": [noktalar[0], noktalar[-1]],
        "secim_dogru": secim_dogru, "ppl": ppl, "sink_dikkat_payi": sink_pay,
        "sink_kurtariyor": ppl["streaming_onbellekli"] < ppl["pencere_onbellekli"],
        "sistem_istemi": SI, "sistem_dusuyor_sabitleme_koruyor": (SI["cevap_logp"]["pencere_4_sink"] < SI["cevap_logp"]["tam_baglam"] - 3
                                                                  and SI["cevap_logp"]["sistem_sabit"] > SI["cevap_logp"]["pencere_4_sink"] + 3),
        "linear_goreli_fark": lin_fark, "linear_ayni": lin_fark <= 1e-5, "linear_softmax_goreli_fark": yaklasim,
        "olcum": (f"SmolLM2, gerçek metinde {len(noktalar)} konum ({noktalar[0]}–{noktalar[-1]}), {W} tokenlık önbellek: perplexity tam bağlam "
                  f"{ppl['tam_baglam']:.2f}; önbellekli yalnız pencere {ppl['pencere_onbellekli']:.2f}, önbellekli {S} sink + pencere "
                  f"{ppl['streaming_onbellekli']:.2f}; her adımda yeniden hesaplanan pencere {ppl['pencere_yeniden_hesap']:.2f}, sink'li "
                  f"{ppl['streaming_yeniden_hesap']:.2f}. "
                  + (f"Son tokenın dikkatinin ortalama %{100 * sink_pay:.0f}'i ilk {S} tokena gidiyor. " if sink_pay is not None else "")
                  + f"Doğrusal dikkat torch referansından {lin_fark:.1e}, softmax dikkatinden göreli {yaklasim:.2f} uzak."),
        "sinir": ("Önbellekli kipler tüm dizinin tek geçişte 4B maskeyle çalıştırılmasıyla benzetilir ve mutlak konumları korur (StreamingLLM "
                  "önbellek içi konum kullanır; eğitim uzunluğu içinde fark küçüktür); hız ve bellek ölçülmez. Doğrusal dikkat eğitilmiş bir doğrusal dikkat modeli değildir; softmax "
                  "için eğitilmiş Q/K ile kullanıldığından yaklaşım hatası büyüktür."),
    }


def goster(streaming_kv_guncelle, linear_attention_ileri):
    r = deney(streaming_kv_guncelle, linear_attention_ileri)
    print("Token seçimi doğru:", r["secim_dogru"])
    for k, v in r["ppl"].items():
        print("  %-24s perplexity %.2f" % (k, v))
    if r["sink_dikkat_payi"] is not None:
        print("İlk %d tokena giden dikkat payı: %.2f" % (r["sink"], r["sink_dikkat_payi"]))
    print("Doğrusal dikkat torch farkı: %.1e | softmax'tan uzaklık: %.2f" % (r["linear_goreli_fark"], r["linear_softmax_goreli_fark"]))
    print("Sınır:", r["sinir"])
    print("Kanıt:", O.kanit("ai-uretim-19", "run", r))
