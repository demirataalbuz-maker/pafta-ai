---
id: ai-temel-03
title: "Logitler ve Softmax: Sonraki Tokenin Olasılığı"
summary: Üç tokenlık sentetik logitlerde kararlı softmax, greedy seçim ve çapraz entropi hesapla.
esleme: ai-temel-02, ai-temel-04, ai-matematik-07
timeout: 45
---

::: anlat Logit olasılık değildir

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Dil modeli her konumda sözlükteki adaylar için ham logit üretir | İlk üç görevde görünür üç adaylı sentetik JSON; son görevde kurulu SmolLM2 tokenizer/modelinin gerçek çıktıları | Üç sayılık örnek gerçek modelin sözlük boyutu veya tahmin kalitesinin ölçümü değildir |
| Softmax ve sıcaklık logitleri olasılık dağılımına çevirir | Önce kararlı Python hesabı, sonra gerçek son-konum logitlerinde tüm sözlük üzerinde softmax | Yüksek token olasılığı doğruluk veya güvenlik garantisi değildir |

> [!NOT]
> `veri/logitler.json` elle yazılmış **sentetik** veridir; modelden kaydedilmemiştir. İlk üç görev aynı dosyayı okur. Setup her çalıştırmada geçici kopya oluşturur, düzenlemeler kalıcı değildir. Kaynak fixture dosyasını editörde açabilir, ders kodunda yüklenen listenin kopyasını değiştirip Run ile gözleyebilirsin. Gizli testler bu dosyadan bağımsızdır. Son görev gerçek tokenizer ve kurulu yerel modeli CPU'da çalıştırır; ders sırasında indirme yapılmaz.

Modelin son katmanı her aday token için bir logit üretir. Logitler negatif olabilir ve toplamları bir olmak zorunda değildir. Softmax üstel değerleri normalize ederek olasılık dağılımı oluşturur; bütün logitlere aynı sabiti eklemek dağılımı değiştirmez.

Görevler 1–3 sentetik logitlerle çalışır; son adım gerçek Transformers modelini ve tokenizer’ını çalıştırır. Büyük logitlerde taşmayı önlemek için her değerden maksimum logit çıkarılır. Bu kararlı yöntem matematiksel sonucu korur ve güvenlik testlerinin tekrarlanabilirliğini artırır.
:::

::: anlat Seçim ve kayıp farklı sorulara cevap verir

Önce `veri/logitler.json` dosyasını aç. `logitler`, `tokenlar` ve `hedef` aynı üç adaylı senaryoyu taşır; `buyuk_logitler` taşma tehlikesini görünür kılar. Birinci görev bu sayıları dağılıma çevirir, ikinci görev en güçlü adayı seçer, üçüncü görev belirtilen hedefin kaybını hesaplar. Ham veriyi ve sonucu birlikte yazdırmak üç farklı işlemin aynı girdiye nasıl baktığını gösterir. Hedefi değiştirince logitler aynı kalır ama kayıp değişir; hedef sütunu modelin kendi tahmini değildir.

Logit, normalize edilmemiş bir tercih skorudur. Negatif olması olağandır; olasılık gibi sıfır ile bir arasına sıkıştırılmaz. Softmax her skoru üstel fonksiyondan geçirip toplam üstel değere böler. Büyük pozitif değerler doğrudan exp hesabında taşabileceği için bütün değerlerden maksimum çıkarılır. Bu, skorların farklarını korur. Üç logite aynı sabiti eklemek olasılıkları değiştirmez; skorları ikiyle çarpmak ise genellikle dağılımı keskinleştirir. Bu iki işlemi aynı hata sanmak yanlış öğrenmeye yol açar.

Greedy seçim en büyük skoru alır; rastgele örnekleme yapmaz. Pozitif sıcaklıkla bölmek aday sırasını değiştirmese de olasılıkları değiştirir. Bu nedenle yalnız kazanan tokena bakmak sıcaklık uygulandığını kanıtlamaz. Gerçek görevde hem ham logit hem sıcaklıklı olasılık istenir. Ham logit alanına bölünmüş değeri yazarsan ikisini karıştırmış olursun. Benzer biçimde yalnız en iyi beş tokenın olasılık toplamı genellikle bir değildir; bütün sözlük toplamıyla seçilmiş ilk adayların toplamı farklıdır.

