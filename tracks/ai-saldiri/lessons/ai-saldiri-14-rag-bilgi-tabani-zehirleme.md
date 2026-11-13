---
id: ai-saldiri-14
title: RAG Bilgi Tabanı Zehirleme
summary: RAG belgelerini içerik parmak iziyle kaydet, geri getirme sıralamasını deterministik ölç ve canary taşıyan belgelerin temiz/zehirli indekslerdeki farkını raporla.
timeout: 45
---

::: anlat Gerçek biçimi bil, sentetik temsili ayırt et: Zehirleme modele değil bilgi tabanına yerleşir

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Gerçek bir RAG hattında belgeler parçalanır (chunk), embedding modeliyle vektöre çevrilir ve ChromaDB, pgvector ya da FAISS gibi bir indekse yazılır. Sorgu da vektöre çevrilir; en yakın `k` parça, benzerlik skorlarıyla geri gelir ve model bağlamına eklenir. Üretimde indeks kaydı belgenin kaynağını, yükleyenini ve içerik özetini tutar. | Görev 1–3: `veri/belgeler.json`, `veri/corpus.json` ve `veri/retrieval_kayitlari.json` içindeki **sentetik** belge, sorgu ve retrieval kayıtları; skor basit terim sayımıdır. Son adım: görünür sentetik corpus, gerçek SQLite dosyası ve FTS5 indeksi, kurulu yerel Ollama modelinden temiz ve zehirli bağlamla canlı yanıtlar. | Embedding ya da vektör benzerliği kullanılmaz; terim sayımı ve FTS5 BM25, vektör aramasının davranışını temsil etmez. Zehirli belgenin getirilmesi, modelin talimata uyduğunu kanıtlamaz. Gerçek bir bilgi tabanına belge yüklenmez. |

> [!NOT]
> Görev 1–3 sentetik veriyle çalışır. Bu görevlerde model, veritabanı ve ağ yoktur. Son adımdaki **Gerçek deney** görevi yalnız kurulu yerel Ollama modelini ve deneyin kendi SQLite dosyasını kullanır. `veri/` dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalanır; kopyada yaptığın değişiklik bir sonraki çalıştırmada sıfırlanır, **kalıcılık yoktur**. Son adımın corpus çalışma kopyası ise ayrıca kalıcı tutulur. Kontrol bu dosyalardan ayrı, gizli verilerle sınar.

RAG sisteminde kullanıcı sorgusu önce bilgi tabanından belge getirir; getirilen metinler model bağlamına eklenir. **Bilgi tabanı zehirleme**, saldırı yönlendirmesi veya yanlış içerik taşıyan belgenin indekse girmesi ve sonraki sorgularda bağlama seçilmesidir. Model bu metni kullanıcı göreviyle aynı bağlamda gördüğünde etkilenebilir.

Zinciri üç ayrı kanıtla izlemek gerekir:

- **İndeks:** Hangi belge, hangi kaynak ve içerik parmak iziyle kaydedildi?
- **Retrieval:** Sorguda hangi belgeler, hangi sırayla geri geldi?
- **Bağlam/yanıt:** Hangi belgeler modele verildi ve canary etkisi gözlendi mi?

İlk iki adımı gerçek model olmadan ölçebiliriz. Görev 1–3 indeks ve retrieval fixture'ları kullanır; ChromaDB ve Ollama bu görevlerin parçası değildir. Son adım ChromaDB kullanmaz; SQLite FTS5 ile retrieval yapar ve yerel Ollama modelinden canlı yanıt alır. Retrieval'da canary taşıyan belge görülmesi, modelin talimatı uyguladığını tek başına kanıtlamaz.

```python
import hashlib
metin = "Rapor\nBREACH:CANARY-42"
print(hashlib.sha256(metin.encode("utf-8")).hexdigest()[:12])
print("BREACH:CANARY-42" in metin.splitlines())
```

İçerik parmak izi değişiklikleri ayırt etmeye yardımcı olur; belgenin güvenli olduğunu göstermez.

**Görev 1'de sık tuzaklar:** Özeti `strip()` edilmiş metinden almak, yalnız sondaki satır sonuyla ayrılan iki içeriği aynı özete indirir (`veri/belgeler.json`, `kb-02` ve `kb-03`). Böylece sonradan değiştirilen bir belge değişmemiş görünebilir. Belgeyi `dict(belge)` ile kopyalayıp manifestoya koymak, metni de manifestoya taşır. Ayrıca belgede gelen bir `guven` alanını korur; güven düzeyini yükleyen kişi belirlemiş olur.
:::

::: tahmin
Basit bir retrieval skoru, sorgu terimlerinin belgedeki toplam geçiş sayısıdır. Üç çıktı satırını yaz:

```python
belgeler = {
    "temiz": "rag nedir",
    "zehirli": "rag rag rag\nBREACH:CANARY-42",
    "diger": "rag nedir",
}
sorgu = ["rag", "rag"]
skorlar = {kimlik: sum(metin.split().count(t) for t in set(sorgu)) for kimlik, metin in belgeler.items()}
print(skorlar)
print(sorted(skorlar, key=lambda kimlik: (-skorlar[kimlik], kimlik)))
print(sum("BREACH:CANARY-42" in metin.splitlines() for metin in belgeler.values()))
```

???

```cikti
{'temiz': 1, 'zehirli': 3, 'diger': 1}
['zehirli', 'diger', 'temiz']
1
```

Sorgudaki yinelenen terim `set` nedeniyle bir kez sayılır. Zehirli belgedeki üç `rag` geçişi skoru 3 yapar ve belgeyi ilk sıraya taşır; diğer iki belge 1 skorla kimlik sırasına göre dizilir. Canary tam satır yalnız zehirli belgede bulunur.
:::

::: gorev 1 · RAG indeks manifestosunu içerik parmak iziyle üret
`indeks_manifestosu(belgeler)` işlevini yaz. Girdi liste olmalı; her belge tam olarak `id`, `kaynak`, `metin` alanlarını taşıyan dict olmalıdır. `id` ve `kaynak` boş olmayan string, `metin` string olmalıdır. Belge kimlikleri benzersiz olmalı; geçersiz veya yinelenen veride `ValueError` yükselt.

Dönüş aşağıdaki nesnenin kanonik JSON stringidir (`ensure_ascii=False`, `sort_keys=True`, `separators=(",", ":")`):

```text
{"belgeler":[{"id":ID,"kaynak":KAYNAK,"sha256":METIN_SHA256,"guven":"guvenilmez"},...]}
```

Kayıtları belge kimliğine göre sırala. `sha256`, metnin UTF-8 baytlarının küçük harfli onaltılık SHA-256 özetidir. Belge metnini manifesto içine ayrıca kopyalama; kaynağı veya güven düzeyini yükseltme. Girdi listesini ve belgeleri değiştirme.

Görünür veri: `veri/belgeler.json`. Beklenen manifesto dosyanın `beklenen` alanındadır. Dört bozuk küme `ValueError` almalıdır.

