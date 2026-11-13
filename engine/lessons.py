# -*- coding: utf-8 -*-
"""Dil yolları (track) ve ders dosyaları.

Her yol `tracks/<id>/track.json` ile tanımlanır; dersler `tracks/<id>/lessons/*.md`
dosyalarıdır. Ders biçimi:

    ---
    id: p01
    title: Merhaba Python
    summary: tek satırlık özet
    kazanim: PCEP 1.5, PCAP 5.4        (isteğe bağlı: tracks/<id>/kazanim.json'daki maddeler)
    backend: wsl                     (isteğe bağlı: Python/Bash için gerçek Linux)
    timeout: 120                     (isteğe bağlı: saniye; adım meta'sı öncelikli)
    ---
    ::: anlat Adımın başlığı
    markdown...
    :::
    ::: tahmin
    ```python
    print(2 ** 10)
    ```
    :::
    ::: gorev Görev başlığı
    markdown...
    ```starter / ```stdin / ```test / ```solution / ```hint / ```setup / ```meta
    :::
"""
import json
import os
import re
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACKS_DIR = os.path.join(ROOT, "tracks")

STEP_KINDS = ("anlat", "tahmin", "gorev")
KOD_DILLERI = ("python", "py", "", "regex", "bash", "sh", "powershell", "ps1", "sql", "kql", "kusto", "spl", "splunk",
               "javascript", "js", "c", "php", "java", "csharp", "cs", "asm", "x86", "ad", "ldap", "sigma", "yara", "kibana", "lucene", "eql", "cmd", "batch", "bat", "wireshark", "bpf", "packets", "tshark", "tcpdump-lab", "suricata", "zeek", "esql", "ingest", "rule", "vql")
# gercek: çalıştırılamayan dillerde (C, PHP) tahmin adımının gerçek çıktısı, ders yazarınca verilir
SPECIAL = ("starter", "stdin", "test", "solution", "hint", "setup", "meta", "gercek")
_STEP_RE = re.compile(r"^:::\s*(anlat|tahmin|gorev)\b\s*(.*)$")
_FENCE_RE = re.compile(r"^```\s*([\w-]*)\s*(.*)$")


def _front_matter(text):
    meta = {}
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            for line in text[3:end].strip().splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
            text = text[end + 4:]
    return meta, text


def _parse_meta(lines):
    out = {}
    for line in lines:
        if ":" in line:
            k, v = line.split(":", 1)
            v = v.strip()
            out[k.strip()] = int(v) if v.isdigit() else v
    return out


def _parse_step(kind, title, lines):
    body, parts = [], {k: [] for k in SPECIAL}
    code = None
    code_dil = None
    i = 0
    while i < len(lines):
        m = _FENCE_RE.match(lines[i])
        if not m:
            body.append(lines[i])
            i += 1
            continue
        info = m.group(1)
        j = i + 1
        block = []
        while j < len(lines) and not lines[j].startswith("```"):
            block.append(lines[j])
            j += 1
        if info in SPECIAL:
            parts[info].append("\n".join(block))
        elif kind == "tahmin" and code is None and info in KOD_DILLERI:
            code = "\n".join(block)
            code_dil = info
        else:
            body.extend(lines[i:j + 1])
        i = j + 1

    step = {"kind": kind, "title": title, "body": "\n".join(body).strip()}
    if kind == "tahmin":
        step["code"] = code or ""
        if code_dil in ("kibana", "lucene", "eql", "esql", "ingest", "rule", "wireshark", "bpf", "packets", "tshark", "tcpdump-lab"):
            step["code_dil"] = code_dil
    for k in ("starter", "stdin", "test", "solution", "setup"):
        if parts[k]:
            step[k] = parts[k][0]
    if kind == "tahmin" and parts["gercek"]:
        step["gercek"] = parts["gercek"][0] + "\n"
    if kind == "tahmin" and parts["stdin"]:
        step["stdin"] = parts["stdin"][0]
    step["hints"] = [h.strip() for h in parts["hint"]]
    step["meta"] = _parse_meta(parts["meta"][0].splitlines()) if parts["meta"] else {}
    return step


def kazanim_ayir(metin):
    """'PCAP 1.1, PCAP  3.2' → ['PCAP 1.1', 'PCAP 3.2']: sertifika kimliği + madde kodu."""
    return [" ".join(p.split()) for p in (metin or "").split(",") if p.strip()]


def parse_lesson(text):
    meta, body = _front_matter(text.replace("\r\n", "\n"))
    lines = body.split("\n")
    steps = []
    i = 0
    while i < len(lines):
        m = _STEP_RE.match(lines[i])
        if not m:
            i += 1
            continue
        kind, title = m.group(1), m.group(2).strip()
        j, buf, fence = i + 1, [], False
        while j < len(lines):
            line = lines[j]
            if line.startswith("```"):
                fence = not fence
            elif not fence and line.strip() == ":::":
                break
            buf.append(line)
            j += 1
        steps.append(_parse_step(kind, title, buf))
        i = j + 1
    # A lesson can opt in without changing its whole language track. Explicit
    # step metadata wins, including backend: native for a comparison example.
    defaults = _parse_meta([f"{key}: {meta[key]}" for key in ("backend", "timeout") if key in meta])
    for step in steps:
        step["meta"] = dict(defaults, **step["meta"])
    return {
        "id": meta.get("id", ""),
        "title": meta.get("title", "Adsız ders"),
        "summary": meta.get("summary", ""),
        "kazanim": kazanim_ayir(meta.get("kazanim")),
        "steps": steps,
    }


