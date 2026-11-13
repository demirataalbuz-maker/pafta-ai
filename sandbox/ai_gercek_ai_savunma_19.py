# -*- coding: utf-8 -*-
"""ai-savunma-19 gerçek deneyi: kiracı yalıtımı, çapraz kiracı kaydı en benzer olsa bile getirmez.

Deney GERÇEK gömme modeliyle (all-minilm:22m) bir kiracı-a sorgusu ile vektör kayıtları arasındaki
kosinüs benzerliğini (gerçek `skor`) hesaplar. Kayıtların biri kiracı-b'ye aittir ve sorguya en
benzer olandır. Öğrencinin `yetkili_vektorleri_getir` işlevi yalnız aynı kiracının (a) ve skor eşiğini
geçen kayıtlarını getirir.

Kritik ölçüm: en yüksek gerçek embedding skoruna sahip kayıt kiracı-b'den geliyorsa sonuca GİRMEZ;
getirilen bütün kayıtlar kiracı-a'dır. Böylece benzerlik sıralaması kiracı sınırını aşamaz — çapraz
kiracı sızıntısı olmaz.

Kayıtlar sentetiktir. Gömme modeli bu deney tarafından yüklendiyse boşaltılır (kullanıcınınkine
dokunulmaz). Geçersiz vektör deneyi durdurur. Filtresi başka kiracıya çevrilmiş ikinci bir sorgu da sınanır.
`yetkili_vektorleri_getir_referans` yalnız test içindir.
"""
import json
import math
import urllib.error
import urllib.request

import ai_lab

GOMME_MODELI = "all-minilm:22m"
SORGU_METNI = "İade süresi kaç gündür?"
POLITIKA = {"izinli_kiracilar": ["a", "b"], "min_skor": 0.3, "max_top_k": 5,
            "filtre_zorunlu": True, "capraz_kiraci": False}
SORGU = {"id": "q-1", "kiraci": "a", "filtre_kiraci": "a", "top_k": 3}
# Aynı kiracıdan, filtresi başka kiracıya ayarlanmış (manipüle) sorgu: boş sonuç üretmelidir
FILTRE_SORGUSU = {"id": "q-2", "kiraci": "a", "filtre_kiraci": "b", "top_k": 3}
# (id, kiraci, metin) — b-iade kiracı-b'ye ait ve sorguya en benzer
KAYIT_TANIM = [
    ("a-iade", "a", "İade süresi teslimattan sonra 14 gündür."),
    ("b-iade", "b", "İade süresi kaç gündür? İade süresi 30 gündür."),
    ("a-kargo", "a", "140 TL üzeri siparişlerde kargo ücretsizdir."),
]


def _istek(adres, yol, govde, sure=120):
    req = urllib.request.Request(adres + yol, json.dumps(govde).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=sure) as r:
        return json.loads(r.read())


class _Gomucu:
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
        self.kayit = {"model": GOMME_MODELI, "parametre": det.get("parameter_size"), "once_yukluydu": self.once_yukluydu}

    def __call__(self, metinler):
        govde = {"model": GOMME_MODELI, "input": metinler}
        if not self.once_yukluydu:
            govde["keep_alive"] = 0
        try:
            return _istek(self.adres, "/api/embed", govde)["embeddings"]
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Ollama /api/embed HTTP {e.code}") from e


def _birim(v):
    boy = math.sqrt(sum(x * x for x in v))
    return [x / boy for x in v] if boy else list(v)


def _kosinus(a, b):
    ua, ub = _birim(a), _birim(b)
    return sum(x * y for x, y in zip(ua, ub))