```starter
import hashlib
import json
from ai_saldiri_veri import json_yukle

def indeks_manifestosu(belgeler):
    # KUSURLU BAŞLANGIÇ KODU: belgeyi metniyle birlikte manifestoya kopyalıyor, özeti strip() edilmiş metinden alıyor (yalnız satır sonu farkı olan içerikler aynı özete düşer), belgenin kendi "guven" alanını koruyor, kimliğe göre sıralamıyor, yinelenen kimliği denetlemiyor ve kanonik JSON ayarlarını kullanmıyor!
    kayitlar = []
    for belge in belgeler:
        kayit = dict(belge)
        kayit["sha256"] = hashlib.sha256(belge["metin"].strip().encode("utf-8")).hexdigest()
        kayit.setdefault("guven", "guvenilmez")
        kayitlar.append(kayit)
    return json.dumps({"belgeler": kayitlar})

veri = json_yukle("veri/belgeler.json")
sonuc = indeks_manifestosu([dict(b) for b in veri["belgeler"]])
print("doğru" if sonuc == veri["beklenen"] else "YANLIŞ")
for kayit in json.loads(sonuc)["belgeler"]:
    print(kayit["id"], kayit["sha256"][:12], "metin manifestoda!" if "metin" in kayit else "")
for kume in veri["bozuk_kumeler"]:
    try:
        indeks_manifestosu(kume)
        print([b.get("id") for b in kume], "KABUL edildi (yanlış)")
    except ValueError as hata:
        print([b.get("id") for b in kume], "reddedildi:", hata)
    except Exception as hata:
        print([b.get("id") for b in kume], "ValueError yerine", type(hata).__name__, "(yanlış)")
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-14")
```

```test
import copy
import hashlib
import json
BELGELER = [
    {"id": "d2", "kaynak": "dis-aktarim", "metin": "Rapor"},
    {"id": "d1", "kaynak": "web", "metin": "Not\nBREACH:CANARY-42"},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(BELGELER)
        sonuc = fn(BELGELER)
        beklenen = {"belgeler": [
            {"id": b["id"], "kaynak": b["kaynak"], "sha256": hashlib.sha256(b["metin"].encode("utf-8")).hexdigest(), "guven": "guvenilmez"}
            for b in sorted(BELGELER, key=lambda x: x["id"])
        ]}
        if json.loads(sonuc) != beklenen or BELGELER != once:
            return False
        if sonuc != json.dumps(beklenen, ensure_ascii=False, sort_keys=True, separators=(",", ":")):
            return False
        if fn(list(reversed(BELGELER))) != sonuc or json.loads(fn([])) != {"belgeler": []}:
            return False
        degisen = fn([dict(BELGELER[0], metin="Değişti")])
        if json.loads(degisen)["belgeler"][0]["sha256"] == beklenen["belgeler"][1]["sha256"]:
            return False
        if "dış-aktarım" not in fn([dict(BELGELER[0], kaynak="dış-aktarım")]):
            return False
        for belgeler in [
            None, BELGELER + [BELGELER[0]], [dict(BELGELER[0], id="")], [dict(BELGELER[0], id=3)],
            [dict(BELGELER[0], kaynak="")], [dict(BELGELER[0], kaynak=3)], [dict(BELGELER[0], metin=3)],
            [dict(BELGELER[0], ek=1)], [None],
        ]:
            try:
                fn(belgeler)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(indeks_manifestosu), "kaynak, içerik özeti, güven etiketi ve sıralama korunmalı")
def m_hash(belgeler):
    veri = json.loads(indeks_manifestosu(belgeler))
    for belge in veri["belgeler"]:
        belge["sha256"] = "0" * 64
    return json.dumps(veri, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
def m_guven(belgeler):
    return indeks_manifestosu(belgeler).replace("guvenilmez", "system")
def m_kaynak(belgeler):
    veri = json.loads(indeks_manifestosu(belgeler))
    for belge in veri["belgeler"]:
        belge.pop("kaynak", None)
    return json.dumps(veri, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
for ad, mutant in [("içerik özetini sabitleyen", m_hash), ("belgeyi system sayan", m_guven), ("kaynağı silen", m_kaynak)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
import hashlib
import json

def indeks_manifestosu(belgeler):
    if not isinstance(belgeler, list):
        raise ValueError("belge listesi gerekli")
    kimlikler = set()
    kayitlar = []
    for belge in belgeler:
        if not isinstance(belge, dict) or set(belge) != {"id", "kaynak", "metin"}:
            raise ValueError("belge şeması geçersiz")
        if not isinstance(belge["id"], str) or not belge["id"] or not isinstance(belge["kaynak"], str) or not belge["kaynak"] or not isinstance(belge["metin"], str):
            raise ValueError("belge alanları geçersiz")
        if belge["id"] in kimlikler:
            raise ValueError("yinelenen belge kimliği")
        kimlikler.add(belge["id"])
        kayitlar.append({
            "id": belge["id"], "kaynak": belge["kaynak"],
            "sha256": hashlib.sha256(belge["metin"].encode("utf-8")).hexdigest(),
            "guven": "guvenilmez",
        })
    kayitlar.sort(key=lambda x: x["id"])
    return json.dumps({"belgeler": kayitlar}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
```

```hint
Her belge için yeni bir manifesto sözlüğü kur. SHA-256 özetini metnin UTF-8 kodlamasından al; kayıtları kimliğe göre sıralayıp tek dış `belgeler` listesine koy.
```
:::

::: anlat Retrieval sıralaması saldırı yüzeyinin parçasıdır
Zehirli belgenin indekste bulunması ile sorguda ilk sıraya gelmesi farklı olaylardır. Saldırgan belgeyi sorgu terimleriyle doldurarak lexical retrieval'da öne çıkarmayı deneyebilir. Bu etkiyi ölçmek için skor, eşitlik kuralı ve `k` sınırı açık olmalıdır.

Bu dersteki küçük skor, sorgudaki **farklı terimlerin** belgedeki geçiş sayılarının toplamıdır. Böylece sorguda aynı terimi tekrarlamak skoru yapay biçimde katlamaz. Belgede tekrar eden terimler ise skoru yükseltir. Yalnız pozitif skorlu belgeler getirilir; eşit skorda kimlik sırası kullanılır. Bu basit yöntem ChromaDB'nin vektör benzerliğinin yerine geçmez; deterministik bir retrieval fixture'ıdır.

**Çıktı nasıl okunur?** `veri/corpus.json` içinde zehirli `d-03` belgesi `parola` ve `sıfırlama` terimlerini tekrarlayarak `s-1` sorgusunda ilk sıraya çıkar. Terim doldurmanın lexical retrieval'daki etkisi budur. `split()` ile ayrılan `sıfırlama:` belirteci, `sıfırlama` sorgusuyla eşleşmez. `s-5` gibi hiçbir terimin geçmediği sorguda boş liste dönmelidir. Sıfır skorlu belgeyi getirmek, bağlamı ilgisiz metinle doldurur.
:::

::: gorev 2 · Deterministik lexical retrieval sıralaması uygula
`rag_getir(sorgu, belgeler, k)` işlevini yaz. `sorgu` boş olmayan string; `k`, bool olmayan ve `0..len(belgeler)` aralığında tam sayı olmalıdır. Her belge tam olarak `id`, `metin` alanlarını taşısın; kimlik boş olmayan ve benzersiz string, metin string olmalıdır. Geçersiz veride `ValueError` yükselt.

