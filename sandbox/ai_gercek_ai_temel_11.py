"""ai-temel-11: real frozen LM logits + trainable token-bias policy.

No fixtures, downloads or server calls. Only this lesson imports this helper.
The base LM is evaluated once per prompt; only an additive output bias trains.
"""
import hashlib
import random


def hazirla():
    import torch
    from sandbox import ai_gercek_lab as lab
    tok, model, bilgi = lab.dil_modeli()
    seed = random.SystemRandom().randrange(1, 2**31)
    rng = random.Random(seed)
    pairs = [(' yes', ' no'), (' left', ' right'), (' red', ' blue')]
    contexts = [f'Training sample {rng.randrange(10000,99999)}: choose a label.',
                f'An invented direction exercise {rng.randrange(10000,99999)}: choose a label.',
                f'An invented color exercise {rng.randrange(10000,99999)}: choose a label.']
    bases, cases, raw = {}, [], []
    for prompt, (chosen, rejected) in zip(contexts, pairs):
        ids = tok(prompt, add_special_tokens=False)['input_ids']
        cs=tok(chosen,add_special_tokens=False)['input_ids']
        rs=tok(rejected,add_special_tokens=False)['input_ids']
        if len(cs)!=1 or len(rs)!=1:raise lab.GercekLabYok('Bu deney tek tokenlık tamamlamalar ister.')
        c,r=cs[0],rs[0]
        if c == r:
            raise lab.GercekLabYok('Seçilen ve reddedilen gerçek token kimlikleri aynı.')
        with torch.no_grad():
            logits = model(torch.tensor([ids]), use_cache=False).logits[0, -1].double().detach().clone()
        bases[prompt] = logits
        cases.append({'prompt': prompt, 'chosen': c, 'rejected': r})
        raw.append({'prompt': prompt, 'token_idleri': ids, 'chosen': c, 'rejected': r,
                    'chosen_metin': tok.decode([c]), 'rejected_metin': tok.decode([r]),
                    'chosen_logit': logits[c].item(), 'rejected_logit': logits[r].item(),
                    'logit_sha256': hashlib.sha256(logits.numpy().tobytes()).hexdigest()})
    info = dict(bilgi, uyarlama='Yalnız sözlük boyutlu ek çıktı biası; LM ağırlıkları eğitilmez.',
                protokol='Gerçek son-konum logitleri; tek tokenlık chosen/rejected tamamlamalar.',
                veri_tohumu=seed, gercek_cagrilar=raw)
    return bases, cases, info


def modeller(bases, lr):
    import torch
    class Politika(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.token_bias = torch.nn.Parameter(torch.zeros_like(next(iter(bases.values()))))
        def forward(self, prompt):
            return bases[prompt] + self.token_bias
    class Referans(torch.nn.Module):
        def forward(self, prompt):
            return bases[prompt].clone()
    policy, reference = Politika(), Referans()
    return policy, reference, torch.optim.SGD(policy.parameters(), lr=lr, momentum=0, weight_decay=0)


def analitik(bases,vakalar,beta,adim,lr):
    import torch,math
    bias=torch.zeros_like(next(iter(bases.values())))
    losses=[]
    for _ in range(adim):
        grad=torch.zeros_like(bias)
        total=0.0
        for v in vakalar:
            c,r=v["chosen"],v["rejected"]
            margin=float((bias[c]-bias[r]).item())
            z=beta*margin
            total+=max(-z,0)+math.log1p(math.exp(-abs(z)))
            g=-beta/(1+math.exp(z))/len(vakalar)
            grad[c]+=g;grad[r]-=g
        losses.append(total/len(vakalar))
        bias=bias-lr*grad
    return {"kayiplar":losses,"son_marjlar":[float((bias[v["chosen"]]-bias[v["rejected"]]).item()) for v in vakalar]},bias

def goster(fn):
    from sandbox import ai_gercek_lab as lab
    import torch
    bases,vs,bilgi=hazirla()
    p,r,opt=modeller(bases,0.1)
    gozlem={"gradyan":0,"adim":0,"referans_grad_acik":[]}
    def gr(g):gozlem["gradyan"]+=1
    def st(*a):gozlem["adim"]+=1
    def rf(*a):gozlem["referans_grad_acik"].append(torch.is_grad_enabled())
    handles=[p.token_bias.register_hook(gr),opt.register_step_post_hook(st),r.register_forward_hook(rf)]
    try:d=fn(p,r,opt,vs,0.4,3)
    finally:
        for h in handles:h.remove()
    ids=sorted({v[k] for v in vs for k in ("chosen","rejected")})
    bias={str(i):p.token_bias[i].item() for i in ids}
    print("Gerçek tercihler:",bilgi["gercek_cagrilar"])
    print("DPO sonucu:",d,"bias:",bias,"gözlem:",gozlem)
    lab.kanit_yaz("temel-11-dpo-calistir",{"kaynak":"gercek","kabul":False,"model_bilgisi":bilgi,"ayarlar":{"beta":0.4,"adim":3,"lr":0.1,"vakalar":vs},"ciktilar":d,"bias_ozeti":bias,"olculen":gozlem,"sinir":"tek-token ek bias eğitimi; Çalıştır kabul değildir; tam LM fine-tuning/güvenlik ölçülmez","temizlik":"CPU, kalıcı süreç veya model dosyası değişikliği yok"})
