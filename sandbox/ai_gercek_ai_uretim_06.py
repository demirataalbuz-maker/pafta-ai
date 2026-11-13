# -*- coding: utf-8 -*-
"""ai-uretim-06 gerçek deney: (1) öğrencinin MinHash-LSH tekilleştiricisi Pafta ders metinlerinden alınan gerçek
paragraflarda ve onların yakın kopyalarında gerçek Jaccard'a karşı ölçülür, kelime araya ekleme ile tekilleştirmeden
kaçış gösterilir; (2) öğrencinin belge paketleme maskesi gerçek SmolLM2'ye 4B dikkat maskesi olarak verilir ve paketli
belgelerin logit'leri tek başına çalıştırılan belgelerle karşılaştırılır; (3) Gopher süzgeci gerçek deepset/prompt-injections
metinlerinde çalıştırılır: kalite süzgecinin enjeksiyonları ayıklamadığı ölçülür."""
import glob, os, random, re
import ai_lab
from sandbox import ai_uretim_ortak as O

AYAR = {"paragraf": 60, "bant": 16, "satir": 4, "seed": 6, "baglam": 96,
        "belgeler": ["The backup job finished at midnight and all volumes were verified.",
                     "Kedi pencerenin önünde uyuyor, dışarıda yağmur yağıyor.",
                     "def topla(a, b):\n    return a + b\n",
                     "Revenue grew in the third quarter while operating costs stayed flat across all regions and teams."]}
VERI = "deepset/prompt-injections"
VERI_REV = "4f61ecb038e9c3fb77e21034b22511b523772cdd"
VERI_DOSYA = "data/test-00000-of-00001-701d16158af87368.parquet"


def _paragraflar():
    out = []
    for yol in sorted(glob.glob(os.path.join(O.KOK, "tracks", "ai-*", "lessons", "*.md"))):
        t = re.sub(r"```.*?```", " ", open(yol, encoding="utf-8").read(), flags=re.S)
        for p in re.split(r"\n\s*\n", t):
            p = " ".join(p.split())
            if 40 <= len(p.split()) <= 120 and not p.startswith((":::", "#", "|", "-", "*")):
                out.append(p)
    return out


def _jaccard(a, b):
    def sh(x):
        w = x.lower().split()
        return {" ".join(w[i:i + 2]) for i in range(len(w) - 1)} if len(w) >= 2 else set(w)
    A, B = sh(a), sh(b)
    return len(A & B) / len(A | B) if A | B else 1.0


def _lsh_kismi(lsh_tekillestir, rnd):
    paragraflar = _paragraflar()
    rnd.shuffle(paragraflar)
    taban = paragraflar[: AYAR["paragraf"]]
    belgeler, cift = list(taban), []
    for i, p in enumerate(taban[:20]):              # yakın kopya: bir kelime değişir (sürüm/yazım farkı gibi)
        w = p.split()
        j = rnd.randrange(len(w))
        w[j] = w[j] + "x"
        belgeler.append(" ".join(w)); cift.append((i, len(belgeler) - 1, "yakin"))
    for i, p in enumerate(taban[20:30], start=20):  # saldırgan kopyası: her 3 kelimede bir dolgu kelimesi
        w = p.split()
        y = []
        for k, x in enumerate(w):
            y.append(x)
            if k % 3 == 2:
                y.append("ve")
        belgeler.append(" ".join(y)); cift.append((i, len(belgeler) - 1, "kacis"))
    o = lsh_tekillestir(belgeler, AYAR["bant"], AYAR["satir"])
    elenen = set(o["elenen_indeksler"])
    sonuc = {"yakin": [0, 0], "kacis": [0, 0]}
    jac = {"yakin": [], "kacis": []}
    for a, b, tur in cift:
        sonuc[tur][0] += b in elenen
        sonuc[tur][1] += 1
        jac[tur].append(_jaccard(belgeler[a], belgeler[b]))
    yanlis = sum(1 for i in elenen if i < AYAR["paragraf"])          # özgün paragraflardan elenen (yanlış pozitif)
    b, r = AYAR["bant"], AYAR["satir"]
    s_yakin = sum(jac["yakin"]) / len(jac["yakin"])
    s_kacis = sum(jac["kacis"]) / len(jac["kacis"])
    return {
        "belge_sayisi": len(belgeler), "yakin_kopya_yakalanan": sonuc["yakin"][0], "yakin_kopya": sonuc["yakin"][1],
        "kacis_kopya_yakalanan": sonuc["kacis"][0], "kacis_kopya": sonuc["kacis"][1], "ozgun_yanlis_elenen": yanlis,
        "ort_jaccard_yakin": s_yakin, "ort_jaccard_kacis": s_kacis,
        "teorik_yakalama_yakin": 1 - (1 - s_yakin ** r) ** b, "teorik_yakalama_kacis": 1 - (1 - s_kacis ** r) ** b,
    }


