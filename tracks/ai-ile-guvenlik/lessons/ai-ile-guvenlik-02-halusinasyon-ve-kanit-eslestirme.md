---
id: ai-ile-guvenlik-02
title: "Güvenlik Analizinde Halüsinasyon ve Kanıt Eşleştirme"
summary: Modelin raporladığı dosya adını, satır numarasını, kod kanıtını ve önerilen paketi gerçek kaynak haritasıyla çapraz doğrula; halüsinasyon oranını ölç ve uydurma bulguları ele.
timeout: 300
esleme: ai-ile-guvenlik-01, ai-ile-guvenlik-04
---

::: anlat Gerçek biçimi bil, sentetik temsili ayırt et
Büyük dil modellerinin (LLM) statik kod analizi (SAST) ve güvenlik açığı denetimlerinde kullanımı hızla yaygınlaşmaktadır. Bir önceki derste model çıktısını katı bir JSON şemasına zorlamayı öğrendik. Ancak şemaya uymak, üretilen **içeriğin gerçek ve doğrulanabilir olduğu** anlamına gelmez. Dil modelleri olasılıksal belirteç (token) dizilimleri ürettiklerinden, kod tabanını incelerken sıklıkla 5 satırlık bir dosyada `"satir_no": 99` raporlar, repoda var olmayan hayali dosya adları (`olmayan_dosya.py`) uydurur ya da yama önerilerinde gerçekte var olmayan paketler (`uydurma-sec-shield`) önerir.

Güvenlik mühendisliğinde ve MLSecOps süreçlerinde temel aksiyom şudur: **Fiziksel kaynak koduyla ve satır kanıtıyla birebir eşleşmeyen her model iddiası bir halüsinasyondur ve doğrudan elenmelidir.**

### 1. Aracın Altında Ne Olur: Dört Katmanlı Kanıt Merdiveni
Otomatik bir kanıt eşleştirme motoru, modelden gelen her güvenlik iddiasını sırasıyla dört deterministik doğrulama filtresinden geçirir:
1. **Dosya Varlığı Doğrulaması (`uydurma_dosya`):** İddia edilen dosya (`dosya_adi`) projenin taranan kaynak haritasında (`kaynak_haritasi["dosyalar"]`) mevcut mu? Eğer model repoda hiç yer almayan bir dosya adı vermişse, iddia ilk adımda elenir.
2. **Satır Sınırı Kontrolü (`uydurma_satir`):** Araçlar ve modeller satır numaralarını insan gözüyle uyumlu olarak 1-tabanlı (`1..N`) raporlar. Raporlanan `satir_no` değeri ilgili dosyanın toplam satır sayısını (`len(dosyalar[dosya_adi])`) aşıyorsa, satır uydurmadır.
3. **Kanıt Alt Dizgesi Eşleştirmesi (`uyusmayan_kanit`):** Modelin zafiyet gerekçesi olarak gösterdiği kod parçası (`kanit_alt_dizgesi`), ilgili satır metninin (`dosyalar[dosya_adi][satir_no - 1]`) içinde gerçekten geçiyor mu? Model doğru satır numarasını verip başka bir satırın kodunu kanıt göstermişse veya kodu hayal etmişse eşleşme başarısız olur.
4. **Paket ve Bağımlılık Doğrulaması (`uydurma_paket`):** Modelin zafiyeti onarmak için önerdiği kütüphane (`onerilen_paket`), kuruluşun onaylı ve taranmış bağımlılık listesinde (`bilinen_paketler`) yer alıyor mu?

### 2. Çıktı Nasıl Okunur: Halüsinasyon Türleri ve Güvenilirlik Kapısı
Modelin güvenlik analiz performansı yalnız tekil iddiaların doğrulanmasıyla değil, iki temel analitik katmanla değerlendirilir:
- **Halüsinasyon Hata Dağılımı (`halusinasyon_turleri`):** Modelin en çok hangi aşamada çuvalladığını gösterir (`uydurma_dosya`, `uydurma_satir`, `uyusmayan_kanit`, `uydurma_paket`). Bu dağılım, modelin context window kapasitesi, prompt kalitesi veya RAG retrieval başarımı hakkında doğrudan mühendislik geri bildirimi sağlar.
- **Rapor Güvenilirlik Kapısı (`rapor_karari`):** Bir güvenlik raporunda halüsinasyon oranı önceden belirlenen güvenlik eşiğini aşarsa (`halusinasyon_orani > max_halusinasyon_orani`) veya raporda doğrulanmış tek bir geçerli bulgu dahi yoksa, rapor bütünüyle `"guvenilmez_model_raporu"` olarak işaretlenir ve otomatik CI/CD ardışık düzeni tarafından reddedilir.

### 3. Saldırgan Neyi Dener? (Threat Vectors)
- **Paket Halüsinasyonu İstismarı (Slopsquatting / Package Hallucination):** LLM'lerin popüler güvenlik açıklarını kapatmak için sıkça önerdiği ancak kamu depolarında (PyPI, npm, RubyGems) henüz tescil edilmemiş paket adlarını saldırganlar takip eder. Saldırgan bu hayali paket adlarını kamu kayıt defterinde kendi adına tescil edip içine zararlı yük (reverse shell, credential harvester) yerleştirir. Geliştirici modelin önerisine güvenip paketi yüklediğinde tedarik zinciri saldırısı gerçekleşmiş olur.
- **Alarm Yorgunluğu (Alert Fatigue) ile Boğma:** Saldırgan, kod tabanına veya LLM prompt girdilerine enjekte ettiği yanıltıcı yorum satırlarıyla modelin yüzlerce uydurma güvenlik uyarısı üretmesini sağlayabilir. Triyaj mühendisleri sahte pozitifler arasında boğulurken gerçek güvenlik açıkları gözden kaçar.

### 4. Savunma Neden Kırılır ve Sık Yapılan Geliştirici Tuzakları
- **İndeksleme Uyuşmazlığı (1-Tabanlı vs 0-Tabanlı):** Model `satir_no = 2` raporladığında, Python listesindeki karşılığı `satirlar[1]`'dir. Geliştiricinin `satirlar[satir_no]` yazması durumunda hem `IndexError` riski doğar hem de kanıt yanlış satırda aranır.
- **Python'da Boolean Tip Sızıntısı:** Python'da `bool` sınıfı `int` sınıfının alt sınıfıdır (`isinstance(True, int) == True`). Katı tip denetimi yapılmazsa `satir_no = True` değeri `satir_no = 1` olarak işleme alınır ve hatalı onay verilir.
- **Sessizce Girdiyi Değiştirme (Mutation):** Doğrulama işlevinin girdi sözlüklerini yerinde değiştirmesi veya referansları bozması diğer denetim araçlarında yan etkilere yol açar.
- **Açık Dünya Varsayımı (Open-World Assumption):** Modelin önerdiği her harici paketi internetten indirmeye kalkışmak, yukarıda bahsedilen slopsquatting saldırılarına kapı aralar. Yalnızca kapalı izin listesinde (`bilinen_paketler`) yer alan paketler doğrulanmış sayılmalıdır.

| Gerçek araç / model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Yerel Ollama modelinin (`qwen3` vb.) kaynak kod hakkındaki bulgu iddialarını ve gerçek dosya satırlarıyla yapılan deterministik çapraz doğrulamayı | İlk üç görevde `kaynak_dosyalar.json`, `model_bulgu_iddialari.jsonl` ve `triyaj_adaylari.json` sentetik verilerini; son görevde canlı `ai_lab.SohbetOturumu` ile kanıt eşleştirme deneyini | Kanıt satırı dosyada gerçekten var olan (`dogrulandi`) bir iddianın çalışma zamanında kesinlikle sömürülebilir (exploitable) olduğunu söyleyemez; yalnızca modelin iddia ettiği satır ve kodun fiziksel olarak var olduğunu kanıtlar |
| SAST / LLM çıktılarındaki paket önerilerinin taranması ve hayali bağımlılıkların (slopsquatting) tespiti | Proje bazlı `bilinen_paketler` izin listesi kontrolü | Bir paketin izin listesinde olması, o paketin sürümünde henüz keşfedilmemiş sıfır-gün (zero-day) açığı bulunmadığını garanti etmez |
| Güvenlik CI/CD kapısında model raporu güvenilirlik eşiği (`max_halusinasyon_orani`) ve otomatik triyaj filtrelemesi | `kanitli_bulgu_suzgeci` ile doğrulanmış bulguların ayrıştırılması ve rapor kararının (`onaylandi` / `guvenilmez_model_raporu`) üretilmesi | Raporun onaylanması kod tabanında başka hiçbir güvenlik açığı kalmadığını kanıtlamaz; yalnızca eldeki model raporunun güvenilirlik sınırları içinde olduğunu gösterir |

