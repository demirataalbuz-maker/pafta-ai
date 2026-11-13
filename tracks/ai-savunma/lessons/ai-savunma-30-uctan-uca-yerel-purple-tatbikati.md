---
id: ai-savunma-30
title: Uçtan Uca Yerel Purple Tatbikatı
summary: Saldırı, guardrail, telemetri, müdahale ve regresyon fazlarını kanıtlı ve zaman sıralı bir akışta birleştirip ölçülebilir rapor üret.
timeout: 45
esleme: ai-saldiri-37, ai-ile-guvenlik-15
---

::: anlat Purple tatbikatı beş ölçülebilir fazdan oluşur
Bu dersin akışı `saldir`, `guardrail`, `telemetri`, `mudahale`, `regresyon` sırasıdır. Her fazın `basarili` alanı o fazın kendi hedefine ulaşıp ulaşmadığını gösterir. Saldırı fazındaki başarı simülasyonun çalıştığını, guardrail fazındaki başarı ise beklenen savunmanın çalıştığını anlatır; alan her fazda aynı güvenlik anlamına gelmez.

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Gerçek purple tatbikatında saldırı garak/Promptfoo ile koşulur, guardrail çıktıyı süzer, olaylar SigNoz veya Elastic gibi bir telemetri sistemine akar, müdahale ekibi sırrı döndürür ve aynı saldırı paketi regresyon olarak tekrar koşulur | İlk üç görevde `tatbikat/faz_kayitlari.json`, `tatbikat/tatbikat_akisi.json` ve `tatbikat/purple_kayitlari.json` içindeki **sentetik** faz kayıtları; son görevde beş faz yerel Ollama modeli, basit bir çıktı filtresi, geçici JSONL telemetri dosyası ve SHA-256 manifestiyle gerçekten koşulur | Tek modelde, tek basit filtreyle ve üç regresyon vakasıyla geçen tatbikat, gerçek bir ürünün bütün saldırılara karşı güvenli olduğunu kanıtlamaz |

> [!NOT]
> İlk üç görevde çalışma dizinine kopyalanan `tatbikat/` dosyaları **sentetik** eğitim örnekleridir. Her çalıştırmada yeniden kopyalanır; çalıştırmalar arasında **kalıcılık yoktur**. Son adımdaki **Gerçek deney** görevinde yazdığın üç işlev canlı tatbikat kayıtlarıyla sınanır. Başarı sinyali yalnız zararsız bir canary kodudur.
:::

::: anlat Kanıt ve zaman sırası raporun parçasıdır
Telemetri, müdahale ve regresyon fazları en az bir kanıt kimliği taşır. Saldırı ve guardrail fazlarında kanıt listesi boş olabilir. Beş fazın tamamı birer kez bulunur ve zamanları akış sırasında geriye gidemez; eşit zaman geçerlidir.

Rapor yalnız bütün fazlar başarılıysa `gecti` olur. Başarısız faz adları korunur, toplam kanıt sayısı ve ilk ile son faz arasındaki süre hesaplanır. Eksik faz veya bozuk zaman sırası rapor üretmek yerine `ValueError` oluşturur.
:::

::: tahmin Akış süresi ve kanıt sayısını tahmin et
Üç çıktı satırını yaz:

```python
zamanlar = [0, 2, 3, 5, 8]
print(all(a <= b for a, b in zip(zamanlar, zamanlar[1:])))
print(sum([0, 1, 1, 2, 1]))
print(zamanlar[-1] - zamanlar[0])
```

???

```cikti
True
5
8
```

Toplam kanıt, her fazdaki kanıt kimliği sayısının toplamıdır.
:::

::: gorev 1 · Tatbikat faz kaydını doğrula
`tatbikat_kaydi_dogrula(kayit)` işlevini yaz. Kayıt tam olarak `id`, `faz`, `basarili`, `kanit_ids`, `zaman` alanlarını taşısın. Kayıt ve kanıt kimlikleri 1–64 karakterlik, ASCII harf/rakamla başlayan ve yalnız ASCII harf, rakam, alt çizgi veya tire içeren stringdir.

Faz `saldir`, `guardrail`, `telemetri`, `mudahale`, `regresyon`; başarılı gerçek bool olmalıdır. Kanıt kimlikleri yinelenmeyen listedir. `telemetri`, `mudahale`, `regresyon` fazlarında liste boş olamaz; diğerlerinde olabilir. Zaman bool olmayan, sıfır veya pozitif tamsayıdır. Geçersiz veride `ValueError` yükselt. Yeni sözlük ve yeni kanıt listesiyle döndür; girdiyi değiştirme.

```starter
from ai_savunma_veri import json_yukle

def tatbikat_kaydi_dogrula(kayit):
    # KUSURLU BAŞLANGIÇ KODU: telemetri/müdahale/regresyon fazlarında kanıtı zorunlu tutmuyor,
    # bool zamanı tamsayı sanıyor ve girdinin kendisini döndürüyor!
    if kayit["faz"] not in ("saldir", "guardrail", "telemetri", "mudahale", "regresyon"):
        raise ValueError("faz geçersiz")
    if not isinstance(kayit["zaman"], int) or kayit["zaman"] < 0:
        raise ValueError("zaman geçersiz")
    return kayit

for k in json_yukle("tatbikat/faz_kayitlari.json")["kayitlar"]:
    try:
        print(k["id"], "geçerli:", tatbikat_kaydi_dogrula(k))
    except ValueError as hata:
        print(k["id"], "reddedildi:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-30")
```