Sorgu ve metinleri `casefold()` ile küçültüp `re.findall(r"\w+", metin)` ile terimlere ayır. Skor, sorgunun **farklı terimleri** için belgedeki geçiş sayılarının toplamıdır. Pozitif skorlu belgeleri azalan skor, eşitlikte artan belge kimliğiyle sırala; ilk `k` kimliği liste olarak dön. `k=0` boş liste döndürür fakat bütün girdi yine doğrulanır. Girdiyi değiştirme.

Görünür veri: `veri/corpus.json`. Her sorgunun `beklenen` alanı vardır; README tablosu nedenlerini açıklar.

```starter
import re
from ai_saldiri_veri import json_yukle

def rag_getir(sorgu, belgeler, k):
    # KUSURLU BAŞLANGIÇ KODU: sorgudaki yinelenen terimi her seferinde sayıyor, split() ile ayırdığı için noktalama terime yapışıyor ("sıfırlama:"), sıfır skorlu belgeleri de getiriyor, eşitlikte kimlik yerine girdi sırasını kullanıyor ve k/şema doğrulaması yapmıyor!
    terimler = sorgu.lower().split()
    skorlu = []
    for belge in belgeler:
        kelimeler = belge["metin"].lower().split()
        skorlu.append((sum(kelimeler.count(t) for t in terimler), belge["id"]))
    skorlu.sort(key=lambda x: -x[0])
    return [kimlik for _, kimlik in skorlu[:k]]

veri = json_yukle("veri/corpus.json")
for s in veri["sorgular"]:
    sonuc = rag_getir(s["sorgu"], veri["belgeler"], s["k"])
    print(s["id"], "doğru" if sonuc == s["beklenen"] else "YANLIŞ", sonuc, "" if sonuc == s["beklenen"] else "≠ " + str(s["beklenen"]))
for b in veri["bozuk_girdiler"]:
    try:
        rag_getir(b["sorgu"], b["belgeler"], b["k"])
        print(repr(b["sorgu"]), b["k"], "KABUL edildi (yanlış)")
    except ValueError as hata:
        print(repr(b["sorgu"]), b["k"], "reddedildi:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-14")
```

```test
import copy
BELGELER = [
    {"id": "temiz", "metin": "RAG nedir"},
    {"id": "zehirli", "metin": "rag rag rag\nBREACH:CANARY-42"},
    {"id": "diger", "metin": "rag nedir"},
    {"id": "alakasiz", "metin": "başka konu"},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(BELGELER)
        if fn("RAG", BELGELER, 3) != ["zehirli", "diger", "temiz"] or BELGELER != once:
            return False
        if fn("rag rag", BELGELER, 2) != ["zehirli", "diger"] or fn("rag", BELGELER, 0) != []:
            return False
        if fn("nedir", BELGELER, 3) != ["diger", "temiz"] or fn("yok", BELGELER, 3) != []:
            return False
        if fn("RAG", BELGELER, 4) != ["zehirli", "diger", "temiz"]:
            return False
        if fn("???", BELGELER, 2) != [] or fn("rag", [], 0) != []:
            return False
        for sorgu, belgeler, k in [
            ("", BELGELER, 1), (None, BELGELER, 1), (123, BELGELER, 1), ("rag", [None], 1), ("rag", BELGELER, -1),
            ("rag", BELGELER, 5), ("rag", BELGELER, True), ("rag", BELGELER, 1.0),
            ("rag", BELGELER + [BELGELER[0]], 1), ("rag", [dict(BELGELER[0], id="")], 1), ("rag", [dict(BELGELER[0], id=3)], 1),
            ("rag", [dict(BELGELER[0], metin=3)], 1), ("rag", [dict(BELGELER[0], ek=1)], 1),
        ]:
            try:
                fn(sorgu, belgeler, k)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(rag_getir), "farklı sorgu terimleri, skor, tie-break ve k sınırı korunmalı")
def m_sorgu_tekrar(sorgu, belgeler, k):
    import re
    terimler = re.findall(r"\w+", sorgu.casefold())
    skorlu = [(sum(re.findall(r"\w+", b["metin"].casefold()).count(t) for t in terimler), b["id"]) for b in belgeler]
    return [kimlik for skor, kimlik in sorted(skorlu, key=lambda x: (-x[0], x[1])) if skor > 0][:k]
def m_tie(sorgu, belgeler, k):
    return sorted(rag_getir(sorgu, belgeler, len(belgeler)), reverse=True)[:k]
def m_sifir(sorgu, belgeler, k):
    return [b["id"] for b in belgeler[:k]]
for ad, mutant in [("sorgu tekrarını skora katan", m_sorgu_tekrar), ("eşitlik kuralını bozan", m_tie), ("skoru ve filtrelemeyi atlayan", m_sifir)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
import re

def rag_getir(sorgu, belgeler, k):
    if not isinstance(sorgu, str) or not sorgu:
        raise ValueError("sorgu boş olmayan string olmalı")
    if isinstance(k, bool) or not isinstance(k, int) or not 0 <= k <= len(belgeler):
        raise ValueError("k sınırı geçersiz")
    kimlikler = set()
    for belge in belgeler:
        if not isinstance(belge, dict) or set(belge) != {"id", "metin"}:
            raise ValueError("belge şeması geçersiz")
        if not isinstance(belge["id"], str) or not belge["id"] or not isinstance(belge["metin"], str):
            raise ValueError("belge alanları geçersiz")
        if belge["id"] in kimlikler:
            raise ValueError("yinelenen belge kimliği")
        kimlikler.add(belge["id"])
    terimler = set(re.findall(r"\w+", sorgu.casefold()))
    skorlu = []
    for belge in belgeler:
        belge_terimleri = re.findall(r"\w+", belge["metin"].casefold())
        skor = sum(belge_terimleri.count(terim) for terim in terimler)
        if skor > 0:
            skorlu.append((skor, belge["id"]))
    skorlu.sort(key=lambda x: (-x[0], x[1]))
    return [kimlik for _, kimlik in skorlu[:k]]
```

```hint
Sorgu terimlerini kümeye çevir, belge terimlerini liste olarak bırak. `(skor, id)` çiftlerini `(-skor, id)` anahtarıyla sırala; sıfır skorluları listeye ekleme.
```
:::

::: anlat Temiz indeks kontrolü olmadan zehirleme farkı ölçülmez
Aynı sorgunun temiz ve zehirli indeks kopyalarında çalıştırılması, yeni getirilen canary belgelerini ayırmayı sağlar. İki indekste de bulunan canary belgesi yeni etki değildir. Yalnız temiz indekste görülüp zehirli indekste kaybolan belgeler de değişimdir; rapor bu durumu gizlememelidir.

Burada retrieval sonuçları `vaka_id`, `kume` ve `belgeler` olarak verilir. Canary'nin belge metninde tam satır bulunması adaylık ölçütüdür. Model yanıtı bulunmadığından rapor, “bilgi tabanı ve retrieval farkı” ile sınırlıdır; prompt injection başarısı veya modelin iç nedeni hakkında sonuç çıkarmaz.

