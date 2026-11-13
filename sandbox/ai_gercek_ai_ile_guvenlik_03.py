# -*- coding: utf-8 -*-
"""ai-ile-guvenlik-03 (Embedding ile Güvenlik Korpusu ve Benzer Zafiyet Arama) gerçek deney modülü."""
import json
import math
import urllib.error
import urllib.request
import ai_lab

GOMME_MODELI = "all-minilm:22m"


def _vektor_dogrula(v):
    if not isinstance(v, list) or not v:
        raise ValueError("vektör boş olmayan liste olmalı")
    boy_kare = 0.0
    for x in v:
        if isinstance(x, bool) or not isinstance(x, (int, float)):
            raise ValueError("vektör elemanları sayısal olmalı")
        boy_kare += float(x) * float(x)
    if boy_kare <= 0.0:
        raise ValueError("sıfır vektör kullanılamaz")
    return math.sqrt(boy_kare)


def kosinus_benzerligi_referans(v1, v2):
    b1 = _vektor_dogrula(v1)
    b2 = _vektor_dogrula(v2)
    if len(v1) != len(v2):
        raise ValueError("vektör boyutları eşit olmalı")
    carpim = sum(float(a) * float(b) for a, b in zip(v1, v2))
    return round(carpim / (b1 * b2), 4)


def benzer_zafiyet_ara_referans(sorgu_vektoru, korpus, esik=0.75, en_cok=3):
    _vektor_dogrula(sorgu_vektoru)
    if not isinstance(korpus, list) or not korpus:
        raise ValueError("korpus boş olmayan liste olmalı")
    if isinstance(esik, bool) or not isinstance(esik, (int, float)) or esik < 0 or esik > 1:
        raise ValueError("eşik 0 ile 1 arasında olmalı")
    if isinstance(en_cok, bool) or not isinstance(en_cok, int) or en_cok < 1:
        raise ValueError("en_cok pozitif tam sayı olmalı")

    beklenen = {"kayit_id", "kategori", "vektor", "yama_ozeti"}
    gorulen = set()
    adaylar = []
    for k in korpus:
        if not isinstance(k, dict) or set(k.keys()) != beklenen:
            raise ValueError("korpus kaydı şeması geçersiz")
        kid = k["kayit_id"]
        if not isinstance(kid, str) or not kid.strip() or kid in gorulen:
            raise ValueError("kayıt kimliği geçersiz")
        gorulen.add(kid)
        if not isinstance(k["kategori"], str) or not k["kategori"].strip():
            raise ValueError("kategori boş olamaz")
        if not isinstance(k["yama_ozeti"], str) or not k["yama_ozeti"].strip():
            raise ValueError("yama özeti boş olamaz")
        skor = kosinus_benzerligi_referans(sorgu_vektoru, k["vektor"])
        if skor >= esik:
            adaylar.append({
                "kayit_id": kid,
                "kategori": k["kategori"],
                "benzerlik": skor,
                "yama_ozeti": k["yama_ozeti"],
            })

    adaylar.sort(key=lambda x: (-x["benzerlik"], x["kayit_id"]))
    return adaylar[:en_cok]


def esik_kalibrasyonu_olc_referans(sorgular, korpus, esik):
    if not isinstance(sorgular, list) or not sorgular:
        raise ValueError("sorgular boş olamaz")
    beklenen_s = {"sorgu_id", "beklenen_kategori", "vektor"}
    gorulen_s = set()
    dogru_eslesme = 0
    yanlis_eslesme = 0
    cevapsiz = 0

    for s in sorgular:
        if not isinstance(s, dict) or set(s.keys()) != beklenen_s:
            raise ValueError("sorgu şeması geçersiz")
        sid = s["sorgu_id"]
        if not isinstance(sid, str) or not sid.strip() or sid in gorulen_s:
            raise ValueError("sorgu kimliği geçersiz")
        gorulen_s.add(sid)
        bkat = s["beklenen_kategori"]
        if not isinstance(bkat, str) or not bkat.strip():
            raise ValueError("beklenen kategori boş olamaz")
        sonuclar = benzer_zafiyet_ara_referans(s["vektor"], korpus, esik, 1)
        if not sonuclar:
            if bkat == "bilinmeyen":
                dogru_eslesme += 1
            else:
                cevapsiz += 1
        else:
            en_iyi = sonuclar[0]
            if en_iyi["kategori"] == bkat:
                dogru_eslesme += 1
            else:
                yanlis_eslesme += 1

    toplam = len(sorgular)
    return {
        "dogru_eslesme": dogru_eslesme,
        "yanlis_eslesme": yanlis_eslesme,
        "cevapsiz": cevapsiz,
        "isabet_orani": round(dogru_eslesme / toplam, 4),
    }


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
            raise ai_lab.GercekLabYok(f"gömme modeli {GOMME_MODELI} kurulu değil ({type(e).__name__})") from e
        with urllib.request.urlopen(adres + "/api/ps", timeout=30) as r:
            yuklu = [m["name"] for m in json.loads(r.read())["models"]]
        self.once_yukluydu = GOMME_MODELI in yuklu
        self.kayit = {"model": GOMME_MODELI, "parametre": bilgi.get("details", {}).get("parameter_size")}

    def __call__(self, metinler):
        govde = {"model": GOMME_MODELI, "input": metinler}
        if not self.once_yukluydu:
            govde["keep_alive"] = 0
        try:
            return _istek(self.adres, "/api/embed", govde)["embeddings"]
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Ollama /api/embed HTTP {e.code}") from e


