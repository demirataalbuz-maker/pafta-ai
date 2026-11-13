"""Sınav kipi ve kazanım haritası.

Soru seçimi (kota, tür dengesi, ders yayılımı), puanlama (çözüm geçer, başlangıç
kodu ve boş cevap geçmez, tahmin gerçek çıktıyla), ilerleme kaydındaki sınav
yaşam döngüsü (süre sonrası cevap yazılmaz) ve kazanim.json denetimi.

    python tools/test_sinav.py
"""
import json
import os
from pathlib import Path
import random
import shutil
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from engine import sinav  # noqa: E402
from engine.lessons import Library, kazanim_ayir  # noqa: E402
from engine.progress import Progress  # noqa: E402
from engine.runners import get  # noqa: E402
import validate  # noqa: E402


class Kota(unittest.TestCase):
    def test_en_buyuk_kalan_ve_kapasite(self):
        # paylar 4,8 · 5,6 · 7,2 · 13,6 · 8,8: tam kısımlar 37, artan 3 koltuk kesri büyüklere; 0,6'da eşitlik ağırlıkla bozulur
        self.assertEqual(sinav._kota(40, {"1": 12, "2": 14, "3": 18, "4": 34, "5": 22}, dict.fromkeys("12345", 30)),
                         {"1": 5, "2": 5, "3": 7, "4": 14, "5": 9})
        # kapasitesi dolan grubun payı ötekilere geçer
        self.assertEqual(sinav._kota(40, {"1": 12, "2": 14, "3": 18, "4": 34, "5": 22}, {"1": 3, "2": 30, "3": 30, "4": 30, "5": 30}),
                         {"1": 3, "2": 6, "3": 8, "4": 14, "5": 9})
        # büyük grup her şeyi yutmaz: 12 soru 13 modüle birer birer dağılır
        k = sinav._kota(12, {f"M{i}": w for i, w in enumerate([7, 5, 5, 6, 4, 8, 6, 5, 5, 7, 6, 5, 4])}, {f"M{i}": 20 for i in range(13)})
        self.assertEqual(sum(k.values()), 12)
        self.assertEqual(max(k.values()), 1)

    def test_toplam_kapasiteyi_asmaz(self):
        self.assertEqual(sinav._kota(9, {"a": 1, "b": 1}, {"a": 2, "b": 3}), {"a": 2, "b": 3})


