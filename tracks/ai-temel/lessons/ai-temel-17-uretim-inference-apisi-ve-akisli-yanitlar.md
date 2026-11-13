---
id: ai-temel-17
title: "Üretim Tipi Inference API’si ve Akışlı Yanıtlar"
summary: Sohbet isteğini bağlam bütçesine göre kabul et, SSE akışını eksiksiz ayrıştır ve sürekli batching zamanlayıcısını benzet; son adımda yerel Ollama'nın NDJSON akışını çözüp TTFT'yi ve num_predict kesmesini gerçek sunucuda ölç.
esleme: ai-temel-08, ai-temel-20, ai-uretim-10
timeout: 45
---

::: anlat Kabul denetimi isteği kuyruğa girmeden önce sınırlar

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Yerel inference sunucusu akış parçaları ve tamamlanma metrikleri üretir | İlk üç görev sentetik istek/SSE/FIFO dosyaları; final gerçek Ollama NDJSON, dört ardışık ve iki eşzamanlı HTTP isteği | SSE ile Ollama NDJSON aynı protokol değildir; ilk görev gerçek tokenizer değildir |
| Üretim zamanlayıcıları kaynakları ve kuyrukları yönetir | Slot/FIFO/deadline benzetimi ve gerçek istemci eşzamanlılık zaman çizelgesi | vLLM/llama.cpp kurulumu, iç sürekli batching, backend KV yalıtımı ve üretim ölçek kabulü yapılmış sayılmaz |

> [!NOT]
> `veri/istekler.json`, `veri/openai_sse.txt` ve `veri/openai_sse_yarim.txt` elle yazılmış sentetik örneklerdir; canlı sunucudan kaydedilmemiştir. Setup her Run/Check için geçici kopya oluşturur; değişiklikler kalıcı değildir. Kaynak dosyaları editörde aç veya koddan yüklenen kopyayı değiştirip Run ile dene. Gizli testler ayrıdır. Son adım kurulu yerel Ollama'yı gerçekten çağırır; yeni model/araç indirmez.

