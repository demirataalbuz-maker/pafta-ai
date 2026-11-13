---
id: ai-temel-22
title: "Retrieval Kalitesi ve Bağlam Seçimi"
summary: Parça sıralamasını belge düzeyine indirip retrieval ölçütlerini sorgu bazında hesapla, lexical ve dense sıralamaları RRF ile birleştir ve MMR ile çeşitli kanıtı bağlamın kenarlarına diz; son adımda gerçek gömmelerde k seçiminin retrieval kalitesine etkisini ölç.
esleme: ai-temel-21, ai-temel-24, ai-guvence-10
timeout: 45
---

::: anlat Modele hangi kanıtın ulaşacağını retrieval kalitesi belirler

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Retrieval değerlendiricisi etiketli sıralamanın kalitesini ölçer | İlk 3 görev görünür sentetik parça/derece, RRF listeleri ve MMR tablosu | FAISS, BM25 veya cross-encoder'ın gerçekten çalıştığı anlamına gelmez |
| Yerel embedding modeli metni gerçek vektörlere dönüştürür | Final Ollama `all-minilm:22m` ile 10 parça + 6 soru; kosinüs arama, k1/k3 karşılaştırması | Üretim RAG başarısı, zehirlenme savunması veya Türkçe için genel model kalitesi kanıtı değildir |

> [!NOT]
> `veri/retrieval.json` elle yazılmış sentetik sıralama ve puan örneğidir; model çıktısı değildir. İlk 3 görev aynı dosyayı okur. Setup her Run/Check için geçici kopya hazırlar; kalıcılık yoktur. Kaynağı editörde aç veya kodda yüklenen kopyayı değiştirip Run dene. Gizli testler ayrı. Final kurulu gömme modelini gerçekten çağırır; yeni indirme yoktur.

