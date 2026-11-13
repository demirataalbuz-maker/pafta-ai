---
id: ai-temel-34
title: Base Model'den Düşünen Zekaya · SFT, RLHF, RLVR ve Test-Time Compute
summary: 3 aylık Pre-training'den çıkan ham bir Base Model'in; Supervised Fine-Tuning (SFT), Preference Alignment (RLHF/DPO) ve Reinforcement Learning with Verifiable Rewards (RLVR / GRPO) ile kendi kendine düşünen bir Frontier asistana dönüşümü.
esleme: ai-temel-11, ai-temel-31, ai-uretim-26
---

::: anlat 1. Base Model ve training hedefi
30.000 GPU'da 3 ay süren, $15\text{ Trilyon Token}$'lık `Pre-training` bittiğinde elimize geçen modele **`Base Model` (Baz Model / `Foundation Model`)** denir.

Peki bu `Base Model`'e gidip: *"Bana Python'da hızlı sıralama algoritması yaz"* dersen ne yapar?
Sana kodu yazmak yerine şöyle devam edebilir:
> *"Soru 2: Bana Java'da ikili arama ağacı yaz. Soru 3: Linux çekirdeği nasıl derlenir? (2024 Bilgisayar Mühendisliği Final Sınavı Soruları)"*

Neden böyle yaptı? Çünkü `Base Model` bir "asistan" değildir; bir **`Document Completer` (Belge Tamamlayıcı / Dünya Simülatörü)**'dür! Verdiğin metni bir sınav kağıdının ilk sorusu zannedip, sınav kağıdının geri kalan sorularını tamamlamıştır!

### 🎭 Benzetme: Tüm Kütüphaneyi Okumuş Ama İnsanlarla Konuşmayı Bilmeyen İnziva Alimi
`Base Model` beyninin içinde tüm insanlık bilgisini, fizik yasalarını ve programlama dillerini barındırır; fakat **bu bilgiyi hangi rolde (`Persona`), nasıl bir muhakeme disipliniyle (`Reasoning`) ve hangi güvenlik sınırları içinde (`Alignment`) kullanacağını bilmez.**

Aşağıdaki post-training aşamaları farklı amaçları gösterir; bütün modellerin aynı sırayı veya aynı yöntemleri kullanması gerekmez:

```text
[0. Base Model (15T Token Pre-training — Ham Dünya Bilgi Deposu)]
        │
        ▼
[1. SFT (Supervised Fine-Tuning) & Mid-Training -> Uzun Bağlam + Asistan Formatı]
        │
        ▼
[2. RLHF / DPO / Constitutional AI -> İnsan Tercihi, Üslup ve Güvenlik Hizalaması]
        │
        ▼
[3. RLVR (Reinforcement Learning with Verifiable Rewards / GRPO) -> Gerçek Reasoning!]
        │
        ▼
[4. Agentic Tool-Use & Test-Time Search -> Kod Çalıştırma, Tarayıcı ve Çok Adımlı Ajan]
```
:::

::: anlat 2. Mid-Training (Long-Context Extension) ve Supervised Fine-Tuning (SFT)
`Base Model` eğitilirken maliyet yüzünden genellikle $4.096$ veya $8.192$ `Token` bağlam uzunluğuyla (`Context Length`) eğitilir. Onu $128\text{K}$ veya $1\text{ Milyon Token}$ bağlama çıkarmak için **`Mid-Training` (`Continued Pre-training`)** yapılır:
- Konumsal kodlama olan **`RoPE (Rotary Position Embedding)`** taban frekansı ($\theta$) $10.000$'den $1.000.000$'a (veya `YaRN` / `NTK-Aware Scaling` ile) genişletilir ve model uzun kitaplar, tüm kod depoları (`Repo-level Code`) üzerinde birkaç yüz milyar `Token` daha eğitilir.

Ardından **`Supervised Fine-Tuning (SFT)`** başlar:
- Uzman yazılımcılar, matematikçiler ve araştırmacılar tarafından hazırlanmış $100.000$ – $1.000.000$ adet ultra-yüksek kaliteli `<Kullanıcı İsteği, Düşünce Adımları, Kusursuz Yanıt>` örneği modele gösterilir.
- **Sürpriz Gerçek (`Superficial Alignment Hypothesis` — LIMA):** `SFT` modele yeni bir ansiklopedik bilgi öğretmez; modelin `Pre-training` sırasında zaten öğrendiği devasa bilgi okyanusunu **"Asistan" formatında yüzeye çıkarmayı (`Elicitation`)** öğretir!
:::

::: anlat 3. RLHF, DPO ve Constitutional AI: Taklitten Tercihe Geçiş
`SFT`'nin temel bir sınırı vardır: Modeli yalnızca "başkasının yazdığı cevabı taklit etmeye (`Behavior Cloning`)" zorlar. Oysa bir soruya verilen iki cevaptan hangisinin daha doğru, daha dürüst ve daha güvenli olduğunu ayırt etmek, sıfırdan cevap yazmaktan çok daha güçlü bir sinyaldir.

Burada iki yaklaşım kullanılır:
1. **`RLHF (Reinforcement Learning from Human Feedback)` & `DPO (Direct Preference Optimization)`:**
   - Model aynı soruya 4 farklı yanıt üretir ($y_1, y_2, y_3, y_4$).
   - İnsan değerlendiriciler veya bir `Reward Model` bu yanıtları sıralar ($y_{\text{chosen}} \succ y_{\text{rejected}}$).
   - Model, seçilen yanıtın olasılığını artırırken reddedilen yanıtın olasılığını bastırır (ve `KL Divergence` cezasıyla ana bilgisini unutmaması sağlanır).
