"""ai-temel-07 için gerçek yerel model raporu ve keşif kaydı. İndirme yok."""
from sandbox import ai_gercek_lab as lab

def referans(metin,butce):
    import torch
    if not isinstance(metin,str) or not metin.strip() or type(butce) is not int or not 1<=butce<=32:
        raise ValueError("metin veya bütçe")
    tok,model,_=lab.dil_modeli()
    sinir=int(model.config.max_position_embeddings)
    if butce>sinir:raise ValueError("model sınırı")
    tum=tok(metin,add_special_tokens=False)["input_ids"]
    ids=tum[-butce:]
    if not ids:raise ValueError("token yok")
    pos=list(range(len(ids)))
    with torch.no_grad():
        out=model(input_ids=torch.tensor([ids]),position_ids=torch.tensor([pos]),use_cache=False).logits[0,-1].double()
    return {"model_siniri":sinir,"girdi_token_sayisi":len(tum),"dusen_token_sayisi":len(tum)-len(ids),"token_idleri":ids,"konumlar":pos,"en_olasi_id":int(out.argmax().item()),"ornek_logitler":out[:8].tolist()}

def goster(fn):
    import torch
    _,model,bilgi=lab.dil_modeli()
    metin="The old instruction was removed; the latest note is green."
    kayit=[]
    def izle(mod,args,kwargs):
        ids=args[0] if args else kwargs.get("input_ids")
        pos=kwargs.get("position_ids")
        kayit.append({"ids":ids.detach().tolist() if isinstance(ids,torch.Tensor) else None,"konumlar":pos.detach().tolist() if isinstance(pos,torch.Tensor) else None,"use_cache":kwargs.get("use_cache"),"grad_acik":torch.is_grad_enabled()})
    h=model.register_forward_pre_hook(izle,with_kwargs=True)
    cikti=[]
    try:
        for butce in (2,8):
            d=fn(metin,butce);cikti.append({"butce":butce,"rapor":d});print("Bütçe",butce,d)
    finally:h.remove()
    lab.kanit_yaz("temel-07-baglam-calistir",{"kaynak":"gercek","kabul":False,"model_bilgisi":bilgi,"ayarlar":{"metin":metin,"butceler":[2,8]},"ciktilar":cikti,"gercek_forward_cagrilari":kayit,"sinir":"Çalıştır keşif kaydı; kabul değildir. Tam context kapasitesi ölçülmez.","temizlik":"CPU; kalıcı süreç veya model indirme yok"})
