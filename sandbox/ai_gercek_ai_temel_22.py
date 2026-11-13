# -*- coding: utf-8 -*-
"""ai-temel-22 gerçek deneyi: gerçek gömme modeliyle (all-MiniLM-L6-v2, Ollama) etiketli bir derlemde
retrieval kalitesini ölçer. Her sorgunun altın parçası bellidir; öğrenci kosinüs sıralaması yapıp
isabet, anma (recall@k), MRR ve nDCG hesaplar. Deney bağlam seçimini (k=1 ile k=3) karşılaştırır.

Derlem sentetiktir. Gömme modelini bu deney yüklediyse sonunda boşaltır (kaynak sahipliği ai_lab'de).
"""
import json
import math
import urllib.error
import urllib.request

import ai_lab

GOMME_MODELI = "all-minilm:22m"
PARCALAR = [
    ("iade#0", "İade süresi teslimattan sonra 23 gündür."),
    ("kargo#0", "140 TL üzeri siparişlerde kargo ücretsizdir."),
    ("kargo#1", "Siparişler hafta içi 16:00'ya kadar verilirse aynı gün kargolanır."),
    ("guv#0", "Parolalar en az 14 karakter olmalıdır."),
    ("guv#1", "VPN erişimi için donanım anahtarı zorunludur."),
    ("yedek#0", "Sunucu yedekleri 35 gün saklanır."),
    ("yedek#1", "Geri yükleme testi her ayın ilk cuması yapılır."),
    ("izin#0", "Yıllık izin hakkı 14 gündür."),
    ("maas#0", "Maaşlar her ayın son iş günü ödenir."),
    ("toplanti#0", "Haftalık ekip toplantısı salı sabahı yapılır."),
]
SORULAR = [
    ("İade için kaç günüm var?", ["iade#0"]),
    ("Kargo ne zaman ücretsiz olur?", ["kargo#0"]),
    ("Parola en az kaç karakter olmalı?", ["guv#0"]),
    ("Sunucu yedekleri kaç gün saklanır?", ["yedek#0"]),
    ("Yıllık izin hakkım kaç gün?", ["izin#0"]),
    ("Maaşlar ne zaman ödenir?", ["maas#0"]),
]
K = 3


def _birim(v, normalize=True):
    if not normalize: return list(v)
    from fractions import Fraction
    olcek=max(abs(x) for x in v)
    if not olcek: return list(v)
    vv=[float(Fraction(x)/Fraction(olcek)) for x in v]
    boy=math.hypot(*vv)
    return [x/boy for x in vv]


def _sirala(sorgu_vek, idler, vekler, normalize):
    q = _birim(sorgu_vek, normalize)
    skor = [sum(a * b for a, b in zip(_birim(v, normalize), q)) for v in vekler]
    order = sorted(range(len(vekler)), key=lambda i: (-skor[i], i))
    return [idler[i] for i in order]


def _metrik(sirali, altin, k, *, mrr_tam=True, ndcg_norm=True):
    aset = set(altin)
    hit = sum(1 for x in sirali[:k] if x in aset)
    bakilan = sirali if mrr_tam else sirali[:k]
    rr = 0.0
    for i, x in enumerate(bakilan, 1):
        if x in aset:
            rr = 1 / i
            break
    dcg = sum(1 / math.log2(i + 1) for i, x in enumerate(sirali[:k], 1) if x in aset)
    idcg = sum(1 / math.log2(i + 1) for i in range(1, min(k, len(aset)) + 1))
    ndcg = (dcg / idcg) if (ndcg_norm and idcg) else dcg
    return {"isabet": hit > 0, "anma": round(hit / len(aset), 4), "mrr": round(rr, 4), "ndcg": round(ndcg, 4)}


def referans_getir(sorgu_vek, parca_idler, parca_vekleri, altin, k, *, normalize=True, mrr_tam=True, ndcg_norm=True):
    """Doğru sonuç (varsayılanlarla) ve testlerin kullandığı hatalı varyantlar."""
    sirali = _sirala(sorgu_vek, parca_idler, parca_vekleri, normalize)
    return {"sirali": sirali, **_metrik(sirali, altin, k, mrr_tam=mrr_tam, ndcg_norm=ndcg_norm)}


