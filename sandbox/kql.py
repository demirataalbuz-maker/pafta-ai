# -*- coding: utf-8 -*-
"""Pafta · KQL → SQLite çevirici.

Kusto Query Language'in öğretilen alt kümesini SQLite SQL'e çevirir. Her boru (|)
aşaması bir CTE olur. Sıralama aşamasından sonra satır sırası gizli bir __sira
sütunuyla taşınır (düzenek sonuçtan atar). Dizgi işleçleri (contains, has,
startswith, =~) KQL'deki gibi büyük-küçük harfe duyarsız olsun diye Python
fonksiyonları olarak kaydedilir: fonksiyonlari_kaydet(db).

Türler: tarih değerleri 'YYYY-AA-GG SS:DD' metnidir (veriden örneklenerek tanınır).
Süre (timespan) saniye cinsinden sayı, dinamik değer JSON metni, bool 1/0 olarak
taşınır; bu üç tür CTE başına açıkça izlenir ve son çıktıda KQL biçimine çevrilir
(süre → 00:30:00, bool → true/false).

Sıralı satır fonksiyonları (prev, next, row_number, row_cumsum, row_window_session)
iç içe pencere fonksiyonu yasağına takılmasın diye her biri önceki bir CTE'de
yardımcı sütun olarak hesaplanır.

    cevir(kaynak, sutun_bul) → SQL metni
    sutun_bul(sql) → o sorgunun sütun adları (her aşamada sorguyu doğrulamak için)
    sutun_bul.satirlar(sql) → satırlar (tür örneklemesi için; yoksa tarih tanınmaz)
"""
import json
import math
import re
from datetime import datetime, timedelta

SIMDI = "2026-10-19 12:00"     # now() ve ago() için sabit "şimdi": sonuçlar her gün aynı kalsın

ISLECLER = ("where", "project", "project-away", "project-rename", "project-reorder", "extend", "summarize",
            "sort", "order", "take", "limit", "top", "count", "distinct", "join", "lookup", "union", "parse",
            "parse-where", "mv-expand", "mv-apply", "evaluate", "serialize", "getschema", "render")
GRAFIKLER = {"anomalychart", "areachart", "barchart", "card", "columnchart", "ladderchart", "linechart",
             "piechart", "pivotchart", "scatterchart", "stackedareachart", "table", "timechart", "timepivot",
             "treemap"}

_TARIH_DESENI = re.compile(r"\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?)?")


class KqlHatasi(Exception):
    def __init__(self, msg, konum=None):
        super().__init__(msg)
        self.msg = msg
        self.konum = konum


_TOKEN = re.compile(r"""
    (?P<bosluk>\s+|//[^\n]*)
  | (?P<tarih>datetime\s*\(\s*(?P<tarih_ic>[^)]*?)\s*\))
  | (?P<metin>@"[^"\n]*"|@'[^'\n]*'|"(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*')
  | (?P<sure>\d+(?:\.\d+)?(?:ms|d|h|m|s)(?!\w))
  | (?P<sayi>\d+(?:\.\d+)?(?!\w))
  | (?P<ad>in~(?!\w)|\$?[^\W\d]\w*(?:-(?:away|rename|reorder|expand|apply|where))?)
  | (?P<isl>==|!=|<=|>=|=~|!~|\.\.|[<>=+\-*/%(),.|!;\[\]:])
""", re.X)
_TURLER = ("bosluk", "tarih", "metin", "sure", "sayi", "ad", "isl")
_DINAMIK = re.compile(r"dynamic\s*\(")


def _dinamik_sonu(kaynak, i):
    """`dynamic(` açılışından sonra eşleşen kapanış parantezinin konumu."""
    derinlik, tirnak = 1, None
    while i < len(kaynak):
        c = kaynak[i]
        if tirnak:
            if c == "\\":
                i += 1
            elif c == tirnak:
                tirnak = None
        elif c in "\"'":
            tirnak = c
        elif c in "([{":
            derinlik += 1
        elif c in ")]}":
            derinlik -= 1
            if derinlik == 0:
                return i
        i += 1
    raise KqlHatasi("dynamic( ... ) kapanmamış", i)


def _jetonla(kaynak):
    out, i = [], 0
    while i < len(kaynak):
        d = _DINAMIK.match(kaynak, i)
        if d and (i == 0 or not (kaynak[i - 1].isalnum() or kaynak[i - 1] == "_")):
            son = _dinamik_sonu(kaynak, d.end())
            out.append(("dinamik", kaynak[d.end():son].strip(), i))
            i = son + 1
            continue
        m = _TOKEN.match(kaynak, i)
        if not m:
            raise KqlHatasi(f"tanınmayan karakter: {kaynak[i]!r}", i)
        tur = next(t for t in _TURLER if m.group(t) is not None)
        if tur == "tarih":
            out.append(("tarih", m.group("tarih_ic"), i))
        elif tur != "bosluk":
            out.append((tur, m.group(tur), i))
        i = m.end()
    return out


Hata = KqlHatasi


def q(ad):
    return "[" + ad.replace("]", "]]") + "]"


def sql_metin(s):
    return "'" + s.replace("'", "''") + "'"


def _metin_coz(t):
    if t.startswith("@"):
        return t[2:-1]                     # @"..." ham metin: ters eğik çizgiler olduğu gibi kalır (regex için)
    govde = t[1:-1]
    return re.sub(r"\\(.)", lambda m: {"n": "\n", "t": "\t"}.get(m.group(1), m.group(1)), govde)


def _tarih(ic):
    ic = ic.strip().strip("\"'").replace("T", " ").rstrip("Z")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2}(?::\d{2})?)?", ic):
        raise KqlHatasi(f"tarih biçimi anlaşılmadı: {ic!r} (ör. datetime(2026-10-12) ya da datetime(2026-10-12 08:00))")
    if len(ic) == 19 and ic.endswith(":00"):
        ic = ic[:16]
    if len(ic) == 10:
        ic += " 00:00"                     # yalnızca tarih = gece yarısı; '2026-10-13 00:00' > datetime(2026-10-13) yanlış olmalı
    return ic


_BIRIM_SANIYE = {"ms": 0.001, "s": 1, "m": 60, "h": 3600, "d": 86400}


def _sure(t):
    m = re.fullmatch(r"(\d+(?:\.\d+)?)(ms|d|h|m|s)", t)
    return float(m.group(1)), m.group(2)


def _sure_saniye(t):
    n, birim = _sure(t)
    s = n * _BIRIM_SANIYE[birim]
    return int(s) if s == int(s) else s


def _dinamik_json(ic, konum):
    if not ic:
        return "null"
    for aday in (ic, re.sub(r"'((?:\\.|[^'\\])*)'", lambda m: json.dumps(m.group(1)), ic)):
        try:
            return json.dumps(json.loads(aday), ensure_ascii=False, separators=(",", ":"))
        except ValueError:
            continue
    raise KqlHatasi("dynamic(...) içindeki değer JSON olarak okunamadı", konum)


# Toplama fonksiyonlarının varsayılan sütun adları (KQL'deki gibi)
_TOPLAMA_ADI = {"count": "count_", "countif": "countif_", "dcount": "dcount_{}", "dcountif": "dcountif_{}",
                "sum": "sum_{}", "sumif": "sumif_{}", "avg": "avg_{}", "avgif": "avgif_{}", "min": "min_{}",
                "max": "max_{}", "make_list": "list_{}", "make_set": "set_{}", "take_any": "take_any_{}",
                "stdev": "stdev_{}", "variance": "variance_{}", "percentile": "percentile_{}_{}"}
_DIZGI = {"contains": "kql_contains", "contains_cs": "kql_contains_cs", "has": "kql_has", "has_cs": "kql_has_cs",
          "startswith": "kql_startswith", "startswith_cs": "kql_startswith_cs",
          "endswith": "kql_endswith", "endswith_cs": "kql_endswith_cs",
          "hasprefix": "kql_hasprefix", "hassuffix": "kql_hassuffix"}
_SIRALI_FN = ("prev", "next", "row_number", "row_cumsum", "row_window_session")
_PENCERE = "OVER (ORDER BY [__sira] ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)"
_TIP_ADI = {"string": "string", "int": "int", "long": "long", "real": "real", "double": "real", "decimal": "real",
            "bool": "bool", "boolean": "bool", "datetime": "datetime", "date": "datetime", "timespan": "timespan",
            "time": "timespan", "dynamic": "dynamic", "guid": "string"}


