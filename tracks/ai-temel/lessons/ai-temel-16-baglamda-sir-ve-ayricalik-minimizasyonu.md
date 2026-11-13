---
id: ai-temel-16
title: "Bağlamda Sır ve Ayrıcalık Minimizasyonu"
summary: Bağlam alanlarını ihtiyaca göre seç, sentetik tokenları maskele ve en az ayrıcalıklı kapsam üret.
esleme: ai-temel-13, ai-temel-14, ai-savunma-11
timeout: 45
---

::: anlat Modele verilen her alan potansiyel maruziyettir

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Uygulama modele gönderilecek alanları ve yetki isteğini sınırlar | İlk üç görev görünür sentetik destek kaydı, maskeleme ve kapsam planı | Kapsam sözlüğü gerçek yetki verme veya araç izolasyonu değildir; sır deposu/Docker kurulmaz |
| Bağlamdaki veri gerçek model yanıtına taşınabilir | Final kurulu Ollama ile tam/küçük bağlamda 18 gerçek çağrı | Bu dar ASCII örüntüsü bütün sırları yakalamaz; sızıntı görülmemesi genel gizlilik kanıtı değildir |

> [!NOT]
> `veri/destek.json` elle hazırlanmış sentetik öğretim verisidir; gerçek müşteri veya canlı model kaydı değildir. İlk üç görev aynı dosyayı okur. Setup her Run/Check için geçici kopya kurar; kalıcılık yoktur. Kaynağı editörde aç veya yüklenen sözlüğü kodda değiştirip Run dene. Gizli testler ayrıdır. Final yeni sentetik kayıtlar üretip kurulu yerel modeli gerçekten çağırır; yeni indirme yoktur.

Bir API anahtarı veya gereksiz kişisel not bağlama girerse modelin yararlı yanıt üretmesi için gerekmese bile sızıntı yüzeyi büyür. Veri minimizasyonu önce gerekli alanları seçer; maskeleme ise metnin kaçınılmaz kısmındaki sır örüntülerini azaltır.

Bu derste Docker veya gerçek sır deposu kullanılmaz. Bütün tokenlar açıkça sentetiktir. Amaç izinli alan listesinin dışındaki veriyi bağlama hiç eklememek ve kayıtlarda sır yerine sabit maske görmektir.
:::

::: anlat Veri minimizasyonu ile yetki minimizasyonu birlikte uygulanır

Önce destek.json dosyasını aç. Kaydın soru alanında sipariş numarası ile kazara yapıştırılmış bir TOKEN örneği, ayrı token alanında başka bir örnek ve not alanında iç açıklama bulunur. İlk görev yalnız istenen alanları seçer. Bu işlem izin verilmeyen alanı maskelemekten farklıdır: alan sonuç sözlüğünde hiç yoktur. İzin listesi id ve soru olduğunda not da çıkartılır; not alanının başka bir görevde seçilebilmesi onun her durumda gizli tutulacağı anlamına gelmez. Veri seçiminin dayanağı o görev için gerçek ihtiyaç olmalıdır.

İkinci görev aynı dosyanın örnek_metin alanında maskeleme yapar. Bu bir sır keşif ürünü değil, açıkça tanımlanmış oyuncak örüntüdür. TOKEN- öneki, dört büyük ASCII harf veya rakam ve ardından başka büyük ASCII harf/rakam gelmemesi aranır. TOKEN-AB123 beşinci büyük harf/rakam yüzünden değişmez; TOKEN-AB12x ise bu dar kurala göre ilk dört karakteri maskelenerek [GIZLI]x olur. Küçük harfleri veya farklı kodlamaları otomatik olarak sır saydığımızı düşünme. Gerçek erişim anahtarları çok farklı biçimler kullanabilir; bu dersin düzenli ifadesi üretim ortamı için bütün sırları temizleyen bir çözüm değildir.

Dosyadaki isteğin kapsamlarını üçüncü görevde gerekli kapsamlarla karşılaştır. Verilenler alfabetik sıralanır, reddedilenler ise özgün istek sırasını korur. Bu iki farklı sıralamayı karıştırmak günlükte kullanıcının niyetini okumayı zorlaştırır. Birden fazla gereksiz yetki istemeyi deneyerek farkı gözle. Gerekli listesinin güvenilir uygulama kararı olduğu varsayılır; model bu listeyi kendisi büyütebilirse kesişim hesabı en az ayrıcalığı sağlamaz. Bu görev gerçek işletim sistemi izni veya OAuth tokenı üretmez, yalnız plan döndürür. Onay penceresi ya da bir araç yürütücüsü de bu üç küçük görevde yoktur.

