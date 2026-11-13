# -*- coding: utf-8 -*-
"""ai-uretim-35 gerçek deney: (1) yerel Ollama modeli (qwen3:4b-instruct) beş küçük kodlama sorusuna sorusu başına n
örnek üretir; her örnek izole bir alt süreçte gerçek birim testleriyle çalıştırılır ve öğrencinin yansız pass@k
tahmincisi gerçek doğru sayılarıyla hesaplanır, torch'suz kapalı form ve örneklemeyle karşılaştırılır. (2) Pafta ders
metinlerinden oluşan gerçek bir korpusa test sorularının birebir, hafif değiştirilmiş ve yeniden yazılmış kopyaları
yerleştirilir; öğrencinin n-gram temizleyicisinin farklı n değerlerinde yakalama ve yanlış alarm oranı ölçülür."""
import glob, math, os, random, re, subprocess, sys, tempfile
import ai_lab
from sandbox import ai_uretim_ortak as O

AYAR = {"model": "llama3.2:3b", "n": 8, "kler": [1, 3, 5], "sicaklik": 0.8, "zaman": 10, "seed": 35, "ngramlar": [5, 8, 13], "paragraf": 200}
GOREVLER = [
    ("asal_mi", "Write a Python function asal_mi(n) that returns True if the integer n is a prime number and False otherwise.",
     "assert asal_mi(2) and asal_mi(13) and asal_mi(7919)\nassert not asal_mi(1) and not asal_mi(0) and not asal_mi(15) and not asal_mi(-7) and not asal_mi(7917)"),
    ("kelime_say", "Write a Python function kelime_say(metin) that returns a dict mapping each word to its count; comparison ignores case and leading/trailing punctuation .,!?;: is stripped from words.",
     "assert kelime_say('Hello, hello! World.') == {'hello': 2, 'world': 1}\nassert kelime_say('') == {}\nassert kelime_say('a; A: b') == {'a': 2, 'b': 1}"),
    ("roma", "Write a Python function roma(n) that converts an integer 1 <= n <= 3999 to a Roman numeral string.",
     "assert roma(4) == 'IV' and roma(9) == 'IX' and roma(14) == 'XIV' and roma(40) == 'XL' and roma(90) == 'XC'\nassert roma(1994) == 'MCMXCIV' and roma(3999) == 'MMMCMXCIX' and roma(444) == 'CDXLIV'"),
    ("parantez_dengeli", "Write a Python function parantez_dengeli(s) that returns True if the brackets (), [] and {} in the string s are balanced and correctly nested, ignoring all other characters.",
     "assert parantez_dengeli('a(b[c]{d})') and parantez_dengeli('')\nassert not parantez_dengeli('(]') and not parantez_dengeli('([)]') and not parantez_dengeli('((') and not parantez_dengeli('}{')"),
    ("aralik_birlestir", "Write a Python function aralik_birlestir(araliklar) that takes a list of [start, end] integer intervals and returns the sorted list of merged intervals, where touching intervals like [1, 2] and [2, 3] are merged.",
     "assert aralik_birlestir([[5, 6], [1, 3], [2, 4]]) == [[1, 4], [5, 6]]\nassert aralik_birlestir([[1, 2], [2, 3]]) == [[1, 3]]\nassert aralik_birlestir([]) == []\nassert aralik_birlestir([[1, 10], [2, 3]]) == [[1, 10]]"),]


def _kod(yanit):
    m = re.findall(r"```(?:python)?\n(.*?)```", yanit, re.S)
    return m[0] if m else yanit


def _calistir(kod, test):
    with tempfile.TemporaryDirectory() as d:
        yol = os.path.join(d, "aday.py")
        open(yol, "w", encoding="utf-8").write(kod + "\n\n" + test + "\nprint('GECTI')\n")
        try:
            p = subprocess.run([sys.executable, "-I", yol], capture_output=True, text=True, timeout=AYAR["zaman"], cwd=d,
                               env={"PATH": os.environ.get("PATH", ""), "SYSTEMROOT": os.environ.get("SYSTEMROOT", "")})
        except subprocess.TimeoutExpired:
            return False
        return p.returncode == 0 and "GECTI" in p.stdout


def _paragraflar():
    out = []
    for yol in sorted(glob.glob(os.path.join(O.KOK, "tracks", "ai-*", "lessons", "*.md"))):
        t = re.sub(r"```.*?```", " ", open(yol, encoding="utf-8").read(), flags=re.S)
        out += [" ".join(p.split()) for p in re.split(r"\n\s*\n", t) if 30 <= len(p.split()) <= 120]
    return out