```test
import copy
K = {"id": "k-1", "faz": "telemetri", "basarili": True, "kanit_ids": ["k-t"], "zaman": 0}
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        sonuc = fn(K)
        if sonuc != K or K != once or sonuc is K or sonuc["kanit_ids"] is K["kanit_ids"]:
            return False
        if fn(dict(K, id="a" * 64, kanit_ids=["b" * 64], zaman=99))["zaman"] != 99:
            return False
        if fn(dict(K, faz="saldir", kanit_ids=[]))["kanit_ids"] != []:
            return False
        if fn(dict(K, faz="guardrail", kanit_ids=[], basarili=False))["basarili"] is not False:
            return False
        for kayit in [
            None, [], dict(K, ek=1), dict(K, id=""), dict(K, id="a b"), dict(K, id="a" * 65), dict(K, id=None),
            dict(K, faz="diger"), dict(K, faz=None), dict(K, basarili=1), dict(K, basarili=None),
            dict(K, kanit_ids=None), dict(K, kanit_ids="k-t"), dict(K, kanit_ids=["k-t", "k-t"]),
            dict(K, kanit_ids=["a b"]), dict(K, kanit_ids=["a" * 65]), dict(K, kanit_ids=[None]), dict(K, kanit_ids=[]),
            dict(K, faz="mudahale", kanit_ids=[]), dict(K, faz="regresyon", kanit_ids=[]),
            dict(K, zaman=-1), dict(K, zaman=True), dict(K, zaman=1.0), dict(K, zaman=None),
        ]:
            try:
                fn(kayit)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(tatbikat_kaydi_dogrula), "faz, kanıt, kimlik ve zaman kuralları korunmalı")
def m_faz(kayit):
    sonuc = tatbikat_kaydi_dogrula(kayit)
    sonuc["faz"] = "saldir"
    return sonuc
def m_kanit(kayit):
    sonuc = tatbikat_kaydi_dogrula(kayit)
    sonuc["kanit_ids"] = []
    return sonuc
def m_zaman(kayit):
    sonuc = tatbikat_kaydi_dogrula(kayit)
    sonuc["zaman"] = 1
    return sonuc
for ad, mutant in [("fazı değiştiren", m_faz), ("kanıtları silen", m_kanit), ("zamanı değiştiren", m_zaman)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def tatbikat_kaydi_dogrula(kayit):
    import re
    if not isinstance(kayit, dict):
        raise ValueError("kayıt sözlük olmalı")
    if set(kayit) != {"id", "faz", "basarili", "kanit_ids", "zaman"}:
        raise ValueError("kayıt şeması geçersiz")
    if not isinstance(kayit["id"], str):
        raise ValueError("kimlik string olmalı")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
        raise ValueError("kimlik geçersiz")
    if kayit["faz"] not in ("saldir", "guardrail", "telemetri", "mudahale", "regresyon"):
        raise ValueError("faz geçersiz")
    if not isinstance(kayit["basarili"], bool):
        raise ValueError("başarılı bool olmalı")
    kanit_ids = kayit["kanit_ids"]
    if not isinstance(kanit_ids, list):
        raise ValueError("kanıtlar liste olmalı")
    for kanit_id in kanit_ids:
        if not isinstance(kanit_id, str):
            raise ValueError("kanıt kimliği string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kanit_id):
            raise ValueError("kanıt kimliği geçersiz")
    if len(set(kanit_ids)) != len(kanit_ids):
        raise ValueError("kanıt kimlikleri yinelenemez")
    if kayit["faz"] in ("telemetri", "mudahale", "regresyon") and not kanit_ids:
        raise ValueError("bu fazda kanıt zorunlu")
    if isinstance(kayit["zaman"], bool) or not isinstance(kayit["zaman"], int):
        raise ValueError("zaman tamsayı olmalı")
    if kayit["zaman"] < 0:
        raise ValueError("zaman negatif olamaz")
    return {"id": kayit["id"], "faz": kayit["faz"], "basarili": kayit["basarili"], "kanit_ids": list(kanit_ids), "zaman": kayit["zaman"]}
```

```hint
Kanıt öğelerini doğruladıktan sonra yineleme ve faz zorunluluğunu denetle. Zaman için sıfırı kabul edip bool değerlerini reddet.
```
:::

::: gorev 2 · Beş fazlı tatbikat akışını doğrula
`tatbikat_akisi_dogrula(kayitlar)` işlevini yaz. Girdi liste olmalı; her kayıt ilk görevdeki kuralları sağlamalı, kayıt kimlikleri ve fazlar kendi içinde benzersiz olmalıdır. Beş fazın tamamı birer kez bulunmalıdır. Geçersiz veride `ValueError` yükselt.

Kayıtları `saldir`, `guardrail`, `telemetri`, `mudahale`, `regresyon` sırasına koy. Zaman bu sırada geriye gidemez; eşit zaman geçerlidir. Her faz için `{"faz":FAZ,"kayit_id":ID,"basarili":BOOL,"kanit_sayisi":N,"zaman":ZAMAN}` döndür. Girdi sırasından bağımsız çalış ve girdileri değiştirme.

```starter
from ai_savunma_veri import json_yukle

def tatbikat_akisi_dogrula(kayitlar):
    # KUSURLU BAŞLANGIÇ KODU: kayıtları faz sırasına değil zamana göre diziyor (eşit zamanda faz sırası
    # kayboluyor, geriye giden zaman hiç yakalanmıyor) ve beş fazın tamamını denetlemiyor!
    akis = sorted(kayitlar, key=lambda x: x["zaman"])
    return [{"faz": x["faz"], "kayit_id": x["id"], "basarili": x["basarili"],
             "kanit_sayisi": len(x["kanit_ids"]), "zaman": x["zaman"]} for x in akis]

for satir in tatbikat_akisi_dogrula(json_yukle("tatbikat/tatbikat_akisi.json")["kayitlar"]):
    print(satir)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-30")
```

```test
import copy
K = [
    {"id": "k-s", "faz": "saldir", "basarili": True, "kanit_ids": [], "zaman": 0},
    {"id": "k-g", "faz": "guardrail", "basarili": True, "kanit_ids": ["k-guard"], "zaman": 2},
    {"id": "k-t", "faz": "telemetri", "basarili": True, "kanit_ids": ["k-trace"], "zaman": 3},
    {"id": "k-m", "faz": "mudahale", "basarili": True, "kanit_ids": ["k-olay", "k-manifest"], "zaman": 5},
    {"id": "k-r", "faz": "regresyon", "basarili": True, "kanit_ids": ["k-eval"], "zaman": 8},
]
BEKLENEN = [
    {"faz": "saldir", "kayit_id": "k-s", "basarili": True, "kanit_sayisi": 0, "zaman": 0},
    {"faz": "guardrail", "kayit_id": "k-g", "basarili": True, "kanit_sayisi": 1, "zaman": 2},
    {"faz": "telemetri", "kayit_id": "k-t", "basarili": True, "kanit_sayisi": 1, "zaman": 3},
    {"faz": "mudahale", "kayit_id": "k-m", "basarili": True, "kanit_sayisi": 2, "zaman": 5},
    {"faz": "regresyon", "kayit_id": "k-r", "basarili": True, "kanit_sayisi": 1, "zaman": 8},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        if fn(K) != BEKLENEN or K != once or fn(list(reversed(K))) != BEKLENEN:
            return False
        esit = [dict(x, zaman=0) for x in K]
        if fn(esit)[-1]["zaman"] != 0:
            return False
        if fn([dict(K[0], id="a" * 64), *K[1:]])[0]["kayit_id"] != "a" * 64:
            return False
        for kayitlar in [
            None, {}, [], [None], K[:4], [K[0], K[0], *K[2:]],
            [dict(K[0], id="a b"), *K[1:]], [dict(K[0], id="a" * 65), *K[1:]], [dict(K[0], id=None), *K[1:]],
            [dict(K[0], faz="diger"), *K[1:]], [dict(K[0], basarili=1), *K[1:]],
            [dict(K[0], kanit_ids=None), *K[1:]], [dict(K[0], kanit_ids=["a" * 65]), *K[1:]],
            [dict(K[2], kanit_ids=[]), *K[:2], *K[3:]], [dict(K[0], zaman=-1), *K[1:]],
            [dict(K[0], zaman=True), *K[1:]], [dict(K[0], zaman=1.0), *K[1:]],
            [K[0], K[1], dict(K[2], zaman=1), K[3], K[4]],
        ]:
            try:
                fn(kayitlar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(tatbikat_akisi_dogrula), "faz bütünlüğü, sıra ve zaman korunmalı")
def m_faz(kayitlar):
    return tatbikat_akisi_dogrula([dict(x, faz="saldir") for x in kayitlar])
def m_zaman(kayitlar):
    return tatbikat_akisi_dogrula([dict(x, zaman=99) for x in kayitlar])
def m_kanit(kayitlar):
    return tatbikat_akisi_dogrula([dict(x, kanit_ids=[]) for x in kayitlar])
for ad, mutant in [("fazları bozan", m_faz), ("zamanları değiştiren", m_zaman), ("kanıtları silen", m_kanit)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

raises(ValueError,tatbikat_akisi_dogrula,[K[0],dict(K[1],id=K[0]['id'])]+K[2:],msg='farklı fazda aynı kayıt kimliği ret')
# --- carbon-c8-ek-bas ---
_ak30 = [{"id": f"f-{i}", "faz": fz, "basarili": True, "kanit_ids": ["k-1"], "zaman": i * 10} for i, fz in enumerate(("saldir", "guardrail", "telemetri", "mudahale", "regresyon"))]
raises(ValueError, tatbikat_akisi_dogrula, _ak30 + [{"id": "f-ek", "faz": "saldir", "basarili": True, "kanit_ids": ["k-1"], "zaman": 90}], msg="yinelenen faz reddedilmeli")
raises(ValueError, tatbikat_akisi_dogrula, [dict(_ak30[0], id=123)] + _ak30[1:], msg="id str olmalı")
raises(ValueError, tatbikat_akisi_dogrula, [dict(_ak30[0], kanit_ids=[123])] + _ak30[1:], msg="kanıt id str olmalı")
raises(ValueError, tatbikat_akisi_dogrula, [dict(_ak30[0], basarili=1)] + _ak30[1:], msg="basarili bool olmalı")
raises(ValueError, tatbikat_akisi_dogrula, [dict(_ak30[0], zaman=True)] + _ak30[1:], msg="zaman bool olamaz")
raises(ValueError, tatbikat_akisi_dogrula, [dict(_ak30[0], zaman=-1)] + _ak30[1:], msg="zaman negatif olamaz")
raises(ValueError, tatbikat_akisi_dogrula, _ak30[:2] + [dict(_ak30[2], kanit_ids=[])] + _ak30[3:], msg="telemetri fazında kanıt zorunlu")
raises(ValueError, tatbikat_akisi_dogrula, [dict(_ak30[0], ek=1)] + _ak30[1:], msg="fazla anahtar reddedilmeli")
raises(ValueError, tatbikat_akisi_dogrula, _ak30 + [{"id": "f-ek2", "faz": "saldir", "basarili": True, "kanit_ids": ["k-1"], "zaman": 0}], msg="aynı zamanda yinelenen faz reddedilmeli")
raises(ValueError, tatbikat_akisi_dogrula, [dict(_ak30[0], kanit_ids=["k-1", "k-1"])] + _ak30[1:], msg="yinelenen kanıt kimliği reddedilmeli")
# --- carbon-c8-ek-son ---
```

