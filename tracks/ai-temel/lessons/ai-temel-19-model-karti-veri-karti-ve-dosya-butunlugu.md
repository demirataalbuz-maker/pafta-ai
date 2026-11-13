---
id: ai-temel-19
title: "Model Kartı, Veri Kartı ve Dosya Bütünlüğü"
summary: Git LFS işaretçisini içerikle doğrula, safetensors başlığını yüklemeden denetle ve kart sınırlarını sürüm ile özet kanıtına bağlayan dağıtım kapısı kur; son adımda önbellekteki gerçek model dosyalarını Hub kaydıyla doğrula.
esleme: ai-temel-18, ai-savunma-19, ai-guvence-14
timeout: 45
---

::: anlat Kart bir beyandır; commit ve özet onu belirli baytlara bağlar

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| LFS içeriği boyut/özetle, safetensors başlığı tensör aralıklarıyla tanımlar | İlk 3 görev görünür sentetik işaretçi, küçük ikili dosya ve kart/politika JSON'u | Genel LFS/safetensors uygulamasının tamamı veya lisans konusunda hukuki kabul değildir |
| Sabit model dosyaları önceden alınmış manifestle karşılaştırılabilir | Final yerel SmolLM2 önbelleğini, başlığını ve kendi geçici kurcalama kopyalarını gerçekten okur | Ders sırasında Hub'a yeniden sorgu atılmaz; gerçek model/veri kartı içerik denetimi ve imzalı tedarik zinciri kabulü yoktur |

> [!NOT]
> `veri/ornek.safetensors`, `veri/model.lfs`, `veri/kartlar.json` ve `veri/baslik.json` kontrollü üretilmiş **sentetik** örneklerdir; indirilen gerçek model ağırlığı değildir. Setup her Run/Check için geçici kopya hazırlar; kalıcılık yoktur. Kaynağı editörle aç veya kodda yüklenen kopyayı değiştirip Run ile dene. Gizli testler ayrıdır. Son görev kurulu gerçek model dosyalarını kullanır; ağ/indirme yoktur.

Hugging Face Hub'da model kartı deponun kökündeki `README.md` dosyasıdır: başta `---` satırları arasında YAML meta verisi (`license`, `base_model`, `datasets`, `language`, `pipeline_tag`, `library_name`), ardından amaçlanan kullanım, kapsam dışı kullanım (`Out-of-Scope Use`) ve sınırlamalar gibi düz yazı bölümleri gelir. Veri kartı aynı düzeni veri deposunda izler; `license`, `language`, `task_categories` ve `source_datasets` alanları verinin kaynağını ve kullanım koşulunu anlatır. Bu belgeleme fikri Mitchell ve arkadaşlarının "Model Cards for Model Reporting" (2019) ve Gebru ve arkadaşlarının "Datasheets for Datasets" çalışmalarına dayanır. Kart kanıt değil beyandır: model lisansı serbest olsa bile eğitim verisinin kartı ticari olmayan bir lisans taşıyabilir ya da istenen kullanım kartta kapsam dışı sayılmış olabilir. Bu yüzden dağıtım kararı iki kartı, istenen kullanımı ve kartın gerçekten yüklenen dosyaları anlattığına dair kanıtı birlikte değerlendirir; 17. ve 18. derslerdeki sunucu ile konteyner yanlış dosyayı yüklüyorsa bütün sınırlar yanlış nesneyi korur.

Hub deposu bir git deposudur ve `revision` bir dal (`main`), etiket ya da commit olabilir; dal her yeni commit'le ilerler, etiket de silinip yeniden oluşturulursa başka içeriği gösterir. Tekrarlanabilir dağıtım 40 karakterlik commit kimliğini sabitler, örneğin `hf_hub_download(repo_id, filename, revision=<commit>)`, ve kartı da ağırlıklarla aynı commit'ten okur. Büyük dosyalar git'te Git LFS işaretçisi olarak durur: `version https://git-lfs.github.com/spec/v1`, `oid sha256:<64 küçük harfli onaltılık>` ve `size <bayt>` satırları bu sırayla ve her biri LF ile biterek yazılır. Belirtim `ext-` ile başlayan uzantı satırlarına da izin verir (`version` dışındaki anahtarlar alfabetik sıralanır, bilinmeyen anahtarlar korunur) ve işaretçinin 1024 bayttan küçük olmasını ister; 1. görev yalnız uzantısız kanonik üç satırlık işaretçiyi kabul eden katı bir politika uygular. Commit işaretçiyi, işaretçi de içeriğin sha256 özetini ve boyutunu sabitlediği için kart, işaretçi ve indirilen baytlar tek bir doğrulanabilir zincire bağlanır. Görevler 1–3 görünür sentetik işaretçi, dosya baytları ve ayrıştırılmış kart örneklerini işler. Final huggingface_hub yerel önbellek çözümlemesi ve gerçek SmolLM2 dosyalarıyla çalışır; `local_files_only=True` kullanılır, ağ ve git süreci yoktur.
:::

::: anlat Biçim yüklemede neyin çalışacağını, özet algoritması kanıtın gücünü belirler

Önce veri klasöründeki dosyaları incele. model.lfs yalnız üç satırlık metindir; ornek.safetensors küçük bir F32 tensörünü taşıyan kontrollü ikili örnektir. baslik.json aynı dosyanın okunabilir başlık görünümüdür. İlk görev gerçek baytları işaretçinin boyut ve özetiyle karşılaştırır; ikinci görev aynı baytların başlığını açar; üçüncü görev `kartlar.json` içindeki manifesti, hesaplanan özeti ve yerel dağıtım politikasını karşılaştırır. Örnek karttaki commit benzeri değer sentetiktir, gerçek bir Hub revizyonu olduğu iddia edilmez. Bu dosyaları değiştirmek gizli testin beklenen cevabını değiştirmez.

Başlık geçerli diye içerik değişmemiş sayılmaz. Tensörün veri bölümündeki tek bir baytı değiştirirsen aralıklar ve boyutlar aynı kalabilir; başlık denetimi bunu yakalamaz ama SHA256 değişir. Tersine yanlış başlık uzunluğu veya kesilmiş dosya yapısal hatadır. İki kontrol birbirinin yerine geçmez. Boş tensör ve skaler de farklıdır: `shape=[0]` sıfır öğe, `shape=[]` bir öğe sayılır. Parametre sayısı bayt sayısı değildir; dtype boyu ile ayrı hesaplanır. İlk küçük görev 4096 bayt başlık sınırı kullanır, gerçek dosya görevi bir milyon bayt sınırı kullanır; aynı eşiği körlemesine kopyalama.

Başlıkta aynı anahtarın iki kez geçmesi belirsizliktir. Varsayılan Python json son değeri seçer; katı doğrulayıcı çiftleri sözlüğe dönüşmeden görüp reddeder. Başlık solunda boşluk veya sonunda satır sonu da bu görevde geçerli dolgu değildir; yalnız son ASCII boşlukları kabul edilir. Dosyanın ilk sekiz baytını büyük endian okursan küçük başlık çok büyük görünebilir. Yapısal sınırı doğrulamadan o kadar bayt okumaya kalkmak kaynak tüketimine yol açar. Veri aralıkları başlığa değil veri tamponuna göredir; başlık uzunluğunu ofsetlere ikinci kez ekleme.

Kart kapısının lisans alanı bir izinli liste karşılaştırmasıdır. Kartın yazarı yanlış veya eksik beyanda bulunmuş olabilir; kod bu beyanın doğruluğunu ispatlamaz. Manifesti saldırgan da değiştirebiliyorsa dosya ile özeti birlikte değiştirebilir. Güvenilir kaynaktan alınmış ve sabit revizyona bağlanmış beklenen değerler gerekir; imza zinciri bu derste kurulmaz. MD5 kaydını zayıf saymak ile SHA256 eşleşmesini görmek de kaynağın kimliğini kriptografik olarak doğrulamakla aynı şey değildir.

Gerçek final yeni bir Hub bağlantısı açmaz. Kodda kaynağı ve tarihi belirtilen manifestin sabit sürümüyle kurulu önbellek dosyalarını karşılaştırır. Doğrulama dosyaları okur; kurcalama yalnız kendi geçici kopyasında yapılır. Öğrencinin dosyasını veya model önbelleğini bozmaz. Parametre karşılaştırması için güvenilir mevcut model açılır; bu güvenilmeyen rastgele bir pickle dosyasını çalıştırma örneği değildir. Eksik önbellek, uyuşmayan özet veya başarısız başlık kontrolü geçme değildir. Çalıştır inceleme raporu verir; kabul Check ile ayrıca sınanır.