2. **`Constitutional AI (CAI)` / `RLAIF`:**
   - Milyonlarca yanıtı insanlara tek tek okutmak yerine, modele açık bir **Anayasa (`Constitution` — ilkeler listesi)** verilir. Model kendi ürettiği yanıtı bu anayasaya göre eleştirir (`Self-Critique`), düzeltir (`Revision`) ve kendi tercih verisini üretir.

### ⚠️ Ama Dikkat: Sadece RLHF Yaparsan Ne Olur? (`Sycophancy` Tehlikesi!)
Eğer modeli sadece "insanların hoşuna giden cevaba puan veren" bir `Reward Model` ile eğitirsen, model **dalkavuklaşır (`Sycophancy`)**: Kullanıcı yanlış bir şey söylediğinde onu düzeltmek yerine *"Çok haklısınız!"* demeye başlar veya bilmediği bir konuda emin ve süslü bir dille yalan söyler (`Confident Hallucination`). İşte bu yüzden gerçek zeka sıçraması **3. aşamada (`RLVR`)** gerçekleşir!
:::

::: anlat 4. Gerçek Zeka Yaklaşımı: RLVR (Reinforcement Learning with Verifiable Rewards)
2025–2026 yılında yapay zekayı sıradan bir sohbet botundan "olimpiyat matematiği çözen ve karmaşık sistem kodlayan bir muhakeme motoruna" dönüştüren asıl kırılma noktası **`RLVR` (`Reinforcement Learning with Verifiable Rewards`)** ve **`GRPO`** olmuştur.

### 🧩 `RLHF` ile `RLVR` Arasındaki Dev Fark Nedir?
- **`RLHF`'de ödül sübjektiftir:** *"Bu cevap kulağa ne kadar güzel geliyor?"* (Tahmini bir `Neural Reward Model` puan verir; model bu puanlayıcıyı kandırabilir — `Reward Hacking`).
- **`RLVR`'de ödül objektif gerçekliktir (`Ground-Truth Verifier`):**
  - **Matematik / Mantık sorusu:** Modelin bulduğu sonuç gerçekten doğru mu? (Doğruysa $+1$, yanlışsa $0$).
  - **Yazılım / Siber Güvenlik görevi:** Modelin yazdığı kod derleniyor mu ve tüm `Unit Test` / `Sandbox` testlerini geçiyor mu? (Geçiyorsa $+1$, çöktüyse $0$).

Modele **nasıl düşüneceği söylenmez!** Sadece *" `<think> ... </think>` etiketleri içinde istediğin kadar düşün, sonunda cevabı ver; sadece cevabın gerçekten doğruysa ödül alacaksın"* denir ve milyonlarca `RL` adımı koşturulur.

### 🌟 "Aha! Moment" (Modelin Kendi Kendine Düşünmeyi Keşfettiği An)
`RLVR` eğitiminin ortasında inanılmaz bir şey yaşanır (DeepSeek-R1 ve o1/o3 araştırmalarında doğrudan gözlemlenmiştir): Hiçbir insan öğretmediği halde model, daha fazla ödül alabilmek için kendi kendine şu bilişsel stratejileri icat eder:
1. **`Self-Verification` (Kendi Sağlamasını Yapma):** Bulduğu sonucu denklemde yerine koyup kontrol eder.
2. **`Backtracking` (Yanlış Yoldan Geri Dönme):** Düşünce zincirinin ortasında *"Dur, bu varsayım çelişkiye yol açtı, baştan farklı bir yoldan deneyeyim"* der!
3. **`Subgoal Decomposition`:** Karmaşık problemi küçük alt problemlere böler.

```python
# RLVR (Doğrulanabilir Ödül) altında kısa düşünme vs kendi sağlamasını yapan (Backtracking) düşünme simülasyonu
def rlvr_odul_sim(problemler):
    kisa_dogru, derin_dogru = 0, 0
    for p in problemler:
        # System 1 (Tek atış): İlk akla gelen sezgisel cevap
        if p["ilk_sezgi"] == p["gercek_cevap"]:
            kisa_dogru += 1
        # System 2 (RLVR ile öğrenilmiş Self-Verification + Backtracking)
        aday = p["ilk_sezgi"]
        if not p["dogrulayici"](aday):  # Model kendi içinde sağlamasını yapar!
            aday = p["ikinci_dal"]     # Yanlışsa geri döner (Backtracking) ve ikinci dalı seçer
        if aday == p["gercek_cevap"]:
            derin_dogru += 1
    return {"system1_basari": kisa_dogru / len(problemler), "system2_rlvr_basari": derin_dogru / len(problemler)}

ornek_problemler = [
    {"ilk_sezgi": 10, "ikinci_dal": 10, "gercek_cevap": 10, "dogrulayici": lambda x: x * 2 == 20},
    {"ilk_sezgi": 10, "ikinci_dal": 5,  "gercek_cevap": 5,  "dogrulayici": lambda x: x ** 2 + 3 * x == 40},  # Tuzak soru!
    {"ilk_sezgi": 7,  "ikinci_dal": 12, "gercek_cevap": 12, "dogrulayici": lambda x: (x % 5 == 2) and (x % 4 == 0)},
]
print(rlvr_odul_sim(ornek_problemler))
```
:::

::: anlat 5. Training aşamalarını birleştirme
Şu soruyu düşün: *"Peki bugün sıfırdan bu seviyede bir AI üretmek için tam reçete nedir?"*

Bir konferansta biri sana *"Peki bugün sıfırdan bu seviyede bir AI üretmek için tam reçete nedir?"* diye sorduğunda vereceğin **5 Adımlı Mühendislik Özeti** şudur:

