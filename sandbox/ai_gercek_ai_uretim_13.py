# -*- coding: utf-8 -*-
"""ai-uretim-13 gerçek deney: öğrencinin stride, broadcasting ve einops planlayıcısı SmolLM2'nin gerçek dikkat
tensörleri üzerinde torch'un .stride(), storage_offset(), is_contiguous(), broadcast_shapes/broadcast_to ve
einops.rearrange sonuçlarıyla karşılaştırılır; sessiz broadcasting hatası gerçek bir kayıp hesabında gösterilir."""
import random
import ai_lab
from sandbox import ai_uretim_ortak as O

AYAR = {"metin": "The analyst exported the firewall logs and compared them with the badge records.", "katman": 3, "seed": 13, "deneme": 40}


def _gercek_tensorler(torch):
    tok, model, bilgi = O.smol()
    ids = tok(AYAR["metin"], return_tensors="pt").input_ids
    T = ids.shape[1]
    with torch.no_grad():
        hs = model(ids, output_hidden_states=True).hidden_states[AYAR["katman"]]
        L = model.model.layers[AYAR["katman"]]
        x = L.input_layernorm(hs)
        q = L.self_attn.q_proj(x).view(1, T, model.config.num_attention_heads, -1)          # HF Llama: view (b, t, h, d)
        cos, _ = model.model.rotary_emb(x, torch.arange(T).unsqueeze(0))
        logits = model(ids).logits[0]
    return tok, model, bilgi, ids, T, hs, q, cos, logits


class _Kanarya:
    """Zararsız yük: pickle açılırken geçici klasörde bir kanarya dosyası oluşturur (kod çalıştırmanın kanıtı)."""
    def __init__(self, yol):
        self.yol = yol

    def __reduce__(self):
        return (open, (self.yol, "w"))


def _serilestirme(torch, model):
    """Tensör dosya biçimleri: pickle tabanlı torch.save kod çalıştırabilir; safetensors yalnız başlık + ham bayt içerir."""
    import json, os, struct, tempfile
    from safetensors.torch import load_file, save_file
    W = model.model.layers[0].self_attn.q_proj.weight.detach().clone()
    with tempfile.TemporaryDirectory() as d:
        kanarya = os.path.join(d, "KANARYA_kod_calisti.txt")
        zararli = os.path.join(d, "model.pt")
        torch.save({"agirlik": W, "yuk": _Kanarya(kanarya)}, zararli)       # gerçek torch.save biçimi (zip + pickle)
        engellendi = False
        try:
            torch.load(zararli, weights_only=True)
        except Exception:  # noqa: BLE001  (UnpicklingError)
            engellendi = True
        guvenli_sonra = os.path.exists(kanarya)
        yuklenen_pt = torch.load(zararli, weights_only=False)
        calisti = os.path.exists(kanarya)
        if hasattr(yuklenen_pt.get("yuk"), "close"):
            yuklenen_pt["yuk"].close()                                       # yükün açtığı dosya tutamacı
        st = os.path.join(d, "model.safetensors")
        save_file({"q_proj": W.contiguous()}, st)
        with open(st, "rb") as f:
            n = struct.unpack("<Q", f.read(8))[0]
            baslik = json.loads(f.read(n))
        yuklenen = load_file(st)["q_proj"]
        bozuk = os.path.join(d, "bozuk.safetensors")
        b2 = dict(baslik)
        b2["q_proj"] = dict(baslik["q_proj"], shape=[576, 576, 4])          # veriden büyük şekil
        hb = json.dumps(b2).encode()
        with open(st, "rb") as f:
            f.read(8 + n)
            veri = f.read()
        with open(bozuk, "wb") as f:
            f.write(struct.pack("<Q", len(hb)) + hb + veri)
        try:
            load_file(bozuk)
            bozuk_reddedildi = False
        except Exception:  # noqa: BLE001
            bozuk_reddedildi = True
    t = baslik["q_proj"]
    return {"weights_only_engelledi": engellendi and not guvenli_sonra, "weights_only_false_kod_calisti": calisti,
            "safetensors_baslik": {"dtype": t["dtype"], "shape": t["shape"], "data_offsets": t["data_offsets"]},
            "baslik_bayt_tutarli": t["data_offsets"][1] - t["data_offsets"][0] == W.numel() * W.element_size(),
            "safetensors_ayni": torch.equal(yuklenen, W), "bozuk_baslik_reddedildi": bozuk_reddedildi}


