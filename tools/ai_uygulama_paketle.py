# -*- coding: utf-8 -*-
"""Yalnız AI ve kuantum derslerinden oluşan ayrı Pafta uygulamasını bir klasöre kurar.

Kullanıcı kararı (12.11.2026): AI uygulamasına şimdilik yalnız kesin 100 olan dersler girer
(`docs/ai-gercek/ai-puanlar.json` içinde `durum: puanlandi` ve 100 puan). AI dışı yollar ve
henüz 100 olmayan dersler sonra eklenir; betik yeniden koşunca güncel listeyle yeniden kurar.

Kopyalanır: Pafta.pyw, server.py, icon.ico, engine/, web/, sandbox/, tools/, AI ve kuantum yolları
(yalnız kesin dersler; fixtures/ ve veri/ klasörleri tam), gerçek deneylerin okuduğu kurulum kayıtları.
Kopyalanmaz: AI dışı yollar, docs/, outputs/ (kayıtlar hariç), ortam klasörleri (.ai-venv, .ai-araclar,
.deps) ve git geçmişi. Kaynak klasörde hiçbir şey değişmez.

    python -X utf8 tools/ai_uygulama_paketle.py <hedef-klasör> [--sil]
"""
import json
import os
import shutil
import sys

KAYNAK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOSYALAR = ["Pafta.pyw", "server.py", "icon.ico", "requirements-detection.txt", "requirements-http.txt",
            "requirements-packets.txt"]
KLASORLER = ["engine", "web", "sandbox", "tools"]
KAYITLAR = ["outputs/ocr38-kurulum", "outputs/vlm53-kurulum"]
BELGELER = ["docs/ai-gercek-kurulum-onayi.md", "docs/ai-gercek-lab.md"]
ARACTA_YOK = ["PaftaAMDLauncher.cs", "PaftaNVIDIALauncher.cs", "amd_rocm_kur.py", "nvidia_cuda_kur.py", "amd-rocm"]
# AI grubunda olmayan ama AI eğitimi için gereken yollar; yalnız kesin 100 olan dersleri girer
EK_YOLLAR = ["python"]
# Ek yolların AI uygulamasındaki adı ve tanıtımı (tam yolun yalnız bir kısmı girdiği için)
YOL_ADLARI = {"python": {"name": "Python · AI için temel",
                         "tagline": "Sıfırdan Python: ilk satırdan dosya ve veri biçimlerine 30 ders. Her ders, konunun AI derslerinde nerede kullanıldığını gösterir."}}
YOK_SAY = shutil.ignore_patterns("__pycache__", "*.pyc")


def kesin_dersler():
    with open(os.path.join(KAYNAK, "docs", "ai-gercek", "ai-puanlar.json"), encoding="utf-8") as f:
        veri = json.load(f)
    return {d["id"] for d in veri["dersler"]
            if d.get("durum") == "puanlandi" and d.get("puan") and sum(d["puan"].values()) == 100}


def ai_yollari():
    out = []
    for ad in sorted(os.listdir(os.path.join(KAYNAK, "tracks"))):
        p = os.path.join(KAYNAK, "tracks", ad, "track.json")
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as f:
                if json.load(f).get("group") == "ai" or ad in EK_YOLLAR:
                    out.append(ad)
    return out