class _Cevirici:
    def __init__(self, kaynak, sutun_bul):
        self.kaynak = kaynak
        self.j = _jetonla(kaynak)
        self.i = 0
        self.sutun_bul = sutun_bul
        self.ctes = []
        self.ozyineli = False
        self.acik = {}            # CTE → {sütun: 'timespan' | 'dynamic' | 'bool'}
        self._tip_onbellek = {}
        self.letler = {}
        self.tipler = {}          # bu aşamada üretilen SQL ifadelerinin türleri
        self.kaynak_cte = None    # sütun türlerine bakılacak CTE
        self.yardimci = []        # sıralı fonksiyonlar için önce hesaplanacak sütunlar
        self.girdi_sirali = False
        self.sayac = 0

    # — jeton yardımcıları —
    def bak(self, k=0):
        n = self.i + k
        return self.j[n] if n < len(self.j) else ("son", "", len(self.kaynak))

    def isl_mi(self, deger, k=0):
        t = self.bak(k)
        return t[0] == "isl" and t[1] == deger

    def kelime_mi(self, deger, k=0):
        t = self.bak(k)
        return t[0] == "ad" and t[1] == deger

    def bekle(self, deger):
        t = self.bak()
        if t[1] != deger:
            raise KqlHatasi(f"'{deger}' bekleniyordu, '{t[1] or 'sorgunun sonu'}' geldi", t[2])
        self.i += 1

    def ad_al(self):
        t = self.bak()
        if t[0] != "ad":
            raise KqlHatasi(f"bir sütun adı bekleniyordu, '{t[1] or 'sorgunun sonu'}' geldi", t[2])
        self.i += 1
        return t[1]

    def virgul(self):
        if self.isl_mi(","):
            self.i += 1
            return True
        return False

    # — türler —
    def T(self, sql, tip):
        if tip:
            self.tipler[sql] = tip
        return sql

    def tipi(self, sql):
        return self.tipler.get(sql)

    def baglam(self, cte, sirali=False):
        """Bir işlecin ifadelerini ayrıştırmadan önce: sütun türleri bu CTE'den okunur."""
        self.kaynak_cte = cte
        self.tipler = {}
        self.yardimci = []
        self.girdi_sirali = sirali

    def baglam_sakla(self):
        return (self.kaynak_cte, self.tipler, self.yardimci, self.girdi_sirali)

    def baglam_don(self, b):
        self.kaynak_cte, self.tipler, self.yardimci, self.girdi_sirali = b

    def cte_tipleri(self, ad):
        """Sütun → tür: açıkça izlenenler + veriden tanınan tarih/sayı/metin."""
        if ad in self._tip_onbellek:
            return self._tip_onbellek[ad]
        tipler = dict(self.acik.get(ad, {}))
        satir_fn = getattr(self.sutun_bul, "satirlar", None)
        cols = self.sutun_bul(self.with_sql(f"SELECT * FROM {ad} LIMIT 0"))
        if satir_fn:
            satirlar = satir_fn(self.with_sql(f"SELECT * FROM {ad} LIMIT 200"))
            for n, c in enumerate(cols):
                if c in tipler or c == "__sira":
                    continue
                degerler = [r[n] for r in satirlar if r[n] is not None]
                if not degerler:
                    continue
                if all(isinstance(v, str) and _TARIH_DESENI.fullmatch(v) for v in degerler):
                    tipler[c] = "datetime"
                elif all(isinstance(v, int) for v in degerler):
                    tipler[c] = "long"
                elif all(isinstance(v, (int, float)) for v in degerler):
                    tipler[c] = "real"
                else:
                    tipler[c] = "string"
        self._tip_onbellek[ad] = tipler
        return tipler

    def kolon_tipi(self, ad):
        if self.kaynak_cte is None:
            return None
        return self.cte_tipleri(self.kaynak_cte).get(ad)

    def acik_tasi(self, kaynak, ad_degis=None, sec=None):
        """Kaynak CTE'nin açık türlerini (isteğe bağlı yeniden adlandırarak) döndür."""
        out = {}
        for c, t in self.acik.get(kaynak, {}).items():
            yeni = (ad_degis or {}).get(c, c)
            if sec is None or yeni in sec:
                out[yeni] = t
        return out

    # — CTE yardımcıları —
    def yeni(self, sql, tipler=None):
        ad = f"a{len(self.ctes) + 1}"
        self.ctes.append((ad, sql))
        if tipler:
            self.acik[ad] = {c: t for c, t in tipler.items() if t in ("timespan", "dynamic", "bool")}
        self.sutunlar(ad, dogrula=True)          # her aşama hemen denetlensin: hata doğru yerde çıksın
        return ad

    def yeni_ozyineli(self, sablon, tipler=None):
        self.ozyineli = True
        ad = f"a{len(self.ctes) + 1}"
        return self.yeni(sablon.format(ad=ad), tipler)

    def with_sql(self, son):
        if not self.ctes:
            return son
        bas = "WITH RECURSIVE " if self.ozyineli else "WITH "
        return bas + ",\n     ".join(f"{a} AS ({s})" for a, s in self.ctes) + "\n" + son

    def sutunlar(self, ad, dogrula=False):
        cols = self.sutun_bul(self.with_sql(f"SELECT * FROM {ad} LIMIT 0"))
        return cols if dogrula else [c for c in cols if c != "__sira" and not c.startswith("__y")]

    def secim(self, cols, sira, on_ek=""):
        parca = [on_ek + q(c) for c in cols]
        if sira:
            parca.append(on_ek + "[__sira]")
        return ", ".join(parca)

    def yardimci_uygula(self, onceki):
        """Ayrıştırma sırasında biriken sıralı fonksiyon sütunlarını sırayla hesapla."""
        for ad, sql in self.yardimci:
            onceki = self.yeni(f"SELECT *, {sql} AS {q(ad)} FROM {onceki}", self.acik.get(onceki))
        self.yardimci = []
        return onceki

    # — sorgu —
    def sorgu(self):
        """Kaynak ve ardından | işleçleri → (CTE adı, sıralı mı)."""
        t = self.bak()
        if t[0] == "isl" and t[1] == "(":
            self.i += 1
            ad, sira = self.sorgu()
            self.bekle(")")
        elif self.kelime_mi("print"):
            self.i += 1
            self.baglam(None)
            ogeler = self.ogeler(varsayilan="print_{}")
            ad, sira = self.yeni("SELECT " + ", ".join(f"{s} AS {q(a)}" for a, s in ogeler),
                                 {a: self.tipi(s) for a, s in ogeler}), False
        elif self.kelime_mi("datatable") and self.isl_mi("(", 1):
            ad, sira = self.datatable(), False
        elif self.kelime_mi("range") and self.bak(1)[0] == "ad":
            ad, sira = self.kaynak_range(), True
        elif self.kelime_mi("union"):
            self.i += 1
            ad, sira = self.union_sql([], kaynak_bicimi=True), False
        elif self.watchlist_mi():
            ad, sira = self.kaynak_watchlist(), False
        elif t[0] == "ad":
            self.i += 1
            if t[1] in self.letler:
                tur, deger, let_sira = self.letler[t[1]]
                if tur != "tablo":
                    raise KqlHatasi(f"{t[1]} bir tablo değil, bir değer (let ile skaler tanımlanmış)", t[2])
                ad, sira = self.yeni(f"SELECT * FROM {deger}", self.acik.get(deger)), let_sira
            else:
                ad, sira = self.yeni(f"SELECT * FROM {q(t[1])}"), False
        else:
            raise KqlHatasi("sorgu bir tablo adıyla başlamalı (ör. sunucular | where ...)", t[2])
        while self.isl_mi("|"):
            self.i += 1
            op = self.bak()
            if op[0] != "ad":
                raise KqlHatasi("| işaretinden sonra bir işleç bekleniyordu", op[2])
            if op[1] not in ISLECLER:
                if op[1] in ("make-series", "top-nested", "as", "invoke", "search"):
                    raise KqlHatasi(f"{op[1]} bu tezgahta desteklenmiyor", op[2])
                raise KqlHatasi(f"bu işleç desteklenmiyor: {op[1]} (desteklenenler: {', '.join(ISLECLER)})", op[2])
            self.i += 1
            ad, sira = getattr(self, "op_" + op[1].replace("-", "_"))(ad, sira)
        return ad, sira

    def let_ifadesi(self):
        self.i += 1
        t = self.bak()
        ad = self.ad_al()
        self.bekle("=")
        if self.kelime_mi("materialize") and self.isl_mi("(", 1):
            self.i += 2
            cte, sira = self.sorgu()
            self.bekle(")")
            self.letler[ad] = ("tablo", cte, sira)
        else:
            konum, n_cte, ozy = self.i, len(self.ctes), self.ozyineli
            tablo = None
            if self.bak()[0] in ("ad", "isl") and not self.isl_mi("-") and not (
                    self.bak()[0] == "ad" and self.isl_mi("(", 1)
                    and not (self.kelime_mi("datatable") or self.kelime_mi("_GetWatchlist"))):
                try:
                    tablo = self.sorgu()
                    if not self.isl_mi(";"):
                        raise KqlHatasi("", None)
                except Exception:                       # tablo değilmiş: skaler olarak dene
                    for ad_, _ in self.ctes[n_cte:]:
                        self.acik.pop(ad_, None)
                        self._tip_onbellek.pop(ad_, None)
                    self.i, self.ctes, self.ozyineli, tablo = konum, self.ctes[:n_cte], ozy, None
            if tablo:
                self.letler[ad] = ("tablo", tablo[0], tablo[1])
            else:
                self.baglam(None)
                sql = self.ifade()
                self.letler[ad] = ("skaler", sql, self.tipi(sql))
        if not self.isl_mi(";"):
            raise KqlHatasi(f"let {ad} = ... ifadesinden sonra ';' bekleniyordu", self.bak()[2])
        self.i += 1
        return t

    def ogeler(self, varsayilan="Column{}", toplama=False):
        """`ad = ifade` ya da `ifade`, virgülle ayrık → [(ad, sql)]."""
        out = []
        while True:
            t = self.bak()
            if toplama and t[0] == "ad" and t[1] == "percentiles" and self.isl_mi("(", 1):
                out.extend(self._percentiles())
                if not self.virgul():
                    return out
                continue
            if t[0] == "ad" and self.isl_mi("=", 1):
                self.i += 2
                out.append((t[1], self.ifade()))
            else:
                bas = self.i
                sql = self.ifade()
                ad = None
                if self.i == bas + 1 and t[0] == "ad":
                    ad = t[1]                                       # tek başına bir sütun
                elif t[0] == "ad" and bas + 1 < len(self.j) and self.j[bas + 1][:2] == ("isl", "("):
                    fn = t[1]
                    arg = self.j[bas + 2] if bas + 2 < len(self.j) else ("son", "", 0)
                    if toplama and fn == "percentile":
                        p = self.j[bas + 4] if bas + 4 < len(self.j) else ("son", "", 0)
                        ad = _TOPLAMA_ADI[fn].format(arg[1] if arg[0] == "ad" else "", p[1].replace(".", "_"))
                    elif toplama and fn in _TOPLAMA_ADI:
                        ad = _TOPLAMA_ADI[fn].format(arg[1] if arg[0] == "ad" else "")
                    elif fn == "bin" and arg[0] == "ad":
                        ad = arg[1]
                if ad is None:
                    ad = varsayilan.format(len(out) + (0 if "print" in varsayilan else 1))
                out.append((ad, sql))
            if not self.virgul():
                return out

    def _percentiles(self):
        self.i += 2
        arg = self.bak()
        x = self.ifade()
        yuzdeler = []
        while self.virgul():
            p = self.bak()
            if p[0] != "sayi":
                raise KqlHatasi("percentiles(sütun, 50, 95, ...) biçiminde yüzdeler bekleniyordu", p[2])
            self.i += 1
            yuzdeler.append(p[1])
        self.bekle(")")
        if not yuzdeler:
            raise KqlHatasi("percentiles() en az bir yüzde ister", arg[2])
        ad = arg[1] if arg[0] == "ad" else ""
        return [(f"percentile_{ad}_{p.replace('.', '_')}", self.T(f"kql_pct({x}, {p})", self.tipi(x)))
                for p in yuzdeler]

    # — kaynaklar —
    def datatable(self):
        bas = self.bak()
        self.i += 2
        kolonlar = []
        while True:
            ad = self.ad_al()
            self.bekle(":")
            t = self.bak()
            tip = _TIP_ADI.get(self.ad_al())
            if tip is None:
                raise KqlHatasi(f"bilinmeyen tür: {t[1]}", t[2])
            kolonlar.append((ad, tip))
            if not self.virgul():
                break
        self.bekle(")")
        self.bekle("[")
        degerler = []
        self.baglam(None)
        while not self.isl_mi("]"):
            degerler.append(self.deger_ifadesi())
            if not self.virgul():
                break
        self.bekle("]")
        n = len(kolonlar)
        if len(degerler) % n:
            raise KqlHatasi(f"datatable: {len(degerler)} değer {n} sütuna bölünemiyor", bas[2])
        tipler = {a: t for a, t in kolonlar}
        if not degerler:
            secim = ", ".join(f"NULL AS {q(a)}" for a, _ in kolonlar)
            return self.yeni(f"SELECT {secim} WHERE 0", tipler)
        satirlar = []
        for k in range(0, len(degerler), n):
            parca = []
            for (a, tip), v in zip(kolonlar, degerler[k:k + n]):
                if tip in ("int", "long") and v not in ("NULL",):
                    v = f"CAST({v} AS INTEGER)"
                elif tip == "real" and v != "NULL":
                    v = f"CAST({v} AS REAL)"
                parca.append(f"{v} AS {q(a)}" if not satirlar else v)
            satirlar.append("SELECT " + ", ".join(parca))
        return self.yeni(" UNION ALL ".join(satirlar), tipler)

    def deger_ifadesi(self):
        t = self.bak()
        if t[0] == "dinamik":
            self.i += 1
            return sql_metin(_dinamik_json(t[1], t[2]))
        if t[0] == "sure":
            self.i += 1
            return str(_sure_saniye(t[1]))
        if self.kelime_mi("null"):
            self.i += 1
            return "NULL"
        return self.toplama()

    def kaynak_range(self):
        self.i += 1
        ad = self.ad_al()
        self.baglam(None)
        if not self.kelime_mi("from"):
            raise KqlHatasi("range Ad from Başlangıç to Bitiş step Adım biçimi bekleniyordu", self.bak()[2])
        self.i += 1
        a = self.toplama()
        self.bekle("to")
        b = self.toplama()
        self.bekle("step")
        t = self.bak()
        s = self.toplama()
        if self.tipi(s) == "timespan" or self.tipi(a) == "datetime":
            if self.tipi(s) != "timespan":
                raise KqlHatasi("tarih aralığında adım bir süre olmalı (ör. step 1h)", t[2])
            ileri = f"kql_dt_add({q(ad)}, {s})"
        else:
            ileri = f"({q(ad)} + {s})"
        if re.fullmatch(r"-?\d+(?:\.\d+)?", s) and float(s) <= 0:
            raise KqlHatasi("range adımı sıfırdan büyük olmalı", t[2])
        sablon = (f"SELECT {a} AS {q(ad)}, 1 AS [__sira] UNION ALL "
                  f"SELECT {ileri}, [__sira] + 1 FROM {{ad}} WHERE {ileri} <= {b} AND [__sira] < 100000")
        return self.yeni_ozyineli(sablon, {ad: self.tipi(a)})

    def union_sql(self, parcalar, kaynak_bicimi=False):
        kaynak_adi = None
        while self.kelime_mi("kind") or self.kelime_mi("withsource") or self.kelime_mi("isfuzzy"):
            anahtar = self.ad_al()
            self.bekle("=")
            if anahtar == "withsource":
                kaynak_adi = self.ad_al()
            else:
                self.ad_al()
        if kaynak_adi and not kaynak_bicimi:
            raise KqlHatasi("withsource yalnızca 'union A, B' kaynak biçiminde destekleniyor", self.bak()[2])
        while True:
            t = self.bak()
            if self.isl_mi("("):
                self.i += 1
                ad, _ = self.sorgu()
                self.bekle(")")
                parcalar.append((ad, f"union_arg{len(parcalar)}"))
            elif self.watchlist_mi():
                parcalar.append((self.kaynak_watchlist(), f"union_arg{len(parcalar)}"))
            else:
                isim = self.ad_al()
                if isim in self.letler and self.letler[isim][0] == "tablo":
                    ad = self.yeni(f"SELECT * FROM {self.letler[isim][1]}", self.acik.get(self.letler[isim][1]))
                else:
                    ad = self.yeni(f"SELECT * FROM {q(isim)}")
                parcalar.append((ad, isim))
            if not self.virgul():
                break
        if len(parcalar) < 2 and kaynak_bicimi:
            raise KqlHatasi("union en az iki tablo ister", t[2])
        tum, tipler = [], {}
        for ad, _ in parcalar:
            for c in self.sutunlar(ad):
                if c not in tum:
                    tum.append(c)
            for c, tip in self.acik.get(ad, {}).items():
                tipler.setdefault(c, tip)
        secimler = []
        for ad, isim in parcalar:
            cols = self.sutunlar(ad)
            parca = ([f"{sql_metin(isim or '')} AS {q(kaynak_adi)}"] if kaynak_adi else []) + \
                    [f"{q(c)} AS {q(c)}" if c in cols else f"NULL AS {q(c)}" for c in tum]
            secimler.append(f"SELECT {', '.join(parca)} FROM {ad}")
        return self.yeni(" UNION ALL ".join(secimler), tipler)

    # — işleçler —
    def op_where(self, onceki, sira):
        self.baglam(onceki, sira)
        kosul = self.ifade()
        cols = self.sutunlar(onceki)
        kaynak = self.yardimci_uygula(onceki)
        return self.yeni(f"SELECT {self.secim(cols, sira)} FROM {kaynak} WHERE {kosul}", self.acik.get(onceki)), sira

    def op_project(self, onceki, sira):
        self.baglam(onceki, sira)
        ogeler = self.ogeler()
        kaynak = self.yardimci_uygula(onceki)
        secim = ", ".join(f"{s} AS {q(a)}" for a, s in ogeler) + (", [__sira]" if sira else "")
        return self.yeni(f"SELECT {secim} FROM {kaynak}", {a: self.tipi(s) for a, s in ogeler}), sira

    def op_project_away(self, onceki, sira):
        cols = self.sutunlar(onceki)
        at = []
        while True:
            t = self.bak()
            ad = self.ad_al()
            if ad not in cols:
                raise KqlHatasi(f"böyle bir sütun yok: {ad}", t[2])
            at.append(ad)
            if not self.virgul():
                break
        kalan = [c for c in cols if c not in at]
        return self.yeni(f"SELECT {self.secim(kalan, sira)} FROM {onceki}", self.acik_tasi(onceki, sec=kalan)), sira

    def op_project_rename(self, onceki, sira):
        cols = self.sutunlar(onceki)
        ad_degis = {}
        while True:
            yeni_ad = self.ad_al()
            self.bekle("=")
            t = self.bak()
            eski = self.ad_al()
            if eski not in cols:
                raise KqlHatasi(f"böyle bir sütun yok: {eski}", t[2])
            ad_degis[eski] = yeni_ad
            if not self.virgul():
                break
        secim = ", ".join(f"{q(c)} AS {q(ad_degis.get(c, c))}" for c in cols) + (", [__sira]" if sira else "")
        return self.yeni(f"SELECT {secim} FROM {onceki}", self.acik_tasi(onceki, ad_degis)), sira

    def op_project_reorder(self, onceki, sira):
        cols = self.sutunlar(onceki)
        one = []
        while True:
            t = self.bak()
            ad = self.ad_al()
            if ad not in cols:
                raise KqlHatasi(f"böyle bir sütun yok: {ad}", t[2])
            one.append(ad)
            if not self.virgul():
                break
        sirali = one + [c for c in cols if c not in one]
        return self.yeni(f"SELECT {self.secim(sirali, sira)} FROM {onceki}", self.acik.get(onceki)), sira

    def op_extend(self, onceki, sira):
        while True:
            self.baglam(onceki, sira)
            t = self.bak()
            if t[0] == "ad" and self.isl_mi("=", 1):
                self.i += 2
                ad, sql = t[1], self.ifade()
            else:
                bas = self.i
                sql = self.ifade()
                ad = t[1] if (self.i == bas + 1 and t[0] == "ad") else None
                if ad is None:
                    self.sayac += 1
                    ad = f"Column{self.sayac}"
            tip = self.tipi(sql)
            cols = self.sutunlar(onceki)
            kaynak = self.yardimci_uygula(onceki)
            tipler = self.acik_tasi(onceki)
            tipler.pop(ad, None)
            if tip:
                tipler[ad] = tip
            if ad in cols:
                secim = ", ".join(f"{sql} AS {q(c)}" if c == ad else q(c) for c in cols)
            else:
                secim = ", ".join(q(c) for c in cols) + f", {sql} AS {q(ad)}"
            onceki = self.yeni(f"SELECT {secim}{', [__sira]' if sira else ''} FROM {kaynak}", tipler)
            if not self.virgul():
                return onceki, sira

    def op_summarize(self, onceki, sira):
        self.baglam(onceki, sira)
        if (self.kelime_mi("arg_max") or self.kelime_mi("arg_min")) and self.isl_mi("(", 1):
            return self._arg_max(onceki)
        toplamalar = [] if self.kelime_mi("by") else self.ogeler(toplama=True)
        gruplar = []
        if self.kelime_mi("by"):
            self.i += 1
            gruplar = self.ogeler()
        if not toplamalar and not gruplar:
            raise KqlHatasi("summarize'dan sonra bir toplama (ör. count()) ya da by bekleniyordu", self.bak()[2])
        kaynak = self.yardimci_uygula(onceki)
        secim = ", ".join(f"{s} AS {q(a)}" for a, s in gruplar + toplamalar)
        sql = f"SELECT {secim} FROM {kaynak}"
        if gruplar:
            sql += " GROUP BY " + ", ".join(str(n + 1) for n in range(len(gruplar)))
        return self.yeni(sql, {a: self.tipi(s) for a, s in gruplar + toplamalar}), False

    def _arg_max(self, onceki):
        fn = self.ad_al()
        self.i += 1
        e_t = self.bak()
        e = self.ifade()
        e_ad = e_t[1] if e_t[0] == "ad" and e == q(e_t[1]) else ("max_" if fn == "arg_max" else "min_") + "expr"
        istenen = None
        self.bekle(",")
        if self.isl_mi("*"):
            self.i += 1
        else:
            istenen = []
            while True:
                istenen.append(self.ad_al())
                if not self.virgul():
                    break
        self.bekle(")")
        if self.isl_mi(","):
            raise KqlHatasi(f"bu tezgahta {fn}() summarize içinde tek başına kullanılmalı", self.bak()[2])
        gruplar = []
        if self.kelime_mi("by"):
            self.i += 1
            gruplar = self.ogeler()
        cols = self.sutunlar(onceki)
        anahtar_adlar = [a for a, _ in gruplar]
        bolum = ("PARTITION BY " + ", ".join(s for _, s in gruplar) + " ") if gruplar else ""
        yon = "DESC NULLS LAST" if fn == "arg_max" else "ASC NULLS LAST"
        ek = [f"{s} AS [__g{n}]" for n, (_, s) in enumerate(gruplar)]
        ek += [f"{e} AS [__e]", f"ROW_NUMBER() OVER ({bolum}ORDER BY {e} {yon}) AS [__rn]"]
        kaynak = self.yardimci_uygula(onceki)
        ara = self.yeni(f"SELECT *, {', '.join(ek)} FROM {kaynak}", self.acik.get(onceki))
        geri = [c for c in (istenen if istenen is not None else cols) if c not in anahtar_adlar and c != e_ad]
        secim = [f"[__g{n}] AS {q(a)}" for n, a in enumerate(anahtar_adlar)]
        if e_ad not in anahtar_adlar:
            secim.append(f"[__e] AS {q(e_ad)}")
        secim += [q(c) for c in geri]
        tipler = self.acik_tasi(onceki)
        for a, s in gruplar:
            if self.tipi(s):
                tipler[a] = self.tipi(s)
        if self.tipi(e):
            tipler[e_ad] = self.tipi(e)
        return self.yeni(f"SELECT {', '.join(secim)} FROM {ara} WHERE [__rn] = 1", tipler), False

    def _siralama(self):
        parcalar = []
        while True:
            e = self.ifade()
            yon = "DESC"                                   # KQL'de varsayılan yön azalandır
            if self.kelime_mi("asc"):
                yon = "ASC"
                self.i += 1
            elif self.kelime_mi("desc"):
                self.i += 1
            if self.kelime_mi("nulls"):
                self.i += 1
                yon += " NULLS " + self.ad_al().upper()
            parcalar.append(f"{e} {yon}")
            if not self.virgul():
                return parcalar

    def _sirala(self, onceki, sira, parcalar):
        cols = self.sutunlar(onceki)
        anahtar = ", ".join(parcalar) + (", [__sira]" if sira else "")
        return self.yeni(f"SELECT {', '.join(q(c) for c in cols)}, ROW_NUMBER() OVER (ORDER BY {anahtar}) AS [__sira] "
                         f"FROM {onceki}", self.acik.get(onceki))

    def op_sort(self, onceki, sira):
        self.bekle("by")
        self.baglam(onceki, sira)
        return self._sirala(onceki, sira, self._siralama()), True

    op_order = op_sort

    def _sayi(self):
        t = self.bak()
        if t[0] != "sayi":
            raise KqlHatasi(f"bir sayı bekleniyordu, '{t[1] or 'sorgunun sonu'}' geldi", t[2])
        self.i += 1
        return int(float(t[1]))

    def op_take(self, onceki, sira):
        n = self._sayi()
        return self.yeni(f"SELECT * FROM {onceki}{' ORDER BY [__sira]' if sira else ''} LIMIT {n}",
                         self.acik.get(onceki)), sira

    op_limit = op_take

    def op_top(self, onceki, sira):
        n = self._sayi()
        self.bekle("by")
        self.baglam(onceki, sira)
        sirali = self._sirala(onceki, sira, self._siralama())
        return self.yeni(f"SELECT * FROM {sirali} ORDER BY [__sira] LIMIT {n}", self.acik.get(onceki)), True

    def op_count(self, onceki, sira):
        return self.yeni(f"SELECT COUNT(*) AS [Count] FROM {onceki}"), False

    def op_distinct(self, onceki, sira):
        if self.isl_mi("*"):
            self.i += 1
            cols = self.sutunlar(onceki)
        else:
            cols = []
            while True:
                cols.append(self.ad_al())
                if not self.virgul():
                    break
        return self.yeni(f"SELECT DISTINCT {', '.join(q(c) for c in cols)} FROM {onceki}",
                         self.acik_tasi(onceki, sec=cols)), False

    def op_serialize(self, onceki, sira):
        if not sira:
            cols = self.sutunlar(onceki)
            onceki = self.yeni(f"SELECT {', '.join(q(c) for c in cols)}, ROW_NUMBER() OVER () AS [__sira] FROM {onceki}",
                               self.acik.get(onceki))
        if self.bak()[0] == "ad" and not self.isl_mi("|"):
            return self.op_extend(onceki, True)
        return onceki, True

    def op_render(self, onceki, sira):
        """render sonucu değiştirmez; istemciye "bunu şöyle çiz" der. Tezgah grafik türünü ve render'ın
        sorgunun son işleci olduğunu denetler, tabloyu olduğu gibi gösterir (with (...) seçenekleri atlanır)."""
        t = self.bak()
        if t[0] != "ad" or t[1] not in GRAFIKLER:
            raise KqlHatasi(f"render'dan sonra bir grafik türü bekleniyordu: {', '.join(sorted(GRAFIKLER))}", t[2])
        self.i += 1
        if self.bak()[0] == "ad" and self.bak()[1] == "with":
            self.i += 1
            self.bekle("(")
            derinlik = 1
            while derinlik:
                if self.bak()[0] == "son":
                    raise KqlHatasi("render with (...) parantezi kapanmadı", self.bak()[2])
                if self.isl_mi("("):
                    derinlik += 1
                elif self.isl_mi(")"):
                    derinlik -= 1
                self.i += 1
        if self.isl_mi("|"):
            raise KqlHatasi("render sorgunun son işleci olmalı", self.bak()[2])
        return onceki, sira

    def op_getschema(self, onceki, sira):
        tipler = self.cte_tipleri(onceki)
        net = {"string": "System.String", "long": "System.Int64", "int": "System.Int32", "real": "System.Double",
               "datetime": "System.DateTime", "timespan": "System.TimeSpan", "dynamic": "System.Object",
               "bool": "System.SByte"}
        degerler = []
        for n, c in enumerate(self.sutunlar(onceki)):
            tip = tipler.get(c, "string")
            degerler.append(f"({sql_metin(c)}, {n}, {sql_metin(net.get(tip, 'System.String'))}, {sql_metin(tip)})")
        return self.yeni("SELECT column1 AS ColumnName, column2 AS ColumnOrdinal, column3 AS DataType, "
                         f"column4 AS ColumnType FROM (VALUES {', '.join(degerler)})"), False

    def op_union(self, onceki, sira):
        return self.union_sql([(onceki, None)]), False

    def _katilim_anahtarlari(self):
        kosullar = []
        while True:
            if self.kelime_mi("$left"):
                self.i += 1
                self.bekle(".")
                a = self.ad_al()
                self.bekle("==")
                if not self.kelime_mi("$right"):
                    raise KqlHatasi("$left.a == $right.b biçimi bekleniyordu", self.bak()[2])
                self.i += 1
                self.bekle(".")
                b = self.ad_al()
            else:
                a = b = self.ad_al()
            kosullar.append((a, b))
            if not self.virgul():
                return kosullar

    def watchlist_mi(self):
        return self.kelime_mi("_GetWatchlist") and self.isl_mi("(", 1)

    def kaynak_watchlist(self):
        # Sentinel watchlist'i: görevin hazırlığı onu watchlist_<takma ad> tablosu olarak kurar
        self.i += 2
        m = self.bak()
        if m[0] != "metin":
            raise KqlHatasi("_GetWatchlist('takma ad') bekleniyordu", m[2])
        self.i += 1
        self.bekle(")")
        tablo = "watchlist_" + _metin_coz(m[1])
        try:
            self.sutun_bul(f"SELECT * FROM {q(tablo)} LIMIT 0")
        except Exception:
            raise KqlHatasi(f"watchlist bulunamadı: {_metin_coz(m[1])}", m[2])
        return self.yeni(f"SELECT * FROM {q(tablo)}")

    def _sag_taraf(self):
        if self.isl_mi("("):
            self.i += 1
            sag, _ = self.sorgu()
            self.bekle(")")
            return sag
        if self.watchlist_mi():                            # join/lookup _GetWatchlist('ad') on ... (parantezsiz)
            return self.kaynak_watchlist()
        isim = self.ad_al()
        if isim in self.letler and self.letler[isim][0] == "tablo":
            return self.yeni(f"SELECT * FROM {self.letler[isim][1]}", self.acik.get(self.letler[isim][1]))
        return self.yeni(f"SELECT * FROM {q(isim)}")

    def op_join(self, onceki, sira):
        tur = "innerunique"                               # KQL'in varsayılanı
        if self.kelime_mi("kind"):
            self.i += 1
            self.bekle("=")
            t = self.bak()
            tur = self.ad_al()
            if tur not in ("innerunique", "inner", "leftouter", "rightouter", "fullouter", "leftanti", "leftsemi",
                           "rightanti", "rightsemi"):
                raise KqlHatasi(f"bu join türü desteklenmiyor: {tur}", t[2])
        sag = self._sag_taraf()
        self.bekle("on")
        kosullar = self._katilim_anahtarlari()
        L, R = self.sutunlar(onceki), self.sutunlar(sag)
        on = " AND ".join(f"l.{q(a)} = r.{q(b)}" for a, b in kosullar)
        if tur in ("leftanti", "leftsemi"):
            var = "NOT EXISTS" if tur == "leftanti" else "EXISTS"
            return self.yeni(f"SELECT {', '.join('l.' + q(c) for c in L)} FROM {onceki} AS l "
                             f"WHERE {var} (SELECT 1 FROM {sag} AS r WHERE {on})", self.acik.get(onceki)), False
        if tur in ("rightanti", "rightsemi"):
            var = "NOT EXISTS" if tur == "rightanti" else "EXISTS"
            return self.yeni(f"SELECT {', '.join('r.' + q(c) for c in R)} FROM {sag} AS r "
                             f"WHERE {var} (SELECT 1 FROM {onceki} AS l WHERE {on})", self.acik.get(sag)), False
        sol = onceki
        if tur == "innerunique":
            # Sol taraf anahtar başına tek satıra indirilir; KQL'in çoğu kişiyi şaşırtan varsayılanı
            anahtar = ", ".join(q(a) for a, _ in kosullar)
            sol = self.yeni(f"SELECT * FROM (SELECT *, ROW_NUMBER() OVER (PARTITION BY {anahtar}"
                            f"{' ORDER BY [__sira]' if sira else ''}) AS [__tek] FROM {onceki}) WHERE [__tek] = 1",
                            self.acik.get(onceki))
        sag_adlar = []
        for c in R:
            yeni_ad, k = c, 1
            while yeni_ad in L or yeni_ad in sag_adlar:
                yeni_ad, k = f"{c}{k}", k + 1
            sag_adlar.append(yeni_ad)
        katilim = {"inner": "JOIN", "innerunique": "JOIN", "leftouter": "LEFT JOIN",
                   "rightouter": "RIGHT JOIN", "fullouter": "FULL JOIN"}[tur]
        secim = [f"l.{q(c)} AS {q(c)}" for c in L] + [f"r.{q(c)} AS {q(n)}" for c, n in zip(R, sag_adlar)]
        tipler = self.acik_tasi(onceki)
        tipler.update(self.acik_tasi(sag, dict(zip(R, sag_adlar))))
        return self.yeni(f"SELECT {', '.join(secim)} FROM {sol} AS l {katilim} {sag} AS r ON {on}", tipler), False

    def op_lookup(self, onceki, sira):
        tur = "leftouter"
        if self.kelime_mi("kind"):
            self.i += 1
            self.bekle("=")
            t = self.bak()
            tur = self.ad_al()
            if tur not in ("leftouter", "inner"):
                raise KqlHatasi("lookup türü leftouter ya da inner olabilir", t[2])
        sag = self._sag_taraf()
        self.bekle("on")
        kosullar = self._katilim_anahtarlari()
        L, R = self.sutunlar(onceki), self.sutunlar(sag)
        sag_anahtar = {b for _, b in kosullar}
        on = " AND ".join(f"l.{q(a)} = r.{q(b)}" for a, b in kosullar)
        ekler, adlar = [], {}
        for c in R:
            if c in sag_anahtar:
                continue
            yeni_ad, k = c, 1
            while yeni_ad in L or yeni_ad in adlar.values():
                yeni_ad, k = f"{c}{k}", k + 1
            adlar[c] = yeni_ad
            ekler.append(f"r.{q(c)} AS {q(yeni_ad)}")
        secim = [f"l.{q(c)} AS {q(c)}" for c in L] + ekler + (["l.[__sira] AS [__sira]"] if sira else [])
        tipler = self.acik_tasi(onceki)
        tipler.update(self.acik_tasi(sag, adlar))
        katilim = "LEFT JOIN" if tur == "leftouter" else "JOIN"
        return self.yeni(f"SELECT {', '.join(secim)} FROM {onceki} AS l {katilim} {sag} AS r ON {on}", tipler), sira

    def _parse_deseni(self):
        tur = "simple"
        if self.kelime_mi("kind"):
            self.i += 1
            self.bekle("=")
            t = self.bak()
            tur = self.ad_al()
            if tur not in ("simple", "regex"):
                raise KqlHatasi("parse türü simple ya da regex olabilir", t[2])
        if self.kelime_mi("flags"):
            raise KqlHatasi("parse flags= bu tezgahta desteklenmiyor", self.bak()[2])
        self.baglam(self.kaynak_cte)
        kaynak = self.toplama()
        self.bekle("with")
        parcalar, kolonlar = [], []
        while not (self.bak()[0] == "son" or self.isl_mi("|") or self.isl_mi(")") or self.isl_mi(";")):
            t = self.bak()
            if t[0] == "metin":
                self.i += 1
                lit = _metin_coz(t[1])
                parcalar.append(lit if tur == "regex" else re.escape(lit))
            elif self.isl_mi("*"):
                self.i += 1
                parcalar.append(".*?")
            elif t[0] == "ad":
                ad = self.ad_al()
                tip = "string"
                if self.isl_mi(":"):
                    self.i += 1
                    tt = self.bak()
                    tip = _TIP_ADI.get(self.ad_al())
                    if tip is None:
                        raise KqlHatasi(f"bilinmeyen tür: {tt[1]}", tt[2])
                desen = {"int": r"(-?\d+)", "long": r"(-?\d+)", "real": r"(-?\d+(?:\.\d+)?)"}.get(tip, "(.*?)")
                parcalar.append(desen)
                kolonlar.append((ad, tip))
            else:
                raise KqlHatasi("parse deseninde metin, * ya da sütun adı bekleniyordu", t[2])
        if not kolonlar:
            raise KqlHatasi("parse deseninde en az bir sütun olmalı", self.bak()[2])
        desen = "^" + "".join(parcalar) + "$"
        try:
            re.compile(desen)
        except re.error as e:
            raise KqlHatasi(f"parse deseni geçersiz: {e}", self.bak()[2])
        return kaynak, desen, kolonlar

    def _parse_sutunlari(self, onceki, sira, filtre):
        self.kaynak_cte = onceki
        kaynak, desen, kolonlar = self._parse_deseni()
        cols = self.sutunlar(onceki)
        tipler = self.acik_tasi(onceki)
        yeni = {}
        for n, (ad, tip) in enumerate(kolonlar, 1):
            ham = f"kql_parse({kaynak}, {sql_metin(desen)}, {n})"
            if tip in ("int", "long"):
                ham = f"CAST({ham} AS INTEGER)"
            elif tip == "real":
                ham = f"CAST({ham} AS REAL)"
            elif tip == "timespan":
                ham = f"kql_totimespan({ham})"
            elif tip == "bool":
                ham = f"(kql_kucuk({ham}) = 'true')"
            yeni[ad] = ham
            tipler.pop(ad, None)
            if tip in ("timespan", "bool"):
                tipler[ad] = tip
        secim = [f"{yeni[c]} AS {q(c)}" if c in yeni else q(c) for c in cols]
        secim += [f"{s} AS {q(a)}" for a, s in yeni.items() if a not in cols]
        if sira:
            secim.append("[__sira]")
        sql = f"SELECT {', '.join(secim)} FROM {onceki}"
        if filtre:
            sql += f" WHERE kql_parse_ok({kaynak}, {sql_metin(desen)})"
        return self.yeni(sql, tipler), sira

    def op_parse(self, onceki, sira):
        return self._parse_sutunlari(onceki, sira, False)

    def op_parse_where(self, onceki, sira):
        return self._parse_sutunlari(onceki, sira, True)

    def op_mv_expand(self, onceki, sira):
        self.baglam(onceki, sira)
        t = self.bak()
        if t[0] == "ad" and self.isl_mi("=", 1):
            self.i += 2
            hedef = t[1]
            kaynak = self.ifade()
        else:
            hedef = self.ad_al()
            kaynak = q(hedef)
        donustur = None
        if self.kelime_mi("to"):
            self.i += 1
            self.bekle("typeof")
            self.bekle("(")
            tt = self.bak()
            donustur = _TIP_ADI.get(self.ad_al())
            if donustur is None:
                raise KqlHatasi(f"bilinmeyen tür: {tt[1]}", tt[2])
            self.bekle(")")
        cols = self.sutunlar(onceki)
        dizi = f"kql_dizi(t.{kaynak})" if kaynak == q(hedef) else f"kql_dizi({kaynak})"
        deger = "je.value"
        if donustur in ("int", "long"):
            deger = "CAST(je.value AS INTEGER)"
        elif donustur == "real":
            deger = "CAST(je.value AS REAL)"
        elif donustur == "string":
            deger = "CAST(je.value AS TEXT)"
        secim = [f"{deger} AS {q(c)}" if c == hedef else f"t.{q(c)}" for c in cols]
        if hedef not in cols:
            secim.append(f"{deger} AS {q(hedef)}")
        if sira:
            secim.append("ROW_NUMBER() OVER (ORDER BY t.[__sira], je.id) AS [__sira]")
        tipler = self.acik_tasi(onceki)
        tipler.pop(hedef, None)
        if donustur in (None, "dynamic"):
            tipler[hedef] = "dynamic"
        return self.yeni(f"SELECT {', '.join(secim)} FROM {onceki} AS t, json_each({dizi}) AS je", tipler), sira

    # — mv-apply ve evaluate bag_unpack —
    def _alt_son(self):
        """Şu anki konumdan, parantez derinliği 0'da gelen ilk | ya da ) jetonunun indeksi."""
        derinlik, k = 0, self.i
        while k < len(self.j):
            t = self.j[k]
            if t[0] == "isl" and t[1] in ("(", "["):
                derinlik += 1
            elif t[0] == "isl" and t[1] in (")", "]"):
                if derinlik == 0:
                    return k
                derinlik -= 1
            elif t[0] == "isl" and t[1] == "|" and derinlik == 0:
                return k
            k += 1
        raise KqlHatasi("mv-apply alt sorgusu ')' ile kapanmalı", len(self.kaynak))

    def _enjekte(self, jetonlar):
        son = self._alt_son()
        konum = self.j[son][2]
        self.j[son:son] = [(tur, deger, konum) for tur, deger in jetonlar]

    def op_mv_apply(self, onceki, sira):
        """mv-apply [x =] dizi [to typeof(T)] on ( alt sorgu ): her satırın dizisine alt sorgu uygulanır.
        Alt sorguda where, extend, project, summarize, top ve take desteklenir; her işleç satır başına çalışır
        (gizli __mvr kimliğiyle; __mv önekli sütunlar sonuca girmez). Alt sorgu satır üretmeyen dış satırlar sonuçtan düşer;
        by'sız summarize ise her dış satıra bir satır verir (boş dizide count() = 0)."""
        self.baglam(onceki, sira)
        t = self.bak()
        if t[0] == "ad" and self.isl_mi("=", 1):
            self.i += 2
            hedef = t[1]
            kaynak = self.ifade()
        else:
            hedef = self.ad_al()
            kaynak = q(hedef)
        donustur = None
        if self.kelime_mi("to"):
            self.i += 1
            self.bekle("typeof")
            self.bekle("(")
            tt = self.bak()
            donustur = _TIP_ADI.get(self.ad_al())
            if donustur is None:
                raise KqlHatasi(f"bilinmeyen tür: {tt[1]}", tt[2])
            self.bekle(")")
        self.bekle("on")
        self.bekle("(")
        cols = self.sutunlar(onceki)
        numarali = self.yeni(f"SELECT t.*, ROW_NUMBER() OVER ({'ORDER BY t.[__sira]' if sira else ''}) AS [__mvr] "
                             f"FROM {onceki} AS t", self.acik_tasi(onceki))
        dizi = f"kql_dizi(t.{kaynak})" if kaynak == q(hedef) else f"kql_dizi({kaynak})"
        deger = {"int": "CAST(je.value AS INTEGER)", "long": "CAST(je.value AS INTEGER)",
                 "real": "CAST(je.value AS REAL)", "string": "CAST(je.value AS TEXT)"}.get(donustur, "je.value")
        alt = self.yeni(f"SELECT t.[__mvr], {deger} AS {q(hedef)} FROM {numarali} AS t, json_each({dizi}) AS je",
                        {hedef: "dynamic"} if donustur in (None, "dynamic") else None)
        ilk = True
        while True:
            if not ilk:
                if self.isl_mi(")"):
                    break
                self.bekle("|")
            ilk = False
            op = self.bak()
            if op[0] != "ad":
                raise KqlHatasi("mv-apply alt sorgusunda bir işleç bekleniyordu", op[2])
            self.i += 1
            if op[1] in ("where", "extend"):
                alt, _ = getattr(self, "op_" + op[1])(alt, False)
            elif op[1] == "project":
                self._enjekte([("isl", ","), ("ad", "__mvr")])
                alt, _ = self.op_project(alt, False)
            elif op[1] == "summarize":
                son = self._alt_son()
                by_var = any(self.j[k][0] == "ad" and self.j[k][1] == "by" for k in range(self.i, son))
                if by_var:
                    self._enjekte([("isl", ","), ("ad", "__mvr")])
                    alt, _ = self.op_summarize(alt, False)
                    continue
                # by'sız summarize boş girdide de tek satır verir (count() = 0): elemanı kalmayan satırlara
                # aynı toplamaların boş tablodaki sonucu eklenir
                bas = self.i
                bos, _ = self.op_summarize(self.yeni(f"SELECT * FROM {alt} WHERE 0", self.acik.get(alt)), False)
                self.i = bas
                self._enjekte([("ad", "by"), ("ad", "__mvr")])
                grup, _ = self.op_summarize(alt, False)
                ozet = [c for c in self.sutunlar(bos)]
                liste = ", ".join(q(c) for c in ozet)
                alt = self.yeni(f"SELECT [__mvr], {liste} FROM {grup} UNION ALL "
                                f"SELECT n.[__mvr], {', '.join('e.' + q(c) for c in ozet)} FROM {numarali} AS n, {bos} AS e "
                                f"WHERE n.[__mvr] NOT IN (SELECT [__mvr] FROM {grup})", self.acik.get(grup))
            elif op[1] in ("top", "take", "limit"):
                n = self._sayi()
                if op[1] == "top":
                    self.bekle("by")
                    self.baglam(alt, False)
                    e = self.ifade()
                    yon = "DESC"
                    if self.kelime_mi("asc") or self.kelime_mi("desc"):
                        yon = self.bak()[1].upper()
                        self.i += 1
                    sirala = f"{e} {yon} NULLS {'LAST' if yon == 'DESC' else 'FIRST'}"
                else:
                    sirala = "(SELECT NULL)"
                alt = self.yeni(f"SELECT * FROM (SELECT *, ROW_NUMBER() OVER (PARTITION BY [__mvr] ORDER BY {sirala}) "
                                f"AS [__mvrn] FROM {alt}) WHERE [__mvrn] <= {n}", self.acik.get(alt))
            else:
                raise KqlHatasi(f"mv-apply alt sorgusunda bu işleç desteklenmiyor: {op[1]} "
                                "(desteklenenler: where, extend, project, summarize, top, take)", op[2])
        self.bekle(")")
        alt_cols = [c for c in self.sutunlar(alt) if not c.startswith("__mv")]
        dis = [c for c in cols if c not in alt_cols]
        secim = [f"t.{q(c)}" for c in dis] + [f"s.{q(c)}" for c in alt_cols]
        if sira:
            secim.append("t.[__sira]")
        tipler = {c: v for c, v in self.acik_tasi(onceki).items() if c in dis}
        tipler.update({c: v for c, v in self.acik.get(alt, {}).items() if c in alt_cols})
        return self.yeni(f"SELECT {', '.join(secim)} FROM {numarali} AS t JOIN {alt} AS s ON t.[__mvr] = s.[__mvr]"
                         + (" ORDER BY t.[__sira]" if sira else ""), tipler), sira

    def op_evaluate(self, onceki, sira):
        t = self.bak()
        if not (t[0] == "ad" and t[1] == "bag_unpack" and self.isl_mi("(", 1)):
            raise KqlHatasi("bu tezgahta evaluate ile yalnız bag_unpack(sütun[, 'önek']) desteklenir", t[2])
        self.i += 2
        sutun = self.ad_al()
        onek = ""
        if self.virgul():
            m = self.bak()
            if m[0] != "metin":
                raise KqlHatasi("bag_unpack'in ikinci argümanı bir önek metni olmalı", m[2])
            self.i += 1
            onek = _metin_coz(m[1])
        self.bekle(")")
        cols = self.sutunlar(onceki)
        if sutun not in cols:
            raise KqlHatasi(f"böyle bir sütun yok: {sutun}", t[2])
        nesne = f"json_valid(t.{q(sutun)}) AND json_type(t.{q(sutun)}) = 'object'"
        anahtar_sql = self.with_sql(f"SELECT DISTINCT je.key FROM {onceki} AS t, json_each(t.{q(sutun)}) AS je WHERE {nesne}")
        anahtarlar = sorted(r[0] for r in self.sutun_bul.satirlar(anahtar_sql))
        kalan = [c for c in cols if c != sutun]
        cakisan = sorted({onek + a for a in anahtarlar} & set(kalan))
        if cakisan:
            raise KqlHatasi(f"bag_unpack: açılan anahtar var olan sütunla çakışıyor: {', '.join(cakisan)}", t[2])

        def yol(a):
            return "'$.\"" + a.replace("'", "''").replace('"', '\\"') + "\"'"
        secim = [f"t.{q(c)}" for c in kalan] + [
            f"(CASE WHEN {nesne} THEN json_extract(t.{q(sutun)}, {yol(a)}) END) AS {q(onek + a)}" for a in anahtarlar]
        if sira:
            secim.append("t.[__sira]")
        tipler = {c: v for c, v in self.acik_tasi(onceki).items() if c in kalan}
        tipler.update({onek + a: "dynamic" for a in anahtarlar})
        return self.yeni(f"SELECT {', '.join(secim)} FROM {onceki} AS t", tipler), sira

    # — ifadeler —
    def ifade(self):
        s = self.ve()
        while self.kelime_mi("or"):
            self.i += 1
            s = self.T(f"({s} OR {self.ve()})", "bool")
        return s

    def ve(self):
        s = self.karsilastirma()
        while self.kelime_mi("and"):
            self.i += 1
            s = self.T(f"({s} AND {self.karsilastirma()})", "bool")
        return s

    def _liste(self):
        self.bekle("(")
        liste = [self.ifade()]
        while self.virgul():
            liste.append(self.ifade())
        self.bekle(")")
        return liste

    def _dizi_sql(self, liste):
        if len(liste) == 1 and self.tipi(liste[0]) == "dynamic":
            return liste[0]
        return f"json_array({', '.join(liste)})"

    def karsilastirma(self):
        s = self.toplama()
        t = self.bak()
        if t[0] == "isl" and t[1] in ("==", "!=", "<", "<=", ">", ">=", "=~", "!~"):
            self.i += 1
            r = self.toplama()
            return self.T({"==": f"({s} = {r})", "!=": f"({s} <> {r})", "=~": f"kql_esit({s}, {r})",
                           "!~": f"(NOT kql_esit({s}, {r}))"}.get(t[1], f"({s} {t[1]} {r})"), "bool")
        olumsuz = False
        if t[0] == "isl" and t[1] == "!" and self.bak(1)[0] == "ad":
            olumsuz = True
            self.i += 1
            t = self.bak()
        sql = None
        if t[0] == "ad" and t[1] in _DIZGI:
            self.i += 1
            sql = f"{_DIZGI[t[1]]}({s}, {self.toplama()})"
        elif t[0] == "ad" and t[1] == "matches" and self.kelime_mi("regex", 1):
            self.i += 2
            sql = f"kql_regex({s}, {self.toplama()})"
        elif t[0] == "ad" and t[1] in ("in", "in~"):
            self.i += 1
            liste = self._liste()
            if len(liste) == 1 and self.tipi(liste[0]) == "dynamic":
                deger = "kql_kucuk(value)" if t[1] == "in~" else "value"
                sol = f"kql_kucuk({s})" if t[1] == "in~" else s
                sql = f"({sol} IN (SELECT {deger} FROM json_each({liste[0]})))"
            elif t[1] == "in":
                sql = f"({s} IN ({', '.join(liste)}))"
            else:
                sql = f"(kql_kucuk({s}) IN ({', '.join('kql_kucuk(' + x + ')' for x in liste)}))"
        elif t[0] == "ad" and t[1] in ("has_any", "has_all"):
            self.i += 1
            sql = f"kql_{t[1]}({s}, {self._dizi_sql(self._liste())})"
        elif t[0] == "ad" and t[1] == "between":
            self.i += 1
            self.bekle("(")
            a = self.toplama()
            self.bekle("..")
            b = self.toplama()
            self.bekle(")")
            sql = f"({s} BETWEEN {a} AND {b})"
        if sql is None:
            if olumsuz:
                raise KqlHatasi("! işaretinden sonra contains, has, startswith, endswith, in, has_any ya da between "
                                "bekleniyordu", t[2])
            return s
        return self.T(f"(NOT {sql})" if olumsuz else sql, "bool")

    def toplama(self):
        s = self.carpma()
        while self.isl_mi("+") or self.isl_mi("-"):
            op = self.bak()[1]
            self.i += 1
            r = self.carpma()
            ts, tr = self.tipi(s), self.tipi(r)
            if ts == "datetime" and tr == "timespan":
                s = self.T(f"kql_dt_add({s}, {'-' if op == '-' else ''}({r}))", "datetime")
            elif ts == "timespan" and tr == "datetime" and op == "+":
                s = self.T(f"kql_dt_add({r}, {s})", "datetime")
            elif ts == "datetime" and tr == "datetime" and op == "-":
                s = self.T(f"kql_dt_diff({s}, {r})", "timespan")
            elif ts == "timespan" or tr == "timespan":
                s = self.T(f"({s} {op} {r})", "timespan")
            else:
                s = f"({s} {op} {r})"
        return s

    def carpma(self):
        s = self.tekli()
        while self.isl_mi("*") or self.isl_mi("/") or self.isl_mi("%"):
            op = self.bak()[1]
            self.i += 1
            r = self.tekli()
            ts, tr = self.tipi(s), self.tipi(r)
            if op == "/" and ts == "timespan" and tr == "timespan":
                s = self.T(f"(CAST({s} AS REAL) / {r})", "real")
            elif ts == "timespan" or tr == "timespan":
                s = self.T(f"({s} {op} {r})", "timespan")
            else:
                s = f"({s} {op} {r})"
        return s

    def tekli(self):
        if self.isl_mi("-"):
            self.i += 1
            ic = self.tekli()
            return self.T(f"(-{ic})", self.tipi(ic))
        return self.sonek(self.birincil())

    def sonek(self, s):
        """Dinamik değerde .ad, ["ad"] ve [0] erişimi."""
        while True:
            if self.isl_mi(".") and self.bak(1)[0] == "ad":
                self.i += 1
                anahtar = self.ad_al()
                s = self.T(f"kql_dyn_get({s}, {sql_metin(anahtar)})", "dynamic")
            elif self.isl_mi("["):
                self.i += 1
                anahtar = self.ifade()
                self.bekle("]")
                s = self.T(f"kql_dyn_get({s}, {anahtar})", "dynamic")
            else:
                return s

    def birincil(self):
        t = self.bak()
        if t[0] == "sayi":
            self.i += 1
            return self.T(t[1], "real" if "." in t[1] else "long")
        if t[0] == "metin":
            self.i += 1
            return self.T(sql_metin(_metin_coz(t[1])), "string")
        if t[0] == "tarih":
            self.i += 1
            try:
                return self.T(sql_metin(_tarih(t[1])), "datetime")
            except KqlHatasi as e:
                raise KqlHatasi(e.msg, t[2])
        if t[0] == "sure":
            self.i += 1
            return self.T(str(_sure_saniye(t[1])), "timespan")
        if t[0] == "dinamik":
            self.i += 1
            return self.T(sql_metin(_dinamik_json(t[1], t[2])), "dynamic")
        if self.isl_mi("("):
            self.i += 1
            s = self.ifade()
            self.bekle(")")
            return self.T(f"({s})", self.tipi(s))
        if t[0] == "ad":
            if t[1] in ("true", "false"):
                self.i += 1
                return self.T("1" if t[1] == "true" else "0", "bool")
            if t[1] == "null" and not self.isl_mi("(", 1):
                self.i += 1
                return "NULL"
            if self.isl_mi("(", 1):
                return self.fonksiyon()
            self.i += 1
            if t[1] in self.letler and self.letler[t[1]][0] == "skaler":
                _, sql, tip = self.letler[t[1]]
                return self.T(f"({sql})", tip)
            return self.T(q(t[1]), self.kolon_tipi(t[1]))
        raise KqlHatasi(f"beklenmeyen: '{t[1] or 'sorgunun sonu'}'", t[2])

    def fonksiyon(self):
        ad_t = self.bak()
        ad = ad_t[1]
        self.i += 2
        if ad == "toscalar":
            b = self.baglam_sakla()
            cte, _ = self.sorgu()
            self.bekle(")")
            self.baglam_don(b)
            cols = self.sutunlar(cte)
            tip = self.cte_tipleri(cte).get(cols[0])
            return self.T(f"(SELECT {q(cols[0])} FROM {cte} LIMIT 1)", tip)
        if ad == "bin":
            x = self.ifade()
            self.bekle(",")
            t = self.bak()
            if t[0] == "sure" and self.tipi(x) == "timespan":
                self.i += 1
                n = _sure_saniye(t[1])
                sql = self.T(f"(CAST(({x}) / {n} AS INTEGER) * {n})", "timespan")
            elif t[0] == "sure":
                self.i += 1
                sql = self.T(self._bin_sure(x, t), "datetime")
            else:
                n = self.ifade()
                sql = f"(CAST(({x}) / ({n}) AS INTEGER) * ({n}))"
            self.bekle(")")
            return sql
        if ad == "ago":
            t = self.bak()
            if t[0] != "sure":
                raise KqlHatasi("ago() içinde bir süre bekleniyordu (ör. ago(1d), ago(6h))", t[2])
            self.i += 1
            self.bekle(")")
            return self.T(f"kql_dt_add('{SIMDI}', -{_sure_saniye(t[1])})", "datetime")
        args = []
        if not self.isl_mi(")"):
            args.append(self.ifade())
            while self.virgul():
                args.append(self.ifade())
        self.bekle(")")
        return self._fn(ad, args, ad_t[2])

    def _bin_sure(self, x, t):
        n, birim = _sure(t[1])
        n = int(n)
        if birim == "d" and n == 1:
            return f"(date({x}) || ' 00:00')"
        if birim == "h" and 24 % n == 0:
            return f"(date({x}) || ' ' || printf('%02d:00', (CAST(strftime('%H', {x}) AS INTEGER) / {n}) * {n}))"
        if birim == "m" and 60 % n == 0:
            return f"(strftime('%Y-%m-%d %H:', {x}) || printf('%02d', (CAST(strftime('%M', {x}) AS INTEGER) / {n}) * {n}))"
        raise KqlHatasi("bin() zaman için 1d, 24'ü bölen saatler (1h, 6h) ya da 60'ı bölen dakikalar (15m) destekliyor", t[2])

    def _sirali(self, ad, sql, tip, konum):
        if not self.girdi_sirali:
            raise KqlHatasi(f"{ad}() sıralı bir girdi ister: önce sort by, top ya da serialize kullan", konum)
        self.sayac += 1
        yad = f"__y{self.sayac}"
        self.yardimci.append((yad, sql))
        return self.T(q(yad), tip)

    def _fn(self, ad, a, konum):
        def say(n):
            if len(a) not in (n if isinstance(n, tuple) else (n,)):
                raise KqlHatasi(f"{ad}() fonksiyonuna yanlış sayıda argüman verildi", konum)

        tip0 = self.tipi(a[0]) if a else None
        if ad in _TIP_ADI and a == ["NULL"]:
            return self.T("NULL", _TIP_ADI[ad])                       # int(null), timespan(null) …
        if ad == "count":
            say((0, 1))
            return self.T("COUNT(*)" if not a else f"COUNT({a[0]})", "long")
        if ad in ("prev", "next"):
            say((1, 2, 3))
            fn = "LAG" if ad == "prev" else "LEAD"
            return self._sirali(ad, f"{fn}({', '.join(a)}) OVER (ORDER BY [__sira])", tip0, konum)
        if ad == "row_number":
            say((0, 1, 2))
            if len(a) == 2:
                return self._sirali(ad, f"kql_rn({a[0]}, {a[1]}) {_PENCERE}", "long", konum)
            bas = a[0] if a else "1"
            return self._sirali(ad, f"(ROW_NUMBER() OVER (ORDER BY [__sira]) + ({bas}) - 1)", "long", konum)
        if ad == "row_cumsum":
            say((1, 2))
            return self._sirali(ad, f"kql_cumsum({a[0]}, {a[1] if len(a) == 2 else 0}) {_PENCERE}", tip0, konum)
        if ad == "row_window_session":
            say((3, 4))
            if self.tipi(a[1]) != "timespan" or self.tipi(a[2]) != "timespan":
                raise KqlHatasi("row_window_session(Zaman, ilkten_en_fazla, komşular_arası_en_fazla) süre ister "
                                "(ör. 1h, 15m)", konum)
            return self._sirali(ad, f"kql_rws({a[0]}, {a[1]}, {a[2]}, {a[3] if len(a) == 4 else 0}) {_PENCERE}",
                                "datetime", konum)
        toplama = {"countif": ("COUNT(CASE WHEN {0} THEN 1 END)", "long"),   # boş girdide 0
                   "dcount": ("COUNT(DISTINCT {0})", "long"),
                   "sum": ("SUM({0})", None), "avg": ("AVG({0})", None), "min": ("MIN({0})", None),
                   "max": ("MAX({0})", None), "take_any": ("MIN({0})", None),
                   "make_list": ("json_group_array({0})", "dynamic"),
                   "make_set": ("json_group_array(DISTINCT {0})", "dynamic"),
                   "stdev": ("kql_stdev({0})", "real"), "variance": ("kql_variance({0})", "real")}
        if ad in toplama:
            say(1)
            sablon, tip = toplama[ad]
            if tip is None:
                tip = tip0 if tip0 in ("timespan", "datetime") else ("real" if ad == "avg" else tip0)
            return self.T(sablon.format(a[0]), tip)
        kosullu = {"dcountif": "COUNT(DISTINCT CASE WHEN {1} THEN {0} END)",
                   "sumif": "coalesce(SUM(CASE WHEN {1} THEN {0} END), 0)",
                   "avgif": "AVG(CASE WHEN {1} THEN {0} END)"}
        if ad in kosullu:
            say(2)
            return self.T(kosullu[ad].format(a[0], a[1]), tip0 if tip0 == "timespan" else None)
        if ad == "percentile":
            say(2)
            return self.T(f"kql_pct({a[0]}, {a[1]})", tip0)
        tek = {"strlen": ("length({0})", "long"), "tolower": ("kql_kucuk({0})", "string"),
               "toupper": ("kql_buyuk({0})", "string"),
               "isnull": ("({0} IS NULL)", "bool"), "isnotnull": ("({0} IS NOT NULL)", "bool"),
               "isempty": ("({0} IS NULL OR {0} = '')", "bool"),
               "isnotempty": ("({0} IS NOT NULL AND {0} <> '')", "bool"),
               "toint": ("CAST({0} AS INTEGER)", "long"), "tolong": ("CAST({0} AS INTEGER)", "long"),
               "todouble": ("CAST({0} AS REAL)", "real"), "toreal": ("CAST({0} AS REAL)", "real"),
               "todatetime": ("{0}", "datetime"), "totimespan": ("kql_totimespan({0})", "timespan"),
               "hourofday": ("CAST(strftime('%H', {0}) AS INTEGER)", "long"),
               "dayofmonth": ("CAST(strftime('%d', {0}) AS INTEGER)", "long"),
               "getmonth": ("CAST(strftime('%m', {0}) AS INTEGER)", "long"),
               "getyear": ("CAST(strftime('%Y', {0}) AS INTEGER)", "long"),
               "dayofweek": ("(CAST(strftime('%w', {0}) AS INTEGER) * 86400)", "timespan"),
               "startofday": ("(date({0}) || ' 00:00')", "datetime"),
               "startofweek": ("(date({0}, '-6 days', 'weekday 0') || ' 00:00')", "datetime"),
               "startofmonth": ("(date({0}, 'start of month') || ' 00:00')", "datetime"),
               "abs": ("abs({0})", None), "not": ("(NOT {0})", "bool"),
               "parse_json": ("kql_json({0})", "dynamic"), "todynamic": ("kql_json({0})", "dynamic"),
               "array_length": ("kql_dizi_uzunluk({0})", "long"), "bag_keys": ("kql_anahtarlar({0})", "dynamic"),
               "array_sort_asc": ("kql_sirala({0}, 0)", "dynamic"), "array_sort_desc": ("kql_sirala({0}, 1)", "dynamic"),
               "parse_url": ("kql_parse_url({0})", "dynamic"), "parse_ipv4": ("kql_ipv4({0})", "long"),
               "ipv4_is_private": ("kql_ipv4_ozel({0})", "bool")}
        if ad in tek:
            say(1)
            sablon, tip = tek[ad]
            return self.T(sablon.format(a[0]), tip if tip else tip0)
        if ad == "tostring":
            say(1)
            if tip0 == "timespan":
                return self.T(f"kql_ts_fmt({a[0]})", "string")
            if tip0 == "bool":
                return self.T(f"(CASE WHEN {a[0]} THEN 'true' ELSE 'false' END)", "string")
            return self.T(f"CAST({a[0]} AS TEXT)", "string")
        if ad == "now":
            say(0)
            return self.T(f"'{SIMDI}'", "datetime")
        if ad == "round":
            say((1, 2))
            return self.T(f"round({', '.join(a)})", "real")
        if ad == "substring":
            say((2, 3))
            return self.T(f"substr({a[0]}, ({a[1]}) + 1{', ' + a[2] if len(a) == 3 else ''})", "string")
        if ad == "strcat":
            if not a:
                raise KqlHatasi("strcat() en az bir argüman ister", konum)
            parcalar = []
            for x in a:
                tx = self.tipi(x)
                if tx == "timespan":
                    x = f"kql_ts_fmt({x})"
                elif tx == "bool":
                    x = f"(CASE WHEN {x} THEN 'true' ELSE 'false' END)"
                parcalar.append(f"coalesce({x}, '')")
            return self.T("(" + " || ".join(parcalar) + ")", "string")
        if ad == "replace_string":
            say(3)
            return self.T(f"replace({a[0]}, {a[1]}, {a[2]})", "string")
        if ad == "replace_regex":
            say(3)
            return self.T(f"kql_replace_regex({a[0]}, {a[1]}, {a[2]})", "string")
        if ad in ("iff", "iif"):
            say(3)
            return self.T(f"(CASE WHEN {a[0]} THEN {a[1]} ELSE {a[2]} END)", self.tipi(a[1]) or self.tipi(a[2]))
        if ad == "case":
            if len(a) < 3 or len(a) % 2 == 0:
                raise KqlHatasi("case(koşul1, değer1, ..., varsayılan) biçiminde tek sayıda argüman bekleniyordu", konum)
            dallar = " ".join(f"WHEN {a[n]} THEN {a[n + 1]}" for n in range(0, len(a) - 1, 2))
            return self.T(f"(CASE {dallar} ELSE {a[-1]} END)", self.tipi(a[1]))
        if ad == "coalesce":
            if len(a) < 2:
                raise KqlHatasi("coalesce() en az iki argüman ister", konum)
            return self.T(f"coalesce({', '.join(a)})", tip0)
        if ad == "extract":
            say((3, 4))
            return self.T(f"kql_extract({a[0]}, {a[1]}, {a[2]})", "string")
        if ad == "extract_all":
            say(2)
            return self.T(f"kql_extract_all({a[0]}, {a[1]})", "dynamic")
        if ad == "split":
            say((2, 3))
            if len(a) == 3:
                return self.T(f"kql_dyn_get(kql_split({a[0]}, {a[1]}), {a[2]})", "dynamic")
            return self.T(f"kql_split({a[0]}, {a[1]})", "dynamic")
        if ad == "strcat_array":
            say(2)
            return self.T(f"kql_strcat_array({a[0]}, {a[1]})", "string")
        if ad == "set_has_element":
            say(2)
            return self.T(f"kql_has_element({a[0]}, {a[1]})", "bool")
        if ad in ("trim", "trim_start", "trim_end"):
            say(2)
            return self.T(f"kql_{ad}({a[0]}, {a[1]})", "string")
        if ad == "indexof":
            say(2)
            return self.T(f"(instr({a[0]}, {a[1]}) - 1)", "long")
        if ad == "countof":
            say(2)
            return self.T(f"kql_countof({a[0]}, {a[1]})", "long")
        if ad == "ipv4_is_in_range":
            say(2)
            return self.T(f"kql_ipv4_aralik({a[0]}, {a[1]})", "bool")
        if ad == "format_datetime":
            say(2)
            return self.T(f"kql_fmt_dt({a[0]}, {a[1]})", "string")
        if ad == "format_timespan":
            say(2)
            return self.T(f"kql_fmt_ts({a[0]}, {a[1]})", "string")
        if ad == "datetime_part":
            say(2)
            return self.T(f"kql_dt_part({a[0]}, {a[1]})", "long")
        if ad == "datetime_add":
            say(3)
            return self.T(f"kql_dt_add_part({a[0]}, {a[1]}, {a[2]})", "datetime")
        if ad == "datetime_diff":
            say(3)
            birim = a[0].strip("'")
            if birim not in ("year", "quarter", "month", "week", "day", "hour", "minute", "second"):
                raise KqlHatasi("datetime_diff birimi 'year', 'month', 'week', 'day', 'hour', 'minute' ya da "
                                "'second' olmalı", konum)
            return self.T(f"kql_dtdiff({a[0]}, {a[1]}, {a[2]})", "long")
        raise KqlHatasi(f"bu fonksiyon desteklenmiyor: {ad}()", konum)