> [!NOT]
> **Kapsam ve dürüstlük sınırı:** İlk üç görevdeki örnek dosyalar **sentetik** eğitim verisidir ve her çalıştırmada (`setup`) çalışma klasörüne yeniden kopyalanır (kalıcılık yoktur). Doğrulayıcı yalnızca yerel bellek/dosya haritasına bakar; dış paket depolarına sorgu atmaz. Dördüncü görevde yerel Ollama modeliyle canlı kod analizi ve kanıt çapraz doğrulaması yapılır.
:::

::: anlat Model iddiası dört katmanlı kanıt merdiveninden geçmeden bulgu sayılmaz
Modelin ürettiği her güvenlik iddiası sırasıyla dört deterministik kontrolden geçer:

1. **Dosya Varlığı (`uydurma_dosya`):** İddia edilen `dosya_adi` proje kaynak haritasında (`kaynak_haritasi["dosyalar"]`) mevcut mu?
2. **Satır Sınırı (`uydurma_satir`):** 1-tabanlı `satir_no` değeri dosyanın toplam satır sayısını (`len(dosyalar[dosya_adi])`) aşıyor mu?
3. **Kanıt Alt Dizgesi (`uyusmayan_kanit`):** Modelin kanıt olarak gösterdiği `kanit_alt_dizgesi` gerçekten ilgili satırın (`dosyalar[dosya_adi][satir_no - 1]`) içinde geçiyor mu?
4. **Paket Doğrulaması (`uydurma_paket`):** Modelin çözüm için önerdiği `onerilen_paket`, projenin `bilinen_paketler` izin listesinde yer alıyor mu?
:::

::: anlat Bulguyu sınırlı ve doğrulanabilir yaz: halüsinasyon oranını yalnız reddedilenlerle değil, kök neden dağılımıyla raporla
Bir modelin güvenlik analizi kalitesini ölçerken yalnızca toplam `halusinasyon_orani` yetmez; hataların `halusinasyon_turleri` dağılımı (`uydurma_satir`, `uyusmayan_kanit`, `uydurma_paket`) da çıkarılmalıdır. Ayrıca bir analiz oturumunda `halusinasyon_orani > max_halusinasyon_orani` ise veya hiç doğrulanmış bulgu yoksa tüm rapor `"guvenilmez_model_raporu"` olarak işaretlenmelidir.
:::

::: tahmin 1-tabanlı satır numarası ile 0-tabanlı Python dizini eşleştirmesini tahmin et
Aşağıdaki Python kodunun çıktısını tahmin et:

```python
satirlar = ["import sqlite3", "def giris(k):", "    return k"]
iddia_satir_no = 2
kanit = "def giris"

gecerli = iddia_satir_no <= len(satirlar) and kanit in satirlar[iddia_satir_no - 1]
print(gecerli, satirlar[iddia_satir_no - 1])
```

???

```cikti
True def giris(k):
```

Araçlar ve modeller satır numaralarını `1`'den başlatarak raporlar (`iddia_satir_no = 2`), Python listeleri ise `0`-tabanlıdır (`satirlar[2 - 1] == "def giris(k):"`).
:::

::: gorev 1 · Tekil model iddiasını kaynak dosya satırıyla ve paket listesiyle eşleştir
`kanit_satiri_eslestir(iddia, kaynak_haritasi)` işlevini yaz.

Girdi kuralları:
- `iddia`: tam olarak `{"iddia_id", "dosya_adi", "satir_no", "kanit_alt_dizgesi", "onerilen_paket"}` anahtarlarını taşıyan `dict`.
  - `iddia_id`, `dosya_adi`, `kanit_alt_dizgesi`, `onerilen_paket`: boş olmayan (`strip()` sonrası dolu) `str`.
  - `satir_no`: `bool` olmayan pozitif (`1` veya daha büyük) `int`.
- `kaynak_haritasi`: tam olarak `{"dosyalar", "bilinen_paketler"}` anahtarlarını taşıyan `dict`.
  - `dosyalar`: boş olmayan `dict`; her anahtar boş olmayan `str`, her değer boş olmayan `str` listesi.
  - `bilinen_paketler`: her öğesi boş olmayan `str` olan boş olmayan `list`.
- Geçersiz şema veya değerde `ValueError` yükselt.

Eşleştirme sırası (ilk takılan kural durumu belirler):
1. `dosya_adi not in kaynak_haritasi["dosyalar"]` -> `"uydurma_dosya"`
2. `satir_no > len(kaynak_haritasi["dosyalar"][dosya_adi])` -> `"uydurma_satir"`
3. `kanit_alt_dizgesi not in kaynak_haritasi["dosyalar"][dosya_adi][satir_no - 1]` -> `"uyusmayan_kanit"`
4. `onerilen_paket not in kaynak_haritasi["bilinen_paketler"]` -> `"uydurma_paket"`
5. Yukarıdakilerin hepsi geçerse -> `"dogrulandi"`

Döndürülecek sözlük:
`{"iddia_id": iddia["iddia_id"], "durum": durum, "gecerli": durum == "dogrulandi"}`

```starter
import json
from ai_ile_guvenlik_veri import json_yukle, metin_yukle

kaynak = json_yukle("kaynak_dosyalar.json")
satirlar = metin_yukle("model_bulgu_iddialari.jsonl").splitlines()

def kanit_satiri_eslestir(iddia, kaynak_haritasi):
    # KUSURLU BAŞLANGIÇ KODU: satır sınırını, kanıt alt dizgesini ve paket listesini kontrol etmeden yalnızca dosya varlığına bakıyor!
    var = iddia["dosya_adi"] in kaynak_haritasi["dosyalar"]
    return {
        "iddia_id": iddia["iddia_id"],
        "durum": "dogrulandi" if var else "uydurma_dosya",
        "gecerli": var,
    }

for s in satirlar:
    if s.strip():
        print(kanit_satiri_eslestir(json.loads(s), kaynak))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-02")
```

