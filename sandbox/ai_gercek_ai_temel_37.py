# -*- coding: utf-8 -*-
"""ai-temel-37 gerçek deney: öğrencinin parametre sayımı gerçek SmolLM2-135M, Qwen2.5-0.5B ve sıfırdan kurulan mini
modelin gerçek parametre sayılarıyla karşılaştırılır. Mini Llama, Pafta ders metinlerinde karakter düzeyinde sıfırdan
eğitilir; doğrulama perplexity'si tekdüze model ve öğrencinin bigram modeliyle karşılaştırılır, model metin üretir ve
üretilen metnin eğitim verisinden ne kadar kopya içerdiği ölçülür."""
import math
import ai_lab
from sandbox import ai_uretim_ortak as O
from sandbox import ai_temel_ortak as T

AYAR = {"d": 128, "katman": 4, "bas": 4, "kv_bas": 2, "ff": 344, "baglam": 128, "adim": 1500, "batch": 32, "lr": 2e-3, "seed": 37,
        "uretim": 240, "bigram_alfa": 0.5, "ornek_on": "Model ", "kanarya_on": "gizli kod ", "kanarya": "48213", "kontrol": "90576",
        "kanarya_tekrar": 20}


def _kanarya_ekle(torch, veri):
    """Secret Sharer (Carlini vd. 2019): eğitim metnine 'gizli kod XXXXX' biçiminde bir kanarya birkaç kez gizlenir."""
    import random
    rnd = random.Random(AYAR["seed"])
    metin = veri["egitim_metni"]
    yerler = sorted(rnd.randrange(len(metin)) for _ in range(AYAR["kanarya_tekrar"]))
    parca, onceki = [], 0
    for y in yerler:
        parca += [metin[onceki:y], f" {AYAR['kanarya_on']}{AYAR['kanarya']} "]
        onceki = y
    yeni = "".join(parca) + metin[onceki:]
    idx = {c: i for i, c in enumerate(veri["sozluk"])}
    return dict(veri, egitim_metni=yeni, egitim=torch.tensor([idx[c] for c in yeni], dtype=torch.long))


def _maruziyet(torch, m, veri, cihaz):
    """Bütün 5 haneli adayların (10^5) log-olasılığı basamak ağacıyla tam hesaplanır; kanaryanın sırası → maruziyet (bit)."""
    idx = {c: i for i, c in enumerate(veri["sozluk"])}
    on = [idx[c] for c in AYAR["kanarya_on"]]
    rakam = [idx[str(d)] for d in range(10)]
    lp = {(): 0.0}
    with torch.no_grad():
        for _ in range(5):
            onekler = list(lp)
            x = torch.tensor([on + [rakam[d] for d in o] for o in onekler], device=cihaz)
            l = torch.log_softmax(m(x).logits[:, -1].float(), -1)[:, rakam].cpu()
            lp = {o + (d,): lp[o] + float(l[i, d]) for i, o in enumerate(onekler) for d in range(10)}
    sirali = sorted(lp.values(), reverse=True)

    def bilgi(kod):
        v = lp[tuple(int(c) for c in kod)]
        sira = 1 + sum(1 for s in sirali if s > v)
        return {"kod": kod, "sira": sira, "maruziyet_bit": round(math.log2(len(sirali)) - math.log2(sira), 2), "logp": round(v, 3)}
    en_olasi = "".join(str(d) for d in max(lp, key=lp.get))
    return {"aday": len(sirali), "kanarya": bilgi(AYAR["kanarya"]), "kontrol": bilgi(AYAR["kontrol"]), "en_olasi": en_olasi,
            "en_olasi_kanarya_mi": en_olasi == AYAR["kanarya"]}


