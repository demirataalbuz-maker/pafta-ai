# -*- coding: utf-8 -*-
"""ai-uretim-14 gerçek deney: öğrencinin BF16/E4M3 yuvarlaması SmolLM2'nin gerçek ağırlıklarında torch'un bfloat16 ve
float8_e4m3fn dönüşümüyle bit bit karşılaştırılır; blok ölçekli nicemleme gerçek ağırlıklarda ölçülür; kararlı
logsumexp ve cross-entropy 49 152 sözcüklük gerçek logit'lerde torch ile karşılaştırılır. Son olarak tüm doğrusal
katmanlar FP8'e nicemlenip perplexity'ye etkisi ölçülür (blok ölçek ve tensör ölçek)."""
import copy, random
import ai_lab
from sandbox import ai_uretim_ortak as O

AYAR = {"seed": 14, "eleman": 1500, "blok": 128,
        "istemler": ["The safest way to store passwords is", "To disable the antivirus on a work laptop, you", "Q: Is it legal to scan a network you do not own? A:",
                     "The capital of Australia is", "If a stranger asks for your one-time code, you should"], "metin": ("Backups protect a company only if someone regularly checks that they can be restored. "
        "Many teams discover during an incident that the nightly job had been failing silently for weeks, or that the "
        "restore procedure depends on a password nobody remembers. A short monthly drill avoids most of these surprises.")}


def _fp8_model(torch, model, blok, int8=False):
    m = copy.deepcopy(model)
    with torch.no_grad():
        for mod in m.modules():
            if isinstance(mod, torch.nn.Linear) and mod.weight.shape[0] != m.config.vocab_size:
                W = mod.weight
                if int8:                                    # karşılaştırma: tensör ölçekli simetrik INT8 (255 seviye)
                    s = W.abs().amax().clamp(min=1e-12) / 127.0
                    W.copy_(torch.clamp(torch.round(W / s), -127, 127) * s)
                elif blok:
                    v = W.view(-1, blok)
                    s = v.abs().amax(1, keepdim=True).clamp(min=1e-12) / 448.0
                    W.copy_(((v / s).to(torch.float8_e4m3fn).float() * s).view_as(W))
                else:
                    s = W.abs().amax().clamp(min=1e-12) / 448.0
                    W.copy_((W / s).to(torch.float8_e4m3fn).float() * s)
    return m


def _ppl(torch, model, ids):
    with torch.no_grad():
        return float(torch.exp(model(ids, labels=ids).loss))


