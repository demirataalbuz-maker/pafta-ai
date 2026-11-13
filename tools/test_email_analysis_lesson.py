# -*- coding: utf-8 -*-
"""PU14 sentetik .eml analizi dersinin sözleşme ve davranış testleri.

    python tools/test_email_analysis_lesson.py

Dış DNS, URL açma, ek çalıştırma, ağ ve paket kurulumu kullanılmaz.
"""
import ast
from email import policy
from email.parser import BytesParser
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "sandbox"))

from engine.lessons import Library  # noqa: E402
from engine.runners import for_step, get  # noqa: E402
from sandbox import email_analysis_lab as lab  # noqa: E402

LESSON_PATH = ROOT / "tracks/purple/lessons/pu14-oltalama-email-analizi.md"
LESSON = Library().lesson("purple", "pu14")
TASKS = [s for s in LESSON["steps"] if s["kind"] == "gorev"]
MUTATIONS = [
    (0, 'if not kurumsal and re.search(r"[\\w.+-]+@" + re.escape(kurumsal_alan) + r"\\b", gorunen, re.I):',
     "if False:", "display-name spoofing atlanır"),
    (0, 'if not kurumsal and kurumsal_alan.split(".", 1)[0] in from_domain:',
     "if False:", "lookalike alan atlanır"),
    (0, 'auth["spf_aligned"] = ayni_kok(auth["spf_domain"], from_domain)',
     'auth["spf_aligned"] = True', "SPF alignment hep doğru sayılır"),
    (0, 'auth["dkim_aligned"] = ayni_kok(auth["dkim_domain"], from_domain)',
     'auth["dkim_aligned"] = True', "DKIM alignment hep doğru sayılır"),
    (0, '"stage_received_index": next((i for i, h in enumerate(received) if h["by"] == authserv), None)',
     '"stage_received_index": 0', "Authentication-Results aşaması varsayılır"),
    (0, 'if alan(reply_to) and alan(reply_to) != from_domain:',
     "if False:", "Reply-To alan farkı atlanır"),
    (0, 'if alan(return_path) and alan(return_path) != from_domain:',
     "if False:", "Return-Path alan farkı atlanır"),
    (1, '"alan": (parca.hostname or "").lower()', '"alan": gercek',
     "URL host yerine ham metin kullanılır"),
    (1, '"kullanici_bilgisi": parca.username', '"kullanici_bilgisi": None',
     "URL userinfo atlanır"),
    (1, '"uyusmuyor": gorunen != gercek', '"uyusmuyor": False',
     "gövde ve gerçek hedef farkı atlanır"),
    (1, '.replace(":", "[:]").replace(".", "[.]")', "",
     "defang atlanır"),
    (1, 'if parca.get_content_type() == "text/html":', "if False:",
     "HTML MIME parçaları atlanır"),
    (2, 'hashlib.sha256(icerik).hexdigest()', 'hashlib.sha256(ad.encode("utf-8")).hexdigest()',
     "içerik yerine dosya adı hashlenir"),
    (2, 'if icerik.startswith(b"MZ"):', "if False:", "MZ içerik kanıtı atlanır"),
    (2, 'if uzanti in beklenen_mime and mime not in beklenen_mime[uzanti]:',
     "if False:", "MIME/uzantı uyuşmazlığı atlanır"),
    (2, 'if len(uzantilar) >= 2 and uzantilar[-2] in belge and uzanti in tehlikeli:',
     "if False:", "çift uzantı atlanır"),
    (2, 'if uzanti in tehlikeli:', "if False:", "tehlikeli son uzantı atlanır"),
    (2, '"size": len(icerik)', '"size": len(ad)', "içerik boyutu atlanır"),
]