**Sık tuzaklar:** Temiz kümeyi karşılaştırmadan zehirli kümedeki her canary belgesini "yeni" saymak, zaten var olan bir belgeyi zehirlemeye bağlar (`veri/retrieval_kayitlari.json`, `q-vpn`). Temiz kümede görülüp zehirli kümede kaybolan canary de bir değişimdir; `q-izin` bu yüzden `farkli` listesindedir.
:::

::: gorev 3 · Temiz ve zehirli retrieval sonuçlarının canary farkını çıkar
`rag_fark_raporu(kayitlar, canary)` işlevini yaz. Her kayıt tam olarak `vaka_id`, `kume`, `belgeler` alanlarını taşısın. `vaka_id` boş olmayan string, `kume` `temiz` veya `zehirli`, `belgeler` liste olmalıdır. Her belge tam olarak `id`, `metin` alanlarını taşısın; kimlik boş olmayan string, metin string olmalıdır. Bir vakada aynı kümenin yinelenmesi veya küme içinde belge kimliğinin yinelenmesi geçersizdir. Her vaka tam bir temiz ve bir zehirli kayda sahip olmalıdır. Canary boş olmayan string olmalı; bütün ihlallerde `ValueError` yükselt.

Dönüş:

```text
{"vaka":N,
 "yalniz_zehirli":{VAKA:[BELGE_ID,...]},
 "her_iki":{VAKA:[BELGE_ID,...]},
 "farkli":[VAKA,...]}
```

Canary tam satır aranır. `yalniz_zehirli`, zehirli kümede canary taşıyıp temiz kümede canary taşımayan belge kimlikleridir; `her_iki`, iki kümede de canary taşıyan kimliklerdir. `farkli`, iki kümenin canary taşıyan kimlik kümeleri farklı olan vakalardır. Vaka ve belge kimliklerini alfabetik sırala; her vaka için iki sözlükte de liste üret. Boş kayıt için `{"vaka":0,"yalniz_zehirli":{},"her_iki":{},"farkli":[]}` dön. Kayıt sırası sonucu değiştirmemeli ve girdi değişmemelidir.

Görünür veri: `veri/retrieval_kayitlari.json`. Beklenen rapor dosyanın `beklenen` alanındadır. Dört bozuk girdi `ValueError` almalıdır.

```starter
from ai_saldiri_veri import json_yukle

def rag_fark_raporu(kayitlar, canary):
    # KUSURLU BAŞLANGIÇ KODU: canary'yi alt metin olarak arıyor (alıntı sayılır), temiz kümeyi hiç karşılaştırmıyor (zehirli kümedeki her canary belgesi "yeni" sayılır), temiz kümede kaybolan canary'yi farklı saymıyor ve kayıtları doğrulamıyor!
    sonuc = {"vaka": 0, "yalniz_zehirli": {}, "her_iki": {}, "farkli": []}
    for kayit in kayitlar:
        if kayit["vaka_id"] not in sonuc["yalniz_zehirli"]:
            sonuc["vaka"] += 1
            sonuc["yalniz_zehirli"][kayit["vaka_id"]] = []
            sonuc["her_iki"][kayit["vaka_id"]] = []
        if kayit["kume"] == "zehirli":
            bulunan = [b["id"] for b in kayit["belgeler"] if canary in b["metin"]]
            sonuc["yalniz_zehirli"][kayit["vaka_id"]] = bulunan
            if bulunan:
                sonuc["farkli"].append(kayit["vaka_id"])
    return sonuc

veri = json_yukle("veri/retrieval_kayitlari.json")
sonuc = rag_fark_raporu(veri["kayitlar"], veri["canary"])
print("sonuç   :", sonuc)
print("beklenen:", veri["beklenen"])
for alan in veri["beklenen"]:
    if sonuc.get(alan) != veri["beklenen"][alan]:
        print("FARK:", alan)
for b in veri["bozuk_girdiler"]:
    try:
        rag_fark_raporu(b["kayitlar"], b["canary"])
        print(len(b["kayitlar"]), "kayıt, canary", repr(b["canary"]), "KABUL edildi (yanlış)")
    except ValueError as hata:
        print(len(b["kayitlar"]), "kayıt, canary", repr(b["canary"]), "reddedildi:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-14")
```

