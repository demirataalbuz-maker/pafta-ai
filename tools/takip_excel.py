# -*- coding: utf-8 -*-
"""Pafta_Takip.xlsx dosyasını DENETIM.md ve ASAMA2.md kaynaklarından sade biçimde üreten betik.

Kullanım:
    python -X utf8 tools/takip_excel.py
"""
import json
import os
import re
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DENETIM_PATH = os.path.join(ROOT, "DENETIM.md")
ASAMA2_PATH = os.path.join(ROOT, "ASAMA2.md")
OUTPUT_PATH = os.path.join(ROOT, "Pafta_Takip.xlsx")

# Renkler (açık pastel dolgular ve koyu okunabilir metinler)
FILL_BITTI = PatternFill(start_color="D4EDDA", end_color="D4EDDA", fill_type="solid")
FONT_BITTI = Font(name="Segoe UI", size=10, bold=True, color="155724")
FILL_BITTI_SATIR = PatternFill(start_color="E6F4EA", end_color="E6F4EA", fill_type="solid")

FILL_CALISILIYOR = PatternFill(start_color="FFF3CD", end_color="FFF3CD", fill_type="solid")
FONT_CALISILIYOR = Font(name="Segoe UI", size=10, bold=True, color="856404")

# Kullanıcı isteği (25 Ekim): Codex / Opus 4.8'in alacağı maddeler kırmızı, Claude'un alabilecekleri mavi
# (docs/durum.json'daki codex-opus ve claude-alabilir durumları)
FILL_KIRMIZI = PatternFill(start_color="F8D0CC", end_color="F8D0CC", fill_type="solid")
FILL_MAVI = PatternFill(start_color="CFE0FA", end_color="CFE0FA", fill_type="solid")
FILL_BEKLIYOR = PatternFill(start_color="F8F9FA", end_color="F8F9FA", fill_type="solid")
FONT_BEKLIYOR = Font(name="Segoe UI", size=10, bold=False, color="495057")

FILL_HEADER = PatternFill(start_color="203764", end_color="203764", fill_type="solid")
FONT_HEADER = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")

FILL_OZET = PatternFill(start_color="E9ECEF", end_color="E9ECEF", fill_type="solid")
FONT_OZET = Font(name="Segoe UI", size=11, bold=True, color="212529")

FONT_DATA = Font(name="Segoe UI", size=10)
FONT_SIRA = Font(name="Segoe UI", size=10, bold=True, color="495057")

THIN_BORDER = Border(
    left=Side(style="thin", color="DEE2E6"),
    right=Side(style="thin", color="DEE2E6"),
    top=Side(style="thin", color="DEE2E6"),
    bottom=Side(style="thin", color="DEE2E6")
)


def parse_asama2(path):
    """ASAMA2.md'deki her yol tablosundan madde adı, neden gerekli ve önerilen yazarı çıkarır."""
    items = {}
    current_track = None
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("## ") and "tracks/" in line:
                idx = line.find("tracks/")
                end_idx = line.find("`", idx)
                current_track = line[idx + 7:end_idx] if end_idx != -1 else line[idx + 7:].strip()
                continue
            if current_track and line.startswith("|") and not line.startswith("| Eksik") and not line.startswith("|---"):
                parts = [p.strip().replace(r"\|", "|") for p in re.split(r"(?<!\\)\|", line)[1:-1]]
                if len(parts) >= 5:
                    madde = parts[0]
                    neden = parts[1]
                    oneri_yazar = parts[4]
                    items[(current_track, madde)] = {
                        "madde": madde,
                        "neden": neden,
                        "oneri_yazar": oneri_yazar,
                        "yol": current_track
                    }
                    items[madde] = items[(current_track, madde)]
    return items