Kaynaklar: [safetensors biçimi](https://github.com/safetensors/safetensors/blob/main/README.md#format) ve [Git LFS belirtimi](https://github.com/git-lfs/git-lfs/blob/main/docs/spec.md). Ders küçük bir biçim altkümesini uygular; gerçek dosyaların içerik kalitesi, lisans koşullarının tam yorumu veya model davranış güvenliği bu yapısal denetimden çıkarılamaz.

PyTorch'un klasik `.bin` ve `.pt` kontrol noktaları pickle tabanlıdır ve pickle akışı `__reduce__` gibi yollarla yükleme anında keyfi bir çağrılabilir nesneyi çalıştırabilir. PyTorch 2.6'dan beri `torch.load` varsayılan olarak `weights_only=True` kısıtlı yükleyicisini kullanır; eski sürümler ve açıkça `weights_only=False` veren kod ise bu riski taşımaya devam eder. Safetensors dosyası yalnız veri taşır: ilk 8 bayt başlık uzunluğu N'yi işaretsiz 64 bit little-endian tamsayı olarak verir, ardından `{` ile başlayan ve sonu boşlukla doldurulabilen N baytlık UTF-8 JSON başlık, en sonda da ham bayt tamponu gelir. Her tensör `dtype`, `shape` ve tamponun başına göre `data_offsets: [begin, end]` taşır; isteğe bağlı `__metadata__` yalnız string→string haritasıdır ve imzalı olmadığı için kanıt değil beyandır. Belirtim tamponun deliksiz ve çakışmasız tamamen indekslenmesini isteyerek aynı baytların başka bir biçim olarak da yorumlanabildiği polyglot dosyaları engeller. Yinelenen anahtarlar da yasaktır, ama belirtim her ayrıştırıcının buna uymayabileceğini not eder; doğrulayıcı ile yükleyici farklı tensör tablosu görürse denetim anlamını yitirir.

DVC büyük veri ve model dosyalarını git dışında tutar; `.dvc` dosyasındaki ve `dvc.lock` içindeki `outs` girdileri `path`, `md5` ve `size` alanlarını taşır (DVC 3 kayıtlarında ayrıca `hash: md5` alanı bulunur) ve yerel önbellek bu md5 değerine göre adreslenir. Bu kayıt kazara bozulmayı ve önbellek tutarsızlığını yakalamak için yeterlidir; ancak MD5 için pratik çakışma saldırıları bilindiğinden, dosyayı üretebilen bir saldırgana karşı bütünlük garantisi vermez. Bu yüzden dağıtım kapısı md5 girdisini zayıf kanıt sayar ve sabitlenmiş commit'e ya da imzalı bir manifeste bağlı sha256 özeti ister. Görevler 1–3 `struct`/`json`/`hashlib` ile sentetik baytları işler; final gerçek model dosyalarını okuyup parametre sayısını transformers/torch modeliyle karşılaştırır. DVC çalıştırılmaz; öğrenci başlığı hazır safetensors yükleyicisi kullanmadan ayrıştırır. LFS işaretçisi ve safetensors başlığı gerçek biçimin katı bir alt kümesini izler; 3. görevdeki `md5:` önekli manifest değeri ise DVC `outs` girdisindeki `md5` alanının bu derse özgü sadeleştirilmiş gösterimidir.
:::

::: tahmin Katı ayrıştırma çıktısını tahmin et
Dört çıktı satırını yaz:

```python
import json, struct
print(int(" +7"), int("1_0"))
d = struct.pack("<Q", 7) + b'{"a":1}' + bytes(4)
print(d[:8])
print(int.from_bytes(d[:8], "little"), len(d) - 8 - 7)
print(json.loads('{"w": "F32", "w": "I64"}'))
```

???

```cikti
7 10
b'\x07\x00\x00\x00\x00\x00\x00\x00'
7 4
{'w': 'I64'}
```

İlk satır `int()` işlevinin baştaki boşluğu, `+` işaretini ve rakamlar arasındaki alt çizgiyi kabul ettiğini gösterir; LFS `size` alanı bu yüzden ayrıştırıldıktan sonra kanonik metinle karşılaştırılır. İkinci satır uzunluğun little-endian yazıldığını, yani en düşük anlamlı baytın başta durduğunu gösterir. Üçüncü satır 7 baytlık başlıktan sonra tamponda 4 bayt kaldığını gösterir; tensörlerin `data_offsets` aralıkları bu 4 baytı deliksiz kapsamalıdır. Dördüncü satır Python `json` modülünün yinelenen anahtarda son değeri sessizce seçtiğini gösterir; belirtim yinelenen anahtarı yasakladığı için doğrulayıcı onu açıkça reddetmelidir.
:::

::: gorev 1 · Git LFS işaretçisini içerikle doğrula
`lfs_dogrula(isaretci, icerik)` işlevini yaz. `isaretci` string, `icerik` `bytes` türündedir; içerik yerine `str` veya `bytearray`, işaretçi yerine `bytes` geçersizdir. İşaretçi tam üç satırdır ve her satır `\n` ile biter: `version https://git-lfs.github.com/spec/v1`, `oid sha256:<oid>`, `size <boyut>`. `oid` 64 karakterlik küçük harfli onaltılık özettir. `boyut` yalnız ASCII rakamlarından oluşan, başında işaret, boşluk, alt çizgi ya da gereksiz sıfır bulunmayan negatif olmayan ondalık tamsayıdır (`0` geçerlidir, üst sınır yoktur). CRLF satır sonu, eksik veya fazla satır, değişmiş satır sırası, fazladan boşluk ve başka sürüm satırı geçersizdir. Geçersiz veride `ValueError` yükselt.

`{"oid": oid, "boyut": boyut, "durum": durum}` döndür; `boyut` tamsayıdır. İçeriğin bayt uzunluğu boyuttan farklıysa durum `boyut_farkli`, uzunluk tutup içeriğin sha256 özeti oid'den farklıysa `ozet_farkli`, ikisi de tutuyorsa `tamam` olur.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-19")
```

```starter
from pathlib import Path
from ai_temel_veri import json_yukle,metin_yukle
def lfs_dogrula(isaretci, icerik):
    # KUSURLU BAŞLANGIÇ KODU: biçimi normalleştirir, içerik özetini hiç karşılaştırmaz.
    satirlar=isaretci.strip().splitlines()
    return {"oid":satirlar[1].split(":")[-1].lower(),"boyut":int(satirlar[2].split()[-1]),"durum":"tamam"}

ham=Path("veri/ornek.safetensors").read_bytes()
ptr=metin_yukle("veri/model.lfs")
print("Sentetik LFS:",repr(ptr),"bayt:",len(ham))
print("Doğrulama:",lfs_dogrula(ptr,ham))
```

```test
import hashlib
V = b"pafta-agirlik-v1"
H = hashlib.sha256(V).hexdigest()
B = hashlib.sha256(b"").hexdigest()
def isaretci(oid, boyut):
    return "version https://git-lfs.github.com/spec/v1\noid sha256:" + oid + "\nsize " + boyut + "\n"
P = isaretci(H, "16")
def sozlesme(fn):
    try:
        if fn(P, V) != {"oid": H, "boyut": 16, "durum": "tamam"} or fn(P, V + b"x") != {"oid": H, "boyut": 16, "durum": "boyut_farkli"}:
            return False
        if fn(P, V[::-1]) != {"oid": H, "boyut": 16, "durum": "ozet_farkli"} or fn(P, b"")["durum"] != "boyut_farkli":
            return False
        if fn(isaretci(B, "0"), b"") != {"oid": B, "boyut": 0, "durum": "tamam"} or fn(isaretci(B, "0"), b"\x00")["durum"] != "boyut_farkli":
            return False
        if fn(isaretci(H, "9" * 30), V) != {"oid": H, "boyut": int("9" * 30), "durum": "boyut_farkli"}:
            return False
        s = P.split("\n")
        gecersiz = ["", "x", P[:-1], P + "\n", P.replace("\n", "\r\n"), P.replace("v1", "v2"), " " + P, "\n".join([s[0], s[2], s[1], ""]), P.replace("sha256:", "sha512:"), P.replace("size ", "size  "),
                    isaretci(H.upper(), "16"), isaretci(H[:-1], "16"), isaretci(H + "a", "16"), isaretci(H[:-1] + "g", "16"),
                    isaretci("0x" + H[2:], "16"), isaretci(H[:30] + "_" + H[31:], "16"), isaretci(" " + H[1:], "16"), isaretci("+" + H[1:], "16"),
                    isaretci(H, "-1"), isaretci(H, "016"), isaretci(H, "+16"), isaretci(H, "1_6"), isaretci(H, "16 "), isaretci(H, ""), isaretci(H, "١٦")]
        for args in [(x, V) for x in gecersiz] + [(P.encode(), V), (None, V), (P, None), (P, bytearray(V)), (P, V.decode())]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(lfs_dogrula), "kanonik işaretçi, boyut ve sha256 doğrulaması korunmalı")