def _paket_kismi(belge_paketle):
    torch = O.torch_al()
    tok, model, bilgi = O.smol()
    diziler = [tok(m, add_special_tokens=False).input_ids for m in AYAR["belgeler"]]
    eos = tok.eos_token_id
    o = belge_paketle([list(d) for d in diziler], AYAR["baglam"], eos)
    ids = torch.tensor([o["paketlenmis_tokenlar"]])
    did = o["doc_ids"]
    T = len(did)
    pos, sayac = [], {}
    for d in did:
        pos.append(sayac.get(d, 0)); sayac[d] = sayac.get(d, 0) + 1
    maske = torch.tensor(o["maske"], dtype=torch.bool)
    maske = maske | torch.eye(T, dtype=torch.bool)                   # dolgu satırları NaN üretmesin (karşılaştırmaya girmez)
    m4 = torch.zeros(1, 1, T, T).masked_fill(~maske, torch.finfo(torch.float32).min)
    with torch.no_grad():
        paketli = model(ids, attention_mask=m4, position_ids=torch.tensor([pos])).logits[0]
        duz = model(ids).logits[0]                                   # yalnız nedensel maske: belgeler birbirini görür
    fark_maske, fark_duz = 0.0, 0.0
    bas = 0
    for n, d in enumerate(diziler):
        uz = len(d) + 1
        if bas + uz > T:
            break
        with torch.no_grad():
            tek = model(torch.tensor([list(d) + [eos]])).logits[0]
        fark_maske = max(fark_maske, float((paketli[bas:bas + uz] - tek).abs().max()))
        if n > 0:
            fark_duz = max(fark_duz, float((duz[bas:bas + uz] - tek).abs().max()))
        bas += uz
    dogru = torch.zeros(T, T, dtype=torch.bool)
    for i in range(T):
        for j in range(i + 1):
            dogru[i, j] = did[i] == did[j] and did[i] != -1
    return bilgi, {
        "baglam": T, "belge_token": [len(d) for d in diziler], "maske_dogru": bool((torch.tensor(o["maske"], dtype=torch.bool) == dogru).all()),
        "aktif_dikkat": o["aktif_dikkat_sayisi"], "nedensel_dikkat": T * (T + 1) // 2,
        "paketli_tek_logit_fark": fark_maske, "maskesiz_tek_logit_fark": fark_duz,
    }


def _suzgec_kismi(kalite_suzgeci):
    try:
        import pandas as pd
        from huggingface_hub import hf_hub_download
        yol = hf_hub_download(VERI, VERI_DOSYA, repo_type="dataset", revision=VERI_REV, local_files_only=True)
    except Exception as e:  # noqa: BLE001
        raise ai_lab.GercekLabYok(f"{VERI}@{VERI_REV[:8]} yerelde yok: {e}") from e
    df = pd.read_parquet(yol)
    say = {0: [0, 0], 1: [0, 0]}
    ihlal = {}
    for metin, et in zip(df.text, df.label):
        o = kalite_suzgeci(str(metin), 8, 100000)
        say[int(et)][0] += bool(o["gecti"]); say[int(et)][1] += 1
        for i in o["ihlaller"]:
            ihlal[i] = ihlal.get(i, 0) + 1
    return {"veri": f"{VERI}@{VERI_REV[:8]} test", "zararsiz_gecen": say[0][0], "zararsiz": say[0][1],
            "enjeksiyon_gecen": say[1][0], "enjeksiyon": say[1][1], "ihlal_sayilari": ihlal}