RAG hattında model yalnız retriever'ın ilk k sonucunu görür; doğru belge k'nın dışında kalırsa model kanıtsız yanıt üretir, içeride ilgisiz ya da saldırganın yerleştirdiği bir parça varsa onu kanıt sanar. Bu yüzden retrieval, etiketli bir değerlendirme kümesiyle (sorgu → ilgili belge kimlikleri ve ilgililik dereceleri) ölçülür. recall@k ilgili belgelerin ne kadarının ilk k'ya girdiğini, precision@k ilk k'nın ne kadarının ilgili olduğunu, reciprocal rank (RR) ilk ilgili belgenin 1/sıra değerini verir; RR'nin sorgular üzerindeki ortalaması MRR'dir. Dereceli ilgililikte nDCG@k kullanılır: DCG@k = Σ rel_i / log2(i + 1) (i sıra numarasıdır, 1'den başlar), IDCG@k aynı toplamın dereceler büyükten küçüğe dizilmiş ideal sıralamadaki değeridir ve nDCG@k = DCG@k / IDCG@k. Literatürde kazanç için 2^rel − 1 biçimi de yaygındır; iki sürümün sayıları karşılaştırılamaz, raporda hangisinin kullanıldığı yazılmalıdır.

Chunking ve embedding kararları bu sayıları doğrudan değiştirir. Büyük parçada kanıt cümlesi konu dışı cümlelerle tek vektöre ortalanır (Sentence Transformers modellerinin çoğu mean pooling kullanır) ve sorguya benzerliği düşer; küçük parça ise koşul ya da istisna cümlesini komşu parçada bırakıp yanıltıcı kanıt üretebilir. Model ayrıca `max_seq_length` sınırını aşan metni sessizce keser (örneğin `all-MiniLM-L6-v2` varsayılan olarak 256 word piece'ten sonrasını almaz), yani parçanın sonundaki kanıt embedding'e hiç girmez. FAISS'te `IndexFlatIP` kesin iç çarpım araması yapar ve kosinüs için vektörler önce `faiss.normalize_L2` ile normalize edilir; `IndexHNSWFlat` (`hnsw.efSearch`) ve `IndexIVFFlat` (`nprobe`) gibi yaklaşık indeksler hız için recall'dan feragat eder, bu kayıp da Flat sonuçlarına göre recall@k ile ölçülür. Parça düzeyindeki indeks aynı belgenin birden çok parçasını döndürebildiğinden belge düzeyinde ölçerken her belge ilk parçasının sırasında bir kez sayılır; aksi hâlde aynı kanıtın kopyaları ilk k'yı doldurup recall ve precision'ı şişirir. Görevler 1–3 sentetik sıralama, derece ve benzerlik dosyalarında çalışır. Final kurulu all-minilm:22m embedding modelini gerçek Ollama API üzerinden çağırır. FAISS ve cross-encoder bu derste çalıştırılmaz.
:::

::: anlat Füzyon, yeniden sıralama ve çeşitlilik bağlama gireni seçer

Önce retrieval.json içindeki üç bölümü incele. olcutler bölümünde aynı belgenin iki parçası sıralamada bulunur; bunları iki ayrı ilgili belge saymamalısın. rrf bölümünde lexical ve dense diye etiketlenmiş listeler vardır ama puanlar gerçek arama motorundan alınmamıştır. mmr bölümü sorgu benzerliklerini ve simetrik belge benzerliklerini taşır. İlk görev ölçer, ikinci iki sıralamayı birleştirir, üçüncü çeşitlilik ve bağlam sırası seçer. Bu dosyayı kurcalayarak aynı belgenin yeni bir parçasını eklemenin belge düzeyindeki recall'u neden değiştirmediğini gözleyebilirsin.

Metriklerin paydası ve hangi düzeyde ölçüldüğü açık olmalıdır. İlk görev belge düzeyinde ve dereceli ilgililikte çalışır; aynı belgenin sonraki parçaları k kesmesinden önce atılır. Precision paydası liste kısa olsa da k'dır. RR yalnız ilk k içindedir; sorguların RR ortalaması MRR olur. Gerçek final ise tek sorguda parça kimliklerini kullanır ve MRR'yi bütün sıralamada arar. Finalin nDCG'si ikili, ilk görevin nDCG'si 1–3 dereceli doğrusal kazançtır. İkisini aynı ölçüm sanarak yan yana sonuç kıyaslama. Makro ortalama önce hesaplanır, sonra yuvarlanır; her sorguyu önce yuvarlamak küçük ama sistematik hata üretir.

RRF listelerin özgün puanını kullanmaz. İki listede de iyi sırada olan belge tek listede birinci olanı geçebilir; bu kaynak güvenliği kontrolü değildir. Altı ondalıkta puan eşitliği ve alfabetik kimlik sırası bu görevde belirlenimlilik sağlar. MMR seçimi de sonraki bağlam sıralamasıyla aynı liste değildir. Önce ilgililik/çeşitlilik puanıyla seçim yapılır, sonra seçilenler kenarlara dizilir. λ yüz olduğunda çeşitlilik cezası kalkar, λ sıfır olduğunda ilk seçimde bütün MMR puanları eşitlenir ve sözleşmedeki ek eşitlik kuralı önem kazanır. Bağlamın kenarına dizmenin bu görevde hesaplanması, yanıt kalitesinin gerçekten arttığını göstermez; burada üretici model karşılaştırması yapılmaz.

Finalde gerçek embedding modeli iki toplu istekte metinleri işler. Parçalar ve sorular aynı model ve boyut uzayında olmalıdır. API'nin beklenen sayıda vektör döndürdüğü, tüm değerlerin sonlu olduğu ve vektörlerin sıfır olmadığı denetlenir; eksik toplu yanıt zip ile sessizce kısaltılıp kabul edilmez. Kosinüs, vektör uzunluğunu değil yönünü karşılaştırır. Çok büyük veya çok küçük sayılarda doğrudan kareleri toplamak taşabilir veya sıfıra yuvarlanabilir. Ölçekleyerek normalleştirmek bu sayısal sorunu giderir. Eşit skorda küçük giriş indeksi önce gelir; alfabetik kimlik sırasını burada kullanma.

Etiketli derlem küçük ve sentetiktir. all-minilm embedding vektörleri kullanmak veriyi gerçek yapmaz; gerçek olan metinden vektör üreten model hesabıdır. `k` birden üçe çıkarıldığında altın parçanın ilk kümede bulunma oranı düşmemelidir; bu iç içe `top-k` kümelerinin özelliğidir. Kesinlikle artması istenmez, aynı da kalabilir. Daha fazla parça bağlama daha fazla gereksiz veya güvensiz metin de taşıyabilir; bu ders kaynak yetkisi veya prompt enjeksiyon savunması sınamaz. Ortalama recall tek başına her sorgunun başarılı olduğunu söylemez; kanıtta her sorunun altın kimliği, sıralaması ve k1/k3 metriklerini oku.

Kanıt, derlemin tam metnini, iki API çağrısını, model özeti/digestini, ham vektörleri ve sonuçları saklar. Yeniden dosyadan okunması yeni model çağrısı sayılmaz. Çalıştır sonuçları inceletir ve `kabul=False` kanıtı üretir; görevin kabulü Check ile ayrıca verilir. Eksik model veya bozuk toplu yanıt geçme değildir. Yalnız deneyin yüklediği embedding modeli boşaltılır; önceden yüklü model korunur.

Kaynak: [Ollama embed API](https://docs.ollama.com/api/embed). API metin veya metin listesi alır; dersin etiketleri ve metrik sözleşmesi bu API'nin garantisi değildir.

Lexical arama (örneğin BM25) hata kodu, CVE kimliği veya ürün adı gibi tam terimlerde, dense arama ise eşanlamlı ve yeniden ifade edilmiş sorularda güçlüdür; iki puan ölçeği doğrudan karşılaştırılamadığından hibrit sistemler ya puanları normalize edip ağırlıklı toplar (convex combination) ya da yalnız sıraları birleştirir; RRF ikinci yoldur ve ayar ya da etiketli veri gerektirmediği için yaygın bir varsayılandır. Reciprocal Rank Fusion (Cormack, Clarke ve Büttcher, SIGIR 2009) bir belgeye geçtiği her listede 1/(k + sıra) ekler; sıra 1'den başlar ve makalede k = 60 alınır. Bu yapı tek bir listeyi ele geçirmenin etkisini sınırlar: anahtar kelimeyle doldurulmuş zehirli belge BM25'te birinci olsa bile 1/61 alır, iki listede de ikinci olan belge 2/62 ile onu geçer. Füzyondan sonra bir cross-encoder sorgu ile pasajı birlikte kodlayarak daha isabetli ilgililik puanı üretir (Sentence Transformers'ta `CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2").predict([(sorgu, pasaj), ...])`); her çift için tam model çalıştığından yalnız ilk birkaç düzine adaya uygulanır. Bu derste cross-encoder çalıştırılmaz, yalnız füzyon hesaplanır.

Yakın kopyalar ilk k'yı doldurursa bağlam bütçesi tek kaynağa harcanır ve aynı içeriği çoğaltan saldırgan modele tek sesli bir kanıt seti sunar. Maximal Marginal Relevance (Carbonell ve Goldstein, SIGIR 1998) her adımda λ·sim(d, q) − (1 − λ)·max_{s∈S} sim(d, s) değerini en büyük yapan belgeyi seçilmişler kümesi S'ye ekler; λ = 1 saf ilgililik, küçük λ daha fazla çeşitlilik demektir. MMR güven kararı vermez, farklı ama zehirli bir kaynağı da seçebilir; kaynak politikası ayrı bir katmandır. Seçilen kanıtın bağlamdaki yeri de önemlidir: "Lost in the Middle" (Liu ve diğ., 2023) uzun bağlamda ilgili bilgi başta veya sondayken başarının en yüksek, ortadayken belirgin biçimde düşük olduğunu gösterdi. Görev 3 bu nedenle MMR'nin önce seçtiği kanıtları kenarlara yerleştirir; benzerlikler tamsayı yüzde ölçeğinde verildiğinden eşitlik kırma float gürültüsü olmadan belirlenimlidir.
:::

::: tahmin Parça boyutunun benzerliğe etkisini tahmin et
Üç çıktı satırını yaz:

```python
import math
def cos(a, b):
    return sum(x * y for x, y in zip(a, b)) / (math.hypot(*a) * math.hypot(*b))
q = [1.0, 0.0]
kanit, dolgu, komsu = [1.0, 0.0], [0.0, 1.0], [0.6, 0.8]
buyuk = [(kanit[i] + 2 * dolgu[i]) / 3 for i in range(2)]
print(round(cos(q, kanit), 3))
print(round(cos(q, buyuk), 3))
print(cos(q, komsu) > cos(q, buyuk))
```

???

```cikti
1.0
0.447
True
```

İlk satır yalnız kanıt cümlesini taşıyan küçük parçanın sorguyla tam hizalandığını gösterir. İkinci satırda aynı kanıt iki dolgu cümlesiyle ortalanınca (mean pooling) vektör [1/3, 2/3] olur ve kosinüs 1/√5 ≈ 0.447'ye düşer. Üçüncü satır seyrelmenin sonucudur: kanıt içermeyen ama yakın konulu parça (0.6) büyük parçayı geçer ve top-k'da onun yerini alabilir.
:::

::: gorev 1 · Parça sıralamasını belgeye indir, recall, precision, RR ve nDCG hesapla
`retrieval_olcutleri(siralamalar, ilgililer, k)` işlevini yaz. `siralamalar` 1–20 sorguluk bir sözlüktür: anahtar boş olmayan string sorgu kimliği, değer parça düzeyindeki indeksin döndürdüğü 1–50 öğeli, yinelenmeyen parça kimliği listesidir (ilk öğe 1. sıradır). Parça kimliği `belge#parça` biçiminde bir stringdir: tam olarak bir `#` içerir ve iki yanı da boş değildir; belge kimliği `#` işaretinden önceki kısımdır. `ilgililer` tam olarak aynı anahtar kümesine sahip sözlüktür; her değeri 1–20 öğeli `{belge: derece}` sözlüğüdür, belge `#` içermeyen boş olmayan string, derece 1–3 tamsayıdır (bool değil). İlgili belge sıralamada hiç geçmeyebilir. `k` 1–20 tamsayıdır (bool değil). Geçersiz veride `ValueError` yükselt.

Her sorguda önce parça sıralamasını belge sıralamasına indir: her belge ilk parçasının geçtiği yerde bir kez yer alır, aynı belgenin sonraki parçaları atılır. Sonra bu belge sıralamasının ilk k öğesine bak (k'dan kısaysa tamamına): `recall` = ilk k'daki ilgili belge sayısı / ilgili belge sayısı; `precision` = aynı sayı / k (liste kısa olsa da payda k); `rr` = ilk k içindeki ilk ilgili belgenin sırası r ise 1/r, yoksa 0; `ndcg` = DCG/IDCG, burada DCG = Σ derece_i / log2(i + 1) (i = 1, 2, ... sıra; ilgisiz belgenin derecesi 0), IDCG ise aynı formülün o sorgunun dereceleri büyükten küçüğe dizilip ilk k tanesine uygulanmış hâlidir. `{"sorgular": {sorgu: {"recall": ..., "precision": ..., "rr": ..., "ndcg": ...}}, "ortalama": {"recall": ..., "precision": ..., "mrr": ..., "ndcg": ...}}` döndür. Ortalama her sorguya eşit ağırlık veren makro ortalamadır (`mrr` = `rr` ortalaması) ve yuvarlanmamış sorgu değerlerinden hesaplanır. Bütün çıktı değerlerini `round(x, 4)` ile yuvarla. Girdileri değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-22")
```

```starter
from ai_temel_veri import json_yukle
def retrieval_olcutleri(siralamalar, ilgililer, k):
    # KUSURLU BAŞLANGIÇ KODU: aynı belgenin parçalarını ayrı isabet sayar ve diğer ölçütleri kopyalar.
    rows={}
    for q,liste in siralamalar.items():
        hit=sum(p.split("#")[0] in ilgililer[q] for p in liste[:k])
        rows[q]={"recall":hit/len(ilgililer[q]),"precision":hit/k,"rr":1.0 if hit else 0.0,"ndcg":1.0 if hit else 0.0}
    return {"sorgular":rows,"ortalama":{a:sum(v[b] for v in rows.values())/len(rows) for a,b in [("recall","recall"),("precision","precision"),("mrr","rr"),("ndcg","ndcg")]}}

v=json_yukle("veri/retrieval.json")["olcutler"]
print("Sentetik sıralama/dereceler:",v)
print("Ölçütler:",retrieval_olcutleri(v["siralamalar"],v["ilgililer"],v["k"]))
```

```test
import copy
S = {"q1": ["d3#0", "d1#p2", "d7#1", "d1#p0", "d2#0", "d9#4"], "q2": ["d4#0", "d4#1", "d8#0"], "q3": ["d6#a"]}
I = {"q1": {"d5": 1, "d2": 2, "d1": 3}, "q2": {"d4": 1}, "q3": {"d2": 2}}
B3 = {"sorgular": {"q1": {"recall": 0.3333, "precision": 0.3333, "rr": 0.5, "ndcg": 0.3975}, "q2": {"recall": 1.0, "precision": 0.3333, "rr": 1.0, "ndcg": 1.0}, "q3": {"recall": 0.0, "precision": 0.0, "rr": 0.0, "ndcg": 0.0}}, "ortalama": {"recall": 0.4444, "precision": 0.2222, "mrr": 0.5, "ndcg": 0.4658}}
UZUN = ["d%d#0" % j for j in range(50)]
COK = {"d%d" % j: 3 for j in range(20)}
BS = {"q%d" % j: UZUN for j in range(20)}
BI = {"q%d" % j: COK for j in range(20)}
def sozlesme(fn):
    try:
        s, i = copy.deepcopy(S), copy.deepcopy(I)
        if fn(s, i, 3) != B3 or s != S or i != I:
            return False
        if fn(S, I, 2)["sorgular"]["q1"] != {"recall": 0.3333, "precision": 0.5, "rr": 0.5, "ndcg": 0.4441} or fn(S, I, 1)["sorgular"]["q1"] != {"recall": 0.0, "precision": 0.0, "rr": 0.0, "ndcg": 0.0}:
            return False
        if fn(S, I, 4)["ortalama"] != {"recall": 0.5556, "precision": 0.25, "mrr": 0.5, "ndcg": 0.5261}:
            return False
        tek = {"recall": 1.0, "precision": 1.0, "rr": 1.0, "ndcg": 1.0}
        if fn({"q": ["a#0"]}, {"q": {"a": 1}}, 1) != {"sorgular": {"q": tek}, "ortalama": {"recall": 1.0, "precision": 1.0, "mrr": 1.0, "ndcg": 1.0}}:
            return False
        if fn(BS, BI, 20)["sorgular"]["q19"] != tek or fn(BS, BI, 1)["ortalama"]["recall"] != 0.05:
            return False
        l8 = ["r%d#0" % j for j in range(8)] + ["x%d#0" % j for j in range(12)]
        l15 = ["r%d#0" % j for j in range(15)] + ["x%d#0" % j for j in range(5)]
        r19, r17 = {"r%d" % j: 1 for j in range(19)}, {"r%d" % j: 1 for j in range(17)}
        if fn({"a": l8, "b": l8, "c": l15}, {"a": r19, "b": r19, "c": r17}, 20)["ortalama"]["recall"] != 0.5748:
            return False
        for args in [(None, I, 3), ([], I, 3), ({}, {}, 3), (S, None, 3), (S, dict(I, q4={"a": 1}), 3), (dict(S, q4=["a#0"]), I, 3), ({"": ["a#0"]}, {"": {"a": 1}}, 1), ({1: ["a#0"]}, {1: {"a": 1}}, 1),
                     (dict(S, q1=("d1#0",)), I, 3), (dict(S, q1=[]), I, 3), (dict(S, q1=["d1#0", "d1#0"]), I, 3), (dict(S, q1=["d1#0", b"d2#0"]), I, 3), (dict(S, q1=["d1#0", 7]), I, 3), (dict(S, q1=["d1#0", ""]), I, 3),
                     (dict(S, q1=["d1#0", "d2"]), I, 3), (dict(S, q1=["d1#0", "#0"]), I, 3), (dict(S, q1=["d1#0", "d2#"]), I, 3), (dict(S, q1=["d1#0", "d2#0#1"]), I, 3), (dict(S, q1=UZUN + ["x#0"]), I, 3),
                     (S, dict(I, q1={}), 3), (S, dict(I, q1=[("d1", 3)]), 3), (S, dict(I, q1={"d1": 0}), 3), (S, dict(I, q1={"d1": 4}), 3), (S, dict(I, q1={"d1": True}), 3), (S, dict(I, q1={"d1": 2.0}), 3),
                     (S, dict(I, q1={"": 1}), 3), (S, dict(I, q1={b"d1": 1}), 3), (S, dict(I, q1={"d1#0": 1}), 3), (S, dict(I, q1=dict(COK, x=1)), 3), (dict(BS, q20=UZUN), dict(BI, q20=COK), 3),
                     (S, I, 0), (S, I, 21), (S, I, True), (S, I, 3.0), (S, I, None)]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(retrieval_olcutleri), "ölçüt formülleri, makro ortalama, yuvarlama ve sınırlar korunmalı")
def m_sira(s, i, k):
    return retrieval_olcutleri({q: list(reversed(l)) for q, l in s.items()}, i, k)
def m_ikili(s, i, k):
    return retrieval_olcutleri(s, {q: {d: 1 for d in g} for q, g in i.items()}, k)
def m_k(s, i, k):
    return retrieval_olcutleri(s, i, k + 1)
for ad, mutant in [("sıralamayı ters çeviren", m_sira), ("dereceyi yok sayan", m_ikili), ("k sınırını kaydıran", m_k)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle
def retrieval_olcutleri(siralamalar, ilgililer, k):
    import math
    def metin(x):
        return isinstance(x, str) and len(x) > 0
    def belge(x):
        b, _, p = x.partition("#") if isinstance(x, str) else ("", "", "")
        if not b or not p or "#" in p:
            raise ValueError("parça geçersiz")
        return b
    if type(k) is not int or not 1 <= k <= 20:
        raise ValueError("k geçersiz")
    if not isinstance(siralamalar, dict) or not isinstance(ilgililer, dict) or not 1 <= len(siralamalar) <= 20 or set(siralamalar) != set(ilgililer):
        raise ValueError("sorgular geçersiz")
    ham = {}
    for q, liste in siralamalar.items():
        ilgili = ilgililer[q]
        if not metin(q) or not isinstance(liste, list) or not 1 <= len(liste) <= 50:
            raise ValueError("sıralama geçersiz")
        belgeler = list(dict.fromkeys(belge(x) for x in liste))
        if len(set(liste)) != len(liste):
            raise ValueError("sıralama geçersiz")
        if not isinstance(ilgili, dict) or not 1 <= len(ilgili) <= 20 or not all(metin(d) and "#" not in d and type(g) is int and 1 <= g <= 3 for d, g in ilgili.items()):
            raise ValueError("ilgililik geçersiz")
        ust = belgeler[:k]
        isabet = sum(d in ilgili for d in ust)
        rr = next((1 / (i + 1) for i, d in enumerate(ust) if d in ilgili), 0)
        dcg = sum(ilgili.get(d, 0) / math.log2(i + 2) for i, d in enumerate(ust))
        idcg = sum(g / math.log2(i + 2) for i, g in enumerate(sorted(ilgili.values(), reverse=True)[:k]))
        ham[q] = {"recall": isabet / len(ilgili), "precision": isabet / k, "rr": rr, "ndcg": dcg / idcg}
    ortalama = {a: round(sum(o[b] for o in ham.values()) / len(ham), 4) for a, b in [("recall", "recall"), ("precision", "precision"), ("mrr", "rr"), ("ndcg", "ndcg")]}
    return {"sorgular": {q: {a: round(v, 4) for a, v in o.items()} for q, o in ham.items()}, "ortalama": ortalama}

if __name__ == "__main__":
    v=json_yukle("veri/retrieval.json")["olcutler"]
    print("Sentetik sıralama/dereceler:",v)
    print("Ölçütler:",retrieval_olcutleri(v["siralamalar"],v["ilgililer"],v["k"]))
```

```hint
Önce her parça kimliğinin `#` öncesini al ve her belgeyi yalnız ilk görüldüğü yerde tut (`dict.fromkeys` ekleme sırasını korur); k ile bu belge listesini kes, parça listesini değil. DCG'de i. sıranın paydası log2(i + 1) olduğundan `enumerate` ile 0'dan sayıyorsan `i + 2` kullan; IDCG'yi derecelerin büyükten küçüğe sıralanmış ilk k tanesinden kur. Ortalamayı yuvarlamadan önce al, `mrr` anahtarının sorgu tarafındaki karşılığı `rr`'dir.
```
:::

::: gorev 2 · Lexical ve dense sıralamaları RRF ile birleştir
`rrf_birlestir(siralamalar, n)` işlevini yaz. `siralamalar` 1–5 sıralı listeden oluşan bir listedir (örneğin BM25 ve dense retriever çıktısı); her iç liste 1–100 öğeli, yinelenmeyen, boş olmayan string belge kimliği listesidir ve ilk öğe 1. sıradır. Aynı belge farklı listelerde yer alabilir. `n` 1–20 tamsayıdır (bool değil). Geçersiz veride `ValueError` yükselt.

Her belgenin puanı, geçtiği her listedeki sırası r için 1/(60 + r) değerlerinin toplamıdır; belgenin geçmediği liste puan katmaz. Sıralama anahtarı `round(puan, 6)` değeridir: belgeleri bu değere göre büyükten küçüğe, bu değer eşitse belge kimliğine göre alfabetik (Python string sırası, küçükten büyüğe) sırala. Böylece toplama sırasından doğan float farkı ya da altıncı ondalıktan sonraki fark eşitlik kırmayı değiştirmez. İlk n belgeyi `(belge, round(puan, 6))` demetlerinin (tuple) listesi olarak döndür; n'den az belge varsa hepsini döndür. Girdileri değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-22")
```

```starter
from ai_temel_veri import json_yukle
def rrf_birlestir(siralamalar, n):
    # KUSURLU BAŞLANGIÇ KODU: füzyon yerine yalnız ilk sıralamanın sonuçlarını kullanır.
    return [(d,round(1/(60+r),6)) for r,d in enumerate(siralamalar[0],1)][:n]

v=json_yukle("veri/retrieval.json")["rrf"]
print("Sentetik lexical/dense:",v)
print("RRF:",rrf_birlestir(v["siralamalar"],v["n"]))
```

```test
import copy
L = [["zehir", "b", "a", "c"], ["a", "b", "d"]]
UZUN = ["d%03d" % j for j in range(100)]
X = [["y", "f1", "f2", "f3", "f4", "f5", "x"], ["x", "y"], ["g1", "x", "g2", "g3", "g4", "g5", "y"]]
def yerles(konum):
    f = iter(["f%02d" % j for j in range(13)])
    return [konum.get(r) or next(f) for r in range(1, 16)]
Z = [yerles({10: "z", 11: "a"}), yerles({11: "a", 13: "z"}), yerles({13: "z", 14: "a"})]
def sozlesme(fn):
    try:
        g = copy.deepcopy(L)
        if fn(g, 5) != [("a", 0.032266), ("b", 0.032258), ("zehir", 0.016393), ("d", 0.015873), ("c", 0.015625)] or g != L:
            return False
        if fn(L, 2) != [("a", 0.032266), ("b", 0.032258)] or fn([["x", "y"], ["y", "x"]], 1) != [("x", 0.032522)]:
            return False
        if fn([["a", "m"], ["c", "k"]], 20) != [("a", 0.016393), ("c", 0.016393), ("k", 0.016129), ("m", 0.016129)] or fn([["a"]], 1) != [("a", 0.016393)]:
            return False
        if fn(X, 2) != [("x", 0.047448), ("y", 0.047448)] or [t for t in fn(Z, 20) if t[0] in ("a", "z")] != [("a", 0.041683), ("z", 0.041683)]:
            return False
        r = fn([UZUN] * 5, 20)
        if [d for d, _ in r] != UZUN[:20] or r[0] != ("d000", 0.081967) or r[-1] != ("d019", 0.0625):
            return False
        for args in [(None, 3), ((["a"],), 3), ([], 3), ([["a"]] * 6, 3), ([["a"], None], 3), ([["a"], ("b",)], 3), ([["a"], []], 3), ([["a", "a"]], 3),
                     ([["a", ""]], 3), ([["a", b"b"]], 3), ([["a", 1]], 3), ([UZUN + ["x"]], 3), (L, 0), (L, 21), (L, True), (L, 2.0), (L, None)]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(rrf_birlestir), "RRF puanı, eşitlik kırma, kesme ve sınırlar korunmalı")
def m_sira(s, n):
    return rrf_birlestir([list(reversed(l)) for l in s], n)
def m_tek(s, n):
    return rrf_birlestir(s[:1], n)
def m_alfabe(s, n):
    return sorted(rrf_birlestir(s, n))
for ad, mutant in [("sırayı ters çeviren", m_sira), ("tek listeye düşen", m_tek), ("puan sırasını bozan", m_alfabe)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle
def rrf_birlestir(siralamalar, n):
    if type(n) is not int or not 1 <= n <= 20:
        raise ValueError("n geçersiz")
    if not isinstance(siralamalar, list) or not 1 <= len(siralamalar) <= 5:
        raise ValueError("liste sayısı geçersiz")
    puan = {}
    for liste in siralamalar:
        if not isinstance(liste, list) or not 1 <= len(liste) <= 100 or not all(isinstance(d, str) and len(d) > 0 for d in liste) or len(set(liste)) != len(liste):
            raise ValueError("sıralama geçersiz")
        for sira, d in enumerate(liste, 1):
            puan[d] = puan.get(d, 0) + 1 / (60 + sira)
    yuvarlak = {d: round(p, 6) for d, p in puan.items()}
    secim = sorted(yuvarlak, key=lambda d: (-yuvarlak[d], d))[:n]
    return [(d, yuvarlak[d]) for d in secim]

if __name__ == "__main__":
    v=json_yukle("veri/retrieval.json")["rrf"]
    print("Sentetik lexical/dense:",v)
    print("RRF:",rrf_birlestir(v["siralamalar"],v["n"]))
```

```hint
Puanları bir sözlükte biriktir; `enumerate(liste, 1)` sırayı 1'den başlatır. Puanları sıralamadan önce yuvarla; `(-yuvarlanmis_puan, kimlik)` demetini sıralama anahtarı yapmak iki sıralama kuralını birden uygular.
```
:::

::: gorev 3 · MMR ile çeşitli kanıt seç ve bağlamın kenarlarına diz
`mmr_sec(adaylar, benzerlik, adet, lam)` işlevini yaz. `adaylar` 1–30 öğeli `{belge: sorgu_benzerligi}` sözlüğüdür; belge boş olmayan string, benzerlik 0–100 tamsayıdır (yüzde ölçeği, bool değil). `benzerlik` tam olarak adaylarla aynı anahtar kümesine sahip sözlüktür; `benzerlik[a]` tam olarak a dışındaki adayları anahtar alan, değerleri 0–100 tamsayı (bool değil) olan bir sözlüktür ve tablo simetriktir (`benzerlik[a][b]` ile `benzerlik[b][a]` aynı). `adet` 1–10, `lam` 0–100 tamsayıdır (bool değil). Geçersiz veride `ValueError` yükselt.

Seçimi adım adım yap. S seçilmişler olmak üzere her adımda seçilmemiş her d için puan = lam · sorgu_benzerligi(d) − (100 − lam) · max_{s∈S} benzerlik[d][s] hesapla (S boşken ceza 0). En yüksek puanlıyı S'ye ekle; eşit puanda sorgu benzerliği yüksek olan, o da eşitse alfabetik olarak küçük kimlik seçilir. min(adet, aday sayısı) belge seçince dur. `{"secim": [...], "baglam": [...]}` döndür: `secim` seçim sırasıdır; `baglam` önce secim'in 1., 3., 5., ... öğelerini sırayla, ardından 2., 4., ... öğelerini sondan başa içerir (MMR'nin ilk seçtiği iki kanıt başta ve sonda, son seçilenler ortada kalır). Girdileri değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-22")
```

```starter
from ai_temel_veri import json_yukle
def mmr_sec(adaylar, benzerlik, adet, lam):
    # KUSURLU BAŞLANGIÇ KODU: benzerlik cezasını ve kenar dizilimini yok sayar.
    s=sorted(adaylar,key=lambda d:(-adaylar[d],d))[:adet]
    return {"secim":s,"baglam":list(s)}

v=json_yukle("veri/retrieval.json")["mmr"]
print("Sentetik MMR tablosu:",v)
print("Seçim:",mmr_sec(v["adaylar"],v["benzerlik"],v["adet"],v["lam"]))
```

```test
import copy
A = {"rehber": 95, "kopya": 94, "politika": 80, "sss": 70}
B = {"rehber": {"kopya": 98, "politika": 30, "sss": 20}, "kopya": {"rehber": 98, "politika": 30, "sss": 25},
     "politika": {"rehber": 30, "kopya": 30, "sss": 40}, "sss": {"rehber": 20, "kopya": 25, "politika": 40}}
IDS = ["b%02d" % j for j in range(31)]
def tablo(ids, v):
    return {a: {b: v for b in ids if b != a} for a in ids}
def cift(a, b, v):
    yeni = copy.deepcopy(B)
    yeni[a][b] = yeni[b][a] = v
    return yeni
def sozlesme(fn):
    try:
        a, b = copy.deepcopy(A), copy.deepcopy(B)
        if fn(a, b, 4, 70) != {"secim": ["rehber", "politika", "sss", "kopya"], "baglam": ["rehber", "sss", "kopya", "politika"]} or a != A or b != B:
            return False
        if fn(A, B, 2, 100) != {"secim": ["rehber", "kopya"], "baglam": ["rehber", "kopya"]} or fn(A, B, 10, 0)["secim"] != ["rehber", "sss", "politika", "kopya"]:
            return False
        if fn({"m": 60, "k": 50, "z": 90}, {"m": {"k": 0, "z": 20}, "k": {"m": 0, "z": 10}, "z": {"m": 20, "k": 10}}, 3, 50)["secim"] != ["z", "m", "k"]:
            return False
        if fn({"a": 100, "b": 41, "c": 99}, {"a": {"b": 0, "c": 59}, "b": {"a": 0, "c": 0}, "c": {"a": 59, "b": 0}}, 2, 50)["secim"] != ["a", "b"]:
            return False
        f_b = {"p": {"q": 0, "x": 40, "y": 60}, "q": {"p": 0, "x": 40, "y": 0}, "x": {"p": 40, "q": 40, "y": 0}, "y": {"p": 60, "q": 0, "x": 0}}
        if fn({"p": 90, "q": 80, "x": 50, "y": 50}, f_b, 4, 50) != {"secim": ["p", "q", "x", "y"], "baglam": ["p", "x", "y", "q"]}:
            return False
        if fn({"c": 60, "a": 60, "b": 40}, tablo(["a", "b", "c"], 0), 1, 100) != {"secim": ["a"], "baglam": ["a"]} or fn({"x": 0}, {"x": {}}, 1, 0) != {"secim": ["x"], "baglam": ["x"]}:
            return False
        a30 = {d: min(100, j * 4) for j, d in enumerate(IDS[:30])}
        r = fn(a30, tablo(IDS[:30], 100), 10, 100)
        if r["secim"] != ["b25", "b26", "b27", "b28", "b29", "b24", "b23", "b22", "b21", "b20"] or r["baglam"] != ["b25", "b27", "b29", "b23", "b21", "b20", "b22", "b24", "b28", "b26"]:
            return False
        for args in [(None, B, 2, 70), ([], B, 2, 70), ({}, {}, 2, 70), (dict(a30, b30=1), tablo(IDS, 0), 2, 70), ({"": 50}, {"": {}}, 1, 70), ({b"x": 50}, {b"x": {}}, 1, 70),
                     ({"x": 101}, {"x": {}}, 1, 70), ({"x": -1}, {"x": {}}, 1, 70), ({"x": True}, {"x": {}}, 1, 70), ({"x": 50.0}, {"x": {}}, 1, 70),
                     (A, None, 2, 70), (A, {d: r for d, r in B.items() if d != "sss"}, 2, 70), (A, dict(B, ek={}), 2, 70), (A, dict(B, sss=[("rehber", 20)]), 2, 70), (A, dict(B, sss={"rehber", "kopya", "politika"}), 2, 70),
                     (A, dict(B, sss={"rehber": 20, "kopya": 25}), 2, 70), (A, dict(B, sss=dict(B["sss"], sss=100)), 2, 70), (A, dict(B, sss=dict(B["sss"], rehber=21)), 2, 70),
                     (A, cift("sss", "rehber", 101), 2, 70), (A, cift("sss", "rehber", -1), 2, 70), (A, cift("sss", "rehber", True), 2, 70), (A, cift("sss", "rehber", 20.0), 2, 70),
                     (A, B, 0, 70), (A, B, 11, 70), (A, B, True, 70), (A, B, 2.0, 70), (A, B, 2, -1), (A, B, 2, 101), (A, B, 2, True), (A, B, 2, 0.7), (A, B, 2, None)]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(mmr_sec), "MMR puanı, eşitlik kırma, bağlam dizilimi ve sınırlar korunmalı")
def m_lam(a, b, adet, lam):
    return mmr_sec(a, b, adet, 100)
def m_benzerlik(a, b, adet, lam):
    return mmr_sec(a, {x: {y: 0 for y in r} for x, r in b.items()}, adet, lam)
def m_dizilim(a, b, adet, lam):
    r = mmr_sec(a, b, adet, lam)
    return {"secim": r["secim"], "baglam": list(r["secim"])}
for ad, mutant in [("çeşitliliği kapatan", m_lam), ("benzerlik cezasını sıfırlayan", m_benzerlik), ("kenar dizilimini kaldıran", m_dizilim)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle
def mmr_sec(adaylar, benzerlik, adet, lam):
    def puan(x):
        return type(x) is int and 0 <= x <= 100
    if type(adet) is not int or not 1 <= adet <= 10 or not puan(lam):
        raise ValueError("parametre geçersiz")
    if not isinstance(adaylar, dict) or not 1 <= len(adaylar) <= 30 or not all(isinstance(d, str) and len(d) > 0 and puan(s) for d, s in adaylar.items()):
        raise ValueError("adaylar geçersiz")
    if not isinstance(benzerlik, dict) or set(benzerlik) != set(adaylar) or not all(isinstance(r, dict) and set(r) == set(adaylar) - {a} for a, r in benzerlik.items()):
        raise ValueError("benzerlik geçersiz")
    if not all(puan(v) and v == benzerlik[b][a] for a, r in benzerlik.items() for b, v in r.items()):
        raise ValueError("benzerlik geçersiz")
    secim = []
    for _ in range(min(adet, len(adaylar))):
        def deger(d):
            ceza = max([benzerlik[d][s] for s in secim], default=0)
            return (-(lam * adaylar[d] - (100 - lam) * ceza), -adaylar[d], d)
        secim.append(min([d for d in adaylar if d not in secim], key=deger))
    return {"secim": secim, "baglam": secim[::2] + secim[1::2][::-1]}

if __name__ == "__main__":
    v=json_yukle("veri/retrieval.json")["mmr"]
    print("Sentetik MMR tablosu:",v)
    print("Seçim:",mmr_sec(v["adaylar"],v["benzerlik"],v["adet"],v["lam"]))
```

```hint
Her adımda seçilmemişler arasından `(-mmr_puani, -sorgu_benzerligi, kimlik)` anahtarının en küçüğünü al; `max(..., default=0)` boş S cezasını çözer. Bağlam dizilimi için `secim[::2]` ile ters çevrilmiş `secim[1::2]` dilimlerini birleştir.
```
:::

::: gorev Gerçek deney · Gerçek gömmelerde getir ve retrieval kalitesini ölç
`getir_ve_olc(sorgu_vek, parca_idler, parca_vekleri, altin, k)` işlevini yaz.

- Doğrulama, aksi hâlde `ValueError`: `parca_idler` 1–1000 öğeli, yinelenmeyen, boş olmayan string listesi; `parca_vekleri` aynı uzunlukta liste. `sorgu_vek` ve her parça vektörü aynı uzunlukta (2–4096), öğeleri bool olmayan sonlu int/float olan, sıfır olmayan liste. `altin` boş olmayan, yinelenmeyen, hepsi `parca_idler` içinde olan string listesi. `k` bool olmayan int, `1 ≤ k ≤ len(parca_idler)`.
- Sorguyu ve her vektörü L2 normuna böl (kosinüs); skora göre azalan, eşitlikte küçük indeks önce sırala → `sirali` (tüm parça kimlikleri sıralı). Metrikler: `isabet` (ilk k'da altın var mı), `anma` = recall@k (round 4), `mrr` tüm sıralamadaki ilk altının sırası r ise 1/r, yoksa 0 (round 4), `ndcg` = nDCG@k (round 4): ikili ilgi kullanılır (altındaki öğe 1, diğerleri 0), `DCG@k = Σ ilgi_i / log₂(i + 1)`, `IDCG@k` ilk `min(k, len(altin))` konumun hepsi ilgiliymiş gibi hesaplanır; IDCG 0 ise 0.0.
- `{"sirali": sıralı kimlikler, "isabet", "anma", "mrr", "ndcg"}` döndür. Girdileri değiştirme.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import math
import ai_lab

def getir_ve_olc(sorgu_vek, parca_idler, parca_vekleri, altin, k):
    return {"sirali": [], "isabet": False, "anma": 0.0, "mrr": 0.0, "ndcg": 0.0}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_22 as deney
    deney.goster(getir_ve_olc)
```

```test
import copy
import ai_lab
sonuclar = []
def kontrol(kosul, mesaj):
    sonuclar.append(bool(kosul))
    return ok(kosul, mesaj)
import ast
_yasak=("referans","referans_getir","getattr","_birim","_sirala","_metrik","kanit_yaz")
sorun=ai_lab.kod_denetimi(src,yasak=_yasak)
for n in ast.walk(ast.parse(src)):
    if isinstance(n,ast.ImportFrom) and any(a.name in _yasak or a.name=="*" for a in n.names): sorun.append("referans importu yasak")
if not kontrol(not sorun,"Kendi retrieval ölçümünü yaz: "+"; ".join(sorun)): stop()
fn = need("getir_ve_olc")
from sandbox import ai_gercek_ai_temel_22 as D
idler = ["p0", "p1", "p2", "p3"]
vek = [[1.0, 0.0], [0.9, 0.1], [0.0, 1.0], [-1.0, 0.0]]
vakalar = [([1.0, 0.0], idler, vek, ["p0"], 2), ([1.0, 0.0], idler, vek, ["p2", "p3"], 3),
           ([0.0, 1.0], idler, vek, ["p0"], 1), ([1.0, 1.0], idler, vek, ["p1", "p2"], 2)]
vakalar += [([s,s],["z","a"],[[s,0],[0,s]],["z","a"],1) for s in (1e300,1e-300,10**400)]

def ayni(a, b):
    return isinstance(a, dict) and set(a) == set(b) and a["sirali"] == b["sirali"] and all(a[x] == b[x] for x in ("isabet", "anma", "mrr", "ndcg"))
def sozlesme(f):
    try:
        for q, idl, vk, alt, k in vakalar:
            qq, ii, vv, aa = list(q), list(idl), copy.deepcopy(vk), list(alt)
            if not ayni(f(qq, ii, vv, aa, k), D.referans_getir(q, idl, vk, alt, k)) or qq != q or ii != idl or vv != vk or aa != alt:
                return False
        ek_vakalar = [
            ([1.0, 0.0], ["p0"], [[1.0, 0.0]], ["p0"], 1),
            ([1.0, 0.0], idler, vek, ["p0", "p1", "p2"], 1),
            ([1.0, 0.0], idler, vek, ["p0"], 4),
            ([1.0] + [0.0] * 4095, ["p0", "p1"], [[1.0] + [0.0] * 4095, [0.0, 1.0] + [0.0] * 4094], ["p0"], 2),
            ([1.0, 0.0], [f"p{i}" for i in range(1000)], [[1.0, 0.0]] + [[0.0, 1.0]] * 999, ["p0"], 1),
        ]
        for q2, idl2, vk2, alt2, k2 in ek_vakalar:
            if not ayni(f(list(q2), list(idl2), copy.deepcopy(vk2), list(alt2), k2), D.referans_getir(q2, idl2, vk2, alt2, k2)):
                return False
        q, idl, vk, alt, k = vakalar[0]
        for arg in [(q, None, vk, alt, 1), (q, [f"p{i}" for i in range(1001)], [[1.0, 0.0]] * 1001, ["p0"], 1),
                    (q, [1, "p1", "p2", "p3"], vk, ["p1"], 1), (q, ["", "p1", "p2", "p3"], vk, ["p1"], 1),
                    (q, idl, tuple(vk), alt, 1), (None, idl, vk, alt, 1),
                    ([1.0] * 4097, ["p0"], [[1.0] * 4097], ["p0"], 1),
                    (q, idl, [tuple(vk[0])] + vk[1:], alt, 2), (q, idl, [["a", 0.0]] + vk[1:], alt, 2),
                    ([1.0, float("inf")], idl, vk, alt, 2), (q, idl, [[1.0, float("inf")]] + vk[1:], alt, 2),
                    (q, idl, vk, ("p0",), 1), ([1.0], ["p0"], [[1.0]], ["p0"], 1),
                    (q, idl, vk, [1], 1), (q, idl, vk, [""], 1),
                    (q,idl,vk,[["p0"]],1),(q,idl,vk,None,1),(q, [], [], alt, 1), (q, idl, vk[:-1], alt, 2), (q, idl + ["x"], vk, alt, 2),
                    (q, ["p0", "p0", "p2", "p3"], vk, alt, 2), (q, idl, vk, ["yok"], 2), (q, idl, vk, [], 2), (q, idl, vk, ["p0", "p0"], 2),
                    (q, idl, vk, alt, 0), (q, idl, vk, alt, 5), (q, idl, vk, alt, True), (q, idl, vk, alt, 1.0),
                    ([0.0, 0.0], idl, vk, alt, 2), (q, idl, [[1.0, 0.0], [0.9, 0.1], [0.0, 1.0], [0.0, 0.0]], alt, 2),
                    (q[:1], idl, vk, alt, 2), (q, idl, [[1.0], [0.9, 0.1], [0.0, 1.0], [-1.0, 0.0]], alt, 2),
                    ([1.0, float("nan")], idl, vk, alt, 2), ([1.0, True], idl, vk, alt, 2)]:
            try:
                f(*arg)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
kontrol(sozlesme(fn), "kosinüs sıralaması ve recall@k/MRR/nDCG@k doğru; geçersiz girdi reddedilmeli")
for ad, kw in [("vektörleri normalize etmeyen", {"normalize": False}), ("MRR'ı yalnız ilk k'da arayan", {"mrr_tam": False}),
               ("nDCG'yi normalize etmeyen", {"ndcg_norm": False})]:
    kontrol(not sozlesme(lambda q, i, v, a, k, kw=kw: D.referans_getir(q, i, v, a, k, **kw)), "hatalı çözüm reddedilmeli: " + ad)
sabit = D.referans_getir(*vakalar[0])
kontrol(not sozlesme(lambda *a: sabit), "hatalı çözüm reddedilmeli: ezber sonuç")
r, oz = None, None
if all(sonuclar):
    try:
        r = D.deney(fn)
    except ai_lab.GercekLabYok as e:
        kontrol(False, f"GERÇEK MODEL YOK, deney yapılmadı: {e}")
        stop()
    pv, sv = r["vektorler"]["parca"], r["vektorler"]["soru"]
    kontrol(len(pv)==len(D.PARCALAR) and len(sv)==len(D.SORULAR) and len(r["kayitlar"])==len(D.SORULAR),"iki gerçek embed çağrısının tüm10parça ve6soru sonuçları mevcut")
    kontrol(r["ortam"]["gomme"]["once_yukluydu"] or r["ortam"]["gomme"]["model_bosaltildi"],"deney yalnız kendi yüklediği gömme modelini bıraktı")
    kontrol(len(pv[0]) == 384 and r["ortam"]["gomme"]["model"] == D.GOMME_MODELI, f"gerçek gömmeler: {len(pv)} parça × {len(pv[0])} boyut")
    esit = all(ayni(k["k"+str(adet)],D.referans_getir(q,r["idler"],pv,k["altin"],adet))
               for k,q in zip(r["kayitlar"],sv) for adet in (1,D.K))
    kontrol(esit, "gerçek vektörlerde sıralama ve metrikler bağımsız hesapla aynı")
    oz = D.ozet(r)
    kontrol(oz["anma_k3"] >= oz["anma_k1"], f"büyük k anma'yı düşürmez: recall@3 {oz['anma_k3']} ≥ recall@1 {oz['anma_k1']}")
yol = ai_lab.kanit_yaz("temel-retrieval", {"kaynak": "gercek", "kabul": all(sonuclar), "ders": "ai-temel-22",
                                           "ortam": (r or {}).get("ortam"), "ozet": oz, "deney": r, "sinir":"sentetik derlem üzerinde gerçek gömmeler;genel RAG kalite/güvenlik kabulü değil"})
if oz:
    ok(True, f"BULGU ({D.GOMME_MODELI}, {oz['boyut']} boyut): {oz['soru']} soruda recall@3 {oz['anma_k3']} vs recall@1 {oz['anma_k1']}, "
             f"MRR {oz['mrr']}, nDCG@3 {oz['ndcg_k3']}; isabet@3 {oz['isabet_k3']}/{oz['soru']} vs isabet@1 {oz['isabet_k1']}/{oz['soru']}. "
             f"Büyük k anma'yı düşürmez ama bağlama daha çok parça sokar.")
```

```solution
import math
import ai_lab

def getir_ve_olc(sorgu_vek, parca_idler, parca_vekleri, altin, k):
    if not isinstance(parca_idler, list) or not 1 <= len(parca_idler) <= 1000 \
            or any(not isinstance(x, str) or not x for x in parca_idler) or len(set(parca_idler)) != len(parca_idler):
        raise ValueError("parca_idler yinelenmeyen, boş olmayan string listesi olmalı")
    if not isinstance(parca_vekleri, list) or len(parca_vekleri) != len(parca_idler):
        raise ValueError("parca_vekleri parça sayısına eşit olmalı")
    if not isinstance(sorgu_vek, list) or not 2 <= len(sorgu_vek) <= 4096:
        raise ValueError("sorgu_vek 2-4096 uzunlukta liste olmalı")
    def birim(v):
        if not isinstance(v, list) or len(v) != len(sorgu_vek) \
                or any(isinstance(x, bool) or not isinstance(x, (int, float)) or (isinstance(x,float) and not math.isfinite(x)) for x in v):
            raise ValueError("vektör geçersiz")
        from fractions import Fraction
        olcek=max(abs(x) for x in v)
        if not olcek: raise ValueError("sıfır vektör")
        vv=[float(Fraction(x)/Fraction(olcek)) for x in v]
        boy=math.hypot(*vv)
        return [x/boy for x in vv]
    if not isinstance(altin, list) or not altin \
            or any(not isinstance(x, str) or not x or x not in parca_idler for x in altin) or len(set(altin)) != len(altin):
        raise ValueError("altin, parca_idler içinde yinelenmeyen kimlikler olmalı")
    if isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= len(parca_idler):
        raise ValueError("k 1 ile parça sayısı arası tamsayı olmalı")
    q = birim(sorgu_vek)
    skor = [sum(a * b for a, b in zip(birim(v), q)) for v in parca_vekleri]
    order = sorted(range(len(parca_vekleri)), key=lambda i: (-skor[i], i))
    sirali = [parca_idler[i] for i in order]
    aset = set(altin)
    isabet_sayisi = sum(1 for x in sirali[:k] if x in aset)
    rr = 0.0
    for i, x in enumerate(sirali, 1):
        if x in aset:
            rr = 1 / i
            break
    dcg = sum(1 / math.log2(i + 1) for i, x in enumerate(sirali[:k], 1) if x in aset)
    idcg = sum(1 / math.log2(i + 1) for i in range(1, min(k, len(aset)) + 1))
    return {"sirali": sirali, "isabet": isabet_sayisi > 0, "anma": round(isabet_sayisi / len(aset), 4),
            "mrr": round(rr, 4), "ndcg": round(dcg / idcg, 4) if idcg else 0.0}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_22 as deney
    deney.goster(getir_ve_olc)
```

```hint
Önce bütün vektörleri birim vektöre çevir (geçersiz/sıfır vektörü burada yakala), kosinüsü `(-skor, indeks)` anahtarıyla sırala. Metrikler 1. görevdekilerin ikili ilgili, tek sorguluk hâlidir: `anma` recall@k, `mrr` tüm sıralamada ilk altın, `ndcg` yalnız ilk k üzerinden DCG/IDCG.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Belge düzeyinde ölçüm (`Recall@k`, `MRR`, `nDCG@k`) (30 sn).** "Aynı belgenin beş parçası ilk beşi doldurduğunda parça düzeyinde `precision` şişer; gerçek kaliteyi görmek için önce belge düzeyinde tekilleştirme yapılır ve sıralama duyarlı `MRR`/`nDCG@k` ölçülür."
2. **Puan ölçeği gerektirmeyen füzyon (`RRF`) (35 sn).** "`BM25` tam terimde, `dense` arama eşanlamlıda güçlüdür; `RRF` ham skorları karıştırmak yerine her listedeki sıradan $\frac{1}{60 + r}$ toplayarak tek listede anahtar kelime dolgusu yapan zehirli belgenin etkisini sınırlar."
3. **Çeşitlilik (`MMR`) ve kenar dizilimi (`Lost in the Middle`) (30 sn).** "`MMR` yakın kopyaların bağlam bütçesini tekelleştirmesini önler; seçilen en güçlü kanıtların bağlamın başına ve sonuna yerleştirilmesi uzun bağlam ortası dikkat düşüşünü azaltır."
4. **Soru (25 sn).** "`MMR` çeşitliliği artırdığı halde neden zehirlenmiş bir kaynağı tek başına eleyemez ve hangi ek katmana ihtiyaç duyar?"
:::
