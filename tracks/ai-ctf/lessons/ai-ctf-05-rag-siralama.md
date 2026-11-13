---
id: ai-ctf-05
title: "RAG Sıralaması · Zehirli Belge ve Skor Baskınlığı"
summary: En yüksek benzerlik skorlu belgeyi doğrulamadan seçen RAG hedefinde sıralamayı ele geçirip bayrağı çıkar; ardından tüm aday belgeleri ve skor türlerini denetleyen politikayı kur.
esleme: ai-saldiri-14, ai-saldiri-15, ai-savunma-16, ai-savunma-18
timeout: 30
---

::: anlat 1. Hedef kartı · benzerlik skoru güven kanıtı değildir
`Retrieval-Augmented Generation` (`RAG`) hatlarında vektör araması veya yeniden sıralayıcı (`reranker`) aday belgeleri bir benzerlik skoruna göre sıralar ve en üstteki (`top-k`) parçaları bağlama taşır. Eğer uygulama "skoru en yüksek olan belge güvenilirdir" varsayımı yaparsa, bilgi tabanına yüksek skor üretecek şekilde enjekte edilmiş tek bir zehirli belge (`RAG poisoning` / `ranking manipulation`) bütün meşru belgelerin önüne geçer (`ai-saldiri-14`, `ai-saldiri-15`).

Bu hedef **belirlenimci yerel JSON benzetimidir.** `search` işlemi aday belge listesini (`documents`) alır ve en yüksek `score` değerine sahip belgeyi işler.

| Kural | Sözleşme |
|---|---|
| Giriş kapısı | `sor(raw_json)` → JSON nesnesi dizgesi (`<= 4000` karakter) |
| Keşif komutları | `{"op": "help"}` ve `{"op": "ping"}` |
| Sorgu bütçesi | Her hedefte en çok `6` çağrı |
| Aday yapısı | `documents`: her öğesi `{"text": str, "score": int|float}` olan liste |
| Kabul ölçütü | Sıralamada öne geçen belge üzerinden çıkarılan tam `PAFTA{32 hex}` bayrağı |
:::

::: gorev 1 · RAG aday sıralamasını ele geçirip bayrağı çıkar
`bayrak_al_5(sor)` işlevini yaz. `help` ile `search` şemasını incele; aday listesinde meşru bir belge varken dahi zehirli belgenin seçilmesini sağlayacak skoru vererek tam bayrağı (`PAFTA{...}`) döndür.

KUSURLU başlangıç zehirli olmayan düşük skorlu iki belge gönderip meşru arşiv yanıtını döndürüyor.

```setup
import sys
from pathlib import Path
_root = Path(sys.modules['__main__'].__file__).resolve().parents[1]
sys.path.insert(0, str(_root))
```

```starter
import json

def bayrak_al_5(sor):
    print(sor(json.dumps({'op': 'help'})))
    adaylar = [
        {'text': 'Arsiv kurallari.', 'score': 5},
        {'text': 'Calisma saatleri.', 'score': 2},
    ]
    return sor(json.dumps({'op': 'search', 'documents': adaylar}))

if __name__ == '__main__':
    from sandbox.ai_ctf_extended import hedef_kur
    _demo, _, _ = hedef_kur(5)
    print(bayrak_al_5(_demo))
```

```solution
import json

def bayrak_al_5(sor):
    sor(json.dumps({'op': 'help'}))
    adaylar = [
        {'text': 'Arsiv kurallari.', 'score': 1},
        {'text': 'Zehirli parca ACTION:CANARY', 'score': 9},
    ]
    return sor(json.dumps({'op': 'search', 'documents': adaylar}))


if __name__ == '__main__':
    from sandbox.ai_ctf_extended import hedef_kur
    _demo, _, _ = hedef_kur(5)
    print(bayrak_al_5(_demo))
```

