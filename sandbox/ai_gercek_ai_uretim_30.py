# -*- coding: utf-8 -*-
"""ai-uretim-30 gerçek deney: gerçek ubikuitin yapısı (PDB 1UBQ, 76 kalıntı, 1.8 Å) üzerinde öğrencinin SE(3) değişmez
dRMSD'si dönme/öteleme, gürültü ve ayna görüntüsüyle sınanır; aynanın dRMSD'de görünmediği ve kiralitenin ayrıca
ölçülmesi gerektiği gösterilir. Gerçek temas haritasından kurulan çift temsili öğrencinin üçgen çarpımsal
güncellemesine, gerçek aminoasit dizisi ve mesafe yanlılığı öğrencinin MSA satır dikkatine verilir."""
import math, os
import ai_lab
from sandbox import ai_uretim_ortak as O

AYAR = {"pdb": "1UBQ.pdb", "gurultu_a": 0.5, "seed": 30, "h": 8}
UC = {"ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C", "GLN": "Q", "GLU": "E", "GLY": "G", "HIS": "H", "ILE": "I",
      "LEU": "L", "LYS": "K", "MET": "M", "PHE": "F", "PRO": "P", "SER": "S", "THR": "T", "TRP": "W", "TYR": "Y", "VAL": "V"}


def pdb_oku(yol):
    kal = {}
    for s in open(yol, encoding="ascii", errors="replace"):
        if s.startswith("ATOM") and s[16] in " A":
            no, ad, res = int(s[22:26]), s[12:16].strip(), s[17:20]
            kal.setdefault(no, {"res": res})[ad] = (float(s[30:38]), float(s[38:46]), float(s[46:54]))
    return [kal[k] for k in sorted(kal) if {"N", "CA", "C"} <= set(kal[k])]


def _kabsch(torch, A, B):
    a, b = A - A.mean(0), B - B.mean(0)
    U, S, Vh = torch.linalg.svd(a.T @ b)
    dd = torch.sign(torch.det(Vh.T @ U.T))
    R = Vh.T @ torch.diag(torch.tensor([1.0, 1.0, float(dd)], dtype=A.dtype)) @ U.T
    return float(((a @ R.T - b) ** 2).sum(1).mean().sqrt())


def _kiralite(torch, kal, X):
    """CA etrafındaki işaretli hacim (N, C, CB yönleri); L-aminoasitlerde tutarlı işaret."""
    isaret = []
    for i, k in enumerate(kal):
        if "CB" not in k:
            continue
        ca = X["CA"][i]; v = torch.stack([X["N"][i] - ca, X["C"][i] - ca, X["CB"][i] - ca])
        isaret.append(float(torch.det(v)) > 0)
    return sum(isaret) / len(isaret)


