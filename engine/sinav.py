# -*- coding: utf-8 -*-
"""Sınav kipi: süreli, ipuçsuz, çözümsüz deneme sınavı.

Soru havuzu bir yolun tahmin ve görev adımlarıdır. Kapsam bütün yol, bir sertifika
(tracks/<id>/kazanim.json) ya da sertifikanın tek bölümü olabilir. Sertifika kapsamında
sorular bölüm ağırlıklarına, yol kapsamında modüllerin ders sayısına göre dağıtılır;
aynı dersten ikinci soru, başka ders kalmayınca seçilir. Cevaplar sınav sürerken
kaydedilir, puanlama sınav bitince yapılır: tahminler dersteki gibi gerçek çıktıyla,
görevler görev testleriyle.
"""
import random
import time
from concurrent.futures import ThreadPoolExecutor

from engine.runners import argv_coz, for_step

SURE = {"tahmin": 120, "gorev": 360}     # soru başına saniye
VARSAYILAN_GECME = 70
CEVAP_SINIRI = 20_000
GECIKME_PAYI = 10                        # süre bittikten sonra gelen son kayıt için saniye


def normalize(text):
    lines = [l.rstrip() for l in (text or "").replace("\r\n", "\n").split("\n")]
    while lines and not lines[-1]:
        lines.pop()
    while lines and not lines[0]:
        lines.pop(0)
    return "\n".join(lines)


def tahmin_calistir(runner, step):
    """Tahmin adımının gerçek sonucu: (sonuç, çıktı metni)."""
    if step.get("gercek") is not None:
        # Çalıştırılamayan dil (C, PHP): gerçek çıktıyı ders yazarı vermiştir
        res = {"status": "ok", "segs": [["out", step["gercek"]]], "error": None}
    else:
        runner = for_step(runner, step)
        res = runner.run(step["code"], step.get("stdin", ""), step.get("setup"), argv=argv_coz(step.get("meta")))
    return res, "".join(t for k, t in res.get("segs", []) if k == "out")


def tahmin_dogru(tahmin, res, gercek):
    """Dersteki kural: çıktı satır satır aynı olmalı; hata bekleniyorsa hatanın adı yeter."""
    tahmin = normalize(tahmin)
    err = res.get("error")
    if err:
        g = tahmin.lower()
        return bool(g) and (err["type"].lower() in g or g in ("hata", "error"))
    return tahmin == normalize(gercek)


# ── havuz ve seçim ───────────────────────────────────────────────────────────
def sertifika_bul(kazanim, sid):
    return next((s for s in kazanim["sertifikalar"] if s["id"] == sid), None)


def havuz(lib, tid, sertifika=None, bolum=None, biten=None):
    """(sorular, gruplar). Her soru {lesson, step, kind, gruplar}; gruplar {anahtar: {baslik, agirlik}}.

    biten verilirse yalnızca o kümedeki dersler havuza girer.
    """
    outline = lib.outline(tid)
    gruplar, ders_grup = {}, {}
    if sertifika:
        sert = sertifika_bul(lib.kazanim(tid, outline), sertifika)
        if sert is None:
            raise ValueError(f"bu yolda {sertifika} sertifikası yok")
        for b in sert["bolumler"]:
            if bolum and b["kod"] != bolum:
                continue
            gruplar[b["kod"]] = {"baslik": b["baslik"], "agirlik": b.get("agirlik") or 1}
            for m in b["maddeler"]:
                for lid in m["dersler"]:
                    ders_grup.setdefault(lid, [])
                    if b["kod"] not in ders_grup[lid]:
                        ders_grup[lid].append(b["kod"])
        if bolum and not gruplar:
            raise ValueError(f"{sertifika} içinde {bolum} bölümü yok")
    else:
        for m in outline["modules"]:
            dersler = [l["id"] for l in m["lessons"] if not l.get("missing")]
            if not dersler:
                continue
            anahtar = f"M{m['index']:02d}"
            gruplar[anahtar] = {"baslik": m["title"], "agirlik": len(dersler)}
            for lid in dersler:
                ders_grup[lid] = [anahtar]
    sorular = []
    for lid in outline["order"]:
        if lid not in ders_grup or (biten is not None and lid not in biten):
            continue
        for i, st in enumerate(lib.lesson(tid, lid)["steps"]):
            if (st.get("meta") or {}).get("motor") == "ai-gercek":
                continue    # gerçek model deneyi: süreli sınavda kurulum/çağrı süresine bağlanmaz
            if (st["kind"] == "gorev" and st.get("test")) or (st["kind"] == "tahmin" and st.get("code")):
                sorular.append({"lesson": lid, "step": i, "kind": st["kind"], "gruplar": ders_grup[lid]})
    return sorular, gruplar


