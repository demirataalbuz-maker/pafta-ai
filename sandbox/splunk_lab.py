# -*- coding: utf-8 -*-
"""SPL yolunun gerçek Splunk laboratuvarı (adım meta'sında motor: splunk).

Splunk Enterprise, Splunk'ın resmi Docker imajıyla (IMAJ, özetiyle sabit) pafta-splunk
konteynerinde çalışır. Web arayüzü ve yönetim API'si yalnız 127.0.0.1'e açılır; konteyner
--restart no ile kurulur, açılışta başlamaz. Docker Desktop'ın kendisi kullanıcı tarafından
açılmalıdır. Yönetici parolası ilk kurulumda üretilir ve .deps/splunk/parola dosyasında durur.

Bütün işler aynı laboratuvar dizinini (pafta_ders) kullanır: dizin bir kez kurulur, her işin
başında ve sonunda içindeki olaylar `| delete` ile silinir (admin'e can_delete rolü verilir;
Splunk'ta dizin silmek arka planda biter ve hemen yeniden kurulamaz). İki işin birbirinin
verisini görmemesi için işler bir dosya kilidiyle sıraya girer.

Elle hazırlamak ya da durumu görmek için:  python sandbox/splunk_lab.py
"""
import base64
import json
import os
import secrets
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KONTEYNER = "pafta-splunk"
IMAJ = "splunk/splunk:10.6.1@sha256:2a7cf9d2e8a2226773a9fac95b5e0e2cc8752496abfb134a21bdf8f67c9ee44d"
API = "https://127.0.0.1:8089"
WEB = "http://127.0.0.1:8000"
DIZIN = "pafta_ders"
BASTIRMA_PAYI = 1    # alarm üreten çalıştırmadan sonra (sn): kayıtlar bir sonraki çalıştırmadan önce yerleşsin
ONEK = "pafta_"                   # laboratuvarın kurduğu her nesnenin (sourcetype, kayıtlı arama) adı
KLASOR = os.path.join(ROOT, ".deps", "splunk")
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

_ssl = ssl.create_default_context()
_ssl.check_hostname = False
_ssl.verify_mode = ssl.CERT_NONE          # konteynerin kendi imzalı sertifikası; yalnız 127.0.0.1


class SplunkHatasi(Exception):
    pass


def dispatch_after(previous, interval, clock=time.monotonic, sleep=time.sleep):
    """Space dispatch starts, not job completion plus the requested interval.

    Native searches consume wall time too. Adding their duration to each wait
    can silently expire a short suppression period before the second dispatch.
    """
    now=clock()
    if previous is not None and interval:
        remaining=previous+interval-now
        if remaining < -interval/6:
            raise SplunkHatasi('Gerçek saat deneyi dispatch aralığını aştı; Splunk yükünü azaltıp yeniden deneyin.')
        if remaining>0:
            sleep(remaining)
            now=clock()
    return now


def verify_dispatch_window(start, interval, previous=None, clock=time.monotonic):
    """Do not show a timing prediction after backend latency ate its margin.

    SP22 uses starts 12s apart and a 20s suppression period. Keep start drift
    and consecutive response-latency jitter each within 2s; constant backend
    latency need not be zero. Overruns are explicit errors, never alternate
    'correct' predictions or emulated alarm counts.
    """
    elapsed=clock()-start
    if interval and previous is not None and abs(elapsed-previous)>interval/6:
        raise SplunkHatasi('Gerçek saat deneyi zaman payını aştı; Splunk yükünü azaltıp yeniden deneyin.')
    return elapsed


def _docker(*args, timeout=60):
    p = subprocess.run(["docker", *args], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, timeout=timeout, creationflags=NO_WINDOW)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def parola():
    yol = os.path.join(KLASOR, "parola")
    if not os.path.exists(yol):
        os.makedirs(KLASOR, exist_ok=True)
        with open(yol, "w", encoding="ascii") as f:
            f.write("Pafta-" + secrets.token_urlsafe(18))
    with open(yol, encoding="ascii") as f:
        return f.read().strip()


