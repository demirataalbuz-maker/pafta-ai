"""Ders09 gerçek eğitim referansı; öğrenci çözümüne kopyalanamaz."""
import ai_lab
import torch

def referans_egit(model, optimizer, x, y, adim):
    if type(adim) is not int or not 1<=adim<=8:
        raise ValueError("adım 1-8 tamsayı olmalı")
    kayiplar=[]
    for _ in range(adim):
        optimizer.zero_grad(set_to_none=True)
        loss=torch.nn.functional.mse_loss(model(x),y,reduction="mean")
        kayiplar.append(float(loss.item()))
        loss.backward()
        optimizer.step()
    return {"kayiplar":kayiplar,"agirlik":model.weight.detach().flatten().tolist(),"bias":float(model.bias.item())}

