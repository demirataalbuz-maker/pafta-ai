---
id: ai-uretim-35
title: "Bilimsel Değerlendirme Çatısı (Eval Harness): Yansız Pass@k Tahmincisi ve Benchmark Decontamination"
summary: "Kod ve muhakeme modellerini ölçen Chen et al. (HumanEval) düşük varyanslı kombinatorik yansız Pass@k tahmincisi, çoktan seçmeli kıyaslamalarda uzunluk normalize edilmiş Log-Likelihood ve N-gram tabanlı Benchmark Decontamination (Soru Sızıntısı Temizliği)."
esleme: ai-uretim-36, ai-uretim-21, ai-guvence-04
track: ai-uretim
order: 35
duration_minutes: 35
difficulty: orta
xp: 290
prerequisites: [ai-uretim-34]
tags: [evaluation, eval-harness, pass-at-k, decontamination, humaneval, mmlu, benchmark]
---

::: anlat
## Evaluation ve contamination

Bir modelin üretimlerini değerlendirirken örnekleme sayısı, test sızıntısı ve başarı tanımı önemlidir. Bu derste pass@k tahmincisini ve n-gram tabanlı contamination taramasını hesaplayacaksın. Test verisine benzeyen bütün eğitim örnekleri otomatik hile, benzemeyenler de otomatik temiz kabul edilmez.

Bir değerlendirme çatısı (`lm-evaluation-harness`, `EvalPlus`, `SWE-bench`) üç temel sütun üzerinde yükselir:
1. **Yansız `Pass@k` Tahmincisi (`Chen et al., OpenAI Codex / HumanEval`):** Kod ve matematik sorularında sadece $k$ örnek üretip "en az biri geçti mi?" diye bakmak aşırı gürültülüdür (`High Variance`). Bunun yerine $n \ge k$ örnek üretip $c$ doğru sayıdan kombinatorik olasılık hesaplanır!
2. **Uzunluk Normalize Edilmiş `Log-Likelihood` (`MMLU / ARC`):** Çoktan seçmeli testlerde uzun şıkların ham log-olasılık toplamı her zaman daha negatiftir; karakter/bayt uzunluğuna bölerek (`Byte-Length Normalization`) adil seçim yapılır.
3. **`Benchmark Decontamination` (N-Gram Sızıntı Temizliği):** Trilyon tokenlık web taramasında `GSM8K`, `MMLU` veya `HumanEval` test sorularının eğitim verisine sızıp sızmadığı `10-gram / 13-gram` çakışmasıyla taranır ve kirli belgeler derlemden kazınır!

```
┌────────────────────────────────────────────────────────────────────────────┐
│             FRONTIER AI EVALUATION HARNESS & DECONTAMINATION               │
├─────────────────────────────────────┬──────────────────────────────────────┤
│ 1. UNBIASED PASS@K (CHEN ET AL.)    │ 2. N-GRAM DECONTAMINATION            │
│ ─────────────────────────────────── │ ──────────────────────────────────── │
│ • Naif Yöntem: Sadece k örnek üret, │ • Tehlike: Web'den çekilen eğitim    │
│   1 tanesi geçerse 1.0 de -> Yüksek │   verisinde HumanEval/MMLU soruları  │
│   varyans, her koşuda farklı skor!  │   varsa model soruyu ezberler!       │
│ • Doğru Yöntem: n (ör. n=20) örnek  │ • Çözüm (OpenAI / Llama-3):          │
│   üret, geçen c sayısını say:       │   Test sorularındaki tüm N-gram'ları │
│   Pass@k = 1 - C(n - c, k) / C(n, k)│   (ör. 10-gram / 13-gram) indeksle.  │
│ • Çarpım formuyla taşmadan hesapla: │ • Eğitim belgesinde tek bir N-gram   │
│   1 - Π_{i=0..k-1} (n - c - i)/(n-i)│   bile eşleşirse belgeyi KARANTİNAYA │
│                                     │   al ve eğitimden çıkar!             │
└─────────────────────────────────────┴──────────────────────────────────────┘
```

---

### 1. `Chen et al. (Codex)` Kombinatorik Yansız `Pass@k` Tahmincisi

Bir kodlama sorusu için modelden sıcaklık $T = 0.8$ ile $n$ adet (ör. $n = 20$) bağımsız çözüm üretelim ve bunlardan $c$ tanesi birim testleri (`Unit Tests`) geçsin.
Bu $n$ örnek içinden rastgele seçilecek $k$ örneğin **hiçbirinin** doğru olmama olasılığı, $n - c$ yanlış örnek arasından $k$ tane seçme kombinasyonunun tüm $\binom{n}{k}$ seçimlere oranıdır! Dolayısıyla **en az birinin** doğru olma olasılığı (**Yansız `Pass@k` Tahmincisi**):

$$\text{Pass@}k = 1 - \frac{\binom{n - c}{k}}{\binom{n}{k}}$$

