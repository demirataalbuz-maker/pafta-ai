# -*- coding: utf-8 -*-
"""Madde 103 çevrimdışı canlandırma ve kanıt üreticisinin özel testleri.

    python tools/test_capstone_lab.py
"""
import copy
import csv
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine import runners  # noqa: E402
from engine.lessons import Library  # noqa: E402
from sandbox import saldiri_zinciri_lab as lab  # noqa: E402

VERI = ROOT / "tracks" / "bitirme" / "veri"
SENARYO = VERI / "scenario.json"
NEGATIF = VERI / "negative_controls.json"


class BT01DersRegresyonTest(unittest.TestCase):
    """Dersin gerçek runner'ında çözüm, starter ve saldırgan mutasyonları sınar."""

    @classmethod
    def setUpClass(cls):
        cls.adimlar = [s for s in Library().lesson("bitirme", "bt07")["steps"] if s["kind"] == "gorev"]
        if len(cls.adimlar) != 3:
            raise RuntimeError("BT01 için tam üç görev beklenir")

    def sonuc(self, gorev, kod):
        adim = self.adimlar[gorev]
        return runners.for_step(runners.get("python"), adim).test(kod, adim)

    def gecmeli(self, gorev, kod):
        sonuc = self.sonuc(gorev, kod)
        self.assertEqual(sonuc.get("status"), "pass", (sonuc.get("checks"), sonuc.get("error")))

    def kalmali(self, gorev, kod):
        sonuc = self.sonuc(gorev, kod)
        self.assertEqual(sonuc.get("status"), "fail", (sonuc.get("checks"), sonuc.get("error")))

    def test_cozumler_gecer_ve_starterlar_kalir(self):
        for i, adim in enumerate(self.adimlar):
            with self.subTest(gorev=i + 1, tur="solution"):
                self.gecmeli(i, adim["solution"])
            with self.subTest(gorev=i + 1, tur="starter"):
                self.kalmali(i, adim["starter"])

    def test_gorev1_technique_ile_filtreleme_ve_ek_mutasyon_kalir(self):
        cozum = self.adimlar[0]["solution"]
        bildirilen = cozum.replace('if not k["is_negative"]:', 'if k["attack_technique"]:')
        self.kalmali(0, bildirilen)
        bos_pozitifi_dusuren = cozum.replace(
            'if not k["is_negative"]:', 'if not k["is_negative"] and k["attack_technique"]:')
        self.kalmali(0, bos_pozitifi_dusuren)
        sadece_negatif_adi = cozum.replace(
            'if not k["is_negative"]:', 'if not k["event_id"].startswith("N"):')
        self.kalmali(0, sadece_negatif_adi)

    def test_gorev2_hash_hesaplamayan_ve_yok_sayan_kodlar_kalir(self):
        bildirilen = '''import hashlib  # sha256 kaynakta görünse bile davranış yeterli değil
import json
import sys
kayitlar = json.loads(sys.stdin.read())
print(str(len(kayitlar)) + "/2 SAĞLAM")
'''
        self.kalmali(1, bildirilen)
        hesaplayip_yok_sayan = '''import hashlib
import json
import sys
kayitlar = json.loads(sys.stdin.read())
for k in kayitlar:
    hashlib.sha256(k["content"].encode("utf-8")).hexdigest()
print(str(len(kayitlar)) + "/2 SAĞLAM")
'''
        self.kalmali(1, hesaplayip_yok_sayan)
        sadece_alan_varligi = '''import hashlib
import json
import sys
kayitlar = json.loads(sys.stdin.read())
saglam = all(k["sha256"] for k in kayitlar)
print("2/2 SAĞLAM" if saglam else "BUTUNLUK BOZUK")
'''
        self.kalmali(1, sadece_alan_varligi)

    def test_gorev3_expected_kendisiyle_karsilastirma_ve_ek_mutasyon_kalir(self):
        cozum = self.adimlar[2]["solution"]
        bildirilen = cozum.replace('a["observed_evidence"]', 'a["expected_evidence"]')
        self.kalmali(2, bildirilen)
        sadece_bosluk = '''import json
import sys
adimlar = json.loads(sys.stdin.read())
for a in adimlar:
    if not a["observed_evidence"]:
        print("REDDEDILDI:" + a["step_id"])
        break
else:
    print("ZINCIR TAM")
'''
        self.kalmali(2, sadece_bosluk)
        ters_kume = cozum.replace(
            'set(a["expected_evidence"]).issubset(a["observed_evidence"])',
            'set(a["observed_evidence"]).issubset(a["expected_evidence"])')
        self.kalmali(2, ters_kume)


