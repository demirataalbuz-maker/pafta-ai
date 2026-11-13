# -*- coding: utf-8 -*-
"""ai-temel-36 gerçek deney: Pafta ders paragrafları "eğitim kümesi" olarak yerel all-minilm modeliyle gömülür. Dört grup
metin karşılaştırılır: ayrılmış gerçek paragraflar, qwen3'ün eğitim paragraflarını özetlediği metinler, qwen3'ün
"daha önce kullanılmamış bir benzetmeyle" anlattığı metinler ve alan dışı Python kodu. Öğrencinin k-NN yenilik skoru
gömme uzayında, n-gram yenilik ve en uzun kopya ölçüsü metin düzeyinde hesaplanır."""
import glob, os, random, re, time
import ai_lab
from sandbox import ai_uretim_ortak as O

AYAR = {"egitim": 150, "grup": 8, "k": 5, "n": 4, "seed": 36, "gomme_modeli": "all-minilm:22m", "ezber_bas": 20,
        "kavramlar": ["gradyan inişi", "dikkat mekanizması", "aşırı uyum", "tokenizer", "kayıp fonksiyonu", "öğrenme oranı", "gömme vektörü", "düzenlileştirme"]}


MIT = ("Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files "
       "(the \"Software\"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, "
       "publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, "
       "subject to the following conditions: The above copyright notice and this permission notice shall be included in all copies or "
       "substantial portions of the Software. THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING "
       "BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.")
CIFTLER = [("beehive", "database"), ("origami", "encryption"), ("volcano", "project management"), ("jazz improvisation", "compiler")]


def _cos(a, b):
    import math
    return sum(x * y for x, y in zip(a, b)) / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


def _paragraflar():
    out = []
    for yol in sorted(glob.glob(os.path.join(O.KOK, "tracks", "ai-*", "lessons", "*.md"))):
        t = re.sub(r"```.*?```", " ", open(yol, encoding="utf-8").read(), flags=re.S)
        out += [" ".join(p.split()) for p in re.split(r"\n\s*\n", t) if 40 <= len(p.split()) <= 110 and not p.lstrip().startswith((":::", "#", "|", "-"))]
    return out


