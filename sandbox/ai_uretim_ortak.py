# -*- coding: utf-8 -*-
"""ai-uretim ve ai-temel 31–37 gerçek deneylerinin ortak yardımcıları.

Deney modülleri öğrencinin saf Python işlevlerini gerçek model ağırlıkları, gerçek araçlar ve gerçek veriyle çalıştırır
ve sonucu bağımsız bir torch / kütüphane hesabıyla karşılaştırır. Model ve veri yalnız yerel önbellekten okunur.
"""
import importlib.metadata
import math
import os

import ai_lab

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERI = os.path.join(KOK, "tracks", "ai-uretim", "veri")
MAMBA_MODEL = "state-spaces/mamba-130m-hf"
MAMBA_REVIZYON = "1e76775f628fbf1350fbe4dbb3d971ba64af25a1"
QWEN_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
QWEN_REVIZYON = "7ae557604adf67be50417f59c2c2f167def9a775"
INSTRUCT_MODEL = "HuggingFaceTB/SmolLM2-135M-Instruct"
INSTRUCT_REVIZYON = "12fd25f77366fa6b3b4b768ec3050bf629380bac"


def torch_al():
    try:
        import torch
        return torch
    except ImportError as e:
        raise ai_lab.GercekLabYok("torch kurulu değil (.ai-venv)") from e


def sayi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)


def en_buyuk_fark(a, b):
    """İç içe liste/sayı yapıları arasında en büyük mutlak fark (yapı uyuşmazsa inf)."""
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        if len(a) != len(b):
            return float("inf")
        return max((en_buyuk_fark(x, y) for x, y in zip(a, b)), default=0.0)
    if sayi(a) and sayi(b):
        return abs(float(a) - float(b))
    return float("inf")


def goreli_fark(a, b):
    """en_buyuk_fark / max(1, |b|'nin en büyük öğesi)."""
    def mx(x):
        if isinstance(x, (list, tuple)):
            return max((mx(y) for y in x), default=0.0)
        return abs(float(x)) if sayi(x) else 0.0
    return en_buyuk_fark(a, b) / max(1.0, mx(b))


def liste(t, basamak=None):
    """torch tensörü → iç içe float listesi."""
    v = t.detach().double().cpu().tolist()
    if basamak is None:
        return v

    def yuv(x):
        return [yuv(y) for y in x] if isinstance(x, list) else round(x, basamak)
    return yuv(v)


def surumler(*paketler):
    out = {}
    for p in ("torch", "transformers") + paketler:
        try:
            out[p] = importlib.metadata.version(p)
        except importlib.metadata.PackageNotFoundError:
            out[p] = None
    return out


def smol():
    """(tokenizer, model, bilgi): SmolLM2-135M, CPU float32, sabit revizyon (ai_lab.dil_modeli)."""
    return ai_lab.dil_modeli()


def hf_model(ad, revizyon=None, dtype="float32", cihaz="cpu"):
    """Yerel önbellekten causal LM ve tokenizer; indirme yapılmaz."""
    torch = torch_al()
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        t = AutoTokenizer.from_pretrained(ad, revision=revizyon, local_files_only=True)
        m = AutoModelForCausalLM.from_pretrained(ad, revision=revizyon, local_files_only=True,
                                                 dtype=getattr(torch, dtype)).to(cihaz).eval()
    except Exception as e:  # noqa: BLE001
        raise ai_lab.GercekLabYok(f"{ad} yerel önbellekte yok ya da yüklenemedi ({type(e).__name__}: {e})") from e
    return t, m


def kanit(ders, etiket, r):
    return ai_lab.kanit_yaz(f"{ders}-{etiket}", {"kaynak": "gercek", "kabul": False, "ders": ders, "deney": r})


def goster_ozet(r, alanlar=()):
    """Deney sözlüğünün okunur özeti (Çalıştır düğmesi için)."""
    print("Ölçüm:", r.get("olcum", ""))
    for a in alanlar:
        if a in r:
            print(f"  {a}: {r[a]}")
    if r.get("sinir"):
        print("Sınır:", r["sinir"])
