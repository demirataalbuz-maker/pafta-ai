"""Paylaşımlı GPU bellek kalıntısı ve tensör sıfırlama (scrubbing): tek süreçli çok kiracılı bir çıkarım sunucusunda
PyTorch'un önbellekli GPU ayırıcısı serbest bırakılan bloğu sıfırlamadan bir sonraki isteğe verir. Kurbanın gerçek
SmolLM2-135M gömme aktivasyonları saldırganın `torch.empty` ile aldığı tensörden okunur ve token token kurtarılır."""
import copy, importlib.metadata, math, random, secrets
import ai_lab

AYAR = {
    "seed": 63,
    "batch_token": 512,          # ~1,2 MB: büyük blok havuzu, aynı boyuttaki istek aynı segmenti alır
    "aday_sozluk": 1000,         # öğrencinin kurtarma işlevine verilen aday token sayısı (gizli tokenlar dahil)
    "tol": 1e-6,
}
SIR = "The vault PIN is 4831 and the backup phrase is copper lantern."
DOLGU = " Routine log entry: service restarted, disk usage normal, no alerts were raised during the night shift."


def _sayi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)


def referans_enerji(tampon, beklenen_sifir_tol):
    if not isinstance(tampon, list) or not tampon or not all(_sayi(v) for v in tampon):
        raise ValueError("tampon")
    if not _sayi(beklenen_sifir_tol) or beklenen_sifir_tol < 0:
        raise ValueError("tol")
    n = len(tampon)
    dolu = sum(1 for x in tampon if abs(x) > beklenen_sifir_tol)
    enerji = sum(x * x for x in tampon) / n
    return {
        "doluluk_orani": dolu / n,
        "ortalama_enerji": enerji,
        "sizinti_var": dolu > 0,
    }


def _norm(v):
    return math.sqrt(sum(x * x for x in v))


def referans_kurtarma(kalinti_vektor, sozluk_gommeleri):
    if not isinstance(kalinti_vektor, list) or not kalinti_vektor or not all(_sayi(v) for v in kalinti_vektor):
        raise ValueError("vektör")
    nk = _norm(kalinti_vektor)
    if nk == 0:
        raise ValueError("sıfır vektör")
    if not isinstance(sozluk_gommeleri, dict) or not sozluk_gommeleri:
        raise ValueError("sözlük")
    d = len(kalinti_vektor)
    skorlar = {}
    for tok, emb in sozluk_gommeleri.items():
        if not isinstance(tok, str) or not tok or not isinstance(emb, list) or len(emb) != d or not all(_sayi(v) for v in emb):
            raise ValueError("eleman")
        ne = _norm(emb)
        if ne == 0:
            raise ValueError("sıfır gömme")
        skorlar[tok] = sum(a * b for a, b in zip(kalinti_vektor, emb)) / (nk * ne)
    en_iyi = min(skorlar, key=lambda k: (-skorlar[k], k))
    en_kos = skorlar[en_iyi]
    return {
        "kurtarilan_token": en_iyi,
        "kosinus_benzerligi": en_kos,
        "guvenli_eslesme": en_kos >= 0.85,
    }


def referans_temizle(tampon_listesi):
    if not isinstance(tampon_listesi, list) or not tampon_listesi:
        raise ValueError("liste")
    for t in tampon_listesi:
        if not isinstance(t, list) or not t or not all(_sayi(v) for v in t):
            raise ValueError("tampon")
    temiz = [[0.0 for _ in t] for t in tampon_listesi]
    silinen = sum(1 for t in tampon_listesi for x in t if x != 0)
    kalan = sum(x * x for t in temiz for x in t)
    return {
        "temiz_tamponlar": temiz,
        "temizlenen_eleman_sayisi": silinen,
        "kalan_enerji": kalan,
    }