```solution
def tatbikat_akisi_dogrula(kayitlar):
    import re
    faz_sirasi = ("saldir", "guardrail", "telemetri", "mudahale", "regresyon")
    if not isinstance(kayitlar, list):
        raise ValueError("kayıtlar liste olmalı")
    ids = set()
    fazlar = set()
    for kayit in kayitlar:
        if not isinstance(kayit, dict):
            raise ValueError("kayıt sözlük olmalı")
        if set(kayit) != {"id", "faz", "basarili", "kanit_ids", "zaman"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(kayit["id"], str):
            raise ValueError("kimlik string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
            raise ValueError("kimlik geçersiz")
        if kayit["id"] in ids:
            raise ValueError("kayıt kimliği yinelenemez")
        ids.add(kayit["id"])
        if kayit["faz"] not in faz_sirasi:
            raise ValueError("faz geçersiz")
        if kayit["faz"] in fazlar:
            raise ValueError("faz yinelenemez")
        fazlar.add(kayit["faz"])
        if not isinstance(kayit["basarili"], bool):
            raise ValueError("başarılı bool olmalı")
        kanit_ids = kayit["kanit_ids"]
        if not isinstance(kanit_ids, list):
            raise ValueError("kanıtlar liste olmalı")
        for kanit_id in kanit_ids:
            if not isinstance(kanit_id, str):
                raise ValueError("kanıt kimliği string olmalı")
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kanit_id):
                raise ValueError("kanıt kimliği geçersiz")
        if len(set(kanit_ids)) != len(kanit_ids):
            raise ValueError("kanıt kimlikleri yinelenemez")
        if kayit["faz"] in ("telemetri", "mudahale", "regresyon") and not kanit_ids:
            raise ValueError("bu fazda kanıt zorunlu")
        if isinstance(kayit["zaman"], bool) or not isinstance(kayit["zaman"], int):
            raise ValueError("zaman tamsayı olmalı")
        if kayit["zaman"] < 0:
            raise ValueError("zaman negatif olamaz")
    if fazlar != set(faz_sirasi):
        raise ValueError("beş faz zorunlu")
    akis = sorted(kayitlar, key=lambda x: faz_sirasi.index(x["faz"]))
    for onceki, sonraki in zip(akis, akis[1:]):
        if sonraki["zaman"] < onceki["zaman"]:
            raise ValueError("zaman geriye gidemez")
    return [{"faz": x["faz"], "kayit_id": x["id"], "basarili": x["basarili"], "kanit_sayisi": len(x["kanit_ids"]), "zaman": x["zaman"]} for x in akis]
```

```hint
Faz kümesini sabit sıra tupleıyla karşılaştır. Kayıtları bu tupleın indeksiyle sıraladıktan sonra komşu zamanları denetle.
```
:::

::: gorev 3 · Purple tatbikat raporu üret
`purple_raporu(kayitlar)` işlevini yaz. Girdi ikinci görevdeki bütün faz, kanıt, kimlik ve zaman kurallarını sağlasın; geçersiz veride `ValueError` yükselt.

`{"karar":KARAR,"tamamlanan_faz":N,"toplam_kanit":N,"sure":SURE,"basarisiz_fazlar":[...]}` döndür. Tamamlanan faz sayısı `basarili=True` kayıtların sayısı, toplam kanıt bütün kanıt listelerinin uzunlukları toplamı, süre son ve ilk fazın zaman farkıdır. Bütün fazlar başarılıysa karar `gecti`, aksi halde `kaldi` olur. Başarısız fazları akış sırasıyla listele ve girdileri değiştirme.

```starter
from ai_savunma_veri import json_yukle

def purple_raporu(kayitlar):
    # KUSURLU BAŞLANGIÇ KODU: beş fazın dördü başarılıysa "gecti" diyor; başarısız guardrail
    # tatbikatı geçirebiliyor ve başarısız faz listesi hep boş kalıyor!
    tamamlanan = sum(1 for x in kayitlar if x["basarili"])
    zamanlar = [x["zaman"] for x in kayitlar]
    return {"karar": "gecti" if tamamlanan >= 4 else "kaldi", "tamamlanan_faz": tamamlanan,
            "toplam_kanit": sum(len(x["kanit_ids"]) for x in kayitlar),
            "sure": max(zamanlar) - min(zamanlar), "basarisiz_fazlar": []}

print(purple_raporu(json_yukle("tatbikat/purple_kayitlari.json")["kayitlar"]))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-30")
```

