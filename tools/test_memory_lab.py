# -*- coding: utf-8 -*-
"""PU04 bellek laboratuvarı; yalnız standart kitaplık ve sentetik fixture.

    python tools/test_memory_lab.py

Gerçek Volatility/MemProcFS bu testlerde kendiliğinden çalıştırılmaz. Eksik
araç/imaj yolları açık durum sonuçlarıyla, başarılı ve hatalı çağrılar sahte
alt süreç/API nesneleriyle sınanır.
"""
import contextlib
import csv
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "sandbox"))

from engine.lessons import Library  # noqa: E402
from engine.runners import get  # noqa: E402
from sandbox import memory_lab as ml  # noqa: E402


@contextlib.contextmanager
def calisma():
    eski = os.getcwd()
    with tempfile.TemporaryDirectory(prefix="pu04_test_") as tmp:
        os.chdir(tmp)
        try:
            ml.hazirla("bellek")
            yield tmp
        finally:
            os.chdir(eski)


def cozum(index):
    les = Library().lesson("purple", "pu10")
    st = [s for s in les["steps"] if s["kind"] == "gorev"][index]
    ns = {"__name__": "__main__"}
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compile(st["solution"], "<pu04-solution>", "exec"), ns)
    return ns


class Yardimcilar(unittest.TestCase):
    def test_donusumler(self):
        self.assertEqual(ml.sayi("0x500000"), 0x500000)
        self.assertEqual(ml.sayi(" 4242 "), 4242)
        self.assertIsNone(ml.sayi("N/A"))
        self.assertFalse(ml.evet(False))
        self.assertFalse(ml.evet("False"))
        self.assertTrue(ml.evet("True"))
        self.assertEqual(ml.zaman("2026-10-19T09:04:00Z"), "2026-10-19 09:04:00")
        self.assertEqual(ml.zaman("2026-10-19 09:04:00 UTC"), "2026-10-19 09:04:00")
        self.assertEqual(ml.metin("***"), "")

    def test_fixture_kucuk_ve_zararsiz(self):
        adlar = sorted(os.listdir(ml.FIXTURE))
        self.assertEqual(len(adlar), 7)
        self.assertIn("README.md", adlar)
        for ad in adlar:
            yol = os.path.join(ml.FIXTURE, ad)
            self.assertLess(os.path.getsize(yol), 8192, ad)
            self.assertTrue(ad.endswith((".csv", ".json", ".md")), ad)

    def test_json_renderer_satirlari(self):
        with calisma() as tmp:
            yol = os.path.join(tmp, "renderer.json")
            with open(yol, "w", encoding="utf-8") as f:
                json.dump({"rows": [{"PID": 4, "__children": [{"PID": 8}]}, {"__children": []}]}, f)
            self.assertEqual(ml.satirlari_oku(yol), [{"PID": 4}, {"PID": 8}])


class DersSozlesmesi(unittest.TestCase):
    def test_solution_kabul_starter_red(self):
        les = Library().lesson("purple", "pu10")
        adimlar = [s for s in les["steps"] if s["kind"] == "gorev"]
        self.assertEqual(len(adimlar), 3)
        runner = get("purple")
        for i, st in enumerate(adimlar, 1):
            with self.subTest(gorev=i, kod="solution"):
                r = runner.test(st["solution"], st)
                self.assertEqual(r["status"], "pass", (r.get("checks"), r.get("error")))
            with self.subTest(gorev=i, kod="starter"):
                r = runner.test(st["starter"], st)
                self.assertNotEqual(r["status"], "pass")
                self.assertNotEqual(r["status"], "internal", r.get("detail"))

    def test_belirsiz_pid_rastgele_secilmez(self):
        with calisma():
            ns = cozum(1)
            ps = ns["surecler"]()
            ps.append(dict(ps[-1], ad="baska.exe"))
            cs = ns["baglantilar"](ps)
            c = next(c for c in cs if c["pid"] == 4242 and c["zaman"] == "2026-10-19 09:04:00")
            self.assertIsNone(c["surec"])
            self.assertEqual(c["eslesme"], "yok")

    def test_gelecekteki_ag_ve_kapali_durum_kanit_olmaz(self):
        with calisma():
            ns = cozum(2)
            ps = ns["surecler"]()
            cs = ns["baglantilar"](ps)
            # Bağlantı bölgeden sonra oluştuysa geriye dönük gerekçe yazılmaz.
            for c in cs:
                if c["pid"] == 4242 and c["surec"] == "rundll32.exe":
                    c["zaman"] = "2026-10-19 09:06:00"
            bs = ns["bulgular"](ps, cs)
            ana = next(b for b in bs if b["pid"] == 4242)
            self.assertEqual(ana["nedenler"], ["rwx-ozel-dosyasiz"])

    def test_ozel_olmayan_kaybolur_sahipsiz_kaybolmaz(self):
        with calisma():
            for ad in ("volatility_malfind.csv", "memprocfs_vads.json"):
                yol = os.path.join("bellek", ad)
                if ad.endswith(".csv"):
                    with open(yol, encoding="utf-8", newline="") as f:
                        rows = list(csv.DictReader(f)); fields = rows[0].keys()
                    for r in rows:
                        if r["PID"] == "900":
                            r["PrivateMemory"] = "False"
                    with open(yol, "w", encoding="utf-8", newline="") as f:
                        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
                else:
                    with open(yol, encoding="utf-8") as f:
                        rows = json.load(f)
                    for r in rows:
                        if r["pid"] == 900:
                            r["private"] = False
                    with open(yol, "w", encoding="utf-8") as f:
                        json.dump(rows, f)
            ns = cozum(2); ps = ns["surecler"](); bs = ns["bulgular"](ps, ns["baglantilar"](ps))
            self.assertNotIn(900, [b["pid"] for b in bs])
            self.assertIn(9999, [b["pid"] for b in bs])
            self.assertIsNone(next(b for b in bs if b["pid"] == 9999)["surec"])