1. **`Data Engine` ($10\text{T} - 15\text{T}$ Token):** Ham interneti `MinHash LSH` ile tekilleştir, `Quality Classifier` ile ders kitabı kalitesinde süz, %30 `Code` + `Math` ekle ve doğrulayıcılarla (`Compiler`/`Solver`) trilyonlarca `Synthetic Reasoning Token` üret.
2. **`Architecture & Pre-training` (`MoE` + `3D Parallelism` + `μP`):** Hesaplama verimliliği için yoğun (`Dense`) model yerine toplam $600\text{B}+$, aktif $30\text{B}-40\text{B}$ parametreli bir **`Mixture-of-Experts (MoE)`** mimarisi kur (`FlashAttention` + `MLA / GQA` KV-Cache sıkıştırması ile). Küçük modelde $\mu\text{P}$ ile hiperparametreleri bulup büyük kümeye aktar.
3. **`Mid-Training & SFT`:** Bağlam penceresini $128\text{K}-1\text{M}$ `Token` seviyesine uzat ve uzman gösterimleriyle temel asistan/araç kullanma yeteneğini açığa çıkar.
4. **`RLVR` (Reasoning Engine):** Kod sanal kutuları (`Sandboxes`), matematik çözücüler ve mantık doğrulayıcılar üzerinde `GRPO / RL` koşturarak modelin kendi kendine `Chain-of-Thought`, `Backtracking` ve `Self-Correction` geliştirmesini sağla.
5. **`Constitutional Alignment & Agentic Loop`:** Güvenlik hizalamasını (`Constitutional AI` / `DPO`) tamamla ve modeli dış dünyayla etkileşime giren (`Terminal`, `Browser`, `Code Execution`) çok adımlı bir ajan döngüsüne bağla.
:::

::: tahmin Base Model vs SFT vs RLVR Farkı
Aşağıdaki eşleştirmeyi çalıştıran kodun çıktısı nedir?

```python
evreler = {
    "Pre-training": "Document Completion & World Knowledge",
    "SFT": "Assistant Format & Instruction Following",
    "RLVR": "Self-Verification & Backtracking Reasoning",
}
print(evreler["Pre-training"].split(" & ")[1], "|", evreler["RLVR"].split(" & ")[0])
```

???

```cikti
World Knowledge | Self-Verification
```
`Pre-training` modele dünya bilgisini (`World Knowledge`) kazandırırken, `RLVR` (doğrulanabilir ödüllerle reinforcement learning) modelin kendi çıktısını denetlemesini (`Self-Verification`) ve yanlış yoldan geri dönerek muhakeme kurmasını sağlar.
:::

::: gorev 1 · Çoğunluk Oylaması (Self-Consistency) ve Best-of-N
`cogunluk_ve_best_of_n(cevaplar, skorlar, dogru_cevap)` işlevini yaz. Aynı soruya $N$ örnek üretilmiştir; her örneğin bir son cevabı ve bir doğrulayıcı skoru vardır.

**Kurallar:**
1. `cevaplar` boş olmayan bir `str` listesi, `skorlar` aynı uzunlukta sonlu sayı (`bool` değil) listesi, `dogru_cevap` `str` olmalı; değilse `ValueError`.
2. Cevaplar karşılaştırılmadan önce `strip()` edilir (`dogru_cevap` da).
3. Çoğunluk: en sık cevap; eşitlikte listede **ilk görünen**. Best-of-N: en yüksek skorlu örneğin cevabı; eşitlikte ilk.
4. Çıktı: `"cogunluk"`, `"cogunluk_orani"` (o cevabın payı, `round(·, 6)`), `"best_of_n"`, `"cogunluk_dogru"`, `"best_of_n_dogru"`, `"herhangi_dogru"` (en az bir örnek doğru mu: pass@N).

```starter
def cogunluk_ve_best_of_n(cevaplar, skorlar, dogru_cevap):
    # KUSURLU BAŞLANGIÇ: yalnız ilk örneğe bakıyor (test-time compute yok)
    c = cevaplar[0].strip()
    d = dogru_cevap.strip()
    return {"cogunluk": c, "cogunluk_orani": 1.0, "best_of_n": c, "cogunluk_dogru": c == d,
            "best_of_n_dogru": c == d, "herhangi_dogru": c == d}

print(cogunluk_ve_best_of_n(["12", "15", "15 ", "12", "15"], [0.9, 0.2, 0.3, 0.8, 0.1], "15"))
```