```test
need("kanit_satiri_eslestir")

KAYNAK = {
    "dosyalar": {
        "app.py": ["import os", "x = eval(girdi)"],
    },
    "bilinen_paketler": ["os", "json"],
}

BAZ_IDDIA = {
    "iddia_id": "i-1",
    "dosya_adi": "app.py",
    "satir_no": 2,
    "kanit_alt_dizgesi": "eval(girdi)",
    "onerilen_paket": "json",
}

def sozlesme(fn):
    try:
        if fn(dict(BAZ_IDDIA), KAYNAK) != {"iddia_id": "i-1", "durum": "dogrulandi", "gecerli": True}:
            return False
        if fn(dict(BAZ_IDDIA, satir_no=1, kanit_alt_dizgesi="import os"), KAYNAK)["durum"] != "dogrulandi":
            return False
        if fn(dict(BAZ_IDDIA, dosya_adi="yok.py"), KAYNAK) != {"iddia_id": "i-1", "durum": "uydurma_dosya", "gecerli": False}:
            return False
        if fn(dict(BAZ_IDDIA, satir_no=3), KAYNAK) != {"iddia_id": "i-1", "durum": "uydurma_satir", "gecerli": False}:
            return False
        if fn(dict(BAZ_IDDIA, kanit_alt_dizgesi="system("), KAYNAK) != {"iddia_id": "i-1", "durum": "uyusmayan_kanit", "gecerli": False}:
            return False
        if fn(dict(BAZ_IDDIA, onerilen_paket="hayali-pkg"), KAYNAK) != {"iddia_id": "i-1", "durum": "uydurma_paket", "gecerli": False}:
            return False

        hatalilar = [
            (None, KAYNAK),
            ({}, KAYNAK),
            (dict(BAZ_IDDIA, ek=1), KAYNAK),
            (dict(BAZ_IDDIA, iddia_id=" "), KAYNAK),
            (dict(BAZ_IDDIA, iddia_id=1), KAYNAK),
            (dict(BAZ_IDDIA, dosya_adi=" "), KAYNAK),
            (dict(BAZ_IDDIA, dosya_adi=1), KAYNAK),
            (dict(BAZ_IDDIA, kanit_alt_dizgesi=" "), KAYNAK),
            (dict(BAZ_IDDIA, kanit_alt_dizgesi=1), KAYNAK),
            (dict(BAZ_IDDIA, onerilen_paket=" "), KAYNAK),
            (dict(BAZ_IDDIA, onerilen_paket=1), KAYNAK),
            (dict(BAZ_IDDIA, satir_no=0), KAYNAK),
            (dict(BAZ_IDDIA, satir_no=True), KAYNAK),
            (dict(BAZ_IDDIA, satir_no="2"), KAYNAK),
            (BAZ_IDDIA, None),
            (BAZ_IDDIA, {}),
            (BAZ_IDDIA, {"dosyalar": 123, "bilinen_paketler": ["os"]}),
            (BAZ_IDDIA, {"dosyalar": {}, "bilinen_paketler": ["os"]}),
            (BAZ_IDDIA, {"dosyalar": {1: ["a"]}, "bilinen_paketler": ["os"]}),
            (BAZ_IDDIA, {"dosyalar": {"a.py": 123}, "bilinen_paketler": ["os"]}),
            (BAZ_IDDIA, {"dosyalar": {"a.py": ["x"]}, "bilinen_paketler": 123}),
            (BAZ_IDDIA, {"dosyalar": {"a.py": ["x"]}, "bilinen_paketler": [1]}),
            (BAZ_IDDIA, {"dosyalar": {" ": ["a"]}, "bilinen_paketler": ["os"]}),
            (BAZ_IDDIA, {"dosyalar": {"a.py": []}, "bilinen_paketler": ["os"]}),
            (BAZ_IDDIA, {"dosyalar": {"a.py": [123]}, "bilinen_paketler": ["os"]}),
            (BAZ_IDDIA, {"dosyalar": {"a.py": ["x"]}, "bilinen_paketler": []}),
            (BAZ_IDDIA, {"dosyalar": {"a.py": ["x"]}, "bilinen_paketler": [" "]}),
        ]
        for i_in, k_in in hatalilar:
            try:
                fn(i_in, k_in)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(kanit_satiri_eslestir), "tekil model iddiası dört kanıt kuralıyla doğru eşleştirilmeli")
def m_paket_atlayan(i, k):
    r = kanit_satiri_eslestir(i, k)
    return {"iddia_id": r["iddia_id"], "durum": "dogrulandi", "gecerli": True} if r["durum"] == "uydurma_paket" else r
def m_satir_kaydiran(i, k):
    return kanit_satiri_eslestir(dict(i, satir_no=i["satir_no"] + 1), k)
for ad, mutant in [("uydurma paketi doğrulayan", m_paket_atlayan), ("satır dizinini kaydıran", m_satir_kaydiran)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
ZORUNLU_IDDIA_ALANLARI = ("iddia_id", "dosya_adi", "satir_no", "kanit_alt_dizgesi", "onerilen_paket")

def _dogrula_kaynak_haritasi(kaynak_haritasi):
    if not isinstance(kaynak_haritasi, dict):
        raise ValueError("kaynak haritası sözlük olmalı")
    if set(kaynak_haritasi.keys()) != {"dosyalar", "bilinen_paketler"}:
        raise ValueError("kaynak haritası şeması geçersiz")
    dosyalar = kaynak_haritasi["dosyalar"]
    paketler = kaynak_haritasi["bilinen_paketler"]
    if not isinstance(dosyalar, dict) or not dosyalar:
        raise ValueError("dosyalar boş olmayan sözlük olmalı")
    for ad, satirlar in dosyalar.items():
        if not isinstance(ad, str) or not ad.strip():
            raise ValueError("dosya adı geçersiz")
        if not isinstance(satirlar, list) or not satirlar:
            raise ValueError("dosya satırları boş olmayan liste olmalı")
        for s in satirlar:
            if not isinstance(s, str):
                raise ValueError("her satır string olmalı")
    if not isinstance(paketler, list) or not paketler:
        raise ValueError("bilinen paketler boş olmayan liste olmalı")
    for p in paketler:
        if not isinstance(p, str) or not p.strip():
            raise ValueError("paket adı geçersiz")

def kanit_satiri_eslestir(iddia, kaynak_haritasi):
    if not isinstance(iddia, dict) or set(iddia.keys()) != set(ZORUNLU_IDDIA_ALANLARI):
        raise ValueError("iddia şeması geçersiz")
    for alan in ("iddia_id", "dosya_adi", "kanit_alt_dizgesi", "onerilen_paket"):
        if not isinstance(iddia[alan], str) or not iddia[alan].strip():
            raise ValueError("metin alanı boş olamaz")
    satir_no = iddia["satir_no"]
    if isinstance(satir_no, bool) or not isinstance(satir_no, int) or satir_no < 1:
        raise ValueError("satır numarası pozitif tam sayı olmalı")
    _dogrula_kaynak_haritasi(kaynak_haritasi)

    dosyalar = kaynak_haritasi["dosyalar"]
    paketler = kaynak_haritasi["bilinen_paketler"]
    dosya_adi = iddia["dosya_adi"]

    if dosya_adi not in dosyalar:
        durum = "uydurma_dosya"
    elif satir_no > len(dosyalar[dosya_adi]):
        durum = "uydurma_satir"
    elif iddia["kanit_alt_dizgesi"] not in dosyalar[dosya_adi][satir_no - 1]:
        durum = "uyusmayan_kanit"
    elif iddia["onerilen_paket"] not in paketler:
        durum = "uydurma_paket"
    else:
        durum = "dogrulandi"

    return {
        "iddia_id": iddia["iddia_id"],
        "durum": durum,
        "gecerli": durum == "dogrulandi",
    }
```

```hint
1-tabanlı `satir_no` değerini Python listesinde okurken `dosyalar[dosya_adi][satir_no - 1]` indeksini kullan.
```
:::

::: gorev 2 · Çoklu model iddiasında halüsinasyon oranını ve hata dağılımını hesapla
`halusinasyon_orani_hesapla(iddia_listesi, kaynak_haritasi)` işlevini yaz.

Girdi kuralları:
- `iddia_listesi`: boş olmayan `list`; her öğesi 1. görevdeki `iddia` şemasına uymalı ve `iddia_id` değerleri benzersiz olmalıdır.
- `kaynak_haritasi`: 1. görevdeki `kaynak_haritasi` şemasına uymalıdır.
- Geçersiz girdi veya tekrar eden `iddia_id` durumunda `ValueError` yükselt.

Hesaplama kuralları:
- Her iddiayı 1. görevdeki kurallarla değerlendir:
  - `gecerli == True` olanların kimliğini `dogrulanan_idleri` listesine ekle (`sorted`).
  - `gecerli == False` olanların `durum` değerini `halusinasyon_turleri` sözlüğünde say (anahtarlara göre alfabetik sıralı `dict`).
- `halusinasyon_orani`: `round((len(iddia_listesi) - len(dogrulanan_idleri)) / len(iddia_listesi), 4)`.