Çapraz entropi, belirtilen doğru tokenın negatif log olasılığıdır. Gerçek hedef eğitim örneğinden gelir; bu görevde hedefi senaryo dosyası belirler. En güçlü token hedef değilse kayıp daha yüksek olabilir. Hesapta önce olasılığı altı haneye yuvarlayıp sonra log almak, küçük olasılığı sıfıra indirerek yanlış sonuç verebilir. Bu yüzden kayıp doğrudan kararlı log-sum-exp üzerinden hesaplanır. Çok büyük ortak sabitlerde önce büyük sayıları toplayıp sonra birbirinden çıkarmak da anlamlı basamak kaybettirir; farkı mümkün olduğunca erken almak gerekir.

Gerçek modelin çıktısı konum ve sözlük eksenlerini içerir. Sonraki token için metnin son konumuna bakılır; ilk konumdaki logitler aynı soruyu cevaplamaz. Token kimliği, tokenizer sözlüğündeki sayıdır; karakter konumu veya kelime sırası değildir. Bir kelime birden fazla tokene ayrılabilir. Tokenizer'ın iç parça gösterimi ile tek kimliği decode ederek elde edilen metin de farklı görünebilir. Boşlukları çıktıda repr ile okumak bu farkı yakalamaya yardımcı olur.

Bir saldırgan modelin girdisini değiştirerek belirli tokenların skorunu yükseltmeye çalışabilir; bu sayılar o denemenin etkisini incelemeye yardım eder. Ancak yüksek olasılık saldırının başarılı olduğunu kanıtlamaz: başarı ölçütü hedef göreve ve tehdit modeline bağlıdır. Savunma açısından da en olası yanıtı otomatik olarak doğru kabul etmek risklidir. Bu ders zararlı davranışın bütün türlerini puanlamaz, temel sayısal ölçümü öğretir.

Sık tuzaklar bool'u tamsayı sanmak, NaN karşılaştırmalarının olağan sayı gibi davranacağını varsaymak, girdiyi yerinde sıralamak ve eşitlikte son adayı seçmektir. Sayısal girdi ve çıktıların sonlu olduğu açıkça doğrulanır. İlk görevlerde sonuç altı haneye yuvarlanır; örneğin üç kez 0.333333 toplamı 0.999999 olur, bu yalnız yuvarlama etkisidir. Gerçek model görevinde yuvarlama yapılmaz, toleransla karşılaştırılır. Model yokluğu, bozuk çıktı veya eksik kabul gerçek deneyin başarılı olduğu anlamına gelmez.

Greedy seçim en büyük logitli tokenı alır; eşitlikte sözlükteki ilk aday kazanır. Olasılıkların toplamının bir olması, seçilen tokenın doğru veya güvenli olduğunu göstermez.

Çapraz entropi doğru tokenın negatif log olasılığıdır. Doğru tokenın olasılığı azaldıkça kayıp büyür. Küçük sentetik örnekler, eğitim ve değerlendirme raporlarındaki kayıp değerlerini yorumlamayı kolaylaştırır.
:::

::: tahmin Softmax ve seçimi tahmin et
Üç çıktı satırını yaz:

```python
import math
p = [math.exp(x - 1) for x in [0, 1, 2]]
p = [round(x / sum(p), 6) for x in p]
print(p)
print([0, 1, 2][p.index(max(p))])
print(round(-math.log(1 / 3), 6))
```

???

```cikti
[0.090031, 0.244728, 0.665241]
2
1.098612
```

İlk satır normalize olasılıkları, ikinci satır en yüksek olasılıklı token kimliğini, üçüncü satır üç eşit olasılıkta doğru tokenın kaybını verir.
:::

::: gorev 1 · Kararlı softmax uygula
`softmax(logitler)` işlevini yaz. Girdi tam üç adet sonlu, bool olmayan int/float içeren listedir; geçersiz veride `ValueError` yükselt. Maksimum logiti çıkararak kararlı üstel hesap yap, normalize et ve her olasılığı altı ondalığa yuvarlanmış float olarak döndür. Girdiyi değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-03")
```

```starter
from ai_temel_veri import json_yukle
import math

def softmax(logitler):
    # KUSURLU BAŞLANGIÇ KODU: logitleri olasılık sanıp doğrudan toplama böler.
    toplam=sum(logitler)
    return [round(x/toplam,6) for x in logitler]