def _istek(adres, yol, govde, sure=120):
    req = urllib.request.Request(adres + yol, json.dumps(govde).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=sure) as r:
        return json.loads(r.read())


class _Gomucu:
    """Ollama /api/embed; model önceden yüklü değilse keep_alive=0 ile boşaltır (kullanıcınınkine dokunmaz)."""

    def __init__(self, adres):
        self.adres = adres
        try:
            bilgi = _istek(adres, "/api/show", {"model": GOMME_MODELI}, sure=30)
        except Exception as e:
            raise ai_lab.GercekLabYok(f"gömme modeli {GOMME_MODELI} kurulu değil ({type(e).__name__}). "
                                      f"Kurulum: ollama pull {GOMME_MODELI}") from e
        with urllib.request.urlopen(adres + "/api/ps", timeout=30) as r:
            yuklu = [m["name"] for m in json.loads(r.read())["models"]]
        self.once_yukluydu = GOMME_MODELI in yuklu
        det = bilgi.get("details", {})
        with urllib.request.urlopen(adres+"/api/tags",timeout=30) as r:
            etiketler=json.loads(r.read()).get("models",[])
        secili=next((m for m in etiketler if m.get("name")==GOMME_MODELI),{})
        self.kayit = {"digest":secili.get("digest"),"boyut_bayt":secili.get("size"),
                      "lisans_ilk_satir":str(bilgi.get("license","")).splitlines()[:1],"cagrilar":[],
                      "model": GOMME_MODELI, "parametre": det.get("parameter_size"),
                      "num_ctx": " ".join((bilgi.get("parameters") or "").split()), "once_yukluydu": self.once_yukluydu}

    def __call__(self, metinler):
        govde = {"model": GOMME_MODELI, "input": metinler}
        if not self.once_yukluydu:
            govde["keep_alive"] = "5m"
        try:
            sonuc=_istek(self.adres,"/api/embed",govde)
            self.kayit["cagrilar"].append({"istek":govde,"yanit":sonuc})
            vectors=sonuc.get("embeddings")
            if not isinstance(vectors,list) or len(vectors)!=len(metinler):
                raise ai_lab.GercekLabYok("embed yanıtında eksik/fazla vektör")
            for v in vectors:
                if not isinstance(v,list) or len(v)!=384 or not any(v) or any(type(x) not in (int,float) or not math.isfinite(x) for x in v):
                    raise ai_lab.GercekLabYok("embed boyutu/değerleri geçersiz")
            return vectors
        except urllib.error.HTTPError as e:
            hata=e.read().decode("utf-8",errors="replace")
            self.kayit["cagrilar"].append({"istek":govde,"hata":hata,"http":e.code})
            raise RuntimeError(f"Ollama /api/embed HTTP {e.code}: {hata}") from e


    def kapat(self):
        if self.once_yukluydu:
            self.kayit["temizlik"]="korundu: kullanıcı önceden yüklemişti"
            return
        import time
        sonuc=_istek(self.adres,"/api/generate",{"model":GOMME_MODELI,"keep_alive":0,"stream":False},sure=30)
        self.kayit["bosaltma_yaniti"]=sonuc
        son=time.monotonic()+20
        while True:
            with urllib.request.urlopen(self.adres+"/api/ps",timeout=30) as r:
                yuklu=[m["name"] for m in json.loads(r.read())["models"]]
            self.kayit["model_bosaltildi"]=GOMME_MODELI not in yuklu
            if self.kayit["model_bosaltildi"] or time.monotonic()>=son: break
            time.sleep(0.1)