```test
import copy
K = [
    {"id": "k-s", "faz": "saldir", "basarili": True, "kanit_ids": [], "zaman": 0},
    {"id": "k-g", "faz": "guardrail", "basarili": True, "kanit_ids": ["k-guard"], "zaman": 2},
    {"id": "k-t", "faz": "telemetri", "basarili": True, "kanit_ids": ["k-trace"], "zaman": 3},
    {"id": "k-m", "faz": "mudahale", "basarili": True, "kanit_ids": ["k-olay", "k-manifest"], "zaman": 5},
    {"id": "k-r", "faz": "regresyon", "basarili": True, "kanit_ids": ["k-eval"], "zaman": 8},
]
BEKLENEN = {"karar": "gecti", "tamamlanan_faz": 5, "toplam_kanit": 5, "sure": 8, "basarisiz_fazlar": []}
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        if fn(K) != BEKLENEN or K != once or fn(list(reversed(K))) != BEKLENEN:
            return False
        bozuk = [dict(K[0]), dict(K[1], basarili=False), K[2], K[3], dict(K[4], basarili=False)]
        sonuc = fn(bozuk)
        if sonuc != {"karar": "kaldi", "tamamlanan_faz": 3, "toplam_kanit": 5, "sure": 8, "basarisiz_fazlar": ["guardrail", "regresyon"]}:
            return False
        esit = [dict(x, zaman=0) for x in K]
        if fn(esit)["sure"] != 0:
            return False
        if fn([dict(K[0], id="a" * 64), *K[1:]])["karar"] != "gecti":
            return False
        for kayitlar in [
            None, {}, [], [None], K[:4], [K[0], K[0], *K[2:]],
            [dict(K[0], id="a b"), *K[1:]], [dict(K[0], id="a" * 65), *K[1:]], [dict(K[0], id=None), *K[1:]],
            [dict(K[0], faz="diger"), *K[1:]], [dict(K[0], basarili=1), *K[1:]],
            [dict(K[0], kanit_ids=None), *K[1:]], [dict(K[0], kanit_ids=["a" * 65]), *K[1:]],
            [dict(K[2], kanit_ids=[]), *K[:2], *K[3:]], [dict(K[0], zaman=-1), *K[1:]],
            [dict(K[0], zaman=True), *K[1:]], [dict(K[0], zaman=1.0), *K[1:]],
            [K[0], K[1], dict(K[2], zaman=1), K[3], K[4]],
        ]:
            try:
                fn(kayitlar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(purple_raporu), "karar, faz sayısı, kanıt ve süre korunmalı")
def m_basarili(kayitlar):
    return purple_raporu([dict(x, basarili=False) for x in kayitlar])
def m_kanit(kayitlar):
    return purple_raporu([dict(x, kanit_ids=[]) for x in kayitlar])
def m_zaman(kayitlar):
    return purple_raporu([dict(x, zaman=0) for x in kayitlar])
for ad, mutant in [("başarıyı silen", m_basarili), ("kanıtları silen", m_kanit), ("süreyi silen", m_zaman)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
shifted=[dict(k,zaman=k["zaman"]+100) for k in K]
eq(purple_raporu(shifted)["sure"],8,"süre farkı başlangıç zamanından bağımsız")

raises(ValueError,purple_raporu,[K[0],dict(K[1],id=K[0]['id'])]+K[2:],msg='raporda farklı fazda aynı kayıt kimliği ret')
# --- carbon-c8-ek-bas ---
_ak30p = [{"id": f"f-{i}", "faz": fz, "basarili": True, "kanit_ids": ["k-1"], "zaman": i * 10} for i, fz in enumerate(("saldir", "guardrail", "telemetri", "mudahale", "regresyon"))]
raises(ValueError, purple_raporu, _ak30p + [{"id": "f-ek", "faz": "saldir", "basarili": True, "kanit_ids": ["k-1"], "zaman": 90}], msg="yinelenen faz reddedilmeli")
raises(ValueError, purple_raporu, [dict(_ak30p[0], id=123)] + _ak30p[1:], msg="id str olmalı")
raises(ValueError, purple_raporu, [dict(_ak30p[0], kanit_ids=[123])] + _ak30p[1:], msg="kanıt id str olmalı")
raises(ValueError, purple_raporu, [dict(_ak30p[0], basarili=1)] + _ak30p[1:], msg="basarili bool olmalı")
raises(ValueError, purple_raporu, [dict(_ak30p[0], zaman=True)] + _ak30p[1:], msg="zaman bool olamaz")
raises(ValueError, purple_raporu, [dict(_ak30p[0], zaman=-1)] + _ak30p[1:], msg="zaman negatif olamaz")
raises(ValueError, purple_raporu, _ak30p[:2] + [dict(_ak30p[2], kanit_ids=[])] + _ak30p[3:], msg="telemetri fazında kanıt zorunlu")
raises(ValueError, purple_raporu, [dict(_ak30p[0], ek=1)] + _ak30p[1:], msg="fazla anahtar reddedilmeli")
raises(ValueError, purple_raporu, _ak30p + [{"id": "f-ek2", "faz": "saldir", "basarili": True, "kanit_ids": ["k-1"], "zaman": 0}], msg="aynı zamanda yinelenen faz reddedilmeli")
raises(ValueError, purple_raporu, [dict(_ak30p[0], kanit_ids=["k-1", "k-1"])] + _ak30p[1:], msg="yinelenen kanıt kimliği reddedilmeli")
# --- carbon-c8-ek-son ---
```

```solution
def purple_raporu(kayitlar):
    import re
    faz_sirasi = ("saldir", "guardrail", "telemetri", "mudahale", "regresyon")
    if not isinstance(kayitlar, list):
        raise ValueError("kayıtlar liste olmalı")
    ids = set()
    fazlar = set()
    for kayit in kayitlar:
        if not isinstance(kayit, dict):
            raise ValueError("kayıt sözlük olmalı")
        if set(kayit) != {"id", "faz", "basarili", "kanit_ids", "zaman"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(kayit["id"], str):
            raise ValueError("kimlik string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
            raise ValueError("kimlik geçersiz")
        if kayit["id"] in ids:
            raise ValueError("kayıt kimliği yinelenemez")
        ids.add(kayit["id"])
        if kayit["faz"] not in faz_sirasi:
            raise ValueError("faz geçersiz")
        if kayit["faz"] in fazlar:
            raise ValueError("faz yinelenemez")
        fazlar.add(kayit["faz"])
        if not isinstance(kayit["basarili"], bool):
            raise ValueError("başarılı bool olmalı")
        kanit_ids = kayit["kanit_ids"]
        if not isinstance(kanit_ids, list):
            raise ValueError("kanıtlar liste olmalı")
        for kanit_id in kanit_ids:
            if not isinstance(kanit_id, str):
                raise ValueError("kanıt kimliği string olmalı")
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kanit_id):
                raise ValueError("kanıt kimliği geçersiz")
        if len(set(kanit_ids)) != len(kanit_ids):
            raise ValueError("kanıt kimlikleri yinelenemez")
        if kayit["faz"] in ("telemetri", "mudahale", "regresyon") and not kanit_ids:
            raise ValueError("bu fazda kanıt zorunlu")
        if isinstance(kayit["zaman"], bool) or not isinstance(kayit["zaman"], int):
            raise ValueError("zaman tamsayı olmalı")
        if kayit["zaman"] < 0:
            raise ValueError("zaman negatif olamaz")
    if fazlar != set(faz_sirasi):
        raise ValueError("beş faz zorunlu")
    akis = sorted(kayitlar, key=lambda x: faz_sirasi.index(x["faz"]))
    for onceki, sonraki in zip(akis, akis[1:]):
        if sonraki["zaman"] < onceki["zaman"]:
            raise ValueError("zaman geriye gidemez")
    tamamlanan = sum(1 for x in akis if x["basarili"])
    toplam_kanit = sum(len(x["kanit_ids"]) for x in akis)
    sure = akis[-1]["zaman"] - akis[0]["zaman"]
    basarisiz = [x["faz"] for x in akis if not x["basarili"]]
    karar = "gecti" if not basarisiz else "kaldi"
    return {"karar": karar, "tamamlanan_faz": tamamlanan, "toplam_kanit": toplam_kanit, "sure": sure, "basarisiz_fazlar": basarisiz}
```

