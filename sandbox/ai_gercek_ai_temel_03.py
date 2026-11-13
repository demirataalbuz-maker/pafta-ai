"""Ders03 gerçek dağılım referansı; öğrenci çözümüne kopyalanamaz."""
import torch
import ai_lab
import math

def referans_dagilim(metin, k=5, sicaklik=1.0):
    if not isinstance(metin, str) or not metin.strip():
        raise ValueError("metin boş olamaz")
    if isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= 20:
        raise ValueError("k 1-20 arası tamsayı olmalı")
    if isinstance(sicaklik, bool) or not isinstance(sicaklik, (int, float)) or not math.isfinite(sicaklik) or not sicaklik > 0:
        raise ValueError("sıcaklık pozitif olmalı")
    tokenizer, model, _ = ai_lab.dil_modeli()
    ids = tokenizer(metin)["input_ids"]
    with torch.no_grad():
        logit = model(torch.tensor([ids])).logits[0, -1].double()
    p = torch.softmax(logit / sicaklik, dim=0)
    en = sorted(torch.topk(p, k + 5).indices.tolist(), key=lambda i: (-p[i].item(), i))[:k]
    return {"token_idleri": ids, "tokenlar": tokenizer.convert_ids_to_tokens(ids),
            "en_olasi": [{"id": i, "metin": tokenizer.decode([i]), "logit": logit[i].item(), "olasilik": p[i].item()}
                         for i in en],
            "olasilik_toplami": p.sum().item()}