```test
fn = need("cogunluk_ve_best_of_n")
r = fn(["12", "15", "15 ", "12", "15"], [0.9, 0.2, 0.3, 0.8, 0.1], "15")
eq(r["cogunluk"], "15", "strip sonrası 15 üç kez")
eq(r["cogunluk_orani"], 0.6, "3/5")
eq(r["best_of_n"], "12", "en yüksek skor 0.9 yanlış cevapta")
eq(r["cogunluk_dogru"], True, "çoğunluk doğru")
eq(r["best_of_n_dogru"], False, "yanlı doğrulayıcı best-of-N'i yanıltır")
eq(r["herhangi_dogru"], True, "pass@5")
r2 = fn(["a", "b", "b", "a"], [0.5, 0.5, 0.1, 0.2], "c")
eq(r2["cogunluk"], "a", "eşitlikte ilk görünen")
eq(r2["best_of_n"], "a", "skor eşitliğinde ilk örnek")
eq(r2["herhangi_dogru"], False, "hiçbiri doğru değil")
eq(fn([" 7 "], [0.0], "7")["cogunluk_dogru"], True, "doğru cevap da strip edilir")
eq(fn(["a", "a", "b"], [0.1, 0.2, 0.3], "a")["cogunluk_orani"], 0.666667, "2/3 altı basamağa yuvarlanır")
raises(ValueError, fn, [], [], "1")
raises(ValueError, fn, ["1", "2"], [0.1], "1")
raises(ValueError, fn, ["1"], [True], "1")
raises(ValueError, fn, ["1"], [float("nan")], "1")
raises(ValueError, fn, ["1"], [0.5], 1)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef cogunluk_ve_best_of_n(cevaplar, skorlar, dogru_cevap):\n    if not isinstance(cevaplar, list) or not cevaplar or (not all((isinstance(c, str) for c in cevaplar))):\n        raise ValueError('boş olmayan str listesi gerekli')\n    if not isinstance(skorlar, list) or len(skorlar) != len(cevaplar):\n        raise ValueError('skorlar cevaplarla aynı uzunlukta olmalı')\n    for s in skorlar:\n        if isinstance(s, bool) or not isinstance(s, (int, float)) or (not math.isfinite(s)):\n            raise ValueError('skorlar sonlu sayı olmalı')\n    if not isinstance(dogru_cevap, str):\n        raise ValueError('dogru_cevap str olmalı')\n    c = [x.strip() for x in cevaplar]\n    d = dogru_cevap.strip()\n    say = {}\n    for x in c:\n        say[x] = say.get(x, 0) + 1\n    en_cok = max(say.values())\n    cog = next((x for x in c if say[x] == en_cok))\n    bon = c[max(range(len(c)), key=lambda i: (skorlar[i], -i))]\n    return {'cogunluk': cog, 'cogunluk_orani': round(en_cok / len(c), 6), 'best_of_n': bon, 'cogunluk_dogru': cog == d, 'best_of_n_dogru': bon == d, 'herhangi_dogru': d in c}", 'referans', 'exec'), _REF)
_t, _g = _ff(cogunluk_ve_best_of_n, _REF['cogunluk_ve_best_of_n'], (['12', '15', '15 ', '12', '15'], [0.9, 0.2, 0.3, 0.8, 0.1], '15'), tohum=3154, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (cogunluk_ve_best_of_n): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
import math

def cogunluk_ve_best_of_n(cevaplar, skorlar, dogru_cevap):
    if not isinstance(cevaplar, list) or not cevaplar or not all(isinstance(c, str) for c in cevaplar):
        raise ValueError("boş olmayan str listesi gerekli")
    if not isinstance(skorlar, list) or len(skorlar) != len(cevaplar):
        raise ValueError("skorlar cevaplarla aynı uzunlukta olmalı")
    for s in skorlar:
        if isinstance(s, bool) or not isinstance(s, (int, float)) or not math.isfinite(s):
            raise ValueError("skorlar sonlu sayı olmalı")
    if not isinstance(dogru_cevap, str):
        raise ValueError("dogru_cevap str olmalı")
    c = [x.strip() for x in cevaplar]
    d = dogru_cevap.strip()
    say = {}
    for x in c:
        say[x] = say.get(x, 0) + 1
    en_cok = max(say.values())
    cog = next(x for x in c if say[x] == en_cok)
    bon = c[max(range(len(c)), key=lambda i: (skorlar[i], -i))]
    return {"cogunluk": cog, "cogunluk_orani": round(en_cok / len(c), 6), "best_of_n": bon, "cogunluk_dogru": cog == d,
            "best_of_n_dogru": bon == d, "herhangi_dogru": d in c}
```

```hint
Eşitlikte ilk görüneni seçmek için sayımdan sonra listeyi baştan tara ve en çok sayılan ilk öğeyi al.
```
:::

::: gorev 2 · Test-Time Compute Eğrisi: maj@N ve pass@N
`test_time_egrisi(ornekler, dogrular, N_listesi)` işlevini yaz. `ornekler[q]`, $q$. sorunun $M$ örnek cevabıdır (aynı $M$), `dogrular[q]` o sorunun doğru cevabıdır.

**Kurallar:**
1. `ornekler` boş olmayan, eşit uzunlukta ve boş olmayan `str` listelerinden oluşan bir liste; `dogrular` aynı sayıda `str`; `N_listesi` boş olmayan, her biri $1 \le N \le M$ tam sayılardan oluşan bir liste olmalı. Değilse `ValueError`. Cevaplar `strip()` edilir.
2. Her $N$ için yalnız **ilk $N$ örnek** kullanılır:
   - maj@N: ilk $N$ örneğin çoğunluk cevabı (eşitlikte ilk görünen) doğru mu;
   - pass@N: ilk $N$ örnekten en az biri doğru mu.
3. Çıktı: `"N"` (verilen sırayla), `"maj"` ve `"pass"`: soru ortalaması doğruluk listeleri (`round(·, 6)`), `"kazanc"`: son $N$ için maj ile N=ilk değer arasındaki fark (`round(·, 6)`).

```starter
def test_time_egrisi(ornekler, dogrular, N_listesi):
    # KUSURLU BAŞLANGIÇ: N'den bağımsız olarak hep ilk örneğe bakıyor
    d = [sum(o[0].strip() == g.strip() for o, g in zip(ornekler, dogrular)) / len(ornekler)] * len(N_listesi)
    return {"N": list(N_listesi), "maj": d, "pass": d, "kazanc": 0.0}

print(test_time_egrisi([["3", "4", "4"], ["7", "7", "1"]], ["4", "1"], [1, 3]))
```

