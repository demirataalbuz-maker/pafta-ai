"""Ders08 KV eşdeğerliği için kopyalanması yasak referans."""
import ai_lab
import torch

def referans_kv_deneyi(metin, bolme):
    if not isinstance(metin,str) or not metin.strip() or type(bolme) is not int:
        raise ValueError("metin veya bölme geçersiz")
    tok,model,_=ai_lab.dil_modeli()
    ids=tok(metin,add_special_tokens=False)["input_ids"]
    if not 2<=len(ids)<=24 or not 1<=bolme<len(ids):
        raise ValueError("token sınırı veya bölme geçersiz")
    with torch.no_grad():
        pre=model(torch.tensor([ids[:bolme]]),use_cache=True)
        cache=pre.past_key_values
        once=int(cache.get_seq_length())
        devam=model(torch.tensor([ids[bolme:]]),past_key_values=cache,use_cache=True)
        sonra=int(devam.past_key_values.get_seq_length())
        cache_l=devam.logits[0,-1].double()
        tam=model(torch.tensor([ids]),use_cache=False).logits[0,-1].double()
    return {"token_idleri":ids,"prefill_token":bolme,"devam_token":len(ids)-bolme,
            "cache_once":once,"cache_sonra":sonra,"en_olasi_id":int(cache_l.argmax().item()),
            "cache_logitleri":cache_l[:8].tolist(),"max_logit_farki":float((cache_l-tam).abs().max().item())}