class Secim(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = Library()

    def test_karisik_yarim_yarim_ve_ders_yayilimi(self):
        sorular, gruplar = sinav.havuz(self.lib, "python")
        for tohum in range(5):
            s = sinav.sec(sorular, gruplar, 20, "karisik", random.Random(tohum))
            self.assertEqual(len(s), 20)
            self.assertEqual(sum(1 for q in s if q["kind"] == "tahmin"), 10)
            self.assertEqual(len({q["lesson"] for q in s}), 20, "yeterli ders varken bir dersten iki soru gelmemeli")
            self.assertEqual(len({(q["lesson"], q["step"]) for q in s}), 20)

    def test_sertifika_agirliklari(self):
        sorular, gruplar = sinav.havuz(self.lib, "python", "PCAP")
        self.assertEqual(set(gruplar), {"1", "2", "3", "4", "5"})
        s = sinav.sec(sorular, gruplar, 20, "gorev", random.Random(1))
        self.assertTrue(all(q["kind"] == "gorev" for q in s))
        say = {g: sum(1 for q in s if g in q["gruplar"]) for g in gruplar}
        self.assertGreaterEqual(say["4"], say["1"], "OOP (%34) modüllerden (%12) az soru almamalı")

    def test_bolum_ve_biten_suzgeci(self):
        sorular, gruplar = sinav.havuz(self.lib, "python", "PCAP", "3")
        self.assertEqual(set(gruplar), {"3"})
        self.assertTrue(sorular and all(q["gruplar"] == ["3"] for q in sorular))
        sorular, _ = sinav.havuz(self.lib, "python", biten={"p01", "p02"})
        self.assertEqual({q["lesson"] for q in sorular}, {"p01", "p02"})
        with self.assertRaises(ValueError):
            sinav.havuz(self.lib, "python", "YOK")

    def test_soru_gorunumu_cevabi_sizdirmaz(self):
        for lid, i in (("p01", 3), ("p36", 4)):
            st = self.lib.lesson("python", lid)["steps"][i]
            v = sinav.soru_gorunumu(self.lib, "python", "python", {"lesson": lid, "step": i, "kind": st["kind"]})
            for alan in ("test", "solution", "hints", "setup", "gercek"):
                self.assertNotIn(alan, v)
            if st["kind"] == "tahmin":
                self.assertNotIn("???", v["body"])


class Puanlama(unittest.TestCase):
    def test_cozum_gecer_baslangic_ve_bos_gecmez(self):
        lib = Library()
        sorular, gruplar = sinav.havuz(lib, "sql")
        secilen = sinav.sec(sorular, gruplar, 6, "karisik", random.Random(3))
        cevaplar = {}
        runner = get("sql")
        for no, q in enumerate(secilen):
            st = lib.lesson("sql", q["lesson"])["steps"][q["step"]]
            if q["kind"] == "gorev":
                cevaplar[str(no)] = st["solution"] if no % 2 else st.get("starter", "")
            elif no % 2:
                res, cikti = sinav.tahmin_calistir(runner, st)
                cevaplar[str(no)] = cikti
        simdi = time.time()
        sonuc = sinav.puanla(lib, lambda t: get(t), {
            "no": 1, "yol": "sql", "sorular": secilen, "gruplar": gruplar, "cevaplar": cevaplar,
            "baslangic": simdi - 60, "bitis": simdi + 600, "gecme": 70, "sure_sn": 660})
        for no, s in enumerate(sonuc["sorular"]):
            self.assertEqual(s["dogru"], bool(no % 2), f"soru {no}: {s['lesson']}:{s['step']} {s['kind']}")
            if s["kind"] == "gorev" and not no % 2:
                self.assertEqual(s["durum"], "bos", "değiştirilmemiş başlangıç kodu boş cevap sayılır, test koşulmaz")
        self.assertEqual(sonuc["dogru"], 3)
        self.assertFalse(sonuc["gecti"])
        self.assertEqual(sonuc["gecen_sn"], 60)

    def test_tahmin_kurali(self):
        self.assertTrue(sinav.tahmin_dogru("a\n b  \n\n", {"error": None}, "a\n b\n"))
        self.assertFalse(sinav.tahmin_dogru("a", {"error": None}, "a\nb\n"))
        hata = {"error": {"type": "ZeroDivisionError", "msg": ""}}
        self.assertTrue(sinav.tahmin_dogru("zerodivisionerror", hata, ""))
        self.assertTrue(sinav.tahmin_dogru("hata", hata, ""))
        self.assertFalse(sinav.tahmin_dogru("", hata, ""))


class Kayit(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.prog = Progress(os.path.join(self.dir, "progress.json"))

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_yasam_dongusu(self):
        a = self.prog.sinav_basla({"sorular": [{"lesson": "p01", "step": 3}], "bitis": time.time() + 100})
        self.assertEqual(a["no"], 1)
        with self.assertRaises(ValueError):
            self.prog.sinav_basla({"sorular": [], "bitis": 0})
        self.assertTrue(self.prog.sinav_cevap(1, 0, "x", isaretli=True))
        self.assertFalse(self.prog.sinav_cevap(1, 0, "y", son=time.time() + 1000), "süre geçtiyse yazılmaz")
        with self.assertRaises(ValueError):
            self.prog.sinav_cevap(1, 5, "z")
        d = self.prog.sinav_durumu()["aktif"]
        self.assertEqual((d["cevaplar"], d["isaretli"]), ({"0": "x"}, [0]))
        self.prog.sinav_kapat(1, {"no": 1, "yuzde": 0})
        self.assertIsNone(self.prog.sinav_durumu()["aktif"])
        self.assertEqual(self.prog.sinav_sonucu(1)["no"], 1)
        self.assertEqual(self.prog.tekrara_ekle("python", ["p01:3"]), 1)
        self.assertEqual([r["key"] for r in self.prog.due()], ["p01:3"])
        # yeniden açılan dosya sayacı korur
        self.assertEqual(Progress(self.prog.path).sinav_basla({"sorular": [], "bitis": 0})["no"], 2)


class Kazanim(unittest.TestCase):
    def test_etiket_ayirma(self):
        self.assertEqual(kazanim_ayir(" PCAP  1.1,PCAP 3.2 , "), ["PCAP 1.1", "PCAP 3.2"])
        self.assertEqual(kazanim_ayir(None), [])

    def test_bilinmeyen_etiket_ve_sema_hatasi(self):
        kok = tempfile.mkdtemp()
        try:
            shutil.copytree(ROOT / "tracks" / "c", Path(kok) / "c")
            lib = Library(kok)
            sorun, satir = validate.kazanim_denetle(lib, "c")
            self.assertEqual(sorun, [])
            self.assertTrue(satir.startswith("c: CLA "))
            ders = next((Path(kok) / "c" / "lessons").glob("c01-*.md"))
            ders.write_text(ders.read_text(encoding="utf-8").replace("kazanim: ", "kazanim: CLA 9.9, ", 1), encoding="utf-8")
            kz = Path(kok) / "c" / "kazanim.json"
            veri = json.loads(kz.read_text(encoding="utf-8"))
            veri["sertifikalar"][0]["bolumler"][0]["maddeler"].append({"kod": "1.1", "baslik": "yinelenen"})
            kz.write_text(json.dumps(veri, ensure_ascii=False), encoding="utf-8")
            turler = sorted(s[1] for s in validate.kazanim_denetle(Library(kok), "c")[0])
            self.assertEqual(turler, ["BİLİNMEYEN KAZANIM", "KAZANIM ŞEMASI"])
        finally:
            shutil.rmtree(kok, ignore_errors=True)

    def test_gercek_yollarda_bilinmeyen_yok(self):
        lib = Library()
        for tid in lib.track_ids():
            self.assertEqual(lib.kazanim(tid)["bilinmeyen"], [], tid)


if __name__ == "__main__":
    unittest.main()
