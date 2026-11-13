# -*- coding: utf-8 -*-
"""Görev testleri için farksal geçersiz-girdi taraması.

Geçerli bir taban girdinin her argümanını (ve iç içe liste/sözlük öğelerini) tek noktada bozar: tür değişimi, bool,
metin, NaN/sonsuz, sınır değerleri, eksik/fazla öğe, eksik/fazla alan. Her bozulmuş girdide öğrencinin fonksiyonu ile
dersin bağımsız referansı aynı davranmalıdır: ikisi de `ValueError` verir ya da ikisi de aynı sonucu döndürür.
Referansın kendisinin `ValueError` dışında hata verdiği girdiler tanımsız sayılır ve atlanır.

    from ai_fark_fuzz import fark_fuzz
    tamam, girdi = fark_fuzz(ogrenci_fn, referans_fn, (taban_arg1, taban_arg2), tohum=25)

Taban yalnız geçerli bir girdi olmalıdır; sınır değerleri ayrıca `ekler` ile verilebilir (ör. tam eşik değerleri).

mod="gecerli": girdi doğrulaması tanımlanmamış görevler içindir. Tür ve yapı korunur, yalnız sayılar (ve metin seçenekleri)
geçerli komşularıyla değiştirilir (±1, ters işaret, katlar, tabandaki ve referans çıktısındaki diğer değerler: eşikler
tam yakalanır). Referansın hata verdiği girdi tanımsız sayılıp atlanır; öğrencinin daha sıkı doğrulama yapıp ValueError
vermesine izin verilir; başka bir hata ya da farklı sonuç ayrılma sayılır.
"""
import copy
import math
import random
import sys

HAVUZ = (None, True, False, "a", float("nan"), float("inf"), float("-inf"),
         -1, 0, 1, 2, 3, -0.5, -0.1, 0.0, 0.1, 0.5, 0.9, 1.0, 1.1, 2.5, [], ())