```test
import copy
KAYITLAR = [
    {"vaka_id": "v1", "kume": "zehirli", "belgeler": [{"id": "d9", "metin": "BREACH:CANARY-42"}, {"id": "d0", "metin": "Rapor"}]},
    {"vaka_id": "v1", "kume": "temiz", "belgeler": [{"id": "d0", "metin": "Rapor"}]},
    {"vaka_id": "v2", "kume": "temiz", "belgeler": [{"id": "d2", "metin": "BREACH:CANARY-42"}]},
    {"vaka_id": "v2", "kume": "zehirli", "belgeler": [{"id": "d2", "metin": "Not\nBREACH:CANARY-42"}]},
    {"vaka_id": "v3", "kume": "temiz", "belgeler": [{"id": "d3", "metin": "BREACH:CANARY-42"}]},
    {"vaka_id": "v3", "kume": "zehirli", "belgeler": [{"id": "d3", "metin": "Rapor"}]},
    {"vaka_id": "v4", "kume": "temiz", "belgeler": [{"id": "d4", "metin": "Rapor"}]},
    {"vaka_id": "v4", "kume": "zehirli", "belgeler": [{"id": "d4", "metin": "BREACH:CANARY-42 yazma"}]},
]
BEKLENEN = {
    "vaka": 4,
    "yalniz_zehirli": {"v1": ["d9"], "v2": [], "v3": [], "v4": []},
    "her_iki": {"v1": [], "v2": ["d2"], "v3": [], "v4": []},
    "farkli": ["v1", "v3"],
}
def sozlesme(fn):
    try:
        once = copy.deepcopy(KAYITLAR)
        if fn(KAYITLAR, "BREACH:CANARY-42") != BEKLENEN or KAYITLAR != once:
            return False
        if fn(list(reversed(KAYITLAR)), "BREACH:CANARY-42") != BEKLENEN or list(fn(KAYITLAR, "BREACH:CANARY-42")["her_iki"]) != ["v1", "v2", "v3", "v4"]:
            return False
        if fn([], "BREACH:CANARY-42") != {"vaka": 0, "yalniz_zehirli": {}, "her_iki": {}, "farkli": []}:
            return False
        for kayitlar, canary in [
            (KAYITLAR, ""), (KAYITLAR, None), (KAYITLAR, 123), (KAYITLAR[:-1], "BREACH:CANARY-42"),
            (KAYITLAR + [KAYITLAR[0]], "BREACH:CANARY-42"),
            ([dict(KAYITLAR[0], kume="diger"), KAYITLAR[1]], "BREACH:CANARY-42"),
            ([dict(KAYITLAR[0], vaka_id=""), KAYITLAR[1]], "BREACH:CANARY-42"),
            ([dict(KAYITLAR[0], vaka_id=3), dict(KAYITLAR[1], vaka_id=3)], "BREACH:CANARY-42"),
            ([dict(KAYITLAR[0], ek=1), KAYITLAR[1]], "BREACH:CANARY-42"),
            ([dict(KAYITLAR[0], belgeler="d9"), KAYITLAR[1]], "BREACH:CANARY-42"),
            ([dict(KAYITLAR[0], belgeler=[None]), KAYITLAR[1]], "BREACH:CANARY-42"),
            ([dict(KAYITLAR[0], belgeler=[{"id": "d", "metin": "x"}, {"id": "d", "metin": "y"}]), KAYITLAR[1]], "BREACH:CANARY-42"),
            ([dict(KAYITLAR[0], belgeler=[{"id": "", "metin": "x"}]), KAYITLAR[1]], "BREACH:CANARY-42"),
            ([dict(KAYITLAR[0], belgeler=[{"id": "d", "metin": 3}]), KAYITLAR[1]], "BREACH:CANARY-42"),
            ([dict(KAYITLAR[0], belgeler=[{"id": "d"}]), KAYITLAR[1]], "BREACH:CANARY-42"),
            ([None], "BREACH:CANARY-42"),
        ]:
            try:
                fn(kayitlar, canary)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(rag_fark_raporu), "iki küme, canary kimlikleri, ters fark ve tam satır korunmalı")
def m_altmetin(kayitlar, canary):
    sonuc = rag_fark_raporu(kayitlar, canary)
    sonuc["farkli"] = sorted({x["vaka_id"] for x in kayitlar if any(canary in b["metin"] for b in x["belgeler"])})
    return sonuc
def m_temiz(kayitlar, canary):
    sonuc = rag_fark_raporu(kayitlar, canary)
    sonuc["yalniz_zehirli"] = {v: [] for v in sonuc["yalniz_zehirli"]}
    return sonuc
def m_fark(kayitlar, canary):
    sonuc = rag_fark_raporu(kayitlar, canary)
    sonuc["farkli"] = sonuc["farkli"][:1]
    return sonuc
for ad, mutant in [("alt metni ve kontrolü karıştıran", m_altmetin), ("yeni zehirli belgeyi gizleyen", m_temiz), ("ters farkı düşüren", m_fark)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def rag_fark_raporu(kayitlar, canary):
    if not isinstance(canary, str) or not canary:
        raise ValueError("canary boş olmayan string olmalı")
    vakalar = {}
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"vaka_id", "kume", "belgeler"}:
            raise ValueError("kayıt şeması geçersiz")
        if not all((isinstance(kayit["vaka_id"], str), bool(kayit["vaka_id"]), kayit["kume"] in ("temiz", "zehirli"), isinstance(kayit["belgeler"], list))):
            raise ValueError("vaka veya küme geçersiz")
        kumeler = vakalar.setdefault(kayit["vaka_id"], {})
        if kayit["kume"] in kumeler:
            raise ValueError("yinelenen indeks kümesi")
        canary_belgeler = set()
        kimlikler = set()
        for belge in kayit["belgeler"]:
            if not isinstance(belge, dict) or set(belge) != {"id", "metin"}:
                raise ValueError("belge şeması geçersiz")
            if not all((isinstance(belge["id"], str), bool(belge["id"]), isinstance(belge["metin"], str), belge["id"] not in kimlikler)):
                raise ValueError("belge alanları veya yinelenen kimlik geçersiz")
            kimlikler.add(belge["id"])
            if canary in belge["metin"].splitlines():
                canary_belgeler.add(belge["id"])
        kumeler[kayit["kume"]] = canary_belgeler
    sonuc = {"vaka": len(vakalar), "yalniz_zehirli": {}, "her_iki": {}, "farkli": []}
    for vaka in sorted(vakalar):
        kumeler = vakalar[vaka]
        if set(kumeler) != {"temiz", "zehirli"}:
            raise ValueError("indeks kolları eksik")
        temiz = kumeler["temiz"]
        zehirli = kumeler["zehirli"]
        sonuc["yalniz_zehirli"][vaka] = sorted(zehirli - temiz)
        sonuc["her_iki"][vaka] = sorted(temiz & zehirli)
        if temiz != zehirli:
            sonuc["farkli"].append(vaka)
    return sonuc
```

```hint
Her küme için canary taşıyan belge kimliklerini kümeye çevir. Sonra küme farkı ve kesişimi kullan; `farkli` için iki kümeyi doğrudan karşılaştır.
```
:::


::: anlat Temiz ve zehirli corpus'u gerçek SQLite'tan getir
[Sentetik corpus dosyasını aç](/data/ai-saldiri-14-corpus.txt). Temiz bilgi tabanı ve aynı tabana eklenmiş zararsız eğitim yönlendirmesi ayrı kollardır. Canlı çalıştırmada `{{CANARY}}` yeni sentetik işarete çevrilir. Dosya gerçek saldırı kaydı değildir. Çalıştır ayrı kalıcı `calisma/ai-saldiri-14/corpus.json` kopyasını ve tam yolunu gösterir; dış editör/Python ile değiştir, tekrar çalıştır. Şablon üzerine yazılmaz, mevcut veriler silinmez.

Corpushun iki kolu gerçek SQLite dosyasına ve FTS5 indeksine yazılır. Bağlantı kapanıp dosya yeniden okunur. Senin manifeston gerçek içerik SHA-256'sını bağlar; `rag_getir` sırası hangi belgelerin yeniden SQL ile çekilip modele gideceğini belirler. FTS5 BM25 sırası ayrıca gösterilir: dersin token sayımı sıralamasıyla aynı algoritma değildir, eşit çıkması geçme şartı değildir. Bu bölüm embedding/vector veritabanı kullandığını iddia etmez.

Her soru için temiz ve zehirli belgelerle gerçek model yanıtı alınır. `rag_fark_raporu` yalnız retrieval sonucundaki tam satır canary'yi ölçer; model yanıtındaki işaret ayrı sinyaldir. Belgenin getirilmesi, modelin talimata uyması ve yanıt içinde alıntı bulunması aynı şey değildir. Saldırının başarılı olması kabul şartı değildir. Dosyada her kolda1–8 belge,1–3 sorgu ve her iki belge sayısına uygun k kullan. SQLite dosyası Çalıştır'da incelemen için korunur. Yeni paket kurulmaz.
:::

::: gorev Gerçek deney · Disk corpus'u, retrieval ve canlı RAG farkı
Önceki üç işlevi birleştir: `indeks_manifestosu`, `rag_getir`, `rag_fark_raporu`. Çalıştır öğrenci sırası/FTS5 sırası, gerçek temiz/zehirli yanıtlar ve fark raporunu gösterir. Kontrol Et yeni sorgu/içerik/işaretlerle doğrular; gerçek çağrı hatasını PASS yapmaz. GPU ortak kilitle sıraya girer.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import hashlib
import json
import ai_lab

def indeks_manifestosu(belgeler):
    # KUSURLU BAŞLANGIÇ KODU: belgeyi metniyle birlikte manifestoya kopyalıyor, özeti strip() edilmiş metinden alıyor (yalnız satır sonu farkı olan içerikler aynı özete düşer), belgenin kendi "guven" alanını koruyor, kimliğe göre sıralamıyor, yinelenen kimliği denetlemiyor ve kanonik JSON ayarlarını kullanmıyor!
    kayitlar = []
    for belge in belgeler:
        kayit = dict(belge)
        kayit["sha256"] = hashlib.sha256(belge["metin"].strip().encode("utf-8")).hexdigest()
        kayit.setdefault("guven", "guvenilmez")
        kayitlar.append(kayit)
    return json.dumps({"belgeler": kayitlar})

