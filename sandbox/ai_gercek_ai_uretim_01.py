# -*- coding: utf-8 -*-
"""ai-uretim-01 gerçek deney: öğrencinin skaler geri yayılımı ve linear katman gradyanları gerçek SmolLM2 değerleriyle
torch.autograd'a karşı sınanır; tek örnekli gradyandan gerçek bir token gömmesinin birebir geri çıkarıldığı gösterilir."""
import ai_lab
from sandbox import ai_uretim_ortak as O

AYAR = {"metin": "The admin changed the router settings and saved the new configuration file.", "katman": 2,
        "gizli_kelime": " password", "neuron_aday": list(range(0, 64)), "lin_satir": [1, 4, 6], "lin_din": 16, "lin_dout": 8}


def _ref_graf_ve_grad(torch, xs, ws, b):
    xt = [torch.tensor(v, dtype=torch.float64, requires_grad=True) for v in xs]
    wt = [torch.tensor(v, dtype=torch.float64, requires_grad=True) for v in ws]
    bt = torch.tensor(b, dtype=torch.float64, requires_grad=True)
    s = xt[0] * wt[0]
    for x, w in zip(xt[1:], wt[1:]):
        s = s + x * w
    z = s + bt + xt[0]                 # x0 iki kez kullanılır (fan-out: gradyan birikmeli)
    L = torch.relu(z)
    L.backward()
    return float(z.detach()), {**{f"x{i}": float(x.grad) for i, x in enumerate(xt)}, **{f"w{i}": float(w.grad) for i, w in enumerate(wt)},
                      "b": float(bt.grad)}


