---
id: ai-guvence-29
title: Sorumlu Bildirim Raporu
summary: Sentetik bulguyu kapsam, kanıt, yeniden üretim adımları ve belirsizliklerle raporla; CVSS etiketi ve yayın öncesi onayı doğrula.
esleme: ai-guvence-30, ai-guvence-33, ai-ctf-10
timeout: 45
---

::: anlat Sorumlu bildirim yetki ve kanıtla sınırlıdır
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Tekrarlanabilir bulgu, kaynak kanıt, kapsam ve gönderimden önce insan kararı | Görevler 1–3 görünür sentetik bildirim JSON'u; son görev gerçek CPU eğitimi/FGSM kanıtını maskeler, dosya hash'lerini hesaplar ve yerel ZIP'i yeniden doğrular | Sentetik bulgu gerçek ürün zafiyeti veya CVE değildir; gönderime hazır etiketi bildirim gönderildiği anlamına gelmez |

> [!NOT]
> `veri/bildirim.json` ve `veri/onay.json` sentetik öğretim verisidir. Setup her çalıştırmada geçici dizine yeniden kopyalar; kalıcılık yoktur. Başlangıç kodları aynı dosyayı okur ve sonuç yazdırır; aynı çalıştırmada bellekte kopyayla deneme yapılabilir. Son gerçek deneyin `PAFTA_DATA/calisma/ai-guvence-29/ayar.json` ayarı ayrıdır ve kalıcıdır; varsa üzerine yazılmaz. Hiçbir görev e-posta göndermez veya dış hedefle iletişim kurmaz; test girdileri bu örneklerden bağımsızdır.

Sorumlu bildirim raporu yalnız yetkili veya sentetik bir bulguyu konu alır. Etki, kapsam, kanıt ve yeniden üretim adımları ayrı başlıklarda verilir. Bilinmeyenler gizlenmez; belirsizlikler açıkça yazılır. Bu ders gerçek hedef taramaz, Git işlemi yapmaz ve CVSS Calculator çalıştırmaz; İlk üç görev sentetik dosya kaydı kullanır; son görev sentetik veride gerçek model çıktılarından yerel bildirim paketi oluşturur.

Raporun kimliği ve başlığı yanında yetki durumu, sayısal CVSS puanı, etki etiketi ve doğrulama durumu bulunur. Kapsam, kanıt ve adım listeleri boş bırakılamaz. Yeniden üretim adımları somut ve yinelenmeyen girdilerden oluşur; böylece okuyan kişi aynı sentetik sonucu izleyebilir.
:::

::: anlat Yayın kararı puanın ötesinde denetim gerektirir
CVSS puanı etki etiketiyle tutarlı olmalıdır: 0.0 `yok`, 0.1–3.9 `dusuk`, 4.0–6.9 `orta`, 7.0–8.9 `yuksek`, 9.0–10.0 `kritik` olarak etiketlenir. Puan tek başına sorumlu bildirimin bütününü anlatmaz; kapsam ve belirsizlikler yine raporlanır.

Gönderimden önce açık insan onayı, doğrulanmış rapor durumu ve puan–etki uyumu denetlenir. Belirsizlik bulunması yayını engellemez, ancak belirsizlik sayısı rapora eklenir. Markdown çıktısı kanıtı büyütmez veya varsayılmayan bir etki üretmez; yalnız doğrulanmış kaydı biçimlendirir.
:::

::: anlat Ham kayıttan doğrulanmış yerel pakete
Bir bulgu raporunun ilk işi okuyan kişiye hangi gözlemin hangi iddiayı desteklediğini göstermektir. Başlık kısa olabilir; fakat kapsam, yeniden üretim adımları ve belirsizlikler birbirinin yerine geçmez. Bir modelin tek sentetik deneyde bozulması gerçek bir üründe aynı açığın bulunduğunu göstermez. Bu derste gerçek hedef aranmaz ve dışarıya bildirim yapılmaz. İlk üç görevde sayısal CVSS puanı hazır verilmiş bir öğretim alanıdır; puanın temel vektörü hesaplanmaz ve puanın gerçek bir zafiyet değerlendirmesi olduğu iddia edilmez. Etiketi doğru eşlemek, etkiyi keşfetmekle aynı işlem değildir.

Önce `veri/bildirim.json` dosyasını ham biçimde açıp koddan yazdır. Yetki alanı, sentetik veya yetkili kapsamı anlatır; bu alanı değiştirmek gerçek bir sisteme erişim yetkisi oluşturmaz. Kanıt ve adım listelerinin boş olmaması raporu yeniden izlemeyi kolaylaştırır. Yinelenen adımları iki ayrı kanıt gibi sunma. Başlığa satır sonu eklemek Markdown başlık düzenini bozabileceğinden sözleşme bunu reddeder. Şema kontrolü rapordaki iddianın gerçekliğini doğrulamaz; yalnız biçimsel giriş kurallarını uygular. İlk başlangıç kodu özellikle bu doğrulamayı atladığı için çalışmasına rağmen yanlıştır.

İkinci görev aynı dosyayı Markdown raporuna dönüştürür. Puanı sınıfa eşleştirirken sınır değerlerini izle; fakat görsel olarak yüksek görünen bir etiketle gözlem kapsamını büyütme. Belirsizlik bölümünü sonradan silmek raporun daha kesin görünmesine yol açar. Örneğin yalnız sentetik veri kullanıldığını yazmak bir kusur değil, sonucun nerede durduğunu açıklayan bilgidir. Başlangıç kodunun hangi bilgiyi kaybettiğini dosya ile çıktıyı yan yana okuyarak bul. Üçüncü görev `veri/onay.json` içindeki insan onayı temsilini de kontrol eder. Buradaki gönderime hazır sonucu yalnız yerel durum etiketidir; hiçbir ağ çağrısı veya gönderim gerçekleştirmez.

