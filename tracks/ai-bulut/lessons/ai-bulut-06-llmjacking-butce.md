---
id: ai-bulut-06
title: "LLMjacking · Kullanım, Bütçe ve Alarm"
summary: Çalınmış bulut kimliğiyle model çağırmanın (LLMjacking) maliyet mekanizmasını kur; çağrıdan önce en kötü durum maliyetini bütçeden ayıran kapıyı ve saatlik harcamada ani artış alarmını yaz.
esleme: ai-savunma-31, ai-temel-20, ai-bulut-03, ai-bulut-04
timeout: 30
---

::: anlat 1. Gerçek olay: LLMjacking
Sysdig Tehdit Araştırma Ekibi 6 Mayıs 2024'te (Alessandro Brucato) *LLMjacking* adını verdiği bir saldırıyı yayımladı. Zincir kısaca şöyleydi:

1. Saldırganlar, Laravel'in açığı bulunan bir sürümünü çalıştıran bir sistemden (CVE-2021-3129) bulut kimlik bilgilerini ele geçirdi.
2. Bir denetim betiğiyle bu kimliklerin hangi LLM hizmetlerine erişebildiğini sınadılar; betik AWS Bedrock, Azure, GCP Vertex AI, OpenAI, Anthropic ve başka sağlayıcıları kapsıyordu.
3. Gözlenen saldırıda Bedrock üzerindeki bir Anthropic Claude modeli hedeflendi. Erişim, modeli çalıştırmadan, bilerek bozuk parametreyle yapılan çağrılarla sınandı (`ai-bulut-03`).

Rapora göre kurbanın en kötü durumdaki maliyeti günde 46.000 doları aşabilirdi. Saldırgan veriyi çalmak için değil, **başkasının faturasına model kullanmak** için geliyordu. OWASP bu sonucu LLM10:2025 *Unbounded Consumption* maddesinde *Denial of Wallet* olarak adlandırır.

> [!NOTE]
> Bu dersteki tutarlar, token sayıları ve birim fiyatlar **sentetiktir** ve tam sayı "kuruş" birimindedir; gerçek bir sağlayıcının fiyatı değildir. Gerçek hesap, anahtar ya da çağrı yoktur.
:::

::: anlat 2. Mekanizma: neden çağrıdan önce rezerv?
Bir model çağrısının maliyeti iki parçadır: giriş token'ları × giriş fiyatı ve çıkış token'ları × çıkış fiyatı. Giriş token sayısı çağrıdan önce bilinir; **çıkış sayısı bilinmez**, yalnız üst sınırı (`max_output`) bilinir. Bütçeyi çağrıdan sonra gerçek kullanımla düşmek, eşzamanlı çağrılarda bütçenin aşılmasına izin verir: on paralel çağrı aynı kalan bütçeyi görür ve hepsi geçer.

Güvenli kapı bu yüzden en kötü durumu **rezerve eder**:

`rezerv = input_tokens × rate_in + max_output × rate_out`

Rezerv kalan bütçeyi aşıyorsa çağrı reddedilir. Geçerse rezerv hemen düşülür; çağrı bittiğinde kullanılmayan kısım geri verilebilir (bu derste geri verme yok). Tam sayı birim kullanmak, kayan nokta yuvarlamasının bütçe sınırında "neredeyse eşit" hatalar üretmesini önler.

Kapı tek başına yetmez. LLMjacking'de saldırgan geçerli bir kimlikle gelir; bütçe tükenene kadar her çağrı "izinli"dir. İkinci halka harcamanın **şeklini** izlemektir: dün saatte birkaç kuruş harcayan bir anahtarın bu saat yüzlerce katı harcaması bir alarm sinyalidir.

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| Bütçeyi çağrıdan sonra düşmek | Eşzamanlı çağrılar aynı kalan bütçeyi görür | Çağrıdan önce en kötü durumu rezerve et |
| Yalnız giriş maliyetini hesaplamak | Uzun çıktı istenerek bütçe aşılır | `max_output × rate_out` de rezerve edilir |
| `float` para birimi | `0.1 + 0.2` sınırda yanlış karar üretir | Tam sayı en küçük birim |
| `maliyet < kalan` | Bütçeyi tam kullanan meşru çağrı reddedilir | `maliyet <= kalan` |
| Tek eşikli alarm (ör. "saatte 1000'i geç") | Küçük anahtarın 100 katı artışı eşiğin altında kalır | Anahtarın kendi geçmişine göre oran |
:::

::: tahmin Eşzamanlı çağrı ve sonradan düşme
Kalan bütçe 100; her çağrı en çok 60 tutuyor. İki çağrı aynı anda kalan bütçeyi okuyor. "Sonradan düş" yaklaşımında kaç çağrı geçer, "önceden rezerve et" yaklaşımında kaç?

