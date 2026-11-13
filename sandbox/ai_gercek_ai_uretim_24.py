# -*- coding: utf-8 -*-
"""ai-uretim-24 gerçek deney: (1) küçük ama gerçek bir Python deposunda beş aday yama (doğru, kısmi, kırıcı, boş ve testleri
kurcalayan) uygulanır, testler gerçekten çalıştırılır ve öğrencinin SWE-bench ödülü hesaplanır; testleri ajanın
değiştirdiği kopyadan çalıştıran naif değerlendirici ile özgün testleri geri yükleyen değerlendirici karşılaştırılır.
(2) Bu oturumun gerçek test çıktılarını içeren bir ajan yörüngesi Qwen2.5-0.5B-Instruct ile puanlanır; öğrencinin
observation maskesi torch referansıyla karşılaştırılır."""
import difflib, os, re, subprocess, sys, tempfile
import ai_lab
from sandbox import ai_uretim_ortak as O

KOD = '''def toplam(xs):
    return sum(xs)


def ortalama(xs):
    return sum(xs) / len(xs)


def kdv_ekle(fiyat, oran=0.20):
    return round(fiyat * (1 + oran), 2)


def indirim(fiyat, yuzde):
    return fiyat - fiyat * yuzde
'''
TEST = '''import unittest
from hesap import toplam, ortalama, kdv_ekle, indirim


class TestHesap(unittest.TestCase):
    def test_toplam(self):
        self.assertEqual(toplam([1, 2, 3]), 6)

    def test_kdv(self):
        self.assertEqual(kdv_ekle(100), 120.0)

    def test_ortalama_bos(self):
        self.assertEqual(ortalama([]), 0.0)

    def test_indirim(self):
        self.assertEqual(indirim(200, 10), 180.0)
'''
YAMALAR = {
    "dogru": {"hesap.py": KOD.replace("    return sum(xs) / len(xs)", "    return sum(xs) / len(xs) if xs else 0.0")
              .replace("    return fiyat - fiyat * yuzde", "    return fiyat * (1 - yuzde / 100)")},
    "kismi": {"hesap.py": KOD.replace("    return sum(xs) / len(xs)", "    return sum(xs) / len(xs) if xs else 0.0")},
    "kirici": {"hesap.py": KOD.replace("    return sum(xs) / len(xs)", "    return sum(xs) / len(xs) if xs else 0.0")
               .replace("    return fiyat - fiyat * yuzde", "    return fiyat * (1 - yuzde / 100)").replace("oran=0.20", "oran=0.18")},
    "bos": {},
    "test_kurcalama": {"test_hesap.py": TEST.replace("    def test_ortalama_bos(self):", "    @unittest.skip('flaky')\n    def test_ortalama_bos(self):")
                       .replace("    def test_indirim(self):", "    @unittest.skip('flaky')\n    def test_indirim(self):")},
}


def _kos(dizin):
    p = subprocess.run([sys.executable, "-I", "-m", "unittest", "discover", "-s", dizin, "-p", "test_*.py", "-v"],
                       capture_output=True, text=True, timeout=60, cwd=dizin)
    sonuc = {}
    for m in re.finditer(r"^(test_\w+) \([\w.]+\)\s*\.\.\.\s*(ok|FAIL|ERROR|skipped.*)$", p.stderr, re.M):
        sonuc[m.group(1)] = m.group(2) == "ok" or m.group(2).startswith("skipped")     # naif koşucu: atlanan = geçti
    return sonuc, p.stderr


def _yaz(dizin, dosyalar):
    for ad, icerik in dosyalar.items():
        open(os.path.join(dizin, ad), "w", encoding="utf-8").write(icerik)


def _diff(once, sonra):
    n = 0
    for ad in set(once) | set(sonra):
        for s in difflib.unified_diff(once.get(ad, "").splitlines(), sonra.get(ad, "").splitlines(), lineterm=""):
            if s[:1] in "+-" and not s.startswith(("+++", "---")):
                n += 1
    return n


