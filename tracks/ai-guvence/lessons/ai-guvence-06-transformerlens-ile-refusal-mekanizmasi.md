---
id: ai-guvence-06
title: TransformerLens ile Refusal Mekanizması
summary: Aktivasyon fixture'larından refusal-normal yön farkı çıkar, katman skorlarını davranışsal ölçümlerle ilişkilendir ve sonda TransformerLens ile gerçek instruct modelde refusal aktivasyonlarını ölç.
esleme: ai-guvence-10, ai-guvence-41, ai-temel-08
timeout: 300
---

::: anlat Aktivasyon izi davranışla birlikte okunur

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Aktivasyon cache'i belirli girdinin katman çıktılarını verir | İlk üç görev görünür sentetik JSON; final kurulu Qwen2.5-0.5B-Instruct ve TransformerBridge | Sentetik vektörler model kaydı değildir; grup adı gözlenen ret kararı değildir |
| Ortalama fark ve davranış gözlemi birlikte raporlanabilir | Gerçek son-token aktivasyonlarının ilk sekiz bileşeni, dört gerçek yanıt ve dar ret sezgiseli | Müdahale, evrensel refusal yönü veya katmana özel ret oranı ölçülmez; aynı oran için korelasyon None'dır |

> [!NOT]
> `veri/aktivasyon.json` elle hazırlanmış sentetik çalışma verisidir. İlk üç görev aynı dosyayı okur, ilk Çalıştır ham JSON'u gösterir. Setup her Run/Check için geçici veri/ kopyası kurar; değişiklikler sonraki çalıştırmaya taşınmaz. Kaynak dosyayı haricî editörde veya yüklenen sözlüğü kodda değiştirip yeniden Çalıştır deneyebilirsin. Gizli testler ayrıdır. Final yalnız önceden kurulu model ve TransformerLens'i kullanır; yeni indirme yoktur.

Mekanistik yorumlanabilirlik çalışmasında belirli katmanlardaki aktivasyonların refusal ve normal örnekler arasında nasıl değiştiği incelenebilir. Grup ortalamaları arasındaki fark bir yön özeti verir. Ancak bu özet tek başına modelin refusal kararını o yönün ürettiğini göstermez; davranışsal test ve müdahale deneyleri gerekir.

İlk üç görevde aktivasyonlar ve davranış oranları deterministik fixture olarak verilir; son görevde ise TransformerLens 4.3 (`TransformerBridge.boot_transformers`) kullanılarak sabit revizyonlu `Qwen/Qwen2.5-0.5B-Instruct` (`rev: 7ae557604adf67be50417f59c2c2f167def9a775`) modeli üzerinde gerçek katman aktivasyonları ve reddetme davranışı ölçülür.
:::

::: anlat Yön farkı ve korelasyon farklı sorulara cevap verir

Önce aktivasyon.json dosyasındaki kayitlar alanını aç. Her kayıt kimliği, katmanı, grup etiketini ve küçük bir vektörü taşır. Grupların refusal ve normal diye adlandırılması, bu sentetik satırlardan birinin gerçekten bir modelin reddetme durumuna ait olduğunu göstermez. İlk görev yalnız biçimi doğrular ve sıralı bağımsız kopyalar döndürür. Kaynak listeyi sıralamak veya iç vektörü paylaşmak, sonraki görevin girdisini sessizce değiştirebilir. Sonucun bir bileşenini değiştirdiğinde kaynak aynı kalmalıdır. Kimliği ASCII kurallarıyla sınırlamak da Unicode harf kabul eden genel bir karakter sınıfıyla aynı şey değildir; boşluk ve satır sonu gibi görünmeyen farklar ayrı kontrol ister.

İkinci görev dosyanın refusal ve normal vektör gruplarını alır. Örnek sayıları aynı olmak zorunda değildir; eşit olması gereken vektör boyutudur. Her grubun ortalaması kendi örnek sayısına bölünür. Bir grupta üç kayıt, diğerinde iki kayıt varsa toplamları doğrudan çıkarmak farklı bir nicelik üretir. Farkın L2 normunu yuvarlanmamış koordinatlardan hesapla. Önce koordinatları altı ondalığa yuvarlamak küçük farkların normunu bozabilir. İki ortalama aynıysa sıfır fark ve sıfır norm geçerlidir; bu, veri veya modelin bütün davranışlarının aynı olduğunu göstermez. Dosyadaki bir vektörü değiştirip farkın yönünü ve büyüklüğünü birlikte izle.

Üçüncü görev katman_bulgulari alanını kullanır. Buradaki oranlar da sentetik öğretim sayılarıdır. Pearson korelasyonu iki serinin birlikte değişimini ölçer. Skorlar değişirken bütün oranlar aynı kalıyorsa paydadaki varyans sıfırdır ve sonuç None olmalıdır. None değerini sıfır korelasyon diye yorumlama; burada korelasyon tanımlanamamıştır. En güçlü katman seçimi ise ayrı bir kuraldır: mutlak skor en büyük, eşitlikte katman numarası en küçük olan seçilir. Negatif büyük bir skorun mutlak büyüklüğünü unutmak veya aynı skorda son kaydı seçmek yanlış katmanı öne çıkarır. Girdi sırası bu eşitlik kararını etkilememelidir.

Gerçek finalde kurulu instruct model dört açık laboratuvar istemini yanıtlar. İki istem reddetme araştırması için, ikisi normal kullanım için seçilmiştir; bu tasarım etiketleri modelin mutlaka reddedeceği anlamına gelmez. İstemlerin system metinleri de farklıdır. Dolayısıyla grup ortalama farkı yalnız refusal davranışına bağlanamaz: talimat biçimi, konu ve token dizisi gibi etkenler karışıktır. Model bazen şaşırtıcı bir yanıt verebilir ve bu bulgu saklanır. Deneyin geçmesi belirli bir ret cümlesine veya saldırı başarısına bağlanmaz; tamamlanmış gerçek üretim ve doğru ölçüm gerekir.

TransformerBridge aynı gerçek girdinin katman cache'ini döndürür. Katman 6, 12 ve 18 için son konumun residual çıktısı alınır. Öğrencinin sayısal işlevleri ilk sekiz bileşen üzerinde çalışır; bunların normu bütün gizli boyutun normu değildir. Tam yakalanmış vektörler ayrıca kanıtta tutulur. Bu örnekleme öğretimi kolaylaştırır, bütün refusal mekanizmasını açıklamaz. Hedef model revizyonu, ağırlık SHA256, tokenizer girdileri, chat şablonlu tam metin, üretilen tokenlar, gerçek yanıtlar ve çalışma ayarları kaydedilir. Model dosyası veya ağırlığı eğitilmez, dış servis açılmaz.

