---
id: ai-temel-31
title: Scaling Laws, Emergence ve Grokking · Bir AI Neden Diğerinden Daha Zekidir?
summary: Kaplan ve Chinchilla Scaling Laws, Compute-Optimal Pre-training, Grokking (ezberden genellemeye faz geçişi), Emergent Abilities ve Test-Time Compute eksenleriyle modeller arasındaki zeka farkının fiziğini anlamak.
esleme: ai-temel-09, ai-temel-32, ai-temel-34
---

::: anlat 1. Model performansını etkileyen bileşenler
Aynı mimari ailesindeki iki modelin performansı; parametre sayısı, training verisi, hedef fonksiyon, optimization ve inference sırasında kullanılan hesap bütçesine göre değişebilir. Tek bir “zeka skoru” bütün bu farkları ölçmez.

Bir konferansta dinleyicilerin en sık sorduğu soru şudur: *"Küçük bir açık ağırlıklı model de, Opus veya Gemini gibi devasa bir `Frontier Model` de temelde aynı `Transformer` denklemini (`Attention` + `MLP`) kullanıyor. Formül aynıysa, birini sıradan bir metin tamamlayıcı yaparken diğerini karmaşık matematik teoremlerini kanıtlayan, yazılım mimarisi kuran bir zekaya dönüştüren şey nedir?"*

Bu derste **scaling laws** fikrini, bir ölçüm eğrisinin nasıl yorumlandığını ve **test-time compute** bütçesini ayıracağız. Aşağıdaki `model_zeka_skoru` işlevi bilimsel bir IQ testi değildir; farklı maliyetlerin bir arada gösterildiği, katsayıları elle seçilmiş bir oyuncak modeldir.