```starter
import json
from ai_ile_guvenlik_veri import json_yukle, metin_yukle

kaynak = json_yukle("kaynak_dosyalar.json")
iddialar = [json.loads(s) for s in metin_yukle("model_bulgu_iddialari.jsonl").splitlines() if s.strip()]

def halusinasyon_orani_hesapla(iddia_listesi, kaynak_haritasi):
    # KUSURLU BAŞLANGIÇ KODU: tüm iddiaları doğrulanmış sayıyor, halüsinasyon türlerini toplamıyor ve oranı sabit 0.0 döndürüyor!
    return {
        "dogrulanan_idleri": [i["iddia_id"] for i in iddia_listesi],
        "halusinasyon_turleri": {},
        "halusinasyon_orani": 0.0,
    }

print(halusinasyon_orani_hesapla(iddialar, kaynak))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-02")
```

```test
need("halusinasyon_orani_hesapla")

KAYNAK = {
    "dosyalar": {
        "s.py": ["import json", "q = 'SELECT ' + u"],
    },
    "bilinen_paketler": ["json", "sqlite3"],
}

IDDIALAR = [
    {"iddia_id": "id-2", "dosya_adi": "s.py", "satir_no": 2, "kanit_alt_dizgesi": "SELECT ", "onerilen_paket": "sqlite3"},
    {"iddia_id": "id-1", "dosya_adi": "s.py", "satir_no": 1, "kanit_alt_dizgesi": "import json", "onerilen_paket": "json"},
    {"iddia_id": "id-3", "dosya_adi": "yok.py", "satir_no": 1, "kanit_alt_dizgesi": "import", "onerilen_paket": "json"},
    {"iddia_id": "id-4", "dosya_adi": "s.py", "satir_no": 9, "kanit_alt_dizgesi": "SELECT", "onerilen_paket": "json"},
    {"iddia_id": "id-5", "dosya_adi": "s.py", "satir_no": 2, "kanit_alt_dizgesi": "eval(", "onerilen_paket": "json"},
    {"iddia_id": "id-6", "dosya_adi": "s.py", "satir_no": 2, "kanit_alt_dizgesi": "SELECT ", "onerilen_paket": "sahte-pkg"},
]

def sozlesme(fn):
    try:
        r = fn(IDDIALAR, KAYNAK)
        if r != {
            "dogrulanan_idleri": ["id-1", "id-2"],
            "halusinasyon_turleri": {
                "uydurma_dosya": 1,
                "uydurma_paket": 1,
                "uydurma_satir": 1,
                "uyusmayan_kanit": 1,
            },
            "halusinasyon_orani": 0.6667,
        }:
            return False

        r_iki_ayni_tur = fn([IDDIALAR[2], dict(IDDIALAR[2], iddia_id="id-9")], KAYNAK)
        if r_iki_ayni_tur["halusinasyon_turleri"] != {"uydurma_dosya": 2} or r_iki_ayni_tur["halusinasyon_orani"] != 1.0:
            return False

        i0 = IDDIALAR[0]
        hatalilar = [
            (None, KAYNAK),
            (123, KAYNAK),
            ([], KAYNAK),
            ([i0], {"dosyalar": 123, "bilinen_paketler": ["json"]}),
            ([i0], {"dosyalar": {"a.py": 123}, "bilinen_paketler": ["json"]}),
            ([i0], {"dosyalar": {"a.py": ["x"]}, "bilinen_paketler": 123}),
            ("liste", KAYNAK),
            (["sozluk_degil"], KAYNAK),
            ([{"iddia_id": "x"}], KAYNAK),
            ([i0, i0], KAYNAK),
            ([dict(i0, satir_no=0)], KAYNAK),
            ([dict(i0, satir_no=True)], KAYNAK),
            ([dict(i0, satir_no="2")], KAYNAK),
            ([dict(i0, iddia_id=" ")], KAYNAK),
            ([dict(i0, iddia_id=1)], KAYNAK),
            ([dict(i0, dosya_adi=" ")], KAYNAK),
            ([dict(i0, dosya_adi=1)], KAYNAK),
            ([dict(i0, kanit_alt_dizgesi=" ")], KAYNAK),
            ([dict(i0, kanit_alt_dizgesi=1)], KAYNAK),
            ([dict(i0, onerilen_paket=" ")], KAYNAK),
            ([dict(i0, onerilen_paket=1)], KAYNAK),
            ([i0], None),
            ([i0], {}),
            ([i0], {"dosyalar": {}, "bilinen_paketler": ["json"]}),
            ([i0], {"dosyalar": {" ": ["a"]}, "bilinen_paketler": ["json"]}),
            ([i0], {"dosyalar": {1: ["a"]}, "bilinen_paketler": ["json"]}),
            ([i0], {"dosyalar": {"a.py": []}, "bilinen_paketler": ["json"]}),
            ([i0], {"dosyalar": {"a.py": "satir"}, "bilinen_paketler": ["json"]}),
            ([i0], {"dosyalar": {"a.py": [123]}, "bilinen_paketler": ["json"]}),
            ([i0], {"dosyalar": {"a.py": ["x"]}, "bilinen_paketler": []}),
            ([i0], {"dosyalar": {"a.py": ["x"]}, "bilinen_paketler": "json"}),
            ([i0], {"dosyalar": {"a.py": ["x"]}, "bilinen_paketler": [" "]}),
            ([i0], {"dosyalar": {"a.py": ["x"]}, "bilinen_paketler": [1]}),
        ]
        for l_in, k_in in hatalilar:
            try:
                fn(l_in, k_in)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(halusinasyon_orani_hesapla), "halüsinasyon oranı ve hata türleri dağılımı doğru hesaplanmalı")
def m_oran_sifir(l, k):
    return dict(halusinasyon_orani_hesapla(l, k), halusinasyon_orani=0.0)
def m_turler_bos(l, k):
    return dict(halusinasyon_orani_hesapla(l, k), halusinasyon_turleri={})
for ad, mutant in [("halüsinasyon oranını sıfırlayan", m_oran_sifir), ("hata türlerini boş bırakan", m_turler_bos)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
ZORUNLU_IDDIA_ALANLARI = ("iddia_id", "dosya_adi", "satir_no", "kanit_alt_dizgesi", "onerilen_paket")

def _dogrula_kaynak_haritasi(kaynak_haritasi):
    if not isinstance(kaynak_haritasi, dict) or set(kaynak_haritasi.keys()) != {"dosyalar", "bilinen_paketler"}:
        raise ValueError("kaynak haritası şeması geçersiz")
    dosyalar = kaynak_haritasi["dosyalar"]
    paketler = kaynak_haritasi["bilinen_paketler"]
    if not isinstance(dosyalar, dict) or not dosyalar:
        raise ValueError("dosyalar boş olmayan sözlük olmalı")
    for ad, satirlar in dosyalar.items():
        if not isinstance(ad, str) or not ad.strip() or not isinstance(satirlar, list) or not satirlar:
            raise ValueError("dosya tanımı geçersiz")
        for s in satirlar:
            if not isinstance(s, str):
                raise ValueError("her satır string olmalı")
    if not isinstance(paketler, list) or not paketler:
        raise ValueError("bilinen paketler boş olmayan liste olmalı")
    for p in paketler:
        if not isinstance(p, str) or not p.strip():
            raise ValueError("paket adı geçersiz")

def _tekil_eslestir(iddia, kaynak_haritasi):
    if not isinstance(iddia, dict) or set(iddia.keys()) != set(ZORUNLU_IDDIA_ALANLARI):
        raise ValueError("iddia şeması geçersiz")
    for alan in ("iddia_id", "dosya_adi", "kanit_alt_dizgesi", "onerilen_paket"):
        if not isinstance(iddia[alan], str) or not iddia[alan].strip():
            raise ValueError("metin alanı boş olamaz")
    satir_no = iddia["satir_no"]
    if isinstance(satir_no, bool) or not isinstance(satir_no, int) or satir_no < 1:
        raise ValueError("satır numarası pozitif tam sayı olmalı")

    dosyalar = kaynak_haritasi["dosyalar"]
    paketler = kaynak_haritasi["bilinen_paketler"]
    dosya_adi = iddia["dosya_adi"]
    if dosya_adi not in dosyalar:
        durum = "uydurma_dosya"
    elif satir_no > len(dosyalar[dosya_adi]):
        durum = "uydurma_satir"
    elif iddia["kanit_alt_dizgesi"] not in dosyalar[dosya_adi][satir_no - 1]:
        durum = "uyusmayan_kanit"
    elif iddia["onerilen_paket"] not in paketler:
        durum = "uydurma_paket"
    else:
        durum = "dogrulandi"
    return iddia["iddia_id"], durum

def halusinasyon_orani_hesapla(iddia_listesi, kaynak_haritasi):
    if not isinstance(iddia_listesi, list) or not iddia_listesi:
        raise ValueError("iddia listesi boş olamaz")
    _dogrula_kaynak_haritasi(kaynak_haritasi)
    gorulen = set()
    dogrulanan_idleri = []
    halusinasyon_turleri = {}

    for i in iddia_listesi:
        iid, durum = _tekil_eslestir(i, kaynak_haritasi)
        if iid in gorulen:
            raise ValueError("tekrar eden iddia kimliği")
        gorulen.add(iid)
        if durum == "dogrulandi":
            dogrulanan_idleri.append(iid)
        else:
            halusinasyon_turleri[durum] = halusinasyon_turleri.get(durum, 0) + 1

    toplam = len(iddia_listesi)
    halusinasyon_sayisi = toplam - len(dogrulanan_idleri)
    oran = round(halusinasyon_sayisi / toplam, 4)
    return {
        "dogrulanan_idleri": sorted(dogrulanan_idleri),
        "halusinasyon_turleri": dict(sorted(halusinasyon_turleri.items())),
        "halusinasyon_orani": oran,
    }
```