def rag_getir(sorgu, belgeler, k):
    # KUSURLU BAŞLANGIÇ KODU: sorgudaki yinelenen terimi her seferinde sayıyor, split() ile ayırdığı için noktalama terime yapışıyor ("sıfırlama:"), sıfır skorlu belgeleri de getiriyor, eşitlikte kimlik yerine girdi sırasını kullanıyor ve k/şema doğrulaması yapmıyor!
    terimler = sorgu.lower().split()
    skorlu = []
    for belge in belgeler:
        kelimeler = belge["metin"].lower().split()
        skorlu.append((sum(kelimeler.count(t) for t in terimler), belge["id"]))
    skorlu.sort(key=lambda x: -x[0])
    return [kimlik for _, kimlik in skorlu[:k]]

def rag_fark_raporu(kayitlar, canary):
    # KUSURLU BAŞLANGIÇ KODU: canary'yi alt metin olarak arıyor (alıntı sayılır), temiz kümeyi hiç karşılaştırmıyor (zehirli kümedeki her canary belgesi "yeni" sayılır), temiz kümede kaybolan canary'yi farklı saymıyor ve kayıtları doğrulamıyor!
    sonuc = {"vaka": 0, "yalniz_zehirli": {}, "her_iki": {}, "farkli": []}
    for kayit in kayitlar:
        if kayit["vaka_id"] not in sonuc["yalniz_zehirli"]:
            sonuc["vaka"] += 1
            sonuc["yalniz_zehirli"][kayit["vaka_id"]] = []
            sonuc["her_iki"][kayit["vaka_id"]] = []
        if kayit["kume"] == "zehirli":
            bulunan = [b["id"] for b in kayit["belgeler"] if canary in b["metin"]]
            sonuc["yalniz_zehirli"][kayit["vaka_id"]] = bulunan
            if bulunan:
                sonuc["farkli"].append(kayit["vaka_id"])
    return sonuc

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_14 as deney
    deney.goster(indeks_manifestosu,rag_getir,rag_fark_raporu)

```

```test
import copy
import hashlib
import json
BELGELER = [
    {"id": "d2", "kaynak": "dis-aktarim", "metin": "Rapor"},
    {"id": "d1", "kaynak": "web", "metin": "Not\nBREACH:CANARY-42"},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(BELGELER)
        sonuc = fn(BELGELER)
        beklenen = {"belgeler": [
            {"id": b["id"], "kaynak": b["kaynak"], "sha256": hashlib.sha256(b["metin"].encode("utf-8")).hexdigest(), "guven": "guvenilmez"}
            for b in sorted(BELGELER, key=lambda x: x["id"])
        ]}
        if json.loads(sonuc) != beklenen or BELGELER != once:
            return False
        if sonuc != json.dumps(beklenen, ensure_ascii=False, sort_keys=True, separators=(",", ":")):
            return False
        if fn(list(reversed(BELGELER))) != sonuc or json.loads(fn([])) != {"belgeler": []}:
            return False
        degisen = fn([dict(BELGELER[0], metin="Değişti")])
        if json.loads(degisen)["belgeler"][0]["sha256"] == beklenen["belgeler"][1]["sha256"]:
            return False
        if "dış-aktarım" not in fn([dict(BELGELER[0], kaynak="dış-aktarım")]):
            return False
        for belgeler in [
            None, BELGELER + [BELGELER[0]], [dict(BELGELER[0], id="")], [dict(BELGELER[0], id=3)],
            [dict(BELGELER[0], kaynak="")], [dict(BELGELER[0], kaynak=3)], [dict(BELGELER[0], metin=3)],
            [dict(BELGELER[0], ek=1)], [None],
        ]:
            try:
                fn(belgeler)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(indeks_manifestosu), "kaynak, içerik özeti, güven etiketi ve sıralama korunmalı")