def cevir(kaynak, sutun_bul):
    c = _Cevirici(kaynak, sutun_bul)
    if not c.j:
        raise KqlHatasi("sorgu boş", 0)
    while c.kelime_mi("let"):
        c.let_ifadesi()
    if c.bak()[0] == "son":
        raise KqlHatasi("let ifadelerinden sonra bir sorgu bekleniyordu", len(kaynak))
    ad, sira = c.sorgu()
    if c.isl_mi(";"):
        c.i += 1
    if c.i < len(c.j):
        t = c.bak()
        raise KqlHatasi(f"beklenmeyen: '{t[1]}' (iki sorguyu boş bir satırla ayır; işleçlerin önüne | koy)", t[2])
    tipler = c.acik.get(ad, {})
    secim = []
    for col in c.sutunlar(ad):
        tip = tipler.get(col)
        if tip == "timespan":
            secim.append(f"kql_ts_fmt({q(col)}) AS {q(col)}")
        elif tip == "bool":
            secim.append(f"(CASE WHEN {q(col)} IS NULL THEN NULL WHEN {q(col)} THEN 'true' ELSE 'false' END) AS {q(col)}")
        else:
            secim.append(q(col))
    return c.with_sql(f"SELECT {', '.join(secim) or '*'} FROM {ad}" + (" ORDER BY [__sira]" if sira else ""))