v=json_yukle("veri/logitler.json")
print("Sentetik veri:",v)
print("Softmax:",softmax(v["logitler"]))
print("Büyük logitler:",v["buyuk_logitler"])
```

```test
import copy
def sozlesme(fn):
    try:
        x = [0.0, 1.0, 2.0]
        once = copy.deepcopy(x)
        if fn(x) != [0.090031, 0.244728, 0.665241] or x != once:
            return False
        if fn([0, 0, 0]) != [0.333333, 0.333333, 0.333333] or fn([1000, 1000, 1000]) != [0.333333, 0.333333, 0.333333]:
            return False
        if fn([1000,1001,1002]) != fn([0,1,2]) or fn([-1000,0,1000]) != [0.0,0.0,1.0]:
            return False
        for deger in [[float("nan"),0,1],[float("inf"),0,1],[-float("inf"),0,1],None, {}, [], [0, 1], [0, 1, 2, 3], [0, True, 2], [0, "1", 2]]:
            try:
                fn(deger)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(softmax), "kararlı normalizasyon ve logit şeması korunmalı")
def m_sira(x):
    return softmax(list(reversed(x)))
def m_olcek(x):
    return softmax([v * 2 for v in x])
def m_boyut(x):
    return softmax(x + [0])
for ad, mutant in [("sırayı bozan", m_sira), ("dağılımı ölçekle değiştiren", m_olcek), ("boyutu bozan", m_boyut)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle
def softmax(logitler):
    import math
    if not isinstance(logitler, list) or len(logitler) != 3 or any(not isinstance(x, (int, float)) or isinstance(x, bool) or not math.isfinite(x) for x in logitler):
        raise ValueError("logitler geçersiz")
    tepe = max(logitler)
    paylar = [math.exp(x - tepe) for x in logitler]
    toplam = sum(paylar)
    return [round(x / toplam, 6) for x in paylar]
if __name__ == "__main__":
    v=json_yukle("veri/logitler.json")
    print("Sentetik veri:",v)
    print("Softmax:",softmax(v["logitler"]))
    print("Büyük logitler:",v["buyuk_logitler"])

```

```hint
Önce `tepe = max(logitler)` al. Üstel hesabı `x - tepe` üzerinden yapıp payları toplama böl.
```
:::

::: gorev 2 · Greedy sonraki tokenı seç
`greedy_token(logitler, tokenlar)` işlevini yaz. Logitler ilk görevdeki biçimdedir. Tokenlar üç öğeli, birbirinden farklı, boş olmayan string listesidir. Geçersiz veride `ValueError` yükselt.

En yüksek logitli token stringini döndür. Eşitlikte listede daha önce gelen token kazanır; girdileri değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-03")
```

```starter
from ai_temel_veri import json_yukle

def greedy_token(logitler,tokenlar):
    # KUSURLU BAŞLANGIÇ KODU: eşit en yüksek skorlarda son adayı seçer.
    en=max(logitler)
    return tokenlar[max(i for i,x in enumerate(logitler) if x==en)]

v=json_yukle("veri/logitler.json")
print("Sentetik veri:",v)
print("Greedy:",repr(greedy_token(v["logitler"],v["tokenlar"])))
```

```test
T = ["a", "b", "c"]
def sozlesme(fn):
    try:
        if fn([0, 1, 2], T) != "c" or fn([3, 1, 2], T) != "a" or fn([2, 2, 0], T) != "a":
            return False
        if fn([0,3,1],T)!="b" or fn([1,1,1],T)!="a":
            return False
        for args in [([float("nan"),0,1],T),([float("inf"),0,1],T),(["a",1,2],T),(None, T), ([0, 1], T), ([0, True, 2], T), ([0, 1, 2], None), ([0, 1, 2], ["a", "b"]), ([0, 1, 2], ["a", "b", "c", "a"]), ([0, 1, 2], ["a", "a", "c"]), ([0, 1, 2], ["a", "", "c"]), ([0, 1, 2], ["a", 2, "c"])]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(greedy_token), "greedy seçim, eşitlik ve token şeması korunmalı")
def m_logit(x, t):
    return greedy_token(list(reversed(x)), t)
def m_token(x, t):
    return greedy_token(x, list(reversed(t)))
def m_sabit(x, t):
    return t[0]
for ad, mutant in [("logitleri bozan", m_logit), ("tokenları bozan", m_token), ("sabit seçim", m_sabit)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle
def greedy_token(logitler, tokenlar):
    import math
    if not isinstance(logitler, list) or len(logitler) != 3 or any(not isinstance(x, (int, float)) or isinstance(x, bool) or not math.isfinite(x) for x in logitler):
        raise ValueError("logitler geçersiz")
    if not isinstance(tokenlar, list) or len(tokenlar) != 3 or any(not isinstance(x, str) or not x for x in tokenlar) or len(set(tokenlar)) != 3:
        raise ValueError("tokenlar geçersiz")
    return tokenlar[max(range(3), key=lambda i: logitler[i])]
if __name__ == "__main__":
    v=json_yukle("veri/logitler.json")
    print("Sentetik veri:",v)
    print("Greedy:",repr(greedy_token(v["logitler"],v["tokenlar"])))

```

```hint
Tokenı doğrudan değil, `max(range(3), key=...)` ile kazanan indeksi bularak seç.
```
:::

::: gorev 3 · Doğru tokenın çapraz entropisini hesapla
`capraz_entropi(logitler, hedef)` işlevini yaz. Logitler ilk görevdeki biçimde, hedef bool olmayan 0, 1 veya 2 tamsayısıdır. Geçersiz veride `ValueError` yükselt.

Kararlı log-sum-exp kullanarak hedef tokenın negatif log olasılığını hesapla ve altı ondalığa yuvarla. Girdiyi değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-03")
```

```starter
from ai_temel_veri import json_yukle
import math

def capraz_entropi(logitler,hedef):
    # KUSURLU BAŞLANGIÇ KODU: önce doğrudan exp alır; büyük logitte taşar ve yuvarlanmış olasılık kaybeder.
    p=[math.exp(x) for x in logitler]
    hedef_p=round(p[hedef]/sum(p),6)
    return round(-math.log(hedef_p),6)

v=json_yukle("veri/logitler.json")
print("Sentetik veri:",v)
print("Kayıp:",capraz_entropi(v["logitler"],v["hedef"]))
```

```test
def sozlesme(fn):
    try:
        if fn([0, 0, 0], 0) != 1.098612 or fn([0, 1, 2], 2) != 0.407606:
            return False
        if fn([1000, 1000, 1000], 1) != 1.098612 or fn([0, 1, 2], 0) != 2.407606:
            return False
        if fn([1e20,1e20,1e20],1)!=1.098612 or fn([-1000,0,1000],1)!=1000.0:
            return False
        for args in [([float("nan"),0,1],0),([float("inf"),0,1],0),(["a",1,2],0),(None, 0), ([0, 1], 0), ([0, True, 2], 0), ([0, 1, 2], -1), ([0, 1, 2], 3), ([0, 1, 2], True), ([0, 1, 2], 0.0)]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(capraz_entropi), "log-sum-exp, hedef ve kayıp hesabı korunmalı")
