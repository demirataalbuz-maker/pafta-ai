# -*- coding: utf-8 -*-
"""ai-temel-10 gerçek deneyi: SmolLM2'ye elle yazılmış LoRA ile CPU'da gerçek ince ayar.

PEFT kullanılmaz; öğrencinin LoRA sınıfı modelin q_proj/v_proj katmanlarına takılır. Önbellekteki ortak model
değişmesin diye deney modelin bir kopyasında yapılır.
"""
import copy
import hashlib
import math

import ai_lab

HEDEF_METIN = "The secret code of the Pafta lab is 7342."
HEDEF_ONEK = "The secret code of the Pafta lab is"
KONTROL_METNI = "The capital of France is Paris. Water boils at 100 degrees Celsius."
HEDEF_MODULLER = ("q_proj", "v_proj")


def referans_sinifi(*, olcek_tur="alfa/rank", b_sifir=True, dondur=True, yerinde=False, ileri_olcek=True):
    """Doğru LoRA katmanı (varsayılanlarla) ve testlerin kullandığı hatalı varyantlar."""
    torch = ai_lab._torch()

    class ReferansLora(torch.nn.Module):
        def __init__(self, temel, rank, alfa):
            super().__init__()
            if not isinstance(temel, torch.nn.Linear):
                raise ValueError("temel")
            if isinstance(rank, bool) or not isinstance(rank, int) or not 1 <= rank <= min(temel.in_features, temel.out_features):
                raise ValueError("rank")
            if isinstance(alfa, bool) or not isinstance(alfa, (int, float)) or not alfa > 0 or not math.isfinite(alfa):
                raise ValueError("alfa")
            self.temel = temel
            if dondur:
                for p in temel.parameters():
                    p.requires_grad_(False)
            self.A = torch.nn.Parameter(torch.randn(rank, temel.in_features) * 0.01)
            self.B = torch.nn.Parameter(torch.zeros(temel.out_features, rank) if b_sifir
                                        else torch.randn(temel.out_features, rank) * 0.01)
            self.olcek = alfa / rank if olcek_tur == "alfa/rank" else float(alfa)

        def forward(self, x):
            return self.temel(x) + (x @ self.A.T @ self.B.T) * (self.olcek if ileri_olcek else 1.0)

        def birlestir(self):
            fark = (self.olcek * (self.B @ self.A)).detach()
            if yerinde:
                with torch.no_grad():
                    self.temel.weight += fark
                return self.temel.weight.detach()
            return self.temel.weight.detach() + fark

    return ReferansLora


def _ozet(t):
    return hashlib.sha256(t.detach().contiguous().numpy().tobytes()).hexdigest()[:16]


def _kayip(model, tok, metin):
    torch = ai_lab._torch()
    ids = torch.tensor([tok(metin)["input_ids"]])
    with torch.no_grad():
        return model(ids, labels=ids).loss.item()


def _uret(model, tok, onek, n=6):
    torch = ai_lab._torch()
    ids = tok(onek)["input_ids"]
    with torch.no_grad():
        for _ in range(n):
            ids.append(int(model(torch.tensor([ids])).logits[0, -1].argmax()))
    return tok.decode(ids[len(tok(onek)["input_ids"]):])


def lora_tak(model, sinif, rank, alfa):
    """Her katmanın q_proj/v_proj'unu sinif(temel, rank, alfa) ile değiştirir; takılan katmanları döndürür."""
    takilan = []
    for katman in model.model.layers:
        for ad in HEDEF_MODULLER:
            sarmal = sinif(getattr(katman.self_attn, ad), rank, alfa)
            setattr(katman.self_attn, ad, sarmal)
            takilan.append(sarmal)
    return takilan


def _tum_ozet(parametreler):
    return {ad:hashlib.sha256(t.detach().cpu().contiguous().numpy().tobytes()).hexdigest() for ad,t in parametreler}