Canlı adımda küçük sınıflandırıcı gerçekten eğitilir ve FGSM ile temiz ve bozulmuş örnek tahminleri ölçülür. Rastgele üretilmiş sentetik canary ham JSON'a birden fazla yerde yazılır. Öğrencinin maskeleme fonksiyonu bu işaretin bütün tekrarlarını değiştirirken geri kalan metni korumalıdır. İlk görünen örneği sabitlemek veya yalnız ilk eşleşmeyi değiştirmek ikinci bir işarette sır bırakır. Buradaki tam eşleşme maskelemesi genel kişisel veri tespiti değildir; farklı kodlanmış veya başka bir sır biçimini kendiliğinden bulmaz. Görev yalnız verilen canary sözleşmesini sınar.

Ham kanıt özel adlı ayrı yerel klasörde kalır; paylaşılabilir olarak hazırlanan klasörde maskeli kanıt, ayar, model kaydı ve rapor bulunur. Dosya adlarına karşı SHA-256 byte hash'leri manifestte saklanır. Metin satır sonunu veya kodlamayı değiştirirsen byte hash'inin değişmesi normaldir. ZIP oluşturulduktan sonra arşiv tekrar açılır ve içindeki dosyaların hash'leri öğrenci manifestiyle karşılaştırılır. Böylece fonksiyon yalnız bellekte bir sözlük döndürmez, gerçek diskteki paketin bütünlük denetimini etkiler. Manifestin kendisi kendi hash listesine döngüsel biçimde eklenmez.

Saldırgan veya yanlış hazırlanmış bir rapor, güçlü görünen puanı öne çıkarıp eksik kapsamı, sızan işareti veya tekrarlanamayan adımı saklayabilir. Savunma hem ham gözlemi hem yayınlanacak kopyayı ayrı incelemelidir. Hash eşleşmesi dosyanın doğru bilimsel iddia taşıdığını veya güvenilir bir kişi tarafından yazıldığını kanıtlamaz; imza veya kimlik doğrulama yerine geçmez. Bu deneyde saldırının mutlaka başarılı olması kabul koşulu değildir. Kanıtın doğru maskelenmesi, manifestin doğru hesaplanması ve arşivin verilen kurallara uyması sınanır. Sonuç yerel taslaktır; özel veriyle gerçek bildirim süreci ayrıca kapsam ve insan kararını gerektirir.
:::

::: tahmin CVSS etiketini ve yayın koşulunu tahmin et
Üç çıktı satırını yaz:

```python
print("kritik" if 9.1 >= 9.0 else "diger")
print(round(7 / 2, 6))
print(True and "dogrulandi" == "dogrulandi")
```

???

```cikti
kritik
3.5
True
```

İlk satır puanın etki etiketini, ikinci satır iki liste öğesinin toplam uzunluk ortalamasını, üçüncü satır açık onay ile doğrulanmış durumun birlikte sağlandığını gösterir.
:::

::: gorev 1 · Sorumlu bildirim kaydını doğrula
`bildirim_kaydi_dogrula(kayit)` işlevini yaz. Kayıt tam olarak `id`, `baslik`, `yetki`, `cvss`, `etki`, `durum`, `kapsam`, `kanit`, `adimlar`, `belirsizlikler` alanlarını taşır. Kimlik 1–64 karakterlik, ASCII harf/rakamla başlayan ve yalnız ASCII harf, rakam, alt çizgi veya tire içeren; başlık 1–120 karakterlik stringdir. Bütün metinler satır sonu içeremez.

Yetki yalnız `sentetik` veya `yetkili`, etki yalnız `yok`, `dusuk`, `orta`, `yuksek`, `kritik`, durum yalnız `taslak` veya `dogrulandi` olur. CVSS bool olmayan, sonlu, 0.0–10.0 aralığında `int` veya `float` olmalıdır.

Kapsam, kanıt ve adımlar boş olmayan; belirsizlikler boş olabilen listelerdir. Her öğe 1–200 karakterlik, satır sonu içermeyen stringdir ve aynı liste içinde öğeler yinelenemez. Geçersiz veride `ValueError` yükselt. İç listeleri de bağımsız olan derin kopya döndür ve girdiyi değiştirme.

```starter
def bildirim_kaydi_dogrula(kayit):
    # KUSURLU BAŞLANGIÇ KODU: şema ve liste kurallarını denetlemiyor, iç listeleri de bağımsız kopyalamıyor.
    return dict(kayit)

from ai_guvence_veri import json_yukle
print(bildirim_kaydi_dogrula(json_yukle("veri/bildirim.json")))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-29")
```

