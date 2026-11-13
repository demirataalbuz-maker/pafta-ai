# -*- coding: utf-8 -*-
"""ai-temel-04 gerçek deneyi: gerçek SmolLM2 logitlerinde sıcaklık, top-k, top-p ve örnekleme.

Ortak laboratuvar (`ai_lab`) koşucunun kaydettiği modüldür; burada yalnız bu derse özel referans,
bağımsız transformers karşılaştırması ve gösterim vardır.
"""
import ai_lab


def referans(logitler, sicaklik=1.0, k=None, p=1.0, *, sicaklik_kullan=True, sira="kp", esik_dahil=True,
             normalize=True, k_kullan=True):
    """Doğru sonuç (varsayılan argümanlarla) ve testlerin kullandığı hatalı varyantlar."""
    torch = ai_lab._torch()
    z = logitler.double() / (sicaklik if sicaklik_kullan else 1.0)
    olas = torch.softmax(z, dim=0)
    # Kararlı sıralama: olasılık azalan, eşitlikte küçük kimlik önce
    aday = torch.argsort(-olas, stable=True).tolist()
    def kes_k(liste):
        return liste[:k] if (k is not None and k_kullan) else liste
    def kes_p(liste, dagilim):
        secim, toplam = [], 0.0
        for i in liste:
            if not esik_dahil and toplam + dagilim[i].item() > p and secim:
                break
            secim.append(i)
            toplam += dagilim[i].item()
            if toplam >= p:
                break
        return secim
    if sira == "kp":
        aday = kes_k(aday)
        kalan = torch.zeros_like(olas)
        kalan[aday] = olas[aday]
        kalan = kalan / kalan.sum()
        aday = kes_p(aday, kalan)
    else:  # top-p tam dağılımda, sonra top-k
        aday = kes_k(kes_p(aday, olas))
    secili = olas[aday]
    if normalize:
        secili = secili / secili.sum()
    return {"adaylar": aday, "olasiliklar": [float(x) for x in secili.tolist()]}


def hf_referans(logitler, sicaklik, k, p):
    """transformers'ın kendi üretim işlemcileriyle aynı filtre (bağımsız karşılaştırma, yalnız kanıt için)."""
    torch = ai_lab._torch()
    from transformers import TemperatureLogitsWarper, TopKLogitsWarper, TopPLogitsWarper
    s = logitler.double().unsqueeze(0)
    s = TemperatureLogitsWarper(sicaklik)(None, s)
    if k is not None:
        s = TopKLogitsWarper(k)(None, s)
    if p < 1.0:
        s = TopPLogitsWarper(p)(None, s)
    olas = torch.softmax(s[0], dim=0)
    return {i: olas[i].item() for i in torch.nonzero(olas > 0).flatten().tolist()}


def uret(fn, metin, ayar, n=12, seed=0):
    """fn ile adım adım gerçek üretim. ayar None ise greedy. Her adımda aday kümesi boyutu kaydedilir."""
    torch = ai_lab._torch()
    tok, model, _ = ai_lab.dil_modeli()
    ids = tok(metin)["input_ids"]
    g = torch.Generator().manual_seed(seed)
    boyutlar = [];uretilen_idler=[];secim_izi=[]
    for _ in range(n):
        with torch.no_grad():
            logit = model(torch.tensor([ids])).logits[0, -1]
        if ayar is None:
            sonraki = int(torch.argmax(logit))
            boyutlar.append(1);secim_izi.append({"id":sonraki,"olasilik":1.0,"greedy":True})
        else:
            d = fn(logit, **ayar)
            boyutlar.append(len(d["adaylar"]))
            secim = torch.multinomial(torch.tensor(d["olasiliklar"], dtype=torch.float64), 1, generator=g).item()
            sonraki = d["adaylar"][secim]
            secim_izi.append({"id":sonraki,"olasilik":d["olasiliklar"][secim],"greedy":False})
        uretilen_idler.append(sonraki)
        ids.append(sonraki)
        if sonraki == tok.eos_token_id:
            break
    return {"metin": tok.decode(ids[len(tok(metin)["input_ids"]):]), "aday_boyutlari": boyutlar,"uretilen_idler":uretilen_idler,"secim_izi":secim_izi}


DENEY_METNI = "Once upon a time, in a small village,"
DENEY_AYARLARI = [("greedy", None), ("T=0.7, p=0.9", {"sicaklik": 0.7, "p": 0.9}),
                  ("T=1.0, k=50", {"sicaklik": 1.0, "k": 50}), ("T=1.5, p=0.95", {"sicaklik": 1.5, "p": 0.95})]


def kume_boyutlari(fn, metin=DENEY_METNI):
    _, logit = ai_lab.son_logitler(metin)
    return {f"T={T}, p={p}": len(fn(logit.float(), sicaklik=T, p=p)["adaylar"])
            for T in (0.5, 1.0, 1.5) for p in (0.5, 0.9)}


def goster(fn):
    """Çalıştır düğmesi: öğrencinin işleviyle gerçek model üzerinde aday kümeleri ve üretim."""
    tok, _, bilgi = ai_lab.dil_modeli()
    print(f"Model: {bilgi['model']}@{bilgi['revizyon'][:8]} · sözlük {bilgi['sozluk']} token")
    print(f"Metin: {DENEY_METNI!r}\n")
    print("Aday kümesi boyutu (sonraki token):")
    boyutlar = kume_boyutlari(fn)
    for ad, n in boyutlar.items():
        print(f"  {ad:14} → {n} aday")
    print("\nAynı tohumla 12 token üretim:")
    uretimler = {}
    for ad, ayar in DENEY_AYARLARI:
        uretimler[ad] = uret(fn, DENEY_METNI, ayar, seed=7)
        print(f"  {ad:14} {uretimler[ad]['metin']!r}")
    print("\nKanıt:", ai_lab.kanit_yaz("temel-ornekleme-calistir", {
        "kaynak": "gercek", "kabul": False, "ders": "ai-temel-04", "model_bilgisi": bilgi,
        "ayarlar":{"metin":DENEY_METNI,"tohum":7,"en_fazla_token":12,"uretim":DENEY_AYARLARI},"aday_kumesi_boyutlari": boyutlar, "uretimler": uretimler}))
