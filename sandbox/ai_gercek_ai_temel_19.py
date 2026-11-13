# -*- coding: utf-8 -*-
"""ai-temel-19 gerçek deneyi: yerel HF önbelleğindeki gerçek SmolLM2 dosyalarının bütünlüğü.

Beklenen değerler Hub'ın kendi kaydıdır: 2026-10-28'de `HfApi().get_paths_info(REPO, ..., revision=REVIZYON)` ile
okunan git blob kimlikleri, boyutlar ve LFS sha256 oid'i. Ders sırasında ağ kullanılmaz; yalnız yerel dosyalar okunur.
Kurcalama denemeleri geçici klasördeki kopyalarda yapılır ve sonunda silinir; önbellekteki dosyalara dokunulmaz.
"""
import hashlib
import json
import math
import os
import shutil
import struct
import tempfile

import ai_lab

REPO = "HuggingFaceTB/SmolLM2-135M"
REVIZYON = "93efa2f097d58c2a74874c7e644dbc9b0cee75a2"
# Kaynak: HfApi().get_paths_info (Hub API), 2026-10-28. lfs_sha256 yalnız LFS ile saklanan dosyada vardır.
MANIFEST = {
    "config.json": {"boyut": 704, "git_blob": "ccf3dac2f33905d152adbdf3886b5e38a4eb7579", "lfs_sha256": None},
    "generation_config.json": {"boyut": 111, "git_blob": "0fce861c328ff24830f3037d91ce773254447bf7", "lfs_sha256": None},
    "merges.txt": {"boyut": 466391, "git_blob": "69503b13f727ba3812b6803e97442a6de05ef5eb", "lfs_sha256": None},
    "model.safetensors": {"boyut": 269060552, "git_blob": "ed736e4e5f39dd99c5d435bf84c0d8c222839b1b",
                          "lfs_sha256": "80521b40281d6ce74e35c9282c22539e75aa0ac8578892b2a59955ef78d55da1"},
    "special_tokens_map.json": {"boyut": 831, "git_blob": "f6652f246cb895ca1edfb16d10b57917b266e335", "lfs_sha256": None},
    "tokenizer.json": {"boyut": 2104556, "git_blob": "f922b1797f0c88e71addc8393787831f2477a4bd", "lfs_sha256": None},
    "tokenizer_config.json": {"boyut": 3658, "git_blob": "d45192775d58298087a1fedf5967fe5b63b091ab", "lfs_sha256": None},
    "vocab.json": {"boyut": 800662, "git_blob": "0ad5ecc2035b7031b88afb544ee95e2d49baa484", "lfs_sha256": None},
}
DTYPE_BOYU = {"F64": 8, "F32": 4, "F16": 2, "BF16": 2, "I64": 8, "I32": 4, "I16": 2, "I8": 1, "U8": 1, "BOOL": 1}
BASLIK_SINIRI = 1_000_000


def snapshot_dizini():
    try:
        from huggingface_hub import hf_hub_download
        yol = hf_hub_download(REPO, "model.safetensors", revision=REVIZYON, local_files_only=True)
    except Exception as e:
        raise ai_lab.GercekLabYok(f"{REPO}@{REVIZYON[:10]} yerel önbellekte yok ({type(e).__name__}). "
                                  "İndirme: python tools/ai_gercek_kur.py --model-indir") from e
    return os.path.dirname(yol)


def lfs_isaretci(oid, boyut):
    return f"version https://git-lfs.github.com/spec/v1\noid sha256:{oid}\nsize {boyut}\n".encode()


def git_blob_bayt(icerik):
    return hashlib.sha1(b"blob %d\x00" % len(icerik) + icerik).hexdigest()


def referans_ozetler(yol, *, blob_basligi=True):
    if not isinstance(yol, str) or not os.path.isfile(yol):
        raise ValueError("yol")
    boyut = os.path.getsize(yol)
    s256 = hashlib.sha256()
    s1 = hashlib.sha1(b"blob %d\x00" % boyut) if blob_basligi else hashlib.sha1()
    with open(yol, "rb") as f:
        for parca in iter(lambda: f.read(1 << 20), b""):
            s256.update(parca)
            s1.update(parca)
    return {"boyut": boyut, "sha256": s256.hexdigest(), "git_blob": s1.hexdigest()}