class Library:
    """Diskteki yolları ve dersleri okur; dosya değiştikçe yeniden yükler."""

    def __init__(self, root=TRACKS_DIR):
        self.root = root
        self._lock = threading.Lock()
        self._cache = {}  # yol -> (mtime, ders)

    def track_ids(self):
        ids = []
        for name in sorted(os.listdir(self.root)):
            if os.path.isfile(os.path.join(self.root, name, "track.json")):
                ids.append(name)
        return ids

    def track(self, tid):
        path = os.path.join(self.root, tid, "track.json")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("id", tid)
        data.setdefault("modules", [])
        data.setdefault("status", "active")
        return data

    def tracks(self):
        out = [self.track(t) for t in self.track_ids()]
        out.sort(key=lambda t: t.get("order", 99))
        return out

    def _lesson_files(self, tid):
        d = os.path.join(self.root, tid, "lessons")
        if not os.path.isdir(d):
            return {}
        files = {}
        for name in os.listdir(d):
            if name.endswith(".md"):
                # Klasik ``ht22-konu`` ve tireli AI kimlikleri
                # ``ai-saldiri-02-konu`` biçimlerini aynı şekilde çöz.
                match = re.match(r"^(.+?\d+)(?:-.*)?\.md$", name)
                lid = match.group(1) if match else name.split("-", 1)[0]
                files[lid] = os.path.join(d, name)
        return files

    def lesson(self, tid, lid):
        path = self._lesson_files(tid).get(lid)
        if not path:
            return None
        mtime = os.path.getmtime(path)
        with self._lock:
            hit = self._cache.get(path)
            if hit and hit[0] == mtime:
                return hit[1]
        with open(path, encoding="utf-8") as f:
            lesson = parse_lesson(f.read())
        lesson["id"] = lesson["id"] or lid
        with self._lock:
            self._cache[path] = (mtime, lesson)
        return lesson

    def outline(self, tid):
        """Yolun modülleri + her dersin başlığı ve adım türleri."""
        track = self.track(tid)
        order = []
        for mi, mod in enumerate(track["modules"]):
            mod_out = dict(mod, index=mi + 1, lessons=[])
            for lid in mod.get("lessons", []):
                les = self.lesson(tid, lid)
                if les is None:
                    mod_out["lessons"].append({"id": lid, "title": "(yazılmadı)", "summary": "",
                                               "kinds": [], "missing": True})
                    continue
                mod_out["lessons"].append({
                    "id": lid, "title": les["title"], "summary": les["summary"],
                    "kinds": [s["kind"] for s in les["steps"]], "kazanim": les["kazanim"],
                })
                order.append(lid)
            track["modules"][mi] = mod_out
        track["order"] = order
        return track

    def locate(self, tid, lid):
        """Dersin modülü, rütbesi, önceki/sonraki dersi."""
        outline = self.outline(tid)
        order = outline["order"]
        mod = next((m for m in outline["modules"] if any(l["id"] == lid for l in m["lessons"])), None)
        i = order.index(lid) if lid in order else -1
        return {
            "module": {"index": mod["index"], "title": mod["title"], "rank": mod.get("rank", ""),
                       "zen": mod.get("zen", "")} if mod else None,
            "prev": order[i - 1] if i > 0 else None,
            "next": order[i + 1] if 0 <= i < len(order) - 1 else None,
            "number": i + 1, "total": len(order),
        }

    def kazanim(self, tid, outline=None):
        """Yolun sertifika konu listeleri ve her maddeyi karşılayan dersler.

        tracks/<id>/kazanim.json:
            {"sertifikalar": [{"id": "PCAP", "ad": "PCAP-31-03", "tam_ad": ..., "kurum": ..., "kaynak": url,
              "sinav": {"soru": 40, "dakika": 65, "gecme": 70},
              "bolumler": [{"kod": "1", "baslik": ..., "agirlik": 12,
                            "maddeler": [{"kod": "1.1", "baslik": ..., "not": "isteğe bağlı"}]}]}]}
        Dersler maddeyi ön bilgideki `kazanim: PCAP 1.1, ...` satırıyla karşılar. Listede olmayan
        etiketler "bilinmeyen"e düşer (validate bunları hata sayar).
        """
        path = os.path.join(self.root, tid, "kazanim.json")
        data = {"sertifikalar": []}
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        maddeler = {}
        for s in data.get("sertifikalar", []):
            for b in s.get("bolumler", []):
                for m in b.get("maddeler", []):
                    m["dersler"] = []
                    maddeler[f"{s['id']} {m['kod']}"] = m
        bilinmeyen = []
        outline = outline or self.outline(tid)
        for lid in outline["order"]:
            for etiket in self.lesson(tid, lid)["kazanim"]:
                m = maddeler.get(etiket)
                if m is None:
                    bilinmeyen.append({"ders": lid, "etiket": etiket})
                elif lid not in m["dersler"]:
                    m["dersler"].append(lid)
        return {"sertifikalar": data.get("sertifikalar", []), "bilinmeyen": bilinmeyen}


def public_step(step):
    """Ön yüze gidecek adım: test, çözüm ve kurulum kodu gizli."""
    out = {k: v for k, v in step.items() if k not in ("test", "solution", "setup", "gercek")}
    out["has_solution"] = bool(step.get("solution"))
    return out