```python
kalan = 100
maliyet = 60
gorulen = [kalan, kalan]
sonradan = sum(1 for g in gorulen if maliyet <= g)

kalan_r = 100
onceden = 0
for _ in range(2):
    if maliyet <= kalan_r:
        kalan_r -= maliyet
        onceden += 1
print('sonradan düş:', sonradan, '| önceden rezerv:', onceden, '| rezerv sonrası kalan:', kalan_r)
```

???

```cikti
sonradan düş: 2 | önceden rezerv: 1 | rezerv sonrası kalan: 40
```
Sonradan düşmede iki çağrı da aynı 100'ü gördü ve geçti; gerçek harcama 120 olur. Önceden rezervde ilk çağrı 60'ı ayırır, ikinci çağrı kalan 40'ı görür ve reddedilir.
:::

::: gorev 1 · En kötü durumu rezerve eden bütçe kapısı
`butce_kapisi(kalan, input_tokens, max_output, rate_in, rate_out)` işlevini yaz.

- Beş argümanın hepsi `bool` olmayan, `>= 0` bir `int` olmalı; değilse `ValueError`.
- `maliyet = input_tokens * rate_in + max_output * rate_out`.
- `maliyet <= kalan` ise `{'izin': True, 'rezerv': maliyet, 'kalan': kalan - maliyet}`; değilse `{'izin': False, 'rezerv': 0, 'kalan': kalan}`.

KUSURLU başlangıç yalnız giriş maliyetini hesaplıyor, katı `<` kullanıyor ve `float` girdiyi kabul ediyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
Path('ornek.json').write_text('[1000, 200, 300, 1, 3]', encoding='utf-8')
```

```starter
def butce_kapisi(kalan, input_tokens, max_output, rate_in, rate_out):
    maliyet = input_tokens * rate_in
    if maliyet < kalan:
        return {'izin': True, 'rezerv': maliyet, 'kalan': kalan - maliyet}
    return {'izin': False, 'rezerv': 0, 'kalan': kalan}

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(butce_kapisi(*_args))
```

```solution
def butce_kapisi(kalan, input_tokens, max_output, rate_in, rate_out):
    for x in (kalan, input_tokens, max_output, rate_in, rate_out):
        if type(x) is not int or x < 0:
            raise ValueError('butun argumanlar negatif olmayan int olmali')
    maliyet = input_tokens * rate_in + max_output * rate_out
    if maliyet <= kalan:
        return {'izin': True, 'rezerv': maliyet, 'kalan': kalan - maliyet}
    return {'izin': False, 'rezerv': 0, 'kalan': kalan}

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(butce_kapisi(*_args))
```

```test
need('butce_kapisi')
eq(butce_kapisi(1000, 200, 300, 1, 3), {'izin': False, 'rezerv': 0, 'kalan': 1000}, 'çıkış rezervi bütçeyi aşar: 200 + 900 = 1100')
eq(butce_kapisi(1100, 200, 300, 1, 3), {'izin': True, 'rezerv': 1100, 'kalan': 0}, 'maliyet tam kalana eşitse izin')
eq(butce_kapisi(1101, 200, 300, 1, 3), {'izin': True, 'rezerv': 1100, 'kalan': 1}, 'bir birim artıkla izin')
eq(butce_kapisi(1099, 200, 300, 1, 3), {'izin': False, 'rezerv': 0, 'kalan': 1099}, 'bir birim eksikle ret')
eq(butce_kapisi(50, 7, 0, 2, 9), {'izin': True, 'rezerv': 14, 'kalan': 36}, 'çıkışsız çağrı yalnız giriş maliyeti')
eq(butce_kapisi(50, 0, 4, 2, 9), {'izin': True, 'rezerv': 36, 'kalan': 14}, 'girişsiz çağrı yalnız çıkış rezervi')
eq(butce_kapisi(0, 0, 0, 5, 5), {'izin': True, 'rezerv': 0, 'kalan': 0}, 'sıfır maliyet sıfır bütçeyle geçer')
eq(butce_kapisi(0, 1, 0, 1, 0), {'izin': False, 'rezerv': 0, 'kalan': 0}, 'sıfır bütçe pozitif maliyeti reddeder')
_k = 100
_g = 0
for _ in range(3):
    _r = butce_kapisi(_k, 10, 5, 2, 4)
    if _r['izin']:
        _k = _r['kalan']
        _g += 1
eq((_g, _k), (2, 20), 'sıralı rezervler: 40 + 40 geçer, üçüncü (40 > 20) reddedilir')

