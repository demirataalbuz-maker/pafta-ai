# -*- coding: utf-8 -*-
"""ai-guvence-07 gerçek deney referansları: autograd ile FGSM ve ε-doğruluk eğrisi.

Model ve test kümesi ``ai_gercek_lab.fgsm_siniflandirici()`` ile CPU'da gerçekten eğitilir. Bu modüldeki
işlevler yalnız test içindir; öğrenci kodunun bunları import etmesi veya kopyalaması Kontrol'de reddedilir.
"""


def fgsm_referans(model, x, y, eps):
    """Ortalama çapraz entropinin girdiye göre gradyan işaretiyle tek adım, [0, 1] kırpması."""
    import torch
    import torch.nn.functional as F
    x0 = x.clone().detach().requires_grad_(True)
    gradyan, = torch.autograd.grad(F.cross_entropy(model(x0), y), x0)
    return (x0.detach() + eps * gradyan.sign()).clamp(0, 1)


def _dogruluk(model, x, y):
    import torch
    with torch.no_grad():
        return (model(x).argmax(1) == y).float().mean().item()


def epsilon_egrisi_referans(model, x, y, epsler):
    """Her ε için temiz/bozuk doğruluk ve gerçekleşen L∞ (sıra korunur)."""
    temiz = _dogruluk(model, x, y)
    sonuc = []
    for eps in epsler:
        bozuk = fgsm_referans(model, x, y, eps)
        sonuc.append({"eps": eps, "temiz_dogruluk": temiz, "bozuk_dogruluk": _dogruluk(model, bozuk, y),
                      "linf": float((bozuk - x).abs().max())})
    return sonuc
