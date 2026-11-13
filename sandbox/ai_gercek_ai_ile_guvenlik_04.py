# -*- coding: utf-8 -*-
"""ai-ile-guvenlik-04 (AST Ön-Elemesi ve LLM ile Kaynak–Evye Triyajı) gerçek deney modülü."""
import ast
import ai_lab

TEHLIKELI_EVYELER = ("eval", "exec", "system", "run", "Popen", "execute")


def _cagri_adi(func_node):
    if isinstance(func_node, ast.Name):
        return func_node.id
    if isinstance(func_node, ast.Attribute):
        return func_node.attr
    return None


def ast_evye_adaylari_cikar_referans(kaynak_kodu):
    if not isinstance(kaynak_kodu, str) or not kaynak_kodu.strip():
        raise ValueError("kaynak kodu boş olmayan string olmalı")
    try:
        agac = ast.parse(kaynak_kodu)
    except SyntaxError as e:
        raise ValueError("geçersiz Python sözdizimi") from e

    adaylar = []
    for dugum in ast.walk(agac):
        if isinstance(dugum, ast.Call) and dugum.args:
            ad = _cagri_adi(dugum.func)
            if ad in TEHLIKELI_EVYELER:
                ilk = dugum.args[0]
                sabit_mi = isinstance(ilk, ast.Constant)
                adaylar.append({
                    "satir_no": dugum.lineno,
                    "evye_adi": ad,
                    "arguman_turu": "sabit_deger" if sabit_mi else "dinamik_girdi",
                })
    adaylar.sort(key=lambda x: (x["satir_no"], x["evye_adi"]))
    return adaylar


def kaynak_evye_triyaji_referans(adaylar, model_kararlari):
    if not isinstance(adaylar, list) or not adaylar:
        raise ValueError("adaylar boş olamaz")
    if not isinstance(model_kararlari, dict):
        raise ValueError("model kararları sözlük olmalı")

    beklenen_a = {"satir_no", "evye_adi", "arguman_turu"}
    gorulen = set()
    gercek_acik_satirlari = []
    yanlis_alarm_satirlari = []
    kacirilan_satirlar = []

    for a in adaylar:
        if not isinstance(a, dict) or set(a.keys()) != beklenen_a:
            raise ValueError("aday şeması geçersiz")
        sno = a["satir_no"]
        if isinstance(sno, bool) or not isinstance(sno, int) or sno < 1 or sno in gorulen:
            raise ValueError("satır numarası geçersiz")
        gorulen.add(sno)
        if a["evye_adi"] not in TEHLIKELI_EVYELER:
            raise ValueError("evye adı geçersiz")
        atur = a["arguman_turu"]
        if atur not in ("sabit_deger", "dinamik_girdi"):
            raise ValueError("argüman türü geçersiz")
        anahtar = str(sno)
        if anahtar not in model_kararlari:
            raise ValueError("model kararı eksik")
        karar = model_kararlari[anahtar]
        if karar not in ("tehlikeli", "guvenli"):
            raise ValueError("model kararı geçersiz")

        if atur == "dinamik_girdi":
            if karar == "tehlikeli":
                gercek_acik_satirlari.append(sno)
            else:
                kacirilan_satirlar.append(sno)
        else:
            if karar == "tehlikeli":
                yanlis_alarm_satirlari.append(sno)

    alarm_sayisi = len(gercek_acik_satirlari) + len(yanlis_alarm_satirlari)
    yanlis_pozitif_orani = round(len(yanlis_alarm_satirlari) / alarm_sayisi, 4) if alarm_sayisi else 0.0
    return {
        "gercek_acik_satirlari": sorted(gercek_acik_satirlari),
        "yanlis_alarm_satirlari": sorted(yanlis_alarm_satirlari),
        "kacirilan_satirlar": sorted(kacirilan_satirlar),
        "yanlis_pozitif_orani": yanlis_pozitif_orani,
    }


def hibrit_triyaj_kapisi_referans(kaynak_kodu, model_kararlari):
    adaylar = ast_evye_adaylari_cikar_referans(kaynak_kodu)
    triyaj = kaynak_evye_triyaji_referans(adaylar, model_kararlari)
    onaylanan = sorted(set(triyaj["gercek_acik_satirlari"]) | set(triyaj["kacirilan_satirlar"]))
    elenen = sorted(a["satir_no"] for a in adaylar if a["arguman_turu"] == "sabit_deger")
    return {
        "onaylanan_evye_satirlari": onaylanan,
        "elenen_sabit_satirlar": elenen,
        "model_yanlis_pozitif_orani": triyaj["yanlis_pozitif_orani"],
        "hibrit_yanlis_pozitif_orani": 0.0,
    }


