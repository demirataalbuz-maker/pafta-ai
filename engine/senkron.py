# -*- coding: utf-8 -*-
"""İki makine arası ilerleme senkronu (özel GitHub gist üzerinden).

İlerleme (progress.json) repo DIŞINDA, %LOCALAPPDATA%\\Pafta altında tutulur
(bkz. engine/progress.py). Bu modül onu GitHub'daki ÖZEL bir gist ile çift
yönlü eşitler. Kod git ile, ilerleme gist ile gezer — ikisi ayrı kanal.

Pafta'yı kapattıktan sonra çalıştır. İki bilgisayardan aynı anda eşitleme yapma:
Gist güncellemesi dağıtık bir işlem/CAS kilidi sağlamaz. Yerel ve uzak anlık
görüntüler yazımdan önce profile yedeklenir. Birleştirme kuralı:
  * Tamamlanan dersler (steps.done) ve çalışma günleri (days) BİRLEŞTİRİLİR —
    bir ders hangi makinede bitirildiyse bitti sayılır, geri dönmez.
  * Tekrar kutuları (review): daha yüksek kutu; eşitse daha yakın tarih.
  * Taslak/ayar/playground: çakışmada yerel kazanır (bu makinede yazılan).
  * Sınav geçmişi: içerik kimliğiyle birleştirilir; çakışan yerel numaralar
    yeniden atanır, aktif sınav yerelde kalır. Son 30 kayıt tutulur.

Kullanım (repo kökünden):
    python -m engine.senkron durum     # yapılandırma + yerel/uzak özet
    python -m engine.senkron kur       # ilk kez: gist oluştur ya da bağla
    python -m engine.senkron cek       # gist -> yerel (birleştir)
    python -m engine.senkron yolla     # yerel -> gist
    python -m engine.senkron esitle    # cek + yolla (önerilen tek komut)

Gereken: `gh` (GitHub CLI) kurulu ve yetkili. Gist kimliği
%LOCALAPPDATA%\\Pafta\\senkron.json içinde {"gist": "..."}; PAFTA_GIST ortam
değişkeni varsa onu kullanır.
"""
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from engine.progress import data_dir  # noqa: E402

BOS = {"version": 1, "days": [], "last": None, "tracks": {},
       "playground": "", "settings": {"theme": "mavi"}}


# ── yerel dosya ──
def local_path():
    return os.path.join(data_dir(), "progress.json")


def cfg_path():
    return os.path.join(data_dir(), "senkron.json")


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return copy.deepcopy(default)


def save_atomik(path, data):
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".senkron-", suffix=".tmp", dir=parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def offline_gerekli():
    """The normal launcher caches Progress; never replace its file while live."""
    instance = load_json(os.path.join(data_dir(), "instance.json"), {})
    if not instance:
        return
    port, token = instance.get("port"), instance.get("token")
    if type(port) is not int or not 1 <= port <= 65535 or not isinstance(token, str):
        raise ValueError("instance.json geçersiz; açık Pafta durumunu doğrulayamıyorum")
    request = urllib.request.Request(f"http://127.0.0.1:{port}/api/ping",
                                     headers={"X-Pafta-Token": token})
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=2):
            pass
    except urllib.error.HTTPError:
        # Another app/token can occupy the port. Fail closed instead of guessing.
        raise RuntimeError("Pafta portu yanıt veriyor; senkron öncesi Pafta'yı kapat") from None
    except (urllib.error.URLError, OSError):
        return  # stale launcher instance; no listener
    raise RuntimeError("Pafta açık. Kapatıp sunucu durduktan sonra eşitle; bellekteki ilerleme kaydı ezebilir.")


def yedekle(data, kaynak):
    """Local only; never writes backup to the repository or another service."""
    folder = os.path.join(data_dir(), "senkron-yedekleri")
    path = os.path.join(folder, kaynak + "-" + uuid.uuid4().hex + ".json")
    save_atomik(path, data)
    return path


def gist_id():
    return os.environ.get("PAFTA_GIST") or load_json(cfg_path(), {}).get("gist")


