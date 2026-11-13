"""Speculative decoding ve Leviathan red örneklemesi: gerçek SmolLM2-135M'de kendi kendine spekülatif çözme (taslak = erken
katman çıkışı, hedef = tam model), kayıpsızlık özdeşliği ve taslak derinliğinin kabul oranına etkisi."""
import importlib.metadata, math, random, secrets
import ai_lab

AYAR = {
    "seed": 27,
    "gamma": 4,
    "tur_sayisi": 16,
    "taslak_katman": 12,
    "derinlik_tarama": [6, 12, 20],
    "tarama_tur": 4,
}


def _sayi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)


def _tam(v):
    return not isinstance(v, bool) and isinstance(v, int)


def _dagilim_dogrula(d):
    if not isinstance(d, list) or len(d) < 2:
        raise ValueError("dagilim_boyut")
    for x in d:
        if not _sayi(x) or not 0.0 <= x <= 1.0:
            raise ValueError("olasilik_deger")
    if abs(sum(d) - 1.0) > 1e-6:
        raise ValueError("olasilik_toplam")


def referans_kabul_olasiligi(p_hedef, q_taslak):
    if not _sayi(p_hedef) or not 0.0 <= p_hedef <= 1.0:
        raise ValueError("p_hedef")
    if not _sayi(q_taslak) or not 0.0 < q_taslak <= 1.0:
        raise ValueError("q_taslak")
    return float(min(1.0, p_hedef / q_taslak))


def referans_artik_dagilim(p_dagilim, q_dagilim):
    _dagilim_dogrula(p_dagilim)
    _dagilim_dogrula(q_dagilim)
    if len(p_dagilim) != len(q_dagilim):
        raise ValueError("esit_uzunluk")
    fark = [max(0.0, p - q) for p, q in zip(p_dagilim, q_dagilim)]
    toplam = sum(fark)
    if toplam <= 1e-12:
        raise ValueError("sifir_artik")
    return [v / toplam for v in fark]


def referans_spekulatif_ozet(p_adimlar, q_adimlar, tokenlar, u_Ornekler):
    if not isinstance(p_adimlar, list) or not isinstance(q_adimlar, list) or not isinstance(tokenlar, list) or not isinstance(u_Ornekler, list):
        raise ValueError("liste")
    gamma = len(p_adimlar)
    if gamma < 1 or len(q_adimlar) != gamma or len(tokenlar) != gamma or len(u_Ornekler) != gamma:
        raise ValueError("gamma_boyut")
    sozluk = None
    for t in range(gamma):
        p_t, q_t = p_adimlar[t], q_adimlar[t]
        _dagilim_dogrula(p_t)
        _dagilim_dogrula(q_t)
        if len(p_t) != len(q_t) or (sozluk is not None and len(p_t) != sozluk):
            raise ValueError("sozluk_boyut")
        sozluk = len(p_t)
        tok = tokenlar[t]
        u = u_Ornekler[t]
        if not _tam(tok) or not 0 <= tok < sozluk or q_t[tok] <= 0.0:
            raise ValueError("token")
        if not _sayi(u) or not 0.0 <= u < 1.0:
            raise ValueError("u_ornek")

    kabul_sayisi = 0
    red_adimi = None
    kurtarma_token = None
    for t in range(gamma):
        p_t, q_t = p_adimlar[t], q_adimlar[t]
        tok = tokenlar[t]
        alfa = referans_kabul_olasiligi(p_t[tok], q_t[tok])
        if u_Ornekler[t] < alfa:
            kabul_sayisi += 1
        else:
            red_adimi = t
            artik = referans_artik_dagilim(p_t, q_t)
            kurtarma_token = max(range(sozluk), key=lambda i: artik[i])
            break
    uretilen = kabul_sayisi + 1
    return {
        "kabul_sayisi": kabul_sayisi,
        "red_adimi": red_adimi,
        "kurtarma_token": kurtarma_token,
        "uretilen_token": uretilen,
        "hizlanma_carpani": float(uretilen),
    }


