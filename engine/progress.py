# -*- coding: utf-8 -*-
"""İlerleme kaydı.

Veri %LOCALAPPDATA%\\Pafta\\progress.json'da durur: proje klasörü taşınsa ya da
masaüstü yeniden düzenlense bile ilerleme kaybolmaz. Yazımlar atomik
(geçici dosya + os.replace).
"""
import datetime as _dt
import json
import os
import threading

# Leitner kutuları: kutu -> kaç gün sonra tekrar
INTERVALS = {1: 1, 2: 3, 3: 7, 4: 16, 5: 35}
MASTERED = 6


def data_dir():
    base = os.environ.get("PAFTA_DATA") or os.path.join(
        os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "Pafta")
    os.makedirs(base, exist_ok=True)
    return base


def today():
    return _dt.date.today().isoformat()


def _plus_days(n):
    return (_dt.date.today() + _dt.timedelta(days=n)).isoformat()


def _now():
    return _dt.datetime.now().isoformat(timespec="seconds")


class Progress:
    def __init__(self, path=None):
        self.path = path or os.path.join(data_dir(), "progress.json")
        self._lock = threading.Lock()
        self.data = self._load()

    # ── disk ──
    def _load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            d = {}
        d.setdefault("version", 1)
        d.setdefault("days", [])
        d.setdefault("last", None)
        d.setdefault("tracks", {})
        d.setdefault("playground", "")
        d.setdefault("settings", {"theme": "mavi"})
        return d

    def _save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.path)

    def _track(self, tid):
        t = self.data["tracks"].setdefault(tid, {})
        t.setdefault("steps", {})
        t.setdefault("drafts", {})
        t.setdefault("review", {})
        return t

    def _mark_day(self):
        d = today()
        if d not in self.data["days"]:
            self.data["days"].append(d)

    # ── okuma ──
    def snapshot(self):
        with self._lock:
            return json.loads(json.dumps(self.data))

    def track_state(self, tid):
        with self._lock:
            return json.loads(json.dumps(self._track(tid)))

    def streak(self):
        days = set(self.data["days"])
        n, cur = 0, _dt.date.today()
        if cur.isoformat() not in days:
            cur -= _dt.timedelta(days=1)  # bugün henüz çalışmadıysan seri dünden sayılır
        while cur.isoformat() in days:
            n += 1
            cur -= _dt.timedelta(days=1)
        return n

    def due(self):
        out, t = [], today()
        with self._lock:
            for tid, tr in self.data["tracks"].items():
                for key, r in tr.get("review", {}).items():
                    if r.get("box", 0) < MASTERED and r.get("due", "9999") <= t:
                        out.append({"track": tid, "key": key, "box": r["box"], "due": r["due"]})
        out.sort(key=lambda r: (r["due"], r["box"]))
        return out

    # ── yazma ──
    def visit(self, tid, lid, step, done=False):
        with self._lock:
            self.data["last"] = {"track": tid, "lesson": lid, "step": step}
            if done:
                s = self._track(tid)["steps"].setdefault(f"{lid}:{step}", {})
                if not s.get("done"):
                    s.update(done=True, at=_now())
                    self._mark_day()
            self._save()

    def attempt(self, tid, key, passed):
        with self._lock:
            tr = self._track(tid)
            s = tr["steps"].setdefault(key, {})
            s["attempts"] = s.get("attempts", 0) + 1
            first = passed and not s.get("done")
            if passed:
                if not s.get("done"):
                    s.update(done=True, at=_now())
                if key not in tr["review"]:
                    tr["review"][key] = {"box": 1, "due": _plus_days(INTERVALS[1])}
                self._mark_day()
            self._save()
            return {"attempts": s["attempts"], "first": first, "revealed": s.get("revealed", False)}

    def guess(self, tid, key, correct):
        with self._lock:
            s = self._track(tid)["steps"].setdefault(key, {})
            if not s.get("done"):
                s.update(done=True, at=_now(), guess_ok=bool(correct))
                self._mark_day()
            self._save()

    def reveal(self, tid, key):
        with self._lock:
            tr = self._track(tid)
            s = tr["steps"].setdefault(key, {})
            s["revealed"] = True
            # çözüme bakılan görev yarın yeniden sorulur
            tr["review"][key] = {"box": 1, "due": _plus_days(1)}
            self._save()

    def review_result(self, tid, key, passed):
        with self._lock:
            tr = self._track(tid)
            r = tr["review"].setdefault(key, {"box": 1, "due": today()})
            if passed:
                r["box"] = min(r.get("box", 1) + 1, MASTERED)
                r["due"] = _plus_days(INTERVALS[r["box"]]) if r["box"] < MASTERED else "9999-12-31"
                self._mark_day()
            else:
                r["box"], r["due"] = 1, _plus_days(1)
            self._save()
            return dict(r)

    def save_draft(self, tid, key, code):
        with self._lock:
            drafts = self._track(tid)["drafts"]
            if code:
                drafts[key] = code[:100_000]
            else:
                drafts.pop(key, None)
            self._save()

    def playground(self, dil="python"):
        with self._lock:
            if dil == "python":
                return self.data.get("playground", "")
            return self.data.get("playground_diller", {}).get(dil, "")

    def save_playground(self, code, dil="python"):
        with self._lock:
            if dil == "python":
                self.data["playground"] = code[:200_000]
            elif dil in ("regex", "bash", "powershell", "sql", "kql", "spl", "javascript", "sigma", "yara", "packets", "ad", "elastic"):
                self.data.setdefault("playground_diller", {})[dil] = code[:200_000]
            self._save()

    # ── sınav ──
    def _sinav(self):
        s = self.data.setdefault("sinav", {})
        s.setdefault("aktif", None)
        s.setdefault("gecmis", [])
        s.setdefault("sayac", 0)
        return s

    def sinav_durumu(self):
        with self._lock:
            return json.loads(json.dumps(self._sinav()))

    def sinav_basla(self, sinav):
        with self._lock:
            s = self._sinav()
            if s["aktif"]:
                raise ValueError("süren bir sınav var: önce onu bitir ya da vazgeç")
            s["sayac"] += 1
            sinav["no"] = s["sayac"]
            s["aktif"] = sinav
            self._save()
            return json.loads(json.dumps(sinav))

    def sinav_cevap(self, no, soru, cevap=None, isaretli=None, son=None):
        """Süren sınava bir cevap ya da işaret yazar; süre (son) geçtiyse yazmaz."""
        with self._lock:
            a = self._sinav()["aktif"]
            if not a or a["no"] != no or not (0 <= soru < len(a["sorular"])):
                raise ValueError("böyle süren bir sınav ya da soru yok")
            if son is not None and son > a["bitis"]:
                return False
            if cevap is not None:
                a.setdefault("cevaplar", {})[str(soru)] = str(cevap)[:20_000]
            if isaretli is not None:
                isaret = set(a.setdefault("isaretli", []))
                (isaret.add if isaretli else isaret.discard)(soru)
                a["isaretli"] = sorted(isaret)
            self._save()
            return True

    def sinav_kapat(self, no, sonuc=None):
        """Süren sınavı kapatır; sonuç verilirse geçmişin başına yazar (son 30 sınav tutulur)."""
        with self._lock:
            s = self._sinav()
            if not s["aktif"] or s["aktif"]["no"] != no:
                raise ValueError("böyle süren bir sınav yok")
            s["aktif"] = None
            if sonuc is not None:
                s["gecmis"].insert(0, sonuc)
                del s["gecmis"][30:]
                self._mark_day()
            self._save()

    def sinav_sonucu(self, no):
        with self._lock:
            r = next((g for g in self._sinav()["gecmis"] if g.get("no") == no), None)
            return json.loads(json.dumps(r)) if r else None

    def tekrara_ekle(self, tid, keys):
        """Sınavda yanlış yapılan görevler bugün tekrar listesine kutu 1'den girer."""
        with self._lock:
            tr = self._track(tid)
            for key in keys:
                tr["review"][key] = {"box": 1, "due": today()}
            self._save()
            return len(keys)

    def set_setting(self, key, value):
        with self._lock:
            self.data["settings"][key] = value
            self._save()

    def reset(self):
        with self._lock:
            settings = self.data.get("settings", {})
            self.data = self._load_empty()
            self.data["settings"] = settings
            self._save()

    def _load_empty(self):
        return {"version": 1, "days": [], "last": None, "tracks": {}, "playground": "",
                "settings": {"theme": "mavi"}}
