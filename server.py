# -*- coding: utf-8 -*-
"""Pafta yerel sunucusu.

Yalnızca 127.0.0.1'e bağlanır. Kod çalıştıran bir yerel sunucu, ziyaret ettiğin
herhangi bir web sitesinin hedefi olabilir; o yüzden üç kilit var:
  1. Host başlığı 127.0.0.1:<port> / localhost:<port> olmalı (DNS rebinding'e karşı)
  2. Origin varsa yine aynı köken olmalı
  3. /api/* istekleri her açılışta üretilen gizli belirteci X-Pafta-Token
     başlığında taşımalı (başka köken bu başlığı CORS ön-uçuşu olmadan gönderemez)
"""
import argparse
import json
import mimetypes
import os
import random
import re
import secrets
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from engine.runtime_env import refresh_windows_runtime_env  # noqa: E402
refresh_windows_runtime_env()

from engine import runners, sinav  # noqa: E402
from engine.lessons import Library, public_step  # noqa: E402
from engine.progress import Progress, data_dir, today  # noqa: E402
from engine.rota import Rota  # noqa: E402
from engine.sinav import normalize  # noqa: E402,F401  (eski içe aktarımlar için)

WEB = os.path.join(ROOT, "web")
CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
       "img-src 'self' data:; connect-src 'self'; font-src 'self'; base-uri 'none'; "
       "form-action 'none'; frame-ancestors 'none'")