```hint
`halusinasyon_sayisi = len(iddia_listesi) - len(dogrulanan_idleri)` değerini toplam iddia sayısına bölüp `round(..., 4)` uygula.
```
:::

::: gorev 3 · Kanıtlı bulgu süzgeci ve model raporu güvenilirlik kapısı yaz
`kanitli_bulgu_suzgeci(iddia_listesi, kaynak_haritasi, max_halusinasyon_orani=0.35)` işlevini yaz.

Girdi kuralları:
- `iddia_listesi` ve `kaynak_haritasi`: 2. görevdeki kurallarla aynıdır.
- `max_halusinasyon_orani`: `bool` olmayan, `0.0` ile `1.0` (dahil) arasında `int` veya `float`.
- Geçersiz girdi veya eşikte `ValueError` yükselt.

Süzgeç kuralları:
- `kabul_edilen_bulgular`: doğrulanmış iddiaların kimlik listesi (`sorted`).
- `elenen_idleri`: halüsinasyon olduğu için elenen iddiaların kimlik listesi (`sorted`).
- `halusinasyon_orani`: 2. görevdekiyle aynı (`4` ondalık yuvarlanmış).
- `rapor_karari`: `halusinasyon_orani <= max_halusinasyon_orani` **ve** `len(kabul_edilen_bulgular) >= 1` ise `"onaylandi"`, aksi hâlde `"guvenilmez_model_raporu"`.

```starter
from ai_ile_guvenlik_veri import json_yukle

kaynak = json_yukle("kaynak_dosyalar.json")
triyaj = json_yukle("triyaj_adaylari.json")

def kanitli_bulgu_suzgeci(iddia_listesi, kaynak_haritasi, max_halusinasyon_orani=0.35):
    # KUSURLU BAŞLANGIÇ KODU: halüsinasyonlu iddiaları elemiyor, eşik kontrolü yapmıyor ve her zaman 'onaylandi' döndürüyor!
    return {
        "kabul_edilen_bulgular": [i["iddia_id"] for i in iddia_listesi],
        "elenen_idleri": [],
        "halusinasyon_orani": 0.0,
        "rapor_karari": "onaylandi",
    }

print(kanitli_bulgu_suzgeci(triyaj["iddialar"], kaynak, triyaj["max_halusinasyon_orani"]))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-02")
```

