"""Real residual-stream direction extraction for lesson 15. No downloads."""
import hashlib


def agirlik_ozeti(model):
    h = hashlib.sha256()
    for name, p in model.named_parameters():
        h.update(name.encode('utf-8') + b'\0')
        h.update(p.detach().contiguous().cpu().numpy().tobytes())
    return h.hexdigest()


def hazirla():
    import torch
    from sandbox import ai_gercek_lab as lab
    tok, model, info = lab.dil_modeli()
    layers = getattr(getattr(model, 'model', None), 'layers', None)
    if layers is None or len(layers) < 4:
        raise lab.GercekLabYok('Bu deney Llama-benzeri decoder katmanları gerektirir.')
    positive = ['The report is calm and clear.', 'A quiet and careful explanation.']
    negative = ['The report is urgent and loud.', 'A hurried and noisy explanation.']
    directions, records = {}, []
    for index in (0, 2):
        groups = []
        raw_groups=[]
        for texts in (positive, negative):
            states = []
            for text in texts:
                found = []
                def capture(module, args, output):
                    tensor = output[0] if isinstance(output, tuple) else output
                    found.append(tensor[0, -1].detach().double().clone())
                handle = layers[index].register_forward_hook(capture)
                try:
                    with torch.no_grad():
                        ids = tok(text, add_special_tokens=False)['input_ids']
                        model(torch.tensor([ids]), use_cache=False)
                finally:
                    handle.remove()
                states.append(found[0])
            raw_groups.append([v.tolist() for v in states])
            groups.append(torch.stack(states).mean(0))
        direction = groups[0]-groups[1]
        norm = torch.linalg.vector_norm(direction)
        if not bool(torch.isfinite(norm)) or norm.item() == 0:
            raise lab.GercekLabYok('Gerçek aktivasyon farkından sıfır/sonlu olmayan yön çıktı.')
        direction = (direction/norm).detach()
        directions[index] = direction
        records.append({'katman': index, 'pozitif': positive, 'negatif': negative,
                        'fark_normu': norm.item(), 'yon_normu': torch.linalg.vector_norm(direction).item(),
                        'yon_sha256': hashlib.sha256(direction.numpy().tobytes()).hexdigest(),
                        'boyut': direction.numel(), 'gercek_aktivasyonlar':raw_groups,'birim_yon':direction.tolist()})
    return tok, model, directions, dict(info, yon_cikarma=records,
        sinir='Sentetik karşıt metinlerin aktivasyon farkı; semantik/refusal veya güvenlik yönü kabulü değil.')


def referans_yurut(t,m,text,d,k,a,e,hepsi=False):
    import torch
    ids=t(text,add_special_tokens=False)["input_ids"]
    with torch.no_grad():
        before=m(torch.tensor([ids]),use_cache=False).logits[0,-1].double()
    delta=a*d
    norm=torch.linalg.vector_norm(delta)
    clipped=bool(norm.item()>e)
    if clipped:delta=delta*(e/norm)
    actual=[];norms=[]
    def steer(module,args,out):
        h=out[0] if isinstance(out,tuple) else out
        new=h.clone();step=delta.to(dtype=h.dtype,device=h.device)
        if hepsi:new+=step
        else:new[:,-1,:]+=step
        actual.append(new.detach().clone())
        norms.append(torch.linalg.vector_norm((new[:,-1,:]-h[:,-1,:]).double()).item())
        return (new,)+out[1:] if isinstance(out,tuple) else new
    handle=m.model.layers[k].register_forward_hook(steer)
    try:
        with torch.no_grad():after=m(torch.tensor([ids]),use_cache=False).logits[0,-1].double()
    finally:handle.remove()
    return {"kirpildi":clipped,"kayma_normu":float(norms[0]),"temel_logitler":before[:8].tolist(),
            "yeni_logitler":after[:8].tolist(),"temel_en_olasi":int(before.argmax().item()),
            "yeni_en_olasi":int(after.argmax().item())},actual[0]

def goster(fn):
    import torch
    from sandbox import ai_gercek_lab as lab
    tok,model,yonler,bilgi=hazirla()
    metin="A careful report about a river."
    once=agirlik_ozeti(model)
    iz=[]
    def trace(mod,args,kwargs):
        ids=args[0] if args else kwargs.get("input_ids")
        iz.append({"token_idleri":ids.detach().tolist() if isinstance(ids,torch.Tensor) else None,"grad_acik":torch.is_grad_enabled(),"use_cache":kwargs.get("use_cache")})
    h=model.register_forward_pre_hook(trace,with_kwargs=True)
    hooks=[(len(m._forward_hooks),len(m._forward_pre_hooks)) for m in model.modules()]
    try:out=fn(tok,model,metin,yonler[0],0,0.5,0.2)
    finally:h.remove()
    sonra=agirlik_ozeti(model)
    print("Gerçek son-token steering:",out)
    print("İleri hesap izleri:",iz,"ağırlık değişmedi:",once==sonra)
    lab.kanit_yaz("temel-15-steering-calistir",{"kaynak":"gercek","kabul":False,"model_bilgisi":bilgi,"ayarlar":{"metin":metin,"katman":0,"katsayi":0.5,"esik":0.2},"ciktilar":out,"gercek_forward_izleri":iz,"agirlik_once_sha256":once,"agirlik_sonra_sha256":sonra,"sinir":"Çalıştır keşif kaydı; kabul değil. Evrensel anlam/güvenlik veya tüm model eğitimi ölçülmez.","temizlik":"CPU; kendi izleme hooku kaldırıldı; kalıcı süreç/indirme yok"})
