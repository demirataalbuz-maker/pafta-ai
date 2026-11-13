# -*- coding: utf-8 -*-
"""ai-uretim-17 gerçek deney: SmolLM2'nin gerçek k_proj ve v_proj ağırlıkları ortak bir düşük ranklı (MLA tarzı)
latent'e SVD ile ayrıştırılır. Öğrencinin MLA sıkıştırma/açma ve matrix absorption işlevi gerçek gizli durum ve
sorguyla torch'a karşı sınanır; decoupled RoPE'lu latent dikkat gerçek değerlerle karşılaştırılır. Son olarak tüm
katmanların K/V'si rank r latent'ten üretilerek KV-cache boyutu ile perplexity arasındaki denge ölçülür."""
import copy
import ai_lab
from sandbox import ai_uretim_ortak as O

AYAR = {"katman": 4, "rank": 32, "d_rope": 16, "ranklar": [32, 64, 128, 192, 384], "tersine_ranklar": [32, 64, 128], "tersine_katman": 1,
        "gizli_metin": "Customer Elif Kaya called about invoice 7731 and asked us to change her delivery address to Moda Street.",
        "kalibrasyon": ("The museum opened a new wing for modern sculpture last spring. Visitors can join a guided tour every hour, "
                        "and the cafe on the ground floor serves soup, bread and coffee. Tickets are cheaper on weekdays, and students "
                        "with a valid card enter for free. The library next door keeps old maps of the city, which researchers may "
                        "request a day in advance. In the evening the square fills with musicians, families and tourists taking photos."),
        "metin": ("Security teams rotate credentials regularly, review access logs every morning and keep an offline copy of the "
                  "recovery keys. When an alert fires, the on-call engineer checks the dashboard, isolates the affected host and "
                  "writes a short timeline so that the rest of the team can follow what happened.")}


def _ortak_svd(torch, attn):
    Wk = attn.k_proj.weight.detach().double()          # (192, 576)
    Wv = attn.v_proj.weight.detach().double()
    M = torch.cat([Wk.T, Wv.T], 1)                     # (576, 384): h @ M = [k | v]
    U, S, Vh = torch.linalg.svd(M, full_matrices=False)
    return M, U, S, Vh


def _kalibrasyon(torch, tok, model):
    """Her katmanın k_proj girdisinin (normalize gizli durum) kovaryansı: aktivasyon farkında SVD için."""
    girdiler = {}
    kancalar = [L.self_attn.k_proj.register_forward_pre_hook(lambda m, a, i=i: girdiler.setdefault(i, []).append(a[0][0].detach().double()))
                for i, L in enumerate(model.model.layers)]
    try:
        with torch.no_grad():
            model(tok(AYAR["kalibrasyon"], return_tensors="pt").input_ids)
    finally:
        for k in kancalar:
            k.remove()
    C = {}
    for i, x in girdiler.items():
        X = torch.cat(x)
        c = X.T @ X / X.shape[0]
        C[i] = c + 1e-3 * c.diagonal().mean() * torch.eye(c.shape[0], dtype=c.dtype)
    return C


def _dusuk_rank_model(torch, model, r, C=None):
    m = copy.deepcopy(model)
    with torch.no_grad():
        for i, L in enumerate(m.model.layers):
            M, U, S, Vh = _ortak_svd(torch, L.self_attn)
            if C is None:
                Mr = (U[:, :r] * S[:r]) @ Vh[:r]
            else:                                       # min ||X (M − Mr)||: kovaryansın Cholesky çarpanıyla beyazlatılmış SVD
                R = torch.linalg.cholesky(C[i]).T
                U2, S2, Vh2 = torch.linalg.svd(R @ M, full_matrices=False)
                Mr = torch.linalg.solve_triangular(R, (U2[:, :r] * S2[:r]) @ Vh2[:r], upper=True)
            L.self_attn.k_proj.weight.copy_(Mr[:, :192].T.float())
            L.self_attn.v_proj.weight.copy_(Mr[:, 192:].T.float())
    return m


