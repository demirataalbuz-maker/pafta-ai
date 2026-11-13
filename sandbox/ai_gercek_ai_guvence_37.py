"""GCG-lite: token ikamesinde birinci derece tahmin gerçek loss farkını ne kadar öngörür? Zararsız hedef, SmolLM2-135M."""
import copy, importlib.metadata, math, os, random, re, secrets
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
import ai_lab

ONEKLER = ["Sabah pazarda gördüğüm meyve", "Tarifte kullanılacak meyve", "Sepetteki en güzel meyve"]
HEDEF = " muz"
AYAR = {"sonek": 8, "pozisyon": 4, "rastgele_aday": 128, "topk": 32, "arama_adim": 24, "arama_aday": 16, "yigin": 64, "onekler": ONEKLER, "hedef": HEDEF, "uretim_token": 4}


def _sayi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)


def referans_aday(g, mevcut, k, yasak):
    if not isinstance(g, list) or len(g) < 2 or not all(_sayi(v) for v in g):
        raise ValueError("g")
    if isinstance(mevcut, bool) or not isinstance(mevcut, int) or not 0 <= mevcut < len(g):
        raise ValueError("mevcut")
    if isinstance(k, bool) or not isinstance(k, int) or k < 1 or not isinstance(yasak, (set, frozenset)):
        raise ValueError("ayar")
    a = sorted((g[j] - g[mevcut], j) for j in range(len(g)) if j != mevcut and j not in yasak)
    return [{"token": j, "tahmin": d} for d, j in a[:k]]


def _rank(v):
    s = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and v[s[j + 1]] == v[s[i]]:
            j += 1
        for t in range(i, j + 1):
            r[s[t]] = (i + j) / 2 + 1
        i = j + 1
    return r


def referans_spearman(a, b):
    if not isinstance(a, list) or not isinstance(b, list) or len(a) != len(b) or len(a) < 2 or not all(_sayi(v) for v in a + b):
        raise ValueError("girdi")
    x, y = _rank(a), _rank(b)
    mx, my = sum(x) / len(x), sum(y) / len(y)
    sxx = sum((v - mx) ** 2 for v in x)
    syy = sum((v - my) ** 2 for v in y)
    if sxx == 0 or syy == 0:
        return None
    return sum((p - mx) * (q - my) for p, q in zip(x, y)) / math.sqrt(sxx * syy)


def referans_isabet(kayitlar, k):
    if not isinstance(kayitlar, list) or not kayitlar or isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= len(kayitlar):
        raise ValueError("girdi")
    gorulen = set()
    for r in kayitlar:
        if not isinstance(r, dict) or set(r) != {"token", "tahmin", "gercek"} or isinstance(r["token"], bool) or not isinstance(r["token"], int) or r["token"] in gorulen or not _sayi(r["tahmin"]) or not _sayi(r["gercek"]):
            raise ValueError("kayıt")
        gorulen.add(r["token"])
    p = sorted(kayitlar, key=lambda r: (r["tahmin"], r["token"]))[:k]
    q = sorted(kayitlar, key=lambda r: (r["gercek"], r["token"]))[:k]
    en_iyi = min(kayitlar, key=lambda r: (r["gercek"], r["token"]))["token"]
    pk = {r["token"] for r in p}
    return {"isabet": en_iyi in pk, "kesisim": len(pk & {r["token"] for r in q}) / k, "rastgele_beklenti": k / len(kayitlar),
            "iyilesen_oran": sum(r["gercek"] < 0 for r in p) / k, "ort_gercek_topk": sum(r["gercek"] for r in p) / k, "ort_gercek_tum": sum(r["gercek"] for r in kayitlar) / len(kayitlar)}