def deney(geriye_yayilim, linear_geri_yayilim):
    torch = O.torch_al()
    tok, model, bilgi = O.smol()
    k = AYAR["katman"]
    ids = tok(AYAR["metin"], return_tensors="pt").input_ids
    with torch.no_grad():
        hs = model(ids, output_hidden_states=True).hidden_states[k][0].double()
    gate = model.model.layers[k].mlp.gate_proj.weight.detach().double()

    # 1) Skaler graf: L = relu(sum x_i w_i + b + x_0), gerçek gizli durum ve gerçek gate nöronu (z > 0 olan ilk nöron)
    tok_i = 3
    for n in AYAR["neuron_aday"]:
        xs, ws, b = [float(v) for v in hs[tok_i, :6]], [float(v) for v in gate[n, :6]], 0.1
        z_ref, g_ref = _ref_graf_ve_grad(torch, xs, ws, b)
        if z_ref > 0.05:
            break
    dug = [{"id": f"x{i}", "op": "leaf", "inputs": [], "val": xs[i]} for i in range(6)]
    dug += [{"id": f"w{i}", "op": "leaf", "inputs": [], "val": ws[i]} for i in range(6)] + [{"id": "b", "op": "leaf", "inputs": [], "val": b}]
    dug += [{"id": f"u{i}", "op": "mul", "inputs": [f"x{i}", f"w{i}"]} for i in range(6)]
    onceki = "u0"
    for i in range(1, 6):
        dug.append({"id": f"s{i}", "op": "add", "inputs": [onceki, f"u{i}"]})
        onceki = f"s{i}"
    dug += [{"id": "sb", "op": "add", "inputs": [onceki, "b"]}, {"id": "z", "op": "add", "inputs": ["sb", "x0"]},
            {"id": "L", "op": "relu", "inputs": ["z"]}]
    g_ogr = geriye_yayilim(dug, "L")
    graf_fark = max(abs(g_ogr.get(a, float("inf")) - v) for a, v in g_ref.items())

    # 2) Linear katman: gerçek gizli durumlar ve gerçek q_proj dilimi; dY gerçek bir kaybın gradyanı (torch)
    X = hs[AYAR["lin_satir"], :AYAR["lin_din"]].clone().requires_grad_(True)
    W = model.model.layers[k].self_attn.q_proj.weight.detach().double().T[:AYAR["lin_din"], :AYAR["lin_dout"]].clone().requires_grad_(True)
    bb = torch.zeros(AYAR["lin_dout"], dtype=torch.float64, requires_grad=True)
    T = hs[[2, 5, 7], :AYAR["lin_dout"]]
    Y = X @ W + bb
    Y.retain_grad()
    ((Y - T) ** 2).sum().backward()
    o = linear_geri_yayilim(O.liste(X), O.liste(W), O.liste(Y.grad))
    lin_fark = max(O.goreli_fark(o["dX"], O.liste(X.grad)), O.goreli_fark(o["dW"], O.liste(W.grad)), O.goreli_fark(o["db"], O.liste(bb.grad)))

    # 3) Gradyan sızıntısı: tek örnekli batch'te dW[:, o] / db[o] girdinin kendisidir
    gizli_id = tok(AYAR["gizli_kelime"], add_special_tokens=False).input_ids[0]
    E = model.model.embed_tokens.weight.detach().double()
    x = E[gizli_id]
    Wg = gate.T[:, :4]
    c = [0.5, -1.0, 2.0, 1.25]                 # bilinmeyen kayıptan gelen dY (sunucu yalnız gradyanı görür)
    o2 = linear_geri_yayilim([O.liste(x)], O.liste(Wg), [c])
    x_hat = torch.tensor([row[2] for row in o2["dW"]], dtype=torch.float64) / o2["db"][2]
    sizinti_hata = float((x_hat - x).abs().max())
    en_yakin = int(torch.nn.functional.cosine_similarity(E, x_hat.unsqueeze(0)).argmax())
    return {
        "model": {k2: bilgi[k2] for k2 in ("model", "revizyon", "agirlik_sha256", "parametre")}, "surumler": O.surumler(),
        "graf_noron": n, "graf_z": z_ref, "graf_en_buyuk_fark": graf_fark, "graf_ayni": graf_fark <= 1e-5,
        "x0_fanout_grad": g_ref["x0"], "linear_goreli_fark": lin_fark, "linear_ayni": lin_fark <= 1e-5,
        "gizli_token": AYAR["gizli_kelime"], "gizli_id": int(gizli_id), "geri_cikan_id": en_yakin,
        "geri_cikan_token": tok.decode([en_yakin]), "sizinti_en_buyuk_hata": sizinti_hata,
        "sizinti_token_ayni": en_yakin == int(gizli_id), "sizinti_hassas": sizinti_hata <= 1e-4,
        "olcum": (f"SmolLM2 {k}. katman: skaler graf (gate nöronu {n}, z={z_ref:.4f}) autograd farkı {graf_fark:.1e}; linear dX/dW/db göreli "
                  f"fark {lin_fark:.1e}. Tek örnekli gradyandan geri çıkarılan gömme en büyük hata {sizinti_hata:.1e}, en yakın token "
                  f"{tok.decode([en_yakin])!r} (gizli: {AYAR['gizli_kelime']!r})."),
        "sinir": ("Sızıntı tek örnekli batch ve bias'lı doğrusal katman için kesindir; büyük batch'te ve derin ağlarda optimizasyonla yaklaşık "
                  "geri çıkarma gerekir (ai-guvence-44 DLG). Skaler graf yalnız add/mul/relu işlemlerini içerir."),
    }


def goster(geriye_yayilim, linear_geri_yayilim):
    r = deney(geriye_yayilim, linear_geri_yayilim)
    print("Skaler graf farkı (autograd): %.2e | x0 fan-out gradyanı: %.6f" % (r["graf_en_buyuk_fark"], r["x0_fanout_grad"]))
    print("Linear katman göreli fark: %.2e" % r["linear_goreli_fark"])
    print("Gradyan sızıntısı: gizli %r → geri çıkan %r (en büyük hata %.1e)" % (r["gizli_token"], r["geri_cikan_token"], r["sizinti_en_buyuk_hata"]))
    print("Sınır:", r["sinir"])
    print("Kanıt:", O.kanit("ai-uretim-01", "run", r))