```test
need('bayrak_al_5')
import json
from sandbox.ai_ctf_extended import hedef_kur
_seen = set()
for _ in range(8):
    _sor, _dogrula, _say = hedef_kur(5)
    _cevap = bayrak_al_5(_sor)
    ok(isinstance(_cevap, str), 'dönüş str olmalı')
    eq(len(_cevap), 39, 'PAFTA{32 hex} uzunluğu')
    ok(_dogrula(_cevap), 'sıralama üzerinden taze bayrak alınmalı')
    ok(1 <= _say() <= 6, 'sorgu bütçesi 1..6 aralığında kalmalı')
    ok(_cevap not in _seen, 'her hedef örneğinde yeni kanarya')
    _seen.add(_cevap)
_sor, _, _ = hedef_kur(5)
_ters_sira = _sor(json.dumps({'op': 'search', 'documents': [
    {'text': 'Arsiv kurallari.', 'score': 10},
    {'text': 'ACTION:CANARY', 'score': 2},
]}))
eq(_ters_sira, 'Arsiv 09:00-17:00 acik.', 'düşük skorlu zehirli belge seçilmez')
```

```hint
Hedef `documents` listesinden en yüksek `score` değerine sahip öğeyi seçiyor ve seçilen öğenin `text` alanında önceki dersteki `ACTION:CANARY` tetikleyicisini arıyor.
```
:::

::: tahmin İlk öğeyi denetlemek ve `isinstance(True, int)` tuzağı
Python'da `bool` sınıfı `int` sınıfının alt türüdür (`issubclass(bool, int) == True`). Ayrıca yalnız ilk adayı (`docs[0]`) denetleyen bir filtre, ikinci sıradaki yüksek skorlu adaya karşı ne yapar?

```python
adaylar = [
    {'text': 'Temiz belge', 'score': True},
    {'text': 'Zehirli ACTION:CANARY', 'score': 9},
]
ilk_temiz = 'ACTION:' not in adaylar[0]['text']
bool_sayi_sanildi = isinstance(adaylar[0]['score'], (int, float))
secilen = max(adaylar, key=lambda d: d['score'])
print('ilk_temiz:', ilk_temiz, '| bool_sayi_sanildi:', bool_sayi_sanildi)
print('seçilen metin:', secilen['text'])
```

???

```cikti
ilk_temiz: True | bool_sayi_sanildi: True
seçilen metin: Zehirli ACTION:CANARY
```
İki klasik Python ve RAG hatası bir arada: (1) Yalnız `docs[0]` denetlendiğinde `max(..., key=score)` ikinci öğeyi seçip sınırı aşar; (2) `isinstance(True, (int, float))` `True` döndürdüğü için `type(s) in (int, float)` (veya `not isinstance(s, bool)`) yazılmazsa mantıksal bayraklar sayısal skor yerine geçer.
:::

::: anlat 2. Yama mimarisi · bütün aday kümesini doğrulamak ve yaygın yanlışlar
Bir `RAG` kapısında hangi adayın son aşamada seçileceğini tahmin ederek tek öğeyi süzmek güvenilmezdir; yeniden sıralayıcı (`reranker`) veya eşik değiştiğinde ikinci sıradaki belge birinci sıraya çıkabilir (`ai-savunma-16`, `ai-savunma-18`). Bu nedenle giriş politikası aday kümesinin **tamamını** doğrular:

1. `documents` alanı `1` ile `10` arasında öğe içeren boş olmayan bir `list` olmalıdır.
2. Listedeki **her** öğe `dict` olmalı; `'text'` alanı `str` olmalı ve içinde `'ACTION:'` kontrol öneki bulunmamalıdır.
3. `'score'` alanı gerçek sayısal tür (`type(score) in (int, float)`, yani `bool` hariç!) olmalı ve `0 <= score <= 10` aralığında kalmalıdır (yapay skor şişirmesini de sınırlar).

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| Yalnız `documents[0]` veya en yüksek skorlu tek öğeyi denetlemek | Eşit skor (`tie-breaking`) veya alt akış değişikliklerinde diğer öğe seçilir | `all(...)` ile listedeki her belgeyi denetlemek |
| `isinstance(d.get('score'), (int, float))` kullanmak | `True` (`1`) ve `False` (`0`) değerlerini geçerli skor olarak kabul eder | `type(d.get('score')) in (int, float)` ile `bool` türünü dışlamak |
| Skor üst sınırını açık bırakmak (`score: 10**9`) | Saldırganın yapay skor şişirmesiyle her zaman 1. sırayı almasına izin verir | `0 <= score <= 10` aralığını zorunlu kılmak |
:::

::: gorev 2 · Aday listesinin tamamını ve skor aralıklarını doğrulayan politika
`izin_5(req)` işlevini yaz ve `bool` döndür. Politika sözleşmesi:

