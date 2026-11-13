# -*- coding: utf-8 -*-
"""ai-temel-17 gerçek deneyi: yerel üretim tipi inference sunucusunun (Ollama /api/generate,
stream=true) akışlı yanıt yaşam döngüsü. Öğrenci ham NDJSON akışını çözer ve ölçer; deney gerçek
sunucuya akışlı istek atar, her parçanın varış anını kaydeder, num_predict ile akışı kesip
done_reason="length" gözlemler ve sonucu öğrencinin çıktısıyla bağımsızca karşılaştırır.

Bütün istekler zararsız ve sentetiktir. Model bu deney tarafından yüklendiyse sonunda boşaltılır
(kullanıcının sunucusuna ve önceden yüklü modellerine dokunulmaz; kaynak sahipliği ai_lab'dedir).
"""
import json
import time
import urllib.error
import urllib.request

import ai_lab

# Her istek: (etiket, istem, num_predict). Küçük num_predict olan istek akışı token sınırında keser
# (done_reason="length"); büyük olanlar modelin kendi durak jetonuyla biter (done_reason="stop").
ISTEKLER = [
    ("kisa", "İki artı iki kaçtır? Yalnız sayıyı yaz.", 64),
    ("sayma", "Birden başlayarak yüze kadar say, aralarına virgül koy.", 16),  # sınırda kesilir
    ("tanim", "Fotosentezi tek cümlede açıkla.", 64),
    ("baskent", "Türkiye'nin başkenti neresidir? Kısa yanıt ver.", 64),
]


def referans(satirlar, gelisler, *, birlestirme="hepsi", ttft="ilk", kesildi=True, parca="satir"):
    """Akış raporunun doğru çıktısı (varsayılanlarla) ve testlerin kullandığı hatalı varyantlar.

    Girdinin geçerli olduğu varsayılır; doğrulamayı testteki `gecerli` sarmalayıcısı ve öğrenci yapar.
    """
    nesneler = [json.loads(s) for s in satirlar]
    yanitlar = [o for o in nesneler if not o.get("done")]
    son = nesneler[-1]
    parcalar = [o.get("response", "") for o in yanitlar]
    metin = (parcalar[-1] if parcalar else "") if birlestirme == "son" else "".join(parcalar)
    dr = son.get("done_reason")
    return {
        "metin": metin,
        "parca": son.get("eval_count") if parca == "token" else len(yanitlar),
        "done_reason": dr,
        "ttft_ms": (None if not gelisler else (gelisler[-1] if ttft == "son" else gelisler[0])),
        "sure_ms": gelisler[-1] if gelisler else None,
        "tokens": son.get("eval_count"),
        "kesildi": (dr == "length") if kesildi else False,
    }


def _akis_cagir(oturum, istem, num_predict, seed, sicaklik=0.2, sure=120, denemeler=None):
    """Gerçek akışlı /api/generate çağrısı. Ham NDJSON satırlarını ve her yanıt parçasının istekten
    itibaren milisaniye cinsinden varış anını döndürür. Taşıma hatası yükseltilir; çağıran kaydeder."""
    govde = {"model": oturum.model, "prompt": istem, "stream": True,
             "options": {"temperature": sicaklik, "seed": seed, "num_predict": num_predict, "num_ctx": 4096}}
    if getattr(oturum, "dusunme", False):
        govde["think"] = False
    if not oturum._once_yuklu:
        govde["keep_alive"] = "5m"  # döngü boyunca model yüklü kalsın; boşaltmayı oturum.__exit__ yapar
    veri = json.dumps(govde).encode("utf-8")
    # Model yeni yüklenirken ya da sunucu başka bir istekle meşgulken Ollama geçici 500/bağlantı hatası
    # dönebilir (SohbetOturumu.sohbet'teki not). Akış açılışındaki geçici hata en fazla iki kez yeniden
    # denenir; kalıcı hata ya da 4xx çağırana yükseltilir ve istek hatası sayılır.
    for bekle in (2, 4, None):
        satirlar, gelisler, meta = [], [], None
        req = urllib.request.Request(oturum.adres + "/api/generate", veri, {"Content-Type": "application/json"})
        bas = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=sure) as yanit:
                for ham in yanit:  # urllib satır satır verir (NDJSON); her satır tam bir JSON nesnesidir
                    s = ham.decode("utf-8").strip()
                    if not s:
                        continue
                    t_ms = round((time.perf_counter() - bas) * 1000)
                    o = json.loads(s)
                    satirlar.append(s)
                    if o.get("done"):
                        meta = o
                    else:
                        gelisler.append(t_ms)
            return satirlar, gelisler, meta
        except (urllib.error.HTTPError, urllib.error.URLError, ConnectionError) as e:
            if denemeler is not None:
                denemeler.append({"hata":f"{type(e).__name__}: {e}","yeniden_bekle_sn":bekle,
                                  "alinan_satir":len(satirlar)})
            if (isinstance(e, urllib.error.HTTPError) and e.code < 500) or bekle is None:
                raise
            time.sleep(bekle)


