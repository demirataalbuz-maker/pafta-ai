---
id: ai-temel-23
title: "Tool-Call Yaşam Döngüsü ve Ajan Döngüsü"
summary: İki tel biçimindeki araç çağrılarını parametre şemasına göre doğrulayıp tek iç biçime normalize et, her çağrı kimliğine tek sonuç mesajı üret ve adım bütçeli ajan döngüsünü kur; son adımda şemalı dispatch ile ajan döngüsünü gerçek modelde sür.
esleme: ai-temel-14, ai-temel-16, ai-temel-24
timeout: 45
---

::: anlat Araç çağrısı modelin önerdiği veridir ve iki tel biçimiyle gelir

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Araç çağrısı API yanıtında öneri olarak gelir; uygulama doğrulayıp yürütür | İlk üç görev görünür sentetik OpenAI/Ollama biçimleri ve betikli model; final gerçek yerel Ollama ajanı | FastAPI/Pydantic veya uzaktaki OpenAI servisi çalıştırıldığı anlamına gelmez |
| Ajan araç sonucunu bağlama alıp yeni karar verir | Final gerçek Python toplama/çarpma işlevleri ve en çok altı model turu | Dosya/ağ yetkisi, kullanıcı onayı, genel ajan güvenliği veya saldırı başarısı testi değildir |

> [!NOT]
> `veri/cagrilar.json` ve `veri/ajan.json` elle hazırlanmış sentetik örneklerdir; canlı model kaydı değildir. İlk üç görev bu dosyaları okur. Setup her Run/Check için geçici kopya oluşturur; kalıcılık yoktur. Kaynağı editörle aç veya kodda yüklenen kopyayı değiştirip Run dene. Gizli testler ayrıdır. Final kurulu yerel modeli gerçekten çağırır; yeni indirme yoktur.

İstemci araçları istekte `tools` listesiyle bildirir: her öğe `{"type": "function", "function": {"name": ..., "description": ..., "parameters": <JSON Schema>}}` biçimindedir. Model aracı çalıştırmaz; yalnız `tool_calls` alanı dolu bir asistan mesajı üretir. OpenAI Chat Completions yanıtında her çağrı `id`, `type: "function"` ve `function.name` taşır; `function.arguments` ise modelin ürettiği bir JSON **string**idir ve geçersiz JSON, nesne olmayan bir değer ya da şemaya uymayan alanlar içerebilir. `finish_reason` genellikle `"tool_calls"` olur, ancak `tool_choice` belirli bir fonksiyonu zorladığında `"stop"` gelebilir; bu yüzden döngü `finish_reason`'a değil `tool_calls` alanının doluluğuna bakar. Ollama'nın yerel `/api/chat` uç noktasında `arguments` doğrudan bir JSON **nesnesi**dir, sıra `function.index` ile verilir ve sunucunun `ToolCall` yapısında `type` alanı yoktur; çağrı kimliği `id` v0.12.10 sürümünde eklendi, daha eski sunucular onu hiç göndermez. Aynı sunucunun OpenAI uyumlu `/v1/chat/completions` uç noktası ise OpenAI gibi string döndürür, yani tek sunucu iki farklı tür üretebilir.

Bu fark bir güvenlik sınırıdır: tek biçimi varsayan ayrıştırıcı ya çöker ya da yanlış türdeki içeriği sessizce kabul eder. Doğru yaklaşım, çağrıları sınırda tek bir iç biçime (`id`, `ad`, `argumanlar`) çevirmek ve argümanları aracın bildirilen `parameters` şemasına karşı **yürütmeden önce** doğrulamaktır: bildirilmemiş araç, nesneye çözülmeyen argüman, eksik `required` alanı, `additionalProperties: false` ile yasaklanan fazla alan ve yanlış tür onarılmadan reddedilir. JSON Schema'da `true` bir `integer` değildir, Python'da ise `bool` `int`'in alt sınıfıdır; bu yüzden tür denetimi `isinstance` ile değil tam tür karşılaştırmasıyla yapılır. Gerçek bir FastAPI servisinde bu iş Pydantic modelleriyle yapılır: `model_config = ConfigDict(extra="forbid")` bilinmeyen alanı reddeder, `model_validate_json(...)` OpenAI'nin string argümanını, `model_validate(...)` Ollama'nın sözlüğünü doğrular; varsayılan lax modda `"2"` gibi bir string `int`'e çevrilebildiği için tam tür denetimi `strict=True` ister. Görevler 1–3 belgelenen biçimleri izleyen sentetik dosyalarda çalışır; final kurulu Ollama modeliyle gerçek ajan döngüsünü yürütür. FastAPI/Pydantic bu derste kullanılmaz; şema yalnız `string` ve `integer` türlerini içeren küçük bir JSON Schema alt kümesidir ve `id` göndermeyen eski Ollama sunucuları için iç kimliği `ollama-0` gibi sıra numarasından türetmek bu derse özgü bir kuraldır.
:::

::: anlat Ajan döngüsü her çağrıya tek sonuç verir ve bütçeyle durur

Önce cagrilar.json dosyasını aç. Aynı hava/saat isteğinin OpenAI biçiminde JSON metni, Ollama biçiminde doğrudan nesne argümanı vardır. İlk görev bunları tek iç biçime çevirir. Dosyadaki normalize listesi ikinci görevin girdisidir; yerel örnek hava ve saat işlevleri gerçek servis değildir, dosyadaki sentetik sonuçları döndürür. ajan.json üçüncü görev için sırayla iki asistan mesajı taşır. Buradaki betikli model yalnız bu mesajları sırayla verir; internet veya dil modeli kullanmaz. Böylece önce yaşam döngüsünü anlaşılır veride izler, finalde gerçekten üretilmiş çağrıları aynı doğrulama mantığıyla işlersin.

Çağrı kimliği araç adı değildir. Aynı araca iki ayrı çağrı geldiğinde sonuçlar kendi kimliklerine bağlanmalıdır. Öte yandan eski yerel tel biçimi kimlik göndermeyebilir; dersin normalize kimliği yalnız öğretim kuralıdır, bütün sunucuların garantisi değildir. İlk görevin küçük şema altkümesi yalnız string ve integer tanır. Finaldeki şema ise sayı/metin alanları kullanır; sayı burada bool olmayan sonlu int/float kabul eder. İki görevdeki argüman sözleşmesini aynı sanarak ondalıklı değeri ilk görevde kabul etme. Metin olarak gelen bir argümanı sessizce sayıya çevirmek de katı doğrulama değildir.

Bir mesajın bütün çağrılarını önce doğrulamak önemlidir. İlk çağrıyı hemen çalıştırıp ikinci çağrının bozuk olduğunu sonra fark edersen işlem kısmen gerçekleşmiştir. İkinci görev bu yüzden iki geçiş yapar: önce tüm kimlik, araç ve argüman yapıları; sonra yürütme. Bu bir veritabanı işlemi veya geri alma mekanizması değildir. Gerçek araç yan etki yapıyorsa hata sonrası önceki etkileri nasıl telafi edeceğin ayrıca tasarlanır. Bu derste gerçek finalin araçları yalnız aritmetik hesapladığı için dosya, ağ veya öğrenci verisi üzerinde yan etki oluşturmaz.

Sonuç içeriklerinin biçimi de güven sınırıdır. Bir Python sözlüğünü str ile yazmak JSON üretmez; JSON'a çevrilemeyen küme ise TypeError verir. İkinci ve üçüncü görev bu hatayı yalnız sınıf adıyla sonuç mesajına yazar. İstisnanın özel metnini modele göndermek bir dosya yolu veya anahtar sızdırabilir. Buna karşılık SystemExit gibi Exception dışında kalan durumlar yutulmaz. Hata mesajını modele geri vermek, araç sonucunun güvenilir talimata dönüştüğü anlamına gelmez. Sonraki bir model çağrısı bu içeriği veri olarak kullanır; izin ve kaynak politikası başka bir katmandır.