def referans_baslik(yol, *, kapsama=True, endian="<", parametre="eleman"):
    if not isinstance(yol, str) or not os.path.isfile(yol):
        raise ValueError("yol")
    toplam = os.path.getsize(yol)
    with open(yol, "rb") as f:
        bas = f.read(8)
        if len(bas) < 8:
            raise ValueError("8 bayttan kısa")
        n = struct.unpack(endian + "Q", bas)[0]
        if n > BASLIK_SINIRI or 8 + n > toplam:
            raise ValueError("başlık boyu")
        ham = f.read(n)
    try:
        def nesne(ciftler):
            out={}
            for key,value in ciftler:
                if key in out: raise ValueError("yinelenen anahtar")
                out[key]=value
            return out
        metin=ham.decode("utf-8")
        if not metin.startswith("{") or not metin.rstrip(" ").endswith("}"):
            raise ValueError("başlık dolgu/başlangıç")
        baslik = json.loads(metin,object_pairs_hook=nesne)
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise ValueError("başlık JSON değil") from e
    if not isinstance(baslik, dict):
        raise ValueError("başlık nesne değil")
    meta = baslik.pop("__metadata__", {})
    if not isinstance(meta, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in meta.items()):
        raise ValueError("metadata")
    tensorler = []
    for ad, t in baslik.items():
        if not isinstance(t, dict) or set(t) != {"dtype", "shape", "data_offsets"} or not isinstance(t["dtype"],str) or t["dtype"] not in DTYPE_BOYU:
            raise ValueError(f"{ad}: alanlar/dtype")
        sh, off = t["shape"], t["data_offsets"]
        if not isinstance(sh, list) or any(type(x) is not int or x < 0 for x in sh):
            raise ValueError(f"{ad}: shape")
        if not isinstance(off, list) or len(off) != 2 or any(type(x) is not int for x in off) or not 0 <= off[0] <= off[1]:
            raise ValueError(f"{ad}: data_offsets")
        if off[1] - off[0] != math.prod(sh) * DTYPE_BOYU[t["dtype"]]:
            raise ValueError(f"{ad}: boyut tutmuyor")
        tensorler.append({"ad": ad, "dtype": t["dtype"], "shape": list(sh), "bas": off[0], "son": off[1]})
    tensorler.sort(key=lambda t: (t["bas"], t["son"], t["ad"]))
    if kapsama:
        konum = 0
        for t in tensorler:
            if t["bas"] != konum:
                raise ValueError(f"{t['ad']}: boşluk/çakışma")
            konum = t["son"]
        if konum != toplam - 8 - n:
            raise ValueError("tampon uzunluğu tutmuyor")
    say = (lambda t: math.prod(t["shape"])) if parametre == "eleman" else (lambda t: t["son"] - t["bas"])
    return {"metadata": meta, "tensorler": tensorler, "parametre": sum(say(t) for t in tensorler)}


def _dene(fn, *a):
    try:
        fn(*a)
        return "geçti"
    except ValueError as e:
        return f"ValueError: {str(e)[:80]}"