```test
need("kanitli_bulgu_suzgeci")

KAYNAK = {
    "dosyalar": {
        "s.py": ["import json", "q = 'SELECT ' + u"],
    },
    "bilinen_paketler": ["json", "sqlite3"],
}

DOGRU_1 = {"iddia_id": "d-1", "dosya_adi": "s.py", "satir_no": 1, "kanit_alt_dizgesi": "import json", "onerilen_paket": "json"}
DOGRU_2 = {"iddia_id": "d-2", "dosya_adi": "s.py", "satir_no": 2, "kanit_alt_dizgesi": "SELECT ", "onerilen_paket": "sqlite3"}
YANLIS_1 = {"iddia_id": "y-1", "dosya_adi": "s.py", "satir_no": 99, "kanit_alt_dizgesi": "SELECT", "onerilen_paket": "json"}

def sozlesme(fn):
    try:
        r_onay = fn([DOGRU_2, DOGRU_1, YANLIS_1], KAYNAK)
        if r_onay != {
            "kabul_edilen_bulgular": ["d-1", "d-2"],
            "elenen_idleri": ["y-1"],
            "halusinasyon_orani": 0.3333,
            "rapor_karari": "onaylandi",
        }:
            return False

        r_sinir = fn([DOGRU_1, YANLIS_1], KAYNAK, 0.5)
        if r_sinir["rapor_karari"] != "onaylandi" or r_sinir["halusinasyon_orani"] != 0.5:
            return False

        r_red = fn([DOGRU_1, YANLIS_1], KAYNAK, 0.35)
        if r_red["rapor_karari"] != "guvenilmez_model_raporu":
            return False

        r_hepsi_yanlis = fn([YANLIS_1], KAYNAK, 1.0)
        if r_hepsi_yanlis["rapor_karari"] != "guvenilmez_model_raporu":
            return False

        if fn([DOGRU_1], KAYNAK, 0.0)["rapor_karari"] != "onaylandi":
            return False
        if fn([DOGRU_1, YANLIS_1], KAYNAK)["rapor_karari"] != "guvenilmez_model_raporu":
            return False
        r_dort = fn([
            DOGRU_1,
            dict(DOGRU_1, iddia_id="yd", dosya_adi="yok.py"),
            dict(DOGRU_1, iddia_id="yk", kanit_alt_dizgesi="eval("),
            dict(DOGRU_1, iddia_id="yp", onerilen_paket="sahte"),
        ], KAYNAK, 1.0)
        if r_dort["elenen_idleri"] != ["yd", "yk", "yp"]:
            return False

        hatalilar = [
            (None, KAYNAK, 0.35),
            (123, KAYNAK, 0.35),
            ([], KAYNAK, 0.35),
            ([DOGRU_1], {"dosyalar": 123, "bilinen_paketler": ["json"]}, 0.35),
            ([DOGRU_1], {"dosyalar": {"a.py": 123}, "bilinen_paketler": ["json"]}, 0.35),
            ([DOGRU_1], {"dosyalar": {"a.py": ["x"]}, "bilinen_paketler": 123}, 0.35),
            ("liste", KAYNAK, 0.35),
            (["sozluk_degil"], KAYNAK, 0.35),
            ([{"iddia_id": "x"}], KAYNAK, 0.35),
            ([DOGRU_1, DOGRU_1], KAYNAK, 0.35),
            ([dict(DOGRU_1, satir_no=0)], KAYNAK, 0.35),
            ([dict(DOGRU_1, satir_no=True)], KAYNAK, 0.35),
            ([dict(DOGRU_1, satir_no="1")], KAYNAK, 0.35),
            ([dict(DOGRU_1, iddia_id=" ")], KAYNAK, 0.35),
            ([dict(DOGRU_1, iddia_id=1)], KAYNAK, 0.35),
            ([dict(DOGRU_1, dosya_adi=" ")], KAYNAK, 0.35),
            ([dict(DOGRU_1, dosya_adi=1)], KAYNAK, 0.35),
            ([dict(DOGRU_1, kanit_alt_dizgesi=" ")], KAYNAK, 0.35),
            ([dict(DOGRU_1, kanit_alt_dizgesi=1)], KAYNAK, 0.35),
            ([dict(DOGRU_1, onerilen_paket=" ")], KAYNAK, 0.35),
            ([dict(DOGRU_1, onerilen_paket=1)], KAYNAK, 0.35),
            ([DOGRU_1], None, 0.35),
            ([DOGRU_1], {}, 0.35),
            ([DOGRU_1], {"dosyalar": {}, "bilinen_paketler": ["json"]}, 0.35),
            ([DOGRU_1], {"dosyalar": {" ": ["a"]}, "bilinen_paketler": ["json"]}, 0.35),
            ([DOGRU_1], {"dosyalar": {1: ["a"]}, "bilinen_paketler": ["json"]}, 0.35),
            ([DOGRU_1], {"dosyalar": {"a.py": []}, "bilinen_paketler": ["json"]}, 0.35),
            ([DOGRU_1], {"dosyalar": {"a.py": "satir"}, "bilinen_paketler": ["json"]}, 0.35),
            ([DOGRU_1], {"dosyalar": {"a.py": [123]}, "bilinen_paketler": ["json"]}, 0.35),
            ([DOGRU_1], {"dosyalar": {"a.py": ["x"]}, "bilinen_paketler": []}, 0.35),
            ([DOGRU_1], {"dosyalar": {"a.py": ["x"]}, "bilinen_paketler": "json"}, 0.35),
            ([DOGRU_1], {"dosyalar": {"a.py": ["x"]}, "bilinen_paketler": [" "]}, 0.35),
            ([DOGRU_1], {"dosyalar": {"a.py": ["x"]}, "bilinen_paketler": [1]}, 0.35),
            ([DOGRU_1], KAYNAK, float("nan")),
            ([DOGRU_1], KAYNAK, float("inf")),
            ([DOGRU_1], KAYNAK, -0.1),
            ([DOGRU_1], KAYNAK, 1.1),
            ([DOGRU_1], KAYNAK, True),
            ([DOGRU_1], KAYNAK, "0.35"),
        ]
        for l_in, k_in, m_in in hatalilar:
            try:
                fn(l_in, k_in, m_in)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(kanitli_bulgu_suzgeci), "kanıtlı bulgu süzgeci halüsinasyonları elemeli ve eşik kararını doğru vermeli")
def m_hep_onayla(l, k, m=0.35):
    return dict(kanitli_bulgu_suzgeci(l, k, m), rapor_karari="onaylandi")
def m_eleme_yok(l, k, m=0.35):
    return dict(kanitli_bulgu_suzgeci(l, k, m), elenen_idleri=[])
for ad, mutant in [("güvenilmez raporu onaylayan", m_hep_onayla), ("elenen iddiaları gizleyen", m_eleme_yok)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
ZORUNLU_IDDIA_ALANLARI = ("iddia_id", "dosya_adi", "satir_no", "kanit_alt_dizgesi", "onerilen_paket")

def _dogrula_kaynak_haritasi(kaynak_haritasi):
    if not isinstance(kaynak_haritasi, dict) or set(kaynak_haritasi.keys()) != {"dosyalar", "bilinen_paketler"}:
        raise ValueError("kaynak haritası şeması geçersiz")
    dosyalar = kaynak_haritasi["dosyalar"]
    paketler = kaynak_haritasi["bilinen_paketler"]
    if not isinstance(dosyalar, dict) or not dosyalar:
        raise ValueError("dosyalar boş olmayan sözlük olmalı")
    for ad, satirlar in dosyalar.items():
        if not isinstance(ad, str) or not ad.strip() or not isinstance(satirlar, list) or not satirlar:
            raise ValueError("dosya tanımı geçersiz")
        for s in satirlar:
            if not isinstance(s, str):
                raise ValueError("her satır string olmalı")
    if not isinstance(paketler, list) or not paketler:
        raise ValueError("bilinen paketler boş olmayan liste olmalı")
    for p in paketler:
        if not isinstance(p, str) or not p.strip():
            raise ValueError("paket adı geçersiz")

def kanitli_bulgu_suzgeci(iddia_listesi, kaynak_haritasi, max_halusinasyon_orani=0.35):
    if not isinstance(iddia_listesi, list) or not iddia_listesi:
        raise ValueError("iddia listesi boş olamaz")
    import math
    if isinstance(max_halusinasyon_orani, bool) or not isinstance(max_halusinasyon_orani, (int, float)) or not math.isfinite(max_halusinasyon_orani):
        raise ValueError("eşik sayısal olmalı")
    if max_halusinasyon_orani < 0 or max_halusinasyon_orani > 1:
        raise ValueError("eşik geçersiz")
    _dogrula_kaynak_haritasi(kaynak_haritasi)

    dosyalar = kaynak_haritasi["dosyalar"]
    paketler = kaynak_haritasi["bilinen_paketler"]
    gorulen = set()
    kabul = []
    elenen = []

    for iddia in iddia_listesi:
        if not isinstance(iddia, dict) or set(iddia.keys()) != set(ZORUNLU_IDDIA_ALANLARI):
            raise ValueError("iddia şeması geçersiz")
        for alan in ("iddia_id", "dosya_adi", "kanit_alt_dizgesi", "onerilen_paket"):
            if not isinstance(iddia[alan], str) or not iddia[alan].strip():
                raise ValueError("metin alanı boş olamaz")
        satir_no = iddia["satir_no"]
        if isinstance(satir_no, bool) or not isinstance(satir_no, int) or satir_no < 1:
            raise ValueError("satır numarası geçersiz")
        iid = iddia["iddia_id"]
        if iid in gorulen:
            raise ValueError("tekrar eden iddia kimliği")
        gorulen.add(iid)

        dosya_adi = iddia["dosya_adi"]
        gecerli = (
            dosya_adi in dosyalar
            and satir_no <= len(dosyalar[dosya_adi])
            and iddia["kanit_alt_dizgesi"] in dosyalar[dosya_adi][satir_no - 1]
            and iddia["onerilen_paket"] in paketler
        )
        if gecerli:
            kabul.append(iid)
        else:
            elenen.append(iid)

    oran = round(len(elenen) / len(iddia_listesi), 4)
    guvenilir = oran <= max_halusinasyon_orani and bool(kabul)
    return {
        "kabul_edilen_bulgular": sorted(kabul),
        "elenen_idleri": sorted(elenen),
        "halusinasyon_orani": oran,
        "rapor_karari": "onaylandi" if guvenilir else "guvenilmez_model_raporu",
    }
```

```hint
`oran <= max_halusinasyon_orani and bool(kabul)` koşulu sağlandığında `"onaylandi"`, aksi hâlde `"guvenilmez_model_raporu"` döndür.
```
:::

::: gorev Gerçek deney · Yerel model bulgu iddialarını kaynak satırlarıyla çapraz doğrulama
Önceki üç görevde yazdığın `kanit_satiri_eslestir`, `halusinasyon_orani_hesapla` ve `kanitli_bulgu_suzgeci` işlevlerini bu adımda birleştir.

Canlı deneyde:
1. Yerel Ollama modeli (`ai_lab.SohbetOturumu`) örnek bir kaynak dosya (`giris_servisi.py`) üzerinde çalıştırılır.
2. Doğru satır/kanıt referansları ile halüsine satır referansı `kanit_satiri_eslestir` ve `halusinasyon_orani_hesapla` ile ölçülür.
3. `kanitli_bulgu_suzgeci` ile uydurma satır iddiası elenerek yalnızca kanıtlı bulguların rapora girdiği doğrulanır.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab

def kanit_satiri_eslestir(iddia, kaynak_haritasi):
    # KUSURLU BAŞLANGIÇ KODU: satır ve paket kontrollerini yapmadan yalnızca dosya kontrolü yapıyor!
    var = iddia.get("dosya_adi") in kaynak_haritasi.get("dosyalar", {}) if isinstance(iddia, dict) and isinstance(kaynak_haritasi, dict) else False
    return {"iddia_id": iddia.get("iddia_id", "") if isinstance(iddia, dict) else "", "durum": "dogrulandi" if var else "uydurma_dosya", "gecerli": var}

