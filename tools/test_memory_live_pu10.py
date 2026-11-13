# -*- coding: utf-8 -*-
"""PU10'un açık onaylı Volatility yolunu yerel bir imajla sına.

Varsayılan çalıştırmada test atlanır; araç ve imaj kendiliğinden aranmaz::

    PAFTA_MEMORY_LIVE=1 \
    PAFTA_VOLATILITY=/yerel/vol.exe \
    PAFTA_MEMORY_IMAGE=/yerel/image.vmem \
    python tools/test_memory_live_pu10.py

İmaj ve JSON çıktıları depoya yazılmaz. NetScan/Malfind'in boş sonuç vermesi
başarısızlık değildir; PsList gerçek süreç kanıtı içermelidir.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sandbox import memory_lab as ml  # noqa: E402


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


class GercekVolatility(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("PAFTA_MEMORY_LIVE") == "1",
                         "opt-in: PAFTA_MEMORY_LIVE=1 gerekli")
    def test_uc_eklenti_ve_json_sozlesmesi(self):
        ikili = os.environ.get("PAFTA_VOLATILITY", "")
        imaj = os.environ.get("PAFTA_MEMORY_IMAGE", "")
        self.assertTrue(os.path.isfile(ikili), "PAFTA_VOLATILITY dosyası yok")
        self.assertTrue(os.path.isfile(imaj), "PAFTA_MEMORY_IMAGE dosyası yok")
        with tempfile.TemporaryDirectory(prefix="pu10_live_") as tmp:
            sonuc = ml.volatility_topla(
                ikili, imaj, tmp, onay=True,
                timeout=int(os.environ.get("PAFTA_MEMORY_TIMEOUT", "180")))
            self.assertEqual(sonuc["durum"], "tamam", sonuc)
            self.assertTrue(sonuc["calisti"])
            self.assertEqual(len(sonuc["dosyalar"]), 3)
            ozet = {"arac": "volatility", "durum": sonuc["durum"], "eklentiler": {}}
            for yol in sonuc["dosyalar"]:
                ad = Path(yol).stem.removeprefix("volatility_")
                rows = ml.satirlari_oku(yol)
                self.assertIsInstance(rows, list)
                if ad == "pslist":
                    self.assertGreater(len(rows), 0, "gerçek imajda süreç bulunamadı")
                    self.assertIn("PID", rows[0])
                    self.assertIn("ImageFileName", rows[0])
                ozet["eklentiler"][ad] = {
                    "satir": len(rows), "sha256": sha256(yol)}
            rapor = os.environ.get("PAFTA_MEMORY_LIVE_REPORT", "")
            if rapor:
                with open(rapor, "w", encoding="utf-8") as f:
                    json.dump(ozet, f, ensure_ascii=False, indent=2)
                    f.write("\n")
            print(json.dumps(ozet, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    unittest.main(verbosity=2)
