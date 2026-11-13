# -*- coding: utf-8 -*-
"""ai-uretim-23 gerçek deney: öğrencinin PUCT seçimi ve MCTS geri yayılımı gerçek bir oyunda (tic-tac-toe) tam bir MCTS
ajanının parçası olarak çalışır. Her çağrı bağımsız bir referansla denetlenir; ajanın hamleleri tüm oyun ağacını
çözen minimax ile karşılaştırılır ve rastgele oyuncuya ve minimax'a karşı oyunlar oynanır. Simülasyon bütçesinin
etkisi ve rakibin zorladığı tuzak pozisyonlar ölçülür."""
import functools, math, random
import ai_lab
from sandbox import ai_uretim_ortak as O

AYAR = {"butce": [16, 64, 256, 1024], "oyun": 20, "seed": 23, "c_puct": 1.5}
CIZGI = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]


def _kazanan(t):
    for a, b, c in CIZGI:
        if t[a] and t[a] == t[b] == t[c]:
            return t[a]
    return 0 if 0 in t else 2          # 2: berabere


def _sira(t):
    return 1 if t.count(1) == t.count(-1) else -1


@functools.lru_cache(maxsize=None)
def _minimax(t):
    """Tam çözüm: sıradaki oyuncu açısından değer (+1 kazanır, 0 berabere, -1 kaybeder)."""
    k = _kazanan(t)
    if k == 2:
        return 0
    if k:
        return 1 if k == _sira(t) else -1
    s = _sira(t)
    return max(-_minimax(t[:i] + (s,) + t[i + 1:]) for i in range(9) if t[i] == 0)


def _ref_puct(cocuk, c):
    top = sum(d["N"] for d in cocuk)
    en, sec = -float("inf"), None
    for d in cocuk:
        q = d["W"] / d["N"] if d["N"] else 0.0
        p = q + c * d["P"] * math.sqrt(top) / (1 + d["N"])
        if p > en + 1e-12:
            en, sec = p, d["dal_id"]
    return sec


CIZGI_HATALI = [c if c != (0, 4, 8) else (0, 4, 7) for c in CIZGI]     # doğrulayıcıda tek bir yazım hatası


def _hatali_kazanan(t):
    for a, b, c in CIZGI_HATALI:
        if t[a] and t[a] == t[b] == t[c]:
            return t[a]
    return 0 if 0 in t else 2


class _Ajan:
    def __init__(self, puct_dal_sec, mcts_geri_yayilim, rnd, kazanan=None):
        self.puct, self.geri, self.rnd, self.denetim = puct_dal_sec, mcts_geri_yayilim, rnd, {"cagri": 0, "uyusmaz": 0}
        self.kazanan = kazanan or _kazanan

    def hamle(self, t, butce):
        agac = {"k": {"parent": None, "N": 0, "W": 0.0, "Q": 0.0, "durum": t, "cocuk": None}}
        for _ in range(butce):
            dug = "k"
            while agac[dug]["cocuk"]:                                       # seçim
                cocuk = [{"dal_id": c, "N": agac[c]["N"], "W": agac[c]["W"], "P": 1.0 / len(agac[dug]["cocuk"])} for c in agac[dug]["cocuk"]]
                sec = self.puct([dict(x) for x in cocuk], AYAR["c_puct"])["secilen_dal_id"]
                self.denetim["cagri"] += 1
                self.denetim["uyusmaz"] += sec != _ref_puct(cocuk, AYAR["c_puct"])
                dug = sec
            d = agac[dug]["durum"]
            if self.kazanan(d) == 0 and agac[dug]["cocuk"] is None:         # genişletme
                agac[dug]["cocuk"] = []
                for i in range(9):
                    if d[i] == 0:
                        cid = f"{dug}/{i}"
                        agac[cid] = {"parent": dug, "N": 0, "W": 0.0, "Q": 0.0, "durum": d[:i] + (_sira(d),) + d[i + 1:], "cocuk": None}
                        agac[dug]["cocuk"].append(cid)
                dug = self.rnd.choice(agac[dug]["cocuk"])
            s = agac[dug]["durum"]                                          # rastgele oynatma
            while self.kazanan(s) == 0:
                bos = [i for i in range(9) if s[i] == 0]
                i = self.rnd.choice(bos)
                s = s[:i] + (_sira(s),) + s[i + 1:]
            k = self.kazanan(s)
            # ödül, düğüme hamleyi yapan oyuncu açısından; geri yayılımda her seviyede işaret değişir
            yol, x = [], dug
            while x is not None:
                yol.append(x); x = agac[x]["parent"]
            for x in yol:
                hamleci = -_sira(agac[x]["durum"])
                odul = 0.5 if k == 2 else (1.0 if k == hamleci else 0.0)
                saf = {y: {"parent": agac[y]["parent"], "N": agac[y]["N"], "W": agac[y]["W"], "Q": agac[y]["Q"]} for y in (x,)}
                saf[x]["parent"] = None
                o = self.geri(saf, x, odul)
                beklenen_N, beklenen_W = agac[x]["N"] + 1, round(agac[x]["W"] + odul, 6)
                self.denetim["cagri"] += 1
                self.denetim["uyusmaz"] += (o["guncel_agac"][x]["N"] != beklenen_N or abs(o["guncel_agac"][x]["W"] - beklenen_W) > 1e-9)
                agac[x].update(N=o["guncel_agac"][x]["N"], W=o["guncel_agac"][x]["W"], Q=o["guncel_agac"][x]["Q"])
        en = max(agac["k"]["cocuk"], key=lambda c: (agac[c]["N"], c))
        return int(en.rsplit("/", 1)[1])


