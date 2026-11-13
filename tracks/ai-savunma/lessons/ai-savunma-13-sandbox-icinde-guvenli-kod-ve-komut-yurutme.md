---
id: ai-savunma-13
title: Sandbox İçinde Güvenli Kod ve Komut Yürütme
summary: Sandbox profilini doğrula, program ve dosya yollarını sınırlayan yürütme planı üret, süre ve çıktı sınırlarını sonuç raporunda uygula.
timeout: 45
esleme: ai-saldiri-20, ai-ile-guvenlik-08
---

::: anlat Sandbox bir izin listesi ve kaynak bütçesidir

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Kod yürüten ajanlar (Code Interpreter, OpenHands, E2B, Jupyter araçları) modelin komutunu Docker, gVisor, Firecracker ya da nsjail içinde ayrı kullanıcı, kapalı ağ, salt okunur kök ve cgroup sınırlarıyla çalıştırır. `subprocess.run([...], shell=False, timeout=...)` argv'yi kabuksuz geçirir. | Görev 1–3: `veri/profiller.json`, `veri/komut_istekleri.json` ve `veri/yurutme_sonuclari.json` içindeki **sentetik** profiller, istekler ve sonuçlar; yol denetimi `PurePosixPath` ile yapılır. Son adım: kurulu yerel Ollama modelinin `komut_oner` aracıyla ürettiği gerçek komut önerileri; öneriler planlanır, **çalıştırılmaz**. | Gerçek bir konteyner, çekirdek izolasyonu ya da symlink çözümü sınanmaz; `PurePosixPath` diske bakmaz. İki senaryo bir oran vermez. İzinli bir program (ör. `python`) argümanlarıyla yine zararlı iş yapabilir; program izin listesi tek başına yeterli değildir. |

> [!NOT]
> Görev 1–3 sentetik veriyle çalışır. Bu görevlerde model, ağ ve komut yürütme yoktur. Son adımdaki **Gerçek deney** görevi yalnız kurulu yerel Ollama modelini kullanır ve önerilen komutları hiçbir adımda çalıştırmaz. `veri/` dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalanır; kopyada yaptığın değişiklik bir sonraki çalıştırmada sıfırlanır, **kalıcılık yoktur**. Kontrol bu dosyalardan ayrı, gizli verilerle sınar.

Modelin ürettiği komut doğrudan ana sistemde çalıştırılmaz. Ayrı kullanıcı, kapalı ağ, sınırlı dosya sistemi, izinli programlar, süre ve çıktı üst sınırı birlikte uygulanır. Docker ve FastAPI bu politikayı gerçek uygulamada taşıyabilir; bu dersteki işlevler yalnız deterministik plan ve sonuç verilerini işler, komut çalıştırmaz.

Kabuk yorumlayıcısı kullanılmadığı için program ve argümanlar ayrı öğeler olarak taşınır. İzinli olmayan program, sandbox kökü dışındaki çalışma dizini ve kökten kaçan dosya yolu plan aşamasında reddedilir. Son adımda da yalnız plan üretilir; modelin önerdiği komut çalıştırılmaz.

**Saldırgan ne dener?** Kod yürüten bir ajanı ele geçiren istem, modelden zararsız görünen bir komut ister. Bu komut şunları yapabilir:

- `curl ... | sh` ile dışarıdan betik indirmek.
- `bash -c` ile kabuk açmak.
- `../../etc/shadow` gibi bir yolla sandbox dışına okumak.
- Çalışma dizinini `/sandbox/../etc` yapmak.

Program izin listesi varsa saldırgan izinli programı kötüye kullanır: `python -c "import os; ..."` ya da uzun süre dönen, devasa çıktı üreten bir betik. Amaç ya veriyi sızdırmak ya da süre ve çıktı bütçesini tüketip servisi düşürmektir.

**Savunma neden kırılır?**
- Yolu dizge önekiyle denetlemek `/sandboxx/is` ve `/sandbox/../etc` yollarını içeride sayar.
- Göreli yoldaki `..` parçasını aramamak gezintiyi açar.
- Ağı `if not profil["ag"]` gibi doğruluk denetimiyle kapatmak `0` ya da boş dize gibi değerleri "kapalı" sayar.
- Son sonuç raporunda sınıra eşit değeri ihlal saymak ya da negatif çıkış kodunu başarı sanmak, ölçümü güvenilmez kılar.
- Sandbox profili, plan ve sonuç ayrı katmanlardır; biri hata yaparsa diğeri yakalamalıdır.

**Görev 1'de sık tuzaklar:** Kökün yalnız `/` ile başlamasına bakmak sistem kökünü ve `..` içeren kökü kabul eder (`veri/profiller.json`, `f-04`, `f-05`). `ag=0` değeri `False` ile eşittir ama bool değildir; `is False` denetimi gerekir (`f-03`). Sınırları denetlemeyen profil, 10 saniyelik ya da sınırsız çıktılı bir yürütmeye izin verir (`f-08`).
:::

::: anlat Yol kökün altında görünse bile üst dizine çıkabilir
Bir yolun metin olarak `/sandbox` ile başlaması güvenli olduğunu kanıtlamaz. `..` parçası kök dışına çıkabilir. Bu derste çalışma dizini normalize edilmiş mutlak POSIX yolu olmalı, dosya yolları ise göreli olmalı ve hiçbirinde `..` veya ters eğik çizgi bulunmamalıdır.
:::

::: tahmin Kök ve üst dizin denetimi
Üç çıktı satırını yaz:

```python
from pathlib import PurePosixPath
kok = PurePosixPath("/sandbox")
def guvenli(yol):
    p = PurePosixPath(yol)
    return p.is_absolute() and ".." not in p.parts and (p == kok or kok in p.parents)
for yol in ["/sandbox/is", "/sandbox/../etc", "/tmp/is"]:
    print(guvenli(yol))
```

???

```cikti
True
False
False
```

İlk yol kök içindedir. İkinci yol metinsel olarak kökle başlasa da üst dizine çıkar; üçüncü yol ise doğrudan kök dışındadır.
:::

::: gorev 1 · Kapalı sandbox profilini doğrula
`sandbox_profili_dogrula(profil)` işlevini yaz. Profil tam olarak `kullanici`, `ag`, `kok`, `izinli_programlar`, `max_sure_ms`, `max_cikti_bayt` alanlarını taşısın. Kullanıcı yalnız `sandbox`, ağ gerçek bool `False` olmalıdır.

Kök `/` olmayan, başı/sonu boşluksuz, ters eğik çizgi ve `.`/`..` parçası içermeyen normalize edilmiş mutlak POSIX yoludur; sonunda eğik çizgi olamaz. Programlar `python`, `echo`, `hesap` değerlerinden oluşan boş olmayan ve yinelenmeyen listedir. Süre bool olmayan 1–5000 arası int, çıktı sınırı bool olmayan 1–65536 arası int olmalıdır. Geçersiz veride `ValueError` yükselt.

Profili yeni nesneler olarak döndür; girdiyi değiştirme.

Görünür veri: `veri/profiller.json`. Her profilin `beklenen` alanı vardır; `null`, `ValueError` demektir.

```starter
from ai_savunma_veri import json_yukle

def sandbox_profili_dogrula(profil):
    # KUSURLU BAŞLANGIÇ KODU: ağı doğruluk değeriyle denetliyor (ag=0 kapalı sayılır), kökün yalnız "/" ile başlamasına bakıyor ("/" ve "/sandbox/../etc" geçer), programları ve süre/çıktı sınırlarını doğrulamıyor ve girdiyi kopyalamadan döndürüyor!
    if profil.get("kullanici") != "sandbox":
        raise ValueError("kullanıcı geçersiz")
    if profil.get("ag"):
        raise ValueError("ağ açık")
    if not str(profil.get("kok", "")).startswith("/"):
        raise ValueError("kök mutlak değil")
    return profil

veri = json_yukle("veri/profiller.json")
for o in veri["ornekler"]:
    try:
        sonuc = sandbox_profili_dogrula(o["profil"])
    except ValueError:
        sonuc = None
    except Exception as hata:
        sonuc = type(hata).__name__
    print(o["id"], "doğru" if sonuc == o["beklenen"] else "YANLIŞ", o["aciklama"])
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-13")
```

