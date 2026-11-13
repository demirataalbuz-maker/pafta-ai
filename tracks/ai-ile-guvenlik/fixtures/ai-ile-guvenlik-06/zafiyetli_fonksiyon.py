def kullanici_getir(veritabani, kullanici_adi):
    if not kullanici_adi:
        return None
    sorgu = "SELECT id, rol FROM kullanicilar WHERE ad = '" + kullanici_adi + "'"
    return veritabani.sorgula(sorgu)