class App:
    def __init__(self, token=None):
        self.lib = Library()
        self.prog = Progress()
        self.rota = Rota()
        self.token = token or secrets.token_urlsafe(24)
        self.port = None
        self.last_ping = time.time()

    # ── yardımcılar ──
    def runner_for(self, tid):
        try:
            track = self.lib.track(tid)
        except OSError:
            return None
        return runners.get(track.get("runner", tid))

    def step(self, tid, lid, idx):
        les = self.lib.lesson(tid, lid)
        if les is None or not (0 <= idx < len(les["steps"])):
            return None, None
        return les, les["steps"][idx]

    def track_meta(self, t):
        """Ön yüzün bir yol için bilmesi gerekenler: dil, koşucu özellikleri, kahraman metni."""
        runner = runners.get(t.get("runner", t["id"]))
        return {"dil": t.get("dil", t["id"]),
                "ozellik": dict(runner.ozellik) if runner else {"roentgen": False, "dis": None},
                "hazir": bool(runner and runner.available()),
                "kahraman": t.get("kahraman"), "girdi_etiketi": t.get("girdi_etiketi"),
                "okuma_dili": t.get("okuma_dili")}

    def state(self):
        snap = self.prog.snapshot()
        tracks = []
        for t in self.lib.tracks():
            info = {k: t.get(k) for k in ("id", "name", "status", "group", "role", "order", "tagline")}
            info.update(self.track_meta(t))
            if t.get("status") == "active":
                outline = self.lib.outline(t["id"])
                kinds = [k for m in outline["modules"] for l in m["lessons"] for k in l["kinds"]]
                done = snap["tracks"].get(t["id"], {}).get("steps", {})
                info.update(lessons_total=len(outline["order"]), steps_total=len(kinds),
                            steps_done=sum(1 for v in done.values() if v.get("done")))
            tracks.append(info)
        return {"tracks": tracks, "last": snap["last"], "streak": self.prog.streak(),
                "due_count": len(self.prog.due()), "settings": snap["settings"],
                "data_path": self.prog.path, "today": today(), "days": snap["days"][-60:]}

    def track_view(self, tid):
        outline = self.lib.outline(tid)
        outline.update(self.track_meta(outline))
        st = self.prog.track_state(tid)
        return {"track": outline, "steps": st["steps"], "review": st["review"],
                "kazanim": self.lib.kazanim(tid, outline)["sertifikalar"]}

    def lesson_view(self, tid, lid):
        les = self.lib.lesson(tid, lid)
        if les is None:
            return None
        st = self.prog.track_state(tid)
        pre = lid + ":"
        steps = {k[len(pre):]: v for k, v in st["steps"].items() if k.startswith(pre)}
        drafts = {k[len(pre):]: v for k, v in st["drafts"].items() if k.startswith(pre)}
        track = self.lib.track(tid)
        return {"lesson": {"id": les["id"], "title": les["title"], "summary": les["summary"], "kazanim": les["kazanim"],
                           "steps": [public_step(s) for s in les["steps"]]},
                "track": dict({"id": tid, "name": track.get("name", tid), "ranks": track.get("ranks", [])},
                              **self.track_meta(track)),
                "loc": self.lib.locate(tid, lid), "progress": {"steps": steps, "drafts": drafts}}

    def review_view(self):
        out = []
        for r in self.prog.due():
            lid, idx = r["key"].split(":")
            les, step = self.step(r["track"], lid, int(idx))
            if step is None:
                continue
            out.append(dict(r, lesson=lid, step=int(idx), lesson_title=les["title"],
                            title=step["title"] or "Görev"))
        return out

    # ── sınav kipi ──
    def sinav_yollar(self):
        out = []
        for t in self.lib.tracks():
            if t.get("status") != "active":
                continue
            serts = [{k: s.get(k) for k in ("id", "ad", "tam_ad", "kurum", "sinav")} |
                     {"bolumler": [{k: b.get(k) for k in ("kod", "baslik", "agirlik")} for b in s.get("bolumler", [])]}
                     for s in self.lib.kazanim(t["id"])["sertifikalar"]]
            out.append({"id": t["id"], "name": t.get("name", t["id"]), "sertifikalar": serts})
        return out

    def _sinav_secimi(self, b):
        tid = b["yol"]
        track = self.lib.track(tid)
        if track.get("status") != "active":
            raise ValueError("bu yol henüz yazılmadı")
        sert = b.get("sertifika") or None
        bolum = (b.get("bolum") or None) if sert else None
        tur = b.get("tur") or "karisik"
        if tur not in ("karisik", "tahmin", "gorev"):
            raise ValueError("bilinmeyen soru türü")
        biten = None
        if b.get("havuz") == "biten":
            outline = self.lib.outline(tid)
            adimlar = self.prog.track_state(tid)["steps"]
            biten = {l["id"] for m in outline["modules"] for l in m["lessons"]
                     if not l.get("missing") and l["kinds"]
                     and all(adimlar.get(f"{l['id']}:{i}", {}).get("done") for i in range(len(l["kinds"])))}
        sorular, gruplar = sinav.havuz(self.lib, tid, sert, bolum, biten)
        return track, sert, bolum, tur, sorular, gruplar

    def sinav_havuz(self, b):
        _, _, _, tur, sorular, gruplar = self._sinav_secimi(b)
        secilen = sinav.sec(sorular, gruplar, int(b.get("adet") or 20), tur, random.Random(0))
        return {"tahmin": sum(1 for s in sorular if s["kind"] == "tahmin"),
                "gorev": sum(1 for s in sorular if s["kind"] == "gorev"),
                "adet": len(secilen), "sure_sn": sinav.sure_hesapla(secilen)}

    def sinav_basla(self, b):
        track, sert, bolum, tur, sorular, gruplar = self._sinav_secimi(b)
        adet = int(b.get("adet") or 20)
        if not 1 <= adet <= 100:
            raise ValueError("soru sayısı 1 ile 100 arasında olmalı")
        secilen = sinav.sec(sorular, gruplar, adet, tur)
        if not secilen:
            raise ValueError("bu kapsamda soru yok")
        kapsam, gecme = [track.get("name", track["id"])], sinav.VARSAYILAN_GECME
        if sert:
            s = sinav.sertifika_bul(self.lib.kazanim(track["id"]), sert)
            kapsam.append(s.get("ad") or s["id"])
            gecme = (s.get("sinav") or {}).get("gecme") or gecme
            if bolum:
                kapsam.append(f"{bolum} · {gruplar[bolum]['baslik']}")
        simdi = time.time()
        sure_sn = sinav.sure_hesapla(secilen)
        a = self.prog.sinav_basla({
            "yol": track["id"], "yol_adi": track.get("name", track["id"]), "sertifika": sert, "bolum": bolum,
            "kapsam": " · ".join(kapsam), "tur": tur, "havuz": b.get("havuz") or "hepsi", "gecme": gecme,
            "baslangic": simdi, "bitis": simdi + sure_sn, "sure_sn": sure_sn,
            "sorular": secilen, "gruplar": {g: gruplar[g] for g in gruplar
                                            if any(g in q["gruplar"] for q in secilen)},
            "cevaplar": {}, "isaretli": []})
        return self.sinav_gorunumu(a)

    def sinav_gorunumu(self, a):
        track = self.lib.track(a["yol"])
        meta = self.track_meta(track)
        return dict({k: a.get(k) for k in ("no", "yol", "yol_adi", "kapsam", "tur", "sure_sn", "gecme", "sertifika", "bolum")},
                    kalan_sn=max(0, int(a["bitis"] - time.time())),
                    sorular=[sinav.soru_gorunumu(self.lib, a["yol"], meta["dil"], q) for q in a["sorular"]],
                    cevaplar=a.get("cevaplar", {}), isaretli=a.get("isaretli", []),
                    track=dict({"id": a["yol"], "name": track.get("name", a["yol"])}, **meta))

    def sinav_ozeti(self):
        s = self.prog.sinav_durumu()
        a = s["aktif"]
        aktif = None
        if a:
            aktif = {k: a.get(k) for k in ("no", "yol", "yol_adi", "kapsam", "tur", "sure_sn")}
            aktif.update(adet=len(a["sorular"]), cevaplanan=sum(1 for v in a.get("cevaplar", {}).values() if v.strip()),
                         kalan_sn=max(0, int(a["bitis"] - time.time())))
        return {"yollar": self.sinav_yollar(), "aktif": aktif, "gecmis": [sinav.ozet(g) for g in s["gecmis"]]}

    def sinav_bitir(self, no):
        a = self.prog.sinav_durumu()["aktif"]
        if not a or a["no"] != no:
            raise ValueError("böyle süren bir sınav yok")
        sonuc = sinav.puanla(self.lib, self.runner_for, a)
        self.prog.sinav_kapat(no, sonuc)
        return sonuc