for _i in range(5):
    for _kotu in (-1, 1.0, True, '5', None):
        _arg = [1000, 10, 10, 1, 1]
        _arg[_i] = _kotu
        raises(ValueError, butce_kapisi, *_arg, msg=f'{_i}. argüman bozuk ({_kotu!r}) ValueError')
```

```hint
Önce beş argümanı tek döngüde doğrula: `type(x) is not int or x < 0`. Maliyete çıkış rezervini de kat ve sınırı `<=` ile karşılaştır.
```
:::

::: gorev 2 · Saatlik harcamada ani artış alarmı
Her anahtarın saatlik harcamasını kendi geçmişiyle karşılaştıran `harcama_alarmi(saatlik, kat, pencere)` işlevini yaz.

- `saatlik`: `bool` olmayan, `>= 0` `int`'lerden oluşan bir `list` (birim: kuruş). `kat` ve `pencere` `bool` olmayan, `>= 1` `int`'ler. Değilse `ValueError`.
- `i`. saat için taban, önceki `pencere` saatin **ortalamasıdır**: `saatlik[i - pencere : i]`. Önünde `pencere` kadar saat olmayan ilk saatler değerlendirilmez.
- Alarm kuralları:
  - Taban `0` ve `saatlik[i] > 0` → `[i, 'sifirdan-artis']`;
  - Taban `> 0` ve `saatlik[i] * pencere > kat * toplam` (yani `saatlik[i] > kat × ortalama`; tam sayı karşılaştırması, bölme yok) → `[i, 'kat-asimi']`.
- Dönüş: alarm listesi, saat sırasıyla. Girdiyi değiştirme.

KUSURLU başlangıç tabanı sabit ilk saatlerden alıyor, kayan noktalı ortalamayla `>=` karşılaştırıyor ve sıfır tabanı atlıyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def harcama_alarmi(saatlik, kat, pencere):
    taban = sum(saatlik[:pencere]) / pencere
    alarm = []
    for i in range(pencere, len(saatlik)):
        if taban and saatlik[i] >= kat * taban:
            alarm.append([i, 'kat-asimi'])
    return alarm
```

```solution
def _sayi(x, alt):
    return type(x) is int and x >= alt

def harcama_alarmi(saatlik, kat, pencere):
    if not isinstance(saatlik, list) or not all(_sayi(x, 0) for x in saatlik):
        raise ValueError('saatlik negatif olmayan int listesi olmali')
    if not _sayi(kat, 1) or not _sayi(pencere, 1):
        raise ValueError('kat ve pencere >= 1 int olmali')
    alarm = []
    for i in range(pencere, len(saatlik)):
        toplam = sum(saatlik[i - pencere:i])
        if toplam == 0:
            if saatlik[i] > 0:
                alarm.append([i, 'sifirdan-artis'])
        elif saatlik[i] * pencere > kat * toplam:
            alarm.append([i, 'kat-asimi'])
    return alarm
```

```test
need('harcama_alarmi')
import copy
_seri = [4, 6, 5, 5, 20, 21, 600, 5, 0, 0, 0, 0, 3]
_yedek = copy.deepcopy(_seri)
eq(harcama_alarmi(_seri, 4, 4), [[6, 'kat-asimi'], [12, 'sifirdan-artis']],
   'taban kayar pencereyle güncellenir: 20 ve 21 alarm değil (ortalama 5 × 4 = 20, 20 sınırda), 600 alarm; sıfır taban sonrası 3 alarm')
eq(_seri, _yedek, 'girdi değişmemeli')
eq(harcama_alarmi([5, 5, 5, 5, 20], 4, 4), [], 'tam kat sınırında (20 = 4 × 5) alarm yok')
eq(harcama_alarmi([5, 5, 5, 5, 21], 4, 4), [[4, 'kat-asimi']], 'sınırın bir birim üstü alarm')
eq(harcama_alarmi([1, 2, 7], 2, 2), [[2, 'kat-asimi']], 'tam sayı karşılaştırması: 7 × 2 = 14 > 2 × 3 = 6')
eq(harcama_alarmi([3, 4, 7], 2, 2), [], 'ortalama 3,5 × 2 = 7; 7 sınırda, alarm yok')
eq(harcama_alarmi([0, 0, 0], 3, 2), [], 'sıfırdan sıfıra alarm yok')
eq(harcama_alarmi([0, 0, 1], 3, 2), [[2, 'sifirdan-artis']], 'sıfır tabandan en küçük harcama (1) da alarm')
eq(harcama_alarmi([9, 1], 1, 1), [], 'düşüş alarm değildir')
eq(harcama_alarmi([2, 3], 1, 1), [[1, 'kat-asimi']], 'kat = 1 en küçük geçerli değer')
eq(harcama_alarmi([10, 10], 1, 2), [], 'pencere kadar geçmişi olmayan saatler değerlendirilmez')
eq(harcama_alarmi([], 2, 3), [], 'boş seri boş liste')

for _arg in (((1, 2, 3), 2, 1), ([1, -1, 3], 2, 1), ([1, 2.0, 3], 2, 1), ([1, True, 3], 2, 1), ([1, 2], 0, 1),
             ([1, 2], 2, 0), ([1, 2], 2.0, 1), ([1, 2], 2, True), ([1, 2], True, 1), ([1, '2'], 2, 1)):
    raises(ValueError, harcama_alarmi, *_arg, msg=f'bozuk argüman ValueError: {_arg!r}')
```