def _kv_tersine(torch, tok, model):
    """KV önbelleğinin tersine çevrilmesi: tam KV'den ya da sıkıştırılmış latent c_kv'den girdinin hangi token olduğu kestirilebilir mi?
    Kalibrasyon metninde KV → token gömmesi doğrusal eşlemesi (ridge) öğrenilir, ayrı bir 'gizli' metinde denenir."""
    from sandbox.ai_gercek_ai_uretim_31 import _ingilizce
    L = model.model.layers[AYAR["tersine_katman"]]
    yak = []
    kanca = L.self_attn.k_proj.register_forward_pre_hook(lambda m, a: yak.append(a[0][0].detach().double()))
    try:
        kal = torch.tensor([_ingilizce(tok)[:6000]])
        gizli = tok(AYAR["gizli_metin"], return_tensors="pt").input_ids
        with torch.no_grad():
            model(kal); model(gizli)
    finally:
        kanca.remove()
    Hk, Hg = yak[0], yak[1]
    E = model.model.embed_tokens.weight.detach().double()
    M, U, S, _ = _ortak_svd(torch, L.self_attn)
    sonuc = {}
    for r in AYAR["tersine_ranklar"] + ["tam_kv"]:
        W = M if r == "tam_kv" else U[:, :r] * S[:r]
        Ck, Cg = Hk @ W, Hg @ W
        Y = E[kal[0]]
        A = torch.linalg.solve(Ck.T @ Ck + 1e-3 * torch.eye(Ck.shape[1], dtype=Ck.dtype), Ck.T @ Y)
        tahmin = torch.nn.functional.normalize(Cg @ A, dim=1) @ torch.nn.functional.normalize(E, dim=1).T
        dogru = float((tahmin.argmax(1) == gizli[0]).double().mean())
        sonuc[str(r)] = {"token_dogrulugu": dogru, "boyut": int(W.shape[1])}
    ornek = tahmin.argmax(1)[:16].tolist()
    return {"rank": sonuc, "gizli_token": int(gizli.shape[1]), "geri_cikan_ornek": tok.decode(ornek)}


def deney(mla_kv_sikistir_ve_ac, mla_bellek_ve_dikkat):
    torch = O.torch_al()
    import transformers.models.llama.modeling_llama as LL
    tok, model, bilgi = O.smol()
    ids = tok(AYAR["metin"], return_tensors="pt").input_ids
    T = ids.shape[1]
    k = AYAR["katman"]
    L = model.model.layers[k]
    with torch.no_grad():
        h = L.input_layernorm(model(ids, output_hidden_states=True).hidden_states[k])[0].double()
    M, U, S, Vh = _ortak_svd(torch, L.self_attn)
    r = AYAR["rank"]
    W_dkv = U[:, :r] * S[:r]                           # (576, r)
    W_uk = Vh[:r, :64]                                 # head 0 anahtarı (r, 64)
    W_uv = Vh[:r, 192:256]                             # head 0 değeri
    Wq = L.self_attn.q_proj.weight.detach().double()
    q_tum = h @ Wq.T                                   # (T, 576), RoPE öncesi içerik sorgusu
    t = T - 1
    q0 = q_tum[t, :64]
    o = mla_kv_sikistir_ve_ac(O.liste(h[t]), O.liste(q0), O.liste(W_dkv), O.liste(W_uk), O.liste(W_uv))
    c = h[t] @ W_dkv
    ref = {"c_kv": c, "k_c": c @ W_uk, "v_c": c @ W_uv, "q_emilmis": W_uk @ q0}
    sikistir_fark = max(O.goreli_fark(o[a], O.liste(v)) for a, v in ref.items())
    skor_fark = abs(o["dikkat_skoru"] - float(ref["q_emilmis"] @ c))
    tam_k = (h[t] @ M)[:64]
    yaklasim_hata = float((ref["k_c"] - tam_k).norm() / tam_k.norm())

    # Decoupled RoPE: içerik skoru latent üzerinden, konum skoru küçük RoPE'lu ayrı boyutlarla
    dr = AYAR["d_rope"]
    with torch.no_grad():
        cos, sin = model.model.rotary_emb(h.float().unsqueeze(0), torch.arange(T).unsqueeze(0))
    qr = q_tum[:, 64 - dr:64].unsqueeze(0).unsqueeze(0).float()
    kr = (h @ M)[:, 64 - dr:64].unsqueeze(0).unsqueeze(0).float()
    qr, kr = LL.apply_rotary_pos_emb(qr, kr, cos[..., :dr], sin[..., :dr])
    qr, kr = qr[0, 0].double(), kr[0, 0].double()
    c_gecmis = h @ W_dkv
    od = mla_bellek_ve_dikkat(O.liste(ref["q_emilmis"]), O.liste(qr[t]), O.liste(c_gecmis), O.liste(kr), 64)
    sk = (c_gecmis @ ref["q_emilmis"] + kr @ qr[t]) / (64 + dr) ** 0.5
    w = torch.softmax(sk, 0)
    dikkat_fark = max(O.goreli_fark(od["dikkat_agirliklari"], O.liste(w)), O.goreli_fark(od["latent_cikti"], O.liste(w @ c_gecmis)))

    # Rank – perplexity – KV-cache dengesi (tüm katmanlar)
    with torch.no_grad():
        ppl0 = float(torch.exp(model(ids, labels=ids).loss))
    C = _kalibrasyon(torch, tok, model)
    egri = []
    for rr in AYAR["ranklar"]:
        e = {"rank": rr, "kv_sayi_token": 30 * (rr + dr), "enerji_orani": float((S[:rr] ** 2).sum() / (S ** 2).sum())}
        for ad, cc in (("ppl_agirlik_svd", None), ("ppl_aktivasyon_svd", C)):
            m = _dusuk_rank_model(torch, model, rr, cc)
            with torch.no_grad():
                e[ad] = float(torch.exp(m(ids, labels=ids).loss))
            del m
        egri.append(e)
    gqa_sayi = 30 * 2 * 3 * 64
    yarim = [e for e in egri if e["rank"] == 192][0]
    tersine = _kv_tersine(torch, tok, model)
    tr = {k_: v["token_dogrulugu"] for k_, v in tersine["rank"].items()}
    return {
        "model": {k2: bilgi[k2] for k2 in ("model", "revizyon", "agirlik_sha256", "parametre")}, "surumler": O.surumler(),
        "katman": k, "rank": r, "token": T, "tekil_degerler_ilk8": [float(v) for v in S[:8]],
        "sikistir_goreli_fark": sikistir_fark, "skor_fark": skor_fark, "emilim_esdeger": o["emilim_esdeger_mi"],
        "mla_ayni": sikistir_fark <= 1e-5 and skor_fark <= 1e-4 and o["emilim_esdeger_mi"],
        "rank_r_k_goreli_hata": yaklasim_hata, "dikkat_goreli_fark": dikkat_fark, "dikkat_ayni": dikkat_fark <= 1e-5,
        "ppl_tam": ppl0, "rank_egrisi": egri, "kv_sayi_token_gqa": gqa_sayi,
        "tam_rank_ayni": abs(egri[-1]["ppl_agirlik_svd"] - ppl0) <= 1e-3 * ppl0,
        "aktivasyon_svd_daha_iyi": yarim["ppl_aktivasyon_svd"] < yarim["ppl_agirlik_svd"],
        "kv_tersine": tersine, "kv_sizdiriyor": tr["tam_kv"] >= 0.7 and tr["128"] > 0.2 and tr["32"] < tr["128"] < tr["tam_kv"],
        "olcum": (f"SmolLM2 {k}. katman ortak [W_k | W_v] (576×384) SVD, rank {r}: öğrencinin MLA sıkıştırma/açma çıktıları torch'tan göreli "
                  f"{sikistir_fark:.1e}, emilmiş skor farkı {skor_fark:.1e}; head 0 anahtarının rank {r} yaklaşım hatası {yaklasim_hata:.2f}. "
                  f"Decoupled RoPE'lu latent dikkat torch'tan {dikkat_fark:.1e}. Tüm katmanlarda rank → perplexity (tam {ppl0:.1f}; ağırlık SVD / "
                  f"aktivasyon farkında SVD): " + ", ".join(f"{e['rank']}→{e['ppl_agirlik_svd']:.1f}/{e['ppl_aktivasyon_svd']:.1f}" for e in egri) +
                  f". KV önbelleğini tersine çevirme ({AYAR['tersine_katman']}. katman, doğrusal eşleme): gizli cümlenin token doğruluğu "
                  + ", ".join(f"{k_}: %{100 * v:.0f}" for k_, v in tr.items()) + "."),
        "sinir": ("SmolLM2 MLA ile eğitilmemiştir: latent, eğitim sonrası SVD ile çıkarılır (ince ayar yok), bu yüzden düşük rankta kalite "
                  "kaybı MLA ile eğitilmiş bir modelden büyüktür. Decoupled RoPE boyutları sorgu/anahtarın son 16 boyutundan alınır; gerçek "
                  "DeepSeek'te ayrı projeksiyonlardır. KV boyutu yalnız sayı adedi olarak verilir."),
    }