def deney(fp8_blok_nicele, kararli_logsumexp_kayip, bf16_ve_e4m3_yuvarla):
    torch = O.torch_al()
    if not hasattr(torch, "float8_e4m3fn"):
        raise ai_lab.GercekLabYok("bu torch sürümünde float8_e4m3fn yok")
    tok, model, bilgi = O.smol()
    rnd = random.Random(AYAR["seed"])
    W = model.model.layers[7].mlp.down_proj.weight.detach().reshape(-1)
    idx = [rnd.randrange(W.numel()) for _ in range(AYAR["eleman"])]
    ham = [float(W[i]) for i in idx]
    blok = W[: AYAR["blok"]].double()
    s = float(blok.abs().max()) / 448.0
    olcekli = [float(v) / s for v in blok]

    # 1) BF16 ve E4M3: hem ham ağırlıklar (E4M3'te alt normal bölge) hem blok ölçekli değerler
    bf_fark, e4_fark, e4_fark_ornek = 0, 0, []
    for x in ham + olcekli:
        o = bf16_ve_e4m3_yuvarla(x)
        bf_t = float(torch.tensor(x, dtype=torch.float32).to(torch.bfloat16).float())
        e4_t = float(torch.tensor(x, dtype=torch.float32).to(torch.float8_e4m3fn).float())
        bf_fark += o["bf16"] != bf_t
        if o["e4m3"] != e4_t:
            e4_fark += 1
            if len(e4_fark_ornek) < 3:
                e4_fark_ornek.append({"x": x, "ogrenci": o["e4m3"], "torch": e4_t})
    ham_e4_hata = sum(bf16_ve_e4m3_yuvarla(x)["e4m3_goreli_hata"] for x in ham) / len(ham)
    olcekli_e4_hata = sum(bf16_ve_e4m3_yuvarla(x)["e4m3_goreli_hata"] for x in olcekli) / len(olcekli)

    # 2) Blok nicemleme (tamsayı ızgarası) gerçek blokta; aynı ölçekle gerçek E4M3 ızgarası
    o = fp8_blok_nicele([float(v) for v in blok], 448.0)
    ref_q = torch.clamp(torch.round(blok / s), -448, 448)
    ref_mae = float((blok - ref_q * s).abs().mean())
    e4_mae = float((blok - (blok / s).float().to(torch.float8_e4m3fn).double() * s).abs().mean())
    blok_ayni = abs(o["mae"] - ref_mae) <= 2e-6 and abs(o["olcek"] - s) <= 1e-6

    # 3) Kararlı logsumexp: gerçek 49 152 logit
    ids = tok(AYAR["metin"], return_tensors="pt").input_ids
    with torch.no_grad():
        lg = model(ids).logits[0, 10].double()
    hedef = int(ids[0, 11])
    lgt = lg.clone().requires_grad_(True)
    kayip_t = torch.nn.functional.cross_entropy(lgt.unsqueeze(0), torch.tensor([hedef]))
    kayip_t.backward()
    k = kararli_logsumexp_kayip(O.liste(lg), hedef)
    lse_fark = abs(k["lse"] - float(torch.logsumexp(lg, 0)))
    kayip_fark = abs(k["kayip"] - kayip_t.item())
    grad_fark = O.en_buyuk_fark(k["logit_gradyanlari"], O.liste(lgt.grad))
    naif16 = torch.exp(lg.half())
    naif_inf = int(torch.isinf(naif16).sum())
    naif_kayip = float(-torch.log(naif16[hedef] / naif16.sum()))

    # 4) Tüm doğrusal katmanlar FP8 (E4M3): blok ölçek ve tensör ölçek perplexity
    ppl32 = _ppl(torch, model, ids)
    m_blok = _fp8_model(torch, model, AYAR["blok"])
    ppl_blok = _ppl(torch, m_blok, ids)
    ppl_tensor = _ppl(torch, _fp8_model(torch, model, None), ids)
    m_int8 = _fp8_model(torch, model, None, int8=True)
    ppl_int8 = _ppl(torch, m_int8, ids)

    # 5) Davranış ayrışması: nicemlenmiş model ayrı bir modeldir; aynı istemlerde açgözlü üretim ve sonraki token kararları
    def uret(m, istem):
        x = tok(istem, return_tensors="pt").input_ids
        with torch.no_grad():
            g = m.generate(x, attention_mask=torch.ones_like(x), do_sample=False, max_new_tokens=16, pad_token_id=tok.eos_token_id)
        return g[0, x.shape[1]:].tolist()
    with torch.no_grad():
        top32 = model(ids).logits[0].argmax(-1)
        topb = m_blok(ids).logits[0].argmax(-1)
        topi = m_int8(ids).logits[0].argmax(-1)
    ayrisma = {"fp8_blok_token_farki": float((top32 != topb).float().mean()), "int8_token_farki": float((top32 != topi).float().mean())}
    uretim = []
    for istem in AYAR["istemler"]:
        a, b, c = uret(model, istem), uret(m_blok, istem), uret(m_int8, istem)
        uretim.append({"istem": istem, "fp32": tok.decode(a), "fp8_blok_farkli": a != b, "int8_farkli": a != c})
    ayrisma["fp8_blok_farkli_uretim"] = sum(u["fp8_blok_farkli"] for u in uretim)
    ayrisma["int8_farkli_uretim"] = sum(u["int8_farkli"] for u in uretim)
    return {
        "model": {k2: bilgi[k2] for k2 in ("model", "revizyon", "agirlik_sha256", "parametre")}, "surumler": O.surumler(),
        "eleman": len(ham) + len(olcekli), "bf16_farkli": bf_fark, "e4m3_farkli": e4_fark, "e4m3_fark_ornek": e4_fark_ornek,
        "yuvarlama_ayni": bf_fark == 0 and e4_fark == 0,
        "ham_agirlik_e4m3_goreli_hata": ham_e4_hata, "olcekli_e4m3_goreli_hata": olcekli_e4_hata,
        "blok_olcek": s, "blok_tamsayi_mae": o["mae"], "blok_tamsayi_mae_torch": ref_mae, "blok_e4m3_mae": e4_mae, "blok_ayni": blok_ayni,
        "lse_fark": lse_fark, "kayip_fark": kayip_fark, "grad_en_buyuk_fark": grad_fark,
        "lse_ayni": lse_fark <= 1e-5 and kayip_fark <= 1e-5 and grad_fark <= 1e-6,
        "naif_fp16_inf": naif_inf, "naif_fp16_kayip": naif_kayip, "kararli_kayip": k["kayip"],
        "ppl_fp32": ppl32, "ppl_fp8_blok": ppl_blok, "ppl_fp8_tensor": ppl_tensor, "ppl_int8_tensor": ppl_int8,
        "fp8_kucuk_kayip": ppl_blok <= 1.1 * ppl32,
        "ayrisma": ayrisma, "uretim_karsilastirma": uretim,
        "nicemleme_davranisi_degistirir": ayrisma["int8_farkli_uretim"] + ayrisma["fp8_blok_farkli_uretim"] > 0 and ayrisma["int8_token_farki"] > 0,
        "olcum": (f"SmolLM2 down_proj'dan {len(ham)} ham ve {len(olcekli)} blok ölçekli değer: BF16 {bf_fark}, E4M3 {e4_fark} farklı "
                  f"(torch ile). E4M3 ortalama göreli hata ham ağırlıkta {ham_e4_hata:.3f} (alt normal bölge), blok ölçekli {olcekli_e4_hata:.3f}. "
                  f"128'lik blokta tamsayı ızgarası MAE {o['mae']:.2e}, E4M3 ızgarası {e4_mae:.2e}. Gerçek logit'lerde LSE farkı {lse_fark:.1e}; "
                  f"naif fp16 exp {naif_inf} sonsuz üretiyor. Perplexity fp32 {ppl32:.2f}, FP8 blok ölçek {ppl_blok:.2f}, FP8 tensör ölçek "
                  f"{ppl_tensor:.2f}, INT8 tensör ölçek {ppl_int8:.2f}. Davranış: sonraki token kararlarının %{100 * ayrisma['fp8_blok_token_farki']:.1f}'i "
                  f"(FP8 blok) ve %{100 * ayrisma['int8_token_farki']:.1f}'i (INT8) fp32'den farklı; {len(uretim)} istemin açgözlü 16 tokenlık "
                  f"üretiminden {ayrisma['fp8_blok_farkli_uretim']} (FP8) ve {ayrisma['int8_farkli_uretim']} (INT8) tanesi değişiyor."),
        "sinir": ("FP8 yalnız ağırlıklara uygulanır ve hesap fp32'de yapılır (FP8 matmul çekirdeği, aktivasyon nicemlemesi ve hız ölçülmez); "
                  "perplexity tek bir paragrafta ölçülür. Gömme/çıktı katmanı nicemlenmez."),
    }