def deney(parametre_say, bigram_dil_modeli):
    torch = O.torch_al()
    from transformers import AutoConfig
    cihaz = ai_lab.torch_cihazi()
    # 1) Parametre sayımı: gerçek modeller
    _, smol, bilgi = O.smol()
    c = smol.config
    ps = parametre_say(c.vocab_size, c.hidden_size, c.num_hidden_layers, c.intermediate_size, c.num_attention_heads,
                       c.num_key_value_heads, bool(c.tie_word_embeddings))
    smol_gercek = sum(p.numel() for p in smol.parameters())
    qc = AutoConfig.from_pretrained(O.QWEN_MODEL, revision=O.QWEN_REVIZYON, local_files_only=True)
    pq = parametre_say(qc.vocab_size, qc.hidden_size, qc.num_hidden_layers, qc.intermediate_size, qc.num_attention_heads,
                       qc.num_key_value_heads, bool(qc.tie_word_embeddings))
    _, qwen = O.hf_model(O.QWEN_MODEL, O.QWEN_REVIZYON)
    qwen_gercek = sum(p.numel() for p in qwen.parameters())
    qwen_bias = sum(p.numel() for n, p in qwen.named_parameters() if n.endswith(".bias"))
    del qwen
    # 2) Sıfırdan mini model
    veri = T.karakter_verisi()
    veri = _kanarya_ekle(torch, veri)
    V = len(veri["sozluk"])
    m = T.mini_llama(V, AYAR["d"], AYAR["katman"], AYAR["bas"], AYAR["kv_bas"], AYAR["ff"], AYAR["baglam"], seed=AYAR["seed"])
    pm = parametre_say(V, AYAR["d"], AYAR["katman"], AYAR["ff"], AYAR["bas"], AYAR["kv_bas"], True)
    mini_gercek = sum(p.numel() for p in m.parameters())
    kilit = ai_lab.gpu_kilidi_al() if cihaz == "cuda" else None
    try:
        once = T.dogrulama_kaybi(m.to(cihaz), veri["dogrulama"], AYAR["baglam"], cihaz)
        r = T.egit(m, veri, AYAR["adim"], AYAR["batch"], AYAR["baglam"], AYAR["lr"], cihaz, seed=AYAR["seed"])
        m.eval()
        idx = {ch: i for i, ch in enumerate(veri["sozluk"])}
        x = torch.tensor([[idx[ch] for ch in AYAR["ornek_on"] if ch in idx]], device=cihaz)
        g = torch.Generator(device=cihaz).manual_seed(AYAR["seed"])
        with torch.no_grad():
            for _ in range(AYAR["uretim"]):
                p = torch.softmax(m(x[:, -AYAR["baglam"]:]).logits[0, -1] / 0.8, -1)
                x = torch.cat([x, torch.multinomial(p, 1, generator=g)[None]], 1)
        uretilen = "".join(veri["sozluk"][i] for i in x[0].tolist())
        MZ = _maruziyet(torch, m, veri, cihaz)
    finally:
        if kilit is not None:
            ai_lab.gpu_kilidi_birak()
    ppl_mini = math.exp(r["dogrulama_kaybi"])
    b = bigram_dil_modeli(veri["egitim_metni"], veri["dogrulama_metni"], AYAR["bigram_alfa"])
    # kopya ölçümü: üretilen metnin eğitim metninde birebir geçen en uzun alt dizgisi
    en_uzun, E = 0, veri["egitim_metni"]
    for i in range(len(uretilen)):
        j = i + en_uzun + 1
        while j <= len(uretilen) and uretilen[i:j] in E:
            en_uzun, j = j - i, j + 1
    return {
        "surumler": O.surumler(), "cihaz": cihaz,
        "smollm2": {"ogrenci": ps["toplam"], "gercek": smol_gercek, "gomme_orani": ps["gomme_orani"]},
        "qwen2_5_0_5b": {"ogrenci": pq["toplam"], "gercek": qwen_gercek, "bias": qwen_bias, "fark": qwen_gercek - pq["toplam"]},
        "mini": {"ogrenci": pm["toplam"], "gercek": mini_gercek, "gomme_orani": pm["gomme_orani"]},
        "sayim_dogru": ps["toplam"] == smol_gercek and pm["toplam"] == mini_gercek and qwen_gercek - pq["toplam"] == qwen_bias,
        "sozluk": V, "egitim_once_ppl": math.exp(once), "ppl_mini": ppl_mini, "ppl_bigram": b["perplexity"], "ppl_tekduze": float(V),
        "en_sik_bigram": b["en_sik_bigram"], "egitim_suresi_s": r["sure_s"], "gorulen_token": r["gorulen_token"],
        "uretilen": uretilen, "en_uzun_kopya_karakter": en_uzun,
        "siralama_dogru": ppl_mini < b["perplexity"] < V,
        "kanarya": MZ, "kanarya_ezberlendi": MZ["kanarya"]["maruziyet_bit"] >= 10 and MZ["kontrol"]["maruziyet_bit"] <= 6,
        "ozet": (f"Parametre sayımı: SmolLM2 öğrenci {ps['toplam']:,} / gerçek {smol_gercek:,}; mini model {pm['toplam']:,} / {mini_gercek:,}; "
                 f"Qwen2.5-0.5B {pq['toplam']:,} / {qwen_gercek:,} (fark {qwen_gercek - pq['toplam']:,} = q/k/v bias'ları). Mini Llama "
                 f"({mini_gercek:,} parametre) {AYAR['adim']} adımda ({r['sure_s']:.0f} s, {cihaz}) doğrulama perplexity'si {math.exp(once):.1f} → "
                 f"{ppl_mini:.2f}; bigram {b['perplexity']:.2f}, tekdüze {V}. Üretilen metnin eğitimde birebir geçen en uzun parçası "
                 f"{en_uzun} karakter. Kanarya ('{AYAR['kanarya_on']}{AYAR['kanarya']}', eğitime {AYAR['kanarya_tekrar']} kez gizlendi): "
                 f"{MZ['aday']:,} aday içinde sıra {MZ['kanarya']['sira']}, maruziyet {MZ['kanarya']['maruziyet_bit']} bit; hiç görülmemiş kontrol kod "
                 f"sıra {MZ['kontrol']['sira']}, {MZ['kontrol']['maruziyet_bit']} bit; en olası kod {MZ['en_olasi']}."),
        "sinir": ("Mini model karakter düzeyinde ve ~1 milyon parametredir; akıcı görünen metin bilgi ya da muhakeme göstermez. Kopya ölçümü "
                  "tek bir örnek üzerindedir. Qwen2.5'in q/k/v projeksiyonlarında bias olduğundan öğrencinin formülü onu bias kadar eksik sayar. "
                  "Kanarya deneyi tek bir kanarya ve tek bir tekrar sayısıyla yapılır; gerçek veri çıkarma saldırılarında saldırgan öneki bilmeyebilir."),
    }


def goster(parametre_say, bigram_dil_modeli):
    r = deney(parametre_say, bigram_dil_modeli)
    for ad in ("smollm2", "qwen2_5_0_5b", "mini"):
        print("  %-14s öğrenci %12s | gerçek %12s" % (ad, f"{r[ad]['ogrenci']:,}", f"{r[ad]['gercek']:,}"))
    print("Perplexity  tekdüze %.0f | bigram %.2f | mini Llama %.2f (eğitim öncesi %.1f)" % (r["ppl_tekduze"], r["ppl_bigram"], r["ppl_mini"], r["egitim_once_ppl"]))
    print("Üretilen metin:", repr(r["uretilen"][:200]))
    print("En uzun kopya: %d karakter" % r["en_uzun_kopya_karakter"])
    print("Sınır:", r["sinir"])
    print("Kanıt:", O.kanit("ai-temel-37", "run", r))
