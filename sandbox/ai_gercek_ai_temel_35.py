# -*- coding: utf-8 -*-
"""ai-temel-35 gerçek deney: yerel Ollama modeli (qwen3:4b-instruct) gerçek bir metin üretirken GPU gücü nvidia-smi
(AMD'de rocm-smi) ile 100 ms aralıkla örneklenir; boşta güç ayrıca ölçülür. Öğrencinin token başına enerji işlevi
ölçülen güçle, Landauer işlevi GPU'nun ölçülen sıcaklığı ve kaba bir silinen bit tahminiyle çalıştırılır. Güç
telemetrisi olmayan makinede enerji ölçülmez ve bu açıkça kaydedilir."""
import re, shutil, subprocess, sys, threading, time
import ai_lab
from sandbox import ai_uretim_ortak as O

AYAR = {"bosta_s": 2.0, "en_fazla": 400, "beyin_watt": 20.0, "bit_flop": 16,
        "istem": "Write a detailed explanation, about 300 words, of how a refrigerator moves heat from inside to outside.",
        "normal_istem": "Name the capital city of France in one word.",
        "sunger_istem": "Write the word data six hundred times, separated by spaces.",
        "sunger_sinir": 700, "savunma_sinir": 60}


class _Olcer:
    def __init__(self):
        self.smi = shutil.which("nvidia-smi")
        self.rocm = None if self.smi else shutil.which("rocm-smi")
        self.ornek, self._dur, self._p, self._t = [], False, None, None

    def var(self):
        return bool(self.smi or self.rocm)

    def basla(self):
        if self.smi:
            self._p = subprocess.Popen([self.smi, "--query-gpu=power.draw,temperature.gpu", "--format=csv,noheader,nounits", "-lms", "100"],
                                       stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, creationflags=getattr(ai_lab, "NO_WINDOW", 0))
            self._t = threading.Thread(target=self._oku_smi, daemon=True)
        elif self.rocm:
            self._t = threading.Thread(target=self._oku_rocm, daemon=True)
        if self._t:
            self._t.start()

    def _oku_smi(self):
        for s in self._p.stdout:
            try:
                w, c = (float(x) for x in s.strip().split(",")[:2])
                self.ornek.append((time.perf_counter(), w, c))
            except ValueError:
                pass

    def _oku_rocm(self):
        while not self._dur:
            out = subprocess.run([self.rocm, "--showpower", "--showtemp"], capture_output=True, text=True).stdout
            w = re.findall(r"Power.*?:\s*([\d.]+)", out)
            c = re.findall(r"Temperature.*?:\s*([\d.]+)", out)
            if w:
                self.ornek.append((time.perf_counter(), float(w[0]), float(c[0]) if c else float("nan")))
            time.sleep(0.1)

    def dur(self):
        self._dur = True
        if self._p:
            self._p.terminate()
        if self._t:
            self._t.join(timeout=3)

    def aralik(self, a, b):
        return [x for x in self.ornek if a <= x[0] <= b]