```test
import copy
K = {"id": "AI-SENT-01", "baslik": "Sentetik politika sapması", "yetki": "sentetik", "cvss": 7.5, "etki": "yuksek", "durum": "dogrulandi", "kapsam": ["sentetik-eval"], "kanit": ["fixture-sonucu"], "adimlar": ["Fixture verisini yükle", "Raporu çalıştır"], "belirsizlikler": ["Yalnız sentetik kapsam"]}
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        sonuc = fn(K)
        if sonuc != K or sonuc is K or any(sonuc[a] is K[a] for a in ("kapsam", "kanit", "adimlar", "belirsizlikler")) or K != once:
            return False
        sonuc["kapsam"].append("kopya")
        if K["kapsam"] != ["sentetik-eval"]:
            return False
        sinir = dict(K, id="a" * 64, baslik="b" * 120, yetki="yetkili", cvss=10, etki="kritik", durum="taslak", kapsam=["k" * 200], kanit=["e" * 200], adimlar=["a" * 200], belirsizlikler=[])
        if fn(sinir) != sinir or fn(dict(K, cvss=0))["cvss"] != 0:
            return False
        if fn(dict(K, baslik="b"))["baslik"] != "b" or fn(dict(K, kapsam=["k"]))["kapsam"] != ["k"]:
            return False
        for kayit in [
            None, [], dict(K, ek=1), dict(K, id=""), dict(K, id="a b"), dict(K, id="a" * 65), dict(K, id=None),
            dict(K, baslik=""), dict(K, baslik="b" * 121), dict(K, baslik="a\nb"), dict(K, baslik="a\rb"), dict(K, baslik=None),
            dict(K, yetki="yetkisiz"), dict(K, yetki=None), dict(K, etki="diger"), dict(K, etki=None), dict(K, durum="yayinlandi"), dict(K, durum=None),
            dict(K, cvss=-0.1), dict(K, cvss=10.1), dict(K, cvss=float("nan")), dict(K, cvss=float("inf")), dict(K, cvss=True), dict(K, cvss=None),
            dict(K, kapsam=[]), dict(K, kapsam={}), dict(K, kapsam=[""]), dict(K, kapsam=["k" * 201]), dict(K, kapsam=["a\nb"]), dict(K, kapsam=["a\rb"]), dict(K, kapsam=[None]), dict(K, kapsam=["x", "x"]),
            dict(K, kanit=[]), dict(K, kanit=[None]), dict(K, kanit=["x", "x"]), dict(K, adimlar=[]), dict(K, adimlar=[1]), dict(K, adimlar=["x", "x"]),
            dict(K, belirsizlikler={}), dict(K, belirsizlikler=[None]), dict(K, belirsizlikler=["x", "x"]),
        ]:
            try:
                fn(kayit)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(bildirim_kaydi_dogrula and sozlesme(bildirim_kaydi_dogrula), "bildirim şeması, listeler ve sayı sınırları korunmalı")
def m_cvss(kayit):
    return bildirim_kaydi_dogrula(dict(kayit, cvss=True))
def m_liste(kayit):
    return bildirim_kaydi_dogrula(dict(kayit, adimlar=[]))
def m_kopya(kayit):
    sonuc = bildirim_kaydi_dogrula(kayit)
    sonuc["kapsam"].clear()
    return sonuc
def m_yetki(kayit):
    return bildirim_kaydi_dogrula(dict(kayit, yetki="yetkisiz"))
for ad, mutant in [("CVSS türünü bozan", m_cvss), ("adımları silen", m_liste), ("kapsamı silen", m_kopya), ("yetkiyi bozan", m_yetki)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def bildirim_kaydi_dogrula(kayit):
    import copy
    import math
    import re
    if not isinstance(kayit, dict):
        raise ValueError("kayıt sözlük olmalı")
    alanlar = {"id", "baslik", "yetki", "cvss", "etki", "durum", "kapsam", "kanit", "adimlar", "belirsizlikler"}
    if set(kayit) != alanlar:
        raise ValueError("kayıt şeması geçersiz")
    if not isinstance(kayit["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
        raise ValueError("kimlik geçersiz")
    if not isinstance(kayit["baslik"], str) or not 1 <= len(kayit["baslik"]) <= 120 or "\n" in kayit["baslik"] or "\r" in kayit["baslik"]:
        raise ValueError("başlık geçersiz")
    if kayit["yetki"] not in ("sentetik", "yetkili") or kayit["etki"] not in ("yok", "dusuk", "orta", "yuksek", "kritik") or kayit["durum"] not in ("taslak", "dogrulandi"):
        raise ValueError("yetki, etki veya durum geçersiz")
    if not isinstance(kayit["cvss"], (int, float)) or isinstance(kayit["cvss"], bool) or not math.isfinite(kayit["cvss"]) or not 0 <= kayit["cvss"] <= 10:
        raise ValueError("CVSS geçersiz")
    for alan in ("kapsam", "kanit", "adimlar", "belirsizlikler"):
        deger = kayit[alan]
        if not isinstance(deger, list) or (alan != "belirsizlikler" and not deger):
            raise ValueError("liste geçersiz")
        for oge in deger:
            if not isinstance(oge, str) or not 1 <= len(oge) <= 200 or "\n" in oge or "\r" in oge:
                raise ValueError("liste öğesi geçersiz")
        if len(set(deger)) != len(deger):
            raise ValueError("liste öğeleri yinelenemez")
    return copy.deepcopy(kayit)

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    print(bildirim_kaydi_dogrula(json_yukle("veri/bildirim.json")))
```

```hint
Dört listeyi ortak döngüde doğrula; yalnız belirsizliklerin boş olmasına izin ver. Derin kopyayı bütün doğrulamalardan sonra döndür.
```
:::

::: gorev 2 · CVSS etiketiyle Markdown bildirim raporu üret
`bildirim_markdown(kayit)` işlevini yaz. Kayıt ilk görevdeki kurallara uyar; geçersiz veride `ValueError` yükselt. Puanın etiketi 0.0 için `yok`, 0.1–3.9 için `dusuk`, 4.0–6.9 için `orta`, 7.0–8.9 için `yuksek`, 9.0–10.0 için `kritik` olur. Kayıttaki etki alanını değiştirmeden hesaplanan etiketi kullan.

Tam olarak şu satır düzeninde string döndür:

```text
# Bulgu: {baslik}
- Kimlik: {id}
- Yetki: {yetki}
- Durum: {durum}
- Etki: {hesaplanan_etiket} ({cvss bir ondalık})

## Kapsam
- {her kapsam öğesi}

## Kanıt
- {her kanıt öğesi}

## Yeniden Üretim
1. {birinci adım}
2. {ikinci adım}

## Belirsizlikler
- {her belirsizlik öğesi}
```

Belirsizlik listesi boşsa o bölümde tek `- Belirsizlik bildirilmedi` satırı bulunur. Bölümler arasında bir boş satır bırak; başlangıçtaki beş meta satırı arasında boş satır olmasın. Son satırı newline ile bitir. Girdiyi değiştirme.

