# -*- coding: utf-8 -*-
"""Pafta · SPL → SQLite çevirici.

Splunk Search Processing Language'in öğretilen alt kümesini SQLite SQL'e çevirir.
Her | komutu bir CTE olur ve satır sırası her aşamada gizli __sira sütunuyla
taşınır. Splunk'a sadık kalınan incelikler:

  - aramada (search) alan=değer büyük-küçük harfe duyarsızdır, * joker karakterdir;
    where/eval içinde karşılaştırmalar duyarlıdır
  - OR / AND / NOT yalnızca BÜYÜK harfle işleçtir; küçük harfle arama terimidir
  - alan!=değer alanı olmayan satırları almaz, NOT alan=değer alır
  - stats sonucu by alanlarına göre sıralanır; top/rare count ve percent üretir
  - join varsayılan olarak alt aramadan anahtar başına yalnızca ilk satırı alır (max=1)
  - tail son N satırı ters sırayla verir
  - çok değerli alanlar (values, list, split, makemv) değerleri MV karakteriyle ayrılmış tek
    metin olarak taşınır; aramada alan=değer herhangi bir değer eşleşince doğrudur
  - _time epoch saniyesidir, sonuçta okunur tarih olarak gösterilir
  - chart'ta olmayan birleşimler boş kalır; timechart boş dilimleri count için 0 yapar
  - transaction diğer alanları alfabetik sıralı tekil değerler olarak birleştirir, startswith/
    endswith verildiğinde yarım kalan işlemleri atar ve sonuçları en yeni işlemden eskiye verir
  - bilgi nesneleri veritabanındaki tablolardan okunur (tracks/spl/veri.sql): `makro` ve
    `makro(a, b)` çağrıları ayrıştırmadan önce düz metin olarak açılır (makrolar); aramada
    eventtype=ad (olay_turleri) ve tag=etiket, tag::alan=etiket (etiketler) süzer; her
    sourcetype=X aramasında önce alan takma adları (alan_takma_adlari), sonra hesaplanan
    alanlar (hesaplanan_alanlar) kendiliğinden uygulanır, Splunk'ın arama zamanı sırasıyla

    cevir(kaynak, sutun_bul) → SQL metni
    sutun_bul(sql) → sütun adları; sutun_bul.satirlar(sql) → satırlar (chart, timechart,
    transaction, xyseries çeviri sırasında veriye bakar)
"""
import json
import math
import re
from datetime import datetime, timezone
from itertools import groupby

SIMDI = "2026-10-19 12:00"
MV = "\x1f"                      # çok değerli alanın değer ayıracı
URETEN = ("inputlookup", "makeresults")     # | ile aramanın başında çalışan komutlar
KOMUTLAR = ("search", "where", "eval", "stats", "table", "fields", "rename", "sort", "head", "tail",
            "dedup", "top", "rare", "bin", "bucket", "rex", "join", "fillnull", "chart", "timechart",
            "eventstats", "streamstats", "transaction", "lookup", "append", "appendpipe", "makemv",
            "mvexpand", "xyseries", "untable") + URETEN
_SURE = {"s": 1, "m": 60, "h": 3600, "d": 86400}


class SplHatasi(Exception):
    def __init__(self, msg, konum=None):
        super().__init__(msg)
        self.msg = msg
        self.konum = konum


Hata = SplHatasi


def q(ad):
    return "[" + ad.replace("]", "]]") + "]"


def sql_metin(s):
    return "'" + str(s).replace("'", "''") + "'"


def _metin_coz(t):
    # Yalnızca \" ve \\ kaçış dizisidir; \d gibi diziler regex fonksiyonları (match, replace) için olduğu gibi kalır
    return re.sub(r'\\(["\\])', lambda m: m.group(1), t[1:-1])


# — jetonlayıcılar —
_ARAMA = re.compile(r'\s*(?:(?P<metin>"(?:\\.|[^"\\])*")|(?P<isl>!=|<=|>=|==|=|<|>|\(|\))|(?P<kelime>[^\s=!<>()"]+))')
_IFADE = re.compile(r"""\s*(?:(?P<metin>"(?:\\.|[^"\\])*")|(?P<alan>'[^'\n]+')|(?P<sayi>\d+(?:\.\d+)?(?!\w))
                    |(?P<isl>==|!=|<=|>=|=|<|>|\(|\)|,|\+|-|\*|/|%|\.)|(?P<kelime>[^\W\d]\w*))""", re.X)
_ALANLAR = re.compile(r'\s*(?:(?P<metin>"(?:\\.|[^"\\])*")|(?P<isl>,|=)|(?P<kelime>[^\s,="]+))')
_STATS = re.compile(r'\s*(?:(?P<metin>"(?:\\.|[^"\\])*")|(?P<isl>[(),=])|(?P<kelime>[^\s(),="]+))')


def _kapanis(metin, i):
    """metin[i] == '[' → eşleşen ']' konumu (tırnak ve iç içe köşeli parantez hesaba katılır), yoksa -1."""
    derinlik, tirnak, n = 0, False, i
    while n < len(metin):
        c = metin[n]
        if tirnak:
            if c == "\\":
                n += 2
                continue
            if c == '"':
                tirnak = False
        elif c == '"':
            tirnak = True
        elif c == "[":
            derinlik += 1
        elif c == "]":
            derinlik -= 1
            if derinlik == 0:
                return n
        n += 1
    return -1


def _parantez_sonu(metin, i):
    """metin[i] == '(' → eşleşen ')' konumu (tırnak içleri hesaba katılır), yoksa -1."""
    derinlik, tirnak, n = 0, False, i
    while n < len(metin):
        c = metin[n]
        if tirnak:
            if c == "\\":
                n += 2
                continue
            if c == '"':
                tirnak = False
        elif c == '"':
            tirnak = True
        elif c == "(":
            derinlik += 1
        elif c == ")":
            derinlik -= 1
            if derinlik == 0:
                return n
        n += 1
    return -1


def _jetonla(desen, metin, bas, alt=False):
    """alt=True: arama ifadesindeki [ ... ] alt aramaları tek bir ("alt", içerik, konum) jetonu olur."""
    out, i = [], 0
    while i < len(metin):
        if metin[i:].strip() == "":
            break
        if alt:
            j = i
            while metin[j].isspace():
                j += 1
            if metin[j] == "[":
                k = _kapanis(metin, j)
                if k < 0:
                    raise SplHatasi("alt aramanın köşeli parantezi kapanmadı: ']' eksik", bas + j)
                out.append(("alt", metin[j + 1:k], bas + j + 1))
                i = k + 1
                continue
        m = desen.match(metin, i)
        if not m or m.end() == i:
            raise SplHatasi(f"tanınmayan karakter: {metin[i:].lstrip()[:1]!r}", bas + i)
        tur = next(t for t, v in m.groupdict().items() if v is not None)
        out.append((tur, m.group(tur), bas + m.start(tur)))
        i = m.end()
    return out


class _Akis:
    def __init__(self, jetonlar, son):
        self.j = jetonlar
        self.i = 0
        self.son = son

    def bak(self, k=0):
        n = self.i + k
        return self.j[n] if n < len(self.j) else ("son", "", self.son)

    def bitti(self):
        return self.i >= len(self.j)

    def al(self):
        t = self.bak()
        self.i += 1
        return t

    def isl_mi(self, v, k=0):
        t = self.bak(k)
        return t[0] == "isl" and t[1] == v

    def kelime_mi(self, v, k=0, harf=False):
        t = self.bak(k)
        return t[0] == "kelime" and (t[1].lower() == v.lower() if not harf else t[1] == v)

    def bekle(self, v):
        t = self.bak()
        if t[1] != v:
            raise SplHatasi(f"'{v}' bekleniyordu, '{t[1] or 'komutun sonu'}' geldi", t[2])
        self.i += 1

    def ad(self):
        t = self.bak()
        if t[0] == "metin":
            self.i += 1
            return _metin_coz(t[1])
        if t[0] != "kelime":
            raise SplHatasi(f"bir alan adı bekleniyordu, '{t[1] or 'komutun sonu'}' geldi", t[2])
        self.i += 1
        return t[1]


def _parcala(kaynak, bas, son):
    """| ile ayır (tırnak ve [ ] içi hariç) → [(metin, mutlak konum)]."""
    parcalar, derinlik, tirnak, i, bas_i = [], 0, False, bas, bas
    while i < son:
        c = kaynak[i]
        if tirnak:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                tirnak = False
        elif c == '"':
            tirnak = True
        elif c == "[":
            derinlik += 1
        elif c == "]":
            derinlik -= 1
        elif c == "|" and derinlik == 0:
            parcalar.append((kaynak[bas_i:i], bas_i))
            bas_i = i + 1
        i += 1
    parcalar.append((kaynak[bas_i:son], bas_i))
    return parcalar


def _joker_rx(desen):
    return re.compile(".*".join(map(re.escape, desen.split("*"))), re.I)


def _arg_bol(metin):
    """Makro argümanlarını en dış düzeydeki virgüllerden ayır (tırnak ve parantez içi hariç)."""
    out, derinlik, tirnak, bas, i = [], 0, False, 0, 0
    while i < len(metin):
        c = metin[i]
        if tirnak:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                tirnak = False
        elif c == '"':
            tirnak = True
        elif c in "([":
            derinlik += 1
        elif c in ")]":
            derinlik -= 1
        elif c == "," and derinlik == 0:
            out.append(metin[bas:i].strip())
            bas = i + 1
        i += 1
    out.append(metin[bas:].strip())
    return out


_MAKRO_CAGRI = re.compile(r"\s*([A-Za-z_][\w.-]*)\s*(?:\((.*)\))?\s*$", re.S)


def _makro_ac(kaynak, sutun_bul):
    """`ad` ve `ad(a, b)` çağrılarını makrolar tablosundaki tanımlarla değiştir. Splunk bunu aramayı
    ayrıştırmadan önce düz metin olarak yapar. → (açılmış metin, konum eşleyici ya da None)"""
    if "`" not in kaynak:
        return kaynak, None
    try:
        satirlar = sutun_bul.satirlar("SELECT ad, argumanlar, tanim FROM makrolar ORDER BY rowid")
    except Exception:
        satirlar = []
    tanimlar = {}
    for ad, argumanlar, tanim in satirlar:
        adlar = [x.strip() for x in (argumanlar or "").split(",") if x.strip()]
        tanimlar[(ad, len(adlar))] = (adlar, tanim)

    def cagri(icerik, konum, yigin):
        m = _MAKRO_CAGRI.match(icerik)
        if not m:
            raise SplHatasi(f"makro çağrısı `ad` ya da `ad(argüman, ...)` biçiminde olmalı: `{icerik}`", konum)
        ad, arg_metni = m.group(1), m.group(2)
        args = _arg_bol(arg_metni) if arg_metni and arg_metni.strip() else []
        anahtar = (ad, len(args))
        if anahtar not in tanimlar:
            var = ", ".join(sorted(f"{a}({n})" if n else a for a, n in tanimlar)) or "yok"
            raise SplHatasi(f"böyle bir makro yok: {ad}({len(args)}) · tanımlı makrolar: {var}", konum)
        if anahtar in yigin:
            raise SplHatasi(f"makro kendini çağırıyor: {' → '.join(a for a, _ in yigin + [anahtar])}", konum)
        adlar, tanim = tanimlar[anahtar]
        for a, v in zip(adlar, args):
            tanim = tanim.replace(f"${a}$", v)
        return ac(tanim, yigin + [anahtar], konum)[0]

    def ac(metin, yigin, konum=None):
        """konum None: en dış düzey, konumlar kaynağa göredir; iç düzeyde bütün hatalar o konuma düşer."""
        out, uzunluk, araliklar, i, tirnak = [], 0, [], 0, False
        while i < len(metin):
            c = metin[i]
            if c == "`" and not tirnak:
                j = metin.find("`", i + 1)
                k = i if konum is None else konum
                if j < 0:
                    raise SplHatasi("makronun ters tırnağı kapanmadı: ` eksik", k)
                acik = cagri(metin[i + 1:j], k, yigin)
                araliklar.append((uzunluk, uzunluk + len(acik), i, j + 1))
                out.append(acik)
                uzunluk += len(acik)
                i = j + 1
                continue
            if tirnak and c == "\\":
                parca = metin[i:i + 2]
            else:
                parca = c
                if c == '"':
                    tirnak = not tirnak
            out.append(parca)
            uzunluk += len(parca)
            i += len(parca)
        return "".join(out), araliklar

    acik, araliklar = ac(kaynak, [])

    def esle(k):
        if k is None:
            return None
        kayma = 0
        for a_bas, a_son, o_bas, o_son in araliklar:
            if k < a_bas:
                break
            if k < a_son:
                return o_bas
            kayma = a_son - o_son
        return k - kayma
    return acik, esle