def yol_kopyala(ad, kesin, hedef):
    kay = os.path.join(KAYNAK, "tracks", ad)
    hed = os.path.join(hedef, "tracks", ad)
    os.makedirs(os.path.join(hed, "lessons"))
    with open(os.path.join(kay, "track.json"), encoding="utf-8") as f:
        tr = json.load(f)
    alinan = 0
    moduller = []
    for m in tr.get("modules", []):
        dersler = [l for l in m["lessons"] if l in kesin]
        if dersler:
            moduller.append(dict(m, lessons=dersler))
            alinan += len(dersler)
    tr["modules"] = moduller
    if ad in YOL_ADLARI:
        tr.update(YOL_ADLARI[ad])
    with open(os.path.join(hed, "track.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(tr, f, ensure_ascii=False, indent=2)
        f.write("\n")
    for dosya in os.listdir(os.path.join(kay, "lessons")):
        lid = "-".join(dosya.split("-")[:-1])
        for k in kesin:
            if dosya.startswith(k + "-") and dosya[len(k) + 1:len(k) + 2].isalpha():
                shutil.copy2(os.path.join(kay, "lessons", dosya), os.path.join(hed, "lessons", dosya))
                break
    for alt in os.listdir(kay):
        if alt not in ("lessons", "track.json") and os.path.isdir(os.path.join(kay, alt)):
            shutil.copytree(os.path.join(kay, alt), os.path.join(hed, alt), ignore=YOK_SAY)
    return alinan, len(os.listdir(os.path.join(hed, "lessons")))


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    hedef = os.path.abspath(sys.argv[1])
    if os.path.commonpath([hedef, KAYNAK]) == KAYNAK:
        sys.exit("Hedef, kaynak klasörün içinde olamaz.")
    if os.path.exists(hedef):
        if "--sil" not in sys.argv:
            sys.exit(f"{hedef} zaten var. Yeniden kurmak için --sil ver (ortam bağlantıları korunur).")
        for ad in os.listdir(hedef):
            p = os.path.join(hedef, ad)
            if ad in (".ai-venv", ".ai-araclar", ".deps", ".git", "Pafta.exe", "pafta-veri.txt"):
                continue
            shutil.rmtree(p) if os.path.isdir(p) and not os.path.islink(p) else os.remove(p)
    os.makedirs(hedef, exist_ok=True)
    kesin = kesin_dersler()
    for d in DOSYALAR:
        if os.path.isfile(os.path.join(KAYNAK, d)):
            shutil.copy2(os.path.join(KAYNAK, d), os.path.join(hedef, d))
    for k in KLASORLER:
        shutil.copytree(os.path.join(KAYNAK, k), os.path.join(hedef, k), ignore=YOK_SAY)
    for ad in ARACTA_YOK:  # eski depolara bağlı başlatıcılar AI uygulamasına girmez
        p = os.path.join(hedef, "tools", ad)
        if os.path.isdir(p):
            shutil.rmtree(p)
        elif os.path.isfile(p):
            os.remove(p)
    shutil.copy2(os.path.join(KAYNAK, "tools", "PaftaYerelLauncher.cs"), os.path.join(hedef, "tools", "PaftaYerelLauncher.cs"))
    os.makedirs(os.path.join(hedef, "docs"), exist_ok=True)
    for d in BELGELER:
        if os.path.isfile(os.path.join(KAYNAK, d)):
            shutil.copy2(os.path.join(KAYNAK, d), os.path.join(hedef, d))
    readme = os.path.join(KAYNAK, "docs", "ai-gercek", "PAFTA-AI-README.md")
    if os.path.isfile(readme):
        shutil.copy2(readme, os.path.join(hedef, "README.md"))
    for k in KAYITLAR:
        if os.path.isdir(os.path.join(KAYNAK, k)):
            shutil.copytree(os.path.join(KAYNAK, k), os.path.join(hedef, k), ignore=YOK_SAY)
    toplam = 0
    for ad in ai_yollari():
        modulde, dosya = yol_kopyala(ad, kesin, hedef)
        toplam += modulde
        print(f"{ad:16} {modulde:3} ders (dosya {dosya})")
    with open(os.path.join(hedef, "pafta-veri.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write("Pafta-AI\n")  # Pafta.exe ilerlemeyi %LOCALAPPDATA%\Pafta-AI altında tutar
    with open(os.path.join(hedef, ".gitignore"), "w", encoding="utf-8", newline="\n") as f:
        f.write(".ai-venv/\n.ai-araclar/\n.deps/\n__pycache__/\n*.pyc\nPafta.exe\n")
    print(f"toplam {toplam} ders → {hedef}")


if __name__ == "__main__":
    main()