# — SQLite tarafı: Python fonksiyonları —

def _dt_coz(x):
    if x is None:
        return None
    s = str(x).strip().replace("T", " ").rstrip("Z")
    for bicim in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, bicim)
        except ValueError:
            continue
    return None


def _dt_yaz(d):
    if d is None:
        return None
    if d.second or d.microsecond:
        return d.strftime("%Y-%m-%d %H:%M:%S")
    return d.strftime("%Y-%m-%d %H:%M")


def _ts_fmt(s):
    if s is None:
        return None
    try:
        s = float(s)
    except (TypeError, ValueError):
        return None
    isaret = "-" if s < 0 else ""
    s = abs(s)
    tam = int(s)
    kesir = s - tam
    gun, kalan = divmod(tam, 86400)
    saat, kalan = divmod(kalan, 3600)
    dk, sn = divmod(kalan, 60)
    metin = f"{isaret}{str(gun) + '.' if gun else ''}{saat:02d}:{dk:02d}:{sn:02d}"
    if kesir > 1e-9:
        metin += "." + f"{kesir:.7f}"[2:]
    return metin


def _ts_coz(x):
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return x
    m = re.fullmatch(r"\s*(-)?(?:(\d+)\.)?(\d{1,2}):(\d{2})(?::(\d{2})(?:\.(\d+))?)?\s*", str(x))
    if not m:
        m2 = re.fullmatch(r"\s*(\d+(?:\.\d+)?)(ms|d|h|m|s)\s*", str(x))
        return _sure_saniye(m2.group(1) + m2.group(2)) if m2 else None
    isaret, gun, saat, dk, sn, kesir = m.groups()
    toplam = int(gun or 0) * 86400 + int(saat) * 3600 + int(dk) * 60 + int(sn or 0)
    if kesir:
        toplam += float("0." + kesir)
    return -toplam if isaret else toplam