Döngü bütçesi model çağrılarını sayar. Son turda araç istenirse o çağrı yürütülüp sonuç geçmişe eklenir, fakat bütçe bittiyse model bir kez daha çağrılmaz. Böyle bir sonuç tamam değil adim_siniri olarak görünmelidir. Betikte iki mesaj bulunması iki araç çağrısı demek değildir; tek mesaj çok sayıda çağrı içerebilir. Geçmişin derin kopyasını modele vermek, betikli modelin geçmişi geriye dönük değiştirmesini önler. Bütün döngü boyunca kimliklerin tekil kalması sonuçların yanlış tura bağlanmasını engeller.

Gerçek final iki aritmetik araç sunar ve hesaplama için modelin bunları seçmesini bekler. Her turdaki tam mesajlar, örnekleme ayarları, ham model yanıtı, çağrılar ve sonuçlar kanıtta kalır. Son metin 444 yerine açıklama içerirse sonuç ayrı bulgu olarak kaydedilir; sabit metin eşleşmesi geçme koşulu değildir. Bununla birlikte gerçek bir araç çağrısı ve öğrenci dispatch'inin doğru çalışması gerekir. Model çağrısı hatası veya hiç çalışmamış deney geçme sayılmaz. Final doğruluğu artık beklenen sayının metin içinde rastgele alt dizi olarak bulunmasıyla ölçülmez; yalnız tek sayısal yanıt ayrıca karşılaştırılır.