def deney(sinif, rank=8, alfa=16, adim=40, ogrenme=2e-3, seed=2026):
    """Gerçek ince ayar. Sonuç sözlüğü kanıta yazılır; kabul koşullarını test belirler."""
    torch = ai_lab._torch()
    tok, temel_model, _ = ai_lab.dil_modeli()
    torch.manual_seed(seed)
    ortak_once=_tum_ozet(temel_model.state_dict().items())
    model = copy.deepcopy(temel_model)
    toplam = sum(p.numel() for p in model.parameters())
    for p in model.parameters():
        p.requires_grad_(False)
    temel_parametreler=list(model.named_parameters());temel_once=_tum_ozet(temel_parametreler)
    once = {"hedef": _kayip(model, tok, HEDEF_METIN), "kontrol": _kayip(model, tok, KONTROL_METNI),
            "uretim": _uret(model, tok, HEDEF_ONEK)}
    takilan = lora_tak(model, sinif, rank, alfa)
    egitilen = [p for p in model.parameters() if p.requires_grad]
    n_egitilen = sum(p.numel() for p in egitilen)
    takili_kayip = _kayip(model, tok, HEDEF_METIN)
    temel_ozet = [_ozet(l.temel.weight) for l in takilan[:2]]
    opt = torch.optim.Adam(egitilen, lr=ogrenme) if egitilen else None
    ids = torch.tensor([tok(HEDEF_METIN)["input_ids"]])
    seyir = [];egitim_adimlari=[]
    model.train()
    for i in range(adim if opt else 0):
        opt.zero_grad()
        kayip = model(ids, labels=ids).loss
        kayip.backward()
        opt.step()
        egitim_adimlari.append({"adim":i,"kayip":kayip.item()})
        if i % 10 == 0 or i == adim - 1:
            seyir.append((i, round(kayip.item(), 4)))
    model.eval()
    sonra = {"hedef": _kayip(model, tok, HEDEF_METIN), "kontrol": _kayip(model, tok, KONTROL_METNI),
             "uretim": _uret(model, tok, HEDEF_ONEK)}
    temel_sonra=_tum_ozet(temel_parametreler)
    temel_degismedi=temel_once==temel_sonra
    # Birleştirme: adaptörsüz yeni kopyaya birleşik ağırlıkları yaz, çıktıları karşılaştır
    birlesik = copy.deepcopy(temel_model)
    k = 0
    for katman in birlesik.model.layers:
        for ad in HEDEF_MODULLER:
            with torch.no_grad():
                getattr(katman.self_attn, ad).weight.copy_(takilan[k].birlestir())
            k += 1
    kontrol_ids = torch.tensor([tok(KONTROL_METNI + " " + HEDEF_ONEK)["input_ids"]])
    with torch.no_grad():
        birlesme_farki = (model(kontrol_ids).logits - birlesik(kontrol_ids).logits).abs().max().item()
    ortak_sonra=_tum_ozet(temel_model.state_dict().items())
    return {"girdiler":{"hedef_metin":HEDEF_METIN,"hedef_tokenlar":ids[0].tolist(),"uretim_oneki":HEDEF_ONEK,"kontrol_metin":KONTROL_METNI,"kontrol_tokenlar":kontrol_ids[0].tolist()},"optimizer":"torch.optim.Adam","egitim_adimlari":egitim_adimlari,"temel_ozetleri":{"once":temel_once,"sonra":temel_sonra},"ortak_ozetleri":{"once":ortak_once,"sonra":ortak_sonra},"rank": rank, "alfa": alfa, "adim": adim, "ogrenme": ogrenme, "seed": seed,
            "hedef_moduller": list(HEDEF_MODULLER), "takilan_katman": len(takilan),
            "toplam_parametre": toplam, "egitilen_parametre": n_egitilen, "oran": n_egitilen / toplam,
            "beklenen_egitilen": sum(rank * (l.temel.in_features + l.temel.out_features) for l in takilan),
            "takinca_hedef_kayip": takili_kayip, "once": once, "sonra": sonra, "seyir": seyir,
            "temel_agirlik_degismedi": temel_degismedi, "birlesme_farki": birlesme_farki,
            "ortak_model_degismedi": ortak_once==ortak_sonra}


def goster(sinif):
    """Çalıştır düğmesi: öğrencinin LoRA sınıfıyla gerçek ince ayar."""
    _, _, bilgi = ai_lab.dil_modeli()
    print(f"Model: {bilgi['model']}@{bilgi['revizyon'][:8]} · LoRA hedefleri: {', '.join(HEDEF_MODULLER)} (30 katman)")
    r = deney(sinif)
    print(f"Eğitilen parametre: {r['egitilen_parametre']:,} / {r['toplam_parametre']:,} (%{100 * r['oran']:.2f}); "
          f"beklenen {r['beklenen_egitilen']:,}")
    print(f"Adaptör takılınca hedef kaybı {r['once']['hedef']:.3f} → {r['takinca_hedef_kayip']:.3f} (B=0 ise değişmemeli)")
    print(f"Eğitim seyri (adım, kayıp): {r['seyir']}")
    print(f"Hedef cümle kaybı:  {r['once']['hedef']:.3f} → {r['sonra']['hedef']:.3f}")
    print(f"İlgisiz metin kaybı: {r['once']['kontrol']:.3f} → {r['sonra']['kontrol']:.3f}")
    print(f"{HEDEF_ONEK!r} devamı: önce {r['once']['uretim']!r}, sonra {r['sonra']['uretim']!r}")
    print(f"Temel ağırlık eğitimde değişmedi: {r['temel_agirlik_degismedi']} · birleşik model ile adaptörlü model farkı "
          f"{r['birlesme_farki']:.1e}")
    print("\nKanıt:", ai_lab.kanit_yaz("temel-lora-calistir", {
        "kaynak": "gercek", "kabul": False, "ders": "ai-temel-10", "model_bilgisi": bilgi, "deney": r}))