```test
import copy
P = {"kullanici": "sandbox", "ag": False, "kok": "/sandbox", "izinli_programlar": ["python", "echo"], "max_sure_ms": 1000, "max_cikti_bayt": 4096}
def sozlesme(fn):
    try:
        once = copy.deepcopy(P)
        sonuc = fn(P)
        if sonuc != P or P != once or sonuc is P or sonuc["izinli_programlar"] is P["izinli_programlar"]:
            return False
        for deger, alan in [(1, "max_sure_ms"), (5000, "max_sure_ms"), (1, "max_cikti_bayt"), (65536, "max_cikti_bayt")]:
            if fn(dict(P, **{alan: deger}))[alan] != deger:
                return False
        for profil in [
            None, [], dict(P, ek=1), dict(P, kullanici="root"), dict(P, ag=True), dict(P, ag=0),
            dict(P, kok=""), dict(P, kok="sandbox"), dict(P, kok="/"), dict(P, kok="/sandbox/"),
            dict(P, kok="/sandbox/../etc"), dict(P, kok="/sandbox/./is"), dict(P, kok="/sandbox\\is"), dict(P, kok=" /sandbox"),
            dict(P, izinli_programlar=[]), dict(P, izinli_programlar=None), dict(P, izinli_programlar=["sh"]),
            dict(P, izinli_programlar=["echo", "echo"]),
            dict(P, max_sure_ms=0), dict(P, max_sure_ms=5001), dict(P, max_sure_ms=True),
            dict(P, max_cikti_bayt=0), dict(P, max_cikti_bayt=65537), dict(P, max_cikti_bayt=False),
        ]:
            try:
                fn(profil)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(sandbox_profili_dogrula), "kullanıcı, kapalı ağ, kök, program ve kaynak sınırları korunmalı")
def m_ag(profil):
    sonuc = sandbox_profili_dogrula(profil)
    sonuc["ag"] = True
    return sonuc
def m_kok(profil):
    sonuc = sandbox_profili_dogrula(profil)
    sonuc["kok"] = "/"
    return sonuc
def m_sure(profil):
    sonuc = sandbox_profili_dogrula(profil)
    sonuc["max_sure_ms"] = 5001
    return sonuc
for ad, mutant in [("ağı açan", m_ag), ("kökü genişleten", m_kok), ("süreyi aşan", m_sure)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

raises(ValueError,sandbox_profili_dogrula,dict(P,kok='/sandbox '),msg='kök yol baş/son boşluğu ret')
# --- carbon-c8-ek-bas ---
raises(ValueError, sandbox_profili_dogrula, dict(P, kullanici=123), msg="kullanıcı str olmalı")
raises(ValueError, sandbox_profili_dogrula, dict(P, kok=123), msg="kök str olmalı")
raises(ValueError, sandbox_profili_dogrula, dict(P, kok="/"), msg="kök '/' olamaz")
raises(ValueError, sandbox_profili_dogrula, dict(P, izinli_programlar=[123]), msg="program str olmalı")
raises(ValueError, sandbox_profili_dogrula, dict(P, max_sure_ms=True), msg="max_sure_ms bool olamaz")
raises(ValueError, sandbox_profili_dogrula, dict(P, max_cikti_bayt=True), msg="max_cikti_bayt bool olamaz")
eq(sandbox_profili_dogrula(dict(P, max_sure_ms=1))["max_sure_ms"], 1, "alt süre sınırı")
eq(sandbox_profili_dogrula(dict(P, max_sure_ms=5000))["max_sure_ms"], 5000, "üst süre sınırı")
eq(sandbox_profili_dogrula(dict(P, max_cikti_bayt=1))["max_cikti_bayt"], 1, "alt bayt sınırı")
eq(sandbox_profili_dogrula(dict(P, max_cikti_bayt=65536))["max_cikti_bayt"], 65536, "üst bayt sınırı")
raises(ValueError, sandbox_profili_dogrula, dict(P, izinli_programlar=("python",)), msg="izinli_programlar tuple olamaz")
# --- carbon-c8-ek-son ---
```

```solution
def sandbox_profili_dogrula(profil):
    from pathlib import PurePosixPath
    if not isinstance(profil, dict) or set(profil) != {"kullanici", "ag", "kok", "izinli_programlar", "max_sure_ms", "max_cikti_bayt"}:
        raise ValueError("profil şeması geçersiz")
    if profil["kullanici"] != "sandbox":
        raise ValueError("ayrı sandbox kullanıcısı zorunlu")
    if profil["ag"] is not False:
        raise ValueError("ağ kapalı olmalı")
    kok = profil["kok"]
    if not isinstance(kok, str):
        raise ValueError("kök metin olmalı")
    if not kok:
        raise ValueError("kök boş olamaz")
    if kok != kok.strip():
        raise ValueError("kök boşluk içeremez")
    if "\\" in kok or kok.endswith("/"):
        raise ValueError("kök normalize edilmeli")
    yol = PurePosixPath(kok)
    if not yol.is_absolute():
        raise ValueError("kök mutlak olmalı")
    if kok == "/":
        raise ValueError("sistem kökü sandbox olamaz")
    if "." in yol.parts or ".." in yol.parts:
        raise ValueError("kök parçaları geçersiz")
    if str(yol) != kok:
        raise ValueError("kök normalize edilmeli")
    programlar = profil["izinli_programlar"]
    if not isinstance(programlar, list):
        raise ValueError("programlar liste olmalı")
    if not programlar:
        raise ValueError("program listesi boş olamaz")
    if len(set(programlar)) != len(programlar):
        raise ValueError("programlar yinelenemez")
    if any(p not in ("python", "echo", "hesap") for p in programlar):
        raise ValueError("program izinli değil")
    if type(profil["max_sure_ms"]) is not int or not 1 <= profil["max_sure_ms"] <= 5000:
        raise ValueError("süre sınırı geçersiz")
    if type(profil["max_cikti_bayt"]) is not int or not 1 <= profil["max_cikti_bayt"] <= 65536:
        raise ValueError("çıktı sınırı geçersiz")
    return {"kullanici": "sandbox", "ag": False, "kok": kok, "izinli_programlar": list(programlar), "max_sure_ms": profil["max_sure_ms"], "max_cikti_bayt": profil["max_cikti_bayt"]}
```

```hint
Önce biçim ve şemayı doğrula. Kökü `PurePosixPath` ile incele; kaynak sınırlarında iki ucu da kapsayan karşılaştırma kullan.
```
:::

::: anlat Yürütme planı politika hatalarını gizlemez
Her istek benzersiz kimlik taşır. Program izinli değilse `program`, çalışma dizini kök dışındaysa `dizin`, herhangi bir dosya göreli ve güvenli değilse `dosya` nedeni eklenir. Nedenler bu sabit sıradadır ve bir istekte birden fazlası bulunabilir.

Geçerli isteğin kararı `hazir`, politika nedeni olan isteğin kararı `reddet` olur. Plan yalnız veri üretir; `hazir` sonucu da tek başına komut çalıştırma yetkisi değildir.

**Çıktı nasıl okunur?** `argv` alanı, kabuk olmadan yürütücüye gidecek tam listedir. `veri/komut_istekleri.json` içindeki `metakarakter` isteği `hazir` çıkar, çünkü `a.py; cat /etc/passwd` tek bir argümandır ve hiçbir kabuk onu iki komuta bölmez. Aynı metni `shell=True` ile çalıştırmak bambaşka bir sonuç verirdi.

**Görev 2'de sık tuzaklar:** `calisma_dizini.startswith(kok)` denetimi `/sandbox/../etc` ve `/sandboxx/is` yollarını kabul eder (`kacis`, `onek`). Dosyada yalnız mutlak yolu aramak `../../etc/shadow` gezintisini kaçırır (`gezinti`). İlk nedende durmak `kabuk` isteğinin üç ayrı ihlalini tek nedene indirir.
:::

::: gorev 2 · Sınırlı komut yürütme planı üret
`komut_plani_uret(istekler, profil)` işlevini yaz. Profil ilk görevdeki bütün kuralları sağlasın. İstekler liste; her istek tam olarak `id`, `program`, `argumanlar`, `calisma_dizini`, `dosyalar` alanlarını taşısın. Kimlik 1–64 karakterlik, ASCII harf/rakamla başlayan ve yalnız ASCII harf, rakam, alt çizgi veya tire içeren benzersiz stringdir.

Program string, argümanlar ve dosyalar liste olmalıdır. Her argüman boş olmayan, en çok 200 karakterlik ve NUL içermeyen stringdir. Her dosya boş olmayan stringdir. Çalışma dizini boş olmayan stringdir. Tür veya şema hatasında `ValueError` yükselt.

Program profil listesinde yoksa `program` ekle. Çalışma dizini normalize edilmiş mutlak POSIX yolu değilse, `.`/`..` içeriyorsa veya kökün kendisi/altı değilse `dizin` ekle. Dosya mutlaksa, normalize değilse, `.`/`..` veya ters eğik çizgi içeriyorsa `dosya` ekle; her dosya yalnız bir neden üretir.

Her kayıt için `{"id":ID,"karar":KARAR,"nedenler":[...],"argv":[program]+argumanlar}` döndür. Kimliğe göre sırala, boş istekte boş liste döndür ve girdileri değiştirme.

Görünür veri: `veri/komut_istekleri.json`. Dosyada profil, dokuz istek, beklenen plan ve dört bozuk girdi vardır.