def parse_denetim(path):
    """DENETIM.md'den açık bulguları ve Aşama 2 durum tablosundaki 90 maddeyi çıkarır."""
    acik_bulgular = []
    durum_maddeleri = []

    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    # Açık bulgular tablosu
    in_acik = False
    for line in lines:
        if line.startswith("## Açık bulgular"):
            in_acik = True
            continue
        if in_acik:
            if line.startswith("## ") or line.startswith("**"):
                break
            if line.startswith("|") and not line.startswith("| #") and not line.startswith("|---"):
                parts = [p.strip().replace(r"\|", "|") for p in re.split(r"(?<!\\)\|", line)[1:-1]]
                if len(parts) >= 5 and parts[0].startswith("A"):
                    acik_bulgular.append({
                        "no": parts[0],
                        "yer": parts[1],
                        "bulgu": parts[2],
                        "duzeltme": parts[3],
                        "sahibi": parts[4]
                    })

    # Aşama 2 durum tablosu
    in_durum = False
    for line in lines:
        if "### Aşama 2 durum tablosu" in line:
            in_durum = True
            continue
        if in_durum:
            if line.startswith("| Sıra | Yol |"):
                break
            if line.startswith("|") and not line.startswith("| #") and not line.startswith("|---"):
                parts = [p.strip().replace(r"\|", "|") for p in re.split(r"(?<!\\)\|", line)[1:-1]]
                if len(parts) >= 6 and parts[0].isdigit():
                    durum_maddeleri.append({
                        "no": int(parts[0]),
                        "yol": parts[1],
                        "madde": parts[2],
                        "dalga": parts[3],
                        "yazar": parts[4],
                        "durum": parts[5]
                    })

    return acik_bulgular, durum_maddeleri


def normalize_durum(raw_durum):
    """Durum metnini Bitti, Çalışılıyor veya Bekliyor kategorisine eşler."""
    raw_lower = raw_durum.lower()
    if raw_lower.startswith("denetlendi") or "bitti" in raw_lower:
        return "Bitti"
    if "verildi" in raw_lower or "çalışılıyor" in raw_lower or "yazılıyor" in raw_lower or "kısmen" in raw_lower:
        return "Çalışılıyor"
    return "Bekliyor"


YOL_ADI = {"python": "Python", "bash": "Bash", "powershell": "PowerShell", "cmd": "CMD", "http": "HTTP ve HTML",
           "sql": "SQL", "kql": "KQL", "spl": "SPL", "elastic": "Elastic", "sigma": "Sigma", "yara": "YARA",
           "regex": "Regex", "packets": "Wireshark/tcpdump", "ad": "Active Directory", "java": "Java",
           "csharp": "C#", "c": "C", "php": "PHP", "javascript": "JavaScript", "asm": "Assembly"}


def build_ne_yapilacak(madde, neden, yol=""):
    """Kısa satır: hangi yola, hangi madde. Ayrıntı (neden) ASAMA2.md'de kalır; kullanıcı kısa liste istedi."""
    m = madde.replace("(Antigravity önerisi)", "").strip()
    return f"{YOL_ADI.get(yol, yol)}: {m}" if yol else m


def style_sheet(ws, title, is_bitenler=False):
    """Sayfa başlıklarını, sütun genişliklerini ve hizalamalarını ayarlar."""
    ws.views.sheetView[0].showGridLines = True
    ws.column_dimensions["A"].width = 10
    ws.column_dimensions["B"].width = 110
    ws.column_dimensions["C"].width = 24
    ws.column_dimensions["D"].width = 20


def durum_renkleri():
    """docs/durum.json: madde adı → durum (yalnız renklendirme için)."""
    yol = os.path.join(ROOT, "docs", "durum.json")
    if not os.path.isfile(yol):
        return {}
    with open(yol, encoding="utf-8") as f:
        return {ad: d.get("durum", "") for ad, d in json.load(f).get("maddeler", {}).items()}


