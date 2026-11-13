# -*- coding: utf-8 -*-
"""Madde 103: deterministik ve tamamen çevrimdışı saldırı zinciri CANLANDIRMASI.

Gerçek ağ isteği, kimlik bilgisi, uzaktan kod yürütme veya kalıcılık üretmez.
Yalnızca kurgusal web/AD kayıtlarından küçük, metin tabanlı kanıt demetleri yazar.

    python sandbox/capstone_lab.py uret --senaryo tracks/bitirme/veri/scenario.json --cikti tracks/bitirme/veri/cikti
    python sandbox/capstone_lab.py dogrula --senaryo tracks/bitirme/veri/scenario.json --cikti tracks/bitirme/veri/cikti
"""
import argparse
import csv
import hashlib
import io
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

SURUM = "pafta-capstone-1"
ZAMAN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
KIMLIK = re.compile(r"^[a-z0-9][a-z0-9._-]{2,80}$")
GIZLI_ALANLAR = {"password", "passwd", "token", "secret", "authorization", "cookie", "credential"}
DOSYALAR = (
    "web.ndjson", "ad_events.ndjson", "ad_events.xml", "normalized.jsonl",
    "kql_events.csv", "spl_events.jsonl", "timeline.json", "detections.json",
    "negative_controls.json",
)


class KanitHatasi(ValueError):
    """Eksik, bozuk, tutarsız veya güvenli olmayan canlandırma kanıtı."""