class CapstoneLabTest(unittest.TestCase):
    def setUp(self):
        self.senaryo = lab.senaryo_dogrula(lab._json_oku(SENARYO))
        self.negatif = lab.negatif_dogrula(lab._json_oku(NEGATIF))
        self.tmp = tempfile.TemporaryDirectory(prefix="capstone-test-", dir=VERI)
        self.cikti = Path(self.tmp.name) / "paket"

    def tearDown(self):
        self.tmp.cleanup()

    def uret(self):
        return lab.yaz(SENARYO, self.cikti, NEGATIF)

    def manifesti_yenile(self):
        yol = self.cikti / "manifest.sha256.json"
        manifest = json.loads(yol.read_text(encoding="utf-8"))
        for kayit in manifest["files"]:
            icerik = (self.cikti / kayit["path"]).read_bytes()
            kayit["bytes"] = len(icerik)
            kayit["sha256"] = hashlib.sha256(icerik).hexdigest()
        yol.write_bytes(lab._json_bayt(manifest))

    def test_iki_uretim_normalize_ve_manifest_baytlari_ayni(self):
        ilk = lab.uret(self.senaryo, self.negatif)
        ikinci = lab.uret(copy.deepcopy(self.senaryo), copy.deepcopy(self.negatif))
        self.assertEqual(ilk["normalized.jsonl"], ikinci["normalized.jsonl"])
        self.assertEqual(ilk, ikinci)
        self.assertEqual(lab._manifest(self.senaryo["run_id"], ilk),
                         lab._manifest(self.senaryo["run_id"], ikinci))

    def test_ure_ve_dogrula(self):
        ozet = self.uret()
        self.assertEqual(ozet, {"run_id": "bt01-20261026t100000z", "files": 10, "events": 12})
        self.assertEqual(lab.dogrula(SENARYO, self.cikti, NEGATIF), {
            "ok": True, "run_id": "bt01-20261026t100000z", "events": 12,
            "detections": 4, "negative_controls": 4,
        })

    def test_web_ve_ad_kayitlari_sentetik_ve_kurgusal(self):
        self.uret()
        web = [json.loads(x) for x in (self.cikti / "web.ndjson").read_text(encoding="utf-8").splitlines()]
        ad = [json.loads(x) for x in (self.cikti / "ad_events.ndjson").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(web), 4)
        self.assertEqual(len(ad), 4)
        self.assertTrue(all(x["simulation"] for x in web + ad))
        self.assertTrue(all(x["host"] in ("web.pafta.test", "DC-01") for x in web + ad))
        self.assertNotIn("password", (self.cikti / "web.ndjson").read_text(encoding="utf-8").lower())

    def test_kql_csv_ve_spl_jsonl_tuketilebilir(self):
        self.uret()
        with (self.cikti / "kql_events.csv").open(encoding="utf-8", newline="") as f:
            kql = list(csv.DictReader(f))
        spl = [json.loads(x) for x in (self.cikti / "spl_events.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(kql), 12)
        self.assertEqual(len(spl), 12)
        self.assertEqual(kql[0]["TimeGenerated"], "2026-10-26T09:55:00Z")
        self.assertEqual(spl[-1]["_time"], "2026-10-26T10:04:00Z")
        self.assertTrue(all(x["sourcetype"].startswith("pafta:synthetic:") for x in spl))

    def test_attack_zaman_cizelgesi_ve_tespitler(self):
        self.uret()
        zaman = json.loads((self.cikti / "timeline.json").read_text(encoding="utf-8"))
        tespit = json.loads((self.cikti / "detections.json").read_text(encoding="utf-8"))
        self.assertEqual([x["attack_technique"] for x in zaman["steps"]],
                         ["T1078", "T1087.002", "T1213.002", "T1041"])
        self.assertEqual([x["expected_detection"]["id"] for x in zaman["steps"]],
                         [x["id"] for x in tespit])
        self.assertTrue(all(x["simulation"] for x in tespit))

    def test_negatif_kontroller_alarm_uretmez(self):
        self.uret()
        normalized = [json.loads(x) for x in (self.cikti / "normalized.jsonl").read_text(encoding="utf-8").splitlines()]
        negatif = [x for x in normalized if x["is_negative"]]
        self.assertEqual(len(negatif), 4)
        self.assertTrue(all(not x["attack_technique"] and not x["detection_id"] for x in negatif))
        tespit = json.loads((self.cikti / "detections.json").read_text(encoding="utf-8"))
        self.assertFalse({x["event_id"] for x in negatif} & {e for x in tespit for e in x["evidence"]})

    def test_eksik_kanit_reddedilir(self):
        self.uret()
        (self.cikti / "normalized.jsonl").unlink()
        with self.assertRaisesRegex(lab.KanitHatasi, "eksik"):
            lab.dogrula(SENARYO, self.cikti, NEGATIF)

    def test_bozuk_kanit_reddedilir(self):
        self.uret()
        (self.cikti / "normalized.jsonl").write_text('{"bozuk":', encoding="utf-8")
        with self.assertRaisesRegex(lab.KanitHatasi, "SHA-256"):
            lab.dogrula(SENARYO, self.cikti, NEGATIF)

    def test_manifest_yenilense_bile_anlamsal_bozulma_reddedilir(self):
        self.uret()
        yol = self.cikti / "normalized.jsonl"
        yol.write_bytes(yol.read_bytes().replace(b'"step_id":"bt01-oturum"', b'"step_id":"bt01-sahte"'))
        self.manifesti_yenile()
        with self.assertRaisesRegex(lab.KanitHatasi, "beklenenle uyuşmuyor"):
            lab.dogrula(SENARYO, self.cikti, NEGATIF)

    def test_manifest_eksikligi_ve_sahteciligi_reddedilir(self):
        self.uret()
        yol = self.cikti / "manifest.sha256.json"
        manifest = json.loads(yol.read_text(encoding="utf-8"))
        manifest["files"] = manifest["files"][:-1]
        yol.write_bytes(lab._json_bayt(manifest))
        with self.assertRaisesRegex(lab.KanitHatasi, "dosya listesi"):
            lab.dogrula(SENARYO, self.cikti, NEGATIF)

    def test_gecersiz_zaman_ve_gizli_alan_reddedilir(self):
        bozuk = copy.deepcopy(self.senaryo)
        bozuk["steps"][0]["timestamp"] = "2026-10-26T13:00:00+03:00"
        with self.assertRaisesRegex(lab.KanitHatasi, "sabit UTC"):
            lab.senaryo_dogrula(bozuk)
        bozuk = copy.deepcopy(self.senaryo)
        bozuk["steps"][0]["web"]["token"] = "asla-kabul-edilmez"
        with self.assertRaisesRegex(lab.KanitHatasi, "gizli alan"):
            lab.senaryo_dogrula(bozuk)

    def test_cli_dogrulama_hatasi_iki_donderir(self):
        self.uret()
        (self.cikti / "ad_events.xml").unlink()
        rc = lab.main(["dogrula", "--senaryo", str(SENARYO), "--negatifler", str(NEGATIF),
                       "--cikti", str(self.cikti)])
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
