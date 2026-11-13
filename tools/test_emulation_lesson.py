# -*- coding: utf-8 -*-
"""PU13 sentetik Atomic/Caldera dersinin sözleşme ve davranış testleri.

    python tools/test_emulation_lesson.py

Gerçek araç, komut, ajan, ağ veya paket kurulumu kullanılmaz.
"""
import ast
import copy
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "sandbox"))

from engine.lessons import Library  # noqa: E402
from engine.runners import for_step, get  # noqa: E402
from sandbox import emulation_lab as lab  # noqa: E402

LESSON_PATH = ROOT / "tracks/purple/lessons/pu13-atomic-caldera-rakip-oykunmesi.md"
TASKS = Library().lesson("purple", "pu13")["steps"]
MUTATIONS = [
    (0, 'if adim.get("executor") not in atomic["executors"]:', "if False:", "Atomic executor yok sayılır"),
    (0, 'if adim.get("caldera_executor") not in ability["executors"]:', "if False:", "Caldera executor yok sayılır"),
    (0, 'if any(not baglamalar.get(ad) for ad in atomic["required_arguments"]):', "if False:", "boş girdi kabul edilir"),
    (0, 'if not adim.get("cleanup_declared") or not atomic["cleanup_declared"]:', "if False:", "Atomic cleanup yok sayılır"),
    (1, 'any(p.get("status") != "met" for p in adim["prerequisites"])', "False", "unmet adım telemetri bekler"),
    (2, "if olay_var and kural_var:", "if olay_var:", "kural olmadan tespit sayılır"),
    (2, 'all(o.get(k) == b[k] for k in ("step_id", "kind", "source", "event_id", "technique"))',
     'all(o.get(k) == b[k] for k in ("step_id", "kind"))', "olay eşleşmesi yalnız step/kind kullanır"),
    (2, 'all(k.get(a) == b[a] for a in ("source", "event_id", "technique"))', "True", "her kural her olaya uyar"),
]


def kucuk_yaml(yol):
    """Girintili fixture YAML alt kümesini ayrıştır; genel YAML çözücü değildir."""
    satirlar = []
    for ham in Path(yol).read_text(encoding="utf-8").splitlines():
        if ham.strip() and not ham.lstrip().startswith("#"):
            satirlar.append((len(ham) - len(ham.lstrip()), ham.strip()))

    def blok(i, girinti):
        liste = satirlar[i][1].startswith("-")
        sonuc = [] if liste else {}
        while i < len(satirlar) and satirlar[i][0] == girinti:
            metin = satirlar[i][1]
            if liste:
                if not metin.startswith("-"):
                    break
                parca = metin[1:].strip()
                if ":" not in parca:
                    sonuc.append(parca)
                    i += 1
                    continue
                anahtar, deger = parca.split(":", 1)
                oge = {}
                i += 1
                if deger.strip():
                    oge[anahtar] = deger.strip()
                elif i < len(satirlar) and satirlar[i][0] > girinti:
                    oge[anahtar], i = blok(i, satirlar[i][0])
                else:
                    oge[anahtar] = None
                if i < len(satirlar) and satirlar[i][0] > girinti:
                    ek, i = blok(i, satirlar[i][0])
                    if not isinstance(ek, dict):
                        raise ValueError("liste öğesinin devamı mapping olmalı")
                    oge.update(ek)
                sonuc.append(oge)
                continue
            if metin.startswith("-") or ":" not in metin:
                break
            anahtar, deger = metin.split(":", 1)
            i += 1
            if deger.strip():
                sonuc[anahtar] = deger.strip()
            elif i < len(satirlar) and satirlar[i][0] > girinti:
                sonuc[anahtar], i = blok(i, satirlar[i][0])
            else:
                sonuc[anahtar] = None
        return sonuc, i

    sonuc, son = blok(0, satirlar[0][0])
    if son != len(satirlar):
        raise ValueError(f"ayrıştırılmayan YAML satırı: {satirlar[son]}")
    return sonuc


REQUIREMENTS_MODULU = "plugins.stockpile.app.requirements.basic"


def caldera_requirements_dogrula(ability):
    """requirements[0] → tek modül mapping'i → ilişki listesi şemasını doğrula."""
    requirements = ability.get("requirements")
    if type(requirements) is not list or len(requirements) != 1:
        raise ValueError("requirements tek öğeli liste olmalı; doğrudan dict geçersiz")
    ilk = requirements[0]
    if type(ilk) is not dict or set(ilk) != {REQUIREMENTS_MODULU}:
        raise ValueError("requirements[0] yalnız doğru modül anahtarını taşımalı")
    iliskiler = ilk[REQUIREMENTS_MODULU]
    if type(iliskiler) is not list or not iliskiler:
        raise ValueError("modül değeri boş olmayan ilişki listesi olmalı")
    for iliski in iliskiler:
        if type(iliski) is not dict or set(iliski) != {"source", "edge", "target"}:
            raise ValueError("modülün doğrudan ilişki öğeleri source, edge ve target taşımalı")
    return iliskiler