def _oyna(ajan, butce, rakip, rnd, ajan_ilk):
    t = (0,) * 9
    sira_ajan = 1 if ajan_ilk else -1
    while _kazanan(t) == 0:
        if _sira(t) == sira_ajan:
            i = ajan.hamle(t, butce)
        elif rakip == "rastgele":
            i = rnd.choice([j for j in range(9) if t[j] == 0])
        else:
            i = max((j for j in range(9) if t[j] == 0), key=lambda j: (-_minimax(t[:j] + (_sira(t),) + t[j + 1:]), -j))
        t = t[:i] + (_sira(t),) + t[i + 1:]
    k = _kazanan(t)
    return "berabere" if k == 2 else ("kazandi" if k == sira_ajan else "kaybetti")


def _hatali_odul(puct_dal_sec, mcts_geri_yayilim):
    """Ödül hacklemesi: doğrulayıcının kazanma çizgilerinde tek bir yazım hatası var ((0,4,8) yerine (0,4,7)). Arama arttıkça
    ajan gerçek en iyi hamle yerine sahte çizgiyi tamamlayan hamleyi daha sık seçer mi?"""
    rnd = random.Random(5)
    poz = []
    for _ in range(20000):
        t = (0,) * 9
        for _ in range(rnd.randrange(2, 6)):
            if _kazanan(t):
                break
            i = rnd.choice([j for j in range(9) if t[j] == 0])
            t = t[:i] + (_sira(t),) + t[i + 1:]
        if _kazanan(t) or _hatali_kazanan(t):
            continue
        s = _sira(t)
        sahte = [j for j in range(9) if t[j] == 0 and _hatali_kazanan(t[:j] + (s,) + t[j + 1:]) == s and _kazanan(t[:j] + (s,) + t[j + 1:]) == 0]
        if not sahte:
            continue
        deg = {j: -_minimax(t[:j] + (s,) + t[j + 1:]) for j in range(9) if t[j] == 0}
        if deg[sahte[0]] < max(deg.values()) and t not in [p[0] for p in poz]:
            poz.append((t, sahte[0], max(deg.values())))
        if len(poz) >= 12:
            break
    tablo = {}
    for b in AYAR["butce"]:
        tablo[b] = {}
        for ad, kz in (("dogru_odul", _kazanan), ("hatali_odul", _hatali_kazanan)):
            aj = _Ajan(puct_dal_sec, mcts_geri_yayilim, random.Random(1), kz)
            sec = [aj.hamle(p[0], b) for p in poz]
            tablo[b][ad] = {"sahte_hamle": sum(h == p[1] for h, p in zip(sec, poz)),
                            "kotu_hamle": sum(-_minimax(p[0][:h] + (_sira(p[0]),) + p[0][h + 1:]) < p[2] for h, p in zip(sec, poz))}
    return {"pozisyon": len(poz), "tablo": tablo}