Kaynak: [Chinchilla: compute-optimal training](https://arxiv.org/abs/2203.15556).

**Örneği okuma:** Aşağıdaki kodda seçilen katsayı ve sınıflar eğitim varsayımıdır; gerçek bir model veya donanım ölçümü değildir. Çıktı, bu varsayımın aritmetik sonucunu gösterir.

```python
# Üç kaldıracın modelin nihai problem çözme kapasitesine etkisini simüle edelim
def model_zeka_skoru(parametre_milyar, token_trilyon, dusunme_adimi):
    import math
    # Chinchilla dengesi: Her 1 milyar parametre için ~20 milyar (0.02 trilyon) token idealdir
    ideal_token = parametre_milyar * 0.02
    veri_verimi = min(1.0, token_trilyon / ideal_token)
    pretrain_gucu = math.log10(1 + parametre_milyar) * veri_verimi
    # Test-Time Compute (System 2) çarpanı: logaritmik düşünme kazancı
    reasoning_gucu = 1.0 + 0.35 * math.log2(max(1, dusunme_adimi))
    return round(pretrain_gucu * reasoning_gucu, 2)

print("Küçük & Düşünmeyen Model (7B, 0.1T token, 1 adım):", model_zeka_skoru(7, 0.1, 1))
print("Chinchilla-Optimal Baz Model (70B, 1.4T token, 1 adım):", model_zeka_skoru(70, 1.4, 1))
print("Frontier Reasoning Modeli (500B, 15T token, 64 düşünme adımı):", model_zeka_skoru(500, 15, 64))
```
:::

::: anlat 2. Scaling laws ve compute-optimal training
**Scaling laws**, belirli veri/model/training koşullarında ölçülen loss ile ölçek değişkenleri arasındaki ampirik ilişkileri ifade eder. Fizik yasası veya her model için geçerli bir başarı garantisi değildir.

Sık kullanılan yaklaşık bütçe hesabı $C \approx 6ND$ biçimindedir: $N$ parametre, $D$ training token sayısıdır. Mimari, sequence length ve implementation maliyetleri sonucu değiştirir. Chinchilla çalışması kendi deney düzeninde model ve veri boyutunu birlikte ölçeklemenin önemini gösterir; $D/N \approx 20$ her yeni model için zorunlu sabit değildir.

Aşağıdaki eşik adları ve loss formülü, bu ders için sadeleştirilmiş bir maliyet örneğidir. Başka veriye doğrudan performans tahmini olarak taşınmamalı.

**Örneği okuma:** Aşağıdaki kodda seçilen katsayı ve sınıflar eğitim varsayımıdır; gerçek bir model veya donanım ölçümü değildir. Çıktı, bu varsayımın aritmetik sonucunu gösterir.

```python
def chinchilla_analizi(parametre_milyar, token_milyar):
    flops = 6 * (parametre_milyar * 1e9) * (token_milyar * 1e9)
    oran = token_milyar / parametre_milyar
    durum = "Under-trained (Parametre israfı)" if oran < 18 else ("Chinchilla-Optimal" if oran <= 30 else "Inference-Optimal (Over-trained)")
    # Basitleştirilmiş Chinchilla Loss tahmini: E + A/N^0.34 + B/D^0.34
    loss = 1.69 + 406.4 / ((parametre_milyar * 1e9) ** 0.34) + 410.7 / ((token_milyar * 1e9) ** 0.34)
    return {"oran_D_N": round(oran, 1), "toplam_exaflops": round(flops / 1e18, 1), "tahmini_loss": round(loss, 4), "durum": durum}

print("GPT-3 (175B N, 300B D)     :", chinchilla_analizi(175, 300))
print("Chinchilla (70B N, 1400B D):", chinchilla_analizi(70, 1400))
```

### Loss modeli: hangi değişken neyi temsil eder?
Bir scaling fit örneği şu biçimde yazılabilir:

$$L(N,D)=E+\frac{A}{N^\alpha}+\frac{B}{D^\beta}.$$

Burada $N$ parametre sayısı, $D$ training token sayısıdır. $A,B,\alpha,\beta,E$ ise bir deney ailesinin ölçümlerine fit edilen değerlerdir; bağımsız evrensel sabitler değildir. $E$ terimi bazen **irreducible entropy** ile ilişkilendirilen bir taban olarak yorumlanır. Fakat sınırlı deney aralığından fit edilen $E$ değerini doğal dilin kesin ve değişmez entropy değeri sayamayız. Dil, tokenizer, corpus ve evaluation düzeni değişince ölçüm de değişir.

Sabit $C\approx6ND$ bütçesinde yalnız $N$ artırırsan $D$ azaltmak zorunda kalabilirsin. Model büyürken daha az örnek görmek, ek parametrelerin yararını sınırlayabilir. Compute-optimal seçim bu trade-off üzerindedir. Inference için defalarca kullanılacak küçük bir modeli daha uzun eğitmek ise farklı bir maliyet hedefini optimize edebilir; training-optimal ile lifetime-cost-optimal aynı şey değildir.

Kodda kullanılan loss katsayıları, $D/N$ eşikleri ve etiketler bir öğrenme örneğidir. Bunları yeni bir model için gerçek validation loss ölçmeden karar kuralına dönüştürme.
:::

::: anlat 3. Loss ile görev başarısını ayır
Cross-entropy loss, modelin doğru tokena verdiği probability ile ilgilidir. Daha düşük validation loss, aynı veri dağılımında daha iyi prediction gösterebilir; tek başına bütün görevlerde daha doğru, güvenli veya daha “zeki” model demek değildir.

Örneğin kopya bir test kümesi loss değerini düşürebilir; fakat yeni bir görevdeki yeteneği göstermez. Loss, task success, calibration ve güvenlik ölçümlerini ayrı raporla. Bir metni sıkıştırabilmek ile o metindeki her iddiayı anlamak/doğrulamak aynı kabul değildir.

### Prediction loss neden bazı görevlere yardımcı olabilir?
Bir sonraki tokenı iyi tahmin etmek bazen syntax, uzun mesafeli bağımlılık veya bir problem çözme örüntüsünü temsil etmeyi gerektirir. Bu, yalnız yüzeysel kelime sayımıyla açıklanamayacak özelliklerin öğrenilebilmesine yol açar. Yine de eğitim hedefi, kaynak doğrulaması veya her problem için doğru reasoning garantisi değildir.

Örneğin iki model aynı validation cross-entropy değerine yakın olabilir; biri code completion, diğeri Türkçe belge retrieval görevinde daha başarılı olabilir. Kararı yalnız loss ile değil, hedef görevin bağımsız ve contamination kontrolü yapılmış testleriyle ver. Compression ile intelligence arasındaki ilişki araştırma sorusudur; eşitlik diye varsayılmaz.
:::

::: anlat 4. Emergence, ölçüm eşiği ve grokking
Bir görev art arda birkaç doğru adım gerektiriyorsa, her adımdaki küçük bir iyileşme toplam başarıda büyük fark oluşturabilir. Son tahminde adımların bağımsız ve aynı başarı probability değerine sahip olduğu varsayılıyor; bu yüzden toplam $p^8$ hesaplanıyor. Bu varsayım gerçek reasoning adımlarında otomatik sağlanmaz.

**Grokking**, bazı küçük algoritmik veri kümelerinde training başarısı yükseldikten çok sonra generalization gelişmesinin gözlenmesidir. Bütün modeller için sabit adımda ortaya çıkacağı veya belirli bir iç devrenin mutlaka oluşacağı söylenemez. [Özgün grokking çalışması](https://arxiv.org/abs/2201.02177).

### Emergence ile ölçüm biçimini ayır
Sekiz adımın her birinin doğru olma probability değeri $p$ ve adımlar bağımsız ise uçtan uca başarı $p^8$ olur. $0.5^8\approx0.0039$, $0.9^8\approx0.4305$ olduğundan adım düzeyindeki 1.8 kat fark toplamda yaklaşık 110 kat fark üretir. Bu bir bağımlılık/ölçüm örneğidir; modelde yeni bir mekanizmanın tam o eşikte ortaya çıktığını tek başına göstermez.

Grokking örneklerinde modüler aritmetik gibi küçük bir görevin train başarısı yükselirken test başarısı daha uzun süre düşük kalabilir. Optimization ve regularization değiştikçe daha sonra generalization artışı görülebilir. Araştırmacılar bazı özel deneylerde Fourier-benzeri temsiller incelemiştir; bütün reasoning modellerinin aynı iç devreyi zorunlu kurduğu sonucu çıkarılmaz.

Bu yüzden bir sıçrama gördüğünde hem skor fonksiyonunu hem modelin iç/çıktı davranışını incele: sadece binary pass/fail eşiği mi değişti, yoksa yeni görevlerde de taşınan bir yetenek mi oluştu?
:::

::: anlat 5. Pre-training compute ve test-time compute
Pre-training compute, ağırlıkları öğrenmek için harcanır. Test-time compute ise üretim, aday arama, tekrar deneme veya verifier ile seçim gibi inference işlemlerinde kullanılır. Bu ayrım, geçmişte hiçbir arama/reasoning yöntemi olmadığı anlamına gelmez.

Daha çok hesap her zaman daha iyi sonuç vermez: verifier hatası, uzun ama yanlış çıktılar ve latency sınırı vardır. Aynı görev ve bütçede doğruluk ile maliyeti birlikte ölç. [DeepSeek-R1 teknik raporu](https://arxiv.org/abs/2501.12948), belirli bir yayımlanmış yönteme örnektir; bütün ticari modellerin eğitim reçetesi değildir.

### Test-time compute hangi biçimlerde harcanır?
Aynı modelden birden fazla aday üretmek, search ağacında dal açmak, tool çağrısı yapmak veya verifier ile aday elemek farklı hesap harcamalarıdır. Toplam token sayısı tek başına bütün maliyeti açıklamaz; latency, tool süresi ve aynı anda kullanılan bellek de önemlidir.

Sağlam deneyde model ve görev setini sabit tutup bütçeyi değiştir; doğru çözüm oranını, verifier hatasını ve maliyeti birlikte raporla. Hatalı bir verifier daha çok adayla daha çok yanıltılabilir. Bu nedenle uzun çıktı veya daha çok search adımı doğrudan daha yüksek zeka diye puanlanmaz.

> **Özet Konferans Cümlesi:** *"Eski nesil AI'lar zekasını yalnızca eğitim sırasında yakılan elektrikten (`Pre-training Compute`) alıyordu; yeni nesil `Frontier AI`'lar ise zekasını hem eğitimdeki `Chinchilla Scaling Laws` dengesinden hem de soru sorulduğu anda harcadığı düşünme süresinden (`Test-Time Compute`) alır."*
:::

::: tahmin Zincirleme Muhakeme Eşiği (Emergence Hesabı)
Aşağıdaki kodda $8$ ardışık mantık adımı gerektiren bir siber güvenlik zafiyet analizi görevinde, adım başı doğruluğu $p=0.50$ olan küçük model ile adım başı doğruluğu $p=0.90$ olan `Frontier Model`'in uçtan uca başarı yüzdesi karşılaştırılıyor. Çıktı ne olur?

```python
kucuk_model = round((0.50 ** 8) * 100, 1)
frontier_model = round((0.90 ** 8) * 100, 1)
print(f"Kucuk: %{kucuk_model} | Frontier: %{frontier_model}")
```

???

```cikti
Kucuk: %0.4 | Frontier: %43.0
```
Adım başı başarıda %50'den %90'a çıkmak (1.8 kat artış), $8$ basamaklı zincirleme bir görevde uçtan uca başarıyı $0.5^8 = \%0.4$'ten $0.9^8 = \%43.0$'a (yani **100 kattan fazla!**) sıçratır. Dışarıdan bakan gözlemci bunu "modelde aniden beliren mucizevi bir yetenek (`Emergent Ability`)" olarak görür.
:::

::: gorev 1 · Chinchilla Kayıp Yasasıyla Hesap-Optimal Model ve Veri Boyutu
`chinchilla_optimal(hesap_flop, A, B, E, alpha, beta)` işlevini yaz. Kayıp yasası $L(N, D) = E + A/N^{\alpha} + B/D^{\beta}$, hesap bütçesi $C = 6ND$ FLOP'tur ($N$ parametre, $D$ token).

**Kurallar:**
1. Bütün argümanlar sonlu sayı olmalı (`bool` değil); `hesap_flop`, `A`, `B`, `alpha`, `beta` pozitif, `E` negatif olmamalı. Değilse `ValueError`.
2. Lagrange çarpanıyla bulunan kapalı form:
   $$N^* = G\left(\frac{C}{6}\right)^{\beta/(\alpha+\beta)},\qquad G = \left(\frac{\alpha A}{\beta B}\right)^{1/(\alpha+\beta)},\qquad D^* = \frac{C/6}{N^*}$$
3. Çıktı: `"N_opt"` ve `"D_opt"` (`round(·)` ile tam sayı), `"kayip"`: $L(N^*, D^*)$ (`round(·, 6)`, yuvarlanmamış $N^*, D^*$ ile), `"token_parametre_orani"`: $D^*/N^*$ (`round(·, 4)`).

Hesap iki katına çıkınca $N^*$ ve $D^*$ birlikte büyür: biri sabit kalırsa diğeri boşa harcanır.

```starter
def chinchilla_optimal(hesap_flop, A, B, E, alpha, beta):
    # KUSURLU BAŞLANGIÇ: "20 token/parametre" kuralını üsleri yok sayarak uyguluyor
    N = (hesap_flop / 120) ** 0.5
    D = 20 * N
    return {"N_opt": round(N), "D_opt": round(D), "kayip": E, "token_parametre_orani": 20.0}

print(chinchilla_optimal(6e18, 400.0, 400.0, 1.7, 0.5, 0.5))
```

```test
fn = need("chinchilla_optimal")
r = fn(6e18, 400.0, 400.0, 1.7, 0.5, 0.5)
eq(r["N_opt"], 1000000000, "α = β ve A = B iken N* = D* = sqrt(C/6)")
eq(r["D_opt"], 1000000000, "D* = (C/6)/N*")
eq(r["token_parametre_orani"], 1.0, "eşit üs ve katsayıda oran 1")
eq(r["kayip"], 1.725298, "1.7 + 2·400/√1e9")
r2 = fn(6e18, 400.0, 400.0, 1.7, 0.6, 0.3)
eq(r2["N_opt"], 2160119, "G = 2^(1/0.9) ≈ 2.16, N* = G·(1e18)^(1/3)")
eq(r2["D_opt"], 462937356144, "D* = 1e18 / N*")
eq(r2["token_parametre_orani"], 214310.9957, "veri üssü küçükse optimum çok token ister")
r3 = fn(1.2e19, 400.0, 400.0, 1.7, 0.5, 0.5)
ok(abs(r3["N_opt"] / r["N_opt"] - 2 ** 0.5) < 1e-6, "hesap iki katı → N* √2 katı")
ok(r3["kayip"] < r["kayip"], "daha çok hesap daha düşük kayıp")
raises(ValueError, fn, 0, 400.0, 400.0, 1.7, 0.5, 0.5)
raises(ValueError, fn, 6e18, 400.0, 400.0, -0.1, 0.5, 0.5)
raises(ValueError, fn, 6e18, 400.0, 400.0, 1.7, True, 0.5)
raises(ValueError, fn, 6e18, float("nan"), 400.0, 1.7, 0.5, 0.5)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef chinchilla_optimal(hesap_flop, A, B, E, alpha, beta):\n    for v in (hesap_flop, A, B, E, alpha, beta):\n        if isinstance(v, bool) or not isinstance(v, (int, float)) or (not math.isfinite(v)):\n            raise ValueError('argümanlar sonlu sayı olmalı')\n    if hesap_flop <= 0 or A <= 0 or B <= 0 or (alpha <= 0) or (beta <= 0) or (E < 0):\n        raise ValueError('hesap, A, B, alpha, beta pozitif; E negatif olmamalı')\n    c6 = float(hesap_flop) / 6.0\n    G = (alpha * A / (beta * B)) ** (1.0 / (alpha + beta))\n    N = G * c6 ** (beta / (alpha + beta))\n    D = c6 / N\n    L = E + A / N ** alpha + B / D ** beta\n    return {'N_opt': round(N), 'D_opt': round(D), 'kayip': round(L, 6), 'token_parametre_orani': round(D / N, 4)}", 'referans', 'exec'), _REF)
_t, _g = _ff(chinchilla_optimal, _REF['chinchilla_optimal'], (6e+18, 400.0, 400.0, 1.7, 0.5, 0.5), tohum=2819, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (chinchilla_optimal): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
import math

def chinchilla_optimal(hesap_flop, A, B, E, alpha, beta):
    for v in (hesap_flop, A, B, E, alpha, beta):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError("argümanlar sonlu sayı olmalı")
    if hesap_flop <= 0 or A <= 0 or B <= 0 or alpha <= 0 or beta <= 0 or E < 0:
        raise ValueError("hesap, A, B, alpha, beta pozitif; E negatif olmamalı")
    c6 = float(hesap_flop) / 6.0
    G = (alpha * A / (beta * B)) ** (1.0 / (alpha + beta))
    N = G * c6 ** (beta / (alpha + beta))
    D = c6 / N
    L = E + A / N ** alpha + B / D ** beta
    return {"N_opt": round(N), "D_opt": round(D), "kayip": round(L, 6), "token_parametre_orani": round(D / N, 4)}
```

```hint
Önce `G`, sonra `N`, sonra `D = (C/6)/N`. Kaybı yuvarlanmamış `N` ve `D` ile hesapla.
```
:::

::: gorev 2 · Kayıp Ölçümlerinden Güç Yasası Uydurmak ve Büyük Modeli Tahmin Etmek
`guc_yasasi_uydur(boyutlar, kayiplar, E, hedef_boyut)` işlevini yaz. Model boyutu $N$ ile kayıp arasında $L(N) = E + a\,N^{-b}$ ilişkisi varsayılır ($E$ indirgenemez kayıp, verilir).

**Kurallar:**
1. `boyutlar` ve `kayiplar` aynı uzunlukta, en az 2 öğeli, sonlu sayı (`bool` değil) listeleri olmalı; boyutlar pozitif ve en az iki farklı değerli, her kayıp `E`'den büyük olmalı. `E` sonlu ve negatif olmayan, `hedef_boyut` pozitif sayı olmalı. Değilse `ValueError`.
2. $x = \ln N$, $y = \ln(L - E)$ üzerinde en küçük kareler doğrusu $y = c + m x$: $m = \frac{\sum (x-\bar x)(y - \bar y)}{\sum (x - \bar x)^2}$, $c = \bar y - m\bar x$. Buradan $b = -m$, $a = e^{c}$.
3. $R^2 = 1 - \frac{\sum (y - \hat y)^2}{\sum (y - \bar y)^2}$; payda 0 ise $R^2 = 1$.
4. Çıktı: `"a"`, `"b"`, `"r2"` ve `"tahmin"` $= E + a \cdot \text{hedef}^{-b}$ (hepsi `round(·, 6)`).

```starter
def guc_yasasi_uydur(boyutlar, kayiplar, E, hedef_boyut):
    # KUSURLU BAŞLANGIÇ: log uzayına geçmeden doğrusal uyduruyor ve E'yi unutuyor
    n = len(boyutlar)
    mx, my = sum(boyutlar) / n, sum(kayiplar) / n
    m = sum((x - mx) * (y - my) for x, y in zip(boyutlar, kayiplar)) / sum((x - mx) ** 2 for x in boyutlar)
    return {"a": 0.0, "b": -m, "r2": 1.0, "tahmin": my + m * (hedef_boyut - mx)}

print(guc_yasasi_uydur([1e6, 1e7, 1e8], [1.5 + 10 * n ** -0.1 for n in (1e6, 1e7, 1e8)], 1.5, 1e9))
```

```test
fn = need("guc_yasasi_uydur")
L = [1.5 + 10 * n ** -0.1 for n in (1e6, 1e7, 1e8)]
r = fn([1e6, 1e7, 1e8], L, 1.5, 1e9)
eq(r["a"], 10.0, "tam güç yasasında a geri bulunur")
eq(r["b"], 0.1, "tam güç yasasında b geri bulunur")
eq(r["r2"], 1.0, "kusursuz uyum")
eq(r["tahmin"], 2.758925, "1.5 + 10·(1e9)^-0.1")
r2 = fn([1, 10, 100, 1000], [3.0, 2.0, 1.4, 1.2], 1.0, 10000)
eq(r2["b"], 0.339794, "gürültülü ölçümde eğim")
eq(r2["a"], 2.04513, "gürültülü ölçümde katsayı")
eq(r2["r2"], 0.996757, "neredeyse doğrusal")
eq(r2["tahmin"], 1.089443, "dış değerleme")
raises(ValueError, fn, [1e6], [2.0], 1.0, 1e7)
raises(ValueError, fn, [1e6, 1e6], [2.0, 1.9], 1.0, 1e7)
raises(ValueError, fn, [1e6, 1e7], [2.0, 0.9], 1.0, 1e7)
raises(ValueError, fn, [1e6, -1e7], [2.0, 1.9], 1.0, 1e7)
raises(ValueError, fn, [1e6, 1e7], [2.0, 1.9], 1.0, 0)
eq(fn([1, 10], [2.0, 1.5], 1.0, 100), {"a": 1.0, "b": 0.30103, "r2": 1.0, "tahmin": 1.25}, "iki nokta yeterli: tam uyum")
eq(fn([10, 100], [2.5, 2.5], 1.0, 1000), {"a": 1.5, "b": 0.0, "r2": 1.0, "tahmin": 2.5}, "sabit kayıpta sst=0 iken r2=1.0")
raises(ValueError, fn, [1e6, 1e7], [2.0, 1.0], 1.0, 1e7)
raises(ValueError, fn, [1e6, 1e7], [2.0, 1.9], -0.5, 1e7)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile('import math\n\ndef guc_yasasi_uydur(boyutlar, kayiplar, E, hedef_boyut):\n    if not isinstance(boyutlar, list) or not isinstance(kayiplar, list) or len(boyutlar) != len(kayiplar) or (len(boyutlar) < 2):\n        raise ValueError(\'eşit uzunlukta en az 2 öğeli listeler gerekli\')\n    for v in boyutlar + kayiplar + [E, hedef_boyut]:\n        if isinstance(v, bool) or not isinstance(v, (int, float)) or (not math.isfinite(v)):\n            raise ValueError(\'değerler sonlu sayı olmalı\')\n    if E < 0 or hedef_boyut <= 0 or any((n <= 0 for n in boyutlar)) or any((l <= E for l in kayiplar)):\n        raise ValueError("boyutlar ve hedef pozitif, kayıplar E\'den büyük, E negatif olmamalı")\n    if len(set(boyutlar)) < 2:\n        raise ValueError(\'en az iki farklı boyut gerekli\')\n    x = [math.log(n) for n in boyutlar]\n    y = [math.log(l - E) for l in kayiplar]\n    mx, my = (sum(x) / len(x), sum(y) / len(y))\n    m = sum(((a - mx) * (b - my) for a, b in zip(x, y))) / sum(((a - mx) ** 2 for a in x))\n    c = my - m * mx\n    sst = sum(((b - my) ** 2 for b in y))\n    sse = sum(((b - (c + m * a)) ** 2 for a, b in zip(x, y)))\n    r2 = 1.0 if sst == 0 else 1.0 - sse / sst\n    a_, b_ = (math.exp(c), -m)\n    return {\'a\': round(a_, 6), \'b\': round(b_, 6), \'r2\': round(r2, 6), \'tahmin\': round(E + a_ * hedef_boyut ** (-b_), 6)}', 'referans', 'exec'), _REF)
_t, _g = _ff(guc_yasasi_uydur, _REF['guc_yasasi_uydur'], ([1000000.0, 10000000.0, 100000000.0], [4.011886431509581, 3.4952623149688797, 3.0848931924611134], 1.5, 1000000000.0), tohum=2655, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (guc_yasasi_uydur): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
import math

def guc_yasasi_uydur(boyutlar, kayiplar, E, hedef_boyut):
    if not isinstance(boyutlar, list) or not isinstance(kayiplar, list) or len(boyutlar) != len(kayiplar) or len(boyutlar) < 2:
        raise ValueError("eşit uzunlukta en az 2 öğeli listeler gerekli")
    for v in boyutlar + kayiplar + [E, hedef_boyut]:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError("değerler sonlu sayı olmalı")
    if E < 0 or hedef_boyut <= 0 or any(n <= 0 for n in boyutlar) or any(l <= E for l in kayiplar):
        raise ValueError("boyutlar ve hedef pozitif, kayıplar E'den büyük, E negatif olmamalı")
    if len(set(boyutlar)) < 2:
        raise ValueError("en az iki farklı boyut gerekli")
    x = [math.log(n) for n in boyutlar]
    y = [math.log(l - E) for l in kayiplar]
    mx, my = sum(x) / len(x), sum(y) / len(y)
    m = sum((a - mx) * (b - my) for a, b in zip(x, y)) / sum((a - mx) ** 2 for a in x)
    c = my - m * mx
    sst = sum((b - my) ** 2 for b in y)
    sse = sum((b - (c + m * a)) ** 2 for a, b in zip(x, y))
    r2 = 1.0 if sst == 0 else 1.0 - sse / sst
    a_, b_ = math.exp(c), -m
    return {"a": round(a_, 6), "b": round(b_, 6), "r2": round(r2, 6), "tahmin": round(E + a_ * hedef_boyut ** (-b_), 6)}
```

```hint
Uydurmayı `ln N` ve `ln(L − E)` üzerinde yap; eğimin eksisi `b`'dir.
```
:::

::: anlat Gerçek deney: Kendi ölçekleme eğrini çıkarmak: beş küçük model, bir tahmin, bir sınama
Final ölçekleme yasasını gerçekten ölçer (indirme yok; GPU varsa kullanılır):

- **Veri:** Pafta ders metinlerinden 400 000 karakter, karakter düzeyinde (sözlük ~150 karakter), %90 eğitim / %10 doğrulama.
- **Modeller:** transformers'ın `LlamaForCausalLM` sınıfıyla **sıfırdan** (rastgele başlatılmış) beş küçük model: 2 katman, genişlik 16, 24, 32, 48, 64. Hepsi aynı adım sayısıyla (600 adım, batch 32, bağlam 64) eğitilir ve doğrulama kaybı ölçülür. $N$ gömme hariç parametre sayısıdır.
- **Güç yasası:** beş $(N, L)$ çifti senin `guc_yasasi_uydur` işlevine verilir ($E = 0$) ve **altıncı**, daha büyük bir modelin (genişlik 96) kaybı önceden tahmin edilir. Sonra o model de eğitilir ve tahmin gerçek kayıpla karşılaştırılır. Ölçekleme yasalarının pratikteki asıl kullanımı budur: büyük eğitime başlamadan sonucu küçük deneylerden kestirmek.
- **Chinchilla:** bu makinenin fp32 matmul hızı ölçülür. %30 verimle bir saatlik hesap bütçesi senin `chinchilla_optimal` işlevine Hoffmann vd. 2022 katsayılarıyla verilir: bu bütçeyle kaç parametreli bir model kaç tokenla eğitilmeli? Bütçe iki katına çıkınca $N^*$ ve $D^*$ birlikte büyümelidir.

**Ek konu — ortaya çıkış metriğe bağlıdır:** Aynı altı modelde iki ölçü hesaplanır: karakter başına doğruluk (sürekli) ve 4 karakterin **hepsinin** doğru tahmin edilmesi (tam eşleşme, eşikli). Karakter doğruluğu en küçükten en büyüğe yalnız ~1.6 kat artar; tam eşleşme ise ~100 kat artar ve küçük modellerde neredeyse sıfırdır. Tam eşleşme kabaca $p^k$ gibi davrandığı için, kayıp düzgün düşerken yetenek "aniden ortaya çıkmış" görünür (Schaeffer vd. 2023). Bu, gerçek yetenek sıçramalarının hiç olmadığı anlamına gelmez; ama bir sıçrama iddiası her zaman sürekli bir ölçüyle de kontrol edilmelidir.

**Güvenlik yönü — yetenekler geç ve ani görünebilir (grokking):** Küçük bir ağ modüler toplamayı ($a + b \bmod 59$, örneklerin %40'ı eğitimde) güçlü weight decay ile öğrenir. Eğitim doğruluğu ~100 adımda %99'a ulaşır, test doğruluğu ise binlerce adım boyunca neredeyse sıfırda kalıp sonra hızla %99'a çıkar (Power vd. 2022). Eğitim metriğine ya da tek bir erken değerlendirmeye bakan biri genellemenin hiç gelmeyeceğini sanırdı. Tehlikeli yetenek değerlendirmeleri (siber saldırı, ikna, kendini kopyalama) bu yüzden eğitim boyunca tekrarlanır ve ölçekleme kararlarına bağlanır (Anthropic RSP, OpenAI Preparedness).

Kabul: iki işlevin farksal taramayı geçmesi; kaybın model büyüdükçe düşmesi; güç yasası uyumunun $R^2 \ge 0.8$ ve $b > 0$ olması; altıncı modelin kaybının en çok %10 hatayla tahmin edilmesi; iki kat bütçede $N^*$, $D^*$'in büyüyüp kaybın düşmesi. Ayrıca 4 karakter tam eşleşmenin büyüme oranı karakter doğruluğununkinin en az 3 katı olmalıdır. Ayrıca eğitim %99'a ulaştıktan sonra test %99'a en az 10 kat daha fazla adımda ulaşmalıdır.

**Kanıt dosyasını oku:** `olcum` (her modelin N'i, kaybı, süresi), `uyum`, `tahmin_kayip`, `gercek_kayip`, `chinchilla`. Soru 1: Bulduğun $b$ neden Kaplan'ın ~0.076'sına yakın ya da uzak? Soru 2: Bütün modeller aynı adımla eğitildi; bu, eğrinin "hesap-optimal" olmadığı anlamına gelir mi? Soru 3: Kaybın düzgün düşmesi, bir yeteneğin aniden "ortaya çıkması" ile nasıl bağdaşır?
:::

::: gorev Gerçek deney · Beş küçük modelle güç yasası, altıncı modelin kaybını önceden tahmin etmek ve Chinchilla bütçesi
Önceki görevlerdeki `chinchilla_optimal`, `guc_yasasi_uydur` işlevlerini buraya birleştir (çözümlerini kopyalayabilirsin). Çalıştır gerçek ölçüm tablosunu gösterir; Kontrol Et önce işlevlerini gizli verilerle ve farksal taramayla sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
ortam: gpu
timeout: 300
```
```starter
import ai_lab
def chinchilla_optimal(hesap_flop, A, B, E, alpha, beta):
    N = (hesap_flop / 120) ** 0.5
    D = 20 * N
    return {'N_opt': round(N), 'D_opt': round(D), 'kayip': E, 'token_parametre_orani': 20.0}

def guc_yasasi_uydur(boyutlar, kayiplar, E, hedef_boyut):
    n = len(boyutlar)
    mx, my = (sum(boyutlar) / n, sum(kayiplar) / n)
    m = sum(((x - mx) * (y - my) for x, y in zip(boyutlar, kayiplar))) / sum(((x - mx) ** 2 for x in boyutlar))
    return {'a': 0.0, 'b': -m, 'r2': 1.0, 'tahmin': my + m * (hedef_boyut - mx)}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_31 as D
    D.goster(chinchilla_optimal, guc_yasasi_uydur)
```
```test
import ai_lab
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('_model', 'karakter_verisi', 'mini_llama', 'kanit_yaz'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
chinchilla_optimal = need("chinchilla_optimal")
guc_yasasi_uydur = need("guc_yasasi_uydur")
# farksal tarama (görev çözümlerinden derlenen referans)
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile('import math\n\ndef chinchilla_optimal(hesap_flop, A, B, E, alpha, beta):\n    for v in (hesap_flop, A, B, E, alpha, beta):\n        if isinstance(v, bool) or not isinstance(v, (int, float)) or (not math.isfinite(v)):\n            raise ValueError(\'argümanlar sonlu sayı olmalı\')\n    if hesap_flop <= 0 or A <= 0 or B <= 0 or (alpha <= 0) or (beta <= 0) or (E < 0):\n        raise ValueError(\'hesap, A, B, alpha, beta pozitif; E negatif olmamalı\')\n    c6 = float(hesap_flop) / 6.0\n    G = (alpha * A / (beta * B)) ** (1.0 / (alpha + beta))\n    N = G * c6 ** (beta / (alpha + beta))\n    D = c6 / N\n    L = E + A / N ** alpha + B / D ** beta\n    return {\'N_opt\': round(N), \'D_opt\': round(D), \'kayip\': round(L, 6), \'token_parametre_orani\': round(D / N, 4)}\n\nimport math\n\ndef guc_yasasi_uydur(boyutlar, kayiplar, E, hedef_boyut):\n    if not isinstance(boyutlar, list) or not isinstance(kayiplar, list) or len(boyutlar) != len(kayiplar) or (len(boyutlar) < 2):\n        raise ValueError(\'eşit uzunlukta en az 2 öğeli listeler gerekli\')\n    for v in boyutlar + kayiplar + [E, hedef_boyut]:\n        if isinstance(v, bool) or not isinstance(v, (int, float)) or (not math.isfinite(v)):\n            raise ValueError(\'değerler sonlu sayı olmalı\')\n    if E < 0 or hedef_boyut <= 0 or any((n <= 0 for n in boyutlar)) or any((l <= E for l in kayiplar)):\n        raise ValueError("boyutlar ve hedef pozitif, kayıplar E\'den büyük, E negatif olmamalı")\n    if len(set(boyutlar)) < 2:\n        raise ValueError(\'en az iki farklı boyut gerekli\')\n    x = [math.log(n) for n in boyutlar]\n    y = [math.log(l - E) for l in kayiplar]\n    mx, my = (sum(x) / len(x), sum(y) / len(y))\n    m = sum(((a - mx) * (b - my) for a, b in zip(x, y))) / sum(((a - mx) ** 2 for a in x))\n    c = my - m * mx\n    sst = sum(((b - my) ** 2 for b in y))\n    sse = sum(((b - (c + m * a)) ** 2 for a, b in zip(x, y)))\n    r2 = 1.0 if sst == 0 else 1.0 - sse / sst\n    a_, b_ = (math.exp(c), -m)\n    return {\'a\': round(a_, 6), \'b\': round(b_, 6), \'r2\': round(r2, 6), \'tahmin\': round(E + a_ * hedef_boyut ** (-b_), 6)}', 'referans', 'exec'), _REF)
_t, _g = _ff(chinchilla_optimal, _REF['chinchilla_optimal'], (6e+18, 400.0, 400.0, 1.7, 0.5, 0.5), tohum=2819, en_cok=600, mod='tam', butce='oto')
kontrol(_t, "farksal tarama (chinchilla_optimal): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(guc_yasasi_uydur, _REF['guc_yasasi_uydur'], ([1000000.0, 10000000.0, 100000000.0], [4.011886431509581, 3.4952623149688797, 3.0848931924611134], 1.5, 1000000000.0), tohum=2655, en_cok=600, mod='tam', butce='oto')
kontrol(_t, "farksal tarama (guc_yasasi_uydur): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
kontrol(guc_yasasi_uydur([1, 10], [2.0, 1.5], 1.0, 100) == {"a": 1.0, "b": 0.30103, "r2": 1.0, "tahmin": 1.25} and guc_yasasi_uydur([10, 100], [2.5, 2.5], 1.0, 1000) == {"a": 1.5, "b": 0.0, "r2": 1.0, "tahmin": 2.5}, "iki nokta ve sabit kayıp sınırları")
def _red31(f, *a):
    try: f(*a); return False
    except ValueError: return True
kontrol(_red31(guc_yasasi_uydur, [1e6], [2.0], 1.0, 1e7) and _red31(guc_yasasi_uydur, [1e6, 1e6], [2.0, 1.9], 1.0, 1e7), "tek nokta ve yinelenen boyut reddedilir")
if not all(checks): stop()
from sandbox import ai_gercek_ai_temel_31 as D
try: r = D.deney(chinchilla_optimal, guc_yasasi_uydur)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r['boyutla_iyilesiyor'] and r['uyum_iyi'], 'kayıp model büyüdükçe düştü; güç yasası uyumu R² ≥ 0.8, b > 0')
kontrol(r['tahmin_tutarli'], 'daha büyük modelin kaybı en çok %10 hatayla önceden tahmin edildi')
kontrol(r['chinchilla_tutarli'], 'iki kat bütçede hesap-optimal N ve D birlikte büyüdü, kayıp düştü')
kontrol(r['ortaya_cikma_metrige_bagli'], 'tam eşleşme ölçüsü karakter doğruluğundan çok daha keskin büyüdü (metriğin yarattığı ortaya çıkış)')
kontrol(r['grokking_goruldu'], "test doğruluğu eğitim doğruluğundan en az 10 kat geç %99'a ulaştı (grokking)")
ai_lab.kanit_yaz("ai-temel-31-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-temel-31", "deney": r})
```
```solution
import ai_lab
import math

def chinchilla_optimal(hesap_flop, A, B, E, alpha, beta):
    for v in (hesap_flop, A, B, E, alpha, beta):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or (not math.isfinite(v)):
            raise ValueError('argümanlar sonlu sayı olmalı')
    if hesap_flop <= 0 or A <= 0 or B <= 0 or (alpha <= 0) or (beta <= 0) or (E < 0):
        raise ValueError('hesap, A, B, alpha, beta pozitif; E negatif olmamalı')
    c6 = float(hesap_flop) / 6.0
    G = (alpha * A / (beta * B)) ** (1.0 / (alpha + beta))
    N = G * c6 ** (beta / (alpha + beta))
    D = c6 / N
    L = E + A / N ** alpha + B / D ** beta
    return {'N_opt': round(N), 'D_opt': round(D), 'kayip': round(L, 6), 'token_parametre_orani': round(D / N, 4)}

def guc_yasasi_uydur(boyutlar, kayiplar, E, hedef_boyut):
    if not isinstance(boyutlar, list) or not isinstance(kayiplar, list) or len(boyutlar) != len(kayiplar) or (len(boyutlar) < 2):
        raise ValueError('eşit uzunlukta en az 2 öğeli listeler gerekli')
    for v in boyutlar + kayiplar + [E, hedef_boyut]:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or (not math.isfinite(v)):
            raise ValueError('değerler sonlu sayı olmalı')
    if E < 0 or hedef_boyut <= 0 or any((n <= 0 for n in boyutlar)) or any((l <= E for l in kayiplar)):
        raise ValueError("boyutlar ve hedef pozitif, kayıplar E'den büyük, E negatif olmamalı")
    if len(set(boyutlar)) < 2:
        raise ValueError('en az iki farklı boyut gerekli')
    x = [math.log(n) for n in boyutlar]
    y = [math.log(l - E) for l in kayiplar]
    mx, my = (sum(x) / len(x), sum(y) / len(y))
    m = sum(((a - mx) * (b - my) for a, b in zip(x, y))) / sum(((a - mx) ** 2 for a in x))
    c = my - m * mx
    sst = sum(((b - my) ** 2 for b in y))
    sse = sum(((b - (c + m * a)) ** 2 for a, b in zip(x, y)))
    r2 = 1.0 if sst == 0 else 1.0 - sse / sst
    a_, b_ = (math.exp(c), -m)
    return {'a': round(a_, 6), 'b': round(b_, 6), 'r2': round(r2, 6), 'tahmin': round(E + a_ * hedef_boyut ** (-b_), 6)}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_31 as D
    D.goster(chinchilla_optimal, guc_yasasi_uydur)
```
```hint
İki görevin çözümlerini olduğu gibi buraya koy.
```
:::

::: anlat Sınır
Bu ders ölçekleme yasalarını, emergence'ı ve grokking'i kavramsal olarak ve tek bir tahminle anlatır; görevler Chinchilla kapalı formunu ve log-log güç yasası uydurmayı yazdırır; final adım küçük modeller eğitip güç yasasını gerçek ölçümlere uydurur, metriğe bağlı ortaya çıkışı aynı modellerde ve grokking'i küçük bir modüler toplama görevinde gösterir. Kaplan ve Chinchilla üsleri belirli veri, mimari ve tokenizer için ölçülmüş ampirik uyumlardır; veri karışımı değişince ya da veri tekrar edilince kayar. Ani 'emergence' çoğu zaman seçilen metriğin (tam eşleşme gibi) süreksizliğinden doğar; sürekli bir metrikle aynı gelişim düzgün görünebilir. Grokking küçük algoritmik veri kümelerinde ve güçlü weight decay ile gözlenmiştir, büyük LLM ön eğitimine doğrudan genellenemez. Düşen kayıp tek başına muhakeme kalitesini ya da güvenli davranışı garanti etmez.

Kaynaklar: [Kaplan vd. 2020 - Scaling Laws for Neural Language Models](https://arxiv.org/abs/2001.08361), [Hoffmann vd. 2022 - Training Compute-Optimal Large Language Models](https://arxiv.org/abs/2203.15556), [Schaeffer vd. 2023 - Are Emergent Abilities of Large Language Models a Mirage?](https://arxiv.org/abs/2304.15004), [Power vd. 2022 - Grokking: Generalization Beyond Overfitting on Small Algorithmic Datasets](https://arxiv.org/abs/2201.02177).
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Sabit bütçede Chinchilla dengesi ($C \approx 6ND$) (30 sn).** "Sabit FLOP bütçesinde yalnız parametre sayısını büyütüp veriyi az tutmak alt-optimaldir; Chinchilla yasası $N$ ve eğitim token sayısı $D$'nin birlikte ölçeklenmesini gösterir, çıkarım maliyeti eklendiğinde ise küçük modeli daha uzun eğitmek (`over-training`) tercih edilir."
2. **Metriğin yarattığı `Emergence` yanılsaması (35 sn).** "Token başı çapraz entropi kaybı ölçekle pürüzsüz bir güç yasası izlerken `tam eşleşme` (`exact match`) gibi kesikli metrikler sıfırdan aniden sıçrıyormuş gibi görünebilir; metrik seçimi gözlenen eğriyi değiştirir."
3. **`Grokking` ve ağırlık çürümesi (`Weight Decay`) (30 sn).** "Küçük cebirsel görevlerde eğitim hatası sıfırlandıktan çok sonra `weight decay` yüksek normlu ezber ağırlıklarını bastırarak düşük normlu genelleme devresini öne çıkarır."
4. **Soru (25 sn).** "Milyarlarca çıkarım isteği alacak bir üretim modelinde neden Chinchilla hesap-optimal noktasından daha küçük ama 5–10 kat fazla tokenla eğitilmiş bir model seçilir?"
:::