def _kota(adet, agirlik, kapasite):
    """adet soruyu ağırlıklara göre böler (en büyük kalan yöntemi); hiçbir grup kapasitesini aşmaz."""
    kota = dict.fromkeys(agirlik, 0)
    kalan = adet
    while kalan > 0:
        acik = [g for g in agirlik if kota[g] < kapasite[g]]
        if not acik:
            break
        toplam = sum(agirlik[g] for g in acik)
        pay = {g: kalan * agirlik[g] / toplam for g in acik}
        ek = {g: min(int(pay[g]), kapasite[g] - kota[g]) for g in acik}
        verilen = sum(ek.values())
        # tam kısımlardan artan koltuklar kesri en büyük olanlara; kapasitesi dolan grubun payı sonraki tura kalır
        for g in sorted(acik, key=lambda g: (pay[g] - int(pay[g]), agirlik[g]), reverse=True):
            if verilen >= kalan:
                break
            if pay[g] > int(pay[g]) and kota[g] + ek[g] < kapasite[g]:
                ek[g] += 1
                verilen += 1
        for g in acik:
            kota[g] += ek[g]
        kalan -= verilen
    return kota


def sec(sorular, gruplar, adet, tur="karisik", rng=None):
    """Havuzdan adet soru: grup kotalarına uyar, karışıkta tahmin/görev yarı yarıya, dersleri yayar."""
    rng = rng or random.Random()
    if tur in ("tahmin", "gorev"):
        sorular = [s for s in sorular if s["kind"] == tur]
    adet = max(0, min(adet, len(sorular)))
    mevcut = {g: [s for s in sorular if g in s["gruplar"]] for g in gruplar}
    kota = _kota(adet, {g: gruplar[g]["agirlik"] for g in gruplar if mevcut[g]},
                 {g: len(mevcut[g]) for g in gruplar if mevcut[g]})
    secilen, alinan, ders_sayac = [], set(), {}

    def al(adaylar):
        adaylar = [s for s in adaylar if (s["lesson"], s["step"]) not in alinan]
        if not adaylar:
            return False
        if tur == "karisik":
            tahmin_n = sum(1 for s in secilen if s["kind"] == "tahmin")
            istenen = "tahmin" if tahmin_n < (len(secilen) + 1) / 2 else "gorev"
            uygun = [s for s in adaylar if s["kind"] == istenen]
            adaylar = uygun or adaylar
        en_az = min(ders_sayac.get(s["lesson"], 0) for s in adaylar)
        s = rng.choice([s for s in adaylar if ders_sayac.get(s["lesson"], 0) == en_az])
        secilen.append(s)
        alinan.add((s["lesson"], s["step"]))
        ders_sayac[s["lesson"]] = ders_sayac.get(s["lesson"], 0) + 1
        return True

    for g in sorted(kota, key=lambda g: -kota[g]):
        for _ in range(kota[g]):
            if not al(mevcut[g]):
                break
    while len(secilen) < adet and al(sorular):    # gruplar örtüştüyse eksik kalanı havuzun geri kalanından
        pass
    rng.shuffle(secilen)
    return secilen


def sure_hesapla(sorular):
    return sum(SURE[s["kind"]] for s in sorular)