def deney(akis_raporu, sicaklik=0.2):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    taban = int(time.time()) % (10 ** 6)
    kayitlar = []
    saat = time.perf_counter()
    with ai_lab.SohbetOturumu() as oturum:
        def calistir(n, etiket, istem, np, kip, bariyer=None):
            if bariyer is not None:
                bariyer.wait(timeout=20)
            kayit = {"etiket":etiket,"istem":istem,"num_predict":np,"seed":taban+n,
                     "kip":kip,"hata":None,"yeniden_denemeler":[],
                     "istem_bas_ms":(time.perf_counter()-saat)*1000}
            try:
                satirlar, gelisler, meta = _akis_cagir(oturum, istem, np, seed=taban+n,
                                                     sicaklik=sicaklik,denemeler=kayit["yeniden_denemeler"])
                # Öğrenci ayrıştırması hata verse de alınan ham sunucu verisini sakla.
                kayit.update(_satirlar=satirlar,_gelisler=gelisler,bitis_nesnesi=meta)
                sonuc = akis_raporu(list(satirlar),list(gelisler))
                kayit.update(sonuc)
                kayit.update(satir_sayisi=len(satirlar),prompt_token=(meta or {}).get("prompt_eval_count"),
                             eval_sure_ms=round((meta or {}).get("eval_duration",0)/1e6) or None,
                             yukleme_ms=round((meta or {}).get("load_duration",0)/1e6) or None)
            except ai_lab.GercekLabYok:
                raise
            except Exception as e:
                kayit["hata"]=f"{type(e).__name__}: {e}"
            finally:
                kayit["istem_son_ms"]=(time.perf_counter()-saat)*1000
            return kayit
        for n,(etiket,istem,np) in enumerate(ISTEKLER):
            kayitlar.append(calistir(n,etiket,istem,np,"ardisik"))
        bariyer=Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as havuz:
            futures=[havuz.submit(calistir,len(ISTEKLER)+i,f"paralel-{i+1}",
                      istem,24,"eszamanli",bariyer) for i,istem in enumerate([
                      "Birden başlayarak kırka kadar say, aralarına virgül koy.",
                      "On farklı bitkinin adını sırayla yaz."])]
            paralel=[f.result() for f in futures]
        kayitlar.extend(paralel)
        bellek=oturum.bellek()
        ortam=dict(oturum.kayit)
    ortam["temizlik"]=oturum.kayit.get("temizlik")
    overlap=max(k["istem_bas_ms"] for k in paralel)<min(k["istem_son_ms"] for k in paralel)
    return {"ortam":ortam,"bellek":bellek,
            "ayarlar":{"sicaklik":sicaklik,"taban_seed":taban,"istek_sayisi":len(kayitlar),"num_ctx":4096},
            "eszamanli":{"istek_sayisi":len(paralel),"cakisan_araliklar":overlap,
                          "sinir":"İstemcide çakışan gerçek HTTP çağrıları; backend sürekli batching kanıtı değil."},
            "kayitlar":kayitlar}


def ozet(r):
    g = [k for k in r["kayitlar"] if k["hata"] is None]
    def tokens_sn(k):
        return round(k["tokens"] / (k["eval_sure_ms"] / 1000), 1) if k.get("tokens") and k.get("eval_sure_ms") else None
    hizlar = [tokens_sn(k) for k in g if tokens_sn(k) is not None]
    ttftler = [k["ttft_ms"] for k in g if k["ttft_ms"] is not None]
    return {"istek": len(r["kayitlar"]), "gecerli": len(g),
            "kesilen": sum(1 for k in g if k["kesildi"]),
            "durak": sum(1 for k in g if k["done_reason"] == "stop"),
            "ttft_ms_min": min(ttftler) if ttftler else None, "ttft_ms_maks": max(ttftler) if ttftler else None,
            "tokens_sn_ort": round(sum(hizlar) / len(hizlar), 1) if hizlar else None,
            "toplam_parca": sum(k["parca"] for k in g if isinstance(k["parca"], int))}


def goster(akis_raporu):
    """Çalıştır düğmesi: gerçek akışlı inference deneyi."""
    r = deney(akis_raporu)
    o = r["ortam"]
    print(f"Sunucu: {o.get('sunucu', {}).get('adres')} ({o.get('sunucu', {}).get('sahip')}) · model: "
          f"{(o.get('model') or {}).get('ad')} · Ollama {o.get('ollama_surumu')}\n")
    for k in r["kayitlar"]:
        if k["hata"]:
            print(f"[{k['etiket']}] HATA: {k['hata']}")
            continue
        hiz = round(k["tokens"] / (k["eval_sure_ms"] / 1000), 1) if k.get("tokens") and k.get("eval_sure_ms") else "?"
        print(f"[{k['etiket']}] num_predict={k['num_predict']} → {k['parca']} parça, done_reason={k['done_reason']}"
              f"{' (KESİLDİ)' if k['kesildi'] else ''}")
        print(f"   TTFT {k['ttft_ms']} ms · toplam {k['sure_ms']} ms · {k['tokens']} token · ~{hiz} token/sn")
        print(f"   yanıt: {k['metin'][:120].strip().replace(chr(10), ' ')}")
    print("\nÖzet:", ozet(r))
    print("Eşzamanlı HTTP:",r["eszamanli"])
    print("\nKanıt:", ai_lab.kanit_yaz("temel-akis-calistir", {"kaynak": "gercek", "kabul": False,
                                                              "ders": "ai-temel-17", "ortam": o, "deney": r, "ozet": ozet(r)}))