def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        server_version = "Pafta"
        sys_version = ""

        def log_message(self, *a):  # pythonw altında stderr yok
            pass

        # ── güvenlik ──
        def _host_ok(self):
            allowed = {f"127.0.0.1:{app.port}", f"localhost:{app.port}"}
            if self.headers.get("Host", "") not in allowed:
                return False
            origin = self.headers.get("Origin")
            if origin and origin not in {f"http://{h}" for h in allowed}:
                return False
            return True

        def _api_ok(self):
            return secrets.compare_digest(self.headers.get("X-Pafta-Token", ""), app.token)

        # ── yanıt ──
        def _send(self, code, body, ctype="application/json; charset=utf-8"):
            if isinstance(body, (dict, list)):
                body = json.dumps(body, ensure_ascii=False).encode("utf-8")
            elif isinstance(body, str):
                body = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", CSP)
            self.end_headers()
            self.wfile.write(body)

        def _json_body(self):
            n = int(self.headers.get("Content-Length") or 0)
            if n > 2_000_000:
                raise ValueError("istek çok büyük")
            raw = self.rfile.read(n) if n else b"{}"
            return json.loads(raw.decode("utf-8") or "{}")

        # ── GET ──
        def do_GET(self):
            if not self._host_ok():
                return self._send(403, {"error": "yasak köken"})
            path = urlparse(self.path).path
            if path.startswith("/api/"):
                if not self._api_ok():
                    return self._send(403, {"error": "belirteç yok"})
                return self._api_get(path)
            return self._static(path)

        def _static(self, path):
            if path in ("/", "/index.html"):
                with open(os.path.join(WEB, "index.html"), encoding="utf-8") as f:
                    html = f.read().replace("{{TOKEN}}", app.token)
                return self._send(200, html, "text/html; charset=utf-8")
            rel = unquote(path.lstrip("/"))
            full = os.path.normpath(os.path.join(WEB, rel))
            if not full.startswith(WEB + os.sep) or not os.path.isfile(full):
                return self._send(404, {"error": "yok"})
            ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
            if full.endswith(".js"):
                ctype = "text/javascript"
            if ctype.startswith("text/"):
                ctype += "; charset=utf-8"
            with open(full, "rb") as f:
                return self._send(200, f.read(), ctype)

        def _api_get(self, path):
            parts = path.strip("/").split("/")[1:]
            try:
                if parts == ["ping"]:
                    app.last_ping = time.time()
                    return self._send(200, {"ok": True})
                if parts == ["state"]:
                    return self._send(200, app.state())
                if len(parts) == 2 and parts[0] == "track":
                    return self._send(200, app.track_view(parts[1]))
                if len(parts) == 3 and parts[0] == "lesson":
                    v = app.lesson_view(parts[1], parts[2])
                    return self._send(200, v) if v else self._send(404, {"error": "ders yok"})
                if parts == ["review"]:
                    snap = app.prog.snapshot()
                    kutular = [0] * 6
                    for tr in snap["tracks"].values():
                        for r in tr.get("review", {}).values():
                            kutular[min(max(r.get("box", 1), 1), 6) - 1] += 1
                    return self._send(200, {"items": app.review_view(), "kutular": kutular})
                if parts == ["playground"]:
                    dil = (parse_qs(urlparse(self.path).query).get("dil") or ["python"])[0]
                    return self._send(200, {"code": app.prog.playground(dil)})
                if parts == ["rota"]:
                    return self._send(200, app.rota.gorunum(app.state()["tracks"]))
                if parts == ["sinav"]:
                    return self._send(200, app.sinav_ozeti())
                if parts == ["sinav", "aktif"]:
                    a = app.prog.sinav_durumu()["aktif"]
                    return self._send(200, app.sinav_gorunumu(a)) if a else self._send(404, {"error": "süren sınav yok"})
                if len(parts) == 3 and parts[:2] == ["sinav", "sonuc"] and parts[2].isdigit():
                    r = app.prog.sinav_sonucu(int(parts[2]))
                    return self._send(200, r) if r else self._send(404, {"error": "böyle bir sınav yok"})
            except OSError as e:
                return self._send(404, {"error": str(e)})
            return self._send(404, {"error": "bilinmeyen uç"})

        # ── POST ──
        def do_POST(self):
            if not self._host_ok() or not self._api_ok():
                return self._send(403, {"error": "yasak"})
            path = urlparse(self.path).path
            try:
                body = self._json_body()
            except ValueError as e:
                return self._send(400, {"error": str(e)})
            name = path.strip("/").split("/", 1)[-1]
            fn = getattr(self, "_post_" + re.sub(r"\W", "_", name), None)
            if not fn:
                return self._send(404, {"error": "bilinmeyen uç"})
            try:
                return fn(body)
            except (KeyError, TypeError, ValueError) as e:
                return self._send(400, {"error": f"eksik/bozuk alan: {e}"})

        def _post_ping(self, b):
            app.last_ping = time.time()
            return self._send(200, {"ok": True})

        def _post_run(self, b):
            runner = app.runner_for(b.get("track", "python"))
            if runner is None:
                return self._send(400, {"error": "bu yolun koşucusu yok"})
            mode, code, stdin = b.get("mode", "run"), b["code"], b.get("stdin", "")
            setup = argv = None
            if b.get("lesson") is not None:
                _, step = app.step(b["track"], b["lesson"], int(b["step"]))
                if step is None:
                    return self._send(404, {"error": "adım yok"})
                setup = step.get("setup")
                argv = runners.argv_coz(step.get("meta"))   # görev argüman bekliyorsa Çalıştır da onlarla koşsun
                runner = runners.for_step(runner, step)
            elif "backend" in b:
                runner = runners.for_step(runner, {"meta": {"backend": b["backend"]}})
            if mode == "trace":
                res = runner.trace(code, stdin, setup, argv)
            elif mode == "dis":
                res = runner.dis(code, setup)
            else:
                res = runner.run(code, stdin, setup, argv=argv)
            if res is None:
                return self._send(400, {"error": "bu dilde bu görünüm yok"})
            if argv and mode != "dis":
                res["argv"] = argv
            return self._send(200, res)

        def _post_check(self, b):
            tid, lid, idx = b["track"], b["lesson"], int(b["step"])
            les, step = app.step(tid, lid, idx)
            if step is None or step["kind"] != "gorev":
                return self._send(404, {"error": "görev yok"})
            res = runners.for_step(app.runner_for(tid), step).test(b["code"], step)
            key = f"{lid}:{idx}"
            passed = res.get("status") == "pass"
            if b.get("review"):
                res["review"] = app.prog.review_result(tid, key, passed) if passed else None
            else:
                res["progress"] = app.prog.attempt(tid, key, passed)
                app.prog.visit(tid, lid, idx)
            return self._send(200, res)

        def _post_guess(self, b):
            tid, lid, idx = b["track"], b["lesson"], int(b["step"])
            _, step = app.step(tid, lid, idx)
            if step is None or step["kind"] != "tahmin":
                return self._send(404, {"error": "tahmin adımı yok"})
            res, actual = sinav.tahmin_calistir(app.runner_for(tid), step)
            correct = sinav.tahmin_dogru(b.get("guess", ""), res, actual)
            app.prog.guess(tid, f"{lid}:{idx}", correct)
            app.prog.visit(tid, lid, idx)
            return self._send(200, {"correct": correct, "result": res, "expected": normalize(actual)})

        def _post_visit(self, b):
            app.prog.visit(b["track"], b["lesson"], int(b["step"]), bool(b.get("done")))
            return self._send(200, {"ok": True})

        def _post_draft(self, b):
            if "playground" in b:
                app.prog.save_playground(b["playground"], b.get("dil", "python"))
            else:
                app.prog.save_draft(b["track"], f'{b["lesson"]}:{int(b["step"])}', b.get("code", ""))
            return self._send(200, {"ok": True})

        def _post_solution(self, b):
            tid, lid, idx = b["track"], b["lesson"], int(b["step"])
            _, step = app.step(tid, lid, idx)
            if step is None or not step.get("solution"):
                return self._send(404, {"error": "çözüm yok"})
            app.prog.reveal(tid, f"{lid}:{idx}")
            return self._send(200, {"solution": step["solution"]})

        # ── sınav kipi ──
        def _sinav(self, fn):
            """Sınav uçlarının hataları kullanıcıya olduğu gibi gider (\"süren bir sınav var\" gibi)."""
            try:
                return self._send(200, fn())
            except OSError:
                return self._send(404, {"error": "böyle bir yol yok"})
            except ValueError as e:
                return self._send(400, {"error": str(e)})

        def _post_sinav_havuz(self, b):
            return self._sinav(lambda: app.sinav_havuz(b))

        def _post_sinav_basla(self, b):
            return self._sinav(lambda: app.sinav_basla(b))

        def _post_sinav_cevap(self, b):
            return self._sinav(lambda: {"ok": app.prog.sinav_cevap(
                int(b["no"]), int(b["soru"]), b.get("cevap"), b.get("isaretli"), son=time.time() - sinav.GECIKME_PAYI)})

        def _post_sinav_bitir(self, b):
            return self._sinav(lambda: app.sinav_bitir(int(b["no"])))

        def _post_sinav_vazgec(self, b):
            return self._sinav(lambda: app.prog.sinav_kapat(int(b["no"])) or {"ok": True})

        def _post_sinav_tekrar(self, b):
            r = app.prog.sinav_sonucu(int(b["no"]))
            if not r:
                return self._send(404, {"error": "böyle bir sınav yok"})
            keys = [f"{q['lesson']}:{q['step']}" for q in r["sorular"] if q["kind"] == "gorev" and not q["dogru"]]
            return self._send(200, {"eklenen": app.prog.tekrara_ekle(r["yol"], keys)})

        def _post_settings(self, b):
            if b.get("key") not in ("theme", "fontsize"):
                return self._send(400, {"error": "bilinmeyen ayar"})
            app.prog.set_setting(b["key"], b.get("value"))
            return self._send(200, {"ok": True})

        def _post_rota(self, b):
            if any(k in b for k in ("hedef", "tempo", "uyelik", "baslangic")):
                return self._send(200, app.rota.hedef_guncelle(
                    b.get("hedef"), b.get("tempo"), b.get("uyelik"), b.get("baslangic"), app.state()["tracks"]))
            k = app.rota.guncelle(b["platform"], b["id"], b.get("yuzde"), b.get("sertifika"))
            return self._send(200, k)

        def _post_reset(self, b):
            if b.get("confirm") != "SIFIRLA":
                return self._send(400, {"error": "onay yok"})
            app.prog.reset()
            return self._send(200, {"ok": True})

    return Handler


def start(preferred_port=8765, token=None):
    """Sunucuyu arka planda başlatır; (app, httpd) döndürür."""
    app = App(token)
    handler = make_handler(app)
    httpd = None
    for port in (preferred_port, 0):
        try:
            httpd = ThreadingHTTPServer(("127.0.0.1", port), handler)
            break
        except OSError:
            continue
    httpd.daemon_threads = True
    app.port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return app, httpd


def main():
    ap = argparse.ArgumentParser(description="Pafta sunucusu (geliştirme modu)")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--token", default=None)
    ap.add_argument("--veri", default=None, help="ilerleme klasörü (test için)")
    args = ap.parse_args()
    if args.veri:
        os.environ["PAFTA_DATA"] = args.veri
    app, httpd = start(args.port, args.token)
    print(f"Pafta: http://127.0.0.1:{app.port}/  (veri: {data_dir()})", flush=True)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        httpd.shutdown()


if __name__ == "__main__":
    main()