def deney(yetkili_vektorleri_getir):
    metinler = [t[2] for t in KAYIT_TANIM]
    with ai_lab.SohbetOturumu() as oturum:
        gom = _Gomucu(oturum.adres)
        sorgu_vek = gom([SORGU_METNI])[0]
        kayit_vek = gom(metinler)
        ortam = dict(oturum.kayit)
    vektorler = [sorgu_vek] + list(kayit_vek or [])
    if len(vektorler) != len(metinler) + 1 or any(not isinstance(v, list) or not v or len(v) != len(sorgu_vek)
                                                    or any(type(x) not in (int, float) or not math.isfinite(x) for x in v)
                                                    or not any(v) for v in vektorler):
        raise ai_lab.GercekLabYok("gömme modeli eksik veya geçersiz vektör döndürdü; deney tamamlanmadı")
    ortam["gomme"] = gom.kayit
    kayitlar = []
    for (kid, kiraci, metin), vek in zip(KAYIT_TANIM, kayit_vek):
        skor = max(0.0, min(1.0, round(_kosinus(sorgu_vek, vek), 6)))
        kayitlar.append({"id": kid, "kiraci": kiraci, "skor": skor, "metin": metin})
    def pol():
        return dict(POLITIKA, izinli_kiracilar=list(POLITIKA["izinli_kiracilar"]))
    sonuc = yetkili_vektorleri_getir([dict(k) for k in kayitlar], dict(SORGU), pol())
    beklenen = yetkili_vektorleri_getir_referans([dict(k) for k in kayitlar], dict(SORGU), pol())
    filtre_sonuc = yetkili_vektorleri_getir([dict(k) for k in kayitlar], dict(FILTRE_SORGUSU), pol())
    en_yuksek = max(kayitlar, key=lambda k: k["skor"])
    gecerli = isinstance(sonuc, list) and all(isinstance(s, dict) for s in sonuc)
    sonuc_idler = [s.get("id") for s in sonuc] if gecerli else []
    sonuc_kiracilar = sorted({s.get("kiraci") for s in sonuc}) if gecerli else []
    ortam["ayarlar"] = {"sorgu": SORGU, "filtre_sorgusu": FILTRE_SORGUSU, "politika": POLITIKA, "vektor_boyutu": len(sorgu_vek)}
    return {"ortam": ortam, "sorgu_metni": SORGU_METNI, "kayitlar": kayitlar, "sonuc": sonuc,
            "beklenen": beklenen, "sonuc_dogru": sonuc == beklenen, "filtre_sonuc": filtre_sonuc,
            "sonuc_idler": sonuc_idler, "sonuc_kiracilar": sonuc_kiracilar,
            "en_yuksek_id": en_yuksek["id"], "en_yuksek_kiraci": en_yuksek["kiraci"],
            "en_yuksek_dislandi": en_yuksek["id"] not in sonuc_idler and en_yuksek["kiraci"] != SORGU["kiraci"],
            "capraz_sizinti": any(k != SORGU["kiraci"] for k in sonuc_kiracilar)}


def ozet(r):
    return {"kayit": len(r["kayitlar"]), "sonuc_idler": r["sonuc_idler"], "sonuc_kiracilar": r["sonuc_kiracilar"],
            "sonuc_dogru": r["sonuc_dogru"], "filtre_sorgusu_bos": r["filtre_sonuc"] == [],
            "en_yuksek_id": r["en_yuksek_id"], "en_yuksek_kiraci": r["en_yuksek_kiraci"],
            "en_yuksek_dislandi": r["en_yuksek_dislandi"], "capraz_sizinti": r["capraz_sizinti"],
            "skorlar": {k["id"]: k["skor"] for k in r["kayitlar"]}}