Ret gözlemi birkaç dilsel işareti arayan sınırlı bir sezgiseldir. Yanıtta cannot geçmesi bir reddetme işareti olabilir; her dildeki veya dolaylı reddetmeyi kapsamaz. Normal bir açıklamada bu kelimenin bulunması da yanlış pozitif üretebilir. Bu nedenle ham yanıt ve işaret eşleşmeleri birlikte gösterilir. İki araştırma istemindeki sezgisel ret oranı bütün katmanlara aynı gözlem olarak eklenir; bu deney katmanlara müdahale etmediğinden üç farklı katman ret oranı üretemez. Oran sabit olduğundan gerçek finalde Pearson None kalır. Katman derinliğiyle oranı çarpıp artan bir sayı çizmek ölçüm değildir ve yapılmaz.

Bir saldırgan izinli bir araştırma ortamında girdileri değiştirip farklı aktivasyon izlerini inceleyebilir. Bir fark vektörünü bulmak, o vektörü silince güvenliğin kalkacağını veya ekleyince güvenliğin artacağını kanıtlamaz. Böyle bir iddia kontrollü müdahale, ayrı değerlendirme örnekleri ve normal işler üzerindeki yan etkilerin ölçümünü gerektirir. Bu dersin finali gözlemseldir; intervention veya ablation kabulü değildir. Dört örnek istatistiksel genelleme için yeterli sayılmaz. Örnek seçimi ve sezgisel etiket hataları açıklanmadan yüksek korelasyon görmek de güvence sağlamaz.

Çalıştır gerçek gözlemleri keşif kaydı olarak `kabul: false` saklar. Kontrol önce görülmemiş sentetik sınır vakalarıyla öğrenci işlevlerini sınar, ardından gerçek model ve cache yolunu doğrular. Eksik model veya kütüphane, başarısız üretim, kayıp aktivasyon veya yarım deney PASS sayılmaz. Hiçbir bağımlılık otomatik indirilmez. Rastgele veya sürüme duyarlı yanıt sabit metinle karşılaştırılmaz. Başarılı bir ders sonucu öğrencinin hesaplarının ve ölçüm yolunun doğru çalıştığını gösterir; modelin genel güvenliğinin veya belirli bir ret mekanizmasının kanıtı değildir.

Refusal ve normal grupların ortalama vektörleri arasındaki fark `ortalama(refusal)-ortalama(normal)` olarak hesaplanır. Farkın L2 normu, yön özetinin büyüklüğünü gösterir. Katman bazındaki yön skorları ile refusal oranları arasındaki Pearson korelasyonu ise birlikte değişimi ölçer.

Korelasyon için iki değişkenin de varyansı sıfırdan büyük olmalıdır; sabit seride sonuç `None` döndürülür. En güçlü katman, mutlak yön skoru en büyük olan katmandır ve eşitlikte düşük katman numarası seçilir. Korelasyon nedensellik değildir.