def _dyn(x):
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return x
    try:
        return json.loads(x)
    except (ValueError, TypeError):
        return x


def _dyn_cikti(e):
    if isinstance(e, bool):
        return int(e)
    if isinstance(e, (dict, list)):
        return json.dumps(e, ensure_ascii=False, separators=(",", ":"))
    return e


def _dizi(x):
    v = _dyn(x)
    return v if isinstance(v, list) else None


class _Pct:
    def __init__(self):
        self.v, self.p = [], 50

    def step(self, x, p):
        if x is not None:
            self.v.append(x)
        if p is not None:
            self.p = float(p)

    def finalize(self):
        if not self.v:
            return None
        v = sorted(self.v)
        sira = max(1, math.ceil(self.p / 100 * len(v)))
        return v[min(sira, len(v)) - 1]


class _Stdev:
    def __init__(self):
        self.v = []

    def step(self, x):
        if x is not None:
            self.v.append(float(x))

    def varyans(self):
        n = len(self.v)
        if n < 2:
            return 0.0 if n == 1 else None
        ort = sum(self.v) / n
        return sum((x - ort) ** 2 for x in self.v) / (n - 1)

    def finalize(self):
        v = self.varyans()
        return None if v is None else math.sqrt(v)


class _Varyans(_Stdev):
    def finalize(self):
        return self.varyans()