def goster(yetkili_vektorleri_getir):
    """Çalıştır düğmesi: gerçek embedding skoru + kiracı yalıtımı."""
    r = deney(yetkili_vektorleri_getir)
    o = r["ortam"]
    print(f"Gömme: {o['gomme']['model']} ({o['gomme']['parametre']}) · sorgu kiracısı: {SORGU['kiraci']!r} · sorgu: {r['sorgu_metni']!r}\n")
    for k in sorted(r["kayitlar"], key=lambda x: -x["skor"]):
        print(f"   {k['id']}: kiracı={k['kiraci']} skor={k['skor']:.4f} metin={k['metin'][:36]!r}")
    oz = ozet(r)
    print(f"\nEn yüksek embedding skoru: {oz['en_yuksek_id']} (kiracı {oz['en_yuksek_kiraci']})")
    print(f"Getirilen kayıtlar: {oz['sonuc_idler']} · kiracılar: {oz['sonuc_kiracilar']} · çapraz kiracı sızıntısı: {oz['capraz_sizinti']}")
    print(f"Referansla aynı: {oz['sonuc_dogru']} · filtresi kiracı-b'ye çevrilmiş sorgu boş döndü: {oz['filtre_sorgusu_bos']}")
    print("Not: benzerlik sıralaması kiracı sınırını aşamaz; kiracı filtresi skordan önce uygulanır.")
    print("Kanıt:", ai_lab.kanit_yaz("savunma-kiraci-calistir", {"kaynak": "gercek", "kabul": False,
                                                               "ders": "ai-savunma-19", "ortam": o, "ozet": oz,
                                                               "kayitlar": r["kayitlar"]}))


def yetkili_vektorleri_getir_referans(kayitlar, sorgu, politika):
    """Yalnız test içindir: politika/sorgu/kayıt doğrulaması ve kiracı yalıtımlı getirme."""
    import re
    kimlik = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")
    def skor_mu(x):
        return not isinstance(x, bool) and isinstance(x, (int, float)) and math.isfinite(x) and 0 <= x <= 1
    if not isinstance(politika, dict) or set(politika) != {"izinli_kiracilar", "min_skor", "max_top_k", "filtre_zorunlu", "capraz_kiraci"}:
        raise ValueError("politika şeması geçersiz")
    k = politika["izinli_kiracilar"]
    if not isinstance(k, list) or not k or len(set(map(str, k))) != len(k) or any(not isinstance(x, str) or not kimlik.fullmatch(x) for x in k):
        raise ValueError("kiracılar geçersiz")
    if not skor_mu(politika["min_skor"]) or type(politika["max_top_k"]) is not int or not 1 <= politika["max_top_k"] <= 20:
        raise ValueError("eşik/sınır geçersiz")
    if politika["filtre_zorunlu"] is not True or politika["capraz_kiraci"] is not False:
        raise ValueError("bayrak geçersiz")
    if not isinstance(sorgu, dict) or set(sorgu) != {"id", "kiraci", "filtre_kiraci", "top_k"}:
        raise ValueError("sorgu şeması geçersiz")
    if any(not isinstance(sorgu[a], str) or not kimlik.fullmatch(sorgu[a]) for a in ("id", "kiraci", "filtre_kiraci")):
        raise ValueError("sorgu kimliği geçersiz")
    if type(sorgu["top_k"]) is not int or sorgu["top_k"] < 1:
        raise ValueError("top_k geçersiz")
    if not isinstance(kayitlar, list):
        raise ValueError("kayıtlar liste olmalı")
    gorulen = set()
    for x in kayitlar:
        if not isinstance(x, dict) or set(x) != {"id", "kiraci", "skor", "metin"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(x["id"], str) or not kimlik.fullmatch(x["id"]) or x["id"] in gorulen:
            raise ValueError("kayıt kimliği geçersiz")
        gorulen.add(x["id"])
        if not isinstance(x["kiraci"], str) or not kimlik.fullmatch(x["kiraci"]) or not skor_mu(x["skor"]):
            raise ValueError("kayıt alanı geçersiz")
        if not isinstance(x["metin"], str) or any(ord(c) < 32 and c not in "\n\r\t" for c in x["metin"]):
            raise ValueError("metin geçersiz")
    if sorgu["kiraci"] not in k or sorgu["filtre_kiraci"] != sorgu["kiraci"] or sorgu["top_k"] > politika["max_top_k"]:
        return []
    uygun = [x for x in kayitlar if x["kiraci"] == sorgu["kiraci"] and x["skor"] >= politika["min_skor"]]
    uygun.sort(key=lambda x: (-x["skor"], x["id"]))
    return [{"id": x["id"], "kiraci": x["kiraci"], "skor": x["skor"], "metin": x["metin"]} for x in uygun[:sorgu["top_k"]]]