def deney(yenilik_skoru, ngram_yenilik):
    rnd = random.Random(AYAR["seed"])
    p = _paragraflar()
    rnd.shuffle(p)
    egitim, ayri = p[: AYAR["egitim"]], p[AYAR["egitim"]: AYAR["egitim"] + AYAR["grup"]]
    with ai_lab.SohbetOturumu() as ot:
        ozet = [ot.sohbet([{"role": "user", "content": "Bu paragrafı Türkçe olarak iki cümlede özetle:\n\n" + egitim[i]}], seed=0, sicaklik=0.3,
                          en_fazla=120)["icerik"].strip() for i in range(AYAR["grup"])]
        yaratici = [ot.sohbet([{"role": "user", "content": f"'{c}' kavramını daha önce hiç kullanılmamış, şaşırtıcı bir benzetmeyle Türkçe olarak üç cümlede anlat."}],
                              seed=0, sicaklik=0.9, en_fazla=150)["icerik"].strip() for c in AYAR["kavramlar"]]
        # Ezber: bilinen bir metnin (MIT lisansı) ve hiç yayımlanmamış Pafta paragraflarının açılışından devam ettirme
        devam = lambda bas: ot.sohbet([{"role": "user", "content": "Continue the following text exactly as it continues in the original. "  # noqa: E731
                                         "Output only the continuation.\n\n" + bas}], seed=0, sicaklik=0.0, en_fazla=220)["icerik"].strip()
        mw = MIT.split()
        ezber = {"mit_lisansi": {"kaynak": MIT, "uretim": devam(" ".join(mw[: AYAR["ezber_bas"]]))}}
        for j, par in enumerate(ayri[:2]):
            ezber[f"pafta_paragraf_{j}"] = {"kaynak": par, "uretim": devam(" ".join(par.split()[: AYAR["ezber_bas"]]))}
        # Boden'ın birleştirici yaratıcılığı: iki uzak kavramı birleştiren fikir ve tek kavramlı açıklama
        birlesik = [ot.sohbet([{"role": "user", "content": f"In two sentences, propose a new idea that combines {a} and {b}."}], seed=0,
                              sicaklik=0.7, en_fazla=90)["icerik"].strip() for a, b in CIFTLER]
        tekli = [ot.sohbet([{"role": "user", "content": f"In two sentences, explain {a}."}], seed=0, sicaklik=0.7, en_fazla=90)["icerik"].strip()
                 for a, _ in CIFTLER]
        uretici = ot.kayit.get("model")
    kodlar = []
    for y in sorted(glob.glob(os.path.join(O.KOK, "sandbox", "ai_gercek_ai_uretim_0*.py")))[: AYAR["grup"]]:
        satir = open(y, encoding="utf-8").read().splitlines()
        kodlar.append(" ".join(" ".join(satir[30:45]).split()))
    gruplar = {"ayrilmis_gercek": ayri, "ozet": ozet, "yaratici_benzetme": yaratici, "alan_disi_kod": kodlar}
    with ai_lab.SohbetOturumu(model=AYAR["gomme_modeli"]) as ot:
        def gom(metinler):
            for bekle in (2, 5, None):                 # model yeni yüklenirken Ollama geçici 500 dönebilir (sohbet çağrısındaki gibi)
                try:
                    r = ai_lab._istek(ot.adres, "/api/embed", {"model": ot.model, "input": metinler}, sure=120)
                    break
                except Exception as e:  # noqa: BLE001
                    if bekle is None or "500" not in str(e):
                        raise
                    time.sleep(bekle)
            return [list(map(float, v)) for v in r["embeddings"]]
        E = gom(egitim)
        G = {ad: gom(m) for ad, m in gruplar.items()}
        KA, KB = gom([a for a, _ in CIFTLER]), gom([b for _, b in CIFTLER])
        GB, GT = gom(birlesik), gom(tekli)
    boden = []
    for i, (a, b) in enumerate(CIFTLER):
        boden.append({"cift": [a, b], "birlesik_min_cos": round(min(_cos(GB[i], KA[i]), _cos(GB[i], KB[i])), 4),
                      "tekli_min_cos": round(min(_cos(GT[i], KA[i]), _cos(GT[i], KB[i])), 4), "kavramlar_arasi_cos": round(_cos(KA[i], KB[i]), 4),
                      "ornek": birlesik[i][:160]})
    for ad, e in ezber.items():
        kalan = " ".join(e["kaynak"].split()[AYAR["ezber_bas"]:])
        o = ngram_yenilik([kalan], e["uretim"], AYAR["n"]) if len(e["uretim"].split()) >= AYAR["n"] else {"en_uzun_kopya": 0, "yenilik_orani": 1.0}
        e.update({"en_uzun_kopya": o["en_uzun_kopya"], "yenilik_orani": o["yenilik_orani"], "uretim": e["uretim"][:300]})
        e.pop("kaynak")
    sonuc = {}
    for ad, vek in G.items():
        o = yenilik_skoru([list(v) for v in E], [list(v) for v in vek], AYAR["k"])
        ng = [ngram_yenilik(list(egitim), m, AYAR["n"]) for m in gruplar[ad] if len(m.split()) >= AYAR["n"]]
        sonuc[ad] = {"ort_knn": sum(x["knn"] for x in o["yeni"]) / len(o["yeni"]), "ort_yuzdelik": sum(x["yuzdelik"] for x in o["yeni"]) / len(o["yeni"]),
                     "dis_oran": o["dis_oran"], "kutu_ici_oran": sum(x["kutu_icinde"] for x in o["yeni"]) / len(o["yeni"]),
                     "ngram_yenilik": sum(x["yenilik_orani"] for x in ng) / len(ng), "en_uzun_kopya_ort": sum(x["en_uzun_kopya"] for x in ng) / len(ng)}
    # bağımsız referans: bir grubun k-NN ortalaması
    import math
    def knn(v):
        u = sorted(math.dist(v, e) for e in E)
        return sum(u[: AYAR["k"]]) / AYAR["k"]
    ref = sum(knn(v) for v in G["alan_disi_kod"]) / len(G["alan_disi_kod"])
    fonk_ayni = abs(ref - sonuc["alan_disi_kod"]["ort_knn"]) <= 1e-5
    return {
        "uretici": uretici, "gomme_modeli": AYAR["gomme_modeli"], "surumler": O.surumler(), "egitim_paragraf": len(egitim), "boyut": len(E[0]),
        "gruplar": sonuc, "ornek_ozet": ozet[0][:200], "ornek_yaratici": yaratici[0][:200], "fonksiyon_ayni": fonk_ayni,
        "kod_en_uzak": sonuc["alan_disi_kod"]["ort_knn"] > max(sonuc[g]["ort_knn"] for g in ("ayrilmis_gercek", "ozet", "yaratici_benzetme")),
        "ozet_daha_cok_kopya": sonuc["ozet"]["en_uzun_kopya_ort"] > sonuc["yaratici_benzetme"]["en_uzun_kopya_ort"],
        "ezber": ezber, "ezber_birebir_geri_geliyor": (ezber["mit_lisansi"]["en_uzun_kopya"] >= 20
                                                         and all(v["en_uzun_kopya"] <= 6 for k_, v in ezber.items() if k_ != "mit_lisansi")),
        "boden_birlestirici": boden,
        "birlesim_iki_kavrama_yakin": (sum(x["birlesik_min_cos"] for x in boden) / len(boden)
                                       > sum(x["tekli_min_cos"] for x in boden) / len(boden) + 0.05),
        "ozet_metin": ("Gömme uzayında (all-minilm, " + str(len(E[0])) + " boyut) k-NN uzaklığı / yüzdelik / kutu içi oranı: "
                       + "; ".join(f"{g} {v['ort_knn']:.3f} / {v['ort_yuzdelik']:.2f} / {v['kutu_ici_oran']:.2f}" for g, v in sonuc.items()) +
                       ". 4-gram yenilik ve ortalama en uzun kopya (kelime): " + "; ".join(f"{g} {v['ngram_yenilik']:.2f} / {v['en_uzun_kopya_ort']:.1f}" for g, v in sonuc.items()) +
                       ". Ezber (ilk " + str(AYAR["ezber_bas"]) + " kelimeden devam, en uzun birebir kopya): " + "; ".join(f"{k_} {v['en_uzun_kopya']}" for k_, v in ezber.items()) +
                       ". Birleştirici yaratıcılık (iki kavrama en düşük kosinüs, birleşik / tek kavramlı): "
                       + "; ".join(f"{x['cift'][0]}+{x['cift'][1]} {x['birlesik_min_cos']:.2f} / {x['tekli_min_cos']:.2f}" for x in boden) + "."),
        "sinir": ("Gömme modeli İngilizce ağırlıklı küçük bir modeldir ve Türkçe metinler için kaba bir uzaydır. Yenilik eğitim kümesine "
                  "uzaklıktır; yaratıcılığı, doğruluğu ya da değeri ölçmez. Gruplar sekizer metindir. Boden'ın türlerinden yalnız birleştirici "
                  "olan, çıktının iki kavrama birlikte yakınlığıyla kaba olarak ölçülür; keşfedici ve dönüştürücü yaratıcılık ölçülmez. Ezber "
                  "deneyi tek bir yaygın metinle (MIT lisansı) yapılır; eğitim verisinde çok tekrarlanan metinler en kolay geri gelir."),
    }


def goster(yenilik_skoru, ngram_yenilik):
    r = deney(yenilik_skoru, ngram_yenilik)
    for g, v in r["gruplar"].items():
        print("  %-18s k-NN %.3f | yüzdelik %.2f | dış oran %.2f | kutu içi %.2f | 4-gram yenilik %.2f | en uzun kopya %.1f"
              % (g, v["ort_knn"], v["ort_yuzdelik"], v["dis_oran"], v["kutu_ici_oran"], v["ngram_yenilik"], v["en_uzun_kopya_ort"]))
    print("Örnek özet:", r["ornek_ozet"])
    print("Örnek benzetme:", r["ornek_yaratici"])
    print("Sınır:", r["sinir"])
    print("Kanıt:", O.kanit("ai-temel-36", "run", r))