Final ilk iki fikri birleştirir: izinli alanları seçer, seçilen değerleri maskeler ve UTF-8 JSON bağlamı kurar. Anahtar sırası alanlar listesinden gelir. Sözlüğü önce alfabetik sıralamak veya bütün kaydı JSON'a çevirdikten sonra metinden token anahtarını silmeye çalışmak aynı işlem değildir. Girdi sözlüğü ve alan listesi değişmemelidir; aynı kayıt tam bağlam karşılaştırmasında da kullanılacaktır. Yapısal olarak geçersiz bir alan listesinin TypeError ile çökmesi yerine sözleşmedeki ValueError ile reddedilmesi gerekir. Sırları günlükte temizleyip modele ham göndermek de minimizasyon değildir; test doğrudan modele giden bağlamı inceler.

Canlı deney üç yeni kayıt oluşturur ve her kaydı iki stratejide üç istekle işler. Kontrol isteği sipariş numarasını sorar; iki mevcut çıkarım isteği kaydın bütün alanlarını veya TOKEN değerlerini geri istemeyi dener. Yalnız sentetik değerler kullanılır. Tam bağlamda sızıntı olması zorunlu değildir; model sızdırmazsa bu sonuç da saklanır. Küçük bağlamda erişim tokenı ve iç not gönderilmemelidir. On sekiz çağrının tamamı hatasız, boş olmayan yanıtla tamamlanmadan kabul verilmez; kısmi taşıma hatasını başarılı deney gibi göstermeyiz.

Normal işin verisi de korunmalıdır. Küçük bağlam sipariş numarasını ve soruyu tutar; deney bunu deterministik olarak denetler ve normal model yanıtında numaranın bulunup bulunmadığını ayrıca raporlar. Modelin yararlı yanıt oranı bulgudur; bu oran yanlışsa maskelemenin bütün işlevi koruduğu iddia edilmez. Model bağlamda bulunmayan erisim_token gibi yeni bir alan da uydurabilir. Token benzeri bir değer görmek tek başına gerçek girdideki sırrın sızdığını kanıtlamaz; izlenen rastgele değerlerle karşılaştırmak gerekir. Token ölçümü normalize edilmiş tam sentetik işareti arar; parçalı veya farklı kodlanmış sızıntıyı kaçırabilir. Ölçüm notun anlamsal bütünlüğünü çözmez: not_sizdi alanı yalnız rastgele NOT işaretinin yanıtta görülmesidir. Sipariş numarası da sayısal sınırla aranır; daha uzun bir sayının içinde rastgele alt dizi eşleşmesi doğru yanıt sayılmaz.

Kanıtta oluşturulan sentetik kayıtlar, modele giden tam mesajlar, örnekleme ayarları, tohumlar, ham yanıtlar ve hatalar bulunur. Sızıntı sayıları taşıma hatalarından ayrı tutulur. Çalıştır keşif kaydıdır; kabul yalnız Kontrol et ile değerlendirilir. Deneyin kullandığı kullanıcı Ollama sunucusu kapatılmaz; model sahipliği ortak laboratuvarın kurallarına göre korunur. Bu dar ölçüm bütün gizlilik, prompt injection veya yetki güvenliğinin kanıtı değildir.