def m_crlf(p, v):
    return lfs_dogrula(p.replace("\r\n", "\n") if isinstance(p, str) else p, v)
def m_kucuk(p, v):
    return lfs_dogrula(p.lower() if isinstance(p, str) else p, v)
def m_durum(p, v):
    return dict(lfs_dogrula(p, v), durum="tamam")
for ad, mutant in [("satır sonunu normalleştiren", m_crlf), ("büyük harfli oid'i kabul eden", m_kucuk), ("doğrulamayı atlayan", m_durum)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from pathlib import Path
from ai_temel_veri import json_yukle,metin_yukle
def lfs_dogrula(isaretci, icerik):
    import hashlib
    import string
    if not isinstance(isaretci, str) or not isinstance(icerik, bytes):
        raise ValueError("tür geçersiz")
    satirlar = isaretci.split("\n")
    if len(satirlar) != 4:
        raise ValueError("satır sayısı geçersiz")
    oid = satirlar[1].removeprefix("oid sha256:")
    boyut = int(satirlar[2].removeprefix("size "))
    if len(oid) != 64 or not set(oid) <= set(string.digits + "abcdef") or boyut < 0:
        raise ValueError("alan geçersiz")
    if isaretci != "version https://git-lfs.github.com/spec/v1\noid sha256:" + oid + "\nsize " + str(boyut) + "\n":
        raise ValueError("kanonik biçim değil")
    if len(icerik) != boyut:
        durum = "boyut_farkli"
    elif hashlib.sha256(icerik).hexdigest() != oid:
        durum = "ozet_farkli"
    else:
        durum = "tamam"
    return {"oid": oid, "boyut": boyut, "durum": durum}

if __name__ == "__main__":
    ham=Path("veri/ornek.safetensors").read_bytes()
    ptr=metin_yukle("veri/model.lfs")
    print("Sentetik LFS:",repr(ptr),"bayt:",len(ham))
    print("Doğrulama:",lfs_dogrula(ptr,ham))
```

```hint
Satırları `split("\n")` ile ayır, oid ve boyutu öneklerinden sonra al; ardından bu değerlerden kanonik işaretçiyi yeniden kurup girdiyle birebir karşılaştır. `int()` boşluk, işaret ve alt çizgiyi kabul ettiği için tek başına katı bir ayrıştırıcı değildir; negatif sayıyı ayrıca ele.
```
:::

::: gorev 2 · Safetensors başlığını yüklemeden denetle
`safetensors_oku(veri)` işlevini yaz. `veri` bütün dosyanın `bytes` değeridir; `bytearray`, `str` ve `None` geçersizdir. İlk 8 bayt başlık uzunluğu N'yi işaretsiz little-endian 64 bit tamsayı olarak verir; 8 bayttan kısa veri, 4096'dan büyük N (gerçek kütüphanenin üst sınırı çok daha büyüktür; bu görev küçük bir sınır kullanır) ve dosyaya sığmayan başlık geçersizdir. Başlık UTF-8 olarak çözülmeli, ilk karakteri `{` olmalı, kapanış `}` karakterinden sonra yalnız boşluk (0x20) dolgusu içermeli ve hiçbir düzeyinde yinelenen anahtar bulunmayan bir JSON nesnesi olmalıdır.

İsteğe bağlı `__metadata__` bütün değerleri string olan bir nesnedir. Diğer her anahtar bir tensör adıdır ve değeri tam `dtype`, `shape`, `data_offsets` anahtarlı nesnedir. Gerçek biçim daha çok dtype tanır; bu görev yalnız şu adları ve bayt boylarını kabul eder: `F32` 4, `F16` 2, `BF16` 2, `I64` 8, `I32` 4, `U8` 1, `BOOL` 1. `shape` negatif olmayan tamsayı listesidir (boş liste skalerdir, 0 içeren şekil boş tensördür); `data_offsets` iki negatif olmayan tamsayıdan oluşan `[begin, end]` listesidir; bool ve ondalıklı sayı tamsayı sayılmaz. `end - begin`, şeklin eleman sayısıyla dtype boyunun çarpımına eşit olmalıdır.

Tensörleri `begin` değerine, eşitlikte `end` değerine, o da eşitse ada göre artan sırala. Bu sırada ilk aralık 0'dan başlamalı, her aralık bir öncekinin bittiği yerden başlamalı ve son `end` başlıktan sonraki tampon uzunluğuna eşit olmalıdır; tensör yoksa tampon boş olmalıdır. Geçersiz veride `ValueError` yükselt. `{"metadata": ..., "tensorler": [...]}` döndür: `metadata` başlıktaki `__metadata__` nesnesi ya da yoksa `{}` olur; `tensorler` bu sırada `{"ad": ad, "dtype": dtype, "shape": shape, "baslangic": begin, "bitis": end}` sözlüklerinden oluşur.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-19")
```

```starter
from pathlib import Path
from ai_temel_veri import json_yukle,metin_yukle
def safetensors_oku(veri):
    # KUSURLU BAŞLANGIÇ KODU: başlığı okuyup ofset, boyut ve tür denetimlerini atlar.
    import json,struct
    n=struct.unpack("<Q",veri[:8])[0];h=json.loads(veri[8:8+n])
    return {"metadata":h.get("__metadata__",{}),"tensorler":list(h)}

ham=Path("veri/ornek.safetensors").read_bytes()
print("Sentetik başlık görünümü:",json_yukle("veri/baslik.json"))
import struct
print("Uzunluk alanı:",repr(ham[:struct.calcsize("<Q")]))
print("Başlık:",safetensors_oku(ham))
```

```test
import json, struct
def dosya(baslik, tampon=b"", dolgu=b""):
    h = (baslik if isinstance(baslik, bytes) else json.dumps(baslik).encode()) + dolgu
    return struct.pack("<Q", len(h)) + h + tampon
T = {"embed.weight": {"dtype": "F16", "shape": [2, 3], "data_offsets": [0, 12]}, "__metadata__": {"format": "pt", "kaynak": "pafta"},
     "lm_head.bias": {"dtype": "F32", "shape": [2], "data_offsets": [12, 20]}, "zz_bos": {"dtype": "F32", "shape": [0, 4], "data_offsets": [0, 0]},
     "norm": {"dtype": "BF16", "shape": [], "data_offsets": [20, 22]}, "adim": {"dtype": "I64", "shape": [1], "data_offsets": [22, 30]},
     "maske": {"dtype": "BOOL", "shape": [3], "data_offsets": [30, 33]}, "kimlik": {"dtype": "I32", "shape": [2, 1], "data_offsets": [33, 41]},
     "bayt": {"dtype": "U8", "shape": [5], "data_offsets": [41, 46]}, "son_b": {"dtype": "I32", "shape": [3, 0], "data_offsets": [46, 46]},
     "son_a": {"dtype": "U8", "shape": [0], "data_offsets": [46, 46]}}
def satir(ad):
    return {"ad": ad, "dtype": T[ad]["dtype"], "shape": T[ad]["shape"], "baslangic": T[ad]["data_offsets"][0], "bitis": T[ad]["data_offsets"][1]}
BEKLENEN = {"metadata": {"format": "pt", "kaynak": "pafta"}, "tensorler": [satir(a) for a in ["zz_bos", "embed.weight", "lm_head.bias", "norm", "adim", "maske", "kimlik", "bayt", "son_a", "son_b"]]}
BOS = {"metadata": {}, "tensorler": []}
TEK = {"w": {"dtype": "F32", "shape": [2], "data_offsets": [0, 8]}}
def w(**alan):
    return {"w": dict(TEK["w"], **alan)}
def u8(a, b):
    return {"a": {"dtype": "U8", "shape": [4], "data_offsets": a}, "b": {"dtype": "U8", "shape": [4], "data_offsets": b}}
def sozlesme(fn):
    try:
        if fn(dosya(T, bytes(range(46)))) != BEKLENEN or fn(dosya({})) != BOS or fn(dosya({}, dolgu=b" " * 4094)) != BOS:
            return False
        if fn(dosya({"__metadata__": {}}, dolgu=b"   ")) != BOS or fn(dosya({"s": {"dtype": "F32", "shape": [], "data_offsets": [0, 4]}}, bytes(4)))["tensorler"] != [{"ad": "s", "dtype": "F32", "shape": [], "baslangic": 0, "bitis": 4}]:
            return False
        if [x["ad"] for x in fn(dosya(u8([4, 8], [0, 4]), bytes(8)))["tensorler"]] != ["b", "a"]:
            return False
        ikiz = b'{"w": {"dtype": "F32", "shape": [1], "data_offsets": [0, 4]}, "w": {"dtype": "F32", "shape": [1], "data_offsets": [0, 4]}}'
        gecersiz = [None, "dosya", bytearray(dosya({})), b"", b"\x02\x00", dosya({})[:9], dosya({}, dolgu=b" " * 4095), struct.pack("<Q", 50) + b"{}", struct.pack("<Q", 2 ** 64 - 1) + b"{}", struct.pack("<Q", 2 + (1 << 56)) + b"{}",
                    dosya(b" {}"), dosya(b"[]"), dosya(b"{}\n"), dosya(b"{}\t"), dosya(b"{} x"), dosya(b'{"\xff": 1}'), dosya(ikiz, bytes(4)), dosya(b'{"w": {"dtype": "F32", "dtype": "F32", "shape": [1], "data_offsets": [0, 4]}}', bytes(4)),
                    dosya({"__metadata__": "pt"}), dosya({"__metadata__": {"surum": 1}}), dosya({"__metadata__": []}), dosya({"__metadata__": None}), dosya({"__metadata__": ""}), dosya({"w": 5}), dosya({"w": [0, 8]}),
                    dosya(w(ek=1), bytes(8)), dosya({"w": {"dtype": "F32", "shape": [2]}}, bytes(8)), dosya(w(dtype="F64"), bytes(8)), dosya(w(dtype=["F32"]), bytes(8)), dosya(w(dtype=None), bytes(8)),
                    dosya(w(shape=2), bytes(8)), dosya(w(shape="2"), bytes(8)), dosya(w(shape=[2.0]), bytes(8)), dosya(w(shape=[True, 2]), bytes(8)), dosya(w(shape=[-2, -1]), bytes(8)), dosya(w(shape=[-1, 0], data_offsets=[0, 0]), b""),
                    dosya(w(data_offsets="0,8"), bytes(8)), dosya(w(data_offsets={"0": 0, "1": 8}), bytes(8)), dosya(w(data_offsets=[0]), bytes(8)), dosya(w(data_offsets=[0, 8, 9]), bytes(8)), dosya(w(data_offsets=[0, 8.0]), bytes(8)), dosya(w(data_offsets=[False, 8]), bytes(8)),
                    dosya(w(data_offsets=[0, 7]), bytes(7)), dosya(w(data_offsets=[8, 0]), bytes(8)), dosya(w(data_offsets=[4, 12]), bytes(12)), dosya(TEK, bytes(9)), dosya(TEK, bytes(7)), dosya(TEK),
                    dosya(u8([0, 4], [6, 10]), bytes(10)), dosya(u8([0, 4], [2, 6]), bytes(6)), dosya({}, b"\x00"),
                    dosya({"w": TEK["w"], "z": {"dtype": "U8", "shape": [0], "data_offsets": [100, 100]}}, bytes(8)), dosya({"w": TEK["w"], "z": {"dtype": "U8", "shape": [0], "data_offsets": [4, 4]}}, bytes(8))]
        for veri in gecersiz:
            try:
                fn(veri)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(safetensors_oku), "başlık sınırı, tensör şeması ve tampon kapsaması korunmalı")
def m_yut(v):
    try:
        return safetensors_oku(v)
    except ValueError:
        return {"metadata": {}, "tensorler": []}
def m_ad(v):
    r = safetensors_oku(v)
    return dict(r, tensorler=sorted(r["tensorler"], key=lambda x: x["ad"]))
def m_meta(v):
    return dict(safetensors_oku(v), metadata={})
for ad, mutant in [("hatayı yutan", m_yut), ("ada göre sıralayan", m_ad), ("metadatayı atan", m_meta)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from pathlib import Path
from ai_temel_veri import json_yukle,metin_yukle
def safetensors_oku(veri):
    import json
    import math
    boyutlar = {"F32": 4, "F16": 2, "BF16": 2, "I64": 8, "I32": 4, "U8": 1, "BOOL": 1}
    if not isinstance(veri, bytes):
        raise ValueError("veri geçersiz")
    n = int.from_bytes(veri[:8], "little")
    if n > 4096 or len(veri) < 8 + n:
        raise ValueError("başlık uzunluğu geçersiz")
    metin = veri[8:8 + n].decode()
    if not metin.startswith("{") or not metin.rstrip(" ").endswith("}"):
        raise ValueError("başlık sınırı geçersiz")
    def nesne(ciftler):
        if len({k for k, _ in ciftler}) != len(ciftler):
            raise ValueError("yinelenen anahtar")
        return dict(ciftler)
    baslik = json.loads(metin, object_pairs_hook=nesne)
    meta = baslik.pop("__metadata__", {})
    if not isinstance(meta, dict) or any(not isinstance(v, str) for v in meta.values()):
        raise ValueError("metadata geçersiz")
    tablo = []
    for ad, t in baslik.items():
        if not isinstance(t, dict) or set(t) != {"dtype", "shape", "data_offsets"} or not isinstance(t["dtype"], str) or t["dtype"] not in boyutlar:
            raise ValueError("tensör şeması geçersiz")
        sekil, ofset = t["shape"], t["data_offsets"]
        if not isinstance(sekil, list) or not isinstance(ofset, list) or len(ofset) != 2 or any(not isinstance(x, int) or isinstance(x, bool) or x < 0 for x in sekil + ofset):
            raise ValueError("şekil veya ofset geçersiz")
        if ofset[1] - ofset[0] != math.prod(sekil) * boyutlar[t["dtype"]]:
            raise ValueError("bayt sayısı uyuşmuyor")
        tablo.append({"ad": ad, "dtype": t["dtype"], "shape": sekil, "baslangic": ofset[0], "bitis": ofset[1]})
    tablo.sort(key=lambda x: (x["baslangic"], x["bitis"], x["ad"]))
    konum = 0
    for x in tablo:
        if x["baslangic"] != konum:
            raise ValueError("tamponda boşluk veya çakışma")
        konum = x["bitis"]
    if konum != len(veri) - 8 - n:
        raise ValueError("tampon tam kapsanmıyor")
    return {"metadata": meta, "tensorler": tablo}

if __name__ == "__main__":
    ham=Path("veri/ornek.safetensors").read_bytes()
    print("Sentetik başlık görünümü:",json_yukle("veri/baslik.json"))
    import struct
    print("Uzunluk alanı:",repr(ham[:struct.calcsize("<Q")]))
    print("Başlık:",safetensors_oku(ham))
```

```hint
Uzunluğu `int.from_bytes(veri[:8], "little")` ile oku. `json.loads(metin, object_pairs_hook=...)` kancası her JSON nesnesinin anahtar-değer çiftlerini liste olarak verir; yinelenen anahtarı orada yakala. Kapsamayı, sıralanmış tensörleri tek bir `konum` değişkeniyle gezerek denetle.
```
:::

::: gorev 3 · Kart sınırlarını sürüm ve özet kanıtıyla birleştir
`dagitim_engelleri(model_karti, veri_karti, kanit, politika)` işlevini yaz. `model_karti` tam `revizyon`, `license`, `datasets`, `kapsam_disi`; `veri_karti` tam `id`, `license`; `kanit` tam `revizyon`, `manifest`, `hesaplanan`; `politika` tam `lisanslar`, `kullanim` anahtarlı sözlüktür. `model_karti["revizyon"]` kartın (`README.md`) okunduğu commit, `kanit["revizyon"]` ağırlık özetlerinin hesaplandığı commit'tir. `revizyon`, `license`, `id` ve `kullanim` değerleri boş olmayan string; `datasets`, `kapsam_disi` ve `lisanslar` boş olabilen, yinelenmeyen ve boş olmayan stringlerden oluşan listedir. `manifest` en az bir, `hesaplanan` sıfır ya da daha çok girdili sözlüktür; anahtarları boş olmayan dosya adı stringidir. Manifest değeri `sha256:` ardından 64 ya da `md5:` ardından 32 küçük harfli onaltılık karakterdir; hesaplanan değer öneksiz, 64 küçük harfli onaltılık karakterlik sha256 özetidir. `md5:` önekli değer DVC `outs` girdisinin sadeleştirilmiş gösterimidir; gerçek DVC kaydı `path`, `md5` ve `size` alanlarını ayrı tutar. Gerçek kartta kapsam dışı kullanımlar düz yazıdır; burada incelemede etiket listesine çevrildiklerini varsay. Geçersiz veride `ValueError` yükselt.

Engelleri şu sırayla içeren liste döndür: kanıt revizyonu 40 küçük harfli onaltılık karakter değilse `revizyon_sabit_degil`; kart revizyonu kanıt revizyonundan farklıysa `kart_revizyonu_farkli`; model lisansı `lisanslar` içinde değilse `model_lisansi`; veri lisansı `lisanslar` içinde değilse `veri_lisansi`; veri kartının `id` değeri `datasets` içinde değilse `veri_beyan_edilmemis`; `kullanim` değeri `kapsam_disi` içindeyse `kapsam_disi_kullanim`.

Ardından manifest ve hesaplanan anahtarlarının birleşimini `sorted` sırasıyla gez ve her dosya için en çok bir engel ekle; öncelik şöyledir: hesaplananda yoksa `eksik:<ad>`, manifestte yoksa `beklenmeyen:<ad>`, manifest değeri md5 ise `zayif_ozet:<ad>`, manifestteki sha256 özeti hesaplanandan farklıysa `ozet_farkli:<ad>`. Engel yoksa boş liste döndür. Girdileri değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-19")
```

```starter
from pathlib import Path
from ai_temel_veri import json_yukle,metin_yukle
def dagitim_engelleri(model_karti, veri_karti, kanit, politika):
    # KUSURLU BAŞLANGIÇ KODU: yalnız model lisansını denetler, veri kartı ve özetleri yok sayar.
    return [] if model_karti["license"] in politika["lisanslar"] else ["model_lisansi"]

v=json_yukle("veri/kartlar.json")
print("Sentetik kart/kanıt:",v)
print("Engeller:",dagitim_engelleri(v["model"],v["veri"],v["kanit"],v["politika"]))
```

```test
import copy, hashlib
R = hashlib.sha1(b"pafta-commit").hexdigest()
R2 = hashlib.sha1(b"baska-commit").hexdigest()
HA = hashlib.sha256(b"ornek-agirlik").hexdigest()
HB = hashlib.sha256(b"kart").hexdigest()
HC = hashlib.sha256(b"tokenizer").hexdigest()
M5 = hashlib.md5(b"config").hexdigest()
MK = {"revizyon": R, "license": "apache-2.0", "datasets": ["pafta/ek", "pafta/egitim"], "kapsam_disi": ["tibbi-tani", "kimlik-tespiti"]}
VK = {"id": "pafta/egitim", "license": "cc-by-4.0"}
KN = {"revizyon": R, "manifest": {"model.safetensors": "sha256:" + HA, "README.md": "sha256:" + HB}, "hesaplanan": {"README.md": HB, "model.safetensors": HA}}
PO = {"lisanslar": ["cc-by-4.0", "apache-2.0"], "kullanim": "ozetleme"}
MAN = {"tokenizer.json": "sha256:" + HC, "model.safetensors": "sha256:" + HA, "config.json": "md5:" + M5, "README.md": "sha256:" + HB}
HES = {"pytorch_model.bin": HA, "model.safetensors": HB, "config.json": HC, "README.md": HB}
DOSYA = ["zayif_ozet:config.json", "ozet_farkli:model.safetensors", "beklenmeyen:pytorch_model.bin", "eksik:tokenizer.json"]
def g(m={}, v={}, k={}, p={}):
    return (dict(MK, **m), dict(VK, **v), dict(KN, **k), dict(PO, **p))
def eksik(d, a):
    return {x: y for x, y in d.items() if x != a}
def sozlesme(fn):
    try:
        once = copy.deepcopy((MK, VK, KN, PO, MAN, HES))
        if fn(MK, VK, KN, PO) != [] or fn(*g(k={"manifest": MAN, "hesaplanan": HES})) != DOSYA or (MK, VK, KN, PO, MAN, HES) != once:
            return False
        for r in ["main", "v1.0", R[:-1], R + "a", R.upper(), R + "\n", "0x" + R[2:], R[:20] + "_" + R[21:], " " + R[1:]]:
            if fn(*g(m={"revizyon": r}, k={"revizyon": r})) != ["revizyon_sabit_degil"]:
                return False
        if fn(*g(m={"revizyon": R2})) != ["kart_revizyonu_farkli"] or fn(*g(k={"revizyon": "main"})) != ["revizyon_sabit_degil", "kart_revizyonu_farkli"]:
            return False
        if fn(*g(m={"license": "cc-by-nc-4.0"})) != ["model_lisansi"] or fn(*g(v={"license": "cc-by-nc-4.0"})) != ["veri_lisansi"] or fn(*g(p={"lisanslar": []})) != ["model_lisansi", "veri_lisansi"]:
            return False
        if fn(*g(m={"datasets": []})) != ["veri_beyan_edilmemis"] or fn(*g(v={"id": "baska/veri"})) != ["veri_beyan_edilmemis"] or fn(*g(p={"kullanim": "tibbi-tani"})) != ["kapsam_disi_kullanim"] or fn(*g(m={"kapsam_disi": []})) != []:
            return False
        hepsi = ["revizyon_sabit_degil", "kart_revizyonu_farkli", "model_lisansi", "veri_lisansi", "veri_beyan_edilmemis", "kapsam_disi_kullanim"] + DOSYA
        if fn(*g(m={"license": "x", "datasets": ["y"], "kapsam_disi": ["ozetleme"]}, v={"license": "z"}, k={"revizyon": "main", "manifest": MAN, "hesaplanan": HES})) != hepsi:
            return False
        if fn(*g(k={"manifest": {"config.json": "md5:" + M5}, "hesaplanan": {}})) != ["eksik:config.json"] or fn(*g(k={"manifest": {"a": "sha256:" + HA}, "hesaplanan": {"a": HA}})) != []:
            return False
        gecersiz = [(None, VK, KN, PO), (MK, None, KN, PO), (MK, VK, None, PO), (MK, VK, KN, None), ([MK], VK, KN, PO), g(m={"ek": 1}), g(v={"ek": 1}), g(k={"ek": 1}), g(p={"ek": 1}),
                    (eksik(MK, "kapsam_disi"), VK, KN, PO), (MK, eksik(VK, "id"), KN, PO), (MK, VK, eksik(KN, "hesaplanan"), PO), (MK, VK, KN, eksik(PO, "kullanim")),
                    g(m={"revizyon": ""}), g(m={"license": ""}), g(v={"id": ""}), g(v={"license": ""}), g(k={"revizyon": ""}), g(p={"kullanim": ""}), g(m={"license": b"mit"}), g(k={"revizyon": None}), g(p={"kullanim": 1}),
                    g(m={"datasets": ("pafta/egitim",)}), g(m={"datasets": ["x", "x"]}), g(m={"datasets": ["pafta/egitim", 1]}), g(m={"datasets": [""]}), g(m={"kapsam_disi": [""]}), g(m={"kapsam_disi": "tibbi-tani"}), g(m={"kapsam_disi": ["a", "a"]}),
                    g(p={"lisanslar": [b"mit"]}), g(p={"lisanslar": ["mit", "mit"]}), g(p={"lisanslar": ["apache-2.0", ""]}),
                    g(k={"hesaplanan": {"a": HA + "\n"}}), g(k={"manifest": {"a": "sha256:" + HA + "\n"}}), g(k={"hesaplanan": {"a": "0x" + HA[2:]}}), g(k={"manifest": {"a": "sha256:" + HA[:30] + "_" + HA[31:]}}),
                    g(k={"manifest": ["sha256:" + HA]}), g(k={"manifest": {}}), g(k={"manifest": {"": "sha256:" + HA}}), g(k={"manifest": {1: "sha256:" + HA}}),
                    g(k={"manifest": {"a": "sha256:" + HA[:-1]}}), g(k={"manifest": {"a": "sha256:" + HA + "0"}}), g(k={"manifest": {"a": "sha256:" + HA.upper()}}), g(k={"manifest": {"a": "md5:" + M5[:-1]}}), g(k={"manifest": {"a": "md5:" + M5 + "0"}}),
                    g(k={"manifest": {"a": "md5:" + HA}}), g(k={"manifest": {"a": "sha256:" + M5}}), g(k={"manifest": {"a": "sha1:" + R}}), g(k={"manifest": {"a": HA}}), g(k={"manifest": {"a": ("sha256:" + HA).encode()}}), g(k={"manifest": {"a": None}}),
                    g(k={"hesaplanan": [HA]}), g(k={"hesaplanan": {"": HA}}), g(k={"hesaplanan": {1: HA}}), g(k={"hesaplanan": {"a": HA[:-1]}}), g(k={"hesaplanan": {"a": HA.upper()}}), g(k={"hesaplanan": {"a": "sha256:" + HA}}), g(k={"hesaplanan": {"a": None}})]
        for args in gecersiz:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return (MK, VK, KN, PO, MAN, HES) == once
    except Exception:
        return False
ok(sozlesme(dagitim_engelleri), "revizyon sabitleme, kart-kanıt bağı, lisans ve özet engelleri korunmalı")
def m_kart(m, v, k, p):
    return dagitim_engelleri(dict(m, revizyon=k["revizyon"]), v, k, p)
def m_md5(m, v, k, p):
    return [e for e in dagitim_engelleri(m, v, k, p) if not e.startswith("zayif_ozet:")]
def m_veri(m, v, k, p):
    return [e for e in dagitim_engelleri(m, v, k, p) if not e.startswith("veri_")]
for ad, mutant in [("kart revizyonunu kanıta eşitleyen", m_kart), ("md5'i yeterli sayan", m_md5), ("veri kartını yok sayan", m_veri)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from pathlib import Path
from ai_temel_veri import json_yukle,metin_yukle
def dagitim_engelleri(model_karti, veri_karti, kanit, politika):
    import string
    def metin_mi(x):
        return isinstance(x, str) and x != ""
    def ozet_mi(x, uzunluk):
        return isinstance(x, str) and len(x) == uzunluk and set(x) <= set(string.digits + "abcdef")
    def liste_mi(x):
        return isinstance(x, list) and all(map(metin_mi, x)) and len(set(x)) == len(x)
    semalar = [(model_karti, {"revizyon", "license", "datasets", "kapsam_disi"}), (veri_karti, {"id", "license"}), (kanit, {"revizyon", "manifest", "hesaplanan"}), (politika, {"lisanslar", "kullanim"})]
    if any(not isinstance(s, dict) or set(s) != anahtarlar for s, anahtarlar in semalar):
        raise ValueError("şema geçersiz")
    man, hes, rev = kanit["manifest"], kanit["hesaplanan"], kanit["revizyon"]
    metinler = [model_karti["revizyon"], model_karti["license"], veri_karti["id"], veri_karti["license"], rev, politika["kullanim"]]
    if not all(map(metin_mi, metinler)) or not all(map(liste_mi, [model_karti["datasets"], model_karti["kapsam_disi"], politika["lisanslar"]])):
        raise ValueError("alan geçersiz")
    if not isinstance(man, dict) or not isinstance(hes, dict) or not man or not all(map(metin_mi, list(man) + list(hes))):
        raise ValueError("özet haritası geçersiz")
    uzunluklar = {"sha256": 64, "md5": 32}
    if any(not ozet_mi(h, 64) for h in hes.values()) or any(not isinstance(d, str) or not ozet_mi(d.partition(":")[2], uzunluklar.get(d.partition(":")[0])) for d in man.values()):
        raise ValueError("özet değeri geçersiz")
    kurallar = [(not ozet_mi(rev, 40), "revizyon_sabit_degil"), (model_karti["revizyon"] != rev, "kart_revizyonu_farkli"),
                (model_karti["license"] not in politika["lisanslar"], "model_lisansi"), (veri_karti["license"] not in politika["lisanslar"], "veri_lisansi"),
                (veri_karti["id"] not in model_karti["datasets"], "veri_beyan_edilmemis"), (politika["kullanim"] in model_karti["kapsam_disi"], "kapsam_disi_kullanim")]
    engeller = [ad for kosul, ad in kurallar if kosul]
    for ad in sorted(set(man) | set(hes)):
        if ad not in hes:
            engeller.append("eksik:" + ad)
        elif ad not in man:
            engeller.append("beklenmeyen:" + ad)
        elif man[ad].startswith("md5:"):
            engeller.append("zayif_ozet:" + ad)
        elif man[ad] != "sha256:" + hes[ad]:
            engeller.append("ozet_farkli:" + ad)
    return engeller

if __name__ == "__main__":
    v=json_yukle("veri/kartlar.json")
    print("Sentetik kart/kanıt:",v)
    print("Engeller:",dagitim_engelleri(v["model"],v["veri"],v["kanit"],v["politika"]))
```

```hint
Önce dört sözlüğün anahtar kümelerini ve değer türlerini doğrula, sonra altı kuralı sabit sırayla değerlendir. Dosyalar için `sorted(set(manifest) | set(hesaplanan))` üzerinde gez ve her dosyada ilk tutan koşulda dur; md5 girdisini hiçbir zaman sha256 özetiyle karşılaştırma.
```
:::

::: gorev Gerçek deney · Önbellekteki model dosyalarını Hub kaydıyla doğrula
İki işlev yaz.

**`ozetler(yol)`**: `yol` var olan bir dosyanın yolu (str) değilse `ValueError`. Dosyayı 1 MiB'lık parçalarla **akış hâlinde** oku (tamamını belleğe alma) ve `{"boyut": int, "sha256": hex, "git_blob": hex}` döndür; `git_blob = sha1(b"blob " + str(boyut).encode() + b"\0" + içerik)`.

**`safetensors_baslik(yol)`**: yalnız başlığı oku, veri bölümünü okuma; dosya boyutunu `os.path.getsize` ile al. Geçersiz durumda `ValueError`:
- Dosya 8 bayttan kısa; ilk 8 baytın işaretsiz little-endian 64 bit değeri N, 1.000.000'dan büyük ya da `8 + N` dosya boyunu aşıyor.
- Başlık UTF-8 JSON nesnesi değil, ilk baytı { değil, sonunda ASCII boşluk dışında dolgu var veya herhangi bir düzeyde yinelenen anahtar var. İsteğe bağlı `__metadata__` bütün anahtar ve değerleri str olan nesne değil.
- Bir tensörün alanları tam `dtype`, `shape`, `data_offsets` değil; dtype şu tabloda değil: `F64` 8, `F32` 4, `F16` 2, `BF16` 2, `I64` 8, `I32` 4, `I16` 2, `I8` 1, `U8` 1, `BOOL` 1; `shape` negatif olmayan int listesi değil; `data_offsets` `[bas, son]`, `0 <= bas <= son` int ikilisi değil ya da `son - bas` eleman sayısı × dtype boyuna eşit değil.
- Tensörler `(bas, son, ad)` sırasında 0'dan başlayıp boşluksuz, çakışmasız ilerlemiyor ya da son `son` değeri `dosya boyu - 8 - N`'ye eşit değil.

Döndür: `{"metadata": dict, "tensorler": [{"ad", "dtype", "shape", "bas", "son"}, …] (aynı sırayla), "parametre": eleman sayılarının toplamı}`.

Test işlevlerini önce geçici sentetik dosyalarda sınar, sonra gerçek önbellek dosyalarında Hub manifestiyle karşılaştırır, başlıktan sayılan parametreyi transformers modeliyle karşılaştırır ve kurcalanmış kopyaları dener. Çalıştır düğmesi aynı raporu gösterir.

```meta
motor: ai-gercek
gereksinim: torch
timeout: 240
```

```starter
import hashlib
import json
import math
import os
import struct
import ai_lab

def ozetler(yol):
    return {}

def safetensors_baslik(yol):
    return {}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_19 as deney
    deney.goster(ozetler, safetensors_baslik)
```

```test
import hashlib
import json
import os
import random
import shutil
import struct
import tempfile
import ai_lab
sonuclar = []
def kontrol(kosul, mesaj):
    sonuclar.append(bool(kosul))
    return ok(kosul, mesaj)
import ast
_yasak=("referans_ozetler","referans_baslik","git_blob_bayt","kanit_yaz","getattr","safe_open","load_file")
sorun=ai_lab.kod_denetimi(src,yasak=_yasak)
for n in ast.walk(ast.parse(src)):
    if isinstance(n,ast.ImportFrom) and any(a.name in _yasak or a.name=="*" for a in n.names):
        sorun.append("referans importu yasak")
if not kontrol(not sorun,"Kendi dosya doğrulayıcını yaz: "+"; ".join(sorun)):
    stop()
ozet_fn = need("ozetler")
baslik_fn = need("safetensors_baslik")
from sandbox import ai_gercek_ai_temel_19 as D
rnd = random.Random()
klasor = tempfile.mkdtemp(prefix="pafta_ai19_test_")
def dosya(ad, icerik):
    yol = os.path.join(klasor, ad)
    with open(yol, "wb") as f:
        f.write(icerik)
    return yol
def st(baslik, tampon, n=None, ham=None):
    b = ham if ham is not None else json.dumps(baslik).encode()
    return struct.pack("<Q", len(b) if n is None else n) + b + tampon
try:
    ozet_dosyalari = [dosya("bos.bin", b""), dosya("kisa.txt", "Pafta ğüşiöç\n".encode()),
                      dosya("buyuk.bin", rnd.randbytes(3 * 1024 * 1024 + rnd.randint(1, 999)))]
    gecerli = {
        "tam": st({"__metadata__": {"format": "pt"}, "b.w": {"dtype": "F16", "shape": [2, 3], "data_offsets": [8, 20]},
                   "a.w": {"dtype": "I64", "shape": [1], "data_offsets": [0, 8]}, "bos": {"dtype": "F32", "shape": [0], "data_offsets": [8, 8]},
                   "z": {"dtype": "BF16", "shape": [2], "data_offsets": [20, 24]}}, rnd.randbytes(24)),
        "metasiz": st({"w": {"dtype": "U8", "shape": [3, 1], "data_offsets": [0, 3]}}, b"abc"),
        "tipler": st({"f64": {"dtype": "F64", "shape": [1], "data_offsets": [0, 8]}, "f32": {"dtype": "F32", "shape": [1], "data_offsets": [8, 12]}, "i32": {"dtype": "I32", "shape": [1], "data_offsets": [12, 16]}, "i16": {"dtype": "I16", "shape": [1], "data_offsets": [16, 18]}, "i8": {"dtype": "I8", "shape": [1], "data_offsets": [18, 19]}, "bl": {"dtype": "BOOL", "shape": [1], "data_offsets": [19, 20]}}, bytes(20)),
        "n_sinir": st(None, b"", ham=b"{}" + b" " * 999_998),
        "hic": st({}, b""),
    }
    gecersiz = {
        "kisa": b"\x01\x00", "n_buyuk": struct.pack("<Q", 2_000_000) + b"{}", "n_tasiyor": struct.pack("<Q", 50) + b"{}",
        "utf8_degil": st(None, b"", ham=b"\xff\xfe{}"), "nesne_degil": st([1, 2], b""),
        "dtype": st({"w": {"dtype": "F8", "shape": [1], "data_offsets": [0, 1]}}, b"x"),
        "fazla_alan": st({"w": {"dtype": "U8", "shape": [1], "data_offsets": [0, 1], "x": 1}}, b"x"),
        "negatif_sekil": st({"w": {"dtype": "U8", "shape": [-1], "data_offsets": [0, 0]}}, b""),
        "boy_tutmuyor": st({"w": {"dtype": "F32", "shape": [2], "data_offsets": [0, 4]}}, b"xxxx"),
        "bosluk": st({"a": {"dtype": "U8", "shape": [1], "data_offsets": [0, 1]}, "b": {"dtype": "U8", "shape": [1], "data_offsets": [2, 3]}}, b"xxx"),
        "cakisma": st({"a": {"dtype": "U8", "shape": [2], "data_offsets": [0, 2]}, "b": {"dtype": "U8", "shape": [2], "data_offsets": [1, 3]}}, b"xxx"),
        "fazla_tampon": st({"w": {"dtype": "U8", "shape": [1], "data_offsets": [0, 1]}}, b"xy"),
        "meta_str_degil": st({"__metadata__": {"n": 1}}, b""),
    }
    gecersiz.update({"liste_dtype":st({"w":{"dtype":["U8"],"shape":[1],"data_offsets":[0,1]}},b"x"),"ikiz":st({},b"",ham=b'{"__metadata__":{},"__metadata__":{}}'),
                     "ic_ikiz":st({},bytes(1),ham=b'{"w":{"dtype":"U8","dtype":"U8","shape":[1],"data_offsets":[0,1]}}'),
                     "basta_bosluk":st({},b"",ham=b' {}'),"sonda_lf":st({},b"",ham=b'{}\n'),
                     "kisa7":b"\x00"*7,"n_1m1":struct.pack("<Q",1_000_001)+b"{}"+b" "*999_999,"n_eksik1":struct.pack("<Q",3)+b"{}",
                     "n_ust_bayt":struct.pack("<Q",2+(1<<56))+b"{}","meta_int":st({"__metadata__":1},b""),
                     "t_list":st({"w":["dtype","shape","data_offsets"]},b""),
                     "sekil_int":st({"w":{"dtype":"U8","shape":1,"data_offsets":[0,1]}},b"x"),
                     "sekil_str":st({"w":{"dtype":"U8","shape":"1","data_offsets":[0,1]}},b"x"),
                     "sekil_bool":st({"w":{"dtype":"U8","shape":[True],"data_offsets":[0,1]}},b"x"),
                     "sekil_neg0":st({"w":{"dtype":"U8","shape":[-1,0],"data_offsets":[0,0]}},b""),
                     "ofs_int":st({"w":{"dtype":"U8","shape":[1],"data_offsets":1}},b"x"),
                     "ofs_str":st({"w":{"dtype":"U8","shape":[1],"data_offsets":"01"}},b"x"),
                     "ofs_uc":st({"w":{"dtype":"U8","shape":[1],"data_offsets":[0,1,2]}},b"x"),
                     "ofs_bool":st({"w":{"dtype":"U8","shape":[1],"data_offsets":[False,True]}},b"x"),
                     "ofs_neg":st({"w":{"dtype":"U8","shape":[1],"data_offsets":[-1,0]}},b"x"),
                     "ofs_ters":st({"w":{"dtype":"U8","shape":[0],"data_offsets":[2,1]}},b"")})
    g_yol = {ad: dosya(ad + ".safetensors", b) for ad, b in gecerli.items()}
    h_yol = {ad: dosya(ad + "_x.safetensors", b) for ad, b in gecersiz.items()}
    def sinirli_cagir(fn,yol,yalniz_baslik=False):
        if not isinstance(yol,str) or not os.path.isfile(yol): return fn(yol)
        import builtins,io
        from unittest.mock import patch
        asil=builtins.open
        with asil(yol,"rb") as f:
            ilk=f.read(8)
        boyut_dosya=os.path.getsize(yol)
        gecerli_baslik=len(ilk)==8 and struct.unpack("<Q",ilk)[0]<=1_000_000 and 8+struct.unpack("<Q",ilk)[0]<=boyut_dosya
        son=8+struct.unpack("<Q",ilk)[0] if gecerli_baslik else boyut_dosya
        class Okuyucu:
            def __init__(self,f): self.f=f
            def __enter__(self): return self
            def __exit__(self,*a): return self.f.__exit__(*a)
            def __getattr__(self,ad): return getattr(self.f,ad)
            def read(self,n=-1):
                if type(n) is not int or n<0 or n>(1<<20): raise ValueError("okuma parça sınırı")
                if yalniz_baslik and gecerli_baslik and self.f.tell()+n>son: raise ValueError("tensör veri bölümü okunamaz")
                return self.f.read(n)
        def ac(dosya,*args,**kwargs):
            f=asil(dosya,*args,**kwargs)
            return Okuyucu(f) if os.fspath(dosya)==yol else f
        with patch("builtins.open",ac),patch("io.open",ac):
            return fn(yol)
    def sozlesme(oz, bas):
        asil_oz,asil_bas=oz,bas
        oz=lambda y:sinirli_cagir(asil_oz,y)
        bas=lambda y:sinirli_cagir(asil_bas,y,True)
        try:
            if not all(oz(y) == D.referans_ozetler(y) for y in ozet_dosyalari):
                return False
            if not all(bas(y) == D.referans_baslik(y) for y in g_yol.values()):
                return False
            for y in list(h_yol.values()) + [os.path.join(klasor, "yok.safetensors"), None]:
                for f in (bas,) if y is not None and y.endswith(".safetensors") and os.path.exists(y) else (bas, oz):
                    try:
                        f(y)
                        return False
                    except ValueError:
                        pass
            return True
        except Exception:
            return False
    kontrol(sozlesme(ozet_fn, baslik_fn), "sentetik dosyalar: akışlı sha256/git blob, başlık sözleşmesi ve bütün geçersiz durumlar doğru")
    def tum_dosyayi_oku(y):
        with open(y,"rb") as f: f.read()
        return D.referans_ozetler(y)
    def veri_tamponunu_oku(y):
        with open(y,"rb") as f: f.read(os.path.getsize(y))
        return D.referans_baslik(y)
    kontrol(not sozlesme(tum_dosyayi_oku,baslik_fn),"hatalı çözüm reddedilmeli: dosyanın tümünü belleğe alan")
    kontrol(not sozlesme(ozet_fn,veri_tamponunu_oku),"hatalı çözüm reddedilmeli: başlık için veri tamponunu okuyan")
    for ad, oz, bas in [("git blob başlığı yok", lambda y: D.referans_ozetler(y, blob_basligi=False), D.referans_baslik),
                        ("tampon kapsaması denetlenmiyor", D.referans_ozetler, lambda y: D.referans_baslik(y, kapsama=False)),
                        ("başlık boyu big-endian okunuyor", D.referans_ozetler, lambda y: D.referans_baslik(y, endian=">")),
                        ("parametre yerine bayt sayılıyor", D.referans_ozetler, lambda y: D.referans_baslik(y, parametre="bayt"))]:
        kontrol(not sozlesme(oz, bas), "hatalı çözüm reddedilmeli: " + ad)
    kontrol(not sozlesme(lambda y: {"boyut": 0, "sha256": hashlib.sha256(b"").hexdigest(), "git_blob": "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"},
                         lambda y: {"metadata": {}, "tensorler": [], "parametre": 0}), "hatalı çözüm reddedilmeli: sabit cevap")
finally:
    shutil.rmtree(klasor, ignore_errors=True)
r = None
if all(sonuclar):
    try:
        r = D.deney(ozet_fn, baslik_fn)
    except ai_lab.GercekLabYok as e:
        kontrol(False, f"GERÇEK MODEL DOSYALARI YOK, deney yapılmadı: {e}")
        stop()
    ds = {k["ad"]: k for k in r["dosyalar"]}
    kontrol(set(ds) == set(D.MANIFEST) and r["snapshot_revizyonu"] == D.REVIZYON, "önbellekteki dosya kümesi ve snapshot commit'i Hub kaydıyla aynı")
    kontrol(all(v for k in ds.values() for x, v in k.items() if x.endswith("tutuyor")),
            "gerçek dosyalar: boyutlar, git blob kimlikleri, LFS sha256 oid'i ve işaretçinin blob kimliği Hub'la aynı")
    kontrol(r["baslik"]["parametre"] == r["model_parametresi"], f"başlıktan sayılan parametre modelle aynı ({r['model_parametresi']:,})")
    k = r["kurcalama"]
    kontrol(k["veri_bayti"]["baslik"] == "geçti" and not k["veri_bayti"]["sha256_tutuyor"], "veri baytı kurcalaması: başlık geçerli kalıyor, sha256 yakalıyor")
    kontrol(k["kesik"]["baslik"].startswith("ValueError") and k["baslik_boyu"]["baslik"].startswith("ValueError"),
            "kesik dosya ve bozuk başlık boyu başlık denetiminde reddediliyor")
    kontrol(r["gecici_silindi"], "kurcalama kopyaları silindi; önbelleğe dokunulmadı")
bilgi = (r or {}).pop("model_bilgisi", None)
yol = ai_lab.kanit_yaz("temel-dosya-butunlugu", {"kaynak": "gercek", "kabul": all(sonuclar), "ders": "ai-temel-19",
                                                 "model_bilgisi": bilgi, "manifest_kaynagi": "HfApi.get_paths_info, 2026-10-28", "deney": r})
if r and all(sonuclar):
    b = r["baslik"]
    ok(True, f"GERÇEK ÇIKTI ({D.REPO}@{D.REVIZYON[:8]}): {len(r['dosyalar'])} dosya Hub kaydıyla aynı; safetensors başlığı {b['baslik_bayt']:,} bayt, "
             f"{b['tensor_sayisi']} tensör {b['dtypeler']}, {b['parametre']:,} parametre; tek bayt değişikliğini yalnız sha256 yakaladı")
```

```solution
import hashlib
import json
import math
import os
import struct
import ai_lab

BOY = {"F64": 8, "F32": 4, "F16": 2, "BF16": 2, "I64": 8, "I32": 4, "I16": 2, "I8": 1, "U8": 1, "BOOL": 1}

def ozetler(yol):
    if not isinstance(yol, str) or not os.path.isfile(yol):
        raise ValueError("var olan bir dosya yolu gerekli")
    boyut = os.path.getsize(yol)
    s256 = hashlib.sha256()
    s1 = hashlib.sha1(b"blob " + str(boyut).encode() + b"\0")
    with open(yol, "rb") as f:
        while parca := f.read(1 << 20):
            s256.update(parca)
            s1.update(parca)
    return {"boyut": boyut, "sha256": s256.hexdigest(), "git_blob": s1.hexdigest()}

def safetensors_baslik(yol):
    if not isinstance(yol, str) or not os.path.isfile(yol):
        raise ValueError("var olan bir dosya yolu gerekli")
    toplam = os.path.getsize(yol)
    with open(yol, "rb") as f:
        bas = f.read(8)
        if len(bas) < 8:
            raise ValueError("dosya 8 bayttan kısa")
        n = struct.unpack("<Q", bas)[0]
        if n > 1_000_000 or 8 + n > toplam:
            raise ValueError("başlık uzunluğu geçersiz")
        ham = f.read(n)
    try:
        def nesne(ciftler):
            out={}
            for key,value in ciftler:
                if key in out: raise ValueError("yinelenen anahtar")
                out[key]=value
            return out
        metin=ham.decode("utf-8")
        if not metin.startswith("{") or not metin.rstrip(" ").endswith("}"):
            raise ValueError("başlık dolgu/başlangıç")
        baslik = json.loads(metin,object_pairs_hook=nesne)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("başlık UTF-8 JSON değil")
    if not isinstance(baslik, dict):
        raise ValueError("başlık bir nesne olmalı")
    meta = baslik.pop("__metadata__", {})
    if not isinstance(meta, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in meta.items()):
        raise ValueError("__metadata__ str→str olmalı")
    tensorler = []
    for ad, t in baslik.items():
        if not isinstance(t, dict) or set(t) != {"dtype", "shape", "data_offsets"} or not isinstance(t["dtype"],str) or t["dtype"] not in BOY:
            raise ValueError(f"{ad}: alanlar ya da dtype geçersiz")
        sekil, ofs = t["shape"], t["data_offsets"]
        if not isinstance(sekil, list) or any(type(x) is not int or x < 0 for x in sekil):
            raise ValueError(f"{ad}: shape geçersiz")
        if not isinstance(ofs, list) or len(ofs) != 2 or any(type(x) is not int for x in ofs) or not 0 <= ofs[0] <= ofs[1]:
            raise ValueError(f"{ad}: data_offsets geçersiz")
        if ofs[1] - ofs[0] != math.prod(sekil) * BOY[t["dtype"]]:
            raise ValueError(f"{ad}: bayt boyu şekille tutmuyor")
        tensorler.append({"ad": ad, "dtype": t["dtype"], "shape": sekil, "bas": ofs[0], "son": ofs[1]})
    tensorler.sort(key=lambda t: (t["bas"], t["son"], t["ad"]))
    konum = 0
    for t in tensorler:
        if t["bas"] != konum:
            raise ValueError(f"{t['ad']}: boşluk ya da çakışma")
        konum = t["son"]
    if konum != toplam - 8 - n:
        raise ValueError("veri bölümü uzunluğu başlıkla tutmuyor")
    return {"metadata": meta, "tensorler": tensorler, "parametre": sum(math.prod(t["shape"]) for t in tensorler)}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_19 as deney
    deney.goster(ozetler, safetensors_baslik)
```

```hint
`hashlib.sha1(b"blob " + str(boyut).encode() + b"\0")` nesnesini önce kur, sonra her parçayı hem bunu hem sha256'yı güncelleyerek ver. Başlıkta veri bölümünü hiç okumana gerek yok: beklenen veri uzunluğu `os.path.getsize(yol) - 8 - N`'dir.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Beyan vs kriptografik bağ (`Model/Data Card` + `Commit`) (30 sn).** "Model ve veri kartları lisans ile kapsam dışı kullanımı beyan eder; bu beyanın gerçekten yüklenen ağırlık baytlarını anlattığını kanıtlamak için dal adı (`main`) yerine 40 karakterlik `commit` ve `SHA-256` özeti sabitlenir."
2. **Neden `pickle` değil `safetensors`? (35 sn).** "Klasik `pickle` ağırlık yüklerken keyfî kod çalıştırabilir; `safetensors` ise 8 baytlık küçük-endian uzunluk + katı JSON başlığı + bitişik/çakışmasız veri tamponu yapısıyla kod yürütmeden ve `polyglot` boşluğu bırakmadan doğrulanır."
3. **Dağıtım kapısı zinciri (30 sn).** "Başlık geçerliliği tek başına veri tamponundaki tek baytlık bozulmayı yakalamaz; `SHA-256` özeti, başlık kontrolü ve hem model hem veri kartı lisans uyumu birlikte geçmeden dağıtım açılmaz."
4. **Soru (25 sn).** "`safetensors` başlığında iki tensörün `data_offsets` aralıkları arasında kullanılmayan bir bayt boşluğu (`hole`) bırakılmasına izin verilseydi saldırgan o boşluğa ne gizleyebilirdi?"
:::