Kaynaklar: [Arditi vd. 2024 — Refusal in Language Models Is Mediated by a Single Direction (arXiv:2406.11717)](https://arxiv.org/abs/2406.11717), [Zou vd. 2023 — Representation Engineering: A Top-Down Approach to AI Transparency (arXiv:2310.01405)](https://arxiv.org/abs/2310.01405).
:::

::: tahmin Aktivasyon özetini tahmin et
Üç çıktı satırını yaz:

```python
print(round((0.1 + 0.3) / 2, 6))
print(round((10 ** 0.5), 6))
print(None if len({0.1, 0.1}) == 1 else "degisken")
```

???

```cikti
0.2
3.162278
None
```

İlk satır iki aktivasyon değerinin ortalaması, ikinci satır `[1,3]` fark vektörünün L2 normudur.
:::

::: gorev 1 · Aktivasyon kayıtlarını doğrula
`aktivasyon_kayitlarini_dogrula(kayitlar)` işlevini yaz. Kayıtlar boş olmayan listedir. Her kayıt tam olarak `id`, `katman`, `tur`, `vektor` alanlarını taşısın. Kimlik 1–64 karakterlik, ASCII harf/rakamla başlayan ve yalnız ASCII harf, rakam, alt çizgi veya tire içeren benzersiz stringdir. Katman bool olmayan, sıfır veya pozitif tamsayı; tür `refusal` veya `normal` olmalıdır.

Vektör boş olmayan listedir; her değer bool olmayan sonlu sayıdır. Bütün vektörler aynı boyutta olmalıdır. Geçersiz veride `ValueError` yükselt. Kayıtları `(katman, tur, id)` ile artan sıralayıp vektörleri de kopyalanmış yeni sözlüklerle döndür. Girdiyi değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-06")
```

```starter
from ai_guvence_veri import json_yukle,metin_yukle

def aktivasyon_kayitlarini_dogrula(kayitlar):
    # KUSURLU BAŞLANGIÇ KODU: sıralar fakat kaynak sözlük/vektörleri paylaşır ve şemayı doğrulamaz.
    return sorted(kayitlar,key=lambda x:(x["katman"],x["tur"],x["id"]))

v=json_yukle("veri/aktivasyon.json")
print("Sentetik ham dosya:\n",metin_yukle("veri/aktivasyon.json"))
print("Kayıtlar:",aktivasyon_kayitlarini_dogrula(v["kayitlar"]))
```

```test
import copy
A = [
    {"id": "n-1", "katman": 2, "tur": "normal", "vektor": [0, 1]},
    {"id": "r-1", "katman": 1, "tur": "refusal", "vektor": [1, 2]},
    {"id": "n-2", "katman": 1, "tur": "normal", "vektor": [0, 2]},
]
BEKLENEN = [A[2], A[1], A[0]]
def sozlesme(fn):
    try:
        once = copy.deepcopy(A)
        sonuc = fn(A)
        if sonuc != BEKLENEN or A != once or any(sonuc[i] is A[i] for i in range(len(A))):
            return False
        if any(sonuc[i]["vektor"] is A[i]["vektor"] for i in range(len(A))):
            return False
        if fn([dict(A[0], id="a" * 64, katman=0)])[0]["katman"] != 0:
            return False
        for kayitlar in [
            None, tuple(A), {}, [], [None], [dict(A[0], ek=1)], [dict(A[0], id=123)], [dict(A[0], id="")], [dict(A[0], id="a b")],
            [dict(A[0], id="a" * 65)], [dict(A[0], id=None)], [A[0], A[0]],
            [dict(A[0], katman=-1)], [dict(A[0], katman=True)], [dict(A[0], katman=1.0)], [dict(A[0], katman=None)],
            [dict(A[0], tur="baska")], [dict(A[0], tur=None)], [dict(A[0], vektor=[])], [dict(A[0], vektor=None)],
            [dict(A[0], vektor=(0, 1))], [dict(A[0], vektor="12")], [dict(A[0], vektor=[True, 1])], [dict(A[0], vektor=["0", 1])],
            [dict(A[0], vektor=[float("nan"), 1])], [dict(A[0], vektor=[float("inf"), 1])],
            [A[0], dict(A[1], vektor=[1, 2, 3])],
        ]:
            try:
                fn(kayitlar)
                return False
            except ValueError:
                pass
        kaynak={x["id"]:x for x in A}
        if any(x is kaynak[x["id"]] or x["vektor"] is kaynak[x["id"]]["vektor"] for x in sonuc):return False
        sonuc[0]["vektor"][0]=99
        if A!=once:return False
        for ad in ["_abc","-abc","éx","a\n"]:
            try:fn([dict(A[0],id=ad)]);return False
            except ValueError:pass
        return True
    except Exception:
        return False
ok(sozlesme(aktivasyon_kayitlarini_dogrula), "kayıt, vektor boyutu ve sıralama korunmalı")
def m_katman(kayitlar):
    return aktivasyon_kayitlarini_dogrula([dict(x, katman=0) for x in kayitlar])
def m_vektor(kayitlar):
    return aktivasyon_kayitlarini_dogrula([dict(x, vektor=[0 for _ in x["vektor"]]) for x in kayitlar])
def m_tur(kayitlar):
    return aktivasyon_kayitlarini_dogrula([dict(x, tur="normal") for x in kayitlar])
for ad, mutant in [("katmanları silen", m_katman), ("vektörleri silen", m_vektor), ("türleri değiştiren", m_tur)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_guvence_veri import json_yukle,metin_yukle

def aktivasyon_kayitlarini_dogrula(kayitlar):
    import math
    import re
    if not isinstance(kayitlar, list):
        raise ValueError("kayıtlar liste olmalı")
    if not kayitlar:
        raise ValueError("kayıtlar boş olamaz")
    kimlikler = set()
    boyut = None
    sonuc = []
    for kayit in kayitlar:
        if not isinstance(kayit, dict):
            raise ValueError("kayıt sözlük olmalı")
        if set(kayit) != {"id", "katman", "tur", "vektor"}:
            raise ValueError("kayıt şeması geçersiz")
        kimlik = kayit["id"]
        if not isinstance(kimlik, str):
            raise ValueError("kimlik string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kimlik):
            raise ValueError("kimlik geçersiz")
        if kimlik in kimlikler:
            raise ValueError("kimlik yinelenemez")
        katman = kayit["katman"]
        if isinstance(katman, bool) or not isinstance(katman, int):
            raise ValueError("katman tamsayı olmalı")
        if katman < 0:
            raise ValueError("katman negatif olamaz")
        if kayit["tur"] not in ("refusal", "normal"):
            raise ValueError("tür geçersiz")
        vektor = kayit["vektor"]
        if not isinstance(vektor, list):
            raise ValueError("vektör liste olmalı")
        if not vektor:
            raise ValueError("vektör boş olamaz")
        if boyut is None:
            boyut = len(vektor)
        if len(vektor) != boyut:
            raise ValueError("vektör boyutları farklı")
        for deger in vektor:
            if isinstance(deger, bool) or not isinstance(deger, (int, float)):
                raise ValueError("aktivasyon sayı olmalı")
            if not math.isfinite(deger):
                raise ValueError("aktivasyon sonlu olmalı")
        kimlikler.add(kimlik)
        sonuc.append({"id": kimlik, "katman": katman, "tur": kayit["tur"], "vektor": list(vektor)})
    return sorted(sonuc, key=lambda x: (x["katman"], x["tur"], x["id"]))

if __name__ == "__main__":
    v=json_yukle("veri/aktivasyon.json")
    print("Sentetik ham dosya:\n",metin_yukle("veri/aktivasyon.json"))
    print("Kayıtlar:",aktivasyon_kayitlarini_dogrula(v["kayitlar"]))
```

```hint
İlk vektörün boyutunu referans al. Her kaydı ve aktivasyon değerini doğruladıktan sonra vektörü listeyle kopyala.
```
:::

::: gorev 2 · Refusal-normal yön farkını hesapla
`grup_vektor_farki(refusal, normal)` işlevini yaz. İki girdi de boş olmayan vektör listeleridir. Her vektör boş olmayan, aynı boyutta ve bool olmayan sonlu sayılardan oluşan listedir; iki grubun boyutları da eşit olmalıdır. Geçersiz veride `ValueError` yükselt.

Her koordinatta grup ortalamalarını bul ve `refusal_normal_farki = ortalama(refusal)-ortalama(normal)` hesapla. `{"fark":[X,...],"l2":X}` döndür. Fark koordinatlarını ve L2 normunu altı ondalık basamağa yuvarla. Girdileri değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-06")
```

```starter
from ai_guvence_veri import json_yukle,metin_yukle

def grup_vektor_farki(refusal,normal):
    # KUSURLU BAŞLANGIÇ KODU: grup ortalamaları yerine toplamlarını çıkarır.
    import math
    fark=[sum(v[i] for v in refusal)-sum(v[i] for v in normal) for i in range(len(refusal[0]))]
    return {"fark":[round(x,6) for x in fark],"l2":round(math.hypot(*fark),6)}

v=json_yukle("veri/aktivasyon.json")
print("Sentetik grup farkı:",grup_vektor_farki(v["refusal"],v["normal"]))
```

```test
import copy
R = [[1, 3], [3, 5]]
N = [[0, 1], [2, 1]]
BEKLENEN = {"fark": [1.0, 3.0], "l2": 3.162278}
def sozlesme(fn):
    try:
        ronce = copy.deepcopy(R)
        nonce = copy.deepcopy(N)
        if fn(R, N) != BEKLENEN or R != ronce or N != nonce:
            return False
        if fn([[0, 0]], [[0, 0]]) != {"fark": [0.0, 0.0], "l2": 0.0}:
            return False
        if fn([[1 / 3]], [[0]]) != {"fark": [0.333333], "l2": 0.333333}:
            return False
        if fn([[1], [3]], [[0], [0], [0]])["fark"] != [2.0]:
            return False
        for refusal, normal in [
            (None, N), (R, None), (tuple(R), N), (R, tuple(N)), ({}, N), (R, {}), ([], []), ([], N), (R, []), ([None], N), (R, [None]),
            ([(1, 3)], N), (R, [(0, 1)]), ([[]], [[]]), ([[]], N), (R, [[]]),
            ([[1, 2, 99], [1, 2]], N), (R, [[0, 1, 99], [2, 1]]), ([[1, 2], [3]], N), (R, [[0], [1]]), ([[1]], [[0, 1]]),
            ([[True]], [[0]]), ([["1"]], [[0]]), ([[float("nan")]], [[0]]), ([[float("inf")]], [[0]]),
            ([[1]], [[True]]), ([[1]], [["0"]]), ([[1]], [[float("nan")]]), ([[1]], [[float("inf")]]),
        ]:
            try:
                fn(refusal, normal)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(grup_vektor_farki), "grup ortalamaları, fark ve L2 normu korunmalı")
def m_refusal(refusal, normal):
    return grup_vektor_farki([[0 for _ in refusal[0]]], normal)
def m_normal(refusal, normal):
    return grup_vektor_farki(refusal, [[0 for _ in normal[0]]])
def m_sil(refusal, normal):
    return grup_vektor_farki(refusal[:1], normal[:1])
for ad, mutant in [("refusal grubunu silen", m_refusal), ("normal grubu silen", m_normal), ("örnekleri azaltan", m_sil)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_guvence_veri import json_yukle,metin_yukle

def grup_vektor_farki(refusal, normal):
    import math
    def dogrula(grup):
        if not isinstance(grup, list):
            raise ValueError("grup liste olmalı")
        if not grup:
            raise ValueError("grup boş olamaz")
        boyut = None
        for vektor in grup:
            if not isinstance(vektor, list):
                raise ValueError("vektör liste olmalı")
            if not vektor:
                raise ValueError("vektör boş olamaz")
            if boyut is None:
                boyut = len(vektor)
            if len(vektor) != boyut:
                raise ValueError("grup içindeki vektör boyutları farklı")
            for deger in vektor:
                if isinstance(deger, bool) or not isinstance(deger, (int, float)):
                    raise ValueError("aktivasyon sayı olmalı")
                if not math.isfinite(deger):
                    raise ValueError("aktivasyon sonlu olmalı")
        return boyut
    rboyut = dogrula(refusal)
    nboyut = dogrula(normal)
    if rboyut != nboyut:
        raise ValueError("grup boyutları farklı")
    fark = []
    for i in range(rboyut):
        ro = sum(v[i] for v in refusal) / len(refusal)
        no = sum(v[i] for v in normal) / len(normal)
        fark.append(ro - no)
    return {"fark": [round(x, 6) for x in fark], "l2": round(math.sqrt(sum(x * x for x in fark)), 6)}

if __name__ == "__main__":
    v=json_yukle("veri/aktivasyon.json")
    print("Sentetik grup farkı:",grup_vektor_farki(v["refusal"],v["normal"]))
```

```hint
İki grubu aynı doğrulama yardımcısından geçir. Koordinat bazında ham farkları saklayıp normu yuvarlanmamış değerlerden hesapla.
```
:::

::: gorev 3 · Katman skorlarıyla davranışı ilişkilendir
`davranis_iliskisi(kayitlar)` işlevini yaz. Kayıtlar en az iki öğeli listedir. Her kayıt tam olarak `katman`, `yon_skoru`, `refusal_orani` alanlarını taşısın. Katman bool olmayan, sıfır veya pozitif ve benzersiz tamsayıdır. Yön skoru bool olmayan sonlu sayı, refusal oranı bool olmayan sonlu sayı ve `[0,1]` aralığındadır. Geçersiz veride `ValueError` yükselt.

Yön skorları ve refusal oranları arasında Pearson korelasyonu hesapla. Serilerden birinin varyansı sıfırsa korelasyon `None` olsun. `{"korelasyon":X_VEYA_NONE,"en_guclu_katman":N,"bulgular":[KAYIT,...]}` döndür. Korelasyonu altı ondalık basamağa yuvarla, bulguları katmana göre sırala ve kopyala. En güçlü katman mutlak yön skoru en büyük olan, eşitlikte en düşük numaralı katmandır. Girdiyi değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-06")
```

```starter
from ai_guvence_veri import json_yukle,metin_yukle

def davranis_iliskisi(kayitlar):
    # KUSURLU BAŞLANGIÇ KODU: sabit seriye de korelasyon1 atar ve mutlak skor yerine ham skoru seçer.
    return {"korelasyon":1.0,"en_guclu_katman":max(kayitlar,key=lambda x:x["yon_skoru"])["katman"],"bulgular":[dict(x) for x in sorted(kayitlar,key=lambda x:x["katman"])]}

v=json_yukle("veri/aktivasyon.json")
print("Sentetik davranış ilişkisi:",davranis_iliskisi(v["katman_bulgulari"]))
```

```test
import copy
K = [
    {"katman": 2, "yon_skoru": 0.2, "refusal_orani": 0.4},
    {"katman": 0, "yon_skoru": 0.1, "refusal_orani": 0.2},
    {"katman": 1, "yon_skoru": 0.3, "refusal_orani": 0.6},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        sonuc = fn(K)
        if sonuc["korelasyon"] != 1.0 or sonuc["en_guclu_katman"] != 1 or K != once:
            return False
        if [x["katman"] for x in sonuc["bulgular"]] != [0, 1, 2] or any(sonuc["bulgular"][i] is K[i] for i in range(len(K))):
            return False
        if fn(K[:2])["korelasyon"] != 1.0 or fn(K[:2])["en_guclu_katman"] != 2:
            return False
        negatif = [dict(K[0], yon_skoru=-1, refusal_orani=1), dict(K[1], yon_skoru=0, refusal_orani=0.5), dict(K[2], yon_skoru=1, refusal_orani=0)]
        if fn(negatif)["korelasyon"] != -1.0:
            return False
        sabit = [dict(x, yon_skoru=0.1) for x in K]
        if fn(sabit)["korelasyon"] is not None or fn(sabit)["en_guclu_katman"] != 0:
            return False
        if fn([dict(x, refusal_orani=0.5) for x in K])["korelasyon"] is not None:
            return False
        yuvarla = [dict(K[0], yon_skoru=1, refusal_orani=0.1), dict(K[1], yon_skoru=2, refusal_orani=0.2), dict(K[2], yon_skoru=3, refusal_orani=0.4)]
        if fn(yuvarla)["korelasyon"] != 0.981981:
            return False
        for kayitlar in [
            None, tuple(K), {}, [], [K[0]], [None, K[1]], [dict(K[0], ek=1), K[1]], [K[0], K[0]],
            [dict(K[0], katman=-1), K[1]], [dict(K[0], katman=True), K[1]], [dict(K[0], katman=1.0), K[1]],
            [dict(K[0], yon_skoru=True), K[1]], [dict(K[0], yon_skoru="0.2"), K[1]],
            [dict(K[0], yon_skoru=float("nan")), K[1]], [dict(K[0], yon_skoru=float("inf")), K[1]],
            [dict(K[0], refusal_orani=True), K[1]], [dict(K[0], refusal_orani="0.4"), K[1]],
            [dict(K[0], refusal_orani=float("nan")), K[1]], [dict(K[0], refusal_orani=float("inf")), K[1]],
            [dict(K[0], refusal_orani=-0.1), K[1]], [dict(K[0], refusal_orani=1.1), K[1]],
        ]:
            try:
                fn(kayitlar)
                return False
            except ValueError:
                pass
        for oran in [0,1]:
            q=fn([dict(K[0],refusal_orani=oran),dict(K[1],refusal_orani=oran)])
            if q["korelasyon"] is not None:return False
        b=[{"katman":2,"yon_skoru":-3,"refusal_orani":0},{"katman":0,"yon_skoru":3,"refusal_orani":1}]
        if fn(b)["en_guclu_katman"]!=0 or fn(list(reversed(b)))["en_guclu_katman"]!=0:return False
        return True
    except Exception:
        return False
ok(sozlesme(davranis_iliskisi), "korelasyon, sabit seri ve katman seçimi korunmalı")
def m_skor(kayitlar):
    return davranis_iliskisi([dict(x, yon_skoru=0) for x in kayitlar])
def m_davranis(kayitlar):
    return davranis_iliskisi([dict(x, refusal_orani=0) for x in kayitlar])
def m_sil(kayitlar):
    return davranis_iliskisi(kayitlar[:2])
for ad, mutant in [("skorları silen", m_skor), ("davranışı silen", m_davranis), ("katmanları azaltan", m_sil)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_guvence_veri import json_yukle,metin_yukle

def davranis_iliskisi(kayitlar):
    import math
    if not isinstance(kayitlar, list):
        raise ValueError("kayıtlar liste olmalı")
    if len(kayitlar) < 2:
        raise ValueError("en az iki katman gerekli")
    katmanlar = set()
    bulgular = []
    for kayit in kayitlar:
        if not isinstance(kayit, dict):
            raise ValueError("kayıt sözlük olmalı")
        if set(kayit) != {"katman", "yon_skoru", "refusal_orani"}:
            raise ValueError("kayıt şeması geçersiz")
        katman = kayit["katman"]
        if isinstance(katman, bool) or not isinstance(katman, int):
            raise ValueError("katman tamsayı olmalı")
        if katman < 0:
            raise ValueError("katman negatif olamaz")
        if katman in katmanlar:
            raise ValueError("katman yinelenemez")
        skor = kayit["yon_skoru"]
        if isinstance(skor, bool) or not isinstance(skor, (int, float)):
            raise ValueError("yön skoru sayı olmalı")
        if not math.isfinite(skor):
            raise ValueError("yön skoru sonlu olmalı")
        oran = kayit["refusal_orani"]
        if isinstance(oran, bool) or not isinstance(oran, (int, float)):
            raise ValueError("refusal oranı sayı olmalı")
        if not math.isfinite(oran):
            raise ValueError("refusal oranı sonlu olmalı")
        if oran < 0 or oran > 1:
            raise ValueError("refusal oranı aralık dışında")
        katmanlar.add(katman)
        bulgular.append({"katman": katman, "yon_skoru": skor, "refusal_orani": oran})
    xs = [x["yon_skoru"] for x in bulgular]
    ys = [x["refusal_orani"] for x in bulgular]
    if len(set(xs)) == 1 or len(set(ys)) == 1:
        korelasyon = None
    else:
        xo = sum(xs) / len(xs)
        yo = sum(ys) / len(ys)
        xv = sum((x - xo) ** 2 for x in xs)
        yv = sum((y - yo) ** 2 for y in ys)
        korelasyon = round(sum((x - xo) * (y - yo) for x, y in zip(xs, ys)) / math.sqrt(xv * yv), 6)
    en_guclu = min(bulgular, key=lambda x: (-abs(x["yon_skoru"]), x["katman"]))["katman"]
    return {"korelasyon": korelasyon, "en_guclu_katman": en_guclu, "bulgular": sorted(bulgular, key=lambda x: x["katman"])}

if __name__ == "__main__":
    v=json_yukle("veri/aktivasyon.json")
    print("Sentetik davranış ilişkisi:",davranis_iliskisi(v["katman_bulgulari"]))
```

```hint
Ortalamaları ve iki varyansı ayrı hesapla. Korelasyondan önce sıfır varyansı denetle; en güçlü katmanı mutlak skor ve katman çiftiyle seç.
```
:::

::: anlat TransformerLens 4.3 (`TransformerBridge`) ve `Qwen2.5-0.5B-Instruct` ile canlı refusal aktivasyonu deneyi
İlk üç görevde aktivasyon doğrulama, grup vektör farkı ve katman–davranış ilişkisini deterministik fixture'larla kurdun. Şimdi aynı üç işlevi **TransformerLens 4.3 (`transformer_lens.model_bridge.TransformerBridge.boot_transformers`)** üzerinden yerel `Qwen/Qwen2.5-0.5B-Instruct` (`rev: 7ae557604adf67be50417f59c2c2f167def9a775`) modeline bağlıyoruz:

1. İki refusal araştırması istemi (modelin reddetmesi garanti veya geçme şartı değildir) ve iki normal istem `bridge.run_with_cache(...)` ile çalıştırılır.
2. Katman 6, 12 ve 18'deki `blocks.{katman}.hook_resid_post` son token aktivasyon vektörleri toplanıp `aktivasyon_kayitlarini_dogrula` ve `grup_vektor_farki` işlevlerinden geçirilir.
3. Yön farkı normları ve aynı dört yanıtın gözlenen ret oranı raporlanır. Katmana özel müdahale yoktur: aynı oran üç katmanda yinelenir ve korelasyon None olur. Önceki sentetik görevdeki değişken oranlar gerçek ölçüm sanılmaz.
:::

::: gorev Gerçek deney · TransformerLens ile Qwen2.5-0.5B-Instruct üzerinde refusal yönü ölçümü
Önceki üç görevde yazdığın `aktivasyon_kayitlarini_dogrula(kayitlar)`, `grup_vektor_farki(refusal, normal)` ve `davranis_iliskisi(kayitlar)` işlevlerini burada birleştir.

```meta
motor: ai-gercek
gereksinim: torch
ortam: gpu
timeout: 300
```

```starter
import math
import re
import ai_lab
from sandbox import ai_gercek_ai_guvence_06 as L

def aktivasyon_kayitlarini_dogrula(kayitlar):
    # KUSURLU BAŞLANGIÇ KODU: kayıtları sıralamadan ve kopyalamadan olduğu gibi döndürüyor!
    return list(kayitlar) if isinstance(kayitlar, list) else []

def grup_vektor_farki(refusal, normal):
    return {"fark": [], "l2": 0.0}

def davranis_iliskisi(kayitlar):
    return {"korelasyon": None, "en_guclu_katman": 0, "bulgular": []}

if ai_lab.CALISTIR:
    L.goster(aktivasyon_kayitlarini_dogrula, grup_vektor_farki, davranis_iliskisi)
```

```test
import copy
import ai_lab
from sandbox import ai_gercek_ai_guvence_06 as L

checks = []
_base_ok = ok
def ok(kosul, mesaj):
    checks.append(bool(kosul))
    return _base_ok(kosul, mesaj)

import ast
yasak=("aktivasyon_kayitlarini_dogrula_referans","grup_vektor_farki_referans","davranis_iliskisi_referans","kanit_yaz","getattr")
ihlal=ai_lab.kod_denetimi(src,yasak=yasak)
try:
    for node in ast.walk(ast.parse(src)):
        if isinstance(node,ast.ImportFrom) and any(a.name in yasak or a.name=="*" for a in node.names):ihlal.append("referans ithali")
except SyntaxError:ihlal.append("sözdizimi")
ok(not ihlal,"Kendi aktivasyon hesaplarını yaz; referans ithali yasak")
if ihlal:stop()

def _sozlesme_kontrol():
    try:
        A = [
            {"id": "n-1", "katman": 2, "tur": "normal", "vektor": [0, 1]},
            {"id": "r-1", "katman": 1, "tur": "refusal", "vektor": [1, 2]},
            {"id": "n-2", "katman": 1, "tur": "normal", "vektor": [0, 2]},
        ]
        sonuc_a = aktivasyon_kayitlarini_dogrula(A)
        if sonuc_a != [A[2], A[1], A[0]] or any(sonuc_a[i]["vektor"] is A[i]["vektor"] for i in range(len(A))):
            return False
        for ba in [None, [], [A[0], A[0]], [dict(A[0], katman=-1)], [dict(A[0], tur="x")], [A[0], dict(A[1], vektor=[1, 2, 3])]]:
            try:
                aktivasyon_kayitlarini_dogrula(ba)
                return False
            except ValueError:
                pass

        if grup_vektor_farki([[1, 3], [3, 5]], [[0, 1], [2, 1]]) != {"fark": [1.0, 3.0], "l2": 3.162278}:
            return False
        for br, bn in [(None, [[0]]), ([], [[0]]), ([[1]], [[0, 1]]), ([[True]], [[0]])]:
            try:
                grup_vektor_farki(br, bn)
                return False
            except ValueError:
                pass

        K = [
            {"katman": 2, "yon_skoru": 0.2, "refusal_orani": 0.4},
            {"katman": 0, "yon_skoru": 0.1, "refusal_orani": 0.2},
            {"katman": 1, "yon_skoru": 0.3, "refusal_orani": 0.6},
        ]
        sonuc_k = davranis_iliskisi(K)
        if sonuc_k["korelasyon"] != 1.0 or sonuc_k["en_guclu_katman"] != 1 or [x["katman"] for x in sonuc_k["bulgular"]] != [0, 1, 2]:
            return False
        if davranis_iliskisi([dict(x, yon_skoru=0.1) for x in K])["korelasyon"] is not None:
            return False
        for bk in [None, [], [K[0]], [K[0], K[0]], [dict(K[0], refusal_orani=1.2), K[1]]]:
            try:
                davranis_iliskisi(bk)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

def _birim1(fn):
    import copy
    A = [
        {"id": "n-1", "katman": 2, "tur": "normal", "vektor": [0, 1]},
        {"id": "r-1", "katman": 1, "tur": "refusal", "vektor": [1, 2]},
        {"id": "n-2", "katman": 1, "tur": "normal", "vektor": [0, 2]},
    ]
    BEKLENEN = [A[2], A[1], A[0]]
    def sozlesme(fn):
        try:
            once = copy.deepcopy(A)
            sonuc = fn(A)
            if sonuc != BEKLENEN or A != once or any(sonuc[i] is A[i] for i in range(len(A))):
                return False
            if any(sonuc[i]["vektor"] is A[i]["vektor"] for i in range(len(A))):
                return False
            if fn([dict(A[0], id="a" * 64, katman=0)])[0]["katman"] != 0:
                return False
            for kayitlar in [
                None, tuple(A), {}, [], [None], [dict(A[0], ek=1)], [dict(A[0], id=123)], [dict(A[0], id="")], [dict(A[0], id="a b")],
                [dict(A[0], id="a" * 65)], [dict(A[0], id=None)], [A[0], A[0]],
                [dict(A[0], katman=-1)], [dict(A[0], katman=True)], [dict(A[0], katman=1.0)], [dict(A[0], katman=None)],
                [dict(A[0], tur="baska")], [dict(A[0], tur=None)], [dict(A[0], vektor=[])], [dict(A[0], vektor=None)],
                [dict(A[0], vektor=(0, 1))], [dict(A[0], vektor="12")], [dict(A[0], vektor=[True, 1])], [dict(A[0], vektor=["0", 1])],
                [dict(A[0], vektor=[float("nan"), 1])], [dict(A[0], vektor=[float("inf"), 1])],
                [A[0], dict(A[1], vektor=[1, 2, 3])],
            ]:
                try:
                    fn(kayitlar)
                    return False
                except ValueError:
                    pass
            kaynak={x["id"]:x for x in A}
            if any(x is kaynak[x["id"]] or x["vektor"] is kaynak[x["id"]]["vektor"] for x in sonuc):return False
            sonuc[0]["vektor"][0]=99
            if A!=once:return False
            for ad in ["_abc","-abc","éx","a\n"]:
                try:fn([dict(A[0],id=ad)]);return False
                except ValueError:pass
            return True
        except Exception:
            return False
    return sozlesme(fn)

def _birim2(fn):
    import copy
    R = [[1, 3], [3, 5]]
    N = [[0, 1], [2, 1]]
    BEKLENEN = {"fark": [1.0, 3.0], "l2": 3.162278}
    def sozlesme(fn):
        try:
            ronce = copy.deepcopy(R)
            nonce = copy.deepcopy(N)
            if fn(R, N) != BEKLENEN or R != ronce or N != nonce:
                return False
            if fn([[0, 0]], [[0, 0]]) != {"fark": [0.0, 0.0], "l2": 0.0}:
                return False
            if fn([[1 / 3]], [[0]]) != {"fark": [0.333333], "l2": 0.333333}:
                return False
            if fn([[1], [3]], [[0], [0], [0]])["fark"] != [2.0]:
                return False
            for refusal, normal in [
                (None, N), (R, None), (tuple(R), N), (R, tuple(N)), ({}, N), (R, {}), ([], []), ([], N), (R, []), ([None], N), (R, [None]),
                ([(1, 3)], N), (R, [(0, 1)]), ([[]], [[]]), ([[]], N), (R, [[]]),
                ([[1, 2, 99], [1, 2]], N), (R, [[0, 1, 99], [2, 1]]), ([[1, 2], [3]], N), (R, [[0], [1]]), ([[1]], [[0, 1]]),
                ([[True]], [[0]]), ([["1"]], [[0]]), ([[float("nan")]], [[0]]), ([[float("inf")]], [[0]]),
                ([[1]], [[True]]), ([[1]], [["0"]]), ([[1]], [[float("nan")]]), ([[1]], [[float("inf")]]),
            ]:
                try:
                    fn(refusal, normal)
                    return False
                except ValueError:
                    pass
            return True
        except Exception:
            return False
    return sozlesme(fn)

def _birim3(fn):
    import copy
    K = [
        {"katman": 2, "yon_skoru": 0.2, "refusal_orani": 0.4},
        {"katman": 0, "yon_skoru": 0.1, "refusal_orani": 0.2},
        {"katman": 1, "yon_skoru": 0.3, "refusal_orani": 0.6},
    ]
    def sozlesme(fn):
        try:
            once = copy.deepcopy(K)
            sonuc = fn(K)
            if sonuc["korelasyon"] != 1.0 or sonuc["en_guclu_katman"] != 1 or K != once:
                return False
            if [x["katman"] for x in sonuc["bulgular"]] != [0, 1, 2] or any(sonuc["bulgular"][i] is K[i] for i in range(len(K))):
                return False
            if fn(K[:2])["korelasyon"] != 1.0 or fn(K[:2])["en_guclu_katman"] != 2:
                return False
            negatif = [dict(K[0], yon_skoru=-1, refusal_orani=1), dict(K[1], yon_skoru=0, refusal_orani=0.5), dict(K[2], yon_skoru=1, refusal_orani=0)]
            if fn(negatif)["korelasyon"] != -1.0:
                return False
            sabit = [dict(x, yon_skoru=0.1) for x in K]
            if fn(sabit)["korelasyon"] is not None or fn(sabit)["en_guclu_katman"] != 0:
                return False
            if fn([dict(x, refusal_orani=0.5) for x in K])["korelasyon"] is not None:
                return False
            yuvarla = [dict(K[0], yon_skoru=1, refusal_orani=0.1), dict(K[1], yon_skoru=2, refusal_orani=0.2), dict(K[2], yon_skoru=3, refusal_orani=0.4)]
            if fn(yuvarla)["korelasyon"] != 0.981981:
                return False
            for kayitlar in [
                None, tuple(K), {}, [], [K[0]], [None, K[1]], [dict(K[0], ek=1), K[1]], [K[0], K[0]],
                [dict(K[0], katman=-1), K[1]], [dict(K[0], katman=True), K[1]], [dict(K[0], katman=1.0), K[1]],
                [dict(K[0], yon_skoru=True), K[1]], [dict(K[0], yon_skoru="0.2"), K[1]],
                [dict(K[0], yon_skoru=float("nan")), K[1]], [dict(K[0], yon_skoru=float("inf")), K[1]],
                [dict(K[0], refusal_orani=True), K[1]], [dict(K[0], refusal_orani="0.4"), K[1]],
                [dict(K[0], refusal_orani=float("nan")), K[1]], [dict(K[0], refusal_orani=float("inf")), K[1]],
                [dict(K[0], refusal_orani=-0.1), K[1]], [dict(K[0], refusal_orani=1.1), K[1]],
            ]:
                try:
                    fn(kayitlar)
                    return False
                except ValueError:
                    pass
            for oran in [0,1]:
                q=fn([dict(K[0],refusal_orani=oran),dict(K[1],refusal_orani=oran)])
                if q["korelasyon"] is not None:return False
            b=[{"katman":2,"yon_skoru":-3,"refusal_orani":0},{"katman":0,"yon_skoru":3,"refusal_orani":1}]
            if fn(b)["en_guclu_katman"]!=0 or fn(list(reversed(b)))["en_guclu_katman"]!=0:return False
            return True
        except Exception:
            return False
    return sozlesme(fn)

ok(_birim1(aktivasyon_kayitlarini_dogrula), "aktivasyon_kayitlarini_dogrula tam birim sözleşmesini geçmeli")
ok(_birim2(grup_vektor_farki), "grup_vektor_farki tam birim sözleşmesini geçmeli")
ok(_birim3(davranis_iliskisi), "davranis_iliskisi tam birim sözleşmesini geçmeli")
ok(_sozlesme_kontrol(), "aktivasyon_kayitlarini_dogrula, grup_vektor_farki ve davranis_iliskisi sözleşme kontrollerini geçmeli")
if not all(checks):
    stop()

try:
    rapor = L.deney(aktivasyon_kayitlarini_dogrula, grup_vektor_farki, davranis_iliskisi)
except ai_lab.GercekLabYok as e:
    ok(False, str(e))
    stop()
except Exception as e:
    ok(False, f"GERÇEK TRANSFORMERLENS REFUSAL DENEYİ YAPILAMADI: {type(e).__name__}: {e}")
    stop()

k = rapor["kontroller"]
ok(k["aktivasyon_dogrulama_uyumu"], f"aktivasyon_kayitlarini_dogrula canlı aktivasyonlarda referansla uyuşmalı")
ok(k["grup_farki_uyumu"], f"grup_vektor_farki canlı katman aktivasyonlarında referansla uyuşmalı: {rapor['ozet']['katman_l2_normlari']}")
ok(k["davranis_iliskisi_uyumu"], f"davranis_iliskisi canlı katman bulgularında referansla uyuşmalı: {rapor['iliski']}")
ok(k["gercek_uretim_tamamlandi"], "dört gerçek yanıt ve üç katmanın aktivasyonları eksiksiz; ret başarısı şart değildir")
ok(k["sabit_oran_durust"], "katmana özel uydurma oran yok; aynı gözlemle korelasyon None")

kabul = all(checks)
kanit_yolu = ai_lab.kanit_yaz("guvence-06-transformerlens-refusal", dict(rapor, kaynak="gercek", kabul=kabul))
o = rapor["ozet"]
print(f"GERÇEK TRANSFORMERLENS DENEYİ: model={o['model']}@{o['revizyon']} en_guclu_katman={o['en_guclu_katman']} L2={o['katman_l2_normlari']} kanıt={kanit_yolu}")
```

```solution
import math
import re
import ai_lab
from sandbox import ai_gercek_ai_guvence_06 as L

def aktivasyon_kayitlarini_dogrula(kayitlar):
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar liste olmalı")
    kimlikler = set()
    boyut = None
    sonuc = []
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"id", "katman", "tur", "vektor"}:
            raise ValueError("kayıt şeması geçersiz")
        kimlik = kayit["id"]
        if not isinstance(kimlik, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kimlik) or kimlik in kimlikler:
            raise ValueError("kimlik geçersiz")
        katman = kayit["katman"]
        if isinstance(katman, bool) or not isinstance(katman, int) or katman < 0:
            raise ValueError("katman geçersiz")
        if kayit["tur"] not in ("refusal", "normal"):
            raise ValueError("tür geçersiz")
        vektor = kayit["vektor"]
        if not isinstance(vektor, list) or not vektor:
            raise ValueError("vektör geçersiz")
        if boyut is None:
            boyut = len(vektor)
        if len(vektor) != boyut:
            raise ValueError("vektör boyutları farklı")
        for deger in vektor:
            if isinstance(deger, bool) or not isinstance(deger, (int, float)) or not math.isfinite(deger):
                raise ValueError("aktivasyon geçersiz")
        kimlikler.add(kimlik)
        sonuc.append({"id": kimlik, "katman": katman, "tur": kayit["tur"], "vektor": list(vektor)})
    return sorted(sonuc, key=lambda x: (x["katman"], x["tur"], x["id"]))

def grup_vektor_farki(refusal, normal):
    def dogrula(grup):
        if not isinstance(grup, list) or not grup:
            raise ValueError("grup geçersiz")
        boyut = None
        for vektor in grup:
            if not isinstance(vektor, list) or not vektor:
                raise ValueError("vektör geçersiz")
            if boyut is None:
                boyut = len(vektor)
            if len(vektor) != boyut:
                raise ValueError("boyut farklı")
            for deger in vektor:
                if isinstance(deger, bool) or not isinstance(deger, (int, float)) or not math.isfinite(deger):
                    raise ValueError("değer geçersiz")
        return boyut
    rboyut = dogrula(refusal)
    nboyut = dogrula(normal)
    if rboyut != nboyut:
        raise ValueError("grup boyutları farklı")
    fark = []
    for i in range(rboyut):
        ro = sum(v[i] for v in refusal) / len(refusal)
        no = sum(v[i] for v in normal) / len(normal)
        fark.append(ro - no)
    return {"fark": [round(x, 6) for x in fark], "l2": round(math.sqrt(sum(x * x for x in fark)), 6)}

def davranis_iliskisi(kayitlar):
    if not isinstance(kayitlar, list) or len(kayitlar) < 2:
        raise ValueError("en az iki katman gerekli")
    katmanlar = set()
    bulgular = []
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"katman", "yon_skoru", "refusal_orani"}:
            raise ValueError("şema geçersiz")
        katman = kayit["katman"]
        if isinstance(katman, bool) or not isinstance(katman, int) or katman < 0 or katman in katmanlar:
            raise ValueError("katman geçersiz")
        skor = kayit["yon_skoru"]
        if isinstance(skor, bool) or not isinstance(skor, (int, float)) or not math.isfinite(skor):
            raise ValueError("skor geçersiz")
        oran = kayit["refusal_orani"]
        if isinstance(oran, bool) or not isinstance(oran, (int, float)) or not math.isfinite(oran) or oran < 0 or oran > 1:
            raise ValueError("oran geçersiz")
        katmanlar.add(katman)
        bulgular.append({"katman": katman, "yon_skoru": skor, "refusal_orani": oran})
    xs = [x["yon_skoru"] for x in bulgular]
    ys = [x["refusal_orani"] for x in bulgular]
    if len(set(xs)) == 1 or len(set(ys)) == 1:
        korelasyon = None
    else:
        xo = sum(xs) / len(xs)
        yo = sum(ys) / len(ys)
        xv = sum((x - xo) ** 2 for x in xs)
        yv = sum((y - yo) ** 2 for y in ys)
        korelasyon = round(sum((x - xo) * (y - yo) for x, y in zip(xs, ys)) / math.sqrt(xv * yv), 6)
    en_guclu = min(bulgular, key=lambda x: (-abs(x["yon_skoru"]), x["katman"]))["katman"]
    return {"korelasyon": korelasyon, "en_guclu_katman": en_guclu, "bulgular": sorted(bulgular, key=lambda x: x["katman"])}

if ai_lab.CALISTIR:
    L.goster(aktivasyon_kayitlarini_dogrula, grup_vektor_farki, davranis_iliskisi)
```

```hint
Önceki üç görevde yazdığın `aktivasyon_kayitlarini_dogrula`, `grup_vektor_farki` ve `davranis_iliskisi` işlevlerini eksiksiz taşı; canlı deneyde TransformerBridge ile katman 6, 12 ve 18 aktivasyonları ölçülür.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Rezidüel akışta ortalama fark yönü (30 sn).** "Transformer katmanlarında reddedilen ve normal istemlerin son-token aktivasyon ortalamaları arasındaki fark (`ortalama(refusal) - ortalama(normal)`) ve L2 normu, katmanlar arası ayrışma sinyali için gözlemsel bir özet üretir."
2. **Sıfır varyans ve gözlemsel sınır (35 sn).** "Katmanlara ayrı müdahale yapılmayan bir koşuda gözlenen ret oranı bütün katmanlarda sabittir; varyans sıfır olduğunda uydurma eğri çizmek yerine Pearson korelasyonu dürüstçe `None` raporlanır."
3. **Korelasyon nedensellik değildir (30 sn).** "Bir katmanda L2 farkının büyük çıkması ret kararını tek başına o yönün ürettiğini kanıtlamaz; nedensel iddia için kontrollü projeksiyon/ablasyon müdahalesi (bkz. `ai-guvence-10`) gerekir."
4. **Soru (25 sn).** "İki grupta örnek sayıları farklıyken ortalamaları çıkarmak yerine toplam vektörleri çıkarmak yön özetini nasıl çarpıtır?"
:::