def halusinasyon_orani_hesapla(iddia_listesi, kaynak_haritasi):
    # KUSURLU BAŞLANGIÇ KODU: tüm iddiaları doğrulanmış sayıyor ve hata türlerini saymıyor!
    return {"dogrulanan_idleri": [i["iddia_id"] for i in iddia_listesi if isinstance(i, dict)], "halusinasyon_turleri": {}, "halusinasyon_orani": 0.0}

def kanitli_bulgu_suzgeci(iddia_listesi, kaynak_haritasi, max_halusinasyon_orani=0.35):
    # KUSURLU BAŞLANGIÇ KODU: eşik denetimi yapmadan tüm iddiaları onaylıyor!
    return {"kabul_edilen_bulgular": [i["iddia_id"] for i in iddia_listesi if isinstance(i, dict)], "elenen_idleri": [], "halusinasyon_orani": 0.0, "rapor_karari": "onaylandi"}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_ile_guvenlik_02 as deney
    deney.goster(kanit_satiri_eslestir, halusinasyon_orani_hesapla, kanitli_bulgu_suzgeci)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-02")
```

```test
import copy
import ast
import ai_lab
from sandbox import ai_gercek_ai_ile_guvenlik_02 as D

checks = []
_base_ok = ok
def ok(kosul, mesaj):
    checks.append(bool(kosul))
    return _base_ok(kosul, mesaj)

for ad in ("kanit_satiri_eslestir", "halusinasyon_orani_hesapla", "kanitli_bulgu_suzgeci"):
    need(ad)

sorun = ai_lab.kod_denetimi(
    src,
    ("kanit_satiri_eslestir_referans", "halusinasyon_orani_hesapla_referans", "kanitli_bulgu_suzgeci_referans", "kanit_yaz"),
)
ok(not sorun, "laboratuvar yamalanmamalı, referans işlevler çağrılmamalı")
if not all(checks):
    stop()

try:
    _ag_tree = ast.parse(src)
    for _node in ast.walk(_ag_tree):
        if isinstance(_node, ast.ImportFrom):
            for _alias in _node.names:
                if _alias.name == "*":
                    ok(False, "Kopya/güvenlik ihlali: wildcard (*) import yasaktır")
        if isinstance(_node, ast.Name) and "referans" in _node.id.lower():
            ok(False, f"Kopya/güvenlik ihlali: 'referans' kullanımı tespit edildi: {_node.id}")
        if isinstance(_node, ast.Attribute) and "referans" in _node.attr.lower():
            ok(False, f"Kopya/güvenlik ihlali: 'referans' niteliği tespit edildi: {_node.attr}")
        if isinstance(_node, ast.Call) and isinstance(_node.func, ast.Name) and _node.func.id in ("getattr", "eval", "exec"):
            ok(False, f"Kopya/güvenlik ihlali: dinamik fonksiyon çağrısı yasaktır: {_node.func.id}")
except Exception as _e:
    ok(False, f"AST ayrıştırma hatası: {_e}")
if not all(checks):
    stop()

ORNEK_KAYNAK = {"dosyalar": {"a.py": ["x = 1"]}, "bilinen_paketler": ["json"]}
ORNEK_IDDIA = {"iddia_id": "i1", "dosya_adi": "a.py", "satir_no": 1, "kanit_alt_dizgesi": "x = 1", "onerilen_paket": "json"}
ok(kanit_satiri_eslestir(ORNEK_IDDIA, ORNEK_KAYNAK) == D.kanit_satiri_eslestir_referans(ORNEK_IDDIA, ORNEK_KAYNAK), "sentetik ön kontrol: kanıt eşleştirme referansla uyumlu")
def _on_sozlesme():
    try:
        k = {"dosyalar": {"a.py": ["x = 1", "y = 2"]}, "bilinen_paketler": ["json", "os"]}
        d1 = {"iddia_id": "b", "dosya_adi": "a.py", "satir_no": 1, "kanit_alt_dizgesi": "x = 1", "onerilen_paket": "json"}
        d2 = {"iddia_id": "a", "dosya_adi": "a.py", "satir_no": 2, "kanit_alt_dizgesi": "y = 2", "onerilen_paket": "os"}
        u_dosya = dict(d1, iddia_id="u1", dosya_adi="yok.py")
        u_satir = dict(d1, iddia_id="u2", satir_no=3)
        u_kanit = dict(d1, iddia_id="u3", kanit_alt_dizgesi="z = 3")
        u_paket = dict(d1, iddia_id="u4", onerilen_paket="uydurma")
        if kanit_satiri_eslestir(u_dosya, k)["durum"] != "uydurma_dosya": return False
        if kanit_satiri_eslestir(u_satir, k)["durum"] != "uydurma_satir": return False
        if kanit_satiri_eslestir(u_kanit, k)["durum"] != "uyusmayan_kanit": return False
        if kanit_satiri_eslestir(u_paket, k)["durum"] != "uydurma_paket": return False
        oz = halusinasyon_orani_hesapla([d1, d2, u_dosya], k)
        if oz != {"dogrulanan_idleri": ["a", "b"], "halusinasyon_turleri": {"uydurma_dosya": 1}, "halusinasyon_orani": 0.3333}: return False
        if kanitli_bulgu_suzgeci([d1, u_dosya], k, 0.5) != {"kabul_edilen_bulgular": ["b"], "elenen_idleri": ["u1"], "halusinasyon_orani": 0.5, "rapor_karari": "onaylandi"}: return False
        if kanitli_bulgu_suzgeci([d1, u_dosya], k, 0.49)["rapor_karari"] != "guvenilmez_model_raporu": return False
        if kanitli_bulgu_suzgeci([u_dosya], k, 1.0)["rapor_karari"] != "guvenilmez_model_raporu": return False
        if kanitli_bulgu_suzgeci([d1], k, 0.0)["rapor_karari"] != "onaylandi": return False
        if kanitli_bulgu_suzgeci([d1, u_dosya], k)["rapor_karari"] != "guvenilmez_model_raporu": return False
        if kanitli_bulgu_suzgeci([d1, d2, dict(d1, iddia_id="c"), u_dosya], k)["rapor_karari"] != "onaylandi": return False
        for l_in, k_in, m_in in [
            ([], k, 0.5), (123, k, 0.5), ([123], k, 0.5), ([{"iddia_id": "x"}], k, 0.5), ([d1, d1], k, 0.5),
            ([dict(d1, satir_no=0)], k, 0.5), ([dict(d1, satir_no=True)], k, 0.5), ([dict(d1, satir_no="1")], k, 0.5),
            ([dict(d1, iddia_id=" ")], k, 0.5), ([dict(d1, iddia_id=1)], k, 0.5),
            ([d1], 123, 0.5), ([d1], {"dosyalar": {"a.py": ["x"]}}, 0.5),
            ([d1], {"dosyalar": 123, "bilinen_paketler": ["json"]}, 0.5),
            ([d1], {"dosyalar": {}, "bilinen_paketler": ["json"]}, 0.5),
            ([d1], {"dosyalar": {" ": ["x"]}, "bilinen_paketler": ["json"]}, 0.5),
            ([d1], {"dosyalar": {1: ["x"]}, "bilinen_paketler": ["json"]}, 0.5),
            ([d1], {"dosyalar": {"a.py": 123}, "bilinen_paketler": ["json"]}, 0.5),
            ([d1], {"dosyalar": {"a.py": []}, "bilinen_paketler": ["json"]}, 0.5),
            ([d1], {"dosyalar": {"a.py": [1]}, "bilinen_paketler": ["json"]}, 0.5),
            ([d1], {"dosyalar": {"a.py": ["x"]}, "bilinen_paketler": 123}, 0.5),
            ([d1], {"dosyalar": {"a.py": ["x"]}, "bilinen_paketler": []}, 0.5),
            ([d1], {"dosyalar": {"a.py": ["x"]}, "bilinen_paketler": [" "]}, 0.5),
            ([d1], {"dosyalar": {"a.py": ["x"]}, "bilinen_paketler": [1]}, 0.5),
            ([d1], k, -0.1), ([d1], k, 1.1), ([d1], k, True), ([d1], k, "0.5"), ([d1], k, float("nan")), ([d1], k, float("inf")),
        ]:
            try: kanitli_bulgu_suzgeci(l_in, k_in, m_in); return False
            except ValueError: pass
        return True
    except Exception:
        return False