def deney(getir_ve_olc):
    idler = [p[0] for p in PARCALAR]
    with ai_lab.SohbetOturumu() as oturum:
        gom = _Gomucu(oturum.adres)
        hata=None
        try:
            pv = gom([t for _, t in PARCALAR])
            sv = gom([s for s, _ in SORULAR])
            kayitlar = []
            for (soru, altin), q in zip(SORULAR, sv):
                r3 = getir_ve_olc(list(q), list(idler), [list(v) for v in pv], list(altin), K)
                r1 = getir_ve_olc(list(q), list(idler), [list(v) for v in pv], list(altin), 1)
                kayitlar.append({"soru": soru, "altin": altin, "k3": r3, "k1": r1,
                                 "ilk": r3["sirali"][0], "altin_sira": (r3["sirali"].index(altin[0]) + 1) if altin[0] in r3["sirali"] else None})
        except Exception as e:
            hata=e
        finally:
            try:
                gom.kapat()
            except Exception as e:
                if hata is None: hata=e
        if hata is not None:
            ai_lab.kanit_yaz("temel-retrieval-hata",{"kaynak":"gercek","kabul":False,"ders":"ai-temel-22",
                "ortam":{"model":{"ad":GOMME_MODELI}},"gomme":gom.kayit,
                "hata":f"{type(hata).__name__}: {hata}"})
            raise ai_lab.GercekLabYok(f"Gerçek gömme deneyi başarısız: {hata}") from hata
        ortam = dict(oturum.kayit)
    ortam["temizlik"] = oturum.kayit.get("temizlik")
    ortam["gomme"] = gom.kayit
    ortam["sohbet_oturumu_modeli"]=ortam.get("model")
    ortam["sohbet_oturumu_temizligi"]=ortam.get("temizlik")
    ortam["model_once_yukluydu"]=gom.once_yukluydu
    ortam["temizlik"]={"model_bosaltildi":gom.kayit.get("model_bosaltildi") if not gom.once_yukluydu else "korundu: kullanıcı önceden yüklemişti"}
    ortam["model"]={"ad":GOMME_MODELI,"digest":gom.kayit.get("digest"),"boyut":gom.kayit.get("boyut_bayt")}
    ortam["sinir"]="Ortak oturum sunucu sahipliği için kullanılır;sohbet modelinden yanıt üretilmez."
    return {"ortam": ortam, "k": K, "parca_sayisi": len(PARCALAR), "soru_sayisi": len(SORULAR),
            "kayitlar": kayitlar, "vektorler": {"parca": pv, "soru": sv}, "idler": idler, "parcalar":PARCALAR,"sorular":SORULAR}


def _ort(xs):
    return round(sum(xs) / len(xs), 4) if xs else 0.0


def ozet(r):
    k = r["kayitlar"]
    return {"soru": len(k), "boyut": len(r["vektorler"]["parca"][0]),
            "anma_k3": _ort([x["k3"]["anma"] for x in k]), "anma_k1": _ort([x["k1"]["anma"] for x in k]),
            "mrr": _ort([x["k3"]["mrr"] for x in k]), "ndcg_k3": _ort([x["k3"]["ndcg"] for x in k]),
            "isabet_k3": sum(x["k3"]["isabet"] for x in k), "isabet_k1": sum(x["k1"]["isabet"] for x in k)}


def goster(getir_ve_olc):
    """Çalıştır düğmesi: gerçek gömmelerle retrieval kalitesi."""
    r = deney(getir_ve_olc)
    o = r["ortam"]
    print(f"Gömme: {o['gomme']['model']} ({o['gomme']['parametre']}, {o['gomme']['num_ctx']}) · "
          f"{r['parca_sayisi']} parça × {len(r['vektorler']['parca'][0])} boyut · {r['soru_sayisi']} soru · k={r['k']}\n")
    for x in r["kayitlar"]:
        print(f"S: {x['soru']}  (altın {x['altin']}, altın sıra: {x['altin_sira']})")
        print(f"   k=3 → getirilen ilk: {x['ilk']} · anma {x['k3']['anma']} mrr {x['k3']['mrr']} ndcg {x['k3']['ndcg']}")
    oz = ozet(r)
    print(f"\nOrtalama: recall@3 {oz['anma_k3']} vs recall@1 {oz['anma_k1']} · MRR {oz['mrr']} · nDCG@3 {oz['ndcg_k3']} "
          f"· isabet@3 {oz['isabet_k3']}/{oz['soru']} vs isabet@1 {oz['isabet_k1']}/{oz['soru']}")
    print("Kanıt:", ai_lab.kanit_yaz("temel-retrieval-calistir", {"kaynak": "gercek", "kabul": False, "ders": "ai-temel-22",
                                                                 "ortam": o, "ozet": oz, "deney":r, "sinir":"Sentetik derlemde gerçek gömme;genel RAG kalite/güvenlik kabulü değil."}))