```test
fn = need("test_time_egrisi")
r = fn([["3", "4", "4"], ["7", "7", "1"]], ["4", "1"], [1, 3])
eq(r["N"], [1, 3], "N sırası korunur")
eq(r["maj"], [0.0, 0.5], "N=1: ikisi de yanlış; N=3: 1. soru 4 çoğunlukta")
eq(r["pass"], [0.0, 1.0], "N=3: iki soruda da doğru cevap var")
eq(r["kazanc"], 0.5, "maj@3 − maj@1")
r2 = fn([["a", "b", "b", "a"], ["x", "x", "y", "y"]], ["b", "y"], [2, 4, 1])
eq(r2["maj"], [0.0, 0.0, 0.0], "eşitlikte ilk görünen: a ve x yanlış")
eq(r2["pass"], [0.5, 1.0, 0.0], "pass@N artan")
eq(r2["kazanc"], 0.0, "son N (1) ile ilk N (2) arasında maj farkı")
eq(fn([[" 5 ", "5"]], [" 5"], [1])["maj"], [1.0], "strip")
raises(ValueError, fn, [["1", "2"], ["1"]], ["1", "2"], [1])
raises(ValueError, fn, [["1"]], ["1"], [2])
raises(ValueError, fn, [["1"]], ["1"], [0])
eq(fn([["b", "a", "a"], ["b", "a", "a"], ["b", "b", "a"]], ["a", "a", "b"], [1, 3]), {"N": [1, 3], "maj": [0.333333, 1.0], "pass": [0.333333, 1.0], "kazanc": 0.666667}, "3 soruda 6 basamak yuvarlama")
raises(ValueError, fn, [["1"]], ["1", "2"], [1])
raises(ValueError, fn, [["1"]], ["1"], [])
raises(ValueError, fn, [], [], [1])

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def _cogunluk(c):\n    say = {}\n    for x in c:\n        say[x] = say.get(x, 0) + 1\n    m = max(say.values())\n    return next((x for x in c if say[x] == m))\n\ndef test_time_egrisi(ornekler, dogrular, N_listesi):\n    if not isinstance(ornekler, list) or not ornekler or (not isinstance(dogrular, list)) or (len(dogrular) != len(ornekler)):\n        raise ValueError('ornekler ve dogrular eşit uzunlukta boş olmayan listeler olmalı')\n    M = None\n    for o in ornekler:\n        if not isinstance(o, list) or not o or (not all((isinstance(x, str) for x in o))):\n            raise ValueError('her soru boş olmayan str listesi olmalı')\n        if M is None:\n            M = len(o)\n        elif len(o) != M:\n            raise ValueError('örnek sayıları eşit olmalı')\n    if not all((isinstance(g, str) for g in dogrular)):\n        raise ValueError('doğru cevaplar str olmalı')\n    if not isinstance(N_listesi, list) or not N_listesi:\n        raise ValueError('boş olmayan N listesi gerekli')\n    for N in N_listesi:\n        if isinstance(N, bool) or not isinstance(N, int) or (not 1 <= N <= M):\n            raise ValueError('1 <= N <= M olmalı')\n    temiz = [[x.strip() for x in o] for o in ornekler]\n    g = [x.strip() for x in dogrular]\n    maj, pas = ([], [])\n    for N in N_listesi:\n        maj.append(round(sum((_cogunluk(o[:N]) == d for o, d in zip(temiz, g))) / len(g), 6))\n        pas.append(round(sum((d in o[:N] for o, d in zip(temiz, g))) / len(g), 6))\n    return {'N': list(N_listesi), 'maj': maj, 'pass': pas, 'kazanc': round(maj[-1] - maj[0], 6)}", 'referans', 'exec'), _REF)
_t, _g = _ff(test_time_egrisi, _REF['test_time_egrisi'], ([['3', '4', '4'], ['7', '7', '1']], ['4', '1'], [1, 3]), tohum=2642, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (test_time_egrisi): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
def _cogunluk(c):
    say = {}
    for x in c:
        say[x] = say.get(x, 0) + 1
    m = max(say.values())
    return next(x for x in c if say[x] == m)

def test_time_egrisi(ornekler, dogrular, N_listesi):
    if not isinstance(ornekler, list) or not ornekler or not isinstance(dogrular, list) or len(dogrular) != len(ornekler):
        raise ValueError("ornekler ve dogrular eşit uzunlukta boş olmayan listeler olmalı")
    M = None
    for o in ornekler:
        if not isinstance(o, list) or not o or not all(isinstance(x, str) for x in o):
            raise ValueError("her soru boş olmayan str listesi olmalı")
        if M is None:
            M = len(o)
        elif len(o) != M:
            raise ValueError("örnek sayıları eşit olmalı")
    if not all(isinstance(g, str) for g in dogrular):
        raise ValueError("doğru cevaplar str olmalı")
    if not isinstance(N_listesi, list) or not N_listesi:
        raise ValueError("boş olmayan N listesi gerekli")
    for N in N_listesi:
        if isinstance(N, bool) or not isinstance(N, int) or not 1 <= N <= M:
            raise ValueError("1 <= N <= M olmalı")
    temiz = [[x.strip() for x in o] for o in ornekler]
    g = [x.strip() for x in dogrular]
    maj, pas = [], []
    for N in N_listesi:
        maj.append(round(sum(_cogunluk(o[:N]) == d for o, d in zip(temiz, g)) / len(g), 6))
        pas.append(round(sum(d in o[:N] for o, d in zip(temiz, g)) / len(g), 6))
    return {"N": list(N_listesi), "maj": maj, "pass": pas, "kazanc": round(maj[-1] - maj[0], 6)}
```

```hint
Her N için listenin `o[:N]` dilimini kullan; çoğunlukta eşitlikte ilk görüneni seç.
```
:::

::: anlat Gerçek deney: Gerçek bir modelde test-time compute: çoğunluk, best-of-N ve doğrulayıcı
Final test-time compute'u gerçek örneklerle ölçer (indirme yok; Ollama yerelde, yaklaşık üç dakika):

