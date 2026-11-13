import os
import subprocess

def saglik_kontrolu(kullanici_komutu, sql_eki):
    sabit_versiyon = subprocess.run("python --version")
    dinamik_komut = os.system(kullanici_komutu)
    sabit_hesap = eval("2 + 2")
    dinamik_sorgu = cursor.execute("SELECT * FROM t WHERE x=" + sql_eki)
    return sabit_versiyon, dinamik_komut, sabit_hesap, dinamik_sorgu