class _Cevirici:
    def __init__(self, kaynak, sutun_bul):
        self.kaynak = kaynak
        self.sutun_bul = sutun_bul
        self.ctes = []
        self.tablo = None              # aramanın sourcetype'ı (olay türü ve etiket tanımları buna bakar)
        self._acik_turler = set()

    def yeni(self, sql):
        ad = f"a{len(self.ctes) + 1}"
        self.ctes.append((ad, sql))
        self.sutun_bul(self.with_sql(f"SELECT * FROM {ad} LIMIT 0"))    # aşama hemen denetlensin
        return ad

    def with_sql(self, son):
        if not self.ctes:
            return son
        return "WITH " + ",\n     ".join(f"{a} AS ({s})" for a, s in self.ctes) + "\n" + son

    def sutunlar(self, ad):
        return [c for c in self.sutun_bul(self.with_sql(f"SELECT * FROM {ad} LIMIT 0")) if c != "__sira"]

    def secim(self, cols, on_ek=""):
        return ", ".join(on_ek + q(c) for c in cols)

    # — boru hattı —
    def hat(self, bas, son, baslangic=None):
        """baslangic verilirse (appendpipe) bütün parçalar komuttur ve o sonuçtan başlar."""
        dis_tablo = self.tablo                 # alt arama bitince dış aramanın sourcetype'ı geri gelsin
        try:
            return self._hat(bas, son, baslangic)
        finally:
            self.tablo = dis_tablo

    def _hat(self, bas, son, baslangic):
        parcalar = _parcala(self.kaynak, bas, son)
        if baslangic is not None:
            ad = baslangic
            kalan = parcalar[1:] if not parcalar[0][0].strip() and len(parcalar) > 1 else parcalar
        elif not parcalar[0][0].strip() and len(parcalar) > 1:
            metin, konum = parcalar[1]
            govde = metin.strip()
            if not govde:
                raise SplHatasi("| işaretinden sonra bir komut bekleniyordu", konum)
            komut = govde.split(None, 1)[0]
            if komut.lower() not in URETEN:
                raise SplHatasi(f"| ile başlayan arama veri üreten bir komutla başlamalı: {', '.join(URETEN)}",
                                konum + metin.index(komut))
            arg_bas = konum + metin.index(komut) + len(komut)
            ad = getattr(self, "u_" + komut.lower())(self.kaynak[arg_bas:konum + len(metin)], arg_bas)
            kalan = parcalar[2:]
        else:
            ilk, ilk_konum = parcalar[0]
            komut0 = ilk.strip().split(None, 1)[0].lower() if ilk.strip() else ""
            if komut0 == "search":
                ilk_konum += ilk.index(ilk.strip().split(None, 1)[0]) + len("search")
                ilk = self.kaynak[ilk_konum:ilk_konum + len(ilk) - (ilk_konum - parcalar[0][1])]
            ad = self.temel_arama(ilk, ilk_konum)
            kalan = parcalar[1:]
        for metin, konum in kalan:
            govde = metin.strip()
            if not govde:
                raise SplHatasi("| işaretinden sonra bir komut bekleniyordu", konum)
            komut = govde.split(None, 1)[0]
            k = komut.lower()
            if k not in KOMUTLAR:
                raise SplHatasi(f"bu komut desteklenmiyor: {komut} (desteklenenler: {', '.join(KOMUTLAR)})",
                                konum + metin.index(komut))
            if k in URETEN:
                raise SplHatasi(f"{komut} veri üreten bir komuttur; aramanın başında yazılır: | {k} ...",
                                konum + metin.index(komut))
            arg_bas = konum + metin.index(komut) + len(komut)
            arg = self.kaynak[arg_bas:konum + len(metin)]
            ad = getattr(self, "k_" + {"bucket": "bin"}.get(k, k))(ad, arg, arg_bas)
        return ad

    # — arama —
    def temel_arama(self, metin, bas):
        jet = _jetonla(_ARAMA, metin, bas, alt=True)
        tablo, kalan, n, st_konum = None, [], 0, bas
        while n < len(jet):
            t = jet[n]
            if t[0] == "kelime" and t[1].lower() in ("sourcetype", "index") and n + 2 < len(jet) and jet[n + 1][1] == "=":
                deger = jet[n + 2]
                d = _metin_coz(deger[1]) if deger[0] == "metin" else deger[1]
                if t[1].lower() == "sourcetype":
                    tablo, st_konum = d, t[2]
                elif d not in ("ops", "*"):
                    raise SplHatasi(f"böyle bir index yok: {d} (bu tezgahta index=ops)", deger[2])
                n += 3
                continue
            kalan.append(t)
            n += 1
        if not tablo:
            adaylar = self._kaynak_tahmini(kalan)
            if len(adaylar) > 1:
                raise SplHatasi(f"bu olay türleri ve etiketler birden çok sourcetype'a uyuyor ({', '.join(sorted(adaylar))}); "
                                "tezgahta bir arama tek sourcetype okur, başa sourcetype=... ekle", bas)
            tablo = next(iter(adaylar), None)
        if not tablo:
            raise SplHatasi("arama sourcetype=<tablo> ile başlamalı (ör. sourcetype=biletler durum=açık)", bas)
        self.tablo = tablo
        kaynak = self.yeni(f"SELECT *, rowid AS [__sira] FROM {q(tablo)}")
        kaynak = self._arama_zamani_alanlari(kaynak, tablo, st_konum)
        if not kalan:
            return kaynak
        return self._arama_uygula(kaynak, kalan, bas + len(metin))

    # — bilgi nesneleri —
    def _tanim(self, sql):
        """Bilgi nesnesi tablosunu oku; tablo yoksa boş."""
        try:
            return self.sutun_bul.satirlar(sql)
        except Exception:
            return []

    def _arama_zamani_alanlari(self, kaynak, tablo, konum):
        """props.conf'taki FIELDALIAS ve EVAL tanımları: Splunk bunları her aramada kendiliğinden,
        önce takma adlar sonra hesaplanan alanlar sırasıyla uygular. Hesaplanan alanlar **aynı anda**
        değerlendirilir: hepsi takma adlardan sonraki olayı görür, biri ötekinin sonucunu göremez
        (başka bir hesaplanan alana dayanan ifade o alanı boş görür)."""
        st = sql_metin(tablo)
        for alan, takma in self._tanim(f"SELECT alan, takma_ad FROM alan_takma_adlari WHERE sourcetype = {st} ORDER BY rowid"):
            cols = self.sutunlar(kaynak)
            if alan in cols:                   # kaynak alanı olmayan olayda takma ad da oluşmaz
                secim = self._ust_yaz(cols, [takma], lambda c: q(alan))
                kaynak = self.yeni(f"SELECT {', '.join(secim)}, [__sira] FROM {kaynak}")
        hesaplar = self._tanim(f"SELECT alan, ifade FROM hesaplanan_alanlar WHERE sourcetype = {st} ORDER BY rowid")
        if not hesaplar:
            return kaynak
        cols = self.sutunlar(kaynak)
        yeniler = [a for a in dict.fromkeys(alan for alan, _ in hesaplar) if a not in cols]
        if yeniler:                            # henüz hesaplanmamış alanlar: öteki ifadeler bunları boş görür
            kaynak = self.yeni(f"SELECT *, {', '.join(f'NULL AS {q(a)}' for a in yeniler)} FROM {kaynak}")
        ifadeler = {}
        for alan, ifade in hesaplar:
            try:
                a = _Akis(_jetonla(_IFADE, ifade, konum), konum)
                sql = self._i_veya(a)
                if not a.bitti():
                    raise SplHatasi(f"beklenmeyen: '{a.bak()[1]}'", konum)
                self.sutun_bul(self.with_sql(f"SELECT {sql} FROM {kaynak} LIMIT 0"))
            except Exception as e:
                raise SplHatasi(f"hesaplanan alan {alan} = {ifade}: {getattr(e, 'msg', e)}", konum)
            ifadeler[alan] = sql
        secim = ", ".join(f"{ifadeler[c]} AS {q(c)}" if c in ifadeler else q(c) for c in self.sutunlar(kaynak))
        return self.yeni(f"SELECT {secim}, [__sira] FROM {kaynak}")

    def _olay_turleri(self, desen):
        rx = _joker_rx(desen)
        return [(ad, arama) for ad, arama in self._tanim("SELECT ad, arama FROM olay_turleri ORDER BY rowid")
                if rx.fullmatch(ad)]

    def _etiketler(self, desen, alan_kisiti):
        rx = _joker_rx(desen)
        return [(alan, deger) for alan, deger, etiket in self._tanim("SELECT alan, deger, etiket FROM etiketler ORDER BY rowid")
                if rx.fullmatch(etiket) and (not alan_kisiti or alan == alan_kisiti)]

    def _tur_kaynaklari(self, desen):
        return {m.group(1) for _, arama in self._olay_turleri(desen)
                for m in re.finditer(r'(?i)\bsourcetype\s*=\s*"?([^\s"()]+)', arama)}

    def _kaynak_tahmini(self, jet):
        """sourcetype yazılmamış aramada olay türü ve etiket tanımlarının işaret ettiği sourcetype'lar."""
        adaylar = set()
        for t, isl, v in zip(jet, jet[1:], jet[2:]):
            if t[0] != "kelime" or isl[1] != "=" or v[0] not in ("kelime", "metin"):
                continue
            d = _metin_coz(v[1]) if v[0] == "metin" else v[1]
            alan = t[1].lower()
            if alan == "eventtype":
                adaylar |= self._tur_kaynaklari(d)
            elif alan == "tag" or alan.startswith("tag::"):
                for a_, deger in self._etiketler(d, t[1][5:] if alan.startswith("tag::") else None):
                    if a_ == "sourcetype":
                        adaylar.add(deger)
                    elif a_ == "eventtype":
                        adaylar |= self._tur_kaynaklari(deger)
        return adaylar

    def _kaynak_kosulu(self, deger):
        return "1" if self.tablo and deger.lower() == self.tablo.lower() else "0"

    def _olay_turu_kosulu(self, desen, cols, konum):
        """eventtype=ad: olay türünün kayıtlı aramasını bu aramanın alanları üzerinde bir koşula çevir."""
        parcalar = []
        for ad, arama in self._olay_turleri(desen):
            if ad in self._acik_turler:
                raise SplHatasi(f"olay türü kendine başvuruyor: {ad}", konum)
            self._acik_turler.add(ad)
            try:
                jet, n = [], 0
                ham = _jetonla(_ARAMA, arama, konum, alt=True)
                while n < len(ham):
                    t = ham[n]
                    if t[0] == "kelime" and t[1].lower() in ("sourcetype", "index") and n + 2 < len(ham) and ham[n + 1][1] == "=":
                        d = _metin_coz(ham[n + 2][1]) if ham[n + 2][0] == "metin" else ham[n + 2][1]
                        jet.append(("sabit", self._kaynak_kosulu(d) if t[1].lower() == "sourcetype"
                                    else ("1" if d in ("ops", "*") else "0"), t[2]))
                        n += 3
                        continue
                    jet.append(t)
                    n += 1
                a = _Akis(jet, konum)
                kosul = self._a_ve(a, cols)
                if not a.bitti():
                    raise SplHatasi(f"beklenmeyen: '{a.bak()[1]}'", konum)
                parcalar.append(kosul)
            except SplHatasi as e:
                if e.msg.startswith("olay türü "):
                    raise
                raise SplHatasi(f"olay türü {ad} ({arama}): {e.msg}", konum)
            finally:
                self._acik_turler.discard(ad)
        return "(" + " OR ".join(parcalar) + ")" if parcalar else "0"

    def _etiket_kosulu(self, desen, alan_kisiti, cols, konum):
        """tag=etiket: etiketin bağlı olduğu alan=değer çiftlerinden herhangi biri tutuyorsa."""
        parcalar = []
        for alan, deger in self._etiketler(desen, alan_kisiti):
            if alan == "eventtype":
                parcalar.append(self._olay_turu_kosulu(deger, cols, konum))
            elif alan == "sourcetype":
                parcalar.append(self._kaynak_kosulu(deger))
            elif alan in cols:
                parcalar.append(f"spl_esit({q(alan)}, {sql_metin(deger)})")
        return "(" + " OR ".join(parcalar) + ")" if parcalar else "0"

    def k_search(self, onceki, arg, bas):
        jet = _jetonla(_ARAMA, arg, bas, alt=True)
        if not jet:
            raise SplHatasi("search'ten sonra bir arama ifadesi bekleniyordu", bas)
        return self._arama_uygula(onceki, jet, bas + len(arg))

    def _arama_kosulu(self, onceki, jet, son):
        """Arama jetonlarını onceki üzerinde bir SQL koşuluna çevir (alt aramalar onceki'ye bağlanır)."""
        a = _Akis(jet, son)
        cols = self.sutunlar(onceki)
        dis, self._dis = getattr(self, "_dis", None), onceki
        try:
            kosul = self._a_ve(a, cols)
        finally:
            self._dis = dis
        if not a.bitti():
            t = a.bak()
            raise SplHatasi(f"beklenmeyen: '{t[1]}'", t[2])
        return kosul

    def _arama_uygula(self, onceki, jet, son):
        return self.yeni(f"SELECT * FROM {onceki} WHERE {self._arama_kosulu(onceki, jet, son)}")

    def _alt_arama(self, metin, bas):
        """[ ... ] içeriğini kendi boru hattı olarak çevir → CTE adı."""
        ilk = metin.strip().split(None, 1)
        alt_bas = bas
        if ilk and ilk[0].lower() == "search":
            alt_bas = bas + metin.index(ilk[0]) + len("search")
        if not metin.strip():
            raise SplHatasi("alt arama boş", bas)
        return self.hat(alt_bas, bas + len(metin))

    def _alt_kosul(self, t, cols):
        """Splunk alt aramanın sonucunu ( (a="x" AND b="y") OR (...) ) aramasına çevirir."""
        alt = self._alt_arama(t[1], t[2])
        acols = self.sutunlar(alt)
        if not acols or any(c not in cols for c in acols):
            return "0"                              # alt aramanın alanı olayda yoksa hiçbir olay eşleşmez
        dis = self._dis
        kosul = " AND ".join(f"(s.{q(c)} IS NULL OR spl_alt_esit({dis}.{q(c)}, s.{q(c)}))" for c in acols)
        return f"EXISTS (SELECT 1 FROM {alt} AS s WHERE {kosul})"

    # Splunk'ın search komutunda öncelik: parantez, NOT, OR, AND (SQL'in tersine OR, AND'den sıkı bağlanır)
    def _a_ve(self, a, cols):
        s = self._a_veya(a, cols)
        while not a.bitti() and not a.isl_mi(")"):
            if a.kelime_mi("AND", harf=True):
                a.i += 1
            s = f"({s} AND {self._a_veya(a, cols)})"
        return s

    def _a_veya(self, a, cols):
        s = self._a_degil(a, cols)
        while a.kelime_mi("OR", harf=True):
            a.i += 1
            s = f"({s} OR {self._a_degil(a, cols)})"
        return s

    def _a_degil(self, a, cols):
        if a.kelime_mi("NOT", harf=True):
            a.i += 1
            return f"(NOT {self._a_degil(a, cols)})"
        if a.isl_mi("("):
            a.i += 1
            s = self._a_ve(a, cols)
            a.bekle(")")
            return f"({s})"
        return self._a_terim(a, cols)

    def _a_terim(self, a, cols):
        t = a.al()
        if t[0] == "sabit":                    # olay türü tanımındaki sourcetype=... (önceden çözüldü)
            return t[1]
        if t[0] == "alt":
            return self._alt_kosul(t, cols)
        if t[0] == "isl":
            raise SplHatasi(f"beklenmeyen: '{t[1]}'", t[2])
        if t[0] == "kelime" and a.bak()[0] == "isl" and a.bak()[1] in ("=", "!=", "<", ">", "<=", ">=", "=="):
            alan, op = t[1], a.al()[1]
            v = a.al()
            if v[0] not in ("kelime", "metin"):
                raise SplHatasi(f"'{alan}{op}' sonrasında bir değer bekleniyordu", v[2])
            deger = _metin_coz(v[1]) if v[0] == "metin" else v[1]
            if alan.lower() in ("eventtype", "tag") or alan.lower().startswith("tag::"):
                if op not in ("=", "==", "!="):
                    raise SplHatasi(f"{alan} yalnızca = ve != ile aranır", t[2])
                if alan.lower() == "eventtype":
                    kosul = self._olay_turu_kosulu(deger, cols, t[2])
                else:
                    kosul = self._etiket_kosulu(deger, alan[5:] if alan.lower().startswith("tag::") else None, cols, t[2])
                return f"(NOT {kosul})" if op == "!=" else kosul
            if alan not in cols:
                return "0" if op != "!=" else "0"              # alanı olmayan olay eşleşmez
            if op in ("<", ">", "<=", ">="):
                try:
                    float(deger)
                except ValueError:
                    raise SplHatasi(f"{op} ile karşılaştırma için bir sayı bekleniyordu", v[2])
                return f"({q(alan)} {op} {deger})"
            esit = f"spl_wild({q(alan)}, {sql_metin(deger)})" if "*" in deger else f"spl_esit({q(alan)}, {sql_metin(deger)})"
            return f"({q(alan)} IS NOT NULL AND NOT {esit})" if op == "!=" else esit
        # serbest metin: herhangi bir alanda geçiyorsa
        terim = _metin_coz(t[1]) if t[0] == "metin" else t[1].replace("*", "")
        if not terim:
            return "1"
        return "(" + " OR ".join(f"spl_icerir({q(c)}, {sql_metin(terim)})" for c in cols) + ")"

    # — ifadeler (where, eval) —
    def ifade_cevir(self, arg, bas):
        a = _Akis(_jetonla(_IFADE, arg, bas), bas + len(arg))
        return a, self._i_veya(a)

    def _i_veya(self, a):
        s = self._i_ve(a)
        while a.kelime_mi("OR"):
            a.i += 1
            s = f"({s} OR {self._i_ve(a)})"
        return s

    def _i_ve(self, a):
        s = self._i_degil(a)
        while a.kelime_mi("AND"):
            a.i += 1
            s = f"({s} AND {self._i_degil(a)})"
        return s

    def _i_degil(self, a):
        if a.kelime_mi("NOT"):
            a.i += 1
            return f"(NOT {self._i_degil(a)})"
        return self._i_karsilastir(a)

    def _i_karsilastir(self, a):
        s = self._i_topla(a)
        t = a.bak()
        if t[0] == "isl" and t[1] in ("=", "==", "!=", "<", ">", "<=", ">="):
            a.i += 1
            r = self._i_topla(a)
            op = {"=": "=", "==": "=", "!=": "<>"}.get(t[1], t[1])
            return f"({s} {op} {r})"
        return s

    def _i_topla(self, a):
        s = self._i_carp(a)
        while a.isl_mi("+") or a.isl_mi("-") or a.isl_mi("."):
            op = a.al()[1]
            r = self._i_carp(a)
            s = f"({s} || {r})" if op == "." else f"({s} {op} {r})"
        return s

    def _i_carp(self, a):
        s = self._i_tekli(a)
        while a.isl_mi("*") or a.isl_mi("/") or a.isl_mi("%"):
            op = a.al()[1]
            r = self._i_tekli(a)
            # Splunk'ta bölme her zaman ondalıklıdır: 300/11 = 27.27…, SQLite gibi 27 değil
            s = f"(CAST({s} AS REAL) / {r})" if op == "/" else f"({s} {op} {r})"
        return s

    def _i_tekli(self, a):
        if a.isl_mi("-"):
            a.i += 1
            return f"(-{self._i_tekli(a)})"
        return self._i_birincil(a)

    def _i_birincil(self, a):
        t = a.bak()
        if t[0] == "sayi":
            a.i += 1
            return t[1]
        if t[0] == "metin":
            a.i += 1
            return sql_metin(_metin_coz(t[1]))
        if t[0] == "alan":
            a.i += 1
            return q(t[1][1:-1])
        if a.isl_mi("("):
            a.i += 1
            s = self._i_veya(a)
            a.bekle(")")
            return f"({s})"
        if t[0] == "kelime":
            if a.isl_mi("(", 1):
                return self._i_fonksiyon(a)
            a.i += 1
            return q(t[1])
        raise SplHatasi(f"beklenmeyen: '{t[1] or 'ifadenin sonu'}'", t[2])

    def _i_fonksiyon(self, a):
        ad_t = a.al()
        ad, konum = ad_t[1], ad_t[2]
        a.bekle("(")
        args = []
        if not a.isl_mi(")"):
            args.append(self._i_veya(a))
            while a.isl_mi(","):
                a.i += 1
                args.append(self._i_veya(a))
        a.bekle(")")

        def say(*n):
            if len(args) not in n:
                raise SplHatasi(f"{ad}() fonksiyonuna yanlış sayıda argüman verildi", konum)

        f = ad.lower()
        sabit = {"true": "1", "false": "0", "null": "NULL", "now": str(_epoch(SIMDI))}
        if f in sabit:
            say(0)
            return sabit[f]
        tek = {"isnull": "({0} IS NULL)", "isnotnull": "({0} IS NOT NULL)", "len": "length({0})",
               "lower": "spl_kucuk({0})", "upper": "spl_buyuk({0})", "abs": "abs({0})",
               "tonumber": "CAST({0} AS NUMERIC)", "tostring": "CAST({0} AS TEXT)"}
        if f in tek:
            say(1)
            return tek[f].format(args[0])
        if f == "if":
            say(3)
            return f"(CASE WHEN {args[0]} THEN {args[1]} ELSE {args[2]} END)"
        if f == "case":
            if len(args) < 2 or len(args) % 2:
                raise SplHatasi("case(koşul1, değer1, koşul2, değer2, ...) biçiminde çift sayıda argüman bekleniyordu", konum)
            return "(CASE " + " ".join(f"WHEN {args[n]} THEN {args[n + 1]}" for n in range(0, len(args), 2)) + " END)"
        if f == "coalesce":
            return f"coalesce({', '.join(args)}{', NULL' if len(args) == 1 else ''})"
        if f == "round":
            say(1, 2)
            return f"round({', '.join(args)})"
        if f == "substr":
            say(2, 3)
            return f"substr({', '.join(args)})"
        if f == "like":
            say(2)
            return f"spl_like({args[0]}, {args[1]})"
        if f == "match":
            say(2)
            return f"spl_regex({args[0]}, {args[1]})"
        if f == "replace":
            say(3)
            return f"spl_replace({args[0]}, {args[1]}, {args[2]})"
        if f == "strptime":
            say(2)
            return f"spl_strptime({args[0]}, {args[1]})"
        if f == "strftime":
            say(2)
            return f"spl_strftime({args[0]}, {args[1]})"
        if f in ("min", "max"):
            if len(args) < 2:
                raise SplHatasi(f"eval içinde {f}() en az iki değer ister; toplama için stats kullan", konum)
            return f"{f}({', '.join(args)})"
        tek2 = {"mvcount": "spl_mvcount({0})", "mvdedup": "spl_mvdedup({0})", "mvsort": "spl_mvsort({0})",
                "typeof": "spl_typeof({0})", "isnum": "(spl_typeof({0}) = 'Number')",
                "isstr": "(spl_typeof({0}) = 'String')", "floor": "spl_floor({0})", "ceiling": "spl_ceil({0})",
                "ceil": "spl_ceil({0})", "sqrt": "spl_sqrt({0})"}
        if f in tek2:
            say(1)
            return tek2[f].format(args[0])
        if f == "split":
            say(2)
            return f"spl_split({args[0]}, {args[1]})"
        if f == "mvindex":
            say(2, 3)
            return f"spl_mvindex({args[0]}, {args[1]}, {args[2] if len(args) == 3 else 'NULL'})"
        if f == "mvjoin":
            say(2)
            return f"spl_mvjoin({args[0]}, {args[1]})"
        if f == "mvappend":
            if not args:
                raise SplHatasi("mvappend() en az bir değer ister", konum)
            return f"spl_mvappend({', '.join(args)})"
        if f in ("trim", "ltrim", "rtrim"):
            say(1, 2)
            return f"spl_{f}({args[0]}, {args[1] if len(args) == 2 else 'NULL'})"
        if f == "in":
            if len(args) < 2:
                raise SplHatasi("in(alan, değer1, değer2, ...) en az bir değer ister", konum)
            return f"({args[0]} IN ({', '.join(args[1:])}))"
        if f == "nullif":
            say(2)
            return f"nullif({args[0]}, {args[1]})"
        if f == "pow":
            say(2)
            return f"spl_pow({args[0]}, {args[1]})"
        if f == "printf":
            if not args:
                raise SplHatasi('printf("biçim", değerler...) bir biçim metni ister', konum)
            return f"spl_printf({', '.join(args)})"
        raise SplHatasi(f"bu fonksiyon desteklenmiyor: {ad}()", konum)

    # — komutlar —
    def k_where(self, onceki, arg, bas):
        a, kosul = self.ifade_cevir(arg, bas)
        if not a.bitti():
            t = a.bak()
            raise SplHatasi(f"beklenmeyen: '{t[1]}'", t[2])
        return self.yeni(f"SELECT * FROM {onceki} WHERE {kosul}")

    def k_eval(self, onceki, arg, bas):
        a = _Akis(_jetonla(_IFADE, arg, bas), bas + len(arg))
        while True:
            t = a.bak()
            if t[0] not in ("kelime", "alan") or not a.isl_mi("=", 1):
                raise SplHatasi("eval alan = ifade biçiminde olmalı", t[2])
            hedef = t[1] if t[0] == "kelime" else t[1][1:-1]
            a.i += 2
            sql = self._i_veya(a)
            cols = self.sutunlar(onceki)
            if hedef in cols:
                secim = ", ".join(f"{sql} AS {q(c)}" if c == hedef else q(c) for c in cols)
            else:
                secim = self.secim(cols) + f", {sql} AS {q(hedef)}"
            onceki = self.yeni(f"SELECT {secim}, [__sira] FROM {onceki}")
            if a.isl_mi(","):
                a.i += 1
                continue
            if not a.bitti():
                t = a.bak()
                raise SplHatasi(f"beklenmeyen: '{t[1]}' (birden çok atamayı virgülle ayır)", t[2])
            return onceki

    def _alan_listesi(self, arg, bas):
        a = _Akis(_jetonla(_ALANLAR, arg, bas), bas + len(arg))
        adlar = []
        while not a.bitti():
            if a.isl_mi(","):
                a.i += 1
                continue
            adlar.append((a.ad(), a.bak(-1)[2]))
        return adlar

    def k_table(self, onceki, arg, bas):
        adlar = self._alan_listesi(arg, bas)
        if not adlar:
            raise SplHatasi("table'dan sonra alan adları bekleniyordu", bas)
        cols = self.sutunlar(onceki)
        secim = ", ".join(q(ad) if ad in cols else f"NULL AS {q(ad)}" for ad, _ in adlar)
        return self.yeni(f"SELECT {secim}, [__sira] FROM {onceki}")

    def k_fields(self, onceki, arg, bas):
        govde = arg.strip()
        cols = self.sutunlar(onceki)
        if govde.startswith("-"):
            at = {ad for ad, _ in self._alan_listesi(arg[arg.index("-") + 1:], bas + arg.index("-") + 1)}
            kalan = [c for c in cols if c not in at]
        else:
            kalan = [ad for ad, _ in self._alan_listesi(arg.replace("+", " ", 1) if govde.startswith("+") else arg, bas)
                     if ad in cols]
        return self.yeni(f"SELECT {self.secim(kalan)}, [__sira] FROM {onceki}")

    def k_rename(self, onceki, arg, bas):
        a = _Akis(_jetonla(_ALANLAR, arg, bas), bas + len(arg))
        cols = self.sutunlar(onceki)
        degis = {}
        while not a.bitti():
            if a.isl_mi(","):
                a.i += 1
                continue
            t = a.bak()
            eski = a.ad()
            if not a.kelime_mi("as"):
                raise SplHatasi("rename eski AS yeni biçiminde olmalı", a.bak()[2])
            a.i += 1
            yeni_ad = a.ad()
            if eski not in cols:
                raise SplHatasi(f"böyle bir alan yok: {eski}", t[2])
            degis[eski] = yeni_ad
        secim = ", ".join(f"{q(c)} AS {q(degis.get(c, c))}" for c in cols)
        return self.yeni(f"SELECT {secim}, [__sira] FROM {onceki}")

    def k_sort(self, onceki, arg, bas):
        jet = _jetonla(_ALANLAR, arg, bas)
        limit, parcalar, yon_bekleyen = None, [], None
        for n, t in enumerate(jet):
            if t[0] == "isl":
                continue
            v = t[1]
            if n == 0 and v.isdigit():
                limit = int(v)
                continue
            if v in ("-", "+"):
                yon_bekleyen = v
                continue
            yon = yon_bekleyen or "+"
            yon_bekleyen = None
            if v[0] in "-+":
                yon, v = v[0], v[1:]
            parcalar.append(f"{q(v)} {'DESC' if yon == '-' else 'ASC'}")
        if not parcalar:
            raise SplHatasi("sort'tan sonra en az bir alan bekleniyordu (azalan için -alan)", bas)
        cols = self.sutunlar(onceki)
        sirali = self.yeni(f"SELECT {self.secim(cols)}, ROW_NUMBER() OVER (ORDER BY {', '.join(parcalar)}, [__sira]) "
                           f"AS [__sira] FROM {onceki}")
        if limit:
            return self.yeni(f"SELECT * FROM {sirali} ORDER BY [__sira] LIMIT {limit}")
        return sirali

    def _sayi_arg(self, arg, bas, varsayilan):
        govde = arg.strip()
        if not govde:
            return varsayilan
        if not govde.isdigit():
            raise SplHatasi("bir sayı bekleniyordu", bas + arg.index(govde))
        return int(govde)

    def k_head(self, onceki, arg, bas):
        return self.yeni(f"SELECT * FROM {onceki} ORDER BY [__sira] LIMIT {self._sayi_arg(arg, bas, 10)}")

    def k_tail(self, onceki, arg, bas):
        n = self._sayi_arg(arg, bas, 10)
        son = self.yeni(f"SELECT * FROM {onceki} ORDER BY [__sira] DESC LIMIT {n}")
        cols = self.sutunlar(son)
        return self.yeni(f"SELECT {self.secim(cols)}, ROW_NUMBER() OVER (ORDER BY [__sira] DESC) AS [__sira] FROM {son}")

    def k_dedup(self, onceki, arg, bas):
        adlar = [ad for ad, _ in self._alan_listesi(arg, bas)]
        if not adlar:
            raise SplHatasi("dedup'tan sonra alan adı bekleniyordu", bas)
        cols = self.sutunlar(onceki)
        anahtar = ", ".join(q(a) for a in adlar)
        return self.yeni(f"SELECT {self.secim(cols)}, [__sira] FROM (SELECT *, ROW_NUMBER() OVER (PARTITION BY {anahtar} "
                         f"ORDER BY [__sira]) AS [__ilk] FROM {onceki} WHERE " +
                         " AND ".join(f"{q(a)} IS NOT NULL" for a in adlar) + ") WHERE [__ilk] = 1")

    def _stats_coz(self, arg, bas, komut="stats", secenekli=False):
        """'count, avg(cpu) as ort by rol' → ([(ad, sql, fn)], [gruplar], {seçenek: (değer, konum)})."""
        a = _Akis(_jetonla(_STATS, arg, bas), bas + len(arg))
        toplamalar, secenek = [], {}
        while not a.bitti() and not a.kelime_mi("by"):
            if a.isl_mi(","):
                a.i += 1
                continue
            t = a.bak()
            if secenekli and t[0] == "kelime" and a.isl_mi("=", 1):
                a.i += 2
                secenek[t[1].lower()] = (a.ad(), t[2])
                continue
            toplamalar.append(self._toplama_oku(a))
        gruplar = []
        if a.kelime_mi("by"):
            a.i += 1
            while not a.bitti():
                if a.isl_mi(","):
                    a.i += 1
                    continue
                gruplar.append(a.ad())
        if not toplamalar:
            raise SplHatasi(f"{komut}'tan sonra en az bir toplama bekleniyordu (ör. {komut} count by rol)", bas)
        return toplamalar, gruplar, secenek

    def k_stats(self, onceki, arg, bas):
        toplamalar, gruplar, _ = self._stats_coz(arg, bas)
        return self._stats_sql(onceki, toplamalar, gruplar)

    def _stats_sql(self, onceki, toplamalar, gruplar):
        secim = ", ".join([q(g) for g in gruplar] + [f"{s} AS {q(n)}" for n, s, _ in toplamalar])
        if gruplar:
            sira = f"ROW_NUMBER() OVER (ORDER BY {', '.join(q(g) for g in gruplar)})"
            sql = (f"SELECT {secim}, {sira} AS [__sira] FROM {onceki} WHERE "
                   + " AND ".join(f"{q(g)} IS NOT NULL" for g in gruplar)
                   + f" GROUP BY {', '.join(q(g) for g in gruplar)}")
        else:
            sql = f"SELECT {secim}, 1 AS [__sira] FROM {onceki}"
        return self.yeni(sql)

    def _toplama_oku(self, a):
        """Akıştan bir toplama oku: count, avg(alan), count(eval(koşul)) as ad → (ad, sql, fn)."""
        t = a.bak()
        if t[0] != "kelime":
            raise SplHatasi(f"bir toplama fonksiyonu bekleniyordu (count, sum, avg...), '{t[1]}' geldi", t[2])
        fn = t[1].lower()
        a.i += 1
        alan = ifade = None
        if a.isl_mi("("):
            a.i += 1
            if a.kelime_mi("eval") and a.isl_mi("(", 1):
                ac = a.bak(1)[2]                          # eval'in açılış parantezi (mutlak konum)
                kapa = _parantez_sonu(self.kaynak, ac)
                if kapa < 0:
                    raise SplHatasi("eval( ... ) kapanmadı: ')' eksik", ac)
                ia, ifade = self.ifade_cevir(self.kaynak[ac + 1:kapa], ac + 1)
                if not ia.bitti():
                    raise SplHatasi(f"beklenmeyen: '{ia.bak()[1]}'", ia.bak()[2])
                while not a.bitti() and a.bak()[2] <= kapa:
                    a.i += 1
            else:
                alan = a.ad()
            a.bekle(")")
        if ifade is not None:
            sablon = {"count": "SUM(CASE WHEN {0} THEN 1 ELSE 0 END)", "sum": "SUM({0})", "avg": "AVG({0})",
                      "mean": "AVG({0})", "min": "MIN({0})", "max": "MAX({0})", "dc": "COUNT(DISTINCT {0})",
                      "distinct_count": "COUNT(DISTINCT {0})", "values": "spl_values({0})"}
            if fn not in sablon:
                raise SplHatasi(f"{fn}(eval(...)) desteklenmiyor (count, sum, avg, min, max, dc, values)", t[2])
            sql, ad = sablon[fn].format(f"({ifade})"), None
        else:
            sql, ad = self._toplama(fn, alan, t[2])
        if a.kelime_mi("as"):
            a.i += 1
            ad = a.ad()
        if ad is None:
            raise SplHatasi(f"{fn}(eval(...)) sonucuna bir ad verilmeli: {fn}(eval(...)) as ad", t[2])
        return ad, sql, fn

    def _toplama(self, fn, alan, konum):
        if fn == "count":
            return ("COUNT(*)", "count") if alan is None else (f"COUNT({q(alan)})", f"count({alan})")
        if alan is None:
            raise SplHatasi(f"{fn} bir alan ister: {fn}(alan)", konum)
        sablon = {"dc": "COUNT(DISTINCT {0})", "distinct_count": "COUNT(DISTINCT {0})", "sum": "SUM({0})",
                  "avg": "AVG({0})", "mean": "AVG({0})", "min": "MIN({0})", "max": "MAX({0})",
                  "range": "(MAX({0}) - MIN({0}))", "values": "spl_values({0})", "list": "spl_list({0} ORDER BY [__sira])",
                  "stdev": "spl_stdev({0})", "var": "spl_var({0})",
                  "earliest": "spl_earliest({0}, [_time])", "latest": "spl_latest({0}, [_time])"}
        if fn not in sablon:
            raise SplHatasi(f"bu toplama desteklenmiyor: {fn}() (desteklenenler: count, dc, sum, avg, min, max, "
                            "range, values, list, stdev, var, earliest, latest)", konum)
        return sablon[fn].format(q(alan)), f"{fn}({alan})"

    def _top_rare(self, onceki, arg, bas, azalan):
        a = _Akis(_jetonla(_ALANLAR, arg, bas), bas + len(arg))
        limit, alanlar, gruplar, hedef = 10, [], [], None
        while not a.bitti():
            if a.isl_mi(","):
                a.i += 1
                continue
            t = a.bak()
            if t[0] == "kelime" and t[1].lower() == "limit" and a.isl_mi("=", 1):
                a.i += 2
                limit = int(a.ad())
                continue
            if t[0] == "kelime" and t[1].isdigit() and not alanlar:
                a.i += 1
                limit = int(t[1])
                continue
            if a.kelime_mi("by"):
                a.i += 1
                hedef = gruplar
                continue
            (hedef if hedef is not None else alanlar).append(a.ad())
        if not alanlar:
            raise SplHatasi("top/rare bir alan ister: top rol", bas)
        anahtar = gruplar + alanlar
        sayim = self.yeni(f"SELECT {', '.join(q(c) for c in anahtar)}, COUNT(*) AS [count] FROM {onceki} WHERE "
                          + " AND ".join(f"{q(c)} IS NOT NULL" for c in anahtar)
                          + f" GROUP BY {', '.join(q(c) for c in anahtar)}")
        bolum = f"PARTITION BY {', '.join(q(g) for g in gruplar)} " if gruplar else ""
        yon = "DESC" if azalan else "ASC"
        sirali = self.yeni(
            f"SELECT {', '.join(q(c) for c in anahtar)}, [count], "
            f"printf('%.6f', 100.0 * [count] / SUM([count]) OVER ({bolum.strip()})) AS [percent], "
            f"ROW_NUMBER() OVER ({bolum}ORDER BY [count] {yon}, {', '.join(q(c) for c in alanlar)}) AS [__n] FROM {sayim}")
        sira = ", ".join([q(g) for g in gruplar] + ["[__n]"])
        return self.yeni(f"SELECT {', '.join(q(c) for c in anahtar)}, [count], [percent], "
                         f"ROW_NUMBER() OVER (ORDER BY {sira}) AS [__sira] FROM {sirali} WHERE [__n] <= {limit}")

    def k_top(self, onceki, arg, bas):
        return self._top_rare(onceki, arg, bas, True)

    def k_rare(self, onceki, arg, bas):
        return self._top_rare(onceki, arg, bas, False)

    def k_bin(self, onceki, arg, bas):
        m = re.fullmatch(r"\s*(\S+)\s+span\s*=\s*(\d+)([dhm]?)\s*", arg)
        if not m:
            raise SplHatasi("bin alan span=1d biçiminde olmalı (1d, 1h, 15m ya da bir sayı)", bas)
        alan, n, birim = m.group(1), int(m.group(2)), m.group(3)
        cols = self.sutunlar(onceki)
        if alan not in cols:
            raise SplHatasi(f"böyle bir alan yok: {alan}", bas + arg.index(alan))
        x = q(alan)
        if alan == "_time":                         # epoch saniyesi: dilimin başına yuvarla
            s = n * _SURE.get(birim or "s", 1)
            secim = ", ".join(f"(CAST({x} / {s} AS INTEGER) * {s}) AS {x}" if c == alan else q(c) for c in cols)
            return self.yeni(f"SELECT {secim}, [__sira] FROM {onceki}")
        if not birim:
            ifade = f"(CAST({x} / {n} AS INTEGER) * {n})"
        elif birim == "d" and n == 1:
            ifade = f"(date({x}) || ' 00:00')"
        elif birim == "h" and 24 % n == 0:
            ifade = f"(date({x}) || ' ' || printf('%02d:00', (CAST(strftime('%H', {x}) AS INTEGER) / {n}) * {n}))"
        elif birim == "m" and 60 % n == 0:
            ifade = f"(strftime('%Y-%m-%d %H:', {x}) || printf('%02d', (CAST(strftime('%M', {x}) AS INTEGER) / {n}) * {n}))"
        else:
            raise SplHatasi("span için 1d, 24'ü bölen saatler (1h, 6h) ya da 60'ı bölen dakikalar (15m) destekleniyor", bas)
        secim = ", ".join(f"{ifade} AS {q(c)}" if c == alan else q(c) for c in cols)
        return self.yeni(f"SELECT {secim}, [__sira] FROM {onceki}")

    def k_rex(self, onceki, arg, bas):
        m = re.fullmatch(r'\s*field\s*=\s*(\S+)\s+("(?:\\.|[^"\\])*")\s*', arg)
        if not m:
            raise SplHatasi('rex field=alan "(?<ad>desen)" biçiminde olmalı', bas)
        alan, desen = m.group(1), m.group(2)[1:-1].replace('\\"', '"')
        adlar = re.findall(r"\(\?<([A-Za-z_]\w*)>", desen)
        if not adlar:
            raise SplHatasi("rex deseninde en az bir adlı grup olmalı: (?<ad>...)", bas)
        python_deseni = re.sub(r"\(\?<(?=[A-Za-z_])", "(?P<", desen)
        try:
            re.compile(python_deseni)
        except re.error as e:
            raise SplHatasi(f"desen derlenemedi: {e}", bas)
        for ad in adlar:
            cols = self.sutunlar(onceki)
            ifade = f"spl_rex({sql_metin(python_deseni)}, {sql_metin(ad)}, {q(alan)})"
            secim = ", ".join(f"{ifade} AS {q(c)}" if c == ad else q(c) for c in cols)
            if ad not in cols:
                secim += f", {ifade} AS {q(ad)}"
            onceki = self.yeni(f"SELECT {secim}, [__sira] FROM {onceki}")
        return onceki

    def k_join(self, onceki, arg, bas):
        if "[" not in arg or not arg.rstrip().endswith("]"):
            raise SplHatasi("join alan [alt arama] biçiminde olmalı: join sunucu_id [search sourcetype=sunucular ...]", bas)
        ac = arg.index("[")
        kapa = len(arg.rstrip()) - 1
        bas_kisim = arg[:ac]
        secenek = dict(re.findall(r"(\w+)\s*=\s*(\w+)", bas_kisim))
        tur = secenek.get("type", "inner").lower()
        if tur not in ("inner", "left", "outer"):
            raise SplHatasi(f"bu join türü desteklenmiyor: {tur} (inner ya da left)", bas)
        anahtarlar = [k for k in re.split(r"[\s,]+", re.sub(r"\w+\s*=\s*\w+", " ", bas_kisim).strip()) if k]
        if not anahtarlar:
            raise SplHatasi("join için en az bir ortak alan gerekiyor: join sunucu_id [ ... ]", bas)
        alt_bas = bas + ac + 1
        alt_son = bas + kapa
        alt_metin = self.kaynak[alt_bas:alt_son]
        ilk = alt_metin.strip().split(None, 1)
        if ilk and ilk[0].lower() == "search":
            alt_bas += alt_metin.index(ilk[0]) + len("search")
        sag = self.hat(alt_bas, alt_son)
        L, R = self.sutunlar(onceki), self.sutunlar(sag)
        for k in anahtarlar:
            if k not in L or k not in R:
                raise SplHatasi(f"join alanı iki tarafta da olmalı: {k}", bas)
        anahtar = ", ".join(q(k) for k in anahtarlar)
        tek = self.yeni(f"SELECT * FROM (SELECT *, ROW_NUMBER() OVER (PARTITION BY {anahtar} ORDER BY [__sira]) AS [__ilk] "
                        f"FROM {sag}) WHERE [__ilk] = 1")
        on = " AND ".join(f"l.{q(k)} = r.{q(k)}" for k in anahtarlar)
        secim = [f"coalesce(r.{q(c)}, l.{q(c)}) AS {q(c)}" if c in R and c not in anahtarlar else f"l.{q(c)} AS {q(c)}"
                 for c in L]
        secim += [f"r.{q(c)} AS {q(c)}" for c in R if c not in L]
        katilim = "JOIN" if tur == "inner" else "LEFT JOIN"
        return self.yeni(f"SELECT {', '.join(secim)}, l.[__sira] AS [__sira] FROM {onceki} AS l {katilim} {tek} AS r ON {on}")

    # — yardımcılar —
    def _satirlar(self, sql):
        """Çeviri sırasında veriye bak (chart sütunları, zaman dilimleri, transaction grupları)."""
        al = getattr(self.sutun_bul, "satirlar", None)
        if al is None:
            raise SplHatasi("bu komut çeviri sırasında veriye bakmayı gerektiriyor")
        return al(self.with_sql(sql))

    def _kose(self, arg, bas, ornek):
        """'seçenekler [ alt arama ]' → (seçenek metni, alt arama metni, alt aramanın mutlak başı)."""
        ac = arg.find("[")
        kapa = len(arg.rstrip()) - 1
        if ac < 0 or _kapanis(arg, ac) != kapa:
            raise SplHatasi(f"biçim: {ornek}", bas)
        return arg[:ac], arg[ac + 1:kapa], bas + ac + 1

    @staticmethod
    def _secenekler(arg, bas):
        """'delim="," maxpause=1h alan1 alan2' → ({seçenek: (değer, konum)}, [(kelime, konum)])."""
        secenek, kelimeler = {}, []
        for m in re.finditer(r'(\w+)\s*=\s*("(?:\\.|[^"\\])*"|[^\s,]+)|([^\s,=]+)', arg):
            if m.group(3):
                kelimeler.append((m.group(3), bas + m.start(3)))
            else:
                v = m.group(2)
                tirnakli = v.startswith('"') and len(v) > 1
                secenek[m.group(1).lower()] = (_metin_coz(v) if tirnakli else v, bas + m.start(2) + int(tirnakli))
        return secenek, kelimeler

    @staticmethod
    def _fazla_secenek(secenek, komut, izinli):
        for ad, (_, konum) in secenek.items():
            if ad not in izinli:
                raise SplHatasi(f"bu {komut} seçeneği desteklenmiyor: {ad} (desteklenenler: {', '.join(izinli)})", konum)

    @staticmethod
    def _sure_coz(v, konum):
        m = re.fullmatch(r"(\d+)\s*(s|sec|m|min|h|d)?", v.strip().lower())
        if not m or int(m.group(1)) == 0:
            raise SplHatasi("süre 30s, 15m, 1h ya da 1d biçiminde olmalı", konum)
        birim = {"sec": "s", "min": "m"}.get(m.group(2), m.group(2) or "s")
        return int(m.group(1)) * _SURE[birim]

    def _alan_var(self, cols, ad, konum):
        if ad not in cols:
            raise SplHatasi(f"böyle bir alan yok: {ad}", konum)

    @staticmethod
    def _deger_sql(v):
        try:
            float(v)
            return v
        except ValueError:
            return sql_metin(v)

    @staticmethod
    def _ust_yaz(cols, yeniler, ifade):
        """Sütunlar sırasıyla; yeni alan aynı adlı alanın yerine geçer, olmayanlar sona eklenir."""
        secim = [f"{ifade(c)} AS {q(c)}" if c in yeniler else q(c) for c in cols]
        return secim + [f"{ifade(n)} AS {q(n)}" for n in yeniler if n not in cols]

    # — fillnull —
    def k_fillnull(self, onceki, arg, bas):
        secenek, kelimeler = self._secenekler(arg, bas)
        self._fazla_secenek(secenek, "fillnull", ("value",))
        deger = self._deger_sql(secenek["value"][0]) if "value" in secenek else "0"
        cols = self.sutunlar(onceki)
        adlar = [k for k, _ in kelimeler]
        hedef = adlar or cols
        secim = [f"coalesce({q(c)}, {deger}) AS {q(c)}" if c in hedef else q(c) for c in cols]
        secim += [f"{deger} AS {q(a)}" for a in adlar if a not in cols]
        return self.yeni(f"SELECT {', '.join(secim)}, [__sira] FROM {onceki}")

    # — eventstats, streamstats —
    def k_eventstats(self, onceki, arg, bas):
        toplamalar, gruplar, _ = self._stats_coz(arg, bas, "eventstats")
        cols = self.sutunlar(onceki)
        for g in gruplar:
            self._alan_var(cols, g, bas)
        aggs = ", ".join(f"{s} AS {q(n)}" for n, s, _ in toplamalar)
        if gruplar:
            ozet = self.yeni(f"SELECT {', '.join(q(g) for g in gruplar)}, {aggs} FROM {onceki} WHERE "
                             + " AND ".join(f"{q(g)} IS NOT NULL" for g in gruplar)
                             + f" GROUP BY {', '.join(q(g) for g in gruplar)}")
            on = " AND ".join(f"l.{q(g)} = r.{q(g)}" for g in gruplar)
        else:
            ozet = self.yeni(f"SELECT {aggs} FROM {onceki}")
            on = "1"
        yeniler = [n for n, _, _ in toplamalar]
        secim = [f"r.{q(c)} AS {q(c)}" if c in yeniler else f"l.{q(c)} AS {q(c)}" for c in cols]
        secim += [f"r.{q(n)} AS {q(n)}" for n in yeniler if n not in cols]
        return self.yeni(f"SELECT {', '.join(secim)}, l.[__sira] AS [__sira] FROM {onceki} AS l LEFT JOIN {ozet} AS r ON {on}")

    def k_streamstats(self, onceki, arg, bas):
        toplamalar, gruplar, secenek = self._stats_coz(arg, bas, "streamstats", secenekli=True)
        self._fazla_secenek(secenek, "streamstats", ("window", "current"))
        pencere, konum = secenek.get("window", ("0", bas))
        if not pencere.isdigit():
            raise SplHatasi("window= bir sayı olmalı", konum)
        n = int(pencere)
        dahil = secenek.get("current", ("t", bas))[0].lower() in ("t", "true", "1")
        ust = "CURRENT ROW" if dahil else "1 PRECEDING"
        alt = "UNBOUNDED PRECEDING" if n == 0 else f"{n - 1 if dahil else n} PRECEDING"
        if alt == "0 PRECEDING":
            alt = "CURRENT ROW"
        cols = self.sutunlar(onceki)
        for g in gruplar:
            self._alan_var(cols, g, bas)
        bolum = f"PARTITION BY {', '.join(q(g) for g in gruplar)} " if gruplar else ""
        cerceve = f"OVER ({bolum}ORDER BY [__sira] ROWS BETWEEN {alt} AND {ust})"
        ifade = {}
        for ad, sql, fn in toplamalar:
            if fn not in ("count", "sum", "avg", "mean", "min", "max"):
                raise SplHatasi(f"bu tezgahta streamstats count, sum, avg, min ve max ile çalışır ({fn} değil)", bas)
            ifade[ad] = f"{sql} {cerceve}"
        secim = self._ust_yaz(cols, list(ifade), lambda c: ifade[c] if c in ifade else q(c))
        return self.yeni(f"SELECT {', '.join(secim)}, [__sira] FROM {onceki}")

    # — chart, timechart —
    def _seri_coz(self, arg, bas, komut):
        """'count over a by b limit=5' → (seçenekler, [(ad, sql, fn)], over, [by alanları])."""
        a = _Akis(_jetonla(_STATS, arg, bas), bas + len(arg))
        secenek, toplamalar, over, by = {}, [], None, []
        while not a.bitti():
            if a.isl_mi(","):
                a.i += 1
                continue
            t = a.bak()
            if t[0] == "kelime" and a.isl_mi("=", 1):
                a.i += 2
                secenek[t[1].lower()] = (a.ad(), t[2])
                continue
            if a.kelime_mi("over"):
                a.i += 1
                over = a.ad()
                continue
            if a.kelime_mi("by"):
                a.i += 1
                while not a.bitti() and not (a.bak()[0] == "kelime" and a.isl_mi("=", 1)):
                    if a.isl_mi(","):
                        a.i += 1
                        continue
                    by.append((a.ad(), a.bak(-1)[2]))
                continue
            toplamalar.append(self._toplama_oku(a))
        if not toplamalar:
            raise SplHatasi(f"{komut}'tan sonra bir toplama bekleniyordu (ör. {komut} count by durum)", bas)
        return secenek, toplamalar, over, by

    @staticmethod
    def _seri_sirasi(degerler):
        ozel = [d for d in ("NULL", "OTHER") if d in degerler]
        duz = [d for d in degerler if d not in ("NULL", "OTHER")]
        try:
            duz.sort(key=float)
        except (TypeError, ValueError):
            duz.sort()
        return duz + ozel

    def _seriler(self, onceki, satir, sutun, sql, secenek, kosul):
        """Sütun bölmesi: (__r, __c, __v) özeti ve seri adları; limit, useother ve usenull uygulanır."""
        def evet(ad):
            return secenek.get(ad, ("t", 0))[0].lower() in ("t", "true", "1")
        lim, konum = secenek.get("limit", ("10", 0))
        lim = lim.lower().replace("top", "")
        if not lim.isdigit():
            raise SplHatasi("limit= bir sayı olmalı (0: sınırsız)", konum)
        limit = int(lim)
        anahtar = f"CAST({q(sutun)} AS TEXT)"
        nul = f" AND {q(sutun)} IS NOT NULL"
        if evet("usenull"):
            anahtar, nul = f"coalesce({anahtar}, 'NULL')", ""

        def ozet(c):
            return self.yeni(f"SELECT {satir} AS [__r], {c} AS [__c], {sql} AS [__v] FROM {onceki} "
                             f"WHERE {kosul}{nul} GROUP BY [__r], [__c]")
        ham = ozet(anahtar)
        toplam = self._satirlar(f"SELECT [__c], SUM([__v]) FROM {ham} GROUP BY [__c]")
        degerler = [r[0] for r in toplam]
        if limit and len(degerler) > limit:
            secilen = [r[0] for r in sorted(toplam, key=lambda r: (-(r[1] or 0), str(r[0])))[:limit]]
            liste = ", ".join(sql_metin(v) for v in secilen)
            if evet("useother"):
                ham = ozet(f"CASE WHEN {anahtar} IN ({liste}) THEN {anahtar} ELSE 'OTHER' END")
                degerler = secilen + ["OTHER"]
            else:
                ham = self.yeni(f"SELECT * FROM {ham} WHERE [__c] IN ({liste})")
                degerler = secilen
        return ham, self._seri_sirasi(degerler)

    @staticmethod
    def _hucreler(seriler, sifirla=False):
        def hucre(v):
            h = f"MAX(CASE WHEN [__c] = {sql_metin(v)} THEN [__v] END)"
            return f"coalesce({h}, 0)" if sifirla else h
        return "".join(f", {hucre(v)} AS {q(v)}" for v in seriler)

    def k_chart(self, onceki, arg, bas):
        secenek, toplamalar, over, by = self._seri_coz(arg, bas, "chart")
        self._fazla_secenek(secenek, "chart", ("limit", "useother", "usenull"))
        if over is None:
            if len(by) > 2:
                raise SplHatasi("chart en çok iki bölme alır: chart count by satır_alanı sütun_alanı", by[2][1])
            satir, sutun = (by + [None, None])[:2]
        else:
            if len(by) > 1:
                raise SplHatasi("over kullanınca by tek alan alır: chart count over satır by sütun", by[1][1])
            satir, sutun = (over, bas), (by[0] if by else None)
        cols = self.sutunlar(onceki)
        for f in (satir, sutun):
            if f:
                self._alan_var(cols, *f)
        if sutun is None:                               # tek boyut: stats ile aynı tablo
            return self._stats_sql(onceki, toplamalar, [satir[0]] if satir else [])
        if len(toplamalar) > 1:
            raise SplHatasi("sütun bölmesiyle chart tek bir toplama alır", bas)
        _, sql, _ = toplamalar[0]
        ham, seriler = self._seriler(onceki, q(satir[0]), sutun[0], sql, secenek, f"{q(satir[0])} IS NOT NULL")
        return self.yeni(f"SELECT [__r] AS {q(satir[0])}{self._hucreler(seriler)}, ROW_NUMBER() OVER (ORDER BY [__r]) "
                         f"AS [__sira] FROM {ham} GROUP BY [__r]")

    def k_timechart(self, onceki, arg, bas):
        secenek, toplamalar, over, by = self._seri_coz(arg, bas, "timechart")
        self._fazla_secenek(secenek, "timechart", ("span", "limit", "useother", "usenull"))
        if over is not None or len(by) > 1:
            raise SplHatasi("timechart satırları zamana böler; en çok bir by alanı alır: timechart span=1h count by rol", bas)
        if "span" not in secenek:
            raise SplHatasi("bu tezgahta timechart için span= zorunlu (ör. span=1d, span=1h, span=30m)", bas)
        s = self._sure_coz(*secenek["span"])
        cols = self.sutunlar(onceki)
        if "_time" not in cols:
            raise SplHatasi('timechart _time alanına göre çalışır; önce zamanı kur: '
                            'eval _time=strptime(acilis, "%Y-%m-%d %H:%M")', bas)
        kova = f"(CAST([_time] / {s} AS INTEGER) * {s})"

        def sifir(fn):
            return fn in ("count", "dc", "distinct_count")
        if not by:
            aggs = ", ".join(f"{sql} AS {q(ad)}" for ad, sql, _ in toplamalar)
            ham = self.yeni(f"SELECT {kova} AS [__r], {aggs} FROM {onceki} WHERE [_time] IS NOT NULL GROUP BY [__r]")
            adlar = [(ad, sifir(fn)) for ad, _, fn in toplamalar]
        else:
            self._alan_var(cols, *by[0])
            if len(toplamalar) > 1:
                raise SplHatasi("by ile timechart tek bir toplama alır", bas)
            _, sql, fn = toplamalar[0]
            ozet, seriler = self._seriler(onceki, kova, by[0][0], sql, secenek, "[_time] IS NOT NULL")
            ham = self.yeni(f"SELECT [__r]{self._hucreler(seriler)} FROM {ozet} GROUP BY [__r]")
            adlar = [(v, sifir(fn)) for v in seriler]
        lo, hi = self._satirlar(f"SELECT MIN([__r]), MAX([__r]) FROM {ham}")[0]
        if lo is None:
            kovalar = self.yeni("SELECT NULL AS [__r] WHERE 0")
        else:
            adet = (int(hi) - int(lo)) // s + 1
            if adet > 2000:
                raise SplHatasi(f"{adet} zaman dilimi çıkıyor; span'ı büyüt", secenek["span"][1])
            kovalar = self.yeni("SELECT column1 AS [__r] FROM (VALUES "
                                + ", ".join(f"({int(lo) + n * s})" for n in range(adet)) + ")")
        secim = "".join(f", {'coalesce(h.' + q(a) + ', 0)' if z else 'h.' + q(a)} AS {q(a)}" for a, z in adlar)
        return self.yeni(f"SELECT k.[__r] AS [_time]{secim}, ROW_NUMBER() OVER (ORDER BY k.[__r]) AS [__sira] "
                         f"FROM {kovalar} AS k LEFT JOIN {ham} AS h ON h.[__r] = k.[__r]")

    # — transaction —
    def _filtre(self, onceki, metin, konum):
        """startswith / endswith değeri: bir arama ifadesi, (arama ifadesi) ya da eval(boolean ifade)."""
        govde = metin.strip()
        if not govde:
            raise SplHatasi("startswith/endswith boş olamaz", konum)
        if govde.lower().startswith("eval(") and govde.endswith(")"):
            ic_bas = konum + metin.index("(") + 1
            a, kosul = self.ifade_cevir(govde[5:-1], ic_bas)
            if not a.bitti():
                raise SplHatasi(f"beklenmeyen: '{a.bak()[1]}'", a.bak()[2])
            return kosul
        if govde.startswith("(") and govde.endswith(")"):
            govde = govde[1:-1]
        return self._arama_kosulu(onceki, _jetonla(_ARAMA, govde, konum), konum + len(govde))

    def k_transaction(self, onceki, arg, bas):
        secenek, kelimeler = self._secenekler(arg, bas)
        self._fazla_secenek(secenek, "transaction", ("maxspan", "maxpause", "startswith", "endswith"))
        cols = self.sutunlar(onceki)
        if "_time" not in cols:
            raise SplHatasi('transaction olayları _time\'a göre dizer; önce zamanı kur: '
                            'eval _time=strptime(zaman, "%Y-%m-%d %H:%M")', bas)
        if not kelimeler:
            raise SplHatasi("transaction en az bir alan ister: transaction sunucu maxpause=1h", bas)
        for ad, konum in kelimeler:
            self._alan_var(cols, ad, konum)
        anahtar = [a for a, _ in kelimeler]
        maxspan = self._sure_coz(*secenek["maxspan"]) if "maxspan" in secenek else None
        maxpause = self._sure_coz(*secenek["maxpause"]) if "maxpause" in secenek else None
        bas_k = self._filtre(onceki, *secenek["startswith"]) if "startswith" in secenek else "0"
        son_k = self._filtre(onceki, *secenek["endswith"]) if "endswith" in secenek else "0"
        satirlar = self._satirlar(
            f"SELECT [__sira], [_time], {', '.join(q(a) for a in anahtar)}, ({bas_k}), ({son_k}) FROM {onceki} "
            "WHERE [_time] IS NOT NULL AND " + " AND ".join(f"{q(a)} IS NOT NULL" for a in anahtar))
        gruplar = _islem_gruplari(satirlar, len(anahtar), maxspan, maxpause,
                                  "startswith" in secenek, "endswith" in secenek)
        if gruplar:
            uyeler = self.yeni("SELECT column1 AS [__s], column2 AS [__g] FROM (VALUES "
                               + ", ".join(f"({s}, {g})" for s, g in gruplar) + ")")
        else:
            uyeler = self.yeni("SELECT NULL AS [__s], NULL AS [__g] WHERE 0")
        secim = ["MIN(o.[_time]) AS [_time]"] + [f"MIN(o.{q(a)}) AS {q(a)}" for a in anahtar]
        secim += ["MAX(o.[_time]) - MIN(o.[_time]) AS [duration]", "COUNT(*) AS [eventcount]"]
        secim += [f"spl_values(o.{q(c)}) AS {q(c)}" for c in cols
                  if c not in anahtar and c not in ("_time", "duration", "eventcount")]
        return self.yeni(f"SELECT {', '.join(secim)}, ROW_NUMBER() OVER (ORDER BY MIN(o.[_time]) DESC, "
                         f"MIN(o.[__sira]) DESC) AS [__sira] FROM {onceki} AS o JOIN {uyeler} AS u "
                         f"ON u.[__s] = o.[__sira] GROUP BY u.[__g]")

    # — lookup —
    def _lookup_tablosu(self, a):
        t = a.bak()
        tablo = a.ad()
        if tablo.lower().endswith(".csv"):
            tablo = tablo[:-4]
        try:
            return tablo, list(self.sutun_bul(f"SELECT * FROM {q(tablo)} LIMIT 0"))
        except SplHatasi:
            raise
        except Exception:
            raise SplHatasi(f"böyle bir lookup tablosu yok: {tablo}", t[2])

    def k_lookup(self, onceki, arg, bas):
        a = _Akis(_jetonla(_ALANLAR, arg, bas), bas + len(arg))
        if a.bitti():
            raise SplHatasi("biçim: lookup tablo alan [AS yerel_alan] OUTPUT çıktı_alanı [AS yeni_ad]", bas)
        tablo, lcols = self._lookup_tablosu(a)
        eslesme, cikti, kip = [], [], None
        while not a.bitti():
            if a.isl_mi(","):
                a.i += 1
                continue
            if a.kelime_mi("OUTPUT") or a.kelime_mi("OUTPUTNEW"):
                kip = a.al()[1].upper()
                continue
            t = a.bak()
            ad = a.ad()
            yerel = ad
            if a.kelime_mi("as"):
                a.i += 1
                yerel = a.ad()
            (cikti if kip else eslesme).append((ad, yerel, t[2]))
        if not eslesme:
            raise SplHatasi("lookup için en az bir eşleşme alanı gerekir: lookup sla oncelik", bas)
        for ad, _, konum in eslesme + cikti:
            if ad not in lcols:
                raise SplHatasi(f"{tablo} lookup'ında böyle bir alan yok: {ad} (alanlar: {', '.join(lcols)})", konum)
        if not cikti:
            es = {e[0] for e in eslesme}
            cikti = [(c, c, bas) for c in lcols if c not in es]
            kip = "OUTPUT"
        cols = self.sutunlar(onceki)
        anahtar = ", ".join(q(e[0]) for e in eslesme)
        ozet = self.yeni(f"SELECT {anahtar}, " + ", ".join(f"spl_values({q(c[0])}) AS [__o{n}]" for n, c in enumerate(cikti))
                         + f", 1 AS [__eslesti] FROM {q(tablo)} GROUP BY {anahtar}")
        on = " AND ".join(f"l.{q(yerel)} = r.{q(ad)}" if yerel in cols else "0" for ad, yerel, _ in eslesme)
        hedef = {c[1]: n for n, c in enumerate(cikti)}

        def deger(c):
            n = hedef[c]
            if c not in cols:
                return f"r.[__o{n}]"
            if kip == "OUTPUTNEW":
                return f"coalesce(l.{q(c)}, r.[__o{n}])"
            return f"CASE WHEN r.[__eslesti] IS NULL THEN l.{q(c)} ELSE r.[__o{n}] END"
        secim = [f"{deger(c)} AS {q(c)}" if c in hedef else f"l.{q(c)} AS {q(c)}" for c in cols]
        secim += [f"{deger(h)} AS {q(h)}" for h in hedef if h not in cols]
        return self.yeni(f"SELECT {', '.join(secim)}, l.[__sira] AS [__sira] FROM {onceki} AS l LEFT JOIN {ozet} AS r ON {on}")

    # — veri üreten komutlar —
    def u_inputlookup(self, arg, bas):
        a = _Akis(_jetonla(_ALANLAR, arg, bas), bas + len(arg))
        if a.bitti():
            raise SplHatasi("inputlookup bir tablo adı ister: | inputlookup sla", bas)
        tablo, _ = self._lookup_tablosu(a)
        if not a.bitti():
            raise SplHatasi(f"beklenmeyen: '{a.bak()[1]}'", a.bak()[2])
        return self.yeni(f"SELECT *, rowid AS [__sira] FROM {q(tablo)}")

    def u_makeresults(self, arg, bas):
        m = re.fullmatch(r"\s*(?:count\s*=\s*(\d+))?\s*", arg)
        if not m:
            raise SplHatasi("biçim: | makeresults [count=N]", bas)
        n = int(m.group(1) or 1)
        if not 1 <= n <= 1000:
            raise SplHatasi("count 1 ile 1000 arasında olmalı", bas)
        an = _epoch(SIMDI)
        return self.yeni("SELECT column1 AS [_time], column2 AS [__sira] FROM (VALUES "
                         + ", ".join(f"({an}, {i})" for i in range(1, n + 1)) + ")")

    # — append, appendpipe —
    def _ekle(self, ust, alt):
        L, R = self.sutunlar(ust), self.sutunlar(alt)
        hepsi = L + [c for c in R if c not in L]

        def sec(var):
            return ", ".join(q(c) if c in var else f"NULL AS {q(c)}" for c in hepsi)
        birlesik = self.yeni(f"SELECT {sec(L)}, 0 AS [__p], [__sira] AS [__s] FROM {ust} "
                             f"UNION ALL SELECT {sec(R)}, 1, [__sira] FROM {alt}")
        return self.yeni(f"SELECT {self.secim(hepsi)}, ROW_NUMBER() OVER (ORDER BY [__p], [__s]) AS [__sira] FROM {birlesik}")

    def k_append(self, onceki, arg, bas):
        on, ic, ic_bas = self._kose(arg, bas, "append [search sourcetype=... | ...]")
        if on.strip():
            raise SplHatasi("bu tezgahta append seçenek almaz", bas)
        return self._ekle(onceki, self._alt_arama(ic, ic_bas))

    def k_appendpipe(self, onceki, arg, bas):
        on, ic, ic_bas = self._kose(arg, bas, 'appendpipe [stats count | eval durum="TOPLAM"]')
        if on.strip():
            raise SplHatasi("bu tezgahta appendpipe seçenek almaz", bas)
        if not ic.strip():
            raise SplHatasi("appendpipe'ın alt borusu boş", ic_bas)
        return self._ekle(onceki, self.hat(ic_bas, ic_bas + len(ic), baslangic=onceki))

    # — çok değerli alanlar —
    def _tek_alan(self, kelimeler, komut, ornek, bas):
        if len(kelimeler) != 1:
            raise SplHatasi(f"{komut} tek bir alan ister: {ornek}", bas)
        return kelimeler[0]

    def k_makemv(self, onceki, arg, bas):
        secenek, kelimeler = self._secenekler(arg, bas)
        self._fazla_secenek(secenek, "makemv", ("delim", "allowempty"))
        alan, konum = self._tek_alan(kelimeler, "makemv", 'makemv delim="," alan', bas)
        cols = self.sutunlar(onceki)
        self._alan_var(cols, alan, konum)
        ayrac = secenek.get("delim", (" ", bas))[0]
        if not ayrac:
            raise SplHatasi("delim boş olamaz", bas)
        bos = int(secenek.get("allowempty", ("f", bas))[0].lower() in ("t", "true", "1"))
        secim = self._ust_yaz(cols, [alan], lambda c: f"spl_makemv({q(c)}, {sql_metin(ayrac)}, {bos})" if c == alan else q(c))
        return self.yeni(f"SELECT {', '.join(secim)}, [__sira] FROM {onceki}")

    def k_mvexpand(self, onceki, arg, bas):
        secenek, kelimeler = self._secenekler(arg, bas)
        self._fazla_secenek(secenek, "mvexpand", ("limit",))
        alan, konum = self._tek_alan(kelimeler, "mvexpand", "mvexpand alan", bas)
        cols = self.sutunlar(onceki)
        self._alan_var(cols, alan, konum)
        sinir = ""
        if "limit" in secenek:
            if not secenek["limit"][0].isdigit():
                raise SplHatasi("limit= bir sayı olmalı", secenek["limit"][1])
            sinir = f" WHERE j.key < {int(secenek['limit'][0])}"
        secim = ", ".join(f"j.value AS {q(c)}" if c == alan else f"o.{q(c)} AS {q(c)}" for c in cols)
        return self.yeni(f"SELECT {secim}, ROW_NUMBER() OVER (ORDER BY o.[__sira], j.key) AS [__sira] "
                         f"FROM {onceki} AS o, json_each(spl_mvjson(o.{q(alan)})) AS j{sinir}")

    # — xyseries, untable —
    def k_xyseries(self, onceki, arg, bas):
        adlar = self._alan_listesi(arg, bas)
        if len(adlar) != 3:
            raise SplHatasi("xyseries üç alan ister: xyseries satır_alanı sütun_alanı değer_alanı", bas)
        cols = self.sutunlar(onceki)
        for ad, konum in adlar:
            self._alan_var(cols, ad, konum)
        x, y, v = (ad for ad, _ in adlar)
        ham = self.yeni(f"SELECT {q(x)} AS [__r], CAST({q(y)} AS TEXT) AS [__c], {q(v)} AS [__v], [__sira] FROM {onceki} "
                        f"WHERE {q(x)} IS NOT NULL AND {q(y)} IS NOT NULL")
        seriler = self._seri_sirasi([r[0] for r in self._satirlar(f"SELECT DISTINCT [__c] FROM {ham}")])
        return self.yeni(f"SELECT [__r] AS {q(x)}{self._hucreler(seriler)}, ROW_NUMBER() OVER (ORDER BY MIN([__sira])) "
                         f"AS [__sira] FROM {ham} GROUP BY [__r]")

    def k_untable(self, onceki, arg, bas):
        adlar = self._alan_listesi(arg, bas)
        if len(adlar) != 3:
            raise SplHatasi("untable üç alan ister: untable satır_alanı ad_alanı değer_alanı", bas)
        cols = self.sutunlar(onceki)
        self._alan_var(cols, *adlar[0])
        x, ad, deger = (a for a, _ in adlar)
        digerleri = [c for c in cols if c != x]
        if not digerleri:
            return self.yeni(f"SELECT {q(x)}, NULL AS {q(ad)}, NULL AS {q(deger)}, [__sira] FROM {onceki} WHERE 0")
        birlesik = self.yeni(" UNION ALL ".join(
            f"SELECT {q(x)} AS {q(x)}, {sql_metin(c)} AS {q(ad)}, {q(c)} AS {q(deger)}, [__sira] AS [__s], {n} AS [__n] "
            f"FROM {onceki} WHERE {q(c)} IS NOT NULL" for n, c in enumerate(digerleri)))
        return self.yeni(f"SELECT {q(x)}, {q(ad)}, {q(deger)}, ROW_NUMBER() OVER (ORDER BY [__s], [__n]) AS [__sira] "
                         f"FROM {birlesik}")