def _yakin(a, b, tol=1e-9):
    if isinstance(a, dict):
        return isinstance(b, dict) and set(a) == set(b) and all(_yakin(a[k], b[k], tol) for k in a)
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(_yakin(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, (bool, str)) or a is None:
        return type(a) is type(b) and a == b
    return _sayi(a) and _sayi(b) and abs(a - b) <= tol * max(1.0, abs(a), abs(b))


class _Lab:
    def __init__(self):
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
            self.tok = AutoTokenizer.from_pretrained(ai_lab.HF_MODEL, revision=ai_lab.HF_REVIZYON, local_files_only=True)
            self.cihaz = ai_lab.torch_cihazi()
            self.net = AutoModelForCausalLM.from_pretrained(ai_lab.HF_MODEL, revision=ai_lab.HF_REVIZYON, local_files_only=True, dtype=torch.float32).to(self.cihaz).eval()
        except Exception as e:
            raise ai_lab.GercekLabYok(str(e)) from e
        self.torch = torch
        for p in self.net.parameters():
            p.requires_grad_(False)
        self.E = self.net.get_input_embeddings().weight
        tokenler = self.tok.convert_ids_to_tokens(list(range(self.E.shape[0])))
        izin = [i for i, t in enumerate(tokenler) if t and re.fullmatch(r"[A-Za-z]{2,10}", t)]
        self.izin = izin
        self.yasak = frozenset(set(range(self.E.shape[0])) - set(izin))

    def kur(self, onek, rng):
        t = self.tok.encode(onek, add_special_tokens=False)
        h = self.tok.encode(HEDEF, add_special_tokens=False)
        return t, [rng.choice(self.izin) for _ in range(AYAR["sonek"])], h

    def kayip(self, t, sonekler, h):
        torch = self.torch
        out = []
        for i in range(0, len(sonekler), AYAR["yigin"]):
            p = sonekler[i: i + AYAR["yigin"]]
            ids = torch.tensor([t + s + h for s in p], device=self.cihaz)
            with torch.no_grad():
                z = self.net(input_ids=ids).logits
            b = len(t) + AYAR["sonek"]
            hedef = ids[:, b:]
            ls = torch.nn.functional.cross_entropy(z[:, b - 1:-1].transpose(1, 2).double(), hedef, reduction="none").mean(1)
            out += ls.tolist()
        return out

    def gradyan(self, t, s, h, poz):
        torch = self.torch
        ids = torch.tensor([t + s + h], device=self.cihaz)
        e = self.E[ids].detach()
        bir = torch.zeros(self.E.shape[0], device=self.cihaz, dtype=self.E.dtype)
        bir[s[poz]] = 1.0
        bir.requires_grad_(True)
        konum = len(t) + poz
        emb = torch.cat([e[:, :konum], (bir @ self.E).view(1, 1, -1), e[:, konum + 1:]], 1)
        z = self.net(inputs_embeds=emb).logits
        b = len(t) + AYAR["sonek"]
        ls = torch.nn.functional.cross_entropy(z[:, b - 1:-1].transpose(1, 2), ids[:, b:])
        return torch.autograd.grad(ls, bir)[0].double().tolist()


def deney(aday_fn, spearman_fn, isabet_fn):
    lab = _Lab()
    rng = random.Random(secrets.randbits(64))
    onek = rng.choice(ONEKLER)
    t, s, h = lab.kur(onek, rng)
    taban = lab.kayip(t, [s], h)[0]
    aday_ayni, sp_ayni, is_ayni = True, True, True
    pozlar = []
    for poz in rng.sample(range(AYAR["sonek"]), AYAR["pozisyon"]):
        g = lab.gradyan(t, s, h, poz)
        o = aday_fn(list(g), s[poz], AYAR["topk"], lab.yasak)
        r = referans_aday(g, s[poz], AYAR["topk"], lab.yasak)
        aday_ayni = aday_ayni and _yakin(o, r)
        ras = rng.sample([i for i in lab.izin if i != s[poz] and i not in {k["token"] for k in r}], AYAR["rastgele_aday"])
        hepsi = ras + [k["token"] for k in r]
        sonekler = [s[:poz] + [j] + s[poz + 1:] for j in hepsi]
        ger = lab.kayip(t, sonekler, h)
        kay = [{"token": j, "tahmin": g[j] - g[s[poz]], "gercek": v - taban} for j, v in zip(hepsi, ger)]
        rs = referans_spearman([k["tahmin"] for k in kay], [k["gercek"] for k in kay])
        so = spearman_fn([k["tahmin"] for k in kay], [k["gercek"] for k in kay])
        sp_ayni = sp_ayni and _yakin(so, rs)
        ri = referans_isabet(kay, AYAR["topk"])
        oi = isabet_fn(copy.deepcopy(kay), AYAR["topk"])
        is_ayni = is_ayni and _yakin(oi, ri)
        ras_kay = [k for k in kay if k["token"] in set(ras)]
        pozlar.append({"poz": poz, "spearman": rs, "spearman_rastgele": referans_spearman([k["tahmin"] for k in ras_kay], [k["gercek"] for k in ras_kay]), "isabet": ri,
                       "ort_gercek_rastgele": sum(k["gercek"] for k in ras_kay) / len(ras_kay), "tahmin_ort_mutlak": sum(abs(k["tahmin"]) for k in kay) / len(kay), "gercek_ort_mutlak": sum(abs(k["gercek"]) for k in kay) / len(kay)})

    def ara(secici):
        sonek = list(s)
        k = lab.kayip(t, [sonek], h)[0]
        iz = [k]
        sorgu = 0
        for _ in range(AYAR["arama_adim"]):
            poz = rng.randrange(AYAR["sonek"])
            ad = secici(sonek, poz)
            son = [sonek[:poz] + [j] + sonek[poz + 1:] for j in ad]
            v = lab.kayip(t, son, h)
            sorgu += len(ad)
            m = min(range(len(ad)), key=lambda i: v[i])
            if v[m] < k:
                k, sonek = v[m], son[m]
            iz.append(k)
        return {"iz": iz, "sorgu": sorgu, "sonek": sonek, "son_kayip": k}

    grad = ara(lambda so, poz: [d["token"] for d in aday_fn(lab.gradyan(t, so, h, poz), so[poz], AYAR["arama_aday"], lab.yasak)])
    rast = ara(lambda so, poz: rng.sample([i for i in lab.izin if i != so[poz]], AYAR["arama_aday"]))

    def uret(so):
        ids = lab.torch.tensor([t + so], device=lab.cihaz)
        with lab.torch.no_grad():
            y = lab.net.generate(ids, max_new_tokens=AYAR["uretim_token"], do_sample=False, pad_token_id=lab.tok.eos_token_id)
        return lab.tok.decode(y[0, ids.shape[1]:], skip_special_tokens=True)

    for ad, r in (("grad", grad), ("rast", rast)):
        r["uretim"] = uret(r["sonek"])
        r["sonek_metin"] = lab.tok.decode(r["sonek"])
    sonuc = {"model": ai_lab.HF_MODEL, "revizyon": ai_lab.HF_REVIZYON, "cihaz": str(lab.cihaz), "surumler": {x: importlib.metadata.version(x) for x in ("torch", "transformers")}, "ayarlar": AYAR, "onek": onek,
             "sozluk": lab.E.shape[0], "izinli": len(lab.izin), "taban_kayip": taban, "pozisyonlar": pozlar, "aday_ayni": aday_ayni, "spearman_ayni": sp_ayni, "isabet_ayni": is_ayni, "gradyan_arama": grad, "rastgele_arama": rast,
             "olcum": "Tahmin: g[j]-g[mevcut] (one-hot gradient). Gerçek: tokeni değiştirip modeli yeniden koşturunca hedef token loss farkı. Hedef zararsız ' muz' kelimesidir.",
             "sinir": "Tek küçük model, zararsız kısa hedef, tek rastgele başlangıç; güvenlik hizalaması, jailbreak başarısı veya transfer hakkında bilgi vermez."}
    del lab
    return sonuc


def goster(aday_fn, spearman_fn, isabet_fn):
    r = deney(aday_fn, spearman_fn, isabet_fn)
    print("Model", r["model"], r["revizyon"][:10], r["cihaz"], "| önek:", r["onek"], "| taban kayıp %.3f" % r["taban_kayip"])
    for p in r["pozisyonlar"]:
        print("Poz %d Spearman tüm=%.3f rastgele adaylar=%.3f | |tahmin| ort=%.3f |gerçek| ort=%.3f" % (p["poz"], p["spearman"], p["spearman_rastgele"], p["tahmin_ort_mutlak"], p["gercek_ort_mutlak"]))
        print("   top-k ort gerçek=%.3f rastgele ort gerçek=%.3f iyileşen oran=%.3f isabet=%s" % (p["isabet"]["ort_gercek_topk"], p["ort_gercek_rastgele"], p["isabet"]["iyilesen_oran"], p["isabet"]["isabet"]))
    for ad, k in (("gradyan", "gradyan_arama"), ("rastgele", "rastgele_arama")):
        print(ad, "aramasında sorgu", r[k]["sorgu"], "son kayıp %.3f" % r[k]["son_kayip"], "üretim:", repr(r[k]["uretim"]))
    print("Sınır:", r["sinir"])
    print("Kanıt:", ai_lab.kanit_yaz("ai-guvence-37-run", {"kaynak": "gercek", "kabul": False, "ders": "ai-guvence-37", "deney": r}))