def m_logit(x, h):
    return capraz_entropi(list(reversed(x)), h)
def m_hedef(x, h):
    return capraz_entropi(x, 2 - h)
def m_boyut(x, h):
    return capraz_entropi(x + [0], h)
for ad, mutant in [("logitleri bozan", m_logit), ("hedefi bozan", m_hedef), ("boyutu bozan", m_boyut)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle
def capraz_entropi(logitler, hedef):
    import math
    if not isinstance(logitler, list) or len(logitler) != 3 or any(not isinstance(x, (int, float)) or isinstance(x, bool) or not math.isfinite(x) for x in logitler):
        raise ValueError("logitler geçersiz")
    if not isinstance(hedef, int) or isinstance(hedef, bool) or not 0 <= hedef < 3:
        raise ValueError("hedef geçersiz")
    tepe = max(logitler)
    log_toplam = math.log(sum(math.exp(x - tepe) for x in logitler))
    return round(log_toplam + (tepe - logitler[hedef]), 6)
if __name__ == "__main__":
    v=json_yukle("veri/logitler.json")
    print("Sentetik veri:",v)
    print("Kayıp:",capraz_entropi(v["logitler"],v["hedef"]))

```

```hint
Kayıp `log(sum(exp(logit))) - logit[hedef]` biçimindedir; toplamı maksimum logit dışarı alınarak hesapla.
```
:::

::: anlat Gerçek deney: gerçek tokenizer, gerçek logit
Şimdiye kadarki logitler elle yazılmış üç sayıydı. Bu adımda **gerçek bir küçük dil modeli** (varsayılan: `HuggingFaceTB/SmolLM2-135M`, Apache-2.0, sabit commit) ve onun **gerçek tokenizer'ı** CPU'da çalışır. `ai_lab.dil_modeli()` yalnız yerel önbellekten yükler; ders sırasında indirme yapmaz, model yoksa açık hata verir ve görev geçmez.

Zincir şudur: metin → tokenizer → token kimlikleri → model ileri hesabı → her konum için sözlük boyu kadar logit → **son konumun** logitleri → sıcaklıkla bölünmüş softmax → sonraki tokenın olasılık dağılımı. Model kimliği, ağırlık dosyasının SHA-256'sı, torch/transformers sürümleri ve cihaz kanıta yazılır. Test her Kontrol'de rastgele metin, `k` ve sıcaklık seçer; sabit bir tabloyu ezberleyen çözüm geçemez.

Kaynaklar: [Goodfellow, Bengio ve Courville — Deep Learning, Bölüm 4: Sayısal Hesaplama (Softmax Taşması)](https://www.deeplearningbook.org/contents/numerical.html), [PyTorch — CrossEntropyLoss ve LogSumExp Belgeleri](https://docs.pytorch.org/docs/stable/generated/torch.nn.CrossEntropyLoss.html).
:::

::: gorev Gerçek deney · Gerçek modelde token kimlikleri, logitler ve olasılıklar
`sonraki_token_dagilimi(metin, k=5, sicaklik=1.0)` işlevini yaz:

- `metin` boşluk dışı en az bir karakter içeren `str`; `k` bool olmayan `int`, 1–20; `sicaklik` bool olmayan, sonlu ve sıfırdan büyük `int`/`float`. Aksi hâlde `ValueError`.
- `tokenizer, model, bilgi = ai_lab.dil_modeli()` ile gerçek modeli al. `token_idleri = tokenizer(metin)["input_ids"]`.
- `torch.no_grad()` içinde modeli çalıştır; **son konumun** logitlerini al, `sicaklik`'a bölüp softmax uygula (float64 önerilir).
- Döndür: `{"token_idleri": [...], "tokenlar": tokenizer.convert_ids_to_tokens(token_idleri), "en_olasi": [...], "olasilik_toplami": float}`. `en_olasi` en yüksek olasılıklı `k` token: her öğe `{"id": int, "metin": tokenizer.decode([id]), "logit": float, "olasilik": float}`, olasılığa göre azalan. `olasilik_toplami` bütün sözlükteki olasılıkların toplamı.

`logit`, sıcaklıkla bölünmemiş ham değerdir. Laboratuvarın referans işlevlerini çağırma.

```meta
motor: ai-gercek
gereksinim: torch
timeout: 240
```

```starter
import ai_lab

def sonraki_token_dagilimi(metin, k=5, sicaklik=1.0):
    return {}

if ai_lab.CALISTIR:
    ai_lab.temel_goster(sonraki_token_dagilimi)
```

```test
import random
import math
import ai_lab
sonuclar = []
def kontrol(kosul, mesaj):
    sonuclar.append(bool(kosul))
    return ok(kosul, mesaj)
import ast
_yasak=("son_logitler","referans_dagilim","kanit_yaz")
sorun=ai_lab.kod_denetimi(src,yasak=_yasak)
for n in ast.walk(ast.parse(src)):
    if isinstance(n,ast.ImportFrom) and any(a.name in _yasak or a.name=="*" for a in n.names):
        sorun.append("referans importu yasak")
if not kontrol(not sorun,"Kendi token dağılımı işlevini yaz: "+"; ".join(sorun)):
    stop()
fn = need("sonraki_token_dagilimi")
try:
    tok, model, bilgi = ai_lab.dil_modeli()
    import torch
except ai_lab.GercekLabYok as e:
    kontrol(False, f"GERÇEK MODEL YOK, deney yapılmadı: {e}")
    stop()
def referans(metin, k, T, konum=-1, softmax=True, sicaklik_kullan=True):
    ids = tok(metin)["input_ids"]
    with torch.no_grad():
        logit = model(torch.tensor([ids])).logits[0, konum].double()
    olc = logit / T if sicaklik_kullan else logit
    p = torch.softmax(olc, dim=0) if softmax else olc
    en = sorted(torch.topk(p, k + 5).indices.tolist(), key=lambda i: (-p[i].item(), i))[:k]
    return {"token_idleri": ids, "tokenlar": tok.convert_ids_to_tokens(ids),
            "en_olasi": [{"id": i, "metin": tok.decode([i]), "logit": logit[i].item(), "olasilik": p[i].item()} for i in en],
            "olasilik_toplami": p.sum().item()}
rnd = random.Random()
sozcuk = ["kedi", "the", "river", "Ankara", "model", "güvenlik", "green", "data", "music", "token"]
metinler = ["The capital of France is", f"{rnd.choice(sozcuk)} {rnd.choice(sozcuk)} {rnd.randint(10, 9999)} and the",
            f"Bugün {rnd.choice(sozcuk)} ile {rnd.choice(sozcuk)}"]
ayarlar = [(m, rnd.randint(3, 8), T) for m, T in zip(metinler, [1.0, rnd.choice([0.5, 0.8]), rnd.choice([1.3, 1.5])])]
ayarlar += [(metinler[0],1,1.0),(metinler[1],20,0.8)]
def ayni(a, b):
    if not isinstance(a, dict) or set(a) != set(b):
        return False
    if a["token_idleri"] != b["token_idleri"] or a["tokenlar"] != b["tokenlar"]:
        return False
    if not isinstance(a["olasilik_toplami"], float) or not math.isfinite(a["olasilik_toplami"]) or abs(a["olasilik_toplami"] - b["olasilik_toplami"]) > 1e-6:
        return False
    if not isinstance(a["en_olasi"], list) or len(a["en_olasi"]) != len(b["en_olasi"]):
        return False
    for x, y in zip(a["en_olasi"], b["en_olasi"]):
        if not isinstance(x, dict) or set(x) != set(y) or x["id"] != y["id"] or x["metin"] != y["metin"]:
            return False
        if not isinstance(x["logit"], float) or not isinstance(x["olasilik"], float) or not math.isfinite(x["logit"]) or not math.isfinite(x["olasilik"]):
            return False
        if abs(x["logit"] - y["logit"]) > 1e-3 or abs(x["olasilik"] - y["olasilik"]) > 1e-5:
            return False
    return True
def sozlesme(f):
    try:
        if not ayni(f(metinler[0]), referans(metinler[0], 5, 1.0)) or not ayni(f(metinler[0], 3), referans(metinler[0], 3, 1.0)):
            return False
        if not all(ayni(f(m, k, T), referans(m, k, T)) for m, k, T in ayarlar):
            return False
        for arg in [("",), ("   ",), (None,), ("a", 0), ("a", 21), ("a", 2.5), ("a", "5"), ("a", True), ("a", 5, 0), ("a", 5, -1.0), ("a", 5, "1.0"), ("a", 5, True), ("a",5,float("nan")), ("a",5,float("inf"))]:
            try:
                f(*arg)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
kontrol(sozlesme(fn), "gerçek model: token kimlikleri, tokenlar, son konum logitleri ve sıcaklıklı softmax doğru")
def gecerli(f):
    def sarmal(m, k=5, T=1.0):
        if not isinstance(m, str) or not m.strip() or isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= 20 \
                or isinstance(T, bool) or not isinstance(T, (int, float)) or not math.isfinite(T) or not T > 0:
            raise ValueError("geçersiz")
        return f(m, k, T)
    return sarmal
sabit = referans(*ayarlar[0])
for ad, mutant in [("ilk konumun logitleri", gecerli(lambda m, k, T: referans(m, k, T, konum=0))),
                   ("softmax yok", gecerli(lambda m, k, T: referans(m, k, T, softmax=False))),
                   ("sıcaklık yok sayılıyor", gecerli(lambda m, k, T: referans(m, k, T, sicaklik_kullan=False))),
                   ("ezber tablo", gecerli(lambda m, k, T: sabit))]:
    kontrol(not sozlesme(mutant), "hatalı çözüm reddedilmeli: " + ad)
def m_sonlu_olmayan(m,k=5,T=1.0):
    d=referans(m,k,T)
    d["olasilik_toplami"]=float("nan")
    for x in d["en_olasi"]:
        x["logit"]=float("nan")
        x["olasilik"]=float("nan")
    return d
kontrol(not sozlesme(gecerli(m_sonlu_olmayan)),"hatalı çözüm reddedilmeli: NaN ile tolerans karşılaştırmasını atlatan")
if not all(sonuclar):
    stop()
ornek = fn(metinler[0], 5, 1.0)
kontrol(tok.decode(ornek["token_idleri"]) == metinler[0], "token kimlikleri gerçek tokenizer'la metne geri çözülüyor")
yol = ai_lab.kanit_yaz("temel-logit", {
    "kaynak": "gercek", "kabul": all(sonuclar), "model_bilgisi": dict(bilgi, model=bilgi["model"]),
    "ayarlar": {"tolerans": {"logit": 1e-3, "olasilik": 1e-5}, "girdiler": [list(a) for a in ayarlar]},
    "ciktilar": [fn(m, k, T) for m, k, T in ayarlar]})
ilk = ornek["en_olasi"][0]
ok(True, f"GERÇEK ÇIKTI ({bilgi['model']}@{bilgi['revizyon'][:8]}): {metinler[0]!r} → {len(ornek['token_idleri'])} token, "
         f"en olası sonraki token {ilk['metin']!r} (id {ilk['id']}, logit {ilk['logit']:.3f}, p={ilk['olasilik']:.4f})")
```

```solution
import torch
import ai_lab
import math

def sonraki_token_dagilimi(metin, k=5, sicaklik=1.0):
    if not isinstance(metin, str) or not metin.strip():
        raise ValueError("metin boş olamaz")
    if isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= 20:
        raise ValueError("k 1-20 arası tamsayı olmalı")
    if isinstance(sicaklik, bool) or not isinstance(sicaklik, (int, float)) or not math.isfinite(sicaklik) or not sicaklik > 0:
        raise ValueError("sıcaklık pozitif olmalı")
    tokenizer, model, _ = ai_lab.dil_modeli()
    ids = tokenizer(metin)["input_ids"]
    with torch.no_grad():
        logit = model(torch.tensor([ids])).logits[0, -1].double()
    p = torch.softmax(logit / sicaklik, dim=0)
    en = sorted(torch.topk(p, k + 5).indices.tolist(), key=lambda i: (-p[i].item(), i))[:k]
    return {"token_idleri": ids, "tokenlar": tokenizer.convert_ids_to_tokens(ids),
            "en_olasi": [{"id": i, "metin": tokenizer.decode([i]), "logit": logit[i].item(), "olasilik": p[i].item()}
                         for i in en],
            "olasilik_toplami": p.sum().item()}

if ai_lab.CALISTIR:
    ai_lab.temel_goster(sonraki_token_dagilimi)
```

```hint
`model(torch.tensor([ids])).logits` biçimi `[1, konum, sözlük]`'tür; sonraki token için `[0, -1]` gerekir. Sıcaklığı softmax'tan önce uygula, `logit` alanına ise bölünmemiş değeri yaz.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Ham skordan olasılığa (`Softmax`) (30 sn).** "Modelin son katmanı eksi veya artı her gerçek sayıyı alabilen `logit` vektörü üretir; kararlı `softmax` önce en büyük logiti çıkarıp ($z_i - \max_j z_j$) üstel taşmayı (`overflow`) önler ve toplamı 1 olan dağılım verir."
2. **Seçim ile kayıp aynı şey değildir (35 sn).** "`Greedy` seçim yalnız en yüksek logitli adayı seçer; çapraz entropi (`cross-entropy`) ise eğitimdeki gerçek hedef tokena verilen negatif log-olasılığı ($-\ln p_{\text{hedef}}$) kararlı `log-sum-exp` ile ölçer."
3. **Yüksek olasılık doğruluk kanıtı değildir (30 sn).** "Modelin bir tokena %99 olasılık vermesi yalnız eğitim dağılımındaki koşullu güvenini gösterir; olgusal doğruluğu ya da güvenlik uygunluğunu garanti etmez."
4. **Soru (25 sn).** "Çapraz entropiyi önce olasılığı 6 ondalığa yuvarlayıp sonra `-math.log(p)` ile hesaplarsan düşük olasılıklı hedef tokenlarda neden çökme veya büyük sapma yaşarsın?"
:::