```starter
def bildirim_markdown(kayit):
    import math
    import re
    if not isinstance(kayit, dict):
        raise ValueError("kayıt sözlük olmalı")
    alanlar = {"id", "baslik", "yetki", "cvss", "etki", "durum", "kapsam", "kanit", "adimlar", "belirsizlikler"}
    if set(kayit) != alanlar:
        raise ValueError("kayıt şeması geçersiz")
    if not isinstance(kayit["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
        raise ValueError("kimlik geçersiz")
    if not isinstance(kayit["baslik"], str) or not 1 <= len(kayit["baslik"]) <= 120 or "\n" in kayit["baslik"] or "\r" in kayit["baslik"]:
        raise ValueError("başlık geçersiz")
    if kayit["yetki"] not in ("sentetik", "yetkili") or kayit["etki"] not in ("yok", "dusuk", "orta", "yuksek", "kritik") or kayit["durum"] not in ("taslak", "dogrulandi"):
        raise ValueError("yetki, etki veya durum geçersiz")
    if not isinstance(kayit["cvss"], (int, float)) or isinstance(kayit["cvss"], bool) or not math.isfinite(kayit["cvss"]) or not 0 <= kayit["cvss"] <= 10:
        raise ValueError("CVSS geçersiz")
    for alan in ("kapsam", "kanit", "adimlar", "belirsizlikler"):
        deger = kayit[alan]
        if not isinstance(deger, list) or (alan != "belirsizlikler" and not deger):
            raise ValueError("liste geçersiz")
        for oge in deger:
            if not isinstance(oge, str) or not 1 <= len(oge) <= 200 or "\n" in oge or "\r" in oge:
                raise ValueError("liste öğesi geçersiz")
        if len(set(deger)) != len(deger):
            raise ValueError("liste öğeleri yinelenemez")
    puan = kayit["cvss"]
    if puan == 0:
        etiket = "yok"
    elif puan < 4:
        etiket = "dusuk"
    elif puan < 7:
        etiket = "orta"
    elif puan < 9:
        etiket = "yuksek"
    else:
        etiket = "kritik"
    # KUSURLU BAŞLANGIÇ KODU: var olan belirsizlikleri rapordan saklıyor.
    satirlar = [f"# Bulgu: {kayit['baslik']}", f"- Kimlik: {kayit['id']}", f"- Yetki: {kayit['yetki']}", f"- Durum: {kayit['durum']}", f"- Etki: {etiket} ({puan:.1f})", "", "## Kapsam"]
    satirlar += ["- " + x for x in kayit["kapsam"]]
    satirlar += ["", "## Kanıt"]
    satirlar += ["- " + x for x in kayit["kanit"]]
    satirlar += ["", "## Yeniden Üretim"]
    satirlar += [f"{i}. {x}" for i, x in enumerate(kayit["adimlar"], 1)]
    satirlar += ["", "## Belirsizlikler"]
    satirlar += ["- " + x for x in kayit["belirsizlikler"]] if False else ["- Belirsizlik bildirilmedi"]
    return "\n".join(satirlar) + "\n"

from ai_guvence_veri import json_yukle
print(bildirim_markdown(json_yukle("veri/bildirim.json")))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-29")
```

