# -*- coding: utf-8 -*-
"""MITRE ATT&CK Enterprise STIX verisinden Purple Team yolunun sade özetini üretir.

Kaynak, MITRE'nin resmi deposundaki sürüm sabit dosyadır (.deps/attack/enterprise-attack-<sürüm>.json):
https://github.com/mitre-attack/attack-stix-data. Özet, derslerin çalışma klasörüne kopyalanan
tracks/purple/veri/attack.json dosyasıdır.

    curl -L -o .deps/attack/enterprise-attack-19.2.json \\
        https://raw.githubusercontent.com/mitre-attack/attack-stix-data/master/enterprise-attack/enterprise-attack-19.2.json
    python tools/attack_ozet.py

© The MITRE Corporation. ATT&CK® MITRE'nin tescilli markasıdır; veri MITRE'nin kullanım koşullarıyla
(https://attack.mitre.org/resources/legal-and-branding/terms-of-use/) atıf verilerek kullanılır.
"""
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SURUM = "19.2"
OZET = "dc1639caa5501d720e280cf1cbd8fbe009884a0c9b3e6e9ed9d0c25166c3d8f4"
KAYNAK = os.path.join(ROOT, ".deps", "attack", f"enterprise-attack-{SURUM}.json")
HEDEF = os.path.join(ROOT, "tracks", "purple", "veri", "attack.json")


def kimlik(o):
    return next((r["external_id"] for r in o.get("external_references", []) if r.get("source_name") == "mitre-attack"), None)


def main():
    with open(KAYNAK, "rb") as f:
        ham = f.read()
    if hashlib.sha256(ham).hexdigest() != OZET:
        sys.exit(f"{KAYNAK} beklenen sürüm değil (sha256 uyuşmuyor)")
    nesneler = json.loads(ham)["objects"]
    stix = {o["id"]: o for o in nesneler}

    matris = next(o for o in nesneler if o["type"] == "x-mitre-matrix")
    taktikler = [{"id": kimlik(stix[r]), "kisa": stix[r]["x_mitre_shortname"], "ad": stix[r]["name"]}
                 for r in matris["tactic_refs"]]

    yerine = {}
    for o in nesneler:
        if o["type"] == "relationship" and o["relationship_type"] == "revoked-by":
            eski, yeni = stix.get(o["source_ref"]), stix.get(o["target_ref"])
            if eski and yeni and eski["type"] == "attack-pattern":
                yerine[kimlik(eski)] = kimlik(yeni)

    teknikler, emekli, kullanim_disi = [], {}, []
    for o in nesneler:
        if o["type"] != "attack-pattern":
            continue
        tid = kimlik(o)
        if o.get("revoked"):
            if tid in yerine:
                emekli[tid] = yerine[tid]
            continue
        if o.get("x_mitre_deprecated"):
            kullanim_disi.append(tid)
            continue
        teknikler.append({"id": tid, "ad": o["name"],
                          "taktikler": [p["phase_name"] for p in o.get("kill_chain_phases", [])
                                        if p.get("kill_chain_name") == "mitre-attack"],
                          "platformlar": sorted(o.get("x_mitre_platforms", []))})
    teknikler.sort(key=lambda t: [int(p) if p.isdigit() else p for p in t["id"][1:].split(".")])
    ozet = {"kaynak": f"MITRE ATT&CK Enterprise {SURUM} (attack-stix-data), © The MITRE Corporation",
            "surum": SURUM, "taktikler": taktikler, "teknikler": teknikler,
            "emekli": dict(sorted(emekli.items())), "kullanim_disi": sorted(kullanim_disi)}
    os.makedirs(os.path.dirname(HEDEF), exist_ok=True)
    with open(HEDEF, "w", encoding="utf-8", newline="\n") as f:
        json.dump(ozet, f, ensure_ascii=False, indent=0, separators=(",", ":"))
        f.write("\n")
    print(f"{len(taktikler)} taktik, {len(teknikler)} teknik, {len(emekli)} emekli, {len(kullanim_disi)} kullanım dışı → {HEDEF}")


if __name__ == "__main__":
    main()
