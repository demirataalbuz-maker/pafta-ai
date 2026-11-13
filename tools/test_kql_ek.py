# -*- coding: utf-8 -*-
"""KQL tezgahının mv-apply, evaluate bag_unpack ve _GetWatchlist eklemeleri (sandbox/kql.py).

    python tools/test_kql_ek.py
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine import runners  # noqa: E402

D = "datatable(ad:string, olcum:dynamic)['a', dynamic([5,1,9]), 'b', dynamic([2]), 'c', dynamic([])]"


def kos(sorgu, setup=None):
    r = runners.get("kql").run(sorgu, "", setup)
    return r.get("error"), "".join(t for k, t in r.get("segs", []) if k == "out")


class MvApply(unittest.TestCase):
    def test_summarize_satir_basina(self):
        hata, out = kos(D + " | mv-apply x = olcum to typeof(long) on (summarize toplam = sum(x), en_buyuk = max(x)) | project ad, toplam, en_buyuk")
        self.assertIsNone(hata)
        self.assertEqual(out, "a|15|9\nb|2|2\nc||\n", "by'sız summarize boş dizide de bir satır verir")
        hata, out = kos(D + " | mv-apply x = olcum to typeof(long) on (where x > 4 | summarize n = count()) | project ad, n")
        self.assertEqual(out, "a|2\nb|0\nc|0\n", "eleman kalmayan satırda count() = 0")
        hata, out = kos(D + " | mv-apply x = olcum to typeof(long) on (where x > 4 | summarize n = count() by x) | project ad, n")
        self.assertEqual(out, "a|1\na|1\n", "by'lı summarize boş grupta satır vermez")

    def test_top_satir_basina(self):
        hata, out = kos(D + " | mv-apply x = olcum to typeof(long) on (top 1 by x asc) | project ad, x")
        self.assertEqual(out, "a|1\nb|2\n")
        hata, out = kos(D + " | mv-apply x = olcum to typeof(long) on (top 2 by x desc) | summarize s = sum(x) by ad | sort by ad asc")
        self.assertEqual(out, "a|14\nb|2\n", "a'dan 9 ve 5")

    def test_zincir_ve_take(self):
        hata, out = kos(D + " | mv-apply x = olcum to typeof(long) on (extend iki = x * 2 | where iki > 3 | take 1) | project ad, x, iki")
        self.assertEqual(out, "a|5|10\nb|2|4\n")

    def test_by_ile_summarize(self):
        hata, out = kos(D + " | mv-apply x = olcum to typeof(long) on (summarize c = count() by tek = x % 2) | project ad, tek, c")
        self.assertEqual(sorted(out.splitlines()), ["a|1|3", "b|0|1"])

    def test_hedefsiz_bicim(self):
        hata, out = kos(D + " | mv-apply olcum to typeof(long) on (top 1 by olcum) | project ad, olcum")
        self.assertEqual(out, "a|9\nb|2\n")

    def test_gercek_tablo(self):
        hata, out = kos("istekler | extend d = parse_json(ayrinti) | mv-apply e = d.etiketler to typeof(string) on "
                        "(where e == 'beta' | project e) | project zaman, e")
        self.assertIsNone(hata)
        self.assertTrue(out and all(s.endswith("|beta") for s in out.splitlines()))

    def test_hatalar(self):
        hata, _ = kos(D + " | mv-apply x = olcum on (sort by x)")
        self.assertIn("desteklenmiyor: sort", hata["msg"])
        hata, _ = kos(D + " | mv-apply x = olcum on (where x > 1")
        self.assertIsNotNone(hata)


class BagUnpack(unittest.TestCase):
    T = ("datatable(id:long, d:dynamic)[1, dynamic({'a':1,'b':'x'}), 2, dynamic({'b':'y','c':[1,2]}), "
         "3, dynamic(null), 4, dynamic([1,2])]")

    def test_anahtarlar_ve_eksikler(self):
        hata, out = kos(self.T + " | evaluate bag_unpack(d) | project id, a, b, c")
        self.assertIsNone(hata)
        self.assertEqual(out, "1|1|x|\n2||y|[1,2]\n3|||\n4|||\n",
                         "olmayan anahtar null; nesne olmayan satır (null, dizi) korunur, hepsi null")

    def test_sutun_listesi_ve_onek(self):
        hata, out = kos(self.T + " | evaluate bag_unpack(d, 'p_') | getschema | project ColumnName")
        self.assertEqual(out.split(), ["id", "p_a", "p_b", "p_c"], "kaynak sütun düşer; anahtarlar sıralı, önekli")

    def test_cakisma(self):
        hata, _ = kos("datatable(a:long, d:dynamic)[1, dynamic({'a':2})] | evaluate bag_unpack(d)")
        self.assertIn("çakışıyor", hata["msg"])
        hata, out = kos("datatable(a:long, d:dynamic)[1, dynamic({'a':2})] | evaluate bag_unpack(d, 'd_') | project a, d_a")
        self.assertEqual(out, "1|2\n", "önek çakışmayı çözer")

    def test_desteklenmeyen_eklenti(self):
        hata, _ = kos("istekler | evaluate pivot(durum)")
        self.assertIn("bag_unpack", hata["msg"])


class Watchlist(unittest.TestCase):
    def test_watchlist(self):
        kur = "CREATE TABLE watchlist_vip (SearchKey TEXT, Rol TEXT); INSERT INTO watchlist_vip VALUES ('ayse','admin'),('can','muhasebe');"
        hata, out = kos("_GetWatchlist('vip') | project SearchKey, Rol | sort by SearchKey asc", kur)
        self.assertEqual(out, "ayse|admin\ncan|muhasebe\n")
        hata, out = kos("let vip = _GetWatchlist('vip') | project kullanici = SearchKey, Rol; "
                        "istekler | join kind=inner vip on kullanici | summarize n = count() by Rol", kur)
        self.assertIsNone(hata)
        hata, _ = kos("_GetWatchlist('yok')")
        self.assertIn("watchlist bulunamadı", hata["msg"])

    def test_watchlist_parantezsiz_sag_taraf(self):
        kur = "CREATE TABLE watchlist_vip (SearchKey TEXT, Rol TEXT); INSERT INTO watchlist_vip VALUES ('ayse','admin'),('can','muhasebe');"
        for isl in ("join kind=inner", "lookup kind=inner"):
            hata, out = kos(f"istekler | {isl} _GetWatchlist('vip') on $left.kullanici == $right.SearchKey "
                            "| summarize n = count() by Rol | sort by Rol asc", kur)
            self.assertIsNone(hata, isl)
            self.assertEqual(out, "admin|5\nmuhasebe|5\n", isl)
        hata, out = kos("union _GetWatchlist('vip'), _GetWatchlist('vip') | count", kur)
        self.assertIsNone(hata)
        self.assertEqual(out, "4\n")


if __name__ == "__main__":
    unittest.main(verbosity=1)