def _islem_gruplari(satirlar, nk, maxspan, maxpause, bas_var, son_var):
    """transaction: (sira, _time, anahtar..., başlar_mı, biter_mi) satırları → [(sira, grup no)].

    Olaylar anahtara ve zamana göre dizilir. Yeni işlem şu durumlarda başlar: araya maxpause'tan uzun
    süre girdi, işlem maxspan'ı aştı ya da startswith'e uyan bir olay geldi. endswith'e uyan olay işlemi
    kapatır. startswith/endswith istenip tamamlanmayan işlemler atılır (Splunk'ın varsayılanı keepevicted=false).
    """
    sonuc, gid = [], 0

    def anahtar(r):
        return tuple(str(x) for x in r[2:2 + nk])
    for _, grup in groupby(sorted(satirlar, key=lambda r: (anahtar(r), r[1], r[0])), key=anahtar):
        acik = None
        for r in grup:
            sira, t, b, e = r[0], r[1], r[2 + nk], r[3 + nk]
            if acik is not None and ((maxpause is not None and t - acik["son"] > maxpause)
                                     or (maxspan is not None and t - acik["bas"] > maxspan) or (bas_var and b)):
                if not son_var:
                    gid += 1
                    sonuc.extend((s, gid) for s in acik["uyeler"])
                acik = None
            if acik is None:
                if bas_var and not b:
                    continue                    # başlangıç olayı gelmeden gelen olay hiçbir işleme girmez
                acik = {"bas": t, "son": t, "uyeler": []}
            acik["uyeler"].append(sira)
            acik["son"] = t
            if son_var and e:
                gid += 1
                sonuc.extend((s, gid) for s in acik["uyeler"])
                acik = None
        if acik is not None and not son_var:
            gid += 1
            sonuc.extend((s, gid) for s in acik["uyeler"])
    return sonuc


