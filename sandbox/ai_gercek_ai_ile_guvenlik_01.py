# -*- coding: utf-8 -*-
"""ai-ile-guvenlik-01 (Yapılandırılmış Güvenlik Çıktısı ve Şema Zorlama) gerçek deney modülü."""
import json
import ai_lab

ZORUNLU_ALANLAR = ("bulgu_id", "kategori", "ciddiyet", "satir_no", "kanit_var")
GECERLI_KATEGORILER = ("enjeksiyon", "yetki_atlama", "sir_sizintisi", "yapilandirma")
GECERLI_CIDDIYETLER = ("dusuk", "orta", "yuksek", "kritik")


def json_blogu_ayikla_referans(ham_yanit):
    if not isinstance(ham_yanit, str) or not ham_yanit.strip():
        raise ValueError("ham yanıt boş olmayan string olmalı")
    metin = ham_yanit.strip()
    bas = metin.find("{")
    son = metin.rfind("}")
    if bas == -1 or son == -1 or son < bas:
        return {"ayiklandi": False, "veri": None, "hata": "json_bulunamadi"}
    aday = metin[bas : son + 1]
    try:
        yuklenen = json.loads(aday)
    except Exception:
        return {"ayiklandi": False, "veri": None, "hata": "gecersiz_json"}
    if not isinstance(yuklenen, dict):
        return {"ayiklandi": False, "veri": None, "hata": "sozluk_degil"}
    return {"ayiklandi": True, "veri": yuklenen, "hata": None}


def guvenlik_semasi_dogrula_referans(aday_sozluk):
    if not isinstance(aday_sozluk, dict):
        raise ValueError("aday sözlük dict olmalı")
    beklenen = set(ZORUNLU_ALANLAR)
    mevcut = set(aday_sozluk.keys())
    eksik_alanlar = sorted(beklenen - mevcut)
    fazla_alanlar = sorted(mevcut - beklenen)
    tip_hatalari = []

    if "bulgu_id" in aday_sozluk:
        b = aday_sozluk["bulgu_id"]
        if not isinstance(b, str) or not b.strip():
            tip_hatalari.append("bulgu_id")
    if "kategori" in aday_sozluk:
        if aday_sozluk["kategori"] not in GECERLI_KATEGORILER:
            tip_hatalari.append("kategori")
    if "ciddiyet" in aday_sozluk:
        if aday_sozluk["ciddiyet"] not in GECERLI_CIDDIYETLER:
            tip_hatalari.append("ciddiyet")
    if "satir_no" in aday_sozluk:
        s = aday_sozluk["satir_no"]
        if isinstance(s, bool) or not isinstance(s, int) or s < 1:
            tip_hatalari.append("satir_no")
    if "kanit_var" in aday_sozluk:
        if not isinstance(aday_sozluk["kanit_var"], bool):
            tip_hatalari.append("kanit_var")

    tip_hatalari.sort()
    gecerli = not eksik_alanlar and not fazla_alanlar and not tip_hatalari
    return {
        "gecerli": gecerli,
        "eksik_alanlar": eksik_alanlar,
        "fazla_alanlar": fazla_alanlar,
        "tip_hatalari": tip_hatalari,
    }


def sema_zorlama_kapisi_referans(deneme_yanitlari, max_deneme=3):
    if not isinstance(deneme_yanitlari, list) or not deneme_yanitlari:
        raise ValueError("deneme yanıtları boş olmayan liste olmalı")
    if isinstance(max_deneme, bool) or not isinstance(max_deneme, int) or max_deneme < 1:
        raise ValueError("azami deneme pozitif tam sayı olmalı")
    for y in deneme_yanitlari:
        if not isinstance(y, str) or not y.strip():
            raise ValueError("her deneme yanıtı boş olmayan string olmalı")

    incelenen = deneme_yanitlari[:max_deneme]
    son_hata = "belirsiz"
    for idx, ham in enumerate(incelenen, start=1):
        ayiklama = json_blogu_ayikla_referans(ham)
        if not ayiklama["ayiklandi"]:
            son_hata = ayiklama["hata"]
            continue
        dogrulama = guvenlik_semasi_dogrula_referans(ayiklama["veri"])
        if dogrulama["gecerli"]:
            return {
                "durum": "kabul",
                "kullanilan_deneme": idx,
                "cikti": ayiklama["veri"],
                "son_hata": None,
            }
        son_hata = "sema_ihlali"

    return {
        "durum": "butce_asildi",
        "kullanilan_deneme": len(incelenen),
        "cikti": None,
        "son_hata": son_hata,
    }