class FixtureSozlesmesi(unittest.TestCase):
    def test_hazirlama_benzersiz_dizin_ve_baytlari_kopyalar(self):
        with tempfile.TemporaryDirectory(prefix="pu14_test_") as tmp:
            hedef = lab.hazirla(tmp)
            self.assertEqual(hedef.name, "email_analysis")
            self.assertEqual({p.name for p in hedef.iterdir()}, set(lab.DOSYALAR))
            for ad in lab.DOSYALAR:
                self.assertEqual((hedef / ad).read_bytes(), (lab.FIXTURE / ad).read_bytes())
            self.assertEqual(lab.eml_yukle(hedef / "oltalama.eml")["Message-ID"],
                             "<PU14-OLTALAMA-001@pafta-billing.example>")

    def test_gercek_eml_mime_ve_sentetik_kanit_sinirlari(self):
        for ad in ("oltalama.eml", "kurumsal.eml"):
            with (lab.FIXTURE / ad).open("rb") as akim:
                mesaj = BytesParser(policy=policy.default).parse(akim)
            self.assertFalse(mesaj.defects, (ad, mesaj.defects))
            self.assertTrue(mesaj.is_multipart())
            self.assertEqual(mesaj.get_all("Authentication-Results") is not None, True)
            self.assertIn("edge.pafta.test", mesaj["Authentication-Results"])
            self.assertTrue(all(".example" in h or "pafta.test" in h for h in mesaj.get_all("Received")))
        oltalama = lab.eml_yukle(lab.FIXTURE / "oltalama.eml")
        self.assertEqual(len(oltalama.get_all("Received")), 2)
        self.assertEqual([a.get_filename() for a in oltalama.iter_attachments()],
                         ["Fatura_1042.pdf.exe", "odeme_notu.pdf"])
        self.assertIn(b"PU14 SENTETIK", next(oltalama.iter_attachments()).get_payload(decode=True))

    def test_yardimci_yalniz_yerel_parser_ve_kopyalama_ice_aktarir(self):
        tree = ast.parse((ROOT / "sandbox/email_analysis_lab.py").read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertEqual(imported, {"email", "pathlib", "shutil"})

    def test_cozumlerde_ag_url_acma_ve_ek_calistirma_yok(self):
        yasak_moduller = {"requests", "socket", "subprocess", "dns", "httpx", "ftplib"}
        yasak_cagrilar = {"urlopen", "system", "popen", "run", "Popen", "exec", "eval"}
        for step in TASKS:
            tree = ast.parse(step["solution"])
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    self.assertFalse({a.name.split(".")[0] for a in node.names} & yasak_moduller)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    self.assertNotIn(node.module.split(".")[0], yasak_moduller)
                    self.assertNotEqual(node.module, "urllib.request")
                elif isinstance(node, ast.Call):
                    ad = node.func.attr if isinstance(node.func, ast.Attribute) else (
                        node.func.id if isinstance(node.func, ast.Name) else "")
                    self.assertNotIn(ad, yasak_cagrilar)

    def test_utf8_lf_ve_track_kaydi(self):
        for path in [LESSON_PATH, Path(__file__), ROOT / "sandbox/email_analysis_lab.py",
                     *(lab.FIXTURE / ad for ad in lab.DOSYALAR)]:
            raw = path.read_bytes()
            self.assertNotIn(b"\r", raw, str(path))
            raw.decode("utf-8")
        track = (ROOT / "tracks/purple/track.json").read_text(encoding="utf-8")
        self.assertEqual(track.count('"pu14"'), 1)


class DersDavranisi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if len(TASKS) != 5:
            raise RuntimeError("PU14 için tam beş görev beklenir")

    def sonuc(self, gorev, kod):
        step = TASKS[gorev]
        return for_step(get("purple"), step).test(kod, step)

    def gecmeli(self, gorev, kod):
        sonuc = self.sonuc(gorev, kod)
        self.assertEqual(sonuc.get("status"), "pass", sonuc)

    def kalmali(self, gorev, kod):
        sonuc = self.sonuc(gorev, kod)
        self.assertEqual(sonuc.get("status"), "fail", sonuc)

    def test_tahmin_gercek_ciktiyla_calisir(self):
        step = next(s for s in LESSON["steps"] if s["kind"] == "tahmin")
        sonuc = for_step(get("purple"), step).run(step["code"], setup=step.get("setup"))
        self.assertEqual(sonuc["status"], "ok", sonuc)
        cikti = "".join(v for k, v in sonuc["segs"] if k == "out")
        self.assertEqual(cikti, "True\nFalse\n")

    def test_solution_gecer_starter_kalir(self):
        for index, step in enumerate(TASKS):
            with self.subTest(gorev=index + 1, tur="solution"):
                self.gecmeli(index, step["solution"])
            with self.subTest(gorev=index + 1, tur="starter"):
                self.kalmali(index, step["starter"])

    def test_yanlis_cozum_ve_alan_atlama_mutasyonlari_kalir(self):
        for index, old, new, name in MUTATIONS:
            with self.subTest(gorev=index + 1, mutasyon=name):
                cozum = TASKS[index]["solution"]
                self.assertIn(old, cozum)
                self.kalmali(index, cozum.replace(old, new, 1))

    def test_yalniz_dmarca_veya_hashe_bakan_cozumler_kalir(self):
        sadece_dmarc = '''from email_analysis_lab import eml_yukle
mesaj = eml_yukle("email_analysis/oltalama.eml")
def baslik_analizi(mesaj, kurumsal_alan="pafta.test"):
    return {"authentication": {"dmarc": "pass"}, "findings": []}
'''
        self.kalmali(0, sadece_dmarc)
        sadece_gorunen = '''from email_analysis_lab import eml_yukle
mesaj = eml_yukle("email_analysis/oltalama.eml")
def baglantilari_analizet(mesaj):
    return [{"gorunen": "https://pafta.test/odeme/1042", "uyusmuyor": False}]
'''
        self.kalmali(1, sadece_gorunen)
        sadece_hash = '''import hashlib
from email_analysis_lab import eml_yukle
mesaj = eml_yukle("email_analysis/oltalama.eml")
def ek_kanitlari(mesaj):
    return [{"sha256": hashlib.sha256(a.get_payload(decode=True)).hexdigest()} for a in mesaj.iter_attachments()]
'''
        self.kalmali(2, sadece_hash)


if __name__ == "__main__":
    unittest.main(verbosity=2)