def deney(ucgen_carpimsal_guncelle, se3_degismez_rmsd, msa_satir_dikkati):
    torch = O.torch_al()
    yol = os.path.join(O.VERI, AYAR["pdb"])
    if not os.path.isfile(yol):
        raise ai_lab.GercekLabYok(f"{yol} yok")
    kal = pdb_oku(yol)
    CA = torch.tensor([k["CA"] for k in kal], dtype=torch.float64)
    N = CA.shape[0]
    g = torch.Generator().manual_seed(AYAR["seed"])
    Q, _ = torch.linalg.qr(torch.randn(3, 3, generator=g, dtype=torch.float64))
    Q = Q * torch.sign(torch.det(Q))                                         # det +1: saf dönme
    don = CA @ Q.T + torch.tensor([12.0, -7.0, 3.5], dtype=torch.float64)
    gurultu = CA + AYAR["gurultu_a"] * torch.randn(N, 3, generator=g, dtype=torch.float64)
    ayna = CA * torch.tensor([-1.0, 1.0, 1.0], dtype=torch.float64)
    sonuc = {}
    for ad, B in (("dondurulmus", don), ("gurultulu", gurultu), ("ayna", ayna)):
        o = se3_degismez_rmsd(O.liste(CA), O.liste(B))
        ref = float(((torch.cdist(CA, CA) - torch.cdist(B, B)) ** 2).mean().sqrt())
        sonuc[ad] = {"drmsd": o["drmsd"], "ref_drmsd": ref, "kabsch_rmsd": _kabsch(torch, CA, B), "ozdes": o["ozdes_yapi_mi"]}
    drmsd_ayni = all(abs(v["drmsd"] - v["ref_drmsd"]) <= 1e-4 for v in sonuc.values())
    tum = {ad: torch.tensor([k.get(ad, k["CA"]) for k in kal], dtype=torch.float64) for ad in ("N", "CA", "C", "CB")}
    kir_orijinal = _kiralite(torch, kal, tum)
    kir_ayna = _kiralite(torch, kal, {a: v * torch.tensor([-1.0, 1.0, 1.0], dtype=torch.float64) for a, v in tum.items()})
    # Değerlendirme kapısı: yalnız dRMSD'ye bakan bir kabul ölçütü ayna yapıyı "kusursuz" sayar mı? Kiralite eklenince ne olur?
    adim = torch.randn(N, 3, generator=g, dtype=torch.float64)
    rastgele = torch.cumsum(3.8 * adim / adim.norm(dim=1, keepdim=True), 0)              # 3.8 Å adımlı rastgele yürüyüş (yapısız zincir)
    adaylar = {"dondurulmus": ({a: v @ Q.T for a, v in tum.items()}, don), "gurultulu": (tum, gurultu),
               "ayna": ({a: v * torch.tensor([-1.0, 1.0, 1.0], dtype=torch.float64) for a, v in tum.items()}, ayna),
               "rastgele_zincir": (None, rastgele)}
    kapi = {}
    for ad, (atomlar, B) in adaylar.items():
        d = float(((torch.cdist(CA, CA) - torch.cdist(B, B)) ** 2).mean().sqrt())
        k = _kiralite(torch, kal, atomlar) if atomlar is not None else 0.5
        kapi[ad] = {"drmsd": round(d, 4), "kiralite": round(k, 3), "yalniz_drmsd_kabul": d < 1.0, "drmsd_ve_kiralite_kabul": d < 1.0 and k >= 0.8}

    # Üçgen çarpımsal güncelleme: gerçek temas haritasından çift temsili
    D = torch.cdist(CA, CA)
    Z = torch.exp(-D / 8.0)
    z = ucgen_carpimsal_guncelle(O.liste(Z), 0.5, 0.5)
    A_, B_ = 0.5 * Z, 0.5 * Z
    ref_z = Z + (A_ @ B_.T) / math.sqrt(N)
    ucgen_fark = O.en_buyuk_fark(z, O.liste(ref_z))
    temas = D < 8.0
    dolayli = (~temas) & ((temas.double() @ temas.double()) > 0)            # doğrudan temas yok, ortak komşu var
    artis_dolayli = float((ref_z - Z)[dolayli].mean())
    artis_uzak = float((ref_z - Z)[~temas & ~dolayli].mean()) if (~temas & ~dolayli).any() else 0.0

    # MSA satır dikkati: gerçek dizi (one-hot) ve mesafe yanlılığı
    harfler = sorted(set(UC.values()))
    dizi = "".join(UC.get(k["res"], "X") for k in kal)
    X1 = torch.zeros(N, 20, dtype=torch.float64)
    for i, c in enumerate(dizi):
        if c in harfler:
            X1[i, harfler.index(c)] = 1.0
    h = AYAR["h"]
    W = [torch.randn(20, h, generator=g, dtype=torch.float64) * 0.3 for _ in range(4)]
    yanlilik = -D / 4.0
    o = msa_satir_dikkati(O.liste(X1), O.liste(yanlilik), *[O.liste(w) for w in W])
    q, k_, v = X1 @ W[0], X1 @ W[1], X1 @ W[2]
    a = torch.softmax(q @ k_.T / math.sqrt(h) + yanlilik, 1)
    cikti = torch.sigmoid(X1 @ W[3]) * (a @ v)
    msa_fark = max(O.en_buyuk_fark(o["dikkat"], O.liste(a)), O.en_buyuk_fark(o["cikti"], O.liste(cikti)))
    a0 = torch.softmax(q @ k_.T / math.sqrt(h), 1)
    komsu_payi = float((torch.tensor(o["dikkat"], dtype=torch.float64) * temas.double()).sum(1).mean())
    komsu_payi_yanliliksiz = float((a0 * temas.double()).sum(1).mean())
    return {
        "surumler": O.surumler(), "pdb": "1UBQ (ubikuitin, 1.8 Å)", "kalinti": N, "dizi": dizi,
        "se3": sonuc, "drmsd_ayni": drmsd_ayni,
        "donme_degismez": sonuc["dondurulmus"]["ozdes"] and sonuc["dondurulmus"]["kabsch_rmsd"] < 1e-6,
        "ayna_gorunmez": sonuc["ayna"]["ozdes"] and sonuc["ayna"]["kabsch_rmsd"] > 1.0,
        "kiralite_orijinal": kir_orijinal, "kiralite_ayna": kir_ayna, "kiralite_ayirt_ediyor": abs(kir_orijinal - kir_ayna) > 0.8,
        "degerlendirme_kapisi": kapi,
        "metrik_oyunu_olculdu": (kapi["ayna"]["yalniz_drmsd_kabul"] and not kapi["ayna"]["drmsd_ve_kiralite_kabul"]
                                 and kapi["dondurulmus"]["drmsd_ve_kiralite_kabul"] and not kapi["rastgele_zincir"]["yalniz_drmsd_kabul"]),
        "ucgen_fark": ucgen_fark, "ucgen_ayni": ucgen_fark <= 1e-4, "ucgen_artis_dolayli": artis_dolayli, "ucgen_artis_uzak": artis_uzak,
        "msa_fark": msa_fark, "msa_ayni": msa_fark <= 1e-5, "komsu_dikkat_payi": komsu_payi, "komsu_dikkat_payi_yanliliksiz": komsu_payi_yanliliksiz,
        "olcum": (f"1UBQ ({N} kalıntı) CA koordinatları: dRMSD dönmüş kopyada {sonuc['dondurulmus']['drmsd']}, {AYAR['gurultu_a']} Å gürültülüde "
                  f"{sonuc['gurultulu']['drmsd']} (Kabsch RMSD {sonuc['gurultulu']['kabsch_rmsd']:.2f}), aynada {sonuc['ayna']['drmsd']} "
                  f"(Kabsch RMSD {sonuc['ayna']['kabsch_rmsd']:.1f} Å). Kiralite (CA etrafında pozitif hacim oranı) orijinal {kir_orijinal:.2f}, "
                  f"ayna {kir_ayna:.2f}. Üçgen güncelleme torch'tan {ucgen_fark:.1e}; doğrudan teması olmayan ama ortak komşusu olan çiftlerde "
                  f"ortalama artış {artis_dolayli:.3f}, uzak çiftlerde {artis_uzak:.3f}. MSA satır dikkati torch'tan {msa_fark:.1e}; mesafe "
                  f"yanlılığıyla dikkatin %{100 * komsu_payi:.0f}'i 8 Å içindeki kalıntılara (yanlılıksız %{100 * komsu_payi_yanliliksiz:.0f}). "
                  "Değerlendirme kapısı (dRMSD < 1 Å / dRMSD + kiralite ≥ 0.8): "
                  + "; ".join(f"{a} {v['yalniz_drmsd_kabul']} / {v['drmsd_ve_kiralite_kabul']}" for a, v in kapi.items()) + "."),
        "sinir": ("Gerçek bir yapı tahmin modeli çalıştırılmaz; çift temsili temas haritasından, MSA ise tek bir gerçek diziden kurulur ve "
                  "ağırlıklar rastgeledir. Kiralite CA etrafındaki işaretli hacimle kaba olarak ölçülür (glisinler hariç)."),
    }


def goster(ucgen_carpimsal_guncelle, se3_degismez_rmsd, msa_satir_dikkati):
    r = deney(ucgen_carpimsal_guncelle, se3_degismez_rmsd, msa_satir_dikkati)
    print("1UBQ dizisi:", r["dizi"])
    for k, v in r["se3"].items():
        print("  %-11s dRMSD %.4f | Kabsch RMSD %.3f | özdeş: %s" % (k, v["drmsd"], v["kabsch_rmsd"], v["ozdes"]))
    print("Kiralite: orijinal %.2f | ayna %.2f" % (r["kiralite_orijinal"], r["kiralite_ayna"]))
    print("Üçgen güncelleme farkı %.1e | dolaylı artış %.3f, uzak %.3f" % (r["ucgen_fark"], r["ucgen_artis_dolayli"], r["ucgen_artis_uzak"]))
    print("MSA dikkati farkı %.1e | 8 Å komşu payı %.2f (yanlılıksız %.2f)" % (r["msa_fark"], r["komsu_dikkat_payi"], r["komsu_dikkat_payi_yanliliksiz"]))
    print("Sınır:", r["sinir"])
    print("Kanıt:", O.kanit("ai-uretim-30", "run", r))