```test
import copy
K = {"id": "AI-SENT-01", "baslik": "Sentetik politika sapması", "yetki": "sentetik", "cvss": 7.5, "etki": "yuksek", "durum": "dogrulandi", "kapsam": ["sentetik-eval"], "kanit": ["fixture-sonucu"], "adimlar": ["Fixture verisini yükle", "Raporu çalıştır"], "belirsizlikler": ["Yalnız sentetik kapsam"]}
BEKLENEN = "# Bulgu: Sentetik politika sapması\n- Kimlik: AI-SENT-01\n- Yetki: sentetik\n- Durum: dogrulandi\n- Etki: yuksek (7.5)\n\n## Kapsam\n- sentetik-eval\n\n## Kanıt\n- fixture-sonucu\n\n## Yeniden Üretim\n1. Fixture verisini yükle\n2. Raporu çalıştır\n\n## Belirsizlikler\n- Yalnız sentetik kapsam\n"
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        if fn(K) != BEKLENEN or K != once:
            return False
        bos = fn(dict(K, belirsizlikler=[]))
        if not bos.endswith("## Belirsizlikler\n- Belirsizlik bildirilmedi\n") or bos.count("\n\n") != 4:
            return False
        for puan, etiket in [(0, "yok"), (0.1, "dusuk"), (3.9, "dusuk"), (4, "orta"), (6.9, "orta"), (7, "yuksek"), (8.9, "yuksek"), (9, "kritik"), (10, "kritik")]:
            if f"- Etki: {etiket} ({puan:.1f})\n" not in fn(dict(K, cvss=puan)):
                return False
        sinir = dict(K, id="a" * 64, baslik="b" * 120, cvss=10, kapsam=["k" * 200], kanit=["e" * 200], adimlar=["a" * 200], belirsizlikler=[])
        if not fn(sinir).startswith("# Bulgu: " + "b" * 120 + "\n"):
            return False
        if "- Etki: dusuk (0.0)\n" not in fn(dict(K, cvss=0.04)):
            return False
        kisa = dict(K, baslik="b", kapsam=["k"], kanit=["e"], adimlar=["a"], belirsizlikler=["b"])
        if "# Bulgu: b\n" not in fn(kisa) or "- k\n" not in fn(kisa):
            return False
        for kayit in [
            None, {}, dict(K, ek=1), dict(K, id="a b"), dict(K, id="a" * 65), dict(K, id=None), dict(K, baslik=""), dict(K, baslik="b" * 121), dict(K, baslik="a\nb"), dict(K, baslik="a\rb"), dict(K, baslik=None),
            dict(K, yetki="diger"), dict(K, etki="diger"), dict(K, durum="diger"), dict(K, cvss=-1), dict(K, cvss=11), dict(K, cvss=True), dict(K, cvss=None), dict(K, cvss=float("nan")),
            dict(K, kapsam=[]), dict(K, kapsam=[None]), dict(K, kapsam=[""]), dict(K, kapsam=["k" * 201]), dict(K, kapsam=["a\nb"]), dict(K, kapsam=["a\rb"]), dict(K, kapsam=["x", "x"]), dict(K, kanit=[]), dict(K, adimlar=[]), dict(K, belirsizlikler={}), dict(K, belirsizlikler=["x", "x"]),
        ]:
            try:
                fn(kayit)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(bildirim_markdown), "Markdown düzeni, CVSS sınırları ve belirsizlik notu korunmalı")
def m_puan(kayit):
    return bildirim_markdown(dict(kayit, cvss=9.0))
def m_liste(kayit):
    return bildirim_markdown(dict(kayit, adimlar=["Tek adım"]))
def m_belirsiz(kayit):
    return bildirim_markdown(dict(kayit, belirsizlikler=[]))
def m_baslik(kayit):
    return bildirim_markdown(dict(kayit, baslik="Değişen başlık"))
for ad, mutant in [("puanı değiştiren", m_puan), ("adımları değiştiren", m_liste), ("belirsizliği silen", m_belirsiz), ("başlığı değiştiren", m_baslik)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def bildirim_markdown(kayit):
    import math
    import re
    if not isinstance(kayit, dict):
        raise ValueError("kayıt sözlük olmalı")
    alanlar = {"id", "baslik", "yetki", "cvss", "etki", "durum", "kapsam", "kanit", "adimlar", "belirsizlikler"}
    if set(kayit) != alanlar:
        raise ValueError("kayıt şeması geçersiz")
    if not isinstance(kayit["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
        raise ValueError("kimlik geçersiz")
    if not isinstance(kayit["baslik"], str) or not 1 <= len(kayit["baslik"]) <= 120 or "\n" in kayit["baslik"] or "\r" in kayit["baslik"]:
        raise ValueError("başlık geçersiz")
    if kayit["yetki"] not in ("sentetik", "yetkili") or kayit["etki"] not in ("yok", "dusuk", "orta", "yuksek", "kritik") or kayit["durum"] not in ("taslak", "dogrulandi"):
        raise ValueError("yetki, etki veya durum geçersiz")
    if not isinstance(kayit["cvss"], (int, float)) or isinstance(kayit["cvss"], bool) or not math.isfinite(kayit["cvss"]) or not 0 <= kayit["cvss"] <= 10:
        raise ValueError("CVSS geçersiz")
    for alan in ("kapsam", "kanit", "adimlar", "belirsizlikler"):
        deger = kayit[alan]
        if not isinstance(deger, list) or (alan != "belirsizlikler" and not deger):
            raise ValueError("liste geçersiz")
        for oge in deger:
            if not isinstance(oge, str) or not 1 <= len(oge) <= 200 or "\n" in oge or "\r" in oge:
                raise ValueError("liste öğesi geçersiz")
        if len(set(deger)) != len(deger):
            raise ValueError("liste öğeleri yinelenemez")
    puan = kayit["cvss"]
    if puan == 0:
        etiket = "yok"
    elif puan < 4:
        etiket = "dusuk"
    elif puan < 7:
        etiket = "orta"
    elif puan < 9:
        etiket = "yuksek"
    else:
        etiket = "kritik"
    satirlar = [f"# Bulgu: {kayit['baslik']}", f"- Kimlik: {kayit['id']}", f"- Yetki: {kayit['yetki']}", f"- Durum: {kayit['durum']}", f"- Etki: {etiket} ({puan:.1f})", "", "## Kapsam"]
    satirlar += ["- " + x for x in kayit["kapsam"]]
    satirlar += ["", "## Kanıt"]
    satirlar += ["- " + x for x in kayit["kanit"]]
    satirlar += ["", "## Yeniden Üretim"]
    satirlar += [f"{i}. {x}" for i, x in enumerate(kayit["adimlar"], 1)]
    satirlar += ["", "## Belirsizlikler"]
    satirlar += ["- " + x for x in kayit["belirsizlikler"]] if kayit["belirsizlikler"] else ["- Belirsizlik bildirilmedi"]
    return "\n".join(satirlar) + "\n"

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    print(bildirim_markdown(json_yukle("veri/bildirim.json")))
```

```hint
Etiketi puanın tam sınırlarından hesapla. Liste bölümlerini ayrı ayrı ekle; belirsizlikler boşsa alternatif tek satırı kullan.
```
:::

::: gorev 3 · Gönderim onayını ve rapor tutarlılığını denetle
`bildirim_gonderim_raporu(kayit, onayli)` işlevini yaz. Kayıt ilk görevdeki kurallara uyar; `onayli` bool olmalıdır. Geçersiz veride `ValueError` yükselt.

İkinci görevdeki puan sınırlarıyla hesaplanan etiketi `seviye` alanında döndür. `onayli` değilse `onay_eksik`; durum `dogrulandi` değilse `dogrulama_eksik`; kayıttaki etki hesaplanan seviyeden farklıysa `etki_cvss_uyusmaz` alarmı ekle. Alarmları bu sırayla üret. Alarm yoksa karar `gonderime_hazir`, varsa `duzeltme_gerekli` olur.

`{"seviye":S,"alarmlar":A,"belirsizlik_sayisi":B,"karar":K}` döndür. Belirsizlik sayısı listenin uzunluğudur ve tek başına alarm üretmez. Girdiyi değiştirme.