def _zaman_metni(v):
    try:
        an = datetime.fromtimestamp(float(v), timezone.utc)
    except (TypeError, ValueError, OverflowError, OSError):
        return v
    return an.strftime("%Y-%m-%d %H:%M:%S" if an.second else "%Y-%m-%d %H:%M")


def satir_donustur(sutunlar, satirlar):
    """Sonuçları göstermeye hazırla → (testlerin gördüğü satırlar, tabloda gösterilen satırlar).

    _time okunur tarih olur; çok değerli alan testlerde liste, tabloda MV ile ayrık metin kalır."""
    zaman = [n for n, c in enumerate(sutunlar) if c == "_time"]
    ham, goster = [], []
    for r in satirlar:
        r = list(r)
        for n in zaman:
            if isinstance(r[n], (int, float)):
                r[n] = _zaman_metni(r[n])
        goster.append(tuple(r))
        ham.append(tuple(v.split(MV) if isinstance(v, str) and MV in v else v for v in r))
    return ham, goster


def _epoch(metin):
    return int(datetime.strptime(metin, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).timestamp())


def cevir(kaynak, sutun_bul):
    if not kaynak.strip():
        raise SplHatasi("arama boş", 0)
    acik, esle = _makro_ac(kaynak, sutun_bul)
    c = _Cevirici(acik, sutun_bul)
    try:
        ad = c.hat(0, len(acik))
    except SplHatasi as e:
        if esle:
            e.konum = esle(e.konum)
            e.msg += f" · makrolar açılınca arama: {' '.join(acik.split())}"
        raise
    return c.with_sql(f"SELECT * FROM {ad} ORDER BY [__sira]")