def deney(puct_dal_sec, mcts_geri_yayilim):
    HO = _hatali_odul(puct_dal_sec, mcts_geri_yayilim)
    hb = [HO["tablo"][b]["hatali_odul"]["sahte_hamle"] for b in AYAR["butce"]]
    rnd = random.Random(AYAR["seed"])
    ajan = _Ajan(puct_dal_sec, mcts_geri_yayilim, rnd)
    # Tuzak pozisyonlar: tek doğru hamlesi olan gerçek pozisyonlar (minimax ile bulunur)
    tuzaklar = []
    for _ in range(4000):
        t = (0,) * 9
        for _ in range(rnd.randrange(2, 6)):
            if _kazanan(t):
                break
            i = rnd.choice([j for j in range(9) if t[j] == 0])
            t = t[:i] + (_sira(t),) + t[i + 1:]
        if _kazanan(t) == 0:
            degerler = {j: -_minimax(t[:j] + (_sira(t),) + t[j + 1:]) for j in range(9) if t[j] == 0}
            en = max(degerler.values())
            if list(degerler.values()).count(en) == 1 and en >= 0 and len(degerler) >= 4 and t not in [x[0] for x in tuzaklar]:
                tuzaklar.append((t, max(degerler, key=degerler.get)))
        if len(tuzaklar) >= 12:
            break
    tablo = {}
    for b in AYAR["butce"]:
        dogru = sum(ajan.hamle(t, b) == j for t, j in tuzaklar)
        tablo[b] = {"tuzak_dogru": dogru, "tuzak": len(tuzaklar)}
    son = AYAR["butce"][-1]
    sonuc = {"rastgele": {"kazandi": 0, "berabere": 0, "kaybetti": 0}, "minimax": {"kazandi": 0, "berabere": 0, "kaybetti": 0}}
    for g in range(AYAR["oyun"]):
        for rakip in sonuc:
            sonuc[rakip][_oyna(ajan, son, rakip, rnd, g % 2 == 0)] += 1
    return {
        "surumler": O.surumler(), "c_puct": AYAR["c_puct"], "cagri": ajan.denetim["cagri"], "uyusmaz": ajan.denetim["uyusmaz"],
        "cagri_ayni": ajan.denetim["uyusmaz"] == 0, "butce_tablosu": tablo, "oyunlar": sonuc,
        "minimaxa_kaybetmedi": sonuc["minimax"]["kaybetti"] == 0, "rastgeleye_kaybetmedi": sonuc["rastgele"]["kaybetti"] == 0,
        "butce_iyilestirdi": tablo[AYAR["butce"][-1]]["tuzak_dogru"] > tablo[AYAR["butce"][0]]["tuzak_dogru"],
        "hatali_odul": HO,
        "arama_hatayi_somuruyor": (hb[-1] > hb[0] and hb[-1] >= 0.75 * HO["pozisyon"]
                                   and HO["tablo"][AYAR["butce"][-1]]["dogru_odul"]["sahte_hamle"] == 0),
        "olcum": (f"Öğrencinin PUCT ve geri yayılım işlevleri {ajan.denetim['cagri']} çağrıda referansla "
                  f"{'aynı' if ajan.denetim['uyusmaz'] == 0 else str(ajan.denetim['uyusmaz']) + ' kez farklı'}. Tek doğru hamleli "
                  f"{len(tuzaklar)} tuzak pozisyonda doğru hamle (bütçe " + ", ".join(f"{b}: {v['tuzak_dogru']}" for b, v in tablo.items()) +
                  f"). {son} simülasyonla {AYAR['oyun']} oyun: rastgeleye karşı {sonuc['rastgele']}, minimax'a karşı {sonuc['minimax']}. "
                  f"Hatalı ödül ((0,4,8) yerine (0,4,7)): sahte çizgiyi tamamlayan hamle {HO['pozisyon']} pozisyonda bütçe "
                  + ", ".join(f"{b}: {HO['tablo'][b]['hatali_odul']['sahte_hamle']}" for b in AYAR["butce"]) +
                  "; doğru ödülle " + ", ".join(f"{b}: {HO['tablo'][b]['dogru_odul']['sahte_hamle']}" for b in AYAR["butce"]) + "."),
        "sinir": ("Öncül olasılıklar (P) tekdüzedir ve değer ağı yoktur: AlphaZero'daki öğrenilmiş politika/değer yerine rastgele oynatma "
                  "kullanılır. Tic-tac-toe küçük bir oyundur; LLM akıl yürütme ağaçlarında dallar metin, ödül doğrulayıcıdır. Hatalı ödül "
                  "deneyi tek bir elle konmuş hatayla yapılır; gerçek doğrulayıcı hataları daha seyrek ve bulunması daha zordur."),
    }


def goster(puct_dal_sec, mcts_geri_yayilim):
    r = deney(puct_dal_sec, mcts_geri_yayilim)
    print("Çağrı denetimi: %d çağrı, %d uyuşmazlık" % (r["cagri"], r["uyusmaz"]))
    for b, v in r["butce_tablosu"].items():
        print("  bütçe %4s: tuzak pozisyonlarda doğru hamle %d/%d" % (b, v["tuzak_dogru"], v["tuzak"]))
    print("Oyunlar:", r["oyunlar"])
    print("Sınır:", r["sinir"])
    print("Kanıt:", O.kanit("ai-uretim-23", "run", r))