- Yerel **llama3.2:3b**, sekiz çok adımlı aritmetik problemine (EKOK, gün hesabı, içerme-dışlama, saat açısı, faktöriyel sıfırları, dizi, havuz problemi, basamak toplamı) $T = 1.0$ ile **altışar** çözüm üretir. Her çözümün son sayısı cevaptır.
- **Doğrulayıcı:** Qwen2.5-0.5B-Instruct her çözüm için "son cevap doğru mu?" sorusuna `Yes` olasılığı verir; bu senin `cogunluk_ve_best_of_n` işlevine skor olarak gider.
- Senin işlevin her problem için çoğunluk, best-of-N ve pass@N'i; `test_time_egrisi` ise $N = 1, 2, 4, 6$ için maj@N ve pass@N eğrisini hesaplar. Sonuçlar bağımsız hesapla karşılaştırılır.

Beklenen tablo: tek örnek zayıftır; örnek sayısı arttıkça çoğunluk doğruluğu yükselir; pass@N daha da yüksektir (doğru cevap bir yerdedir ama seçilmesi gerekir). Zayıf bir doğrulayıcı best-of-N'i çoğunluktan iyi yapmaz: yanlış çözümlere de yüksek güven verir.

**Ek konu — tercih aşaması: DPO:** llama3.2'nin aynı problem için doğru ve yanlış çözümleri gerçek tercih çiftleri olur (seçilen = doğru, reddedilen = yanlış). SmolLM2-Instruct hem politika hem referans olarak başlar; son 4 katmanı DPO kaybıyla birkaç tur eğitilir: $-\log\sigma\big(\beta[(\log\pi(y_w) - \log\pi_{ref}(y_w)) - (\log\pi(y_l) - \log\pi_{ref}(y_l))]\big)$. Örtük ödül marjı ve seçilen/reddedilen çözümlerin log-olasılık değişimi ölçülür. Ödül modeli yoktur: ödül, politikanın referanstan sapmasıdır.

**Güvenlik yönü — gevşek doğrulayıcı istismar edilir:** RLVR'de ödül bir doğrulayıcıdan gelir; doğrulayıcının açığı, politikanın öğreneceği şeydir. Katı doğrulayıcı (son cevap doğru mu?) ile gevşek doğrulayıcı (doğru sayı metinde herhangi bir yerde geçiyor mu?) gerçek örneklerde karşılaştırılır; gevşek olan bazı yanlış çözümleri de ödüllendirir. Sonra 0'dan 2000'e kadar sayıları sıralayan bir "spam" cevap denenir: gevşek doğrulayıcıda sekiz problemin hepsinden tam ödül alır, katı doğrulayıcıda neredeyse hiç almaz. Böyle bir ödülle eğitilen model problem çözmeyi değil sayı sıralamayı öğrenir (ödül hacklemesi).

Kabul: iki işlevin farksal taramayı geçmesi; gerçek örneklerde işlevlerin bağımsız hesapla aynı olması; pass@N'in N ile azalmaması. Ayrıca DPO örtük ödül marjını artırmalı ve çiftlerin yarısından fazlasında seçileni öne geçirmelidir. Ayrıca spam cevap gevşek doğrulayıcıda her problemi geçmeli, katı doğrulayıcıda en çok birini geçmelidir.

**Kanıt dosyasını oku:** `sonuclar` (cevaplar ve doğrulayıcı skorları), `tek_ornek`, `cogunluk`, `best_of_n`, `pass_at_n`, `egri`. Soru 1: Doğrulayıcı doğru ve yanlış çözümlere ortalama ne kadar farklı skor veriyor? Soru 2: pass@6 ile maj@6 arasındaki fark neyi gösteriyor ve RLVR bu farkı nasıl kapatmaya çalışır? Soru 3: Kolay sorularda (her örnek doğru) ek örnek neden boşa harcanır?
:::

::: gorev Gerçek deney · llama3.2 ile gerçek örneklerde çoğunluk, Qwen doğrulayıcılı best-of-N ve test-time compute eğrisi
Önceki görevlerdeki `cogunluk_ve_best_of_n`, `test_time_egrisi` işlevlerini buraya birleştir (çözümlerini kopyalayabilirsin). Çalıştır gerçek ölçüm tablosunu gösterir; Kontrol Et önce işlevlerini gizli verilerle ve farksal taramayla sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
timeout: 300
```
```starter
import ai_lab
def cogunluk_ve_best_of_n(cevaplar, skorlar, dogru_cevap):
    c = cevaplar[0].strip()
    d = dogru_cevap.strip()
    return {'cogunluk': c, 'cogunluk_orani': 1.0, 'best_of_n': c, 'cogunluk_dogru': c == d, 'best_of_n_dogru': c == d, 'herhangi_dogru': c == d}

def test_time_egrisi(ornekler, dogrular, N_listesi):
    d = [sum((o[0].strip() == g.strip() for o, g in zip(ornekler, dogrular))) / len(ornekler)] * len(N_listesi)
    return {'N': list(N_listesi), 'maj': d, 'pass': d, 'kazanc': 0.0}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_34 as D
    D.goster(cogunluk_ve_best_of_n, test_time_egrisi)