```starter
def bildirim_gonderim_raporu(kayit, onayli):
    import math
    import re
    if not isinstance(onayli, bool):
        raise ValueError("onay bool olmalı")
    if not isinstance(kayit, dict):
        raise ValueError("kayıt sözlük olmalı")
    alanlar = {"id", "baslik", "yetki", "cvss", "etki", "durum", "kapsam", "kanit", "adimlar", "belirsizlikler"}
    if set(kayit) != alanlar:
        raise ValueError("kayıt şeması geçersiz")
    if not isinstance(kayit["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
        raise ValueError("kimlik geçersiz")
    if not isinstance(kayit["baslik"], str) or not 1 <= len(kayit["baslik"]) <= 120 or "\n" in kayit["baslik"] or "\r" in kayit["baslik"]:
        raise ValueError("başlık geçersiz")
    if kayit["yetki"] not in ("sentetik", "yetkili") or kayit["etki"] not in ("yok", "dusuk", "orta", "yuksek", "kritik") or kayit["durum"] not in ("taslak", "dogrulandi"):
        raise ValueError("yetki, etki veya durum geçersiz")
    if not isinstance(kayit["cvss"], (int, float)) or isinstance(kayit["cvss"], bool) or not math.isfinite(kayit["cvss"]) or not 0 <= kayit["cvss"] <= 10:
        raise ValueError("CVSS geçersiz")
    for alan in ("kapsam", "kanit", "adimlar", "belirsizlikler"):
        deger = kayit[alan]
        if not isinstance(deger, list) or (alan != "belirsizlikler" and not deger):
            raise ValueError("liste geçersiz")
        for oge in deger:
            if not isinstance(oge, str) or not 1 <= len(oge) <= 200 or "\n" in oge or "\r" in oge:
                raise ValueError("liste öğesi geçersiz")
        if len(set(deger)) != len(deger):
            raise ValueError("liste öğeleri yinelenemez")
    puan = kayit["cvss"]
    if puan == 0:
        seviye = "yok"
    elif puan < 4:
        seviye = "dusuk"
    elif puan < 7:
        seviye = "orta"
    elif puan < 9:
        seviye = "yuksek"
    else:
        seviye = "kritik"
    # KUSURLU BAŞLANGIÇ KODU: insan onayı koşulunu ters yorumluyor.
    alarmlar = []
    if onayli:
        alarmlar.append("onay_eksik")
    if kayit["durum"] != "dogrulandi":
        alarmlar.append("dogrulama_eksik")
    if kayit["etki"] != seviye:
        alarmlar.append("etki_cvss_uyusmaz")
    return {"seviye": seviye, "alarmlar": alarmlar, "belirsizlik_sayisi": len(kayit["belirsizlikler"]), "karar": "duzeltme_gerekli" if alarmlar else "gonderime_hazir"}

from ai_guvence_veri import json_yukle
onay = json_yukle("veri/onay.json")
print(bildirim_gonderim_raporu(json_yukle("veri/bildirim.json"), **onay))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-29")
```