def _yakin(a, b, tol=1e-9):
    if isinstance(a, dict):
        return isinstance(b, dict) and set(a) == set(b) and all(_yakin(a[k], b[k], tol) for k in a)
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(_yakin(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, (bool, str)) or a is None:
        return type(a) is type(b) and a == b
    return _sayi(a) and _sayi(b) and abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def deney(enerji_fn, kurtarma_fn, temizle_fn):
    try:
        import torch
    except ImportError as e:
        raise ai_lab.GercekLabYok(str(e)) from e
    tok, model, bilgi = ai_lab.dil_modeli()
    cihaz = ai_lab.torch_cihazi()
    if cihaz != "cuda":
        raise ai_lab.GercekLabYok("bu deney GPU önbellekli ayırıcısını ölçer; CUDA/ROCm GPU gerekli")
    model.to(cihaz)
    E = model.get_input_embeddings().weight.detach()
    d = int(E.shape[1])
    gizli = tok(SIR, add_special_tokens=False)["input_ids"]
    batch = (gizli + tok(DOLGU * 60, add_special_tokens=False)["input_ids"])[:AYAR["batch_token"]]
    n = len(gizli)
    En = torch.nn.functional.normalize(E.double(), dim=1)

    def kurban_istegi(temizleyici):
        """Kurban: batch'in gömme aktivasyonunu GPU tamponunda hesaplar, işi bitince tamponu serbest bırakır."""
        torch.cuda.synchronize()
        torch.cuda.empty_cache()
        v = torch.empty(len(batch), d, device=cihaz)
        torch.index_select(E, 0, torch.tensor(batch, device=cihaz), out=v)
        torch.cuda.synchronize()
        if temizleyici is not None:
            v.copy_(torch.tensor(temizleyici(v.double().tolist()), dtype=v.dtype, device=cihaz))
            torch.cuda.synchronize()
        adres = v.data_ptr()
        del v
        return adres

    def saldirgan_istegi():
        """Saldırgan: aynı süreçte, aynı boyutta tensör ister ve içini okur (torch.empty sıfırlamaz)."""
        k = torch.empty(len(batch), d, device=cihaz)
        satirlar = k[:n].double()
        tam = (torch.nn.functional.normalize(satirlar, dim=1) @ En.T).argmax(1).tolist() if float(satirlar.abs().sum()) > 0 else []
        return k.data_ptr(), satirlar.tolist(), tam

    # 1 · Temizleme yok
    a1 = kurban_istegi(None)
    b1, kalinti, tam1 = saldirgan_istegi()
    gen = torch.Generator().manual_seed(AYAR["seed"])
    adaylar = list(dict.fromkeys(gizli + torch.randint(0, E.shape[0], (AYAR["aday_sozluk"],), generator=gen).tolist()))[:AYAR["aday_sozluk"]]
    sozluk = {f"{i}:{tok.convert_ids_to_tokens(i)}": E[i].double().tolist() for i in adaylar}
    enerji_ayni = kurtarma_ayni = True
    kurtarilan = []
    for v in kalinti:
        r_e = referans_enerji(v, AYAR["tol"])
        enerji_ayni = enerji_ayni and _yakin(enerji_fn(list(v), AYAR["tol"]), r_e)
        r_k = referans_kurtarma(v, sozluk)
        kurtarma_ayni = kurtarma_ayni and _yakin(kurtarma_fn(list(v), copy.deepcopy(sozluk)), r_k)
        kurtarilan.append(r_k["kurtarilan_token"])
    beklenen = [f"{i}:{tok.convert_ids_to_tokens(i)}" for i in gizli]

    # 2 · Kurban tamponu senin temizleme işlevinle sıfırlayıp serbest bırakır
    o_t_tut = {}

    def ogrenci_temizleyici(liste):
        r_t = referans_temizle(liste[:n])
        o_t = temizle_fn(copy.deepcopy(liste[:n]))
        o_t_tut.update(ayni=_yakin(o_t, r_t), silinen=r_t["temizlenen_eleman_sayisi"])
        return o_t["temiz_tamponlar"] + [[0.0] * d for _ in liste[n:]]

    a2 = kurban_istegi(ogrenci_temizleyici)
    b2, kalinti2, tam2 = saldirgan_istegi()
    sonra = referans_enerji(kalinti2[0], AYAR["tol"])
    enerji_ayni = enerji_ayni and _yakin(enerji_fn(list(kalinti2[0]), AYAR["tol"]), sonra)

    return {
        "cihaz": str(cihaz),
        "dtype": "float32 (okuma float64)",
        "model": {k: bilgi[k] for k in ("model", "revizyon", "agirlik_sha256", "parametre")},
        "surumler": {"torch": importlib.metadata.version("torch"), "transformers": importlib.metadata.version("transformers")},
        "ayarlar": AYAR,
        "tampon_bayt": len(batch) * d * 4,
        "ayni_blok_temizlemesiz": a1 == b1,
        "ayni_blok_temizlemeli": a2 == b2,
        "gizli_token_sayisi": n,
        "gizli_tokenler": beklenen,
        "kurtarilan_tokenler": kurtarilan,
        "tam_kurtarma_basarili": kurtarilan == beklenen,
        "tam_sozlukte_kurtarilan_metin": tok.decode(tam1) if tam1 else "",
        "tam_sozlukte_tam_kurtarma": tam1 == gizli,
        "kalinti_enerji_ilk_satir": referans_enerji(kalinti[0], AYAR["tol"])["ortalama_enerji"],
        "temizlik_sonrasi_sizinti": sonra["sizinti_var"],
        "temizlik_sonrasi_kurtarilan_metin": tok.decode(tam2) if tam2 else "",
        "enerji_ayni": enerji_ayni,
        "kurtarma_ayni": kurtarma_ayni,
        "temizle_ayni": bool(o_t_tut.get("ayni")),
        "olcum": (f"SmolLM2-135M gömme aktivasyonu, {len(batch)} tokenlık batch tamponu (~{len(batch) * d * 4 / 1e6:.1f} MB). Kurban tamponu "
                  f"serbest bıraktıktan sonra saldırganın torch.empty isteği aynı bloğu aldı ({a1 == b1}); temizlemesiz kalıntıdan sır "
                  f"cümlesinin {n} tokenı tam sözlükte {'birebir' if tam1 == gizli else 'kısmen'} kurtarıldı: {tok.decode(tam1)!r}. Kurban tamponu "
                  f"senin temizleme işlevinle sıfırlayınca saldırgan aynı bloğu aldı ({a2 == b2}) ama sızıntı {sonra['sizinti_var']}."),
        "sinir": ("Tek süreçli bir sunucuda PyTorch önbellekli GPU ayırıcısının blok yeniden kullanımını ölçer. Süreçler arası GPU yerel bellek "
                  "(LDS) sızıntısını (LeftoverLocals, CVE-2023-4969: AMD/Apple/Qualcomm; NVIDIA etkilenmedi), sürücü düzeyinde sayfa "
                  "eşlemesini ve ara tensörlerin (aynı veriyi taşıyan geçici kopyalar) sızıntısını kapsamaz."),
    }


def goster(enerji_fn, kurtarma_fn, temizle_fn):
    r = deney(enerji_fn, kurtarma_fn, temizle_fn)
    print("Model:", r["model"]["model"], "| cihaz:", r["cihaz"], "| tampon:", r["tampon_bayt"], "bayt | aynı blok:", r["ayni_blok_temizlemesiz"])
    print("Temizlemesiz kalıntıdan kurtarılan:", repr(r["tam_sozlukte_kurtarilan_metin"]), "| aday sözlükte tam:", r["tam_kurtarma_basarili"])
    print("Temizleme sonrası sızıntı:", r["temizlik_sonrasi_sizinti"], "| kurtarılan:", repr(r["temizlik_sonrasi_kurtarilan_metin"]))
    print("Sınır:", r["sinir"])
    print("Kanıt:", ai_lab.kanit_yaz("ai-saldiri-63-run", {"kaynak": "gercek", "kabul": False, "ders": "ai-saldiri-63", "deney": r}))