def fonksiyonlari_kaydet(db):
    def m(x):
        return "" if x is None else str(x)

    def joker(a, desen):
        if a is None:
            return 0
        rx = "^" + ".*".join(re.escape(p) for p in m(desen).split("*")) + "$"
        return int(re.search(rx, m(a), re.I | re.S) is not None)

    def like(a, desen):
        if a is None:
            return None
        rx = "^" + "".join(".*" if ch == "%" else "." if ch == "_" else re.escape(ch) for ch in m(desen)) + "$"
        return int(re.search(rx, m(a), re.S) is not None)

    def regex(a, desen):
        if a is None:
            return None
        try:
            return int(re.search(m(desen), m(a)) is not None)
        except re.error:
            return 0

    def degistir(a, desen, yeni):
        if a is None:
            return None
        try:
            return re.sub(m(desen), re.sub(r"\\(\d)", r"\\\1", m(yeni)), m(a))
        except re.error:
            return a

    def rex(desen, ad, metin):
        if metin is None:
            return None
        r = re.search(desen, m(metin))
        return r.group(ad) if r else None

    def strptime(metin, bicim):
        if metin is None:
            return None
        try:
            return int(datetime.strptime(m(metin), m(bicim)).replace(tzinfo=timezone.utc).timestamp())
        except ValueError:
            return None

    def strftime(an, bicim):
        if an is None:
            return None
        try:
            return datetime.fromtimestamp(float(an), timezone.utc).strftime(m(bicim))
        except (ValueError, OverflowError, OSError):
            return None

    def degerler(x):
        """Çok değerli alanın değerleri (tek değer → tek elemanlı liste, boş → boş liste)."""
        if x is None:
            return []
        return x.split(MV) if isinstance(x, str) and MV in x else [x]

    def mv(liste):
        """Değer listesini alana çevir: boş → NULL, tek değer → kendisi, çok değer → MV ile ayrık metin."""
        if not liste:
            return None
        if len(liste) == 1:
            return liste[0]
        return MV.join(m(v) for v in liste)

    def herhangi(a, kosul):
        return int(any(kosul(m(v)) for v in degerler(a)))

    def alt_esit(a, b):
        b = m(b)
        if "*" in b:
            return herhangi(a, lambda v: joker(v, b))
        return herhangi(a, lambda v: v.lower() == b.lower())

    def mvindex(x, bas, son):
        d = degerler(x)
        if not d or bas is None:
            return None
        n = len(d)
        i = int(bas) + (n if int(bas) < 0 else 0)
        if son is None:
            return d[i] if 0 <= i < n else None
        j = int(son) + (n if int(son) < 0 else 0)
        if i < 0 or i >= n or j < i:
            return None
        return mv(d[i:min(j, n - 1) + 1])

    def bol(x, ayrac):
        if x is None:
            return None
        x, ayrac = m(x), m(ayrac)
        return mv(list(x) if ayrac == "" else x.split(ayrac))

    def makemv(x, ayrac, bos):
        if x is None:
            return None
        parcalar = m(x).split(m(ayrac))
        return mv(parcalar if bos else [p for p in parcalar if p != ""])

    def tur(x):
        if x is None:
            return "Invalid"
        if isinstance(x, (int, float)):
            return "Number"
        return "String"

    def kirp(yon):
        def f(x, kars):
            if x is None:
                return None
            k = None if kars is None else m(kars)
            return {"": m(x).strip, "l": m(x).lstrip, "r": m(x).rstrip}[yon](k)
        return f

    def printf(bicim, *args):
        try:
            return m(bicim) % tuple(args)
        except (TypeError, ValueError):
            return None

    def sayi(fn):
        def f(x, *y):
            if x is None or any(v is None for v in y):
                return None
            try:
                return fn(float(x), *(float(v) for v in y))
            except (ValueError, OverflowError):
                return None
        return f

    class Values:
        """stats values(): farklı değerler, metin olarak sıralı."""
        def __init__(self):
            self.v = set()

        def step(self, x):
            self.v.update(degerler(x))

        def finalize(self):
            if len(self.v) == 1:
                return next(iter(self.v))
            return mv(sorted(self.v, key=m))

    class Liste:
        """stats list(): bütün değerler geliş sırasıyla."""
        def __init__(self):
            self.v = []

        def step(self, x):
            self.v.extend(degerler(x))

        def finalize(self):
            return mv(self.v)

    fonksiyonlar = {
        "spl_esit": (2, lambda a, b: herhangi(a, lambda v: v.lower() == m(b).lower())),
        "spl_wild": (2, lambda a, b: herhangi(a, lambda v: joker(v, b))),
        "spl_icerir": (2, lambda a, b: herhangi(a, lambda v: m(b).lower() in v.lower())),
        "spl_alt_esit": (2, alt_esit),
        "spl_mvcount": (1, lambda x: len(degerler(x)) or None),
        "spl_mvindex": (3, mvindex),
        "spl_mvjoin": (2, lambda x, d: None if x is None else m(d).join(m(v) for v in degerler(x))),
        "spl_mvappend": (-1, lambda *xs: mv([v for x in xs for v in degerler(x)])),
        "spl_mvdedup": (1, lambda x: mv(list(dict.fromkeys(degerler(x))))),
        "spl_mvsort": (1, lambda x: mv(sorted(degerler(x), key=m))),
        "spl_mvjson": (1, lambda x: json.dumps(degerler(x), ensure_ascii=False)),
        "spl_split": (2, bol),
        "spl_makemv": (3, makemv),
        "spl_typeof": (1, tur),
        "spl_trim": (2, kirp("")),
        "spl_ltrim": (2, kirp("l")),
        "spl_rtrim": (2, kirp("r")),
        "spl_printf": (-1, printf),
        "spl_floor": (1, sayi(lambda x: int(math.floor(x)))),
        "spl_ceil": (1, sayi(lambda x: int(math.ceil(x)))),
        "spl_sqrt": (1, sayi(lambda x: math.sqrt(x) if x >= 0 else None)),
        "spl_pow": (2, sayi(lambda x, y: x ** y)),
        "spl_kucuk": (1, lambda a: None if a is None else str(a).lower()),
        "spl_buyuk": (1, lambda a: None if a is None else str(a).upper()),
        "spl_like": (2, like),
        "spl_regex": (2, regex),
        "spl_replace": (3, degistir),
        "spl_rex": (3, rex),
        "spl_strptime": (2, strptime),
        "spl_strftime": (2, strftime),
    }
    class Sapma:
        """stdev ve var: örneklem (n − 1) formülü, Splunk'taki gibi."""
        def __init__(self):
            self.v = []

        def step(self, x):
            try:
                self.v.append(float(x))
            except (TypeError, ValueError):
                pass

        def varyans(self):
            n = len(self.v)
            if n < 2:
                return 0.0 if n == 1 else None
            ort = sum(self.v) / n
            return sum((x - ort) ** 2 for x in self.v) / (n - 1)

        def finalize(self):
            v = self.varyans()
            return None if v is None else math.sqrt(v)

    class Varyans(Sapma):
        def finalize(self):
            return self.varyans()

    class Uc:
        """earliest/latest: _time'ı en küçük/en büyük olan olayın değeri."""
        en_buyuk = False

        def __init__(self):
            self.t = self.d = None

        def step(self, x, t):
            if x is None or t is None:
                return
            if self.t is None or (t > self.t if self.en_buyuk else t < self.t):
                self.t, self.d = t, x

        def finalize(self):
            return self.d

    class EnGec(Uc):
        en_buyuk = True

    for ad, (n, fn) in fonksiyonlar.items():
        db.create_function(ad, n, fn, deterministic=True)
    db.create_aggregate("spl_values", 1, Values)
    db.create_aggregate("spl_list", 1, Liste)
    db.create_aggregate("spl_stdev", 1, Sapma)
    db.create_aggregate("spl_var", 1, Varyans)
    db.create_aggregate("spl_earliest", 2, Uc)
    db.create_aggregate("spl_latest", 2, EnGec)