def deney(stride_ofset_ve_devrik, broadcast_boyut_hesapla, einops_rearrange_plan):
    torch = O.torch_al()
    try:
        import einops
    except ImportError as e:
        raise ai_lab.GercekLabYok("einops kurulu değil") from e
    tok, model, bilgi, ids, T, hs, q, cos, logits = _gercek_tensorler(torch)
    rnd = random.Random(AYAR["seed"])

    # 1) Stride, ofset ve devrik: gerçek tensörler ve gerçek ağırlık şekilleri
    tensorler = {"q (b,t,h,d)": q, "gizli (b,t,c)": hs, "gate_proj": model.model.layers[0].mlp.gate_proj.weight.detach(),
                 "q_bas (h,d,c)": model.model.layers[0].self_attn.q_proj.weight.detach().view(9, 64, 576)}
    stride_hata, ornek = [], None
    for ad, t in tensorler.items():
        t = t.contiguous()
        for _ in range(AYAR["deneme"] // len(tensorler)):
            idx = [rnd.randrange(s) for s in t.shape]
            a, b = rnd.sample(range(t.dim()), 2) if t.dim() > 1 else (0, 0)
            o = stride_ofset_ve_devrik(list(t.shape), idx, a, b)
            tt = t.transpose(a, b)
            beklenen = {"orijinal_strides": list(t.stride()), "orijinal_ofset": t[tuple(idx)].storage_offset() - t.storage_offset(),
                        "devrik_boyutlar": list(tt.shape), "devrik_strides": list(tt.stride()), "devrik_contiguous_mu": tt.is_contiguous()}
            for k, v in beklenen.items():
                if o[k] != v:
                    stride_hata.append({"tensor": ad, "anahtar": k, "ogrenci": o[k], "torch": v})
            if ad == "q (b,t,h,d)" and ornek is None:
                o2 = stride_ofset_ve_devrik(list(t.shape), [0, 0, 0, 0], 1, 2)
                ornek = {"q_sekil": list(t.shape), "q_stride": o2["orijinal_strides"], "transpose_1_2_stride": o2["devrik_strides"],
                         "contiguous": o2["devrik_contiguous_mu"], "torch_contiguous": t.transpose(1, 2).is_contiguous()}

    # 2) Broadcasting: modelin kendi içindeki gerçek şekil çiftleri
    ciftler = {"rmsnorm agirlik * gizli": (list(model.model.norm.weight.shape), list(hs.shape)),
               "dikkat skoru + maske": ([1, 9, T, T], [1, 1, T, T]), "rope cos * q (b,h,t,d)": ([1, 1, T, 64], [1, 9, T, 64]),
               "hatali: tahmin (N,) - hedef (N,1)": ([T - 1], [T - 1, 1]), "uyumsuz: q (t,576) + k (t,192)": ([T, 576], [T, 192])}
    bc_hata, bc_tablo = [], {}
    for ad, (sa, sb) in ciftler.items():
        o = broadcast_boyut_hesapla(list(sa), list(sb))
        try:
            hedef = list(torch.broadcast_shapes(tuple(sa), tuple(sb)))
            st_a = list(torch.empty(sa).broadcast_to(hedef).stride())
            st_b = list(torch.empty(sb).broadcast_to(hedef).stride())
            ref = {"uyumlu_mu": True, "cikti_sekli": hedef, "genisletilmis_stride_a": st_a, "genisletilmis_stride_b": st_b}
        except RuntimeError:
            ref = {"uyumlu_mu": False, "cikti_sekli": [], "genisletilmis_stride_a": [], "genisletilmis_stride_b": []}
        if o != ref:
            bc_hata.append({"cift": ad, "ogrenci": o, "torch": ref})
        bc_tablo[ad] = o["cikti_sekli"]
    # sessiz hata: gerçek token log-olasılıkları (N,) ile hedef (N,1) farkı N×N'e yayılır
    lp = torch.log_softmax(logits[:-1].double(), -1).gather(1, ids[0, 1:].unsqueeze(1)).squeeze(1)
    hedef = lp.detach().clone().unsqueeze(1) + 0.1
    dogru = float(((lp - hedef.squeeze(1)) ** 2).mean())
    sessiz = float(((lp - hedef) ** 2).mean())

    # 3) einops: gerçek q üzerinde HF'nin kendi yeniden düzenlemeleri
    desenler = {"b t h d -> b h t d": q, "b h t d -> b t (h d)": q.transpose(1, 2).contiguous(), "b t h d -> b t (h d)": q,
                "b t h d -> (b t) h d": q}
    ein_hata, ein_tablo = [], {}
    for desen, x in desenler.items():
        o = einops_rearrange_plan(desen, list(x.shape))
        y = einops.rearrange(x, desen)
        perm_ok = torch.equal(x.permute(o["permutasyon"]).reshape(o["cikti_sekli"]), y)
        ayni_bellek = y.untyped_storage().data_ptr() == x.untyped_storage().data_ptr()
        gorunum = ayni_bellek and y.is_contiguous()
        if list(y.shape) != o["cikti_sekli"] or not perm_ok or o["gorunum_yeterli"] != gorunum:
            ein_hata.append({"desen": desen, "ogrenci": o, "torch_sekil": list(y.shape), "perm_ok": perm_ok, "gorunum": gorunum})
        ein_tablo[desen] = {"sekil": o["cikti_sekli"], "kopya": not ayni_bellek, "contiguous": y.is_contiguous()}
    hf_ayni = torch.equal(einops.rearrange(q, "b t h d -> b h t d"), q.transpose(1, 2))
    S = _serilestirme(torch, model)
    return {
        "model": {k2: bilgi[k2] for k2 in ("model", "revizyon", "agirlik_sha256", "parametre")}, "surumler": O.surumler("einops"),
        "stride_deneme": AYAR["deneme"], "stride_hatalari": stride_hata[:5], "stride_ayni": not stride_hata, "q_ornek": ornek,
        "broadcast_hatalari": bc_hata, "broadcast_ayni": not bc_hata, "broadcast_tablo": bc_tablo,
        "sessiz_hata_dogru_kayip": dogru, "sessiz_hata_yayilmis_kayip": sessiz, "sessiz_hata_kat": sessiz / dogru,
        "einops_hatalari": ein_hata, "einops_ayni": not ein_hata, "einops_tablo": ein_tablo, "hf_transpose_ayni": hf_ayni,
        "serilestirme": S, "serilestirme_guvenligi": S["weights_only_engelledi"] and S["weights_only_false_kod_calisti"] and S["safetensors_ayni"]
                                                  and S["baslik_bayt_tutarli"] and S["bozuk_baslik_reddedildi"],
        "olcum": (f"SmolLM2 gerçek tensörlerinde {AYAR['deneme']} stride/ofset/devrik denemesi torch ile {'aynı' if not stride_hata else 'farklı'}; "
                  f"q {ornek['q_sekil']} stride {ornek['q_stride']}, transpose(1,2) contiguous {ornek['torch_contiguous']}. "
                  f"{len(ciftler)} broadcasting çifti torch.broadcast_shapes ile {'aynı' if not bc_hata else 'farklı'}. (N,) − (N,1) hatası "
                  f"kaybı {dogru:.4f} yerine {sessiz:.4f} yapıyor ({sessiz / dogru:.0f}×, hata yok). {len(desenler)} einops deseni "
                  f"einops.rearrange ile {'aynı' if not ein_hata else 'farklı'}. Dosya biçimi: zararsız kanarya yüklü pickle torch.load(weights_only=False) "
                  f"ile {'kod çalıştırdı' if S['weights_only_false_kod_calisti'] else 'kod çalıştırmadı'}, weights_only=True ile "
                  f"{'engellendi' if S['weights_only_engelledi'] else 'engellenmedi'}; safetensors başlığı {S['safetensors_baslik']} ve veriden büyük "
                  f"şekilli bozuk başlık {'reddedildi' if S['bozuk_baslik_reddedildi'] else 'kabul edildi'}."),
        "sinir": ("Karşılaştırma CPU'da, contiguous ve devrik görünümlerle sınırlıdır; as_strided, negatif adım ve bellek hizalaması "
                  "ölçülmez. einops'ta yalnız sağ tarafta birleştirme olan desenler denenir."),
    }


def goster(stride_ofset_ve_devrik, broadcast_boyut_hesapla, einops_rearrange_plan):
    r = deney(stride_ofset_ve_devrik, broadcast_boyut_hesapla, einops_rearrange_plan)
    print("Stride/ofset/devrik torch ile aynı:", r["stride_ayni"], "| q örneği:", r["q_ornek"])
    print("Broadcasting torch ile aynı:", r["broadcast_ayni"], r["broadcast_tablo"])
    print("Sessiz broadcasting hatası: doğru kayıp %.4f | (N,)−(N,1) ile %.4f" % (r["sessiz_hata_dogru_kayip"], r["sessiz_hata_yayilmis_kayip"]))
    print("einops ile aynı:", r["einops_ayni"], r["einops_tablo"])
    print("Serileştirme:", r["serilestirme"])
    print("Sınır:", r["sinir"])
    print("Kanıt:", O.kanit("ai-uretim-13", "run", r))