def deney(yansiz_pass_at_k, benchmark_sizinti_temizle):
    rnd = random.Random(AYAR["seed"])
    # 1) Gerçek üretim + gerçek test koşusu
    dogru, ornekler = [], {}
    with ai_lab.SohbetOturumu(model=AYAR["model"]) as ot:
        for ad, soru, test in GOREVLER:
            c = 0
            for s in range(AYAR["n"]):
                y = ot.sohbet([{"role": "user", "content": soru + " Reply with only the code in a single Python code block."}],
                              seed=s, sicaklik=AYAR["sicaklik"], en_fazla=300)["icerik"]
                gecti = _calistir(_kod(y), test)
                c += gecti
                ornekler.setdefault(ad, []).append(gecti)
            dogru.append(c)
        kayit = ot.kayit.get("model")
    tablo, fark = {}, 0.0
    for k in AYAR["kler"]:
        o = yansiz_pass_at_k(AYAR["n"], list(dogru), k)
        kapali = [1.0 - (math.comb(AYAR["n"] - c, k) / math.comb(AYAR["n"], k) if AYAR["n"] - c >= k else 0.0) for c in dogru]
        orneklem = [sum(any(rnd.sample(ornekler[ad], k)) for _ in range(4000)) / 4000 for ad, _, _ in GOREVLER]
        naif = [sum(ornekler[ad][:k]) > 0 for ad, _, _ in GOREVLER]              # ilk k örneğe bakan yanlı tahmin
        fark = max(fark, max(abs(a - b) for a, b in zip(o["soru_skorlari"], kapali)))
        tablo[k] = {"ogrenci": o["ortalama_pass_at_k"], "kapali_form": sum(kapali) / len(kapali), "orneklem": sum(orneklem) / len(orneklem),
                    "ilk_k_naif": sum(naif) / len(naif)}
    # 2) Sızıntı temizleme: gerçek korpus + yerleştirilmiş sızıntılar
    para = _paragraflar()
    rnd.shuffle(para)
    temiz = para[: AYAR["paragraf"]]
    sorular = [s for _, s, _ in GOREVLER]
    birebir = [f"Homework solution notes. {sorular[0]} Answer: check divisors up to the square root."]
    hafif = [f"Exercise: {sorular[2].replace('Write a Python function', 'Implement a Python function')} Tip: use a table of values."]
    yeniden = ["Practice task: implement aralik_birlestir which joins overlapping or adjacent integer ranges and returns them in sorted order."]
    korpus = temiz + birebir + hafif + yeniden
    sizinti_idx = {"birebir": len(temiz), "hafif": len(temiz) + 1, "yeniden_yazilmis": len(temiz) + 2}
    dc = {}
    for n in AYAR["ngramlar"]:
        o = benchmark_sizinti_temizle(list(korpus), list(sorular), n)
        kirli = set(o["kirli_indisler"])
        dc[n] = {"yakalanan": {k: v in kirli for k, v in sizinti_idx.items()}, "yanlis_alarm": sum(1 for i in kirli if i < len(temiz)),
                 "test_ngram": o["test_ngram_sayisi"]}
    return {
        "model": kayit, "surumler": O.surumler(), "n": AYAR["n"], "dogru_sayilari": dict(zip([g[0] for g in GOREVLER], dogru)),
        "pass_at_k": tablo, "pass_fark": fark, "pass_ayni": fark <= 1e-12,
        "orneklemle_tutarli": all(abs(v["ogrenci"] - v["orneklem"]) <= 0.05 for v in tablo.values()),
        "temizleme": dc, "korpus": len(korpus),
        "birebir_yakalandi": dc[5]["yakalanan"]["birebir"] and dc[8]["yakalanan"]["birebir"], "yanlis_alarm_yok": all(v["yanlis_alarm"] == 0 for v in dc.values()),
        "kisa_n_kapsami": {n: v["test_ngram"] for n, v in dc.items()},
        "yeniden_yazilmis_kacti": not any(v["yakalanan"]["yeniden_yazilmis"] for v in dc.values()),
        "olcum": (f"{(kayit or {}).get('ad', 'Ollama')} {len(GOREVLER)} soruda {AYAR['n']}'er örnek (T={AYAR['sicaklik']}), gerçek test koşusuyla doğru "
                  f"sayıları {dogru}. pass@k (öğrenci / örnekleme / yalnız ilk k örnek): "
                  + "; ".join(f"k={k}: {v['ogrenci']:.3f} / {v['orneklem']:.3f} / {v['ilk_k_naif']:.2f}" for k, v in tablo.items()) +
                  f". {len(temiz)} gerçek paragraf + 3 sızıntı: " + "; ".join(f"n={n} yakalanan {sum(v['yakalanan'].values())}/3, yanlış alarm {v['yanlis_alarm']}" for n, v in dc.items()) + "."),
        "sinir": ("Beş soru ve soru başına 8 örnek küçük bir örneklemdir; testler sorunun yalnız birkaç durumunu kapsar. Üretilen kod "
                  "izole bir alt süreçte (python -I, geçici klasör, zaman aşımı) çalıştırılır ama işletim sistemi düzeyinde bir sandbox yoktur. "
                  "Sızıntılar elle yerleştirilmiştir."),
    }


def goster(yansiz_pass_at_k, benchmark_sizinti_temizle):
    r = deney(yansiz_pass_at_k, benchmark_sizinti_temizle)
    print("Doğru sayıları (n=%d):" % r["n"], r["dogru_sayilari"])
    for k, v in r["pass_at_k"].items():
        print("  pass@%d  öğrenci %.3f | kapalı form %.3f | örnekleme %.3f | ilk k (yanlı) %.2f" % (k, v["ogrenci"], v["kapali_form"], v["orneklem"], v["ilk_k_naif"]))
    for n, v in r["temizleme"].items():
        print("  n=%-2d yakalanan %s | yanlış alarm %d" % (n, v["yakalanan"], v["yanlis_alarm"]))
    print("Sınır:", r["sinir"])
    print("Kanıt:", O.kanit("ai-uretim-35", "run", r))