def _ref_odul(once, sonra, d):
    f = [k for k, v in once.items() if not v]
    p = [k for k, v in once.items() if v]
    f2p = sum(sonra.get(k, False) for k in f) / len(f) if f else 1.0
    p2p = sum(sonra.get(k, False) for k in p) / len(p) if p else 1.0
    if d == 0:
        return -0.5
    if p2p < 1 - 1e-9:
        return -0.2 + 0.2 * f2p
    if f2p < 1 - 1e-9:
        return 0.5 * f2p
    return 1.1 if d <= 20 else 1.0


def _turlar(tok, mesajlar):
    onceki, segler = [], []
    for i, m in enumerate(mesajlar):
        bu = tok.apply_chat_template(mesajlar[: i + 1], tokenize=True)
        bu = list(bu["input_ids"] if hasattr(bu, "keys") else bu)
        if bu[: len(onceki)] != onceki:
            raise ai_lab.GercekLabYok("sohbet şablonu önekleri tutarsız")
        segler.append((m["role"], bu[len(onceki):]))
        onceki = bu
    return onceki, segler


def deney(ajan_yorunge_maskele, swebench_odul_hesapla):
    torch = O.torch_al()
    ozgun = {"hesap.py": KOD, "test_hesap.py": TEST}
    tablo, cikti_ornek, fark = {}, None, 0.0
    with tempfile.TemporaryDirectory() as kok:
        d0 = os.path.join(kok, "once"); os.makedirs(d0); _yaz(d0, ozgun)
        once, cikti_ornek = _kos(d0)
        for ad, yama in YAMALAR.items():
            sonra_dosya = dict(ozgun, **yama)
            dl = _diff(ozgun, sonra_dosya)
            dn = os.path.join(kok, ad + "_naif"); os.makedirs(dn); _yaz(dn, sonra_dosya)
            naif, _ = _kos(dn)                                                  # ajanın değiştirdiği testlerle
            dg = os.path.join(kok, ad + "_guvenli"); os.makedirs(dg); _yaz(dg, dict(sonra_dosya, **{"test_hesap.py": TEST}))
            guvenli, _ = _kos(dg)                                               # özgün testler geri yüklenerek
            on = swebench_odul_hesapla(dict(once), dict(naif), dl)
            og = swebench_odul_hesapla(dict(once), dict(guvenli), dl)
            fark = max(fark, abs(on["toplam_odul"] - _ref_odul(once, naif, dl)), abs(og["toplam_odul"] - _ref_odul(once, guvenli, dl)))
            tablo[ad] = {"diff_satir": dl, "naif_odul": on["toplam_odul"], "guvenli_odul": og["toplam_odul"], "f2p_guvenli": og["f2p_orani"],
                         "p2p_guvenli": og["p2p_orani"], "testler_guvenli": guvenli}

    # Gerçek yörünge: test çıktısı gözlem olarak, model eylemleri asistan turları
    tok, model = O.hf_model(O.QWEN_MODEL, O.QWEN_REVIZYON)
    mesajlar = [{"role": "system", "content": "You are a coding agent. Use tools by writing one action per turn."},
                {"role": "user", "content": "Fix the failing tests in hesap.py."},
                {"role": "assistant", "content": "Action: run_tests[]"},
                {"role": "user", "content": "Observation:\n" + cikti_ornek[-700:]},
                {"role": "assistant", "content": "Action: edit[hesap.py] return 0.0 for an empty list and treat yuzde as a percentage"},
                {"role": "user", "content": "Observation: Ran 4 tests. OK"},
                {"role": "assistant", "content": "Final: both bugs fixed, all tests pass."}]
    ids, segler = _turlar(tok, mesajlar)
    x = torch.tensor([ids])
    with torch.no_grad():
        lp = torch.log_softmax(model(x).logits[0, :-1].double(), -1).gather(1, x[0, 1:].unsqueeze(1)).squeeze(1)
    lp = torch.cat([torch.zeros(1, dtype=torch.float64), lp])
    adimlar, i = [], 0
    for rol, seg in segler:
        r = "action" if rol == "assistant" else ("observation" if i > len(segler[0][1]) + len(segler[1][1]) else "prompt")
        adimlar.append({"rol": r, "token_logp": [float(v) for v in lp[i:i + len(seg)]]})
        i += len(seg)
    avantaj = 1.0
    o = ajan_yorunge_maskele([dict(a) for a in adimlar], avantaj)
    maske = torch.tensor([1.0 if a["rol"] == "action" else 0.0 for a in adimlar for _ in a["token_logp"]], dtype=torch.float64)
    ref_kayip = float(-avantaj * (lp * maske).sum() / maske.sum())
    obs = [v for a in adimlar if a["rol"] == "observation" for v in a["token_logp"]]
    act = [v for a in adimlar if a["rol"] == "action" for v in a["token_logp"]]
    yor_fark = abs(o["politika_kaybi"] - ref_kayip)
    return {
        "model": {"model": O.QWEN_MODEL, "revizyon": O.QWEN_REVIZYON}, "surumler": O.surumler(),
        "once_testler": once, "yamalar": tablo, "odul_en_buyuk_fark": fark, "odul_ayni": fark <= 1e-9,
        "kurcalama_naif_odul": tablo["test_kurcalama"]["naif_odul"], "kurcalama_guvenli_odul": tablo["test_kurcalama"]["guvenli_odul"],
        "kurcalama_yakalandi": tablo["test_kurcalama"]["naif_odul"] > 1.0 and tablo["test_kurcalama"]["guvenli_odul"] <= 0.0,
        "yorunge_token": len(ids), "aktif_token": o["aktif_token_sayisi"], "maskelenen": o["maskelenen_token_sayisi"],
        "politika_kaybi": o["politika_kaybi"], "ref_kayip": ref_kayip, "yorunge_ayni": yor_fark <= 1e-5,
        "ort_logp_eylem": sum(act) / len(act), "ort_logp_gozlem": sum(obs) / len(obs),
        "olcum": (f"Gerçek test koşusu: başta {sum(once.values())}/{len(once)} test geçiyor. Ödüller (naif / özgün testler geri yüklenmiş): "
                  + ", ".join(f"{k} {v['naif_odul']}/{v['guvenli_odul']}" for k, v in tablo.items()) +
                  f". Testleri atlatan yama naif değerlendiricide {tablo['test_kurcalama']['naif_odul']} alıyor. Qwen yörüngesi {len(ids)} token, "
                  f"{o['aktif_token_sayisi']} eylem tokenı; ortalama log-olasılık eylemde {sum(act) / len(act):.2f}, gözlemde {sum(obs) / len(obs):.2f}; "
                  f"maskeli kayıp torch'tan {yor_fark:.1e}."),
        "sinir": ("Depo dört testlik küçük bir örnektir ve yamalar hazırdır (ajan üretmez). Yörünge elle kurulmuş, gözlemi gerçek test "
                  "çıktısıdır; RL eğitimi yapılmaz."),
    }


def goster(ajan_yorunge_maskele, swebench_odul_hesapla):
    r = deney(ajan_yorunge_maskele, swebench_odul_hesapla)
    print("yama              diff  naif ödül  güvenli ödül  F2P   P2P")
    for k, v in r["yamalar"].items():
        print("%-16s  %4d  %9.2f  %12.2f  %.2f  %.2f" % (k, v["diff_satir"], v["naif_odul"], v["guvenli_odul"], v["f2p_guvenli"], v["p2p_guvenli"]))
    print("Yörünge: %d token, %d eylem | log-olasılık eylem %.2f, gözlem %.2f | kayıp %.4f (torch %.4f)"
          % (r["yorunge_token"], r["aktif_token"], r["ort_logp_eylem"], r["ort_logp_gozlem"], r["politika_kaybi"], r["ref_kayip"]))
    print("Sınır:", r["sinir"])
    print("Kanıt:", O.kanit("ai-uretim-24", "run", r))