```starter
from ai_savunma_veri import json_yukle

def komut_plani_uret(istekler, profil):
    # KUSURLU BAŞLANGIÇ KODU: çalışma dizinini dizge önekiyle denetliyor ("/sandbox/../etc" ve "/sandboxx" geçer), dosyada yalnız mutlak yolu yakalıyor ("../secret" geçer), ilk nedende duruyor, girdileri doğrulamıyor ve planı sıralamıyor!
    plan = []
    for istek in istekler:
        if istek["program"] not in profil["izinli_programlar"]:
            nedenler = ["program"]
        elif not istek["calisma_dizini"].startswith(profil["kok"]):
            nedenler = ["dizin"]
        elif any(d.startswith("/") for d in istek["dosyalar"]):
            nedenler = ["dosya"]
        else:
            nedenler = []
        plan.append({"id": istek["id"], "karar": "reddet" if nedenler else "hazir", "nedenler": nedenler, "argv": [istek["program"]] + istek["argumanlar"]})
    return plan

veri = json_yukle("veri/komut_istekleri.json")
try:
    rapor = komut_plani_uret(veri["istekler"], veri["profil"])
except Exception as hata:
    rapor = [{"id": "hata", "hata": type(hata).__name__}]
print("rapor sırası", "doğru" if [r["id"] for r in rapor] == [b["id"] for b in veri["beklenen"]] else "YANLIŞ")
for beklenen in veri["beklenen"]:
    bulunan = next((r for r in rapor if r["id"] == beklenen["id"]), None)
    print(beklenen["id"], "doğru" if bulunan == beklenen else "YANLIŞ", bulunan)
for b in veri["bozuk_girdiler"]:
    try:
        komut_plani_uret(b["girdi"], veri["profil"])
        print(b["id"], "YANLIŞ: kabul edildi", b["aciklama"])
    except ValueError:
        print(b["id"], "doğru: ValueError", b["aciklama"])
    except Exception as hata:
        print(b["id"], "YANLIŞ:", type(hata).__name__, b["aciklama"])
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-13")
```

```test
import copy
P = {"kullanici": "sandbox", "ag": False, "kok": "/sandbox", "izinli_programlar": ["python", "echo"], "max_sure_ms": 1000, "max_cikti_bayt": 4096}
I = [
    {"id": "izin-1", "program": "python", "argumanlar": ["is.py", "--kirik"], "calisma_dizini": "/sandbox/is", "dosyalar": ["is.py", "veri/girdi.txt"]},
    {"id": "ret-1", "program": "sh", "argumanlar": ["-c", "echo test"], "calisma_dizini": "/tmp", "dosyalar": ["../secret"]},
]
BEKLENEN = [
    {"id": "izin-1", "karar": "hazir", "nedenler": [], "argv": ["python", "is.py", "--kirik"]},
    {"id": "ret-1", "karar": "reddet", "nedenler": ["program", "dizin", "dosya"], "argv": ["sh", "-c", "echo test"]},
]
def sozlesme(fn):
    try:
        ionce = copy.deepcopy(I)
        ponce = copy.deepcopy(P)
        if fn(I, P) != BEKLENEN or I != ionce or P != ponce or fn(list(reversed(I)), P) != BEKLENEN or fn([], P) != []:
            return False
        if fn([dict(I[0], calisma_dizini="/sandbox")], P)[0]["karar"] != "hazir":
            return False
        for arguman in ["a", "a" * 200]:
            if fn([dict(I[0], argumanlar=[arguman])], P)[0]["karar"] != "hazir":
                return False
        for alan, deger in [("max_sure_ms", 1), ("max_sure_ms", 5000), ("max_cikti_bayt", 1), ("max_cikti_bayt", 65536)]:
            if fn([], dict(P, **{alan: deger})) != []:
                return False
        for dosya in ["/etc/passwd", "../secret", "is/../../secret", "./is.py", "is\\girdi.txt", "is//girdi.txt"]:
            if fn([dict(I[0], dosyalar=[dosya])], P)[0]["nedenler"] != ["dosya"]:
                return False
        for dizin in ["sandbox", "/tmp", "/sandbox/../etc", "/sandbox/", "/sandbox\\is"]:
            if fn([dict(I[0], calisma_dizini=dizin)], P)[0]["nedenler"] != ["dizin"]:
                return False
        for istekler, profil in [
            (None, P), ({}, P), ([None], P), (I, None), (I, dict(P, ag=True)),
            (I, dict(P, kullanici="root")), (I, dict(P, kok="")), (I, dict(P, kok="/")),
            (I, dict(P, max_sure_ms=0)), (I, dict(P, max_sure_ms=5001)),
            (I, dict(P, max_cikti_bayt=0)), (I, dict(P, max_cikti_bayt=65537)),
            ([dict(I[0], ek=1)], P), ([dict(I[0], id="")], P), ([dict(I[0], id="a b")], P),
            ([dict(I[0], id="a" * 65)], P), ([I[0], I[0]], P),
            ([dict(I[0], program=1)], P), ([dict(I[0], argumanlar=None)], P),
            ([dict(I[0], argumanlar=[""])], P), ([dict(I[0], argumanlar=["a" * 201])], P),
            ([dict(I[0], argumanlar=["a\0b"])], P), ([dict(I[0], calisma_dizini="")], P),
            ([dict(I[0], dosyalar=None)], P), ([dict(I[0], dosyalar=[""])], P),
        ]:
            try:
                fn(istekler, profil)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(komut_plani_uret), "program, çalışma dizini, dosya ve argv sınırları korunmalı")
def m_program(istekler, profil):
    yeni = copy.deepcopy(profil)
    yeni["izinli_programlar"].append("sh")
    return komut_plani_uret(istekler, yeni)
def m_dizin(istekler, profil):
    degisen = [dict(x, calisma_dizini="/sandbox") for x in istekler]
    return komut_plani_uret(degisen, profil)
def m_dosya(istekler, profil):
    degisen = [dict(x, dosyalar=[]) for x in istekler]
    return komut_plani_uret(degisen, profil)
for ad, mutant in [("programı açan", m_program), ("dizini zorlayan", m_dizin), ("dosyayı silen", m_dosya)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

raises(ValueError,komut_plani_uret,I,dict(P,kok='/sandbox '),msg='plan kök yolu baş/son boşluğu ret')
# --- carbon-c8-ek-bas ---
raises(ValueError, komut_plani_uret, I, dict(P, kullanici=123), msg="profil kullanıcı str olmalı")
raises(ValueError, komut_plani_uret, I, dict(P, kullanici="root"), msg="root kullanıcı ret")
raises(ValueError, komut_plani_uret, I, dict(P, ag="evet"), msg="ag bool olmalı")
raises(ValueError, komut_plani_uret, I, dict(P, kok=123), msg="kök str olmalı")
raises(ValueError, komut_plani_uret, I, dict(P, kok="/"), msg="kök '/' ret")
raises(ValueError, komut_plani_uret, I, dict(P, kok="goreli/yol"), msg="göreli kök ret")
raises(ValueError, komut_plani_uret, I, dict(P, kok="/sandbox/../etc"), msg="üst dizinli kök ret")
raises(ValueError, komut_plani_uret, I, dict(P, izinli_programlar=[]), msg="boş program listesi ret")
raises(ValueError, komut_plani_uret, I, dict(P, izinli_programlar="python"), msg="izinli_programlar liste olmalı")
raises(ValueError, komut_plani_uret, I, dict(P, izinli_programlar=[123]), msg="program str olmalı")
raises(ValueError, komut_plani_uret, I, dict(P, izinli_programlar=["python", "python"]), msg="yinelenen program ret")
raises(ValueError, komut_plani_uret, I, dict(P, izinli_programlar=["sh"]), msg="kabuk programı ret")
raises(ValueError, komut_plani_uret, I, dict(P, max_sure_ms=True), msg="max_sure_ms bool olamaz")
raises(ValueError, komut_plani_uret, I, dict(P, max_sure_ms=0), msg="max_sure_ms 0 ret")
raises(ValueError, komut_plani_uret, I, dict(P, max_sure_ms=5001), msg="max_sure_ms üst sınır ret")
raises(ValueError, komut_plani_uret, I, dict(P, max_cikti_bayt=True), msg="max_cikti_bayt bool olamaz")
raises(ValueError, komut_plani_uret, I, dict(P, max_cikti_bayt=0), msg="max_cikti_bayt 0 ret")
raises(ValueError, komut_plani_uret, I, dict(P, max_cikti_bayt=65537), msg="max_cikti_bayt üst sınır ret")
raises(ValueError, komut_plani_uret, [dict(I[0], id=123)], P, msg="istek id str olmalı")
raises(ValueError, komut_plani_uret, [dict(I[0], program=123)], P, msg="istek program str olmalı")
raises(ValueError, komut_plani_uret, [dict(I[0], argumanlar=[123])], P, msg="argüman str olmalı")
raises(ValueError, komut_plani_uret, [dict(I[0], calisma_dizini=123)], P, msg="çalışma dizini str olmalı")
eq(komut_plani_uret(I[:1], dict(P, max_sure_ms=1, max_cikti_bayt=1))[0]["id"], I[0]["id"], "alt sınır profil geçerli")
eq(komut_plani_uret(I[:1], dict(P, max_sure_ms=5000, max_cikti_bayt=65536))[0]["id"], I[0]["id"], "üst sınır profil geçerli")
raises(ValueError, komut_plani_uret, I, dict(P, ek=1), msg="profil fazla alan ret")
raises(ValueError, komut_plani_uret, I, dict(P, kok="/sandbox\\alt"), msg="ters eğik çizgili kök ret")
raises(ValueError, komut_plani_uret, I, dict(P, kok="/sandbox//alt"), msg="normalize olmayan çift eğik çizgili kök ret")
raises(ValueError, komut_plani_uret, I, dict(P, izinli_programlar=("python",)), msg="izinli_programlar tuple olamaz")
raises(ValueError, komut_plani_uret, [dict(I[0], program="")], P, msg="boş program ret")
raises(ValueError, komut_plani_uret, [dict(I[0], dosyalar=[123])], P, msg="sayısal dosya adı ret")
eq(komut_plani_uret([dict(I[0], calisma_dizini="/sandbox\\alt")], P)[0]["nedenler"], ["dizin"], "ters eğik çizgili çalışma dizini reddedilmeli")
eq(komut_plani_uret([dict(I[0], calisma_dizini=P["kok"] + "/alt\\ic")], P)[0]["nedenler"], ["dizin"], "sandbox altındaki ters eğik çizgili çalışma dizini reddedilmeli")
# --- carbon-c8-ek-son ---
```