def deney(landauer_karsilastir, token_enerjisi):
    olcer = _Olcer()
    with ai_lab.SohbetOturumu() as ot:
        ot.sohbet([{"role": "user", "content": "Say OK."}], seed=0, sicaklik=0.0, en_fazla=5)    # modeli yükle (ölçüme girmesin)
        olcer.basla()
        time.sleep(0.3)
        t_bos = time.perf_counter()
        time.sleep(AYAR["bosta_s"])
        t0 = time.perf_counter()
        y = ot.sohbet([{"role": "user", "content": AYAR["istem"]}], seed=0, sicaklik=0.7, en_fazla=AYAR["en_fazla"])
        t1 = time.perf_counter()
        time.sleep(0.2)
        sunger = {}                                                            # enerji-gecikme saldırısı: girdi kısa, çıktı uzun
        for ad, istem, sinir in (("normal", AYAR["normal_istem"], AYAR["sunger_sinir"]), ("sunger", AYAR["sunger_istem"], AYAR["sunger_sinir"]),
                                 ("sunger_token_siniri", AYAR["sunger_istem"], AYAR["savunma_sinir"])):
            a = time.perf_counter()
            yy = ot.sohbet([{"role": "user", "content": istem}], seed=0, sicaklik=0.0, en_fazla=sinir)
            b = time.perf_counter()
            om = olcer.aralik(a, b)
            if len(om) < 2:                                                    # 100 ms'den kısa istek: en yakın örnekler
                time.sleep(0.25)
                om = olcer.aralik(a - 0.2, b + 0.2)
            w = sum(x[1] for x in om) / len(om) if len(om) >= 2 else None
            sunger[ad] = {"girdi_karakter": len(istem), "cikti_token": int(yy.get("eval_count") or 0), "sure_s": round(b - a, 3),
                          "ortalama_watt": round(w, 2) if w is not None else None, "joule": round(w * (b - a), 2) if w is not None else None}
            time.sleep(0.2)
        olcer.dur()
        kayit = ot.kayit.get("model") or {}
    token = int(y.get("eval_count") or 0)
    if token <= 0:
        raise ai_lab.GercekLabYok("Ollama üretilen token sayısını vermedi")
    sure = t1 - t0
    bos = olcer.aralik(t_bos, t0)
    uretim = olcer.aralik(t0, t1)
    olculdu = olcer.var() and len(uretim) >= 3 and len(bos) >= 3
    watt = [w for _, w, _ in uretim] if olculdu else [0.0]
    o = token_enerjisi(list(watt), sure, token, AYAR["beyin_watt"])
    p = sum(watt) / len(watt)
    ref = {"ortalama_watt": round(p, 6), "joule_token": round(p * sure / token, 6), "beyin_joule_token": round(AYAR["beyin_watt"] * sure / token, 6)}
    fonk_ayni = all(abs(o[k] - v) <= 1e-6 for k, v in ref.items())
    bos_watt = sum(w for _, w, _ in bos) / len(bos) if olculdu else None
    ek_joule_token = (p - bos_watt) * sure / token if olculdu else None
    m = re.match(r"([\d.]+)\s*B", str((kayit.get("ayrinti") or {}).get("parameter_size", "")))
    param = float(m.group(1)) * 1e9 if m else 4.0e9
    flop_token = 2 * param
    sicaklik = (sum(c for _, _, c in uretim) / len(uretim) + 273.15) if olculdu else 300.0
    L = landauer_karsilastir(sicaklik, flop_token * AYAR["bit_flop"], o["joule_token"]) if olculdu else None
    L_ref = 1.380649e-23 * sicaklik * 0.6931471805599453 * flop_token * AYAR["bit_flop"] if olculdu else None
    landauer_ayni = (not olculdu) or abs(L["min_joule"] - L_ref) <= 1e-9 * L_ref
    olcut = "joule" if all(v["joule"] for v in sunger.values()) else "sure_s"
    carpan = sunger["sunger"][olcut] / max(sunger["normal"][olcut], 1e-9)
    savunma = sunger["sunger"][olcut] / max(sunger["sunger_token_siniri"][olcut], 1e-9)
    return {
        "model": kayit, "surumler": O.surumler(), "platform": sys.platform, "telemetri": "nvidia-smi" if olcer.smi else ("rocm-smi" if olcer.rocm else None),
        "enerji_olculdu": olculdu, "uretilen_token": token, "sure_s": sure, "token_s": token / sure,
        "bosta_watt": bos_watt, "ornek_sayisi": len(uretim), "enerji": o, "fonksiyon_ayni": fonk_ayni,
        "ek_joule_token": ek_joule_token, "parametre": param, "flop_token": flop_token, "gpu_sicaklik_k": sicaklik if olculdu else None,
        "landauer": L, "landauer_ayni": landauer_ayni,
        "beyinden_fazla": (not olculdu) or o["beyin_orani"] > 0,
        "sunger": sunger, "sunger_olcutu": olcut, "sunger_carpani": round(carpan, 2), "token_siniri_kazanci": round(savunma, 2),
        "sunger_saldirisi_olculdu": carpan >= 10 and savunma >= 3 and sunger["normal"]["girdi_karakter"] >= 0.5 * sunger["sunger"]["girdi_karakter"],
        "ozet": ((f"{kayit.get('ad', 'Ollama')} {token} token, {sure:.1f} s ({token / sure:.1f} token/s). Ortalama GPU gücü {p:.1f} W (boşta {bos_watt:.1f} W): "
                  f"{o['joule_token']:.3f} J/token (boşa göre ek {ek_joule_token:.3f} J/token); aynı sürede 20 W'lık beyin {o['beyin_joule_token']:.3f} J/token "
                  f"harcar (oran {o['beyin_orani']:.1f}). Landauer: {flop_token:.1e} FLOP/token × {AYAR['bit_flop']} bit ≈ {flop_token * AYAR['bit_flop']:.1e} "
                  f"silinen bit için alt sınır {L['min_joule']:.2e} J; ölçülen 10^{L['log10_oran']} katı.") if olculdu else
                 (f"{kayit.get('ad', 'Ollama')} {token} token, {sure:.1f} s ({token / sure:.1f} token/s). Bu makinede GPU güç telemetrisi yok; enerji ölçülmedi."))
                + f" Sünger istek ({olcut}): normal {sunger['normal'][olcut]} / sünger {sunger['sunger'][olcut]} / {AYAR['savunma_sinir']} token sınırlı "
                  f"{sunger['sunger_token_siniri'][olcut]} (çıktı token {sunger['normal']['cikti_token']} / {sunger['sunger']['cikti_token']} / "
                  f"{sunger['sunger_token_siniri']['cikti_token']}); benzer uzunlukta bir girdi {carpan:.0f} kat kaynak harcatıyor.",
        "sinir": ("Yalnız GPU kartının bildirdiği güç ölçülür (CPU, bellek, güç kaynağı kaybı hariç); örnekleme 100 ms'dir. Silinen bit sayısı "
                  "FLOP başına 16 bit varsayımıyla kaba bir tahmindir. Beyin karşılaştırması aynı süredeki toplam beyin gücüdür; beyin bu işi yapmaz. "
                  "Sünger istek tek ve açık bir uzun çıktı isteğidir; Shumailov vd. 2021'in optimize edilmiş sünger girdileri aynı çıktı sınırında "
                  "da hesap başına enerjiyi artırabilir. Telemetri yoksa karşılaştırma süreyle yapılır."),
    }


def goster(landauer_karsilastir, token_enerjisi):
    r = deney(landauer_karsilastir, token_enerjisi)
    print(r["ozet"])
    print("Enerji:", r["enerji"])
    print("Landauer:", r["landauer"])
    print("Sınır:", r["sinir"])
    print("Kanıt:", O.kanit("ai-temel-35", "run", r))