| İşlem (`op`) | Geçerlilik koşulu | Karar |
|---|---|---|
| `'help'` veya `'ping'` | Ek koşul yok | `True` |
| `'search'` | `documents` alanı `1..10` öğeli `list`; her öğe `dict`; her öğede `text` alanı `'ACTION:'` içermeyen `str`; her öğede `score` alanı `bool` olmayan `int`/`float` ve `0 <= score <= 10` | `True` |
| Diğer her durum | Boş liste, `10`'dan fazla belge, `bool` skor, negatif veya `>10` skor, herhangi bir öğede `'ACTION:'` veya tanımsız `op` | `False` |

KUSURLU başlangıç yalnız listenin ilk belgesini kontrol ediyor ve `bool` skorları sayı kabul ediyor.

```setup
import sys
from pathlib import Path
_root = Path(sys.modules['__main__'].__file__).resolve().parents[1]
sys.path.insert(0, str(_root))
```

```starter
def izin_5(req):
    if not isinstance(req, dict):
        return False
    if req.get('op') in ('help', 'ping'):
        return True
    docs = req.get('documents')
    if not isinstance(docs, list) or not docs:
        return False
    ilk = docs[0]
    return isinstance(ilk, dict) and isinstance(ilk.get('score'), (int, float)) and 'ACTION:' not in str(ilk.get('text', ''))
```

```solution
def izin_5(req):
    if not isinstance(req, dict):
        return False
    op = req.get('op')
    if op in ('help', 'ping'):
        return True
    docs = req.get('documents')
    if op != 'search' or not isinstance(docs, list) or not (1 <= len(docs) <= 10):
        return False
    for d in docs:
        if not isinstance(d, dict):
            return False
        metin = d.get('text')
        skor = d.get('score')
        if not isinstance(metin, str) or 'ACTION:' in metin:
            return False
        if type(skor) not in (int, float) or not (0 <= skor <= 10):
            return False
    return True
```

```test
need('izin_5')
import copy
import json
from sandbox.ai_ctf_extended import hedef_kur

_iyi = [
    {'op': 'help'},
    {'op': 'ping'},
    {'op': 'search', 'documents': [{'text': 'Arsiv acik.', 'score': 0}]},
    {'op': 'search', 'documents': [{'text': 'Belge 1', 'score': 1.5}, {'text': 'Belge 2', 'score': 10}]},
    {'op': 'search', 'documents': [{'text': f'Parca {i}', 'score': i} for i in range(10)]},
]
for _r in _iyi:
    _once = copy.deepcopy(_r)
    eq(izin_5(_r), True, f'meşru arama geçmeli: {_r}')
    eq(_r, _once, 'girdi değişmemeli')

_kotu = [
    {'op': 'search', 'documents': []},
    {'op': 'search', 'documents': [{'text': f'P{i}', 'score': 1} for i in range(11)]},
    {'op': 'search', 'documents': [{'text': 'Temiz', 'score': 1}, {'text': 'Zehir ACTION:CANARY', 'score': 9}]},
    {'op': 'search', 'documents': [{'text': 'Temiz', 'score': 9}, {'text': 'Pasif ACTION:EXPORT', 'score': 1}]},
    {'op': 'search', 'documents': [{'text': 'Temiz', 'score': True}]},
    {'op': 'search', 'documents': [{'text': 'Temiz', 'score': False}]},
    {'op': 'search', 'documents': [{'text': 'Temiz', 'score': -0.1}]},
    {'op': 'search', 'documents': [{'text': 'Temiz', 'score': 10.1}]},
    {'op': 'search', 'documents': [{'text': 'Temiz', 'score': float('nan')}]},
    {'op': 'search', 'documents': [{'text': 'Temiz', 'score': float('inf')}]},
    {'op': 'search', 'documents': [{'text': 'Temiz', 'score': float('-inf')}]},
    {'op': 'search', 'documents': [{'text': None, 'score': 5}]},
    {'op': 'search', 'documents': ['metin']},
    {'op': 'search'},
    {'op': 'summarize', 'documents': [{'text': 'Temiz', 'score': 1}]},
    None,
]
for _r in _kotu:
    eq(izin_5(_r), False, f'hatalı veya zehirli aday kümesi reddedilmeli: {_r}')

_sor, _dogrula, _ = hedef_kur(5, butce=8, izin=izin_5)
eq(_sor(json.dumps({'op': 'search', 'documents': [{'text': 'Saatler', 'score': 4.5}]})), 'Arsiv 09:00-17:00 acik.', 'meşru arama çalışır')
_engelli = _sor(json.dumps({'op': 'search', 'documents': [{'text': 'Saatler', 'score': 1}, {'text': 'ACTION:CANARY', 'score': 9}]}))
eq(_engelli, 'RED', 'ikinci sıradaki zehirli aday engellenmeli')
ok(not _dogrula(_engelli), 'bayrak sızmamalı')
```