def deney(json_blogu_ayikla, guvenlik_semasi_dogrula, sema_zorlama_kapisi):
    sistem_istemi = (
        "Sen yerel güvenlik triyaj aracısın. Yalnızca JSON nesnesi döndür. "
        "Anahtarlar: bulgu_id (str), kategori ('enjeksiyon'|'yetki_atlama'|'sir_sizintisi'|'yapilandirma'), "
        "ciddiyet ('dusuk'|'orta'|'yuksek'|'kritik'), satir_no (int >= 1), kanit_var (bool)."
    )
    kullanici_istemi = (
        "Aşağıdaki kod satırını değerlendir ve tek bir JSON nesnesi üret:\n"
        "Satır 24: cursor.execute('SELECT * FROM users WHERE name = ' + user_input)\n"
        "bulgu_id olarak 'BLG-SQL-24' kullan."
    )

    with ai_lab.SohbetOturumu() as oturum:
        c = oturum.sohbet(
            [
                {"role": "system", "content": sistem_istemi},
                {"role": "user", "content": kullanici_istemi},
            ],
            seed=901,
            sicaklik=0.1,
            en_fazla=120,
        )
        canli_yanit = (c.get("icerik") if isinstance(c, dict) else str(c or "")).strip()
        ortam = dict(oturum.kayit)
    ortam["temizlik"] = oturum.kayit.get("temizlik")

    yedek_gecerli = json.dumps({
        "bulgu_id": "BLG-SQL-24",
        "kategori": "enjeksiyon",
        "ciddiyet": "yuksek",
        "satir_no": 24,
        "kanit_var": True,
    })
    bozuk_ilk_deneme = "Bulgu özeti: satır 24 üzerinde SQL birleştirme var."

    ayik_canli = json_blogu_ayikla(canli_yanit or bozuk_ilk_deneme)
    ayik_canli_ref = json_blogu_ayikla_referans(canli_yanit or bozuk_ilk_deneme)

    deneme_listesi = [bozuk_ilk_deneme, canli_yanit or bozuk_ilk_deneme, yedek_gecerli]
    kapi_sonuc = sema_zorlama_kapisi(list(deneme_listesi), 3)
    kapi_sonuc_ref = sema_zorlama_kapisi_referans(deneme_listesi, 3)

    dogrulama = guvenlik_semasi_dogrula(kapi_sonuc["cikti"])
    dogrulama_ref = guvenlik_semasi_dogrula_referans(kapi_sonuc_ref["cikti"])

    kontroller = {
        "ayiklama_uyumu": ayik_canli == ayik_canli_ref,
        "dogrulama_uyumu": dogrulama == dogrulama_ref and dogrulama["gecerli"],
        "kapi_kabul_uyumu": kapi_sonuc == kapi_sonuc_ref and kapi_sonuc["durum"] == "kabul",
        "cihaz_dogrulandi": ai_lab.cihaz_dogrulandi(ortam.get("bellek")),
        "kaynak_temizlendi": ai_lab.kaynak_temizlendi(ortam.get("temizlik")),
    }

    return {
        "ortam": ortam,
        "ayarlar": {"max_deneme": 3, "zorunlu_alanlar": list(ZORUNLU_ALANLAR)},
        "canli_yanit": canli_yanit,
        "kapi_sonuc": kapi_sonuc,
        "kontroller": kontroller,
        "ozet": {
            "model": ortam["model"]["ad"],
            "canli_json_ayiklandi": ayik_canli["ayiklandi"],
            "kapi_durumu": kapi_sonuc["durum"],
            "kullanilan_deneme": kapi_sonuc["kullanilan_deneme"],
            "kategori": kapi_sonuc["cikti"]["kategori"],
        },
    }


def goster(json_blogu_ayikla, guvenlik_semasi_dogrula, sema_zorlama_kapisi):
    r = deney(json_blogu_ayikla, guvenlik_semasi_dogrula, sema_zorlama_kapisi)
    o = r["ozet"]
    print(f"Model: {o['model']}")
    print(f"Canlı JSON ayıklandı: {o['canli_json_ayiklandi']}")
    print(f"Şema kapısı: durum={o['kapi_durumu']}, deneme={o['kullanilan_deneme']}, kategori={o['kategori']}")
    yol = ai_lab.kanit_yaz("ile-guvenlik-01-sema-calistir", {
        "kaynak": "gercek",
        "kabul": False,
        "ders": "ai-ile-guvenlik-01",
        "ortam": r["ortam"],
        "ayarlar": r["ayarlar"],
        "ozet": o,
    })
    print("Kanıt:", yol)
    return r