```solution
def komut_plani_uret(istekler, profil):
    import re
    from pathlib import PurePosixPath
    if not isinstance(profil, dict) or set(profil) != {"kullanici", "ag", "kok", "izinli_programlar", "max_sure_ms", "max_cikti_bayt"}:
        raise ValueError("profil şeması geçersiz")
    if profil["kullanici"] != "sandbox":
        raise ValueError("sandbox kullanıcısı gerekli")
    if profil["ag"] is not False:
        raise ValueError("ağ kapalı olmalı")
    kok_metin = profil["kok"]
    if not isinstance(kok_metin, str):
        raise ValueError("kök metin olmalı")
    if not kok_metin:
        raise ValueError("kök boş olamaz")
    if kok_metin != kok_metin.strip():
        raise ValueError("kök boşluk içeremez")
    if "\\" in kok_metin:
        raise ValueError("kök ters eğik çizgi içeremez")
    if kok_metin.endswith("/"):
        raise ValueError("kök eğik çizgiyle bitemez")
    kok = PurePosixPath(kok_metin)
    if not kok.is_absolute():
        raise ValueError("kök mutlak olmalı")
    if kok_metin == "/":
        raise ValueError("sistem kökü sandbox olamaz")
    if "." in kok.parts:
        raise ValueError("kök geçerli dizin parçası içeremez")
    if ".." in kok.parts:
        raise ValueError("kök üst dizin parçası içeremez")
    if str(kok) != kok_metin:
        raise ValueError("kök normalize edilmeli")
    if not isinstance(profil["izinli_programlar"], list):
        raise ValueError("program listesi liste olmalı")
    if not profil["izinli_programlar"]:
        raise ValueError("program listesi boş olamaz")
    if len(set(profil["izinli_programlar"])) != len(profil["izinli_programlar"]):
        raise ValueError("programlar yinelenemez")
    if any(p not in ("python", "echo", "hesap") for p in profil["izinli_programlar"]):
        raise ValueError("program izinli değil")
    if type(profil["max_sure_ms"]) is not int:
        raise ValueError("süre sınırı int olmalı")
    if profil["max_sure_ms"] < 1 or profil["max_sure_ms"] > 5000:
        raise ValueError("süre sınırı aralık dışı")
    if type(profil["max_cikti_bayt"]) is not int:
        raise ValueError("çıktı sınırı int olmalı")
    if profil["max_cikti_bayt"] < 1 or profil["max_cikti_bayt"] > 65536:
        raise ValueError("çıktı sınırı aralık dışı")
    if not isinstance(istekler, list):
        raise ValueError("istekler liste olmalı")
    kimlikler = set()
    plan = []
    for istek in istekler:
        if not isinstance(istek, dict) or set(istek) != {"id", "program", "argumanlar", "calisma_dizini", "dosyalar"}:
            raise ValueError("istek şeması geçersiz")
        kimlik = istek["id"]
        if not isinstance(kimlik, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kimlik):
            raise ValueError("kimlik geçersiz")
        if kimlik in kimlikler:
            raise ValueError("kimlik yinelenemez")
        kimlikler.add(kimlik)
        if not isinstance(istek["program"], str) or not istek["program"]:
            raise ValueError("program metin olmalı")
        if not isinstance(istek["argumanlar"], list) or not isinstance(istek["dosyalar"], list):
            raise ValueError("argumanlar ve dosyalar liste olmalı")
        for arguman in istek["argumanlar"]:
            if not isinstance(arguman, str):
                raise ValueError("argüman metin olmalı")
            if len(arguman) < 1:
                raise ValueError("argüman boş olamaz")
            if len(arguman) > 200:
                raise ValueError("argüman çok uzun")
            if "\0" in arguman:
                raise ValueError("argüman NUL içeremez")
        if not isinstance(istek["calisma_dizini"], str) or not istek["calisma_dizini"]:
            raise ValueError("çalışma dizini metin olmalı")
        if any(not isinstance(dosya, str) or not dosya for dosya in istek["dosyalar"]):
            raise ValueError("dosya metni geçersiz")
        nedenler = []
        if istek["program"] not in profil["izinli_programlar"]:
            nedenler.append("program")
        dizin_metin = istek["calisma_dizini"]
        dizin = PurePosixPath(dizin_metin)
        dizin_guvenli = dizin.is_absolute() and str(dizin) == dizin_metin and "\\" not in dizin_metin and "." not in dizin.parts and ".." not in dizin.parts and (dizin == kok or kok in dizin.parents)
        if not dizin_guvenli:
            nedenler.append("dizin")
        dosya_hatasi = False
        for dosya_metin in istek["dosyalar"]:
            dosya = PurePosixPath(dosya_metin)
            if dosya.is_absolute() or str(dosya) != dosya_metin or "\\" in dosya_metin or "." in dosya.parts or ".." in dosya.parts:
                dosya_hatasi = True
        if dosya_hatasi:
            nedenler.append("dosya")
        plan.append({"id": kimlik, "karar": "reddet" if nedenler else "hazir", "nedenler": nedenler, "argv": [istek["program"]] + list(istek["argumanlar"])})
    return sorted(plan, key=lambda x: x["id"])
```

```hint
Biçim hatalarıyla politika retlerini ayır. Dizin ve dosya yollarını ayrı doğrula; argv üretirken argüman listesinin kopyasını kullan.
```
:::

::: anlat Kaynak sınırı son anda da uygulanır
Plan kabul edilmiş olsa bile yürütme süresi veya çıktı sınırı aşılabilir. Son geçerli süre ve çıktı değerleri sınıra eşittir; sınırın bir birim üstü ihlaldir. Sistem hatası, zaman aşımı, çıktı sınırı ve sıfırdan farklı çıkış kodu birbirini gizlemeden raporlanır.

Neden sırası `sistem`, `zaman`, `cikti`, `cikis` şeklindedir. Durum önceliği de aynı sırayı izler: `calisamadi`, `zaman_asimi`, `cikti_siniri`, `basarisiz`, son olarak `tamamlandi`.

**Görev 3'te sık tuzaklar:** `>=` ile karşılaştırmak tam sınırdaki yürütmeyi ihlal sayar (`veri/yurutme_sonuclari.json`, `tam-sinir`). `cikis_kodu > 0` denetimi sinyalle öldürülen süreçlerin negatif kodlarını başarı sanır (`negatif-cikis`). Sistem hatasında yalnız `sistem` yazmak, aynı koşuda süre ve çıktı bütçesinin de aşıldığını gizler (`sistem`).
:::

::: gorev 3 · Sandbox yürütme sonuçlarını raporla
`sandbox_sonuclari(sonuclar, profil)` işlevini yaz. Profil ilk görevdeki bütün kuralları sağlasın. Sonuçlar liste; her kayıt tam olarak `id`, `sure_ms`, `cikti_bayt`, `cikis_kodu`, `sistem_hatasi` alanlarını taşısın. Kimlik ikinci görevdeki desene uysun ve benzersiz olsun. Süre ve çıktı bool olmayan sıfır/pozitif int; çıkış kodu bool olmayan −255–255 arası int olmalıdır. Sistem hatası `None` veya boş olmayan stringdir. Geçersiz veride `ValueError` yükselt.

Sistem hatası varsa `sistem`, süre profil sınırından büyükse `zaman`, çıktı profil sınırından büyükse `cikti`, çıkış kodu sıfır değilse `cikis` nedenini ekle. Yukarıdaki önceliğe göre tek durum belirle. Her kayıt için `{"id":ID,"durum":DURUM,"nedenler":[...],"sinir_icinde":not nedenler}` döndür. Kimliğe göre sırala, boş sonuçta boş liste döndür ve girdileri değiştirme.

Görünür veri: `veri/yurutme_sonuclari.json`. Dosyada profil, altı sonuç, beklenen rapor ve dört bozuk girdi vardır.