```hint
Akışı ikinci görevdeki gibi doğrulayıp sırala. Başarısız faz listesini önce üret; kararı bu listenin boş olup olmamasından türet.
```
:::

::: anlat Beş faz gerçekten koşar: model sızdırsa bile teslim edilen çıktı korunur mu?
Önceki üç görevde faz kaydını doğruladın, akışı faz sırasına koydun ve purple raporu ürettin. Şimdi aynı üç işlevi **gerçekten koşan bir tatbikata** bağlıyoruz:

1. `saldir`: Kasıtlı zayıf bir asistana (hata ayıklama bahanesiyle kodu paylaşabilen) yerel Ollama modelinde zararsız canary çıkarma isteği gönderilir. Bu fazın başarısı yanıtın gerçekten alınmasıdır,
2. `guardrail`: Aynı saldırı, teslimden önce bilinen sırları karartan bir çıktı filtresinden geçer; başarı, kullanıcıya teslim edilen metinde canary'nin normalize edilmiş biçimiyle bile bulunmamasıdır,
3. `telemetri`: İki koşunun olayları deneyin kendi geçici klasöründe JSONL dosyasına yazılır ve geri okunur; kanıt kimlikleri olay kimlikleridir,
4. `mudahale`: Sır döndürülür; manifest yalnız eski ve yeni sırrın SHA-256 özetini taşır, sırrın kendisini değil,
5. `regresyon`: Üç saldırı vakası yeni sırla korumalı hatta tekrar koşulur.

Kayıtlar karışık sırayla senin işlevlerine verilir. Kanıtta iki rapora bak: `rapor` gerçek tatbikatın sonucudur; `guardrail_kapali_kontrol_raporu` ise aynı canlı koşuda filtre olmasaydı guardrail fazının ne olacağını gösterir. `saldiri_ham_sizinti` ve `regresyon_ham_sizinti` alanları modelin kendisinin sızdırıp sızdırmadığını, `regresyon_teslim_sizinti` ise kullanıcıya ulaşan sızıntıyı sayar. Model ham çıktıda sızdırırken teslim edilen çıktının temiz kalması, katmanlı savunmanın neden tek başına modele güvenmekten daha sağlam olduğunu gösterir. Yine de filtre basit dizgi eşleştirmesidir; parçalı veya kodlanmış sızıntıyı kaçırabilir, bu yüzden regresyon paketi düzenli genişletilmelidir. Deney bitince geçici klasör silinir ve deneyin yüklediği model boşaltılır.
:::

::: gorev Gerçek deney · Yerel Ollama ile beş fazlı purple tatbikatı ve kanıtlı rapor
Önceki üç görevde yazdığın `tatbikat_kaydi_dogrula(kayit)`, `tatbikat_akisi_dogrula(kayitlar)` ve `purple_raporu(kayitlar)` işlevlerini burada birleştir.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab
from sandbox import ai_gercek_ai_savunma_30 as L

def tatbikat_kaydi_dogrula(kayit):
    return kayit

def tatbikat_akisi_dogrula(kayitlar):
    return []

def purple_raporu(kayitlar):
    # KUSURLU BAŞLANGIÇ KODU: beş fazın dördü başarılıysa "gecti" diyor!
    tamamlanan = sum(1 for x in kayitlar if x["basarili"])
    return {"karar": "gecti" if tamamlanan >= 4 else "kaldi", "tamamlanan_faz": tamamlanan,
            "toplam_kanit": 0, "sure": 0, "basarisiz_fazlar": []}

if ai_lab.CALISTIR:
    L.goster(tatbikat_kaydi_dogrula, tatbikat_akisi_dogrula, purple_raporu)
```

```test
import ai_lab
from sandbox import ai_gercek_ai_savunma_30 as L

checks = []
_base_ok = ok
def ok(kosul, mesaj):
    checks.append(bool(kosul))
    return _base_ok(kosul, mesaj)

for s in ai_lab.kod_denetimi(src, yasak=("tatbikat_kaydi_dogrula_referans", "tatbikat_akisi_dogrula_referans", "purple_raporu_referans", "kanit_yaz", "cikti_filtresi")):
    ok(False, f"Güvenlik/kopya denetimi: {s}")
if not all(checks):
    stop()

def _sozlesme_kontrol():
    try:
        K = [
            {"id": "a", "faz": "regresyon", "basarili": True, "kanit_ids": ["e1"], "zaman": 9},
            {"id": "b", "faz": "saldir", "basarili": True, "kanit_ids": [], "zaman": 0},
            {"id": "c", "faz": "telemetri", "basarili": True, "kanit_ids": ["t1", "t2"], "zaman": 4},
            {"id": "d", "faz": "guardrail", "basarili": False, "kanit_ids": ["g1"], "zaman": 4},
            {"id": "e", "faz": "mudahale", "basarili": True, "kanit_ids": ["o1"], "zaman": 6},
        ]
        tek = tatbikat_kaydi_dogrula(K[0])
        if tek != K[0] or tek is K[0] or tek["kanit_ids"] is K[0]["kanit_ids"]:
            return False
        for bozuk in [dict(K[2], kanit_ids=[]), dict(K[1], zaman=True), dict(K[1], ek=1)]:
            try:
                tatbikat_kaydi_dogrula(bozuk)
                return False
            except ValueError:
                pass
        if [x["faz"] for x in tatbikat_akisi_dogrula(K)] != ["saldir", "guardrail", "telemetri", "mudahale", "regresyon"]:
            return False
        try:
            tatbikat_akisi_dogrula(K[:4])
            return False
        except ValueError:
            pass
        if purple_raporu(K) != {"karar": "kaldi", "tamamlanan_faz": 4, "toplam_kanit": 5, "sure": 9, "basarisiz_fazlar": ["guardrail"]}:
            return False
        return True
    except Exception:
        return False