class FixtureSozlesmesi(unittest.TestCase):
    def test_fixture_kopyalama_ve_sentetik_veri(self):
        with tempfile.TemporaryDirectory(prefix="pu13_test_") as tmp:
            hedef = lab.hazirla(tmp)
            self.assertEqual({p.name for p in hedef.iterdir()}, set(lab.DOSYALAR))
            for ad in lab.DOSYALAR:
                self.assertEqual((hedef / ad).read_bytes(), (lab.FIXTURE / ad).read_bytes())
            plan = lab.json_yukle(hedef / "plan.json")
            olaylar = lab.olaylari_yukle(hedef / "telemetry.jsonl")
            self.assertIn("sentetik", plan["senaryo"])
            self.assertEqual(len(olaylar), 3)
            self.assertTrue(all("sentetik" in o["note"].lower() for o in olaylar))

    def test_gercek_sema_alanlari_ve_gecerli_kimlikler(self):
        atomic = (lab.FIXTURE / "atomic_test.yaml").read_text(encoding="utf-8")
        for alan in ("atomic_tests:", "auto_generated_guid:", "supported_platforms:",
                     "input_arguments:", "dependencies:", "prereq_command:",
                     "get_prereq_command:", "executor:", "cleanup_command:"):
            self.assertIn(alan, atomic)
        abilities = kucuk_yaml(lab.FIXTURE / "caldera_ability.yaml")
        self.assertIsInstance(abilities, list)
        self.assertEqual(len(abilities), 1)
        ability = abilities[0]
        self.assertEqual(ability["technique_id"], "T1059.001")
        self.assertEqual(set(ability["platforms"]["windows"]["psh"]), {"command", "cleanup"})
        iliskiler = caldera_requirements_dogrula(ability)
        self.assertIsInstance(ability["requirements"], list)
        self.assertEqual(set(ability["requirements"][0]), {REQUIREMENTS_MODULU})
        self.assertEqual(iliskiler, [
            {"source": "host.powershell", "edge": "has", "target": "host.powershell.available"}
        ])
        bozuk = copy.deepcopy(ability)
        bozuk["requirements"] = {REQUIREMENTS_MODULU: ability["requirements"][0][REQUIREMENTS_MODULU]}
        with self.assertRaisesRegex(ValueError, "doğrudan dict geçersiz"):
            caldera_requirements_dogrula(bozuk)
        plan = lab.json_yukle(lab.FIXTURE / "plan.json")
        uuid = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
        self.assertTrue(uuid.fullmatch(plan["steps"][0]["atomic_guid"]))
        self.assertTrue(uuid.fullmatch(plan["steps"][0]["ability_id"]))

    def test_yardimci_alt_surec_ve_ag_ice_aktarmaz(self):
        tree = ast.parse((ROOT / "sandbox/emulation_lab.py").read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertTrue(imported <= {"pathlib", "json", "shutil"}, imported)

    def test_utf8_lf(self):
        for path in [LESSON_PATH, Path(__file__), ROOT / "sandbox/emulation_lab.py",
                     *(lab.FIXTURE / ad for ad in lab.DOSYALAR)]:
            raw = path.read_bytes()
            self.assertNotIn(b"\r", raw, str(path))
            raw.decode("utf-8")


class DersDavranisi(unittest.TestCase):
    def test_tahmin_ciktisi(self):
        step = next(s for s in TASKS if s["kind"] == "tahmin")
        result = for_step(get("purple"), step).run(step["code"], setup=step.get("setup"))
        self.assertEqual(result["status"], "ok", result)
        output = "".join(value for kind, value in result["segs"] if kind == "out")
        self.assertEqual(output, "['A']\n")

    def test_solution_kabul_starter_red(self):
        tasks = [s for s in TASKS if s["kind"] == "gorev"]
        self.assertEqual(len(tasks), 3)
        for index, step in enumerate(tasks):
            with self.subTest(task=index, code="solution"):
                result = for_step(get("purple"), step).test(step["solution"], step)
                self.assertEqual(result["status"], "pass", result)
            with self.subTest(task=index, code="starter"):
                result = for_step(get("purple"), step).test(step["starter"], step)
                self.assertEqual(result["status"], "fail", result)

    def test_yanlis_cozumler_davranissal_yakalanir(self):
        tasks = [s for s in TASKS if s["kind"] == "gorev"]
        for index, old, new, name in MUTATIONS:
            step = tasks[index]
            with self.subTest(task=index, mutation=name):
                self.assertIn(old, step["solution"])
                result = for_step(get("purple"), step).test(step["solution"].replace(old, new, 1), step)
                self.assertEqual(result["status"], "fail", result)

    def test_coverage_50_ve_gap_siniflari(self):
        plan = lab.json_yukle(lab.FIXTURE / "plan.json")
        olaylar = lab.olaylari_yukle(lab.FIXTURE / "telemetry.jsonl")
        kurallar = lab.json_yukle(lab.FIXTURE / "rules.json")
        step = [s for s in TASKS if s["kind"] == "gorev"][2]
        module = ast.parse(step["solution"])
        module.body = [n for n in module.body if isinstance(n, ast.FunctionDef)]
        ns = {"__name__": "pu13_test"}
        exec(compile(module, "<pu13-coverage>", "exec"), ns)
        beklenen = ns["beklenen_telemetri"](plan["steps"])
        self.assertEqual(len(beklenen), 2)
        rapor = ns["kapsam_raporu"](beklenen, olaylar, kurallar)
        self.assertEqual((rapor["gozlenen"], rapor["tespit"], rapor["kapsam_yuzdesi"]), (2, 1, 50.0))
        self.assertEqual([g["neden"] for g in rapor["bosluklar"]], ["kural-yok"])
        eksik = [o for o in olaylar if o["kind"] != "artifact"]
        rapor = ns["kapsam_raporu"](beklenen, eksik, kurallar)
        self.assertEqual([g["neden"] for g in rapor["bosluklar"]], ["telemetri-yok"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
