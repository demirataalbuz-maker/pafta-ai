# -*- coding: utf-8 -*-
"""ai-guvence-31 gerçek deneyi: embedding inversion. Gerçek bir gömme modeli (all-MiniLM-L6-v2, Ollama)
depolanan metinleri vektöre çevirir; saldırgan yalnız vektöre bakarak kaynağı geri çıkarır. İki sızıntı
ölçülür: (1) parafraz geri-çıkarma — bir metnin yeniden yazılmışı bile en yakın komşu aramasıyla özgün
kaynağa eşlenir (recovery@k); (2) nitelik çıkarımı — gömmeye bakarak hassas bir nitelik tahmin edilir.

Bütün kayıtlar sentetik ve kurgusaldır. Model bu deney tarafından yüklendiyse sonunda boşaltılır.
"""
import json
import math
import urllib.error
import urllib.request

import ai_lab

GOMME_MODELI = "all-minilm:22m"
# Kurgusal hasta kayıtları: nitelik = kan şekeri yüksek (1) / normal (0). Her kaydın bir parafrazı var.
KAYITLAR = [
    ("h1", "Birinci hasta düzenli yürüyüş yapıyor ve kan şekeri değerleri normal.", 0),
    ("h2", "İkinci hastanın kan şekeri yüksek, doktor insülin önerdi.", 1),
    ("h3", "Üçüncü hasta sağlıklı besleniyor, şeker değerleri normal seyrediyor.", 0),
    ("h4", "Dördüncü hastada yüksek kan şekeri tespit edildi ve tedavi başladı.", 1),
    ("h5", "Beşinci hasta sporu bıraktı ama kan şekeri hâlâ normal.", 0),
    ("h6", "Altıncı hastanın şekeri yüksek çıktı, diyet listesi verildi.", 1),
    ("h7", "Yedinci hasta düzenli kontrole geliyor, kan şekeri normal.", 0),
    ("h8", "Sekizinci hastada kan şekeri yüksekliği sürüyor, ilaç dozu artırıldı.", 1),
]
PARAFRAZ = {
    "h1": "1 numaralı hasta sık sık yürüyor; şeker ölçümleri olağan sınırlarda.",
    "h2": "2. hastanın glikozu fazla olduğundan hekim insülin yazdı.",
    "h3": "Üç numaralı kişi dengeli yiyor ve kan şekeri normal gidiyor.",
    "h4": "4. hastada şeker yüksekliği bulundu, tedaviye geçildi.",
    "h5": "Beşinci kişi artık spor yapmıyor fakat glikoz değeri normal.",
    "h6": "Altı numaralı hastanın şekeri yükseldi, beslenme programı hazırlandı.",
    "h7": "Yedinci hasta kontrollerini aksatmıyor; şekeri normal.",
    "h8": "8. hastada yüksek glikoz devam ediyor, ilaç miktarı yükseltildi.",
}
K = 3


def _birim(v):
    boy = math.sqrt(sum(x * x for x in v))
    return [x / boy for x in v] if boy else list(v)


def yakin_komsu_ref(hedef, adaylar, k):
    q = _birim(hedef)
    skor = [sum(a * b for a, b in zip(_birim(v), q)) for v in adaylar]
    return sorted(range(len(adaylar)), key=lambda i: (-skor[i], i))[:k]


def referans_inversion(hedef, aday_vekler, aday_idler, dogru_id, k, *, normalize=True):
    if normalize:
        sira = yakin_komsu_ref(hedef, aday_vekler, k)
    else:
        skor = [sum(a * b for a, b in zip(v, hedef)) for v in aday_vekler]  # normalize yok: uzunluk yanlılığı
        sira = sorted(range(len(aday_vekler)), key=lambda i: (-skor[i], i))[:k]
    sirali = [aday_idler[i] for i in sira]
    return {"sirali": sirali, "recovery1": bool(sirali) and sirali[0] == dogru_id, "recoveryk": dogru_id in sirali}