def deney(kosinus_benzerligi, benzer_zafiyet_ara, esik_kalibrasyonu_olc):
    korpus_metinleri = [
        ("ZAF-SQL-1", "sql_enjeksiyonu", "SQL sorgusunda kullanıcı girdisi doğrudan string birleştirme ile çalıştırılıyor.", "Parametreli sorgu kullan."),
        ("ZAF-SQL-2", "sql_enjeksiyonu", "Veritabanı SELECT ifadesinde filtresiz parametre ekleme zafiyeti.", "Prepared statement zorla."),
        ("ZAF-PATH-1", "yol_gecisi", "Dosya okuma aracında ../ dizin geçişi kontrolü eksik.", "realpath ve kök dizin kilidi uygula."),
        ("ZAF-SSRF-1", "ssrf", "Kullanıcının verdiği URL sunucu tarafından doğrudan iç ağa (169.254.169.254) çağrılıyor.", "Özel IP aralıklarını engelle."),
    ]
    sorgu_metinleri = [
        ("sorgu-sql", "sql_enjeksiyonu", "Kullanıcı adı SQL SELECT cümlesine doğrudan ekleniyor."),
        ("sorgu-path", "yol_gecisi", "Dosya yolunda üst klasöre (../) çıkış engellenmemiş."),
        ("sorgu-ssrf", "ssrf", "Sunucu iç metaveri IP adresine (169.254.169.254) HTTP isteği atıyor."),
    ]

    with ai_lab.SohbetOturumu() as oturum:
        gom = _Gomucu(oturum.adres)
        k_vekler = gom([m[2] for m in korpus_metinleri])
        s_vekler = gom([s[2] for s in sorgu_metinleri])
        ortam = dict(oturum.kayit)
    ortam["temizlik"] = oturum.kayit.get("temizlik")
    ortam["gomme"] = gom.kayit

    canli_korpus = [
        {
            "kayit_id": korpus_metinleri[i][0],
            "kategori": korpus_metinleri[i][1],
            "vektor": list(k_vekler[i]),
            "yama_ozeti": korpus_metinleri[i][3],
        }
        for i in range(len(korpus_metinleri))
    ]
    canli_sorgular = [
        {
            "sorgu_id": sorgu_metinleri[i][0],
            "beklenen_kategori": sorgu_metinleri[i][1],
            "vektor": list(s_vekler[i]),
        }
        for i in range(len(sorgu_metinleri))
    ]

    benzerlik_sql = kosinus_benzerligi(canli_sorgular[0]["vektor"], canli_korpus[0]["vektor"])
    benzerlik_sql_ref = kosinus_benzerligi_referans(canli_sorgular[0]["vektor"], canli_korpus[0]["vektor"])

    arama_sql = benzer_zafiyet_ara(canli_sorgular[0]["vektor"], canli_korpus, 0.3, 2)
    arama_sql_ref = benzer_zafiyet_ara_referans(canli_sorgular[0]["vektor"], canli_korpus, 0.3, 2)

    kalibrasyon = esik_kalibrasyonu_olc(canli_sorgular, canli_korpus, 0.3)
    kalibrasyon_ref = esik_kalibrasyonu_olc_referans(canli_sorgular, canli_korpus, 0.3)

    kontroller = {
        "kosinus_uyumu": benzerlik_sql == benzerlik_sql_ref,
        "arama_uyumu": arama_sql == arama_sql_ref and len(arama_sql) >= 1,
        "kalibrasyon_uyumu": kalibrasyon == kalibrasyon_ref and kalibrasyon["dogru_eslesme"] >= 2,
        "cihaz_dogrulandi": ai_lab.cihaz_dogrulandi(ortam.get("bellek")),
        "kaynak_temizlendi": ai_lab.kaynak_temizlendi(ortam.get("temizlik")),
    }

    return {
        "ortam": ortam,
        "ayarlar": {"gomme_modeli": GOMME_MODELI, "esik": 0.3, "boyut": len(k_vekler[0])},
        "arama_sql": arama_sql,
        "kalibrasyon": kalibrasyon,
        "kontroller": kontroller,
        "ozet": {
            "gomme_modeli": GOMME_MODELI,
            "boyut": len(k_vekler[0]),
            "sql_benzerlik": benzerlik_sql,
            "isabet_orani": kalibrasyon["isabet_orani"],
            "dogru_eslesme": kalibrasyon["dogru_eslesme"],
        },
    }


def goster(kosinus_benzerligi, benzer_zafiyet_ara, esik_kalibrasyonu_olc):
    r = deney(kosinus_benzerligi, benzer_zafiyet_ara, esik_kalibrasyonu_olc)
    o = r["ozet"]
    print(f"Gömme modeli: {o['gomme_modeli']} ({o['boyut']} boyut)")
    print(f"SQL sorgu-korpus benzerliği: {o['sql_benzerlik']}")
    print(f"Kalibrasyon: doğru={o['dogru_eslesme']}, isabet oranı={o['isabet_orani']}")
    yol = ai_lab.kanit_yaz("ile-guvenlik-03-embedding-calistir", {
        "kaynak": "gercek",
        "kabul": False,
        "ders": "ai-ile-guvenlik-03",
        "ortam": r["ortam"],
        "ayarlar": r["ayarlar"],
        "ozet": o,
    })
    print("Kanıt:", yol)
    return r