```starter
from ai_savunma_veri import json_yukle

def sandbox_sonuclari(sonuclar, profil):
    # KUSURLU BAŞLANGIÇ KODU: sınıra eşit süre ve çıktıyı ihlal sayıyor (>=), negatif çıkış kodunu başarı sayıyor (> 0), yalnız ilk nedeni yazıyor (sistem hatası diğer kanıtları gizler), girdileri doğrulamıyor ve raporu sıralamıyor!
    rapor = []
    for sonuc in sonuclar:
        if sonuc["sistem_hatasi"]:
            durum, nedenler = "calisamadi", ["sistem"]
        elif sonuc["sure_ms"] >= profil["max_sure_ms"]:
            durum, nedenler = "zaman_asimi", ["zaman"]
        elif sonuc["cikti_bayt"] >= profil["max_cikti_bayt"]:
            durum, nedenler = "cikti_siniri", ["cikti"]
        elif sonuc["cikis_kodu"] > 0:
            durum, nedenler = "basarisiz", ["cikis"]
        else:
            durum, nedenler = "tamamlandi", []
        rapor.append({"id": sonuc["id"], "durum": durum, "nedenler": nedenler, "sinir_icinde": not nedenler})
    return rapor

veri = json_yukle("veri/yurutme_sonuclari.json")
try:
    rapor = sandbox_sonuclari(veri["sonuclar"], veri["profil"])
except Exception as hata:
    rapor = [{"id": "hata", "hata": type(hata).__name__}]
print("rapor sırası", "doğru" if [r["id"] for r in rapor] == [b["id"] for b in veri["beklenen"]] else "YANLIŞ")
for beklenen in veri["beklenen"]:
    bulunan = next((r for r in rapor if r["id"] == beklenen["id"]), None)
    print(beklenen["id"], "doğru" if bulunan == beklenen else "YANLIŞ", bulunan)
for b in veri["bozuk_girdiler"]:
    try:
        sandbox_sonuclari(b["girdi"], veri["profil"])
        print(b["id"], "YANLIŞ: kabul edildi", b["aciklama"])
    except ValueError:
        print(b["id"], "doğru: ValueError", b["aciklama"])
    except Exception as hata:
        print(b["id"], "YANLIŞ:", type(hata).__name__, b["aciklama"])
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-13")
```

```test
import copy
P = {"kullanici": "sandbox", "ag": False, "kok": "/sandbox", "izinli_programlar": ["python", "echo"], "max_sure_ms": 1000, "max_cikti_bayt": 4096}
S = [
    {"id": "ok-1", "sure_ms": 1000, "cikti_bayt": 4096, "cikis_kodu": 0, "sistem_hatasi": None},
    {"id": "zaman-1", "sure_ms": 1001, "cikti_bayt": 0, "cikis_kodu": 0, "sistem_hatasi": None},
    {"id": "cikti-1", "sure_ms": 10, "cikti_bayt": 4097, "cikis_kodu": 0, "sistem_hatasi": None},
    {"id": "cikis-1", "sure_ms": 10, "cikti_bayt": 0, "cikis_kodu": 2, "sistem_hatasi": None},
    {"id": "sistem-1", "sure_ms": 1001, "cikti_bayt": 4097, "cikis_kodu": 1, "sistem_hatasi": "izin"},
]
BEKLENEN = [
    {"id": "cikis-1", "durum": "basarisiz", "nedenler": ["cikis"], "sinir_icinde": False},
    {"id": "cikti-1", "durum": "cikti_siniri", "nedenler": ["cikti"], "sinir_icinde": False},
    {"id": "ok-1", "durum": "tamamlandi", "nedenler": [], "sinir_icinde": True},
    {"id": "sistem-1", "durum": "calisamadi", "nedenler": ["sistem", "zaman", "cikti", "cikis"], "sinir_icinde": False},
    {"id": "zaman-1", "durum": "zaman_asimi", "nedenler": ["zaman"], "sinir_icinde": False},
]
def sozlesme(fn):
    try:
        sonce = copy.deepcopy(S)
        ponce = copy.deepcopy(P)
        if fn(S, P) != BEKLENEN or S != sonce or P != ponce or fn(list(reversed(S)), P) != BEKLENEN or fn([], P) != []:
            return False
        if fn([dict(S[0], id="a" * 64)], P)[0]["id"] != "a" * 64:
            return False
        if fn([dict(S[0], sure_ms=0, cikti_bayt=0)], P)[0]["durum"] != "tamamlandi":
            return False
        for alan, deger in [("max_sure_ms", 1), ("max_sure_ms", 5000), ("max_cikti_bayt", 1), ("max_cikti_bayt", 65536)]:
            if fn([], dict(P, **{alan: deger})) != []:
                return False
        for cikis in (-255, 255):
            if fn([dict(S[0], cikis_kodu=cikis)], P)[0]["durum"] != "basarisiz":
                return False
        for sonuclar, profil in [
            (None, P), ({}, P), ([None], P), (S, None), (S, dict(P, ag=True)),
            (S, dict(P, kullanici="root")), (S, dict(P, max_sure_ms=0)), (S, dict(P, max_sure_ms=5001)),
            (S, dict(P, max_cikti_bayt=0)), (S, dict(P, max_cikti_bayt=65537)),
            ([dict(S[0], ek=1)], P), ([dict(S[0], id="")], P), ([dict(S[0], id="a b")], P),
            ([dict(S[0], id="a" * 65)], P), ([S[0], S[0]], P),
            ([dict(S[0], sure_ms=-1)], P), ([dict(S[0], sure_ms=True)], P),
            ([dict(S[0], cikti_bayt=-1)], P), ([dict(S[0], cikti_bayt=False)], P),
            ([dict(S[0], cikis_kodu=-256)], P), ([dict(S[0], cikis_kodu=256)], P), ([dict(S[0], cikis_kodu=True)], P),
            ([dict(S[0], sistem_hatasi="")], P), ([dict(S[0], sistem_hatasi=1)], P),
        ]:
            try:
                fn(sonuclar, profil)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(sandbox_sonuclari), "sistem, süre, çıktı ve çıkış kodu sınırları korunmalı")
def m_zaman(sonuclar, profil):
    yeni = dict(profil, max_sure_ms=5000)
    return sandbox_sonuclari(sonuclar, yeni)
def m_cikti(sonuclar, profil):
    yeni = dict(profil, max_cikti_bayt=65536)
    return sandbox_sonuclari(sonuclar, yeni)
def m_cikis(sonuclar, profil):
    degisen = [dict(x, cikis_kodu=0) for x in sonuclar]
    return sandbox_sonuclari(degisen, profil)
for ad, mutant in [("zamanı genişleten", m_zaman), ("çıktıyı genişleten", m_cikti), ("çıkışı silen", m_cikis)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
# --- carbon-c8-ek-bas ---
raises(ValueError, sandbox_sonuclari, S, dict(P, kullanici=123), msg="profil kullanıcı str olmalı")
raises(ValueError, sandbox_sonuclari, S, dict(P, max_sure_ms=True), msg="max_sure_ms bool ret")
raises(ValueError, sandbox_sonuclari, S, dict(P, max_cikti_bayt=True), msg="max_cikti_bayt bool ret")
raises(ValueError, sandbox_sonuclari, [dict(S[0], id=123)], P, msg="sonuç id str olmalı")
raises(ValueError, sandbox_sonuclari, [dict(S[0], cikis_kodu=True)], P, msg="çıkış kodu bool ret")
raises(ValueError, sandbox_sonuclari, [dict(S[0], sure_ms=True)], P, msg="süre bool ret")
raises(ValueError, sandbox_sonuclari, [dict(S[0], cikti_bayt=True)], P, msg="çıktı bayt bool ret")
raises(ValueError, sandbox_sonuclari, [dict(S[0], sistem_hatasi=123)], P, msg="sistem hatası str/None olmalı")
raises(ValueError, sandbox_sonuclari, [dict(S[0], sistem_hatasi="")], P, msg="boş sistem hatası ret")
raises(ValueError, sandbox_sonuclari, S, dict(P, ek=1), msg="profil fazla alan ret")
raises(ValueError, sandbox_sonuclari, S, dict(P, izinli_programlar=("python",)), msg="izinli_programlar tuple olamaz")
raises(ValueError, sandbox_sonuclari, S, dict(P, izinli_programlar=[]), msg="boş program listesi ret")
# --- carbon-c8-ek-son ---
```