def main():
    renkler = durum_renkleri()
    asama2_dict = parse_asama2(ASAMA2_PATH)
    acik_bulgular, durum_maddeleri = parse_denetim(DENETIM_PATH)

    # Maddeleri kategorilere ayır
    yapilacak_acik_hatalar = []
    yapilacak_ilk_dalga = []
    yapilacak_kalanlar = []
    bitenler = []

    for a in acik_bulgular:
        ne_yapilacak = f"{a['no']}: {a['yer']} — {a['duzeltme']}"
        if not ne_yapilacak.endswith("."):
            ne_yapilacak += "."
        yapilacak_acik_hatalar.append({
            "kaynak_id": a["no"],
            "ne_yapilacak": ne_yapilacak,
            "kim_yapacak": a["sahibi"],
            "durum": "Bekliyor"
        })

    for item in durum_maddeleri:
        durum_norm = normalize_durum(item["durum"])
        info = asama2_dict.get((item["yol"], item["madde"])) or asama2_dict.get(item["madde"])
        neden = info["neden"] if info else item["madde"]
        kim = item["yazar"]
        if kim == "—" and info and info.get("oneri_yazar"):
            kim = info["oneri_yazar"]

        ne_yapilacak = build_ne_yapilacak(item["madde"], neden, item["yol"])
        kayit = {
            "kaynak_id": item["no"],
            "ne_yapilacak": ne_yapilacak,
            "kim_yapacak": kim,
            "durum": durum_norm,
            "dalga": item["dalga"]
        }

        if durum_norm == "Bitti":
            bitenler.append(kayit)
        else:
            if item["dalga"].startswith("1"):
                yapilacak_ilk_dalga.append(kayit)
            else:
                yapilacak_kalanlar.append(kayit)

    # Kullanıcı isteği (24 Ekim): biten maddeler listeden düşmez; ilk sayfada açık hatalar ve
    # ardından bütün maddeler kendi sırasıyla görünür, bitenlerin satırı yeşildir.
    tum_maddeler = sorted(bitenler + yapilacak_ilk_dalga + yapilacak_kalanlar, key=lambda k: k["kaynak_id"])
    tum_yapilacaklar = yapilacak_acik_hatalar + tum_maddeler

    toplam_bitti = len(bitenler)
    toplam_kaldi = len(yapilacak_acik_hatalar) + len(yapilacak_ilk_dalga) + len(yapilacak_kalanlar)

    wb = openpyxl.Workbook()

    # --- 1. SAYFA: Yapılacaklar ---
    ws_yapilacak = wb.active
    ws_yapilacak.title = "Yapılacaklar"   # ad korunur: tools/durum_listesi.py bu sayfayı okur
    style_sheet(ws_yapilacak, "Yapılacaklar")

    # En başta tek satırlık özet
    ozet_metin = (f"Özet: {toplam_bitti} bitti (yeşil), {toplam_kaldi} kaldı (Açık hatalar: {len(yapilacak_acik_hatalar)}, "
                  f"İlk dalga: {len(yapilacak_ilk_dalga)}, Kalan maddeler: {len(yapilacak_kalanlar)})")
    ws_yapilacak.merge_cells("A1:D1")
    cell_ozet1 = ws_yapilacak["A1"]
    cell_ozet1.value = ozet_metin
    cell_ozet1.font = FONT_OZET
    cell_ozet1.fill = FILL_OZET
    cell_ozet1.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws_yapilacak.row_dimensions[1].height = 28

    # Başlık satırı
    headers = ["Sıra", "Ne yapılacak", "Kim yapacak", "Durum"]
    for col_idx, h in enumerate(headers, 1):
        cell = ws_yapilacak.cell(row=2, column=col_idx, value=h)
        cell.font = FONT_HEADER
        cell.fill = FILL_HEADER
        cell.alignment = Alignment(horizontal="center" if col_idx in (1, 4) else "left", vertical="center")
        cell.border = THIN_BORDER
    ws_yapilacak.row_dimensions[2].height = 24

    # Veri satırları
    for idx, item in enumerate(tum_yapilacaklar, 1):
        r = idx + 2
        ws_yapilacak.row_dimensions[r].height = 26
        bitti = item["durum"] == "Bitti"

        # Sıra
        c_sira = ws_yapilacak.cell(row=r, column=1, value=idx)
        c_sira.font = FONT_SIRA
        c_sira.alignment = Alignment(horizontal="center", vertical="center")
        c_sira.border = THIN_BORDER

        # Ne yapılacak
        c_is = ws_yapilacak.cell(row=r, column=2, value=item["ne_yapilacak"])
        c_is.font = FONT_DATA
        c_is.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        c_is.border = THIN_BORDER

        # Kim yapacak
        c_kim = ws_yapilacak.cell(row=r, column=3, value=item["kim_yapacak"])
        c_kim.font = FONT_DATA
        c_kim.alignment = Alignment(horizontal="left", vertical="center")
        c_kim.border = THIN_BORDER

        # Durum
        c_durum = ws_yapilacak.cell(row=r, column=4, value="Bitti (denetlendi)" if bitti else item["durum"])
        if bitti:
            for c in (c_sira, c_is, c_kim):
                c.fill = FILL_BITTI_SATIR
        elif renkler.get(item["ne_yapilacak"]) in ("codex-opus", "claude-alabilir"):
            kirmizi = renkler[item["ne_yapilacak"]] == "codex-opus"
            c_kim.value = "Codex / Opus 4.8" if kirmizi else "Claude"
            for c in (c_sira, c_is, c_kim):
                c.fill = FILL_KIRMIZI if kirmizi else FILL_MAVI
        if item["durum"] == "Bitti":
            c_durum.fill = FILL_BITTI
            c_durum.font = FONT_BITTI
        elif item["durum"] == "Çalışılıyor":
            c_durum.fill = FILL_CALISILIYOR
            c_durum.font = FONT_CALISILIYOR
        else:
            c_durum.fill = FILL_BEKLIYOR
            c_durum.font = FONT_BEKLIYOR
        c_durum.alignment = Alignment(horizontal="center", vertical="center")
        c_durum.border = THIN_BORDER

    # --- 2. SAYFA: Bitenler ---
    ws_biten = wb.create_sheet(title="Bitenler")
    style_sheet(ws_biten, "Bitenler", is_bitenler=True)

    # En başta tek satırlık özet
    ws_biten.merge_cells("A1:D1")
    cell_ozet2 = ws_biten["A1"]
    cell_ozet2.value = f"Özet: {toplam_bitti} bitti, {toplam_kaldi} kaldı"
    cell_ozet2.font = FONT_OZET
    cell_ozet2.fill = FILL_OZET
    cell_ozet2.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws_biten.row_dimensions[1].height = 28

    # Başlık satırı
    headers_biten = ["Sıra", "Ne yapıldı", "Kim yaptı", "Durum"]
    for col_idx, h in enumerate(headers_biten, 1):
        cell = ws_biten.cell(row=2, column=col_idx, value=h)
        cell.font = FONT_HEADER
        cell.fill = FILL_HEADER
        cell.alignment = Alignment(horizontal="center" if col_idx in (1, 4) else "left", vertical="center")
        cell.border = THIN_BORDER
    ws_biten.row_dimensions[2].height = 24

    # Biten veri satırları
    for idx, item in enumerate(bitenler, 1):
        r = idx + 2
        ws_biten.row_dimensions[r].height = 26

        c_sira = ws_biten.cell(row=r, column=1, value=idx)
        c_sira.font = FONT_SIRA
        c_sira.alignment = Alignment(horizontal="center", vertical="center")
        c_sira.border = THIN_BORDER

        c_is = ws_biten.cell(row=r, column=2, value=item["ne_yapilacak"])
        c_is.font = FONT_DATA
        c_is.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        c_is.border = THIN_BORDER

        c_kim = ws_biten.cell(row=r, column=3, value=item["kim_yapacak"])
        c_kim.font = FONT_DATA
        c_kim.alignment = Alignment(horizontal="left", vertical="center")
        c_kim.border = THIN_BORDER

        c_durum = ws_biten.cell(row=r, column=4, value=item["durum"])
        c_durum.fill = FILL_BITTI
        c_durum.font = FONT_BITTI
        c_durum.alignment = Alignment(horizontal="center", vertical="center")
        c_durum.border = THIN_BORDER

    wb.save(OUTPUT_PATH)
    print(f"Pafta_Takip.xlsx oluşturuldu: {toplam_bitti} bitti, {toplam_kaldi} kaldı ({OUTPUT_PATH})")


if __name__ == "__main__":
    main()