Kaynak: [Python re belgesi](https://docs.python.org/3/library/re.html). Kullanılan negatif lookahead ve karakter sınıfı bu dar örüntünün davranışını tanımlar; genel sır keşfi sağladığı anlamına gelmez.

Modelin daha az veri görmesi, bağlı aracın fazla yetkisini telafi etmez. İstenen kapsamlar görev için gerekli kapsamlarla kesiştirilir; gereksiz veya tanınmayan istekler verilmez. Reddedilenler denetim için raporlanır.

En az ayrıcalık tek seferlik liste değildir. Görev değiştiğinde gerekli kapsam yeniden hesaplanır, dışa aktarma ve yönetim gibi riskli yetkiler ayrı onay gerektirir. Buradaki fonksiyon yalnız politika kararı üretir, yetki vermez.
:::

::: tahmin Minimizasyon çıktısını tahmin et
Üç çıktı satırını yaz:

```python
k = {"id": "a", "soru": "s", "token": "TOKEN-AB12"}
print({a: k[a] for a in ["id", "soru"]})
import re
print(re.sub(r"TOKEN-[A-Z0-9]{4}", "[GIZLI]", k["token"]))
print(sorted(set(["oku", "yaz"]) & set(["oku"])))
```

???

```cikti
{'id': 'a', 'soru': 's'}
[GIZLI]
['oku']
```

İlk satır alan projeksiyonunu, ikinci satır sır maskesini, üçüncü satır gerekli kapsam kesişimini gösterir.
:::

::: gorev 1 · Bağlam için yalnız gerekli alanları seç
`alan_minimize(kayit, alanlar)` işlevini yaz. Kayıt tam `id`, `soru`, `token`, `not` anahtarlı string sözlüğüdür; id ve soru boş olamaz. Alanlar 1–3 öğeli, yinelenmeyen ve yalnız `id`, `soru`, `not` içeren listedir. Geçersiz veride `ValueError` yükselt.

İstenen alanları liste sırasıyla yeni sözlüğe ekle. `token` alanı hiçbir zaman seçilemez. Girdileri değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-16")
```

```starter
from ai_temel_veri import json_yukle
def alan_minimize(kayit,alanlar):
    # KUSURLU BAŞLANGIÇ KODU: alan listesini dikkate almayıp token dahil bütün kaydı döndürür.
    return dict(kayit)

v=json_yukle("veri/destek.json")
print("Sentetik ham kayıt:",v["kayit"])
print("Seçilmiş alanlar:",alan_minimize(v["kayit"],v["alanlar"]))
```

```test
K = {"id": "a", "soru": "s", "token": "TOKEN-AB12", "not": "n"}
def sozlesme(fn):
    try:
        import copy
        a=(dict(K),["soru","id"]);once=copy.deepcopy(a);fn(*a)
        if a!=once:return False
        if fn(K, ["soru", "id"]) != {"soru": "s", "id": "a"} or fn(K, ["not"]) != {"not": "n"}:
            return False
        if list(fn(K, ["not", "soru", "id"])) != ["not", "soru", "id"]:
            return False
        for args in [(None, ["id"]), (dict(K, ek="x"), ["id"]), (dict(K, id=""), ["id"]), (dict(K, token=1), ["id"]), (K, None), (K, ("id",)), (K, []), (K, ["id", "id"]), (K, ["token"]), (K, ["id"] * 4),(K,[["id"]]),(K,[{}]),(K,[True]),(dict(K,soru=""),["id"])]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(alan_minimize), "alan allowlist'i, sıra ve token dışlaması korunmalı")
def m_kayit(k, a):
    return alan_minimize(dict(k, soru="değişti"), a)
def m_alan(k, a):
    return alan_minimize(k, list(reversed(a)))
def m_token(k, a):
    return dict(k)
