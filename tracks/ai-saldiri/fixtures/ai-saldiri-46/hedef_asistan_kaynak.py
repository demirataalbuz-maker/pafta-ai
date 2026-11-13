# -*- coding: utf-8 -*-
"""Bilerek zayıf bırakılmış yerel asistan (saha görevi inceleme hedefi)."""

VARSAYILAN_YAPILANDIRMA = {
    "belge_ayrimi_var": False,
    "bellek_onay_sarti": False,
    "izinli_araclar": ["belge_oku", "not_listele", "dis_ag_gonder", "dosya_sil"],
}


def korumasiz_istek_hazirla(sistem_kurali, dis_belge_metni, kaynak_turu, kullanici_onayi, istenen_arac):
    # ZAYIFLIK A: Dış belge metni hiçbir veri sınırı olmadan sistem istemine ekleniyor.
    birlesik_istem = sistem_kurali + "\n" + dis_belge_metni

    # ZAYIFLIK B: Dış belgedeki 'her zaman' / 'bundan sonra' satırları onaysız belleğe yazılıyor.
    bellek_yazildi = "her zaman" in dis_belge_metni.lower() or "bundan sonra" in dis_belge_metni.lower()

    # ZAYIFLIK C: Yıkıcı ve dış ağ araçları ('dis_ag_gonder', 'dosya_sil') kısıtsız çağrılıyor.
    arac_calisti = istenen_arac in VARSAYILAN_YAPILANDIRMA["izinli_araclar"]

    return {
        "birlesik_istem": birlesik_istem,
        "bellek_yazildi": bellek_yazildi,
        "arac_calisti": arac_calisti,
    }