def merkez_sinifla_ref(vekler, etiketler):
    """Bırak-biri-dışarıda en yakın merkez sınıflandırması: gömmeden niteliğin tahmin doğruluğu."""
    n = len(vekler)
    dogru = 0
    for i in range(n):
        merkez = {}
        for e in set(etiketler):
            grup = [vekler[j] for j in range(n) if j != i and etiketler[j] == e]
            if grup:
                merkez[e] = [sum(c) / len(grup) for c in zip(*grup)]
        if not merkez:
            continue
        tahmin = min(merkez, key=lambda e: sum((a - b) ** 2 for a, b in zip(vekler[i], merkez[e])))
        dogru += (tahmin == etiketler[i])
    return round(dogru / n, 4)


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
        self.kayit = {"model": GOMME_MODELI, "parametre": bilgi.get("details", {}).get("parameter_size")}

    def __call__(self, metinler):
        govde = {"model": GOMME_MODELI, "input": metinler}
        if not self.once_yukluydu:
            govde["keep_alive"] = 0
        try:
            return _istek(self.adres, "/api/embed", govde)["embeddings"]
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Ollama /api/embed HTTP {e.code}") from e


def deney(inversion_raporu):
    idler = [k[0] for k in KAYITLAR]
    with ai_lab.SohbetOturumu() as oturum:
        gom = _Gomucu(oturum.adres)
        ov = gom([t for _, t, _ in KAYITLAR])           # özgün kayıt gömmeleri (depolanan)
        pv = gom([PARAFRAZ[i] for i in idler])          # parafraz gömmeleri (saldırganın sorgusu)
        kayitlar = []
        for i, dogru in enumerate(idler):
            r = inversion_raporu(list(pv[i]), [list(v) for v in ov], list(idler), dogru, K)
            kayitlar.append({"dogru": dogru, "sirali": r["sirali"], "recovery1": r["recovery1"], "recoveryk": r["recoveryk"]})
        nitelik = merkez_sinifla_ref(ov, [e for _, _, e in KAYITLAR])
        ortam = dict(oturum.kayit)
    ortam["temizlik"] = oturum.kayit.get("temizlik")
    ortam["gomme"] = gom.kayit
    return {"ortam": ortam, "k": K, "kayit_sayisi": len(KAYITLAR), "boyut": len(ov[0]),
            "kayitlar": kayitlar, "nitelik_dogrulugu": nitelik, "vektorler": {"orijinal": ov, "parafraz": pv}, "idler": idler}


def ozet(r):
    k = r["kayitlar"]
    return {"kayit": len(k), "boyut": r["boyut"],
            "recovery1": round(sum(x["recovery1"] for x in k) / len(k), 4),
            "recoveryk": round(sum(x["recoveryk"] for x in k) / len(k), 4),
            "nitelik_dogrulugu": r["nitelik_dogrulugu"]}


def goster(inversion_raporu):
    """Çalıştır düğmesi: embedding inversion deneyi."""
    r = deney(inversion_raporu)
    o = r["ortam"]
    print(f"Gömme: {o['gomme']['model']} ({o['gomme']['parametre']}) · {r['kayit_sayisi']} kayıt × {r['boyut']} boyut · k={r['k']}\n")
    for x, (i, t, _) in zip(r["kayitlar"], KAYITLAR):
        isabet = "✓" if x["recovery1"] else ("~" if x["recoveryk"] else "✗")
        print(f"[{isabet}] {i}: parafrazdan geri çıkan ilk {r['k']}: {x['sirali']} (doğru {x['dogru']})")
    oz = ozet(r)
    print(f"\nParafraz geri-çıkarma: recovery@1 {oz['recovery1']}, recovery@{r['k']} {oz['recoveryk']} "
          f"({r['kayit_sayisi']} kayıt üzerinden)")
    print(f"Nitelik çıkarımı (gömmeden kan şekeri durumu): en yakın merkez doğruluğu {oz['nitelik_dogrulugu']} (0.5 = şans)")
    print("Kanıt:", ai_lab.kanit_yaz("guvence-inversion-calistir", {"kaynak": "gercek", "kabul": False, "ders": "ai-guvence-31",
                                                                   "ortam": o, "ozet": oz}))