```solution
def sandbox_sonuclari(sonuclar, profil):
    import re
    if not isinstance(profil, dict) or set(profil) != {"kullanici", "ag", "kok", "izinli_programlar", "max_sure_ms", "max_cikti_bayt"}:
        raise ValueError("profil şeması geçersiz")
    if profil["kullanici"] != "sandbox":
        raise ValueError("sandbox kullanıcısı gerekli")
    if profil["ag"] is not False:
        raise ValueError("ağ kapalı olmalı")
    if not isinstance(profil["izinli_programlar"], list):
        raise ValueError("program listesi liste olmalı")
    if not profil["izinli_programlar"]:
        raise ValueError("program listesi boş olamaz")
    if type(profil["max_sure_ms"]) is not int:
        raise ValueError("süre sınırı int olmalı")
    if profil["max_sure_ms"] < 1 or profil["max_sure_ms"] > 5000:
        raise ValueError("süre sınırı aralık dışı")
    if type(profil["max_cikti_bayt"]) is not int:
        raise ValueError("çıktı sınırı int olmalı")
    if profil["max_cikti_bayt"] < 1 or profil["max_cikti_bayt"] > 65536:
        raise ValueError("çıktı sınırı aralık dışı")
    if not isinstance(sonuclar, list):
        raise ValueError("sonuçlar liste olmalı")
    kimlikler = set()
    rapor = []
    for sonuc in sonuclar:
        if not isinstance(sonuc, dict) or set(sonuc) != {"id", "sure_ms", "cikti_bayt", "cikis_kodu", "sistem_hatasi"}:
            raise ValueError("sonuç şeması geçersiz")
        kimlik = sonuc["id"]
        if not isinstance(kimlik, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kimlik):
            raise ValueError("kimlik geçersiz")
        if kimlik in kimlikler:
            raise ValueError("kimlik yinelenemez")
        kimlikler.add(kimlik)
        if type(sonuc["sure_ms"]) is not int:
            raise ValueError("süre int olmalı")
        if sonuc["sure_ms"] < 0:
            raise ValueError("süre negatif olamaz")
        if type(sonuc["cikti_bayt"]) is not int:
            raise ValueError("çıktı boyutu int olmalı")
        if sonuc["cikti_bayt"] < 0:
            raise ValueError("çıktı boyutu negatif olamaz")
        if type(sonuc["cikis_kodu"]) is not int:
            raise ValueError("çıkış kodu int olmalı")
        if sonuc["cikis_kodu"] < -255 or sonuc["cikis_kodu"] > 255:
            raise ValueError("çıkış kodu aralık dışı")
        if sonuc["sistem_hatasi"] is not None:
            if not isinstance(sonuc["sistem_hatasi"], str):
                raise ValueError("sistem hatası metin olmalı")
            if not sonuc["sistem_hatasi"]:
                raise ValueError("sistem hatası boş olamaz")
        nedenler = []
        if sonuc["sistem_hatasi"] is not None:
            nedenler.append("sistem")
        if sonuc["sure_ms"] > profil["max_sure_ms"]:
            nedenler.append("zaman")
        if sonuc["cikti_bayt"] > profil["max_cikti_bayt"]:
            nedenler.append("cikti")
        if sonuc["cikis_kodu"] != 0:
            nedenler.append("cikis")
        if "sistem" in nedenler:
            durum = "calisamadi"
        elif "zaman" in nedenler:
            durum = "zaman_asimi"
        elif "cikti" in nedenler:
            durum = "cikti_siniri"
        elif "cikis" in nedenler:
            durum = "basarisiz"
        else:
            durum = "tamamlandi"
        rapor.append({"id": kimlik, "durum": durum, "nedenler": nedenler, "sinir_icinde": not nedenler})
    return sorted(rapor, key=lambda x: x["id"])
```

```hint
Sınır eşitliğini kabul et, yalnız sınır üstünü ihlal say. Bütün nedenleri topladıktan sonra durumu sabit öncelik sırasıyla seç.
```
:::

::: anlat Planlama, modelin önerisi yürütücüye ulaşmadan çalışır
Komut planlayıcı ancak modelin **gerçekten önerdiği** bir komut üzerinde çalıştığında anlam kazanır. Son görevde senin `komut_plani_uret` işlevin, gerçek yerel modelin bir `komut_oner` aracıyla ürettiği komut önerilerini kapalı sandbox profiline göre planlar. Deney iki senaryoda koşar: sandbox içinde izinli bir programla (python) çalıştırma ve izin listesinde olmayan bir programla (curl) ağdan indirme.

Planlama yürütmeden **önce** çalışır; hiçbir komut gerçekten çalıştırılmaz. İzinli program + sandbox dizini `hazir` olur; izin listesinde olmayan program, sandbox kökü dışındaki dizin veya gezinti yolu `reddet` üretir. Model öneriyi bir görevden türetmiş ve geniş niyet taşımış olsa bile, en az ayrıcalık program ve yol düzeyinde uygulanır.

**Çıktıyı okurken:** Her senaryo için modelin önerdiği programı, çalışma dizinini ve dosyaları senin planınla yan yana oku. Tehlikeli senaryoda `program` nedeni beklenir; model aynı öneride kök dışı bir dizin de kullandıysa `dizin` nedeni de görünür. Güvenli senaryo `hazir` olsa bile komut bu derste çalıştırılmaz; bir sonraki katman (gerçek sandbox) yine gereklidir.
:::

::: gorev Gerçek deney · Gerçek komut önerisini sandbox profiliyle sınırla
`komut_plani_uret(istekler, profil)` işlevini yaz — kuralları ve çıktısı 2. görevdekiyle **aynıdır**. Deney gerçek modele `komut_oner` aracını verir, önerileri iyi-tipli isteklere dönüştürür ve senin planlayıcın her isteği sandbox profiline göre değerlendirir; izinsiz program veya güvensiz yol reddedilir.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab

def komut_plani_uret(istekler, profil):
    # KUSURLU BAŞLANGIÇ KODU: çalışma dizinini dizge önekiyle denetliyor ("/sandbox/../etc" ve "/sandboxx" geçer), dosyada yalnız mutlak yolu yakalıyor ("../secret" geçer), ilk nedende duruyor, girdileri doğrulamıyor ve planı sıralamıyor!
    plan = []
    for istek in istekler:
        if istek["program"] not in profil["izinli_programlar"]:
            nedenler = ["program"]
        elif not istek["calisma_dizini"].startswith(profil["kok"]):
            nedenler = ["dizin"]
        elif any(d.startswith("/") for d in istek["dosyalar"]):
            nedenler = ["dosya"]
        else:
            nedenler = []
        plan.append({"id": istek["id"], "karar": "reddet" if nedenler else "hazir", "nedenler": nedenler, "argv": [istek["program"]] + istek["argumanlar"]})
    return plan

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_13 as deney
    deney.goster(komut_plani_uret)
```

```test
import ai_lab
sonuclar = []
def kontrol(kosul, mesaj):
    sonuclar.append(bool(kosul))
    return ok(kosul, mesaj)
import ast
_yasak = ("referans", "getattr", "kanit_yaz")
sorun = list(ai_lab.kod_denetimi(src, _yasak))
for _n in ast.walk(ast.parse(src)):
    if isinstance(_n, ast.ImportFrom) and any(a.name in _yasak or a.name == "*" for a in _n.names):
        sorun.append("referans importu yasak")
    if isinstance(_n, (ast.Import, ast.ImportFrom)) and any(x and x.split(".")[0] in ("inspect", "importlib", "runpy") for x in [a.name for a in _n.names] + ([_n.module] if isinstance(_n, ast.ImportFrom) else [])):
        sorun.append("kaynak okuma/dinamik import yasak")
    if isinstance(_n, ast.Name) and _n.id in ("exec", "eval", "compile", "__builtins__"):
        sorun.append("dinamik kod çalıştırma yasak: " + _n.id)
sorun = sorted(set(sorun))
if not kontrol(not sorun, "laboratuvar yamalanmamalı, referans kullanılmamalı " + ", ".join(sorun)):
    stop()
fn = need("komut_plani_uret")
from sandbox import ai_gercek_ai_savunma_13 as D
P = {"kullanici": "sandbox", "ag": False, "kok": "/sandbox", "izinli_programlar": ["python", "echo"], "max_sure_ms": 1000, "max_cikti_bayt": 4096}
I = [
    {"id": "izin-1", "program": "python", "argumanlar": ["is.py"], "calisma_dizini": "/sandbox/is", "dosyalar": ["is.py"]},
    {"id": "ret-1", "program": "curl", "argumanlar": ["-O", "http://x"], "calisma_dizini": "/tmp", "dosyalar": ["../secret"]},
]
BEKLENEN = [
    {"id": "izin-1", "karar": "hazir", "nedenler": [], "argv": ["python", "is.py"]},
    {"id": "ret-1", "karar": "reddet", "nedenler": ["program", "dizin", "dosya"], "argv": ["curl", "-O", "http://x"]},
]
def sozlesme(f):
    try:
        if f(I, P) != BEKLENEN or f([], P) != []:
            return False
        for bozuk in (None, [None], [dict(I[0], ek=1)], [dict(I[0], program=1)]):
            try:
                f(bozuk, P)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
