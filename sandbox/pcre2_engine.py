# -*- coding: utf-8 -*-
"""Regex yolunun gerçek PCRE2 motoru: libpcre2-8 kitaplığı, ctypes ile.

Python re'nin derlemediği yapılar — (?R), (?&ad), (?|...) branch reset, (*SKIP)(*FAIL)
gibi kontrol fiilleri — burada PCRE2'nin kendisinde çalışır. Kitaplık Git for Windows ile
gelir (mingw64/bin/libpcre2-8-0.dll); başka bir yerdeyse PAFTA_PCRE2_DLL onu gösterir.

Desen her zaman UTF ve UCP kipinde derlenir: Python 3'ün str desenleri gibi \\w, \\d ve
\\b Unicode'a göre çalışır. PCRE2 bayt konumu verir; dışarıya karakter konumu döner.
Nesne arayüzü re.Pattern'ın düzeneğin kullandığı alt kümesidir: search, fullmatch,
finditer, sub, split, groups, groupindex.
"""
import ctypes
import os
import re
import shutil

UTF = 0x00080000
UCP = 0x00020000
ANCHORED = 0x80000000
ENDANCHORED = 0x20000000
NOTEMPTY_ATSTART = 0x00000008
INFO_CAPTURECOUNT = 4
INFO_NAMECOUNT = 17
INFO_NAMEENTRYSIZE = 18
INFO_NAMETABLE = 19
CONFIG_VERSION = 11
ERROR_NOMATCH = -1
UNSET = ctypes.c_size_t(-1).value
ESLESME_SINIRI = 1_000_000          # felaket geri izlemede sonsuza dek dönmesin
DERINLIK_SINIRI = 10_000

_lib = None


class Pcre2Hatasi(Exception):
    def __init__(self, msg, pos=None):
        super().__init__(msg)
        self.msg = msg
        self.pos = pos


def dll_yolu():
    aday = os.environ.get("PAFTA_PCRE2_DLL")
    if aday:
        return aday if os.path.isfile(aday) else None
    kokler = []
    git = shutil.which("git")
    if git:
        # ...\Git\cmd\git.exe ya da ...\Git\bin\git.exe → ...\Git
        kokler.append(os.path.dirname(os.path.dirname(os.path.realpath(git))))
    for ortam in ("ProgramFiles", "ProgramW6432", "LOCALAPPDATA"):
        if os.environ.get(ortam):
            kokler.append(os.path.join(os.environ[ortam], "Git"))
            kokler.append(os.path.join(os.environ[ortam], "Programs", "Git"))
    for kok in kokler:
        yol = os.path.join(kok, "mingw64", "bin", "libpcre2-8-0.dll")
        if os.path.isfile(yol):
            return yol
    return None


def available():
    try:
        _yukle()
        return True
    except Pcre2Hatasi:
        return False


def _yukle():
    global _lib
    if _lib is not None:
        return _lib
    yol = dll_yolu()
    if not yol:
        raise Pcre2Hatasi("PCRE2 kitaplığı bulunamadı (Git for Windows'un mingw64/bin/libpcre2-8-0.dll'i; "
                          "başka yerdeyse PAFTA_PCRE2_DLL ortam değişkeniyle göster).")
    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(os.path.dirname(yol))
    try:
        lib = ctypes.CDLL(yol)
    except OSError as e:
        raise Pcre2Hatasi(f"PCRE2 kitaplığı yüklenemedi: {e}")
    S, P, U32 = ctypes.c_size_t, ctypes.c_void_p, ctypes.c_uint32
    imzalar = {
        "pcre2_compile_8": (P, [ctypes.c_char_p, S, U32, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(S), P]),
        "pcre2_code_free_8": (None, [P]),
        "pcre2_match_data_create_from_pattern_8": (P, [P, P]),
        "pcre2_match_data_free_8": (None, [P]),
        "pcre2_match_context_create_8": (P, [P]),
        "pcre2_match_context_free_8": (None, [P]),
        "pcre2_set_match_limit_8": (ctypes.c_int, [P, U32]),
        "pcre2_set_depth_limit_8": (ctypes.c_int, [P, U32]),
        "pcre2_match_8": (ctypes.c_int, [P, ctypes.c_char_p, S, S, U32, P, P]),
        "pcre2_get_ovector_pointer_8": (ctypes.POINTER(S), [P]),
        "pcre2_get_error_message_8": (ctypes.c_int, [ctypes.c_int, ctypes.c_char_p, S]),
        "pcre2_pattern_info_8": (ctypes.c_int, [P, U32, P]),
        "pcre2_config_8": (ctypes.c_int, [U32, P]),
    }
    for ad, (donus, argumanlar) in imzalar.items():
        f = getattr(lib, ad)
        f.restype = donus
        f.argtypes = argumanlar
    _lib = lib
    return lib


