# -*- coding: utf-8 -*-
"""ai-temel 31–37 gerçek deneylerinin ortak yardımcıları: Pafta ders metinlerinden karakter düzeyinde veri ve sıfırdan
(rastgele başlatılmış) küçük Llama tarzı modellerin eğitimi. İndirme yapılmaz; mimari transformers'ın LlamaForCausalLM
sınıfıdır, ağırlıklar rastgele başlar."""
import time

import ai_lab
from sandbox import ai_uretim_ortak as O
from sandbox.ai_gercek_ai_uretim_18 import uzun_metin


def karakter_verisi(karakter=400_000, dogrulama_orani=0.1):
    torch = O.torch_al()
    metin = uzun_metin(karakter)[:karakter]
    sozluk = sorted(set(metin))
    idx = {c: i for i, c in enumerate(sozluk)}
    veri = torch.tensor([idx[c] for c in metin], dtype=torch.long)
    n = int(len(veri) * (1 - dogrulama_orani))
    return {"metin": metin, "sozluk": sozluk, "egitim": veri[:n], "dogrulama": veri[n:], "egitim_metni": metin[:n], "dogrulama_metni": metin[n:]}


def mini_llama(V, d, L, bas, kv_bas, ff, baglam, seed=0):
    torch = O.torch_al()
    from transformers import LlamaConfig, LlamaForCausalLM
    torch.manual_seed(seed)
    cfg = LlamaConfig(vocab_size=V, hidden_size=d, intermediate_size=ff, num_hidden_layers=L, num_attention_heads=bas,
                      num_key_value_heads=kv_bas, max_position_embeddings=baglam, tie_word_embeddings=True, rms_norm_eps=1e-5,
                      attention_bias=False, mlp_bias=False)
    return LlamaForCausalLM(cfg)


def egit(model, veri, adim, batch, baglam, lr, cihaz, seed=0, degerlendirme_batch=64):
    """AdamW + kosinüs; dönüş: doğrulama kaybı (nat/karakter), eğitim süresi, görülen token."""
    torch = O.torch_al()
    g = torch.Generator().manual_seed(seed)
    model.to(cihaz).train()
    opt = torch.optim.AdamW(model.parameters(), lr=lr, betas=(0.9, 0.95), weight_decay=0.1)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, adim)
    E = veri["egitim"]
    t0 = time.perf_counter()
    for _ in range(adim):
        bas = torch.randint(0, len(E) - baglam - 1, (batch,), generator=g)
        x = torch.stack([E[b:b + baglam + 1] for b in bas]).to(cihaz)
        k = torch.nn.functional.cross_entropy(model(x[:, :-1]).logits.reshape(-1, model.config.vocab_size), x[:, 1:].reshape(-1))
        opt.zero_grad(); k.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step(); sched.step()
    if cihaz == "cuda":
        torch.cuda.synchronize()
    sure = time.perf_counter() - t0
    return {"dogrulama_kaybi": dogrulama_kaybi(model, veri["dogrulama"], baglam, cihaz, degerlendirme_batch), "sure_s": sure,
            "gorulen_token": adim * batch * baglam}


def dogrulama_kaybi(model, D, baglam, cihaz, n_batch=64):
    torch = O.torch_al()
    model.eval()
    parca = [D[i:i + baglam + 1] for i in range(0, len(D) - baglam - 1, baglam)][:n_batch * 4]
    top, say = 0.0, 0
    with torch.no_grad():
        for j in range(0, len(parca), n_batch):
            x = torch.stack(parca[j:j + n_batch]).to(cihaz)
            lg = model(x[:, :-1]).logits
            top += float(torch.nn.functional.cross_entropy(lg.reshape(-1, lg.shape[-1]), x[:, 1:].reshape(-1), reduction="sum"))
            say += x[:, 1:].numel()
    model.train()
    return top / say


def govde_parametre(model):
    """Gömme hariç (non-embedding) parametre sayısı: Kaplan tarzı ölçekleme yasalarındaki N."""
    return sum(p.numel() for n, p in model.named_parameters() if "embed_tokens" not in n and "lm_head" not in n)
