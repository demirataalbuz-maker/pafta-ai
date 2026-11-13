# -*- coding: utf-8 -*-
"""SmolLM2 gerçek giriş embedding tablosu; bağımsız ağırlık seçimi ve Run gösterimi."""
import ai_lab


def referans_raporu(metin):
    if not isinstance(metin,str) or not metin.strip():raise ValueError("metin")
    import torch
    tok,model,_=ai_lab.dil_modeli()
    ids=tok(metin,add_special_tokens=False)["input_ids"]
    if not 1<=len(ids)<=16:raise ValueError("token sayısı")
    with torch.no_grad():
        v=model.get_input_embeddings().weight.detach().index_select(0,torch.tensor(ids)).double()
        norm=torch.linalg.vector_norm(v,dim=1,keepdim=True)
        if bool((norm==0).any()):raise ValueError("sıfır norm")
        u=v/norm;cos=u@u.T
    return {"token_idleri":ids,"boyut":v.shape[1],"vektorler":v.tolist(),"kosinus":cos.tolist()}


def goster(fn):
    import torch
    _,model,bilgi=ai_lab.dil_modeli()
    katman_izleri=[];forward_izleri=[]
    h=model.get_input_embeddings().register_forward_pre_hook(lambda *a:katman_izleri.append(torch.is_grad_enabled()))
    f=model.register_forward_pre_hook(lambda *a:forward_izleri.append(True))
    metin=" the the river"
    try:d=fn(metin)
    finally:h.remove();f.remove()
    iz={"embedding_cagrisi":len(katman_izleri),"embedding_grad_acik":any(katman_izleri),"transformer_forward":len(forward_izleri)}
    print("Model:",bilgi["model"],"CPU giriş embedding deneyi")
    print("Ölçülen çağrı izi:",iz)
    print("Metin:",repr(metin),"Token kimlikleri:",d["token_idleri"],"boyut:",d["boyut"])
    print("İlk vektörün ilk6bileşeni:",d["vektorler"][0][:6])
    print("Kosinüs matrisi:",d["kosinus"])
    print("Kanıt:",ai_lab.kanit_yaz("temel-02-embedding-calistir",{"kaynak":"gercek","kabul":False,"ders":"ai-temel-02","model_bilgisi":bilgi,"ayarlar":{"metin":metin,"add_special_tokens":False,"max_token":16,"dtype_hesap":"float64"},"cikti":d,"islem_izi":iz,"temizlik":"CPU;süreç veya dış sunucu açılmadı"}))