def deney(ast_evye_adaylari_cikar, kaynak_evye_triyaji, hibrit_triyaj_kapisi):
    ornek_kod = (
        "import os\n"
        "import subprocess\n"
        "def islem(kullanici_verisi):\n"
        "    a = subprocess.run('uptime')\n"
        "    b = os.system(kullanici_verisi)\n"
        "    c = eval('10 + 20')\n"
        "    return a, b, c\n"
    )
    adaylar = ast_evye_adaylari_cikar(ornek_kod)
    adaylar_ref = ast_evye_adaylari_cikar_referans(ornek_kod)

    with ai_lab.SohbetOturumu() as oturum:
        c = oturum.sohbet(
            [
                {
                    "role": "system",
                    "content": "Sen statik kod analistisin. Hangi satırda dış kullanıcı girdisi doğrudan os.system içine giriyor?",
                },
                {"role": "user", "content": ornek_kod},
            ],
            seed=904,
            sicaklik=0.1,
            en_fazla=90,
        )
        canli_yanit = (c.get("icerik") if isinstance(c, dict) else str(c or "")).strip()
        ortam = dict(oturum.kayit)
    ortam["temizlik"] = oturum.kayit.get("temizlik")

    model_kararlari = {
        "4": "tehlikeli",
        "5": "tehlikeli",
        "6": "guvenli",
    }
    triyaj = kaynak_evye_triyaji(adaylar, model_kararlari)
    triyaj_ref = kaynak_evye_triyaji_referans(adaylar_ref, model_kararlari)

    hibrit = hibrit_triyaj_kapisi(ornek_kod, model_kararlari)
    hibrit_ref = hibrit_triyaj_kapisi_referans(ornek_kod, model_kararlari)

    kontroller = {
        "ast_aday_uyumu": adaylar == adaylar_ref and len(adaylar) == 3,
        "triyaj_uyumu": triyaj == triyaj_ref,
        "hibrit_uyumu": hibrit == hibrit_ref and hibrit["onaylanan_evye_satirlari"] == [5],
        "cihaz_dogrulandi": ai_lab.cihaz_dogrulandi(ortam.get("bellek")),
        "kaynak_temizlendi": ai_lab.kaynak_temizlendi(ortam.get("temizlik")),
    }

    return {
        "ortam": ortam,
        "ayarlar": {"tehlikeli_evyeler": list(TEHLIKELI_EVYELER)},
        "canli_yanit": canli_yanit,
        "adaylar": adaylar,
        "triyaj": triyaj,
        "hibrit": hibrit,
        "kontroller": kontroller,
        "ozet": {
            "model": ortam["model"]["ad"],
            "aday_sayisi": len(adaylar),
            "onaylanan_satirlar": hibrit["onaylanan_evye_satirlari"],
            "elenen_sabit_satirlar": hibrit["elenen_sabit_satirlar"],
            "model_fp_orani": hibrit["model_yanlis_pozitif_orani"],
        },
    }


def goster(ast_evye_adaylari_cikar, kaynak_evye_triyaji, hibrit_triyaj_kapisi):
    r = deney(ast_evye_adaylari_cikar, kaynak_evye_triyaji, hibrit_triyaj_kapisi)
    o = r["ozet"]
    print(f"Model: {o['model']}")
    print(f"AST aday sayısı={o['aday_sayisi']}, Onaylanan dinamik evyeler={o['onaylanan_satirlar']}, Elenen sabitler={o['elenen_sabit_satirlar']}")
    print(f"Model yanlış pozitif oranı: {o['model_fp_orani']}")
    yol = ai_lab.kanit_yaz("ile-guvenlik-04-ast-calistir", {
        "kaynak": "gercek",
        "kabul": False,
        "ders": "ai-ile-guvenlik-04",
        "ortam": r["ortam"],
        "ayarlar": r["ayarlar"],
        "ozet": o,
    })
    print("Kanıt:", yol)
    return r