def esit(a, b, tol=1e-9):
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if isinstance(a, float) and math.isnan(a):
            return isinstance(b, float) and math.isnan(b)
        if isinstance(b, float) and math.isnan(b):
            return False
        if math.isinf(a) or math.isinf(b):
            return a == b
        return abs(a - b) <= tol * max(1.0, abs(a), abs(b))
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(esit(a[k], b[k], tol) for k in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return type(a) is type(b) and len(a) == len(b) and all(esit(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, (set, frozenset)) and isinstance(b, (set, frozenset)):
        return a == b
    return type(a) is type(b) and a == b


def _ayni(v, x):
    return type(v) is type(x) and not isinstance(v, (list, tuple)) and v == x


def yapraklar(x, out=None):
    """Taban girdideki metin ve sayı yaprakları: yer değiştirme adayları (geçerli başka operatör, eşit eşik vb.)."""
    out = out if out is not None else {"str": [], "sayi": []}
    if isinstance(x, str) and x not in out["str"] and len(out["str"]) < 120:
        out["str"].append(x)
    elif isinstance(x, (int, float)) and not isinstance(x, bool) and x not in out["sayi"] and len(out["sayi"]) < 120:
        out["sayi"].append(x)
    elif isinstance(x, (list, tuple)):
        for v in x:
            yapraklar(v, out)
    elif isinstance(x, dict):
        for k, v in x.items():
            yapraklar(k, out)
            yapraklar(v, out)
    return out


def bozulmalar(x, derinlik=0, ek=None):
    ek = ek or {"str": [], "sayi": []}
    out = [v for v in HAVUZ if not _ayni(v, x)]
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        out += [x - 1, x + 1, -x, x * 1.5] + [v for v in ek["sayi"] if v != x]
        if isinstance(x, int):
            out.append(float(x))
            out += [v for v in range(-2, 33) if v != x] + [x * 2, x // 2]
    if isinstance(x, str):
        out += ["", " ", x + "_yok", x.upper() if x.upper() != x else x.lower()] + [v for v in ek["str"] if v != x]
    if isinstance(x, list):
        out.append(tuple(x))
        if x:
            out += [x[:-1], x + [copy.deepcopy(x[-1])], x[1:]] + [x[:n] for n in (1, 2, 3) if n < len(x)]
        if derinlik < 2:
            for j in range(min(len(x), 3)):
                for b in bozulmalar(x[j], derinlik + 1, ek):
                    y = copy.deepcopy(x)
                    y[j] = b
                    out.append(y)
    if isinstance(x, dict):
        out.append({**x, "ek_alan": 1})
        if x:
            v0 = copy.deepcopy(next(iter(x.values())))
            out += [{**x, "": v0}, {**x, " ": v0}, {**x, 5: v0}]
        for k in list(x)[:8]:
            y = dict(x)
            del y[k]
            out.append(y)
            if derinlik < 2:
                for b in bozulmalar(x[k], derinlik + 1, ek):
                    y = copy.deepcopy(x)
                    y[k] = b
                    out.append(y)
    return out


def gecerli_komsular(x, derinlik=0, ek=None):
    """Tür ve yapıyı koruyan geçerli varyantlar (mod="gecerli")."""
    ek = ek or {"str": [], "sayi": []}
    out = []
    if isinstance(x, bool):
        out.append(not x)
    elif isinstance(x, int):
        # tam sayılar çoğu zaman boyut/döngü sayısıdır: pozitif olan sıfırın altına inmez, büyüklük sınırlıdır
        tavan = max(2 * abs(x), 32)
        aday = [x - 1, x + 1, 2 * x, x // 2, 1, 2] + [int(v) for v in ek["sayi"] if isinstance(v, int)][:40]
        aday += [] if x >= 1 else [-x, 0]
        out += [v for v in aday if abs(v) <= tavan and (x < 1 or v >= 1)]
    elif isinstance(x, float):
        out += [x - 1.0, x + 1.0, -x, 1.5 * x, x / 2.0, 0.0, 0.5, 1.0] + [float(v) for v in ek["sayi"]][:40]
    elif isinstance(x, str):
        out += [v for v in ek["str"] if v != x][:20]
    elif isinstance(x, (list, tuple)) and derinlik < 3:
        for j in range(min(len(x), 6)):
            for b in gecerli_komsular(x[j], derinlik + 1, ek):
                y = list(copy.deepcopy(x))
                y[j] = b
                out.append(type(x)(y) if isinstance(x, tuple) else y)
    elif isinstance(x, dict) and derinlik < 3:
        for k in list(x)[:8]:
            for b in gecerli_komsular(x[k], derinlik + 1, ek):
                y = copy.deepcopy(x)
                y[k] = b
                out.append(y)
    return [v for v in out if not _ayni(v, x)]


class SatirButcesiAsildi(Exception):
    """Aday girdide işlev satır bütçesini aştı (ör. ebeveyn zincirinde döngü → sonsuz while)."""


def _kos(fn, x, butce=None, sayac=None):
    x = copy.deepcopy(x)
    if butce is None:
        try:
            return "ok", fn(*x)
        except ValueError:
            return "hata", None
    sayac = sayac if sayac is not None else [0]

    def iz(frame, olay, arg):
        if olay == "line":
            sayac[0] += 1
            if sayac[0] > butce:
                raise SatirButcesiAsildi(butce)
        return iz
    eski = sys.gettrace()
    sys.settrace(iz)
    try:
        return "ok", fn(*x)
    except ValueError:
        return "hata", None
    finally:
        sys.settrace(eski)


def fark_fuzz(f, ref, taban, en_cok=10000, tohum=0, ekler=(), mod="tam", butce=None):
    """(tamam, sorunlu_girdi) döndürür. tamam=False ise öğrenci referanstan ayrıldı.

    butce="oto": referansın taban girdide çalıştırdığı satır sayısının 50 katı (en az 5000) referans bütçesidir;
    bütçeyi aşan aday tanımsız sayılıp atlanır. Öğrenciye 4 katı verilir; aşarsa (sonsuz döngü) ayrılma sayılır."""
    rng = random.Random(tohum)
    if butce == "oto":
        n0 = [0]
        try:
            _kos(ref, tuple(taban), 10 ** 7, n0)
        except Exception:  # noqa: BLE001
            pass
        butce = max(5000, 50 * n0[0])
    ogr_butce = None if butce is None else 4 * butce
    ek = yapraklar(taban)
    try:  # referansın taban çıktısındaki sayılar: eşiği hesaplanan değere tam eşitlemek için
        yapraklar(ref(*copy.deepcopy(tuple(taban))), ek)
    except Exception:  # noqa: BLE001
        pass
    uret = gecerli_komsular if mod == "gecerli" else bozulmalar
    adaylar = []
    for i, a in enumerate(taban):
        for b in uret(a, 0, ek):
            x = list(copy.deepcopy(taban))
            x[i] = b
            adaylar.append(tuple(x))
    if len(adaylar) > en_cok:
        adaylar = rng.sample(adaylar, en_cok)
    for x in [tuple(taban), *ekler, *adaylar]:
        try:
            r = _kos(ref, x, butce)
        except Exception:  # noqa: BLE001 — referansın tanımsız bıraktığı girdi
            continue
        if mod == "gecerli" and r[0] != "ok":
            continue
        try:
            s = _kos(f, x, ogr_butce)
        except Exception:  # noqa: BLE001
            return False, x
        if mod == "gecerli" and s[0] == "hata":
            continue
        if r[0] != s[0] or (r[0] == "ok" and not esit(r[1], s[1])):
            return False, x
    return True, None