def _json_bayt(deger):
    return (json.dumps(deger, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _satir_bayt(satirlar):
    return b"".join((json.dumps(s, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
                    for s in satirlar)


def _json_oku(yol):
    try:
        with Path(yol).open(encoding="utf-8") as f:
            return json.load(f)
    except (OSError, UnicodeError, json.JSONDecodeError) as e:
        raise KanitHatasi(f"JSON okunamadı: {yol}: {e}") from e


def _gizli_alan_yok(deger, yer="senaryo"):
    if isinstance(deger, dict):
        for anahtar, alt in deger.items():
            if str(anahtar).lower() in GIZLI_ALANLAR:
                raise KanitHatasi(f"{yer}: gizli alan kabul edilmez: {anahtar}")
            _gizli_alan_yok(alt, f"{yer}.{anahtar}")
    elif isinstance(deger, list):
        for i, alt in enumerate(deger):
            _gizli_alan_yok(alt, f"{yer}[{i}]")


def _zaman_dogrula(metin, yer):
    if not isinstance(metin, str) or not ZAMAN.fullmatch(metin):
        raise KanitHatasi(f"{yer}: sabit UTC biçimi YYYY-MM-DDTHH:MM:SSZ olmalı")
    try:
        datetime.strptime(metin, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as e:
        raise KanitHatasi(f"{yer}: geçersiz UTC zamanı") from e


def senaryo_dogrula(s):
    if not isinstance(s, dict) or s.get("schema_version") != 1 or s.get("simulation") is not True:
        raise KanitHatasi("schema_version=1 ve simulation=true zorunludur")
    if not isinstance(s.get("run_id"), str) or not KIMLIK.fullmatch(s["run_id"]):
        raise KanitHatasi("run_id küçük harfli, sabit ve 3-81 karakter olmalı")
    _zaman_dogrula(s.get("utc"), "utc")
    if s.get("madde") != 103:
        raise KanitHatasi("Bu üretici yalnız madde 103 canlandırması içindir")
    env = s.get("environment")
    if not isinstance(env, dict) or not all(isinstance(env.get(k), str) and env[k] for k in
                                           ("domain", "web_host", "client_host", "dc_host", "account", "source_ip")):
        raise KanitHatasi("Kurgusal environment alanları eksik")
    adimlar = s.get("steps")
    if not isinstance(adimlar, list) or len(adimlar) < 2:
        raise KanitHatasi("En az iki canlandırma adımı gerekir")
    once = ""
    beklenen = set()
    for i, adim in enumerate(adimlar, 1):
        yer = f"steps[{i - 1}]"
        if not isinstance(adim, dict) or adim.get("order") != i:
            raise KanitHatasi(f"{yer}: order ardışık olmalı")
        if not isinstance(adim.get("id"), str) or not KIMLIK.fullmatch(adim["id"]):
            raise KanitHatasi(f"{yer}: geçersiz id")
        _zaman_dogrula(adim.get("timestamp"), f"{yer}.timestamp")
        if adim["timestamp"] <= once:
            raise KanitHatasi("Adım zamanları kesin artan UTC olmalı")
        once = adim["timestamp"]
        attack = adim.get("attack") or {}
        if not re.fullmatch(r"T\d{4}(?:\.\d{3})?", attack.get("technique", "")) or not attack.get("name"):
            raise KanitHatasi(f"{yer}: ATT&CK technique/name eksik")
        web, ad = adim.get("web"), adim.get("ad")
        if not isinstance(web, dict) or not isinstance(ad, dict):
            raise KanitHatasi(f"{yer}: sentetik web ve ad kayıtları gerekli")
        if web.get("event_id") != f"W{i:03d}" or ad.get("event_id") != f"A{i:03d}":
            raise KanitHatasi(f"{yer}: kanıt kimlikleri W###/A### sırasına uymalı")
        if web.get("method") not in ("GET", "POST") or not str(web.get("uri", "")).startswith("/"):
            raise KanitHatasi(f"{yer}: yalnız yerel GET/POST günlük canlandırması desteklenir")
        if not isinstance(ad.get("event_code"), int):
            raise KanitHatasi(f"{yer}: AD event_code tamsayı olmalı")
        beklenen.update(adim.get("expected_evidence", []))
        detection = adim.get("expected_detection") or {}
        if not detection.get("id") or not detection.get("title"):
            raise KanitHatasi(f"{yer}: beklenen tespit eksik")
        for kanit in adim.get("expected_evidence", []):
            if kanit not in (web["event_id"], ad["event_id"]):
                raise KanitHatasi(f"{yer}: beklenen kanıt adımın kayıtlarına işaret etmeli")
    gercek = {a[k]["event_id"] for a in adimlar for k in ("web", "ad")}
    if beklenen != gercek:
        raise KanitHatasi("expected_evidence bütün web/AD kanıtlarını tam olarak kapsamalı")
    _gizli_alan_yok(s)
    return s


def negatif_dogrula(kontroller):
    if not isinstance(kontroller, list) or not kontroller:
        raise KanitHatasi("En az bir negatif kontrol gerekir")
    kimlikler = set()
    for n in kontroller:
        if not isinstance(n, dict) or n.get("is_negative") is not True:
            raise KanitHatasi("Negatif kontrol is_negative=true olmalı")
        if not isinstance(n.get("event_id"), str) or n["event_id"] in kimlikler:
            raise KanitHatasi("Negatif kontrol event_id eksik veya yinelenmiş")
        kimlikler.add(n["event_id"])
        _zaman_dogrula(n.get("timestamp"), f"{n['event_id']}.timestamp")
        if not all(isinstance(n.get(k), str) and n[k] for k in ("source", "host", "account", "action", "object")):
            raise KanitHatasi(f"{n['event_id']}: negatif kontrol alanları eksik")
    _gizli_alan_yok(kontroller, "negatif_kontroller")
    return kontroller


def _normalize(s, negatifler):
    env = s["environment"]
    satirlar = []
    for adim in s["steps"]:
        attack = adim["attack"]
        detection = adim["expected_detection"]
        web, ad = adim["web"], adim["ad"]
        ortak = {
            "schema": SURUM, "run_id": s["run_id"], "timestamp": adim["timestamp"],
            "step_id": adim["id"], "host": env["client_host"], "account": env["account"],
            "attack_technique": attack["technique"], "detection_id": detection["id"],
            "is_negative": False, "result": "success",
        }
        satirlar.append(dict(ortak, event_id=web["event_id"], source="web", action=web["action"],
                             object=web["uri"], status=int(web["status"]), bytes=int(web.get("bytes", 0))))
        satirlar.append(dict(ortak, event_id=ad["event_id"], source="ad", host=env["dc_host"],
                             action=ad["action"], object=ad["object"], event_code=ad["event_code"]))
    for n in negatifler:
        satirlar.append({
            "schema": SURUM, "run_id": s["run_id"], "timestamp": n["timestamp"],
            "step_id": "negative-control", "event_id": n["event_id"], "source": n["source"],
            "host": n["host"], "account": n["account"], "action": n["action"],
            "object": n["object"], "result": "success", "attack_technique": "",
            "detection_id": "", "is_negative": True,
        })
    return sorted(satirlar, key=lambda r: (r["timestamp"], r["event_id"]))


def _xml_bayt(s):
    kok = ET.Element("Events", {"RunId": s["run_id"], "Simulation": "true"})
    for adim in s["steps"]:
        ad = adim["ad"]
        olay = ET.SubElement(kok, "Event")
        system = ET.SubElement(olay, "System")
        ET.SubElement(system, "Provider", {"Name": "Pafta-Synthetic-AD"})
        ET.SubElement(system, "EventID").text = str(ad["event_code"])
        ET.SubElement(system, "TimeCreated", {"SystemTime": adim["timestamp"]})
        ET.SubElement(system, "Computer").text = s["environment"]["dc_host"]
        ET.SubElement(system, "EventRecordID").text = ad["event_id"]
        data = ET.SubElement(olay, "EventData")
        for adi, deger in (("RunId", s["run_id"]), ("StepId", adim["id"]),
                           ("TargetUserName", s["environment"]["account"]),
                           ("Action", ad["action"]), ("Object", ad["object"]),
                           ("Simulation", "true")):
            ET.SubElement(data, "Data", {"Name": adi}).text = str(deger)
    ET.indent(kok, space="  ")
    return ET.tostring(kok, encoding="utf-8", xml_declaration=True, short_empty_elements=True) + b"\n"


def uret(s, negatifler):
    """Bellekte bayt üretir; saat, PID, rasgelelik, ağ veya mutlak yol kullanmaz."""
    senaryo_dogrula(s)
    negatif_dogrula(negatifler)
    env = s["environment"]
    web, ad = [], []
    for adim in s["steps"]:
        w, a = adim["web"], adim["ad"]
        web.append({
            "timestamp": adim["timestamp"], "run_id": s["run_id"], "event_id": w["event_id"],
            "simulation": True, "source_ip": env["source_ip"], "host": env["web_host"],
            "account": env["account"], "method": w["method"], "uri": w["uri"],
            "status": int(w["status"]), "bytes": int(w.get("bytes", 0)), "action": w["action"],
        })
        ad.append({
            "timestamp": adim["timestamp"], "run_id": s["run_id"], "event_id": a["event_id"],
            "simulation": True, "host": env["dc_host"], "account": env["account"],
            "event_code": a["event_code"], "action": a["action"], "object": a["object"],
        })
    normalized = _normalize(s, negatifler)
    zaman = [{
        "order": a["order"], "timestamp": a["timestamp"], "step_id": a["id"],
        "title": a["title"], "attack_technique": a["attack"]["technique"],
        "attack_name": a["attack"]["name"], "expected_evidence": a["expected_evidence"],
        "expected_detection": a["expected_detection"],
    } for a in s["steps"]]
    tespitler = [{
        "id": a["expected_detection"]["id"], "timestamp": a["timestamp"],
        "run_id": s["run_id"], "step_id": a["id"], "title": a["expected_detection"]["title"],
        "attack_technique": a["attack"]["technique"], "evidence": a["expected_evidence"],
        "simulation": True,
    } for a in s["steps"]]
    out = io.StringIO(newline="")
    alanlar = ["TimeGenerated", "RunId", "StepId", "EventId", "Source", "Computer", "Account",
               "Action", "Object", "Result", "AttackTechnique", "DetectionId", "IsNegative"]
    writer = csv.DictWriter(out, fieldnames=alanlar, lineterminator="\n")
    writer.writeheader()
    for r in normalized:
        writer.writerow({
            "TimeGenerated": r["timestamp"], "RunId": r["run_id"], "StepId": r["step_id"],
            "EventId": r["event_id"], "Source": r["source"], "Computer": r["host"],
            "Account": r["account"], "Action": r["action"], "Object": r["object"],
            "Result": r["result"], "AttackTechnique": r["attack_technique"],
            "DetectionId": r["detection_id"], "IsNegative": str(r["is_negative"]).lower(),
        })
    spl = [dict(r, _time=r["timestamp"], sourcetype=f"pafta:synthetic:{r['source']}") for r in normalized]
    return {
        "web.ndjson": _satir_bayt(web), "ad_events.ndjson": _satir_bayt(ad),
        "ad_events.xml": _xml_bayt(s), "normalized.jsonl": _satir_bayt(normalized),
        "kql_events.csv": out.getvalue().encode("utf-8"), "spl_events.jsonl": _satir_bayt(spl),
        "timeline.json": _json_bayt({"run_id": s["run_id"], "simulation": True, "steps": zaman}),
        "detections.json": _json_bayt(tespitler), "negative_controls.json": _json_bayt(negatifler),
    }


def _manifest(run_id, dosyalar):
    return _json_bayt({
        "algorithm": "SHA-256", "run_id": run_id, "simulation": True,
        "files": [{"path": ad, "sha256": hashlib.sha256(dosyalar[ad]).hexdigest(), "bytes": len(dosyalar[ad])}
                  for ad in DOSYALAR],
    })


def yaz(senaryo_yolu, cikti_yolu, negatif_yolu=None):
    s = senaryo_dogrula(_json_oku(senaryo_yolu))
    senaryo_yolu = Path(senaryo_yolu)
    negatif_yolu = Path(negatif_yolu) if negatif_yolu else senaryo_yolu.parent / "negative_controls.json"
    negatifler = negatif_dogrula(_json_oku(negatif_yolu))
    dosyalar = uret(s, negatifler)
    cikti = Path(cikti_yolu)
    cikti.mkdir(parents=True, exist_ok=True)
    for ad, icerik in dosyalar.items():
        (cikti / ad).write_bytes(icerik)
    (cikti / "manifest.sha256.json").write_bytes(_manifest(s["run_id"], dosyalar))
    return {"run_id": s["run_id"], "files": len(dosyalar) + 1,
            "events": len(dosyalar["normalized.jsonl"].splitlines())}


def dogrula(senaryo_yolu, cikti_yolu, negatif_yolu=None):
    """Manifesti ve bütün içeriği yeniden üretimle karşılaştırır; hiçbir hatayı yutmaz."""
    s = senaryo_dogrula(_json_oku(senaryo_yolu))
    senaryo_yolu = Path(senaryo_yolu)
    negatif_yolu = Path(negatif_yolu) if negatif_yolu else senaryo_yolu.parent / "negative_controls.json"
    negatifler = negatif_dogrula(_json_oku(negatif_yolu))
    beklenen = uret(s, negatifler)
    beklenen["manifest.sha256.json"] = _manifest(s["run_id"], beklenen)
    cikti = Path(cikti_yolu)
    try:
        manifest = _json_oku(cikti / "manifest.sha256.json")
    except KanitHatasi as e:
        raise KanitHatasi(f"Manifest eksik veya bozuk: {e}") from e
    if manifest.get("algorithm") != "SHA-256" or manifest.get("run_id") != s["run_id"]:
        raise KanitHatasi("Manifest algoritması veya run_id uyuşmuyor")
    kayitlar = manifest.get("files")
    if not isinstance(kayitlar, list) or {r.get("path") for r in kayitlar} != set(DOSYALAR):
        raise KanitHatasi("Manifest dosya listesi eksik, fazla veya bozuk")
    for kayit in kayitlar:
        ad = kayit["path"]
        try:
            icerik = (cikti / ad).read_bytes()
        except OSError as e:
            raise KanitHatasi(f"Kanıt dosyası eksik: {ad}") from e
        if len(icerik) != kayit.get("bytes") or hashlib.sha256(icerik).hexdigest() != kayit.get("sha256"):
            raise KanitHatasi(f"SHA-256/boyut uyuşmazlığı: {ad}")
    for ad, icerik in beklenen.items():
        try:
            gercek = (cikti / ad).read_bytes()
        except OSError as e:
            raise KanitHatasi(f"Beklenen kanıt eksik: {ad}") from e
        if gercek != icerik:
            raise KanitHatasi(f"Normalize kanıt veya manifest içeriği beklenenle uyuşmuyor: {ad}")
    try:
        satirlar = [json.loads(x) for x in (cikti / "normalized.jsonl").read_text(encoding="utf-8").splitlines()]
        kok = ET.parse(cikti / "ad_events.xml").getroot()
    except (OSError, UnicodeError, json.JSONDecodeError, ET.ParseError) as e:
        raise KanitHatasi(f"NDJSON/XML ayrıştırılamadı: {e}") from e
    if kok.tag != "Events" or len(kok.findall("Event")) != len(s["steps"]):
        raise KanitHatasi("Sentetik AD XML kanıtı eksik")
    return {"ok": True, "run_id": s["run_id"], "events": len(satirlar),
            "detections": len(s["steps"]), "negative_controls": len(negatifler)}


def main(argv=None):
    p = argparse.ArgumentParser(description="Pafta madde 103 çevrimdışı canlandırma kanıtı")
    p.add_argument("komut", choices=("uret", "dogrula"))
    p.add_argument("--senaryo", required=True)
    p.add_argument("--cikti", required=True)
    p.add_argument("--negatifler")
    args = p.parse_args(argv)
    try:
        sonuc = yaz(args.senaryo, args.cikti, args.negatifler) if args.komut == "uret" else dogrula(
            args.senaryo, args.cikti, args.negatifler)
    except KanitHatasi as e:
        print(f"REDDEDİLDİ: {e}", file=sys.stderr)
        return 2
    print(json.dumps(sonuc, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