Kaynak: [Ollama tool calling](https://docs.ollama.com/capabilities/tool-calling). Yerel sonuç mesajındaki tool_name ile uygulamanın iç çağrı kimliği farklı alanlardır; dersin sınırlı biçimleri bütün SDK ve sürümlerin birebir kopyası değildir.

Uygulama çağrıları yürüttükten sonra her sonucu bağlama ayrı bir mesaj olarak ekler. OpenAI biçiminde bu mesaj `{"role": "tool", "tool_call_id": ..., "content": ...}` şeklindedir ve çağrıları içeren asistan mesajının hemen ardından, her `id` için bir tane gelir; yanıtlanmamış bir çağrı kimliği bırakılırsa API sonraki isteği reddeder. Ollama yerel biçiminde sonuç mesajı aracı `tool_name` alanıyla adlandırır (`tool_call_id` OpenAI biçiminin alanıdır ve Ollama'nın OpenAI uyumlu `/v1` uç noktasında kullanılır); çağrı kimliği göndermeyen eski sunucularda eşleme ad ve sıra üzerinden yapılır ve aynı araca yapılan iki çağrı ancak sırayla ayırt edilir. Bu derste string sonuç içeriğe olduğu gibi girer, diğer sonuçlar JSON'a çevrilir. Araç hatası istisna olarak döngüyü kırmaz, `HATA: TypeError` gibi içerik olarak modele döner ki model isteğini düzeltebilsin; ancak istisna mesajı değil yalnız sınıf adı gönderilir, çünkü hata metinleri dosya yolu, anahtar veya yığın izi taşıyabilir ve modelin çıktısı sonunda kullanıcıya ulaşır.

Ajan döngüsü bu adımları tekrarlar: modeli geçmişle çağır, `tool_calls` boşsa son yanıtı al, doluysa bütün çağrıları önce doğrula, sonra sırayla yürüt, sonuçları ekle ve modeli yeniden çağır. Adım sınırı olmadan sürekli araç isteyen bir model, ya da bir araç sonucuna gömülü talimatla buna yönlendirilmiş bir model, sınırsız maliyet ve sınırsız eylem demektir; bu yüzden `max_adim` model çağrılarını sınırlar ve `adim_siniri` durumu `tamam` durumundan ayrı kaydedilir. Modele geçmişin derin kopyası verilir ki model kodu dökümü geriye dönük değiştiremesin; kimlikler bütün döngü boyunca tekildir, böylece her sonuç tek bir çağrıya bağlanır. Araç sonuçları bağlama geri giren güvenilmeyen veridir; hangi aracın hangi izin, onay ve kaynak politikasıyla çalışacağı sonraki dersin konusudur.
:::

::: tahmin Çağrı ve sonuç akışını tahmin et
Dört çıktı satırını yaz:

```python
import json
openai_args = '{"sehir": "Ankara", "gun": 2}'
ollama_args = {"sehir": "Ankara", "gun": 2}
print(type(openai_args).__name__, type(ollama_args).__name__)
print(json.loads(openai_args) == ollama_args)
turlar = [["c1", "c2"], ["c3"], []]
sonuclar = [{"role": "tool", "tool_call_id": i} for t in turlar for i in t]
print(len(sonuclar), sonuclar[-1]["tool_call_id"])
print(next(n for n, t in enumerate(turlar, 1) if not t))
```

???

```cikti
str dict
True
3 c3
3
```

İlk satır aynı argümanın OpenAI'de string, Ollama yerel biçiminde nesne olduğunu gösterir. İkinci satır string çözüldükten sonra iki biçimin aynı iç değere indiğini gösterir. Üçüncü satır her çağrı kimliğine bir sonuç mesajı düştüğünü ve sonuçların çağrı sırasını izlediğini gösterir. Dördüncü satır döngünün araç çağrısı içermeyen ilk model yanıtında, yani üçüncü turda durduğunu gösterir.
:::

::: gorev 1 · İki tel biçimindeki araç çağrılarını şemaya göre normalize et
`cagrilari_normalize(mesaj, bicim, araclar)` işlevini yaz. `bicim` tam olarak `"openai"` veya `"ollama"` stringidir. `araclar` boş olmayan sözlüktür: anahtarı boş olmayan string araç adı, değeri tam `required`, `properties` anahtarlı şema sözlüğüdür. `properties` sözlüğünün (boş olabilir) anahtarları boş olmayan string alan adları, değerleri `"string"` veya `"integer"`dir; `required`, `properties` içinde bulunan alan adlarının yinelenmeyen listesidir (boş olabilir). `mesaj` tam `role`, `content`, `tool_calls` anahtarlı sözlüktür: `role` `"assistant"`, `content` string veya `None`, `tool_calls` 1–8 öğeli listedir.

OpenAI biçiminde her çağrı tam `id`, `type`, `function` anahtarlı sözlüktür: `type` `"function"`, `function` tam `name`, `arguments` anahtarlı sözlük, `arguments` ise JSON object'e çözülen bir stringdir. Ollama biçiminde her çağrı `function` anahtarını taşıyan, isteğe bağlı olarak `id` ve `type` anahtarlarını da içerebilen ve başka anahtarı olmayan sözlüktür; `type` varsa `"function"` olmalıdır. Ollama'da `function` tam `index`, `name`, `arguments` anahtarlı sözlüktür; `index` çağrının listedeki 0'dan başlayan sırasına eşit bool olmayan int, `arguments` doğrudan sözlüktür. Kimlik `id` anahtarı varsa onun değeri, yoksa `"ollama-" + str(index)` olur; kimlik boş olmayan string olmalı ve aynı mesajda yinelenmemelidir. Her iki biçimde `name`, `araclar` anahtarlarından biri olan stringdir ve argüman sözlüğü o aracın şemasına uymalıdır: yalnız `properties` alanlarını ve `required` alanlarının hepsini içerir; `"string"` alanın değeri `str`, `"integer"` alanın değeri bool olmayan `int`'tir. OpenAI JSON argümanında yinelenen anahtar da geçersizdir. Geçersiz veride `ValueError` yükselt.

Çağrı sırasıyla `{"id": ..., "ad": ..., "argumanlar": ...}` sözlüklerinin listesini döndür; `argumanlar` çözülmüş argüman sözlüğüdür. Aracı çalıştırma. Girdileri değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-23")
```

```starter
from ai_temel_veri import json_yukle
def cagrilari_normalize(mesaj, bicim, araclar):
    # KUSURLU BAŞLANGIÇ KODU: kimlikleri yeniden üretir, şemayı doğrulamadan argümanı kabul eder.
    import json
    out=[]
    for c in mesaj["tool_calls"]:
        f=c["function"];arg=f["arguments"]
        out.append({"id":"ayni-kimlik","ad":f["name"],"argumanlar":json.loads(arg) if isinstance(arg,str) else arg})
    return out

v=json_yukle("veri/cagrilar.json")
for bicim in ("openai","ollama"):
    print("Sentetik ham çağrı:",bicim,v[bicim])
    print("Normalize:",cagrilari_normalize(v[bicim],bicim,v["semalar"]))
```

```test
import copy
A = {"hava": {"required": ["sehir"], "properties": {"sehir": "string", "gun": "integer"}}, "saat": {"required": [], "properties": {}}}
def oc(kimlik="call_x", ad="saat", arg="{}", tur="function"):
    return {"id": kimlik, "type": tur, "function": {"name": ad, "arguments": arg}}
def lc(i, ad="saat", arg=None, **ek):
    return dict(ek, function={"index": i, "name": ad, "arguments": {} if arg is None else arg})
def msj(cagrilar, icerik=None):
    return {"role": "assistant", "content": icerik, "tool_calls": cagrilar}
def sema(**d):
    return dict(A, hava=dict(A["hava"], **d))
def ha(arg):
    return msj([oc(ad="hava", arg=arg)])
OA = msj([oc("call_a", "hava", '{"sehir": "Ankara"}'), oc("call_b")])
OL = msj([lc(0), lc(1, "hava", {"sehir": "Ankara", "gun": 2})], "")
OY = msj([lc(0, id="call_k"), lc(1, "hava", {"sehir": "Van"}, id="call_m", type="function")], "")
def sozlesme(fn):
    try:
        oa, ol, oy, a = copy.deepcopy(OA), copy.deepcopy(OL), copy.deepcopy(OY), copy.deepcopy(A)
        if fn(oa, "openai", a) != [{"id": "call_a", "ad": "hava", "argumanlar": {"sehir": "Ankara"}}, {"id": "call_b", "ad": "saat", "argumanlar": {}}]:
            return False
        if fn(ol, "ollama", a) != [{"id": "ollama-0", "ad": "saat", "argumanlar": {}}, {"id": "ollama-1", "ad": "hava", "argumanlar": {"sehir": "Ankara", "gun": 2}}]:
            return False
        if fn(oy, "ollama", a) != [{"id": "call_k", "ad": "saat", "argumanlar": {}}, {"id": "call_m", "ad": "hava", "argumanlar": {"sehir": "Van"}}]:
            return False
        if oa != OA or ol != OL or oy != OY or a != A:
            return False
        if fn(msj([oc("k", "hava", '{"gun": 3, "sehir": "Muş"}')], "metin"), "openai", {"hava": A["hava"]}) != [{"id": "k", "ad": "hava", "argumanlar": {"gun": 3, "sehir": "Muş"}}]:
            return False
        D = {"saat": {"required": [], "properties": {"dilim": "string"}}}
        if fn(msj([lc(0, type="function"), lc(1, arg={"dilim": "UTC"})]), "ollama", D) != [{"id": "ollama-0", "ad": "saat", "argumanlar": {}}, {"id": "ollama-1", "ad": "saat", "argumanlar": {"dilim": "UTC"}}]:
            return False
        if [c["id"] for c in fn(msj([oc("c" + str(i)) for i in range(8)]), "openai", A)] != ["c" + str(i) for i in range(8)]:
            return False
        if len(fn(msj([lc(i) for i in range(8)]), "ollama", A)) != 8:
            return False
        gecersiz = [
            (OA, "OpenAI", A), (OL, "yanlis", A), (OA, None, A),
            (msj([oc("a", "hava", '{"sehir": "Ankara", "gun": 2}')]), "openai", sema(properties={"sehir": "string", "gun": "number"})),
            (ha('{"sehir": "Van"}'), "openai", dict(A, saat={"required": ["il"], "properties": {}})),
            (msj([oc(arg="[]")]), "openai", A), (OA, "openai", None), (OA, "openai", {}), (OA, "openai", ["hava", "saat"]),
            (OA, "openai", dict(A, **{"": A["saat"]})), (OA, "openai", {**A, 1: A["saat"]}), (OA, "openai", dict(A, saat=None)),
            (OA, "openai", dict(A, saat={"properties": {}})), (OA, "openai", dict(A, saat=dict(A["saat"], type="object"))),
            (OA, "openai", sema(properties=["sehir"])), (OA, "openai", sema(properties={"sehir": "string", "": "string"})),
            (OA, "openai", sema(properties={"sehir": "string", 1: "string"})), (OA, "openai", sema(properties={"sehir": "number"})),
            (OA, "openai", sema(properties={"sehir": None})), (OA, "openai", sema(properties={"sehir": ["string"]})),
            (OA, "openai", sema(required=("sehir",))), (OA, "openai", sema(required=None)), (OA, "openai", sema(required=["il"])),
            (OA, "openai", sema(required=["sehir", "sehir"])), (OA, "openai", sema(required=[1])), (OA, "openai", sema(required=[["sehir"]])),
            (None, "openai", A), (dict(OA, role="user"), "openai", A), (dict(OA, ek=1), "openai", A),
            ({"role": "assistant", "tool_calls": OA["tool_calls"]}, "openai", A), (dict(OA, content=1), "openai", A),
            (dict(OA, content=b""), "openai", A), (msj([]), "openai", A), (msj(None), "openai", A),
            (msj({"x": oc()}), "openai", A), (msj(tuple(OA["tool_calls"])), "openai", A), (msj([oc("c" + str(i)) for i in range(9)]), "openai", A),
            (msj([None]), "openai", A), (msj([["id", "type", "function"]]), "openai", A), (msj([dict(oc(), ek=1)]), "openai", A),
            (msj([{"type": "function", "function": {"name": "saat", "arguments": "{}"}}]), "openai", A),
            (msj([{"id": "a", "function": {"name": "saat", "arguments": "{}"}}]), "openai", A),
            (msj([oc("")]), "openai", A), (msj([oc(1)]), "openai", A), (msj([oc(tur="tool")]), "openai", A),
            (msj([dict(oc(), function=["name", "arguments"])]), "openai", A),
            (msj([dict(oc(), function={"name": "saat", "arguments": "{}", "ek": 1})]), "openai", A),
            (msj([oc(arg={})]), "openai", A), (msj([oc(arg=b"{}")]), "openai", A), (msj([oc(arg="{bozuk")]), "openai", A),
            (msj([oc(arg="[1]")]), "openai", A), (msj([oc(arg='"x"')]), "openai", A), (msj([oc(ad="sil")]), "openai", A),
            (msj([oc(ad=None)]), "openai", A), (msj([oc(ad=["saat"])]), "openai", A), (msj([oc("ayni"), oc("ayni")]), "openai", A),
            (ha('{"sehir":"Ankara","sehir":"Van"}'),"openai",A),
            (ha('{"il": "Van"}'), "openai", A), (ha('{"sehir": 1}'), "openai", A), (ha('{"sehir": "Van", "gun": true}'), "openai", A),
            (ha('{"sehir": "Van", "gun": 2.0}'), "openai", A), (ha('{"sehir": "Van", "gun": "2"}'), "openai", A),
            (ha('{"sehir": "Van", "ek": "x"}'), "openai", A), (ha('{"gun": 2}'), "openai", A), (ha("{}"), "openai", A),
            (OL, "openai", A), (OA, "ollama", A), (msj([lc(1)]), "ollama", A), (msj([lc(0), lc(True)]), "ollama", A),
            (msj([lc("0")]), "ollama", A), (msj([lc(0.0)]), "ollama", A), (msj([lc(0), lc(0)]), "ollama", A),
            (msj([lc(0, arg='{"a": 1}')]), "ollama", A), (msj([lc(0, arg=[1])]), "ollama", A), (msj([lc(0, "sil")]), "ollama", A),
            (msj([lc(0, type="tool")]), "ollama", A), (msj([lc(0, id="")]), "ollama", A), (msj([lc(0, id=1)]), "ollama", A),
            (msj([lc(0, ek=1)]), "ollama", A), (msj([{"id": "a"}]), "ollama", A), (msj([None]), "ollama", A),
            (msj([{"function": {"name": "saat", "arguments": {}}}]), "ollama", A),
            (msj([{"function": {"index": 0, "name": "saat", "arguments": {}, "ek": 1}}]), "ollama", A),
            (msj([{"function": ["index", "name", "arguments"]}]), "ollama", A), (msj([lc(i) for i in range(9)]), "ollama", A),
            (msj([lc(0, id="a"), lc(1, id="a")]), "ollama", A), (msj([lc(0), lc(1, id="ollama-0")]), "ollama", A),
            (msj([lc(0, "hava", {"il": "Van"})]), "ollama", A), (msj([lc(0, "hava", {"sehir": b"Van"})]), "ollama", A),
            (msj([lc(0, "hava", {"sehir": "Van", "gun": True})]), "ollama", A),
        ]
        for args in gecersiz:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(cagrilari_normalize), "iki tel biçimi, kimlik tekilliği ve argüman şeması korunmalı")
def m_sira(m, b, a):
    return list(reversed(cagrilari_normalize(m, b, a)))
def m_kimlik(m, b, a):
    return [dict(c, id="ollama-" + str(i)) for i, c in enumerate(cagrilari_normalize(m, b, a))]
def m_gevsek(m, b, a):
    return cagrilari_normalize(m, b, {k: dict(v, required=[]) for k, v in a.items()} if isinstance(a, dict) else a)
for ad, mutant in [("çağrı sırasını bozan", m_sira), ("model kimliğini atan", m_kimlik), ("zorunlu alanı düşüren", m_gevsek)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle
def cagrilari_normalize(mesaj, bicim, araclar):
    import json
    def nesne(ciftler):
        out={}
        for key,value in ciftler:
            if key in out: raise ValueError("yinelenen anahtar")
            out[key]=value
        return out
    if bicim not in ("openai", "ollama") or not isinstance(araclar, dict) or not araclar:
        raise ValueError("girdi")
    for ad, s in araclar.items():
        if not isinstance(ad, str) or not ad or not isinstance(s, dict) or set(s) != {"required", "properties"}:
            raise ValueError("şema")
        p, r = s["properties"], s["required"]
        if not isinstance(p, dict) or any(not isinstance(k, str) or not k or v not in ("string", "integer") for k, v in p.items()):
            raise ValueError("şema")
        if not isinstance(r, list) or any(not isinstance(k, str) or k not in p for k in r) or len(set(r)) != len(r):
            raise ValueError("şema")
    if not isinstance(mesaj, dict) or set(mesaj) != {"role", "content", "tool_calls"} or mesaj["role"] != "assistant":
        raise ValueError("mesaj")
    if mesaj["content"] is not None and not isinstance(mesaj["content"], str):
        raise ValueError("içerik")
    cagrilar = mesaj["tool_calls"]
    if not isinstance(cagrilar, list) or not 1 <= len(cagrilar) <= 8:
        raise ValueError("çağrılar")
    sonuc = []
    for i, c in enumerate(cagrilar):
        if not isinstance(c, dict) or not {"function"} <= set(c) <= {"id", "type", "function"} or c.get("type", "function") != "function":
            raise ValueError("çağrı")
        f = c["function"]
        if bicim == "openai":
            if set(c) != {"id", "type", "function"} or not isinstance(f, dict) or set(f) != {"name", "arguments"} or not isinstance(f["arguments"], str):
                raise ValueError("openai")
            arg = json.loads(f["arguments"],object_pairs_hook=nesne)
        else:
            if not isinstance(f, dict) or set(f) != {"index", "name", "arguments"} or type(f["index"]) is not int or f["index"] != i:
                raise ValueError("ollama")
            arg = f["arguments"]
        kimlik = c["id"] if "id" in c else "ollama-" + str(i)
        if not isinstance(kimlik, str) or not kimlik or not isinstance(f["name"], str) or f["name"] not in araclar or not isinstance(arg, dict):
            raise ValueError("çağrı")
        s = araclar[f["name"]]
        if not set(s["required"]) <= set(arg) <= set(s["properties"]):
            raise ValueError("argüman")
        if any(type(v) is not (str if s["properties"][k] == "string" else int) for k, v in arg.items()):
            raise ValueError("argüman")
        sonuc.append({"id": kimlik, "ad": f["name"], "argumanlar": arg})
    if len({s["id"] for s in sonuc}) != len(sonuc):
        raise ValueError("kimlik")
    return sonuc

if __name__ == "__main__":
    v=json_yukle("veri/cagrilar.json")
    for bicim in ("openai","ollama"):
        print("Sentetik ham çağrı:",bicim,v[bicim])
        print("Normalize:",cagrilari_normalize(v[bicim],bicim,v["semalar"]))
```

```hint
Önce şemaları, sonra mesajı, en son her çağrıyı denetle. OpenAI'de `json.loads` sonucunun da sözlük olduğunu ayrıca kontrol et, çünkü `"[1]"` geçerli JSON'dur ama nesne değildir. Argümanın anahtar kümesi `required` ile `properties` arasında kalmalıdır; tür için `type(x) is int` kullan, çünkü `True == 1` olduğundan `isinstance` bool'u kaçırır.
```
:::

::: gorev 2 · Çağrıları yürüt ve kimlik başına sonuç mesajı üret
`cagrilari_yurut(cagrilar, kayit)` işlevini yaz. `kayit` boş olmayan sözlüktür; anahtarları string araç adı, değerleri çağrılabilir nesnedir. `cagrilar` 1–8 öğeli listedir; her öğe tam `id`, `ad`, `argumanlar` anahtarlı sözlüktür: `id` boş olmayan string, `ad` `kayit` içinde bulunan string, `argumanlar` sözlüktür. Kimlikler yinelenemez. Geçersiz veride `ValueError` yükselt; bütün doğrulama hiçbir araç çalışmadan önce bitmelidir.

Çağrıları liste sırasıyla `kayit[ad](**argumanlar)` biçiminde yürüt. Dönen değer string ise içerik odur; değilse `json.dumps(deger, ensure_ascii=False, sort_keys=True)` sonucudur. Araç çağrısı veya JSON'a çevirme sırasında herhangi bir `Exception` oluşursa içerik `"HATA: " + istisna sınıfının adı` olur ve yürütme sonraki çağrıyla sürer; istisna mesajını içeriğe koyma. `Exception` sınıfından türemeyen istisnalar (ör. `SystemExit`) yakalanmaz.

Her çağrı için bir `{"role": "tool", "tool_call_id": id, "content": icerik}` sözlüğü üret ve listeyi çağrı sırasıyla döndür. Girdileri değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-23")
```

```starter
from ai_temel_veri import json_yukle
def cagrilari_yurut(cagrilar, kayit):
    # KUSURLU BAŞLANGIÇ KODU: yalnız ilk çağrıyı çalıştırır, sonucu çağrı kimliği yerine araç adına bağlar.
    import json
    c=next(iter(cagrilar));v=kayit[c["ad"]](**c["argumanlar"])
    return [{"role":"tool","tool_call_id":c["ad"],"content":v if isinstance(v,str) else json.dumps(v,ensure_ascii=False,sort_keys=True)}]

def _ornek_araclar(v):
    return {"hava":lambda sehir:dict(v["arac_sonuclari"]["hava"],sehir=sehir),"saat":lambda:v["arac_sonuclari"]["saat"]}
v=json_yukle("veri/cagrilar.json")
print("Sentetik normalize çağrılar:",v["normalize"])
print("Sonuç mesajları:",cagrilari_yurut(v["normalize"],_ornek_araclar(v)))
```

```test
import copy
IZ = []
def hava(sehir):
    IZ.append(sehir)
    return {"sehir": sehir, "derece": 21, "durum": "güneşli"}
def saat():
    return "12:00"
def bozuk():
    raise KeyError("SAHTE-ANAHTAR-yalniz-ornek")
def sifir():
    return 1 // 0
def kume():
    return {"a"}
def liste():
    return [None, "ç", 3]
def cik():
    raise SystemExit(3)
def ozel():
    class KotaHatasi(Exception):
        pass
    raise KotaHatasi("SAHTE-kota-yalniz-ornek")
K = {"hava": hava, "saat": saat, "bozuk": bozuk, "sifir": sifir, "kume": kume, "liste": liste, "cik": cik, "ozel": ozel}
def c(kimlik, ad="saat", arg=None):
    return {"id": kimlik, "ad": ad, "argumanlar": {} if arg is None else arg}
C = [c("c1", "hava", {"sehir": "İzmir"}), c("c2", "bozuk"), c("c3", "sifir"), c("c4"), c("c5", "kume"), c("c6", "liste")]
def sozlesme(fn):
    try:
        del IZ[:]
        cc, kk = copy.deepcopy(C), dict(K)
        beklenen = ['{"derece": 21, "durum": "güneşli", "sehir": "İzmir"}', "HATA: KeyError", "HATA: ZeroDivisionError", "12:00", "HATA: TypeError", '[null, "ç", 3]']
        if fn(cc, kk) != [{"role": "tool", "tool_call_id": "c" + str(i + 1), "content": b} for i, b in enumerate(beklenen)]:
            return False
        if IZ != ["İzmir"] or cc != C or kk != K:
            return False
        if fn([c("tek", "hava", {"sehir": "Muş"})], {"hava": hava}) != [{"role": "tool", "tool_call_id": "tek", "content": '{"derece": 21, "durum": "güneşli", "sehir": "Muş"}'}]:
            return False
        if fn([c("o1", "ozel")], K) != [{"role": "tool", "tool_call_id": "o1", "content": "HATA: KotaHatasi"}]:
            return False
        if [m["tool_call_id"] for m in fn([c("k" + str(i)) for i in range(8)], K)] != ["k" + str(i) for i in range(8)]:
            return False
        try:
            fn([c("s1"), c("s2", "cik"), c("s3")], K)
            return False
        except SystemExit:
            pass
        del IZ[:]
        gecersiz = [
            (C, None), (C, {}), (C, dict(K, saat="x")), (C, {**K, 1: saat}), (C, list(K)), (None, K), ([], K), ({"c1": c("c1")}, K),
            (tuple(C), K), ([c("k" + str(i)) for i in range(9)], K), ([None], K), ([c("")], K), ([c(1)], K), ([c("a", "yok")], K),
            ([c("a", None)], K), ([c("a", ["saat"])], K), ([c("a", "saat", "{}")], K), ([dict(c("a"), ek=1)], K),
            ([{"id": "a", "ad": "saat"}], K), ([c("a"), c("a")], K), ([c("v", "hava", {"sehir": "Van"}), c("w", "yok")], K),
            ([c("v", "hava", {"sehir": "Van"}), c("v")], K),
        ]
        for args in gecersiz:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return IZ == []
    except Exception:
        return False
ok(sozlesme(cagrilari_yurut), "çağrı sırası, kimlik eşlemesi ve hata içeriği korunmalı")
def m_teker(cc, kk):
    if not isinstance(cc, list) or not cc:
        raise ValueError("liste")
    return [m for x in cc for m in cagrilari_yurut([x], kk)]
def m_yutan(cc, kk):
    return [dict(m, content="") if m["content"].startswith("HATA") else m for m in cagrilari_yurut(cc, kk)]
def m_ad(cc, kk):
    return [dict(m, tool_call_id=x["ad"]) for m, x in zip(cagrilari_yurut(cc, kk), cc)]
for ad, mutant in [("doğrulamadan önce yürüten", m_teker), ("hatayı yutan", m_yutan), ("kimlik yerine ad eşleyen", m_ad)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle
def cagrilari_yurut(cagrilar, kayit):
    import json
    if not isinstance(kayit, dict) or any(not isinstance(k, str) or not callable(v) for k, v in kayit.items()):
        raise ValueError("kayıt")
    if not isinstance(cagrilar, list) or not 1 <= len(cagrilar) <= 8:
        raise ValueError("çağrılar")
    for c in cagrilar:
        if not isinstance(c, dict) or set(c) != {"id", "ad", "argumanlar"} or not isinstance(c["id"], str) or not c["id"]:
            raise ValueError("çağrı")
        if not isinstance(c["ad"], str) or c["ad"] not in kayit or not isinstance(c["argumanlar"], dict):
            raise ValueError("çağrı")
    if len({c["id"] for c in cagrilar}) != len(cagrilar):
        raise ValueError("kimlik")
    mesajlar = []
    for c in cagrilar:
        try:
            deger = kayit[c["ad"]](**c["argumanlar"])
            icerik = deger if isinstance(deger, str) else json.dumps(deger, ensure_ascii=False, sort_keys=True)
        except Exception as e:
            icerik = "HATA: " + type(e).__name__
        mesajlar.append({"role": "tool", "tool_call_id": c["id"], "content": icerik})
    return mesajlar

if __name__ == "__main__":
    def _ornek_araclar(v):
        return {"hava":lambda sehir:dict(v["arac_sonuclari"]["hava"],sehir=sehir),"saat":lambda:v["arac_sonuclari"]["saat"]}
    v=json_yukle("veri/cagrilar.json")
    print("Sentetik normalize çağrılar:",v["normalize"])
    print("Sonuç mesajları:",cagrilari_yurut(v["normalize"],_ornek_araclar(v)))
```

```hint
İki ayrı döngü kur: ilki yalnız doğrular, ikincisi yürütür. `try` bloğunun içine hem araç çağrısını hem `json.dumps` satırını al; küme gibi JSON'a çevrilemeyen bir sonuç da `TypeError` üretir. `BaseException` yakalamak `SystemExit` gibi süreci durdurma isteklerini de yutar.
```
:::

::: gorev 3 · Adım bütçeli ajan döngüsünü kur
`ajan_dongusu(model, araclar, istek, max_adim)` işlevini yaz. `model` çağrılabilir nesnedir. `araclar` boş olmayan sözlüktür; anahtarları string, değerleri çağrılabilirdir. `istek` boş olmayan stringdir. `max_adim` 1–10 arası bool olmayan int'tir.

Geçmiş `[{"role": "user", "content": istek}]` ile başlar. Her turda `model(gecmisin_derin_kopyasi)` çağır. Dönen mesaj tam `role`, `content`, `tool_calls` anahtarlı sözlük olmalıdır: `role` `"assistant"`, `content` string, `tool_calls` 0–4 öğeli listedir. Her çağrı tam `id`, `ad`, `argumanlar` anahtarlı sözlüktür: `id` boş olmayan string, `ad` `araclar` içinde bulunan string, `argumanlar` sözlüktür. Bir `id` bütün döngü boyunca yalnız bir kez kullanılabilir. Geçersiz girdi veya geçersiz model mesajında `ValueError` yükselt; bir mesajın bütün çağrıları, hiçbiri çalışmadan önce doğrulanır.

Geçerli mesajı geçmişe ekle. `tool_calls` boşsa `{"durum": "tamam", "adim": tur_sayisi, "yanit": content, "gecmis": gecmis}` döndür. Doluysa çağrıları sırayla `araclar[ad](**argumanlar)` ile yürüt ve her biri için `{"role": "tool", "tool_call_id": id, "content": icerik}` ekle; içerik Görev 2'deki kuralla üretilir: string sonuç olduğu gibi kalır, diğerleri `json.dumps(deger, ensure_ascii=False, sort_keys=True)` sonucudur, yürütme veya çevirme sırasında oluşan `Exception` için `"HATA: " + sınıf adı` olur ve döngü sürer; `Exception` sınıfından türemeyen istisnalar (ör. `SystemExit`) yakalanmaz. Model en çok `max_adim` kez çağrılır; son turda gelen çağrılar da yürütülüp sonuçları eklenir, ardından `{"durum": "adim_siniri", "adim": max_adim, "yanit": None, "gecmis": gecmis}` döndür. `tur_sayisi` modelin kaçıncı çağrısında durulduğudur.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-23")
```

```starter
from ai_temel_veri import json_yukle
def ajan_dongusu(model, araclar, istek, max_adim):
    # KUSURLU BAŞLANGIÇ KODU: araç çağrıları varken tamam sayar ve hiçbir sonucu modele geri göndermez.
    g=[{"role":"user","content":istek}];m=model(g)
    return {"durum":"tamam","adim":1,"yanit":m["content"],"gecmis":g+[m]}

def _ornek_araclar(v):
    return {"hava":lambda sehir:dict(v["arac_sonuclari"]["hava"],sehir=sehir),"saat":lambda:v["arac_sonuclari"]["saat"]}
import copy
v=json_yukle("veri/cagrilar.json");a=json_yukle("veri/ajan.json")
adimlar=iter(a["model_betigi"])
def ornek_model(gecmis): return copy.deepcopy(next(adimlar))
print("Sentetik model betiği:",a)
print("Döngü:",ajan_dongusu(ornek_model,_ornek_araclar(v),a["istek"],a["max_adim"]))
```

```test
import copy
def hava(sehir):
    return {"sehir": sehir, "derece": 18, "durum": "güneşli"}
def bozuk():
    raise KeyError("SAHTE-yalniz-ornek")
def saat():
    return "12:00"
def kume():
    return {"a"}
def sifir():
    return 1 // 0
AR = {"hava": hava, "bozuk": bozuk, "saat": saat, "kume": kume, "sifir": sifir}
def asis(cagrilar, icerik=""):
    return {"role": "assistant", "content": icerik, "tool_calls": cagrilar}
def c(kimlik, ad="saat", arg=None):
    return {"id": kimlik, "ad": ad, "argumanlar": {} if arg is None else arg}
def betik(*yanitlar):
    def model(g):
        y = yanitlar[sum(1 for m in g if m["role"] == "assistant")]
        return y(g) if callable(y) else copy.deepcopy(y)
    return model
T1 = asis([c("c1", "hava", {"sehir": "İzmir"}), c("c2", "bozuk")])
T2 = asis([c("x1", "kume"), c("x2", "sifir")])
SON = lambda g: asis([], "Özet: " + g[2]["content"] + " | " + g[-1]["content"])
def sonsuz(g):
    return asis([c("t" + str(len(g)))])
def sozlesme(fn):
    try:
        goruntu = []
        ic = betik(T1, T2, SON)
        def kaydeden(g):
            goruntu.append(copy.deepcopy(g))
            y = ic(g)
            g[0]["content"] = "bozuldu"
            g.append({"role": "user", "content": "enjekte"})
            return y
        U = {"role": "user", "content": "İzmir hava?"}
        A1 = {"role": "tool", "tool_call_id": "c1", "content": '{"derece": 18, "durum": "güneşli", "sehir": "İzmir"}'}
        A2 = {"role": "tool", "tool_call_id": "c2", "content": "HATA: KeyError"}
        X1 = {"role": "tool", "tool_call_id": "x1", "content": "HATA: TypeError"}
        X2 = {"role": "tool", "tool_call_id": "x2", "content": "HATA: ZeroDivisionError"}
        Y = "Özet: " + A1["content"] + " | HATA: ZeroDivisionError"
        ar = dict(AR)
        r = fn(kaydeden, ar, "İzmir hava?", 3)
        if r != {"durum": "tamam", "adim": 3, "yanit": Y, "gecmis": [U, T1, A1, A2, T2, X1, X2, asis([], Y)]}:
            return False
        if goruntu != [[U], [U, T1, A1, A2], [U, T1, A1, A2, T2, X1, X2]] or ar != AR:
            return False
        if fn(betik(asis([], "hemen")), AR, "x", 1) != {"durum": "tamam", "adim": 1, "yanit": "hemen", "gecmis": [{"role": "user", "content": "x"}, asis([], "hemen")]}:
            return False
        b = fn(sonsuz, AR, "x", 2)
        if b["durum"] != "adim_siniri" or b["adim"] != 2 or b["yanit"] is not None or [m.get("tool_call_id") for m in b["gecmis"]] != [None, None, "t1", None, "t3"]:
            return False
        b = fn(sonsuz, AR, "x", 1)
        if b != {"durum": "adim_siniri", "adim": 1, "yanit": None, "gecmis": [{"role": "user", "content": "x"}, asis([c("t1")]), {"role": "tool", "tool_call_id": "t1", "content": "12:00"}]}:
            return False
        if fn(sonsuz, AR, "x", 10)["adim"] != 10 or len(fn(sonsuz, AR, "x", 10)["gecmis"]) != 21:
            return False
        dort = fn(betik(asis([c("d" + str(i)) for i in range(4)]), asis([], "son")), AR, "x", 2)
        if dort["durum"] != "tamam" or len(dort["gecmis"]) != 7:
            return False
        def cik():
            raise SystemExit(3)
        try:
            fn(betik(asis([c("s1", "cik")]), asis([], "son")), dict(AR, cik=cik), "x", 2)
            return False
        except SystemExit:
            pass
        tamam = betik(asis([], "son"))
        gecersiz = [
            (None, AR, "x", 2), (tamam, {}, "x", 2), (tamam, None, "x", 2), (tamam, ["saat"], "x", 2), (tamam, {"saat": 1}, "x", 2), (tamam, {1: saat}, "x", 2),
            (tamam, AR, "", 2), (tamam, AR, b"x", 2), (tamam, AR, None, 2), (tamam, AR, "x", 0), (tamam, AR, "x", 11),
            (tamam, AR, "x", True), (tamam, AR, "x", 2.0), (tamam, AR, "x", "2"),
            (betik(None), AR, "x", 2), (betik(dict(asis([]), role="user")), AR, "x", 2), (betik(asis([], None)), AR, "x", 2),
            (betik(dict(asis([]), ek=1)), AR, "x", 2), (betik({"role": "assistant", "content": ""}), AR, "x", 2),
            (betik(asis(None)), AR, "x", 2), (betik(asis(())), AR, "x", 2), (betik(asis([c("e" + str(i)) for i in range(5)])), AR, "x", 2),
            (betik(asis([c("a"), c("a")])), AR, "x", 2), (betik(asis([c("a")]), asis([c("a")])), AR, "x", 3),
            (betik(asis([c("")])), AR, "x", 2), (betik(asis([c(1)])), AR, "x", 2), (betik(asis([c("a", "sil")])), AR, "x", 2),
            (betik(asis([c("a", ["saat"])])), AR, "x", 2), (betik(asis([c("a", "saat", "{}")])), AR, "x", 2),
            (betik(asis([None])), AR, "x", 2), (betik(asis([dict(c("a"), ek=1)])), AR, "x", 2),
        ]
        for args in gecersiz:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        sayac = []
        def izleyen():
            sayac.append(1)
            return "ok"
        try:
            fn(betik(asis([c("v", "izle"), c("w", "yok")])), {"izle": izleyen}, "x", 2)
            return False
        except ValueError:
            pass
        return sayac == []
    except Exception:
        return False
ok(sozlesme(ajan_dongusu), "döngü bütçesi, durma nedeni, döküm ve kimlik tekilliği korunmalı")
def m_butce(md, ar, ist, n):
    return ajan_dongusu(md, ar, ist, n + 1)
def m_kor(md, ar, ist, n):
    return ajan_dongusu(lambda g: md([m for m in g if m["role"] != "tool"]), ar, ist, n)
def m_durum(md, ar, ist, n):
    return dict(ajan_dongusu(md, ar, ist, n), durum="tamam")
for ad, mutant in [("bütçeyi aşan", m_butce), ("sonucu modele göstermeyen", m_kor), ("durma nedenini gizleyen", m_durum)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle
def ajan_dongusu(model, araclar, istek, max_adim):
    import copy, json
    if not callable(model) or not isinstance(araclar, dict) or not araclar or any(not isinstance(k, str) or not callable(v) for k, v in araclar.items()):
        raise ValueError("girdi")
    if not isinstance(istek, str) or not istek or type(max_adim) is not int or not 1 <= max_adim <= 10:
        raise ValueError("girdi")
    gecmis = [{"role": "user", "content": istek}]
    gorulen = set()
    for tur in range(1, max_adim + 1):
        m = model(copy.deepcopy(gecmis))
        if not isinstance(m, dict) or set(m) != {"role", "content", "tool_calls"} or m["role"] != "assistant" or not isinstance(m["content"], str):
            raise ValueError("mesaj")
        if not isinstance(m["tool_calls"], list) or len(m["tool_calls"]) > 4:
            raise ValueError("mesaj")
        for c in m["tool_calls"]:
            if not isinstance(c, dict) or set(c) != {"id", "ad", "argumanlar"} or not isinstance(c["id"], str) or not c["id"] or c["id"] in gorulen:
                raise ValueError("çağrı")
            if not isinstance(c["ad"], str) or c["ad"] not in araclar or not isinstance(c["argumanlar"], dict):
                raise ValueError("çağrı")
            gorulen.add(c["id"])
        gecmis.append(m)
        if not m["tool_calls"]:
            return {"durum": "tamam", "adim": tur, "yanit": m["content"], "gecmis": gecmis}
        for c in m["tool_calls"]:
            try:
                deger = araclar[c["ad"]](**c["argumanlar"])
                icerik = deger if isinstance(deger, str) else json.dumps(deger, ensure_ascii=False, sort_keys=True)
            except Exception as e:
                icerik = "HATA: " + type(e).__name__
            gecmis.append({"role": "tool", "tool_call_id": c["id"], "content": icerik})
    return {"durum": "adim_siniri", "adim": max_adim, "yanit": None, "gecmis": gecmis}

if __name__ == "__main__":
    def _ornek_araclar(v):
        return {"hava":lambda sehir:dict(v["arac_sonuclari"]["hava"],sehir=sehir),"saat":lambda:v["arac_sonuclari"]["saat"]}
    import copy
    v=json_yukle("veri/cagrilar.json");a=json_yukle("veri/ajan.json")
    adimlar=iter(a["model_betigi"])
    def ornek_model(gecmis): return copy.deepcopy(next(adimlar))
    print("Sentetik model betiği:",a)
    print("Döngü:",ajan_dongusu(ornek_model,_ornek_araclar(v),a["istek"],a["max_adim"]))
```

```hint
Döngüden önce görülen kimlikler için bir küme tut ve her mesajın çağrılarını yürütmeden önce o kümeye karşı denetle. Model çağrısını `range(1, max_adim + 1)` ile sınırla; döngüden normal çıkış, bütçenin bittiği anlamına gelir. Sonuç içeriği için Görev 2'deki yardımcı mantığı yeniden kullanabilirsin.
```
:::

::: gorev Gerçek deney · Şemalı dispatch ve gerçek ajan döngüsü
`arac_calistir(cagri, semalar, araclar)` işlevini yaz.

- Doğrulama (yapı bozuksa `ValueError`): `cagri` tam `ad` (boş olmayan str) ve `arg` (sözlük) anahtarlı sözlük. `semalar` araç adları boş olmayan string olan sözlüktür; gerekli alanları boş olmayan stringlerden oluşan, yinelenmeyen listelerdir. Her değeri `gerekli` (string listesi) ve `tipler` (anahtar→`"sayi"`/`"metin"` sözlüğü) anahtarlı sözlük ve `tipler`'in anahtarları `gerekli` ile aynı. `araclar` sözlüktür; anahtarları `semalar` ile aynı, değerleri çağrılabilir.
- Çağrıyı değerlendir (modelin hatasında **yükseltme**, hata sözlüğü döndür): `ad` `semalar`'da yoksa `{"durum": "hata", "hata": "..."}`. `arg` anahtarları şemanın `gerekli`siyle birebir değilse hata. Bir argümanın tipi şemaya uymuyorsa (`"sayi"` → bool olmayan sonlu int/float, `"metin"` → str) hata. Hepsi geçerliyse `araclar[ad](**arg)` çalıştır; işlev hata verirse de hata sözlüğü döndür. Başarıda `{"durum": "ok", "sonuc": dönen değer}`.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab
import math

def arac_calistir(cagri, semalar, araclar):
    return {"durum": "hata", "hata": "yazılmadı"}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_23 as deney
    deney.goster(arac_calistir)
```

```test
import ai_lab
sonuclar = []
def kontrol(kosul, mesaj):
    sonuclar.append(bool(kosul))
    return ok(kosul, mesaj)
import ast
_yasak=("referans","referans_calistir","getattr","kanit_yaz")
sorun=ai_lab.kod_denetimi(src,yasak=_yasak)
for n in ast.walk(ast.parse(src)):
    if isinstance(n,ast.ImportFrom) and any(a.name in _yasak or a.name=="*" for a in n.names): sorun.append("referans importu yasak")
if not kontrol(not sorun,"Kendi dispatch işlevini yaz: "+"; ".join(sorun)): stop()
fn = need("arac_calistir")
from sandbox import ai_gercek_ai_temel_23 as D
SEMA = {"topla": {"gerekli": ["a", "b"], "tipler": {"a": "sayi", "b": "sayi"}},
        "carp": {"gerekli": ["a", "b"], "tipler": {"a": "sayi", "b": "sayi"}}}
ARAC = {"topla": lambda a, b: a + b, "carp": lambda a, b: a * b}
def sozlesme(f):
    try:
        if f({"ad": "carp", "arg": {"a": 23, "b": 19}}, SEMA, ARAC) != {"durum": "ok", "sonuc": 437}:
            return False
        if f({"ad": "topla", "arg": {"a": 4, "b": 5}}, SEMA, ARAC) != {"durum": "ok", "sonuc": 9}:
            return False
        if f({"ad": "yok", "arg": {}}, SEMA, ARAC)["durum"] != "hata":
            return False
        if f({"ad": "carp", "arg": {"a": 1}}, SEMA, ARAC)["durum"] != "hata":
            return False
        if f({"ad": "carp", "arg": {"a": 1, "b": "2"}}, SEMA, ARAC)["durum"] != "hata":
            return False
        if f({"ad": "carp", "arg": {"a": 1, "b": True}}, SEMA, ARAC)["durum"] != "hata":
            return False
        import copy
        h={"ad":"topla","arg":{"a":1,"b":2}};once=copy.deepcopy((h,SEMA))
        if f(h,SEMA,ARAC)!={"durum":"ok","sonuc":3} or (h,SEMA)!=once: return False
        for v in (float("nan"),float("inf")):
            if f({"ad":"topla","arg":{"a":v,"b":2}},SEMA,ARAC)["durum"]!="hata": return False
        if f({"ad":"topla","arg":{"a":1.5,"b":2.5}},SEMA,ARAC)!={"durum":"ok","sonuc":4.0}: return False
        met={"yaz":{"gerekli":["x"],"tipler":{"x":"metin"}}}
        if f({"ad":"yaz","arg":{"x":"örnek"}},met,{"yaz":lambda x:x})!={"durum":"ok","sonuc":"örnek"}: return False
        if f({"ad":"yaz","arg":{"x":123}},met,{"yaz":lambda x:x}).get("durum")!="hata": return False
        def patla(a,b): raise KeyError("SAHTE-SIR-TEST")
        hata=f(h,SEMA,dict(ARAC,topla=patla))
        if hata.get("durum")!="hata" or "KeyError" not in hata.get("hata","") or "SAHTE-SIR-TEST" in str(hata): return False
        iz=[]
        def izle(a,b): iz.append(1);return a+b
        if f({"ad":"topla","arg":{"a":True,"b":2}},SEMA,dict(ARAC,topla=izle))["durum"]!="hata" or iz:return False
        for kotu in [({"ad": 1, "arg": {}}, SEMA, ARAC), (h, None, ARAC), (h, SEMA, None), (h, {"x": SEMA["topla"]}, ARAC),
                     (h, {"": {"gerekli": [], "tipler": {}}}, {"": lambda: 0}), (h, {1: {"gerekli": [], "tipler": {}}}, {1: lambda: 0}),
                     (h, {"x": None}, {"x": lambda: 0}), (h, {"x": {"gerekli": []}}, {"x": lambda: 0}),
                     (h, {"x": {"gerekli": (), "tipler": {}}}, {"x": lambda: 0}), (h, {"x": {"gerekli": [], "tipler": []}}, {"x": lambda: 0}),
                     (h, {"x": {"gerekli": ["a"], "tipler": {"b": "sayi"}}}, {"x": lambda a: a}),
                     (h, {"x": {"gerekli": ["a"], "tipler": {"a": "bool"}}}, {"x": lambda a: a}),
                     (h, {"x": {"gerekli": [""], "tipler": {"": "sayi"}}}, {"x": lambda **kw: 0}),
                     (h,{"x":{"gerekli":[["a"]],"tipler":{}}},{"x":lambda:0}),(h,{"x":{"gerekli":["a","a"],"tipler":{"a":"sayi"}}},{"x":lambda a:a}),(h,SEMA,dict(ARAC,topla=3)),(None, SEMA, ARAC), ({"ad": "carp"}, SEMA, ARAC), ({"ad": "", "arg": {}}, SEMA, ARAC),
                     ({"ad": "carp", "arg": 5}, SEMA, ARAC), ({"ad": "carp", "arg": {}, "ek": 1}, SEMA, ARAC)]:
            try:
                f(*kotu)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
kontrol(sozlesme(fn), "şema doğrulama + dispatch doğru; bozuk girdi ValueError, model hatası hata sözlüğü")
for ad, kw in [("şema doğrulamayı atlayan", {"sema_yok": True}), ("tip doğrulamayı atlayan", {"tip_yok": True})]:
    kontrol(not sozlesme(lambda c, s, a, kw=kw: D.referans_calistir(c, s, a, **kw)), "hatalı çözüm reddedilmeli: " + ad)
r, oz = None, None
if all(sonuclar):
    try:
        r = D.deney(fn)
    except ai_lab.GercekLabYok as e:
        kontrol(False, f"GERÇEK MODEL YOK, deney yapılmadı: {e}")
        stop()
    kontrol(r["hata"] is None, f"ajan döngüsü hatasız koştu: {r['hata']}")
    kontrol(r["durum"] in ("tamam","adim_siniri") and len(r["turler"])<=r["tur_siniri"],"döngü durma nedeni ve gerçek model çağrı bütçesi kaydedildi")
    oz = D.ozet(r)
    kontrol(oz["arac_cagri"] > 0, f"model gerçekten araç çağırdı: {oz['arac_cagri']} çağrı, araçlar {oz['kullanilan_araclar']}")
    kontrol(oz["dogru_cagri"] > 0 and oz["dogru_cagri"] == oz["arac_cagri"],
            f"senin dispatch'in araçları doğru çalıştırdı: {oz['dogru_cagri']}/{oz['arac_cagri']} doğru")
if r is not None:
    yol = ai_lab.kanit_yaz("temel-ajan", {"kaynak": "gercek", "kabul": all(sonuclar), "ders": "ai-temel-23",
                                          "ortam": (r or {}).get("ortam"), "deney": r, "ozet": oz})

if oz:
    ok(True, f"BULGU ({r['ortam']['model']['ad']}): {oz['tur']} turlu ajan döngüsü, {oz['arac_cagri']} araç çağrısı "
             f"({oz['dogru_cagri']} doğru), araçlar {oz['kullanilan_araclar']}; final doğru: {oz['final_dogru']} (beklenen {r['beklenen']}).")
```

```solution
import ai_lab
import math

def arac_calistir(cagri, semalar, araclar):
    if not isinstance(cagri, dict) or set(cagri) != {"ad", "arg"} or not isinstance(cagri["ad"], str) or not cagri["ad"] \
            or not isinstance(cagri["arg"], dict):
        raise ValueError("cagri tam ad(str) ve arg(dict) içermeli")
    if not isinstance(semalar, dict) or not isinstance(araclar, dict) or set(araclar) != set(semalar):
        raise ValueError("semalar ve araclar aynı anahtarlara sahip sözlük olmalı")
    if any(not isinstance(ad,str) or not ad for ad in semalar): raise ValueError("araç adı")
    for s in semalar.values():
        if not isinstance(s, dict) or set(s) != {"gerekli", "tipler"} or not isinstance(s["gerekli"], list) \
                or not isinstance(s["tipler"], dict) or any(not isinstance(k,str) or not k for k in s["gerekli"]) or len(set(s["gerekli"]))!=len(s["gerekli"]) or set(s["tipler"]) != set(s["gerekli"]) \
                or any(t not in ("sayi", "metin") for t in s["tipler"].values()):
            raise ValueError("şema gerekli(list) ve tipler(sayi/metin) içermeli")
    if any(not callable(a) for a in araclar.values()):
        raise ValueError("araclar değerleri çağrılabilir olmalı")
    ad, arg = cagri["ad"], cagri["arg"]
    if ad not in semalar:
        return {"durum": "hata", "hata": f"bilinmeyen araç: {ad}"}
    sema = semalar[ad]
    if set(arg) != set(sema["gerekli"]):
        return {"durum": "hata", "hata": "argüman anahtarları şemayla uyuşmuyor"}
    for anahtar, tip in sema["tipler"].items():
        v = arg[anahtar]
        if tip == "sayi" and (isinstance(v, bool) or not isinstance(v, (int, float)) or (isinstance(v,float) and not math.isfinite(v))):
            return {"durum": "hata", "hata": f"{anahtar} sayı olmalı"}
        if tip == "metin" and not isinstance(v, str):
            return {"durum": "hata", "hata": f"{anahtar} metin olmalı"}
    try:
        return {"durum": "ok", "sonuc": araclar[ad](**arg)}
    except Exception as e:
        return {"durum": "hata", "hata": f"araç hatası: {type(e).__name__}"}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_23 as deney
    deney.goster(arac_calistir)
```

```hint
İki tür hatayı ayır: `cagri`/`semalar`/`araclar`'ın **yapısı** bozuksa `ValueError` yükselt (host'un sözleşmesi ihlal edilmiş). Ama modelin ürettiği çağrı geçerli yapıdayken yanlışsa (bilinmeyen araç, eksik/yanlış tip argüman) **yükseltme**, `{"durum": "hata", ...}` döndür — döngü bunu modele geri verip düzeltme şansı tanır. `bool`'u `sayi` kabul etme.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Tel biçiminden kanonik iç şemaya (`OpenAI` vs `Ollama`) (30 sn).** "Farklı sağlayıcılar araç argümanlarını ham JSON dizgisi ya da nesne olarak döndürür; yürütücü önce tüm çağrıları tek iç şemaya normalize edip izinli araç adı ve argüman tiplerini (`bool` != `int`) doğrular."
2. **Atomik ön-doğrulama ve hata sarmalama (35 sn).** "Bir adımda birden çok araç çağrısı geldiğinde hiçbiri çalışmadan önce tüm liste ve çağrı kimliği benzersizliği doğrulanır; çalışma sırasındaki `Exception` yığın izi sızdırmadan kontrollü sonuç mesajına çevrilir."
3. **Adım bütçesi (`max_adim`) kapısı (30 sn).** "Modelin sonsuz araç çağırma döngüsüne girerek maliyet ve yan etki üretmesini engellemek için ajan döngüsü sert bir tur tavanıyla sınırlandırılır."
4. **Soru (25 sn).** "Araç yürütücüsü `except Exception:` yerine `except BaseException:` kullanırsa zaman aşımı veya süreç durdurma (`SystemExit`, `KeyboardInterrupt`) sinyallerine ne olur?"
:::