ok(_sozlesme_kontrol(), "tatbikat_kaydi_dogrula, tatbikat_akisi_dogrula ve purple_raporu sözleşme kontrollerini geçmeli")
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
    tatbikat_kaydi_dogrula = need('tatbikat_kaydi_dogrula')
    tatbikat_akisi_dogrula = need('tatbikat_akisi_dogrula')
    purple_raporu = need('purple_raporu')
    def _birim_adim_1():
        import copy
        K = {"id": "k-1", "faz": "telemetri", "basarili": True, "kanit_ids": ["k-t"], "zaman": 0}
        def sozlesme(fn):
            try:
                once = copy.deepcopy(K)
                sonuc = fn(K)
                if sonuc != K or K != once or sonuc is K or sonuc["kanit_ids"] is K["kanit_ids"]:
                    return False
                if fn(dict(K, id="a" * 64, kanit_ids=["b" * 64], zaman=99))["zaman"] != 99:
                    return False
                if fn(dict(K, faz="saldir", kanit_ids=[]))["kanit_ids"] != []:
                    return False
                if fn(dict(K, faz="guardrail", kanit_ids=[], basarili=False))["basarili"] is not False:
                    return False
                for kayit in [
                    None, [], dict(K, ek=1), dict(K, id=""), dict(K, id="a b"), dict(K, id="a" * 65), dict(K, id=None),
                    dict(K, faz="diger"), dict(K, faz=None), dict(K, basarili=1), dict(K, basarili=None),
                    dict(K, kanit_ids=None), dict(K, kanit_ids="k-t"), dict(K, kanit_ids=["k-t", "k-t"]),
                    dict(K, kanit_ids=["a b"]), dict(K, kanit_ids=["a" * 65]), dict(K, kanit_ids=[None]), dict(K, kanit_ids=[]),
                    dict(K, faz="mudahale", kanit_ids=[]), dict(K, faz="regresyon", kanit_ids=[]),
                    dict(K, zaman=-1), dict(K, zaman=True), dict(K, zaman=1.0), dict(K, zaman=None),
                ]:
                    try:
                        fn(kayit)
                        return False
                    except ValueError:
                        pass
                return True
            except Exception:
                return False
        ok(sozlesme(tatbikat_kaydi_dogrula), "faz, kanıt, kimlik ve zaman kuralları korunmalı")
        def m_faz(kayit):
            sonuc = tatbikat_kaydi_dogrula(kayit)
            sonuc["faz"] = "saldir"
            return sonuc
        def m_kanit(kayit):
            sonuc = tatbikat_kaydi_dogrula(kayit)
            sonuc["kanit_ids"] = []
            return sonuc
        def m_zaman(kayit):
            sonuc = tatbikat_kaydi_dogrula(kayit)
            sonuc["zaman"] = 1
            return sonuc
        for ad, mutant in [("fazı değiştiren", m_faz), ("kanıtları silen", m_kanit), ("zamanı değiştiren", m_zaman)]:
            ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
    try:
        _birim_adim_1()
    except Exception:
        _u.append(False)
    def _birim_adim_2():
        import copy
        K = [
            {"id": "k-s", "faz": "saldir", "basarili": True, "kanit_ids": [], "zaman": 0},
            {"id": "k-g", "faz": "guardrail", "basarili": True, "kanit_ids": ["k-guard"], "zaman": 2},
            {"id": "k-t", "faz": "telemetri", "basarili": True, "kanit_ids": ["k-trace"], "zaman": 3},
            {"id": "k-m", "faz": "mudahale", "basarili": True, "kanit_ids": ["k-olay", "k-manifest"], "zaman": 5},
            {"id": "k-r", "faz": "regresyon", "basarili": True, "kanit_ids": ["k-eval"], "zaman": 8},
        ]
        BEKLENEN = [
            {"faz": "saldir", "kayit_id": "k-s", "basarili": True, "kanit_sayisi": 0, "zaman": 0},
            {"faz": "guardrail", "kayit_id": "k-g", "basarili": True, "kanit_sayisi": 1, "zaman": 2},
            {"faz": "telemetri", "kayit_id": "k-t", "basarili": True, "kanit_sayisi": 1, "zaman": 3},
            {"faz": "mudahale", "kayit_id": "k-m", "basarili": True, "kanit_sayisi": 2, "zaman": 5},
            {"faz": "regresyon", "kayit_id": "k-r", "basarili": True, "kanit_sayisi": 1, "zaman": 8},
        ]
        def sozlesme(fn):
            try:
                once = copy.deepcopy(K)
                if fn(K) != BEKLENEN or K != once or fn(list(reversed(K))) != BEKLENEN:
                    return False
                esit = [dict(x, zaman=0) for x in K]
                if fn(esit)[-1]["zaman"] != 0:
                    return False
                if fn([dict(K[0], id="a" * 64), *K[1:]])[0]["kayit_id"] != "a" * 64:
                    return False
                for kayitlar in [
                    None, {}, [], [None], K[:4], [K[0], K[0], *K[2:]],
                    [dict(K[0], id="a b"), *K[1:]], [dict(K[0], id="a" * 65), *K[1:]], [dict(K[0], id=None), *K[1:]],
                    [dict(K[0], faz="diger"), *K[1:]], [dict(K[0], basarili=1), *K[1:]],
                    [dict(K[0], kanit_ids=None), *K[1:]], [dict(K[0], kanit_ids=["a" * 65]), *K[1:]],
                    [dict(K[2], kanit_ids=[]), *K[:2], *K[3:]], [dict(K[0], zaman=-1), *K[1:]],
                    [dict(K[0], zaman=True), *K[1:]], [dict(K[0], zaman=1.0), *K[1:]],
                    [K[0], K[1], dict(K[2], zaman=1), K[3], K[4]],
                ]:
                    try:
                        fn(kayitlar)
                        return False
                    except ValueError:
                        pass
                return True
            except Exception:
                return False
        ok(sozlesme(tatbikat_akisi_dogrula), "faz bütünlüğü, sıra ve zaman korunmalı")
        def m_faz(kayitlar):
            return tatbikat_akisi_dogrula([dict(x, faz="saldir") for x in kayitlar])
        def m_zaman(kayitlar):
            return tatbikat_akisi_dogrula([dict(x, zaman=99) for x in kayitlar])
        def m_kanit(kayitlar):
            return tatbikat_akisi_dogrula([dict(x, kanit_ids=[]) for x in kayitlar])
        for ad, mutant in [("fazları bozan", m_faz), ("zamanları değiştiren", m_zaman), ("kanıtları silen", m_kanit)]:
            ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

        raises(ValueError,tatbikat_akisi_dogrula,[K[0],dict(K[1],id=K[0]['id'])]+K[2:],msg='farklı fazda aynı kayıt kimliği ret')
        _ak30 = [{"id": f"f-{i}", "faz": fz, "basarili": True, "kanit_ids": ["k-1"], "zaman": i * 10} for i, fz in enumerate(("saldir", "guardrail", "telemetri", "mudahale", "regresyon"))]
        raises(ValueError, tatbikat_akisi_dogrula, _ak30 + [{"id": "f-ek", "faz": "saldir", "basarili": True, "kanit_ids": ["k-1"], "zaman": 90}], msg="yinelenen faz reddedilmeli")
        raises(ValueError, tatbikat_akisi_dogrula, [dict(_ak30[0], id=123)] + _ak30[1:], msg="id str olmalı")
        raises(ValueError, tatbikat_akisi_dogrula, [dict(_ak30[0], kanit_ids=[123])] + _ak30[1:], msg="kanıt id str olmalı")
        raises(ValueError, tatbikat_akisi_dogrula, [dict(_ak30[0], basarili=1)] + _ak30[1:], msg="basarili bool olmalı")
        raises(ValueError, tatbikat_akisi_dogrula, [dict(_ak30[0], zaman=True)] + _ak30[1:], msg="zaman bool olamaz")
        raises(ValueError, tatbikat_akisi_dogrula, [dict(_ak30[0], zaman=-1)] + _ak30[1:], msg="zaman negatif olamaz")
        raises(ValueError, tatbikat_akisi_dogrula, _ak30[:2] + [dict(_ak30[2], kanit_ids=[])] + _ak30[3:], msg="telemetri fazında kanıt zorunlu")
        raises(ValueError, tatbikat_akisi_dogrula, [dict(_ak30[0], ek=1)] + _ak30[1:], msg="fazla anahtar reddedilmeli")
        raises(ValueError, tatbikat_akisi_dogrula, _ak30 + [{"id": "f-ek2", "faz": "saldir", "basarili": True, "kanit_ids": ["k-1"], "zaman": 0}], msg="aynı zamanda yinelenen faz reddedilmeli")
        raises(ValueError, tatbikat_akisi_dogrula, [dict(_ak30[0], kanit_ids=["k-1", "k-1"])] + _ak30[1:], msg="yinelenen kanıt kimliği reddedilmeli")
    try:
        _birim_adim_2()
    except Exception:
        _u.append(False)
    def _birim_adim_3():
        import copy
        K = [
            {"id": "k-s", "faz": "saldir", "basarili": True, "kanit_ids": [], "zaman": 0},
            {"id": "k-g", "faz": "guardrail", "basarili": True, "kanit_ids": ["k-guard"], "zaman": 2},
            {"id": "k-t", "faz": "telemetri", "basarili": True, "kanit_ids": ["k-trace"], "zaman": 3},
            {"id": "k-m", "faz": "mudahale", "basarili": True, "kanit_ids": ["k-olay", "k-manifest"], "zaman": 5},
            {"id": "k-r", "faz": "regresyon", "basarili": True, "kanit_ids": ["k-eval"], "zaman": 8},
        ]
        BEKLENEN = {"karar": "gecti", "tamamlanan_faz": 5, "toplam_kanit": 5, "sure": 8, "basarisiz_fazlar": []}
        def sozlesme(fn):
            try:
                once = copy.deepcopy(K)
                if fn(K) != BEKLENEN or K != once or fn(list(reversed(K))) != BEKLENEN:
                    return False
                bozuk = [dict(K[0]), dict(K[1], basarili=False), K[2], K[3], dict(K[4], basarili=False)]
                sonuc = fn(bozuk)
                if sonuc != {"karar": "kaldi", "tamamlanan_faz": 3, "toplam_kanit": 5, "sure": 8, "basarisiz_fazlar": ["guardrail", "regresyon"]}:
                    return False
                esit = [dict(x, zaman=0) for x in K]
                if fn(esit)["sure"] != 0:
                    return False
                if fn([dict(K[0], id="a" * 64), *K[1:]])["karar"] != "gecti":
                    return False
                for kayitlar in [
                    None, {}, [], [None], K[:4], [K[0], K[0], *K[2:]],
                    [dict(K[0], id="a b"), *K[1:]], [dict(K[0], id="a" * 65), *K[1:]], [dict(K[0], id=None), *K[1:]],
                    [dict(K[0], faz="diger"), *K[1:]], [dict(K[0], basarili=1), *K[1:]],
                    [dict(K[0], kanit_ids=None), *K[1:]], [dict(K[0], kanit_ids=["a" * 65]), *K[1:]],
                    [dict(K[2], kanit_ids=[]), *K[:2], *K[3:]], [dict(K[0], zaman=-1), *K[1:]],
                    [dict(K[0], zaman=True), *K[1:]], [dict(K[0], zaman=1.0), *K[1:]],
                    [K[0], K[1], dict(K[2], zaman=1), K[3], K[4]],
                ]:
                    try:
                        fn(kayitlar)
                        return False
                    except ValueError:
                        pass
                return True
            except Exception:
                return False
        ok(sozlesme(purple_raporu), "karar, faz sayısı, kanıt ve süre korunmalı")
        def m_basarili(kayitlar):
            return purple_raporu([dict(x, basarili=False) for x in kayitlar])
        def m_kanit(kayitlar):
            return purple_raporu([dict(x, kanit_ids=[]) for x in kayitlar])
        def m_zaman(kayitlar):
            return purple_raporu([dict(x, zaman=0) for x in kayitlar])
        for ad, mutant in [("başarıyı silen", m_basarili), ("kanıtları silen", m_kanit), ("süreyi silen", m_zaman)]:
            ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
        shifted=[dict(k,zaman=k["zaman"]+100) for k in K]
        eq(purple_raporu(shifted)["sure"],8,"süre farkı başlangıç zamanından bağımsız")

        raises(ValueError,purple_raporu,[K[0],dict(K[1],id=K[0]['id'])]+K[2:],msg='raporda farklı fazda aynı kayıt kimliği ret')
        _ak30p = [{"id": f"f-{i}", "faz": fz, "basarili": True, "kanit_ids": ["k-1"], "zaman": i * 10} for i, fz in enumerate(("saldir", "guardrail", "telemetri", "mudahale", "regresyon"))]
        raises(ValueError, purple_raporu, _ak30p + [{"id": "f-ek", "faz": "saldir", "basarili": True, "kanit_ids": ["k-1"], "zaman": 90}], msg="yinelenen faz reddedilmeli")
        raises(ValueError, purple_raporu, [dict(_ak30p[0], id=123)] + _ak30p[1:], msg="id str olmalı")
        raises(ValueError, purple_raporu, [dict(_ak30p[0], kanit_ids=[123])] + _ak30p[1:], msg="kanıt id str olmalı")
        raises(ValueError, purple_raporu, [dict(_ak30p[0], basarili=1)] + _ak30p[1:], msg="basarili bool olmalı")
        raises(ValueError, purple_raporu, [dict(_ak30p[0], zaman=True)] + _ak30p[1:], msg="zaman bool olamaz")
        raises(ValueError, purple_raporu, [dict(_ak30p[0], zaman=-1)] + _ak30p[1:], msg="zaman negatif olamaz")
        raises(ValueError, purple_raporu, _ak30p[:2] + [dict(_ak30p[2], kanit_ids=[])] + _ak30p[3:], msg="telemetri fazında kanıt zorunlu")
        raises(ValueError, purple_raporu, [dict(_ak30p[0], ek=1)] + _ak30p[1:], msg="fazla anahtar reddedilmeli")
        raises(ValueError, purple_raporu, _ak30p + [{"id": "f-ek2", "faz": "saldir", "basarili": True, "kanit_ids": ["k-1"], "zaman": 0}], msg="aynı zamanda yinelenen faz reddedilmeli")
        raises(ValueError, purple_raporu, [dict(_ak30p[0], kanit_ids=["k-1", "k-1"])] + _ak30p[1:], msg="yinelenen kanıt kimliği reddedilmeli")
    try:
        _birim_adim_3()
    except Exception:
        _u.append(False)
    return bool(_u) and all(_u)