```test
import copy
K = {"id": "AI-SENT-01", "baslik": "Sentetik politika sapması", "yetki": "sentetik", "cvss": 7.5, "etki": "yuksek", "durum": "dogrulandi", "kapsam": ["sentetik-eval"], "kanit": ["fixture-sonucu"], "adimlar": ["Fixture verisini yükle", "Raporu çalıştır"], "belirsizlikler": ["Yalnız sentetik kapsam"]}
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        if fn(K, True) != {"seviye": "yuksek", "alarmlar": [], "belirsizlik_sayisi": 1, "karar": "gonderime_hazir"} or K != once:
            return False
        if fn(K, False)["alarmlar"] != ["onay_eksik"]:
            return False
        taslak = dict(K, durum="taslak", etki="kritik")
        if fn(taslak, False)["alarmlar"] != ["onay_eksik", "dogrulama_eksik", "etki_cvss_uyusmaz"] or fn(taslak, True)["karar"] != "duzeltme_gerekli":
            return False
        if fn(dict(K, belirsizlikler=[]), True)["belirsizlik_sayisi"] != 0 or fn(dict(K, belirsizlikler=[]), True)["karar"] != "gonderime_hazir":
            return False
        for puan, etiket in [(0, "yok"), (0.1, "dusuk"), (3.9, "dusuk"), (4, "orta"), (6.9, "orta"), (7, "yuksek"), (8.9, "yuksek"), (9, "kritik"), (10, "kritik")]:
            sonuc = fn(dict(K, cvss=puan, etki=etiket, belirsizlikler=[]), True)
            if sonuc["seviye"] != etiket or sonuc["alarmlar"] != []:
                return False
        if fn(dict(K, cvss=0.04, etki="dusuk"), True)["seviye"] != "dusuk" or fn(dict(K, cvss=3.95, etki="dusuk"), True)["seviye"] != "dusuk":
            return False
        sinir = dict(K, id="a" * 64, baslik="b" * 120, cvss=10, etki="kritik", kapsam=["k" * 200], kanit=["e" * 200], adimlar=["a" * 200], belirsizlikler=[])
        if fn(sinir, True)["karar"] != "gonderime_hazir":
            return False
        kisa = dict(K, baslik="b", kapsam=["k"], kanit=["e"], adimlar=["a"], belirsizlikler=["b"])
        if fn(kisa, True)["karar"] != "gonderime_hazir":
            return False
        for args in [
            (None, True), ({}, True), (dict(K, ek=1), True), (dict(K, id="a" * 65), True), (dict(K, id=None), True), (dict(K, baslik=""), True), (dict(K, baslik="b" * 121), True), (dict(K, baslik=None), True), (dict(K, baslik="a\nb"), True), (dict(K, baslik="a\rb"), True), (dict(K, yetki="diger"), True),
            (dict(K, cvss=-1), True), (dict(K, cvss=11), True), (dict(K, cvss=True), True), (dict(K, cvss=None), True), (dict(K, cvss=float("inf")), True),
            (dict(K, etki="diger"), True), (dict(K, durum="diger"), True), (dict(K, kapsam=[]), True), (dict(K, kanit=[]), True), (dict(K, adimlar=[]), True),
            (dict(K, kapsam=[None]), True), (dict(K, kapsam=[""]), True), (dict(K, kapsam=["k" * 201]), True), (dict(K, kapsam=["a\nb"]), True), (dict(K, kapsam=["a\rb"]), True),
            (dict(K, belirsizlikler={}), True), (dict(K, kapsam=["x", "x"]), True), (K, None), (K, 1), (K, "evet"),
        ]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(bildirim_gonderim_raporu), "onay, doğrulama, CVSS uyumu ve belirsizlik sayısı korunmalı")
def m_onay(kayit, onayli):
    return bildirim_gonderim_raporu(kayit, False)
def m_durum(kayit, onayli):
    return bildirim_gonderim_raporu(dict(kayit, durum="taslak"), onayli)
def m_etki(kayit, onayli):
    return bildirim_gonderim_raporu(dict(kayit, etki="kritik"), onayli)
def m_belirsiz(kayit, onayli):
    return bildirim_gonderim_raporu(dict(kayit, belirsizlikler=[]), onayli)
for ad, mutant in [("onayı silen", m_onay), ("durumu bozan", m_durum), ("etkiyi bozan", m_etki), ("belirsizliği silen", m_belirsiz)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def bildirim_gonderim_raporu(kayit, onayli):
    import math
    import re
    if not isinstance(onayli, bool):
        raise ValueError("onay bool olmalı")
    if not isinstance(kayit, dict):
        raise ValueError("kayıt sözlük olmalı")
    alanlar = {"id", "baslik", "yetki", "cvss", "etki", "durum", "kapsam", "kanit", "adimlar", "belirsizlikler"}
    if set(kayit) != alanlar:
        raise ValueError("kayıt şeması geçersiz")
    if not isinstance(kayit["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
        raise ValueError("kimlik geçersiz")
    if not isinstance(kayit["baslik"], str) or not 1 <= len(kayit["baslik"]) <= 120 or "\n" in kayit["baslik"] or "\r" in kayit["baslik"]:
        raise ValueError("başlık geçersiz")
    if kayit["yetki"] not in ("sentetik", "yetkili") or kayit["etki"] not in ("yok", "dusuk", "orta", "yuksek", "kritik") or kayit["durum"] not in ("taslak", "dogrulandi"):
        raise ValueError("yetki, etki veya durum geçersiz")
    if not isinstance(kayit["cvss"], (int, float)) or isinstance(kayit["cvss"], bool) or not math.isfinite(kayit["cvss"]) or not 0 <= kayit["cvss"] <= 10:
        raise ValueError("CVSS geçersiz")
    for alan in ("kapsam", "kanit", "adimlar", "belirsizlikler"):
        deger = kayit[alan]
        if not isinstance(deger, list) or (alan != "belirsizlikler" and not deger):
            raise ValueError("liste geçersiz")
        for oge in deger:
            if not isinstance(oge, str) or not 1 <= len(oge) <= 200 or "\n" in oge or "\r" in oge:
                raise ValueError("liste öğesi geçersiz")
        if len(set(deger)) != len(deger):
            raise ValueError("liste öğeleri yinelenemez")
    puan = kayit["cvss"]
    if puan == 0:
        seviye = "yok"
    elif puan < 4:
        seviye = "dusuk"
    elif puan < 7:
        seviye = "orta"
    elif puan < 9:
        seviye = "yuksek"
    else:
        seviye = "kritik"
    alarmlar = []
    if not onayli:
        alarmlar.append("onay_eksik")
    if kayit["durum"] != "dogrulandi":
        alarmlar.append("dogrulama_eksik")
    if kayit["etki"] != seviye:
        alarmlar.append("etki_cvss_uyusmaz")
    return {"seviye": seviye, "alarmlar": alarmlar, "belirsizlik_sayisi": len(kayit["belirsizlikler"]), "karar": "duzeltme_gerekli" if alarmlar else "gonderime_hazir"}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    onay = json_yukle("veri/onay.json")
    print(bildirim_gonderim_raporu(json_yukle("veri/bildirim.json"), **onay))
```

```hint
CVSS sınıflandırmasını ikinci görevle aynı tut. Üç alarmı ayrı koşullarla ve belirtilen sırada ekle; belirsizlik sayısını karardan bağımsız hesapla.
```
:::


::: anlat Gerçek deney · Gerçek kanıttan yerel bildirim paketi
Önce görünür sentetik [ayar dosyasını](/data/ai-guvence-29-deney.txt) incele: /data/ai-guvence-29-deney.txt. Bu bir sunucu kaydı değildir. Çalıştır ilk kullanımda ayrı kalıcı kopya oluşturur ve gerçek yol/içeriğini gösterir. Yerleşik dosya editörü yoktur; yolu yerel editörde aç, seed veya eps değiştir ve yeniden Çalıştır. Kopya varsa üzerine yazılmaz. Göreli PAFTA_DATA proje köküne göre çözülür; geçici koşucu klasörüne göre değil. Kontrol ayrı görülmemiş ayarı kullanır; öğrenci dosyasını değiştirmek beklenen cevabı değiştirmez.

kanit_maskele(text,canary): yalnız verilen canary bütün tekrarlarını [MASKELI] ile değiştir; kalan metni koru. bildirim_manifesti(files): gerçek Path listesini ada göre sıralayıp dosyaadı:SHA256(byte) sözlüğü üret. Fonksiyonlar gerçekten eğitilen modele yapılan FGSM ölçümünün kanıtını ve diskteki ZIP paketini belirler. Özel ham kanıt ayrı klasörde kalır; maskeli ZIP yeniden okunup hash ve canary açısından doğrulanır. Bu yalnız sentetik yerel bulgu taslağıdır; gerçek ürün zafiyeti/CVE iddiası yoktur. Bildirim gönderilmez.