# ── gh (GitHub CLI) ──
def _gh(args, govde=None):
    try:
        p = subprocess.run(["gh"] + args, input=govde,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        raise SystemExit("gh (GitHub CLI) kurulu değil → https://cli.github.com")
    if p.returncode != 0:
        hata = (p.stderr or b"").decode("utf-8", "replace").strip()
        if "auth" in hata.lower() or "logged" in hata.lower():
            raise SystemExit("gh yetkili değil → `gh auth login` çalıştır.")
        raise SystemExit("gh hata: " + hata)
    return (p.stdout or b"").decode("utf-8", "replace")


def remote_get(gist):
    d = json.loads(_gh(["api", f"gists/{gist}"]))
    if d.get("public") is True:
        raise ValueError("Bu gist herkese açık; ilerleme için gizli gist kullan")
    dosya = (d.get("files") or {}).get("progress.json")
    if not dosya or not dosya.get("content"):
        return None
    if dosya.get("truncated"):
        raise ValueError("GitHub ilerleme içeriğini kırptı; kısmi veriyle eşitleme yapılmadı")
    return json.loads(dosya["content"])


def _govde(data, **ek):
    icerik = json.dumps(data, ensure_ascii=False, indent=1)
    govde = dict(ek, files={"progress.json": {"content": icerik}})
    return json.dumps(govde).encode("utf-8")


def remote_put(gist, data):
    _gh(["api", "-X", "PATCH", f"gists/{gist}", "--input", "-"], govde=_govde(data))


def remote_create(data):
    out = _gh(["api", "-X", "POST", "gists", "--input", "-"],
              govde=_govde(data, public=False, description="Pafta ilerleme senkronu"))
    return json.loads(out)["id"]


# ── birleştirme ──
def _merge_step(a, b):
    out = dict(b)
    out.update(a)
    if a.get("done") or b.get("done"):
        out["done"] = True
        atlar = [x.get("at") for x in (a, b) if x.get("at")]
        if atlar:
            out["at"] = min(atlar)          # ilk tamamlama anı
    out["attempts"] = max(a.get("attempts", 0), b.get("attempts", 0))
    if a.get("revealed") or b.get("revealed"):
        out["revealed"] = True
    if "guess_ok" in a or "guess_ok" in b:
        out["guess_ok"] = a.get("guess_ok", b.get("guess_ok"))
    return out


def _merge_review(a, b):
    if not a:
        return dict(b or {})
    if not b:
        return dict(a)
    if a.get("box", 0) != b.get("box", 0):            # daha ilerlemiş kutu
        return dict(a if a.get("box", 0) > b.get("box", 0) else b)
    return dict(a if a.get("due", "9999") <= b.get("due", "9999") else b)  # daha yakın tekrar


def merge(yerel, uzak):
    m = copy.deepcopy(yerel)
    m["version"] = max(yerel.get("version", 1), uzak.get("version", 1))
    m["days"] = sorted(set(yerel.get("days", [])) | set(uzak.get("days", [])))
    m["last"] = yerel.get("last")

    yt, ut = yerel.get("tracks", {}), uzak.get("tracks", {})
    mt = {}
    for tid in set(yt) | set(ut):
        a, b = yt.get(tid, {}), ut.get(tid, {})
        steps = {}
        sa, sb = a.get("steps", {}), b.get("steps", {})
        for k in set(sa) | set(sb):
            steps[k] = _merge_step(sa.get(k, {}), sb.get(k, {}))
        review = {}
        ra, rb = a.get("review", {}), b.get("review", {})
        for k in set(ra) | set(rb):
            review[k] = _merge_review(ra.get(k), rb.get(k))
        drafts = dict(b.get("drafts", {}))
        drafts.update(a.get("drafts", {}))          # çakışmada yerel
        track = copy.deepcopy(b)
        track.update(copy.deepcopy(a))
        track.update(steps=steps, drafts=drafts, review=review)
        mt[tid] = track
    m["tracks"] = mt

    if not yerel.get("playground") and uzak.get("playground"):
        m["playground"] = uzak["playground"]
    pd = dict(uzak.get("playground_diller", {}))
    pd.update(yerel.get("playground_diller", {}))
    if pd:
        m["playground_diller"] = pd
    ayar = dict(uzak.get("settings", {}))
    ayar.update(yerel.get("settings", {}))          # çakışmada yerel
    m["settings"] = ayar

    ys, us = yerel.get("sinav"), uzak.get("sinav")
    if ys or us:
        ys, us = ys or {}, us or {}
        gec, kullanilan = {}, set()
        if isinstance(ys.get("aktif"), dict):
            kullanilan.add(ys["aktif"]["no"])
        en_son = max(ys.get("sayac", 0), us.get("sayac", 0),
                     *(g.get("no", 0) for g in ys.get("gecmis", []) + us.get("gecmis", [])), 0)
        # Preserve local UI ids; give a distinct imported exam a free numeric id.
        for g in (ys.get("gecmis", []) + us.get("gecmis", [])):
            if not isinstance(g, dict) or "no" not in g:
                continue
            record = copy.deepcopy(g)
            content = {k: v for k, v in record.items() if k not in ("no", "_sync_id", "_onceki_no")}
            identity = record.get("_sync_id") or hashlib.sha256(
                json.dumps(content, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
            if identity in gec:
                continue
            record["_sync_id"] = identity
            if record["no"] in kullanilan:
                en_son += 1
                record["_onceki_no"], record["no"] = record["no"], en_son
            kullanilan.add(record["no"])
            gec[identity] = record
        m["sinav"] = {"aktif": ys.get("aktif"),
                      "gecmis": sorted(gec.values(), key=lambda g: g.get("no", 0), reverse=True)[:30],
                      "sayac": max(en_son, *kullanilan, 0)}
    return m


def tamamlanan(data):
    return sum(1 for t in data.get("tracks", {}).values()
               for s in t.get("steps", {}).values() if s.get("done"))


# ── komutlar ──
def kur():
    gid = gist_id()
    if gid:
        print(f"Zaten bağlı: gist {gid}")
        return gid
    yerel = load_json(local_path(), BOS)
    gid = remote_create(yerel)
    save_atomik(cfg_path(), {"gist": gid})
    print(f"Oluşturuldu ve bağlandı: gist {gid}")
    print("Diğer makinede bağlamak için: PAFTA_GIST=%s (ya da senkron.json'a yaz)" % gid)
    return gid


def cek():
    offline_gerekli()
    gid = gist_id()
    if not gid:
        raise SystemExit("Gist bağlı değil → önce `python -m engine.senkron kur`")
    uzak = remote_get(gid)
    yerel = load_json(local_path(), BOS)
    if uzak is None:
        print("Uzakta veri yok; yerel korunuyor.")
        return yerel
    once = tamamlanan(yerel)
    m = merge(yerel, uzak)
    yedekle(yerel, "yerel")
    yedekle(uzak, "uzak")
    offline_gerekli()
    save_atomik(local_path(), m)
    print(f"Çekildi + birleşti. Tamamlanan ders: {once} → {tamamlanan(m)} "
          f"(uzak {tamamlanan(uzak)}). Gün: {len(m['days'])}")
    return m


def yolla():
    offline_gerekli()
    gid = gist_id()
    if not gid:
        raise SystemExit("Gist bağlı değil → önce `python -m engine.senkron kur`")
    yerel = load_json(local_path(), BOS)
    uzak = remote_get(gid)
    m = merge(yerel, uzak) if uzak is not None else yerel
    yedekle(yerel, "yerel")
    if uzak is not None:
        yedekle(uzak, "uzak")
    offline_gerekli()
    remote_put(gid, m)
    save_atomik(local_path(), m)
    print(f"Yollandı + birleşti. Tamamlanan ders: {tamamlanan(m)}, gün: {len(m['days'])}")


def esitle():
    cek()
    yolla()
    print("Eşitlendi (iki yön).")


def durum():
    gid = gist_id()
    yerel = load_json(local_path(), BOS)
    print(f"Gist: {gid or '(bağlı değil)'}")
    print(f"Yerel: {tamamlanan(yerel)} ders tamam, {len(yerel.get('days', []))} gün, "
          f"dosya: {local_path()}")
    if gid:
        try:
            uzak = remote_get(gid)
            print(f"Uzak:  {tamamlanan(uzak) if uzak else 0} ders tamam"
                  + ("" if uzak else " (boş)"))
        except SystemExit as e:
            print(f"Uzak:  okunamadı ({e})")


KOMUTLAR = {"durum": durum, "kur": kur, "cek": cek, "yolla": yolla, "esitle": esitle}

if __name__ == "__main__":
    komut = sys.argv[1] if len(sys.argv) > 1 else "durum"
    if komut not in KOMUTLAR:
        raise SystemExit(f"Bilinmeyen komut: {komut}. Seçenekler: {', '.join(KOMUTLAR)}")
    KOMUTLAR[komut]()