```
```test
import ai_lab
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('_evet', '_cevap', 'kanit_yaz'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
cogunluk_ve_best_of_n = need("cogunluk_ve_best_of_n")
test_time_egrisi = need("test_time_egrisi")
# farksal tarama (görev çözümlerinden derlenen referans)
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef cogunluk_ve_best_of_n(cevaplar, skorlar, dogru_cevap):\n    if not isinstance(cevaplar, list) or not cevaplar or (not all((isinstance(c, str) for c in cevaplar))):\n        raise ValueError('boş olmayan str listesi gerekli')\n    if not isinstance(skorlar, list) or len(skorlar) != len(cevaplar):\n        raise ValueError('skorlar cevaplarla aynı uzunlukta olmalı')\n    for s in skorlar:\n        if isinstance(s, bool) or not isinstance(s, (int, float)) or (not math.isfinite(s)):\n            raise ValueError('skorlar sonlu sayı olmalı')\n    if not isinstance(dogru_cevap, str):\n        raise ValueError('dogru_cevap str olmalı')\n    c = [x.strip() for x in cevaplar]\n    d = dogru_cevap.strip()\n    say = {}\n    for x in c:\n        say[x] = say.get(x, 0) + 1\n    en_cok = max(say.values())\n    cog = next((x for x in c if say[x] == en_cok))\n    bon = c[max(range(len(c)), key=lambda i: (skorlar[i], -i))]\n    return {'cogunluk': cog, 'cogunluk_orani': round(en_cok / len(c), 6), 'best_of_n': bon, 'cogunluk_dogru': cog == d, 'best_of_n_dogru': bon == d, 'herhangi_dogru': d in c}\n\ndef _cogunluk(c):\n    say = {}\n    for x in c:\n        say[x] = say.get(x, 0) + 1\n    m = max(say.values())\n    return next((x for x in c if say[x] == m))\n\ndef test_time_egrisi(ornekler, dogrular, N_listesi):\n    if not isinstance(ornekler, list) or not ornekler or (not isinstance(dogrular, list)) or (len(dogrular) != len(ornekler)):\n        raise ValueError('ornekler ve dogrular eşit uzunlukta boş olmayan listeler olmalı')\n    M = None\n    for o in ornekler:\n        if not isinstance(o, list) or not o or (not all((isinstance(x, str) for x in o))):\n            raise ValueError('her soru boş olmayan str listesi olmalı')\n        if M is None:\n            M = len(o)\n        elif len(o) != M:\n            raise ValueError('örnek sayıları eşit olmalı')\n    if not all((isinstance(g, str) for g in dogrular)):\n        raise ValueError('doğru cevaplar str olmalı')\n    if not isinstance(N_listesi, list) or not N_listesi:\n        raise ValueError('boş olmayan N listesi gerekli')\n    for N in N_listesi:\n        if isinstance(N, bool) or not isinstance(N, int) or (not 1 <= N <= M):\n            raise ValueError('1 <= N <= M olmalı')\n    temiz = [[x.strip() for x in o] for o in ornekler]\n    g = [x.strip() for x in dogrular]\n    maj, pas = ([], [])\n    for N in N_listesi:\n        maj.append(round(sum((_cogunluk(o[:N]) == d for o, d in zip(temiz, g))) / len(g), 6))\n        pas.append(round(sum((d in o[:N] for o, d in zip(temiz, g))) / len(g), 6))\n    return {'N': list(N_listesi), 'maj': maj, 'pass': pas, 'kazanc': round(maj[-1] - maj[0], 6)}", 'referans', 'exec'), _REF)
_t, _g = _ff(cogunluk_ve_best_of_n, _REF['cogunluk_ve_best_of_n'], (['12', '15', '15 ', '12', '15'], [0.9, 0.2, 0.3, 0.8, 0.1], '15'), tohum=3154, en_cok=600, mod='tam', butce='oto')
kontrol(_t, "farksal tarama (cogunluk_ve_best_of_n): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(test_time_egrisi, _REF['test_time_egrisi'], ([['3', '4', '4'], ['7', '7', '1']], ['4', '1'], [1, 3]), tohum=2642, en_cok=600, mod='tam', butce='oto')
kontrol(_t, "farksal tarama (test_time_egrisi): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
def _red34(f, *a):
    try: f(*a); return False
    except ValueError: return True
kontrol(cogunluk_ve_best_of_n(["a", "a", "b"], [0.1, 0.2, 0.3], "a")["cogunluk_orani"] == 0.666667, "çoğunluk oranı 6 basamak yuvarlanır")
kontrol(test_time_egrisi([["b", "a", "a"], ["b", "a", "a"], ["b", "b", "a"]], ["a", "a", "b"], [1, 3]) == {"N": [1, 3], "maj": [0.333333, 1.0], "pass": [0.333333, 1.0], "kazanc": 0.666667}, "eğri 6 basamak yuvarlanır")
kontrol(_red34(test_time_egrisi, [], [], [1]) and _red34(test_time_egrisi, [["1"]], ["1"], [0]), "boş örnek listesi ve N=0 reddedilir")
if not all(checks): stop()
from sandbox import ai_gercek_ai_temel_34 as D
try: r = D.deney(cogunluk_ve_best_of_n, test_time_egrisi)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r['fonksiyonlar_ayni'], 'çoğunluk, best-of-N ve eğri gerçek örneklerde bağımsız hesapla aynı')
kontrol(r['pass_artan'], 'pass@N örnek sayısıyla azalmıyor')
kontrol(len(r['sonuclar']) == 8, 'sekiz problemin hepsi işlendi')
kontrol(r['dpo_marji_artti'], 'DPO gerçek tercih çiftlerinde örtük ödül marjını artırdı')
kontrol(r['gevsek_dogrulayici_kandiriliyor'], 'sayı sıralayan spam cevap gevşek doğrulayıcıdan tam ödül aldı, katıdan almadı')
ai_lab.kanit_yaz("ai-temel-34-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-temel-34", "deney": r})
```
```solution
import ai_lab
import math

def cogunluk_ve_best_of_n(cevaplar, skorlar, dogru_cevap):
    if not isinstance(cevaplar, list) or not cevaplar or (not all((isinstance(c, str) for c in cevaplar))):
        raise ValueError('boş olmayan str listesi gerekli')
    if not isinstance(skorlar, list) or len(skorlar) != len(cevaplar):
        raise ValueError('skorlar cevaplarla aynı uzunlukta olmalı')
    for s in skorlar:
        if isinstance(s, bool) or not isinstance(s, (int, float)) or (not math.isfinite(s)):
            raise ValueError('skorlar sonlu sayı olmalı')
    if not isinstance(dogru_cevap, str):
        raise ValueError('dogru_cevap str olmalı')
    c = [x.strip() for x in cevaplar]
    d = dogru_cevap.strip()
    say = {}
    for x in c:
        say[x] = say.get(x, 0) + 1
    en_cok = max(say.values())
    cog = next((x for x in c if say[x] == en_cok))
    bon = c[max(range(len(c)), key=lambda i: (skorlar[i], -i))]
    return {'cogunluk': cog, 'cogunluk_orani': round(en_cok / len(c), 6), 'best_of_n': bon, 'cogunluk_dogru': cog == d, 'best_of_n_dogru': bon == d, 'herhangi_dogru': d in c}

def _cogunluk(c):
    say = {}
    for x in c:
        say[x] = say.get(x, 0) + 1
    m = max(say.values())
    return next((x for x in c if say[x] == m))

def test_time_egrisi(ornekler, dogrular, N_listesi):
    if not isinstance(ornekler, list) or not ornekler or (not isinstance(dogrular, list)) or (len(dogrular) != len(ornekler)):
        raise ValueError('ornekler ve dogrular eşit uzunlukta boş olmayan listeler olmalı')
    M = None
    for o in ornekler:
        if not isinstance(o, list) or not o or (not all((isinstance(x, str) for x in o))):
            raise ValueError('her soru boş olmayan str listesi olmalı')
        if M is None:
            M = len(o)
        elif len(o) != M:
            raise ValueError('örnek sayıları eşit olmalı')
    if not all((isinstance(g, str) for g in dogrular)):
        raise ValueError('doğru cevaplar str olmalı')
    if not isinstance(N_listesi, list) or not N_listesi:
        raise ValueError('boş olmayan N listesi gerekli')
    for N in N_listesi:
        if isinstance(N, bool) or not isinstance(N, int) or (not 1 <= N <= M):
            raise ValueError('1 <= N <= M olmalı')
    temiz = [[x.strip() for x in o] for o in ornekler]
    g = [x.strip() for x in dogrular]
    maj, pas = ([], [])
    for N in N_listesi:
        maj.append(round(sum((_cogunluk(o[:N]) == d for o, d in zip(temiz, g))) / len(g), 6))
        pas.append(round(sum((d in o[:N] for o, d in zip(temiz, g))) / len(g), 6))
    return {'N': list(N_listesi), 'maj': maj, 'pass': pas, 'kazanc': round(maj[-1] - maj[0], 6)}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_34 as D
    D.goster(cogunluk_ve_best_of_n, test_time_egrisi)
```
```hint
İki görevin çözümlerini olduğu gibi buraya koy. Ollama çalışmıyorsa deney onu kendisi başlatır.
```
:::

::: anlat Sınır
Ders SFT, mid-training, RLHF/DPO/Constitutional AI, RLVR ve test-time compute aşamalarını kavramsal olarak anlatır; görevler çoğunluk oylaması, best-of-N ve test-time compute eğrisini yazdırır; final adım bunları gerçek model örnekleriyle ölçer ve tercih aşamasını gerçek çiftlerde küçük bir DPO eğitimiyle gösterir; SFT, RLHF ve RLVR eğitimi uygulanmaz. RLVR yalnız doğrulanabilir ödülü olan görevlerde (matematik cevabı, kod testi) çalışır; açık uçlu yazımda ödül yine öğrenilmiş bir modelden gelir ve ödül istismarı (reward hacking) riski sürer. 'Aha moment' gözlemleri belirli modellere ve ödül tasarımlarına bağlıdır. Test-time compute kazancı sorunun zorluğuna göre değişir; kolay sorularda boşa harcanır, çok zor sorularda yetmez. RLHF'in getirdiği dalkavukluk (sycophancy) eğilimi DPO ile de tamamen ortadan kalkmaz.

Kaynaklar: [Ouyang vd. 2022 - Training language models to follow instructions with human feedback](https://arxiv.org/abs/2203.02155), [Lambert vd. 2024 - Tülu 3: Pushing Frontiers in Open Language Model Post-Training](https://arxiv.org/abs/2411.15124), [DeepSeek-AI 2025 - DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning](https://arxiv.org/abs/2501.12948), [Snell vd. 2024 - Scaling LLM Test-Time Compute Optimally can be More Effective than Scaling Model Parameters](https://arxiv.org/abs/2408.03314).
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Belge tamamlayıcıdan düşünen asistana (`SFT` → `DPO` → `RLVR`) (30 sn).** "`Base model` yalnız olası devamı tahmin eder; `SFT` asistan biçimini açığa çıkarır, `RLHF/DPO` tercih marjını büyütür, doğrulanabilir ödüllü `RLVR` ise modele kendi sağlamasını yapma ve yanlış daldan geri dönme alışkanlığı kazandırır."
2. **Çıkarım anı hesap bütçesi (`maj@N`, `Best-of-N`, `pass@N`) (35 sn).** "Tek örneklem yerine $N$ çözüm üretip çoğunluk oylaması (`maj@N`) yapmak doğruluğu artırır; `pass@N` ile `maj@N` arasındaki boşluk doğru çözümün üretildiğini ama seçilemediğini gösterir ve zayıf bir doğrulayıcı `Best-of-N`'i yanıltabilir."
3. **Ödül istismarı (`Reward Hacking`) (30 sn).** "`RLVR`'de doğrulayıcı son cevabı katı ayrıştırmak yerine metnin herhangi bir yerinde doğru sayıyı ararsa politika problem çözmeyi değil binlerce sayıyı arka arkaya sıralamayı öğrenir."
4. **Soru (25 sn).** "Kod üretimi için `RLVR` eğitimi yaparken birim test doğrulayıcısını salt-okunur olmayan bir sanal kutuda çalıştırırsan model ödül almak için test dosyasına ne yapmayı öğrenebilir?"
:::