```hint
Tabanı her saat için yeniden hesapla: `toplam = sum(saatlik[i - pencere:i])`. Ortalamayla bölmek yerine iki tarafı `pencere` ile çarp; böylece kayan nokta yuvarlaması kararı etkilemez.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Olay (25 sn).** "Sysdig 2024'te LLMjacking'i yayımladı: Laravel açığından çalınan bulut kimlikleriyle Bedrock'ta Claude çağrılıyor. Saldırganın amacı veri değil, başkasının faturasına model kullanmak; en kötü durum günde 46 bin doları aşıyor."
2. **Rezerv (30 sn).** "Çıkış token sayısı çağrıdan önce bilinmez. Bu yüzden kapı en kötü durumu, yani giriş artı maksimum çıkışı, çağrıdan önce bütçeden ayırıyor. Testte bütçeyi tam kullanan çağrı geçiyor, bir kuruş fazlası reddediliyor."
3. **Eşzamanlılık (20 sn).** "Sonradan düşmede iki paralel çağrı aynı kalan bütçeyi görüp ikisi de geçiyordu; önceden rezerv bunu kapattı."
4. **Alarm (30 sn).** "Saldırgan geçerli kimlikle geldiği için kapı bütçe bitene kadar izin verir. İkinci halka her anahtarın saatlik harcamasını kendi kayan ortalamasıyla karşılaştırıyor. Sıfır geçmişten aniden harcamaya geçişi de ayrı yakalıyor."
5. **Sınır (15 sn).** "Fiyatlar sentetik ve tam sayı; gerçek sağlayıcının faturalama gecikmesi ve geri iade mantığı modellenmedi."
:::

::: anlat Sınır ve kaynak
Bu ders tek bir bütçe sayacını ve tek bir anahtarın saatlik serisini modeller. Gerçek sistemde sayaç paylaşımlıdır ve atomik güncellenmelidir (ör. veritabanı işlemi). Çağrı bitince kullanılmayan rezervin geri verilmesi ve sağlayıcının faturalama gecikmesi burada yoktur. Alarm kuralı mevsimselliği (gece/gündüz, hafta sonu) bilmez; gerçek tespitte taban aynı saat dilimlerinden kurulur. Rapordaki 46.000 dolar rakamı Sysdig'in en kötü durum tahminidir, gözlenmiş bir fatura değildir.

- Birincil kaynaklar: [Sysdig — LLMjacking: Stolen Cloud Credentials Used in New AI Attack (Brucato, 6 Mayıs 2024)](https://sysdig.com/blog/llmjacking-stolen-cloud-credentials-used-in-new-ai-attack/) (CVE-2021-3129 üzerinden kimlik hırsızlığı, hedeflenen hizmetler, günlük maliyet tahmini); [OWASP GenAI — LLM10:2025 Unbounded Consumption](https://genai.owasp.org/llmrisk/llm102025-unbounded-consumption/) (*Denial of Wallet*); [Amazon Bedrock — Per-request metadata tagging](https://docs.aws.amazon.com/bedrock/latest/userguide/cost-mgmt-request-metadata.html) (çağrı başına etiketle kullanımı anahtara ve ekibe bağlama). Doğrulama tarihi: 11 Kasım 2026.
:::

::: dusun
Saldırgan alarmı biliyorsa harcamayı günlerce yavaşça artırabilir; her saat bir öncekinin yalnız biraz üstünde kalır. Kayan pencere tabanı bu "kaynatma" stratejisine karşı neden zayıftır? Hangi ikinci taban (ör. geçen ayın aynı haftası) bunu yakalar?
:::

::: ozet
- LLMjacking'de saldırgan geçerli kimlikle gelir; hedef veri değil, başkasının faturasına model kullanmaktır.
- Bütçe kapısı çağrıdan önce en kötü durumu (giriş + maksimum çıkış) rezerve eder; sonradan düşmek eşzamanlı çağrılarda bütçeyi aşar.
- Para tam sayı en küçük birimle tutulur; sınır `<=` ile karşılaştırılır.
- İkinci halka, harcamayı anahtarın kendi geçmişiyle karşılaştıran oran tabanlı alarmdır.
:::