def _yakin(a, b, tol=1e-9):
    if isinstance(a, dict):
        return isinstance(b, dict) and set(a) == set(b) and all(_yakin(a[k], b[k], tol) for k in a)
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(_yakin(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, (bool, str)) or a is None:
        return type(a) is type(b) and a == b
    return _sayi(a) and _sayi(b) and abs(a - b) <= tol * max(1.0, abs(a), abs(b))


ISTEMLER = ["The history of the old harbor town begins", "To make a simple tomato soup, first", "The security team reviewed the logs and",
            "In the morning the market was full of"]
EGITIM_ISTEMLERI = ["Once upon a time in a small village", "The report describes the main findings of", "A good way to start the day is",
                    "The engineers tested the new bridge by", "Last summer we travelled to the coast and", "The museum guide explained that",
                    "Our neighbors often talk about", "The recipe calls for two cups of"]


class _SelfSpec:
    """Hedef: tam SmolLM2-135M. Taslak: aynı modelin `cikis` katmanından erken çıkış (son norm + lm_head)."""

    def __init__(self, torch, model, cihaz):
        self.t, self.m, self.c = torch, model, cihaz
        self.adaptor = {}

    def dagilim(self, ids, cikis=None):
        """ids'in her konumundaki sonraki-token dağılımı (float64); cikis verilirse o katmandan erken çıkış
        (o katman için eğitilmiş adaptör varsa önce adaptörden geçer)."""
        with self.t.no_grad():
            o = self.m(self.t.tensor([ids], device=self.c), output_hidden_states=cikis is not None)
            if cikis is None:
                z = o.logits[0]
            else:
                h = o.hidden_states[cikis][0]
                if cikis in self.adaptor:
                    h = self.adaptor[cikis](h)
                z = self.m.lm_head(self.m.model.norm(h))
        return self.t.softmax(z.double(), dim=-1)

    def adaptor_egit(self, tok, cikis, istemler, adim=150, uzunluk=64):
        """Kendi kendine damıtma: modelin ürettiği metinde cikis katmanı gizli durumunu son dağılıma KL ile eşleyen doğrusal adaptör."""
        t = self.t
        g = t.Generator(device=self.c).manual_seed(27)
        H, P = [], []
        for s in istemler:
            ids = tok(s, add_special_tokens=False)["input_ids"]
            with t.no_grad():
                seq = self.m.generate(t.tensor([ids], device=self.c), max_new_tokens=uzunluk, do_sample=True, top_k=0,
                                      pad_token_id=tok.eos_token_id)
                o = self.m(seq, output_hidden_states=True)
            H.append(o.hidden_states[cikis][0].float())
            P.append(t.log_softmax(o.logits[0].float(), dim=-1))
        H, P = t.cat(H), t.cat(P)
        d = H.shape[1]
        lin = t.nn.Linear(d, d).to(self.c)
        with t.no_grad():
            lin.weight.copy_(t.eye(d, device=self.c))
            lin.bias.zero_()
        opt = t.optim.Adam(lin.parameters(), lr=1e-3)
        for p in self.m.parameters():
            p.requires_grad_(False)
        for _ in range(adim):
            opt.zero_grad()
            lq = t.log_softmax(self.m.lm_head(self.m.model.norm(lin(H))).float(), dim=-1)
            (t.exp(P) * (P - lq)).sum(-1).mean().backward()
            opt.step()
        lin.requires_grad_(False)
        self.adaptor[cikis] = lin


def _tur_referans(ss, torch, ids, gamma, cikis, gen):
    """Torch ile bir spekülatif tur (derinlik taraması için): üretilen token sayısı ve yeni bağlam."""
    taslak, qs = [], []
    for _ in range(gamma):
        q = ss.dagilim(ids + taslak, cikis)[-1]
        taslak.append(int(torch.multinomial(q, 1, generator=gen)))
        qs.append(q)
    P = ss.dagilim(ids + taslak)[len(ids) - 1:]
    kabul = 0
    for t in range(gamma):
        tok = taslak[t]
        if float(torch.rand(1, generator=gen, device=P.device)) < min(1.0, float(P[t, tok] / qs[t][tok])):
            kabul += 1
        else:
            artik = (P[t] - qs[t]).clamp_min(0)
            return kabul + 1, ids + taslak[:t] + [int(artik.argmax())]
    return kabul + 1, ids + taslak + [int(P[gamma].argmax())]


def deney(kabul_fn, artik_fn, ozet_fn):
    try:
        import torch
    except ImportError as e:
        raise ai_lab.GercekLabYok(str(e)) from e
    tok, model, bilgi = ai_lab.dil_modeli()
    cihaz = ai_lab.torch_cihazi()
    model.to(cihaz)
    ss = _SelfSpec(torch, model, cihaz)
    G, cikis = AYAR["gamma"], AYAR["taslak_katman"]

    def tarama_yap():
        sonuc = {}
        for d in AYAR["derinlik_tarama"]:
            g2 = torch.Generator(device=cihaz).manual_seed(AYAR["seed"])
            uret = tur = 0
            for istem in ISTEMLER:
                x = tok(istem, add_special_tokens=False)["input_ids"]
                for _ in range(AYAR["tarama_tur"]):
                    n, x = _tur_referans(ss, torch, x, G, d, g2)
                    uret += n
                    tur += 1
            sonuc[d] = uret / tur
        return sonuc

    tarama_ayarsiz = tarama_yap()
    for d in AYAR["derinlik_tarama"]:
        ss.adaptor_egit(tok, d, EGITIM_ISTEMLERI)
    tarama = tarama_yap()
    gen = torch.Generator(device=cihaz).manual_seed(secrets.randbits(31))
    rng = random.Random(secrets.randbits(64))
    kabul_ayni = artik_ayni = ozet_ayni = artik_toplam_bir = True
    toplam_uretilen, tam_kabul_say, turlar = 0, 0, []
    for istem in ISTEMLER:
        ids = tok(istem, add_special_tokens=False)["input_ids"]
        for _ in range(AYAR["tur_sayisi"] // len(ISTEMLER)):
            taslak, q_ad = [], []
            for _ in range(G):
                q = ss.dagilim(ids + taslak, cikis)[-1]
                taslak.append(int(torch.multinomial(q, 1, generator=gen)))
                q_ad.append(q.tolist())
            P = ss.dagilim(ids + taslak)[len(ids) - 1:]
            p_ad = [P[t].tolist() for t in range(G)]
            u_orn = [rng.uniform(0.0, 0.9999) for _ in range(G)]
            for t in range(G):
                kabul_ayni = kabul_ayni and _yakin(kabul_fn(p_ad[t][taslak[t]], q_ad[t][taslak[t]]),
                                                   referans_kabul_olasiligi(p_ad[t][taslak[t]], q_ad[t][taslak[t]]))
            t0 = 0
            ar_o, ar_r = artik_fn(list(p_ad[t0]), list(q_ad[t0])), referans_artik_dagilim(p_ad[t0], q_ad[t0])
            artik_ayni = artik_ayni and _yakin(ar_o, ar_r)
            artik_toplam_bir = artik_toplam_bir and abs(sum(ar_o) - 1.0) <= 1e-9
            oz_o = ozet_fn([list(r) for r in p_ad], [list(r) for r in q_ad], list(taslak), list(u_orn))
            oz_r = referans_spekulatif_ozet(p_ad, q_ad, taslak, u_orn)
            ozet_ayni = ozet_ayni and _yakin(oz_o, oz_r)
            toplam_uretilen += oz_r["uretilen_token"]
            tam_kabul_say += oz_r["red_adimi"] is None
            if oz_r["red_adimi"] is None:
                ids = ids + taslak + [int(P[G].argmax())]
            else:
                ids = ids + taslak[:oz_r["red_adimi"]] + [oz_r["kurtarma_token"]]
            if len(turlar) < 4:
                turlar.append({"istem": istem, "taslak": tok.decode(taslak), "ozet": oz_r})

    # Kayıpsızlık: ilk istemin ilk adımında kabul + red sonrası artık dağılım = hedef dağılım (49.152 token).
    ids0 = tok(ISTEMLER[0], add_special_tokens=False)["input_ids"]
    p0, q0 = ss.dagilim(ids0)[-1].tolist(), ss.dagilim(ids0, cikis)[-1].tolist()
    a0 = artik_fn(list(p0), list(q0))
    kabul_k = sum(q0[j] * kabul_fn(p0[j], q0[j]) for j in range(len(p0)) if q0[j] > 0)
    spek = [(q0[j] * kabul_fn(p0[j], q0[j]) if q0[j] > 0 else 0.0) + (1.0 - kabul_k) * a0[j] for j in range(len(p0))]
    sapma = max(abs(spek[j] - p0[j]) for j in range(len(p0)))

    n_tur = AYAR["tur_sayisi"] // len(ISTEMLER) * len(ISTEMLER)
    return {
        "cihaz": str(cihaz), "dtype": "float32 (dağılımlar float64)",
        "model": {k: bilgi[k] for k in ("model", "revizyon", "agirlik_sha256", "parametre")},
        "surumler": {"torch": importlib.metadata.version("torch"), "transformers": importlib.metadata.version("transformers")},
        "ayarlar": AYAR, "tur_sayisi": n_tur, "katman_sayisi": int(model.config.num_hidden_layers),
        "kabul_ayni": kabul_ayni, "artik_ayni": artik_ayni, "ozet_ayni": ozet_ayni, "artik_toplam_bir": artik_toplam_bir,
        "kayipsizlik_max_sapma": sapma, "dagilim_degismez": sapma <= 1e-9,
        "ortalama_hizlanma": toplam_uretilen / n_tur, "tam_kabul_orani": tam_kabul_say / n_tur,
        "derinlik_taramasi": tarama, "derinlik_taramasi_ayarsiz": tarama_ayarsiz, "ornek_turlar": turlar,
        "olcum": (f"SmolLM2-135M kendi kendine spekülatif çözme: taslak {cikis}. katmandan erken çıkış + kendi metninde damıtılmış doğrusal "
                  f"adaptör, hedef tam model ({model.config.num_hidden_layers} katman), γ={G}, {n_tur} tur. Hedef çağrısı başına ortalama "
                  f"{toplam_uretilen / n_tur:.2f} token, tam kabul oranı {tam_kabul_say / n_tur:.2f}; kayıpsızlık özdeşliğinde en büyük sapma "
                  f"{sapma:.1e}. Token/çağrı, ayarsız erken çıkış → ayarlı: "
                  + ", ".join(f"katman {d}: {tarama_ayarsiz[d]:.2f} → {tarama[d]:.2f}" for d in tarama) + "."),
        "sinir": ("Hızlanmayı hedef çağrısı başına token olarak ölçer, duvar saati süresini değil: erken çıkış taslağı burada aynı ileri geçişten "
                  "hesaplanır. Ağaç tabanlı doğrulama (Medusa, EAGLE), KV önbelleği ve sıcaklık/top-p etkisi ölçülmez."),
    }


def goster(kabul_fn, artik_fn, ozet_fn):
    r = deney(kabul_fn, artik_fn, ozet_fn)
    print("Model:", r["model"]["model"], "| cihaz:", r["cihaz"], "| taslak katmanı:", AYAR["taslak_katman"], "/", r["katman_sayisi"], "| tur:", r["tur_sayisi"])
    print("Hedef çağrısı başına token: %.3f | Tam kabul oranı: %.3f | Derinlik taraması: %s" % (r["ortalama_hizlanma"], r["tam_kabul_orani"], r["derinlik_taramasi"]))
    print("Kayıpsızlık en büyük sapma:", r["kayipsizlik_max_sapma"])
    print("Kayıpsız hedef dağılım değişmezliği doğrulandı mı?:", r["dagilim_degismez"])
    for idx, o in enumerate(r["ornek_turlar"][:3], 1):
        print("  Tur", idx, "taslak:", repr(o["taslak"]), "->", o["ozet"])
    print("Sınır:", r["sinir"])
    print("Kanıt:", ai_lab.kanit_yaz("ai-temel-27-run", {"kaynak": "gercek", "kabul": False, "ders": "ai-temel-27", "deney": r}))
