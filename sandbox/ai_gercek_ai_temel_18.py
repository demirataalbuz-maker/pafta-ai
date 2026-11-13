# -*- coding: utf-8 -*-
"""ai-temel-18 gerçek deneyi: model servisini saran konteynerin kaynak ve izolasyon sınırları gerçekten
uygulanıyor mu. Öğrenci sertleştirme bayraklarını (docker run flag'leri) üretir; deney bu bayraklarla
GERÇEK busybox konteyneri çalıştırır, konteynerin İÇİNDEN cgroup limitlerini okur (memory.max, pids.max),
dış ağ ve kök dosya sistemine yazmayı dener, sonucu sınırsız bir taban koşusuyla karşılaştırır.

Her şey yereldir ve zararsızdır; konteynerler --rm ile silinir, imaj ders sırasında indirilmez.
"""
import re
import subprocess

import ai_lab

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
IMAJ = "busybox:1.36"
# Deneyin kullandığı sertleştirme hedefi (öğrencinin sertlestirme_argv'si bunu üretmeli)
SPEC = {"imaj": IMAJ, "bellek_mb": 32, "pids": 16, "cpus": 0.5, "ag": False, "salt_okunur": True, "yetki_dus": True}
KONTROLLER = ("ag", "bellek", "dosya", "pids")

# Konteyner içinde tek seferde bütün sinyalleri toplayan betik (hiçbir şey yazmaz; yalnız dener)
PROBE = (
    'echo "MEM=$(cat /sys/fs/cgroup/memory.max 2>/dev/null || echo yok)"; '
    'echo "PIDS=$(cat /sys/fs/cgroup/pids.max 2>/dev/null || echo yok)"; '
    'echo "IF=$(ls /sys/class/net 2>/dev/null | tr \'\\n\' \' \')"; '
    'if touch /pafta_write_test 2>/dev/null; then echo WRITE=ok; rm -f /pafta_write_test; else echo WRITE=red; fi; '
    'if wget -T 2 -q -O /dev/null http://1.1.1.1 2>/dev/null; then echo NET=ok; else echo NET=red; fi'
)


def referans_argv(spec, *, swap=True, pids=True, ag=True, salt=True, yetki=True, cpu=True):
    """Doğru sertleştirme bayrakları (varsayılanlarla) ve testlerin kullandığı eksik/hatalı varyantlar.
    Girdinin geçerli olduğu varsayılır; doğrulamayı öğrenci ve testteki sarmalayıcı yapar."""
    f = [f"--memory={spec['bellek_mb']}m"]
    if swap:
        f.append(f"--memory-swap={spec['bellek_mb']}m")
    if cpu and spec.get("cpus") is not None:
        f.append(f"--cpus={spec['cpus']}")
    if pids:
        f.append(f"--pids-limit={spec['pids']}")
    if ag and not spec["ag"]:
        f.append("--network=none")
    if salt and spec["salt_okunur"]:
        f.append("--read-only")
    if yetki and spec["yetki_dus"]:
        f.append("--cap-drop=ALL")
        f.append("--security-opt=no-new-privileges")
    return f


def referans_karar(gozlem):
    """Ham gözlemden hangi denetimin uygulandığı (görev 2'nin referansı)."""
    return {"bellek": gozlem["memory_max"] is not None,
            "pids": gozlem["pids_max"] is not None,
            "ag": set(gozlem["arayuzler"]) <= {"lo"} and gozlem["ag"] == "red",
            "dosya": gozlem["yazma"] == "red"}


def _docker_var():
    try:
        p = subprocess.run(["docker", "version", "--format", "{{.Server.Version}}"],
                           capture_output=True, text=True, timeout=20, creationflags=NO_WINDOW)
    except FileNotFoundError as e:
        raise ai_lab.GercekLabYok("docker bulunamadı (PATH). Kurulum: https://docs.docker.com/get-docker/") from e
    except Exception as e:
        raise ai_lab.GercekLabYok(f"docker çağrılamadı: {type(e).__name__}") from e
    if p.returncode != 0 or not p.stdout.strip():
        raise ai_lab.GercekLabYok("Docker daemon çalışmıyor (Docker Desktop kapalı). Başlat ve tekrar dene. "
                                  f"Hata: {(p.stderr or '').strip()[:160]}")
    return p.stdout.strip()


def _imaj_var():
    p = subprocess.run(["docker", "image", "inspect", IMAJ], capture_output=True, text=True,
                       timeout=20, creationflags=NO_WINDOW)
    if p.returncode != 0:
        raise ai_lab.GercekLabYok(f"{IMAJ} imajı yerelde yok (ders sırasında indirilmez). Kurulum: docker pull {IMAJ}")