class _Pencere:
    def __init__(self):
        self.d = None

    def inverse(self, *a):
        pass

    def value(self):
        return self.d

    def finalize(self):
        return self.d


class _Rn(_Pencere):
    def step(self, bas, yeniden):
        self.d = bas if (self.d is None or yeniden) else self.d + 1


class _Cumsum(_Pencere):
    def step(self, x, yeniden):
        x = x or 0
        self.d = x if (self.d is None or yeniden) else self.d + x


class _Rws(_Pencere):
    def __init__(self):
        super().__init__()
        self.bas = self.son = None

    def step(self, zaman, ilk, komsu, yeniden):
        t = _dt_coz(zaman)
        if t is None:
            self.d = None
            return
        if (self.bas is None or yeniden or (t - self.son).total_seconds() > komsu
                or (t - self.bas).total_seconds() > ilk):
            self.bas, self.d = t, zaman
        self.son = t


_OZEL_AGLAR = None


def fonksiyonlari_kaydet(db):
    """KQL'in dizgi işleçlerini ve fonksiyonlarını SQLite'a Python fonksiyonu olarak tanıt."""
    import ipaddress
    global _OZEL_AGLAR
    if _OZEL_AGLAR is None:
        _OZEL_AGLAR = [ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")]

    def m(x):
        return "" if x is None else str(x)

    def terim(a, b, bayrak):
        return re.search(r"(?<!\w)" + re.escape(m(b)) + r"(?!\w)", m(a), bayrak) is not None

    def regex(a, desen):
        try:
            return int(re.search(m(desen), m(a)) is not None)
        except re.error:
            return 0

    def cikar(desen, grup, metin):
        try:
            r = re.search(m(desen), m(metin))
        except re.error:
            return None
        if not r:
            return None
        try:
            return r.group(int(grup))
        except (IndexError, ValueError):
            return None

    def cikar_hepsi(desen, metin):
        try:
            rx = re.compile(m(desen))
        except re.error:
            return None
        out = []
        for r in rx.finditer(m(metin)):
            if rx.groups == 0:
                out.append(r.group(0))
            elif rx.groups == 1:
                out.append(r.group(1))
            else:
                out.append(list(r.groups()))
        return json.dumps(out, ensure_ascii=False, separators=(",", ":"))

    _parse_onbellek = {}

    def parse_esles(metin, desen):
        rx = _parse_onbellek.get(desen)
        if rx is None:
            rx = _parse_onbellek[desen] = re.compile(desen, re.S)
        return rx.match(m(metin))

    def parse(metin, desen, n):
        r = parse_esles(metin, desen)
        return r.group(n) if r else None

    def dyn_get(x, k):
        v = _dyn(x)
        if isinstance(v, list) and isinstance(k, (int, float)):
            n = int(k)
            return _dyn_cikti(v[n]) if -len(v) <= n < len(v) else None
        if isinstance(v, dict):
            return _dyn_cikti(v.get(str(k)))
        return None

    def json_norm(x):
        v = _dyn(x)
        return _dyn_cikti(v) if not isinstance(v, str) else v

    def dizi_sql(x):
        """mv-expand için: dizi ise kendisi, nesne ise anahtar-değer nesneleri, skaler ise tek elemanlı dizi."""
        v = _dyn(x)
        if isinstance(v, list):
            return json.dumps(v, ensure_ascii=False)
        if isinstance(v, dict):
            return json.dumps([{a: b} for a, b in v.items()], ensure_ascii=False)
        if v is None:
            return "[]"
        return json.dumps([v], ensure_ascii=False)

    def sirala(x, azalan):
        v = _dizi(x)
        if v is None:
            return None
        dolu = [e for e in v if e is not None]
        try:
            dolu.sort(reverse=bool(azalan))
        except TypeError:
            dolu.sort(key=str, reverse=bool(azalan))
        return json.dumps(dolu + [None] * (len(v) - len(dolu)), ensure_ascii=False, separators=(",", ":"))

    def parse_url(u):
        from urllib.parse import urlsplit, parse_qsl
        try:
            p = urlsplit(m(u))
            return json.dumps({"Scheme": p.scheme, "Host": p.hostname or "", "Port": str(p.port or ""),
                               "Path": p.path, "Username": p.username or "", "Password": p.password or "",
                               "Query Parameters": dict(parse_qsl(p.query, keep_blank_values=True)),
                               "Fragment": p.fragment}, ensure_ascii=False, separators=(",", ":"))
        except ValueError:
            return None

    def ipv4(x):
        try:
            return int(ipaddress.IPv4Address(m(x).strip()))
        except ValueError:
            return None

    def ipv4_ozel(x):
        try:
            a = ipaddress.IPv4Address(m(x).strip())
        except ValueError:
            return None
        return int(any(a in n for n in _OZEL_AGLAR))

    def ipv4_aralik(x, aralik):
        try:
            a = ipaddress.IPv4Address(m(x).strip())
            n = ipaddress.ip_network(m(aralik).strip(), strict=False)
        except ValueError:
            return None
        return int(a in n)

    def dt_add(x, sn):
        d = _dt_coz(x)
        if d is None or sn is None:
            return None
        return _dt_yaz(d + timedelta(seconds=float(sn)))

    def dt_diff(a, b):
        da, db_ = _dt_coz(a), _dt_coz(b)
        if da is None or db_ is None:
            return None
        s = (da - db_).total_seconds()
        return int(s) if s == int(s) else s

    def dt_add_part(birim, n, x):
        d = _dt_coz(x)
        if d is None or n is None:
            return None
        n = int(n)
        if birim in ("year", "month", "quarter"):
            ay = d.month - 1 + n * {"year": 12, "quarter": 3, "month": 1}[birim]
            yil, ay = d.year + ay // 12, ay % 12 + 1
            import calendar
            gun = min(d.day, calendar.monthrange(yil, ay)[1])
            return _dt_yaz(d.replace(year=yil, month=ay, day=gun))
        sn = {"week": 604800, "day": 86400, "hour": 3600, "minute": 60, "second": 1}.get(birim)
        return None if sn is None else _dt_yaz(d + timedelta(seconds=n * sn))

    def dtdiff(birim, a, b):
        """KQL'deki gibi: aradaki süre değil, geçilen birim sınırlarının sayısı."""
        da, db_ = _dt_coz(a), _dt_coz(b)
        if da is None or db_ is None:
            return None
        if birim == "year":
            return da.year - db_.year
        if birim == "quarter":
            return (da.year - db_.year) * 4 + (da.month - 1) // 3 - (db_.month - 1) // 3
        if birim == "month":
            return (da.year - db_.year) * 12 + da.month - db_.month
        if birim == "week":
            def hafta(d):
                return (d.date() - timedelta(days=(d.weekday() + 1) % 7)).toordinal()
            return (hafta(da) - hafta(db_)) // 7
        kes = {"day": "%Y-%m-%d", "hour": "%Y-%m-%d %H", "minute": "%Y-%m-%d %H:%M", "second": "%Y-%m-%d %H:%M:%S"}
        bicim = kes[birim]
        sa = datetime.strptime(da.strftime(bicim), bicim)
        sb = datetime.strptime(db_.strftime(bicim), bicim)
        bolen = {"day": 86400, "hour": 3600, "minute": 60, "second": 1}[birim]
        return int(round((sa - sb).total_seconds() / bolen))

    def dt_part(birim, x):
        d = _dt_coz(x)
        if d is None:
            return None
        return {"year": d.year, "quarter": (d.month - 1) // 3 + 1, "month": d.month, "day": d.day, "hour": d.hour,
                "minute": d.minute, "second": d.second, "dayofyear": d.timetuple().tm_yday,
                "weekofyear": d.isocalendar()[1]}.get(m(birim).lower())

    def fmt_dt(x, bicim):
        d = _dt_coz(x)
        if d is None:
            return None
        esle = {"yyyy": "%Y", "yy": "%y", "MM": "%m", "dd": "%d", "HH": "%H", "hh": "%I", "mm": "%M", "ss": "%S",
                "tt": "%p", "M": str(d.month), "d": str(d.day), "H": str(d.hour), "m": str(d.minute), "s": str(d.second)}
        parcalar = re.findall(r"yyyy|yy|MM|dd|HH|hh|mm|ss|tt|[MdHms]|.", m(bicim))
        return "".join(d.strftime(esle[p]) if esle.get(p, "").startswith("%") else esle.get(p, p) for p in parcalar)

    def fmt_ts(x, bicim):
        if x is None:
            return None
        s = abs(float(x))
        g, k = divmod(int(s), 86400)
        sa, k = divmod(k, 3600)
        dk, sn = divmod(k, 60)
        esle = {"d": str(g), "hh": f"{sa:02d}", "h": str(sa), "mm": f"{dk:02d}", "m": str(dk), "ss": f"{sn:02d}",
                "s": str(sn)}
        parcalar = re.findall(r"hh|mm|ss|[dhms]|.", m(bicim))
        return "".join(esle.get(p, p) for p in parcalar)

    def trim(desen, x, bas=True, son=True):
        if x is None:
            return None
        s = str(x)
        try:
            if bas:
                s = re.sub(r"^(?:" + m(desen) + r")+", "", s)
            if son:
                s = re.sub(r"(?:" + m(desen) + r")+$", "", s)
        except re.error:
            return s
        return s

    def has_any(x, dizi, hepsi=False):
        terimler = _dizi(dizi) or []
        bulunan = [terim(x, t, re.I) for t in terimler if t is not None]
        return int(all(bulunan) if hepsi else any(bulunan))

    def replace_regex(x, desen, yeni):
        if x is None:
            return None
        try:
            return re.sub(m(desen), m(yeni).replace("\\0", "\\g<0>"), str(x))
        except re.error:
            return x

    fonksiyonlar = {
        "kql_contains": (2, lambda a, b: int(m(b).lower() in m(a).lower())),
        "kql_contains_cs": (2, lambda a, b: int(m(b) in m(a))),
        "kql_has": (2, lambda a, b: int(terim(a, b, re.I))),
        "kql_has_cs": (2, lambda a, b: int(terim(a, b, 0))),
        "kql_hasprefix": (2, lambda a, b: int(re.search(r"(?<!\w)" + re.escape(m(b)), m(a), re.I) is not None)),
        "kql_hassuffix": (2, lambda a, b: int(re.search(re.escape(m(b)) + r"(?!\w)", m(a), re.I) is not None)),
        "kql_startswith": (2, lambda a, b: int(m(a).lower().startswith(m(b).lower()))),
        "kql_startswith_cs": (2, lambda a, b: int(m(a).startswith(m(b)))),
        "kql_endswith": (2, lambda a, b: int(m(a).lower().endswith(m(b).lower()))),
        "kql_endswith_cs": (2, lambda a, b: int(m(a).endswith(m(b)))),
        "kql_esit": (2, lambda a, b: int(m(a).lower() == m(b).lower())),
        "kql_kucuk": (1, lambda a: None if a is None else str(a).lower()),
        "kql_buyuk": (1, lambda a: None if a is None else str(a).upper()),
        "kql_regex": (2, regex),
        "kql_extract": (3, cikar),
        "kql_extract_all": (2, cikar_hepsi),
        "kql_parse": (3, parse),
        "kql_parse_ok": (2, lambda x, d: int(parse_esles(x, d) is not None)),
        "kql_dyn_get": (2, dyn_get),
        "kql_json": (1, json_norm),
        "kql_dizi": (1, dizi_sql),
        "kql_dizi_uzunluk": (1, lambda x: None if _dizi(x) is None else len(_dizi(x))),
        "kql_anahtarlar": (1, lambda x: json.dumps(list(_dyn(x).keys()), ensure_ascii=False, separators=(",", ":"))
                           if isinstance(_dyn(x), dict) else None),
        "kql_sirala": (2, sirala),
        "kql_split": (2, lambda x, d: None if x is None else json.dumps(str(x).split(m(d)), ensure_ascii=False,
                                                                        separators=(",", ":"))),
        "kql_strcat_array": (2, lambda x, d: None if _dizi(x) is None else m(d).join(
            "" if e is None else (json.dumps(e, ensure_ascii=False) if isinstance(e, (dict, list)) else str(e))
            for e in _dizi(x))),
        "kql_has_element": (2, lambda x, v: int(v in (_dizi(x) or []))),
        "kql_has_any": (2, lambda x, d: has_any(x, d)),
        "kql_has_all": (2, lambda x, d: has_any(x, d, True)),
        "kql_trim": (2, lambda d, x: trim(d, x)),
        "kql_trim_start": (2, lambda d, x: trim(d, x, son=False)),
        "kql_trim_end": (2, lambda d, x: trim(d, x, bas=False)),
        "kql_countof": (2, lambda x, a: None if x is None else (m(x).count(m(a)) if a else 0)),
        "kql_replace_regex": (3, replace_regex),
        "kql_parse_url": (1, parse_url),
        "kql_ipv4": (1, ipv4),
        "kql_ipv4_ozel": (1, ipv4_ozel),
        "kql_ipv4_aralik": (2, ipv4_aralik),
        "kql_dt_add": (2, dt_add),
        "kql_dt_diff": (2, dt_diff),
        "kql_dt_add_part": (3, dt_add_part),
        "kql_dtdiff": (3, dtdiff),
        "kql_dt_part": (2, dt_part),
        "kql_fmt_dt": (2, fmt_dt),
        "kql_fmt_ts": (2, fmt_ts),
        "kql_ts_fmt": (1, _ts_fmt),
        "kql_totimespan": (1, _ts_coz),
    }
    for ad, (n, fn) in fonksiyonlar.items():
        db.create_function(ad, n, fn, deterministic=True)
    db.create_aggregate("kql_pct", 2, _Pct)
    db.create_aggregate("kql_stdev", 1, _Stdev)
    db.create_aggregate("kql_variance", 1, _Varyans)
    db.create_window_function("kql_rn", 2, _Rn)
    db.create_window_function("kql_cumsum", 2, _Cumsum)
    db.create_window_function("kql_rws", 4, _Rws)