OpenAI uyumlu yerel sunucular (`vllm serve` ile açılan vLLM sunucusu ve llama.cpp'nin `llama-server` programı) `/v1/chat/completions` uç noktasında `model`, `messages`, `max_tokens` ve `stream` gibi alanlar alır. Kabul denetimi bu alanları istek zamanlayıcıya ulaşmadan doğrular: model kimliği izinli listede olmalı, her mesaj `role` ve `content` taşımalı, `max_tokens` pozitif bir tam sayı olmalıdır. Belirleyici kural bağlam penceresidir: istem tokenları ile `max_tokens` toplamı modelin bağlam uzunluğunu aşamaz. vLLM bu sınırı `--max-model-len` ile alır ve aşan isteği üretime başlamadan HTTP 400 ile reddeder; llama.cpp'de `-c` ile verilen bağlam `-np`/`--parallel` slotları arasında paylaşılır ve slot başına düşen pay sürüme göre değiştiği için sınırı sunucunun bildirdiği değerden okumak gerekir. Sohbet şablonu (chat template) her mesajın çevresine rol ve ayraç tokenları ekler, sonuna da yanıtı başlatan bir üretim istemi koyar; yalnız içerik kelimelerini sayan istemci bütçeyi olduğundan küçük hesaplar.

Kabul denetimi gevşekse tek bir istek devasa bir mesaj listesi veya sınırsız `max_tokens` ile GPU zamanını ve önbellek belleğini tekelleştirir; OWASP LLM Top 10 (2025) bunu LLM10 "Unbounded Consumption" başlığında toplar. Bu yüzden ucuz yapısal denetim önce, token bütçesi sonra gelir ve bütçeyi aşan istek sessizce kırpılmaz, reddedilir; kırpma istemcinin beklemediği `length` bitişleri üretir. Zaman aşımı iki ayrı saatle ölçülür: toplam süre sınırı (deadline) ve akışta iki parça arasındaki boşluk sınırı. Yalnız boşluk sınırı olan istemci yavaş ama sürekli damlayan bir yanıtı sonsuza kadar bekler, yalnız toplam sınırı olan istemci ise takılan bağlantıyı geç fark eder. Bu derste vLLM veya llama.cpp çalıştırılmaz: token sayımı "boşlukla ayrılmış kelime + mesaj başına 4 şablon tokenı + üretim istemi için 2 token" biçiminde sentetik bir kuraldır, gerçek tokenizer ve şablonlar modele göre farklı sayılar üretir ve zaman duvar saatiyle değil adım numarasıyla temsil edilir.
:::

::: anlat Sürekli batching ve akış isteği adım adım yönetir

Önce görünür dosyaları incele. `istekler.json` izinli model adlarını, bağlam sınırını, sohbet isteğini ve zamanlayıcı işlerini taşır. Bu adlar örnek kimliklerdir; kurulu modele otomatik yönlendirilmez. İlk görev sohbet isteğinin yapısını ve sentetik bütçesini doğrular, üçüncü görev aynı dosyadaki işleri slotlara yerleştirir. İkinci görev `openai_sse.txt` dosyasını olduğu gibi okur. Yorum satırı, boş olay ve yalnız ilk boşluğun atılması veri üzerinde görülebilir. Tam ve yarım dosyayı karşılaştır: aynı içerik gelmiş olsa bile kapanış işareti işlenmemişse `tamam=False` kalır. Dosyayı strip ile temizlemek olay sınırını veya anlamlı boşluğu kaybettirebilir.

SSE genel bir olay taşıma biçimidir; görevdeki chat chunk şeması bunun üstünde bir uygulama sözleşmesidir. Öğretim ayrıştırıcısı standarttaki bütün alanları ve satır sonlarını desteklemez. Bu kısıt bilinçlidir; gerçek bir EventSource yerine kullanılmamalıdır. Ollama'nın yerel generate akışıysa her satırında bir JSON nesnesi taşır: data öneki ve DONE metni yoktur. Bitiş `done=True` ile, üretilen token sayısı `eval_count` ile gelir. Satır sayısını token sayısı sanma; boş içerikli veya birden çok karakter içeren parçalar olabilir. Gerçek finalin TTFT alanı ilk `done=False` NDJSON parçasının gelişidir; parça boş da olabilir. Bu bir ilk yanıt parçası gecikmesi vekilidir, cihazdaki ilk token çekirdeğinin kesin zaman ölçümü değildir.

İstemci zaman çizelgesi istekten önce başlayan monoton saatle tutulur. Soğuk model yükleme ve sunucu kuyruğu ilk parçaya kadar geçen süreye dahil olabilir; sıcak ve soğuk koşuları doğrudan aynı performans sonucu gibi yorumlama. Son parçanın geliş süresi, `done=True` bitiş nesnesinin toplam süresi ve sunucunun eval_duration değeri farklı saatlerdir. token/sn hesaplamasında sunucunun değerlendirme süresi kullanılır; istemcinin bütün uçtan uca süresiyle aynı ölçüm değildir. Birinci görevin kelime sayısı da gerçek tokenizer sayısı değildir; sohbet şablonları dahil gerçek bütçe için ilgili modelin tokenizer ve şablonu gerekir.

Sürekli batching benzetimi gerçek GPU zamanlayıcısını çalıştırmaz. Her adımda önce FIFO kabulü, sonra bir token üretimi ve bitiş uygulanır; boşalan slot sonraki adımda kullanılır. Deadline hem aktif hem bekleyen istek için geçerlidir. Aynı anda hedefe ulaşan ve deadline'a gelen iş tamam sayılır. Sıra değişirse kısa bir istek bir adım erken başlayıp yanlış sonuç verebilir. Öğrenci slot sayısını değiştirerek kuyruğu gözler ama buradan gerçek model hızlanma katsayısı çıkaramaz; prefill, KV blokları ve gerçek token bütçesi benzetimde yoktur.

Final önce dört gerçek akış isteğini ardışık, sonra iki isteği istemci iş parçacıklarında birlikte başlatır. Her isteğin başlangıç/bitiş aralığı ve ham NDJSON kayıtları kanıtta kalır. İstemci aralıklarının çakışması aynı anda açık HTTP çağrılarını gösterir. Sunucu bunları sıraya koyabilir; bu gözlem iki isteğin GPU'da aynı decode adımında yürüdüğünü kanıtlamaz. İç batching kabulü ayrı backend telemetrisi ve uygun sunucu deneyi gerektirir. Kapsam ve kalan sınırlar TEMEL-17-SUNUCU-KAPSAMI.md dosyasında da yazılıdır.

Bir taşıma hatası varken diğer isteklerin başarılı olması tüm deneyi başarılı yapmaz. Altı planlı isteğin tamamı hatasız bitmeli; ham yanıtlar öğrencinin ayrıştırıcısıyla ve bağımsız hesapla aynı olmalıdır. Boş/sabit sonuçlar, ilk yerine son parçanın gecikmesini döndüren veya parça sayısını token diye veren çözümler reddedilir. Üretilen cümlenin sabit bir metne eşit olması istenmez. Sonuç model sürümüne, cihaza, istemlere ve örnekleme ayarlarına bağlıdır. Zaman çizelgesi bu bilgisayardaki sınırlı gözlemdir, genel performans veya hizmet güvencesi değildir.

Kaynaklar: [Ollama generate API](https://docs.ollama.com/api/generate) ve [WHATWG SSE ayrıştırma standardı](https://html.spec.whatwg.org/multipage/server-sent-events.html#parsing-an-event-stream). İlk kaynak gerçek API alanlarını, ikinci kaynak genel olay biçimini tanımlar; dersin katı altkümesi ayrıca görev sözleşmesinde yazılıdır.

Statik batching bir grup isteği birlikte başlatır ve en uzun dizi bitene kadar bütün slotları tutar; kısa yanıtı biten slot boşta bekler. Orca (Yu ve diğ., OSDI 2022) ile yaygınlaşan yineleme düzeyinde zamanlamada her çözme (decode) adımında biten diziler çıkarılır ve kuyrukta bekleyenler boşalan yerlere alınır; vLLM bu sürekli batching yaklaşımını kullanır. vLLM'de `--max-num-seqs` bir adımdaki eşzamanlı dizi sayısını, `--max-num-batched-tokens` bir adımda işlenen token sayısını sınırlar. Slotlar doluyken gelen istek kuyrukta bekler ve süre sınırı kuyrukta da işler; bu nedenle bir istek tek token üretmeden zaman aşımına uğrayabilir. Zamanlayıcıyı adım adım benzetmek, bir saldırganın uzun istekleri art arda göndererek kısa istekleri kuyrukta zaman aşımına düşürmesinin nasıl görüneceğini de açıklar. Bu derste vLLM zamanlayıcısı çalıştırılmaz; görevdeki benzetim prefill, KV blokları ve token bütçesini yok sayıp yalnız slot sayısını, FIFO kabulünü ve süre sınırını modeller.

`"stream": true` istendiğinde yanıt Server-Sent Events (SSE) olarak gelir: bir olay bir veya daha çok `data:` satırı ve onu bitiren boş satırdır, aynı olaydaki `data:` değerleri `\n` ile birleştirilir, `data:` sonrasındaki tek boşluk atılır ve `:` ile başlayan satırlar canlı tutma için kullanılan yorumlardır. OpenAI uyumlu sunucularda her olay bir `chat.completion.chunk` JSON nesnesidir; metin `choices[0].delta.content` içinde parça parça gelir, son parçada `finish_reason` çoğunlukla `stop` (doğal bitiş) veya `length` (`max_tokens` sınırı) olur, araç çağrısında `tool_calls`, içerik filtresinde `content_filter` de görülebilir ve akış `data: [DONE]` ile kapanır. OpenAI API'sinde ve bunu destekleyen sunucularda `stream_options` içinde `include_usage` açıkken `[DONE]` öncesinde `choices` listesi boş, `usage` alanı dolu ek bir parça gelir. `[DONE]` gelmeden kopan akış eksik yanıttır; onu tam yanıt gibi işlemek yarım bir JSON'u veya kesilmiş bir talimatı sonraki adıma taşır. Sunucu tarafında istemci koptuğunda üretim durdurulmalıdır, yoksa terk edilmiş istekler slotları ve KV bloklarını tüketmeye devam eder: FastAPI'de `StreamingResponse` üretecinin içinde `await request.is_disconnected()` denetlenir, vLLM'in OpenAI sunucusu da kopan isteği motor tarafında iptal eder. Görevler 1–3 ağ bağlantısı kurmadan sentetik dosyaları işler; final yerel Ollama HTTP akışlarını gerçekten çağırır. FastAPI çalıştırılmaz; görevdeki ayrıştırıcı bilerek katıdır: gerçek SSE istemcileri `event:`, `id:` ve `retry:` alanlarını da işler, tanımadıkları alanları yok sayar, CR ve CRLF satır sonlarını da kabul eder, burada ise yalnız `data:`, yorum ve boş satırlar ile `stop`/`length` bitişleri geçerlidir.
:::

::: tahmin Bütçe, SSE, batching ve süre sınırı sonucunu tahmin et
Dört çıktı satırını yaz:

```python
mesajlar = ["Sen yardımcı bir asistansın", "Merhaba"]
istem = sum(len(m.split()) + 4 for m in mesajlar) + 2
print(istem, 32 - istem)
deger = "data:  [DONE]"[5:].removeprefix(" ")
print(repr(deger), deger == "[DONE]")
hedef = [6, 1, 1, 1]
print(max(hedef[:2]) + max(hedef[2:]), max(hedef[0], sum(hedef[1:])))
damla, takilan = [2, 4, 6, 8, 10, 12], [1, 2, 9]
print([(max(b - a for a, b in zip([0] + z, z)) > 3, z[-1] > 10) for z in (damla, takilan)])
```

???

```cikti
15 17
' [DONE]' False
7 6
[(False, True), (True, False)]
```

İlk satır sentetik istem bütçesidir: 4 ve 1 kelimeye mesaj başına 4 şablon tokenı ve 2 üretim istemi tokenı eklenince 15 olur, 32 tokenlık bağlamda en çok 17 token üretilebilir. İkinci satır SSE'de yalnız ilk boşluğun atıldığını gösterir; iki boşluklu satır `[DONE]` sonlandırıcısı değildir. Üçüncü satır iki slotlu sunucuda dört isteğin süresidir: statik batching `[6, 1]` grubunu 6, `[1, 1]` grubunu 1 adımda bitirip toplam 7 adım harcar; sürekli batching'de ikinci slot üç kısa isteği art arda alır ve iş 6 adımda biter. Dördüncü satır iki saati ayırır: listeler parçaların geldiği adımlardır, her demet (boşluk sınırı 3 aşıldı mı, toplam sınır 10 aşıldı mı) sorusunu yanıtlar. İki adımda bir damlayan akış boşluk sınırını hiç aşmaz ama 12. adımda toplam sınıra takılır; 2. adımdan sonra 9. adıma kadar susan akış ise toplam sınırın içinde kalsa da 7 adımlık boşlukla yakalanır.
:::

::: gorev 1 · Sohbet isteğini bağlam bütçesine göre kabul et
`istek_dogrula(istek, modeller, baglam)` işlevini yaz; bu `/v1/chat/completions` biçimini izleyen sınırlı sentetik bir isteğin kabul denetimidir. `modeller` izinli model kimliklerinin listesidir: öğeleri boş olmayan ve yinelenmeyen stringlerdir. `baglam` 16–32768 aralığında bir tam sayıdır (bool olamaz) ve `--max-model-len` karşılığıdır. `istek` bir sözlüktür: `model` ve `messages` anahtarları zorunlu, `max_tokens` ve `stream` anahtarları isteğe bağlıdır, başka anahtar olamaz. `model` değeri `modeller` içinde olmalıdır.

`messages` 1–64 öğeli bir listedir; her öğe tam `role` ve `content` anahtarlı bir sözlüktür, `role` `system`, `user` veya `assistant` olur, `content` en az bir boşluk dışı karakter içeren bir stringdir. Sentetik sayım: her mesaj `len(content.split())` + 4 şablon tokenı tutar, toplama üretim istemi için 2 eklenir; sonuç `istem_tokenlari` değeridir. `max_tokens` verildiyse en az 1 olan bir tam sayı (bool olamaz) olmalı ve `istem_tokenlari + max_tokens <= baglam` sağlanmalıdır; verilmediyse `baglam - istem_tokenlari` kullanılır ve bu değer de en az 1 olmalıdır. Bütçeyi aşan istek kırpılmaz, reddedilir. `stream` verildiyse bool olmalıdır, verilmediyse `False` kabul edilir. Geçersiz veride `ValueError` yükselt.

Tam `model`, `messages`, `max_tokens`, `stream`, `istem_tokenlari` anahtarlı yeni bir sözlük döndür; `messages` aynı sırada, yalnız `role` ve `content` içeren yeni sözlüklerden oluşan yeni bir liste olmalıdır; `role` ve `content` değerleri aynen (boşlukları kırpılmadan) kopyalanır. Girdileri değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-17")
```

```starter
from ai_temel_veri import json_yukle
def istek_dogrula(istek, modeller, baglam):
    # KUSURLU BAŞLANGIÇ KODU: şablon tokenlarını yok sayar, taşan isteği sessizce kırpar.
    import copy
    istem=sum(len(m["content"].split()) for m in istek["messages"])
    return dict(copy.deepcopy(istek),max_tokens=min(istek.get("max_tokens",baglam-istem),baglam-istem),stream=istek.get("stream",False),istem_tokenlari=istem)

v=json_yukle("veri/istekler.json")
print("Sentetik istek:",v["istek"])
print("Kabul:",istek_dogrula(v["istek"],v["modeller"],v["baglam"]))
```

```test
import copy
M = ["yerel-sohbet-7b", "yerel-kod-1b"]
def istek(**ek):
    i = {"model": "yerel-sohbet-7b", "messages": [{"role": "system", "content": "Kısa yanıt ver"}, {"role": "user", "content": "Sürekli batching nedir"}]}
    i.update(ek)
    return i
def mesaj(n, metin="a"):
    return [{"role": "user", "content": metin} for _ in range(n)]
def sozlesme(fn):
    try:
        g = istek(max_tokens=48)
        kopya = copy.deepcopy(g)
        r = fn(g, M, 64)
        if r != {"model": "yerel-sohbet-7b", "messages": kopya["messages"], "max_tokens": 48, "stream": False, "istem_tokenlari": 16}:
            return False
        if g != kopya or r["messages"] is g["messages"] or any(a is b for a, b in zip(r["messages"], g["messages"])):
            return False
        g2 = istek()
        k2 = copy.deepcopy(g2)
        fn(g2, M, 64)
        if g2 != k2:
            return False
        if fn(istek(stream=True), M, 100) != {"model": "yerel-sohbet-7b", "messages": kopya["messages"], "max_tokens": 84, "stream": True, "istem_tokenlari": 16}:
            return False
        if fn(istek(), M, 17)["max_tokens"] != 1 or fn(istek(max_tokens=1, stream=False), M, 17)["max_tokens"] != 1:
            return False
        k = {"model": "yerel-kod-1b", "messages": [{"role": "assistant", "content": "a b"}]}
        if fn(k, M, 16) != {"model": "yerel-kod-1b", "messages": [{"role": "assistant", "content": "a b"}], "max_tokens": 8, "stream": False, "istem_tokenlari": 8}:
            return False
        w = {"model": "yerel-kod-1b", "messages": mesaj(1, "  çok   boşluklu\tmetin\n")}
        rw = fn(w, M, 20)
        if rw["istem_tokenlari"] != 9 or rw["messages"] != w["messages"] or rw["messages"][0] is w["messages"][0]:
            return False
        if fn({"model": "yerel-kod-1b", "messages": mesaj(64)}, M, 32768)["istem_tokenlari"] != 322:
            return False
        if fn({"model": "yerel-kod-1b", "messages": mesaj(1), "max_tokens": 32761}, M, 32768)["max_tokens"] != 32761:
            return False
        T = istek()
        for args in [(None, M, 64), ([T], M, 64), ({"messages": T["messages"]}, M, 64), ({"model": "yerel-kod-1b"}, M, 64), (istek(temperature=0), M, 64),
                     (istek(model="baska-model"), M, 64), (istek(model=None), M, 64), (istek(messages=None), M, 64), (istek(messages=tuple(T["messages"])), M, 64),
                     (istek(messages=[]), M, 64), ({"model": "yerel-kod-1b", "messages": mesaj(65)}, M, 32768), (istek(messages=[["role", "content"]]), M, 64), (istek(messages=["a"]), M, 64),
                     (istek(messages=[{"role": "user"}]), M, 64), (istek(messages=[{"role": "user", "content": "a", "name": "x"}]), M, 64),
                     (istek(messages=[{"role": "tool", "content": "a"}]), M, 64), (istek(messages=mesaj(1, "")), M, 64), (istek(messages=mesaj(1, " \t\n")), M, 64),
                     (istek(messages=mesaj(1, b"a")), M, 64), (istek(messages=mesaj(1, 5)), M, 64),
                     (istek(max_tokens=49), M, 64), (istek(max_tokens=0), M, 64), (istek(max_tokens=-1), M, 64), (istek(max_tokens=True), M, 64),
                     (istek(max_tokens=2.0), M, 64), (istek(max_tokens="4"), M, 64), (istek(max_tokens=None), M, 64), (istek(), M, 16),
                     ({"model": "yerel-kod-1b", "messages": mesaj(1), "max_tokens": 32762}, M, 32768),
                     (istek(stream="true"), M, 64), (istek(stream=1), M, 64), (istek(stream=None), M, 64),
                     (istek(), None, 64), (istek(), tuple(M), 64), (istek(), [], 64), (istek(), M + M, 64), (istek(model=""), [""], 64), (istek(), [5] + M, 64),
                     (k, M, 15), (k, M, 32769), (istek(), M, True), (istek(), M, 64.0), (istek(), M, "64"), (istek(), M, None)]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(istek_dogrula), "kabul kuralları, şablon yükü ve bağlam bütçesi korunmalı")
def m_sablon(i, m, b):
    return istek_dogrula(i, m, b + 4 * len(i["messages"]) + 2)
def m_kirp(i, m, b):
    try:
        return istek_dogrula(i, m, b)
    except ValueError:
        return istek_dogrula({a: d for a, d in i.items() if a != "max_tokens"}, m, b)
def m_model(i, m, b):
    return istek_dogrula(i, list(m) + ["baska-model"], b)
for ad, mutant in [("şablon yükünü yok sayan", m_sablon), ("taşan isteği kırpan", m_kirp), ("model allowlist'ini genişleten", m_model)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle
def istek_dogrula(istek, modeller, baglam):
    if not isinstance(modeller, list) or any(not isinstance(m, str) or not m for m in modeller) or len(set(modeller)) != len(modeller):
        raise ValueError("modeller")
    if type(baglam) is not int or not 16 <= baglam <= 32768:
        raise ValueError("bağlam")
    if not isinstance(istek, dict) or not {"model", "messages"} <= set(istek) <= {"model", "messages", "max_tokens", "stream"} or istek["model"] not in modeller:
        raise ValueError("istek")
    mesajlar = istek["messages"]
    if not isinstance(mesajlar, list) or not 1 <= len(mesajlar) <= 64:
        raise ValueError("mesajlar")
    istem, temiz = 2, []
    for m in mesajlar:
        if not isinstance(m, dict) or set(m) != {"role", "content"} or m["role"] not in ("system", "user", "assistant") or not isinstance(m["content"], str) or not m["content"].split():
            raise ValueError("mesaj")
        istem += len(m["content"].split()) + 4
        temiz.append({"role": m["role"], "content": m["content"]})
    akis = istek.get("stream", False)
    cikti = istek.get("max_tokens", baglam - istem)
    if type(akis) is not bool or type(cikti) is not int or cikti < 1 or istem + cikti > baglam:
        raise ValueError("bütçe")
    return {"model": istek["model"], "messages": temiz, "max_tokens": cikti, "stream": akis, "istem_tokenlari": istem}

if __name__ == "__main__":
    v=json_yukle("veri/istekler.json")
    print("Sentetik istek:",v["istek"])
    print("Kabul:",istek_dogrula(v["istek"],v["modeller"],v["baglam"]))
```

```hint
Önce yapıyı (anahtar kümeleri, türler, roller) doğrula, sonra kelime sayısına mesaj başına şablon yükünü ekleyerek istem bütçesini hesapla. `max_tokens` yoksa varsayılanı kalan bağlamdan türet; sonra iki durumu aynı bütçe denetiminden geçir. `bool` bir `int` alt sınıfı olduğu için tür denetiminde `type(x) is int` kullan.
```
:::

::: gorev 2 · SSE akışını parçalardan yanıta birleştir
`sse_ayristir(akis)` işlevini yaz. `akis` 1–20000 karakterlik bir stringdir ve satırlar yalnız `\n` ile ayrılır; `\r` veya ` ` gibi diğer karakterler satır sonu sayılmaz. Satırları sırayla işle: `:` ile başlayan satır yorumdur ve atlanır. `data:` ile başlayan satırın değeri önekten sonraki metindir; değer boşlukla başlıyorsa yalnız ilk boşluk atılır ve değer olayın veri tamponuna eklenir. Hiç karakter içermeyen boş satır olayı bitirir (yalnız boşluk içeren satır boş sayılmaz): tampon doluysa öğeleri `\n` ile birleştirilip olay işlenir ve tampon boşaltılır, tampon boşsa hiçbir şey olmaz. Bunların dışındaki her satır geçersizdir. Akış boş satırla bitmezse tampondaki yarım olay işlenmeden atılır.

Olay verisi tam olarak `[DONE]` ise akış tamamlanır; daha önce bitiş nedeni gelmemişse bu geçersizdir. `[DONE]` işlendikten sonra gelen her `data:` satırı geçersizdir (yorum ve boş satır gelebilir). Diğer olay verisi bir JSON nesnesi olmalıdır: `choices` tam bir öğeli bir listedir; bu öğe `delta` anahtarında bir sözlük taşıyan ve `finish_reason` anahtarı bulunan bir sözlüktür; `finish_reason` `null`, `"stop"` veya `"length"` olur. `delta` içinde `content` yoksa veya `null` ise parça boş metin sayılır, varsa string olmalıdır; `delta` içindeki diğer anahtarlar (`role` gibi) yok sayılır. `finish_reason` değeri `null` olmayan bir parçadan sonra yalnız `[DONE]` gelebilir. Geçersiz veride (bozuk JSON dahil) `ValueError` yükselt.

`{"metin": ..., "bitis": ..., "tamam": ...}` döndür: `metin` içerik parçalarının geliş sırasıyla birleşimi, `bitis` gelen bitiş nedeni ya da gelmediyse `None`, `tamam` `[DONE]` işlendiyse `True`, değilse `False` olur.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-17")
```

```starter
from ai_temel_veri import metin_yukle
def sse_ayristir(akis):
    # KUSURLU BAŞLANGIÇ KODU: olay sınırını ve kapanışın gerçekten gelmesini yok sayar.
    import json
    parcalar=[];bitis=None
    for line in akis.splitlines():
        if not line.startswith("data:"):continue
        data=line[5:].strip()
        if data=="[DONE]":continue
        obj=json.loads(data); c=obj["choices"][0]
        parcalar.append(c["delta"].get("content") or "")
        bitis=c.get("finish_reason") or bitis
    return {"metin":"".join(parcalar),"bitis":bitis,"tamam":True}

for yol in ("veri/openai_sse.txt","veri/openai_sse_yarim.txt"):
    ham=metin_yukle(yol)
    print("Sentetik ham dosya:",yol,repr(ham))
    print("Ayrıştırma:",sse_ayristir(ham))
```

```test
def P(icerik, bitis=None):
    import json
    return "data: " + json.dumps({"choices": [{"index": 0, "delta": {"content": icerik}, "finish_reason": bitis}]}) + "\n\n"
DONE = "data: [DONE]\n\n"
def sozlesme(fn):
    try:
        a = 'data: {"choices":[{"delta":{"role":"assistant","content":""},"finish_reason":null}]}\n\n: ping\n\ndata:{"choices":[{"delta":{"content":"Mer"},"finish_reason":null}]}\n\n' + P("haba", "stop") + DONE
        if fn(a) != {"metin": "Merhaba", "bitis": "stop", "tamam": True}:
            return False
        b = 'data: {"choices":[{"delta":\ndata: {"content":"a\\nb"},"finish_reason":"length"}]}\n\n'
        if fn(b) != {"metin": "a\nb", "bitis": "length", "tamam": False}:
            return False
        if fn(P("x", "stop") + "data: [DONE]") != {"metin": "x", "bitis": "stop", "tamam": False}:
            return False
        if fn(P("ilk") + P("yarım")[:-2]) != {"metin": "ilk", "bitis": None, "tamam": False}:
            return False
        e = P(None) + "\n\n" + 'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\n' + DONE + ": son\n\n"
        if fn(e) != {"metin": "", "bitis": "stop", "tamam": True}:
            return False
        if fn(":" + "x" * 19999) != {"metin": "", "bitis": None, "tamam": False} or fn("\n") != {"metin": "", "bitis": None, "tamam": False}:
            return False
        import json
        u = "data: " + json.dumps({"choices": [{"delta": {"content": "a b\x85c"}, "finish_reason": "stop"}]}, ensure_ascii=False) + "\n\n" + DONE
        if fn(u) != {"metin": "a b\x85c", "bitis": "stop", "tamam": True}:
            return False
        for deger in [None, b"data: x\n\n", "", ":" + "x" * 20000, "event: x\n\n", "data\n\n", " data: x\n\n", "data: {bozuk\n\n", "data: 5\n\n", "data: [1]\n\n", "data:\n\n",
                      DONE, P("x", "stop") + DONE + "data: x", P("x", "stop") + DONE + DONE, P("x", "stop") + P("y"), P("x", "stop") + "data:  [DONE]\n\n",
                      'data: {"choices":[{"delta":{"content":"a"},"finish_reason":nu\ndata: ll}]}\n\n', 'data: {"choices":[]}\n\n', 'data: {"x":1}\n\n', 'data: {"choices":[{"delta":{},"finish_reason":null},{"delta":{},"finish_reason":null}]}\n\n',
                      'data: {"choices":["x"]}\n\n', 'data: {"choices":[{"delta":{}}]}\n\n', 'data: {"choices":[{"finish_reason":null}]}\n\n',
                      'data: {"choices":[{"delta":"x","finish_reason":null}]}\n\n', P("x", "bitti"), P(5), P(["x"]), P(False), P(0), P([]), P({}),
                      P("a") + " \n", P("a") + "\t\n", P("x", "stop") + "data: [DONE] \n\n"]:
            try:
                fn(deger)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(sse_ayristir), "SSE satır kuralları, parça birleştirme ve [DONE] yaşam döngüsü korunmalı")
def m_tamam(a):
    return dict(sse_ayristir(a), tamam=True)
def m_sira(a):
    r = sse_ayristir(a)
    return dict(r, metin=r["metin"][::-1])
def m_yarim(a):
    return sse_ayristir(a + "\n\n")
for ad, mutant in [("eksik akışı tamam sayan", m_tamam), ("parça sırasını bozan", m_sira), ("yarım olayı işleyen", m_yarim)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import metin_yukle
def sse_ayristir(akis):
    import json
    if not isinstance(akis, str) or not 1 <= len(akis) <= 20000:
        raise ValueError("akış")
    parcalar, tampon, bitis, bitti = [], [], None, False
    for satir in akis.split("\n"):
        if satir.startswith(":"):
            continue
        if satir.startswith("data:"):
            if bitti:
                raise ValueError("kapanış sonrası")
            deger = satir[5:]
            tampon.append(deger[1:] if deger.startswith(" ") else deger)
            continue
        if satir:
            raise ValueError("satır")
        if not tampon:
            continue
        veri, tampon = "\n".join(tampon), []
        if veri == "[DONE]":
            if bitis is None:
                raise ValueError("bitiş yok")
            bitti = True
            continue
        parca = json.loads(veri)
        if bitis is not None or not isinstance(parca, dict) or not isinstance(parca.get("choices"), list) or len(parca["choices"]) != 1:
            raise ValueError("parça")
        secim = parca["choices"][0]
        if not isinstance(secim, dict) or not isinstance(secim.get("delta"), dict) or "finish_reason" not in secim or secim["finish_reason"] not in (None, "stop", "length"):
            raise ValueError("seçim")
        icerik = secim["delta"].get("content")
        if not isinstance(icerik, (str, type(None))):
            raise ValueError("içerik")
        parcalar.append(icerik or "")
        bitis = secim["finish_reason"]
    return {"metin": "".join(parcalar), "bitis": bitis, "tamam": bitti}

if __name__ == "__main__":
    for yol in ("veri/openai_sse.txt","veri/openai_sse_yarim.txt"):
        ham=metin_yukle(yol)
        print("Sentetik ham dosya:",yol,repr(ham))
        print("Ayrıştırma:",sse_ayristir(ham))
```

```hint
Satırları bir durum makinesi gibi işle: `data:` satırları tampona girer, olay ancak boş satırda işlenir; döngü bittiğinde tamponda kalan yarım olayı bilerek işleme. `[DONE]` için ayrı bir bayrak tut ve bayrak açıkken yeni `data:` satırını reddet. `json.JSONDecodeError` zaten `ValueError` alt sınıfıdır.
```
:::

::: gorev 3 · Sürekli batching zamanlayıcısını adım adım benzet
`surekli_batch(istekler, azami_dizi)` işlevini yaz. `azami_dizi` 1–64 aralığında bir tam sayıdır (bool olamaz) ve benzetimde azami slot sayısını temsil eder; gerçek bir sunucu ayarını değiştirmez. `istekler` 1–50 öğeli bir listedir; her öğe tam `id`, `varis`, `hedef`, `son_adim` anahtarlı bir sözlüktür. `id` boş olmayan ve yinelenmeyen bir stringdir; `varis` 0–1000, `hedef` 1–100 aralığında, `son_adim` ise `varis` veya daha büyük bir tam sayıdır (üçü de bool olamaz). Geçersiz veride `ValueError` yükselt.

Benzetim `t = 0` adımından başlar ve her adımda şu sırayı izler. Kabul: kuyrukta bekleyen ve `varis <= t` olan istekler, boş slot kaldıkça FIFO sırasıyla alınır; FIFO sırası `varis` değerine göre artan, eşitlikte girdi sırasıdır. Üretim: slottaki her istek bir token üretir. Bitiş: üretilen token sayısı `hedef` değerine ulaşan istek `tamam` olur; ulaşamamış ve `t == son_adim` olan istek `zaman_asimi` olur. Slottan çıkan isteğin yeri bir sonraki adımın kabulünde kullanılır. Kuyrukta bekleyen (slot alamamış) istek de `t == son_adim` olduğunda sıfır tokenla `zaman_asimi` olur. Benzetim bütün istekler sonuçlanınca durur.

`{id: (durum, bitis_adimi, uretilen)}` sözlüğü döndür; `durum` `"tamam"` veya `"zaman_asimi"`, `bitis_adimi` isteğin sonuçlandığı `t`, `uretilen` ürettiği token sayısıdır. Girdileri değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-17")
```

```starter
from ai_temel_veri import json_yukle
def surekli_batch(istekler, azami_dizi):
    # KUSURLU BAŞLANGIÇ KODU: slotları sınırsız sayar, kuyruk beklemesini yok sayar.
    return {i["id"]:("tamam",i["varis"]+i["hedef"]-1,i["hedef"]) for i in istekler}

v=json_yukle("veri/istekler.json")
print("Sentetik işler:",v["batch"])
print("Slot sonucu:",surekli_batch(v["batch"],v["azami_dizi"]))
```

```test
import copy
def R(id, varis, hedef, son):
    return {"id": id, "varis": varis, "hedef": hedef, "son_adim": son}
def sozlesme(fn):
    try:
        s1 = [R("a", 0, 4, 10), R("b", 0, 1, 10), R("c", 0, 2, 10), R("d", 1, 3, 3)]
        kopya = copy.deepcopy(s1)
        if fn(s1, 2) != {"a": ("tamam", 3, 4), "b": ("tamam", 0, 1), "c": ("tamam", 2, 2), "d": ("zaman_asimi", 3, 1)} or s1 != kopya:
            return False
        if fn([R("x", 0, 3, 5), R("y", 0, 1, 1)], 1) != {"x": ("tamam", 2, 3), "y": ("zaman_asimi", 1, 0)}:
            return False
        if fn([R("r1", 3, 1, 9), R("r2", 0, 5, 9), R("r3", 0, 1, 9)], 1) != {"r2": ("tamam", 4, 5), "r3": ("tamam", 5, 1), "r1": ("tamam", 6, 1)}:
            return False
        if fn([R("z", 2, 2, 3)], 1) != {"z": ("tamam", 3, 2)} or fn([R("w", 5, 2, 5)], 1) != {"w": ("zaman_asimi", 5, 1)}:
            return False
        if fn([R("v", 0, 1, 0), R("u", 1000, 100, 1099)], 64) != {"v": ("tamam", 0, 1), "u": ("tamam", 1099, 100)}:
            return False
        elli = [R("k" + str(n), 0, 1, 0) for n in range(50)]
        if fn(elli, 64) != {"k" + str(n): ("tamam", 0, 1) for n in range(50)}:
            return False
        if fn([R("p", 0, 2, 9), R("q", 0, 2, 9), R("s", 0, 1, 9)], 2) != {"p": ("tamam", 1, 2), "q": ("tamam", 1, 2), "s": ("tamam", 2, 1)}:
            return False
        if fn([R("b", 0, 2, 9), R("a", 0, 1, 9)], 1) != {"b": ("tamam", 1, 2), "a": ("tamam", 2, 1)}:
            return False
        if fn([R("a", 0, 1, 5), R("b", 0, 1, 0)], 1) != {"a": ("tamam", 0, 1), "b": ("zaman_asimi", 0, 0)}:
            return False
        x = [R("b", 1, 1, 9), R("a", 0, 1, 9)]
        k2 = copy.deepcopy(x)
        if fn(x, 1) != {"a": ("tamam", 0, 1), "b": ("tamam", 1, 1)} or x != k2:
            return False
        T = [R("a", 0, 1, 0)]
        for args in [(None, 1), ((R("a", 0, 1, 0),), 1), ([], 1), (elli + [R("son", 0, 1, 0)], 64), (T, 0), (T, 65), (T, True), (T, 2.0), (T, None),
                     (["a"], 1), ([["id", "varis", "hedef", "son_adim"]], 1), ([{"id": "a", "varis": 0, "hedef": 1}], 1), ([dict(R("a", 0, 1, 0), ek=1)], 1), ([R("", 0, 1, 0)], 1), ([R(5, 0, 1, 0)], 1),
                     ([R(b"a", 0, 1, 0)], 1), ([R("a", 0, 1, 0), R("a", 0, 1, 0)], 1), ([R("a", -1, 1, 0)], 1), ([R("a", 1001, 1, 1001)], 1),
                     ([R("a", True, 1, 1)], 1), ([R("a", 0.0, 1, 0)], 1), ([R("a", 0, 0, 0)], 1), ([R("a", 0, 101, 200)], 1), ([R("a", 0, True, 0)], 1),
                     ([R("a", 0, 1.0, 0)], 1), ([R("a", 3, 1, 2)], 1), ([R("a", 0, 1, "5")], 1), ([R("a", 0, 1, True)], 1), ([R("a", 0, 1, None)], 1)]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(surekli_batch), "slot sınırı, FIFO kabulü ve süre sınırı korunmalı")
def m_slot(istekler, a):
    return surekli_batch(istekler, 64)
def m_sure(istekler, a):
    return surekli_batch([dict(i, son_adim=i["son_adim"] + 1) for i in istekler], a)
def m_durum(istekler, a):
    return {k: ("tamam", b, u) for k, (d, b, u) in surekli_batch(istekler, a).items()}
for ad, mutant in [("slot sınırını yok sayan", m_slot), ("süre sınırını kaydıran", m_sure), ("zaman aşımını gizleyen", m_durum)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle
def surekli_batch(istekler, azami_dizi):
    if type(azami_dizi) is not int or not 1 <= azami_dizi <= 64 or not isinstance(istekler, list) or not 1 <= len(istekler) <= 50:
        raise ValueError("girdi")
    for i in istekler:
        if not isinstance(i, dict) or set(i) != {"id", "varis", "hedef", "son_adim"} or not isinstance(i["id"], str) or not i["id"]:
            raise ValueError("istek")
        if any(type(i[k]) is not int for k in ("varis", "hedef", "son_adim")) or not 0 <= i["varis"] <= 1000 or not 1 <= i["hedef"] <= 100 or i["son_adim"] < i["varis"]:
            raise ValueError("istek")
    if len({i["id"] for i in istekler}) != len(istekler):
        raise ValueError("kimlik")
    kuyruk = sorted(istekler, key=lambda i: i["varis"])
    aktif, uretilen, sonuc, t = [], {}, {}, 0
    while kuyruk or aktif:
        while kuyruk and len(aktif) < azami_dizi and kuyruk[0]["varis"] <= t:
            aktif.append(kuyruk.pop(0))
        for i in list(aktif):
            n = uretilen[i["id"]] = uretilen.get(i["id"], 0) + 1
            if n == i["hedef"] or t == i["son_adim"]:
                sonuc[i["id"]] = ("tamam" if n == i["hedef"] else "zaman_asimi", t, n)
                aktif.remove(i)
        for i in list(kuyruk):
            if t == i["son_adim"]:
                sonuc[i["id"]] = ("zaman_asimi", t, 0)
                kuyruk.remove(i)
        t += 1
    return sonuc

if __name__ == "__main__":
    v=json_yukle("veri/istekler.json")
    print("Sentetik işler:",v["batch"])
    print("Slot sonucu:",surekli_batch(v["batch"],v["azami_dizi"]))
```

```hint
Kuyruğu `varis` değerine göre kararlı biçimde sırala; Python'un `sorted` işlevi eşitlikte girdi sırasını korur. Her adımda önce kabul, sonra üretim, sonra bitiş ve süre denetimi yap; slottan çıkan isteğin yerini aynı adımda doldurma. Döngüyü kuyruk ve slotlar boşalana kadar sürdür.
```
:::

::: gorev Gerçek deney · Akışı çöz, TTFT'yi ve token sınırını ölç
`akis_raporu(satirlar, gelisler)` işlevini yaz.

- Doğrulama, aksi hâlde `ValueError`: `satirlar` 1–4096 öğeli, her öğesi JSON nesnesine ayrışan string; her nesnede bool `done` var. Tam **bir** satırda `done` True ve o **son** satır; o satırda boş olmayan string `done_reason` ve bool olmayan negatif olmayan tam sayı `eval_count` var. `done` False satırlarda string `response` var. `gelisler`, `done` False satır sayısına eşit uzunlukta liste; her öğe bool olmayan sonlu, negatif olmayan, azalmayan sayı.
- Döndür: `{"metin": response birleşimi, "parca": done False satır sayısı, "done_reason": bitiş satırından, "ttft_ms": gelisler[0] (parça yoksa None), "sure_ms": gelisler[-1] (parça yoksa None), "tokens": bitiş satırının eval_count'u, "kesildi": done_reason == "length"}`.

Test işlevini sentetik akışlarda sınar; sonra yerel sunucuya gerçek akışlı istekler atıp sonucunu bağımsız hesapla karşılaştırır, TTFT'nin ölçüldüğünü ve en az bir isteğin `num_predict` ile kesildiğini doğrular. Çalıştır düğmesi dört ardışık ve iki eşzamanlı gerçek HTTP isteğini ve ölçülerini gösterir. Eşzamanlı istemci aralıkları iç sürekli batching kanıtı değildir. TTFT burada ilk yanıt parçası gecikmesidir.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import json
import math
import ai_lab

def akis_raporu(satirlar, gelisler):
    return {"metin": "", "parca": 0, "done_reason": None, "ttft_ms": None, "sure_ms": None, "tokens": None, "kesildi": False}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_17 as deney
    deney.goster(akis_raporu)
```

```test
import json
import random
import ai_lab
sonuclar = []
def kontrol(kosul, mesaj):
    sonuclar.append(bool(kosul))
    return ok(kosul, mesaj)
import ast
_yasak=("referans","kanit_yaz","getattr")
sorun=ai_lab.kod_denetimi(src,yasak=_yasak)
for n in ast.walk(ast.parse(src)):
    if isinstance(n,ast.ImportFrom) and any(a.name in _yasak or a.name=="*" for a in n.names):
        sorun.append("referans importu yasak")
if not kontrol(not sorun,"Kendi akış raporunu yaz: "+"; ".join(sorun)):
    stop()
fn = need("akis_raporu")
from sandbox import ai_gercek_ai_temel_17 as D
rnd = random.Random()
def kur(parcalar, done_reason, eval_count, bas, artis):
    satir = [json.dumps({"response": t, "done": False}) for t in parcalar]
    satir.append(json.dumps({"response": "", "done": True, "done_reason": done_reason, "eval_count": eval_count}))
    gelis = [bas + i * artis for i in range(len(parcalar))]
    return satir, gelis
vakalar = [kur([],"stop",0,0,0),kur(["", "x"],"stop",2,0,0),kur(["a ", "b ", "c "], "stop", 9, 50, 10), kur(["x ", "y "], "length", 4, 30, 20), kur(["solo "], "stop", 1, 40, 0)]
for _ in range(5):
    m = rnd.randint(1, 8)
    vakalar.append(kur(["t%d " % i for i in range(m)], rnd.choice(["stop", "length"]), rnd.randint(m, m + 5), rnd.randint(20, 200), rnd.randint(5, 40)))
def ayni(a, b):
    return isinstance(a, dict) and set(a) == set(b) and all(a[x] == b[x] for x in b)
def sozlesme(f):
    try:
        s4096, g4096 = kur(["x"] * 4095, "stop", 4095, 10, 1)
        if not ayni(f(s4096, g4096), D.referans(s4096, g4096)):
            return False
        for satir, gelis in vakalar:
            s2, g2 = list(satir), list(gelis)
            if not ayni(f(s2, g2), D.referans(satir, gelis)) or s2 != satir or g2 != gelis:
                return False
        satir, gelis = vakalar[2]
        tdone = satir[-1]
        for arg in [(satir,[float("nan"),60,70]),(satir,[50,60,float("inf")]),(satir[:-1]+[json.dumps({"done":True,"done_reason":"stop","eval_count":True})],gelis),(satir[:-1]+[json.dumps({"done":True,"done_reason":"","eval_count":3})],gelis),(None, gelis), (satir, None), ([], []), (satir, gelis[:-1]), (satir, gelis + [80]), (satir[:-1], gelis),
                    (satir + [json.dumps({"response": "z", "done": False})], gelis + [80]),
                    (kur(["x"] * 4096, "stop", 4096, 10, 1)), ([b'{"done":true,"done_reason":"stop","eval_count":0}'], []), (["[]", tdone], [50]),
                    ([tdone, tdone], [50]), ([tdone, json.dumps({"response": "x", "done": False, "done_reason": "stop", "eval_count": 1})], [50]),
                    ([json.dumps({"response": 5, "done": False}), tdone], [50]), ([json.dumps({"done": True, "done_reason": 5, "eval_count": 0})], []),
                    ([json.dumps({"done": True, "done_reason": "stop", "eval_count": -1})], []),
                    ([tdone] + satir[:-1], gelis), (satir, [50, 40, 70]), (satir, [True, 60, 70]), (satir, [50, 60, "70"]), (satir, [-1, 60, 70]),
                    (["düz metin"] + satir[1:], gelis), ([json.dumps({"response": "a"})] + satir[1:], gelis),
                    (satir[:-1] + [json.dumps({"response": "", "done": True, "done_reason": "stop"})], gelis),
                    (satir[:-1] + [json.dumps({"response": "", "done": True, "eval_count": 3})], gelis)]:
            try:
                f(*arg)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
kontrol(sozlesme(fn), "sentetik akış: birleştirme, parça, done_reason, TTFT, kesilme ve geçersiz girdiler doğru")
for ad, kw in [("son parçayı metin sayan", {"birlestirme": "son"}), ("TTFT'yi son parça sayan", {"ttft": "son"}),
               ("kesilmeyi yok sayan", {"kesildi": False}), ("parçayı token sayan", {"parca": "token"})]:
    kontrol(not sozlesme(lambda s, g, kw=kw: D.referans(s, g, **kw)), "hatalı çözüm reddedilmeli: " + ad)
sabit = D.referans(*vakalar[0])
kontrol(not sozlesme(lambda s, g: sabit), "hatalı çözüm reddedilmeli: ezber sonuç")
r, oz = None, None
if all(sonuclar):
    try:
        r = D.deney(fn)
    except ai_lab.GercekLabYok as e:
        kontrol(False, f"GERÇEK SUNUCU YOK, deney yapılmadı: {e}")
        stop()
    g = [k for k in r["kayitlar"] if k["hata"] is None]
    kontrol(len(g) == r["ayarlar"]["istek_sayisi"] == 6, f"yerel sunucu akışlı yanıt verdi ({len(g)}/{len(r['kayitlar'])} istek hatasız)")
    esit = all(all(k[x] == D.referans(k["_satirlar"], k["_gelisler"])[x] for x in ("metin", "parca", "done_reason", "ttft_ms", "sure_ms", "tokens", "kesildi")) for k in g)
    kontrol(esit, "akış çözümü, TTFT ve token sayısı bağımsız hesapla aynı")
    kesilen = sum(1 for k in g if k["kesildi"])
    kontrol(kesilen > 0, f"num_predict token sınırı en az bir isteği kesti (done_reason=length): {kesilen}")
    kontrol(all(isinstance(k["ttft_ms"], int) and k["ttft_ms"] >= 0 for k in g), "her geçerli istekte ilk token süresi (TTFT) ölçüldü")
    kontrol(r["eszamanli"]["istek_sayisi"]==2 and r["eszamanli"]["cakisan_araliklar"],"iki gerçek HTTP istemci çağrısı çakışan aralıklarda tamamlandı; iç batching kanıtı değil")
    oz = D.ozet(r)
yol = ai_lab.kanit_yaz("temel-akis", {"kaynak": "gercek", "kabul": all(sonuclar), "ders": "ai-temel-17",
                                      "ortam": (r or {}).get("ortam"), "deney": r, "ozet": oz})
if oz:
    ok(True, f"BULGU ({r['ortam']['model']['ad']}): {oz['gecerli']} istek akışla yanıtlandı; TTFT {oz['ttft_ms_min']}–{oz['ttft_ms_maks']} ms, "
             f"~{oz['tokens_sn_ort']} token/sn; {oz['kesilen']} istek num_predict ile kesildi (length), {oz['durak']} istek durak jetonuyla bitti (stop).")
```

```solution
import json
import math
import ai_lab

def akis_raporu(satirlar, gelisler):
    if not isinstance(satirlar, list) or not 1 <= len(satirlar) <= 4096:
        raise ValueError("satırlar 1-4096 öğeli liste olmalı")
    nesneler = []
    for s in satirlar:
        if not isinstance(s, str):
            raise ValueError("satır metin olmalı")
        try:
            o = json.loads(s)
        except (ValueError, TypeError):
            raise ValueError("satır JSON nesnesi değil")
        if not isinstance(o, dict) or not isinstance(o.get("done"), bool):
            raise ValueError("satırda bool done yok")
        nesneler.append(o)
    bitti_idx = [i for i, o in enumerate(nesneler) if o["done"]]
    if len(bitti_idx) != 1 or bitti_idx[0] != len(nesneler) - 1:
        raise ValueError("done son satırda tam bir kez olmalı")
    son = nesneler[-1]
    yanitlar = nesneler[:-1]
    for o in yanitlar:
        if not isinstance(o.get("response"), str):
            raise ValueError("yanıt parçasında response metni yok")
    dr = son.get("done_reason")
    if not isinstance(dr, str) or not dr:
        raise ValueError("bitiş satırında done_reason metni yok")
    ec = son.get("eval_count")
    if not isinstance(ec, int) or isinstance(ec, bool) or ec < 0:
        raise ValueError("bitiş satırında eval_count yok")
    if not isinstance(gelisler, list) or len(gelisler) != len(yanitlar):
        raise ValueError("gelişler yanıt parçası sayısına eşit olmalı")
    for i, x in enumerate(gelisler):
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or x < 0:
            raise ValueError("varış anı negatif olmayan sonlu sayı olmalı")
        if i and x < gelisler[i - 1]:
            raise ValueError("varış anları azalmamalı")
    return {"metin": "".join(o["response"] for o in yanitlar), "parca": len(yanitlar), "done_reason": dr,
            "ttft_ms": gelisler[0] if gelisler else None, "sure_ms": gelisler[-1] if gelisler else None,
            "tokens": ec, "kesildi": dr == "length"}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_17 as deney
    deney.goster(akis_raporu)
```

```hint
Akış çözümü 2. görevdeki SSE ayrıştırmasına benzer, ama burada Ollama'nın yerel akışı her satırda bir JSON nesnesi (NDJSON) verir, `data:` öneki ve `[DONE]` yoktur; bitiş satırı zorunludur ve `eval_count` taşır; `gelisler` uzunluğu yanıt parçası sayısına eşit olmalı. Önce satırları çöz ve bitişi doğrula, sonra `gelisler`'i denetle; TTFT `gelisler[0]`, kesilme `done_reason == "length"`.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Kuyruk öncesi kabul kapısı (`LLM10`) (30 sn).** "İstek zamanlayıcıya girmeden önce izinli model kimliği, mesaj şeması ve `istem_tokenlari + max_tokens <= baglam` bütçesi doğrulanır; bütçeyi aşan isteği sessizce kırpmak yerine `400` ile reddetmek yarım çıktı sürprizlerini önler."
2. **Akış bütünlüğü (`SSE` vs `NDJSON`) (35 sn).** "Akışlı yanıtlarda `[DONE]` veya `done=True` kapanış çerçevesi görülmeden kopan akış eksik yanıttır; kopuk akışı tam yanıt gibi alt katmana taşımak yarım JSON veya kesik talimat hatası üretir."
3. **Sürekli `batching` ve kuyruk `deadline`'ı (30 sn).** "Yineleme düzeyinde zamanlama (`continuous batching`) biten dizinin slotunu hemen yeni isteğe açar; ancak süre sınırı kuyrukta beklerken de işlediği için uzun istek seli kısa istekleri kuyrukta düşürebilir."
4. **Soru (25 sn).** "İstemci bağlantıyı yarıda kapattığında sunucu üretim döngüsünü iptal etmezse GPU slotlarına ve `KV cache` bloklarına ne olur?"
:::