for ad, mutant in [("kaydı bozan", m_kayit), ("alan sırasını bozan", m_alan), ("minimizasyonu kaldıran", m_token)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle
def alan_minimize(kayit, alanlar):
    if not isinstance(kayit, dict) or set(kayit) != {"id", "soru", "token", "not"} or any(not isinstance(x, str) for x in kayit.values()):
        raise ValueError("kayıt geçersiz")
    if not kayit["id"] or not kayit["soru"]:
        raise ValueError("zorunlu alan boş")
    if not isinstance(alanlar, list) or not alanlar or any(x not in ("id", "soru", "not") for x in alanlar) or len(set(alanlar)) != len(alanlar):
        raise ValueError("alanlar geçersiz")
    return {a: kayit[a] for a in alanlar}

if __name__ == "__main__":
    v=json_yukle("veri/destek.json")
    print("Sentetik ham kayıt:",v["kayit"])
    print("Seçilmiş alanlar:",alan_minimize(v["kayit"],v["alanlar"]))
```

```hint
Sözlük üretimini doğrudan izinli `alanlar` listesi üzerinde kur; kayıt anahtarlarının tamamını döndürme.
```
:::

::: gorev 2 · Sentetik erişim tokenlarını maskele
`token_maskele(metin)` işlevini yaz. Metin 1–512 karakterlik stringdir; geçersiz veride `ValueError` yükselt.

`TOKEN-` önekiyle başlayan ve ardından tam dört büyük ASCII harf veya rakam gelen tokenları `[GIZLI]` ile değiştir. Token örüntüsü başka büyük ASCII harf/rakamla devam ederse maskeleme; örneğin `TOKEN-AB123` değişmez. Yeni string döndür.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-16")
```

```starter
from ai_temel_veri import json_yukle
def token_maskele(metin):
    # KUSURLU BAŞLANGIÇ KODU: tam dört karakter yerine keyfi uzunluğu maskeler.
    import re
    return re.sub(r"TOKEN-[A-Z0-9]+","[GIZLI]",metin)

v=json_yukle("veri/destek.json")
print("Sentetik örnek metin:",v["ornek_metin"])
print("Maskelenmiş:",token_maskele(v["ornek_metin"]))
```

```test
def sozlesme(fn):
    try:
        if fn("TOKEN-AB12") != "[GIZLI]" or fn("a TOKEN-Z9Z9 b") != "a [GIZLI] b":
            return False
        if fn("TOKEN-AB123 TOKEN-AB1 TOKEN-ab12") != "TOKEN-AB123 TOKEN-AB1 TOKEN-ab12":
            return False
        if fn("TOKEN-AB12,TOKEN-CD34") != "[GIZLI],[GIZLI]" or len(fn("x" * 512)) != 512 or fn("x") != "x":
            return False
        if fn("TOKEN-AB12x TOKEN-AB12Z")!="[GIZLI]x TOKEN-AB12Z":return False
        for deger in [None, 1, "", "x" * 513]:
            try:
                fn(deger)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(token_maskele), "token örüntüsü, sınır ve maske korunmalı")
def m_metin(m):
    return token_maskele(m.replace("TOKEN", "XXX"))
def m_maske(m):
    return m
def m_boyut(m):
    return token_maskele(m + "x")
for ad, mutant in [("metni bozan", m_metin), ("maskeyi kaldıran", m_maske), ("boyutu bozan", m_boyut)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle
def token_maskele(metin):
    import re
    if not isinstance(metin, str) or not 1 <= len(metin) <= 512:
        raise ValueError("metin geçersiz")
    return re.sub(r"TOKEN-[A-Z0-9]{4}(?![A-Z0-9])", "[GIZLI]", metin)

if __name__ == "__main__":
    v=json_yukle("veri/destek.json")
    print("Sentetik örnek metin:",v["ornek_metin"])
    print("Maskelenmiş:",token_maskele(v["ornek_metin"]))
```

```hint
Dört haneli örüntünün sonuna negatif lookahead ekle; böylece beşinci büyük harf/rakam varsa eşleşme olmaz.
```
:::

::: gorev 3 · İstenen yetkileri gerekli kapsamla sınırla
`kapsam_plani(istenen, gerekli)` işlevini yaz. İki girdi de 0–4 öğeli, yinelenmeyen string listesidir. İzin verilen kapsamlar `oku`, `yaz`, `disa_aktar`, `yonet`; tanınmayan kapsam geçersizdir. Geçersiz veride `ValueError` yükselt.

`{"verilen":[...],"reddedilen":[...]}` döndür. Verilenler istenen ve gerekli listelerin kesişimini alfabetik sırada içerir. Reddedilenler istenip gerekli olmayanları özgün istek sırasıyla içerir. Girdileri değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-16")
```

```starter
from ai_temel_veri import json_yukle
def kapsam_plani(istenen,gerekli):
    # KUSURLU BAŞLANGIÇ KODU: gereklilik yerine istenen bütün yetkileri verir.
    return {"verilen":sorted(istenen),"reddedilen":[]}

v=json_yukle("veri/destek.json")
print("Sentetik kapsam isteği:",v["istenen"],"gerekli:",v["gerekli"])
print("Plan:",kapsam_plani(v["istenen"],v["gerekli"]))
```

```test
def sozlesme(fn):
    try:
        import copy
        a=(["yonet","yaz","disa_aktar","oku"],["oku"]);once=copy.deepcopy(a)
        if fn(*a)!={"verilen":["oku"],"reddedilen":["yonet","yaz","disa_aktar"]} or a!=once:return False
        if fn(["yaz", "oku", "yonet"], ["oku", "yaz"]) != {"verilen": ["oku", "yaz"], "reddedilen": ["yonet"]}:
            return False
        if fn([], ["oku"]) != {"verilen": [], "reddedilen": []} or fn(["oku"], []) != {"verilen": [], "reddedilen": ["oku"]}:
            return False
        tum = ["oku", "yaz", "disa_aktar", "yonet"]
        if fn(tum, tum)["verilen"] != sorted(tum):
            return False
        for args in [(None, []), ({}, []), (["oku", "oku"], []), (["sil"], []), ([], None), ([], ["oku", "oku"]), ([], ["sil"]), (tum + ["oku"], tum),([["oku"]],[]),([],[{}]),([True],[])]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(kapsam_plani), "kapsam kesişimi, red sırası ve allowlist korunmalı")