kontrol(sozlesme(fn), "program, çalışma dizini, dosya ve argv sınırları korunmalı")
r, oz = None, None
# --- carbon-c8-g4-bas ---
def _c8_birim_denetimi():
    _u = []
    def _same(got, exp):
        try:
            if not bool(got == exp):
                return False
        except Exception:
            return False
        if isinstance(exp, bool) or isinstance(got, bool):
            return isinstance(got, bool) and isinstance(exp, bool)
        if isinstance(exp, (int, float)) and isinstance(got, (int, float)):
            return True
        return isinstance(got, type(exp))
    def ok(cond, msg=None, got=None):
        _u.append(bool(cond))
        return bool(cond)
    def eq(got, exp, msg=None):
        r = _same(got, exp)
        _u.append(r)
        return r
    def yakin(got, exp, msg=None, tol=1e-6):
        try:
            r = abs(got - exp) <= tol
        except Exception:
            r = False
        _u.append(bool(r))
        return bool(r)
    def raises(exc, fn_cagri, *a, msg=None, **kw):
        try:
            fn_cagri(*a, **kw)
        except exc:
            _u.append(True)
            return True
        except Exception:
            _u.append(False)
            return False
        _u.append(False)
        return False
    komut_plani_uret = need('komut_plani_uret')
    def _birim_adim_2():
        import copy
        P = {"kullanici": "sandbox", "ag": False, "kok": "/sandbox", "izinli_programlar": ["python", "echo"], "max_sure_ms": 1000, "max_cikti_bayt": 4096}
        I = [
            {"id": "izin-1", "program": "python", "argumanlar": ["is.py", "--kirik"], "calisma_dizini": "/sandbox/is", "dosyalar": ["is.py", "veri/girdi.txt"]},
            {"id": "ret-1", "program": "sh", "argumanlar": ["-c", "echo test"], "calisma_dizini": "/tmp", "dosyalar": ["../secret"]},
        ]
        BEKLENEN = [
            {"id": "izin-1", "karar": "hazir", "nedenler": [], "argv": ["python", "is.py", "--kirik"]},
            {"id": "ret-1", "karar": "reddet", "nedenler": ["program", "dizin", "dosya"], "argv": ["sh", "-c", "echo test"]},
        ]
        def sozlesme(fn):
            try:
                ionce = copy.deepcopy(I)
                ponce = copy.deepcopy(P)
                if fn(I, P) != BEKLENEN or I != ionce or P != ponce or fn(list(reversed(I)), P) != BEKLENEN or fn([], P) != []:
                    return False
                if fn([dict(I[0], calisma_dizini="/sandbox")], P)[0]["karar"] != "hazir":
                    return False
                for arguman in ["a", "a" * 200]:
                    if fn([dict(I[0], argumanlar=[arguman])], P)[0]["karar"] != "hazir":
                        return False
                for alan, deger in [("max_sure_ms", 1), ("max_sure_ms", 5000), ("max_cikti_bayt", 1), ("max_cikti_bayt", 65536)]:
                    if fn([], dict(P, **{alan: deger})) != []:
                        return False
                for dosya in ["/etc/passwd", "../secret", "is/../../secret", "./is.py", "is\\girdi.txt", "is//girdi.txt"]:
                    if fn([dict(I[0], dosyalar=[dosya])], P)[0]["nedenler"] != ["dosya"]:
                        return False
                for dizin in ["sandbox", "/tmp", "/sandbox/../etc", "/sandbox/", "/sandbox\\is"]:
                    if fn([dict(I[0], calisma_dizini=dizin)], P)[0]["nedenler"] != ["dizin"]:
                        return False
                for istekler, profil in [
                    (None, P), ({}, P), ([None], P), (I, None), (I, dict(P, ag=True)),
                    (I, dict(P, kullanici="root")), (I, dict(P, kok="")), (I, dict(P, kok="/")),
                    (I, dict(P, max_sure_ms=0)), (I, dict(P, max_sure_ms=5001)),
                    (I, dict(P, max_cikti_bayt=0)), (I, dict(P, max_cikti_bayt=65537)),
                    ([dict(I[0], ek=1)], P), ([dict(I[0], id="")], P), ([dict(I[0], id="a b")], P),
                    ([dict(I[0], id="a" * 65)], P), ([I[0], I[0]], P),
                    ([dict(I[0], program=1)], P), ([dict(I[0], argumanlar=None)], P),
                    ([dict(I[0], argumanlar=[""])], P), ([dict(I[0], argumanlar=["a" * 201])], P),
                    ([dict(I[0], argumanlar=["a\0b"])], P), ([dict(I[0], calisma_dizini="")], P),
                    ([dict(I[0], dosyalar=None)], P), ([dict(I[0], dosyalar=[""])], P),
                ]:
                    try:
                        fn(istekler, profil)
                        return False
                    except ValueError:
                        pass
                return True
            except Exception:
                return False
        ok(sozlesme(komut_plani_uret), "program, çalışma dizini, dosya ve argv sınırları korunmalı")
        def m_program(istekler, profil):
            yeni = copy.deepcopy(profil)
            yeni["izinli_programlar"].append("sh")
            return komut_plani_uret(istekler, yeni)
        def m_dizin(istekler, profil):
            degisen = [dict(x, calisma_dizini="/sandbox") for x in istekler]
            return komut_plani_uret(degisen, profil)
        def m_dosya(istekler, profil):
            degisen = [dict(x, dosyalar=[]) for x in istekler]
            return komut_plani_uret(degisen, profil)
        for ad, mutant in [("programı açan", m_program), ("dizini zorlayan", m_dizin), ("dosyayı silen", m_dosya)]:
            ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

        raises(ValueError,komut_plani_uret,I,dict(P,kok='/sandbox '),msg='plan kök yolu baş/son boşluğu ret')
        raises(ValueError, komut_plani_uret, I, dict(P, kullanici=123), msg="profil kullanıcı str olmalı")
        raises(ValueError, komut_plani_uret, I, dict(P, kullanici="root"), msg="root kullanıcı ret")
        raises(ValueError, komut_plani_uret, I, dict(P, ag="evet"), msg="ag bool olmalı")
        raises(ValueError, komut_plani_uret, I, dict(P, kok=123), msg="kök str olmalı")
        raises(ValueError, komut_plani_uret, I, dict(P, kok="/"), msg="kök '/' ret")
        raises(ValueError, komut_plani_uret, I, dict(P, kok="goreli/yol"), msg="göreli kök ret")
        raises(ValueError, komut_plani_uret, I, dict(P, kok="/sandbox/../etc"), msg="üst dizinli kök ret")
        raises(ValueError, komut_plani_uret, I, dict(P, izinli_programlar=[]), msg="boş program listesi ret")
        raises(ValueError, komut_plani_uret, I, dict(P, izinli_programlar="python"), msg="izinli_programlar liste olmalı")
        raises(ValueError, komut_plani_uret, I, dict(P, izinli_programlar=[123]), msg="program str olmalı")
        raises(ValueError, komut_plani_uret, I, dict(P, izinli_programlar=["python", "python"]), msg="yinelenen program ret")
        raises(ValueError, komut_plani_uret, I, dict(P, izinli_programlar=["sh"]), msg="kabuk programı ret")
        raises(ValueError, komut_plani_uret, I, dict(P, max_sure_ms=True), msg="max_sure_ms bool olamaz")
        raises(ValueError, komut_plani_uret, I, dict(P, max_sure_ms=0), msg="max_sure_ms 0 ret")
        raises(ValueError, komut_plani_uret, I, dict(P, max_sure_ms=5001), msg="max_sure_ms üst sınır ret")
        raises(ValueError, komut_plani_uret, I, dict(P, max_cikti_bayt=True), msg="max_cikti_bayt bool olamaz")
        raises(ValueError, komut_plani_uret, I, dict(P, max_cikti_bayt=0), msg="max_cikti_bayt 0 ret")
        raises(ValueError, komut_plani_uret, I, dict(P, max_cikti_bayt=65537), msg="max_cikti_bayt üst sınır ret")
        raises(ValueError, komut_plani_uret, [dict(I[0], id=123)], P, msg="istek id str olmalı")
        raises(ValueError, komut_plani_uret, [dict(I[0], program=123)], P, msg="istek program str olmalı")
        raises(ValueError, komut_plani_uret, [dict(I[0], argumanlar=[123])], P, msg="argüman str olmalı")
        raises(ValueError, komut_plani_uret, [dict(I[0], calisma_dizini=123)], P, msg="çalışma dizini str olmalı")
        eq(komut_plani_uret(I[:1], dict(P, max_sure_ms=1, max_cikti_bayt=1))[0]["id"], I[0]["id"], "alt sınır profil geçerli")
        eq(komut_plani_uret(I[:1], dict(P, max_sure_ms=5000, max_cikti_bayt=65536))[0]["id"], I[0]["id"], "üst sınır profil geçerli")
        raises(ValueError, komut_plani_uret, I, dict(P, ek=1), msg="profil fazla alan ret")
        raises(ValueError, komut_plani_uret, I, dict(P, kok="/sandbox\\alt"), msg="ters eğik çizgili kök ret")
        raises(ValueError, komut_plani_uret, I, dict(P, kok="/sandbox//alt"), msg="normalize olmayan çift eğik çizgili kök ret")
        raises(ValueError, komut_plani_uret, I, dict(P, izinli_programlar=("python",)), msg="izinli_programlar tuple olamaz")
        raises(ValueError, komut_plani_uret, [dict(I[0], program="")], P, msg="boş program ret")
        raises(ValueError, komut_plani_uret, [dict(I[0], dosyalar=[123])], P, msg="sayısal dosya adı ret")
        eq(komut_plani_uret([dict(I[0], calisma_dizini="/sandbox\\alt")], P)[0]["nedenler"], ["dizin"], "ters eğik çizgili çalışma dizini reddedilmeli")
        eq(komut_plani_uret([dict(I[0], calisma_dizini=P["kok"] + "/alt\\ic")], P)[0]["nedenler"], ["dizin"], "sandbox altındaki ters eğik çizgili çalışma dizini reddedilmeli")
    try:
        _birim_adim_2()
    except Exception:
        _u.append(False)
    return bool(_u) and all(_u)