- Eğer $n - c < k$ ise (yani yanlışların sayısı $k$'dan azsa), seçilen $k$ örnekten en az biri **kesinlikle doğrudur** ve $\text{Pass@}k = 1.0$ olur!
- Büyük $n$ değerlerinde faktoriyel (`math.factorial`) hesaplamak taşmaya (`Overflow`) yol açabileceği için kesir doğrudan çarpım dizisi olarak sadeleştirilir:

$$\frac{\binom{n - c}{k}}{\binom{n}{k}} = \prod_{i=0}^{k-1} \frac{n - c - i}{n - i} \implies \text{Pass@}k = 1.0 - \prod_{i=0}^{k-1} \left(1.0 - \frac{c}{n - i}\right)$$

```python
# n=10 örnekten c=2 tanesi doğruysa Pass@1, Pass@3 ve Pass@5 kaçtır?
def pass_at_k_carpim(n, c, k):
    if n - c < k:
        return 1.0
    yanlis_olasilik = 1.0
    for i in range(k):
        yanlis_olasilik *= (n - c - i) / (n - i)
    return 1.0 - yanlis_olasilik

for k_deger in (1, 3, 5):
    print(f"n=10, c=2 -> Pass@{k_deger} = {pass_at_k_carpim(10, 2, k_deger):.4f}")
```

---

### 2. `N-Gram Benchmark Decontamination`: Soru Sızıntısını Tespit Etmek

Bir model `GSM8K` matematik testinde %95 alıyorsa, gerçekten akıl yürüttüğü için mi yoksa o sorular GitHub ödev depolarından ön-eğitim kümesine sızdığı için mi %95 almıştır?
`GPT-4`, `Llama-3` ve `DeepSeek-V3` teknik raporlarında kullanılan standart temizleme protokolü şöyledir:
1. Metinler küçük harfe çevrilir, noktalama işaretleri temizlenir ve kelimelere (`tokens / words`) ayrılır.
2. Tüm değerlendirme (`Benchmark Test`) sorularından ardışık $N$ kelimelik pencereler (**`N-Grams`**, ör. $N=10$ veya $N=13$) çıkarılarak bir `Hash Set` içine kaydedilir.
3. Eğitim derlemindeki her belge taranır; eğer bir eğitim belgesi test kümesindeki herhangi bir `N-Gram` ile çakışıyorsa, o belge **kirli (`Contaminated`)** olarak işaretlenir ve eğitim kümesinden silinir!

---

### 3. Gerçek PyTorch Üretim Kodu: `LogLikelihoodMultipleChoiceEvaluator`

`lm-evaluation-harness` içinde çoktan seçmeli (`MMLU / HellaSwag / ARC`) soruları bağlam önekini maskeleyip bayt uzunluğuyla normalize ederek puanlayan gerçek PyTorch değerlendirme motoru:

```python norun
import torch
import torch.nn as nn
import torch.nn.functional as F

class MultipleChoiceEvalHarness:
    @staticmethod
    @torch.no_grad()
    def score_choices(
        model: nn.Module,
        prompt_ids: list[int],
        choice_ids_list: list[list[int]],
        choice_byte_lengths: list[int],
        device: torch.device,
    ) -> dict[str, int]:
        raw_logliks = []
        norm_logliks = []
        p_len = len(prompt_ids)

        for c_ids, byte_len in zip(choice_ids_list, choice_byte_lengths):
            full_ids = torch.tensor([prompt_ids + c_ids], dtype=torch.long, device=device)
            logits = model(full_ids)[0]  # (SeqLen, VocabSize)
            log_probs = F.log_softmax(logits, dim=-1)

            # Yalnızca şık (choice) tokenlarının koşullu log-olasılıklarını topla
            choice_lp = 0.0
            for idx, tok_id in enumerate(c_ids):
                pos = p_len - 1 + idx
                choice_lp += log_probs[pos, tok_id].item()

            raw_logliks.append(choice_lp)
            norm_logliks.append(choice_lp / max(1, byte_len))

        return {
            "acc_pred": int( max(range(len(raw_logliks)), key=lambda i: raw_logliks[i]) ),
            "acc_norm_pred": int( max(range(len(norm_logliks)), key=lambda i: norm_logliks[i]) ),
        }
```

**Uygulama sınırı:** Görevler Python ile küçük, denetlenebilir hesaplar yapar. `python norun` blokları PyTorch/GPU tarafını incelemek içindir; bu tezgâhta otomatik çalıştırılıp gerçek training/serving kabulü yapılmaz.

**Birincil kaynak:** [HumanEval / pass@k makalesi](https://arxiv.org/abs/2107.03374). Kaynak, yöntemin ayrıntıları içindir; dersteki küçük örnek ölçülmüş üretim benchmarkı değildir.
:::

::: tahmin Kombinatorik Yansız Pass@k vs Naif Oran
Bir kodlama sorusunda modelden $n = 5$ adet çözüm üretildi ve bunlardan $c = 2$ tanesi birim testleri geçti.
1. $k = 1$ için `Pass@1` değeri kaçtır?
2. $k = 2$ için naif olarak $2 \times (2/5) = 0.80$ tahmin etmek yerine, yansız kombinatorik formül $1 - \frac{\binom{5-2}{2}}{\binom{5}{2}}$ kaç verir?

```python
n, c = 5, 2
pass_1 = 1.0 - ((n - c) / n)
pass_2 = 1.0 - (((n - c) * (n - c - 1)) / (n * (n - 1)))

print(f"Pass@1 = {pass_1:.2f} | Yansiz Pass@2 = {pass_2:.2f}")
```

???

```cikti
Pass@1 = 0.40 | Yansiz Pass@2 = 0.70
```
$k = 1$ için $\text{Pass@}1 = c / n = 2 / 5 = 0.40$'tır. $k = 2$ için toplam $\binom{5}{2} = 10$ olası ikili seçimden, ikisinin de yanlış olduğu seçim sayısı $\binom{3}{2} = 3$'tür. Dolayısıyla en az birinin doğru olma olasılığı $1 - 3/10 = 0.70$ (%70) olur! Naif toplama kesişim olasılığını ihmal ettiği için gerçek başarıyı olduğundan yüksek gösterir.
:::

::: gorev 1 · Sayısal Kararlı Kombinatorik Yansız Pass@k Tahmincisi
Bir değerlendirme kümesindeki sorular için üretilen toplam örnek sayısı (`n_toplam`), her soruda testleri geçen doğru örnek sayıları listesi (`c_dogru_listesi`) ve seçim bütçesi (`k_secim`) verildiğinde her sorunun yansız `Pass@k` değerini ve tüm soruların ortalamasını hesaplayan `yansiz_pass_at_k(n_toplam, c_dogru_listesi, k_secim)` işlevini yaz.

**Girdi Kuralları ve Doğrulama:**
- `n_toplam`: Soru başına üretilen toplam örnek sayısı $n$ (`bool` olmayan `int`, $n \ge 1$).
- `c_dogru_listesi`: Boş olmayan bir `list`. Her elemanı $j$. soruda geçen örnek sayısı $c_j$ (`bool` olmayan `int`, $0 \le c_j \le n$).
- `k_secim`: Değerlendirilecek $k$ bütçesi (`bool` olmayan `int`, $1 \le k \le n$).

**Hesaplama Kuralları:**
1. Her soru $c \in \text{c\_dogru\_listesi}$ için:
   - Eğer $n - c < k$ ise o sorunun skoru tam `1.0` (`float`) olur.
   - Aksi halde faktoriyel taşmasına yol açmadan çarpım formülüyle hesapla:
     $$\text{skor} = 1.0 - \prod_{i=0}^{k-1} \frac{n - c - i}{n - i}$$
2. `soru_skorlari`: Her soru için hesaplanan `Pass@k` skorları listesi (`list[float]`).
3. `ortalama_pass_at_k`: Tüm soruların `Pass@k` skorlarının aritmetik ortalaması (`float`).
4. `tam_cozulen_soru`: Skoru `> 0.0` olan (yani $c_j \ge 1$ olan) soru sayısı (`int`).
5. İşlev şu sözlüğü döndürmelidir:
   `{"soru_skorlari": list[float], "ortalama_pass_at_k": float, "tam_cozulen_soru": int}`
- Geçersiz herhangi bir girdide `ValueError` yükseltilmelidir.

```starter
import math

# KUSURLU BAŞLANGIÇ KODU: Kombinatorik formül yerine min(1.0, k * c / n) yaklaşıklaması yapıyor!
def yansiz_pass_at_k(n_toplam, c_dogru_listesi, k_secim):
    skorlar = [min(1.0, (k_secim * c) / n_toplam) for c in c_dogru_listesi]
    return {
        "soru_skorlari": skorlar,
        "ortalama_pass_at_k": sum(skorlar) / len(skorlar),
        "tam_cozulen_soru": sum(1 for c in c_dogru_listesi if c > 0),
    }

print(yansiz_pass_at_k(n_toplam=10, c_dogru_listesi=[0, 2, 5, 9], k_secim=3))
```
```test
def sinama_passk(f):
    import copy, math, random
    def _tek(n, c, k):
        if n - c < k:
            return 1.0
        p = 1.0
        for i in range(k):
            p *= float(n - c - i) / float(n - i)
        return 1.0 - p
    def _ref(n, clist, k):
        sk = [_tek(n, c, k) for c in clist]
        return {
            "soru_skorlari": sk,
            "ortalama_pass_at_k": sum(sk) / len(sk),
            "tam_cozulen_soru": sum(1 for c in clist if c > 0),
        }
    def _yakin(a, b):
        keys = {"soru_skorlari", "ortalama_pass_at_k", "tam_cozulen_soru"}
        if not isinstance(a, dict) or set(a.keys()) != keys:
            return False
        if type(a["tam_cozulen_soru"]) is not int or a["tam_cozulen_soru"] != b["tam_cozulen_soru"]:
            return False
        if abs(a["ortalama_pass_at_k"] - b["ortalama_pass_at_k"]) > 1e-10:
            return False
        return isinstance(a["soru_skorlari"], list) and len(a["soru_skorlari"]) == len(b["soru_skorlari"]) and all(abs(x - y) <= 1e-10 for x, y in zip(a["soru_skorlari"], b["soru_skorlari"]))
    try:
        cl = [0, 2, 5, 9]
        old = copy.deepcopy(cl)
        out = f(10, cl, 3)
        if cl != old or not _yakin(out, _ref(10, cl, 3)):
            return False
        # c=9, n=10, k=3 -> n - c = 1 < 3 olduğu için tam 1.0 olmalı!
        if out["soru_skorlari"][0] != 0.0 or out["soru_skorlari"][3] != 1.0:
            return False

        # Büyük n (ör. n=1000) taşma ve n=1 sınır testi
        if not _yakin(f(1000, [50, 200], 20), _ref(1000, [50, 200], 20)) or not _yakin(f(1, [0, 1], 1), _ref(1, [0, 1], 1)):
            return False

        rng = random.Random(3501)
        for _ in range(20):
            n = rng.randint(2, 50)
            k = rng.randint(1, n)
            cc = [rng.randint(0, n) for _ in range(rng.randint(1, 8))]
            if not _yakin(f(n, cc, k), _ref(n, cc, k)):
                return False

        bad_cases = [
            (0, [0], 1),
            (5, [], 1),
            (5, [-1], 1),
            (5, [6], 1),
            (5, [2], 0),
            (5, [2], 6),
            (True, [1], 1),
            (5, [True], 1),
            (5, [1], True),
        ]
        for bn, bc, bk in bad_cases:
            try:
                f(bn, bc, bk)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

yansiz_pass_at_k = need("yansiz_pass_at_k")
ok(sinama_passk(yansiz_pass_at_k), "Chen et al. yansız kombinatorik Pass@k tahmincisi ve sınır kontrolleri")
for ad, mut in [
    ("naif k*c/n kullanan", lambda n, c, k: dict(yansiz_pass_at_k(n, c, k), soru_skorlari=[min(1.0, k * ci / n) for ci in c])),
    ("tam çözülen soruyu yanlış sayan", lambda n, c, k: dict(yansiz_pass_at_k(n, c, k), tam_cozulen_soru=0)),
]:
    ok(not sinama_passk(mut), "mutant reddedildi: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef yansiz_pass_at_k(n_toplam, c_dogru_listesi, k_secim):\n    if isinstance(n_toplam, bool) or not isinstance(n_toplam, int) or n_toplam < 1:\n        raise ValueError('n_toplam >= 1 tam sayı olmalı')\n    if isinstance(k_secim, bool) or not isinstance(k_secim, int) or (not 1 <= k_secim <= n_toplam):\n        raise ValueError('k_secim [1, n_toplam] aralığında tam sayı olmalı')\n    if not isinstance(c_dogru_listesi, list) or not c_dogru_listesi:\n        raise ValueError('c_dogru_listesi boş olmayan liste olmalı')\n    for c in c_dogru_listesi:\n        if isinstance(c, bool) or not isinstance(c, int) or (not 0 <= c <= n_toplam):\n            raise ValueError('her c değeri [0, n_toplam] aralığında tam sayı olmalı')\n    skorlar = []\n    for c in c_dogru_listesi:\n        if n_toplam - c < k_secim:\n            skorlar.append(1.0)\n        else:\n            yanlis_oran = 1.0\n            for i in range(k_secim):\n                yanlis_oran *= float(n_toplam - c - i) / float(n_toplam - i)\n            skorlar.append(1.0 - yanlis_oran)\n    return {'soru_skorlari': skorlar, 'ortalama_pass_at_k': sum(skorlar) / float(len(skorlar)), 'tam_cozulen_soru': sum((1 for c in c_dogru_listesi if c > 0))}", 'referans', 'exec'), _REF)
_t, _g = _ff(yansiz_pass_at_k, _REF['yansiz_pass_at_k'], (10, [0, 2, 5, 9], 3), tohum=2772, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (yansiz_pass_at_k): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math

def yansiz_pass_at_k(n_toplam, c_dogru_listesi, k_secim):
    if isinstance(n_toplam, bool) or not isinstance(n_toplam, int) or n_toplam < 1:
        raise ValueError("n_toplam >= 1 tam sayı olmalı")
    if isinstance(k_secim, bool) or not isinstance(k_secim, int) or not (1 <= k_secim <= n_toplam):
        raise ValueError("k_secim [1, n_toplam] aralığında tam sayı olmalı")
    if not isinstance(c_dogru_listesi, list) or not c_dogru_listesi:
        raise ValueError("c_dogru_listesi boş olmayan liste olmalı")

    for c in c_dogru_listesi:
        if isinstance(c, bool) or not isinstance(c, int) or not (0 <= c <= n_toplam):
            raise ValueError("her c değeri [0, n_toplam] aralığında tam sayı olmalı")

    skorlar = []
    for c in c_dogru_listesi:
        if n_toplam - c < k_secim:
            skorlar.append(1.0)
        else:
            yanlis_oran = 1.0
            for i in range(k_secim):
                yanlis_oran *= float(n_toplam - c - i) / float(n_toplam - i)
            skorlar.append(1.0 - yanlis_oran)

    return {
        "soru_skorlari": skorlar,
        "ortalama_pass_at_k": sum(skorlar) / float(len(skorlar)),
        "tam_cozulen_soru": sum(1 for c in c_dogru_listesi if c > 0),
    }

if __name__ == "__main__":
    print(yansiz_pass_at_k(n_toplam=10, c_dogru_listesi=[0, 2, 5, 9], k_secim=3))
```
```hint
Her $c$ değeri için $n - c < k$ ise `1.0` ekle; aksi halde `i in range(k_secim)` döngüsüyle `yanlis_oran *= (n - c - i) / (n - i)` çarpımını oluşturup `1.0 - yanlis_oran` hesapla.
```
:::

::: gorev 2 · N-Gram Tabanlı Benchmark Decontamination (Test Sızıntısı Tarayıcısı)
Eğitim belgeleri listesi (`egitim_belgeleri`) içinde değerlendirme test sorularından (`test_sorulari`) herhangi bir ardışık kelime `n_gram` dizisi sızmış olan kirli belgeleri tespit edip temizleyen `benchmark_sizinti_temizle(egitim_belgeleri, test_sorulari, n_gram)` işlevini yaz.

**Girdi Kuralları ve Doğrulama:**
- `egitim_belgeleri`: Boş olmayan `list[str]`. Her elemanı boş olmayan bir metin dizgisi olmalıdır.
- `test_sorulari`: Boş olmayan `list[str]`. Her elemanı boş olmayan bir metin dizgisi olmalıdır.
- `n_gram`: Ardışık kelime penceresi uzunluğu $N$ (`bool` olmayan `int`, $N \ge 2$).

**Normalizasyon ve Tarama Kuralları:**
1. Bir metni kelimelere ayırırken küçük harfe çevir (`lower()`) ve boşluklardan böl (`split()`).
2. Bir kelime listesinden `kelimeler` ($L$ uzunlukta) çıkarılan `n_gram` kümeleri:
   - Eğer $L < N$ ise o metinden hiç `n_gram` çıkmaz (boş küme).
   - Eğer $L \ge N$ ise tüm `tuple(kelimeler[i : i + N])` ($i = 0, \dots, L - N$) demetleri çıkarılır.
3. Önce tüm `test_sorulari` içindeki benzersiz `n_gram` demetlerinin birleşim kümesini (`test_ngram_havuzu`) oluştur. (En az bir test sorusu $\ge N$ kelime içermelidir; eğer havuz tamamen boş kalırsa `ValueError` yükseltilmelidir).
4. `egitim_belgeleri` içindeki her belgeyi sırasıyla tara:
   - Belgenin `n_gram` demetlerinden **en az biri** `test_ngram_havuzu` içinde varsa, belge **kirli** kabul edilir (`kirli_indisler` listesine belgenin indisi eklenir).
   - Hiçbir `n_gram` çakışması yoksa belge `temiz_belgeler` listesine (orijinal metin haliyle) eklenir.
5. `sizinti_orani`: Kirli belge sayısının toplam eğitim belgesi sayısına oranı (`float`).
6. İşlev şu sözlüğü döndürmelidir:
   `{"temiz_belgeler": list[str], "kirli_indisler": list[int], "sizinti_orani": float, "test_ngram_sayisi": int}`
- Geçersiz herhangi bir girdide `ValueError` yükseltilmelidir.

```starter
# KUSURLU BAŞLANGIÇ KODU: N-gram penceresi yerine yalnızca tam cümle eşitliğine bakıyor!
def benchmark_sizinti_temizle(egitim_belgeleri, test_sorulari, n_gram):
    test_set = set(s.lower().strip() for s in test_sorulari)
    temiz, kirli = [], []
    for idx, b in enumerate(egitim_belgeleri):
        if b.lower().strip() in test_set:
            kirli.append(idx)
        else:
            temiz.append(b)
    return {
        "temiz_belgeler": temiz,
        "kirli_indisler": kirli,
        "sizinti_orani": len(kirli) / len(egitim_belgeleri),
        "test_ngram_sayisi": len(test_set),
    }

egitim = [
    "Python dilinde liste siralama algoritmalari cok hizlidir",
    "Odev cozumu: bir dizideki en buyuk iki sayinin toplamini donen islevi yaz",
    "Derin ogrenme modellerinde katman normalizasyonu gradyanlari dengeler",
]
test = [
    "Soru 1: bir dizideki en buyuk iki sayinin toplamini hesaplayan algoritma",
]
print(benchmark_sizinti_temizle(egitim, test, n_gram=5))
```
```test
def sinama_decontam(f):
    import copy, random
    def _ngrams(txt, n):
        w = txt.lower().split()
        return {tuple(w[i : i + n]) for i in range(len(w) - n + 1)} if len(w) >= n else set()
    def _ref(eg, ts, n):
        havuz = set()
        for s in ts:
            havuz |= _ngrams(s, n)
        if not havuz:
            raise ValueError("boş test ngram havuzu")
        temiz, kirli = [], []
        for idx, b in enumerate(eg):
            if _ngrams(b, n) & havuz:
                kirli.append(idx)
            else:
                temiz.append(b)
        return {
            "temiz_belgeler": temiz,
            "kirli_indisler": kirli,
            "sizinti_orani": len(kirli) / float(len(eg)),
            "test_ngram_sayisi": len(havuz),
        }
    try:
        eg = [
            "Python dilinde liste siralama algoritmalari cok hizlidir",
            "Odev cozumu: bir dizideki en buyuk iki sayinin toplamini donen islevi yaz",
            "Derin ogrenme modellerinde katman normalizasyonu gradyanlari dengeler",
        ]
        ts = ["Soru 1: bir dizideki en buyuk iki sayinin toplamini hesaplayan algoritma"]
        old = (copy.deepcopy(eg), copy.deepcopy(ts))
        out = f(eg, ts, 5)
        if (eg, ts) != old or out != _ref(eg, ts, 5):
            return False
        if out["kirli_indisler"] != [1] or len(out["temiz_belgeler"]) != 2:
            return False

        rng = random.Random(3502)
        kelime_havuzu = ["alfa", "beta", "gama", "delta", "epsilon", "zeta", "eta", "teta", "iota", "kapa"]
        for _ in range(15):
            n = rng.randint(2, 4)
            ts_r = [" ".join(rng.choice(kelime_havuzu) for _ in range(rng.randint(n, 7))) for _ in range(2)]
            eg_r = [" ".join(rng.choice(kelime_havuzu) for _ in range(rng.randint(2, 8))) for _ in range(5)]
            if f(eg_r, ts_r, n) != _ref(eg_r, ts_r, n):
                return False

        bad_cases = [
            ([], ts, 3),
            (eg, [], 3),
            ([""], ts, 3),
            (["   "], ts, 3),
            (eg, ["   ", ts[0]], 3),
            (eg, ["kisa metin"], 5),   # test sorusundan hiç 5-gram çıkmıyor!
            (eg, ts, 1),
            (eg, ts, True),
            ([123], ts, 3),
        ]
        for be, bt, bn in bad_cases:
            try:
                f(be, bt, bn)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

benchmark_sizinti_temizle = need("benchmark_sizinti_temizle")
ok(sinama_decontam(benchmark_sizinti_temizle), "N-gram soru sızıntısı taraması, kirli belge filtreleme ve sızıntı oranı")
for ad, mut in [
    ("büyük/küçük harf duyarlı arayan", lambda e, t, n: dict(benchmark_sizinti_temizle(e, t, n), test_ngram_sayisi=0)),
    ("kirli belgeyi temiz listeye de ekleyen", lambda e, t, n: dict(benchmark_sizinti_temizle(e, t, n), temiz_belgeler=list(e))),
]:
    ok(not sinama_decontam(mut), "mutant reddedildi: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def _ngram_kumesi(metin, n):\n    kelimeler = metin.lower().split()\n    if len(kelimeler) < n:\n        return set()\n    return {tuple(kelimeler[i:i + n]) for i in range(len(kelimeler) - n + 1)}\n\ndef benchmark_sizinti_temizle(egitim_belgeleri, test_sorulari, n_gram):\n    if isinstance(n_gram, bool) or not isinstance(n_gram, int) or n_gram < 2:\n        raise ValueError('n_gram >= 2 tam sayı olmalı')\n    if not isinstance(egitim_belgeleri, list) or not egitim_belgeleri:\n        raise ValueError('egitim_belgeleri boş olmayan liste olmalı')\n    if not isinstance(test_sorulari, list) or not test_sorulari:\n        raise ValueError('test_sorulari boş olmayan liste olmalı')\n    for b in egitim_belgeleri:\n        if not isinstance(b, str) or not b.strip():\n            raise ValueError('her eğitim belgesi boş olmayan str olmalı')\n    for s in test_sorulari:\n        if not isinstance(s, str) or not s.strip():\n            raise ValueError('her test sorusu boş olmayan str olmalı')\n    test_havuzu = set()\n    for soru in test_sorulari:\n        test_havuzu |= _ngram_kumesi(soru, n_gram)\n    if not test_havuzu:\n        raise ValueError('test sorularından hiçbir n-gram çıkarılamadı')\n    temiz_belgeler = []\n    kirli_indisler = []\n    for idx, belge in enumerate(egitim_belgeleri):\n        belge_ngram = _ngram_kumesi(belge, n_gram)\n        if belge_ngram & test_havuzu:\n            kirli_indisler.append(idx)\n        else:\n            temiz_belgeler.append(belge)\n    return {'temiz_belgeler': temiz_belgeler, 'kirli_indisler': kirli_indisler, 'sizinti_orani': len(kirli_indisler) / float(len(egitim_belgeleri)), 'test_ngram_sayisi': len(test_havuzu)}", 'referans', 'exec'), _REF)
_t, _g = _ff(benchmark_sizinti_temizle, _REF['benchmark_sizinti_temizle'], (['Python dilinde liste siralama algoritmalari cok hizlidir', 'Odev cozumu: bir dizideki en buyuk iki sayinin toplamini donen islevi yaz', 'Derin ogrenme modellerinde katman normalizasyonu gradyanlari dengeler'], ['Soru 1: bir dizideki en buyuk iki sayinin toplamini hesaplayan algoritma'], 5), tohum=3727, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (benchmark_sizinti_temizle): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
def _ngram_kumesi(metin, n):
    kelimeler = metin.lower().split()
    if len(kelimeler) < n:
        return set()
    return {tuple(kelimeler[i : i + n]) for i in range(len(kelimeler) - n + 1)}

def benchmark_sizinti_temizle(egitim_belgeleri, test_sorulari, n_gram):
    if isinstance(n_gram, bool) or not isinstance(n_gram, int) or n_gram < 2:
        raise ValueError("n_gram >= 2 tam sayı olmalı")
    if not isinstance(egitim_belgeleri, list) or not egitim_belgeleri:
        raise ValueError("egitim_belgeleri boş olmayan liste olmalı")
    if not isinstance(test_sorulari, list) or not test_sorulari:
        raise ValueError("test_sorulari boş olmayan liste olmalı")

    for b in egitim_belgeleri:
        if not isinstance(b, str) or not b.strip():
            raise ValueError("her eğitim belgesi boş olmayan str olmalı")
    for s in test_sorulari:
        if not isinstance(s, str) or not s.strip():
            raise ValueError("her test sorusu boş olmayan str olmalı")

    test_havuzu = set()
    for soru in test_sorulari:
        test_havuzu |= _ngram_kumesi(soru, n_gram)

    if not test_havuzu:
        raise ValueError("test sorularından hiçbir n-gram çıkarılamadı")

    temiz_belgeler = []
    kirli_indisler = []
    for idx, belge in enumerate(egitim_belgeleri):
        belge_ngram = _ngram_kumesi(belge, n_gram)
        if belge_ngram & test_havuzu:
            kirli_indisler.append(idx)
        else:
            temiz_belgeler.append(belge)

    return {
        "temiz_belgeler": temiz_belgeler,
        "kirli_indisler": kirli_indisler,
        "sizinti_orani": len(kirli_indisler) / float(len(egitim_belgeleri)),
        "test_ngram_sayisi": len(test_havuzu),
    }

if __name__ == "__main__":
    egitim = [
        "Python dilinde liste siralama algoritmalari cok hizlidir",
        "Odev cozumu: bir dizideki en buyuk iki sayinin toplamini donen islevi yaz",
        "Derin ogrenme modellerinde katman normalizasyonu gradyanlari dengeler",
    ]
    test = [
        "Soru 1: bir dizideki en buyuk iki sayinin toplamini hesaplayan algoritma",
    ]
    print(benchmark_sizinti_temizle(egitim, test, n_gram=5))
```
```hint
Her metni `metin.lower().split()` ile kelimelere ayırıp `tuple(kelimeler[i:i+n_gram])` pencerelerini kümeye ekle. Eğitim belgesinin kümesi ile `test_havuzu` kesişimi boş değilse (`belge_ngram & test_havuzu`) belgeyi kirli olarak işaretle.
```
:::

::: anlat Gerçek deney: Gerçek kod örneklerinin gerçek testlerde koşturulması, pass@k ve sızıntı tarama
Final değerlendirmenin iki gerçek parçasını yürütür (indirme yok; Ollama yerelde):

- **Gerçek kod, gerçek test:** yerel `llama3.2:3b` modeli beş Python sorusunun her birine $T = 0.8$ ile 8 örnek üretir: asal sayı, noktalama ayıklayan kelime sayacı, Roma rakamı, parantez dengesi, aralık birleştirme. Her örnek **izole bir alt süreçte** (`python -I`, geçici klasör, 10 sn zaman aşımı, kısıtlı ortam değişkenleri) birim testleriyle gerçekten çalıştırılır. Soru başına doğru sayısı $c$, senin `yansiz_pass_at_k` işlevine verilir.
- **Karşılaştırma:** senin tahminin kapalı formla ($1 - \binom{n-c}{k} / \binom{n}{k}$), 4 000 tekrarlı rastgele k-altküme örneklemesiyle ve yalnız ilk k örneğe bakan yanlı tahminle karşılaştırılır.
- **Sızıntı tarama:** Pafta ders metinlerinden 200 gerçek paragrafa üç sızıntı eklenir: test sorusunun birebir kopyası, hafif değiştirilmiş kopyası ve yeniden yazılmış hâli. Senin `benchmark_sizinti_temizle` işlevin $n = 5, 8, 13$ ile çalıştırılır; hangi sızıntının yakalandığı ve kaç temiz paragrafın yanlışlıkla elendiği ölçülür.

Model tarafından üretilen kodu çalıştırmak başlı başına bir güvenlik kararıdır: burada testler kolay ve fonksiyonlar saftır. Gerçek değerlendirme altyapısında ağ, dosya sistemi ve kaynak sınırlı bir sandbox gerekir (ai-uretim-24).

Kabul: iki işlevin farksal taramayı geçmesi; pass@k'nın kapalı formla aynı ve örneklemeyle tutarlı olması; birebir sızıntının $n = 5$ ve 8'de yakalanması; temiz paragraflarda yanlış alarm olmaması; yeniden yazılmış sızıntının hiçbir $n$'de yakalanmaması (n-gram'ın sınırı).

**Kanıt dosyasını oku:** `dogru_sayilari`, `pass_at_k`, `temizleme`, `kisa_n_kapsami`. Soru 1: Yalnız ilk k örneğe bakmak neden yanlı? Soru 2: Yeniden yazılmış sızıntıyı yakalamak için ne yapardın ve bunun yanlış alarm bedeli ne olur? Soru 3: Neden "düşük n-gram çakışması = temiz" denemez?
:::

::: gorev Gerçek deney · llama3.2 kod örneklerinin gerçek testlerle pass@k'sı ve gerçek korpusta sızıntı tarama
Önceki görevlerdeki `yansiz_pass_at_k`, `benchmark_sizinti_temizle` işlevlerini buraya birleştir (çözümlerini kopyalayabilirsin). Çalıştır gerçek ölçüm tablosunu gösterir; Kontrol Et önce işlevlerini gizli verilerle ve farksal taramayla sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
timeout: 300
```
```starter
import ai_lab
import math

def yansiz_pass_at_k(n_toplam, c_dogru_listesi, k_secim):
    skorlar = [min(1.0, k_secim * c / n_toplam) for c in c_dogru_listesi]
    return {'soru_skorlari': skorlar, 'ortalama_pass_at_k': sum(skorlar) / len(skorlar), 'tam_cozulen_soru': sum((1 for c in c_dogru_listesi if c > 0))}

def benchmark_sizinti_temizle(egitim_belgeleri, test_sorulari, n_gram):
    test_set = set((s.lower().strip() for s in test_sorulari))
    temiz, kirli = ([], [])
    for idx, b in enumerate(egitim_belgeleri):
        if b.lower().strip() in test_set:
            kirli.append(idx)
        else:
            temiz.append(b)
    return {'temiz_belgeler': temiz, 'kirli_indisler': kirli, 'sizinti_orani': len(kirli) / len(egitim_belgeleri), 'test_ngram_sayisi': len(test_set)}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_35 as D
    D.goster(yansiz_pass_at_k, benchmark_sizinti_temizle)
```
```test
import ai_lab
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('_calistir', '_paragraflar', 'kanit_yaz'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
yansiz_pass_at_k = need("yansiz_pass_at_k")
benchmark_sizinti_temizle = need("benchmark_sizinti_temizle")
# farksal tarama (görev çözümlerinden derlenen referans)
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef yansiz_pass_at_k(n_toplam, c_dogru_listesi, k_secim):\n    if isinstance(n_toplam, bool) or not isinstance(n_toplam, int) or n_toplam < 1:\n        raise ValueError('n_toplam >= 1 tam sayı olmalı')\n    if isinstance(k_secim, bool) or not isinstance(k_secim, int) or (not 1 <= k_secim <= n_toplam):\n        raise ValueError('k_secim [1, n_toplam] aralığında tam sayı olmalı')\n    if not isinstance(c_dogru_listesi, list) or not c_dogru_listesi:\n        raise ValueError('c_dogru_listesi boş olmayan liste olmalı')\n    for c in c_dogru_listesi:\n        if isinstance(c, bool) or not isinstance(c, int) or (not 0 <= c <= n_toplam):\n            raise ValueError('her c değeri [0, n_toplam] aralığında tam sayı olmalı')\n    skorlar = []\n    for c in c_dogru_listesi:\n        if n_toplam - c < k_secim:\n            skorlar.append(1.0)\n        else:\n            yanlis_oran = 1.0\n            for i in range(k_secim):\n                yanlis_oran *= float(n_toplam - c - i) / float(n_toplam - i)\n            skorlar.append(1.0 - yanlis_oran)\n    return {'soru_skorlari': skorlar, 'ortalama_pass_at_k': sum(skorlar) / float(len(skorlar)), 'tam_cozulen_soru': sum((1 for c in c_dogru_listesi if c > 0))}\n\ndef _ngram_kumesi(metin, n):\n    kelimeler = metin.lower().split()\n    if len(kelimeler) < n:\n        return set()\n    return {tuple(kelimeler[i:i + n]) for i in range(len(kelimeler) - n + 1)}\n\ndef benchmark_sizinti_temizle(egitim_belgeleri, test_sorulari, n_gram):\n    if isinstance(n_gram, bool) or not isinstance(n_gram, int) or n_gram < 2:\n        raise ValueError('n_gram >= 2 tam sayı olmalı')\n    if not isinstance(egitim_belgeleri, list) or not egitim_belgeleri:\n        raise ValueError('egitim_belgeleri boş olmayan liste olmalı')\n    if not isinstance(test_sorulari, list) or not test_sorulari:\n        raise ValueError('test_sorulari boş olmayan liste olmalı')\n    for b in egitim_belgeleri:\n        if not isinstance(b, str) or not b.strip():\n            raise ValueError('her eğitim belgesi boş olmayan str olmalı')\n    for s in test_sorulari:\n        if not isinstance(s, str) or not s.strip():\n            raise ValueError('her test sorusu boş olmayan str olmalı')\n    test_havuzu = set()\n    for soru in test_sorulari:\n        test_havuzu |= _ngram_kumesi(soru, n_gram)\n    if not test_havuzu:\n        raise ValueError('test sorularından hiçbir n-gram çıkarılamadı')\n    temiz_belgeler = []\n    kirli_indisler = []\n    for idx, belge in enumerate(egitim_belgeleri):\n        belge_ngram = _ngram_kumesi(belge, n_gram)\n        if belge_ngram & test_havuzu:\n            kirli_indisler.append(idx)\n        else:\n            temiz_belgeler.append(belge)\n    return {'temiz_belgeler': temiz_belgeler, 'kirli_indisler': kirli_indisler, 'sizinti_orani': len(kirli_indisler) / float(len(egitim_belgeleri)), 'test_ngram_sayisi': len(test_havuzu)}", 'referans', 'exec'), _REF)
_t, _g = _ff(yansiz_pass_at_k, _REF['yansiz_pass_at_k'], (10, [0, 2, 5, 9], 3), tohum=2772, en_cok=600, mod='tam', butce='oto')
kontrol(_t, "farksal tarama (yansiz_pass_at_k): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(benchmark_sizinti_temizle, _REF['benchmark_sizinti_temizle'], (['Python dilinde liste siralama algoritmalari cok hizlidir', 'Odev cozumu: bir dizideki en buyuk iki sayinin toplamini donen islevi yaz', 'Derin ogrenme modellerinde katman normalizasyonu gradyanlari dengeler'], ['Soru 1: bir dizideki en buyuk iki sayinin toplamini hesaplayan algoritma'], 5), tohum=3727, en_cok=600, mod='tam', butce='oto')
kontrol(_t, "farksal tarama (benchmark_sizinti_temizle): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
def _sinir35():
    try:
        if yansiz_pass_at_k(1, [0, 1], 1) != _REF['yansiz_pass_at_k'](1, [0, 1], 1):
            return False
        for fn_, args_ in [(yansiz_pass_at_k, (True, [1], 1)), (benchmark_sizinti_temizle, (['merhaba dunya test'], ['   ', 'merhaba dunya test'], 2))]:
            try:
                fn_(*args_)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
kontrol(_sinir35(), 'n=1 pass@k ve boşluklu test sorusu sınır kontrolleri')
if not all(checks): stop()
from sandbox import ai_gercek_ai_uretim_35 as D
try: r = D.deney(yansiz_pass_at_k, benchmark_sizinti_temizle)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r['pass_ayni'] and r['orneklemle_tutarli'], 'pass@k gerçek doğru sayılarında kapalı formla aynı, örneklemeyle tutarlı')
kontrol(r['birebir_yakalandi'] and r['yanlis_alarm_yok'], "birebir sızıntı n=5 ve 8'de yakalandı, temiz paragraflarda yanlış alarm yok")
kontrol(r['yeniden_yazilmis_kacti'], 'yeniden yazılmış sızıntı n-gram taramasından kaçtı')
ai_lab.kanit_yaz("ai-uretim-35-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-uretim-35", "deney": r})
```
```solution
import ai_lab
import math

def yansiz_pass_at_k(n_toplam, c_dogru_listesi, k_secim):
    if isinstance(n_toplam, bool) or not isinstance(n_toplam, int) or n_toplam < 1:
        raise ValueError('n_toplam >= 1 tam sayı olmalı')
    if isinstance(k_secim, bool) or not isinstance(k_secim, int) or (not 1 <= k_secim <= n_toplam):
        raise ValueError('k_secim [1, n_toplam] aralığında tam sayı olmalı')
    if not isinstance(c_dogru_listesi, list) or not c_dogru_listesi:
        raise ValueError('c_dogru_listesi boş olmayan liste olmalı')
    for c in c_dogru_listesi:
        if isinstance(c, bool) or not isinstance(c, int) or (not 0 <= c <= n_toplam):
            raise ValueError('her c değeri [0, n_toplam] aralığında tam sayı olmalı')
    skorlar = []
    for c in c_dogru_listesi:
        if n_toplam - c < k_secim:
            skorlar.append(1.0)
        else:
            yanlis_oran = 1.0
            for i in range(k_secim):
                yanlis_oran *= float(n_toplam - c - i) / float(n_toplam - i)
            skorlar.append(1.0 - yanlis_oran)
    return {'soru_skorlari': skorlar, 'ortalama_pass_at_k': sum(skorlar) / float(len(skorlar)), 'tam_cozulen_soru': sum((1 for c in c_dogru_listesi if c > 0))}

def _ngram_kumesi(metin, n):
    kelimeler = metin.lower().split()
    if len(kelimeler) < n:
        return set()
    return {tuple(kelimeler[i:i + n]) for i in range(len(kelimeler) - n + 1)}

def benchmark_sizinti_temizle(egitim_belgeleri, test_sorulari, n_gram):
    if isinstance(n_gram, bool) or not isinstance(n_gram, int) or n_gram < 2:
        raise ValueError('n_gram >= 2 tam sayı olmalı')
    if not isinstance(egitim_belgeleri, list) or not egitim_belgeleri:
        raise ValueError('egitim_belgeleri boş olmayan liste olmalı')
    if not isinstance(test_sorulari, list) or not test_sorulari:
        raise ValueError('test_sorulari boş olmayan liste olmalı')
    for b in egitim_belgeleri:
        if not isinstance(b, str) or not b.strip():
            raise ValueError('her eğitim belgesi boş olmayan str olmalı')
    for s in test_sorulari:
        if not isinstance(s, str) or not s.strip():
            raise ValueError('her test sorusu boş olmayan str olmalı')
    test_havuzu = set()
    for soru in test_sorulari:
        test_havuzu |= _ngram_kumesi(soru, n_gram)
    if not test_havuzu:
        raise ValueError('test sorularından hiçbir n-gram çıkarılamadı')
    temiz_belgeler = []
    kirli_indisler = []
    for idx, belge in enumerate(egitim_belgeleri):
        belge_ngram = _ngram_kumesi(belge, n_gram)
        if belge_ngram & test_havuzu:
            kirli_indisler.append(idx)
        else:
            temiz_belgeler.append(belge)
    return {'temiz_belgeler': temiz_belgeler, 'kirli_indisler': kirli_indisler, 'sizinti_orani': len(kirli_indisler) / float(len(egitim_belgeleri)), 'test_ngram_sayisi': len(test_havuzu)}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_35 as D
    D.goster(yansiz_pass_at_k, benchmark_sizinti_temizle)
```
```hint
İki görevin çözümlerini olduğu gibi buraya koy. Ollama çalışmıyorsa deney onu kendisi başlatır.
```
:::

::: anlat Sınır
Görevler sayısal kararlı yansız pass@k tahmincisini ve n-gram tabanlı benchmark decontamination taramasını saf Python ile yazdırır; final adım gerçek bir modelin kod çıktılarını izole alt süreçte çalıştırır. pass@k'nın yansızlığı n ≥ k örnek ve bağımsız örnekleme varsayar; az örnekte varyans yüksektir. N-gram çakışması yeniden yazılmış, çevrilmiş ya da parafraz edilmiş sızıntıyı yakalamaz; düşük çakışma temizlik kanıtı değildir. Testi ezberlemiş bir model yüksek skor alır; bu yüzden zamanla güncellenen ve sızıntıya dayanıklı değerlendirmeler gerekir.

Kaynaklar: [Chen vd. 2021 - Evaluating Large Language Models Trained on Code](https://arxiv.org/abs/2107.03374), [Golchin ve Surdeanu 2023 - Time Travel in LLMs: Tracing Data Contamination in Large Language Models](https://arxiv.org/abs/2308.08493).
:::

::: dusun
**Mimari Soru:** Bir saldırgan veya model üreticisi, `MMLU` veya `GSM8K` test sorularını başka kelimelerle yeniden yazarak (`Paraphrasing / Sentetik Çeviri`) eğitim verisine gömerse, kelimesi kelimesine bakan `13-gram` filtresi bu sızıntıyı yakalayabilir mi? Bunu yakalamak için `MinHash` ve `Embedding Cosine Similarity` tabanlı **Anlamsal Sızıntı Taraması (`Semantic Decontamination`)** nasıl kurulmalıdır?
:::

::: ozet
- **`Pass@k (Chen et al., Codex)`**, $n$ örnek üretip $c$ doğru sayı üzerinden $1 - \binom{n-c}{k} / \binom{n}{k}$ kombinatorik formülüyle düşük varyanslı, yansız başarı tahmini yapar.
- Çoktan seçmeli kıyaslamalarda (`MMLU / ARC`), ham log-olabilirliği şıkların karakter/bayt uzunluğuna bölmek (**`Byte-Length Normalization`**) uzun şık aleyhine olan yanlılığı giderir.
- **`Benchmark Decontamination`**, değerlendirme test sorularındaki tüm `N-Gram` pencerelerini indeksleyerek eğitim derlemine sızmış belgeleri eğitim öncesinde temizler.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Düşük varyanslı yansız `Pass@k` (35 sn).** "Soru başına yalnız $k$ örnek çekmek yüksek varyanslıdır; $n \ge k$ bağımsız örnek üretip geçen $c$ sayıdan $1 - \prod_{i=0}^{k-1} \frac{n-c-i}{n-i}$ çarpımıyla taşmasız ve yansız `Pass@k` hesaplanır."
2. **`N-Gram Benchmark Decontamination` (30 sn).** "Test sorularındaki ardışık $N$ kelimelik pencereler kümelenir; eğitim derleminde tek bir pencere çakışması olan belgeler sızıntı sayılır ve karantinaya alınır."
3. **N-gram temizliğinin sınırı (30 sn).** "Birebir veya hafif kopyalar $N=5..13$ ile yakalanır, ancak kelimeleri değiştirilerek yeniden yazılmış (`paraphrased`) ya da çevrilmiş sızıntılar n-gram taramasından kaçar."
4. **Soru (25 sn).** "Değerlendirme sırasında modelin ürettiği Python kodunu birim testlerle koştururken izole alt süreç ve zaman aşımı kullanmazsak ne tür bir güvenlik riski doğar?"
:::