def deney(lsh_tekillestir, belge_paketle, kalite_suzgeci):
    rnd = random.Random(AYAR["seed"])
    L = _lsh_kismi(lsh_tekillestir, rnd)
    bilgi, P = _paket_kismi(belge_paketle)
    S = _suzgec_kismi(kalite_suzgeci)
    gecme_z = S["zararsiz_gecen"] / S["zararsiz"]
    gecme_e = S["enjeksiyon_gecen"] / S["enjeksiyon"]
    return {
        "model": {k2: bilgi[k2] for k2 in ("model", "revizyon", "agirlik_sha256", "parametre")}, "surumler": O.surumler("pandas"),
        "lsh": L, "paket": P, "suzgec": S,
        "lsh_yakin_orani": L["yakin_kopya_yakalanan"] / L["yakin_kopya"], "lsh_kacis_orani": L["kacis_kopya_yakalanan"] / L["kacis_kopya"],
        "paket_izole": P["paketli_tek_logit_fark"] <= 1e-3, "maskesiz_sizar": P["maskesiz_tek_logit_fark"] > 0.1,
        "suzgec_enjeksiyon_gecme": gecme_e, "suzgec_zararsiz_gecme": gecme_z,
        "olcum": (f"LSH (b={AYAR['bant']}, r={AYAR['satir']}) {L['belge_sayisi']} gerçek ders paragrafında: tek kelimelik yakın kopyaların "
                  f"{L['yakin_kopya_yakalanan']}/{L['yakin_kopya']}'i elendi (ort. Jaccard {L['ort_jaccard_yakin']:.2f}), dolgu kelimeli "
                  f"kopyaların {L['kacis_kopya_yakalanan']}/{L['kacis_kopya']}'i (Jaccard {L['ort_jaccard_kacis']:.2f}); özgünlerden "
                  f"{L['ozgun_yanlis_elenen']} yanlış eleme. Paketli SmolLM2 logit'leri tek başına çalıştırmadan en çok "
                  f"{P['paketli_tek_logit_fark']:.1e} farklı, maskesiz paketlemede {P['maskesiz_tek_logit_fark']:.2f}. Gopher süzgeci "
                  f"enjeksiyonların %{100 * gecme_e:.0f}'ini, zararsızların %{100 * gecme_z:.0f}'ini geçiriyor."),
        "sinir": ("LSH ölçümü 90 belgelik küçük bir korpustadır ve öğrencinin doğrusal hash ailesi gerçek MinHash'ten zayıftır; Jaccard "
                  "kelime ikilisi üzerinden hesaplanır. Paketleme deneyi tek bir 96 tokenlik bağlamdır. Süzgeç ölçümünde min_kelime 8'e "
                  "indirilmiştir; deepset test kümesi 116 kısa metindir."),
    }


def goster(lsh_tekillestir, belge_paketle, kalite_suzgeci):
    r = deney(lsh_tekillestir, belge_paketle, kalite_suzgeci)
    L, P, S = r["lsh"], r["paket"], r["suzgec"]
    print("LSH yakın kopya: %d/%d elendi (Jaccard %.2f, teorik %.2f)" % (L["yakin_kopya_yakalanan"], L["yakin_kopya"], L["ort_jaccard_yakin"], L["teorik_yakalama_yakin"]))
    print("LSH dolgu kelimeli kaçış: %d/%d elendi (Jaccard %.2f, teorik %.2f)" % (L["kacis_kopya_yakalanan"], L["kacis_kopya"], L["ort_jaccard_kacis"], L["teorik_yakalama_kacis"]))
    print("Paketli logit farkı (senin maskenle): %.2e | maskesiz: %.3f | maske doğru: %s" % (P["paketli_tek_logit_fark"], P["maskesiz_tek_logit_fark"], P["maske_dogru"]))
    print("Gopher süzgecinden geçen  enjeksiyon: %d/%d | zararsız: %d/%d" % (S["enjeksiyon_gecen"], S["enjeksiyon"], S["zararsiz_gecen"], S["zararsiz"]))
    print("Sınır:", r["sinir"])
    print("Kanıt:", O.kanit("ai-uretim-06", "run", r))