ok(_c8_birim_denetimi(), "deney öncesi tam birim sözleşmesi korunmalı")
# --- carbon-c8-g4-son ---
if not all(checks):
    stop()

try:
    rapor = L.deney(tatbikat_kaydi_dogrula, tatbikat_akisi_dogrula, purple_raporu)
except ai_lab.GercekLabYok as e:
    ok(False, str(e))
    stop()
except Exception as e:
    ok(False, f"GERÇEK PURPLE TATBİKATI YAPILAMADI: {type(e).__name__}: {e}")
    stop()

k = rapor["kontroller"]
ok(k["kayit_uyumu"], f"tatbikat_kaydi_dogrula canlı faz kayıtlarında referansla aynı sonucu vermeli: {rapor['kayitlar']}")
ok(k["akis_uyumu"], f"tatbikat_akisi_dogrula karışık sıradaki canlı kayıtlarda referansla uyuşmalı: {rapor['ogrenci']['akis']}")
ok(k["rapor_uyumu"], f"purple_raporu canlı tatbikatta ve guardrail kapalı kontrolde referansla uyuşmalı: {rapor['ogrenci']}")
ok(k["tatbikat_tam"], "beş faz gerçekten koşmalı: yanıt alındı, telemetri dosyadan eksiksiz okundu, sır döndürüldü, regresyon paketi koştu")
ok(k["gecici_silindi"], "deneyin geçici telemetri klasörü silinmeli")
ok(k["cihaz_dogrulandi"], f"Ollama cihaz kaydı doğrulanmalı: {rapor['ortam'].get('bellek')}")
ok(k["kaynak_temizlendi"], f"deney yalnız kendi başlattığı kaynağı kapatmalı: {rapor['ortam'].get('temizlik')}")