def istek(yol, veri=None, yontem=None, timeout=30):
    """Yönetim API'sine istek → JSON. veri bir sözlükse form olarak gönderilir."""
    url = API + yol + ("&" if "?" in yol else "?") + "output_mode=json"
    govde = urllib.parse.urlencode(veri, doseq=True).encode() if veri is not None else None
    r = urllib.request.Request(url, data=govde, method=yontem or ("POST" if govde is not None else "GET"))
    r.add_header("Authorization", "Basic " + base64.b64encode(f"admin:{parola()}".encode()).decode())
    try:
        with urllib.request.urlopen(r, context=_ssl, timeout=timeout) as y:
            icerik = y.read()
    except urllib.error.HTTPError as e:
        icerik = e.read()
        try:
            mesaj = "; ".join(m.get("text", "") for m in json.loads(icerik).get("messages", []))
        except ValueError:
            mesaj = icerik.decode("utf-8", "replace")[:300]
        raise SplunkHatasi(f"{e.code} {yol}: {mesaj}") from None
    return json.loads(icerik) if icerik.strip() else {}


def _api_acik():
    try:
        istek("/services/server/info", timeout=5)
        return True
    except (OSError, SplunkHatasi):
        return False


def durum():
    """'docker-yok' | 'yok' | 'durdu' | 'calisiyor'"""
    try:
        kod, out, _ = _docker("inspect", "-f", "{{.State.Running}}", KONTEYNER, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return "docker-yok"
    if kod != 0:
        kod, _, _ = _docker("info", "--format", "{{.ServerVersion}}", timeout=20)
        return "yok" if kod == 0 else "docker-yok"
    return "calisiyor" if out.strip() == "true" else "durdu"


def available():
    return durum() in ("yok", "durdu", "calisiyor")


def hazirla(bekle=600):
    """Konteyneri gerekirse kur ya da başlat, API açılana kadar bekle. Sorun yoksa None, varsa açıklama."""
    d = durum()
    if d == "docker-yok":
        return "Docker çalışmıyor: Docker Desktop'ı aç, sonra yeniden dene."
    if d == "yok":
        kod, _, err = _docker(
            "run", "-d", "--name", KONTEYNER, "--restart", "no", "--hostname", "pafta-splunk",
            "-p", "127.0.0.1:8000:8000", "-p", "127.0.0.1:8089:8089",
            "-e", "SPLUNK_START_ARGS=--accept-license",
            "-e", "SPLUNK_GENERAL_TERMS=--accept-sgt-current-at-splunk-com",
            "-e", "SPLUNK_PASSWORD=" + parola(), "-e", "TZ=UTC",
            "-v", "pafta-splunk-etc:/opt/splunk/etc", "-v", "pafta-splunk-var:/opt/splunk/var",
            IMAJ, timeout=300)
        if kod != 0:
            return f"Splunk konteyneri kurulamadı: {err.strip()[-400:]}"
    elif d == "durdu":
        kod, _, err = _docker("start", KONTEYNER, timeout=120)
        if kod != 0:
            return f"Splunk konteyneri başlatılamadı: {err.strip()[-400:]}"
    son = time.time() + bekle
    while time.time() < son:
        if _api_acik():
            return None
        time.sleep(3)
    return f"Splunk API'si {bekle} saniyede açılmadı ({API}); docker logs {KONTEYNER} ile bak."


CIM_MODELLER = ("Authentication", "Web", "Network_Traffic", "Endpoint", "Change")


def cim_kurulu():
    try:
        istek("/services/apps/local/Splunk_SA_CIM")
        return True
    except SplunkHatasi:
        return False


def _dizin_kur():
    try:
        icerik = istek(f"/services/data/indexes/{DIZIN}")["entry"][0]["content"]
        if icerik.get("disabled"):
            istek(f"/services/data/indexes/{DIZIN}/enable", {})
    except SplunkHatasi as e:
        if not str(e).startswith("404"):
            raise
        istek("/services/data/indexes", {"name": DIZIN, "datatype": "event"})
    if cim_kurulu():
        # CIM veri modelleri olayları `cim_<model>_indexes` makrosundaki dizinlerde arar; laboratuvarın dizini
        for model in CIM_MODELLER:
            istek(f"/servicesNS/nobody/Splunk_SA_CIM/configs/conf-macros/cim_{model}_indexes",
                  {"definition": f"(index={DIZIN})"})
    roller = istek("/services/authentication/users/admin")["entry"][0]["content"]["roles"]
    if "can_delete" not in roller:
        istek("/services/authentication/users/admin", {"roles": roller + ["can_delete"]})


# ── iş başına laboratuvar ──

def _yasiyor(pid):
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        k = ctypes.windll.kernel32
        tutamac = k.OpenProcess(0x00100000, False, pid)          # SYNCHRONIZE
        if not tutamac:
            return False
        try:
            return k.WaitForSingleObject(tutamac, 0) == 0x102      # WAIT_TIMEOUT: süreç çalışıyor
        finally:
            k.CloseHandle(tutamac)
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


class _Kilit:
    """İşleri süreçler arasında sıraya sokar (validate aynı anda birçok iş çalıştırabilir)."""

    def __init__(self, timeout=900):
        self.yol = os.path.join(KLASOR, "kilit")
        self.timeout = timeout

    def __enter__(self):
        os.makedirs(KLASOR, exist_ok=True)
        son = time.time() + self.timeout
        while True:
            try:
                self.fd = os.open(self.yol, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(self.fd, str(os.getpid()).encode())
                return self
            except FileExistsError:
                try:
                    with open(self.yol, encoding="ascii") as f:
                        icerik = f.read().strip()            # boşsa kilit henüz yazılıyor
                    if (icerik and not _yasiyor(int(icerik))) or time.time() - os.path.getmtime(self.yol) > self.timeout:
                        os.remove(self.yol)            # çökmüş ya da kesilmiş bir işten kalan kilit
                        continue
                except (OSError, ValueError):
                    pass
                if time.time() > son:
                    raise SplunkHatasi("Splunk laboratuvarı başka bir işle meşgul (kilit zaman aşımı)")
                time.sleep(0.5)

    def __exit__(self, *a):
        os.close(self.fd)
        try:
            os.remove(self.yol)
        except OSError:
            pass


def _ara(spl, en_cok=10000, timeout=120):
    """Aramayı bitene kadar çalıştır → (alanlar, satırlar[dict]). Arama hatası SplunkHatasi olur."""
    arama = spl.strip()
    if not arama.startswith("|") and not arama.lower().startswith("search "):
        arama = "search " + arama
    is_ = istek("/services/search/jobs", {"search": arama, "exec_mode": "blocking",
                                          "earliest_time": "0", "latest_time": "+10y", "timeout": "60"},
                timeout=timeout)
    sid = is_["sid"]
    try:
        bilgi = istek(f"/services/search/jobs/{sid}")["entry"][0]["content"]
        hatalar = [m["text"] for m in bilgi.get("messages", []) if m.get("type") in ("FATAL", "ERROR")]
        if bilgi.get("isFailed") or hatalar:
            raise SplunkHatasi("; ".join(hatalar) or "arama başarısız")
        sonuc = istek(f"/services/search/jobs/{sid}/results?count={en_cok}", timeout=timeout)
        alanlar = [a["name"] if isinstance(a, dict) else a for a in sonuc.get("fields", [])]
        return alanlar, sonuc.get("results", [])
    finally:
        try:
            istek(f"/services/search/jobs/{sid}", yontem="DELETE")
        except (OSError, SplunkHatasi):
            pass


class Lab:
    """Bir işin Splunk ortamı: temiz pafta_ders dizini, pafta_ önekli sourcetype ve kayıtlı aramalar.
    with bloğu bitince hepsi silinir."""

    def __init__(self):
        self._kilit = _Kilit()
        self.sourcetypelar = set()
        self.aramalar = set()

    def __enter__(self):
        self._kilit.__enter__()
        try:
            _dizin_kur()
            self._temizle()
        except Exception:
            self._kilit.__exit__()
            raise
        return self

    def __exit__(self, *a):
        try:
            self._temizle()
        finally:
            self._kilit.__exit__()

    def _temizle(self):
        for ad in self._kayitli("/servicesNS/nobody/search/saved/searches"):
            istek(f"/servicesNS/nobody/search/saved/searches/{urllib.parse.quote(ad, safe='')}", yontem="DELETE")
        for dosya in ("props", "eventtypes"):
            for ad in self._kayitli(f"/servicesNS/nobody/search/configs/conf-{dosya}"):
                istek(f"/servicesNS/nobody/search/configs/conf-{dosya}/{urllib.parse.quote(ad, safe='')}", yontem="DELETE")
        etiketler = istek("/servicesNS/nobody/search/configs/conf-tags?count=0").get("entry", [])
        for e in etiketler:                      # tags.conf kıtası "alan=değer"; değer laboratuvarınsa sil
            if ONEK in e["name"] and e.get("acl", {}).get("app") == "search":
                istek(f"/servicesNS/nobody/search/configs/conf-tags/{urllib.parse.quote(e['name'], safe='')}", yontem="DELETE")
        son = time.time() + 60
        while self.say():                        # geç ulaşan olay kalmasın: dizin gerçekten boşalana kadar
            if time.time() > son:
                raise SplunkHatasi(f"{DIZIN} dizini boşaltılamadı")
            _ara(f"search index={DIZIN} | delete")
            time.sleep(1)

    def bosalt(self):
        """Olayları, pafta_ önekli props kıtalarını ve kayıtlı aramaları sil (testin dene()'si için)."""
        self._temizle()

    def _kayitli(self, yol):
        veri = istek(yol + "?count=0&search=" + urllib.parse.quote(f"name={ONEK}*"))
        return [e["name"] for e in veri.get("entry", []) if e["name"].startswith(ONEK)
                and e.get("acl", {}).get("app") == "search"]

    # — görev hazırlığının ve testlerin kullandığı işlemler —

    def props(self, sourcetype, ayarlar):
        """props.conf'ta [sourcetype] kıtası (search uygulamasında)."""
        if not sourcetype.startswith(ONEK):
            raise SplunkHatasi(f"laboratuvarın sourcetype adları {ONEK} ile başlamalı: {sourcetype}")
        yol = "/servicesNS/nobody/search/configs/conf-props"
        try:
            istek(f"{yol}/{urllib.parse.quote(sourcetype, safe='')}", yontem="DELETE")
        except SplunkHatasi:
            pass
        istek(yol, dict({"name": sourcetype}, **ayarlar))
        istek("/servicesNS/nobody/search/configs/conf-props/_reload")
        self.sourcetypelar.add(sourcetype)

    def props_ekle(self, sourcetype, ayarlar):
        """Var olan [sourcetype] kıtasına ayar ekle ya da değiştir (yoksa kur); hazırlığın ayarları korunur."""
        if not sourcetype.startswith(ONEK):
            raise SplunkHatasi(f"laboratuvarın sourcetype adları {ONEK} ile başlamalı: {sourcetype}")
        yol = "/servicesNS/nobody/search/configs/conf-props"
        try:
            istek(f"{yol}/{urllib.parse.quote(sourcetype, safe='')}", ayarlar)
        except SplunkHatasi as e:
            if not str(e).startswith("404"):
                raise
            istek(yol, dict({"name": sourcetype}, **ayarlar))
        istek(f"{yol}/_reload")

    def olay_turu(self, ad, arama, **ek):
        """eventtypes.conf'ta [ad] kıtası."""
        if not ad.startswith(ONEK):
            raise SplunkHatasi(f"laboratuvarın olay türü adları {ONEK} ile başlamalı: {ad}")
        yol = "/servicesNS/nobody/search/configs/conf-eventtypes"
        try:
            istek(f"{yol}/{urllib.parse.quote(ad, safe='')}", yontem="DELETE")
        except SplunkHatasi:
            pass
        istek(yol, dict(ek, name=ad, search=arama))

    def etiket(self, alan_deger, ayarlar):
        """tags.conf'ta [alan=değer] kıtası; ayarlar {etiket: enabled|disabled}. Değer pafta_ önekli olmalı."""
        if ONEK not in alan_deger.split("=", 1)[-1]:
            raise SplunkHatasi(f"laboratuvarın etiket kıtası pafta_ önekli bir değere bağlanmalı: [{alan_deger}]")
        yol = "/servicesNS/nobody/search/configs/conf-tags"
        try:
            istek(f"{yol}/{urllib.parse.quote(alan_deger, safe='')}", yontem="DELETE")
        except SplunkHatasi:
            pass
        istek(yol, dict(ayarlar, name=alan_deger))

    def yukle(self, metin, sourcetype, kaynak="ders.log"):
        """Ham metni bir dosya olarak konteynere koyup tek seferlik girişle (oneshot) dizine al;
        olaylar aranabilir olana kadar bekle → alınan olay sayısı."""
        if not sourcetype.startswith(ONEK):
            raise SplunkHatasi(f"laboratuvarın sourcetype adları {ONEK} ile başlamalı: {sourcetype}")
        ad = f"{secrets.token_hex(4)}_{os.path.basename(kaynak)}"
        hedef = f"/tmp/pafta/{ad}"
        yerel = os.path.join(KLASOR, "aktar_" + ad)
        with open(yerel, "w", encoding="utf-8", newline="") as f:
            f.write(metin)
        try:
            _docker("exec", "-u", "root", KONTEYNER, "mkdir", "-p", "/tmp/pafta", timeout=60)
            kod, _, err = _docker("cp", yerel, f"{KONTEYNER}:{hedef}", timeout=120)
            if kod != 0:
                raise SplunkHatasi("dosya konteynere kopyalanamadı: " + err.strip()[-300:])
            _docker("exec", "-u", "root", KONTEYNER, "chmod", "644", hedef, timeout=60)
        finally:
            os.remove(yerel)
        once = self.say()
        istek("/services/data/inputs/oneshot", {"name": hedef, "index": DIZIN, "sourcetype": sourcetype,
                                                "rename-source": kaynak})
        son = time.time() + 120                 # tek seferlik giriş dosyayı bitirince listeden düşer
        while any(e["name"] == hedef for e in istek("/services/data/inputs/oneshot?count=0").get("entry", [])):
            if time.time() > son:
                raise SplunkHatasi(f"{kaynak} 120 saniyede dizine alınamadı")
            time.sleep(0.5)
        return self._bekle_dizin(once) - once

    def _bekle_dizin(self, once, timeout=90):
        """Olay sayısı değişip 3 saniye durağan kalana kadar bekle."""
        son, onceki, sabit = time.time() + timeout, -1, 0
        while time.time() < son:
            n = self.say()
            if n == onceki and n != once:
                sabit += 1
                if sabit >= 3:
                    return n
            else:
                sabit = 0
            onceki = n
            time.sleep(1)
        return onceki

    def say(self):
        _, satirlar = _ara(f"search index={DIZIN} | stats count")
        return int(satirlar[0]["count"]) if satirlar else 0

    def ara(self, spl, en_cok=10000):
        return _ara(spl, en_cok)

    # — zamanlanmış aramalar (alarm) —

    def kural(self, ad, ayarlar):
        """savedsearches.conf'ta bir kıta kur → Splunk'taki adı. Ad her işte yenidir: Splunk bastırma
        durumunu kayıtlı aramanın adına bağlar, eski bir işin bastırması yeni işe sızmasın.
        Gerçek zamanlayıcı kuralı kendiliğinden çalıştırmasın diye takvim yılda bire çekilir;
        çalıştırma anlarını laboratuvar dispatch.now ile verir (calistir)."""
        if not ad.startswith(ONEK):
            raise SplunkHatasi(f"laboratuvarın kayıtlı arama adları {ONEK} ile başlamalı: {ad}")
        ic_ad = f"{ad}_{secrets.token_hex(3)}"
        istek("/servicesNS/nobody/search/configs/conf-savedsearches",
              dict(ayarlar, name=ic_ad, enableSched="1", cron_schedule="0 0 1 1 *", disabled="0"))
        istek("/servicesNS/nobody/search/saved/searches/_reload")
        self.aramalar.add(ic_ad)
        return ic_ad

    def calistir(self, ic_ad, an):
        """Kuralı `an` (epoch) zamanlayıcının o anda çalıştırmış gibi çalıştır, alarm eylemleriyle →
        (sid, pencere başı, pencere sonu, teslim edilen sonuçlar). Bastırılan sonuçlar teslim edilmez."""
        r = istek(f"/servicesNS/nobody/search/saved/searches/{urllib.parse.quote(ic_ad, safe='')}/dispatch",
                  {"trigger_actions": "1", "dispatch.now": str(int(an))})
        sid = r["sid"]
        son = time.time() + 120
        visible_until = time.monotonic() + 10
        while True:
            try:
                c = istek(f"/services/search/jobs/{sid}")["entry"][0]["content"]
            except SplunkHatasi as exc:
                # Dispatch returns before its SID is always visible to the
                # status endpoint. Retry only that initial 404, boundedly;
                # authentication/product failures must never become empty data.
                if str(exc).startswith('404 ') and time.monotonic()<visible_until:
                    time.sleep(0.2)
                    continue
                raise
            visible_until = 0
            if c.get("isDone"):
                break
            if time.time() > son:
                raise SplunkHatasi(f"kural {ic_ad} 120 saniyede bitmedi")
            time.sleep(0.5)
        hatalar = [m["text"] for m in c.get("messages", []) if m.get("type") in ("FATAL", "ERROR")]
        if c.get("isFailed") or hatalar:
            raise SplunkHatasi("; ".join(hatalar) or "kuralın araması başarısız")
        sonuc = istek(f"/services/search/jobs/{sid}/results?count=1000")
        alanlar = [a["name"] if isinstance(a, dict) else a for a in sonuc.get("fields", [])]
        if int(c.get("resultCount") or 0):
            time.sleep(BASTIRMA_PAYI)   # alarm ve bastırma kaydı bir sonraki çalıştırmadan önce yerleşsin
        return sid, c.get("earliestTime"), c.get("latestTime"), alanlar, sonuc.get("results", [])

    def zamanlayici(self, ic_ad, sidler, timeout=90):
        """Her çalıştırmanın kaydı → {sid: (sonuç sayısı, tetiklenen alarm, bastırılan)}. Sonuç ve bastırma
        zamanlayıcı günlüğünden (_internal), tetiklenen alarmlar denetim günlüğünden (_audit alert_fired)
        okunur: özet modunda (alert.digest_mode = 1) zamanlayıcı günlüğü tetiklenmeyi yazmaz."""
        son = time.time() + timeout
        while True:
            _, satirlar = _ara(f"search index=_internal sourcetype=scheduler savedsearch_name={ic_ad} "
                               "| table sid result_count suppressed")
            kayit = {s["sid"]: (int(s.get("result_count") or 0), int(s.get("suppressed") or 0)) for s in satirlar}
            if all(sid in kayit for sid in sidler):
                break
            if time.time() > son:
                raise SplunkHatasi("zamanlayıcı günlüğünde çalıştırma kayıtları bulunamadı")
            time.sleep(1)
        time.sleep(2)                                   # denetim kaydı aynı anda yazılır; dizine ulaşsın
        _, satirlar = _ara(f"search index=_audit action=alert_fired ss_name={ic_ad} "
                           "| stats sum(triggered_alerts) AS n by sid")
        tetik = {s["sid"]: int(s.get("n") or 0) for s in satirlar}
        return {sid: (kayit[sid][0], tetik.get(sid, 0), kayit[sid][1]) for sid in sidler}


if __name__ == "__main__":
    print("durum:", durum())
    sorun = hazirla()
    if sorun:
        print(sorun)
        sys.exit(1)
    bilgi = istek("/services/server/info")["entry"][0]["content"]
    print(f"Splunk {bilgi['version']} hazır · {WEB} (kullanıcı admin, parola {os.path.join(KLASOR, 'parola')})")
    print("lisans:", bilgi.get("activeLicenseGroup"))