class GercekAracSozlesmesi(unittest.TestCase):
    def test_onaysiz_gereksinim_yok_ve_hicbir_sey_calismaz(self):
        with tempfile.TemporaryDirectory() as tmp:
            hedef = os.path.join(tmp, "out")
            with mock.patch.object(ml.subprocess, "run") as run:
                for arac in ("volatility", "memprocfs"):
                    if arac == "volatility":
                        r = ml.volatility_topla("yok", "yok", hedef)
                    else:
                        r = ml.memprocfs_topla("yok", hedef)
                    self.assertEqual(r["durum"], "gereksinim-yok")
                    self.assertFalse(r["calisti"])
                run.assert_not_called()
            self.assertFalse(os.path.exists(hedef))

    def test_onayli_ama_arac_veya_imaj_yoksa_atlandi(self):
        with tempfile.TemporaryDirectory() as tmp:
            hedef = os.path.join(tmp, "out")
            r = ml.volatility_topla("yok", "yok", hedef, onay=True)
            self.assertEqual((r["durum"], r["calisti"]), ("atlandi", False))
            r = ml.memprocfs_topla("yok", hedef, onay=True)
            self.assertEqual((r["durum"], r["calisti"]), ("atlandi", False))
            self.assertFalse(os.path.exists(hedef))

    def test_volatility_basari_hata_ve_bozuk_json_ayrik(self):
        with tempfile.TemporaryDirectory() as tmp:
            vol = os.path.join(tmp, "vol.py"); imaj = os.path.join(tmp, "image.raw")
            open(vol, "w").close(); open(imaj, "wb").close()
            out = os.path.join(tmp, "out")
            ok = mock.Mock(returncode=0, stdout=b'{"rows": []}', stderr=b"")
            with mock.patch.object(ml.subprocess, "run", return_value=ok) as run:
                r = ml.volatility_topla(vol, imaj, out, onay=True)
            self.assertEqual(r["durum"], "tamam")
            self.assertTrue(r["calisti"])
            self.assertEqual(len(r["dosyalar"]), 3)
            self.assertEqual(run.call_count, 3)
            for call in run.call_args_list:
                cmd = call.args[0]
                self.assertIsInstance(cmd, list)
                self.assertIn("windows.", " ".join(cmd))
                self.assertIn("-r", cmd)
            bad = mock.Mock(returncode=2, stdout=b"", stderr=b"plugin failed")
            with mock.patch.object(ml.subprocess, "run", return_value=bad):
                r = ml.volatility_topla(vol, imaj, out, onay=True)
            self.assertEqual(r["durum"], "hata")
            self.assertIn("plugin failed", r["neden"])
            invalid = mock.Mock(returncode=0, stdout=b"not-json", stderr=b"")
            with mock.patch.object(ml.subprocess, "run", return_value=invalid):
                r = ml.volatility_topla(vol, imaj, out, onay=True)
            self.assertEqual(r["durum"], "hata")
            self.assertIn("geçerli JSON yok", r["neden"])

    def test_memprocfs_yalniz_metaveri_yazar(self):
        class Maps:
            def net(self):
                return [{"pid": 42, "dst-ip": "198.51.100.1", "dst-port": 443}]

        class ProcMaps:
            def vad(self):
                return [{"start": 4096, "protection": "rwx", "private": True}]

        class Proc:
            pid, ppid, name, state, pathuser = 42, 4, "ornek.exe", 0, ""
            maps = ProcMaps()

        class Vmm:
            def __init__(self, args):
                self.args = args
                self.maps = Maps()

            def process_list(self):
                return [Proc()]

        class Modul:
            pass

        Modul.Vmm = Vmm
        with tempfile.TemporaryDirectory() as tmp:
            imaj = os.path.join(tmp, "image.raw"); open(imaj, "wb").close()
            out = os.path.join(tmp, "out")
            r = ml.memprocfs_topla(imaj, out, onay=True, modul=Modul)
            self.assertEqual(r["durum"], "tamam", r)
            self.assertEqual(len(r["dosyalar"]), 3)
            with open(os.path.join(out, "memprocfs_processes.json"), encoding="utf-8") as f:
                ps = json.load(f)
            with open(os.path.join(out, "memprocfs_vads.json"), encoding="utf-8") as f:
                vad = json.load(f)
            self.assertEqual(ps[0]["pid"], 42)
            self.assertEqual(vad, [{"start": 4096, "protection": "rwx", "private": True, "pid": 42}])

    def test_memprocfs_api_hatasi_tamam_degildir(self):
        class Modul:
            class Vmm:
                def __init__(self, args):
                    raise RuntimeError("imaj açılamadı")

        with tempfile.TemporaryDirectory() as tmp:
            imaj = os.path.join(tmp, "image.raw"); open(imaj, "wb").close()
            r = ml.memprocfs_topla(imaj, os.path.join(tmp, "out"), onay=True, modul=Modul)
            self.assertEqual(r["durum"], "hata")
            self.assertIn("imaj açılamadı", r["neden"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