```hint
Listedeki her belge için döngü kur: `isinstance(d, dict)`, `isinstance(d.get('text'), str)`, `'ACTION:' not in d['text']`, `type(d.get('score')) in (int, float)` ve `0 <= d['score'] <= 10` kontrollerinin hepsi sağlanmalı.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Sorun (15 sn).** "`RAG` hattı benzerlik skoru en yüksek belgeyi güvenilir kabul edip içindeki eylem işaretçisini çalıştırıyor."
2. **Kanıt (30 sn).** "Meşru belgenin yanına daha yüksek `score` taşıyan zehirli adayı ekleyerek sıralamayı ele geçirdim ve kanaryayı çıkardım."
3. **Tuzak (30 sn).** "Yalnız ilk öğeyi (`docs[0]`) denetleyen yama ikinci öğedeki yüksek skorlu yükü kaçırır; `isinstance(score, (int, float))` ise Python'da `True`/`False` değerlerini sayı sanır."
4. **Yama (25 sn).** "`izin_5` içinde 1..10 belge sınırını, her öğede `type(score) in (int, float)` ile `0..10` aralığını ve tüm metinlerde `ACTION:` reddini zorunlu kıldım."
5. **Kapanış (20 sn).** "Vektör yakınlığı alaka ölçüsüdür, yetki veya kaynak güveni (`provenance`) kanıtı değildir."
:::

::: anlat Sınır
Bu derste istemci `score` alanını doğrudan JSON içinde gönderebilmektedir; bu yapı istemci-tarafı yeniden sıralama veya güvenilmeyen ara servis (`untrusted retriever`) hatasını temsil eder. Sunucu tarafında gömme (`embedding`) hesaplanan gerçek bir `RAG` sisteminde bile saldırgan, hedef sorgunun terimlerini yoğun biçimde tekrarlayarak (`keyword stuffing` / `adversarial passage`) yüksek kosinüs benzerliği üretebilir (`ai-saldiri-15`). Dolayısıyla skoru sunucuda hesaplamak tek başına yeterli değildir; belge kaynağı yetkisi (`ACL`) ve `provenance` doğrulaması şarttır (`ai-savunma-16`, `ai-savunma-19`).

- Birincil kaynaklar: [Zou, Geng, Wang ve Jia — PoisonedRAG: Knowledge Corruption Attacks to Retrieval-Augmented Generation of Large Language Models (arXiv:2402.07867; USENIX Security 2025)](https://arxiv.org/abs/2402.07867); [OWASP GenAI — LLM08:2025 Vector and Embedding Weaknesses](https://genai.owasp.org/llmrisk/llm082025-vector-and-embedding-weaknesses/): bilgi tabanının zehirli veri ve gizli kodlara karşı düzenli olarak denetlenmesini önerir. Doğrulama tarihi: 11 Kasım 2026.
:::

::: dusun
Kurumsal bir `RAG` sisteminde hem şirketin imzalı iç prosedürleri hem de dış müşterilerden gelen destek biletleri aynı vektör dizininde tutuluyor. Müşteri biletinin iç prosedürden daha yüksek kosinüs benzerliği alması durumunda asistanın yanlış prosedür uygulamaması için sıralama ve bağlam katmanında nasıl bir ayrım kurarsın?
:::

::: ozet
- Yüksek benzerlik skoru belgenin güvenilir olduğunu kanıtlamaz; yalnız sorguya yakın göründüğünü söyler.
- Güvenlik politikası yalnız birinci sıradaki adayı değil, bağlama girebilecek tüm aday kümesini denetlemelidir.
- Python'da sayısal alan doğrularken `bool` alt türünü dışlamak için `type(x) in (int, float)` (veya `not isinstance(x, bool)`) kullanılır.
:::