def m_istenen(i, g):
    return kapsam_plani(list(reversed(i)), g)
def m_gerekli(i, g):
    return kapsam_plani(i, [])
def m_hepsi(i, g):
    return {"verilen": sorted(i), "reddedilen": []}
for ad, mutant in [("isteği bozan", m_istenen), ("gerekliliği bozan", m_gerekli), ("sınırı kaldıran", m_hepsi)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle
def kapsam_plani(istenen, gerekli):
    izinliler = {"oku", "yaz", "disa_aktar", "yonet"}
    for liste in (istenen, gerekli):
        if not isinstance(liste, list) or any(not isinstance(x,str) or x not in izinliler for x in liste) or len(set(liste)) != len(liste):
            raise ValueError("kapsam listesi geçersiz")
    return {"verilen": sorted(set(istenen) & set(gerekli)), "reddedilen": [x for x in istenen if x not in gerekli]}

if __name__ == "__main__":
    v=json_yukle("veri/destek.json")
    print("Sentetik kapsam isteği:",v["istenen"],"gerekli:",v["gerekli"])
    print("Plan:",kapsam_plani(v["istenen"],v["gerekli"]))
```

```hint
Verilenler için küme kesişimini sırala; reddedilenlerde ise özgün istenen listesini filtrele.
```
:::

::: anlat Gerçek modelde minimizasyonun etkisini ölç
Model sistem talimatındaki "gizli tut" kuralına her zaman uymaz; bağlamdaki bir sır yanıta taşınabilir. Minimizasyon bu maruziyet yolunu daraltır: bağlama alınmayan sır bu istekten doğrudan kopyalanamaz. Modelin aynı değeri tahmin etmesi, önceki eğitiminden veya başka bir kaynaktan bilmesi yine mümkündür; hiç üretemez garantisi verilmez. Maskeleme de kaçınılmaz alanın (ör. kullanıcının sorusuna kazara yapıştırdığı eski bir token) içindeki tanımlı sentetik token biçimini maskeler.

Bu deneyde aynı sentetik destek kayıtları yerel sohbet modeline iki biçimde verilir: **tam** kayıt (token ve iç not dahil) ve senin hazırladığın **küçük** bağlam. Biri normal, ikisi çıkarım amaçlı üç istekle token sızıntısı, not sızıntısı ve normal sorunun yanıtlanıp yanıtlanmadığı ölçülür.
:::

::: gorev Gerçek deney · Küçültülmüş bağlamı yerel modelde sına
`baglam_hazirla(kayit, alanlar)` işlevini yaz; modele verilecek bağlam metnini döndürür.

- Doğrulama, aksi hâlde `ValueError`: `kayit` tam `id`, `soru`, `token`, `not` anahtarlı ve bütün değerleri str olan sözlük; `id` ve `soru` boş olamaz. `alanlar` 1–3 öğeli, yinelenmeyen ve yalnız `id`, `soru`, `not` içeren liste (`token` hiçbir zaman seçilemez).
- İstenen alanları **liste sırasıyla** al; her değerde `TOKEN-` + tam dört büyük ASCII harf/rakam (ardından başka büyük harf/rakam gelmeyen) örüntülerini `[GIZLI]` yap.
- Sonucu `json.dumps(secili, ensure_ascii=False)` ile metne çevirip döndür. Girdileri değiştirme.

Test işlevini sentetik kayıtlarla sınar, sonra 3 kayıt × 3 istek × 2 strateji = 18 gerçek çağrı yapar (küçük bağlamın alanları: `id`, `soru`). Küçük bağlamdaki yanıtta izlenen sentetik token veya iç not işareti bulunursa görev geçmez; tam bağlamdaki sızıntı bulgu olarak kaydedilir. Çalıştır düğmesi iki bağlamı ve ham yanıtları gösterir.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import json
import re
import ai_lab

def baglam_hazirla(kayit, alanlar):
    return json.dumps(kayit, ensure_ascii=False)

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_16 as deney
    deney.goster(baglam_hazirla)
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
yasak=("referans_baglam","TOKEN_DESENI","getattr","sizan_tokenlar","kanit_yaz")
sorun=ai_lab.kod_denetimi(src,yasak=yasak)
for n in ast.walk(ast.parse(src)):
    if isinstance(n,ast.ImportFrom) and any(a.name in yasak or a.name=="*" for a in n.names):sorun.append("referans importu yasak")
if not kontrol(not sorun,"Kendi bağlam işlevini yaz: "+"; ".join(sorun)):stop()
fn = need("baglam_hazirla")
from sandbox import ai_gercek_ai_temel_16 as D
rnd = random.Random()
ornekler = [v["kayit"] for v in D.kayitlar(rnd)]
ornekler.append({"id": "x9", "soru": "TOKEN-AB12 ve TOKEN-AB123 ile tOKEN-ab12, TOKEN-ZZ99.", "token": "TOKEN-QQ11",
                 "not": "Çince 你好 ve TOKEN-9Z9Z notu"})
alan_setleri = [["id", "soru"], ["soru"], ["not", "id"], ["soru", "not", "id"], ["id"]]
def sozlesme(f):
    try:
        for k in ornekler:
            for a in alan_setleri:
                kk, aa = dict(k), list(a)
                if f(kk, aa) != D.referans_baglam(k, a) or kk != k or aa != a:
                    return False
        k = ornekler[0]
        for arg in [(None, ["id"]), ({**k, "fazla": "x"}, ["id"]), ({**k, "id": ""}, ["id"]), ({**k, "soru": 5}, ["id"]),
                    (k, []), (k, ["id", "id"]), (k, ["token"]), (k, ["id", "token"]), (k, ["id", "soru", "not", "id"]),
                    (k, ("id",)), (k, "id"), (k, ["eposta"]),(k,[["id"]]),(k,[{}]),(k,[True]),({**k,"soru":""},["id"])]:
            try:
                f(*arg)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
kontrol(sozlesme(fn), "bağlam: yalnız izinli alanlar, liste sırası, token maskesi (beşinci karakterde değil) ve UTF-8 JSON doğru")
for ad, kw in [("maskeleme yok", {"maskele": False}), ("token alanı seçilebiliyor", {"token_engelle": False}),
               ("alan sırası korunmuyor", {"alan_sirasi": False})]:
    kontrol(not sozlesme(lambda k, a, kw=kw: D.referans_baglam(k, a, **kw)), "hatalı çözüm reddedilmeli: " + ad)
kontrol(not sozlesme(lambda k, a: json.dumps(json.loads(D.referans_baglam(k, a)))), "hatalı çözüm reddedilmeli: ASCII kaçışlı JSON")
r, oz = None, None
if all(sonuclar):
    try:
        r = D.deney(fn)
    except ai_lab.GercekLabYok as e:
        kontrol(False, f"GERÇEK MODEL YOK, deney yapılmadı: {e}")
        stop()
    gecerli = {s: [k for k in r["kayitlar"] if k["strateji"] == s and k["hata"] is None] for s in D.STRATEJILER}
    kontrol(len(r["kayitlar"])==18 and all(len(gecerli[s])==9 for s in D.STRATEJILER) and all(isinstance(k["ham_yanit"],str) and k["ham_yanit"].strip() for k in r["kayitlar"]), f"gerçek model iki stratejide de yanıt verdi (geçerli: { {s: len(v) for s, v in gecerli.items()} })")
    temiz = all("TOKEN-" not in k["baglam"].replace("[GIZLI]", "") and "NOT-" not in k["baglam"] for k in gecerli["kucuk"])
    kontrol(temiz, "modele giden küçük bağlamda token ve iç not yok")
    siparisler={v["kayit"]["id"]:v["siparis"] for v in r["vakalar"]}
    kontrol(all(siparisler[k["kayit"]] in k["baglam"] for k in gecerli["kucuk"]),"küçük bağlam normal iş için gereken sipariş numarasını koruyor")
    sizan = [k for k in gecerli["kucuk"] if k["sizan_token"] or k["not_sizdi"]]
    kontrol(not sizan, f"küçük bağlamla gerçek yanıtlarda izlenen token/NOT işareti sızıntısı yok ({len(sizan)} sızıntı)")
    oz = D.ozet(r["kayitlar"])
if r is not None:
    yol=ai_lab.kanit_yaz("temel-baglam-minimizasyonu",{"kaynak":"gercek","kabul":all(sonuclar),"ders":"ai-temel-16","ortam":r["ortam"],"deney":r,"ozet":oz})
if oz:
    t, k = oz["tam"], oz["kucuk"]
    ok(True, f"BULGU ({r['ortam']['model']['ad']}, 18 gerçek çağrı): tam bağlamda {t['saldiri']} saldırı yanıtından {t['token_sizan_yanit']} tanesinde "
             f"token, {t['not_sizan_yanit']} tanesinde iç not işareti sızdı, normal yanıtlardan {t['kontrol_token_sizan']} tanesine token taşındı; "
             f"küçük bağlamda {k['token_sizan_yanit']} token / {k['not_sizan_yanit']} NOT işareti sızıntısı. Sipariş numarası: tam {t['kontrol_fayda']}, küçük {k['kontrol_fayda']}.")
```

```solution
import json
import re
import ai_lab

DESEN = re.compile(r"TOKEN-[A-Z0-9]{4}(?![A-Z0-9])")

def baglam_hazirla(kayit, alanlar):
    if not isinstance(kayit, dict) or set(kayit) != {"id", "soru", "token", "not"}:
        raise ValueError("kayıt tam id, soru, token, not alanlarını içermeli")
    if not all(isinstance(v, str) for v in kayit.values()) or not kayit["id"] or not kayit["soru"]:
        raise ValueError("kayıt değerleri metin olmalı; id ve soru boş olamaz")
    if not isinstance(alanlar, list) or not 1 <= len(alanlar) <= 3 or any(not isinstance(a,str) for a in alanlar) or len(set(alanlar)) != len(alanlar):
        raise ValueError("alanlar 1-3 öğeli, yinelenmeyen liste olmalı")
    if any(a not in ("id", "soru", "not") for a in alanlar):
        raise ValueError("yalnız id, soru, not seçilebilir")
    secili = {a: DESEN.sub("[GIZLI]", kayit[a]) for a in alanlar}
    return json.dumps(secili, ensure_ascii=False)

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_16 as deney
    deney.goster(baglam_hazirla)
```

```hint
Sözlüğü doğrudan `alanlar` listesi üzerinde kur; böylece hem sıra korunur hem de listede olmayan alan bağlama hiç girmez. Desenin sonundaki `(?![A-Z0-9])` beşinci karakterli tokenı maskelemez.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Bağlama girmeyen sır sızamaz (30 sn).** "Modele `gizli tut` talimatı vermek bir erişim kontrolü değildir; bağlama giren her ham veritabanı alanı veya API anahtarı istem enjeksiyonunda doğrudan maruziyet yüzeyidir."
2. **Alan daraltma ve desen maskeleme (35 sn).** "Model çağrısından önce deterministik katmanda yalnız görev için zorunlu alanlar seçilir (`data minimization`) ve serbest metindeki belirteç kalıpları sınır duyarlı ifadelerle maskelenir; ancak regex maskeleme tek başına tam DLP sayılmaz."
3. **En az yetki kapsamı (`Least Privilege`) (30 sn).** "Ajanın istediği yetkilerle görevin gerektirdiği kapsamın kesişimi (`istenen ∩ gerekli`) verilir; fazladan istenen her yetki açıkça reddedilip denetim izine yazılır."
4. **Soru (25 sn).** "Neden `TOKEN-[A-Z0-9]{4}` ifadesinde negatif ileri bakış (`(?![A-Z0-9])`) kullanmazsan daha uzun bir kimliğin ilk parçasını yanlışlıkla bozup kalan karakterleri açıkta bırakırsın?"
:::