ok(_on_sozlesme(), "sentetik ön kontrol: halüsinasyon oranı ve süzgeç sınırları tam")

if not all(checks):
    stop()

try:
    r = D.deney(kanit_satiri_eslestir, halusinasyon_orani_hesapla, kanitli_bulgu_suzgeci)
except Exception as e:
    ok(False, f"GERÇEK HALÜSİNASYON DOĞRULAMA DENEYİ YAPILAMADI: {type(e).__name__}: {e}")
    stop()

for ad, deger in r["kontroller"].items():
    ok(deger, "gerçek deney: " + ad)

ai_lab.kanit_yaz("ile-guvenlik-02-halusinasyon", {
    "kaynak": "gercek",
    "kabul": all(checks),
    "ders": "ai-ile-guvenlik-02",
    "ortam": r["ortam"],
    "ayarlar": r["ayarlar"],
    "deney": r,
    "ozet": r["ozet"],
})
o = r["ozet"]
ok(
    True,
    f"BULGU ({o['model']}): doğrulanan={o['dogrulanan_sayisi']}, elenen={o['elenen_sayisi']}, halüsinasyon_oranı={o['halusinasyon_orani']}, karar={o['rapor_karari']}.",
)
```

```solution
import ai_lab

ZORUNLU_IDDIA_ALANLARI = ("iddia_id", "dosya_adi", "satir_no", "kanit_alt_dizgesi", "onerilen_paket")

def _dogrula_kaynak_haritasi(kaynak_haritasi):
    if not isinstance(kaynak_haritasi, dict) or set(kaynak_haritasi.keys()) != {"dosyalar", "bilinen_paketler"}:
        raise ValueError("kaynak haritası şeması geçersiz")
    dosyalar = kaynak_haritasi["dosyalar"]
    paketler = kaynak_haritasi["bilinen_paketler"]
    if not isinstance(dosyalar, dict) or not dosyalar:
        raise ValueError("dosyalar boş olmayan sözlük olmalı")
    for ad, satirlar in dosyalar.items():
        if not isinstance(ad, str) or not ad.strip() or not isinstance(satirlar, list) or not satirlar:
            raise ValueError("dosya tanımı geçersiz")
        for s in satirlar:
            if not isinstance(s, str):
                raise ValueError("her satır string olmalı")
    if not isinstance(paketler, list) or not paketler:
        raise ValueError("bilinen paketler boş olmayan liste olmalı")
    for p in paketler:
        if not isinstance(p, str) or not p.strip():
            raise ValueError("paket adı geçersiz")

def kanit_satiri_eslestir(iddia, kaynak_haritasi):
    if not isinstance(iddia, dict) or set(iddia.keys()) != set(ZORUNLU_IDDIA_ALANLARI):
        raise ValueError("iddia şeması geçersiz")
    for alan in ("iddia_id", "dosya_adi", "kanit_alt_dizgesi", "onerilen_paket"):
        if not isinstance(iddia[alan], str) or not iddia[alan].strip():
            raise ValueError("metin alanı boş olamaz")
    satir_no = iddia["satir_no"]
    if isinstance(satir_no, bool) or not isinstance(satir_no, int) or satir_no < 1:
        raise ValueError("satır numarası pozitif tam sayı olmalı")
    _dogrula_kaynak_haritasi(kaynak_haritasi)

    dosyalar = kaynak_haritasi["dosyalar"]
    paketler = kaynak_haritasi["bilinen_paketler"]
    dosya_adi = iddia["dosya_adi"]

    if dosya_adi not in dosyalar:
        durum = "uydurma_dosya"
    elif satir_no > len(dosyalar[dosya_adi]):
        durum = "uydurma_satir"
    elif iddia["kanit_alt_dizgesi"] not in dosyalar[dosya_adi][satir_no - 1]:
        durum = "uyusmayan_kanit"
    elif iddia["onerilen_paket"] not in paketler:
        durum = "uydurma_paket"
    else:
        durum = "dogrulandi"

    return {
        "iddia_id": iddia["iddia_id"],
        "durum": durum,
        "gecerli": durum == "dogrulandi",
    }

def halusinasyon_orani_hesapla(iddia_listesi, kaynak_haritasi):
    if not isinstance(iddia_listesi, list) or not iddia_listesi:
        raise ValueError("iddia listesi boş olamaz")
    _dogrula_kaynak_haritasi(kaynak_haritasi)
    gorulen = set()
    dogrulanan_idleri = []
    halusinasyon_turleri = {}

    for i in iddia_listesi:
        sonuc = kanit_satiri_eslestir(i, kaynak_haritasi)
        iid = sonuc["iddia_id"]
        if iid in gorulen:
            raise ValueError("tekrar eden iddia kimliği")
        gorulen.add(iid)
        if sonuc["gecerli"]:
            dogrulanan_idleri.append(iid)
        else:
            tur = sonuc["durum"]
            halusinasyon_turleri[tur] = halusinasyon_turleri.get(tur, 0) + 1

    toplam = len(iddia_listesi)
    halusinasyon_sayisi = toplam - len(dogrulanan_idleri)
    oran = round(halusinasyon_sayisi / toplam, 4)
    return {
        "dogrulanan_idleri": sorted(dogrulanan_idleri),
        "halusinasyon_turleri": dict(sorted(halusinasyon_turleri.items())),
        "halusinasyon_orani": oran,
    }

def kanitli_bulgu_suzgeci(iddia_listesi, kaynak_haritasi, max_halusinasyon_orani=0.35):
    import math
    if isinstance(max_halusinasyon_orani, bool) or not isinstance(max_halusinasyon_orani, (int, float)) or not math.isfinite(max_halusinasyon_orani):
        raise ValueError("eşik sayısal olmalı")
    if max_halusinasyon_orani < 0 or max_halusinasyon_orani > 1:
        raise ValueError("eşik geçersiz")
    ozet = halusinasyon_orani_hesapla(iddia_listesi, kaynak_haritasi)
    elenen = [i["iddia_id"] for i in iddia_listesi if i["iddia_id"] not in ozet["dogrulanan_idleri"]]
    guvenilir = ozet["halusinasyon_orani"] <= max_halusinasyon_orani and bool(ozet["dogrulanan_idleri"])
    return {
        "kabul_edilen_bulgular": ozet["dogrulanan_idleri"],
        "elenen_idleri": sorted(elenen),
        "halusinasyon_orani": ozet["halusinasyon_orani"],
        "rapor_karari": "onaylandi" if guvenilir else "guvenilmez_model_raporu",
    }

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_ile_guvenlik_02 as deney
    deney.goster(kanit_satiri_eslestir, halusinasyon_orani_hesapla, kanitli_bulgu_suzgeci)
```

```hint
Önceki üç görevdeki `kanit_satiri_eslestir`, `halusinasyon_orani_hesapla` ve `kanitli_bulgu_suzgeci` çözümlerini birleştir.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
### Model iddiası dosya ve satırla sınanır

Bir paket adının varlığı, bir satırın gerçekten dosyada bulunması ve o satırın iddiayı desteklemesi ayrı kontrollerdir. Kaynakla eşleşmeyen bulgu halüsinasyon olarak raporlanır; sessizce doğru bulguların yanına eklenmez. Bu dar kapı gerçek zafiyetin bütün yürütme bağlamını ispatlamaz, fakat uydurma dosya/satır ve paket iddialarını görünür kılar.

| Yaygın yanlış | Kontrolün gösterdiği |
|---|---|
| Kaynakta sözcük geçmesi zafiyet kanıtıdır | Konum eşleşmesi gerekli olabilir; güvenlik yorumu ayrıca doğrulanır. |

Sonraki bağlantı: ai-ile-guvenlik-04. [Birincil kaynak](https://docs.python.org/3/library/ast.html). Kaynak ilgili araç veya yöntemi açıklar; labın gerçek sonucu ham kanıt kaydındadır.
:::