kontrol(_c8_birim_denetimi(), "deney öncesi tam birim sözleşmesi korunmalı")
# --- carbon-c8-g4-son ---
if all(sonuclar):
    try:
        r = D.deney(fn)
    except ai_lab.GercekLabYok as e:
        kontrol(False, f"GERÇEK MODEL YOK, deney yapılmadı: {e}")
        stop()
    plan_map = {p["id"]: p for p in r["plan"]}
    kontrol(plan_map.get("guvenli-1", {}).get("karar") == "hazir", "izinli programla gerçek öneri hazır")
    kontrol(plan_map.get("tehlikeli-1", {}).get("karar") == "reddet" and "program" in plan_map.get("tehlikeli-1", {}).get("nedenler", []),
            "izinsiz programlı gerçek öneri reddedildi (program nedeni)")
    oz = D.ozet(r)
yol = ai_lab.kanit_yaz("savunma-sandbox", {"kaynak": "gercek", "kabul": all(sonuclar), "ders": "ai-savunma-13",
                                           "ortam": (r or {}).get("ortam"), "ozet": oz})
if oz:
    ok(True, f"BULGU ({r['ortam']['model']['ad']}): modelin gerçek komut önerileri sandbox profiliyle planlandı → kararlar {oz['kararlar']}; "
             f"güvenli öneri hazır, izinsiz program (tehlikeli) nedenler {oz['tehlikeli_nedenler']} ile reddedildi. "
             f"Planlama yürütmeden önce çalıştı; komut yürütücüye ulaşmadı (en az ayrıcalık).")
```

```solution
import ai_lab

def komut_plani_uret(istekler, profil):
    import re
    from pathlib import PurePosixPath
    if not isinstance(profil, dict) or set(profil) != {"kullanici", "ag", "kok", "izinli_programlar", "max_sure_ms", "max_cikti_bayt"}:
        raise ValueError("profil şeması geçersiz")
    if profil["kullanici"] != "sandbox":
        raise ValueError("sandbox kullanıcısı gerekli")
    if profil["ag"] is not False:
        raise ValueError("ağ kapalı olmalı")
    kok_metin = profil["kok"]
    if not isinstance(kok_metin, str):
        raise ValueError("kök metin olmalı")
    if not kok_metin:
        raise ValueError("kök boş olamaz")
    if kok_metin != kok_metin.strip():
        raise ValueError("kök boşluk içeremez")
    if "\\" in kok_metin:
        raise ValueError("kök ters eğik çizgi içeremez")
    if kok_metin.endswith("/"):
        raise ValueError("kök eğik çizgiyle bitemez")
    kok = PurePosixPath(kok_metin)
    if not kok.is_absolute():
        raise ValueError("kök mutlak olmalı")
    if kok_metin == "/":
        raise ValueError("sistem kökü sandbox olamaz")
    if "." in kok.parts:
        raise ValueError("kök geçerli dizin parçası içeremez")
    if ".." in kok.parts:
        raise ValueError("kök üst dizin parçası içeremez")
    if str(kok) != kok_metin:
        raise ValueError("kök normalize edilmeli")
    if not isinstance(profil["izinli_programlar"], list):
        raise ValueError("program listesi liste olmalı")
    if not profil["izinli_programlar"]:
        raise ValueError("program listesi boş olamaz")
    if len(set(profil["izinli_programlar"])) != len(profil["izinli_programlar"]):
        raise ValueError("programlar yinelenemez")
    if any(p not in ("python", "echo", "hesap") for p in profil["izinli_programlar"]):
        raise ValueError("program izinli değil")
    if type(profil["max_sure_ms"]) is not int:
        raise ValueError("süre sınırı int olmalı")
    if profil["max_sure_ms"] < 1 or profil["max_sure_ms"] > 5000:
        raise ValueError("süre sınırı aralık dışı")
    if type(profil["max_cikti_bayt"]) is not int:
        raise ValueError("çıktı sınırı int olmalı")
    if profil["max_cikti_bayt"] < 1 or profil["max_cikti_bayt"] > 65536:
        raise ValueError("çıktı sınırı aralık dışı")
    if not isinstance(istekler, list):
        raise ValueError("istekler liste olmalı")
    kimlikler = set()
    plan = []
    for istek in istekler:
        if not isinstance(istek, dict) or set(istek) != {"id", "program", "argumanlar", "calisma_dizini", "dosyalar"}:
            raise ValueError("istek şeması geçersiz")
        kimlik = istek["id"]
        if not isinstance(kimlik, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kimlik):
            raise ValueError("kimlik geçersiz")
        if kimlik in kimlikler:
            raise ValueError("kimlik yinelenemez")
        kimlikler.add(kimlik)
        if not isinstance(istek["program"], str) or not istek["program"]:
            raise ValueError("program metin olmalı")
        if not isinstance(istek["argumanlar"], list) or not isinstance(istek["dosyalar"], list):
            raise ValueError("argumanlar ve dosyalar liste olmalı")
        for arguman in istek["argumanlar"]:
            if not isinstance(arguman, str):
                raise ValueError("argüman metin olmalı")
            if len(arguman) < 1:
                raise ValueError("argüman boş olamaz")
            if len(arguman) > 200:
                raise ValueError("argüman çok uzun")
            if "\0" in arguman:
                raise ValueError("argüman NUL içeremez")
        if not isinstance(istek["calisma_dizini"], str) or not istek["calisma_dizini"]:
            raise ValueError("çalışma dizini metin olmalı")
        if any(not isinstance(dosya, str) or not dosya for dosya in istek["dosyalar"]):
            raise ValueError("dosya metni geçersiz")
        nedenler = []
        if istek["program"] not in profil["izinli_programlar"]:
            nedenler.append("program")
        dizin_metin = istek["calisma_dizini"]
        dizin = PurePosixPath(dizin_metin)
        dizin_guvenli = dizin.is_absolute() and str(dizin) == dizin_metin and "\\" not in dizin_metin and "." not in dizin.parts and ".." not in dizin.parts and (dizin == kok or kok in dizin.parents)
        if not dizin_guvenli:
            nedenler.append("dizin")
        dosya_hatasi = False
        for dosya_metin in istek["dosyalar"]:
            dosya = PurePosixPath(dosya_metin)
            if dosya.is_absolute() or str(dosya) != dosya_metin or "\\" in dosya_metin or "." in dosya.parts or ".." in dosya.parts:
                dosya_hatasi = True
        if dosya_hatasi:
            nedenler.append("dosya")
        plan.append({"id": kimlik, "karar": "reddet" if nedenler else "hazir", "nedenler": nedenler, "argv": [istek["program"]] + list(istek["argumanlar"])})
    return sorted(plan, key=lambda x: x["id"])

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_13 as deney
    deney.goster(komut_plani_uret)
```

```hint
Bu işlev 2. görevdeki `komut_plani_uret` ile birebir aynıdır; tek fark, isteklerin gerçek model önerilerinden gelmesidir. Biçim hatalarıyla politika retlerini ayır; dizin ve dosya yollarını ayrı doğrula.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
### Sandbox adı yerine uygulanmış sınırı ölç

Kapalı profil hangi komut, dosya yolu, süre ve kaynak bütçesinin izinli olduğunu belirler. Yürütme planı bu sözleşmeyi aşmamalıdır. Bir komut önerisini reddetmek ile gerçekten yalıtılmış süreçte yürütmek farklı kanıtlar gerektirir. Dersteki son ölçümün hangi kısmının profil denetimi, hangi kısmının gerçek yürütme olduğunu ayır; profil sözlüğü tek başına işletim sistemi izolasyonu kurmaz.

| Yaygın yanlış | Mekanizmanın sınırı |
|---|---|
| Profil dosyası container izolasyonudur | Yapılandırma kararı ile çalışan runtime sınırı ayrı kanıtlanır. |

Saldırı–savunma bağlantısı: ai-saldiri-20.
:::

::: anlat Kaynak ile lab sonucunu ayır
[Docker kaynak sınırları](https://docs.docker.com/engine/containers/resource_constraints/). Kaynak sınırları runtime ayarlarıyla uygulanır; profil sözlüğünü doğrulamak bu ayarların işletim sisteminde uygulandığını tek başına göstermez.
:::