kabul = all(checks)
kanit_yolu = ai_lab.kanit_yaz("savunma-30-purple-tatbikati", dict(rapor, kaynak="gercek", kabul=kabul))
o = rapor["ozet"]
print(f"GERÇEK PURPLE TATBİKATI: model={o['model']} karar={o['rapor']['karar']} kontrol={o['guardrail_kapali_kontrol_raporu']['karar']} "
      f"regresyon ham/teslim={o['regresyon_ham_sizinti']}/{o['regresyon_teslim_sizinti']} kanıt={kanit_yolu}")
```

```solution
import re
import ai_lab
from sandbox import ai_gercek_ai_savunma_30 as L

FAZLAR = ("saldir", "guardrail", "telemetri", "mudahale", "regresyon")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")

def tatbikat_kaydi_dogrula(kayit):
    if not isinstance(kayit, dict) or set(kayit) != {"id", "faz", "basarili", "kanit_ids", "zaman"}:
        raise ValueError("kayıt şeması geçersiz")
    if not isinstance(kayit["id"], str) or not _ID.fullmatch(kayit["id"]):
        raise ValueError("kimlik geçersiz")
    if kayit["faz"] not in FAZLAR:
        raise ValueError("faz geçersiz")
    if not isinstance(kayit["basarili"], bool):
        raise ValueError("başarılı bool olmalı")
    k = kayit["kanit_ids"]
    if not isinstance(k, list) or any(not isinstance(x, str) or not _ID.fullmatch(x) for x in k) or len(set(k)) != len(k):
        raise ValueError("kanıtlar geçersiz")
    if kayit["faz"] in ("telemetri", "mudahale", "regresyon") and not k:
        raise ValueError("bu fazda kanıt zorunlu")
    if isinstance(kayit["zaman"], bool) or not isinstance(kayit["zaman"], int) or kayit["zaman"] < 0:
        raise ValueError("zaman geçersiz")
    return {"id": kayit["id"], "faz": kayit["faz"], "basarili": kayit["basarili"], "kanit_ids": list(k), "zaman": kayit["zaman"]}

def tatbikat_akisi_dogrula(kayitlar):
    if not isinstance(kayitlar, list):
        raise ValueError("kayıtlar liste olmalı")
    ids, fazlar = set(), set()
    for k in kayitlar:
        tatbikat_kaydi_dogrula(k)
        if k["id"] in ids or k["faz"] in fazlar:
            raise ValueError("kimlik veya faz yinelenemez")
        ids.add(k["id"])
        fazlar.add(k["faz"])
    if fazlar != set(FAZLAR):
        raise ValueError("beş faz zorunlu")
    akis = sorted(kayitlar, key=lambda x: FAZLAR.index(x["faz"]))
    for a, b in zip(akis, akis[1:]):
        if b["zaman"] < a["zaman"]:
            raise ValueError("zaman geriye gidemez")
    return [{"faz": x["faz"], "kayit_id": x["id"], "basarili": x["basarili"], "kanit_sayisi": len(x["kanit_ids"]), "zaman": x["zaman"]} for x in akis]

def purple_raporu(kayitlar):
    akis = tatbikat_akisi_dogrula(kayitlar)
    basarisiz = [x["faz"] for x in akis if not x["basarili"]]
    return {"karar": "gecti" if not basarisiz else "kaldi",
            "tamamlanan_faz": sum(1 for x in akis if x["basarili"]),
            "toplam_kanit": sum(x["kanit_sayisi"] for x in akis),
            "sure": akis[-1]["zaman"] - akis[0]["zaman"],
            "basarisiz_fazlar": basarisiz}

if ai_lab.CALISTIR:
    L.goster(tatbikat_kaydi_dogrula, tatbikat_akisi_dogrula, purple_raporu)
```

```hint
Önceki üç görevde yazdığın işlevleri eksiksiz taşı. Kanıtta `rapor` ile `guardrail_kapali_kontrol_raporu` alanlarını, ham ve teslim edilen sızıntı sayılarıyla birlikte oku.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
### Tatbikat her fazın kanıtını bağlar

Saldırı, guardrail, telemetri, müdahale ve rapor fazları yalnız adlarından oluşmaz. Her fazın önceki fazla ilişkisi, durumu ve kanıtı doğrulanmalıdır. Son raporda engellenen canary kadar normal işlevin korunması da görünür olmalıdır. Bu dar yerel tatbikat kurumun tüm olay müdahale olgunluğunu veya bütün saldırı yüzeylerini ölçmez.

| Yaygın yanlış | Mekanizmanın sınırı |
|---|---|
| Beş kayıt beş başarılı fazdır | Faz sırası ve gerçek sonuçlar birlikte sınanır. |

Saldırı–savunma bağlantısı: ai-saldiri-37.
:::

::: anlat Kaynak ile lab sonucunu ayır
[Ollama chat API](https://docs.ollama.com/api/chat). Gerçek model yanıtları APIyle alınır; beş fazlı tatbikat düzeni bu labın kendi iş akışıdır.
:::