# ── ön yüze giden soru ───────────────────────────────────────────────────────
def soru_gorunumu(lib, tid, dil, q):
    """Sınavda gösterilecek kadarı: tahminin açıklaması, ipuçları, testler ve çözüm yok."""
    les = lib.lesson(tid, q["lesson"])
    st = les["steps"][q["step"]]
    # lesson/step yalnızca Çalıştır'ın görev hazırlığını (setup) bulması için; ekranda gösterilmez
    out = {"lesson": q["lesson"], "step": q["step"], "kind": st["kind"], "title": st["title"],
           "meta": st.get("meta", {}), "stdin": st.get("stdin", "")}
    if dil in ("packets", "elastic"):
        # bu yollarda dil ve korpus dersin herhangi bir adımında tanımlı olabilir
        out["ders_dil"] = next((s["meta"]["dil"] for s in les["steps"] if s.get("meta", {}).get("dil")), None)
        out["ders_stdin"] = next((s["stdin"] for s in les["steps"] if s.get("stdin")), "")
    if st["kind"] == "tahmin":
        out["body"] = (st.get("body") or "").split("???")[0].rstrip()
        out["code"] = st.get("code", "")
        if st.get("code_dil"):
            out["code_dil"] = st["code_dil"]
    else:
        out["body"] = st.get("body", "")
        out["starter"] = st.get("starter", "")
    return out


# ── puanlama ─────────────────────────────────────────────────────────────────
def puanla(lib, runner_for, sinav, simdi=None):
    """Bitmiş sınavın sonucu: soru soru doğru/yanlış, gruplara göre döküm, geçme kararı."""
    simdi = simdi or time.time()
    tid = sinav["yol"]
    runner = runner_for(tid)
    cevaplar = sinav.get("cevaplar", {})

    def bir(no_q):
        no, q = no_q
        les = lib.lesson(tid, q["lesson"])
        st = les["steps"][q["step"]]
        cevap = cevaplar.get(str(no), "")
        satir = {"lesson": q["lesson"], "step": q["step"], "kind": q["kind"], "gruplar": q["gruplar"],
                 "title": st["title"] or ("Tahmin" if st["kind"] == "tahmin" else "Görev"),
                 "lesson_title": les["title"], "kazanim": les["kazanim"], "cevap": cevap,
                 "isaretli": no in sinav.get("isaretli", [])}
        if q["kind"] == "tahmin":
            res, gercek = tahmin_calistir(runner, st)
            err = res.get("error")
            satir["beklenen"] = normalize(gercek) + (f"\n{err['type']}: {err['msg']}" if err else "")
            satir["dogru"] = bool(cevap.strip()) and tahmin_dogru(cevap, res, gercek)
        elif not cevap.strip() or cevap == st.get("starter", ""):
            satir.update(dogru=False, durum="bos", kontroller=[])
        else:
            res = for_step(runner, st).test(cevap, st)
            satir["dogru"] = res.get("status") == "pass"
            satir["durum"] = res.get("status")
            satir["kontroller"] = [{"ok": bool(c.get("ok")), "msg": str(c.get("msg", ""))[:400]}
                                   for c in res.get("checks", [])[:20]]
            if res.get("error"):
                e = res["error"]
                satir["hata"] = f"{e.get('type', '')}: {e.get('msg', '')}"[:400]
        return satir

    with ThreadPoolExecutor(max_workers=4) as ex:
        sorular = list(ex.map(bir, enumerate(sinav["sorular"])))
    dogru = sum(1 for s in sorular if s["dogru"])
    toplam = len(sorular)
    gruplar = []
    for anahtar, g in sinav["gruplar"].items():
        ilgili = [s for s in sorular if anahtar in s["gruplar"]]
        if ilgili:
            gruplar.append({"anahtar": anahtar, "baslik": g["baslik"], "agirlik": g.get("agirlik"),
                            "dogru": sum(1 for s in ilgili if s["dogru"]), "toplam": len(ilgili)})
    yuzde = round(dogru / toplam * 100) if toplam else 0
    gecen = int(min(simdi, sinav["bitis"]) - sinav["baslangic"])
    return dict({k: sinav.get(k) for k in ("no", "yol", "yol_adi", "sertifika", "bolum", "kapsam", "tur", "havuz", "sure_sn", "gecme")},
                tarih=time.strftime("%Y-%m-%d %H:%M", time.localtime(sinav["baslangic"])), adet=toplam, dogru=dogru,
                yuzde=yuzde, gecti=yuzde >= sinav["gecme"], gecen_sn=max(0, gecen), gruplar=gruplar, sorular=sorular)


def ozet(sonuc):
    """Geçmiş listesi için kısa satır."""
    return {k: sonuc.get(k) for k in ("no", "tarih", "yol", "yol_adi", "kapsam", "tur", "adet", "dogru", "yuzde",
                                      "gecme", "gecti", "sure_sn", "gecen_sn")}