def surum():
    lib = _yukle()
    buf = ctypes.create_string_buffer(64)
    lib.pcre2_config_8(CONFIG_VERSION, buf)
    return buf.value.decode("ascii", "replace")


def _hata_metni(kod):
    buf = ctypes.create_string_buffer(256)
    _yukle().pcre2_get_error_message_8(kod, buf, len(buf))
    return buf.value.decode("utf-8", "replace")


class _Metin:
    """Bir konu metninin UTF-8 baytları ve bayt ↔ karakter konum eşlemesi."""

    def __init__(self, s):
        self.s = s
        self.b = s.encode("utf-8", "surrogatepass")
        self.bas = [0]                    # karakter i, bas[i] baytında başlar
        for ch in s:
            self.bas.append(self.bas[-1] + len(ch.encode("utf-8", "surrogatepass")))
        self.kar = {b: i for i, b in enumerate(self.bas)}

    def sonraki(self, bayt):
        return self.bas[self.kar[bayt] + 1] if self.kar.get(bayt, len(self.s)) < len(self.s) else len(self.b) + 1


class Eslesme:
    """re.Match'in düzenekte kullanılan alt kümesi."""

    def __init__(self, desen, metin, araliklar):
        self.re = desen
        self.string = metin
        self._a = araliklar               # [(bas, son)] karakter konumu; grup katılmadıysa (-1, -1)

    def _no(self, g):
        if isinstance(g, int):
            if 0 <= g < len(self._a):
                return g
            raise IndexError("no such group")
        adaylar = self.re._adlar.get(g)
        if not adaylar:
            raise IndexError("no such group")
        # Aynı ad birden çok grupta olabilir (?J ya da branch reset): katılan ilki
        return next((n for n in adaylar if self._a[n][0] >= 0), adaylar[0])

    def _deger(self, n, varsayilan=None):
        bas, son = self._a[n]
        return varsayilan if bas < 0 else self.string[bas:son]

    def group(self, *gruplar):
        if not gruplar:
            gruplar = (0,)
        degerler = [self._deger(self._no(g)) for g in gruplar]
        return degerler[0] if len(degerler) == 1 else tuple(degerler)

    def __getitem__(self, g):
        return self.group(g)

    def groups(self, default=None):
        return tuple(self._deger(n, default) for n in range(1, len(self._a)))

    def groupdict(self, default=None):
        return {ad: self._deger(self._no(ad), default) for ad in self.re._ad_sirasi}

    def start(self, g=0):
        return self._a[self._no(g)][0]

    def end(self, g=0):
        return self._a[self._no(g)][1]

    def span(self, g=0):
        return self._a[self._no(g)]

    def expand(self, sablon):
        def yerine(m):
            if m.group(0) == "\\\\":
                return "\\"
            g = m.group(1) or m.group(2)
            return self._deger(self._no(int(g) if g.isdigit() else g), "") or ""
        return re.sub(r"\\g<(\w+)>|\\(\d{1,2})|\\\\", yerine, sablon)

    def __repr__(self):
        return f"<pcre2.Eslesme span={self.span()} match={self.group(0)!r}>"