def goster(fp8_blok_nicele, kararli_logsumexp_kayip, bf16_ve_e4m3_yuvarla):
    r = deney(fp8_blok_nicele, kararli_logsumexp_kayip, bf16_ve_e4m3_yuvarla)
    print("BF16 / E4M3 torch'tan farklı eleman: %d / %d (toplam %d)" % (r["bf16_farkli"], r["e4m3_farkli"], r["eleman"]))
    print("E4M3 göreli hata  ham ağırlık: %.3f | blok ölçekli: %.3f" % (r["ham_agirlik_e4m3_goreli_hata"], r["olcekli_e4m3_goreli_hata"]))
    print("Blok MAE  tamsayı ızgarası: %.2e (torch %.2e) | E4M3: %.2e" % (r["blok_tamsayi_mae"], r["blok_tamsayi_mae_torch"], r["blok_e4m3_mae"]))
    print("LSE / kayıp / gradyan farkı: %.1e / %.1e / %.1e | naif fp16 exp sonsuz: %d" % (r["lse_fark"], r["kayip_fark"], r["grad_en_buyuk_fark"], r["naif_fp16_inf"]))
    print("Perplexity  fp32: %.2f | FP8 blok: %.2f | FP8 tensör: %.2f | INT8 tensör: %.2f" % (r["ppl_fp32"], r["ppl_fp8_blok"], r["ppl_fp8_tensor"], r["ppl_int8_tensor"]))
    print("Davranış ayrışması:", r["ayrisma"])
    for u in r["uretim_karsilastirma"]:
        print("  %-55s FP8 farklı: %-5s INT8 farklı: %s" % (u["istem"][:55], u["fp8_blok_farkli"], u["int8_farkli"]))
    print("Sınır:", r["sinir"])
    print("Kanıt:", O.kanit("ai-uretim-14", "run", r))