def deney(ozetler, baslik):
    """Gerçek dosyalar: Hub manifestiyle karşılaştırma, başlık/parametre denetimi ve kopyalarda kurcalama."""
    snap = snapshot_dizini()
    dosyalar = []
    for ad in sorted(os.listdir(snap)):
        o = ozetler(os.path.join(snap, ad))
        m = MANIFEST.get(ad)
        k = {"ad": ad, "ozet": o, "manifestte": m is not None}
        if m:
            k["boyut_tutuyor"] = o["boyut"] == m["boyut"]
            if m["lfs_sha256"]:
                k["lfs_sha256_tutuyor"] = o["sha256"] == m["lfs_sha256"]
                k["isaretci_blob_tutuyor"] = git_blob_bayt(lfs_isaretci(o["sha256"], o["boyut"])) == m["git_blob"]
            else:
                k["git_blob_tutuyor"] = o["git_blob"] == m["git_blob"]
        dosyalar.append(k)
    model_yolu = os.path.join(snap, "model.safetensors")
    b = baslik(model_yolu)
    _, model, bilgi = ai_lab.dil_modeli()
    dtypeler = {}
    for t in b["tensorler"]:
        dtypeler[t["dtype"]] = dtypeler.get(t["dtype"], 0) + 1
    with open(model_yolu, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
    kurcalama = {}
    gecici = tempfile.mkdtemp(prefix="pafta_ai19_")
    try:
        kopya = os.path.join(gecici, "veri_bayti.safetensors")
        shutil.copyfile(model_yolu, kopya)
        with open(kopya, "r+b") as f:
            f.seek(8 + n + 1000)
            x = f.read(1)
            f.seek(8 + n + 1000)
            f.write(bytes([x[0] ^ 0x01]))
        kurcalama["veri_bayti"] = {"baslik": _dene(baslik, kopya),
                                   "sha256_tutuyor": ozetler(kopya)["sha256"] == MANIFEST["model.safetensors"]["lfs_sha256"]}
        os.remove(kopya)
        kesik = os.path.join(gecici, "kesik.safetensors")
        with open(model_yolu, "rb") as f, open(kesik, "wb") as g:
            g.write(f.read(8 + n + 4096))
        kurcalama["kesik"] = {"baslik": _dene(baslik, kesik),
                              "sha256_tutuyor": ozetler(kesik)["sha256"] == MANIFEST["model.safetensors"]["lfs_sha256"]}
        boy = os.path.join(gecici, "baslik_boyu.safetensors")
        with open(kesik, "rb") as f:
            ham = f.read()
        with open(boy, "wb") as g:
            g.write(struct.pack("<Q", n + 5) + ham[8:])
        kurcalama["baslik_boyu"] = {"baslik": _dene(baslik, boy),
                                    "sha256_tutuyor": ozetler(boy)["sha256"] == MANIFEST["model.safetensors"]["lfs_sha256"]}
    finally:
        shutil.rmtree(gecici, ignore_errors=True)
    return {"repo": REPO, "revizyon": REVIZYON, "snapshot_revizyonu": os.path.basename(snap), "dosyalar": dosyalar,
            "baslik": {"metadata": b["metadata"], "tensor_sayisi": len(b["tensorler"]), "dtypeler": dtypeler,
                       "parametre": b["parametre"], "baslik_bayt": n},
            "model_parametresi": sum(p.numel() for p in model.parameters()), "model_bilgisi": bilgi,
            "kurcalama": kurcalama, "gecici_silindi": not os.path.exists(gecici)}


def goster(ozetler, baslik):
    """Çalıştır düğmesi: gerçek önbellek dosyalarında bütünlük raporu."""
    r = deney(ozetler, baslik)
    print(f"{r['repo']} @ {r['revizyon'][:12]} · snapshot klasörü {r['snapshot_revizyonu'][:12]}")
    print("Dosya                     boyut        Hub ile karşılaştırma")
    for k in r["dosyalar"]:
        if not k["manifestte"]:
            durum = "manifestte yok"
        elif "lfs_sha256_tutuyor" in k:
            durum = f"LFS sha256 {'✓' if k['lfs_sha256_tutuyor'] else '✗'} · işaretçinin git blob kimliği {'✓' if k['isaretci_blob_tutuyor'] else '✗'}"
        else:
            durum = f"git blob {'✓' if k['git_blob_tutuyor'] else '✗'}"
        print(f"  {k['ad']:24} {k['ozet']['boyut']:>11,}  {durum}")
    bb = r["baslik"]
    print(f"\nsafetensors başlığı: {bb['baslik_bayt']:,} bayt, {bb['tensor_sayisi']} tensör, {bb['dtypeler']}, metadata {bb['metadata']}")
    print(f"Başlıktan sayılan parametre {bb['parametre']:,} · transformers modelinin parametresi {r['model_parametresi']:,}")
    print("\nKurcalanmış kopyalar (geçici klasörde):")
    for ad, s in r["kurcalama"].items():
        print(f"  {ad:12} başlık denetimi: {s['baslik']:<45} sha256 Hub'la {'aynı' if s['sha256_tutuyor'] else 'FARKLI'}")
    print("\nKanıt:", ai_lab.kanit_yaz("temel-dosya-butunlugu-calistir", {
        "kaynak": "gercek", "kabul": False, "ders": "ai-temel-19", "model_bilgisi": r.pop("model_bilgisi"), "deney": r}))