class Desen:
    """Derlenmiş bir PCRE2 deseni; re.Pattern gibi kullanılır."""

    def __init__(self, pattern):
        lib = _yukle()
        self.pattern = pattern
        b = pattern.encode("utf-8", "surrogatepass")
        hata, konum = ctypes.c_int(), ctypes.c_size_t()
        self._kod = lib.pcre2_compile_8(b, len(b), UTF | UCP, ctypes.byref(hata), ctypes.byref(konum), None)
        if not self._kod:
            # PCRE2 bayt konumu verir; desende karakter konumuna çevir
            kar = len(b[:konum.value].decode("utf-8", "ignore"))
            raise Pcre2Hatasi(_hata_metni(hata.value), kar)
        self._md = lib.pcre2_match_data_create_from_pattern_8(self._kod, None)
        self._mc = lib.pcre2_match_context_create_8(None)
        lib.pcre2_set_match_limit_8(self._mc, ESLESME_SINIRI)
        lib.pcre2_set_depth_limit_8(self._mc, DERINLIK_SINIRI)
        n = ctypes.c_uint32()
        lib.pcre2_pattern_info_8(self._kod, INFO_CAPTURECOUNT, ctypes.byref(n))
        self.groups = n.value
        self._adlar, self._ad_sirasi = {}, []
        lib.pcre2_pattern_info_8(self._kod, INFO_NAMECOUNT, ctypes.byref(n))
        adet = n.value
        if adet:
            lib.pcre2_pattern_info_8(self._kod, INFO_NAMEENTRYSIZE, ctypes.byref(n))
            boy = n.value
            tablo = ctypes.c_void_p()
            lib.pcre2_pattern_info_8(self._kod, INFO_NAMETABLE, ctypes.byref(tablo))
            ham = ctypes.string_at(tablo.value, adet * boy)
            kayitlar = []
            for i in range(adet):
                parca = ham[i * boy:(i + 1) * boy]
                kayitlar.append((parca[0] << 8 | parca[1], parca[2:].split(b"\0", 1)[0].decode("utf-8")))
            for no, ad in sorted(kayitlar):          # re.groupindex gibi: grup numarası sırası
                if ad not in self._adlar:
                    self._ad_sirasi.append(ad)
                self._adlar.setdefault(ad, []).append(no)
        self.groupindex = {ad: nolar[0] for ad, nolar in self._adlar.items()}

    def __del__(self):
        lib = _lib
        if lib is None:
            return
        for ad, isaretci in (("pcre2_match_data_free_8", "_md"), ("pcre2_match_context_free_8", "_mc"),
                             ("pcre2_code_free_8", "_kod")):
            p = getattr(self, isaretci, None)
            if p:
                getattr(lib, ad)(p)

    def _eslestir(self, m, bayt, secenek):
        lib = _lib
        rc = lib.pcre2_match_8(self._kod, m.b, len(m.b), bayt, secenek, self._md, self._mc)
        if rc == ERROR_NOMATCH:
            return None
        if rc < 0:
            raise Pcre2Hatasi("eşleştirme durdu: " + _hata_metni(rc))
        ov = lib.pcre2_get_ovector_pointer_8(self._md)
        if ov[0] > ov[1]:
            raise Pcre2Hatasi("\\K bakınma içinde eşleşmenin başını sonundan sonraya taşıdı; bu tezgah desteklemiyor.")
        araliklar = []
        for i in range(self.groups + 1):
            bas, son = ov[2 * i], ov[2 * i + 1]
            if i >= rc and i > 0 or bas == UNSET:
                araliklar.append((-1, -1))
            else:
                araliklar.append((m.kar[bas], m.kar[son]))
        return Eslesme(self, m.s, araliklar), ov[0], ov[1]

    def search(self, s, pos=0):
        m = _Metin(s)
        r = self._eslestir(m, m.bas[min(pos, len(s))], 0)
        return r[0] if r else None

    def match(self, s, pos=0):
        m = _Metin(s)
        r = self._eslestir(m, m.bas[min(pos, len(s))], ANCHORED)
        return r[0] if r else None

    def fullmatch(self, s, pos=0):
        m = _Metin(s)
        r = self._eslestir(m, m.bas[min(pos, len(s))], ANCHORED | ENDANCHORED)
        return r[0] if r else None

    def finditer(self, s):
        """pcre2demo'daki döngü: boş eşleşmeden sonra aynı yerde boş olmayanı dene, olmazsa bir karakter ilerle."""
        m = _Metin(s)
        bayt, secenek = 0, 0
        while bayt <= len(m.b):
            r = self._eslestir(m, bayt, secenek)
            if r is None:
                if secenek == 0:
                    return
                bayt, secenek = m.sonraki(bayt), 0
                continue
            es, bas, son = r
            yield es
            bayt = son
            secenek = NOTEMPTY_ATSTART | ANCHORED if bas == son else 0

    def findall(self, s):
        sonuc = []
        for es in self.finditer(s):
            if self.groups == 0:
                sonuc.append(es.group(0))
            elif self.groups == 1:
                sonuc.append(es.group(1) or "")
            else:
                sonuc.append(es.groups(""))
        return sonuc

    def sub(self, yeni, s, count=0):
        parcalar, son, n = [], 0, 0
        for es in self.finditer(s):
            if count and n >= count:
                break
            parcalar.append(s[son:es.start()])
            parcalar.append(yeni(es) if callable(yeni) else es.expand(yeni))
            son, n = es.end(), n + 1
        parcalar.append(s[son:])
        return "".join(parcalar)

    def split(self, s, maxsplit=0):
        parcalar, son, n = [], 0, 0
        for es in self.finditer(s):
            if maxsplit and n >= maxsplit:
                break
            parcalar.append(s[son:es.start()])
            parcalar.extend(es.groups())
            son, n = es.end(), n + 1
        parcalar.append(s[son:])
        return parcalar


def compile(pattern):
    return Desen(pattern)


def bilgi(pattern):
    """Ağaç düğmesinin PCRE2 karşılığı: sürüm, grup sayısı ve adlı gruplar."""
    d = Desen(pattern)
    satirlar = [f"PCRE2 {surum()} · UTF + UCP kipi",
                f"yakalayan grup: {d.groups}"]
    for ad in d._ad_sirasi:
        satirlar.append(f"  (?<{ad}>…) → grup {', '.join(map(str, d._adlar[ad]))}")
    satirlar.append("PCRE2 ayrıştırma ağacını dışarı vermez; desenin nasıl eşleştiğini Çalıştır ile metin üzerinde dene.")
    return "\n".join(satirlar)