def m_hash(belgeler):
    veri = json.loads(indeks_manifestosu(belgeler))
    for belge in veri["belgeler"]:
        belge["sha256"] = "0" * 64
    return json.dumps(veri, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
def m_guven(belgeler):
    return indeks_manifestosu(belgeler).replace("guvenilmez", "system")
def m_kaynak(belgeler):
    veri = json.loads(indeks_manifestosu(belgeler))
    for belge in veri["belgeler"]:
        belge.pop("kaynak", None)
    return json.dumps(veri, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
for ad, mutant in [("içerik özetini sabitleyen", m_hash), ("belgeyi system sayan", m_guven), ("kaynağı silen", m_kaynak)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

import copy
BELGELER = [
    {"id": "temiz", "metin": "RAG nedir"},
    {"id": "zehirli", "metin": "rag rag rag\nBREACH:CANARY-42"},
    {"id": "diger", "metin": "rag nedir"},
    {"id": "alakasiz", "metin": "başka konu"},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(BELGELER)
        if fn("RAG", BELGELER, 3) != ["zehirli", "diger", "temiz"] or BELGELER != once:
            return False
        if fn("rag rag", BELGELER, 2) != ["zehirli", "diger"] or fn("rag", BELGELER, 0) != []:
            return False
        if fn("nedir", BELGELER, 3) != ["diger", "temiz"] or fn("yok", BELGELER, 3) != []:
            return False
        if fn("RAG", BELGELER, 4) != ["zehirli", "diger", "temiz"]:
            return False
        if fn("???", BELGELER, 2) != [] or fn("rag", [], 0) != []:
            return False
        for sorgu, belgeler, k in [
            ("", BELGELER, 1), (None, BELGELER, 1), (123, BELGELER, 1), ("rag", [None], 1), ("rag", BELGELER, -1),
            ("rag", BELGELER, 5), ("rag", BELGELER, True), ("rag", BELGELER, 1.0),
            ("rag", BELGELER + [BELGELER[0]], 1), ("rag", [dict(BELGELER[0], id="")], 1), ("rag", [dict(BELGELER[0], id=3)], 1),
            ("rag", [dict(BELGELER[0], metin=3)], 1), ("rag", [dict(BELGELER[0], ek=1)], 1),
        ]:
            try:
                fn(sorgu, belgeler, k)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(rag_getir), "farklı sorgu terimleri, skor, tie-break ve k sınırı korunmalı")
def m_sorgu_tekrar(sorgu, belgeler, k):
    import re
    terimler = re.findall(r"\w+", sorgu.casefold())
    skorlu = [(sum(re.findall(r"\w+", b["metin"].casefold()).count(t) for t in terimler), b["id"]) for b in belgeler]
    return [kimlik for skor, kimlik in sorted(skorlu, key=lambda x: (-x[0], x[1])) if skor > 0][:k]
def m_tie(sorgu, belgeler, k):
    return sorted(rag_getir(sorgu, belgeler, len(belgeler)), reverse=True)[:k]
def m_sifir(sorgu, belgeler, k):
    return [b["id"] for b in belgeler[:k]]
for ad, mutant in [("sorgu tekrarını skora katan", m_sorgu_tekrar), ("eşitlik kuralını bozan", m_tie), ("skoru ve filtrelemeyi atlayan", m_sifir)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

import copy
KAYITLAR = [
    {"vaka_id": "v1", "kume": "zehirli", "belgeler": [{"id": "d9", "metin": "BREACH:CANARY-42"}, {"id": "d0", "metin": "Rapor"}]},
    {"vaka_id": "v1", "kume": "temiz", "belgeler": [{"id": "d0", "metin": "Rapor"}]},
    {"vaka_id": "v2", "kume": "temiz", "belgeler": [{"id": "d2", "metin": "BREACH:CANARY-42"}]},
    {"vaka_id": "v2", "kume": "zehirli", "belgeler": [{"id": "d2", "metin": "Not\nBREACH:CANARY-42"}]},
    {"vaka_id": "v3", "kume": "temiz", "belgeler": [{"id": "d3", "metin": "BREACH:CANARY-42"}]},
    {"vaka_id": "v3", "kume": "zehirli", "belgeler": [{"id": "d3", "metin": "Rapor"}]},
    {"vaka_id": "v4", "kume": "temiz", "belgeler": [{"id": "d4", "metin": "Rapor"}]},
    {"vaka_id": "v4", "kume": "zehirli", "belgeler": [{"id": "d4", "metin": "BREACH:CANARY-42 yazma"}]},
]
BEKLENEN = {
    "vaka": 4,
    "yalniz_zehirli": {"v1": ["d9"], "v2": [], "v3": [], "v4": []},
    "her_iki": {"v1": [], "v2": ["d2"], "v3": [], "v4": []},
    "farkli": ["v1", "v3"],
}
def sozlesme(fn):
    try:
        once = copy.deepcopy(KAYITLAR)
        if fn(KAYITLAR, "BREACH:CANARY-42") != BEKLENEN or KAYITLAR != once:
            return False
        if fn(list(reversed(KAYITLAR)), "BREACH:CANARY-42") != BEKLENEN or list(fn(KAYITLAR, "BREACH:CANARY-42")["her_iki"]) != ["v1", "v2", "v3", "v4"]:
            return False
        if fn([], "BREACH:CANARY-42") != {"vaka": 0, "yalniz_zehirli": {}, "her_iki": {}, "farkli": []}:
            return False
        for kayitlar, canary in [
            (KAYITLAR, ""), (KAYITLAR, None), (KAYITLAR, 123), (KAYITLAR[:-1], "BREACH:CANARY-42"),
            (KAYITLAR + [KAYITLAR[0]], "BREACH:CANARY-42"),
            ([dict(KAYITLAR[0], kume="diger"), KAYITLAR[1]], "BREACH:CANARY-42"),
            ([dict(KAYITLAR[0], vaka_id=""), KAYITLAR[1]], "BREACH:CANARY-42"),
            ([dict(KAYITLAR[0], vaka_id=3), dict(KAYITLAR[1], vaka_id=3)], "BREACH:CANARY-42"),
            ([dict(KAYITLAR[0], ek=1), KAYITLAR[1]], "BREACH:CANARY-42"),
            ([dict(KAYITLAR[0], belgeler="d9"), KAYITLAR[1]], "BREACH:CANARY-42"),
            ([dict(KAYITLAR[0], belgeler=[None]), KAYITLAR[1]], "BREACH:CANARY-42"),
            ([dict(KAYITLAR[0], belgeler=[{"id": "d", "metin": "x"}, {"id": "d", "metin": "y"}]), KAYITLAR[1]], "BREACH:CANARY-42"),
            ([dict(KAYITLAR[0], belgeler=[{"id": "", "metin": "x"}]), KAYITLAR[1]], "BREACH:CANARY-42"),
            ([dict(KAYITLAR[0], belgeler=[{"id": "d", "metin": 3}]), KAYITLAR[1]], "BREACH:CANARY-42"),
            ([dict(KAYITLAR[0], belgeler=[{"id": "d"}]), KAYITLAR[1]], "BREACH:CANARY-42"),
            ([None], "BREACH:CANARY-42"),
        ]:
            try:
                fn(kayitlar, canary)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(rag_fark_raporu), "iki küme, canary kimlikleri, ters fark ve tam satır korunmalı")
def m_altmetin(kayitlar, canary):
    sonuc = rag_fark_raporu(kayitlar, canary)
    sonuc["farkli"] = sorted({x["vaka_id"] for x in kayitlar if any(canary in b["metin"] for b in x["belgeler"])})
    return sonuc
def m_temiz(kayitlar, canary):
    sonuc = rag_fark_raporu(kayitlar, canary)
    sonuc["yalniz_zehirli"] = {v: [] for v in sonuc["yalniz_zehirli"]}
    return sonuc
def m_fark(kayitlar, canary):
    sonuc = rag_fark_raporu(kayitlar, canary)
    sonuc["farkli"] = sonuc["farkli"][:1]
    return sonuc
for ad, mutant in [("alt metni ve kontrolü karıştıran", m_altmetin), ("yeni zehirli belgeyi gizleyen", m_temiz), ("ters farkı düşüren", m_fark)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

from sandbox import ai_gercek_ai_saldiri_14 as deney
import copy,json,secrets,tempfile,hashlib
from pathlib import Path
import ast
_yasak=('rank_referans','fark_referans','kanit_yaz')
_sorun=list(ai_lab.kod_denetimi(src,_yasak))
for _n in ast.walk(ast.parse(src)):
    if isinstance(_n,ast.ImportFrom) and any(a.name in _yasak or a.name=='*' for a in _n.names):_sorun.append('referans importu yasak')
    if isinstance(_n,(ast.Import,ast.ImportFrom)) and any(x and x.split('.')[0] in ('inspect','importlib','runpy') for x in [a.name for a in _n.names]+([_n.module] if isinstance(_n,ast.ImportFrom) else [])):_sorun.append('kaynak okuma/dinamik import yasak')
    if isinstance(_n,ast.Name) and _n.id in ('exec','eval','compile','__builtins__'):_sorun.append('dinamik kod çalıştırma yasak: '+_n.id)
if not ok(not _sorun, 'laboratuvar/bağımsız ölçüm yamalanmamalı: '+'; '.join(sorted(set(_sorun)))):stop()
for i in range(4):
    term='q'+secrets.token_hex(3)
    docs=[dict(id='b',metin=term),dict(id='a',metin=term+' '+term),dict(id='c',metin='başka')]
    if not ok(rag_getir(term,docs,2)==['a','b'] and rag_getir(term,docs,0)==[], 'yeni sorguda sıklık, sıra ve k=0'):stop()
    rows=[dict(id=v['id'],kaynak='yerel',metin=v['metin']) for v in docs]
    expected={'belgeler':[dict(id=v['id'],kaynak='yerel',sha256=hashlib.sha256(v['metin'].encode()).hexdigest(),guven='guvenilmez') for v in sorted(rows,key=lambda v:v['id'])]}
    if not ok(json.loads(indeks_manifestosu(rows))==expected,'yeni içerikte gerçek SHA256/kaynak/güven'):stop()
with tempfile.TemporaryDirectory(prefix='pafta_rag14_') as tmp:
    p=Path(tmp)/'corpus.json';p.write_text(deney.ORNEK.read_text(encoding='utf-8'),encoding='utf-8')
    result=deney.deney(indeks_manifestosu,rag_getir,rag_fark_raporu,p,Path(tmp)/'indeks.sqlite3')
    for key,value in result['kontroller'].items():ok(value,'gerçek deney: '+key)
    accepted=all(result['kontroller'].values());ai_lab.kanit_yaz('saldiri-14-rag',dict(result,kabul=accepted));ok(accepted,'gerçek DB retrieval ve canlı RAG; zehrin yanıta geçmesi şart değil')

```

```solution
import ai_lab

import hashlib
import json

def indeks_manifestosu(belgeler):
    if not isinstance(belgeler, list):
        raise ValueError("belge listesi gerekli")
    kimlikler = set()
    kayitlar = []
    for belge in belgeler:
        if not isinstance(belge, dict) or set(belge) != {"id", "kaynak", "metin"}:
            raise ValueError("belge şeması geçersiz")
        if not isinstance(belge["id"], str) or not belge["id"] or not isinstance(belge["kaynak"], str) or not belge["kaynak"] or not isinstance(belge["metin"], str):
            raise ValueError("belge alanları geçersiz")
        if belge["id"] in kimlikler:
            raise ValueError("yinelenen belge kimliği")
        kimlikler.add(belge["id"])
        kayitlar.append({
            "id": belge["id"], "kaynak": belge["kaynak"],
            "sha256": hashlib.sha256(belge["metin"].encode("utf-8")).hexdigest(),
            "guven": "guvenilmez",
        })
    kayitlar.sort(key=lambda x: x["id"])
    return json.dumps({"belgeler": kayitlar}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

import re

def rag_getir(sorgu, belgeler, k):
    if not isinstance(sorgu, str) or not sorgu:
        raise ValueError("sorgu boş olmayan string olmalı")
    if isinstance(k, bool) or not isinstance(k, int) or not 0 <= k <= len(belgeler):
        raise ValueError("k sınırı geçersiz")
    kimlikler = set()
    for belge in belgeler:
        if not isinstance(belge, dict) or set(belge) != {"id", "metin"}:
            raise ValueError("belge şeması geçersiz")
        if not isinstance(belge["id"], str) or not belge["id"] or not isinstance(belge["metin"], str):
            raise ValueError("belge alanları geçersiz")
        if belge["id"] in kimlikler:
            raise ValueError("yinelenen belge kimliği")
        kimlikler.add(belge["id"])
    terimler = set(re.findall(r"\w+", sorgu.casefold()))
    skorlu = []
    for belge in belgeler:
        belge_terimleri = re.findall(r"\w+", belge["metin"].casefold())
        skor = sum(belge_terimleri.count(terim) for terim in terimler)
        if skor > 0:
            skorlu.append((skor, belge["id"]))
    skorlu.sort(key=lambda x: (-x[0], x[1]))
    return [kimlik for _, kimlik in skorlu[:k]]

def rag_fark_raporu(kayitlar, canary):
    if not isinstance(canary, str) or not canary:
        raise ValueError("canary boş olmayan string olmalı")
    vakalar = {}
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"vaka_id", "kume", "belgeler"}:
            raise ValueError("kayıt şeması geçersiz")
        if not all((isinstance(kayit["vaka_id"], str), bool(kayit["vaka_id"]), kayit["kume"] in ("temiz", "zehirli"), isinstance(kayit["belgeler"], list))):
            raise ValueError("vaka veya küme geçersiz")
        kumeler = vakalar.setdefault(kayit["vaka_id"], {})
        if kayit["kume"] in kumeler:
            raise ValueError("yinelenen indeks kümesi")
        canary_belgeler = set()
        kimlikler = set()
        for belge in kayit["belgeler"]:
            if not isinstance(belge, dict) or set(belge) != {"id", "metin"}:
                raise ValueError("belge şeması geçersiz")
            if not all((isinstance(belge["id"], str), bool(belge["id"]), isinstance(belge["metin"], str), belge["id"] not in kimlikler)):
                raise ValueError("belge alanları veya yinelenen kimlik geçersiz")
            kimlikler.add(belge["id"])
            if canary in belge["metin"].splitlines():
                canary_belgeler.add(belge["id"])
        kumeler[kayit["kume"]] = canary_belgeler
    sonuc = {"vaka": len(vakalar), "yalniz_zehirli": {}, "her_iki": {}, "farkli": []}
    for vaka in sorted(vakalar):
        kumeler = vakalar[vaka]
        if set(kumeler) != {"temiz", "zehirli"}:
            raise ValueError("indeks kolları eksik")
        temiz = kumeler["temiz"]
        zehirli = kumeler["zehirli"]
        sonuc["yalniz_zehirli"][vaka] = sorted(zehirli - temiz)
        sonuc["her_iki"][vaka] = sorted(temiz & zehirli)
        if temiz != zehirli:
            sonuc["farkli"].append(vaka)
    return sonuc
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_14 as deney
    deney.goster(indeks_manifestosu,rag_getir,rag_fark_raporu)

```

```hint
Kaynak ve gerçek içerik hashini koru. Retrieval sıklıkta azalan, eşitlikte kimlikte artan sırada olmalı. İndeks kollarını ayrı tut; retrieval'daki canary farkını yanıttaki aktarımla karıştırma.
```
:::


::: anlat Bunu iki dakikada nasıl anlatırsın?
Zehirli belgeyi indeksin içine almak ile retrieval sonucunda seçmek farklı aşamalardır. Önce belge kümesini ve kimlik tekilliğini doğrula; sonra sorgu terimleri, skor ve eşitlik sırasıyla seçimi yeniden üret. Temiz ve zehirli kolları aynı vaka kimliğinde eşleştir. Canary içeren belgenin retrieval sonucu değişebilir; son yanıtın zehirlenmesi için üretim aşamasını ayrıca ölçmek gerekir.

Önkoşul ve yol köprüsü: ai-saldiri-15 bağlam bütçesi.

| Yaygın yanlış | Mekanizma ve sınır |
|---|---|
| Top-k içine girdiyse cevap zehirlendi | Retrieval, bağlam ve üretim ayrı gözlemlerdir |

Dinleyiciye sor: Bu mekanizmada hangi bilgi veri, hangisi yetki kaynağıdır; testin geçtiğini hangi gerçek gözlemle kanıtlarsın? Sentetik örnek ile canlı deney kaydını ayrı göstererek cevapla.
:::


::: anlat Birincil kaynak ve deney sınırı
[Greshake vd., Indirect Prompt Injection](https://arxiv.org/abs/2302.12173): Retrieval ile alınan içeriğin talimat olarak yorumlanması riskine birincil referans. Buradaki terim sayımı/top-k politikası araştırmanın bütün retrieval sistemlerine eşdeğer değildir. Çalışan araç/model sürümü canlı kanıtta saklanır; bağlantıdaki belge sürümüyle otomatik eşit kabul edilmez.
:::