def _calistir(flaglar, komut, sure=40):
    tam = ["docker", "run", "--rm"] + list(flaglar) + [IMAJ] + list(komut)
    p = subprocess.run(tam, capture_output=True, text=True, timeout=sure, creationflags=NO_WINDOW)
    return {"cikis": p.returncode, "stdout": p.stdout, "stderr": p.stderr}


def _coz(stdout):
    """Probe çıktısını gözlem sözlüğüne çevirir."""
    d = {}
    for satir in stdout.splitlines():
        if "=" in satir:
            a, _, b = satir.partition("=")
            d[a.strip()] = b.strip()
    def bayt(v):
        return None if v in (None, "", "max", "yok") else int(v)
    return {"memory_max": bayt(d.get("MEM")), "pids_max": bayt(d.get("PIDS")),
            "arayuzler": d.get("IF", "").split(), "yazma": d.get("WRITE"), "ag": d.get("NET")}


def gozlemle(flaglar):
    r = _calistir(flaglar, ["sh", "-c", PROBE])
    g = _coz(r["stdout"])
    g["_cikis"] = r["cikis"]
    g["_stderr"] = r["stderr"][:300]
    return g


def deney(sertlestirme_argv):
    _docker_var()
    _imaj_var()
    spec = dict(SPEC)
    argv_sert = sertlestirme_argv(dict(spec))
    argv_ref = referans_argv(dict(spec))
    g_sert = gozlemle(argv_sert)
    g_baz = gozlemle([])  # sınırsız taban: blast radius'u gösterir
    k_sert = referans_karar(g_sert)
    k_baz = referans_karar(g_baz)
    # pids sınırı fork'u gerçekten engelliyor mu (ikincil gösterim)
    fork = _calistir(argv_sert, ["sh", "-c", "i=0; while [ $i -lt 40 ]; do sleep 2 & i=$((i+1)); done; echo bitti"], sure=25)
    fork_engellendi = "can't fork" in (fork["stderr"] + fork["stdout"]).lower()
    surum = _docker_var()
    return {"ortam": {"kaynak": "gercek", "arac": "docker", "docker_surumu": surum, "imaj": IMAJ,
                      "cgroup_surum": "v2" if g_sert["memory_max"] is not None or g_baz["memory_max"] is None else "?"},
            "spec": spec, "argv_sert": argv_sert, "argv_ref": argv_ref,
            "sert": {"gozlem": g_sert, "karar": k_sert}, "baz": {"gozlem": g_baz, "karar": k_baz},
            "beklenen_bellek_bayt": spec["bellek_mb"] * 1024 * 1024, "fork_engellendi": fork_engellendi}


def ozet(r):
    ks, kb = r["sert"]["karar"], r["baz"]["karar"]
    return {"sert_uygulanan": sorted(k for k in KONTROLLER if ks[k]),
            "taban_uygulanan": sorted(k for k in KONTROLLER if kb[k]),
            "blast_kapatilan": sorted(k for k in KONTROLLER if ks[k] and not kb[k]),
            "tam_izole": all(ks.values()), "bellek_bayt": r["sert"]["gozlem"]["memory_max"],
            "beklenen_bellek_bayt": r["beklenen_bellek_bayt"], "fork_engellendi": r["fork_engellendi"],
            "argv_dogru": r["argv_sert"] == r["argv_ref"]}


def goster(sertlestirme_argv):
    """Çalıştır düğmesi: gerçek konteyner izolasyon deneyi."""
    r = deney(sertlestirme_argv)
    o = r["ortam"]
    print(f"Docker {o['docker_surumu']} · imaj {o['imaj']} · cgroup {o['cgroup_surum']}")
    print("Sertleştirme bayrakları:", " ".join(r["argv_sert"]))
    print(f"  {'(referansla aynı)' if r['argv_sert'] == r['argv_ref'] else 'UYARI: referanstan farklı: ' + ' '.join(r['argv_ref'])}\n")
    for ad, b in [("SERTLEŞTİRİLMİŞ", r["sert"]), ("SINIRSIZ TABAN", r["baz"])]:
        g, k = b["gozlem"], b["karar"]
        print(f"[{ad}] memory.max={g['memory_max']} pids.max={g['pids_max']} arayüzler={g['arayuzler']} "
              f"yazma={g['yazma']} ağ={g['ag']}")
        print(f"   uygulanan denetimler: {sorted(x for x in KONTROLLER if k[x]) or '(yok)'}")
    print(f"\nBellek limiti gerçekten cgroup'ta: {r['sert']['gozlem']['memory_max']} bayt "
          f"(beklenen {r['beklenen_bellek_bayt']}) · pids fork engellendi: {r['fork_engellendi']}")
    print("Özet:", ozet(r))
    print("Kanıt:", ai_lab.kanit_yaz("temel-konteyner-calistir", {"kaynak": "gercek", "kabul": False,
                                                                  "ders": "ai-temel-18", "ortam": o, "deney": r, "ozet": ozet(r)}))