def goster(mla_kv_sikistir_ve_ac, mla_bellek_ve_dikkat):
    r = deney(mla_kv_sikistir_ve_ac, mla_bellek_ve_dikkat)
    print("MLA sıkıştır/aç göreli fark: %.1e | emilim eşdeğer: %s | skor farkı %.1e" % (r["sikistir_goreli_fark"], r["emilim_esdeger"], r["skor_fark"]))
    print("Decoupled RoPE latent dikkat farkı: %.1e" % r["dikkat_goreli_fark"])
    print("rank  ppl (ağırlık SVD)  ppl (aktivasyon SVD)  KV sayı/token  enerji")
    for e in r["rank_egrisi"]:
        print("%4d  %17.2f  %20.2f  %13d  %.3f" % (e["rank"], e["ppl_agirlik_svd"], e["ppl_aktivasyon_svd"], e["kv_sayi_token"], e["enerji_orani"]))
    print("Tam model perplexity: %.2f" % r["ppl_tam"])
    print("KV tersine çevirme (rank → token doğruluğu):", {k: round(v["token_dogrulugu"], 3) for k, v in r["kv_tersine"]["rank"].items()},
          "| örnek:", repr(r["kv_tersine"]["geri_cikan_ornek"]))
    print("Sınır:", r["sinir"])
    print("Kanıt:", O.kanit("ai-uretim-17", "run", r))
