# -*- coding: utf-8 -*-
"""AI gerçek pilotlarının kurulum kontrolü ve (onaydan sonra) model indirme.

    python tools/ai_gercek_kur.py --kontrol                    # hiçbir şey kurmaz/indirmez
    .ai-venv\\Scripts\\python tools/ai_gercek_kur.py --model-indir   # SmolLM2-135M, sabit commit

Kurulumun kendisi (venv, pip) docs/ai-gercek-kurulum-onayi.md'deki komutlarla, kullanıcı onayından
sonra elle yapılır. Bu araç paket kurmaz, Ollama modeli çekmez ve hiçbir şeyi silmez.
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine.runners import ai_python  # noqa: E402
from sandbox import ai_gercek_lab as L  # noqa: E402


def kontrol():
    rapor = {"pafta_python": L.durum(), "ai_venv": ai_python(), "ai_venv_var": os.path.isfile(ai_python())}
    if rapor["ai_venv_var"]:
        kod = ("import json,sys; sys.path.insert(0, sys.argv[1]); from sandbox import ai_gercek_lab as L; "
               "d = L.durum()\ntry:\n    _, _, b = L.dil_modeli(); d['hf_model'] = {k: b[k] for k in ('model','revizyon','agirlik_sha256','parametre')}\n"
               "except Exception as e:\n    d['hf_model'] = 'YOK: ' + str(e)[:200]\nprint(json.dumps(d))")
        out = subprocess.run([ai_python(), "-X", "utf8", "-c", kod, ROOT], capture_output=True, text=True, timeout=300)
        rapor["ai_venv_durum"] = json.loads(out.stdout) if out.returncode == 0 else out.stderr[-500:]
    try:
        with L.SohbetOturumu() as o:
            rapor["sohbet_modeli"] = o.kayit["model"]
    except Exception as e:
        rapor["sohbet_modeli"] = f"YOK: {e}"
    print(json.dumps(rapor, ensure_ascii=False, indent=1))


def model_indir():
    from huggingface_hub import snapshot_download
    ad = os.environ.get("PAFTA_AI_HF_MODEL", L.HF_MODEL)
    rev = os.environ.get("PAFTA_AI_HF_REVIZYON", L.HF_REVIZYON)
    yol = snapshot_download(ad, revision=rev, allow_patterns=["*.json", "*.safetensors", "*.txt"])
    print("İndirildi:", ad, rev, "→", yol)
    _, _, bilgi = L.dil_modeli()
    print(json.dumps(bilgi, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    if "--model-indir" in sys.argv:
        model_indir()
    else:
        kontrol()