CPU .ai-venv torch ile gerçek Adam/autograd eğitimi, ağırlık hash'i, ham logitler ve ölçüm kanıtı yazılır. Model indirilmez, GPU kullanılmaz. Testte geçici ağırlıklar temizlenir; eğitim/logit/hash kanıtta korunur. Çalıştır çıktıları kalıcı öğrenci klasöründe kalır. Eski adımlar yukarıda fixture olarak korunmuştur; bu ek adım canlı deneydir.

Kaynaklar: [ISO/IEC 29147:2018 — Information Technology: Vulnerability Disclosure](https://www.iso.org/standard/72311.html), [FIRST — CVSS v3.1 Specification Document](https://www.first.org/cvss/v3.1/specification-document).
:::

::: gorev Gerçek deney · Gerçek kanıttan yerel bildirim paketi
kanit_maskele(text,canary): yalnız verilen canary bütün tekrarlarını [MASKELI] ile değiştir; kalan metni koru. bildirim_manifesti(files): gerçek Path listesini ada göre sıralayıp dosyaadı:SHA256(byte) sözlüğü üret. Fonksiyonlar gerçekten eğitilen modele yapılan FGSM ölçümünün kanıtını ve diskteki ZIP paketini belirler. Özel ham kanıt ayrı klasörde kalır; maskeli ZIP yeniden okunup hash ve canary açısından doğrulanır. Bu yalnız sentetik yerel bulgu taslağıdır; gerçek ürün zafiyeti/CVE iddiası yoktur. Bildirim gönderilmez.

```meta
motor: ai-gercek
gereksinim: torch
timeout: 120
```

```starter
def kanit_maskele(*args):
    return None

def bildirim_manifesti(*args):
    return None

import ai_lab
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_29 as deney
    deney.goster(kanit_maskele,bildirim_manifesti)
```

```test
import ai_lab
import ast
YASAK = ("attack_ref", "redact_ref", "manifest_ref", "kanit_yaz")
sorunlar = ai_lab.kod_denetimi(src, yasak=YASAK)
for dugum in ast.walk(ast.parse(src)):
    if isinstance(dugum, ast.ImportFrom):
        if any(ad.name in YASAK or ad.name == "*" for ad in dugum.names):
            sorunlar.append("referans veya kanıt yazıcısı içe aktarılamaz")
if sorunlar:
    ok(False, "Kendi ölçüm işlevlerini yaz: " + "; ".join(sorunlar))
    stop()
import tempfile
from pathlib import Path
from sandbox import ai_gercek_ai_guvence_29 as deney
# Test configuration is separate from the persistent editable student copy.
import hashlib as _hl
ok(kanit_maskele('a GIZLI b GIZLI c', 'GIZLI') == 'a [MASKELI] b [MASKELI] c' and kanit_maskele('temiz metin', 'GIZLI') == 'temiz metin', 'kanit_maskele tüm canary tekrarlarını [MASKELI] ile değiştirmeli')
with tempfile.TemporaryDirectory(prefix='pafta-guvence-29-u-') as _ut:
    _p2 = Path(_ut) / 'z.txt'; _p1 = Path(_ut) / 'a.txt'
    _p2.write_bytes(b'123'); _p1.write_bytes(b'abc')
    _mf = bildirim_manifesti([_p2, _p1])
    ok(list(_mf.keys()) == ['a.txt', 'z.txt'] and _mf == {'a.txt': _hl.sha256(b'abc').hexdigest(), 'z.txt': _hl.sha256(b'123').hexdigest()}, 'bildirim_manifesti sıralı dosya adlarıyla SHA-256 sözlüğü üretmeli')
with tempfile.TemporaryDirectory(prefix="pafta-guvence-29-") as tmp:
    config=Path(tmp)/"ayar.json"
    config.write_text('{"seed":942,"eps":0.23}',encoding="utf-8")
    r=deney.deney(kanit_maskele,bildirim_manifesti,config,Path(tmp)/"deney")
    for name,value in r["kontroller"].items():ok(value,"GERCEK: "+name)
    ai_lab.kanit_yaz("guvence-29",dict(r,kabul=all(r["kontroller"].values())))
```

```solution
def kanit_maskele(text,canary):
    return text.replace(canary,'[MASKELI]')

def bildirim_manifesti(files):
    import hashlib
    return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}

import ai_lab
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_29 as deney
    deney.goster(kanit_maskele,bildirim_manifesti)
```

```hint
Fonksiyonların etkisini gerçek model/araç akışında koru. Sabit oran veya hep izin/red kullanma. Bağımlılık yoksa gerçek kabul verilmez. Veri sentetiktir, eğitim ve dosya etkileri gerçektir.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Yeniden üretilemeyen bildirim aksiyon üretmez (30 sn).** "Sorumlu güvenlik bildirimi (`CVD`) 'modeli kırdım' ekran görüntüsü değildir; test edilen kapsamı, kesin yeniden üretim adımlarını, `CVSS` ciddiyet uyumunu ve açık belirsizlik sınırlarını yapısal olarak belgelemelidir."
2. **Kanıt bütünlüğü + gizli veri maskeleme (35 sn).** "Bildirim paketindeki ham günlüklerde gerçek anahtar veya hassas `canary` kalmamalı (`[MASKELI]`), aynı zamanda paketlenen dosyaların `SHA-256` manifestosu karşı tarafın kanıtı doğrulamasına imkân vermelidir."
3. **İnsan onayı ve yetki kapısı (30 sn).** "Doğrulanmamış taslaklar veya `CVSS` puanıyla metin etiketi çelişen raporlar otomatik gönderilmez; açık insan onayı (`onayli=True`) olmadan dış bildirim çıkmaz."
4. **Soru (25 sn).** "Deterministik olmayan bir LLM güvenlik bulgusunu karşı ekibin yeniden üretebilmesi için rapora hangi ortam ve örnekleme parametrelerini eklemek şarttır?"
:::
